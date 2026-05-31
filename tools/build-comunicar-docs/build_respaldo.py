"""
Genera el PDF 'Comunicar la Política · Respaldo académico' (Sprint H · v2).
Marco teórico de las cinco escuelas + ~30 referencias canónicas.
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
ref_style = ParagraphStyle('ref', parent=ss['BodyText'], fontName='Helvetica',
    fontSize=9, leading=12, textColor=INK, alignment=TA_LEFT, spaceAfter=4, leftIndent=14, firstLineIndent=-14)
callout_style = ParagraphStyle('callout', parent=body_style, fontName='Helvetica-Oblique',
    fontSize=9.5, leading=13, textColor=INK_2, leftIndent=10)

def header_footer(c, doc):
    c.saveState()
    c.setStrokeColor(RULE); c.setLineWidth(0.5)
    c.line(doc.leftMargin, letter[1]-1.1*cm, letter[0]-doc.rightMargin, letter[1]-1.1*cm)
    c.setFillColor(INK_3); c.setFont("Helvetica", 8)
    c.drawString(doc.leftMargin, letter[1]-1.4*cm, "Comunicar la Política · Ricardo Ruiz")
    c.drawRightString(letter[0]-doc.rightMargin, letter[1]-1.4*cm, "Respaldo académico · v1.0 · mayo 2026")
    c.line(doc.leftMargin, 1.3*cm, letter[0]-doc.rightMargin, 1.3*cm)
    c.drawString(doc.leftMargin, 0.9*cm, "ricardoruiz.co · consultoría en datos y política pública")
    c.drawRightString(letter[0]-doc.rightMargin, 0.9*cm, f"Página {doc.page}")
    c.restoreState()

REFS = [
    "OECD (2021). <i>Public Communication: The Global Context and the Way Forward</i>. OECD Publishing, París.",
    "OECD (2022). <i>The OECD Report on Public Communication</i> — Working Paper 54: Accessible and Inclusive Public Communication. OECD Publishing.",
    "OECD (2020). <i>Innovative Citizen Participation and New Democratic Institutions: Catching the Deliberative Wave</i>. OECD Publishing.",
    "CLAD (2016). <i>Carta Iberoamericana de Gobierno Abierto</i>. Centro Latinoamericano de Administración para el Desarrollo, Bogotá.",
    "Función Pública (2017). <i>Decreto 1499 de 2017</i> — Modelo Integrado de Planeación y Gestión (MIPG), Dimensión 5: Información y Comunicación. República de Colombia.",
    "Función Pública (2024). <i>Manual Operativo del MIPG</i>, versión 6, diciembre. Departamento Administrativo de la Función Pública.",
    "Congreso de Colombia (2014). <i>Ley 1712 de 2014</i> — Ley de Transparencia y del Derecho de Acceso a la Información Pública Nacional.",
    "Ganz, M. (2011). «Public Narrative, Collective Action, and Power». En S. Odugbemi & T. Lee (eds.), <i>Accountability through Public Opinion</i>, World Bank.",
    "Ganz, M. (2009). <i>Why David Sometimes Wins: Leadership, Organization, and Strategy in the California Farm Worker Movement</i>. Oxford University Press.",
    "Lakoff, G. (2004 / 2014 ed.). <i>Don't Think of an Elephant! Know Your Values and Frame the Debate</i>. Chelsea Green.",
    "Lakoff, G. (2008). <i>The Political Mind</i>. Viking.",
    "Shenker-Osorio, A. (2012). <i>Don't Buy It: The Trouble with Talking Nonsense About the Economy</i>. PublicAffairs.",
    "Behavioural Insights Team (2014). <i>EAST: Four Simple Ways to Apply Behavioural Insights</i>. The Behavioural Insights Team, Londres.",
    "Thaler, R. & Sunstein, C. (2008). <i>Nudge: Improving Decisions About Health, Wealth, and Happiness</i>. Yale University Press.",
    "Sunstein, C. (2013). <i>Simpler: The Future of Government</i>. Simon &amp; Schuster.",
    "Stone, D. (2012). <i>Policy Paradox: The Art of Political Decision Making</i>, 3.ª ed. W.W. Norton.",
    "Entman, R. M. (1993). «Framing: Toward Clarification of a Fractured Paradigm». <i>Journal of Communication</i>, 43(4).",
    "Chong, D. & Druckman, J. N. (2007). «Framing Theory». <i>Annual Review of Political Science</i>, 10.",
    "Snow, D. A. & Benford, R. D. (1988). «Ideology, Frame Resonance, and Participant Mobilization». <i>International Social Movement Research</i>, 1.",
    "Kahneman, D. & Tversky, A. (1984). «Choices, Values, and Frames». <i>American Psychologist</i>, 39(4).",
    "McCombs, M. & Shaw, D. (1972). «The Agenda-Setting Function of Mass Media». <i>Public Opinion Quarterly</i>, 36(2).",
    "Habermas, J. (1989). <i>The Structural Transformation of the Public Sphere</i>. MIT Press.",
    "Coffman, J. (2002). <i>Public Communication Campaign Evaluation: An Environmental Scan of Challenges, Criticisms, Practice, and Opportunities</i>. Harvard Family Research Project.",
    "Atkin, C. K. & Rice, R. E. (eds.) (2013). <i>Public Communication Campaigns</i>, 4.ª ed. SAGE.",
    "Heath, C. & Heath, D. (2007). <i>Made to Stick: Why Some Ideas Survive and Others Die</i>. Random House.",
    "Westen, D. (2007). <i>The Political Brain: The Role of Emotion in Deciding the Fate of the Nation</i>. PublicAffairs.",
    "Luntz, F. (2007). <i>Words That Work: It's Not What You Say, It's What People Hear</i>. Hyperion.",
    "Odugbemi, S. & Lee, T. (eds.) (2011). <i>Accountability through Public Opinion: From Inertia to Public Action</i>. World Bank.",
    "Wardle, C. & Derakhshan, H. (2017). <i>Information Disorder: Toward an Interdisciplinary Framework for Research and Policymaking</i>. Council of Europe.",
    "Rincón, O. (2018). «Narrativas mediáticas, política y comunicación». Centro de Estudios en Periodismo (CEPER), Universidad de los Andes.",
    "CEPAL / ILPES. Serie <i>Manuales</i> sobre planificación, marco lógico y comunicación de políticas públicas. Naciones Unidas.",
]

def build():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=2.0*cm, bottomMargin=1.9*cm,
        title="Comunicar la Política · Respaldo académico",
        author="Ricardo Ruiz · ricardoruiz.co",
        subject="Marco teórico y referencias del módulo de comunicación de política pública"
    )
    e = []

    e.append(Paragraph("Comunicar la Política", title_style))
    e.append(Paragraph("Respaldo académico · marco teórico y referencias", subtitle_style))
    e.append(Paragraph(
        "El módulo de comunicación del Lab no improvisa: cada mecánica está anclada "
        "en literatura establecida de comunicación pública, ciencia política del "
        "lenguaje y economía del comportamiento. Este documento resume las cinco "
        "escuelas que lo fundamentan y lista la bibliografía de respaldo.",
        body_style))

    e.append(Paragraph("1 · Comunicación pública como función de gobierno (OCDE · CLAD · MIPG)", h2_style))
    e.append(Paragraph(
        "La OCDE (2021) define la comunicación pública como una función central del "
        "Estado — distinta de la comunicación política o el marketing — orientada a "
        "informar, escuchar y construir confianza. De ahí provienen las <b>nueve "
        "dimensiones de medición</b> (alcance, engagement, atención, comprensión, "
        "satisfacción, apoyo, cambio actitudinal, intención y comportamiento) que "
        "estructuran la mecánica de medición. La Carta Iberoamericana de Gobierno "
        "Abierto del CLAD (2016, firmada en Bogotá) la ancla en apertura y "
        "participación. En Colombia, el MIPG (Decreto 1499 de 2017, Dimensión 5) y "
        "la Ley 1712 de 2014 imponen obligaciones de información, lenguaje claro y "
        "transparencia activa.",
        body_style))

    e.append(Paragraph("2 · Narrativa pública (Ganz)", h2_style))
    e.append(Paragraph(
        "Marshall Ganz (Harvard Kennedy School) formaliza la <i>public narrative</i> "
        "como la traducción de valores en acción colectiva mediante tres movimientos "
        "— Story of Self, Story of Us y Story of Now. La narrativa no sustituye los "
        "datos: les da urgencia moral y pertenencia. La estructura es la base de la "
        "mecánica 4 del módulo.",
        body_style))

    e.append(Paragraph("3 · Encuadre y lenguaje (Lakoff · Shenker-Osorio · Stone)", h2_style))
    e.append(Paragraph(
        "George Lakoff demuestra que el lenguaje activa marcos conceptuales: negar "
        "el término del adversario lo refuerza (<i>«no pienses en un elefante»</i>). "
        "Anat Shenker-Osorio aporta evidencia experimental (priming y dial surveys) "
        "sobre qué mensajes mueven opinión — la regla de empezar por el valor, no por "
        "el problema. Deborah Stone (<i>Policy Paradox</i>) muestra cómo el conteo, la "
        "causalidad y la comparación son actos retóricos, no neutrales. Robert Entman "
        "y Chong &amp; Druckman dan la base académica del framing. Esto fundamenta la "
        "mecánica 5 (valor central, metáfora, palabras propias vs. del adversario).",
        body_style))

    e.append(Paragraph("4 · Economía del comportamiento aplicada a canales (BIT EAST)", h2_style))
    e.append(Paragraph(
        "El Behavioural Insights Team (Reino Unido) condensa décadas de economía del "
        "comportamiento (Thaler &amp; Sunstein) en la heurística <b>EAST</b>: Easy, "
        "Attractive, Social, Timely. Es el criterio práctico para diseñar el mensaje "
        "de cada canal en la matriz audiencia × canal (mecánica 6). Un mensaje "
        "correcto en el marco equivocado de fricción, momento o norma social no "
        "produce comportamiento.",
        body_style))

    e.append(Paragraph("5 · Evaluación de campañas y contexto colombiano (Coffman · Rincón)", h2_style))
    e.append(Paragraph(
        "La evaluación de campañas de comunicación pública (Coffman, Harvard FRP; "
        "Atkin &amp; Rice) advierte contra medir solo alcance: una campaña con gran "
        "exposición y cero cambio de comportamiento falló. De ahí la gradación de las "
        "nueve dimensiones. Omar Rincón (Universidad de los Andes) aterriza las "
        "narrativas mediáticas al contexto colombiano y latinoamericano.",
        body_style))

    e.append(Paragraph("Referencias", h2_style))
    e.append(Paragraph(
        "Bibliografía canónica de respaldo (selección).",
        callout_style))
    for i, r in enumerate(REFS, 1):
        e.append(Paragraph(f"[{i}] {r}", ref_style))

    doc.build(e, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"✓ Generado: {OUT}")
    print(f"  Tamaño: {OUT.stat().st_size / 1024:.1f} KB")
    print(f"  Referencias: {len(REFS)}")

if __name__ == "__main__":
    build()
