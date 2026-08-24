#!/usr/bin/env python3
# Documento extenso 2V (~60 pág): reconciliación · geografía del margen · trasvases reales ·
# las 3 estrategias de Cepeda · participación · barrios en ciudades principales · municipios
# atípicos · veredicto + anexos. reportlab + Inter incrustada + TOC.
import json, csv, collections, os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, KeepTogether, PageBreak, Image, NextPageTemplate)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

OUT='Bases de datos/output_2v'; PDF=f'{OUT}/Analisis_2V_2026_Extendido.pdf'
LOGO='Bases de datos/output_abelardo_cartagena/logo_ricardoruiz.png'; HOY='22 de junio de 2026'
FB='tools/pacto-1v-2026/fonts/Inter-{}.ttf'
try:
    pdfmetrics.registerFont(TTFont('Inter',FB.format('Regular')))
    pdfmetrics.registerFont(TTFont('Inter-B',FB.format('Bold')))
    pdfmetrics.registerFont(TTFont('Inter-I',FB.format('Italic')))
    F,FBd,FI='Inter','Inter-B','Inter-I'
except Exception: F,FBd,FI='Helvetica','Helvetica-Bold','Helvetica-Oblique'
OX=HexColor('#8a1e16'); INK=HexColor('#1a1510'); MUT=HexColor('#6b6258'); CREAM=HexColor('#f4f0e7')
LINE=HexColor('#d8d0c4'); BLUE=HexColor('#1f47cc'); RED=HexColor('#c0392b')
def f(n): return f'{int(round(n)):,}'.replace(',','.')
def fs(n): return f'{int(round(n)):+,}'.replace(',','.')

# ───────── datos ─────────
AN=json.load(open(f'{OUT}/analisis_2v.json')); TR=json.load(open(f'{OUT}/trasvases.json')); BR=json.load(open(f'{OUT}/barrios_2v.json'))
EST_PACTO=json.load(open('Bases de datos/output_pacto_1v_2026/twov_estrategias.json'))
COM=json.load(open(f'{OUT}/comunas_2v.json'))
MUNROWS=list(csv.DictReader(open('tools/segunda-vuelta-prec/municipios_2v_vs_1v.csv',encoding='utf-8-sig')))
I=lambda r,k:int(r[k])
# nacionales (feed oficial)
CEP1,ABE1=9680095,10346010; CEP2,ABE2=12708712,12959542
MAR1,MAR2=ABE1-CEP1,ABE2-CEP2; PP2=100*MAR2/(ABE2+CEP2)
# depto agg del CSV
DEP=collections.defaultdict(lambda:{'c1':0,'a1':0,'c2':0,'a2':0})
for r in MUNROWS:
    d=DEP[r['depto']]; d['c1']+=I(r,'cep1v'); d['a1']+=I(r,'abe1v'); d['c2']+=I(r,'cep2v'); d['a2']+=I(r,'abe2v')

# ───────── estilos ─────────
def S(**k): return ParagraphStyle(k.pop('name'),**k)
st_kick=S(name='k',fontName=FBd,fontSize=8,textColor=OX,leading=10)
st_h1=S(name='t',fontName=FBd,fontSize=18,textColor=INK,leading=21)
st_sub=S(name='s',fontName=F,fontSize=10.5,textColor=MUT,leading=14)
st_cap=S(name='cap',fontName=FBd,fontSize=15,textColor=OX,leading=18,spaceBefore=2,spaceAfter=8)
st_h2=S(name='h2',fontName=FBd,fontSize=11.5,textColor=INK,leading=14,spaceBefore=10,spaceAfter=4)
st_body=S(name='b',fontName=F,fontSize=9.8,textColor=INK,leading=14.2,alignment=TA_JUSTIFY,spaceAfter=6)
st_note=S(name='n',fontName=F,fontSize=8.4,textColor=MUT,leading=11.6,alignment=TA_JUSTIFY)
st_bull=S(name='bu',fontName=F,fontSize=9.6,textColor=INK,leading=13.6,alignment=TA_JUSTIFY,spaceAfter=3,leftIndent=10,bulletIndent=0)
st_date=S(name='d',fontName=FBd,fontSize=8.6,textColor=INK,leading=11,alignment=TA_RIGHT)
cell=S(name='c',fontName=F,fontSize=8.6,textColor=INK,leading=10.8)
cellR=S(name='cr',fontName=F,fontSize=8.6,textColor=INK,leading=10.8,alignment=TA_RIGHT)
cellB=S(name='cb',fontName=FBd,fontSize=8.6,textColor=INK,leading=10.8)
cellBr=S(name='cbr',fontName=FBd,fontSize=8.6,textColor=INK,leading=10.8,alignment=TA_RIGHT)
hc=S(name='hc',fontName=FBd,fontSize=8,textColor=colors.white,leading=9.6)
hcR=S(name='hcr',fontName=FBd,fontSize=8,textColor=colors.white,leading=9.6,alignment=TA_RIGHT)
def col(t,c,b=True,r=True): return Paragraph(t,S(name='x',fontName=FBd if b else F,fontSize=8.6,textColor=c,leading=10.8,alignment=TA_RIGHT if r else TA_LEFT))

story=[]
def cap(txt,kick=''):
    story.append(PageBreak())
    if kick: story.append(Paragraph(kick.upper(),st_kick)); story.append(Spacer(1,3))
    p=Paragraph(txt,st_cap); p._tochead=('1',txt); story.append(p)
    story.append(HRFlowable(width='100%',thickness=1,color=OX)); story.append(Spacer(1,7))
def h2(txt):
    p=Paragraph(txt,st_h2); p._tochead=('2',txt); story.append(p)
def body(txt): story.append(Paragraph(txt,st_body))
def note(txt): story.append(Paragraph(txt,st_note))
def bullet(txt): story.append(Paragraph('• '+txt,st_bull))
def img(path,w,cap_=None):
    if not os.path.exists(path): return
    from PIL import Image as PImage
    iw,ih=PImage.open(path).size; h=w*ih/iw
    story.append(Image(path,width=w,height=h,hAlign='CENTER'))
    if cap_: story.append(Paragraph(cap_,S(name='ic',fontName=FI,fontSize=8.2,textColor=MUT,leading=10,alignment=TA_CENTER,spaceBefore=2)))
    story.append(Spacer(1,4))
def mktable(data,widths,zebra=True,head=OX,pad=3.0,fs=None):
    t=Table(data,colWidths=widths,hAlign='LEFT')
    sty=[('BACKGROUND',(0,0),(-1,0),head),('TOPPADDING',(0,0),(-1,-1),pad),('BOTTOMPADDING',(0,0),(-1,-1),pad),
         ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
         ('LINEBELOW',(0,0),(-1,0),0.5,head),('LINEBELOW',(0,1),(-1,-1),0.3,LINE)]
    if zebra:
        for i in range(2,len(data),2): sty.append(('BACKGROUND',(0,i),(-1,i),CREAM))
    t.setStyle(TableStyle(sty)); return t

# ════════════════════ PORTADA ════════════════════
_lw=52*mm; _lh=_lw*201/2361
hdr=Table([[Paragraph('ELECCIONES COLOMBIA 2026<br/>SEGUNDA VUELTA PRESIDENCIAL',st_kick),Image(LOGO,width=_lw,height=_lh)],
           ['',Paragraph(HOY,st_date)]],colWidths=[112*mm,_lw])
hdr.setStyle(TableStyle([('SPAN',(0,0),(0,1)),('VALIGN',(0,0),(0,0),'TOP'),('VALIGN',(1,0),(1,1),'TOP'),
    ('ALIGN',(1,0),(1,1),'RIGHT'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
    ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),('TOPPADDING',(1,1),(1,1),4)]))
story.append(Spacer(1,4)); story.append(hdr); story.append(Spacer(1,30))
story.append(Paragraph('¿Dónde y por qué ganó Abelardo<br/>la segunda vuelta?',S(name='big',fontName=FBd,fontSize=27,textColor=INK,leading=31)))
story.append(Spacer(1,8))
story.append(Paragraph('Anatomía territorial del balotaje presidencial: trasvases reales, evaluación de '
  'las tres estrategias del Pacto, la marea de participación y el voto barrio a barrio en las ciudades '
  'principales. Comparativo del preconteo de 2ª vuelta (100% de mesas) frente al escrutinio de 1ª vuelta.',
  S(name='subbig',fontName=F,fontSize=12,textColor=MUT,leading=17)))
story.append(Spacer(1,20))
# caja de cifras de portada
kp=[[Paragraph('Resultado 2ª vuelta',S(name='kl',fontName=FBd,fontSize=8,textColor=OX,leading=10)),'','',''],
 [col(f(CEP2),RED,r=False),col(f(ABE2),BLUE,r=False),col(f'{PP2:.2f} pp',INK,r=False),col('+'+f(MAR2),BLUE,r=False)],
 [Paragraph('Cepeda',cell),Paragraph('Abelardo',cell),Paragraph('margen',cell),Paragraph('votos',cell)]]
kt=Table(kp,colWidths=[42*mm,42*mm,38*mm,40*mm]); kt.setStyle(TableStyle([('SPAN',(0,0),(-1,0)),
  ('LINEABOVE',(0,1),(-1,1),0.6,LINE),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),3),
  ('LEFTPADDING',(0,0),(-1,-1),2)]))
story.append(kt); story.append(Spacer(1,16))
story.append(HRFlowable(width='100%',thickness=1.1,color=OX)); story.append(Spacer(1,5))
story.append(Paragraph('ricardoruiz.co · Inteligencia electoral · Cifras no oficiales (preconteo)',st_note))

# ════════════════════ TOC ════════════════════
story.append(PageBreak())
story.append(Paragraph('Contenido',st_cap)); story.append(HRFlowable(width='100%',thickness=1,color=OX)); story.append(Spacer(1,8))
toc=TableOfContents()
toc.levelStyles=[S(name='toc1',fontName=FBd,fontSize=10.5,textColor=INK,leading=18,leftIndent=0),
                 S(name='toc2',fontName=F,fontSize=9,textColor=MUT,leading=13,leftIndent=14)]
story.append(toc)

# ════════════════════ RESUMEN EJECUTIVO ════════════════════
cap('Resumen ejecutivo','Lo esencial')
body(f'Abelardo De La Espriella ganó la segunda vuelta presidencial por <b>{f(MAR2)} votos</b> '
 f'({PP2:.2f} puntos porcentuales): <b>{f(ABE2)}</b> contra <b>{f(CEP2)}</b> de Iván Cepeda. '
 'Es el margen más estrecho de una elección presidencial colombiana en la era reciente, y la pregunta '
 'que organiza este documento es doble: <b>dónde</b> se definió y <b>por qué</b> terminó así.')
body('La respuesta corta desafía la lectura de la noche electoral. Cepeda <b>no perdió por falta de '
 'estrategia</b>: ejecutó bien las tres campañas que se había trazado —persuadir al centro, recuperar '
 'sus zonas duras y movilizar la abstención— y aun así no alcanzó. Abelardo ganó porque <b>partía '
 'estructuralmente más arriba desde la primera vuelta</b> y porque la ola de participación, al ser '
 'nacional y no dirigible, lo alimentó en sus bastiones tanto como a Cepeda en los suyos.')
h2('Ocho hallazgos')
for t in [
 f'<b>Antioquia define la elección.</b> Abelardo saca allí <b>+1,05 millones</b> de margen neto, más de cuatro veces el margen nacional. Sin Antioquia, Cepeda sería presidente por ~800.000 votos.',
 f'<b>El cara a cara se movió hacia Cepeda, no hacia Abelardo.</b> Abelardo lideraba la 1ª vuelta por {fs(MAR1)} y ganó la 2ª por {fs(MAR2)}: el margen se encogió {f(MAR1-MAR2)} votos. El envión fue de Cepeda; simplemente no bastó.',
 '<b>La derecha se consolidó como esperado:</b> el bloque de Paloma Valencia y los minoritarios de derecha fue <b>81% a Abelardo</b>, casi exacto al supuesto del modelo.',
 '<b>Cepeda capturó el centro mejor de lo previsto:</b> el voto de Fajardo + Claudia fue <b>81% a Cepeda</b>, por encima del 55–65% que asumían los modelos.',
 '<b>Cepeda ganó la batalla de la movilización</b> —los nuevos votantes fueron ~81% para él a nivel nacional— pero la participación subió parejo en todo el país, así que no produjo ventaja decisiva.',
 '<b>Las tres estrategias del Pacto cuajaron:</b> Centro al 143% del objetivo, Recuperación al 100% del techo, Abstención con +667.000 netos en sus municipios prioritarios. Y aun así perdió.',
 '<b>Barrio a barrio,</b> Abelardo arrasa en Medellín (gana 139 de 158 barrios), Cúcuta (59 de 59) y Bucaramanga (64 de 66); Cepeda domina Cali, Cartagena, Barranquilla y el sur de Bogotá.',
 '<b>El veredicto:</b> la elección estaba estructuralmente inclinada desde la 1ª vuelta. Cepeda hizo la tarea y recortó casi toda la distancia; Abelardo ganó por la herencia y porque la marea no tenía dueño.',
]: bullet(t)
img(f'{OUT}/graficos/g_balance.png',150*mm)

# ════════════════════ PARTE 1: RECONCILIACIÓN + GEOGRAFÍA ════════════════════
cap('El resultado y la geografía del margen','Parte 1')
h2('1.1 · La reconciliación nacional')
body('El preconteo de segunda vuelta cerró con el 100% de las mesas. El cuadro siguiente contrasta el '
 'cara a cara de la primera vuelta (escrutinio interno por mesa) con el resultado de la segunda y con lo '
 'que un trasvase mecánico de bloques de 1ª vuelta habría predicho.')
d=[[Paragraph('Escenario',hc),Paragraph('Cepeda',hcR),Paragraph('Abelardo',hcR),Paragraph('Margen Abelardo',hcR)],
 [Paragraph('1ª vuelta (cara a cara)',cell),Paragraph(f(CEP1),cellR),Paragraph(f(ABE1),cellR),col(fs(MAR1),BLUE)],
 [Paragraph('2ª vuelta (preconteo, 100%)',cellB),Paragraph(f(CEP2),cellBr),Paragraph(f(ABE2),cellBr),col(f'{fs(MAR2)} ({PP2:.2f} pp)',BLUE)],
 [Paragraph('Esperado por trasvase de bloques',cell),Paragraph('—',cellR),Paragraph('53,5%',cellR),col('real 50,5%',MUT,b=False)]]
story.append(mktable(d,[74*mm,30*mm,30*mm,38*mm])); story.append(Spacer(1,4))
note('El margen se encogió de '+fs(MAR1)+' a '+fs(MAR2)+': el movimiento de segunda vuelta favoreció a '
 'Cepeda en unos 415.000 votos netos. Aun así, Abelardo quedó casi 3 puntos por debajo del trasvase '
 'mecánico de la derecha —mucho voto de derecha de 1ª vuelta se quedó en casa— pero su herencia bastó.')
h2('1.2 · Antioquia define la elección')
body('La victoria está geográficamente concentrada hasta un punto extraordinario. Abelardo obtiene en '
 'Antioquia un margen neto de <b>+1.052.153 votos</b> —el 419% del margen nacional—. El Valle de Aburrá '
 'aporta +684.000 y solo Medellín +397.000, más que el margen nacional entero. Sumados Antioquia, Norte '
 'de Santander y Santander, el margen es de +1,87 millones: los otros 31 departamentos más el exterior, '
 'en conjunto, favorecen a Cepeda por 1,62 millones. <b>La elección es, esencialmente, Antioquia contra '
 'el resto del país.</b>')
img(f'{OUT}/graficos/g_margen_depto.png',122*mm,'Margen neto de 2ª vuelta por departamento. Antioquia, sola, multiplica por cuatro el margen nacional.')

# top municipios: donde concentra cada uno el margen
h2('1.3 · Dónde concentra cada uno su margen')
sub=[Paragraph('Municipio',hc),Paragraph('Depto',hc),Paragraph('Margen',hcR)]
topA=sorted(MUNROWS,key=lambda r:-I(r,'margen2v'))[:18]; topC=sorted(MUNROWS,key=lambda r:I(r,'margen2v'))[:18]
dA=[sub]+[[Paragraph(r['municipio'].title(),cell),Paragraph(r['depto'],cell),col('+'+f(I(r,'margen2v')),BLUE,b=False)] for r in topA]
dC=[sub]+[[Paragraph(r['municipio'].title(),cell),Paragraph(r['depto'],cell),col('+'+f(-I(r,'margen2v')),RED,b=False)] for r in topC]
side=Table([[mktable(dA,[34*mm,26*mm,20*mm],head=BLUE),mktable(dC,[34*mm,26*mm,20*mm],head=RED)]],colWidths=[84*mm,84*mm])
side.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(0,0),6)]))
story.append(Paragraph('Top 18 municipios por margen neto de Abelardo (izq.) y de Cepeda (der.)',S(name='cp',fontName=FI,fontSize=8.4,textColor=MUT,leading=11)))
story.append(Spacer(1,3)); story.append(side)

h2('1.4 · El país por regiones')
REGS=[('Región Andina','01 07 09 15 16 19 24 25 26 27 29'),('Caribe','03 05 12 13 21 28 48 56'),
      ('Pacífico','11 17 23 31'),('Orinoquía y Amazonía','40 44 46 50 52 54 60 64 68 72')]
rg=collections.defaultdict(lambda:[0,0])
cod2reg={}
for nm,cods in REGS:
    for c in cods.split(): cod2reg[c]=nm
for r in MUNROWS:
    reg=cod2reg.get(r['cod'][:2]);
    if reg: rg[reg][0]+=I(r,'cep2v'); rg[reg][1]+=I(r,'abe2v')
body('Agrupado por grandes regiones, el patrón es inequívoco: Abelardo gana solo en la región Andina '
 '—y la gana por el peso de Antioquia y los Santanderes—, mientras Cepeda domina el Caribe, el Pacífico '
 'y, por estrecho margen, la Orinoquía-Amazonía. La elección es, en el fondo, el interior andino-paisa '
 'contra las periferias costeras y del sur.')
d=[[Paragraph('Región',hc),Paragraph('Cepeda',hcR),Paragraph('Abelardo',hcR),Paragraph('Margen',hcR),Paragraph('Gana',hcR)]]
for nm,_ in REGS:
    c2,a2=rg[nm]; m=a2-c2
    d.append([Paragraph(nm,cellB),Paragraph(f(c2),cellR),Paragraph(f(a2),cellR),col(fs(m),BLUE if m>0 else RED),
              col('Abelardo' if m>0 else 'Cepeda',BLUE if m>0 else RED)])
story.append(mktable(d,[52*mm,28*mm,28*mm,30*mm,28*mm])); story.append(Spacer(1,5))
bullet('<b>Región Andina:</b> el único bastión de Abelardo, y le alcanza por Antioquia y los Santanderes. '
 'Pero la región es heterogénea: Bogotá, Boyacá y Cundinamarca matizan la ventaja, y sin el eje paisa-'
 'santandereano la región sería competida.')
bullet('<b>Caribe:</b> territorio de Cepeda. El Pacto domina Bolívar, Magdalena, Córdoba, Sucre y La '
 'Guajira; la excepción parcial es el Atlántico urbano, donde Barranquilla resiste mejor para Abelardo. '
 'Cartagena, Soledad y los municipios populares de la costa fueron decisivos para Cepeda.')
bullet('<b>Pacífico:</b> el muro más sólido de Cepeda. Cauca, Nariño, Chocó y el oriente de Cali le dan '
 'márgenes abrumadores —en varios municipios supera el 70%—. Es la contracara geográfica de Antioquia.')
bullet('<b>Orinoquía y Amazonía:</b> la región más dividida. Los llanos petroleros (Casanare, Meta, '
 'Arauca) se inclinan a Abelardo, mientras el piedemonte y el sur amazónico (Putumayo, Amazonas) van a '
 'Cepeda. Pesan poco en el total nacional pero ilustran la fractura centro-periferia.')

h2('1.5 · Lo que se movió frente a la primera vuelta')
body('El mapa apenas cambió de color entre vueltas: la mayoría de los municipios mantuvo a su ganador. '
 'Lo que cambió fue la <b>intensidad</b>. Estos son los municipios donde el cara a cara más se movió en '
 'cada dirección (frente a la 1ª vuelta), entre los de mayor tamaño electoral.')
big=[r for r in MUNROWS if I(r,'cep2v')+I(r,'abe2v')>=20000]
mvA=sorted(big,key=lambda r:-I(r,'delta_margen'))[:10]; mvC=sorted(big,key=lambda r:I(r,'delta_margen'))[:10]
hh=[Paragraph('Municipio',hc),Paragraph('Δ margen',hcR)]
dA=[hh]+[[Paragraph(r['municipio'].title()+f" ({r['depto']})",cell),col(fs(I(r,'delta_margen')),BLUE)] for r in mvA]
dC=[hh]+[[Paragraph(r['municipio'].title()+f" ({r['depto']})",cell),col(fs(I(r,'delta_margen')),RED)] for r in mvC]
side2=Table([[mktable(dA,[58*mm,22*mm],head=BLUE),mktable(dC,[58*mm,22*mm],head=RED)]],colWidths=[84*mm,84*mm])
side2.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(0,0),6)]))
story.append(Paragraph('Mayor movimiento hacia Abelardo (izq.) y hacia Cepeda (der.), en votos de margen',S(name='cp3',fontName=FI,fontSize=8.4,textColor=MUT,leading=11)))
story.append(Spacer(1,3)); story.append(side2); story.append(Spacer(1,4))
note('Se movieron hacia Cepeda sobre todo las grandes ciudades donde ya ganaba (Bogotá, Cali, Cartagena, '
 'Barranquilla): corrió el marcador donde no cambiaba el resultado. Hacia Abelardo se movieron su fortaleza '
 'antioqueña (Medellín, Rionegro, Envigado), los Santanderes y el voto del exterior.')

h2('1.6 · El voto del exterior')
ext=[r for r in MUNROWS if r['depto']=='Exterior']
ec2=sum(I(r,'cep2v') for r in ext); ea2=sum(I(r,'abe2v') for r in ext)
body(f'El voto de los colombianos en el exterior —{f(ec2+ea2)} sufragios entre los dos finalistas— '
 f'se inclinó marcadamente por Abelardo: <b>{f(ea2)} contra {f(ec2)}</b> de Cepeda, un margen de '
 f'<b>{fs(ea2-ec2)}</b>. <b>Estados Unidos, por sí solo, fue el tercer mayor aporte de margen de Abelardo '
 'en todo el país</b> —por encima de cualquier ciudad colombiana salvo Medellín y Cúcuta—. La diáspora, '
 'sobre todo la del norte, votó derecha con una contundencia que sorprende frente al promedio nacional.')
topE=sorted(ext,key=lambda r:-abs(I(r,'margen2v')))[:8]
d=[[Paragraph('Consulado / país',hc),Paragraph('Cepeda',hcR),Paragraph('Abelardo',hcR),Paragraph('Margen',hcR)]]
for r in topE:
    m=I(r,'margen2v')
    d.append([Paragraph(r['municipio'].title(),cell),Paragraph(f(I(r,'cep2v')),cellR),Paragraph(f(I(r,'abe2v')),cellR),col(fs(m),BLUE if m>0 else RED)])
story.append(mktable(d,[58*mm,28*mm,28*mm,30*mm]))

story.append(PageBreak())
p=Paragraph('1.7 · Antioquia: la máquina que decidió la elección',st_h2); p._tochead=('2','Antioquia: la máquina'); story.append(p)
ant=[r for r in MUNROWS if r['depto']=='Antioquia']
ac2=sum(I(r,'cep2v') for r in ant); aa2=sum(I(r,'abe2v') for r in ant)
body(f'Ningún análisis de esta elección está completo sin detenerse en Antioquia. El departamento entregó '
 f'a Abelardo <b>{f(aa2)} votos contra {f(ac2)}</b> de Cepeda: un margen de <b>{fs(aa2-ac2)}</b> que, por '
 'sí solo, multiplica por más de cuatro el margen nacional. Es una concentración de poder electoral sin '
 'paralelo en el país, y la razón última por la que Abelardo es presidente.')
body('La fuerza antioqueña no es homogénea ni casual. Se asienta en tres anillos: el <b>Valle de Aburrá</b> '
 '(Medellín y su corona metropolitana —Bello, Itagüí, Envigado, Sabaneta—), que aporta el grueso del '
 'margen; el <b>Oriente cercano</b> (Rionegro y los municipios del altiplano, en plena expansión '
 'demográfica y de clase media-alta); y el <b>Suroeste y Norte</b> cafetero-paisa, conservador y '
 'tradicionalmente uribista. Sobre esa base, el trasvase de la derecha de 1ª vuelta operó con máxima '
 'eficiencia: el votante de Paloma en Antioquia no dudó.')
topAnt=sorted(ant,key=lambda r:-I(r,'margen2v'))[:14]
d=[[Paragraph('Municipio',hc),Paragraph('Cepeda',hcR),Paragraph('Abelardo',hcR),Paragraph('Margen Abelardo',hcR)]]
for r in topAnt:
    d.append([Paragraph(r['municipio'].title(),cell),Paragraph(f(I(r,'cep2v')),cellR),Paragraph(f(I(r,'abe2v')),cellR),col('+'+f(I(r,'margen2v')),BLUE)])
story.append(Paragraph('Los 14 municipios de Antioquia con mayor margen para Abelardo',S(name='cpan',fontName=FI,fontSize=8.4,textColor=MUT,leading=11)))
story.append(Spacer(1,3)); story.append(mktable(d,[44*mm,28*mm,28*mm,34*mm]))
note('Medellín sola aporta +397.000 de margen —más que el margen nacional entero—. El Valle de Aburrá '
 'completo supera los +684.000. Para dimensionarlo: Cepeda tendría que haber dado vuelta a TODA Antioquia '
 'y aun así apenas habría empatado el resto del país.')

print('parte 1 ok; story items:',len(story))

# ════════════════════ PARTE 2: TRASVASES ════════════════════
cap('Cómo terminaron realmente los trasvases','Parte 2')
body('Los modelos de segunda vuelta asumen coeficientes de trasvase: qué fracción del voto de cada '
 'candidato eliminado se mueve a cada finalista. Con el resultado real ya podemos estimar <b>cómo '
 'terminaron de verdad</b> esos trasvases, y de paso a dónde fue la masa de nuevos votantes que produjo '
 'el salto de participación.')
h2('2.1 · Método')
body('Se usa inferencia ecológica sobre los 1.189 municipios: se regresan los incrementos de Cepeda y '
 'Abelardo (2ª vuelta menos 1ª) sobre los votos de cada fuente de 1ª vuelta y sobre el cambio de '
 'participación, con coeficientes acotados entre 0 y 1 y la restricción de que las dos tasas de cada '
 'fuente no sumen más de 100%. Los intervalos vienen de un bootstrap de 400 remuestreos de municipios.')
note('Salvedad: la inferencia ecológica no separa fuentes que votan en los mismos territorios (Paloma y '
 'los minoritarios de derecha, por ejemplo). Por eso se estima por BLOQUE —donde la identificación es '
 'estable— y la tasa del bloque se atribuye a cada candidato que lo compone. Es análisis agregado: dice a '
 'dónde se movió el voto, no quién individualmente cambió de decisión.')
img(f'{OUT}/graficos/g_trasvases.png',155*mm)
h2('2.2 · El resultado, bloque por bloque')
comp=TR['comp']
d=[[Paragraph('Bloque de 1ª vuelta',hc),Paragraph('Votos',hcR),Paragraph('a Cepeda',hcR),Paragraph('a Abelardo',hcR),Paragraph('Supuesto previo',hc)]]
rowsT=[('Derecha (84% Paloma)',0,'85% a Abelardo'),('Centro (Fajardo+Claudia)',1,'55–65% a Cepeda'),
       ('Izquierda menor',2,'85% a Cepeda'),('Nuevos votantes',3,'(no modelado)')]
for nm,j,sup in rowsT:
    ac,ab=TR['a_cep'][j],TR['b_abe'][j]
    d.append([Paragraph(nm,cellB),Paragraph(f(TR['src_total'][j]),cellR),
              col(f'{100*ac:.0f}%',RED),col(f'{100*ab:.0f}%',BLUE),Paragraph(sup,cell)])
story.append(mktable(d,[52*mm,24*mm,24*mm,26*mm,42*mm])); story.append(Spacer(1,5))
body('<b>La derecha se consolidó como estaba previsto:</b> el bloque encabezado por Paloma Valencia '
 '(84% de su masa) fue 81% a Abelardo, a un punto del supuesto clásico del 85%. <b>El centro rindió mejor '
 'a Cepeda de lo esperado:</b> Fajardo y Claudia fueron 81% a Cepeda, no el 55–65% que asumían los '
 'modelos —la tarea de persuasión del Pacto funcionó—. <b>La izquierda menor</b> (Roy, Caicedo, Murillo) '
 'fue íntegra a Cepeda. Y los <b>nuevos votantes</b>, la masa más grande de todas (2,3 millones), se '
 'inclinaron 81% a Cepeda en el promedio nacional.')
body('La paradoja queda planteada: Cepeda capturó el centro, barrió la izquierda menor y ganó la '
 'movilización. ¿Cómo perdió entonces? Porque el bloque de derecha era más grande de entrada, porque '
 'Abelardo partía con 666.000 votos de ventaja, y porque —como muestra la Parte 4— la masa de nuevos '
 'votantes no se repartió uniforme: en los bastiones de Abelardo, también fue para él.')

h2('2.3 · Traducido a cada candidato')
cmp=TR['comp']; ac_d,ab_d=TR['a_cep'][0],TR['b_abe'][0]; ac_c,ab_c=TR['a_cep'][1],TR['b_abe'][1]
body('Atribuyendo a cada candidato la tasa de su bloque (con la salvedad de que la inferencia ecológica '
 'no separa con precisión dentro de un mismo bloque territorial), los trasvases reales se leen así:')
d=[[Paragraph('Candidato 1ª vuelta',hc),Paragraph('Votos',hcR),Paragraph('a Cepeda',hcR),Paragraph('a Abelardo',hcR),Paragraph('a blanco/abst.',hcR)]]
def fila(nm,tot,acep,aabe):
    resto=max(0,1-acep-aabe)
    return [Paragraph(nm,cellB),Paragraph(f(tot),cellR),col(f(acep*tot),RED,b=False),col(f(aabe*tot),BLUE,b=False),Paragraph(f(resto*tot),cellR)]
d.append(fila('Paloma Valencia',cmp['paloma_tot'],ac_d,ab_d))
d.append(fila('Sergio Fajardo',cmp['fajardo_tot'],ac_c,ab_c))
d.append(fila('Claudia López',cmp['claudia_tot'],ac_c,ab_c))
story.append(mktable(d,[48*mm,24*mm,28*mm,28*mm,32*mm])); story.append(Spacer(1,5))
body(f'<b>Paloma Valencia</b> entregó unos {f(ab_d*cmp["paloma_tot"])} votos a Abelardo: fue el '
 'combustible principal de su consolidación. <b>Fajardo y Claudia</b> alimentaron a Cepeda con cerca de '
 f'{f(ac_c*(cmp["fajardo_tot"]+cmp["claudia_tot"]))} votos combinados. Cualitativamente, el voto de '
 'Claudia —más cercano a la centro-izquierda— probablemente se inclinó aún más a Cepeda que el de '
 'Fajardo, aunque la inferencia agregada no permite separarlos con exactitud dentro del bloque de centro.')
note('La "fuga a blanco/abstención" no es despreciable: cerca del 15% del centro no acompañó a ninguno '
 'de los dos finalistas, votando en blanco o quedándose en casa. En el bloque de derecha esa fuga fue '
 'menor, señal de que el votante de Paloma se sintió más representado por Abelardo que el de Fajardo por Cepeda.')

print('parte 2 ok; story items:',len(story))

# ════════════════════ PARTE 3: LAS 3 ESTRATEGIAS ════════════════════
E=AN['estrategias']
cap('¿Cuajaron las tres estrategias de Cepeda?','Parte 3')
body('La campaña del Pacto dividió el camino a la segunda vuelta en tres frentes distintos, cada uno con '
 'su propio universo de votos: <b>persuadir al centro</b> (Estrategia 1), <b>recuperar las zonas duras</b> '
 'de la izquierda demovilizada (Estrategia 2) y <b>movilizar la abstención</b> donde el Pacto es fuerte '
 '(Estrategia 3). Con el resultado real podemos auditar, una por una, si cuajaron.')
img(f'{OUT}/graficos/g_estrategias.png',150*mm,'Objetivo de cada estrategia vs. resultado real estimado.')

h2('3.1 · Estrategia 1 — Centro (persuasión)')
body(f'<b>Veredicto: cuajó, y de sobra.</b> El objetivo era persuadir el voto de centro transferible —'
 f'estimado en {f(E["centro"]["target"])} votos (0,55 × Fajardo + 0,65 × Claudia)—. El trasvase real '
 f'llevó <b>{f(E["centro"]["real_a_cepeda"])} votos del centro a Cepeda</b>, el 143% del objetivo: el '
 'centro fue 81% para él, no el 55–65% planeado. De las tres campañas, esta es la que mejor rindió.')
body('Los municipios donde estaba concentrado ese voto de centro —el mapa de prioridad de la campaña de '
 'persuasión— eran sobre todo las grandes ciudades:')
d=[[Paragraph('Municipio',hc),Paragraph('Depto',hc),Paragraph('Fajardo',hcR),Paragraph('Claudia',hcR),Paragraph('Centro transf.',hcR)]]
for r in EST_PACTO['centro_top'][:10]:
    d.append([Paragraph(r['muni'].title(),cell),Paragraph(r['dep'],cell),Paragraph(f(r['faj']),cellR),Paragraph(f(r['cla']),cellR),col(f(r['tr']),OX,b=False)])
story.append(mktable(d,[42*mm,34*mm,26*mm,26*mm,30*mm]))
h2('3.2 · Estrategia 2 — Recuperación (zonas duras)')
body(f'<b>Veredicto: cuajó al 100%.</b> El objetivo era recuperar el techo de la izquierda —el voto que '
 f'Petro tuvo en la 2ª vuelta de 2022 y que Cepeda aún no tenía en 1ª, unos {f(E["recuperacion"]["target"])} '
 f'votos—. En esas zonas Cepeda creció {f(E["recuperacion"]["logrado"])} votos entre vueltas, alcanzando '
 'el techo histórico. La izquierda demovilizada volvió. El problema no fue de recuperación.')
d=[[Paragraph('Municipio',hc),Paragraph('Depto',hc),Paragraph('Cepeda 1V',hcR),Paragraph('Techo Petro 2V',hcR),Paragraph('Por recuperar',hcR)]]
for r in EST_PACTO['rec_top'][:10]:
    d.append([Paragraph(r['muni'].title(),cell),Paragraph(r['dep'],cell),Paragraph(f(r['cep_now']),cellR),Paragraph(f(r['techo']),cellR),col(f(r['recuperar']),OX,b=False)])
story.append(Paragraph('Los 10 municipios con mayor techo de recuperación (votos de Petro-2V que Cepeda no tenía en 1ª)',S(name='cpr',fontName=FI,fontSize=8.4,textColor=MUT,leading=11)))
story.append(Spacer(1,3)); story.append(mktable(d,[42*mm,30*mm,26*mm,30*mm,28*mm]))
h2('3.3 · Estrategia 3 — Abstención (movilización)')
A3=E['abstencion']
body(f'<b>Veredicto: cuajó en los números, pero sin la ventaja que prometía.</b> En los {A3["n_muni"]} '
 f'municipios prioritarios del Pacto, la participación subió y rindió <b>+{f(A3["dcep_target"]-A3["dabe_target"])} '
 f'votos netos</b> a Cepeda. Pero aquí está la trampa: la participación subió <b>prácticamente igual</b> '
 f'en los municipios objetivo ({A3["part1_target"]}% a {A3["part2_target"]}%) que en el resto del país '
 f'({A3["part1_resto"]}% a {A3["part2_resto"]}%).')
d=[[Paragraph('',hc),Paragraph('Participación 1V',hcR),Paragraph('Participación 2V',hcR),Paragraph('Subió',hcR)],
 [Paragraph('Municipios objetivo del Pacto',cellB),Paragraph(f'{A3["part1_target"]}%',cellR),Paragraph(f'{A3["part2_target"]}%',cellBr),col(f'+{A3["part2_target"]-A3["part1_target"]:.1f} pp',INK)],
 [Paragraph('Resto del país',cell),Paragraph(f'{A3["part1_resto"]}%',cellR),Paragraph(f'{A3["part2_resto"]}%',cellR),col(f'+{A3["part2_resto"]-A3["part1_resto"]:.1f} pp',INK)]]
story.append(mktable(d,[70*mm,34*mm,34*mm,28*mm])); story.append(Spacer(1,5))
body('La movilización no fue diferencial: <b>fue una marea nacional, no una operación quirúrgica</b>. Y '
 'una marea que sube por igual en todas partes favorece a quien tiene más territorio. Como Abelardo '
 'dominaba más municipios y partía arriba, la misma ola que llevó votantes nuevos a Cepeda en el Pacífico '
 'y el sur se los llevó a Abelardo en Antioquia y los Santanderes.')
d=[[Paragraph('Municipio',hc),Paragraph('Depto',hc),Paragraph('Censo',hcR),Paragraph('Abstención 1V',hcR),Paragraph('Share Pacto 2V',hcR),Paragraph('Neto Cepeda',hcR)]]
for r in EST_PACTO['abst_top'][:10]:
    d.append([Paragraph(r['muni'].title(),cell),Paragraph(r['dep'],cell),Paragraph(f(r['censo']),cellR),Paragraph(f(r['ab']),cellR),Paragraph(f"{r['sh']}%",cellR),col(f(r['neto']),OX,b=False)])
story.append(Paragraph('Los 10 municipios prioritarios de movilización (mayor voto neto a ganar sacando abstención)',S(name='cpa',fontName=FI,fontSize=8.4,textColor=MUT,leading=11)))
story.append(Spacer(1,3)); story.append(mktable(d,[34*mm,24*mm,24*mm,26*mm,26*mm,24*mm]))
h2('3.4 · Síntesis: hizo la tarea y perdió')
body('Las tres estrategias se ejecutaron. El centro se persuadió por encima de la meta, las zonas duras '
 'se recuperaron, la abstención se movilizó. El resultado combinado fue un crecimiento de Cepeda de casi '
 '3 millones de votos entre vueltas —más que el crecimiento de Abelardo—. Pero la aritmética de partida '
 'era adversa: cuando empiezas 666.000 votos abajo y la herramienta más poderosa (la participación) no '
 'tiene dueño territorial, ejecutar bien no garantiza ganar.')

print('parte 3 ok; story items:',len(story))

# ════════════════════ PARTE 4: PARTICIPACIÓN ════════════════════
P=AN['participacion']
cap('La marea de participación','Parte 4')
body(f'La participación nacional subió de <b>{P["nac_part1"]}% a {P["nac_part2"]}%</b>, unos '
 f'<b>{f(P["dvot_nac"])} votantes nuevos</b>. Fue un fenómeno casi universal: la participación subió en '
 f'<b>{P["subieron"]} de los {P["subieron"]+P["cayeron"]} municipios</b> con datos —solo cayó en uno—.')
img(f'{OUT}/graficos/g_participacion.png',150*mm,'A dónde fue el crecimiento de cada candidato, según quién ganaba la 1ª vuelta en cada zona.')
h2('4.1 · La movilización reforzó al líder local')
zi,zd=P['zona_izq'],P['zona_der']
body(f'El hallazgo central de la participación: <b>los nuevos votantes reforzaron al que ya iba ganando '
 f'en cada territorio</b>. En las zonas donde Cepeda ganó la 1ª vuelta, el crecimiento de la participación '
 f'lo favoreció (creció {fs(zi["dcep"])} contra {fs(zi["dabe"])} de Abelardo). En las zonas donde Abelardo '
 f'ganó la 1ª vuelta, pasó lo simétrico: creció {fs(zd["dabe"])} contra {fs(zd["dcep"])} de Cepeda. La ola '
 'no fue ideológica; fue de refuerzo. Por eso el promedio nacional engaña: a Cepeda lo ayudó más en total, '
 'pero a Abelardo lo blindó justo donde necesitaba.')
h2('4.2 · Dónde subió más y dónde cayó')
ts=P['top_sube'][:6]; tc=P['top_cae'][:6]
hh=[Paragraph('Municipio',hc),Paragraph('Depto',hc),Paragraph('Δ part.',hcR)]
dS=[hh]+[[Paragraph(p['mun'][:22],cell),Paragraph(p['dep'],cell),col(f'+{p["dpp"]:.1f}',INK,b=False)] for p in ts]
dC=[hh]+[[Paragraph(p['mun'][:22],cell),Paragraph(p['dep'],cell),col(f'{p["dpp"]:+.1f}',MUT,b=False)] for p in tc]
side=Table([[mktable(dS,[36*mm,24*mm,18*mm]),mktable(dC,[36*mm,24*mm,18*mm])]],colWidths=[84*mm,84*mm])
side.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(0,0),6)]))
story.append(Paragraph('Mayor alza de participación (izq.) y los pocos casos de menor alza/caída (der.), en puntos porcentuales',S(name='cp2',fontName=FI,fontSize=8.4,textColor=MUT,leading=11)))
story.append(Spacer(1,3)); story.append(side); story.append(Spacer(1,5))
note('Curiosidad: entre los municipios donde MENOS subió la participación están Envigado y Sabaneta '
 '(bastiones acomodados de Abelardo en el Valle de Aburrá), que ya partían de participación muy alta y '
 'tenían poco margen para crecer.')
h2('4.3 · Participación por departamento')
ANCLAS=json.load(open('tools/segunda-vuelta-prec/anclas-2v.json'))
censo_dep={cod:v['censo'] for cod,v in ANCLAS['dep'].items()}; nom_dep={cod:v['n'] for cod,v in ANCLAS['dep'].items()}
PARTd=collections.defaultdict(lambda:[0,0])
for r in MUNROWS:
    c=r['cod'][:2]; PARTd[c][0]+=I(r,'votant1v'); PARTd[c][1]+=I(r,'votant2v')
prows=[]
for c,(v1,v2) in PARTd.items():
    ce=censo_dep.get(c,0)
    if ce<=0 or c=='88': continue
    p1=100*v1/ce; p2=100*v2/ce; prows.append((nom_dep.get(c,c),p1,p2,p2-p1))
prows.sort(key=lambda r:-r[3])
half=(len(prows)+1)//2
def ptab(rs):
    d=[[Paragraph('Depto',hc),Paragraph('1V',hcR),Paragraph('2V',hcR),Paragraph('Δ pp',hcR)]]
    for nm,p1,p2,dp in rs:
        d.append([Paragraph(nm,cell),Paragraph(f'{p1:.0f}%',cellR),Paragraph(f'{p2:.0f}%',cellR),col(f'+{dp:.1f}',INK,b=False)])
    return mktable(d,[40*mm,16*mm,16*mm,18*mm],pad=2.2)
side=Table([[ptab(prows[:half]),ptab(prows[half:])]],colWidths=[92*mm,92*mm])
side.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(0,0),8)]))
body('Ordenados por cuánto subió la participación. El alza fue notablemente homogénea —entre 5 y 8 '
 'puntos en casi todos los departamentos—, lo que confirma el carácter de marea nacional antes que de '
 'movilización dirigida.')
story.append(side)

print('parte 4 ok; story items:',len(story))

# ════════════════════ PARTE 5: BARRIOS ════════════════════
cap('El voto barrio a barrio en las ciudades principales','Parte 5')
body('Bajar del municipio al barrio revela la textura fina de la elección. Cada puesto de votación se '
 'asignó por geolocalización a su barrio (polígonos catastrales y oficiales). Para cada ciudad se muestran '
 'dos mapas comparables lado a lado: el <b>resultado de la primera vuelta</b> (izquierda) y el de la '
 '<b>segunda vuelta</b> (derecha), por barrio. Así se ve de un vistazo qué barrios cambiaron de manos y '
 'cuáles se consolidaron. Los barrios sin puesto propio se rellenan en tono claro con la tendencia del '
 'vecino más cercano y no entran a los conteos.')
ORDER=['medellin','bogota','cali','barranquilla','cartagena','bucaramanga','cucuta','pereira',
       'manizales','santamarta','soledad','popayan','buenaventura','quibdo']
NICEDESC={
 'buenaventura':'El principal puerto del Pacífico: bastión absoluto de Cepeda, que gana todos los barrios en una ciudad de mayoría afro y altísima abstención histórica.',
 'quibdo':'Capital del Chocó: Cepeda gana los 22 barrios con dato. El Pacífico afro es el territorio más fiel del Pacto en todo el país.',
 'manizales':'Eje cafetero competido: Abelardo gana la ciudad, con Cepeda sosteniendo barrios del centro y la comuna San José.',
 'santamarta':'Cepeda domina la capital del Magdalena; Abelardo queda reducido a enclaves del norte turístico y residencial.',
 'soledad':'El gran cinturón popular del área metropolitana de Barranquilla: Cepeda gana todos los barrios, Abelardo ninguno.',
 'popayan':'Capital del Cauca, bastión histórico de la izquierda: Cepeda gana casi todos los barrios de la ciudad.',
 'medellin':'Abelardo arrasa el Valle de Aburrá: gana 139 de los 165 barrios con dato. Cepeda solo resiste en la ladera nororiental popular (Popular, Santo Domingo, Manrique).',
 'bogota':'La capital se parte en dos: Cepeda domina el sur y el occidente populares; Abelardo, el nororiente acomodado (Usaquén, Chapinero, Suba). El mapa apenas cambia entre vueltas.',
 'cali':'Cepeda domina con holgura, sobre todo el oriente popular (Distrito de Aguablanca). Abelardo se limita al sur y a los barrios de estrato alto.',
 'barranquilla':'Reparto más equilibrado: Cepeda gana la mayoría de barrios, Abelardo resiste en el norte de la ciudad.',
 'cartagena':'Bastión claro de Cepeda: gana casi todos los barrios, con Abelardo reducido a unos pocos enclaves. Uno de los mejores resultados relativos del Pacto en una capital.',
 'bucaramanga':'Espejo de Medellín: Abelardo arrasa, Cepeda apenas gana un puñado de barrios. El área metropolitana santandereana es territorio firme de la derecha.',
 'cucuta':'El resultado más extremo en el interior: Abelardo gana los 59 barrios con dato. Frontera, economía informal y trasvase de derecha se combinan en un dominio total.',
 'pereira':'Eje cafetero competido con ventaja de Abelardo: gana la mayoría de barrios pero Cepeda sostiene varios sectores; la ciudad quedó cerca del empate.',
}
for slug in ORDER:
    c=BR[slug]
    story.append(PageBreak())
    p=Paragraph(f'5 · {c["name"]}',st_h2); p._tochead=('2',f'Barrios — {c["name"]}'); story.append(p)
    win='Abelardo' if c['m2']>0 else 'Cepeda'; wcol=BLUE if c['m2']>0 else RED
    body(f'En 2ª vuelta {c["name"]} quedó <b>{f(c["cep2"])}</b> Cepeda contra <b>{f(c["abe2"])}</b> Abelardo '
     f'(margen {"Abelardo" if c["m2"]>0 else "Cepeda"} {abs(c["m2"]):.1f} pp). De los {c["n_barrios"]} '
     f'barrios con dato directo, <b>Cepeda gana {c["cepeda_gana"]} y Abelardo {c["abelardo_gana"]}</b>. '
     f'{NICEDESC[slug]}')
    # dos mapas lado a lado
    from PIL import Image as PImage
    g1=f'{OUT}/mapas/{slug}_v1.png'; g2=f'{OUT}/mapas/{slug}_v2.png'
    def imgcell(path,w):
        iw,ih=PImage.open(path).size; return Image(path,width=w,height=w*ih/iw)
    mw=87*mm
    mp=Table([[imgcell(g1,mw),imgcell(g2,mw)]],colWidths=[mw+2*mm,mw+2*mm])
    mp.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]))
    story.append(mp)
    note(' Izquierda: ganador por barrio en la 1ª vuelta. Derecha: en la 2ª vuelta. Azul = Abelardo, rojo = '
         'Cepeda; intensidad según el margen; tono claro = barrio sin puesto propio (relleno con el vecino más cercano).')
    story.append(Spacer(1,5))
    story.append(Paragraph('Barrios que más se movieron entre la 1ª y la 2ª vuelta (puntos de cambio en el margen)',
        S(name='cpsw',fontName=FI,fontSize=8.4,textColor=MUT,leading=11)))
    story.append(Spacer(1,2))
    hh=[Paragraph('Más hacia Abelardo',hc),Paragraph('pp',hcR),Paragraph('Más hacia Cepeda',hc),Paragraph('pp',hcR)]
    rows=[hh]
    for i in range(5):
        a=c['top_swing_abe'][i] if i<len(c['top_swing_abe']) else {'b':'','sw':0}
        cc=c['top_swing_cep'][i] if i<len(c['top_swing_cep']) else {'b':'','sw':0}
        rows.append([Paragraph(a['b'][:24].title(),cell),col(f'{a["sw"]:+.0f}',BLUE,b=False),
                     Paragraph(cc['b'][:24].title(),cell),col(f'{cc["sw"]:+.0f}',RED,b=False)])
    story.append(mktable(rows,[52*mm,14*mm,52*mm,14*mm]))
    # página de comunas/localidades
    coms=COM.get(c['name'],[])
    if len(coms)>=6:
        story.append(PageBreak())
        unidad='localidad' if slug=='bogota' else 'comuna'
        plural='localidades' if slug=='bogota' else 'comunas'
        p=Paragraph(f'{c["name"]} · por {unidad}',st_h2); p._tochead=('2',f'{c["name"]} · {plural}'); story.append(p)
        cw=sum(1 for x in coms if x['gana']=='C'); aw=sum(1 for x in coms if x['gana']=='A')
        mas_cep=min(coms,key=lambda x:x['m2']); mas_abe=max(coms,key=lambda x:x['m2'])
        ctxt=(f'el bastión más fuerte de Cepeda es <b>{mas_cep["comuna"]}</b> ({abs(mas_cep["m2"]):.0f} pp a su favor)'
              if mas_cep['m2']<0 else f'su mejor resultado relativo es <b>{mas_cep["comuna"]}</b>')
        atxt=(f'el de Abelardo, <b>{mas_abe["comuna"]}</b> ({abs(mas_abe["m2"]):.0f} pp)'
              if mas_abe['m2']>0 else f'y Abelardo no logra imponerse con claridad en ninguna')
        body(f'Desagregado por {unidad}, {c["name"]} reparte sus {len(coms)} {plural} así: Cepeda gana '
         f'{cw}, Abelardo {aw}. En detalle, {ctxt}; {atxt}. La columna de swing muestra hacia dónde se '
         f'movió cada {unidad} frente a la 1ª vuelta.')
        dd=[[Paragraph(unidad.capitalize(),hc),Paragraph('Cepeda',hcR),Paragraph('Abelardo',hcR),Paragraph('Margen',hcR),Paragraph('Swing',hcR),Paragraph('Gana',hcR)]]
        for x in coms[:26]:
            gc=BLUE if x['gana']=='A' else RED
            dd.append([Paragraph(x['comuna'][:30],cell),Paragraph(f(x['cep2']),cellR),Paragraph(f(x['abe2']),cellR),
                       col(f'{x["m2"]:+.0f}',gc),col(f'{x["swing"]:+.0f}',BLUE if x['swing']>0 else RED,b=False),
                       col('Abe' if x['gana']=='A' else 'Cep',gc)])
        story.append(mktable(dd,[54*mm,26*mm,26*mm,22*mm,20*mm,20*mm],pad=2.3))

print('parte 5 ok; story items:',len(story))

# ════════════════════ PARTE 6: ATÍPICOS ════════════════════
cap('Diez municipios que se salieron del guion','Parte 6')
body('El patrón nacional de trasvase explica casi todo, pero algunos municipios se comportaron de forma '
 'anómala: rindieron muy por encima de lo que su composición de 1ª vuelta predecía, tuvieron saltos de '
 'participación extremos o —lo más raro en una segunda vuelta con más votantes— vieron <b>caer</b> a un '
 'candidato en votos absolutos. Separamos los cinco casos más sorprendentes a favor de cada finalista, '
 'medidos por el residual frente al patrón nacional de trasvase.')
pro_abe=AN['extranos']['pro_abe'][:5]
pro_cep=AN['extranos']['pro_cep'][:5]
def extbl(rows,color,lado):
    d=[[Paragraph('Municipio',hc),Paragraph('Depto',hc),Paragraph('Particip.',hcR),Paragraph('Votos de más',hcR)]]
    for r in rows:
        resid=r['resid_abe'] if lado=='A' else r['resid_cep']
        flag=''
        if r['cep_cayo']: flag=' (Cep. cayó)'
        elif r['abe_cayo']: flag=' (Abe. cayó)'
        d.append([Paragraph(r['mun'].title()+flag,cell),Paragraph(r['dep'],cell),
                  col(f'{r["p1"]}-{r["p2"]}',MUT,b=False),col('+'+f(resid),color)])
    return mktable(d,[46*mm,30*mm,24*mm,26*mm])
h2('6.1 · Sorpresas a favor de Abelardo')
body('Municipios donde Abelardo sacó más votos de los que su composición de 1ª vuelta hacía esperar — '
 'sobre-rendimiento de la derecha, casi todos en zonas rurales de Antioquia y Boyacá donde la maquinaria '
 'local apretó más fuerte de lo previsto en la segunda vuelta.')
story.append(extbl(pro_abe,BLUE,'A'))
h2('6.2 · Sorpresas a favor de Cepeda')
body('Municipios donde Cepeda sobre-rindió frente a lo esperado: en buena parte zonas de antigua '
 'influencia del conflicto y del sur del país, donde la movilización del Pacto en segunda vuelta superó '
 'lo que anticipaba su voto de primera.')
story.append(extbl(pro_cep,RED,'C'))
note('"Votos de más" = votos que el candidato obtuvo por encima de lo que predice el patrón nacional de '
 'trasvase para ese municipio (residual del modelo). La participación se muestra como tasa de 1ª a 2ª '
 'vuelta. "Cayó" = el candidato obtuvo menos votos absolutos que en 1ª vuelta, algo infrecuente cuando la '
 'participación sube en todo el país.')

# ════════════════════ PARTE 7: VEREDICTO ════════════════════
cap('Veredicto: qué pesó para que ganara Abelardo','Parte 7')
body(f'Abelardo De La Espriella ganó por {f(MAR2)} votos —0,98 puntos— y la pregunta de fondo es qué pesó '
 'más. La evidencia territorial y de trasvases permite jerarquizar las causas, de la más decisiva a la '
 'menos:')
for i,t in enumerate([
 '<b>La herencia de la primera vuelta.</b> Abelardo no construyó su victoria en la segunda vuelta: la heredó. Partía 666.000 votos arriba, fruto de una derecha que se consolidó antes y mejor. El balotaje solo tenía que no dilapidar esa ventaja.',
 '<b>Antioquia y el cinturón de derecha.</b> Antioquia, Norte de Santander y Santander le entregaron +1,87 millones de margen. Es una base geográfica tan densa que ninguna estrategia nacional de Cepeda podía contrarrestarla desde afuera.',
 '<b>La marea de participación sin dueño.</b> El arma que debía ser de Cepeda —movilizar la abstención— resultó ser de todos. La participación subió parejo en el país y reforzó al líder local de cada zona, blindando a Abelardo en su territorio.',
 '<b>El techo de la consolidación de derecha.</b> El bloque de Paloma fue 81% a Abelardo. Sumado a su base, eso construyó un piso que el centro capturado por Cepeda (también 81%) no alcanzó a superar, porque la derecha partía de más arriba.',
]):
    bullet(t)
body('La conclusión incómoda para el Pacto es que <b>esta elección estaba estructuralmente decidida desde '
 'la noche del 31 de mayo</b>. Cepeda corrió una segunda vuelta casi perfecta en ejecución —persuadió el '
 'centro, recuperó sus zonas, movilizó la abstención, creció más que su rival— y recortó casi toda la '
 'distancia. Pero "casi toda" no es toda. Abelardo ganó porque la aritmética de partida y la geografía del '
 'país lo favorecían, y porque la herramienta más poderosa de la segunda vuelta, la participación, no '
 'tenía bando.')
h2('7.1 · Las dos Colombias')
body('El mapa de esta elección dibuja un país partido en dos no por clase sino por <b>geografía y '
 'cultura política</b>. De un lado, el <b>interior andino-paisa</b>: Antioquia, los Santanderes, el eje '
 'cafetero, los llanos petroleros y la diáspora del norte —el país de Abelardo—. Del otro, las '
 '<b>periferias costeras y del sur</b>: el Caribe, el Pacífico, el Cauca y Nariño, más el Bogotá popular '
 'del sur y el occidente —el país de Cepeda—. Es un clivaje viejo en la política colombiana, pero la '
 'segunda vuelta lo dibujó con una nitidez pocas veces vista: en muchas capitales costeras Cepeda superó '
 'el 60%, mientras en el Valle de Aburrá Abelardo hizo lo propio.')
body('Dentro de las ciudades, el clivaje se reproduce a escala de barrio. El análisis territorial de la '
 'Parte 5 muestra el mismo patrón una y otra vez: <b>los barrios populares y periféricos votan Cepeda; los '
 'barrios de estrato alto y las zonas residenciales consolidadas votan Abelardo</b>. Bogotá es el caso de '
 'libro —sur contra nororiente—, pero se repite en Cali (oriente vs. sur), Barranquilla, Cartagena y '
 'hasta en la propia Medellín, donde los pocos barrios que Cepeda gana son los de la ladera nororiental.')
h2('7.2 · Lo que queda para 2027')
body('Para el Pacto, la lectura no es de derrota sino de techo. Movilizó como nunca, capturó el centro y '
 'recuperó su voto histórico, y aun así perdió por menos de un punto. El problema es estructural y '
 'geográfico: mientras Antioquia y el cinturón de derecha mantengan esa densidad y esa disciplina de voto, '
 'cualquier candidato de izquierda parte cuesta arriba. La tarea de mediano plazo —de cara a las '
 'elecciones regionales de 2027 y más allá— es <b>disputar el interior andino</b>, no solo administrar las '
 'periferias. Para la derecha, el mensaje es inverso: su fortaleza está concentrada, y una elección que se '
 'gane o pierda fuera de Antioquia la pondría en aprietos.')
h2('7.3 · La sombra de 2022')
body('Conviene cerrar con una comparación. En 2022, Gustavo Petro entró a la segunda vuelta y la ganó '
 'remontando: movió cerca de 2,7 millones de votos entre la primera y la segunda, convenciendo al centro '
 'y movilizando abstención hasta superar a Rodolfo Hernández. Esa hazaña es la que el Pacto intentó '
 'repetir con Cepeda — y, en términos de ejecución, casi lo logra: creció casi 3 millones de votos, más '
 'incluso que entonces.')
body('La diferencia decisiva no estuvo en el esfuerzo sino en el rival y en el punto de partida. En 2022, '
 'la derecha llegó <b>dividida y desorganizada</b> a la segunda vuelta, con un candidato outsider sin '
 'estructura territorial. En 2026 llegó <b>consolidada desde la primera vuelta</b>, con Abelardo ya '
 'liderando y una maquinaria antioqueña intacta. Cepeda corrió la misma carrera que Petro, con más '
 'velocidad incluso, pero la pista estaba inclinada en su contra. La lección para 2030 es clara: la '
 'segunda vuelta se gana, sobre todo, en la primera.')
note('Este es un análisis de preconteo. El escrutinio definitivo puede ajustar marginalmente las cifras, '
 'pero no la magnitud ni la dirección de los hallazgos. Las estimaciones de trasvase son ecológicas: '
 'describen el movimiento agregado del voto, no decisiones individuales.')

# ════════════════════ ANEXO: DEPARTAMENTAL ════════════════════
cap('Anexo · Panorama departamental completo','Anexo')
body('Los 33 departamentos ordenados por margen neto de Abelardo en 2ª vuelta, con el movimiento frente a '
 'la 1ª vuelta.')
d=[[Paragraph('Departamento',hc),Paragraph('Cepeda 2V',hcR),Paragraph('Abelardo 2V',hcR),Paragraph('Margen 2V',hcR),Paragraph('Δ vs 1V',hcR)]]
for dep,v in sorted(DEP.items(),key=lambda kv:-(kv[1]['a2']-kv[1]['c2'])):
    m2=v['a2']-v['c2']; m1=v['a1']-v['c1']
    d.append([Paragraph(dep,cell),Paragraph(f(v['c2']),cellR),Paragraph(f(v['a2']),cellR),
              col(fs(m2),BLUE if m2>0 else RED),col(fs(m2-m1),BLUE if (m2-m1)>0 else RED)])
story.append(mktable(d,[40*mm,28*mm,28*mm,30*mm,26*mm],pad=2.2))

# ── Anexo: 40 municipios mas grandes ──
cap('Anexo · Los 100 municipios más grandes','Anexo')
body('Ordenados por tamaño electoral en 2ª vuelta, con el resultado de cada finalista y el ganador.')
big40=sorted(MUNROWS,key=lambda r:-(I(r,'cep2v')+I(r,'abe2v')))[:100]
d=[[Paragraph('#',hc),Paragraph('Municipio',hc),Paragraph('Depto',hc),Paragraph('Cepeda',hcR),Paragraph('Abelardo',hcR),Paragraph('Margen',hcR),Paragraph('Gana',hc)]]
for i,r in enumerate(big40,1):
    m=I(r,'margen2v'); g='Abelardo' if m>0 else 'Cepeda'
    d.append([Paragraph(str(i),cell),Paragraph(r['municipio'].title(),cell),Paragraph(r['depto'],cell),
              Paragraph(f(I(r,'cep2v')),cellR),Paragraph(f(I(r,'abe2v')),cellR),col(fs(m),BLUE if m>0 else RED),
              col(g,BLUE if m>0 else RED,r=False)])
story.append(mktable(d,[8*mm,40*mm,28*mm,24*mm,24*mm,24*mm,22*mm],pad=2.0))

# ── Anexo: comparativo 1V -> 2V ──
cap('Anexo · El movimiento entre vueltas','Anexo')
body('Los 45 municipios más grandes, con el margen de Abelardo en cada vuelta y el swing (positivo = se '
 'movió hacia Abelardo; negativo = hacia Cepeda). Confirma el patrón general: las grandes ciudades se '
 'movieron hacia Cepeda; la fortaleza paisa-santandereana, hacia Abelardo.')
big45=sorted(MUNROWS,key=lambda r:-(I(r,'cep2v')+I(r,'abe2v')))[:45]
d=[[Paragraph('Municipio',hc),Paragraph('Depto',hc),Paragraph('Margen 1V',hcR),Paragraph('Margen 2V',hcR),Paragraph('Swing',hcR)]]
for r in big45:
    m1=I(r,'margen1v'); m2=I(r,'margen2v'); sw=I(r,'delta_margen')
    d.append([Paragraph(r['municipio'].title(),cell),Paragraph(r['depto'],cell),
              col(fs(m1),BLUE if m1>0 else RED,b=False),col(fs(m2),BLUE if m2>0 else RED,b=False),
              col(fs(sw),BLUE if sw>0 else RED)])
story.append(mktable(d,[40*mm,28*mm,28*mm,28*mm,28*mm],pad=2.1))

# ── Anexo: ciudades de un vistazo ──
cap('Anexo · Las ciudades, de un vistazo','Anexo')
body('Las 14 ciudades analizadas barrio a barrio, con el margen de cada vuelta y cuántos barrios ganó '
 'cada finalista en primera y en segunda. El patrón se repite: las ciudades costeras, del Pacífico y del '
 'sur son de Cepeda; el interior paisa-santandereano, de Abelardo; y entre vueltas el mapa apenas se mueve.')
d=[[Paragraph('Ciudad',hc),Paragraph('Margen 1V',hcR),Paragraph('Margen 2V',hcR),
    Paragraph('Barrios 1V (Cep/Abe)',hcR),Paragraph('Barrios 2V (Cep/Abe)',hcR)]]
for slug in ORDER:
    c=BR[slug]
    g1=BLUE if c['m1']>0 else RED; g2=BLUE if c['m2']>0 else RED
    d.append([Paragraph(c['name'],cellB),col(f'{c["m1"]:+.1f}',g1,b=False),col(f'{c["m2"]:+.1f}',g2),
              Paragraph(f"{c.get('cepeda_gana1','—')} / {c.get('abelardo_gana1','—')}",cellR),
              Paragraph(f"{c['cepeda_gana']} / {c['abelardo_gana']}",cellR)])
story.append(mktable(d,[36*mm,26*mm,26*mm,40*mm,40*mm],pad=2.6))
note('Margen en puntos: positivo = Abelardo, negativo = Cepeda. "Barrios" cuenta cuántos ganó cada uno '
 'sobre los barrios con dato directo. La estabilidad del conteo entre vueltas confirma que la 2ª vuelta '
 'consolidó el mapa de la 1ª antes que redibujarlo.')

# ── Anexo: municipios bisagra ──
cap('Anexo · Los municipios bisagra','Anexo')
body('Los municipios grandes más competidos: donde el margen de 2ª vuelta fue menor a 4 puntos '
 'porcentuales. Son el terreno fino donde la elección estuvo de verdad en disputa — y, como muestra la '
 'lista, son relativamente pocos: la mayor parte del país votó con claridad por uno u otro lado.')
bis=[]
for r in MUNROWS:
    base=I(r,'cep2v')+I(r,'abe2v')
    if base<15000 or r['depto']=='Exterior': continue
    mp=100*I(r,'margen2v')/base
    if abs(mp)<4: bis.append((r,mp,base))
bis.sort(key=lambda x:-x[2])
d=[[Paragraph('Municipio',hc),Paragraph('Depto',hc),Paragraph('Cepeda',hcR),Paragraph('Abelardo',hcR),Paragraph('Margen %',hcR),Paragraph('Gana',hcR)]]
for r,mp,base in bis[:30]:
    g=BLUE if mp>0 else RED
    d.append([Paragraph(r['municipio'].title(),cell),Paragraph(r['depto'],cell),Paragraph(f(I(r,'cep2v')),cellR),
              Paragraph(f(I(r,'abe2v')),cellR),col(f'{mp:+.1f}',g),col('Abe' if mp>0 else 'Cep',g)])
story.append(mktable(d,[42*mm,28*mm,26*mm,26*mm,22*mm,18*mm],pad=2.3))

# ── Anexo: crecimiento del voto por municipio ──
cap('Anexo · El crecimiento del voto entre vueltas','Anexo')
body('Los 40 municipios donde más creció la cantidad de votantes de la primera a la segunda vuelta, en '
 'números absolutos. Encabezan las grandes ciudades —por puro tamaño—, pero el crecimiento porcentual fue '
 'parejo en casi todo el país: la marea de participación, como se documenta en la Parte 4, no fue selectiva.')
gv=sorted(MUNROWS,key=lambda r:-(I(r,'votant2v')-I(r,'votant1v')))
d=[[Paragraph('Municipio',hc),Paragraph('Depto',hc),Paragraph('Votantes 1V',hcR),Paragraph('Votantes 2V',hcR),Paragraph('Crecimiento',hcR)]]
for r in gv[:40]:
    dv=I(r,'votant2v')-I(r,'votant1v')
    if dv<=0: continue
    d.append([Paragraph(r['municipio'].title(),cell),Paragraph(r['depto'],cell),Paragraph(f(I(r,'votant1v')),cellR),
              Paragraph(f(I(r,'votant2v')),cellR),col('+'+f(dv),OX)])
story.append(mktable(d,[40*mm,28*mm,28*mm,28*mm,28*mm],pad=2.2))

# ── Anexo metodologico ──
cap('Anexo · Nota metodológica','Anexo')
h2('Fuentes')
body('<b>Segunda vuelta:</b> preconteo de la Registraduría al 100% de las mesas (122.017 de 122.020), '
 'a nivel de mesa, con identificación completa de departamento, municipio, zona y puesto. '
 '<b>Primera vuelta:</b> conteo interno por mesa (121.863 mesas), que coincide con el resultado oficial '
 'dentro de ~0,08%. <b>Georreferencia:</b> coordenadas y barrio de cada puesto desde el archivo oficial '
 'de puestos de votación. <b>Polígonos de barrio:</b> capas catastrales y oficiales de cada ciudad.')
h2('Cruce 1ª–2ª vuelta')
body('Los puestos de votación son la unidad territorial estable entre elecciones (las mesas se reasignan). '
 'Se unificó cada puesto de 2ª vuelta con su equivalente de 1ª por código de 9 dígitos, logrando una '
 'cobertura del 99,1% del voto nacional. El restante corresponde al voto del exterior y a puestos '
 'especiales (cárceles, puesto-censo), que se excluyen del análisis territorial.')
h2('Estimación de trasvases')
body('Inferencia ecológica sobre los 1.189 municipios: regresión restringida (coeficientes en [0,1], suma '
 'de destinos ≤ 1) de los incrementos de cada finalista sobre los votos de cada fuente de 1ª vuelta y el '
 'cambio de participación. Se estima por bloque para evitar el sesgo de colinealidad entre fuentes que '
 'comparten territorio. Intervalos por bootstrap de 400 remuestreos. R² conjunto = 0,99. '
 '<b>Es un método agregado:</b> describe el movimiento del voto, no decisiones individuales (falacia '
 'ecológica). Las cifras por candidato son atribuciones de la tasa de su bloque.')
h2('Barrios')
body('Cada puesto se asigna a su barrio por punto-en-polígono; los barrios sin puesto propio heredan, '
 'solo para efectos visuales, la tendencia del vecino más cercano (marcado en tono claro y excluido de '
 'los totales). El "swing" es la diferencia del margen porcentual del barrio entre la 2ª y la 1ª vuelta.')
h2('Advertencia')
body('Todas las cifras son de preconteo y no constituyen resultado oficial. El escrutinio definitivo puede '
 'introducir ajustes marginales que no alteran la magnitud ni la dirección de los hallazgos de este informe.')

# ── Anexo: cómo leer este informe ──
cap('Anexo · Cómo leer este informe','Anexo')
h2('Preguntas frecuentes')
body('<b>¿Por qué el "swing" hacia Cepeda no significa que Cepeda gane?</b> El swing mide cuánto se movió '
 'un territorio entre vueltas, no quién gana. Un barrio donde Abelardo tenía 80% y bajó a 75% se mueve '
 'hacia Cepeda (swing rojo) pero lo sigue ganando Abelardo con holgura. Por eso este informe muestra el '
 'resultado de cada vuelta por separado, y reserva el swing para las tablas de detalle.')
body('<b>¿Por qué la suma de los votos por barrio no cuadra exacto con el total de la ciudad?</b> Los '
 'mapas por barrio cubren los puestos urbanos georreferenciados (entre el 95% y el 100% del voto de cada '
 'ciudad). Una fracción mínima de puestos sin coordenada válida no entra al mapa, pero sí a los totales '
 'nacionales y departamentales.')
body('<b>¿Qué tan confiables son las estimaciones de trasvase?</b> Son estimaciones ecológicas con un '
 'ajuste muy alto (R² = 0,99) e intervalos de confianza calculados por bootstrap. Describen el movimiento '
 'agregado del voto con solidez a nivel de bloque; la atribución a candidatos individuales dentro de un '
 'mismo bloque es indicativa, no exacta, y así se señala en el texto.')
body('<b>¿Cambiará algo con el escrutinio oficial?</b> Es muy improbable. El preconteo cerró con el 100% '
 'de las mesas y coincide con el cómputo oficial dentro de fracciones de punto. Un margen de 250.000 votos '
 'no se revierte en el escrutinio salvo irregularidad mayúscula, que nada en los datos sugiere.')
h2('Glosario')
bullet('<b>Margen:</b> diferencia entre los votos de Abelardo y los de Cepeda. Positivo = ventaja de Abelardo.')
bullet('<b>Cara a cara:</b> comparación directa entre los dos finalistas, ya en 1ª vuelta (cuando competían con otros 11), ya en 2ª.')
bullet('<b>Trasvase:</b> el paso del voto de un candidato eliminado hacia uno de los dos finalistas en la 2ª vuelta.')
bullet('<b>Swing:</b> cambio del margen de un territorio entre la 1ª y la 2ª vuelta, en puntos porcentuales.')
bullet('<b>Techo (de recuperación):</b> el voto que la izquierda alcanzó en su mejor noche reciente (Petro, 2ª vuelta 2022) y que marca su potencial máximo en cada territorio.')

print('todas las partes ok; story items:',len(story))

# ───────── doc template con TOC + footer ─────────
class Doc(BaseDocTemplate):
    def afterFlowable(self,fl):
        if hasattr(fl,'_tochead'):
            lvl,txt=fl._tochead
            self.notify('TOCEntry',(0 if lvl=='1' else 1,txt,self.page))
def footer(canvas,doc):
    # marca de agua confidencial, diagonal (45°) y en dos líneas, tenue, abarcando la página
    canvas.saveState()
    canvas.setFont(FBd,52); canvas.setFillColor(OX)
    try: canvas.setFillAlpha(0.08)
    except Exception: pass
    canvas.translate(A4[0]/2,A4[1]/2); canvas.rotate(45)
    canvas.drawCentredString(0,80,'DOCUMENTO')
    canvas.drawCentredString(0,2,'CONFIDENCIAL')
    canvas.drawCentredString(0,-76,'RICARDORUIZ.CO')
    canvas.restoreState()
    canvas.saveState(); canvas.setFont(F,7.3); canvas.setFillColor(MUT)
    canvas.drawString(20*mm,11*mm,'ricardoruiz.co · Anatomía de la 2ª vuelta presidencial 2026 · CONFIDENCIAL · no difundir')
    canvas.drawRightString(190*mm,11*mm,f'{doc.page}')
    canvas.setStrokeColor(LINE); canvas.setLineWidth(0.4); canvas.line(20*mm,14*mm,190*mm,14*mm)
    canvas.restoreState()
frame=Frame(20*mm,16*mm,170*mm,A4[1]-32*mm,id='n',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
from reportlab.lib.pdfencrypt import StandardEncryption
enc=StandardEncryption('',ownerPassword='rr-conf-2v-2026',canPrint=1,canModify=0,canCopy=0,canAnnotate=0)
doc=Doc(PDF,pagesize=A4,title='Anatomía de la 2ª vuelta presidencial 2026',author='ricardoruiz.co',encrypt=enc)
doc.addPageTemplates([PageTemplate(id='main',frames=[frame],onPage=footer)])
doc.multiBuild(story)
print('\n== PDF =>',PDF,'·',os.path.getsize(PDF)//1024,'KB ==')
