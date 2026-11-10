#!/usr/bin/env python3
"""Escrutinio oficial presidencial 2026 (MMV de las 33 comisiones generales) -> por PUESTO.

Salida: Bases de datos/nuevo-liberalismo/pres-puesto.json
  {pcode: {v1:{cepeda,abelardo,paloma,fajardo,otros,blanco,nulos}, v2:{cepeda,abelardo,blanco,nulos}}}
No trae el exterior (las comisiones generales no lo incluyen; ver CLAUDE.md).
"""
import csv, glob, json, os, collections
BASE = os.path.join(os.path.dirname(__file__), '..', '..', 'Bases de datos')
OUT = os.path.join(BASE, 'nuevo-liberalismo')

def clave(nombre):
    n = nombre.upper()
    if 'CEPEDA' in n: return 'cepeda'
    if 'ESPRIELLA' in n: return 'abelardo'
    if 'PALOMA' in n: return 'paloma'
    if 'FAJARDO' in n: return 'fajardo'
    if 'BLANCO' in n: return 'blanco'
    if 'NULO' in n or 'NO MARCADO' in n: return 'nulos'
    return 'otros'

def lee(carpeta):
    P = collections.defaultdict(collections.Counter)
    for f in sorted(glob.glob(os.path.join(BASE, 'escrutinio-2026', carpeta, 'MMV_*.csv'))):
        with open(f, encoding='utf-8-sig', newline='', errors='replace') as fh:
            for r in csv.DictReader(fh, delimiter=';'):
                try: v = int(r['VOTOS'])
                except Exception: continue
                if not v or not r.get('DEP'): continue
                pcode = r['DEP'].zfill(2) + r['MUN'].zfill(3) + r['ZONA'].zfill(2) + r['PUESTO'].zfill(2)
                P[pcode][clave(r['CANNOMBRE'])] += v
    return P

v1, v2 = lee('raw'), lee('raw-2v')
out = {}
for p in set(v1) | set(v2):
    out[p] = {'v1': dict(v1.get(p, {})), 'v2': dict(v2.get(p, {}))}
json.dump(out, open(os.path.join(OUT, 'pres-puesto.json'), 'w'))
t1 = collections.Counter(); t2 = collections.Counter()
for p in out.values():
    t1.update(p['v1']); t2.update(p['v2'])
print('puestos', len(out)); print('1V', dict(t1)); print('2V', dict(t2))
# control contra el escrutinio (CLAUDE.md): 1V Abelardo 10.045.330 · Cepeda 9.536.162 ; 2V 12.569.192 · 12.495.109
assert abs(t1['abelardo'] - 10045330) < 2000 and abs(t1['cepeda'] - 9536162) < 2000, (t1['abelardo'], t1['cepeda'])
assert abs(t2['abelardo'] - 12569192) < 2000 and abs(t2['cepeda'] - 12495109) < 2000, (t2['abelardo'], t2['cepeda'])
print('control OK')
