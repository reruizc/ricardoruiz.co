#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_ips.py — listado de IPS por departamento para el autocompletar de e_ips.

Fuente: REPS oficial (Registro Especial de Prestadores) en datos.gov.co,
dataset `c36g-9fc2`. Se filtra a la clase IPS y se deduplica a UNA fila por
IPS-entidad (agrupando por `codigoprestador`, el ID estable del prestador;
el dataset trae una fila por sede). 10.939 IPS únicas.

Como son ~11 mil (demasiado para embeber inline como el divipola), se parte por
departamento (mismo patrón que los municipios del proyecto) y cada archivo se
sube a S3; el frontend baja solo el del departamento de los hechos, bajo demanda.

Uso:
    python3 tools/tutela-analiza/build_ips.py

Salidas (gitignored salvo el índice):
    Bases de datos/tutelas-salud/ips/ips-{cod_dpto}.json   (por depto, claves cortas)
    tools/tutela-analiza/ips-index.json                    (cod_dpto -> nombre + conteo)
"""

import json
import os
import re
import subprocess
import sys
import urllib.parse
from collections import defaultdict

# Acrónimo con puntos: S.A.S., I.P.S., E.S.E., D.C., U.T., E.U. …
DOTTED_RE = re.compile(r"^(?:[a-zñ]\.){1,}[a-zñ]?\.?$", re.I)

RESOURCE = "c36g-9fc2"
BASE = f"https://www.datos.gov.co/resource/{RESOURCE}.json"
CLASE_IPS = "Instituciones Prestadoras de Servicios de Salud - IPS"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(ROOT, "Bases de datos", "tutelas-salud", "ips")
INDEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ips-index.json")


def fetch(params, intentos=4):
    url = BASE + "?" + urllib.parse.urlencode(params)
    for i in range(intentos):
        try:
            r = subprocess.run(["curl", "-s", "-m", "120", "-A", UA, url],
                               capture_output=True, timeout=150)
            txt = r.stdout.decode("utf-8", errors="replace")
            if not txt.strip():
                raise ValueError("respuesta vacía")
            data = json.loads(txt)
            if isinstance(data, dict) and data.get("error"):
                raise ValueError(data.get("message", "error Socrata"))
            return data
        except Exception as e:
            if i == intentos - 1:
                raise
            print(f"  reintento {i + 1} tras: {e}", flush=True)
    return []


def titlecase(s):
    """REPS trae nombres en MAYÚSCULA. Título legible, respetando siglas."""
    s = " ".join((s or "").split())
    if not s:
        return s
    small = {"de", "del", "la", "las", "los", "el", "y", "e", "en", "a"}
    keep = {"IPS", "EPS", "ESE", "SAS", "SA", "LTDA", "ONG", "UT", "EU",
            "SES", "HUV", "HOMI", "SURA"}
    out = []
    for i, w in enumerate(s.split(" ")):
        if DOTTED_RE.match(w):            # S.A.S., I.P.S., D.C. …
            out.append(w.upper())
        elif w.upper() in keep:           # siglas sin puntos
            out.append(w.upper())
        else:
            lw = w.lower()
            out.append(lw if (i > 0 and lw in small) else (lw[:1].upper() + lw[1:]))
    return " ".join(out)


def main():
    print(f"Descargando IPS del REPS ({RESOURCE})…", flush=True)
    filas = fetch({
        "$select": ("codigoprestador, max(nombreprestador) AS nombre, "
                    "max(municipioprestadordesc) AS municipio, "
                    "max(municipio_prestador) AS cod_mpio, "
                    "max(departamentoprestadordesc) AS depto"),
        "$where": f"claseprestador='{CLASE_IPS}'",
        "$group": "codigoprestador",
        "$limit": 50000,
    })
    print(f"  {len(filas)} IPS únicas", flush=True)

    por_dpto = defaultdict(list)
    depto_nombre = {}
    vistos = defaultdict(set)  # cod_dpto -> set de (nombre_norm, municipio) para dedup exacto
    for r in filas:
        nombre = titlecase(r.get("nombre"))
        muni = titlecase(r.get("municipio"))
        cod = (r.get("cod_mpio") or "").strip()
        if not nombre or len(cod) < 4:
            continue
        cod_dpto = cod[:-3] if len(cod) == 5 else cod[:2]
        cod_dpto = cod_dpto.zfill(2)
        clave = (nombre.lower(), muni.lower())
        if clave in vistos[cod_dpto]:
            continue
        vistos[cod_dpto].add(clave)
        por_dpto[cod_dpto].append({"n": nombre, "m": muni})
        if r.get("depto"):
            depto_nombre[cod_dpto] = titlecase(r.get("depto"))

    os.makedirs(OUT_DIR, exist_ok=True)
    index = {}
    total = 0
    for cod_dpto, lst in sorted(por_dpto.items()):
        lst.sort(key=lambda x: x["n"])
        path = os.path.join(OUT_DIR, f"ips-{cod_dpto}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(lst, f, ensure_ascii=False, separators=(",", ":"))
        index[cod_dpto] = {"depto": depto_nombre.get(cod_dpto, ""), "n": len(lst)}
        total += len(lst)

    with open(INDEX, "w", encoding="utf-8") as f:
        json.dump({"v": RESOURCE, "total": total, "deptos": index}, f,
                  ensure_ascii=False, indent=1)

    tam = sum(os.path.getsize(os.path.join(OUT_DIR, x)) for x in os.listdir(OUT_DIR))
    print(f"  {len(index)} departamentos · {total} IPS · {tam/1024:.0f} KB total")
    grandes = sorted(index.items(), key=lambda kv: -kv[1]["n"])[:5]
    for c, info in grandes:
        print(f"    {c} {info['depto']:<20} {info['n']:>5} IPS")
    print(f"  -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
