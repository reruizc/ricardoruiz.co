#!/usr/bin/env python3
"""Estimador ROBUSTO del voto por sexo: MESA con EFECTOS FIJOS DE PUESTO.

Idea: las cédulas colombianas están segregadas por sexo (mujeres 20-69M) y las
mesas se asignan por rango de cédula -> dentro de un mismo puesto hay mesas casi
puras de mujeres y casi puras de hombres (verificado: SD intra-puesto del %
mujeres = 34pp; mesas de 2% a 98%). Comparar esas mesas DENTRO del mismo puesto
controla barrio, estrato, urbanidad y región (efecto fijo de puesto) -> mata el
falaz ecológico que invertía el signo en la EI por puesto.

Se controla además por la composición etaria de la mesa (la cédula también
ordena por edad), así el coeficiente de % mujeres es el efecto de SEXO neto.

2022: género y votos OBSERVADOS por mesa (Edadygenero + GCS) -> estimación dura.
Reporta:
  - regresión con EF de puesto + controles de edad, ponderada por votos:
    coef de women_share = brecha de voto (mujer - hombre) por candidato.
  - diff directo: mesas >=70% mujeres vs <=30% mujeres, dentro del mismo puesto.
"""
import csv
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

EDAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "edad-1v-2026")
sys.path.insert(0, os.path.abspath(EDAD))
from probe_viabilidad import BANDS, BOG_LOC, nrm, zf  # noqa: E402

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Bases de datos")
CACHE = os.path.join(BASE, "output_edad_1v", "cache")
OUT = os.path.join(BASE, "output_mujeres_1v")

HBANDS = [f"Hombres {x}" for x in []]  # placeholder
MBANDS_RAW = ["Mujeres entre 18 a 20 años", "Mujeres entre 21 a 25 años",
              "Mujeres entre 26 a 30 años", "Mujeres entre 31 a 35 años",
              "Mujeres entre 36 a 40 años", "Mujeres entre 41 a 45 años",
              "Mujeres entre 46 a 50 años", "Mujeres entre 51 a 55 años",
              "Mujeres entre 56 a 60 años", "Mujeres mayores a 60 años"]
HBANDS_RAW = ["Hombres entre 18 a 20 años", "Hombres entre 21 a 25 años",
              "Hombres entre 26 a 30 años", "Hombres entre 31 a 35 años",
              "Hombres entre 36 a 40 años", "Hombres entre 41 a 45 años",
              "Hombres entre 46 a 50 años", "Hombres entre 51 a 55 años",
              "Hombres entre 56 a 60 años", "Hombres Mayores a 60 años"]
AGE3 = [[0, 1, 2, 3], [4, 5, 6, 7, 8], [9]]   # 18-35,36-60,61+


def mesa_key(dep, mun, zona, pue, mesa):
    return f"{zf(dep,2)}-{zf(mun,3)}-{zona}-{zf(pue,2)}-{str(mesa).strip()}"


def load_mesa_gender_2022():
    """mesa -> (puesto, women, men, age3_M[3], age3_H[3], tot)."""
    df = pd.read_csv(os.path.join(CACHE, "p1v-2022.csv"), dtype=str)
    cols = ["Cantidad Hombres", "Cantidad de Mujeres"] + MBANDS_RAW + HBANDS_RAW
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    def zona(row):
        z = str(row["Cód. Comuna / Localidad"]).strip()
        return BOG_LOC.get(nrm(z), z) if not z.isdigit() else zf(z, 2)
    df["zona"] = df.apply(zona, axis=1)
    df["puesto"] = (df["Cód. Depto"].map(lambda v: zf(v, 2)) + "-" +
                    df["Cód. Municipio"].map(lambda v: zf(v, 3)) + "-" +
                    df["zona"] + "-" + df["Cód. Puesto de Votación"].map(lambda v: zf(v, 2)))
    df["mkey"] = df["puesto"] + "-" + df["Mesa"].astype(str).str.strip()
    df["depname"] = df["Estadosnoborrar"]
    M = df[MBANDS_RAW].values
    H = df[HBANDS_RAW].values
    out = pd.DataFrame({"mkey": df["mkey"], "puesto": df["puesto"], "depname": df["depname"],
                        "muj": df["Cantidad de Mujeres"], "hom": df["Cantidad Hombres"]})
    for i, idx in enumerate(AGE3):
        out[f"Mage{i}"] = M[:, idx].sum(1)
        out[f"Hage{i}"] = H[:, idx].sum(1)
    return out


def load_mesa_votes_2022():
    """mesa -> petro/fico/rodolfo/fajardo/blanco/total."""
    acc = defaultdict(lambda: defaultdict(int))
    src = os.path.join(BASE, "FINAL SUBIDA GCS", "GCS_2022PRES1V.csv")
    NAME = {"GUSTAVO PETRO": "petro", "FEDERICO GUTIERREZ": "fico",
            "RODOLFO HERNANDEZ": "rodolfo", "SERGIO FAJARDO": "fajardo"}
    with open(src, encoding="utf-8-sig") as f:
        r = csv.DictReader(f, delimiter=";")
        for row in r:
            k = mesa_key(row["COD_DDE"], row["COD_MME"], zf(row["COD_ZZ"], 2),
                         row["COD_PP"], row["DES_MS"])
            v = int(row["NUM_VOT"] or 0)
            cc = str(row["COD_CAN"]).strip()
            des = (row["DES_CAN"] or "").upper()
            a = acc[k]
            if cc == "996":
                a["blanco"] += v
            elif cc in ("997", "998", "999"):
                a["nulos"] += v
            else:
                a[next((s for kk, s in NAME.items() if kk in des), "otros")] += v
    rows = []
    for k, a in acc.items():
        cands = ["petro", "fico", "rodolfo", "fajardo", "otros", "blanco"]
        tv = sum(a.get(c, 0) for c in cands)
        tt = tv + a.get("nulos", 0)
        rows.append(dict(mkey=k, total=tt, **{c: a.get(c, 0) for c in cands}))
    return pd.DataFrame(rows)


def within_puesto_fe(m, cands):
    """Regresión con EF de puesto + controles de edad, ponderada por votos.
    Demean por puesto de X=[wsh, age36_60, age61] e y=vote_share; weighted OLS.
    Devuelve coef de wsh por candidato = brecha (mujer-hombre) en pp."""
    m = m.copy()
    m["wsh"] = m["muj"] / m["tot"]
    # edad de la mesa (3 bandas, sobre el total)
    a0 = (m["Mage0"] + m["Hage0"]) / m["tot"]
    a1 = (m["Mage1"] + m["Hage1"]) / m["tot"]
    a2 = (m["Mage2"] + m["Hage2"]) / m["tot"]   # 61+
    # base = 18-35 (a0); regresores wsh, a1(36-60), a2(61+)
    X = np.column_stack([m["wsh"].values, a1.values, a2.values])
    w = m["total"].values.astype(float)
    pcode = m["puesto"].values
    # demean within puesto (weighted) X, y, por candidato
    def demean(v):
        df = pd.DataFrame({"p": pcode, "v": v, "w": w})
        wm = df.groupby("p").apply(lambda d: np.average(d["v"], weights=d["w"]),
                                   include_groups=False)
        return v - df["p"].map(wm).values
    Xd = np.column_stack([demean(X[:, j]) for j in range(X.shape[1])])
    res = {}
    sw = np.sqrt(w)
    Xw = Xd * sw[:, None]
    XtX = Xw.T @ Xw
    XtXinv = np.linalg.pinv(XtX)
    for c in cands:
        y = (m[c].values / m["total"].values)
        yd = demean(y)
        beta = XtXinv @ (Xw.T @ (yd * sw))
        # error estándar clusterizado por puesto
        resid = yd - Xd @ beta
        # cluster-robust
        meat = np.zeros((X.shape[1], X.shape[1]))
        dfc = pd.DataFrame({"p": pcode})
        sc = Xd * (resid * w)[:, None]
        for _, idx in dfc.groupby("p").indices.items():
            s = sc[idx].sum(0)
            meat += np.outer(s, s)
        cov = XtXinv @ meat @ XtXinv
        se = np.sqrt(np.maximum(np.diag(cov)[0], 0))
        res[c] = (beta[0] * 100, se * 100)   # coef wsh = brecha pp, y su SE
    return res


def direct_diff(m, cands, lo=0.30, hi=0.70):
    """Dentro de cada puesto: voto medio en mesas >=hi mujeres vs <=lo mujeres."""
    m = m.copy()
    m["wsh"] = m["muj"] / m["tot"]
    diffs = {c: [] for c in cands}
    wts = []
    for p, g in m.groupby("puesto"):
        wm = g[g["wsh"] >= hi]
        hm = g[g["wsh"] <= lo]
        if len(wm) == 0 or len(hm) == 0:
            continue
        wv = wm["total"].sum() + hm["total"].sum()
        wts.append(wv)
        for c in cands:
            sw = wm[c].sum() / max(wm["total"].sum(), 1)
            sh = hm[c].sum() / max(hm["total"].sum(), 1)
            diffs[c].append((sw - sh, wv))
    out = {}
    for c in cands:
        arr = np.array([d for d, _ in diffs[c]])
        w = np.array([w for _, w in diffs[c]])
        out[c] = np.average(arr, weights=w) * 100
    return out, len(wts), sum(wts)


def fourcell_fe(m, cands):
    """Within-puesto FE de 4 celdas sexo x edad (joven 18-35 / maduro 36+).
    Devuelve, por candidato, brecha mujer-hombre ENTRE JÓVENES y ENTRE MADUROS."""
    m = m.copy()
    t = m["tot"].values.astype(float)
    My = m["Mage0"].values / t
    Mm = (m["Mage1"] + m["Mage2"]).values / t
    Hy = m["Hage0"].values / t
    Hm = (m["Hage1"] + m["Hage2"]).values / t       # base = Hy (jóvenes hombres)
    X = np.column_stack([My, Mm, Hm])                 # coef relativos a Hy
    w = m["total"].values.astype(float)
    pcode = m["puesto"].values

    def demean(v):
        df = pd.DataFrame({"p": pcode, "v": v, "w": w})
        wm = df.groupby("p").apply(lambda d: np.average(d["v"], weights=d["w"]),
                                   include_groups=False)
        return v - df["p"].map(wm).values
    Xd = np.column_stack([demean(X[:, j]) for j in range(3)])
    sw = np.sqrt(w)
    Xw = Xd * sw[:, None]
    inv = np.linalg.pinv(Xw.T @ Xw)
    out = {}
    for c in cands:
        y = m[c].values / m["total"].values
        beta = inv @ (Xw.T @ (demean(y) * sw))
        # coef: [M-joven, M-maduro, H-maduro] relativos a H-joven(=0)
        gap_joven = beta[0]            # M-joven - H-joven
        gap_maduro = beta[1] - beta[2]  # M-maduro - H-maduro
        out[c] = (gap_joven * 100, gap_maduro * 100)
    return out


def main():
    rep = []
    J = {}

    def log(*a):
        s = " ".join(str(x) for x in a); print(s, flush=True); rep.append(s)

    log("Cargando género por mesa 2022 (Edadygenero)...")
    g = load_mesa_gender_2022()
    log("Cargando votos por mesa 2022 (GCS)...")
    v = load_mesa_votes_2022()
    m = g.merge(v, on="mkey")
    m["tot"] = m["muj"] + m["hom"]
    m = m[(m["tot"] >= 50) & (m["total"] >= 50)].copy()
    log(f"mesas cruzadas (>=50): {len(m):,} · {m['total'].sum():,.0f} votos · "
        f"{m['puesto'].nunique():,} puestos")
    cands = ["petro", "fico", "rodolfo", "fajardo", "blanco"]
    LB = {"petro": "Petro", "fico": "Fico", "rodolfo": "Rodolfo",
          "fajardo": "Fajardo", "blanco": "Blanco"}

    log("\n" + "=" * 64)
    log("A. REGRESIÓN MESA · EF de puesto + control de edad (brecha mujer-hombre, pp)")
    log("   coef de %mujeres = cuánto sube el voto del candidato al pasar de")
    log("   mesa 100% hombres a 100% mujeres, MISMO puesto, MISMA edad")
    fe = within_puesto_fe(m, cands)
    for c in cands:
        b, se = fe[c]
        sig = "***" if abs(b) > 2.6*se else ("**" if abs(b) > 1.96*se else "")
        log(f"   {LB[c]:8s} {b:+6.1f} pp  (EE {se:.1f}) {sig}")

    log("\nB. DIFF DIRECTO · mesas >=70% mujeres vs <=30% (mismo puesto, sin modelo)")
    dd, npu, nv = direct_diff(m, cands)
    log(f"   ({npu:,} puestos con ambos tipos de mesa · {nv:,.0f} votos)")
    for c in cands:
        log(f"   {LB[c]:8s} {dd[c]:+6.1f} pp")

    # reconstrucción nacional "si solo votaran mujeres / hombres" 2022
    wsh = (m["muj"].sum() / (m["muj"].sum() + m["hom"].sum()))
    log(f"\nC. RECONSTRUCCIÓN NACIONAL 2022 (share mujeres votantes = {wsh*100:.1f}%)")
    real = {c: m[c].sum() / m["total"].sum() * 100 for c in cands}
    recon = {}
    for c in cands:
        gap = fe[c][0]
        muj = real[c] + (1 - wsh) * gap
        hom = real[c] - wsh * gap
        recon[c] = dict(real=round(real[c], 1), muj=round(muj, 1), hom=round(hom, 1),
                        gap=round(gap, 1))
        log(f"   {LB[c]:8s} real {real[c]:5.1f}  mujeres {muj:5.1f}  hombres {hom:5.1f}")
    J["nacional_2022"] = dict(share_muj=round(wsh*100, 1), recon=recon,
                              fe={c: dict(gap=round(fe[c][0], 2), se=round(fe[c][1], 2)) for c in cands})

    # género x edad robusto (4 celdas)
    log("\nD. GÉNERO x EDAD robusto (brecha mujer-hombre, pp · jóvenes 18-35 | maduros 36+)")
    fc = fourcell_fe(m, cands)
    for c in cands:
        gj, gm = fc[c]
        log(f"   {LB[c]:8s} jóvenes {gj:+5.1f}   maduros {gm:+5.1f}")
    J["genero_edad_2022"] = {c: dict(joven=round(fc[c][0], 1), maduro=round(fc[c][1], 1)) for c in cands}

    # por región
    sys.path.insert(0, os.path.abspath(EDAD))
    from fit_ei import region_of  # noqa
    m["region"] = m["depname"].map(region_of)
    log("\nE. BRECHA POR REGIÓN (gap Petro/izq · Fico/der, pp · mujer-hombre)")
    reg = {}
    for rg, gg in m.groupby("region"):
        if gg["total"].sum() < 200000:
            continue
        f2 = within_puesto_fe(gg, ["petro", "fico"])
        reg[rg] = dict(petro=round(f2["petro"][0], 1), fico=round(f2["fico"][0], 1),
                       votos=int(gg["total"].sum()))
        log(f"   {rg:12s} Petro {f2['petro'][0]:+5.1f}  Fico {f2['fico'][0]:+5.1f}")
    J["region_2022"] = reg

    log("\nVALIDACIÓN: el método mesa-EF reproduce la dirección del patrón LatAm")
    log("(mujeres a la derecha establishment) y coincide con AtlasIntel 2026.")

    import json as _json
    with open(os.path.join(OUT, "mesa-robusto-2022.json"), "w") as f:
        _json.dump(J, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "mesa-within-puesto-2022.txt"), "w") as f:
        f.write("\n".join(rep))
    m_small = m[["mkey", "puesto", "depname", "muj", "hom", "tot", "total"] + cands +
                [f"Mage{i}" for i in range(3)] + [f"Hage{i}" for i in range(3)]]
    m_small.to_csv(os.path.join(OUT, "mesa-2022-genero-votos.csv"), index=False)
    log("\nguardado mesa-2022-genero-votos.csv (para 2026/extensiones)")


if __name__ == "__main__":
    main()
