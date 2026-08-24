#!/usr/bin/env python3
"""Paso 4 · inferencia ecológica RxC sexo×edad por municipio.

Para cada (corporación, año):
  1. estima beta[partido, celda] = % del voto del partido DENTRO de cada celda
     sexo×edad, con WLS + restricción de símplex por celda (Goodman+Duchi 2008),
     a nivel departamental (Cundinamarca), ponderado por votos.
  2. en cada municipio, reparte el voto real de cada lista entre las 10 celdas
     por ajuste biproporcional (IPF) que respeta DOS márgenes observados:
       - filas  = votos reales de cada lista en el municipio
       - columnas = votantes por celda (observado 2022 / proyectado 2026)
     => la estimación SIEMPRE cuadra con los totales reales.
  3. cotas duras de Duncan-Davis por celda (sin supuestos) + IC 90% por
     bootstrap de conglomerados (municipios) sobre beta.

Salidas:
  ei-cundi-long.csv      (year,corp,mun,partido,sexo,grupo,punto,cota_min,cota_max,ic_lo,ic_hi)
  ei-cundi-beta-dept.csv (year,corp,partido,celda,beta,dd_lo,dd_hi)
"""
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, CELL_LABELS, CELLS

BLANCO, NULOS, NOMARC = "__BLANCO__", "__NULOS__", "__NOMARC__"
PARTY_MIN_SHARE = 0.008          # < 0.8% del válido+blanco -> "Otras listas"
MINV = {2022: 60, 2026: 100}     # votos mínimos por unidad para estimar beta
B_BOOT = 200
RNG = np.random.default_rng(20260619)

# La señal de EDAD entre unidades es fuerte y bien identificada; la de SEXO es
# ~nula (corr(%mujeres, voto)≈0 en Cundinamarca: las mesas están segregadas por
# sexo pero el voto no cambia con el % de mujeres). Sin regularización la QP
# explota esa dirección no-identificada y produce contrastes de sexo absurdos
# (artefacto/solución de esquina). Penalizamos el CONTRASTE de sexo dentro de
# cada grupo de edad (empuja beta_Hg -> beta_Mg salvo que el dato lo sostenga) y
# añadimos un ridge global leve que levanta los ceros exactos. La EDAD queda libre.
HCOLS = [0, 1, 2, 3, 4]          # celdas Hombres por grupo
MCOLS = [5, 6, 7, 8, 9]          # celdas Mujeres por grupo
LAM_SEX_FRAC = 1.0               # fuerza del shrink al contraste de sexo
LAM0_FRAC = 0.30                 # ridge global: levanta esquinas (ceros exactos)


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


def fit_qp(W, Y, T, s, iters=3000, tol=1e-11):
    """min Σ_p T_p ||y_p - B w_p||² + λsex·Σ(β_Hg-β_Mg)² + λ0·||B-s||²
    s.a. columnas de B en el símplex. s = cuota global del partido (C,)."""
    G = (W * T[:, None]).T @ W
    H = (Y * T[:, None]).T @ W
    ev = np.linalg.eigvalsh(G)
    base = ev.mean()
    lam_sex = LAM_SEX_FRAC * base
    lam0 = LAM0_FRAC * base
    L = 2 * ev.max() + 2 * lam0 + 2 * lam_sex
    eta = 1.0 / L
    B = np.tile(s[:, None], (1, W.shape[1])).astype(float)
    for _ in range(iters):
        grad = 2 * (B @ G - H) + 2 * lam0 * (B - s[:, None])
        diff = B[:, HCOLS] - B[:, MCOLS]
        D = np.zeros_like(B)
        D[:, HCOLS] = diff
        D[:, MCOLS] = -diff
        grad += 2 * lam_sex * D
        Bn = proj_simplex_cols(B - eta * grad)
        if np.abs(Bn - B).max() < tol:
            return Bn
        B = Bn
    return B


def rake(seed, row_marg, col_marg, iters=400):
    """IPF biproporcional: ajusta seed (C×A) a márgenes fila y columna."""
    X = np.maximum(seed, 0) + 1e-9 * col_marg[None, :]
    X[row_marg <= 0, :] = 0.0
    for _ in range(iters):
        rs = X.sum(1)
        X *= np.where(rs > 0, row_marg / np.maximum(rs, 1e-12), 0.0)[:, None]
        cs = X.sum(0)
        X *= np.where(cs > 0, col_marg / np.maximum(cs, 1e-12), 1.0)[None, :]
    return X


def rake_batch(seeds, row_marg, col_marg, iters=120):
    """IPF vectorizado sobre B semillas (B×C×A) con los mismos márgenes."""
    X = np.maximum(seeds, 0) + 1e-9 * col_marg[None, None, :]
    X[:, row_marg <= 0, :] = 0.0
    rm = row_marg[None, :]
    cm = col_marg[None, :]
    for _ in range(iters):
        rs = X.sum(2)
        X *= np.where(rs > 0, rm / np.maximum(rs, 1e-12), 0.0)[:, :, None]
        cs = X.sum(1)
        X *= np.where(cs > 0, cm / np.maximum(cs, 1e-12), 1.0)[:, None, :]
    return X


def duncan_davis(W, Y, T):
    """cotas deterministas de beta DENTRO de cada celda (fracción), nivel dept."""
    n_a = W * T[:, None]
    V = Y * T[:, None]
    C, A = Y.shape[1], W.shape[1]
    lo = np.zeros((C, A)); hi = np.zeros((C, A))
    for a in range(A):
        rest = T - n_a[:, a]
        for c in range(C):
            lo[c, a] = np.maximum(0.0, V[:, c] - rest).sum()
            hi[c, a] = np.minimum(V[:, c], n_a[:, a]).sum()
    tot = n_a.sum(axis=0)
    return lo / tot, hi / tot


# ----------------------------------------------------------------- datos
def load_units(corp, year):
    if year == 2022:
        v = pd.read_csv(os.path.join(OUT, "votos-2022-cundi-mesa.csv"), dtype=str)
        comp = pd.read_csv(os.path.join(OUT, "comp-2022-mesa.csv"), dtype={"mesa": str})
        keycol = "mesa"
    else:
        v = pd.read_csv(os.path.join(OUT, "votos-2026-cundi-puesto.csv"), dtype=str)
        comp = pd.read_csv(os.path.join(OUT, "comp-2026-puesto.csv"), dtype={"puesto": str})
        keycol = "puesto"
    v["votos"] = pd.to_numeric(v["votos"], errors="coerce").fillna(0)
    v = v[v["corp"] == corp].copy()
    v = v[~v["par_code"].isin([NULOS, NOMARC])]          # universo = listas + blanco

    # set de partidos nombrados (>= umbral del total válido+blanco)
    tot = v.groupby(["par_code", "partido"])["votos"].sum()
    base = tot.sum()
    named = [(pc, nm) for (pc, nm), s in tot.items()
             if pc != BLANCO and s >= PARTY_MIN_SHARE * base]
    named.sort(key=lambda x: -tot[x])
    named_codes = {pc for pc, _ in named}

    def colname(pc, nm):
        if pc == BLANCO:
            return "Votos en blanco"
        if pc in named_codes:
            return nm
        return "Otras listas"
    v["col"] = [colname(pc, nm) for pc, nm in zip(v["par_code"], v["partido"])]
    order = [nm for _, nm in named] + ["Otras listas", "Votos en blanco"]
    order = [c for c in order if c in set(v["col"])]

    # totales por municipio (TODAS las unidades, exactos)
    vm = v.copy()
    vm["mun"] = vm["key"].str[:6]
    Vmun = (vm.groupby(["mun", "col"])["votos"].sum().unstack(fill_value=0)
            .reindex(columns=order, fill_value=0))

    # matriz unidad × partido (para estimar beta)
    pv = (v.groupby(["key", "col"])["votos"].sum().unstack(fill_value=0)
          .reindex(columns=order, fill_value=0))
    df = comp.merge(pv, left_on=keycol, right_index=True, how="inner")
    n = df[CELL_LABELS].values.astype(float)
    Vc = df[order].values.astype(float)
    Tv = Vc.sum(1)
    keep = (Tv >= MINV[year]) & (n.sum(1) > 0)
    df, n, Vc, Tv = df[keep], n[keep], Vc[keep], Tv[keep]
    W = n / np.maximum(n.sum(1, keepdims=True), 1e-9)
    Y = Vc / np.maximum(Tv[:, None], 1e-9)
    meta = pd.DataFrame({"mun": df[keycol].str[:6].values})
    return meta, W, Y, Tv, order, Vmun


def bootstrap_beta(meta, W, Y, T, s, B=B_BOOT):
    blocks = [np.asarray(ix) for ix in meta.groupby("mun").indices.values()]
    out = []
    for _ in range(B):
        pick = RNG.integers(0, len(blocks), len(blocks))
        idx = np.concatenate([blocks[i] for i in pick])
        out.append(fit_qp(W[idx], Y[idx], T[idx], s, iters=1500))
    return out


# ----------------------------------------------------------------- por municipio
def municipal(corp, year, beta, betas_boot, order, Vmun):
    comp = pd.read_csv(os.path.join(OUT, f"comp-{year}-mun.csv"), dtype={"mun": str})
    comp = comp.set_index("mun")
    BB = np.stack(betas_boot)                              # B×C×A
    rows = []
    for mun, vrow in Vmun.iterrows():
        if mun not in comp.index:
            continue
        n_a = comp.loc[mun, CELL_LABELS].values.astype(float)
        V = vrow.values.astype(float)                    # por partido (order)
        Tv = V.sum()
        if Tv <= 0 or n_a.sum() <= 0:
            continue
        c_a = n_a * (Tv / n_a.sum())                     # celdas escaladas a válido+blanco
        X = rake(beta * c_a[None, :], V, c_a)            # punto C×A
        # cotas duras por celda
        lo_hard = np.maximum(0.0, V[:, None] + c_a[None, :] - Tv)
        hi_hard = np.minimum(V[:, None], c_a[None, :])
        # IC por bootstrap de beta (raking vectorizado sobre B)
        seeds = BB * c_a[None, None, :]                   # B×C×A
        stack = rake_batch(seeds, V, c_a)
        ic_lo = np.percentile(stack, 5, axis=0)
        ic_hi = np.percentile(stack, 95, axis=0)
        for p, party in enumerate(order):
            if V[p] <= 0:
                continue
            for a, (sx, gr) in enumerate(CELLS):
                rows.append((year, corp, mun, party, sx, gr,
                             X[p, a], lo_hard[p, a], hi_hard[p, a],
                             ic_lo[p, a], ic_hi[p, a]))
    return rows


def main():
    long_rows, beta_rows = [], []
    for corp in ("SENADO", "CAMARA"):
        for year in (2022, 2026):
            meta, W, Y, T, order, Vmun = load_units(corp, year)
            obs = (Y * T[:, None]).sum(0) / T.sum()       # cuota global (s)
            beta = fit_qp(W, Y, T, obs)
            dd_lo, dd_hi = duncan_davis(W, Y, T)
            betas_boot = bootstrap_beta(meta, W, Y, T, obs)
            # consistencia dept: implícito vs observado
            Wsh = (W * T[:, None]).sum(0); Wsh /= Wsh.sum()
            impl = beta @ Wsh
            print(f"\n== {corp} {year} == unidades={len(meta):,} "
                  f"votos muestra={T.sum():,.0f} · partidos={len(order)}")
            print("   consistencia implícito/observado (máx dif pp): "
                  f"{np.abs(impl-obs).max()*100:.2f}")
            for p, party in enumerate(order):
                for a, lab in enumerate(CELL_LABELS):
                    beta_rows.append((year, corp, party, lab,
                                      beta[p, a], dd_lo[p, a], dd_hi[p, a]))
            mrows = municipal(corp, year, beta, betas_boot, order, Vmun)
            long_rows += mrows
            print(f"   filas municipio×partido×celda: {len(mrows):,}")

    pd.DataFrame(long_rows, columns=[
        "year", "corp", "mun", "partido", "sexo", "grupo",
        "punto", "cota_min", "cota_max", "ic_lo", "ic_hi"]
    ).to_csv(os.path.join(OUT, "ei-cundi-long.csv"), index=False)
    pd.DataFrame(beta_rows, columns=[
        "year", "corp", "partido", "celda", "beta", "dd_lo", "dd_hi"]
    ).to_csv(os.path.join(OUT, "ei-cundi-beta-dept.csv"), index=False)
    print(f"\n-> ei-cundi-long.csv ({len(long_rows):,} filas)")
    print(f"-> ei-cundi-beta-dept.csv ({len(beta_rows):,} filas)")


if __name__ == "__main__":
    main()
