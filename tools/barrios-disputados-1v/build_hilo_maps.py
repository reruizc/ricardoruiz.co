#!/usr/bin/env python3
"""Mapas para el hilo de Twitter de barrios veleta (proyección 2ª vuelta).

Lee los GeoJSON por ciudad (output_barrios_veleta/{slug}.json, ya con c/a/b/C/A/f)
y pinta imágenes apaisadas 1600x900 con la identidad de los carruseles:
Arima bold, papel #f1eee4, tinta #1a1510, kicker oxblood #8a1e16.
Color de dato: dorado = veleta · rojo = Cepeda · azul = Abelardo.

Salida: rrss/twitter/barrios-veleta-png/bv-*.png
"""
import os, json
import geopandas as gpd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams, font_manager
from matplotlib.patches import Patch

ROOT = '/Users/ricardoruiz/ricardoruiz.co'
DATA = f'{ROOT}/Bases de datos/output_barrios_veleta'
FONTS = f'{ROOT}/tools/edad-1v-2026/fonts'
OUT = f'{ROOT}/rrss/twitter/barrios-veleta-png'
os.makedirs(OUT, exist_ok=True)

for f in ('Arima-SemiBold.ttf', 'Arima-Bold.ttf'):
    p = os.path.join(FONTS, f)
    if os.path.exists(p): font_manager.fontManager.addfont(p)
rcParams['font.family'] = ['Helvetica Neue', 'Helvetica', 'Arial', 'DejaVu Sans']
TITLE = {'family': 'Arima', 'weight': 'bold'}

BG='#f1eee4'; FG='#1a1510'; INK2='#5a5448'; INK3='#9a9180'; OX='#8a1e16'
CEP=['#f2a59d','#e2685c','#cf4135','#9c1e15']
ABE=['#9db4f5','#5b82ef','#3a5bd0','#1f2a8c']
GOLD='#f4c430'; GREY='#d8d3c6'
BLANK2V=0.024; THR=3.0

def load(slug):
    g = gpd.read_file(f'{DATA}/{slug}.json').set_crs('EPSG:4326', allow_override=True)
    if slug == 'bogota':   # rotación 90° CCW (norte a la izquierda), convención del sitio
        g['geometry'] = g.geometry.rotate(90, origin=(-74.08, 4.65))
    return g

def margin(r, view):
    if view == '1v':
        return (r['c']-r['a'])/r['b']*100 if r['b'] else 0
    t = r['C']+r['A']; return (r['C']-r['A'])/t*100*(1-BLANK2V) if t else 0

GREYX = '#8d8676'   # parque / no residencial (f=2)
def color(r, view):
    if r['f'] == 2: return GREYX
    m = margin(r, view); am = abs(m)
    if am <= THR: return GOLD            # veleta (directo o heredado)
    ramp = CEP if m >= 0 else ABE
    return ramp[0 if am<7 else 1 if am<15 else 2 if am<30 else 3]

def counts(g, view):   # cuenta barrios por representante (f=0, r=1) — sin duplicar nombres
    vel=cep=abe=0
    for _,row in g.iterrows():
        if row['f']!=0 or int(row.get('r',1))!=1 or row['b']<=0: continue
        m=margin(row,view)
        if abs(m)<=THR: vel+=1
        elif m>0: cep+=1
        else: abe+=1
    return vel, cep, abe

def paint(ax, g, view):
    g = g.copy(); g['col'] = g.apply(lambda r: color(r, view), axis=1)
    park = g[g['f']==2]; nonpark = g[g['f']!=2]
    if len(park): park.plot(ax=ax, color=GREYX, edgecolor='white', linewidth=.2, alpha=.45)
    nonpark.plot(ax=ax, color=nonpark['col'], edgecolor='white', linewidth=.25)  # directo y heredado, color pleno
    fb = g[g['f']==0]
    if not len(fb): fb = nonpark
    minx,miny,maxx,maxy = fb.total_bounds; px=(maxx-minx)*.04; py=(maxy-miny)*.04
    ax.set_xlim(minx-px,maxx+px); ax.set_ylim(miny-py,maxy+py)
    ax.set_aspect('equal'); ax.set_axis_off()

def legend(ax):
    h=[Patch(fc=GOLD,ec='white',label='Veleta (±3 pp)'),
       Patch(fc='#cf4135',ec='white',label='Gana Cepeda'),
       Patch(fc='#3a5bd0',ec='white',label='Gana Abelardo')]
    ax.legend(handles=h, loc='lower left', frameon=False, fontsize=10.5,
              bbox_to_anchor=(0.0,-0.02), labelcolor=FG, handlelength=1.1)

def frame(fig, kicker, title, sub=None):
    fig.patch.set_facecolor(BG)
    fig.text(0.045, 0.945, kicker.upper(), fontsize=15, color=OX, fontweight='bold', va='top')
    fig.text(0.045, 0.905, title, fontsize=30, color=FG, va='top', **TITLE)
    if sub: fig.text(0.045, 0.838, sub, fontsize=13.5, color=INK2, va='top')
    fig.text(0.955, 0.045, 'ricardoruiz.co', fontsize=12, color=INK3, ha='right')

def save(fig, name):
    fig.savefig(f'{OUT}/{name}', dpi=160, facecolor=BG, bbox_inches='tight', pad_inches=0.18)
    plt.close(fig); print('✓', name)

# 01 · Bogotá 2V (hook)
def img_bogota_2v():
    g = load('bogota'); v,c,a = counts(g,'2v')
    fig = plt.figure(figsize=(10,5.625)); fig.subplots_adjust(left=.02,right=.98,top=.80,bottom=.06)
    ax = fig.add_axes([0.30,0.04,0.68,0.74]); paint(ax,g,'2v')
    frame(fig,'Barrios veleta · proyección 2ª vuelta','Bogotá, barrio por barrio',
          'Dónde se pelea voto a voto Cepeda vs Abelardo si el país transfiere como\nlas encuestas (Paloma → Abelardo, Fajardo → Cepeda…). Norte a la izquierda.')
    fig.text(0.045,0.62,f'{v}',fontsize=64,color=GOLD,**TITLE)
    fig.text(0.045,0.50,'barrios veleta',fontsize=15,color=FG)
    fig.text(0.045,0.455,'a ±3 puntos en 2ª vuelta',fontsize=12,color=INK2)
    fig.text(0.045,0.36,f'Cepeda gana {c}  ·  Abelardo gana {a}',fontsize=12.5,color=INK2)
    axl=fig.add_axes([0.045,0.10,0.22,0.14]); axl.set_axis_off(); legend(axl)
    save(fig,'bv-01-bogota-2v.png')

# 02 · Bogotá 1V vs 2V (el efecto del trasvase)
def img_bogota_1v_2v():
    g = load('bogota')
    v1,c1,a1 = counts(g,'1v'); v2,c2,a2 = counts(g,'2v')
    fig = plt.figure(figsize=(10,5.625))
    for i,(view,lab,cc,aa,vv) in enumerate([('1v','1ª vuelta (real)',c1,a1,v1),('2v','2ª vuelta (proyección)',c2,a2,v2)]):
        ax = fig.add_axes([0.04+ i*0.49, 0.07, 0.45, 0.66]); paint(ax,g,view)
        ax.text(0.5,1.04,lab,transform=ax.transAxes,ha='center',fontsize=15,color=FG,**TITLE)
        ax.text(0.5,-0.02,f'Cepeda {cc} · Abelardo {aa} · veleta {vv}',transform=ax.transAxes,
                ha='center',fontsize=10.5,color=INK2)
    frame(fig,'El trasvase mueve el mapa','Bogotá: de la 1ª vuelta a la 2ª',
          f'Cepeda ganó {c1} barrios en 1ª vuelta; al sumar el voto de Paloma a Abelardo,\nla proyección de 2ª vuelta lo deja en {c2} y Abelardo sube a {a2}.')
    save(fig,'bv-02-bogota-1v-2v.png')

# 03 · ciudades 2V (small multiples)
def img_ciudades():
    cities = [('bogota','Bogotá'),('medellin','Medellín'),('cali','Cali'),
              ('barranquilla','Barranquilla'),('cartagena','Cartagena'),('pereira','Pereira')]
    fig = plt.figure(figsize=(10,5.625))
    for i,(slug,name) in enumerate(cities):
        r,col = divmod(i,3)
        ax = fig.add_axes([0.035+col*0.325, 0.42-r*0.385, 0.30, 0.30])
        g = load(slug); paint(ax,g,'2v'); v,c,a = counts(g,'2v')
        ax.text(0.5,1.02,name,transform=ax.transAxes,ha='center',fontsize=12,color=FG,**TITLE)
        ax.text(0.5,-0.07,f'{v} veleta · C {c} · A {a}',transform=ax.transAxes,ha='center',fontsize=8.5,color=INK2)
    frame(fig,'Proyección 2ª vuelta · barrio por barrio','Seis ciudades, seis pulsos',
          'Bogotá es el campo de batalla; Medellín, un muro azul; Cali aguanta rojo. '+
          'Dorado = veleta (±3 pp).')
    save(fig,'bv-03-ciudades-2v.png')

# 04 · cierre (tarjeta)
def img_cierre():
    fig = plt.figure(figsize=(10,5.625)); fig.patch.set_facecolor(BG)
    fig.text(0.06,0.86,'BARRIOS VELETA · 2ª VUELTA 2026',fontsize=15,color=OX,fontweight='bold',va='top')
    fig.text(0.06,0.78,'El mapa interactivo,\n11 ciudades, barrio por barrio.',fontsize=34,color=FG,va='top',**TITLE)
    for i,t in enumerate([
        'Toggle 1ª vuelta real ↔ proyección de 2ª vuelta.',
        'Trasvase del simulador de ponderador-2v (matriz AtlasIntel) + blanco 2,4%.',
        'Umbral ajustable; cada barrio con su detalle al pasar el cursor.',
        'Cartografía oficial · incluye Popayán y Manizales.']):
        fig.text(0.07,0.46-i*0.075,'•  '+t,fontsize=14.5,color=INK2,va='top')
    fig.text(0.06,0.085,'ricardoruiz.co/barrios-veleta-1v.html',fontsize=16,color=OX,fontweight='bold')
    # franja de muestra de color (sin solaparse con los bullets)
    for i,(cl,lb) in enumerate([(GOLD,'veleta'),('#cf4135','Cepeda'),('#3a5bd0','Abelardo')]):
        fig.patches.append(plt.Rectangle((0.70,0.79-i*0.055),0.022,0.035,transform=fig.transFigure,fc=cl,ec='white',lw=.5,clip_on=False))
        fig.text(0.73,0.807-i*0.055,lb,fontsize=12.5,color=INK2,va='center')
    save(fig,'bv-04-cierre.png')

# ════════ INSTAGRAM · 8 piezas cuadradas 1080×1080 ════════
IGOUT = f'{ROOT}/rrss/instagram/barrios-veleta-png'

def frame_sq(fig, kicker, title, sub=None):
    fig.patch.set_facecolor(BG)
    fig.text(0.065, 0.955, kicker.upper(), fontsize=15, color=OX, fontweight='bold', va='top')
    fig.text(0.065, 0.912, title, fontsize=33, color=FG, va='top', **TITLE)
    if sub: fig.text(0.065, 0.840, sub, fontsize=13.5, color=INK2, va='top')
    fig.text(0.935, 0.022, 'ricardoruiz.co', fontsize=12.5, color=INK3, ha='right')

def igsave(fig, name):
    fig.savefig(f'{IGOUT}/{name}', dpi=160, facecolor=BG)
    plt.close(fig); print('✓ ig', name)

def sq_fig():
    fig = plt.figure(figsize=(6.75,6.75)); fig.patch.set_facecolor(BG); return fig

def sq_legend(fig, x=0.065, y=0.085):
    for i,(cl,lb) in enumerate([(GOLD,'veleta (±3 pp)'),('#cf4135','gana Cepeda'),('#3a5bd0','gana Abelardo')]):
        fig.patches.append(plt.Rectangle((x,y-i*0.045),0.028,0.030,transform=fig.transFigure,fc=cl,ec='white',lw=.5,clip_on=False))
        fig.text(x+0.04,y+0.015-i*0.045,lb,fontsize=12.5,color=INK2,va='center')

def ig_map(name_out, slug, kicker, title, sub):
    g = load(slug)
    fig = sq_fig(); ax = fig.add_axes([0.05,0.085,0.90,0.66]); paint(ax,g,'2v')
    frame_sq(fig,kicker,title,sub); sq_legend(fig)
    igsave(fig,name_out)

def ig_portada():
    g = load('bogota')
    fig = sq_fig(); ax = fig.add_axes([0.03,0.035,0.94,0.45]); paint(ax,g,'2v')
    fig.text(0.065,0.955,'ELECCIONES 2026 · 2ª VUELTA',fontsize=15,color=OX,fontweight='bold',va='top')
    fig.text(0.065,0.905,'Los barrios\nveleta',fontsize=52,color=FG,va='top',linespacing=0.95,**TITLE)
    fig.text(0.065,0.66,'Dónde se pelea voto a voto Cepeda vs Abelardo,\nbarrio por barrio · proyección de 2ª vuelta · 11 ciudades',
             fontsize=13.5,color=INK2,va='top')
    fig.text(0.935,0.022,'ricardoruiz.co',fontsize=12.5,color=INK3,ha='right')
    igsave(fig,'ig-01-portada.png')

def ig_bogota_shift():
    g = load('bogota'); v1,c1,a1 = counts(g,'1v'); v2,c2,a2 = counts(g,'2v')
    fig = sq_fig()
    for i,(view,lab,cc,aa,vv) in enumerate([('1v','1ª vuelta (real)',c1,a1,v1),('2v','2ª vuelta (proyección)',c2,a2,v2)]):
        ax = fig.add_axes([0.04+i*0.49, 0.30, 0.45, 0.42]); paint(ax,g,view)
        ax.text(0.5,1.03,lab,transform=ax.transAxes,ha='center',fontsize=14.5,color=FG,**TITLE)
        ax.text(0.5,-0.05,f'Cepeda {cc} · Abelardo {aa} · veleta {vv}',transform=ax.transAxes,ha='center',fontsize=10,color=INK2)
    frame_sq(fig,'El trasvase mueve el mapa','Bogotá: de la 1ª a la 2ª',
             f'Cepeda ganó {c1} barrios en 1ª vuelta. Tras el trasvase,\nla 2ª vuelta proyectada los deja en {c2} vs {a2} barrios.')
    sq_legend(fig, y=0.20); igsave(fig,'ig-03-bogota-shift.png')

def ig_trasvase():
    fig = sq_fig()
    frame_sq(fig,'Cómo se proyecta','El trasvase de votos',
             'A cada barrio se le aplica el reparto que miden las\nencuestas (matriz AtlasIntel · simulador ponderador-2v):')
    rows = [('#3a5bd0','Paloma','~85% a Abelardo'),
            ('#cf4135','Fajardo','~58% a Cepeda'),
            ('#cf4135','Claudia','~55% a Cepeda'),
            ('#9a9180','Menores + Botero','se dividen casi por mitad'),
            ('#9a9180','Blanco / nulo 1V','la mayoría se queda en blanco'),
            ('#9a9180','Abstención','una parte se moviliza, se inclina a Abelardo')]
    for i,(cl,k,v) in enumerate(rows):
        y = 0.70 - i*0.095
        fig.patches.append(plt.Rectangle((0.075,y-0.006),0.030,0.046,transform=fig.transFigure,fc=cl,ec='white',lw=.5,clip_on=False))
        fig.text(0.13,y+0.038,k,fontsize=17,color=FG,va='top',**TITLE)
        fig.text(0.13,y+0.002,v,fontsize=13,color=INK2,va='top')
    fig.text(0.065,0.085,'Cada finalista guarda su fidelidad; se deja un voto en blanco del 2,4%.\nEs un ejercicio de escenarios, no un pronóstico.',fontsize=12.5,color=INK3,va='top')
    fig.text(0.935,0.022,'ricardoruiz.co',fontsize=12.5,color=INK3,ha='right')
    igsave(fig,'ig-04-trasvase.png')

def ig_cuatro():
    cities=[('barranquilla','Barranquilla'),('cartagena','Cartagena'),('pereira','Pereira'),('manizales','Manizales')]
    fig = sq_fig()
    for i,(slug,name) in enumerate(cities):
        r,col = divmod(i,2)
        ax = fig.add_axes([0.06+col*0.47, 0.42-r*0.34, 0.42, 0.30])
        g = load(slug); paint(ax,g,'2v'); v,c,a = counts(g,'2v')
        ax.text(0.5,1.03,name,transform=ax.transAxes,ha='center',fontsize=14,color=FG,**TITLE)
        ax.text(0.5,-0.06,f'{v} veleta · C {c} · A {a}',transform=ax.transAxes,ha='center',fontsize=9.5,color=INK2)
    frame_sq(fig,'Proyección 2ª vuelta','Cuatro ciudades más',
             'Cartagena y Barranquilla aguantan rojas; en Pereira y Manizales los\npocos focos de Cepeda se encogen al sumarle Paloma a Abelardo.')
    igsave(fig,'ig-07-cuatro.png')

def ig_cierre():
    fig = sq_fig()
    frame_sq(fig,'Barrios veleta · 2ª vuelta 2026','El mapa interactivo')
    for i,t in enumerate(['Alterna entre 1ª vuelta real y proyección de 2ª vuelta.',
                          'Mueve el umbral y mira cada barrio al pasar el cursor.',
                          'Trasvase del simulador de ponderador-2v + blanco 2,4%.',
                          'Cartografía oficial · 11 ciudades, con Popayán y Manizales.']):
        fig.text(0.075,0.74-i*0.085,'•  '+t,fontsize=15,color=INK2,va='top')
    fig.text(0.065,0.30,'ricardoruiz.co/\nbarrios-veleta-1v.html',fontsize=24,color=OX,va='top',**TITLE)
    sq_legend(fig, y=0.13); igsave(fig,'ig-08-cierre.png')

def build_ig():
    os.makedirs(IGOUT, exist_ok=True)
    vb,_,_ = counts(load('bogota'),'2v')
    _,cm,am2 = counts(load('medellin'),'2v')
    _,cc,ac = counts(load('cali'),'2v')
    ig_portada()
    ig_map('ig-02-bogota.png','bogota','Proyección 2ª vuelta','Bogotá',
           f'El campo de batalla: {vb} barrios veleta sobre la frontera norte–sur.')
    ig_bogota_shift()
    ig_trasvase()
    ig_map('ig-05-medellin.png','medellin','Proyección 2ª vuelta','Medellín',
           f'Un muro azul: Abelardo gana {am2} barrios; Cepeda, {cm}.')
    ig_map('ig-06-cali.png','cali','Proyección 2ª vuelta','Cali',
           f'Aguanta rojo: Cepeda gana {cc} barrios; Abelardo, {ac}.')
    ig_cuatro()
    ig_cierre()

if __name__ == '__main__':
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if mode in ('all','tw','counts'):
        print('— conteos (método del sitio, con blanco 2,4% en 2V) —')
        for slug,name in [('bogota','Bogotá'),('medellin','Medellín'),('cali','Cali'),
                          ('barranquilla','Barranquilla'),('cartagena','Cartagena'),('cucuta','Cúcuta'),
                          ('bucaramanga','Bucaramanga'),('pereira','Pereira'),('manizales','Manizales'),
                          ('popayan','Popayán'),('soledad','Soledad')]:
            g = load(slug); v1,c1,a1 = counts(g,'1v'); v2,c2,a2 = counts(g,'2v')
            print(f'{name:<13} 1V vel{v1:>3} C{c1:>3} A{a1:>3}  |  2V vel{v2:>3} C{c2:>3} A{a2:>3}')
        print()
    if mode in ('all','tw'):
        img_bogota_2v(); img_bogota_1v_2v(); img_ciudades(); img_cierre()
    if mode in ('all','ig'):
        build_ig()
