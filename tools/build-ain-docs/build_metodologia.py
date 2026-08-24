"""
Genera 'Análisis de Impacto Normativo · Guía paso a paso' (Sprint D.10 del Lab).
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
PAPER = HexColor("#f4f3ef"); RULE = HexColor("#14110a40"); GOLD = HexColor("#8a6a1a")

OUT_DIR = Path(__file__).resolve().parents[2] / "Bases de datos" / "ain"
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
example_style = ParagraphStyle('example', parent=body_style, fontName='Helvetica',
    fontSize=9.5, leading=13, textColor=INK, leftIndent=10, spaceAfter=6)

def header_footer(c, doc):
    c.saveState()
    c.setStrokeColor(RULE); c.setLineWidth(0.5)
    c.line(doc.leftMargin, letter[1]-1.1*cm, letter[0]-doc.rightMargin, letter[1]-1.1*cm)
    c.setFillColor(INK_3); c.setFont("Helvetica", 8)
    c.drawString(doc.leftMargin, letter[1]-1.4*cm, "Análisis de Impacto Normativo · Ricardo Ruiz")
    c.drawRightString(letter[0]-doc.rightMargin, letter[1]-1.4*cm, "Guía paso a paso · v1.0 · mayo 2026")
    c.line(doc.leftMargin, 1.3*cm, letter[0]-doc.rightMargin, 1.3*cm)
    c.drawString(doc.leftMargin, 0.9*cm, "ricardoruiz.co · consultoría en datos y política pública")
    c.drawRightString(letter[0]-doc.rightMargin, 0.9*cm, f"Página {doc.page}")
    c.restoreState()

def build():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=2.0*cm, bottomMargin=1.9*cm,
        title="Análisis de Impacto Normativo · Guía paso a paso",
        author="Ricardo Ruiz · ricardoruiz.co",
        subject="AIN/RIA: DNP Decreto 1081/2015 + Función Pública Decreto 1273/2020 + OCDE RIA 2012"
    )
    e = []

    e.append(Paragraph("Análisis de Impacto Normativo", title_style))
    e.append(Paragraph(
        "Guía paso a paso para sustentar un proyecto normativo con AIN: problema regulatorio, "
        "objetivos, opciones, impactos, consulta pública, riesgo regulatorio e implementación",
        subtitle_style))
    e.append(Paragraph(
        "Esta guía acompaña el uso de la herramienta web en "
        "<font color='#8a1e16'>ricardoruiz.co/ain.html</font>. Es el sexto módulo "
        "del Laboratorio de Políticas y opera sobre el estándar <b>Regulatory "
        "Impact Assessment (RIA)</b> de la OCDE (2012, revisión 2022), "
        "operacionalizado en Colombia por el <b>DNP</b> y <b>Función Pública</b> "
        "vía <b>Decreto 1081/2015</b> (proyectos normativos) y <b>Decreto 1273/2020</b> "
        "(consulta pública obligatoria). Marco teórico en Sunstein, Hahn-Tetlock, "
        "Stigler y Mashaw.",
        body_style))
    e.append(Spacer(1, 12))

    e.append(Paragraph("Contenido", h3_style))
    toc = [
        ["01", "Qué hace el módulo y para qué sirve"],
        ["02", "Mecánica 1 · problema regulatorio (tipo de falla)"],
        ["03", "Mecánica 2 · objetivos normativos (medibles)"],
        ["04", "Mecánica 3 · opciones regulatorias (6 familias)"],
        ["05", "Mecánica 4 · matriz de impactos"],
        ["06", "Mecánica 5 · consulta pública + riesgo regulatorio"],
        ["07", "Mecánica 6 · implementación + monitoreo + revisión"],
        ["08", "Copiloto IA (3 acciones)"],
        ["09", "Cómo encadenar con los demás módulos del lab"],
        ["10", "Ejemplo · regulación de pólizas de salud prepagada"],
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

    e.append(Paragraph("01 · Qué hace el módulo y para qué sirve", h2_style))
    e.append(Paragraph(
        "El AIN obliga a sustentar técnicamente un proyecto normativo "
        "<i>antes</i> de expedirlo. La mayoría de regulaciones falla no "
        "por mal diseño técnico sino por ausencia de tres preguntas "
        "previas: <i>¿por qué regular?</i>, <i>¿qué pasaría si no "
        "regulamos?</i>, <i>¿quién va a aguantar esta carga?</i>. El "
        "módulo te guía por las seis decisiones que separan una propuesta "
        "que se cae en consulta pública de una defendible ante comité "
        "técnico.",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Defender el proyecto ante Función Pública y el sector regulado.</b> Cuando puedes explicar qué falla del mercado justifica regular, qué opciones consideraste y por qué descartas las menos invasivas, dejas de ser tratado como burócrata expedidor y empiezas a ser tratado como diseñador técnico de la regulación.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Reducir el riesgo de captura, asimetría y carga excesiva.</b> Los tres factores que la literatura (Stigler 1971, Hahn-Tetlock 2008) identifica como predictores de fracaso regulatorio se hacen visibles antes de expedir, no después.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Producir un memo CONPES regulatorio formal.</b> El entregable final es un PDF con la estructura que la Oficina Jurídica espera + memo .md editable + matriz .csv.", list_style), leftIndent=15),
    ], bulletType='bullet'))

    e.append(Paragraph("02 · Mecánica 1 · problema regulatorio", h2_style))
    e.append(Paragraph(
        "Caracterizar el problema regulatorio significa tipificar <b>qué "
        "falla del mercado o problema de coordinación justifica la "
        "intervención del Estado</b>. La economía de la regulación (Pigou "
        "1920, Coase 1960, Stigler 1971, Akerlof 1970, Hayek 1945) "
        "identifica seis familias canónicas:",
        body_style))
    fallas = [
        ["Falla de mercado",        "Bienes públicos, externalidades agregadas, costos de transacción altos"],
        ["Externalidad",            "Costos/beneficios recaen en terceros (contaminación, congestión, vacunación)"],
        ["Asimetría de información","Una parte sabe lo que la otra no (Akerlof, Stiglitz). Selección adversa o riesgo moral"],
        ["Coordinación",            "Beneficio social > privado en estandarización, normas técnicas, redes"],
        ["Equidad distributiva",    "El mercado distribuye de forma socialmente inaceptable"],
        ["Monopolio natural",       "Costos fijos altos hacen ineficiente la competencia (servicios públicos en red)"],
    ]
    ft = Table([["Tipo de falla", "Definición"]] + fallas, colWidths=[4.8*cm, 10.2*cm])
    ft.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('TEXTCOLOR', (0,0), (-1,0), ACCENT),
        ('TEXTCOLOR', (0,1), (-1,-1), INK),
        ('BACKGROUND', (0,0), (-1,0), ACCENT_SOFT),
        ('LINEBELOW', (0,0), (-1,-1), 0.3, RULE),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    e.append(ft)
    e.append(Spacer(1, 6))
    e.append(Paragraph(
        "El campo de evidencia inicial cita estudios, sentencias, cifras "
        "oficiales — la consulta pública pregunta primero por esta "
        "evidencia. Si vienes del módulo de Problema Público, el módulo "
        "auto-importa el enunciado, afectados y evidencia con un click.",
        callout_style))

    e.append(Paragraph("03 · Mecánica 2 · objetivos normativos medibles", h2_style))
    e.append(Paragraph(
        "Cada objetivo normativo necesita cuatro campos: <b>enunciado, "
        "indicador, meta y plazo</b>. Sin estos cuatro no es objetivo "
        "sino intención política. La regulación responde a estos "
        "objetivos; los indicadores son los que se reportarán en la "
        "revisión a 24-36 meses.",
        body_style))
    e.append(Paragraph(
        "Entre 1 y 5 objetivos. Más vuelve la regulación inmanejable y "
        "difumina la responsabilidad institucional.",
        body_style))

    e.append(Paragraph("04 · Mecánica 3 · opciones regulatorias", h2_style))
    e.append(Paragraph(
        "Cass Sunstein (<i>Simpler: The Future of Government</i>, 2013) "
        "insiste en que el regulador moderno debe considerar al menos "
        "seis familias de opciones. La regulación directa rara vez gana "
        "el análisis costo-beneficio:",
        body_style))
    opc_tab = [
        ["statu-quo",         "Baseline obligatorio. No expedir norma nueva"],
        ["regular",           "Regulación directa con obligaciones y régimen sancionatorio"],
        ["autorregulación",   "El gremio regulado define y supervisa sus propios estándares"],
        ["co-regulación",     "Estado define principios; el gremio implementa y supervisa"],
        ["sandbox",           "Marco experimental temporal con licencia para innovar"],
        ["instr-mercado",     "Impuesto pigouviano, cuotas transables, subsidio, etiquetado obligatorio"],
    ]
    ot = Table([["Tipo", "Definición"]] + opc_tab, colWidths=[3.8*cm, 11.2*cm])
    ot.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('TEXTCOLOR', (0,0), (-1,0), ACCENT),
        ('TEXTCOLOR', (0,1), (-1,-1), INK),
        ('BACKGROUND', (0,0), (-1,0), ACCENT_SOFT),
        ('LINEBELOW', (0,0), (-1,-1), 0.3, RULE),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    e.append(ot)
    e.append(Spacer(1, 6))
    e.append(Paragraph(
        "Si ya tienes alternativas analizadas en el módulo de "
        "<b>Alternativas</b> (Zwicky · Lempert · Ritchey), el AIN las "
        "auto-importa como opciones regulatorias con un click. Las "
        "alternativas del módulo morfológico tienen mucho mejor "
        "exploración del espacio de diseño; el AIN sólo añade la "
        "tipología regulatoria.",
        callout_style))

    e.append(Paragraph("05 · Mecánica 4 · matriz de impactos", h2_style))
    e.append(Paragraph(
        "Matriz <b>opciones × 5 categorías de impacto</b> con escala "
        "cualitativa bajo / medio / alto / muy alto:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Costos directos al regulado:</b> lo que tendrá que pagar/invertir por cumplir. Invertido: bajo = mejor.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Costos indirectos / cumplimiento:</b> asesoría legal, ajuste de procesos, capacitación, sistemas. Invertido.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Beneficios esperados:</b> beneficio social agregado de la opción. Directo: alto = mejor.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Riesgo de captura:</b> probabilidad de que el regulador termine sirviendo al regulado. Invertido.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Carga administrativa al Estado:</b> costo público de supervisar e implementar. Invertido.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "Score agregado por opción = <em>beneficios − promedio de costos y riesgos</em>. "
        "Score más alto = mejor opción. La opción ganadora se highlightea "
        "automáticamente en la tabla y en el memo CONPES final.",
        callout_style))

    e.append(Paragraph("06 · Mecánica 5 · consulta pública + riesgo regulatorio", h2_style))
    e.append(Paragraph(
        "El Decreto 1273 de 2020 hace obligatoria la consulta pública "
        "sobre proyectos normativos. Pero la consulta sirve poco si llega "
        "al final y sólo abre la página web. El módulo planifica la "
        "consulta como insumo del diseño:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Audiencias clave</b> (chips): stakeholders a consultar — gremio regulado, beneficiarios, sociedad civil, organismos técnicos. Cobertura representativa.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Instrumentos</b> (multi-select): foro público, consulta web (Decreto 1273), mesa técnica, audiencia pública, audiencia Congreso, panel expertos, encuesta usuarios. Combina al menos dos.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Cronograma</b>: tiempos por instrumento y secuencia. Mínimo 15 días para comentarios web (Decreto 1273).", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "Hahn &amp; Tetlock (<i>JEP</i>, 2008) identificaron <b>cinco "
        "riesgos regulatorios</b> que predicen fracaso. El AIN los evalúa "
        "como bajo/medio/alto con el copiloto IA:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Captura del regulador</b> (Stigler 1971): regulador termina sirviendo al regulado.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Asimetría de información</b>: supervisor no tiene la info técnica que el regulado sí.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Carga excesiva</b>: costo de cumplimiento supera beneficio social.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Fragmentación normativa</b>: contradicción/solapamiento con normas vigentes.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Obsolescencia tecnológica</b>: rigidez vs. cambio del sector regulado.", list_style), leftIndent=15),
    ], bulletType='bullet'))

    e.append(Paragraph("07 · Mecánica 6 · implementación + monitoreo + revisión", h2_style))
    e.append(Paragraph(
        "Una regulación sin cláusula de revisión es un compromiso "
        "vitalicio. El AIN cierra con cinco campos: cronograma de "
        "implementación, responsables institucionales, presupuesto "
        "estimado, indicadores de monitoreo y <b>cláusula de revisión "
        "explícita</b> (24-36 meses típico) con criterio cuantitativo "
        "para mantener / ajustar / derogar.",
        body_style))
    e.append(Paragraph(
        "El campo de cláusula de revisión es lo que distingue un "
        "proyecto normativo profesional del decreto que entra en "
        "vigor y nadie revisa: <i>\"si el indicador X no llega al Y% "
        "en el plazo Z, la norma se ajusta o se deroga\"</i>.",
        callout_style))

    e.append(Paragraph("08 · Copiloto IA (3 acciones)", h2_style))
    e.append(Paragraph(
        "Tres acciones del copiloto IA distribuidas en el flow:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Sugerir opciones regulatorias</b> (Pro+) · paso 3. Dado el problema y los objetivos, propone 4-6 opciones cubriendo al menos 4 familias distintas con descripción operativa y justificación.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Detectar riesgos regulatorios</b> (Premium+) · paso 5. Estima los 5 riesgos canónicos (Hahn-Tetlock + Stigler) como bajo/medio/alto con justificación por dimensión y mitigaciones sugeridas. Botón \"Adoptar\" para inyectar al state.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Narrativa AIN</b> (Premium+) · paso final. Redacta el informe estilo DNP con justificación del problema + justificación de la recomendación + objeciones anticipadas en consulta + mitigaciones de riesgo + condiciones para reconsiderar.", list_style), leftIndent=15),
    ], bulletType='bullet'))

    e.append(Paragraph("09 · Cómo encadenar con los demás módulos del lab", h2_style))
    e.append(Paragraph(
        "El AIN cierra el ciclo del lab cuando el entregable final es "
        "una norma. Cuándo encadenar:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Antes:</b> empieza por <i>Problema Público</i> si todavía no enmarcaste el problema. El AIN auto-importa el enunciado, afectados y evidencia.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Antes (alternativo):</b> si ya hiciste análisis morfológico en <i>Alternativas</i>, el AIN auto-importa esas alternativas como opciones regulatorias.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Paralelo:</b> <i>Mactor</i> mapea actores con poder regulatorio (gremio, Congreso, sociedad civil) — útil para diseñar la consulta pública y anticipar el riesgo de captura.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Después:</b> envía la opción recomendada + objetivos + indicadores al módulo <i>Evaluación</i> para diseñar el M&amp;E formal de la regulación. Cierre natural del ciclo.", list_style), leftIndent=15),
    ], bulletType='bullet'))

    e.append(Paragraph("10 · Ejemplo · regulación de pólizas de salud prepagada", h2_style))
    e.append(Paragraph(
        "Problema regulatorio (paso 1):",
        body_style))
    e.append(Paragraph(
        "Asimetría de información entre proveedores y consumidores en el "
        "mercado de medicina prepagada produce contratos opacos y "
        "dispersión de precios del 80% para servicios equivalentes. "
        "Tipo de falla: asimetría de información. Evidencia: Superfinanciera "
        "(12.4M reclamos 2024), Fedesarrollo (dispersión de precios 2023), "
        "Corte Constitucional (sentencia C-313/2014).",
        example_style))
    e.append(Paragraph("<b>Objetivos (paso 2):</b>", body_style))
    e.append(Paragraph(
        "(1) Estandarizar cláusulas contractuales — meta 100% pólizas en 24m. "
        "(2) Reducir dispersión de precios para procedimientos equivalentes "
        "&lt; 20% — plazo 36m.",
        example_style))
    e.append(Paragraph("<b>Opciones (paso 3):</b>", body_style))
    e.append(Paragraph(
        "Statu quo (baseline) · regulación directa con cláusulas obligatorias · "
        "autorregulación con esquema Fasecolda · co-regulación con CRC + "
        "Superfinanciera · etiquetado obligatorio (instrumento de mercado).",
        example_style))
    e.append(Paragraph("<b>Matriz (paso 4):</b>", body_style))
    e.append(Paragraph(
        "La co-regulación gana score 0.75: alto beneficio (3 → estandarización + "
        "transparencia precios) con costos directos medios (2), costos "
        "indirectos medios (2), captura medio (2), carga admin medio (2). "
        "Score = 3 − 2 = +1 luego ajustado por probabilidad.",
        example_style))
    e.append(Paragraph("<b>Consulta + riesgo (paso 5):</b>", body_style))
    e.append(Paragraph(
        "Audiencias: ANDI, Fasecolda, EPS, defensorías del consumidor, "
        "Superfinanciera, CRC, Asocajas. Instrumentos: foro técnico + consulta "
        "web 30 días + mesa con consumidores. Riesgo: captura medio (mitigable con "
        "panel técnico balanceado), asimetría alto (mitigable con auditoría "
        "externa periódica).",
        example_style))
    e.append(Paragraph("<b>Implementación (paso 6):</b>", body_style))
    e.append(Paragraph(
        "Cronograma: M0 publicación; M1-3 socialización; M4-6 transitorio; "
        "M7 vigencia plena; M30 revisión. Presupuesto: 4.500 millones COP año 1 "
        "(8 inspectores Supersalud + sistemas) + 1.800 anuales operación. "
        "Cláusula: si % pólizas estandarizadas &lt; 80% al M30, ajustar; "
        "si &lt; 50%, derogar.",
        example_style))

    e.append(Spacer(1, 8))
    e.append(Paragraph(
        "Tiempo aproximado de un AIN bien hecho: 4 a 12 horas. Vale la "
        "pena cuando la regulación es nueva, costosa de cumplir o "
        "afecta a sector concentrado.",
        callout_style))

    doc.build(e, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"✓ Generado: {OUT}")
    print(f"  Tamaño: {OUT.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    build()
