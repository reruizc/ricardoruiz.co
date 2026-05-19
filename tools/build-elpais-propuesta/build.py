#!/usr/bin/env python3
"""
Genera la propuesta comercial en PDF para El País Cali (1.5 páginas).
Salida: Bases de datos/test-presidencial/elpais-propuesta-test-presidencial.pdf
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    Table, TableStyle, FrameBreak,
)

OUT = ("/Users/ricardoruiz/ricardoruiz.co/Bases de datos/test-presidencial/"
       "elpais-propuesta-test-presidencial.pdf")

BLUE = colors.HexColor("#0067b1")
BLUE_D = colors.HexColor("#004a80")
RED = colors.HexColor("#E2161F")
INK = colors.HexColor("#14202C")
SOFT = colors.HexColor("#4A4F55")
META = colors.HexColor("#8A9099")
LINE = colors.HexColor("#DCDFE3")
SHELL = colors.HexColor("#F4F6F8")

W, H = letter
MX = 17 * mm

ss = getSampleStyleSheet()
def S(name, **kw):
    base = dict(fontName="Helvetica", fontSize=9.7, leading=14.8,
                textColor=INK, alignment=TA_JUSTIFY, spaceAfter=7)
    base.update(kw)
    return ParagraphStyle(name, parent=ss["Normal"], **base)

st_kicker = S("kicker", fontName="Helvetica-Bold", fontSize=8, leading=11,
              textColor=BLUE, alignment=TA_LEFT, spaceAfter=3)
st_h1 = S("h1", fontName="Helvetica-Bold", fontSize=18.5, leading=21,
          textColor=INK, alignment=TA_LEFT, spaceAfter=4)
st_sub = S("sub", fontName="Helvetica", fontSize=10.5, leading=15,
           textColor=SOFT, alignment=TA_LEFT, spaceAfter=2)
st_sec = S("sec", fontName="Helvetica-Bold", fontSize=11, leading=14,
           textColor=BLUE_D, alignment=TA_LEFT, spaceBefore=13, spaceAfter=6)
st_body = S("body")
st_li = S("li", leftIndent=12, spaceAfter=5, alignment=TA_LEFT, leading=14)
st_small = S("small", fontSize=7.8, leading=11, textColor=META,
             alignment=TA_LEFT)
st_step = S("step", fontName="Helvetica", fontSize=9.5, leading=13.5,
            textColor=INK, alignment=TA_LEFT, spaceAfter=0)
st_cell = S("cell", fontSize=8.2, leading=10.6, alignment=TA_LEFT, spaceAfter=0)
st_cellb = S("cellb", fontName="Helvetica-Bold", fontSize=8.2, leading=10.6,
             textColor=BLUE_D, alignment=TA_LEFT, spaceAfter=0)


def bullet(txt):
    return Paragraph(f'<font color="#0067b1">▪</font>&nbsp;&nbsp;{txt}', st_li)


def header(canvas, doc):
    canvas.saveState()
    # Banda superior
    canvas.setFillColor(BLUE)
    canvas.rect(0, H - 24 * mm, W, 24 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 17)
    canvas.drawString(MX, H - 13 * mm, "EL ")
    wlen = canvas.stringWidth("EL ", "Helvetica-Bold", 17)
    canvas.setFillColor(colors.HexColor("#ffd2d2"))
    canvas.drawString(MX + wlen, H - 13 * mm, "PAÍS")
    wlen2 = wlen + canvas.stringWidth("PAÍS", "Helvetica-Bold", 17)
    canvas.setFillColor(colors.white)
    canvas.drawString(MX + wlen2, H - 13 * mm, "  ·  CALI")
    canvas.setFont("Helvetica", 8.3)
    canvas.drawRightString(W - MX, H - 12.4 * mm,
                           "Propuesta de alianza editorial — sin costo")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#bcd8ec"))
    canvas.drawString(MX, H - 19.5 * mm,
                      "Test Presidencial 2026  ·  datos electorales por ricardoruiz.co")
    # Pie
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.6)
    canvas.line(MX, 13 * mm, W - MX, 13 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(META)
    canvas.drawString(MX, 9.5 * mm,
                      "ricardoruiz.co  ·  Plataforma electoral Colombia 2026")
    canvas.drawRightString(W - MX, 9.5 * mm,
                           "Contacto: reruizc@gmail.com")
    canvas.restoreState()


def build():
    doc = BaseDocTemplate(OUT, pagesize=letter,
                          leftMargin=MX, rightMargin=MX,
                          topMargin=29 * mm, bottomMargin=16 * mm)
    frame = Frame(MX, 16 * mm, W - 2 * MX, H - 29 * mm - 16 * mm, id="f")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame],
                                       onPage=header)])

    s = []
    s.append(Paragraph("LA RECTA FINAL, CON DATOS Y NO CON RUIDO", st_kicker))
    s.append(Paragraph("Un test que convierte a tu lector del Valle "
                       "en tu mejor fuente de audiencia", st_h1))
    s.append(Paragraph("Interactivo, embebible en cualquier nota, con la "
                        "marca de El País. Para ustedes: gratis.", st_sub))
    s.append(Spacer(1, 7))

    s.append(Paragraph("Qué es", st_sec))
    s.append(Paragraph(
        "<b>“¿Qué tan cerca estás de tu candidato?”</b> es un test donde tu "
        "lector descubre, en dos minutos, qué tan alineado está con su "
        "apuesta presidencial. No es una encuesta más: cruza lo que <i>declara</i>, "
        "su <i>arquetipo emocional</i> de votante y la <b>huella electoral real "
        "de su propio barrio</b> (histórico 2010–2025 + consultas + senado, "
        "ponderado). Una IA le devuelve una lectura personalizada con el tono "
        "de su región y cómo le va a su candidato en su zona. Se embebe con un "
        "<i>iframe</i> que ya viene con la paleta y tipografía de El País.", st_body))

    s.append(Paragraph("Por qué les conviene — y por qué ahora", st_sec))
    s.append(bullet("<b>Retención.</b> El lector no responde y se va: recibe "
                    "un espejo con su nombre, su barrio y su candidato. Comparte "
                    "(WhatsApp, X) con el hashtag de su campaña. Tráfico que "
                    "vuelve."))
    s.append(bullet("<b>Inteligencia de audiencia, en vivo y solo para "
                    "ustedes.</b> Un tablero privado les dice — de forma "
                    "anónima — quién es la audiencia que El País moviliza en "
                    "el Valle."))
    s.append(bullet("<b>La ventana es ahora.</b> Cada día de campaña que pasa "
                    "sin medir es señal perdida. Lo que capturen hasta primera "
                    "vuelta es exactamente el insumo para encuadrar la segunda."))

    s.append(Paragraph("Lo que sabrán de su propia audiencia", st_sec))
    s.append(bullet("<b>Por quién vota su lector del Valle</b>: candidato más "
                    "declarado, y la intención proyectada barrio a barrio."))
    s.append(bullet("<b>Qué la mueve</b>: el arquetipo emocional dominante "
                    "(de cinco) — el porqué profundo del voto, no solo el qué."))
    s.append(bullet("<b>Dónde hay tensión</b>: la tasa de “vientos cruzados” "
                    "— lectores que declaran X pero cuya zona se inclina "
                    "distinto. Ahí está la historia."))
    s.append(bullet("<b>Mapa del Valle</b>: distribución por municipio, "
                    "clic a clic. Todo anónimo; contacto solo de quien lo "
                    "autoriza expresamente (Ley 1581)."))

    s.append(Paragraph("El ángulo editorial para segunda vuelta, servido", st_sec))
    s.append(Paragraph(
        "Cuando cierre la primera vuelta sabrán qué arquetipo predomina en su "
        "audiencia. Ese dato es un encuadre narrativo listo para su cobertura "
        "de la segunda:", S("bodytight", spaceAfter=5)))

    data = [
        [Paragraph("Si su audiencia es mayoría…", st_cellb),
         Paragraph("Encuadre que conecta en segunda vuelta", st_cellb)],
        [Paragraph("<b>Protección</b>", st_cell),
         Paragraph("“¿Quién garantiza orden <i>con resultados</i>?” — "
                   "seguridad, competencia y gestión, no promesas.", st_cell)],
        [Paragraph("<b>Continuidad</b>", st_cell),
         Paragraph("“¿Qué se mantiene y qué se arriesga?” — continuidad "
                   "frente a ruptura, costo del cambio.", st_cell)],
        [Paragraph("<b>Supervivencia</b>", st_cell),
         Paragraph("“El bolsillo manda” — costo de vida, salud y empleo "
                   "como vara para medir a los dos finalistas.", st_cell)],
        [Paragraph("<b>Castigo</b>", st_cell),
         Paragraph("“El voto que cobra” — hartazgo, alternancia y "
                   "fiscalización; la segunda vuelta como ajuste de cuentas.",
                   st_cell)],
        [Paragraph("<b>Pertenencia</b>", st_cell),
         Paragraph("“El Valle decide” — agenda regional e identidad "
                   "territorial frente a un país que mira a Bogotá.", st_cell)],
    ]
    t = Table(data, colWidths=[33 * mm, W - 2 * MX - 33 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), SHELL),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, BLUE),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBEFORE", (1, 1), (1, -1), 0.4, LINE),
    ]))
    s.append(t)
    s.append(Spacer(1, 8))

    s.append(Paragraph("Los términos", st_sec))
    s.append(bullet("<b>Sin costo.</b> No cobramos por embeber el test ni por "
                    "el tablero de audiencia. Solo pedimos publicarlo en sus "
                    "notas durante la recta final y la segunda vuelta."))
    s.append(bullet("<b>Su marca, su territorio.</b> Embed con la identidad "
                    "de El País y filtrado al Valle por defecto. Listo para "
                    "pegar hoy."))
    s.append(bullet("<b>Datos con respaldo.</b> Anonimato por defecto; el "
                    "contacto de un lector con una campaña solo ocurre si él "
                    "lo autoriza, bajo Ley 1581."))

    s.append(Paragraph("Cómo empezar — tres pasos, cero fricción", st_sec))
    steps = [
        [Paragraph("<b>1</b>", st_cellb),
         Paragraph("Nos dicen “sí”. Les enviamos el <i>iframe</i> con la "
                   "marca de El País y el filtro Valle ya configurado.",
                   st_step)],
        [Paragraph("<b>2</b>", st_cellb),
         Paragraph("Lo pegan en sus notas de campaña (una línea de HTML). "
                   "Funciona en web y móvil, sin mantenimiento de su lado.",
                   st_step)],
        [Paragraph("<b>3</b>", st_cellb),
         Paragraph("Abren el tablero privado y ven crecer, en vivo, el "
                   "retrato de su audiencia rumbo a segunda vuelta.",
                   st_step)],
    ]
    ts = Table(steps, colWidths=[10 * mm, W - 2 * MX - 10 * mm])
    ts.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
    ]))
    s.append(ts)
    s.append(Spacer(1, 12))

    close = Table([[Paragraph(
        "<b>El trato es simple:</b> ustedes ponen la audiencia y la pauta "
        "editorial; nosotros ponemos la tecnología, los datos electorales y "
        "la lectura con IA. En una campaña donde todos opinan, El País Cali "
        "llegaría a la segunda vuelta sabiendo — con evidencia — qué mueve "
        "a su gente del Valle. Lo único que se necesita para arrancar es "
        "decir “sí”.",
        S("close", fontName="Helvetica", fontSize=10, leading=14.5,
          textColor=INK, alignment=TA_LEFT, spaceAfter=0))]],
        colWidths=[W - 2 * MX])
    close.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SHELL),
        ("LINEBEFORE", (0, 0), (0, -1), 2.4, BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    s.append(close)
    s.append(Spacer(1, 8))
    s.append(Paragraph(
        "Embed listo: ricardoruiz.co/test-presidencial-2026.html?embed=1&amp;"
        "brand=elpais&amp;territorio=valle&nbsp;&nbsp;·&nbsp;&nbsp;Tablero "
        "privado: ricardoruiz.co/elpais-cali-dashboard.html", st_small))

    doc.build(s)
    import os
    return os.path.getsize(OUT)


if __name__ == "__main__":
    n = build()
    print(f"PDF generado: {OUT}  ({n/1024:.1f} KB)")
