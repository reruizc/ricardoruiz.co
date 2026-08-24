#!/usr/bin/env python3
"""Demografía de los votantes de Juvinao por MESA-EF (método del usuario):
estructura demográfica por mesa de 2022 (cache p1v-2022) proyectada como
composición de las mesas 2026, y EI con EFECTOS FIJOS DE PUESTO sobre el voto
preferente de Juvinao por mesa. Esto rompe la confusión ecológica de género
(la variación intra-puesto identifica el efecto) y da edad limpia.

slope δ = efecto intra-puesto de %mujeres (o %jóvenes/%mayores) sobre la tasa
de voto a Juvinao; luego se compone el % de SUS votantes por grupo. IC bootstrap
por puesto."""
import csv, os
import numpy as np
from collections import defaultdict
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"out")
BD="/Users/ricardoruiz/ricardoruiz.co/Bases de datos"
MMV=os.path.join(BD,"DEPTOS_DECLARADOS","MMV_XXX_16_000_XXX_XX_XX_XXX_1009.csv")
CACHE=os.path.join(BD,"output_edad_1v","cache","p1v-2022.csv")
JUV_CED='22698997'; RNG=np.random.default_rng(3)
BOG_LOC={"USAQUEN":"01","CHAPINERO":"02","SANTA FE":"03","SAN CRISTOBAL":"04","USME":"05",
"TUNJUELITO":"06","BOSA":"07","KENNEDY":"08","FONTIBON":"09","ENGATIVA":"10","SUBA":"11",
"BARRIOS UNIDOS":"12","TEUSAQUILLO":"13","LOS MARTIRES":"14","ANTONIO NARINO":"15",
"PUENTE ARANDA":"16","LA CANDELARIA":"17","CANDELARIA":"17","RAFAEL URIBE URIBE":"18",
"RAFAEL URIBE":"18","CIUDAD BOLIVAR":"19","SUMAPAZ":"20","CORFERIAS":"90","CARCELES":"98"}
def nrm(s): return (s or '').upper().strip().replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U')
def ik(s):
    try: return int(s)
    except: return -1
YB=["18 a 20 años","21 a 25 años","26 a 30 años","31 a 35 años"]
AB=["36 a 40 años","41 a 45 años","46 a 50 años","51 a 55 años","56 a 60 años"]
OB=["Mayor a 60 años"]

# --- estructura demográfica por mesa 2022 (Bogotá) ---
demo={}
with open(CACHE,encoding='utf-8') as f:
    for r in csv.DictReader(f):
        loc=BOG_LOC.get(nrm(r["Cód. Comuna / Localidad"]))
        if not loc: continue                       # solo Bogotá (localidad por nombre)
        k=(ik(loc),ik(r["Cód. Puesto de Votación"]),ik(r["Mesa"]))
        muj=float(r["Cantidad de Mujeres"] or 0); hom=float(r["Cantidad Hombres"] or 0)
        tot=muj+hom
        ya=sum(float(r[c] or 0) for c in YB); aa=sum(float(r[c] or 0) for c in AB); oa=sum(float(r[c] or 0) for c in OB)
        tage=ya+aa+oa
        if tot<20 or tage<20: continue
        demo[k]={'wf':muj/tot,'yf':ya/tage,'of':oa/tage}

# --- voto Juvinao + turnout Cámara por mesa 2026 ---
juv=defaultdict(float); cam=defaultdict(float)
with open(MMV,newline='',encoding='utf-8',errors='replace') as f:
    rr=csv.reader(f,delimiter=';'); h=next(rr); ix={x:i for i,x in enumerate(h)}
    iCOR,iCIR,iZ,iP,iM,iCED,iV=ix['CORCODIGO'],ix['CIR'],ix['ZONA'],ix['PUESTO'],ix['MESA'],ix['CANCEDULA'],ix['VOTOS']
    for row in rr:
        if len(row)<=iV or row[iCOR]!='02': continue
        try: v=int(row[iV])
        except: continue
        k=(ik(row[iZ]),ik(row[iP]),ik(row[iM])); cam[k]+=v
        if row[iCIR]=='1' and row[iCED]==JUV_CED: juv[k]+=v

K=[k for k in juv if k in demo and k in cam and cam[k]>0]
print(f"mesas Juvinao∩demografía2022∩turnout: {len(K):,} (de {len(juv):,} con voto Juvinao)")
y=np.array([juv[k]/cam[k] for k in K])             # share Juvinao en la mesa
wf=np.array([demo[k]['wf'] for k in K]); yf=np.array([demo[k]['yf'] for k in K]); of=np.array([demo[k]['of'] for k in K])
pue=np.array([(k[0],k[1]) for k in K])
juvv=np.array([juv[k] for k in K]); camv=np.array([cam[k] for k in K])

# --- within-puesto demean (efectos fijos de puesto) ---
def demean(arr,groups):
    out=arr.copy().astype(float);
    idx=defaultdict(list)
    for i,g in enumerate(map(tuple,groups)): idx[g].append(i)
    for g,ii in idx.items():
        ii=np.array(ii); out[ii]-=out[ii].mean()
    return out
def slope(Y,X):                                     # OLS intra-puesto, X puede ser matriz
    Yd=demean(Y,pue); Xd=np.column_stack([demean(X[:,j],pue) for j in range(X.shape[1])])
    beta,_,_,_=np.linalg.lstsq(Xd,Yd,rcond=None); return beta
# género: 1 regresor (wf). δ>0 => votantes de Juvinao más mujeres
dG=slope(y,wf[:,None])[0]
# edad: 2 regresores (yf, of), adulto = referencia
bA=slope(y,np.column_stack([yf,of]))

def composition_gender(dg):
    # tasa mujeres = base_p + dg ; hombres = base_p ; base_p = media_p(y) - dg*media_p(wf)
    wv=mv=0.0; idx=defaultdict(list)
    for i,g in enumerate(map(tuple,pue)): idx[g].append(i)
    for g,ii in idx.items():
        ii=np.array(ii); basep=y[ii].mean()-dg*wf[ii].mean()
        muj=wf[ii]*camv[ii]; hom=(1-wf[ii])*camv[ii]
        wv+=(muj*(basep+dg)).sum(); mv+=(hom*basep).sum()
    return wv/(wv+mv)
def composition_age(b):
    dy,do=b; jv=jo=ja=0.0; idx=defaultdict(list)
    for i,g in enumerate(map(tuple,pue)): idx[g].append(i)
    for g,ii in idx.items():
        ii=np.array(ii); basep=y[ii].mean()-dy*yf[ii].mean()-do*of[ii].mean()
        ny=yf[ii]*camv[ii]; no=of[ii]*camv[ii]; na=(1-yf[ii]-of[ii])*camv[ii]
        jv+=(ny*(basep+dy)).sum(); jo+=(no*(basep+do)).sum(); ja+=(na*basep).sum()
    t=jv+jo+ja; return jv/t,ja/t,jo/t

wcomp=composition_gender(dG); ycomp,acomp,ocomp=composition_age(bA)
# bootstrap por puesto
puestos=sorted(set(map(tuple,pue))); pidx=defaultdict(list)
for i,g in enumerate(map(tuple,pue)): pidx[g].append(i)
bw=[]; by=[]; bo=[]
for _ in range(300):
    samp=np.concatenate([np.array(pidx[puestos[j]]) for j in RNG.integers(0,len(puestos),len(puestos))])
    Ys=y[samp]; pus=pue[samp]; wfs=wf[samp]; yfs=yf[samp]; ofs=of[samp]; cs=camv[samp]
    def dm(a):
        o=a.astype(float).copy(); idx=defaultdict(list)
        for i,g in enumerate(map(tuple,pus)): idx[g].append(i)
        for g,ii in idx.items(): ii=np.array(ii); o[ii]-=o[ii].mean()
        return o
    dg=(dm(Ys)@dm(wfs))/(dm(wfs)@dm(wfs))
    Xd=np.column_stack([dm(yfs),dm(ofs)]); ba,_,_,_=np.linalg.lstsq(Xd,dm(Ys),rcond=None)
    # composición con esta muestra
    def comp_g(dgg):
        wv=mv=0.0; idx=defaultdict(list)
        for i,g in enumerate(map(tuple,pus)): idx[g].append(i)
        for g,ii in idx.items():
            ii=np.array(ii); basep=Ys[ii].mean()-dgg*wfs[ii].mean()
            wv+=((wfs[ii]*cs[ii])*(basep+dgg)).sum(); mv+=(((1-wfs[ii])*cs[ii])*basep).sum()
        return wv/(wv+mv)
    bw.append(comp_g(dg))
    def comp_a(b):
        dy,do=b; jv=jo=ja=0.0; idx=defaultdict(list)
        for i,g in enumerate(map(tuple,pus)): idx[g].append(i)
        for g,ii in idx.items():
            ii=np.array(ii); basep=Ys[ii].mean()-dy*yfs[ii].mean()-do*ofs[ii].mean()
            jv+=((yfs[ii]*cs[ii])*(basep+dy)).sum(); jo+=((ofs[ii]*cs[ii])*(basep+do)).sum(); ja+=(((1-yfs[ii]-ofs[ii])*cs[ii])*basep).sum()
        t=jv+jo+ja; return jv/t,jo/t
    yy,oo=comp_a(ba); by.append(yy); bo.append(oo)
bw=np.array(bw); by=np.array(by); bo=np.array(bo)
# baseline Bogotá (electorado, ponderado por turnout)
base_w=(wf*camv).sum()/camv.sum(); base_y=(yf*camv).sum()/camv.sum(); base_o=(of*camv).sum()/camv.sum()
print("\n"+"="*70)
print("VOTANTES DE JUVINAO — MESA-EF (efectos fijos de puesto · estructura 2022)")
print("="*70)
print(f"  δ género (intra-puesto): {dG:+.4f}   {'(votantes más MUJERES)' if dG>0 else '(votantes más HOMBRES)'}")
print(f"  % MUJERES:  Juvinao {wcomp*100:.1f}% (IC {np.percentile(bw,2.5)*100:.1f}-{np.percentile(bw,97.5)*100:.1f})   Bogotá {base_w*100:.1f}%")
print(f"  % JÓVENES 18-35: Juvinao {ycomp*100:.1f}% (IC {np.percentile(by,2.5)*100:.1f}-{np.percentile(by,97.5)*100:.1f})   Bogotá {base_y*100:.1f}%")
print(f"  % MAYORES 61+:   Juvinao {ocomp*100:.1f}% (IC {np.percentile(bo,2.5)*100:.1f}-{np.percentile(bo,97.5)*100:.1f})   Bogotá {base_o*100:.1f}%")
print("="*70)
