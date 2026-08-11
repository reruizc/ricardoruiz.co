#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Imagen IG 1080x1080 · "mercado de predicción" del Contralor General 2026-2030.
Elección: Congreso en pleno, 12 de agosto de 2026, voto secreto.

El número de la barra es un ÍNDICE PROPIO declarado, NO una probabilidad de
mercado ni una encuesta. Pesos (visibles en la pieza):
    60%  respaldo político declarado en prensa
    25%  convergencia del reporteo (en cuántos artículos-sonajero aparece)
    15%  puntaje del concurso de méritos (normalizado sobre los 10 elegibles)

Fuentes de cada dato en LEEME.md. Sistema visual v2 (oscuro + Helvetica Neue).
"""
import os
from PIL import Image, ImageDraw, ImageFont

W = H = 1080
BG        = (6, 8, 16)
INK       = (244, 243, 239)
MUTE      = (150, 158, 178)
DIM       = (98, 106, 126)
BLUE      = (0, 71, 255)
BLUE_SOFT = (61, 111, 255)
GREEN     = (74, 222, 128)
RED       = (239, 91, 91)
AMBER     = (249, 158, 52)
CARD      = (14, 17, 30)
LINE      = (38, 44, 64)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FDIR = os.path.join(ROOT, 'reforma-tributaria-2026', 'fonts')
def F(name, size):
    return ImageFont.truetype(os.path.join(FDIR, name), size)
BOLD, MED, REG = 'helveticaneue-bold.ttf', 'helveticaneue-medium.ttf', 'helveticaneue.ttf'

# --- datos: MISMA fuente de verdad que quien-queda.html --------------------
# Se leen del estado que produce tools/pronosticos/motor.py, para que la imagen
# y la página nunca digan números distintos. Con --local usa el archivo del
# repo; por defecto lee el que está publicado en S3.
ESTADO_S3 = ('https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/'
             'congreso-2026/output/pronosticos/contralor-2026.json')
ESTADO_LOCAL = os.path.join(os.path.dirname(ROOT), 'Bases de datos',
                            'pronosticos', 'contralor-2026.json')
# Respaldos en una línea para la pieza (el motor guarda el score, no la frase).
RESP_TXT = {
    'laverde':  "Liberales (Lidio García, Simón Gaviria) · toma ventaja esta semana",
    'castro':   "Procurador Eljach + sectores del Pacto · el otro contendor real",
    'zuluaga':  "Se le desgranaron los votos que lo sostenían",
    'monsalvo': "El gobierno se apartó: no cogió vuelo entre las bancadas",
    'abadia':   "Ganó el concurso y sigue sin padrino político",
    'torres':   "Perfil técnico, sin padrino visible",
}


def cargar_estado(local=False):
    import json as _json
    if local:
        with open(ESTADO_LOCAL, encoding='utf-8') as fh:
            return _json.load(fh)
    import urllib.request
    req = urllib.request.Request(ESTADO_S3, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return _json.loads(r.read())


def preparar(est, n=4):
    """Top n para las barras + Abadía como contraste."""
    tabla = est['tabla']
    top = [f for f in tabla if f['id'] != 'abadia'][:n]
    cand = []
    for f in top:
        d = f.get('delta')
        cand.append(dict(
            ape=f['corto'].upper(), nom=f['nombre'], cargo=f['cargo'],
            idx=f['prob'], pts=f['pts'],
            resp=RESP_TXT.get(f['id'], ''),
            tend=0 if not d else (1 if d > 0 else -1)))
    ab = next((f for f in tabla if f['id'] == 'abadia'), None)
    abadia = dict(nom=ab['nombre'], pts=ab['pts'], idx=ab['prob']) if ab else None
    return cand, abadia, est


def rr(d, box, r, fill=None, outline=None, w=1):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=w)


def tri(d, cx, cy, s, up, color):
    """Triángulo de tendencia (Helvetica no trae flechas fiables)."""
    if up:
        d.polygon([(cx, cy - s), (cx - s, cy + s * .7), (cx + s, cy + s * .7)], fill=color)
    else:
        d.polygon([(cx, cy + s), (cx - s, cy - s * .7), (cx + s, cy - s * .7)], fill=color)


def build(out, CAND, ABADIA, est):
    lider = max([c['idx'] for c in CAND] + [1])
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)

    # halo azul superior
    glow = Image.new('RGB', (W, H), BG)
    gd = ImageDraw.Draw(glow)
    for i in range(70, 0, -1):
        a = i / 70
        col = (int(6 + 20 * a * a), int(8 + 26 * a * a), int(16 + 74 * a * a))
        gd.ellipse([W * .5 - 620 * a, -420 - 180 * a, W * .5 + 620 * a, 300 + 120 * a], fill=col)
    img = Image.blend(img, glow, .55)
    d = ImageDraw.Draw(img)

    M = 64
    y = 52

    # kicker
    d.text((M, y), "CONGRESO EN PLENO", font=F(BOLD, 20), fill=BLUE_SOFT)
    kw = d.textlength("CONGRESO EN PLENO", font=F(BOLD, 20))
    d.text((M + kw + 13, y), "·  12 DE AGOSTO DE 2026  ·  VOTO SECRETO", font=F(MED, 20), fill=DIM)
    y += 40

    # título
    d.text((M, y), "¿Quién será el próximo", font=F(BOLD, 55), fill=INK); y += 58
    d.text((M, y), "Contralor General?", font=F(BOLD, 55), fill=INK); y += 72

    sub1 = "El Centro Democrático (47 votos) define mañana. "
    d.text((M, y), sub1, font=F(BOLD, 23), fill=INK)
    d.text((M + d.textlength(sub1, font=F(BOLD, 23)), y), "Detrás se alinean las demás.",
           font=F(MED, 23), fill=MUTE)
    y += 46

    # --- filas ---
    BARX, BARW, BARH = M, 660, 14
    for c in CAND:
        top = y
        rr(d, [M - 20, top - 14, W - M + 20, top + 126], 20, fill=CARD)

        d.text((BARX, top), c["ape"], font=F(BOLD, 34), fill=INK)

        # número grande
        num = f'{c["idx"]}%'
        nf = F(BOLD, 54)
        nw = d.textlength(num, font=nf)
        d.text((W - M - nw - 32, top - 8), num, font=nf, fill=INK)
        if c["tend"] != 0:
            col = GREEN if c["tend"] > 0 else RED
            tri(d, W - M - 13, top + 22, 10, c["tend"] > 0, col)

        d.text((BARX, top + 42), c["cargo"], font=F(REG, 20), fill=MUTE)

        # barra
        by = top + 72
        rr(d, [BARX, by, BARX + BARW, by + BARH], BARH // 2, fill=(24, 28, 44))
        wpx = int(BARW * c["idx"] / lider)
        grad = Image.new('RGB', (max(wpx, 1), BARH))
        gdd = ImageDraw.Draw(grad)
        for x in range(max(wpx, 1)):
            t = x / max(wpx - 1, 1)
            gdd.line([(x, 0), (x, BARH)], fill=(int(BLUE[0] + (BLUE_SOFT[0] - BLUE[0]) * t),
                                                int(BLUE[1] + (BLUE_SOFT[1] - BLUE[1]) * t),
                                                int(BLUE[2] + (BLUE_SOFT[2] - BLUE[2]) * t)))
        mask = Image.new('L', (max(wpx, 1), BARH), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, max(wpx, 1) - 1, BARH - 1], radius=BARH // 2, fill=255)
        img.paste(grad, (BARX, by), mask)
        d = ImageDraw.Draw(img)

        d.text((BARX + BARW + 18, by - 4), f"concurso {c['pts']:.2f}".replace('.', ','),
               font=F(MED, 18), fill=DIM)

        # respaldo, dentro de la misma tarjeta
        # (Helvetica no trae flechas/triángulos: se dibuja el bullet a mano)
        cy = by + 36
        d.polygon([(BARX + 1, cy - 6), (BARX + 1, cy + 6), (BARX + 10, cy)], fill=BLUE_SOFT)
        d.text((BARX + 22, by + 26), c["resp"], font=F(REG, 19), fill=(178, 186, 206))

        y += 152

    # --- contraste Abadía ---
    y += 4
    rr(d, [M - 20, y, W - M + 20, y + 86], 18, fill=(26, 18, 10), outline=(74, 52, 22), w=2)
    d.text((M, y + 15), "EL QUE GANÓ EL CONCURSO NO TIENE VOTOS", font=F(BOLD, 19), fill=AMBER)
    p1 = f"{ABADIA['nom']} sacó 86,74, el mejor de los diez. "
    d.text((M, y + 45), p1, font=F(MED, 20), fill=INK)
    d.text((M + d.textlength(p1, font=F(MED, 20)), y + 45),
           f"Sigue sin padrino: {ABADIA['idx']}%.", font=F(REG, 20), fill=MUTE)
    y += 104

    # --- footer ---
    ts = str(est.get('actualizado', ''))[:16].replace('T', ' ')
    d.line([(M, y), (W - M, y)], fill=LINE, width=1); y += 15
    d.text((M, y), "Índice propio, no es encuesta ni mercado de apuestas. Pesos: respaldo político declarado",
           font=F(REG, 16), fill=DIM)
    d.text((M, y + 20), f"en prensa 60% · presencia en el reporteo 25% · concurso 15%. "
                        f"Se actualiza cada 6 h · {ts}",
           font=F(REG, 16), fill=DIM)

    # logo
    lx, ly = W - M - 196, y + 4
    for i, hgt in enumerate([26, 18, 30, 22]):
        d.rectangle([lx + i * 11, ly + (30 - hgt), lx + i * 11 + 6, ly + 30], fill=BLUE_SOFT)
    d.text((lx + 58, ly + 4), "ricardoruiz.co", font=F(BOLD, 22), fill=INK)

    img.save(out, quality=95)
    print("→", out)


if __name__ == '__main__':
    import sys
    est = cargar_estado(local='--local' in sys.argv)
    cand, abadia, est = preparar(est)
    out = os.path.join(ROOT, '..', 'rrss', 'instagram', 'contralor-png', 'contralor-mercado.png')
    build(os.path.normpath(out), cand, abadia, est)
    print('  ' + ' · '.join(f"{c['ape'].title()} {c['idx']}%" for c in cand)
          + f" · Abadía {abadia['idx']}%")
