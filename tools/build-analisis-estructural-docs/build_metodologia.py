"""
Genera el PDF "Análisis Estructural · Guía paso a paso" usando reportlab.

Salida: Bases de datos/analisis-estructural/metodologia-paso-a-paso.pdf
Después subir a S3:
  aws s3 cp "Bases de datos/analisis-estructural/metodologia-paso-a-paso.pdf" \
    "s3://elecciones-2026/ricardoruiz.co/bases de datos/analisis-estructural/metodologia-paso-a-paso.pdf" \
    --content-type application/pdf --cache-control "public, max-age=86400"
"""
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY, TA_CENTER
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, ListFlowable, ListItem
)
from reportlab.pdfgen import canvas

# Paleta del módulo (modo noche)
INK       = HexColor("#14110a")
INK_2     = HexColor("#5a5448")
INK_3     = HexColor("#948e80")
ACCENT    = HexColor("#8a1e16")
ACCENT_2  = HexColor("#a02a20")
ACCENT_SOFT = HexColor("#8a1e161a")
PAPER     = HexColor("#f4f3ef")
RULE      = HexColor("#14110a40")

OUT_DIR = Path(__file__).resolve().parents[2] / "Bases de datos" / "analisis-estructural"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "metodologia-paso-a-paso.pdf"

# ────────────────────────── Estilos ──────────────────────────
ss = getSampleStyleSheet()

title_style = ParagraphStyle(
    'title', parent=ss['Heading1'], fontName='Helvetica-Bold',
    fontSize=22, leading=26, textColor=INK, spaceAfter=6, alignment=TA_LEFT
)
subtitle_style = ParagraphStyle(
    'subtitle', parent=ss['BodyText'], fontName='Helvetica-Oblique',
    fontSize=11, leading=14, textColor=INK_2, spaceAfter=18
)
h2_style = ParagraphStyle(
    'h2', parent=ss['Heading2'], fontName='Helvetica-Bold',
    fontSize=14, leading=18, textColor=ACCENT, spaceBefore=18, spaceAfter=8
)
h3_style = ParagraphStyle(
    'h3', parent=ss['Heading3'], fontName='Helvetica-Bold',
    fontSize=11, leading=14, textColor=INK, spaceBefore=10, spaceAfter=4
)
body_style = ParagraphStyle(
    'body', parent=ss['BodyText'], fontName='Helvetica',
    fontSize=10, leading=14, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=8
)
list_style = ParagraphStyle(
    'list', parent=body_style, leftIndent=0, spaceAfter=4
)
mono_style = ParagraphStyle(
    'mono', parent=ss['BodyText'], fontName='Courier',
    fontSize=9, leading=12, textColor=INK_2, spaceAfter=8
)
callout_style = ParagraphStyle(
    'callout', parent=body_style, fontName='Helvetica-Oblique',
    fontSize=9.5, leading=13, textColor=INK_2, leftIndent=10
)
eyebrow_style = ParagraphStyle(
    'eyebrow', parent=ss['BodyText'], fontName='Helvetica-Bold',
    fontSize=8, leading=10, textColor=ACCENT,
    spaceAfter=4
)

# ────────────────────────── Header / footer ──────────────────────────
def header_footer(canvas_obj, doc):
    canvas_obj.saveState()
    # Header line
    canvas_obj.setStrokeColor(RULE)
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(doc.leftMargin, letter[1] - 1.1*cm,
                    letter[0] - doc.rightMargin, letter[1] - 1.1*cm)
    canvas_obj.setFillColor(INK_3)
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.drawString(doc.leftMargin, letter[1] - 1.4*cm,
                          "Análisis Estructural · Ricardo Ruiz")
    canvas_obj.drawRightString(letter[0] - doc.rightMargin, letter[1] - 1.4*cm,
                                "Guía paso a paso · v1.0 · mayo 2026")
    # Footer line
    canvas_obj.line(doc.leftMargin, 1.3*cm,
                    letter[0] - doc.rightMargin, 1.3*cm)
    canvas_obj.drawString(doc.leftMargin, 0.9*cm,
                          "ricardoruiz.co · consultoría en datos y política pública")
    canvas_obj.drawRightString(letter[0] - doc.rightMargin, 0.9*cm,
                                f"Página {doc.page}")
    canvas_obj.restoreState()

# ────────────────────────── Contenido ──────────────────────────
def build():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=2.2*cm, rightMargin=2.2*cm,
        topMargin=2.0*cm, bottomMargin=1.9*cm,
        title="Análisis Estructural · Guía paso a paso",
        author="Ricardo Ruiz · ricardoruiz.co",
        subject="Documentación de uso de la herramienta de análisis estructural"
    )
    elems = []

    # Portada
    elems.append(Paragraph("Análisis Estructural", title_style))
    elems.append(Paragraph("Guía paso a paso para identificar las variables clave de un sistema", subtitle_style))
    elems.append(Spacer(1, 8))
    elems.append(Paragraph(
        "Esta guía acompaña el uso de la herramienta web en "
        "<font color='#8a1e16'>ricardoruiz.co/analisis-estructural.html</font>. "
        "Está pensada para oficinas de planeación territorial, secretarías "
        "sectoriales, consultorías de prospectiva y trabajos académicos. "
        "Recorre las cuatro etapas del análisis y explica cómo leer los tres "
        "lentes complementarios que ofrece la herramienta: MicMac, DEMATEL e ISM.",
        body_style))
    elems.append(Spacer(1, 12))

    # Resumen visual rápido (índice)
    elems.append(Paragraph("Contenido", h3_style))
    toc_rows = [
        ["01", "Qué es el análisis estructural"],
        ["02", "Antes de empezar: cómo definir bien tus variables"],
        ["03", "El wizard de cuatro preguntas"],
        ["04", "Capturar la matriz de influencias"],
        ["05", "Leer los resultados: MicMac, DEMATEL e ISM"],
        ["06", "Modo difuso: cuando la confianza importa"],
        ["07", "Compartir con tu equipo (multiusuario)"],
        ["08", "Errores comunes y cómo evitarlos"],
    ]
    toc = Table(toc_rows, colWidths=[1.2*cm, 13.5*cm])
    toc.setStyle(TableStyle([
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
    elems.append(toc)

    # ─── 01 ─── Qué es
    elems.append(Paragraph("01 · Qué es el análisis estructural", h2_style))
    elems.append(Paragraph(
        "El análisis estructural es una técnica que identifica las pocas "
        "variables clave que mueven un sistema complejo. Surgió en los años "
        "setenta dentro de la <i>escuela francesa de prospectiva estratégica</i> "
        "(LIPSOR, Michel Godet) y se difundió en Colombia desde la Universidad "
        "Externado, donde Francisco José Mojica formó dos generaciones de "
        "consultores y servidores públicos en su uso.",
        body_style))
    elems.append(Paragraph(
        "La idea central es simple. Si tienes un sistema descrito por entre 8 y "
        "30 variables (por ejemplo: seguridad ciudadana en una ciudad, sistema "
        "educativo de un departamento, productividad de una región), no todas "
        "las variables son iguales. Algunas son <b>palancas</b>: si las mueves, "
        "el sistema entero cambia. Otras son <b>resultados</b>: solo cambian "
        "cuando el resto del sistema se transformó. Saber cuáles son cuáles te "
        "permite priorizar inversiones, alinear equipos y construir escenarios "
        "de futuro con argumentos defendibles.",
        body_style))
    elems.append(Paragraph(
        "La herramienta hace todo el cálculo numérico por ti. Tu trabajo es "
        "definir las variables y calificar cómo se influyen entre sí. El "
        "resto es matemática matricial que se ejecuta en tu navegador en "
        "menos de un segundo.",
        body_style))

    # ─── 02 ─── Variables
    elems.append(Paragraph("02 · Antes de empezar: cómo definir bien tus variables", h2_style))
    elems.append(Paragraph(
        "La calidad del análisis depende de las variables. Tres reglas:",
        body_style))
    elems.append(ListFlowable([
        ListItem(Paragraph(
            "<b>Específicas, no genéricas.</b> &quot;Calidad de vida&quot; es demasiado "
            "amplio para ser una variable. &quot;Cobertura de educación media&quot; sí "
            "lo es. Si una variable tuya cabría en cualquier informe del país, "
            "probablemente está demasiado general.",
            list_style), leftIndent=15),
        ListItem(Paragraph(
            "<b>Mutuamente excluyentes.</b> Evita variables que se solapen. "
            "&quot;Pobreza&quot; y &quot;Pobreza multidimensional&quot; juntas confunden el "
            "análisis. Escoge una.",
            list_style), leftIndent=15),
        ListItem(Paragraph(
            "<b>Entre 10 y 25.</b> Por debajo de 8 el análisis pierde resolución; "
            "por encima de 30 la matriz se vuelve impractica de llenar (con 30 "
            "variables son 870 celdas).",
            list_style), leftIndent=15),
    ], bulletType='bullet'))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph(
        "<b>Sugerencia:</b> usa una de las once plantillas de la herramienta como "
        "punto de partida. Editar, agregar y quitar variables es trivial; "
        "empezar desde una página en blanco siempre se demora más.",
        callout_style))

    # ─── 03 ─── Wizard
    elems.append(Paragraph("03 · El wizard de cuatro preguntas", h2_style))
    elems.append(Paragraph(
        "Al hacer clic en <b>Empezar</b> arranca un wizard de cuatro preguntas. "
        "Las respuestas no son rígidas: la herramienta usa la combinación para "
        "sugerirte una de once plantillas, pero siempre puedes cambiarla o "
        "empezar en blanco.",
        body_style))

    wcell_style = ParagraphStyle('wcell', parent=ss['BodyText'], fontName='Helvetica',
                                 fontSize=9, leading=12, textColor=INK)
    wq = [
        ["P1",
         Paragraph("¿Qué tipo de organización eres?", wcell_style),
         Paragraph("Oficina de planeación · Secretaría sectorial · Consultoría o firma · Academia o investigación", wcell_style)],
        ["P2",
         Paragraph("¿Para qué vas a usarlo?", wcell_style),
         Paragraph("Visión de largo plazo · Plan de Desarrollo Territorial · Política sectorial · Diagnóstico participativo", wcell_style)],
        ["P3",
         Paragraph("¿Qué tan técnico es tu equipo?", wcell_style),
         Paragraph("Mixto · Técnico estándar · Técnico avanzado", wcell_style)],
        ["P4",
         Paragraph("¿Sobre qué dominio es el análisis?", wcell_style),
         Paragraph("Desarrollo · Seguridad · Movilidad · Salud · Educación · Economía · Ambiente · Gobernanza", wcell_style)],
    ]
    wt = Table(wq, colWidths=[1.0*cm, 4.6*cm, 9.4*cm])
    wt.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (0,-1), ACCENT),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,-1), 0.3, RULE),
        ('BACKGROUND', (0,0), (0,-1), ACCENT_SOFT),
    ]))
    elems.append(wt)
    elems.append(Spacer(1, 6))
    elems.append(Paragraph(
        "La sugerencia hace un <i>scoring de overlap</i> entre tus respuestas y "
        "los tags de cada plantilla (organización × propósito × nivel × dominio). "
        "El dominio temático tiene el mayor peso. La plantilla sugerida "
        "abre con entre 8 y 18 variables ya cargadas y un perfil de uso "
        "esperado.",
        body_style))

    # ─── 04 ─── Matriz
    elems.append(Paragraph("04 · Capturar la matriz de influencias", h2_style))
    elems.append(Paragraph(
        "Aquí está el corazón del trabajo. Para cada par de variables (A, B), "
        "calificas <b>cuánto influye A sobre B</b> y en qué dirección. La escala "
        "combina dos decisiones del experto: la <b>intensidad</b> (0 a 3) y la "
        "<b>dirección</b> (+ facilita · − inhibe):",
        body_style))
    sc = [
        ["0",  "Nula",            "A no influye sobre B"],
        ["+1", "Facilita débil",  "A promueve a B, pero marginalmente"],
        ["+2", "Facilita medio",  "A promueve a B de forma notoria"],
        ["+3", "Facilita fuerte", "A promueve decisivamente a B"],
        ["−1", "Inhibe débil",    "A frena a B, pero marginalmente"],
        ["−2", "Inhibe medio",    "A frena a B de forma notoria"],
        ["−3", "Inhibe fuerte",   "A frena decisivamente a B"],
        ["P",  "Potencial",       "Relación que no existe hoy pero podría activarse"],
    ]
    st = Table(sc, colWidths=[1.3*cm, 2.2*cm, 11.5*cm])
    st.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (0,-1), 12),
        ('TEXTCOLOR', (0,0), (0,-1), ACCENT),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (1,0), (-1,-1), 10),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,-1), 0.3, RULE),
        ('BACKGROUND', (0,0), (0,-1), ACCENT_SOFT),
    ]))
    elems.append(st)
    elems.append(Spacer(1, 8))

    elems.append(Paragraph("Dos formas de capturar", h3_style))
    elems.append(Paragraph(
        "<b>Modo matriz:</b> ves toda la matriz NxN como una tabla. Cada celda "
        "se cicla con clic (0 → 1 → 2 → 3 → P → 0) o con teclas. Las flechas "
        "te mueven entre celdas. Útil cuando ya tienes claro el sistema y "
        "quieres avanzar rápido.",
        body_style))
    elems.append(Paragraph(
        "<b>Modo guiado:</b> la herramienta te hace una pregunta a la vez, "
        "tipo &quot;¿Cuánto influye [A] sobre [B]?&quot;. Cinco botones grandes "
        "(0/1/2/3/P), barra de progreso, opción de saltar y devolverse. Útil "
        "para llenar la matriz en taller con un grupo.",
        body_style))
    elems.append(Spacer(1, 6))
    elems.append(Paragraph(
        "<b>La diagonal está deshabilitada</b> — una variable no se influye "
        "a sí misma. Cada celda se autoguarda en cuanto la calificas: si "
        "cierras el navegador y vuelves más tarde, todo está donde lo dejaste.",
        callout_style))

    # Sección 05 - Resultados
    elems.append(PageBreak())
    elems.append(Paragraph("05 · Leer los resultados: MicMac, DEMATEL e ISM", h2_style))
    elems.append(Paragraph(
        "La misma matriz se analiza con tres lentes complementarios. En la "
        "pantalla de resultados los tres están en tabs: empieza por MicMac "
        "(es el más intuitivo), confirma con DEMATEL e ISM.",
        body_style))

    elems.append(Paragraph("A · MicMac — cuadrantes motricidad / dependencia", h3_style))
    elems.append(Paragraph(
        "La herramienta eleva la matriz a la k-ésima potencia hasta que el "
        "ordenamiento de las variables se estabilice (típicamente 3 a 6 "
        "iteraciones). Eso hace visibles las relaciones <i>indirectas</i> "
        "— las que se dan a través de cadenas — que el ojo no detecta solo "
        "mirando influencias directas.",
        body_style))
    elems.append(ListFlowable([
        ListItem(Paragraph("<b>Motrices</b> (alta motricidad · baja dependencia): mueven el sistema. Palancas de intervención.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Clave</b> (alta motricidad · alta dependencia): críticas e inestables. Te pueden volar el análisis si las descuidas.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Resultado</b> (baja motricidad · alta dependencia): determinadas por el sistema. Indicadores de salida.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Autónomas</b> (baja motricidad · baja dependencia): bajo poder e independientes. Marginales.", list_style), leftIndent=15),
    ], bulletType='bullet'))

    elems.append(Paragraph("B · DEMATEL — causas / efectos · prominencia", h3_style))
    elems.append(Paragraph(
        "DEMATEL (Fontela &amp; Gabus, Battelle Memorial Institute, 1972) "
        "descompone la matriz en su <i>total relation matrix</i> y de ahí "
        "saca dos números por variable: la <b>prominencia</b> (R+C, cuán "
        "involucrada está la variable en el sistema) y la <b>relación</b> "
        "(R−C, signo positivo = causa, signo negativo = efecto). Es "
        "complementario a MicMac porque captura la dirección causal, no "
        "solo la intensidad.",
        body_style))

    elems.append(Paragraph("C · ISM — jerarquía estructural", h3_style))
    elems.append(Paragraph(
        "ISM (Warfield, 1973) calcula la matriz de alcanzabilidad por "
        "algoritmo de Warshall y extrae niveles por intersección de los "
        "conjuntos de alcance y antecedentes. El resultado es una pirámide: "
        "arriba las variables que <b>determinan</b> el sistema (raíces), "
        "abajo las que <b>resultan</b> de él (hojas). Cambia el umbral si "
        "el sistema queda muy denso o muy disperso.",
        body_style))

    # 06 Difuso
    elems.append(Paragraph("06 · Modo difuso: cuando la confianza importa", h2_style))
    elems.append(Paragraph(
        "Por defecto la herramienta interpreta cada calificación como un "
        "valor exacto. Pero las calificaciones de expertos suelen tener "
        "incertidumbre — sobre todo cuando vienen de un solo experto, de "
        "un panel con desacuerdo o de un dominio en debate metodológico.",
        body_style))
    elems.append(Paragraph(
        "Activa el modo difuso desde el selector <b>Confianza en las "
        "calificaciones</b> en la pantalla de captura:",
        body_style))
    cl = [
        ["Alta", "Sin incertidumbre. Resultados como puntos exactos."],
        ["Media (±0.5)", "Cada valor se interpreta como ±0.5. Útil para paneles de expertos consistentes."],
        ["Baja (±1.0)", "Cada valor se interpreta como ±1.0. Útil para un solo experto o debates abiertos."],
    ]
    ct = Table(cl, colWidths=[3.0*cm, 12.0*cm])
    ct.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9.5),
        ('TEXTCOLOR', (0,0), (0,-1), ACCENT),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('LINEBELOW', (0,0), (-1,-1), 0.3, RULE),
    ]))
    elems.append(ct)
    elems.append(Spacer(1, 6))
    elems.append(Paragraph(
        "Con modo difuso activo, los scatters de MicMac y DEMATEL dibujan "
        "<b>cruces de incertidumbre</b> alrededor de cada punto. Si una "
        "variable cruza la mediana del cuadrante (línea punteada), su "
        "clasificación es <i>sensible</i> al panel de expertos y deberías "
        "discutirla antes de tomar decisiones.",
        body_style))

    # 07 Multiusuario
    elems.append(Paragraph("07 · Compartir con tu equipo (multiusuario)", h2_style))
    elems.append(Paragraph(
        "Si inicias sesión, puedes guardar el análisis en la nube y trabajarlo "
        "con tu equipo. El botón <b>Guardar en la nube</b> aparece en la "
        "barra superior del paso de captura y de resultados.",
        body_style))
    elems.append(ListFlowable([
        ListItem(Paragraph(
            "<b>Invitar colaboradores:</b> en resultados, botón "
            "<i>Invitar colaborador</i>. Ingresa el correo y a esa persona le "
            "llega un link con token válido por 14 días.",
            list_style), leftIndent=15),
        ListItem(Paragraph(
            "<b>Edición concurrente:</b> el sistema hace polling cada 10 "
            "segundos. Si tu colega calificó una celda hace poco, ves un toast "
            "&quot;Cambios de [correo]&quot; y la matriz se actualiza.",
            list_style), leftIndent=15),
        ListItem(Paragraph(
            "<b>Cuotas por plan:</b> Free 1 proyecto · Pro 5 · Premium 25 · "
            "Full 50.",
            list_style), leftIndent=15),
    ], bulletType='bullet'))

    # 08 Errores comunes
    elems.append(Paragraph("08 · Errores comunes y cómo evitarlos", h2_style))
    errors = [
        ("Llenar solo la mitad de la matriz",
         "Las celdas sin información se procesan como 0 (sin influencia). Si "
         "calificaste solo lo que &quot;importa&quot;, el algoritmo va a sobreestimar las "
         "variables que sí calificaste. Recomendación: llena al menos el 60% "
         "de las celdas no diagonales antes de pasar a resultados."),
        ("Mezclar variables &quot;de stock&quot; con &quot;de flujo&quot;",
         "Algunas variables son estados (&quot;Pobreza multidimensional&quot;) y otras "
         "son procesos (&quot;Crecimiento del empleo&quot;). Mezclarlas confunde la "
         "interpretación. Mantente en un solo tipo por análisis."),
        ("Sobreusar el 3 (fuerte)",
         "Si la mitad de tus celdas son 3, perdiste resolución. Reservar el 3 "
         "para las pocas relaciones realmente decisivas hace que el ranking "
         "de variables clave sea informativo."),
        ("Ignorar las variables potenciales (P)",
         "P es para relaciones que no existen hoy pero podrían activarse "
         "(nueva ley, nuevo actor, nuevo programa). Útiles en ejercicios "
         "prospectivos. Si nunca usas P, probablemente estás haciendo solo "
         "diagnóstico actual, no prospectiva."),
        ("Confiar ciegamente en una sola lente",
         "MicMac, DEMATEL e ISM están de acuerdo en lo grueso pero pueden "
         "diferir en lo fino. Las variables que aparecen como clave en las "
         "tres lentes son las más robustas. Las que solo aparecen en una "
         "merecen segundo análisis."),
    ]
    for title, desc in errors:
        elems.append(Paragraph(title, h3_style))
        elems.append(Paragraph(desc, body_style))

    # Cierre
    elems.append(Spacer(1, 12))
    elems.append(Paragraph("¿Dudas?", h3_style))
    elems.append(Paragraph(
        "Escríbenos a <font color='#8a1e16'>contacto@ricardoruiz.co</font> o "
        "a través del formulario en <font color='#8a1e16'>ricardoruiz.co</font>. "
        "Si vas a usar esta herramienta para un proyecto de consultoría o un "
        "documento académico, podemos prepararte un soporte metodológico a la medida.",
        body_style))

    doc.build(elems, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"OK: {OUT} ({OUT.stat().st_size/1024:.1f} KB)")

if __name__ == "__main__":
    build()
