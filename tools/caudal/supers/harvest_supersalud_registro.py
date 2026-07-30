#!/usr/bin/env python3
"""
Caudal · pilar Regulatorio — REGISTRO REAL de sanciones de Supersalud (vía 3).

El fetch_supersalud() de harvest_comunicados.py cosecha la SALA DE PRENSA
(Comunicaciones/Comunicados, ~16 sanciones publicitadas). Este script cosecha el
REGISTRO REAL: las resoluciones sancionatorias que Supersalud publica para
notificación en sus bibliotecas SharePoint. Son cientos, con títulos OPACOS
(número de resolución) → hay que LEER el PDF = pipeline PDF→DeepSeek, mismo
patrón que la fase 3 de gacetas del pilar Congreso (extraer_gaceta + acción
`gaceta` de la Lambda), pero corrido OFFLINE (como los demás harvesters de
supers) para producir el dataset y subir solo el resultado.

Bibliotecas fuente (body-match 'sancionatorio' en la SharePoint Search API):
  PortalWeb/Notificaciones/Por Aviso                (~544)  2016-2026
  PortalWeb/Notificaciones/NotificacionesPorAviso   (~184)  2017-2026
  PortalWeb/Juridica/Resoluciones                   (~72)   2005-2026

Comandos (resumible; cada fase deja su caché en disco):
  python3 tools/caudal/supers/harvest_supersalud_registro.py enumerate
      → manifest.json: candidatos dedup por nº de resolución
  python3 tools/caudal/supers/harvest_supersalud_registro.py download [--limit N]
      → baja PDFs + extrae texto (pypdf). Marca los escaneados (necesitan OCR).
  python3 tools/caudal/supers/harvest_supersalud_registro.py extract [--limit N]
      → DeepSeek por doc → esquema normalizado. Necesita DEEPSEEK_API_KEY en env.
        (se puede leer de la Lambda: ver README/nota al final.)
  python3 tools/caudal/supers/harvest_supersalud_registro.py stats

Salida final: RAW/supersalud-registro.json (filas YA en el esquema normalizado)
→ la recoge harvest_supers.py normalize (fuente 'supersalud-registro' con map
identidad en fuentes.json) → build_s3.py. Todo stdlib salvo pypdf.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = REPO / 'Bases de datos' / 'leyes-senado' / 'supers'
RAW = OUT / 'raw'
REG = OUT / 'registro'          # cache de esta cosecha (gitignored)
PDFDIR = REG / 'pdf'
TXTDIR = REG / 'txt'
EXDIR = REG / 'extract'         # una respuesta DeepSeek por doc (cache)
MANIFEST = REG / 'manifest.json'

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')

FOLDERS = [
    ('por-aviso', 'https://docs.supersalud.gov.co/PortalWeb/Notificaciones/Por Aviso'),
    ('notif-por-aviso', 'https://docs.supersalud.gov.co/PortalWeb/Notificaciones/NotificacionesPorAviso'),
    ('resoluciones', 'https://docs.supersalud.gov.co/PortalWeb/Juridica/Resoluciones'),
]
SEARCH = 'https://www.supersalud.gov.co/es-co/_api/search/query'
DEEPSEEK_MODEL = 'deepseek-v4-flash'
DEEPSEEK_URL = 'https://api.deepseek.com/chat/completions'


# ------------------------------------------------------------------ util
def _curl(url, timeout=90, binary=False, headers=None):
    cmd = ['/usr/bin/curl', '-s', '-A', UA, '--max-time', str(timeout), '-L']
    for k, v in (headers or {}).items():
        cmd += ['-H', f'{k}: {v}']
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout + 15)
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0:
        return None
    return r.stdout if binary else r.stdout.decode('utf-8', errors='replace')


# ------------------------------------------------------------- enumerate
def _search_all(qt, props='Title,Path,Write', cap=6000):
    rows, start, total = [], 0, 0
    while start < cap:
        url = (f"{SEARCH}?querytext='{quote(qt)}'&rowlimit=500&startrow={start}"
               f"&selectproperties='{quote(props)}'&trimduplicates=false")
        raw = _curl(url, headers={'Accept': 'application/json;odata=nometadata'})
        if raw is None:
            print('   ! search sin respuesta @', start, file=sys.stderr)
            break
        try:
            rr = json.loads(raw)['PrimaryQueryResult']['RelevantResults']
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print('   ! shape inesperado:', e, file=sys.stderr)
            break
        total = rr.get('TotalRows', 0)
        table = rr['Table']['Rows']
        for r in table:
            c = {x['Key']: x['Value'] for x in r['Cells']}
            rows.append({'title': c.get('Title') or '', 'path': c.get('Path') or '',
                         'write': (c.get('Write') or '')[:10]})
        start += len(table)
        if not table or start >= total:
            break
        time.sleep(0.25)
    return rows, total


# número de resolución para dedup. Tres familias (verificado en el manifest):
#   moderno: "resolución número 2024910030001372-6" / "No.20227200000058176"
#            (16-18 díg, a veces con sufijo -N de tipo de acto) → base de dígitos
#   PARL:    "Resolución No. PARL 001797 de 2016" → PARL-001797-2016
#   viejo:   "RESOLUCION N° 005720 DE 2017" → 005720-2017
# El citación + la notificación de una misma resolución comparten el nº → mismo key.
_RES_MODERNO = re.compile(r'(\d{13,20})')                       # base larga
_RES_PARL = re.compile(r'PARL\s*0*(\d{3,7})(?:\s+de\s+(\d{4}))?', re.I)
_RES_VIEJO = re.compile(r'resoluci[oó]n\s*(?:n[°º.]*\s*|no\.?\s*|n[uú]mero\s*)?'
                        r'(\d{3,7})\s+de\s+(\d{4})', re.I)


def _resnum(title, path):
    fn = path.rsplit('/', 1)[-1]
    hay = f'{title} {fn}'
    m = _RES_MODERNO.search(hay)             # el más específico primero (≥13 díg)
    if m:
        return m.group(1)
    m = _RES_PARL.search(hay)
    if m:
        return f'PARL-{int(m.group(1)):06d}' + (f'-{m.group(2)}' if m.group(2) else '')
    m = _RES_VIEJO.search(hay)
    if m:
        return f'{int(m.group(1)):06d}-{m.group(2)}'
    return None


# tipo de doc por el título: preferimos la NOTIFICACIÓN/RESOLUCIÓN sobre la
# CITACIÓN/COMUNICACIÓN (esas solo emplazan; la resolución trae el contenido).
def _docrank(title):
    t = title.lower()
    if t.startswith('resoluci') or 'resolución número' in t or 'resolucion numero' in t:
        return 3
    if 'notificaci' in t:
        return 2
    if 'comunicaci' in t:
        return 1
    return 0          # citación u otros


def cmd_enumerate():
    REG.mkdir(parents=True, exist_ok=True)
    cand = {}
    for slug, path in FOLDERS:
        rows, total = _search_all(f'sancionatorio path:"{path}"')
        pdfs = [r for r in rows if r['path'].lower().endswith('.pdf')]
        print(f'  {slug:18s} body-match sancionatorio: {total} · PDFs {len(pdfs)}')
        for r in pdfs:
            rn = _resnum(r['title'], r['path'])
            key = rn or ('path:' + r['path'])       # sin nº → su propia entrada
            entry = {'resolucion': rn, 'title': r['title'], 'path': r['path'],
                     'write': r['write'], 'folder': slug, 'rank': _docrank(r['title'])}
            prev = cand.get(key)
            # nos quedamos con el doc de mayor rank (resolución > notificación >
            # comunicación > citación); a igual rank, el más reciente.
            if (prev is None or entry['rank'] > prev['rank']
                    or (entry['rank'] == prev['rank'] and entry['write'] > prev['write'])):
                cand[key] = entry
    manifest = sorted(cand.values(), key=lambda e: (e['write'] or ''), reverse=True)
    for i, e in enumerate(manifest):
        e['id'] = f'sns-reg-{e["resolucion"] or f"x{i:04d}"}'
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8')
    con_num = sum(1 for e in manifest if e['resolucion'])
    print(f'\n  manifest: {len(manifest)} candidatos únicos (dedup por nº de '
          f'resolución) · con nº {con_num}')
    print(f'  → {MANIFEST.relative_to(REPO)}')


# -------------------------------------------------------------- download
def _extract_pdf_text(pdf_path):
    try:
        import pypdf
    except ImportError:
        print('  ! falta pypdf (pip install pypdf)', file=sys.stderr)
        raise
    try:
        r = pypdf.PdfReader(str(pdf_path))
        return '\n'.join((p.extract_text() or '') for p in r.pages)
    except Exception as e:
        return f'__ERROR_PYPDF__ {e}'


def cmd_download(limit=None):
    if not MANIFEST.exists():
        print('corre "enumerate" primero', file=sys.stderr); sys.exit(1)
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    PDFDIR.mkdir(parents=True, exist_ok=True)
    TXTDIR.mkdir(parents=True, exist_ok=True)
    done = ok = scan = fail = 0
    for e in manifest:
        txt_path = TXTDIR / f'{e["id"]}.txt'
        if txt_path.exists():
            continue                       # resumible
        if limit and done >= limit:
            break
        done += 1
        # los Path de SharePoint traen espacios y acentos LITERALES → curl los
        # rechaza; hay que codificarlos (safe=':/%' preserva estructura y lo ya
        # pre-codificado). Verificado: sin esto, 725 KB de PDF llegan como 0 bytes.
        raw = _curl(quote(e['path'], safe=':/%'), binary=True)
        if raw is None or not raw[:5].startswith(b'%PDF'):
            print(f'  ! {e["id"]}: descarga falló'); fail += 1
            time.sleep(0.3); continue
        pdf_path = PDFDIR / f'{e["id"]}.pdf'
        pdf_path.write_bytes(raw)
        txt = _extract_pdf_text(pdf_path)
        txt_path.write_text(txt, encoding='utf-8')
        digital = len(txt) > 500 and not txt.startswith('__ERROR_PYPDF__')
        if digital:
            ok += 1
        else:
            scan += 1
            print(f'  ~ {e["id"]}: {len(txt)} chars → escaneado/ilegible (OCR pendiente)')
        # el PDF ya no se necesita (guardamos el texto); borrarlo ahorra disco
        pdf_path.unlink(missing_ok=True)
        if done % 25 == 0:
            print(f'  ... {done} procesados (ok {ok} · escaneados {scan} · fallos {fail})')
        time.sleep(0.35)
    print(f'\n  descargados esta corrida: {done} · digitales {ok} · '
          f'escaneados {scan} · fallos {fail}')
    total_txt = len(list(TXTDIR.glob("*.txt")))
    print(f'  textos en cache: {total_txt} / {len(manifest)} del manifest')


# --------------------------------------------------------------- extract
SNS_REG_SYSTEM = (
    "Eres analista del pilar regulatorio de Cauce. Te doy el TEXTO de un documento "
    "de la Superintendencia Nacional de Salud de Colombia (una resolución "
    "sancionatoria o su notificación/citación por aviso). Tu tarea: extraer la "
    "sanción de forma estructurada. REGLA DURA: usa SOLO lo que dice el texto; si "
    "un dato no aparece, ponlo en null. NO inventes montos, nombres ni NIT.\n"
    "Devuelves SIEMPRE un JSON válido con estas claves:\n"
    "- es_sancion: true si el acto IMPONE o CONFIRMA una sanción (multa, "
    "amonestación, etc.) a una entidad o persona vigilada; false si es apertura de "
    "investigación / formulación de pliego de cargos / archivo / exoneración / "
    "revocatoria / acto no sancionatorio.\n"
    "- tipo_acto: 'sancion_impuesta' | 'apertura_investigacion' | 'archivo' | "
    "'confirma_sancion' | 'revoca' | 'otro'.\n"
    "- sancionado: razón social o nombre de la entidad/persona sancionada (o "
    "investigada), null si no aparece.\n"
    "- identificacion: NIT o cédula si aparece, si no null.\n"
    "- tipo_sancion: 'Multa' | 'Amonestación escrita' | 'Otra' | null.\n"
    "- monto_cop: valor de la multa en pesos colombianos como NÚMERO entero sin "
    "puntos ni símbolos (ej 250000000), null si no hay multa o no se indica.\n"
    "- motivo: por qué se sanciona/investiga, en una frase breve, null si no está.\n"
    "- resolucion: número y año de la resolución (ej '005720 de 2017'), null si no.\n"
    "- fecha: fecha del acto en formato YYYY-MM-DD, null si no se puede.\n"
    "- estado: 'en firme' | 'notificada' | 'recurrible' | 'ejecutoriada' | null.\n"
    "- resumen: 1 frase describiendo el acto."
)


def _deepseek(system, user, max_tokens=2000, timeout=90):
    key = os.environ.get('DEEPSEEK_API_KEY')
    if not key:
        raise RuntimeError(
            'DEEPSEEK_API_KEY no está en el entorno. Léela de la Lambda:\n'
            "  export DEEPSEEK_API_KEY=$(aws lambda get-function-configuration "
            "--function-name caudal-analiza --query 'Environment.Variables.DEEPSEEK_API_KEY' --output text)")
    import urllib.request
    body = json.dumps({
        'model': DEEPSEEK_MODEL,
        'messages': [{'role': 'system', 'content': system},
                     {'role': 'user', 'content': user}],
        'temperature': 0.2, 'max_tokens': max_tokens,
        'response_format': {'type': 'json_object'},
    }).encode('utf-8')
    req = urllib.request.Request(
        DEEPSEEK_URL, data=body,
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    return d['choices'][0]['message']['content']


def _to_normalized(ex, e):
    """DeepSeek dict + entrada del manifest → fila en el esquema normalizado."""
    monto = ex.get('monto_cop')
    if isinstance(monto, str):
        monto = re.sub(r'[^\d]', '', monto) or None
        monto = float(monto) if monto else None
    return {
        'sancionado': ex.get('sancionado'),
        'identificacion': ex.get('identificacion'),
        'tipo_sancion': ex.get('tipo_sancion') or ('Multa' if monto else 'Sanción'),
        'motivo': ex.get('motivo'),
        'monto': monto,
        'resolucion': ex.get('resolucion') or (e.get('resolucion') or ''),
        'fecha_firmeza': ex.get('fecha') or (e.get('write') or None),
        'estado': ex.get('estado'),
        'descripcion': ex.get('resumen'),
        'url': e['path'],
        '_id': e['id'],
    }


def cmd_extract(limit=None):
    if not MANIFEST.exists():
        print('corre "enumerate" + "download" primero', file=sys.stderr); sys.exit(1)
    manifest = {e['id']: e for e in json.loads(MANIFEST.read_text(encoding='utf-8'))}
    EXDIR.mkdir(parents=True, exist_ok=True)
    txts = sorted(TXTDIR.glob('*.txt'))
    done = kept = drop = err = 0
    for tp in txts:
        doc_id = tp.stem
        e = manifest.get(doc_id)
        if e is None:
            continue
        cache = EXDIR / f'{doc_id}.json'
        if cache.exists():
            continue                       # resumible
        if limit and done >= limit:
            break
        txt = tp.read_text(encoding='utf-8')
        if len(txt) < 500 or txt.startswith('__ERROR_PYPDF__'):
            continue                       # escaneado: se salta (OCR aparte)
        done += 1
        user = (f"Documento (resolución {e.get('resolucion') or '?'}, "
                f"{e['folder']}):\n\n{txt[:30000]}")
        try:
            raw = _deepseek(SNS_REG_SYSTEM, user).strip()
            if raw.startswith('```'):
                raw = raw.split('```')[1].lstrip('json').strip()
            ex = json.loads(raw)
        except Exception as exn:
            print(f'  ! {doc_id}: extracción falló ({str(exn)[:100]})'); err += 1
            time.sleep(1); continue
        cache.write_text(json.dumps(ex, ensure_ascii=False), encoding='utf-8')
        if ex.get('es_sancion'):
            kept += 1
        else:
            drop += 1
        if done % 25 == 0:
            print(f'  ... {done} extraídos (sanciones {kept} · no-sanción {drop} · err {err})')
        time.sleep(0.4)
    _consolidar(manifest)
    print(f'\n  extraídos esta corrida: {done} · sanciones {kept} · '
          f'no-sanción {drop} · err {err}')


def _consolidar(manifest):
    """Junta todas las extracciones cacheadas que SON sanción → raw JSON."""
    rows = []
    for cache in sorted(EXDIR.glob('*.json')):
        ex = json.loads(cache.read_text(encoding='utf-8'))
        if not ex.get('es_sancion'):
            continue
        e = manifest.get(cache.stem)
        if e is None:
            continue
        rows.append(_to_normalized(ex, e))
    (RAW / 'supersalud-registro.json').write_text(
        json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    con_m = sum(1 for r in rows if r['monto'])
    print(f'  consolidado: {len(rows)} sanciones ({con_m} con monto) → '
          f'{(RAW / "supersalud-registro.json").relative_to(REPO)}')


def cmd_stats():
    if MANIFEST.exists():
        m = json.loads(MANIFEST.read_text(encoding='utf-8'))
        print(f'manifest: {len(m)} candidatos')
    print(f'textos descargados: {len(list(TXTDIR.glob("*.txt"))) if TXTDIR.exists() else 0}')
    print(f'extracciones: {len(list(EXDIR.glob("*.json"))) if EXDIR.exists() else 0}')
    reg = RAW / 'supersalud-registro.json'
    if reg.exists():
        rows = json.loads(reg.read_text(encoding='utf-8'))
        con_m = sum(1 for r in rows if r['monto'])
        print(f'consolidado (sanciones): {len(rows)} · con monto {con_m}')


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('enumerate')
    dp = sub.add_parser('download'); dp.add_argument('--limit', type=int)
    xp = sub.add_parser('extract'); xp.add_argument('--limit', type=int)
    sub.add_parser('stats')
    a = ap.parse_args()
    if a.cmd == 'enumerate':
        cmd_enumerate()
    elif a.cmd == 'download':
        cmd_download(a.limit)
    elif a.cmd == 'extract':
        cmd_extract(a.limit)
    else:
        cmd_stats()


if __name__ == '__main__':
    main()
