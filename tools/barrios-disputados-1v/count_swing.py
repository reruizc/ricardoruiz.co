#!/usr/bin/env python3
"""Cuenta barrios DISPUTADOS (swing/veleta) por ciudad: |Cepeda% - Abelardo%| pequeño.

Reusa la mecánica de tools/pacto-1v-2026/build_maps.py (puesto -> barrio por
sjoin_nearest sobre la capa catastral real). Margen en puntos sobre votos
validos (todos los candidatos + blanco). Reporta conteos a varios umbrales
para decidir el corte final.
"""
import json, sys
import geopandas as gpd
from shapely.geometry import Point

ROOT = '/Users/ricardoruiz/ricardoruiz.co'
GEO  = f'{ROOT}/Bases de datos/output_pacto_1v_2026/geo'
MASTER = f'{ROOT}/Bases de datos/output_pacto_1v_2026/master_2026_puesto.json'

CAND = ['cepeda','abelardo','paloma','fajardo','botero','lizcano','miguel_uribe',
        'macollins','roy','murillo','caicedo','matamoros','claudia']

MED_URBAN = {'Aranjuez','Belén','Buenos Aires','Castilla','Doce de Octubre','El Poblado',
             'Guayabal','La América','La Candelaria','Laureles Estadio','Manrique','Popular',
             'Robledo','San Javier','Santa Cruz','Villa Hermosa'}

# name, code(dep+mun), geojson, namefield, bbox, comuna_field, urban_set
CITIES = [
    ('Bogotá',      '16001','BOG-BARRIOS-CATASTRALES.json','nombre',(-74.35,4.3,-73.9,4.95), None, None),
    ('Medellín',    '01001','MEDELLIN_BARRIOS_OFICIAL.json','NOMBRE',(-75.75,6.1,-75.45,6.40),'COMUNA',MED_URBAN),
    ('Cali',        '31001','CALI-BARRIOS.json','barrio',(-76.60,3.30,-76.42,3.52), None, None),
    ('Barranquilla','03001','BARRANQUILLA-BARRIOS.json','NOMBRE',(-74.92,10.88,-74.74,11.12), None, None),
    ('Cartagena',   '05001','CARTAGENA-BARRIOS.json','NOMBRE',(-75.58,10.33,-75.45,10.50), None, None),
    ('Manizales',   '09001','MANIZALES-BARRIOS.json','BARRIOS',(-75.57,5.00,-75.41,5.12), None, None),
    ('Pereira',     '24001','PEREIRA-BARRIOS.json','NOMBRE',(-75.78,4.76,-75.64,4.84), None, None),
    ('Bucaramanga', '27001','BUCARAMANGA-BARRIOS.json','barrio',(-73.18,7.04,-73.08,7.19), None, None),
    ('Cúcuta',      '25001','CUCUTA-BARRIOS.json','barrio',(-72.57,7.84,-72.45,7.97), None, None),
    ('Soledad',     '03052','SOLEDAD-BARRIOS.json','barrio',(-74.84,10.86,-74.74,10.95), None, None),
    ('Popayán',     '11001','POPAYAN-BARRIOS.json','BARRIOS',(-76.66,2.40,-76.53,2.51), None, None),
]

THRESHOLDS = [1, 2, 3, 5]

print('cargando master_2026_puesto.json ...', file=sys.stderr)
d26 = json.load(open(MASTER))

def city_puestos(dep, mun, bbox):
    rows = []
    for p in d26:
        if str(p.get('dep','')).zfill(2) != dep or str(p.get('mun','')).zfill(3) != mun:
            continue
        try: lat = float(p['lat']); lon = float(p['lon'])
        except: continue
        if bbox and not (bbox[0] < lon < bbox[2] and bbox[1] < lat < bbox[3]):
            continue
        base = sum(int(p.get(c,0) or 0) for c in CAND) + int(p.get('votos_blanco',0) or 0)
        rows.append({'cep': int(p.get('cepeda',0) or 0),
                     'abe': int(p.get('abelardo',0) or 0),
                     'base': base, 'geometry': Point(lon, lat)})
    return gpd.GeoDataFrame(rows, crs='EPSG:4326')

hdr = f"{'Ciudad':<14}{'barrios':>9}{'Cepeda':>8}{'Abel.':>7}" + ''.join(('≤%dpp' % t).rjust(7) for t in THRESHOLDS)
print(hdr); print('-'*len(hdr))

GRAND = {t: 0 for t in THRESHOLDS}; gtot = 0; gcep = 0; gabe = 0
for name, code, gj, nf, bbox, cfield, uset in CITIES:
    dep, mun = code[:2], code[2:]
    cols = [nf, 'geometry'] + ([cfield] if cfield else [])
    bar = gpd.read_file(f'{GEO}/{gj}')[cols].to_crs('EPSG:4326').rename(columns={nf: 'NB'})
    if cfield and uset is not None:
        bar = bar[bar[cfield].isin(uset)].copy()
    pts = city_puestos(dep, mun, bbox)
    if not len(pts):
        print(f'{name:<14}  sin puestos'); continue
    j = gpd.sjoin_nearest(pts, bar[['NB','geometry']], how='left')
    j = j[~j.index.duplicated(keep='first')]
    agg = j.groupby('NB').agg(cep=('cep','sum'), abe=('abe','sum'), base=('base','sum')).reset_index()
    agg = agg[agg['base'] > 0].copy()
    agg['margin'] = (agg['cep'] - agg['abe']) / agg['base'] * 100  # +Cepeda / -Abelardo
    nbar = len(agg)
    ncep = int((agg['margin'] > 0).sum())
    nabe = int((agg['margin'] < 0).sum())
    counts = {t: int((agg['margin'].abs() <= t).sum()) for t in THRESHOLDS}
    for t in THRESHOLDS: GRAND[t] += counts[t]
    gtot += nbar; gcep += ncep; gabe += nabe
    print(f'{name:<14}{nbar:>9}{ncep:>8}{nabe:>7}' + ''.join(f'{counts[t]:>7}' for t in THRESHOLDS))

print('-'*len(hdr))
print(f"{'TOTAL':<14}{gtot:>9}{gcep:>8}{gabe:>7}" + ''.join(f'{GRAND[t]:>7}' for t in THRESHOLDS))
print('\nMargen = (Cepeda% - Abelardo%) sobre votos válidos (cand + blanco), por barrio (dato directo).')
