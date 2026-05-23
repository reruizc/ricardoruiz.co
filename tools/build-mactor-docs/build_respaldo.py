"""Genera el PDF de respaldo académico de Mactor."""
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, ListFlowable, ListItem

INK = HexColor("#14110a"); INK_2 = HexColor("#5a5448"); INK_3 = HexColor("#948e80")
ACCENT = HexColor("#8a1e16"); RULE = HexColor("#14110a40")

OUT_DIR = Path(__file__).resolve().parents[2] / "Bases de datos" / "mactor"
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
formula_style = ParagraphStyle('formula', parent=ss['BodyText'], fontName='Courier-Bold',
    fontSize=10.5, leading=14, textColor=ACCENT, spaceAfter=10, leftIndent=18, alignment=TA_LEFT)
bib_style = ParagraphStyle('bib', parent=ss['BodyText'], fontName='Helvetica',
    fontSize=9, leading=12, textColor=INK_2, leftIndent=14, firstLineIndent=-14, spaceAfter=5)

def header_footer(c, doc):
    c.saveState()
    c.setStrokeColor(RULE); c.setLineWidth(0.5)
    c.line(doc.leftMargin, letter[1]-1.1*cm, letter[0]-doc.rightMargin, letter[1]-1.1*cm)
    c.setFillColor(INK_3); c.setFont("Helvetica", 8)
    c.drawString(doc.leftMargin, letter[1]-1.4*cm, "Análisis de Actores · Ricardo Ruiz")
    c.drawRightString(letter[0]-doc.rightMargin, letter[1]-1.4*cm, "Respaldo metodológico · v1.0 · mayo 2026")
    c.line(doc.leftMargin, 1.3*cm, letter[0]-doc.rightMargin, 1.3*cm)
    c.drawString(doc.leftMargin, 0.9*cm, "ricardoruiz.co · consultoría en datos y política pública")
    c.drawRightString(letter[0]-doc.rightMargin, 0.9*cm, f"Página {doc.page}")
    c.restoreState()

def build():
    doc = SimpleDocTemplate(str(OUT), pagesize=letter,
        leftMargin=2.2*cm, rightMargin=2.2*cm, topMargin=2.0*cm, bottomMargin=1.9*cm,
        title="Mactor · Respaldo metodológico",
        author="Ricardo Ruiz · ricardoruiz.co",
        subject="Fundamentación teórica del análisis de actores")
    e = []
    e.append(Paragraph("Respaldo metodológico", title_style))
    e.append(Paragraph("Fundamentación teórica del análisis de actores y conflictos. Para defender el rigor ante auditores o consultores expertos.", subtitle_style))
    e.append(Paragraph(
        "Este documento acompaña la herramienta web publicada en "
        "<font color='#8a1e16'>ricardoruiz.co/mactor.html</font>. Documenta el "
        "origen del método, la formulación matemática, validez interna, "
        "limitaciones reconocidas y bibliografía.",
        body_style))

    e.append(Paragraph("1 · Origen disciplinar", h2_style))
    e.append(Paragraph(
        "Mactor (Matrix of Alliances and Conflicts: Tactics, Objectives, "
        "Recommendations) fue formulado por Michel Godet en el laboratorio "
        "LIPSOR (Laboratoire d'Investigation en Prospective, Stratégie et "
        "Organisation) del CNAM en París, alrededor de 1991. Es el "
        "complemento natural del análisis estructural MICMAC: mientras "
        "MICMAC diagnostica las variables que mueven el sistema, Mactor "
        "analiza a los actores que tienen poder sobre esas variables.",
        body_style))
    e.append(Paragraph(
        "En Colombia el referente es <b>Francisco José Mojica Sastoque</b>, "
        "doctor por la Universidad de París V (Sorbona) y discípulo directo "
        "del grupo de Godet. Mojica dirige el Centro de Pensamiento "
        "Estratégico y Prospectiva del Externado, la Maestría en Pensamiento "
        "Estratégico y Prospectiva, y la Cátedra UNESCO de Estudios de Futuro. "
        "Ha aplicado Mactor en más de 50 estudios prospectivos en Colombia, "
        "Venezuela, Ecuador, México y Perú.",
        body_style))

    e.append(Paragraph("2 · Estructura del método", h2_style))
    e.append(Paragraph(
        "El método trabaja sobre dos matrices declarativas que el experto "
        "construye:",
        body_style))
    e.append(Paragraph(
        "<b>MID — Matrice des Influences Directes</b> (actor × actor). "
        "Cada celda MID[i,j] codifica cuánto influye el actor i sobre el j, "
        "en una escala 0-4 que captura la profundidad del impacto: "
        "0 nula, 1 procesos operativos, 2 proyectos, 3 misión, 4 existencia.",
        body_style))
    e.append(Paragraph(
        "<b>MAO — Matrice Acteurs × Objectifs</b> (actor × objetivo). "
        "Cada celda MAO[i,j] codifica la posición del actor i sobre el "
        "objetivo j, en escala −4 a +4. El signo positivo significa apoyo "
        "(intensidad por la profundidad del impacto del objetivo en el "
        "actor); el signo negativo, oposición con la misma intensidad.",
        body_style))

    e.append(Paragraph("3 · Cálculos", h2_style))
    e.append(Paragraph("Influencia y dependencia directas:", body_style))
    e.append(Paragraph("Ii = sum_j MID[i,j]    (influencia que i ejerce)", formula_style))
    e.append(Paragraph("Di = sum_j MID[j,i]    (dependencia que i recibe)", formula_style))
    e.append(Paragraph(
        "El <b>poder relativo</b> de cada actor lo medimos como:",
        body_style))
    e.append(Paragraph("Ri = Ii / (Ii + Di)", formula_style))
    e.append(Paragraph(
        "(Si Ii=Di=0, Ri se define como 0.) Esta normalización mantiene Ri "
        "en [0,1] y permite comparar actores entre sí. En el plot de "
        "Influencia × Dependencia, los actores se ubican según (Di, Ii) "
        "normalizados a [0,100] por el máximo observado de cada eje.",
        body_style))
    e.append(Paragraph(
        "<b>Convergencia y divergencia</b> entre pares de actores sobre el "
        "conjunto de objetivos:",
        body_style))
    e.append(Paragraph("Conv[i,j] = sum_k min(|MAO[i,k]|, |MAO[j,k]|)  si signo(MAO[i,k]) == signo(MAO[j,k])", formula_style))
    e.append(Paragraph("Div[i,j]  = sum_k min(|MAO[i,k]|, |MAO[j,k]|)  si signos opuestos", formula_style))
    e.append(Paragraph(
        "El uso del <i>mínimo</i> de las dos posiciones absolutas es la "
        "convención de Godet: dos actores con +4 y +1 no comparten cuatro "
        "unidades de convergencia, comparten una (la del actor menos "
        "comprometido). Esto evita inflar las alianzas con actores que "
        "tienen posiciones tibias.",
        body_style))
    e.append(Paragraph("Por objetivo:", body_style))
    e.append(Paragraph("Mov_k = sum_i |MAO[i,k]|                  (movilización)", formula_style))
    e.append(Paragraph("Saldo_k = sum_i MAO[i,k] · Ri[i]          (saldo neto ponderado)", formula_style))
    e.append(Paragraph(
        "La movilización mide qué tan disputado está el objetivo (la suma "
        "absoluta de las posiciones). El saldo neto pondera las posiciones "
        "por el poder relativo del actor — un actor poderoso que apoya con "
        "+2 pesa más en el saldo que un actor débil con +4.",
        body_style))

    e.append(Paragraph("4 · Validez interna y limitaciones reconocidas", h2_style))
    e.append(ListFlowable([
        ListItem(Paragraph("<b>Escala ordinal tratada como cardinal.</b> Las operaciones (sumas, productos por Ri) son cardinales sobre una escala que es de jure ordinal. La crítica viene del propio Godet en publicaciones posteriores y se reconoce en la literatura prospectiva. La mitigación práctica es no tratar los números absolutos como ciencia exacta — son ordenamientos relativos defendibles.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Sesgo del panel.</b> Igual que MICMAC, Mactor depende de quién esté en la mesa. Si tu mesa de expertos es homogénea ideológicamente, el resultado lo será.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Modelo estático.</b> Mactor da una foto del juego de actores en un momento. No captura cómo evolucionan las alianzas con el tiempo ni cómo cambian las prioridades. Para procesos largos hay que rehacer el análisis periódicamente.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>No captura comunicación ni reputación.</b> Un actor débil pero con alta capacidad de incidencia mediática puede ganar batallas que el modelo no predice. La incidencia comunicacional es una dimensión separada que conviene tratar fuera del método.", list_style), leftIndent=15),
        ListItem(Paragraph("<b>Implementación simplificada en esta herramienta.</b> El Mactor original calcula influencias indirectas via una <i>matriz pivotada MIDI</i> (sumas con producto interior sobre MID iterada) que esta versión MVP no incluye. Influencias indirectas estarán en versiones siguientes.", list_style), leftIndent=15),
    ], bulletType='bullet'))

    e.append(Paragraph("5 · Bibliografía", h2_style))
    bib = [
        "Godet, M. (1991). <i>De l'anticipation à l'action: manuel de prospective et de stratégie</i>. Dunod, Paris.",
        "Godet, M. (1994). <i>From Anticipation to Action: A Handbook of Strategic Prospective</i>. UNESCO Publishing.",
        "Godet, M., Bourse, F., Chapuy, P. &amp; Menant, I. (1991). <i>Futures studies: a tool-box for problem solving</i>. UNESCO, Paris.",
        "Godet, M. (2000). The art of scenarios and strategic planning: tools and pitfalls. <i>Technological Forecasting and Social Change</i>, 65(1), 3-22.",
        "Mojica, F. J. (2006). <i>Concepto y aplicación de la prospectiva estratégica</i>. Universidad Externado de Colombia, Bogotá.",
        "Mojica, F. J. (2008). Forecasting y foresight: dos escuelas, dos enfoques. <i>Med-UNAB</i>, 11(1).",
        "Medina Vásquez, J. &amp; Ortegón, E. (2006). <i>Manual de prospectiva y decisión estratégica: bases teóricas e instrumentos para América Latina y el Caribe</i>. CEPAL, Serie Manuales No. 51, Santiago.",
        "Saritas, O. &amp; Smith, J. E. (2011). The big picture — trends, drivers, wild cards, discontinuities and weak signals. <i>Futures</i>, 43(3), 292-312.",
        "Bishop, P. &amp; Hines, A. (2012). <i>Teaching about the Future</i>. Palgrave Macmillan, London.",
        "Bendahan, S., Camponovo, G. &amp; Pigneur, Y. (2004). Multi-issue actor analysis: tools and models for assessing technology environments. <i>Journal of Decision Systems</i>, 13(2).",
    ]
    for b in bib: e.append(Paragraph(b, bib_style))

    e.append(Paragraph("6 · Limitaciones de esta implementación", h2_style))
    e.append(ListFlowable([
        ListItem(Paragraph("Trato ordinal-cardinal: los cálculos asumen aditividad de una escala ordinal. Defensible para diagnóstico estratégico; insuficiente para predicción cuantitativa.", list_style), leftIndent=15),
        ListItem(Paragraph("Mediana como divisor de cuadrantes en los dos plots (Influencia × Dependencia y Convergencia × Divergencia). Robusta a outliers pero sensible al tamaño del set de actores: agregar un actor extremo cambia la mediana y por lo tanto la clasificación de algunos cercanos al límite.", list_style), leftIndent=15),
        ListItem(Paragraph("No se calculan influencias indirectas (matriz pivotada MIDI). En sistemas muy interconectados esto subestima el poder de actores con influencia indirecta importante. Se incorporará en versión siguiente.", list_style), leftIndent=15),
        ListItem(Paragraph("Reproducibilidad: el cálculo es local en el cliente y el export JSON contiene las dos matrices originales más los rankings y cuadrantes derivados. Verificación independiente es trivial.", list_style), leftIndent=15),
    ], bulletType='bullet'))

    doc.build(e, onFirstPage=header_footer, onLaterPages=header_footer)
    print(f"OK: {OUT} ({OUT.stat().st_size/1024:.1f} KB)")

if __name__ == "__main__":
    build()
