#!/usr/bin/env python3
"""
Caudal · pilar Regulatorio — REGISTRO REAL de ACTOS de Supersalud (vía 3).

El fetch_supersalud() de harvest_comunicados.py cosecha la SALA DE PRENSA
(Comunicaciones/Comunicados, ~16 sanciones publicitadas). Este script cosecha el
REGISTRO REAL: los actos administrativos que Supersalud publica para
notificación en sus bibliotecas SharePoint. Son cientos, con títulos OPACOS
(número de resolución) → hay que LEER el PDF = pipeline PDF→DeepSeek, mismo
patrón que la fase 3 de gacetas del pilar Congreso (extraer_gaceta + acción
`gaceta` de la Lambda), pero corrido OFFLINE (como los demás harvesters de
supers) para producir el dataset y subir solo el resultado.

REENCUADRE jul-2026 — el pilar es "actos regulatorios", no solo "sanciones".
Medido sobre una muestra de 12: CERO sanciones reales; todo eran actos
procesales (archivo, apertura de investigación, contribución especial). Antes
esos se DESCARTABAN; ahora se conservan TODOS y se tipan con `tipo_acto`:

    sancion · apertura_investigacion · archivo · contribucion_especial ·
    resolucion · circular · otro

El cliente quiere ver toda la actividad del Estado sobre su sector, no solo las
multas. La vista de sanciones se preserva filtrando `tipo_acto == 'sancion'`.

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
from collections import Counter
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

# Sube PROMPT_VERSION al cambiar SNS_REG_SYSTEM: las extracciones cacheadas con
# versión vieja se re-piden solas (mismo criterio que el PROMPT_VERSION de la
# Lambda). v1 = prompt "solo sanciones"; v2 = prompt de actos regulatorios.
PROMPT_VERSION = 'v2'

# Taxonomía canónica del pilar. El modelo devuelve un vocabulario más granular
# (y el prompt v1 usaba otro) → _norm_tipo_acto() colapsa ambos a estos 7.
TIPOS_ACTO = ('sancion', 'apertura_investigacion', 'archivo',
              'contribucion_especial', 'resolucion', 'circular', 'otro')


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
    "Eres analista del pilar regulatorio de Cauce. Te doy el TEXTO de un acto "
    "administrativo de la Superintendencia Nacional de Salud de Colombia (una "
    "resolución, o su notificación/citación por aviso). Tu tarea: extraer el acto "
    "de forma estructurada, SEA O NO una sanción — nos interesa toda la actividad "
    "regulatoria sobre los vigilados, no solo las multas. REGLA DURA: usa SOLO lo "
    "que dice el texto; si un dato no aparece, ponlo en null. NO inventes montos, "
    "nombres ni NIT.\n"
    "Devuelves SIEMPRE un JSON válido con estas claves:\n"
    "- tipo_acto: clasifica el acto en UNA de estas categorías:\n"
    "    'sancion' — IMPONE o CONFIRMA una sanción (multa, amonestación) a un "
    "vigilado.\n"
    "    'apertura_investigacion' — abre investigación o formula pliego de cargos.\n"
    "    'archivo' — archiva la actuación, exonera, revoca o desiste.\n"
    "    'contribucion_especial' — liquida, cobra o ajusta la contribución especial "
    "a favor de la Supersalud (es un TRIBUTO de los vigilados, NUNCA una multa).\n"
    "    'resolucion' — otra resolución administrativa de contenido general o "
    "particular que no cae en las anteriores (habilitaciones, medidas especiales, "
    "liquidaciones de entidades, nombramientos).\n"
    "    'circular' — circular externa o instrucción a los vigilados.\n"
    "    'otro' — no se puede determinar.\n"
    "- es_sancion: true SOLO si tipo_acto es 'sancion'. Sirve de verificación.\n"
    "- entidad: razón social o nombre de la entidad/persona DESTINATARIA del acto "
    "(sancionada, investigada, o a quien se le liquida la contribución). Ponla "
    "SIEMPRE que aparezca, sea o no una sanción. null si no aparece.\n"
    "- identificacion: NIT o cédula si aparece, si no null.\n"
    "- tipo_sancion: 'Multa' | 'Amonestación escrita' | 'Otra' | null. Solo si "
    "tipo_acto es 'sancion'; en cualquier otro caso null.\n"
    "- monto_cop: valor en pesos colombianos como NÚMERO entero sin puntos ni "
    "símbolos (ej 250000000). Solo el monto de una MULTA o de la contribución "
    "liquidada; null si el acto no fija un valor.\n"
    "- motivo: por qué se sanciona / investiga / se expide el acto, en una frase "
    "breve, null si no está.\n"
    "- resolucion: número y año de la resolución (ej '005720 de 2017'), null si no.\n"
    "- fecha: fecha del acto en formato YYYY-MM-DD, null si no se puede.\n"
    "- estado: 'en firme' | 'notificada' | 'recurrible' | 'ejecutoriada' | null.\n"
    "- resumen: 1 frase describiendo el acto."
)

# El modelo (y el prompt v1) usan vocabularios más granulares → se colapsan a
# TIPOS_ACTO. Todo lo que no matchee cae a 'otro' (nunca se inventa un tipo).
_TIPO_ALIAS = {
    # v1 (prompt viejo, para que las extracciones cacheadas sigan sirviendo)
    'sancion_impuesta': 'sancion', 'confirma_sancion': 'sancion',
    'revoca': 'archivo',
    # variantes que el modelo produce con el prompt v2
    'sanción': 'sancion', 'multa': 'sancion',
    'apertura_de_investigacion': 'apertura_investigacion',
    'pliego_de_cargos': 'apertura_investigacion',
    'investigacion': 'apertura_investigacion',
    'archivo_actuacion': 'archivo', 'exoneracion': 'archivo',
    'contribucion': 'contribucion_especial',
    'contribución_especial': 'contribucion_especial',
    'circular_externa': 'circular',
}


def _norm_tipo_acto(v, es_sancion=None):
    """Vocabulario del modelo → uno de TIPOS_ACTO. Nunca inventa: cae a 'otro'."""
    t = (v or '').strip().lower().replace(' ', '_').replace('-', '_')
    t = _TIPO_ALIAS.get(t, t)
    if t in TIPOS_ACTO:
        return t
    # sin tipo utilizable, el booleano de verificación es el último recurso
    return 'sancion' if es_sancion else 'otro'


# max_tokens 6000, NO 2000: V4 gasta el presupuesto en reasoning y con 2000
# devolvía `content` vacío con finish_reason=length en 7 de 20 docs (medido —
# es el mismo gotcha que la síntesis de la Lambda). El costo no sube por el
# techo: solo se cobran los tokens realmente generados.
def _deepseek(system, user, max_tokens=6000, timeout=120):
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
    ch = d['choices'][0]
    # el usage sirve para reportar costo real de la corrida (no estimarlo)
    return ch['message']['content'], (d.get('usage') or {}), ch.get('finish_reason')


def _extraer_doc(user):
    """Una extracción, con reintento de presupuesto si el modelo se trunca.

    Aun con 6000 el reasoning agota el budget en ~10% de los docs y deja el
    JSON a medias (`finish_reason='length'`) — se reintenta con el doble antes
    de darlo por perdido. Devuelve (dict, usage_acumulado).
    """
    tot = {'prompt_tokens': 0, 'completion_tokens': 0}
    for max_tok in (6000, 12000):
        raw, usage, fin = _deepseek(SNS_REG_SYSTEM, user, max_tokens=max_tok)
        tot['prompt_tokens'] += usage.get('prompt_tokens', 0)
        tot['completion_tokens'] += usage.get('completion_tokens', 0)
        raw = (raw or '').strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1].lstrip('json').strip()
        if fin == 'length' and not raw.endswith('}'):
            continue                        # truncado: se reintenta más ancho
        return json.loads(raw), tot
    raise ValueError(f'truncado dos veces (finish_reason=length, {max_tok} tokens)')


# rótulo legible del acto cuando NO es sanción (el campo `tipo_sancion` del
# esquema normalizado pasa a ser "qué es este acto" — lo pinta el frontend).
_TIPO_TXT = {
    'apertura_investigacion': 'Apertura de investigación',
    'archivo': 'Archivo / exoneración',
    'contribucion_especial': 'Contribución especial',
    'resolucion': 'Resolución', 'circular': 'Circular', 'otro': 'Acto administrativo',
}


def _to_normalized(ex, e):
    """DeepSeek dict + entrada del manifest → fila en el esquema normalizado."""
    monto = ex.get('monto_cop')
    if isinstance(monto, str):
        monto = re.sub(r'[^\d]', '', monto) or None
        monto = float(monto) if monto else None
    tipo_acto = _norm_tipo_acto(ex.get('tipo_acto'), ex.get('es_sancion'))
    if tipo_acto == 'sancion':
        tipo_txt = ex.get('tipo_sancion') or ('Multa' if monto else 'Sanción')
    else:
        tipo_txt = _TIPO_TXT.get(tipo_acto, 'Acto administrativo')
    return {
        # `sancionado` conserva el nombre del esquema (no romper Lambda/frontend),
        # pero su semántica es "entidad destinataria del acto".
        'sancionado': ex.get('entidad') or ex.get('sancionado'),
        'identificacion': ex.get('identificacion'),
        'tipo_acto': tipo_acto,
        'tipo_sancion': tipo_txt,
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
    done = err = 0
    tipos = Counter()
    tok_in = tok_out = 0
    for tp in txts:
        doc_id = tp.stem
        e = manifest.get(doc_id)
        if e is None:
            continue
        cache = EXDIR / f'{doc_id}.json'
        if cache.exists():
            # resumible, pero solo si la extracción es de este prompt: al subir
            # PROMPT_VERSION las viejas se re-piden solas.
            try:
                prev = json.loads(cache.read_text(encoding='utf-8'))
            except json.JSONDecodeError:
                prev = {}
            if prev.get('_pv') == PROMPT_VERSION:
                continue
        if limit and done >= limit:
            break
        txt = tp.read_text(encoding='utf-8')
        if len(txt) < 500 or txt.startswith('__ERROR_PYPDF__'):
            continue                       # escaneado: se salta (OCR aparte)
        done += 1
        user = (f"Documento (resolución {e.get('resolucion') or '?'}, "
                f"{e['folder']}):\n\n{txt[:30000]}")
        try:
            ex, usage = _extraer_doc(user)
        except Exception as exn:
            print(f'  ! {doc_id}: extracción falló ({str(exn)[:100]})'); err += 1
            time.sleep(1); continue
        tok_in += usage.get('prompt_tokens', 0)
        tok_out += usage.get('completion_tokens', 0)
        ex['_pv'] = PROMPT_VERSION
        cache.write_text(json.dumps(ex, ensure_ascii=False), encoding='utf-8')
        tipos[_norm_tipo_acto(ex.get('tipo_acto'), ex.get('es_sancion'))] += 1
        if done % 25 == 0:
            print(f'  ... {done} extraídos · {dict(tipos)} · err {err}')
        time.sleep(0.4)
    _consolidar(manifest)
    print(f'\n  extraídos esta corrida: {done} · err {err}')
    for t, n in tipos.most_common():
        print(f'    {t:24s} {n:>4d}')
    if tok_in or tok_out:
        # tarifa DeepSeek V4 Flash (USD por 1M tokens) — si cambia, ajustar.
        usd = tok_in / 1e6 * 0.28 + tok_out / 1e6 * 0.42
        print(f'  tokens: {tok_in:,} in · {tok_out:,} out  ≈ USD {usd:.4f} '
              f'({usd / max(done, 1):.5f}/doc)')


def _consolidar(manifest):
    """Junta TODAS las extracciones cacheadas (sanción o no) → raw JSON.

    Antes filtraba por es_sancion y tiraba el 95% del material. Con el
    reencuadre a "actos regulatorios" se conserva todo, tipado con tipo_acto;
    la vista de sanciones filtra río abajo (Lambda), no aquí.
    """
    rows = []
    for cache in sorted(EXDIR.glob('*.json')):
        try:
            ex = json.loads(cache.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            continue
        e = manifest.get(cache.stem)
        if e is None:
            continue
        rows.append(_to_normalized(ex, e))
    (RAW / 'supersalud-registro.json').write_text(
        json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    tipos = Counter(r['tipo_acto'] for r in rows)
    con_m = sum(1 for r in rows if r['monto'])
    print(f'  consolidado: {len(rows)} actos ({tipos.get("sancion", 0)} sanciones · '
          f'{con_m} con monto) → {(RAW / "supersalud-registro.json").relative_to(REPO)}')


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
        print(f'consolidado (actos): {len(rows)} · con monto {con_m}')
        for t, n in Counter(r.get('tipo_acto', 'otro') for r in rows).most_common():
            print(f'  {t:24s} {n:>4d}')


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
