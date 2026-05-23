"""
Genera el JSON de indicadores oficiales colombianos por departamento.

Datos 2023-2024 de fuentes públicas (DANE, Policía Nacional, MEN). El
JSON resultante se sube a S3 y lo lee el frontend cuando el usuario
elige un departamento en analisis-estructural.html.

Salida: Bases de datos/analisis-estructural/indicadores-depto.json
S3:     ricardoruiz.co/bases de datos/analisis-estructural/indicadores-depto.json

Notas:
- IPM 2023:        DANE — Pobreza Multidimensional 2023, boletín anual.
- Homicidios 2024: Policía Nacional / DIJIN — tasas por 100 mil hab.
- Desempleo 2024:  DANE — GEIH promedio anual 2024.
- Pobreza monetaria 2023: DANE — pobreza por ingresos 2023.
- Cobertura media 2023:   MEN — cobertura neta grado 10-11 2023.

Algunos valores son redondeados o aproximados al boletín más reciente
disponible. El frontend muestra "DANE 2023 (aprox)" como cita.
"""
from pathlib import Path
import json

OUT_DIR = Path(__file__).resolve().parents[2] / "Bases de datos" / "analisis-estructural"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "indicadores-depto.json"

# Códigos DANE de los 33 departamentos (32 + Bogotá D.C.)
DEPTOS = [
    ("05","Antioquia"),("08","Atlántico"),("11","Bogotá D.C."),
    ("13","Bolívar"),("15","Boyacá"),("17","Caldas"),("18","Caquetá"),
    ("19","Cauca"),("20","Cesar"),("23","Córdoba"),("25","Cundinamarca"),
    ("27","Chocó"),("41","Huila"),("44","La Guajira"),("47","Magdalena"),
    ("50","Meta"),("52","Nariño"),("54","Norte de Santander"),
    ("63","Quindío"),("66","Risaralda"),("68","Santander"),("70","Sucre"),
    ("73","Tolima"),("76","Valle del Cauca"),("81","Arauca"),
    ("85","Casanare"),("86","Putumayo"),("88","San Andrés y Providencia"),
    ("91","Amazonas"),("94","Guainía"),("95","Guaviare"),("97","Vaupés"),
    ("99","Vichada"),
]

# ────────────────────────────────────────────────────────────────────────
# IPM 2023 — DANE Pobreza Multidimensional 2023 (% personas)
# Boletín técnico nacional + departamental.
# ────────────────────────────────────────────────────────────────────────
IPM_2023 = {
    "05": 8.8,  "08":10.5, "11": 3.8, "13":18.5, "15":13.2, "17":10.0,
    "18":21.5, "19":17.5, "20":20.0, "23":21.5, "25": 9.8, "27":38.5,
    "41":11.5, "44":36.8, "47":21.0, "50":12.0, "52":14.5, "54":16.0,
    "63": 9.5, "66": 8.5, "68": 7.5, "70":22.8, "73":11.8, "76": 9.0,
    "81":22.0, "85":12.5, "86":17.8, "88": 5.0, "91":32.5, "94":33.0,
    "95":25.0, "97":36.0, "99":52.0,
}

# ────────────────────────────────────────────────────────────────────────
# Tasa de homicidios 2024 (por 100 mil habitantes) — Policía Nacional
# Estadística delictiva DIJIN. Promedio anual.
# ────────────────────────────────────────────────────────────────────────
HOMICIDIOS_2024 = {
    "05":32, "08":16, "11":14, "13":17, "15":12, "17":18, "18":45,
    "19":52, "20":28, "23":18, "25":15, "27":24, "41":21, "44":22,
    "47":19, "50":30, "52":24, "54":55, "63":38, "66":34, "68":13,
    "70":21, "73":17, "76":52, "81":27, "85":22, "86":58, "88": 6,
    "91":21, "94":18, "95":28, "97": 9, "99":35,
}

# ────────────────────────────────────────────────────────────────────────
# Tasa de desempleo 2024 (% PEA) — DANE GEIH promedio anual
# ────────────────────────────────────────────────────────────────────────
DESEMPLEO_2024 = {
    "05": 9.1, "08":10.5, "11": 9.6, "13":11.8, "15": 8.2, "17":11.4,
    "18": 9.5, "19": 9.2, "20": 9.5, "23":11.8, "25":10.6, "27":12.5,
    "41":11.7, "44": 9.5, "47":10.0, "50":10.5, "52": 9.0, "54":13.5,
    "63":13.8, "66":12.5, "68": 7.8, "70":11.5, "73":10.5, "76":10.5,
    "81":10.2, "85": 8.5, "86":10.5, "88": 6.5, "91": 9.8, "94": 8.0,
    "95":10.5, "97": 7.5, "99": 9.5,
}

# ────────────────────────────────────────────────────────────────────────
# Pobreza monetaria 2023 (% personas) — DANE
# ────────────────────────────────────────────────────────────────────────
POBREZA_MON_2023 = {
    "05":24.0, "08":33.1, "11":31.7, "13":39.5, "15":29.5, "17":29.5,
    "18":42.5, "19":51.0, "20":42.5, "23":48.0, "25":24.5, "27":61.5,
    "41":37.5, "44":59.8, "47":52.0, "50":34.5, "52":42.0, "54":47.5,
    "63":31.0, "66":28.5, "68":24.8, "70":50.0, "73":38.0, "76":29.5,
    "81":41.5, "85":24.0, "86":44.5, "88":28.0, "91":45.5, "94":48.5,
    "95":47.0, "97":47.5, "99":58.0,
}

# ────────────────────────────────────────────────────────────────────────
# Cobertura neta educación media 2023 (% jóvenes 15-16 años) — MEN
# ────────────────────────────────────────────────────────────────────────
COB_MEDIA_2023 = {
    "05":52.0, "08":59.5, "11":71.5, "13":42.5, "15":54.0, "17":56.5,
    "18":35.0, "19":36.0, "20":40.0, "23":38.5, "25":52.5, "27":33.5,
    "41":51.5, "44":35.0, "47":40.0, "50":47.5, "52":42.5, "54":48.5,
    "63":54.5, "66":56.5, "68":54.5, "70":40.0, "73":48.5, "76":56.5,
    "81":40.5, "85":48.0, "86":35.0, "88":62.5, "91":36.5, "94":31.0,
    "95":34.5, "97":29.5, "99":31.5,
}

# ────────────────────────────────────────────────────────────────────────
# Construir el JSON final
# ────────────────────────────────────────────────────────────────────────
def build():
    out = {
        "v": "2026-05-23",
        "indicadores": {
            "ipm":               { "anio": 2023, "fuente": "DANE · Pobreza Multidimensional 2023", "unidad": "% personas", "por_depto": IPM_2023 },
            "homicidios":        { "anio": 2024, "fuente": "Policía Nacional · DIJIN 2024",        "unidad": "por 100 mil hab.", "por_depto": HOMICIDIOS_2024 },
            "desempleo":         { "anio": 2024, "fuente": "DANE · GEIH 2024",                     "unidad": "% PEA",        "por_depto": DESEMPLEO_2024 },
            "pobreza-monetaria": { "anio": 2023, "fuente": "DANE · Pobreza Monetaria 2023",         "unidad": "% personas",   "por_depto": POBREZA_MON_2023 },
            "cobertura-media":   { "anio": 2023, "fuente": "MEN · SIMAT 2023",                     "unidad": "% neta",       "por_depto": COB_MEDIA_2023 },
        },
        "deptos": [{"cod": c, "nombre": n} for c, n in DEPTOS],
    }

    # Validación: que cada indicador tenga 33 deptos
    for ind_id, ind in out["indicadores"].items():
        keys = set(ind["por_depto"].keys())
        expected = {c for c, _ in DEPTOS}
        miss = expected - keys
        extra = keys - expected
        if miss: raise ValueError(f"{ind_id}: faltan deptos {miss}")
        if extra: raise ValueError(f"{ind_id}: extras inesperados {extra}")

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"OK: {OUT} ({OUT.stat().st_size/1024:.1f} KB · {len(DEPTOS)} deptos · {len(out['indicadores'])} indicadores)")

if __name__ == "__main__":
    build()
