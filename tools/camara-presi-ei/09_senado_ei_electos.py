#!/usr/bin/env python3
"""Pass 2 — EI individual de los 8 senadores electos más votados (nacional, por
mesa, estratificado por DEPARTAMENTO). x_p = voto preferente del senador / votantes
presidenciales del mesa. Y = [Cepeda, Abelardo, Resto] / votantes presi.
Llave de mesa CON municipio (dep,mun,zona,puesto,mesa)."""
import csv, glob, os, json
import numpy as np
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "out")
BD = "/Users/ricardoruiz/ricardoruiz.co/Bases de datos"
MMVS = sorted(glob.glob(os.path.join(BD, "DEPTOS_DECLARADOS", "MMV_XXX_*_000_*.csv")))
PRES = os.path.join(BD, "nuevos archivos 1v 2026", "PRECONTEO_1V_2026_MESA_con_Claudia.csv")
RNG = np.random.default_rng(20260616); SHRINK = 0.03; NB = 100

TOP8 = json.load(open(os.path.join(OUT, 'senado_electos_top8.json')))
CED = {e['cedula']: e['nombre'] for e in TOP8}            # cédula -> nombre
SHORT = {'NADYA GEORGETTE BLEL SCAFF':'Nadya Blel','LIDIO ARTURO GARCIA TURBAY':'Lidio García',
         'JONATHAN FERNEY PULIDO HERNANDEZ':'Jota Pe Hernández','YESSID ENRIQUE PULGAR DAZA':'Yessid Pulgar',
         'WADITH ALBERTO MANZUR IMBETT':'Wadith Manzur','NORMA HURTADO SANCHEZ':'Norma Hurtado',
         'ENRIQUE GOMEZ MARTINEZ':'Enrique Gómez','JUAN CARLOS GARCES ROJAS':'Juan Carlos Garcés'}
PARTY = {e['cedula']: e['partido'] for e in TOP8}
def n(s):
    s=(s or '').strip().upper(); return str(int(s)) if s.isdigit() else s

# ---- voto preferente por mesa de los 8 ----
sen = defaultdict(lambda: defaultdict(int))
for fp in MMVS:
    dc = os.path.basename(fp).split('_')[2]
    with open(fp, newline='', encoding='utf-8', errors='replace') as f:
        r=csv.reader(f, delimiter=';'); h=next(r); ix={x:i for i,x in enumerate(h)}
        iCOR,iCIR,iMU,iZ,iP,iM,iCED,iV=ix['CORCODIGO'],ix['CIR'],ix['MUN'],ix['ZONA'],ix['PUESTO'],ix['MESA'],ix['CANCEDULA'],ix['VOTOS']
        for row in r:
            if len(row)<=iV or row[iCOR]!='01' or row[iCIR]!='0': continue
            c=row[iCED]
            if c not in CED: continue
            try: v=int(row[iV])
            except ValueError: continue
            sen[(dc,n(row[iMU]),n(row[iZ]),n(row[iP]),n(row[iM]))][c]+=v
    print(f"  {os.path.basename(fp)[:22]}")

# ---- presidencial nacional por mesa ----
pres={}
with open(PRES, newline='', encoding='utf-8-sig', errors='replace') as f:
    for row in csv.DictReader(f):
        k=(row['cod_departamento'].strip('"'),n(row['cod_municipio'].strip('"')),
           n(row['zona'].strip('"')),n(row['puesto'].strip('"')),n(row['num_mesa'].strip('"')))
        pres[k]=(int(row['Iván Cepeda']),int(row['Abelardo De La Espriella']),int(row['total_votos_urna']))

keys=[k for k in sen if k in pres and pres[k][2]>0]
cep=np.array([pres[k][0] for k in keys],float); abe=np.array([pres[k][1] for k in keys],float)
presT=np.array([pres[k][2] for k in keys],float); resto=np.maximum(presT-cep-abe,0)
dep=np.array([k[0] for k in keys])
Y=np.column_stack([cep,abe,resto])/presT[:,None]
m=np.array([cep.sum(),abe.sum(),resto.sum()])/presT.sum(); B0=np.column_stack([m,m])
print(f"\nmesas con voto de los 8 ∩ presi: {len(keys):,}")

def proj(B):
    C=B.shape[0]; u=-np.sort(-B,0); css=np.cumsum(u,0)-1; j=np.arange(1,C+1)[:,None]
    rho=C-1-np.argmax((u-css/j>0)[::-1],0); tau=css[rho,np.arange(B.shape[1])]/(rho+1)
    return np.maximum(B-tau[None,:],0)
def fit(W,Yy,T,lam,it=2500):
    G=(W*T[:,None]).T@W; H=(Yy*T[:,None]).T@W; eta=1/(2*(np.linalg.eigvalsh(G).max()+lam)); B=B0.copy()
    for _ in range(it):
        Bn=proj(B-eta*(2*(B@G-H)+2*lam*(B-B0)))
        if np.abs(Bn-B).max()<1e-12: return Bn
        B=Bn
    return B
DEPS=sorted(set(dep))
def fit_strat(v,boot=False):
    Bs=[];Ws=[]
    for d in DEPS:
        sel=np.where(dep==d)[0]
        if len(sel)<8: continue
        if boot: sel=sel[RNG.integers(0,len(sel),len(sel))]
        x=np.clip(v[sel]/presT[sel],0,1); W=np.column_stack([x,1-x]); T=presT[sel]
        Bs.append(fit(W,Y[sel],T,SHRINK*T.sum())[:,0]); Ws.append((x*T).sum())
    Ws=np.array(Ws)
    if Ws.sum()==0: return m.copy()
    return (np.array(Bs)*Ws[:,None]/Ws.sum()).sum(0)
def run(v):
    B=fit_strat(v); bs=np.array([fit_strat(v,boot=True) for _ in range(NB)])
    return B, np.percentile(bs,2.5,0), np.percentile(bs,97.5,0)

vmesa={c:np.array([sen[k].get(c,0) for k in keys],float) for c in CED}
print(f"\nNACIONAL Cepeda {cep.sum()/presT.sum()*100:.1f}% / Abelardo {abe.sum()/presT.sum()*100:.1f}%\n")
print(f"{'#':>2} {'Senador/a':20}{'Lista':24}{'→Cepeda':>15}{'→Abelardo':>15}{'→Resto':>8}")
print("-"*86)
out=[]
for e in TOP8:
    c=e['cedula']; B,lo,hi=run(vmesa[c])
    nm=SHORT.get(e['nombre'],e['nombre']); pa=PARTY[c].title()[:22]
    print(f"{e['rank']:>2} {nm[:19]:20}{pa:24}{B[0]*100:5.0f} ({lo[0]*100:.0f}-{hi[0]*100:.0f})"
          f"  {B[1]*100:5.0f} ({lo[1]*100:.0f}-{hi[1]*100:.0f})  {B[2]*100:4.0f}")
    out.append(dict(rank=e['rank'],senador=nm,partido=PARTY[c],votos=e['votos'],
        cepeda=round(B[0]*100,1),cepeda_ic=f"{lo[0]*100:.0f}-{hi[0]*100:.0f}",
        abelardo=round(B[1]*100,1),abelardo_ic=f"{lo[1]*100:.0f}-{hi[1]*100:.0f}",
        resto=round(B[2]*100,1)))
json.dump(out,open(os.path.join(OUT,'senado_ei_electos.json'),'w'),ensure_ascii=False,indent=1)
print("\n[out/senado_ei_electos.json]  ·  EI individual, nacional, por departamento")
