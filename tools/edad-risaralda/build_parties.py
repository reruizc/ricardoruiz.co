#!/usr/bin/env python3
"""Perfil por edad de las LISTAS grandes de Cámara 2026 (EI bloque por partido)
y de los candidatos a Gobernación (territorial, resolubles por puesto).
Fusiona en edad-resultados.json bajo elecciones.camara.partidos y
elecciones.{2019,2023}.candidatos.
"""
import sys, json, os, urllib.request
sys.path.insert(0,"/Users/ricardoruiz/ricardoruiz.co/tools/edad-risaralda")
sys.path.insert(0,"/Users/ricardoruiz/ricardoruiz.co/tools/edad-1v-2026")
import numpy as np
from fit import load_age, ei_bloc, GN, GROUPS
from probe_viabilidad import load_dane
OUT="Bases de datos/output_edad_risaralda"
SCOPES=[("RISARALDA",None),("Pereira","1"),("Dosquebradas","25"),("Santa Rosa de Cabal","86")]
# listas grandes de Cámara (>13% ~ señal de edad interpretable)
BIG_CAM=["PACTO POR RISARALDA","PARTIDO ALIANZA VERDE","PARTIDO LIBERAL COLOMBIANO",
         "PARTIDO DE LA U - CAMBIO RADICAL","CENTRO DEMOCRATICO- MIRA"]

def proj(age, fac):
    o={}
    for pk,v in age.items(): o[pk]={"g":[v["g"][i]*fac[GN[i]] for i in range(3)]}; o[pk]["suf"]=sum(o[pk]["g"])
    return o

def fac(a,b):
    dane=load_dane(years=(a,b)); k=[x for x in dane if "RISARALD" in x][0]
    pa=np.array(dane[k][a]); pb=np.array(dane[k][b])
    return {g:(sum(pb[i] for i in GROUPS[g])/sum(pa[i] for i in GROUPS[g])) for g in GN}

def pad2(x): return f"{int(x):02d}"
def cam_puestos():
    url="https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/camara/dep-24.json"
    d=json.load(urllib.request.urlopen(url))
    P={}
    for m in d["municipios"]:
        mun=str(int(m["cod"]))
        for c in m.get("comunas",[]):
            for pu in c.get("puestos",[]):
                zz=pad2(pu["zon_cod"]); pp=pad2(pu.get("pue_cod_raw") or pu["pue_cod"].split("-")[-1])
                P[f"{mun}-{zz}-{pp}"]={"mun":mun,"validos":pu.get("votval") or 0,"parties":pu.get("partidos",{})}
    return P

def run_party(agePuestos, camP, party):
    res={}
    for nombre,mf in SCOPES:
        vp={pk:{"mun":v["mun"],"validos":v["validos"],"alt_votos":v["parties"].get(party,0)} for pk,v in camP.items()}
        r=ei_bloc(agePuestos, vp, mf, B=400)
        if r: r["nombre"]=nombre; res[mf or "DEP"]=r
    return res

def main():
    res=json.load(open(os.path.join(OUT,"edad-resultados.json")))
    age22=proj(load_age("edad-2022-congreso.json"), fac(2022,2026))
    camP=cam_puestos()
    parties={}
    for pty in BIG_CAM:
        parties[pty]={"scopes":run_party(age22,camP,pty)}
        dep=parties[pty]["scopes"].get("DEP")
        if dep: print(f"{pty[:30]:30} 18-35 {dep['grupos']['18-35']['beta']:.1f}% [{dep['grupos']['18-35']['lo']:.0f}-{dep['grupos']['18-35']['hi']:.0f}] · 61+ {dep['grupos']['61+']['beta']:.1f}%")
    res["elecciones"]["camara"]["partidos"]=parties
    json.dump(res, open(os.path.join(OUT,"edad-resultados.json"),"w"))
    print("guardado.")

if __name__=="__main__": main()
