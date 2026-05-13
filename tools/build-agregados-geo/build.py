#!/usr/bin/env python3
"""
build-agregados-geo/build.py

Genera agregados de proyección presidencial por unidad geográfica para el
test-presidencial-2026. Toma proyeccion-por-puesto.json (~13.500 puestos) y
lo cruza contra:
  - 33 UPL de Bogotá       → proyeccion-por-upl-bogota.json
  - 349 barrios de Medellín → proyeccion-por-barrio-medellin.json

Para cada unidad geográfica:
  pct[cand] = Σ_puesto (censo × pct_puesto[cand]) / Σ_puesto censo

Es decir, promedio ponderado por censo (no por número de puestos), que es
lo correcto para representar el peso electoral real de la unidad.

Inputs:
  /Users/ricardoruiz/ricardoruiz.co/Bases de datos/proyeccion-por-puesto-*.json
  /Users/ricardoruiz/ricardoruiz.co/CIUDADES/BOGOTA/BOG-UPL.geojson
  /Users/ricardoruiz/ricardoruiz.co/Bases de datos/proyecto-dc/geo/barrios-veredas-medellin.geojson

Outputs:
  /Users/ricardoruiz/ricardoruiz.co/Bases de datos/output_ponderador/proyeccion-por-upl-bogota.json
  /Users/ricardoruiz/ricardoruiz.co/Bases de datos/output_ponderador/proyeccion-por-barrio-medellin.json

Después: aws s3 cp para subirlos junto al proyeccion-por-puesto.json.

Sin dependencias externas. Usa los helpers del script de UPL para PiP.
"""
import json
import sys
from pathlib import Path
from glob import glob

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "build-bog-upl"))
from build import point_in_geom, bbox_of_geom  # noqa: E402

PUESTOS_GLOB = str(ROOT / "Bases de datos" / "proyeccion-por-puesto-*.json")
BOG_UPL      = ROOT / "CIUDADES" / "BOGOTA" / "BOG-UPL.geojson"
MED_BARRIOS  = ROOT / "Bases de datos" / "proyecto-dc" / "geo" / "barrios-veredas-medellin.geojson"
CAL_COMUNAS  = ROOT / "CIUDADES" / "CALI" / "CALIX.json"
OUT_DIR      = ROOT / "Bases de datos" / "output_ponderador"


def load_latest_puestos():
    """Carga el JSON de puestos más reciente disponible."""
    files = sorted(glob(PUESTOS_GLOB))
    if not files:
        raise SystemExit(f"No encontré ningún proyeccion-por-puesto-*.json en {PUESTOS_GLOB}")
    latest = files[-1]
    print(f"→ Leyendo {Path(latest).name}")
    return json.loads(Path(latest).read_text(encoding="utf-8")), latest


def index_features_by_bbox(fc):
    """Devuelve lista de (bbox, feature) para iteración rápida."""
    out = []
    for f in fc["features"]:
        bb = bbox_of_geom(f["geometry"])
        if bb:
            out.append((bb, f))
    return out


def find_unit(lat, lon, indexed_features, code_key, name_key, area_bbox=None):
    """Para un punto (lat, lon), encuentra el primer feature que lo contiene.

    Devuelve (codigo, nombre) o (None, None).
    Si area_bbox es dado, hace early-exit cuando el punto está fuera del bbox global.
    """
    pt = (lon, lat)  # GeoJSON es [x=lon, y=lat]
    if area_bbox:
        minx, miny, maxx, maxy = area_bbox
        if lon < minx or lon > maxx or lat < miny or lat > maxy:
            return None, None
    for bb, f in indexed_features:
        if lon < bb[0] or lon > bb[2] or lat < bb[1] or lat > bb[3]:
            continue
        if point_in_geom(pt, f["geometry"]):
            return f["properties"].get(code_key), f["properties"].get(name_key)
    return None, None


def global_bbox(indexed_features):
    """BBox que envuelve todos los features indexados."""
    minx = min(bb[0] for bb, _ in indexed_features)
    miny = min(bb[1] for bb, _ in indexed_features)
    maxx = max(bb[2] for bb, _ in indexed_features)
    maxy = max(bb[3] for bb, _ in indexed_features)
    return (minx, miny, maxx, maxy)


def aggregate(puestos, indexed_features, code_key, name_key, extra_keys=None):
    """Acumula puestos por unidad geográfica y devuelve agregados ponderados por censo.

    Para cada unidad:
      pct[cand] = Σ(censo × pct_puesto[cand]) / Σ(censo)

    Si extra_keys es dado, los copia de las properties del feature al output.
    """
    area_bb = global_bbox(indexed_features)
    by_code = {}        # codigo → {nombre, censo, votos_por_cand, n_puestos}
    extra_props = {}    # codigo → dict de extras (Localidades, etc.)
    hits = 0

    for p in puestos:
        lat, lon = p["lat"], p["lon"]
        # Lookup
        if lon < area_bb[0] or lon > area_bb[2] or lat < area_bb[1] or lat > area_bb[3]:
            continue
        pt = (lon, lat)
        feat = None
        for bb, f in indexed_features:
            if lon < bb[0] or lon > bb[2] or lat < bb[1] or lat > bb[3]:
                continue
            if point_in_geom(pt, f["geometry"]):
                feat = f
                break
        if feat is None:
            continue
        cod = feat["properties"].get(code_key)
        nom = feat["properties"].get(name_key)
        if cod is None:
            continue
        hits += 1
        censo = p.get("c", 0) or 0
        if cod not in by_code:
            by_code[cod] = {
                "nombre": nom,
                "censo": 0,
                "puestos": 0,
                "votos": {},  # cand_id → suma ponderada
            }
            if extra_keys:
                extra_props[cod] = {k: feat["properties"].get(k) for k in extra_keys}
        by_code[cod]["censo"] += censo
        by_code[cod]["puestos"] += 1
        for cand_id, pct in p["p"].items():
            by_code[cod]["votos"][cand_id] = by_code[cod]["votos"].get(cand_id, 0) + censo * pct

    # Normalizar a porcentaje (votos / censo total de la unidad)
    out = {}
    for cod, agg in by_code.items():
        if agg["censo"] <= 0:
            continue
        pct = {cid: round(v / agg["censo"], 2) for cid, v in agg["votos"].items()}
        # Ordenar por valor descendente, conservar solo top-9 (Murillo está fuera)
        pct = dict(sorted(pct.items(), key=lambda kv: -kv[1]))
        unit = {
            "nombre": agg["nombre"],
            "puestos": agg["puestos"],
            "censo": agg["censo"],
            "p": pct,
        }
        if extra_keys and cod in extra_props:
            unit.update(extra_props[cod])
        out[cod] = unit

    return out, hits


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pue_data, pue_path = load_latest_puestos()
    puestos = pue_data["puestos"]
    print(f"  {len(puestos)} puestos · versión {pue_data['version']}")
    print()

    # ── Bogotá UPL ──
    print("→ Cargando UPL Bogotá…")
    upl_geo = json.loads(BOG_UPL.read_text(encoding="utf-8"))
    upl_idx = index_features_by_bbox(upl_geo)
    print(f"  {len(upl_idx)} UPL")
    bog_agg, bog_hits = aggregate(
        puestos, upl_idx,
        code_key="CODIGO_UPL", name_key="NOMBRE",
        extra_keys=["SECTOR", "VOCACION", "Localidades"],
    )
    print(f"  {bog_hits} puestos asignados a UPL · {len(bog_agg)} UPL con datos")
    out_bog = {
        "version": pue_data["version"],
        "source": Path(pue_path).name,
        "sliders_signature": pue_data["sliders_signature"],
        "nacional": pue_data["nacional"],
        "ciudad": "bogota",
        "tipo": "upl",
        "agregados": bog_agg,
    }
    bog_path = OUT_DIR / "proyeccion-por-upl-bogota.json"
    bog_path.write_text(json.dumps(out_bog, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  ✓ {bog_path.relative_to(ROOT)} ({bog_path.stat().st_size/1024:.0f} KB)")
    print()

    # ── Medellín barrios ──
    print("→ Cargando barrios Medellín…")
    med_geo = json.loads(MED_BARRIOS.read_text(encoding="utf-8"))
    med_idx = index_features_by_bbox(med_geo)
    print(f"  {len(med_idx)} barrios/veredas")
    med_agg, med_hits = aggregate(
        puestos, med_idx,
        code_key="codigo", name_key="nombre_bar",
        extra_keys=["comuna", "nombre_com"],
    )
    print(f"  {med_hits} puestos asignados a barrio · {len(med_agg)} barrios con datos")
    out_med = {
        "version": pue_data["version"],
        "source": Path(pue_path).name,
        "sliders_signature": pue_data["sliders_signature"],
        "nacional": pue_data["nacional"],
        "ciudad": "medellin",
        "tipo": "barrio",
        "agregados": med_agg,
    }
    med_path = OUT_DIR / "proyeccion-por-barrio-medellin.json"
    med_path.write_text(json.dumps(out_med, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  ✓ {med_path.relative_to(ROOT)} ({med_path.stat().st_size/1024:.0f} KB)")
    print()

    # ── Cali comunas ──
    print("→ Cargando comunas Cali…")
    cal_geo = json.loads(CAL_COMUNAS.read_text(encoding="utf-8"))
    cal_idx = index_features_by_bbox(cal_geo)
    print(f"  {len(cal_idx)} comunas")
    cal_agg, cal_hits = aggregate(
        puestos, cal_idx,
        code_key="comuna", name_key="nombre",
    )
    print(f"  {cal_hits} puestos asignados a comuna · {len(cal_agg)} comunas con datos")
    out_cal = {
        "version": pue_data["version"],
        "source": Path(pue_path).name,
        "sliders_signature": pue_data["sliders_signature"],
        "nacional": pue_data["nacional"],
        "ciudad": "cali",
        "tipo": "comuna",
        "agregados": cal_agg,
    }
    cal_path = OUT_DIR / "proyeccion-por-comuna-cali.json"
    cal_path.write_text(json.dumps(out_cal, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  ✓ {cal_path.relative_to(ROOT)} ({cal_path.stat().st_size/1024:.0f} KB)")
    print()

    # ── Sanity check: top-3 UPL y barrios ──
    print("Top-5 UPL Bogotá por censo:")
    for cod, u in sorted(bog_agg.items(), key=lambda kv: -kv[1]["censo"])[:5]:
        top = list(u["p"].items())[:3]
        print(f"  {cod} {u['nombre']:<25}  censo={u['censo']:>8,}  → " + " · ".join(f"{c}={v}%" for c,v in top))
    print()
    print("Top-5 barrios Medellín por censo:")
    for cod, b in sorted(med_agg.items(), key=lambda kv: -kv[1]["censo"])[:5]:
        top = list(b["p"].items())[:3]
        print(f"  {cod} {b['nombre'][:30]:<30}  censo={b['censo']:>8,}  → " + " · ".join(f"{c}={v}%" for c,v in top))
    print()
    print("Top-5 comunas Cali por censo:")
    for cod, c in sorted(cal_agg.items(), key=lambda kv: -kv[1]["censo"])[:5]:
        top = list(c["p"].items())[:3]
        print(f"  {cod} {c['nombre'][:30]:<30}  censo={c['censo']:>8,}  → " + " · ".join(f"{x}={v}%" for x,v in top))


if __name__ == "__main__":
    main()
