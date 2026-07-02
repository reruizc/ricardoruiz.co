#!/usr/bin/env python3
"""¿Existe el sorting etario por mesa (orden de cédula) dentro del puesto?
Si sí, la regresión con efectos fijos de puesto tiene señal para estimar
edad por candidato. Mide: (a) variación intra-puesto del %61+ entre mesas,
(b) correlación número-de-mesa ↔ %61+ dentro del puesto."""
import json, os, collections, numpy as np
OUT="Bases de datos/output_edad_risaralda"
d=json.load(open(os.path.join(OUT,"edad-2019-local-mesa.json")))
BN=d["bandas"]; mesas=d["mesas"]
by=collections.defaultdict(list)
for mk,v in mesas.items():
    suf=v["suf"];
    if suf<40: continue
    p61=v["bands"]["61+"]/suf*100
    p1835=sum(v["bands"][b] for b in ["18-20","21-25","26-30","31-35"])/suf*100
    by[v["pcode"]].append((v["mesa"], p61, p1835, suf))
# puestos con >=6 mesas
ranges=[]; corrs=[]; nbig=0
for pc,rows in by.items():
    if len(rows)<6: continue
    nbig+=1
    rows.sort()
    ms=np.array([r[0] for r in rows]); p61=np.array([r[1] for r in rows]); p18=np.array([r[2] for r in rows])
    ranges.append(p61.max()-p61.min())
    if ms.std()>0 and p61.std()>0: corrs.append(np.corrcoef(ms,p61)[0,1])
ranges=np.array(ranges); corrs=np.array(corrs)
print(f"puestos con >=6 mesas: {nbig}")
print(f"rango intra-puesto de %61+ entre mesas: mediana {np.median(ranges):.1f} pp · p25 {np.percentile(ranges,25):.1f} · p75 {np.percentile(ranges,75):.1f} · max {ranges.max():.1f}")
print(f"correlación (nº mesa ↔ %61+) dentro del puesto: media {corrs.mean():.2f} · mediana {np.median(corrs):.2f} · % negativas {100*(corrs<0).mean():.0f}%")
# ejemplo puesto grande
big=max(by, key=lambda p:len(by[p]))
rows=sorted(by[big]); print(f"\nEjemplo puesto {big} ({len(rows)} mesas): %61+ por mesa:")
print("  mesa:  "+" ".join(f"{r[0]:>3}" for r in rows[:14]))
print("  %61+:  "+" ".join(f"{r[1]:>3.0f}" for r in rows[:14]))
print("  %jov:  "+" ".join(f"{r[2]:>3.0f}" for r in rows[:14]))
