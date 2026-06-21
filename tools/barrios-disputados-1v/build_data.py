#!/usr/bin/env python3
"""Construye, por ciudad, un GeoJSON compacto con el resultado por barrio para el
mapa de barrios VELETA (disputados) — en 1ª vuelta y en proyección de 2ª vuelta.

Cada feature props: { nb, c, a, b, C, A, f }
  c,a = Cepeda/Abelardo en 1V (votos) · b = válidos 1V (cands + blanco)
  C,A = masa proyectada Cepeda/Abelardo en 2V tras trasvase (votos)
  f   = 1 si el barrio no tiene puesto propio (heredó al vecino más cercano)

El margen y el color se calculan en el cliente (slider de umbral + toggle 1V/2V).
El blanco de 2V (~2,4%) se aplica en el cliente sobre C+A.

Trasvase = modelo de ponderador-2v.html (matriz AtlasIntel 1V->2V):
  Cepeda/Abelardo guardan fidelidad fidC/fidA; cada bloque eliminado (Paloma,
  Fajardo, Claudia, menores+Botero, blanco/nulo) cede su parte transferible
  (1 - BLANCO_FRAC) repartida p / (1-p); la abstención moviliza mob del potencial.

Mismo motor de cruce que tools/pacto-1v-2026/build_maps.py (sjoin_nearest).
Salida: Bases de datos/output_barrios_veleta/{slug}.json + index.json
"""
import json, os, sys, unicodedata
import geopandas as gpd
from shapely.geometry import Point, mapping

def _norm(s):
    return ''.join(c for c in unicodedata.normalize('NFD', str(s).upper()) if unicodedata.category(c) != 'Mn').strip()

# Polígonos no residenciales (parques, clubes) que NO deben colorearse — quedan grises (f=2).
EXCLUDE = {
    'bogota': {'COUNTRY CLUB','SIMON BOLIVAR'},  # + cualquier "PARQUE *" (regla abajo)
}
def is_excl(slug, nb):
    n = _norm(nb)
    if n in EXCLUDE.get(slug, set()): return True
    if slug == 'bogota' and n.startswith('PARQUE '): return True
    return False

ROOT = '/Users/ricardoruiz/ricardoruiz.co'
GEO  = f'{ROOT}/Bases de datos/output_pacto_1v_2026/geo'
MASTER = f'{ROOT}/Bases de datos/output_pacto_1v_2026/master_2026_puesto.json'
OUT  = f'{ROOT}/Bases de datos/output_barrios_veleta'
os.makedirs(OUT, exist_ok=True)

VERSION = '2026-06-20-3v'
CAND = ['cepeda','abelardo','paloma','fajardo','botero','lizcano','miguel_uribe',
        'macollins','roy','murillo','caicedo','matamoros','claudia']
OTR  = ['botero','lizcano','miguel_uribe','macollins','roy','murillo','caicedo','matamoros']
SIMP = 0.00014   # tolerancia de simplificación (~15 m)
RND  = 5

# ── Modelo de trasvase 1V->2V (idéntico a ponderador-2v.html) ──────────────
SIM = dict(fidC=0.97, fidA=0.95, pal=0.033, faj=0.585, cla=0.55, otr=0.478,
           blo=0.11, mob=0.06, mobp=0.342)
BLANCO_FRAC = dict(pal=0.126, faj=0.260, cla=0.180, otr=0.182, blo=0.802, mob=0.130)

def project(cep, abe, pal, faj, cla, otr, bln, urna, pot):
    """Devuelve (C, A): masa proyectada Cepeda/Abelardo en 2V."""
    def tr(v, frac, p):
        t = v * (1 - frac); return (t * p, t * (1 - p))
    C = cep * SIM['fidC']; A = abe * SIM['fidA']
    for v, fk, pk in [(pal,'pal','pal'),(faj,'faj','faj'),(cla,'cla','cla'),
                      (otr,'otr','otr'),(bln,'blo','blo')]:
        c, a = tr(v, BLANCO_FRAC[fk], SIM[pk]); C += c; A += a
    abst = max(0, pot - urna) * SIM['mob']
    c, a = tr(abst, BLANCO_FRAC['mob'], SIM['mobp']); C += c; A += a
    return C, A

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
    # Popayán: capa oficial Alcaldía (ArcGIS Curaduria_2023_WFL1/FeatureServer/2, campo BARRIOS)
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
        g = lambda k: int(p.get(k,0) or 0)
        base = sum(g(c) for c in CAND) + g('votos_blanco')
        rows.append({'cep':g('cepeda'),'abe':g('abelardo'),'pal':g('paloma'),
                     'faj':g('fajardo'),'cla':g('claudia'),'otr':sum(g(c) for c in OTR),
                     'bln':g('votos_blanco')+g('votos_nulos')+g('votos_no_marcados'),
                     'urna':g('total_votos_urna'),'pot':g('pot'),'base':base,
                     'geometry': Point(lon, lat)})
    return gpd.GeoDataFrame(rows, crs='EPSG:4326')

def round_geom(geom):
    gj = mapping(geom)
    def rr(co):
        if isinstance(co[0], (float, int)):
            return [round(co[0], RND), round(co[1], RND)]
        return [rr(c) for c in co]
    gj['coordinates'] = rr(gj['coordinates'])
    return gj

SUMCOLS = ['cep','abe','pal','faj','cla','otr','bln','urna','pot','base']
index = []
for name, region, slug, code, gj, nf, bbox, rotate in CITIES:
    dep, mun = code[:2], code[2:]
    bar = gpd.read_file(f'{GEO}/{gj}')[[nf,'geometry']].to_crs('EPSG:4326').rename(columns={nf:'NB'})
    bar['NB'] = bar['NB'].fillna('').astype(str).str.strip()
    bar = bar[bar['NB'] != ''].reset_index(drop=True)
    bar['excl'] = bar['NB'].map(lambda n: is_excl(slug, n))
    pts = city_puestos(dep, mun, bbox)
    # asignación POR POLÍGONO (no por nombre): cada puesto al polígono no-excluido más cercano
    tgt = bar[~bar['excl']]
    j = gpd.sjoin_nearest(pts, tgt[['geometry']], how='left')
    j = j[~j.index.duplicated(keep='first')].dropna(subset=['index_right'])
    j['index_right'] = j['index_right'].astype(int)
    agg = j.groupby('index_right')[SUMCOLS].sum()
    res = {}
    for idx, r in agg.iterrows():
        if r['base'] <= 0: continue
        C, A = project(r['cep'],r['abe'],r['pal'],r['faj'],r['cla'],r['otr'],r['bln'],r['urna'],r['pot'])
        res[idx] = (int(r['cep']), int(r['abe']), int(r['base']), round(C), round(A))
    # representante por nombre = polígono directo con más votos (para contar barrios sin duplicar)
    byname = {}
    for idx,(c,a,b,C,A) in res.items(): byname.setdefault(bar.at[idx,'NB'], []).append((b, idx))
    repset = {max(lst, key=lambda t: t[0])[1] for lst in byname.values()}
    # huérfanos (no excluidos, sin dato) heredan el polígono directo más cercano
    bar['rep'] = bar.geometry.representative_point()
    have_idx = list(res.keys())
    miss = bar[(~bar['excl']) & (~bar.index.isin(res))]
    fill = {}
    if len(miss) and have_idx:
        hg = gpd.GeoDataFrame({'hi': have_idx}, geometry=bar.loc[have_idx,'rep'].values, crs=bar.crs)
        mg = gpd.GeoDataFrame({'_i': list(miss.index)}, geometry=miss['rep'].values, crs=bar.crs)
        jn = gpd.sjoin_nearest(mg, hg, how='left'); jn = jn[~jn['_i'].duplicated(keep='first')]
        for _, r in jn.iterrows(): fill[int(r['_i'])] = res[int(r['hi'])]

    feats = []; v1=v2=c1=c2=a1=a2=0
    for idx, row in bar.iterrows():
        nb = row['NB']
        if row['excl']:
            feats.append({'type':'Feature','properties':{'nb':nb,'c':0,'a':0,'b':0,'C':0,'A':0,'f':2,'r':0},
                          'geometry': round_geom(row.geometry.simplify(SIMP, preserve_topology=True))}); continue
        if idx in res:        c,a,b,C,A = res[idx]; f = 0; rp = 1 if idx in repset else 0
        elif idx in fill:     c,a,b,C,A = fill[idx]; f = 1; rp = 0
        else: continue
        feats.append({'type':'Feature',
                      'properties':{'nb':nb,'c':c,'a':a,'b':b,'C':C,'A':A,'f':f,'r':rp},
                      'geometry': round_geom(row.geometry.simplify(SIMP, preserve_topology=True))})
        if f == 0 and rp == 1 and b > 0:   # cuenta barrios por representante (sin duplicar nombres)
            m1 = (c - a) / b * 100
            tot = C + A; m2 = (C - A) / tot * 100 if tot else 0
            if abs(m1) <= 3: v1 += 1
            elif m1 > 0: c1 += 1
            else: a1 += 1
            if abs(m2) <= 3: v2 += 1
            elif m2 > 0: c2 += 1
            else: a2 += 1
    ndir = v1 + c1 + a1
    json.dump({'type':'FeatureCollection','features':feats}, open(f'{OUT}/{slug}.json','w'),
              ensure_ascii=False, separators=(',',':'))
    kb = os.path.getsize(f'{OUT}/{slug}.json')//1024
    index.append({'slug':slug,'name':name,'region':region,'rotate':rotate,
                  'nDirect':ndir,'file':f'{slug}.json'})
    print(f'{name:<13} dir {ndir:>4} · 1V[vel{v1:>3} C{c1:>3} A{a1:>3}] · '
          f'2V[vel{v2:>3} C{c2:>3} A{a2:>3}] · {kb} KB')

json.dump({'cities':index,'version':VERSION,'cands':['Cepeda','Abelardo'],
           'blank2v':0.024}, open(f'{OUT}/index.json','w'), ensure_ascii=False, indent=1)
print('\n✓ index.json ·', len(index), 'ciudades ·', VERSION, '->', OUT)
