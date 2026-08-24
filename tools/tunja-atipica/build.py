#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backbone de datos para la elección atípica a la Alcaldía de Tunja (26-jul-2026).

Genera un JSON único que el frontend (mapa público + capa B2B) consume:
  - Alcaldías históricas 2011/2015/2019/2023 por PUESTO y por BARRIO (ganador + votos).
  - Presidencial 2026 1V y 2V por PUESTO y por BARRIO (Cepeda vs Abelardo + 13 cands 1V).
  - Censo electoral por puesto (potencial, mesas) + abstención por elección.
  - Asignación puesto -> barrio catastral por punto-en-polígono (PIP) contra TUNJAX.json.

Unidad estable = PUESTO (26 en Tunja). El barrio es capa visual: la mayoría de los 184
barrios catastrales no tienen puesto propio, así que se colorean SOLO los barrios que
contienen un puesto (con dato directo). No hay relleno de vecino en los agregados.

Códigos Registraduría: Boyacá COD_DDE=7, Tunja COD_MME=1, ALCALDE COD_COR=3.
pcode de cruce = dep(2)+mun(3)+zona(2)+puesto(2) = 070010302.
"""
import csv, json, os, sys
from collections import defaultdict
from shapely.geometry import shape, Point
from shapely.strtree import STRtree

ROOT = "/Users/ricardoruiz/ricardoruiz.co"
GCS  = os.path.join(ROOT, "Bases de datos/FINAL SUBIDA GCS")
GEO  = os.path.join(ROOT, "CIUDADES/TUNJA/TUNJAX.json")
GEOREF = os.path.join(ROOT, "Bases de datos/PUESTOS_GEOREF.csv")
MASTER = os.path.join(ROOT, "Bases de datos/output_2v/master_unificado_puesto.json")
OUT  = os.path.join(ROOT, "Bases de datos/output_tunja/tunja-electoral.json")

DEP, MUN = "7", "1"            # Boyacá / Tunja (sin padding, como vienen en el GCS)
COR_ALCALDE = "3"
TER_YEARS = {2011: "GCS_2011TER.csv", 2015: "GCS_2015TER.csv",
             2019: "GCS_2019TER.csv", 2023: "GCS_2023TER.csv"}

ESPECIALES = {"996": "blanco", "997": "nulos", "998": "no_marcados", "999": "no_marcados"}

def is_especial(cod_can, des_can):
    if cod_can in ESPECIALES:
        return True
    d = (des_can or "").upper()
    return ("BLANCO" in d) or ("NULO" in d) or ("NO MARCAD" in d)

def pcode(zz, pp):
    return f"07001{int(zz):02d}{int(pp):02d}"

# ---------------------------------------------------------------- 1. GEO barrios
def load_barrios():
    gj = json.load(open(GEO))
    polys, names = [], []
    for ft in gj["features"]:
        nm = (ft["properties"].get("Nombre") or "").strip()
        try:
            g = shape(ft["geometry"])
        except Exception:
            continue
        if not g.is_valid:
            g = g.buffer(0)
        polys.append(g)
        names.append(nm if nm else None)
    tree = STRtree(polys)
    return gj, polys, names, tree

def barrio_of(tree, polys, names, lon, lat):
    """Devuelve (idx_poligono, nombre) del barrio que contiene el punto, o (None,None)."""
    pt = Point(lon, lat)
    idxs = tree.query(pt)
    for i in idxs:
        if polys[i].contains(pt):
            return int(i), names[i]
    # fallback: polígono más cercano por centroide (solo si el punto cae en un hueco)
    best, bd = None, 1e9
    for i in idxs:
        d = polys[i].distance(pt)
        if d < bd:
            bd, best = d, int(i)
    if best is not None and bd < 0.004:   # ~400 m
        return best, names[best]
    return None, None

# ---------------------------------------------------------------- 2. PUESTOS geo/censo
def load_puestos():
    puestos = {}
    with open(GEOREF, encoding="utf-8-sig") as f:
        rd = csv.DictReader(f, delimiter=";")
        for r in rd:
            if (r.get("DEPARTAMENTO") == "BOYACA" and r.get("MUNICIPIO") == "TUNJA"):
                code = (r.get("CÓDIGO COMPLETO") or "").strip()
                if not code:
                    continue
                try:
                    lat = float(r["LATITUD"]); lon = float(r["LONGITUD"])
                except Exception:
                    lat = lon = None
                puestos[code] = {
                    "pcode": code,
                    "zona": code[5:7], "puesto": code[7:9],
                    "nombre": (r.get("NOMBRE PUESTO") or "").strip(),
                    "barrio_georef": (r.get("BARRIO") or "").strip(),
                    "lat": lat, "lon": lon,
                    "mujeres": int(r.get("MUJERES") or 0),
                    "hombres": int(r.get("HOMBRES") or 0),
                    "mesas": int(r.get("MESAS") or 0),
                }
    return puestos

# ---------------------------------------------------------------- 3. TER alcaldías
def extract_ter(path):
    """Devuelve por puesto: {pcode: {cod_can: {'des','par','votos'}}} para ALCALDE Tunja."""
    per = defaultdict(lambda: defaultdict(lambda: {"des": "", "par": "", "votos": 0}))
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        rd = csv.reader(f, delimiter=";")
        header = next(rd)
        col = {h.strip().lstrip("﻿"): i for i, h in enumerate(header)}
        cDCOR, cDDE, cMME = col["DES_COR"], col["COD_DDE"], col["COD_MME"]
        cZZ, cPP = col["COD_ZZ"], col["COD_PP"]
        cPAR, cDPAR = col["COD_PAR"], col["DES_PAR"]
        cCAN, cDCAN, cVOT = col["COD_CAN"], col["DES_CAN"], col["NUM_VOT"]
        cmax = max(cDCOR, cDDE, cMME, cZZ, cPP, cPAR, cDPAR, cCAN, cDCAN, cVOT)
        for row in rd:
            if len(row) <= cmax:
                continue
            # ALCALDE (2015/19/23) o ALCALDIA (2011); excluye GOBERNADOR/ASAMBLEA/CONCEJO/JAL
            if not row[cDCOR].strip().upper().startswith("ALCAL"):
                continue
            if row[cDDE] != DEP or row[cMME] != MUN:
                continue
            pc = pcode(row[cZZ], row[cPP])
            can = row[cCAN].strip()
            try:
                v = int(row[cVOT] or 0)
            except ValueError:
                v = 0
            d = per[pc][can]
            d["des"] = row[cDCAN].strip()
            d["par"] = row[cDPAR].strip()
            d["votos"] += v
    return per

def summarize_alcaldia(per_puesto):
    """Winner por puesto + totales por candidato. Excluye blanco/nulos/no-marcados del ganador."""
    by_puesto = {}
    nac = defaultdict(lambda: {"des": "", "par": "", "votos": 0})
    for pc, cands in per_puesto.items():
        validos = 0
        best = None
        cand_list = []
        blanco = 0
        especial_tot = 0
        for can, d in cands.items():
            if is_especial(can, d["des"]):
                especial_tot += d["votos"]
                if "BLANCO" in (d["des"] or "").upper() or can == "996":
                    blanco += d["votos"]
                continue
            validos += d["votos"]
            cand_list.append((can, d))
            n = nac[can]; n["des"] = d["des"]; n["par"] = d["par"]; n["votos"] += d["votos"]
        for can, d in cand_list:
            if best is None or d["votos"] > best[1]["votos"]:
                best = (can, d)
        total = validos + especial_tot
        if best:
            by_puesto[pc] = {
                "winner_can": best[0], "winner": best[1]["des"], "winner_par": best[1]["par"],
                "winner_votos": best[1]["votos"],
                "winner_pct": round(100*best[1]["votos"]/validos, 1) if validos else 0,
                "validos": validos, "blanco": blanco, "total": total,
                "cands": {can: {"des": d["des"], "par": d["par"], "votos": d["votos"]}
                          for can, d in cand_list},
            }
    nac_sorted = sorted(nac.items(), key=lambda kv: -kv[1]["votos"])
    return by_puesto, [{"can": c, "des": d["des"], "par": d["par"], "votos": d["votos"]}
                       for c, d in nac_sorted]

# ---------------------------------------------------------------- 4. Presidencial (master)
def load_presidencial(puestos):
    d = json.load(open(MASTER))
    tun = {x["pcode"]: x for x in d if x["pcode"].startswith("07001")}
    pres = {}
    for pc, x in tun.items():
        pres[pc] = {
            "cep1": x.get("cep1", 0), "abe1": x.get("abe1", 0),
            "cep2": x.get("cep2", 0), "abe2": x.get("abe2", 0),
            "urna1": x.get("urna1", 0), "urna2": x.get("urna2", 0),
            "v1": x.get("v1", {}), "pot": x.get("pot", 0),
        }
    return pres

# ---------------------------------------------------------------- 5. Táctico (B2B neutral)
def compute_tactico(puestos, pres, elecciones):
    """Métricas tácticas candidato-neutrales por puesto para demo B2B.
    peso electoral · abstención de la última alcaldía (bolsón movilizable) ·
    competitividad (margen del ganador) · inclinación izq/der (presidencial 2V)."""
    A23 = elecciones.get("alcaldia_2023", {}).get("by_puesto", {})
    censo_tot = sum(p["mujeres"] + p["hombres"] for p in puestos.values())
    per = {}
    for pc, p in puestos.items():
        censo = p["mujeres"] + p["hombres"]
        if censo == 0:
            continue
        a = A23.get(pc)
        votantes = a["total"] if a else None
        abst = (censo - votantes) if votantes is not None else None
        margen = None
        if a and a["validos"]:
            vs = sorted((c["votos"] for c in a["cands"].values()), reverse=True)
            if len(vs) >= 2:
                margen = round(100 * (vs[0] - vs[1]) / a["validos"], 1)
        lean = None
        pr = pres.get(pc)
        if pr and (pr["cep2"] + pr["abe2"]) > 0:
            lean = round(100 * pr["cep2"] / (pr["cep2"] + pr["abe2"]), 1)
        per[pc] = {
            "nombre": p["nombre"], "zona": p["zona"], "puesto": p["puesto"],
            "censo": censo, "peso_pct": round(100 * censo / censo_tot, 2),
            "votantes_23": votantes, "abst_23": abst,
            "abst_pct": round(100 * abst / censo, 1) if abst is not None else None,
            "margen_23": margen, "lean_cep2": lean,
            "lat": p["lat"], "lon": p["lon"], "mesas": p["mesas"],
        }
    # ranking por peso para el "top puestos que deciden" + concentración
    order = sorted(per.items(), key=lambda kv: -kv[1]["censo"])
    acc = 0
    conc = {}
    for i, (pc, m) in enumerate(order, 1):
        acc += m["censo"]
        conc[str(i)] = round(100 * acc / censo_tot, 1)
    votantes_tot = sum((m["votantes_23"] or 0) for m in per.values())
    return {
        "censo_total": censo_tot,
        "votantes_alcaldia_2023": votantes_tot,
        "abstencion_2023_pct": round(100 * (censo_tot - votantes_tot) / censo_tot, 1),
        "por_puesto": per,
        "ranking_peso": [pc for pc, _ in order],
        "concentracion_acumulada": conc,   # {n: % del censo en los n puestos más grandes}
    }


# ---------------------------------------------------------------- MAIN
def main():
    gj, polys, names, tree = load_barrios()
    puestos = load_puestos()
    print(f"[geo] {len(polys)} polígonos, {sum(1 for n in names if n)} con nombre")
    print(f"[puestos] {len(puestos)} puestos en Tunja")

    # PIP puesto -> barrio
    for pc, p in puestos.items():
        if p["lat"] is None:
            p["barrio_idx"], p["barrio"] = None, None
            continue
        idx, nm = barrio_of(tree, polys, names, p["lon"], p["lat"])
        p["barrio_idx"] = idx
        p["barrio"] = nm or p["barrio_georef"]
    asignados = sum(1 for p in puestos.values() if p["barrio_idx"] is not None)
    print(f"[pip] {asignados}/{len(puestos)} puestos cayeron en un polígono de barrio")

    # Asignación barrio -> puesto más cercano (para colorear TODO el mapa).
    # Un barrio es "directo" si contiene un puesto; si no, hereda el puesto más cercano
    # por centroide (relleno, se pinta translúcido). Solo puestos urbanos (zona 01-03).
    urb = {pc: p for pc, p in puestos.items()
           if p["lat"] is not None and p["zona"] in ("01", "02", "03")}
    direct_by_poly = defaultdict(list)   # poly_idx -> [pcode,...]
    for pc, p in urb.items():
        if p["barrio_idx"] is not None:
            direct_by_poly[p["barrio_idx"]].append(pc)
    barrio_puesto = {}  # poly_idx -> {"pcode","is_direct","nombre"}
    for i, g in enumerate(polys):
        c = g.centroid
        if i in direct_by_poly:
            # el puesto con más mesas dentro del polígono manda el color directo
            pc = max(direct_by_poly[i], key=lambda x: urb[x]["mesas"])
            barrio_puesto[i] = {"pcode": pc, "is_direct": True, "nombre": names[i]}
        else:
            best, bd = None, 1e9
            for pc, p in urb.items():
                d = (c.x - p["lon"])**2 + (c.y - p["lat"])**2
                if d < bd:
                    bd, best = d, pc
            barrio_puesto[i] = {"pcode": best, "is_direct": False, "nombre": names[i]}
    ndir = sum(1 for v in barrio_puesto.values() if v["is_direct"])
    print(f"[barrio] {len(barrio_puesto)} polígonos asignados a puesto ({ndir} directos, {len(barrio_puesto)-ndir} relleno)")

    # Alcaldías (con cache para no re-streamear los GCS de 1.7-3 GB)
    CACHE = os.path.join(os.path.dirname(OUT), "_cache_ter.json")
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    elecciones = {}
    for year, fn in TER_YEARS.items():
        path = os.path.join(GCS, fn)
        if not os.path.exists(path):
            print(f"[skip] {fn} no existe"); continue
        ck = f"alcaldia_{year}"
        if ck in cache:
            print(f"[ter] {fn} desde cache")
            per = {pc: {c: dict(d) for c, d in cs.items()} for pc, cs in cache[ck].items()}
        else:
            print(f"[ter] procesando {fn} ...")
            per = extract_ter(path)
            cache[ck] = per
            json.dump(cache, open(CACHE, "w"), ensure_ascii=False)
        by_puesto, nac = summarize_alcaldia(per)
        # totales de control
        tot = sum(bp["validos"] for bp in by_puesto.values())
        elecciones[f"alcaldia_{year}"] = {
            "tipo": "alcaldia", "anio": year,
            "by_puesto": by_puesto, "nacional": nac[:15],
            "total_validos": tot,
        }
        top = nac[0] if nac else {"des": "—", "votos": 0}
        print(f"       {len(by_puesto)} puestos, válidos={tot:,}, top={top.get('des')} ({top.get('votos',0):,})")

    pres = load_presidencial(puestos)
    tactico = compute_tactico(puestos, pres, elecciones)

    out = {
        "v": "2026-07-05", "municipio": "Tunja", "cod": "07-001",
        "eleccion_atipica": {"fecha": "2026-07-26", "cargo": "Alcalde", "motivo": "nulidad elección Mikhail Krasnov 2024-2027"},
        "puestos": puestos,
        "barrio_puesto": {str(i): v for i, v in barrio_puesto.items()},
        "presidencial_2026": pres,
        "alcaldias": elecciones,
        "tactico": tactico,
        "geo_url": "CIUDADES/TUNJA/TUNJAX.json",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False)
    print(f"[out] {OUT}  ({os.path.getsize(OUT)/1024:.0f} KB)")

if __name__ == "__main__":
    main()
