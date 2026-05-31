"""
Genera el PDF 'Comunicar la Política · Guía paso a paso' (Sprint H · v2).
Octavo módulo del Lab de Políticas Públicas y Prospectiva.
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

OUT_DIR = Path(__file__).resolve().parents[2] / "Bases de datos" / "comunicar"
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
    c.drawString(doc.leftMargin, letter[1]-1.4*cm, "Comunicar la Política · Ricardo Ruiz")
    c.drawRightString(letter[0]-doc.rightMargin, letter[1]-1.4*cm, "Guía paso a paso · v1.0 · mayo 2026")
    c.line(doc.leftMargin, 1.3*cm, letter[0]-doc.rightMargin, 1.3*cm)
    c.drawString(doc.leftMargin, 0.9*cm, "ricardoruiz.co · consultoría en datos y política pública")
    c.drawRightString(letter[0]-doc.rightMargin, 0.9*cm, f"Página {doc.page}")
    c.restoreState()

def build():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=2.0*cm, bottomMargin=1.9*cm,
        title="Comunicar la Política · Guía paso a paso",
        author="Ricardo Ruiz · ricardoruiz.co",
        subject="Plan de comunicación de política pública (OCDE 2021 · CLAD · MIPG · Ganz · Lakoff · EAST)"
    )
    e = []

    e.append(Paragraph("Comunicar la Política", title_style))
    e.append(Paragraph(
        "Guía paso a paso para diseñar el plan de comunicación pública de una "
        "política: audiencias, mensaje, narrativa, framing, canales, vocería, "
        "cronograma y medición",
        subtitle_style))
    e.append(Paragraph(
        "Este módulo es el octavo del Lab de Políticas Públicas y Prospectiva. "
        "Una política bien diseñada que no se comunica bien no se sostiene: la "
        "evidencia muestra que la <i>implementación</i> y la <i>legitimidad</i> de "
        "una política dependen tanto de cómo se cuenta como de qué dice. Este "
        "módulo convierte un buen diagnóstico técnico en un plan de comunicación "
        "operable, medible y defendible.",
        body_style))
    e.append(Spacer(1, 12))

    e.append(Paragraph("Contenido", h3_style))
    toc = [
        ["01", "Qué hace el módulo y en qué se basa"],
        ["02", "Mecánica 1 · contexto y alcance"],
        ["03", "Mecánica 2 · audiencias"],
        ["04", "Mecánica 3 · mensaje clave"],
        ["05", "Mecánica 4 · narrativa pública (Ganz)"],
        ["06", "Mecánica 5 · framing (Lakoff · Shenker-Osorio)"],
        ["07", "Mecánica 6 · canales y matriz EAST"],
        ["08", "Mecánica 7 · vocería"],
        ["09", "Mecánica 8 · cronograma y medición OCDE (9 dimensiones)"],
        ["10", "Exportables y cómo encadenar con los demás módulos"],
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

    e.append(Paragraph("01 · Qué hace el módulo y en qué se basa", h2_style))
    e.append(Paragraph(
        "El módulo te guía por <b>ocho decisiones</b> que estructuran un plan de "
        "comunicación pública. No es marketing: la comunicación pública tiene "
        "estándares propios — transparencia, rendición de cuentas, inclusión y "
        "lenguaje claro. El módulo combina cinco escuelas que la disciplina "
        "considera fundacionales:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>OCDE · Public Communication Report 2021.</b> Define la comunicación pública como función de gobierno y aporta las <i>nueve dimensiones de medición</i> que usa la mecánica 8.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>CLAD · Carta Iberoamericana de Gobierno Abierto 2016.</b> Marco regional firmado en Bogotá; ancla la comunicación en apertura y participación.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Colombia · Función Pública (MIPG, Dimensión 5; Decreto 1499/2017; Ley 1712/2014).</b> Obligaciones de información, comunicación y lenguaje claro.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Marshall Ganz · Public Narrative.</b> La narrativa Story of Self / Us / Now traduce valores en acción colectiva.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Framing (Lakoff · Shenker-Osorio · BIT EAST · Stone · Rincón).</b> Cómo se encuadra un mensaje determina cómo se interpreta.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "<b>Regla de oro:</b> el copiloto sugiere, el humano decide. El plan que "
        "produce el módulo es un borrador estructurado — la vocería y la jurídica "
        "del equipo lo validan antes de salir al aire.",
        callout_style))

    e.append(Paragraph("02 · Mecánica 1 · contexto y alcance", h2_style))
    e.append(Paragraph(
        "Antes de hablar hay que saber desde dónde se habla. Defines la "
        "<b>política</b>, su <b>fase del ciclo</b> (diseño · evaluación · "
        "implementación · crisis), el <b>objetivo comunicacional</b> (informar · "
        "persuadir · movilizar · rendir cuentas · defender · co-crear), el "
        "<b>horizonte temporal</b> y el <b>territorio</b>. La fase importa: "
        "comunicar en diseño busca legitimar; en crisis, contener. Si vienes de "
        "otro módulo del Lab (Problema Público, Evaluación, Alternativas, AIN), el "
        "botón de importación pre-llena el enunciado.",
        body_style))

    e.append(Paragraph("03 · Mecánica 2 · audiencias", h2_style))
    e.append(Paragraph(
        "No se le habla igual a la ciudadanía afectada, a los medios, al concejo o "
        "asamblea, a la sociedad civil organizada, a la academia y al equipo "
        "interno. Defines entre <b>2 y 6 audiencias</b> con perfil, prioridad "
        "(alta/media/baja), conocimiento previo del tema y tono adecuado. El botón "
        "«Cargar audiencias típicas» siembra seis audiencias estándar del sector "
        "público para que edites en vez de empezar de cero. La regla práctica: "
        "segmentar lo suficiente para diferenciar el mensaje, no tanto que el plan "
        "se vuelva inmanejable.",
        body_style))

    e.append(Paragraph("04 · Mecánica 3 · mensaje clave", h2_style))
    e.append(Paragraph(
        "El corazón del plan. Un <b>mensaje primario de ≤15 palabras</b> (con "
        "contador en vivo), <b>tres mensajes secundarios</b>, una <b>promesa "
        "concreta</b>, la <b>evidencia principal</b> que la respalda y los "
        "<b>valores invocados</b> (2 a 5, desde un menú de valores universales). "
        "La heurística de Anat Shenker-Osorio: el mensaje empieza por el valor, no "
        "por el problema del adversario; usa verbo de acción; nombra el beneficio "
        "concreto. Repetir el mensaje del adversario — aunque sea para negarlo — lo "
        "refuerza (Lakoff).",
        body_style))

    e.append(Paragraph("05 · Mecánica 4 · narrativa pública (Ganz)", h2_style))
    e.append(Paragraph(
        "Los datos informan; las historias movilizan. La narrativa pública de "
        "Marshall Ganz tiene tres movimientos:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Story of Self.</b> Por qué a quien comunica le importa esto — la elección de valores hecha pública.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Story of Us.</b> Qué tienen en común quien habla y la audiencia — la identidad compartida.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Story of Now.</b> La urgencia: por qué hay que actuar hoy y qué pasa si no.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "El módulo da una plantilla por cada movimiento. No es relleno retórico: "
        "una política sin Story of Now no genera urgencia, y sin Story of Us se lee "
        "como imposición.",
        callout_style))

    e.append(Paragraph("06 · Mecánica 5 · framing (Lakoff · Shenker-Osorio)", h2_style))
    e.append(Paragraph(
        "Defines el <b>valor central</b> que organiza el encuadre, la <b>metáfora "
        "dominante</b>, las <b>palabras propias</b> (las que sí repetimos) y las "
        "<b>palabras del adversario</b> (las que NO repetimos, regla 1 de Lakoff). "
        "El error más común en comunicación pública es discutir en el marco del "
        "adversario: cada vez que niegas su término, lo activas. El módulo te obliga "
        "a declarar cómo romper el encuadre adversario con uno propio en vez de "
        "reaccionar al suyo.",
        body_style))

    e.append(Paragraph("07 · Mecánica 6 · canales y matriz EAST", h2_style))
    e.append(Paragraph(
        "Eliges entre 3 y 10 canales de un catálogo de 14 (medios tradicionales, "
        "redes Meta, X, TikTok, YouTube, WhatsApp, web oficial, email, territorial, "
        "eventos, sociedad civil, influencers, gremios, academia) y construyes una "
        "<b>matriz audiencia × canal</b> donde cada celda cicla 0→1→2→3 (sin uso · "
        "apoyo · canal principal · saturación). La heurística EAST del Behavioural "
        "Insights Team orienta el diseño de cada mensaje por canal:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Easy</b> — quita fricción: si quieres que la gente haga algo, hazlo fácil.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Attractive</b> — capta la atención y personaliza.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Social</b> — muestra que otros ya lo hacen (norma social).", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Timely</b> — comunica en el momento en que la persona es más receptiva.", list_style), leftIndent=15),
    ], bulletType='bullet'))

    e.append(Paragraph("08 · Mecánica 7 · vocería", h2_style))
    e.append(Paragraph(
        "Defines un <b>vocero principal</b> (nombre, rol y por qué es la voz "
        "adecuada) y hasta ocho <b>multiplicadores</b> con tipo (académico, "
        "gremial, territorial, medios, sociedad civil, celebridad, político "
        "aliado) y la audiencia que cada uno cubre. Documentas <b>riesgos de "
        "vocería</b> y un <b>plan B</b>. La elección del mensajero es parte del "
        "mensaje: la misma frase tiene credibilidad distinta según quién la diga "
        "ante cada audiencia.",
        body_style))

    e.append(Paragraph("09 · Mecánica 8 · cronograma y medición OCDE (9 dimensiones)", h2_style))
    e.append(Paragraph(
        "El plan se ordena en <b>cuatro fases</b> (pre-lanzamiento · lanzamiento · "
        "mantenimiento · evaluación) y se mide con las <b>nueve dimensiones</b> del "
        "Public Communication Report de la OCDE — un KPI por dimensión, con meta y "
        "fuente:",
        body_style))
    dims = [
        ["Dimensión", "Qué captura"],
        ["Alcance", "Cuántas personas fueron expuestas al mensaje"],
        ["Engagement", "Interacción activa (comentarios, compartidos, asistencia)"],
        ["Atención", "Tiempo y profundidad de exposición"],
        ["Comprensión", "Si la audiencia entiende correctamente el mensaje"],
        ["Satisfacción", "Valoración de la comunicación recibida"],
        ["Apoyo", "Respaldo declarado a la política"],
        ["Cambio actitudinal", "Movimiento en percepciones y creencias"],
        ["Intención", "Disposición declarada a actuar"],
        ["Comportamiento", "Acción efectiva observada"],
    ]
    dt = Table(dims, colWidths=[4.2*cm, 11.3*cm])
    dt.setStyle(TableStyle([
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
    e.append(dt)
    e.append(Spacer(1, 6))
    e.append(Paragraph(
        "La gradación es deliberada: medir solo alcance (la métrica fácil) es el "
        "error clásico. Una campaña con gran alcance y cero cambio de comportamiento "
        "falló. El plan también define un <b>plan de monitoreo</b> y los "
        "<b>triggers de ajuste</b> que disparan una corrección de rumbo.",
        body_style))

    e.append(Paragraph("10 · Exportables y cómo encadenar con los demás módulos", h2_style))
    e.append(Paragraph(
        "Tres entregables descargables desde la pantalla final:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Plan de comunicación (.md).</b> Documento en nueve secciones: contexto · audiencias · mensaje · narrativa Ganz · framing · canales · vocería · cronograma · medición OCDE. Footer metodológico con cita a las cinco escuelas.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Matriz (.csv).</b> Dos bloques: matriz audiencia × canal y tabla de KPIs OCDE (dimensión, KPI, meta, fuente) para llevar a Excel o al sistema de monitoreo.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Guía de mensajes (.md).</b> Documento operativo para la vocería y prensa: mensaje primario, secundarios, narrativa Ganz en 90 segundos, lenguaje (qué decimos · qué NO repetimos · valor central · metáfora) y plan de respuesta al frame adversario.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "Este módulo cierra el ciclo del lab: viene <b>después</b> de definir el "
        "problema, mapear actores, construir alternativas, sustentar la norma (AIN), "
        "evaluar y prospectar. El informe combinado del lab (sección «Mi informe "
        "del lab» en el hub) une los ocho módulos en un memo CONPES integrado, "
        "donde el plan de comunicación es la sección 9.",
        callout_style))

    doc.build(e, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"✓ Generado: {OUT}")
    print(f"  Tamaño: {OUT.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    build()
