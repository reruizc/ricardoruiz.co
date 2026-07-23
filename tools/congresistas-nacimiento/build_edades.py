#!/usr/bin/env python3
"""Genera congreso-edades.json (hermano de analisis-candidato.html) con la fecha
de nacimiento de los congresistas, para que la ficha muestre la EDAD.

Fuente: perfiles.json (Congreso Visible · 590 fichas de los cuatrienios 2018/2022/2026,
todas con "Fecha de nacimiento"). Se indexa por nombre normalizado con la MISMA regla
que `normPersona()` de analisis-candidato.html (NFD sin tildes, MAYUS, solo A-Z y espacio)
para que el join en el navegador sea directo.

Salida (compacta): { "<KEY NORMALIZADA>": {"n":"Nombre Apellidos","f":"YYYY-MM-DD"} , ... }
La edad NO se precalcula: la calcula el navegador contra la fecha del día (asi no caduca).
"""
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Bases de datos" / "congresistas-nacimiento"

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


def norm_persona(s: str) -> str:
    """Espejo EXACTO de normPersona() en analisis-candidato.html."""
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z ]", " ", s.upper())).strip()


def parse_fecha(s: str):
    """'24 de octubre de 1962' -> '1962-10-24'. Devuelve None si no parsea."""
    if not s:
        return None
    m = re.search(r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})", s.strip(), re.I)
    if not m:
        return None
    dia, mes_txt, anio = int(m.group(1)), m.group(2).lower(), int(m.group(3))
    mes = MESES.get(unicodedata.normalize("NFKD", mes_txt).encode("ascii", "ignore").decode())
    if not mes or not (1 <= dia <= 31) or not (1900 <= anio <= 2010):
        return None
    return f"{anio:04d}-{mes:02d}-{dia:02d}"


def main():
    perfiles = json.loads((OUT / "perfiles.json").read_text(encoding="utf-8"))
    out = {}
    sin_fecha = 0
    for p in sorted(perfiles, key=lambda x: x.get("cuatrienio_id", 0)):  # asc: mas reciente pisa
        nombre = f"{p['nombres']} {p['apellidos']}".strip()
        key = norm_persona(nombre)
        f = parse_fecha(p.get("fecha_nacimiento"))
        if not key:
            continue
        if not f:
            sin_fecha += 1
            continue
        out[key] = {"n": nombre, "f": f}   # el cuatrienio mayor pisa (misma persona, misma fecha)

    dest = ROOT / "congreso-edades.json"
    dest.write_text(json.dumps({
        "v": "2026-07-22",
        "fuente": "Congreso Visible (Universidad de los Andes)",
        "n": len(out),
        "personas": out,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"-> {dest}  ·  {len(out)} personas con fecha  ·  {sin_fecha} sin fecha parseable")


if __name__ == "__main__":
    main()
