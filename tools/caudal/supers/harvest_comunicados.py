#!/usr/bin/env python3
"""
Caudal · harvester de sanciones anunciadas en COMUNICADOS OFICIALES (vía 2).

Tres superintendencias no publican un registro estructurado de sanciones, pero
sí las anuncian en comunicados oficiales con titulares muy estructurados
("X impone multa de $211 millones a la empresa Y por Z"). Este harvester las
cosecha de la fuente oficial de cada una y extrae sancionado/monto/tipo del
titular por regex (determinista, sin LLM; lo que el regex no saca queda None
y el titular completo va en `titulo` → campo `motivo` del esquema común):

  supertransporte  WordPress REST (?rest_route=/wp/v2/posts, paginado, BOM utf-8-sig)
  sic              listado Drupal /noticias?page=N (~180 páginas; título en
                   <div class="titulo"><a>); fecha del detalle solo para los hits
  supersalud       SharePoint Search API ANÓNIMA (/es-co/_api/search/query) con
                   filtro path a docs.supersalud.gov.co/PortalWeb/Comunicaciones/
                   Comunicados — hallazgo jul-2026: la _api responde sin auth,
                   misma clase de descubrimiento que la api-key de la SFC

OJO semántica: `fecha` es la del COMUNICADO (no la firmeza del acto) y el
registro es el ANUNCIO oficial de la sanción, no la resolución misma — cada
fila trae `url` a la fuente para el que quiera el acto completo.

Uso:
  python3 tools/caudal/supers/harvest_comunicados.py test          # parseo de titulares
  python3 tools/caudal/supers/harvest_comunicados.py fetch         # las 3 fuentes
  python3 tools/caudal/supers/harvest_comunicados.py fetch sic
Luego:
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
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RAW = REPO / 'Bases de datos' / 'leyes-senado' / 'supers' / 'raw'

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')

# filtro de titulares en 3 capas: keyword amplia → verbo de acción
# sancionatoria → sin ruido (alertas, balances, pedagogía, exoneraciones)
KW_RE = re.compile(r'\b(multa[sd]?[oó]?|mult[oó]|sanci[oó]n|sanciones|sanciona(?:ron)?|sancion[oó]|sancionad[oa]s?)\b', re.I)
ACTION_RE = re.compile(
    r'(sancion(?:a|[oó]|an|aron|ad[oa]s?)\b|sanci[oó]n(?:es)?\s+(?:a|al|contra)\b'
    r'|impuso|impone[n]?|impuesto|mult[oó]\b'
    r'|multa[s]?\s+(?:de|con|a|al|contra|por)\b|deja[n]?\s+en\s+firme|queda[n]?\s+en\s+firme|confirma)', re.I)
NOISE_RE = re.compile(
    r'(alerta|llamado|recuerda|recomendaci|exonera|evaluar[áa]?\s+multas|gracias\s+a'
    r'|fraudulent|ha\s+adelantado|profiri[oó]\s+\d|rindi[oó]\s+cuentas'
    r'|en\s+sus\s+primeros|en\s+lo\s+corrido|r[eé]cord|prioriz[oó])', re.I)


def es_sancion(titulo):
    return bool(KW_RE.search(titulo) and ACTION_RE.search(titulo)
                and not NOISE_RE.search(titulo))


def _curl(url, headers=None, timeout=60):
    cmd = ['/usr/bin/curl', '-s', '-A', UA, '--max-time', str(timeout), '-L']
    for k, v in (headers or {}).items():
        cmd += ['-H', f'{k}: {v}']
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout + 10)
    except subprocess.TimeoutExpired:
        return None
    return r.stdout if r.returncode == 0 else None


# ---------------------------------------------------------------- titulares

MONTO_RE = re.compile(
    r'\$\s*([\d][\d.,]*)\s*(mil\s+millones|millones(?:\s+de\s+pesos)?|mil)?', re.I)

# tras un verbo de sanción, "... a/al/contra <NOMBRE>" hasta el conector
# siguiente. OJO: ni el gap ni el corte usan '.' — los montos ($4.060) y las
# razones sociales (S.A.S.) traen puntos internos y se partirían.
SANC_RE = re.compile(
    r'(?:multa[s]?|sanci[oó]n(?:es)?|sanciona(?:ron)?|sancion[oó]|mult[oó]|sancionad[oa]s?)'
    r'[^;]{0,60}?\s+(?:al?|contra)\s+'
    r'(.+?)(?=\s+por\s|\s+con\s+(?:multa|\$)|\s+tras\s|\s+luego\s|\s+debido\s'
    r'|\s+y\s+(?:a\s|le[s]?\s|orden|abr)|\s+e\s+inicia\s|[,;]|$)',
    re.I)

_ART_RE = re.compile(r'^(?:la|el|los|las|una?|otros?)\s+', re.I)
_PREF_RE = re.compile(r'^(?:empresa[s]?|firma|sociedad)\s+', re.I)


def parse_monto(titulo):
    """'$ 4.060 millones' -> 4060000000.0 (COP). None si no hay cifra."""
    m = MONTO_RE.search(titulo)
    if not m:
        return None
    num = m.group(1).rstrip('.,')
    # formato colombiano: punto=miles, coma=decimal
    num = num.replace('.', '').replace(',', '.')
    try:
        v = float(num)
    except ValueError:
        return None
    unit = (m.group(2) or '').lower()
    if unit.startswith('mil millones'):
        v *= 1e9
    elif unit.startswith('millones'):
        v *= 1e6
    elif unit == 'mil':
        v *= 1e3
    return v if 0 < v < 1e15 else None


def parse_sancionado(titulo):
    m = SANC_RE.search(titulo)
    if not m:
        return None
    s = m.group(1).strip()
    s = _ART_RE.sub('', s)
    s = _PREF_RE.sub('', s).strip(' "“”')
    # descartes: capturas vacías, genéricas o kilométricas
    if not (3 <= len(s) <= 90):
        return None
    if re.fullmatch(r'(?:nivel\s+)?nacional|usuarios|ciudadan[oa]s.*|colombia', s, re.I):
        return None
    return s


def parse_titulo(titulo):
    t = re.sub(r'\s+', ' ', titulo).strip()
    tipo = 'Multa' if re.search(r'\bmulta', t, re.I) else 'Sanción'
    estado = 'En firme' if re.search(r'(deja en firme|confirma|queda en firme)', t, re.I) else 'Anunciada'
    return {
        'titulo': t,
        'sancionado': parse_sancionado(t),
        'monto': parse_monto(t),
        'tipo': f'{tipo} (comunicado oficial)',
        'estado': estado,
    }


# ---------------------------------------------------------------- fuentes

def _st_get(query):
    """GET al WP REST de supertransporte -> list de posts, dict (fin de
    paginación) o None (error). BOM utf-8-sig (gotcha conocido del portal)."""
    raw = _curl(f'https://www.supertransporte.gov.co/?rest_route=/wp/v2/posts&{query}')
    if raw is None:
        return None
    try:
        return json.loads(raw.decode('utf-8-sig'))
    except json.JSONDecodeError:
        return None  # el 500 de WP devuelve HTML


def fetch_supertransporte():
    """WP REST paginado. Algunas ventanas dan 500 persistente (post corrupto
    del lado del servidor, visto page=9 jul-2026): esa ventana se rescata en
    sub-bloques de 10 vía offset y se sigue con la página siguiente."""
    rows, page = [], 1

    def add(posts):
        for p in posts:
            titulo = html.unescape(p.get('title', {}).get('rendered', '') or '')
            if not es_sancion(titulo):
                continue
            rec = parse_titulo(titulo)
            rec['url'] = p.get('link', '')
            rec['fecha'] = (p.get('date') or '')[:10]
            rec['id'] = f"st-{p.get('id')}"
            rows.append(rec)

    while True:
        data = _st_get(f'per_page=100&page={page}')
        if data is None:  # reintento y, si persiste, rescate por sub-bloques
            time.sleep(1)
            data = _st_get(f'per_page=100&page={page}')
        if isinstance(data, dict) or data == []:
            break  # rest_post_invalid_page_number → se acabaron las páginas
        if data is None:
            base = (page - 1) * 100
            saved = 0
            for sub in range(10):
                chunk = _st_get(f'per_page=10&offset={base + sub * 10}')
                if isinstance(chunk, list):
                    add(chunk)
                    saved += len(chunk)
                time.sleep(0.2)
            print(f'  supertransporte page {page}: 500 persistente, '
                  f'rescatados {saved}/100 por offset')
            page += 1
            continue
        add(data)
        print(f'  supertransporte page {page}: {len(data)} posts, acumulados {len(rows)} hits')
        if len(data) < 100:
            break
        page += 1
        time.sleep(0.2)
    return rows


SIC_ITEM_RE = re.compile(
    r'<div class="titulo[^"]*">\s*<a href="([^"]+)"[^>]*>(.*?)</a>', re.S)
SIC_PAGER_RE = re.compile(r'/noticias\?page=(\d+)')

# la fecha del detalle vive en el dateline del cuerpo ("Bogotá D.C.,
# Noviembre 1 de 2023" / "1° de noviembre de 2023"), no en markup dc:date
_MESES = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5,
          'junio': 6, 'julio': 7, 'agosto': 8, 'septiembre': 9,
          'octubre': 10, 'noviembre': 11, 'diciembre': 12}
_MES_ALT = '|'.join(_MESES)
SIC_FECHA_RES = [
    re.compile(r'datatype="xsd:dateTime" content="(\d{4})-(\d{2})-(\d{2})'),
    re.compile(rf'({_MES_ALT})\s+(\d{{1,2}})°?\s+de\s+(\d{{4}})', re.I),
    re.compile(rf'(\d{{1,2}})°?\s+de\s+({_MES_ALT})\s+de\s+(\d{{4}})', re.I),
]


def _sic_fecha(page_html):
    for i, rx in enumerate(SIC_FECHA_RES):
        m = rx.search(page_html)
        if not m:
            continue
        g = m.groups()
        try:
            if i == 0:
                y, mo, d = int(g[0]), int(g[1]), int(g[2])
            elif i == 1:
                y, mo, d = int(g[2]), _MESES[g[0].lower()], int(g[1])
            else:
                y, mo, d = int(g[2]), _MESES[g[1].lower()], int(g[0])
            if 2000 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
                return f'{y:04d}-{mo:02d}-{d:02d}'
        except (ValueError, KeyError):
            continue
    return None


def fetch_sic():
    """Listado Drupal paginado; fecha del detalle solo para los hits."""
    base = 'https://www.sic.gov.co'
    first = _curl(f'{base}/noticias')
    if first is None:
        print('  ! sic: no responde /noticias', file=sys.stderr)
        return []
    first = first.decode('utf-8', errors='replace')
    last_page = max((int(m) for m in SIC_PAGER_RE.findall(first)), default=0)
    print(f'  sic: {last_page + 1} páginas de listado')

    hits, seen = [], set()

    def scan(page_html):
        for href, txt in SIC_ITEM_RE.findall(page_html):
            titulo = html.unescape(re.sub(r'<[^>]+>', ' ', txt))
            titulo = re.sub(r'\s+', ' ', titulo).strip()
            if not titulo or href in seen or not es_sancion(titulo):
                continue
            seen.add(href)
            rec = parse_titulo(titulo)
            rec['url'] = href if href.startswith('http') else base + href
            rec['fecha'] = None       # se completa abajo
            rec['id'] = f'sic-{href}'
            hits.append(rec)

    scan(first)
    for page in range(1, last_page + 1):
        raw = _curl(f'{base}/noticias?page={page}')
        if raw is None:
            print(f'  ! sic: falló page={page}, sigo', file=sys.stderr)
            continue
        scan(raw.decode('utf-8', errors='replace'))
        if page % 20 == 0:
            print(f'  sic page {page}/{last_page}: {len(hits)} hits')
        time.sleep(0.15)

    # fecha del detalle, solo para los hits
    for i, rec in enumerate(hits):
        raw = _curl(rec['url'], timeout=30)
        if raw:
            rec['fecha'] = _sic_fecha(raw.decode('utf-8', errors='replace'))
        if (i + 1) % 25 == 0:
            print(f'  sic fechas: {i + 1}/{len(hits)}')
        time.sleep(0.15)
    return hits


def fetch_supersalud():
    """SharePoint Search API anónima, filtrada al repositorio de comunicados."""
    path = 'https://docs.supersalud.gov.co/PortalWeb/Comunicaciones/Comunicados'
    qt = f'(multa OR sancion OR sanciona) path:"{path}"'
    rows, seen, start = [], set(), 0
    while True:
        from urllib.parse import quote
        url = ('https://www.supersalud.gov.co/es-co/_api/search/query'
               f"?querytext='{quote(qt)}'&rowlimit=500&startrow={start}"
               f"&selectproperties='Title,Path,Write'")
        raw = _curl(url, headers={'Accept': 'application/json;odata=nometadata'})
        if raw is None:
            print('  ! supersalud: search no responde', file=sys.stderr)
            break
        try:
            rr = json.loads(raw)['PrimaryQueryResult']['RelevantResults']
        except (json.JSONDecodeError, KeyError) as e:
            print(f'  ! supersalud: respuesta inesperada ({e})', file=sys.stderr)
            break
        table = rr['Table']['Rows']
        for r in table:
            c = {x['Key']: x['Value'] for x in r['Cells']}
            titulo, url_doc = c.get('Title') or '', c.get('Path') or ''
            if not titulo or url_doc in seen or not es_sancion(titulo):
                continue
            seen.add(url_doc)
            rec = parse_titulo(titulo)
            rec['url'] = url_doc
            rec['fecha'] = (c.get('Write') or '')[:10] or None
            rec['id'] = f'sns-{url_doc.rsplit("/", 1)[-1]}'
            rows.append(rec)
        total = rr.get('TotalRows', 0)
        start += len(table)
        print(f'  supersalud: {len(rows)} hits de {total} resultados')
        if not table or start >= total:
            break
        time.sleep(0.3)
    return rows


FETCHERS = {
    'supertransporte': fetch_supertransporte,
    'sic': fetch_sic,
    'supersalud': fetch_supersalud,
}


# ---------------------------------------------------------------- comandos

def cmd_fetch(slugs):
    RAW.mkdir(parents=True, exist_ok=True)
    for slug in (slugs or FETCHERS):
        if slug not in FETCHERS:
            print(f'  ? {slug}: no es fuente de comunicados', file=sys.stderr)
            continue
        print(f'{slug}...')
        rows = FETCHERS[slug]()
        (RAW / f'{slug}.json').write_text(
            json.dumps(rows, ensure_ascii=False), encoding='utf-8')
        con_s = sum(1 for r in rows if r['sancionado'])
        con_m = sum(1 for r in rows if r['monto'])
        print(f'  ok {slug:16s} {len(rows):>5d} sanciones '
              f'({con_s} con sancionado · {con_m} con monto)\n')


SAMPLES = [
    'La SuperTransporte impuso multa de $211 millones a la empresa  TRANS LOGYTOUR S.A.S. por el accidente',
    'Superintendencia de Transporte impone sanciones a PRECOLTUR S.A.S. por incumplimientos normativos',
    'Supersalud confirma multa de $350 millones a EPS Sanitas por incumplir',
    'Con multa de $ 250 millones, Supersalud sanciona a exgerente de hospital Emiro Quintero',
    'Supersalud multa con $4.060 millones a la EPSI Pijaos por incumplimiento',
    'Supersalud deja en firme multas por $ 920 millones a 3 EPS por incumplir',
    'Supersalud impone multas de $2.000 millones por incumplimientos en vacunación',
    'Superindustria sanciona a COMCEL con multa de $1.500 millones por publicidad engañosa',
]


def cmd_test():
    for t in SAMPLES:
        r = parse_titulo(t)
        monto = f"{r['monto']:,.0f}" if r['monto'] else '—'
        print(f"  sancionado={str(r['sancionado'])[:42]!r:45s} monto={monto:>16s}  {r['estado']}")
    print('\n(sancionado None es válido: el titular queda completo en `motivo`)')


def cmd_refilter():
    """Re-aplica es_sancion + parse_titulo sobre los raw ya bajados (cuando se
    afinan los regex no hace falta re-fetchear — SIC tarda ~10 min)."""
    for slug in FETCHERS:
        path = RAW / f'{slug}.json'
        if not path.exists():
            print(f'  - {slug}: sin raw, saltando')
            continue
        rows = json.loads(path.read_text(encoding='utf-8'))
        out = []
        for r in rows:
            if not es_sancion(r['titulo']):
                continue
            rec = parse_titulo(r['titulo'])
            rec.update({k: r.get(k) for k in ('url', 'fecha', 'id')})
            out.append(rec)
        path.write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
        con_s = sum(1 for r in out if r['sancionado'])
        print(f'  ok {slug:16s} {len(rows):>4d} -> {len(out):>4d} filas ({con_s} con sancionado)')


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    fp = sub.add_parser('fetch')
    fp.add_argument('slugs', nargs='*')
    sub.add_parser('test')
    sub.add_parser('refilter')
    a = ap.parse_args()
    if a.cmd == 'fetch':
        cmd_fetch(a.slugs)
    elif a.cmd == 'refilter':
        cmd_refilter()
    else:
        cmd_test()


if __name__ == '__main__':
    main()
