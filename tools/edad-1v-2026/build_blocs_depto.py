#!/usr/bin/env python3
"""Margen bloque IZQUIERDA vs DERECHA por departamento, 1V-2022 y 1V-2026.

margen = (derecha% - izquierda%) sobre votos válidos (incluye blanco en el
denominador; centro queda en válidos pero fuera del numerador). Positivo =
derecha; negativo = izquierda.

Bloques (explícitos y documentados):
  2022  IZQ = Petro
        DER = Rodolfo, Fico, J.M. Rodríguez, Enrique Gómez, Luis Pérez
        CEN = Fajardo, Íngrid Betancourt
  2026  IZQ = Cepeda, Roy Barreras, Carlos Caicedo, Gilberto Murillo
        DER = Abelardo, Paloma, Santiago Botero, Miguel Uribe, G. Matamoros, Macollins
        CEN = Fajardo, Claudia López, Mauricio Lizcano

Salida: Bases de datos/output_edad_1v/blocs-depto.csv
  dep, dep_name, izq22,der22,cen22,val22, izq26,der26,cen26,val26,
  margin22, margin26, shift  (shift>0 = se movió a la derecha)
"""
import csv
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..", "..", "Bases de datos")
OUT = os.path.join(BASE, "output_edad_1v")

# dep RNEC code -> nombre (display) y nombre en GeoJSON DEPARTAMENTOS2.json
# Mapeo autoritativo verificado contra Edadygenero (columna depname).
# OJO: códigos RNEC, NO DANE (p.ej. 27=Santander, 25=N. de Santander).
DEP = {
    "01": ("Antioquia", "Antioquia"), "03": ("Atlántico", "Atlántico"),
    "05": ("Bolívar", "Bolívar"), "07": ("Boyacá", "Boyacá"),
    "09": ("Caldas", "Caldas"), "11": ("Cauca", "Cauca"),
    "12": ("Cesar", "Cesar"), "13": ("Córdoba", "Córdoba"),
    "15": ("Cundinamarca", "Cundinamarca"), "16": ("Bogotá D.C.", "Distrito Capital de Bogotá"),
    "17": ("Chocó", "Chocó"), "19": ("Huila", "Huila"),
    "21": ("Magdalena", "Magdalena"), "23": ("Nariño", "Nariño"),
    "24": ("Risaralda", "Risaralda"), "25": ("Norte de Santander", "Norte de Santander"),
    "26": ("Quindío", "Quindío"), "27": ("Santander", "Santander"),
    "28": ("Sucre", "Sucre"), "29": ("Tolima", "Tolima"),
    "31": ("Valle del Cauca", "Valle del Cauca"), "40": ("Arauca", "Arauca"),
    "44": ("Caquetá", "Caquetá"), "46": ("Casanare", "Casanare"),
    "48": ("La Guajira", "La Guajira"), "50": ("Guainía", "Guainía"),
    "52": ("Meta", "Meta"), "54": ("Guaviare", "Guaviare"),
    "56": ("San Andrés", "San Andrés y Providencia"), "60": ("Amazonas", "Amazonas"),
    "64": ("Putumayo", "Putumayo"), "68": ("Vaupés", "Vaupés"),
    "72": ("Vichada", "Vichada"),
}

# ----- 2022 -----
IZQ22 = {"6"}                              # Petro
DER22 = {"1", "3", "2", "5", "7"}          # Rodolfo, Fico, JM Rodríguez, E. Gómez, L. Pérez
CEN22 = {"4", "8"}                          # Fajardo, Íngrid


def agg_2022():
    acc = defaultdict(lambda: defaultdict(int))
    src = os.path.join(BASE, "FINAL SUBIDA GCS", "GCS_2022PRES1V.csv")
    with open(src, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            dep = str(row["COD_DDE"]).strip().zfill(2)
            if dep not in DEP:
                continue
            v = int(row["NUM_VOT"] or 0)
            cod = str(row["COD_CAN"]).strip()
            a = acc[dep]
            if cod == "6":
                a["pacto"] += v                 # Petro (candidato Pacto, comparable)
            elif cod == "1":
                a["rodolfo"] += v               # candidatos de derecha individuales
            elif cod == "3":
                a["fico"] += v                  # (para el margen cara a cara)
            if cod in IZQ22:
                a["izq"] += v; a["val"] += v
            elif cod in DER22:
                a["der"] += v; a["val"] += v
            elif cod in CEN22:
                a["cen"] += v; a["val"] += v
            elif cod == "996":             # blanco -> válidos
                a["val"] += v
            # nulos/no marcados fuera de válidos
    return acc


# ----- 2026 (preconteo con nombres corregidos) -----
COL_IZQ26 = {"Iván Cepeda", "Roy Barreras", "Carlos Caicedo", "Gilberto Murillo"}
COL_DER26 = {"Abelardo De La Espriella", "Paloma Valencia", "Santiago Botero",
             "Miguel Uribe", "Gustavo Matamoros", "Sondra Macollins"}
COL_CEN26 = {"Sergio Fajardo", "Claudia López", "Mauricio Lizcano"}


def agg_2026():
    acc = defaultdict(lambda: defaultdict(int))
    src = os.path.join(BASE, "nuevos archivos 1v 2026",
                       "PRECONTEO_1V_2026_MESA_con_Claudia.csv")
    with open(src, encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        for row in r:
            dep = str(row["cod_departamento"]).strip().strip('"').zfill(2)
            if dep not in DEP:
                continue
            a = acc[dep]
            a["pacto"] += int(row["Iván Cepeda"] or 0)   # Cepeda (candidato Pacto)
            a["abelardo"] += int(row["Abelardo De La Espriella"] or 0)
            a["paloma"] += int(row["Paloma Valencia"] or 0)
            for c in COL_IZQ26:
                a["izq"] += int(row[c] or 0); a["val"] += int(row[c] or 0)
            for c in COL_DER26:
                a["der"] += int(row[c] or 0); a["val"] += int(row[c] or 0)
            for c in COL_CEN26:
                a["cen"] += int(row[c] or 0); a["val"] += int(row[c] or 0)
            a["val"] += int(row["votos_blanco"] or 0)
    return acc


def main():
    a22, a26 = agg_2022(), agg_2026()
    rows = []
    for dep, (name, geoname) in DEP.items():
        x, y = a22[dep], a26[dep]
        if x["val"] == 0 or y["val"] == 0:
            continue
        m22 = (x["der"] - x["izq"]) / x["val"] * 100
        m26 = (y["der"] - y["izq"]) / y["val"] * 100
        pacto22 = x["pacto"] / x["val"] * 100      # Petro %
        pacto26 = y["pacto"] / y["val"] * 100      # Cepeda %
        # margen cara a cara: Pacto - candidato de derecha más votado del depto
        topder22 = max(x["rodolfo"], x["fico"]) / x["val"] * 100
        topder26 = max(y["abelardo"], y["paloma"]) / y["val"] * 100
        h2h22 = pacto22 - topder22
        h2h26 = pacto26 - topder26
        rows.append(dict(dep=dep, dep_name=name, geoname=geoname,
                         izq22=x["izq"], der22=x["der"], cen22=x["cen"], val22=x["val"],
                         izq26=y["izq"], der26=y["der"], cen26=y["cen"], val26=y["val"],
                         margin22=round(m22, 2), margin26=round(m26, 2),
                         shift=round(m26 - m22, 2),
                         pacto22=round(pacto22, 2), pacto26=round(pacto26, 2),
                         pacto_shift=round(pacto26 - pacto22, 2),
                         h2h22=round(h2h22, 2), h2h26=round(h2h26, 2),
                         h2h_shift=round(h2h26 - h2h22, 2)))
    rows.sort(key=lambda r: r["pacto26"])
    with open(os.path.join(OUT, "blocs-depto.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # control nacional
    ti22 = sum(r["izq22"] for r in rows); td22 = sum(r["der22"] for r in rows)
    tc22 = sum(r["cen22"] for r in rows); tv22 = sum(r["val22"] for r in rows)
    ti26 = sum(r["izq26"] for r in rows); td26 = sum(r["der26"] for r in rows)
    tc26 = sum(r["cen26"] for r in rows); tv26 = sum(r["val26"] for r in rows)
    print(f"NACIONAL 2022: izq {ti22/tv22*100:.1f}% · der {td22/tv22*100:.1f}% · "
          f"cen {tc22/tv22*100:.1f}% · margen {(td22-ti22)/tv22*100:+.1f}")
    print(f"NACIONAL 2026: izq {ti26/tv26*100:.1f}% · der {td26/tv26*100:.1f}% · "
          f"cen {tc26/tv26*100:.1f}% · margen {(td26-ti26)/tv26*100:+.1f}")
    tpa22 = sum(r["pacto22"]*r["val22"] for r in rows)/tv22
    tpa26 = sum(r["pacto26"]*r["val26"] for r in rows)/tv26
    print(f"\nPACTO (Petro->Cepeda) nacional: {tpa22:.1f}% -> {tpa26:.1f}% ({tpa26-tpa22:+.1f})")
    grew = sum(1 for r in rows if r["pacto_shift"] > 0)
    print(f"Cepeda CRECIÓ vs Petro en {grew} de {len(rows)} deptos · cayó en {len(rows)-grew}")
    print("\nDonde más CRECIÓ el Pacto:")
    for r in sorted(rows, key=lambda r: -r["pacto_shift"])[:6]:
        print(f"   {r['dep_name']:22} {r['pacto22']:5.1f} -> {r['pacto26']:5.1f} "
              f"({r['pacto_shift']:+.1f})")
    print("Donde más CAYÓ el Pacto:")
    for r in sorted(rows, key=lambda r: r["pacto_shift"])[:6]:
        print(f"   {r['dep_name']:22} {r['pacto22']:5.1f} -> {r['pacto26']:5.1f} "
              f"({r['pacto_shift']:+.1f})")
    print("\nMARGEN cara a cara (Pacto - mejor derecha) por depto:")
    adelante22 = sum(1 for r in rows if r["h2h22"] > 0)
    adelante26 = sum(1 for r in rows if r["h2h26"] > 0)
    cerro = sum(1 for r in rows if r["h2h_shift"] < 0)
    print(f"   izquierda adelante: {adelante22} deptos (2022) -> {adelante26} (2026) · "
          f"el margen se le CERRÓ en {cerro} de {len(rows)}")
    for r in sorted(rows, key=lambda r: r["h2h26"]):
        flip = " FLIP" if (r["h2h22"] > 0) != (r["h2h26"] > 0) else ""
        print(f"   {r['dep_name']:22} {r['h2h22']:+6.1f} -> {r['h2h26']:+6.1f}{flip}")
    print(f"\nblocs-depto.csv: {len(rows)} departamentos")


if __name__ == "__main__":
    main()
