#!/usr/bin/env python3
# Graficos nacionales para el documento 2V (Inter, paleta del proyecto).
#   g_trasvases · g_estrategias · g_participacion · g_margen_depto · g_balance
import json, collections
import numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
OUT='Bases de datos/output_2v'
import os; os.makedirs(f'{OUT}/graficos',exist_ok=True)
for f in ['Regular','Bold']:
    try: font_manager.fontManager.addfont(f'tools/pacto-1v-2026/fonts/Inter-{f}.ttf')
    except: pass
plt.rcParams['font.family']='Inter'
INK='#1a1510'; MUT='#6b6258'; BLUE='#1f47cc'; RED='#c0392b'; GREY='#c9c2b4'; PAPER='#f4f1ea'; OX='#8a1e16'
def fnum(n): return f'{int(round(n)):,}'.replace(',','.')
TR=json.load(open(f'{OUT}/trasvases.json')); AN=json.load(open(f'{OUT}/analisis_2v.json'))
M=json.load(open(f'{OUT}/master_unificado_puesto.json'))

# ── g_trasvases: reparto de cada bloque 1V -> Cepeda / Abelardo / resto ──
def g_trasvases():
    fig,ax=plt.subplots(figsize=(8.6,4.4),dpi=140); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    blocks=TR['blocks']; tot=TR['src_total']; a=TR['a_cep']; b=TR['b_abe']
    y=np.arange(len(blocks))[::-1]
    for i,(bl,t,ac,ab) in enumerate(zip(blocks,tot,a,b)):
        yy=y[i]; c=ac*t; ab_=ab*t; r=max(0,t-c-ab_)
        ax.barh(yy,c,color=RED,edgecolor='white'); ax.barh(yy,ab_,left=c,color=BLUE,edgecolor='white')
        ax.barh(yy,r,left=c+ab_,color=GREY,edgecolor='white')
        if ac>0.06: ax.text(c/2,yy,f'{100*ac:.0f}%',ha='center',va='center',color='white',fontsize=10,fontweight='bold')
        if ab>0.06: ax.text(c+ab_/2,yy,f'{100*ab:.0f}%',ha='center',va='center',color='white',fontsize=10,fontweight='bold')
        ax.text(t+30000,yy,fnum(t),va='center',fontsize=8.5,color=MUT)
    ax.set_yticks(y); ax.set_yticklabels(blocks,fontsize=10,color=INK)
    ax.set_xlim(0,max(tot)*1.16); ax.set_xticks([])
    for s in ax.spines.values(): s.set_visible(False)
    ax.text(0,1.15,'Destino de cada bloque de 1ª vuelta en 2ª vuelta',transform=ax.transAxes,fontsize=13,fontweight='bold',color=INK,va='bottom')
    ax.text(0,1.04,'rojo = a Cepeda · azul = a Abelardo · gris = a blanco/abstención',transform=ax.transAxes,fontsize=9,color=MUT,va='bottom')
    fig.savefig(f'{OUT}/graficos/g_trasvases.png',facecolor=PAPER,bbox_inches='tight'); plt.close(fig)

# ── g_estrategias: las 3 estrategias, target vs logrado ──
def g_estrategias():
    E=AN['estrategias']
    fig,ax=plt.subplots(figsize=(8.6,4.0),dpi=140); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    labels=['Centro\n(persuasión)','Recuperación\n(zonas duras)','Abstención\n(movilización)']
    target=[E['centro']['target'],E['recuperacion']['target'],E['abstencion']['target']]
    logr=[E['centro']['real_a_cepeda'],E['recuperacion']['logrado'],E['abstencion']['dcep_target']-E['abstencion']['dabe_target']]
    x=np.arange(3); w=0.38
    ax.bar(x-w/2,target,w,color=GREY,edgecolor='white',label='Objetivo del plan')
    ax.bar(x+w/2,logr,w,color=RED,edgecolor='white',label='Logrado (real)')
    for i in range(3):
        ax.text(x[i]-w/2,target[i],fnum(target[i]),ha='center',va='bottom',fontsize=8.5,color=MUT)
        ax.text(x[i]+w/2,logr[i],fnum(logr[i]),ha='center',va='bottom',fontsize=8.5,color=RED,fontweight='bold')
    ax.set_xticks(x); ax.set_xticklabels(labels,fontsize=10,color=INK); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)
    ax.legend(frameon=False,fontsize=9,loc='upper right')
    ax.set_title('Las 3 estrategias de Cepeda: objetivo vs. resultado real',fontsize=13,fontweight='bold',color=INK,loc='left')
    ax.set_ylim(0,max(target+logr)*1.18)
    fig.savefig(f'{OUT}/graficos/g_estrategias.png',facecolor=PAPER,bbox_inches='tight'); plt.close(fig)

# ── g_participacion: la marea por zona ──
def g_participacion():
    P=AN['participacion']; zi=P['zona_izq']; zd=P['zona_der']
    fig,ax=plt.subplots(figsize=(8.6,4.0),dpi=140); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    grp=['Zonas donde Cepeda\nganó la 1ª vuelta','Zonas donde Abelardo\nganó la 1ª vuelta']
    cep=[zi['dcep'],zd['dcep']]; abe=[zi['dabe'],zd['dabe']]
    x=np.arange(2); w=0.36
    ax.bar(x-w/2,cep,w,color=RED,edgecolor='white',label='Creció Cepeda')
    ax.bar(x+w/2,abe,w,color=BLUE,edgecolor='white',label='Creció Abelardo')
    for i in range(2):
        ax.text(x[i]-w/2,cep[i],'+'+fnum(cep[i]),ha='center',va='bottom',fontsize=9,color=RED,fontweight='bold')
        ax.text(x[i]+w/2,abe[i],'+'+fnum(abe[i]),ha='center',va='bottom',fontsize=9,color=BLUE,fontweight='bold')
    ax.set_xticks(x); ax.set_xticklabels(grp,fontsize=10,color=INK); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)
    ax.legend(frameon=False,fontsize=9.5,loc='upper right'); ax.set_ylim(0,max(cep+abe)*1.2)
    ax.set_title('La marea de participación reforzó al líder local de cada zona',fontsize=13,fontweight='bold',color=INK,loc='left')
    fig.savefig(f'{OUT}/graficos/g_participacion.png',facecolor=PAPER,bbox_inches='tight'); plt.close(fig)

# ── g_margen_depto: margen neto 2V por depto (diverging) ──
def g_margen_depto():
    DEPN={'01':'Antioquia','03':'Atlántico','05':'Bolívar','07':'Boyacá','09':'Caldas','11':'Cauca','12':'Cesar','13':'Córdoba','15':'Cundinamarca','16':'Bogotá','17':'Chocó','19':'Huila','21':'Magdalena','23':'Nariño','24':'Risaralda','25':'N. Santander','26':'Quindío','27':'Santander','28':'Sucre','29':'Tolima','31':'Valle','40':'Arauca','44':'Caquetá','46':'Casanare','48':'La Guajira','50':'Guainía','52':'Meta','54':'Guaviare','56':'San Andrés','60':'Amazonas','64':'Putumayo','68':'Vaupés','72':'Vichada'}
    d=collections.defaultdict(lambda:[0,0])
    for r in M:
        if r['cep2'] is None or r['cod5'][:2]=='88': continue
        dd=d[r['cod5'][:2]]; dd[0]+=r['cep2']; dd[1]+=r['abe2']
    rows=sorted(([DEPN.get(k,k),v[1]-v[0]] for k,v in d.items()),key=lambda r:r[1])
    fig,ax=plt.subplots(figsize=(7.6,8.6),dpi=140); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    names=[r[0] for r in rows]; vals=[r[1] for r in rows]; y=np.arange(len(rows))
    ax.barh(y,vals,color=[BLUE if v>0 else RED for v in vals],edgecolor='white')
    ax.set_yticks(y); ax.set_yticklabels(names,fontsize=8.5,color=INK)
    ax.axvline(0,color=INK,lw=0.8); ax.set_xticks([])
    for i,v in enumerate(vals):
        ax.text(v+(40000 if v>0 else -40000),i,('+' if v>0 else '')+fnum(v),va='center',ha='left' if v>0 else 'right',fontsize=7.5,color=MUT)
    for s in ax.spines.values(): s.set_visible(False)
    ax.set_xlim(min(vals)*1.35,max(vals)*1.35)
    ax.text(0,1.035,'Margen neto de 2ª vuelta por departamento',transform=ax.transAxes,fontsize=13,fontweight='bold',color=INK,va='bottom')
    ax.text(0,1.01,'azul = Abelardo · rojo = Cepeda · Antioquia define la elección',transform=ax.transAxes,fontsize=9,color=MUT,va='bottom')
    fig.savefig(f'{OUT}/graficos/g_margen_depto.png',facecolor=PAPER,bbox_inches='tight'); plt.close(fig)

# ── g_balance: por qué Abelardo gana pese al envión de Cepeda ──
def g_balance():
    fig,ax=plt.subplots(figsize=(8.6,3.4),dpi=140); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    # incremento de cada uno
    cep_inc=TR['real_inc_cep']; abe_inc=TR['real_inc_abe']
    steps=[('Ventaja Abelardo\n1ª vuelta',665915,BLUE),
           ('Cepeda crece más\nen 2ª vuelta',-(cep_inc-abe_inc),RED),
           ('Ventaja Abelardo\n2ª vuelta',250830,BLUE)]
    x=np.arange(3);
    vals=[665915,250830]
    ax.bar([0],[665915],0.5,color=BLUE,edgecolor='white')
    ax.bar([2],[250830],0.5,color=BLUE,edgecolor='white')
    ax.bar([1],[-(cep_inc-abe_inc)],0.5,bottom=665915,color=RED,edgecolor='white')
    ax.text(0,665915,'+'+fnum(665915),ha='center',va='bottom',fontsize=10,color=BLUE,fontweight='bold')
    ax.text(2,250830,'+'+fnum(250830),ha='center',va='bottom',fontsize=10,color=BLUE,fontweight='bold')
    ax.text(1,665915-(cep_inc-abe_inc)/2,'−'+fnum(cep_inc-abe_inc),ha='center',va='center',fontsize=10,color='white',fontweight='bold')
    ax.set_xticks(x); ax.set_xticklabels([s[0] for s in steps],fontsize=9.5,color=INK); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)
    ax.set_title('Cepeda creció más entre vueltas — pero no alcanzó la ventaja de Abelardo',fontsize=12.5,fontweight='bold',color=INK,loc='left')
    ax.set_ylim(0,720000)
    fig.savefig(f'{OUT}/graficos/g_balance.png',facecolor=PAPER,bbox_inches='tight'); plt.close(fig)

for fn in (g_trasvases,g_estrategias,g_participacion,g_margen_depto,g_balance):
    fn(); print('  ✓',fn.__name__)
print(f'-> {OUT}/graficos/ (5 gráficos)')
