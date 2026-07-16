#!/usr/bin/env python3
"""
Caudal · harvester de sanciones de la Superintendencia Financiera (vía 2).

El buscador público de sanciones ("SiriCasillero", `SiriWeb/main.js`, Angular)
habla con una API interna que exige un header `api-key`. La key vive embebida
en texto plano dentro del bundle público (`const Qt = {..., apiKey:"..."}`) —
no es una credencial nuestra ni de un tercero protegido, es la misma key que
usa cualquier visitante del navegador al abrir el buscador. Se re-extrae en
cada corrida (la nota de `fuentes.json` ya avisa que rota).

Endpoint: GET {api_url_siri}/api/actoAdmin/listarSancionesMercadoValores
Devuelve ~800 sanciones a entidades del mercado de valores/financiero, cada
una con fechas en epoch-millis y el número de acto administrativo como int —
ambos se normalizan aquí (a 'YYYY-MM-DD' y string) para que
`normalize_row()`/`map` de harvest_supers.py los levante sin tocar nada más.

Uso:
  python3 tools/caudal/supers/harvest_sfc.py fetch
  python3 tools/caudal/supers/harvest_sfc.py test    # solo valida la key + 1 fila
Luego:
  python3 tools/caudal/supers/harvest_supers.py normalize
  python3 tools/caudal/supers/build_s3.py
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RAW = REPO / 'Bases de datos' / 'leyes-senado' / 'supers' / 'raw'
FUENTES = json.loads((HERE / 'fuentes.json').read_text(encoding='utf-8'))
SLUG = 'sfc-mercado-valores'

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')
MAIN_JS = 'https://www.superfinanciera.gov.co/SiriWeb/main.js'
API_KEY_RE = re.compile(r'apiKey\s*:\s*"([^"]+)"')

# años sanos para fechaFirmeza/fechaActoAdmin — la fuente trae al menos un
# typo real (año 3022 visto jul-2026); fuera de rango se descarta la fecha en
# vez de adivinarla, para no fabricar dato ni dejar basura en "más recientes".
ANIO_MIN, ANIO_MAX = 2000, datetime.date.today().year + 1


def _curl(url, headers=None, timeout=60):
    cmd = ['/usr/bin/curl', '-s', '-A', UA, '--max-time', str(timeout)]
    for k, v in (headers or {}).items():
        cmd += ['-H', f'{k}: {v}']
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, timeout=timeout + 10)
    return r.stdout


def get_api_key():
    """Baja el bundle público y extrae la apiKey en texto plano."""
    js = _curl(MAIN_JS).decode('utf-8', errors='replace')
    m = API_KEY_RE.search(js)
    if not m:
        print('  ! no se encontró apiKey en el bundle — el bundle cambió de forma, '
              'revisar a mano (buscar "apiKey:" en SiriWeb/main.js)', file=sys.stderr)
        return None
    return m.group(1)


def get_endpoint():
    for f in FUENTES['fuentes']:
        if f['slug'] == SLUG:
            return f['endpoint']
    raise SystemExit(f'fuente {SLUG!r} no está en fuentes.json')


def _epoch_to_iso(v):
    """epoch-millis -> 'YYYY-MM-DD', o None si falta / cae fuera de rango sano."""
    if not v:
        return None
    try:
        d = datetime.datetime.fromtimestamp(int(v) / 1000, tz=datetime.timezone.utc).date()
    except (ValueError, OSError, OverflowError):
        return None
    if not (ANIO_MIN <= d.year <= ANIO_MAX):
        return None
    return d.isoformat()


def transform(row):
    """Deja la fila con los mismos nombres de campo (para el `map` de
    fuentes.json) pero con fechas ISO y el nº de acto como string."""
    row = dict(row)
    row['fechaFirmeza'] = _epoch_to_iso(row.get('fechaFirmeza'))
    row['fechaActoAdmin'] = _epoch_to_iso(row.get('fechaActoAdmin'))
    if row.get('numeroActoAdmin') is not None:
        row['numeroActoAdmin'] = str(row['numeroActoAdmin'])
    return row


def cmd_fetch():
    key = get_api_key()
    if not key:
        raise SystemExit(1)
    print(f'  api-key: {key[:6]}...{key[-4:]}')
    endpoint = get_endpoint()
    raw = _curl(endpoint, headers={'api-key': key, 'Accept': 'application/json'})
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(f'  ! respuesta no-JSON (posible key rotada): {raw[:200]!r}', file=sys.stderr)
        raise SystemExit(1)
    if not isinstance(data, list):
        print(f'  ! respuesta inesperada: {data}', file=sys.stderr)
        raise SystemExit(1)
    rows = [transform(r) for r in data]
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f'{SLUG}.json').write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    con_fecha = sum(1 for r in rows if r.get('fechaFirmeza'))
    con_monto = sum(1 for r in rows if r.get('montoSancion'))
    print(f'  ok {SLUG:22s} {len(rows):>6d} filas  '
          f'({con_fecha} con fecha_firmeza · {con_monto} con monto)')


def cmd_test():
    key = get_api_key()
    if not key:
        raise SystemExit(1)
    print(f'  api-key OK: {key[:6]}...{key[-4:]}')
    endpoint = get_endpoint()
    raw = _curl(endpoint, headers={'api-key': key, 'Accept': 'application/json'}, timeout=30)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print('  FALLA: respuesta no-JSON')
        raise SystemExit(1)
    print(f'  OK: {len(data)} filas. Ejemplo transformado:')
    print(json.dumps(transform(data[0]), ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('fetch')
    sub.add_parser('test')
    a = ap.parse_args()
    if a.cmd == 'fetch':
        cmd_fetch()
    elif a.cmd == 'test':
        cmd_test()


if __name__ == '__main__':
    main()
