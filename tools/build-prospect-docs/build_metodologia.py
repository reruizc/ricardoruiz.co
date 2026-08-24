"""
Genera el PDF 'Escenarios Prospectivos · Guía paso a paso' (Sprint F.D.3).
Sin dependencias externas además de reportlab.
"""
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    ListFlowable, ListItem
)

INK = HexColor("#14110a"); INK_2 = HexColor("#5a5448"); INK_3 = HexColor("#948e80")
ACCENT = HexColor("#8a1e16"); ACCENT_SOFT = HexColor("#8a1e161a")
PAPER = HexColor("#f4f3ef"); RULE = HexColor("#14110a40")

OUT_DIR = Path(__file__).resolve().parents[2] / "Bases de datos" / "prospect"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "metodologia-paso-a-paso.pdf"

ss = getSampleStyleSheet()
title_style = ParagraphStyle('title', parent=ss['Heading1'], fontName='Helvetica-Bold',
    fontSize=22, leading=26, textColor=INK, spaceAfter=6, alignment=TA_LEFT)
subtitle_style = ParagraphStyle('subtitle', parent=ss['BodyText'], fontName='Helvetica-Oblique',
    fontSize=11, leading=14, textColor=INK_2, spaceAfter=18)
h2_style = ParagraphStyle('h2', parent=ss['Heading2'], fontName='Helvetica-Bold',
    fontSize=14, leading=18, textColor=ACCENT, spaceBefore=18, spaceAfter=8)
h3_style = ParagraphStyle('h3', parent=ss['Heading3'], fontName='Helvetica-Bold',
    fontSize=11, leading=14, textColor=INK, spaceBefore=10, spaceAfter=4)
body_style = ParagraphStyle('body', parent=ss['BodyText'], fontName='Helvetica',
    fontSize=10, leading=14, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=8)
list_style = ParagraphStyle('list', parent=body_style, leftIndent=0, spaceAfter=4)
callout_style = ParagraphStyle('callout', parent=body_style, fontName='Helvetica-Oblique',
    fontSize=9.5, leading=13, textColor=INK_2, leftIndent=10)

def header_footer(c, doc):
    c.saveState()
    c.setStrokeColor(RULE); c.setLineWidth(0.5)
    c.line(doc.leftMargin, letter[1]-1.1*cm, letter[0]-doc.rightMargin, letter[1]-1.1*cm)
    c.setFillColor(INK_3); c.setFont("Helvetica", 8)
    c.drawString(doc.leftMargin, letter[1]-1.4*cm, "Escenarios Prospectivos · Ricardo Ruiz")
    c.drawRightString(letter[0]-doc.rightMargin, letter[1]-1.4*cm, "Guía paso a paso · v1.0 · mayo 2026")
    c.line(doc.leftMargin, 1.3*cm, letter[0]-doc.rightMargin, 1.3*cm)
    c.drawString(doc.leftMargin, 0.9*cm, "ricardoruiz.co · consultoría en datos y política pública")
    c.drawRightString(letter[0]-doc.rightMargin, 0.9*cm, f"Página {doc.page}")
    c.restoreState()

def build():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=2.0*cm, bottomMargin=1.9*cm,
        title="Escenarios Prospectivos · Guía paso a paso",
        author="Ricardo Ruiz · ricardoruiz.co",
        subject="Construcción de escenarios prospectivos para política pública (Godet · Mojica · Schwartz · Lempert)"
    )
    e = []

    e.append(Paragraph("Escenarios Prospectivos", title_style))
    e.append(Paragraph(
        "Guía paso a paso para construir 4 escenarios plausibles, cruzar variables/actores/alternativas, e "
        "identificar decisiones no-regret",
        subtitle_style))
    e.append(Paragraph(
        "Este módulo es el séptimo del Lab de Políticas Públicas y Prospectiva. Es el "
        "lugar natural para preguntar <i>¿qué pasa si el contexto cambia?</i> y para "
        "diseñar decisiones que aguanten en futuros distintos al pronóstico central.",
        body_style))
    e.append(Spacer(1, 12))

    e.append(Paragraph("Contenido", h3_style))
    toc = [
        ["01", "Qué hace el módulo y por qué importa"],
        ["02", "Mecánica 1 · identificar dos incertidumbres críticas"],
        ["03", "Mecánica 2 · narrar los cuatro cuadrantes"],
        ["04", "Mecánica 3 · cross-impact con otros módulos"],
        ["05", "Mecánica 4 · decisiones no-regret + señales tempranas"],
        ["06", "Resultados y exportación"],
        ["07", "Cómo encadenar con los demás módulos"],
    ]
    t = Table(toc, colWidths=[1.2*cm, 13.5*cm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9.5),
        ('TEXTCOLOR', (0,0), (0,-1), ACCENT),
        ('TEXTCOLOR', (1,0), (1,-1), INK),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('LINEBELOW', (0,0), (-1,-2), 0.3, RULE),
    ]))
    e.append(t)

    e.append(Paragraph("01 · Qué hace el módulo y por qué importa", h2_style))
    e.append(Paragraph(
        "La prospectiva estratégica no predice el futuro: <b>construye futuros</b> "
        "alternativos suficientemente plausibles para que la decisión pueda probarse "
        "contra cada uno. La tradición francesa (Godet · Mojica · LIPSOR) lo llama "
        "<i>análisis morfológico de futuros</i>; la tradición anglo (Schwartz · "
        "Global Business Network) lo llama <i>método de los ejes de incertidumbre</i>. "
        "Ambas convergen en lo mismo: dos incertidumbres críticas estructuran cuatro "
        "cuadrantes; cada cuadrante es un futuro plausible; las decisiones robustas son "
        "las que funcionan en al menos tres de los cuatro (Lempert &amp; Walker, RAND 2003).",
        body_style))
    e.append(Paragraph("Para qué te sirve:", body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Anticipar el cambio de contexto.</b> Una política basada en un solo pronóstico es frágil; una política diseñada para múltiples escenarios anticipa shocks.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Defender la decisión frente al comité.</b> Cuando alguien pregunta «¿qué pasa si la economía se desacelera?», puedes responder con la celda específica del escenario pesimista.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Diseñar vigilancia estratégica.</b> Para cada escenario identificas señales tempranas — indicadores que avisan que ese futuro se está materializando antes de que sea tarde.", list_style), leftIndent=15),
    ], bulletType='bullet'))

    e.append(Paragraph("02 · Mecánica 1 · identificar dos incertidumbres críticas", h2_style))
    e.append(Paragraph(
        "Una incertidumbre crítica cumple dos condiciones: (1) <i>importa mucho</i> para "
        "el resultado de la política, y (2) <i>no se puede predecir con seguridad</i>. "
        "Una variable que importa pero es predecible es una restricción, no una "
        "incertidumbre. Una variable incierta pero irrelevante es ruido.",
        body_style))
    e.append(Paragraph(
        "El módulo te pide dos incertidumbres porque <b>dos ejes generan cuatro cuadrantes</b>. "
        "Más ejes son inmanejables narrativamente (8 cuadrantes para 3 ejes, 16 para 4). Si "
        "tienes más de dos, prioriza por el producto importancia × incertidumbre.",
        body_style))
    e.append(Paragraph(
        "<b>Tip del lab:</b> si ya hiciste análisis estructural (MicMac), las dos variables "
        "más motrices del sistema son candidatas naturales — el botón <i>«Importar de MicMac»</i> "
        "las pre-llena automáticamente. Cada incertidumbre tiene un polo negativo y uno positivo "
        "(no juzgar todavía cuál es deseable; sólo describir).",
        callout_style))

    e.append(Paragraph("03 · Mecánica 2 · narrar los cuatro cuadrantes", h2_style))
    e.append(Paragraph(
        "Cada cuadrante combina un polo de cada eje:",
        body_style))
    cuad = [
        ["Cuadrante", "Combinación", "Pregunta narrativa"],
        ["NE", "Eje X positivo + Eje Y positivo", "¿Cómo se ve el mundo si ambas fuerzas se materializan favorablemente?"],
        ["NO", "Eje X negativo + Eje Y positivo", "¿Y si una avanza pero la otra retrocede?"],
        ["SO", "Ambos polos negativos",          "¿Cuál es el escenario adverso? El peor caso plausible (no catastrofismo, plausibilidad)."],
        ["SE", "Eje X positivo + Eje Y negativo","¿Avance en una dimensión, fracaso en la otra?"],
    ]
    ct = Table(cuad, colWidths=[2.0*cm, 5.5*cm, 8.0*cm])
    ct.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (-1,0), ACCENT),
        ('TEXTCOLOR', (0,1), (-1,-1), INK),
        ('BACKGROUND', (0,0), (-1,0), ACCENT_SOFT),
        ('LINEBELOW', (0,0), (-1,-1), 0.3, RULE),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    e.append(ct)
    e.append(Spacer(1, 6))
    e.append(Paragraph(
        "Por cada cuadrante: <b>nombre evocador</b> (no «escenario NE» — un nombre como "
        "«Tigres asiáticos» o «Década perdida» se recuerda), <b>narrativa de 3-5 frases</b> "
        "que describa cómo se vive en ese futuro, y <b>probabilidad subjetiva</b> 0-100. La "
        "suma debe ser ≈100%. Si alguien dice «no se puede asignar probabilidad», recordarles: "
        "asignar 25/25/25/25 también es una probabilidad — el método obliga a explicitarla.",
        body_style))

    e.append(Paragraph("04 · Mecánica 3 · cross-impact con otros módulos", h2_style))
    e.append(Paragraph(
        "Aquí el módulo se conecta con el resto del lab. Importas elementos:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Variables</b> del análisis estructural (MicMac) — cómo se mueven en cada escenario.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Actores</b> de Mactor — quién gana o pierde poder en cada cuadrante.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Alternativas</b> de tu análisis de Alternativas — ¿se vuelve más viable o menos viable en cada escenario?", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "Para cada par (elemento, escenario), asignas un valor <b>-2..+2</b>: -2 = se "
        "debilita fuerte, -1 = se debilita, 0 = neutral, +1 = se fortalece, +2 = se "
        "fortalece fuerte. Es el método de cross-impact original de Theodore Gordon "
        "(RAND, 1968).",
        body_style))
    e.append(Paragraph(
        "Cuando tengas la matriz llena, ya tienes la materia prima para la decisión "
        "no-regret: las alternativas con +1 o más en al menos tres escenarios son "
        "robustas (Lempert).",
        callout_style))

    e.append(Paragraph("05 · Mecánica 4 · decisiones no-regret + señales tempranas", h2_style))
    e.append(Paragraph(
        "El módulo calcula automáticamente, para cada alternativa importada, en cuántos "
        "escenarios tiene impacto ≥ +1. Si son ≥3 de 4, lleva badge <b>«✓ NO-REGRET»</b>. "
        "Esa es la decisión robusta. Cuidado: el método no recomienda elegir solo "
        "no-regret a costa de todo — a veces aceptas mayor riesgo a cambio de mayor "
        "ganancia esperada. El no-regret es <i>una opción a considerar</i>, no <i>la</i> "
        "opción.",
        body_style))
    e.append(Paragraph(
        "<b>Plan de contingencia:</b> si eliges una alternativa no perfectamente no-regret, "
        "documenta qué harías en el escenario donde falla. Esto es lo que distingue una "
        "decisión audaz de una decisión imprudente.",
        body_style))
    e.append(Paragraph(
        "<b>Señales tempranas:</b> para cada escenario, ¿qué indicador me dice que se "
        "está materializando antes de que sea tarde? La prospectiva sin vigilancia "
        "estratégica es ejercicio académico. Con vigilancia, es disciplina ejecutiva.",
        body_style))

    e.append(Paragraph("06 · Resultados y exportación", h2_style))
    e.append(Paragraph(
        "Tres entregables descargables desde la pantalla final:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Memo prospectivo (.md).</b> Documento estructurado en 5 secciones: incertidumbres + narrativa de los cuatro cuadrantes + matriz cross-impact + decisiones no-regret + plan de contingencia y señales tempranas. Footer metodológico con cita a las escuelas.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Matriz cross-impact (.csv).</b> Tabla cruda elementos × escenarios para llevar a Excel, replicar el análisis o cargar al sistema de monitoreo.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Ficha de escenarios (.pdf).</b> Formato presentable a comité con la narrativa de los cuatro cuadrantes y las decisiones robustas resaltadas. Disclaimer: «borrador estilo CONPES; no es CONPES oficial».", list_style), leftIndent=15),
    ], bulletType='bullet'))

    e.append(Paragraph("07 · Cómo encadenar con los demás módulos", h2_style))
    e.append(Paragraph(
        "Este módulo está pensado para llegar <b>después</b> del análisis estructural, "
        "el mapa de actores y las alternativas — usa sus outputs como input. La ruta "
        "típica:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>1.</b> Problema público → enuncia el problema.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>2.</b> Análisis estructural → identifica las variables motrices.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>3.</b> Mactor → mapea actores y sus posiciones.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>4.</b> Alternativas → construye 3-5 alternativas con análisis morfológico.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>5.</b> Escenarios prospectivos (este módulo) → prueba las alternativas contra 4 futuros.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>6.</b> Evaluación → diseña cómo medir si la alternativa elegida funcionó.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>7.</b> AIN → si la salida es regulatoria, dimensiona impactos normativos.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "El informe combinado del lab (sección «Mi informe del lab» en el hub) une "
        "los siete módulos en un memo CONPES integrado.",
        callout_style))

    doc.build(e, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"✓ Generado: {OUT}")
    print(f"  Tamaño: {OUT.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    build()
