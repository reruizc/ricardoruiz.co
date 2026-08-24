#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Infografía cuadrada (1080x1080) para el post de LinkedIn sobre la reforma
tributaria radicada el 20-jul-2026. Identidad: sistema visual v2.

Tipografía: los woff2 de `fonts/` del repo convertidos a TTF con fontTools
(matplotlib no lee woff2, y el Helvetica Neue del sistema solo registra el
peso 400 → `fontweight='bold'` salía sintético/aguado). Los TTF viven en
tools/reforma-tributaria-2026/fonts/ y se regeneran con --fonts.

Logo: lockup del sitio dibujado a mano — 4 barras descendentes (18/14/9/5)
en azul + "Ricardo.Ruiz" en Syne ExtraBold con el punto azul.

Salida → rrss/linkedin/reforma-tributaria-0-infografia.png
Correr:  python3 tools/reforma-tributaria-2026/build_infografia.py
"""
import os, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyBboxPatch as FBP

ROOT = '/Users/ricardoruiz/ricardoruiz.co'
HERE = f'{ROOT}/tools/reforma-tributaria-2026'
FDIR = f'{HERE}/fonts'
OUT  = f'{ROOT}/rrss/linkedin/reforma-tributaria-0-infografia.png'

BG, CARD   = '#060810', '#11141f'
INK, MUTED = '#f4f3ef', '#8b8f9c'
BLUE, ORANGE = '#3d6fff', '#f97316'
BLUE_LOGO  = '#0047FF'
GRID = '#232739'


def build_fonts():
    """woff2 del repo → ttf (una vez). matplotlib no lee woff2."""
    from fontTools.ttLib import TTFont
    os.makedirs(FDIR, exist_ok=True)
    for w in ('helveticaneue.woff2', 'helveticaneue-bold.woff2',
              'helveticaneue-medium.woff2'):
        f = TTFont(f'{ROOT}/fonts/{w}')
        f.flavor = None
        f.save(f'{FDIR}/{w.replace(".woff2", ".ttf")}')


if '--fonts' in sys.argv or not os.path.exists(f'{FDIR}/helveticaneue-bold.ttf'):
    build_fonts()

for f in os.listdir(FDIR):
    if f.endswith('.ttf'):
        font_manager.fontManager.addfont(f'{FDIR}/{f}')
SYNE = f'{ROOT}/tools/build-cotizacion-campana/fonts/Syne-ExtraBold.ttf'
font_manager.fontManager.addfont(SYNE)
SYNE_NAME = font_manager.FontProperties(fname=SYNE).get_name()

REG  = {'family': 'Helvetica Neue', 'weight': 'normal'}
BOLD = {'family': 'Helvetica Neue', 'weight': 'bold'}
MED  = {'family': 'Helvetica Neue', 'weight': 500}

plt.rcParams.update({'font.family': 'Helvetica Neue', 'text.color': INK,
                     'figure.facecolor': BG, 'savefig.facecolor': BG})

fig = plt.figure(figsize=(10.8, 10.8), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 100)
ax.axis('off'); ax.set_facecolor(BG)


def card(x, y, w, h, fc=CARD, ec=GRID, lw=1.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle='round,pad=0,rounding_size=1.2',
                                fc=fc, ec=ec, lw=lw, zorder=1))


def _tw(txt, fs):
    """Ancho de un texto en unidades de eje (mide y descarta)."""
    t = ax.text(0, -50, txt, fontsize=fs, family=SYNE_NAME)
    fig.canvas.draw()
    w = t.get_window_extent(fig.canvas.get_renderer()) \
         .transformed(ax.transData.inverted()).width
    t.remove()
    return w


def logo(right, y, scale=1.0):
    """Lockup Ricardo.Ruiz (4 barras + wordmark Syne, punto azul),
    anclado por su borde DERECHO en `right`, baseline en `y`."""
    heights = [18, 14, 9, 5]
    bw, gap = 0.42 * scale, 0.24 * scale
    fs = 10.5 * scale
    bars_w = len(heights) * bw + (len(heights) - 1) * gap
    sep = 0.9 * scale
    w1, wd, w2 = _tw('Ricardo', fs), _tw('.', fs), _tw('Ruiz', fs)
    x = right - (bars_w + sep + w1 + wd + w2)

    for i, hh in enumerate(heights):
        ax.add_patch(FBP((x + i * (bw + gap), y), bw, hh * 0.115 * scale,
                         boxstyle='round,pad=0,rounding_size=0.08',
                         fc=BLUE_LOGO, ec='none', alpha=0.92, zorder=4))
    tx = x + bars_w + sep
    for seg, wseg, col in (('Ricardo', w1, INK), ('.', wd, BLUE_LOGO), ('Ruiz', w2, INK)):
        ax.text(tx, y, seg, fontsize=fs, family=SYNE_NAME, color=col,
                va='baseline', zorder=4)
        tx += wseg


M = 7.0   # margen lateral

# ---------------- cabecera ----------------
ax.text(M, 95.4, 'REFORMA TRIBUTARIA  ·  RADICADA EL 20 DE JULIO DE 2026',
        fontsize=12.5, color=ORANGE, va='top', **BOLD)

TL = 5.4   # interlínea del titular (antes 6.4)
ax.text(M, 91.4, 'Un gobierno que se va',        fontsize=33, color=INK, va='top', **BOLD)
ax.text(M, 91.4 - TL, 'en 18 días radicó una',   fontsize=33, color=INK, va='top', **BOLD)
ax.text(M, 91.4 - 2*TL, 'reforma de $21,9 billones',
        fontsize=33, color=BLUE, va='top', **BOLD)

ax.plot([M, 93], [74.6, 74.6], color=GRID, lw=1.2, zorder=2)

# ---------------- bloque 1: de dónde sale la plata ----------------
ax.text(M, 72.4, 'DE DÓNDE SALDRÍA LA PLATA  ·  RECAUDO 2027',
        fontsize=11, color=MUTED, va='top', **BOLD)

rows = [
    ('Empresas vuelven a pagar salud, SENA e ICBF\npor salarios de 3 a 10 mínimos', 8.5, ORANGE),
    ('IVA y beneficios tributarios\n(gasolina, apuestas, Temu, híbridos)',           6.7, BLUE),
    ('Renta, patrimonio y sobretasa a bancos',                                       3.4, BLUE),
    ('Impuestos verdes y saludables\n(carbono, licores, tabaco, petróleo)',          3.2, BLUE),
]
x0, xmax = 47.0, 84.0
top, rowh = 68.6, 6.4
for i, (lab, val, col) in enumerate(rows):
    y = top - i * rowh
    ax.text(M, y, lab, fontsize=10.4, color=INK, va='top', linespacing=1.3, **REG)
    w = (val / 8.5) * (xmax - x0)
    ax.add_patch(Rectangle((x0, y - 3.4), w, 2.5, fc=col, ec='none', zorder=3))
    ax.text(x0 + w + 1.2, y - 2.15, f'${val:,.1f} bn'.replace('.', ','),
            fontsize=11.5, color=col, va='center', **BOLD)

ax.text(M, 43.0, 'El 39% de toda la reforma está en esa primera línea: '
                 'no es la gasolina ni el patrimonio.',
        fontsize=10.6, color=ORANGE, va='top', **MED)

# ---------------- bloque 2: qué dice el histórico ----------------
ax.plot([M, 93], [39.6, 39.6], color=GRID, lw=1.2, zorder=2)
ax.text(M, 37.2, 'QUÉ DICE EL HISTÓRICO LEGISLATIVO  ·  1990-2026',
        fontsize=11, color=MUTED, va='top', **BOLD)

facts = [
    ('1 de 3', 'tributarias de este\ngobierno llegaron a ley'),
    ('0',      'votaciones en plenaria\ntuvieron las 2 que murieron'),
    ('35%',    'de los proyectos muere\npor reloj en el año 4'),
]
bw_, gap_ = 27.0, 2.5
for i, (big, small) in enumerate(facts):
    x = M + i * (bw_ + gap_)
    card(x, 18.6, bw_, 14.0)
    ax.text(x + bw_/2, 29.6, big, fontsize=27, color=BLUE, ha='center', va='top', **BOLD)
    ax.text(x + bw_/2, 24.2, small, fontsize=10.2, color=INK, ha='center',
            va='top', linespacing=1.35, **REG)

# ---------------- remate ----------------
card(M, 9.6, 86, 7.0, fc='#12182e', ec=BLUE, lw=1.4)
ax.text(M + 2.6, 14.9, 'En 36 años de registro no hay una sola reforma tributaria',
        fontsize=12.2, color=INK, va='top', **BOLD)
ax.text(M + 2.6, 12.2, 'radicada por un gobierno saliente. Esto nunca había pasado.',
        fontsize=12.2, color=INK, va='top', **BOLD)

ax.text(M, 4.6, 'Fuentes: texto radicado del proyecto (MinHacienda · DIAN, 105 págs.)\n'
                'Caudal: 13.172 proyectos de ley y 317.455 votos nominales de la Cámara.',
        fontsize=8.4, color=MUTED, va='center', linespacing=1.5, **REG)
logo(93, 3.9, scale=1.0)

fig.savefig(OUT, dpi=100)
print('✓', OUT)
