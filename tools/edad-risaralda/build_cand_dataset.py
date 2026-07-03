#!/usr/bin/env python3
"""candidatos-edad.json: perfil por edad por candidato (mesa-FE), etiqueta de
muestra insuficiente donde no alcance.
  Dept-wide  : Cámara 2026 (MMV) · Gobernación 2019/2023 · Asamblea 2019/2023
  Municipal  : Alcaldía 2019/2023 · Concejo 2019/2023  (perfil dentro del mun)
"""
import sys, os, json, csv, collections
import numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from build_cand_mesa import fe_candidate
OUT="Bases de datos/output_edad_risaralda"
BN=["18-20","21-25","26-30","31-35","36-40","41-45","46-50","51-55","56-60","61+"]
GJ=[0,1,2,3]; GO=[9]
BIGMUN=["1","25","86"]; DEPT_SCOPES=[("DEP",None),("1",1),("25",25),("86",86)]
MIN_TOT=400

def load_age_mesa(fn):
    d=json.load(open(os.path.join(OUT,fn)))["mesas"]; out={}
    for mk,v in d.items():
        s=v["suf"]
        if s<40: continue
        out[mk]={"fy":sum(v["bands"][BN[i]] for i in GJ)/s,"fo":sum(v["bands"][BN[i]] for i in GO)/s,"pcode":v["pcode"]}
    return out

def load_gcs(path, corr, municipal, byparty):
    votes=collections.defaultdict(dict); valid=collections.defaultdict(int)
    tot=collections.defaultdict(int); meta={}
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
            par=row[ix["COD_PAR"]].strip() if "COD_PAR" in ix else ""
            parts=([str(mun)] if municipal else [])+([par] if byparty else [])+[cod]
            key="|".join(parts)
            votes[mk][key]=votes[mk].get(key,0)+vot; tot[key]+=vot
            meta[key]={"nombre":row[ix["DES_CAN"]].strip(),"partido":row[ix["DES_PAR"]].strip() if byparty else None,"mun":str(mun) if municipal else None}
    return votes,valid,tot,meta

def load_mmv_camara():
    MMV="Bases de datos/DEPTOS_DECLARADOS/MMV_XXX_24_000_XXX_XX_XX_XXX_1014.csv"
    votes=collections.defaultdict(dict); valid=collections.defaultdict(int); tot=collections.defaultdict(int); meta={}
    with open(MMV,encoding="utf-8",errors="replace") as f:
        r=csv.reader(f,delimiter=";"); hdr=next(r); ix={h.strip():i for i,h in enumerate(hdr)}
        for row in r:
            if str(row[ix["CORNOMBRE"]]).strip().upper()!="CAMARA": continue
            try: mun=int(row[ix["MUN"]]);zz=int(row[ix["ZONA"]]);pp=int(row[ix["PUESTO"]]);ms=int(row[ix["MESA"]])
            except (ValueError,TypeError): continue
            mk=f"{mun}-{zz:02d}-{pp:02d}-{ms:03d}"; nom=str(row[ix["CANNOMBRE"]]).strip(); par=str(row[ix["PARNOMBRE"]]).strip()
            up=nom.upper(); vot=int(row[ix["VOTOS"]] or 0)
            if "TOTALES" in up or "NULO" in up or "NO MARCAD" in up: continue
            valid[mk]+=vot
            if "BLANCO" in up: continue
            key=par+"|"+nom; votes[mk][key]=votes[mk].get(key,0)+vot; tot[key]+=vot; meta[key]={"nombre":nom,"partido":par,"mun":None}
    return votes,valid,tot,meta

def profile(mesas):
    if len(mesas)<40: return {"insuf":True,"n":len(mesas)}
    wsum=sum(m["w"] for m in mesas); S=sum(m["share"]*m["w"] for m in mesas)/wsum
    Fy=sum(m["fy"]*m["w"] for m in mesas)/wsum; Fo=sum(m["fo"]*m["w"] for m in mesas)/wsum
    r=fe_candidate(mesas,None)
    if not r or r.get("insuf"): return {"insuf":True,"n":(r or {}).get("n",len(mesas)),"npuestos":(r or {}).get("npuestos",0)}
    by,bo=r["b"]; r36=S-by*Fy-bo*Fo
    cl=lambda x: round(max(0,min(100,x*100)),1)
    return {"grupos":{"18-35":{"beta":cl(r36+by),"lo":cl(r36+r["lo"][0]),"hi":cl(r36+r["hi"][0])},
        "36-60":{"beta":cl(r36)},"61+":{"beta":cl(r36+bo),"lo":cl(r36+r["lo"][1]),"hi":cl(r36+r["hi"][1])}},
        "n":r["n"],"npuestos":r["npuestos"]}

def mesas_for(k, votes, valid, age, mun=None):
    out=[]
    for mk,cv in votes.items():
        a=age.get(mk); val=valid.get(mk,0)
        if not a or val<20: continue
        if mun is not None and int(a["pcode"].split("-")[0])!=int(mun): continue
        out.append({"share":cv.get(k,0)/val,"fy":a["fy"],"fo":a["fo"],"w":val,"pcode":a["pcode"]})
    return out

def run(votes,valid,tot,meta,age,municipal):
    res={}
    for k in [k for k in tot if tot[k]>=MIN_TOT]:
        e={"nombre":meta[k]["nombre"],"partido":meta[k]["partido"],"votos":tot[k],"mun":meta[k]["mun"],"scopes":{}}
        if municipal:
            mun=meta[k]["mun"]; e["scopes"][mun]=profile(mesas_for(k,votes,valid,age,mun))
        else:
            for skey,mun in DEPT_SCOPES: e["scopes"][skey]=profile(mesas_for(k,votes,valid,age,mun))
        res[k]=e
    return res

def main():
    a19=load_age_mesa("edad-2019-local-mesa.json"); a22=load_age_mesa("edad-2022-congreso-mesa.json")
    G19="Bases de datos/FINAL SUBIDA GCS/GCS_2019TER.csv"; G23="Bases de datos/FINAL SUBIDA GCS/GCS_2023TER.csv"
    res={"grupos":["18-35","36-60","61+"],"elecciones":{}}
    JOBS=[
        ("camara", "mmv", None, None, a22, False),
        ("gob2019","GOBERNADOR",False,False,a19,False), ("gob2023","GOBERNADOR",False,False,a19,False),
        ("asa2019","ASAMBLEA", False,True, a19,False),  ("asa2023","ASAMBLEA", False,True, a19,False),
        ("alc2019","ALCALDE",  True, True, a19,True),    ("alc2023","ALCALDE",  True, True, a19,True),
        ("con2019","CONCEJO",  True, True, a19,True),    ("con2023","CONCEJO",  True, True, a19,True),
    ]
    for key,corr,municipal,byparty,age,muni in JOBS:
        if key=="camara": v,va,t,m=load_mmv_camara()
        else: v,va,t,m=load_gcs(G19 if key.endswith("2019") else G23, corr, municipal, byparty)
        res["elecciones"][key]=run(v,va,t,m,age,muni)
        print(f"{key}: {len(res['elecciones'][key])} candidatos", flush=True)
    json.dump(res, open(os.path.join(OUT,"candidatos-edad.json"),"w"))
    print(f"candidatos-edad.json ({os.path.getsize(os.path.join(OUT,'candidatos-edad.json'))/1024:.0f} KB)")

if __name__=="__main__": main()
