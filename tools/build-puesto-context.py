#!/usr/bin/env python3
"""
tools/build-puesto-context.py

Construye el "contexto" territorial de cada puesto en las 14 ciudades
soportadas por el módulo Oportunidad. Para cada puesto incluye su
comuna/localidad (PUESTOS_GEOREF.csv) y, para Bogotá, también la UPL
(point-in-polygon contra BOG-UPL.geojson).

Output: puesto-context.json (formato compacto)
  { 'dd-mm-zz-pp': { com_cod, com_nombre, upl_cod?, upl_nombre? } }

Uso:
  python3 tools/build-puesto-context.py \
    "Bases de datos/PUESTOS_GEOREF.csv" \
    "CIUDADES/BOGOTA/BOG-UPL.geojson" \
    "Bases de datos"
"""

import csv, json, os, sys, re

# Las 14 ciudades del módulo. Códigos electorales (mismo que en oportunidad.html).
CITIES = {
    'medellin':      ('01', '001'), 'bogota':        ('16', '001'),
    'cali':          ('31', '001'), 'barranquilla':  ('03', '001'),
    'ibague':        ('29', '001'), 'manizales':     ('09', '001'),
    'pereira':       ('24', '001'), 'monteria':      ('13', '001'),
    'bucaramanga':   ('27', '001'), 'cucuta':        ('25', '001'),
    'neiva':         ('19', '001'), 'popayan':       ('11', '001'),
    'sincelejo':     ('28', '001'), 'villavicencio': ('52', '001'),
}
# Reverse lookup: depCod → cityKey
DEP_TO_CITY = {dep: k for k, (dep, _) in CITIES.items()}


def pad2(s): return str(s).zfill(2)
def pad3(s): return str(s).zfill(3)


def point_in_ring(x, y, ring):
    inside = False
    n = len(ring); j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and \
           (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def point_in_feature(x, y, geom):
    polys = [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']
    for poly in polys:
        if not poly or not point_in_ring(x, y, poly[0]): continue
        in_hole = any(point_in_ring(x, y, ring) for ring in poly[1:])
        if not in_hole: return True
    return False


def feature_bbox(geom):
    minx, miny, maxx, maxy = 1e9, 1e9, -1e9, -1e9
    polys = [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']
    for poly in polys:
        for ring in poly:
            for x, y in ring:
                if x < minx: minx = x
                if x > maxx: maxx = x
                if y < miny: miny = y
                if y > maxy: maxy = y
    return minx, miny, maxx, maxy


def clean_com_name(raw):
    """ '01COMUNA 1 POPULAR' o '01LOCALIDAD 1 USAQUEN' → solo el nombre. """
    if not raw: return ''
    raw = re.sub(r'^\d+\s*', '', raw)
    return re.sub(r'\s+', ' ', raw.strip()).title()


def main():
    if len(sys.argv) < 4:
        print('Uso: build-puesto-context.py <PUESTOS_GEOREF.csv> <BOG-UPL.geojson> <out-dir>', file=sys.stderr)
        sys.exit(1)
    csv_path, upl_path, out_dir = sys.argv[1:4]
    os.makedirs(out_dir, exist_ok=True)

    # 1) PUESTOS_GEOREF → mapping (dep,mun,zz,pp) → context
    context = {}
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';')
        header = next(reader); header[0] = header[0].replace('﻿', '')
        col = lambda n: next(i for i, h in enumerate(header) if h.strip().upper() == n.upper())
        iDep = col('DEPARTAMENTO'); iMun = col('MUNICIPIO')
        iZon = col('ZONA'); iPue = col('PUESTO')
        iLat = col('LATITUD'); iLon = col('LONGITUD')
        iComCod = col('CÓDIGO COMUNA'); iComNom = col('NOMBRE COMUNA')
        iBarrio = col('BARRIO'); iNomPue = col('NOMBRE PUESTO')

        # Map nombre dep/mun → código electoral usando heurística:
        # 14 ciudades = nombre depto/mun conocido.
        DEP_NAME_HINTS = {
            'BOGOTA': '16', 'ANTIOQUIA': '01', 'VALLE': '31', 'ATLANTICO': '03',
            'TOLIMA': '29', 'CALDAS': '09', 'RISARALDA': '24', 'CORDOBA': '13',
            'SANTANDER': '27', 'NORTE': '25', 'HUILA': '19', 'CAUCA': '11',
            'SUCRE': '28', 'META': '52',
        }
        for row in reader:
            if not row or len(row) <= iLon: continue
            dep_raw = (row[iDep] or '').upper()
            mun_raw = (row[iMun] or '').upper()
            # Match a una de las 14 ciudades por nombre dep + mun = capital.
            dep_cod = None
            for hint, code in DEP_NAME_HINTS.items():
                if hint in dep_raw:
                    dep_cod = code; break
            if not dep_cod: continue
            # Mun debe ser capital. Verificamos contra CITIES.
            cfg = CITIES.get(DEP_TO_CITY.get(dep_cod))
            if not cfg: continue
            _, mun_cod = cfg
            # Solo capitales — el primer puesto de cada ciudad debería
            # llevar el nombre canónico (Medellín, Bogotá D.C., etc.).
            # PUESTOS_GEOREF a veces mete varios municipios bajo el mismo
            # depto; filtramos por mun_cod después de calcular zz-pp.
            zz = pad2(row[iZon]); pp = pad2(row[iPue])
            key = f'{dep_cod}-{mun_cod}-{zz}-{pp}'
            com_cod = pad2(row[iComCod]) if row[iComCod] else ''
            com_nom = clean_com_name(row[iComNom])
            try:
                lat = float((row[iLat] or '').replace(',', '.'))
                lon = float((row[iLon] or '').replace(',', '.'))
            except ValueError:
                lat, lon = None, None
            context[key] = {
                'com_cod': com_cod,
                'com_nombre': com_nom,
                'puesto_nombre': row[iNomPue] or '',
                'barrio': row[iBarrio] or '',
                'lat': lat, 'lon': lon,
            }
    print(f'[1] {len(context)} puestos cargados de las 14 ciudades')

    # 2) UPL Bogotá: point-in-polygon
    upl_geo = json.load(open(upl_path))
    upls = []
    for f in upl_geo['features']:
        cod = f['properties'].get('CODIGO_UPL')
        if not cod: continue
        upls.append((cod, f['properties'].get('NOMBRE', ''),
                     feature_bbox(f['geometry']), f['geometry']))
    nUpl = 0
    for key, ctx in context.items():
        if not key.startswith('16-001-'): continue
        if ctx['lat'] is None or ctx['lon'] is None: continue
        x, y = ctx['lon'], ctx['lat']
        for cod, nombre, bb, geom in upls:
            if x < bb[0] or x > bb[2] or y < bb[1] or y > bb[3]: continue
            if point_in_feature(x, y, geom):
                ctx['upl_cod'] = cod
                ctx['upl_nombre'] = nombre
                nUpl += 1
                break
    print(f'[2] {nUpl}/{sum(1 for k in context if k.startswith("16-001-"))} puestos de Bogotá asignados a UPL')

    # 3) Output compacto: solo los campos que el frontend usa.
    compact = {}
    for k, v in context.items():
        c = {}
        if v.get('com_cod'):     c['com_cod']     = v['com_cod']
        if v.get('com_nombre'):  c['com_nombre']  = v['com_nombre']
        if v.get('barrio'):      c['barrio']      = v['barrio']
        if v.get('upl_cod'):     c['upl_cod']     = v['upl_cod']
        if v.get('upl_nombre'):  c['upl_nombre']  = v['upl_nombre']
        compact[k] = c
    out_path = os.path.join(out_dir, 'puesto-context.json')
    json.dump(compact, open(out_path, 'w'), separators=(',', ':'))
    print(f'✓ {out_path} ({os.path.getsize(out_path)/1024:.0f} KB · {len(compact)} entries)')


if __name__ == '__main__':
    main()
