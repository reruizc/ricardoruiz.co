#!/usr/bin/env python3
"""EI por edad a nivel GEOGRÁFICO (ciudad y departamento) · 1V-2026.

Reusa el estimador QP-símplex de fit_ei.py sobre subconjuntos de puestos.
Composición etaria 2026 = proyección w26 (build_w26). Bootstrap por puesto.

Salidas en Bases de datos/output_edad_1v/:
  ei-ciudades.csv   year,unit,cand,grupo,beta,lo,hi   (6 ciudades + Nacional)
  ei-deptos.csv     dep,dep_name,cand,grupo,beta,lo,hi (33 deptos, para mapas)
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fit_ei import load_year, fit_qp, fit_national  # noqa: E402
from build_blocs_depto import DEP  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "Bases de datos", "output_edad_1v")

# 3 bandas (estables a nivel ciudad/depto): colapsa las 5 de fit_ei
# [18-25,26-35] -> Jóvenes 18-35 · [36-45,46-60] -> Adultos 36-60 · [61+] -> Mayores
COLLAPSE3 = [[0, 1], [2, 3], [4]]
GNAMES = ["18-35", "36-60", "61+"]


def to3(W5):
    return np.stack([W5[:, idx].sum(axis=1) for idx in COLLAPSE3], axis=1)

CANDS26 = ["cepeda", "abelardo", "paloma", "fajardo26", "blanco", "resto"]
LABEL = {"cepeda": "Cepeda", "abelardo": "Abelardo", "paloma": "Paloma",
         "fajardo26": "Fajardo", "blanco": "Blanco", "resto": "Resto"}

# 6 ciudades principales: (nombre, dep, mun) con códigos RNEC correctos
CIUDADES = [
    ("Bogotá", "16", "001"), ("Medellín", "01", "001"),
    ("Cali", "31", "001"), ("Barranquilla", "03", "001"),
    ("Cartagena", "05", "001"), ("Bucaramanga", "27", "001"),
]
RNG = np.random.default_rng(20260610)

# Fracción de pooling parcial hacia el prior nacional (peso del prior = SHRINK
# x el peso de los datos locales). Corrige el sesgo de frontera de la EI a N
# moderado (p.ej. Cepeda acorralado a 0% en 61+) sin imponer el patrón nacional.
SHRINK = 0.02
from fit_ei import proj_simplex_cols  # noqa: E402


def fit_qp_reg(W, Y, T, B0, lam, iters=3000, tol=1e-10):
    """min Σ_p T_p ||y_p - B w_p||² + lam·||B-B0||²  · columnas en el símplex."""
    G = (W * T[:, None]).T @ W
    H = (Y * T[:, None]).T @ W
    L = 2 * (np.linalg.eigvalsh(G).max() + lam)
    eta = 1.0 / L
    B = B0.copy()
    for _ in range(iters):
        grad = 2 * (B @ G - H) + 2 * lam * (B - B0)
        Bn = proj_simplex_cols(B - eta * grad)
        if np.abs(Bn - B).max() < tol:
            B = Bn
            break
        B = Bn
    return B


def fit_unit(W, Y, T, B0, n_boot=200):
    lam = SHRINK * T.sum()
    Bn = fit_qp_reg(W, Y, T, B0, lam)
    n = len(T)
    boots = []
    for _ in range(n_boot):
        idx = RNG.integers(0, n, n)
        Tb = T[idx]
        boots.append(fit_qp_reg(W[idx], Y[idx], Tb, B0, SHRINK * Tb.sum(), iters=1200))
    boots = np.stack(boots)
    lo = np.percentile(boots, 2.5, axis=0)
    hi = np.percentile(boots, 97.5, axis=0)
    impl = Bn @ ((W * T[:, None]).sum(axis=0) / T.sum())
    obs = (Y * T[:, None]).sum(axis=0) / T.sum()
    return Bn, lo, hi, impl, obs




def main():
    meta, W5, Y6, T = load_year(2026)
    meta = meta.reset_index(drop=True)
    meta["dep"] = meta["pcode"].str[:2]
    W = to3(W5)                       # 3 bandas estables

    # ===== cara a cara Cepeda vs Abelardo (EI binaria, robusta) =====
    cep, abe = Y6[:, 0], Y6[:, 1]
    tot2 = np.maximum(cep + abe, 1e-9)
    Y2 = np.column_stack([cep / tot2, abe / tot2])   # share entre los dos punteros
    T2 = tot2 * T                                     # peso = votos de los dos punteros
    B0, _, _ = fit_national(meta, W, Y2, T2)          # prior nacional por estratos
    print(f"prior nac H2H Cepeda por banda: " +
          " · ".join(f"{g} {B0[0,a]*100:.0f}%" for a, g in enumerate(GNAMES)))

    def fit_h2h(mask, nb):
        Bn, lo, hi, impl, obs = fit_unit(W[mask], Y2[mask], T2[mask], B0, n_boot=nb)
        return Bn, lo, hi, abs(impl[0] - obs[0]) * 100   # Bn fila0=Cepeda share

    # ---------------- ciudades + nacional (head-to-head) ----------------
    rows = []
    print("\nCIUDADES (Cepeda % entre los dos punteros, por banda · err consist):")
    Bn, lo, hi, err = fit_h2h(np.ones(len(T), bool), 200)
    for a, g in enumerate(GNAMES):
        rows.append(dict(unit="Nacional", grupo=g, cepeda=Bn[0, a], abelardo=Bn[1, a],
                         cep_lo=lo[0, a], cep_hi=hi[0, a]))
    print("  Nacional      " + " · ".join(f"{g} {Bn[0,a]*100:.0f}" for a, g in enumerate(GNAMES)))
    for name, dep, mun in CIUDADES:
        mask = (meta["mun"] == f"{dep}-{mun}").values
        Bn, lo, hi, err = fit_h2h(mask, 200)
        for a, g in enumerate(GNAMES):
            rows.append(dict(unit=name, grupo=g, cepeda=Bn[0, a], abelardo=Bn[1, a],
                             cep_lo=lo[0, a], cep_hi=hi[0, a]))
        print(f"  {name:13} " + " · ".join(f"{g} {Bn[0,a]*100:.0f}" for a, g in enumerate(GNAMES))
              + f"   (consist {err:.1f})")
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "ei-ciudades.csv"), index=False)

    # ---------------- departamentos (head-to-head, para mapas) ----------------
    drows = []
    print("\nDEPARTAMENTOS (Cepeda % entre los dos punteros · jóvenes / mayores):")
    for dep, (name, geo) in DEP.items():
        mask = (meta["dep"] == dep).values
        npu = mask.sum()
        if npu < 20:
            drows.append(dict(dep=dep, dep_name=name, geoname=geo, npuestos=npu, robust=0))
            continue
        nb = 120 if npu < 100 else 200
        Bn, lo, hi, err = fit_h2h(mask, nb)
        for a, g in enumerate(GNAMES):
            drows.append(dict(dep=dep, dep_name=name, geoname=geo, npuestos=npu, robust=1,
                              grupo=g, cepeda=Bn[0, a], abelardo=Bn[1, a],
                              cep_lo=lo[0, a], cep_hi=hi[0, a]))
        print(f"  {name:20} ({npu:3}p) jóvenes {Bn[0,0]*100:3.0f} · mayores {Bn[0,2]*100:3.0f}")
    pd.DataFrame(drows).to_csv(os.path.join(OUT, "ei-deptos.csv"), index=False)
    print("\nei-ciudades.csv + ei-deptos.csv escritos.")


if __name__ == "__main__":
    main()
