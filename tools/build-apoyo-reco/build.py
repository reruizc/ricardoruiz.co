#!/usr/bin/env python3
"""
tools/build-apoyo-reco/build.py

Regenera apoyo-recomendaciones.json a partir del .txt editable
(la fuente de verdad la edita Ricardo a mano: tono + hashtags reales).

Flujo:
  1. Editar  Bases de datos/test-presidencial/apoyo-recomendaciones.txt
  2. python3 tools/build-apoyo-reco/build.py
  3. aws s3 cp Bases\\ de\\ datos/test-presidencial/apoyo-recomendaciones.json \\
       s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/test-presidencial/apoyo-recomendaciones.json \\
       --content-type application/json --cache-control "public, max-age=3600"

El frontend (test-presidencial-2026.html → cargarReco) lo lee de S3.
Estructura del JSON: { v, reco:{registro:{arquetipo:texto}}, hashtags:{cid:[...]} }

Formato esperado del .txt:
  Headers de sección: 'POPULAR …', 'DIGITAL …', 'ANALITICO …', 'HASHTAGS …'
  Dentro de un registro: línea 'arquetipo:' y debajo el texto indentado.
  En HASHTAGS: 'ic  Iván Cepeda  → #uno #dos'
"""

import json
import os
import re
import sys

ROOT = "/Users/ricardoruiz/ricardoruiz.co"
TXT = f"{ROOT}/Bases de datos/test-presidencial/apoyo-recomendaciones.txt"
OUT = f"{ROOT}/Bases de datos/test-presidencial/apoyo-recomendaciones.json"
VERSION = "2026-05-19"

ARQ = {"proteccion", "estabilidad", "supervivencia", "castigo", "pertenencia"}
CANDS = {"ic", "ae", "pv", "sf", "cl", "rb"}


def build(txt_path=TXT, out_path=OUT):
    lines = open(txt_path, encoding="utf-8").read().split("\n")
    reco, hashtags = {}, {}
    section = None
    cur_arq, buf = None, []

    def flush():
        nonlocal cur_arq, buf
        if section in ("popular", "digital", "analitico") and cur_arq and buf:
            reco.setdefault(section, {})[cur_arq] = " ".join(
                w.strip() for w in buf
            ).strip()
        cur_arq, buf = None, []

    for ln in lines:
        s = ln.strip()
        up = s.upper()
        if up.startswith("POPULAR"):
            flush(); section = "popular"; continue
        if up.startswith("DIGITAL"):
            flush(); section = "digital"; continue
        if up.startswith("ANALITICO") or up.startswith("ANALÍTICO"):
            flush(); section = "analitico"; continue
        if up.startswith("HASHTAGS"):
            flush(); section = "hashtags"; continue
        if s and set(s) <= set("═─ "):  # separador decorativo
            flush(); continue
        if section in ("popular", "digital", "analitico"):
            m = re.match(r"^([a-zñ]+):\s*$", s)
            if m and m.group(1) in ARQ:
                flush(); cur_arq = m.group(1); continue
            if cur_arq and s:
                buf.append(s)
        elif section == "hashtags":
            m = re.match(r"^([a-z]{2})\s+.*?→\s*(.+)$", s)
            if m:
                tags = re.findall(r"#\S+", m.group(2))
                if tags:
                    hashtags[m.group(1)] = tags
    flush()

    # Validación dura: si el .txt quedó incompleto, fallar antes de subir basura.
    assert set(reco) == {"popular", "digital", "analitico"}, f"registros: {set(reco)}"
    for r in reco:
        falt = ARQ - set(reco[r])
        assert not falt, f"{r} sin arquetipos: {falt}"
    falt = CANDS - set(hashtags)
    assert not falt, f"hashtags faltantes: {falt}"

    out = {"v": VERSION, "reco": reco, "hashtags": hashtags}
    json.dump(out, open(out_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return out


if __name__ == "__main__":
    o = build()
    print(f"OK → {OUT}")
    print(f"  registros: {list(o['reco'])} · 5 arquetipos c/u")
    for k in ["ic", "ae", "pv", "sf", "cl", "rb"]:
        print(f"  {k}: {o['hashtags'][k]}")
    print("Sube con:")
    print('  aws s3 cp "%s" \\' % OUT)
    print('    s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/'
          'test-presidencial/apoyo-recomendaciones.json \\')
    print('    --content-type application/json --cache-control "public, max-age=3600"')
