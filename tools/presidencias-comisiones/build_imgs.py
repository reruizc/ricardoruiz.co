#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dos imágenes para X: quién presidirá cada comisión constitucional en la
legislatura 2026-2027 (Senado y Cámara).

Identidad: sistema visual v2 (fondo #060810 + Helvetica Neue, sin modo claro).
Colores de partido = los mismos de BANCADAS en comision.html, para que la
imagen y el sitio hablen el mismo idioma visual.

Salidas → rrss/twitter/presidencias-png/presidencias-{senado,camara}.png

Datos verificados el 29-jul-2026 contra El Tiempo, El Espectador, Noticias RCN, La FM,
Portafolio, Infobae y La Silla Vacía; los 26 nombres se cotejaron uno por uno
contra comisiones-2026.json (todos son integrantes reales de la comisión que
presiden). 12 de 14 presidencias votadas; 2 pendientes.

Gotcha: Helvetica no trae emoji ni flechas (→ ★ ⏳) — se ven como cajas.
Usar solo texto y viñetas dibujadas.
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib import font_manager

ROOT = '/Users/ricardoruiz/ricardoruiz.co'
OUT = f'{ROOT}/rrss/twitter/presidencias-png'

# ---------- identidad v2 ----------
BG, CARD, INK = '#060810', '#0d0f18', '#f4f3ef'
MUTED, GRID = '#8b8f9c', '#1d2030'
BLUE, ORANGE, AMBER = '#3d6fff', '#f97316', '#e8b93b'

# colores de bancada (BANCADAS de comision.html)
PCOL = {
    'Salvación Nacional': '#00AEEF',
    'Centro Democrático': '#0088BB',
    'Liberal': '#C8102E',
    'Conservador': '#003580',
    'Partido de la U': '#F7941D',
    'Cambio Radical': '#E91E8C',
    'MIRA': '#1A3FC4',
    'Nuevo Liberalismo': '#4CAF50',
}

FAM = 'Helvetica Neue RR'   # familia propia para no chocar con la .ttc del sistema


def _helvetica():
    """Registra la Helvetica Neue DEL REPO (la misma que sirve el sitio).

    No se usa la del sistema: /System/Library/Fonts/HelveticaNeue.ttc es una
    colección .ttc y freetype revienta al fijar el tamaño con dpi>1
    ('invalid ppem value', error 0x97). Los woff2 de fonts/ se convierten una
    vez a .ttf con fontTools (necesita brotli) y quedan cacheados aquí.
    """
    from fontTools.ttLib import TTFont
    cache = f'{os.path.dirname(os.path.abspath(__file__))}/fonts'
    os.makedirs(cache, exist_ok=True)
    ok = False
    for src, dst in (('helveticaneue.woff2', 'HelveticaNeueRR.ttf'),
                     ('helveticaneue-bold.woff2', 'HelveticaNeueRR-Bold.ttf'),
                     ('helveticaneue-medium.woff2', 'HelveticaNeueRR-Medium.ttf'),
                     ('helveticaneue-italic.woff2', 'HelveticaNeueRR-Italic.ttf')):
        out = f'{cache}/{dst}'
        if not os.path.exists(out):
            try:
                f = TTFont(f'{ROOT}/fonts/{src}')
                f.flavor = None      # sin esto vuelve a guardar woff2
                # se renombra la familia: con el nombre original, findfont sigue
                # prefiriendo la .ttc del sistema y vuelve el error de ppem
                for rec in f['name'].names:
                    if rec.nameID in (1, 16):
                        rec.string = FAM
                    elif rec.nameID == 4:
                        rec.string = FAM + ' ' + str(rec).split()[-1]
                f.save(out)
            except Exception as e:
                print(f'  (aviso) no se pudo convertir {src}: {e}')
                continue
        font_manager.fontManager.addfont(out)
        ok = True
    return FAM if ok else 'Arial'


FONT = _helvetica()
plt.rcParams.update({'font.family': FONT, 'text.color': INK,
                     'figure.facecolor': BG, 'savefig.facecolor': BG})

# (comisión, tema, presidente, partido, vice, vice_partido, votado)
SENADO = [
    ('Primera', 'Reformas constitucionales, paz',
     'Enrique Gómez Martínez', 'Salvación Nacional',
     'José Nicolás Gómez', 'Cambio Radical', True),
    ('Segunda', 'Defensa, relaciones exteriores',
     'Lidio García o Luis A. Mejía', None, None, None, False),
    ('Tercera', 'Hacienda, impuestos, banca',
     'Sara Jimena Castellanos', 'Salvación Nacional',
     'Juan Fernando Caicedo', 'Centro Democrático', True),
    ('Cuarta', 'Presupuesto y control fiscal',
     'Diela Liliana Benavides', 'Conservador',
     'Álvaro Monedero', 'Liberal', True),
    ('Quinta', 'Agro, ambiente, minas y energía',
     'Juan Fernando Espinal', 'Centro Democrático',
     'Gonzalo Baute', 'Cambio Radical', True),
    ('Sexta', 'Educación, transporte, comunicaciones',
     'Carlos Eduardo Guevara', 'MIRA',
     'María Lucía Villalba', 'Nuevo Liberalismo', True),
    ('Séptima', 'Salud, trabajo, seguridad social',
     'Andrés Eduardo Forero', 'Centro Democrático',
     'Ana Paola Agudelo', 'MIRA', True),
]
CAMARA = [
    ('Primera', 'Reformas constitucionales, paz',
     'José Jaime Uscátegui', 'Centro Democrático',
     'Mónica Karina Bocanegra', 'Liberal', True),
    ('Segunda', 'Defensa, relaciones exteriores',
     'Elizabeth Jay-Pang Díaz', 'Liberal',
     'Diana Maritza Álvarez', 'MIRA', True),
    ('Tercera', 'Hacienda, impuestos, banca',
     'Alfredo «Ape» Cuello', 'Conservador',
     'Diego Fran Ariza', 'Partido de la U', True),
    ('Cuarta', 'Presupuesto y control fiscal',
     'Alexánder Bermúdez Lasso', 'Liberal',
     'José Alejandro Martínez', 'Conservador', True),
    ('Quinta', 'Agro, ambiente, minas y energía',
     'Julio Roberto Salazar', 'Conservador',
     'Mateo Hidalgo Montoya', 'Centro Democrático', True),
    ('Sexta', 'Educación, transporte, comunicaciones',
     'Sin acuerdo · suena Nataly Vélez', None, None, None, False),
    ('Séptima', 'Salud, trabajo, seguridad social',
     'Juan Felipe Corzo', 'Centro Democrático',
     'Jorge Méndez', 'Cambio Radical', True),
]

# el lienzo se mide en pulgadas: 12x8 in a 200 dpi = 2400x1600 px.
# OJO: no pasar dpi=2 — ppem = pt*dpi/72 se redondea a 0 y freetype lanza
# 'invalid ppem value' (error 0x97).
# 16:9 a propósito: X recorta a ese aspecto en el timeline, así que una
# imagen más alta perdería la última fila y el pie en la vista previa.
W, H, DPI = 1200, 675, 200


def chip(ax, x, y, txt, color, fs=8.4):
    """pastilla de partido: cuadrito de color + sigla del partido"""
    ax.add_patch(Rectangle((x, y - .0055), .009, .016, color=color,
                           transform=ax.transAxes, clip_on=False))
    ax.text(x + .015, y, txt, fontsize=fs, color=MUTED, va='center',
            transform=ax.transAxes)


def tabla(rows, corp, fname):
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis('off')

    ax.text(.045, .955, 'CONGRESO 2026-2030 · LEGISLATURA 2026-2027',
            fontsize=10.5, color=ORANGE, fontweight='bold', va='top',
            transform=ax.transAxes)
    ax.text(.045, .885, f'Quién presidirá cada comisión: {corp}',
            fontsize=23, color=INK, fontweight='bold', va='top',
            transform=ax.transAxes)

    # encabezados
    y0, dy = .700, .0940
    for x, t in ((.045, 'COMISIÓN'), (.235, 'PRESIDENCIA'),
                 (.615, 'VICEPRESIDENCIA')):
        # matplotlib no tiene letterspacing: se simula separando los caracteres
        ax.text(x, y0 + .075, ' '.join(t), fontsize=8.2, color=MUTED,
                fontweight='bold', va='center', transform=ax.transAxes)
    ax.plot([.045, .955], [y0 + .055, y0 + .055], color=GRID, lw=1.1,
            transform=ax.transAxes, clip_on=False)

    for i, (com, tema, pres, part, vice, vpart, votado) in enumerate(rows):
        y = y0 - i * dy
        if i % 2 == 0:
            ax.add_patch(Rectangle((.032, y - .044), .936, .092, color=CARD,
                                   transform=ax.transAxes, clip_on=False, zorder=0))
        # comisión + tema
        ax.text(.045, y + .014, com, fontsize=13.5, color=INK, fontweight='bold',
                va='center', transform=ax.transAxes)
        ax.text(.045, y - .022, tema, fontsize=7.2, color=MUTED, va='center',
                transform=ax.transAxes)
        # presidencia
        if votado:
            ax.text(.235, y + .014, pres, fontsize=13.5, color=INK,
                    fontweight='bold', va='center', transform=ax.transAxes)
            chip(ax, .235, y - .022, part.upper(), PCOL[part])
        else:
            txt = pres if part is None else f'{pres} (previsto)'
            ax.text(.235, y + .014, txt, fontsize=13.5, color=AMBER,
                    style='italic', va='center', transform=ax.transAxes)
            ax.text(.235, y - .022, 'SIN VOTAR', fontsize=8, color=AMBER,
                    fontweight='bold', va='center', transform=ax.transAxes)
        # vicepresidencia
        if vice:
            ax.text(.615, y + .014, vice, fontsize=11.8, color=INK, va='center',
                    transform=ax.transAxes)
            chip(ax, .615, y - .022, vpart.upper(), PCOL[vpart], fs=7.4)
        else:
            ax.text(.615, y + .014, '—', fontsize=11.8, color=MUTED, va='center',
                    transform=ax.transAxes)

    n_ok = sum(1 for r in rows if r[6])
    ax.text(.045, .036, f'{n_ok} de 7 presidencias votadas el 29 de julio de 2026. '
            'Fuente: El Tiempo, El Espectador, RCN, Portafolio, La Silla Vacía, La FM.',
            fontsize=8.2, color=MUTED, va='bottom', transform=ax.transAxes)
    ax.text(.955, .036, 'ricardoruiz.co/legislativo', fontsize=9.6, color=INK,
            fontweight='bold', va='bottom', ha='right', transform=ax.transAxes)

    os.makedirs(OUT, exist_ok=True)
    p = f'{OUT}/{fname}.png'
    fig.savefig(p, dpi=DPI, facecolor=BG)
    plt.close(fig)
    print(f'  {p}  ({int(W/100*DPI)}x{int(H/100*DPI)} px)')


if __name__ == '__main__':
    print('presidencias de comisiones · 2 imágenes para X')
    tabla(SENADO, 'Senado', 'presidencias-senado')
    tabla(CAMARA, 'Cámara', 'presidencias-camara')
