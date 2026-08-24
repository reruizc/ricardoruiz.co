#!/usr/bin/env python3
"""Inferencia ecológica del voto por SEXO (y sexo x edad) · 1V-2026 vs 2022.

Reutiliza el estimador QP-símplex de tools/edad-1v-2026/fit_ei.py.

Bloques:
  A. Nacional sexo (2 grupos: Mujer/Hombre, 6 candidatos) -> "si solo votaran
     mujeres / hombres", brecha por candidato, cotas Duncan-Davis, IC bootstrap.
  B. Nacional sexo x edad (6 grupos) -> mujeres jóvenes vs adultas vs mayores.
  C. Head-to-head Cepeda vs Abelardo por SEXO en depto y ciudad (binario,
     robusto) -> mapa de ganador entre mujeres vs entre hombres.
  D. Head-to-head Cepeda vs Abelardo por sexo x edad (3 bandas) nacional +
     ciudades, con shrink al prior nacional -> "el gráfico de la imagen, mujeres".

Salida: Bases de datos/output_mujeres_1v/mujeres-ei.json (+ -report.txt)
"""
import json
import os
import sys

import numpy as np
import pandas as pd

EDAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "edad-1v-2026")
sys.path.insert(0, os.path.abspath(EDAD))
from fit_ei import (fit_qp, fit_national, duncan_davis, region_of,  # noqa: E402
                    proj_simplex_cols)
from build_blocs_depto import DEP  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..", "..", "Bases de datos")
OUT = os.path.join(BASE, "output_mujeres_1v")
EOUT = os.path.join(BASE, "output_edad_1v")

HCOLS = [f"H{b}" for b in range(10)]
MCOLS = [f"M{b}" for b in range(10)]
# colapso a 3 bandas etarias (como la imagen): 18-35 / 36-60 / 61+
B3 = [[0, 1, 2, 3], [4, 5, 6, 7, 8], [9]]
AGE3 = ["18-35", "36-60", "61+"]

CANDS = {2022: ["petro", "fico", "rodolfo", "fajardo", "blanco"],
         2026: ["cepeda", "abelardo", "paloma", "fajardo26", "blanco"]}
LABEL = {"petro": "Petro", "fico": "Fico", "rodolfo": "Rodolfo",
         "fajardo": "Fajardo", "cepeda": "Cepeda", "abelardo": "Abelardo",
         "paloma": "Paloma", "fajardo26": "Fajardo", "blanco": "Blanco",
         "resto": "Otros*"}
RNG = np.random.default_rng(20260611)
SHRINK = 0.02
WS_LO, WS_HI = 0.25, 0.75   # sanity de share de mujeres por puesto


def load_year(year, min_votes=200, seeds=("puesto", "zona")):
    """-> meta(df), cells(n x 20 conteos sexo x banda), Y(shares incl resto), T."""
    if year == 2022:
        g = pd.read_csv(os.path.join(OUT, "gen-2022-puesto.csv"), dtype={"pcode": str})
        v = pd.read_csv(os.path.join(EOUT, "votos-2022-puesto.csv"), dtype={"pcode": str})
        m = g.merge(v, on="pcode")
        m["ratio"] = m["Cantidad de Sufragantes"] / m["total_votos"].clip(lower=1)
        m = m[m["ratio"].between(0.70, 1.10) & (m["total_votos"] >= min_votes)].copy()
        cells = m[HCOLS + MCOLS].values.astype(float)
        depname = m["depname"]
        cands = CANDS[2022]
    else:
        w = pd.read_csv(os.path.join(OUT, "w26-gen-puesto.csv"), dtype={"pcode": str})
        v = pd.read_csv(os.path.join(EOUT, "votos-2026-puesto.csv"), dtype={"pcode": str})
        g = pd.read_csv(os.path.join(OUT, "gen-2022-puesto.csv"), dtype={"pcode": str})
        dep2name = (g.assign(dep=g["pcode"].str[:2])
                    .groupby("dep")["depname"].agg(lambda s: s.mode()[0]))
        m = w[w["seed_level"].isin(list(seeds))].merge(v, on="pcode", suffixes=("", "_v"))
        m = m[m["total_votos"] >= min_votes].copy()
        cells = m[HCOLS + MCOLS].values.astype(float)
        depname = m["pcode"].str[:2].map(dep2name)
        cands = CANDS[2026]
    # sanity share mujeres
    tot = cells.sum(axis=1)
    wsh = cells[:, 10:].sum(axis=1) / np.maximum(tot, 1e-9)
    keep = (wsh >= WS_LO) & (wsh <= WS_HI)
    m, cells, depname = m[keep].copy(), cells[keep], depname[keep]
    T = m["total_votos"].values.astype(float)
    Y = m[cands].values.astype(float)
    Y = np.column_stack([Y, T - Y.sum(axis=1)]) / T[:, None]
    meta = pd.DataFrame({"pcode": m["pcode"].values,
                         "mun": m["pcode"].str[:6].values,
                         "dep": m["pcode"].str[:2].values,
                         "stratum": depname.map(region_of).values})
    return meta.reset_index(drop=True), cells, Y, T


def W_sex(cells):
    """[Mujer, Hombre] shares."""
    M = cells[:, 10:].sum(axis=1)
    H = cells[:, :10].sum(axis=1)
    Wg = np.column_stack([M, H])
    return Wg / np.maximum(Wg.sum(axis=1, keepdims=True), 1e-9)


def W_sexage(cells):
    """6 grupos: M18-35,M36-60,M61, H18-35,H36-60,H61 (shares)."""
    M = cells[:, 10:]
    H = cells[:, :10]
    cols = ([M[:, idx].sum(axis=1) for idx in B3] +
            [H[:, idx].sum(axis=1) for idx in B3])
    Wg = np.column_stack(cols)
    return Wg / np.maximum(Wg.sum(axis=1, keepdims=True), 1e-9)


def boot_national(meta, W, Y, T, B=250):
    muns = meta.groupby(["stratum", "mun"]).indices
    by = {}
    for (s, mn), idx in muns.items():
        by.setdefault(s, []).append(np.asarray(idx))
    out = []
    for _ in range(B):
        Bs, Ms = {}, {}
        for s, blocks in by.items():
            pick = RNG.integers(0, len(blocks), len(blocks))
            idx = np.concatenate([blocks[i] for i in pick])
            Bs[s] = fit_qp(W[idx], Y[idx], T[idx], iters=1500)
            Ms[s] = (W[idx] * T[idx, None]).sum(axis=0)
        Mtot = sum(Ms.values())
        out.append(sum(Bs[s] * (Ms[s] / Mtot)[None, :] for s in Bs))
    return np.stack(out)


# ----------------------------------------------------- head-to-head helpers
def fit_qp_reg(W, Y, T, B0, lam, iters=2500, tol=1e-10):
    G = (W * T[:, None]).T @ W
    H = (Y * T[:, None]).T @ W
    L = 2 * (np.linalg.eigvalsh(G).max() + lam)
    eta = 1.0 / L
    B = B0.copy()
    for _ in range(iters):
        Bn = proj_simplex_cols(B - eta * (2 * (B @ G - H) + 2 * lam * (B - B0)))
        if np.abs(Bn - B).max() < tol:
            B = Bn
            break
        B = Bn
    return B


def h2h_YT(Y, T, cands):
    ci, ai = cands.index("cepeda" if "cepeda" in cands else "petro"), \
             cands.index("abelardo" if "abelardo" in cands else "fico")
    # Y already shares incl resto; reconstruct counts via T
    cep = Y[:, ci] * T
    abe = Y[:, ai] * T
    tot2 = np.maximum(cep + abe, 1e-9)
    Y2 = np.column_stack([cep / tot2, abe / tot2])
    return Y2, tot2


def main():
    rep, J = [], {}

    def log(*a):
        s = " ".join(str(x) for x in a)
        print(s, flush=True)
        rep.append(s)

    for year in (2022, 2026):
        cands = CANDS[year] + ["resto"]
        meta, cells, Y, T = load_year(year)
        Wg = W_sex(cells)
        log("=" * 70)
        log(f"1V-{year} · {len(meta):,} puestos · {T.sum():,.0f} votos muestra EI")
        log(f"  share mujeres en la muestra: {(Wg[:,0]*T).sum()/T.sum()*100:.2f}%")

        # ---- A. nacional por sexo ----
        Bn, Bs, Mtot = fit_national(meta, Wg, Y, T)
        dd_lo, dd_hi = duncan_davis(Wg, Y, T)
        boots = boot_national(meta, Wg, Y, T)
        lo = np.percentile(boots, 2.5, axis=0)
        hi = np.percentile(boots, 97.5, axis=0)
        obs = (Y * T[:, None]).sum(0) / T.sum()
        impl = Bn @ (Mtot / Mtot.sum())
        log(f"  consistencia (impl/obs): " +
            " · ".join(f"{LABEL[c]} {impl[i]*100:.1f}/{obs[i]*100:.1f}"
                       for i, c in enumerate(cands)))
        log("  voto DENTRO de cada sexo · punto (IC95) [cota dura DD]:")
        log(f"    {'cand':9s}{'MUJERES':>26s}{'HOMBRES':>26s}  brecha(M-H)")
        ydict = {}
        for i, c in enumerate(cands):
            mc = f"{Bn[i,0]*100:5.1f} ({lo[i,0]*100:4.1f}-{hi[i,0]*100:4.1f})[{dd_lo[i,0]*100:.0f}-{dd_hi[i,0]*100:.0f}]"
            hc = f"{Bn[i,1]*100:5.1f} ({lo[i,1]*100:4.1f}-{hi[i,1]*100:4.1f})[{dd_lo[i,1]*100:.0f}-{dd_hi[i,1]*100:.0f}]"
            log(f"    {LABEL[c]:9s}{mc:>26s}{hc:>26s}  {(Bn[i,0]-Bn[i,1])*100:+5.1f}")
            ydict[c] = dict(label=LABEL[c],
                            muj=round(Bn[i, 0]*100, 2), hom=round(Bn[i, 1]*100, 2),
                            muj_lo=round(lo[i, 0]*100, 2), muj_hi=round(hi[i, 0]*100, 2),
                            dd_lo=round(dd_lo[i, 0]*100, 1), dd_hi=round(dd_hi[i, 0]*100, 1),
                            real=round(obs[i]*100, 2),
                            brecha=round((Bn[i, 0]-Bn[i, 1])*100, 2))
        J.setdefault(str(year), {})["sexo_nacional"] = ydict
        J[str(year)]["share_mujeres_votantes"] = round((Wg[:, 0]*T).sum()/T.sum()*100, 2)

        # ---- B. nacional sexo x edad (6 grupos) ----
        W6 = W_sexage(cells)
        B6, Bs6, M6 = fit_national(meta, W6, Y, T)
        gnames6 = ["M·18-35", "M·36-60", "M·61+", "H·18-35", "H·36-60", "H·61+"]
        log("\n  voto por sexo x edad (6 grupos) · % dentro del grupo:")
        log("    " + "cand".ljust(9) + "".join(f"{g:>11s}" for g in gnames6))
        sxa = {}
        for i, c in enumerate(cands):
            log("    " + LABEL[c].ljust(9) + "".join(f"{B6[i,a]*100:10.1f} " for a in range(6)))
            sxa[c] = {gnames6[a]: round(B6[i, a]*100, 2) for a in range(6)}
        J[str(year)]["sexo_edad_nacional"] = sxa
        J[str(year)]["peso_grupo_sexoedad"] = {gnames6[a]: round(M6[a]/M6.sum()*100, 2)
                                               for a in range(6)}

    # ===================== 2026: H2H geográfico por sexo =====================
    meta, cells, Y, T = load_year(2026)
    cands = CANDS[2026] + ["resto"]
    Wg = W_sex(cells)
    W6 = W_sexage(cells)
    Y2, T2 = h2h_YT(Y, T, cands)

    # prior nacional H2H por sexo (2 grupos) y por sexo x edad (6 grupos)
    B0_sex, _, _ = fit_national(meta, Wg, Y2, T2)
    B0_sxa, _, M6 = fit_national(meta, W6, Y2, T2)
    log("\n" + "=" * 70)
    log("H2H Cepeda vs Abelardo · NACIONAL")
    log(f"  por sexo  -> mujeres {B0_sex[0,0]*100:.1f} · hombres {B0_sex[0,1]*100:.1f}")
    log("  por sexo x edad (Cepeda % del duelo):")
    gnames6 = ["M·18-35", "M·36-60", "M·61+", "H·18-35", "H·36-60", "H·61+"]
    log("    " + "".join(f"{g}:{B0_sxa[0,a]*100:.0f} " for a, g in enumerate(gnames6)))

    nat_obs = (Y2[:, 0] * T2).sum() / T2.sum()

    # ---- C. H2H por sexo en cada depto (mapa de ganador) ----
    drows = []
    for dep, (name, geo) in DEP.items():
        mask = (meta["dep"] == dep).values
        npu = int(mask.sum())
        if npu < 8:
            drows.append(dict(dep=dep, dep_name=name, geoname=geo, npuestos=npu,
                              robust=0))
            continue
        lam = 0.04 * T2[mask].sum()
        B = fit_qp_reg(Wg[mask], Y2[mask], T2[mask], B0_sex, lam)
        boots = []
        idxall = np.where(mask)[0]
        for _ in range(80):
            idx = idxall[RNG.integers(0, len(idxall), len(idxall))]
            boots.append(fit_qp_reg(Wg[idx], Y2[idx], T2[idx], B0_sex,
                                    0.04 * T2[idx].sum(), iters=1200))
        boots = np.stack(boots)
        cep_m = B[0, 0]*100
        cep_h = B[0, 1]*100
        drows.append(dict(dep=dep, dep_name=name, geoname=geo, npuestos=npu, robust=1,
                          cep_muj=round(cep_m, 1), cep_hom=round(cep_h, 1),
                          cep_muj_lo=round(np.percentile(boots[:, 0, 0], 2.5)*100, 1),
                          cep_muj_hi=round(np.percentile(boots[:, 0, 0], 97.5)*100, 1),
                          gana_muj="Cepeda" if cep_m >= 50 else "Abelardo",
                          gana_hom="Cepeda" if cep_h >= 50 else "Abelardo"))
    pd.DataFrame(drows).to_csv(os.path.join(OUT, "mujeres-h2h-deptos.csv"), index=False)
    flips = [d for d in drows if d.get("robust") and d["gana_muj"] != d["gana_hom"]]
    log(f"\nH2H por sexo en deptos: {sum(1 for d in drows if d.get('robust'))} robustos · "
        f"{len(flips)} cambian de ganador entre mujeres y hombres:")
    for d in flips:
        log(f"   {d['dep_name']:20s} mujeres->{d['gana_muj']:8s} ({d['cep_muj']:.0f}) "
            f"hombres->{d['gana_hom']:8s} ({d['cep_hom']:.0f})")
    J["h2h_deptos"] = drows

    # ---- D. H2H por sexo x edad (3 bandas) nacional + ciudades ----
    CIUDADES = [("Bogotá", "16-001"), ("Medellín", "01-001"), ("Cali", "31-001"),
                ("Barranquilla", "03-001"), ("Cartagena", "05-001"),
                ("Bucaramanga", "27-001")]

    def h2h_unit(mask, B0, nb=120):
        idxall = np.where(mask)[0]
        lam = 0.04 * T2[mask].sum()
        B = fit_qp_reg(W6[mask], Y2[mask], T2[mask], B0, lam)
        boots = []
        for _ in range(nb):
            idx = idxall[RNG.integers(0, len(idxall), len(idxall))]
            boots.append(fit_qp_reg(W6[idx], Y2[idx], T2[idx], B0,
                                    0.04 * T2[idx].sum(), iters=1000))
        boots = np.stack(boots)
        lo = np.percentile(boots, 2.5, axis=0)
        hi = np.percentile(boots, 97.5, axis=0)
        return B, lo, hi

    crows = []
    units = [("Nacional", np.ones(len(T), bool))] + \
            [(n, (meta["mun"] == k).values) for n, k in CIUDADES]
    log("\nH2H Cepeda por sexo x edad (Cepeda % del duelo · mujeres | hombres):")
    log("    " + "ciudad".ljust(13) + "  M18-35 M36-60  M61+  | H18-35 H36-60  H61+")
    for name, mask in units:
        B, lo, hi = h2h_unit(mask, B0_sxa, nb=150 if name == "Nacional" else 100)
        row = dict(unit=name, npuestos=int(mask.sum()))
        for a, g in enumerate(gnames6):
            row[g] = round(B[0, a]*100, 1)
            row[g + "_lo"] = round(lo[0, a]*100, 1)
            row[g + "_hi"] = round(hi[0, a]*100, 1)
        crows.append(row)
        log(f"    {name:13s}" + "  " +
            " ".join(f"{B[0,a]*100:5.0f}" for a in range(3)) + "  | " +
            " ".join(f"{B[0,a]*100:5.0f}" for a in range(3, 6)))
    pd.DataFrame(crows).to_csv(os.path.join(OUT, "mujeres-h2h-ciudades.csv"), index=False)
    J["h2h_sexoedad_ciudades"] = crows

    with open(os.path.join(OUT, "mujeres-ei.json"), "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "mujeres-ei-report.txt"), "w") as f:
        f.write("\n".join(rep))
    log("\nmujeres-ei.json + csv escritos en output_mujeres_1v/")


if __name__ == "__main__":
    main()
