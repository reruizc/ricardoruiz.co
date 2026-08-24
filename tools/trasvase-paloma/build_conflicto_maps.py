#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mapas del carrusel 'zonas de conflicto': cómo cambió la izquierda (Petro22 -> Cepeda26)
en los 150 municipios CITREP. Salida: PNG transparentes para incrustar en el carrusel IG."""
import json, math
from pathlib import Path
import geopandas as gpd
import pandas as pd
from pyproj import Transformer
from shapely.geometry import shape

_TF = Transformer.from_crs(4326, 3857, always_xy=True)
def m(lon, lat): return _TF.transform(lon, lat)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

plt.rcParams['font.family'] = ['Helvetica Neue', 'Helvetica', 'Arial', 'sans-serif']

GEO = Path('Bases de datos/output_pacto_1v_2026/geo')
OUT = Path('rrss/instagram/conflicto-png/maps'); OUT.mkdir(parents=True, exist_ok=True)

# paleta del carrusel
PAPER = '#f1eee4'
INK = '#1a1510'
OX = '#8a1e16'      # la izquierda retrocedió
GREEN = '#2e7d46'   # la izquierda creció
SAND = '#c9b89a'    # estable
SILH = '#e3ddcf'    # silueta país (no-CITREP)
SILH_EDGE = '#cdc4b2'
CEP = '#6a4c93'     # ganó Cepeda (morado Pacto)
ABE = '#16235e'     # ganó Abelardo (azul marino)

rows = json.load(open('/tmp/conflicto_por_muni.json'))
data = {r['key']: r for r in rows}

def cls(d):
    if d >= 3: return GREEN
    if d <= -3: return OX
    return SAND

# ---- silueta nacional (departamentos) ----
deps = gpd.read_file(GEO / 'DEPARTAMENTOS2.json').to_crs(3857)

# ---- municipios CITREP coloreados ----
feats = []
citrep_deps = sorted(set(r['key'].split('-')[0] for r in rows), key=lambda x: int(x))
matched = 0
for dep in citrep_deps:
    fp = GEO / 'mps' / f'{int(dep):02d}.json'
    if not fp.exists(): continue
    g = json.load(open(fp))
    for ft in g['features']:
        p = ft['properties']
        de = str(p.get('dep_electoral') or '').lstrip('0') or '0'
        me = str(p.get('mun_elec') or '').lstrip('0') or '0'
        key = f"{de}-{me}"
        if key in data:
            r = data[key]
            feats.append({'geometry': shape(ft['geometry']), 'key': key,
                          'mun': r['mun'], 'dep': r['dep'], 'delta': r['delta_pp'],
                          'cepeda': r['cepeda_pct'], 'abelardo': r['abelardo_pct'],
                          'petro': r['petro_pct'], 'gana': r['gana26'], 'color': cls(r['delta_pp']),
                          'wcolor': ABE if r['gana26'] == 'Abelardo' else CEP})
            matched += 1
gdf = gpd.GeoDataFrame(feats, crs=4326).to_crs(3857)
print(f"CITREP matched {matched}/{len(rows)}  ·  green={sum(1 for f in feats if f['color']==GREEN)} sand={sum(1 for f in feats if f['color']==SAND)} ox={sum(1 for f in feats if f['color']==OX)}")

def base(ax):
    deps.plot(ax=ax, color=SILH, edgecolor=SILH_EDGE, linewidth=0.6, zorder=1)
    ax.set_axis_off()

def draw(gsel, fname, xlim=None, ylim=None, w=12, h=12, labels=None, lw=0.4, edge='#f1eee4', col='color'):
    fig, ax = plt.subplots(figsize=(w, h), dpi=120)
    base(ax)
    gsel.plot(ax=ax, color=gsel[col], edgecolor=edge, linewidth=lw, zorder=3)
    if xlim: ax.set_xlim(*xlim)
    if ylim: ax.set_ylim(*ylim)
    if labels:
        for mun, (lx, ly), (px, py), ha in labels:
            ax.annotate(mun, xy=(px, py), xytext=(lx, ly), ha=ha, va='center',
                        fontsize=15, fontweight='bold', color=INK,
                        arrowprops=dict(arrowstyle='-', color=INK, lw=1.1, shrinkA=0, shrinkB=2))
    ax.margins(0)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    fig.savefig(OUT / fname, transparent=True, bbox_inches='tight', pad_inches=0.06)
    plt.close(fig)
    print('  ✓', fname)

# === 1 · COVER NACIONAL (continente) ===
x0, y0 = m(-79.2, -4.3); x1, y1 = m(-66.8, 12.7)
draw(gdf, 'map-cover.png', xlim=(x0, x1), ylim=(y0, y1), w=11, h=13, lw=0.35)

# === 2 · PACÍFICO (Nariño + Cauca + Putumayo) — el corredor de la grieta ===
pac = gdf[gdf['dep'].isin(['NARIÑO', 'CAUCA', 'PUTUMAYO'])].copy()
xp0, yp0 = m(-78.9, 0.3); xp1, yp1 = m(-75.5, 3.4)
draw(pac, 'map-pacifico.png', xlim=(xp0, xp1), ylim=(yp0, yp1), w=11, h=11, lw=0.5)

# === 3 · ANTIOQUIA (Bajo Cauca + Urabá) — la izquierda RECONQUISTÓ ===
ant = gdf[gdf['dep'] == 'ANTIOQUIA'].copy()
xa0, ya0 = m(-77.2, 6.4); xa1, ya1 = m(-73.9, 8.9)
draw(ant, 'map-antioquia.png', xlim=(xa0, xa1), ylim=(ya0, ya1), w=11, h=10, lw=0.5)

# === 4 · GANADOR NACIONAL (Cepeda morado vs Abelardo navy) ===
nwin = sum(1 for f in feats if f['gana'] == 'Abelardo')
print(f"ganador: Cepeda={len(feats)-nwin}  Abelardo={nwin}")
draw(gdf, 'map-winner.png', xlim=(x0, x1), ylim=(y0, y1), w=11, h=13, lw=0.35, col='wcolor')

# === 5 · FRONTERA ORIENTAL (Catatumbo→Abelardo vs Arauca→Cepeda) ===
fro = gdf[gdf['dep'].isin(['NORTE DE SAN', 'ARAUCA'])].copy()
print(f"frontera: {sorted((f['mun'], f['dep'], f['gana']) for f in feats if f['dep'] in ('NORTE DE SAN', 'ARAUCA'))}")
xf0, yf0 = m(-73.7, 5.9); xf1, yf1 = m(-69.6, 9.4)
draw(fro, 'map-frontera.png', xlim=(xf0, xf1), ylim=(yf0, yf1), w=12, h=10, lw=0.6, col='wcolor')

print('DONE')
