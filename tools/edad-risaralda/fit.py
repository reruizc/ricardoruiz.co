#!/usr/bin/env python3
"""Inferencia ecológica bloque-por-edad para Risaralda.
Modelo: alt_share_i ≈ Σ_g f_ig · β_g, con β_g ∈ [0,1] (tasa de voto
alternativo del grupo etario g), WLS ponderada por válidos, resuelta con
lsq_linear. IC por bootstrap de puestos (B=600). Cotas duras Duncan-Davis.

3 grupos: 18-35 / 36-60 / 61+.  Uso: importado por build_edad.py.
"""
import json, os, numpy as np
from scipy.optimize import lsq_linear

BAND_NAMES=["18-20","21-25","26-30","31-35","36-40","41-45","46-50","51-55","56-60","61+"]
GROUPS={"18-35":[0,1,2,3], "36-60":[4,5,6,7,8], "61+":[9]}
GN=list(GROUPS)

def load_age(fn):
    d=json.load(open(os.path.join("Bases de datos/output_edad_risaralda",fn)))
    out={}
    for pk,v in d["puestos"].items():
        b=v["bands"]; g=[sum(b[BAND_NAMES[i]] for i in GROUPS[gn]) for gn in GN]
        out[pk]={"g":g, "suf":sum(g)}
    return out

def vote_puestos(fn, corp):
    d=json.load(open(os.path.join("Bases de datos/output_risaralda",fn)))
    blk=d.get(corp,{}) if corp else d; out={}
    for mun,pp in blk.items():
        for zzpp,v in pp.items(): out[f"{mun}-{zzpp}"]={"mun":mun, **v}
    return out

def _fit(F, y, w):
    sw=np.sqrt(w); A=F*sw[:,None]; b=y*sw
    r=lsq_linear(A,b,bounds=(0,1),max_iter=200)
    return r.x

def ei_bloc(agePuestos, votePuestos, munFilter=None, B=600, seed=12345):
    rows=[]
    for pk,av in agePuestos.items():
        vv=votePuestos.get(pk)
        if not vv: continue
        if munFilter and str(vv["mun"])!=str(munFilter): continue
        val=vv.get("validos") or 0; alt=vv.get("alt_votos") or 0; suf=av["suf"]
        if val<25 or suf<25: continue
        f=[gi/suf for gi in av["g"]]
        rows.append((f, alt/val, val, av["g"]))
    n=len(rows)
    if n<8: return None
    F=np.array([r[0] for r in rows]); y=np.array([r[1] for r in rows]); w=np.array([r[2] for r in rows],float)
    G=np.array([r[3] for r in rows],float)  # conteos por grupo
    beta=_fit(F,y,w)
    # composición etaria de los votantes (dato duro): fracción por grupo
    gtot=G.sum(axis=0); comp=gtot/gtot.sum()
    # cotas Duncan-Davis por grupo (agregado del scope)
    A=(y*w).sum(); V=w.sum()  # aprox alt totales / válidos totales
    dd=[]
    for k in range(len(GN)):
        Ng=gtot[k]
        lo=max(0.0,(A-(V-Ng))/Ng) if Ng>0 else 0; hi=min(1.0, A/Ng) if Ng>0 else 1
        dd.append((round(lo*100,1),round(hi*100,1)))
    # bootstrap por puestos
    rng=np.random.default_rng(seed); boots=np.zeros((B,len(GN)))
    for bi in range(B):
        idx=rng.integers(0,n,n)
        boots[bi]=_fit(F[idx],y[idx],w[idx])
    lo=np.percentile(boots,2.5,axis=0)*100; hi=np.percentile(boots,97.5,axis=0)*100
    out={"n_puestos":n, "alt_pct_scope":round(A/V*100,2), "grupos":{}}
    # composición del voto alternativo: de dónde salen los votos alt
    altvotes=[gtot[k]*beta[k] for k in range(len(GN))]; altsum=sum(altvotes) or 1
    for k,gn in enumerate(GN):
        out["grupos"][gn]={
            "beta":round(beta[k]*100,1),          # % de ese grupo que vota alternativo
            "lo":round(lo[k],1),"hi":round(hi[k],1),
            "dd_lo":dd[k][0],"dd_hi":dd[k][1],
            "comp_votantes":round(comp[k]*100,1), # % de votantes que son de ese grupo
            "comp_alt":round(altvotes[k]/altsum*100,1), # % del voto alt que viene de ese grupo
        }
    return out

if __name__=="__main__":
    # smoke test: 2019 gobernación
    age=load_age("edad-2019-local.json"); vote=vote_puestos("risaralda-2019-puestos.json","gobernacion")
    for label,mf in [("RISARALDA",None),("PEREIRA","1"),("DOSQUEBRADAS","25"),("SANTA ROSA","86")]:
        r=ei_bloc(age,vote,mf)
        if not r: print(label,"— muestra insuficiente"); continue
        print(f"\n{label}  (n={r['n_puestos']} puestos · alt scope {r['alt_pct_scope']}%)")
        for gn,g in r["grupos"].items():
            print(f"  {gn:6}  alt {g['beta']:5.1f}%  [IC {g['lo']:.1f}–{g['hi']:.1f} · DD {g['dd_lo']:.0f}–{g['dd_hi']:.0f}]  · {g['comp_votantes']:.0f}% de votantes")
