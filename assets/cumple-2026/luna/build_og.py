#!/usr/bin/env python3
"""Imagen para compartir (og:image, 1200×630) de la invitación de cumpleaños.
Toma una pose de Luna del atlas de fiesta limpio (v2) y la pone sobre el navy de
la página con el título. Sale a assets/cumple-2026/og.jpg (< 300 KB para WhatsApp)."""
import random, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
random.seed(3)
W, H = 1200, 630
NAVY = (10, 23, 51); ORO = (255, 193, 69); ROSA = (255, 93, 143); MENTA = (95, 224, 183); LILA = (185, 166, 255)
im = Image.new('RGB', (W, H), NAVY)
# resplandor azul arriba a la derecha, como el CSS
glow = Image.new('RGB', (W, H), NAVY); g = ImageDraw.Draw(glow)
g.ellipse((600, -400, 1500, 350), fill=(29, 63, 134)); glow = glow.filter(ImageFilter.GaussianBlur(160))
im = Image.blend(im, glow, 0.85)
d = ImageDraw.Draw(im)
# confeti
for _ in range(70):
    x, y = random.randint(0, W), random.randint(0, H); w, h = random.randint(8, 16), random.randint(4, 8)
    c = random.choice([ORO, ROSA, MENTA, LILA, (255, 255, 255)])
    piece = Image.new('RGBA', (w * 2, h * 2), (0, 0, 0, 0)); ImageDraw.Draw(piece).rectangle((w // 2, h // 2, w // 2 + w, h // 2 + h), fill=c + (230,))
    rot = piece.rotate(random.randint(0, 180), expand=True); im.paste(rot, (x, y), rot)
d = ImageDraw.Draw(im)
F = '/System/Library/Fonts/HelveticaNeue.ttc'
mono = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', 20)
bold = ImageFont.truetype(F, 78, index=1); med = ImageFont.truetype(F, 30, index=10); reg = ImageFont.truetype(F, 26, index=0)
d.text((72, 64), 'CUMPLEAÑOS DE RICARDO · 2026', font=mono, fill=(169, 189, 230), spacing=4)
y = 130
for linea, col in [('Te convoco a la', (243, 247, 255)), ('jornada de', ORO), ('cumpleaños.', ORO)]:
    d.text((68, y), linea, font=bold, fill=col); y += 84
d.text((72, y + 26), 'Cena en casa · sábado 3 de octubre · 7:30 p.m.', font=med, fill=(243, 247, 255))
d.text((72, y + 72), 'Inscríbete y te llega la invitación al correo.', font=reg, fill=(211, 222, 245))
# Luna: pose 1 del atlas de fiesta (sentada, gorro), recortada de la celda
a = np.array(Image.open('assets/cumple-2026/luna/luna-cumple-fiesta-v2.png').convert('RGBA'))
ch, cw = a.shape[0] // 4, a.shape[1] // 4
cell = Image.fromarray(a[0:ch, 0:cw]); bb = cell.getbbox(); cell = cell.crop(bb)
alto = 520; luna = cell.resize((int(cell.width * alto / cell.height), alto), Image.LANCZOS)
im.paste(luna, (W - luna.width - 40, H - luna.height - 18), luna)
im.save('assets/cumple-2026/og.jpg', quality=84, optimize=True, progressive=True)
import os; print('og.jpg', os.path.getsize('assets/cumple-2026/og.jpg') // 1024, 'KB')
