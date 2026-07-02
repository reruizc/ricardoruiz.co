#!/usr/bin/env python3
"""Probe de viabilidad: ¿las llaves de puesto de Edadygenero (Risaralda)
casan con las de los datos de voto? Reporta cobertura por elección y por
municipio grande.
"""
import json, os, collections
OUT="Bases de datos/output_edad_risaralda"

def load_age(fn):
    d=json.load(open(os.path.join(OUT,fn))); return d["puestos"]

def vote_keys_terr(fn, corp):
    d=json.load(open(os.path.join("Bases de datos/output_risaralda",fn)))
    blk=d.get(corp,{}); out={}
    for mun,pp in blk.items():
        for zzpp,v in pp.items(): out[f"{mun}-{zzpp}"]=v
    return out

def vote_keys_camara(fn):
    d=json.load(open(os.path.join("Bases de datos/output_risaralda",fn)))
    out={}
    for mun,pp in d.items():
        for zzpp,v in pp.items(): out[f"{mun}-{zzpp}"]=v
    return out

def report(age, vote, label):
    ak=set(age); vk=set(vote); inter=ak&vk
    vval=sum((v.get("validos") or 0) for v in vote.values())
    mval=sum((vote[k].get("validos") or 0) for k in inter)
    print(f"\n=== {label} ===")
    print(f"  puestos edad: {len(ak)} · puestos voto: {len(vk)} · en ambos: {len(inter)}")
    print(f"  cobertura de votos casados: {mval}/{vval} = {100*mval/max(1,vval):.1f}%")
    # por municipio grande
    bymun=collections.Counter(); bymunhit=collections.Counter()
    for k in vk:
        mun=k.split("-")[0]; bymun[mun]+=1; bymunhit[mun]+= (1 if k in ak else 0)
    big=sorted(bymun, key=lambda m:-bymun[m])[:6]
    for m in big:
        print(f"    mun {m}: {bymunhit[m]}/{bymun[m]} puestos con edad")

print("2019 territorial (gobernación) vs edad 2019-local:")
report(load_age("edad-2019-local.json"), vote_keys_terr("risaralda-2019-puestos.json","gobernacion"), "2019")
print("\nCámara 2026 vs edad 2022-congreso (molde de proyección):")
report(load_age("edad-2022-congreso.json"), vote_keys_camara("risaralda-camara-2026-puestos.json"), "Cámara2026←2022")
print("\n2023 territorial (gobernación) vs edad 2019-local (molde proyección):")
report(load_age("edad-2019-local.json"), vote_keys_terr("risaralda-2023-puestos.json","gobernacion"), "2023←2019")
