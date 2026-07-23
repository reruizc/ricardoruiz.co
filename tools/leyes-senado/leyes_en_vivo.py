#!/usr/bin/env python3
"""
Feed "Proyectos de ley en vivo" para legislativo.html.

Produce un JSON compacto con los ÚLTIMOS 5 proyectos de ley radicados en cada
cámara de la legislatura viva (2026-2027) y sube a S3 tanto el JSON como el PDF
del texto radicado de cada uno. El frontend (sección "En vivo" de
legislativo.html) lo lee directo de S3.

Dos fuentes, dos mecanismos (ver notas de campo abajo):
  · SENADO  → POST leyes.senado.gov.co/api/search_pdly.php {legislatura}
              + GET  get_detalle_pdly.php?id=N   (para fecha + URL del PDF)
  · CÁMARA  → POST camara.gov.co/wp-admin/admin-ajax.php
                   {action:download_proyectos_ley_xlsx, legislatura:20}
              devuelve un XLSX ya ordenado del más nuevo al más viejo con
              objeto, autores, estado, comisión y el link a la ficha (de donde
              sale el PDF). legislatura 20 = 2026-2027.

Diseñado para correr como Lambda (EventBridge 3×/día) SIN dependencias externas:
solo stdlib (urllib para HTTP, zipfile+ElementTree para el XLSX, boto3 —que ya
viene en el runtime de Lambda— para S3). También corre como CLI para sembrar el
primer JSON y depurar.

Notas de campo:
  · Senado tiene un WAF que banea a curl por fingerprint TLS ante RÁFAGAS
    (~30 req seguidas). Este feed hace poco volumen (1 lista + 5 detalles +
    los PDFs que falten) con pausas, y ADEMÁS es idempotente: si el PDF ya
    está en S3 no lo vuelve a bajar. En régimen, casi no toca la red de Senado.
  · Cámara es WordPress limpio (admin-ajax), sin WAF agresivo. El "nonce" de
    la página NO es obligatorio para el download del XLSX (acción pública),
    pero se scrapea de la página por si algún día empieza a exigirlo.
  · Robusto a caídas: primero lee el en-vivo.json que ya está en S3; si una
    cámara no responde esta corrida, conserva lo que había (no borra el feed).

Uso:
  python3 tools/leyes-senado/leyes_en_vivo.py            # escribe local + baja PDFs a staging
  python3 tools/leyes-senado/leyes_en_vivo.py --upload   # + sube a S3 (aws cli)
  python3 tools/leyes-senado/leyes_en_vivo.py --only camara
"""
import argparse
import datetime as dt
import io
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')

SEN_API = 'https://leyes.senado.gov.co/api'
CAM_AJAX = 'https://www.camara.gov.co/wp-admin/admin-ajax.php'
CAM_PL_PAGE = 'https://www.camara.gov.co/secretaria/proyectos-de-ley'

LEG_SEN = '2026-2027'
LEG_CAM = '20'            # id interno de la legislatura 2026-2027 en camara.gov.co
N = 5                     # cuántos mostrar por cámara

# S3 (mismo prefijo público donde vive comisiones-2026.json)
S3_BUCKET = 'elecciones-2026'
S3_PREFIX = 'ricardoruiz.co/congreso-2026/output/legislativo'
PUBLIC_BASE = f'https://{S3_BUCKET}.s3.us-east-1.amazonaws.com/{S3_PREFIX}/'

# staging local (para la corrida CLI antes de subir con aws s3 cp)
REPO = Path(__file__).resolve().parents[2]
STAGE = REPO / 'Bases de datos' / 'leyes-senado' / 'en-vivo'

RE_TEXTO_RADICADO = re.compile(
    r"""id=['"]textoRadicadoBtn['"][^>]*?data-link=['"]([^'"]*)['"]""", re.I | re.S)
RE_PL_NONCE = re.compile(r"""PL_NONCE\s*[:=]\s*['"]([a-f0-9]+)['"]""", re.I)


# ─────────────────────────────────────────────────────────────── red
def http(url, data=None, headers=None, timeout=45, binary=False, retries=3):
    """GET/POST con urllib. data (dict) → POST urlencoded. Reintenta con backoff."""
    hdr = {'User-Agent': UA, 'Accept': '*/*'}
    if headers:
        hdr.update(headers)
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        hdr.setdefault('Content-Type', 'application/x-www-form-urlencoded')
    for intento in range(retries):
        try:
            req = urllib.request.Request(url, data=body, headers=hdr)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                blob = r.read()
                return blob if binary else blob.decode('utf-8', errors='replace')
        except Exception as e:                                    # noqa: BLE001
            if intento == retries - 1:
                print(f'  ! http fallo {url[:70]}: {e}', file=sys.stderr)
                return b'' if binary else ''
            time.sleep(1.5 * (intento + 1))
    return b'' if binary else ''


def slug(txt):
    import unicodedata
    txt = unicodedata.normalize('NFKD', str(txt)).encode('ascii', 'ignore').decode()
    return re.sub(r'[^A-Za-z0-9]+', '-', txt).strip('-').upper()


# ──────────────────────────────────────────────────────────── SENADO
def fetch_senado(n=N, delay=2.5):
    body = http(f'{SEN_API}/search_pdly.php', data={'legislatura': LEG_SEN})
    try:
        data = json.loads(body).get('data') or []
    except json.JSONDecodeError:
        print('  ! search_pdly no devolvió JSON', file=sys.stderr)
        return []
    # id ascendente = orden de radicación → los más nuevos son los id más altos
    data.sort(key=lambda r: int(r.get('id', 0)), reverse=True)
    out = []
    for r in data[:n]:
        rid = r.get('id')
        det = {}
        html = http(f'{SEN_API}/get_detalle_pdly.php?id={rid}')
        if html:
            m = RE_TEXTO_RADICADO.search(html)
            det['pdf_url'] = m.group(1).strip() if m else ''
            mf = re.search(r'Fecha de Presentaci[oó]n.*?(\d{4}[-/]\d{2}[-/]\d{2})', html, re.I | re.S)
            det['fecha'] = mf.group(1) if mf else ''
        out.append({
            'numero': r.get('numero_senado', '') or str(rid),
            'titulo': r.get('titulo', ''),
            'resumen': '',                       # Senado no trae objeto aparte; el título ES el objeto
            'autor': r.get('autor', ''),
            'comision': r.get('comision', ''),
            'fecha': det.get('fecha', ''),
            'estado': r.get('estado', ''),
            'tipo': r.get('tipo_de_ley', ''),
            'pdf_url': det.get('pdf_url', ''),   # URL de origen del PDF (se re-aloja en S3)
            'fuente': 'https://leyes.senado.gov.co/proyectos-de-ley',
            '_id': str(rid),
        })
        time.sleep(delay)
    return out


# ──────────────────────────────────────────────────────────── CÁMARA
def _col_idx(ref):
    col = re.match(r'[A-Z]+', ref or 'A')
    ci = 0
    for ch in (col.group(0) if col else 'A'):
        ci = ci * 26 + (ord(ch) - 64)
    return ci - 1


def _xlsx_rows(blob):
    """Lee un .xlsx (stdlib) → (filas como listas de strings, links{fila:{col:url}}).
    Los links salen de los <hyperlink> de la hoja resueltos contra sheet1.xml.rels
    (así se recupera la URL real de la ficha del proyecto, no un slug adivinado)."""
    z = zipfile.ZipFile(io.BytesIO(blob))
    ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    rns = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        root = ET.fromstring(z.read('xl/sharedStrings.xml'))
        for si in root.findall(f'{ns}si'):
            shared.append(''.join(t.text or '' for t in si.iter(f'{ns}t')))
    # rels: rId → target URL (para hyperlinks externos)
    rels = {}
    rp = 'xl/worksheets/_rels/sheet1.xml.rels'
    if rp in z.namelist():
        for r in ET.fromstring(z.read(rp)):
            rels[r.get('Id')] = r.get('Target')
    sheet = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
    rows = []
    rownum = 0
    for row in sheet.iter(f'{ns}row'):
        rownum += 1
        cells, maxc = {}, 0
        for c in row.findall(f'{ns}c'):
            ci = _col_idx(c.get('r', ''))
            v = c.find(f'{ns}v')
            txt = ''
            if v is not None and v.text is not None:
                txt = shared[int(v.text)] if c.get('t') == 's' else v.text
            cells[ci] = txt
            maxc = max(maxc, ci)
        rows.append([cells.get(i, '') for i in range(maxc + 1)])
    # hyperlinks: {rownum(1-based data-row) : {col_idx: url}}
    links = {}
    for hl in sheet.iter(f'{ns}hyperlink'):
        ref = hl.get('ref', '')
        rid = hl.get(f'{rns}id')
        url = rels.get(rid) or hl.get('location') or ''
        m = re.match(r'([A-Z]+)(\d+)', ref)
        if m and url:
            links.setdefault(int(m.group(2)), {})[_col_idx(m.group(1))] = url
    return rows, links


def _cam_pdf_from_page(page_url):
    """La ficha de un proyecto en camara.gov.co enlaza su PDF de texto radicado."""
    if not page_url:
        return ''
    html = http(page_url)
    if not html:
        return ''
    # el texto radicado suele venir como un <a href="...pdf"> con "radicado"/"texto" cerca,
    # o dentro de un iframe/visor. Se toma el primer PDF plausible.
    cands = re.findall(r'href=["\']([^"\']+\.pdf[^"\']*)["\']', html, re.I)
    if not cands:
        return ''
    pref = [u for u in cands if re.search(r'radicad|texto|proyecto', u, re.I)]
    return urllib.parse.urljoin(page_url, (pref or cands)[0])


def fetch_camara(n=N, delay=1.5):
    # nonce (opcional) desde la página; si no aparece, se manda vacío
    page = http(CAM_PL_PAGE)
    m = RE_PL_NONCE.search(page or '')
    nonce = m.group(1) if m else ''
    blob = http(CAM_AJAX, data={'action': 'download_proyectos_ley_xlsx',
                                'legislatura': LEG_CAM, 'nonce': nonce}, binary=True)
    if not blob or blob[:2] != b'PK':
        print('  ! Cámara no devolvió XLSX', file=sys.stderr)
        return []
    rows, links = _xlsx_rows(blob)
    if len(rows) < 2:
        return []                                  # solo cabecera → aún sin proyectos
    hdr = [str(c).strip() for c in rows[0]]

    def col(name):
        for i, h in enumerate(hdr):
            if h.lower().startswith(name.lower()):
                return i
        return -1
    ci = {k: col(v) for k, v in {
        'num': 'No. Cámara', 'fecha': 'Fecha Cámara', 'proyecto': 'Proyecto',
        'titulo': 'Título', 'objeto': 'Objeto', 'autores': 'Autores',
        'estado': 'Estado', 'tipo': 'Tipo', 'comision': 'Comisión', 'link': 'Link',
    }.items()}

    def get(row, key):
        i = ci.get(key, -1)
        return str(row[i]).strip() if 0 <= i < len(row) else ''

    li = ci.get('link', -1)
    out = []
    for ri, row in enumerate(rows[1:1 + n], start=2):   # fila 1 = cabecera; datos desde la 2
        # URL real de la ficha desde el hyperlink de la celda "Link del Proyecto"
        page_url = (links.get(ri, {}) or {}).get(li, '') if li >= 0 else ''
        comnum = re.search(r'(primera|segunda|tercera|cuarta|quinta|sexta|s[eé]ptima)',
                           get(row, 'comision'), re.I)
        out.append({
            'numero': get(row, 'num'),
            'titulo': get(row, 'titulo') or get(row, 'proyecto'),
            'resumen': get(row, 'objeto'),
            'autor': get(row, 'autores'),
            'comision': (comnum.group(1).upper() if comnum else get(row, 'comision')),
            'fecha': get(row, 'fecha'),
            'estado': get(row, 'estado'),
            'tipo': get(row, 'tipo'),
            'pdf_url': '',                          # se resuelve desde la ficha (abajo)
            'fuente': page_url or CAM_PL_PAGE,
            '_page': page_url,
        })
    # resolver PDFs desde la ficha (una petición por proyecto)
    for it in out:
        it['pdf_url'] = _cam_pdf_from_page(it.pop('_page', ''))
        time.sleep(delay)
    return out


# ──────────────────────────────────────────────────────────── S3 / PDFs
def s3_key_pdf(camara, numero):
    return f'{S3_PREFIX}/en-vivo/{camara}/{slug(numero)}.pdf'


def _boto3():
    try:
        import boto3
        return boto3.client('s3')
    except Exception:                              # noqa: BLE001
        return None


def rehost_pdfs(items, camara, s3):
    """Descarga el PDF de origen y lo re-aloja en S3 (idempotente: si ya está, lo reusa).
    Devuelve la ruta relativa (respecto de PUBLIC_BASE) para el JSON, o None."""
    for it in items:
        rel = f'en-vivo/{camara}/{slug(it["numero"])}.pdf'
        key = f'{S3_PREFIX}/{rel}'
        it['pdf'] = None
        if s3:                                     # ¿ya está en S3?
            try:
                s3.head_object(Bucket=S3_BUCKET, Key=key)
                it['pdf'] = rel
                continue
            except Exception:                      # noqa: BLE001
                pass
        url = it.get('pdf_url') or ''
        if not url:
            continue
        blob = http(urllib.parse.quote(url, safe=':/?=&%'), binary=True, timeout=120)
        if blob[:4] != b'%PDF':
            continue
        if s3:
            s3.put_object(Bucket=S3_BUCKET, Key=key, Body=blob,
                          ContentType='application/pdf',
                          CacheControl='public, max-age=300')
            it['pdf'] = rel
        else:                                      # CLI sin boto3 → staging local
            dst = STAGE / camara / f'{slug(it["numero"])}.pdf'
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(blob)
            it['pdf'] = rel
        time.sleep(1.0)
    for it in items:
        it.pop('pdf_url', None)
        it.pop('_id', None)
    return items


def load_previo(s3):
    """en-vivo.json actual en S3 (para conservar una cámara si esta corrida falla)."""
    try:
        if s3:
            o = s3.get_object(Bucket=S3_BUCKET, Key=f'{S3_PREFIX}/en-vivo.json')
            return json.loads(o['Body'].read())
        blob = http(PUBLIC_BASE + 'en-vivo.json', binary=True)
        return json.loads(blob) if blob else {}
    except Exception:                              # noqa: BLE001
        return {}


# ──────────────────────────────────────────────────────────── build
def build(only=None, upload=False):
    s3 = _boto3() if upload else None
    previo = load_previo(s3)
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

    result = {'actualizado': now, 'base_pdf': PUBLIC_BASE,
              'senado': previo.get('senado', []), 'camara': previo.get('camara', [])}

    if only in (None, 'senado'):
        try:
            sen = fetch_senado()
            if sen:
                result['senado'] = rehost_pdfs(sen, 'senado', s3)
        except Exception as e:                     # noqa: BLE001
            print(f'  ! senado falló, conservo lo previo: {e}', file=sys.stderr)
    if only in (None, 'camara'):
        try:
            cam = fetch_camara()
            # cám puede venir vacía legítimamente (aún sin radicados en 2026-2027):
            # solo se conserva lo previo si la petición REVENTÓ (excepción), no si
            # devolvió [] limpio.
            result['camara'] = rehost_pdfs(cam, 'camara', s3)
        except Exception as e:                     # noqa: BLE001
            print(f'  ! cámara falló, conservo lo previo: {e}', file=sys.stderr)

    payload = json.dumps(result, ensure_ascii=False, indent=1)
    if s3:
        s3.put_object(Bucket=S3_BUCKET, Key=f'{S3_PREFIX}/en-vivo.json',
                      Body=payload.encode('utf-8'), ContentType='application/json',
                      CacheControl='public, max-age=300')
    STAGE.mkdir(parents=True, exist_ok=True)
    (STAGE / 'en-vivo.json').write_text(payload, encoding='utf-8')
    return result


# ──────────────────────────────────────────────────────────── Lambda
def handler(event, context):                       # noqa: ARG001
    r = build(upload=True)
    return {'ok': True, 'senado': len(r['senado']), 'camara': len(r['camara']),
            'actualizado': r['actualizado']}


# ──────────────────────────────────────────────────────────── CLI
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', choices=['senado', 'camara'])
    ap.add_argument('--upload', action='store_true', help='sube a S3 (requiere boto3/creds)')
    args = ap.parse_args()
    r = build(only=args.only, upload=args.upload)
    print(f'· senado: {len(r["senado"])} · cámara: {len(r["camara"])} · {r["actualizado"]}')
    for cam in ('senado', 'camara'):
        for it in r[cam]:
            pdf = '✓pdf' if it.get('pdf') else '—'
            print(f'  [{cam[:3]}] {it["numero"]:>10}  {pdf}  {it["titulo"][:70]}')
    print(f'· staging → {STAGE.relative_to(REPO)}')
    if not args.upload:
        print('  (usa --upload para subir a S3, o aws s3 cp del staging)')


if __name__ == '__main__':
    main()
