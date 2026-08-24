#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis del voto en el exterior (depto 88 · Consulados) 1V vs 2V 2026.

Fuentes crudas (ground truth):
  1V: Bases de datos/nuevos archivos 1v 2026/PRECONTEO_1V_2026_MESA_con_Claudia.csv
      (depto 88, 13 candidatos + blanco/nulos/no-marcados, Claudia recuperada)
  2V: Bases de datos/output_2v/detalle_nacional_presidencia_mesas.xlsx
      (CONSULADOS, Cepeda/Abelardo + blanco/nulos/no-marcados)
  crosswalk código país -> nombre: Bases de datos/test-presidencial/divipola.json (dep 88)

Salida: exterior_1v_2v.json (totales nacionales-exterior + por país)
"""
import csv, json, unicodedata, os, sys
import openpyxl

BASE = "/Users/ricardoruiz/ricardoruiz.co/Bases de datos"
CSV_1V = os.path.join(BASE, "nuevos archivos 1v 2026", "PRECONTEO_1V_2026_MESA_con_Claudia.csv")
XLSX_2V = os.path.join(BASE, "output_2v", "detalle_nacional_presidencia_mesas.xlsx")
DIVIPOLA = os.path.join(BASE, "test-presidencial", "divipola.json")
OUT = "/Users/ricardoruiz/ricardoruiz.co/tools/exterior-2v/exterior_1v_2v.json"

def norm(s):
    if s is None: return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii","ignore").decode("ascii")
    return " ".join(s.upper().replace(".","").split())

# --- crosswalk código municipio (dep 88) -> nombre país ---
dv = json.load(open(DIVIPOLA))
ext_dep = [d for d in dv["deptos"] if d["cod"]=="88"][0]
CODE2COUNTRY = {m["cod"]: m["nombre"] for m in ext_dep["muns"]}      # '120' -> 'Alemania'
NAME2CODE = {norm(m["nombre"]): m["cod"] for m in ext_dep["muns"]}    # 'ALEMANIA' -> '120'

# candidatos en el header del CSV 1V (orden exacto de columnas)
CANDS_1V = ["Iván Cepeda","Santiago Botero","Abelardo De La Espriella","Mauricio Lizcano",
            "Miguel Uribe","Sondra Macollins","Roy Barreras","Carlos Caicedo","Gustavo Matamoros",
            "Paloma Valencia","Sergio Fajardo","Gilberto Murillo","Claudia López"]
SLUG = {"Iván Cepeda":"cepeda","Santiago Botero":"botero","Abelardo De La Espriella":"abelardo",
        "Mauricio Lizcano":"lizcano","Miguel Uribe":"miguel_uribe","Sondra Macollins":"macollins",
        "Roy Barreras":"roy","Carlos Caicedo":"caicedo","Gustavo Matamoros":"matamoros",
        "Paloma Valencia":"paloma","Sergio Fajardo":"fajardo","Gilberto Murillo":"murillo",
        "Claudia López":"claudia"}

# -------- 1V: agregar por país (código municipio) --------
v1_pais = {}   # code -> {slug: votos, blanco, nulos, no_marcados, urna, mesas}
def blank_pais(): return {s:0 for s in SLUG.values()} | {"blanco":0,"nulos":0,"no_marcados":0,"urna":0,"mesas":0}
with open(CSV_1V, encoding="utf-8-sig") as f:
    r = csv.reader(f)
    header = next(r)
    # localizar índices
    idx = {h:i for i,h in enumerate(header)}
    iCand = {c: idx[c] for c in CANDS_1V}
    iBl, iNu, iNm, iUr = idx["votos_blanco"], idx["votos_nulos"], idx["votos_no_marcados"], idx["total_votos_urna"]
    iDep, iMun = idx["cod_departamento"], idx["cod_municipio"]
    for row in r:
        if row[iDep] != "88": continue
        code = row[iMun]
        d = v1_pais.setdefault(code, blank_pais())
        for c in CANDS_1V:
            d[SLUG[c]] += int(row[iCand[c]] or 0)
        d["blanco"] += int(row[iBl] or 0)
        d["nulos"]  += int(row[iNu] or 0)
        d["no_marcados"] += int(row[iNm] or 0)
        d["urna"]   += int(row[iUr] or 0)
        d["mesas"]  += 1

# -------- 2V: agregar por país (nombre municipio) --------
v2_pais = {}   # code -> {cepeda, abelardo, blanco, nulos, no_marcados, urna, mesas}
unmatched_2v = {}
wb = openpyxl.load_workbook(XLSX_2V, read_only=True)
ws = wb["Presidencia_Mesas"]
def num(x):
    try: return int(x)
    except: return 0
for row in ws.iter_rows(min_row=2, values_only=True):
    if row[1] != "CONSULADOS": continue
    pais_nombre = row[2]
    code = NAME2CODE.get(norm(pais_nombre))
    if code is None:
        unmatched_2v[pais_nombre] = unmatched_2v.get(pais_nombre,0)+1
        code = "ZZ:"+norm(pais_nombre)   # conservar, marcar
    d = v2_pais.setdefault(code, {"cepeda":0,"abelardo":0,"blanco":0,"nulos":0,"no_marcados":0,"urna":0,"mesas":0})
    d["blanco"]      += num(row[7])
    d["no_marcados"] += num(row[8])
    d["nulos"]       += num(row[9])
    d["cepeda"]      += num(row[10])
    d["abelardo"]    += num(row[11])
    d["urna"] = d["cepeda"]+d["abelardo"]+d["blanco"]+d["nulos"]+d["no_marcados"]
    d["mesas"]       += 1

# -------- ensamblar por país --------
all_codes = set(v1_pais) | set(v2_pais)
paises = []
for code in all_codes:
    nombre = CODE2COUNTRY.get(code, code.replace("ZZ:",""))
    a = v1_pais.get(code, blank_pais())
    b = v2_pais.get(code, {"cepeda":0,"abelardo":0,"blanco":0,"nulos":0,"no_marcados":0,"urna":0,"mesas":0})
    val1 = a["urna"] - a["blanco"] - a["nulos"] - a["no_marcados"]   # válidos candidato 1V (incl. todos)
    cc1, ca1 = a["cepeda"], a["abelardo"]
    val2 = b["cepeda"] + b["abelardo"]
    paises.append({
        "code": code, "pais": nombre,
        "v1": {k:a[k] for k in a},
        "v2": {"cepeda":b["cepeda"],"abelardo":b["abelardo"],"blanco":b["blanco"],
               "nulos":b["nulos"],"no_marcados":b["no_marcados"],"urna":b["urna"],"mesas":b["mesas"]},
        "cep1": cc1, "abe1": ca1,
        "cep2": b["cepeda"], "abe2": b["abelardo"],
        "validos1": val1, "validos2": val2,
    })

# totales
def acc(field_fn):
    return sum(field_fn(p) for p in paises)
tot = {
    "1v": {s: acc(lambda p,s=s: p["v1"][s]) for s in SLUG.values()},
    "2v": {"cepeda": acc(lambda p: p["cep2"]), "abelardo": acc(lambda p: p["abe2"])},
}
tot["1v"]["blanco"] = acc(lambda p: p["v1"]["blanco"])
tot["1v"]["nulos"]  = acc(lambda p: p["v1"]["nulos"])
tot["1v"]["no_marcados"] = acc(lambda p: p["v1"]["no_marcados"])
tot["1v"]["urna"]   = acc(lambda p: p["v1"]["urna"])
tot["1v"]["mesas"]  = acc(lambda p: p["v1"]["mesas"])
tot["2v"]["blanco"] = acc(lambda p: p["v2"]["blanco"])
tot["2v"]["nulos"]  = acc(lambda p: p["v2"]["nulos"])
tot["2v"]["no_marcados"] = acc(lambda p: p["v2"]["no_marcados"])
tot["2v"]["urna"]   = acc(lambda p: p["v2"]["urna"])
tot["2v"]["mesas"]  = acc(lambda p: p["v2"]["mesas"])

out = {"totales": tot, "paises": sorted(paises, key=lambda p:-p["v2"]["urna"]),
       "unmatched_2v": unmatched_2v}
json.dump(out, open(OUT,"w"), ensure_ascii=False, indent=1)

# -------- reporte en consola --------
def pct(x,t): return 100*x/t if t else 0
print("="*70)
print("VOTO EN EL EXTERIOR (depto 88 · Consulados)  —  1V vs 2V 2026")
print("="*70)
t1, t2 = tot["1v"], tot["2v"]
val1 = t1["urna"]-t1["blanco"]-t1["nulos"]-t1["no_marcados"]
print(f"\nMesas:        1V {t1['mesas']:,}   |   2V {t2['mesas']:,}")
print(f"Votos urna:   1V {t1['urna']:,}   |   2V {t2['urna']:,}   (Δ {t2['urna']-t1['urna']:+,})")
print(f"\n--- 1V · campo completo (válidos candidato = {val1:,}) ---")
order = sorted(SLUG.values(), key=lambda s:-t1[s])
for s in order:
    if t1[s] > 0:
        print(f"  {s:<12} {t1[s]:>9,}   {pct(t1[s],val1):5.1f}%")
print(f"  {'blanco':<12} {t1['blanco']:>9,}")
print(f"  {'nulos':<12} {t1['nulos']:>9,}")
print(f"\n--- 1V cara a cara Cepeda vs Abelardo ---")
cc1, ca1 = t1["cepeda"], t1["abelardo"]
print(f"  Cepeda   {cc1:>9,}   {pct(cc1,cc1+ca1):5.1f}%")
print(f"  Abelardo {ca1:>9,}   {pct(ca1,cc1+ca1):5.1f}%   (margen {ca1-cc1:+,} = {pct(ca1,cc1+ca1)-pct(cc1,cc1+ca1):+.1f} pp)")
print(f"\n--- 2V (válidos = {t2['cepeda']+t2['abelardo']:,}) ---")
cc2, ca2 = t2["cepeda"], t2["abelardo"]
v2t = cc2+ca2
print(f"  Cepeda   {cc2:>9,}   {pct(cc2,v2t):5.1f}%")
print(f"  Abelardo {ca2:>9,}   {pct(ca2,v2t):5.1f}%   (margen {ca2-cc2:+,} = {pct(ca2,v2t)-pct(cc2,v2t):+.1f} pp)")
print(f"  blanco {t2['blanco']:,} | nulos {t2['nulos']:,}")
if unmatched_2v:
    print("\n[!] países 2V sin match en divipola:", unmatched_2v)
print(f"\nJSON -> {OUT}")
