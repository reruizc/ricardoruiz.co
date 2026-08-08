#!/usr/bin/env python3
"""
Caudal · harvester de actos regulatorios de la DIAN (vía 2).

La DIAN es el regulador fiscal de todo cliente con operación en Colombia y era
el hueco más grande del pilar Regulatorio. Este harvester baja el REGISTRO
COMPLETO de resoluciones y circulares que expide la entidad.

⚠️ NO confundir con el pilar Ejecutivo. `normativa.jsonl` (Presidencia) tiene
~195 normas que MENCIONAN a la DIAN, pero son decretos de Presidencia: otra
cosa distinta de las resoluciones que la DIAN expide por su cuenta. Antes de
esta fuente, la Resolución 000240 del 24-dic-2025 (la de criptoactivos) no
existía en Caudal por ninguna vía — verificado con grep sobre normativa.jsonl
(0 aciertos) y sanciones.jsonl (8 aciertos, todos falsos positivos: SECOP I
000240 de 2014, ANLA 000240 de 2024/2025/2026 y NITs que contienen la cadena).

LA API (vía 2, no documentada)
------------------------------
El portal es SharePoint y expone una capa de servicios propia bajo /scripts/.
La página https://www.dian.gov.co/normatividad/Paginas/Resoluciones.aspx trae
inline la declaración del filtro:

    normativity.normFilter = { listName:"Normas", normType:"Resolución",
                               includeAnnex:true }

y el bundle público https://www.dian.gov.co/SiteAssets/js/dian.min.js arma la
llamada en `normativity.loadNorms`:

    GET /normatividad/scripts/HNormativity?type=Norms&filter=<JSON url-encoded>

con `year` agregado al filtro. Sin auth, sin token, sin ViewState. Devuelve
`{errorMessage, message, results:[...], status, statusMessage}` con status 0 =OK.

Cada fila: {id, name, description, issueDate, link, annex[]}.

POR QUÉ ESTA FUENTE Y NO EL NORMOGRAMA
--------------------------------------
`normograma.dian.gov.co` ("Compilación Jurídica DIAN") también publica normas y
es fácil de cosechar (árbol de partes estáticas, `t_1_normativa_tributaria_parte_07.html`
lista 648 resoluciones). Pero es una COMPILACIÓN CURADA, no el registro: trae
~22-40 resoluciones por año contra las ~200 reales, y **no incluye la 000240 de
2025** (su 2025 salta de la 0227 a nada). Se descartó por eso. Ver la bitácora
completa de vías probadas en el README del pilar / _pendiente-dian.json.

GOTCHAS MEDIDOS (no los "arregles" sin volver a medir)
------------------------------------------------------
1. `issueDate` viene en formato .NET `/Date(1767157200000)/` (epoch-millis), no
   ISO. Se convierte con `_dotnet_date_to_iso`, que descarta años fuera de
   [1990, hoy+1] en vez de inventar la fecha.
2. **El `link` trae ESPACIOS y ACENTOS literales**:
   `/normatividad/Normatividad/Resolución 000240 de 24-12-2025.pdf`
   Adivinar el nombre con guiones y sin tilde (`Resolucion-000240-de-24-12-2025.pdf`)
   da 404 — lo probé. Hay que usar el `link` que devuelve la API y
   percent-encodearlo (`_abs_url`), nunca reconstruirlo a mano.
3. `Anio` de la lista SharePoint es un campo **Calculated** → no se puede filtrar
   por él vía `_api` (`SPException: no se puede usar el campo "Anio" de tipo
   "Calculated"`). Por eso se pagina por año contra /scripts/, no contra _api.
4. La lista `Normas` tiene 5.684 ítems, por encima del list view threshold de
   SharePoint (5.000). El endpoint /scripts/ ya viene partido por año, así que
   esquiva el problema; no volver a intentar un `$top=6000` contra `_api`.
5. `_api/search/query` del portal está ROTO del lado del servidor
   (`SafeQueryPropertiesTemplateUrl ... no es una dirección URL válida`). No es
   nuestro; no perder tiempo ahí.
6. Los CONCEPTOS (doctrina) NO están en esta lista: viven en otro backend
   (`type=Doctrine`) con otro contrato. No se cosechan aquí todavía; ver la nota
   `doctrina` de _pendiente-dian.json.

Uso:
  python3 tools/caudal/supers/harvest_dian.py test     # valida la API + 1 fila
  python3 tools/caudal/supers/harvest_dian.py fetch    # baja todo (resumible)
  python3 tools/caudal/supers/harvest_dian.py fetch --desde 2020
  python3 tools/caudal/supers/harvest_dian.py fetch --force   # ignora caché
  python3 tools/caudal/supers/harvest_dian.py stats    # resumen de lo cosechado
Luego (archivos compartidos del pilar, NO los toca este script):
  python3 tools/caudal/supers/harvest_supers.py normalize
  python3 tools/caudal/supers/build_s3.py
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
import time
import urllib.parse
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = REPO / 'Bases de datos' / 'leyes-senado' / 'supers'
RAW = OUT / 'raw'
CACHE = RAW / 'dian-cache'          # un JSON por (tipo, año); resumible
SLUG = 'dian-normas'

BASE = 'https://www.dian.gov.co'
ENDPOINT = BASE + '/normatividad/scripts/HNormativity'
PAGINA = BASE + '/normatividad/Paginas/{}.aspx'

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')

# Los dos tipos que el portal publica bajo la lista "Normas". Medido sobre los
# 5.684 ítems de la lista: Resolución 2.980 · Circular 1.343 · 662 sin tipo
# (son anexos) · y colas de <6 (Memorando, Decreto, Ley...). El `pagina` es de
# donde se leen los años disponibles; `tipo_acto` es el del esquema del pilar.
TIPOS = [
    {'norm_type': 'Resolución', 'pagina': 'Resoluciones', 'tipo_acto': 'resolucion'},
    {'norm_type': 'Circular',   'pagina': 'Circulares',   'tipo_acto': 'circular'},
]

ANIO_MIN, ANIO_MAX = 1990, datetime.date.today().year + 1
DELAY = 1.2          # ritmo cortés con un portal del Estado
REINTENTOS = 3

# --- doctrina (conceptos y oficios) ---------------------------------------
# Backend distinto del de Normas, con otro contrato. Ver cmd_doctrina y la
# nota `doctrina` de _pendiente-dian.json.
SLUG_DOC = 'dian-doctrina'
CACHE_DOC = RAW / 'dian-doctrina-cache'
# MEDIDO sobre el barrido completo (8.249 conceptos): 1993-2019. OJO — un
# muestreo previo daba 2001-2019 y era FALSO: hay 17 documentos entre 1993 y
# 2000 que solo aparecen al barrer todo. El piso importa de verdad, porque es
# el rango con el que se parten los prefijos que se caen: con 2001 se habrían
# perdido en silencio los pre-2001 de esos prefijos.
DOC_ANIO_MIN, DOC_ANIO_MAX = 1993, 2019
DOC_INTERP_MAX = 3000     # recorte de legalInterpretation en el raw
DELAY_DOC = 2.0           # más lento: son respuestas de hasta ~2 MB

DOTNET_DATE = re.compile(r'/Date\((-?\d+)\)/')
YEAR_OPT = re.compile(r'<option[^>]*value=["\']?(\d{4})["\']?', re.I)


# --------------------------------------------------------------------------
# red
# --------------------------------------------------------------------------
def _curl(url, timeout=90):
    """curl por subprocess (mismo patrón del resto del pilar: esquiva el TLS
    de python 3.14 y deja poner UA de navegador, sin el cual varios portales
    del Estado responden 403).

    `-g` (globoff) es obligatorio: las URLs de doctrina llevan JSON crudo con
    corchetes y sin él curl aborta con 'bad range specification' antes de
    salir a la red."""
    cmd = ['/usr/bin/curl', '-s', '-g', '-A', UA, '--max-time', str(timeout), url]
    r = subprocess.run(cmd, capture_output=True, timeout=timeout + 15)
    return r.stdout.decode('utf-8', errors='replace')


def _curl_json(url, timeout=90):
    """Devuelve (data, error). El portal contesta HTML cuando se cae, así que
    el fallo de parseo se reporta como error legible en vez de reventar."""
    for intento in range(1, REINTENTOS + 1):
        body = _curl(url, timeout)
        if not body.strip():
            err = 'respuesta vacía'
        else:
            try:
                d = json.loads(body)
            except json.JSONDecodeError:
                err = f'respuesta no-JSON ({body.strip()[:60]!r})'
            else:
                if d.get('status') != 0:
                    return None, f"status={d.get('status')} {d.get('errorMessage')}"
                return d.get('results') or [], None
        if intento < REINTENTOS:
            time.sleep(DELAY * 2 * intento)
    return None, err


# --------------------------------------------------------------------------
# normalización de campos
# --------------------------------------------------------------------------
def _dotnet_date_to_iso(v):
    """'/Date(1767157200000)/' -> '2025-12-24'. Fuera de rango sano devuelve
    None en vez de adivinar (misma regla que harvest_sfc.py con su año 3022)."""
    if not v:
        return None
    m = DOTNET_DATE.search(str(v))
    if not m:
        return None
    try:
        d = datetime.datetime.fromtimestamp(int(m.group(1)) / 1000.0,
                                            datetime.timezone.utc)
    except (ValueError, OSError, OverflowError):
        return None
    return d.date().isoformat() if ANIO_MIN <= d.year <= ANIO_MAX else None


def _abs_url(link):
    """Absolutiza y percent-encodea. El link real trae espacios y tilde
    ('/normatividad/Normatividad/Resolución 000240 de 24-12-2025.pdf'); sin
    encodear no abre, y reconstruirlo a mano con guiones da 404."""
    if not link:
        return None
    link = str(link).strip()
    if not link:
        return None
    if link.startswith('http'):
        p = urllib.parse.urlsplit(link)
        return urllib.parse.urlunsplit(
            (p.scheme, p.netloc, urllib.parse.quote(p.path, safe='/%'),
             p.query, p.fragment))
    if not link.startswith('/'):
        link = '/' + link
    return BASE + urllib.parse.quote(link, safe='/%')


def _numero(name):
    """'Resolución 000240 de 2025' -> '000240' (conserva los ceros a la
    izquierda: así es como la cita la prensa y el cliente)."""
    if not name:
        return None
    m = re.search(r'\b(\d{1,7})\s+de\s+\d{4}', str(name))
    return m.group(1) if m else None


def fila(row, t, anio):
    """Fila cruda -> shape plano que `harvest_supers.normalize_row` mapea con
    el `map` de fuentes.json. `tipo_acto` va POR FILA porque esta fuente mezcla
    resoluciones y circulares (solo supersalud-registro hacía esto antes)."""
    name = (row.get('name') or '').strip()
    anexos = [{'nombre': (a.get('name') or '').strip(), 'url': _abs_url(a.get('link'))}
              for a in (row.get('annex') or [])]
    return {
        '_id': f"dian-{t['tipo_acto']}-{row.get('id')}",
        'id': row.get('id'),
        'titulo': name,
        'numero': _numero(name),
        'anio': anio,
        'tipo_norma': t['norm_type'],
        'tipo_acto': t['tipo_acto'],
        'fecha': _dotnet_date_to_iso(row.get('issueDate')),
        'descripcion': (row.get('description') or '').strip() or None,
        'url': _abs_url(row.get('link')),
        'anexos': anexos,
        'n_anexos': len(anexos),
    }


# --------------------------------------------------------------------------
# cosecha
# --------------------------------------------------------------------------
def anios_de(t):
    """Lee los años del <select> de la página del tipo. Es más honesto que
    hardcodear un rango: si la DIAN agrega un año, entra solo. Si la página
    cambia de forma, cae al rango completo y se reporta."""
    html = _curl(PAGINA.format(t['pagina']), timeout=60)
    anios = sorted({int(a) for a in YEAR_OPT.findall(html)
                    if ANIO_MIN <= int(a) <= ANIO_MAX}, reverse=True)
    if not anios:
        print(f"  ! {t['norm_type']}: no pude leer el <select> de años, "
              f"caigo al rango {ANIO_MIN}-{ANIO_MAX}", file=sys.stderr)
        anios = list(range(ANIO_MAX, ANIO_MIN - 1, -1))
    return anios


def url_anio(t, anio):
    f = {'listName': 'Normas', 'normType': t['norm_type'],
         'includeAnnex': True, 'year': str(anio)}
    return (ENDPOINT + '?' + urllib.parse.urlencode(
        {'type': 'Norms', 'filter': json.dumps(f, ensure_ascii=False)}))


def fetch(desde=None, force=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    hoy = datetime.date.today().year
    total, fallos = 0, []

    for t in TIPOS:
        anios = [a for a in anios_de(t) if desde is None or a >= desde]
        print(f"\n{t['norm_type']}: {len(anios)} años ({max(anios)}..{min(anios)})")
        time.sleep(DELAY)

        for anio in anios:
            cf = CACHE / f"{t['tipo_acto']}-{anio}.json"
            # El año en curso (y el siguiente, que ya trae normas) se re-baja
            # siempre: es el único que crece. Los cerrados salen del caché.
            cerrado = anio < hoy
            if cf.exists() and cerrado and not force:
                total += len(json.loads(cf.read_text(encoding='utf-8')))
                continue

            rows, err = _curl_json(url_anio(t, anio))
            if err:
                print(f"  ! {anio}: {err}", file=sys.stderr)
                fallos.append((t['tipo_acto'], anio, err))
                time.sleep(DELAY)
                continue

            recs = [fila(r, t, anio) for r in rows]
            cf.write_text(json.dumps(recs, ensure_ascii=False), encoding='utf-8')
            total += len(recs)
            print(f"  {anio}  {len(recs):>4d}")
            time.sleep(DELAY)

    consolidar()
    if fallos:
        print(f"\n⚠️  {len(fallos)} (tipo, año) fallaron y NO están en el raw:",
              file=sys.stderr)
        for ta, a, e in fallos[:12]:
            print(f"     {ta} {a}: {e}", file=sys.stderr)
    return fallos


def consolidar():
    """Une el caché por año en el raw/{slug}.json plano que espera el pilar."""
    rows = []
    for cf in sorted(CACHE.glob('*.json')):
        for r in json.loads(cf.read_text(encoding='utf-8')):
            # backfill: los cachés escritos antes de que existiera `_id` se
            # completan aquí en vez de exigir un re-fetch de todo el histórico.
            r.setdefault('_id', f"dian-{r.get('tipo_acto')}-{r.get('id')}")
            rows.append(r)
    # dedup defensivo por (tipo, id): si un acto llegara repetido entre años,
    # el conteo mentiría hacia arriba.
    vistos, out = set(), []
    for r in rows:
        k = (r.get('tipo_acto'), r.get('id'))
        if k in vistos:
            continue
        vistos.add(k)
        out.append(r)
    out.sort(key=lambda r: (r.get('fecha') or '', r.get('titulo') or ''), reverse=True)
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f'{SLUG}.json').write_text(json.dumps(out, ensure_ascii=False),
                                      encoding='utf-8')
    print(f"\n  ok {SLUG:18s} {len(out):>6d} actos -> raw/{SLUG}.json")
    return out


# --------------------------------------------------------------------------
# doctrina · conceptos y oficios (backend distinto de Normas)
# --------------------------------------------------------------------------
# Contrato (de normativity.executeSearch en dian.min.js):
#   GET /normatividad/scripts/HNormativity?type=Doctrine&<JSON crudo url-encoded>
# ⚠️ El JSON va PEGADO como fragmento de query string, NO como filter=...
#
# GOTCHAS MEDIDOS:
#  a) `descriptor` DEBE ir como string pelado. El bundle manda un array (es un
#     multi-select) y el servidor revienta con array en 6 de 6 pruebas — no es
#     volumen: descriptores con 1 sola fila fallan igual y en el mismo tiempo.
#  b) NO hay tope de resultados: medido conceptNumber="77" -> 287 filas / 1,96 MB
#     sin recorte. El costo es el payload, no un TOP N.
#  c) `conceptNumber` es CONTAINS sobre normNumber, no prefijo: "241" trae
#     016241, 022410, 024107, 84241... Por eso el barrido de 2 dígitos es un
#     conjunto cubridor: todo número de >=2 dígitos contiene algún par.
#  d) Algunos prefijos ("24", "9") devuelven HTML de error en <1 s — demasiado
#     rápido para ser timeout; parece una fila que rompe la serialización. Se
#     rescatan partiendo por año: "24" cae, pero "24"+2001 devuelve 32 filas.
#  e) RANGO REAL 2001-2019. Verificado con prefijos independientes (55, 300,
#     999) y con rangos de fecha hacia afuera: 0 filas antes de 2001 y después
#     de 2019. La doctrina posterior a 2019 NO está en este endpoint.
#  f) NO hay PDF: `link` viene vacío en todas las filas. El documento es la
#     ficha HTML DetalleDoctrina.aspx?DianId={id}, que además trae banco y
#     descriptores (que el buscador devuelve en null).
DETALLE_DOC = (BASE + '/normatividad/doctrina/Paginas/DetalleDoctrina.aspx?DianId={}')

_TAG = re.compile(r'<[^>]+>')
_WS = re.compile(r'[ \t ]+')


def _limpiar_html(s):
    """La interpretación viene con HTML crudo de SharePoint pegado
    ('<div class="ExternalClass...">...'). Sin limpiarlo se le muestra marcado
    al cliente y además ensucia el blob de búsqueda (un `<div>` no es texto que
    nadie vaya a buscar). Se quitan tags y se desescapan entidades."""
    if not s:
        return None
    import html as _html
    s = _TAG.sub(' ', str(s))
    s = _html.unescape(s)
    s = _WS.sub(' ', s)
    s = re.sub(r'\s*\n\s*', '\n', s)
    return s.strip() or None


def _url_doctrina(concept='', descriptor='', anio=None):
    f = {'descriptor': descriptor, 'conceptNumber': concept, 'textInside': ''}
    if anio:
        f['dateRangeStart'] = f'{anio}-01-01T05:00:00.000Z'
        f['dateRangeEnd'] = f'{anio}-12-31T05:00:00.000Z'
    return (ENDPOINT + '?type=Doctrine&'
            + urllib.parse.quote(json.dumps(f, ensure_ascii=False)))


def _anio_doc(row, fecha):
    """El campo `year` de la fuente NO es de fiar: en 21 de 8.249 contradice a
    su propio issueDate, e incluye un typo real (year=1029 con fecha
    2019-07-11). Manda la fecha, que sí está validada; `year` solo se usa
    cuando no hay fecha."""
    if fecha:
        return int(fecha[:4])
    y = row.get('year')
    return y if isinstance(y, int) and ANIO_MIN <= y <= ANIO_MAX else None


def fila_doc(row):
    interp = _limpiar_html(row.get('legalInterpretation')) or ''
    doc = (row.get('documentName') or '').strip()
    fecha = _dotnet_date_to_iso(row.get('issueDate'))
    return {
        '_id': f"dian-doctrina-{row.get('id')}",
        'id': row.get('id'),
        'titulo': doc,
        'numero': (row.get('normNumber') or '').strip() or None,
        'anio': _anio_doc(row, fecha),
        # normType real: 'Concepto' u 'Oficio'. tipo_acto va a 'otro' porque el
        # pilar no tiene una clase 'concepto' y sus _tipos_acto viven en
        # fuentes.json, que es compartido y no me toca tocar. Ver la nota
        # `mejora_tipo_acto_concepto` de _pendiente-dian.json.
        'tipo_norma': (row.get('normType') or '').strip() or 'Concepto',
        'tipo_acto': 'otro',
        'fecha': fecha,
        # La interpretación es la sustancia del concepto (lo que fija la
        # doctrina). Se recorta para que el raw no crezca a cientos de MB;
        # el texto íntegro siempre queda a un clic en `url`.
        'descripcion': (interp[:DOC_INTERP_MAX] or None),
        'interpretacion_truncada': len(interp) > DOC_INTERP_MAX,
        'fuentes_formales': _limpiar_html(row.get('formalOrigins')),
        'url': DETALLE_DOC.format(row.get('id')),
    }


def fetch_doctrina(force=False):
    """Barrido de conceptNumber de 2 dígitos ('00'..'99'), partiendo por año
    el prefijo que se cae. Dedup por id (un documento sale en varios prefijos)."""
    CACHE_DOC.mkdir(parents=True, exist_ok=True)
    caidos, rescatados_parcial = [], []

    for i in range(100):
        pref = f'{i:02d}'
        cf = CACHE_DOC / f'{pref}.json'
        if cf.exists() and not force:
            continue

        rows, err = _curl_json(_url_doctrina(concept=pref), timeout=120)
        if err is None:
            cf.write_text(json.dumps([fila_doc(r) for r in rows], ensure_ascii=False),
                          encoding='utf-8')
            print(f'  {pref}  {len(rows):>4d}')
            time.sleep(DELAY_DOC)
            continue

        # cae -> se parte por año (gotcha d)
        print(f'  {pref}  cae ({err[:40]}) -> parto por año', file=sys.stderr)
        acc, ok_anios = [], 0
        for anio in range(DOC_ANIO_MIN, DOC_ANIO_MAX + 1):
            time.sleep(DELAY_DOC)
            r2, e2 = _curl_json(_url_doctrina(concept=pref, anio=anio), timeout=120)
            if e2:
                continue
            ok_anios += 1
            acc.extend(fila_doc(r) for r in r2)
        if ok_anios:
            cf.write_text(json.dumps(acc, ensure_ascii=False), encoding='utf-8')
            print(f'  {pref}  {len(acc):>4d} (por año: {ok_anios}/'
                  f'{DOC_ANIO_MAX - DOC_ANIO_MIN + 1} años)')
            if ok_anios < DOC_ANIO_MAX - DOC_ANIO_MIN + 1:
                rescatados_parcial.append((pref, ok_anios))
        else:
            caidos.append(pref)
        time.sleep(DELAY_DOC)

    out = consolidar_doctrina()
    if rescatados_parcial:
        print(f'\n⚠️  {len(rescatados_parcial)} prefijos rescatados SOLO EN PARTE '
              f'(faltan años): {rescatados_parcial[:10]}', file=sys.stderr)
    if caidos:
        print(f'⚠️  {len(caidos)} prefijos NO se pudieron cosechar ni por año: '
              f'{caidos}', file=sys.stderr)
    return out


def consolidar_doctrina():
    vistos, out = set(), []
    for cf in sorted(CACHE_DOC.glob('*.json')):
        for r in json.loads(cf.read_text(encoding='utf-8')):
            if r['_id'] in vistos:
                continue
            vistos.add(r['_id'])
            # Retro-limpieza: los cachés escritos antes del fix traen el HTML
            # de SharePoint pegado. Se limpia aquí para no tener que re-barrer
            # las ~100 peticiones. Idempotente: sobre texto ya limpio no hace
            # nada. Se re-recorta después de limpiar, porque el recorte previo
            # contaba tags como si fueran contenido.
            if r.get('descripcion') and '<' in r['descripcion']:
                r['descripcion'] = _limpiar_html(r['descripcion'])
                r['interpretacion_truncada'] = bool(
                    r['descripcion'] and len(r['descripcion']) >= DOC_INTERP_MAX)
            if r.get('fuentes_formales') and '<' in r['fuentes_formales']:
                r['fuentes_formales'] = _limpiar_html(r['fuentes_formales'])
            # Retro-fix del año: la fecha manda sobre el `year` de la fuente
            # (21 filas lo contradicen, una con year=1029).
            if r.get('fecha') and str(r.get('anio')) != r['fecha'][:4]:
                r['anio'] = int(r['fecha'][:4])
            out.append(r)
    out.sort(key=lambda r: (r.get('fecha') or ''), reverse=True)
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f'{SLUG_DOC}.json').write_text(json.dumps(out, ensure_ascii=False),
                                          encoding='utf-8')
    print(f'\n  ok {SLUG_DOC:18s} {len(out):>6d} conceptos -> raw/{SLUG_DOC}.json')
    return out


def cmd_stats_doctrina():
    f = RAW / f'{SLUG_DOC}.json'
    if not f.exists():
        print('sin cosecha de doctrina: corre `doctrina`')
        return 1
    rows = json.loads(f.read_text(encoding='utf-8'))
    fechas = sorted(r['fecha'] for r in rows if r.get('fecha'))
    print(f'conceptos: {len(rows)}')
    print(f'rango: {fechas[0]} .. {fechas[-1]}' if fechas else 'sin fechas')
    print(f"sin fecha: {sum(1 for r in rows if not r.get('fecha'))}")
    print(f"truncados: {sum(1 for r in rows if r.get('interpretacion_truncada'))}")
    print('\npor tipo:')
    for k, v in Counter(r['tipo_norma'] for r in rows).most_common():
        print(f'  {v:>6}  {k}')
    print('\npor año:')
    for a, v in sorted(Counter(r['anio'] for r in rows).items(), reverse=True):
        print(f'  {a}  {v:>5}')
    return 0


# --------------------------------------------------------------------------
# comandos
# --------------------------------------------------------------------------
def cmd_test():
    """Valida el contrato de la API y la prueba de fuego del pilar."""
    print('1) endpoint Norms, año 2025, tipo Resolución')
    rows, err = _curl_json(url_anio(TIPOS[0], 2025))
    if err:
        print('   FALLA:', err)
        return 1
    print(f'   ok, {len(rows)} filas')

    recs = [fila(r, TIPOS[0], 2025) for r in rows]
    print('\n2) fila 0 normalizada')
    for k, v in recs[0].items():
        print(f'   {k:12} = {str(v)[:88]}')

    print('\n3) prueba de fuego · Resolución 000240 de 24-12-2025')
    hit = [r for r in recs if r['numero'] == '000240']
    if not hit:
        print('   FALLA: no está en la cosecha')
        return 1
    h = hit[0]
    ok = h['fecha'] == '2025-12-24'
    print(f"   {'ok' if ok else 'FALLA'}  {h['titulo']} · {h['fecha']}")
    print(f"   {h['descripcion'][:150]}")
    print(f"   pdf: {h['url']}")
    return 0 if ok else 1


def cmd_stats():
    f = RAW / f'{SLUG}.json'
    if not f.exists():
        print('sin cosecha todavía: corre `fetch`')
        return 1
    rows = json.loads(f.read_text(encoding='utf-8'))
    fechas = sorted(r['fecha'] for r in rows if r.get('fecha'))
    print(f"actos: {len(rows)}")
    print(f"rango: {fechas[0]} .. {fechas[-1]}" if fechas else 'sin fechas')
    print(f"sin fecha: {sum(1 for r in rows if not r.get('fecha'))}")
    print(f"sin pdf:   {sum(1 for r in rows if not r.get('url'))}")
    print('\npor tipo_acto:')
    for k, v in Counter(r['tipo_acto'] for r in rows).most_common():
        print(f'  {v:>6}  {k}')
    print('\npor año:')
    por = Counter((r['anio'], r['tipo_acto']) for r in rows)
    for a in sorted({a for a, _ in por}, reverse=True):
        res, cir = por.get((a, 'resolucion'), 0), por.get((a, 'circular'), 0)
        print(f'  {a}  resolucion {res:>4}   circular {cir:>4}')
    return 0


def main():
    p = argparse.ArgumentParser(description='Harvester DIAN (Caudal · pilar Regulatorio)')
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('test')
    fp = sub.add_parser('fetch')
    fp.add_argument('--desde', type=int, help='año mínimo a cosechar')
    fp.add_argument('--force', action='store_true', help='ignora el caché por año')
    sub.add_parser('stats')
    dp = sub.add_parser('doctrina', help='conceptos y oficios (2001-2019)')
    dp.add_argument('--force', action='store_true', help='ignora el caché por prefijo')
    sub.add_parser('stats-doctrina')
    a = p.parse_args()

    if a.cmd == 'test':
        return cmd_test()
    if a.cmd == 'stats':
        return cmd_stats()
    if a.cmd == 'stats-doctrina':
        return cmd_stats_doctrina()
    if a.cmd == 'doctrina':
        fetch_doctrina(force=a.force)
        return 0
    fetch(desde=a.desde, force=a.force)
    return 0


if __name__ == '__main__':
    sys.exit(main())
