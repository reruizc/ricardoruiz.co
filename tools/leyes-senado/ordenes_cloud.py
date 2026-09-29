#!/usr/bin/env python3
"""Feed autónomo de próximas órdenes del día para AWS Lambda.

Consulta los índices de Cámara y Senado y lee los PDF oficiales de las agendas
vigentes. Publica el mismo ``ordenes-vigentes.json`` que consume
``legislativo.html``, enriquecido con los proyectos que aparecen en cada orden.
"""
import datetime as dt
import html
import io
import json
import re
import unicodedata
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from zoneinfo import ZoneInfo

from leyes_en_vivo import S3_BUCKET, S3_PREFIX, http

CAM_API = 'https://www.camara.gov.co/wp-json/wp/v2/evento'
SEN_DOCS = 'https://www.senado.gov.co/index.php/documentos'
SEN_PLEN = 'http://www.secretariasenado.gov.co/index.php/orden-del-dia-senado'
KEY = f'{S3_PREFIX}/ordenes-vigentes.json'

CAMARAS = {
    'primera': 183, 'segunda': 184, 'tercera': 248, 'cuarta': 249,
    'quinta': 250, 'sexta': 251, 'septima': 252, 'afro': 272,
    'ordenamiento': 260, 'ddhh': 271, 'cuentas': 257, 'etica': 258,
    'mujer': 266, 'electoral': 269, 'plenaria': 253,
}
CAM_NICE = {
    **{x: f'Comisión {x.title()}' for x in
       ('primera', 'segunda', 'tercera', 'cuarta', 'quinta', 'sexta', 'septima')},
    'afro': 'Comisión Afro', 'ordenamiento': 'Ordenamiento Territorial',
    'ddhh': 'Derechos Humanos', 'cuentas': 'Comisión de Cuentas',
    'etica': 'Comisión de Ética', 'mujer': 'Comisión de la Mujer',
    'electoral': 'Comisión Electoral', 'plenaria': 'Plenaria de Cámara',
}
SEN_SCOPE = {'comision-cuarta': 'Comisión Cuarta',
             'comision-quinta': 'Comisión Quinta',
             'comision-sexta': 'Comisión Sexta'}
MESES = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5,
         'junio': 6, 'julio': 7, 'agosto': 8, 'septiembre': 9,
         'setiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12}
PROJECT_RE = re.compile(
    r'Proyecto\s+de\s+(Ley|Acto\s+Legislativo)(?:\s+Org[aá]nica)?'
    r'[^0-9“\"]{0,45}(\d{1,4})\s+de\s+(2\s?0\s?\d\s?\d)'
    r'(?:\s+(C[aá]mara|Senado))?.{0,180}?[“\"](.+?)[”\"]', re.I | re.S)


def _plain(value):
    value = html.unescape(re.sub(r'<[^>]+>', ' ', str(value or '')))
    return re.sub(r'\s+', ' ', value).strip()


def _pdf_plain(value):
    """Limpia separaciones espurias observadas en fuentes embebidas de Cámara."""
    value = _plain(value)
    for bad, good in (('modifi ca', 'modifica'), ('pro cesos', 'procesos'),
                      ('otra s', 'otras')):
        value = value.replace(bad, good)
    return value


def _fold(value):
    value = unicodedata.normalize('NFD', _plain(value).lower())
    return ''.join(c for c in value if unicodedata.category(c) != 'Mn')


def _fecha(title, published=''):
    """Fecha de sesión desde títulos oficiales, en formatos largos o numéricos."""
    text = _fold(title)
    month_pat = '|'.join(MESES)
    m = re.search(r'\b(\d{1,2})\s+(?:de\s+)?(' + month_pat +
                  r')(?:\s+(?:de\s+)?)?(20\d{2})\b', text)
    if m:
        try:
            return dt.date(int(m.group(3)), MESES[m.group(2)], int(m.group(1))).isoformat()
        except ValueError:
            pass
    m = re.search(r'\b(' + month_pat + r')\s+(\d{1,2})(?:\s+(?:de\s+)?)?(20\d{2})\b', text)
    if m:
        try:
            return dt.date(int(m.group(3)), MESES[m.group(1)], int(m.group(2))).isoformat()
        except ValueError:
            pass
    for pat in (r'\b(20\d{2})[./-](\d{1,2})[./-](\d{1,2})\b',
                r'\b(\d{1,2})[./-](\d{1,2})[./-](20\d{2})\b'):
        m = re.search(pat, text)
        if not m:
            continue
        y, mo, day = ((m.group(1), m.group(2), m.group(3)) if pat.startswith(r'\b(20')
                      else (m.group(3), m.group(2), m.group(1)))
        try:
            return dt.date(int(y), int(mo), int(day)).isoformat()
        except ValueError:
            pass
    # Una "agenda semanal" suele declarar un rango; la primera fecha ya fue
    # capturada arriba. Nunca usamos publicación como fecha de sesión: podría
    # convertir un documento viejo en una cita falsa de hoy.
    return ''


def _fecha_fin(title, inicio):
    """Fin inclusivo de una agenda semanal; para una sesión normal es inicio."""
    text = _fold(title)
    month_pat = '|'.join(MESES)
    found = []
    for day, month, year in re.findall(
            r'\b(\d{1,2})\s+(?:de\s+)?(' + month_pat +
            r')(?:\s+(?:de\s+)?)?(20\d{2})\b', text):
        try:
            found.append(dt.date(int(year), MESES[month], int(day)).isoformat())
        except ValueError:
            pass
    return max(found) if found else inicio


def _pdf_projects(url):
    """Extrae los proyectos debatibles del PDF, sin incluir el anuncio futuro."""
    if not url:
        return []
    blob = http(url, timeout=45, binary=True, retries=2)
    if not blob or len(blob) > 20_000_000:
        return []
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(blob), strict=False)
        text = '\n'.join((page.extract_text() or '') for page in reader.pages[:12])
    except Exception:
        return []
    # En comisiones el anuncio de la próxima sesión suele estar al final. En
    # plenaria aparece antes de los proyectos del día, así que solo se recorta
    # cuando queda después de la primera cita real.
    first = PROJECT_RE.search(text)
    if first:
        # «Anuncio de proyecto: 16 septiembre» es un dato de cada proyecto
        # (Senado Quinta), no la sección: con los dos puntos no se corta.
        for marker in re.finditer(r'anuncio\s+de\s+proyectos?\b(?!\s*:)', text, re.I):
            if marker.start() > first.start():
                text = text[:marker.start()]
                break
    out, seen = [], set()
    for match in PROJECT_RE.finditer(text):
        kind, number, year, chamber, title = match.groups()
        year = re.sub(r'\s+', '', year)
        key = f'{int(number):03d}-{year}-{("AL" if "acto" in _fold(kind) else "PL")}'
        if key in seen:
            continue
        seen.add(key)
        title = _pdf_plain(title).strip(' “”.')
        if len(title) < 12:
            continue
        out.append({'numero': f'{int(number):03d} de {year}' + (f' {chamber}' if chamber else ''),
                    'titulo': title})
    return out


def _en_ventana(fecha, fecha_fin, desde, hasta):
    return bool(fecha and fecha <= hasta and (fecha_fin or fecha) >= desde)


def _pdf_from_wp(event):
    body = ((event.get('content') or {}).get('rendered') or '')
    urls = re.findall(r'(?:href|src)=["\']([^"\']+\.pdf[^"\']*)', body, re.I)
    return html.unescape(urls[0]) if urls else ''


def _camara_scope(name, term, desde, hasta):
    query = urllib.parse.urlencode({
        'comision_evento': term, 'evento_tipo': 185, 'per_page': 30, 'page': 1,
        '_fields': 'id,date,title,content',
    })
    raw = http(f'{CAM_API}?{query}', timeout=35, retries=2)
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError('respuesta de Cámara no es una lista')
    rows = []
    for event in data:
        title = _plain((event.get('title') or {}).get('rendered'))
        fecha = _fecha(title, (event.get('date') or '')[:10])
        url = _pdf_from_wp(event)
        fecha_fin = _fecha_fin(title, fecha)
        if _en_ventana(fecha, fecha_fin, desde, hasta) and url:
            projects = _pdf_projects(url)
            rows.append({'id': f"cam-{event.get('id')}", 'fecha': fecha,
                         'fecha_fin': fecha_fin,
                         'publicado': (event.get('date') or '')[:10],
                         'corporacion': 'Cámara', 'ambito': CAM_NICE[name],
                         'titulo': title, 'url': url,
                         'proyectos': projects, 'n_proyectos': len(projects)})
    return name, rows


def _sen_scope(doc):
    href = (((doc.get('links') or {}).get('file') or {}).get('href') or '')
    path = href.split('/index.php/documentos/')[-1].split('/')
    for slug, nice in SEN_SCOPE.items():
        if slug in path and 'comisiones' in path and 'constitucionales' in path:
            return nice
    return None


def _senado(desde, hasta):
    # Sin orden explícito el índice devuelve documentos de 2019 y ninguna
    # orden vigente entra, sin error: hay que pedirlo del más nuevo al más viejo.
    raw = http(f'{SEN_DOCS}?format=json&view=documents&limit=100&offset=0'
               '&sort=created_on&direction=desc', timeout=45, retries=2)
    docs = (json.loads(raw).get('entities') or [])
    rows = []
    for doc in docs:
        title, ambito = _plain(doc.get('title')), _sen_scope(doc)
        label = _fold(f"{doc.get('category_slug') or ''} {title}")
        if not ambito or not re.search(r'orden(?:es)?[- ]del[- ]dia', label):
            continue
        fecha = _fecha(title, (doc.get('publish_date') or '')[:10])
        url = (((doc.get('links') or {}).get('file') or {}).get('href') or '').replace('http://', 'https://')
        fecha_fin = _fecha_fin(title, fecha)
        if _en_ventana(fecha, fecha_fin, desde, hasta) and url:
            projects = _pdf_projects(url)
            rows.append({'id': f"sen-{doc.get('id')}", 'fecha': fecha,
                         'fecha_fin': fecha_fin,
                         'publicado': (doc.get('publish_date') or '')[:10],
                         'corporacion': 'Senado', 'ambito': ambito,
                         'titulo': title, 'url': url,
                         'proyectos': projects, 'n_proyectos': len(projects)})
    return rows


def _senado_plenaria(desde, hasta):
    raw = http(f'{SEN_PLEN}?format=json&limit=20&offset=0', timeout=55, retries=3)
    docs = ((json.loads(raw).get('linked') or {}).get('documents') or [])
    rows = []
    for doc in docs:
        title = _plain(doc.get('title'))
        folded = _fold(title)
        if re.search(r'comunicado|cronograma|correccion|cambio de hora', folded):
            continue
        fecha = _fecha(title, (doc.get('publish_date') or '')[:10])
        url = (((doc.get('links') or {}).get('file') or {}).get('href') or '').replace('http://', 'https://')
        fecha_fin = _fecha_fin(title, fecha)
        if _en_ventana(fecha, fecha_fin, desde, hasta) and url:
            projects = _pdf_projects(url)
            rows.append({'id': f"sen-{doc.get('id')}", 'fecha': fecha,
                         'fecha_fin': fecha_fin,
                         'publicado': (doc.get('publish_date') or '')[:10],
                         'corporacion': 'Senado', 'ambito': 'Plenaria de Senado',
                         'titulo': title, 'url': url,
                         'proyectos': projects, 'n_proyectos': len(projects)})
    return rows


def build_ordenes(upload=True):
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    today = now.astimezone(ZoneInfo('America/Bogota')).date()
    desde, hasta = (today - dt.timedelta(days=1)).isoformat(), (today + dt.timedelta(days=14)).isoformat()
    rows, errors, ok_scopes = [], [], set()

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_camara_scope, name, term, desde, hasta): ('camara', name)
                   for name, term in CAMARAS.items()}
        futures[pool.submit(_senado, desde, hasta)] = ('senado', 'comisiones')
        futures[pool.submit(_senado_plenaria, desde, hasta)] = ('senado', 'plenaria')
        for future in as_completed(futures):
            source, scope = futures[future]
            try:
                value = future.result()
                if source == 'camara':
                    scope, value = value
                rows.extend(value)
                ok_scopes.add((source, scope))
            except Exception as exc:  # una fuente caída no borra las demás
                errors.append(f'{source}/{scope}: {exc}')

    if not ok_scopes:
        raise RuntimeError('ninguna fuente de órdenes respondió: ' + '; '.join(errors))

    # Dedup de correcciones/republicaciones: gana la publicación más nueva.
    best = {}
    for row in rows:
        key = (row['corporacion'], row['ambito'], row['fecha'])
        if key not in best or (row['publicado'], row['n_proyectos']) > (best[key]['publicado'], best[key]['n_proyectos']):
            best[key] = row
    rows = sorted(best.values(), key=lambda x: (x['fecha'], x['corporacion'], x['ambito']))
    result = {'v': now.isoformat(), 'desde': desde, 'hasta': hasta, 'n': len(rows),
              'ordenes': rows,
              'cobertura': 'Cámara: 14 comisiones y plenaria. Senado: plenaria y comisiones Cuarta, Quinta y Sexta.',
              'fuentes_ok': len(ok_scopes), 'fuentes_error': errors}
    if upload:
        import boto3
        boto3.client('s3').put_object(Bucket=S3_BUCKET, Key=KEY,
            Body=json.dumps(result, ensure_ascii=False, indent=1).encode(),
            ContentType='application/json', CacheControl='public, max-age=300')
    return result


if __name__ == '__main__':
    result = build_ordenes(upload=False)
    print(json.dumps(result, ensure_ascii=False, indent=1))
