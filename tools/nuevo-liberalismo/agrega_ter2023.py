#!/usr/bin/env python3
"""Territoriales 2023 (GCS_2023TER.csv, 1,96 GB) -> agregado por municipio / depto y partido.

Una sola pasada. Códigos de corporación de 2023: 1 = gobernador · 2 = asamblea ·
3 = alcalde · 4 = concejo (las cuatro vienen INTERCALADAS en el archivo).
COD_CAN 0 = voto solo por la lista · 996 blanco · 997 nulos · 998 no marcados.

Salida: Bases de datos/nuevo-liberalismo/ter2023-agg.json
  concejo:  {"DD-MMM": {p:{par:{n, l, c:{can:[nombre,votos]}}}, b, nu}}
  asamblea: {"DD":     {p:{par:{n, l, c:{...}}}, b, nu, m:{"MMM":{par:votos}, ...}, mb:{"MMM":blanco}}}
  alcaldia: {"DD-MMM": {c:[[nombre, partido, votos], ...], b}}
  gobernacion: {"DD":  {c:[[nombre, partido, votos], ...], b}}
"""
import csv, json, os, sys, collections, time
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Bases de datos')
SRC = os.path.join(BASE, 'FINAL SUBIDA GCS', 'GCS_2023TER.csv')
OUT = os.path.join(BASE, 'nuevo-liberalismo', 'ter2023-agg.json')
ESP = {'996', '997', '998', '999'}

def nuevo(): return {'p': {}, 'b': 0, 'nu': 0}
conc = collections.defaultdict(nuevo)
asam = collections.defaultdict(lambda: {'p': {}, 'b': 0, 'nu': 0, 'm': collections.defaultdict(collections.Counter), 'mb': collections.Counter()})
alc = collections.defaultdict(lambda: {'c': {}, 'b': 0})
gob = collections.defaultdict(lambda: {'c': {}, 'b': 0})

def suma_lista(d, par, nom, can, cnom, v):
    e = d['p'].get(par)
    if e is None: e = d['p'][par] = {'n': nom, 'l': 0, 'c': {}}
    if can == '0': e['l'] += v
    else:
        c = e['c'].get(can)
        if c is None: e['c'][can] = [cnom, v]
        else: c[1] += v

t0 = time.time(); n = 0
with open(SRC, encoding='utf-8-sig', newline='') as fh:
    rd = csv.reader(fh, delimiter=';')
    h = next(rd); ix = {k: i for i, k in enumerate(h)}
    iC, iD, iM, iP, iPN, iK, iKN, iV = (ix[k] for k in ('COD_COR', 'COD_DDE', 'COD_MME', 'COD_PAR', 'DES_PAR', 'COD_CAN', 'DES_CAN', 'NUM_VOT'))
    for r in rd:
        n += 1
        if len(r) < 16: continue
        try: v = int(r[iV])
        except ValueError: continue
        if not v: continue
        cor = r[iC]; dd = r[iD].zfill(2); mm = r[iM].zfill(3); can = r[iK].lstrip('0') or '0'
        if cor == '4':
            d = conc[dd + '-' + mm]
            if can in ESP:
                if can == '996': d['b'] += v
                else: d['nu'] += v
            else: suma_lista(d, r[iP], r[iPN].strip(), can, r[iKN].strip(), v)
        elif cor == '2':
            d = asam[dd]
            if can in ESP:
                if can == '996': d['b'] += v; d['mb'][mm] += v
                else: d['nu'] += v
            else:
                suma_lista(d, r[iP], r[iPN].strip(), can, r[iKN].strip(), v)
                d['m'][mm][r[iP]] += v
        elif cor in ('3', '1'):
            d = (alc[dd + '-' + mm] if cor == '3' else gob[dd])
            if can in ESP:
                if can == '996': d['b'] += v
            else:
                k = r[iP] + '|' + can
                c = d['c'].get(k)
                if c is None: d['c'][k] = [r[iKN].strip(), r[iPN].strip(), v]
                else: c[2] += v
        if n % 4_000_000 == 0: print(n, round(time.time() - t0), 's', file=sys.stderr, flush=True)

out = {
    'concejo': conc,
    'asamblea': {k: {'p': v['p'], 'b': v['b'], 'nu': v['nu'], 'm': {m: dict(c) for m, c in v['m'].items()}, 'mb': dict(v['mb'])} for k, v in asam.items()},
    'alcaldia': {k: {'c': sorted(v['c'].values(), key=lambda x: -x[2]), 'b': v['b']} for k, v in alc.items()},
    'gobernacion': {k: {'c': sorted(v['c'].values(), key=lambda x: -x[2]), 'b': v['b']} for k, v in gob.items()},
}
json.dump(out, open(OUT, 'w'), ensure_ascii=False)
g = out['alcaldia']['16-001']['c'][0]
print('filas', n, '· concejos', len(conc), '· asambleas', len(asam), '· alcaldias', len(alc), '· gobernaciones', len(gob))
print('control Bogotá alcaldía:', g)
assert g[2] == 1499734, 'Galán debe dar 1.499.734'
