#!/usr/bin/env python3
"""
Caudal · índice invertido de TEXTO COMPLETO de Gaceta del Congreso.

Hasta ahora buscar() solo matchea contra el TÍTULO del proyecto (+ alias de
sanción). Un término puede no estar en el título pero sí adentro de la
ponencia/acta — este índice cierra ese hueco: palabra → [proyectos cuyas
gacetas mencionan esa palabra], construido sobre los ~12.5k textos ya
cosechados en s3://caudal-legislativo/gacetas-texto/ (harvest_gacetas_texto.py).

DOS FUENTES DE TEXTO (jul-2026 en adelante)
-------------------------------------------
  a) GACETAS del trámite (gacetas-texto/) — el histórico.
  b) TEXTO DEL RADICADO de la legislatura EN CURSO (radicados-texto/ y
     radicados-camara-texto/), que el cron diario baja 2x/día.

(b) se agregó porque el índice se construía solo con (a) y la legislatura viva
no se podía buscar por articulado: los proyectos que se están debatiendo HOY
—justo los que le importan a un cliente que paga— eran invisibles al texto. Los
radicados son un documento POR proyecto (no un boletín), así que no les aplica
el filtro MAX_COMPARTIDA, y se leen del disco local del cron cuando está
disponible (gratis) antes que de S3.

Mecánica:
  1. Carga proyectos.jsonl + actos-legis.jsonl (dist/) → para cada uno, sus
     gacetas referenciadas (campo 'gaceta': 'NNN/AAAA') y su texto de radicado
     (campo 'texto_s3', que pone build_dataset).
  2. Invierte a documento → [proyectos] (una gaceta puede ser común a varios
     si comparten radicación/conciliación bicameral; un radicado nunca).
  3. Para cada documento con texto, extrae palabras significativas (≥5 chars,
     sin stopwords, stem) y las asigna a los proyectos que lo referencian. Las
     gacetas se traen de S3 por streaming (`aws s3 cp -`, SIN tocar disco: el
     corpus completo son ~3GB); los radicados salen del disco local del cron.
  4. Filtra palabras demasiado comunes (aparecen en >5% de los proyectos
     procesados) — no discriminan y solo inflan el índice.
  5. Escribe dist/texto-index.json ({palabra: [tb:id, ...]}).

Uso:
  python3 tools/caudal/build_texto_index.py [--workers 8] [--max-docfreq 0.05]
  # tras cosechar gacetas nuevas (reusa el caché, solo baja lo que falta):
  python3 tools/caudal/build_texto_index.py --incremental
  # solo re-filtrar sin tocar la red:
  python3 tools/caudal/build_texto_index.py --from-cache
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

MAX_COMPARTIDA_EXPO = 2
# La exposición de motivos estaba excluida SIEMPRE, con el argumento de que es
# la más propensa a venir en boletines. Medido (ago-2026), el argumento tapaba
# el caso bueno: de las 2.930 gacetas de expo-motivos que los proyectos
# referencian, 1.433 pertenecen a UN SOLO proyecto — ahí la gaceta no es un
# boletín, es literalmente el texto radicado de ese proyecto, y excluirla era
# botar la única fuente de texto que tienen los proyectos que mueren antes del
# primer debate (o sea, el 74% del universo: los que nunca generan ponencia).
# Por eso ahora entra con umbral PROPIO y más estricto que el general: 1 o 2
# proyectos. El riesgo de contaminación a 2 es simétrico y acotado, el mismo que
# ya se acepta para las ponencias compartidas. Medido: +441 proyectos con texto
# sin bajar un solo archivo nuevo (ya estaban en S3), +974 más al cosechar.
# ⚠️ Este criterio debe seguir siendo IDÉNTICO al de
# harvest_gacetas_texto.indexable_keys(), o el harvester bajaría un set distinto
# del que el índice consume.


def build_gaceta_to_proyectos():
    """gaceta_key 'NNN-AAAA' -> [tokens 'tb:id'] de los proyectos que la
    referencian. Descarta las compartidas por demasiados proyectos, con umbral
    más estricto para la exposición de motivos (ver MAX_COMPARTIDA_EXPO)."""
    mp = defaultdict(list)
    solo_expo = defaultdict(bool)
    for fn, tb in [('proyectos.jsonl', 'pdly'), ('actos-legis.jsonl', 'pal')]:
        for r in load(fn):
            tok = f"{tb}:{r['id']}"
            for g in r.get('gacetas', []):
                gk = g.get('gaceta')
                if not gk:
                    continue
                k = gk.replace('/', '-')
                mp[k].append(tok)
                # una gaceta puede ser expo-motivos de un proyecto y ponencia de
                # otro; el umbral estricto solo aplica si SIEMPRE es expo.
                solo_expo[k] = solo_expo.get(k, True) and g.get('tipo') == 'exposicion_motivos'
    return {k: v for k, v in mp.items()
            if len(v) <= (MAX_COMPARTIDA_EXPO if solo_expo[k] else MAX_COMPARTIDA)}


RAD_PREFIX = 'rad::'      # separa las llaves de radicado de las de gaceta en el
                          # mismo caché, sin invalidar lo ya extraído


# el cron deja el mismo .txt en disco antes de subirlo; la ruta es derivable de
# la key, así que no hace falta ensuciar el dataset (que va a S3) con rutas de
# esta máquina. Si el local no está, se cae a S3 sin ruido.
_DIARIO = {'radicados-texto': REPO / 'Bases de datos' / 'leyes-senado' / 'diario',
           'radicados-camara-texto': REPO / 'Bases de datos' / 'leyes-senado' / 'diario-camara'}


def _local_de(key):
    partes = key.split('/')
    if len(partes) != 3 or partes[0] not in _DIARIO:
        return None
    _, leg, nombre = partes
    return _DIARIO[partes[0]] / leg / 'textos-txt' / nombre


def build_radicado_to_proyectos():
    """rad::{tb:id} -> ([token], ruta_local|None, key_s3) para el texto del
    radicado de la legislatura en curso. Un radicado es de UN solo proyecto."""
    mp = {}
    for fn, tb in [('proyectos.jsonl', 'pdly'), ('actos-legis.jsonl', 'pal')]:
        for r in load(fn):
            key = r.get('texto_s3')
            if not key:
                continue
            tok = f"{tb}:{r['id']}"
            mp[f'{RAD_PREFIX}{tok}'] = ([tok], _local_de(key), key)
    return mp


def fetch_texto(key, radicados=None):
    """Texto de un documento. Las gacetas se traen de S3 por streaming; los
    radicados salen del disco local del cron si está, y si no de S3."""
    if key.startswith(RAD_PREFIX):
        _, local, s3key = (radicados or {}).get(key, (None, None, None))
        if local and Path(local).exists():
            return Path(local).read_text(encoding='utf-8', errors='replace')
        if not s3key:
            return None
        s3path = f's3://{BUCKET}/{s3key}'
    else:
        s3path = f's3://{BUCKET}/gacetas-texto/{key}.txt'
    r = subprocess.run(['aws', 's3', 'cp', s3path, '-'],
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
    ap.add_argument('--incremental', action='store_true',
                    help='como --from-cache pero SÍ baja las gacetas que falten en el caché '
                         '(el modo normal tras una cosecha nueva: reusa lo ya extraído y '
                         'solo paga la red por lo nuevo)')
    args = ap.parse_args()

    print('· cruzando proyectos con sus gacetas referenciadas…')
    gac2proy = build_gaceta_to_proyectos()
    rad2proy = build_radicado_to_proyectos()
    doc2proy = dict(gac2proy)
    doc2proy.update({k: v[0] for k, v in rad2proy.items()})
    keys = list(doc2proy.keys())
    if args.limit:
        keys = keys[:args.limit]
    n_rad_local = sum(1 for _, loc, _ in rad2proy.values() if loc and loc.exists())
    print(f'  {len(gac2proy)} gacetas distintas referenciadas por algún proyecto')
    print(f'  {len(rad2proy)} textos de radicado de la legislatura viva '
          f'({n_rad_local} en disco local, el resto de S3)')

    doc_words = {}
    if (args.from_cache or args.incremental) and CACHE.exists():
        print(f'  · reusando caché de palabras por gaceta ({CACHE.name})')
        cache = json.load(open(CACHE, encoding='utf-8'))
        # solo lo que sigue siendo relevante para ESTE set de keys
        wanted = set(keys)
        doc_words = {k: set(v) for k, v in cache.items() if k in wanted}
        print(f'    {len(doc_words)} gacetas vienen del caché')

    if args.from_cache:
        pendientes = []          # --from-cache: no se toca la red
    else:
        pendientes = [k for k in keys if k not in doc_words]
    # los radicados cambian mientras la legislatura corre (el cron re-baja el
    # PDF cuando el proyecto se mueve) → se re-leen siempre. Son ~200 archivos
    # locales, cuesta segundos.
    frescos = [k for k in keys if k.startswith(RAD_PREFIX)]
    pendientes = list(dict.fromkeys(pendientes + frescos))

    n_ok, n_sinTexto = len(doc_words), 0
    if pendientes:
        print(f'  · bajando {len(pendientes)} gacetas que faltan…')

        def _procesar(key):
            txt = fetch_texto(key, rad2proy)
            if not txt:
                return key, None
            return key, significant_words(txt)

        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(_procesar, k): k for k in pendientes}
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
                    print(f'  …{done}/{len(pendientes)} · con texto={n_ok} sin texto={n_sinTexto}')

        # el caché se MERGEA (no se pisa): conserva gacetas de corridas anteriores
        # que hoy no estén en `keys` — si un proyecto cambia de gacetas, no hay
        # que volver a bajarlas.
        prev = {}
        if CACHE.exists():
            try:
                prev = json.load(open(CACHE, encoding='utf-8'))
            except Exception:
                prev = {}
        prev.update({k: sorted(v) for k, v in doc_words.items()})
        json.dump(prev, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False)
        print(f'  · caché actualizado ({len(prev)} gacetas) → --incremental la próxima vez')

    n_rad_ok = sum(1 for k in doc_words if k.startswith(RAD_PREFIX))
    print(f'\n{n_ok} documentos con texto procesados '
          f'({n_rad_ok} radicados de la legislatura viva) · '
          f'{n_sinTexto} sin texto (aún no cosechados)')

    inv = defaultdict(set)          # palabra -> set(tokens)
    for key, words in doc_words.items():
        for tok in doc2proy.get(key, []):
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

    out = {'v': '2026-08-02', 'n_gacetas_procesadas': n_ok, 'n_proyectos_cubiertos': n_proy,
           'n_radicados_procesados': n_rad_ok,
           'n_palabras': len(filtrado_int), 'ids': todos_ids, 'index': filtrado_int}
    outp = DIST / 'texto-index.json'
    json.dump(out, open(outp, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'\n→ {outp.relative_to(REPO)} · {outp.stat().st_size/1024/1024:.1f} MB')


if __name__ == '__main__':
    main()
