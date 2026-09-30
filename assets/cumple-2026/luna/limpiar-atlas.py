#!/usr/bin/env python3
"""Limpia los atlas v1 de Astra y produce los v2 que sirve cumple.html.

Por cada celda del atlas conserva solo los componentes conexos que pesan ≥2 % de
la celda (la perrita, la urna, el sobre) y borra los fragmentos de las celdas
vecinas que el generador dejó adentro (42 en total). Recalcula además el piso de
cada pose (borde inferior con alfa > 200) y lo escribe en pisos-v2.json, de donde
salen los arrays BB de luna-cumple.js.

    python3 limpiar-atlas.py        # PNG v1 → PNG v2 + WebP v2 + pisos-v2.json
"""
import json, subprocess, numpy as np
from PIL import Image
from scipy import ndimage as ndi

ATLAS = {'llegada': (5, 4), 'fiesta': (4, 4), 'celebra': (6, 4)}
out = {}
for f, (c, r) in ATLAS.items():
    a = np.array(Image.open(f'luna-cumple-{f}-v1.png').convert('RGBA')); A = a[..., 3]
    H, W = A.shape; ch, cw = H / r, W / c; pisos = []; quitados = 0
    for i in range(r):
        for j in range(c):
            y0, y1, x0, x1 = int(i * ch), int((i + 1) * ch), int(j * cw), int((j + 1) * cw)
            cell = A[y0:y1, x0:x1]; mask = cell > 40
            lab, n = ndi.label(mask); sizes = ndi.sum(mask, lab, range(1, n + 1))
            keep = np.zeros_like(mask)
            for k, sz in enumerate(sizes, 1):
                if sz >= 0.02 * mask.size: keep |= (lab == k)
                else: quitados += 1
            keep = ndi.binary_dilation(keep, iterations=2)  # conserva el antialias del borde
            cell[~keep] = 0
            ys, _ = np.where(cell > 200)
            pisos.append(round(float(ys.max()) / (y1 - y0), 3) if len(ys) else 0.97)
    Image.fromarray(a).save(f'luna-cumple-{f}-v2.png')
    subprocess.run(['cwebp', '-quiet', '-q', '90', '-alpha_q', '100', '-m', '6', f'luna-cumple-{f}-v2.png', '-o', f'luna-cumple-{f}-v2.webp'], check=True)
    out[f] = pisos; print(f, 'fragmentos quitados:', quitados)
json.dump(out, open('pisos-v2.json', 'w'))
