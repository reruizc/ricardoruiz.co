#!/usr/bin/env python3
"""Set final de senadores (curado por el usuario): 5 del top + Pedraza + Señor
Bíter (Gersson Vargas). Una sola pasada: (1) confirma que cada uno fue ELECTO
(rank por preferente dentro de su lista vs curules D'Hondt del paso 1), (2) corre
el EI individual nacional por mesa estratificado por departamento."""
import csv, glob, os, json
import numpy as np
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "out")
BD = "/Users/ricardoruiz/ricardoruiz.co/Bases de datos"
MMVS = sorted(glob.glob(os.path.join(BD, "DEPTOS_DECLARADOS", "MMV_XXX_*_000_*.csv")))
PRES = os.path.join(BD, "nuevos archivos 1v 2026", "PRECONTEO_1V_2026_MESA_con_Claudia.csv")
RNG = np.random.default_rng(20260616); SHRINK = 0.03; NB = 100

# cédula -> (display, PARNOMBRE de su lista, votos preferente nacional del paso previo)
TARGETS = {
 '52890539':  ('Nadya Blel',         'PARTIDO CONSERVADOR COLOMBIANO'),
 '73547966':  ('Lidio García',       'PARTIDO LIBERAL COLOMBIANO'),
 '1095927582':('Jota Pe Hernández',  'ALIANZA POR COLOMBIA'),
 '8761461':   ('Yessid Pulgar',      'PARTIDO LIBERAL COLOMBIANO'),
 '79468770':  ('Enrique Gómez',      'MOVIMIENTO SALVACIÓN NACIONAL'),
 '1010227070':('Jennifer Pedraza',   'AHORA COLOMBIA'),
 '80032055':  ('Señor Bíter',        'PARTIDO LIBERAL COLOMBIANO'),
}
SEATS = {'PARTIDO CONSERVADOR COLOMBIANO':10,'PARTIDO LIBERAL COLOMBIANO':13,
         'ALIANZA POR COLOMBIA':11,'MOVIMIENTO SALVACIÓN NACIONAL':3,'AHORA COLOMBIA':5}
PARTIES = set(SEATS)
def n(s):
    s=(s or '').strip().upper(); return str(int(s)) if s.isdigit() else s

sen = defaultdict(lambda: defaultdict(int))               # mesa -> cédula -> votos (targets)
prefs = defaultdict(lambda: defaultdict(int))             # PARNOMBRE -> cédula -> preferente nacional
for fp in MMVS:
    dc = os.path.basename(fp).split('_')[2]
    with open(fp, newline='', encoding='utf-8', errors='replace') as f:
        r=csv.reader(f, delimiter=';'); h=next(r); ix={x:i for i,x in enumerate(h)}
        iCOR,iCIR,iMU,iZ,iP,iM,iPARN,iCAN,iCED,iV=ix['CORCODIGO'],ix['CIR'],ix['MUN'],ix['ZONA'],ix['PUESTO'],ix['MESA'],ix['PARNOMBRE'],ix['CAN'],ix['CANCEDULA'],ix['VOTOS']
        for row in r:
            if len(row)<=iV or row[iCOR]!='01' or row[iCIR]!='0': continue
            try: v=int(row[iV])
            except ValueError: continue
            c=row[iCED]
            if c in TARGETS:
                sen[(dc,n(row[iMU]),n(row[iZ]),n(row[iP]),n(row[iM]))][c]+=v
            if row[iCAN]!='000':
                parn=row[iPARN].strip().upper()
                if parn in PARTIES: prefs[parn][c]+=v
    print(f"  {os.path.basename(fp)[:22]}")

# confirmar electos
print("\nConfirmación de ELECTOS (rank por preferente nacional vs curules):")
elected_ok={}
for ced,(nm,pn) in TARGETS.items():
    rank=sorted(prefs[pn].items(), key=lambda x:-x[1])
    pos=next((i for i,(cc,_) in enumerate(rank,1) if cc==ced), None)
    ok = pos is not None and pos<=SEATS[pn]
    elected_ok[ced]=ok
    print(f"  {nm:20} {pn[:26]:26} rank {pos}/{SEATS[pn]}  {'ELECTO ✓' if ok else 'NO ELECTO ✗'}  (pref {prefs[pn].get(ced,0):,})")

# presidencial nacional por mesa
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
    return m.copy() if Ws.sum()==0 else (np.array(Bs)*Ws[:,None]/Ws.sum()).sum(0)
def run(v):
    B=fit_strat(v); bs=np.array([fit_strat(v,boot=True) for _ in range(NB)])
    return B,np.percentile(bs,2.5,0),np.percentile(bs,97.5,0)

vmesa={c:np.array([sen[k].get(c,0) for k in keys],float) for c in TARGETS}
ORDER=['1010227070','80032055','73547966','8761461','1095927582','52890539','79468770']  # Pedraza, Bíter, García, Pulgar, JotaPe, Blel, Gómez
print(f"\nNACIONAL Cepeda {cep.sum()/presT.sum()*100:.1f}% / Abelardo {abe.sum()/presT.sum()*100:.1f}% · mesas {len(keys):,}\n")
print(f"{'Senador/a':20}{'Lista':24}{'→Cepeda':>14}{'→Abelardo':>14}{'→Resto':>8}")
print("-"*82)
out=[]
PSHORT={'PARTIDO CONSERVADOR COLOMBIANO':'Conservador','PARTIDO LIBERAL COLOMBIANO':'Liberal',
        'ALIANZA POR COLOMBIA':'Alianza por Colombia','MOVIMIENTO SALVACIÓN NACIONAL':'Salvación Nacional',
        'AHORA COLOMBIA':'Ahora Colombia'}
for c in ORDER:
    nm,pn=TARGETS[c]; B,lo,hi=run(vmesa[c])
    print(f"{nm:20}{PSHORT[pn]:24}{B[0]*100:4.0f} ({lo[0]*100:.0f}-{hi[0]*100:.0f})"
          f"  {B[1]*100:4.0f} ({lo[1]*100:.0f}-{hi[1]*100:.0f})  {B[2]*100:4.0f}")
    out.append(dict(senador=nm,lista=PSHORT[pn],electo=elected_ok[c],
        votos_pref=prefs[pn].get(c,0),cepeda=round(B[0]*100,1),cepeda_ic=f"{lo[0]*100:.0f}-{hi[0]*100:.0f}",
        abelardo=round(B[1]*100,1),abelardo_ic=f"{lo[1]*100:.0f}-{hi[1]*100:.0f}",resto=round(B[2]*100,1)))
json.dump(out,open(os.path.join(OUT,'senado_final.json'),'w'),ensure_ascii=False,indent=1)
print("\n[out/senado_final.json]")
