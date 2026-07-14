#!/usr/bin/env python3
"""
Caudal · harvester de sanciones de superintendencias y entidades reguladoras
(módulo de Cauce — el "dapper interno").

Piloto vía 1 (Socrata / datos.gov.co): cada fuente publica sus sanciones como
un dataset JSON con API directa. Este script las baja, las normaliza a un
esquema común de sanción y consolida a JSONL + CSV, listo para que la Lambda
las indexe por tema/sector y el analista de Cauce las lea.

Las fuentes vía 2 (API interna del portal, ej. Superfinanciera) y vía 3
(normograma/PDF, ej. Supersalud) quedan registradas en fuentes.json con su
endpoint; se implementan en harvesters hermanos (harvest_sfc.py, etc.) reusando
el mismo esquema y este consolidador.

Todo stdlib. curl por subprocess (mismo patrón que scrape_cne.py / harvest.py:
esquiva el TLS de python 3.14). Resumible: los raw ya bajados no se re-piden.

Uso:
  python3 tools/caudal/supers/harvest_supers.py list
  python3 tools/caudal/supers/harvest_supers.py fetch                 # todas las vía 1
  python3 tools/caudal/supers/harvest_supers.py fetch invima secop1-multas
  python3 tools/caudal/supers/harvest_supers.py fetch --desde 2024-01-01
  python3 tools/caudal/supers/harvest_supers.py normalize             # raw -> dist
  python3 tools/caudal/supers/harvest_supers.py test                  # smoke test
"""
import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
FUENTES = json.loads((HERE / 'fuentes.json').read_text(encoding='utf-8'))
OUT = REPO / 'Bases de datos' / 'leyes-senado' / 'supers'
RAW = OUT / 'raw'
DIST = OUT / 'dist'

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')
PAGE = 50000  # tope SoQL por request

NORM_FIELDS = FUENTES['_schema_normalizado']


def curl_json(url, timeout=60):
    """GET url y parsea JSON. Devuelve (data, error)."""
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


def via1_sources(slugs=None):
    out = []
    for f in FUENTES['fuentes']:
        if f.get('via') != 1:
            continue
        if slugs and f['slug'] not in slugs:
            continue
        out.append(f)
    return out


def fetch_source(f, desde=None):
    """Baja un dataset Socrata paginando por $offset. Guarda raw JSON."""
    dom, rid = f['socrata_domain'], f['socrata_id']
    base = f'https://{dom}/resource/{rid}.json'
    where = ''
    if desde and f.get('fecha_col'):
        where = f"&$where={f['fecha_col']}>='{desde}T00:00:00'"
    rows, offset = [], 0
    while True:
        url = f"{base}?$limit={PAGE}&$offset={offset}&$order=:id{where}"
        data, err = curl_json(url)
        if err:
            print(f"  ! {f['slug']}: {err}", file=sys.stderr)
            return None
        if not data:
            break
        rows.extend(data)
        if len(data) < PAGE:
            break
        offset += PAGE
        time.sleep(0.2)
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f"{f['slug']}.json").write_text(
        json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    print(f"  ok {f['slug']:22s} {len(rows):>6d} filas")
    return rows


def normalize_row(f, row):
    """Aplica el mapeo de fuentes.json a una fila cruda -> esquema común."""
    m = f.get('map') or {}
    rec = {
        'fuente': f['slug'],
        'fuente_nombre': f['nombre'],
        'sector': f.get('sector', ''),
    }
    for nf in NORM_FIELDS:
        if nf in ('fuente', 'fuente_nombre', 'sector', '_raw'):
            continue
        src = m.get(nf)
        rec[nf] = row.get(src) if src else None
    rec['_raw'] = row
    return rec


def normalize_all():
    """Lee todos los raw/*.json y consolida a dist/ (JSONL + CSV)."""
    DIST.mkdir(parents=True, exist_ok=True)
    all_recs, per_fuente = [], {}
    for f in FUENTES['fuentes']:
        raw = RAW / f"{f['slug']}.json"
        if not raw.exists():
            continue
        rows = json.loads(raw.read_text(encoding='utf-8'))
        if f.get('granularidad') == 'agregado' or not f.get('map'):
            per_fuente[f['slug']] = {'filas': len(rows), 'granularidad': f.get('granularidad'),
                                     'nota': 'agregado / sin mapeo — no entra al consolidado por entidad'}
            continue
        recs = [normalize_row(f, r) for r in rows]
        all_recs.extend(recs)
        per_fuente[f['slug']] = {'filas': len(recs), 'granularidad': 'entidad'}

    jsonl = DIST / 'sanciones.jsonl'
    with jsonl.open('w', encoding='utf-8') as fh:
        for r in all_recs:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')

    csv_cols = [c for c in NORM_FIELDS if c != '_raw']
    with (DIST / 'sanciones.csv').open('w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=csv_cols, extrasaction='ignore')
        w.writeheader()
        for r in all_recs:
            w.writerow({k: r.get(k) for k in csv_cols})

    stats = {
        'total_sanciones_entidad': len(all_recs),
        'por_fuente': per_fuente,
        'campos': csv_cols,
    }
    (DIST / 'stats.json').write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\nconsolidado: {len(all_recs)} sanciones (nivel entidad) -> {jsonl.relative_to(REPO)}")
    for slug, s in per_fuente.items():
        print(f"  {slug:22s} {s['filas']:>6d}  {s.get('granularidad','')}")


def cmd_list():
    print(f"{'slug':22s} {'vía':3s} {'gran':9s} {'dif':6s}  fuente")
    print('-' * 78)
    for f in FUENTES['fuentes']:
        print(f"{f['slug']:22s} {str(f.get('via')):3s} "
              f"{f.get('granularidad',''):9s} {f.get('dificultad',''):6s}  {f['nombre']}")
    n1 = len(via1_sources())
    print(f"\nvía 1 (Socrata, listas para fetch): {n1}   ·   "
          f"vía 2/3 (registradas, pendientes): {len(FUENTES['fuentes'])-n1}")


def cmd_test():
    """Smoke test: baja 1 fila de cada fuente vía 1 y valida el mapeo."""
    ok = True
    for f in via1_sources():
        url = (f"https://{f['socrata_domain']}/resource/{f['socrata_id']}.json"
               f"?$limit=1")
        data, err = curl_json(url, timeout=30)
        if err or not data:
            print(f"  FALLA {f['slug']}: {err or 'sin filas'}")
            ok = False
            continue
        rec = normalize_row(f, data[0])
        mapped = sum(1 for k in ('sancionado', 'fecha_firmeza') if rec.get(k))
        flag = 'ok' if mapped else 'REVISAR MAPEO'
        print(f"  {flag:14s} {f['slug']:22s} sancionado={str(rec.get('sancionado'))[:40]!r}")
        if not mapped and f.get('granularidad') == 'entidad':
            ok = False
    print('\nTEST OK' if ok else '\nTEST con hallazgos — revisar mapeos arriba')
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('list')
    fp = sub.add_parser('fetch')
    fp.add_argument('slugs', nargs='*')
    fp.add_argument('--desde', default=None, help='YYYY-MM-DD (filtra por fecha de firmeza)')
    sub.add_parser('normalize')
    sub.add_parser('test')
    a = ap.parse_args()

    if a.cmd == 'list':
        cmd_list()
    elif a.cmd == 'fetch':
        srcs = via1_sources(a.slugs or None)
        if not srcs:
            print('sin fuentes vía 1 que coincidan', file=sys.stderr)
            sys.exit(1)
        print(f"bajando {len(srcs)} fuente(s) vía 1...")
        for f in srcs:
            fetch_source(f, desde=a.desde)
        print("\nlisto. corre 'normalize' para consolidar.")
    elif a.cmd == 'normalize':
        normalize_all()
    elif a.cmd == 'test':
        sys.exit(0 if cmd_test() else 1)


if __name__ == '__main__':
    main()
