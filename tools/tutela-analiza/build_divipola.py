#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_divipola.py — lista depto→municipios para los selectores de tutelas-salud.html.

Se construye desde el MISMO universo de la Corte Constitucional (`wamb-dzb6`,
todas las tutelas, mejor cobertura de municipios que el subconjunto de salud),
así los nombres de departamento calzan EXACTO con los que usa el score
(`tasas-tutela-salud.json`) — cero fricción de join — y quedan en código DANE.

Se prefiere esta fuente al `divipola.json` de la Registraduría del repo, que usa
códigos electorales (Antioquia=01, no 05) y nombres sin tildes.

Salida (se embebe inline en el HTML para no romper la promesa de "sin fetch"):
    tools/tutela-analiza/divipola-corte.json
"""

import json
import os
import subprocess
import sys
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone

RESOURCE = "wamb-dzb6"
BASE = f"https://www.datos.gov.co/resource/{RESOURCE}.json"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "divipola-corte.json")


def fetch(params, intentos=4):
    url = BASE + "?" + urllib.parse.urlencode(params)
    for i in range(intentos):
        try:
            r = subprocess.run(["curl", "-s", "-m", "90", "-A", UA, url],
                               capture_output=True, timeout=120)
            txt = r.stdout.decode("utf-8", errors="replace")
            if not txt.strip():
                raise ValueError("respuesta vacía")
            return json.loads(txt)
        except Exception as e:
            if i == intentos - 1:
                raise
            print(f"    reintento {i + 1} tras: {e}", flush=True)
    return []


def main():
    print("Descargando municipios distintos de la Corte…", flush=True)
    filas, off, LIM = [], 0, 5000
    while True:
        lote = fetch({
            "$select": "departamento, cod_dpto, municipio, cod_mpio",
            "$group": "departamento, cod_dpto, municipio, cod_mpio",
            "$limit": LIM, "$offset": off,
        })
        filas.extend(lote)
        if len(lote) < LIM:
            break
        off += LIM

    deptos = defaultdict(lambda: {"nombre": "", "muns": {}})
    for r in filas:
        dn = (r.get("departamento") or "").strip()
        dc = (r.get("cod_dpto") or "").strip()
        mn = (r.get("municipio") or "").strip()
        mc = (r.get("cod_mpio") or "").strip()
        # descarta "Sin Registro", exterior y filas incompletas
        if not dn or not dc or dc.upper() == "NA" or not mn or not mc:
            continue
        if dn.lower().startswith("sin registro") or mn.lower().startswith("sin registro"):
            continue
        deptos[dc]["nombre"] = dn
        deptos[dc]["muns"][mc] = mn

    out_deptos = []
    for dc in sorted(deptos):
        muns = [{"cod": mc, "nombre": mn}
                for mc, mn in sorted(deptos[dc]["muns"].items(),
                                     key=lambda kv: kv[1])]
        out_deptos.append({"cod": dc, "nombre": deptos[dc]["nombre"], "muns": muns})

    out = {
        "v": datetime.now(timezone.utc).strftime("%Y%m%d"),
        "fuente": f"Corte Constitucional · datos.gov.co · {RESOURCE} (códigos DANE)",
        "deptos": out_deptos,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    nmun = sum(len(d["muns"]) for d in out_deptos)
    kb = os.path.getsize(OUT) / 1024
    print(f"  {len(out_deptos)} departamentos · {nmun} municipios · {kb:.0f} KB")
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
