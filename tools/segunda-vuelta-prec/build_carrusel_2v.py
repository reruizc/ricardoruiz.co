#!/usr/bin/env python3
# Carrusel 10 láminas (1080x1080) · ¿Por qué ganó Abelardo, y por qué por 1 punto?
# Identidad: paper #f1eee4, títulos Arima 700, kicker oxblood, Cepeda rojo / Abelardo azul.
# -> rrss/instagram/carrusel-2v/NN_*.png
import os
import numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle
from PIL import Image, ImageOps, ImageDraw

OUT='rrss/instagram/carrusel-2v'; os.makedirs(OUT,exist_ok=True)
PAPER='#f1eee4'; INK='#1a1510'; OX='#8a1e16'; MUT='#6b6258'; RED='#c0392b'; BLUE='#1f47cc'; GREY='#cfc7b6'
AR =fm.FontProperties(fname='tools/edad-1v-2026/fonts/Arima-Bold.ttf')
ARS=fm.FontProperties(fname='tools/edad-1v-2026/fonts/Arima-SemiBold.ttf')
IN =fm.FontProperties(fname='tools/pacto-1v-2026/fonts/Inter-Regular.ttf')
INB=fm.FontProperties(fname='tools/pacto-1v-2026/fonts/Inter-Bold.ttf')
LOGO='Bases de datos/output_abelardo_cartagena/logo_ricardoruiz.png'

def base(n):
    fig=plt.figure(figsize=(10.8,10.8),dpi=100); fig.patch.set_facecolor(PAPER)
    ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off'); ax.set_facecolor(PAPER)
    ax.text(0.93,0.058,f'{n} / 10',transform=ax.transAxes,fontsize=15,color=MUT,fontproperties=IN,ha='right',va='center')
    if n!=1 and n!=10:  # logo chiquito al pie en interiores
        _logo(fig,0.072,0.045,0.20)
    return fig,ax
def _logo(fig,x,y,w):
    lg=Image.open(LOGO).convert('RGBA'); r=lg.height/lg.width
    axl=fig.add_axes([x,y,w,w*r*10.8/10.8]); axl.imshow(lg); axl.axis('off')
def kicker(ax,t): ax.text(0.072,0.93,t,transform=ax.transAxes,fontsize=18,color=OX,fontproperties=INB,va='center')
def title(ax,t,y=0.80,fs=52,color=INK,lh=1.06):
    ax.text(0.072,y,t,transform=ax.transAxes,fontsize=fs,color=color,fontproperties=AR,va='top',linespacing=lh)
def support(ax,t,y=0.20,fs=25,color=MUT):
    ax.text(0.072,y,t,transform=ax.transAxes,fontsize=fs,color=color,fontproperties=IN,va='top',linespacing=1.32)
def hero(ax,t,y=0.50,fs=150,color=OX):
    ax.text(0.072,y,t,transform=ax.transAxes,fontsize=fs,color=color,fontproperties=AR,va='center')
def rule(ax,y=0.885,c=OX):
    ax.add_line(plt.Line2D([0.072,0.928],[y,y],color=c,lw=2.2,transform=ax.transAxes))

def duo_circle(path,dark,size=560,ybias=0.12):
    im=Image.open(path).convert('L'); im=ImageOps.autocontrast(im,cutoff=1)
    im=ImageOps.colorize(im,black=dark,white='#efe9db').convert('RGBA')
    w,h=im.size; s=min(w,h); x0=(w-s)//2; y0=int((h-s)*ybias)
    im=im.crop((x0,y0,x0+s,y0+s)).resize((size,size)).convert('RGBA')
    m=Image.new('L',(size,size),0); ImageDraw.Draw(m).ellipse((0,0,size-1,size-1),fill=255); im.putalpha(m)
    return im

# ═════════ 1 · PORTADA ═════════
def s1():
    fig,ax=base(1); kicker(ax,'ELECCIONES COLOMBIA 2026 · SEGUNDA VUELTA')
    cep=duo_circle('_candidatos/cepeda.jpg',  '#7a1812',ybias=0.06)
    abe=duo_circle('_candidatos/abelardo-hd.jpg','#14246e',ybias=0.0)
    for img,x,col,nm,pt in [(cep,0.115,RED,'Iván Cepeda','Pacto Histórico'),
                            (abe,0.555,BLUE,'Abelardo D.','Independiente')]:
        axp=fig.add_axes([x,0.575,0.33,0.33]); axp.imshow(img); axp.axis('off')
        axp.add_patch(Circle((0.5,0.5),0.495,transform=axp.transAxes,fill=False,ec=col,lw=6))
        ax.text(x+0.165,0.55,nm,transform=ax.transAxes,fontsize=22,color=INK,fontproperties=INB,ha='center',va='top')
        ax.text(x+0.165,0.515,pt,transform=ax.transAxes,fontsize=15,color=MUT,fontproperties=IN,ha='center',va='top')
    ax.text(0.5,0.66,'VS',transform=ax.transAxes,fontsize=30,color=MUT,fontproperties=AR,ha='center',va='center')
    title(ax,'¿Por qué ganó\nAbelardo? ¿Y por qué\npor solo 1 punto?',y=0.45,fs=60,lh=1.05)
    support(ax,'Crucé el preconteo de la Registraduría mesa a mesa,\nde la primera a la segunda vuelta.',y=0.155,fs=24)
    _logo(fig,0.072,0.052,0.21)
    fig.savefig(f'{OUT}/01_portada.png',facecolor=PAPER); plt.close(fig)

# ═════════ 2 · EL RESULTADO ═════════
def s2():
    fig,ax=base(2); kicker(ax,'EL RESULTADO'); rule(ax)
    hero(ax,'0,98',y=0.70,fs=215,color=INK); ax.text(0.715,0.70,'puntos',transform=ax.transAxes,fontsize=44,color=OX,fontproperties=AR,va='center')
    # barras
    axb=fig.add_axes([0.072,0.30,0.856,0.22]); axb.set_xlim(0,13.0); axb.set_ylim(-0.6,1.6); axb.axis('off')
    for i,(nm,v,c) in enumerate([('ABELARDO',12.959542,BLUE),('CEPEDA',12.708712,RED)]):
        y=1 if i==0 else 0
        axb.add_patch(Rectangle((0,y-0.34),v,0.68,color=c))
        axb.text(0.22,y,nm,fontsize=22,color='white',fontproperties=INB,va='center')
        axb.text(v-0.22,y,f'{v*1e6:,.0f}'.replace(',','.'),fontsize=23,color='white',fontproperties=INB,va='center',ha='right')
    support(ax,'Una diferencia de 250.830 votos: el margen más estrecho\nde una elección presidencial en décadas.',y=0.225,fs=25)
    fig.savefig(f'{OUT}/02_resultado.png',facecolor=PAPER); plt.close(fig)

# ═════════ 3 · TRAS LA 1V (participación récord) ═════════
def s3():
    fig,ax=base(3); kicker(ax,'TRAS LA PRIMERA VUELTA'); rule(ax)
    title(ax,'La participación creció\ncomo nunca antes',y=0.83,fs=51)
    yrs=['2010','2014','2018','2022','2026']; val=[44.5,48.0,53.0,58.2,63.6]
    axb=fig.add_axes([0.10,0.215,0.82,0.38]); axb.set_xlim(-0.6,4.6); axb.set_ylim(0,72); axb.axis('off')
    for i,(yr,v) in enumerate(zip(yrs,val)):
        c=OX if yr=='2026' else GREY
        axb.add_patch(Rectangle((i-0.34,0),0.68,v,color=c))
        axb.text(i,v+2,f'{v:.1f}%'.replace('.',','),fontsize=20,color=OX if yr=='2026' else MUT,fontproperties=INB,ha='center')
        axb.text(i,-4.5,yr,fontsize=18,color=INK if yr=='2026' else MUT,fontproperties=INB if yr=='2026' else IN,ha='center',va='top')
    support(ax,'Récord histórico en una 2ª vuelta: 63,6% nacional. Lideraron\nCundinamarca (73,5%), Cauca (73,3%) y Casanare (72%).',y=0.135,fs=22)
    fig.savefig(f'{OUT}/03_participacion.png',facecolor=PAPER); plt.close(fig)

# ═════════ helper de lámina "estrategia / dato" ═════════
def big_slide(n,fname,kick,ttl,heroline,heroclr,sup,ttly=0.80,herox=0.072,heroy=0.50,herofs=150,subhero=None):
    fig,ax=base(n); kicker(ax,kick); rule(ax)
    if ttl: title(ax,ttl,y=ttly,fs=49)
    ax.text(herox,heroy,heroline,transform=ax.transAxes,fontsize=herofs,color=heroclr,fontproperties=AR,va='center')
    if subhero: ax.text(herox,heroy-0.105,subhero,transform=ax.transAxes,fontsize=27,color=INK,fontproperties=INB,va='center')
    support(ax,sup,y=0.205,fs=25)
    fig.savefig(f'{OUT}/{fname}.png',facecolor=PAPER); plt.close(fig)

def s4(): big_slide(4,'04_centro','LO QUE LE FUNCIONÓ · 1 DE 3','Persuadió al centro\nde Fajardo y Claudia',
    '81%',RED,'Su voto se fue 81% a Cepeda, muy por encima del\n55–65% que proyectaban los modelos.',
    ttly=0.83, heroy=0.48, herofs=180, subhero='del centro se fue a Cepeda')

# 5 · condensa Recuperación + Abstención
def s5():
    fig,ax=base(5); kicker(ax,'LO QUE LE FUNCIONÓ · 2 Y 3 DE 3'); rule(ax)
    title(ax,'Recuperó su techo y\nmovilizó la abstención',y=0.83,fs=51)
    for yv,num,t1,t2 in [(0.55,'100%','del techo de Petro-2022','recuperado'),
                         (0.37,'+2,3M','votantes nuevos','movilizados')]:
        ax.text(0.072,yv,num,transform=ax.transAxes,fontsize=84,color=RED,fontproperties=AR,va='center')
        ax.text(0.47,yv+0.030,t1,transform=ax.transAxes,fontsize=25,color=INK,fontproperties=INB,va='center')
        ax.text(0.47,yv-0.018,t2,transform=ax.transAxes,fontsize=25,color=INK,fontproperties=INB,va='center')
    support(ax,'Trajo de vuelta a la izquierda demovilizada y sacó a votar\nla abstención en sus zonas fuertes.',y=0.205,fs=24)
    fig.savefig(f'{OUT}/05_estrategias.png',facecolor=PAPER); plt.close(fig)

# 6 · ¿cómo perdió? (creció 3M)
def s6():
    fig,ax=base(6); kicker(ax,'ENTONCES, ¿CÓMO PERDIÓ?'); rule(ax)
    title(ax,'Cepeda creció 3\nmillones de votos.\nMás que Abelardo.',y=0.80,fs=62)
    support(ax,'Hizo la tarea y aun así no le alcanzó. La respuesta no\nestá en la campaña: está en los números.',y=0.34,fs=26,color=INK)
    fig.savefig(f'{OUT}/06_sorpresa.png',facecolor=PAPER); plt.close(fig)

# 7 · ¿a quién ayudó la participación? (abstencionistas, estimación por zona)
def s7():
    from matplotlib.colors import to_rgba
    fig,ax=base(7); kicker(ax,'¿A QUIÉN AYUDÓ LA PARTICIPACIÓN?'); rule(ax)
    title(ax,'La marea alimentó\na los dos',y=0.82,fs=53)
    axb=fig.add_axes([0.072,0.34,0.83,0.27]); axb.set_xlim(0,3.25); axb.set_ylim(-0.5,1.8); axb.axis('off')
    for i,(nm,c,tras,abst) in enumerate([('ABELARDO',BLUE,1.607,0.902),('CEPEDA',RED,1.518,1.427)]):
        y=1 if i==0 else 0
        axb.add_patch(Rectangle((0,y-0.30),tras,0.60,color=c))
        axb.add_patch(Rectangle((tras,y-0.30),abst,0.60,facecolor=to_rgba(c,0.22),hatch='////',edgecolor=c,lw=1.0))
        axb.text(0.04,y+0.47,nm,fontsize=18,color=INK,fontproperties=INB,va='center')
        axb.text(tras/2,y,'trasvases',fontsize=15,color='white',fontproperties=INB,va='center',ha='center')
        axb.text(tras+abst/2,y,f'+{abst:.1f}M'.replace('.',','),fontsize=18,color=c,fontproperties=INB,va='center',ha='center')
    support(ax,'Crecimiento de cada uno entre vueltas. De los votantes nuevos,\n~1,4M se inclinaron por Cepeda y ~0,9M por Abelardo (rayado): la\nmarea subió pareja en el país y no rompió el empate.',y=0.255,fs=22)
    fig.savefig(f'{OUT}/07_abstencionistas.png',facecolor=PAPER); plt.close(fig)

def s8(): big_slide(8,'08_antioquia','LA CLAVE','Antioquia, sola,\ndecidió la elección',
    '+1.052.153',BLUE,'El doble de lo que Cepeda sacó en su mejor departamento\n(Valle: +525.000). Sin Antioquia, Cepeda sería presidente.',
    ttly=0.82, heroy=0.485, herofs=90, subhero='= cuatro veces el margen nacional')

# 9 · trasvases (dónde aportó Paloma)
def s9():
    fig,ax=base(9); kicker(ax,'POR QUÉ NO ALCANZÓ'); rule(ax)
    title(ax,'La derecha partía\nmás grande desde el inicio',y=0.83,fs=48)
    ax.text(0.072,0.595,'81%',transform=ax.transAxes,fontsize=104,color=BLUE,fontproperties=AR,va='center')
    ax.text(0.43,0.617,'del voto de Paloma',transform=ax.transAxes,fontsize=25,color=INK,fontproperties=INB,va='center')
    ax.text(0.43,0.573,'se fue a Abelardo',transform=ax.transAxes,fontsize=25,color=INK,fontproperties=INB,va='center')
    ax.text(0.072,0.45,'Donde más le aportó: Bogotá,',transform=ax.transAxes,fontsize=24,color=INK,fontproperties=IN,va='center')
    ax.text(0.072,0.408,'Antioquia y Cundinamarca.',transform=ax.transAxes,fontsize=24,color=INK,fontproperties=IN,va='center')
    ax.text(0.072,0.335,'Y él ya iba +666.000 votos arriba desde la 1ª vuelta.',transform=ax.transAxes,fontsize=23,color=INK,fontproperties=INB,va='center')
    support(ax,'Ganar los trasvases no basta cuando arrancas tan abajo.',y=0.205,fs=25)
    fig.savefig(f'{OUT}/09_trasvases.png',facecolor=PAPER); plt.close(fig)

# 10 · veredicto + barrios más votados
def s10():
    fig,ax=base(10); kicker(ax,'EL VEREDICTO'); rule(ax)
    title(ax,'La geografía pesó\nmás que la campaña.',y=0.87,fs=52)
    ax.text(0.072,0.585,'Los barrios más votados (Bogotá · Medellín · Cali)',transform=ax.transAxes,fontsize=17.5,color=OX,fontproperties=INB,va='center')
    cols=[(0.072,BLUE,'ABELARDO',[('Colina Campestre','Bogotá'),('Salitre','Bogotá'),('Laureles','Medellín')]),
          (0.53,RED,'CEPEDA',[('Bosa Centro','Bogotá'),('Cdad. Kennedy','Bogotá'),('El Recreo','Bogotá')])]
    for x,c,nm,lst in cols:
        ax.text(x,0.52,nm,transform=ax.transAxes,fontsize=20,color=c,fontproperties=INB,va='center')
        for j,(b,ci) in enumerate(lst):
            yy=0.455-j*0.058
            ax.text(x,yy,f'{j+1}.  {b}',transform=ax.transAxes,fontsize=20,color=INK,fontproperties=IN,va='center')
            ax.text(x+0.018,yy-0.026,ci,transform=ax.transAxes,fontsize=13,color=MUT,fontproperties=IN,va='center')
    support(ax,'La segunda vuelta, casi siempre, se gana en la primera.',y=0.205,fs=24,color=INK)
    _logo(fig,0.072,0.065,0.24)
    fig.savefig(f'{OUT}/10_veredicto.png',facecolor=PAPER); plt.close(fig)

for fn in [s1,s2,s3,s4,s5,s6,s7,s8,s9,s10]: fn(); print('  ✓',fn.__name__)
print('->',OUT,'· 10 láminas 1080x1080')
