"""
Genera 'Alternativas de Política · Guía paso a paso' (Sprint C.9 del Lab).
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

OUT_DIR = Path(__file__).resolve().parents[2] / "Bases de datos" / "alt"
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
    c.drawString(doc.leftMargin, letter[1]-1.4*cm, "Alternativas de Política · Ricardo Ruiz")
    c.drawRightString(letter[0]-doc.rightMargin, letter[1]-1.4*cm, "Guía paso a paso · v1.0 · mayo 2026")
    c.line(doc.leftMargin, 1.3*cm, letter[0]-doc.rightMargin, 1.3*cm)
    c.drawString(doc.leftMargin, 0.9*cm, "ricardoruiz.co · consultoría en datos y política pública")
    c.drawRightString(letter[0]-doc.rightMargin, 0.9*cm, f"Página {doc.page}")
    c.restoreState()

def build():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=2.0*cm, bottomMargin=1.9*cm,
        title="Alternativas de Política · Guía paso a paso",
        author="Ricardo Ruiz · ricardoruiz.co",
        subject="Análisis morfológico de Zwicky + Robust Decision Making (Lempert) + MVPF (Hendren) + CEA (J-PAL)"
    )
    e = []

    e.append(Paragraph("Alternativas de Política", title_style))
    e.append(Paragraph(
        "Guía paso a paso para construir alternativas defendibles con análisis morfológico, "
        "robustez en escenarios y lente económica opcional",
        subtitle_style))
    e.append(Paragraph(
        "Esta guía acompaña el uso de la herramienta web en "
        "<font color='#8a1e16'>ricardoruiz.co/alternativas.html</font>. Es la versión "
        "profunda del paso de alternativas del módulo de Problema Público — donde "
        "Bardach te pide enumerar 3-5 opciones, este módulo te obliga a recorrer "
        "el espacio completo de combinaciones, descartar las inviables, y probar "
        "las restantes contra cuatro escenarios antes de recomendar una. "
        "Las cinco mecánicas se basan en escuelas distintas pero complementarias: "
        "el análisis morfológico de Fritz Zwicky (Caltech, 1969) y su evolución "
        "moderna en Tom Ritchey (Swedish Morphological Society, 2011); el Robust "
        "Decision Making de Robert Lempert y Warren Walker (RAND, 2003); y la lente "
        "económica con MVPF (Hendren &amp; Sprung-Keyser, NBER 2020) y CEA (J-PAL).",
        body_style))
    e.append(Spacer(1, 12))

    e.append(Paragraph("Contenido", h3_style))
    toc = [
        ["01", "Qué hace el módulo y por qué importa"],
        ["02", "Mecánica 1 · variables de decisión"],
        ["03", "Mecánica 2 · opciones por variable"],
        ["04", "Mecánica 3 · matriz morfológica (Zwicky)"],
        ["05", "Mecánica 4 · alternativas ensambladas"],
        ["06", "Mecánica 5 · robustez en escenarios + lente económica"],
        ["07", "Mecánica 6 · decisión final + 3 exports"],
        ["08", "Copiloto IA (4 acciones)"],
        ["09", "Cómo encadenar con los demás módulos del lab"],
        ["10", "Ejemplo completo · política de retención escolar"],
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

    e.append(Paragraph("01 · Qué hace el módulo y por qué importa", h2_style))
    e.append(Paragraph(
        "El error más común al construir alternativas en política pública es "
        "enumerar tres opciones evidentes — usualmente <i>statu quo</i>, una "
        "moderada y una radical — y recomendar la moderada. Cuando comparas "
        "tres alternativas, te perdiste las cuarenta y siete que no consideraste. "
        "Una política de cobertura nacional tiene mínimo cuatro variables de "
        "decisión con cuatro opciones cada una: 256 combinaciones posibles. Sin "
        "método, el ojo humano sólo considera tres.",
        body_style))
    e.append(Paragraph(
        "Para qué sirve, en concreto:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Recorrer el espacio completo.</b> El análisis morfológico de Zwicky descompone una alternativa en variables independientes y opciones discretas por variable — cualquier combinación es candidato. La matriz hace visible lo que el ojo no ve.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Defender la decisión.</b> Cuando quien decide pregunta <i>\"¿por qué no esta otra combinación?\"</i>, poder responder <i>\"la consideramos y la descartamos por X en el escenario disruptivo\"</i> en vez de <i>\"no se nos había ocurrido\"</i>.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Aguantar el peor escenario.</b> La alternativa con mejor desempeño esperado puede ser catastrófica en escenarios pesimistas. Robust Decision Making cambia la pregunta de <i>\"¿cuál maximiza el valor esperado?\"</i> a <i>\"¿cuál es la peor que puedo elegir y aceptar?\"</i>.", list_style), leftIndent=15),
    ], bulletType='bullet'))

    e.append(Paragraph("02 · Mecánica 1 · variables de decisión", h2_style))
    e.append(Paragraph(
        "Una <b>variable de decisión</b> es un parámetro sobre el que se construye "
        "la política. No es un objetivo ni un indicador. Cobertura (universal vs "
        "focalizada), financiamiento (impuesto vs crédito), gobernanza "
        "(centralizada vs municipalizada), instrumento (subsidio vs servicio vs "
        "regulación), condicionalidad (libre vs ligada), timing (gradual vs "
        "choque). Entre 3 y 8 variables — menos te deja sin espacio de diseño, "
        "más vuelve la matriz inmanejable. Para una política seria, suelen ser 5 o 6.",
        body_style))
    e.append(Paragraph(
        "El módulo trae <b>seis plantillas de dominio</b> que precargan variables "
        "típicas: cobertura social, reforma fiscal, servicio público, regulación, "
        "seguridad y blanco. Las puedes editar, borrar o complementar. El copiloto "
        "IA (plan Pro+) sugiere 5-7 variables a partir del enunciado del problema.",
        body_style))
    e.append(Paragraph(
        "Cada variable se etiqueta con un <i>tipo</i> del catálogo cerrado "
        "(cobertura, financiamiento, instrumento, gobernanza, condicionalidad, "
        "timing, población, ámbito, modalidad, sostenibilidad, otra). El tipo es "
        "metadata orientativa — no constriñe la edición libre del nombre.",
        callout_style))

    e.append(Paragraph("03 · Mecánica 2 · opciones por variable", h2_style))
    e.append(Paragraph(
        "Tres a cinco opciones por variable. Menos de tres no es análisis "
        "morfológico, es una elección obligada. Más de cinco infla la matriz a "
        "costa de discriminación. Cada opción debe ser <b>distinguible "
        "operativamente</b>: si dos opciones se ejecutan igual, son la misma. "
        "Para variables binarias (sí/no) está bien tener dos.",
        body_style))
    e.append(Paragraph(
        "El copiloto IA (plan Pro+) opera sobre <b>una variable a la vez</b> — "
        "elige la variable del dropdown y dispara la sugerencia. Devuelve 3-5 "
        "opciones específicas para esa variable, consistentes con el contexto "
        "del problema.",
        body_style))

    e.append(Paragraph("04 · Mecánica 3 · matriz morfológica (Zwicky)", h2_style))
    e.append(Paragraph(
        "Fritz Zwicky (Caltech, 1969) propuso descomponer cualquier problema "
        "de diseño en variables independientes y opciones discretas. Cada "
        "<b>columna</b> de la matriz es una variable, cada <b>celda en la "
        "columna</b> es una opción. Una alternativa es una selección de una "
        "opción por columna. Con 5 variables × 4 opciones tienes 1.024 "
        "combinaciones — la mayoría inviable.",
        body_style))
    e.append(Paragraph(
        "El paso clave es <b>marcar las incompatibilidades</b>. Tom Ritchey "
        "(Swedish Morphological Society) llamó a este paso <i>cross-consistency "
        "assessment</i>: identificar pares de opciones que no pueden coexistir "
        "en una alternativa coherente (ej.: cobertura universal + financiamiento "
        "por tarifa al usuario). Una buena matriz reduce el espacio al ~10% manejable.",
        body_style))
    e.append(Paragraph(
        "La matriz tiene dos modos. <b>Marcar incompatibilidades</b>: clic en una "
        "opción, clic en otra opción de variable distinta, queda marcado el par "
        "como incompatible (clic doble para deshacer). <b>Explorar combinación</b>: "
        "selecciona una opción por columna, cuando esté completa y sin conflictos "
        "puedes guardarla como alternativa con un botón.",
        body_style))
    e.append(Paragraph(
        "El módulo cuenta combinaciones brutas (producto de opciones por variable), "
        "pares incompatibles marcados y restantes posibles (brute-force hasta 5.000 "
        "combinaciones — si excede, muestra <i>demasiadas para enumerar</i>).",
        callout_style))

    e.append(Paragraph("05 · Mecánica 4 · alternativas ensambladas", h2_style))
    e.append(Paragraph(
        "De la matriz a alternativas concretas. Una alternativa es una "
        "combinación específica de opciones — una por variable — más un nombre "
        "legible, una descripción operativa, supuestos críticos, costo "
        "aproximado, plazo y riesgo dominante. Máximo 6 alternativas + un "
        "baseline.",
        body_style))
    e.append(Paragraph(
        "La <b>primera card es <i>Statu quo</i></b> (no hacer nada explícito). "
        "Es el baseline contra el que se compara todo. No se elimina pero se "
        "puede renombrar. Hendren &amp; Sprung-Keyser (2020) insisten en que sin "
        "un baseline explícito no puedes hablar de marginal — y la economía del "
        "bienestar es marginal por construcción.",
        body_style))
    e.append(Paragraph(
        "Cada alternativa se ensambla en dos vías: (a) desde la matriz "
        "morfológica modo explorar (botón <i>Guardar como alternativa</i>); o "
        "(b) manual con <i>+ Agregar alternativa manual</i>, después editas el "
        "combo opción por opción. El copiloto IA (plan Premium+) valida la "
        "coherencia entre opciones de una misma alternativa.",
        body_style))

    e.append(Paragraph("06 · Mecánica 5 · robustez en escenarios + lente económica", h2_style))
    e.append(Paragraph(
        "Lempert &amp; Walker (RAND, 2003) propusieron <b>Robust Decision Making</b> "
        "como respuesta al problema de la incertidumbre profunda: cuando no "
        "puedes asignar probabilidades creíbles a futuros distintos, la "
        "alternativa robusta es la que aguanta el peor caso aceptablemente — "
        "no la que maximiza el valor esperado.",
        body_style))
    e.append(Paragraph(
        "El módulo trae <b>cuatro escenarios pre-definidos</b> con probabilidad "
        "subjetiva editable: baseline (40%), optimista (25%), pesimista (25%), "
        "disruptivo (10%). Calificas cada alternativa 1-5 en cada escenario. "
        "El score esperado se calcula como Σ(probabilidad × rating) normalizado. "
        "Hay un <b>bonus de robustez de +0.5</b> si el peor caso de la "
        "alternativa es ≥ 3 — es lo que distingue robustez de promedio.",
        body_style))
    e.append(Paragraph(
        "La <b>lente económica es opcional</b>. Si para una alternativa tienes "
        "costo total y beneficio total en COP, se calcula el MVPF (Marginal "
        "Value of Public Funds, Hendren &amp; Sprung-Keyser NBER 2020): "
        "beneficio/costo. Si MVPF &gt; 1, la política es Pareto-superior. "
        "Si tienes costo y un outcome físico (estudiantes retenidos, vidas "
        "salvadas, etc.), se calcula el CEA (Cost-Effectiveness Analysis, "
        "J-PAL): costo por unidad de outcome.",
        body_style))
    e.append(Paragraph(
        "Llenar la lente económica es opcional y no afecta la robustez. La "
        "razón: para muchas políticas — sobre todo reformas institucionales — "
        "monetizar beneficios es prematuro o imposible. El rating cualitativo "
        "1-5 sigue siendo defendible sin él.",
        callout_style))

    e.append(Paragraph("07 · Mecánica 6 · decisión final + 3 exports", h2_style))
    e.append(Paragraph(
        "La decisión es del humano, no del modelo. El módulo te muestra el "
        "ranking por score final (esperado + bonus robustez) y el score "
        "económico si lo tienes, pero la alternativa recomendada se elige a "
        "mano con justificación textual obligatoria. Documentar el <i>por qué "
        "esta y no la siguiente</i> es lo que vuelve la decisión auditable.",
        body_style))
    e.append(Paragraph(
        "Tres entregables encadenados:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Memo de alternativas (.md).</b> Markdown estructurado en 5 secciones: contexto, variables+opciones, matriz Zwicky con incompatibilidades, alternativas ensambladas, robustez + recomendación. Listo para circular en mesa técnica.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Matriz de robustez (.csv).</b> Tabla con alternativas × escenarios + scores + lente económica. Compatible con Excel y sistemas de soporte a la decisión.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Ficha CONPES light (.pdf).</b> PDF descargable estructurado en formato CONPES: problema → variables → alternativas → análisis de robustez → lente económica → recomendación. <i>No es CONPES oficial</i> — es un borrador formateado para presentar.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "Adicionalmente: botón <b>Enviar a Problema Público</b> que escribe "
        "las alternativas en el state del módulo de Bardach (paso 3), "
        "manteniendo la trazabilidad y permitiendo cerrar el ciclo del "
        "Eightfold Path con tus alternativas profundas.",
        callout_style))

    e.append(Paragraph("08 · Copiloto IA (4 acciones)", h2_style))
    e.append(Paragraph(
        "El módulo incluye cuatro acciones del copiloto IA distribuidas en el flow:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Sugerir variables</b> (Pro+) · paso 1. Dado el enunciado del problema, propone 5-7 variables de decisión típicas con tipo del catálogo y justificación corta.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Sugerir opciones</b> (Pro+) · paso 2. Por variable, propone 3-5 opciones distinguibles consistentes con el contexto.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Validar coherencia</b> (Premium+) · paso 4. Revisa cada alternativa ensamblada y detecta combinaciones operativamente contradictorias. Conservador: sólo señala lo que no funciona, no preferencias.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Narrativa de alternativas</b> (Premium+) · paso 7. Lectura interpretativa del ranking + fortalezas de la recomendada + por_qué_no_la_siguiente + supuestos críticos + condiciones para reconsiderar.", list_style), leftIndent=15),
    ], bulletType='bullet'))
    e.append(Paragraph(
        "El copiloto <i>sugiere</i>; el humano <i>decide</i>. Las propuestas vienen "
        "con botón <i>+ Agregar</i> para inyectarlas al state, pero revisa y edita "
        "antes de defender el plan ante un comité — el modelo no conoce tu "
        "contexto operativo.",
        callout_style))

    e.append(Paragraph("09 · Cómo encadenar con los demás módulos del lab", h2_style))
    e.append(Paragraph(
        "Alternativas es la versión profunda del paso 3 de Problema Público (Bardach). "
        "Cuando encadenar:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Antes:</b> empieza por <i>Problema Público</i> si todavía no enmarcaste el problema, la magnitud, la evidencia y los criterios de decisión. El paso 3 de Bardach trae un editor rápido de alternativas; cuando se queda corto, abres este módulo.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Paralelo:</b> el <i>análisis estructural</i> (MicMac) te dice qué variables mueven el sistema. Las variables motrices son candidatos naturales a variables de decisión en tu matriz morfológica.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Después:</b> antes de publicar la recomendación, abre <i>Mactor</i> para mapear quién aprueba, quién bloquea y dónde tienes que negociar. Una alternativa técnicamente impecable puede ser rechazada por razones políticas.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Cierre:</b> el módulo de <i>Evaluación</i> diseña la pregunta evaluativa, la teoría de cambio, los indicadores SMART y el método (RCT/DiD/RD/SC/cualitativo/VfM) para saber si la alternativa elegida funcionó.", list_style), leftIndent=15),
    ], bulletType='bullet'))

    e.append(Paragraph("10 · Ejemplo completo · política de retención escolar", h2_style))
    e.append(Paragraph(
        "Problema: deserción escolar en grados 9-11 en Ciudad Bolívar (Bogotá), "
        "12% anual. Mecánicas, paso a paso:",
        body_style))
    e.append(Paragraph(
        "<b>Variables (paso 1, plantilla cobertura-social):</b> Cobertura · "
        "Población objetivo · Instrumento · Condicionalidad · Financiamiento · "
        "Gobernanza. <i>(6 variables.)</i>",
        example_style))
    e.append(Paragraph(
        "<b>Opciones (paso 2):</b> Cobertura: <i>universal / focalizada por "
        "SISBEN III / categorizada por riesgo</i>. Población: <i>grados 9-11 / "
        "9-11 + 6-8 con bajo logro</i>. Instrumento: <i>subsidio monetario / "
        "subsidio + tutoría / servicio integral</i>. Condicionalidad: "
        "<i>incondicional / condicionada a asistencia 80% / condicionada + "
        "rendimiento mínimo</i>. Financiamiento: <i>presupuesto general / "
        "tributo a juegos de azar / mixto con sector privado</i>. Gobernanza: "
        "<i>Secretaría de Educación / colegio receptor + SED / mesa "
        "interinstitucional</i>.",
        example_style))
    e.append(Paragraph(
        "<b>Matriz (paso 3):</b> 3 × 2 × 3 × 3 × 3 × 3 = 486 combinaciones "
        "brutas. Se marcan como incompatibles: <i>universal</i> ⟷ <i>tributo a "
        "juegos de azar</i> (no alcanza el presupuesto); <i>incondicional</i> ⟷ "
        "<i>condicionada + rendimiento mínimo</i> (mutuamente excluyentes); "
        "<i>servicio integral</i> ⟷ <i>incondicional</i> (servicio requiere "
        "compromiso). Restantes: ~280.",
        example_style))
    e.append(Paragraph(
        "<b>Alternativas (paso 4, 4 cards más baseline):</b> A1 Statu quo. "
        "A2 <i>Subsidio focalizado condicionado clásico</i>. A3 <i>Servicio "
        "integral focalizado por riesgo</i>. A4 <i>Universal incondicional</i>. "
        "A5 <i>Mixto: subsidio + tutoría con corresponsabilidad</i>.",
        example_style))
    e.append(Paragraph(
        "<b>Robustez (paso 5):</b> Probs 40/25/25/10. Ratings (esperado · peor "
        "caso · final): A1 2.0 · 2 · 2.0. A2 3.6 · 3 · 4.1. A3 4.1 · 3 · 4.6. "
        "A4 3.4 · 2 · 3.4 (peor caso bajo). A5 4.3 · 4 · 4.8. <b>A5 gana</b>: "
        "score esperado alto y peor caso ≥ 4 (bonus +0.5). MVPF de A5 (con "
        "estimación CBA de 1.6) = Pareto-superior.",
        example_style))
    e.append(Paragraph(
        "<b>Decisión (paso 6):</b> Recomendamos A5. Vence a A3 por 0.2 puntos "
        "en score final y por mejor MVPF. Aceptamos sacrificar simplicidad "
        "operativa (mixto requiere coordinación tutoría + transferencia) a "
        "cambio de robustez frente al escenario disruptivo (crisis fiscal: "
        "el subsidio se sostiene, la tutoría se suspende sin cancelar el "
        "programa). Reconsideramos si la SED no puede contratar tutorías a "
        "tiempo o si el censo de bajo logro cae &lt; 15.000 estudiantes.",
        example_style))

    e.append(Spacer(1, 8))
    e.append(Paragraph(
        "Tiempo aproximado de un análisis bien hecho: 2 a 6 horas dependiendo "
        "de la profundidad del equipo. Vale la pena cuando la decisión es "
        "irreversible o costosa.",
        callout_style))

    doc.build(e, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"✓ Generado: {OUT}")
    print(f"  Tamaño: {OUT.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    build()
