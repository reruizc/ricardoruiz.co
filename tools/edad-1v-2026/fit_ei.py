#!/usr/bin/env python3
"""Paso 3 del modelo: inferencia ecológica RxC con restricciones de símplex.

Estimador: mínimos cuadrados ponderados por votos con beta_ca ∈ [0,1] y
Σ_c beta_ca = 1 (proyección al símplex por banda; Duchi et al. 2008),
estimado POR ESTRATO (región x Bogotá) y agregado nacionalmente con pesos
de votantes por banda. Incertidumbre: bootstrap por conglomerados
(municipios) + ruido de proyección en w26 calibrado con el backtest
2018->2022. Cotas deterministas de Duncan-Davis (1953) condicionales a la
composición etaria.

Salidas en Bases de datos/output_edad_1v/:
   ei-final.csv (long: year, cand, grupo, beta, lo, hi, dd_lo, dd_hi)
   ei-report.txt
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe_viabilidad import BANDS, nrm  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "Bases de datos", "output_edad_1v")

GROUPS = {"18-25": [0, 1], "26-35": [2, 3], "36-45": [4, 5],
          "46-60": [6, 7, 8], "61+": [9]}
GNAMES = list(GROUPS)
NG = len(GNAMES)

REGION = {}
for n in ("ATLANTICO BOLIVAR CESAR CORDOBA MAGDALENA SUCRE".split()):
    REGION[n] = "CARIBE"
REGION.update({"LA GUAJIRA": "CARIBE", "GUAJIRA": "CARIBE", "SAN ANDRES": "CARIBE"})
for n in ("ANTIOQUIA CALDAS QUINDIO RISARALDA".split()):
    REGION[n] = "ANT-EJE"
for n in ("CAUCA NARINO CHOCO".split()):
    REGION[n] = "PACIFICO"
REGION.update({"VALLE": "PACIFICO", "VALLE DEL CAUCA": "PACIFICO"})
for n in ("CUNDINAMARCA BOYACA SANTANDER".split()):
    REGION[n] = "CEN-ORIENTE"
REGION["NORTE DE SANTANDER"] = "CEN-ORIENTE"
for n in ("TOLIMA HUILA CAQUETA PUTUMAYO AMAZONAS".split()):
    REGION[n] = "SUR"
for n in ("META CASANARE ARAUCA VICHADA GUAVIARE GUAINIA VAUPES".split()):
    REGION[n] = "LLANOS"
REGION["BOGOTA DC"] = "BOGOTA"

CANDS = {
    2022: ["petro", "fico", "rodolfo", "fajardo", "blanco", "resto"],
    2026: ["cepeda", "abelardo", "paloma", "fajardo26", "blanco", "resto"],
}
LABEL = {"petro": "Petro", "fico": "Fico", "rodolfo": "Rodolfo",
         "fajardo": "Fajardo", "cepeda": "Cepeda", "abelardo": "Abelardo",
         "paloma": "Paloma", "fajardo26": "Fajardo", "blanco": "Blanco",
         "resto": "Resto*"}

RNG = np.random.default_rng(20260609)
B_BOOT = 300


def region_of(depname):
    n = nrm(depname)
    if n in REGION:
        return REGION[n]
    for k, v in REGION.items():
        if k in n or n in k:
            return v
    return "SUR"


# ----------------------------------------------------------------- solver
def proj_simplex_cols(B):
    C = B.shape[0]
    u = -np.sort(-B, axis=0)
    css = np.cumsum(u, axis=0) - 1.0
    j = np.arange(1, C + 1)[:, None]
    cond = u - css / j > 0
    rho = C - 1 - np.argmax(cond[::-1, :], axis=0)
    tau = css[rho, np.arange(B.shape[1])] / (rho + 1)
    return np.maximum(B - tau[None, :], 0.0)


def fit_qp(W, Y, T, iters=3000, tol=1e-10):
    """min Σ_p T_p ||y_p - B w_p||²  s.a. columnas de B en el símplex."""
    G = (W * T[:, None]).T @ W
    H = (Y * T[:, None]).T @ W
    L = 2 * np.linalg.eigvalsh(G).max()
    eta = 1.0 / L
    C = Y.shape[1]
    B = np.full((C, W.shape[1]), 1.0 / C)
    for _ in range(iters):
        Bn = proj_simplex_cols(B - eta * 2 * (B @ G - H))
        if np.abs(Bn - B).max() < tol:
            B = Bn
            break
        B = Bn
    return B


# ----------------------------------------------------------------- datos
def load_year(year):
    """-> df con pcode, mun, stratum, T, W (shares 5 grupos), Y (shares)."""
    if year == 2022:
        e = pd.read_csv(os.path.join(OUT, "edad-2022-puesto.csv"), dtype={"pcode": str})
        v = pd.read_csv(os.path.join(OUT, "votos-2022-puesto.csv"), dtype={"pcode": str})
        m = e.merge(v, on="pcode")
        m["ratio"] = m["Cantidad de Sufragantes"] / m["total_votos"].clip(lower=1)
        m = m[m["ratio"].between(0.70, 1.10) & (m["total_votos"] >= 200)].copy()
        raw = m[BANDS].values.astype(float)
        depname = m["depname"]
        cands = ["petro", "fico", "rodolfo", "fajardo", "blanco"]
    else:
        w = pd.read_csv(os.path.join(OUT, "w26-puesto.csv"), dtype={"pcode": str})
        v = pd.read_csv(os.path.join(OUT, "votos-2026-puesto.csv"), dtype={"pcode": str})
        e = pd.read_csv(os.path.join(OUT, "edad-2022-puesto.csv"), dtype={"pcode": str})
        dep2name = (e.assign(dep=e["pcode"].str[:2])
                    .groupby("dep")["depname"].agg(lambda s: s.mode()[0]))
        m = w[w["seed_level"].isin(["puesto", "zona"])].merge(v, on="pcode",
                                                              suffixes=("", "_v"))
        m = m[m["total_votos"] >= 200].copy()
        raw = m[[f"b{b}" for b in range(10)]].values.astype(float)
        depname = m["pcode"].str[:2].map(dep2name)
        cands = ["cepeda", "abelardo", "paloma", "fajardo26", "blanco"]

    Wg = np.stack([raw[:, idx].sum(axis=1) for idx in GROUPS.values()], axis=1)
    Wg = Wg / np.maximum(Wg.sum(axis=1, keepdims=True), 1e-9)
    T = m["total_votos"].values.astype(float)
    Y = m[cands].values.astype(float)
    resto = T - Y.sum(axis=1)
    Y = np.column_stack([Y, resto]) / T[:, None]
    return pd.DataFrame({
        "pcode": m["pcode"].values,
        "mun": m["pcode"].str[:6].values,
        "stratum": depname.map(region_of).values,
    }), Wg, Y, T


# ----------------------------------------------------------------- agregación
def fit_national(meta, W, Y, T):
    strata = sorted(meta["stratum"].unique())
    Bs, Ms = {}, {}
    for s in strata:
        sel = (meta["stratum"] == s).values
        Bs[s] = fit_qp(W[sel], Y[sel], T[sel])
        Ms[s] = (W[sel] * T[sel, None]).sum(axis=0)   # votantes por grupo
    Mtot = sum(Ms.values())
    Bn = sum(Bs[s] * (Ms[s] / Mtot)[None, :] for s in strata)
    return Bn, Bs, Mtot


def duncan_davis(W, Y, T):
    n_a = W * T[:, None]                  # votantes por grupo (condicional a w)
    V = Y * T[:, None]
    C, A = Y.shape[1], W.shape[1]
    lo = np.zeros((C, A))
    hi = np.zeros((C, A))
    for a in range(A):
        rest = T - n_a[:, a]
        for c in range(C):
            lo[c, a] = np.maximum(0.0, V[:, c] - rest).sum()
            hi[c, a] = np.minimum(V[:, c], n_a[:, a]).sum()
    tot = n_a.sum(axis=0)
    return lo / tot, hi / tot


def backtest_sigma():
    """sd del error de forma por grupo (5) derivado del backtest 18->22."""
    e18 = pd.read_csv(os.path.join(OUT, "edad-2018-puesto.csv"), dtype={"pcode": str})
    e22 = pd.read_csv(os.path.join(OUT, "edad-2022-puesto.csv"), dtype={"pcode": str})
    ks = set(e18.pcode) & set(e22.pcode)
    a18 = e18[e18.pcode.isin(ks)].set_index("pcode")[BANDS].astype(float)
    a22 = e22[e22.pcode.isin(ks)].set_index("pcode")[BANDS].astype(float).loc[a18.index]
    ok = (a18.sum(axis=1) >= 100) & (a22.sum(axis=1) >= 100)
    g18 = np.stack([a18[ok].values[:, i].sum(axis=1) for i in GROUPS.values()], axis=1)
    g22 = np.stack([a22[ok].values[:, i].sum(axis=1) for i in GROUPS.values()], axis=1)
    s18 = g18 / g18.sum(axis=1, keepdims=True)
    s22 = g22 / g22.sum(axis=1, keepdims=True)
    mae = np.abs(s18 - s22).mean(axis=0)          # por grupo
    return mae * 1.2533                            # MAE -> sd (half-normal)


def bootstrap(meta, W, Y, T, sigma=None, B=B_BOOT):
    muns = meta.groupby(["stratum", "mun"]).indices
    by_stratum = {}
    for (s, mn), idx in muns.items():
        by_stratum.setdefault(s, []).append(np.asarray(idx))
    out = []
    for _ in range(B):
        Bs, Ms = {}, {}
        for s, blocks in by_stratum.items():
            pick = RNG.integers(0, len(blocks), len(blocks))
            idx = np.concatenate([blocks[i] for i in pick])
            Wb = W[idx]
            if sigma is not None:                  # ruido de proyección (2026)
                Wb = np.maximum(Wb + RNG.normal(0, sigma, Wb.shape), 1e-4)
                Wb = Wb / Wb.sum(axis=1, keepdims=True)
            Bs[s] = fit_qp(Wb, Y[idx], T[idx], iters=1500)
            Ms[s] = (Wb * T[idx, None]).sum(axis=0)
        Mtot = sum(Ms.values())
        out.append(sum(Bs[s] * (Ms[s] / Mtot)[None, :] for s in Bs))
    return np.stack(out)                           # B x C x A


# ----------------------------------------------------------------- report
def run_year(year, sigma, report, rows):
    meta, W, Y, T = load_year(year)
    cands = CANDS[year]
    report.append(f"\n{'='*74}\n1V-{year} · {len(meta):,} puestos · "
                  f"{T.sum():,.0f} votos en muestra EI\n{'='*74}")
    Bn, Bs, M = fit_national(meta, W, Y, T)
    dd_lo, dd_hi = duncan_davis(W, Y, T)
    # IC: bootstrap por conglomerados SIN ruido extra (el ruido de proyección
    # se evalúa aparte como sensibilidad — meterlo al bootstrap atenúa, EIV)
    boots = bootstrap(meta, W, Y, T, sigma=None)
    lo = np.percentile(boots, 2.5, axis=0)
    hi = np.percentile(boots, 97.5, axis=0)

    Wsh = M / M.sum()
    report.append("peso de cada grupo etario en la muestra: " +
                  "  ".join(f"{g}:{Wsh[a]*100:.1f}%" for a, g in enumerate(GNAMES)))
    report.append("\n% del voto DENTRO de cada grupo etario · punto (IC 95%) [cotas DD]:")
    head = "          " + "".join(f"{g:>22s}" for g in GNAMES)
    report.append(head)
    for c, cand in enumerate(cands):
        cells = []
        for a in range(NG):
            cells.append(f"{Bn[c,a]*100:5.1f} ({lo[c,a]*100:4.1f}-{hi[c,a]*100:4.1f})"
                         f"[{dd_lo[c,a]*100:2.0f}-{dd_hi[c,a]*100:3.0f}]")
        report.append(f"  {LABEL[cand]:8s}" + "  ".join(cells))
        for a in range(NG):
            rows.append(dict(year=year, cand=LABEL[cand], grupo=GNAMES[a],
                             beta=Bn[c, a], lo=lo[c, a], hi=hi[c, a],
                             dd_lo=dd_lo[c, a], dd_hi=dd_hi[c, a]))

    # consistencia nacional
    impl = Bn @ Wsh
    obs = (Y * T[:, None]).sum(axis=0) / T.sum()
    report.append("\nconsistencia nacional (implícito vs observado en muestra):")
    report.append("  " + " · ".join(f"{LABEL[c]} {i*100:.1f}/{o*100:.1f}"
                                    for c, i, o in zip(cands, impl, obs)))

    # sensibilidad al error de proyección (solo 2026): re-estima con ruido
    # sigma del backtest en w; la compresión hacia el centro acota el efecto
    if sigma is not None:
        boots_n = bootstrap(meta, W, Y, T, sigma=sigma, B=150)
        med_n = np.median(boots_n, axis=0)
        report.append("\nsensibilidad a error de proyección (ruido sigma del "
                      "backtest en w26; compresión máx por candidato, pp):")
        report.append("  " + " · ".join(
            f"{LABEL[c]} {np.abs(med_n[i]-Bn[i]).max()*100:.1f}"
            for i, c in enumerate(cands)))
        report.append("  (el error de proyección ATENÚA: los contrastes "
                      "reales serían iguales o mayores que los reportados)")

    # composición del electorado de cada candidato (gamma)
    gam = Bn * Wsh[None, :]
    gam = gam / gam.sum(axis=1, keepdims=True)
    gb = boots * Wsh[None, None, :]
    gb = gb / gb.sum(axis=2, keepdims=True)
    glo, ghi = np.percentile(gb, 2.5, axis=0), np.percentile(gb, 97.5, axis=0)
    report.append("\ncomposición etaria del electorado de cada candidato (filas=100%):")
    report.append(head)
    for c, cand in enumerate(cands):
        cells = [f"{gam[c,a]*100:5.1f} ({glo[c,a]*100:4.1f}-{ghi[c,a]*100:4.1f})"
                 for a in range(NG)]
        report.append(f"  {LABEL[cand]:8s}" + "  ".join(f"{x:>22s}" for x in cells))
    return Bn


def main():
    report, rows = [], []
    sig = backtest_sigma()
    report.append("sd de ruido de proyección por grupo (de backtest 18->22, pp): " +
                  "  ".join(f"{g}:{s*100:.2f}" for g, s in zip(GNAMES, sig)))
    run_year(2022, None, report, rows)
    run_year(2026, sig, report, rows)
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "ei-final.csv"), index=False)
    txt = "\n".join(report)
    with open(os.path.join(OUT, "ei-report.txt"), "w") as f:
        f.write(txt)
    print(txt)
    print("\n* Resto = otros candidatos + nulos + no marcados (2026 incluye "
          "Claudia López); base = total de votantes.")


if __name__ == "__main__":
    main()
