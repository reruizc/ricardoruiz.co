"""
Genera el PDF 'Problema Público · Respaldo académico' (Sprint A.6).
Fórmulas, autores y bibliografía detrás del módulo.
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

OUT_DIR = Path(__file__).resolve().parents[2] / "Bases de datos" / "pp"
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
list_style = ParagraphStyle('list', parent=body_style, leftIndent=0, spaceAfter=4)
callout_style = ParagraphStyle('callout', parent=body_style, fontName='Helvetica-Oblique',
    fontSize=9.5, leading=13, textColor=INK_2, leftIndent=10)
formula_style = ParagraphStyle('formula', parent=body_style, fontName='Courier',
    fontSize=10, leading=14, textColor=ACCENT, alignment=TA_LEFT, leftIndent=12, spaceAfter=10)
bib_style = ParagraphStyle('bib', parent=body_style, fontSize=9.5, leading=13,
    spaceAfter=6, alignment=TA_LEFT, leftIndent=18, firstLineIndent=-18)

def header_footer(c, doc):
    c.saveState()
    c.setStrokeColor(RULE); c.setLineWidth(0.5)
    c.line(doc.leftMargin, letter[1]-1.1*cm, letter[0]-doc.rightMargin, letter[1]-1.1*cm)
    c.setFillColor(INK_3); c.setFont("Helvetica", 8)
    c.drawString(doc.leftMargin, letter[1]-1.4*cm, "Problema Público · Ricardo Ruiz")
    c.drawRightString(letter[0]-doc.rightMargin, letter[1]-1.4*cm, "Respaldo académico · v1.0 · mayo 2026")
    c.line(doc.leftMargin, 1.3*cm, letter[0]-doc.rightMargin, 1.3*cm)
    c.drawString(doc.leftMargin, 0.9*cm, "ricardoruiz.co · consultoría en datos y política pública")
    c.drawRightString(letter[0]-doc.rightMargin, 0.9*cm, f"Página {doc.page}")
    c.restoreState()

def build():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=2.0*cm, bottomMargin=1.9*cm,
        title="Problema Público · Respaldo académico",
        author="Ricardo Ruiz · ricardoruiz.co",
        subject="Fórmulas, autores y bibliografía del módulo de Problema Público"
    )
    e = []

    # ─── Portada ─────────────────────────────────────────────────────────
    e.append(Paragraph("Problema Público", title_style))
    e.append(Paragraph(
        "Respaldo metodológico: fórmulas, autores referenciados y bibliografía",
        subtitle_style))
    e.append(Paragraph(
        "Este documento sustenta las decisiones metodológicas del módulo "
        "<font color='#8a1e16'>ricardoruiz.co/problema-publico.html</font>. "
        "Documenta el marco general del análisis de políticas, el Eightfold Path "
        "de Bardach, las 10 propiedades de Rittel-Webber, el árbol del problema "
        "de CEPAL/Ortegón, los 4 marcos analíticos referenciados, la fórmula del "
        "score ponderado y la bibliografía completa.",
        body_style))
    e.append(Spacer(1, 12))

    # ─── Contenido ───────────────────────────────────────────────────────
    e.append(Paragraph("Contenido", h3_style))
    toc = [
        ["01", "Marco general: análisis de políticas como disciplina"],
        ["02", "Eightfold Path (Bardach &amp; Patashnik 2016)"],
        ["03", "Wicked problems (Rittel &amp; Webber 1973)"],
        ["04", "Árbol del problema (CEPAL · ILPES · Ortegón)"],
        ["05", "Cuatro marcos analíticos según complejidad"],
        ["06", "Fórmula del score ponderado"],
        ["07", "Bibliografía"],
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

    # ─── 01 ──────────────────────────────────────────────────────────────
    e.append(Paragraph("01 · Marco general: análisis de políticas como disciplina", h2_style))
    e.append(Paragraph(
        "El análisis de políticas públicas (<i>policy analysis</i>) se "
        "consolida como disciplina aplicada en EE. UU. después de la Segunda "
        "Guerra Mundial, con la creación de la RAND Corporation (1948) y "
        "luego de la Kennedy School of Government en Harvard (1969). Su "
        "premisa central es que las decisiones de política se pueden y "
        "deben sustentar con análisis sistemático — no con intuición o "
        "lealtades — sin que eso sustituya el juicio político final.",
        body_style))
    e.append(Paragraph(
        "Tres autores definen el campo: <b>Eugene Bardach</b> (Berkeley) "
        "con el <i>Eightfold Path</i>; <b>William N. Dunn</b> (Pittsburgh) "
        "con el modelo descriptivo + normativo + prescriptivo; y <b>Carol "
        "Weiss</b> (Harvard) con la distinción entre uso instrumental, "
        "conceptual y simbólico del análisis. En América Latina los "
        "referentes son <b>Edgar Ortegón</b> (ILPES/CEPAL) con el manual de "
        "prospectiva y decisión estratégica, y en Colombia <b>Jaime "
        "Torres-Melo &amp; Jairo Santander</b> (Instituto de Estudios del "
        "Ministerio Público) con la <i>Introducción a las políticas públicas</i>.",
        body_style))

    # ─── 02 ──────────────────────────────────────────────────────────────
    e.append(Paragraph("02 · Eightfold Path (Bardach &amp; Patashnik 2016)", h2_style))
    e.append(Paragraph(
        "El método más usado en escuelas de política pública anglosajonas. "
        "Eight steps que el analista recorre iterativamente:",
        body_style))
    eightfold_table = [
        ["Paso", "Bardach &amp; Patashnik", "Cómo lo cubre este módulo"],
        ["1", "Define the Problem",            "Wizard de síntoma + stage Definir (formulario o árbol)"],
        ["2", "Assemble the Evidence",         "Stage Acopiar evidencia (tabla editable, seed de 3 fuentes)"],
        ["3", "Construct the Alternatives",    "Stage Alternativas (3-5 cards, baseline obligatorio)"],
        ["4", "Select the Criteria",           "Stage Criterios (5 default, pesos editables)"],
        ["5", "Project the Outcomes",          "Matriz de comparación (celdas 1-5 por criterio)"],
        ["6", "Confront the Trade-offs",       "Score ponderado en cada celda + ranking visual"],
        ["7", "Decide",                        "Recomendación destacada en stage Results"],
        ["8", "Tell Your Story",               "Memo (.md) e Issue Paper (.md) descargables"],
    ]
    t = Table(eightfold_table, colWidths=[1.1*cm, 5.5*cm, 7.8*cm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (-1,0), ACCENT),
        ('TEXTCOLOR', (0,1), (-1,-1), INK),
        ('BACKGROUND', (0,0), (-1,0), ACCENT_SOFT),
        ('LINEBELOW', (0,0), (-1,-1), 0.3, RULE),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    e.append(t)
    e.append(Spacer(1, 6))
    e.append(Paragraph(
        "El módulo condensa los 8 pasos en 5 mecánicas operativas: los pasos 5-7 "
        "(project · confront · decide) quedan integrados en la matriz de comparación "
        "con score ponderado. La razón es práctica: cuando una herramienta web pide "
        "8 pantallas separadas, el usuario se cansa antes de la mitad y abandona.",
        callout_style))

    # ─── 03 ──────────────────────────────────────────────────────────────
    e.append(Paragraph("03 · Wicked problems (Rittel &amp; Webber 1973)", h2_style))
    e.append(Paragraph(
        "Horst Rittel y Melvin Webber, en su artículo seminal de 1973 "
        "\"Dilemmas in a General Theory of Planning\" (Policy Sciences 4, "
        "155-169), distinguen problemas <i>tame</i> (técnicos, bien "
        "definidos) de problemas <i>wicked</i> (mal definidos, ambiguos, "
        "sin solución óptima). Las 10 propiedades de un wicked problem:",
        body_style))
    rittel_props = [
        "01 · No existe formulación definitiva del problema.",
        "02 · No hay regla de parada (stopping rule) para el análisis.",
        "03 · Las soluciones no son verdaderas o falsas, son mejores o peores según quién las juzgue.",
        "04 · No hay test inmediato ni último de la solución.",
        "05 · Toda solución es one-shot: no hay ensayo-y-error sin consecuencias.",
        "06 · No hay lista exhaustiva de alternativas; el menú depende de la creatividad del equipo.",
        "07 · Cada wicked problem es esencialmente único.",
        "08 · Todo wicked problem puede ser síntoma de otro problema más profundo.",
        "09 · La elección de la explicación determina la naturaleza de la resolución.",
        "10 · Quien planifica no tiene derecho a estar equivocado (responsabilidad moral).",
    ]
    e.append(ListFlowable([
        ListItem(Paragraph(p, list_style), leftIndent=15) for p in rittel_props
    ], bulletType='bullet'))
    e.append(Spacer(1, 6))
    e.append(Paragraph(
        "El módulo traduce cada propiedad a una pregunta SÍ/NO. El score (0-10) "
        "clasifica el problema y orienta el marco analítico. Los thresholds 0-2 / "
        "3-5 / 6-8 / 9-10 son una propuesta del módulo (no de Rittel-Webber, que "
        "deja la clasificación cualitativa). Si el score cae justo en un borde, "
        "el usuario puede inspeccionar las preguntas individuales para decidir.",
        body_style))

    # ─── 04 ──────────────────────────────────────────────────────────────
    e.append(Paragraph("04 · Árbol del problema (CEPAL · ILPES · Ortegón)", h2_style))
    e.append(Paragraph(
        "El árbol del problema (o <i>problem tree</i>) es una herramienta "
        "clásica de la planeación pública latinoamericana, popularizada por "
        "el ILPES (Instituto Latinoamericano y del Caribe de Planificación "
        "Económica y Social) en sus manuales de los años 90 y formalizada "
        "por Edgar Ortegón en \"Manual de prospectiva y decisión estratégica\" "
        "(2007).",
        body_style))
    e.append(Paragraph(
        "Estructura canónica:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Raíces (causas).</b> Lo que <i>genera</i> el problema. Idealmente 3-5 causas raíz; si pones más se vuelve difícil priorizar.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Tronco (problema central).</b> La afirmación del problema en una sola frase. Debe ser específica, medible y referirse al estado actual (no al estado deseado).", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Ramas (efectos).</b> Lo que el problema <i>produce</i>. Útil para conectar el problema con cosas que el comité reconozca como costosas.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Spacer(1, 4))
    e.append(Paragraph(
        "El método tiene un complemento natural — el <i>árbol de objetivos</i> "
        "(o <i>árbol de soluciones</i>) — que invierte el árbol para describir "
        "el escenario deseado. Este módulo no lo implementa explícitamente, "
        "pero el stage de Alternativas cumple parcialmente esa función: cada "
        "alternativa es un sub-árbol de objetivos potencial.",
        callout_style))

    # ─── 05 ──────────────────────────────────────────────────────────────
    e.append(Paragraph("05 · Cuatro marcos analíticos según complejidad", h2_style))
    e.append(Paragraph(
        "Tras el test Rittel-Webber, el módulo recomienda 1 de 4 marcos. La "
        "lógica: a mayor wicked-ness, menos puede el análisis racional "
        "individual decidir bien y más necesita el proceso ser distribuido, "
        "iterativo y participativo.",
        body_style))
    marcos = [
        ["Tipo (score)",       "Marco analítico",                                  "Autores referenciados"],
        ["Tame (0-2)",         "Análisis racional · multi-criterio simple",        "Bardach &amp; Patashnik (2016); Lindblom (1959, contraste)"],
        ["Complejo (3-5)",     "Multi-criterio + escenarios adaptativos",          "Walker &amp; Marchau (2003); Lempert et al. (2003)"],
        ["Wicked (6-8)",       "Diseño participativo + co-creación",               "Roberts (2000); Head &amp; Alford (2015)"],
        ["Meta-wicked (9-10)", "Gobernanza colaborativa de red",                   "Ansell &amp; Gash (2008); Provan &amp; Kenis (2008)"],
    ]
    t = Table(marcos, colWidths=[2.7*cm, 5.6*cm, 6.1*cm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (-1,0), ACCENT),
        ('TEXTCOLOR', (0,1), (-1,-1), INK),
        ('BACKGROUND', (0,0), (-1,0), ACCENT_SOFT),
        ('LINEBELOW', (0,0), (-1,-1), 0.3, RULE),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    e.append(t)
    e.append(Spacer(1, 6))
    e.append(Paragraph(
        "El usuario puede cambiar la recomendación. Lo importante es que la "
        "elección quede explícita en el memo final como anclaje teórico — un "
        "comité técnico que sepa que el análisis usó \"gobernanza colaborativa "
        "Ansell-Gash\" puede juzgar el rigor del trabajo sin abrir cada "
        "celda de la matriz.",
        body_style))

    # ─── 06 ──────────────────────────────────────────────────────────────
    e.append(Paragraph("06 · Fórmula del score ponderado", h2_style))
    e.append(Paragraph(
        "El score de cada alternativa <i>i</i> se calcula como la suma "
        "ponderada de sus calificaciones, donde los pesos se normalizan por "
        "la suma total:",
        body_style))
    e.append(Paragraph(
        "score_i  =  Σ_j  ( valor_ij  ×  ( peso_j / Σ_k peso_k ) )",
        formula_style))
    e.append(Paragraph(
        "Donde:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>valor_ij</b> ∈ {0, 1, 2, 3, 4, 5} es la calificación de la alternativa <i>i</i> en el criterio <i>j</i>. 0 = celda no calificada; 1-5 = muy bajo a muy alto.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>peso_j</b> ∈ [0, 100] es el peso bruto del criterio <i>j</i>, asignado por el usuario.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Σ_k peso_k</b> es la suma de todos los pesos. La normalización <i>peso_j / Σ_k peso_k</i> hace que la suma de pesos normalizados sea 1, sin importar si los brutos suman 100, 80 o 120.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "El rango del score es aproximadamente [0, 5]. Las celdas no calificadas "
        "cuentan como 0 — esto es decisión metodológica para no premiar "
        "implícitamente a las alternativas mal documentadas (la alternativa "
        "ganadora suele ser la mejor sustentada, no necesariamente la mejor).",
        body_style))
    e.append(Paragraph(
        "Limitación conocida: el método multi-criterio asume independencia entre "
        "criterios y aditividad. En problemas wicked esto NO se cumple (por eso "
        "los marcos 3 y 4 recomiendan complementar con escenarios adaptativos o "
        "co-creación). El score sirve como punto de partida, no como veredicto.",
        callout_style))

    # ─── 07 ──────────────────────────────────────────────────────────────
    e.append(Paragraph("07 · Bibliografía", h2_style))
    e.append(Paragraph("Marco general", h3_style))
    refs_general = [
        "<b>Bardach, E. &amp; Patashnik, E. M.</b> (2016). <i>A Practical Guide for Policy Analysis: The Eightfold Path to More Effective Problem Solving</i> (5ª ed.). CQ Press.",
        "<b>Dunn, W. N.</b> (2017). <i>Public Policy Analysis</i> (6ª ed.). Routledge.",
        "<b>Weiss, C. H.</b> (1979). \"The Many Meanings of Research Utilization\". <i>Public Administration Review</i>, 39(5), 426-431.",
        "<b>Ortegón, E.</b> (2007). <i>Manual de prospectiva y decisión estratégica: bases teóricas e instrumentos para América Latina y el Caribe</i>. ILPES/CEPAL, Santiago.",
        "<b>Torres-Melo, J. &amp; Santander, J.</b> (2013). <i>Introducción a las políticas públicas: conceptos y herramientas desde la relación entre Estado y ciudadanía</i>. IEMP Ediciones, Bogotá.",
    ]
    for r in refs_general: e.append(Paragraph(r, bib_style))

    e.append(Paragraph("Wicked problems y diseño participativo", h3_style))
    refs_wicked = [
        "<b>Rittel, H. W. J. &amp; Webber, M. M.</b> (1973). \"Dilemmas in a General Theory of Planning\". <i>Policy Sciences</i>, 4(2), 155-169.",
        "<b>Roberts, N.</b> (2000). \"Wicked Problems and Network Approaches to Resolution\". <i>International Public Management Review</i>, 1(1), 1-19.",
        "<b>Head, B. W. &amp; Alford, J.</b> (2015). \"Wicked Problems: Implications for Public Policy and Management\". <i>Administration &amp; Society</i>, 47(6), 711-739.",
        "<b>Conklin, J.</b> (2005). <i>Dialogue Mapping: Building Shared Understanding of Wicked Problems</i>. Wiley.",
    ]
    for r in refs_wicked: e.append(Paragraph(r, bib_style))

    e.append(Paragraph("Análisis adaptativo y escenarios", h3_style))
    refs_adap = [
        "<b>Walker, W. E., Rahman, S. A. &amp; Cave, J.</b> (2001). \"Adaptive Policies, Policy Analysis, and Policy-Making\". <i>European Journal of Operational Research</i>, 128(2), 282-289.",
        "<b>Lempert, R. J., Popper, S. W. &amp; Bankes, S. C.</b> (2003). <i>Shaping the Next One Hundred Years: New Methods for Quantitative, Long-Term Policy Analysis</i>. RAND Corporation.",
        "<b>Marchau, V. A. W. J. et al. (eds.)</b> (2019). <i>Decision Making under Deep Uncertainty: From Theory to Practice</i>. Springer (open access).",
    ]
    for r in refs_adap: e.append(Paragraph(r, bib_style))

    e.append(Paragraph("Gobernanza colaborativa", h3_style))
    refs_gob = [
        "<b>Ansell, C. &amp; Gash, A.</b> (2008). \"Collaborative Governance in Theory and Practice\". <i>Journal of Public Administration Research and Theory</i>, 18(4), 543-571.",
        "<b>Provan, K. G. &amp; Kenis, P.</b> (2008). \"Modes of Network Governance: Structure, Management, and Effectiveness\". <i>Journal of Public Administration Research and Theory</i>, 18(2), 229-252.",
    ]
    for r in refs_gob: e.append(Paragraph(r, bib_style))

    e.append(Paragraph("Árbol del problema (CEPAL / ILPES)", h3_style))
    refs_arbol = [
        "<b>Aldunate, E. &amp; Córdoba, J.</b> (2011). <i>Formulación de programas con la metodología de marco lógico</i>. CEPAL/ILPES, Serie Manuales 68, Santiago.",
        "<b>Ortegón, E., Pacheco, J. F. &amp; Prieto, A.</b> (2005). <i>Metodología del marco lógico para la planificación, el seguimiento y la evaluación de proyectos y programas</i>. CEPAL/ILPES, Serie Manuales 42, Santiago.",
    ]
    for r in refs_arbol: e.append(Paragraph(r, bib_style))

    e.append(Paragraph("Contraste y referencias clásicas", h3_style))
    refs_clasicos = [
        "<b>Lindblom, C. E.</b> (1959). \"The Science of 'Muddling Through'\". <i>Public Administration Review</i>, 19(2), 79-88.",
        "<b>Simon, H. A.</b> (1947). <i>Administrative Behavior</i>. Macmillan.",
        "<b>Lasswell, H. D.</b> (1956). <i>The Decision Process: Seven Categories of Functional Analysis</i>. University of Maryland Press.",
    ]
    for r in refs_clasicos: e.append(Paragraph(r, bib_style))

    e.append(Spacer(1, 10))
    e.append(Paragraph(
        "Esta bibliografía no pretende ser exhaustiva — selecciona las referencias "
        "operativas que sustentan las decisiones del módulo. Para inmersión "
        "completa, los manuales de CEPAL/ILPES y la guía de Bardach &amp; Patashnik "
        "son los mejores puntos de partida en español e inglés respectivamente.",
        callout_style))

    doc.build(e, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"✓ Generado: {OUT}")
    print(f"  Tamaño: {OUT.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    build()
