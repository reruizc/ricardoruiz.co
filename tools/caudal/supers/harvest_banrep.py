#!/usr/bin/env python3
"""
Caudal · pilar Regulatorio — Banco de la República · régimen cambiario y
reglamentación de la Junta Directiva (vía 2).

⚠️ EL BANREP NO SANCIONA. No es una superintendencia: no impone multas ni abre
investigaciones. Su acto es NORMATIVO — Resoluciones Externas de la Junta
Directiva y Circulares Reglamentarias que definen qué se puede hacer con
divisas. Por eso todos los registros salen con `tipo_acto` ∈ {resolucion,
circular, otro} y NUNCA 'sancion', y `sancionado` va NULL a propósito (una
norma general no tiene destinatario individual — ver la nota
`interaccion_sancionado_guion` de _pendiente-banrep.json).

DOS BLOQUES, complementarios:

  A) NOVEDADES  — /es/normatividad, la vista Drupal cronológica de todo acto
     reglamentario publicado. Tabla con columnas limpias (tipo · número ·
     asunto · <time datetime> · PDF). 3.635 actos, 1986-12-31 → hoy, sin un
     solo registro sin fecha ni sin PDF. Es el HISTORIAL DE CAMBIOS: cada
     boletín que modifica algo. Los años 1986-1990 traen UN registro por año
     ("Resoluciones de la Junta Monetaria de 1988"): son compilaciones
     anuales, no actos sueltos — no leer ese tramo como "casi no hubo
     actividad". El registro acto por acto arranca en 1991.

  B) CAMBIARIO  — el COMPENDIO VIGENTE del régimen de cambios, que la vista de
     novedades NO contiene: ahí solo están los boletines que lo modifican, no
     el texto consolidado que el cliente tiene que cumplir hoy.

     ⚠️⚠️ LA DCIN-83 YA NO ES LA VIGENTE. Es la referencia que todo el mundo
     cita de memoria, pero el compendio de la DCIN-83 quedó congelado el
     31-ago-2021 y fue sustituido por la **Circular Reglamentaria DCIP-83
     (2023)**, que es la que rige. Verificado en la propia página de
     compendios del banco, que lista tres compendios históricos (DCIN-83 hasta
     24-may-2018 · DCIN-83 hasta 31-ago-2021 · DCIP-83 hasta 31-oct-2023) y
     enlaza aparte el "Compendio actualizado" → DCIP-83. Traer solo la DCIN-83
     sería entregarle a un cliente de comercio exterior el régimen derogado.
     Los tres compendios históricos se conservan, marcados `vigente=False`.

     El compendio DCIP-83 se publica DESPIEZADO en 28 documentos: 12 capítulos
     (declaraciones de cambio · importaciones · exportaciones · endeudamiento
     externo · cuentas de compensación · zonas francas · hidrocarburos y
     minería …), 12 formularios/reportes periódicos y 4 anexos. Cada uno con
     su PDF. Se emiten como 28 registros, no como uno solo: el cliente busca
     "cuentas de compensación", no "DCIP-83".

WAF: www.banrep.gov.co está detrás de Radware/ShieldSquare (PerfDrive). Un
curl pelado —incluso con User-Agent de Chrome— es redirigido a
validate.perfdrive.com y NO ve el sitio. Pasa con el JUEGO COMPLETO de headers
de navegador (Accept, Accept-Language, sec-ch-ua, Sec-Fetch-*,
Upgrade-Insecure-Requests): ver HEADERS. Si algún día deja de pasar, el
síntoma es inconfundible (la respuesta trae 'perfdrive' y ~16 KB).

Descartadas y por qué:
  · vía 1 (Socrata): el BanRep publica 5 datasets en datos.gov.co y son TODOS
    indicadores estadísticos (DTF · UVR · IBR · IPVU) más una landing de
    "Conjuntos de Datos Obligatorios". Cero normatividad. Buscar "régimen
    cambiario" en el catálogo da 0 resultados.
  · El buscador de la vista (`modal_search_term`) es un modal decorativo: se
    ignora como parámetro GET y devuelve siempre la primera página. Medido con
    'DCIN-83' y 'DCIN'. Por eso la cosecha pagina, no busca.
  · /jsonapi y /sitemap.xml dan 404 (a diferencia de la UIAF, que sí expone
    JSON:API).

Incremental: la vista va en orden cronológico DESC, así que un acto nuevo
DESPLAZA todo. Cachear por número de página es correcto solo para el fondo
histórico; el frente se re-baja siempre. `fetch` recorre desde la página 0 y
PARA en la primera página cuyos items ya estén todos conocidos (algoritmo
correcto para un feed DESC: si una página entera es conocida, lo que sigue
también). Con `--full` re-baja las 606. Dedup global por URL de nodo.

Comandos:
  python3 tools/caudal/supers/harvest_banrep.py test     # WAF + 1 página + DCIP-83 vigente
  python3 tools/caudal/supers/harvest_banrep.py fetch    # incremental (novedades + cambiario)
  python3 tools/caudal/supers/harvest_banrep.py fetch --full [--workers N]
  python3 tools/caudal/supers/harvest_banrep.py build    # caché -> raw/banrep-normatividad.json
  python3 tools/caudal/supers/harvest_banrep.py stats
"""
import argparse
import hashlib
import html
import json
import re
import subprocess
import sys
import time
from collections import Counter, OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SUP = REPO / 'Bases de datos' / 'leyes-senado' / 'supers'
RAW = SUP / 'raw'
PAGES = RAW / 'banrep-pages'
OUT_JSON = RAW / 'banrep-normatividad.json'

BASE = 'https://www.banrep.gov.co'
NOVEDADES = BASE + '/es/normatividad'
COMPENDIO_DCIP = BASE + '/es/regulacion-operaciones-cambiarias-dcip-83'
COMPENDIOS_HIST = BASE + '/es/normatividad/regulacion-operaciones-cambiarias/compendios-dcin-83-dcip-83'

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')
# El juego COMPLETO es lo que pasa el WAF. No recortar.
HEADERS = [
    'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language: es-CO,es;q=0.9,en;q=0.8',
    'sec-ch-ua: "Chromium";v="126", "Not)A;Brand";v="24"',
    'sec-ch-ua-mobile: ?0',
    'sec-ch-ua-platform: "macOS"',
    'Sec-Fetch-Dest: document',
    'Sec-Fetch-Mode: navigate',
    'Sec-Fetch-Site: none',
    'Sec-Fetch-User: ?1',
    'Upgrade-Insecure-Requests: 1',
]

TIPOS_ACTO = ('sancion', 'apertura_investigacion', 'archivo',
              'contribucion_especial', 'resolucion', 'circular', 'otro')

# Referencia del acto dentro del asunto: "Circular Reglamentaria Externa DSP-465",
# "Circular Externa Operativa y de Servicios DFV-108", "Resolución Externa 1 de 2018".
REF_SIGLA = re.compile(
    r'\b((?:Circular\s+Reglamentaria(?:\s+Externa)?(?:\s+Operativa\s+y\s+de\s+Servicios)?'
    r'|Circular\s+Externa\s+Operativa\s+y\s+de\s+Servicios'
    r'|Carta\s+Circular\s+Externa|Circular\s+Externa|Circular)\s+'
    r'([A-ZÁÉÍÓÚÑ]{2,7}-\d+[A-Za-z0-9\-]*))', re.I)
REF_NUM = re.compile(
    r'\b((?:Resoluci[oó]n(?:es)?\s+[Ee]xterna(?:s)?|Resoluci[oó]n)\s+'
    r'(?:No\.?\s*)?(\d+[A-Za-z]?)\s+de\s+(\d{4}))', re.I)


# --------------------------------------------------------------------- http
def curl(url, timeout=60, retries=3):
    cmd = ['/usr/bin/curl', '-sk', '-m', str(timeout), '-A', UA, '--compressed', '-L']
    for h in HEADERS:
        cmd += ['-H', h]
    cmd.append(url)
    last = None
    for i in range(retries):
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=timeout + 15)
            body = r.stdout.decode('utf-8', errors='replace')
            if r.returncode == 0 and body:
                if 'perfdrive' in body[:4000].lower() and len(body) < 40000:
                    last = RuntimeError('WAF: bloqueado por PerfDrive/ShieldSquare')
                else:
                    return body
            else:
                last = RuntimeError(f'curl rc={r.returncode}')
        except subprocess.TimeoutExpired:
            last = RuntimeError('timeout')
        time.sleep(2.0 * (i + 1))
    raise last


def _txt(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()


def _nid(nodo):
    """Id estable a partir de la RUTA COMPLETA del nodo.

    ⚠️ No usar el último segmento truncado: Drupal le pega sufijos -0/-1/-2 a
    cada modificación sucesiva de la misma circular ('…-dte-184-asunto-33-…-6')
    y ese sufijo es lo ÚNICO que las distingue. Truncar a 90 caracteres lo
    cortaba y producía 44 ids compartidos por 195 actos distintos. Además dos
    rutas distintas pueden terminar igual, así que el hash va sobre la ruta
    entera y el slug legible queda solo como prefijo.
    """
    slug = nodo.rstrip('/').rsplit('/', 1)[-1][:60]
    return f'{slug}-{hashlib.md5(nodo.encode("utf-8")).hexdigest()[:8]}'


def _abs(u):
    """CloudFront viene protocol-relative (//d1b4...); el resto, relativo."""
    u = html.unescape((u or '').strip())
    if u.startswith('//'):
        return 'https:' + u
    if u.startswith('/'):
        return BASE + u
    return u


# ------------------------------------------------------------------ parseo A
def parse_novedades(doc):
    """Filas de la tabla de /es/normatividad -> lista de dicts."""
    out = []
    for tr in re.findall(r'<tr>(.*?)</tr>', doc, re.S):
        tit = re.search(r'views-field-title"[^>]*>(.*?)</td>', tr, re.S)
        if not tit:
            continue                                   # <thead>
        a = re.search(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>', tit.group(1), re.S)
        if not a:
            continue
        def col(f):
            m = re.search(rf'views-field-field-{f}"[^>]*>(.*?)</td>', tr, re.S)
            return _txt(m.group(1)) if m else ''
        t = re.search(r'datetime="(\d{4}-\d{2}-\d{2})', tr)
        pdf = re.search(r'href="([^"]+\.pdf[^"]*)"', tr, re.I)
        out.append({
            'tipo_fuente': col('regla'),
            'numero_col': col('num-regla'),
            'titulo': _txt(a.group(2)),
            'nodo': html.unescape(a.group(1)),
            'fecha': t.group(1) if t else '',
            'pdf': _abs(pdf.group(1)) if pdf else '',
        })
    return out


def ultima_pagina(doc):
    ns = [int(x) for x in re.findall(r'\?page=(\d+)', doc)]
    return max(ns) if ns else 0


def clasificar(tipo_fuente, titulo):
    """tipo_acto + rótulo. Whitelist dura; nunca se inventa un valor.

    Se mira PRIMERO el título y después la columna de tipo: 'Boletines y
    resoluciones de la Junta Directiva' es un contenedor y adentro puede ir
    tanto una resolución externa como una circular reglamentaria.
    """
    t = (titulo or '').lower()
    tf = (tipo_fuente or '').lower()
    if 'proyecto' in tf or t.startswith('proyecto de '):
        # NO está vigente: es norma en consulta. Marcarlo importa.
        return 'otro', 'Proyecto de regulación'
    if 'derogaci' in t:
        return 'otro', 'Derogación'
    if re.search(r'resoluci[oó]n(es)?\s+externa', t):
        return 'resolucion', 'Resolución Externa'
    if 'carta circular' in t or 'carta circular' in tf:
        return 'circular', 'Carta Circular Externa'
    if 'circular reglamentaria' in t:
        return 'circular', 'Circular Reglamentaria Externa'
    if 'circular' in t or 'circular' in tf:
        return 'circular', 'Circular Externa'
    if 'resoluci' in t or 'resoluci' in tf:
        return 'resolucion', 'Resolución'
    if 'junta directiva' in tf:
        return 'resolucion', 'Boletín de la Junta Directiva'
    return 'otro', (tipo_fuente or 'Acto del Banco de la República')


def referencia(titulo, tipo_fuente, numero_col, fecha):
    """Identificador corto del acto (va al campo `resolucion`)."""
    m = REF_SIGLA.search(titulo or '')
    if m:
        return re.sub(r'\s+', ' ', m.group(1)).strip()
    m = REF_NUM.search(titulo or '')
    if m:
        return re.sub(r'\s+', ' ', m.group(1)).strip()
    anio = (fecha or '')[:4]
    n = (numero_col or '').strip()
    if 'junta directiva' in (tipo_fuente or '').lower() and n and anio:
        return f'Boletín {n} de {anio}'
    return f'{tipo_fuente} {n}'.strip() if n else (tipo_fuente or '').strip()


# ------------------------------------------------------------------ parseo B
def parse_compendio_dcip(doc):
    """28 piezas del compendio VIGENTE (12 capítulos + reportes + anexos)."""
    out = []
    vistos = set()
    for u, t in re.findall(
            r'<a[^>]+href="(/es/normatividad/compendio-dcip-83/[^"]+)"[^>]*>(.*?)</a>',
            doc, re.S):
        nom = _txt(t)
        if not nom or u in vistos:
            continue
        vistos.add(u)
        # el PDF asociado es el enlace 'Descargar' que sigue al capítulo
        i = doc.find(u)
        pdf = re.search(r'href="([^"]+\.pdf[^"]*)"', doc[i:i + 1600], re.I)
        out.append({'nombre': nom, 'nodo': u,
                    'pdf': _abs(pdf.group(1)) if pdf else ''})
    return out


def parse_compendios_hist(doc):
    out = []
    for u, t in re.findall(r'<a[^>]+href="([^"]+\.pdf[^"]*)"[^>]*>(.*?)</a>', doc, re.S):
        nom = _txt(t)
        if 'compendio' in nom.lower():
            out.append({'nombre': nom, 'pdf': _abs(u)})
    # el mismo PDF aparece dos veces (cloudfront + banrep.gov.co)
    ded = OrderedDict()
    for r in out:
        ded.setdefault(r['pdf'].rsplit('/', 1)[-1], r)
    return list(ded.values())


# -------------------------------------------------------------------- fetch
def _page_path(p):
    return PAGES / f'{p:04d}.html'


def fetch(full=False, workers=3):
    PAGES.mkdir(parents=True, exist_ok=True)
    doc0 = curl(f'{NOVEDADES}?page=0')
    last = ultima_pagina(doc0)
    _page_path(0).write_text(doc0, encoding='utf-8')
    print(f'  novedades: última página = {last} (~{(last + 1) * 6} actos)')

    conocidos = set()
    for f in sorted(PAGES.glob('*.html')):
        try:
            for r in parse_novedades(f.read_text(encoding='utf-8', errors='replace')):
                conocidos.add(r['nodo'])
        except Exception:
            pass

    if full:
        faltan = [p for p in range(last + 1)]
        print(f'  --full: re-bajando {len(faltan)} páginas con {workers} obreros')
        def one(p):
            _page_path(p).write_text(curl(f'{NOVEDADES}?page={p}'), encoding='utf-8')
            return p
        ok = err = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(one, p): p for p in faltan}
            for fu in as_completed(futs):
                try:
                    fu.result(); ok += 1
                except Exception as e:
                    err += 1
                    print(f'    ! p{futs[fu]}: {e}', file=sys.stderr)
                if (ok + err) % 60 == 0:
                    print(f'    {ok + err}/{len(faltan)}')
        print(f'  novedades: {ok} ok · {err} fallos')
    else:
        # feed DESC: parar en la primera página enteramente conocida
        nuevos, p = 0, 0
        while p <= last:
            doc = doc0 if p == 0 else curl(f'{NOVEDADES}?page={p}')
            rows = parse_novedades(doc)
            _page_path(p).write_text(doc, encoding='utf-8')
            frescos = [r for r in rows if r['nodo'] not in conocidos]
            nuevos += len(frescos)
            for r in frescos:
                conocidos.add(r['nodo'])
            if rows and not frescos and p > 0:
                print(f'  novedades: página {p} ya conocida entera -> paro. '
                      f'{nuevos} actos nuevos')
                break
            if not _page_path(p + 1).exists() and p + 1 <= last:
                pass                                   # hueco: seguimos
            p += 1
            time.sleep(0.8)
        else:
            print(f'  novedades: recorridas todas. {nuevos} actos nuevos')

    # bloque cambiario: siempre fresco, son 3 peticiones
    (RAW / 'banrep-compendio-dcip.html').write_text(curl(COMPENDIO_DCIP), encoding='utf-8')
    (RAW / 'banrep-compendios-hist.html').write_text(curl(COMPENDIOS_HIST), encoding='utf-8')
    print('  cambiario: compendio DCIP-83 vigente + compendios históricos ok')


# -------------------------------------------------------------------- build
def build():
    recs = OrderedDict()

    # --- A) novedades
    for f in sorted(PAGES.glob('*.html')):
        doc = f.read_text(encoding='utf-8', errors='replace')
        for r in parse_novedades(doc):
            if r['nodo'] in recs:
                continue
            ta, rot = clasificar(r['tipo_fuente'], r['titulo'])
            ref = referencia(r['titulo'], r['tipo_fuente'], r['numero_col'], r['fecha'])
            recs[r['nodo']] = {
                '_id': f'banrep-{_nid(r["nodo"])}',
                'bloque': 'novedades',
                'tipo_acto': ta,
                'rotulo': rot,
                'resolucion': ref,
                'motivo': r['titulo'],
                'fecha': r['fecha'],
                'url': _abs(r['pdf'] or r['nodo']),
                'url_nodo': _abs(r['nodo']),
                'vigente': None,
            }

    # --- B) compendio cambiario VIGENTE (DCIP-83)
    p = RAW / 'banrep-compendio-dcip.html'
    if p.exists():
        doc = p.read_text(encoding='utf-8', errors='replace')
        for c in parse_compendio_dcip(doc):
            k = 'dcip::' + c['nodo']
            nid = c['nodo'].rstrip('/').rsplit('/', 1)[-1][:60]
            recs[k] = {
                '_id': f'banrep-dcip83-{nid}',
                'bloque': 'cambiario-vigente',
                'tipo_acto': 'circular',
                'rotulo': 'Circular Reglamentaria DCIP-83 (régimen cambiario vigente)',
                'resolucion': 'Circular Reglamentaria DCIP-83',
                'motivo': c['nombre'],
                'fecha': '2023-11-01',   # rige desde el 1-nov-2023 (el compendio
                                         # anterior estuvo vigente hasta el 31-oct-2023)
                'url': c['pdf'] or _abs(c['nodo']),
                'url_nodo': _abs(c['nodo']),
                'vigente': True,
            }

    # --- B2) compendios históricos (DCIN-83 y DCIP-83 anteriores)
    p = RAW / 'banrep-compendios-hist.html'
    if p.exists():
        doc = p.read_text(encoding='utf-8', errors='replace')
        for c in parse_compendios_hist(doc):
            fn = c['pdf'].rsplit('/', 1)[-1]
            recs['hist::' + fn] = {
                '_id': 'banrep-compendio-' + re.sub(r'\.pdf$', '', fn)[:60],
                'bloque': 'cambiario-historico',
                'tipo_acto': 'circular',
                'rotulo': 'Compendio cambiario derogado',
                'resolucion': ('Circular Reglamentaria DCIP-83'
                               if 'dcip' in fn.lower() else
                               'Circular Reglamentaria Externa DCIN-83'),
                'motivo': c['nombre'],
                'fecha': _fecha_compendio(c['nombre']),
                'url': c['pdf'],
                'url_nodo': COMPENDIOS_HIST,
                'vigente': False,
            }

    rows = list(recs.values())
    rows.sort(key=lambda r: (r['fecha'] or ''), reverse=True)
    RAW.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    print(f'  build: {len(rows)} actos -> {OUT_JSON.relative_to(REPO)}')
    return rows


MESES = {'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
         'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
         'septiembre': '09', 'octubre': '10', 'noviembre': '11',
         'diciembre': '12'}


def _fecha_compendio(nombre):
    """'Compendio ... vigente hasta el 31 de octubre de 2023' -> 2023-10-31."""
    m = re.search(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})', nombre or '', re.I)
    if not m:
        return ''
    d, mes, a = m.group(1).zfill(2), MESES.get(m.group(2).lower(), ''), m.group(3)
    return f'{a}-{mes}-{d}' if mes else ''


# -------------------------------------------------------------------- stats
def stats():
    if not OUT_JSON.exists():
        print('  (no hay build todavía)'); return
    rows = json.loads(OUT_JSON.read_text(encoding='utf-8'))
    print(f'  actos: {len(rows)}')
    print('  tipo_acto:', dict(Counter(r['tipo_acto'] for r in rows)))
    print('  bloque   :', dict(Counter(r['bloque'] for r in rows)))
    print('  rótulos  :')
    for k, v in Counter(r['rotulo'] for r in rows).most_common():
        print(f'      {v:5d}  {k}')
    fs = sorted(r['fecha'] for r in rows if r['fecha'])
    print(f'  rango    : {fs[0]} .. {fs[-1]}   sin fecha: {sum(1 for r in rows if not r["fecha"])}')
    print(f'  sin PDF  : {sum(1 for r in rows if not r["url"])}')
    print('  por año:')
    for a, v in sorted(Counter(r['fecha'][:4] for r in rows if r['fecha']).items()):
        print(f'      {a}  {v:4d}  {"#" * min(60, v // 2)}')


# --------------------------------------------------------------------- test
def test():
    print('· WAF + primera página')
    doc = curl(f'{NOVEDADES}?page=0')
    rows = parse_novedades(doc)
    assert rows, 'no se parseó ninguna fila (¿cambió el marcado?)'
    print(f'  ok · {len(rows)} filas · última página {ultima_pagina(doc)}')
    for r in rows[:3]:
        ta, rot = clasificar(r['tipo_fuente'], r['titulo'])
        print(f'    {r["fecha"]} [{ta}/{rot}] {referencia(r["titulo"], r["tipo_fuente"], r["numero_col"], r["fecha"])}')
        print(f'        {r["titulo"][:96]}')

    print('· compendio cambiario VIGENTE (prueba de fuego: debe ser DCIP-83, no DCIN-83)')
    doc = curl(COMPENDIO_DCIP)
    caps = parse_compendio_dcip(doc)
    ti = re.search(r'<title>(.*?)</title>', doc, re.S)
    print('  título:', _txt(ti.group(1))[:80] if ti else '?')
    assert 'DCIP-83' in doc, 'la página vigente no menciona DCIP-83'
    assert len(caps) >= 12, f'solo {len(caps)} piezas del compendio'
    print(f'  ok · {len(caps)} piezas · con PDF: {sum(1 for c in caps if c["pdf"])}')
    for c in caps[:4]:
        print(f'    - {c["nombre"][:88]}')

    print('· compendios históricos')
    hist = parse_compendios_hist(curl(COMPENDIOS_HIST))
    for c in hist:
        print(f'    - {c["nombre"][:70]}  -> {_fecha_compendio(c["nombre"])}')
    assert hist, 'no se encontró ningún compendio histórico'
    print('TEST OK')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['test', 'fetch', 'build', 'stats'])
    ap.add_argument('--full', action='store_true')
    ap.add_argument('--workers', type=int, default=3)
    a = ap.parse_args()
    if a.cmd == 'test':
        test()
    elif a.cmd == 'fetch':
        fetch(full=a.full, workers=a.workers)
    elif a.cmd == 'build':
        build(); stats()
    else:
        stats()


if __name__ == '__main__':
    main()
