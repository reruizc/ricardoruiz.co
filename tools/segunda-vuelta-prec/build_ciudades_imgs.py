#!/usr/bin/env python3
# Imágenes públicas (1080x1080) del hilo "las 4 grandes ciudades, barrio por barrio".
# Sirven para X y para el carrusel de IG. Identidad: paper #f1eee4, títulos Arima,
# kicker oxblood, Cepeda rojo / Abelardo azul, logo + crédito. SIN watermark (públicas).
# -> rrss/twitter/ciudades-2v-png/{00_portada, <slug>_mapa, <slug>_a1, <slug>_a2, 13_cierre}.png
import os, json, warnings
import numpy as np, geopandas as gpd, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle, FancyArrow, Circle
from matplotlib.colors import to_rgb
from shapely.ops import transform
from PIL import Image, ImageOps, ImageDraw
warnings.filterwarnings('ignore')

OUT = 'rrss/twitter/ciudades-2v-png'; os.makedirs(OUT, exist_ok=True)
GEO = 'Bases de datos/output_pacto_1v_2026/geo'
DATA = json.load(open('Bases de datos/output_2v/ciudades-barrios-2v.json'))
GEOFILE = {'bogota':'BOG-BARRIOS-CATASTRALES.json','medellin':'MEDELLIN_BARRIOS_OFICIAL.json',
           'barranquilla':'BARRANQUILLA-BARRIOS.json','cali':'CALI-BARRIOS.json'}

PAPER='#f1eee4'; INK='#1a1510'; OX='#8a1e16'; MUT='#6b6258'; GREY='#cfc7b6'
RED='#c0392b'; BLUE='#1f47cc'
CEPE=['#f2a59d','#e2685c','#cf4135','#9c1e15']; ABEL=['#9db4f5','#5b82ef','#3a5bd0','#1f2a8c']
AR =fm.FontProperties(fname='tools/edad-1v-2026/fonts/Arima-Bold.ttf')
ARS=fm.FontProperties(fname='tools/edad-1v-2026/fonts/Arima-SemiBold.ttf')
IN =fm.FontProperties(fname='tools/pacto-1v-2026/fonts/Inter-Regular.ttf')
INB=fm.FontProperties(fname='tools/pacto-1v-2026/fonts/Inter-Bold.ttf')
for f in ['tools/pacto-1v-2026/fonts/Inter-Regular.ttf','tools/pacto-1v-2026/fonts/Inter-Bold.ttf']:
    fm.fontManager.addfont(f)
plt.rcParams['font.family']='Inter'
LOGO='Bases de datos/output_abelardo_cartagena/logo_ricardoruiz.png'

CITY = {
 'bogota':       dict(name='Bogotá',       fld='nombre', sub='Cepeda 53,7% · Abelardo 46,3% · 423 barrios vs 194', rot=True),
 'medellin':     dict(name='Medellín',     fld='NOMBRE', sub='Abelardo 66,3% · Cepeda 33,7% · 134 barrios vs 25', rot=False),
 'barranquilla': dict(name='Barranquilla', fld='NOMBRE', sub='Cepeda 54,8% · Abelardo 45,2% · 67 barrios vs 29', rot=False),
 'cali':         dict(name='Cali',         fld='barrio', sub='Cepeda 60,6% · Abelardo 39,4% · 118 barrios vs 32', rot=False),
}

def canvas():
    fig=plt.figure(figsize=(10.8,10.8),dpi=100); fig.patch.set_facecolor(PAPER)
    return fig
def logo(fig,x,y,w):
    lg=Image.open(LOGO).convert('RGBA'); r=lg.height/lg.width
    axl=fig.add_axes([x,y,w,w*r]); axl.imshow(lg); axl.axis('off')
def credit(fig,n=None):
    fig.text(0.93,0.038,'ricardoruiz.co',fontsize=15,color=MUT,fontproperties=INB,ha='right',va='center')
    if n is not None:
        fig.text(0.5,0.038,f'{n} / 14',fontsize=13,color=MUT,fontproperties=IN,ha='center',va='center')
def kicker(fig,t,y=0.945):
    fig.text(0.066,y,t,fontsize=18,color=OX,fontproperties=INB,va='center')
def title(fig,t,y=0.885,fs=46):
    fig.text(0.066,y,t,fontsize=fs,color=INK,fontproperties=AR,va='top',linespacing=1.04)
def duo_circle(path,dark,size=520,ybias=0.08):
    im=Image.open(path).convert('L'); im=ImageOps.autocontrast(im,cutoff=1)
    im=ImageOps.colorize(im,black=dark,white='#efe9db').convert('RGBA')
    w,h=im.size; s=min(w,h); x0=(w-s)//2; y0=int((h-s)*ybias)
    im=im.crop((x0,y0,x0+s,y0+s)).resize((size,size)).convert('RGBA')
    m=Image.new('L',(size,size),0); ImageDraw.Draw(m).ellipse((0,0,size-1,size-1),fill=255); im.putalpha(m)
    return im

def _rotg(geom,cx=-74.08,cy=4.65): return transform(lambda x,y,z=None:(cx-(y-cy),cy+(x-cx)),geom)

def winrgba(d,fill):
    w=d['w2']; m=abs(d['m2']); a=0.34+0.66*min(1,m/55.0)
    base=BLUE if w=='A' else RED
    return (*to_rgb(base), a*0.42 if fill else a)

# ---------- geo + colores por ciudad (reutilizable) ----------
def city_geo_colors(slug):
    cfg=CITY[slug]; meta=DATA[slug]['meta']; bd=DATA[slug]['b']
    gj=json.load(open(f"{GEO}/{GEOFILE[slug]}"))
    g=gpd.GeoDataFrame.from_features(gj['features']).set_crs('EPSG:4326').reset_index(drop=True)
    keyfld=meta['keyfld']; cols=[]
    for i,f in enumerate(gj['features']):
        k=str(i) if keyfld=='__idx' else str(f['properties'].get(keyfld))
        d=bd.get(k); cols.append(winrgba(d,d['f']) if d else (*to_rgb(GREY),0.4))
    if cfg['rot']: g=g.set_geometry(g.geometry.apply(_rotg))
    return g,cols

def plot_into(ax,slug,lw=0.12):
    g,cols=city_geo_colors(slug); ax.set_facecolor(PAPER); ax.axis('off')
    g.plot(ax=ax,color=cols,edgecolor='white',linewidth=lw)
    minx,miny,maxx,maxy=g.total_bounds; dx,dy=maxx-minx,maxy-miny; pad=0.04*max(dx,dy)
    ax.set_xlim(minx-pad,maxx+pad); ax.set_ylim(miny-pad,maxy+pad); ax.set_aspect('equal')

# ---------- MAPA por ciudad ----------
def map_city(slug,n):
    cfg=CITY[slug]
    fig=canvas()
    kicker(fig,'SEGUNDA VUELTA 2026 · 21 DE JUNIO')
    title(fig,f"{cfg['name']}, barrio por barrio",y=0.905,fs=42)
    fig.text(0.066,0.838,cfg['sub'],fontsize=19,color=MUT,fontproperties=IN,va='center')
    ax=fig.add_axes([0.03,0.085,0.94,0.715]); plot_into(ax,slug)
    # leyenda
    ov=fig.add_axes([0,0,1,1]); ov.set_xlim(0,1); ov.set_ylim(0,1); ov.axis('off'); ov.patch.set_alpha(0)
    ov.add_patch(Rectangle((0.066,0.052),0.018,0.018,color=RED))
    fig.text(0.092,0.061,'Cepeda',fontsize=16,color=RED,fontproperties=INB,va='center')
    ov.add_patch(Rectangle((0.235,0.052),0.018,0.018,color=BLUE))
    fig.text(0.261,0.061,'Abelardo',fontsize=16,color=BLUE,fontproperties=INB,va='center')
    fig.text(0.41,0.061,'tono = ventaja del ganador · translúcido = vecino',fontsize=12.5,color=MUT,fontproperties=IN,va='center')
    credit(fig,n)
    fig.savefig(f'{OUT}/{slug}_mapa.png',facecolor=PAPER); plt.close(fig)

# ---------- ANÁLISIS 1: dos ciudades en una (leaderboard) ----------
def a1_city(slug,n):
    cfg=CITY[slug]; bd=DATA[slug]['b']
    def pa(d): t=d['c2']+d['a2']; return d['a2']/t if t>0 else 0
    direct=[d for d in bd.values() if not d['f'] and (d['c2']+d['a2'])>800]
    topA=sorted(direct,key=lambda d:-pa(d))[:5]
    topC=sorted(direct,key=lambda d: pa(d))[:5]
    fig=canvas()
    kicker(fig,f"{cfg['name'].upper()} · LA DIVISORIA DE ESTRATO")
    title(fig,"Dos ciudades\nen una",y=0.905,fs=52)
    fig.text(0.066,0.745,'Los barrios donde cada uno arrasó en 2ª vuelta',fontsize=20,color=MUT,fontproperties=IN,va='center')
    ov=fig.add_axes([0,0,1,1]); ov.set_xlim(0,1); ov.set_ylim(0,1); ov.axis('off'); ov.patch.set_alpha(0)
    def col(x,head,hcol,lst,pctf):
        ov.add_patch(Rectangle((x,0.658),0.018,0.018,color=hcol))
        fig.text(x+0.028,0.667,head,fontsize=22,color=hcol,fontproperties=INB,va='center')
        for j,d in enumerate(lst):
            yy=0.585-j*0.092
            fig.text(x,yy,d['n'][:22],fontsize=20,color=INK,fontproperties=IN,va='center')
            fig.text(x+0.40,yy,f'{pctf(d)*100:.0f}%',fontsize=23,color=hcol,fontproperties=INB,va='center',ha='right')
    col(0.066,'Más Cepeda',RED,topC,lambda d:1-pa(d))
    col(0.535,'Más Abelardo',BLUE,topA,pa)
    ov.add_line(plt.Line2D([0.50,0.50],[0.12,0.64],color=GREY,lw=1.2))
    fig.text(0.066,0.082,'% de los dos candidatos en cada barrio · preconteo 2V por mesa',fontsize=13,color=MUT,fontproperties=IN,va='center')
    logo(fig,0.066,0.028,0.17); credit(fig,n)
    fig.savefig(f'{OUT}/{slug}_a1.png',facecolor=PAPER); plt.close(fig)

# ---------- ANÁLISIS 2: el cambio 1V -> 2V ----------
def a2_city(slug,n):
    cfg=CITY[slug]; m=DATA[slug]['meta']
    def split(R):
        c,a=m['cep'+R],m['abe'+R]; t=c+a; return 100*c/t,100*a/t
    pc1,pa1=split('1'); pc2,pa2=split('2')
    lead='Cepeda' if m['m2']<0 else 'Abelardo'; lc=RED if lead=='Cepeda' else BLUE
    dm=abs(m['m2'])-abs(m['m1'])
    fig=canvas()
    kicker(fig,f"{cfg['name'].upper()} · EL CAMBIO ENTRE VUELTAS")
    if abs(dm)<0.6: tt='El margen casi\nno se movió'
    elif dm>0: tt=f'{lead} amplió\nsu ventaja'
    else: tt='La ciudad\nse cerró'
    title(fig,tt,y=0.905,fs=52)
    fig.text(0.066,0.745,f"Cómo votó {cfg['name']} en cada vuelta",fontsize=20,color=MUT,fontproperties=IN,va='center')
    # encabezado Cepeda / Abelardo + dos barras 100% apiladas (Cepeda rojo izq, Abelardo azul der)
    axb=fig.add_axes([0.066,0.40,0.87,0.26]); axb.set_xlim(0,100); axb.set_ylim(-0.2,2.5); axb.axis('off')
    axb.text(0,2.30,'Cepeda',fontsize=16,color=RED,fontproperties=INB,va='center')
    axb.text(100,2.30,'Abelardo',fontsize=16,color=BLUE,fontproperties=INB,va='center',ha='right')
    for i,(lbl,pc,pa) in enumerate([('1ª vuelta',pc1,pa1),('2ª vuelta',pc2,pa2)]):
        y=1-i
        axb.text(0,y+0.40,lbl,fontsize=15,color=INK,fontproperties=INB,va='center')
        axb.add_patch(Rectangle((0,y-0.27),pc,0.54,color=RED))
        axb.add_patch(Rectangle((pc,y-0.27),pa,0.54,color=BLUE))
        axb.text(1.6,y,f'{pc:.1f}'.replace('.',','),fontsize=19,color='white',fontproperties=INB,va='center')
        axb.text(98.4,y,f'{pa:.1f}'.replace('.',','),fontsize=19,color='white',fontproperties=INB,va='center',ha='right')
    # callout del margen con flecha dibujada
    ov=fig.add_axes([0,0,1,1]); ov.set_xlim(0,1); ov.set_ylim(0,1); ov.axis('off'); ov.patch.set_alpha(0)
    fig.text(0.066,0.305,'Margen del ganador',fontsize=18,color=MUT,fontproperties=IN,va='center')
    fig.text(0.066,0.225,f"{abs(m['m1']):.1f}".replace('.',','),fontsize=56,color=MUT,fontproperties=AR,va='center')
    ov.annotate('',xy=(0.345,0.227),xytext=(0.255,0.227),arrowprops=dict(arrowstyle='-|>',color=INK,lw=3.2,mutation_scale=22))
    fig.text(0.37,0.225,f"{abs(m['m2']):.1f} pts".replace('.',','),fontsize=56,color=lc,fontproperties=AR,va='center')
    sign='+' if dm>0 else '−'
    fig.text(0.066,0.135,f"{sign}{abs(dm):.1f} pts hacia {lead} entre la 1ª y la 2ª vuelta".replace('.',','),fontsize=19,color=INK,fontproperties=INB,va='center')
    logo(fig,0.066,0.03,0.17); credit(fig,n)
    fig.savefig(f'{OUT}/{slug}_a2.png',facecolor=PAPER); plt.close(fig)

# ---------- PORTADA (contraste Bogotá vs Medellín) ----------
def portada():
    fig=canvas()
    kicker(fig,'ELECCIONES COLOMBIA 2026 · SEGUNDA VUELTA')
    title(fig,'Las 4 grandes ciudades,\nbarrio por barrio',y=0.905,fs=46)
    # dos mapas lado a lado: Bogotá (rojo) vs Medellín (azul)
    axb=fig.add_axes([0.045,0.345,0.45,0.40]); plot_into(axb,'bogota',lw=0.10)
    axm=fig.add_axes([0.515,0.345,0.45,0.40]); plot_into(axm,'medellin',lw=0.10)
    ov=fig.add_axes([0,0,1,1]); ov.set_xlim(0,1); ov.set_ylim(0,1); ov.axis('off'); ov.patch.set_alpha(0)
    fig.text(0.27,0.305,'Bogotá',fontsize=27,color=INK,fontproperties=AR,ha='center',va='center')
    fig.text(0.27,0.272,'gana Cepeda',fontsize=17,color=RED,fontproperties=INB,ha='center',va='center')
    fig.text(0.74,0.305,'Medellín',fontsize=27,color=INK,fontproperties=AR,ha='center',va='center')
    fig.text(0.74,0.272,'gana Abelardo',fontsize=17,color=BLUE,fontproperties=INB,ha='center',va='center')
    fig.text(0.066,0.205,'Abelardo fue presidente por 0,98 puntos. Pero perdió 3 de las\n4 ciudades más grandes. El mapa de la 2ª vuelta, polígono a polígono.',
             fontsize=20,color=MUT,fontproperties=IN,va='top',linespacing=1.34)
    logo(fig,0.066,0.045,0.20); credit(fig,1)
    fig.savefig(f'{OUT}/00_portada.png',facecolor=PAPER); plt.close(fig)

# ---------- CIERRE ----------
def cierre():
    fig=canvas()
    kicker(fig,'EL VEREDICTO')
    title(fig,'Cepeda ganó las\nciudades. Abelardo\nganó el país.',y=0.875,fs=52)
    ov=fig.add_axes([0,0,1,1]); ov.set_xlim(0,1); ov.set_ylim(0,1); ov.axis('off'); ov.patch.set_alpha(0)
    rows=[('Bogotá','Cepeda','+7,4'),('Cali','Cepeda','+21,3'),
          ('Barranquilla','Cepeda','+9,6'),('Medellín','Abelardo','+32,7')]
    for j,(c,w,mg) in enumerate(rows):
        yy=0.55-j*0.075
        col=RED if 'Cepeda' in w else BLUE
        fig.text(0.066,yy,c,fontsize=24,color=INK,fontproperties=INB,va='center')
        ov.add_patch(Rectangle((0.45,yy-0.009),0.017,0.017,color=col))
        fig.text(0.485,yy,w,fontsize=22,color=col,fontproperties=IN,va='center')
        fig.text(0.86,yy,mg,fontsize=24,color=col,fontproperties=INB,va='center',ha='right')
    fig.text(0.066,0.205,'La 2ª vuelta no se ganó en las ciudades: se ganó afuera,\nen los municipios medianos y la periferia.',
             fontsize=21,color=MUT,fontproperties=IN,va='top',linespacing=1.34)
    fig.text(0.066,0.115,'Explóralo barrio por barrio  —  ricardoruiz.co/ciudades-2v-barrios.html',
             fontsize=16,color=OX,fontproperties=INB,va='center')
    logo(fig,0.066,0.035,0.20); credit(fig,14)
    fig.savefig(f'{OUT}/13_cierre.png',facecolor=PAPER); plt.close(fig)

n=1; portada()
order=['bogota','medellin','barranquilla','cali']
nmap={'bogota':2,'medellin':5,'barranquilla':8,'cali':11}
for slug in order:
    b=nmap[slug]; map_city(slug,b); a1_city(slug,b+1); a2_city(slug,b+2)
    print('  ✓',slug)
cierre()
print('->',OUT,'· 14 imágenes 1080x1080')
