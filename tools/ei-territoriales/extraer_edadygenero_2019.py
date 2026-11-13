#!/usr/bin/env python3
"""Sufragantes 2019 (Autoridades Locales) por puesto, con sexo y edad.

Lee Edadygenero.xlsx (mesa a mesa, RNEC) y agrega a puesto con la misma llave
y el mismo mapeo de localidades de Bogotá que tools/edad-1v-2026/probe_viabilidad.py.
Salida: Bases de datos/output_edad_1v/edad-al2019-puesto.csv
"""
import csv, os, sys, time
from collections import defaultdict
import openpyxl
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'edad-1v-2026'))
from probe_viabilidad import BANDS, BOG_LOC, nrm, zf  # noqa: E402

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Bases de datos')
SRC = os.path.join(BASE, 'Edadygenero.xlsx')
OUT = os.path.join(BASE, 'output_edad_1v', 'edad-al2019-puesto.csv')
COLS = ['Cantidad de Sufragantes', 'Edad Indefinida', 'Cantidad Hombres', 'Cantidad de Mujeres'] + BANDS

t0 = time.time()
wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
ws = wb[wb.sheetnames[0]]
acc = defaultdict(lambda: [0] * (len(COLS) + 1))
h = None; n = 0; sinmap = set()
for row in ws.iter_rows(values_only=True):
    if h is None:
        h = {c: i for i, c in enumerate(row)}; continue
    n += 1
    if 'Autoridades' not in str(row[h['Datos de tipo de elección']] or ''):
        continue
    a = row[h['Año']]
    anio = a.year if hasattr(a, 'year') else int(str(a)[:4])
    if anio != 2019:
        continue
    z = str(row[h['Cód. Comuna / Localidad']]).strip()
    if not z.isdigit():
        zz = BOG_LOC.get(nrm(z))
        if zz is None:
            sinmap.add(z); continue
    else:
        zz = zf(z, 2)
    k = f"{zf(row[h['Cód. Depto']], 2)}-{zf(row[h['Cód. Municipio']], 3)}-{zz}-{zf(row[h['Cód. Puesto de Votación']], 2)}"
    v = acc[k]
    for i, c in enumerate(COLS):
        try: v[i] += int(row[h[c]] or 0)
        except (TypeError, ValueError): pass
    v[-1] += 1
    if n % 100000 == 0:
        print(f'  {n} filas · {time.time()-t0:.0f}s', flush=True)
with open(OUT, 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['pcode'] + COLS + ['n_mesas'])
    for k in sorted(acc): w.writerow([k] + acc[k])
print(f'{len(acc)} puestos · {sum(v[0] for v in acc.values()):,} sufragantes · {time.time()-t0:.0f}s · sin mapeo: {sorted(sinmap)[:10]}')
