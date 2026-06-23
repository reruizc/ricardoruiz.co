#!/usr/bin/env python3
# Datos por barrio para las 4 ciudades principales (Bogotá · Medellín · Barranquilla
# · Cali), 1V y 2V, para el HTML interactivo + las imágenes públicas del hilo.
# Cruza puestos georreferenciados (lat/lon del master) a polígonos de barrio por
# punto-en-polígono (+ vecino más cercano para huérfanos). Emite un ARRAY por
# ciudad alineado al orden de features del GeoJSON, así el frontend colorea cada
# polígono por índice sin ambigüedad de nombres repetidos.
# -> Bases de datos/output_2v/ciudades-barrios-2v.json
import json, collections, warnings, os
import numpy as np, geopandas as gpd, pandas as pd
from shapely.geometry import Point
warnings.filterwarnings('ignore')

OUT = 'Bases de datos/output_2v'
GEO = 'Bases de datos/output_pacto_1v_2026/geo'
S3  = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co'

CITIES = [
 dict(slug='bogota', name='Bogotá', cod5='16001',
      geo='BOG-BARRIOS-CATASTRALES.json', fld='nombre', com='loc_nombre', key='codigo', rot=True,
      url=f'{S3}/congreso-2026/output/mapas-2026/Ciudades-COM-LOC/BOG-BARRIOS-CATASTRALES.json'),
 dict(slug='medellin', name='Medellín', cod5='01001',
      geo='MEDELLIN_BARRIOS_OFICIAL.json', fld='NOMBRE', com='COMUNA', key='CODIGO', rot=False,
      url=f'{S3}/bases+de+datos/MEDELLIN_BARRIOS_OFICIAL.json'),
 dict(slug='barranquilla', name='Barranquilla', cod5='03001',
      geo='BARRANQUILLA-BARRIOS.json', fld='NOMBRE', com='LOCALIDAD', key='__idx', rot=False,
      url=f'{S3}/congreso-2026/output/mapas-2026/Ciudades-COM-LOC/BARRANQUILLA-BARRIOS.json'),
 dict(slug='cali', name='Cali', cod5='31001',
      geo='CALI-BARRIOS.json', fld='barrio', com='comuna', key='__idx', rot=False,
      url=f'{S3}/congreso-2026/output/mapas-2026/Ciudades-COM-LOC/CALI-BARRIOS.json'),
 dict(slug='bucaramanga', name='Bucaramanga', cod5='27001',
      geo='BUCARAMANGA-BARRIOS.json', fld='barrio', com='cod_comuna', key='__idx', rot=False,
      url=f'{S3}/congreso-2026/output/mapas-2026/Ciudades-COM-LOC/BUCARAMANGA-BARRIOS.json'),
 dict(slug='soledad', name='Soledad', cod5='03052',
      geo='SOLEDAD-BARRIOS.json', fld='barrio', com='comuna', key='__idx', rot=False,
      url=f'{S3}/congreso-2026/output/mapas-2026/Ciudades-COM-LOC/SOLEDAD-BARRIOS.json'),
 dict(slug='manizales', name='Manizales', cod5='09001',
      geo='MANIZALES-BARRIOS.json', fld='BARRIOS', com='Id_Comuna', key='__idx', rot=False,
      url=f'{S3}/congreso-2026/output/mapas-2026/Ciudades-COM-LOC/MANIZALES-BARRIOS.json'),
 dict(slug='pereira', name='Pereira', cod5='24001',
      geo='PEREIRA-BARRIOS.json', fld='NOMBRE', com='COMUNA', key='__idx', rot=False,
      url=f'{S3}/congreso-2026/output/mapas-2026/Ciudades-COM-LOC/PEREIRA-BARRIOS.json'),
]

def margin(c, a): return (a - c) / (a + c) if (a + c) > 0 else 0.0

def fmt_com(slug, v):
    if v is None: return ''
    s = str(v).strip()
    if not s or s.lower() in ('none', 'nan', 'sn'): return ''
    if slug == 'bogota': return s.title()              # localidad (texto)
    if s.replace('.', '').isdigit():                    # código de comuna -> "Comuna N"
        try: return f'Comuna {int(float(s))}'
        except: return s
    return s.title()

M = json.load(open(f'{OUT}/master_unificado_puesto.json'))
bycity = collections.defaultdict(list)
for r in M:
    if r['cep2'] is None or not r.get('lat'): continue
    try: lat, lon = float(r['lat']), float(r['lon'])
    except: continue
    if not (-5 < lat < 13 and -80 < lon < -66): continue
    bycity[r['cod5']].append((lon, lat, r['cep1'], r['abe1'], r['cep2'], r['abe2']))

RESULT = {}
for cfg in CITIES:
    pts = bycity.get(cfg['cod5'], [])
    gj = json.load(open(f"{GEO}/{cfg['geo']}"))
    g = gpd.GeoDataFrame.from_features(gj['features']).set_crs('EPSG:4326')
    g = g.reset_index(drop=True)
    g['fid'] = range(len(g))
    g['nm'] = g[cfg['fld']].astype(str)
    g['cm'] = g[cfg['com']].astype(str) if cfg['com'] in g.columns else ''

    pdf = pd.DataFrame(pts, columns=['lon','lat','cep1','abe1','cep2','abe2'])
    P = gpd.GeoDataFrame(pdf, geometry=[Point(xy) for xy in zip(pdf.lon, pdf.lat)], crs='EPSG:4326')
    j = gpd.sjoin(P, g[['fid','geometry']], how='left', predicate='within')
    miss = j['index_right'].isna()
    dropped = 0
    if miss.any():
        # nearest SOLO si está cerca (~550 m): evita que puestos rurales/cerros fuera
        # de la cartografía urbana (veredas, La Calera) se peguen a un barrio del borde
        # y lo contaminen (caso Santa Ana en Usaquén). Los lejanos quedan sin barrio.
        jn = gpd.sjoin_nearest(P[miss.values], g[['fid','geometry']], how='left', max_distance=0.005)
        jn = jn[~jn.index.duplicated(keep='first')].reindex(P[miss.values].index)
        j.loc[miss.values, 'fid'] = jn['fid'].values
        dropped = int(j.loc[miss.values, 'fid'].isna().sum())
    agg = j.groupby('fid')[['cep1','abe1','cep2','abe2']].sum()
    g = g.merge(agg, left_on='fid', right_index=True, how='left')

    direct = g['cep2'].notna()
    have = g[direct]; cent = have.geometry.centroid
    for i in g[~direct].index:
        c = g.geometry[i].centroid
        d = ((cent.x - c.x) ** 2 + (cent.y - c.y) ** 2)
        nn = have.index[int(np.argmin(d.values))]
        for col in ['cep1','abe1','cep2','abe2']:
            g.loc[i, col] = g.loc[nn, col]
    g['fill'] = ~direct
    g[['cep1','abe1','cep2','abe2']] = g[['cep1','abe1','cep2','abe2']].fillna(0)

    g = g.sort_values('fid').reset_index(drop=True)
    keyfld = cfg['key']
    if keyfld != '__idx':
        keys = g[keyfld].astype(str).tolist()
        if len(set(keys)) != len(keys):
            print(f"  ! {cfg['name']}: clave '{keyfld}' NO única -> uso índice")
            keyfld = '__idx'
    bd = {}
    for i, r in enumerate(g.itertuples()):
        c1, a1, c2, a2 = float(r.cep1), float(r.abe1), float(r.cep2), float(r.abe2)
        m1, m2 = margin(c1, a1), margin(c2, a2)
        k = str(i) if keyfld == '__idx' else str(getattr(g.iloc[i], keyfld))
        bd[k] = {
            'n': r.nm, 'cm': fmt_com(cfg['slug'], r.cm),
            'c1': int(c1), 'a1': int(a1), 'c2': int(c2), 'a2': int(a2),
            'w1': 'A' if a1 >= c1 else 'C', 'w2': 'A' if a2 >= c2 else 'C',
            'm1': round(100 * m1, 1), 'm2': round(100 * m2, 1),
            'sw': round(100 * (m2 - m1), 1), 'f': 1 if r.fill else 0,
        }

    tc1, ta1 = pdf['cep1'].sum(), pdf['abe1'].sum()
    tc2, ta2 = pdf['cep2'].sum(), pdf['abe2'].sum()
    dd = g[direct.values] if len(direct) == len(g) else g[~g['fill']]
    cw1 = int((dd['abe1'] < dd['cep1']).sum()); aw1 = int((dd['abe1'] >= dd['cep1']).sum())
    cw2 = int((dd['abe2'] < dd['cep2']).sum()); aw2 = int((dd['abe2'] >= dd['cep2']).sum())
    meta = {
        'name': cfg['name'], 'n': int((~g['fill']).sum()), 'nfeat': len(g),
        'fld': cfg['fld'], 'com': cfg['com'], 'keyfld': keyfld, 'rot': cfg['rot'], 'url': cfg['url'],
        'cep1': int(tc1), 'abe1': int(ta1), 'cep2': int(tc2), 'abe2': int(ta2),
        'm1': round(100 * margin(tc1, ta1), 1), 'm2': round(100 * margin(tc2, ta2), 1),
        'cep_gana1': cw1, 'abe_gana1': aw1, 'cep_gana2': cw2, 'abe_gana2': aw2,
    }
    RESULT[cfg['slug']] = {'meta': meta, 'b': bd}
    print(f"  {cfg['name']:13s} feats {len(g):4d} · directos {meta['n']:4d} · drop {dropped:3d} · "
          f"1V Cep {cw1}/Abe {aw1} -> 2V Cep {cw2}/Abe {aw2} · "
          f"margen 1V {meta['m1']:+.1f} -> 2V {meta['m2']:+.1f}")

json.dump(RESULT, open(f'{OUT}/ciudades-barrios-2v.json', 'w'), ensure_ascii=False, separators=(',', ':'))
sz = os.path.getsize(f'{OUT}/ciudades-barrios-2v.json')
print(f"\n-> {OUT}/ciudades-barrios-2v.json  ({sz/1024:.0f} KB)")
