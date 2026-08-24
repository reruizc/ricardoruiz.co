#!/usr/bin/env python3
# Motor de mapas del informe Pacto 1V 2026.
# Genera coropletas (departamento + municipio), mapa de estrato por manzana de
# Bogotá y mapas de ciudad, en el estilo claro del informe.
import json, unicodedata, warnings
warnings.filterwarnings('ignore')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm, ListedColormap
from matplotlib.patches import Patch
import geopandas as gpd, pandas as pd
from shapely.geometry import Point
# Tipografía Inter (unificar con el informe Word). Las imágenes de redes/Instagram
# NO usan esto: conservan Helvetica + su formato propio (ver CLAUDE.md).
for _f in ('Inter-Regular.ttf','Inter-Bold.ttf','Inter-Italic.ttf'):
    try: font_manager.fontManager.addfont(f'tools/pacto-1v-2026/fonts/{_f}')
    except Exception: pass
plt.rcParams['font.family']='Inter'

OUT='Bases de datos/output_pacto_1v_2026'; GEO=f'{OUT}/geo'
PAPER='#faf8f2'; INK='#1a1510'; INK2='#6b6354'; GREY='#cfc8b8'
OX='#8a1e16'; NAVY='#16166b'; PURP='#534a8f'; GREEN='#2e7d46'; GOLD='#c98b2e'; ROYAL='#1f47cc'  # azul rey Abelardo (contrasta con el morado de Cepeda)
def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFD',str(s).upper().strip()) if unicodedata.category(c)!='Mn')

# colormaps a medida
CM_CEP=LinearSegmentedColormap.from_list('cep',['#f1eef6','#bcbddc','#807dba','#54278f'])       # izquierda (morado)
CM_DER=LinearSegmentedColormap.from_list('der',['#eef0f6','#9ea7c9','#4a5594','#16166b'])        # derecha (azul)
CM_SWING=LinearSegmentedColormap.from_list('sw',[OX,'#d98b7d','#f6efe6','#86c39a',GREEN])         # diverge: rojo↘ verde↗
CM_REC=LinearSegmentedColormap.from_list('rec',['#f1eee4','#a8d5b6','#4a9e68','#1f6b3a'])         # recuperación (verde)
CM_ABS=LinearSegmentedColormap.from_list('abs',['#f4efe6','#e0b48a','#c97a3a','#8a3a16'])         # abstención (cobre)
CM_CENTRO=LinearSegmentedColormap.from_list('cen',['#f6f0e2','#ecd28f','#d3a23a','#9a6a16'])      # centro (ámbar/oro)
LABELS={}   # fname → {city, metric, total, top:[{n,barrio,val}]} · para numerar mapas y desarrollar en el Word
EST_COLORS={1:'#8a1e16',2:'#cf6a4d',3:'#e9c46a',4:'#9fb98b',5:'#5a86b0',6:'#26456e'}             # estrato 1→6

BA=json.load(open(f'{OUT}/blocks_all.json')); BF=json.load(open(f'{OUT}/blocks_full.json'))
DIF=json.load(open(f'{OUT}/dif_2022.json'))
DEPN_BY_NORM={norm(k):k for k in BA['depto']}
ALIAS={'DISTRITO CAPITAL DE BOGOTA':'Bogotá','SAN ANDRES Y PROVIDENCIA':'San Andrés'}

# ---- agregación master 2026 por dep y por mun (cepeda/abelardo/paloma/base) ----
CAND=['cepeda','abelardo','paloma','fajardo','claudia','miguel_uribe','roy','lizcano','botero','caicedo','murillo','macollins','matamoros']
d26=json.load(open(f'{OUT}/master_2026_puesto.json'))
AGG_DEP={}; AGG_MUN={}
for p in d26:
    dep=str(p.get('dep','')).zfill(2); mun=str(p.get('mun','')).zfill(3); mk=dep+mun
    base=sum(int(p.get(c,0) or 0) for c in CAND)+int(p.get('votos_blanco',0) or 0)
    for store,key in ((AGG_DEP,dep),(AGG_MUN,mk)):
        a=store.setdefault(key,{'cepeda':0,'abelardo':0,'paloma':0,'base':0})
        a['cepeda']+=int(p.get('cepeda',0) or 0); a['abelardo']+=int(p.get('abelardo',0) or 0)
        a['paloma']+=int(p.get('paloma',0) or 0); a['base']+=base

# ---- techo Petro-2V por puesto (para recuperar a nivel UPL/barrio) ----
d22=json.load(open(f'{OUT}/master_2022_puesto.json'))
def _pc(p):
    try: return f"{int(p['dep']):02d}{int(p['mun']):03d}{int(p['zona']):02d}{int(p['puesto']):02d}"
    except: return None
SHARE22={}
for p in (d22 if isinstance(d22,list) else d22.values()):
    k=_pc(p)
    if k and p.get('base2v'): SHARE22[k]=(p['petro2v']/p['base2v']) if p['base2v'] else None

# ---- Claudia por municipio (no existe a puesto) para el mapa de centro ----
import csv as _csv, collections as _coll
CLA_MUN=_coll.defaultdict(int)
with open('Bases de datos/nuevos archivos 1v 2026/Base nombres corregidos primera vuelta 2026.csv',newline='',encoding='utf-8-sig') as _f:
    for _r in _csv.DictReader(_f):
        if 'CLAUDIA' in (_r['Candidato'] or '').upper():
            CLA_MUN[str(_r['cod_departamento'] or '').zfill(2)+str(_r['cod_municipio'] or '').zfill(3)]+=int(_r['Suma de Votos'] or 0)

def load_deptos():
    g=gpd.read_file(f'{GEO}/DEPARTAMENTOS2.json')
    g['rrname']=g['name'].map(lambda n: ALIAS.get(norm(n)) or DEPN_BY_NORM.get(norm(n)))
    return g
def load_muns():
    parts=[]
    import glob,os
    for fp in sorted(glob.glob(f'{GEO}/mps/*.json')):
        try:
            g=gpd.read_file(fp)
            g['mk']=g['dep_electoral'].astype(str).str.zfill(2)+g['mun_elec'].astype(str).str.zfill(3)
            parts.append(g[['mk','geometry']])
        except Exception as e: print('  mun skip',fp,e)
    return gpd.GeoDataFrame(pd.concat(parts,ignore_index=True),crs=parts[0].crs)

def style_ax(ax,title,sub):
    ax.set_axis_off()
    ax.set_xlim(-79.3,-66.8); ax.set_ylim(-4.4,13.7)
    ax.set_title('')
    ax.text(0.0,1.045,title,transform=ax.transAxes,fontsize=14.5,fontweight='bold',color=INK,ha='left',va='top')
    if sub: ax.text(0.0,1.005,sub,transform=ax.transAxes,fontsize=9.3,color=INK2,ha='left',va='top')

def cbar(fig,ax,sm,label,fmt='{:.0f}'):
    cax=fig.add_axes([0.085,0.30,0.022,0.30])   # costado izquierdo, sobre el Pacífico (vacío)
    cb=fig.colorbar(sm,cax=cax); cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=7.5,colors=INK2,length=2)
    cb.set_label(label,fontsize=7.8,color=INK2); cb.ax.yaxis.set_label_position('left')

def choropleth_dep(metric, fname, title, sub, cmap, vmin, vmax, label, center=None):
    g=load_deptos()
    g['val']=g['rrname'].map(lambda n: BA['depto'].get(n,{}).get(metric) if n else None)
    fig,ax=plt.subplots(figsize=(6.0,6.6)); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    g.plot(ax=ax,color=GREY,edgecolor='white',linewidth=0.4)  # base (faltantes en gris)
    sub_g=g[g['val'].notna()]
    norm_=plt.Normalize(vmin,vmax)
    sub_g.plot(ax=ax,column='val',cmap=cmap,norm=norm_,edgecolor='white',linewidth=0.4)
    style_ax(ax,title,sub)
    sm=plt.cm.ScalarMappable(cmap=cmap,norm=norm_); sm.set_array([])
    cbar(fig,ax,sm,label)
    fig.text(0.012,0.02,'Fuente: preconteo Registraduría 2026 + escrutinios 2022 (GCS). Proporciones sobre válidos + blanco.',fontsize=6.4,color=INK2)
    plt.savefig(f'{OUT}/{fname}',dpi=155,facecolor=PAPER,bbox_inches='tight'); plt.close()
    print('✓',fname)

def choropleth_mun(valfn, fname, title, sub, cmap, vmin, vmax, label):
    g=load_muns()
    g['val']=g['mk'].map(valfn)
    fig,ax=plt.subplots(figsize=(6.0,6.6)); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    g.plot(ax=ax,color=GREY,edgecolor='white',linewidth=0.12)
    sub_g=g[g['val'].notna()]
    norm_=plt.Normalize(vmin,vmax)
    sub_g.plot(ax=ax,column='val',cmap=cmap,norm=norm_,edgecolor='white',linewidth=0.12)
    style_ax(ax,title,sub)
    sm=plt.cm.ScalarMappable(cmap=cmap,norm=norm_); sm.set_array([])
    cbar(fig,ax,sm,label)
    fig.text(0.012,0.02,'Fuente: preconteo Registraduría 2026 + escrutinios 2022 (GCS). ~1.100 municipios. Proporciones sobre válidos + blanco.',fontsize=6.4,color=INK2)
    plt.savefig(f'{OUT}/{fname}',dpi=160,facecolor=PAPER,bbox_inches='tight'); plt.close()
    print('✓',fname)

def winner_dep(fname):
    g=load_deptos()
    def win(n):
        a=AGG_DEP.get(BA['depto'].get(n,{}).get('cod','')) if n else None
        if not a or a['base']==0: return None
        return 'cep' if a['cepeda']>=a['abelardo'] else 'abe'
    g['w']=g['rrname'].map(win)
    fig,ax=plt.subplots(figsize=(6.0,6.6)); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    g.plot(ax=ax,color=GREY,edgecolor='white',linewidth=0.4)
    for key,col in (('cep',PURP),('abe',ROYAL)):
        sub=g[g['w']==key]
        if len(sub): sub.plot(ax=ax,color=col,edgecolor='white',linewidth=0.4)
    style_ax(ax,'Quién ganó cada departamento','Ganador de la 1ª vuelta · Cepeda vs Abelardo')
    leg=[Patch(facecolor=PURP,label='Ganó Cepeda'),Patch(facecolor=ROYAL,label='Ganó Abelardo')]
    ax.legend(handles=leg,loc='lower left',frameon=False,fontsize=9.5,bbox_to_anchor=(0.0,0.02))
    fig.text(0.012,0.02,'Fuente: preconteo Registraduría 2026 (votos por candidato a nivel de mesa).',fontsize=6.4,color=INK2)
    plt.savefig(f'{OUT}/{fname}',dpi=155,facecolor=PAPER,bbox_inches='tight'); plt.close()
    print('✓',fname)

def rotate_gdf(g, angle=90, origin=None):
    # rota 90° a la izquierda (CCW) alrededor de un origen común — Bogotá se ve así por convención
    if origin is None:
        minx,miny,maxx,maxy=g.total_bounds; origin=((minx+maxx)/2,(miny+maxy)/2)
    g=g.copy(); g['geometry']=g.geometry.rotate(angle,origin=origin); return g, origin

def bogota_estrato_map(fname):
    g=gpd.read_file(f'{OUT}/manzana_estrato_bog.gpkg')[['ESTRATO','geometry']]
    g['ESTRATO']=g['ESTRATO'].astype(int)
    g,_=rotate_gdf(g,90)   # 90° a la izquierda
    fig,ax=plt.subplots(figsize=(7.6,5.2)); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    g[g['ESTRATO']==0].plot(ax=ax,color='#e7e2d4',edgecolor='none')
    for e in range(1,7):
        sub=g[g['ESTRATO']==e]
        if len(sub): sub.plot(ax=ax,color=EST_COLORS[e],edgecolor='none')
    ax.set_axis_off(); ax.set_aspect('equal')
    ax.text(0.0,1.085,'Bogotá por estrato socioeconómico',transform=ax.transAxes,fontsize=14.5,fontweight='bold',color=INK,va='top')
    ax.text(0.0,1.03,'44.260 manzanas · estratificación oficial SDP/IDECA (oct-2025) · norte a la izquierda',transform=ax.transAxes,fontsize=9.3,color=INK2,va='top')
    leg=[Patch(facecolor=EST_COLORS[e],label=f'Estrato {e}') for e in range(1,7)]+[Patch(facecolor='#e7e2d4',label='No residencial')]
    ax.legend(handles=leg,loc='lower left',frameon=False,fontsize=8.4,bbox_to_anchor=(0.0,0.0),ncol=2,columnspacing=1.0)
    fig.text(0.012,0.02,'El voto de Cepeda cae del estrato 1 (62%) al 6 (10%); el de Abelardo sube al revés. Ver capítulo 5.',fontsize=6.7,color=INK2)
    plt.savefig(f'{OUT}/{fname}',dpi=170,facecolor=PAPER,bbox_inches='tight'); plt.close()
    print('✓',fname)

def bogota_upl_cepeda_map(fname):
    import matplotlib.patheffects as pe
    upl=gpd.read_file(f'{GEO}/BOG-UPL.json')[['CODIGO_UPL','NOMBRE','geometry']]
    rows=[]
    for p in d26:
        if str(p.get('dep','')).zfill(2)!='16': continue
        try: lat=float(p['lat']); lon=float(p['lon'])
        except: continue
        if not (4.3<lat<4.95 and -74.35<lon<-73.9): continue
        base=sum(int(p.get(c,0) or 0) for c in CAND)+int(p.get('votos_blanco',0) or 0)
        rows.append({'cepeda':int(p.get('cepeda',0) or 0),'base':base,'geometry':Point(lon,lat)})
    pts=gpd.GeoDataFrame(rows,crs='EPSG:4326')
    j=gpd.sjoin_nearest(pts,upl,how='left'); j=j[~j.index.duplicated(keep='first')]
    agg=j.groupby('CODIGO_UPL').agg(cep=('cepeda','sum'),base=('base','sum')).reset_index()
    agg['val']=agg.apply(lambda r: r['cep']/r['base']*100 if r['base'] else None,axis=1)
    upl=upl.merge(agg[['CODIGO_UPL','val']],on='CODIGO_UPL',how='left')
    upl,origin=rotate_gdf(upl,90)
    ptsR=pts.copy(); ptsR['geometry']=pts.geometry.rotate(90,origin=origin)
    fig,ax=plt.subplots(figsize=(7.6,5.4)); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    norm_=plt.Normalize(30,70)
    upl[upl['val'].isna()].plot(ax=ax,color=GREY,edgecolor='white',linewidth=0.6)
    sub_g=upl[upl['val'].notna()]
    sub_g.plot(ax=ax,column='val',cmap=CM_CEP,norm=norm_,edgecolor='white',linewidth=0.6)
    for _,row in sub_g.iterrows():
        c=row.geometry.representative_point()
        t=ax.annotate(row['NOMBRE'],(c.x,c.y),fontsize=5.0,color=INK,ha='center',va='center',fontweight='bold')
        t.set_path_effects([pe.withStroke(linewidth=1.6,foreground=PAPER)])
    # encuadre a la zona urbana (donde hay puestos)
    minx,miny,maxx,maxy=ptsR.total_bounds; padx=(maxx-minx)*0.06; pady=(maxy-miny)*0.10
    ax.set_xlim(minx-padx,maxx+padx); ax.set_ylim(miny-pady,maxy+pady*3.0)   # headroom arriba para títulos
    ax.set_axis_off(); ax.set_aspect('equal')
    ax.text(0.0,1.10,'Cepeda por UPL de Bogotá',transform=ax.transAxes,fontsize=14,fontweight='bold',color=INK,va='top')
    ax.text(0.0,1.035,'% Cepeda · 33 UPL · 1ª vuelta 2026 · norte a la izquierda',transform=ax.transAxes,fontsize=9,color=INK2,va='top')
    sm=plt.cm.ScalarMappable(cmap=CM_CEP,norm=norm_); sm.set_array([])
    cax=fig.add_axes([0.90,0.16,0.020,0.30]); cb=fig.colorbar(sm,cax=cax); cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=7.5,colors=INK2,length=2); cb.set_label('% Cepeda',fontsize=7.8,color=INK2); cb.ax.yaxis.set_label_position('left')
    fig.text(0.012,0.02,'Fuente: preconteo Registraduría 2026 · 1.038 puestos georreferenciados agregados a UPL (cruce punto-en-polígono).',fontsize=6.4,color=INK2)
    plt.savefig(f'{OUT}/{fname}',dpi=170,facecolor=PAPER,bbox_inches='tight'); plt.close()
    print('✓',fname)

def bogota_recuperar_map(fname):
    import matplotlib.patheffects as pe
    g=gpd.read_file(f'{GEO}/BOG-LOCALIDADX.json')
    g=g[g['LocNombre'].map(norm)!='SUMAPAZ'].copy()
    cm=BA['city_comuna'].get('Bogotá',{})
    agg={}  # fusiona duplicados por tilde (Ciudad Bolívar/Ciudad Bolivar, Mártires/Martires)
    for com,v in cm.items():
        base=v['base_votos']; k=norm(com)
        a=agg.setdefault(k,{'cep':0,'techo':0})
        a['cep']+=round(v['cep26']/100*base); a['techo']+=round((v.get('petro2v') or 0)/100*base)
    recby={k:max(0,a['techo']-a['cep']) for k,a in agg.items()}
    g['val']=g['LocNombre'].map(lambda n: recby.get(norm(n)))
    g,origin=rotate_gdf(g,90)
    fig,ax=plt.subplots(figsize=(7.6,5.6)); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    norm_=plt.Normalize(0,90000)
    g[g['val'].isna()].plot(ax=ax,color=GREY,edgecolor='white',linewidth=0.7)
    sub_g=g[g['val'].notna()]
    sub_g.plot(ax=ax,column='val',cmap=CM_REC,norm=norm_,edgecolor='white',linewidth=0.7)
    for _,row in sub_g.iterrows():
        c=row.geometry.representative_point(); v=row['val']
        t=ax.annotate(f"{row['LocNombre'].title()}\n{v/1000:.0f}k",(c.x,c.y),fontsize=5.6,color=INK,ha='center',va='center',fontweight='bold')
        t.set_path_effects([pe.withStroke(linewidth=1.6,foreground=PAPER)])
    minx,miny,maxx,maxy=g.total_bounds; padx=(maxx-minx)*0.04; pady=(maxy-miny)*0.04
    ax.set_xlim(minx-padx,maxx+padx); ax.set_ylim(miny-pady,maxy+pady*3.2); ax.set_axis_off(); ax.set_aspect('equal')
    ax.text(0.0,1.10,'Bogotá: votos por recuperar por localidad',transform=ax.transAxes,fontsize=14,fontweight='bold',color=INK,va='top')
    ax.text(0.0,1.04,'Distancia hasta el techo de Petro en 2ª vuelta 2022 · norte a la izquierda',transform=ax.transAxes,fontsize=9,color=INK2,va='top')
    sm=plt.cm.ScalarMappable(cmap=CM_REC,norm=norm_); sm.set_array([])
    cax=fig.add_axes([0.90,0.16,0.020,0.30]); cb=fig.colorbar(sm,cax=cax,format=lambda x,_:f'{x/1000:.0f}k'); cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=7.5,colors=INK2,length=2); cb.set_label('votos por recuperar',fontsize=7.6,color=INK2); cb.ax.yaxis.set_label_position('left')
    fig.text(0.012,0.02,'Fuente: preconteo Registraduría 2026 + Petro 2ª vuelta 2022 (GCS) por localidad. No incluye Sumapaz (rural).',fontsize=6.4,color=INK2)
    plt.savefig(f'{OUT}/{fname}',dpi=170,facecolor=PAPER,bbox_inches='tight'); plt.close()
    print('✓',fname)

def bogota_recuperar_upl_map(fname):
    import matplotlib.patheffects as pe
    upl=gpd.read_file(f'{GEO}/BOG-UPL.json')[['CODIGO_UPL','NOMBRE','geometry']]
    rows=[]
    for p in d26:
        if str(p.get('dep','')).zfill(2)!='16': continue
        sh=SHARE22.get(_pc(p))
        if sh is None: continue
        try: lat=float(p['lat']); lon=float(p['lon'])
        except: continue
        if not (4.3<lat<4.95 and -74.35<lon<-73.9): continue
        base=sum(int(p.get(c,0) or 0) for c in CAND)+int(p.get('votos_blanco',0) or 0)
        rows.append({'cepeda':int(p.get('cepeda',0) or 0),'techo':round(sh*base),'geometry':Point(lon,lat)})
    pts=gpd.GeoDataFrame(rows,crs='EPSG:4326')
    j=gpd.sjoin_nearest(pts,upl,how='left'); j=j[~j.index.duplicated(keep='first')]
    agg=j.groupby('CODIGO_UPL').agg(cep=('cepeda','sum'),techo=('techo','sum')).reset_index()
    agg['val']=agg.apply(lambda r: max(0,r['techo']-r['cep']),axis=1)
    upl=upl.merge(agg[['CODIGO_UPL','val']],on='CODIGO_UPL',how='left')
    upl,origin=rotate_gdf(upl,90)
    ptsR=pts.copy(); ptsR['geometry']=pts.geometry.rotate(90,origin=origin)
    fig,ax=plt.subplots(figsize=(7.6,5.6)); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    sub_g=upl[upl['val'].notna()]; vmax=max(sub_g['val'].max(),1); norm_=plt.Normalize(0,vmax)
    upl[upl['val'].isna()].plot(ax=ax,color=GREY,edgecolor='white',linewidth=0.5)
    sub_g.plot(ax=ax,column='val',cmap=CM_REC,norm=norm_,edgecolor='white',linewidth=0.5)
    for _,row in sub_g.iterrows():
        c=row.geometry.representative_point(); v=row['val']
        t=ax.annotate(f"{row['NOMBRE'].title()}\n{v/1000:.0f}k",(c.x,c.y),fontsize=4.2,color=INK,ha='center',va='center',fontweight='bold')
        t.set_path_effects([pe.withStroke(linewidth=1.4,foreground=PAPER)])
    minx,miny,maxx,maxy=ptsR.total_bounds; padx=(maxx-minx)*0.06; pady=(maxy-miny)*0.10
    ax.set_xlim(minx-padx,maxx+padx); ax.set_ylim(miny-pady,maxy+pady*3.0); ax.set_axis_off(); ax.set_aspect('equal')
    ax.text(0.0,1.10,'Bogotá: votos por recuperar por UPL',transform=ax.transAxes,fontsize=14,fontweight='bold',color=INK,va='top')
    ax.text(0.0,1.035,'Distancia hasta el techo de Petro en 2ª vuelta 2022 · 33 UPL · norte a la izquierda',transform=ax.transAxes,fontsize=9,color=INK2,va='top')
    sm=plt.cm.ScalarMappable(cmap=CM_REC,norm=norm_); sm.set_array([])
    cax=fig.add_axes([0.90,0.16,0.020,0.30]); cb=fig.colorbar(sm,cax=cax,format=lambda x,_:f'{x/1000:.0f}k'); cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=7.5,colors=INK2,length=2); cb.set_label('votos por recuperar',fontsize=7.6,color=INK2); cb.ax.yaxis.set_label_position('left')
    fig.text(0.012,0.02,'Fuente: preconteo Registraduría 2026 + Petro 2ª vuelta 2022 (GCS) · puestos georreferenciados agregados a UPL (punto-en-polígono).',fontsize=6.4,color=INK2)
    plt.savefig(f'{OUT}/{fname}',dpi=170,facecolor=PAPER,bbox_inches='tight'); plt.close()
    print('✓',fname)

MED_URBAN={'Aranjuez','Belén','Buenos Aires','Castilla','Doce de Octubre','El Poblado','Guayabal','La América','La Candelaria','Laureles Estadio','Manrique','Popular','Robledo','San Javier','Santa Cruz','Villa Hermosa'}

def _city_puestos(dep, mun, bbox=None):
    rows=[]
    for p in d26:
        if str(p.get('dep','')).zfill(2)!=dep or str(p.get('mun','')).zfill(3)!=mun: continue
        try: lat=float(p['lat']); lon=float(p['lon'])
        except: continue
        if bbox and not (bbox[0]<lon<bbox[2] and bbox[1]<lat<bbox[3]): continue
        sh=SHARE22.get(_pc(p))   # centro NO necesita techo; abst/rec se filtran luego por has_sh
        base=sum(int(p.get(c,0) or 0) for c in CAND)+int(p.get('votos_blanco',0) or 0)
        rows.append({'cep':int(p.get('cepeda',0) or 0),'faj':int(p.get('fajardo',0) or 0),'base':base,
                     'pot':int(p.get('pot',0) or 0),'urna':int(p.get('total_votos_urna',0) or 0),
                     'techo':round(sh*base) if sh is not None else 0,'has_sh':sh is not None,'geometry':Point(lon,lat)})
    return gpd.GeoDataFrame(rows,crs='EPSG:4326')

def _fill_neighbors(bar, col='val'):   # barrios sin puesto propio heredan el valor del barrio vecino más cercano (por centroide)
    bar=bar.copy(); bar['filled']=False
    have=bar[bar[col].notna()]; miss=bar[bar[col].isna()]
    if len(miss) and len(have):
        hg=gpd.GeoDataFrame({col:have[col].values},geometry=have.geometry.representative_point().values,crs=bar.crs)
        mg=gpd.GeoDataFrame({'_i':list(miss.index)},geometry=miss.geometry.representative_point().values,crs=bar.crs)
        jn=gpd.sjoin_nearest(mg,hg,how='left'); jn=jn[~jn['_i'].duplicated(keep='first')]
        for _,r in jn.iterrows(): bar.loc[r['_i'],col]=r[col]; bar.loc[r['_i'],'filled']=True
    return bar

def barrio_map(city, dep, mun, geofile, namefield, fname, metric='abst', rotate=False, figsize=(6.6,6.8),
               bbox=None, comuna_field=None, urban_set=None, label_top=10, fontsz=6.6, frame='bar', citycode=None, approx=False, vq=0.92):
    import matplotlib.patheffects as pe
    cols=[namefield,'geometry']+([comuna_field] if comuna_field else [])
    bar=gpd.read_file(geofile)[cols].to_crs('EPSG:4326').rename(columns={namefield:'NB'})
    pts=_city_puestos(dep,mun,bbox)
    if metric!='centro': pts=pts[pts['has_sh']].copy()   # abst/rec necesitan techo 2022; centro usa todos
    j=gpd.sjoin_nearest(pts,bar[['NB','geometry']],how='left'); j=j[~j.index.duplicated(keep='first')]   # sjoin contra TODOS los barrios
    if metric=='abst':
        a=j.groupby('NB').agg(pot=('pot','sum'),urna=('urna','sum'),base=('base','sum'),techo=('techo','sum')).reset_index()
        a['val']=a.apply(lambda r: max(0,round((r['pot']-r['urna'])*(2*(r['techo']/r['base'])-1))) if r['base']>0 and r['pot']>r['urna'] else 0,axis=1)
        cmap=CM_ABS; clabel='voto neto por movilizar'; ttl=f'{city}: abstención movilizable por barrio'
        sub='Voto neto de Cepeda al subir la participación'
    elif metric=='centro':
        a=j.groupby('NB').agg(faj=('faj','sum')).reset_index(); ftot=a['faj'].sum() or 1
        cla=CLA_MUN.get(citycode or (dep+mun),0)
        a['val']=a['faj'].apply(lambda f: round(0.55*f + 0.65*(cla*f/ftot)))   # 0,55·Fajardo + 0,65·Claudia(est, repartida ∝ Fajardo)
        cmap=CM_CENTRO; clabel='voto de centro transferible'; ttl=f'{city}: voto de centro por barrio'
        sub='Fajardo + Claudia transferible a Cepeda (0,55·F + 0,65·C est.)'
    else:  # rec
        a=j.groupby('NB').agg(cep=('cep','sum'),techo=('techo','sum')).reset_index()
        a['val']=(a['techo']-a['cep']).clip(lower=0)
        cmap=CM_REC; clabel='votos por recuperar'; ttl=f'{city}: votos por recuperar por barrio'
        sub='Distancia hasta el techo de Petro en 2ª vuelta 2022'
    bar=bar.merge(a[['NB','val']],on='NB',how='left')
    if comuna_field and urban_set is not None: bar=bar[bar[comuna_field].isin(urban_set)].copy()   # solo casco urbano
    bar=_fill_neighbors(bar,'val')
    if rotate: bar,origin=rotate_gdf(bar,90); pts['geometry']=pts.geometry.rotate(90,origin=origin)
    fig,ax=plt.subplots(figsize=figsize); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    sub_g=bar[bar['val'].notna()]; vmax=max(sub_g['val'].quantile(vq),1); norm_=plt.Normalize(0,vmax)
    gnan=bar[bar['val'].isna()]
    if len(gnan): gnan.plot(ax=ax,color=GREY,edgecolor='white',linewidth=0.3)   # geopandas revienta si el subset vacío (gotcha set_aspect)
    sub_g.plot(ax=ax,column='val',cmap=cmap,norm=norm_,edgecolor='white',linewidth=0.3)
    # etiquetas NUMÉRICAS sobre barrios con DATO DIRECTO (los rellenados son copias de vecino, no se numeran ni suman)
    direct=bar[(~bar['filled'])&bar['val'].notna()].sort_values('val',ascending=False)
    items=[]; seen=set()
    for _,row in direct.iterrows():
        nb=str(row['NB']).title()
        if nb in seen: continue   # un barrio puede venir en varios polígonos catastrales: numéralo una sola vez
        seen.add(nb); n=len(items)+1; c=row.geometry.representative_point()
        ax.scatter([c.x],[c.y],s=78,color='white',edgecolor=INK,linewidth=0.7,zorder=5)
        ax.annotate(str(n),(c.x,c.y),fontsize=fontsz,color=INK,ha='center',va='center',fontweight='bold',zorder=6)
        items.append({'n':n,'barrio':nb,'val':int(row['val'])})
        if len(items)>=label_top: break
    LABELS[fname]={'city':city,'metric':metric,'total':int(round(a['val'].sum())),'top':items}   # total por nombre único (no por polígono)
    fb=pts if frame=='pts' else bar   # encuadre: a los puestos (casco urbano) o a todos los barrios
    minx,miny,maxx,maxy=fb.total_bounds; padx=(maxx-minx)*0.06; pady=(maxy-miny)*0.06
    ax.set_xlim(minx-padx,maxx+padx); ax.set_ylim(miny-pady,maxy+pady*(3.0 if rotate else 2.3)); ax.set_axis_off(); ax.set_aspect('equal')
    ax.text(0.0,1.08,ttl,transform=ax.transAxes,fontsize=14,fontweight='bold',color=INK,va='top')
    ax.text(0.0,1.025,sub+(' · norte a la izquierda' if rotate else '')+f' · numerados los {len(items)} mayores (ver texto)',transform=ax.transAxes,fontsize=7.8,color=INK2,va='top')
    sm=plt.cm.ScalarMappable(cmap=cmap,norm=norm_); sm.set_array([])
    cax=fig.add_axes([0.89,0.16,0.020,0.30]); cb=fig.colorbar(sm,cax=cax,format=lambda x,_:f'{x/1000:.1f}k'); cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=7.5,colors=INK2,length=2); cb.set_label(clabel,fontsize=7.6,color=INK2); cb.ax.yaxis.set_label_position('left')
    nfill=int(bar['filled'].sum())
    src=f'Fuente: preconteo Registraduría 2026'+('' if metric=='centro' else ' + Petro 2ª vuelta 2022 (GCS)')+f' · puestos a barrio (punto-en-polígono). {nfill} barrios sin puesto propio heredan la tendencia del vecino más cercano.'
    if approx: src+=' Polígonos aproximados (celdas de puesto disueltas por barrio; sin capa catastral pública).'
    fig.text(0.012,0.02,src,fontsize=6.0,color=INK2)
    plt.savefig(f'{OUT}/{fname}',dpi=170,facecolor=PAPER,bbox_inches='tight'); plt.close()
    print(f'✓ {fname} · barrios {len(sub_g)} · rellenados {nfill} · total {LABELS[fname]["total"]:,}')

def city_recuperar_map(city, geofile, codefield, namefield, fname, mode='num', figsize=(7.2,6.2)):
    import matplotlib.patheffects as pe, re
    cm=BA['city_comuna'].get(city,{})
    def dkey(name):
        u=norm(name)
        if any(x in u for x in ('PUESTO CENSO','CONSULADO','CARCEL','EXTERIOR','CORREGIMIENTO','CORR.','NULL','MEDELLIN')): return None
        if mode=='num':
            m=re.search(r'\d+',str(name)); return int(m.group()) if m else None
        s=re.sub(r'^(no\.?\s*)?\d+\s*','',str(name).strip(),flags=re.I); return (re.sub(r'[^A-Z0-9]','',norm(s))[:8] or None)  # prefijo alfanumérico 8 chars: fusiona nombres partidos/truncados
    agg={}
    for com,v in cm.items():
        k=dkey(com)
        if k is None: continue
        base=v['base_votos']; a=agg.setdefault(k,{'cep':0,'techo':0})
        a['cep']+=round(v['cep26']/100*base); a['techo']+=round((v.get('petro2v') or 0)/100*base)
    rec={k:max(0,a['techo']-a['cep']) for k,a in agg.items()}
    g=gpd.read_file(geofile)
    def look(val):
        if mode=='num':
            m=re.search(r'\d+',str(val)); return rec.get(int(m.group())) if m else None
        return rec.get(re.sub(r'[^A-Z0-9]','',norm(val))[:8])
    g['val']=g[codefield].map(look)
    g.loc[g[namefield].isna() | (g[namefield].astype(str).str.strip().isin(['','None','nan','SN'])),'val']=None  # descarta polígonos sin nombre
    vmax=max([v for v in g['val'] if v] or [1])
    fig,ax=plt.subplots(figsize=figsize); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    norm_=plt.Normalize(0,vmax)
    gi=g[g['val'].isna()]
    if len(gi): gi.plot(ax=ax,color=GREY,edgecolor='white',linewidth=0.7)   # geopandas falla si el subset gris está vacío
    sub_g=g[g['val'].notna()]
    sub_g.plot(ax=ax,column='val',cmap=CM_REC,norm=norm_,edgecolor='white',linewidth=0.7)
    for _,row in sub_g.iterrows():
        c=row.geometry.representative_point(); v=row['val']
        nm=str(row[namefield]).replace('Comuna ','C').title()
        t=ax.annotate(f"{nm}\n{v/1000:.0f}k",(c.x,c.y),fontsize=5.6,color=INK,ha='center',va='center',fontweight='bold')
        t.set_path_effects([pe.withStroke(linewidth=1.6,foreground=PAPER)])
    ax.set_axis_off(); ax.set_aspect('equal')
    ax.text(0.0,1.05,f'{city}: votos por recuperar por comuna',transform=ax.transAxes,fontsize=14,fontweight='bold',color=INK,va='top')
    ax.text(0.0,1.005,'Distancia hasta el techo de Petro en 2ª vuelta 2022',transform=ax.transAxes,fontsize=9,color=INK2,va='top')
    sm=plt.cm.ScalarMappable(cmap=CM_REC,norm=norm_); sm.set_array([])
    cax=fig.add_axes([0.90,0.16,0.020,0.30]); cb=fig.colorbar(sm,cax=cax,format=lambda x,_:f'{x/1000:.0f}k'); cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=7.5,colors=INK2,length=2); cb.set_label('votos por recuperar',fontsize=7.6,color=INK2); cb.ax.yaxis.set_label_position('left')
    fig.text(0.012,0.02,'Fuente: preconteo Registraduría 2026 + Petro 2ª vuelta 2022 (GCS) por comuna.',fontsize=6.4,color=INK2)
    plt.savefig(f'{OUT}/{fname}',dpi=170,facecolor=PAPER,bbox_inches='tight'); plt.close()
    print('✓',fname,'· comunas con dato:',int(sub_g['val'].notna().sum()))

if __name__=='__main__':
    # 1) ganador por depto
    winner_dep('m_ganador_dep.png')
    # 2) Cepeda % por municipio
    choropleth_mun(lambda mk: BF['muni'].get(mk,{}).get('cep26'),'m_cepeda_mun.png',
        'Cepeda en cada municipio','% de Cepeda sobre válidos + blanco · 1ª vuelta 2026',CM_CEP,0,70,'% Cepeda')
    # 3) swing izquierda por municipio (Cepeda26 − Petro1V22)
    choropleth_mun(lambda mk: BF['muni'].get(mk,{}).get('dif_cep'),'m_swing_mun.png',
        'Dónde creció y dónde cayó la izquierda','Cepeda 2026 − Petro 1ª vuelta 2022 (puntos)',CM_SWING,-15,15,'pp')
    # 4) swing por depto
    choropleth_dep('dif_cep','m_swing_dep.png','El giro de la izquierda por departamento',
        'Cepeda 2026 − Petro 1ª vuelta 2022 (puntos)',CM_SWING,-12,12,'pp')
    # 5) derecha por depto
    choropleth_dep('der26','m_derecha_dep.png','La fuerza de la derecha hoy',
        'Abelardo + Paloma · % válidos + blanco · 2026',CM_DER,20,75,'% derecha')
    # 6) espacio de recuperación 2V por depto (Petro 2V22 − Cepeda 26)
    g=BA['depto']
    for k,v in g.items():
        v['_rec']=round((v['petro2v']-v['cep26']),1) if v.get('petro2v') and v.get('cep26') else None
    choropleth_dep('_rec','m_recuperacion_dep.png','El techo por recuperar en 2ª vuelta',
        'Petro 2ª vuelta 2022 − Cepeda hoy (puntos de margen disponible)',CM_REC,0,30,'pp')
    # 7) abstención por municipio
    choropleth_mun(lambda mk: (100-BF['muni'][mk]['part26']) if mk in BF['muni'] and BF['muni'][mk].get('part26') else None,
        'm_abstencion_mun.png','La geografía de la abstención','% que no votó · 1ª vuelta 2026',CM_ABS,25,65,'% abstención')
    # 8) Bogotá estrato (manzana) — rotado 90° izq
    bogota_estrato_map('m_bogota_estrato.png')
    # 9) Bogotá Cepeda por UPL — rotado 90° izq
    bogota_upl_cepeda_map('m_bogota_upl_cepeda.png')
    # 10) Bogotá votos por recuperar por localidad — rotado 90° izq
    bogota_recuperar_map('m_bogota_recuperar.png')
    # 10b) Bogotá votos por recuperar por UPL (más fino que localidad) — rotado 90° izq
    bogota_recuperar_upl_map('m_bogota_recuperar_upl.png')
    # 10c) MAPAS POR BARRIO · 9 ciudades × 3 campañas (centro y recuperación: todas · abstención: solo zonas fuertes)
    CITY_BARRIO=[  # name, slug, code, geojson, namefield, opts (mismos para las 3 métricas de la ciudad)
        ('Bogotá','bogota','16001','BOG-BARRIOS-CATASTRALES.json','nombre',dict(rotate=True,bbox=(-74.35,4.3,-73.9,4.95),figsize=(7.8,5.8),fontsz=5.6)),
        ('Medellín','medellin','01001','MEDELLIN_BARRIOS_OFICIAL.json','NOMBRE',dict(bbox=(-75.75,6.1,-75.45,6.40),comuna_field='COMUNA',urban_set=MED_URBAN,figsize=(6.4,7.0),vq=0.90)),
        ('Cali','cali','31001','CALI-BARRIOS.json','barrio',dict(bbox=(-76.60,3.30,-76.42,3.52),figsize=(6.8,6.6))),
        ('Barranquilla','barranquilla','03001','BARRANQUILLA-BARRIOS.json','NOMBRE',dict(bbox=(-74.92,10.88,-74.74,11.12),figsize=(6.0,6.9))),
        ('Cartagena','cartagena','05001','CARTAGENA-BARRIOS.json','NOMBRE',dict(bbox=(-75.58,10.33,-75.45,10.50),frame='pts',figsize=(6.4,6.8))),
        ('Manizales','manizales','09001','MANIZALES-BARRIOS.json','BARRIOS',dict(bbox=(-75.57,5.00,-75.41,5.12),figsize=(7.4,5.2),vq=0.90)),
        ('Pereira','pereira','24001','PEREIRA-BARRIOS.json','NOMBRE',dict(bbox=(-75.78,4.76,-75.64,4.84),figsize=(7.0,5.6))),
        ('Bucaramanga','bucaramanga','27001','BUCARAMANGA-BARRIOS.json','barrio',dict(bbox=(-73.18,7.04,-73.08,7.19),figsize=(5.8,7.0),vq=0.90)),
        ('Cúcuta','cucuta','25001','CUCUTA-BARRIOS.json','barrio',dict(bbox=(-72.57,7.84,-72.45,7.97),figsize=(6.6,6.4),vq=0.90)),  # capa REAL (424 barrios · GeoServer geoservicioside.cucuta vía WFS)
    ]
    for name,slug,code,gj,nf,opts in CITY_BARRIO:
        dep,mun=code[:2],code[2:]
        barrio_map(name,dep,mun,f'{GEO}/{gj}',nf,f'm_{slug}_centro_barrio.png',metric='centro',citycode=code,**opts)
        barrio_map(name,dep,mun,f'{GEO}/{gj}',nf,f'm_{slug}_recuperar_barrio.png',metric='rec',**opts)
        barrio_map(name,dep,mun,f'{GEO}/{gj}',nf,f'm_{slug}_abstencion_barrio.png',metric='abst',**opts)   # las 9, también las débiles (consistencia)
    # zonas fuertes de abstención añadidas (solo abstención). Buenaventura/Soledad/Quibdó con capa REAL; Pasto/SantaMarta/Palmira/Tumaco/Sincelejo Voronoi aprox.
    ABST_EXTRA=[
        ('Buenaventura','buenaventura','31019','BUENAVENTURA-BARRIOS.json','barrio',dict(bbox=(-77.10,3.83,-76.96,3.90),figsize=(6.8,5.2),vq=0.90)),  # capa REAL (110 barrios, services2.arcgis.com/EsyoEkMlTcucSCqP)
        ('Quibdó','quibdo','17001','QUIBDO-BARRIOS.json','barrio',dict(bbox=(-76.68,5.66,-76.61,5.73),figsize=(6.0,6.8),vq=0.90)),  # capa REAL (60 barrios · ArcGIS services4/3OgCxmjOXo22H0MY); 43 puestos caen en 20 barrios
        ('Pasto','pasto','23001','PASTO-BARRIOS.json','barrio',dict(bbox=(-77.34,1.17,-77.23,1.25),frame='pts',figsize=(6.4,6.4),approx=True)),
        ('Santa Marta','santamarta','21001','SANTAMARTA-BARRIOS.json','barrio',dict(bbox=(-74.24,11.19,-74.10,11.27),frame='pts',figsize=(6.6,5.8),approx=True)),
        ('Palmira','palmira','31079','PALMIRA-BARRIOS.json','barrio',dict(bbox=(-76.35,3.50,-76.26,3.58),frame='pts',figsize=(6.2,6.4),approx=True)),
        ('Tumaco','tumaco','23139','TUMACO-BARRIOS.json','barrio',dict(bbox=(-78.84,1.74,-78.66,1.86),frame='pts',figsize=(6.4,6.2),approx=True)),
        ('Sincelejo','sincelejo','28001','SINCELEJO-BARRIOS.json','barrio',dict(bbox=(-75.50,9.23,-75.36,9.39),frame='pts',figsize=(6.4,6.4),approx=True)),
        ('Soledad','soledad','03052','SOLEDAD-BARRIOS.json','barrio',dict(bbox=(-74.84,10.86,-74.74,10.95),figsize=(6.4,6.4),vq=0.90)),  # capa REAL (239 barrios · GeoServer catastrosoledad vía WFS)
    ]
    for name,slug,code,gj,nf,opts in ABST_EXTRA:
        barrio_map(name,code[:2],code[2:],f'{GEO}/{gj}',nf,f'm_{slug}_abstencion_barrio.png',metric='abst',**opts)
    json.dump(LABELS,open(f'{OUT}/barrio_labels.json','w'),ensure_ascii=False,indent=1)
    print(f'\n✓ mapas listos · {len(LABELS)} mapas por barrio · barrio_labels.json')
