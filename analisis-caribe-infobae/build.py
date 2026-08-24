#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mapas + estadísticas de la 1ª vuelta presidencial 2026 en la Costa Caribe,
con estética editorial de Infobae (fondo blanco, kicker naranja, sans limpia).

Insumos:
  - ESCRUTINIO-1V/ESCRUTINIO_1V_2026_PUESTO.csv (escrutinio oficial por puesto)
  - PUESTOS_GEOREF.csv (lat/lon por puesto) + censos-puesto-2026.json (censo electoral)
  - master_2022_puesto.json (Petro/Fico/Rodolfo 1V-2V 2022 por puesto)
  - geo/DEPARTAMENTOS2.json + geo/mps/{cod}.json + geo/*-BARRIOS.json
    (Santa Marta: SANTAMARTA-BARRIOS-REAL.json, 283 polígonos reales del
     Observatorio Nacional de Seguridad Vial · ANSV en ArcGIS Online)

Salidas (en esta misma carpeta):
  01..08 PNG + stats.json
"""
import json, csv, unicodedata, os
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

BASE  = '/Users/ricardoruiz/ricardoruiz.co'
OUT   = os.path.join(BASE, 'analisis-caribe-infobae')
GEO   = os.path.join(BASE, 'Bases de datos/output_pacto_1v_2026/geo')
ESC   = os.path.join(BASE, 'Bases de datos/ESCRUTINIO-1V/ESCRUTINIO_1V_2026_PUESTO.csv')
GEOREF= os.path.join(BASE, 'Bases de datos/PUESTOS_GEOREF.csv')
CENSO = os.path.join(BASE, 'Bases de datos/censos-puesto-2026.json')
M22   = os.path.join(BASE, 'Bases de datos/output_pacto_1v_2026/master_2022_puesto.json')

CARIBE = {'03':'Atlántico','05':'Bolívar','12':'Cesar','13':'Córdoba',
          '21':'Magdalena','28':'Sucre','48':'La Guajira'}
# columnas del escrutinio → slug (Murillo y Caicedo no están en el escrutinio)
COLMAP = {'Abelardo De La Espriella':'abelardo','Iván Cepeda Castro':'cepeda',
          'Paloma Valencia Laserna':'paloma','Sergio Fajardo Valderrama':'fajardo',
          'Claudia López':'claudia','Raúl Santiago Botero Jaramillo':'botero',
          'Óscar Mauricio Lizcano Arango':'lizcano','Miguel Uribe Londoño':'miguel_uribe',
          'Sondra Macollins Garvin Pinto':'macollins',
          'Roy Leonardo Barreras Montealegre':'roy','Gustavo Matamoros Camacho':'matamoros'}
CANDS  = list(COLMAP.values())
NOMBRE = {'cepeda':'Iván Cepeda','abelardo':'Abelardo De La Espriella',
          'paloma':'Paloma Valencia','fajardo':'Sergio Fajardo','botero':'Santiago Botero',
          'claudia':'Claudia López','blanco':'Voto en blanco'}

# ---------- estética Infobae ----------
NARANJA = '#FF6600'
INK     = '#1f1f1f'
GRIS    = '#666666'
GRISCL  = '#d9d9d9'
CEP     = '#d3342c'   # Cepeda (izquierda) rojo
ABE     = '#1d5ca8'   # De La Espriella (derecha) azul
OTRO    = '#9aa0a6'
FUENTE  = ('Fuente: Registraduría Nacional (escrutinio oficial, 1ª vuelta · 31 de mayo de 2026) · '
           'Procesamiento y análisis: Ricardo Ruiz · ricardoruiz.co')

plt.rcParams['font.family'] = ['Helvetica Neue', 'Helvetica', 'Arial']
plt.rcParams['axes.edgecolor'] = GRISCL
plt.rcParams['text.color'] = INK

CMAP_DIV = LinearSegmentedColormap.from_list('abe_cep', [ABE, '#eef1f5', CEP])

def frame(fig, kicker, title, subtitle, note=None):
    """Cabecera + pie estilo Infobae sobre la figura completa."""
    fig.patch.set_facecolor('white')
    fig.text(0.045, 0.965, kicker.upper(), fontsize=12.5, fontweight='bold',
             color=NARANJA, va='top')
    fig.text(0.045, 0.938, title, fontsize=21, fontweight='bold', color=INK, va='top')
    fig.text(0.045, 0.898, subtitle, fontsize=12.5, color=GRIS, va='top')
    # regla naranja corta bajo el kicker
    fig.add_artist(plt.Line2D([0.045, 0.105], [0.978, 0.978], transform=fig.transFigure,
                              color=NARANJA, lw=3, solid_capstyle='butt'))
    if note:
        import textwrap
        nw = '\n'.join(textwrap.wrap(note, 150))
        fig.text(0.045, 0.012, nw, fontsize=8.5, color=GRIS, va='bottom', linespacing=1.4)
        fig.text(0.045, 0.046, FUENTE, fontsize=9, color=GRIS, va='bottom')
    else:
        fig.text(0.045, 0.022, FUENTE, fontsize=9, color=GRIS, va='bottom')

def fmt(n):
    return f'{n:,.0f}'.replace(',', '.')

def norm(s):
    s = unicodedata.normalize('NFD', str(s or ''))
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').upper().strip()

# ---------- carga ----------
m22 = json.load(open(M22))

# georef oficial (lat/lon por puesto, clave de 9 dígitos dep+mun+zona+puesto)
georef = {}
with open(GEOREF, encoding='utf-8-sig') as f:
    for row in csv.DictReader(f, delimiter=';'):
        cc = row['CÓDIGO COMPLETO']
        try:
            georef[cc] = (float(row['LATITUD']), float(row['LONGITUD']))
        except (ValueError, TypeError):
            pass

censo_pp = json.load(open(CENSO))['porPuesto']

pts = []
with open(ESC, encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        if row['cod_departamento'] not in CARIBE: continue
        dep, mn = row['cod_departamento'], row['cod_municipio']
        zona, pu = row['zona'].zfill(2), row['cod_puesto'].zfill(2)
        p = {COLMAP[c]: int(row[c] or 0) for c in COLMAP}
        p.update(dep=dep, mun=mn, zona=zona, puesto=pu,
                 mun_nombre=row['municipio'],
                 votos_blanco=int(row['Votos en blanco'] or 0),
                 votos_nulos=int(row['Votos nulos'] or 0),
                 votos_no_marcados=int(row['Votos no marcados'] or 0),
                 total_votos_urna=int(row['total_votos'] or 0),
                 claudia_r=0,
                 pot=censo_pp.get(f'{dep}-{mn}-{zona}-{pu}') or 0)
        ll = georef.get(dep + mn + zona + pu)
        p['lat'], p['lon'] = (ll if ll else (None, None))
        pts.append(p)
print('puestos escrutinio Caribe:', len(pts),
      '· con georef:', sum(1 for p in pts if p['lat']),
      '· con censo:', sum(1 for p in pts if p['pot']))

# agregado municipal
mun = {}
for p in pts:
    k = f"{p['dep']}-{p['mun']}"
    a = mun.setdefault(k, {c: 0 for c in CANDS} | {'claudia_r':0,'blanco':0,'nulos':0,'nm':0,'total':0,'pot':0,'dep':p['dep'],'nombre':p['mun_nombre']})
    for c in CANDS: a[c] += p[c]
    a['claudia_r'] += p['claudia_r']
    a['blanco'] += p['votos_blanco']; a['nulos'] += p['votos_nulos']
    a['nm'] += p['votos_no_marcados']; a['total'] += p['total_votos_urna']
    a['pot'] += p.get('pot') or 0

def validos(a):
    return sum(a[c] for c in CANDS) + a['claudia_r'] + a['blanco']

# agregado departamental 2026 + 2022
dep = {d: {c:0 for c in CANDS} | {'claudia_r':0,'blanco':0,'total':0,'pot':0} for d in CARIBE}
for k, a in mun.items():
    d = a['dep']
    for c in CANDS: dep[d][c] += a[c]
    dep[d]['claudia_r'] += a['claudia_r']; dep[d]['blanco'] += a['blanco']
    dep[d]['total'] += a['total']; dep[d]['pot'] += a['pot']

d22 = {d: {'petro1v':0,'fico1v':0,'rodolfo1v':0,'base1v':0,'petro2v':0,'base2v':0} for d in CARIBE}
for p in m22:
    if p['dep'] in CARIBE:
        for f in d22[p['dep']]: d22[p['dep']][f] += p.get(f) or 0

# nombres de municipios desde los geojson
mun_names = {}
def load_mps(d):
    g = gpd.read_file(os.path.join(GEO, 'mps', f'{d}.json'))
    g['key'] = g['dep_electoral'] + '-' + g['mun_elec']
    for _, r in g.iterrows():
        mun_names[r['key']] = str(r['mpio_cnmbr']).title()
    return g

gmps = pd.concat([load_mps(d) for d in CARIBE], ignore_index=True)
gmps = gpd.GeoDataFrame(gmps, crs='EPSG:4326')

def mun_metrics(k):
    a = mun.get(k)
    if not a or validos(a) == 0: return None
    v = validos(a)
    return {'cep': a['cepeda']/v*100, 'abe': a['abelardo']/v*100,
            'margen': (a['cepeda']-a['abelardo'])/v*100, 'validos': v, 'total': a['total']}

gmps['met'] = gmps['key'].map(mun_metrics)
gmps = gmps[gmps['met'].notna()].copy()
gmps['margen'] = gmps['met'].apply(lambda m: m['margen'])
gmps['winner'] = np.where(gmps['margen'] >= 0, 'cep', 'abe')
gmps['wpct']   = gmps['met'].apply(lambda m: max(m['cep'], m['abe']))

gdep = gpd.read_file(os.path.join(GEO, 'DEPARTAMENTOS2.json'))
gdep['n'] = gdep['name'].apply(norm)
CARN = {norm(v) for v in CARIBE.values()}
gdep_c = gdep[gdep['n'].isin(CARN)]

# ---------- 01 · ganador por municipio ----------
fig, ax = plt.subplots(figsize=(12, 11))
fig.subplots_adjust(top=0.86, bottom=0.07, left=0.02, right=0.98)
def shade(base, pct):
    # intensidad: 45% -> claro, 75% -> pleno
    t = min(1, max(0, (pct - 42) / 33))
    base_rgb = np.array(matplotlib.colors.to_rgb(base))
    return tuple(base_rgb * (0.45 + 0.55*t) + np.array([1,1,1]) * (0.55 - 0.55*t) * 0 + (1-(0.45+0.55*t)) * np.array([1,1,1]) * 0 + base_rgb*0)  # placeholder
def mixw(base, pct):
    t = min(1, max(0, (pct - 42) / 33))
    b = np.array(matplotlib.colors.to_rgb(base)); w = np.array([1, 1, 1])
    return tuple(w + (b - w) * (0.35 + 0.65 * t))
gmps['fc'] = [mixw(CEP if w == 'cep' else ABE, p) for w, p in zip(gmps['winner'], gmps['wpct'])]
gmps.plot(ax=ax, color=gmps['fc'], edgecolor='white', linewidth=0.4)
gdep_c.boundary.plot(ax=ax, color=INK, linewidth=0.9)
for _, r in gdep_c.iterrows():
    c = r.geometry.representative_point()
    ax.annotate(r['name'], (c.x, c.y), fontsize=10.5, fontweight='bold', color=INK,
                ha='center', path_effects=[pe.withStroke(linewidth=2.5, foreground='white')])
ax.set_axis_off()
handles = [Patch(facecolor=CEP, label='Ganó Iván Cepeda'),
           Patch(facecolor=ABE, label='Ganó Abelardo De La Espriella')]
ax.legend(handles=handles, loc='upper right', frameon=False, fontsize=11.5)
ncep = int((gmps['winner']=='cep').sum()); nabe = int((gmps['winner']=='abe').sum())
frame(fig, 'Elecciones 2026 · Primera vuelta',
      'Quién ganó en cada municipio de la costa Caribe',
      f'Cepeda ganó en {ncep} municipios y De La Espriella en {nabe}. El tono indica el porcentaje del ganador.',
      note='Porcentajes sobre votos válidos (candidatos + voto en blanco). No incluye San Andrés y Providencia.')
fig.savefig(os.path.join(OUT, '01-caribe-municipios-ganador.png'), dpi=150)
plt.close(fig)

# ---------- 02 · margen Cepeda - Abelardo ----------
fig, ax = plt.subplots(figsize=(12, 11))
fig.subplots_adjust(top=0.86, bottom=0.07, left=0.02, right=0.98)
vmax = 60
nrm = TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)
gmps.plot(ax=ax, column='margen', cmap=CMAP_DIV, norm=nrm, edgecolor='white', linewidth=0.4)
gdep_c.boundary.plot(ax=ax, color=INK, linewidth=0.9)
ax.set_axis_off()
sm = plt.cm.ScalarMappable(cmap=CMAP_DIV, norm=nrm)
cb = fig.colorbar(sm, ax=ax, shrink=0.45, anchor=(0.0, 0.05), pad=0.01)
cb.set_label('Ventaja en puntos porcentuales', fontsize=10, color=GRIS)
cb.ax.tick_params(labelsize=9, colors=GRIS)
cb.outline.set_visible(False)
fig.text(0.79, 0.50, '← azul: ventaja De La Espriella\n→ rojo: ventaja Cepeda',
         fontsize=9.5, color=GRIS)
frame(fig, 'Elecciones 2026 · Primera vuelta',
      'El margen municipio a municipio en el Caribe',
      'Diferencia en puntos entre Iván Cepeda y Abelardo De La Espriella sobre votos válidos.',
      note='Escrutinio oficial por puesto agregado a municipio. No incluye San Andrés y Providencia.')
fig.savefig(os.path.join(OUT, '02-caribe-margen.png'), dpi=150)
plt.close(fig)

# ---------- mapas por barrio ----------
def barrio_map(city, depc, munc, geofile, namefield, fname, approx=False, max_snap=None):
    """max_snap (grados): tope de distancia para asignar al barrio más cercano un
    puesto que cae fuera de todo polígono. Con tope, los puestos rurales lejanos
    (corregimientos) quedan fuera del mapa urbano en vez de contaminar un barrio."""
    g = gpd.read_file(os.path.join(GEO, geofile)).to_crs('EPSG:4326')
    g = g[g.geometry.notna()].copy().reset_index(drop=True)
    g[namefield] = g[namefield].fillna('')
    pp = [p for p in pts if p['dep']==depc and p['mun']==munc
          and p['zona'] not in ('90','98') and p.get('lat') and p.get('lon')]
    pdf = gpd.GeoDataFrame({
        'cep':[p['cepeda'] for p in pp], 'abe':[p['abelardo'] for p in pp],
        'val':[sum(p[c] for c in CANDS)+p['claudia_r']+p['votos_blanco'] for p in pp]},
        geometry=gpd.points_from_xy([float(p['lon']) for p in pp], [float(p['lat']) for p in pp]),
        crs='EPSG:4326')
    j = gpd.sjoin(pdf, g[[namefield,'geometry']], how='left', predicate='within')
    missing = j[j[namefield].isna()]
    if len(missing):
        kw = {'max_distance': max_snap} if max_snap else {}
        jn = gpd.sjoin_nearest(missing.drop(columns=[c for c in missing.columns if c.startswith('index_') or c==namefield]),
                               g[[namefield,'geometry']], how='left', **kw)
        j = pd.concat([j[j[namefield].notna()], jn])
    agg = j.groupby(namefield)[['cep','abe','val']].sum()
    agg = agg[agg['val']>0]
    agg['margen'] = (agg['cep']-agg['abe'])/agg['val']*100
    g2 = g.merge(agg, left_on=namefield, right_index=True, how='left')
    # relleno de vecino para barrios sin puesto
    have = g2[g2['margen'].notna()]
    fillidx = g2[g2['margen'].isna()].index
    cent = have.geometry.representative_point()
    for i in fillidx:
        c = g2.loc[i].geometry.representative_point()
        d = cent.distance(c)
        if len(d):
            g2.loc[i, 'margen_f'] = have.loc[d.idxmin(), 'margen']
    fig, ax = plt.subplots(figsize=(12, 11.5))
    fig.subplots_adjust(top=0.845, bottom=0.07, left=0.02, right=0.98)
    nrm = TwoSlopeNorm(vmin=-70, vcenter=0, vmax=70)
    gf = g2[g2['margen'].isna() & g2['margen_f'].notna()] if 'margen_f' in g2 else g2.iloc[0:0]
    if len(gf):
        gf.plot(ax=ax, column='margen_f', cmap=CMAP_DIV, norm=nrm, alpha=0.30,
                edgecolor='white', linewidth=0.3)
    gnan = g2[g2['margen'].isna() & (g2['margen_f'].isna() if 'margen_f' in g2 else True)]
    if len(gnan):
        gnan.plot(ax=ax, color='#f2f2f2', edgecolor='white', linewidth=0.3)
    gd = g2[g2['margen'].notna()]
    gd.plot(ax=ax, column='margen', cmap=CMAP_DIV, norm=nrm, edgecolor='white', linewidth=0.35)
    # encuadre al casco urbano: percentiles de los puestos (descarta rural/islas lejanas)
    xs = pdf.geometry.x.to_numpy(); ys = pdf.geometry.y.to_numpy()
    x0, x1 = np.percentile(xs, 8), np.percentile(xs, 92)
    y0, y1 = np.percentile(ys, 8), np.percentile(ys, 92)
    mx = (x1-x0)*0.30; my = (y1-y0)*0.30
    ax.set_xlim(x0-mx, x1+mx); ax.set_ylim(y0-my, y1+my)
    ax.set_axis_off()
    # titular: resultado de TODO el municipio (incluye corregimientos rurales)
    am = mun[f'{depc}-{munc}']; vm = validos(am)
    cv = am['cepeda']/vm*100; av = am['abelardo']/vm*100
    ncep = int((agg['margen']>=0).sum()); nabe = int((agg['margen']<0).sum())
    handles = [Patch(facecolor=CEP, label=f'Cepeda adelante ({ncep} barrios con dato)'),
               Patch(facecolor=ABE, label=f'De La Espriella adelante ({nabe})'),
               Patch(facecolor='#e9e4e1', label='Sin puesto propio (tendencia del vecino)')]
    # leyenda horizontal FUERA del mapa, entre el subtítulo y el lienzo
    fig.legend(handles=handles, loc='upper left', bbox_to_anchor=(0.045, 0.882),
               ncol=3, frameon=False, fontsize=10.5, handlelength=1.5,
               columnspacing=1.4, handletextpad=0.6, borderaxespad=0)
    sub = (f'En {city} el resultado fue Cepeda {cv:.1f}% – De La Espriella {av:.1f}%. '
           'La intensidad refleja la ventaja en cada barrio.')
    note = ('Cada puesto de votación se asigna al barrio donde está ubicado; los barrios sin puesto '
            'heredan la tendencia del más cercano (tono tenue). Excluye puesto censo y cárceles.')
    if max_snap:
        note += ' El mapa cubre el casco urbano; los corregimientos rurales no se asignan a barrios.'
    if approx:
        note += ' Polígonos de barrio aproximados (área de influencia de cada puesto).'
    frame(fig, 'Elecciones 2026 · Primera vuelta',
          f'{city}, barrio por barrio', sub, note=note)
    fig.savefig(os.path.join(OUT, fname), dpi=150)
    plt.close(fig)
    return {'ciudad': city, 'cep_pct': round(cv,1), 'abe_pct': round(av,1),
            'barrios_dato': int(len(agg)), 'barrios_cep': ncep, 'barrios_abe': nabe,
            'validos': int(agg['val'].sum())}

cities = []
cities.append(barrio_map('Barranquilla', '03', '001', 'BARRANQUILLA-BARRIOS.json', 'NOMBRE',
                         '03-barranquilla-barrios.png'))
cities.append(barrio_map('Cartagena', '05', '001', 'CARTAGENA-BARRIOS.json', 'NOMBRE',
                         '04-cartagena-barrios.png'))
cities.append(barrio_map('Soledad', '03', '052', 'SOLEDAD-BARRIOS.json', 'barrio',
                         '05-soledad-barrios.png'))
cities.append(barrio_map('Santa Marta', '21', '001', 'SANTAMARTA-BARRIOS-REAL.json', 'barrio',
                         '06-santamarta-barrios.png', max_snap=0.006))

# ---------- 07 · resultado agregado Caribe (barras) ----------
tot = {c: sum(dep[d][c] for d in dep) for c in CANDS}
tot['claudia'] += sum(dep[d]['claudia_r'] for d in dep)
blanco = sum(dep[d]['blanco'] for d in dep)
vcar = sum(tot.values()) + blanco
serie = [('cepeda', tot['cepeda'], CEP), ('abelardo', tot['abelardo'], ABE),
         ('paloma', tot['paloma'], OTRO), ('fajardo', tot['fajardo'], OTRO),
         ('botero', tot['botero'], OTRO), ('blanco', blanco, '#c9b458')]
fig, ax = plt.subplots(figsize=(12, 7.2))
fig.subplots_adjust(top=0.80, bottom=0.10, left=0.26, right=0.92)
labels = [NOMBRE[s[0]] for s in serie][::-1]
vals   = [s[1]/vcar*100 for s in serie][::-1]
cols   = [s[2] for s in serie][::-1]
bars = ax.barh(labels, vals, color=cols, height=0.62)
for b, v, raw in zip(bars, vals, [s[1] for s in serie][::-1]):
    ax.text(b.get_width()+0.8, b.get_y()+b.get_height()/2, f'{v:.1f}%  ({fmt(raw)})',
            va='center', fontsize=11, color=INK)
ax.set_xlim(0, 64)
ax.spines[['top','right','bottom']].set_visible(False)
ax.tick_params(axis='y', labelsize=12, length=0)
ax.tick_params(axis='x', labelsize=9, colors=GRIS)
ax.xaxis.set_major_formatter(lambda x, _: f'{x:.0f}%')
frame(fig, 'Elecciones 2026 · Primera vuelta',
      'Así votó la costa Caribe',
      f'Resultado agregado de los 7 departamentos del Caribe continental · {fmt(vcar)} votos válidos.',
      note='Porcentajes sobre votos válidos. Claudia López y otros candidatos suman menos del 1%.')
fig.savefig(os.path.join(OUT, '07-caribe-resultado.png'), dpi=150)
plt.close(fig)

# ---------- 08 · participación por departamento ----------
NAC_PART = 58.0
rows = []
for d, info in dep.items():
    part = info['total']/info['pot']*100 if info['pot'] else None
    rows.append((CARIBE[d], part))
rows.sort(key=lambda r: r[1])
fig, ax = plt.subplots(figsize=(12, 7.2))
fig.subplots_adjust(top=0.80, bottom=0.10, left=0.18, right=0.92)
labels = [r[0] for r in rows]; vals = [r[1] for r in rows]
bars = ax.barh(labels, vals, color=NARANJA, height=0.62)
for b, v in zip(bars, vals):
    ax.text(b.get_width()+0.6, b.get_y()+b.get_height()/2, f'{v:.1f}%', va='center',
            fontsize=11, color=INK)
ax.axvline(NAC_PART, color=INK, lw=1.2, ls='--')
ax.text(NAC_PART+0.4, len(rows)-0.25, f'Nacional: {NAC_PART:.0f}%', fontsize=10, color=INK)
ax.set_xlim(0, 72)
ax.spines[['top','right','bottom']].set_visible(False)
ax.tick_params(axis='y', labelsize=12, length=0)
ax.tick_params(axis='x', labelsize=9, colors=GRIS)
ax.xaxis.set_major_formatter(lambda x, _: f'{x:.0f}%')
frame(fig, 'Elecciones 2026 · Primera vuelta',
      'La participación en el Caribe quedó por debajo del país',
      'Votantes sobre censo electoral por departamento, frente al 58% nacional.',
      note='Censo electoral 2026 por puesto (Registraduría) frente a votos del escrutinio oficial.')
fig.savefig(os.path.join(OUT, '08-caribe-participacion.png'), dpi=150)
plt.close(fig)

# ---------- stats para el artículo ----------
stats = {'caribe': {'validos': int(vcar),
                    'pct': {k: round(v/vcar*100, 2) for k, v in (list(tot.items())+[('blanco', blanco)])},
                    'votos': {k: int(v) for k, v in (list(tot.items())+[('blanco', blanco)])},
                    'total_urna': int(sum(dep[d]['total'] for d in dep)),
                    'pot': int(sum(dep[d]['pot'] for d in dep))},
         'deptos': {}, 'ciudades': cities,
         'top_mun_cep': [], 'top_mun_abe': []}
for d in sorted(CARIBE):
    i = dep[d]; v = sum(i[c] for c in CANDS) + i['claudia_r'] + i['blanco']
    o = d22[d]
    stats['deptos'][CARIBE[d]] = {
        'cep_pct': round(i['cepeda']/v*100, 1), 'abe_pct': round(i['abelardo']/v*100, 1),
        'validos': int(v), 'part': round(i['total']/i['pot']*100, 1) if i['pot'] else None,
        'petro1v22_pct': round(o['petro1v']/o['base1v']*100, 1) if o['base1v'] else None,
        'petro2v22_pct': round(o['petro2v']/o['base2v']*100, 1) if o['base2v'] else None}
ms = []
for k, a in mun.items():
    v = validos(a)
    if v >= 5000:
        ms.append((a.get('nombre') or mun_names.get(k, k), CARIBE[a['dep']], v, a['cepeda']/v*100, a['abelardo']/v*100))
stats['top_mun_cep'] = sorted([m for m in ms], key=lambda m: -m[3])[:10]
stats['top_mun_abe'] = sorted([m for m in ms], key=lambda m: -m[4])[:10]
json.dump(stats, open(os.path.join(OUT, 'stats.json'), 'w'), ensure_ascii=False, indent=1)
print('OK ·', len(gmps), 'municipios mapeados ·', len(cities), 'ciudades por barrio')
print(json.dumps(stats['caribe']['pct'], ensure_ascii=False))
