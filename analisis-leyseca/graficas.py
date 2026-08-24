#!/usr/bin/env python3
"""Genera 2 PNG por tema (light + dark) para Twitter y para la web."""

import json
import matplotlib.pyplot as plt
from matplotlib import rcParams

with open('reporte.json', encoding='utf-8') as f:
    rep = json.load(f)


THEMES = {
    'light': {
        'bg':     '#f4f3ef',
        'fg':     '#1a1a2e',
        'blue':   '#0047FF',
        'gray':   '#888888',
        'orange': '#c8312c',
        'grid':   '#dcdad4',
        'bar_base_alpha': 0.65,
    },
    'dark': {
        'bg':     '#060810',
        'fg':     '#f4f3ef',
        'blue':   '#3b6aff',
        'gray':   '#9aa3b4',
        'orange': '#fb923c',
        'grid':   'rgba(255,255,255,0.08)',
        'bar_base_alpha': 0.55,
    },
}

rcParams['font.family'] = ['DejaVu Sans', 'Helvetica', 'sans-serif']
rcParams['axes.spines.top'] = False
rcParams['axes.spines.right'] = False


def _style_axes(ax, t):
    ax.set_facecolor(t['bg'])
    for side in ('left', 'bottom'):
        ax.spines[side].set_color(t['fg'])
    ax.tick_params(colors=t['fg'])
    ax.yaxis.label.set_color(t['fg'])
    ax.xaxis.label.set_color(t['fg'])
    ax.grid(axis='y', color=t['grid'] if isinstance(t['grid'], str) and t['grid'].startswith('#') else '#2a2e3e', linewidth=0.6)
    ax.set_axisbelow(True)


def grafica_fds(theme):
    t = THEMES[theme]
    days = ['viernes', 'sabado', 'domingo', 'lunes']
    day_labels = ['Viernes\n(sin ley seca hist.)', 'Sábado', 'Domingo\n(elección)', 'Lunes']
    obs = {d: 0 for d in days}
    base = {d: 0 for d in days}
    for b in rep:
        for r in b['detalle']['lesiones']['bogota']['dias']:
            obs[r['dia']] += r['cant']
            base[r['dia']] += r['baseline_mean']

    fig, ax = plt.subplots(figsize=(12, 6.75), dpi=180)
    fig.patch.set_facecolor(t['bg'])
    _style_axes(ax, t)

    x = list(range(len(days)))
    w = 0.36
    ax.bar([i - w/2 for i in x], [obs[d] for d in days], w,
           label='Observado (Σ 4 elecciones)', color=t['blue'], edgecolor=t['fg'], linewidth=0.6)
    ax.bar([i + w/2 for i in x], [base[d] for d in days], w,
           label='Esperado · baseline mismo día semana', color=t['gray'],
           alpha=t['bar_base_alpha'], edgecolor=t['fg'], linewidth=0.6)

    for i, d in enumerate(days):
        o = obs[d]
        bv = base[d]
        delta = (o - bv) / bv * 100 if bv else 0
        ax.text(i - w/2, o + 6, f'{int(o)}', ha='center', va='bottom',
                fontsize=10.5, fontweight='bold', color=t['fg'])
        ax.text(i + w/2, bv + 6, f'{bv:.0f}', ha='center', va='bottom',
                fontsize=10.5, color=t['gray'])
        color = t['orange'] if delta > -10 else t['blue']
        ax.text(i, max(o, bv) + 35, f'{delta:+.1f}%',
                ha='center', va='bottom', fontsize=14, fontweight='bold',
                color=color)

    ax.set_xticks(x)
    ax.set_xticklabels(day_labels, fontsize=11, color=t['fg'])
    ax.set_ylabel('Lesiones personales · Bogotá D.C.', fontsize=11, color=t['fg'])
    ax.set_title('Fin de semana electoral en Bogotá · suma de 4 presidenciales (2010 + 2014 + 2018 + 2022)',
                 fontsize=13.5, fontweight='bold', color=t['fg'], pad=36, loc='left')
    ax.text(0, 1.025,
            'El viernes pre-electoral en Bogotá tiene una caída de −6,7 % frente al baseline — dentro del ruido estadístico.',
            transform=ax.transAxes, fontsize=10.5, color=t['gray'], style='italic')

    ax.set_ylim(0, max(max(obs.values()), max(base.values())) * 1.22)

    leg = ax.legend(loc='upper right', frameon=False, fontsize=10.5)
    for txt in leg.get_texts():
        txt.set_color(t['fg'])

    fig.text(0.012, 0.012,
             'Fuente: DIJIN · Policía Nacional · Grupo de Información de Criminalidad.    ricardoruiz.co',
             fontsize=9, color=t['gray'])

    plt.tight_layout(rect=[0, 0.025, 1, 1])
    suffix = '' if theme == 'light' else '-dark'
    fn = f'grafica-fds-bogota{suffix}.png'
    plt.savefig(fn, dpi=180, bbox_inches='tight', facecolor=t['bg'])
    plt.close()
    print(f'· {fn}')


def grafica_viernes(theme):
    t = THEMES[theme]
    years = [2010, 2014, 2018, 2022]
    obs_y = []
    base_y = []
    std_y = []
    for b in rep:
        vie = [r for r in b['detalle']['lesiones']['bogota']['dias'] if r['dia'] == 'viernes'][0]
        obs_y.append(vie['cant'])
        base_y.append(vie['baseline_mean'])
        std_y.append(vie['baseline_std'])

    fig, ax = plt.subplots(figsize=(12, 6.75), dpi=180)
    fig.patch.set_facecolor(t['bg'])
    _style_axes(ax, t)

    x = list(range(len(years)))
    w = 0.36

    ax.bar([i - w/2 for i in x], obs_y, w,
           label='Viernes pre-electoral observado', color=t['blue'], edgecolor=t['fg'], linewidth=0.6)
    ax.bar([i + w/2 for i in x], base_y, w,
           label='Baseline · viernes promedio mismo año', color=t['gray'],
           alpha=t['bar_base_alpha'], edgecolor=t['fg'], linewidth=0.6)
    ax.errorbar([i + w/2 for i in x], base_y, yerr=std_y,
                fmt='none', ecolor=t['fg'], capsize=4, capthick=1.2, linewidth=1.2, alpha=0.85)

    for i, y in enumerate(years):
        o = obs_y[i]
        bv = base_y[i]
        delta = (o - bv) / bv * 100 if bv else 0
        ax.text(i - w/2, o + 1.5, f'{int(o)}', ha='center', va='bottom',
                fontsize=11, fontweight='bold', color=t['fg'])
        ax.text(i + w/2, bv + std_y[i] + 1.5, f'{bv:.1f}', ha='center', va='bottom',
                fontsize=11, color=t['gray'])
        color = t['orange'] if delta > -10 else t['blue']
        ax.text(i, max(o, bv + std_y[i]) + 8, f'{delta:+.1f}%',
                ha='center', va='bottom', fontsize=13.5, fontweight='bold', color=color)

    ax.set_xticks(x)
    ax.set_xticklabels([str(y) for y in years], fontsize=11, color=t['fg'])
    ax.set_ylabel('Lesiones personales · Bogotá D.C.', fontsize=11, color=t['fg'])
    ax.set_title('Viernes pre-electoral en Bogotá · cada elección presidencial 2010-2022',
                 fontsize=13.5, fontweight='bold', color=t['fg'], pad=36, loc='left')
    ax.text(0, 1.025,
            'Ninguno de los 4 viernes pre-electorales se distingue de un viernes promedio (±1σ del baseline).',
            transform=ax.transAxes, fontsize=10.5, color=t['gray'], style='italic')

    ax.set_ylim(0, max(max(obs_y), max(base_y[i] + std_y[i] for i in range(4))) * 1.28)

    leg = ax.legend(loc='upper left', frameon=False, fontsize=10.5)
    for txt in leg.get_texts():
        txt.set_color(t['fg'])

    fig.text(0.012, 0.012,
             'Fuente: DIJIN · Policía Nacional · Grupo de Información de Criminalidad.    ricardoruiz.co',
             fontsize=9, color=t['gray'])

    plt.tight_layout(rect=[0, 0.025, 1, 1])
    suffix = '' if theme == 'light' else '-dark'
    fn = f'grafica-viernes-anios{suffix}.png'
    plt.savefig(fn, dpi=180, bbox_inches='tight', facecolor=t['bg'])
    plt.close()
    print(f'· {fn}')


if __name__ == '__main__':
    for theme in ('light', 'dark'):
        grafica_fds(theme)
        grafica_viernes(theme)
