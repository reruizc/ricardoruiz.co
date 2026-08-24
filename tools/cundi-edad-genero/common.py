#!/usr/bin/env python3
"""Helpers compartidos del pipeline edad×género del Congreso · Cundinamarca.

Construye la tabla de votación por municipio × partido × sexo × grupo de edad
(y "en general") para Cámara y Senado, 2022 (observado) y 2026 (proyectado),
en el departamento de Cundinamarca (código electoral RNEC = 15).

Celdas demográficas: 2 sexos × 5 grupos de edad = 10 celdas.
  H/M × {18-25, 26-35, 36-45, 46-60, 61+}

Fuentes:
  - Edadygenero.xlsx (RNEC)  → sufragantes por mesa × sexo × edad (joint), 2022.
  - GCS_2022CON.csv (RNEC)   → votos por mesa × lista, Congreso 2022.
  - DEPTOS_DECLARADOS/MMV_..._15_...csv → votos por mesa × lista, Congreso 2026.
  - DANE-AreaSexoEdadDep-2018-2050_VP.xlsx → población por sexo × edad simple × depto.
"""
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.normpath(os.path.join(HERE, "..", "..", "Bases de datos"))
OUT = os.path.join(BASE, "output_cundi_edad_genero")

DEP_CUNDI = "15"          # código electoral RNEC (consistente 2022 y 2026)
DEP_DANE_NAME = "Cundinamarca"

# ---- bandas RNEC (10) en Edadygenero, joint por sexo ----
BANDS10 = ["18 a 20 años", "21 a 25 años", "26 a 30 años", "31 a 35 años",
           "36 a 40 años", "41 a 45 años", "46 a 50 años", "51 a 55 años",
           "56 a 60 años", "Mayor a 60 años"]

# nombres EXACTOS de las columnas joint en el header de Edadygenero
H_COLS = ["Hombres entre 18 a 20 años", "Hombres entre 21 a 25 años",
          "Hombres entre 26 a 30 años", "Hombres entre 31 a 35 años",
          "Hombres entre 36 a 40 años", "Hombres entre 41 a 45 años",
          "Hombres entre 46 a 50 años", "Hombres entre 51 a 55 años",
          "Hombres entre 56 a 60 años", "Hombres Mayores a 60 años"]
M_COLS = ["Mujeres entre 18 a 20 años", "Mujeres entre 21 a 25 años",
          "Mujeres entre 26 a 30 años", "Mujeres entre 31 a 35 años",
          "Mujeres entre 36 a 40 años", "Mujeres entre 41 a 45 años",
          "Mujeres entre 46 a 50 años", "Mujeres entre 51 a 55 años",
          "Mujeres entre 56 a 60 años", "Mujeres mayores a 60 años"]
H_INDEF = "Hombres Edad Indefinida"
M_INDEF = "Mujeres Edad Indefinida"

# ---- 5 grupos de edad (colapso de las 10 bandas) ----
GROUPS = ["18-25", "26-35", "36-45", "46-60", "61+"]
# índice de banda RNEC (0..9) -> índice de grupo (0..4)
BAND_TO_GROUP = [0, 0, 1, 1, 2, 2, 3, 3, 3, 4]
SEXES = ["H", "M"]

# 10 celdas en orden canónico: H-18-25, H-26-35, ..., M-61+
CELLS = [(s, g) for s in SEXES for g in GROUPS]
CELL_LABELS = [f"{s}-{g}" for (s, g) in CELLS]


def cell_index(sex, gi):
    """(sex 'H'/'M', group idx 0..4) -> índice de celda 0..9."""
    return (0 if sex == "H" else 5) + gi


def nrm(s):
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Z0-9 ]", "", s.upper()).strip()


def zf(v, w):
    s = str(v).strip().strip('"')
    return s.zfill(w) if s.isdigit() else s


def mesa_key(dep, mun, zona, puesto, mesa):
    """Llave de mesa canónica dep-mun-zona-puesto-mesa (ceros a la izquierda)."""
    return "-".join([zf(dep, 2), zf(mun, 3), zf(zona, 2), zf(puesto, 2), zf(mesa, 3)])


def puesto_key(dep, mun, zona, puesto):
    return "-".join([zf(dep, 2), zf(mun, 3), zf(zona, 2), zf(puesto, 2)])


def collapse_bands_to_groups(bands10):
    """[10 valores por banda RNEC] -> [5 valores por grupo]."""
    g = [0.0] * 5
    for b in range(10):
        g[BAND_TO_GROUP[b]] += float(bands10[b] or 0)
    return g


# ------------------------------------------------------------------ DANE
def load_dane_sexedad(depname=DEP_DANE_NAME, years=(2018, 2022, 2026)):
    """Población por sexo × grupo de edad para UN departamento.

    -> {year: [10 valores]} en el orden de CELLS (H-18-25..M-61+), área Total.
    """
    import openpyxl
    wb = openpyxl.load_workbook(
        os.path.join(BASE, "DANE-AreaSexoEdadDep-2018-2050_VP.xlsx"),
        read_only=True, data_only=True)
    ws = wb["PobDepartamentalxÁreaSexoEdad"]
    rows = ws.iter_rows(min_row=8, values_only=True)
    h8 = next(rows)
    h9 = next(rows)
    labels = [h8[i] if i < 4 else h9[i] for i in range(len(h9))]
    age_cols = []   # (idx, 'H'/'M', edad_int)
    for i, lab in enumerate(labels):
        if lab is None:
            continue
        m = re.match(r"^(Hombres|Mujeres)\s+(\d+|100)", str(lab))
        if m and ("año" in str(lab)):
            sx = "H" if m.group(1) == "Hombres" else "M"
            age_cols.append((i, sx, int(m.group(2))))

    def group_of(age):
        if age < 18:
            return None
        if age <= 25:
            return 0
        if age <= 35:
            return 1
        if age <= 45:
            return 2
        if age <= 60:
            return 3
        return 4

    target = nrm(depname)
    out = {y: [0.0] * 10 for y in years}
    for row in rows:
        if row[0] is None:
            continue
        try:
            anio = int(row[2])
        except (TypeError, ValueError):
            continue
        if anio not in years or str(row[3]).strip() != "Total":
            continue
        if nrm(row[1]) != target:
            continue
        for i, sx, edad in age_cols:
            gi = group_of(edad)
            if gi is None or row[i] is None:
                continue
            out[anio][cell_index(sx, gi)] += float(row[i])
    wb.close()
    return out


if __name__ == "__main__":
    print("CELLS:", CELL_LABELS)
    d = load_dane_sexedad()
    for y in (2018, 2022, 2026):
        tot = sum(d[y])
        print(f"DANE {DEP_DANE_NAME} {y}: total 18+ = {tot:,.0f}")
        print("   " + "  ".join(f"{lab}:{d[y][i]/1e3:.0f}k"
                                for i, lab in enumerate(CELL_LABELS)))
