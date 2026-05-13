#!/usr/bin/env python3
"""
build-bog-upl/build-worker-data.py

Toma los GeoJSON oficiales de las ciudades soportadas (Bogotá UPL +
Localidades, Medellín Barrios + Comunas, Cali Comunas) y emite un fragmento
JS con las geometrías simplificadas (Douglas-Peucker) listas para embeber
en el Worker rr-auth. El Worker hace point-in-polygon del lado server, así
el cliente nunca descarga el geojson completo (~varios MB).

Output: tools/build-bog-upl/worker-snippet.js
        (bloque JS para pegar en rr-auth-updated.js, antes del router)

Estrategia para minimizar tamaño:
  - Simplificación Douglas-Peucker con tolerancia ~0.0002° (~22m)
  - Estructuras compactas: {n:nombre, k:codigo, bb:bbox, g:{k,c}, [extra]}
  - Coordenadas redondeadas a 5 decimales (~1m precisión, sobra para PiP)
  - Bogotá: dos capas (UPL + localidades) — para mostrar "UPL Chapinero · Localidad Chapinero"
  - Medellín: dos capas (Barrio + Comuna) — los barrios traen comuna en properties
  - Cali: una capa (comunas) — granularidad social estándar

Las funciones JS expuestas en el snippet:
  bogLookup(lat,lon) → {upl:{nombre,codigo}|null, localidad:{nombre,codigo}|null}
  medLookup(lat,lon) → {barrio:{nombre,codigo,comuna,nombre_comuna}|null}
  calLookup(lat,lon) → {comuna:{nombre,codigo}|null}
  cityLookup(lat,lon) → resuelve la ciudad por bbox y delega
"""
import json
import gzip
from pathlib import Path

ROOT     = Path(__file__).resolve().parents[2]
OUT_JS   = Path(__file__).parent / "worker-snippet.js"

BOG_UPL  = ROOT / "CIUDADES" / "BOGOTA" / "BOG-UPL.geojson"
BOG_LOC  = ROOT / "CIUDADES" / "BOGOTA" / "BOG-LOCALIDADX.json"
MED_BARR = ROOT / "Bases de datos" / "proyecto-dc" / "geo" / "barrios-veredas-medellin.geojson"
CAL_COM  = ROOT / "CIUDADES" / "CALI" / "CALIX.json"

DP_TOL = 0.0002
COORD_DECIMALS = 5


def perp_dist(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx = bx - ax; dy = by - ay
    if dx == 0 and dy == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx = ax + t * dx; cy = ay + t * dy
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5


def douglas_peucker(points, tol):
    if len(points) < 3:
        return points
    dmax = 0.0; idx = 0
    a, b = points[0], points[-1]
    for i in range(1, len(points) - 1):
        d = perp_dist(points[i], a, b)
        if d > dmax:
            dmax = d; idx = i
    if dmax > tol:
        left = douglas_peucker(points[: idx + 1], tol)
        right = douglas_peucker(points[idx:], tol)
        return left[:-1] + right
    return [a, b]


def simplify_ring(ring, tol):
    out = douglas_peucker(ring, tol)
    if out[0] != out[-1]:
        out.append(out[0])
    if len(out) < 4:
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


def shrink_geom(geom):
    """Polygon → {k:'p', c:rings}; MultiPolygon → {k:'m', c:[[rings],...]}."""
    if geom["type"] == "Polygon":
        return {"k": "p", "c": geom["coordinates"]}
    return {"k": "m", "c": geom["coordinates"]}


def build_layer(geojson_path, name_prop, code_prop, extras=None):
    """Lee un GeoJSON, simplifica cada feature, retorna lista de entries.
    extras = lista de prop names a copiar tal cual (sin simplificar).
    """
    data = json.loads(geojson_path.read_text(encoding="utf-8"))
    out = []
    for f in data["features"]:
        sg = simplify_geom(f["geometry"], DP_TOL)
        if not sg:
            continue
        props = f["properties"]
        entry = {
            "n":  props.get(name_prop),
            "k":  props.get(code_prop),
            "bb": bbox_of(sg),
            "g":  shrink_geom(sg),
        }
        if extras:
            for ek in extras:
                v = props.get(ek)
                if v is not None:
                    entry[ek] = v
        out.append(entry)
    return out


def global_bbox(entries):
    return [
        min(e["bb"][0] for e in entries),
        min(e["bb"][1] for e in entries),
        max(e["bb"][2] for e in entries),
        max(e["bb"][3] for e in entries),
    ]


def main():
    print("→ Simplificando capas geo…")
    bog_upl = build_layer(BOG_UPL, "NOMBRE",     "CODIGO_UPL")
    bog_loc = build_layer(BOG_LOC, "LocNombre",  "LocCodigo")
    med_bar = build_layer(MED_BARR, "nombre_bar","codigo", extras=["comuna", "nombre_com"])
    cal_com = build_layer(CAL_COM,  "nombre",    "comuna")

    bog_bbox = global_bbox(bog_loc)  # Bogotá completa = unión de localidades
    med_bbox = global_bbox(med_bar)
    cal_bbox = global_bbox(cal_com)

    js_parts = [
        "// ─── Datos geo Bogotá / Medellín / Cali ────────────────────────────",
        "// Generado por tools/build-bog-upl/build-worker-data.py — NO EDITAR A MANO.",
        f"// Bogotá: {len(bog_upl)} UPL + {len(bog_loc)} localidades",
        f"// Medellín: {len(med_bar)} barrios+veredas",
        f"// Cali: {len(cal_com)} comunas",
        f"// Simplificación Douglas-Peucker tol {DP_TOL}° (~22m)",
        f"const BOG_BBOX = {json.dumps(bog_bbox)};",
        f"const MED_BBOX = {json.dumps(med_bbox)};",
        f"const CAL_BBOX = {json.dumps(cal_bbox)};",
        f"const BOG_UPL = {json.dumps(bog_upl, ensure_ascii=False, separators=(',',':'))};",
        f"const BOG_LOC = {json.dumps(bog_loc, ensure_ascii=False, separators=(',',':'))};",
        f"const MED_BAR = {json.dumps(med_bar, ensure_ascii=False, separators=(',',':'))};",
        f"const CAL_COM = {json.dumps(cal_com, ensure_ascii=False, separators=(',',':'))};",
        "",
        "// Ray casting sobre un anillo cerrado (array de [x,y]).",
        "function _pir(pt, ring) {",
        "  const x = pt[0], y = pt[1];",
        "  let inside = false;",
        "  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {",
        "    const xi = ring[i][0], yi = ring[i][1];",
        "    const xj = ring[j][0], yj = ring[j][1];",
        "    if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / ((yj - yi) || 1e-15) + xi)) {",
        "      inside = !inside;",
        "    }",
        "  }",
        "  return inside;",
        "}",
        "",
        "// PiP sobre {k:'p', c:rings} (Polygon) o {k:'m', c:[[rings],...]} (MultiPolygon).",
        "function _pig(pt, g) {",
        "  if (g.k === 'p') {",
        "    const rings = g.c;",
        "    if (!rings.length || !_pir(pt, rings[0])) return false;",
        "    for (let i = 1; i < rings.length; i++) if (_pir(pt, rings[i])) return false;",
        "    return true;",
        "  }",
        "  for (const poly of g.c) {",
        "    if (!poly.length) continue;",
        "    if (!_pir(pt, poly[0])) continue;",
        "    let inHole = false;",
        "    for (let i = 1; i < poly.length; i++) {",
        "      if (_pir(pt, poly[i])) { inHole = true; break; }",
        "    }",
        "    if (!inHole) return true;",
        "  }",
        "  return false;",
        "}",
        "",
        "// Helper: encuentra primer feature de una capa que contenga el punto.",
        "function _findInLayer(pt, layer) {",
        "  for (const e of layer) {",
        "    const bb = e.bb;",
        "    if (pt[0] < bb[0] || pt[0] > bb[2] || pt[1] < bb[1] || pt[1] > bb[3]) continue;",
        "    if (_pig(pt, e.g)) return e;",
        "  }",
        "  return null;",
        "}",
        "",
        "// Devuelve {city, scope, label, codigo, sub?, sub_codigo?} para el lat/lon dado,",
        "// o {} si no está en ninguna de las ciudades soportadas.",
        "function cityLookup(lat, lon) {",
        "  if (lat == null || lon == null) return {};",
        "  const pt = [lon, lat];",
        "  // Bogotá",
        "  if (lon >= BOG_BBOX[0] && lon <= BOG_BBOX[2] && lat >= BOG_BBOX[1] && lat <= BOG_BBOX[3]) {",
        "    const upl = _findInLayer(pt, BOG_UPL);",
        "    const loc = _findInLayer(pt, BOG_LOC);",
        "    if (upl || loc) {",
        "      return {",
        "        city: 'Bogotá D.C.',",
        "        scope: 'upl',",
        "        label: upl ? upl.n : null,",
        "        codigo: upl ? upl.k : null,",
        "        sub: loc ? loc.n : null,",
        "        sub_codigo: loc ? loc.k : null,",
        "      };",
        "    }",
        "  }",
        "  // Medellín",
        "  if (lon >= MED_BBOX[0] && lon <= MED_BBOX[2] && lat >= MED_BBOX[1] && lat <= MED_BBOX[3]) {",
        "    const bar = _findInLayer(pt, MED_BAR);",
        "    if (bar) {",
        "      return {",
        "        city: 'Medellín',",
        "        scope: 'barrio',",
        "        label: bar.n,",
        "        codigo: bar.k,",
        "        sub: bar.nombre_com || null,",
        "        sub_codigo: bar.comuna || null,",
        "      };",
        "    }",
        "  }",
        "  // Cali",
        "  if (lon >= CAL_BBOX[0] && lon <= CAL_BBOX[2] && lat >= CAL_BBOX[1] && lat <= CAL_BBOX[3]) {",
        "    const com = _findInLayer(pt, CAL_COM);",
        "    if (com) {",
        "      return {",
        "        city: 'Cali',",
        "        scope: 'comuna',",
        "        label: com.n,",
        "        codigo: com.k,",
        "      };",
        "    }",
        "  }",
        "  return {};",
        "}",
        "",
        "// Compat: alias del lookup anterior solo-Bogotá. Devuelve { upl, localidad } como antes.",
        "function bogLookup(lat, lon) {",
        "  const r = cityLookup(lat, lon);",
        "  if (r.city !== 'Bogotá D.C.') return {};",
        "  return {",
        "    upl: r.label ? { nombre: r.label, codigo: r.codigo } : null,",
        "    localidad: r.sub ? { nombre: r.sub, codigo: r.sub_codigo } : null,",
        "  };",
        "}",
    ]
    js = "\n".join(js_parts) + "\n"
    OUT_JS.write_text(js, encoding="utf-8")
    raw = len(js.encode("utf-8")) / 1024
    gz  = len(gzip.compress(js.encode("utf-8"))) / 1024
    print(f"✓ {OUT_JS.relative_to(ROOT)}")
    print(f"  raw  : {raw:.0f} KB")
    print(f"  gzip : {gz:.0f} KB  (límite gratis Cloudflare: 1024 KB)")
    print(f"  Bogotá UPL: {len(bog_upl)} · Loc: {len(bog_loc)}")
    print(f"  Medellín bar: {len(med_bar)}")
    print(f"  Cali comunas: {len(cal_com)}")


if __name__ == "__main__":
    main()
