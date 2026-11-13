#!/usr/bin/env python3
"""Top 15 de candidatos a concejo (nacional y por departamento) → top-candidatos.json.

concejo-2023.html no puede bajar los 33 municipios.json (10 MB) solo para pintar
los 15 más votados del país; este archivo los trae precalculados. Lee la salida
local de Bases de datos/concejo-2023/output/ (la misma que está en S3).

  python3 tools/analisis-candidato/build_concejo_top.py [--subir]
"""
import glob, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.join(ROOT, 'Bases de datos', 'concejo-2023', 'output')
N = 15

filas = []
for f in sorted(glob.glob(os.path.join(BASE, 'departamentos', '*', 'municipios.json'))):
    dep = os.path.basename(os.path.dirname(f))
    for m in json.load(open(f)):
        vv = m.get('votos_validos') or 0
        for p in m['partidos']:
            el = {(e.get('cod'), e['nombre']) for e in p.get('electos', [])}
            for c in p.get('candidatos', []):
                filas.append({'n': c['nombre'], 'v': c['votos'],
                              'pct': round(100 * c['votos'] / vv, 2) if vv else 0,
                              'd': dep, 'mc': m['mun'], 'm': m['nombre'], 'p': p['partido'],
                              'g': (c.get('cod'), c['nombre']) in el})
filas.sort(key=lambda x: -x['v'])
out = {'v': 2023, 'nacional': filas[:N], 'deps': {}}
for x in filas:
    l = out['deps'].setdefault(x['d'], [])
    if len(l) < N:
        l.append(x)
dst = os.path.join(BASE, 'nacional', 'top-candidatos.json')
json.dump(out, open(dst, 'w'), ensure_ascii=False, separators=(',', ':'))
print(f'{len(filas):,} candidaturas · {len(out["deps"])} deptos → {dst} ({os.path.getsize(dst)/1024:.0f} KB)')
print('1º', filas[0]['n'], filas[0]['v'])
if '--subir' in sys.argv:
    subprocess.run(['aws', 's3', 'cp', dst,
                    's3://elecciones-2026/ricardoruiz.co/bases de datos/concejo-2023/output/nacional/top-candidatos.json',
                    '--content-type', 'application/json', '--cache-control', 'public, max-age=300'], check=True)
