#!/usr/bin/env python3
"""fem_mindefensa.py — feminicidio desde MinDefensa (datos.gov.co, m8fd-ahd9,
`spoa_caracterizacion='FEMINICIDIO'`), para el observatorio de la mujer.

Por qué existe: la serie propia (artículo 104A en `DESCRIPCION_CONDUCTA` de la
base SIEDCO) se corta en 2023 — los lotes 2024-2026 no traen el artículo penal
en homicidios. MinDefensa publica el mismo registro con la marca de
feminicidio hasta el último mes. Se usa como serie principal 2015-2026; la
propia queda al lado como control (coinciden salvo 2017 y 2022-2023).

    from fem_mindefensa import feminicidio
    F = feminicidio()      # usa la caché de build_mindefensa.py
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_mindefensa import soql, n  # noqa  (misma caché en PONAL-SIEDCO/mindefensa-raw)

DS = "m8fd-ahd9"
W = "spoa_caracterizacion='FEMINICIDIO'"
CORTE = "2026-08-31"


def feminicidio():
    anio, dep, mun, mun_nom = defaultdict(int), defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int)), {}
    for r in soql(DS, {"$select": "date_extract_y(fecha_hecho) as a,cod_depto,cod_muni,municipio,sum(cantidad) as n",
                       "$where": W, "$group": "a,cod_depto,cod_muni,municipio", "$limit": 50000}):
        if not r.get("a"):
            continue
        a, q = r["a"], n(r["n"])
        anio[a] += q
        dep[r.get("cod_depto") or "?"][a] += q
        mun[r.get("cod_muni") or "?"][a] += q
        mun_nom[r.get("cod_muni") or "?"] = (r.get("municipio") or "").title()
    def por(campo):
        out = defaultdict(lambda: defaultdict(int))
        for r in soql(DS, {"$select": f"date_extract_y(fecha_hecho) as a,{campo} as k,sum(cantidad) as n",
                           "$where": W, "$group": "a,k", "$limit": 5000}):
            if r.get("a"):
                out[r.get("k") or "SIN DATO"][r["a"]] += n(r["n"])
        return {k: dict(v) for k, v in out.items()}
    mes = {}
    for r in soql(DS, {"$select": "date_trunc_ym(fecha_hecho) as m,sum(cantidad) as n",
                       "$where": W + " AND fecha_hecho >= '2024-01-01T00:00:00'", "$group": "m", "$order": "m", "$limit": 100}):
        if r.get("m"):
            mes[r["m"][:7]] = n(r["n"])
    return {"fuente": "MinDefensa · datos.gov.co m8fd-ahd9 (spoa_caracterizacion = FEMINICIDIO)",
            "corte": CORTE, "anio": dict(sorted(anio.items())),
            "depto": {d: dict(sorted(v.items())) for d, v in dep.items()},
            "mun": {m: dict(sorted(v.items())) for m, v in mun.items()}, "mun_nom": mun_nom,
            "arma": por("arma_medio"), "zona": por("zona"), "mes": mes}


if __name__ == "__main__":
    F = feminicidio()
    print(F["anio"])
    print("municipios", len(F["mun"]), "· meses", list(F["mes"].items())[-3:])
    print({k: v.get("2025") for k, v in F["arma"].items()})
