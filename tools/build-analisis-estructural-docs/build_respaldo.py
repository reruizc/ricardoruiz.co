"""
Genera el PDF "Análisis Estructural · Respaldo metodológico y académico".

Para defender el rigor de la herramienta ante consultores expertos,
académicos o auditores. Cubre orígenes, formulación matemática, validez,
limitaciones reconocidas en la literatura y bibliografía.

Salida: Bases de datos/analisis-estructural/respaldo-academico.pdf
"""
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, ListFlowable, ListItem
)

INK       = HexColor("#14110a")
INK_2     = HexColor("#5a5448")
INK_3     = HexColor("#948e80")
ACCENT    = HexColor("#8a1e16")
ACCENT_SOFT = HexColor("#8a1e161a")
PAPER     = HexColor("#f4f3ef")
RULE      = HexColor("#14110a40")

OUT_DIR = Path(__file__).resolve().parents[2] / "Bases de datos" / "analisis-estructural"
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
mono_style = ParagraphStyle('mono', parent=ss['BodyText'], fontName='Courier',
    fontSize=9, leading=13, textColor=INK_2, spaceAfter=8, leftIndent=12)
formula_style = ParagraphStyle('formula', parent=ss['BodyText'], fontName='Courier-Bold',
    fontSize=10.5, leading=14, textColor=ACCENT, spaceAfter=10, leftIndent=18, alignment=TA_LEFT)
bib_style = ParagraphStyle('bib', parent=ss['BodyText'], fontName='Helvetica',
    fontSize=9, leading=12, textColor=INK_2, leftIndent=14, firstLineIndent=-14,
    spaceAfter=5, alignment=TA_LEFT)
callout_style = ParagraphStyle('callout', parent=body_style, fontName='Helvetica-Oblique',
    fontSize=9.5, leading=13, textColor=INK_2, leftIndent=10)

def header_footer(c, doc):
    c.saveState()
    c.setStrokeColor(RULE); c.setLineWidth(0.5)
    c.line(doc.leftMargin, letter[1] - 1.1*cm,
           letter[0] - doc.rightMargin, letter[1] - 1.1*cm)
    c.setFillColor(INK_3); c.setFont("Helvetica", 8)
    c.drawString(doc.leftMargin, letter[1] - 1.4*cm,
                 "Análisis Estructural · Ricardo Ruiz")
    c.drawRightString(letter[0] - doc.rightMargin, letter[1] - 1.4*cm,
                       "Respaldo metodológico · v1.0 · mayo 2026")
    c.line(doc.leftMargin, 1.3*cm, letter[0] - doc.rightMargin, 1.3*cm)
    c.drawString(doc.leftMargin, 0.9*cm,
                 "ricardoruiz.co · consultoría en datos y política pública")
    c.drawRightString(letter[0] - doc.rightMargin, 0.9*cm, f"Página {doc.page}")
    c.restoreState()

def build():
    doc = SimpleDocTemplate(
        str(OUT), pagesize=letter,
        leftMargin=2.2*cm, rightMargin=2.2*cm,
        topMargin=2.0*cm, bottomMargin=1.9*cm,
        title="Análisis Estructural · Respaldo metodológico",
        author="Ricardo Ruiz · ricardoruiz.co",
        subject="Fundamentación teórica de la herramienta de análisis estructural"
    )
    e = []

    # Portada
    e.append(Paragraph("Respaldo metodológico y académico", title_style))
    e.append(Paragraph(
        "Fundamentación teórica, formulación matemática, validez y "
        "limitaciones reconocidas. Para defender el rigor del análisis "
        "ante auditores, consultores expertos o comités académicos.",
        subtitle_style))
    e.append(Paragraph(
        "Este documento acompaña la herramienta web de análisis estructural "
        "publicada en <font color='#8a1e16'>ricardoruiz.co/analisis-estructural.html</font>. "
        "Documenta las tres lentes que ofrece la herramienta — MicMac, "
        "DEMATEL e ISM — con su procedencia, formulación, validez interna y "
        "límites; el manejo opcional de incertidumbre (scoring difuso); y la "
        "bibliografía de referencia.",
        body_style))

    # 1. Origen y posición
    e.append(Paragraph("1 · Origen disciplinar y posición epistémica", h2_style))
    e.append(Paragraph(
        "El análisis estructural pertenece a la familia de métodos de "
        "<i>prospectiva estratégica</i> desarrollada en Francia desde los años "
        "setenta, principalmente por Michel Godet en LIPSOR (Laboratoire "
        "d'Investigation en Prospective, Stratégie et Organisation) del CNAM, "
        "París. Godet sistematizó técnicas dispersas — algunas con raíces en "
        "la Battelle Memorial Institute de Estados Unidos en los sesenta — y "
        "las articuló en una caja de herramientas conocida como <i>la prospective</i>: "
        "MICMAC, MACTOR, SMIC, escenarios morfológicos, entre otras.",
        body_style))
    e.append(Paragraph(
        "En Colombia el método llegó por dos vías paralelas. La principal: "
        "<b>Francisco José Mojica Sastoque</b> (Universidad Externado), doctor "
        "de la Universidad de París V – René Descartes (Sorbonne), discípulo "
        "directo de Godet en el grupo <i>laprospective</i>. Mojica dirige el "
        "Centro de Pensamiento Estratégico y Prospectiva del Externado, la "
        "Maestría homónima y el Doctorado en Administración, además de la "
        "Cátedra UNESCO de Estudios de Futuro. Ha dirigido más de cincuenta "
        "estudios prospectivos en Colombia, Venezuela, Ecuador, México y Perú.",
        body_style))
    e.append(Paragraph(
        "La vía latinoamericana complementaria pasa por <b>Javier Medina "
        "Vásquez</b> (Universidad del Valle) y <b>Edgar Ortegón</b> (ILPES / "
        "CEPAL), autores del manual de prospectiva estratégica para América "
        "Latina y el Caribe (CEPAL, Serie Manuales 51, 2006). Ese manual "
        "integra la escuela francesa con escuela anglosajona (Foresight "
        "británico) y adaptaciones al contexto regional (institucionalidad "
        "débil, calidad de datos, volatilidad). La herramienta documentada "
        "aquí se apoya en ambas tradiciones, sin alinear ideológicamente con "
        "ninguna escuela.",
        body_style))
    e.append(Paragraph(
        "<b>Posición epistémica:</b> el análisis estructural es <i>cualitativo "
        "asistido por estructura matemática</i>. Su input — las calificaciones "
        "de influencia — viene del juicio experto. Su mérito está en hacer "
        "explícitas las relaciones indirectas que el ojo humano no ve cuando "
        "observa solo influencias directas. No reemplaza modelos econométricos "
        "ni simulación basada en agentes; los complementa en la fase "
        "exploratoria de un análisis de política pública.",
        body_style))

    # 2. MicMac
    e.append(Paragraph("2 · MICMAC — Matrices d'Impacts Croisés Multiplication Appliquée à un Classement", h2_style))
    e.append(Paragraph(
        "<b>Origen:</b> el método fue formulado por Michel Godet con François "
        "Bourse en 1971 y publicado de forma sistemática en <i>Manuel de "
        "prospective stratégique</i> (Dunod, 1997, 2 vol.). El acrónimo "
        "describe el procedimiento: matriz de impactos cruzados, multiplicación "
        "aplicada a un ordenamiento de variables.",
        body_style))
    e.append(Paragraph("Formulación", h3_style))
    e.append(Paragraph(
        "Sea M una matriz n × n de influencias directas donde "
        "M[i,j] está en {0, 1, 2, 3, P} — la calificación de cuánto influye la "
        "variable i sobre la j (P = potencial, se trata como 1 en la "
        "agregación numérica).",
        body_style))
    e.append(Paragraph("Motricidad directa:  r_i = sum_j M[i, j]", formula_style))
    e.append(Paragraph("Dependencia directa: c_j = sum_i M[i, j]", formula_style))
    e.append(Paragraph(
        "Para capturar las influencias indirectas se eleva M a potencias "
        "sucesivas. Las relaciones de orden k aparecen en M elevado a k. El "
        "criterio de detención es la <i>estabilización del ordenamiento</i>: "
        "se itera hasta que el ranking de motricidad y dependencia de M^k "
        "no cambie respecto a M^(k-1). En la práctica esto ocurre "
        "entre la tercera y la sexta iteración para sistemas de 8 a 30 variables.",
        body_style))
    e.append(Paragraph("Motricidad indirecta:  r*_i = sum_j (M^k)[i, j]", formula_style))
    e.append(Paragraph("Dependencia indirecta: c*_j = sum_i (M^k)[i, j]", formula_style))
    e.append(Paragraph(
        "Las variables se ubican en un plano (c*, r*) y se clasifican según su "
        "posición respecto a la mediana de cada eje en cuatro cuadrantes: "
        "<b>motrices</b>, <b>clave / enlace</b>, <b>resultado / dependientes</b> "
        "y <b>autónomas / excluidas</b>.",
        body_style))
    e.append(Paragraph("Validez interna y limitaciones reconocidas", h3_style))
    e.append(Paragraph(
        "MicMac sigue ampliamente utilizado en publicaciones académicas "
        "recientes (educación, resiliencia nacional, logística humanitaria, "
        "gestión del agua, cadenas de suministro, integración del metaverso, "
        "people analytics — 2020-2025, ver bibliografía). Las críticas "
        "metodológicas reconocidas se concentran en cinco frentes:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Escala ordinal tratada como cardinal.</b> El scoring 0-3 es ordinal pero las operaciones (suma, multiplicación de matrices) son cardinales. La crítica viene del propio Bishop &amp; Hines (2012) y Saritas &amp; Smith (2011); la herramienta la mitiga con el modo difuso opcional (±0.5, ±1.0) que captura la incertidumbre en bandas.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Criterio de convergencia opaco.</b> El número de iteraciones rara vez se justifica formalmente. Esta herramienta hace explícito el criterio (rank stability) y reporta el k al que se estabilizó.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Sesgo del panel de expertos.</b> Quién está en la mesa determina el resultado. El modo difuso ayuda a visualizar qué tan sensibles son las clasificaciones al panel.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Modelo estático.</b> No captura no-linealidades temporales. Para sistemas con dinámicas rápidas se recomienda complementar con simulación basada en agentes.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>No distingue tipo de relación.</b> Una influencia puede ser facilitadora o inhibidora, causal o correlacional. MicMac trata todas igual. La herramienta complementa con DEMATEL para capturar la dirección causa-efecto.", list_style), leftIndent=15),
    ], bulletType='bullet'))

    # 3. DEMATEL
    e.append(PageBreak())
    e.append(Paragraph("3 · DEMATEL — Decision Making Trial and Evaluation Laboratory", h2_style))
    e.append(Paragraph(
        "<b>Origen:</b> desarrollado en el Battelle Memorial Institute, Geneva "
        "Research Centre, por Emilio Fontela y André Gabus entre 1972 y "
        "1976, originalmente para el estudio de problemas complejos del "
        "Club of Rome. El método ha tenido un renacimiento desde los años "
        "2000 con aplicaciones en cadena de suministro, riesgo y gestión "
        "ambiental.",
        body_style))
    e.append(Paragraph("Formulación", h3_style))
    e.append(Paragraph(
        "Partiendo de la misma matriz M de influencias directas:",
        body_style))
    e.append(Paragraph("1. Normalización:  D = M / s, donde s = max(max_i sum_j M[i,j], max_j sum_i M[i,j])", formula_style))
    e.append(Paragraph("2. Total relation matrix:  T = D x (I - D)^(-1)", formula_style))
    e.append(Paragraph("3. R = sumas por fila de T (influencia ejercida)", formula_style))
    e.append(Paragraph("   C = sumas por columna de T (influencia recibida)", formula_style))
    e.append(Paragraph("4. Prominencia = R + C        Relación = R - C", formula_style))
    e.append(Paragraph(
        "El plot (R+C) vs (R-C) separa las variables en cuatro cuadrantes según "
        "intensidad de involucramiento (R+C alto o bajo) y dirección causal "
        "(R-C positivo = causa, R-C negativo = efecto). La inversión de "
        "(I - D) se realiza por eliminación Gauss-Jordan local en el cliente.",
        body_style))
    e.append(Paragraph(
        "<b>Convergencia:</b> el límite teórico T = D x (I - D)^(-1) asume que el "
        "radio espectral de D es menor que 1, condición que se cumple para "
        "matrices normalizadas correctamente. La herramienta verifica la "
        "invertibilidad de (I - D) durante la ejecución; si la matriz es "
        "singular (caso patológico), reporta error y sugiere revisar los "
        "datos.",
        body_style))
    e.append(Paragraph(
        "<b>Comparación con MicMac:</b> DEMATEL es más sensible a la "
        "intensidad relativa de las influencias (la normalización lo absorbe) "
        "pero pierde la lectura ordinal directa. En la práctica, las "
        "variables que aparecen como clave en MicMac y como causas-centrales "
        "en DEMATEL son las más robustas.",
        body_style))

    # 4. ISM
    e.append(Paragraph("4 · ISM — Interpretive Structural Modeling", h2_style))
    e.append(Paragraph(
        "<b>Origen:</b> formulado por John N. Warfield en 1973 mientras "
        "trabajaba en Battelle Memorial Institute. ISM es una técnica de "
        "modelización por grafos dirigidos que ordena las variables del "
        "sistema en niveles jerárquicos según una relación de "
        "alcanzabilidad transitiva.",
        body_style))
    e.append(Paragraph("Formulación", h3_style))
    e.append(Paragraph(
        "Dada la matriz M de influencias directas y un umbral t (en esta "
        "herramienta t en {1, 2, 3}, con default 2):",
        body_style))
    e.append(Paragraph("1. Binarización:  B[i,j] = 1 si M[i,j] >= t, 0 en otro caso. B[i,i] = 1 para todo i.", formula_style))
    e.append(Paragraph("2. Reachability matrix R:  cierre transitivo de B por algoritmo de Warshall.", formula_style))
    e.append(Paragraph("3. Conjuntos:  Reach(i) = {j : R[i,j] = 1}", formula_style))
    e.append(Paragraph("              Antec(i) = {j : R[j,i] = 1}", formula_style))
    e.append(Paragraph("4. Variable i pertenece al nivel actual si  Reach(i) intersección Antec(i) = Reach(i).", formula_style))
    e.append(Paragraph("5. Eliminar variables del nivel y repetir hasta agotar el conjunto.", formula_style))
    e.append(Paragraph(
        "El resultado es una jerarquía en la que el nivel superior contiene "
        "las variables que <i>determinan</i> el sistema (raíces) y el nivel "
        "inferior las que <i>resultan</i> de él (hojas). La herramienta "
        "renderiza la jerarquía como una pirámide con conectores verticales "
        "entre niveles.",
        body_style))
    e.append(Paragraph(
        "<b>Sensibilidad al umbral:</b> ISM es paramétrico. Un t demasiado "
        "bajo genera un sistema denso con un solo nivel; uno demasiado alto, "
        "una jerarquía vacía. Se recomienda probar los tres umbrales "
        "(1, 2, 3) y reportar el que produce una estructura interpretable.",
        body_style))

    # 5. Modo difuso
    e.append(Paragraph("5 · Modo difuso (scoring con bandas de incertidumbre)", h2_style))
    e.append(Paragraph(
        "La crítica ordinal-cardinal mencionada se mitiga con un modo difuso "
        "opcional. Cada calificación v en {0, 1, 2, 3} se interpreta como una "
        "banda triangular degenerada:",
        body_style))
    e.append(Paragraph("Confianza alta:   [v, v]                                    (sin incertidumbre, default)", formula_style))
    e.append(Paragraph("Confianza media:  [max(0, v - 0.5),  min(3, v + 0.5)]", formula_style))
    e.append(Paragraph("Confianza baja:   [max(0, v - 1.0),  min(3, v + 1.0)]", formula_style))
    e.append(Paragraph(
        "Los cálculos de MicMac y DEMATEL corren tres veces: con la matriz de "
        "extremo inferior, central y superior. Los scatters de resultados "
        "dibujan cruces de incertidumbre alrededor de cada punto. Las "
        "variables cuya cruz toca la línea de mediana del cuadrante "
        "son sensibles al panel y deben discutirse.",
        body_style))
    e.append(Paragraph(
        "La implementación se inspira en la familia de <b>Fuzzy MICMAC</b> "
        "documentada por Chang et al. (2007) y Khatwani et al. (2015), "
        "simplificando la representación trapezoidal a una banda simétrica "
        "alrededor del valor central. Versiones futuras incorporarán "
        "scoring triangular completo {min, mod, max} por celda.",
        callout_style))

    # 6. Bibliografía
    e.append(PageBreak())
    e.append(Paragraph("6 · Bibliografía", h2_style))
    e.append(Paragraph("Fuentes primarias", h3_style))
    bib_primary = [
        "Godet, M. (1991). <i>De l'anticipation à l'action: manuel de prospective et de stratégie</i>. Dunod, Paris.",
        "Godet, M., Bourse, F., Chapuy, P. &amp; Menant, I. (1991). <i>Futures studies: a tool-box for problem solving</i>. UNESCO, Paris.",
        "Godet, M. (2000). The art of scenarios and strategic planning: tools and pitfalls. <i>Technological Forecasting and Social Change</i>, 65(1), 3-22.",
        "Fontela, E. &amp; Gabus, A. (1976). <i>The DEMATEL Observer, DEMATEL 1976 Report</i>. Battelle Geneva Research Center, Geneva.",
        "Warfield, J. N. (1973). On arranging elements of a hierarchy in graphic form. <i>IEEE Transactions on Systems, Man, and Cybernetics</i>, SMC-3(2), 121-132.",
        "Warfield, J. N. (1974). Developing interconnection matrices in structural modeling. <i>IEEE Transactions on Systems, Man, and Cybernetics</i>, SMC-4(1), 81-87.",
    ]
    for b in bib_primary: e.append(Paragraph(b, bib_style))

    e.append(Paragraph("Tradición colombiana y latinoamericana", h3_style))
    bib_co = [
        "Mojica, F. J. (2006). <i>Concepto y aplicación de la prospectiva estratégica</i>. Universidad Externado de Colombia, Bogotá.",
        "Mojica, F. J. (2008). <i>Forecasting</i> y <i>foresight</i>: dos escuelas, dos enfoques. <i>Med-UNAB</i>, 11(1).",
        "Medina Vásquez, J. &amp; Ortegón, E. (2006). <i>Manual de prospectiva y decisión estratégica: bases teóricas e instrumentos para América Latina y el Caribe</i>. CEPAL, Serie Manuales No. 51, Santiago.",
        "Medina Vásquez, J., Becerra, S. &amp; Castaño, P. (2014). <i>Prospectiva y política pública para el cambio estructural en América Latina y el Caribe</i>. CEPAL, Santiago.",
    ]
    for b in bib_co: e.append(Paragraph(b, bib_style))

    e.append(Paragraph("Críticas, revisiones y extensiones modernas (2007-2025)", h3_style))
    bib_mod = [
        "Chang, B., Chang, C. W. &amp; Wu, C. H. (2007). Fuzzy DEMATEL method for developing supplier selection criteria. <i>Expert Systems with Applications</i>, 38, 1850-1858.",
        "Saritas, O. &amp; Smith, J. E. (2011). The big picture — trends, drivers, wild cards, discontinuities and weak signals. <i>Futures</i>, 43(3), 292-312.",
        "Bishop, P. &amp; Hines, A. (2012). <i>Teaching about the Future</i>. Palgrave Macmillan, London.",
        "Khatwani, G., Singh, S. P., Trivedi, A. &amp; Chauhan, A. (2015). Fuzzy-TISM: a fuzzy extension of TISM for group decision making. <i>Global Journal of Flexible Systems Management</i>, 16(1), 97-112.",
        "Saxena, J. P., Sushil &amp; Vrat, P. (1992). Hierarchy and classification of program plan elements using interpretive structural modeling. <i>Systems Practice</i>, 5(6), 651-670.",
        "Pawar, S., Tiwari, A. &amp; Daim, T. (2024). Identifying key influencing factors of cross-regional railway infrastructure interconnection: a fuzzy integrated MCDM framework. <i>Humanities and Social Sciences Communications</i>, 12(1).",
        "Hota, J. R. (2024). Framework of challenges affecting adoption of people analytics in India using ISM and MICMAC analysis. <i>Vision: The Journal of Business Perspective</i>, 28(3).",
        "Si, S. L., You, X. Y., Liu, H. C. &amp; Zhang, P. (2018). DEMATEL technique: a systematic review of the state-of-the-art literature on methodologies and applications. <i>Mathematical Problems in Engineering</i>, vol. 2018, art. 3696457.",
    ]
    for b in bib_mod: e.append(Paragraph(b, bib_style))

    e.append(Paragraph("Aplicaciones en política pública latinoamericana", h3_style))
    bib_app = [
        "Departamento Nacional de Planeación, Colombia (varios años). <i>Prospectiva Territorial</i> — ejercicios de visión de largo plazo para departamentos (Arauca, Atlántico, Boyacá, Cauca, Cesar, Magdalena, Meta, Risaralda).",
        "DNP Colombia (2024). <i>Kit de Planeación Territorial (KPT)</i>. Herramienta para construcción de Planes de Desarrollo Territorial con metodología de cadena de valor. Cubre 889 municipios y 32 gobernaciones.",
        "Garibay-Carlos, A., Castañeda-Burciaga, S. &amp; Cuevas-Vargas, H. (2020). Análisis estructural MicMac para determinar las variables estratégicas de la agroindustria azucarera en México. <i>Agricultura, Sociedad y Desarrollo</i>, 17(4), 1325-1346.",
    ]
    for b in bib_app: e.append(Paragraph(b, bib_style))

    # 7. Limitaciones de esta herramienta
    e.append(Paragraph("7 · Limitaciones reconocidas de esta implementación", h2_style))
    e.append(Paragraph(
        "Por transparencia, declaramos las decisiones de implementación que "
        "afectan los resultados y que un auditor podría cuestionar:",
        body_style))
    e.append(ListFlowable([
        ListItem(Paragraph(
            "<b>Trato de la categoría P (potencial).</b> Numéricamente se "
            "interpreta como 1 (débil). En la matriz se marca con color "
            "distinto para preservar la información cualitativa. Versiones "
            "futuras tratarán P como un escalar configurable.",
            list_style), leftIndent=15),
        ListItem(Paragraph(
            "<b>Mediana como divisor de cuadrantes.</b> Tanto MicMac como "
            "DEMATEL usan la mediana de los valores para dividir los "
            "cuadrantes. Esto es robusto a outliers pero puede mover una "
            "variable de cuadrante si se agrega o se quita una variable "
            "atípica. La media aritmética sería más estable pero más "
            "sensible a outliers.",
            list_style), leftIndent=15),
        ListItem(Paragraph(
            "<b>Convergencia de MicMac al paso 3-6.</b> Si la matriz no se "
            "estabiliza al paso 6, reportamos el paso 6 como tope. En la "
            "práctica esto solo ocurre con matrices casi sin información (la "
            "mayoría de celdas en cero) o con ciclos cerrados de "
            "retroalimentación muy fuerte.",
            list_style), leftIndent=15),
        ListItem(Paragraph(
            "<b>Inversión de (I − D) en DEMATEL.</b> Se realiza por "
            "eliminación Gauss-Jordan local en el navegador. Para matrices "
            "n ≤ 60 (límite actual del módulo) la complejidad O(n³) es "
            "irrelevante. Para n > 60 la herramienta no permite ingresar "
            "más variables.",
            list_style), leftIndent=15),
        ListItem(Paragraph(
            "<b>Resolución de ciclos en ISM.</b> Si después de iterar por n+2 "
            "pasos quedan variables sin asignar (por ciclos cerrados sin "
            "resolución), se agrupan en un último nivel etiquetado como "
            "<i>indeterminado</i>. Esto es trazable en el output JSON.",
            list_style), leftIndent=15),
    ], bulletType='bullet'))

    e.append(Spacer(1, 16))
    e.append(Paragraph(
        "<b>Reproducibilidad.</b> Toda la matemática se ejecuta en el cliente. "
        "El código fuente es legible en la herramienta web (View Source). El "
        "export JSON contiene la matriz, las variables, el paso de "
        "estabilización de MicMac, el umbral de ISM y los rankings de las "
        "tres lentes, permitiendo verificación independiente.",
        body_style))

    e.append(Spacer(1, 16))
    e.append(Paragraph("Cierre", h3_style))
    e.append(Paragraph(
        "Esta herramienta no busca reemplazar el juicio experto sino "
        "estructurarlo. Sus resultados son tan buenos como las variables que "
        "definas y las calificaciones que ingreses. Tres lentes "
        "complementarios sobre la misma matriz reducen el riesgo de leer mal "
        "el sistema: cuando las tres apuntan a la misma variable como clave, "
        "la inferencia es robusta. Cuando difieren, hay que mirar el detalle. "
        "Esa es, en últimas, la promesa del análisis estructural: hacer "
        "explícita la complejidad que el cerebro humano no puede sostener.",
        body_style))

    doc.build(e, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"OK: {OUT} ({OUT.stat().st_size/1024:.1f} KB)")

if __name__ == "__main__":
    build()
