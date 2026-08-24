# -*- coding: utf-8 -*-
"""
Carrusel Instagram (10 slides · 1080x1080) — Voto fusil 2026.
Portada = imagen de referencia (comandante EMC "profesor"). Resto condensa
el análisis (tijera por puesto, Llorente, inversión, participación, 10 zonas,
coacción documentada, simetría Catatumbo, cierre).

Identidad: paper #f1eee4, ink #1a1510, oxblood #8a1e16, ámbar #cf7d2a,
Cepeda rojo #c0392b / Abelardo azul #1f47cc. Títulos Arima, cuerpo DejaVu Sans.
Logo + crédito + contador n/10. SIN watermark (públicas).

Corre: python3 tools/voto-fusil/build_carrusel_ig.py
Salida: rrss/instagram/carrusel-voto-fusil/01..10.png
"""
import os, json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle, FancyArrowPatch
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONTS = os.path.join(ROOT, 'tools/edad-1v-2026/fonts')
OUT = os.path.join(ROOT, 'rrss/instagram/carrusel-voto-fusil')
GEO = os.path.join(ROOT, 'Bases de datos/output_pacto_1v_2026/geo')
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
LOGO = os.path.join(ROOT, 'Bases de datos/output_abelardo_cartagena/logo_ricardoruiz.png')
os.makedirs(OUT, exist_ok=True)

for f in ('Arima-Bold.ttf', 'Arima-SemiBold.ttf'):
    fm.fontManager.addfont(os.path.join(FONTS, f))
AR = fm.FontProperties(fname=os.path.join(FONTS, 'Arima-Bold.ttf'))
ARS = fm.FontProperties(fname=os.path.join(FONTS, 'Arima-SemiBold.ttf'))
SANS = fm.FontProperties(family='DejaVu Sans')
SANSB = fm.FontProperties(family='DejaVu Sans', weight='bold')

PAPER = '#f1eee4'; INK = '#1a1510'; OX = '#8a1e16'; AMBER = '#cf7d2a'; MUT = '#6b6258'
CEP = '#c0392b'; ABE = '#1f47cc'; AFRO = '#2f6e8e'; INDIG = '#2e8b57'; CAMP = '#8c2018'
GRID = '#cfc7b6'

plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['text.color'] = INK


def canvas():
    fig = plt.figure(figsize=(10.8, 10.8), dpi=100)
    fig.patch.set_facecolor(PAPER)
    return fig


def chrome(fig, n):
    """logo abajo-izq + crédito abajo-der + contador n/10."""
    lg = Image.open(LOGO).convert('RGBA'); r = lg.height / lg.width
    w = 0.20
    axl = fig.add_axes([0.066, 0.034, w, w * r]); axl.imshow(lg); axl.axis('off')
    fig.text(0.934, 0.045, 'ricardoruiz.co', fontsize=15, color=MUT,
             fontproperties=SANSB, ha='right', va='center')
    fig.text(0.5, 0.045, f'{n} / 10', fontsize=13, color=MUT, fontproperties=SANS,
             ha='center', va='center')


def kicker(fig, t='VOTO FUSIL 2026', y=0.945):
    fig.text(0.066, y, ' '.join(t), fontsize=15, color=OX, fontproperties=SANSB, va='center')


def title(fig, t, y=0.895, fs=44):
    fig.text(0.066, y, t, fontsize=fs, color=INK, fontproperties=AR, va='top',
             linespacing=1.05)


def paras(fig, lines, y0, fs=22, dy=0.046, x=0.066, color='#2a251f', bold_idx=()):
    for i, ln in enumerate(lines):
        fp = SANSB if i in bold_idx else SANS
        fig.text(x, y0 - i * dy, ln, fontsize=fs, color=color, fontproperties=fp,
                 va='top')


# =====================================================================
# 01 · portada (imagen de referencia)
# =====================================================================
def s01():
    fig = canvas()
    im = Image.open(os.path.join(ASSETS, 'portada-ref.png')).convert('RGB')
    iw, ih = im.size
    # recorta a banda apaisada (mantiene tablero + comandante), grande para no dejar hueco
    band_h = 0.55
    crop_h = min(ih, int(iw * band_h))  # banda llena 1080 ancho sin distorsión
    im = im.crop((0, 0, iw, crop_h))
    ax = fig.add_axes([0.0, 1 - band_h, 1.0, band_h]); ax.imshow(im); ax.axis('off')
    # kicker sobre la imagen (esquina)
    fig.text(0.045, 1 - 0.055, ' '.join('VOTO FUSIL 2026'), fontsize=15, color='#f4ede0',
             fontproperties=SANSB, va='center')
    # título hasta "conflicto"
    fig.text(0.066, 1 - band_h - 0.05,
             'El voto fusil de 2026:\nno se puede ser\nnegacionista del conflicto.',
             fontsize=38, color=INK, fontproperties=AR, va='top', linespacing=1.08)
    # resto como subtítulo
    fig.text(0.066, 0.165, 'Está ahí y está probado.\nNo está donde lo buscan.',
             fontsize=25, color=OX, fontproperties=SANSB, va='top', linespacing=1.12)
    chrome(fig, 1)
    fig.savefig(os.path.join(OUT, '01.png'), facecolor=PAPER)
    plt.close(fig); print('OK 01 portada')


# =====================================================================
# 02 · el dato que prendió todo
# =====================================================================
def s02():
    fig = canvas(); kicker(fig)
    title(fig, 'El dato que\nprendió todo', y=0.885, fs=52)
    fig.text(0.066, 0.60, '675', fontproperties=AR, fontsize=170, color=CEP, va='center')
    fig.text(0.066, 0.475, 'mesas con 100% para Cepeda', fontproperties=SANSB,
             fontsize=26, color=INK, va='center')
    paras(fig, [
        'Suena a fraude armado. Pero esas mesas pesan menos del',
        '0,5% del país y no movieron el resultado: Abelardo ganó',
        'por 250.830 votos. Tres análisis serios lo mostraron bien.',
        '',
        'Y ahí cerraron la pregunta. Nosotros apenas la abrimos.',
    ], y0=0.37, fs=22, dy=0.050, bold_idx=(4,))
    chrome(fig, 2)
    fig.savefig(os.path.join(OUT, '02.png'), facecolor=PAPER)
    plt.close(fig); print('OK 02')


# =====================================================================
# 03 · la tijera
# =====================================================================
def s03():
    fig = canvas(); kicker(fig)
    title(fig, 'La métrica que\nnadie midió: la tijera', y=0.885, fs=46)
    paras(fig, [
        'No el nivel de votación (el 100%), sino la dinámica de votos',
        'entre 1ª y 2ª vuelta. Subió la participación: lo normal es que',
        'los DOS candidatos crezcan. Lo raro es que uno crezca y el',
        'rival se DESPLOME en votos absolutos —que sus votantes',
        'reales, que en marzo existían, en junio desaparezcan.',
    ], y0=0.685, fs=23, dy=0.050)
    paras(fig, [
        'Y no viaja sola: donde se concentra, la acompaña presión',
        'armada documentada por la Defensoría y la prensa.',
    ], y0=0.415, fs=22, dy=0.046, color=OX, bold_idx=(0, 1))
    # franja destacada
    fig.patches.append(Rectangle((0.066, 0.135), 0.868, 0.115, transform=fig.transFigure,
                                 facecolor='#e7e0d0', edgecolor='none'))
    fig.text(0.5, 0.193, 'La mido a nivel de PUESTO rural georreferenciado,',
             fontsize=20, color=INK, fontproperties=SANSB, ha='center', va='center')
    fig.text(0.5, 0.158, 'no de municipio. 14.206 puestos, uno por uno.',
             fontsize=20, color=INK, fontproperties=SANSB, ha='center', va='center')
    chrome(fig, 3)
    fig.savefig(os.path.join(OUT, '03.png'), facecolor=PAPER)
    plt.close(fig); print('OK 03')


# =====================================================================
# 04 · caso Llorente (barras)
# =====================================================================
def s04():
    cep1, abe1 = 1816, 219
    cep2, abe2 = 3678, 101
    fig = canvas(); kicker(fig)
    title(fig, 'Llorente, Tumaco:\nun caso con nombre', y=0.895, fs=44)
    fig.text(0.066, 0.695, 'Llegaron 1.681 votantes más… y Abelardo cayó de 219 a 101.',
             fontsize=21, color='#2a251f', fontproperties=SANS, va='top')
    fig.text(0.066, 0.655, 'Cara a cara, Cepeda pasó de 89% a 97%.',
             fontsize=20, color=OX, fontproperties=SANSB, va='top')
    # contexto: el caso no viene solo, hay presión armada documentada
    fig.text(0.066, 0.615,
             'Y no es solo el dato: el corredor de Llorente está bajo control armado\n'
             'documentado (frente Oliver Sinisterra · Defensoría AT 013-25).',
             fontsize=16, color='#3a352d', fontproperties=SANS, va='top', linespacing=1.2)

    ax = fig.add_axes([0.10, 0.205, 0.84, 0.34]); ax.set_facecolor(PAPER)
    xc = [0.22, 1.18]; bw = 0.30
    for i, (lab, c, a) in enumerate([('1ª vuelta', cep1, abe1), ('2ª vuelta', cep2, abe2)]):
        x = xc[i]
        ax.bar(x - bw / 2, c, bw, color=CEP, zorder=3)
        ax.bar(x + bw / 2, a, bw, color=ABE, zorder=3)
        ax.text(x - bw / 2, c + 80, f'{c:,}'.replace(',', '.'), ha='center', va='bottom',
                color=CEP, fontproperties=SANSB, fontsize=22)
        ax.text(x + bw / 2, a + 80, f'{a:,}'.replace(',', '.'), ha='center', va='bottom',
                color=ABE, fontproperties=SANSB, fontsize=22)
        ax.text(x, -180, lab, ha='center', va='top', fontproperties=SANSB, fontsize=22)
    ax.annotate('', xy=(0.98, 4200), xytext=(0.42, 4200),
                arrowprops=dict(arrowstyle='-|>', color=MUT, lw=2.2))
    ax.text(0.70, 4330, '+1.681 votantes', ha='center', va='bottom', color='#4a443c',
            fontproperties=SANSB, fontsize=21)
    ax.set_xlim(-0.12, 1.55); ax.set_ylim(0, 4700); ax.axis('off')
    # leyenda (debajo, separada de las etiquetas de eje)
    for lx, col, lab in [(0.10, CEP, 'Cepeda'), (0.40, ABE, 'Abelardo')]:
        fig.patches.append(Rectangle((lx, 0.112), 0.026, 0.032, transform=fig.transFigure,
                                     facecolor=col, edgecolor='none'))
        fig.text(lx + 0.040, 0.128, lab, fontsize=21, fontproperties=SANS, va='center')
    chrome(fig, 4)
    fig.savefig(os.path.join(OUT, '04.png'), facecolor=PAPER)
    plt.close(fig); print('OK 04')


# =====================================================================
# 05 · la inversión (étnico vs campesino)
# =====================================================================
def s05():
    fig = canvas(); kicker(fig)
    title(fig, 'El 100% es étnico.\nLa anomalía, campesina.', y=0.895, fs=44)
    fig.text(0.066, 0.70, 'Lo unánime y lo sospechoso NO viven en el mismo territorio.',
             fontsize=21, color='#2a251f', fontproperties=SANS, va='top')
    fig.text(0.066, 0.662, 'Esas tijeras campesinas están en zona cocalera, bajo control del EMC.',
             fontsize=18, color=OX, fontproperties=SANSB, va='top')

    ax = fig.add_axes([0.066, 0.21, 0.868, 0.40]); ax.set_facecolor(PAPER)
    ax.set_xlim(0, 100); ax.set_ylim(0, 10); ax.axis('off')

    def stacked(y, segs, label):
        ax.text(0, y + 2.5, label, fontproperties=SANSB, fontsize=20, color=INK)
        x = 0
        for w, col, lab in segs:
            ax.add_patch(Rectangle((x, y), w, 2.0, facecolor=col, edgecolor=PAPER, lw=2))
            if w >= 7:
                ax.text(x + w / 2, y + 1.0, lab, ha='center', va='center', color='white',
                        fontproperties=SANSB, fontsize=18)
            x += w
    stacked(5.7, [(52, AFRO, '52%'), (27, INDIG, '27%'), (22, CAMP, '22%')],
            'MESAS 100%  ·  voto en bloque')
    stacked(1.2, [(17, AFRO, '17%'), (8, INDIG, '8%'), (72, CAMP, '72%'), (3, '#c4bda8', '')],
            '“TIJERAS”  ·  la anomalía real')
    ax.text(99, 4.5, '22%  →  72%', ha='right', va='center', color=CAMP,
            fontproperties=SANSB, fontsize=20)

    leg = [(AFRO, 'Consejo afro'), (INDIG, 'Resguardo indígena'), (CAMP, 'Campesino / coca')]
    lx = 0.066
    for col, lab in leg:
        fig.patches.append(Rectangle((lx, 0.135), 0.022, 0.028, transform=fig.transFigure,
                                     facecolor=col, edgecolor='none'))
        fig.text(lx + 0.034, 0.149, lab, fontsize=18, fontproperties=SANS, va='center')
        lx += 0.034 + 0.0135 * len(lab) + 0.05
    chrome(fig, 5)
    fig.savefig(os.path.join(OUT, '05.png'), facecolor=PAPER)
    plt.close(fig); print('OK 05')


# =====================================================================
# 06 · participación = movilización
# =====================================================================
def s06():
    fig = canvas(); kicker(fig)
    title(fig, 'No es abstención:\nes movilización', y=0.895, fs=46)
    paras(fig, [
        'Estas zonas arrancaron por DEBAJO del promedio nacional de',
        'participación… y en 2ª vuelta lo sobrepasaron, subiendo el doble.',
        'Inusual, aun con el alza general de participación entre vueltas.',
    ], y0=0.715, fs=20, dy=0.040)

    ax = fig.add_axes([0.10, 0.155, 0.86, 0.45]); ax.set_facecolor(PAPER)
    series = [('Las 10 zonas', 56, 70, OX, '+14'),
              ('Nacional', 59, 65, '#9a9388', '+6'),
              ('Tumaco', 38, 58, AMBER, '+20')]
    for name, v1, v2, col, dl in series:
        ax.plot([0, 1], [v1, v2], '-', color=col, lw=6, solid_capstyle='round', zorder=3)
        ax.plot([0, 1], [v1, v2], 'o', color=col, ms=15, zorder=4)
        ax.text(-0.05, v1, f'{v1}%', ha='right', va='center', color=col,
                fontproperties=SANSB, fontsize=20)
        ax.text(1.05, v2, f'{v2}%', ha='left', va='center', color=col,
                fontproperties=SANSB, fontsize=20)
        ax.text(1.27, v2, f'{name} ({dl})', ha='left', va='center', color=col,
                fontproperties=SANSB, fontsize=19)
    ax.set_xlim(-0.20, 2.30); ax.set_ylim(28, 78)
    ax.set_xticks([0, 1]); ax.set_xticklabels(['1ª vuelta', '2ª vuelta'],
                                              fontproperties=SANSB, fontsize=19)
    ax.tick_params(length=0); ax.set_yticks([])
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color(GRID)
    fig.text(0.066, 0.098, 'Llega más gente Y el rival cae: firma de votación organizada.',
             fontsize=17, color=OX, fontproperties=SANSB, va='center')
    chrome(fig, 6)
    fig.savefig(os.path.join(OUT, '06.png'), facecolor=PAPER)
    plt.close(fig); print('OK 06')


# =====================================================================
# 07 · las 10 zonas (mapa Cauca + Nariño)
# =====================================================================
ZONAS = {
    ('23', '139'): ('Tumaco', 'full'), ('23', '098'): ('Policarpa', 'full'),
    ('11', '005'): ('Argelia', 'full'), ('11', '058'): ('Patía', 'full'),
    ('11', '025'): ('El Tambo', 'full'), ('11', '046'): ('Mercaderes', 'full'),
    ('11', '007'): ('Bolívar', 'parcial'), ('23', '080'): ('Leiva', 'parcial'),
    ('23', '039'): ('Cumbitara', 'parcial'), ('11', '004'): ('Almaguer', 'parcial'),
}


def s07():
    import geopandas as gpd
    tij = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '_tijeras.json')))
    pts = [p for p in tij if (p['dep'], p['mun']) in ZONAS]
    fig = canvas(); kicker(fig)
    title(fig, '10 zonas, un solo dueño', y=0.895, fs=46)
    paras(fig, [
        'Las tijeras coinciden con grupo armado + Defensoría + prensa',
        'en 10 zonas de Cauca y Nariño. Todas del EMC, línea ‘Mordisco’:',
        'frentes Carlos Patiño, Franco Benavides y Oliver Sinisterra.',
    ], y0=0.79, fs=21, dy=0.043)

    ax = fig.add_axes([0.02, 0.115, 0.78, 0.55]); ax.set_facecolor(PAPER)
    g11 = gpd.read_file(os.path.join(GEO, 'mps', '11.json'))
    g23 = gpd.read_file(os.path.join(GEO, 'mps', '23.json'))
    for g in (g11, g23):
        g.plot(ax=ax, facecolor='#e4dfd1', edgecolor=GRID, lw=0.5)
        g['ME'] = g['mun_elec'].astype(str).str.zfill(3)
    for (dep, mun), (nombre, tipo) in ZONAS.items():
        col = OX if tipo == 'full' else AMBER
        g = g11 if dep == '11' else g23
        sub = g[(g['dep_electoral'].astype(str).str.zfill(2) == dep) & (g['ME'] == mun)]
        if len(sub):
            sub.plot(ax=ax, facecolor=col, alpha=0.16, edgecolor=col, lw=1.2)
    for tipo, col in (('full', OX), ('parcial', AMBER)):
        xs = [p['lon'] for p in pts if ZONAS[(p['dep'], p['mun'])][1] == tipo]
        ys = [p['lat'] for p in pts if ZONAS[(p['dep'], p['mun'])][1] == tipo]
        ax.scatter(xs, ys, s=130, c=col, edgecolor='white', lw=1.1, zorder=5, alpha=0.92)
    # recorta a la extensión de los puestos-tijera (sin el oriente vacío de los deptos)
    lons = [p['lon'] for p in pts]; lats = [p['lat'] for p in pts]
    mx = (max(lons) - min(lons)) * 0.12 + 0.12
    my = (max(lats) - min(lats)) * 0.12 + 0.12
    ax.set_xlim(min(lons) - mx, max(lons) + mx)
    ax.set_ylim(min(lats) - my, max(lats) + my)
    ax.set_aspect('equal'); ax.axis('off')

    # leyenda a la derecha
    fig.patches.append(Rectangle((0.80, 0.46), 0.030, 0.030, transform=fig.transFigure,
                                 facecolor=OX, edgecolor='none'))
    fig.text(0.80, 0.435, 'Hecho fechado\n(6 zonas)', fontsize=16, fontproperties=SANS, va='top')
    fig.patches.append(Rectangle((0.80, 0.345), 0.030, 0.030, transform=fig.transFigure,
                                 facecolor=AMBER, edgecolor='none'))
    fig.text(0.80, 0.32, 'Presencia +\nalerta (4 zonas)', fontsize=16, fontproperties=SANS, va='top')
    fig.text(0.80, 0.20, '66 puestos-\ntijera', fontsize=17, color=OX,
             fontproperties=SANSB, va='top')
    chrome(fig, 7)
    fig.savefig(os.path.join(OUT, '07.png'), facecolor=PAPER)
    plt.close(fig); print('OK 07 ·', len(pts), 'puestos')


# =====================================================================
# 08 · coacción documentada
# =====================================================================
def s08():
    fig = canvas(); kicker(fig)
    title(fig, 'Acá no estamos\nadivinando', y=0.895, fs=48)
    fig.text(0.066, 0.695, 'En estas zonas la evidencia ya inclina la balanza:',
             fontsize=22, color='#2a251f', fontproperties=SANS, va='top')

    cards = [
        ('Policarpa', ['Masacre en zona rural el 5 de marzo y audio',
                       'de las disidencias exigiendo el certificado',
                       'electoral para poder moverse.']),
        ('Tumaco', ['“Gobernanza criminal” que veta candidaturas',
                    '(Defensoría AT 013-25). Líder indígena Awá',
                    'asesinado el 14 de junio, a una semana del voto.']),
    ]
    y = 0.59
    for nombre, body in cards:
        fig.patches.append(Rectangle((0.066, y - 0.165), 0.868, 0.155, transform=fig.transFigure,
                                     facecolor='#e7e0d0', edgecolor='none'))
        fig.patches.append(Rectangle((0.066, y - 0.165), 0.012, 0.155, transform=fig.transFigure,
                                     facecolor=OX, edgecolor='none'))
        fig.text(0.10, y - 0.02, nombre, fontsize=27, color=OX, fontproperties=AR, va='top')
        for i, ln in enumerate(body):
            fig.text(0.10, y - 0.062 - i * 0.034, ln, fontsize=19, color='#2a251f',
                     fontproperties=SANS, va='top')
        y -= 0.235
    fig.text(0.066, 0.125, 'El terreno valida cada denuncia. No decide si el fenómeno existe.',
             fontsize=19, color=INK, fontproperties=SANSB, va='center')
    chrome(fig, 8)
    fig.savefig(os.path.join(OUT, '08.png'), facecolor=PAPER)
    plt.close(fig); print('OK 08')


# =====================================================================
# 09 · el otro bando (Catatumbo · coincidencia, no prueba)
# =====================================================================
def s09():
    fig = canvas(); kicker(fig)
    title(fig, '¿Y el otro bando?', y=0.895, fs=50)
    paras(fig, [
        'En el Catatumbo, a nivel municipio, hay una coincidencia:',
        'la ideología del grupo que manda se alinea con la mayoría.',
    ], y0=0.74, fs=22, dy=0.046)
    # dos columnas
    fig.text(0.10, 0.62, 'Manda el ELN', fontsize=22, color=CEP, fontproperties=SANSB, va='top')
    paras(fig, ['El Tarra 82%', 'Teorama 86%', 'San Calixto 89%', '→ ganó Cepeda'],
          y0=0.575, fs=20, dy=0.040, x=0.10, color=INK)
    fig.text(0.55, 0.62, 'Mandan grupos de derecha', fontsize=22, color=ABE,
             fontproperties=SANSB, va='top')
    paras(fig, ['Sardinata 89%', 'Ábrego 82%', 'Tibú 60%', '→ ganó Abelardo'],
          y0=0.575, fs=20, dy=0.040, x=0.55, color=INK)
    # caveat
    fig.patches.append(Rectangle((0.066, 0.135), 0.868, 0.215, transform=fig.transFigure,
                                 facecolor='#e7e0d0', edgecolor='none'))
    fig.text(0.10, 0.318, 'Pero es coincidencia, no prueba.', fontsize=23, color=OX,
             fontproperties=SANSB, va='top')
    paras(fig, [
        'A diferencia de las 10 zonas, acá no hay tijera por puesto',
        'ni un solo hecho de coacción electoral documentado en 2026.',
        'Puede ser presión… o liderazgos locales con ideología afín,',
        'sin que nadie tenga que apuntar un arma.',
    ], y0=0.272, fs=19.5, dy=0.036, x=0.10, color='#2a251f')
    chrome(fig, 9)
    fig.savefig(os.path.join(OUT, '09.png'), facecolor=PAPER)
    plt.close(fig); print('OK 09')


# =====================================================================
# 10 · cierre / posición
# =====================================================================
def s10():
    fig = canvas(); kicker(fig)
    title(fig, 'En resumen…', y=0.885, fs=56)
    qa = [
        ('¿Hubo voto fusil?', 'Sí, puntual y en varios bandos.'),
        ('¿Fue masivo?', 'No: el grueso del 100% es voto étnico legítimo.'),
        ('¿Cambió la elección?', 'No: pesa ~0,2% y Abelardo ganó por 250 mil.'),
    ]
    y = 0.66
    for q, a in qa:
        fig.text(0.066, y, q, fontsize=24, color=OX, fontproperties=SANSB, va='top')
        fig.text(0.066, y - 0.040, a, fontsize=21, color=INK, fontproperties=SANS, va='top')
        y -= 0.115
    fig.patches.append(Rectangle((0.066, 0.16), 0.868, 0.14, transform=fig.transFigure,
                                 facecolor='#e7e0d0', edgecolor='none'))
    fig.text(0.10, 0.275, 'La pregunta correcta no es “¿ganó por el fusil?” (no).',
             fontsize=19, color=INK, fontproperties=SANS, va='top')
    fig.text(0.10, 0.232, 'Es: ¿dónde el conflicto le quita a la gente',
             fontsize=20, color=INK, fontproperties=SANSB, va='top')
    fig.text(0.10, 0.196, 'la libertad de votar?',
             fontsize=20, color=INK, fontproperties=SANSB, va='top')
    fig.text(0.066, 0.115, 'Metodología y tabla zona por zona  ·  ricardoruiz.co/voto-fusil-2026.html',
             fontsize=15, color=OX, fontproperties=SANSB, va='center')
    chrome(fig, 10)
    fig.savefig(os.path.join(OUT, '10.png'), facecolor=PAPER)
    plt.close(fig); print('OK 10')


if __name__ == '__main__':
    s01(); s02(); s03(); s04(); s05(); s06(); s07(); s08(); s09(); s10()
    print('\ncarrusel listo en', OUT)
