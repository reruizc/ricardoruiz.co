#!/usr/bin/env python3
# Genera polígonos de barrio APROXIMADOS (celdas Voronoi de los puestos, disueltas por nombre de
# barrio y recortadas al límite de comunas) para ciudades SIN capa pública de barrios (Bucaramanga,
# Cúcuta). Cada puesto del master trae su barrio; Voronoi reparte el territorio entre puestos.
# Reutilizable: agrega (ciudad, dep, mun, comuna_geojson, salida) a CITIES.
import json, warnings; warnings.filterwarnings('ignore')
import geopandas as gpd
from shapely.geometry import Point, MultiPoint
from shapely.ops import voronoi_diagram, unary_union
OUT='Bases de datos/output_pacto_1v_2026'; GEO=f'{OUT}/geo'
M=json.load(open(f'{OUT}/master_2026_puesto.json'))
def z(x,n): return str(x).zfill(n)
CITIES=[  # (nombre, dep, mun, geojson_comunas|None→silueta, salida)
    # NO incluir aquí las que ya tienen capa REAL (Cúcuta, Buenaventura, Soledad, Quibdó, Bucaramanga):
    # el script las sobrescribiría. Solo las que siguen sin capa pública de barrios → Voronoi.
    ('Pasto','23','001',None,'PASTO-BARRIOS.json'),
    ('Santa Marta','21','001',None,'SANTAMARTA-BARRIOS.json'),
    ('Palmira','31','079',None,'PALMIRA-BARRIOS.json'),
    ('Tumaco','23','139',None,'TUMACO-BARRIOS.json'),
    ('Sincelejo','28','001',None,'SINCELEJO-BARRIOS.json'),
]
def build(nombre,dep,mun,comfile,outfile):
    # límite: geojson de comuna si hay; si no, convex-hull de los puestos (bufferizado)
    pts0=[]
    for p in M:
        if z(p['dep'],2)!=dep or z(p['mun'],3)!=mun or z(p['zona'],2) in ('90','98'): continue
        try: pts0.append(Point(float(p['lon']),float(p['lat'])))
        except: pass
    if comfile:
        boundary=unary_union(gpd.read_file(f'{GEO}/{comfile}').to_crs('EPSG:4326').geometry.values)
    else:   # SILUETA: unión de buffers de los puestos del casco (contorno ORGÁNICO, no convexo) ∩ polígono municipal real
        xs=sorted(p.x for p in pts0); ys=sorted(p.y for p in pts0); q=lambda a,f:a[min(len(a)-1,int(len(a)*f))]
        x0,x1,y0,y1=q(xs,0.04),q(xs,0.96),q(ys,0.04),q(ys,0.96)
        core=[p for p in pts0 if x0<=p.x<=x1 and y0<=p.y<=y1] or pts0
        blob=unary_union([p.buffer(0.014) for p in core]).buffer(0.003)   # abraza los puestos
        try:
            mg=gpd.read_file(f'{GEO}/mps/{dep}.json').to_crs('EPSG:4326'); mg['_m']=mg['mun_electoral'].astype(str).str.zfill(3)
            muni=unary_union(mg[mg['_m']==mun].geometry.values)
            boundary=blob.intersection(muni) if not muni.is_empty else blob
            if boundary.is_empty: boundary=blob
        except Exception: boundary=blob
    pts=[]
    for p in M:
        if z(p['dep'],2)!=dep or z(p['mun'],3)!=mun: continue
        if z(p['zona'],2) in ('90','98'): continue
        bar=(p.get('barrio') or '').strip()
        if not bar: continue
        try: lat=float(p['lat']); lon=float(p['lon'])
        except: continue
        if not boundary.buffer(0.02).contains(Point(lon,lat)): continue   # dentro del casco (con holgura)
        pts.append((Point(lon,lat),bar))
    if len(pts)<5: print(f'  ⚠ {nombre}: solo {len(pts)} puestos, salto'); return
    mp=MultiPoint([g for g,_ in pts])
    cells=list(voronoi_diagram(mp, envelope=boundary).geoms)
    gd=gpd.GeoDataFrame({'barrio':[None]*len(cells)},geometry=cells,crs='EPSG:4326')
    gp=gpd.GeoDataFrame({'barrio':[b for _,b in pts]},geometry=[g for g,_ in pts],crs='EPSG:4326')
    j=gpd.sjoin(gp,gd[['geometry']],how='left',predicate='within')
    for _,r in j.iterrows():
        if r['index_right']==r['index_right']: gd.loc[r['index_right'],'barrio']=r['barrio']
    gd['geometry']=gd.geometry.intersection(boundary)
    gd=gd[~gd.geometry.is_empty & gd.geometry.notna() & gd['barrio'].notna()]
    dis=gd.dissolve(by='barrio').reset_index()
    dis=dis[dis.geometry.is_valid | dis.geometry.buffer(0).is_valid].copy()
    dis['geometry']=dis.geometry.buffer(0)
    dis[['barrio','geometry']].to_file(f'{GEO}/{outfile}',driver='GeoJSON')
    print(f'  ✓ {outfile}: {len(dis)} barrios (de {len(pts)} puestos) · bounds {[round(x,3) for x in dis.total_bounds]}')

if __name__=='__main__':
    print('Voronoi-barrios (aprox · puestos→celdas→disuelto por barrio):')
    for c in CITIES: build(*c)
