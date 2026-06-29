# -*- coding: utf-8 -*-
"""
Voto fusil 2026 — regenera las imágenes corregidas (a, b, c, d).
Identidad: paper #f1eee4, ink #1a1510, oxblood #8a1e16, ámbar #cf7d2a,
Cepeda rojo #c0392b / Abelardo azul #1f47cc. Títulos Arima.

Reconstruido jun-2026 (el script original no quedó en el repo).
Corre: python3 tools/voto-fusil/build_imgs.py
Salidas: rrss/twitter/voto-fusil-png/
  inversion-territorio.png         (fix a)
  participacion-movilizacion.png   (fix b)
  mapa-tijeras-cauca.png           (fix c-1)  [reemplaza mapa-10-sitios.png]
  mapa-tijeras-narino.png          (fix c-2)
  tabla-10-zonas-1.png             (fix d-1)  [reemplaza tabla-10-zonas.png]
  tabla-10-zonas-2.png             (fix d-2)
"""
import json, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyArrowPatch, Rectangle
from matplotlib.path import Path
import matplotlib.patches as mpatches

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONTS = os.path.join(ROOT, 'tools/edad-1v-2026/fonts')
OUT = os.path.join(ROOT, 'rrss/twitter/voto-fusil-png')
GEO = os.path.join(ROOT, 'Bases de datos/output_pacto_1v_2026/geo')
os.makedirs(OUT, exist_ok=True)

# ---- fonts ----
for f in ('Arima-Bold.ttf', 'Arima-SemiBold.ttf'):
    fm.fontManager.addfont(os.path.join(FONTS, f))
ARIMA_B = fm.FontProperties(fname=os.path.join(FONTS, 'Arima-Bold.ttf'))
ARIMA_SB = fm.FontProperties(fname=os.path.join(FONTS, 'Arima-SemiBold.ttf'))
SANS = fm.FontProperties(family='DejaVu Sans')
SANS_B = fm.FontProperties(family='DejaVu Sans', weight='bold')

# ---- palette ----
PAPER = '#f1eee4'
INK = '#1a1510'
OX = '#8a1e16'
AMBER = '#cf7d2a'
CEP = '#c0392b'
ABE = '#1f47cc'
AFRO = '#2f6e8e'
INDIG = '#2e8b57'
CAMP = '#8c2018'
MUTE = '#9a9388'
GRID = '#cfc8b8'

plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['text.color'] = INK
plt.rcParams['axes.edgecolor'] = INK


def kicker(fig, x=0.03, y=0.955):
    fig.text(x, y, 'V O T O   F U S I L   2 0 2 6', fontproperties=SANS_B,
             fontsize=12, color=OX)


def footer(fig, txt, x=0.03, y=0.045, size=10.5):
    fig.text(x, y, txt, fontproperties=SANS, fontsize=size, color='#6b655c', va='top')


def title(fig, txt, x=0.03, y=0.905, size=33):
    fig.text(x, y, txt, fontproperties=ARIMA_B, fontsize=size, color=INK, va='top')


def subtitle_lines(fig, lines, x=0.03, y=0.835, size=15.5, dy=0.0295, color='#33302a'):
    """Render subtitle line-by-line with generous line spacing (fix a/b)."""
    for i, ln in enumerate(lines):
        fig.text(x, y - i * dy, ln, fontproperties=SANS, fontsize=size,
                 color=color, va='top')


# =====================================================================
# (a) inversion-territorio.png
# =====================================================================
def build_inversion():
    fig = plt.figure(figsize=(11.0, 9.0), dpi=120)
    fig.patch.set_facecolor(PAPER)
    kicker(fig)
    title(fig, 'El 100% es étnico. La anomalía es campesina.', size=31)
    subtitle_lines(fig, [
        'Las mesas con 100% para Cepeda son voto en bloque de territorios afro e',
        'indígenas (genuino: el rival siempre estuvo en ~0). Pero la “tijera”',
        '—donde el rival real se desploma en votos de 1ª a 2ª vuelta— vive en',
        'territorio campesino-coca.',
    ], y=0.825, size=15, dy=0.030)

    ax = fig.add_axes([0.03, 0.10, 0.94, 0.55])
    ax.set_facecolor(PAPER)
    ax.set_xlim(0, 100); ax.set_ylim(0, 10)
    ax.axis('off')

    def stacked(y, h, segs, label):
        ax.text(0, y + h + 0.55, label, fontproperties=SANS_B, fontsize=15,
                color=INK)
        x = 0
        for w, col, lab in segs:
            ax.add_patch(Rectangle((x, y), w, h, facecolor=col, edgecolor=PAPER, lw=2))
            if w >= 6:
                ax.text(x + w / 2, y + h / 2, lab, ha='center', va='center',
                        color='white', fontproperties=SANS_B, fontsize=17)
            x += w

    # MESAS 100%  (52 afro / 27 indig / 22 campesino)
    stacked(6.0, 2.2, [(52, AFRO, '52%'), (27, INDIG, '27%'), (22, CAMP, '22%')],
            'MESAS 100%  ·  voto en bloque')
    # TIJERAS (17 afro / 8 indig / 72 campesino / 3 otro)
    stacked(1.0, 2.2, [(17, AFRO, '17%'), (8, INDIG, '8%'), (72, CAMP, '72%'),
                       (3, '#c4bda8', '')],
            '“TIJERAS”  ·  la anomalía real')

    # connector arrow 22% -> 72%
    arr = FancyArrowPatch((87, 6.0), (61, 3.2), connectionstyle='arc3,rad=-0.35',
                          arrowstyle='-', color=CAMP, lw=2.4)
    ax.add_patch(arr)
    ax.text(99, 4.65, '22%  →  72%', ha='right', va='center', color=CAMP,
            fontproperties=SANS_B, fontsize=16)

    # legend (separar cuadro de texto: gap ancho)
    leg = [(AFRO, 'Consejo afro'), (INDIG, 'Resguardo indígena'), (CAMP, 'Campesino / coca')]
    lx = 0.04
    for col, lab in leg:
        fig.patches.append(Rectangle((lx, 0.075), 0.022, 0.030, transform=fig.transFigure,
                                     facecolor=col, edgecolor='none', clip_on=False))
        fig.text(lx + 0.034, 0.090, lab, fontproperties=SANS, fontsize=13,
                 color=INK, va='center')
        lx += 0.034 + 0.012 * len(lab) + 0.05

    footer(fig, '675 mesas 100% Cepeda · 89 puestos con “tijera” fuerte (≥95% y rival cae ≥10 votos).   '
                'Fuente: preconteo 1V/2V 2026 + ANT.   Ricardo Ruiz · ricardoruiz.co', y=0.030, size=9.3)
    fig.savefig(os.path.join(OUT, 'inversion-territorio.png'), facecolor=PAPER,
                bbox_inches=None)
    plt.close(fig)
    print('OK inversion-territorio.png')


# =====================================================================
# (b) participacion-movilizacion.png
# =====================================================================
def build_participacion():
    fig = plt.figure(figsize=(10.3, 10.6), dpi=120)
    fig.patch.set_facecolor(PAPER)
    kicker(fig)
    title(fig, 'No es abstención: es movilización', size=33)
    subtitle_lines(fig, [
        'En las 10 zonas críticas la participación arrancó por debajo del',
        'promedio nacional y lo sobrepasó: subió más del doble entre 1ª y 2ª',
        'vuelta. Donde el rival se desploma, llega más gente a votar. Es la',
        'firma de la coacción organizada.',
    ], y=0.845, size=14.5, dy=0.0265)

    ax = fig.add_axes([0.10, 0.11, 0.85, 0.58])
    ax.set_facecolor(PAPER)
    # lines: (name, v1, v2, color, delta)
    series = [
        ('Las 10 zonas', 56, 70, OX, '+14'),
        ('Nacional', 59, 65, MUTE, '+6'),
        ('Tumaco', 38, 58, AMBER, '+20'),
    ]
    for name, v1, v2, col, dl in series:
        ax.plot([0, 1], [v1, v2], '-', color=col, lw=5, solid_capstyle='round', zorder=3)
        ax.plot([0, 1], [v1, v2], 'o', color=col, ms=13, zorder=4)
        # left label: % a la izquierda del punto
        ax.text(-0.045, v1, f'{v1}%', ha='right', va='center', color=col,
                fontproperties=SANS_B, fontsize=16)
        # right label: separar % del nombre (dos textos)
        ax.text(1.03, v2, f'{v2}%', ha='left', va='center', color=col,
                fontproperties=SANS_B, fontsize=16)
        ax.text(1.22, v2, f'{name}  ({dl})', ha='left', va='center', color=col,
                fontproperties=SANS_B, fontsize=16)

    ax.set_xlim(-0.18, 2.05)
    ax.set_ylim(28, 78)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['1ª vuelta', '2ª vuelta'], fontproperties=SANS_B, fontsize=15)
    ax.tick_params(length=0)
    ax.set_yticks([])
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color(GRID)
    ax.spines['left'].set_visible(True); ax.spines['left'].set_color(GRID)

    footer(fig, 'Participación = votantes / censo electoral, por puesto.   Puestos-tijera (89): 70%→83% (+14).\n'
                'Fuente: preconteo Registraduría + censo Divipole 2026.   Ricardo Ruiz · ricardoruiz.co', y=0.058)
    fig.savefig(os.path.join(OUT, 'participacion-movilizacion.png'), facecolor=PAPER)
    plt.close(fig)
    print('OK participacion-movilizacion.png')


# =====================================================================
# (c) mapas a nivel PUESTO — Cauca y Nariño
# =====================================================================
# zonas: (dep, mun) -> (nombre, frente, tipo full/parcial)
ZONAS = {
    ('23', '139'): ('Tumaco', 'Oliver Sinisterra', 'full'),
    ('23', '098'): ('Policarpa', 'Franco Benavides', 'full'),
    ('11', '005'): ('Argelia', 'Carlos Patiño', 'full'),
    ('11', '058'): ('Patía', 'Carlos Patiño', 'full'),
    ('11', '025'): ('El Tambo', 'Carlos Patiño', 'full'),
    ('11', '046'): ('Mercaderes', 'Carlos Patiño', 'full'),
    ('11', '007'): ('Bolívar', 'Carlos Patiño + ELN', 'parcial'),
    ('23', '080'): ('Leiva', 'Franco Benavides', 'parcial'),
    ('23', '039'): ('Cumbitara', 'Franco Benavides', 'parcial'),
    ('11', '004'): ('Almaguer', 'Carlos Patiño', 'parcial'),
}


def _load_geopandas():
    import geopandas as gpd
    return gpd


def _mun_geo(dep):
    import geopandas as gpd
    g = gpd.read_file(os.path.join(GEO, 'mps', dep + '.json'))
    return g


def build_mapa(dep, fname, panel_title, label_offsets):
    import geopandas as gpd
    tij = json.load(open(os.path.join(os.path.dirname(__file__), '_tijeras.json')))
    pts = [p for p in tij if p['dep'] == dep and (p['dep'], p['mun']) in ZONAS]

    g = _mun_geo(dep)
    g['ME'] = g['mun_elec'].astype(str).str.zfill(3)
    zmuns = {m: v for (d, m), v in ZONAS.items() if d == dep}

    fig = plt.figure(figsize=(10.5, 11.0), dpi=120)
    fig.patch.set_facecolor(PAPER)
    kicker(fig)
    title(fig, panel_title, size=30)
    subtitle_lines(fig, [
        'Cada punto es un puesto rural con “tijera” fuerte (zona 99,',
        'georreferenciado): Cepeda ≥95% y el rival cae ≥10 votos de 1V a 2V.',
        'Rojo = zona con hecho fechado · ámbar = presencia + alerta.',
    ], y=0.825, size=14, dy=0.027)

    ax = fig.add_axes([0.02, 0.085, 0.96, 0.66])
    ax.set_facecolor(PAPER)
    # base: todo el depto en gris claro
    g.plot(ax=ax, facecolor='#e4dfd1', edgecolor=GRID, lw=0.5)
    # resaltar los municipios-zona
    for m, (nombre, frente, tipo) in zmuns.items():
        col = OX if tipo == 'full' else AMBER
        sub = g[g['ME'] == m]
        if len(sub):
            sub.plot(ax=ax, facecolor=col, alpha=0.16, edgecolor=col, lw=1.4)
    # puntos puesto
    for tipo, col in (('full', OX), ('parcial', AMBER)):
        xs = [p['lon'] for p in pts if zmuns.get(p['mun'], ('', '', ''))[2] == tipo]
        ys = [p['lat'] for p in pts if zmuns.get(p['mun'], ('', '', ''))[2] == tipo]
        ax.scatter(xs, ys, s=120, c=col, edgecolor='white', lw=1.2, zorder=5,
                   alpha=0.92)

    # etiquetas de municipio: nombre + nº tijeras + frente
    from collections import Counter
    cnt = Counter((p['mun']) for p in pts)
    for m, (nombre, frente, tipo) in zmuns.items():
        sub = g[g['ME'] == m]
        if not len(sub):
            continue
        c = sub.geometry.iloc[0].representative_point()
        ox_, oy_ = label_offsets.get(m, (0.0, 0.12))
        col = OX if tipo == 'full' else AMBER
        ntj = cnt.get(m, 0)
        ax.annotate(f'{nombre}  ·  {ntj} tij.',
                    xy=(c.x, c.y), xytext=(c.x + ox_, c.y + oy_),
                    fontproperties=SANS_B, fontsize=12.5, color=INK,
                    ha='center', zorder=6,
                    arrowprops=dict(arrowstyle='-', color='#8b857a', lw=0.8))
        ax.text(c.x + ox_, c.y + oy_ - 0.075, f'F. {frente}', ha='center',
                va='top', fontproperties=SANS, fontsize=10, color=col, zorder=6)

    # recortar al área de las zonas (puntos + municipios), no todo el depto
    xs_all = [p['lon'] for p in pts]
    ys_all = [p['lat'] for p in pts]
    sub_all = g[g['ME'].isin(list(zmuns.keys()))]
    minx, miny, maxx, maxy = sub_all.total_bounds
    minx = min(minx, min(xs_all)); maxx = max(maxx, max(xs_all))
    miny = min(miny, min(ys_all)); maxy = max(maxy, max(ys_all))
    mx = (maxx - minx) * 0.10 + 0.05
    my = (maxy - miny) * 0.10 + 0.05
    ax.set_xlim(minx - mx, maxx + mx)
    ax.set_ylim(miny - my, maxy + my)
    ax.set_aspect('equal')
    ax.axis('off')

    # leyenda
    fig.patches.append(Rectangle((0.04, 0.052), 0.020, 0.026, transform=fig.transFigure,
                                 facecolor=OX, edgecolor='none', clip_on=False))
    fig.text(0.066, 0.065, 'Hecho fechado (grupo + Defensoría + prensa)',
             fontproperties=SANS, fontsize=11.5, va='center')
    fig.patches.append(Rectangle((0.04, 0.020), 0.020, 0.026, transform=fig.transFigure,
                                 facecolor=AMBER, edgecolor='none', clip_on=False))
    fig.text(0.066, 0.033, 'Presencia armada + alerta + prensa estructural',
             fontproperties=SANS, fontsize=11.5, va='center')
    fig.text(0.97, 0.022, f'{len(pts)} puestos-tijera · EMC línea ‘Mordisco’.   ricardoruiz.co',
             fontproperties=SANS, fontsize=10, color='#6b655c', ha='right')
    fig.savefig(os.path.join(OUT, fname), facecolor=PAPER)
    plt.close(fig)
    print('OK', fname, '·', len(pts), 'puestos')


# =====================================================================
# (d) tabla 10 zonas — partida en 2, con el HECHO visible
# =====================================================================
TABLA = [
    # nombre, depto, frente, tipo, mesas100, tijeras, hecho
    ('Tumaco', 'Nariño', 'Oliver Sinisterra / CN-EB', 'full', 112, 9,
     '“Gobernanza criminal” que veta candidaturas (Defensoría AT 013-25); minas 11-may; líder Awá asesinado 14-jun.'),
    ('Policarpa', 'Nariño', 'Franco Benavides (EMC)', 'full', 9, 6,
     'Masacre en La Vega (5-mar) + audio disidente exigiendo certificado electoral para moverse (31-may).'),
    ('Argelia', 'Cauca', 'Carlos Patiño (EMC)', 'full', 7, 6,
     'Combates y desplazamiento en El Plateado (9–12 abr); cabecera bajo presión del frente.'),
    ('Patía', 'Cauca', 'Carlos Patiño (EMC)', 'full', 4, 6,
     'Atentado en la vía Panamericana (25-abr); homicidio de líder social (22-abr).'),
    ('El Tambo', 'Cauca', 'Carlos Patiño (EMC)', 'full', 8, 5,
     'Sometimiento de corregimientos y control de movilidad rural (abr 2026).'),
    ('Mercaderes', 'Cauca', 'Carlos Patiño (EMC)', 'full', 4, 3,
     'Atentado en la Panamericana (25-abr); asesinato del líder Faiver Cerón y su familia (18-feb).'),
    ('Bolívar', 'Cauca', 'Carlos Patiño + ELN', 'parcial', 24, 18,
     'Cinturón de líderes asesinados del sur del Cauca; disputa Carlos Patiño–ELN (presencia estructural).'),
    ('Leiva', 'Nariño', 'Franco Benavides (EMC)', 'parcial', 6, 8,
     'Control disidente de la cordillera nariñense; corredor cocalero (presencia estructural).'),
    ('Cumbitara', 'Nariño', 'Franco Benavides (EMC)', 'parcial', 12, 3,
     'Combates y expulsiones atribuidas a la disidencia en el río Patía (inicio 2026).'),
    ('Almaguer', 'Cauca', 'Carlos Patiño (EMC)', 'parcial', 11, 2,
     'Cinturón de violencia del Macizo / sur del Cauca (presencia estructural).'),
]


def _wrap(txt, n):
    words = txt.split()
    lines, cur = [], ''
    for w in words:
        if len(cur) + len(w) + 1 <= n:
            cur = (cur + ' ' + w).strip()
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def build_tabla(rows, fname, part_label):
    n = len(rows)
    rowh = 1.0
    fig = plt.figure(figsize=(11.5, 1.9 + n * 1.18), dpi=120)
    fig.patch.set_facecolor(PAPER)
    H = fig.get_size_inches()[1]
    kicker(fig, y=1 - 0.55 / H)
    fig.text(0.03, 1 - 1.15 / H, 'Las 10 zonas, una por una', fontproperties=ARIMA_B,
             fontsize=30, color=INK, va='top')
    for i, ln in enumerate(_wrap(part_label, 88)):
        fig.text(0.03, 1 - (1.78 + i * 0.40) / H, ln, fontproperties=SANS,
                 fontsize=13, color='#33302a', va='top')

    ax = fig.add_axes([0.0, 0.075, 1.0, 1 - 2.95 / H - 0.075])
    ax.set_xlim(0, 100); ax.set_ylim(0, n * 3 + 0.5)
    ax.axis('off')

    y = n * 3 - 0.3
    for (nombre, depto, frente, tipo, m100, tj, hecho) in rows:
        col = OX if tipo == 'full' else AMBER
        # franja de color a la izquierda
        ax.add_patch(Rectangle((2.5, y - 2.4), 0.7, 2.5, facecolor=col, edgecolor='none'))
        # nombre + depto (mide el ancho real del nombre para no encimar)
        tn = ax.text(4.5, y, nombre, fontproperties=SANS_B, fontsize=18, color=INK, va='top')
        fig.canvas.draw()
        bb = tn.get_window_extent(renderer=fig.canvas.get_renderer())
        x_right = ax.transData.inverted().transform((bb.x1, bb.y0))[0]
        ax.text(x_right + 1.6, y - 0.10, f'({depto})', fontproperties=SANS,
                fontsize=12.5, color=MUTE, va='top')
        # frente
        ax.text(4.5, y - 0.95, f'F. {frente}', fontproperties=SANS_B, fontsize=12.5,
                color=col, va='top')
        # hecho (wrap)
        wl = _wrap(hecho, 74)
        for i, ln in enumerate(wl):
            ax.text(4.5, y - 1.55 - i * 0.52, ln, fontproperties=SANS, fontsize=11.5,
                    color='#33302a', va='top')
        # métricas a la derecha
        tag = 'full' if tipo == 'full' else 'parcial'
        ax.text(98, y, f'{m100} mesas 100%', fontproperties=SANS_B, fontsize=13.5,
                color=INK, va='top', ha='right')
        ax.text(98, y - 0.62, f'{tj} tijeras', fontproperties=SANS_B, fontsize=13.5,
                color=col, va='top', ha='right')
        # separador
        ax.plot([2.5, 98], [y - 2.65, y - 2.65], color=GRID, lw=0.8)
        y -= 3.0

    footer(fig, 'Rojo = 3 fuentes coinciden (grupo armado + Defensoría + prensa con hecho fechado) · '
                'ámbar = presencia + alerta + prensa estructural.\n'
                'Tijera = puesto rural (zona 99): Cepeda ≥95% y el rival cae ≥10 votos de 1V a 2V.   '
                'Ricardo Ruiz · ricardoruiz.co',
           y=0.040, size=9.5)
    fig.savefig(os.path.join(OUT, fname), facecolor=PAPER)
    plt.close(fig)
    print('OK', fname)


# =====================================================================
# caso puntual: Llorente (Tumaco) — anatomía de una tijera
# =====================================================================
def build_caso_llorente():
    # datos reales del puesto 231399959 (master_unificado_puesto.json)
    cep1, abe1, urna1 = 1816, 219, 2214
    cep2, abe2, urna2 = 3678, 101, 3895
    fig = plt.figure(figsize=(10.6, 9.4), dpi=120)
    fig.patch.set_facecolor(PAPER)
    kicker(fig)
    title(fig, 'Anatomía de una “tijera”: Llorente', size=31)
    subtitle_lines(fig, [
        'Un solo puesto rural —Llorente, corregimiento de Tumaco (Nariño)—,',
        'georreferenciado. Entre 1ª y 2ª vuelta llegaron 1.681 votantes más…',
        'y los votos de Abelardo se cayeron a menos de la mitad.',
    ], y=0.825, size=14.5, dy=0.028)

    # takeaway destacado debajo del subtítulo
    fig.text(0.03, 0.665, 'Cepeda 89% → 97% (cara a cara)   ·   Abelardo 219 → 101 votos',
             fontproperties=SANS_B, fontsize=15, color=OX, va='top')

    ax = fig.add_axes([0.08, 0.165, 0.88, 0.45])
    ax.set_facecolor(PAPER)
    groups = [('1ª vuelta', cep1, abe1, urna1), ('2ª vuelta', cep2, abe2, urna2)]
    xc = [0.20, 1.20]
    bw = 0.26
    for i, (lab, c, a, u) in enumerate(groups):
        x = xc[i]
        ax.bar(x - bw / 2, c, bw, color=CEP, zorder=3)
        ax.bar(x + bw / 2, a, bw, color=ABE, zorder=3)
        ax.text(x - bw / 2, c + 70, f'{c:,}'.replace(',', '.'), ha='center',
                va='bottom', color=CEP, fontproperties=SANS_B, fontsize=15)
        ax.text(x + bw / 2, a + 70, f'{a:,}'.replace(',', '.'), ha='center',
                va='bottom', color=ABE, fontproperties=SANS_B, fontsize=15)
        ax.text(x, -210, lab, ha='center', va='top', fontproperties=SANS_B, fontsize=15)

    # arco de turnout
    ax.annotate('', xy=(1.0, 4150), xytext=(0.4, 4150),
                arrowprops=dict(arrowstyle='-|>', color='#6b655c', lw=1.8))
    ax.text(0.70, 4270, '+1.681 votantes', ha='center', va='bottom',
            color='#4a443c', fontproperties=SANS_B, fontsize=14)

    ax.set_xlim(-0.15, 1.62)
    ax.set_ylim(0, 4600)
    ax.axis('off')
    # leyenda candidatos (sólo izquierda, separada de las etiquetas de eje)
    fig.patches.append(Rectangle((0.08, 0.072), 0.020, 0.028, transform=fig.transFigure,
                                 facecolor=CEP, edgecolor='none', clip_on=False))
    fig.text(0.112, 0.086, 'Cepeda', fontproperties=SANS, fontsize=13.5, va='center')
    fig.patches.append(Rectangle((0.27, 0.072), 0.020, 0.028, transform=fig.transFigure,
                                 facecolor=ABE, edgecolor='none', clip_on=False))
    fig.text(0.302, 0.086, 'Abelardo', fontproperties=SANS, fontsize=13.5, va='center')

    footer(fig, 'Puesto 23-139-99-59 (LLORENTE, corregimiento de Tumaco), zona 99 rural · 14 mesas · censo ~4.750.\n'
                'Frente Oliver Sinisterra / CN-EB.   Fuente: preconteo 1V/2V 2026.   Ricardo Ruiz · ricardoruiz.co',
           y=0.040, size=9.3)
    fig.savefig(os.path.join(OUT, 'caso-llorente.png'), facecolor=PAPER)
    plt.close(fig)
    print('OK caso-llorente.png')


if __name__ == '__main__':
    build_caso_llorente()
    build_inversion()
    build_participacion()
    # mapas a nivel puesto, partidos por depto
    build_mapa('11', 'mapa-tijeras-cauca.png',
               'Cauca: 6 zonas, puesto por puesto',
               {'005': (-0.30, 0.18), '058': (0.28, 0.10), '025': (-0.32, 0.10),
                '046': (0.10, -0.22), '007': (0.30, 0.16), '004': (0.28, -0.18)})
    build_mapa('23', 'mapa-tijeras-narino.png',
               'Nariño: 4 zonas, puesto por puesto',
               {'139': (0.18, -0.30), '098': (0.34, 0.14), '080': (0.30, 0.12),
                '039': (-0.30, 0.14)})
    # tabla partida
    build_tabla(TABLA[:5], 'tabla-10-zonas-1.png',
                'Votación irregular de la “tijera” (1V→2V). Las 6 zonas FULL: grupo armado + Defensoría + prensa con hecho fechado.')
    build_tabla(TABLA[5:], 'tabla-10-zonas-2.png',
                'Las 4 zonas PARCIAL (presencia + alerta + prensa estructural) — y el cierre de las 6 FULL.')
    print('\nlisto.')
