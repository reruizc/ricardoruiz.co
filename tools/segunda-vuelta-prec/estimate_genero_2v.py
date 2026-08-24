#!/usr/bin/env python3
"""
Modelo de voto por SEXO para 2V 2026 y 2V 2022 (comparativo), insumo del xlsx por barrio.

Salida -> output_2v/genero-modelo-2v.json:
  gaps     : brecha mujer-hombre en la cuota IZQUIERDA, para 2026 (análogo).
             base 1V 2022 BINARIA izq(Petro) vs der(Fico+Rodolfo) — mejor análogo del
             2V 2026 Cepeda-vs-Abelardo que el 2V 2022 (Rodolfo no es derecha clásica).
  gaps22   : brecha mujer-hombre en la cuota izquierda del 2V 2022 REAL (Petro vs Rodolfo).
             se usa para descomponer por sexo el resultado de 2022 (cada año su propio gap).
  wfrac_puesto   : fracción de mujeres del electorado 2026 por puesto (proyección DANE w26).
  wfrac22_puesto : fracción de mujeres del electorado 2022 por puesto (observada, gen-2022).

Método del gap: MESA con EFECTOS FIJOS DE PUESTO (las cédulas segregan por sexo y las
mesas se asignan por rango -> mesas casi puras de mujeres/hombres dentro del puesto;
comparar dentro del puesto mata el falaz ecológico). Granularidad: comuna/localidad en
Bogotá/Cali/Medellín/Barranquilla, ciudad en el resto, con SHRINKAGE jerárquico
(comuna->ciudad->región->nacional, ponderado por nº de mesas).
"""
import os, sys, csv, json, re, unicodedata
from collections import defaultdict
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
EDAD = os.path.join(HERE, '..', 'edad-1v-2026')
sys.path.insert(0, os.path.abspath(EDAD))
from probe_viabilidad import BOG_LOC, nrm as _nrm, zf      # noqa
from fit_ei import region_of                                # noqa

BD     = os.path.join(HERE, '..', '..', 'Bases de datos')
CACHE  = os.path.join(BD, 'output_edad_1v', 'cache')
MUJ    = os.path.join(BD, 'output_mujeres_1v')
OUT    = os.path.join(BD, 'output_2v')
GEOREF = os.path.join(BD, 'PUESTOS_GEOREF.csv')
MASTER = os.path.join(OUT, 'master_unificado_puesto.json')

K_SHRINK = 1200.0

def nrm(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', str(s or '').upper().strip())
                if unicodedata.category(c) != 'Mn')
    return ' '.join(s.split())
def clean_comuna_name(raw):
    s = ' '.join(str(raw or '').split())
    m = re.match(r'^(\d{2,3})\s*(.+)$', s)
    return nrm(m.group(2)) if m else nrm(s)

CITY = {'16001':'Bogotá','01001':'Medellín','31001':'Cali','03001':'Barranquilla',
        '05001':'Cartagena','25001':'Cúcuta','27001':'Bucaramanga','29001':'Ibagué',
        '24001':'Pereira','52001':'Villavicencio','15247':'Soacha','21001':'Santa Marta',
        '13001':'Montería','23001':'Pasto','09001':'Manizales','03052':'Soledad','11001':'Popayán'}
BIG4 = {'16001','01001','31001','03001'}
CITY_DEPNAME = {'16001':'BOGOTA D.C.','01001':'ANTIOQUIA','31001':'VALLE','03001':'ATLANTICO',
                '05001':'BOLIVAR','25001':'NORTE DE SANTANDER','27001':'SANTANDER','29001':'TOLIMA',
                '24001':'RISARALDA','52001':'META','15247':'CUNDINAMARCA','21001':'MAGDALENA',
                '13001':'CORDOBA','23001':'NARIÑO','09001':'CALDAS','03052':'ATLANTICO','11001':'CAUCA'}

MBANDS = ["Mujeres entre 18 a 20 años","Mujeres entre 21 a 25 años","Mujeres entre 26 a 30 años",
          "Mujeres entre 31 a 35 años","Mujeres entre 36 a 40 años","Mujeres entre 41 a 45 años",
          "Mujeres entre 46 a 50 años","Mujeres entre 51 a 55 años","Mujeres entre 56 a 60 años",
          "Mujeres mayores a 60 años"]
HBANDS = ["Hombres entre 18 a 20 años","Hombres entre 21 a 25 años","Hombres entre 26 a 30 años",
          "Hombres entre 31 a 35 años","Hombres entre 36 a 40 años","Hombres entre 41 a 45 años",
          "Hombres entre 46 a 50 años","Hombres entre 51 a 55 años","Hombres entre 56 a 60 años",
          "Hombres Mayores a 60 años"]
AGE3 = [[0,1,2,3],[4,5,6,7,8],[9]]

DEP2NAME = {}; COMUNA = {}
def load_maps():
    for p in json.load(open(MASTER)):
        COMUNA[p['pcode']] = clean_comuna_name(p.get('comuna'))
    with open(GEOREF, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f, delimiter=';'):
            cc = (r['CÓDIGO COMPLETO'] or '').strip()
            if len(cc) >= 9:
                DEP2NAME.setdefault(cc[:2], (r['DEPARTAMENTO'] or '').strip())
                COMUNA.setdefault(cc, clean_comuna_name(r.get('NOMBRE COMUNA')))
load_maps()
def comuna_geo(p9):
    c5 = p9[:5]
    if c5 not in BIG4: return None
    cm = COMUNA.get(p9, '')
    return f'{CITY[c5]}|{cm}' if cm else None

def load_gender(cache_file):
    df = pd.read_csv(os.path.join(CACHE, cache_file), dtype=str)
    for c in ["Cantidad Hombres","Cantidad de Mujeres"] + MBANDS + HBANDS:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)
    def zona(row):
        z = str(row["Cód. Comuna / Localidad"]).strip()
        return BOG_LOC.get(_nrm(z), z) if not z.isdigit() else zf(z, 2)
    df['zona'] = df.apply(zona, axis=1)
    df['p9'] = (df['Cód. Depto'].map(lambda v: zf(v,2)) + df['Cód. Municipio'].map(lambda v: zf(v,3))
                + df['zona'] + df['Cód. Puesto de Votación'].map(lambda v: zf(v,2)))
    df['mkey'] = df['p9'] + '-' + df['Mesa'].astype(str).str.strip()
    M = df[MBANDS].values; H = df[HBANDS].values
    out = pd.DataFrame({'mkey':df['mkey'],'puesto':df['p9'],
                        'muj':df['Cantidad de Mujeres'],'hom':df['Cantidad Hombres']})
    for i,idx in enumerate(AGE3):
        out[f'M{i}'] = M[:,idx].sum(1); out[f'H{i}'] = H[:,idx].sum(1)
    return out

def load_votes(year_file, mode):
    """izq vs der por mesa. mode '1v' -> izq=Petro, der=Fico+Rodolfo; '2v' -> izq=Petro, der=Rodolfo."""
    acc = defaultdict(lambda: defaultdict(int))
    with open(os.path.join(BD, 'FINAL SUBIDA GCS', year_file), encoding='utf-8-sig') as f:
        for row in csv.DictReader(f, delimiter=';'):
            p9 = zf(row['COD_DDE'],2)+zf(row['COD_MME'],3)+zf(row['COD_ZZ'],2)+zf(row['COD_PP'],2)
            k = p9 + '-' + str(row['DES_MS']).strip()
            v = int(row['NUM_VOT'] or 0); des = (row['DES_CAN'] or '').upper()
            if 'GUSTAVO PETRO' in des: acc[k]['izq'] += v
            elif 'RODOLFO HERNANDEZ' in des or (mode == '1v' and 'FEDERICO GUTIERREZ' in des):
                acc[k]['der'] += v
    return pd.DataFrame([dict(mkey=k, izq=a['izq'], der=a['der'], validos=a['izq']+a['der'])
                         for k,a in acc.items()])

def gap_fe(m):
    m = m[(m['validos'] >= 30) & (m['tot'] >= 30)].copy()
    if len(m) < 40 or m['puesto'].nunique() < 8: return None
    w = m['validos'].astype(float).values
    df = pd.DataFrame({'p': m['puesto'].values, 'w': w,
                       'wsh': (m['muj']/m['tot']).values,
                       'a1': ((m['M1']+m['H1'])/m['tot']).values,
                       'a2': ((m['M2']+m['H2'])/m['tot']).values,
                       'y':  (m['izq']/m['validos']).values})
    def dem(col):
        wm = (df['w']*df[col]).groupby(df['p']).transform('sum') / df['w'].groupby(df['p']).transform('sum')
        return (df[col] - wm).values
    Xd = np.column_stack([dem('wsh'), dem('a1'), dem('a2')]); yd = dem('y'); sw = np.sqrt(w)
    if np.sqrt((Xd[:,0]**2 * w).sum()/w.sum()) < 0.03: return None
    Xw = Xd*sw[:,None]
    try: beta = np.linalg.pinv(Xw.T@Xw) @ (Xw.T@(yd*sw))
    except np.linalg.LinAlgError: return None
    return float(beta[0]), int(len(m))

def shrink(raw, n, parent): return (n*raw + K_SHRINK*parent) / (n + K_SHRINK)

def estimate_gaps(gender_file, votes_file, mode, label):
    print(f'\n[{label}] cargando género ({gender_file}) y votos ({votes_file}, {mode})...', flush=True)
    m = load_gender(gender_file).merge(load_votes(votes_file, mode), on='mkey')
    m['tot'] = m['muj'] + m['hom']
    m = m[(m['tot'] >= 30) & (m['validos'] >= 30)].copy()
    m['region'] = m['puesto'].str[:2].map(lambda d: region_of(DEP2NAME.get(d, '')))
    m['city'] = m['puesto'].map(lambda p: p[:5] if p[:5] in CITY else None)
    m['cgeo'] = m['puesto'].map(comuna_geo)
    NAT = gap_fe(m)[0]
    print(f'  nacional {NAT*100:+.1f} pp  ({len(m):,} mesas)')
    reg_s = {rg: shrink(*gap_fe(gg), NAT) for rg, gg in m.groupby('region') if gap_fe(gg)}
    gaps = {'__national__': {'gap': round(NAT, 4)}}
    city_s = {}
    for c5, name in CITY.items():
        r = gap_fe(m[m['city'] == c5]); parent = reg_s.get(region_of(CITY_DEPNAME[c5]), NAT)
        cs = shrink(r[0], r[1], parent) if r else parent
        city_s[c5] = cs
        if c5 not in BIG4: gaps[f'{name}|*'] = {'gap': round(cs, 4)}
    for c5 in BIG4:
        name = CITY[c5]; parent = city_s[c5]; gaps[f'{name}|*'] = {'gap': round(parent, 4)}
        for cgeo, gg in m[m['city'] == c5].groupby('cgeo'):
            r = gap_fe(gg)
            gaps[cgeo] = {'gap': round(shrink(r[0], r[1], parent) if r else parent, 4)}
    return gaps, NAT

def wfrac_from_w26():
    wf = {}
    with open(os.path.join(MUJ, 'w26-gen-puesto.csv'), encoding='utf-8') as f:
        Hc = [f'H{i}' for i in range(10)]; Mc = [f'M{i}' for i in range(10)]
        for r in csv.DictReader(f):
            pc = r['pcode'].replace('-', '')
            if len(pc) != 9: continue
            muj = sum(float(r[c] or 0) for c in Mc); tot = muj + sum(float(r[c] or 0) for c in Hc)
            if tot > 0: wf[pc] = [round(muj, 1), round(tot, 1)]
    return wf

def wfrac_from_gen2022():
    wf = {}
    with open(os.path.join(MUJ, 'gen-2022-puesto.csv'), encoding='utf-8') as f:
        for r in csv.DictReader(f):
            pc = r['pcode'].replace('-', '')
            if len(pc) != 9: continue
            muj = float(r['Cantidad de Mujeres'] or 0); hom = float(r['Cantidad Hombres'] or 0)
            if muj + hom > 0: wf[pc] = [round(muj, 1), round(muj + hom, 1)]
    return wf

def main():
    gaps26, nat26 = estimate_gaps('p1v-2022.csv', 'GCS_2022PRES1V.csv', '1v', '2026 (análogo 1V izq-der)')
    gaps22, nat22 = estimate_gaps('p2v-2022.csv', 'GCS_2022PRES2V.csv', '2v', '2022 (2V Petro-Rodolfo real)')
    wf26 = wfrac_from_w26(); wf22 = wfrac_from_gen2022()
    f26 = sum(x[0] for x in wf26.values())/sum(x[1] for x in wf26.values())
    f22 = sum(x[0] for x in wf22.values())/sum(x[1] for x in wf22.values())
    print(f'\nfracción mujeres: 2026(DANE) {f26*100:.1f}%  ·  2022(obs) {f22*100:.1f}%')
    print(f'gap nacional izq: 2026 {nat26*100:+.1f}  ·  2022 {nat22*100:+.1f}  '
          f'(la brecha de sexo se AMPLÍA: Abelardo polariza más que Rodolfo)')
    J = {'meta': {'gap_nac_2026_pp': round(nat26*100,2), 'gap_nac_2022_pp': round(nat22*100,2),
                  'fmuj_nacional': round(f26,4), 'fmuj_nacional_2022': round(f22,4),
                  'big4': sorted(CITY[c] for c in BIG4)},
         'gaps': gaps26, 'gaps22': gaps22, 'wfrac_puesto': wf26, 'wfrac22_puesto': wf22}
    json.dump(J, open(os.path.join(OUT,'genero-modelo-2v.json'),'w'), ensure_ascii=False)
    print(f'\n-> {OUT}/genero-modelo-2v.json  (gaps26 {len(gaps26)} · gaps22 {len(gaps22)} · '
          f'puestos26 {len(wf26):,} · puestos22 {len(wf22):,})')

if __name__ == '__main__':
    main()
