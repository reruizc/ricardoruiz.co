#!/usr/bin/env python3
"""Prueba de viabilidad del modelo de composición etaria del voto 1V-2026.

1. Agrega Edadygenero (mesa) a puesto para P1V-2018 y P1V-2022.
2. Cruza con votos por puesto (GCS-2022, preconteo-2026) y censos por puesto.
3. Construye crosswalk DANE<->RNEC a nivel depto y factores demográficos.
4. Backtest dep-level: proyecta composición etaria de votantes 2018->2022
   (supuesto: forma de tasas de participación por edad estable) y compara
   contra lo observado en 2022. MAE en puntos porcentuales por banda.

Salidas en Bases de datos/output_edad_1v/:
   edad-2018-puesto.csv · edad-2022-puesto.csv · viabilidad-report.txt
"""
import csv
import json
import os
import re
import unicodedata
from collections import defaultdict

import pandas as pd

HERE = os.path.dirname(__file__)
BASE = os.path.join(HERE, "..", "..", "Bases de datos")
OUT = os.path.join(BASE, "output_edad_1v")
CACHE = os.path.join(OUT, "cache")

BANDS = ["18 a 20 años", "21 a 25 años", "26 a 30 años", "31 a 35 años",
         "36 a 40 años", "41 a 45 años", "46 a 50 años", "51 a 55 años",
         "56 a 60 años", "Mayor a 60 años"]
BSHORT = ["18-20", "21-25", "26-30", "31-35", "36-40",
          "41-45", "46-50", "51-55", "56-60", "61+"]

REPORT = []


def log(*args):
    line = " ".join(str(a) for a in args)
    print(line, flush=True)
    REPORT.append(line)


def nrm(s):
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Z0-9 ]", "", s.upper()).strip()


def zf(v, w):
    s = str(v).strip()
    return s.zfill(w) if s.isdigit() else s


# Bogotá: Edadygenero trae el NOMBRE de la localidad en vez del código de
# zona electoral. Mapeo canónico localidad -> zz (mismo del preconteo 2026).
BOG_LOC = {
    "USAQUEN": "01", "CHAPINERO": "02", "SANTA FE": "03", "SAN CRISTOBAL": "04",
    "USME": "05", "TUNJUELITO": "06", "BOSA": "07", "KENNEDY": "08",
    "FONTIBON": "09", "ENGATIVA": "10", "SUBA": "11", "BARRIOS UNIDOS": "12",
    "TEUSAQUILLO": "13", "LOS MARTIRES": "14", "ANTONIO NARINO": "15",
    "PUENTE ARANDA": "16", "LA CANDELARIA": "17", "CANDELARIA": "17",
    "RAFAEL URIBE URIBE": "18", "RAFAEL URIBE": "18", "CIUDAD BOLIVAR": "19",
    "SUMAPAZ": "20", "CORFERIAS": "90", "CARCELES": "98",
}


# ------------------------------------------------------------------ edad->puesto
def edad_puesto(year):
    df = pd.read_csv(os.path.join(CACHE, f"p1v-{year}.csv"), dtype=str)
    num_cols = ["Cantidad de Sufragantes", "Edad Indefinida",
                "Cantidad Hombres", "Cantidad de Mujeres"] + BANDS
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
    nonnum = df[~df["Cód. Comuna / Localidad"].astype(str).str.strip().str.isdigit()]
    sin_map = sorted(set(nrm(z) for z in nonnum["Cód. Comuna / Localidad"])
                     - set(BOG_LOC))
    if sin_map:
        log(f"   [{year}] zonas con nombre sin mapeo: {sin_map}")
    df["depname"] = df["Estadosnoborrar"]
    g = df.groupby(["pcode", "depname"], as_index=False)[num_cols].sum()
    g["n_mesas"] = df.groupby(["pcode", "depname"]).size().values
    g.to_csv(os.path.join(OUT, f"edad-{year}-puesto.csv"), index=False)
    return g


# ------------------------------------------------------------------ votos
def load_votos(fname):
    df = pd.read_csv(os.path.join(OUT, fname), dtype={"pcode": str})
    return df


def load_censo(year):
    with open(os.path.join(BASE, f"censos-puesto-{year}.json")) as f:
        return json.load(f)["porPuesto"]


# ------------------------------------------------------------------ DANE
def load_dane(years=(2018, 2022, 2026)):
    """-> {dpnom_norm: {year: [pop por banda 0..9]}} (área Total, ambos sexos)."""
    import openpyxl
    wb = openpyxl.load_workbook(
        os.path.join(BASE, "DANE-AreaSexoEdadDep-2018-2050_VP.xlsx"),
        read_only=True, data_only=True)
    ws = wb["PobDepartamentalxÁreaSexoEdad"]
    rows = ws.iter_rows(min_row=8, values_only=True)
    h8 = next(rows)
    h9 = next(rows)
    labels = [h8[i] if i < 4 else h9[i] for i in range(len(h9))]
    # columnas de edad simple por sexo
    age_cols = []   # (idx, sexo, edad_int)
    for i, lab in enumerate(labels):
        if lab is None:
            continue
        m = re.match(r"^(Hombres|Mujeres)\s+(\d+|100)", str(lab))
        if m and ("año" in str(lab)):
            age_cols.append((i, m.group(1), int(m.group(2))))
    def band_of(age):
        if age < 18: return None
        if age <= 20: return 0
        if age <= 25: return 1
        if age <= 30: return 2
        if age <= 35: return 3
        if age <= 40: return 4
        if age <= 45: return 5
        if age <= 50: return 6
        if age <= 55: return 7
        if age <= 60: return 8
        return 9
    dane = defaultdict(lambda: defaultdict(lambda: [0.0] * 10))
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
        for i, sexo, edad in age_cols:
            b = band_of(edad)
            if b is None or row[i] is None:
                continue
            dane[key][anio][b] += float(row[i])
    wb.close()
    return dane


def crosswalk(depnames_rnec, dane_keys):
    """nombre RNEC normalizado -> key DANE normalizada."""
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
            # casos especiales
            if "SAN ANDRES" in n:
                hit = [k for k in dane_keys if "SAN ANDRES" in k]
            elif "BOGOTA" in n:
                hit = [k for k in dane_keys if "BOGOTA" in k]
            elif "VALLE" in n:
                hit = [k for k in dane_keys if "VALLE DEL CAUCA" in k]
            cw[dn] = hit[0] if hit else None
    return cw


# ------------------------------------------------------------------ main
def main():
    os.makedirs(OUT, exist_ok=True)
    log("=" * 78)
    log("A. AGREGACIÓN EDADYGENERO -> PUESTO")
    log("=" * 78)
    e18 = edad_puesto(2018)
    e22 = edad_puesto(2022)
    for y, e in ((2018, e18), (2022, e22)):
        suf = e["Cantidad de Sufragantes"].sum()
        indef = e["Edad Indefinida"].sum()
        bsum = e[BANDS].sum().sum()
        log(f"P1V-{y}: {len(e):,} puestos · {e['n_mesas'].sum():,} mesas · "
            f"{suf:,} sufragantes · bandas suman {bsum:,} · "
            f"edad indefinida {indef:,} ({indef/suf*100:.2f}%)")

    v22 = load_votos("votos-2022-puesto.csv")
    v26 = load_votos("votos-2026-puesto.csv")
    c22 = load_censo(2022)
    c26 = load_censo(2026)

    log("")
    log("=" * 78)
    log("B. CRUCE PUESTO-A-PUESTO (llave dep-mun-zz-pp)")
    log("=" * 78)

    # --- B1: edad22 vs votos22 (mismo año: valida la llave)
    k_e22, k_v22 = set(e22["pcode"]), set(v22["pcode"])
    inter = k_e22 & k_v22
    v22i = v22[v22["pcode"].isin(inter)]
    log(f"B1 · edad22 ∩ votos22: {len(inter):,} puestos "
        f"(edad22={len(k_e22):,}, votos22={len(k_v22):,})")
    log(f"     votos 2022 cubiertos por el cruce: "
        f"{v22i['total_votos'].sum()/v22['total_votos'].sum()*100:.2f}%")

    # cobertura interna: sufragantes edad22 / votos GCS22 en puestos cruzados
    m = e22.merge(v22, on="pcode")
    m["cov"] = m["Cantidad de Sufragantes"] / m["total_votos"].clip(lower=1)
    log(f"     cobertura sufragantes-con-edad / votos-escrutinio por puesto: "
        f"mediana {m['cov'].median()*100:.1f}% · p10 {m['cov'].quantile(.1)*100:.1f}% "
        f"· p90 {m['cov'].quantile(.9)*100:.1f}%")
    nac = m["Cantidad de Sufragantes"].sum() / m["total_votos"].sum()
    log(f"     cobertura nacional (puestos cruzados): {nac*100:.1f}%")
    bad = m[m["cov"] < .70]
    log(f"     puestos con cobertura <70%: {len(bad):,} "
        f"({bad['total_votos'].sum()/m['total_votos'].sum()*100:.1f}% de los votos)")
    peor = (m.groupby("depname")
              .apply(lambda d: d["Cantidad de Sufragantes"].sum() / d["total_votos"].sum(),
                     include_groups=False)
              .sort_values())
    log("     5 deptos con peor cobertura: " +
        " · ".join(f"{i} {v*100:.0f}%" for i, v in peor.head(5).items()))

    # --- B2: votos26 cubiertos por perfil etario 2022 (la semilla del modelo)
    k_v26 = set(v26["pcode"])
    dom26 = {k for k in k_v26
             if not k.startswith("88-") and k.split("-")[2] not in ("90", "98")}
    con_perfil = dom26 & k_e22
    v26d = v26[v26["pcode"].isin(dom26)]
    v26c = v26[v26["pcode"].isin(con_perfil)]
    log("")
    log(f"B2 · puestos 2026 domésticos (sin exterior/cárcel/censo): {len(dom26):,} "
        f"de {len(k_v26):,}")
    log(f"     con perfil etario 2022 directo: {len(con_perfil):,} "
        f"({len(con_perfil)/len(dom26)*100:.1f}%)")
    log(f"     votos 2026 cubiertos con perfil directo: "
        f"{v26c['total_votos'].sum()/v26d['total_votos'].sum()*100:.2f}%")
    # fallback zona para puestos nuevos
    sin = dom26 - k_e22
    zonas22 = {k.rsplit("-", 2)[0] + "-" + k.split("-")[2] for k in k_e22}
    sin_zona_ok = {k for k in sin
                   if (k.rsplit("-", 2)[0] + "-" + k.split("-")[2]) in zonas22}
    v26sz = v26[v26["pcode"].isin(sin_zona_ok)]
    log(f"     puestos nuevos sin perfil: {len(sin):,} · con fallback de ZONA: "
        f"{len(sin_zona_ok):,} ({v26sz['total_votos'].sum()/v26d['total_votos'].sum()*100:.2f}% votos)")

    # --- B3: censos
    log("")
    log(f"B3 · censo26 ∩ votos26 domésticos: "
        f"{len(set(c26) & dom26):,} / {len(dom26):,}")
    log(f"     censo22 ∩ edad22: {len(set(c22) & k_e22):,} / {len(k_e22):,}")

    # --- B4: tamaño de puesto (para ruido de EI)
    log("")
    log(f"B4 · votos por puesto 2026: mediana {v26d['total_votos'].median():.0f} · "
        f"p10 {v26d['total_votos'].quantile(.1):.0f} · p90 {v26d['total_votos'].quantile(.9):.0f}")
    zz = v26d.copy()
    zz["zcode"] = zz["pcode"].map(lambda k: k.rsplit("-", 2)[0] + "-" + k.split("-")[2])
    gz = zz.groupby("zcode")["total_votos"].sum()
    log(f"     nivel zona: {len(gz):,} zonas · mediana {gz.median():.0f} votos")

    # ------------------------------------------------------------- DANE
    log("")
    log("=" * 78)
    log("C. DANE: CROSSWALK DEPTO + FACTORES DEMOGRÁFICOS 2022->2026")
    log("=" * 78)
    dane = load_dane()
    depnames = sorted(set(e22["depname"]) - {"Consulados"})
    cw = crosswalk(depnames, set(dane.keys()))
    miss = [d for d, v in cw.items() if v is None]
    log(f"C1 · deptos RNEC: {len(depnames)} · matcheados a DANE: "
        f"{sum(1 for v in cw.values() if v)} · sin match: {miss if miss else 'ninguno'}")

    nat = defaultdict(lambda: [0.0] * 10)
    for k in dane:
        for y in (2018, 2022, 2026):
            for b in range(10):
                nat[y][b] += dane[k][y][b]
    log("C2 · población nacional 18+ por banda (millones) y factor 22->26:")
    log("     banda   2018   2022   2026   G(22->26)")
    for b in range(10):
        log(f"     {BSHORT[b]:6s} {nat[2018][b]/1e6:6.2f} {nat[2022][b]/1e6:6.2f} "
            f"{nat[2026][b]/1e6:6.2f}   {nat[2026][b]/nat[2022][b]:.3f}")

    # ------------------------------------------------------------- backtest
    log("")
    log("=" * 78)
    log("D. BACKTEST DEP-LEVEL 2018->2022 (supuesto de proyección)")
    log("=" * 78)
    log("Proyecta shares etarios de votantes 2022 = ρ_a(2018)·N_a(2022) renormalizado;")
    log("compara contra shares observados 2022. Error en puntos porcentuales (pp).")

    def dep_bands(e):
        d = defaultdict(lambda: [0.0] * 10)
        for _, r in e.iterrows():
            if r["depname"] == "Consulados":
                continue
            for b in range(10):
                d[r["depname"]][b] += r[BANDS[b]]
        return d

    d18, d22 = dep_bands(e18), dep_bands(e22)
    rows_bt = []
    nat_obs = [0.0] * 10
    nat_prj = [0.0] * 10
    for dep in depnames:
        dk = cw.get(dep)
        if not dk or dep not in d18 or dep not in d22:
            continue
        s18, s22 = d18[dep], d22[dep]
        if sum(s18) == 0 or sum(s22) == 0:
            continue
        rho = [s18[b] / max(dane[dk][2018][b], 1) for b in range(10)]
        prj = [rho[b] * dane[dk][2022][b] for b in range(10)]
        tp, to = sum(prj), sum(s22)
        sh_p = [p / tp * 100 for p in prj]
        sh_o = [o / to * 100 for o in s22]
        mae = sum(abs(a - b) for a, b in zip(sh_p, sh_o)) / 10
        rows_bt.append((dep, mae, max(abs(a - b) for a, b in zip(sh_p, sh_o))))
        for b in range(10):
            nat_prj[b] += prj[b] / tp * to     # pondera por tamaño del dep
            nat_obs[b] += s22[b]
    tobs = sum(nat_obs)
    tprj = sum(nat_prj)
    log("")
    log("D1 · NACIONAL (agregado de deptos): share proyectado vs observado 2022")
    log("     banda   proy%   obs%   err(pp)")
    errs = []
    for b in range(10):
        p, o = nat_prj[b] / tprj * 100, nat_obs[b] / tobs * 100
        errs.append(abs(p - o))
        log(f"     {BSHORT[b]:6s} {p:6.2f} {o:6.2f}   {p-o:+.2f}")
    log(f"     MAE nacional: {sum(errs)/10:.2f} pp · máx |err|: {max(errs):.2f} pp")
    rows_bt.sort(key=lambda r: -r[1])
    log("")
    log("D2 · MAE por depto: mediana "
        f"{pd.Series([r[1] for r in rows_bt]).median():.2f} pp · "
        f"peores 5: " + " · ".join(f"{d} {m:.2f}" for d, m, _ in rows_bt[:5]))

    # naive (sin ajuste DANE): share 2018 directo como proyección de 2022
    nv_errs = []
    for b in range(10):
        sh18 = sum(d18[dep][b] for dep in d18) / sum(sum(v) for v in d18.values()) * 100
        sh22 = nat_obs[b] / tobs * 100
        nv_errs.append(abs(sh18 - sh22))
    log(f"D3 · comparación naive (share-2018 sin DANE): MAE {sum(nv_errs)/10:.2f} pp "
        f"vs modelo {sum(errs)/10:.2f} pp")

    with open(os.path.join(OUT, "viabilidad-report.txt"), "w") as f:
        f.write("\n".join(REPORT))
    log("")
    log(f"Reporte guardado en {os.path.join(OUT, 'viabilidad-report.txt')}")


if __name__ == "__main__":
    main()
