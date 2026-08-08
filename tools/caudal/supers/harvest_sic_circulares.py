#!/usr/bin/env python3
"""
Caudal · pilar Regulatorio — CIRCULARES y RESOLUCIONES DE CARÁCTER GENERAL de la SIC
(vía 2: view Drupal con filtros expuestos de la sede electrónica).

POR QUÉ ESTE HARVESTER. De la SIC el pilar solo tenía las 76 SANCIONES que
`harvest_comunicados.py` saca de la sala de prensa. Una sanción cuenta lo que
OTRO hizo mal; una circular externa cambia lo que la empresa vigilada tiene que
hacer. Para un cliente regulado (el caso que lo motivó: dos de las siete normas
colombianas que le aplican a Binance son circulares externas de la SIC, la 001
del 18-sep-2025 y la 002 del 07-oct-2025) la segunda vale más.

LA FUENTE. `sedeelectronica.sic.gov.co/transparencia/normativa/busqueda-de-normas/entidad`
es el registro de normativa que la SIC publica por Ley 1712. Es un view Drupal
server-rendered (sin JS, sin auth, sin token) con TRES filtros expuestos que dan
exactamente los ejes que hacen falta:

  field_clasificacion2_target_id   tipo de norma   179=Circulares · 177=Resoluciones
  field_clasificacion5_target_id   DELEGATURA      398=Protección al Consumidor
                                                   399=Protección de Datos Personales
                                                   397=Protección a la Competencia (+5 más)
  field_tipo_acto_target_id        6704=Carácter General · 6705=Particular · 6706=No aplica

El tercero es el hallazgo que hace viable el encargo: **la SIC misma marca qué
actos son de carácter general**, así que "resoluciones de carácter general" no
hay que inferirlo — se pide. Recorta resoluciones de ~2.020 a ~240 y deja fuera
los nombramientos y demás actos particulares, que no le cambian la vida a nadie.

VÍAS DESCARTADAS (medidas, no supuestas):

  Vía 1 · Socrata. La SIC publica 19 datasets en datos.gov.co y NINGUNO es de
    normativa (son patentes, RNBD, integraciones, demandas…). El único índice
    normativo es `fiev-nid6` (SUIN-Juriscol, de MinJusticia): tiene 652 normas
    de la SIC (221 CIRCULAR EXTERNA + 428 RESOLUCION) y llega a 2026, así que
    CONFIRMA que las dos circulares de validación existen — pero solo trae
    tipo/número/año/vigencia: **sin título, sin fecha, sin descripción y sin
    PDF**. Es un índice, no la norma; no sirve para decirle a un cliente qué
    tiene que hacer. Queda registrado como control cruzado de completitud.
    (Hallazgo colateral fuera de este encargo: `73dx-n59j` "Sanciones impuestas
    en firme por la SIC" SÍ es un registro estructurado de sanciones y podría
    superar a las 76 de comunicados. No lo toco — es otra fuente y otro dueño.)

  Vía 2a · www.sic.gov.co/repositorio-de-normatividad. El repositorio viejo, que
    a primera vista es ideal (tabla con tema, título, descripción, fecha y PDF).
    **Está congelado**: sus circulares se detienen en dic-2022 y ningún tipo de
    norma pasa de feb-2024 (medido barriendo los 14 valores del filtro). Usarlo
    habría dado una cosecha que se ve completa y no tiene NADA de 2023-2026 —
    ni las dos circulares del encargo. Se conserva la medición aquí para que
    nadie vuelva a intentarlo.

  Vía 3 · PDF+LLM. Innecesaria: la descripción de cada acto ya viene en texto
    en el propio nodo. El PDF se referencia (`url_pdf`) para el que quiera el
    articulado, pero no hay que pagar extracción para saber de qué trata.

TRAMPAS MEDIDAS (no las quites sin volver a medir):

  ① "Normativa aplicable" NO significa "de otra entidad". El view mezcla en el
     mismo tipo las circulares propias con las AJENAS que le aplican a la SIC
     (MinTrabajo, MinHacienda, CRC, directivas presidenciales), rotulándolas
     "Circulares, Normativa aplicable". Pero de esas 24, **9 son circulares
     PROPIAS de la SIC de 2023 y 2024** — justo los años que el repositorio
     viejo no tiene. Filtrar por la etiqueta a secas las perdería. Por eso el
     emisor se decide en dos pasos: la etiqueta limpia se acepta como propia, y
     dentro del bucket "Normativa aplicable" se exige que el acto se identifique
     como de la SIC (`_SIC_RE`). Lo ajeno se cuenta y se reporta, no se emite:
     un acto de MinTrabajo publicado bajo `fuente=sic` mentiría.

  ② La fecha del nodo miente en el bucket "Normativa aplicable". La Circular
     Externa 1 **de 2023** trae `fecha-generacion` = 19-ago-**2025**: es la fecha
     en que la cargaron a la sede, no la de expedición. Por eso `anio` sale del
     TÍTULO cuando el título lo dice (que es la fuente autoritativa del número y
     el año) y la fecha del nodo se marca `fecha_confiable=False` cuando las dos
     se contradicen. No se inventa una fecha: se declara que no es de fiar.

  ③ 195 de 245 circulares NO traen año en el título ("Circular 06", "Circular
     01"), así que el título tampoco basta solo — por eso se cosechan las dos y
     se cruzan, en vez de elegir una.

  ④ `items_per_page` NO funciona (el view ignora el parámetro y devuelve su
     página fija) → hay que paginar. Y la paginación se corta por página vacía o
     repetida, no por el número del pager: el pager solo muestra una ventana.

  ⑤ El listado trae título, tipo y descripción pero NO la fecha ni el PDF; esos
     viven en el nodo. Las clasificaciones (delegatura y carácter) no están en
     NINGUNO de los dos como texto — se obtienen corriendo el listado una vez por
     faceta y anotando en qué corridas cae cada nodo. Sale más barato que abrir
     cada nodo a adivinar.

DEDUP. Las 76 sanciones viven en `www.sic.gov.co/{slider,noticias}/…`; estas
viven en `sedeelectronica.sic.gov.co/transparencia/normativa/…`. No se solapan,
pero no se asume: `fetch` cruza contra `raw/sic.json` por URL y por título
normalizado y aborta el volcado si encuentra colisión.

SALIDA. `raw/sic-circulares.json`, con `tipo_acto` POR FILA (circular ·
resolucion), listo para `harvest_supers.py normalize`. La entrada propuesta para
fuentes.json va en `_pendiente-sic.json` (este harvester NO toca fuentes.json).

Uso:
  python3 tools/caudal/supers/harvest_sic_circulares.py probe    # mapea el view, no escribe
  python3 tools/caudal/supers/harvest_sic_circulares.py fetch    # cosecha (resumible)
  python3 tools/caudal/supers/harvest_sic_circulares.py fetch --reparsear   # sin red
  python3 tools/caudal/supers/harvest_sic_circulares.py fetch --solo-circulares
  python3 tools/caudal/supers/harvest_sic_circulares.py test     # valida CE 001/002 de 2025 + dedup
Luego (los corre su dueño, no este script):
  python3 tools/caudal/supers/harvest_supers.py normalize
  python3 tools/caudal/supers/build_s3.py
"""
import argparse
import html
import json
import re
import subprocess
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RAW = REPO / 'Bases de datos' / 'leyes-senado' / 'supers' / 'raw'
SLUG = 'sic-circulares'
OUT_JSON = RAW / f'{SLUG}.json'
CACHE = RAW / f'{SLUG}-nodos.json'      # cache de nodos ya abiertos (resumible)

BASE = 'https://sedeelectronica.sic.gov.co'
VIEW = f'{BASE}/transparencia/normativa/busqueda-de-normas/entidad'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')

# --- taxonomía del view (leída de los <select> expuestos, jul/ago-2026) -------
TIPO_NORMA = {179: 'Circulares', 177: 'Resoluciones'}
CARACTER = {6704: 'Carácter General', 6705: 'Carácter Particular', 6706: 'No aplica'}
DELEGATURA = {
    395: 'Asuntos Jurisdiccionales',
    396: 'Propiedad Industrial',
    397: 'Protección a la Competencia',
    398: 'Protección al Consumidor',
    399: 'Protección de Datos Personales',
    400: 'Reglamentos Técnicos y Metrología Legal',
    401: 'Oficina Servicios al Consumidor y de Apoyo Empresarial',
    406: 'Despacho de la Superintendencia',
}
CARACTER_GENERAL = 6704

# Las tres delegaturas que pidió el encargo (las que le cambian obligaciones a
# una empresa vigilada). Las otras cinco se cosechan igual —no cuesta nada y son
# el mismo acto— pero estas van marcadas para poder priorizarlas río abajo.
DELEGATURAS_CLAVE = {397, 398, 399}

MAX_PAGES = 60          # cota dura: el view más grande medido tiene ~14 páginas
PAUSA = 0.35            # cortesía con el portal


def _curl(url, timeout=60):
    cmd = ['/usr/bin/curl', '-s', '-A', UA, '--max-time', str(timeout), '-L', url]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout + 15)
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0:
        return None
    return r.stdout.decode('utf-8', errors='replace')


def _txt(s):
    """HTML → texto plano colapsado."""
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s or ''))).strip()


def _norm(s):
    """Clave de comparación: sin tildes, sin puntuación, minúsculas."""
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


# ------------------------------------------------------------------ listado

_ROW_RE = re.compile(r'<div class="normas--row.*?</div></span>', re.S)
_TIPO_RE = re.compile(r'Tipo de norma:\s*<strong>(.*?)</strong>', re.S)
_LINK_RE = re.compile(r'<h2[^>]*>\s*<a href="([^"]+)"[^>]*>(.*?)</a>', re.S)
_DESC_RE = re.compile(r'<div class="col-md-12">(.*?)</div>', re.S)


def listar(params, max_pages=MAX_PAGES):
    """Pagina un listado del view y devuelve {path: fila}.

    Corta por página vacía o sin paths nuevos — el pager solo muestra una
    ventana de números, así que su máximo no es el total (trampa ④).
    """
    qs = '&'.join(f'{k}={v}' for k, v in params.items())
    out, page = {}, 0
    while page < max_pages:
        url = f'{VIEW}?{qs}&page={page}' if qs else f'{VIEW}?page={page}'
        t = _curl(url)
        if t is None:
            print(f'    ! sin respuesta en page={page} ({qs})', file=sys.stderr)
            break
        nuevos = 0
        for blk in _ROW_RE.findall(t):
            a = _LINK_RE.search(blk)
            if not a:
                continue
            path = html.unescape(a.group(1)).strip()
            if path in out:
                continue
            tipo = _TIPO_RE.search(blk)
            desc = _DESC_RE.search(blk)
            out[path] = {
                'path': path,
                'titulo': _txt(a.group(2)),
                'tipo_norma': _txt(tipo.group(1)) if tipo else '',
                'desc_listado': _txt(desc.group(1)) if desc else '',
            }
            nuevos += 1
        if nuevos == 0:
            break
        page += 1
        time.sleep(PAUSA)
    return out


# -------------------------------------------------------------------- nodo

# El `[^>]*>` NO es decorativo: sin él la captura arranca a mitad del tag y se
# lleva el resto de sus atributos, que _txt no puede limpiar porque ya no están
# dentro de <…>. Costaba 685 de 719 cuerpos empezando con
# 'field--type-text-long field--label-hidden field__item">'.
_FLD_RE = {
    'fecha_expedicion': re.compile(r'field--name-field-fecha-generacion[^>]*>(.*?)</div>\s*</div>', re.S),
    'fecha_publicacion': re.compile(r'field--name-field-fecha-publicacion[^>]*>(.*?)</div>\s*</div>', re.S),
    'cuerpo': re.compile(r'field--name-field-body2[^>]*>(.*?)</div>\s*</div>', re.S),
}
# la etiqueta del campo viaja dentro del div y no aporta nada al texto
_LABEL_RE = re.compile(r'^\s*(?:Fecha\s+(?:Expedici[oó]n|publicaci[oó]n)|Cuerpo)\s*', re.I)
_MES = {'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04', 'may': '05', 'jun': '06',
        'jul': '07', 'ago': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12'}
_FECHA_TXT_RE = re.compile(r'([A-Za-zÁÉÍÓÚáéíóú]{3})\w*\s+(\d{1,2}),?\s+(\d{4})')
_PDF_RE = re.compile(r'href="([^"]+\.pdf[^"]*)"', re.I)
# el pie del sitio cuelga estos PDFs en TODAS las páginas: no son el acto
_PDF_CHROME = ('rminos y condiciones', 'terminos%20y%20condiciones', 'infografia')


def _fecha_iso(seg):
    """'Fecha Expedición Sep 18, 2025' → '2025-09-18'."""
    m = _FECHA_TXT_RE.search(_txt(seg))
    if not m:
        return ''
    mes = _MES.get(_norm(m.group(1))[:3])
    return f'{m.group(3)}-{mes}-{int(m.group(2)):02d}' if mes else ''


def parse_nodo(t):
    """Extrae del HTML del nodo: fechas, cuerpo y PDF del acto."""
    rec = {'fecha_expedicion': '', 'fecha_publicacion': '', 'cuerpo': '', 'url_pdf': ''}
    for k, rx in _FLD_RE.items():
        m = rx.search(t)
        if not m:
            continue
        if k == 'cuerpo':
            rec[k] = _LABEL_RE.sub('', _txt(m.group(1)))
        else:
            rec[k] = _fecha_iso(m.group(1))
    for h in _PDF_RE.findall(t):
        h = html.unescape(h)
        if any(c in h.lower() for c in _PDF_CHROME):
            continue
        rec['url_pdf'] = h if h.startswith('http') else BASE + h
        break
    return rec


# El cache guarda el HTML CRUDO, no el resultado del parseo: si mañana hay que
# corregir una regex (ya pasó dos veces en este archivo), re-parsear las 742
# fichas debe ser gratis y sin red — `fetch --reparsear`. Guardar solo el
# parseado obliga a re-descargar el portal entero por un cambio de una línea.
def nodo(path):
    t = _curl(BASE + path)
    return None if t is None else t


# ------------------------------------------------------------ clasificación

# subtipo, en orden de especificidad (el genérico va al final)
_SUBTIPOS = [
    (re.compile(r'circular\s+externa\s+conjunta', re.I), 'Circular Externa Conjunta'),
    (re.compile(r'circular\s+conjunta', re.I), 'Circular Conjunta'),
    (re.compile(r'circular\s+externa', re.I), 'Circular Externa'),
    (re.compile(r'circular\s+interna', re.I), 'Circular Interna'),
    (re.compile(r'circular\s+[uú]nica', re.I), 'Circular Única'),
    (re.compile(r'circular', re.I), 'Circular'),
]
# el acto se identifica como propio de la SIC
_SIC_RE = re.compile(r'superintendencia\s+de\s+industria|superindustria|\bsic\b', re.I)
_ANIO_RE = re.compile(r'\b(20\d{2}|19\d{2})\b')
_ANIO_MIN = 1990
_ANIO_MAX = time.localtime().tm_year + 1
# El "No." es OPCIONAL: exigirlo dejaba sin número a 616 de 719 actos ("Resolución
# 26806 de 2026", "Circular Externa 001 del 18 de septiembre de 2025"), incluida
# la circular de validación. Se toma el primer número que siga a la palabra clave
# dentro de una ventana corta. 'cirular' no es un typo mío: está así en la fuente.
_NUM_RE = re.compile(
    r'(?:circular|cirular|resoluci[oó]n)[^\d]{0,45}?(\d{1,6})', re.I)


def subtipo_de(titulo, cuerpo, es_circular):
    """Externa / interna / conjunta / única, del título y si no del cuerpo.

    Muchas circulares viejas se titulan solo "Circular 06" y su PDF tampoco lo
    dice (medido: 0 de 196 lo declaran en el nombre del archivo), así que el
    cuerpo es el último recurso. Si ninguno lo declara se queda en 'Circular' a
    secas — no se asume que sea externa. Contexto para leer ese residuo: en toda
    la cosecha hay UNA sola circular explícitamente interna, así que casi todo
    lo que el registro publica es de destinatario externo; aun así, afirmarlo
    acto por acto sería inventar.
    """
    if not es_circular:
        return 'Resolución de carácter general'
    for rx, lab in _SUBTIPOS:
        if rx.search(titulo or ''):
            return lab
    for rx, lab in _SUBTIPOS[:-1]:          # en el cuerpo no vale el genérico
        if rx.search(cuerpo or ''):
            return lab
    return 'Circular'


def numero_anio(titulo):
    """Número y año TAL COMO LOS DECLARA EL TÍTULO (autoritativo, ver trampa ②).

    El año es el PRIMERO del título, no el último: muchos actos citan en su
    propio título la norma que derogan o modifican ("Circular Externa 4 de 2024
    'Derogar la Circular Externa No. 004 de 13 de diciembre de 2021'") y quedarse
    con el último los fecharía con el año de la norma derogada.
    """
    t = titulo or ''
    num = _NUM_RE.search(t)
    # El número del acto se ve igual que un año ("Resolución 2064 de 26 de enero
    # del 2022" → 2064 NO es el año, es el número; "Resolución 2090 de 2019"
    # igual). Se excluye el tramo que ya se leyó como número y se acotan los
    # años a un rango sano, en vez de creerle al primer 20xx del título.
    ini, fin = num.span(1) if num else (-1, -1)
    anio = ''
    for m in _ANIO_RE.finditer(t):
        if m.start() == ini and m.end() == fin:
            continue
        if _ANIO_MIN <= int(m.group(1)) <= _ANIO_MAX:
            anio = m.group(1)
            break
    return (num.group(1) if num else ''), anio


def emisor_de(tipo_norma, titulo, desc):
    """'sic' | 'otra_entidad'  (ver trampa ①: la etiqueta sola no alcanza)."""
    if 'normativa aplicable' not in _norm(tipo_norma):
        return 'sic'                      # etiqueta limpia = clasificación propia de la SIC
    return 'sic' if _SIC_RE.search(f'{titulo} {desc}') else 'otra_entidad'


# El destinatario de una circular no es un sancionado: es el universo vigilado
# al que le cambian las obligaciones, y el cuerpo suele encabezarlo con "Para …".
# La frase puede ser larga ("Para Sujetos vigilados por la Superintendencia … que
# realicen tratamiento de datos personales …"), así que se corta por palabra en
# vez de exigir un punto cerca: pedir el punto dentro de 90 caracteres dejaba
# fuera justo a las circulares que más lo declaran.
_PARA_RE = re.compile(r'\bpara\s*:?\s+((?:los?\s+|las?\s+)?[^.;]{4,200})', re.I)
_DEST_MAX = 90


def destinatario_de(cuerpo):
    m = _PARA_RE.search(cuerpo or '')
    if not m:
        return None
    d = re.sub(r'\s+', ' ', m.group(1)).strip(' ,:;')
    if len(d) > _DEST_MAX:                       # corta en la última palabra entera
        d = d[:_DEST_MAX].rsplit(' ', 1)[0].strip(' ,:;')
    return d if len(d) >= 4 else None


# ------------------------------------------------------------------- fetch

def _cargar_cache():
    if not CACHE.exists():
        return {}
    try:
        c = json.loads(CACHE.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        print('  ! cache corrupto, se re-cosecha', file=sys.stderr)
        return {}
    # el cache guardó parseado hasta ago-2026 y ahora guarda HTML crudo; el
    # formato viejo no se puede re-parsear, así que se descarta en vez de
    # mezclarlo en silencio
    if c and not isinstance(next(iter(c.values())), str):
        print('  ! cache en formato viejo (parseado): se vuelve a bajar', file=sys.stderr)
        return {}
    return c


def _guardar_cache(c):
    tmp = CACHE.with_suffix('.tmp')
    tmp.write_text(json.dumps(c, ensure_ascii=False), encoding='utf-8')
    tmp.replace(CACHE)                    # atómico: no deja cache a medias


def _facetas(tipo_id, extra=None):
    """Corre el listado una vez por faceta y devuelve (carácter, delegatura, pin).

    El nodo no publica su delegatura ni su carácter en ninguna parte del HTML;
    lo único que lo sabe es el propio view. Preguntárselo por faceta cuesta
    ~10 listados y evita abrir 500 nodos a adivinar (trampa ⑤).

    OJO con el orden de las claves: si el objetivo YA fija el carácter (las
    resoluciones se piden solo de carácter general), preguntar por faceta es
    a la vez redundante y peligroso — un `update(extra)` detrás pisaba la clave
    de la faceta y las tres corridas devolvían el mismo conjunto, dejando 467
    resoluciones rotuladas "No aplica" siendo todas de carácter general. Cuando
    viene fijado se devuelve como `pin` y no se pregunta.
    """
    extra = dict(extra or {})
    pin = CARACTER.get(extra.get('field_tipo_acto_target_id'))
    car, dele = {}, {}
    if pin:
        print(f'    carácter: fijado por el filtro del objetivo → {pin}')
    else:
        for cid, lab in CARACTER.items():
            p = dict(extra)
            p['field_clasificacion2_target_id'] = tipo_id
            p['field_tipo_acto_target_id'] = cid      # la faceta manda sobre extra
            got = listar(p)
            for path in got:
                car[path] = lab
            print(f'    carácter {lab:22s} {len(got):4d}')
    for did, lab in DELEGATURA.items():
        p = dict(extra)
        p['field_clasificacion2_target_id'] = tipo_id
        p['field_clasificacion5_target_id'] = did     # la faceta manda sobre extra
        got = listar(p)
        for path in got:
            dele[path] = lab
        if got:
            print(f'    delegatura {lab[:34]:36s} {len(got):4d}')
    return car, dele, pin


def _dedup_sanciones(recs):
    """Cruza contra las 76 sanciones de comunicados. Devuelve las colisiones."""
    prev = RAW / 'sic.json'
    if not prev.exists():
        print('  ! no está raw/sic.json — no se pudo verificar el dedup', file=sys.stderr)
        return []
    viejas = json.loads(prev.read_text(encoding='utf-8'))
    urls = {(v.get('url') or '').strip().rstrip('/') for v in viejas}
    tits = {_norm(v.get('titulo')) for v in viejas if v.get('titulo')}
    choques = []
    for r in recs:
        if (r.get('url') or '').strip().rstrip('/') in urls or _norm(r.get('titulo')) in tits:
            choques.append(r.get('titulo'))
    return choques


def cmd_fetch(solo_circulares=False, refrescar=False, reparsear=False):
    RAW.mkdir(parents=True, exist_ok=True)
    cache = {} if refrescar else _cargar_cache()
    if reparsear and not cache:
        print('no hay HTML cacheado que re-parsear — corre `fetch` primero',
              file=sys.stderr)
        return 1
    objetivos = [(179, {})]
    if not solo_circulares:
        # Resoluciones SOLO de carácter general: las particulares son
        # nombramientos y actos de trámite, que no le cambian nada a nadie.
        objetivos.append((177, {'field_tipo_acto_target_id': CARACTER_GENERAL}))

    filas, facetas = {}, {}
    for tipo_id, extra in objetivos:
        print(f'\n== {TIPO_NORMA[tipo_id]}' + (' · solo Carácter General' if extra else ''))
        p = {'field_clasificacion2_target_id': tipo_id}
        p.update(extra)
        got = listar(p)
        print(f'    listado: {len(got)} nodos')
        for path, row in got.items():
            row['tipo_id'] = tipo_id
            filas.setdefault(path, row)
        print('    facetas:')
        facetas[tipo_id] = _facetas(tipo_id, extra)

    faltan = [p for p in filas if p not in cache]
    print(f'\n== nodos: {len(filas)}  (en cache: {len(filas) - len(faltan)}'
          f'  ·  por bajar: {len(faltan) if not reparsear else 0})')
    if not reparsear:
        for i, path in enumerate(faltan, 1):
            t = nodo(path)
            if t is None:
                print(f'    ! nodo sin respuesta: {path}', file=sys.stderr)
                t = ''
            cache[path] = t
            if i % 25 == 0:
                _guardar_cache(cache)
                print(f'    {i}/{len(faltan)}')
            time.sleep(PAUSA)
        _guardar_cache(cache)
    sin_html = sum(1 for p in filas if not (cache.get(p) or '').strip())
    if sin_html:
        print(f'    ! {sin_html} nodo(s) sin HTML: van sin fecha ni PDF', file=sys.stderr)

    # -------------------------------------------------------- ensamblado
    recs, descartados = [], Counter()
    for path, row in filas.items():
        d = parse_nodo(cache.get(path) or '')
        tipo_id = row['tipo_id']
        es_circular = tipo_id == 179
        titulo = row['titulo']
        cuerpo = d.get('cuerpo') or row.get('desc_listado') or ''
        emisor = emisor_de(row['tipo_norma'], titulo, cuerpo)
        if emisor != 'sic':
            descartados['otra_entidad'] += 1
            continue
        car, dele, pin = facetas.get(tipo_id, ({}, {}, None))
        num, anio_tit = numero_anio(titulo)
        fecha = d.get('fecha_expedicion') or d.get('fecha_publicacion') or ''
        # trampa ②: si el título declara un año y la fecha del nodo dice otro,
        # la fecha es de carga, no de expedición. Se conserva pero se marca.
        confiable = not (anio_tit and fecha[:4] and anio_tit != fecha[:4])
        deleg = dele.get(path)
        subtipo = subtipo_de(titulo, cuerpo, es_circular)
        anio = anio_tit or fecha[:4]
        # `referencia` es la cita corta del acto ("Circular Externa 001 de 2025"),
        # que es como el cliente y su abogado lo nombran. Va al campo `resolucion`
        # del esquema común.
        referencia = ' '.join(x for x in (subtipo, num, ('de ' + anio) if anio else '') if x)
        # La delegatura NO viaja en ningún campo que build_s3 meta al blob de
        # búsqueda `q` (= sancionado + motivo + descripcion + fuente_nombre), así
        # que se anexa al final de la descripción: queda buscable ("protección de
        # datos personales") sin desplazar el arranque del texto, que es lo único
        # que se muestra (la vista corta a 120 caracteres).
        dest = destinatario_de(cuerpo)
        desc = cuerpo
        for extra_txt in (f'Delegatura: {deleg}' if deleg else '',
                          f'Dirigida a: {dest}' if dest else ''):
            if extra_txt:
                desc = f'{desc} · {extra_txt}'.strip(' ·')
        recs.append({
            'titulo': titulo,
            # Titular de la tarjeta río abajo. Va la CITA del acto, no el
            # destinatario: es corta, uniforme y es como el cliente y su abogado
            # nombran la norma. Dejarlo vacío haría que build_s3 pusiera '—' y
            # reaparecería el modo de falla ya documentado con ANLA (tarjetas
            # tituladas con un guion); el destinatario, cuando existe, viaja en
            # su propio campo y queda buscable desde la descripción.
            'titular': referencia or titulo[:90],
            'tipo_acto': 'circular' if es_circular else 'resolucion',
            'subtipo': subtipo,
            'referencia': referencia,
            'numero': num,
            'anio': anio,
            'destinatario': dest,
            'descripcion': desc,
            'cuerpo': cuerpo,
            'delegatura': deleg,
            'delegatura_clave': bool(deleg and deleg in
                                     {DELEGATURA[d_] for d_ in DELEGATURAS_CLAVE}),
            'caracter': car.get(path) or pin,
            'fecha': fecha,
            'fecha_publicacion': d.get('fecha_publicacion') or '',
            'fecha_confiable': confiable,
            'emisor': 'sic',
            'tipo_norma_fuente': row['tipo_norma'],
            'url': BASE + path,
            'url_pdf': d.get('url_pdf') or '',
            'id': f'sic-norma-{path.rsplit("/", 1)[-1][:120]}',
        })

    choques = _dedup_sanciones(recs)
    if choques:
        print(f'\n!! DEDUP: {len(choques)} colisión(es) con las sanciones de '
              f'raw/sic.json — NO se escribe nada:', file=sys.stderr)
        for c in choques[:10]:
            print('   ', c, file=sys.stderr)
        return 1

    recs.sort(key=lambda r: (r['fecha'] or '', r['titulo']), reverse=True)
    OUT_JSON.write_text(json.dumps(recs, ensure_ascii=False), encoding='utf-8')

    # ------------------------------------------------------------ resumen
    print(f'\n=> {len(recs)} actos → {OUT_JSON.relative_to(REPO)}')
    print(f'   descartados por emisor ajeno: {descartados["otra_entidad"]}')
    for k, lab in (('tipo_acto', 'por tipo'), ('subtipo', 'por subtipo'),
                   ('delegatura', 'por delegatura'), ('caracter', 'por carácter')):
        c = Counter(r[k] or '(sin dato)' for r in recs)
        print(f'   {lab}:')
        for v, n in c.most_common(9):
            print(f'      {str(v)[:44]:46s} {n:4d}')
    con_pdf = sum(1 for r in recs if r['url_pdf'])
    con_fecha = sum(1 for r in recs if r['fecha'])
    dudosas = sum(1 for r in recs if not r['fecha_confiable'])
    print(f'   con PDF: {con_pdf}/{len(recs)}   con fecha: {con_fecha}/{len(recs)}'
          f'   fecha no confiable (trampa ②): {dudosas}')
    fechas = sorted(r['fecha'] for r in recs if r['fecha'])
    if fechas:
        print(f'   rango: {fechas[0]} → {fechas[-1]}')
    print('\nlisto. la entrada propuesta para fuentes.json está en _pendiente-sic.json')
    return 0


# -------------------------------------------------------------------- probe

def cmd_probe():
    """Mapea el view sin escribir nada: cuánto hay por cada combinación."""
    print('view:', VIEW)
    tot = listar({}, max_pages=3)
    print(f'  sin filtro (3 págs de muestra): {len(tot)} nodos')
    for tid, lab in TIPO_NORMA.items():
        n = len(listar({'field_clasificacion2_target_id': tid}))
        g = len(listar({'field_clasificacion2_target_id': tid,
                        'field_tipo_acto_target_id': CARACTER_GENERAL}))
        print(f'  {lab:14s} total={n:5d}   de carácter general={g:5d}')
    print('  delegaturas (sobre Circulares):')
    for did, lab in DELEGATURA.items():
        n = len(listar({'field_clasificacion2_target_id': 179,
                        'field_clasificacion5_target_id': did}))
        marca = ' *clave' if did in DELEGATURAS_CLAVE else ''
        print(f'    {lab[:44]:46s} {n:4d}{marca}')


# --------------------------------------------------------------------- test

# El encargo fija la validación: la cosecha debe traer estas dos.
ESPERADAS = [
    ('001', '2025', '2025-09-18'),
    ('002', '2025', '2025-10-07'),
]


def cmd_test():
    if not OUT_JSON.exists():
        print('no hay cosecha todavía — corre `fetch` primero', file=sys.stderr)
        return 1
    recs = json.loads(OUT_JSON.read_text(encoding='utf-8'))
    ok = True

    print(f'cosecha: {len(recs)} actos')
    for num, anio, fecha_esp in ESPERADAS:
        hit = [r for r in recs
               if r['tipo_acto'] == 'circular' and r['numero'] == num and r['anio'] == anio
               and r['subtipo'].startswith('Circular Externa')]
        if not hit:
            print(f'  FALLA  circular externa {num} de {anio}: no está')
            ok = False
            continue
        r = hit[0]
        marca = 'ok' if r['fecha'] == fecha_esp else f'OJO fecha={r["fecha"]} esperada={fecha_esp}'
        if r['fecha'] != fecha_esp:
            ok = False
        print(f'  {marca:14s} CE {num}/{anio} · {r["titulo"][:52]}')
        print(f'                 delegatura={r["delegatura"]} · pdf={"sí" if r["url_pdf"] else "NO"}')

    choques = _dedup_sanciones(recs)
    print(f'  {"ok" if not choques else "FALLA"}: dedup vs las sanciones de '
          f'raw/sic.json → {len(choques)} colisión(es)')
    ok = ok and not choques

    # nadie debe quedar sin lo mínimo para ser útil
    sin_fecha = [r for r in recs if not r['fecha']]
    sin_desc = [r for r in recs if not (r['descripcion'] or '').strip()]
    print(f'  sin fecha: {len(sin_fecha)}   ·   sin descripción: {len(sin_desc)}')
    ajenos = [r for r in recs if r['emisor'] != 'sic']
    if ajenos:
        print(f'  FALLA: {len(ajenos)} actos de otra entidad se colaron')
        ok = False

    print('\nTEST OK' if ok else '\nTEST con hallazgos')
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('probe', help='mapea el view, no escribe')
    fp = sub.add_parser('fetch', help='cosecha (resumible)')
    fp.add_argument('--solo-circulares', action='store_true',
                    help='omite las resoluciones de carácter general')
    fp.add_argument('--refrescar', action='store_true',
                    help='ignora el cache de nodos y los vuelve a abrir')
    fp.add_argument('--reparsear', action='store_true',
                    help='re-parsea el HTML ya cacheado, sin tocar la red')
    sub.add_parser('test', help='valida CE 001/002 de 2025 y el dedup')
    a = ap.parse_args()
    if a.cmd == 'probe':
        cmd_probe()
    elif a.cmd == 'fetch':
        sys.exit(cmd_fetch(a.solo_circulares, a.refrescar, a.reparsear))
    elif a.cmd == 'test':
        sys.exit(cmd_test())


if __name__ == '__main__':
    main()
