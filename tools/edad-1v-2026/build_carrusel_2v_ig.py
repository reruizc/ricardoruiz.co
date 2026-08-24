# -*- coding: utf-8 -*-
"""
Carrusel Instagram (10 slides · 1080x1080) — El abismo generacional de la 2V 2026.
Lee ei-2v-final.csv + ei-2v-regional.csv. Identidad de los carruseles del
proyecto: paper #f1eee4, ink #1a1510, oxblood #8a1e16, Cepeda rojo #c0392b /
Abelardo azul #1f47cc. Títulos Arima, cuerpo DejaVu Sans. Logo + crédito +
contador n/10. SIN watermark (públicas).

Corre: python3 tools/edad-1v-2026/build_carrusel_2v_ig.py
Salida: rrss/instagram/carrusel-edades-2v/01..10.png
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FONTS = os.path.join(HERE, 'fonts')
DATA = os.path.join(ROOT, 'Bases de datos', 'output_edad_1v')
OUT = os.path.join(ROOT, 'rrss', 'instagram', 'carrusel-edades-2v')
LOGO = os.path.join(ROOT, 'Bases de datos', 'output_abelardo_cartagena', 'logo_ricardoruiz.png')
os.makedirs(OUT, exist_ok=True)

for f in ('Arima-Bold.ttf', 'Arima-SemiBold.ttf'):
    fm.fontManager.addfont(os.path.join(FONTS, f))
AR = fm.FontProperties(fname=os.path.join(FONTS, 'Arima-Bold.ttf'))
ARS = fm.FontProperties(fname=os.path.join(FONTS, 'Arima-SemiBold.ttf'))
SANS = fm.FontProperties(family='DejaVu Sans')
SANSB = fm.FontProperties(family='DejaVu Sans', weight='bold')

PAPER = '#f1eee4'; INK = '#1a1510'; OX = '#8a1e16'; AMBER = '#cf7d2a'; MUT = '#6b6258'
CEP = '#c0392b'; ABE = '#1f47cc'; GREY = '#9aa3b4'; GRID = '#cfc7b6'
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['text.color'] = INK

GN = ['18-25', '26-35', '36-45', '46-60', '61+']
FINAL = pd.read_csv(os.path.join(DATA, 'ei-2v-final.csv'))
REG = pd.read_csv(os.path.join(DATA, 'ei-2v-regional.csv'))


def curve(contest):
    d = FINAL[FINAL.contest == contest].set_index('grupo').loc[GN]
    return d['izq_share'].values * 100, d['lo'].values * 100, d['hi'].values * 100


# --------------------------------------------------------------- chrome/helpers
def canvas():
    fig = plt.figure(figsize=(10.8, 10.8), dpi=100)
    fig.patch.set_facecolor(PAPER)
    return fig


def chrome(fig, n):
    lg = Image.open(LOGO).convert('RGBA'); r = lg.height / lg.width
    w = 0.20
    axl = fig.add_axes([0.066, 0.032, w, w * r]); axl.imshow(lg); axl.axis('off')
    fig.text(0.934, 0.045, 'ricardoruiz.co', fontsize=15, color=MUT,
             fontproperties=SANSB, ha='right', va='center')
    fig.text(0.5, 0.045, f'{n} / 10', fontsize=13, color=MUT, fontproperties=SANS,
             ha='center', va='center')


def kicker(fig, t='SEGUNDA VUELTA 2026 · POR EDAD', y=0.945):
    fig.text(0.066, y, ' '.join(t), fontsize=13.5, color=OX, fontproperties=SANSB, va='center')


def title(fig, t, y=0.885, fs=46):
    fig.text(0.066, y, t, fontsize=fs, color=INK, fontproperties=AR, va='top',
             linespacing=1.06)


def paras(fig, lines, y0, fs=22, dy=0.045, x=0.066, color='#2a251f', bold_idx=()):
    for i, ln in enumerate(lines):
        fp = SANSB if i in bold_idx else SANS
        fig.text(x, y0 - i * dy, ln, fontsize=fs, color=color, fontproperties=fp, va='top')


# =====================================================================
def s01():
    fig = canvas()
    kicker(fig, y=0.90)
    title(fig, 'Cepeda ganó a los\njóvenes, a los adultos\ny a los maduros.', y=0.83, fs=54)
    fig.text(0.066, 0.50, 'Perdió la presidencia\nentre los mayores de 60.',
             fontsize=32, color=OX, fontproperties=ARS, va='top', linespacing=1.12)
    fig.text(0.066, 0.375, 'Quién votó por quién, por edad, en la segunda vuelta.',
             fontsize=19, color=MUT, fontproperties=SANS, va='top')
    # curva decorativa en banda inferior (sin cruzar texto)
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0]); ax.axis('off'); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    y, _, _ = curve('2V-2026')
    xs = np.linspace(0.10, 0.94, 5)
    yy = 0.145 + np.array(y) / 100 * 0.14
    ax.plot(xs, yy, color=CEP, lw=5, alpha=0.22, zorder=0)
    ax.scatter(xs, yy, s=220, color=CEP, alpha=0.22, zorder=0)
    chrome(fig, 1)
    fig.savefig(os.path.join(OUT, '01.png'), facecolor=PAPER); plt.close(fig); print('OK 01')


def s02():
    fig = canvas(); kicker(fig)
    title(fig, 'Ganó 4 de los 5\ngrupos de edad', y=0.885, fs=52)
    # 5 bloques
    ax = fig.add_axes([0.066, 0.40, 0.868, 0.20]); ax.axis('off'); ax.set_xlim(0, 5); ax.set_ylim(0, 1)
    cols = [CEP, CEP, CEP, CEP, ABE]
    for i, (g, c) in enumerate(zip(GN, cols)):
        ax.add_patch(Rectangle((i + 0.06, 0.15), 0.88, 0.70, color=c))
        ax.text(i + 0.5, 0.5, g, ha='center', va='center', color='#f4ede0',
                fontproperties=SANSB, fontsize=17)
    fig.text(0.066, 0.35, 'Cuatro en rojo para Cepeda. Uno en azul para Abelardo.',
             fontsize=20, color=MUT, fontproperties=SANS, va='top')
    paras(fig, [
        'Y aun así no llegó a la Casa de Nariño. Toda la',
        'elección se jugó en esa única franja azul.',
    ], 0.28, fs=23, bold_idx=())
    chrome(fig, 2)
    fig.savefig(os.path.join(OUT, '02.png'), facecolor=PAPER); plt.close(fig); print('OK 02')


def s03():
    fig = canvas(); kicker(fig)
    title(fig, 'Cuánto le votó\ncada edad', y=0.885, fs=52)
    y, lo, hi = curve('2V-2026')
    ax = fig.add_axes([0.10, 0.175, 0.85, 0.47])
    ax.set_facecolor(PAPER)
    x = np.arange(5)
    ax.fill_between(x, lo, hi, color=CEP, alpha=0.12, lw=0)
    ax.plot(x, y, '-', color=CEP, lw=4, zorder=4)
    ax.scatter(x, y, s=230, color=CEP, zorder=5, edgecolor=PAPER, lw=2)
    for i, v in enumerate(y):
        ax.text(i, v + 7, f'{v:.0f}%', ha='center', color=CEP, fontproperties=SANSB, fontsize=22)
    ax.axhline(50, color=MUT, lw=1.2, ls=':')
    ax.set_xticks(x); ax.set_xticklabels(GN, fontproperties=SANSB, fontsize=17, color=INK)
    ax.set_yticks([0, 50, 100]); ax.set_yticklabels(['0%', '50%', '100%'], fontsize=13, color=MUT)
    ax.set_ylim(-6, 106)
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'): ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUT)
    fig.text(0.066, 0.72, 'Voto a Cepeda entre los dos finalistas, por edad',
             fontsize=18, color=MUT, fontproperties=SANS)
    fig.text(0.066, 0.085, 'Un descenso suave… y un precipicio al final.',
             fontsize=21, color=OX, fontproperties=SANSB)
    chrome(fig, 3)
    fig.savefig(os.path.join(OUT, '03.png'), facecolor=PAPER); plt.close(fig); print('OK 03')


def s04():
    fig = canvas(); kicker(fig)
    title(fig, 'Entre los mayores\nde 60:', y=0.885, fs=50)
    fig.text(0.066, 0.60, '94', fontproperties=AR, fontsize=150, color=ABE, va='center')
    fig.text(0.44, 0.635, 'de cada 100', fontproperties=SANSB, fontsize=30, color=INK, va='center')
    fig.text(0.44, 0.565, 'votaron por Abelardo', fontproperties=SANSB, fontsize=30, color=ABE, va='center')
    paras(fig, [
        'Ese grupo es 1 de cada 5 votantes del país.',
        '',
        'Ahí —y solo ahí— se decidió quién iba a ser',
        'el presidente de Colombia.',
    ], 0.40, fs=24, bold_idx=(3,))
    chrome(fig, 4)
    fig.savefig(os.path.join(OUT, '04.png'), facecolor=PAPER); plt.close(fig); print('OK 04')


def s05():
    fig = canvas(); kicker(fig)
    title(fig, 'Dos países que\nvotaron el mismo día', y=0.885, fs=48)
    # dos columnas
    ax = fig.add_axes([0.066, 0.30, 0.868, 0.40]); ax.axis('off'); ax.set_xlim(0, 2); ax.set_ylim(0, 1)
    ax.text(0.5, 0.92, 'CEPEDA', ha='center', color=CEP, fontproperties=SANSB, fontsize=24)
    ax.text(1.5, 0.92, 'ABELARDO', ha='center', color=ABE, fontproperties=SANSB, fontsize=24)
    ax.text(0.5, 0.60, '48%', ha='center', color=CEP, fontproperties=AR, fontsize=54)
    ax.text(0.5, 0.42, 'menor de 36 años', ha='center', color=INK, fontproperties=SANS, fontsize=18)
    ax.text(1.5, 0.60, '39%', ha='center', color=ABE, fontproperties=AR, fontsize=54)
    ax.text(1.5, 0.42, 'mayor de 60 años', ha='center', color=INK, fontproperties=SANS, fontsize=18)
    ax.text(0.5, 0.16, 'Apenas 2% supera los 60', ha='center', color=MUT, fontproperties=SANS, fontsize=14)
    ax.text(1.5, 0.16, 'Apenas 7% es menor de 26', ha='center', color=MUT, fontproperties=SANS, fontsize=14)
    ax.plot([1, 1], [0.05, 0.98], color=GRID, lw=1.4)
    fig.text(0.066, 0.235, 'La frontera no es de clase ni de región.',
             fontsize=23, color=INK, fontproperties=SANSB, va='top')
    fig.text(0.066, 0.185, 'Es la fecha de nacimiento.',
             fontsize=23, color=OX, fontproperties=SANSB, va='top')
    chrome(fig, 5)
    fig.savefig(os.path.join(OUT, '05.png'), facecolor=PAPER); plt.close(fig); print('OK 05')


def s06():
    fig = canvas(); kicker(fig)
    title(fig, 'Esto ya había pasado,\nidéntico, en 2022', y=0.885, fs=44)
    ax = fig.add_axes([0.10, 0.20, 0.85, 0.46]); ax.set_facecolor(PAPER)
    x = np.arange(5)
    for contest, col, lab in (('2V-2026', CEP, 'Cepeda vs Abelardo (2026)'),
                              ('2V-2022', '#7a5cb0', 'Petro vs Rodolfo (2022)')):
        y, _, _ = curve(contest)
        ax.plot(x, y, '-o', color=col, lw=3.4, ms=11, markeredgecolor=PAPER,
                markeredgewidth=1.6, label=lab, zorder=4)
    ax.axhline(50, color=MUT, lw=1, ls=':')
    ax.set_xticks(x); ax.set_xticklabels(GN, fontproperties=SANSB, fontsize=15, color=INK)
    ax.set_yticks([0, 50, 100]); ax.set_yticklabels(['0%', '50%', '100%'], fontsize=12, color=MUT)
    ax.set_ylim(-6, 108)
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'): ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUT)
    ax.legend(loc='upper right', frameon=False, fontsize=14, prop=SANSB)
    fig.text(0.066, 0.155, 'Brecha joven–mayor:  2022  +74 pts   ·   2026  +70 pts',
             fontsize=20, color=INK, fontproperties=SANSB)
    fig.text(0.066, 0.115, 'El eje generacional no lo inventó esta elección. Es estructural.',
             fontsize=18, color=OX, fontproperties=SANS)
    chrome(fig, 6)
    fig.savefig(os.path.join(OUT, '06.png'), facecolor=PAPER); plt.close(fig); print('OK 06')


def s07():
    fig = canvas(); kicker(fig)
    title(fig, 'Hasta el outsider\nde TikTok terminó\nvotado por los viejos', y=0.90, fs=42)
    fig.text(0.066, 0.55, '94%', fontproperties=AR, fontsize=110, color='#7a5cb0', va='center')
    fig.text(0.066, 0.435, 'de los mayores de 60 votaron a Rodolfo en 2022',
             fontproperties=SANSB, fontsize=21, color=INK, va='center')
    paras(fig, [
        'Pese a su imagen antisistema, en el balotaje',
        'Rodolfo Hernández quedó con el perfil de un',
        'conservador clásico. El mismo espejo que hoy',
        'tiene Abelardo entre los mayores.',
    ], 0.35, fs=23)
    chrome(fig, 7)
    fig.savefig(os.path.join(OUT, '07.png'), facecolor=PAPER); plt.close(fig); print('OK 07')


def s08():
    fig = canvas(); kicker(fig)
    title(fig, 'Quedar dos candidatos\nno cerró la brecha:\nla abrió', y=0.90, fs=44)
    ax = fig.add_axes([0.066, 0.42, 0.55, 0.22]); ax.axis('off'); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.text(0.0, 0.5, '+66', fontproperties=AR, fontsize=64, color=MUT, va='center')
    ax.annotate('', xy=(0.62, 0.5), xytext=(0.40, 0.5),
                arrowprops=dict(arrowstyle='-|>', color=OX, lw=3))
    ax.text(0.66, 0.5, '+70', fontproperties=AR, fontsize=64, color=OX, va='center')
    fig.text(0.066, 0.40, 'Brecha generacional · de 1ª a 2ª vuelta',
             fontsize=17, color=MUT, fontproperties=SANS, va='top')
    paras(fig, [
        'Al quedar dos candidatos, Cepeda absorbió el',
        'voto joven del centro. Los mayores, en cambio,',
        'no se movieron un milímetro.',
    ], 0.30, fs=23)
    chrome(fig, 8)
    fig.savefig(os.path.join(OUT, '08.png'), facecolor=PAPER); plt.close(fig); print('OK 08')


def s09():
    fig = canvas(); kicker(fig)
    title(fig, 'El acantilado es,\nsobre todo, andino', y=0.90, fs=46)
    d = REG[REG.contest == '2V-2026']
    yv = d[d.grupo == '18-25'].set_index('region')['izq_share'] * 100
    ov = d[d.grupo == '61+'].set_index('region')['izq_share'] * 100
    order = (yv - ov).sort_values().index.tolist()
    ax = fig.add_axes([0.30, 0.30, 0.63, 0.42]); ax.set_facecolor(PAPER)
    for i, r in enumerate(order):
        ax.plot([ov[r], yv[r]], [i, i], color=MUT, lw=2.2, zorder=1)
        ax.scatter(ov[r], i, s=150, color=GREY, zorder=3, edgecolor=PAPER, lw=1.3)
        ax.scatter(yv[r], i, s=150, color=CEP, zorder=3, edgecolor=PAPER, lw=1.3)
        ax.text(yv[r] + 3, i, f'{yv[r]:.0f}', va='center', ha='left', color=CEP,
                fontproperties=SANSB, fontsize=13)
        ax.text(ov[r] - 3, i, f'{ov[r]:.0f}', va='center', ha='right', color=MUT,
                fontproperties=SANSB, fontsize=13)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([r.replace(' (Tolima-Huila-Amazonía)', '') for r in order],
                       fontproperties=SANSB, fontsize=14, color=INK)
    ax.set_xlim(-12, 112); ax.set_xticks([0, 50, 100])
    ax.set_xticklabels(['0%', '50%', '100%'], fontsize=12, color=MUT)
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'): ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUT)
    fig.text(0.066, 0.745, 'Voto a Cepeda: jóvenes (rojo) vs mayores de 60 (gris)',
             fontsize=16, color=MUT, fontproperties=SANS)
    fig.text(0.066, 0.205, 'En la costa (Pacífico 22%, Caribe 16%) los mayores',
             fontsize=18, color=OX, fontproperties=SANSB, va='top')
    fig.text(0.066, 0.160, 'están mucho más divididos que en el interior.',
             fontsize=18, color=OX, fontproperties=SANSB, va='top')
    chrome(fig, 9)
    fig.savefig(os.path.join(OUT, '09.png'), facecolor=PAPER); plt.close(fig); print('OK 09')


def s10():
    fig = canvas(); kicker(fig)
    title(fig, 'La izquierda no tiene\nun problema\nde jóvenes', y=0.90, fs=50)
    paras(fig, [
        'Los arrasa.',
        '',
        'Tiene un problema de mayores que no ha movido',
        'en dos segundas vueltas seguidas. Y los mayores',
        'de 60 son, justamente, el grupo que más crece',
        'cada año.',
    ], 0.50, fs=24, bold_idx=(0,))
    fig.text(0.066, 0.145,
             'Inferencia ecológica por puesto de votación · IC 95%.',
             fontsize=14, color=MUT, fontproperties=SANS)
    fig.text(0.066, 0.115,
             'Registraduría (edad de votantes) + DANE · preconteo, preliminar.',
             fontsize=14, color=MUT, fontproperties=SANS)
    chrome(fig, 10)
    fig.savefig(os.path.join(OUT, '10.png'), facecolor=PAPER); plt.close(fig); print('OK 10')


if __name__ == '__main__':
    for fn in (s01, s02, s03, s04, s05, s06, s07, s08, s09, s10):
        fn()
    print('\nCarrusel en', OUT)
