#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Carrusel Instagram (10 slides) — Atípica Tunja 26-jul-2026.
Identidad de redes v2: FONDO OSCURO + HELVETICA. **1080x1080 (IG cuadrado)**.
Portada = captura real del tablero. Handle @ricardoeruiz_.

  python3 tools/tunja-atipica/build_ig.py  → rrss/instagram/carrusel-tunja/01..10.png
"""
import os, json, unicodedata
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch
import matplotlib.image as mpimg
import geopandas as gpd

ROOT="/Users/ricardoruiz/ricardoruiz.co"
SRC =os.path.join(ROOT,"Bases de datos/output_tunja/tunja-electoral.json")
GEO =os.path.join(ROOT,"CIUDADES/TUNJA/TUNJAX.json")
CAP =os.path.join(ROOT,"rrss/twitter/tunja-png/0-portada-web.png")
OUT =os.path.join(ROOT,"rrss/instagram/carrusel-tunja")
HN  =os.path.join(ROOT,"tools/tunja-atipica/fonts-hn")
os.makedirs(OUT,exist_ok=True)
HANDLE="@ricardoeruiz_"

for f in ("HelveticaNeue-Regular.ttf","HelveticaNeue-Medium.ttf","HelveticaNeue-Bold.ttf"):
    fm.fontManager.addfont(os.path.join(HN,f))
R =fm.FontProperties(fname=os.path.join(HN,"HelveticaNeue-Regular.ttf"))
M =fm.FontProperties(fname=os.path.join(HN,"HelveticaNeue-Medium.ttf"))
B =fm.FontProperties(fname=os.path.join(HN,"HelveticaNeue-Bold.ttf"))
plt.rcParams['font.family']='Helvetica Neue'

BG="#0b0e18"; PANEL="#141a29"; TXT="#f4f3ef"; MUT="#8b93a7"; LINE="#26304a"
BLUE="#3d6fff"; BLUEK="#0047ff"; CEP="#e05545"; ABE="#1f47cc"
PARTY_COLORS=[("FUERZA DE LA PAZ","#1fae9b"),("PACTO HISTORICO","#7a68c9"),
  ("CENTRO DEMOCRAT","#2450a8"),("CONSERVADOR","#2e5fe0"),("CAMBIO RADICAL","#d84b6a"),
  ("ALIANZA VERDE","#3fae5a"),("PARTIDO VERDE","#3fae5a"),("LIBERAL","#e04545"),
  ("POLO DEMOCR","#e8c34a"),("DE LA U","#f28c28"),("AUTORIDADES INDIGENAS","#cd7f52")]
NEU=["#f0a04b","#b07fd8","#3fb5c9","#e8c34a","#cd7f52","#7ec95c"]
def _n(s): return ''.join(c for c in unicodedata.normalize('NFD',(s or '').upper()) if unicodedata.category(c)!='Mn')
def pcolor(par):
    p=_n(par); best=None; bi=1e9
    for kw,c in PARTY_COLORS:
        i=p.find(kw)
        if i>=0 and i<bi: best,bi=c,i
    return best
def apellido(nom):
    t=(nom or '').split(); take=t[-2:] if len(t)>=3 else t[-1:]
    return ' '.join(w.capitalize() for w in take)

D=json.load(open(SRC)); ALC=D['alcaldias']; PRES=D['presidencial_2026']; BP=D['barrio_puesto']

W=H=10.8   # 1080x1080 @ dpi100
def canvas():
    fig=plt.figure(figsize=(W,H),dpi=100); fig.patch.set_facecolor(BG)
    ax=fig.add_axes([0,0,1,1]); ax.set_facecolor(BG); ax.axis('off')
    ax.set_xlim(0,W); ax.set_ylim(0,H)
    ax.add_patch(plt.Circle((W*0.86,H*1.04),4.2,color="#12224f",alpha=0.5,zorder=0))
    ax.add_patch(plt.Circle((W*0.10,-.6),3.4,color="#101a3a",alpha=0.5,zorder=0))
    return fig,ax
def head(ax,kick,title,sub=None,ty=None,tsize=40):
    ax.text(0.7,H-0.75,kick,fontproperties=M,fontsize=14,color=BLUE)
    if ty is None: ty=H-1.45
    ax.text(0.7,ty,title,fontproperties=B,fontsize=tsize,color=TXT,va='top',linespacing=1.04)
    if sub:
        sy=ty-1.02*(title.count(chr(10))+1)-0.14
        ax.text(0.7,sy,sub,fontproperties=R,fontsize=19,color=MUT,va='top',linespacing=1.34)
    return ty
def foot(ax,right="ricardoruiz.co/tunja-atipica.html"):
    ax.text(0.7,0.48,HANDLE,fontproperties=M,fontsize=15,color=MUT)
    ax.text(W-0.7,0.48,right,fontproperties=M,fontsize=14,color=BLUE,ha='right')
def num(ax,i):
    ax.text(W-0.7,H-0.75,f"{i:02d}/10",fontproperties=M,fontsize=14,color=MUT,ha='right')
def save(fig,name): fig.savefig(os.path.join(OUT,name),facecolor=BG); plt.close(fig); print("✓",name)

# ============ 01 · portada (captura, recortada a hero+mapa)
def s01():
    fig,ax=canvas()
    ax.text(0.7,H-0.75,"ELECCIÓN ATÍPICA · TUNJA · BOYACÁ",fontproperties=M,fontsize=14,color=BLUE)
    ax.text(0.7,H-1.35,"Tunja elige alcalde\nel 26 de julio",fontproperties=B,fontsize=40,color=TXT,va='top',linespacing=1.04)
    ax.text(0.7,H-3.35,"Antes de la primera encuesta, mira cómo ha votado la ciudad\n—barrio por barrio— en un tablero interactivo.",
            fontproperties=R,fontsize=15.5,color=MUT,va='top',linespacing=1.3)
    img=mpimg.imread(CAP); ih,iw=img.shape[:2]
    img=img[:int(0.62*ih)]              # recorta el panel inferior → tira hero+mapa
    ih2=img.shape[0]; ar=iw/ih2
    fw=9.6; fh=fw/ar; fx=(W-fw)/2; fy=1.15
    ax.imshow(img,extent=[fx,fx+fw,fy,fy+fh],zorder=3,aspect='auto')
    ax.add_patch(FancyBboxPatch((fx,fy),fw,fh,boxstyle="round,pad=0.0,rounding_size=0.02",
                 fill=False,ec=LINE,lw=1.5,zorder=4))
    ax.text(W/2,0.6,"Desliza para ver el análisis   ·   ricardoruiz.co/tunja-atipica.html",
            fontproperties=M,fontsize=13.5,color=TXT,ha='center')
    save(fig,"01-portada.png")

# ============ 02 · alternancia
def s02():
    yrs=[('2011','alcaldia_2011'),('2015','alcaldia_2015'),('2019','alcaldia_2019'),('2023','alcaldia_2023')]
    rows=[]
    for y,e in yrs:
        E=ALC[e]; w=sorted(E['nacional'],key=lambda x:-x['votos'])[0]; tot=E['total_validos']
        par=w['par']
        flag=('Partido Verde' if 'VERDE' in par and 'ALIANZA' not in par else
              'Cambio Radical' if 'CAMBIO RADICAL' in par else
              'Conservador' if 'CONSERVADOR' in par else
              'Fuerza de la Paz' if 'FUERZA DE LA PAZ' in par else par.title())
        rows.append((y,apellido(w['des']),flag,100*w['votos']/tot,pcolor(par) or NEU[0]))
    fig,ax=canvas(); num(ax,2)
    head(ax,"EL HISTÓRICO · 2011–2023","Tunja no tiene dueño",
         "Cuatro alcaldías seguidas, cuatro banderas distintas.\nNinguna fuerza repite.")
    y0=6.3; h=1.12; gap=0.24
    for i,(yr,ape,flag,pct,col) in enumerate(rows):
        yy=y0-i*(h+gap)
        ax.add_patch(FancyBboxPatch((0.7,yy),W-1.4,h,boxstyle="round,pad=0.02,rounding_size=0.08",fc=PANEL,ec=LINE,lw=1))
        ax.add_patch(plt.Rectangle((0.7,yy),0.13,h,fc=col,ec='none'))
        ax.text(1.15,yy+h/2,yr,fontproperties=B,fontsize=27,color=TXT,va='center')
        ax.text(3.0,yy+h*0.63,ape,fontproperties=M,fontsize=19,color=TXT,va='center')
        ax.text(3.0,yy+h*0.27,flag,fontproperties=R,fontsize=14.5,color=MUT,va='center')
        bx=W-3.5; bw=2.1
        ax.add_patch(plt.Rectangle((bx,yy+h*0.38),bw,0.28,fc="#26304a",ec='none'))
        ax.add_patch(plt.Rectangle((bx,yy+h*0.38),bw*pct/100,0.28,fc=col,ec='none'))
        ax.text(W-0.72,yy+h/2,f"{pct:.1f}%",fontproperties=B,fontsize=18,color=TXT,va='center',ha='right')
    foot(ax); save(fig,"02-alternancia.png")

# ============ mapa dark
def map_slide(name,idx,kick,title,sub,winner_color_fn,legend):
    gdf=gpd.read_file(GEO); cols=[]
    for i in range(len(gdf)):
        bp=BP.get(str(i)); c="none"
        if bp: c=winner_color_fn(bp['pcode']) or "none"
        cols.append(c)
    gdf=gdf.copy(); gdf['col']=cols
    fig,ax0=canvas(); num(ax0,idx)
    head(ax0,kick,title,sub,tsize=34)
    nsub=sub.count(chr(10))+1
    top_frac={1:0.585,2:0.545,3:0.495}.get(nsub,0.49); bottom=0.135
    axm=fig.add_axes([0.02,bottom,0.96,top_frac-bottom]); axm.set_facecolor(BG); axm.axis('off')
    hid=gdf[gdf['col']=="none"]; sh=gdf[gdf['col']!="none"]
    if len(hid): hid.plot(ax=axm,color="#1a2233",ec="#2a3550",lw=0.15)
    sh.plot(ax=axm,color=sh['col'],ec=BG,lw=0.35)
    lx=0.7
    for lab,c in legend:
        ax0.add_patch(plt.Rectangle((lx,1.02),0.26,0.26,fc=c,ec='none'))
        ax0.text(lx+0.38,1.07,lab,fontproperties=R,fontsize=15,color=TXT)
        lx+=4.7
    foot(ax0); save(fig,name)

def s03():
    byp=ALC['alcaldia_2023']['by_puesto']
    fn=lambda pc:(pcolor(byp[pc]['winner_par']) or NEU[0]) if pc in byp else None
    map_slide("03-mapa-2023.png",3,"ALCALDÍA 2023 · BARRIO POR BARRIO",
              "Krasnov ganó 23 de 26\npuestos… con 33,7%",
              "La ciudad se vio de un color, pero el alcalde llegó\ncon apenas un tercio de los votos. La disputa real\nfue entre años, no dentro de 2023.",
              fn,[("Krasnov · Fuerza de la Paz","#1fae9b"),("Carrero · Coalición",NEU[0])])

def s04():
    E=ALC['alcaldia_2023']; tot=E['total_validos']
    top=sorted(E['nacional'],key=lambda x:-x['votos'])[:6]
    rows=[]; used=set(); ni=0
    for n in top:
        c=pcolor(n['par'])
        if not c:
            while NEU[ni%len(NEU)] in used: ni+=1
            c=NEU[ni%len(NEU)]; used.add(c); ni+=1
        else: used.add(c)
        rows.append((apellido(n['des']),100*n['votos']/tot,c))
    fig,ax=canvas(); num(ax,4)
    head(ax,"CÓMO SE GANA UNA ATÍPICA","No con simpatía: movilizando",
         "En 2023 seis candidatos se repartieron el voto.",tsize=34)
    x0=3.3; bw=6.7; y=6.15; bh=0.42; gap=0.30; mx=max(p for _,p,_ in rows)
    for i,(ape,pct,c) in enumerate(rows):
        yy=y-i*(bh+gap)
        ax.text(x0-0.22,yy+bh/2,ape,fontproperties=R,fontsize=15.5,color=TXT,va='center',ha='right')
        ax.add_patch(plt.Rectangle((x0,yy),bw,bh,fc="#26304a",ec='none'))
        ax.add_patch(plt.Rectangle((x0,yy),bw*pct/mx,bh,fc=c,ec='none'))
        ax.text(x0+bw*pct/mx+0.13,yy+bh/2,f"{pct:.1f}%",fontproperties=M,fontsize=14.5,color=TXT,va='center')
    facts=[("34%","ganó el alcalde"),("34%","no votó"),("10","puestos = ⅔ del censo")]
    fw=3.0
    for i,(big,small) in enumerate(facts):
        xx=0.7+i*(fw+0.15)
        ax.add_patch(FancyBboxPatch((xx,1.1),fw,1.35,boxstyle="round,pad=0.02,rounding_size=0.08",fc=PANEL,ec=LINE,lw=1))
        ax.add_patch(plt.Rectangle((xx,1.1),0.1,1.35,fc=BLUE,ec='none'))
        ax.text(xx+0.32,2.02,big,fontproperties=B,fontsize=26,color=TXT)
        ax.text(xx+0.32,1.36,small,fontproperties=R,fontsize=13.5,color=MUT)
    foot(ax); save(fig,"04-fragmentacion.png")

# ============ 05 · presidencial 2026
def s05():
    c1=a1=c2=a2=u2=pot=0
    for pc,p in PRES.items():
        c1+=p['cep1'];a1+=p['abe1'];c2+=p['cep2'];a2+=p['abe2'];u2+=p['urna2'];pot+=p['pot']
    fig,ax=canvas(); num(ax,5)
    head(ax,"LA SEÑAL MÁS RECIENTE · PRESIDENCIAL 2026","Tunja se inclinó a la izquierda",
         "En la última elección nacional, el Pacto ganó la ciudad\nen las dos vueltas.",tsize=34)
    rows=[("Cepeda",100*c2/(c2+a2),CEP),("De la Espriella",100*a2/(c2+a2),ABE)]
    y=5.7; bh=0.85; gap=0.55; x0=0.7; bw=W-1.4
    for i,(nm,pct,c) in enumerate(rows):
        yy=y-i*(bh+gap)
        ax.text(x0,yy+bh+0.12,nm,fontproperties=M,fontsize=18.5,color=TXT)
        ax.add_patch(plt.Rectangle((x0,yy),bw,bh,fc="#26304a",ec='none'))
        ax.add_patch(plt.Rectangle((x0,yy),bw*pct/100,bh,fc=c,ec='none'))
        ax.text(x0+0.25,yy+bh/2,f"{pct:.1f}%",fontproperties=B,fontsize=27,color="#ffffff",va='center')
    ax.text(0.7,2.05,f"1ª vuelta: Cepeda {100*c1/(c1+a1):.1f}%    ·    participación 2V {100*u2/pot:.1f}%",
            fontproperties=R,fontsize=16.5,color=MUT)
    ax.text(0.7,1.4,"El techo de la izquierda es alto. La pregunta de la atípica es si\nese voto se traduce en un solo candidato local.",
            fontproperties=R,fontsize=16,color=MUT,linespacing=1.32)
    foot(ax); save(fig,"05-presidencial.png")

def s06():
    fn=lambda pc:(CEP if PRES[pc]['cep2']>=PRES[pc]['abe2'] else ABE) if pc in PRES else None
    map_slide("06-mapa-presi.png",6,"PRESIDENCIAL 2026 · 2ª VUELTA POR BARRIO",
              "Cepeda ganó 21 de\nlos 26 puestos",
              "Misma ciudad, huella distinta: en lo nacional,\nTunja es claramente de izquierda.",
              fn,[("Cepeda","#e05545"),("De la Espriella",ABE)])

# ============ 07 · izquierda dividida
def s07():
    fig,ax=canvas(); num(ax,7)
    head(ax,"EL PUENTE ENTRE LO NACIONAL Y LO LOCAL","La izquierda tiene los votos… repartidos",
         "En la atípica, ese electorado va en cuatro tarjetones distintos.",tsize=32)
    blocs=[("Pacto Histórico","Nicolás Cortés","#7a68c9"),
           ("Alianza por Tunja · Verde","Yamir López","#3fae5a"),
           ("Esperanza Democrática","José R. López","#3fb5c9"),
           ("Ecologista","Jonathan Bosigas","#7ec95c")]
    y0=6.0; h=0.95; gap=0.22
    for i,(par,nm,c) in enumerate(blocs):
        yy=y0-i*(h+gap)
        ax.add_patch(FancyBboxPatch((0.7,yy),W-1.4,h,boxstyle="round,pad=0.02,rounding_size=0.08",fc=PANEL,ec=LINE,lw=1))
        ax.add_patch(plt.Rectangle((0.7,yy),0.13,h,fc=c,ec='none'))
        ax.text(1.1,yy+h*0.62,nm,fontproperties=M,fontsize=18.5,color=TXT,va='center')
        ax.text(1.1,yy+h*0.26,par,fontproperties=R,fontsize=14,color=MUT,va='center')
    ax.text(0.7,1.1,"Sumados valen más que cualquiera por separado. Divididos, le abren\nla puerta al bloque tradicional y a los independientes.",
            fontproperties=R,fontsize=15.5,color=MUT,linespacing=1.3)
    foot(ax); save(fig,"07-izquierda-dividida.png")

# ============ 08 · nombres
def s08():
    fig,ax=canvas(); num(ax,8)
    head(ax,"SIN ENCUESTAS AÚN · SEGÚN ANALISTAS LOCALES","Cuatro nombres a seguir",
         "El Diario Boyacá y Orfetv coinciden: 3-4 con opciones reales.",tsize=34)
    cands=[("Rafael Acevedo","ASI · exsecretario de Infraestructura","#2e5fe0"),
           ("Yamir López","Alianza por Tunja · el voto verde","#3fae5a"),
           ("Nicolás Cortés","Pacto Histórico","#7a68c9"),
           ("Sandra Estupiñán","Cambio Radical – Conservador","#d84b6a")]
    y0=6.15; h=1.12; gap=0.24
    for i,(nm,par,c) in enumerate(cands):
        yy=y0-i*(h+gap)
        ax.add_patch(FancyBboxPatch((0.7,yy),W-1.4,h,boxstyle="round,pad=0.02,rounding_size=0.08",fc=PANEL,ec=LINE,lw=1))
        ax.add_patch(plt.Circle((1.4,yy+h/2),0.3,fc=c,ec='none'))
        ax.text(2.15,yy+h*0.62,nm,fontproperties=B,fontsize=20,color=TXT,va='center')
        ax.text(2.15,yy+h*0.27,par,fontproperties=R,fontsize=14.5,color=MUT,va='center')
    foot(ax); save(fig,"08-candidatos.png")

# ============ 09 · lectura
def s09():
    fig,ax=canvas(); num(ax,9)
    head(ax,"LA LECTURA DE FONDO","Gana quien sume y movilice",None,tsize=34)
    pts=["La izquierda tiene el techo más alto, pero llega dividida en cuatro tarjetones.",
         "El bloque tradicional —que gobernó en 2015 y 2019— va más consolidado tras Estupiñán.",
         "1 de cada 3 tunjanos no votó: el voto dormido, no la persuasión, decide la atípica.",
         "10 puestos concentran ⅔ del censo. Ganar Tunja es ganar un puñado de colegios."]
    y=6.7
    for t in pts:
        ax.add_patch(plt.Circle((1.0,y+0.02),0.11,fc=BLUE,ec='none'))
        ax.text(1.4,y,t,fontproperties=R,fontsize=18.5,color=TXT,va='center',wrap=True,linespacing=1.3)
        y-=1.45
    foot(ax); save(fig,"09-lectura.png")

# ============ 10 · cierre
def s10():
    fig,ax=canvas()
    ax.text(0.7,H-0.9,"EXPLÓRALO TÚ MISMO",fontproperties=M,fontsize=14,color=BLUE)
    ax.text(0.7,H-1.7,"El mapa completo,\nbarrio por barrio",fontproperties=B,fontsize=40,color=TXT,va='top',linespacing=1.04)
    ax.text(0.7,H-4.15,"Las 4 alcaldías (2011–2023) y la presidencial 2026, gratis.\nHistórico completo, capa de puestos y base descargable\nen los planes.",
            fontproperties=R,fontsize=18,color=MUT,va='top',linespacing=1.35)
    ax.add_patch(FancyBboxPatch((0.7,3.9),W-1.4,1.35,boxstyle="round,pad=0.02,rounding_size=0.1",fc=BLUEK,ec='none'))
    ax.text(W/2,4.57,"ricardoruiz.co/tunja-atipica.html",fontproperties=B,fontsize=21,color="#ffffff",ha='center',va='center')
    ax.text(W/2,3.05,"#Tunja   #Boyacá   #Atípicas2026",fontproperties=M,fontsize=15,color=MUT,ha='center')
    ax.text(W/2,1.15,HANDLE,fontproperties=M,fontsize=17,color=TXT,ha='center')
    save(fig,"10-cierre.png")

if __name__=="__main__":
    s01();s02();s03();s04();s05();s06();s07();s08();s09();s10()
    print("Listo →",OUT)
