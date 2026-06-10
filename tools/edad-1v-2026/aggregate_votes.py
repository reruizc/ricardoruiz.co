#!/usr/bin/env python3
"""Agrega votos presidenciales 1V a nivel de puesto (dep-mun-zz-pp).

  - 2022: GCS_2022PRES1V.csv (escrutinio, mesa-level, ';')
  - 2026: PRECONTEO_1V_2026_MESA_con_Claudia.csv (preconteo 0247 + Claudia)

Salida en Bases de datos/output_edad_1v/:
  votos-2022-puesto.csv   pcode + candidatos top + blanco/nulos/nm + total
  votos-2026-puesto.csv   idem 2026
"""
import csv
import os
from collections import defaultdict

BASE = os.path.join(os.path.dirname(__file__), "..", "..", "Bases de datos")
OUT = os.path.join(BASE, "output_edad_1v")


def norm(v, width):
    """código RNEC → string zero-padded; alfanumérico (exterior) queda igual."""
    s = str(v).strip().strip('"')
    return s.zfill(width) if s.isdigit() else s


def pcode(dep, mun, zz, pp):
    return f"{norm(dep,2)}-{norm(mun,3)}-{norm(zz,2)}-{norm(pp,2)}"


# --------------------------------------------------------------- 2022
CAND22 = {  # DES_CAN (normalizado contains) -> slug
    "GUSTAVO PETRO": "petro",
    "FEDERICO GUTIERREZ": "fico",
    "RODOLFO HERNANDEZ": "rodolfo",
    "SERGIO FAJARDO": "fajardo",
}
COLS22 = ["petro", "fico", "rodolfo", "fajardo", "otros",
          "blanco", "nulos", "no_marcados", "total_validos", "total_votos"]


def agg_2022():
    acc = defaultdict(lambda: defaultdict(int))
    src = os.path.join(BASE, "FINAL SUBIDA GCS", "GCS_2022PRES1V.csv")
    with open(src, encoding="utf-8-sig") as f:
        r = csv.DictReader(f, delimiter=";")
        for row in r:
            key = pcode(row["COD_DDE"], row["COD_MME"], row["COD_ZZ"], row["COD_PP"])
            v = int(row["NUM_VOT"] or 0)
            cod_can = str(row["COD_CAN"]).strip()
            des = (row["DES_CAN"] or "").upper()
            a = acc[key]
            if cod_can == "996":
                a["blanco"] += v
            elif cod_can == "997":
                a["nulos"] += v
            elif cod_can in ("998", "999"):
                a["no_marcados"] += v
            else:
                slug = next((s for k, s in CAND22.items() if k in des), "otros")
                a[slug] += v
    write(acc, COLS22, "votos-2022-puesto.csv")
    return acc


# --------------------------------------------------------------- 2026
CAND26 = {
    "Iván Cepeda": "cepeda",
    "Abelardo De La Espriella": "abelardo",
    "Paloma Valencia": "paloma",
    "Sergio Fajardo": "fajardo26",
    "Claudia López": "claudia",
}
COLS26 = ["cepeda", "abelardo", "paloma", "fajardo26", "claudia", "otros",
          "blanco", "nulos", "no_marcados", "total_validos", "total_votos"]


def agg_2026():
    acc = defaultdict(lambda: defaultdict(int))
    src = os.path.join(BASE, "nuevos archivos 1v 2026",
                       "PRECONTEO_1V_2026_MESA_con_Claudia.csv")
    with open(src, encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        cand_cols = [c for c in r.fieldnames
                     if c not in ("cod_departamento", "cod_municipio", "zona",
                                  "puesto", "num_mesa", "votos_blanco",
                                  "votos_nulos", "votos_no_marcados",
                                  "total_votos_urna", "fecha_actualizacion")]
        for row in r:
            key = pcode(row["cod_departamento"], row["cod_municipio"],
                        row["zona"], row["puesto"])
            a = acc[key]
            for c in cand_cols:
                v = int(row[c] or 0)
                a[CAND26.get(c, "otros")] = a.get(CAND26.get(c, "otros"), 0) + v
            a["blanco"] += int(row["votos_blanco"] or 0)
            a["nulos"] += int(row["votos_nulos"] or 0)
            a["no_marcados"] += int(row["votos_no_marcados"] or 0)
    write(acc, COLS26, "votos-2026-puesto.csv")
    return acc


def write(acc, cols, fname):
    os.makedirs(OUT, exist_ok=True)
    cand_cols = [c for c in cols if c not in
                 ("total_validos", "total_votos", "nulos", "no_marcados")]
    with open(os.path.join(OUT, fname), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pcode"] + cols)
        for key in sorted(acc):
            a = acc[key]
            tv = sum(a.get(c, 0) for c in cand_cols)          # válidos = cands + blanco
            tt = tv + a.get("nulos", 0) + a.get("no_marcados", 0)
            w.writerow([key] + [a.get(c, 0) for c in cols[:-2]] + [tv, tt])
    tot = defaultdict(int)
    for a in acc.values():
        for k, v in a.items():
            tot[k] += v
    print(f"{fname}: {len(acc)} puestos")
    for k in cols[:-2]:
        print(f"   {k:14s} {tot.get(k,0):>12,}")


if __name__ == "__main__":
    print("== 2022 ==")
    agg_2022()
    print("== 2026 ==")
    agg_2026()
