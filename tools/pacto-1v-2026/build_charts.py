#!/usr/bin/env python3
# Regenera los gráficos g_*.png del informe en tipografía Inter (coherencia con el
# Word y los mapas). NO aplica a imágenes de redes/Instagram (esas conservan
# Helvetica + su formato propio — ver CLAUDE.md).
import json
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import matplotlib.patheffects as pe

FDIR='tools/pacto-1v-2026/fonts'
for _f in ('Inter-Regular.ttf','Inter-Bold.ttf','Inter-Italic.ttf'):
    try: font_manager.fontManager.addfont(f'{FDIR}/{_f}')
    except Exception: pass
plt.rcParams['font.family']='Inter'

OUT='Bases de datos/output_pacto_1v_2026'
PAPER='#faf8f2'; INK='#1a1510'; INK2='#6b6354'; GREY='#cfc8b8'
OX='#8a1e16'; NAVY='#16166b'; PURP='#534a8f'; GREEN='#2e7d46'; GOLD='#d99a2b'
DIF=json.load(open(f'{OUT}/dif_2022.json'))
BF=json.load(open(f'{OUT}/blocks_full.json'))['muni']
OVI=json.load(open(f'{OUT}/oviedo_bogota_localidad.json'))
EST=json.load(open(f'{OUT}/estrato_bogota.json'))['estratos']

# ───────── 1) Ciudades · techo (Cepeda hoy → Petro 2V 2022) ─────────
def ciudades_techo():
    cities=[('Barranquilla','03001'),('Bogotá','16001'),('Cali','31001'),('Medellín','01001')]
    rows=[]
    for nm,code in cities:
        v=BF[code]; rows.append((nm,v['cep26'],v['petro2v']))
    rows.sort(key=lambda r:(r[2]-r[1]))  # por espacio
    fig,ax=plt.subplots(figsize=(8.6,3.9)); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    ys=list(range(len(rows)))[::-1]
    for y,(nm,cep,techo) in zip(ys,rows):
        ax.plot([cep,techo],[y,y],color=GREY,lw=3,zorder=2,solid_capstyle='round')
        ax.scatter([cep],[y],s=120,color=PURP,zorder=4)
        ax.scatter([techo],[y],s=120,color=GREEN,zorder=4)
        ax.text(cep-1.2,y,f'{cep:.0f}',va='center',ha='right',fontsize=10.5,fontweight='bold',color=PURP)
        ax.text(techo+1.2,y,f'{techo:.0f}',va='center',ha='left',fontsize=10.5,fontweight='bold',color=GREEN)
        ax.text((cep+techo)/2,y+0.22,f'+{techo-cep:.0f}',va='bottom',ha='center',fontsize=9.5,fontweight='bold',color=INK2)
        ax.text(8,y,nm,va='center',ha='left',fontsize=11.5,fontweight='bold',color=INK)
    ax.set_xlim(6,70); ax.set_ylim(-0.6,len(rows)-0.4); ax.set_axis_off()
    ax.text(0.0,1.16,'El techo no es la caída: cuánto puede subir Cepeda',transform=ax.transAxes,fontsize=14.5,fontweight='bold',color=INK,va='top')
    ax.text(0.0,1.04,'Cepeda hoy (morado) y su techo: Petro en 2ª vuelta 2022 (verde)',transform=ax.transAxes,fontsize=9.6,color=INK2,va='top')
    fig.text(0.012,0.02,'Fuente: preconteo Registraduría 2026 + 2ª vuelta 2022 (GCS). % válidos + blanco.',fontsize=6.8,color=INK2)
    plt.tight_layout(rect=[0,0.04,1,0.9]); plt.savefig(f'{OUT}/g_ciudades_techo.png',dpi=170,facecolor=PAPER,bbox_inches='tight'); plt.close()
    print('✓ g_ciudades_techo.png')

# ───────── 2) Bogotá · recuperación por localidad (Cepeda26 − Petro1V22) ─────────
def bogota_recuperacion():
    rows=[(r[0],r[3]) for r in DIF['bogota_loc'] if r[0]!='Ciudad Bolivar']
    rows.sort(key=lambda r:r[1])
    fig,ax=plt.subplots(figsize=(7.2,5.6)); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    ys=list(range(len(rows)))
    for y,(nm,d) in zip(ys,rows):
        ax.barh(y,d,color=OX if d<=-5 else '#c98b7d',height=0.66,zorder=3)
        ax.text(d-0.15,y,f'{d:+.1f}',va='center',ha='right',fontsize=8.2,fontweight='bold',color=INK2)
        ax.text(0.25,y,nm,va='center',ha='left',fontsize=8.6,color=INK)
    ax.axvline(0,color=INK,lw=.8)
    ax.set_xlim(min(r[1] for r in rows)-2.2,3); ax.set_ylim(-0.7,len(rows)-0.3); ax.set_axis_off()
    fig.text(0.012,0.965,'Bogotá: la erosión fue transversal',fontsize=14,fontweight='bold',color=INK,ha='left',va='top')
    fig.text(0.012,0.925,'Cepeda 2026 − Petro 1ª vuelta 2022, por localidad (puntos)',fontsize=9.3,color=INK2,ha='left',va='top')
    fig.text(0.012,0.02,'Fuente: preconteo Registraduría 2026 + Petro 1ª 2022 (GCS) por localidad.',fontsize=6.8,color=INK2)
    plt.tight_layout(rect=[0,0.04,1,0.90]); plt.savefig(f'{OUT}/g_bogota_recuperacion.png',dpi=170,facecolor=PAPER,bbox_inches='tight'); plt.close()
    print('✓ g_bogota_recuperacion.png')

# ───────── 3) Oviedo Bogotá por localidad (coloreado por ganador 1V) ─────────
def oviedo_localidad():
    rows=sorted(OVI,key=lambda r:-r['oviedo'])
    disp=sum(r['oviedo'] for r in rows if r['win1v']=='Cepeda')
    der=sum(r['oviedo'] for r in rows if r['win1v']!='Cepeda')
    tot=disp+der
    fig,ax=plt.subplots(figsize=(7.6,6.0)); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    ys=list(range(len(rows)))[::-1]
    for y,r in zip(ys,rows):
        c=PURP if r['win1v']=='Cepeda' else NAVY
        ax.barh(y,r['oviedo'],color=c,height=0.68,zorder=3)
        ax.text(r['oviedo']+1500,y,f"{r['oviedo']:,}".replace(',','.'),va='center',ha='left',fontsize=7.4,color=INK2)
        ax.text(-1500,y,r['localidad'],va='center',ha='right',fontsize=8,color=INK)
    ax.set_xlim(-1500,max(r['oviedo'] for r in rows)*1.18); ax.set_ylim(-0.7,len(rows)-0.3); ax.set_axis_off()
    fig.text(0.012,0.965,'Bogotá: ¿de quién es el voto de Oviedo?',fontsize=14.5,fontweight='bold',color=INK,ha='left',va='top')
    fig.text(0.012,0.925,'Votos de Oviedo en la Gran Consulta (mar-2026), por localidad · color = quién ganó la localidad en 1ª vuelta',fontsize=8.8,color=INK2,ha='left',va='top')
    from matplotlib.patches import Patch
    leg=[Patch(facecolor=PURP,label=f'Localidad que ganó Cepeda · disputable · {disp:,} ({disp/tot*100:.0f}%)'.replace(',','.')),
         Patch(facecolor=NAVY,label=f'Localidad que ganó Abelardo · ya en la derecha · {der:,} ({der/tot*100:.0f}%)'.replace(',','.'))]
    ax.legend(handles=leg,loc='lower right',frameon=True,fontsize=7.6,facecolor=PAPER,edgecolor=GREY)
    fig.text(0.012,0.02,'ricardoruiz.co · Registraduría (consulta y 1ª vuelta 2026) · El hueco de Cepeda vs Petro-2022 en Bogotá: ~258.000 votos.',fontsize=6.6,color=INK2)
    plt.tight_layout(rect=[0,0.04,1,0.90]); plt.savefig(f'{OUT}/g_oviedo_bogota_localidad.png',dpi=170,facecolor=PAPER,bbox_inches='tight'); plt.close()
    print('✓ g_oviedo_bogota_localidad.png')

# ───────── 4) Bogotá por estrato (líneas + barras diferencial) ─────────
def bogota_estrato():
    from matplotlib import font_manager as fm
    E=list(range(1,7)); xs=list(range(6))
    cep=[EST[str(e)]['cepeda'] for e in E]; abe=[EST[str(e)]['abelardo'] for e in E]
    techo=[EST[str(e)]['pet2v22'] for e in E]; dif=[EST[str(e)]['dif_cep_pet'] for e in E]
    labels=[f"E{e}" for e in E]
    fig,(ax1,ax2)=plt.subplots(1,2,figsize=(11.4,4.6),gridspec_kw={'width_ratios':[1.32,1]})
    fig.patch.set_facecolor(PAPER)
    for ax in (ax1,ax2): ax.set_facecolor(PAPER)
    ax1.plot(xs,techo,'--',color=GREY,lw=1.6,zorder=2)
    ax1.plot(xs,cep,'-o',color=PURP,lw=3,ms=7,zorder=4,label='Cepeda 2026')
    ax1.plot(xs,abe,'-o',color=NAVY,lw=3,ms=7,zorder=4,label='Abelardo 2026')
    for x,(c,a) in enumerate(zip(cep,abe)):
        ax1.annotate(f'{c:.0f}',(x,c),textcoords='offset points',xytext=(0,9),ha='center',color=PURP,fontsize=9,fontweight='bold')
        ax1.annotate(f'{a:.0f}',(x,a),textcoords='offset points',xytext=(0,-16),ha='center',color=NAVY,fontsize=9,fontweight='bold')
    ax1.annotate('Empate técnico\nen estrato 3',(2,40.5),textcoords='offset points',xytext=(6,30),ha='left',fontsize=8.5,color=INK2,arrowprops=dict(arrowstyle='-',color=GREY,lw=1))
    ax1.annotate('Techo: Petro 2V 2022',(5,techo[5]),textcoords='offset points',xytext=(-6,8),ha='right',fontsize=8,color=INK2,style='italic')
    ax1.set_xticks(xs); ax1.set_xticklabels(labels,fontsize=10,color=INK)
    ax1.set_ylim(0,90); ax1.set_ylabel('% válidos + blanco',fontsize=9,color=INK2)
    ax1.set_title('La capital se ordena por estrato',fontsize=12.5,color=INK,fontweight='bold',loc='left',pad=10)
    ax1.legend(loc='upper right',frameon=False,fontsize=9.5)
    for s in ['top','right']: ax1.spines[s].set_visible(False)
    for s in ['left','bottom']: ax1.spines[s].set_color(GREY)
    ax1.tick_params(colors=INK2); ax1.grid(axis='y',color=GREY,alpha=.25,lw=.6)
    cols=[OX if e==4 else '#c98b7d' for e in E]
    ax2.bar(xs,dif,color=cols,width=.66,zorder=3)
    for x,v in zip(xs,dif):
        ax2.annotate(f'{v:+.1f}',(x,v),textcoords='offset points',xytext=(0,-13 if v<0 else 4),ha='center',fontsize=9,fontweight='bold',color=OX if E[x]==4 else INK2)
    ax2.axhline(0,color=INK,lw=.9)
    ax2.set_xticks(xs); ax2.set_xticklabels(labels,fontsize=10,color=INK); ax2.set_ylim(-8,1.4)
    ax2.set_title('Dónde cedió la izquierda\n(Cepeda 2026 − Petro 1ª 2022)',fontsize=11.5,color=INK,fontweight='bold',loc='left',pad=10)
    ax2.annotate('El golpe está en\nla clase media (E3-E4)',xy=(3,-6.3),xytext=(0.35,-3.0),ha='left',fontsize=8.8,color=OX,fontweight='bold',arrowprops=dict(arrowstyle='->',color=OX,lw=1.2))
    for s in ['top','right','left']: ax2.spines[s].set_visible(False)
    ax2.spines['bottom'].set_color(GREY); ax2.tick_params(colors=INK2,left=False); ax2.set_yticks([])
    fig.text(0.012,0.025,'Fuente: preconteo Registraduría 2026 + GCS 2022 · 1.038 puestos georreferenciados sobre 44.260 manzanas (estratificación SDP/IDECA, oct 2025) · join espacial point-in-polygon.',fontsize=6.7,color=INK2)
    plt.tight_layout(rect=[0,0.04,1,1]); plt.savefig(f'{OUT}/g_bogota_estrato.png',dpi=160,facecolor=PAPER,bbox_inches='tight'); plt.close()
    print('✓ g_bogota_estrato.png')

# ───────── 4b) Destino del voto de Oviedo (consulta → 1ª vuelta) ─────────
def oviedo_destino():
    PBLUE='#1866DF'
    dest=[('Cepeda',67,PURP),('Fajardo',20,GOLD),('Paloma',8,PBLUE),('Abelardo',5,NAVY)]
    fig,ax=plt.subplots(figsize=(8.4,3.5)); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    ys=list(range(len(dest)))[::-1]
    for y,(nm,v,c) in zip(ys,dest):
        ax.barh(y,v,color=c,height=0.62,zorder=3)
        ax.text(v+1.2,y,f'{v}%',va='center',ha='left',fontsize=13,fontweight='bold',color=c)
        ax.text(-1.5,y,nm,va='center',ha='right',fontsize=12,color=INK,fontweight='bold')
    ax.set_xlim(-12,82); ax.set_ylim(-0.7,len(dest)-0.3); ax.set_axis_off()
    fig.text(0.012,0.95,'¿A dónde se fue el voto de Oviedo?',fontsize=15.5,fontweight='bold',color=INK,ha='left',va='top')
    fig.text(0.012,0.875,'Destino estimado de los 1,26M de Oviedo (2º en la Gran Consulta) — cruce mesa a mesa',fontsize=9.6,color=INK2,ha='left',va='top')
    ax.annotate('La hipótesis a examinar',(8,1),xytext=(20,1.0),fontsize=9,color=PBLUE,fontweight='bold',va='center',
                arrowprops=dict(arrowstyle='->',color=PBLUE,lw=1.2))
    fig.text(0.012,0.05,'87% del voto de Oviedo se fue a la izquierda y el centro (Cepeda + Fajardo); solo 13% a la derecha (Paloma + Abelardo).',fontsize=8.2,color=OX,fontweight='bold')
    fig.text(0.012,0.012,'Estimación por inferencia ecológica sobre 8.431 puestos. La cota dura de King no fija el punto (techo teórico ~64%), pero la estimación y el perfil ideológico coinciden en que fue marginal.',fontsize=6.6,color=INK2)
    plt.tight_layout(rect=[0,0.10,1,0.85]); plt.savefig(f'{OUT}/g_oviedo_destino.png',dpi=170,facecolor=PAPER,bbox_inches='tight'); plt.close()
    print('✓ g_oviedo_destino.png')

# ───────── 5) Trasvase 2ª vuelta (composición + brecha) ─────────
def trasvase_2v():
    from matplotlib.patches import Patch
    M=json.load(open(f'{OUT}/twov_model.json'))
    MM=1_000_000
    abe=M['abe_comp']; cep=M['cep_comp']
    abe_tot=sum(v for _,v in abe); cep_tot=sum(v for _,v in cep); gap=abe_tot-cep_tot
    cabe=[NAVY,'#3c3c86','#6f6fa6','#a6a6c6']; ccep=[PURP,GOLD,GREEN]
    fig,ax=plt.subplots(figsize=(9.4,4.0)); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    def stack(y,comp,cols):
        x=0
        for (lbl,val),c in zip(comp,cols):
            ax.barh(y,val/MM,left=x/MM,color=c,height=0.52,zorder=3,edgecolor=PAPER,lw=1.2); x+=val
        return x
    xa=stack(1,abe,cabe); xc=stack(0,cep,ccep)
    # brecha (lo que falta) en la barra de Cepeda, hachurada
    ax.barh(0,(abe_tot-cep_tot)/MM,left=cep_tot/MM,color='none',edgecolor=OX,hatch='////',height=0.52,zorder=3,lw=0)
    ax.axvline(abe_tot/MM,color=OX,lw=1.6,ls=(0,(4,2)),zorder=4)
    # totales
    ax.text(xa/MM+0.12,1,f'{xa/MM:.2f}M',va='center',ha='left',fontsize=11,fontweight='bold',color=NAVY)
    ax.text(cep[0][1]/2/MM,0,f'{xc/MM:.2f}M',va='center',ha='center',fontsize=11,fontweight='bold',color='white',zorder=5)  # centrado en la base
    ax.text((cep_tot+gap/2)/MM,0,f'faltan\n{gap/MM:.1f}M',va='center',ha='center',fontsize=8.6,fontweight='bold',color=OX,zorder=6)
    ax.text(-0.15,1,'Abelardo',va='center',ha='right',fontsize=12.5,fontweight='bold',color=INK)
    ax.text(-0.15,0,'Cepeda',va='center',ha='right',fontsize=12.5,fontweight='bold',color=INK)
    ax.set_xlim(-2.2,13.4); ax.set_ylim(-0.6,1.7); ax.set_axis_off()
    ax.text(0.0,1.30,'¿Cuántos votos necesita Cepeda para ganar la 2ª vuelta?',transform=ax.transAxes,fontsize=14.5,fontweight='bold',color=INK,va='top')
    ax.text(0.0,1.18,'Composición estimada del voto de 2ª vuelta (escenario base de trasvase). La línea roja es el piso de la derecha consolidada.',transform=ax.transAxes,fontsize=9,color=INK2,va='top')
    leg=[Patch(facecolor=NAVY,label='Base 1V'),Patch(facecolor='#3c3c86',label='Paloma'),
         Patch(facecolor='#6f6fa6',label='Otros derecha'),Patch(facecolor=GOLD,label='Centro (Fajardo/Claudia)'),
         Patch(facecolor=GREEN,label='Minoritarios izq.'),Patch(facecolor='none',edgecolor=OX,hatch='////',label='Lo que falta: movilización')]
    ax.legend(handles=leg,loc='lower center',bbox_to_anchor=(0.5,-0.16),frameon=False,fontsize=8,ncol=3,columnspacing=1.4)
    fig.text(0.012,0.015,'Supuestos: Paloma 85% a Abelardo · Fajardo 55% Cepeda / 30% Abelardo · Claudia 65% / 20%. Cifras de preconteo. La movilización de nuevos votantes alimenta a ambos bloques.',fontsize=6.6,color=INK2)
    plt.tight_layout(rect=[0,0.08,1,0.86]); plt.savefig(f'{OUT}/g_trasvase_2v.png',dpi=170,facecolor=PAPER,bbox_inches='tight'); plt.close()
    print('✓ g_trasvase_2v.png')

def brecha_2v():   # referencia al final del Cap 2: cuánto debe crecer Cepeda (waterfall) + aviso de las 3 estrategias
    M=json.load(open(f'{OUT}/twov_model.json'))
    cep=M['votos']['cepeda']; centro=round(0.55*1007627+0.65*225287); mov=M['gap']; floor=M['abe_floor']
    nf=lambda v: f'{v/1e6:.2f}M'.replace('.',',')
    from matplotlib.patches import Patch
    fig,ax=plt.subplots(figsize=(9,2.6)); fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)
    y=0.55; h=0.46
    for x0,w,col in [(0,cep,PURP),(cep,centro,GOLD),(cep+centro,mov,GREEN)]:
        ax.barh(y,w,left=x0,height=h,color=col,edgecolor=PAPER,linewidth=1.6)
        ax.text(x0+w/2,y,nf(w),ha='center',va='center',color='white',fontsize=10.5,fontweight='bold',
                path_effects=[pe.withStroke(linewidth=1.4,foreground=col)])
    ax.axvline(floor,color=OX,linestyle=(0,(4,2)),linewidth=1.6)
    ax.text(floor,y+h/2+0.06,f'Piso de la derecha · {nf(floor)}',ha='center',va='bottom',color=OX,fontsize=9.5,fontweight='bold')
    ax.set_xlim(0,floor*1.07); ax.set_ylim(-0.05,1.30); ax.axis('off')
    ax.text(0,1.24,'Cuánto debe crecer Cepeda para empatar a la derecha en 2ª vuelta',fontsize=13,fontweight='bold',color=INK,va='top')
    ax.legend(handles=[Patch(color=PURP,label='Cepeda · 1ª vuelta'),Patch(color=GOLD,label='+ Centro (persuasión)'),
                       Patch(color=GREEN,label='+ Movilización (recuperación / abstención)')],
              loc='upper center',bbox_to_anchor=(0.5,0.16),ncol=3,frameon=False,fontsize=8.5,handlelength=1.0,handleheight=1.0,columnspacing=1.6)
    fig.text(0.012,0.02,'Cepeda parte de sus 9,68M de 1ª vuelta. Para igualar el piso de la derecha consolidada necesita sumar ~2,65M: ~0,7M del centro y ~1,9M de movilización. Esos dos bloques se desarrollan en el Capítulo 8 como tres estrategias.',fontsize=7.6,color=INK2)
    plt.savefig(f'{OUT}/g_brecha_2v.png',dpi=170,facecolor=PAPER,bbox_inches='tight'); plt.close()
    print('✓ g_brecha_2v.png')

if __name__=='__main__':
    ciudades_techo(); bogota_recuperacion(); oviedo_localidad(); oviedo_destino(); bogota_estrato(); trasvase_2v(); brecha_2v()
    print('✓ gráficos en Inter listos')
