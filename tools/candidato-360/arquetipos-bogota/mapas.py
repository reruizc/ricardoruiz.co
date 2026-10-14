#!/usr/bin/env python3
"""Mapas del borrador: un panel por arquetipo, para Concejo y para Alcaldía.

    python3 tools/candidato-360/arquetipos-bogota/mapas.py

Un panel por arquetipo y no un solo mapa con seis colores: con barrios vecinos
de cualquier tipo, seis tonos categóricos no se distinguen todos entre sí (lo
mide el validador de color). En cada panel los barrios del arquetipo van en un
solo tono, más oscuro cuanto más nítida es la asignación (confianza en 200
re-muestras). Bogotá rotada 90° a la izquierda, como en el resto del proyecto;
Sumapaz fuera del encuadre.

Salida: Propuestas/candidato-360/arquetipos-bogota/mapa-{concejo,alcaldia}.png
"""
import json
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from shapely import affinity

RAIZ = Path(__file__).resolve().parents[3]
BD = RAIZ / 'Bases de datos'
OUT = RAIZ / 'Propuestas' / 'candidato-360' / 'arquetipos-bogota'
for f in ('Inter-Regular.ttf', 'Inter-Bold.ttf'):
    font_manager.fontManager.addfont(str(RAIZ / 'tools' / 'pacto-1v-2026' / 'fonts' / f))
plt.rcParams['font.family'] = 'Inter'

INK, MUTED, GRID = '#1a1a19', '#6b6a65', '#e4e2dc'
SIN_DATO, OTRO = '#f4f3ef', '#dedcd5'
TONO = {'alta': '#1c5cab', 'media': '#5b93d6', 'baja': '#a9c5ea'}   # una sola tinta, por confianza


def main():
    arq = json.loads((BD / 'arquetipos-bogota' / 'arquetipos-bogota.json').read_text())
    g = gpd.read_file(BD / 'output_pacto_1v_2026' / 'geo' / 'BOG-BARRIOS-CATASTRALES.json')
    g = g[g['loc_codigo'] != '20'].copy()
    c = g.union_all().centroid
    g['geometry'] = g['geometry'].apply(lambda x: affinity.rotate(x, 90, origin=(c.x, c.y)))
    loc = g.dissolve('loc_codigo')
    OUT.mkdir(parents=True, exist_ok=True)
    tot_vot = sum(b['vars']['votantes23'] or 0 for b in arq['barrios'].values())
    for corp, titulo in (('concejo', 'Concejo'), ('alcaldia', 'Alcaldía')):
        A = arq['corporaciones'][corp]
        orden = sorted(A['arquetipos'], key=lambda s: -A['arquetipos'][s]['votantes'])
        n = len(orden)
        cols = 3
        filas = (n + cols - 1) // cols
        fig, axs = plt.subplots(filas, cols, figsize=(cols * 5.4, filas * 3.55 + 1.6),
                                gridspec_kw={'hspace': 0.32, 'wspace': 0.04})
        axs = axs.ravel()
        for ax, s in zip(axs, orden):
            a = A['arquetipos'][s]
            col = []
            for cod in g['codigo']:
                b = arq['barrios'].get(cod, {}).get(corp)
                if not b:
                    col.append(SIN_DATO)
                elif b['dom'] != s:
                    col.append(OTRO)
                else:
                    col.append(TONO['alta'] if b['conf'] >= .8 else TONO['media'] if b['conf'] >= .6 else TONO['baja'])
            g.plot(ax=ax, color=col, edgecolor='white', linewidth=0.15)
            loc.boundary.plot(ax=ax, color='#8a8880', linewidth=0.45)
            ax.set_axis_off()
            ax.set_aspect('equal')
            ax.set_title(a['nombre'], fontsize=13, fontweight='bold', color=INK, loc='left', pad=17)
            ax.text(0, 1.01, f"{a['barrios']} barrios · {a['votantes'] / tot_vot:.0%} de los votantes", transform=ax.transAxes,
                    fontsize=9.5, color=MUTED, va='bottom', ha='left')
        for ax in axs[n:]:
            ax.set_axis_off()
        from matplotlib.patches import Patch
        hand = [Patch(facecolor=TONO['alta'], edgecolor='#c9c7c0', label='Del arquetipo · nítido (80 % o más)'),
                Patch(facecolor=TONO['media'], edgecolor='#c9c7c0', label='probable (60-80 %)'),
                Patch(facecolor=TONO['baja'], edgecolor='#c9c7c0', label='de frontera (<60 %)'),
                Patch(facecolor=OTRO, edgecolor='#c9c7c0', label='De otro arquetipo'),
                Patch(facecolor=SIN_DATO, edgecolor='#c9c7c0', label='Sin puesto de votación propio')]
        fig.legend(handles=hand, loc='lower left', ncol=5, frameon=False, fontsize=9.5, bbox_to_anchor=(0.01, 0.0),
                   handlelength=1.4, columnspacing=1.6)
        fig.text(0.01, 0.045, 'El porcentaje es la confianza: en cuántas de 200 re-muestras el barrio cae en el mismo arquetipo. '
                 'Bogotá rotada 90°: el norte queda a la izquierda. Líneas grises: localidades; Sumapaz fuera del encuadre.',
                 fontsize=8.8, color=MUTED, ha='left')
        m = A['meta']
        fig.text(.01, .975, f'Arquetipos de voto en Bogotá · {titulo} 2023 (borrador)', ha='left', va='top', fontsize=18,
                 fontweight='bold', color=INK)
        fig.text(.01, .925, f"{m['barrios']} barrios con puesto de votación · {m['nitidos']} nítidos, {m['frontera']} de frontera · "
                 'Fuente: Registraduría (resultados 2019, 2023 y 1V 2026), censo electoral, estrato SDP/IDECA',
                 fontsize=9.5, color=MUTED, ha='left', va='top')
        fig.subplots_adjust(left=.01, right=.99, top=.84 if filas == 2 else .78, bottom=.1)
        fig.savefig(OUT / f'mapa-{corp}.png', dpi=150, facecolor='white')
        plt.close(fig)
        print('ok', OUT / f'mapa-{corp}.png')


if __name__ == '__main__':
    main()
