#!/usr/bin/env python3
"""Envuelve cada datos/*.json en datos/*.js (window.NLD[nombre] = ...) para que la presentación
abra con doble clic (file://), sin servidor y sin internet. Correr tras cada build."""
import glob, json, os
D = os.path.join(os.path.dirname(__file__), '..', '..', 'Propuestas', 'nuevo-liberalismo', 'datos')
for f in sorted(glob.glob(os.path.join(D, '*.json')) + glob.glob(os.path.join(D, '*.geojson'))):
    n = os.path.splitext(os.path.basename(f))[0]
    with open(f, encoding='utf-8') as fh: txt = fh.read().strip()
    json.loads(txt)  # valida
    open(os.path.join(D, n + '.js'), 'w', encoding='utf-8').write(f"window.NLD=window.NLD||{{}};window.NLD['{n}']={txt};\n")
    print(n, round(len(txt) / 1024), 'KB')
