#!/usr/bin/env python3
# Genera el PDF de analisis "Donde se definio la 2V 2026" para compartir.
# Lee municipios_2v_vs_1v.csv (recomputa agregados para que texto y tablas
# siempre cuadren) y arma un documento con reportlab + Inter incrustada.
import csv, os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, HRFlowable, KeepTogether, PageBreak, Image)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

CSV = 'tools/segunda-vuelta-prec/municipios_2v_vs_1v.csv'
OUT = 'Bases de datos/output_2v/Analisis_2V_2026_donde_gano_Abelardo.pdf'
LOGO = 'Bases de datos/output_abelardo_cartagena/logo_ricardoruiz.png'
HOY  = '21 de junio de 2026'

# ---- fuentes ----
FB = 'tools/pacto-1v-2026/fonts/Inter-{}.ttf'
try:
    pdfmetrics.registerFont(TTFont('Inter', FB.format('Regular')))
    pdfmetrics.registerFont(TTFont('Inter-B', FB.format('Bold')))
    pdfmetrics.registerFont(TTFont('Inter-I', FB.format('Italic')))
    F, FBd, FI = 'Inter', 'Inter-B', 'Inter-I'
except Exception:
    F, FBd, FI = 'Helvetica', 'Helvetica-Bold', 'Helvetica-Oblique'

OX   = HexColor('#8a1e16')   # oxblood (acento del proyecto)
INK  = HexColor('#1a1510')
MUT  = HexColor('#6b6258')
CREAM= HexColor('#f4f0e7')
LINE = HexColor('#d8d0c4')
BLUE = HexColor('#1f47cc')   # Abelardo / derecha
RED  = HexColor('#c0392b')   # Cepeda / izquierda

def f(n):  return f'{int(round(n)):,}'.replace(',', '.')
def fs(n): return f'{int(round(n)):+,}'.replace(',', '.')

# ---- datos ----
rows = list(csv.DictReader(open(CSV, encoding='utf-8-sig')))
I = lambda r, k: int(r[k])
for r in rows:
    r['base2'] = I(r, 'cep2v') + I(r, 'abe2v')

cep1 = sum(I(r,'cep1v') for r in rows); abe1 = sum(I(r,'abe1v') for r in rows)
cep2 = sum(I(r,'cep2v') for r in rows); abe2 = sum(I(r,'abe2v') for r in rows)
mar1, mar2 = abe1-cep1, abe2-cep2
pp2 = 100*mar2/(abe2+cep2)
vot1 = sum(I(r,'votant1v') for r in rows); vot2 = sum(I(r,'votant2v') for r in rows)
# bloque esperado (constantes verificadas por analisis_2v_vs_1v.py)
CEPX, ABEX = 10_414_776, 11_970_563
exp_share = 100*ABEX/(ABEX+CEPX)

ant   = [r for r in rows if r['depto']=='Antioquia']
m_ant = sum(I(r,'margen2v') for r in ant)
ABU   = {'MEDELLIN','BELLO','ITAGUI','ENVIGADO','SABANETA','LA ESTRELLA',
         'GIRARDOTA','COPACABANA','BARBOSA','CALDAS'}
m_abu = sum(I(r,'margen2v') for r in ant if r['municipio'] in ABU)
m_med = next(I(r,'margen2v') for r in rows if r['municipio']=='MEDELLIN')
TRES  = ('Antioquia','N. de Santander','Santander')
m_tres= sum(I(r,'margen2v') for r in rows if r['depto'] in TRES)
swc = sum(I(r,'delta_margen') for r in rows if I(r,'delta_margen')<0)
swc_won = sum(I(r,'delta_margen') for r in rows
              if I(r,'delta_margen')<0 and I(r,'margen1v')<0)
big4 = {'BOGOTA. D.C.','CALI','CARTAGENA','BARRANQUILLA'}
s4 = sum(I(r,'delta_margen') for r in rows if r['municipio'] in big4)

big = [r for r in rows if r['base2'] >= 3000]
top_abe = sorted(rows, key=lambda r:-I(r,'margen2v'))[:10]
top_cep = sorted(rows, key=lambda r: I(r,'margen2v'))[:10]
mov_abe = sorted(big, key=lambda r:-I(r,'delta_margen'))[:10]
mov_cep = sorted(big, key=lambda r: I(r,'delta_margen'))[:10]

# ---- estilos ----
def S(**k): return ParagraphStyle(k.pop('name'), **k)
st_title = S(name='t', fontName=FBd, fontSize=19, textColor=INK, leading=22)
st_sub   = S(name='s', fontName=F,   fontSize=10.5, textColor=MUT, leading=14)
st_date  = S(name='d', fontName=FBd, fontSize=8.6, textColor=INK, leading=11, alignment=TA_RIGHT)
st_h2    = S(name='h', fontName=FBd, fontSize=12.5, textColor=OX, leading=15,
             spaceBefore=13, spaceAfter=5)
st_body  = S(name='b', fontName=F, fontSize=9.7, textColor=INK, leading=14,
             alignment=TA_JUSTIFY, spaceAfter=5)
st_kick  = S(name='k', fontName=FBd, fontSize=8, textColor=OX, leading=10)
st_note  = S(name='n', fontName=F, fontSize=8.3, textColor=MUT, leading=11.5,
             alignment=TA_JUSTIFY)
cell   = S(name='c',  fontName=F,   fontSize=8.7, textColor=INK, leading=11)
cellR  = S(name='cr', fontName=F,   fontSize=8.7, textColor=INK, leading=11, alignment=TA_RIGHT)
cellB  = S(name='cb', fontName=FBd, fontSize=8.7, textColor=INK, leading=11)
cellBr = S(name='cbr',fontName=FBd, fontSize=8.7, textColor=INK, leading=11, alignment=TA_RIGHT)
hcell  = S(name='hc', fontName=FBd, fontSize=8.2, textColor=colors.white, leading=10)
hcellR = S(name='hcr',fontName=FBd, fontSize=8.2, textColor=colors.white, leading=10, alignment=TA_RIGHT)
def colored(txt, col, b=True, right=True):
    return Paragraph(txt, S(name='x', fontName=FBd if b else F, fontSize=8.7,
                            textColor=col, leading=11, alignment=TA_RIGHT if right else TA_LEFT))

def mktable(data, widths, aligns=None, zebra=True, headcolor=OX, pad=3.2):
    t = Table(data, colWidths=widths, hAlign='LEFT')
    sty = [('BACKGROUND',(0,0),(-1,0),headcolor),
           ('TOPPADDING',(0,0),(-1,-1),pad),('BOTTOMPADDING',(0,0),(-1,-1),pad),
           ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
           ('LINEBELOW',(0,0),(-1,0),0.5,OX),
           ('VALIGN',(0,0),(-1,-1),'MIDDLE')]
    if zebra:
        for i in range(1,len(data)):
            if i%2==0: sty.append(('BACKGROUND',(0,i),(-1,i),CREAM))
    sty.append(('LINEBELOW',(0,1),(-1,-1),0.3,LINE))
    t.setStyle(TableStyle(sty))
    return t

# ---- documento ----
os.makedirs(os.path.dirname(OUT), exist_ok=True)
story = []
# header: categoría (izq) + logo Ricardo.Ruiz y fecha (der, pegados al margen).
# La columna del logo mide EXACTAMENTE su ancho para que llegue al margen derecho
# (reportlab ignora hAlign de una Image dentro de una lista de flowables en celda).
_lw = 50*mm; _lh = _lw*201/2361
_logo = Image(LOGO, width=_lw, height=_lh)
hdr = Table([
    [Paragraph('ELECCIONES COLOMBIA 2026<br/>SEGUNDA VUELTA PRESIDENCIAL', st_kick), _logo],
    ['', Paragraph(HOY, st_date)],
], colWidths=[120*mm, _lw])
hdr.setStyle(TableStyle([
    ('SPAN',(0,0),(0,1)),
    ('VALIGN',(0,0),(0,0),'TOP'), ('VALIGN',(1,0),(1,1),'TOP'),
    ('ALIGN',(1,0),(1,1),'RIGHT'),
    ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
    ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
    ('TOPPADDING',(1,1),(1,1),4)]))
story.append(hdr)
story.append(Spacer(1,10))
story.append(Paragraph('¿Dónde se definió la victoria de Abelardo?', st_title))
story.append(Spacer(1,2))
story.append(Paragraph('Comparativo del preconteo de segunda vuelta (100% de mesas) frente al '
    'escrutinio de primera vuelta, municipio por municipio.', st_sub))
story.append(Spacer(1,7))
story.append(HRFlowable(width='100%', thickness=1.1, color=OX))
story.append(Spacer(1,9))

# Resumen ejecutivo (caja)
res = [
 [Paragraph('LO ESENCIAL', S(name='re', fontName=FBd, fontSize=9, textColor=OX, leading=11))],
 [Paragraph(f'<b>Antioquia es la elección.</b> Abelardo ganó por <b>{f(mar2)} votos</b> '
   f'({pp2:.2f} pp) y solo en Antioquia saca <b>{fs(m_ant)}</b> de margen neto. '
   f'Sin Antioquia, Cepeda sería presidente por <b>{f(abs(mar2-m_ant))}</b> votos.', st_body)],
 [Paragraph(f'<b>No ganó por crecer en segunda vuelta.</b> Lideró la primera por '
   f'{fs(mar1)} y ganó la segunda por apenas {fs(mar2)}: el cara a cara se movió '
   f'<b>{fs(mar2-mar1)}</b> votos <i>hacia Cepeda</i>. Abelardo ganó porque su ventaja '
   f'de primera vuelta alcanzó para aguantar el envión de Cepeda.', st_body)],
 [Paragraph(f'<b>El voto de Cepeda fue ineficiente.</b> El {100*swc_won/swc:.0f}% de su '
   f'crecimiento cayó en municipios que <i>ya ganaba</i> (Bogotá, Cali, Caribe, Pacífico): '
   f'corrió el marcador donde no cambiaba el resultado nacional.', st_body)],
]
box = Table(res, colWidths=[170*mm])
box.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),HexColor('#faf7f1')),
    ('BOX',(0,0),(-1,-1),0.8,LINE),('LEFTPADDING',(0,0),(-1,-1),9),
    ('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(0,0),7),
    ('BOTTOMPADDING',(0,-1),(-1,-1),6),('LINEBEFORE',(0,0),(0,-1),2.5,OX)]))
story.append(box)

# 1. Reconciliacion
story.append(Paragraph('1. La reconciliación nacional', st_h2))
d = [[Paragraph('Escenario',hcell), Paragraph('Cepeda',hcellR), Paragraph('Abelardo',hcellR),
      Paragraph('Margen Abelardo',hcellR)],
 [Paragraph('Primera vuelta (cara a cara, archivo interno)',cell), Paragraph(f(cep1),cellR),
  Paragraph(f(abe1),cellR), colored(fs(mar1),BLUE)],
 [Paragraph('Segunda vuelta (preconteo, 100% mesas)',cellB), Paragraph(f(cep2),cellBr),
  Paragraph(f(abe2),cellBr), colored(f'{fs(mar2)}  ({pp2:.2f} pp)',BLUE)],
 [Paragraph('Esperado por trasvase de bloques 1V',cell), Paragraph('—',cellR),
  Paragraph(f'{exp_share:.1f}%',cellR), colored(f'real {100-100*cep2/(abe2+cep2):.1f}%',MUT,b=False)]]
story.append(mktable(d,[78*mm,28*mm,28*mm,36*mm]))
story.append(Spacer(1,4))
story.append(Paragraph(f'El cara a cara se encogió de {fs(mar1)} a {fs(mar2)}: el envión de '
  f'segunda vuelta fue de Cepeda ({fs(mar2-mar1)} netos), apoyado en una participación que '
  f'subió +{f(vot2-vot1)} votos ({f(vot1)} a {f(vot2)}). Pero Abelardo quedó '
  f'{exp_share-(100-100*cep2/(abe2+cep2)):.1f} pp por debajo del trasvase mecánico de la '
  f'derecha: mucho voto de derecha de primera vuelta se quedó en casa o cruzó. '
  f'Aun así, la herencia bastó.', st_note))

# 2. Donde se banca
story.append(Paragraph('2. Dónde se bancó la victoria (la geografía del margen)', st_h2))
conc = [[Paragraph('Concentración',hcell), Paragraph('Margen neto Abelardo',hcellR),
         Paragraph('% del margen nacional',hcellR)],
 [Paragraph('Antioquia',cellB), colored(fs(m_ant),BLUE), Paragraph(f'{100*m_ant/mar2:.0f}%',cellBr)],
 [Paragraph('   Valle de Aburrá (10 municipios)',cell), colored(fs(m_abu),BLUE,b=False),
  Paragraph(f'{100*m_abu/mar2:.0f}%',cellR)],
 [Paragraph('   Medellín solo',cell), colored(fs(m_med),BLUE,b=False),
  Paragraph(f'{100*m_med/mar2:.0f}%',cellR)],
 [Paragraph('Antioquia + N. de Santander + Santander',cellB), colored(fs(m_tres),BLUE),
  Paragraph(f'{100*m_tres/mar2:.0f}%',cellBr)],
 [Paragraph('Los otros 31 deptos + exterior (neto)',cell), colored(fs(mar2-m_tres),RED,b=False),
  Paragraph('—',cellR)]]
story.append(mktable(conc,[92*mm,42*mm,36*mm], zebra=False))
story.append(Spacer(1,3))
story.append(Paragraph('<b>Medellín por sí solo (+'+f(m_med)+') aporta más que el margen '
  'nacional entero.</b> Los "responsables" en orden: el aparato antioqueño (Medellín, Valle '
  'de Aburrá y Oriente/Rionegro), Cúcuta y el área metropolitana de Bucaramanga, y el voto '
  'del exterior (EE.UU.); con un segundo anillo en Boyacá, eje cafetero, Llanos (Meta y '
  'Casanare) y Huila/Tolima.', st_note))
story.append(Spacer(1,7))

# tablas top municipios lado a lado
def munirows(lst, who):
    out=[[Paragraph('Municipio',hcell), Paragraph('Depto',hcell),
          Paragraph(f'Margen {who}',hcellR)]]
    for r in lst:
        col = BLUE if who=='Abelardo' else RED
        mg = I(r,'margen2v'); val = mg if who=='Abelardo' else -mg
        out.append([Paragraph(r['municipio'].title(),cell),
                    Paragraph(r['depto'],cell), colored('+'+f(val),col,b=False)])
    return out
tA = mktable(munirows(top_abe,'Abelardo'),[40*mm,28*mm,20*mm], headcolor=BLUE)
tC = mktable(munirows(top_cep,'Cepeda'),[40*mm,28*mm,20*mm], headcolor=RED)
side = Table([[tA, tC]], colWidths=[88*mm,88*mm])
side.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
    ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(0,0),6)]))
story.append(KeepTogether([Paragraph('Top 10 municipios donde cada uno bancó margen neto en 2V',
    S(name='cap',fontName=FI,fontSize=8.4,textColor=MUT,leading=11)), Spacer(1,3), side]))

# 3. Cambios vs 1V
story.append(Paragraph('3. Dónde estuvieron los cambios frente a primera vuelta', st_h2))
_bog = next(r for r in rows if r['municipio']=='BOGOTA. D.C.')
_med = next(r for r in rows if r['municipio']=='MEDELLIN')
story.append(Paragraph('El mapa casi no cambió de color (solo 26 municipios cambiaron de '
  'ganador cara a cara, todos pequeños). Lo que cambió fueron las <b>magnitudes</b>. El envión '
  f'pro-Cepeda se concentró en las grandes ciudades, el Caribe y el Pacífico (Bogotá pasó de '
  f'{fs(I(_bog,"margen1v"))} a {fs(I(_bog,"margen2v"))}); el pro-Abelardo, más chico, en su '
  f'fortaleza (Medellín de {fs(I(_med,"margen1v"))} a {fs(I(_med,"margen2v"))}). '
  f'Bogotá + Cali + Cartagena + Barranquilla concentran el {100*s4/swc:.0f}% de todo el '
  f'envión de Cepeda — y perdía las cuatro desde primera vuelta.', st_note))
story.append(Spacer(1,6))
def movrows(lst, toward):
    col = BLUE if toward=='Abelardo' else RED
    out=[[Paragraph('Municipio',hcell), Paragraph('Depto',hcell), Paragraph('Δ margen 2V',hcellR)]]
    for r in lst:
        out.append([Paragraph(r['municipio'].title(),cell), Paragraph(r['depto'],cell),
                    colored(fs(I(r,'delta_margen')),col,b=True)])
    return out
mA = mktable(movrows(mov_abe,'Abelardo'),[40*mm,28*mm,20*mm], headcolor=BLUE)
mC = mktable(movrows(mov_cep,'Cepeda'),[40*mm,28*mm,20*mm], headcolor=RED)
side2 = Table([[mA, mC]], colWidths=[88*mm,88*mm])
side2.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
    ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(0,0),6)]))
story.append(Table([[Paragraph('Se movieron hacia <b>Abelardo</b> (consolidó su fortaleza)',
    S(name='lA',fontName=F,fontSize=8.4,textColor=BLUE,leading=10)),
    Paragraph('Se movieron hacia <b>Cepeda</b> (envión que no alcanzó)',
    S(name='lC',fontName=F,fontSize=8.4,textColor=RED,leading=10))]],
    colWidths=[88*mm,88*mm]))
story.append(Spacer(1,2)); story.append(side2)

# 4. Eficiencia
story.append(Paragraph('4. Por qué ganó con el envión en contra', st_h2))
story.append(Paragraph(f'Es una elección de <b>distribución del voto</b>. Cepeda ganó el envión '
  f'de segunda vuelta ({f(abs(swc))} votos netos a su favor), pero el <b>{100*swc_won/swc:.0f}%</b> '
  f'cayó en municipios que ya ganaba — corriendo el marcador donde no movía el tablero nacional. '
  f'Abelardo movió menos votos, pero los movió donde consolidaba su ventaja: Antioquia, los '
  f'Santanderes, el exterior y el eje cafetero. Su victoria es <b>herencia estructural de '
  f'primera vuelta, no persuasión de segunda</b>: en ningún municipio grande superó la '
  f'expectativa del trasvase de bloques.', st_body))

# 5. Panorama por departamento (pagina nueva, llena de detalle macro)
story.append(PageBreak())
story.append(Paragraph('5. Panorama por departamento', st_h2))
story.append(Paragraph('Los 34 ámbitos (33 departamentos + exterior) ordenados por margen neto '
  'de Abelardo en segunda vuelta. La última columna es el movimiento del cara a cara frente a '
  'primera vuelta (azul = se movió hacia Abelardo; rojo = hacia Cepeda).', st_note))
story.append(Spacer(1,5))
byd = {}
for r in rows:
    dd = byd.setdefault(r['depto'], {'cep2':0,'abe2':0,'m1':0,'m2':0})
    dd['cep2']+=I(r,'cep2v'); dd['abe2']+=I(r,'abe2v')
    dd['m1']+=I(r,'margen1v'); dd['m2']+=I(r,'margen2v')
deps_sorted = sorted(byd.items(), key=lambda kv:-kv[1]['m2'])
def dcell(v):
    return colored(fs(v), BLUE if v>0 else (RED if v<0 else MUT), b=True)
dep_data = [[Paragraph('Departamento',hcell), Paragraph('Cepeda 2V',hcellR),
             Paragraph('Abelardo 2V',hcellR), Paragraph('Margen neto 2V',hcellR),
             Paragraph('Δ vs 1V',hcellR)]]
for dep, v in deps_sorted:
    dep_data.append([Paragraph(dep,cell), Paragraph(f(v['cep2']),cellR),
                     Paragraph(f(v['abe2']),cellR), dcell(v['m2']), dcell(v['m2']-v['m1'])])
story.append(mktable(dep_data,[42*mm,30*mm,30*mm,32*mm,26*mm], pad=2.3))

# Salvedades
story.append(Paragraph('Salvedades metodológicas', st_h2))
story.append(Paragraph(
  '• <b>Fuentes:</b> el escrutinio de primera vuelta proviene del conteo por mesa interno '
  '(121.863 mesas; coincide con el resultado oficial dentro de ~0,08%). La segunda vuelta es el '
  'preconteo en vivo de la Registraduría al 100% de mesas, sujeto a ajustes menores en el '
  'escrutinio definitivo.<br/>'
  '• <b>Modelo de bloques:</b> el "esperado" usa coeficientes de trasvase propios (Paloma 0,85 a '
  'Abelardo; Fajardo 0,55 y Claudia 0,65 a Cepeda; etc.). Si los supuestos cambian, las magnitudes '
  'del over/under se mueven, pero la dirección (Cepeda superó la consolidación mecánica) es robusta.<br/>'
  '• <b>Alcance:</b> análisis ecológico/agregado. Dice <i>dónde</i> se movieron los votos, no '
  '<i>quién</i> individualmente cambió de voto. Cifras no oficiales.', st_note))

# ---- footer ----
def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(F, 7.3); canvas.setFillColor(MUT)
    canvas.drawString(20*mm, 11*mm,
        'ricardoruiz.co · Preconteo 2V vs escrutinio 1V · 21 jun 2026 · cifras no oficiales')
    canvas.drawRightString(190*mm, 11*mm, f'Página {doc.page}')
    canvas.setStrokeColor(LINE); canvas.setLineWidth(0.4)
    canvas.line(20*mm, 14*mm, 190*mm, 14*mm)
    canvas.restoreState()

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm,
                        topMargin=16*mm, bottomMargin=18*mm,
                        title='Análisis 2V 2026 — Dónde ganó Abelardo', author='ricardoruiz.co')
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print('OK ->', OUT)
print('paginas/size:', os.path.getsize(OUT), 'bytes')
