#!/usr/bin/env python3
"""
build-bog-upl/build-worker-data.py

Toma BOG-UPL.geojson + BOG-LOCALIDADX.json y emite un fragmento JS con las
geometrías simplificadas (Douglas-Peucker) listas para embeber en el Worker
rr-auth. El Worker hace point-in-polygon del lado server, así el cliente
nunca descarga el geojson completo (~1.8 MB).

Output: tools/build-bog-upl/worker-snippet.js
        (bloque JS para pegar en rr-auth-updated.js, antes del router)

Estrategia para minimizar tamaño:
  - Simplificación Douglas-Peucker con tolerancia ~0.0002° (~22m)
  - Solo Polygon/MultiPolygon (descartamos props irrelevantes)
  - Sólo guardamos lo mínimo: nombre, código, coords, y bbox precomputado
  - Coordenadas redondeadas a 5 decimales (~1m precisión, sobra para PiP)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UPL_IN = ROOT / "CIUDADES" / "BOGOTA" / "BOG-UPL.geojson"
LOC_IN = ROOT / "CIUDADES" / "BOGOTA" / "BOG-LOCALIDADX.json"
OUT_JS = Path(__file__).parent / "worker-snippet.js"

# Tolerancia DP en grados decimales. 0.0002° ≈ 22m en latitud de Bogotá.
DP_TOL = 0.0002
COORD_DECIMALS = 5


def perp_dist(p, a, b):
    """Distancia perpendicular del punto p al segmento ab."""
    ax, ay = a
    bx, by = b
    px, py = p
    dx = bx - ax
    dy = by - ay
    if dx == 0 and dy == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx = ax + t * dx
    cy = ay + t * dy
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5


def douglas_peucker(points, tol):
    """Simplificación recursiva. Conserva primer y último punto."""
    if len(points) < 3:
        return points
    # Encuentra el punto más distante al segmento entre los extremos
    dmax = 0.0
    idx = 0
    a, b = points[0], points[-1]
    for i in range(1, len(points) - 1):
        d = perp_dist(points[i], a, b)
        if d > dmax:
            dmax = d
            idx = i
    if dmax > tol:
        left = douglas_peucker(points[: idx + 1], tol)
        right = douglas_peucker(points[idx:], tol)
        return left[:-1] + right
    return [a, b]


def simplify_ring(ring, tol):
    out = douglas_peucker(ring, tol)
    if out[0] != out[-1]:
        out.append(out[0])
    if len(out) < 4:  # ring degenerado, descarta
        return None
    return [[round(x, COORD_DECIMALS), round(y, COORD_DECIMALS)] for x, y in out]


def simplify_geom(geom, tol):
    if geom["type"] == "Polygon":
        rings = []
        for r in geom["coordinates"]:
            sr = simplify_ring(r, tol)
            if sr:
                rings.append(sr)
        return {"type": "Polygon", "coordinates": rings} if rings else None
    if geom["type"] == "MultiPolygon":
        polys = []
        for poly in geom["coordinates"]:
            srs = []
            for r in poly:
                sr = simplify_ring(r, tol)
                if sr:
                    srs.append(sr)
            if srs:
                polys.append(srs)
        return {"type": "MultiPolygon", "coordinates": polys} if polys else None
    return None


def bbox_of(geom):
    minx, miny = float("inf"), float("inf")
    maxx, maxy = float("-inf"), float("-inf")
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    for poly in polys:
        for x, y in poly[0]:
            if x < minx: minx = x
            if y < miny: miny = y
            if x > maxx: maxx = x
            if y > maxy: maxy = y
    return [round(minx, COORD_DECIMALS), round(miny, COORD_DECIMALS),
            round(maxx, COORD_DECIMALS), round(maxy, COORD_DECIMALS)]


def shrink_polygon(geom):
    """Convierte Polygon → arr[arr[arr[num]]] o MultiPolygon → arr[arr[arr[arr[num]]]].
    El Worker recibe estructura mínima sin 'type'."""
    if geom["type"] == "Polygon":
        return {"k": "p", "c": geom["coordinates"]}
    return {"k": "m", "c": geom["coordinates"]}


def main():
    upl_in = json.loads(UPL_IN.read_text(encoding="utf-8"))
    loc_in = json.loads(LOC_IN.read_text(encoding="utf-8"))

    # UPL
    upl_out = []
    for f in upl_in["features"]:
        sg = simplify_geom(f["geometry"], DP_TOL)
        if not sg:
            continue
        upl_out.append({
            "n": f["properties"]["NOMBRE"],
            "k": f["properties"]["CODIGO_UPL"],
            "bb": bbox_of(sg),
            "g": shrink_polygon(sg),
        })

    # Localidades
    loc_out = []
    for f in loc_in["features"]:
        sg = simplify_geom(f["geometry"], DP_TOL)
        if not sg:
            continue
        loc_out.append({
            "n": f["properties"]["LocNombre"],
            "k": f["properties"]["LocCodigo"],
            "bb": bbox_of(sg),
            "g": shrink_polygon(sg),
        })

    # BBox global de Bogotá (suma de todas las localidades) para early-exit
    minx = min(l["bb"][0] for l in loc_out)
    miny = min(l["bb"][1] for l in loc_out)
    maxx = max(l["bb"][2] for l in loc_out)
    maxy = max(l["bb"][3] for l in loc_out)
    bog_bbox = [minx, miny, maxx, maxy]

    # Render del bloque JS — JSON minificado inline + helpers
    upl_json = json.dumps(upl_out, ensure_ascii=False, separators=(",", ":"))
    loc_json = json.dumps(loc_out, ensure_ascii=False, separators=(",", ":"))
    bbox_json = json.dumps(bog_bbox)

    js = (
        "// ─── Datos geo Bogotá (UPL + localidades) ─────────────────────────────\n"
        "// Generado por tools/build-bog-upl/build-worker-data.py — NO EDITAR A MANO.\n"
        f"// {len(upl_out)} UPL · {len(loc_out)} localidades · DP tol {DP_TOL}° (~22m)\n"
        f"const BOG_BBOX = {bbox_json};\n"
        f"const BOG_UPL = {upl_json};\n"
        f"const BOG_LOC = {loc_json};\n"
        "\n"
        "// Ray casting sobre un anillo cerrado (array de [x,y]).\n"
        "function _pir(pt, ring) {\n"
        "  const x = pt[0], y = pt[1];\n"
        "  let inside = false;\n"
        "  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {\n"
        "    const xi = ring[i][0], yi = ring[i][1];\n"
        "    const xj = ring[j][0], yj = ring[j][1];\n"
        "    if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / ((yj - yi) || 1e-15) + xi)) {\n"
        "      inside = !inside;\n"
        "    }\n"
        "  }\n"
        "  return inside;\n"
        "}\n"
        "\n"
        "// PiP sobre {k:'p', c:rings} (Polygon) o {k:'m', c:[[rings],...]} (MultiPolygon).\n"
        "// Asume primer ring = outer, resto = holes.\n"
        "function _pig(pt, g) {\n"
        "  if (g.k === 'p') {\n"
        "    const rings = g.c;\n"
        "    if (!rings.length || !_pir(pt, rings[0])) return false;\n"
        "    for (let i = 1; i < rings.length; i++) if (_pir(pt, rings[i])) return false;\n"
        "    return true;\n"
        "  }\n"
        "  for (const poly of g.c) {\n"
        "    if (!poly.length) continue;\n"
        "    if (!_pir(pt, poly[0])) continue;\n"
        "    let inHole = false;\n"
        "    for (let i = 1; i < poly.length; i++) {\n"
        "      if (_pir(pt, poly[i])) { inHole = true; break; }\n"
        "    }\n"
        "    if (!inHole) return true;\n"
        "  }\n"
        "  return false;\n"
        "}\n"
        "\n"
        "// Lookup principal: dado (lat, lon), devuelve {upl, localidad} o {} si fuera de BOG.\n"
        "function bogLookup(lat, lon) {\n"
        "  if (lat == null || lon == null) return {};\n"
        "  const pt = [lon, lat]; // GeoJSON es [x=lon, y=lat]\n"
        "  if (lon < BOG_BBOX[0] || lon > BOG_BBOX[2] || lat < BOG_BBOX[1] || lat > BOG_BBOX[3]) return {};\n"
        "  let upl = null, loc = null;\n"
        "  for (const u of BOG_UPL) {\n"
        "    const bb = u.bb;\n"
        "    if (lon < bb[0] || lon > bb[2] || lat < bb[1] || lat > bb[3]) continue;\n"
        "    if (_pig(pt, u.g)) { upl = { nombre: u.n, codigo: u.k }; break; }\n"
        "  }\n"
        "  for (const l of BOG_LOC) {\n"
        "    const bb = l.bb;\n"
        "    if (lon < bb[0] || lon > bb[2] || lat < bb[1] || lat > bb[3]) continue;\n"
        "    if (_pig(pt, l.g)) { loc = { nombre: l.n, codigo: l.k }; break; }\n"
        "  }\n"
        "  return { upl, localidad: loc };\n"
        "}\n"
    )

    OUT_JS.write_text(js, encoding="utf-8")
    size_kb = OUT_JS.stat().st_size / 1024
    # Estima tamaño gzipped
    import gzip
    gz_kb = len(gzip.compress(js.encode("utf-8"))) / 1024
    print(f"✓ {OUT_JS.relative_to(ROOT)}")
    print(f"  raw  : {size_kb:.0f} KB")
    print(f"  gzip : {gz_kb:.0f} KB")
    print(f"  UPL  : {len(upl_out)} features")
    print(f"  LOC  : {len(loc_out)} features")
    print(f"  bbox : {bog_bbox}")


if __name__ == "__main__":
    main()
