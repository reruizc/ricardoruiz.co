#!/usr/bin/env python3
# Barrios por ciudad: cruza puestos (lat/lon) a poligonos de barrio (PIP + vecino
# mas cercano), agrega 1V y 2V, y pinta 2 mapas: RESULTADO 1V (izq) y RESULTADO 2V
# (der) por barrio. Encuadre robusto: el mapa SIEMPRE llena su lienzo (padding
# relativo al tamano de la ciudad; sin bbox_inches que descuadra el aspecto).
# -> output_2v/mapas/{slug}_{v1,v2}.png  +  output_2v/barrios_2v.json
import json, collections, warnings
import numpy as np, geopandas as gpd, pandas as pd
from shapely.geometry import Point
from shapely.ops import transform
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import to_rgb
warnings.filterwarnings('ignore')

OUT='Bases de datos/output_2v'; GEO='Bases de datos/output_pacto_1v_2026/geo'
import os; os.makedirs(f'{OUT}/mapas',exist_ok=True)
for fnt in ['Regular','Bold']:
    try: font_manager.fontManager.addfont(f'tools/pacto-1v-2026/fonts/Inter-{fnt}.ttf')
    except: pass
plt.rcParams['font.family']='Inter'
INK='#1a1510'; MUT='#6b6258'; BLUE='#1f47cc'; RED='#c0392b'; PAPER='#f4f1ea'

CITIES=[
 dict(slug='medellin',name='Medellín',cod5='01001',geo='MEDELLIN_BARRIOS_OFICIAL.json',fld='NOMBRE',rot=False),
 dict(slug='bogota',name='Bogotá',cod5='16001',geo='BOG-BARRIOS-CATASTRALES.json',fld='nombre',rot=True),
 dict(slug='cali',name='Cali',cod5='31001',geo='CALI-BARRIOS.json',fld='barrio',rot=False),
 dict(slug='barranquilla',name='Barranquilla',cod5='03001',geo='BARRANQUILLA-BARRIOS.json',fld='NOMBRE',rot=False),
 dict(slug='cartagena',name='Cartagena',cod5='05001',geo='CARTAGENA-BARRIOS.json',fld='NOMBRE',rot=False),
 dict(slug='bucaramanga',name='Bucaramanga',cod5='27001',geo='BUCARAMANGA-BARRIOS.json',fld='barrio',rot=False),
 dict(slug='cucuta',name='Cúcuta',cod5='25001',geo='CUCUTA-BARRIOS.json',fld='barrio',rot=False),
 dict(slug='pereira',name='Pereira',cod5='24001',geo='PEREIRA-BARRIOS.json',fld='NOMBRE',rot=False),
 dict(slug='manizales',name='Manizales',cod5='09001',geo='MANIZALES-BARRIOS.json',fld='BARRIOS',rot=False),
 dict(slug='santamarta',name='Santa Marta',cod5='21001',geo='SANTAMARTA-BARRIOS-REAL.json',fld='barrio',rot=False),
 dict(slug='soledad',name='Soledad',cod5='03052',geo='SOLEDAD-BARRIOS.json',fld='barrio',rot=False),
 dict(slug='popayan',name='Popayán',cod5='11001',geo='POPAYAN-BARRIOS.json',fld='BARRIOS',rot=False),
 dict(slug='buenaventura',name='Buenaventura',cod5='31019',geo='BUENAVENTURA-BARRIOS.json',fld='barrio',rot=False),
 dict(slug='quibdo',name='Quibdó',cod5='17001',geo='QUIBDO-BARRIOS.json',fld='barrio',rot=False),
]

M=json.load(open(f'{OUT}/master_unificado_puesto.json'))
bycity=collections.defaultdict(list)
for r in M:
    if r['cep2'] is None or not r.get('lat'): continue
    try: lat,lon=float(r['lat']),float(r['lon'])
    except: continue
    if not(-5<lat<13 and -80<lon<-66): continue
    bycity[r['cod5']].append((lon,lat,r['cep1'],r['abe1'],r['cep2'],r['abe2']))

def _rotg(geom,cx=-74.08,cy=4.65): return transform(lambda x,y,z=None:(cx-(y-cy),cy+(x-cx)),geom)
def rotg(gdf): return gdf.set_geometry(gdf.geometry.apply(_rotg))
def margin(c,a): return (a-c)/(a+c) if (a+c)>0 else 0

def draw(gp,colors,bounds,title,sub,out):
    minx,miny,maxx,maxy=bounds; dx=maxx-minx; dy=maxy-miny; pad=0.04*max(dx,dy,1e-4)
    xlim=(minx-pad,maxx+pad); ylim=(miny-pad,maxy+pad)
    dxl,dyl=xlim[1]-xlim[0],ylim[1]-ylim[0]
    fw=7.0; maph=fw*dyl/dxl; titleh=0.62; fh=maph+titleh
    fig=plt.figure(figsize=(fw,fh)); fig.patch.set_facecolor(PAPER)
    ax=fig.add_axes([0,0,1,maph/fh]); ax.set_facecolor(PAPER)
    gp.plot(ax=ax,color=colors,edgecolor='white',linewidth=0.13)
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.axis('off')
    # marca de agua confidencial diagonal (45°) sobre el mapa (anti-robo de la pieza suelta)
    ax.text(0.5,0.5,'DOCUMENTO\nCONFIDENCIAL\nRICARDORUIZ.CO',transform=ax.transAxes,rotation=45,ha='center',va='center',
            fontsize=50,fontweight='bold',color='#1a1510',alpha=0.20,zorder=20,linespacing=1.25)
    fig.text(0.012,1-0.40*titleh/fh,title,fontsize=14.5,fontweight='bold',color=INK,va='center')
    fig.text(0.012,1-0.83*titleh/fh,sub,fontsize=8.6,color=MUT,va='center')
    fig.savefig(out,facecolor=PAPER,dpi=135); plt.close(fig)

SUMMARY={}
for cfg in CITIES:
    pts=bycity.get(cfg['cod5'],[])
    if not pts: print('  ! sin puestos',cfg['name']); continue
    gj=json.load(open(f"{GEO}/{cfg['geo']}"))
    g=gpd.GeoDataFrame.from_features(gj['features']).set_crs('EPSG:4326'); g['bn']=g[cfg['fld']].astype(str)
    pdf=pd.DataFrame(pts,columns=['lon','lat','cep1','abe1','cep2','abe2'])
    P=gpd.GeoDataFrame(pdf,geometry=[Point(xy) for xy in zip(pdf.lon,pdf.lat)],crs='EPSG:4326')
    j=gpd.sjoin(P,g[['bn','geometry']],how='left',predicate='within'); miss=j['index_right'].isna()
    if miss.any():
        jn=gpd.sjoin_nearest(P[miss.values],g[['bn','geometry']],how='left'); j.loc[miss.values,'bn']=jn['bn'].values
    agg=j.groupby('bn')[['cep1','abe1','cep2','abe2']].sum(); g=g.merge(agg,left_on='bn',right_index=True,how='left')
    direct=g['cep2'].notna(); have=g[direct]; cent=have.geometry.centroid
    for i in g[~direct].index:
        c=g.geometry[i].centroid; d=((cent.x-c.x)**2+(cent.y-c.y)**2)
        nn=have.index[int(np.argmin(d.values))]
        for col in ['cep1','abe1','cep2','abe2']: g.loc[i,col]=g.loc[nn,col]
    g['fill']=~direct; g[['cep1','abe1','cep2','abe2']]=g[['cep1','abe1','cep2','abe2']].fillna(0)
    g['m1']=g.apply(lambda r:margin(r.cep1,r.abe1),axis=1); g['m2']=g.apply(lambda r:margin(r.cep2,r.abe2),axis=1)
    g['swing']=g['m2']-g['m1']
    g['w1']=np.where(g['abe1']>=g['cep1'],'A','C'); g['w2']=np.where(g['abe2']>=g['cep2'],'A','C')
    gp=rotg(g) if cfg['rot'] else g
    # encuadre al CASCO URBANO = barrios con dato directo (ignora puestos rurales lejanos)
    bounds=gp[direct.values].total_bounds
    def wincol(mcol,wcol):
        out=[]
        for r in g.itertuples():
            m=abs(getattr(r,mcol)); base=BLUE if getattr(r,wcol)=='A' else RED; a=0.32+0.68*min(1,m/0.5)
            out.append((*to_rgb(base),a if not r.fill else a*0.42))
        return out
    cw1=int((g[direct]['w1']=='C').sum()); aw1=int((g[direct]['w1']=='A').sum())
    cw2=int((g[direct]['w2']=='C').sum()); aw2=int((g[direct]['w2']=='A').sum())
    nb=int(direct.sum())
    draw(gp,wincol('m1','w1'),bounds,f'{cfg["name"]} · resultado 1ª vuelta',f'Cepeda gana {cw1} barrios · Abelardo {aw1}  (de {nb} con dato)',f'{OUT}/mapas/{cfg["slug"]}_v1.png')
    draw(gp,wincol('m2','w2'),bounds,f'{cfg["name"]} · resultado 2ª vuelta',f'Cepeda gana {cw2} barrios · Abelardo {aw2}  (de {nb} con dato)',f'{OUT}/mapas/{cfg["slug"]}_v2.png')
    tc1,ta1,tc2,ta2=pdf['cep1'].sum(),pdf['abe1'].sum(),pdf['cep2'].sum(),pdf['abe2'].sum()
    dd=g[direct].copy()
    SUMMARY[cfg['slug']]={'name':cfg['name'],'n_barrios':nb,'cep1':int(tc1),'abe1':int(ta1),'cep2':int(tc2),'abe2':int(ta2),
      'm1':round(100*margin(tc1,ta1),1),'m2':round(100*margin(tc2,ta2),1),
      'cepeda_gana':cw2,'abelardo_gana':aw2,'cepeda_gana1':cw1,'abelardo_gana1':aw1,
      'top_swing_abe':[{'b':r.bn,'sw':round(100*r.swing,1)} for r in dd.nlargest(5,'swing').itertuples()],
      'top_swing_cep':[{'b':r.bn,'sw':round(100*r.swing,1)} for r in dd.nsmallest(5,'swing').itertuples()]}
    print(f'  {cfg["name"]:14s} {nb:4d} barrios · 1V gana Cep {cw1}/Abe {aw1} -> 2V Cep {cw2}/Abe {aw2}')

json.dump(SUMMARY,open(f'{OUT}/barrios_2v.json','w'),ensure_ascii=False,indent=1)
print(f'\n-> {OUT}/barrios_2v.json  + {2*len(SUMMARY)} mapas')
