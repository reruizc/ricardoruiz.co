#!/usr/bin/env python3
"""
build-bog-upl/build.py

One-shot tool. Descarga el Esri JSON oficial de Unidades de Planeamiento Local
(UPL) de Bogotá desde Datos Abiertos Bogotá, lo convierte a GeoJSON estándar
WGS84 y le inyecta la localidad a la que pertenece cada UPL mediante un
spatial join contra BOG-LOCALIDADX.json (centroide UPL → polígono localidad).

Output: CIUDADES/BOGOTA/BOG-UPL.geojson

Propiedades del GeoJSON resultante (por feature):
  - CODIGO_UPL  ("UPL13")
  - NOMBRE      ("Tintal")
  - SECTOR      ("Sector Sur Occidente")
  - VOCACION    ("Urbano-Rural" | "Urbano" | "Rural")
  - AREA_HA     1284.99
  - LocCodigo   "08"     ← inyectado por spatial join
  - LocNombre   "KENNEDY" ← inyectado por spatial join

Sin dependencias externas (stdlib + urllib). El Esri JSON ya viene en
WGS84 (wkid 4686), así que no hay reproyección.
"""
import json
import os
import urllib.request
from pathlib import Path

UPL_URL = (
    "https://datosabiertos.bogota.gov.co/dataset/"
    "808582fc-ffc8-4649-8428-7e1fd8d3820c/resource/"
    "a5c8c591-0708-420f-8eb7-9f3147e21c40/download/unidadplaneamientolocal.json"
)
ROOT = Path(__file__).resolve().parents[2]
LOCALIDADES = ROOT / "CIUDADES" / "BOGOTA" / "BOG-LOCALIDADX.json"
OUT = ROOT / "CIUDADES" / "BOGOTA" / "BOG-UPL.geojson"


def signed_area(ring):
    """Shoelace. >0 = CW (Esri outer), <0 = CCW (Esri hole)."""
    s = 0.0
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        s += (x2 - x1) * (y2 + y1)
    return s


def point_in_ring(pt, ring):
    """Ray casting. ring = lista de [x,y]."""
    x, y = pt
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-15) + xi):
            inside = not inside
        j = i
    return inside


def point_in_geom(pt, geom):
    """Point-in-polygon contra geometry GeoJSON (Polygon o MultiPolygon)."""
    if geom["type"] == "Polygon":
        rings = geom["coordinates"]
        if not rings:
            return False
        # Outer es primer ring; resto son holes.
        if not point_in_ring(pt, rings[0]):
            return False
        for hole in rings[1:]:
            if point_in_ring(pt, hole):
                return False
        return True
    if geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            if not poly:
                continue
            if point_in_ring(pt, poly[0]):
                in_hole = False
                for hole in poly[1:]:
                    if point_in_ring(pt, hole):
                        in_hole = True
                        break
                if not in_hole:
                    return True
        return False
    return False


def bbox_of_geom(geom):
    """Bounding box (minx, miny, maxx, maxy) de Polygon/MultiPolygon."""
    minx, miny = float("inf"), float("inf")
    maxx, maxy = float("-inf"), float("-inf")
    if geom["type"] == "Polygon":
        polys = [geom["coordinates"]]
    elif geom["type"] == "MultiPolygon":
        polys = geom["coordinates"]
    else:
        return None
    for poly in polys:
        if not poly or not poly[0]:
            continue
        for x, y in poly[0]:
            if x < minx: minx = x
            if y < miny: miny = y
            if x > maxx: maxx = x
            if y > maxy: maxy = y
    return (minx, miny, maxx, maxy)


def localidades_solape(upl_geom, localidades, min_pct=5.0):
    """Calcula el % de solape de la UPL con cada localidad.

    Las UPL son transversales a las localidades por diseño del POT 555/2021,
    así que devolvemos un array ordenado por % de solape descendente. La UI
    decide si mostrar solo la principal o el split completo.

    Retorna lista [{LocCodigo, LocNombre, pct}], filtrando solapes < min_pct%.
    """
    bb = bbox_of_geom(upl_geom)
    if not bb:
        return []
    minx, miny, maxx, maxy = bb
    N = 60  # 60×60 = 3600 muestras
    dx = (maxx - minx) / (N - 1)
    dy = (maxy - miny) / (N - 1)

    counts = {}
    name_by_code = {}
    total_in = 0
    for i in range(N):
        x = minx + i * dx
        for j in range(N):
            y = miny + j * dy
            if not point_in_geom((x, y), upl_geom):
                continue
            total_in += 1
            for lf in localidades["features"]:
                if point_in_geom((x, y), lf["geometry"]):
                    cod = lf["properties"].get("LocCodigo")
                    counts[cod] = counts.get(cod, 0) + 1
                    name_by_code[cod] = lf["properties"].get("LocNombre")
                    break

    if not total_in:
        return []
    out = []
    for cod, c in counts.items():
        pct = 100.0 * c / total_in
        if pct >= min_pct:
            out.append({
                "LocCodigo": cod,
                "LocNombre": name_by_code[cod],
                "pct": round(pct, 1),
            })
    out.sort(key=lambda x: -x["pct"])
    return out


def esri_to_geojson_geometry(rings):
    """Convierte rings de Esri (CW = outer, CCW = hole) a Polygon/MultiPolygon GeoJSON.

    Esri rings no diferencian explícitamente outer/hole; se determina por winding.
    Cada outer arranca un polígono nuevo, y los holes se asignan al outer que los
    contiene.
    """
    if not rings:
        return None
    outers = []  # lista de (ring, holes[])
    holes_pending = []
    for r in rings:
        if signed_area(r) > 0:
            outers.append((r, []))
        else:
            holes_pending.append(r)
    # Asignar cada hole al primer outer que lo contenga
    for h in holes_pending:
        if not h:
            continue
        pt = (h[0][0], h[0][1])
        assigned = False
        for outer, hs in outers:
            if point_in_ring(pt, outer):
                hs.append(h)
                assigned = True
                break
        # Si no se asigna a ningún outer, lo descarto (no debería pasar en datos limpios)
    if len(outers) == 1:
        outer, hs = outers[0]
        coords = [outer] + hs
        return {"type": "Polygon", "coordinates": coords}
    polys = []
    for outer, hs in outers:
        polys.append([outer] + hs)
    return {"type": "MultiPolygon", "coordinates": polys}


def main():
    print(f"→ Descargando UPL Esri JSON desde Datos Abiertos Bogotá…")
    with urllib.request.urlopen(UPL_URL) as r:
        raw = json.load(r)
    print(f"  {len(raw['features'])} features recibidas")
    crs = raw.get("spatialReference", {})
    wkid = crs.get("latestWkid", crs.get("wkid"))
    if wkid not in (4686, 4326):
        raise SystemExit(
            f"CRS inesperado: wkid={wkid}. Se esperaba 4686 (MAGNA-SIRGAS) "
            f"o 4326 (WGS84). Si el dataset cambió de proyección, agregar "
            f"reproyección con pyproj antes de continuar."
        )

    print(f"→ Cargando localidades para spatial join…")
    localidades = json.loads(LOCALIDADES.read_text(encoding="utf-8"))
    print(f"  {len(localidades['features'])} localidades")

    out_features = []
    sin_loc = []
    for f in raw["features"]:
        attrs = f["attributes"]
        geom = esri_to_geojson_geometry(f["geometry"].get("rings", []))
        if geom is None:
            continue

        # Solape con localidades (array, las UPL son transversales por diseño)
        locs = localidades_solape(geom, localidades, min_pct=5.0)
        if not locs:
            sin_loc.append(attrs.get("NOMBRE"))

        props = {
            "CODIGO_UPL":   attrs.get("CODIGO_UPL"),
            "NOMBRE":       attrs.get("NOMBRE"),
            "SECTOR":       attrs.get("SECTOR"),
            "VOCACION":     attrs.get("VOCACION"),
            "AREA_HA":      round(attrs.get("AREA_HA", 0), 2),
            # Localidades con las que solapa la UPL (≥5%), ordenadas por % desc.
            # Las UPL son transversales a las localidades por diseño del POT 555.
            "Localidades":  locs,
        }
        out_features.append({
            "type": "Feature",
            "properties": props,
            "geometry": geom,
        })

    out = {
        "type": "FeatureCollection",
        "name": "BOG-UPL",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "features": out_features,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    size_kb = OUT.stat().st_size / 1024
    print(f"✓ Escrito {OUT.relative_to(ROOT)}  ({size_kb:.0f} KB, {len(out_features)} features)")
    if sin_loc:
        print(f"⚠ {len(sin_loc)} UPL sin localidad asignada (centroide fuera): {sin_loc}")
    else:
        print(f"✓ Todas las UPL tienen localidad asignada")


if __name__ == "__main__":
    main()
