#!/usr/bin/env python3
"""Demo de inferencia ecológica (Goodman ponderado, NNLS) para validar
viabilidad del modelo edad x candidato. NO es el estimador final (ese será
simplex-constrained / bayesiano con bounds de Duncan-Davis); es la prueba
de que la señal existe y apunta en la dirección documentada.

2022: usa composición etaria OBSERVADA por puesto (Edadygenero P1V-2022).
2026: usa composición PROYECTADA = shape 2022 x factores DANE 22->26
      por depto, renormalizada (sin raking fino aún).
"""
import os
import numpy as np
import pandas as pd
from scipy.optimize import nnls

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "..", "Bases de datos", "output_edad_1v")

BANDS = ["18 a 20 años", "21 a 25 años", "26 a 30 años", "31 a 35 años",
         "36 a 40 años", "41 a 45 años", "46 a 50 años", "51 a 55 años",
         "56 a 60 años", "Mayor a 60 años"]
# colapso a 5 grupos para estabilidad
GROUPS = {"18-25": [0, 1], "26-35": [2, 3], "36-45": [4, 5],
          "46-60": [6, 7, 8], "61+": [9]}
GNAMES = list(GROUPS)

# factores DANE nacionales 22->26 por banda original (de probe C2)
G2226 = np.array([0.994, 1.001, 1.034, 1.102, 1.063,
                  1.075, 1.095, 1.010, 1.042, 1.135])


def load():
    e22 = pd.read_csv(os.path.join(OUT, "edad-2022-puesto.csv"), dtype={"pcode": str})
    v22 = pd.read_csv(os.path.join(OUT, "votos-2022-puesto.csv"), dtype={"pcode": str})
    v26 = pd.read_csv(os.path.join(OUT, "votos-2026-puesto.csv"), dtype={"pcode": str})
    return e22, v22, v26


def collapse(mat):
    return np.stack([mat[:, idx].sum(axis=1) for idx in GROUPS.values()], axis=1)


def goodman(W, Y, weights):
    """NNLS ponderado por candidato. W: n x A shares; Y: n x C shares."""
    sw = np.sqrt(weights)
    Xw = W * sw[:, None]
    B = []
    for c in range(Y.shape[1]):
        beta, _ = nnls(Xw, Y[:, c] * sw)
        B.append(beta)
    return np.array(B)   # C x A


def report(B, cands, W_nat, y_nat, label):
    print(f"\n=== {label} ===")
    # normaliza columnas (cada grupo etario reparte 100% entre candidatos)
    coln = B / B.sum(axis=0, keepdims=True)
    print("Distribución estimada del voto DENTRO de cada grupo etario (cols=100%):")
    print("           " + "  ".join(f"{g:>7s}" for g in GNAMES))
    for i, c in enumerate(cands):
        print(f"  {c:9s}" + "  ".join(f"{coln[i, a]*100:7.1f}" for a in range(len(GNAMES))))
    # chequeo de consistencia: nacional implícito vs real
    impl = B @ W_nat
    impl = impl / impl.sum()
    print("Consistencia nacional (implícito vs observado, % de válidos):")
    for i, c in enumerate(cands):
        print(f"  {c:9s} {impl[i]*100:6.1f} vs {y_nat[i]*100:6.1f}")


def main():
    e22, v22, v26 = load()

    # ---------- 2022: composición observada ----------
    m = e22.merge(v22, on="pcode")
    m["cov"] = m["Cantidad de Sufragantes"] / m["total_votos"].clip(lower=1)
    m = m[(m["cov"].between(0.70, 1.10)) & (m["total_validos"] >= 200)].copy()
    print(f"2022: {len(m):,} puestos en la muestra EI "
          f"({m['total_validos'].sum():,} votos válidos)")

    Wm = collapse(m[BANDS].values.astype(float))
    Wm = Wm / Wm.sum(axis=1, keepdims=True)
    cands22 = ["petro", "fico", "rodolfo", "fajardo", "blanco"]
    Ym = m[cands22].values.astype(float)
    otros = m["total_validos"].values - Ym.sum(axis=1)
    Ym = np.column_stack([Ym, otros]) / m["total_validos"].values[:, None]
    cands22 += ["otros"]
    wts = m["total_validos"].values.astype(float)
    B22 = goodman(Wm, Ym, wts)
    W_nat = (Wm * wts[:, None]).sum(axis=0) / wts.sum()
    y_nat = (Ym * wts[:, None]).sum(axis=0) / wts.sum()
    report(B22, cands22, W_nat, y_nat,
           "1V-2022 (composición etaria observada)")

    # ---------- 2026: composición proyectada ----------
    e26 = e22.copy()
    shp = e26[BANDS].values.astype(float)
    shp = shp * G2226[None, :]                       # ajuste demográfico
    e26[BANDS] = shp
    m6 = e26.merge(v26, on="pcode")
    # gate de calidad heredado del 2022 (mismos puestos limpios)
    ok22 = set(m["pcode"])
    m6 = m6[(m6["pcode"].isin(ok22)) & (m6["total_validos"] >= 200)].copy()
    print(f"\n2026: {len(m6):,} puestos con perfil proyectado "
          f"({m6['total_validos'].sum():,} votos válidos · "
          f"{m6['total_validos'].sum()/v26['total_validos'].sum()*100:.0f}% del total)")
    W6 = collapse(m6[BANDS].values.astype(float))
    W6 = W6 / W6.sum(axis=1, keepdims=True)
    cands26 = ["cepeda", "abelardo", "paloma", "fajardo26", "blanco"]
    Y6 = m6[cands26].values.astype(float)
    otros6 = m6["total_validos"].values - Y6.sum(axis=1)
    Y6 = np.column_stack([Y6, otros6]) / m6["total_validos"].values[:, None]
    cands26 += ["otros"]
    w6 = m6["total_validos"].values.astype(float)
    B26 = goodman(W6, Y6, w6)
    W6n = (W6 * w6[:, None]).sum(axis=0) / w6.sum()
    y6n = (Y6 * w6[:, None]).sum(axis=0) / w6.sum()
    report(B26, cands26, W6n, y6n,
           "1V-2026 (composición etaria PROYECTADA — preliminar)")


if __name__ == "__main__":
    main()
