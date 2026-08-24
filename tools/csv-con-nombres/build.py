#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py — Genera 3 CSV mesa-a-mesa 2026 con CÓDIGOS + NOMBRES.

Salidas en: Bases de datos/csv_con_nombres_2026/
  - presidencial_1v_2026.csv
  - presidencial_2v_2026.csv
  - congreso_2026.csv

Formato largo (una fila por mesa x candidato/partido), UTF-8 con BOM (Excel),
delimitado por coma. Columnas comunes de códigos: cod_departamento,
cod_municipio, cod_zona, cod_puesto, cod_mesa + nombres de depto/municipio/
puesto + nombre de candidato + partido + votos.

Fuentes:
  1V  Bases de datos/nuevos archivos 1v 2026/PRECONTEO_1V_2026_MESA_con_Claudia.csv
      (formato ancho, SIN nombres geograficos -> se cruzan con GEOREF+2V;
       partido presidencial via dict PARTIDO_1V).
  2V  Bases de datos/output_2v/PRECONTEO_2V_2026_MESA.csv
      (ya trae NOM_DEP/NOM_MUN/NOM_PUESTO/NOM_CAN; partido via dict PARTIDO_2V).
  Congreso  Bases de datos/DEPTOS_DECLARADOS/*.csv (58 archivos MMV/CITREP, ';')
      (ya traen todos los nombres; se excluye la corporacion CONSULTAS).
"""
import csv, glob, os, sys

BASE = "/Users/ricardoruiz/ricardoruiz.co/Bases de datos"
OUT  = os.path.join(BASE, "csv_con_nombres_2026")
os.makedirs(OUT, exist_ok=True)
csv.field_size_limit(10**7)

# ── Partidos presidenciales ───────────────────────────────────────────────
# Confirmados desde el repo (test-presidencial/candidatos.json) + notorios.
# Los que quedan en "" son candidatos menores sin fuente en el repo -> Ricardo
# los completa y se re-corre este script (dict de arriba).
PARTIDO_1V = {
    "Iván Cepeda":              "Pacto Histórico",
    "Abelardo De La Espriella": "Independiente",
    "Paloma Valencia":          "Centro Democrático",
    "Claudia López":            "Centro",
    "Sergio Fajardo":           "Coalición de Centro",
    "Roy Barreras":             "Frente por la Vida",
    "Carlos Caicedo":           "Fuerza Ciudadana",
    "Miguel Uribe":             "Partido Demócrata",
    "Mauricio Lizcano":         "Coalición F.A.M.I.L.I.A.",
    "Santiago Botero":          "MSC Romper el Sistema",
    "Sondra Macollins":         "Partido Digital Colombia Soy Yo",
    "Gustavo Matamoros":        "Partido Ecologista Colombiano",
    "Gilberto Murillo":         "La Oportunidad es Colombia",
}
PARTIDO_2V = {
    "IVAN CEPEDA CASTRO":       "Pacto Histórico",
    "ABELARDO DE LA ESPRIELLA": "Independiente",
}
COMMON_HDR = ["cod_departamento","cod_municipio","cod_zona","cod_puesto","cod_mesa",
              "nom_departamento","nom_municipio","nom_puesto","nom_candidato","partido","votos"]

def nk(x):
    x = str(x).strip()
    try: return str(int(x))
    except ValueError: return x.upper()
def key(d,m,z,p): return (nk(d),nk(m),nk(z),nk(p))

# ── Lookup de nombres geograficos para 1V (GEOREF primario, 2V fallback) ───
def build_geo_lookup():
    geo = {}
    with open(os.path.join(BASE,"PUESTOS_GEOREF.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            cc = row["CÓDIGO COMPLETO"].strip()
            if len(cc)!=9 or not cc.isdigit(): continue
            geo[key(cc[:2],cc[2:5],cc[5:7],cc[7:9])] = (
                row["DEPARTAMENTO"].strip(), row["MUNICIPIO"].strip(), row["NOMBRE PUESTO"].strip())
    with open(os.path.join(BASE,"output_2v/PRECONTEO_2V_2026_MESA.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            k = key(row["COD_DEP"],row["COD_MUN"],row["COD_ZONA"],row["COD_PUESTO"])
            if k not in geo:
                geo[k] = (row["NOM_DEP"].strip(), row["NOM_MUN"].strip(), row["NOM_PUESTO"].strip())
    return geo

# ── 1ra vuelta ─────────────────────────────────────────────────────────────
def build_1v(geo):
    src = os.path.join(BASE,"nuevos archivos 1v 2026/PRECONTEO_1V_2026_MESA_con_Claudia.csv")
    dst = os.path.join(OUT,"presidencial_1v_2026.csv")
    ESPECIALES = {"votos_blanco":"VOTOS EN BLANCO","votos_nulos":"VOTOS NULOS",
                  "votos_no_marcados":"VOTOS NO MARCADOS"}
    cand_cols = list(PARTIDO_1V.keys())
    n=0; miss=set()
    with open(src, encoding="utf-8-sig") as f, open(dst,"w",encoding="utf-8-sig",newline="") as g:
        r = csv.DictReader(f); w = csv.writer(g); w.writerow(COMMON_HDR)
        # validar que todas las columnas de candidato existan
        for c in cand_cols:
            if c not in r.fieldnames: raise SystemExit(f"1V: falta columna candidato '{c}'")
        for row in r:
            k = key(row["cod_departamento"],row["cod_municipio"],row["zona"],row["puesto"])
            nd,nm,npu = geo.get(k, ("","",""))
            if k not in geo: miss.add(k)
            base = [row["cod_departamento"],row["cod_municipio"],row["zona"],row["puesto"],row["num_mesa"],nd,nm,npu]
            for c in cand_cols:
                w.writerow(base + [c, PARTIDO_1V[c], row[c]]); n+=1
            for col,nom in ESPECIALES.items():
                w.writerow(base + [nom, "", row[col]]); n+=1
    print(f"[1V] filas={n:,} puestos_sin_nombre={len(miss)} -> {dst}")

# ── 2da vuelta ─────────────────────────────────────────────────────────────
def build_2v():
    src = os.path.join(BASE,"output_2v/PRECONTEO_2V_2026_MESA.csv")
    dst = os.path.join(OUT,"presidencial_2v_2026.csv")
    n=0
    with open(src, encoding="utf-8-sig") as f, open(dst,"w",encoding="utf-8-sig",newline="") as g:
        r = csv.DictReader(f); w = csv.writer(g); w.writerow(COMMON_HDR)
        for row in r:
            w.writerow([row["COD_DEP"],row["COD_MUN"],row["COD_ZONA"],row["COD_PUESTO"],row["COD_MESA"],
                        row["NOM_DEP"],row["NOM_MUN"],row["NOM_PUESTO"],
                        row["NOM_CAN"], PARTIDO_2V.get(row["NOM_CAN"].strip(),""), row["VOTOS"]]); n+=1
    print(f"[2V] filas={n:,} -> {dst}")

# ── Congreso ────────────────────────────────────────────────────────────────
def build_congreso():
    files = sorted(glob.glob(os.path.join(BASE,"DEPTOS_DECLARADOS","*.csv")))
    dst = os.path.join(OUT,"congreso_2026.csv")
    hdr = ["cod_departamento","cod_municipio","cod_zona","cod_puesto","cod_mesa",
           "corporacion","circunscripcion_cod","nom_departamento","nom_municipio","nom_puesto",
           "partido","nom_candidato","votos"]
    n=0; excl=0
    with open(dst,"w",encoding="utf-8-sig",newline="") as g:
        w = csv.writer(g); w.writerow(hdr)
        for fp in files:
            with open(fp, encoding="utf-8-sig") as f:
                r = csv.DictReader(f, delimiter=";")
                for row in r:
                    cor = row["CORNOMBRE"].strip()
                    if cor == "CONSULTAS":   # excluir consultas presidenciales
                        excl+=1; continue
                    w.writerow([row["DEP"],row["MUN"],row["ZONA"],row["PUESTO"],row["MESA"],
                                cor, row["CIR"], row["DEPNOMBRE"].strip(), row["MUNNOMBRE"].strip(),
                                row["PUESNOMBRE"].strip(), row["PARNOMBRE"].strip(),
                                row["CANNOMBRE"].strip(), row["VOTOS"]]); n+=1
    print(f"[Congreso] archivos={len(files)} filas={n:,} consultas_excluidas={excl:,} -> {dst}")

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv)>1 else "all"
    if which in ("all","1v","2v"): geo = build_geo_lookup() if which in ("all","1v") else None
    if which in ("all","1v"): build_1v(geo)
    if which in ("all","2v"): build_2v()
    if which in ("all","congreso"): build_congreso()
