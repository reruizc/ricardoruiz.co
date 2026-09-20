#!/usr/bin/env python3
"""Cartagena por Unidad Comunera de Gobierno: la capa y el mapa puesto → UCG.

Emite DOS archivos:
  · CARTAGENA-UCG.json        las 16 UCG disueltas, para pintar el mapa.
  · cartagena-puesto-ucg.json {pcode: UCG}, para que los builders sepan a qué
                              unidad pertenece cada puesto.

El segundo existe porque la UCG NO está en el georef —ahí solo van las 3
localidades— y hay dos builders que la necesitan (`build_territorial_resultados`
y `build_territorial_comuna_detalle`). Resolverla por PIP en cada uno sería
tener la misma cuenta en dos sitios y que un día dejen de coincidir.

`CARTAGENAX.json` trae 213 polígonos de BARRIO con el campo `UCG`. Sirve para
saber a qué comunera pertenece cada uno, pero no para pintar un mapa por
comuna: serían 213 polígonos con 16 colores y 13 tooltips distintos diciendo lo
mismo. Acá se fusionan por `UCG` y queda una capa de 16, que es la que el mapa
del panel 07 espera (una unidad, un polígono, un dato).

La UCG 20 es la RURAL e insular: Barú, Bocachica, Tierra Bomba, Islas del
Rosario, Isla Fuerte, Pasacaballos, Bayunca, La Boquilla, Santa Ana… No es un
error de numeración, es cómo el Distrito agrupa sus corregimientos.
"""
import csv, json, os, urllib.request, collections
from shapely.geometry import shape, mapping, Point
from shapely.ops import unary_union
from shapely.strtree import STRtree

S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/mapas-2026/Ciudades-COM-LOC'
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BD = os.path.join(RAIZ, 'Bases de datos')
SAL = os.path.join(BD, 'output_hvp', 'CARTAGENA-UCG.json')
SAL_PUESTOS = os.path.join(BD, 'output_hvp', 'cartagena-puesto-ucg.json')
GEOREF = os.path.join(BD, 'PUESTOS_GEOREF.csv')
# La UCG rural, a la que pertenecen por definición los puestos de zona 99.
RURAL = 20
# Tope para pegar un puesto urbano al polígono más cercano cuando cae en un
# vacío del mapa (una vía, un centro comercial). Medido: los cuatro casos de
# Cartagena están entre 39 y 252 m.
TOPE_M = 1000

geo = json.load(urllib.request.urlopen(f'{S3}/CARTAGENAX.json', timeout=180))
grupos, locs = collections.defaultdict(list), {}
for ft in geo['features']:
    p = ft.get('properties') or {}
    u = p.get('UCG')
    if u is None:
        continue
    try:
        g = shape(ft['geometry'])
    except Exception:
        continue
    if g.is_empty:
        continue
    grupos[int(u)].append(g.buffer(0))      # buffer(0) limpia auto-intersecciones
    locs.setdefault(int(u), p.get('LOC'))

feats = []
for u in sorted(grupos):
    fusion = unary_union(grupos[u])
    feats.append({'type': 'Feature',
                  'properties': {'UCG': u, 'CODIGO': f'{u:02d}',
                                 'NOMBRE': f'UCG {u}' if u != 20 else 'UCG 20 · rural e insular',
                                 'LOC': locs.get(u), 'BARRIOS': len(grupos[u])},
                  'geometry': mapping(fusion)})

os.makedirs(os.path.dirname(SAL), exist_ok=True)
with open(SAL, 'w', encoding='utf-8') as f:
    json.dump({'type': 'FeatureCollection', 'features': feats}, f,
              ensure_ascii=False, separators=(',', ':'))
print(f'{len(feats)} UCG · {os.path.getsize(SAL)/1024:.0f} KB → {SAL}')

# ── puesto → UCG ────────────────────────────────────────────────────────────
# Cascada: PIP exacto → zona 99 a la UCG rural → barrio vecino a menos de
# TOPE_M → nombre del barrio que le pone el georef. La última capa existe por
# el Coliseo Bernardo Caraballo (5.479 votos), georreferenciado a 3,5 km de la
# ciudad: su coordenada está mal pero su barrio, Torices, lo ubica.
barrios, ucgs, por_nombre = [], [], {}
norm = lambda x: ''.join(c for c in (x or '').upper().strip() if c.isalnum() or c == ' ')
for ft in geo['features']:
    pr = ft.get('properties') or {}
    if pr.get('UCG') is None:
        continue
    try:
        g = shape(ft['geometry'])
    except Exception:
        continue
    if g.is_empty:
        continue
    barrios.append(g); ucgs.append(int(pr['UCG']))
    por_nombre.setdefault(norm(pr.get('NOMBRE')), int(pr['UCG']))
tree = STRtree(barrios)

mapa, cuenta = {}, collections.Counter()
with open(GEOREF, encoding='utf-8-sig') as f:
    for row in csv.DictReader(f, delimiter=';'):
        code = (row.get('CÓDIGO COMPLETO') or '').strip()
        if code[:5] != '05001':
            continue
        try:
            pt = Point(float(row['LONGITUD']), float(row['LATITUD']))
        except (ValueError, TypeError, KeyError):
            pt = None
        u = None
        if pt is not None:
            for j in tree.query(pt):
                if barrios[j].covers(pt):
                    u = ucgs[j]; cuenta['pip'] += 1; break
        if u is None and code[5:7] == '99':
            u = RURAL; cuenta['rural'] += 1
        elif u is None and pt is not None:
            j = tree.nearest(pt)
            if barrios[j].distance(pt) * 111320 <= TOPE_M:
                u = ucgs[j]; cuenta['vecino'] += 1
        if u is None:
            u = por_nombre.get(norm(row.get('BARRIO')))
            if u is not None:
                cuenta['nombre'] += 1
        if u is None:
            cuenta['sin'] += 1
            continue
        mapa[code] = f'{u:02d}'
with open(SAL_PUESTOS, 'w', encoding='utf-8') as f:
    json.dump(mapa, f, separators=(',', ':'))
print(f'{len(mapa)} puestos → UCG  ({dict(cuenta)})  → {SAL_PUESTOS}')
for ft in feats:
    p = ft['properties']
    print(f"  UCG {p['UCG']:>2} · {p['BARRIOS']:>3} barrios · loc {p['LOC']}")
