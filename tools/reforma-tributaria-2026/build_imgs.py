#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gráficos del artículo LinkedIn sobre la reforma tributaria radicada el 20-jul-2026.
Identidad: sistema visual v2 (fondo #060810 + Helvetica Neue, sin modo claro).
Salidas → rrss/linkedin/reforma-tributaria-{1-fuentes,2-coalicion-2022,3-reloj}.png

Datos:
  1-fuentes   : Tabla 1 de la exposición de motivos del PL (MHCP, 20-jul-2026).
  2-coalicion : dist/votaciones-camara-nominal.jsonl (PL 118/2022C, plenaria 2-nov-2022,
                votación de bloque de artículos v17 — la de mayor participación, 134 votos).
  3-reloj     : dist/stats.json → mortandad_por_anio_cuatrienio (Caudal, 1990-2026).
"""
import json, collections, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = '/Users/ricardoruiz/ricardoruiz.co'
DIST = f'{ROOT}/Bases de datos/leyes-senado/dist'
OUT  = f'{ROOT}/rrss/linkedin'

# ---------- identidad v2 ----------
BG     = '#060810'
CARD   = '#0d0f18'
INK    = '#f4f3ef'
MUTED  = '#8b8f9c'
BLUE   = '#3d6fff'
BLUE2  = '#0047FF'
ORANGE = '#f97316'
GREEN  = '#4ade80'
GRID   = '#1d2030'

for fam in ('Helvetica Neue', 'Helvetica'):
    try:
        font_manager.findfont(fam, fallback_to_default=False)
        FONT = fam
        break
    except Exception:
        FONT = 'Arial'
plt.rcParams.update({
    'font.family': FONT,
    'text.color': INK, 'axes.edgecolor': GRID,
    'axes.labelcolor': INK, 'xtick.color': MUTED, 'ytick.color': MUTED,
    'figure.facecolor': BG, 'axes.facecolor': BG, 'savefig.facecolor': BG,
})

W, H, DPI = 1200, 675, 2  # 2400×1350 reales


def _frame(fig, title, kicker, foot):
    fig.text(0.045, 0.955, kicker.upper(), fontsize=10.5, color=ORANGE,
             fontweight='bold', va='top')
    fig.text(0.045, 0.915, title, fontsize=19, color=INK, fontweight='bold', va='top')
    fig.text(0.045, 0.045, foot, fontsize=8.2, color=MUTED, va='bottom')
    fig.text(0.955, 0.045, 'ricardoruiz.co · Caudal', fontsize=9, color=INK,
             fontweight='bold', va='bottom', ha='right')


# ================================================================
# 1 · ¿De dónde salen los $21,9 billones?
# ================================================================
def fuentes():
    rows = [
        ('Empresas vuelven a pagar salud,\nSENA e ICBF (salarios 3–10 mín.)', 8.5, ORANGE,
         '39% del total — la fuente más grande'),
        ('IVA y gasto tributario\n(gasolina, apuestas, Temu, híbridos…)', 6.7, BLUE, ''),
        ('Renta, patrimonio y sobretasas\n(personas de altos ingresos, bancos)', 3.4, BLUE, ''),
        ('Impuestos verdes y saludables\n(carbono, licores, tabaco, petróleo)', 3.2, BLUE, ''),
    ]
    fig, ax = plt.subplots(figsize=(W/100, H/100), dpi=DPI*100//2)
    fig.subplots_adjust(left=0.34, right=0.90, top=0.80, bottom=0.13)
    labels = [r[0] for r in rows][::-1]
    vals   = [r[1] for r in rows][::-1]
    cols   = [r[2] for r in rows][::-1]
    bars = ax.barh(labels, vals, color=cols, height=0.62, zorder=3)
    for b, v in zip(bars, vals):
        ax.text(b.get_width()+0.12, b.get_y()+b.get_height()/2,
                f'${v:,.1f} bn'.replace('.', ','), va='center', fontsize=12.5,
                color=INK, fontweight='bold')
    ax.text(8.5, 3 + 0.52, '39% de toda la reforma', fontsize=10.5, color=ORANGE,
            ha='right', fontweight='bold')
    ax.set_xlim(0, 10.4)
    ax.xaxis.set_visible(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(axis='y', labelsize=11, length=0)
    _frame(fig,
           'La medida que casi no ha sonado es la más grande de la reforma',
           'Recaudo estimado 2027 · $21,9 billones en total',
           'Fuente: Tabla 1 de la exposición de motivos del PL de reforma tributaria '
           '(MinHacienda · DIAN, radicado 20-jul-2026). Cifras en billones de pesos de 2027, por título del proyecto.')
    fig.savefig(f'{OUT}/reforma-tributaria-1-fuentes.png')
    plt.close(fig)
    print('✓ 1-fuentes')


# ================================================================
# 2 · La coalición que ya no existe (voto nominal 2-nov-2022)
# ================================================================
def _party(p):
    p = (p or '').upper()
    if 'LIBERAL' in p: return 'Liberal'
    if 'CONSERVADOR' in p: return 'Conservador'
    if 'PACTO' in p: return 'Pacto Histórico'
    if 'ALIANZA VERDE' in p: return 'Alianza Verde'
    if 'UNIÓN POR LA GENTE' in p or 'PARTIDO DE LA U' in p: return 'La U'
    if 'CAMBIO RADICAL' in p: return 'Cambio Radical'
    if 'CENTRO DEMOCRÁTICO' in p: return 'Centro Democrático'
    return 'Otros (étnicos, CITREP, coaliciones)'


def coalicion():
    agg = collections.defaultdict(collections.Counter)
    with open(f'{DIST}/votaciones-camara-nominal.jsonl') as f:
        for line in f:
            v = json.loads(line)
            if (v.get('proyecto_numero_camara') or '').replace(' ', '') != '118/22':
                continue
            if v['fecha'] != '2022-11-02' or v['votacion_numero'] != 17:
                continue
            r = v['respuesta']
            if r in ('Sí', 'Si'):
                agg[_party(v.get('partido'))]['si'] += 1
            elif r == 'No':
                agg[_party(v.get('partido'))]['no'] += 1
    order = sorted(agg, key=lambda p: agg[p]['si'] - agg[p]['no'], reverse=True)
    si = [agg[p]['si'] for p in order]
    no = [agg[p]['no'] for p in order]

    fig, ax = plt.subplots(figsize=(W/100, H/100), dpi=DPI*100//2)
    fig.subplots_adjust(left=0.26, right=0.94, top=0.78, bottom=0.13)
    y = range(len(order))[::-1]
    ax.barh(y, si, color=BLUE, height=0.6, label='Sí', zorder=3)
    ax.barh(y, [-n for n in no], color=ORANGE, height=0.6, label='No', zorder=3)
    ax.axvline(0, color=INK, lw=0.8)
    for yi, s, n in zip(y, si, no):
        if s: ax.text(s+0.5, yi, str(s), va='center', fontsize=11.5, color=BLUE, fontweight='bold')
        if n: ax.text(-n-0.5, yi, str(n), va='center', ha='right', fontsize=11.5,
                      color=ORANGE, fontweight='bold')
    ax.set_yticks(list(y))
    ax.set_yticklabels(order, fontsize=11)
    ax.set_xlim(-16, 26)
    ax.xaxis.set_visible(False)
    for s_ in ax.spines.values():
        s_.set_visible(False)
    ax.tick_params(axis='y', length=0)
    ax.legend(loc='lower right', frameon=False, fontsize=10.5,
              labelcolor=INK, ncols=2)
    _frame(fig,
           'La tributaria de 2022 la aprobó una coalición que ya no existe',
           'Voto nominal · plenaria de la Cámara · 2-nov-2022',
           'Votación de bloque de artículos del PL 118/2022C (la de mayor participación: 134 votos). '
           'Liberales y conservadores votaron en bloque por el Sí; solo Centro Democrático y Cambio Radical en contra.\n'
           'Fuente: actas de votación electrónica de la Secretaría General de la Cámara, procesadas en Caudal.')
    fig.savefig(f'{OUT}/reforma-tributaria-2-coalicion-2022.png')
    plt.close(fig)
    print('✓ 2-coalicion-2022', dict(agg))


# ================================================================
# 3 · El reloj legislativo: año de cuatrienio
# ================================================================
def reloj():
    st = json.load(open(f'{DIST}/stats.json'))
    m = st['mortandad_por_anio_cuatrienio']
    anios = ['1', '2', '3', '4']
    muere = [m[a]['pct_muerte_tiempo'] for a in anios]
    ley   = [m[a]['pct_ley'] for a in anios]

    fig, ax = plt.subplots(figsize=(W/100, H/100), dpi=DPI*100//2)
    fig.subplots_adjust(left=0.07, right=0.70, top=0.78, bottom=0.16)
    x = range(4)
    bw = 0.38
    b1 = ax.bar([i-bw/2 for i in x], muere, bw, color=ORANGE, zorder=3,
                label='Muere por vencimiento de términos')
    b2 = ax.bar([i+bw/2 for i in x], ley, bw, color=BLUE, zorder=3,
                label='Termina en ley')
    for bars in (b1, b2):
        for b in bars:
            ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.6,
                    f'{b.get_height():.0f}%', ha='center', fontsize=11.5,
                    color=INK, fontweight='bold')
    ax.set_xticks(list(x))
    ax.set_xticklabels([f'Año {a}' for a in anios], fontsize=12)
    ax.set_ylim(0, 42)
    ax.yaxis.set_visible(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    ax.legend(loc='upper left', frameon=False, fontsize=10, labelcolor=INK)

    # panel lateral: esta reforma ni siquiera es año 4
    fig.text(0.735, 0.66, 'Y esta reforma ni\nsiquiera es "año 4":', fontsize=13,
             color=INK, fontweight='bold', va='top')
    fig.text(0.735, 0.53,
             'se radicó el 20-jul-2026,\na 18 días del cambio\nde gobierno.\n\n'
             'En 36 años de registro\nno hay otra tributaria\nradicada por un\n'
             'gobierno saliente.', fontsize=11, color=MUTED, va='top', linespacing=1.45)
    _frame(fig,
           'El último año del cuatrienio es un cementerio de proyectos',
           'Todos los proyectos de ley radicados 1990-2026, por año de cuatrienio',
           'Porcentaje de proyectos según resultado final, sobre 9.919 proyectos de ley del registro histórico '
           'de leyes.senado.gov.co (los demás resultados —archivado en votación, retiro, en trámite— completan el 100%).\n'
           'Fuente: Caudal · ricardoruiz.co.')
    fig.savefig(f'{OUT}/reforma-tributaria-3-reloj.png')
    plt.close(fig)
    print('✓ 3-reloj')


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    fuentes()
    coalicion()
    reloj()
