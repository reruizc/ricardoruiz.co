#!/usr/bin/env python3
"""Cámara Bogotá → presidencial 1V, ahora a nivel MESA (no puesto).
Mismo método (King's EI condicional, sin censo) pero la unidad es la mesa: las
MISMAS cédulas en marzo y mayo (elecciones del mismo año). ~17k mesas vs 1.078
puestos → más observaciones, identificación más fina. Compara contra el puesto.
"""
import csv, os
import numpy as np
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "out")
BD = "/Users/ricardoruiz/ricardoruiz.co/Bases de datos"
MMV = os.path.join(BD, "DEPTOS_DECLARADOS", "MMV_XXX_16_000_XXX_XX_XX_XXX_1009.csv")
PRES = os.path.join(BD, "nuevos archivos 1v 2026", "PRECONTEO_1V_2026_MESA_con_Claudia.csv")
RNG = np.random.default_rng(20260616); SHRINK = 0.025; NB = 300

OPEN_CED = {'1010199050': 'briceno'}
PARTY = {'cd': 'PARTIDO CENTRO DEMOCRÁTICO', 'verde': 'PARTIDO ALIANZA VERDE',
         'liberal': 'PARTIDO LIBERAL COLOMBIANO', 'salvacion': 'MOVIMIENTO SALVACIÓN NACIONAL'}
PACTO = 'MOVIMIENTO POLÍTICO PACTO HISTÓRICO'
SRCMETA = {'pacto': 'Lista Pacto Histórico', 'briceno': 'Daniel Briceño',
           'cd_resto': 'Resto Centro Democrático', 'verde': 'Lista Alianza Verde',
           'liberal': 'Lista Partido Liberal', 'salvacion': 'Lista Salvación Nacional'}
PUESTO = {'pacto': (73, 13, 13), 'briceno': (14, 58, 28), 'cd_resto': (21, 53, 26),
          'verde': (36, 41, 23), 'liberal': (42, 37, 21), 'salvacion': (34, 43, 23)}

def n(s):
    s = (s or '').strip().upper()
    return str(int(s)) if s.isdigit() else s

# ---- Cámara por mesa ----
cam = defaultdict(lambda: defaultdict(int))
with open(MMV, newline='', encoding='utf-8', errors='replace') as f:
    r = csv.reader(f, delimiter=';'); h = next(r); ix = {x: i for i, x in enumerate(h)}
    iCOR, iCIR, iZ, iP, iM = ix['CORCODIGO'], ix['CIR'], ix['ZONA'], ix['PUESTO'], ix['MESA']
    iPARN, iCED, iV = ix['PARNOMBRE'], ix['CANCEDULA'], ix['VOTOS']
    for row in r:
        if len(row) <= iV or row[iCOR] != '02' or row[iCIR] != '1':
            continue
        try: v = int(row[iV])
        except ValueError: continue
        k = (n(row[iZ]), n(row[iP]), n(row[iM])); parn = row[iPARN].strip().upper()
        if row[iCED] in OPEN_CED: cam[k][OPEN_CED[row[iCED]]] += v
        if parn == PACTO: cam[k]['pacto'] += v
        for sl, pn in PARTY.items():
            if parn == pn: cam[k][sl] += v

# ---- Presidencial por mesa ----
pres = {}
with open(PRES, newline='', encoding='utf-8-sig', errors='replace') as f:
    for row in csv.DictReader(f):
        if row['cod_departamento'].strip('"') != '16': continue
        k = (n(row['zona'].strip('"')), n(row['puesto'].strip('"')), n(row['num_mesa'].strip('"')))
        t = int(row['total_votos_urna'])
        pres[k] = (int(row['Iván Cepeda']), int(row['Abelardo De La Espriella']), t)

keys = [k for k in cam if k in pres and pres[k][2] > 0]
print(f"mesas Cámara∩Presi (con votos): {len(keys):,}  ·  Cámara solo {len(cam):,} · Presi solo {len(pres):,}")

cep = np.array([pres[k][0] for k in keys], float)
abe = np.array([pres[k][1] for k in keys], float)
presT = np.array([pres[k][2] for k in keys], float)
resto = np.maximum(presT - cep - abe, 0)
def col(s): return np.array([cam[k].get(s, 0) for k in keys], float)
V = {'pacto': col('pacto'), 'briceno': col('briceno'),
     'cd_resto': np.maximum(col('cd') - col('briceno'), 0),
     'verde': col('verde'), 'liberal': col('liberal'), 'salvacion': col('salvacion')}
Y = np.column_stack([cep, abe, resto]) / presT[:, None]
m = np.array([cep.sum(), abe.sum(), resto.sum()]) / presT.sum(); B0 = np.column_stack([m, m])
P = len(keys)

def proj(B):
    C = B.shape[0]; u = -np.sort(-B, 0); css = np.cumsum(u, 0) - 1
    j = np.arange(1, C + 1)[:, None]; rho = C - 1 - np.argmax((u - css / j > 0)[::-1], 0)
    tau = css[rho, np.arange(B.shape[1])] / (rho + 1); return np.maximum(B - tau[None, :], 0)
def fit(W, Yy, T, lam, start=None, it=6000):
    G = (W * T[:, None]).T @ W; H = (Yy * T[:, None]).T @ W
    eta = 1 / (2 * (np.linalg.eigvalsh(G).max() + lam)); B = (B0 if start is None else start).copy()
    for _ in range(it):
        Bn = proj(B - eta * (2 * (B @ G - H) + 2 * lam * (B - B0)))
        if np.abs(Bn - B).max() < 1e-12: return Bn
        B = Bn
    return B
def run(v):
    x = np.clip(v / presT, 0, 1); W = np.column_stack([x, 1 - x])
    Bfull = fit(W, Y, presT, SHRINK * presT.sum())
    B = Bfull[:, 0]
    bs = np.empty((NB, 3))
    for b in range(NB):
        idx = RNG.integers(0, P, P)
        bs[b] = fit(W[idx], Y[idx], presT[idx], SHRINK * presT[idx].sum(),
                    start=Bfull, it=4000)[:, 0]
    return B, np.percentile(bs, 2.5, 0), np.percentile(bs, 97.5, 0)

print(f"\nNIVEL MESA · {P:,} mesas · Bogotá Cepeda {cep.sum()/presT.sum()*100:.1f}% / "
      f"Abelardo {abe.sum()/presT.sum()*100:.1f}%\n")
print(f"{'Lista':26}{'MESA  Cep/Abe/Res (IC95 Cep)':>34}     {'PUESTO':>14}")
print("-" * 80)
for s in ['pacto', 'briceno', 'cd_resto', 'verde', 'liberal', 'salvacion']:
    B, lo, hi = run(V[s])
    pc, pa, pr = PUESTO[s]
    print(f"{SRCMETA[s][:25]:26}{B[0]*100:5.0f}/{B[1]*100:3.0f}/{B[2]*100:3.0f}  "
          f"({lo[0]*100:.0f}-{hi[0]*100:.0f})        {pc:3.0f}/{pa:3.0f}/{pr:3.0f}")
print("\n(Comparación con el resultado por puesto del paso 3. Deben coincidir ±pocos pp.)")
