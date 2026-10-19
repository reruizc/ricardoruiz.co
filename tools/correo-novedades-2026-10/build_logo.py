"""Logo de Ricardo.Ruiz en PNG para correos (los clientes de correo no cargan
Syne). Mismas proporciones que .logo-bars/.logo-text del sitio: 4 barras azules
de 20/15/9/4 px junto al texto, el punto en azul. Se dibuja a 4x y se muestra
a 1x en el correo para que se vea nítido en pantallas retina.

    python3 tools/correo-novedades-2026-10/build_logo.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[2]
FUENTE = RAIZ / 'tools/build-cotizacion-campana/fonts/Syne-ExtraBold.ttf'
S = 4                       # escala de dibujo
TXT = 28 * S                # tamaño del texto (1.8rem del sitio ≈ 28px)
AZUL, TINTA = (0, 71, 255), (11, 13, 17)


def logo(tinta, salida):
    f = ImageFont.truetype(str(FUENTE), TXT)
    track = -0.03 * TXT                        # letter-spacing:-.03em
    partes = [('Ricardo', tinta), ('.', AZUL), ('Ruiz', tinta)]
    ancho_txt = 0
    for t, _ in partes:
        for ch in t:
            ancho_txt += f.getlength(ch) + track
    barras = [20, 15, 9, 4]
    bw, gap, sep = 5 * S, 3 * S, int(0.55 * 16 * S)
    ancho_barras = len(barras) * bw + (len(barras) - 1) * gap
    asc, desc = f.getmetrics()
    alto = asc + desc
    W = int(ancho_barras + sep + ancho_txt + 2 * S)
    img = Image.new('RGBA', (W, alto), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    base = asc                                  # línea base del texto
    x = 0
    for h in barras:                            # barras apoyadas en la línea base
        d.rectangle([x, base - h * S * 1.15, x + bw - 1, base], fill=AZUL + (217,))
        x += bw + gap
    x = ancho_barras + sep
    for t, color in partes:
        for ch in t:
            d.text((x, 0), ch, font=f, fill=color)
            x += f.getlength(ch) + track
    img = img.crop(img.getbbox())
    img.save(salida, optimize=True)
    print(salida, img.size, '→ mostrar a', round(img.size[0] / S), 'x', round(img.size[1] / S))


logo(TINTA, RAIZ / 'imagenes/marca/logo-ricardoruiz.png')       # para fondo claro
logo((244, 243, 239), RAIZ / 'imagenes/marca/logo-ricardoruiz-claro.png')  # para fondo oscuro
