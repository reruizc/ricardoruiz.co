#!/usr/bin/env python3
"""Paso 2 del modelo: composición etaria PROYECTADA de los votantes 2026
por puesto (w26), consistente con (a) el perfil local 2022, (b) la deriva
demográfica DANE 2022->2026 por depto, y (c) los votantes reales 2026 por
puesto (preconteo).

Método: tasas de participación por edad 2022 a nivel depto aplicadas a la
población DANE 2026 -> márgenes etarios por depto; raking IPF sobre la matriz
puesto x banda sembrada con el perfil 2022 del puesto (gate de calidad
cov∈[0.70,1.10]; fallback zona -> municipio -> depto).

Salida: Bases de datos/output_edad_1v/w26-puesto.csv
   pcode, dep, seed_level, total_votos, b0..b9 (votantes proyectados por banda)
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe_viabilidad import BANDS, load_dane, crosswalk, nrm  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "Bases de datos", "output_edad_1v")

COV_LO, COV_HI = 0.70, 1.10


def main():
    e22 = pd.read_csv(os.path.join(OUT, "edad-2022-puesto.csv"), dtype={"pcode": str})
    v22 = pd.read_csv(os.path.join(OUT, "votos-2022-puesto.csv"), dtype={"pcode": str})
    v26 = pd.read_csv(os.path.join(OUT, "votos-2026-puesto.csv"), dtype={"pcode": str})

    e22["dep"] = e22["pcode"].str[:2]
    e22["mun"] = e22["pcode"].str[:6]
    e22["zon"] = e22["pcode"].str.rsplit("-", n=1).str[0]

    # ---------- gate de calidad sobre el perfil 2022 ----------
    cov = e22.merge(v22[["pcode", "total_votos"]], on="pcode", how="left")
    cov["ratio"] = cov["Cantidad de Sufragantes"] / cov["total_votos"].clip(lower=1)
    clean = cov[cov["ratio"].between(COV_LO, COV_HI)].copy()
    print(f"perfiles 2022 limpios: {len(clean):,}/{len(e22):,} puestos")

    band_mat = clean[BANDS].values.astype(float)
    prof_puesto = dict(zip(clean["pcode"], band_mat))
    # agregados con TODOS los datos (las reasignaciones de mesa entre puestos
    # vecinos se cancelan al agregar; el gate solo aplica a la semilla directa)
    prof_zona = e22.groupby("zon")[BANDS].sum()
    prof_mun = e22.groupby("mun")[BANDS].sum()
    prof_dep = e22.groupby("dep")[BANDS].sum()

    # ---------- universo 2026 doméstico ----------
    v26["dep"] = v26["pcode"].str[:2]
    v26["mun"] = v26["pcode"].str[:6]
    v26["zon"] = v26["pcode"].str.rsplit("-", n=1).str[0]
    v26["zz"] = v26["pcode"].str.split("-").str[2]
    dom = v26[(v26["dep"] != "88") & (~v26["zz"].isin(["90", "98"]))].copy()
    print(f"puestos 2026 domésticos: {len(dom):,} · "
          f"{dom['total_votos'].sum():,} votos")

    def seed_for(row):
        p = row["pcode"]
        if p in prof_puesto:
            return prof_puesto[p], "puesto"
        if row["zon"] in prof_zona.index:
            return prof_zona.loc[row["zon"]].values, "zona"
        if row["mun"] in prof_mun.index:
            return prof_mun.loc[row["mun"]].values, "mun"
        return prof_dep.loc[row["dep"]].values, "dep"

    seeds, levels = [], []
    for _, row in dom.iterrows():
        s, lv = seed_for(row)
        s = np.asarray(s, dtype=float)
        seeds.append(s / max(s.sum(), 1e-9))
        levels.append(lv)
    dom["seed_level"] = levels
    S_shape = np.vstack(seeds)                       # n x 10 (shares semilla)
    print("nivel de semilla (% de votos 2026):")
    for lv in ("puesto", "zona", "mun", "dep"):
        sel = dom["seed_level"] == lv
        print(f"   {lv:7s} {sel.sum():6,} puestos · "
              f"{dom.loc[sel,'total_votos'].sum()/dom['total_votos'].sum()*100:5.1f}%")

    # ---------- márgenes etarios por depto: rho_a(2022) x N_a(DANE 2026) ----------
    dane = load_dane()
    dep_names = (e22[e22["depname"] != "Consulados"]
                 .groupby("dep")["depname"].agg(lambda s: s.mode()[0]))
    cw = crosswalk(sorted(dep_names.unique()), set(dane.keys()))

    n22_dep = e22.groupby("dep")[BANDS].sum()        # sufragantes 2022 por banda
    T26 = dom["total_votos"].values.astype(float)

    W = np.zeros_like(S_shape)
    for dep, g in dom.groupby("dep"):
        idx = g.index
        pos = dom.index.get_indexer(idx)
        dk = cw.get(dep_names.get(dep, ""), None)
        t26 = T26[pos]
        if dk is None or dep not in n22_dep.index:
            # sin DANE (no debería pasar en doméstico): semilla sin re-ponderar
            W[pos] = S_shape[pos] * t26[:, None]
            continue
        n22 = n22_dep.loc[dep].values.astype(float)
        N22 = np.array(dane[dk][2022], dtype=float)
        N26 = np.array(dane[dk][2026], dtype=float)
        rho = n22 / np.maximum(N22, 1.0)
        tgt = rho * N26                              # votantes esperados por banda
        tgt = tgt / tgt.sum() * t26.sum()            # kappa: nivel = dato real
        # IPF: filas = puestos (margen t26), columnas = bandas (margen tgt)
        S = S_shape[pos] * t26[:, None]
        for _ in range(120):
            cs = S.sum(axis=0)
            S *= np.where(cs > 0, tgt / np.maximum(cs, 1e-9), 1.0)[None, :]
            rs = S.sum(axis=1)
            S *= (t26 / np.maximum(rs, 1e-9))[:, None]
        W[pos] = S

    out = dom[["pcode", "dep", "seed_level", "total_votos"]].copy()
    for b in range(10):
        out[f"b{b}"] = W[:, b]
    out.to_csv(os.path.join(OUT, "w26-puesto.csv"), index=False)

    # control nacional
    sh26 = W.sum(axis=0) / W.sum()
    sh22 = e22[BANDS].sum().values / e22[BANDS].sum().sum()
    print("\nshare nacional de votantes por banda (proyección 2026 vs obs 2022):")
    SHORT = ["18-20", "21-25", "26-30", "31-35", "36-40",
             "41-45", "46-50", "51-55", "56-60", "61+"]
    for b in range(10):
        print(f"   {SHORT[b]:6s} {sh26[b]*100:5.2f}  (2022: {sh22[b]*100:5.2f})")
    print(f"\nw26-puesto.csv: {len(out):,} puestos · "
          f"{out['total_votos'].sum():,} votos proyectados")


if __name__ == "__main__":
    main()
