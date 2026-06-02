#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""¿Cuántos votos del bloque de Juan Carlos Pinzón (Gran Consulta) fueron a
Paloma en 1ª vuelta? Mesa a mesa: cotas de King + regresión + split restringido."""
import csv, json, os, glob
import numpy as np
from scipy.optimize import nnls, minimize
csv.field_size_limit(1<<24)
ROOT="/Users/ricardoruiz/ricardoruiz.co"
PRE=os.path.join(ROOT,"Bases de datos/nuevos archivos 1v 2026/PRECONTEO_1V_2026_MESA_nombres_corregidos.csv")
MMVDIR=os.path.join(ROOT,"Bases de datos/DEPTOS_DECLARADOS")
CENSO=os.path.join(ROOT,"Bases de datos/censos-puesto-2026.json")
def nz(x):
    x=str(x).strip(); return str(int(x)) if x.isdigit() else x.upper()
def mk(d,m,z,p,me): return f"{d}-{m}-{nz(z)}-{nz(p)}-{nz(me)}"
def pp(d,m,z,p):
    z=f"{int(z):02d}" if str(z).strip().isdigit() else z
    p=f"{int(p):02d}" if str(p).strip().isdigit() else p
    return f"{d}-{m}-{z}-{p}"
PALOMA='PALOMA SUSANA VALENCIA LASERNA'; PINZON='JUAN CARLOS PINZON BUENO'
pres={}; nmesas={}
with open(PRE,encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        k=mk(r['cod_departamento'],r['cod_municipio'],r['zona'],r['puesto'],r['num_mesa'])
        ot=sum(int(r[c]or 0) for c in ['Santiago Botero','Mauricio Lizcano','Sondra Macollins','Roy Barreras','Carlos Caicedo','Gustavo Matamoros','Gilberto Murillo','Claudia López'])
        pres[k]=dict(ab=int(r['Abelardo De La Espriella']or 0),pa=int(r['Paloma Valencia']or 0),
                     ce=int(r['Iván Cepeda']or 0),mu=int(r['Miguel Uribe']or 0),sf=int(r['Sergio Fajardo']or 0),
                     bl=int(r['votos_blanco']or 0),ot=ot,urna=int(r['total_votos_urna']or 0))
        k2=pp(r['cod_departamento'],r['cod_municipio'],r['zona'],r['puesto']); nmesas[k2]=nmesas.get(k2,0)+1
cons={}
for fp in sorted(glob.glob(os.path.join(MMVDIR,"MMV_XXX_*.csv"))):
    if "CITREP" in fp: continue
    with open(fp,encoding='utf-8-sig',newline='') as f:
        rd=csv.reader(f,delimiter=';'); next(rd,None)
        for c in rd:
            if len(c)<19 or c[10]!='06' or c[13]!='0200': continue
            k=mk(c[0],c[2],c[4],c[5],c[7]); v=int(c[18]or 0); d=cons.setdefault(k,{'pal':0,'pin':0,'otg':0})
            if c[17]==PALOMA: d['pal']+=v
            elif c[17]==PINZON: d['pin']+=v
            else: d['otg']+=v
censo=json.load(open(CENSO))['porPuesto']
keys=sorted(set(pres)&set(cons))
PA=[];PI=[];G=[];R=[];AB=[];PAv=[];CE=[];SF=[];MU=[];OTH=[];BL=[];ABST=[]
totPin=0; boundPin={'pa':[0,0],'ab':[0,0],'ce':[0,0]}
for k in keys:
    c=cons[k]; pr=pres[k]; dep,mun,z,p,m=k.split('-')
    ppk=pp(dep,mun,z,p) if z.isdigit() and p.isdigit() else None
    cens=censo.get(ppk); nm=nmesas.get(ppk,1) if ppk else 1
    candpres=pr['ab']+pr['pa']+pr['ce']+pr['mu']+pr['sf']+pr['ot']+pr['bl']
    N=cens/max(nm,1) if cens else None
    if N is None or N<max(candpres,c['pal']+c['pin']+c['otg']): N=max(candpres,c['pal']+c['pin']+c['otg'])
    PA.append(c['pal']);PI.append(c['pin']);G.append(c['otg']);R.append(max(0.0,N-c['pal']-c['pin']-c['otg']))
    AB.append(pr['ab']);PAv.append(pr['pa']);CE.append(pr['ce']);SF.append(pr['sf']);MU.append(pr['mu']);OTH.append(pr['ot']);BL.append(pr['bl'])
    ABST.append(max(0.0,N-candpres)); totPin+=c['pin']
    if c['pin']>0:
        for d,val in [('pa',pr['pa']),('ab',pr['ab']),('ce',pr['ce'])]:
            boundPin[d][0]+=max(0.0,c['pin']+val-N); boundPin[d][1]+=min(c['pin'],val)
X=np.column_stack([PA,PI,G,R]).astype(float)
print(f"Pinzón en la Gran Consulta (mesas cruzadas): {int(totPin):,}\n")
# regresión por destino (tasa sobre bloque Pinzón = col idx 1)
print("Pinzón → destino (regresión por destino):")
for nm_,Y in [('Paloma',PAv),('Abelardo',AB),('Cepeda',CE),('Fajardo',SF),('Miguel Uribe',MU)]:
    coef,_=nnls(X,np.array(Y,float))
    print(f"   → {nm_:<13}{100*coef[1]:5.1f}%   (~{int(coef[1]*totPin):>7,} votos)")
# split restringido (suma 1)
Ymat=np.column_stack([AB,PAv,CE,SF,MU,OTH,BL,ABST]).astype(float)
DN=['Abelardo','Paloma','Cepeda','Fajardo','Miguel Uribe','Otros','Blanco','Abstención']
A_=X.T@X; B_=X.T@Ymat; sc=A_.max(); A_/=sc; B_/=sc; nS,nD=4,8
def f(x):
    T=x.reshape(nS,nD); return sum(T[:,c]@A_@T[:,c]-2*B_[:,c]@T[:,c] for c in range(nD))
def g(x):
    T=x.reshape(nS,nD); G_=np.zeros_like(T)
    for c in range(nD): G_[:,c]=2*(A_@T[:,c]-B_[:,c])
    return G_.ravel()
ceq=[{'type':'eq','fun':(lambda x,b=b:x.reshape(nS,nD)[b,:].sum()-1)} for b in range(nS)]
res=minimize(f,np.full(nS*nD,1/nD),jac=g,method='SLSQP',bounds=[(0,1)]*nS*nD,constraints=ceq,options={'maxiter':1000,'ftol':1e-11})
T=res.x.reshape(nS,nD)
print("\nPinzón → destino (split restringido, suma 100%):")
for c in range(nD):
    if T[1,c]>0.005: print(f"   → {DN[c]:<13}{100*T[1,c]:5.1f}%   (~{int(T[1,c]*totPin):>7,} votos)")
print("\nCotas duras Pinzón→Paloma (mín–máx posible):")
lo=100*boundPin['pa'][0]/totPin; hi=100*boundPin['pa'][1]/totPin
print(f"   [{lo:.1f}% – {hi:.1f}%]  →  entre {int(boundPin['pa'][0]/totPin*totPin):,} y {int(boundPin['pa'][1]):,} votos")
