#!/usr/bin/env python3
# Agrega el preconteo 1V 2026 (mesa) a nivel LOCALIDAD de Bogotá.
# En Bogotá la columna `zona` del preconteo == localidad (01..20), y coincide
# 1:1 con LocCodigo de BOG-LOCALIDADX.json. 90/98 son puesto-censo (Corferias) +
# cárceles → no son localidades, van a un bucket `especiales` aparte.
#
# Salida: Bases de datos/output_prec_1v/bogota-localidades.json
# Subir a: congreso-2026/output/prec-1v/bogota-localidades.json (público)
import csv, json, os, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC  = os.path.join(ROOT, "Bases de datos", "nuevos archivos 1v 2026",
                    "PRECONTEO_1V_2026_MESA_nombres_corregidos.csv")
OUT  = os.path.join(ROOT, "Bases de datos", "output_prec_1v", "bogota-localidades.json")

# columna candidato -> slug (mismas claves que candColor() del frontend)
CAND = [
    ("Iván Cepeda", "cepeda"),
    ("Santiago Botero", "botero"),
    ("Abelardo De La Espriella", "espriella"),
    ("Mauricio Lizcano", "lizcano"),
    ("Miguel Uribe", "uribe"),
    ("Sondra Macollins", "macollins"),
    ("Roy Barreras", "barreras"),
    ("Carlos Caicedo", "caicedo"),
    ("Gustavo Matamoros", "matamoros"),
    ("Paloma Valencia", "valencia"),
    ("Sergio Fajardo", "fajardo"),
    ("Gilberto Murillo", "murillo"),
    ("Claudia López", "lopez"),
]
# nombres oficiales de localidad por código (referencia; el frontend usa LocNombre del geo)
LOC_NOMBRE = {
    "01":"Usaquén","02":"Chapinero","03":"Santa Fe","04":"San Cristóbal","05":"Usme",
    "06":"Tunjuelito","07":"Bosa","08":"Kennedy","09":"Fontibón","10":"Engativá",
    "11":"Suba","12":"Barrios Unidos","13":"Teusaquillo","14":"Los Mártires",
    "15":"Antonio Nariño","16":"Puente Aranda","17":"La Candelaria","18":"Rafael Uribe Uribe",
    "19":"Ciudad Bolívar","20":"Sumapaz",
}

def new_bucket():
    return {"mesas":0, "blanco":0, "nulos":0, "no_marcados":0,
            "votos":{slug:0 for _,slug in CAND}}

locs = {}            # zona(2dig) -> bucket  (solo 01..20)
especiales = new_bucket()
ciudad = new_bucket()

with open(SRC, newline="", encoding="utf-8-sig") as f:
    r = csv.reader(f)
    header = next(r)
    # índices de candidatos por nombre exacto del header
    idx = {}
    for nombre, slug in CAND:
        idx[slug] = header.index(nombre)
    i_blanco = header.index("votos_blanco")
    i_nulos  = header.index("votos_nulos")
    i_nomarc = header.index("votos_no_marcados")
    for row in r:
        if not row or len(row) < 6: continue
        dep = row[0].strip().strip('"')
        mun = row[1].strip().strip('"')
        if dep != "16" or mun != "001": continue
        zona = row[2].strip().strip('"').zfill(2)
        def gi(i):
            try: return int(row[i] or 0)
            except: return 0
        target = locs.setdefault(zona, new_bucket()) if zona in LOC_NOMBRE else especiales
        for slug in idx:
            v = gi(idx[slug]); target["votos"][slug]+=v; ciudad["votos"][slug]+=v
        for key,i in (("blanco",i_blanco),("nulos",i_nulos),("no_marcados",i_nomarc)):
            v = gi(i); target[key]+=v; ciudad[key]+=v
        target["mesas"]+=1; ciudad["mesas"]+=1

def finalize(b, cod=None):
    validos = sum(b["votos"].values())
    base = validos + b["blanco"]            # válidos + blanco (convención de la página)
    win_slug, win_v = None, -1
    for _,slug in CAND:
        if b["votos"][slug] > win_v: win_slug, win_v = slug, b["votos"][slug]
    win_name = next(n for n,s in CAND if s==win_slug)
    out = {
        "mesas": b["mesas"], "blanco": b["blanco"], "nulos": b["nulos"],
        "no_marcados": b["no_marcados"], "validos": validos, "base": base,
        "votos": b["votos"],
        "winner": win_name, "winner_slug": win_slug,
        "winner_pct": round(100*win_v/base, 2) if base else 0,
    }
    if cod: out["nombre"] = LOC_NOMBRE.get(cod, cod)
    return out

data = {
    "fuente": "Preconteo Registraduría · 1ª vuelta 31-may-2026 (snapshot final corregido)",
    "nivel": "localidad",
    "ciudad": "Bogotá D.C.",
    "candidatos": [{"nombre":n, "slug":s} for n,s in CAND],
    "localidades": {cod: finalize(locs[cod], cod) for cod in sorted(locs)},
    "especiales": finalize(especiales),   # 90 Corferias/censo + 98 cárceles (no en mapa)
    "ciudad_total": finalize(ciudad),
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",",":"))

# Resumen de control
print("localidades:", len(data["localidades"]))
print("ciudad mesas:", ciudad["mesas"], "| especiales mesas:", especiales["mesas"])
ct = data["ciudad_total"]
print("ciudad válidos+blanco:", ct["base"], "| ganador ciudad:", ct["winner"], ct["winner_pct"], "%")
for cod in sorted(data["localidades"]):
    L=data["localidades"][cod]
    print(f"  {cod} {L['nombre']:<20} mesas={L['mesas']:>4} base={L['base']:>7} win={L['winner']:<26} {L['winner_pct']:>5}%")
print("OUT:", OUT, os.path.getsize(OUT), "bytes")
