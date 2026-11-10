#!/usr/bin/env python3
"""Congreso 2026 (mesa a mesa de las comisiones) -> votos por PUESTO y partido.

Salida: Bases de datos/nuevo-liberalismo/congreso-puesto.json
  {partidos_sen:[...], partidos_cam:[...],
   puestos:{pcode:{s:{idx:votos}, c:{idx:votos}, sb:blanco, sn:nulos+no marcados, cb:.., cn:..,
                   ac:{CAN:votos}}}}   # ac = Ahora Colombia (Senado) por candidato
Los especiales del MMV de Congreso son CAN 996/997/998 (ver CLAUDE.md).
"""
import csv, glob, json, os, sys, collections
BASE = os.path.join(os.path.dirname(__file__), '..', '..', 'Bases de datos')
SRC = os.path.join(BASE, 'DEPTOS_DECLARADOS')
OUT = os.path.join(BASE, 'nuevo-liberalismo')
os.makedirs(OUT, exist_ok=True)
ps, pc = {}, {}
def idx(d, k):
    if k not in d: d[k] = len(d)
    return d[k]
P = collections.defaultdict(lambda: {'s': collections.Counter(), 'c': collections.Counter(),
                                      'sb': 0, 'sn': 0, 'cb': 0, 'cn': 0, 'ac': collections.Counter()})
cands_ac = {}
tot = collections.Counter()
for f in sorted(glob.glob(os.path.join(SRC, 'MMV_XXX_*.csv'))):
    with open(f, encoding='utf-8-sig', newline='') as fh:
        rd = csv.DictReader(fh, delimiter=';')
        for r in rd:
            try: v = int(r['VOTOS'])
            except Exception: continue
            if not v: continue
            cor = r['CORNOMBRE'].strip().upper()
            cir = r['CIR'].strip()
            pcode = r['DEP'].zfill(2) + r['MUN'].zfill(3) + r['ZONA'].zfill(2) + r['PUESTO'].zfill(2)
            can = r['CAN'].strip(); par = r['PARNOMBRE'].strip()
            e = P[pcode]
            if cor.startswith('SENADO'):
                k = 's'
            elif cor.startswith('CAMARA') or cor.startswith('CÁMARA'):
                k = 'c'
            else:
                tot['otra:' + cor] += v; continue
            if can in ('996', '997', '998'):
                # los especiales se cuentan una sola vez: en la circunscripcion principal
                if (k == 's' and cir in ('0', '1')) or (k == 'c'):
                    if can == '996': e[k + 'b'] += v
                    else: e[k + 'n'] += v
                continue
            tag = par if cir in ('0', '1', '2') else par + ' [CIR ' + cir + ']'
            e[k][idx(ps if k == 's' else pc, tag)] += v
            tot[k + ':' + cir] += v
            if k == 's' and 'AHORA COLOMBIA' in par.upper():
                e['ac'][can] += v
                cands_ac[can] = r['CANNOMBRE'].strip()
    print(os.path.basename(f), len(P), file=sys.stderr)
out = {'partidos_sen': list(ps), 'partidos_cam': list(pc), 'cands_ac': cands_ac,
       'puestos': {k: {'s': dict(v['s']), 'c': dict(v['c']), 'sb': v['sb'], 'sn': v['sn'],
                       'cb': v['cb'], 'cn': v['cn'], 'ac': dict(v['ac'])} for k, v in P.items()}}
json.dump(out, open(os.path.join(OUT, 'congreso-puesto.json'), 'w'), ensure_ascii=False)
print(dict(tot)); print('puestos', len(P), 'partidos sen', len(ps), 'cam', len(pc))
