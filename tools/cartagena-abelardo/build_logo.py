#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Renderiza el logo Ricardo.Ruiz a PNG transparente (Syne 800 + 4 barras azules).
Réplica del lockup del sitio: barras 18/14/9/5, 'Ricardo.Ruiz' con el punto azul."""
from PIL import Image, ImageDraw, ImageFont

FONT = "tools/build-cotizacion-campana/fonts/Syne-ExtraBold.ttf"
OUTDIR = "Bases de datos/output_abelardo_cartagena"
BLUE = (0, 71, 255, 255)     # var(--blue) #0047FF
INK = (26, 26, 46, 255)      # texto oscuro

S = 9                         # factor de escala (crispness)
FS = 22 * S                   # tamaño de fuente Syne
font = ImageFont.truetype(FONT, FS)

# barras: heights, width 5, gap 3 (lógico)
heights = [18, 14, 9, 5]
bw, bg = 5 * S, 3 * S
bars_w = len(heights) * bw + (len(heights) - 1) * bg
maxbar = max(heights) * S
gap_text = 9 * S
pad = 6 * S

# medir texto con leve tracking negativo (-0.03em ~ -3%)
def seg_w(txt):
    return font.getlength(txt) * 0.985

tw = seg_w("Ricardo") + seg_w(".") + seg_w("Ruiz")
W = int(pad * 2 + bars_w + gap_text + tw + 6 * S)
H = int(pad * 2 + maxbar + FS * 0.32)   # margen para descendentes
img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
dr = ImageDraw.Draw(img)

baseline = pad + maxbar  # los pies de las barras y la baseline del texto coinciden
# barras (alpha 0.88, esquina superior levemente redonda)
for i, hh in enumerate(heights):
    x0 = pad + i * (bw + bg)
    y0 = baseline - hh * S
    dr.rounded_rectangle([x0, y0, x0 + bw, baseline], radius=1.2 * S,
                         fill=(BLUE[0], BLUE[1], BLUE[2], 225))

# texto: Ricardo (ink) . (azul) Ruiz (ink) — anchor left-baseline
x = pad + bars_w + gap_text
for txt, col in [("Ricardo", INK), (".", BLUE), ("Ruiz", INK)]:
    dr.text((x, baseline), txt, font=font, fill=col, anchor="ls")
    x += seg_w(txt)

# recorte a contenido + pequeño margen
bbox = img.getbbox()
m = 2 * S
img = img.crop((max(0, bbox[0] - m), max(0, bbox[1] - m),
                min(W, bbox[2] + m), min(H, bbox[3] + m)))
img.save(f"{OUTDIR}/logo_ricardoruiz.png")
print(f"logo -> {OUTDIR}/logo_ricardoruiz.png  ({img.size[0]}x{img.size[1]})")
