"""
Genera el PDF 'Evaluación de Política · Respaldo académico'.
Marco teórico, fórmulas, criterios DAC en detalle, bibliografía.
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

OUT_DIR = Path(__file__).resolve().parents[2] / "Bases de datos" / "ev"
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
    c.drawString(doc.leftMargin, letter[1]-1.4*cm, "Evaluación de Política · Ricardo Ruiz")
    c.drawRightString(letter[0]-doc.rightMargin, letter[1]-1.4*cm, "Respaldo académico · v2.0 · mayo 2026")
    c.line(doc.leftMargin, 1.3*cm, letter[0]-doc.rightMargin, 1.3*cm)
    c.drawString(doc.leftMargin, 0.9*cm, "ricardoruiz.co · consultoría en datos y política pública")
    c.drawRightString(letter[0]-doc.rightMargin, 0.9*cm, f"Página {doc.page}")
    c.restoreState()

def build():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=2.0*cm, bottomMargin=1.9*cm,
        title="Evaluación de Política · Respaldo académico",
        author="Ricardo Ruiz · ricardoruiz.co",
        subject="Marco teórico, fórmulas y bibliografía del módulo de Evaluación del Lab de Políticas Públicas"
    )
    e = []

    e.append(Paragraph("Evaluación de Política", title_style))
    e.append(Paragraph("Respaldo académico · marco teórico, fórmulas y bibliografía", subtitle_style))
    e.append(Paragraph(
        "Este documento sostiene metodológicamente las ocho mecánicas del módulo "
        "web de Evaluación (versión 2.0, con literatura 2020-2026 incorporada). "
        "Cubre la justificación de cada decisión de diseño, las fórmulas usadas "
        "y las referencias completas. Pensado para consultores y comités técnicos "
        "que quieran auditar el método.",
        body_style))

    e.append(Paragraph("1 · Marco general del módulo", h2_style))
    e.append(Paragraph(
        "El módulo asume el enfoque <b>theory-based evaluation</b> (Weiss 1995, "
        "Mayne 2008+, Funnell &amp; Rogers 2011) como armazón conceptual, "
        "complementado con métodos contrafactuales modernos (Athey &amp; "
        "Imbens 2017, Abadie 2010, Callaway-Sant'Anna 2021) y los criterios "
        "OCDE-DAC actualizados en 2019 como lenguaje de comunicación con "
        "organismos multilaterales y comités técnicos.",
        body_style))
    e.append(Paragraph(
        "El módulo NO impone un método único. Diferentes preguntas evaluativas "
        "exigen diferentes métodos: una pregunta causal exige contrafáctico, una "
        "de valor exige métodos cualitativos o económicos, una de proceso exige "
        "observación participante. El selector del paso 4 explicita esa decisión "
        "y la deja documentada.",
        body_style))

    e.append(Paragraph("2 · Tipología de preguntas evaluativas (mecánica 1)", h2_style))
    e.append(Paragraph(
        "Patton (<i>Utilization-Focused Evaluation</i>, 4ª ed. 2008; 5ª ed. 2022) "
        "distingue cinco familias de preguntas que el módulo adopta:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Descripción</b> · ¿qué está pasando? Caracteriza magnitud, distribución, perfiles. No pretende atribuir causalidad.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Atribución causal</b> · ¿la política causó el cambio observado? Exige contrafáctico (RCT, DiD, RD, control sintético, matching).", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Valor</b> · ¿vale la pena lo que cuesta? Juicio normativo: costo-beneficio social, value-for-money, equidad distributiva.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Proceso</b> · ¿cómo se está implementando? Fidelidad, calidad operativa, brechas diseño-ejecución.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Gestión</b> · ¿la organización está aprendiendo? Adaptación, decisiones gerenciales, uso de evidencia (Patton, <i>developmental evaluation</i>, 2011).", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "Rossi, Lipsey &amp; Henry (<i>Evaluation: A Systematic Approach</i>, 8ª ed. "
        "2018) complementan con cuatro alcances temporales que el módulo también "
        "registra: ex-ante, concurrente, ex-post y meta-evaluación.",
        body_style))

    e.append(Paragraph("3 · Teoría de cambio y marco lógico (mecánica 2)", h2_style))
    e.append(Paragraph(
        "El módulo adopta el marco lógico clásico de CEPAL/ILPES (Ortegón, "
        "Pacheco &amp; Prieto, 2005) con cinco niveles canónicos: insumos → "
        "actividades → productos → resultados → impacto. Esta estructura es "
        "compatible con el Logical Framework de USAID y el formato de "
        "matriz de marco lógico exigido en formulación de proyectos por la "
        "mayoría de organismos multilaterales en América Latina.",
        body_style))
    e.append(Paragraph(
        "La capa de <b>supuestos transversales</b> proviene de la tradición de "
        "<i>contribution analysis</i> (Mayne 2001, 2008+): para que una cadena "
        "causal funcione, deben mantenerse condiciones contextuales que la "
        "intervención no controla. Documentarlas explícitamente permite "
        "identificar dónde se rompe la cadena cuando algo falla.",
        body_style))
    e.append(Paragraph(
        "Para problemas complejos, Pawson &amp; Tilley (<i>Realistic Evaluation</i>, "
        "1997) proponen formular la teoría como tríadas <b>contexto-mecanismo-"
        "outcome</b>. Esta refinación NO se exige en el módulo (introducirla "
        "agrega complejidad sin que el usuario promedio la aproveche), pero "
        "queda mencionada como ruta de profundización avanzada.",
        body_style))

    e.append(Paragraph("4 · Indicadores SMART y validación (mecánica 3)", h2_style))
    e.append(Paragraph(
        "El acrónimo SMART proviene de Doran (1981) y fue adoptado por la "
        "tradición de gestión por resultados. El módulo lo aplica con cinco "
        "criterios codificados en el validador automático:",
        body_style))
    smart_t = [
        ["Letra", "Criterio", "Validación en el módulo"],
        ["S",     "Specific (específico)",       "Tiene nombre + definición operativa"],
        ["M",     "Measurable (medible)",        "Tiene fórmula explícita"],
        ["A",     "Achievable (alcanzable)",     "Tiene meta concreta"],
        ["R",     "Relevant (relevante)",        "Tiene nivel asignado (teoría de cambio) + fuente verificable"],
        ["T",     "Time-bound (temporal)",       "Tiene frecuencia definida"],
    ]
    st = Table(smart_t, colWidths=[1.4*cm, 5.0*cm, 8.4*cm])
    st.setStyle(TableStyle([
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
    e.append(st)
    e.append(Spacer(1, 6))
    e.append(Paragraph(
        "El chip SMART por fila muestra el score 0-5 y las letras faltantes "
        "(ej. <i>3/5 · falta M+R</i>). La validación es solo informativa: el "
        "módulo no bloquea indicadores parciales — un comité técnico puede "
        "aceptar indicadores en construcción si la línea base aún no se ha "
        "levantado.",
        body_style))

    e.append(Paragraph("5 · Métodos evaluativos · frontera 2020-2026 (mecánica 4)", h2_style))
    e.append(Paragraph(
        "La versión 2 del módulo precarga <b>catorce métodos</b>, con seis "
        "estimadores frontera de la literatura 2018-2024 integrados al lado de "
        "los clásicos. La razón del salto: TWFE (DID clásico con múltiples "
        "períodos y rollout escalonado) produce sesgos serios — pesos negativos, "
        "signos invertidos — documentados por Goodman-Bacon (2021). En contextos "
        "colombianos con políticas que entran por fases (PND territorial, programas "
        "regionales), esto es regla, no excepción.",
        body_style))
    e.append(Paragraph("Métodos causales estado del arte (★)", h3_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>DID escalonado · ATT(g,t)</b> (Callaway &amp; Sant'Anna 2021; Sun &amp; Abraham 2021; Borusyak-Jaravel-Spiess 2024). Estima un ATT por cada cohorte de inicio y período post-tratamiento; agrega vía exposure-weighted average. Evita la contaminación TWFE. Paquete <code>did</code> (R) o <code>csdid</code> (Stata).", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Synthetic Control aumentado</b> (Ben-Michael, Feller &amp; Rothstein 2021). Pesos de Abadie + ridge regression para desesgar el pre-ajuste imperfecto. Inferencia por placebos in-space (Abadie 2010) + p-values exactos. Estándar para 1 unidad tratada con N pequeño.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>RDD moderno</b> (Cattaneo, Keele &amp; Titiunik 2023, <i>A Practical Introduction</i>). Bandwidth óptimo MSE (Calonico-Cattaneo-Titiunik 2014) + bandas robustas + test McCrary de manipulación. Paquete <code>rdrobust</code>.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Double Machine Learning</b> (Chernozhukov et al. 2018, Econometrics Journal). Cross-fitting 5-fold. ML para funciones nuisance (propensity, outcome) preservando inferencia válida del parámetro causal. Paquete <code>DoubleML</code> (R/Python) · <code>EconML</code> (Microsoft).", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Causal Forests</b> (Wager &amp; Athey 2018; Athey-Tibshirani-Wager 2019). Honest splitting + cross-fitting para estimar efectos heterogéneos (CATE). N ≥ 5.000. Paquete <code>grf</code>.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Análisis de Contribución</b> (Mayne retrospectiva CJPE 2024; WB IEG Quality Guidance 2023). ToC explícita + identificación de riesgos por flecha causal + recolección mixta por riesgo. Narrativa de contribución auditable. Indicado cuando RCT/cuasi-experimental no es factible (reformas institucionales, programas multicomponente).", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph("Métodos clásicos (siguen disponibles)", h3_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>RCT.</b> Banerjee, Duflo &amp; Kremer (Nobel 2019, J-PAL). Asignación aleatoria. Estándar de oro pero caro y a veces inviable.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>DID clásico (2 períodos).</b> Card &amp; Krueger 1994. Solo válido cuando todas las unidades se tratan al mismo tiempo. Si el rollout es escalonado, migrar a DID escalonado.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>RD clásico.</b> Thistlethwaite-Campbell 1960 (original). Imbens-Lemieux 2008. Sensible a bandwidth ad-hoc. Cattaneo 2023 lo reemplaza en el estado del arte.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Control sintético clásico.</b> Abadie, Diamond &amp; Hainmueller 2010. Mejor usar la versión aumentada de Ben-Michael 2021 si el pre-ajuste no es exacto.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Matching / PSM.</b> Rosenbaum &amp; Rubin 1983. Para datos observacionales. Solo controla sesgos observables. Para &gt;20 covariables, DML domina.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Cualitativo.</b> Patton 2022 (5ª ed.); Yin 2018 (6ª ed.). Esencial para preguntas de valor y proceso.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Mixto.</b> Creswell &amp; Plano Clark 2017. QUANT + QUAL. Casi siempre el más defendible ante comités diversos.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Value-for-Money + MVPF.</b> HM Treasury <i>Green Book</i> 2022 + Hendren-Sprung-Keyser MVPF (NBER 2020). Ver sección 7.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "El selector del módulo detecta automáticamente cuando el tratamiento es "
        "<b>escalonado</b> (toggle del paso 4) y emite warning con redirección al "
        "DID escalonado si el usuario tenía DID clásico seleccionado. Esta lógica "
        "implementa el consenso post-2020 sobre la inferencia causal aplicada.",
        callout_style))

    e.append(Paragraph("6 · Corrección por hipótesis múltiples (MHT)", h2_style))
    e.append(Paragraph(
        "Cuando una evaluación reporta efectos sobre múltiples outcomes primarios, "
        "la probabilidad de encontrar al menos un falso positivo crece "
        "rápidamente. Con α = 0.05 y k outcomes independientes, P(al menos un "
        "falso positivo) = 1 − 0.95^k. Para k = 5 outcomes, esa probabilidad "
        "es 23%; para k = 20, supera 64%. El módulo aplica una regla automática "
        "según el número de outcomes primarios pre-registrados:",
        body_style))
    mht_t = [
        ["k primarios", "Corrección recomendada",                    "Justificación"],
        ["1",            "No requerida",                              "Un solo outcome → no hay inflación FWER"],
        ["2-3",          "Bonferroni (α / k)",                        "Control FWER conservador y simple"],
        ["4-8",          "Holm (1979) o Romano-Wolf (2005)",         "Holm domina a Bonferroni; RW captura correlaciones"],
        ["≥9",           "Benjamini-Hochberg FDR ≤ 0.10",            "Control FDR razonable para muchos outcomes"],
    ]
    mt = Table(mht_t, colWidths=[2.4*cm, 5.5*cm, 6.6*cm])
    mt.setStyle(TableStyle([
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
    e.append(mt)
    e.append(Spacer(1, 6))
    e.append(Paragraph(
        "Referencias clave: Anderson (2008, JASA) sobre Romano-Wolf; List, "
        "Shaikh &amp; Xu (2019, Experimental Economics) sobre buenas prácticas "
        "MHT en RCT; Benjamini &amp; Hochberg (1995, JRSS-B) sobre FDR. La "
        "corrección y la justificación quedan registradas en el Pre-Analysis "
        "Plan exportable.",
        body_style))

    e.append(Paragraph("7 · Análisis económico · CBA · MVPF · CEA (mecánica 6)", h2_style))
    e.append(Paragraph(
        "La versión 2 incorpora un paso opcional con tres calculadoras económicas "
        "convivientes. La distinción importa porque cada una pregunta algo "
        "diferente y exige supuestos distintos:",
        body_style))
    e.append(Paragraph("CBA · Cost-Benefit Analysis (Green Book HM Treasury 2022)", h3_style))
    e.append(Paragraph(
        "VPN = Σ_t (B_t − C_t) / (1 + r)^t, con t ∈ [1, h]. El módulo permite "
        "configurar r (DNP: 9%; Green Book: 3.5% ajustado) y h ∈ [1, 50] años. "
        "Reporta VPN en pesos colombianos y B/C como métrica auxiliar. El Green "
        "Book 2022 incorpora <i>weights distribucionales</i> para pesar más los "
        "beneficios sobre poblaciones vulnerables.",
        body_style))
    e.append(Paragraph("MVPF · Marginal Value of Public Funds (Hendren-Sprung-Keyser 2020)", h3_style))
    e.append(Paragraph(
        "MVPF = WTP_recipients / Net cost to government. WTP_recipients = "
        "valor monetario que los beneficiarios darían a la política. Net cost = "
        "costo presupuestal ± efectos fiscales (ahorros por menores beneficios "
        "futuros, mayores impuestos por más empleo, etc.). MVPF &gt; 1 → política "
        "Pareto-superior. El propósito original (Hendren, NBER WP 26144) es "
        "comparar programas heterogéneos (transferencias, becas, capacitación, "
        "seguros) en un solo número, evitando la falsa precisión de monetizar "
        "todos los beneficios sociales.",
        body_style))
    e.append(Paragraph("CEA · Cost-Effectiveness (J-PAL)", h3_style))
    e.append(Paragraph(
        "CEA = Costo total / Outcome total en unidad natural (años adicionales "
        "de escolaridad, vidas salvadas, casos prevenidos, kilogramos de CO₂ "
        "evitados). Útil cuando monetizar el beneficio es éticamente "
        "controvertido o técnicamente imposible. J-PAL publica un repositorio "
        "público de CEAs comparables (povertyactionlab.org/cea).",
        body_style))
    e.append(Paragraph(
        "El PAP exportable incluye los tres números calculados, un disclaimer "
        "sobre el análisis de sensibilidad esperado, y la recomendación de "
        "reportar tornado diagram con los 5 parámetros más sensibles.",
        callout_style))

    e.append(Paragraph("8 · Criterios OCDE-DAC en detalle (mecánica 5)", h2_style))
    e.append(Paragraph(
        "Los criterios DAC fueron definidos por el Development Assistance "
        "Committee de la OCDE en 1991 y actualizados sustancialmente en 2019 "
        "(comunicación oficial OCDE/DAC/STAT(2019)16) para alinear con la "
        "Agenda 2030 de ODS. Estado actual de los seis:",
        body_style))
    dac_t = [
        ["Criterio (EN/ES)",             "Pregunta canónica"],
        ["Relevance / Relevancia",       "¿La intervención está haciendo lo correcto?"],
        ["Coherence / Coherencia",       "¿Encaja con otras intervenciones, políticas y prioridades?"],
        ["Effectiveness / Efectividad",  "¿Está logrando sus objetivos?"],
        ["Efficiency / Eficiencia",      "¿Hace buen uso de los recursos?"],
        ["Impact / Impacto",             "¿Qué diferencia hace? (incluye contrafáctico)"],
        ["Sustainability / Sostenibilidad","¿Los beneficios netos durarán en el tiempo?"],
    ]
    dt = Table(dac_t, colWidths=[5.5*cm, 9.0*cm])
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
        "<b>Coherence</b> es el criterio agregado en la actualización 2019 "
        "(antes solo eran 5). Mide compatibilidad interna (con el resto del "
        "portafolio de la organización ejecutora) y externa (con políticas "
        "nacionales y otros donantes/actores).",
        body_style))
    e.append(Paragraph(
        "El módulo permite marcar un criterio como <i>no aplica</i> con "
        "justificación. Esto es válido y consistente con la guía OCDE-DAC: "
        "no toda evaluación necesita cubrir los 6.",
        callout_style))

    e.append(Paragraph("9 · Pre-Analysis Plan exportable", h2_style))
    e.append(Paragraph(
        "El módulo trata el plan de evaluación como el equivalente público a "
        "un <b>Pre-Analysis Plan</b> (PAP) en investigación experimental. Los "
        "PAP fueron impulsados por el AEA RCT Registry (Olken 2015 JEP) y la "
        "comunidad de pre-registration en ciencias sociales (Nosek et al. 2018 "
        "PNAS). Su lógica:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Antes</b> de recolectar datos finales, se registra qué se va a hacer, cómo y con qué criterios. Timestamp público en socialscienceregistry.org o osf.io.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Durante</b> el análisis, se mantiene el plan; cualquier desviación se documenta en addendum fechado <i>antes</i> del unblinding.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Después</b>, se reportan hallazgos contra el plan; anything no pre-registrado se reporta como exploratorio.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "Esto blinda al evaluador contra el <i>p-hacking</i> (Simmons, Nelson &amp; "
        "Simonsohn 2011 Psych Sci) y el <i>HARKing</i> (Hypothesizing After Results "
        "are Known, Kerr 1998), las dos fallas más extendidas en evaluación de "
        "política pública aplicada.",
        body_style))
    e.append(Paragraph(
        "El módulo exporta un PAP estructurado en 13 secciones (research question, "
        "hipótesis primarias/secundarias, outcomes pre-registrados, teoría de "
        "cambio, identificación + especificación econométrica, MHT correction, "
        "heterogeneidad pre-especificada, cálculo de poder, recolección de datos, "
        "análisis económico opcional, OCDE-DAC, limitaciones + protocolo de "
        "desviaciones, referencias) listo para subir a AEA o OSF.",
        body_style))

    e.append(Paragraph("10 · Sistemas oficiales de monitoreo y evaluación · Colombia", h2_style))
    e.append(Paragraph(
        "El módulo está pensado para ser compatible con tres sistemas "
        "institucionales colombianos:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>SINERGIA</b> · Sistema Nacional de Evaluación de Gestión y Resultados, DNP. CONPES 3134/2001 (creación). Hoy gestiona el monitoreo del PND y evaluaciones de política pública. La <b>tipología de evaluaciones DNP</b> (ejecutiva, operaciones, resultados, impacto, institucional, mapas de evidencia) está integrada al paso 1 del módulo desde la versión 2. La matriz de indicadores .csv del módulo es importable a SINERGIA con ajuste mínimo de columnas.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>SUIFP</b> · Sistema Unificado de Inversiones y Finanzas Públicas. Para proyectos de inversión pública formulados con marco lógico. La teoría de cambio del módulo se mapea directamente a la estructura SUIFP.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>SINERGIA-Seguimiento</b> · módulo de seguimiento a metas del PND con visualización pública. Indicadores SMART exportados por este módulo son compatibles con el formato esperado.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "Como referente internacional, <b>Ivàlua</b> (Institut Català d'Avaluació "
        "de Polítiques Públiques) es la institución pública de referencia en "
        "habla hispana con guías metodológicas abiertas que son consistentes "
        "con la arquitectura de este módulo.",
        body_style))

    e.append(Paragraph("11 · Bibliografía", h2_style))
    refs = [
        "Abadie, A. (2021). Using Synthetic Controls: Feasibility, Data Requirements, and Methodological Aspects. <i>Journal of Economic Literature</i>, 59(2), 391-425.",
        "Abadie, A., Diamond, A., &amp; Hainmueller, J. (2010). Synthetic Control Methods for Comparative Case Studies: Estimating the Effect of California's Tobacco Control Program. <i>Journal of the American Statistical Association</i>, 105(490), 493-505.",
        "Anderson, M. L. (2008). Multiple Inference and Gender Differences in the Effects of Early Intervention: A Reevaluation of the Abecedarian, Perry Preschool, and Early Training Projects. <i>Journal of the American Statistical Association</i>, 103(484), 1481-1495.",
        "Athey, S., &amp; Imbens, G. W. (2017). The State of Applied Econometrics: Causality and Policy Evaluation. <i>Journal of Economic Perspectives</i>, 31(2), 3-32.",
        "Athey, S., Tibshirani, J., &amp; Wager, S. (2019). Generalized Random Forests. <i>Annals of Statistics</i>, 47(2), 1148-1178.",
        "Banerjee, A., &amp; Duflo, E. (2009). The Experimental Approach to Development Economics. <i>Annual Review of Economics</i>, 1, 151-178.",
        "Ben-Michael, E., Feller, A., &amp; Rothstein, J. (2021). The Augmented Synthetic Control Method. <i>Journal of the American Statistical Association</i>, 116(536), 1789-1803.",
        "Benjamini, Y., &amp; Hochberg, Y. (1995). Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing. <i>Journal of the Royal Statistical Society: Series B</i>, 57(1), 289-300.",
        "Borusyak, K., Jaravel, X., &amp; Spiess, J. (2024). Revisiting Event Study Designs: Robust and Efficient Estimation. <i>Review of Economic Studies</i>, 91(6), 3253-3285.",
        "Callaway, B., &amp; Sant'Anna, P. H. C. (2021). Difference-in-Differences with Multiple Time Periods. <i>Journal of Econometrics</i>, 225(2), 200-230.",
        "Calonico, S., Cattaneo, M. D., &amp; Titiunik, R. (2014). Robust Nonparametric Confidence Intervals for Regression-Discontinuity Designs. <i>Econometrica</i>, 82(6), 2295-2326.",
        "Card, D., &amp; Krueger, A. B. (1994). Minimum Wages and Employment: A Case Study of the Fast-Food Industry in New Jersey and Pennsylvania. <i>American Economic Review</i>, 84(4), 772-793.",
        "Cattaneo, M. D., Keele, L., &amp; Titiunik, R. (2023). <i>A Practical Introduction to Regression Discontinuity Designs: Extensions</i>. Cambridge Elements in Quantitative and Computational Methods for the Social Sciences.",
        "Chernozhukov, V., Chetverikov, D., Demirer, M., Duflo, E., Hansen, C., Newey, W., &amp; Robins, J. (2018). Double/Debiased Machine Learning for Treatment and Structural Parameters. <i>The Econometrics Journal</i>, 21(1), C1-C68.",
        "CONPES 3134 de 2001. <i>Lineamientos para el Sistema Nacional de Evaluación de Resultados</i>. DNP, Bogotá.",
        "Creswell, J. W., &amp; Plano Clark, V. L. (2017). <i>Designing and Conducting Mixed Methods Research</i> (3ª ed.). SAGE.",
        "De Chaisemartin, C., &amp; D'Haultfœuille, X. (2022). Two-Way Fixed Effects and Differences-in-Differences with Heterogeneous Treatment Effects: A Survey. <i>The Econometrics Journal</i>, 26(3), C1-C30.",
        "DNP (2014). <i>Guía metodológica para el seguimiento y evaluación de políticas públicas</i>. Dirección de Seguimiento y Evaluación de Políticas Públicas, Bogotá.",
        "Doran, G. T. (1981). There's a S.M.A.R.T. way to write management's goals and objectives. <i>Management Review</i>, 70(11), 35-36.",
        "Funnell, S. C., &amp; Rogers, P. J. (2011). <i>Purposeful Program Theory: Effective Use of Theories of Change and Logic Models</i>. Jossey-Bass.",
        "Goodman-Bacon, A. (2021). Difference-in-Differences with Variation in Treatment Timing. <i>Journal of Econometrics</i>, 225(2), 254-277.",
        "Hendren, N., &amp; Sprung-Keyser, B. (2020). A Unified Welfare Analysis of Government Policies. <i>Quarterly Journal of Economics</i>, 135(3), 1209-1318. NBER Working Paper 26144.",
        "HM Treasury (2022). <i>The Green Book: Central Government Guidance on Appraisal and Evaluation</i>. London: HMSO.",
        "Imbens, G. W., &amp; Lemieux, T. (2008). Regression discontinuity designs: A guide to practice. <i>Journal of Econometrics</i>, 142(2), 615-635.",
        "Imbens, G. W., &amp; Rubin, D. B. (2015). <i>Causal Inference for Statistics, Social, and Biomedical Sciences: An Introduction</i>. Cambridge University Press.",
        "J-PAL (2024). <i>Cost-Effectiveness Analysis: Methodology and Applications in Education and Health</i>. Abdul Latif Jameel Poverty Action Lab.",
        "Kerr, N. L. (1998). HARKing: Hypothesizing After the Results are Known. <i>Personality and Social Psychology Review</i>, 2(3), 196-217.",
        "List, J. A., Shaikh, A. M., &amp; Xu, Y. (2019). Multiple Hypothesis Testing in Experimental Economics. <i>Experimental Economics</i>, 22(4), 773-793.",
        "Mayne, J. (2001). Addressing attribution through contribution analysis: Using performance measures sensibly. <i>The Canadian Journal of Program Evaluation</i>, 16(1), 1-24.",
        "Mayne, J. (2008). <i>Contribution analysis: An approach to exploring cause and effect</i>. ILAC Brief 16.",
        "Mayne, J. (2024). Contribution Analysis: A Retrospective. <i>The Canadian Journal of Program Evaluation</i>, 38(2), 246-260.",
        "Nosek, B. A., Ebersole, C. R., DeHaven, A. C., &amp; Mellor, D. T. (2018). The preregistration revolution. <i>PNAS</i>, 115(11), 2600-2606.",
        "OCDE-DAC (2019). <i>Better Criteria for Better Evaluation: Revised Evaluation Criteria – Definitions and Principles for Use</i>. OECD/DAC Network on Development Evaluation.",
        "Olken, B. A. (2015). Promises and Perils of Pre-Analysis Plans. <i>Journal of Economic Perspectives</i>, 29(3), 61-80.",
        "Ortegón, E., Pacheco, J. F., &amp; Prieto, A. (2005). <i>Metodología del marco lógico para la planificación, el seguimiento y la evaluación de proyectos y programas</i>. Serie Manuales 42, CEPAL/ILPES, Santiago.",
        "Patton, M. Q. (2011). <i>Developmental Evaluation: Applying Complexity Concepts to Enhance Innovation and Use</i>. Guilford Press.",
        "Patton, M. Q. (2022). <i>Qualitative Research &amp; Evaluation Methods</i> (5ª ed.). SAGE.",
        "Pawson, R., &amp; Tilley, N. (1997). <i>Realistic Evaluation</i>. SAGE.",
        "Pearl, J. (2009). <i>Causality: Models, Reasoning and Inference</i> (2ª ed.). Cambridge University Press.",
        "Romano, J. P., &amp; Wolf, M. (2005). Stepwise Multiple Testing as Formalized Data Snooping. <i>Econometrica</i>, 73(4), 1237-1282.",
        "Rosenbaum, P. R., &amp; Rubin, D. B. (1983). The central role of the propensity score in observational studies for causal effects. <i>Biometrika</i>, 70(1), 41-55.",
        "Rossi, P. H., Lipsey, M. W., &amp; Henry, G. T. (2018). <i>Evaluation: A Systematic Approach</i> (8ª ed.). SAGE.",
        "Simmons, J. P., Nelson, L. D., &amp; Simonsohn, U. (2011). False-Positive Psychology. <i>Psychological Science</i>, 22(11), 1359-1366.",
        "Sun, L., &amp; Abraham, S. (2021). Estimating Dynamic Treatment Effects in Event Studies with Heterogeneous Treatment Effects. <i>Journal of Econometrics</i>, 225(2), 175-199.",
        "Thistlethwaite, D. L., &amp; Campbell, D. T. (1960). Regression-discontinuity analysis: An alternative to the ex post facto experiment. <i>Journal of Educational Psychology</i>, 51(6), 309-317.",
        "Wager, S., &amp; Athey, S. (2018). Estimation and Inference of Heterogeneous Treatment Effects Using Random Forests. <i>Journal of the American Statistical Association</i>, 113(523), 1228-1242.",
        "Weiss, C. H. (1995). Nothing as Practical as Good Theory: Exploring Theory-Based Evaluation for Comprehensive Community Initiatives for Children and Families. En J. Connell et al. (eds.), <i>New Approaches to Evaluating Community Initiatives</i>. Aspen Institute.",
        "World Bank IEG (2023). <i>Quality Guidance for Contribution Analysis</i>. Independent Evaluation Group, Washington DC.",
        "Yin, R. K. (2018). <i>Case Study Research and Applications: Design and Methods</i> (6ª ed.). SAGE.",
    ]
    for r in refs:
        e.append(Paragraph("• " + r, ref_style))

    doc.build(e, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"✓ Generado: {OUT}")
    print(f"  Tamaño: {OUT.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    build()
