#!/usr/bin/env python3
"""Composición ETARIA de los votantes de Juvinao — EI robusta (no turf).
Regresión con restricción de no-negatividad (NNLS): el voto de Juvinao por puesto
sobre el nº de electores de cada banda etaria (proyección 2026 w26). 3 parámetros
(β = tasa con que cada banda vota Juvinao) sobre 1.078 puestos -> bien identificado.
gamma_a = β_a·(electores banda a) / votos Juvinao = composición de SUS votantes.
Bootstrap de puestos para IC. (Edad por puesto SÍ es válida — es género lo que
invierte a nivel puesto.)"""
import csv, os
import numpy as np
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"out")
BD="/Users/ricardoruiz/ricardoruiz.co/Bases de datos"
RNG=np.random.default_rng(11); SHRINK=0.015
def n2(s):
    s=(s or '').strip().upper(); return f"{int(s):02d}" if s.isdigit() else s

rows=list(csv.DictReader(open(os.path.join(OUT,'puestos_bogota.csv'))))
juv={(n2(r['zz']),n2(r['pp'])):float(r['juvinao']) for r in rows}

# edad proyectada 2026 por puesto (w26) -> counts en 3 bandas
A_age={}
with open(os.path.join(BD,'output_edad_1v','w26-puesto.csv')) as f:
    for row in csv.DictReader(f):
        if not row['pcode'].startswith('16-001'): continue
        p=row['pcode'].split('-'); k=(n2(p[2]),n2(p[3]))
        b=[float(row[f'b{i}']) for i in range(10)]
        A_age[k]=[sum(b[0:4]), sum(b[4:9]), b[9]]   # joven 18-35, adulto 36-60, mayor 61+

K=[k for k in juv if k in A_age and juv[k]>=0]
juvv=np.array([juv[k] for k in K])
A=np.array([A_age[k] for k in K])              # P x 3 (electores por banda)
T=A.sum(axis=1)                                 # electorado del puesto (proy)
W=A/T[:,None]                                   # shares de edad (suma 1) -> NO colineal por tamaño
Y=np.column_stack([juvv/T, 1-juvv/T])           # [Juvinao, resto] / electorado
mrate=juvv.sum()/T.sum()
B0=np.array([[mrate]*3,[1-mrate]*3])            # prior: misma tasa en toda banda (sin sesgo etario)
BANDS=['Jóvenes 18-35','Adultos 36-60','Mayores 61+']

def proj(B):
    C=B.shape[0]; u=-np.sort(-B,0); css=np.cumsum(u,0)-1; j=np.arange(1,C+1)[:,None]
    rho=C-1-np.argmax((u-css/j>0)[::-1],0); tau=css[rho,np.arange(B.shape[1])]/(rho+1)
    return np.maximum(B-tau[None,:],0)
def fit(Wm,Ym,Tm,lam,it=6000):
    G=(Wm*Tm[:,None]).T@Wm; H=(Ym*Tm[:,None]).T@Wm; eta=1/(2*(np.linalg.eigvalsh(G).max()+lam)); B=B0.copy()
    for _ in range(it):
        Bn=proj(B-eta*(2*(B@G-H)+2*lam*(B-B0)))
        if np.abs(Bn-B).max()<1e-12: return Bn
        B=Bn
    return B
def gamma(Wm,Ym,Tm):
    B=fit(Wm,Ym,Tm,SHRINK*Tm.sum())             # B[0,a]=P(Juvinao|banda a)
    contrib=B[0]*(Wm*Tm[:,None]).sum(0)         # votos Juvinao por banda
    return contrib/contrib.sum()

g=gamma(W,Y,T)
P=len(K)
boots=[]
for _ in range(400):
    idx=RNG.integers(0,P,P); boots.append(gamma(W[idx],Y[idx],T[idx]))
boots=np.array(boots); lo,hi=np.percentile(boots,2.5,0),np.percentile(boots,97.5,0)
base=A.sum(axis=0)/A.sum()

print("="*72)
print(f"COMPOSICIÓN ETARIA DE LOS VOTANTES DE JUVINAO (EI · NNLS · {P} puestos)")
print("="*72)
print(f"{'Banda':18}{'Juvinao (IC95%)':>26}{'Electorado Bogotá':>20}")
for i,b in enumerate(BANDS):
    print(f"{b:18}{f'{g[i]*100:.1f}% ({lo[i]*100:.0f}-{hi[i]*100:.0f})':>26}{base[i]*100:>18.1f}%")
print("\nNota: usa la proyección etaria 2026 (turnout presidencial) como estructura de")
print("edad; la edad a nivel puesto es válida (validado en el análisis etario 1V).")
print("Género NO se incluye: requiere género por mesa (mesa-EF), inexistente para 2026.")
import json
json.dump({'bandas':BANDS,'juvinao':[round(x*100,1) for x in g],
           'ic_lo':[round(x*100,1) for x in lo],'ic_hi':[round(x*100,1) for x in hi],
           'bogota':[round(x*100,1) for x in base]},
          open(os.path.join(OUT,'juvinao_edad.json'),'w'),ensure_ascii=False,indent=1)
