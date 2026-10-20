#!/usr/bin/env python3
"""
Mi Congreso · Fuerzas EXTERNAS de cada proyecto en trámite.

Para cada proyecto vivo de la legislatura 2026-2027 arma la lista de jugadores
de afuera del Congreso —gremios, empresas, entidades, organizaciones,
academia— con tres medidas, que la página dibuja en un plano:

  · postura  (eje X)  −1 en contra … +1 a favor, o null si no se ha
                      pronunciado. La lee DeepSeek en los titulares sobre el
                      tema y SIEMPRE va con la cita (índice del titular). Si el
                      modelo nombra a alguien que no aparece en ese titular, se
                      descarta: no se le atribuye a nadie una frase ajena.
  · cerca    (eje Y)  qué tan directo le toca: 1 = el articulado lo nombra ·
                      .6 = es del sector que el texto regula · .25 = solo
                      aparece en la conversación.
  · peso     (tamaño) cuántos titulares sobre el tema lo nombran.

Fuentes, todas ya existentes:
  · radicados, ficha y articulado ........ API pública de Caudal (proxy rr-auth)
  · titulares sobre el tema .............. acción `medios` (Google News)
  · empresas y gremios con su sector ..... diccionario de Caudal
                                           (tools/caudal/empresas.py)
  · congresistas a excluir (son internos)  fuerzas-internas-2026.json

El articulado de Cámara de la legislatura viva llega cruzado con el de otro
proyecto (oct-2026): se usa solo si su título casa con el del proyecto.

Salida: Bases de datos/legislativo/fuerzas-externas/{S|C}-{num}-{aa}.json + index.json
S3:     congreso-2026/output/legislativo/fuerzas-externas/ (público)

  python3 tools/mi-congreso/build_fuerzas_externas.py --solo 219/26     # un proyecto
  python3 tools/mi-congreso/build_fuerzas_externas.py --max 40          # los 40 primeros
  python3 tools/mi-congreso/build_fuerzas_externas.py --subir           # todos y sube
"""
import argparse
import collections
import concurrent.futures as cf
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tools' / 'caudal'))
import empresas as DIC  # noqa: E402

OUT = REPO / 'Bases de datos' / 'legislativo' / 'fuerzas-externas'
CACHE = OUT / '_cache'
INTERNAS = REPO / 'Bases de datos' / 'legislativo' / 'fuerzas-internas-2026.json'
S3_DIR = 's3://elecciones-2026/ricardoruiz.co/congreso-2026/output/legislativo/fuerzas-externas/'
API = 'https://rr-auth.reruizc.workers.dev/caudal/api'
DEEPSEEK_URL = 'https://api.deepseek.com/chat/completions'
DEEPSEEK_MODEL = 'deepseek-v4-flash'
PV = 'fx2'          # súbelo al cambiar el prompt: invalida la caché del modelo
DIAS = 60
MAX_ACTORES = 40

# ───────────────────────────────────────────────────────────── utilidades
def norm(s):
    s = unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9ñ ]', ' ', s)).strip()


_lock = threading.Lock()
_ultimo = [0.0]


def call(payload, intentos=3):
    """La API pública de Caudal, a no más de ~1,5 consultas por segundo."""
    for k in range(intentos):
        with _lock:
            espera = 0.5 - (time.time() - _ultimo[0])
            if espera > 0:
                time.sleep(espera)
            _ultimo[0] = time.time()
        rq = urllib.request.Request(API, data=json.dumps(payload).encode(), headers={
            'Origin': 'https://ricardoruiz.co', 'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh) Chrome/130 mi-congreso-fuerzas'})
        try:
            with urllib.request.urlopen(rq, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (404, 400):
                return None
            time.sleep(3 * (k + 1))
        except Exception:                                   # noqa: BLE001
            time.sleep(3 * (k + 1))
    return None


def tok_num(s):
    m = re.search(r'0*(\d{1,4})\s*/\s*(?:20)?(\d{2})', str(s or ''))
    return f'{int(m.group(1))}/{m.group(2)}' if m else None


def tok_proyecto(x):
    c = 'S' if x['_cam'] == 'Senado' else 'C'
    t = tok_num(x.get('numero_senado') or x.get('numero_camara')) if c == 'S' \
        else tok_num(x.get('numero_camara') or x.get('numero_senado'))
    return f"{c}-{t.replace('/', '-')}" if t else None


def fin(estado):
    return bool(re.search(r'archivad|retirad|acumulad', norm(estado)))


# ── las mismas palabras de tema que usa la página (mi-congreso-base.js) ──
TITLE_PREF = re.compile(r'^\s*por\s+(?:medio\s+de\s+)?(?:el\s+medio\s+de\s+)?(?:la|el|los|las)?\s*cual(?:es)?\s+se\s+', re.I)
STOP = set(('para sobre entre desde hasta cual cuales donde como contra mediante segun dictan otras '
            'disposiciones medio modifica modifican establece establecen crea crean ley leyes articulo '
            'articulos nacional republica colombia colombiano colombiana por del las los una uno que con '
            'sus mas adiciona adicionan reforma reforman regula regulan expide expiden fortalece promueve '
            'garantiza declara otorga autoriza incluye dicta normas').split())


def palabras_tema(titulo):
    s = TITLE_PREF.sub('', str(titulo or ''))
    out = []
    for w in norm(s).split():
        if len(w) > 4 and w not in STOP and w not in out:
            out.append(w)
    return out[:5]


# ─────────────────────────────────────────────────── diccionario de Caudal
class Diccionario:
    """Busca empresas y gremios por alias, palabra completa, con exclusiones.

    Solo por `alias` (no por el nombre de exhibición: «Protección» casaba con
    cualquier proyecto de protección de niños). Y un alias de UNA palabra exige
    la palabra con mayúscula inicial; si además es una palabra del español
    («claro», «porvenir», «compensar»), que no esté al arranque de la frase."""

    def __init__(self):
        self.por_primera = collections.defaultdict(list)
        for e in DIC.EMPRESAS:
            for a in set(e.get('alias') or []):
                toks = norm(a).split()
                if not toks or (len(toks) == 1 and len(toks[0]) < 3):
                    continue
                self.por_primera[toks[0]].append((toks, e))

    def buscar(self, texto):
        orig = re.findall(r"[\wÀ-ÿ]+|[.!?¿¡:;\"«»()]", str(texto or ''))
        toks, mayus = [], []
        prev = '.'
        for w in orig:
            if not re.match(r'[\wÀ-ÿ]', w):
                prev = w
                continue
            n = norm(w)
            if not n:
                continue
            toks.append(n)
            # mayúscula que no es la de arranque de frase o de titular
            mayus.append((w[0].isupper(), prev in '.!?¿¡:"«(' or len(toks) == 1))
            prev = w
        t = ' '.join(toks)
        hall = {}
        for i, w in enumerate(toks):
            for alias, e in self.por_primera.get(w, ()):
                if toks[i:i + len(alias)] != alias:
                    continue
                if len(alias) == 1:
                    cap, arranque = mayus[i]
                    if not cap or (alias[0] in COMUNES and arranque):
                        continue
                if any(x and x in t for x in (e.get('excluir') or [])):
                    continue
                hall[e['k']] = e
        return hall


# alias de una palabra que también son palabras del español: además de la
# mayúscula, no valen al arranque de una frase («Claro que…», «Porvenir incierto»)
COMUNES = {'claro', 'porvenir', 'compensar', 'pensemos', 'movilizamos', 'interactuar', 'crezcamos',
           'equiparo', 'jumbo', 'oikos', 'vikingos', 'laika', 'habi', 'sena', 'descont', 'challenger', 'processa'}


def tipo_de(e):
    n = norm(e['nombre'])
    if re.match(r'(universidad|fundacion universitaria|instituto tecnologico|escuela)', n):
        return 'academia'
    return e['tipo']



# ── limpieza de nombres que devuelve el modelo ──────────────────────────────
# colectivos vagos: no son un jugador al que se le pueda pedir cita
GENERICOS = {'gremios', 'empresarios', 'expertos', 'analistas', 'organizaciones', 'sectores', 'comunidades',
             'ciudadanos', 'colombianos', 'familias', 'padres', 'usuarios', 'empresas', 'industria', 'sector privado',
             'oposicion', 'congresistas', 'congreso', 'senado', 'camara', 'bancadas', 'partidos'}
# congresistas que la prensa nombra por su nombre público, no por el legal
CONGRESISTAS_ALIAS = {'amaranta hank'}
CANON = [
    (r'^(el )?(gobierno|ejecutivo)( nacional| de colombia| (del presidente )?(de )?abelardo.*| del presidente.*| de la espriella.*)?$', 'Gobierno nacional', 'entidad'),
    (r'^(el )?(presidente|mandatario)( de la republica)?( abelardo)?( de la espriella)?$|^abelardo de la espriella$', 'Presidente Abelardo de la Espriella', 'persona'),
    (r'^(el )?(ministerio del interior|mininterior|ministro del interior)$', 'Ministerio del Interior', 'entidad'),
    (r'^(el )?(ministerio de hacienda|minhacienda|ministro de hacienda)$', 'Ministerio de Hacienda', 'entidad'),
    (r'^(el )?(ministerio de educacion|mineducacion|ministra de educacion|ministro de educacion)$', 'Ministerio de Educación', 'entidad'),
    (r'^(el )?(ministerio de salud|minsalud|ministro de salud|ministra de salud)$', 'Ministerio de Salud', 'entidad'),
    (r'^(la )?defensoria( del pueblo)?$', 'Defensoría del Pueblo', 'entidad'),
    (r'^(la )?procuraduria( general de la nacion)?$', 'Procuraduría', 'entidad'),
    (r'^(la )?contraloria( general de la republica)?$', 'Contraloría', 'entidad'),
]


def canon_actor(nombre, tipo):
    """→ (nombre, tipo) canónicos, o None si hay que descartarlo."""
    n = norm(nombre)
    if not n or n in GENERICOS or n in CONGRESISTAS_ALIAS:
        return None
    for rx, nom, tp in CANON:
        if re.match(rx, n):
            return nom, tp
    return nombre.strip(), tipo

# ──────────────────────────────────────────────────────────────── DeepSeek
def api_key():
    k = os.environ.get('DEEPSEEK_API_KEY')
    if k:
        return k.strip()
    r = subprocess.run(['aws', 'lambda', 'get-function-configuration', '--function-name', 'caudal-analiza',
                        '--query', 'Environment.Variables.DEEPSEEK_API_KEY', '--output', 'text'],
                       capture_output=True, text=True, timeout=30)
    k = (r.stdout or '').strip()
    return k if k and k != 'None' else ''


SYSTEM = (
    'Eres analista de incidencia legislativa en Colombia. Te doy un proyecto de ley y titulares de '
    'prensa sobre su tema. Tu trabajo es identificar a los ACTORES EXTERNOS al Congreso que aparecen '
    'en esos titulares (gremios, empresas, entidades públicas, organizaciones sociales, academia, '
    'personas que no son congresistas) y, solo si el titular lo muestra, su postura frente a lo que '
    'el proyecto propone.\n'
    'Reglas duras:\n'
    '1. Solo actores cuyo nombre aparece LITERALMENTE en el titular que citas. No inventes ni deduzcas.\n'
    '2. NO incluyas congresistas, partidos ni bancadas: esos son fuerzas internas.\n'
    '3. postura: 1 = claramente a favor, 0.5 = a favor con reparos, -0.5 = en contra con matices, '
    '-1 = claramente en contra, null = el titular lo nombra pero no muestra postura. Hay postura SOLO si '
    'el titular muestra apoyo o rechazo a ESTE proyecto o a la medida concreta que propone. Quien toma '
    'por su cuenta una medida parecida, informa, investiga o es mencionado NO tiene postura: null. '
    'Quien radica o impulsa el proyecto sí está a favor. Ante la duda, null.\n'
    '6. Ignora los titulares de otros países (Perú, México, España, etc.): solo actores de Colombia.\n'
    '4. titular: el número del titular que respalda la postura (o donde aparece si es null).\n'
    '5. tipo: gremio | empresa | entidad | organizacion | academia | persona.\n'
    'Devuelve SOLO JSON: {"actores":[{"nombre":"…","tipo":"…","postura":1|0.5|-0.5|-1|null,"titular":N}]}. '
    'Lista vacía si no hay actores externos.')


def deepseek(key, user):
    for max_tok in (4000, 8000):
        body = json.dumps({'model': DEEPSEEK_MODEL, 'temperature': 0.1, 'max_tokens': max_tok,
                           'response_format': {'type': 'json_object'},
                           'messages': [{'role': 'system', 'content': SYSTEM},
                                        {'role': 'user', 'content': user}]}).encode()
        rq = urllib.request.Request(DEEPSEEK_URL, data=body, headers={
            'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
        with urllib.request.urlopen(rq, timeout=120) as r:
            d = json.loads(r.read())
        ch = d['choices'][0]
        raw = (ch['message'].get('content') or '').strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1].lstrip('json').strip()
        if ch.get('finish_reason') == 'length' and not raw.endswith('}'):
            continue
        return json.loads(raw or '{}')
    return {'actores': []}


# ─────────────────────────────────────────────────────────────── proyecto
def ficha(x):
    """Ficha de Caudal para el radicado: se resuelve por título y se confirma
    por número. El articulado solo vale si su título casa con el proyecto."""
    q = ' '.join(norm(x['titulo']).split()[:14])
    r = call({'action': 'buscar', 'query': q, 'limit': 10, 'anio_min': 2026}) or {}
    tS, tC = tok_num(x.get('numero_senado')), tok_num(x.get('numero_camara'))
    hit = next((h for h in r.get('resultados') or []
                if (tS and tok_num(h.get('ns')) == tS) or (tC and tok_num(h.get('nc')) == tC)), None)
    if not hit:
        return None, None
    f = call({'action': 'proyecto', 'id': hit['id'], 'tb': hit.get('tb', 'pdly')})
    if not f:
        return None, None
    art = f.get('articulado')
    if art:
        a, b, c = (norm(z)[:60] for z in (art.get('titulo'), f.get('titulo'), x.get('titulo')))
        if a != b and a != c:
            art = None
    return f, art


def prensa(x):
    P = palabras_tema(x['titulo'])
    if len(P) < 2:
        return P, []
    d = call({'action': 'medios', 'query': ' '.join(P[:4]), 'dias': DIAS}) or {}
    raiz = [w[:6] for w in P]
    res = []
    for r in d.get('resultados') or []:
        t = ' ' + norm(r.get('titulo')) + ' '
        if sum(1 for w in raiz if ' ' + w in t) >= 2:
            res.append({'titulo': r.get('titulo'), 'url': r.get('url'), 'medio': r.get('medio'),
                        'fecha': (r.get('fecha') or '')[:10]})
    return P, res[:30]


def actores_de(x, D, key, congresistas):
    f, art = ficha(x)
    P, tit = prensa(x)
    ap = (art or {}).get('aplica_a') or {}
    sectores = [s for s in (ap.get('sectores') or []) if s != 'multisectorial']
    blob_art = ' '.join([str(ap.get('sujetos') or ''), str(ap.get('actividades') or ''), str((art or {}).get('resumen') or '')]
                        + [str(o.get('sobre_quien') or '') + ' ' + str(o.get('obligacion') or '')
                           for o in (art or {}).get('obligaciones') or []])
    en_texto = D.buscar(blob_art + ' ' + x['titulo'])
    A = {}

    def es_medio(e):
        # un medio que publica la noticia no es un jugador, salvo que el
        # proyecto regule a los medios
        return e and e.get('sector') == 'medios' and 'medios' not in sectores

    def poner(nombre, tipo, sector=None, k=None):
        kk = k or norm(nombre)
        if kk not in A:
            A[kk] = {'n': nombre, 'tipo': tipo, 'sector': sector, 'postura': None, 'cita': None,
                     'peso': 0, 'cerca': .25, 'cerca_por': 'prensa', '_t': set()}
        return A[kk]

    # 1) nombrados en el texto
    for e in en_texto.values():
        if es_medio(e):
            continue
        a = poner(e['nombre'], tipo_de(e), e['sector'], e['k'])
        a['cerca'], a['cerca_por'] = 1.0, 'nombrado'
    # 2) gremios del sector que el texto regula
    gremios = [e for e in DIC.EMPRESAS if e['tipo'] == 'gremio' and e['sector'] in sectores[:2]]
    for e in gremios[:8]:
        a = poner(e['nombre'], 'gremio', e['sector'], e['k'])
        if a['cerca'] < .6:
            a['cerca'], a['cerca_por'] = .6, 'sector'
    # 3) en la conversación: diccionario sobre cada titular
    for i, t in enumerate(tit):
        for e in D.buscar(t['titulo']).values():
            if es_medio(e):
                continue
            a = poner(e['nombre'], tipo_de(e), e['sector'], e['k'])
            a['_t'].add(i)
            if e['sector'] in sectores and a['cerca'] < .6:
                a['cerca'], a['cerca_por'] = .6, 'sector'
    # 4) postura (y actores que el diccionario no conoce) con DeepSeek
    llm = []
    if tit and key:
        h = hashlib.sha1((PV + x['titulo'] + '|'.join(t['titulo'] or '' for t in tit)).encode()).hexdigest()[:20]
        cp = CACHE / f'{h}.json'
        if cp.exists():
            llm = json.loads(cp.read_text())
        else:
            user = (f"PROYECTO: {x['titulo']}\n"
                    + (f"QUÉ CAMBIA: {art.get('resumen')}\n" if art and art.get('resumen') else '')
                    + 'TITULARES:\n' + '\n'.join(f"{i}. {t['titulo']} ({t['medio']})" for i, t in enumerate(tit)))
            try:
                llm = deepseek(key, user).get('actores') or []
                CACHE.mkdir(parents=True, exist_ok=True)
                cp.write_text(json.dumps(llm, ensure_ascii=False))
            except Exception as err:                        # noqa: BLE001
                print('  ! deepseek', x['titulo'][:50], err, file=sys.stderr)
    for r in llm:
        try:
            i = int(r.get('titular'))
        except (TypeError, ValueError):
            continue
        if not (0 <= i < len(tit)) or not r.get('nombre'):
            continue
        nt = ' ' + norm(tit[i]['titulo']) + ' '
        sig = [w for w in norm(r['nombre']).split() if len(w) > 3]
        if not sig or not any(' ' + w in nt for w in sig):
            continue                                        # el nombre no está en ese titular
        if any(norm(r['nombre']) in c or c in norm(r['nombre']) for c in congresistas if len(c) > 8):
            continue                                        # es congresista: interno
        hit = D.buscar(r['nombre'])
        e = next(iter(hit.values()), None)
        if es_medio(e):
            continue
        if e:
            a = poner(e['nombre'], tipo_de(e), e['sector'], e['k'])
        else:
            c = canon_actor(r['nombre'], r.get('tipo') or 'organizacion')
            if not c:
                continue
            a = poner(c[0], c[1])
        a['_t'].add(i)
        p = r.get('postura')
        if p is not None and a['postura'] is None:
            try:
                a['postura'] = max(-1.0, min(1.0, float(p)))
                a['cita'] = tit[i]
            except (TypeError, ValueError):
                pass
    out = []
    for a in A.values():
        a['peso'] = len(a.pop('_t'))
        out.append(a)
    out.sort(key=lambda a: (-(a['postura'] is not None), -a['cerca'], -a['peso'], a['n']))
    return {
        'v': date.today().isoformat(), 'numero': (x.get('numero_senado') if x['_cam'] == 'Senado' else x.get('numero_camara')),
        'camara': x['_cam'], 'titulo': x['titulo'], 'sectores': sectores, 'sujetos': (ap.get('sujetos') or [])[:10],
        'articulado': bool(art), 'palabras': P, 'n_titulares': len(tit), 'dias': DIAS,
        'actores': out[:MAX_ACTORES],
        'nota': ('Actores tomados del texto del proyecto, del diccionario de gremios y empresas de Caudal y de '
                 f'los titulares sobre el tema de los últimos {DIAS} días.'
                 + ('' if art else ' Este proyecto todavía no tiene el articulado leído, así que nadie aparece como «nombrado en el texto».')),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--solo', help='un número de radicado, p. ej. 219/26 o 447/2026C')
    ap.add_argument('--max', type=int, default=0)
    ap.add_argument('--hilos', type=int, default=3)
    ap.add_argument('--subir', action='store_true')
    ap.add_argument('--saltar', action='store_true', help='no rehace los que ya tienen archivo')
    args = ap.parse_args()

    r = call({'action': 'radicados'}) or {}
    todos = [dict(x, _cam='Senado') for x in r.get('radicados') or []] + \
            [dict(x, _cam='Cámara') for x in r.get('radicados_camara') or []]
    if not todos:
        # sin esto, una falla de la API al arrancar terminaba en «0 proyectos»
        # y un índice reescrito como si todo estuviera bien
        sys.exit('! la API no devolvió radicados: no se arma nada')
    vivos = [x for x in todos if not fin(x.get('estado')) and tok_proyecto(x)]
    if args.solo:
        t = tok_num(args.solo)
        vivos = [x for x in vivos if t in (tok_num(x.get('numero_senado')), tok_num(x.get('numero_camara')))]
    if args.saltar:
        vivos = [x for x in vivos if not (OUT / f'{tok_proyecto(x)}.json').exists()]
    if args.max:
        vivos = vivos[:args.max]
    key = api_key()
    if not key:
        print('! sin DEEPSEEK_API_KEY: se arma sin postura', file=sys.stderr)
    D = Diccionario()
    congresistas = []
    if INTERNAS.exists():
        I = json.loads(INTERNAS.read_text())
        congresistas = [norm(m['n']) for c in ('senado', 'camara') for m in I[c]['miembros']]
    OUT.mkdir(parents=True, exist_ok=True)
    print(f'{len(vivos)} proyectos por armar · {len(D.por_primera)} alias en el diccionario')

    hechos, t0 = [], time.time()

    def uno(x):
        tok = tok_proyecto(x)
        d = actores_de(x, D, key, congresistas)
        (OUT / f'{tok}.json').write_text(json.dumps(d, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        return tok, d

    with cf.ThreadPoolExecutor(max_workers=args.hilos) as ex:
        for k, fut in enumerate(cf.as_completed([ex.submit(uno, x) for x in vivos]), 1):
            try:
                tok, d = fut.result()
            except Exception as err:                        # noqa: BLE001
                print('  ! fallo', err, file=sys.stderr)
                continue
            hechos.append(tok)
            conp = sum(1 for a in d['actores'] if a['postura'] is not None)
            if k % 10 == 0 or args.solo or len(vivos) < 15:
                print(f'  [{k}/{len(vivos)}] {tok} · {len(d["actores"])} actores · {conp} con postura · '
                      f'{d["n_titulares"]} titulares · {int(time.time() - t0)} s')

    idx = sorted(p.stem for p in OUT.glob('*-*-*.json'))
    (OUT / 'index.json').write_text(json.dumps({'v': date.today().isoformat(), 'n': len(idx), 'toks': idx}), encoding='utf-8')
    print(f'listo: {len(hechos)} proyectos en {int(time.time() - t0)} s · índice con {len(idx)}')
    if args.subir:
        subprocess.run(['aws', 's3', 'cp', str(OUT) + '/', S3_DIR, '--recursive', '--exclude', '_cache/*',
                        '--content-type', 'application/json', '--cache-control', 'public, max-age=3600'], check=True)
        print('subido a', S3_DIR)


if __name__ == '__main__':
    main()
