#!/usr/bin/env python3
"""Niveles absolutos de voto de IZQUIERDA (Petro 2022) por sexo x edad (3 bandas),
con efectos fijos de puesto. Permite dibujar dos líneas (mujeres / hombres) que
se cruzan por edad -> slide 06 clara.

6 celdas (M·18-35, M·36-60, M·61+, H·18-35, H·36-60, H·61+). Regresión
within-puesto ponderada por votos; se recupera el nivel absoluto sumando la
media nacional al efecto de cada celda.
Salida: output_mujeres_1v/genero-edad-niveles.json
"""
import json
import os

import numpy as np
import pandas as pd

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "..", "Bases de datos", "output_mujeres_1v")

m = pd.read_csv(os.path.join(OUT, "mesa-2022-genero-votos.csv"),
                dtype={"mkey": str, "puesto": str})
m = m[(m["tot"] >= 50) & (m["total"] >= 50)].copy()
t = m["tot"].values.astype(float)
# 6 shares (base = H 18-35)
cells = {"M·18-35": m["Mage0"] / t, "M·36-60": m["Mage1"] / t, "M·61+": m["Mage2"] / t,
         "H·36-60": m["Hage1"] / t, "H·61+": m["Hage2"] / t}        # base Hj omitida
Hj = m["Hage0"].values / t
order = list(cells)
X = np.column_stack([cells[k].values for k in order])
w = m["total"].values.astype(float)
pcode = m["puesto"].values


def demean(v):
    df = pd.DataFrame({"p": pcode, "v": v, "w": w})
    wm = df.groupby("p").apply(lambda d: np.average(d["v"], weights=d["w"]),
                               include_groups=False)
    return v - df["p"].map(wm).values


Xd = np.column_stack([demean(X[:, j]) for j in range(X.shape[1])])
sw = np.sqrt(w)
Xw = Xd * sw[:, None]
inv = np.linalg.pinv(Xw.T @ Xw)
y = (m["petro"].values / m["total"].values)
beta = inv @ (Xw.T @ (demean(y) * sw))                 # coefs vs base Hj

# pesos de votantes por celda (vote-weighted share promedio)
allcells = order + ["H·18-35"]
shares_all = np.column_stack([X[:, j] for j in range(X.shape[1])] + [Hj])
wbar = (shares_all * w[:, None]).sum(0) / w.sum()       # peso de cada celda
beta_all = np.append(beta, 0.0)                         # base = 0
nat = (y * w).sum() / w.sum()                           # Petro nacional en muestra
alpha = nat - (wbar * beta_all).sum()                   # intercepto medio
level = alpha + beta_all                                # nivel absoluto por celda
lv = dict(zip(allcells, level * 100))

AGE = ["18-35", "36-60", "61+"]
res = {"izq_niveles": {
    "Mujeres": {a: round(lv[f"M·{a}"], 1) for a in AGE},
    "Hombres": {a: round(lv[f"H·{a}"], 1) for a in AGE}},
    "nacional_izq": round(nat * 100, 1)}
print("Voto de IZQUIERDA (Petro 2022) por sexo x edad · niveles (%):")
print("         18-35  36-60   61+")
for s in ("Mujeres", "Hombres"):
    print(f"  {s:8s}", "  ".join(f"{res['izq_niveles'][s][a]:5.1f}" for a in AGE))
for a in AGE:
    g = res["izq_niveles"]["Mujeres"][a] - res["izq_niveles"]["Hombres"][a]
    print(f"  brecha {a}: {g:+.1f} pp")
json.dump(res, open(os.path.join(OUT, "genero-edad-niveles.json"), "w"),
          ensure_ascii=False, indent=1)
print("-> genero-edad-niveles.json")
