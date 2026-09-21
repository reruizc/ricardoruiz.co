#!/usr/bin/env python3
"""
Caudal · harvester del pilar Ejecutivo Nacional (decretos y normativa de Presidencia).

Fuente única, vía 1 (Socrata / datos.gov.co) — mismo patrón que harvest_supers.py:
  Dataset "Normativa Nacional · Presidencia de la República"  ->  88h2-dykw
  Verificado jul-2026: 10.193 DECRETOS + leyes/resoluciones/directivas/circulares/
  ACTOS LEGISLATIVOS/AGENDA REGULATORIA, desde 2015. Cada fila trae:
    tipo · fecha · titulo (con el número) · descripcion (el "por medio del cual se…")
    · url = PDF DIRECTO en dapre.presidencia.gov.co/normativa/…  (digital, pypdf limpio)
  Frecuencia de actualización declarada: MENSUAL (ojo: no es "en vivo"; el articulado
  completo se saca del PDF con el pipeline de gacetas de Caudal, bajo demanda).

Este script baja la metadata (cero scraping), extrae número/año del título, y emite
una lista SLIM lista para S3 / la Lambda (acción `ejecutivo`), más un stats.json para
el landing del pilar. El texto completo del decreto NO se baja aquí (es on-demand vía
el `url`, igual que las gacetas): esto es el índice navegable.

Todo stdlib. curl por subprocess (esquiva el TLS de python 3.14, igual que scrape_cne.py).

Uso:
  python3 tools/caudal/ejecutivo/harvest_decretos.py fetch                 # baja toda la normativa
  python3 tools/caudal/ejecutivo/harvest_decretos.py fetch --desde 2024-01-01
  python3 tools/caudal/ejecutivo/harvest_decretos.py build                 # raw -> dist (JSONL + stats)
  python3 tools/caudal/ejecutivo/harvest_decretos.py test                  # smoke test (1 fila)
"""
import argparse
import datetime
import json
import unicodedata
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = REPO / 'Bases de datos' / 'leyes-senado' / 'ejecutivo'
RAW = OUT / 'raw'
DIST = OUT / 'dist'
DO_RAW = RAW / 'diario_oficial.json'   # lo escribe harvest_diario_oficial.py

SOCRATA_DOMAIN = 'www.datos.gov.co'
SOCRATA_ID = '88h2-dykw'
FUENTE_NOMBRE = 'Normativa Nacional · Presidencia de la República'
FRECUENCIA = 'Mensual'  # declarada en la metadata Socrata (jul-2026)

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')
PAGE = 50000  # tope SoQL por request

# el número va en el titulo ("Decreto 1234 del 15 de marzo de 2024"); el año lo
# tomamos de `fecha` (más confiable que el del titulo). Regex ancla en el tipo y
# admite "No."/"N°" opcional antes del número.
_NUM_RE = re.compile(
    r'\b(?:decreto|ley|resoluci[oó]n|directiva|circular|acto\s+legislativo)\b'
    r'[^\d]{0,14}(\d{1,5})', re.I)
_FECHA_MAX = (datetime.date.today() + datetime.timedelta(days=45)).isoformat()


def curl_json(url, timeout=90):
    cmd = ['/usr/bin/curl', '-s', '-A', UA, '--max-time', str(timeout), url]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout + 10)
    except subprocess.TimeoutExpired:
        return None, 'timeout'
    if r.returncode != 0:
        return None, f'curl rc={r.returncode}'
    try:
        return json.loads(r.stdout.decode('utf-8', errors='replace')), None
    except json.JSONDecodeError as e:
        return None, f'json: {e}'


def parse_fecha(v):
    """'2024-03-15T00:00:00.000' | '2024-03-15' -> '2024-03-15' (o '')."""
    if not v:
        return ''
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', str(v))
    if not m:
        return ''
    f = m.group(0)
    return f if '2000-01-01' <= f <= _FECHA_MAX else ''


def parse_numero(titulo):
    m = _NUM_RE.search(titulo or '')
    if m:
        return m.group(1)
    m2 = re.search(r'\b(\d{1,5})\b', titulo or '')  # fallback: primer entero
    return m2.group(1) if m2 else ''


def fetch(desde=None):
    """Baja toda la normativa paginando por $offset. Guarda raw JSON."""
    base = f'https://{SOCRATA_DOMAIN}/resource/{SOCRATA_ID}.json'
    where = f"&$where=fecha>='{desde}T00:00:00'" if desde else ''
    rows, offset = [], 0
    while True:
        url = f"{base}?$limit={PAGE}&$offset={offset}&$order=:id{where}"
        data, err = curl_json(url)
        if err:
            print(f"  ! fetch: {err}", file=sys.stderr)
            return None
        if not data:
            break
        rows.extend(data)
        if len(data) < PAGE:
            break
        offset += PAGE
        time.sleep(0.2)
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / 'normativa.json').write_text(
        json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    print(f"  ok  {len(rows):>6d} filas -> {(RAW / 'normativa.json').relative_to(REPO)}")
    return rows


def slim(row):
    titulo = (row.get('titulo') or '').strip()
    fecha = parse_fecha(row.get('fecha'))
    desc = re.sub(r'\s+', ' ', (row.get('descripcion') or '')).strip()
    tipo = (row.get('tipo') or '').strip()
    numero = parse_numero(titulo)
    url = (row.get('url') or '').strip()
    # Sin tildes: el 70% de los blobs las traía y «declaracion» no encontraba
    # «declaración». Se pliega acá y no en la consulta porque plegar en caliente
    # cuesta segundos por petición (medido en el pilar Regulatorio).
    blob = _blob(titulo, desc)
    return {
        'tipo': tipo,
        'numero': numero,
        'anio': fecha[:4] if fecha else '',
        'fecha': fecha,
        'titulo': titulo or '—',
        'descripcion': desc,
        'url': url,          # PDF oficial (texto completo on-demand)
        'fuente': 'presidencia',
        'q': blob,           # blob de búsqueda (substring en la Lambda)
    }


def _blob(*partes):
    return ''.join(c for c in unicodedata.normalize(
        'NFD', ' '.join(x for x in partes if x).lower())
        if unicodedata.category(c) != 'Mn')


def _llave(r):
    return (r.get('tipo') or '', str(r.get('numero') or '').lstrip('0'), r.get('anio') or '')


def fusionar(recs):
    """Socrata (Presidencia) + Diario Oficial, dedup por (tipo, número, año).

    Socrata MANDA cuando tiene la norma: su descripción es la limpia y su `url`
    es el PDF permanente de Presidencia. El Diario Oficial solo rellena lo que
    Socrata aún no trae — que es justo el mes de rezago del dataset. Devuelve
    (registros, meta) con la cobertura de cada fuente por separado.
    """
    meta = {'diario_oficial': None, 'agregadas': 0, 'ya_en_socrata': 0}
    if not DO_RAW.exists():
        return recs, meta
    try:
        do = json.loads(DO_RAW.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as e:
        print(f"  ! diario oficial ilegible ({e}): se publica solo Socrata", file=sys.stderr)
        return recs, meta
    ya = {_llave(r) for r in recs if r.get('numero')}
    out = list(recs)
    for r in do.get('normas', []):
        if _llave(r) in ya:
            meta['ya_en_socrata'] += 1
            continue
        fila = {k: v for k, v in r.items()}
        fila['q'] = _blob(fila.get('titulo'), fila.get('descripcion'))
        out.append(fila)
        ya.add(_llave(r))
        meta['agregadas'] += 1
    meta['diario_oficial'] = {
        'cobertura': do.get('cobertura') or {},
        'generado': do.get('generado', ''),
        'ediciones': len(do.get('ediciones') or []),
        'fallidas': len(do.get('fallidas') or []),
    }
    return out, meta


def build():
    """raw/normativa.json -> dist/normativa.jsonl (slim) + dist/stats.json."""
    raw = RAW / 'normativa.json'
    if not raw.exists():
        print("no hay raw; corre 'fetch' primero", file=sys.stderr)
        sys.exit(1)
    rows = json.loads(raw.read_text(encoding='utf-8'))
    socrata = [slim(r) for r in rows]
    socrata_hasta = max((r['fecha'] for r in socrata if r['fecha']), default='')
    recs, fus = fusionar(socrata)
    DIST.mkdir(parents=True, exist_ok=True)

    with (DIST / 'normativa.jsonl').open('w', encoding='utf-8') as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')

    por_tipo = Counter(r['tipo'] or '—' for r in recs)
    por_anio = Counter(r['anio'] for r in recs if r['anio'])
    fechas = sorted(r['fecha'] for r in recs if r['fecha'])
    con_url = sum(1 for r in recs if r['url'])
    recientes = sorted([r for r in recs if r['fecha']],
                       key=lambda r: r['fecha'], reverse=True)[:15]
    for r in recientes:
        r.pop('q', None)

    hoy = datetime.date.today().isoformat()
    do_meta = fus['diario_oficial']
    do_hasta = ((do_meta or {}).get('cobertura') or {}).get('hasta', '')
    # La cobertura del pilar es hasta dónde se LEYÓ, no la norma más nueva: un
    # domingo sin decretos no atrasa el registro. Socrata no publica fecha de
    # corte, así que su cobertura es su norma más reciente; la del Diario
    # Oficial es su edición más reciente leída. Manda la mayor, nunca en el futuro.
    cob_hasta = min(max(socrata_hasta, do_hasta), hoy)
    stats = {
        'total': len(recs),
        'con_pdf': con_url,
        'por_tipo': [{'tipo': t, 'n': n} for t, n in por_tipo.most_common()],
        'por_anio': dict(sorted(por_anio.items())),
        # ⚠️ el brief lee rango_fechas[-1] como cobertura: va la COMBINADA
        'rango_fechas': [fechas[0], max(fechas[-1] if fechas else '', cob_hasta)]
                        if fechas else ['', ''],
        'cobertura': {
            'hasta': cob_hasta,
            'socrata': socrata_hasta,
            'diario_oficial': do_hasta,
            'rezago_socrata_dias': ((datetime.date.fromisoformat(hoy)
                                     - datetime.date.fromisoformat(socrata_hasta)).days
                                    if socrata_hasta else None),
            'desde_diario_oficial': fus['agregadas'],
        },
        'recientes': recientes,
        'fuente': {
            'id': SOCRATA_ID, 'nombre': FUENTE_NOMBRE,
            'url': f'https://{SOCRATA_DOMAIN}/resource/{SOCRATA_ID}.json',
            # con el Diario Oficial al día, el pilar es diario aunque Socrata no
            'frecuencia': 'Diaria' if do_hasta else FRECUENCIA,
        },
        'fuentes': [
            {'id': SOCRATA_ID, 'nombre': FUENTE_NOMBRE, 'frecuencia': FRECUENCIA,
             'hasta': socrata_hasta},
        ] + ([{'id': 'diario_oficial', 'nombre': 'Diario Oficial · Imprenta Nacional',
               'frecuencia': 'Diaria', 'hasta': do_hasta,
               'normas_agregadas': fus['agregadas'],
               'ediciones': do_meta.get('ediciones'),
               'ediciones_fallidas': do_meta.get('fallidas')}] if do_meta else []),
    }
    (DIST / 'stats.json').write_text(
        json.dumps(stats, ensure_ascii=False, indent=1), encoding='utf-8')

    print(f"slim: {len(recs)} normas -> {(DIST / 'normativa.jsonl').relative_to(REPO)}")
    print(f"socrata hasta {socrata_hasta or '—'} · diario oficial hasta {do_hasta or '—'}"
          f" · +{fus['agregadas']} normas del Diario Oficial ({fus['ya_en_socrata']} ya estaban)"
          f" · cobertura {cob_hasta}")
    print(f"con PDF: {con_url}/{len(recs)}   ·   rango: {stats['rango_fechas']}")
    for t, n in por_tipo.most_common():
        print(f"  {t:26s} {n:>6d}")


def test():
    url = f'https://{SOCRATA_DOMAIN}/resource/{SOCRATA_ID}.json?$limit=1&$where=tipo=%27DECRETOS%27'
    data, err = curl_json(url, timeout=40)
    if err or not data:
        print(f"FALLA: {err or 'sin filas'}")
        return False
    r = slim(data[0])
    print(f"  tipo={r['tipo']}  numero={r['numero']}  fecha={r['fecha']}")
    print(f"  titulo={r['titulo'][:70]!r}")
    print(f"  url={r['url'][:80]}")
    ok = bool(r['numero'] and r['url'])
    print('\nTEST OK' if ok else '\nTEST: revisar mapeo (número o url vacíos)')
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    fp = sub.add_parser('fetch')
    fp.add_argument('--desde', default=None, help='YYYY-MM-DD (filtra por fecha)')
    sub.add_parser('build')
    sub.add_parser('test')
    a = ap.parse_args()
    if a.cmd == 'fetch':
        if fetch(desde=a.desde) is not None:
            print("\nlisto. corre 'build' para consolidar.")
    elif a.cmd == 'build':
        build()
    elif a.cmd == 'test':
        sys.exit(0 if test() else 1)


if __name__ == '__main__':
    main()
