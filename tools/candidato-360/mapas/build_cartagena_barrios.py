#!/usr/bin/env python3
"""Cartagena barrio por barrio, para el mapa del CRM y el del panel 06.

Emite lo mismo que ya tienen Bogotá y Cali:
  · candidato-360-data/cartagena-barrios/{UCG}.js   los 213 barrios partidos
      por Unidad Comunera de Gobierno, que es la unidad del nivel de arriba.
  · candidato-360-data/cartagena-puesto-barrio.js   {pcode: {barrio, comuna}}

La capa se parte por UCG y no se sirve entera (908 KB) porque el mapa abre UNA
unidad a la vez; la ciudad completa se arma uniendo las partes, igual que en
Bogotá.

⚠️ La UCG de cada puesto NO se recalcula acá: se lee de
`Bases de datos/output_hvp/cartagena-puesto-ucg.json`, que emite
`tools/analisis-candidato/build_cartagena_ucg.py`. Tener la misma cascada en
dos archivos es garantizar que un día dejen de coincidir —es la razón por la
que ese JSON existe—. Acá solo se añade el BARRIO, y si el barrio que sale por
coordenada cae en otra UCG que la del archivo, se avisa en vez de callarlo.

Correr:  python3 tools/candidato-360/mapas/build_cartagena_barrios.py
"""
import collections
import csv
import json
import os
import urllib.request

from shapely.geometry import shape, Point
from shapely.strtree import STRtree

S3 = ('https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/'
      'congreso-2026/output/mapas-2026/Ciudades-COM-LOC')
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BD = os.path.join(RAIZ, 'Bases de datos')
CACHE = os.path.join(BD, 'output_hvp', 'CARTAGENAX.json')
UCG_PUESTOS = os.path.join(BD, 'output_hvp', 'cartagena-puesto-ucg.json')
GEOREF = os.path.join(BD, 'PUESTOS_GEOREF.csv')
SAL_DIR = os.path.join(RAIZ, 'candidato-360-data', 'cartagena-barrios')
SAL_DIC = os.path.join(RAIZ, 'candidato-360-data', 'cartagena-puesto-barrio.js')
# Mismo tope que el builder de UCG: un puesto que cae en un vacío del mapa
# (una vía, un centro comercial) se pega al barrio más cercano hasta 1 km.
TOPE_M = 1000

MINUS = {'DE', 'DEL', 'LA', 'LAS', 'LOS', 'Y', 'EL', 'EN'}


def bonito(nombre):
    """«OLAYA ST. LA PUNTILLA» → «Olaya St. la Puntilla». Las siglas con punto
    se respetan, como en NOMBRE_BONITO del frontend."""
    palabras = str(nombre or '').strip().split()
    out = []
    for i, w in enumerate(palabras):
        if '.' in w:
            out.append(w.upper() if len(w) <= 4 else w.capitalize())
        elif i and w.upper() in MINUS:
            out.append(w.lower())
        else:
            out.append(w.capitalize())
    return ' '.join(out)


def norm(x):
    return ''.join(c for c in str(x or '').upper().strip() if c.isalnum() or c == ' ')


def cargar_geo():
    if not os.path.exists(CACHE):
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with urllib.request.urlopen(f'{S3}/CARTAGENAX.json', timeout=180) as r:
            datos = r.read()
        with open(CACHE, 'wb') as f:
            f.write(datos)
    with open(CACHE, encoding='utf-8') as f:
        return json.load(f)


geo = cargar_geo()
with open(UCG_PUESTOS, encoding='utf-8') as f:
    ucg_de_puesto = json.load(f)

# ── la capa, partida por UCG ────────────────────────────────────────────────
# Las propiedades quedan como las de Cali (`barrio` + `comuna`): el frontend
# las lee con el mismo código y no hace falta una tercera variante.
porucg = collections.defaultdict(list)
figuras, nombres_fig, ucgs_fig, por_nombre = [], [], [], {}
for ft in geo['features']:
    pr = ft.get('properties') or {}
    if pr.get('UCG') is None:
        continue
    ucg = f"{int(pr['UCG']):02d}"
    nombre = bonito(pr.get('NOMBRE'))
    if not nombre:
        continue
    porucg[ucg].append({'type': 'Feature',
                        'properties': {'barrio': nombre, 'comuna': ucg},
                        'geometry': ft['geometry']})
    try:
        g = shape(ft['geometry']).buffer(0)
    except Exception:
        continue
    if g.is_empty:
        continue
    figuras.append(g)
    nombres_fig.append(nombre)
    ucgs_fig.append(ucg)
    por_nombre.setdefault(norm(pr.get('NOMBRE')), (nombre, ucg))

os.makedirs(SAL_DIR, exist_ok=True)
for viejo in os.listdir(SAL_DIR):
    if viejo.endswith('.js'):
        os.remove(os.path.join(SAL_DIR, viejo))
total_kb = 0
for ucg in sorted(porucg):
    fc = {'type': 'FeatureCollection', 'features': porucg[ucg]}
    ruta = os.path.join(SAL_DIR, f'{ucg}.js')
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write('window.Candidato360CartagenaBarrios=window.Candidato360CartagenaBarrios||{};'
                f'window.Candidato360CartagenaBarrios["{ucg}"]=')
        json.dump(fc, f, ensure_ascii=False, separators=(',', ':'))
        f.write(';\n')
    total_kb += os.path.getsize(ruta) / 1024
print(f'{sum(len(v) for v in porucg.values())} barrios en {len(porucg)} UCG '
      f'· {total_kb:.0f} KB → {SAL_DIR}')

# ── puesto → barrio ─────────────────────────────────────────────────────────
tree = STRtree(figuras)
dic, cuenta, discrepan = {}, collections.Counter(), []
with open(GEOREF, encoding='utf-8-sig') as f:
    for row in csv.DictReader(f, delimiter=';'):
        code = (row.get('CÓDIGO COMPLETO') or '').strip()
        if code[:5] != '05001':
            continue
        ucg = ucg_de_puesto.get(code)          # la UCG manda: sale del otro builder
        try:
            pt = Point(float(row['LONGITUD']), float(row['LATITUD']))
        except (ValueError, TypeError, KeyError):
            pt = None
        barrio = ''
        origen = ''
        if pt is not None:
            for j in tree.query(pt):
                if figuras[j].covers(pt):
                    barrio, origen = nombres_fig[j], 'pip'
                    break
            if not barrio:
                j = tree.nearest(pt)
                if figuras[j].distance(pt) * 111320 <= TOPE_M:
                    barrio, origen = nombres_fig[j], 'vecino'
                    j_ucg = ucgs_fig[j]
        if not barrio:
            hit = por_nombre.get(norm(row.get('BARRIO')))
            if hit:
                barrio, origen = hit[0], 'nombre'
        if barrio:
            cuenta[origen] += 1
            propia = next(u for n, u in zip(nombres_fig, ucgs_fig) if n == barrio)
            if ucg and propia != ucg:
                discrepan.append((code, barrio, propia, ucg))
        elif ucg:
            cuenta['solo-ucg'] += 1
        else:
            cuenta['sin'] += 1
            continue
        valor = {'comuna': ucg or ''}
        if barrio:
            valor['barrio'] = barrio
        dic[code] = valor

with open(SAL_DIC, 'w', encoding='utf-8') as f:
    f.write('window.Candidato360CartagenaPuestoBarrio=')
    json.dump(dic, f, ensure_ascii=False, separators=(',', ':'))
    f.write(';\n')
print(f'{len(dic)} puestos · {dict(cuenta)} · {os.path.getsize(SAL_DIC)/1024:.0f} KB → {SAL_DIC}')
if discrepan:
    print(f'⚠️  {len(discrepan)} puestos donde el barrio cae en otra UCG que la del '
          f'archivo de UCG (manda el archivo):')
    for code, barrio, propia, ucg in discrepan[:10]:
        print(f'   {code} · {barrio} · barrio en UCG {propia} · puesto en UCG {ucg}')
