"""
Genera 'Alternativas de Política · Respaldo académico'.
Marco teórico, fórmulas, justificación de mecánicas, bibliografía 25+ refs.
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
RULE = HexColor("#14110a40"); GOLD = HexColor("#8a6a1a")

OUT_DIR = Path(__file__).resolve().parents[2] / "Bases de datos" / "alt"
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
    c.drawString(doc.leftMargin, letter[1]-1.4*cm, "Alternativas de Política · Ricardo Ruiz")
    c.drawRightString(letter[0]-doc.rightMargin, letter[1]-1.4*cm, "Respaldo académico · v1.0 · mayo 2026")
    c.line(doc.leftMargin, 1.3*cm, letter[0]-doc.rightMargin, 1.3*cm)
    c.drawString(doc.leftMargin, 0.9*cm, "ricardoruiz.co · consultoría en datos y política pública")
    c.drawRightString(letter[0]-doc.rightMargin, 0.9*cm, f"Página {doc.page}")
    c.restoreState()

def build():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=2.0*cm, bottomMargin=1.9*cm,
        title="Alternativas de Política · Respaldo académico",
        author="Ricardo Ruiz · ricardoruiz.co",
        subject="Marco teórico, fórmulas y bibliografía del módulo de Alternativas del Lab"
    )
    e = []

    e.append(Paragraph("Alternativas de Política", title_style))
    e.append(Paragraph("Respaldo académico · marco teórico, fórmulas y bibliografía", subtitle_style))
    e.append(Paragraph(
        "Este documento sostiene metodológicamente las seis mecánicas del módulo "
        "web de Alternativas. Cubre la justificación de cada decisión de diseño, "
        "las fórmulas usadas y las referencias completas. Pensado para "
        "consultores y comités técnicos que quieran auditar el método.",
        body_style))

    e.append(Paragraph("1 · Marco general del módulo", h2_style))
    e.append(Paragraph(
        "El módulo combina cinco escuelas metodológicas que convergen en una "
        "pregunta común: <i>¿cómo se construyen alternativas defendibles cuando "
        "el ojo humano sólo considera tres y el futuro es incierto?</i>",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Análisis morfológico</b> · Fritz Zwicky (Caltech, <i>Discovery, Invention, Research through the Morphological Approach</i>, Macmillan 1969). Descompone un problema de diseño en variables independientes y opciones discretas por variable. Cada combinación es una alternativa candidata.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>General Morphological Analysis</b> · Tom Ritchey (Swedish Morphological Society; <i>Wicked Problems · Social Messes</i>, Springer 2011). Aporta el <i>cross-consistency assessment</i>: identificar pares de opciones incompatibles antes de ensamblar, para reducir el espacio combinatorio.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Robust Decision Making (RDM)</b> · Robert Lempert, Steven Popper, Steven Bankes (RAND, <i>Shaping the Next One Hundred Years</i>, 2003). Cuando no hay probabilidades creíbles, la alternativa robusta es la que aguanta el peor caso aceptablemente, no la que maximiza el valor esperado.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Decision Analysis</b> · Ronald A. Howard (Stanford, <i>The Foundations of Decision Analysis</i>, IEEE 1968). Separa preferencias del decisor (qué valora) de creencias sobre el mundo (qué cree que pasará).", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Value-Focused Thinking</b> · Ralph L. Keeney (USC, <i>Value-Focused Thinking</i>, Harvard 1992). Antes de comparar alternativas, hay que explicitar valores; el módulo lo opera vía rating cualitativo por escenario.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Lente económica</b> · MVPF de Hendren &amp; Sprung-Keyser (NBER 2020) y CEA de J-PAL (2023+). Permite unificar comparaciones heterogéneas en una sola métrica defendible cuando hay datos de costo y beneficio.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "Anclaje regulatorio colombiano: SINERGIA · DNP. El export PDF del módulo "
        "se formatea en estructura CONPES light (problema → variables → "
        "alternativas → robustez → lente económica → recomendación) para que el "
        "entregable encaje en el formato institucional sin pretender ser CONPES "
        "oficial.",
        body_style))

    e.append(Paragraph("2 · Variables de decisión (mecánica 1)", h2_style))
    e.append(Paragraph(
        "El módulo asume la perspectiva de <b>policy design</b> de Howlett &amp; "
        "Mukherjee (<i>Handbook of Policy Formulation</i>, 2017) y Salamon "
        "(<i>The Tools of Government</i>, 2002): una política se describe por "
        "el conjunto de <i>instrumentos</i> elegidos sobre cada dimensión de "
        "diseño. Lascoumes &amp; Le Galès (<i>Governing through Instruments</i>, "
        "2007) reforzaron la idea de que <i>la elección del instrumento no es "
        "neutral</i> — define la relación entre Estado y ciudadanía.",
        body_style))
    e.append(Paragraph(
        "El catálogo cerrado de tipos del módulo (cobertura · financiamiento · "
        "instrumento · gobernanza · condicionalidad · timing · población · "
        "ámbito · modalidad · sostenibilidad · otra) sintetiza las dimensiones "
        "más recurrentes en la literatura. Las 6 plantillas seed (cobertura "
        "social, reforma fiscal, servicio público, regulación, seguridad, "
        "blanco) reflejan tipologías de instrumentos estandarizadas por "
        "Salamon y por la guía MGA del DNP.",
        body_style))
    e.append(Paragraph(
        "Restricción: 3 a 8 variables. Es un trade-off conocido en morfología "
        "(Ritchey 2011): por debajo de 3, la matriz colapsa a la trivialidad; "
        "por encima de 8, la complejidad combinatoria sobrepasa la capacidad "
        "humana de leer la matriz.",
        callout_style))

    e.append(Paragraph("3 · Opciones por variable (mecánica 2)", h2_style))
    e.append(Paragraph(
        "Tres a cinco opciones por variable. La restricción inferior viene de "
        "Zwicky: con menos de tres no hay <i>espacio morfológico</i>, hay "
        "elección obligada. La restricción superior viene de Miller "
        "(<i>The Magical Number Seven, Plus or Minus Two</i>, Psychological "
        "Review 1956): el ser humano discrimina ~5±2 opciones simultáneamente; "
        "más infla la matriz a costa de discriminación.",
        body_style))
    e.append(Paragraph(
        "Cada opción debe ser <b>operativamente distinguible</b>. Lindblom "
        "(<i>The Science of Muddling Through</i>, 1959) ya advertía contra "
        "alternativas que son la misma cosa con etiquetas distintas. El "
        "módulo no enforza distinguibilidad — depende del juicio del analista — "
        "pero el copiloto IA marca redundancias cuando se le pide validar.",
        body_style))

    e.append(Paragraph("4 · Matriz morfológica · cross-consistency assessment (mecánica 3)", h2_style))
    e.append(Paragraph(
        "Con n variables y k opciones promedio por variable, el espacio "
        "morfológico tiene <b>k^n</b> combinaciones. Para 5 variables con 4 "
        "opciones, son 1.024 alternativas candidatas. La mayoría es inviable "
        "— el ejercicio clave no es generarlas sino <b>filtrarlas</b>.",
        body_style))
    e.append(Paragraph(
        "El <i>cross-consistency assessment</i> (Ritchey 2011) es una matriz "
        "n(n−1)/2 de pares de opciones: por cada par (opt_i ∈ var_A, opt_j ∈ "
        "var_B) con A ≠ B, se marca compatible o incompatible. El módulo lo "
        "simplifica a una lista plana de pares incompatibles. Para 5 variables × "
        "4 opciones, hay C(20, 2) − C(4, 2)·5 = 190 − 30 = 160 pares posibles "
        "(excluyendo pares dentro de la misma variable). Una matriz bien hecha "
        "marca entre 20 y 40 pares incompatibles.",
        body_style))
    e.append(Paragraph(
        "El conteo de <b>combinaciones restantes</b> tras incompatibilidades "
        "se calcula por enumeración brute-force cuando el producto k^n ≤ 5.000 "
        "(implementado cliente-side en <code>_calcRestantesPostIncompat</code>). "
        "Por encima de ese umbral, el módulo muestra <i>demasiadas para "
        "enumerar</i> y deja la estimación al usuario.",
        body_style))
    e.append(Paragraph(
        "Empíricamente, una buena matriz morfológica reduce el espacio al "
        "5–15% de combinaciones viables (Ritchey 2011, Álvarez-Ritchey 2015). "
        "El restante se procesa en la mecánica 4.",
        callout_style))

    e.append(Paragraph("5 · Alternativas ensambladas (mecánica 4)", h2_style))
    e.append(Paragraph(
        "Una alternativa es una asignación específica de una opción por "
        "variable, más metadata textual: nombre, descripción, supuestos "
        "críticos, costo, plazo, riesgo dominante. Máximo 6 + 1 baseline "
        "<i>Statu quo</i>.",
        body_style))
    e.append(Paragraph(
        "El baseline es <b>obligatorio y no eliminable</b>. Hendren &amp; "
        "Sprung-Keyser (2020) insisten en que la economía del bienestar es "
        "marginal por construcción: sin un baseline explícito no hay marginal. "
        "Es también una recomendación canónica del Green Book del HM Treasury "
        "(2022) y de las guías de Sinergia DNP para evaluación ex-ante.",
        body_style))
    e.append(Paragraph(
        "El paso de <b>coherencia interna</b> (validar-coherencia, plan Premium+) "
        "verifica que la combinación de opciones de una misma alternativa no "
        "sea operativamente contradictoria. Ejemplos clásicos: cobertura "
        "universal + financiamiento por tarifa al usuario (mutuamente "
        "excluyentes); subsidio incondicional + sanción por incumplimiento "
        "(no hay condición que sancionar). El copiloto sólo marca contradicciones "
        "operativas, no preferencias ideológicas.",
        body_style))

    e.append(Paragraph("6 · Robustez en escenarios (mecánica 5)", h2_style))
    e.append(Paragraph(
        "El módulo implementa una versión simplificada del Robust Decision "
        "Making (Lempert &amp; Walker, RAND 2003). Cuatro escenarios "
        "pre-definidos editables (baseline 40% · optimista 25% · pesimista "
        "25% · disruptivo 10%) capturan la <i>incertidumbre profunda</i> en el "
        "sentido de Walker, Marchau &amp; Kwakkel (<i>Handbook of Decision "
        "Making</i>, 2013): no se pretende asignar probabilidades objetivas, "
        "sino capturar la distribución subjetiva del analista.",
        body_style))
    e.append(Paragraph("<b>Cálculos:</b>", h3_style))
    e.append(Paragraph("Sea A_i una alternativa, S_j un escenario con probabilidad p_j y rating r_{ij} ∈ {1,...,5} asignado por el analista a la alternativa i en el escenario j. Sea P = Σ_j p_j (suma de probs, idealmente 100 pero se normaliza).", body_style))
    e.append(Paragraph("Score esperado:  E_i = (Σ_j p_j · r_{ij}) / P", formula_style))
    e.append(Paragraph("Peor caso:       W_i = min_j r_{ij}", formula_style))
    e.append(Paragraph("Bonus robustez:  B_i = 0.5 si W_i ≥ 3, sino 0", formula_style))
    e.append(Paragraph("Score final:     F_i = E_i + B_i", formula_style))
    e.append(Paragraph(
        "La fórmula del score esperado normaliza por P para que el cálculo sea "
        "robusto frente a sumas distintas a 100% (incentivo a explorar "
        "sensibilidad sin tener que rebalancear probabilidades a cada cambio). "
        "El <b>bonus de robustez</b> es la diferencia central con un MCDM "
        "clásico (Multi-Criteria Decision Making): premia explícitamente la "
        "alternativa que no se hunde en el peor escenario, siguiendo el "
        "principio de <i>minimax regret</i> de Savage (1951) en su versión "
        "blanda. La opción de calibrarlo es deliberada: alternativas con "
        "peor caso ≤ 2 son inaceptables aunque tengan score esperado alto.",
        body_style))

    e.append(Paragraph("7 · Lente económica · MVPF + CEA (mecánica 5b)", h2_style))
    e.append(Paragraph(
        "La lente económica es opcional. Cuando hay datos de costo y "
        "beneficio se calcula el <b>MVPF</b> (Marginal Value of Public Funds) "
        "de Hendren &amp; Sprung-Keyser (<i>A Unified Welfare Analysis of "
        "Government Policies</i>, QJE 2020):",
        body_style))
    e.append(Paragraph("MVPF = beneficio_total / costo_neto_gobierno", formula_style))
    e.append(Paragraph(
        "El insight central de los autores es que <b>MVPF &gt; 1 implica que "
        "la política es Pareto-superior</b>: produce más bienestar para los "
        "receptores que el costo neto al gobierno, incluyendo efectos fiscales "
        "futuros (impuestos generados por mayor renta, ahorros en otros "
        "programas). La base pública <i>policyimpacts.org</i> compara cientos "
        "de políticas en EEUU con esta métrica; el análogo LATAM aún no existe.",
        body_style))
    e.append(Paragraph(
        "Cuando los beneficios no son monetizables (educación, salud, vidas) "
        "se calcula el <b>CEA</b> (Cost-Effectiveness Analysis) de J-PAL:",
        body_style))
    e.append(Paragraph("CEA = costo_total / outcome_total  (COP por unidad)", formula_style))
    e.append(Paragraph(
        "El CEA evita la valoración monetaria de beneficios, lo que lo hace "
        "operativamente accesible para sectoriales sociales. J-PAL mantiene "
        "una base abierta de comparación de CEA por sector — útil para "
        "benchmarks pero limitada para Colombia (la mayoría son evaluaciones "
        "en África e India).",
        body_style))
    e.append(Paragraph(
        "El módulo NO incorpora (todavía) tasa social de descuento, weights "
        "distribucionales ni horizonte temporal en años. Para análisis "
        "rigurosos de costo-beneficio social ver el Green Book del HM Treasury "
        "(2022, actualizado) o la guía de Análisis Económico del DNP. "
        "Trade-off consciente: simplicidad operativa sobre rigor financiero.",
        callout_style))

    e.append(Paragraph("8 · Decisión final (mecánica 6)", h2_style))
    e.append(Paragraph(
        "El módulo deja la decisión final al humano. Howard (1968) y Keeney "
        "(1992) son explícitos en este punto: el análisis cuantitativo (score, "
        "MVPF, CEA) <i>informa</i> la decisión, no la sustituye. La razón es "
        "doble: (a) los ratings 1-5 contienen incertidumbre que el modelo no "
        "captura; (b) la decisión final integra consideraciones políticas, "
        "éticas y de oportunidad que están fuera del alcance del análisis "
        "morfológico.",
        body_style))
    e.append(Paragraph(
        "El campo de <b>justificación textual obligatoria</b> documenta el "
        "<i>por qué esta y no la siguiente en ranking</i> — qué sacrificio se "
        "acepta, qué supuestos críticos se asumen, qué condiciones llevarían "
        "a reconsiderar. Esta documentación es lo que distingue una "
        "recomendación auditable del clásico <i>\"porque la financiera dijo "
        "que sí\"</i>.",
        body_style))

    e.append(Paragraph("9 · Estructura del export CONPES light", h2_style))
    e.append(Paragraph(
        "El PDF de export se formatea siguiendo la estructura CONPES (Consejo "
        "Nacional de Política Económica y Social, Colombia): problema → "
        "objetivos → alternativas → análisis → recomendación. La etiqueta "
        "<i>light</i> es explícita: <b>no es CONPES oficial</b>. Un CONPES "
        "oficial requiere un proceso interinstitucional con DNP, sectoriales "
        "y aprobación del Consejo, además de un grado de detalle financiero "
        "que el módulo no exige. El export es un borrador formateado para "
        "presentar a una mesa técnica o como insumo a una formulación CONPES.",
        body_style))

    e.append(Paragraph("10 · Limitaciones conocidas", h2_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Independencia de variables.</b> El análisis morfológico asume variables independientes. En la práctica, las variables de política suelen correlacionarse (ej.: cobertura universal correlaciona con financiamiento por impuesto). El módulo opera con el ideal independiente y delega al usuario la decisión de cuándo agregarlas.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Ratings cualitativos.</b> El score esperado depende de ratings 1-5 subjetivos. El módulo no incorpora intervalos de confianza ni análisis de sensibilidad sobre los ratings — eso queda para una v2 con escenarios what-if.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Cuatro escenarios fijos.</b> RDM en su versión rigurosa puede usar decenas o cientos de escenarios. El módulo se limita a 4 por usabilidad. Lempert (2019, retrospectiva) reconoce que las 4-6 cobertura cubren ~80% de los casos prácticos.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Lente económica simple.</b> Ver sección 7 — no hay tasa de descuento ni weights distribucionales. Para análisis financiero serio, complementar con Green Book HM Treasury o el manual MGA del DNP.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Sin QCA.</b> El análisis morfológico no es QCA (Qualitative Comparative Analysis · Ragin 1987). QCA identifica configuraciones suficientes/necesarias para un outcome a partir de casos empíricos; el módulo opera ex-ante sobre opciones de diseño. Ambos métodos son complementarios; la integración queda para v2.", list_style), leftIndent=15),
    ], bulletType='bullet'))

    e.append(Paragraph("11 · Bibliografía", h2_style))
    refs = [
        "Abadie, A., Diamond, A., &amp; Hainmueller, J. (2010). <i>Synthetic Control Methods for Comparative Case Studies</i>. JASA 105(490): 493–505.",
        "Álvarez, A., &amp; Ritchey, T. (2015). <i>Applications of General Morphological Analysis: From Engineering Design to Policy Analysis</i>. Acta Morphologica Generalis 4(1).",
        "Bardach, E., &amp; Patashnik, E. (2020). <i>A Practical Guide for Policy Analysis: The Eightfold Path to More Effective Problem Solving</i>. 6ª ed. CQ Press.",
        "DNP / Sinergia (2024). <i>Guía Metodológica para Seguimiento y Evaluación de Políticas Públicas</i>. Bogotá: Departamento Nacional de Planeación.",
        "DNP / MGA (2022). <i>Metodología General Ajustada para la formulación y evaluación previa de proyectos</i>. Bogotá: DNP.",
        "Hendren, N., &amp; Sprung-Keyser, B. (2020). <i>A Unified Welfare Analysis of Government Policies</i>. Quarterly Journal of Economics 135(3): 1209–1318.",
        "HM Treasury (2022). <i>The Green Book: Central Government Guidance on Appraisal and Evaluation</i>. Londres: HM Treasury.",
        "Howard, R. A. (1968). <i>The Foundations of Decision Analysis</i>. IEEE Transactions on Systems Science and Cybernetics 4(3): 211–219.",
        "Howard, R. A., &amp; Abbas, A. E. (2015). <i>Foundations of Decision Analysis</i>. Pearson.",
        "Howlett, M., &amp; Mukherjee, I. (eds.) (2017). <i>Handbook of Policy Formulation</i>. Edward Elgar.",
        "J-PAL (2023). <i>Cost-Effectiveness Analysis: Resources and Examples</i>. Cambridge: Abdul Latif Jameel Poverty Action Lab.",
        "Keeney, R. L. (1992). <i>Value-Focused Thinking: A Path to Creative Decisionmaking</i>. Harvard University Press.",
        "Keeney, R. L., &amp; Raiffa, H. (1976). <i>Decisions with Multiple Objectives: Preferences and Value Tradeoffs</i>. Wiley.",
        "Lascoumes, P., &amp; Le Galès, P. (2007). <i>Introduction: Understanding Public Policy through Its Instruments</i>. Governance 20(1): 1–21.",
        "Lempert, R. J., Popper, S. W., &amp; Bankes, S. C. (2003). <i>Shaping the Next One Hundred Years: New Methods for Quantitative, Long-Term Policy Analysis</i>. Santa Monica: RAND.",
        "Lempert, R. J. (2019). <i>Robust Decision Making (RDM)</i>. En Marchau, Walker, Bloemen, Popper (eds.), Decision Making under Deep Uncertainty, Springer.",
        "Lindblom, C. E. (1959). <i>The Science of \"Muddling Through\"</i>. Public Administration Review 19(2): 79–88.",
        "Marchau, V., Walker, W., Bloemen, P., &amp; Popper, S. (eds.) (2019). <i>Decision Making under Deep Uncertainty: From Theory to Practice</i>. Springer Open.",
        "Miller, G. A. (1956). <i>The Magical Number Seven, Plus or Minus Two</i>. Psychological Review 63(2): 81–97.",
        "Mojica, F. J. (1991). <i>La prospectiva: técnicas para visualizar el futuro</i>. Bogotá: Universidad Externado de Colombia.",
        "OCDE/CAD (2021). <i>Applying Evaluation Criteria Thoughtfully</i>. París: OECD Publishing.",
        "Ortegón, E., Pacheco, J. F., &amp; Prieto, A. (2005). <i>Metodología del marco lógico para la planificación, el seguimiento y la evaluación de proyectos y programas</i>. Santiago: CEPAL/ILPES.",
        "Ragin, C. C. (1987). <i>The Comparative Method: Moving Beyond Qualitative and Quantitative Strategies</i>. University of California Press.",
        "Ritchey, T. (2011). <i>Wicked Problems · Social Messes: Decision Support Modelling with Morphological Analysis</i>. Springer.",
        "Salamon, L. M. (ed.) (2002). <i>The Tools of Government: A Guide to the New Governance</i>. Oxford University Press.",
        "Savage, L. J. (1951). <i>The Theory of Statistical Decision</i>. JASA 46(253): 55–67.",
        "Walker, W. E., Lempert, R. J., &amp; Kwakkel, J. H. (2013). <i>Deep Uncertainty</i>. En Encyclopedia of Operations Research and Management Science, Springer.",
        "Weimer, D. L., &amp; Vining, A. R. (2017). <i>Policy Analysis: Concepts and Practice</i>. 6ª ed. Routledge.",
        "Zwicky, F. (1969). <i>Discovery, Invention, Research through the Morphological Approach</i>. Toronto: Macmillan.",
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
