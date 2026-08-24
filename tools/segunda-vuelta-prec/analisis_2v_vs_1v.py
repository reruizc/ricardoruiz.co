#!/usr/bin/env python3
# Decompone DONDE se define la 2V (Abelardo vs Cepeda) contrastando contra el
# preconteo 1V por mesa (archivo interno). Agrega 1V por municipio (13 cands),
# lo cruza con el 2V municipal del feed y produce varias lentes:
#   - reconciliacion nacional (1V head-to-head, 2V, bloque esperado)
#   - tabla por departamento
#   - top municipios por margen neto 2V (donde se "banca" la victoria)
#   - top municipios por movimiento vs 1V (Delta margen head-to-head)
#   - flips de ganador head-to-head 1V -> 2V
#   - over/under-performance vs trasvase de bloques 1V
#   - lente de participacion
import csv, json, sys

CSV_1V = 'Bases de datos/nuevos archivos 1v 2026/PRECONTEO_1V_2026_MESA_con_Claudia.csv'
J_2V   = 'tools/segunda-vuelta-prec/dos_vuelta_municipios.json'

# pesos de trasvase de bloques 1V (identicos a build_anclas.py)
W_CEP = {'Iván Cepeda':1.0,'Sergio Fajardo':0.55,'Claudia López':0.65,
         'Roy Barreras':0.85,'Carlos Caicedo':0.85,'Gilberto Murillo':0.85}
W_ABE = {'Abelardo De La Espriella':1.0,'Paloma Valencia':0.85,'Miguel Uribe':0.78,
         'Gustavo Matamoros':0.78,'Santiago Botero':0.78,'Sondra Macollins':0.78,
         'Mauricio Lizcano':0.55}
CANDS = list(W_CEP) + [c for c in W_ABE if c not in W_CEP]

DEPN = {'01':'Antioquia','03':'Atlántico','05':'Bolívar','07':'Boyacá','09':'Caldas',
        '11':'Cauca','12':'Cesar','13':'Córdoba','15':'Cundinamarca','16':'Bogotá D.C.',
        '17':'Chocó','19':'Huila','21':'Magdalena','23':'Nariño','24':'Risaralda',
        '25':'N. de Santander','26':'Quindío','27':'Santander','28':'Sucre','29':'Tolima',
        '31':'Valle','40':'Arauca','44':'Caquetá','46':'Casanare','48':'La Guajira',
        '50':'Guainía','52':'Meta','54':'Guaviare','56':'San Andrés','60':'Amazonas',
        '64':'Putumayo','68':'Vaupés','72':'Vichada','88':'Exterior'}

# ---- 1) agrega 1V por municipio ----
mun1v = {}
with open(CSV_1V, encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        key = r['cod_departamento'].zfill(2) + r['cod_municipio'].zfill(3)
        m = mun1v.setdefault(key, {c: 0 for c in CANDS} | {'votant': 0})
        for c in CANDS:
            m[c] += int(r[c] or 0)
        m['votant'] += int(r['total_votos_urna'] or 0)

# ---- 2) carga 2V municipal ----
d2 = json.load(open(J_2V))['munis']

# ---- 3) construye tabla cruzada ----
rows = []
for key, v2 in d2.items():
    dep = key[:2]
    m1 = mun1v.get(key)
    cep1 = m1['Iván Cepeda'] if m1 else 0
    abe1 = m1['Abelardo De La Espriella'] if m1 else 0
    cepx = sum(m1[c]*w for c, w in W_CEP.items()) if m1 else 0   # bloque esperado
    abex = sum(m1[c]*w for c, w in W_ABE.items()) if m1 else 0
    cep2, abe2 = v2['cep2v'], v2['abe2v']
    base2 = cep2 + abe2
    rows.append({
        'key': key, 'dep': dep, 'depn': DEPN.get(dep, dep), 'nombre': v2['nombre'],
        'cep1': cep1, 'abe1': abe1, 'cep2': cep2, 'abe2': abe2,
        'cepx': cepx, 'abex': abex,
        'mar1': abe1 - cep1, 'mar2': abe2 - cep2,
        'dmar': (abe2 - cep2) - (abe1 - cep1),
        'votant1': m1['votant'] if m1 else 0, 'votant2': v2['votant2v'],
        'base2': base2,
        'share2': (abe2/base2) if base2 else 0,
        'sharex': (abex/(abex+cepx)) if (abex+cepx) else 0,
        'matched': m1 is not None,
    })

# over-performance de Abelardo vs bloque esperado (pp), y en votos
for r in rows:
    r['over_pp'] = (r['share2'] - r['sharex']) * 100 if r['matched'] else 0
    r['over_votos'] = (r['share2'] - r['sharex']) * r['base2'] if r['matched'] else 0

def fmt(n): return f'{n:,}'.replace(',', '.')

# ===== NACIONAL =====
T = lambda k: sum(r[k] for r in rows)
cep1, abe1, cep2, abe2 = T('cep1'), T('abe1'), T('cep2'), T('abe2')
cepx, abex = T('cepx'), T('abex')
print('='*78)
print('RECONCILIACION NACIONAL')
print('='*78)
print(f"1V head-to-head:  Cepeda {fmt(cep1)}  vs  Abelardo {fmt(abe1)}   "
      f"-> Abelardo +{fmt(abe1-cep1)}")
print(f"2V real:          Cepeda {fmt(cep2)}  vs  Abelardo {fmt(abe2)}   "
      f"-> Abelardo +{fmt(abe2-cep2)} ({100*(abe2-cep2)/(abe2+cep2):.2f}pp)")
print(f"Bloque 1V esperado: Cep {fmt(int(cepx))} vs Abe {fmt(int(abex))} "
      f"-> share Abe esperado {100*abex/(abex+cepx):.2f}%  (real {100*abe2/(abe2+cep2):.2f}%)")
print(f"=> El 2V se movio {fmt((abe2-cep2)-(abe1-cep1))} en votos head-to-head "
      f"(negativo = hacia Cepeda)")
print(f"=> vs trasvase esperado, Abelardo quedo {100*abe2/(abe2+cep2)-100*abex/(abex+cepx):+.2f}pp")
print(f"participacion: 1V {fmt(T('votant1'))}  2V {fmt(T('votant2'))}  "
      f"(+{fmt(T('votant2')-T('votant1'))})")
unm = [r for r in rows if not r['matched']]
print(f"municipios sin match 1V: {len(unm)} "
      f"(Abe2V {fmt(sum(r['abe2'] for r in unm))} / Cep2V {fmt(sum(r['cep2'] for r in unm))})")

# ===== DEPARTAMENTO =====
print('\n'+'='*78)
print('POR DEPARTAMENTO (ordenado por margen neto 2V de Abelardo)')
print('='*78)
print(f"{'Depto':17s}{'Cep2V':>11s}{'Abe2V':>11s}{'margAbe2V':>11s}"
      f"{'margAbe1V':>11s}{'Δmarg':>10s}{'over_pp':>8s}")
byd = {}
for r in rows:
    d = byd.setdefault(r['dep'], {k: 0 for k in
        ['cep1','abe1','cep2','abe2','cepx','abex','votant1','votant2']})
    for k in d: d[k] += r[k]
for dep, d in sorted(byd.items(), key=lambda kv: -(kv[1]['abe2']-kv[1]['cep2'])):
    m2 = d['abe2']-d['cep2']; m1 = d['abe1']-d['cep1']
    over = (d['abe2']/(d['abe2']+d['cep2']) - d['abex']/(d['abex']+d['cepx']))*100 \
           if (d['abex']+d['cepx'] and d['abe2']+d['cep2']) else 0
    print(f"{DEPN.get(dep,dep):17s}{fmt(d['cep2']):>11s}{fmt(d['abe2']):>11s}"
          f"{m2:>+11,}{m1:>+11,}{m2-m1:>+10,}{over:>+8.1f}".replace(',', '.'))

def top(rs, key, n=18, rev=True):
    return sorted(rs, key=lambda r: r[key], reverse=rev)[:n]

big = [r for r in rows if r['base2'] >= 3000]  # filtra municipios chicos para señal

print('\n'+'='*78)
print('A) DONDE SE BANCA LA VICTORIA — top municipios por margen NETO 2V Abelardo')
print('='*78)
for r in top(rows, 'mar2'):
    print(f"  {r['nombre'][:24]:24s} {r['depn'][:14]:14s} "
          f"Abe {fmt(r['abe2']):>9s} Cep {fmt(r['cep2']):>9s} -> +{fmt(r['mar2'])}")
print('  ... contrapeso de Cepeda (margen neto 2V a su favor):')
for r in top(rows, 'mar2', rev=False)[:10]:
    print(f"  {r['nombre'][:24]:24s} {r['depn'][:14]:14s} "
          f"Cep {fmt(r['cep2']):>9s} Abe {fmt(r['abe2']):>9s} -> Cep +{fmt(-r['mar2'])}")

print('\n'+'='*78)
print('B) MOVIMIENTO vs 1V — municipios que MAS se movieron hacia Abelardo (Δmargen)')
print('='*78)
for r in top(big, 'dmar'):
    print(f"  {r['nombre'][:24]:24s} {r['depn'][:13]:13s} "
          f"Δmarg {r['dmar']:>+8,}  (1V {r['mar1']:>+7,} -> 2V {r['mar2']:>+7,})".replace(',', '.'))
print('\n   ... y los que MAS se movieron hacia Cepeda (donde casi pierde Abelardo):')
for r in top(big, 'dmar', rev=False):
    print(f"  {r['nombre'][:24]:24s} {r['depn'][:13]:13s} "
          f"Δmarg {r['dmar']:>+8,}  (1V {r['mar1']:>+7,} -> 2V {r['mar2']:>+7,})".replace(',', '.'))

print('\n'+'='*78)
print('C) OVER-PERFORMANCE de Abelardo vs trasvase esperado (votos ganados de mas)')
print('='*78)
print('   donde Abelardo saco MAS que el bloque 1V predijo (>=3000 votos base):')
for r in top(big, 'over_votos'):
    print(f"  {r['nombre'][:24]:24s} {r['depn'][:13]:13s} "
          f"+{fmt(int(r['over_votos'])):>8s} votos  ({r['over_pp']:+.1f}pp; "
          f"real {100*r['share2']:.1f}% vs esp {100*r['sharex']:.1f}%)")
print('\n   donde Cepeda saco mas que lo esperado (over-performance de la izquierda):')
for r in top(big, 'over_votos', rev=False):
    print(f"  {r['nombre'][:24]:24s} {r['depn'][:13]:13s} "
          f"{fmt(int(r['over_votos'])):>9s} votos  ({r['over_pp']:+.1f}pp; "
          f"real {100*r['share2']:.1f}% vs esp {100*r['sharex']:.1f}%)")

# ===== FLIPS =====
flips_a = [r for r in rows if r['matched'] and r['mar1'] < 0 and r['mar2'] > 0]  # Cep1V -> Abe2V
flips_c = [r for r in rows if r['matched'] and r['mar1'] > 0 and r['mar2'] < 0]  # Abe1V -> Cep2V
print('\n'+'='*78)
print(f'D) FLIPS head-to-head: Cepeda ganaba 1V -> Abelardo gana 2V: {len(flips_a)} munis')
print(f'                       Abelardo ganaba 1V -> Cepeda gana 2V: {len(flips_c)} munis')
print('='*78)
print('  Cep1V->Abe2V (mas grandes por base 2V):')
for r in sorted(flips_a, key=lambda r: -r['base2'])[:12]:
    print(f"  {r['nombre'][:24]:24s} {r['depn'][:13]:13s} "
          f"base {fmt(r['base2']):>8s}  1V {r['mar1']:>+7,} -> 2V {r['mar2']:>+6,}".replace(',', '.'))
print('  Abe1V->Cep2V (mas grandes por base 2V):')
for r in sorted(flips_c, key=lambda r: -r['base2'])[:12]:
    print(f"  {r['nombre'][:24]:24s} {r['depn'][:13]:13s} "
          f"base {fmt(r['base2']):>8s}  1V {r['mar1']:>+7,} -> 2V {r['mar2']:>+6,}".replace(',', '.'))

# ---- dump CSV completo ----
out = 'tools/segunda-vuelta-prec/municipios_2v_vs_1v.csv'
with open(out, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['cod','depto','municipio','cep1v','abe1v','margen1v','cep2v','abe2v',
                'margen2v','delta_margen','share_abe2v_pct','share_abe_esperado_pct',
                'over_pp','over_votos','votant1v','votant2v','delta_votant','matched'])
    for r in sorted(rows, key=lambda r: (r['dep'], r['nombre'])):
        w.writerow([r['key'], r['depn'], r['nombre'], r['cep1'], r['abe1'], r['mar1'],
            r['cep2'], r['abe2'], r['mar2'], r['dmar'], round(100*r['share2'],2),
            round(100*r['sharex'],2), round(r['over_pp'],2), int(r['over_votos']),
            r['votant1'], r['votant2'], r['votant2']-r['votant1'], int(r['matched'])])
print(f'\nCSV completo -> {out}')
