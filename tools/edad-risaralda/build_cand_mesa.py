#!/usr/bin/env python3
"""Edad por CANDIDATO vía efectos fijos de PUESTO a nivel mesa.
Modelo: share_cand,mesa = γ_puesto + b_y·f_joven + b_o·f_61+ + e
(demean intra-puesto; 36-60 como referencia). Identificación por el
sorting de cédula entre mesas del mismo puesto. IC por bootstrap de
puestos (cluster). Reconstruye tasas por grupo anclando al share real.

Caso: Gobernación 2019 (GCS_2019TER, dep 24) + edad 2019 mesa (real).
"""
import sys, os, json, csv, collections
import numpy as np
OUT="Bases de datos/output_edad_risaralda"
GCS="Bases de datos/FINAL SUBIDA GCS/GCS_2019TER.csv"
BN=["18-20","21-25","26-30","31-35","36-40","41-45","46-50","51-55","56-60","61+"]
GJ=[0,1,2,3]; GO=[9]  # joven 18-35, viejo 61+ (36-60 = referencia)
SPECIAL={"996","997","998","999"}

def load_age_mesa():
    d=json.load(open(os.path.join(OUT,"edad-2019-local-mesa.json")))["mesas"]
    out={}
    for mk,v in d.items():
        s=v["suf"]
        if s<40: continue
        fy=sum(v["bands"][BN[i]] for i in GJ)/s
        fo=sum(v["bands"][BN[i]] for i in GO)/s
        out[mk]={"fy":fy,"fo":fo,"suf":s,"pcode":v["pcode"]}
    return out

def load_gob_mesa():
    # votos por candidato por mesa + válidos por mesa (gobernación, dep 24)
    votes=collections.defaultdict(dict)   # mk -> {cand:votos}
    valid=collections.defaultdict(int)    # mk -> válidos (incl blanco)
    names={}
    with open(GCS, encoding="utf-8") as f:
        r=csv.reader((l.replace('﻿','') for l in f), delimiter=';')
        hdr=next(r)
        idx={h.strip():i for i,h in enumerate(hdr)}
        for row in r:
            if row[idx["COD_DDE"]].strip()!="24": continue
            if str(row[idx["DES_COR"]]).strip().upper()!="GOBERNADOR": continue
            try: mun=int(row[idx["COD_MME"]]); zz=int(row[idx["COD_ZZ"]]); pp=int(row[idx["COD_PP"]]); ms=int(row[idx["DES_MS"]])
            except (ValueError,TypeError): continue
            mk=f"{mun}-{zz:02d}-{pp:02d}-{ms:03d}"
            cod=row[idx["COD_CAN"]].strip(); vot=int(row[idx["NUM_VOT"]] or 0)
            if cod in ("997","998","999"): continue     # nulos / no marcados: NO son válidos
            valid[mk]+=vot                               # válidos = candidatos + blanco(996)
            if cod=="996": continue                     # blanco: válido pero no candidato
            votes[mk][cod]=votes[mk].get(cod,0)+vot
            names[cod]=row[idx["DES_CAN"]].strip()
    return votes, valid, names

def fe_candidate(mesas, cod):
    # mesas: lista de dicts con share, fy, fo, w(=válidos), pcode
    rows=[m for m in mesas if m["w"]>=20]
    # agrupar por puesto y demean ponderado
    byp=collections.defaultdict(list)
    for m in rows: byp[m["pcode"]].append(m)
    Y=[];X=[];W=[];P=[]
    for pc,ms in byp.items():
        if len(ms)<3: continue
        w=np.array([m["w"] for m in ms],float); wt=w/w.sum()
        y=np.array([m["share"] for m in ms]); fy=np.array([m["fy"] for m in ms]); fo=np.array([m["fo"] for m in ms])
        ybar=(y*wt).sum(); fybar=(fy*wt).sum(); fobar=(fo*wt).sum()
        for i in range(len(ms)):
            Y.append(y[i]-ybar); X.append([fy[i]-fybar, fo[i]-fobar]); W.append(w[i]); P.append(pc)
    if len(Y)<40: return None
    Y=np.array(Y);X=np.array(X);W=np.array(W);P=np.array(P)
    def wls(Xa,Ya,Wa):
        sw=np.sqrt(Wa); A=Xa*sw[:,None]; b=Ya*sw
        beta,*_=np.linalg.lstsq(A,b,rcond=None); return beta
    b=wls(X,Y,W)  # [b_young, b_old] relativo a 36-60
    # bootstrap por puesto
    pucods=list(set(P)); rng=np.random.default_rng(7); B=500; boots=[]
    pidx={pc:np.where(P==pc)[0] for pc in pucods}
    for _ in range(B):
        samp=rng.choice(pucods,len(pucods)); ii=np.concatenate([pidx[pc] for pc in samp])
        boots.append(wls(X[ii],Y[ii],W[ii]))
    boots=np.array(boots)
    return {"b":b, "lo":np.percentile(boots,2.5,axis=0), "hi":np.percentile(boots,97.5,axis=0)}

def main():
    age=load_age_mesa(); votes,valid,names=load_gob_mesa()
    # totales por candidato
    tot=collections.defaultdict(int)
    for mk,cv in votes.items():
        for c,v in cv.items(): tot[c]+=v
    cands=sorted(tot,key=lambda c:-tot[c])
    # overall age fractions (ponderado por válidos, sobre mesas con edad)
    fyw=fow=wsum=0
    for mk,val in valid.items():
        a=age.get(mk)
        if not a: continue
        fyw+=a["fy"]*val; fow+=a["fo"]*val; wsum+=val
    Fy=fyw/wsum; Fo=fow/wsum
    print(f"Gobernación 2019 · composición electorado: joven {Fy*100:.0f}% · 36-60 {(1-Fy-Fo)*100:.0f}% · 61+ {Fo*100:.0f}%\n")
    print(f"{'CANDIDATO':34}{'votos':>7} {'share':>6}   18-35 / 36-60 / 61+   (tasa por grupo, IC95)")
    for c in cands:
        if tot[c]<3000: continue
        mesas=[]
        for mk,cv in votes.items():
            a=age.get(mk); val=valid.get(mk,0)
            if not a or val<20: continue
            mesas.append({"share":cv.get(c,0)/val,"fy":a["fy"],"fo":a["fo"],"w":val,"pcode":a["pcode"]})
        r=fe_candidate(mesas,c)
        if not r: continue
        S=tot[c]/sum(valid.values())  # share global aprox
        # reconstruir tasas: r36 tal que promedio ponderado = S
        by,bo=r["b"]; r36=S-by*Fy-bo*Fo
        ry=r36+by; ro=r36+bo
        # IC de las tasas via b IC (aprox: mover b, recomputar)
        ry_lo=r36+r["lo"][0]; ry_hi=r36+r["hi"][0]; ro_lo=r36+r["lo"][1]; ro_hi=r36+r["hi"][1]
        print(f"{names[c][:34]:34}{tot[c]:>7} {S*100:>5.1f}%   {ry*100:>4.0f} / {r36*100:>4.0f} / {ro*100:>4.0f}   young[{ry_lo*100:.0f}–{ry_hi*100:.0f}] old[{ro_lo*100:.0f}–{ro_hi*100:.0f}]")

if __name__=="__main__": main()
