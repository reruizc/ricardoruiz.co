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

El articulado se lee directo de s3://caudal-legislativo/metadata/articulado.json
(la extracción con modelo local, 857 proyectos el 27-oct-2026), por número de
radicado y legislatura —nunca por el id de Cámara, que cambia a diario— y solo
se usa si su título casa con el del proyecto. Si el archivo no baja, se cae a
la ficha de la API.

Del articulado salen dos clases de actores con cerca = 1:
  · «obliga»   el texto le impone una obligación (campo sobre_quien), y se
               guarda QUÉ le exige (`exige`, hasta 3), que es lo que se le
               preguntaría a ese actor;
  · «nombrado» el texto dice que le aplica (aplica_a.sujetos) o el diccionario
               de empresas lo encuentra en el texto.
Los colectivos que no son una entidad («operadores de telecomunicaciones»,
«hogares beneficiarios») entran como tipo `grupo`: no tienen vocero único,
pero son a quienes toca el proyecto. Lo que el propio proyecto CREA (un comité
nuevo) no entra: todavía no existe para pronunciarse.

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
ORDENES_URL = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/legislativo/ordenes-vigentes.json'
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
    """«219/26» · «447/2026C» · «011 de 2025 Senado» → «219/26»."""
    m = re.search(r'0*(\d{1,4})\s*(?:/|\bde\b)\s*(?:20)?(\d{2})(?!\d)', str(s or ''), re.I)
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


RX_ENTIDAD = re.compile(r'^(el |la |los |las )?(gobierno|ministeri|minister|superintendenci|agencia|anla|corporaciones? autonom|'
                        r'car |alcald|gobernaci|departament|municipi|distrit|servicio geologico|ungrd|unidad |instituto |icbf|'
                        r'sena\b|direccion |comision de regulacion|crc\b|creg\b|cra\b|dian\b|banco de la republica|fondo |'
                        r'registradur|policia|fuerzas? (militares|publica)|ejercito|armada|fiscal|procuradur|contralor|defensor|'
                        r'consejo nacional|consejo superior|rama judicial|jueces|juzgados|tribunal|corte |entidades? (publicas|territoriales|del estado)|'
                        r'autoridades|empresas sociales del estado|ese\b|hospitales publicos|instituciones educativas oficiales|secretar|'
                        r'dane\b|dnp\b|departamento nacional|departamento administrativo|colombia compra|invima|ica\b|ideam|parques nacionales|'
                        r'servicio nacional|ministerio|presidencia|vicepresidencia|consejer|comisionad)')
# colectivos que no son nadie en particular: no se publican como actor
VAGOS = {'todas las personas', 'personas', 'la ciudadania', 'ciudadania', 'ciudadanos', 'la poblacion', 'poblacion',
         'toda la poblacion', 'los colombianos', 'habitantes', 'el estado', 'estado', 'estado colombiano',
         'terceros', 'sujetos obligados', 'destinatarios', 'beneficiarios', 'interesados', 'particulares', 'usuarios'}


VAGO_RX = re.compile(r'^(las? |los? )?(entidades (competentes|del orden|publicas y privadas|responsables)|personas naturales|'
                     r'toda persona|todas las (entidades|personas)|sector (productivo|publico y privado)|autoridades competentes|'
                     r'actores|demas entidades|instancias|organismos competentes)')
SIGLAS = {'sgc': 'Servicio Geológico Colombiano', 'ungrd': 'Unidad Nacional para la Gestión del Riesgo de Desastres',
          'mintic': 'Ministerio de Tecnologías de la Información y las Comunicaciones', 'anla': 'ANLA',
          'minvivienda': 'Ministerio de Vivienda', 'minagricultura': 'Ministerio de Agricultura y Desarrollo Rural',
          'minambiente': 'Ministerio de Ambiente y Desarrollo Sostenible', 'minhacienda': 'Ministerio de Hacienda',
          'minsalud': 'Ministerio de Salud', 'mineducacion': 'Ministerio de Educación', 'dnp': 'Departamento Nacional de Planeación',
          'dane': 'DANE', 'ica': 'Instituto Colombiano Agropecuario (ICA)', 'icbf': 'ICBF', 'sena': 'SENA', 'dian': 'DIAN',
          'crc': 'Comisión de Regulación de Comunicaciones', 'creg': 'CREG', 'sic': 'Superintendencia de Industria y Comercio'}
_PARTE_ENT = r'(?:el |la |los |las )?(?:Ministeri|Minist|Superintend|Agencia|Corporaci|Unidad|Instituto|Servicio|Gobierno|Departamento|Direcci|Comisi|Fondo|Banco|ANLA|UNGRD|SGC|Min[A-Z]|ICA\b|DNP|DANE|SENA|ICBF|DIAN|CRC|CREG|SIC\b)'


def partes_obligado(nombre):
    """«SGC, UNGRD y MinTIC» → tres entidades. Solo se parte si TODAS las
    piezas son entidades: «Departamentos de Atlántico, Bolívar y Cesar» o
    «Ministerio de Minas y Energía» quedan enteros."""
    s = re.sub(r'\s+', ' ', str(nombre or '')).strip()
    piezas = [p.strip(' .;:') for p in re.split(r',\s*|\s+y\s+(?=' + _PARTE_ENT + ')', s) if p.strip(' .;:')]
    if len(piezas) > 1 and all(re.match(_PARTE_ENT, p) for p in piezas):
        return piezas
    return [s]


def canon_obligado(nombre):
    n = norm(nombre)
    if n in SIGLAS:
        return SIGLAS[n]
    m = re.match(r'^(el |la )?ministr[oa] de (.+)$', n)
    if m:
        return 'Ministerio de ' + nombre.split(' de ', 1)[1]
    return nombre


def tipo_obligado(nombre):
    n = norm(nombre)
    if RX_ENTIDAD.match(n):
        return 'entidad'
    if re.match(r'^(universidad|instituciones de educacion superior)', n):
        return 'academia'
    return 'grupo'


def limpia_obligado(nombre):
    """«operadores de telecomunicaciones (TELCO)» → «Operadores de telecomunicaciones (TELCO)»;
    descarta los vacíos y los demasiado vagos para pedirles cita."""
    s = re.sub(r'\s+', ' ', str(nombre or '')).strip(' .;:,')
    if not s or len(s) < 3 or len(s) > 110 or norm(s) in VAGOS or VAGO_RX.match(norm(s)):
        return None
    s = canon_obligado(s)
    return s[0].upper() + s[1:]


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
ART_S3 = 's3://caudal-legislativo/metadata/articulado.json'
_ART = {'idx': None, 'v': None, 'n': 0}


def articulado_index():
    """(cámara, número) → articulado, de la extracción publicada en S3."""
    if _ART['idx'] is not None:
        return _ART['idx']
    _ART['idx'] = {}
    dst = CACHE / 'articulado.json'
    CACHE.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(['aws', 's3', 'cp', ART_S3, str(dst), '--quiet'], check=True, timeout=180)
        d = json.loads(dst.read_text())
    except Exception as err:                                # noqa: BLE001
        print('  ! no bajó el articulado de S3, se usa la API:', err, file=sys.stderr)
        return _ART['idx']
    _ART['v'], _ART['n'] = d.get('v'), d.get('n')
    for a in (d.get('por_proyecto') or {}).values():
        for cam, num in (('S', a.get('numero_senado')), ('C', a.get('numero_camara'))):
            t = tok_num(num)
            if t:
                _ART['idx'].setdefault((cam, t), []).append(a)
    return _ART['idx']


def _palabras(z):
    return {w for w in norm(z).split() if len(w) > 4 and w not in STOP}


def _titulo_casa(a, *titulos):
    """Mismo arranque del título, o (para los títulos que salen del PDF del
    orden del día, que no vienen idénticos) ≥ 60 % de palabras en común."""
    ta = a.get('titulo') or a.get('titulo_leido')
    t = norm(ta)[:60]
    if not t:
        return False
    for z in titulos:
        if not z:
            continue
        if t == norm(z)[:60]:
            return True
        A, B = _palabras(ta), _palabras(z)
        if A and B and len(A & B) / min(len(A), len(B)) >= .6:
            return True
    return False


def articulado_de(x):
    """El articulado del radicado, por número, con su título verificado (el
    número se repite entre legislaturas y entre cámaras). None si no hay o si
    ningún título casa: antes de prestar el texto de otro proyecto, nada."""
    idx = articulado_index()
    for cam, num in (('S', x.get('numero_senado')), ('C', x.get('numero_camara'))):
        t = tok_num(num)
        for a in (idx.get((cam, t)) or []) if t else []:
            if _titulo_casa(a, x.get('titulo')):
                return a
    return None


def ficha(x):
    """Ficha de Caudal para el radicado: se resuelve por título y se confirma
    por número. El articulado solo vale si su título casa con el proyecto.
    Respaldo de articulado_de() cuando el archivo de S3 no está."""
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


# verbos y sustantivos de trámite que abren muchos títulos y no dicen el tema:
# con ellos la consulta «reconoce derecho eleccion aplicacion» no trae nada.
# Solo para la SEGUNDA consulta: la primera sigue siendo la de la página.
GENERICAS_TEMA = set(('reconoce reconocen derecho derechos marco general politica estado fortalecer focalizacion '
                      'eficiencia sostenibilidad financiera constituye constituyen establecen competencias '
                      'organizacion funcionamiento implementa implementar medidas mecanismos sistema programa '
                      'creacion nueva nuevo integral publica publico nacionales especial especiales '
                      'aplicacion eleccion otorgado otorgada fuentes financiacion modificacion adicion '
                      'parcialmente promover impulsar regimen').split())


# palabras que casan con media prensa: dos de ellas juntas («región Caribe»)
# no prueban que el titular hable del proyecto (salían reinados y tarifas).
COMUNES_TEMA = set(('region caribe pacifico andina orinoquia amazonia departamento departamentos municipio '
                    'municipios ciudad ciudades servicio servicios sistema salud educacion trabajo social sociales '
                    'gobierno personas familias desarrollo nacional fondo').split())


def _consulta(P, minimo=2):
    d = call({'action': 'medios', 'query': ' '.join(P[:4]), 'dias': DIAS}) or {}
    raiz = [w[:6] for w in P]
    comun = {w[:6] for w in COMUNES_TEMA}
    res = []
    for r in d.get('resultados') or []:
        t = ' ' + norm(r.get('titulo')) + ' '
        hit = [w for w in raiz if ' ' + w in t]
        if len(hit) >= min(minimo, len(raiz)) and (len(raiz) == 1 or any(w not in comun for w in hit)):
            res.append({'titulo': r.get('titulo'), 'url': r.get('url'), 'medio': r.get('medio'),
                        'fecha': (r.get('fecha') or '')[:10]})
    return res


def palabras_fuertes(titulo):
    """Las palabras del título que nombran el TEMA, sin las de trámite."""
    s = TITLE_PREF.sub('', str(titulo or ''))
    Q = []
    for w in norm(s).split():
        if len(w) > 4 and w not in STOP and w not in GENERICAS_TEMA and w not in Q:
            Q.append(w)
    return Q[:5]


def prensa(x):
    """Titulares sobre el tema. Se busca con las palabras FUERTES del título
    («marco general política estado bioeconomía» traía notas de Marco Rubio);
    si queda una sola y es larga (≥ 8 letras, «bioeconomia»), basta con ella.
    Si no hay palabras fuertes, se cae a las de la página."""
    Q = palabras_fuertes(x['titulo'])
    P = palabras_tema(x['titulo'])
    res, usadas = [], []
    if len(Q) >= 2:
        res, usadas = _consulta(Q), Q
    elif len(Q) == 1 and len(Q[0]) >= 8:
        res, usadas = _consulta(Q, minimo=1), Q
    # la consulta de la página, con el mismo filtro, suma lo que Google News
    # devuelve distinto para otra combinación de palabras
    if len(P) >= 2 and P[:4] != usadas[:4] and (len(usadas) >= 2 or not usadas):
        vistos = {r['url'] for r in res}
        res += [r for r in _consulta(P) if r['url'] not in vistos]
        usadas = usadas or P
    res.sort(key=lambda r: r.get('fecha') or '', reverse=True)
    return usadas, res[:30]


def actores_de(x, D, key, congresistas):
    art = articulado_de(x)
    if art is None and not _ART['n']:
        _, art = ficha(x)                                   # sin el archivo de S3
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

    # 0) lo que el texto le exige a cada quien: el obligado entra con cerca 1
    #    y con la lista de lo que se le exige. Lo que el proyecto CREA no entra.
    creado = norm(' '.join([str((art or {}).get('resumen') or ''), x['titulo']]))

    def lo_crea(n):
        nn = norm(n)
        return bool(nn) and re.search(r'\b(crea(n|r)?|constituye(n)?|conforma(n)?|instituye(n)?) (el |la |los |las |un |una )?' + re.escape(nn[:40]), creado) is not None

    def del_texto(crudo):
        out = []
        for pieza in partes_obligado(crudo):
            quien = limpia_obligado(pieza)
            if not quien or lo_crea(quien):
                continue
            e = next(iter(D.buscar(quien).values()), None)
            if e and not es_medio(e):
                out.append(poner(e['nombre'], tipo_de(e), e['sector'], e['k']))
                continue
            c = canon_actor(quien, tipo_obligado(quien))
            if c:
                tp = c[1] if c[1] in ('entidad', 'persona') else tipo_obligado(c[0])
                out.append(poner(c[0], tp))
        return out

    for o in (art or {}).get('obligaciones') or []:
        ob = re.sub(r'\s+', ' ', str(o.get('obligacion') or '')).strip()
        for a in del_texto(o.get('sobre_quien')):
            a['cerca'], a['cerca_por'] = 1.0, 'obliga'
            ex = a.setdefault('exige', [])
            if ob and ob not in ex and len(ex) < 3:
                ex.append(ob[:220] + ('' if not o.get('plazo') else f" (plazo: {str(o['plazo'])[:60]})"))
    # 1) nombrados en el texto: los sujetos a los que dice aplicar
    for suj in (ap.get('sujetos') or [])[:12]:
        for a in del_texto(suj):
            if a['cerca_por'] != 'obliga':
                a['cerca'], a['cerca_por'] = 1.0, 'nombrado'
    #    y las empresas o gremios del diccionario que aparecen en el texto
    for e in en_texto.values():
        if es_medio(e):
            continue
        a = poner(e['nombre'], tipo_de(e), e['sector'], e['k'])
        if a['cerca_por'] != 'obliga':
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
    out.sort(key=lambda a: (-(a['postura'] is not None), -a['cerca'], -(a['cerca_por'] == 'obliga'), -a['peso'], a['n']))
    base = (art or {}).get('base')
    solo_titulo = base == 'titulo'
    return {
        'v': date.today().isoformat(), 'numero': (x.get('numero_senado') if x['_cam'] == 'Senado' else x.get('numero_camara')),
        'camara': x['_cam'], 'titulo': x['titulo'], 'sectores': sectores, 'sujetos': (ap.get('sujetos') or [])[:10],
        'articulado': bool(art), 'art_base': base, 'art_confianza': (art or {}).get('confianza'),
        'art_modelo': (art or {}).get('modelo'), 'art_v': _ART['v'],
        'n_obligados': sum(1 for a in out if a['cerca_por'] == 'obliga'),
        'palabras': P, 'n_titulares': len(tit), 'dias': DIAS,
        'actores': out[:MAX_ACTORES],
        'nota': ('Actores tomados del texto del proyecto (a quién le impone obligaciones y a quién dice aplicar), '
                 'del diccionario de gremios y empresas de Caudal y de '
                 f'los titulares sobre el tema de los últimos {DIAS} días.'
                 + (' Este proyecto todavía no tiene el articulado leído, así que nadie aparece como «nombrado en el texto».' if not art
                    else ' Del texto solo leímos el título, así que la lista de obligados puede estar incompleta.' if solo_titulo
                    else ' Lo que el texto exige a cada actor lo resume un modelo de lenguaje local sobre el radicado: ábrelo antes de citarlo.')),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--solo', help='un número de radicado, p. ej. 219/26 o 447/2026C')
    ap.add_argument('--max', type=int, default=0)
    ap.add_argument('--hilos', type=int, default=3)
    ap.add_argument('--subir', action='store_true')
    ap.add_argument('--saltar', action='store_true', help='no rehace los que ya tienen archivo')
    ap.add_argument('--hoy', action='store_true', help='solo los proyectos del orden del día de hoy (ordenes-vigentes.json)')
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
    if args.hoy:
        hoy = time.strftime('%Y-%m-%d', time.gmtime(time.time() - 5 * 3600))   # Bogotá
        with urllib.request.urlopen(urllib.request.Request(ORDENES_URL, headers={'User-Agent': 'mi-congreso-fuerzas'}), timeout=60) as r:
            raw = r.read()
        if raw[:2] == b'\x1f\x8b':
            import gzip
            raw = gzip.decompress(raw)
        O = json.loads(raw).get('ordenes') or []
        pedidos = {}
        for o in O:
            if not (o.get('fecha') <= hoy <= (o.get('fecha_fin') or o.get('fecha'))):
                continue
            cam = 'S' if re.search(r'senado', o.get('corporacion') or '', re.I) else 'C'
            for pr in o.get('proyectos') or []:
                m = re.search(r'(c[aá]mara|senado)\b', str(pr.get('numero') or ''), re.I)
                c = ('S' if m.group(1).lower() == 'senado' else 'C') if m else cam
                t = tok_num(pr.get('numero'))
                if t and pr.get('titulo'):
                    pedidos.setdefault((c, t), pr)
        print(f'orden del día de {hoy}: {len(pedidos)} proyectos citados')

        def clave(x):
            return ('S', tok_num(x.get('numero_senado'))) if x['_cam'] == 'Senado' else ('C', tok_num(x.get('numero_camara')))
        vivos = [x for x in vivos if clave(x) in pedidos]
        # los de una legislatura anterior que siguen en trámite no están en
        # `radicados`: se arman con lo que trae el orden del día
        ya = {clave(x) for x in vivos}
        for (c, t), pr in pedidos.items():
            if (c, t) in ya:
                continue
            num = f"{int(t.split('/')[0])}/{t.split('/')[1]}"
            vivos.append({'titulo': pr.get('titulo'), 'estado': '', '_cam': 'Senado' if c == 'S' else 'Cámara',
                          'numero_senado': num if c == 'S' else None, 'numero_camara': num if c == 'C' else None,
                          '_del_orden': True})
        print(f'  {len(ya)} de la legislatura viva · {len(vivos) - len(ya)} de legislaturas anteriores')
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
