#!/usr/bin/env python3
"""
build-divipole-mun/build.py

Lee CIUDADES/DIVIPOLE-MAR2026.csv (13,746 puestos georef) y emite
preguntas/divipole.json con la lista de departamentos y municipios
electorales (códigos de Registraduría, no DANE).

Estructura:
{
  "version": "2026-05-13",
  "departamentos": [
    { "codigo": "01", "nombre": "Antioquia" },
    { "codigo": "11", "nombre": "Bogotá D.C." },
    ...
  ],
  "municipios": {
    "01": [
      { "codigo": "001", "nombre": "Medellín" },
      { "codigo": "002", "nombre": "Abejorral" },
      ...
    ],
    "11": [
      { "codigo": "001", "nombre": "Bogotá D.C." }
    ],
    ...
  }
}

Usado por el frontend del test cuando el usuario hace click en "no vivo
aquí" → cascada depto → municipio → (si es ciudad mapeada) localidad/comuna.

Sin dependencias externas.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV_IN = ROOT / "CIUDADES" / "DIVIPOLE-MAR2026.csv"
OUT = ROOT / "preguntas" / "divipole.json"

# Override de nombres para que queden con tildes correctas (el CSV viene en
# MAYÚSCULA sin tildes). Solo los más comunes / capitales.
NOMBRE_OVERRIDE = {
    "BOGOTA D.C.": "Bogotá D.C.",
    "MEDELLIN": "Medellín",
    "POPAYAN": "Popayán",
    "MONTERIA": "Montería",
    "IBAGUE": "Ibagué",
    "CUCUTA": "Cúcuta",
    "CARTAGENA": "Cartagena",
    "BARRANQUILLA": "Barranquilla",
    "MANIZALES": "Manizales",
    "BUCARAMANGA": "Bucaramanga",
    "PEREIRA": "Pereira",
    "PASTO": "Pasto",
    "NEIVA": "Neiva",
    "VILLAVICENCIO": "Villavicencio",
    "SINCELEJO": "Sincelejo",
    "TUNJA": "Tunja",
    "SANTA MARTA": "Santa Marta",
    "VALLEDUPAR": "Valledupar",
    "FLORENCIA": "Florencia",
    "YOPAL": "Yopal",
    "RIOHACHA": "Riohacha",
    "MITU": "Mitú",
    "ARMENIA": "Armenia",
    "QUIBDO": "Quibdó",
    "ANTIOQUIA": "Antioquia",
    "ATLANTICO": "Atlántico",
    "BOLIVAR": "Bolívar",
    "BOYACA": "Boyacá",
    "CALDAS": "Caldas",
    "CAQUETA": "Caquetá",
    "CASANARE": "Casanare",
    "CAUCA": "Cauca",
    "CESAR": "Cesar",
    "CHOCO": "Chocó",
    "CORDOBA": "Córdoba",
    "CUNDINAMARCA": "Cundinamarca",
    "GUAINIA": "Guainía",
    "GUAVIARE": "Guaviare",
    "HUILA": "Huila",
    "LA GUAJIRA": "La Guajira",
    "MAGDALENA": "Magdalena",
    "META": "Meta",
    "NARIÑO": "Nariño",
    "NORTE DE SANTANDER": "Norte de Santander",
    "PUTUMAYO": "Putumayo",
    "QUINDIO": "Quindío",
    "RISARALDA": "Risaralda",
    "SAN ANDRES": "San Andrés y Providencia",
    "SANTANDER": "Santander",
    "SUCRE": "Sucre",
    "TOLIMA": "Tolima",
    "VALLE": "Valle del Cauca",
    "VAUPES": "Vaupés",
    "VICHADA": "Vichada",
    "AMAZONAS": "Amazonas",
    "ARAUCA": "Arauca",
    "EXTERIOR": "Exterior",
}


def titleize(s):
    """Convierte UPPER a Title Case sensato, con override de tildes."""
    s = (s or "").strip()
    if not s:
        return ""
    if s in NOMBRE_OVERRIDE:
        return NOMBRE_OVERRIDE[s]
    # Default: title case
    return s.title()


def main():
    deptos = {}     # codigo → nombre
    municipios = {} # codigo_depto → { codigo_mun: nombre }

    with open(CSV_IN, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            dd = (row.get("dd") or "").strip()
            mm = (row.get("mm") or "").strip()
            dep_nom = row.get("departamento") or ""
            mun_nom = row.get("municipio") or ""
            if not dd or not mm or not dep_nom or not mun_nom:
                continue
            deptos[dd] = titleize(dep_nom)
            municipios.setdefault(dd, {})[mm] = titleize(mun_nom)

    # Output ordenado
    out = {
        "version": "2026-05-13",
        "fuente": "Divipole Registraduría marzo 2026",
        "departamentos": [
            {"codigo": cod, "nombre": nom}
            for cod, nom in sorted(deptos.items(), key=lambda kv: kv[1])
        ],
        "municipios": {
            dd: [
                {"codigo": mc, "nombre": mn}
                for mc, mn in sorted(muns.items(), key=lambda kv: kv[1])
            ]
            for dd, muns in municipios.items()
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size_kb = OUT.stat().st_size / 1024

    total_muns = sum(len(v) for v in municipios.values())
    print(f"✓ {OUT.relative_to(ROOT)}")
    print(f"  {len(deptos)} departamentos · {total_muns} municipios")
    print(f"  tamaño: {size_kb:.0f} KB")
    print()
    print("Departamentos (primeros 5):")
    for d in out["departamentos"][:5]:
        n_muns = len(municipios.get(d["codigo"], {}))
        print(f"  {d['codigo']}  {d['nombre']:<25}  {n_muns} municipios")


if __name__ == "__main__":
    main()
