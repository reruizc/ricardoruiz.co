"""
Genera el PDF "Mactor · Guía paso a paso" (análisis de actores y conflictos).
"""
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, ListFlowable, ListItem
)

INK = HexColor("#14110a"); INK_2 = HexColor("#5a5448"); INK_3 = HexColor("#948e80")
ACCENT = HexColor("#8a1e16"); ACCENT_SOFT = HexColor("#8a1e161a")
PAPER = HexColor("#f4f3ef"); RULE = HexColor("#14110a40")

OUT_DIR = Path(__file__).resolve().parents[2] / "Bases de datos" / "mactor"
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
    c.drawString(doc.leftMargin, letter[1]-1.4*cm, "Análisis de Actores · Ricardo Ruiz")
    c.drawRightString(letter[0]-doc.rightMargin, letter[1]-1.4*cm, "Guía paso a paso · v1.0 · mayo 2026")
    c.line(doc.leftMargin, 1.3*cm, letter[0]-doc.rightMargin, 1.3*cm)
    c.drawString(doc.leftMargin, 0.9*cm, "ricardoruiz.co · consultoría en datos y política pública")
    c.drawRightString(letter[0]-doc.rightMargin, 0.9*cm, f"Página {doc.page}")
    c.restoreState()

def build():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=2.0*cm, bottomMargin=1.9*cm,
        title="Mactor · Guía paso a paso",
        author="Ricardo Ruiz · ricardoruiz.co",
        subject="Análisis de actores y conflictos de política pública"
    )
    e = []
    e.append(Paragraph("Análisis de Actores y Conflictos", title_style))
    e.append(Paragraph("Guía paso a paso para mapear quién apoya, quién bloquea y dónde están los conflictos en una decisión de política pública", subtitle_style))
    e.append(Paragraph(
        "Esta guía acompaña el uso de la herramienta web en "
        "<font color='#8a1e16'>ricardoruiz.co/mactor.html</font>. Es el complemento "
        "del análisis estructural de variables: si ese te dice <i>qué mover</i>, "
        "este te dice <i>quiénes son los que pueden moverlo o frenarlo</i>.",
        body_style))
    e.append(Spacer(1, 12))

    e.append(Paragraph("Contenido", h3_style))
    toc = [
        ["01", "Qué es Mactor y para qué sirve"],
        ["02", "Antes de empezar: cómo definir actores"],
        ["03", "Cómo definir objetivos en disputa"],
        ["04", "Calificar influencias entre actores (matriz MID)"],
        ["05", "Calificar posiciones sobre objetivos (matriz MAO)"],
        ["06", "Leer los resultados: influencia, alianzas, objetivos"],
        ["07", "Copiloto IA"],
        ["08", "Cómo conectar con el análisis estructural"],
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

    e.append(Paragraph("01 · Qué es Mactor y para qué sirve", h2_style))
    e.append(Paragraph(
        "Mactor es una herramienta de análisis del <i>juego político</i> alrededor "
        "de una decisión. La idea central: una política pública no falla por "
        "mal diseño técnico, falla porque no entendió a tiempo a los actores "
        "que tienen poder sobre ella. Mactor identifica quién manda, quién "
        "es manejado, quién está aliado con quién y dónde están los conflictos.",
        body_style))
    e.append(Paragraph(
        "El método viene de Michel Godet en LIPSOR (París, 1991) como "
        "complemento natural del análisis estructural MICMAC. En Colombia el "
        "referente es Francisco José Mojica (Universidad Externado), formado "
        "directamente con Godet en la Sorbona.",
        body_style))

    e.append(Paragraph("02 · Antes de empezar: cómo definir actores", h2_style))
    e.append(Paragraph(
        "Los actores son los individuos, organizaciones o grupos con "
        "intereses sobre la decisión que estás analizando. Tres reglas:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Específicos, no genéricos.</b> No \"sociedad civil\" sino \"ANDI\", \"Fedegan\", \"CUT\", \"MinHacienda\". Si el nombre del actor cabe en cualquier proceso del país, está demasiado general.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Entre 6 y 15 en total.</b> Por debajo de 5 el análisis pierde resolución. Por encima de 20 la matriz NxN se vuelve impractica.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Incluye actores en conflicto y árbitros.</b> Si todos están del mismo lado, el análisis no te dirá nada. Asegúrate de incluir los que apoyan y los que bloquean.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Spacer(1, 6))
    e.append(Paragraph("Si no sabes por dónde arrancar, el copiloto IA puede sugerirte una lista típica para tu tema (plan Pro o superior).", callout_style))

    e.append(Paragraph("03 · Cómo definir objetivos en disputa", h2_style))
    e.append(Paragraph(
        "Los objetivos son las decisiones, proyectos, reformas o leyes "
        "concretas sobre las que los actores se posicionan. Idealmente entre "
        "5 y 15: lo suficientemente específicos para que un actor pueda estar "
        "claramente a favor o en contra. Ejemplos: \"Aumentar tarifa de "
        "renta a empresas grandes\", \"Sustitución de cultivos ilícitos en "
        "Tumaco\", \"Reforma de la edad de jubilación\".",
        body_style))

    e.append(Paragraph("04 · Calificar influencias entre actores (matriz MID)", h2_style))
    e.append(Paragraph(
        "Para cada par (A, B), califica <b>cuánto influye A sobre B</b>. La "
        "escala 0-4 captura la <i>profundidad</i> del impacto:",
        body_style))
    sc = [
        ["0", "Nula",         "A no tiene capacidad de afectar a B"],
        ["1", "Procesos",     "A puede afectar procesos operativos de B"],
        ["2", "Proyectos",    "A puede afectar proyectos estratégicos de B"],
        ["3", "Misión",       "A puede afectar la misión institucional de B"],
        ["4", "Existencia",   "A puede poner en riesgo la existencia misma de B"],
    ]
    st = Table(sc, colWidths=[1.3*cm, 2.5*cm, 11.2*cm])
    st.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (0,-1), 12),
        ('TEXTCOLOR', (0,0), (0,-1), ACCENT),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (1,0), (-1,-1), 10),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,-1), 0.3, RULE),
        ('BACKGROUND', (0,0), (0,-1), ACCENT_SOFT),
    ]))
    e.append(st)
    e.append(Spacer(1, 6))
    e.append(Paragraph(
        "La diagonal está bloqueada — un actor no se influye a sí mismo. La "
        "matriz no tiene que ser simétrica: A puede influir mucho sobre B "
        "sin que B influya sobre A.",
        body_style))

    e.append(Paragraph("05 · Calificar posiciones sobre objetivos (matriz MAO)", h2_style))
    e.append(Paragraph(
        "Para cada actor (filas) y cada objetivo (columnas), califica qué "
        "tan a favor (signo positivo) o en contra (signo negativo) está el "
        "actor, en la misma escala de intensidad:",
        body_style))
    sc2 = [
        ["+4 / −4",  "Existencia",     "El objetivo afecta la existencia del actor"],
        ["+3 / −3",  "Misión",          "El objetivo afecta su misión institucional"],
        ["+2 / −2",  "Proyectos",       "El objetivo afecta sus proyectos estratégicos"],
        ["+1 / −1",  "Procesos",        "El objetivo afecta sus procesos operativos"],
        ["0",        "Nula",            "El objetivo no afecta al actor"],
    ]
    st2 = Table(sc2, colWidths=[1.8*cm, 2.5*cm, 10.7*cm])
    st2.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (0,-1), 10.5),
        ('TEXTCOLOR', (0,0), (0,-1), ACCENT),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (1,0), (-1,-1), 10),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,-1), 0.3, RULE),
        ('BACKGROUND', (0,0), (0,-1), ACCENT_SOFT),
    ]))
    e.append(st2)

    e.append(PageBreak())
    e.append(Paragraph("06 · Leer los resultados", h2_style))

    e.append(Paragraph("Influencia × Dependencia", h3_style))
    e.append(Paragraph(
        "Cada actor aparece en un plano según cuánto influye (eje Y, sumas "
        "de fila de MID) y cuánto depende del sistema (eje X, sumas de "
        "columna). Cuatro cuadrantes:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Dominantes</b>: mucha influencia, poca dependencia. Tienen el poder estratégico. Hay que sentarse con ellos primero.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>De enlace</b>: mucha influencia y mucha dependencia. Críticos: pueden ser palancas o cuellos de botella.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Dominados</b>: poca influencia, mucha dependencia. El sistema los empuja.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Autónomos</b>: poca influencia, poca dependencia. Marginales en este análisis.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "El <b>poder relativo Ri</b> = Influencia/(Influencia+Dependencia) "
        "normaliza el peso de cada actor. Es lo que se usa para ponderar las "
        "posiciones sobre objetivos.",
        body_style))

    e.append(Paragraph("Convergencia × Divergencia (alianzas y conflictos)", h3_style))
    e.append(Paragraph(
        "Para cada par de actores, sumamos los objetivos en los que están "
        "del mismo lado (convergencia) y en los que están en lados opuestos "
        "(divergencia). La intensidad se cuenta por el <i>mínimo</i> de sus "
        "posiciones — un actor con +4 y otro con +1 cuentan como +1 de "
        "convergencia.",
        body_style))
    e.append(Paragraph(
        "Las <b>coaliciones prometedoras</b> son pares con alta convergencia "
        "y baja divergencia. Los <b>conflictos a arbitrar</b> son los de "
        "alta divergencia. La herramienta te muestra los top 6 de cada lado.",
        body_style))

    e.append(Paragraph("Objetivos por movilización y saldo neto", h3_style))
    e.append(Paragraph(
        "Para cada objetivo: la <b>movilización</b> es la suma de las "
        "magnitudes de las posiciones (qué tan disputado está). El <b>saldo "
        "neto</b> es la suma de las posiciones ponderadas por el poder Ri "
        "del actor. Signo positivo = apoyo neto, negativo = oposición neta, "
        "cerca de cero = empate de fuerzas (conflicto sin resolver, el más "
        "peligroso de gestionar).",
        body_style))

    e.append(Paragraph("07 · Copiloto IA", h2_style))
    e.append(Paragraph(
        "La herramienta tiene un copiloto de inteligencia artificial que "
        "asiste en tres momentos:",
        body_style))
    cop = [
        ["Sugerir actores",     "El copiloto propone una lista típica de 8-15 actores para tu tema, con familia conceptual (gobierno, gremio, sindicato, etc.) y razón. Plan <b>Pro</b> o superior."],
        ["Revisar posiciones",  "Detecta posiciones improbables: contradicciones con la misión típica del actor, neutralidades sospechosas, asimetrías. Plan <b>Premium</b> o superior."],
        ["Lectura final",       "Redacta panorama, actores clave, alianzas, conflictos, objetivos disputados y tres recomendaciones de incidencia. Plan <b>Premium</b> o superior."],
    ]
    ct = Table(cop, colWidths=[3.5*cm, 11.5*cm])
    ct.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9.5),
        ('TEXTCOLOR', (0,0), (0,-1), ACCENT),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0,0), (-1,-1), 0.3, RULE),
    ]))
    e.append(ct)
    e.append(Spacer(1, 6))
    e.append(Paragraph(
        "<b>Regla básica:</b> el copiloto sugiere; tú decides. Una posición que "
        "el modelo flagea como contradictoria puede ser una hipótesis real "
        "del experto que rompe la intuición naive.",
        callout_style))

    e.append(Paragraph("08 · Cómo conectar con el análisis estructural", h2_style))
    e.append(Paragraph(
        "Mactor y el análisis estructural de variables son dos lentes "
        "complementarios sobre el mismo sistema. El flujo natural:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Empieza con variables</b> en analisis-estructural.html: ¿qué piezas mueven el sistema?", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Identifica las palancas</b>: las variables motrices son los puntos donde una intervención puede transformar el sistema.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Pasa a Mactor</b>: ¿quiénes son los actores con poder sobre esas palancas? Si MinHacienda controla la palanca \"recursos fiscales\", MinHacienda es un actor central en tu Mactor.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Diseña la estrategia</b>: con quién sentarse primero (dominantes alineados), qué conflictos arbitrar (alta divergencia), qué objetivos hay que cabildear con prioridad (alto saldo positivo pero baja movilización).", list_style), leftIndent=15),
    ], bulletType='bullet'))

    e.append(Spacer(1, 12))
    e.append(Paragraph("¿Dudas?", h3_style))
    e.append(Paragraph(
        "Escríbenos a <font color='#8a1e16'>contacto@ricardoruiz.co</font>. "
        "Si vas a usar esta herramienta para una estrategia de incidencia o "
        "una consultoría política, podemos acompañarte con un soporte "
        "metodológico a la medida.",
        body_style))

    doc.build(e, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"OK: {OUT} ({OUT.stat().st_size/1024:.1f} KB)")

if __name__ == "__main__":
    build()
