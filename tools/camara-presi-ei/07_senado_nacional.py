#!/usr/bin/env python3
"""SENADO NACIONAL → presidencial 1V, a nivel MESA, en todo el país.
El Senado es circunscripción nacional: lo honesto es mirar el electorado de
cada lista en TODA Colombia, no solo Bogotá. EI condicional (King's EI) por
mesa, ESTRATIFICADA por región (los punteros presidenciales pesan muy distinto
por región) y agregada con pesos de votos de la lista por región.

Stream de los 34 MMV departamentales (1,6 GB) + preconteo presidencial nacional.
"""
import csv, glob, os
import numpy as np
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "out")
BD = "/Users/ricardoruiz/ricardoruiz.co/Bases de datos"
MMVS = sorted(glob.glob(os.path.join(BD, "DEPTOS_DECLARADOS", "MMV_XXX_*_000_*.csv")))
PRES = os.path.join(BD, "nuevos archivos 1v 2026", "PRECONTEO_1V_2026_MESA_con_Claudia.csv")
RNG = np.random.default_rng(20260616); SHRINK = 0.03; NB = 100

SEN = {'pacto':'PACTO HISTÓRICO SENADO', 'cd':'PARTIDO CENTRO DEMOCRÁTICO',
       'alianza':'ALIANZA POR COLOMBIA', 'ahora':'AHORA COLOMBIA',
       'salvacion':'MOVIMIENTO SALVACIÓN NACIONAL', 'liberal':'PARTIDO LIBERAL COLOMBIANO',
       'cambio':'COALICIÓN CAMBIO RADICAL - ALMA', 'conservador':'PARTIDO CONSERVADOR COLOMBIANO'}
NAME = {'pacto':'Pacto Histórico','cd':'Centro Democrático','alianza':'Alianza por Colombia',
        'ahora':'Ahora Colombia','salvacion':'Salvación Nacional','liberal':'Partido Liberal',
        'cambio':'Cambio Radical','conservador':'Conservador'}

REGION = {}
for n_ in "ATLANTICO BOLIVAR CESAR CORDOBA MAGDALENA SUCRE".split(): REGION[n_]="CARIBE"
REGION.update({"LA GUAJIRA":"CARIBE","GUAJIRA":"CARIBE","SAN ANDRES":"CARIBE"})
for n_ in "ANTIOQUIA CALDAS QUINDIO RISARALDA".split(): REGION[n_]="ANT-EJE"
for n_ in "CAUCA NARINO CHOCO".split(): REGION[n_]="PACIFICO"
REGION.update({"VALLE":"PACIFICO","VALLE DEL CAUCA":"PACIFICO"})
for n_ in "CUNDINAMARCA BOYACA SANTANDER".split(): REGION[n_]="CEN-ORIENTE"
REGION["NORTE DE SANTANDER"]="CEN-ORIENTE"
for n_ in "TOLIMA HUILA CAQUETA PUTUMAYO AMAZONAS".split(): REGION[n_]="SUR"
for n_ in "META CASANARE ARAUCA VICHADA GUAVIARE GUAINIA VAUPES".split(): REGION[n_]="LLANOS"
REGION["BOGOTA DC"]="BOGOTA"
def nrm(s): return (s or '').upper().strip().replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U').replace('.','').replace(' DC','')
def region_of(depname):
    z=nrm(depname)
    if z in REGION: return REGION[z]
    for k,v in REGION.items():
        if k in z or z in k: return v
    return "SUR"

def n(s):
    s=(s or '').strip().upper(); return str(int(s)) if s.isdigit() else s

# ---- senado por mesa, nacional ----
sen = defaultdict(lambda: defaultdict(int)); dep_region = {}
for fp in MMVS:
    depcode = os.path.basename(fp).split('_')[2]
    with open(fp, newline='', encoding='utf-8', errors='replace') as f:
        r=csv.reader(f, delimiter=';'); h=next(r); ix={x:i for i,x in enumerate(h)}
        iCOR,iCIR=ix['CORCODIGO'],ix['CIR']; iDN=ix['DEPNOMBRE']; iMU=ix['MUN']
        iZ,iP,iM,iPARN,iV=ix['ZONA'],ix['PUESTO'],ix['MESA'],ix['PARNOMBRE'],ix['VOTOS']
        for row in r:
            if len(row)<=iV or row[iCOR]!='01' or row[iCIR]!='0': continue
            parn=row[iPARN].strip().upper()
            sl=next((s for s,pn in SEN.items() if parn==pn), None)
            if not sl: continue
            try: v=int(row[iV])
            except ValueError: continue
            k=(depcode,n(row[iMU]),n(row[iZ]),n(row[iP]),n(row[iM])); sen[k][sl]+=v  # +MUN
            if depcode not in dep_region: dep_region[depcode]=region_of(row[iDN])
    print(f"  {os.path.basename(fp)[:22]} · mesas acum {len(sen):,}")

# ---- presidencial nacional por mesa ----
pres={}
with open(PRES, newline='', encoding='utf-8-sig', errors='replace') as f:
    for row in csv.DictReader(f):
        dep=row['cod_departamento'].strip('"')
        k=(dep,n(row['cod_municipio'].strip('"')),n(row['zona'].strip('"')),
           n(row['puesto'].strip('"')),n(row['num_mesa'].strip('"')))   # +MUN
        pres[k]=(int(row['Iván Cepeda']),int(row['Abelardo De La Espriella']),int(row['total_votos_urna']))

keys=[k for k in sen if k in pres and pres[k][2]>0]
cep=np.array([pres[k][0] for k in keys],float); abe=np.array([pres[k][1] for k in keys],float)
presT=np.array([pres[k][2] for k in keys],float); resto=np.maximum(presT-cep-abe,0)
dep=np.array([k[0] for k in keys])          # ESTRATIFICACIÓN POR DEPARTAMENTO
Y=np.column_stack([cep,abe,resto])/presT[:,None]
m=np.array([cep.sum(),abe.sum(),resto.sum()])/presT.sum(); B0=np.column_stack([m,m])
print(f"\nmesas senado∩presi: {len(keys):,} · NACIONAL Cepeda {cep.sum()/presT.sum()*100:.1f}% "
      f"/ Abelardo {abe.sum()/presT.sum()*100:.1f}% / resto {resto.sum()/presT.sum()*100:.1f}%")

def proj(B):
    C=B.shape[0]; u=-np.sort(-B,0); css=np.cumsum(u,0)-1; j=np.arange(1,C+1)[:,None]
    rho=C-1-np.argmax((u-css/j>0)[::-1],0); tau=css[rho,np.arange(B.shape[1])]/(rho+1)
    return np.maximum(B-tau[None,:],0)
def fit(W,Yy,T,lam,start=None,it=4000):
    G=(W*T[:,None]).T@W; H=(Yy*T[:,None]).T@W; eta=1/(2*(np.linalg.eigvalsh(G).max()+lam))
    B=(B0 if start is None else start).copy()
    for _ in range(it):
        Bn=proj(B-eta*(2*(B@G-H)+2*lam*(B-B0)))
        if np.abs(Bn-B).max()<1e-12: return Bn
        B=Bn
    return B
DEPS=sorted(set(dep))
def fit_strat(v, boot=False):
    Bs=[]; Ws=[]
    for d in DEPS:
        sel=np.where(dep==d)[0]
        if len(sel)<8: continue                # depto sin muestra útil para la lista
        if boot: sel=sel[RNG.integers(0,len(sel),len(sel))]
        x=np.clip(v[sel]/presT[sel],0,1); W=np.column_stack([x,1-x]); T=presT[sel]
        Bs.append(fit(W,Y[sel],T,SHRINK*T.sum(),it=2500)[:,0])
        Ws.append((x*T).sum())   # peso depto = votos de la lista entre votantes de mayo
    Ws=np.array(Ws)
    if Ws.sum()==0: return m.copy()
    return (np.array(Bs)*Ws[:,None]/Ws.sum()).sum(0)
def run(v):
    B=fit_strat(v); bs=np.array([fit_strat(v,boot=True) for _ in range(NB)])
    return B, np.percentile(bs,2.5,0), np.percentile(bs,97.5,0)

vmesa={sl:np.array([sen[k].get(sl,0) for k in keys],float) for sl in SEN}
print(f"\n{'Lista (Senado, NACIONAL)':26}{'votos':>11}   {'→ Cepeda':>14}{'→ Abelardo':>13}{'→ Resto':>10}")
print("-"*86)
res={}
order=['pacto','alianza','ahora','liberal','cambio','salvacion','conservador','cd']
for sl in order:
    B,lo,hi=run(vmesa[sl]); res[sl]=(B,lo,hi)
    print(f"{NAME[sl][:25]:26}{int(vmesa[sl].sum()):>11,}   {B[0]*100:4.0f} ({lo[0]*100:.0f}-{hi[0]*100:.0f}) "
          f"  {B[1]*100:4.0f} ({lo[1]*100:.0f}-{hi[1]*100:.0f})  {B[2]*100:4.0f}")

import json
json.dump({sl:{'cep':round(res[sl][0][0]*100,1),'abe':round(res[sl][0][1]*100,1),
               'res':round(res[sl][0][2]*100,1),'votos':int(vmesa[sl].sum())} for sl in res},
          open(os.path.join(OUT,'senado_nacional.json'),'w'), ensure_ascii=False, indent=1)
print("\n[out/senado_nacional.json]  ·  baseline NACIONAL (Abelardo>Cepeda), no Bogotá")
