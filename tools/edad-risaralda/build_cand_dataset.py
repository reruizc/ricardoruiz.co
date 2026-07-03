#!/usr/bin/env python3
"""Genera candidatos-edad.json: perfil por edad de cada candidato (mesa-FE)
a nivel Risaralda + Pereira/Dosquebradas/Santa Rosa, con etiqueta de muestra
insuficiente donde no alcance. Cámara 2026 (MMV) + Gobernación 2019/2023 (GCS).
"""
import sys, os, json, csv, collections
import numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from build_cand_mesa import fe_candidate
OUT="Bases de datos/output_edad_risaralda"
BN=["18-20","21-25","26-30","31-35","36-40","41-45","46-50","51-55","56-60","61+"]
GJ=[0,1,2,3]; GO=[9]
SCOPES=[("DEP",None),("1",1),("25",25),("86",86)]
MIN_TOT=400

def load_age_mesa(fn):
    d=json.load(open(os.path.join(OUT,fn)))["mesas"]; out={}
    for mk,v in d.items():
        s=v["suf"]
        if s<40: continue
        out[mk]={"fy":sum(v["bands"][BN[i]] for i in GJ)/s,"fo":sum(v["bands"][BN[i]] for i in GO)/s,"pcode":v["pcode"]}
    return out

def load_gcs(path, corr):
    votes=collections.defaultdict(dict); valid=collections.defaultdict(int); tot=collections.defaultdict(int); names={}
    with open(path,encoding="utf-8",errors="replace") as f:
        r=csv.reader((l.replace('﻿','') for l in f),delimiter=';'); hdr=next(r)
        ix={h.strip():i for i,h in enumerate(hdr)}
        for row in r:
            if row[ix["COD_DDE"]].strip()!="24": continue
            if str(row[ix["DES_COR"]]).strip().upper()!=corr: continue
            try: mun=int(row[ix["COD_MME"]]);zz=int(row[ix["COD_ZZ"]]);pp=int(row[ix["COD_PP"]]);ms=int(row[ix["DES_MS"]])
            except (ValueError,TypeError): continue
            mk=f"{mun}-{zz:02d}-{pp:02d}-{ms:03d}"; cod=row[ix["COD_CAN"]].strip(); vot=int(row[ix["NUM_VOT"]] or 0)
            if cod in ("997","998","999"): continue
            valid[mk]+=vot
            if cod=="996": continue
            key=cod; votes[mk][key]=votes[mk].get(key,0)+vot; tot[key]+=vot; names[key]=row[ix["DES_CAN"]].strip()
    return votes,valid,tot,names,None

def load_mmv_camara():
    MMV="Bases de datos/DEPTOS_DECLARADOS/MMV_XXX_24_000_XXX_XX_XX_XXX_1014.csv"
    votes=collections.defaultdict(dict); valid=collections.defaultdict(int); tot=collections.defaultdict(int); names={}; party={}
    with open(MMV,encoding="utf-8",errors="replace") as f:
        r=csv.reader(f,delimiter=";"); hdr=next(r); ix={h.strip():i for i,h in enumerate(hdr)}
        for row in r:
            if str(row[ix["CORNOMBRE"]]).strip().upper()!="CAMARA": continue
            try: mun=int(row[ix["MUN"]]);zz=int(row[ix["ZONA"]]);pp=int(row[ix["PUESTO"]]);ms=int(row[ix["MESA"]])
            except (ValueError,TypeError): continue
            mk=f"{mun}-{zz:02d}-{pp:02d}-{ms:03d}"; nom=str(row[ix["CANNOMBRE"]]).strip(); par=str(row[ix["PARNOMBRE"]]).strip()
            up=nom.upper(); vot=int(row[ix["VOTOS"]] or 0)
            if "TOTALES" in up: continue
            if "NULO" in up or "NO MARCAD" in up: continue
            valid[mk]+=vot
            if "BLANCO" in up: continue
            key=par+"|"+nom; votes[mk][key]=votes[mk].get(key,0)+vot; tot[key]+=vot; names[key]=nom; party[key]=par
    return votes,valid,tot,names,party

def profile(mesas, S, Fy, Fo):
    r=fe_candidate(mesas, None)
    if not r or r.get("insuf"): return {"insuf":True, "n":(r or {}).get("n",len(mesas)), "npuestos":(r or {}).get("npuestos",0)}
    by,bo=r["b"]; r36=S-by*Fy-bo*Fo
    def cl(x): return round(max(0,min(100,x*100)),1)
    return {"grupos":{
        "18-35":{"beta":cl(r36+by),"lo":cl(r36+r["lo"][0]),"hi":cl(r36+r["hi"][0])},
        "36-60":{"beta":cl(r36)},
        "61+":{"beta":cl(r36+bo),"lo":cl(r36+r["lo"][1]),"hi":cl(r36+r["hi"][1])}},
        "n":r["n"],"npuestos":r["npuestos"]}

def run_election(votes, valid, tot, names, party, age):
    Vt=sum(valid.values()); out={}
    cands=[k for k in tot if tot[k]>=MIN_TOT]
    for k in cands:
        entry={"nombre":names[k],"partido":(party[k] if party else None),"votos":tot[k],"scopes":{}}
        for skey,mun in SCOPES:
            mesas=[]; vv=0; av=0; w=0
            for mk,cv in votes.items():
                a=age.get(mk); val=valid.get(mk,0)
                if not a or val<20: continue
                if mun is not None and int(a["pcode"].split("-")[0])!=mun: continue
                sh=cv.get(k,0)/val
                mesas.append({"share":sh,"fy":a["fy"],"fo":a["fo"],"w":val,"pcode":a["pcode"]})
                vv+=cv.get(k,0); av+=(a["fy"]*val+0); # placeholders
            if len(mesas)<40: entry["scopes"][skey]={"insuf":True,"n":len(mesas)}; continue
            wsum=sum(m["w"] for m in mesas); S=sum(m["share"]*m["w"] for m in mesas)/wsum
            Fy=sum(m["fy"]*m["w"] for m in mesas)/wsum; Fo=sum(m["fo"]*m["w"] for m in mesas)/wsum
            entry["scopes"][skey]=profile(mesas,S,Fy,Fo)
        out[k]=entry
    return out

def main():
    age19=load_age_mesa("edad-2019-local-mesa.json"); age22=load_age_mesa("edad-2022-congreso-mesa.json")
    res={"grupos":["18-35","36-60","61+"],"metodo":"efectos fijos de puesto (mesa) · sorting de cédula · IC bootstrap por puesto","elecciones":{}}
    print("Cámara 2026…")
    v,va,t,n,p=load_mmv_camara(); res["elecciones"]["camara"]=run_election(v,va,t,n,p,age22)
    print(f"  {len(res['elecciones']['camara'])} candidatos")
    print("Gobernación 2019…")
    v,va,t,n,p=load_gcs("Bases de datos/FINAL SUBIDA GCS/GCS_2019TER.csv","GOBERNADOR"); res["elecciones"]["gob2019"]=run_election(v,va,t,n,p,age19)
    print(f"  {len(res['elecciones']['gob2019'])} candidatos")
    print("Gobernación 2023…")
    v,va,t,n,p=load_gcs("Bases de datos/FINAL SUBIDA GCS/GCS_2023TER.csv","GOBERNADOR"); res["elecciones"]["gob2023"]=run_election(v,va,t,n,p,age19)
    print(f"  {len(res['elecciones']['gob2023'])} candidatos")
    json.dump(res, open(os.path.join(OUT,"candidatos-edad.json"),"w"))
    sz=os.path.getsize(os.path.join(OUT,"candidatos-edad.json"))/1024
    print(f"candidatos-edad.json ({sz:.0f} KB)")
    # muestra Mariana Gil
    for k,e in res["elecciones"]["camara"].items():
        if "MARIANA GIL" in k.upper():
            d=e["scopes"]["DEP"]; print("Mariana Gil DEP:", d.get("grupos") or d)

if __name__=="__main__": main()
