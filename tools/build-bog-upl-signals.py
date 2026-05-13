#!/usr/bin/env python3
"""
tools/build-bog-upl-signals.py

Genera los datos electorales por UPL (Unidad de Planeamiento Local) para
Bogotá, replicando el patrón de Medellín · Barrios. Para cada UPL agrega
las 10 señales históricas y modernas del módulo Oportunidad usando un
point-in-polygon que asocia cada puesto de votación a su UPL.

Outputs (10 archivos):
  output_ciudades/bogota/<sig>-upl.json
    { por_upl: { UPLxx: { upl_cod, nombre, sector, votos_validos,
                          candidatos: [{nombre, votos, pct}], n_puestos } } }

Mapeos:
  - Bogotá depto/mun electoral: 16-001
  - Puestos clave (DD-MMM-ZZ-PP): siempre dep=16, mun=001
  - UPL features: BOG-UPL.geojson (32 UPL)

Uso:
  python3 tools/build-bog-upl-signals.py \
    "Bases de datos/PUESTOS_GEOREF.csv" \
    "CIUDADES/BOGOTA/BOG-UPL.geojson" \
    "Bases de datos/output_ciudades/bogota"
"""

import csv, json, os, sys, re, urllib.request
from collections import defaultdict
from typing import Optional

S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output'

# Las 10 señales que el módulo Oportunidad usa para ciudades. Mismas que
# CITY_SIGNALS en oportunidad.html. Format: 'nac-pres' usa codCan; 'nac-consulta'
# usa nombre directo; 'cong-2026' es array de objetos.
SIGNALS = [
    ('pres-2010',                'nac-pres',     f'{S3}/historicos/pres-2010-v1/por-puesto.json'),
    ('pres-2014',                'nac-pres',     f'{S3}/historicos/pres-2014-v1/por-puesto.json'),
    ('pres-2018',                'nac-pres',     f'{S3}/historicos/pres-2018-v1/por-puesto.json'),
    ('pres-2022',                'nac-pres',     f'{S3}/historicos/pres-2022-v1/por-puesto.json'),
    ('consulta-2025-pacto',      'nac-consulta', f'{S3}/historicos/consulta-2025-pacto/por-puesto.json'),
    ('consulta-2026-gran',       'nac-consulta', f'{S3}/historicos/consulta-2026-gran/por-puesto.json'),
    ('consulta-2026-frente',     'nac-consulta', f'{S3}/historicos/consulta-2026-frente/por-puesto.json'),
    ('consulta-2026-soluciones', 'nac-consulta', f'{S3}/historicos/consulta-2026-soluciones/por-puesto.json'),
    ('senado-2026',              'cong-2026',    f'{S3}/senado/departamentos/16/puestos.json'),
    ('camara-2026',              'cong-2026',    f'{S3}/camara/departamentos/16/puestos.json'),
]

# Bogotá electoral dep-mun
BOG_DEP, BOG_MUN = '16', '001'
PFX_NAC = f'{BOG_DEP}-{BOG_MUN}-'

CACHE_DIR = '/tmp/bog-upl-cache'


def pad2(s): return str(s).zfill(2)
def pad3(s): return str(s).zfill(3)


def fetch_cached(url: str):
    os.makedirs(CACHE_DIR, exist_ok=True)
    fname = os.path.join(CACHE_DIR, re.sub(r'[^a-zA-Z0-9]+', '_', url) + '.json')
    if os.path.exists(fname) and os.path.getsize(fname) > 100:
        return json.load(open(fname))
    print(f'[fetch] {url}', file=sys.stderr)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    with open(fname, 'wb') as f:
        f.write(data)
    return json.loads(data)


# Ray-casting point-in-polygon. Funciona para Polygon y MultiPolygon GeoJSON.
def point_in_ring(x: float, y: float, ring: list) -> bool:
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        intersect = ((yi > y) != (yj > y)) and \
                    (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi)
        if intersect:
            inside = not inside
        j = i
    return inside


def point_in_feature(x: float, y: float, geom: dict) -> bool:
    if geom['type'] == 'Polygon':
        polys = [geom['coordinates']]
    elif geom['type'] == 'MultiPolygon':
        polys = geom['coordinates']
    else:
        return False
    for poly in polys:
        if not poly: continue
        # poly[0] es el outer ring, resto son holes.
        if not point_in_ring(x, y, poly[0]): continue
        in_hole = False
        for ring in poly[1:]:
            if point_in_ring(x, y, ring):
                in_hole = True; break
        if not in_hole:
            return True
    return False


# Bounding box helper para descartar UPL rápidamente.
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


def load_puestos_bogota(csv_path: str):
    """Filtra puestos de Bogotá y extrae (zz, pp) → (lat, lon, nombre)."""
    out = {}
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';')
        header = next(reader)
        header[0] = header[0].replace('﻿', '')
        def col(name): return next(i for i, h in enumerate(header) if h.strip().upper() == name.upper())
        iDep = col('DEPARTAMENTO'); iMun = col('MUNICIPIO')
        iZon = col('ZONA'); iPue = col('PUESTO')
        iLat = col('LATITUD'); iLon = col('LONGITUD')
        iNom = col('NOMBRE PUESTO')
        for row in reader:
            if not row or len(row) <= iLon: continue
            if 'BOGOTA' not in (row[iDep] or '').upper(): continue
            try:
                lat = float((row[iLat] or '').replace(',', '.'))
                lon = float((row[iLon] or '').replace(',', '.'))
            except ValueError:
                continue
            zz = pad2(row[iZon]); pp = pad2(row[iPue])
            out[f'{zz}-{pp}'] = {'lat': lat, 'lon': lon, 'nombre': row[iNom] or ''}
    return out


def build_puesto_to_upl(puestos: dict, upl_geo: dict):
    """{ zzpp: upl_cod }. Si no matchea ningún polígono, queda sin asignar."""
    # Precompute bbox por UPL
    upls = []
    for f in upl_geo['features']:
        cod = f['properties'].get('CODIGO_UPL')
        if not cod: continue
        bbox = feature_bbox(f['geometry'])
        upls.append((cod, bbox, f['geometry']))
    out = {}
    unmatched = []
    for zzpp, p in puestos.items():
        x, y = p['lon'], p['lat']
        assigned = None
        for cod, bb, geom in upls:
            if x < bb[0] or x > bb[2] or y < bb[1] or y > bb[3]: continue
            if point_in_feature(x, y, geom):
                assigned = cod; break
        if assigned: out[zzpp] = assigned
        else: unmatched.append(zzpp)
    return out, unmatched


def iter_puestos_signal(json_data, fmt: str):
    """[(zzpp, vv, votos_dict)] para los puestos de Bogotá."""
    if fmt == 'nac-pres':
        cands = json_data.get('candidatos', {})
        for k, v in (json_data.get('puestos') or {}).items():
            if not k.startswith(PFX_NAC): continue
            parts = k.split('-')
            zzpp = f'{pad2(parts[2])}-{pad2(parts[3])}'
            votos = {}
            for cod, n in (v.get('v') or {}).items():
                nombre = cands.get(cod, {}).get('nombre')
                if not nombre: continue
                votos[nombre] = votos.get(nombre, 0) + (n or 0)
            yield zzpp, v.get('vv', 0) or 0, votos
    elif fmt == 'nac-consulta':
        for k, v in (json_data.get('puestos') or {}).items():
            if not k.startswith(PFX_NAC): continue
            parts = k.split('-')
            zzpp = f'{pad2(parts[2])}-{pad2(parts[3])}'
            votos = {}
            for nombre, n in (v.get('v') or {}).items():
                votos[nombre] = votos.get(nombre, 0) + (n or 0)
            yield zzpp, v.get('vv', 0) or 0, votos
    elif fmt == 'cong-2026':
        for p in (json_data or []):
            if p.get('dep_cod') != BOG_DEP or p.get('mun_cod') != BOG_MUN: continue
            zzpp = f"{pad2(p.get('zon_cod'))}-{pad2(p.get('pue_cod_raw'))}"
            votos = {}
            for k, n in (p.get('partidos') or {}).items():
                if re.match(r'^99[6-9]$', str(k)): continue  # blanco/nulo/no_marc
                votos[k] = votos.get(k, 0) + (n or 0)
            yield zzpp, p.get('votval', 0) or 0, votos


def main():
    if len(sys.argv) < 4:
        print('Uso: build-bog-upl-signals.py <PUESTOS_GEOREF.csv> <BOG-UPL.geojson> <out-dir>', file=sys.stderr)
        sys.exit(1)
    csv_path, geo_path, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out_dir, exist_ok=True)

    print('[1] cargando puestos de Bogotá…')
    puestos = load_puestos_bogota(csv_path)
    print(f'    {len(puestos)} puestos con coords')

    print('[2] cargando GeoJSON UPL…')
    upl_geo = json.load(open(geo_path))
    upl_info = {f['properties']['CODIGO_UPL']: {
                    'cod': f['properties']['CODIGO_UPL'],
                    'nombre': f['properties'].get('NOMBRE', ''),
                    'sector': f['properties'].get('SECTOR', ''),
                    'vocacion': f['properties'].get('VOCACION', ''),
                    'localidades': f['properties'].get('Localidades', []),
                } for f in upl_geo['features'] if f['properties'].get('CODIGO_UPL')}
    print(f'    {len(upl_info)} UPL')

    print('[3] point-in-polygon puesto → UPL…')
    pue_to_upl, unmatched = build_puesto_to_upl(puestos, upl_geo)
    print(f'    matched: {len(pue_to_upl)}/{len(puestos)} · unmatched: {len(unmatched)}')

    # Procesa cada señal
    print('[4] agregando 10 señales por UPL…')
    for sig, fmt, url in SIGNALS:
        try:
            data = fetch_cached(url)
        except Exception as e:
            print(f'    [err] {sig}: {e}', file=sys.stderr); continue
        # Agrega votos por UPL
        by_upl = defaultdict(lambda: {'vv': 0, 'votos': defaultdict(int), 'n_puestos': 0})
        n_in_bog = 0; n_matched = 0
        for zzpp, vv, votos in iter_puestos_signal(data, fmt):
            n_in_bog += 1
            upl_cod = pue_to_upl.get(zzpp)
            if not upl_cod: continue
            n_matched += 1
            bucket = by_upl[upl_cod]
            bucket['vv'] += vv
            bucket['n_puestos'] += 1
            for k, n in votos.items():
                bucket['votos'][k] += n
        # Shape final
        por_upl = {}
        for cod, b in by_upl.items():
            vv = b['vv']
            cands = [{'nombre': k, 'votos': n, 'pct': round(100 * n / vv, 3) if vv else 0}
                     for k, n in b['votos'].items()]
            cands.sort(key=lambda x: -x['votos'])
            info = upl_info.get(cod, {})
            por_upl[cod] = {
                'cod': cod,
                'nombre': info.get('nombre', ''),
                'sector': info.get('sector', ''),
                'votos_validos': vv,
                'n_puestos': b['n_puestos'],
                'candidatos': cands,
            }
        out_path = os.path.join(out_dir, f'{sig}-upl.json')
        with open(out_path, 'w') as f:
            json.dump({'sig': sig, 'n_upl': len(por_upl), 'por_upl': por_upl,
                       'puestos_bogota_total': n_in_bog,
                       'puestos_asignados_a_upl': n_matched}, f)
        print(f'    ✓ {sig:30s} {len(por_upl):2d} upl · {n_matched}/{n_in_bog} puestos')

    # Diagnóstico
    diag = {'n_puestos_bog': len(puestos),
            'n_matched': len(pue_to_upl),
            'unmatched_zzpp': unmatched[:50],
            'n_unmatched_total': len(unmatched)}
    with open(os.path.join(out_dir, '_diagnostico-upl.json'), 'w') as f:
        json.dump(diag, f, indent=2)
    print(f'\n[diag] {len(pue_to_upl)}/{len(puestos)} puestos matched ({100*len(pue_to_upl)/max(1,len(puestos)):.1f}%)')
    if unmatched: print(f'       primeros sin match: {unmatched[:10]}')


if __name__ == '__main__':
    main()
