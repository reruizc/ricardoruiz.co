#!/usr/bin/env python3
"""Paso 1+2 del análisis de voto FEMENINO 1V-2026.

Hermano del pipeline de edad (tools/edad-1v-2026). Construye:

  gen-2018-puesto.csv / gen-2022-puesto.csv
     sufragantes por puesto desglosados en sexo x banda etaria (20 celdas:
     H_b0..H_b9, M_b0..M_b9) + totales H/M. Re-agrega desde el caché de
     Edadygenero (cache/p1v-{year}.csv) con el fix Bogotá-localidad.

  w26-gen-puesto.csv
     composición sexo x edad PROYECTADA de los votantes 2026 por puesto.
     Mismo método del modelo de edad: tasas de participación sexo x banda
     2022 a nivel depto x DANE 2026 -> márgenes; raking IPF sobre la matriz
     puesto x (20 celdas) sembrada con el perfil 2022 del puesto (gate de
     calidad cov in [0.70,1.10]; fallback zona -> mun -> dep).
     Columnas: pcode, dep, seed_level, total_votos, H0..H9, M0..M9.

Reutiliza helpers de tools/edad-1v-2026/probe_viabilidad.py.
"""
import os
import re
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

EDAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "edad-1v-2026")
sys.path.insert(0, os.path.abspath(EDAD))
from probe_viabilidad import BANDS, BOG_LOC, nrm, zf  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..", "..", "Bases de datos")
EOUT = os.path.join(BASE, "output_edad_1v")          # csvs de votos ya hechos
OUT = os.path.join(BASE, "output_mujeres_1v")
CACHE = os.path.join(EOUT, "cache")

COV_LO, COV_HI = 0.70, 1.10

# columnas sexo x banda en el caché de Edadygenero
HBANDS = ["Hombres entre 18 a 20 años", "Hombres entre 21 a 25 años",
          "Hombres entre 26 a 30 años", "Hombres entre 31 a 35 años",
          "Hombres entre 36 a 40 años", "Hombres entre 41 a 45 años",
          "Hombres entre 46 a 50 años", "Hombres entre 51 a 55 años",
          "Hombres entre 56 a 60 años", "Hombres Mayores a 60 años"]
MBANDS = ["Mujeres entre 18 a 20 años", "Mujeres entre 21 a 25 años",
          "Mujeres entre 26 a 30 años", "Mujeres entre 31 a 35 años",
          "Mujeres entre 36 a 40 años", "Mujeres entre 41 a 45 años",
          "Mujeres entre 46 a 50 años", "Mujeres entre 51 a 55 años",
          "Mujeres entre 56 a 60 años", "Mujeres mayores a 60 años"]
HCOLS = [f"H{b}" for b in range(10)]
MCOLS = [f"M{b}" for b in range(10)]
CELLS = HCOLS + MCOLS                                 # 20 celdas, orden fijo


# ---------------------------------------------------------------- edadygenero
def gen_puesto(year):
    df = pd.read_csv(os.path.join(CACHE, f"p1v-{year}.csv"), dtype=str)
    num_cols = ["Cantidad de Sufragantes", "Cantidad Hombres",
                "Cantidad de Mujeres"] + HBANDS + MBANDS
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    def zona(row):
        z = str(row["Cód. Comuna / Localidad"]).strip()
        if not z.isdigit():
            return BOG_LOC.get(nrm(z), z)
        return zf(z, 2)

    df["pcode"] = (df["Cód. Depto"].map(lambda v: zf(v, 2)) + "-" +
                   df["Cód. Municipio"].map(lambda v: zf(v, 3)) + "-" +
                   df.apply(zona, axis=1) + "-" +
                   df["Cód. Puesto de Votación"].map(lambda v: zf(v, 2)))
    df["depname"] = df["Estadosnoborrar"]
    g = df.groupby(["pcode", "depname"], as_index=False)[num_cols].sum()
    # renombra a celdas cortas
    g = g.rename(columns={h: f"H{i}" for i, h in enumerate(HBANDS)})
    g = g.rename(columns={m: f"M{i}" for i, m in enumerate(MBANDS)})
    os.makedirs(OUT, exist_ok=True)
    g.to_csv(os.path.join(OUT, f"gen-{year}-puesto.csv"), index=False)
    h, m = g["Cantidad Hombres"].sum(), g["Cantidad de Mujeres"].sum()
    print(f"gen-{year}-puesto.csv: {len(g):,} puestos · H={h:,} M={m:,} "
          f"· mujeres={m/(h+m)*100:.2f}%")
    return g


# ---------------------------------------------------------------- DANE sexo x edad
def load_dane_sexage(years=(2018, 2022, 2026)):
    """-> {dpnom_norm: {year: np.array (2,10)}}  fila 0=Hombres, 1=Mujeres."""
    import openpyxl
    wb = openpyxl.load_workbook(
        os.path.join(BASE, "DANE-AreaSexoEdadDep-2018-2050_VP.xlsx"),
        read_only=True, data_only=True)
    ws = wb["PobDepartamentalxÁreaSexoEdad"]
    rows = ws.iter_rows(min_row=8, values_only=True)
    h8 = next(rows)
    h9 = next(rows)
    labels = [h8[i] if i < 4 else h9[i] for i in range(len(h9))]
    age_cols = []                                     # (idx, sexo_idx, edad)
    for i, lab in enumerate(labels):
        if lab is None:
            continue
        mt = re.match(r"^(Hombres|Mujeres)\s+(\d+|100)", str(lab))
        if mt and ("año" in str(lab)):
            sx = 0 if mt.group(1) == "Hombres" else 1
            age_cols.append((i, sx, int(mt.group(2))))

    def band_of(a):
        if a < 18:
            return None
        return min((a - 16) // 5, 9) if a <= 60 else 9
    # 18-20->0,21-25->1,...56-60->8,61+->9
    def band(a):
        if a < 18: return None
        if a <= 20: return 0
        if a <= 25: return 1
        if a <= 30: return 2
        if a <= 35: return 3
        if a <= 40: return 4
        if a <= 45: return 5
        if a <= 50: return 6
        if a <= 55: return 7
        if a <= 60: return 8
        return 9

    dane = defaultdict(lambda: defaultdict(lambda: np.zeros((2, 10))))
    for row in rows:
        if row[0] is None:
            continue
        try:
            anio = int(row[2])
        except (TypeError, ValueError):
            continue
        if anio not in years or str(row[3]).strip() != "Total":
            continue
        key = nrm(row[1])
        for i, sx, edad in age_cols:
            b = band(edad)
            if b is None or row[i] is None:
                continue
            dane[key][anio][sx, b] += float(row[i])
    wb.close()
    return dane


def crosswalk(depnames_rnec, dane_keys):
    cw = {}
    for dn in depnames_rnec:
        n = nrm(dn)
        if n in dane_keys:
            cw[dn] = n
            continue
        hit = [k for k in dane_keys if n in k or k in n]
        if len(hit) == 1:
            cw[dn] = hit[0]
        else:
            if "SAN ANDRES" in n:
                hit = [k for k in dane_keys if "SAN ANDRES" in k]
            elif "BOGOTA" in n:
                hit = [k for k in dane_keys if "BOGOTA" in k]
            elif "VALLE" in n:
                hit = [k for k in dane_keys if "VALLE DEL CAUCA" in k]
            cw[dn] = hit[0] if hit else None
    return cw


# ---------------------------------------------------------------- proyección 2026
def build_w26(g22):
    v22 = pd.read_csv(os.path.join(EOUT, "votos-2022-puesto.csv"), dtype={"pcode": str})
    v26 = pd.read_csv(os.path.join(EOUT, "votos-2026-puesto.csv"), dtype={"pcode": str})

    g22 = g22.copy()
    g22["dep"] = g22["pcode"].str[:2]
    g22["mun"] = g22["pcode"].str[:6]
    g22["zon"] = g22["pcode"].str.rsplit("-", n=1).str[0]

    # gate de calidad sobre el perfil 2022 (mismo de edad)
    cov = g22.merge(v22[["pcode", "total_votos"]], on="pcode", how="left")
    cov["ratio"] = cov["Cantidad de Sufragantes"] / cov["total_votos"].clip(lower=1)
    clean = cov[cov["ratio"].between(COV_LO, COV_HI)].copy()
    print(f"perfiles 2022 limpios (sexo x edad): {len(clean):,}/{len(g22):,} puestos")

    prof_puesto = {p: v for p, v in zip(clean["pcode"], clean[CELLS].values.astype(float))}
    prof_zona = g22.groupby("zon")[CELLS].sum()
    prof_mun = g22.groupby("mun")[CELLS].sum()
    prof_dep = g22.groupby("dep")[CELLS].sum()

    v26["dep"] = v26["pcode"].str[:2]
    v26["mun"] = v26["pcode"].str[:6]
    v26["zon"] = v26["pcode"].str.rsplit("-", n=1).str[0]
    v26["zz"] = v26["pcode"].str.split("-").str[2]
    dom = v26[(v26["dep"] != "88") & (~v26["zz"].isin(["90", "98"]))].copy()
    print(f"puestos 2026 domésticos: {len(dom):,} · {dom['total_votos'].sum():,} votos")

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
    S_shape = np.vstack(seeds)                        # n x 20
    for lv in ("puesto", "zona", "mun", "dep"):
        sel = dom["seed_level"] == lv
        print(f"   semilla {lv:7s} {sel.sum():6,} puestos · "
              f"{dom.loc[sel,'total_votos'].sum()/dom['total_votos'].sum()*100:5.1f}%")

    # márgenes sexo x edad por depto: rho(2022) x N(DANE 2026)
    dane = load_dane_sexage()
    dep_names = (g22[g22["depname"] != "Consulados"]
                 .groupby("dep")["depname"].agg(lambda s: s.mode()[0]))
    cw = crosswalk(sorted(dep_names.unique()), set(dane.keys()))

    n22_dep = g22.groupby("dep")[CELLS].sum()          # sufragantes sexo x edad 2022
    T26 = dom["total_votos"].values.astype(float)
    W = np.zeros_like(S_shape)
    for dep, grp in dom.groupby("dep"):
        pos = dom.index.get_indexer(grp.index)
        t26 = T26[pos]
        dk = cw.get(dep_names.get(dep, ""), None)
        if dk is None or dep not in n22_dep.index:
            W[pos] = S_shape[pos] * t26[:, None]
            continue
        n22 = n22_dep.loc[dep].values.astype(float).reshape(2, 10)   # H rows, M rows
        # CELLS = H0..H9, M0..M9 -> reshape(2,10): fila0=H, fila1=M (coincide)
        N22 = dane[dk][2022]
        N26 = dane[dk][2026]
        rho = n22 / np.maximum(N22, 1.0)
        tgt = (rho * N26).reshape(-1)                  # 20 celdas
        tgt = tgt / tgt.sum() * t26.sum()              # nivel = dato real 2026
        S = S_shape[pos] * t26[:, None]
        for _ in range(150):
            cs = S.sum(axis=0)
            S *= np.where(cs > 0, tgt / np.maximum(cs, 1e-9), 1.0)[None, :]
            rs = S.sum(axis=1)
            S *= (t26 / np.maximum(rs, 1e-9))[:, None]
        W[pos] = S

    out = dom[["pcode", "dep", "seed_level", "total_votos"]].copy()
    for i, c in enumerate(CELLS):
        out[c] = W[:, i]
    out.to_csv(os.path.join(OUT, "w26-gen-puesto.csv"), index=False)

    # control nacional
    sh_h = W[:, :10].sum() / W.sum()
    sh_m = W[:, 10:].sum() / W.sum()
    obs_m = g22["Cantidad de Mujeres"].sum() / (
        g22["Cantidad de Mujeres"].sum() + g22["Cantidad Hombres"].sum())
    print(f"\nshare nacional de votantes proyectado 2026: "
          f"Mujeres {sh_m*100:.2f}% · Hombres {sh_h*100:.2f}% "
          f"(obs 2022: mujeres {obs_m*100:.2f}%)")
    print(f"w26-gen-puesto.csv: {len(out):,} puestos · "
          f"{out['total_votos'].sum():,.0f} votos proyectados")


def main():
    print("== EdadyGénero -> puesto (sexo x banda) ==")
    gen_puesto(2018)
    g22 = gen_puesto(2022)
    print("\n== Proyección sexo x edad 2026 (IPF + DANE) ==")
    build_w26(g22)


if __name__ == "__main__":
    main()
