#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Imágenes para el hilo de Twitter de la atípica de Tunja (26-jul-2026).
Identidad de redes del proyecto: Arima (títulos) + paper #f1eee4, colores por
partido iguales a los del tablero tunja-atipica.html. SIN watermark (público).

Genera en rrss/twitter/tunja-png/:
  1-alternancia.png   Tunja no tiene dueño: 4 alcaldías, 4 banderas (2011-2023)
  2-mapa-2023.png     Mapa por barrio · ganador alcaldía 2023 (choropleth)
  3-fragmentacion.png Cómo se gana: fragmentación 2023 + abstención + concentración

  python3 tools/tunja-atipica/build_imgs.py
"""
import os, re, json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch
import geopandas as gpd

ROOT = "/Users/ricardoruiz/ricardoruiz.co"
SRC  = os.path.join(ROOT, "Bases de datos/output_tunja/tunja-electoral.json")
GEO  = os.path.join(ROOT, "CIUDADES/TUNJA/TUNJAX.json")
OUT  = os.path.join(ROOT, "rrss/twitter/tunja-png")
FONTS= os.path.join(ROOT, "tools/edad-1v-2026/fonts")
os.makedirs(OUT, exist_ok=True)

# ---- fuentes ----
for f in ("Arima-Bold.ttf","Arima-SemiBold.ttf"):
    fm.fontManager.addfont(os.path.join(FONTS, f))
ARIMA = fm.FontProperties(fname=os.path.join(FONTS,"Arima-Bold.ttf"))
ARIMA_SB = fm.FontProperties(fname=os.path.join(FONTS,"Arima-SemiBold.ttf"))
plt.rcParams['font.family']='DejaVu Sans'   # cuerpo (soporta tildes)

# ---- paleta ----
PAPER="#f1eee4"; INK="#1a1510"; OX="#8a1e16"; AMBER="#cf7d2a"; MUT="#6b6357"; LINE="#d9d3c6"

# colores por partido (idénticos al tablero)
PARTY_COLORS = [
  ("FUERZA DE LA PAZ","#1fae9b"),("PACTO HISTORICO","#7a68c9"),
  ("CENTRO DEMOCRAT","#2450a8"),("CONSERVADOR","#2e5fe0"),
  ("CAMBIO RADICAL","#d84b6a"),("ALIANZA VERDE","#3fae5a"),
  ("PARTIDO VERDE","#3fae5a"),("LIBERAL","#e04545"),
  ("POLO DEMOCR","#e8c34a"),("DE LA U","#f28c28"),
  ("AUTORIDADES INDIGENAS","#cd7f52"),
]
NEUTRAL = ["#f0a04b","#b07fd8","#3fb5c9","#e8c34a","#9aa7b8","#cd7f52"]
def _norm(s):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD',(s or '').upper()) if unicodedata.category(c)!='Mn')
def party_color(par):
    p=_norm(par); best=None; bi=1e9
    for kw,col in PARTY_COLORS:
        i=p.find(kw)
        if i>=0 and i<bi: best,bi=col,i
    return best

DATA = json.load(open(SRC))
ALC = DATA['alcaldias']

def apellido(nombre):
    # convención COL: [nombre(s)] [apellido paterno] [materno].
    # 3+ tokens → los 2 apellidos; 2 tokens → el único apellido.
    t=(nombre or '').split()
    take = t[-2:] if len(t)>=3 else t[-1:]
    return ' '.join(w.capitalize() for w in take)

# ============================================================ IMG 1 · alternancia
def img_alternancia():
    yrs=[('2011','alcaldia_2011'),('2015','alcaldia_2015'),
         ('2019','alcaldia_2019'),('2023','alcaldia_2023')]
    rows=[]
    for y,e in yrs:
        E=ALC[e]; nac=sorted(E['nacional'],key=lambda x:-x['votos']); w=nac[0]
        tot=E['total_validos']
        col=party_color(w['par']) or NEUTRAL[0]
        # nombre de bandera corto
        par=w['par']
        flag = ('Partido Verde' if 'VERDE' in par and 'ALIANZA' not in par else
                'Cambio Radical' if 'CAMBIO RADICAL' in par else
                'Conservador' if 'CONSERVADOR' in par else
                'La Fuerza de la Paz' if 'FUERZA DE LA PAZ' in par else par.title())
        rows.append((y, apellido(w['des']), flag, 100*w['votos']/tot, col))

    fig,ax=plt.subplots(figsize=(12,9),dpi=100); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    ax.axis('off'); ax.set_xlim(0,12); ax.set_ylim(0,9)
    ax.text(0.6,8.35,"ELECCIÓN ATÍPICA · TUNJA · 26 DE JULIO 2026",fontproperties=ARIMA_SB,
            fontsize=14,color=OX)
    ax.text(0.6,7.5,"Tunja no tiene dueño",fontproperties=ARIMA,fontsize=44,color=INK)
    ax.text(0.6,6.75,"Cuatro alcaldías seguidas, cuatro banderas distintas. Ninguna fuerza\nrepite. Antes de leer encuestas, así se ha movido la ciudad.",
            fontsize=15,color=MUT,linespacing=1.4)

    # cuatro tarjetas horizontales tipo timeline
    x0,x1=0.6,11.4; y=5.4; h=1.05; gap=0.22
    for i,(yr,ape,flag,pct,col) in enumerate(rows):
        yy=y - i*(h+gap)
        card=FancyBboxPatch((x0,yy),x1-x0,h,boxstyle="round,pad=0.02,rounding_size=0.06",
                            fc="#faf8f2",ec=LINE,lw=1.2,mutation_aspect=1)
        ax.add_patch(card)
        ax.add_patch(plt.Rectangle((x0,yy),0.12,h,fc=col,ec='none'))
        ax.text(x0+0.4,yy+h/2,yr,fontproperties=ARIMA,fontsize=30,color=INK,va='center')
        ax.text(x0+2.3,yy+h*0.62,ape,fontproperties=ARIMA_SB,fontsize=19,color=INK,va='center')
        ax.text(x0+2.3,yy+h*0.26,flag,fontsize=13.5,color=MUT,va='center')
        # barra de % a la derecha
        bx=x0+7.7; bw=2.7
        ax.add_patch(plt.Rectangle((bx,yy+h*0.32),bw,0.34,fc="#e7e1d4",ec='none'))
        ax.add_patch(plt.Rectangle((bx,yy+h*0.32),bw*pct/100,0.34,fc=col,ec='none'))
        ax.text(x1-0.15,yy+h/2,f"{pct:.1f}%",fontproperties=ARIMA,fontsize=21,color=INK,va='center',ha='right')

    ax.text(0.6,0.35,"Ganador de cada alcaldía y su porcentaje en la ciudad · Fuente: Registraduría (GCS)   ·   ricardoruiz.co",
            fontsize=11.5,color=MUT)
    fig.savefig(os.path.join(OUT,"1-alternancia.png"),facecolor=PAPER,bbox_inches='tight',pad_inches=0.3)
    plt.close(fig); print("✓ 1-alternancia.png")

# ============================================================ IMG 2 · mapa 2023
def img_mapa():
    gdf=gpd.read_file(GEO)
    BP=DATA['barrio_puesto']; byp=ALC['alcaldia_2023']['by_puesto']
    # feature idx -> color por partido del ganador 2023 del puesto que lo cubre
    cols=[]; winners={}   # winner_can -> (apellido, par, color)
    for i in range(len(gdf)):
        bp=BP.get(str(i)); c=None
        if bp:
            b=byp.get(bp['pcode'])
            if b:
                c=party_color(b['winner_par']) or NEUTRAL[0]
                winners[b['winner_can']]=(apellido(b['winner']), b['winner_par'], c)
        cols.append(c if c else "none")
    gdf=gdf.copy(); gdf['col']=cols

    fig,ax=plt.subplots(figsize=(12,10.6),dpi=100); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    shown=gdf[gdf['col']!="none"]
    hidden=gdf[gdf['col']=="none"]
    if len(hidden): hidden.plot(ax=ax,color="#e7e1d4",ec="#cfc9bd",lw=0.2)
    shown.plot(ax=ax,color=shown['col'],ec=PAPER,lw=0.35)
    ax.axis('off')
    # titular arriba (fuera del marco del mapa)
    ax.set_title("")
    fig.subplots_adjust(top=0.8)
    n_kras=sum(1 for x in cols if x=="#1fae9b")
    fig.text(0.06,0.955,"ELECCIÓN ATÍPICA · TUNJA · 26 DE JULIO 2026",fontproperties=ARIMA_SB,fontsize=14,color=OX)
    fig.text(0.06,0.90,"Tunja, barrio por barrio · Alcaldía 2023",fontproperties=ARIMA,fontsize=34,color=INK)
    fig.text(0.06,0.855,"Krasnov ganó 23 de los 26 puestos; Carrero solo resistió en 3 del sur.\nEn el barrio, la ciudad se vio de un color — la disputa fue entre años, no dentro de 2023.",
             fontsize=13.5,color=MUT,linespacing=1.4)
    # leyenda (solo candidatos que ganaron ≥1 puesto)
    PARLABEL={'PARTIDO POLÍTICO LA FUERZA DE LA PAZ':'Fuerza de la Paz',
              'COALICIÓN JOHN CARRERO ALCALDE':'Coalición'}
    leg=[(f"{ap} · {PARLABEL.get(par,par.title())}",c)
         for ap,par,c in sorted(winners.values(), key=lambda w:-cols.count(w[2]))]
    lx=0.07
    for lab,c in leg:
        yb=0.045
        fig.patches.append(plt.Rectangle((lx,yb),0.022,0.022,transform=fig.transFigure,fc=c,ec='none'))
        fig.text(lx+0.03,yb+0.004,lab,fontsize=12,color=INK)
        lx+=0.32
    fig.text(0.93,0.02,"ricardoruiz.co",fontsize=11.5,color=MUT,ha='right')
    fig.savefig(os.path.join(OUT,"2-mapa-2023.png"),facecolor=PAPER,bbox_inches='tight',pad_inches=0.25)
    plt.close(fig); print("✓ 2-mapa-2023.png")

# ============================================================ IMG 3 · fragmentación
def img_fragmentacion():
    E=ALC['alcaldia_2023']; tot=E['total_validos']
    top=sorted(E['nacional'],key=lambda x:-x['votos'])[:6]
    rows=[(apellido(n['des']), 100*n['votos']/tot, party_color(n['par'])) for n in top]
    # asignar neutral a los sin color de partido, sin repetir
    used=set(c for _,_,c in rows if c); ni=0
    fixed=[]
    for ape,pct,c in rows:
        if not c:
            while NEUTRAL[ni%len(NEUTRAL)] in used: ni+=1
            c=NEUTRAL[ni%len(NEUTRAL)]; used.add(c); ni+=1
        fixed.append((ape,pct,c))

    fig,ax=plt.subplots(figsize=(12,9),dpi=100); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    ax.axis('off'); ax.set_xlim(0,12); ax.set_ylim(0,9)
    ax.text(0.6,8.35,"ELECCIÓN ATÍPICA · TUNJA · 26 DE JULIO 2026",fontproperties=ARIMA_SB,fontsize=14,color=OX)
    ax.text(0.6,7.55,"En una atípica gana quien moviliza",fontproperties=ARIMA,fontsize=38,color=INK)
    ax.text(0.6,6.95,"El voto de Tunja está fragmentado: en 2023 el alcalde ganó con apenas un tercio.",
            fontsize=14.5,color=MUT)

    # barras horizontales top 6 (2023)
    x0=3.2; bw=7.4; y=6.1; bh=0.5; gap=0.34
    mx=max(p for _,p,_ in fixed)
    for i,(ape,pct,c) in enumerate(fixed):
        yy=y-i*(bh+gap)
        ax.text(x0-0.2,yy+bh/2,ape,fontsize=15,color=INK,va='center',ha='right')
        ax.add_patch(plt.Rectangle((x0,yy),bw,bh,fc="#e7e1d4",ec='none'))
        ax.add_patch(plt.Rectangle((x0,yy),bw*pct/mx,bh,fc=c,ec='none'))
        ax.text(x0+bw*pct/mx+0.12,yy+bh/2,f"{pct:.1f}%",fontproperties=ARIMA_SB,fontsize=14,color=INK,va='center')

    # tres cifras clave abajo
    facts=[("34%","ganó el alcalde de 2023"),
           ("34%","de los tunjanos no votó"),
           ("10 puestos","concentran ⅔ del censo")]
    fx=0.6; fw=3.6
    for i,(big,small) in enumerate(facts):
        xx=fx+i*(fw+0.15)
        ax.add_patch(FancyBboxPatch((xx,0.35),fw,1.35,boxstyle="round,pad=0.02,rounding_size=0.06",
                                    fc="#faf8f2",ec=LINE,lw=1.1))
        ax.add_patch(plt.Rectangle((xx,0.35),0.1,1.35,fc=OX,ec='none'))
        ax.text(xx+0.35,1.28,big,fontproperties=ARIMA,fontsize=27,color=INK)
        ax.text(xx+0.35,0.68,small,fontsize=12.5,color=MUT)
    fig.text(0.93,0.012,"Fuente: Registraduría (GCS) · Divipole   ·   ricardoruiz.co",fontsize=11,color=MUT,ha='right')
    fig.savefig(os.path.join(OUT,"3-fragmentacion.png"),facecolor=PAPER,bbox_inches='tight',pad_inches=0.3)
    plt.close(fig); print("✓ 3-fragmentacion.png")

if __name__=="__main__":
    img_alternancia()
    img_mapa()
    img_fragmentacion()
    print("Listo →", OUT)
