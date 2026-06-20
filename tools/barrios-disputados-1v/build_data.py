#!/usr/bin/env python3
"""Construye, por ciudad, un GeoJSON compacto con el resultado Cepeda/Abelardo
por barrio para el mapa de barrios VELETA (disputados).

Cada feature: { nb, c, a, b, f } -> nombre, cepeda, abelardo, base(válidos),
filled(1=heredó vecino). El margen y el color se calculan en el cliente para
que el slider de umbral funcione en vivo.

Salida: Bases de datos/output_barrios_veleta/{slug}.json + index.json
Mismo motor que tools/pacto-1v-2026/build_maps.py (puesto->barrio sjoin_nearest).
"""
import json, os, sys
import geopandas as gpd
from shapely.geometry import Point, mapping

ROOT = '/Users/ricardoruiz/ricardoruiz.co'
GEO  = f'{ROOT}/Bases de datos/output_pacto_1v_2026/geo'
MASTER = f'{ROOT}/Bases de datos/output_pacto_1v_2026/master_2026_puesto.json'
OUT  = f'{ROOT}/Bases de datos/output_barrios_veleta'
os.makedirs(OUT, exist_ok=True)

CAND = ['cepeda','abelardo','paloma','fajardo','botero','lizcano','miguel_uribe',
        'macollins','roy','murillo','caicedo','matamoros','claudia']
SIMP = 0.00014   # tolerancia de simplificación (~15 m); recorta vértices sin deformar
RND  = 5         # decimales en coordenadas

# name, region, slug, code(dep+mun), geojson, namefield, bbox, rotate
CITIES = [
    ('Bogotá',      'Cundinamarca','bogota',      '16001','BOG-BARRIOS-CATASTRALES.json','nombre',(-74.35,4.3,-73.9,4.95), True),
    ('Medellín',    'Antioquia',   'medellin',    '01001','MEDELLIN_BARRIOS_OFICIAL.json','NOMBRE',(-75.75,6.1,-75.45,6.40), False),
    ('Cali',        'Valle',       'cali',        '31001','CALI-BARRIOS.json','barrio',(-76.60,3.30,-76.42,3.52), False),
    ('Barranquilla','Atlántico',   'barranquilla','03001','BARRANQUILLA-BARRIOS.json','NOMBRE',(-74.92,10.88,-74.74,11.12), False),
    ('Cartagena',   'Bolívar',     'cartagena',   '05001','CARTAGENA-BARRIOS.json','NOMBRE',(-75.58,10.33,-75.45,10.50), False),
    ('Cúcuta',      'N. Santander','cucuta',      '25001','CUCUTA-BARRIOS.json','barrio',(-72.57,7.84,-72.45,7.97), False),
    ('Bucaramanga', 'Santander',   'bucaramanga', '27001','BUCARAMANGA-BARRIOS.json','barrio',(-73.18,7.04,-73.08,7.19), False),
    ('Pereira',     'Risaralda',   'pereira',     '24001','PEREIRA-BARRIOS.json','NOMBRE',(-75.78,4.76,-75.64,4.84), False),
    ('Manizales',   'Caldas',      'manizales',   '09001','MANIZALES-BARRIOS.json','BARRIOS',(-75.57,5.00,-75.41,5.12), False),
    # Popayán: capa oficial Alcaldía (ArcGIS Curaduria_2023_WFL1/FeatureServer/2, campo BARRIOS, 450 polys)
    # geo/POPAYAN-BARRIOS.json = curl ".../FeatureServer/2/query?where=1=1&outFields=BARRIOS,Comuna&outSR=4326&f=geojson"
    ('Popayán',     'Cauca',       'popayan',     '11001','POPAYAN-BARRIOS.json','BARRIOS',(-76.66,2.40,-76.53,2.51), False),
    ('Soledad',     'Atlántico',   'soledad',     '03052','SOLEDAD-BARRIOS.json','barrio',(-74.84,10.86,-74.74,10.95), False),
]

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

def round_geom(geom):
    gj = mapping(geom)
    def rr(co):
        if isinstance(co[0], (float, int)):
            return [round(co[0], RND), round(co[1], RND)]
        return [rr(c) for c in co]
    gj['coordinates'] = rr(gj['coordinates'])
    return gj

index = []
for name, region, slug, code, gj, nf, bbox, rotate in CITIES:
    dep, mun = code[:2], code[2:]
    bar = gpd.read_file(f'{GEO}/{gj}')[[nf,'geometry']].to_crs('EPSG:4326').rename(columns={nf:'NB'})
    bar['NB'] = bar['NB'].fillna('').astype(str).str.strip()
    bar = bar[bar['NB'] != ''].reset_index(drop=True)
    pts = city_puestos(dep, mun, bbox)
    j = gpd.sjoin_nearest(pts, bar[['NB','geometry']], how='left')
    j = j[~j.index.duplicated(keep='first')]
    agg = j.groupby('NB').agg(c=('cep','sum'), a=('abe','sum'), b=('base','sum')).reset_index()
    agg = agg[agg['b'] > 0]
    res = {r['NB']: (int(r['c']), int(r['a']), int(r['b'])) for _, r in agg.iterrows()}

    # rellenar barrios huérfanos con el vecino directo más cercano (por centroide)
    bar['rep'] = bar.geometry.representative_point()
    direct_mask = bar['NB'].isin(res)
    have = bar[direct_mask]
    miss = bar[~direct_mask]
    fill = {}
    if len(miss) and len(have):
        hg = gpd.GeoDataFrame({'NB': have['NB'].values}, geometry=have['rep'].values, crs=bar.crs)
        mg = gpd.GeoDataFrame({'_i': list(miss.index)}, geometry=miss['rep'].values, crs=bar.crs)
        jn = gpd.sjoin_nearest(mg, hg, how='left'); jn = jn[~jn['_i'].duplicated(keep='first')]
        for _, r in jn.iterrows():
            fill[r['_i']] = res.get(r['NB'])

    feats = []
    nveleta3 = ncep = nabe = 0; seen = set()
    for idx, row in bar.iterrows():
        nb = row['NB']
        if nb in res:
            c, a, b = res[nb]; f = 0
        elif idx in fill and fill[idx]:
            c, a, b = fill[idx]; f = 1
        else:
            continue  # sin dato ni vecino (raro): se omite del archivo
        feats.append({'type':'Feature',
                      'properties':{'nb': nb, 'c': c, 'a': a, 'b': b, 'f': f},
                      'geometry': round_geom(row.geometry.simplify(SIMP, preserve_topology=True))})
        if f == 0 and b > 0 and nb not in seen:   # conteo por nombre único (= tabla)
            seen.add(nb); m = (c - a) / b * 100
            if abs(m) <= 3: nveleta3 += 1
            elif m > 0: ncep += 1
            else: nabe += 1
    fc = {'type':'FeatureCollection','features':feats}
    path = f'{OUT}/{slug}.json'
    json.dump(fc, open(path,'w'), ensure_ascii=False, separators=(',',':'))
    kb = os.path.getsize(path)//1024
    index.append({'slug':slug,'name':name,'region':region,'rotate':rotate,
                  'nDirect':len(seen),'file':f'{slug}.json'})
    print(f'{name:<13} polys {len(feats):>4} · directos {len(seen):>4} · '
          f'veleta≤3pp {nveleta3:>3} · Cepeda {ncep:>3} · Abelardo {nabe:>3} · {kb} KB')

json.dump({'cities':index,'generated':'1V-2026','cands':['Cepeda','Abelardo']},
          open(f'{OUT}/index.json','w'), ensure_ascii=False, indent=1)
print('\n✓ index.json ·', len(index), 'ciudades ->', OUT)
