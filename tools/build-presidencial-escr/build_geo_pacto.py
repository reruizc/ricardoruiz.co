#!/usr/bin/env python3
"""
Comuna/localidad y barrio de cada puesto de la consulta del Pacto Histórico 2025,
para los filtros de consultas-pacto-2025.html (departamento → municipio →
comuna/localidad → barrio → puesto → mesa).

El árbol de la consulta (dep-XX.json) llega hasta el puesto, pero solo con su
código y su nombre. La comuna y el barrio salen de PUESTOS_GEOREF.csv (censo de
puestos 2026), cruzando por el código de 9 dígitos dep+mun+zona+puesto. La
consulta es de octubre de 2025, así que el código casa casi siempre con el
censo de 2026; lo que no casa queda sin comuna ni barrio y la página lo agrupa
por zona.

Salida: Bases de datos/output_presidencial_escr/pacto2025/geo/{dd}.json
        { "mmm-zz-pp": [comuna, barrio], ... }   (vacío = sin dato)

Uso: python3 tools/build-presidencial-escr/build_geo_pacto.py
"""
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/Users/ricardoruiz/ricardoruiz.co")
GEOREF = ROOT / "Bases de datos/PUESTOS_GEOREF.csv"
DIR = ROOT / "Bases de datos/output_presidencial_escr/pacto2025"
NULOS = {"", "NULL", "NAN", "NONE", "SIN BARRIO", "SIN INFORMACION", "N/A", "NA", "-"}


def limpio(s):
    s = re.sub(r"\s+", " ", (s or "").strip()).upper()
    # Medellín trae a veces el código de comuna pegado al nombre: «16COMUNA 16 BELEN».
    s = re.sub(r"^\d+(?=[A-ZÁÉÍÓÚÑ])", "", s)
    return "" if s in NULOS else s


def clave(s):
    s = unicodedata.normalize("NFD", s.upper())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"^(LA|EL|LOS|LAS) ", "", s)   # «LA CANDELARIA» = «CANDELARIA»
    return re.sub(r"[^A-Z0-9]", "", s)


def main():
    geo = {}
    with GEOREF.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            cod = (r.get("CÓDIGO COMPLETO") or "").strip()
            if len(cod) < 9:
                cod = cod.zfill(9)
            geo[cod] = (limpio(r.get("NOMBRE COMUNA")), limpio(r.get("BARRIO")))

    (DIR / "geo").mkdir(exist_ok=True)
    tot = casan = 0
    for fp in sorted(DIR.glob("dep-*.json")):
        d = json.loads(fp.read_text(encoding="utf-8"))
        dd = d["cod"].zfill(2)
        filas = {}
        # La misma comuna o el mismo barrio llega escrito de varias formas
        # («CIUDAD BOLÍVAR» y «CIUDAD BOLIVAR»): se unifican por municipio con
        # la forma más frecuente, si no el filtro los mostraría dos veces.
        formas = defaultdict(Counter)
        for m in d.get("municipios", []):
            mmm = m["cod"].zfill(3)
            for z in m.get("zonas", []):
                zz = z["cod"].zfill(2)
                for p in z.get("puestos", []):
                    pp = p["cod"].zfill(2)
                    tot += 1
                    com, bar = geo.get(dd + mmm + zz + pp, ("", ""))
                    if com or bar:
                        casan += 1
                    filas[f"{mmm}-{zz}-{pp}"] = [com, bar]
                    if com:
                        formas[(mmm, "c", clave(com))][com] += 1
                    if bar:
                        formas[(mmm, "b", clave(bar))][bar] += 1
        for k, (com, bar) in filas.items():
            mmm = k[:3]
            if com:
                com = formas[(mmm, "c", clave(com))].most_common(1)[0][0]
            if bar:
                bar = formas[(mmm, "b", clave(bar))].most_common(1)[0][0]
            filas[k] = [com, bar]
        (DIR / "geo" / f"{dd}.json").write_text(
            json.dumps(filas, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{casan:,} de {tot:,} puestos con comuna o barrio ({casan / tot * 100:.1f} %)")


if __name__ == "__main__":
    main()
