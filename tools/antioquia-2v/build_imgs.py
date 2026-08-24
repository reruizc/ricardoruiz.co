# -*- coding: utf-8 -*-
"""Imágenes de impacto: el papel de Antioquia / Medellín en la 2V 2026.
Identidad de proyecto: paper #f1eee4, Arima, Cepeda rojo / Abelardo azul.
"""
import json, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch, Rectangle
import geopandas as gpd

BASE = '/Users/ricardoruiz/ricardoruiz.co'
D2V  = f'{BASE}/Bases de datos/output_2v'
GEO  = f'{BASE}/Bases de datos/output_pacto_1v_2026/geo'
OUT  = f'{BASE}/rrss/antioquia-2v'
os.makedirs(OUT, exist_ok=True)

# ---- fuentes
FD = f'{BASE}/tools/edad-1v-2026/fonts'
for f in ['Arima-Bold.ttf','Arima-SemiBold.ttf']:
    fm.fontManager.addfont(f'{FD}/{f}')
ARIMA = fm.FontProperties(fname=f'{FD}/Arima-Bold.ttf').get_name()
plt.rcParams['font.family'] = ARIMA

# ---- paleta
PAPER='#f1eee4'; INK='#1a1510'; OX='#8a1e16'
CEP='#c0392b'; ABE='#1f47cc'
MUTE='#6b6355'

def sep(n): return f'{n:,.0f}'.replace(',', '.')

# ============================================================ datos
agg = json.load(open(f'{D2V}/agg_municipio.json'))
Ncep=sum(m['cep2'] for m in agg); Nabe=sum(m['abe2'] for m in agg)
NAC_MARGEN = Nabe-Ncep
ant=[m for m in agg if m['dep']=='01' and m['has2v']]
Acep=sum(m['cep2'] for m in ant); Aabe=sum(m['abe2'] for m in ant)
ANT_MARGEN = Aabe-Acep
SIN_ANT = (Ncep-Acep)-(Nabe-Aabe)
ANT_AWIN=sum(1 for m in ant if m['abe2']>m['cep2']); ANT_CWIN=len(ant)-ANT_AWIN
med=[m for m in agg if m['cod5']=='01001'][0]
MED_ABE_PCT = med['abe2']/(med['abe2']+med['cep2'])*100

# ============================================================ 1) HERO Antioquia decide
def img1():
    fig,ax=plt.subplots(figsize=(10.8,10.8),dpi=100)
    fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    ax.set_xlim(0,100); ax.set_ylim(0,100); ax.axis('off')

    ax.text(6,94,'SEGUNDA VUELTA · 2026',fontsize=15,color=OX,fontproperties=fm.FontProperties(fname=f'{FD}/Arima-SemiBold.ttf'))
    ax.text(6,88,'Antioquia eligió',fontsize=44,color=INK,va='top')
    ax.text(6,80.5,'al presidente',fontsize=44,color=INK,va='top')

    # comparación de barras: margen nacional vs margen Antioquia
    y0=54; h=8
    maxv=ANT_MARGEN
    def bar(y,val,lab,col,sub):
        w=88*val/maxv
        ax.add_patch(FancyBboxPatch((6,y),w,h,boxstyle='round,pad=0.02,rounding_size=0.6',
                    fc=col,ec='none'))
        ax.text(6,y+h+1.6,lab,fontsize=15.5,color=INK,va='bottom')
        ax.text(6+w-1.5 if w>26 else 6+w+1.5, y+h/2, sep(val),
                fontsize=22,color='white' if w>26 else INK,va='center',
                ha='right' if w>26 else 'left')
        ax.text(6,y-2.4,sub,fontsize=11.5,color=MUTE,va='top',
                fontproperties=fm.FontProperties(fname=f'{FD}/Arima-SemiBold.ttf'))
    bar(y0,ANT_MARGEN,'Ventaja de Abelardo SOLO en Antioquia',ABE,
        f'{ANT_AWIN} de 125 municipios los ganó Abelardo · Cepeda solo {ANT_CWIN}')
    bar(y0-24,NAC_MARGEN,'Ventaja de Abelardo en TODO el país',INK,
        f'El margen con que Abelardo ganó la presidencia')

    # remate
    ax.add_patch(Rectangle((6,6),88,17.5,fc='#e7e2d5',ec='none'))
    ratio=ANT_MARGEN/NAC_MARGEN
    ax.text(9,19.5,f'El margen de Antioquia fue {ratio:.1f} veces el margen nacional.',
            fontsize=18,color=INK,va='center')
    ax.text(9,12.5,f'Sin Antioquia, Cepeda sería presidente por {sep(SIN_ANT)} votos.',
            fontsize=18,color=OX,va='center')

    ax.text(6,2.4,'ricardoruiz.co  ·  preconteo 2V, escrutinio por mesa',fontsize=10.5,color=MUTE)
    fig.savefig(f'{OUT}/1-antioquia-decide.png',facecolor=PAPER,bbox_inches='tight',pad_inches=0.28)
    plt.close(); print('OK 1')

# ============================================================ 2) MAPA Antioquia municipal
def img2():
    g=gpd.read_file(f'{GEO}/mps/01.json')
    win={}; mrg={}
    for m in ant:
        win[m['mun']]= 'A' if m['abe2']>m['cep2'] else 'C'
        tot=m['abe2']+m['cep2']
        mrg[m['mun']]= (m['abe2']-m['cep2'])/tot if tot else 0
    def col(row):
        mn=str(row.get('mun_elec') or row.get('mun_electoral')).zfill(3)
        w=win.get(mn); v=mrg.get(mn,0)
        if w is None: return '#d8d2c4'
        if w=='A':
            t=min(abs(v)/0.6,1); return _mix('#dfe4f7',ABE,0.25+0.75*t)
        t=min(abs(v)/0.6,1); return _mix('#f6dcd8',CEP,0.25+0.75*t)
    g['__c']=g.apply(col,axis=1)

    fig,ax=plt.subplots(figsize=(10.8,11.4),dpi=100)
    fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    g.plot(ax=ax,color=g['__c'],ec='white',lw=0.35)
    # Medellín contorno
    gm=g[g.apply(lambda r:str(r.get('mun_elec')).zfill(3)=='001',axis=1)]
    gm.boundary.plot(ax=ax,ec=INK,lw=1.4)
    c=gm.geometry.iloc[0].centroid
    ax.annotate('Medellín',(c.x,c.y),xytext=(c.x+0.9,c.y+0.7),fontsize=13,color=INK,
                fontproperties=fm.FontProperties(fname=f'{FD}/Arima-SemiBold.ttf'),
                arrowprops=dict(arrowstyle='-',color=INK,lw=1))
    ax.axis('off'); ax.set_aspect('equal')

    ax.set_title('')
    fig.text(0.06,0.95,'SEGUNDA VUELTA · 2026',fontsize=14,color=OX,
             fontproperties=fm.FontProperties(fname=f'{FD}/Arima-SemiBold.ttf'))
    fig.text(0.06,0.905,'Antioquia se pintó de azul',fontsize=34,color=INK)
    fig.text(0.06,0.045,
             f'Abelardo ganó {ANT_AWIN} de los 125 municipios. Cepeda apenas {ANT_CWIN}.\n'
             'Intensidad = margen. ricardoruiz.co · preconteo 2V por mesa',
             fontsize=12.5,color=MUTE)
    # leyenda (rectángulos reales, sin depender de glifos)
    axl=fig.add_axes([0.06,0.09,0.30,0.06]); axl.axis('off'); axl.set_xlim(0,1); axl.set_ylim(0,1)
    axl.add_patch(Rectangle((0.0,0.55),0.05,0.32,fc=ABE,ec='none'))
    axl.text(0.07,0.71,'Ganó Abelardo',fontsize=12.5,color=INK,va='center')
    axl.add_patch(Rectangle((0.0,0.08),0.05,0.32,fc=CEP,ec='none'))
    axl.text(0.07,0.24,'Ganó Cepeda',fontsize=12.5,color=INK,va='center')
    fig.savefig(f'{OUT}/2-mapa-antioquia.png',facecolor=PAPER,bbox_inches='tight',pad_inches=0.25)
    plt.close(); print('OK 2')

# ============================================================ 3) MAPA Medellín por barrio
def img3():
    g=gpd.read_file(f'{GEO}/MEDELLIN_BARRIOS_OFICIAL.json')
    b=json.load(open(f'{D2V}/ciudades-barrios-2v.json'))['medellin']['b']
    def col(row):
        k=str(row['CODIGO'])
        v=b.get(k)
        if not v: return '#d8d2c4'
        tot=v.get('c2',0)+v.get('a2',0)
        if tot<50: return '#d8d2c4'
        pa=v['a2']/tot  # share Abelardo
        if pa>=0.5:
            t=min((pa-0.5)/0.45,1); return _mix('#dfe4f7',ABE,0.2+0.8*t)
        t=min((0.5-pa)/0.25,1); return _mix('#f6dcd8',CEP,0.2+0.8*t)
    g['__c']=g.apply(col,axis=1)
    URB = ~g['COMUNA'].fillna('').str.startswith('Corregimiento')
    fig,ax=plt.subplots(figsize=(10.8,10.2),dpi=100)
    fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    # recorte al casco urbano (comunas, sin corregimientos)
    minx,miny,maxx,maxy=g[URB].total_bounds
    g.plot(ax=ax,color=g['__c'],ec='white',lw=0.2)
    px=(maxx-minx)*0.04; py=(maxy-miny)*0.04
    ax.set_xlim(minx-px,maxx+px); ax.set_ylim(miny-py,maxy+py)
    ax.axis('off'); ax.set_aspect('equal')

    def cluster(comunas):
        gs=g[g['COMUNA'].isin(comunas)]
        return gs.geometry.union_all().centroid
    cp=cluster(['El Poblado'])
    cn=cluster(['Popular','Santa Cruz','Manrique'])
    sb=fm.FontProperties(fname=f'{FD}/Arima-SemiBold.ttf')
    box=lambda c: dict(boxstyle='round,pad=0.4',fc=PAPER,ec=c,lw=1.2,alpha=0.94)
    ax.annotate('El Poblado\n94% Abelardo',(cp.x,cp.y),
                xytext=(maxx+px*0.2,miny+(maxy-miny)*0.30),ha='left',fontsize=13,color=ABE,
                fontproperties=sb,bbox=box(ABE),
                arrowprops=dict(arrowstyle='-',color=ABE,lw=1.3))
    ax.annotate('Nororiente popular\n(Popular, Manrique):\ngana Cepeda',(cn.x,cn.y),
                xytext=(minx-px*0.2,maxy+(maxy-miny)*0.02),ha='left',va='top',fontsize=13,color=CEP,
                fontproperties=sb,bbox=box(CEP),
                arrowprops=dict(arrowstyle='-',color=CEP,lw=1.3))

    fig.text(0.06,0.965,'SEGUNDA VUELTA · 2026 · MEDELLÍN',fontsize=13.5,color=OX,
             fontproperties=fm.FontProperties(fname=f'{FD}/Arima-SemiBold.ttf'))
    fig.text(0.06,0.918,'Una ciudad partida por estrato',fontsize=33,color=INK)
    fig.text(0.06,0.045,
             f'Abelardo ganó Medellín con {MED_ABE_PCT:.1f}%. En los barrios de El Poblado llegó al 94%;\n'
             'en la periferia popular (Popular, Robledo, Manrique) ganó Cepeda.\n'
             'ricardoruiz.co · preconteo 2V por mesa, cruce a barrio',
             fontsize=12,color=MUTE)
    fig.savefig(f'{OUT}/3-mapa-medellin-estrato.png',facecolor=PAPER,bbox_inches='tight',pad_inches=0.25)
    plt.close(); print('OK 3')

# ============================================================ 4) Barrios extremos (barras)
def img4():
    b=json.load(open(f'{D2V}/ciudades-barrios-2v.json'))['medellin']['b']
    rows=[(v['n'],v['cm'],v.get('c2',0),v.get('a2',0)) for v in b.values() if v.get('c2',0)+v.get('a2',0)>300]
    def pa(r): return r[3]/(r[2]+r[3])*100
    rows.sort(key=pa)
    top_c=rows[:5]        # más Cepeda
    top_a=rows[-5:][::-1] # más Abelardo
    fig,ax=plt.subplots(figsize=(10.8,11.4),dpi=100)
    fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER); ax.axis('off')
    ax.set_xlim(0,100); ax.set_ylim(0,100)
    ax.text(6,95,'SEGUNDA VUELTA · 2026 · MEDELLÍN',fontsize=13.5,color=OX,
            fontproperties=fm.FontProperties(fname=f'{FD}/Arima-SemiBold.ttf'))
    ax.text(6,90,'Del 94% al 30%: los extremos',fontsize=32,color=INK,va='top')

    def block(rows,y,title,col,pctf):
        ax.text(6,y,title,fontsize=15.5,color=col,va='top',
                fontproperties=fm.FontProperties(fname=f'{FD}/Arima-SemiBold.ttf'))
        yy=y-5
        for r in rows:
            p=pctf(r); w=70*p/100
            ax.add_patch(FancyBboxPatch((30,yy-2.6),w,3.4,boxstyle='round,pad=0.02,rounding_size=0.3',fc=col,ec='none'))
            ax.text(28.5,yy-0.9,r[0],fontsize=11.5,color=INK,ha='right',va='center')
            ax.text(30+w+1.2,yy-0.9,f'{p:.0f}%',fontsize=13,color=col,va='center',
                    fontproperties=fm.FontProperties(fname=f'{FD}/Arima-SemiBold.ttf'))
            ax.text(30.8,yy-0.9,r[1],fontsize=8.5,color='white',va='center',ha='left')
            yy-=5.2
        return yy
    yb=block(top_a,79,'Barrios más de Abelardo',ABE,pa)
    block(top_c,yb-3,'Barrios más de Cepeda',CEP,lambda r:100-pa(r))
    ax.text(6,5.5,'% de cada barrio para el candidato del bloque. Barrios con +300 votos.\nricardoruiz.co · preconteo 2V por mesa, cruce a barrio',
            fontsize=11,color=MUTE,va='center')
    fig.savefig(f'{OUT}/4-medellin-extremos.png',facecolor=PAPER,bbox_inches='tight',pad_inches=0.28)
    plt.close(); print('OK 4')

def _mix(c1,c2,t):
    import matplotlib.colors as mc
    a=np.array(mc.to_rgb(c1)); b=np.array(mc.to_rgb(c2))
    return mc.to_hex(a+(b-a)*t)

if __name__=='__main__':
    img1(); img2(); img3(); img4()
    print('\nHERO stats:')
    print(' NAC margen', sep(NAC_MARGEN))
    print(' ANT margen', sep(ANT_MARGEN), '=', round(ANT_MARGEN/NAC_MARGEN,1),'x nacional')
    print(' sin ANT Cepeda gana por', sep(SIN_ANT))
    print(' ANT muns Abelardo/Cepeda', ANT_AWIN, ANT_CWIN)
    print(' Medellín Abelardo pct', round(MED_ABE_PCT,1))
