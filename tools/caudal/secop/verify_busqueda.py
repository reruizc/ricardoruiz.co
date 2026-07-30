#!/usr/bin/env python3
"""
Caudal · SECOP — smoke test de las DOS mitigaciones de la búsqueda (FASE 1).

No es parte del pipeline de datos: es la prueba de que el contrato del README es
implementable tal como está escrito. El otro chat puede correr esto para ver el
comportamiento exacto que debe reproducir en la Lambda + la vista.

  Mitigación 1 · CHIPS      — un término se resuelve a un filtro EXACTO de
                              dimensión (sin falsos positivos) usando stats['chips'].
  Mitigación 2 · MATCH      — por qué matcheó cada fila, usando stats['columnas_match']
                              con su orden de prioridad.

Uso:
  python3 tools/caudal/secop/verify_busqueda.py            # término por defecto: transporte
  python3 tools/caudal/secop/verify_busqueda.py salud
"""
import json
import subprocess
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
STATS = REPO / 'Bases de datos' / 'leyes-senado' / 'secop' / 'dist' / 's3' / 'secop-stats.json'
BASE = 'https://www.datos.gov.co/resource/jbjy-vk9h.json'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')


def norm(s):
    s = (s or '').lower()
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')


def curl(url, timeout=60):
    r = subprocess.run(['/usr/bin/curl', '-s', '-A', UA, '--max-time', str(timeout), url],
                       capture_output=True, timeout=timeout + 10)
    return json.loads(r.stdout.decode('utf-8', errors='replace'))


def main():
    q = (sys.argv[1] if len(sys.argv) > 1 else 'transporte').lower()
    st = json.loads(STATS.read_text(encoding='utf-8'))
    qn = norm(q)

    # ---- Mitigación 1: ¿hay un chip de dimensión para este término? ----
    print(f'=== término: "{q}" ===\n')
    print('— Mitigación 1 · CHIPS sugeridos (filtro exacto, 0 falsos positivos) —')
    sug = [c for c in st['chips'] if qn in c['norm']]
    if sug:
        for c in sug[:6]:
            print(f"  [{c['etiqueta']}: {c['valor']}]  ->  {c['campo']}='{c['valor']}'"
                  f"  ({c['n']:,} contratos)")
    else:
        print('  (sin chip — el término va a $q full-text)')

    # ---- Mitigación 2: por qué matcheó cada resultado de $q ----
    cols = st['columnas_match']
    sel = '%2C'.join(c['campo'] for c in cols)
    url = f'{BASE}?$q={q}&$select={sel}&$limit=10'.replace(' ', '%20')
    rows = curl(url)
    if isinstance(rows, dict):
        print(f"\n  ! Socrata error: {rows.get('message', rows)}")
        return 1

    print(f'\n— Mitigación 2 · badge "matchea por" (orden = prioridad) —')
    conteo = {}
    for r in rows:
        razon = None
        for c in cols:                      # la primera columna que contenga, gana
            if qn in norm(r.get(c['campo'])):
                razon = c['etiqueta']
                break
        razon = razon or '(?) columna no probada'
        conteo[razon] = conteo.get(razon, 0) + 1
        ent = (r.get('nombre_entidad') or '—')[:44]
        print(f'  {ent:46s} -> {razon}')

    print('\n  resumen:', ' · '.join(f'{k}: {v}' for k, v in
                                     sorted(conteo.items(), key=lambda x: -x[1])))
    sin = conteo.get('(?) columna no probada', 0)
    if sin:
        print(f'  ! {sin}/10 sin atribuir: $q matcheó una columna fuera de '
              f'columnas_match (o PII excluida). Ver README.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
