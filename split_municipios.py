import json
import os
import re
import unicodedata

# ── Mapping: DANE dept code → electoral dept code (CNE) ──────────────────────
DANE_TO_ELECTORAL = {
    "05": "01",  # ANTIOQUIA
    "08": "03",  # ATLÁNTICO
    "11": "16",  # BOGOTÁ, D.C.
    "13": "05",  # BOLÍVAR
    "15": "07",  # BOYACÁ
    "17": "09",  # CALDAS
    "18": "44",  # CAQUETÁ
    "19": "11",  # CAUCA
    "20": "12",  # CESAR
    "23": "13",  # CÓRDOBA
    "25": "15",  # CUNDINAMARCA
    "27": "17",  # CHOCÓ
    "41": "19",  # HUILA
    "44": "48",  # LA GUAJIRA
    "47": "21",  # MAGDALENA
    "50": "52",  # META
    "52": "23",  # NARIÑO
    "54": "25",  # NORTE DE SANTANDER
    "63": "26",  # QUINDÍO
    "66": "24",  # RISARALDA
    "68": "27",  # SANTANDER
    "70": "28",  # SUCRE
    "73": "29",  # TOLIMA
    "76": "31",  # VALLE DEL CAUCA
    "81": "40",  # ARAUCA
    "85": "46",  # CASANARE
    "86": "64",  # PUTUMAYO
    "88": "56",  # SAN ANDRÉS
    "91": "60",  # AMAZONAS
    "94": "50",  # GUAINÍA
    "95": "54",  # GUAVIARE
    "97": "68",  # VAUPÉS
    "99": "72",  # VICHADA
}

# ── Excepciones hardcodeadas: (dep_electoral, mpio_ccdgo) → mun_electoral ────
# Solo para los nombres que ninguna estrategia automática puede resolver.
# None = municipio sin datos electorales (muy pequeño/remoto).
HARDCODED = {
    # Bolívar
    ("05", "468"): "043",  # SANTA CRUZ DE MOMPOX → MOMPOS
    # Boyacá
    ("07", "407"): "139",  # VILLA DE LEYVA → VILLA DE LEIVA
    # Cundinamarca
    ("15", "843"): "304",  # VILLA DE SAN DIEGO DE UBATÉ → UBATE
    # Bogotá
    ("16", "001"): "001",  # BOGOTÁ, D.C. → BOGOTA. D.C.
    # Sucre
    ("28", "742"): "260",  # SAN LUIS DE SINCÉ → SINCE (4 chars, bajo umbral auto)
    ("28", "820"): "300",  # SANTIAGO DE TOLÚ → TOLU (4 chars, bajo umbral auto)
    # Valle del Cauca
    ("31", "001"): "001",  # SANTIAGO DE CALI → CALI (4 chars, bajo umbral auto)
    ("31", "111"): "022",  # GUADALAJARA DE BUGA → BUGA (4 chars, bajo umbral auto)
    # Amazonas
    ("60", "460"): "019",  # MIRITÍ - PARANÁ → MIRITI PARANA (guion confunde norm)
    ("60", "530"): None,   # PUERTO ALEGRÍA — sin datos electorales
    ("60", "669"): None,   # PUERTO SANTANDER (Amazonas) — sin datos electorales
    # Guainía
    ("50", "885"): None,   # LA GUADALUPE — sin datos electorales
    # Vaupés
    ("68", "511"): "013",  # PACOA → BUENOS AIRES (PACOA) (nombre en paréntesis)
    ("68", "777"): "010",  # PAPUNAHUA → MORICHAL (PAPUNAGUA) (transliteración distinta)
}


def norm(s):
    """Normaliza: mayúsculas, sin tildes, espacios simples."""
    s = unicodedata.normalize("NFD", str(s).upper().strip())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s)


def strip_paren(s):
    """'ALTO BAUDO (PIE DE PATO)' → 'ALTO BAUDO'"""
    return re.sub(r"\s*\(.*", "", s).strip()


def strip_after_dash(s):
    """'PUERTO NARE-LA MAGDALENA' → 'PUERTO NARE'"""
    return re.sub(r"\s*[-–].*", "", s).strip()


def strip_leading_article(s):
    """'EL CARMEN DE ATRATO' → 'CARMEN DE ATRATO'"""
    return re.sub(r"^(EL|LA|LOS|LAS)\s+", "", s).strip()


def remove_spaces(s):
    """'DON MATIAS' → 'DONMATIAS'"""
    return s.replace(" ", "")


def build_electoral_index(electoral_data):
    """Construye índice por dep: {dep_elec: {norm_name_variant: mun_code}}"""
    idx = {}
    for m in electoral_data["mesas"]:
        dep = m["dep"]
        mun = m["mun"]
        if dep not in idx:
            idx[dep] = {}
        name = norm(m["munNom"])
        # Registrar múltiples variantes del nombre electoral
        for variant in [
            name,
            strip_paren(name),
            strip_after_dash(name),
            strip_leading_article(name),
            remove_spaces(name),
            strip_paren(strip_after_dash(name)),
        ]:
            if variant and variant not in idx[dep]:
                idx[dep][variant] = mun
    return idx


def match_mun(geo_name_raw, dep_elec, elec_idx):
    """
    Intenta encontrar el mun_electoral para un nombre de municipio del GeoJSON.
    Devuelve el código electoral o None si no hay match.
    """
    dep = elec_idx.get(dep_elec, {})
    if not dep:
        return None

    geo = norm(geo_name_raw)
    geo_no_art = strip_leading_article(geo)
    geo_nospace = remove_spaces(geo)

    # Estrategia 1: exacto
    if geo in dep:
        return dep[geo]

    # Estrategia 2: sin artículo inicial en el nombre geo
    if geo_no_art and geo_no_art in dep:
        return dep[geo_no_art]

    # Estrategia 3: sin espacios (DONMATIAS == DON MATIAS)
    for elec_name, mun_code in dep.items():
        if remove_spaces(elec_name) == geo_nospace:
            return mun_code

    # Estrategia 4: el nombre geo es prefijo del electoral
    # (PUERTO NARE es prefijo de PUERTO NARE-LA MAGDALENA)
    for elec_name, mun_code in dep.items():
        if elec_name.startswith(geo + " ") or elec_name.startswith(geo + "-"):
            return mun_code
        if geo_no_art and (
            elec_name.startswith(geo_no_art + " ")
            or elec_name.startswith(geo_no_art + "-")
        ):
            return mun_code

    # Estrategia 5: el nombre electoral es prefijo del geo (min 5 chars)
    # (CARTAGENA es prefijo de CARTAGENA DE INDIAS; GUICAN de GUICAN DE LA SIERRA)
    for elec_name, mun_code in dep.items():
        if len(elec_name) >= 5 and (
            geo.startswith(elec_name + " ") or geo_no_art.startswith(elec_name + " ")
        ):
            return mun_code

    # Estrategia 6: el nombre electoral está contenido en el geo (min 6 chars)
    # (BOLIVAR en CIUDAD BOLIVAR)
    for elec_name, mun_code in dep.items():
        if len(elec_name) >= 6 and elec_name in geo:
            return mun_code

    return None


# ── Main ──────────────────────────────────────────────────────────────────────
INPUT_FILE = os.path.join(os.path.dirname(__file__), "MUNICIPIOSX.json")
ELECTORAL_FILE = os.path.join(os.path.dirname(__file__), "EJEMPLO-CANDIDATA.json")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "departamentos")

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Cargando MUNICIPIOSX.json...")
with open(INPUT_FILE, encoding="utf-8") as f:
    geojson = json.load(f)

print("Cargando EJEMPLO-CANDIDATA.json para mapeo de municipios...")
with open(ELECTORAL_FILE, encoding="utf-8") as f:
    electoral_data = json.load(f)

elec_idx = build_electoral_index(electoral_data)

# Agrupar features por código DANE de departamento
by_dane = {}
for feature in geojson["features"]:
    props = feature["properties"]
    dane_code = props["dpto_ccdgo"]
    if dane_code not in by_dane:
        by_dane[dane_code] = []
    by_dane[dane_code].append(feature)

index = []
total_matched = 0
total_unmatched = 0

for dane_code, features in sorted(by_dane.items()):
    electoral_code = DANE_TO_ELECTORAL.get(dane_code)
    if not electoral_code:
        print(f"  ADVERTENCIA: sin código electoral para DANE {dane_code}, omitiendo.")
        continue

    dept_name = features[0]["properties"]["dpto_cnmbr"]
    dept_unmatched = []

    enriched_features = []
    for feat in features:
        props = feat["properties"]
        mpio_ccdgo = props["mpio_ccdgo"]
        mpio_name = props["mpio_cnmbr"]

        # Resolver mun_elec: hardcode > matcher automático
        hardcode_key = (electoral_code, mpio_ccdgo)
        if hardcode_key in HARDCODED:
            mun_elec = HARDCODED[hardcode_key]
        else:
            mun_elec = match_mun(mpio_name, electoral_code, elec_idx)

        if mun_elec:
            total_matched += 1
        else:
            total_unmatched += 1
            dept_unmatched.append(f"{mpio_ccdgo}={mpio_name}")

        enriched = dict(feat)
        enriched["properties"] = dict(props)
        enriched["properties"]["dep_electoral"] = electoral_code
        enriched["properties"]["mun_electoral"] = mpio_ccdgo   # DANE (para referencia)
        enriched["properties"]["mun_elec"] = mun_elec          # CÓDIGO ELECTORAL (para match votos)
        enriched_features.append(enriched)

    collection = {
        "type": "FeatureCollection",
        "dep_dane": dane_code,
        "dep_electoral": electoral_code,
        "dep_nombre": dept_name,
        "features": enriched_features,
    }

    # Bounding box
    all_coords = []
    for feat in enriched_features:
        geom = feat["geometry"]
        if geom["type"] == "Polygon":
            for ring in geom["coordinates"]:
                all_coords.extend(ring)
        elif geom["type"] == "MultiPolygon":
            for polygon in geom["coordinates"]:
                for ring in polygon:
                    all_coords.extend(ring)

    bbox = None
    if all_coords:
        lons = [c[0] for c in all_coords]
        lats = [c[1] for c in all_coords]
        bbox = [min(lons), min(lats), max(lons), max(lats)]
        collection["bbox"] = bbox

    out_path = os.path.join(OUTPUT_DIR, f"{electoral_code}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(collection, f, ensure_ascii=False, separators=(",", ":"))

    status = ""
    if dept_unmatched:
        status = f"  ⚠ sin match: {', '.join(dept_unmatched)}"
    print(f"  {electoral_code}.json → {dept_name} ({len(features)} muns){status}")

    index.append({
        "dep_electoral": electoral_code,
        "dep_dane": dane_code,
        "nombre": dept_name,
        "file": f"departamentos/{electoral_code}.json",
        "municipios": len(features),
        "bbox": bbox,
    })

# Índice
index.sort(key=lambda x: x["dep_electoral"])
index_path = os.path.join(OUTPUT_DIR, "index.json")
with open(index_path, "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

print(f"\nListo. {len(index)} departamentos | matched={total_matched} | sin match={total_unmatched}")
