#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Responde 2 preguntas sobre el hilo, a nivel MESA:
   (1) ¿A dónde fueron los votantes de Oviedo (cuánto a Paloma)?  -> cotas + regresión
   (2) ¿De qué bloques de marzo viene el 1,64M de Paloma en 1V?   -> descomposición
"""
import csv, json, os, glob, sys
import numpy as np
from scipy.optimize import nnls
csv.field_size_limit(1<<24)
ROOT="/Users/ricardoruiz/ricardoruiz.co"
PRE=os.path.join(ROOT,"Bases de datos/nuevos archivos 1v 2026/PRECONTEO_1V_2026_MESA_nombres_corregidos.csv")
MMVDIR=os.path.join(ROOT,"Bases de datos/DEPTOS_DECLARADOS")
CENSO=os.path.join(ROOT,"Bases de datos/censos-puesto-2026.json")
def nz(x):
    x=str(x).strip(); return str(int(x)) if x.isdigit() else x.upper()
def mk(dep,mun,z,p,m): return f"{dep}-{mun}-{nz(z)}-{nz(p)}-{nz(m)}"
def pp(dep,mun,z,p):
    z=f"{int(z):02d}" if str(z).strip().isdigit() else z
    p=f"{int(p):02d}" if str(p).strip().isdigit() else p
    return f"{dep}-{mun}-{z}-{p}"
PALOMA='PALOMA SUSANA VALENCIA LASERNA'; OVIEDO='JUAN DANIEL OVIEDO ARANGO'
# presidencial
pres={}; nmesas={}
with open(PRE,encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        k=mk(r['cod_departamento'],r['cod_municipio'],r['zona'],r['puesto'],r['num_mesa'])
        ot=sum(int(r[c]or 0) for c in ['Santiago Botero','Mauricio Lizcano','Sondra Macollins','Roy Barreras','Carlos Caicedo','Gustavo Matamoros','Gilberto Murillo','Claudia López'])
        pres[k]={'ab':int(r['Abelardo De La Espriella']or 0),'pa':int(r['Paloma Valencia']or 0),
                 'ce':int(r['Iván Cepeda']or 0),'mu':int(r['Miguel Uribe']or 0),
                 'sf':int(r['Sergio Fajardo']or 0),'bl':int(r['votos_blanco']or 0),'ot':ot,
                 'urna':int(r['total_votos_urna']or 0)}
        k2=pp(r['cod_departamento'],r['cod_municipio'],r['zona'],r['puesto']); nmesas[k2]=nmesas.get(k2,0)+1
# gran consulta por mesa: Paloma / Oviedo / otros-gran
cons={}
for fp in sorted(glob.glob(os.path.join(MMVDIR,"MMV_XXX_*.csv"))):
    if "CITREP" in fp: continue
    with open(fp,encoding='utf-8-sig',newline='') as f:
        rd=csv.reader(f,delimiter=';'); next(rd,None)
        for c in rd:
            if len(c)<19 or c[10]!='06' or c[13]!='0200': continue
            k=mk(c[0],c[2],c[4],c[5],c[7]); v=int(c[18]or 0); d=cons.setdefault(k,{'pal':0,'ovi':0,'otg':0})
            if c[17]==PALOMA: d['pal']+=v
            elif c[17]==OVIEDO: d['ovi']+=v
            else: d['otg']+=v
censo=json.load(open(CENSO))['porPuesto']
keys=sorted(set(pres)&set(cons))
# matrices
P=[];O=[];G=[];R=[];AB=[];PA=[];CE=[];SF=[];MU=[];OTH=[];BL=[];ABST=[]
totP=totO=0
boundO={'pa':[0,0],'ce':[0,0],'ab':[0,0],'sf':[0,0]}
for k in keys:
    c=cons[k]; pr=pres[k]
    dep,mun,z,p,m=k.split('-')
    ppk=pp(dep,mun,z,p) if z.isdigit() and p.isdigit() else None
    cens=censo.get(ppk); nm=nmesas.get(ppk,1) if ppk else 1
    candpres=pr['ab']+pr['pa']+pr['ce']+pr['mu']+pr['sf']+pr['ot']+pr['bl']
    N=cens/max(nm,1) if cens else None
    if N is None or N<max(candpres,c['pal']+c['ovi']+c['otg']): N=max(candpres,c['pal']+c['ovi']+c['otg'])
    resto=max(0.0,N-c['pal']-c['ovi']-c['otg'])
    P.append(c['pal']);O.append(c['ovi']);G.append(c['otg']);R.append(resto)
    AB.append(pr['ab']);PA.append(pr['pa']);CE.append(pr['ce']);SF.append(pr['sf']);MU.append(pr['mu']);OTH.append(pr['ot']);BL.append(pr['bl'])
    ABST.append(max(0.0,N-candpres))
    totP+=c['pal']; totO+=c['ovi']
    # cotas Oviedo -> destino
    if c['ovi']>0:
        for d,val in [('pa',pr['pa']),('ce',pr['ce']),('ab',pr['ab']),('sf',pr['sf'])]:
            boundO[d][0]+=max(0.0,c['ovi']+val-N); boundO[d][1]+=min(c['ovi'],val)
X=np.column_stack([P,O,G,R]).astype(float)
print(f"Mesas: {len(keys):,} | Paloma consulta {int(totP):,} | Oviedo consulta {int(totO):,}\n")
print("=== (1) ¿A DÓNDE FUE OVIEDO? (regresión por destino, coef sobre bloque Oviedo) ===")
dest=[('Abelardo',AB),('Iván Cepeda',CE),('Sergio Fajardo',SF),('Paloma',PA),('Miguel Uribe',MU),('Otros',OTH),('Blanco',BL),('Abstención',ABST)]
for nm_,Y in dest:
    coef,_=nnls(X,np.array(Y,float))
    print(f"  Oviedo→{nm_:<13} {100*coef[1]:5.1f}%  (~{int(coef[1]*totO):>8,})")
print("\n  Cotas duras Oviedo→destino (mín–máx posible):")
for d,nm_ in [('pa','Paloma'),('ce','Cepeda'),('ab','Abelardo'),('sf','Fajardo')]:
    lo=100*boundO[d][0]/totO; hi=100*boundO[d][1]/totO
    print(f"    Oviedo→{nm_:<9} [{lo:4.1f}% – {hi:4.1f}%]")
print("\n=== (2) ¿DE QUÉ BLOQUES VIENE EL 1,64M DE PALOMA EN 1V? (regresión destino=Paloma_1V) ===")
coef,_=nnls(X,np.array(PA,float))
blocks=['Paloma consulta','Oviedo consulta','Otros Gran Consulta','Resto electorado']
tots=[totP,totO,sum(G),sum(R)]
attrib=[coef[i]*tots[i] for i in range(4)]
s=sum(attrib)
for i in range(4):
    print(f"  desde {blocks[i]:<22} tasa {100*coef[i]:5.2f}%  → ~{int(attrib[i]):>9,}  ({100*attrib[i]/s:4.1f}% del voto 1V de Paloma)")
print(f"  TOTAL atribuido ≈ {int(s):,}  (Paloma 1V real ≈ 1.637.665)")

# ---- versión restringida (filas suman 1) para split limpio ----
from scipy.optimize import minimize
Ymat=np.column_stack([AB,PA,CE,SF,MU,OTH,BL,ABST]).astype(float)  # 8 destinos
DNAMES=['Abelardo','Paloma','Cepeda','Fajardo','Miguel Uribe','Otros','Blanco','Abstención']
A_=X.T@X; B_=X.T@Ymat; sc=A_.max(); A_/=sc; B_/=sc
nS,nD=4,8
def f(x):
    T=x.reshape(nS,nD); return sum(T[:,c]@A_@T[:,c]-2*B_[:,c]@T[:,c] for c in range(nD))
def g(x):
    T=x.reshape(nS,nD); G_=np.zeros_like(T)
    for c in range(nD): G_[:,c]=2*(A_@T[:,c]-B_[:,c])
    return G_.ravel()
ceq=[{'type':'eq','fun':(lambda x,b=b:x.reshape(nS,nD)[b,:].sum()-1)} for b in range(nS)]
res=minimize(f,np.full(nS*nD,1/nD),jac=g,method='SLSQP',bounds=[(0,1)]*nS*nD,constraints=ceq,options={'maxiter':1000,'ftol':1e-11})
T=res.x.reshape(nS,nD)
print("\n=== RESTRINGIDO (filas suman 100%) ===")
for bi,bn in [(1,'OVIEDO'),(0,'PALOMA')]:
    print(f"  {bn} consulta → :")
    for c in range(nD):
        if T[bi,c]>0.005: print(f"      {DNAMES[c]:<14}{100*T[bi,c]:5.1f}%")
