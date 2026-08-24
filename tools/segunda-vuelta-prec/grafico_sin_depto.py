#!/usr/bin/env python3
# Recrea la gráfica estilo "DataWorld" (votación CON vs SIN un departamento)
# para la 2ª vuelta presidencial 2026, con datos reales del preconteo y marca propia.
#
#   python3 tools/segunda-vuelta-prec/grafico_sin_depto.py [COD_DEPTO]
#   (default 25 = Norte de Santander)
#
# Salida: rrss/sin-<depto>-2v.png  (1080x1080)

import json, subprocess, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Helvetica Neue','Helvetica','Arial','DejaVu Sans']

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
URL = 'https://registraduria-proxy.reruizc.workers.dev/presidente2v'

DANE = {'01':'Antioquia','25':'Norte de Santander','27':'Santander','05':'Bolívar',
        '16':'Bogotá','31':'Valle','11':'Cauca','23':'Nariño'}

# Colores (muestreados del original)
BG='#0a0a0a'; BLUE='#1c3fd6'; RED='#e81e26'; YELLOW='#ffd400'; WHITE='#ffffff'; GREY='#3a3a3a'

DEP = sys.argv[1] if len(sys.argv) > 1 else '25'
name = DANE.get(DEP, DEP)

def fetch():
    out = subprocess.run(['curl','-s','--max-time','30','-A',UA,
        '-H','Referer: https://resultados.registraduria.gov.co/', URL],
        capture_output=True, text=True, timeout=40)
    return json.loads(out.stdout)

gi = lambda o,k: int(str(o.get(k,'0')).replace('.','').replace(',','') or 0)
d = fetch()
deps={}
for e in d['camaras'][0]['mapagan']:
    amb=str(e.get('amb','')).zfill(2); win=str(e.get('codpar')); vot=gi(e,'vot'); votcan=gi(e,'votcan')
    deps[amb]={'cep': vot if win=='2' else votcan-vot, 'abe': vot if win=='3' else votcan-vot}
CEP=sum(v['cep'] for v in deps.values()); ABE=sum(v['abe'] for v in deps.values())
dd=deps[DEP]
sinA=ABE-dd['abe']; sinC=CEP-dd['cep']
# panel: (titulo2, abe, cep, ganador, margen)
panels = [
    ('SIN', sinA, sinC),
    ('CON', ABE, CEP),
]
print(f"{name}: SIN -> Abe {sinA:,} Cep {sinC:,} (gana {'Cepeda' if sinC>sinA else 'Abelardo'} +{abs(sinC-sinA):,})")
print(f"        CON -> Abe {ABE:,} Cep {CEP:,} (gana {'Abelardo' if ABE>CEP else 'Cepeda'} +{abs(ABE-CEP):,})")

# ---------- dibujo ----------
fig = plt.figure(figsize=(10.8,10.8), dpi=100)
fig.patch.set_facecolor(BG)
ax = fig.add_axes([0,0,1,1]); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off'); ax.set_facecolor(BG)

def rbox(x,y,w,h,fc,ec='none',lw=0,rad=0.02):
    ax.add_patch(FancyBboxPatch((x,y),w,h, boxstyle=f"round,pad=0,rounding_size={rad}",
                 mutation_aspect=1, fc=fc, ec=ec, lw=lw, zorder=2))

# Header: banda blanca + check azul
rbox(0.045,0.885,0.74,0.072, WHITE, rad=0.012)
ax.text(0.072,0.921,"COLOMBIA", color='#0a0a0a', fontsize=30, fontweight='heavy', va='center', ha='left')
# chevron »  dibujado a mano (sin glifos de fuente → cero cuadritos)
for i in range(2):
    x0=0.300+i*0.020
    ax.plot([x0, x0+0.014, x0],[0.921+0.018, 0.921, 0.921-0.018], color=BLUE, lw=7,
            solid_capstyle='round', solid_joinstyle='round', zorder=4)
ax.text(0.352,0.921,"PRESIDENCIALES 2026", color='#0a0a0a', fontsize=27, fontweight='heavy', va='center', ha='left')
rbox(0.80,0.885,0.155,0.072, '#2e6bff', rad=0.012)
# checkmark dibujado a mano (la fuente no trae el glifo ✓)
ax.plot([0.853,0.872,0.905],[0.919,0.902,0.938], color=WHITE, lw=8,
        solid_capstyle='round', solid_joinstyle='round', zorder=4)

# Subtítulo + badge marca
ax.text(0.05,0.84,f"ELECCIONES COLOMBIA 2026  ·  {name.upper()}", color=WHITE,
        fontsize=18, fontweight='bold', va='center', ha='left')
rbox(0.775,0.818,0.18,0.045, YELLOW, rad=0.01)
ax.text(0.865,0.8405,"RICARDORUIZ.CO", color='#0a0a0a', fontsize=12.5, fontweight='heavy', va='center', ha='center')

# Panel labels (cajas amarillas)
centers=[0.275,0.725]
ax.text(centers[0],0.70,"VOTACIÓN SIN", color=YELLOW, fontsize=20, fontweight='heavy', va='center', ha='center')
ax.text(centers[1],0.70,"VOTACIÓN CON", color=YELLOW, fontsize=20, fontweight='heavy', va='center', ha='center')
rbox(0.085,0.638,0.38,0.05, YELLOW, rad=0.012)
rbox(0.535,0.638,0.38,0.05, YELLOW, rad=0.012)
ax.text(centers[0],0.663, name.upper(), color='#0a0a0a', fontsize=19, fontweight='heavy', va='center', ha='center')
ax.text(centers[1],0.663, name.upper(), color='#0a0a0a', fontsize=19, fontweight='heavy', va='center', ha='center')

# Barras
base_y=0.215; max_h=0.355
vals=[sinA,sinC,ABE,CEP]
vmin=min(vals)-0.55e6; vmax=max(vals)+0.18e6
def bh(v): return (v-vmin)/(vmax-vmin)*max_h
bw=0.135
# (x, valor, color, nombre)
bars=[
    (0.175, sinA, BLUE, 'ABELARDO'), (0.375, sinC, RED, 'CEPEDA'),
    (0.625, ABE,  BLUE, 'ABELARDO'), (0.825, CEP,  RED, 'CEPEDA'),
]
for x,v,c,nm in bars:
    h=bh(v)
    ax.add_patch(Rectangle((x-bw/2,base_y), bw, h, fc=c, ec='none', zorder=3))
    ax.text(x, base_y+h+0.022, f"{v/1e6:.2f}M", color=WHITE, fontsize=23, fontweight='heavy', va='bottom', ha='center')
    ax.text(x, base_y-0.038, nm, color=WHITE, fontsize=16, fontweight='bold', va='center', ha='center')

# Divisor vertical
ax.add_patch(Rectangle((0.497,0.16),0.006,0.46, fc=GREY, ec='none', zorder=1))

# Caption ganador por panel
ax.text(centers[0],0.115, "GANA CEPEDA", color=RED, fontsize=20, fontweight='heavy', va='center', ha='center')
ax.text(centers[0],0.078, f"+{abs(sinC-sinA):,.0f} votos".replace(',','.'), color=WHITE, fontsize=14, fontweight='bold', va='center', ha='center')
ax.text(centers[1],0.115, "GANA ABELARDO", color=BLUE, fontsize=20, fontweight='heavy', va='center', ha='center')
ax.text(centers[1],0.078, f"+{abs(ABE-CEP):,.0f} votos".replace(',','.'), color=WHITE, fontsize=14, fontweight='bold', va='center', ha='center')

# Footer
ax.text(0.5,0.028, "Preconteo Registraduría · 2ª vuelta presidencial · 21 jun 2026 · cifras no oficiales",
        color='#8a8a8a', fontsize=11, va='center', ha='center')

out='rrss/sin-'+name.lower().replace(' ','-').replace('ó','o')+'-2v.png'
fig.savefig(out, facecolor=BG, dpi=100)
print('->', out)
