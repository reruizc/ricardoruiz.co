#!/usr/bin/env python3
"""Genera el PDF del derecho de peticion a SIEDCO desde el markdown.

El markdown es la FUENTE: este script no duplica el texto, lo lee.
    python3 tools/build-solicitud-ponal/build.py
"""
import os, re, sys
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, ListFlowable, ListItem)

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MD   = os.path.join(RAIZ, 'PONAL 2026', 'solicitud-2026.md')
OUT  = os.path.join(RAIZ, 'PONAL 2026', 'Solicitud RERC DATA 2026.pdf')

FUENTE, FUENTE_B = 'Helvetica', 'Helvetica-Bold'
VERDE = colors.HexColor('#1f7a45')   # el verde de las tablas del oficio original

S = {
 'p':    ParagraphStyle('p', fontName=FUENTE, fontSize=10.5, leading=15.5,
                        alignment=TA_JUSTIFY, spaceAfter=9),
 'enc':  ParagraphStyle('enc', fontName=FUENTE, fontSize=10.5, leading=14,
                        alignment=TA_LEFT, spaceAfter=0),
 'ref':  ParagraphStyle('ref', fontName=FUENTE, fontSize=10.5, leading=15.5,
                        alignment=TA_JUSTIFY, leftIndent=1.4*cm, spaceAfter=14),
 'h':    ParagraphStyle('h', fontName=FUENTE_B, fontSize=11, leading=15,
                        alignment=TA_LEFT, spaceBefore=10, spaceAfter=7),
 'li':   ParagraphStyle('li', fontName=FUENTE, fontSize=10.5, leading=15,
                        alignment=TA_JUSTIFY),
 'th':   ParagraphStyle('th', fontName=FUENTE, fontSize=7.4, leading=8.8,
                        alignment=1, textColor=colors.white),
 'firma':ParagraphStyle('firma', fontName=FUENTE, fontSize=10.5, leading=14,
                        alignment=TA_LEFT, spaceAfter=0),
}

def inline(t):
    """**negrita**, __subrayado__, @B@..@/B@ (negrita de arranque de parrafo)."""
    t = t.replace('&', '&amp;')
    t = re.sub(r'@B@(.+?)@/B@', r'<b>\1</b>', t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'__(.+?)__',    r'<u>\1</u>', t)
    return t

def tabla(celdas, ancho):
    # cada columna recibe, como piso, el ancho de su palabra mas larga: asi
    # ningun rotulo se parte ("DIVIPO / LA"). El sobrante se reparte a prorrata.
    fs = S['th'].fontName, S['th'].fontSize
    pad = 5.0
    minimos = [max(stringWidth(w, *fs) for w in c.split()) + pad for c in celdas]
    sobra = ancho - sum(minimos)
    if sobra < 0:                      # no cabe: encoger la letra y reintentar
        S['th'].fontSize = max(5.6, S['th'].fontSize * ancho / sum(minimos))
        S['th'].leading = S['th'].fontSize * 1.2
        fs = S['th'].fontName, S['th'].fontSize
        minimos = [max(stringWidth(w, *fs) for w in c.split()) + pad for c in celdas]
        sobra = max(0.0, ancho - sum(minimos))
    tot = sum(minimos)
    cols = [m + sobra * m / tot for m in minimos]
    fila = [Paragraph(inline(c), S['th']) for c in celdas]
    t = Table([fila], colWidths=cols)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), VERDE),
        ('GRID',       (0,0), (-1,-1), 0.6, colors.white),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING',(0,0),(-1,-1), 4),
        ('LEFTPADDING',(0,0), (-1,-1), 2),
        ('RIGHTPADDING',(0,0),(-1,-1), 2),
    ]))
    return t

def construir():
    doc = SimpleDocTemplate(OUT, pagesize=letter,
        leftMargin=2.6*cm, rightMargin=2.6*cm, topMargin=2.6*cm, bottomMargin=2.4*cm,
        title='Derecho de peticion - SIEDCO 2026',
        author='Ricardo Esteban Ruiz Castro', subject='Solicitud de informacion SIEDCO 2025-2026')
    ancho = doc.width
    with open(MD, encoding='utf-8') as f:
        lineas = f.read().split('\n')

    fl, buf_num, buf_bul, encabezado, firmando = [], [], [], True, False
    def cerrar_num():
        if buf_num:
            fl.append(ListFlowable(
                [ListItem(Paragraph(inline(x), S['li']), leftIndent=1.1*cm) for x in buf_num],
                bulletType='1', bulletFormat='%s.', bulletFontName=FUENTE, bulletFontSize=10.5,
                leftIndent=1.0*cm, spaceAfter=10))
            buf_num.clear()
    def cerrar_bul():
        if buf_bul:
            fl.append(ListFlowable(
                [ListItem(Paragraph(inline(x), S['li']), leftIndent=0.9*cm) for x in buf_bul],
                bulletType='bullet', bulletFontName=FUENTE, bulletFontSize=10.5,
                leftIndent=0.8*cm, spaceBefore=2, spaceAfter=10))
            buf_bul.clear()

    for ln in lineas:
        s = ln.rstrip()
        if s.startswith('# '):                      # titulo interno, no se imprime
            continue
        if not s.strip():
            cerrar_num(); cerrar_bul()
            continue
        m = re.match(r'^(\d+)\.\s+(.*)$', s)
        if m:
            cerrar_bul(); buf_num.append(m.group(2)); continue
        if s.startswith('- '):
            cerrar_num(); buf_bul.append(s[2:]); continue
        cerrar_num(); cerrar_bul()
        if s.startswith('|'):
            celdas = [c.strip() for c in s.strip('|').split('|')]
            fl.append(tabla(celdas, ancho)); fl.append(Spacer(1, 8)); continue
        if s.startswith('@H@'):
            fl.append(Spacer(1, 4)); fl.append(Paragraph(inline(s[3:]), S['h'])); continue
        if s.startswith('@REF@'):
            encabezado = False
            fl.append(Spacer(1, 16))
            fl.append(Paragraph(inline(s[5:]), S['ref'])); continue
        if s.startswith('@FIRMA@'):
            firmando = True
            fl.append(Spacer(1, 34)); fl.append(Paragraph(inline(s[7:]), S['firma'])); continue
        if firmando:
            fl.append(Paragraph(inline(s), S['firma'])); continue
        if encabezado:
            fl.append(Paragraph(inline(s), S['enc']))
            if s.startswith('Bogotá,'):
                fl.append(Spacer(1, 26))
        else:
            fl.append(Paragraph(inline(s), S['p']))
    cerrar_num(); cerrar_bul()
    doc.build(fl)
    print('OK ->', OUT)

if __name__ == '__main__':
    if not os.path.exists(MD):
        sys.exit('falta ' + MD)
    construir()
