"""
Genera el PDF 'Evaluación de Política · Guía paso a paso' (Sprint B.10 del Lab).
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

OUT_DIR = Path(__file__).resolve().parents[2] / "Bases de datos" / "ev"
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
    c.drawString(doc.leftMargin, letter[1]-1.4*cm, "Evaluación de Política · Ricardo Ruiz")
    c.drawRightString(letter[0]-doc.rightMargin, letter[1]-1.4*cm, "Guía paso a paso · v2.0 · mayo 2026")
    c.line(doc.leftMargin, 1.3*cm, letter[0]-doc.rightMargin, 1.3*cm)
    c.drawString(doc.leftMargin, 0.9*cm, "ricardoruiz.co · consultoría en datos y política pública")
    c.drawRightString(letter[0]-doc.rightMargin, 0.9*cm, f"Página {doc.page}")
    c.restoreState()

def build():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=2.0*cm, bottomMargin=1.9*cm,
        title="Evaluación de Política · Guía paso a paso",
        author="Ricardo Ruiz · ricardoruiz.co",
        subject="Diseño de evaluación de política pública (OCDE-DAC · Mayne · CEPAL · HM Treasury)"
    )
    e = []

    e.append(Paragraph("Evaluación de Política", title_style))
    e.append(Paragraph(
        "Guía paso a paso para diseñar la evaluación de una política pública: pregunta "
        "evaluativa, teoría de cambio, indicadores SMART, método y criterios OCDE-DAC",
        subtitle_style))
    e.append(Paragraph(
        "Esta guía acompaña el uso de la herramienta web en "
        "<font color='#8a1e16'>ricardoruiz.co/evaluacion.html</font>. Es el cuarto módulo "
        "del Lab de Políticas Públicas y Prospectiva, junto con problema público "
        "(Bardach), análisis estructural (MicMac) y análisis de actores (Mactor). "
        "Si los tres primeros te ayudan a <i>diseñar</i> la política, este te ayuda "
        "a <i>diseñar cómo vas a saber si funcionó</i> — antes de implementar.",
        body_style))
    e.append(Spacer(1, 12))

    e.append(Paragraph("Contenido", h3_style))
    toc = [
        ["01", "Qué hace el módulo y para qué sirve"],
        ["02", "Mecánica 1 · pregunta evaluativa (tipo + alcance + Sinergia DNP)"],
        ["03", "Mecánica 2 · teoría de cambio (marco lógico CEPAL)"],
        ["04", "Mecánica 3 · indicadores SMART"],
        ["05", "Mecánica 4 · selector de método (14 métodos · frontera 2020-2026)"],
        ["06", "Mecánica 5 · criterios OCDE-DAC"],
        ["07", "Mecánica 6 · análisis económico (CBA · MVPF · CEA)"],
        ["08", "Mecánica 7 · plan operativo + 3 descargas"],
        ["09", "Pre-Analysis Plan exportable (AEA RCT Registry / OSF)"],
        ["10", "Copiloto IA y cómo aprovecharlo bien"],
        ["11", "Cómo encadenar con los demás módulos del lab"],
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
        "Evaluar bien una política pública no es preguntar <i>¿funcionó?</i> al "
        "final. Es decidir, <b>antes de implementar</b>, qué pregunta vas a "
        "contestar, qué teoría de cambio estás asumiendo, qué vas a medir y con "
        "qué método. El resultado de hacer este trabajo previo es una evaluación "
        "defendible incluso si la política falla en alguna parte.",
        body_style))
    e.append(Paragraph(
        "Para qué te sirve, en concreto:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Defender el plan ante quien financia.</b> Cuando puedes explicar por qué pediste tres meses de línea base y un método cuasi-experimental, dejas de ser tratado como burócrata costoso y empiezas a ser tratado como socio del diseño.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Blindar el análisis contra el p-hacking.</b> Si fijas el plan después de ver los datos, vas a ajustar la evaluación a lo que los datos digan. Registrar el plan antes obliga a reportar los hallazgos contra ese plan, no contra una versión revisada.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Producir un plan formal exportable.</b> El entregable es un documento .md estructurado en 6 secciones, compatible con protocolos Sinergia DNP, y una matriz de indicadores en CSV lista para llevar a Excel o cargar en sistemas de monitoreo.", list_style), leftIndent=15),
    ], bulletType='bullet'))

    e.append(Paragraph("02 · Mecánica 1 · pregunta evaluativa (tipo + alcance + Sinergia DNP)", h2_style))
    e.append(Paragraph(
        "La pregunta evaluativa determina todo lo demás. Una evaluación que "
        "intenta contestar <i>¿el programa funcionó?</i> sin distinguir tipo "
        "de pregunta ni alcance temporal termina midiendo lo más fácil, no lo "
        "más importante. El módulo te pide cuatro cosas:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Tipo de pregunta.</b> Cinco opciones canónicas: descripción (¿qué está pasando?), atribución causal (¿la política causó el cambio?), valor (¿vale la pena lo que cuesta?), proceso (¿cómo se está implementando?), gestión (¿la organización está aprendiendo?). Cada tipo exige métodos distintos en el paso 4.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Alcance temporal.</b> Ex-ante (antes de implementar), concurrente (durante), ex-post (después) o meta-evaluación (evaluar evaluaciones previas).", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Tipología Sinergia DNP.</b> Seis tipos canónicos del sistema colombiano: <i>ejecutiva</i> (capacidad institucional), <i>operaciones</i> (cómo se implementa), <i>resultados</i> (cumple productos y outcomes), <i>impacto</i> (atribución causal del efecto), <i>institucional</i> (capacidad estatal) y <i>mapas de evidencia</i> (síntesis sistemática · Evidence Gap Maps). Alinear la pregunta con la tipología DNP facilita que el plan sea reconocido por Sinergia.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Pregunta principal + sub-preguntas.</b> Una sola pregunta acotada al grupo afectado, la magnitud esperada del efecto, el horizonte temporal y, si es causal, el contrafáctico. Hasta 5 sub-preguntas auxiliares.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "Las clasificaciones (tipo + alcance) condicionan la sugerencia de método del paso 4. "
        "Si cambias el tipo más adelante, la sugerencia se recalcula automáticamente.",
        callout_style))

    e.append(Paragraph("03 · Mecánica 2 · teoría de cambio (marco lógico CEPAL)", h2_style))
    e.append(Paragraph(
        "La teoría de cambio es el puente entre lo que la política <i>hace</i> y "
        "lo que la política <i>logra</i>. Sin ese puente explícito, no hay forma "
        "de saber si un resultado se debió a la intervención o al contexto. El "
        "módulo usa el marco lógico clásico de CEPAL/ILPES (Ortegón, Pacheco &amp; "
        "Prieto, 2005) con cinco niveles:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Insumos.</b> Recursos disponibles: presupuesto, personal, infraestructura, sistemas de información.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Actividades.</b> Lo que hace la política: talleres, capacitaciones, transferencias, regulación.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Productos.</b> Output directo de las actividades: estudiantes con subsidio, capacitaciones dictadas, normas expedidas.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Resultados.</b> Cambios de corto-medio plazo en la población beneficiaria: aumento de asistencia, reducción de deserción.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Impacto.</b> Efecto último sobre el problema. Atribución parcial — el contexto siempre influye.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "Adicionalmente se registran <b>supuestos transversales</b> (hasta 6): "
        "condiciones que deben mantenerse para que la cadena funcione (Mayne, "
        "<i>Contribution Analysis</i>, 2008+).",
        body_style))
    e.append(Paragraph(
        "El módulo trae una plantilla seed de educación. Si tu sector es otro, "
        "el copiloto IA puede validar tu teoría con <i>plan Premium</i>.",
        callout_style))

    e.append(Paragraph("04 · Mecánica 3 · indicadores SMART", h2_style))
    e.append(Paragraph(
        "Un indicador no es una métrica. Una métrica es cualquier cosa que "
        "puedes medir; un indicador es una métrica que captura algo específico "
        "de la teoría de cambio. <b>SMART</b> = Specific, Measurable, "
        "Achievable, Relevant, Time-bound. Si falta uno, el módulo lo marca "
        "automáticamente con un chip ámbar que dice cuál letra falta.",
        body_style))
    e.append(Paragraph(
        "Cada indicador tiene 8 campos: nivel (atado a la teoría de cambio), "
        "nombre, definición operativa, fórmula explícita, fuente verificable, "
        "línea base, meta, frecuencia.",
        body_style))
    e.append(Paragraph(
        "El copiloto IA puede sugerir 4-6 indicadores SMART derivados de tu pregunta "
        "evaluativa y teoría de cambio (plan Pro). Botón <i>+ Agregar</i> los inyecta "
        "directo al state.",
        callout_style))

    e.append(Paragraph("05 · Mecánica 4 · selector de método (14 métodos · frontera 2020-2026)", h2_style))
    e.append(Paragraph(
        "El método se elige por la pregunta, no por la moda. La versión 2 del "
        "módulo trae <b>catorce métodos</b> pre-cargados, actualizados a la "
        "literatura econométrica reciente (2020-2026). Los <i>estado del arte</i> "
        "llevan badge especial para distinguirlos de los clásicos:",
        body_style))
    metodos = [
        ["RCT",                          "Banerjee-Duflo-Kremer · JPAL",                "causal"],
        ["DID escalonado ★",             "Callaway-Sant'Anna 2021 · Sun-Abraham 2021", "causal"],
        ["DID clásico (2 períodos)",     "Card-Krueger 1994",                          "causal"],
        ["Synthetic Control aumentado ★","Ben-Michael-Feller-Rothstein 2021",          "causal"],
        ["Control sintético clásico",    "Abadie-Diamond-Hainmueller 2010",            "causal"],
        ["RDD moderno ★",                "Cattaneo-Keele-Titiunik 2023",              "causal"],
        ["RD clásico",                   "Thistlethwaite-Campbell · Imbens-Lemieux",   "causal"],
        ["Double ML ★",                  "Chernozhukov et al. 2018",                   "causal observacional"],
        ["Causal Forests ★",             "Wager-Athey 2018 · Athey-Tibshirani 2019",  "heterogeneidad"],
        ["Matching / PSM",               "Rosenbaum-Rubin 1983",                       "causal"],
        ["Análisis de Contribución ★",  "Mayne 2024 · WB IEG 2023",                   "valor · proceso · gestión"],
        ["Cualitativo",                  "Patton 2022 · Yin 2018",                     "valor · proceso"],
        ["Mixto (QUANT + QUAL)",         "Creswell-Plano Clark 2017",                  "todo tipo"],
        ["Value-for-Money + MVPF",       "HM Treasury 2022 · Hendren NBER 2020",       "valor · gestión"],
    ]
    mt = Table([["Método", "Autor faro", "Pregunta típica"]] + metodos, colWidths=[4.8*cm, 6.7*cm, 4.0*cm])
    mt.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8.2),
        ('TEXTCOLOR', (0,0), (-1,0), ACCENT),
        ('TEXTCOLOR', (0,1), (-1,-1), INK),
        ('BACKGROUND', (0,0), (-1,0), ACCENT_SOFT),
        ('LINEBELOW', (0,0), (-1,-1), 0.3, RULE),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    e.append(mt)
    e.append(Spacer(1, 6))
    e.append(Paragraph(
        "★ = método estado del arte (2018-2024). La diferencia central frente a "
        "v1: el módulo ahora detecta automáticamente cuando el tratamiento es "
        "<b>escalonado</b> (varias unidades entrando al programa en momentos "
        "distintos) y advierte sobre el sesgo TWFE del DID clásico "
        "(Goodman-Bacon 2021). En ese caso sugiere el estimador ATT(g,t) "
        "de Callaway-Sant'Anna. El método sugerido aparece con badge salmón "
        "según el tipo de pregunta del paso 1. Puedes cambiar la selección — "
        "lo importante es que la decisión sea consciente y quede justificada "
        "en el plan final.",
        callout_style))

    e.append(Paragraph("06 · Mecánica 5 · criterios OCDE-DAC", h2_style))
    e.append(Paragraph(
        "Los seis criterios canónicos (relevance, coherence, effectiveness, "
        "efficiency, impact, sustainability) son el lenguaje franco de la "
        "evaluación internacional desde 1991, actualizados por la OCDE en 2019. "
        "Una evaluación que se posiciona explícitamente frente a cada uno es "
        "leída sin fricción por organismos multilaterales y comités técnicos.",
        body_style))
    e.append(Paragraph(
        "El módulo presenta los 6 criterios como cards con su definición OCDE-DAC "
        "y un campo de auto-evaluación. Si un criterio no aplica a tu caso, lo "
        "puedes marcar con justificación (también es una respuesta válida).",
        body_style))

    e.append(Paragraph("07 · Mecánica 6 · análisis económico (CBA · MVPF · CEA)", h2_style))
    e.append(Paragraph(
        "Tres calculadoras económicas conviven en un mismo paso opcional. La "
        "decisión de cuál usar depende de la pregunta y del público lector:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>CBA · Costo-Beneficio (Green Book HM Treasury 2022).</b> VPN = Σ (B − C) / (1 + r)^t. Tasa de descuento configurable (DNP: 9%; Green Book: 3.5%). Horizonte 1-50 años. Ratio B/C como métrica auxiliar. La calculadora reporta los tres resultados (VPN, ratio, NPV/cost) en moneda colombiana formateada.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>MVPF · Marginal Value of Public Funds (Hendren-Sprung-Keyser 2020).</b> Beneficios netos para receptores / costo neto al gobierno. MVPF &gt; 1 = política Pareto-superior. Diseñado para comparar programas heterogéneos (transferencias, becas, subsidios) en un solo número, evitando la falsa precisión de monetizar todos los beneficios.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>CEA · Cost-Effectiveness (J-PAL).</b> Costo total / outcome total expresado en unidad natural (ej. años adicionales de escolaridad, vidas salvadas, casos prevenidos). Útil cuando monetizar el beneficio es éticamente controvertido o técnicamente imposible.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "El paso es opcional (toggle activo/inactivo). Si se activa, los tres "
        "cálculos quedan incluidos en el plan .md final y en el Pre-Analysis "
        "Plan exportable.",
        callout_style))

    e.append(Paragraph("08 · Mecánica 7 · plan operativo + 3 descargas", h2_style))
    e.append(Paragraph(
        "El módulo cierra con cuatro campos finales: cronograma estimado, equipo "
        "evaluador (con dedicaciones), presupuesto estimado y plan de uso de los "
        "resultados. Estos son los campos que típicamente diferencian un plan "
        "leído de uno archivado.",
        body_style))
    e.append(Paragraph(
        "El entregable son tres descargas:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Plan de evaluación (.md).</b> Documento estructurado en 6 secciones con todo el state: pregunta, teoría, indicadores, método, criterios DAC, plan operativo. Compatible con formato Sinergia/DNP.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Pre-Analysis Plan (.md).</b> Documento estilo AEA RCT Registry / OSF, con hipótesis primarias y secundarias, especificación econométrica explícita, corrección por hipótesis múltiples pre-registrada y protocolo de desviaciones. Ver sección 09.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Matriz de indicadores (.csv).</b> Tabla cruda con SMART score y missing letters. Útil para llevar a Excel, validar con el equipo o cargar en un sistema de monitoreo.", list_style), leftIndent=15),
    ], bulletType='bullet'))

    e.append(Paragraph("09 · Pre-Analysis Plan exportable (AEA RCT Registry / OSF)", h2_style))
    e.append(Paragraph(
        "El Pre-Analysis Plan (PAP) es el blindaje contra el p-hacking. Se "
        "registra <i>antes</i> de recolectar los datos finales; los hallazgos "
        "se reportan contra ese plan, no contra una versión revisada. La "
        "versión 2 del módulo exporta un PAP listo para subir a "
        "socialscienceregistry.org (AEA) o a OSF Registries.",
        body_style))
    e.append(Paragraph(
        "Estructura del PAP generado (13 secciones):",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("Research question + tipología Sinergia DNP + tipo + alcance.", list_style), leftIndent=15),
        ListItem(Paragraph("Hipótesis primarias (H1.k por outcome de impacto/resultado) y secundarias (H2.k por outcome de producto/actividad).", list_style), leftIndent=15),
        ListItem(Paragraph("Outcomes pre-registrados: primarios (impacto/resultados) y secundarios (productos/actividades) con línea base, meta y frecuencia.", list_style), leftIndent=15),
        ListItem(Paragraph("Teoría de cambio (CEPAL/ILPES) con supuestos críticos.", list_style), leftIndent=15),
        ListItem(Paragraph("Estrategia de identificación + especificación econométrica explícita (Y_it = α_i + λ_t + β·T_it + ε; ATT(g,t) si DID escalonado; pesos ridge si SC aumentado; etc.).", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Corrección por hipótesis múltiples (MHT).</b> Bonferroni con k ≤ 3 outcomes; Holm o Romano-Wolf con k ≤ 8; Benjamini-Hochberg FDR ≤ 0.10 con k ≥ 9. Anderson 2008 JASA · List-Shaikh-Xu 2019 Exp Econ.", list_style), leftIndent=15),
        ListItem(Paragraph("Heterogeneidad pre-especificada: sexo, edad, territorio, valor línea base, etnia, dosis-respuesta. Cualquier subgrupo no listado se reporta como exploratorio.", list_style), leftIndent=15),
        ListItem(Paragraph("Cálculo de poder (placeholder con inputs: take-up, ICC, atrición, N tratamiento/control, SD baseline).", list_style), leftIndent=15),
        ListItem(Paragraph("Análisis económico (si el toggle del paso 6 está activo): CBA + MVPF + CEA con análisis de sensibilidad sobre la tasa de descuento.", list_style), leftIndent=15),
        ListItem(Paragraph("Criterios OCDE-DAC (pre-compromiso cualitativo).", list_style), leftIndent=15),
        ListItem(Paragraph("Limitaciones conocidas + <b>protocolo de desviaciones</b>: cualquier ajuste post-registro debe documentarse en un addendum fechado antes del unblinding; lo contrario se reporta como exploratorio (Olken 2015 JEP).", list_style), leftIndent=15),
        ListItem(Paragraph("Referencias y anclajes metodológicos (AEA · BITSS · OECD-DAC · DNP Sinergia · Mayne · Callaway-Sant'Anna · Cattaneo · Hendren).", list_style), leftIndent=15),
    ], bulletType='bullet'))

    e.append(Paragraph("10 · Copiloto IA y cómo aprovecharlo bien", h2_style))
    e.append(Paragraph(
        "El módulo incluye tres acciones del copiloto IA distribuidas en el flow:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Sugerir indicadores</b> (Pro+). En el paso 3, dado tu pregunta y tu teoría de cambio, propone 4-6 indicadores SMART listos para agregar con un click.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Revisar teoría de cambio</b> (Premium+). En el paso 2, detecta saltos lógicos, supuestos implícitos, niveles desbalanceados e impactos vagos. Sugiere supuestos transversales faltantes.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Generar lectura del plan</b> (Premium+). En el paso final, interpreta la coherencia pregunta→método→indicadores→criterios. Identifica fortalezas, riesgos del método y puntos a cerrar antes de comité.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "El copiloto <i>sugiere</i>; el humano <i>decide</i>. Las propuestas vienen con "
        "botón <i>+ Agregar</i> para inyectarlas al state, pero revisa y edita antes "
        "de defender el plan ante un comité — el modelo no conoce tu contexto operativo.",
        callout_style))

    e.append(Paragraph("11 · Cómo encadenar con los demás módulos del lab", h2_style))
    e.append(Paragraph(
        "El módulo de Evaluación es el cierre natural del Lab. Idealmente "
        "llega al final: tienes el problema enmarcado, las palancas del sistema "
        "identificadas y los actores mapeados. Cuándo encadenar:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Antes:</b> si tu política no tiene un problema bien enmarcado, evaluar es evaluar la respuesta equivocada. Empieza por <i>problema público</i>.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Paralelo:</b> tu teoría de cambio se beneficia del <i>análisis estructural</i> (qué variables mueven el sistema) — las palancas identificadas son candidatos a indicadores de resultado.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Después:</b> el plan de evaluación debe ser defendido ante actores con intereses. <i>Mactor</i> te mapea quiénes son y dónde tienes que negociar el alcance o el método.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Spacer(1, 10))
    e.append(Paragraph(
        "El lab está pensado para encadenar. Los cuatro módulos comparten chasis "
        "visual y la información del state se pasa manualmente entre uno y otro "
        "(no automáticamente — eso es por diseño, para que el re-trabajo del "
        "analista sea consciente).",
        body_style))

    doc.build(e, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"✓ Generado: {OUT}")
    print(f"  Tamaño: {OUT.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    build()
