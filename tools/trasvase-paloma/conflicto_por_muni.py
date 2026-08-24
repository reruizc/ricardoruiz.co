#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-municipio: Petro 1V-2022 vs Cepeda 1V-2026 en municipios de conflicto (CITREP).
Exporta JSON + imprime tabla y excepciones (flips a Abelardo + mayores caídas de la izquierda)."""
import csv, glob, collections, json
def k(d, m): return f"{int(d)}-{int(m)}"

# 1) municipios CITREP (código electoral dep-mun + nombres)
conflict = {}
for fp in glob.glob('Bases de datos/DEPTOS_DECLARADOS/CITREP*-MMV*.csv'):
    with open(fp, encoding='utf-8-sig', newline='') as f:
        rd = csv.reader(f, delimiter=';'); h = next(rd); ix = {c.strip(): i for i, c in enumerate(h)}
        for r in rd:
            if len(r) <= ix['MUNNOMBRE']: continue
            try: conflict[k(r[ix['DEP']], r[ix['MUN']])] = (r[ix['DEPNOMBRE']].strip(), r[ix['MUNNOMBRE']].strip())
            except: pass
print(f"municipios CITREP: {len(conflict)}")

# 2) Petro 2022 1V
p22 = collections.defaultdict(lambda: {'petro': 0, 'val': 0})
with open('Bases de datos/FINAL SUBIDA GCS/GCS_2022PRES1V.csv', encoding='utf-8-sig', errors='replace') as f:
    rd = csv.reader(f, delimiter=';'); h = next(rd); ix = {c.strip(): i for i, c in enumerate(h)}
    for r in rd:
        if len(r) <= ix['NUM_VOT']: continue
        try: key = k(r[ix['COD_DDE']], r[ix['COD_MME']])
        except: continue
        if key not in conflict: continue
        cod = r[ix['COD_CAN']]; v = int(r[ix['NUM_VOT']] or 0)
        if cod and cod.isdigit() and int(cod) >= 996: continue
        p22[key]['val'] += v
        if 'PETRO' in r[ix['DES_CAN']].upper(): p22[key]['petro'] += v

# 3) Cepeda + Abelardo 2026 1V (preconteo por mesa, nombres corregidos)
CANDS = ['Iván Cepeda', 'Santiago Botero', 'Abelardo De La Espriella', 'Mauricio Lizcano', 'Miguel Uribe',
         'Sondra Macollins', 'Roy Barreras', 'Carlos Caicedo', 'Gustavo Matamoros', 'Paloma Valencia',
         'Sergio Fajardo', 'Gilberto Murillo', 'Claudia López']
c26 = collections.defaultdict(lambda: {'ce': 0, 'ab': 0, 'val': 0})
with open('Bases de datos/nuevos archivos 1v 2026/PRECONTEO_1V_2026_MESA_nombres_corregidos.csv', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        try: key = k(r['cod_departamento'], r['cod_municipio'])
        except: continue
        if key not in conflict: continue
        c26[key]['ce'] += int(r['Iván Cepeda'] or 0)
        c26[key]['ab'] += int(r['Abelardo De La Espriella'] or 0)
        c26[key]['val'] += sum(int(r[c] or 0) for c in CANDS)

# 4) tabla por muni
rows = []
for key, (dn, mn) in conflict.items():
    pv, cv = p22[key]['val'], c26[key]['val']
    if pv < 100 or cv < 100: continue
    pp = 100 * p22[key]['petro'] / pv
    cp = 100 * c26[key]['ce'] / cv
    ap = 100 * c26[key]['ab'] / cv
    rows.append({
        'key': key, 'dep': dn, 'mun': mn,
        'petro_pct': round(pp, 1), 'cepeda_pct': round(cp, 1), 'abelardo_pct': round(ap, 1),
        'delta_pp': round(cp - pp, 1),
        'val22': pv, 'val26': cv,
        'cepeda_v': c26[key]['ce'], 'abelardo_v': c26[key]['ab'],
        'gana26': 'Cepeda' if c26[key]['ce'] >= c26[key]['ab'] else 'Abelardo',
        'petro_gano22': p22[key]['petro'] / pv > 0.5 if pv else False,
    })

# nacional agregado
PE = sum(p22[r['key']]['petro'] for r in rows); PV = sum(r['val22'] for r in rows)
CE = sum(r['cepeda_v'] for r in rows); CV = sum(r['val26'] for r in rows)
AB = sum(r['abelardo_v'] for r in rows)
print(f"\nAGREGADO CITREP ({len(rows)} muns con datos):")
print(f"  Petro22:  {PE:>9,} / {PV:>9,} = {100*PE/PV:.1f}%")
print(f"  Cepeda26: {CE:>9,} / {CV:>9,} = {100*CE/CV:.1f}%")
print(f"  Abelardo26: {AB:>9,} = {100*AB/CV:.1f}%   |  Δ izq pp = {100*CE/CV-100*PE/PV:+.1f}")

# flips: Petro ganó 2022 y Abelardo gana 2026
flips = [r for r in rows if r['petro_gano22'] and r['gana26'] == 'Abelardo']
print(f"\nFLIPS Petro22→Abelardo26 ({len(flips)}):")
for r in sorted(flips, key=lambda x: -x['val26']):
    print(f"  {r['mun']:<22}{r['dep']:<16} Petro {r['petro_pct']:.0f}%  Cepeda {r['cepeda_pct']:.0f}%  Abelardo {r['abelardo_pct']:.0f}%  (val26={r['val26']:,})")

# mayores caídas de la izquierda (Petro% -> Cepeda%), con tamaño relevante
print("\nMAYORES CAÍDAS izquierda (Δpp, val26>=300):")
for r in sorted([x for x in rows if x['val26'] >= 300], key=lambda x: x['delta_pp'])[:18]:
    print(f"  {r['mun']:<22}{r['dep']:<16} Petro {r['petro_pct']:>4.0f}% → Cepeda {r['cepeda_pct']:>4.0f}%  {r['delta_pp']:>+5.1f}  gana26={r['gana26']}  (val26={r['val26']:,})")

# mayores subidas (para contexto del 14/15)
print("\nMAYORES SUBIDAS izquierda (Δpp, top):")
for r in sorted([x for x in rows if x['val26'] >= 300], key=lambda x: -x['delta_pp'])[:6]:
    print(f"  {r['mun']:<22}{r['dep']:<16} Petro {r['petro_pct']:>4.0f}% → Cepeda {r['cepeda_pct']:>4.0f}%  {r['delta_pp']:>+5.1f}")

json.dump(rows, open('/tmp/conflicto_por_muni.json', 'w'), ensure_ascii=False)
print(f"\n→ /tmp/conflicto_por_muni.json ({len(rows)} muns)")
