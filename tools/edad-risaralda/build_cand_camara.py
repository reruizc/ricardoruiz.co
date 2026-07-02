#!/usr/bin/env python3
"""Edad por CANDIDATO de Cámara 2026 vía efectos fijos de puesto (mesa).
Voto por candidato por mesa del escrutinio MMV (declarados). Edad en la mesa
= edad 2022 congreso de la misma mesa (75% casan; mismo tipo de elección),
opcionalmente corrida por DANE. Mesa-FE con el sorting de cédula → IC.
"""
import sys, os, json, csv, collections
import numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from build_cand_mesa import fe_candidate
OUT="Bases de datos/output_edad_risaralda"
MMV="Bases de datos/DEPTOS_DECLARADOS/MMV_XXX_24_000_XXX_XX_XX_XXX_1014.csv"
BN=["18-20","21-25","26-30","31-35","36-40","41-45","46-50","51-55","56-60","61+"]
GJ=[0,1,2,3]; GO=[9]

def load_age22():
    d=json.load(open(os.path.join(OUT,"edad-2022-congreso-mesa.json")))["mesas"]
    out={}
    for mk,v in d.items():
        s=v["suf"]
        if s<40: continue
        out[mk]={"fy":sum(v["bands"][BN[i]] for i in GJ)/s,"fo":sum(v["bands"][BN[i]] for i in GO)/s,"pcode":v["pcode"]}
    return out

def load_mmv():
    votes=collections.defaultdict(dict)  # mk -> {(par,can_nombre):votos}
    valid=collections.defaultdict(int)
    tot=collections.defaultdict(int)
    with open(MMV,encoding="utf-8",errors="replace") as f:
        r=csv.reader(f,delimiter=";"); hdr=next(r)
        ix={h.strip():i for i,h in enumerate(hdr)}
        for row in r:
            if str(row[ix["CORNOMBRE"]]).strip().upper()!="CAMARA": continue
            try: mun=int(row[ix["MUN"]]);zz=int(row[ix["ZONA"]]);pp=int(row[ix["PUESTO"]]);ms=int(row[ix["MESA"]])
            except (ValueError,TypeError): continue
            mk=f"{mun}-{zz:02d}-{pp:02d}-{ms:03d}"
            nom=str(row[ix["CANNOMBRE"]]).strip(); par=str(row[ix["PARNOMBRE"]]).strip()
            vot=int(row[ix["VOTOS"]] or 0)
            up=nom.upper()
            if "TOTALES" in up: continue                 # subtotal
            if "NULO" in up or "NO MARCAD" in up: continue # no válidos
            valid[mk]+=vot
            if "BLANCO" in up: continue                  # válido, no candidato
            key=(par,nom); votes[mk][key]=votes[mk].get(key,0)+vot; tot[key]+=vot
    return votes, valid, tot

def main():
    age=load_age22(); votes,valid,tot=load_mmv()
    Vt=sum(valid.values())
    # composición
    fyw=fow=w=0
    for mk,val in valid.items():
        a=age.get(mk)
        if a: fyw+=a["fy"]*val; fow+=a["fo"]*val; w+=val
    Fy=fyw/w; Fo=fow/w
    print(f"Cámara 2026 · electorado joven {Fy*100:.0f}% / 36-60 {(1-Fy-Fo)*100:.0f}% / 61+ {Fo*100:.0f}%\n")
    # candidatos objetivo: Mariana Gil + top Verde + top general
    targets=[k for k in tot if "MARIANA GIL" in k[1].upper()]
    verde=sorted([k for k in tot if "ALIANZA VERDE" in k[0].upper()], key=lambda k:-tot[k])[:3]
    topg=sorted(tot, key=lambda k:-tot[k])[:4]
    for k in verde+topg:
        if k not in targets: targets.append(k)
    print(f"{'CANDIDATO (lista)':44}{'votos':>6}  18-35 / 36-60 / 61+   IC young/old")
    for k in targets:
        mesas=[]
        for mk,cv in votes.items():
            a=age.get(mk); val=valid.get(mk,0)
            if not a or val<20: continue
            mesas.append({"share":cv.get(k,0)/val,"fy":a["fy"],"fo":a["fo"],"w":val,"pcode":a["pcode"]})
        r=fe_candidate(mesas,k)
        if not r: print(f"{(k[1][:30]+' · '+k[0][:12]):44}{tot[k]:>6}  (muestra insuf.)"); continue
        S=tot[k]/Vt; by,bo=r["b"]; r36=S-by*Fy-bo*Fo
        ry=r36+by; ro=r36+bo
        lbl=(k[1][:28]+" · "+k[0].replace("PARTIDO ","")[:12])
        print(f"{lbl[:44]:44}{tot[k]:>6}  {ry*100:>4.0f} / {r36*100:>4.0f} / {ro*100:>4.0f}   [{(r36+r['lo'][0])*100:.0f}-{(r36+r['hi'][0])*100:.0f}]/[{(r36+r['lo'][1])*100:.0f}-{(r36+r['hi'][1])*100:.0f}]")

if __name__=="__main__": main()
