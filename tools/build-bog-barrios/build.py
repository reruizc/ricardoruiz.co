#!/usr/bin/env python3
"""
build-bog-barrios/build.py

Descarga el Sector Catastral de Bogotá D.C. (1,217 features) desde el
ArcGIS REST del Catastro Distrital, filtra los urbanos (SCATIPO=0, ~1,001
barrios con nombre social tipo "GALERIAS", "CEDRITOS") y los enriquece
con la localidad correspondiente mediante spatial join contra
BOG-LOCALIDADX.json.

Output:
  CIUDADES/BOGOTA/BOG-BARRIOS-CATASTRALES.geojson  (geometrías completas)

Pipeline siguiente (otro script): generar agregados de proyección por
barrio cruzando con los puestos de votación (lat/lon).

Sin dependencias externas — stdlib pura.
"""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "build-bog-upl"))
from build import point_in_geom, bbox_of_geom  # noqa: E402

ENDPOINT = (
    "https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services/catastro/"
    "sectorcatastral/MapServer/0/query"
)
LOCALIDADES = ROOT / "CIUDADES" / "BOGOTA" / "BOG-LOCALIDADX.json"
OUT = ROOT / "CIUDADES" / "BOGOTA" / "BOG-BARRIOS-CATASTRALES.geojson"


def fetch_page(offset, page_size=1000):
    url = (
        f"{ENDPOINT}?where=1%3D1"
        f"&outFields=SCACODIGO,SCANOMBRE,SCATIPO"
        f"&f=geojson&outSR=4326&returnGeometry=true"
        f"&resultOffset={offset}&resultRecordCount={page_size}"
    )
    with urllib.request.urlopen(url) as r:
        return json.load(r)


def centroid_of_geom(geom):
    """Centroide simple: promedio de vértices del outer ring más grande."""
    if geom["type"] == "Polygon":
        rings = geom["coordinates"]
    elif geom["type"] == "MultiPolygon":
        rings = max(geom["coordinates"], key=lambda p: len(p[0]) if p else 0)
    else:
        return None
    if not rings or not rings[0]:
        return None
    outer = rings[0]
    n = len(outer)
    return (sum(p[0] for p in outer) / n, sum(p[1] for p in outer) / n)


def main():
    # ── 1. Descarga paginada ──
    print("→ Descargando Sector Catastral Bogotá (ArcGIS REST)…")
    all_features = []
    offset = 0
    while True:
        data = fetch_page(offset)
        feats = data.get("features", [])
        if not feats:
            break
        all_features.extend(feats)
        print(f"  página offset={offset}: {len(feats)} features (total: {len(all_features)})")
        if not data.get("exceededTransferLimit") and not data.get("properties", {}).get("exceededTransferLimit"):
            break
        offset += len(feats)
        if offset > 5000:
            print("  ⚠ corte de seguridad a 5000 — revisar paginación")
            break
    print(f"  ✓ {len(all_features)} features totales")

    # ── 2. Filtra urbanos (SCATIPO=0) ──
    urbanos = [f for f in all_features if f["properties"].get("SCATIPO") == 0]
    print(f"→ Filtro urbanos (SCATIPO=0): {len(urbanos)} barrios")

    # ── 3. Spatial join con localidades ──
    print("→ Cargando localidades…")
    localidades = json.loads(LOCALIDADES.read_text(encoding="utf-8"))
    loc_feats = localidades["features"]

    sin_loc = []
    for f in urbanos:
        c = centroid_of_geom(f["geometry"])
        if not c:
            f["properties"]["CODIGO_LOCALIDAD"] = None
            f["properties"]["NOMBRE_LOCALIDAD"] = None
            sin_loc.append(f["properties"].get("SCANOMBRE"))
            continue
        match_codigo = None
        match_nombre = None
        for lf in loc_feats:
            if point_in_geom(c, lf["geometry"]):
                match_codigo = lf["properties"].get("LocCodigo")
                match_nombre = lf["properties"].get("LocNombre")
                break
        f["properties"]["CODIGO_LOCALIDAD"] = match_codigo
        f["properties"]["NOMBRE_LOCALIDAD"] = match_nombre
        if not match_codigo:
            sin_loc.append(f["properties"].get("SCANOMBRE"))

    if sin_loc:
        print(f"  ⚠ {len(sin_loc)} barrios sin localidad (centroide fuera): {sin_loc[:5]}{'…' if len(sin_loc)>5 else ''}")
    else:
        print(f"  ✓ Todos los barrios con localidad")

    # Normaliza nombres: TODO MAYÚSCULA → Title Case
    for f in urbanos:
        p = f["properties"]
        nom = p.get("SCANOMBRE") or ""
        if nom.isupper() and len(nom) > 3:
            p["SCANOMBRE"] = nom.title()
        # Limpia keys redundantes en el output
        f["properties"] = {
            "codigo": p.get("SCACODIGO"),
            "nombre": p.get("SCANOMBRE"),
            "loc_codigo": p.get("CODIGO_LOCALIDAD"),
            "loc_nombre": p.get("NOMBRE_LOCALIDAD"),
        }

    # ── 4. Output ──
    out = {
        "type": "FeatureCollection",
        "name": "BOG-BARRIOS-CATASTRALES",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": urbanos,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size_kb = OUT.stat().st_size / 1024
    print(f"\n✓ {OUT.relative_to(ROOT)}  ({size_kb:.0f} KB, {len(urbanos)} barrios)")

    # Resumen por localidad
    by_loc = {}
    for f in urbanos:
        loc = f["properties"]["loc_nombre"] or "(sin localidad)"
        by_loc[loc] = by_loc.get(loc, 0) + 1
    print("\nBarrios por localidad:")
    for loc, n in sorted(by_loc.items(), key=lambda x: -x[1])[:10]:
        print(f"  {n:>4}  {loc}")


if __name__ == "__main__":
    main()
