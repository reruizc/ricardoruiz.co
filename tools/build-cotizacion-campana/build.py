#!/usr/bin/env python3
"""
Cotización comercial — Plataforma de inteligencia electoral (2V presidencial 2026).
Marca: Ricardo Ruiz (cotización a su nombre). El PRODUCTO es white-label.
Salida: Bases de datos/cotizacion-campana/Cotizacion-Plataforma-Campana-2V-2026.pdf

NO subir a S3, NO commitear: entregable de cliente confidencial.
Total: $64.000.000 COP (IVA incluido). La negociación de IVA u otros ajustes
queda fuera del documento (se conviene en persona).
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY, TA_RIGHT, TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    KeepTogether,
)

OUTDIR = "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/cotizacion-campana"
OUT = f"{OUTDIR}/Cotizacion-Plataforma-Campana-2V-2026.pdf"

# ---- Identidad Ricardo Ruiz -------------------------------------------------
BLUE   = colors.HexColor("#0047FF")
BLUE_D = colors.HexColor("#0033b3")
INK    = colors.HexColor("#1a1a2e")
SOFT   = colors.HexColor("#44485c")
META   = colors.HexColor("#8a8fa0")
LINE   = colors.HexColor("#dde0e8")
SHELL  = colors.HexColor("#f3f4f8")
SHELLB = colors.HexColor("#eef1fb")

F = os.path.expanduser("~/Library/Fonts")
try:
    pdfmetrics.registerFont(TTFont("Inter", f"{F}/Inter-Regular.ttf"))
    pdfmetrics.registerFont(TTFont("Inter-Bold", f"{F}/Inter-Bold.ttf"))
    pdfmetrics.registerFont(TTFont("Inter-Italic", f"{F}/Inter-Italic.ttf"))
    pdfmetrics.registerFontFamily("Inter", normal="Inter", bold="Inter-Bold",
                                  italic="Inter-Italic", boldItalic="Inter-Bold")
    BASE, BOLD, ITAL = "Inter", "Inter-Bold", "Inter-Italic"
except Exception:
    BASE, BOLD, ITAL = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"

# Syne 800 (logo de marca) — instanciada desde la variable de Google Fonts
FONTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
try:
    pdfmetrics.registerFont(TTFont("Syne", os.path.join(FONTDIR, "Syne-ExtraBold.ttf")))
    SYNE = "Syne"
except Exception:
    SYNE = BOLD

W, H = A4
MX = 17 * mm

ss = getSampleStyleSheet()
def S(name, **kw):
    base = dict(fontName=BASE, fontSize=9.6, leading=14.4, textColor=INK,
                alignment=TA_JUSTIFY, spaceAfter=7)
    base.update(kw)
    return ParagraphStyle(name, parent=ss["Normal"], **base)

st_kick = S("kick", fontName=BOLD, fontSize=8, leading=11, textColor=BLUE,
            alignment=TA_LEFT, spaceAfter=3)
st_h1   = S("h1", fontName=BOLD, fontSize=16.5, leading=19.5, textColor=INK,
            alignment=TA_LEFT, spaceAfter=4)
st_sub  = S("sub", fontName=BASE, fontSize=10.2, leading=14.4, textColor=SOFT,
            alignment=TA_LEFT, spaceAfter=2)
st_sec  = S("sec", fontName=BOLD, fontSize=11, leading=14, textColor=BLUE_D,
            alignment=TA_LEFT, spaceBefore=12, spaceAfter=6)
st_body = S("body")
st_li   = S("li", leftIndent=11, spaceAfter=4.5, alignment=TA_LEFT, leading=14)
st_small= S("small", fontSize=7.7, leading=10.6, textColor=META, alignment=TA_LEFT)
st_cell = S("cell", fontSize=8.4, leading=11.4, alignment=TA_LEFT, spaceAfter=0)
st_cellj= S("cellj", fontSize=8.4, leading=11.4, alignment=TA_JUSTIFY, spaceAfter=0)
st_cellb= S("cellb", fontName=BOLD, fontSize=8.4, leading=11.4, textColor=INK,
            alignment=TA_LEFT, spaceAfter=0)
st_money= S("money", fontName=BOLD, fontSize=9, leading=11.4, textColor=INK,
            alignment=TA_RIGHT, spaceAfter=0)


def bullet(txt, style=st_li):
    return Paragraph(f'<font color="#0047FF">•</font>&nbsp;&nbsp;{txt}', style)


def header(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(INK)
    canvas.rect(0, H - 22 * mm, W, 22 * mm, stroke=0, fill=1)
    y = H - 12.8 * mm
    # 4 barras del logo (azul, alturas 18/14/9/5 escaladas)
    bw, bg = 3.6, 2.2
    bx = MX
    canvas.setFillColor(BLUE)
    canvas.setFillAlpha(0.9)
    for hh in (13.5, 10.5, 6.75, 3.75):
        canvas.roundRect(bx, y, bw, hh, 0.6, stroke=0, fill=1)
        bx += bw + bg
    canvas.setFillAlpha(1)
    barsW = 4 * bw + 3 * bg
    # "Ricardo.Ruiz" en Syne 800 (punto azul), con tracking -0.03em
    to = canvas.beginText()
    to.setFont(SYNE, 16)
    to.setCharSpace(-0.5)
    to.setTextOrigin(MX + barsW + 8, y)
    to.setFillColor(colors.white); to.textOut("Ricardo")
    to.setFillColor(BLUE); to.textOut(".")
    to.setFillColor(colors.white); to.textOut("Ruiz")
    canvas.drawText(to)
    canvas.setFont(BASE, 7.4)
    canvas.setFillColor(colors.HexColor("#a9b0c8"))
    canvas.drawString(MX, H - 18.2 * mm, "Inteligencia electoral y datos · Colombia")
    canvas.setFont(BOLD, 8.6)
    canvas.setFillColor(colors.white)
    canvas.drawRightString(W - MX, y, "COTIZACIÓN")
    canvas.setFont(BASE, 7.4)
    canvas.setFillColor(colors.HexColor("#a9b0c8"))
    canvas.drawRightString(W - MX, H - 18 * mm, "RR-2026-06  ·  5 de junio de 2026")
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.6)
    canvas.line(MX, 12.5 * mm, W - MX, 12.5 * mm)
    canvas.setFont(BASE, 7)
    canvas.setFillColor(META)
    canvas.drawString(MX, 9 * mm, "Ricardo Ruiz  ·  reruizc@gmail.com")
    canvas.drawCentredString(W / 2, 9 * mm, "Documento confidencial")
    canvas.drawRightString(W - MX, 9 * mm, f"Página {doc.page}")
    canvas.restoreState()


def build():
    os.makedirs(OUTDIR, exist_ok=True)
    doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=MX, rightMargin=MX,
                          topMargin=27 * mm, bottomMargin=15 * mm)
    frame = Frame(MX, 14 * mm, W - 2 * MX, H - 27 * mm - 14 * mm, id="f")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=header)])
    s = []
    CW = W - 2 * MX

    # ---- Cabecera -----------------------------------------------------------
    s.append(Paragraph("CAMPAÑA PRESIDENCIAL IVÁN CEPEDA · SEGUNDA VUELTA 2026",
                       st_kick))
    s.append(Paragraph("Una sala de mando territorial para los días que deciden "
                       "la segunda vuelta", st_h1))
    s.append(Paragraph("Producto 100% personalizado para la campaña de Iván "
                       "Cepeda, con acompañamiento humano hasta el último día.",
                       st_sub))
    s.append(Spacer(1, 6))

    meta = Table([[
        Paragraph("<b>Preparado para</b><br/>Campaña Presidencial Iván Cepeda "
                  "— Segunda vuelta 2026", st_cell),
        Paragraph("<b>Entrega e implementación</b><br/>Lunes 8 de junio, "
                  "6:00 p.m. + capacitación", st_cell),
        Paragraph("<b>Operación</b><br/>Equipo dedicado 24/7 hasta el cierre "
                  "de campaña", st_cell),
    ]], colWidths=[CW / 3.0] * 3)
    meta.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, -1), SHELL),
        ("LINEBEFORE", (1, 0), (-1, -1), 0.5, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
    ]))
    s.append(meta)

    # ---- Planteamiento ------------------------------------------------------
    s.append(Paragraph("El planteamiento", st_sec))
    s.append(Paragraph(
        "En una segunda vuelta todo se define en el territorio y en muy pocos "
        "días. La campaña no necesita otra encuesta: necesita saber, <b>barrio "
        "por barrio y municipio por municipio</b>, qué mueve al votante, dónde "
        "están los votos por conquistar y qué debe hacer cada coordinador hoy. "
        "Esta plataforma reúne, en una sola herramienta hecha a la medida de la "
        "campaña de Iván Cepeda, el histórico electoral del país (2010–2026) "
        "ponderado, el monitoreo diario de prensa y redes, y una lectura con "
        "inteligencia artificial que, teniendo en cuenta todo el contexto "
        "barrial, veredal o municipal, aterriza ese análisis al territorio de "
        "cada persona. Se despliega <b>bajo la marca y el dominio de la "
        "campaña</b> "
        "(white-label), con un equipo humano detrás ajustándola a diario.",
        st_body))

    # ---- Diferencial --------------------------------------------------------
    s.append(Paragraph("Por qué no es un lector de medios genérico", st_sec))
    s.append(bullet("<b>Construido sobre el dato electoral del país, no solo "
                    "sobre la prensa.</b> Las herramientas de escucha del "
                    "mercado dicen <i>qué se dice</i>; esta plataforma cruza "
                    "esa conversación con el voto real a nivel de barrio, puesto "
                    "y mesa, y dice además <i>dónde está su voto y qué hacer "
                    "con él</i>."))
    s.append(bullet("<b>100% enfocada en la campaña de Iván Cepeda.</b> "
                    "Arquetipos, mensajes, metas y alertas calibrados a esta "
                    "contienda — no un tablero estándar reutilizado para "
                    "cualquier cliente."))
    s.append(bullet("<b>Acompañamiento humano, no un software que se entrega y "
                    "ya.</b> Un equipo dedicado interpreta, ajusta y traduce "
                    "los datos en decisiones todos los días hasta el cierre."))

    # ---- Dos niveles --------------------------------------------------------
    s.append(Paragraph("Cómo se usa — dos niveles de acceso", st_sec))
    s.append(bullet("<b>Coordinadores (25–30 personas).</b> Acceso completo, "
                    "con análisis del candidato propio <i>y</i> del principal "
                    "contendor (inteligencia del rival). Cada coordinador entra "
                    "a un <b>mapa de su zona asignada con la evolución diaria</b> "
                    "de su territorio, y puede hacer drill a cualquier punto del "
                    "país."))
    s.append(bullet("<b>Estructura ampliada (500–1.000 personas).</b> Acceso "
                    "enfocado en la campaña de Cepeda: el <b>mapa de su zona "
                    "asignada con la evolución diaria</b>, su meta y su mensaje "
                    "del día."))

    # ---- Componentes (nombres técnicos + aplicación) ------------------------
    s.append(Paragraph("Qué hace la plataforma — componentes", st_sec))

    def crow(name, app):
        return [Paragraph(name, st_cellb), Paragraph(app, st_cellj)]

    comp_h = [Paragraph("Componente (nombre técnico)", st_cellb),
              Paragraph("Para qué le sirve a la campaña", st_cellb)]
    comps = [
        crow("Cartografía emocional del electorado — segmentación psicográfica "
             "territorial no declarativa (5 arquetipos)",
             "Identifica qué mueve al votante en cada barrio y municipio sin "
             "encuestas, a partir de la huella electoral real; define con qué "
             "mensaje conecta cada territorio."),
        crow("Agregador ponderado de encuestas + inventario de evidencia "
             "territorial",
             "Consolida las encuestas publicadas con un ponderador propio "
             "calibrado (corrige sesgos de firma) y muestra qué datos hay por "
             "territorio: un solo pulso confiable, sin ruido."),
        crow("Media intelligence + escucha social — índices de saliencia, "
             "atribución y volatilidad",
             "Monitoreo diario de prensa y conversación en redes: qué temas "
             "suben, a quién se atribuyen y qué tan rápido se mueven, para "
             "reaccionar el mismo día."),
        crow("Microtargeting territorial y metas de movilización",
             "Traduce la meta nacional en votos concretos por barrio y puesto "
             "para cada coordinador, con el mensaje sugerido del día según el "
             "rastreo de noticias."),
        crow("Mapeo de actores y redes de influencia (proxy electoral)",
             "El edil, concejal o representante más votado en cada punto: a "
             "quién llamar primero para sumar estructura y cerrar alianzas."),
        crow("Modelo de voto persuadible (propensión / soft-vote afín)",
             "Dónde está el voto afín movible —no solo dónde se es fuerte— "
             "para enfocar el esfuerzo donde de verdad hay votos por ganar."),
        crow("Priorización por ROI electoral (análisis de puestos bisagra)",
             "Rankea los puestos donde cada hora de trabajo en territorio rinde "
             "más votos; evita gastar recursos donde la elección ya está "
             "decidida."),
        crow("Sistema de gestión de estructura en tiempo real (CRM de campaña)",
             "Los coordinadores registran el avance y la dirigencia ve la "
             "cobertura en vivo, con huecos y metas: el comando central de la "
             "operación de tierra."),
        crow("Plan de cobertura del día E — testigos por mesa + guion de "
             "contacto",
             "Plan de testigos con detección de huecos y guion de puerta a "
             "puerta por arquetipo, para blindar la jornada y el cierre."),
    ]
    ct = Table([comp_h] + comps, colWidths=[CW * 0.40, CW * 0.60])
    ct.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), SHELL),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, BLUE),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, LINE),
        ("LINEAFTER", (0, 0), (0, -1), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    s.append(ct)

    # ---- Equipo -------------------------------------------------------------
    eq = [Paragraph("Equipo a cargo", st_sec),
          Paragraph("Coordinadores principales de un equipo de <b>6 "
                    "profesionales</b> (ciencia política, análisis de datos, "
                    "enfoque conductual y comunicación estratégica) dedicado "
                    "<b>24/7 hasta el cierre</b> de la campaña.", st_body)]
    team = Table([[
        Paragraph("<b>Ricardo Ruiz</b><br/>Politólogo (Universidad Nacional de "
                  "Colombia) y magíster en Políticas Públicas (Universidad de "
                  "los Andes). Cinco años en análisis de datos aplicado a "
                  "procesos políticos y electorales, en firmas encuestadoras y "
                  "en los sectores público y privado. Especialista en "
                  "comportamiento electoral (con publicaciones académicas), "
                  "modelos cuantitativos y machine learning. Experiencia en "
                  "Colombia, México, Perú y Paraguay.", st_cellj),
        Paragraph("<b>Nury A. Gómez</b><br/>Politóloga (Universidad Nacional de "
                  "Colombia, sede Medellín), magíster en Neuromarketing y en "
                  "Economía Conductual. Consultora política con más de 15 años "
                  "de experiencia en "
                  "campañas en Colombia, Paraguay y Perú. Especialista en "
                  "estrategia, construcción de mensaje y lectura conductual del "
                  "electorado.", st_cellj),
    ]], colWidths=[CW / 2.0, CW / 2.0])
    team.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, -1), SHELL),
        ("LINEBEFORE", (1, 0), (1, -1), 0.5, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
    ]))
    s.append(KeepTogether(eq + [team]))

    # ---- Cómo trabajamos ----------------------------------------------------
    s.append(Paragraph("Cómo trabajamos durante la campaña", st_sec))
    s.append(bullet("<b>Entrega e implementación:</b> lunes 8 de junio de 2026, "
                    "6:00 p.m., con una capacitación al equipo coordinador."))
    s.append(bullet("<b>Operación 24/7:</b> acompañamiento del equipo hasta el "
                    "último día de campaña."))
    s.append(bullet("<b>Reuniones de estrategia semanales</b> y <b>ajustes "
                    "diarios</b> del sistema según la lectura del monitoreo de "
                    "medios y de las conversaciones en redes sociales."))

    # ---- Inversión ----------------------------------------------------------
    inv = [Paragraph("Inversión", st_sec)]
    rows = [
        [Paragraph("Concepto", st_cellb), Paragraph("Detalle", st_cellb),
         Paragraph("Valor (COP)", ParagraphStyle("ih", parent=st_cellb,
                                                  alignment=TA_RIGHT))],
        [Paragraph("<b>Montaje e implementación</b>", st_cell),
         Paragraph("Pago único: desarrollo y personalización total, despliegue "
                   "white-label, integración de fuentes y capacitación.",
                   st_cell),
         Paragraph("$34.000.000", st_money)],
        [Paragraph("<b>Seguimiento y operación 24/7</b>", st_cell),
         Paragraph("Equipo de 6 dedicado hasta el cierre: monitoreo y "
                   "generación con IA, reuniones semanales y ajustes diarios, "
                   "soporte.", st_cell),
         Paragraph("$22.000.000", st_money)],
        [Paragraph("<b>Ciberseguridad y protección de datos</b>", st_cell),
         Paragraph("Aseguramiento de la plataforma, control de accesos, cifrado "
                   "y resguardo de la información de la campaña.", st_cell),
         Paragraph("$8.000.000", st_money)],
        [Paragraph("<b>TOTAL</b>", st_cellb),
         Paragraph("Producto personalizado completo, operación hasta el cierre "
                   "de campaña. IVA incluido.", st_cell),
         Paragraph("<b>$64.000.000</b>", ParagraphStyle(
             "tot", parent=st_money, fontSize=10, textColor=BLUE_D))],
    ]
    it = Table(rows, colWidths=[38 * mm, CW - 38 * mm - 34 * mm, 34 * mm])
    it.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), SHELL),
        ("BACKGROUND", (0, -1), (-1, -1), SHELLB),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, BLUE),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, LINE),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    inv.append(it)
    inv.append(Paragraph("Cifras en pesos colombianos (COP), IVA incluido.",
                         st_small))
    s.append(KeepTogether(inv))

    # ---- Condiciones --------------------------------------------------------
    s.append(Paragraph("Condiciones comerciales", st_sec))
    for t in [
        "<b>Entrega:</b> lunes 8 de junio de 2026, 6:00 p.m., con capacitación.",
        "<b>Operación:</b> hasta el último día de campaña.",
        "<b>Forma de pago:</b> 50% a la aprobación (inicia el montaje), 50% a "
        "la entrega.",
        "<b>Vigencia de esta oferta:</b> hasta el 7 de junio de 2026.",
        "<b>White-label total:</b> el producto se aloja en infraestructura y "
        "dominio que indique la campaña, sin marca del proveedor.",
        "<b>Datos y seguridad:</b> cumplimiento de la Ley 1581/2012 — los "
        "contactos solo se usan con autorización expresa. El seguimiento de "
        "encuestas agrega estudios ya publicados y no constituye una encuesta "
        "nueva (Ley 2494/2025).",
        "<b>No incluye:</b> pauta ni publicidad digital.",
    ]:
        s.append(bullet(t))

    # ---- Cierre -------------------------------------------------------------
    s.append(Spacer(1, 6))
    close = Table([[Paragraph(
        "Esta plataforma le da a la campaña de Iván Cepeda algo que ninguna "
        "herramienta genérica ofrece: el dato electoral granular del país, ya "
        "curado, convertido en una orden clara para cada coordinador — con un "
        "equipo humano interpretándolo y ajustándolo todos los días, hasta el "
        "último de la campaña.",
        S("cl", fontName=BASE, fontSize=10, leading=14.5, textColor=INK,
          alignment=TA_LEFT, spaceAfter=0))]], colWidths=[CW])
    close.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SHELLB),
        ("LINEBEFORE", (0, 0), (0, -1), 2.6, BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    s.append(KeepTogether(close))

    doc.build(s)
    return os.path.getsize(OUT)


if __name__ == "__main__":
    n = build()
    print(f"PDF generado: {OUT}  ({n/1024:.1f} KB)")
