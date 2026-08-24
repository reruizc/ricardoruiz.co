"""
Genera 'Análisis de Impacto Normativo · Respaldo académico'.
Marco teórico, fórmulas, bibliografía 26 refs.
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
RULE = HexColor("#14110a40")

OUT_DIR = Path(__file__).resolve().parents[2] / "Bases de datos" / "ain"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "respaldo-academico.pdf"

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
ref_style = ParagraphStyle('ref', parent=body_style, fontSize=9.5, leading=13, spaceAfter=4, leftIndent=12, firstLineIndent=-12)
list_style = ParagraphStyle('list', parent=body_style, leftIndent=0, spaceAfter=4)
callout_style = ParagraphStyle('callout', parent=body_style, fontName='Helvetica-Oblique',
    fontSize=9.5, leading=13, textColor=INK_2, leftIndent=10)
formula_style = ParagraphStyle('formula', parent=body_style, fontName='Courier',
    fontSize=10, leading=14, textColor=INK, leftIndent=12, spaceBefore=4, spaceAfter=6)

def header_footer(c, doc):
    c.saveState()
    c.setStrokeColor(RULE); c.setLineWidth(0.5)
    c.line(doc.leftMargin, letter[1]-1.1*cm, letter[0]-doc.rightMargin, letter[1]-1.1*cm)
    c.setFillColor(INK_3); c.setFont("Helvetica", 8)
    c.drawString(doc.leftMargin, letter[1]-1.4*cm, "Análisis de Impacto Normativo · Ricardo Ruiz")
    c.drawRightString(letter[0]-doc.rightMargin, letter[1]-1.4*cm, "Respaldo académico · v1.0 · mayo 2026")
    c.line(doc.leftMargin, 1.3*cm, letter[0]-doc.rightMargin, 1.3*cm)
    c.drawString(doc.leftMargin, 0.9*cm, "ricardoruiz.co · consultoría en datos y política pública")
    c.drawRightString(letter[0]-doc.rightMargin, 0.9*cm, f"Página {doc.page}")
    c.restoreState()

def build():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=2.0*cm, bottomMargin=1.9*cm,
        title="Análisis de Impacto Normativo · Respaldo académico",
        author="Ricardo Ruiz · ricardoruiz.co",
        subject="Marco teórico, fórmulas y bibliografía del módulo AIN del Lab"
    )
    e = []

    e.append(Paragraph("Análisis de Impacto Normativo", title_style))
    e.append(Paragraph("Respaldo académico · marco teórico, fórmulas y bibliografía", subtitle_style))
    e.append(Paragraph(
        "Este documento sostiene metodológicamente las seis mecánicas del módulo "
        "web AIN. Cubre la justificación de cada decisión de diseño, las fórmulas "
        "usadas y las referencias completas. Pensado para consultores y "
        "Oficinas Jurídicas que quieran auditar el método.",
        body_style))

    e.append(Paragraph("1 · Marco general del módulo", h2_style))
    e.append(Paragraph(
        "El módulo opera sobre el estándar <b>Regulatory Impact Assessment</b> "
        "(RIA) consolidado por la <b>OCDE</b> en su <i>Recommendation on "
        "Regulatory Policy and Governance</i> (2012, revisión 2022) y "
        "adoptado por casi todos los países miembros como obligatorio para "
        "proyectos normativos de impacto significativo.",
        body_style))
    e.append(Paragraph(
        "En Colombia el AIN está reglado por el <b>Decreto 1081 de 2015</b> "
        "(proyectos normativos) y el <b>Decreto 1273 de 2020</b> (consulta "
        "pública obligatoria sobre proyectos normativos). El DNP y Función "
        "Pública han producido guías operativas. Marco teórico anclado en "
        "Pigou, Coase, Stigler, Akerlof, Hayek, Sunstein, Hahn-Tetlock y "
        "Mashaw.",
        body_style))
    e.append(Paragraph(
        "El módulo NO certifica el cumplimiento de los decretos colombianos — "
        "eso lo hace Función Pública. Lo que produce es el insumo técnico que "
        "alimenta el trámite formal: memo CONPES regulatorio con la "
        "estructura que la Oficina Jurídica espera.",
        callout_style))

    e.append(Paragraph("2 · Caracterización del problema regulatorio (mecánica 1)", h2_style))
    e.append(Paragraph(
        "La economía de la regulación parte de la pregunta normativa "
        "<i>¿por qué intervenir?</i>. La respuesta canónica identifica seis "
        "familias de justificaciones:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Falla de mercado</b> (Pigou 1920): el equilibrio competitivo no maximiza el bienestar agregado por bienes públicos, externalidades agregadas o costos de transacción altos.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Externalidad</b> (Coase 1960): costos o beneficios de una transacción recaen en terceros que no son parte. Caso clásico: contaminación, congestión, vacunación, educación.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Asimetría de información</b> (Akerlof 1970, Stiglitz): una parte sabe lo que la otra no. Produce selección adversa (Akerlof 1970 sobre mercado de limones) o riesgo moral (Stiglitz sobre seguros).", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Problema de coordinación</b> (Schelling): el beneficio social de estandarizar supera al privado. Casos: normas técnicas, redes ferroviarias, sistemas de identificación.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Equidad distributiva</b>: el mercado distribuye recursos de forma que el Estado considera socialmente inaceptable. Justifica subsidios, redistribución, mínimos vitales.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Monopolio natural</b>: costos fijos hacen ineficiente la competencia. Casos: servicios públicos en red (acueducto, eléctrico, gas).", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "Sin esta tipificación explícita, el proyecto normativo es opinión "
        "política sin sustento técnico. El AIN exige el campo de tipo de "
        "falla como obligatorio.",
        callout_style))

    e.append(Paragraph("3 · Objetivos normativos medibles (mecánica 2)", h2_style))
    e.append(Paragraph(
        "Cada objetivo normativo necesita cuatro campos canónicos: "
        "<b>enunciado · indicador · meta · plazo</b>. Sin estos cuatro no es "
        "objetivo: es intención política. Estos son los mismos cuatro "
        "campos que la evaluación posterior (módulo Evaluación) usará como "
        "input para diseñar el M&amp;E. La trazabilidad objetivo → "
        "indicador → revisión es lo que permite cerrar el ciclo regulatorio "
        "con cláusula de revisión auditable.",
        body_style))

    e.append(Paragraph("4 · Opciones regulatorias (mecánica 3)", h2_style))
    e.append(Paragraph(
        "<b>Sunstein</b> (<i>Simpler: The Future of Government</i>, 2013) "
        "elevó la pregunta de <i>qué regular</i> a <i>cómo regular</i>. "
        "Propuso considerar al menos seis familias de opciones, con "
        "<b>statu quo</b> obligatorio como baseline (sin él, no hay "
        "marginal sobre el cual evaluar):",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Regulación directa</b>: obligaciones específicas + régimen sancionatorio. Ejemplo: prohibición, licencia, estándar técnico obligatorio.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Autorregulación</b>: el gremio regulado define sus estándares. Ejemplo: códigos de ética, FASB en contabilidad, FIFA en deporte.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Co-regulación</b>: Estado define principios; el gremio implementa y supervisa. Ejemplo: regulación financiera con FNG + Superfinanciera.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Sandbox regulatorio</b>: marco experimental temporal con licencia para innovar. Ejemplo: FinTech sandbox Superfinanciera, Helsinki Smart Mobility.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Instrumento de mercado</b>: impuesto pigouviano, cuotas transables, subsidio, etiquetado obligatorio. Ejemplo: impuesto al carbono, cuotas de emisión.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "Thaler &amp; Sunstein (<i>Nudge</i>, 2008) mostraron que las "
        "opciones menos invasivas (transparencia obligatoria, default "
        "automático, etiquetado) suelen ganar el análisis costo-beneficio "
        "sobre la regulación directa clásica.",
        callout_style))

    e.append(Paragraph("5 · Matriz de impactos (mecánica 4)", h2_style))
    e.append(Paragraph(
        "Matriz <b>opciones × 5 categorías</b> con escala cualitativa B/M/A/MA. "
        "El score agregado por opción se calcula como:",
        body_style))
    e.append(Paragraph("score = beneficios − promedio(costos_directos, costos_indirectos, captura, carga_admin)", formula_style))
    e.append(Paragraph(
        "donde cada nivel cualitativo se mapea a puntos enteros: bajo=1, "
        "medio=2, alto=3, muy-alto=4. La opción con score más alto se "
        "highlightea como ganadora. La escala invertida (más bajo = mejor) "
        "para costos, captura y carga administrativa, se compensa "
        "matemáticamente: como entran restando, un valor alto en costos "
        "reduce el score.",
        body_style))
    e.append(Paragraph(
        "El score es una <em>guía cualitativa</em>, no un análisis "
        "costo-beneficio monetizado. Para CBA social riguroso con tasa de "
        "descuento social DNP, weights distribucionales y precios sombra, "
        "el AIN se complementa con el módulo de Alternativas (lente "
        "económica MVPF/CEA) o con la metodología del Green Book HM "
        "Treasury.",
        callout_style))

    e.append(Paragraph("6 · Consulta pública + riesgo regulatorio (mecánica 5)", h2_style))
    e.append(Paragraph(
        "<b>Hahn &amp; Tetlock</b> (<i>Has Economic Analysis Improved "
        "Regulatory Decisions?</i>, JEP 2008) revisaron sistemáticamente la "
        "literatura sobre regulación y concluyeron que el factor que más "
        "predice fracaso regulatorio no es el diseño técnico sino cinco "
        "riesgos cualitativos:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Captura del regulador</b> (Stigler 1971): el regulado termina influyendo en la regulación que se le aplica. Más probable si el sector regulado es concentrado, si hay puerta giratoria con el supervisor, si el supervisor depende informacionalmente del regulado.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Asimetría de información</b>: el supervisor no tiene la info técnica que el regulado sí. Más alto en tecnologías complejas, mercados sofisticados, regulación científica.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Carga excesiva</b>: costo de cumplimiento supera el beneficio social. Asfixia al sector formal y empuja a informalidad.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Fragmentación normativa</b>: la norma nueva contradice o se solapa con normas vigentes. Multiplica costos legales.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Obsolescencia tecnológica</b>: la rigidez de la norma queda obsoleta frente a cambios rápidos del sector regulado.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "El módulo evalúa cada dimensión como bajo / medio / alto, con "
        "asistencia del copiloto IA que estima el nivel a partir del "
        "contexto y propone mitigaciones específicas.",
        body_style))
    e.append(Paragraph(
        "<b>Plan de consulta</b>: el Decreto 1273 de 2020 hizo obligatoria "
        "la consulta pública sobre proyectos normativos. Pero como advirtió "
        "Mashaw (<i>Reasoned Administration and Democratic Legitimacy</i>, "
        "2018), la consulta sirve poco si se hace al final. El AIN la "
        "planifica desde el diseño con audiencias clave + instrumentos + "
        "cronograma. Mínimo 15 días para comentarios web (Decreto 1273).",
        body_style))

    e.append(Paragraph("7 · Implementación + cláusula de revisión (mecánica 6)", h2_style))
    e.append(Paragraph(
        "Una regulación sin cláusula de revisión es un compromiso "
        "vitalicio. El AIN cierra con cinco campos:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Cronograma de implementación:</b> hitos desde publicación hasta vigencia plena, con período de transición si aplica.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Responsables institucionales:</b> quién implementa, quién supervisa, quién audita.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Presupuesto estimado:</b> costo público diferenciando inversión inicial vs operación recurrente, con fuente de financiación.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Indicadores de monitoreo:</b> 3-5 indicadores con meta y plazo. Son los que se reportarán en la revisión.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Cláusula de revisión:</b> fecha explícita (24-36 meses) + criterio cuantitativo para mantener / ajustar / derogar.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "La cláusula de revisión cuantitativa es lo que diferencia un AIN "
        "profesional del decreto que entra en vigor y nadie revisa: <i>\"si "
        "el indicador X no llega al Y% en el plazo Z, la norma se ajusta o "
        "se deroga\"</i>.",
        callout_style))

    e.append(Paragraph("8 · Limitaciones conocidas", h2_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Escala cualitativa.</b> La matriz de impactos usa B/M/A/MA, no valoración monetaria. Para CBA social riguroso, complementar con módulo de Alternativas (lente MVPF/CEA) o con metodología externa (Green Book HM Treasury, MGA DNP).", list_style), leftIndent=15),
        ListItem(Paragraph("<b>5 riesgos canónicos.</b> Hahn-Tetlock identifican 5 dimensiones; existen más en la literatura (Posner sobre rent-seeking, Olson sobre acción colectiva). El AIN se limita a las 5 más operativas.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Sin árbol regulatorio.</b> Algunos AIN sofisticados (OECD Better Regulation, OIRA EE.UU.) modelan un árbol de decisión regulatorio con probabilidades. El AIN del lab opera lineal por simplicidad.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>No certifica.</b> El AIN no certifica cumplimiento del Decreto 1081/2015 o 1273/2020. Eso lo hace Función Pública. Lo que produce es el insumo técnico que alimenta el trámite.", list_style), leftIndent=15),
    ], bulletType='bullet'))

    e.append(Paragraph("9 · Bibliografía", h2_style))
    refs = [
        "Akerlof, G. A. (1970). <i>The Market for \"Lemons\": Quality Uncertainty and the Market Mechanism</i>. Quarterly Journal of Economics 84(3): 488-500.",
        "Coase, R. H. (1960). <i>The Problem of Social Cost</i>. Journal of Law and Economics 3: 1-44.",
        "DNP / Función Pública (2017). <i>Guía de Análisis de Impacto Normativo en Colombia</i>. Bogotá. Actualización 2020.",
        "Decreto 1081 de 2015 — proyectos normativos. Presidencia de la República, Colombia.",
        "Decreto 1273 de 2020 — consulta pública obligatoria sobre proyectos normativos. Presidencia de la República, Colombia.",
        "Hahn, R. W., &amp; Tetlock, P. C. (2008). <i>Has Economic Analysis Improved Regulatory Decisions?</i> Journal of Economic Perspectives 22(1): 67-84.",
        "Hayek, F. A. (1945). <i>The Use of Knowledge in Society</i>. American Economic Review 35(4): 519-530.",
        "Howlett, M., &amp; Mukherjee, I. (eds.) (2017). <i>Handbook of Policy Formulation</i>. Edward Elgar.",
        "Mashaw, J. L. (2018). <i>Reasoned Administration and Democratic Legitimacy: How Administrative Law Supports Democratic Government</i>. Cambridge University Press.",
        "OECD (2012). <i>Recommendation of the Council on Regulatory Policy and Governance</i>. París: OECD Publishing. Revisión 2022.",
        "OECD (2020). <i>OECD Best Practice Principles on Regulatory Policy: Regulatory Impact Assessment</i>. París: OECD Publishing.",
        "Olson, M. (1965). <i>The Logic of Collective Action</i>. Harvard University Press.",
        "OIRA / Office of Information and Regulatory Affairs (2003). <i>Circular A-4: Regulatory Analysis</i>. White House, EE.UU.",
        "Pigou, A. C. (1920). <i>The Economics of Welfare</i>. Macmillan.",
        "Posner, R. A. (1974). <i>Theories of Economic Regulation</i>. Bell Journal of Economics 5(2): 335-358.",
        "Salamon, L. M. (ed.) (2002). <i>The Tools of Government: A Guide to the New Governance</i>. Oxford University Press.",
        "Schelling, T. C. (1978). <i>Micromotives and Macrobehavior</i>. Norton.",
        "Stigler, G. J. (1971). <i>The Theory of Economic Regulation</i>. Bell Journal of Economics 2(1): 3-21. — teoría de la captura del regulador.",
        "Stiglitz, J. E. (2002). <i>Information and the Change in the Paradigm in Economics</i>. American Economic Review 92(3): 460-501.",
        "Sunstein, C. R. (2013). <i>Simpler: The Future of Government</i>. Simon &amp; Schuster.",
        "Sunstein, C. R. (2014). <i>The Cost-Benefit State: The Future of Regulatory Protection</i>. American Bar Association.",
        "Thaler, R. H., &amp; Sunstein, C. R. (2008). <i>Nudge: Improving Decisions About Health, Wealth, and Happiness</i>. Yale University Press.",
        "Torres-Melo, J., &amp; Santander, J. (2013). <i>Introducción a las políticas públicas: Conceptos y herramientas desde la relación entre Estado y ciudadanía</i>. IEMP-Procuraduría.",
        "Weimer, D. L., &amp; Vining, A. R. (2017). <i>Policy Analysis: Concepts and Practice</i>. 6ª ed. Routledge.",
        "Wiener, J. B., &amp; Ribeiro, B. R. (2016). <i>Impact Assessment: Diffusion and Integration</i>. En Drechsler, Greiling, Halsbenning (eds.), <i>Handbook of Administrative Sciences</i>. Springer.",
        "World Bank (2020). <i>Global Indicators of Regulatory Governance</i>. Washington DC: World Bank Group.",
    ]
    for r in refs:
        e.append(Paragraph(r, ref_style))

    e.append(Spacer(1, 10))
    e.append(Paragraph(
        "Si encuentras una referencia rota, una versión más reciente o quieres "
        "sugerir un autor para una mecánica específica, escribe a "
        "<font color='#8a1e16'>reruizc@gmail.com</font>.",
        callout_style))

    doc.build(e, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"✓ Generado: {OUT}")
    print(f"  Tamaño: {OUT.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    build()
