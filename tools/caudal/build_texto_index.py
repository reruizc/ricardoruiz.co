#!/usr/bin/env python3
"""
Caudal · índice invertido de TEXTO COMPLETO de Gaceta del Congreso.

Hasta ahora buscar() solo matchea contra el TÍTULO del proyecto (+ alias de
sanción). Un término puede no estar en el título pero sí adentro de la
ponencia/acta — este índice cierra ese hueco: palabra → [proyectos cuyas
gacetas mencionan esa palabra], construido sobre los ~12.5k textos ya
cosechados en s3://caudal-legislativo/gacetas-texto/ (harvest_gacetas_texto.py).

Mecánica:
  1. Carga proyectos.jsonl + actos-legis.jsonl (dist/) → para cada uno, sus
     gacetas referenciadas (campo 'gaceta': 'NNN/AAAA').
  2. Invierte a gaceta_key → [proyectos] (una gaceta puede ser común a varios
     si comparten radicación/conciliación bicameral).
  3. Para cada gaceta_key con texto en S3 (streaming vía `aws s3 cp - `, SIN
     tocar disco — el corpus completo son ~3GB, no vale la pena bajarlo
     entero dado lo ajustado que ha andado el disco hoy), extrae palabras
     significativas (≥5 chars, sin stopwords, stem) y las asigna a TODOS los
     proyectos que referencian esa gaceta.
  4. Filtra palabras demasiado comunes (aparecen en >12% de los proyectos
     procesados) — no discriminan y solo inflan el índice.
  5. Escribe dist/texto-index.json ({palabra: [tb:id, ...]}).

Uso: python3 tools/caudal/build_texto_index.py [--workers 8] [--max-docfreq 0.12]
"""
import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DIST = REPO / 'Bases de datos' / 'leyes-senado' / 'dist'
BUCKET = 'caudal-legislativo'

sys.path.insert(0, str(Path(__file__).resolve().parent))
# el MISMO _stem que usa caudal_core.buscar() para la query — si difiriera del
# de clasificar.py (que usa otra lista de sufijos), el índice podría fallar en
# matchear justo los términos que motivaron esto (ver "clonación").
from caudal_core import _stem, _norm as _core_norm  # noqa: E402

MIN_LEN = 5

# stopwords de PROSA legislativa (más amplio que el de títulos — cuerpo de
# ponencias/actas trae narrativa completa, no solo la fórmula del título).
_STOP_BODY = set("""
de la el los las del y o en a por para con un una que al su sus este esta ese
esa cual cuales medio dicta dictan dictase otra otras otro otros sobre e u
como mediante entre segun cada ser tener hacer fue son fueron era eran esta
estan estaba estaban sido siendo hay habia hubo puede pueden podra podran debe
deben debera deberan asi tambien mas pero sino aunque cuando donde mientras
desde hasta sin bajo ante tras durante todo toda todos todas mismo misma
mismos mismas otro otra cada cual quien quienes cuyo cuya donde adonde
articulo articulos numeral numerales literal literales paragrafo paragrafos
inciso incisos capitulo capitulos titulo titulos libro libros seccion
secciones ley leyes decreto decretos resolucion resoluciones acuerdo acuerdos
codigo codigos norma normas disposicion disposiciones proyecto acto
legislativo honorable honorables senado camara republica congreso comision
comisiones plenaria plenarias colombia colombiano colombiana colombianos
colombianas nacional nacionales gobierno estado publico publica publicos
publicas presidente presidenta ministro ministra ministerio secretaria
secretario doctor doctora senador senadora representante representantes
gaceta bogota constitucion constitucional politica economico economica social
ponente ponentes ponencia ponencias debate debates sesion sesiones fecha
firmado firmada radicado radicada presentado presentada expide expiden
adopta adoptan adoptase modifica modifican reglamenta reglamentan establece
establecen crea crean deroga derogan sancion sanciona gobierno nacional
""".split())


WORD_RE = re.compile(r'[a-z]{%d,}' % MIN_LEN)


def significant_words(texto):
    """set de stems significativos del texto (dedup — no interesa frecuencia
    intra-documento para un índice invertido de presencia, solo de si existe)."""
    t = _core_norm(texto)
    out = set()
    for w in WORD_RE.findall(t):
        if w in _STOP_BODY:
            continue
        out.add(_stem(w))
    return out


def load(name):
    p = DIST / name
    return [json.loads(l) for l in open(p, encoding='utf-8')] if p.exists() else []


MAX_COMPARTIDA = 4   # una gaceta referenciada por más de N proyectos es casi
                     # seguro un boletín de radicación masiva (verificado:
                     # Gaceta 596/2020 sola trae la exposición de motivos de
                     # decenas de proyectos radicados el mismo día) — indexarla
                     # significa que un término mencionado por CUALQUIERA de
                     # esos proyectos "contamina" a todos los demás. Se excluye
                     # completa en vez de intentar aislar por proyecto (eso ya
                     # lo hace, con LLM, la acción `gaceta`/`profundizar` — este
                     # índice es de presencia gruesa, no de atribución exacta).


def build_gaceta_to_proyectos():
    """gaceta_key 'NNN-AAAA' -> [tokens 'tb:id'] de los proyectos que la
    referencian — EXCLUYE exposición de motivos (siempre es la radicación,
    la más propensa a venir en boletines de decenas de proyectos juntos) y
    cualquier gaceta compartida por más de MAX_COMPARTIDA proyectos."""
    mp = defaultdict(list)
    for fn, tb in [('proyectos.jsonl', 'pdly'), ('actos-legis.jsonl', 'pal')]:
        for r in load(fn):
            tok = f"{tb}:{r['id']}"
            for g in r.get('gacetas', []):
                gk = g.get('gaceta')
                if gk and g.get('tipo') != 'exposicion_motivos':
                    mp[gk.replace('/', '-')].append(tok)
    return {k: v for k, v in mp.items() if len(v) <= MAX_COMPARTIDA}


def fetch_texto(key):
    """Trae el texto de una gaceta SIN tocar disco (stdout de aws s3 cp -)."""
    r = subprocess.run(
        ['aws', 's3', 'cp', f's3://{BUCKET}/gacetas-texto/{key}.txt', '-'],
        capture_output=True, timeout=60)
    if r.returncode != 0:
        return None
    return r.stdout.decode('utf-8', errors='replace')


CACHE = DIST / '_texto_words_cache.json'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--max-docfreq', type=float, default=0.05)
    ap.add_argument('--limit', type=int, default=0, help='solo para pruebas')
    ap.add_argument('--from-cache', action='store_true',
                    help='reusa las palabras ya extraídas por gaceta (sin volver a bajar de S3) — '
                         'para iterar el filtro de frecuencia sin repetir ~15 min de red')
    args = ap.parse_args()

    print('· cruzando proyectos con sus gacetas referenciadas…')
    gac2proy = build_gaceta_to_proyectos()
    keys = list(gac2proy.keys())
    if args.limit:
        keys = keys[:args.limit]
    print(f'  {len(keys)} gacetas distintas referenciadas por algún proyecto')

    if args.from_cache and CACHE.exists():
        print(f'  · reusando caché de palabras por gaceta ({CACHE.name})')
        cache = json.load(open(CACHE, encoding='utf-8'))
        doc_words = {k: set(v) for k, v in cache.items()}
        n_ok, n_sinTexto = len(doc_words), 0
    else:
        doc_words = {}
        n_ok = n_sinTexto = 0

        def _procesar(key):
            txt = fetch_texto(key)
            if not txt:
                return key, None
            return key, significant_words(txt)

        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(_procesar, k): k for k in keys}
            done = 0
            for fut in as_completed(futs):
                key = futs[fut]
                try:
                    _, words = fut.result()
                except Exception:
                    words = None
                done += 1
                if words is None:
                    n_sinTexto += 1
                else:
                    n_ok += 1
                    doc_words[key] = words
                if done % 200 == 0:
                    print(f'  …{done}/{len(keys)} · con texto={n_ok} sin texto={n_sinTexto}')

        json.dump({k: sorted(v) for k, v in doc_words.items()}, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False)
        print(f'  · caché de palabras guardado en {CACHE.name} (para re-filtrar sin red: --from-cache)')

    print(f'\n{n_ok} gacetas con texto procesadas · {n_sinTexto} sin texto en S3 (aún no cosechadas)')

    inv = defaultdict(set)          # palabra -> set(tokens)
    for key, words in doc_words.items():
        for tok in gac2proy.get(key, []):
            for w in words:
                inv[w].add(tok)
    print(f'{len(inv)} palabras distintas antes del filtro de frecuencia máxima')

    # universo de proyectos que recibieron AL MENOS una palabra (denominador del docfreq)
    proyectos_tocados = set()
    for toks in inv.values():
        proyectos_tocados |= toks
    n_proy = max(len(proyectos_tocados), 1)
    cutoff = args.max_docfreq * n_proy

    filtrado = {w: sorted(toks) for w, toks in inv.items() if len(toks) <= cutoff}
    n_descartadas = len(inv) - len(filtrado)
    print(f'{n_descartadas} palabras descartadas por ser demasiado comunes (>{args.max_docfreq:.0%} de {n_proy} proyectos)')
    print(f'{len(filtrado)} palabras en el índice final')

    # ids como ENTEROS (índice a la lista 'ids') en vez de strings 'pdly:1234'
    # repetidas miles de veces — corta bastante el tamaño del JSON final.
    todos_ids = sorted(proyectos_tocados)
    id_pos = {tok: i for i, tok in enumerate(todos_ids)}
    filtrado_int = {w: sorted(id_pos[t] for t in toks) for w, toks in filtrado.items()}

    out = {'v': '2026-07-22', 'n_gacetas_procesadas': n_ok, 'n_proyectos_cubiertos': n_proy,
           'n_palabras': len(filtrado_int), 'ids': todos_ids, 'index': filtrado_int}
    outp = DIST / 'texto-index.json'
    json.dump(out, open(outp, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'\n→ {outp.relative_to(REPO)} · {outp.stat().st_size/1024/1024:.1f} MB')


if __name__ == '__main__':
    main()
