#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cartagena · análisis 2V por barrio para la campaña de Abelardo De La Espriella.
Cliente: Tatiana Villarreal.

Lee master_2026_puesto.json (preconteo 1V por puesto, georef), filtra Cartagena
(dep 05 / mun 001), asigna cada puesto a su barrio (sjoin_nearest contra los 213
polígonos de CARTAGENA-BARRIOS.json), agrega votos por barrio y por localidad,
y clasifica el "semáforo político-electoral":

  - VERDE   (base Abelardo)  = votos Abelardo en 1V  -> hay que CUIDAR (testigos/turnout)
  - ROJO    (base Cepeda)    = votos Cepeda en 1V    -> petristas, NO persuadir
  - AMARILLO(disponible)     = votos a los demás candidatos -> universo persuadible 2V
       · afín a Abelardo (derecha/centro-derecha): Paloma, Lizcano, Botero, M. Uribe, Macollins, Matamoros
       · en disputa (centro):                      Fajardo, Claudia
       · afín a Cepeda (izquierda no-Cepeda):      Roy, Caicedo, Murillo
  - BLANCO                   = voto en blanco (protesta/indeciso, se reporta aparte)

Salidas en Bases de datos/output_abelardo_cartagena/:
  cartagena_resumen.json, cartagena_localidades.json, cartagena_barrios.json,
  Anexo_Cartagena_barrios.csv
"""
import json, csv, os, collections
import geopandas as gpd

ROOT = "/Users/ricardoruiz/ricardoruiz.co"
MASTER = f"{ROOT}/Bases de datos/output_pacto_1v_2026/master_2026_puesto.json"
GEO = f"{ROOT}/Bases de datos/output_pacto_1v_2026/geo/CARTAGENA-BARRIOS.json"
OUT = f"{ROOT}/Bases de datos/output_abelardo_cartagena"
os.makedirs(OUT, exist_ok=True)

DEP, MUN = "05", "001"

# bloques del amarillo (afinidad 2V)
PRO_ABE = ["paloma", "lizcano", "botero", "miguel_uribe", "macollins", "matamoros"]
DISPUTA = ["fajardo", "claudia"]
PRO_CEP = ["roy", "caicedo", "murillo"]
OTROS = PRO_ABE + DISPUTA + PRO_CEP  # amarillo completo

LOC_NOMBRE = {
    "LH": "Histórica y del Caribe Norte",
    "LV": "De la Virgen y Turística",
    "LI": "Industrial y de la Bahía",
}

# ---------------------------------------------------------------- carga puestos
master = json.load(open(MASTER))
ctg = [p for p in master if p["dep"] == DEP and p["mun"] == MUN]
print(f"Cartagena puestos: {len(ctg)}")

# GeoDataFrame de puestos
import pandas as pd
pdf = pd.DataFrame(ctg)
for c in ["lat", "lon"]:
    pdf[c] = pdf[c].astype(float)
gp = gpd.GeoDataFrame(pdf, geometry=gpd.points_from_xy(pdf.lon, pdf.lat), crs="EPSG:4326")

bar = gpd.read_file(GEO)[["NOMBRE", "LOC", "geometry"]].to_crs("EPSG:4326")
bar = bar.rename(columns={"NOMBRE": "NB"})

# asignar puesto -> barrio que lo contiene (o el mas cercano), en CRS proyectado
# para que la distancia 'nearest' sea metrica y no en grados.
PROJ = "EPSG:3857"
gp_p = gp.to_crs(PROJ)
bar_p = bar.to_crs(PROJ)
j = gpd.sjoin_nearest(gp_p, bar_p[["NB", "LOC", "geometry"]], how="left")
j = j[~j.index.duplicated(keep="first")]
print(f"puestos asignados a barrio: {j['NB'].notna().sum()} / {len(j)}")


def blank_agg():
    d = {k: 0 for k in (["cepeda", "abelardo"] + OTROS +
                        ["votos_blanco", "votos_nulos", "votos_no_marcados",
                         "total_votos_urna", "pot"])}
    d["puestos"] = 0
    return d


def add(dst, p):
    for k in (["cepeda", "abelardo"] + OTROS +
              ["votos_blanco", "votos_nulos", "votos_no_marcados",
               "total_votos_urna", "pot"]):
        dst[k] += int(p.get(k, 0) or 0)
    dst["puestos"] += 1


# ---------------------------------------------------------- agregacion barrio
barrios = collections.defaultdict(blank_agg)
barrio_loc = {}
for _, p in j.iterrows():
    nb = p["NB"] if isinstance(p["NB"], str) else "SIN BARRIO"
    add(barrios[nb], p)
    barrio_loc[nb] = p.get("LOC", "")


def metrics(d):
    """deriva metricas y clasificacion para un agregado de votos."""
    val = (d["total_votos_urna"] - d["votos_blanco"]
           - d["votos_nulos"] - d["votos_no_marcados"])
    val = max(val, 1)
    abe, cep = d["abelardo"], d["cepeda"]
    amarillo = sum(d[k] for k in OTROS)
    pro_abe = sum(d[k] for k in PRO_ABE)
    disputa = sum(d[k] for k in DISPUTA)
    pro_cep = sum(d[k] for k in PRO_CEP)
    abe_pct = 100 * abe / val
    cep_pct = 100 * cep / val
    ama_pct = 100 * amarillo / val
    margen = abe_pct - cep_pct  # negativo = Abelardo perdio
    # universo movible cosechable hacia Abelardo en 2V (estimacion conservadora):
    # todo el pro_abe + mitad de la disputa + el blanco como protesta no-petrista parcial
    cosecha_eff = pro_abe + 0.5 * disputa
    out = dict(
        puestos=d["puestos"], censo=d["pot"],
        votantes=d["total_votos_urna"], validos=val,
        abelardo=abe, cepeda=cep, amarillo=amarillo,
        blanco=d["votos_blanco"],
        pro_abe=pro_abe, disputa=disputa, pro_cep=pro_cep,
        abe_pct=round(abe_pct, 1), cep_pct=round(cep_pct, 1),
        ama_pct=round(ama_pct, 1), margen=round(margen, 1),
        cosecha_eff=round(cosecha_eff),
        ganador="Abelardo" if abe > cep else ("Cepeda" if cep > abe else "Empate"),
    )
    return out


def clasificar(m):
    """tier de prioridad para el operativo de 2V (logica del cliente)."""
    margen = m["margen"]
    ama_pct = m["ama_pct"]
    abe = m["abelardo"]
    # Bastion propio: Abelardo gano -> solo cuidar el voto
    if margen > 5:
        return ("Bastión Abelardo", "Cuidar el voto (testigos + movilización). No persuadir.")
    # Disputado: competido o perdido por poco -> maxima prioridad
    if margen >= -15:
        return ("Disputado", "Máxima prioridad: cosechar amarillos + cuidar verdes.")
    # Perdido pero cosechable: bolsa amarilla relevante o base verde grande
    if ama_pct >= 7 or abe >= 1500:
        return ("Perdido cosechable", "Cosecha selectiva de amarillos + asegurar turnout de verdes.")
    # Bastion Cepeda
    return ("Bastión Cepeda", "Recursos mínimos: solo testigos para proteger los pocos verdes.")


# ----------------------------------------------------------------- por barrio
rows = []
for nb, d in barrios.items():
    if nb == "SIN BARRIO":
        continue
    m = metrics(d)
    tier, accion = clasificar(m)
    loc = barrio_loc.get(nb, "")
    rows.append(dict(barrio=nb, loc=loc, loc_nombre=LOC_NOMBRE.get(loc, loc),
                     tier=tier, accion=accion, **m))

# orden: por "valor estratégico" = cosecha + base verde a cuidar, dentro de no-bastion-abe
def prio_key(r):
    bono = {"Disputado": 3, "Perdido cosechable": 2, "Bastión Cepeda": 1,
            "Bastión Abelardo": 0}[r["tier"]]
    movible = r["cosecha_eff"] + 0.4 * r["abelardo"]
    return (bono, movible)


rows.sort(key=prio_key, reverse=True)
for i, r in enumerate(rows, 1):
    r["rank"] = i

# ------------------------------------------------------------- por localidad
locs = collections.defaultdict(blank_agg)
for nb, d in barrios.items():
    if nb == "SIN BARRIO":
        continue
    loc = barrio_loc.get(nb, "")
    for k in d:
        locs[loc][k] += d[k]
loc_rows = []
for loc, d in locs.items():
    m = metrics(d)
    loc_rows.append(dict(loc=loc, loc_nombre=LOC_NOMBRE.get(loc, loc),
                         n_barrios=sum(1 for nb in barrios
                                       if barrio_loc.get(nb) == loc and nb != "SIN BARRIO"),
                         **m))
loc_rows.sort(key=lambda r: r["validos"], reverse=True)

# --------------------------------------------------------------- resumen city
tot = blank_agg()
for d in barrios.values():
    for k in d:
        tot[k] += d[k]
res = metrics(tot)
res["n_barrios_con_dato"] = sum(1 for nb in barrios if nb != "SIN BARRIO")
res["n_barrios_geo"] = len(bar)
res["puestos"] = len(ctg)
# desglose amarillo por candidato (ciudad)
res["amarillo_detalle"] = {k: tot[k] for k in OTROS}
# conteo de tiers
res["tiers"] = collections.Counter(r["tier"] for r in rows)

# ------------------------------------------------------------------- guardar
json.dump(res, open(f"{OUT}/cartagena_resumen.json", "w"), ensure_ascii=False, indent=2)
json.dump(loc_rows, open(f"{OUT}/cartagena_localidades.json", "w"), ensure_ascii=False, indent=2)
json.dump(rows, open(f"{OUT}/cartagena_barrios.json", "w"), ensure_ascii=False, indent=2)

# CSV anexo
cols = ["rank", "barrio", "loc_nombre", "tier", "ganador", "abe_pct", "cep_pct",
        "margen", "ama_pct", "abelardo", "cepeda", "amarillo", "pro_abe",
        "disputa", "blanco", "validos", "censo", "puestos", "accion"]
with open(f"{OUT}/Anexo_Cartagena_barrios.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(cols)
    for r in rows:
        w.writerow([r.get(c, "") for c in cols])

# ------------------------------------------------------------------- consola
print("\n=== RESUMEN CARTAGENA 1V ===")
print(f"válidos {res['validos']:,} · Abelardo {res['abe_pct']}% ({res['abelardo']:,}) "
      f"· Cepeda {res['cep_pct']}% ({res['cepeda']:,}) · amarillo {res['ama_pct']}% ({res['amarillo']:,})")
print(f"barrios con dato: {res['n_barrios_con_dato']} / {res['n_barrios_geo']}")
print("tiers:", dict(res["tiers"]))
print("\n=== LOCALIDADES ===")
for r in loc_rows:
    print(f"{r['loc_nombre']:32s} val {r['validos']:>7,} · Abe {r['abe_pct']:>5}% "
          f"· Cep {r['cep_pct']:>5}% · margen {r['margen']:>6} · barrios {r['n_barrios']}")
print("\n=== TOP 15 BARRIOS PRIORITARIOS ===")
for r in rows[:15]:
    print(f"{r['rank']:>3}. {r['barrio'][:26]:26s} [{r['tier'][:18]:18s}] "
          f"Abe {r['abe_pct']:>5}% Cep {r['cep_pct']:>5}% mrg {r['margen']:>6} "
          f"ama {r['amarillo']:>5,} verde {r['abelardo']:>6,}")
print(f"\nOK -> {OUT}")
