#!/usr/bin/env python3
"""Carrusel Instagram 6 slides · 1080×1350 (4:5).

Mensaje: "La ley seca del viernes en Bogotá no tiene sustento técnico".

NO usa Syne. Fondo paper claro #f4f3ef. Tipografía: Helvetica Neue, gruesa
y grande, lectura desde el feed.
"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import rcParams

# Instagram 4:5 — 1080×1350
DPI = 100
W = 10.80
H = 13.50

PAPER = '#f4f3ef'      # crema
INK = '#1a1a2e'        # casi negro azulado
BLUE = '#0047FF'       # azul del sitio
RED = '#c8312c'        # oxblood para destacar negativos
GRAY = '#6a6a72'       # gray secundario
GRAY_DIM = '#aaaaaa'

# Helvetica Neue como display sin Syne
rcParams['font.family'] = ['Helvetica Neue', 'Helvetica', 'Arial', 'DejaVu Sans']
rcParams['axes.spines.top'] = False
rcParams['axes.spines.right'] = False
rcParams['axes.spines.bottom'] = False
rcParams['axes.spines.left'] = False


def base_fig():
    fig, ax = plt.subplots(figsize=(W, H), dpi=DPI)
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    return fig, ax


def kicker(ax, text, color=BLUE, y=0.945):
    ax.text(0.07, y, text, fontsize=22, color=color, fontweight='bold',
            ha='left', va='top', family='Helvetica Neue',
            transform=ax.transAxes)


def page_num(ax, n, total=6):
    ax.text(0.93, 0.945, f'{n}/{total}', fontsize=20, color=GRAY,
            ha='right', va='top', family='Helvetica Neue',
            transform=ax.transAxes)


def brand_footer(ax, msg='ricardoruiz.co'):
    # Línea fina arriba del footer
    ax.plot([0.07, 0.93], [0.075, 0.075], color=INK, linewidth=1.0,
            transform=ax.transAxes, clip_on=False, alpha=0.5)
    ax.text(0.07, 0.055, msg, fontsize=20, color=INK, fontweight='bold',
            ha='left', va='top', family='Helvetica Neue',
            transform=ax.transAxes)
    ax.text(0.93, 0.055, 'Datos: DIJIN · Policía Nacional', fontsize=15,
            color=GRAY, ha='right', va='top', family='Helvetica Neue',
            transform=ax.transAxes)


def save(fig, n):
    fn = f'carrusel-{n:02d}.png'
    fig.savefig(fn, dpi=DPI, facecolor=PAPER, bbox_inches=None,
                pad_inches=0)
    plt.close(fig)
    print(f'· {fn}')


# ───────────────────────────────────────────────────────────────────
# SLIDE 1 — HOOK
# ───────────────────────────────────────────────────────────────────
def slide_1():
    fig, ax = base_fig()
    kicker(ax, 'ANÁLISIS · BOGOTÁ · 29 MAY 2026')
    page_num(ax, 1)

    # Título grande, 4 líneas
    ax.text(0.07, 0.83, 'La ley seca\ndel viernes\nen Bogotá', fontsize=92,
            fontweight='bold', color=INK, ha='left', va='top',
            family='Helvetica Neue', linespacing=0.98,
            transform=ax.transAxes)

    # Bloque destacado abajo del título
    ax.add_patch(patches.Rectangle((0.07, 0.20), 0.86, 0.18,
                                   facecolor=INK, edgecolor='none',
                                   transform=ax.transAxes))
    ax.text(0.5, 0.29, 'no tiene sustento técnico', fontsize=40,
            fontweight='bold', color=PAPER, ha='center', va='center',
            family='Helvetica Neue', transform=ax.transAxes)

    # Hint
    ax.text(0.07, 0.165, 'Lo que muestran 4 elecciones presidenciales\nen las cifras de la Policía',
            fontsize=24, color=GRAY, ha='left', va='top',
            family='Helvetica Neue', linespacing=1.35,
            transform=ax.transAxes)

    brand_footer(ax)
    save(fig, 1)


# ───────────────────────────────────────────────────────────────────
# SLIDE 2 — PRIMERA VEZ
# ───────────────────────────────────────────────────────────────────
def slide_2():
    fig, ax = base_fig()
    kicker(ax, 'LO QUE CAMBIÓ')
    page_num(ax, 2)

    ax.text(0.07, 0.86, 'Por primera vez,', fontsize=38,
            color=GRAY, ha='left', va='top', family='Helvetica Neue',
            transform=ax.transAxes)

    ax.text(0.07, 0.78, 'Bogotá adelanta\nla ley seca\nal VIERNES.', fontsize=78,
            fontweight='bold', color=INK, ha='left', va='top',
            family='Helvetica Neue', linespacing=0.98,
            transform=ax.transAxes)

    # Comparación visual
    box_y = 0.32
    box_h = 0.16
    # ANTES (3 elecciones)
    ax.add_patch(patches.Rectangle((0.07, box_y), 0.40, box_h,
                                   facecolor='none', edgecolor=GRAY,
                                   linewidth=2, transform=ax.transAxes))
    ax.text(0.27, box_y + box_h - 0.025, 'ANTES', fontsize=16,
            color=GRAY, ha='center', va='top', fontweight='bold',
            family='Helvetica Neue', transform=ax.transAxes)
    ax.text(0.27, box_y + box_h/2 - 0.005, 'Sábado', fontsize=42,
            fontweight='bold', color=INK, ha='center', va='center',
            family='Helvetica Neue', transform=ax.transAxes)
    ax.text(0.27, box_y + 0.03, '6:00 p.m.', fontsize=20, color=GRAY,
            ha='center', va='center', family='Helvetica Neue',
            transform=ax.transAxes)

    # AHORA
    ax.add_patch(patches.Rectangle((0.53, box_y), 0.40, box_h,
                                   facecolor=BLUE, edgecolor='none',
                                   transform=ax.transAxes))
    ax.text(0.73, box_y + box_h - 0.025, 'AHORA · 2026', fontsize=16,
            color=PAPER, ha='center', va='top', fontweight='bold',
            family='Helvetica Neue', transform=ax.transAxes)
    ax.text(0.73, box_y + box_h/2 - 0.005, 'Viernes', fontsize=42,
            fontweight='bold', color=PAPER, ha='center', va='center',
            family='Helvetica Neue', transform=ax.transAxes)
    ax.text(0.73, box_y + 0.03, '6:00 p.m.', fontsize=20, color=PAPER,
            ha='center', va='center', family='Helvetica Neue',
            transform=ax.transAxes, alpha=0.85)

    # Caption inferior
    ax.text(0.07, 0.22, 'Decreto Distrital 191 · 28 de mayo de 2026',
            fontsize=20, color=INK, ha='left', va='top',
            fontweight='bold', family='Helvetica Neue',
            transform=ax.transAxes)
    ax.text(0.07, 0.18, '2018 (Peñalosa), 2022 primera vuelta y 2022\nsegunda vuelta (Claudia López) arrancaron sábado.',
            fontsize=18, color=GRAY, ha='left', va='top',
            family='Helvetica Neue', linespacing=1.4,
            transform=ax.transAxes)

    brand_footer(ax)
    save(fig, 2)


# ───────────────────────────────────────────────────────────────────
# SLIDE 3 — EL DEBATE SIN CIFRAS
# ───────────────────────────────────────────────────────────────────
def slide_3():
    fig, ax = base_fig()
    kicker(ax, 'LO EXTRAÑO DEL DEBATE')
    page_num(ax, 3)

    ax.text(0.07, 0.88, 'Nadie\npresentó\ncifras.', fontsize=80,
            fontweight='bold', color=INK, ha='left', va='top',
            family='Helvetica Neue', linespacing=0.98,
            transform=ax.transAxes)

    ax.text(0.07, 0.57, 'Ni la Alcaldía. Ni los gremios. Ni la oposición.',
            fontsize=22, color=GRAY, ha='left', va='top',
            family='Helvetica Neue', transform=ax.transAxes)

    # Lista de actores con más respiración
    actores = [
        ('Alcaldía Galán', 'Argumento preventivo.'),
        ('Asobares · Bares Unidos', 'Impacto al sector nocturno.'),
        ('Heidy Sánchez (UP)', '"Desproporcionada e inconsulta".'),
        ('Angélica Lozano (Verde)', '"Nunca ha incluido el viernes".'),
    ]
    y0 = 0.49
    dy = 0.07
    for i, (nombre, frase) in enumerate(actores):
        y = y0 - i * dy
        ax.add_patch(patches.Rectangle((0.07, y - 0.013), 0.012, 0.022,
                                        facecolor=RED, edgecolor='none',
                                        transform=ax.transAxes))
        ax.text(0.10, y, f'{nombre}.', fontsize=22, color=INK,
                fontweight='bold', ha='left', va='center',
                family='Helvetica Neue', transform=ax.transAxes)
        ax.text(0.10, y - 0.025, frase, fontsize=19, color=GRAY,
                ha='left', va='center', family='Helvetica Neue',
                transform=ax.transAxes)

    # Conclusión chip
    ax.text(0.07, 0.155, 'Todos con equipos técnicos detrás.\nCero datos sobre el viernes pre-electoral.',
            fontsize=21, color=INK, ha='left', va='top',
            fontweight='bold', family='Helvetica Neue', linespacing=1.35,
            transform=ax.transAxes)

    brand_footer(ax)
    save(fig, 3)


# ───────────────────────────────────────────────────────────────────
# SLIDE 4 — LA PREGUNTA
# ───────────────────────────────────────────────────────────────────
def slide_4():
    fig, ax = base_fig()
    kicker(ax, 'LA PREGUNTA BÁSICA')
    page_num(ax, 4)

    ax.text(0.07, 0.85, '¿El viernes\npre-electoral\nen Bogotá ha\nsido más\nviolento que\nun viernes\nnormal?', fontsize=64,
            fontweight='bold', color=INK, ha='left', va='top',
            family='Helvetica Neue', linespacing=0.98,
            transform=ax.transAxes)

    # Sub: lo que hicimos
    ax.add_patch(patches.Rectangle((0.07, 0.13), 0.86, 0.10,
                                   facecolor=BLUE, edgecolor='none',
                                   transform=ax.transAxes))
    ax.text(0.5, 0.21, 'Cruzamos DIJIN — Policía Nacional', fontsize=24,
            color=PAPER, ha='center', va='top', fontweight='bold',
            family='Helvetica Neue', transform=ax.transAxes)
    ax.text(0.5, 0.165, '4 elecciones presidenciales · 2010 · 2014 · 2018 · 2022',
            fontsize=20, color=PAPER, ha='center', va='center',
            family='Helvetica Neue', transform=ax.transAxes, alpha=0.92)

    brand_footer(ax)
    save(fig, 4)


# ───────────────────────────────────────────────────────────────────
# SLIDE 5 — EL DATO (gráfica de barras inline)
# ───────────────────────────────────────────────────────────────────
def slide_5():
    fig, ax = base_fig()
    kicker(ax, 'EL DATO')
    page_num(ax, 5)

    # Sub-titular arriba
    ax.text(0.07, 0.86, 'Viernes pre-electoral\nen Bogotá vs un\nviernes promedio:',
            fontsize=36, color=INK, ha='left', va='top',
            family='Helvetica Neue', linespacing=1.05,
            transform=ax.transAxes)

    # Cifra gigante centrada
    ax.text(0.5, 0.50, '−6,7%', fontsize=180, fontweight='bold',
            color=BLUE, ha='center', va='center',
            family='Helvetica Neue', transform=ax.transAxes)

    # Chip bajo la cifra
    ax.add_patch(patches.Rectangle((0.18, 0.305), 0.64, 0.05,
                                   facecolor=INK, edgecolor='none',
                                   transform=ax.transAxes))
    ax.text(0.5, 0.33, 'DENTRO DEL RUIDO ESTADÍSTICO',
            fontsize=20, fontweight='bold', color=PAPER,
            ha='center', va='center', family='Helvetica Neue',
            transform=ax.transAxes)

    # Explicación
    ax.text(0.07, 0.255,
            '158 lesiones observadas vs 169 esperadas.',
            fontsize=24, color=INK, fontweight='bold',
            ha='left', va='top', family='Helvetica Neue',
            transform=ax.transAxes)
    ax.text(0.07, 0.215,
            'Suma de los 4 viernes pre-electorales\n2010 · 2014 · 2018 · 2022 en Bogotá.',
            fontsize=20, color=GRAY, ha='left', va='top',
            family='Helvetica Neue', linespacing=1.35,
            transform=ax.transAxes)

    # Comparativo con el domingo
    ax.text(0.07, 0.135,
            'Para referencia: el DOMINGO cae −46 %\n(día electoral + ley seca · efectos no separables).',
            fontsize=18, color=GRAY, ha='left', va='top',
            family='Helvetica Neue', linespacing=1.35,
            transform=ax.transAxes)

    brand_footer(ax)
    save(fig, 5)


# ───────────────────────────────────────────────────────────────────
# SLIDE 6 — CIERRE + CTA
# ───────────────────────────────────────────────────────────────────
def slide_6():
    fig, ax = base_fig()
    kicker(ax, 'CONCLUSIÓN')
    page_num(ax, 6)

    ax.text(0.07, 0.88, 'El descenso\ngrande es el\ndomingo.', fontsize=58,
            fontweight='bold', color=INK, ha='left', va='top',
            family='Helvetica Neue', linespacing=0.98,
            transform=ax.transAxes)

    ax.text(0.07, 0.66, 'Y ese descenso no se explica\nsolo por la ley seca:',
            fontsize=22, color=GRAY, ha='left', va='top',
            family='Helvetica Neue', linespacing=1.35,
            transform=ax.transAxes)

    confs = [
        'ley seca activa',
        'jornada electoral · gente votando',
        'transporte restringido',
        'fuerza pública desplegada',
    ]
    y0 = 0.555
    for i, c in enumerate(confs):
        y = y0 - i * 0.042
        ax.add_patch(patches.Rectangle((0.07, y - 0.013), 0.012, 0.022,
                                        facecolor=BLUE, edgecolor='none',
                                        transform=ax.transAxes))
        ax.text(0.10, y, c, fontsize=21, color=INK,
                ha='left', va='center', family='Helvetica Neue',
                transform=ax.transAxes)

    # Conclusión fuerte en bloque
    ax.add_patch(patches.Rectangle((0.07, 0.175), 0.86, 0.19,
                                   facecolor=INK, edgecolor='none',
                                   transform=ax.transAxes))
    ax.text(0.5, 0.335, 'Si la decisión es preventiva,', fontsize=21,
            color=PAPER, ha='center', va='center',
            family='Helvetica Neue', transform=ax.transAxes, alpha=0.85)
    ax.text(0.5, 0.275, 'vale la pena decirlo así.', fontsize=32,
            fontweight='bold', color=PAPER, ha='center', va='center',
            family='Helvetica Neue', transform=ax.transAxes)
    ax.text(0.5, 0.21, 'El histórico no la respalda.', fontsize=21,
            color=PAPER, ha='center', va='center',
            family='Helvetica Neue', transform=ax.transAxes, alpha=0.85)

    # CTA al sitio
    ax.text(0.5, 0.135, 'Análisis completo:', fontsize=18, color=GRAY,
            ha='center', va='center', family='Helvetica Neue',
            transform=ax.transAxes)
    ax.text(0.5, 0.105, 'ricardoruiz.co/analisis-leyseca', fontsize=22,
            fontweight='bold', color=BLUE, ha='center', va='center',
            family='Helvetica Neue', transform=ax.transAxes)

    brand_footer(ax)
    save(fig, 6)


if __name__ == '__main__':
    slide_1()
    slide_2()
    slide_3()
    slide_4()
    slide_5()
    slide_6()
