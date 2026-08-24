"""
Genera el PDF 'Escenarios Prospectivos · Respaldo académico' (Sprint F.D.3).
Marco teórico, fórmulas básicas y bibliografía de las escuelas combinadas.
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

OUT_DIR = Path(__file__).resolve().parents[2] / "Bases de datos" / "prospect"
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

def header_footer(c, doc):
    c.saveState()
    c.setStrokeColor(RULE); c.setLineWidth(0.5)
    c.line(doc.leftMargin, letter[1]-1.1*cm, letter[0]-doc.rightMargin, letter[1]-1.1*cm)
    c.setFillColor(INK_3); c.setFont("Helvetica", 8)
    c.drawString(doc.leftMargin, letter[1]-1.4*cm, "Escenarios Prospectivos · Ricardo Ruiz")
    c.drawRightString(letter[0]-doc.rightMargin, letter[1]-1.4*cm, "Respaldo académico · v1.0 · mayo 2026")
    c.line(doc.leftMargin, 1.3*cm, letter[0]-doc.rightMargin, 1.3*cm)
    c.drawString(doc.leftMargin, 0.9*cm, "ricardoruiz.co · consultoría en datos y política pública")
    c.drawRightString(letter[0]-doc.rightMargin, 0.9*cm, f"Página {doc.page}")
    c.restoreState()

def build():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=2.0*cm, bottomMargin=1.9*cm,
        title="Escenarios Prospectivos · Respaldo académico",
        author="Ricardo Ruiz · ricardoruiz.co",
        subject="Marco teórico de la prospectiva estratégica y construcción de escenarios"
    )
    e = []

    e.append(Paragraph("Escenarios Prospectivos", title_style))
    e.append(Paragraph("Respaldo académico · marco teórico, fórmulas y bibliografía", subtitle_style))
    e.append(Paragraph(
        "Este documento sostiene metodológicamente las cuatro mecánicas del módulo de "
        "Escenarios Prospectivos. Cubre la justificación de cada decisión de diseño, las "
        "fórmulas usadas y las referencias completas. Pensado para consultores y comités "
        "técnicos que quieran auditar el método.",
        body_style))

    e.append(Paragraph("1 · El campo de la prospectiva estratégica", h2_style))
    e.append(Paragraph(
        "La prospectiva estratégica se diferencia de la planificación tradicional en una "
        "premisa básica: el futuro no es único ni predecible. Las herramientas que veremos "
        "son <i>productoras de futuros</i> antes que predictoras. El módulo combina dos "
        "tradiciones complementarias:",
        body_style))
    e.append(Paragraph("La tradición francesa (Godet · LIPSOR · CNAM)", h3_style))
    e.append(Paragraph(
        "Iniciada en los 1970s por Michel Godet en el CNAM (París), formaliza la "
        "prospectiva en una secuencia de instrumentos: análisis estructural (MicMac), "
        "análisis de actores (Mactor), análisis morfológico (MorPhol), y análisis "
        "multipolar de futuros (MultiPol). El énfasis está en la <b>identificación de "
        "variables motrices</b> y la <b>narrativa rica de escenarios</b>. En Colombia, "
        "Francisco José Mojica (Universidad Externado, formado en la Sorbona) es el "
        "principal exponente; el método estructura buena parte de los ejercicios de "
        "Visión Colombia 2025 y planes prospectivos del DNP.",
        body_style))
    e.append(Paragraph("La tradición anglo-corporativa (Schwartz · GBN · Shell)", h3_style))
    e.append(Paragraph(
        "Peter Schwartz, formado en SRI International y luego cofundador de Global "
        "Business Network (GBN), popularizó en <i>The Art of the Long View</i> (1991) "
        "el método de los ejes de incertidumbre: identificar las <b>dos incertidumbres "
        "críticas</b> que estructuran el espacio de futuros y construir cuatro escenarios "
        "por intersección. La tradición se origina en los ejercicios prospectivos de "
        "Royal Dutch Shell en los 1970s (Pierre Wack) y se difundió a planificación "
        "estratégica corporativa, militar e inteligencia gubernamental.",
        body_style))
    e.append(Paragraph("El marco RAND para incertidumbre profunda (Lempert · Walker)", h3_style))
    e.append(Paragraph(
        "Robert Lempert y Warren Walker, en <i>Shaping the Next One Hundred Years</i> "
        "(RAND 2003), formalizaron el Robust Decision Making (RDM): cuando la "
        "incertidumbre es <b>profunda</b> (no se puede asignar probabilidad con "
        "confianza), la decisión óptima no es la de máxima esperanza, es la "
        "<b>robusta</b> — aquella que aguanta en múltiples escenarios sin pérdidas "
        "catastróficas. Es la base teórica del concepto «no-regret» que usa el módulo.",
        body_style))

    e.append(Paragraph("2 · Mecánica 1 · identificación de incertidumbres críticas", h2_style))
    e.append(Paragraph(
        "El módulo opera con dos ejes porque <b>2 incertidumbres × 2 polos = 4 cuadrantes</b>, "
        "el número manejable para narrativa rica. Con más ejes la combinatoria explota "
        "(3 ejes → 8 escenarios, intractable). El usuario debe priorizar las dos "
        "incertidumbres que cumplen simultáneamente:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Alta importancia</b> para el resultado de la política — variable motriz del sistema (en el sentido MicMac).", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Alta incertidumbre</b> — no se puede predecir su valor en el horizonte de la política con confianza ≥80%.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "Para apoyar esta selección, el módulo conecta con análisis estructural: si el "
        "usuario ya levantó MicMac, la fórmula identifica las dos variables con mayor "
        "<b>motricidad directa</b> (suma de filas en valor absoluto de la matriz de "
        "influencias) y las sugiere como candidatas a ejes:",
        body_style))
    e.append(Paragraph(
        "M_i = Σ_j |M[i,j]| &nbsp;&nbsp; (motricidad de variable i)",
        callout_style))
    e.append(Paragraph(
        "Cada incertidumbre se describe por sus dos polos (positivo / negativo). El "
        "nombre del polo es <i>descriptivo</i>, no normativo — el juicio sobre cuál es "
        "deseable se hace en la fase de cross-impact, no en la identificación.",
        body_style))

    e.append(Paragraph("3 · Mecánica 2 · construcción y narrativa de escenarios", h2_style))
    e.append(Paragraph(
        "Cada cuadrante combina un polo de cada eje. Convención del módulo: <b>NE</b> = "
        "ambos polos positivos, <b>NO</b> = X neg + Y pos, <b>SO</b> = ambos negativos, "
        "<b>SE</b> = X pos + Y neg. La probabilidad subjetiva por cuadrante debe sumar "
        "100% (warning suave si no, no bloqueo).",
        body_style))
    e.append(Paragraph(
        "Reglas clásicas de Schwartz (1996) para una narrativa creíble: (1) los escenarios "
        "deben ser <i>plausibles</i> (no catastrofismo, no utopía); (2) <i>internamente "
        "consistentes</i> (todas las piezas del escenario encajan); (3) <i>relevantes</i> "
        "para la decisión; (4) <i>desafiantes</i> de los supuestos del decisor; (5) "
        "<i>distintos</i> entre sí (si dos escenarios son demasiado parecidos, los ejes "
        "están mal elegidos).",
        body_style))
    e.append(Paragraph(
        "El módulo no impone un esquema temporal — el horizonte (2030, 2040) lo decide "
        "el usuario en función de la política. Para reformas estructurales típicamente "
        "10-15 años; para regulaciones, 3-5 años.",
        callout_style))

    e.append(Paragraph("4 · Mecánica 3 · cross-impact analysis", h2_style))
    e.append(Paragraph(
        "El cross-impact analysis fue propuesto por Theodore Gordon y Olaf Helmer (RAND "
        "1966; refinado por Gordon &amp; Hayward 1968) para medir cómo la ocurrencia de "
        "un evento altera la probabilidad de otros. El módulo aplica una versión "
        "simplificada: por cada par <i>(elemento, escenario)</i>, se asigna un valor en "
        "la escala <b>{-2, -1, 0, +1, +2}</b> que indica cómo se mueve el elemento si "
        "ese escenario se materializa:",
        body_style))
    impact = [
        ["Valor", "Interpretación",                                          "Ejemplo"],
        ["-2",    "Se debilita fuertemente / pierde viabilidad casi total",  "Política de transferencias en pesimismo fiscal"],
        ["-1",    "Se debilita",                                              "Cobertura universal en pesimismo demográfico"],
        ["0",     "Neutral",                                                  "Variable independiente del cuadrante"],
        ["+1",    "Se fortalece",                                              "Política digital en escenario de adopción tecnológica acelerada"],
        ["+2",    "Se fortalece fuertemente / se vuelve dominante",          "Energías renovables en cuadrante de altos precios fósiles"],
    ]
    it = Table(impact, colWidths=[1.4*cm, 6.0*cm, 8.0*cm])
    it.setStyle(TableStyle([
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
    e.append(it)
    e.append(Spacer(1, 6))
    e.append(Paragraph(
        "Los elementos que se cruzan provienen de los otros módulos del lab: variables "
        "del análisis estructural, actores del Mactor, alternativas del análisis de "
        "alternativas. El módulo auto-importa estos elementos desde localStorage.",
        body_style))

    e.append(Paragraph("5 · Mecánica 4 · decisiones no-regret + señales tempranas", h2_style))
    e.append(Paragraph(
        "Una alternativa es <b>no-regret</b> (Lempert &amp; Walker 2003) si tiene impacto "
        "<i>positivo o neutro</i> en al menos 3 de los 4 escenarios. Es decir, no falla "
        "catastróficamente en ninguno y se beneficia en la mayoría. Formalmente:",
        body_style))
    e.append(Paragraph(
        "no-regret(alt) = |{s ∈ S : impacto(alt, s) ≥ +1}| ≥ 3 &nbsp;&nbsp; "
        "donde S = {NE, NO, SO, SE}",
        callout_style))
    e.append(Paragraph(
        "El módulo identifica automáticamente las alternativas no-regret con badge "
        "<b>«✓ NO-REGRET»</b> y las prioriza en el ranking final. Sin embargo, el método "
        "RDM no recomienda elegir <i>solo</i> no-regret a costa de todo: a veces hay "
        "razones legítimas para aceptar más riesgo a cambio de mayor ganancia esperada. "
        "El módulo te pide documentar la <b>justificación</b> y un <b>plan de "
        "contingencia</b> si la alternativa elegida no es perfectamente robusta.",
        body_style))
    e.append(Paragraph("Señales tempranas y vigilancia estratégica", h3_style))
    e.append(Paragraph(
        "El componente que distingue una prospectiva ejecutiva de una académica es la "
        "<b>vigilancia estratégica</b> (Godet 2007): para cada escenario, identificar "
        "indicadores que se moverían si ese futuro se está materializando. Si la política "
        "tiene un sistema de monitoreo (evaluación), las señales tempranas se cruzan con "
        "los indicadores SMART del módulo de Evaluación.",
        body_style))

    e.append(Paragraph("6 · Limitaciones del método", h2_style))
    e.append(Paragraph(
        "Las herramientas prospectivas no son adivinatorias y tienen tres limitaciones "
        "documentadas:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Sesgo en la selección de ejes.</b> Los ejes los elige el equipo humano; si los ejes están mal elegidos, los escenarios no exploran el espacio de futuros relevantes. El método no se autocorrige aquí.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Probabilidades subjetivas.</b> Las probabilidades por cuadrante son juicios; no son frecuencias empíricas. Hay que ser explícito sobre su origen y sensibilidad.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>El escenario sorpresa.</b> Por definición los 4 cuadrantes no incluyen el «cisne negro» (Taleb 2007) — un evento fuera del espacio definido por los ejes. La prospectiva mitiga esto pero no lo elimina. Suplementar con análisis de wild cards si la política tiene alta exposición a shocks.", list_style), leftIndent=15),
    ], bulletType='bullet'))

    e.append(Paragraph("7 · Bibliografía", h2_style))
    refs = [
        "Godet, M. (1994). <i>From Anticipation to Action: A Handbook of Strategic Prospective</i>. UNESCO Publishing.",
        "Godet, M. (2000). The Art of Scenarios and Strategic Planning: Tools and Pitfalls. <i>Technological Forecasting and Social Change</i>, 65(1), 3-22.",
        "Godet, M. (2007). <i>Manuel de prospective stratégique</i> (3ª ed.). Dunod.",
        "Gordon, T. J., &amp; Helmer, O. (1966). <i>Report on a Long-Range Forecasting Study</i>. RAND Corporation, P-2982.",
        "Gordon, T. J., &amp; Hayward, H. (1968). Initial Experiments with the Cross Impact Matrix Method of Forecasting. <i>Futures</i>, 1(2), 100-116.",
        "Hayward, P. (2003). Foresight in Everyday Life. <i>Journal of Futures Studies</i>, 7(3), 31-44.",
        "Helmer, O. (1983). <i>Looking Forward: A Guide to Futures Research</i>. Sage Publications.",
        "Lempert, R. J., Popper, S. W., &amp; Bankes, S. C. (2003). <i>Shaping the Next One Hundred Years: New Methods for Quantitative, Long-Term Policy Analysis</i>. RAND Corporation.",
        "Lempert, R. J., &amp; Schlesinger, M. E. (2000). Robust Strategies for Abating Climate Change. <i>Climatic Change</i>, 45(3-4), 387-401.",
        "Medina Vásquez, J., Becerra, S., &amp; Castaño, P. (2014). <i>Prospectiva y política pública para el cambio estructural en América Latina y el Caribe</i>. CEPAL.",
        "Mojica, F. J. (2005). <i>La construcción del futuro: concepto y modelo de prospectiva estratégica, territorial y tecnológica</i>. Universidad Externado de Colombia.",
        "Mojica, F. J. (2008). Dos modelos de la escuela voluntarista de prospectiva estratégica. <i>Documentos de Investigación. Universidad Externado de Colombia</i>.",
        "Ringland, G. (1998). <i>Scenario Planning: Managing for the Future</i>. John Wiley &amp; Sons.",
        "Schoemaker, P. J. H. (1995). Scenario Planning: A Tool for Strategic Thinking. <i>Sloan Management Review</i>, 36(2), 25-40.",
        "Schwartz, P. (1996). <i>The Art of the Long View: Planning for the Future in an Uncertain World</i>. Doubleday.",
        "Taleb, N. N. (2007). <i>The Black Swan: The Impact of the Highly Improbable</i>. Random House.",
        "Van der Heijden, K. (2005). <i>Scenarios: The Art of Strategic Conversation</i> (2ª ed.). John Wiley &amp; Sons.",
        "Wack, P. (1985). Scenarios: Uncharted Waters Ahead. <i>Harvard Business Review</i>, 63(5), 73-89.",
        "Walker, W. E., Lempert, R. J., &amp; Kwakkel, J. H. (2013). Deep Uncertainty. En S. Gass &amp; M. Fu (eds.), <i>Encyclopedia of Operations Research and Management Science</i>. Springer.",
        "World Bank (2017). <i>Foresight Methods: A Toolkit for Strategy and Decision Support</i>. World Bank Group.",
    ]
    for r in refs:
        e.append(Paragraph("• " + r, ref_style))

    doc.build(e, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"✓ Generado: {OUT}")
    print(f"  Tamaño: {OUT.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    build()
