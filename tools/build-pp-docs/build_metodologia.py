"""
Genera el PDF 'Problema Público · Guía paso a paso' (Sprint A.6 del Lab PP).
Sin dependencias externas además de reportlab (ya disponible en el proyecto).
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

# Paleta — espejo del módulo (modo día por defecto, papel claro para imprimir)
INK = HexColor("#14110a"); INK_2 = HexColor("#5a5448"); INK_3 = HexColor("#948e80")
ACCENT = HexColor("#8a1e16"); ACCENT_SOFT = HexColor("#8a1e161a")
PAPER = HexColor("#f4f3ef"); RULE = HexColor("#14110a40")

OUT_DIR = Path(__file__).resolve().parents[2] / "Bases de datos" / "pp"
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
    c.drawString(doc.leftMargin, letter[1]-1.4*cm, "Problema Público · Ricardo Ruiz")
    c.drawRightString(letter[0]-doc.rightMargin, letter[1]-1.4*cm, "Guía paso a paso · v1.0 · mayo 2026")
    c.line(doc.leftMargin, 1.3*cm, letter[0]-doc.rightMargin, 1.3*cm)
    c.drawString(doc.leftMargin, 0.9*cm, "ricardoruiz.co · consultoría en datos y política pública")
    c.drawRightString(letter[0]-doc.rightMargin, 0.9*cm, f"Página {doc.page}")
    c.restoreState()

def build():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=2.0*cm, bottomMargin=1.9*cm,
        title="Problema Público · Guía paso a paso",
        author="Ricardo Ruiz · ricardoruiz.co",
        subject="Diseño de políticas públicas con método (Bardach · Ortegón · Torres-Melo)"
    )
    e = []

    # ─── Portada ─────────────────────────────────────────────────────────
    e.append(Paragraph("Problema Público", title_style))
    e.append(Paragraph(
        "Guía paso a paso para definir un problema público, construir alternativas "
        "y compararlas con criterios explícitos antes de comprometerse con una decisión",
        subtitle_style))
    e.append(Paragraph(
        "Esta guía acompaña el uso de la herramienta web en "
        "<font color='#8a1e16'>ricardoruiz.co/problema-publico.html</font>. "
        "Forma parte del Lab de Políticas Públicas y Prospectiva, junto con los "
        "módulos de análisis estructural (variables) y análisis de actores (Mactor). "
        "Si el análisis estructural te dice <i>qué piezas mover</i> y Mactor te dice "
        "<i>quiénes tienen poder sobre ellas</i>, Problema Público te ayuda a fijar "
        "<i>qué exactamente</i> estás tratando de resolver y <i>con qué criterios</i> "
        "vas a defender una alternativa frente a un comité.",
        body_style))
    e.append(Spacer(1, 12))

    # ─── Contenido ───────────────────────────────────────────────────────
    e.append(Paragraph("Contenido", h3_style))
    toc = [
        ["01", "Qué hace el módulo y para qué sirve"],
        ["02", "Antes de empezar: del síntoma al problema"],
        ["03", "Definir el problema (formulario o árbol)"],
        ["04", "Diagnóstico de complejidad: test Rittel-Webber"],
        ["05", "Escoger el marco analítico"],
        ["06", "Acopiar evidencia"],
        ["07", "Construir alternativas (la regla del baseline)"],
        ["08", "Establecer criterios ANTES de comparar"],
        ["09", "Comparar y leer el ranking"],
        ["10", "Entregables: memo · issue paper · matriz CSV"],
        ["11", "Copiloto IA y cómo aprovecharlo bien"],
        ["12", "Cómo encadenar con los demás módulos del lab"],
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
    e.append(Paragraph("01 · Qué hace el módulo y para qué sirve", h2_style))
    e.append(Paragraph(
        "Una política pública no empieza con una solución, empieza con un "
        "problema bien planteado. Este módulo te lleva por las cinco "
        "decisiones que tu análisis tiene que tomar antes de defender una "
        "alternativa frente a un comité: <b>definir el problema, acopiar "
        "evidencia, construir alternativas, fijar criterios y comparar</b>. "
        "Es una versión condensada del Eightfold Path de Eugene Bardach, "
        "adaptada al contexto colombiano e instrumental.",
        body_style))
    e.append(Paragraph(
        "Para qué te sirve, en concreto:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Blindar tu propuesta contra el sesgo de confirmación.</b> Al fijar los criterios <i>antes</i> de mirar los resultados, te obligas a defender la mejor opción y no la que ya tenías en mente.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Alinear a un equipo.</b> Hacer este ejercicio juntos obliga a poner problema, supuestos y criterios sobre la mesa antes de discutir soluciones.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Producir un memo defendible.</b> El entregable está estructurado: enunciado · evidencia · alternativas · criterios · recomendación. No queda como opinión, queda como argumento.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Spacer(1, 6))

    # ─── 02 ──────────────────────────────────────────────────────────────
    e.append(Paragraph("02 · Antes de empezar: del síntoma al problema", h2_style))
    e.append(Paragraph(
        "El síntoma no es el problema. \"Hay mucha inseguridad\" es un "
        "síntoma; \"los homicidios juveniles en la zona X subieron 30 % en "
        "24 meses concentrados en barrios Y y Z\" es un problema enunciable. "
        "El wizard de síntoma del módulo te ayuda a hacer ese salto con "
        "cuatro preguntas:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>¿Qué síntoma observas?</b> En una frase. Es lo que un ciudadano cualquiera notaría.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>¿Quiénes lo padecen específicamente?</b> Grupo demográfico + lugar. Descarta el \"todos en general\".", list_style), leftIndent=15),
        ListItem(Paragraph("<b>¿Desde cuándo y cómo está cambiando?</b> Trayectoria. Sin esto no sabrás si la política está funcionando.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>¿Qué fuente o cifra inicial lo respalda?</b> Una sola fuente clave por ahora; las demás se acopian en el paso 2.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "El módulo arma un <i>borrador</i> del enunciado en vivo con tus respuestas. "
        "Lo puedes aceptar tal cual o editar libremente en el siguiente paso. Si ya "
        "tienes el problema claro, hay un botón para saltar este wizard.",
        callout_style))

    # ─── 03 ──────────────────────────────────────────────────────────────
    e.append(Paragraph("03 · Definir el problema (formulario o árbol)", h2_style))
    e.append(Paragraph(
        "El paso central es el <b>enunciado del problema</b>: una frase concreta "
        "con <i>qué pasa, dónde, cuánto y desde cuándo</i>. Evita verbos vagos "
        "como \"mejorar\" o \"fortalecer\" — no son medibles. Complementas con "
        "magnitud (cifra + unidad), urgencia (alta / media / baja) y grupos "
        "afectados (chips editables).",
        body_style))
    e.append(Paragraph("Modo árbol del problema (CEPAL · Ortegón)", h3_style))
    e.append(Paragraph(
        "El módulo ofrece una vista alternativa de árbol: causas raíz arriba, "
        "problema central al medio, efectos abajo. Es el método clásico de "
        "CEPAL/ILPES popularizado por Edgar Ortegón. Las <b>causas raíz</b> "
        "son candidatas naturales a variables del análisis estructural; los "
        "<b>efectos</b> ayudan a aterrizar la magnitud del problema en algo que "
        "el comité reconozca.",
        body_style))
    e.append(Paragraph(
        "Hasta 5 causas y 5 efectos. Cada nodo es editable con un click.",
        callout_style))

    # ─── 04 ──────────────────────────────────────────────────────────────
    e.append(Paragraph("04 · Diagnóstico de complejidad: test Rittel-Webber", h2_style))
    e.append(Paragraph(
        "Horst Rittel y Melvin Webber (1973) definieron 10 propiedades que "
        "distinguen un <i>wicked problem</i> de uno bien estructurado. Esto "
        "importa: un problema <b>tame</b> se resuelve con análisis racional "
        "clásico; uno <b>wicked</b> exige diseño participativo y proceso "
        "iterativo. Aplicar el método equivocado al problema equivocado es la "
        "causa principal de políticas que parecen técnicamente impecables pero "
        "fallan en la implementación.",
        body_style))
    e.append(Paragraph(
        "El test propone las 10 propiedades como preguntas SÍ/NO. El score "
        "(0 a 10) clasifica el problema en cuatro tipos:",
        body_style))
    rittel_table = [
        ["Score", "Tipo", "Marco recomendado"],
        ["0-2",   "Tame · bien estructurado",        "Análisis racional / multi-criterio simple"],
        ["3-5",   "Complejo · varias capas",         "Multi-criterio + escenarios adaptativos"],
        ["6-8",   "Wicked · mal estructurado",       "Diseño participativo + co-creación"],
        ["9-10",  "Meta-wicked · sistémico",         "Gobernanza colaborativa de red"],
    ]
    t = Table(rittel_table, colWidths=[1.6*cm, 5.4*cm, 7.4*cm])
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
    ]))
    e.append(t)
    e.append(Spacer(1, 6))
    e.append(Paragraph(
        "No hay respuestas correctas; es tu lectura del caso. Responde por intuición "
        "informada y luego ajusta si el grupo no se siente representado por el resultado.",
        callout_style))

    # ─── 05 ──────────────────────────────────────────────────────────────
    e.append(Paragraph("05 · Escoger el marco analítico", h2_style))
    e.append(Paragraph(
        "Tras el test, el módulo te muestra 4 marcos analíticos posibles, con "
        "el sugerido marcado. Cada uno tiene una lógica distinta y un costo "
        "metodológico distinto:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Racional simple · multi-criterio</b> (Bardach · CEPAL). La matriz alternativas × criterios que ya tiene este módulo basta. Funciona porque el problema está bien estructurado, las alternativas son finitas y los criterios consensuables.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Multi-criterio + escenarios adaptativos</b> (Walker &amp; Marchau · Lempert). A la matriz se le añade exploración de futuros alternativos y revisión periódica de la decisión. La política se diseña para ser robusta ante varios escenarios, no óptima para uno solo.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Diseño participativo + co-creación</b> (Roberts · Head &amp; Alford). El método se vuelve tan importante como el contenido. Talleres iterativos con afectados, expertos y opositores. La calidad se mide por la legitimidad del proceso.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Gobernanza colaborativa de red</b> (Ansell &amp; Gash · Provan). Ningún actor solo puede resolverlo. Se diseña la red de organizaciones que va a tomar decisiones distribuidas, sus reglas de juego y sus mecanismos de coordinación.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Spacer(1, 4))
    e.append(Paragraph(
        "Puedes cambiar la selección — lo importante es que la decisión sea consciente. "
        "El marco elegido se incluye en el memo y el issue paper como anclaje teórico.",
        callout_style))

    # ─── 06 ──────────────────────────────────────────────────────────────
    e.append(Paragraph("06 · Acopiar evidencia", h2_style))
    e.append(Paragraph(
        "Toda afirmación necesita una fuente. Aquí coleccionas las cifras y "
        "referencias que sostienen tu problema y, después, tus alternativas. "
        "Una evidencia débil es una alternativa débil — y un comité técnico "
        "tarda 30 segundos en detectar una cifra sin fuente.",
        body_style))
    e.append(Paragraph(
        "Cada fila tiene: <b>fuente</b> (institución), <b>año</b>, <b>dato/cifra</b>, "
        "<b>link/referencia</b> y <b>nota</b> opcional. El módulo trae un atajo "
        "\"Cargar 3 fuentes típicas\" que pre-llena DANE, TerriData y datos.gov.co — "
        "los repositorios de partida más útiles en Colombia.",
        body_style))

    # ─── 07 ──────────────────────────────────────────────────────────────
    e.append(Paragraph("07 · Construir alternativas (la regla del baseline)", h2_style))
    e.append(Paragraph(
        "Una alternativa es una <b>opción real de política</b>, no un objetivo. "
        "\"Reducir deserción\" no es una alternativa; \"becas condicionadas a "
        "permanencia + subsidio de transporte\" sí lo es. Entre 3 y 5 alternativas "
        "es el rango útil: menos no compara, más se vuelve difícil de defender.",
        body_style))
    e.append(Paragraph("La regla del baseline (no hacer nada)", h3_style))
    e.append(Paragraph(
        "El módulo trae siempre una primera alternativa fija: <b>\"No hacer "
        "nada\"</b> como baseline. <b>Esto no es retórica</b>: sin baseline, "
        "no puedes argumentar que valga la pena moverse. Si tu alternativa "
        "ganadora no le saca diferencia clara al baseline en la matriz de "
        "comparación, significa que el modelo no justifica el costo de la "
        "intervención — y eso es valioso saberlo <i>antes</i> del comité.",
        body_style))
    e.append(Paragraph(
        "El baseline no se puede eliminar; sí se puede renombrar si quieres redefinirlo "
        "(por ejemplo, \"continuar con el programa actual\" en vez de \"no hacer nada\").",
        callout_style))

    # ─── 08 ──────────────────────────────────────────────────────────────
    e.append(Paragraph("08 · Establecer criterios ANTES de comparar", h2_style))
    e.append(Paragraph(
        "Los criterios deben quedar <b>explícitos antes de comparar</b> — este es "
        "el blindaje contra el sesgo de confirmación. Si los defines después de "
        "ver los resultados, vas a ajustarlos para favorecer tu intuición. Este "
        "sesgo es la falla más común en análisis de política y la razón por la "
        "que el método separa estrictamente esta mecánica de la siguiente.",
        body_style))
    e.append(Paragraph(
        "El módulo trae 5 criterios por defecto (eficiencia, equidad, "
        "factibilidad política, costo, sostenibilidad) con pesos editables. "
        "No exige que los pesos sumen 100 — los normaliza internamente al "
        "calcular el score. Puedes agregar, renombrar o eliminar criterios "
        "(mínimo 2, máximo 8). El copiloto IA puede revisarte la lista para "
        "detectar solapamientos y ausencias (plan Premium).",
        body_style))

    # ─── 09 ──────────────────────────────────────────────────────────────
    e.append(Paragraph("09 · Comparar y leer el ranking", h2_style))
    e.append(Paragraph(
        "Para cada par (alternativa, criterio) calificas de 1 a 5 cómo se "
        "desempeña la alternativa en ese criterio. Cada clic en una celda sube "
        "el valor (1 → 2 → … → 5 → vuelve a 1). El score final se calcula como:",
        body_style))
    e.append(Paragraph(
        "<font name='Courier'>score_i = Σ_j  valor_ij × (peso_j / Σ_k peso_k)</font>",
        callout_style))
    e.append(Paragraph(
        "El módulo muestra el ranking con barras horizontales, ordenado de "
        "mayor a menor, con la ganadora resaltada. Si una celda no tiene valor, "
        "cuenta como 0 — no se rellena implícitamente para no inflar "
        "artificialmente el score de las alternativas mal documentadas.",
        body_style))

    # ─── 10 ──────────────────────────────────────────────────────────────
    e.append(Paragraph("10 · Entregables: memo · issue paper · matriz CSV", h2_style))
    e.append(Paragraph(
        "El módulo produce tres entregables descargables en el paso final:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Memo de política (.md)</b>. Resumen ejecutivo estructurado: problema, evidencia, alternativas, criterios, recomendación. Markdown legible en cualquier visor; útil para compartir por email o pegar en Notion / Confluence.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Issue Paper Bardach (.md)</b>. Formato académico extendido en 8 secciones: contexto histórico, afirmación del problema (con árbol y diagnóstico Rittel-Webber), partes interesadas, alternativas evaluadas, criterios, recomendación con warning si el baseline gana, plan de implementación a 30/90/180 días, referencias.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Matriz de comparación (.csv)</b>. La tabla cruda alternativas × criterios con scores y pesos. Útil para llevar a Excel, exploración propia o comité técnico.", list_style), leftIndent=15),
    ], bulletType='bullet'))

    # ─── 11 ──────────────────────────────────────────────────────────────
    e.append(Paragraph("11 · Copiloto IA y cómo aprovecharlo bien", h2_style))
    e.append(Paragraph(
        "El módulo incluye tres acciones de copiloto IA distribuidas en el flow:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Sugerir alternativas</b> (Pro+). En el paso 3, dado tu enunciado del problema, el copiloto propone 3-5 intervenciones de política concretas que no estén en tu lista actual.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Revisar criterios</b> (Premium+). En el paso 4, detecta solapamientos entre criterios, ambigüedades, pesos sospechosos y sugiere criterios típicos que estén faltando.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Generar lectura interpretativa</b> (Premium+). En el paso final, redacta la lógica del ranking, supuestos a cuestionar en comité, riesgos políticos probables y siguiente paso accionable.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "El copiloto <i>sugiere</i>; el humano <i>decide</i>. Las propuestas vienen con "
        "botón \"+ Agregar\" para inyectarlas al state, pero siempre revisa y edita "
        "antes de defender el análisis ante un comité.",
        callout_style))

    # ─── 12 ──────────────────────────────────────────────────────────────
    e.append(Paragraph("12 · Cómo encadenar con los demás módulos del lab", h2_style))
    e.append(Paragraph(
        "Problema Público es el primer eslabón natural del Lab. Una vez tienes "
        "el problema bien enunciado y una alternativa ganadora, los otros "
        "módulos te ayudan a estresarla:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Análisis estructural</b> (MicMac · DEMATEL · ISM): si tu alternativa ganadora tiene supuestos fuertes sobre cómo se influyen las piezas del sistema, vale la pena mapearlos antes de defender el memo. Las causas raíz del árbol son tus candidatas naturales a variables.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Análisis de actores</b> (Mactor): tu alternativa recomendada necesita pasar por una mesa política. Mactor mapea quién tiene poder real sobre ella, sus alianzas posibles y los conflictos a arbitrar antes de que exploten.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Evaluación de política</b> (próximamente): diseña el esquema de evaluación de la alternativa elegida — pregunta evaluativa, teoría de cambio, indicadores SMART, método (RCT, diff-in-diff, value-for-money, cualitativo).", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Spacer(1, 10))
    e.append(Paragraph(
        "El lab está pensado para encadenar. Los cuatro módulos comparten chasis "
        "visual y la información del state se puede pasar manualmente entre uno y "
        "otro (no automáticamente — eso es por diseño, para que el re-trabajo del "
        "analista sea consciente y no mecánico).",
        body_style))

    doc.build(e, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"✓ Generado: {OUT}")
    print(f"  Tamaño: {OUT.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    build()
