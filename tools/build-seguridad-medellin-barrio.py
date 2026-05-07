#!/usr/bin/env python3
"""
build-seguridad-medellin-barrio.py

Genera por-barrio.json para el módulo 02 de seguridad. Toma los CSVs
limpios de la Policía Nacional y los cruza contra el GeoJSON de barrios
y veredas (ONU-Habitat, 349 polígonos) para producir conteos a nivel
barrio (no solo comuna).

Estrategia de match:
  · BARRIOS_HECHO viene como "NOMBRE BARRIO C-XX" (sufijo = comuna política)
  · Stripping de sufijo " C-XX" + normalización (upper, sin tildes)
  · Match estricto por (comuna_hint, nombre_normalizado) → codigo 4 dígitos
  · Si el match estricto falla, fallback a match por nombre normalizado solo
  · "BARRIO PENDIENTE POR ASIGNAR" y similares → bucket OTROS

Uso:
    python3 tools/build-seguridad-medellin-barrio.py \\
        "<CSV input dir>" \\
        "<GeoJSON path>" \\
        "<out dir>"

Salida:
    {out-dir}/por-barrio.json   { codigo → {comuna, nombre_com, nombre_bar,
                                            indicador, total, por_tipologia} }
                                 + meta: cobertura, sin_match, pendientes
"""

import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path


TIPOLOGIAS = [
    "amenazas", "delitos-informaticos", "delitos-sexuales", "extorsion",
    "homicidios", "homicidios-en-at", "hurto-a-comercio", "hurto-a-motos",
    "hurto-a-personas", "hurto-a-residencias", "hurto-automotores",
    "hurto-bicicletas", "hurto-celular", "lesiones-en-at",
    "lesiones-personales", "pirateria-terrestre", "secuestro", "terrorismo",
    "violencia-intrafamiliar",
]

RE_C_SUFFIX = re.compile(r"\s*C-\d+\s*$", re.IGNORECASE)
# Sufijos de corregimiento que la Policía usa cuando no hay C-XX
RE_CORREG_SUFFIX = re.compile(
    r"\s+(S\.?A\.?P\.?|S\.?C\.?|S\.?E\.?|PALM\.?|ALT\.?)\s*$", re.IGNORECASE
)
SUFFIX_TO_COMUNA = {
    "SAP": "80", "SC": "60", "SE": "90", "PALM": "50", "ALT": "70",
}
# Articles + neutral prefixes que la fuente Policía omite o agrega
# distinto que el GeoJSON. Se pelan en ambos lados antes del match.
RE_LEADING_NOISE = re.compile(
    r"^(?:BARRIO|VEREDA|VDA\.?|EL|LA|LOS|LAS)\s+", re.IGNORECASE
)
# "No. 1" / "No.1" / "NO 1" / "Nº 1"  →  "1"
RE_NUM_PREFIX = re.compile(r"\bN[OoºO\.]+\s*(\d)", re.IGNORECASE)
RE_HINT = re.compile(r"C-(\d+)\s*$")

# Aliases manuales: cuando la simplificación automática no alcanza.
# CSV (post-clean + aggressive_norm) → variante esperada en el GeoJSON
# (post aggressive_norm). Si "DOCE DE OCTUBRE" llega sin número, lo
# mandamos al polígono "No.1" para que al menos pinte algo.
MANUAL_ALIAS = {
    "DOCE DE OCTUBRE":   "DOCE DE OCTUBRE 1",
    "CENTRO S.C.":       "CABECERA URBANA SAN CRISTOBAL",
    "CENTRO S.A.P.":     "CABECERA SAN ANTONIO DE PRADO",
    "CAYCEDO":           "CAICEDO",                # typo Policía
    "CAICEDO":           "CAICEDO",
    "13 DE NOVIIEMBRE":  "TRECE DE NOVIEMBRE",     # typo + numeral
    "13 DE NOVIEMBRE":   "TRECE DE NOVIEMBRE",
    "VILLA LILLIAN":     "VILLA LILIAM",           # typo Policía
    "VILLATINA":         "VILLATINA",              # idempotente para no-space
    "VILLA TINA":        "VILLATINA",
    "VILLANUEVA":        "VILLA NUEVA",
    "POPULAR 1":         "SANTO DOMINGO SAVIO 1",  # heurística cabecera com 01
    "POPULAR 2":         "SANTO DOMINGO SAVIO 2",
    "SANTO DOMINGO 1":   "SANTO DOMINGO SAVIO 1",
    "SANTO DOMINGO 2":   "SANTO DOMINGO SAVIO 2",
    "SAN JAVIER LA LOMA":"SAN JAVIER 1",
    "AURORA":            "LA AURORA",
}


def fix_encoding(s: str) -> str:
    """Repara strings que vienen como Latin-1 mal interpretado en UTF-8.
    Idempotente: si ya viene bien, devuelve igual."""
    if not isinstance(s, str):
        return s
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def norm(s: str) -> str:
    s = (s or "").strip().upper()
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    s = re.sub(r"\s+", " ", s)
    return s


def aggressive_norm(s: str) -> str:
    """Normalización con strip de artículos y de 'No.' antes de números.
    Pensada para matching robusto entre CSV y GeoJSON."""
    s = norm(s)
    s = RE_NUM_PREFIX.sub(r"\1", s)         # "NO. 1" → "1"
    s = re.sub(r"\s+", " ", s).strip()
    # Strip de prefijos uno por uno (puede haber dos: "BARRIO EL")
    for _ in range(2):
        new = RE_LEADING_NOISE.sub("", s, count=1)
        if new == s:
            break
        s = new
    return s


def parse_csv_barrio(b: str):
    """Devuelve (cod_hint|None, nombre_limpio).
    Detecta tanto 'C-XX' como sufijos de corregimiento (S.A.P./S.C./S.E.)."""
    b = (b or "").strip()
    cod_hint = None
    m = RE_HINT.search(b)
    if m:
        cod_hint = f"{int(m.group(1)):02d}"
        b = RE_C_SUFFIX.sub("", b)
    else:
        m2 = RE_CORREG_SUFFIX.search(b)
        if m2:
            key = re.sub(r"\.", "", m2.group(1)).upper()
            cod_hint = SUFFIX_TO_COMUNA.get(key)
            b = RE_CORREG_SUFFIX.sub("", b)
    return cod_hint, b.strip()


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    csv_dir = Path(sys.argv[1])
    geo_path = Path(sys.argv[2])
    out_dir = Path(sys.argv[3])
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Load GeoJSON; build lookups múltiples
    with open(geo_path, encoding="utf-8") as f:
        geo = json.load(f)
    by_com_strict = {}      # (comuna, norm_estricto)    → codigo
    by_com_aggr = {}        # (comuna, norm_agresivo)    → codigo
    by_name_aggr = {}       # norm_agresivo              → codigo (último gana)
    barrio_meta = {}        # codigo → meta
    for ft in geo["features"]:
        p = ft["properties"]
        cod = p.get("codigo")
        com = p.get("comuna")
        nom_b = fix_encoding(p.get("nombre_bar") or "")
        nom_c = fix_encoding(p.get("nombre_com") or "")
        n_strict = norm(nom_b)
        n_aggr = aggressive_norm(nom_b)
        meta = {
            "comuna": com,
            "nombre_com": nom_c,
            "nombre_bar": nom_b,
            "indicador": p.get("indicador_"),
        }
        barrio_meta[cod] = meta
        by_com_strict[(com, n_strict)] = cod
        by_com_aggr[(com, n_aggr)] = cod
        by_name_aggr[n_aggr] = cod

    print(f"[geo] {len(barrio_meta)} polígonos cargados")

    # ── Aggregate
    por_barrio = defaultdict(
        lambda: {"total": 0, "por_tipologia": defaultdict(int)}
    )
    sin_match = defaultdict(
        lambda: {"total": 0, "por_tipologia": defaultdict(int)}
    )
    pendientes_total = 0
    incidentes_total = 0
    matched_strict = 0       # (comuna, norm_estricto)
    matched_aggressive = 0   # (comuna, norm_agresivo)
    matched_alias = 0        # alias manual
    matched_loose = 0        # solo nombre, sin comuna hint

    for tip in TIPOLOGIAS:
        path = csv_dir / f"{tip}.csv"
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if (row.get("MUNICIPIO_HECHO") or "").strip() != "Medellín (CT)":
                    continue
                qty = int(row.get("CANTIDAD") or 1) or 1
                incidentes_total += qty
                raw = (row.get("BARRIOS_HECHO") or "").strip()
                if "PENDIENTE" in raw.upper():
                    pendientes_total += qty
                    continue
                cod_hint, cleaned_raw = parse_csv_barrio(raw)
                n_strict = norm(cleaned_raw)
                n_aggr = aggressive_norm(cleaned_raw)
                cod = None
                if cod_hint and (cod_hint, n_strict) in by_com_strict:
                    cod = by_com_strict[(cod_hint, n_strict)]
                    matched_strict += qty
                elif cod_hint and (cod_hint, n_aggr) in by_com_aggr:
                    cod = by_com_aggr[(cod_hint, n_aggr)]
                    matched_aggressive += qty
                elif n_aggr in MANUAL_ALIAS:
                    canonical = MANUAL_ALIAS[n_aggr]
                    if cod_hint and (cod_hint, canonical) in by_com_aggr:
                        cod = by_com_aggr[(cod_hint, canonical)]
                        matched_alias += qty
                    elif canonical in by_name_aggr:
                        cod = by_name_aggr[canonical]
                        matched_alias += qty
                elif n_aggr in by_name_aggr:
                    cod = by_name_aggr[n_aggr]
                    matched_loose += qty
                if cod:
                    por_barrio[cod]["total"] += qty
                    por_barrio[cod]["por_tipologia"][tip] += qty
                else:
                    key = f"{n_aggr} [C-{cod_hint or '??'}]"
                    sin_match[key]["total"] += qty
                    sin_match[key]["por_tipologia"][tip] += qty

    matched_total = matched_strict + matched_aggressive + matched_alias + matched_loose
    sin_match_total = sum(v["total"] for v in sin_match.values())

    # ── Build output
    out = {
        "meta": {
            "generado_en": datetime.now().isoformat(),
            "fuente_geojson": geo_path.name,
            "fuente_csv": str(csv_dir),
            "incidentes_total": incidentes_total,
            "geocodificados_a_barrio": matched_total,
            "geocodificados_pct": round(matched_total / incidentes_total * 100, 2) if incidentes_total else 0,
            "match_estricto": matched_strict,
            "match_agresivo": matched_aggressive,
            "match_alias": matched_alias,
            "match_loose": matched_loose,
            "pendientes": pendientes_total,
            "pendientes_pct": round(pendientes_total / incidentes_total * 100, 2) if incidentes_total else 0,
            "sin_match": sin_match_total,
            "sin_match_pct": round(sin_match_total / incidentes_total * 100, 2) if incidentes_total else 0,
            "barrios_con_data": len(por_barrio),
            "barrios_total_geojson": len(barrio_meta),
        },
        "barrios": {},
        "sin_match_top": {},
    }
    for cod, scope in por_barrio.items():
        meta = barrio_meta.get(cod, {})
        out["barrios"][cod] = {
            **meta,
            "total": scope["total"],
            "por_tipologia": dict(scope["por_tipologia"]),
        }

    # Top 30 sin match para diagnóstico (no se renderiza en frontend)
    top_unmatched = sorted(sin_match.items(), key=lambda kv: -kv[1]["total"])[:30]
    for k, v in top_unmatched:
        out["sin_match_top"][k] = {
            "total": v["total"],
            "por_tipologia": dict(v["por_tipologia"]),
        }

    out_path = out_dir / "por-barrio.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── Sanity print
    pct = lambda n: f"{n/incidentes_total*100:.1f}%" if incidentes_total else "—"
    print(f"\n[resumen]")
    print(f"  Incidentes Medellín:  {incidentes_total:>6,}")
    print(f"  Match a barrio:       {matched_total:>6,}  ({pct(matched_total)})")
    print(f"    estricto (com+nom): {matched_strict:>6,}")
    print(f"    agresivo (com+aggr):{matched_aggressive:>6,}")
    print(f"    alias manual:       {matched_alias:>6,}")
    print(f"    loose (sólo nom):   {matched_loose:>6,}")
    print(f"  Pendientes (fuente):  {pendientes_total:>6,}  ({pct(pendientes_total)})")
    print(f"  Sin match:            {sin_match_total:>6,}  ({pct(sin_match_total)})")
    print(f"  Barrios con data:     {len(por_barrio)}/{len(barrio_meta)}")
    print(f"\n[archivo] {out_path}  ({out_path.stat().st_size/1024:,.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
