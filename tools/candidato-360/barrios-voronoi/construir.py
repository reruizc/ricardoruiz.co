#!/usr/bin/env python3
"""
construir.py — barrios por Voronoi para las ciudades SIN cartografía barrial.
═══════════════════════════════════════════════════════════════════════════
Ibagué y Montería tienen comunas publicadas (IBAGUEX.json, MONTERIAX.json)
pero ningún GeoJSON de barrios en ninguna fuente que se alcance. Lo que sí
hay, para cada puesto de votación, es su coordenada y el barrio que la
Registraduría le asigna (PUESTOS_GEOREF.csv). Con eso se hace lo mismo que
el proyecto hizo para Medellín antes de tener la capa oficial
(tools/build-barrios-voronoi.py): cada puesto se queda con el área que le
queda más cerca (Voronoi), las celdas del mismo barrio se unen, y cada barrio
queda con nombre, comuna y cuántos puestos lo forman.

Dos diferencias con el de Medellín:
  · cada celda se recorta a SU comuna, no solo al contorno de la ciudad, así
    ningún barrio cruza un límite de comuna (el CRM los pinta por comuna);
  · los puestos de corregimientos, que no tienen polígono de comuna, se
    recortan al contorno del municipio y se marcan como tales.

NO es cartografía oficial: el límite de cada barrio es el punto medio entre
sus puestos y los de los vecinos. Sirve para ubicar la votación y repartir la
meta; no para discutir dónde termina un barrio. Va con ese aviso en el
archivo y en la nota del mapa.

    python3 tools/candidato-360/barrios-voronoi/construir.py            (ambas)
    python3 tools/candidato-360/barrios-voronoi/construir.py ibague

Necesita numpy, scipy y shapely.  Escribe candidato-360-data/barrios-voronoi/.
"""
import csv, json, sys, io, urllib.request
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import Polygon, shape, mapping
from shapely.ops import unary_union

RAIZ = Path(__file__).resolve().parents[3]
S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output'
SALIDA = RAIZ / 'candidato-360-data' / 'barrios-voronoi'

CIUDADES = {
    'ibague':   {'prefijo': '29001', 'capa': 'IBAGUEX.json',   'nombre': 'IBAGUE',
                 'comuna_de': lambda p: ''.join(ch for ch in str(p.get('COMUNAS', '')) if ch.isdigit()).zfill(2)},
    'monteria': {'prefijo': '13001', 'capa': 'MONTERIAX.json', 'nombre': 'MONTERIA',
                 'comuna_de': lambda p: str(p.get('CC_COMUNA', '')).strip().zfill(2)},
}

def baja(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'curl/8.0'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()

def normaliza(s):
    return ' '.join(str(s or '').strip().upper().split())

# La Registraduría escribe el mismo barrio de varias formas en distintos
# puestos: «BARRIO LA PRADERA» y «LA PRADERA», «EL DORADO» y «DORADO». La llave
# quita el prefijo de tipo y el artículo inicial para que caigan juntos; el
# nombre que se muestra es el primero que aparece, sin el «BARRIO » delante.
import re, unicodedata
def llave_barrio(s):
    n = unicodedata.normalize('NFD', normaliza(s)).encode('ascii', 'ignore').decode()
    n = re.sub(r'^(BARRIO|BARRIOS|B\.|URBANIZACION|URB\.|URB|CONJUNTO|CIUDADELA|SECTOR)\s+', '', n)
    n = re.sub(r'^(EL|LA|LOS|LAS)\s+', '', n)
    return re.sub(r'[^A-Z0-9 ]+', ' ', n).strip()
def nombre_barrio(s):
    return re.sub(r'^(BARRIO|B\.)\s+', '', normaliza(s), flags=re.I).title()

def puestos_de(prefijo, csv_texto):
    lector = csv.reader(io.StringIO(csv_texto), delimiter=';')
    next(lector, None)
    salida = []
    for fila in lector:
        if len(fila) < 15 or not str(fila[1]).startswith(prefijo):
            continue
        try:
            lat, lon = float(fila[9]), float(fila[10])
        except ValueError:
            continue
        barrio = fila[7].strip()
        if not barrio:
            continue
        salida.append({'codigo': fila[1], 'lat': lat, 'lon': lon, 'barrio': barrio, 'llave': llave_barrio(barrio),
                       'comuna': str(fila[11] or '').strip().zfill(2), 'comuna_nombre': fila[12].strip(),
                       'censo': (int(fila[13] or 0) + int(fila[14] or 0))})
    return salida

def celdas_voronoi(puntos, caja):
    """Celdas finitas: se añaden cuatro puntos lejanos para cerrar las del borde."""
    x0, y0, x1, y1 = caja
    dx, dy = (x1 - x0) * 3, (y1 - y0) * 3
    lejos = np.array([[x0 - dx, y0 - dy], [x1 + dx, y0 - dy], [x0 - dx, y1 + dy], [x1 + dx, y1 + dy]])
    vor = Voronoi(np.vstack([puntos, lejos]))
    celdas = []
    for i in range(len(puntos)):
        region = vor.regions[vor.point_region[i]]
        if not region or -1 in region:
            celdas.append(None); continue
        poligono = Polygon([vor.vertices[v] for v in region])
        celdas.append(poligono if poligono.is_valid else poligono.buffer(0))
    return celdas

def construir(clave):
    cfg = CIUDADES[clave]
    print(f'· {clave}: puestos…', end=' ', flush=True)
    csv_texto = baja(f'{S3}/mapas-2026/PUESTOS_GEOREF.csv').decode('utf-8', 'replace')
    puestos = puestos_de(cfg['prefijo'], csv_texto)
    capa = json.loads(baja(f"{S3}/mapas-2026/Ciudades-COM-LOC/{cfg['capa']}"))
    por_comuna = defaultdict(list)
    for f in capa['features']:
        try:
            por_comuna[cfg['comuna_de'](f['properties'])].append(shape(f['geometry']))
        except Exception:
            continue
    comunas = {k: unary_union(v) for k, v in por_comuna.items()}
    contorno = unary_union(list(comunas.values()))
    print(f'{len(puestos)} con coordenada · {len(comunas)} comunas con polígono')

    # Un puesto que dice comuna 06 pero cae dentro del polígono de la 07 se
    # queda con la 07: manda la geometría, que es lo que el mapa dibuja.
    # La capa de comunas tiene huecos entre polígonos y bordes imprecisos: un
    # puesto puede caer a 300 m de su comuna sin estar en ninguna otra. Ahí
    # manda la comuna MÁS CERCANA (hasta 400 m), y la celda de ese puesto se
    # recorta a la comuna ensanchada lo justo para que el puesto quede dentro
    # de su propio barrio; si no, el CRM no lo encontraría por coordenada.
    from shapely.geometry import Point
    MAX_M = 400
    for p in puestos:
        punto = Point(p['lon'], p['lat'])
        dentro = next((k for k, g in comunas.items() if g.contains(punto)), None)
        if dentro:
            p['comuna_geo'], p['holgura'] = dentro, 0.0
        else:
            k, d = min(((k, g.distance(punto)) for k, g in comunas.items()), key=lambda x: x[1])
            if d * 111000 <= MAX_M:
                p['comuna_geo'], p['holgura'] = k, d + 0.0001      # la distancia más ~10 m
            else:
                p['comuna_geo'], p['holgura'] = '', 0.0

    puntos = np.array([[p['lon'], p['lat']] for p in puestos])
    celdas = celdas_voronoi(puntos, contorno.bounds)

    # Los puestos de corregimiento —fuera de todo polígono de comuna— no
    # entran: su celda recortada al contorno urbano daba una astilla en el
    # borde de la ciudad, un barrio rural dibujado donde no está. El CRM
    # solo abre barrios desde una comuna, así que tampoco los necesitaría.
    fuera = [p for p in puestos if not p['comuna_geo']]
    por_barrio, meta = defaultdict(list), {}
    for p, celda in zip(puestos, celdas):
        if celda is None or celda.is_empty or not p['comuna_geo']:
            continue
        recorte = comunas[p['comuna_geo']].buffer(p['holgura']) if p['holgura'] else comunas[p['comuna_geo']]
        pieza = celda.intersection(recorte)
        if pieza.is_empty:
            continue
        llave = (p['comuna_geo'] or 'XX') + '|' + p['llave']     # el mismo nombre en dos comunas son dos barrios
        por_barrio[llave].append(pieza)
        m = meta.setdefault(llave, {'nombre': nombre_barrio(p['barrio']), 'comuna': p['comuna_geo'], 'comuna_nombre': p['comuna_nombre'],
                                    'n_puestos': 0, 'censo': 0, 'puestos': []})
        m['n_puestos'] += 1; m['censo'] += p['censo']; m['puestos'].append(p['codigo'])

    features = []
    for llave, piezas in por_barrio.items():
        union = unary_union(piezas)
        if union.geom_type == 'GeometryCollection':
            union = unary_union([g for g in union.geoms if g.geom_type in ('Polygon', 'MultiPolygon')])
        if union.is_empty:
            continue
        m = meta[llave]
        features.append({'type': 'Feature', 'properties': {
            'CODIGO': llave.replace('|', '-'), 'NOMBRE': m['nombre'], 'COMUNA': m['comuna'], 'COMUNA_NOMBRE': m['comuna_nombre'],
            'N_PUESTOS': m['n_puestos'], 'CENSO': m['censo'], 'PUESTOS': m['puestos'],
        }, 'geometry': mapping(union.simplify(0.00002, preserve_topology=True))})   # ~2 m: no mueve un puesto fuera de su celda

    fc = {'type': 'FeatureCollection', 'name': f"{cfg['nombre']}_BARRIOS_VORONOI",
          'metadata': {'fuente': 'Aproximación Voronoi sobre PUESTOS_GEOREF.csv, recortada por comuna',
                       'disclaimer': 'NO es cartografía oficial. Cada polígono es el área más cercana a los puestos de votación de ese barrio; los límites no coinciden con los administrativos.',
                       'n_features': len(features), 'n_puestos': len(puestos) - len(fuera), 'puestos_de_corregimiento_omitidos': [p['codigo'] for p in fuera]},
          'features': features}
    SALIDA.mkdir(parents=True, exist_ok=True)
    destino = SALIDA / f"{cfg['nombre']}-BARRIOS.json"
    destino.write_text(json.dumps(fc, ensure_ascii=False, separators=(',', ':')))
    print(f"  ✓ {destino.relative_to(RAIZ)} · {len(features)} barrios · {destino.stat().st_size / 1024:.0f} KB · {len(fuera)} puestos de corregimiento omitidos (fuera de toda comuna)")

if __name__ == '__main__':
    for clave in (sys.argv[1:] or list(CIUDADES)):
        construir(clave)
