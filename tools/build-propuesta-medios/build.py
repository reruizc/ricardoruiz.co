#!/usr/bin/env python3
"""
Genera la propuesta comercial en PDF, versión genérica para cualquier
medio digital con página web. Variante neutral del PDF de El País Cali:
sin marca específica, sin filtro territorial fijo, con 3 beneficios extra
y un bloque de modularidad ("podemos quitar o ajustar lo que prefieran").

Salida: Bases de datos/test-presidencial/propuesta-test-presidencial-medios.pdf
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    Table, TableStyle,
)

OUT = ("/Users/ricardoruiz/ricardoruiz.co/Bases de datos/test-presidencial/"
       "propuesta-test-presidencial-medios.pdf")

INK = colors.HexColor("#14202C")
INK_D = colors.HexColor("#0B1620")
ACCENT = colors.HexColor("#1F4E79")
ACCENT_D = colors.HexColor("#143656")
SOFT = colors.HexColor("#4A4F55")
META = colors.HexColor("#8A9099")
LINE = colors.HexColor("#DCDFE3")
SHELL = colors.HexColor("#F4F6F8")
HIGHLIGHT = colors.HexColor("#FFF7E0")
HIGHLIGHT_BORDER = colors.HexColor("#E0B84A")

W, H = letter
MX = 17 * mm

ss = getSampleStyleSheet()


def S(name, **kw):
    base = dict(fontName="Helvetica", fontSize=9.7, leading=14.8,
                textColor=INK, alignment=TA_JUSTIFY, spaceAfter=7)
    base.update(kw)
    return ParagraphStyle(name, parent=ss["Normal"], **base)


st_kicker = S("kicker", fontName="Helvetica-Bold", fontSize=8, leading=11,
              textColor=ACCENT, alignment=TA_LEFT, spaceAfter=3)
st_h1 = S("h1", fontName="Helvetica-Bold", fontSize=18.5, leading=21,
          textColor=INK, alignment=TA_LEFT, spaceAfter=4)
st_sub = S("sub", fontName="Helvetica", fontSize=10.5, leading=15,
           textColor=SOFT, alignment=TA_LEFT, spaceAfter=2)
st_sec = S("sec", fontName="Helvetica-Bold", fontSize=11, leading=14,
           textColor=ACCENT_D, alignment=TA_LEFT, spaceBefore=9,
           spaceAfter=5)
st_body = S("body")
st_li = S("li", leftIndent=12, spaceAfter=4, alignment=TA_LEFT, leading=13.6)
st_small = S("small", fontSize=7.8, leading=11, textColor=META,
             alignment=TA_LEFT)
st_step = S("step", fontName="Helvetica", fontSize=9.5, leading=13.5,
            textColor=INK, alignment=TA_LEFT, spaceAfter=0)
st_cell = S("cell", fontSize=8.2, leading=10.6, alignment=TA_LEFT,
            spaceAfter=0)
st_cellb = S("cellb", fontName="Helvetica-Bold", fontSize=8.2, leading=10.6,
             textColor=ACCENT_D, alignment=TA_LEFT, spaceAfter=0)


def bullet(txt):
    return Paragraph(f'<font color="#1F4E79">▪</font>&nbsp;&nbsp;{txt}',
                     st_li)


def header(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(INK_D)
    canvas.rect(0, H - 24 * mm, W, 24 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 17)
    canvas.drawString(MX, H - 13 * mm, "TEST PRESIDENCIAL ")
    wlen = canvas.stringWidth("TEST PRESIDENCIAL ",
                              "Helvetica-Bold", 17)
    canvas.setFillColor(colors.HexColor("#FFD089"))
    canvas.drawString(MX + wlen, H - 13 * mm, "2026")
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 8.3)
    canvas.drawRightString(W - MX, H - 12.4 * mm,
                           "Propuesta editorial para medios — sin costo")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#9CB6CC"))
    canvas.drawString(MX, H - 19.5 * mm,
                      "Plataforma electoral Colombia 2026  ·  "
                      "ricardoruiz.co")
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.6)
    canvas.line(MX, 13 * mm, W - MX, 13 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(META)
    canvas.drawString(MX, 9.5 * mm,
                      "ricardoruiz.co  ·  Plataforma electoral "
                      "Colombia 2026")
    canvas.drawRightString(W - MX, 9.5 * mm,
                           "Contacto: reruizc@gmail.com")
    canvas.restoreState()


def build():
    doc = BaseDocTemplate(OUT, pagesize=letter,
                          leftMargin=MX, rightMargin=MX,
                          topMargin=27 * mm, bottomMargin=14 * mm)
    frame = Frame(MX, 14 * mm, W - 2 * MX, H - 27 * mm - 14 * mm, id="f")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame],
                                       onPage=header)])

    s = []
    s.append(Paragraph("PRIMERA VUELTA · DEL 20 AL 31 DE MAYO DE 2026",
                       st_kicker))
    s.append(Paragraph("Un test que convierte a su lector en su "
                       "mejor fuente de audiencia", st_h1))
    s.append(Paragraph("Interactivo, embebible en cualquier nota, con la "
                       "identidad visual de su medio. Para ustedes: "
                       "gratis.", st_sub))
    s.append(Spacer(1, 7))

    s.append(Paragraph("Qué es", st_sec))
    s.append(Paragraph(
        "<b>“¿Qué tan cerca estás de tu candidato?”</b> es un test donde "
        "su lector descubre, en dos minutos, qué tan alineado está con su "
        "apuesta presidencial. No es una encuesta más: cruza lo que "
        "<i>declara</i>, su <i>arquetipo emocional</i> de votante y la "
        "<b>huella electoral real de su propio barrio</b> (histórico "
        "2010–2025 + consultas + senado, ponderado). Una IA le devuelve "
        "una lectura personalizada con el tono de su región y cómo le va "
        "a su candidato en su zona. Se embebe con un <i>iframe</i> que se "
        "configura con la paleta y tipografía de su medio.", st_body))

    s.append(Paragraph("Por qué les conviene — y por qué ahora", st_sec))
    s.append(bullet("<b>Retención.</b> El lector no responde y se va: "
                    "recibe un espejo con su nombre, su barrio y su "
                    "candidato. Comparte (WhatsApp, X) con la marca de su "
                    "medio incrustada. Tráfico que vuelve."))
    s.append(bullet("<b>Inteligencia de audiencia, en vivo y solo para "
                    "ustedes.</b> Un tablero privado les dice — de forma "
                    "anónima — quién es la audiencia que su medio "
                    "moviliza. Es <i>insumo editorial interno</i>, no la "
                    "publicación de un sondeo: les sirve para decidir su "
                    "cobertura, sin entrar en la regulación de "
                    "encuestas."))
    s.append(bullet("<b>Tiempo en sitio que se multiplica.</b> El test "
                    "promedia entre dos y tres minutos de interacción "
                    "activa — una eternidad para web. Eso sube el "
                    "<i>dwell time</i> de la nota donde lo embeben, el "
                    "<i>scroll depth</i> y, en consecuencia, las métricas "
                    "que su equipo comercial le presenta a anunciantes."))
    s.append(bullet("<b>Diferenciación tecnológica frente a su "
                    "competencia.</b> Mientras otros medios replican "
                    "boletines de la Registraduría, ustedes ofrecen un "
                    "producto interactivo con IA y datos electorales "
                    "ponderados. Es un mensaje claro a su audiencia y a "
                    "su mercado: este medio innova."))
    s.append(bullet("<b>Dataset propio para el post-elección.</b> Al "
                    "cierre del 31 de mayo se quedan con el retrato "
                    "agregado de quienes participaron desde su sitio. Es "
                    "material para la nota de balance, para el especial "
                    "de segunda vuelta y para un archivo que la "
                    "competencia no tiene."))
    s.append(bullet("<b>Se conecta a la analítica que ya tienen.</b> El "
                    "embed le va avisando al sitio donde está incrustado "
                    "los momentos clave del recorrido — cuando un lector "
                    "lo carga, cuando termina las preguntas, cuando "
                    "abre la lectura con IA, cuando autoriza un contacto. "
                    "Son señales anónimas, sin datos personales, que su "
                    "equipo de analítica puede capturar desde el primer "
                    "día con Google Analytics, Adobe, Chartbeat o el "
                    "sistema que ya usen. No tenemos que tocar nada de "
                    "su lado: ustedes deciden qué evento les sirve y lo "
                    "amarran a sus tableros."))
    s.append(bullet("<b>La ventana son 11 días.</b> El test corre del 20 "
                    "al 31 de mayo (primera vuelta). Cada día que pasa "
                    "sin medir es señal perdida; lo que capturen hasta el "
                    "cierre es el insumo para encuadrar toda su cobertura "
                    "final."))

    s.append(Paragraph("Lo que sabrán de su propia audiencia", st_sec))
    s.append(bullet("<b>Por quién vota su lector</b>: candidato más "
                    "declarado, y la intención proyectada barrio a "
                    "barrio."))
    s.append(bullet("<b>Qué la mueve</b>: el arquetipo emocional "
                    "dominante (de cinco) — el porqué profundo del voto, "
                    "no solo el qué."))
    s.append(bullet("<b>Dónde hay tensión</b>: la tasa de “vientos "
                    "cruzados” — lectores que declaran X pero cuya zona "
                    "se inclina distinto. Ahí está la historia."))
    s.append(bullet("<b>Mapa nacional o regional</b>: distribución por "
                    "departamento y municipio, clic a clic. Todo "
                    "anónimo; contacto solo de quien lo autoriza "
                    "expresamente (Ley 1581)."))
    s.append(bullet("<b>Desde qué tema piensan</b>: el test detecta si "
                    "su lector prioriza salud, costo de vida, política "
                    "exterior, instituciones o agro, y <i>reescribe sus "
                    "propias preguntas con ese lente</i>. Así no sabrán "
                    "solo que su audiencia es mayoría “Protección”: "
                    "sabrán que es “Protección desde el ángulo de "
                    "salud” o “Castigo desde el costo de vida”. Es un "
                    "matiz que vale oro para titular una nota."))

    s.append(Paragraph("El ángulo editorial, servido", st_sec))
    s.append(Paragraph(
        "Durante estos 11 días sabrán qué arquetipo predomina en su "
        "audiencia. Ese dato es un encuadre narrativo listo: orienta "
        "cómo cubrir la recta final y, cuando se defina, el paso a "
        "segunda vuelta.", S("bodytight", spaceAfter=5)))

    data = [
        [Paragraph("Si su audiencia es mayoría…", st_cellb),
         Paragraph("Encuadre que conecta en segunda vuelta", st_cellb)],
        [Paragraph("<b>Protección</b>", st_cell),
         Paragraph("“¿Quién garantiza orden <i>con resultados</i>?” — "
                   "seguridad, competencia y gestión, no promesas.",
                   st_cell)],
        [Paragraph("<b>Continuidad</b>", st_cell),
         Paragraph("“¿Qué se mantiene y qué se arriesga?” — continuidad "
                   "frente a ruptura, costo del cambio.", st_cell)],
        [Paragraph("<b>Supervivencia</b>", st_cell),
         Paragraph("“El bolsillo manda” — costo de vida, salud y empleo "
                   "como vara para medir a los dos finalistas.",
                   st_cell)],
        [Paragraph("<b>Castigo</b>", st_cell),
         Paragraph("“El voto que cobra” — hartazgo, alternancia y "
                   "fiscalización; la segunda vuelta como ajuste de "
                   "cuentas.", st_cell)],
        [Paragraph("<b>Pertenencia</b>", st_cell),
         Paragraph("“Nuestra región decide” — agenda territorial e "
                   "identidad local frente a un país que mira a Bogotá.",
                   st_cell)],
    ]
    t = Table(data, colWidths=[33 * mm, W - 2 * MX - 33 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), SHELL),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, ACCENT),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBEFORE", (1, 1), (1, -1), 0.4, LINE),
    ]))
    s.append(t)
    s.append(Spacer(1, 8))

    s.append(Paragraph("Modular y adaptable a su criterio editorial",
                       st_sec))
    mod = Table([[Paragraph(
        "<b>Quitamos o ajustamos lo que no encaje con su política "
        "editorial.</b> El test está pensado como una caja de bloques: "
        "ustedes deciden cuáles activamos para sus lectores. En "
        "particular, el bloque de <i>“¿quieres que una campaña te "
        "contacte?”</i> (opt-in explícito, Ley 1581) puede salir "
        "completamente si prefieren mantener al medio fuera de cualquier "
        "circuito de captación. También son removibles, si así lo "
        "deciden: el botón de compartir a redes, los hashtags por "
        "candidato, el bloque “cómo apoyar”, la lectura con IA (puede "
        "quedar solo el resultado cuantitativo) y cualquier referencia a "
        "<i>ricardoruiz.co</i> en la interfaz del embed más allá del "
        "crédito legal mínimo. La condición es una sola conversación de "
        "15 minutos para acordar el alcance final.",
        S("mod", fontName="Helvetica", fontSize=9.5, leading=14,
          textColor=INK, alignment=TA_LEFT, spaceAfter=0))]],
        colWidths=[W - 2 * MX])
    mod.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HIGHLIGHT),
        ("LINEBEFORE", (0, 0), (0, -1), 2.4, HIGHLIGHT_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    s.append(mod)

    s.append(Paragraph("Los términos", st_sec))
    s.append(bullet("<b>Sin costo.</b> No cobramos por embeber el test "
                    "ni por el tablero. Vigencia primera vuelta: del 20 "
                    "al 31 de mayo de 2026. (La segunda vuelta sería un "
                    "módulo aparte.)"))
    s.append(bullet("<b>Su marca, su territorio.</b> Embed con la "
                    "identidad de su medio y filtrado al departamento o "
                    "región que prefieran (o nacional, si su audiencia "
                    "es transversal). Listo en 48 horas hábiles desde el "
                    "acuerdo."))
    s.append(bullet("<b>Inteligencia editorial, no un sondeo.</b> El "
                    "tablero es insumo interno para decidir cobertura — "
                    "el test es audiencia autoseleccionada, no muestra "
                    "probabilística. Publicar cifras al aire queda a "
                    "criterio de su jurídica (Ley 2494/2025 de "
                    "encuestas); el uso editorial interno no tiene esa "
                    "restricción."))
    s.append(bullet("<b>Datos con respaldo.</b> Anonimato por defecto; "
                    "ningún dato personal sale del sistema sin "
                    "consentimiento explícito del lector bajo Ley 1581. "
                    "Si activamos el opt-in de campañas (opcional), su "
                    "medio nunca es el intermediario."))
    s.append(bullet("<b>Exclusividad por territorio.</b> Si quieren ser "
                    "el único medio con el embed en su departamento o "
                    "región durante la primera vuelta, lo amarramos por "
                    "escrito. Se asigna por orden de confirmación."))

    s.append(Paragraph("Cómo empezar — tres pasos, cero fricción",
                       st_sec))
    steps = [
        [Paragraph("<b>1</b>", st_cellb),
         Paragraph("Nos dicen “sí” y agendamos 15 minutos para acordar "
                   "qué bloques quedan activos y qué identidad visual "
                   "aplicamos.", st_step)],
        [Paragraph("<b>2</b>", st_cellb),
         Paragraph("Les enviamos el <i>iframe</i> ya configurado. Lo "
                   "pegan en sus notas de campaña (una línea de HTML). "
                   "Funciona en web y móvil, sin mantenimiento de su "
                   "lado.", st_step)],
        [Paragraph("<b>3</b>", st_cellb),
         Paragraph("Abren el tablero privado y ven crecer, en vivo, el "
                   "retrato de su audiencia rumbo al 31 de mayo.",
                   st_step)],
    ]
    ts = Table(steps, colWidths=[10 * mm, W - 2 * MX - 10 * mm])
    ts.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
    ]))
    s.append(ts)

    close = Table([[Paragraph(
        "<b>El trato es simple:</b> ustedes ponen la audiencia; nosotros "
        "ponemos la tecnología, los datos electorales y la lectura con "
        "IA. Su medio llegaría al 31 de mayo sabiendo — con evidencia — "
        "qué mueve a su gente. Para arrancar basta una conversación de "
        "15 minutos. <font color=\"#8A9099\" size=\"8\">Demo: "
        "ricardoruiz.co/test-presidencial-2026.html</font>",
        S("close", fontName="Helvetica", fontSize=9.5, leading=13.5,
          textColor=INK, alignment=TA_LEFT, spaceAfter=0))]],
        colWidths=[W - 2 * MX])
    close.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SHELL),
        ("LINEBEFORE", (0, 0), (0, -1), 2.4, ACCENT),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    s.append(Spacer(1, 5))
    s.append(close)

    doc.build(s)
    import os
    return os.path.getsize(OUT)


if __name__ == "__main__":
    n = build()
    print(f"PDF generado: {OUT}  ({n/1024:.1f} KB)")
