#!/usr/bin/env python3
"""Resuelve el municipio de nacimiento a DEPARTAMENTO y calcula congresistas
nacidos por departamento per capita.

El problema: Congreso Visible solo da el MUNICIPIO ("Florencia", "Barbosa"), y
65 nombres de municipio se repiten entre departamentos. SIGEP y la investigacion
dirigida si traen departamento explicito, asi que solo hay que desambiguar los CV.

Cascada de desambiguacion:
  1. nombre unico en DIVIPOLA          -> directo
  2. alias ortografico conocido        -> directo
  3. ambiguo: un solo candidato es ciudad grande (censo electoral >= 50.000)
  4. ambiguo: un candidato coincide con la circunscripcion por la que fue electo
  5. ambiguo sin resolver              -> se reporta y NO entra al conteo
"""
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "Bases de datos"
OUT = DATA / "congresistas-nacimiento"


def n(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", s.upper())).strip()


# variantes ortograficas de Congreso Visible que no calzan con DIVIPOLA
ALIAS_MUN = {
    "BOGOTA": ("16", "Bogota D.C."),
    "BOGOTA D C": ("16", "Bogota D.C."),
    "CARMEN DE BOLIVAR": ("13", "Bolivar"),
    "EL BORDO": ("11", "Cauca"),            # cabecera de Patia
    "ITSMINA": ("14", "Choco"),             # Istmina
    "SANTA CRUZ DE MONPOX": ("13", "Bolivar"),
    "SAN ANTONIO DEL PALMITO": ("29", "Sucre"),
    "ENTRERIOS": ("01", "Antioquia"),
    "ARIGUANI": ("21", "Magdalena"),
}

# municipios ambiguos resueltos por verificacion directa en prensa/perfil (nombre -> depto)
OVERRIDE_DEP = {
    "Catherine Juvinao Clavijo": "Cesar",          # La Paz, Cesar (lasillavacia / eltiempo)
    "Ariel Fernando Avila Martinez": "Cundinamarca",  # San Bernardo, Cundinamarca (SIGEP/wiki)
    "Hernan Dario Cadavid Marquez": "Antioquia",   # Barbosa, Antioquia (wikipedia / camara)
    "Luis Eduardo Diaz Mateus": "Santander",       # La Paz, Santander (lasillavacia)
    "Juan Fernando Espinal Ramirez": "Antioquia",  # Jerico, Antioquia (camara / CD)
    "Camilo Andres Torres Villalba": "Atlantico",  # Puerto Colombia, Atlantico (elcolombiano)
    "Juan Pablo Salazar Rivera": "Cauca",          # Suarez, Cauca (congreso a la mano)
}

# nombre de departamento (cualquier fuente) -> nombre DANE 2026
DEP_DANE = {
    "BOGOTA": "BOGOTA, D.C.", "BOGOTA D C": "BOGOTA, D.C.",
    "BOGOTA DC": "BOGOTA, D.C.", "DISTRITO CAPITAL": "BOGOTA, D.C.",
    "SAN ANDRES": "ARCHIPIELAGO DE SAN ANDRES, PROVIDENCIA Y SANTA CATALINA",
    "ARCHIPIELAGO DE SAN ANDRES PROVIDENCIA Y SANTA CATALINA":
        "ARCHIPIELAGO DE SAN ANDRES, PROVIDENCIA Y SANTA CATALINA",
    "SAN ANDRES Y PROVIDENCIA":
        "ARCHIPIELAGO DE SAN ANDRES, PROVIDENCIA Y SANTA CATALINA",
    "SAN ANDRES PROVIDENCIA Y SANTA CATALINA":
        "ARCHIPIELAGO DE SAN ANDRES, PROVIDENCIA Y SANTA CATALINA",
    "VALLE": "VALLE DEL CAUCA", "NORTE DE SAN": "NORTE DE SANTANDER",
    "NARINO": "NARINO", "CAQUETA": "CAQUETA", "CHOCO": "CHOCO",
    "GUAJIRA": "LA GUAJIRA", "ATLANTICO": "ATLANTICO",
}


_OVR_N = {n(k): v for k, v in OVERRIDE_DEP.items()}


def dep_dane(nombre: str) -> str:
    """Nombre de departamento -> llave canonica (la misma que usa el dict de poblacion,
    que se indexa con n()). Ojo: hay que normalizar tambien el VALOR del alias, si no
    'BOGOTA, D.C.' nunca calza con la llave n('Bogotá, D.C.') = 'BOGOTA D C'."""
    k = n(nombre)
    return n(DEP_DANE.get(k, k))


def cargar_divipola():
    dv = json.loads((DATA / "test-presidencial" / "divipola.json").read_text(encoding="utf-8"))
    idx = defaultdict(list)
    for d in dv["deptos"]:
        for m in d["muns"]:
            idx[n(m["nombre"])].append((d["cod"], d["nombre"], m["cod"]))
    return idx


def cargar_censo_mun():
    """censo electoral por (dep,mun) — proxy de tamano del municipio."""
    tot = Counter()
    with open(DATA / "COMUNAS_DATA.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f, delimiter=";"):
            try:
                tot[(r["dd"].zfill(2), r["mm"].zfill(3))] += int(r["total"])
            except (KeyError, ValueError):
                pass
    return tot


def cargar_pob_dane():
    import openpyxl
    wb = openpyxl.load_workbook(DATA / "DANE-AreaSexoEdadDep-2018-2050_VP.xlsx", read_only=True)
    ws = wb["PobDepartamentalxÁreaSexoEdad"]
    pop = {}
    for r in ws.iter_rows(min_row=9, max_col=5, values_only=True):
        if r[1] and str(r[2]) == "2026" and str(r[3]).strip() == "Total":
            pop[n(r[1])] = int(r[4])
    return pop


def main():
    idx = cargar_divipola()
    censo = cargar_censo_mun()
    pop = cargar_pob_dane()
    el = json.loads((OUT / "electos-nacimiento.json").read_text(encoding="utf-8"))

    sin_dato, sin_resolver, exterior = [], [], []
    for e in el:
        lugar = e.get("lugar_nacimiento")
        if not lugar:
            sin_dato.append(e)
            continue
        # fuentes que ya traen departamento (SIGEP / investigacion dirigida)
        if e.get("depto_nacimiento_fuente"):
            d = dep_dane(e["depto_nacimiento_fuente"])
            if d == "EXTERIOR" or "COLOMBIA" not in str(e.get("pais", "COLOMBIA")).upper():
                pass
            e["dep_nac"] = d
            e["dep_via"] = "fuente"
            continue
        ovr = _OVR_N.get(n(e["nombre"]))
        if ovr:
            e["dep_nac"] = dep_dane(ovr)
            e["dep_via"] = "override"
            continue
        k = n(lugar)
        if k in ALIAS_MUN:
            e["dep_nac"] = dep_dane(ALIAS_MUN[k][1])
            e["dep_via"] = "alias"
            continue
        cands = idx.get(k, [])
        if not cands:
            exterior.append(e)          # probablemente nacio fuera de Colombia
            continue
        if len(cands) == 1:
            e["dep_nac"] = dep_dane(cands[0][1])
            e["dep_via"] = "unico"
            continue
        # ambiguo -> ciudad grande
        grandes = [c for c in cands if censo.get((c[0], c[2]), 0) >= 50_000]
        if len(grandes) == 1:
            e["dep_nac"] = dep_dane(grandes[0][1])
            e["dep_via"] = "ambiguo/tamano"
            continue
        # ambiguo -> coincide con la circunscripcion
        circ = dep_dane(e.get("dep", ""))
        coin = [c for c in cands if dep_dane(c[1]) == circ]
        if len(coin) == 1:
            e["dep_nac"] = coin[0] and dep_dane(coin[0][1])
            e["dep_via"] = "ambiguo/circunscripcion"
            continue
        e["_cands"] = [c[1] for c in cands]
        sin_resolver.append(e)

    (OUT / "electos-nacimiento.json").write_text(
        json.dumps(el, ensure_ascii=False, indent=1), encoding="utf-8")

    con = [e for e in el if e.get("dep_nac")]
    print(f"resueltos {len(con)}/{len(el)} · sin dato {len(sin_dato)} · "
          f"sin match divipola {len(exterior)} · ambiguos sin resolver {len(sin_resolver)}")
    print("via:", Counter(e["dep_via"] for e in con))
    if exterior:
        print("\nSIN MATCH DIVIPOLA (revisar, probable exterior):")
        for e in exterior:
            print(f"  {e['nombre']:40} {e['lugar_nacimiento']}")
    if sin_resolver:
        print("\nAMBIGUOS SIN RESOLVER:")
        for e in sin_resolver:
            print(f"  {e['nombre']:40} {e['lugar_nacimiento']:18} {e['_cands']}")

    # ---- ranking per capita -------------------------------------------------
    cnt = Counter(e["dep_nac"] for e in con)
    cob = len(con) / len(el)
    print(f"\n{'DEPARTAMENTO':46} {'CONG':>4} {'POBLACION':>11} {'x1M':>7} {'HAB/CONG':>11}")
    filas = []
    for d, v in cnt.items():
        p = pop.get(d)
        if not p:
            print("  !! sin poblacion DANE:", d)
            continue
        filas.append((v / p * 1e6, d, v, p))
    for r, d, v, p in sorted(filas, reverse=True):
        print(f"{d:46} {v:4d} {p:11,d} {r:7.2f} {p//v:11,d}")
    faltan = sorted(set(pop) - set(cnt))
    print(f"\nsin ningun congresista nacido ahi ({len(faltan)}): {faltan}")
    print(f"\ncobertura: {cob*100:.1f}%  ({len(con)} de {len(el)} electos)")
    json.dump({"conteo": cnt, "poblacion": pop, "cobertura": cob},
              open(OUT / "ranking.json", "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
