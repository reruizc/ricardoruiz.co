#!/usr/bin/env python3
"""Paso 3 · composición de votantes por sexo × grupo de edad (10 celdas).

2022 OBSERVADO:  agrega Edadygenero (mesa) -> mesa / puesto / municipio.
2026 PROYECTADO: tasas de participación por celda 2022 (sufragantes/DANE2022)
                 aplicadas a DANE 2026; raking IPF de los perfiles de puesto
                 2022 a (col=celdas dep 2026, fila=votantes reales 2026/puesto).

Salidas en output_cundi_edad_genero/:
  comp-2022-mesa.csv · comp-2022-puesto.csv · comp-2022-mun.csv
  comp-2026-puesto.csv · comp-2026-mun.csv
"""
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (OUT, CELL_LABELS, H_COLS, M_COLS, H_INDEF, M_INDEF,
                    BAND_TO_GROUP, load_dane_sexedad, mesa_key)

COV_LO, COV_HI = 0.70, 1.10


def _mesa_cells(row):
    """Fila de Edadygenero -> vector de 10 celdas (H/M × 5 grupos), con
    indefinidos de edad/sexo distribuidos. Suma = sufragantes."""
    H = np.array([float(row[c] or 0) for c in H_COLS])   # 10 bandas
    M = np.array([float(row[c] or 0) for c in M_COLS])
    h_ai = float(row[H_INDEF] or 0)     # edad indefinida, sexo H
    m_ai = float(row[M_INDEF] or 0)
    full_indef = float(row["Cantidad de Indefinidos"] or 0)  # sexo indefinido
    # reparte edad-indefinida dentro del sexo ∝ a su perfil etario
    if H.sum() > 0:
        H = H + h_ai * H / H.sum()
    elif h_ai:
        H = H + h_ai / 10
    if M.sum() > 0:
        M = M + m_ai * M / M.sum()
    elif m_ai:
        M = M + m_ai / 10
    # reparte sexo-indefinido ∝ a la mezcla observada H+M
    tot = H.sum() + M.sum()
    if full_indef and tot > 0:
        H = H + full_indef * H.sum() / tot * (H / max(H.sum(), 1e-9))
        M = M + full_indef * M.sum() / tot * (M / max(M.sum(), 1e-9))
    # colapsa 10 bandas -> 5 grupos
    cells = np.zeros(10)
    for b in range(10):
        cells[BAND_TO_GROUP[b]] += H[b]          # H-grupo (idx 0..4)
        cells[5 + BAND_TO_GROUP[b]] += M[b]       # M-grupo (idx 5..9)
    return cells


def build_2022():
    df = pd.read_csv(os.path.join(OUT, "edad-congreso-2022-cundi.csv"), dtype=str)
    numcols = ["Cantidad de Sufragantes", "Cantidad de Indefinidos",
               H_INDEF, M_INDEF] + H_COLS + M_COLS
    for c in numcols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    rows = []
    indef_total = 0.0
    suf_total = 0.0
    for _, r in df.iterrows():
        key = mesa_key(r["Cód. Depto"], r["Cód. Municipio"],
                       r["Cód. Comuna / Localidad"],
                       r["Cód. Puesto de Votación"], r["Mesa"])
        cells = _mesa_cells(r)
        mun = key[:6]
        pue = "-".join(key.split("-")[:4])
        rows.append((key, mun, pue, *cells))
        indef_total += (float(r["Cantidad de Indefinidos"]) +
                        float(r[H_INDEF]) + float(r[M_INDEF]))
        suf_total += float(r["Cantidad de Sufragantes"])
    cols = ["mesa", "mun", "puesto"] + CELL_LABELS
    m = pd.DataFrame(rows, columns=cols)
    m.to_csv(os.path.join(OUT, "comp-2022-mesa.csv"), index=False)

    pue = m.groupby(["puesto", "mun"], as_index=False)[CELL_LABELS].sum()
    pue.to_csv(os.path.join(OUT, "comp-2022-puesto.csv"), index=False)
    mun = m.groupby("mun", as_index=False)[CELL_LABELS].sum()
    mun.to_csv(os.path.join(OUT, "comp-2022-mun.csv"), index=False)

    print(f"2022: {len(m):,} mesas · {len(pue):,} puestos · {len(mun)} munis")
    print(f"   sufragantes={suf_total:,.0f} · indefinidos repartidos="
          f"{indef_total:,.0f} ({indef_total/suf_total*100:.2f}%)")
    sh = m[CELL_LABELS].sum() / m[CELL_LABELS].sum().sum() * 100
    print("   share dep por celda (%): " +
          " ".join(f"{l}:{sh[l]:.1f}" for l in CELL_LABELS))
    return m, pue, mun


def build_2026(pue22):
    # universo 2026 por puesto: usa el total Senado como proxy de sufragantes
    v26 = pd.read_csv(os.path.join(OUT, "votos-2026-cundi-puesto.csv"), dtype=str)
    v26["votos"] = pd.to_numeric(v26["votos"], errors="coerce").fillna(0)
    turn = (v26[v26["corp"] == "SENADO"].groupby("key")["votos"].sum()
            .rename("turnout").reset_index())
    turn["mun"] = turn["key"].str[:6]
    print(f"\n2026: {len(turn):,} puestos con votación Senado · "
          f"{turn['turnout'].sum():,.0f} votantes (proxy)")

    # perfiles semilla 2022 por puesto / zona / mun / dep
    pue22 = pue22.copy()
    pue22["zona"] = pue22["puesto"].str.rsplit("-", n=1).str[0]
    prof_puesto = {r["puesto"]: np.array([r[l] for l in CELL_LABELS], float)
                   for _, r in pue22.iterrows()}
    prof_zona = pue22.groupby("zona")[CELL_LABELS].sum()
    prof_mun = pue22.groupby("mun")[CELL_LABELS].sum()
    prof_dep = pue22[CELL_LABELS].sum().values.astype(float)

    def seed(pk):
        if pk in prof_puesto and prof_puesto[pk].sum() > 0:
            return prof_puesto[pk], "puesto"
        z = pk.rsplit("-", 1)[0]
        if z in prof_zona.index:
            return prof_zona.loc[z].values.astype(float), "zona"
        mn = pk[:6]
        if mn in prof_mun.index:
            return prof_mun.loc[mn].values.astype(float), "mun"
        return prof_dep, "dep"

    seeds, levels = [], []
    for _, r in turn.iterrows():
        s, lv = seed(r["key"])
        s = np.asarray(s, float)
        seeds.append(s / max(s.sum(), 1e-9))
        levels.append(lv)
    S = np.vstack(seeds)                          # n × 10 shares
    turn["seed_level"] = levels
    for lv in ("puesto", "zona", "mun", "dep"):
        sel = turn["seed_level"] == lv
        if sel.any():
            print(f"   semilla {lv:7s}: {sel.sum():5,} puestos · "
                  f"{turn.loc[sel,'turnout'].sum()/turn['turnout'].sum()*100:5.1f}%")

    # márgenes de celda 2026 a nivel dep: rho_c(2022) × DANE2026_c
    dane = load_dane_sexedad()
    suf22 = pue22[CELL_LABELS].sum().values.astype(float)
    N22 = np.array(dane[2022]); N26 = np.array(dane[2026])
    rho = suf22 / np.maximum(N22, 1.0)
    tgt = rho * N26
    T = turn["turnout"].values.astype(float)
    tgt = tgt / tgt.sum() * T.sum()              # nivel = votantes reales 2026

    # IPF: fila = puesto (margen T), col = celda (margen tgt)
    X = S * T[:, None]
    for _ in range(200):
        cs = X.sum(axis=0)
        X *= np.where(cs > 0, tgt / np.maximum(cs, 1e-9), 1.0)[None, :]
        rs = X.sum(axis=1)
        X *= (T / np.maximum(rs, 1e-9))[:, None]

    out = turn[["key", "mun", "seed_level", "turnout"]].copy()
    for i, l in enumerate(CELL_LABELS):
        out[l] = X[:, i]
    out.rename(columns={"key": "puesto"}, inplace=True)
    out.to_csv(os.path.join(OUT, "comp-2026-puesto.csv"), index=False)
    mun = out.groupby("mun", as_index=False)[CELL_LABELS].sum()
    mun.to_csv(os.path.join(OUT, "comp-2026-mun.csv"), index=False)

    sh = X.sum(axis=0) / X.sum() * 100
    sh22 = suf22 / suf22.sum() * 100
    print("   share dep por celda 2026 (2022 obs):")
    for i, l in enumerate(CELL_LABELS):
        print(f"      {l:8s} {sh[i]:5.1f}  ({sh22[i]:5.1f})")
    print(f"   -> comp-2026-puesto.csv ({len(out):,}) · comp-2026-mun.csv ({len(mun)})")


if __name__ == "__main__":
    _, pue22, _ = build_2022()
    build_2026(pue22)
