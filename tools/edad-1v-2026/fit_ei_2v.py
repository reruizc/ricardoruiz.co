#!/usr/bin/env python3
"""Inferencia ecológica BINARIA por edad para 2ª vuelta.

Estima el share de la IZQUIERDA (Cepeda 2026 / Petro 2022) dentro del voto
de los dos finalistas, por banda de edad, para tres contiendas comparables:

  2V-2026   Cepeda vs Abelardo   (w proyectado, raking a participación 2V)
  2V-2022   Petro  vs Rodolfo    (w OBSERVADO de Edadygenero P2V-2022)
  1V-2026*  Cepeda vs Abelardo   (cara a cara dentro de la 1V, w 1V existente)

Mismo estimador que fit_ei.py (QP símplex ponderado por estrato región,
bootstrap por conglomerados-municipio, cotas Duncan-Davis). Binario => 2
columnas, sin corner solutions de 6 candidatos.

Salidas en Bases de datos/output_edad_1v/:
  ei-2v-report.txt
  ei-2v-final.csv  (long: contest, grupo, izq_share, lo, hi, dd_lo, dd_hi)
"""
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe_viabilidad import BANDS, load_dane, crosswalk, nrm  # noqa: E402
from fit_ei import (GROUPS, GNAMES, NG, region_of, proj_simplex_cols,  # noqa: E402
                    fit_qp, duncan_davis)
from fit_ei_geo import fit_qp_reg  # noqa: E402  (QP con shrink a prior)

SHRINK_REG = 0.06   # pooling parcial al prior recentrado por región
PRIOR_FLOOR = 0.02  # piso del prior por banda (la EI no distingue 0 de ~2-3%)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "Bases de datos", "output_edad_1v")
RNG = np.random.default_rng(20260628)
B_BOOT = 300
COV_LO, COV_HI = 0.70, 1.10


def group5(raw10):
    """matriz n x 10 (bandas RNEC) -> n x 5 (grupos) en SHARES."""
    g = np.stack([raw10[:, idx].sum(axis=1) for idx in GROUPS.values()], axis=1)
    return g / np.maximum(g.sum(axis=1, keepdims=True), 1e-9)


# ----------------------------------------------- w proyectada 2V-2026 (raking)
def build_w2v26():
    """Rake del perfil 2V-2022 por puesto a la participación 2V-2026 (urna2),
    con tasas de participación por edad de 2V-2022 x DANE 2026. Devuelve dict
    pcode -> (W10 absoluto, seed_level)."""
    e = pd.read_csv(os.path.join(OUT, "edad-2v2022-puesto.csv"), dtype={"pcode": str})
    v22 = pd.read_csv(os.path.join(OUT, "votos-2v2022-puesto.csv"), dtype={"pcode": str})
    v26 = pd.read_csv(os.path.join(OUT, "votos-2v2026-puesto.csv"), dtype={"pcode": str})
    e["dep"] = e["pcode"].str[:2]
    e["mun"] = e["pcode"].str[:6]
    e["zon"] = e["pcode"].str.rsplit("-", n=1).str[0]

    cov = e.merge(v22[["pcode", "total_votos"]], on="pcode", how="left")
    cov["ratio"] = cov["Cantidad de Sufragantes"] / cov["total_votos"].clip(lower=1)
    clean = cov[cov["ratio"].between(COV_LO, COV_HI)]
    prof_p = dict(zip(clean["pcode"], clean[BANDS].values.astype(float)))
    prof_z = e.groupby("zon")[BANDS].sum()
    prof_m = e.groupby("mun")[BANDS].sum()
    prof_d = e.groupby("dep")[BANDS].sum()

    v26 = v26.copy()
    v26["dep"] = v26["pcode"].str[:2]
    v26["mun"] = v26["pcode"].str[:6]
    v26["zon"] = v26["pcode"].str.rsplit("-", n=1).str[0]
    v26["zz"] = v26["pcode"].str.split("-").str[2]
    dom = v26[(v26["dep"] != "88") & (~v26["zz"].isin(["90", "98"]))
              & (v26["total_votos"] > 0)].copy()

    def seed_for(row):
        p = row["pcode"]
        if p in prof_p:
            return prof_p[p], "puesto"
        if row["zon"] in prof_z.index:
            return prof_z.loc[row["zon"]].values, "zona"
        if row["mun"] in prof_m.index:
            return prof_m.loc[row["mun"]].values, "mun"
        if row["dep"] in prof_d.index:
            return prof_d.loc[row["dep"]].values, "dep"
        return None, None

    seeds, levels, keep = [], [], []
    for _, row in dom.iterrows():
        s, lv = seed_for(row)
        if s is None:
            keep.append(False)
            continue
        s = np.asarray(s, float)
        seeds.append(s / max(s.sum(), 1e-9))
        levels.append(lv)
        keep.append(True)
    dom = dom[keep].copy()
    dom["seed_level"] = levels
    S_shape = np.vstack(seeds)
    T26 = dom["total_votos"].values.astype(float)

    dane = load_dane()
    depn = (e[e["depname"] != "Consulados"].groupby("dep")["depname"]
            .agg(lambda s: s.mode()[0]))
    cw = crosswalk(sorted(depn.unique()), set(dane.keys()))
    n22_dep = e.groupby("dep")[BANDS].sum()

    W = np.zeros_like(S_shape)
    for dep, g in dom.groupby("dep"):
        pos = dom.index.get_indexer(g.index)
        t26 = T26[pos]
        dk = cw.get(depn.get(dep, ""), None)
        if dk is None or dep not in n22_dep.index:
            W[pos] = S_shape[pos] * t26[:, None]
            continue
        n22 = n22_dep.loc[dep].values.astype(float)
        N22 = np.array(dane[dk][2022], float)
        N26 = np.array(dane[dk][2026], float)
        rho = n22 / np.maximum(N22, 1.0)
        tgt = rho * N26
        tgt = tgt / tgt.sum() * t26.sum()
        S = S_shape[pos] * t26[:, None]
        for _ in range(120):
            cs = S.sum(axis=0)
            S *= np.where(cs > 0, tgt / np.maximum(cs, 1e-9), 1.0)[None, :]
            rs = S.sum(axis=1)
            S *= (t26 / np.maximum(rs, 1e-9))[:, None]
        W[pos] = S
    wmap = {}
    for i, p in enumerate(dom["pcode"].values):
        wmap[p] = (W[i], dom["seed_level"].values[i], dom["dep"].values[i])
    return wmap, depn


# -------------------------------------------------------------- carga contienda
def load_2v2026(min_votes=200, seed_only=None):
    """seed_only: si se pasa (p.ej. {'puesto'}), restringe a esos niveles de
    semilla — chequeo de robustez frente a puestos nuevos sin perfil 2022."""
    wmap, depn = build_w2v26()
    v = pd.read_csv(os.path.join(OUT, "votos-2v2026-puesto.csv"), dtype={"pcode": str})
    v = v[v["total_dosc"] >= min_votes]
    meta, Wl, Yl, Tl = [], [], [], []
    for _, r in v.iterrows():
        p = r["pcode"]
        if p not in wmap:
            continue
        W10, lv, dep = wmap[p]
        if seed_only is not None and lv not in seed_only:
            continue
        cep, abe = float(r["cepeda"]), float(r["abelardo"])
        t = cep + abe
        meta.append((p, p[:6], region_of(depn.get(dep, ""))))
        Wl.append(W10)
        Yl.append([cep / t, abe / t])
        Tl.append(t)
    return _pack(meta, Wl, Yl, Tl)


def load_2v2022(min_votes=200):
    e = pd.read_csv(os.path.join(OUT, "edad-2v2022-puesto.csv"), dtype={"pcode": str})
    v = pd.read_csv(os.path.join(OUT, "votos-2v2022-puesto.csv"), dtype={"pcode": str})
    m = e.merge(v, on="pcode")
    m["ratio"] = m["Cantidad de Sufragantes"] / m["total_votos"].clip(lower=1)
    m = m[m["ratio"].between(COV_LO, COV_HI) & (m["total_dosc"] >= min_votes)]
    meta, Wl, Yl, Tl = [], [], [], []
    for _, r in m.iterrows():
        W10 = np.array([r[b] for b in BANDS], float)
        p, ro = float(r["petro"]), float(r["rodolfo"])
        t = p + ro
        meta.append((r["pcode"], r["pcode"][:6], region_of(r["depname"])))
        Wl.append(W10)
        Yl.append([p / t, ro / t])
        Tl.append(t)
    return _pack(meta, Wl, Yl, Tl)


def load_1v2026_h2h(min_votes=200):
    """Cara a cara Cepeda vs Abelardo DENTRO de la 1V (w 1V existente)."""
    w = pd.read_csv(os.path.join(OUT, "w26-puesto.csv"), dtype={"pcode": str})
    v = pd.read_csv(os.path.join(OUT, "votos-2026-puesto.csv"), dtype={"pcode": str})
    e = pd.read_csv(os.path.join(OUT, "edad-2022-puesto.csv"), dtype={"pcode": str})
    dep2name = (e.assign(dep=e["pcode"].str[:2]).groupby("dep")["depname"]
                .agg(lambda s: s.mode()[0]))
    m = w.merge(v, on="pcode", suffixes=("", "_v"))
    m["t"] = m["cepeda"] + m["abelardo"]
    m = m[m["t"] >= min_votes]
    meta, Wl, Yl, Tl = [], [], [], []
    for _, r in m.iterrows():
        W10 = np.array([r[f"b{b}"] for b in range(10)], float)
        cep, abe = float(r["cepeda"]), float(r["abelardo"])
        t = cep + abe
        dep = r["pcode"][:2]
        meta.append((r["pcode"], r["pcode"][:6], region_of(dep2name.get(dep, ""))))
        Wl.append(W10)
        Yl.append([cep / t, abe / t])
        Tl.append(t)
    return _pack(meta, Wl, Yl, Tl)


def _pack(meta, Wl, Yl, Tl):
    md = pd.DataFrame(meta, columns=["pcode", "mun", "stratum"])
    W = group5(np.vstack(Wl))
    Y = np.array(Yl, float)
    T = np.array(Tl, float)
    return md, W, Y, T


# ------------------------------------------------------------------ agregación
def fit_national(meta, W, Y, T):
    Bs, Ms = {}, {}
    for s in sorted(meta["stratum"].unique()):
        sel = (meta["stratum"] == s).values
        Bs[s] = fit_qp(W[sel], Y[sel], T[sel])
        Ms[s] = (W[sel] * T[sel, None]).sum(axis=0)
    Mtot = sum(Ms.values())
    Bn = sum(Bs[s] * (Ms[s] / Mtot)[None, :] for s in Bs)
    return Bn, Mtot, Bs, Ms


def bootstrap(meta, W, Y, T, B=B_BOOT, regional=False):
    muns = meta.groupby(["stratum", "mun"]).indices
    by_s = defaultdict(list)
    for (s, mn), idx in muns.items():
        by_s[s].append(np.asarray(idx))
    strata = sorted(by_s)
    out = []
    reg = {s: [] for s in strata}      # share izq por banda en cada estrato
    for _ in range(B):
        Bs, Ms = {}, {}
        for s, blocks in by_s.items():
            pick = RNG.integers(0, len(blocks), len(blocks))
            idx = np.concatenate([blocks[i] for i in pick])
            Bs[s] = fit_qp(W[idx], Y[idx], T[idx], iters=1500)
            Ms[s] = (W[idx] * T[idx, None]).sum(axis=0)
            if regional:
                reg[s].append(Bs[s][0])     # fila 0 = izquierda
        Mtot = sum(Ms.values())
        out.append(sum(Bs[s] * (Ms[s] / Mtot)[None, :] for s in Bs))
    if regional:
        return np.stack(out), {s: np.stack(v) for s, v in reg.items()}
    return np.stack(out)


# ------------------------------------------------------------------- report
REGION_LABEL = {
    "CARIBE": "Caribe", "ANT-EJE": "Antioquia + Eje", "PACIFICO": "Pacífico",
    "CEN-ORIENTE": "Centro-Oriente", "SUR": "Sur (Tolima-Huila-Amazonía)",
    "LLANOS": "Llanos-Orinoquía", "BOGOTA": "Bogotá",
}
REGION_ORDER = ["BOGOTA", "ANT-EJE", "CARIBE", "PACIFICO", "CEN-ORIENTE",
                "SUR", "LLANOS"]


def run(contest, izqname, dername, loader, report, rows, regrows=None):
    meta, W, Y, T = loader()
    Bn, M, Bs, Ms = fit_national(meta, W, Y, T)
    dd_lo, dd_hi = duncan_davis(W, Y, T)
    boots = bootstrap(meta, W, Y, T)
    lo = np.percentile(boots, 2.5, axis=0)
    hi = np.percentile(boots, 97.5, axis=0)
    Wsh = M / M.sum()

    report.append(f"\n{'='*78}\n{contest} · {izqname} vs {dername} · "
                  f"{len(meta):,} puestos · {T.sum():,.0f} votos 2-cand en muestra\n{'='*78}")
    report.append("peso de cada grupo etario: " +
                  "  ".join(f"{g}:{Wsh[a]*100:.1f}%" for a, g in enumerate(GNAMES)))
    report.append(f"\n% del voto 2-candidatos que va a {izqname} (IZQUIERDA), "
                  "por grupo · punto (IC95) [cota dura DD]:")
    head = "         " + "".join(f"{g:>23s}" for g in GNAMES)
    report.append(head)
    cells = []
    for a in range(NG):
        cells.append(f"{Bn[0,a]*100:5.1f} ({lo[0,a]*100:4.1f}-{hi[0,a]*100:4.1f})"
                     f"[{dd_lo[0,a]*100:2.0f}-{dd_hi[0,a]*100:3.0f}]")
    report.append(f"  {izqname:7s}" + "  ".join(cells))
    gap = (Bn[0, 0] - Bn[0, NG - 1]) * 100
    report.append(f"\n  >> brecha generacional (18-25 menos 61+): {gap:+.1f} pp")

    # consistencia
    impl = (Bn @ Wsh)[0]
    obs = (Y[:, 0] * T).sum() / T.sum()
    report.append(f"  consistencia nacional {izqname}: implícito {impl*100:.1f}% / "
                  f"observado {obs*100:.1f}%")

    # composición etaria del electorado de cada lado
    for c, name in ((0, izqname), (1, dername)):
        gam = Bn[c] * Wsh
        gam = gam / gam.sum()
        report.append(f"  electorado {name:8s} por edad: " +
                      " ".join(f"{g}:{gam[a]*100:.0f}%" for a, g in enumerate(GNAMES)))
        rows_share = gam
    for a in range(NG):
        rows.append(dict(contest=contest, izq=izqname, grupo=GNAMES[a],
                         izq_share=Bn[0, a], lo=lo[0, a], hi=hi[0, a],
                         dd_lo=dd_lo[0, a], dd_hi=dd_hi[0, a],
                         peso_grupo=Wsh[a]))

    # ----------------------------------------------------- desglose regional
    # Estimador REGULARIZADO: shrink a un prior nacional RECENTRADO al resultado
    # global de cada región (swing uniforme sobre el patrón etario nacional).
    # Evita el sesgo de frontera del QP-símplex (61+ clavado en 0% exacto) sin
    # imponer el patrón de otra región. Mismo enfoque que fit_ei_geo (deptos).
    nat_obs = (Y[:, 0] * T).sum() / T.sum()
    report.append(f"\n  --- por REGIÓN ({izqname} = izquierda) · regularizado "
                  "(shrink a prior recentrado) ---")
    report.append("    región                      18-25  26-35  36-45  46-60   61+   "
                  "brecha(IC)        global/obs")
    for s in REGION_ORDER:
        if s not in Bs:
            continue
        sel = (meta["stratum"] == s).values
        Ws, Ys, Ts = W[sel], Y[sel], T[sel]
        obs = (Ys[:, 0] * Ts).sum() / Ts.sum()
        B0r = Bn.copy()
        B0r[0] = np.clip(Bn[0] + (obs - nat_obs), PRIOR_FLOOR, 1 - PRIOR_FLOOR)
        B0r[1] = 1 - B0r[0]
        lam = SHRINK_REG * Ts.sum()
        Br = fit_qp_reg(Ws, Ys, Ts, B0r, lam)
        b = Br[0]
        wsh = (Ws * Ts[:, None]).sum(axis=0)
        wsh = wsh / wsh.sum()
        glob = float(b @ wsh)
        # bootstrap regularizado por municipios (conglomerados)
        blocks = [np.asarray(idx) for idx in
                  meta[sel].groupby("mun").groups.values()]
        gboot = []
        for _ in range(150):
            pick = RNG.integers(0, len(blocks), len(blocks))
            ix = np.concatenate([blocks[i] for i in pick])
            Bb = fit_qp_reg(W[ix], Y[ix], T[ix], B0r, SHRINK_REG * T[ix].sum(),
                            iters=1200)
            gboot.append((Bb[0, 0] - Bb[0, NG - 1]) * 100)
        glo, ghi = np.percentile(gboot, 2.5), np.percentile(gboot, 97.5)
        gap_s = (b[0] - b[NG - 1]) * 100
        report.append(
            f"    {REGION_LABEL[s]:24s}  " +
            "".join(f"{b[a]*100:5.0f}  " for a in range(NG)) +
            f"{gap_s:+5.0f}({glo:+.0f}/{ghi:+.0f})  {glob*100:4.1f}/{obs*100:4.1f}%")
        if regrows is not None:
            for a in range(NG):
                regrows.append(dict(contest=contest, izq=izqname,
                                    region=REGION_LABEL[s], grupo=GNAMES[a],
                                    izq_share=b[a], peso_grupo=float(wsh[a]),
                                    global_izq=glob, obs_izq=float(obs),
                                    gap=gap_s, gap_lo=glo, gap_hi=ghi))
    return Bn[0], gap


def main():
    report, rows, regrows = [], [], []
    report.append("INFERENCIA ECOLÓGICA BINARIA POR EDAD · 2ª VUELTA")
    report.append("Estima el share de la IZQUIERDA entre los dos finalistas, "
                  "por grupo etario.")
    r26, g26 = run("2V-2026", "Cepeda", "Abelardo", load_2v2026, report, rows, regrows)
    r22, g22 = run("2V-2022", "Petro", "Rodolfo", load_2v2022, report, rows, regrows)
    r1v, g1v = run("1V-2026 (cara a cara)", "Cepeda", "Abelardo",
                   load_1v2026_h2h, report, rows, regrows)

    report.append(f"\n{'='*78}\nSÍNTESIS · brecha generacional (share izq 18-25 − 61+)\n{'='*78}")
    report.append(f"  2V-2026 Cepeda-Abelardo : {g26:+5.1f} pp")
    report.append(f"  1V-2026 Cepeda-Abelardo : {g1v:+5.1f} pp  (cara a cara dentro de 1V)")
    report.append(f"  2V-2022 Petro-Rodolfo   : {g22:+5.1f} pp")
    report.append("\n  perfil izquierda por grupo (18-25 / 26-35 / 36-45 / 46-60 / 61+):")
    report.append(f"   2V-2026: " + " ".join(f"{x*100:4.0f}" for x in r26))
    report.append(f"   1V-2026: " + " ".join(f"{x*100:4.0f}" for x in r1v))
    report.append(f"   2V-2022: " + " ".join(f"{x*100:4.0f}" for x in r22))

    # ---------- ROBUSTEZ: ¿los puestos nuevos (semilla de fallback) sesgan? ----
    report.append(f"\n{'='*78}\nROBUSTEZ · 2V-2026 con SOLO semilla directa de puesto "
                  "(63.7% del voto, sin\npuestos nuevos proyectados por zona/mun)\n{'='*78}")
    meta, W, Y, T = load_2v2026(seed_only={"puesto"})
    Bn, M, Bs, Ms = fit_national(meta, W, Y, T)
    report.append(f"  muestra: {len(meta):,} puestos · {T.sum():,.0f} votos 2-cand")
    report.append("  Cepeda por grupo (solo puesto): " +
                  " ".join(f"{Bn[0,a]*100:4.0f}" for a in range(NG)) +
                  f"   brecha {(Bn[0,0]-Bn[0,NG-1])*100:+.1f}pp")
    report.append("  Cepeda por grupo (todo, ref) :  " +
                  " ".join(f"{x*100:4.0f}" for x in r26) +
                  f"   brecha {g26:+.1f}pp")

    pd.DataFrame(rows).to_csv(os.path.join(OUT, "ei-2v-final.csv"), index=False)
    pd.DataFrame(regrows).to_csv(os.path.join(OUT, "ei-2v-regional.csv"), index=False)
    txt = "\n".join(report)
    with open(os.path.join(OUT, "ei-2v-report.txt"), "w") as f:
        f.write(txt)
    print(txt)


if __name__ == "__main__":
    main()
