#!/usr/bin/env python3
"""
build-ciudades-zonas/build.py

Lee los GeoJSON de CIUDADES/ y emite preguntas/ciudades-zonas.json con la
lista de localidades / comunas / barrios por ciudad. El test usa este JSON
para mostrar un dropdown contextual en el formulario demográfico — el
geojson completo NO se carga en frontend (eso sigue siendo trabajo del
worker, que ya tiene Bogotá/Medellín/Cali para PiP).

Sin dependencias externas — stdlib pura.

Output: preguntas/ciudades-zonas.json
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CIUDADES_DIR = ROOT / "CIUDADES"
OUT = ROOT / "preguntas" / "ciudades-zonas.json"

# Mapa: key normalizada (alineada con GEO.city de Cloudflare) → {file, code_key, name_key, label, build_name?}
# label = "localidad" o "comuna" o "barrio" (lo que aparece en la UI: "¿en qué X vives?")
# build_name = función opcional (lambda) que construye el nombre desde el dict de properties.
#   Útil para ciudades donde solo hay código numérico (Bucaramanga, Cúcuta).
CIUDADES = {
    "Bogotá": {
        "file": "BOGOTA/BOG-LOCALIDADX.json",
        "code_key": "LocCodigo",
        "name_key": "LocNombre",
        "label": "localidad",
        "aliases": ["Bogota", "Bogotá D.C.", "Bogota D.C."],
    },
    "Medellín": {
        "file": "MEDELLIN/MEDELLINX.json",
        "code_key": "CODIGO",
        "name_key": "NOMBRE",
        "label": "comuna",
        "aliases": ["Medellin"],
    },
    "Cali": {
        "file": "CALI/CALIX.json",
        "code_key": "comuna",
        "name_key": "nombre",
        "label": "comuna",
        "aliases": ["Santiago de Cali"],
    },
    "Barranquilla": {
        "file": "BARRANQUILLA/BARRANQUILLAX.json",
        "code_key": "id",
        "name_key": "nombre",
        "label": "localidad",
        "aliases": [],
    },
    "Cartagena": {
        "file": "CARTAGENA/CARTAGENAX.json",
        "code_key": "CODIGO",
        "name_key": "NOMBRE",
        "label": "barrio",
        "aliases": ["Cartagena de Indias"],
    },
    "Bucaramanga": {
        "file": "BUCARAMANGA/BUCARAMANGAX.json",
        "code_key": "NOMBRE_COD",
        "name_key": "NOMBRE_COD",
        "label": "comuna",
        "build_name": lambda p: (lambda v: v if isinstance(v, str) and "Comuna" in v else f"Comuna {int(v) if str(v).strip().isdigit() else v}")(p.get("NOMBRE_COD", "")),
        "aliases": [],
    },
    "Manizales": {
        "file": "MANIZALES/MANIZALESX.json",
        "code_key": "ID_COMUNA",
        "name_key": "NOMBRES_CO",
        "label": "comuna",
        "aliases": [],
    },
    "Pasto": {
        "file": "PASTO/PASTOX.json",
        "code_key": "CODIGO",
        "name_key": "NOMBRE",
        "label": "barrio",
        "aliases": ["San Juan de Pasto"],
    },
    "Santa Marta": {
        "file": "SANTA_MARTA/SANTA_MARTAX.json",
        "code_key": "CODIGO",
        "name_key": "NOMBRE",
        "label": "barrio",
        "aliases": ["Santa Marta"],
    },
    "Ibagué": {
        "file": "IBAGUE/IBAGUEX.json",
        "code_key": None,
        "name_key": "COMUNAS",
        "label": "comuna",
        "build_code": lambda p: str(p.get("OBJECTID", "")),
        "aliases": ["Ibague"],
    },
    "Montería": {
        "file": "MONTERIA/MONTERIAX.json",
        "code_key": "CC_COMUNA",
        "name_key": "NMG",
        "label": "comuna",
        "aliases": ["Monteria"],
    },
    "Neiva": {
        "file": "NEIVA/NEIVAX.json",
        "code_key": "FID",
        "name_key": "comuna",
        "label": "comuna",
        "aliases": [],
    },
    "Pereira": {
        "file": "PEREIRA/PEREIRAX.json",
        "code_key": "FID",
        "name_key": "Comuna",
        "label": "comuna",
        "aliases": [],
    },
    "Popayán": {
        "file": "POPAYAN/POPAYANX.json",
        "code_key": "Comuna",
        "name_key": "COMUNAS",
        "label": "comuna",
        "aliases": ["Popayan"],
    },
    "Villavicencio": {
        "file": "VILLAVICENCIO/VILLAVICENCIOX.json",
        "code_key": "FID",
        "name_key": "Comuna",
        "label": "comuna",
        "aliases": [],
    },
    "Cúcuta": {
        "file": "CUCUTA/CUCUTAX.json",
        "code_key": "Comuna",
        "name_key": "Comuna",
        "label": "comuna",
        "build_name": lambda p: f"Comuna {p.get('Comuna') or '?'}",
        "aliases": ["Cucuta", "San José de Cúcuta"],
    },
    "Sincelejo": {
        "file": "SINCELEJO/SINCELEJOX.json",
        "code_key": "FID",
        "name_key": "Nombre",
        "label": "comuna",
        "aliases": [],
    },
}

# Países con consulado / diáspora colombiana significativa, ordenados por relevancia
PAISES = [
    "Estados Unidos", "España", "Venezuela", "Ecuador", "Panamá", "Chile",
    "Argentina", "México", "Canadá", "Italia", "Reino Unido", "Australia",
    "Países Bajos", "Brasil", "Costa Rica", "Suiza", "Francia", "Alemania",
    "Bolivia", "Perú", "República Dominicana", "Cuba", "Aruba", "Curazao",
    "Otro",
]


def extract_zonas(cfg):
    path = CIUDADES_DIR / cfg["file"]
    if not path.exists():
        print(f"  ⚠ {cfg['file']} no existe — saltando")
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    feats = data.get("features", [])
    if not feats:
        return None
    zonas = []
    seen = set()  # dedupe por nombre
    for f in feats:
        p = f.get("properties", {})
        # Código
        if cfg.get("build_code"):
            cod = cfg["build_code"](p)
        elif cfg.get("code_key"):
            cod = str(p.get(cfg["code_key"], "")).strip()
        else:
            cod = ""
        # Nombre
        if cfg.get("build_name"):
            nom = cfg["build_name"](p)
        else:
            nom = str(p.get(cfg["name_key"], "")).strip()
        if not nom or nom == "0":
            continue
        # Limpia formato (capitalize razonable)
        # Si está TODO EN MAYÚSCULA y tiene >3 letras, convertir a Title Case
        if nom.isupper() and len(nom) > 3:
            nom = nom.title()
        # Normaliza "COMUNA  X" → "Comuna X"
        if "  " in nom:
            nom = " ".join(nom.split())
        # Dedupe por nombre
        if nom in seen:
            continue
        seen.add(nom)
        zonas.append({"codigo": cod, "nombre": nom})
    # Ordenar: por código numérico si es entero, si no alfabético
    def sort_key(z):
        c = z["codigo"]
        try:
            return (0, int(c))
        except (ValueError, TypeError):
            return (1, z["nombre"].lower())
    zonas.sort(key=sort_key)
    return zonas


def main():
    out = {
        "version": "2026-05-13",
        "ciudades": {},
        "paises": PAISES,
    }

    for ciudad, cfg in CIUDADES.items():
        zonas = extract_zonas(cfg)
        if not zonas:
            print(f"  ⚠ {ciudad}: sin zonas — saltando")
            continue
        out["ciudades"][ciudad] = {
            "label": cfg["label"],
            "aliases": cfg.get("aliases", []),
            "zonas": zonas,
        }
        print(f"  ✓ {ciudad}: {len(zonas)} {cfg['label']}s")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size_kb = OUT.stat().st_size / 1024
    print(f"\n✓ {OUT.relative_to(ROOT)}  ({size_kb:.0f} KB, {len(out['ciudades'])} ciudades)")


if __name__ == "__main__":
    main()
