#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inyecta el GeoJSON compacto + el JSON de datos en los marcadores de los HTML de Tunja.
Uso: python3 tools/tunja-atipica/inject.py  (procesa ambas páginas)."""
import os
ROOT = "/Users/ricardoruiz/ricardoruiz.co"
OUT = os.path.join(ROOT, "Bases de datos/output_tunja")
PAGES = ["tunja-atipica.html", "tunja-tactico.html"]

geo = open(os.path.join(OUT, "tunja-barrios-min.json")).read()
data = open(os.path.join(OUT, "tunja-electoral.json")).read()

for pg in PAGES:
    path = os.path.join(ROOT, pg)
    if not os.path.exists(path):
        print(f"[skip] {pg} no existe (se creará)"); continue
    h = open(path).read()
    # los marcadores se conservan como comentarios dentro del <script type=json>
    import re
    h = re.sub(r'(<script id="geo-data" type="application/json">).*?(</script>)',
               lambda m: m.group(1) + geo + m.group(2), h, flags=re.S)
    h = re.sub(r'(<script id="elec-data" type="application/json">).*?(</script>)',
               lambda m: m.group(1) + data + m.group(2), h, flags=re.S)
    open(path, "w").write(h)
    print(f"[ok] {pg}  ({os.path.getsize(path)//1024} KB)")
