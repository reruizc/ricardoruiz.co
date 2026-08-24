# -*- coding: utf-8 -*-
"""
PDF "Estado de cosas" para la alianza con Cauce (~12 paginas).
Documento estratégico para Diego Baquero Ospina y socios de Cauce:
plataforma (SKU A gremios + SKU B congresistas), fuentes, IA, diferencial,
mapa competitivo (Dapper / Sonar-Orza / Deloitte) y puntos para la charla.

Cuerpo en Helvetica (base-14; soporta acentos y ñ vía WinAnsi).
Títulos de despliegue en Arima. Gráficos vectoriales propios.
Logo Ricardo.Ruiz al pie.

Salida: Propuestas/Cauce-Estado-de-Cosas-Inteligencia-Legislativa.pdf
Correr: python3 tools/cauce/build_estado_de_cosas.py
"""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    NextPageTemplate, PageBreak, KeepTogether, Flowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.graphics.shapes import Drawing, Rect, String, Polygon, Line

ROOT = "/Users/ricardoruiz/ricardoruiz.co"
ARIMA = os.path.join(ROOT, "tools", "edad-1v-2026", "fonts")
LOGO = os.path.join(ROOT, "Bases de datos", "output_abelardo_cartagena", "logo_ricardoruiz.png")
OUT = os.path.join(ROOT, "Propuestas", "Cauce-Estado-de-Cosas-Inteligencia-Legislativa.pdf")

pdfmetrics.registerFont(TTFont("Arima", os.path.join(ARIMA, "Arima-Bold.ttf")))

BODY, BODY_B, BODY_I, DISP = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Arima"

INK      = colors.HexColor("#16202A")
BRAND    = colors.HexColor("#143A63")
BRAND_MD = colors.HexColor("#2E5385")
BRAND_LT = colors.HexColor("#E9EEF6")
BRAND_XL = colors.HexColor("#8AA0BC")
ACCENT   = colors.HexColor("#B23A2E")
ACCENT_LT= colors.HexColor("#F6E9E6")
GRAY     = colors.HexColor("#59636E")
LINE     = colors.HexColor("#D7DDE4")
WARM     = colors.HexColor("#FBFAF7")
WHITE    = colors.white

PAGE_W, PAGE_H = letter
MX = 2.0 * cm
USABLE = PAGE_W - 2*MX
LOGO_AR = 2361.0 / 201.0

def S(name, **kw): return ParagraphStyle(name, **kw)

st_kicker   = S("kicker", fontName=BODY_B, fontSize=9.5, textColor=BRAND, leading=13)
st_ctitle   = S("ctitle", fontName=DISP, fontSize=34, textColor=INK, leading=38, spaceBefore=10, spaceAfter=14)
st_csub     = S("csub", fontName=BODY, fontSize=13, textColor=GRAY, leading=19, spaceAfter=8)
st_meta     = S("meta", fontName=BODY_B, fontSize=11.5, textColor=INK, leading=16.5)
st_meta_lt  = S("meta_lt", fontName=BODY, fontSize=11.5, textColor=GRAY, leading=16.5)

st_secnum   = S("secnum", fontName=DISP, fontSize=13, textColor=BRAND, leading=15, spaceBefore=24, keepWithNext=1)
st_h2       = S("h2", fontName=DISP, fontSize=20, textColor=INK, leading=24, spaceBefore=2, spaceAfter=10, keepWithNext=1)
st_h3       = S("h3", fontName=BODY_B, fontSize=12.5, textColor=BRAND, leading=16, spaceBefore=8, spaceAfter=4)
st_body     = S("body", fontName=BODY, fontSize=11.3, textColor=INK, leading=16.8, alignment=TA_JUSTIFY, spaceAfter=9)
st_body_l   = S("body_l", fontName=BODY, fontSize=11.3, textColor=INK, leading=16.8, alignment=TA_LEFT, spaceAfter=9)
st_bull     = S("bull", fontName=BODY, fontSize=11.3, textColor=INK, leading=16.4, alignment=TA_LEFT,
                leftIndent=16, bulletIndent=2, spaceAfter=6)
st_callout  = S("callout", fontName=BODY_I, fontSize=14, textColor=INK, leading=20.5, alignment=TA_LEFT)
st_callout_a= S("callout_a", fontName=BODY_B, fontSize=9, textColor=BRAND, leading=13, spaceBefore=8)

st_box_h    = S("box_h", fontName=BODY_B, fontSize=11, textColor=WHITE, leading=14)
st_dif_h    = S("dif_h", fontName=BODY_B, fontSize=10.4, textColor=INK, leading=13.6)
st_dif_b    = S("dif_b", fontName=BODY, fontSize=10.2, textColor=INK, leading=13.8)
st_sku_tag  = S("sku_tag", fontName=BODY_B, fontSize=9, textColor=colors.HexColor("#C7D6EA"), leading=12)

st_mx_h     = S("mx_h", fontName=BODY_B, fontSize=8.6, textColor=WHITE, leading=10.6)
st_mx_dim   = S("mx_dim", fontName=BODY_B, fontSize=8.3, textColor=INK, leading=10.3)
st_mx       = S("mx", fontName=BODY, fontSize=8.2, textColor=INK, leading=10.3)
st_mx_us    = S("mx_us", fontName=BODY_B, fontSize=8.2, textColor=BRAND, leading=10.3)

st_cap      = S("cap", fontName=BODY_I, fontSize=8.5, textColor=GRAY, leading=11.5, spaceBefore=4)


class HRule(Flowable):
    def __init__(self, width, color=LINE, thick=0.8):
        Flowable.__init__(self); self.width=width; self.color=color; self.thick=thick
    def wrap(self, *a): return (self.width, self.thick)
    def draw(self):
        self.canv.setStrokeColor(self.color); self.canv.setLineWidth(self.thick)
        self.canv.line(0, 0, self.width, 0)


def callout(text, attr, accent=ACCENT, bg=ACCENT_LT):
    inner = [Paragraph(text, st_callout), Paragraph(attr, st_callout_a)]
    t = Table([[inner]], colWidths=[USABLE])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),bg),
        ("LEFTPADDING",(0,0),(-1,-1),18),("RIGHTPADDING",(0,0),(-1,-1),18),
        ("TOPPADDING",(0,0),(-1,-1),15),("BOTTOMPADDING",(0,0),(-1,-1),15),
        ("LINEBEFORE",(0,0),(0,-1),3.5,accent),
    ]))
    return t


def stat_strip(items):
    """Fila de estadísticas: (numero, etiqueta)."""
    cells = []
    for num, lab in items:
        cells.append([Paragraph(num, S("sn", fontName=DISP, fontSize=26, textColor=BRAND, leading=28)),
                      Paragraph(lab, S("sl", fontName=BODY, fontSize=8.8, textColor=GRAY, leading=11.5))])
    inner = [Table([[c[0]],[c[1]]], style=TableStyle([
                ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
                ("TOPPADDING",(0,0),(-1,-1),1),("BOTTOMPADDING",(0,0),(-1,-1),1)])) for c in cells]
    n = len(items); cw = USABLE / n
    t = Table([inner], colWidths=[cw]*n)
    st = [("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),
          ("LEFTPADDING",(0,0),(-1,-1),16),("RIGHTPADDING",(0,0),(-1,-1),8),
          ("BACKGROUND",(0,0),(-1,-1),BRAND_LT)]
    for i in range(1, n):
        st.append(("LINEBEFORE",(i,0),(i,0),0.8,BRAND_XL))
    t.setStyle(TableStyle(st))
    return t


def sku_box(tag, title, rows, accent):
    head = Table([[Paragraph(tag, st_sku_tag), Paragraph(title, st_box_h)]], colWidths=[2.4*cm, USABLE-2.4*cm])
    head.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),accent),
        ("LEFTPADDING",(0,0),(-1,-1),12),("RIGHTPADDING",(0,0),(-1,-1),12),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
    body_rows = [[Paragraph(l, st_h3), Paragraph(t, st_body_l)] for l,t in rows]
    bt = Table(body_rows, colWidths=[3.4*cm, USABLE-3.4*cm])
    bt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),WARM),
        ("LEFTPADDING",(0,0),(-1,-1),12),("RIGHTPADDING",(0,0),(-1,-1),12),
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("VALIGN",(0,0),(-1,-1),"TOP"),("LINEBELOW",(0,0),(-1,-2),0.5,LINE)]))
    return KeepTogether([head, bt, Spacer(1,12)])


def _logo(canvas, x, y, h):
    try:
        canvas.drawImage(LOGO, x, y, width=h*LOGO_AR, height=h, mask="auto", preserveAspectRatio=True, anchor="sw")
    except Exception:
        canvas.setFont(BODY_B, 8); canvas.setFillColor(INK); canvas.drawString(x, y, "Ricardo.Ruiz")


def on_cover(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BRAND); canvas.rect(0, PAGE_H-0.5*cm, PAGE_W, 0.5*cm, fill=1, stroke=0)
    canvas.setFillColor(GRAY); canvas.setFont(BODY_I, 9.5)
    canvas.drawString(MX, 2.55*cm, "El valor no está en el volumen de información, sino en el criterio para leerla.")
    canvas.setStrokeColor(LINE); canvas.setLineWidth(0.8); canvas.line(MX, 2.3*cm, PAGE_W-MX, 2.3*cm)
    _logo(canvas, MX, 1.5*cm, 0.52*cm)
    canvas.setFillColor(GRAY); canvas.setFont(BODY, 8.5); canvas.drawRightString(PAGE_W-MX, 1.62*cm, "Julio de 2026")
    canvas.restoreState()


def on_content(canvas, doc):
    canvas.saveState()
    canvas.setFont(BODY_B, 7.5); canvas.setFillColor(BRAND)
    canvas.drawString(MX, PAGE_H-1.35*cm, "CAUCE  ·  POWERED BY RICARDO.RUIZ")
    canvas.setFont(BODY, 7.5); canvas.setFillColor(GRAY)
    canvas.drawRightString(PAGE_W-MX, PAGE_H-1.35*cm, "Inteligencia legislativa y regulatoria  ·  Confidencial")
    canvas.setStrokeColor(LINE); canvas.setLineWidth(0.6); canvas.line(MX, PAGE_H-1.55*cm, PAGE_W-MX, PAGE_H-1.55*cm)
    canvas.line(MX, 1.35*cm, PAGE_W-MX, 1.35*cm)
    _logo(canvas, MX, 0.82*cm, 0.40*cm)
    canvas.setFont(BODY, 8); canvas.setFillColor(GRAY); canvas.drawRightString(PAGE_W-MX, 0.98*cm, "%d" % doc.page)
    canvas.restoreState()


# ---------- GRAFICOS VECTORIALES ----------
def _txt(g, x, y, s, font=BODY, size=9, color=INK, anchor="start"):
    t = String(x, y, s, fontName=font, fontSize=size, fillColor=color); t.textAnchor = anchor; g.add(t)

def funnel_drawing():
    W = USABLE
    bh, gap = 38, 26
    bars = [
        (452, BRAND_XL, "Más de 600 fuentes  ·  miles de documentos al día"),
        (330, BRAND,    "IA de frontera + curaduría: filtra por relevancia"),
        (188, ACCENT,   "3 a 5 alertas que importan"),
    ]
    steps = ["clasificación y descarte del ruido", "lectura del analista de asuntos públicos"]
    H = len(bars)*bh + (len(bars)-1)*gap
    g = Drawing(W, H); cx = W/2.0
    for i,(w, fill, label) in enumerate(bars):
        ytop = H - i*(bh+gap); y = ytop - bh
        g.add(Rect(cx-w/2.0, y, w, bh, rx=5, ry=5, fillColor=fill, strokeColor=None))
        _txt(g, cx, y+bh/2.0-4, label, font=BODY_B, size=9.6, color=WHITE, anchor="middle")
        if i < len(bars)-1:
            ay1 = y - gap + 8
            g.add(Line(cx, y, cx, ay1+3, strokeColor=BRAND_MD, strokeWidth=1.4))
            g.add(Polygon([cx-6, ay1+5, cx+6, ay1+5, cx, ay1-3], fillColor=BRAND_MD, strokeColor=None))
            _txt(g, cx+14, ay1, steps[i], font=BODY_I, size=8.4, color=GRAY, anchor="start")
    return g

def sources_bar_drawing():
    cats = [
        ("Medios (nacionales y regionales)", 200),
        ("Redes sociales oficiales y voceros", 130),
        ("Entidades territoriales", 120),
        ("Ejecutivo nacional (min. y agencias)", 70),
        ("Diarios y gacetas oficiales", 33),
        ("Datos abiertos y contratación", 22),
        ("Superintendencias y comisiones", 18),
        ("Congreso y órgano legislativo", 16),
        ("Órganos de control y altas cortes", 12),
    ]
    labelw = 210
    rowh = 21
    barmax = W_bar = USABLE - labelw - 46
    maxc = max(c for _,c in cats)
    H = len(cats)*rowh + 14
    g = Drawing(USABLE, H)
    for i,(lab,c) in enumerate(cats):
        y = H - 10 - i*rowh
        _txt(g, 0, y-3, lab, font=BODY, size=8.6, color=INK, anchor="start")
        w = max(3, c/maxc*barmax)
        g.add(Rect(labelw, y-8, w, 12, rx=2, ry=2, fillColor=BRAND, strokeColor=None))
        _txt(g, labelw+w+6, y-3, str(c), font=BODY_B, size=8.8, color=BRAND, anchor="start")
    return g

def arch_drawing():
    W = USABLE
    H = 316
    g = Drawing(W, H)
    def box(y, h, fill, tc, title, sub=None, sub_color=WHITE):
        g.add(Rect(0, y, W, h, rx=6, ry=6, fillColor=fill, strokeColor=None))
        if sub:
            _txt(g, W/2.0, y+h-16, title, font=BODY_B, size=10, color=tc, anchor="middle")
            _txt(g, W/2.0, y+8, sub, font=BODY, size=8.6, color=sub_color, anchor="middle")
        else:
            _txt(g, W/2.0, y+h/2.0-4, title, font=BODY_B, size=10, color=tc, anchor="middle")
    def arrow(y):
        g.add(Line(W/2.0, y+9, W/2.0, y+2, strokeColor=BRAND_MD, strokeWidth=1.4))
        g.add(Polygon([W/2.0-6, y+4, W/2.0+6, y+4, W/2.0, y-4], fillColor=BRAND_MD, strokeColor=None))
    y = H-46
    box(y, 46, BRAND_LT, INK, "FUENTES  ·  600+", "Congreso · superintendencias · cortes · ministerios · medios · redes · datos abiertos", sub_color=GRAY)
    arrow(y-22)
    y = y-22-46
    box(y, 46, BRAND_MD, WHITE, "MOTOR DE INGESTA", "normaliza · deduplica · indexa cada documento por tema y territorio")
    arrow(y-22); y = y-22-46
    box(y, 46, BRAND, WHITE, "CAPA DE IA  ·  Claude · DeepSeek", "filtra por relevancia · resume con fidelidad · rastrea el trámite · cita la fuente")
    arrow(y-22); y = y-22-42
    box(y, 42, ACCENT, WHITE, "ANALISTA DE CAUCE", "interpreta · prioriza · recomienda la acción")
    arrow(y-22); y = y-22-40
    half = (W-14)/2.0
    g.add(Rect(0, y, half, 40, rx=6, ry=6, fillColor=WHITE, strokeColor=BRAND, strokeWidth=1.2))
    _txt(g, half/2.0, y+40/2.0-4, "SKU A · Sector privado", font=BODY_B, size=10, color=BRAND, anchor="middle")
    g.add(Rect(W-half, y, half, 40, rx=6, ry=6, fillColor=WHITE, strokeColor=ACCENT, strokeWidth=1.2))
    _txt(g, W-half/2.0, y+40/2.0-4, "SKU B · Congresista", font=BODY_B, size=10, color=ACCENT, anchor="middle")
    return g


def humanloop_drawing():
    W, H = USABLE, 66
    g = Drawing(W, H); gap = 30
    bw = (W - 2*gap) / 3.0
    items = [(BRAND, WHITE, "IA", "filtra el volumen 24/7", False),
             (ACCENT, WHITE, "ASESOR", "aporta el criterio", False),
             (WHITE, BRAND, "CLIENTE", "decide con respaldo", True)]
    for i,(fill, tc, t1, t2, outline) in enumerate(items):
        x = i*(bw+gap)
        if outline:
            g.add(Rect(x, 6, bw, H-12, rx=6, ry=6, fillColor=WHITE, strokeColor=BRAND, strokeWidth=1.3))
        else:
            g.add(Rect(x, 6, bw, H-12, rx=6, ry=6, fillColor=fill, strokeColor=None))
        _txt(g, x+bw/2.0, H-26, t1, font=BODY_B, size=10.5, color=tc, anchor="middle")
        _txt(g, x+bw/2.0, 16, t2, font=BODY, size=8.4, color=(tc if not outline else GRAY), anchor="middle")
        if i < 2:
            axe = x+bw+gap-3; ay = H/2.0
            g.add(Line(x+bw+3, ay, axe-4, ay, strokeColor=BRAND_MD, strokeWidth=1.4))
            g.add(Polygon([axe-6, ay+5, axe-6, ay-5, axe+2, ay], fillColor=BRAND_MD, strokeColor=None))
    return g


def stairs_drawing():
    W, H = USABLE, 126
    g = Drawing(W, H); gap = 16
    bw = (W - 2*gap)/3.0
    steps = [(58, BRAND_XL, "Nivel 1", "Arranque"),
             (86, BRAND_MD, "Nivel 2", "Dedicado"),
             (114, BRAND, "Nivel 3", "Célula de sector")]
    for i,(h, fill, t1, t2) in enumerate(steps):
        x = i*(bw+gap)
        g.add(Rect(x, 0, bw, h, rx=6, ry=6, fillColor=fill, strokeColor=None))
        _txt(g, x+bw/2.0, h-20, t1, font=BODY_B, size=10.5, color=WHITE, anchor="middle")
        _txt(g, x+bw/2.0, h-34, t2, font=BODY, size=8.6, color=WHITE, anchor="middle")
    return g


def dif_box():
    diff = [
        ("Precisión sobre volumen", "Filtramos por relevancia real para ese cliente, no por palabra clave. Menos ruido, más criterio."),
        ("Análisis, no operación", "Leemos el dato, no solo lo entregamos. El insumo llega interpretado y con una recomendación."),
        ("Humano + IA", "El analista de asuntos públicos de Cauce sobre un motor de datos propio: la combinación que ningún competidor reúne hoy."),
        ("Data propia", "Construimos el histórico legislativo y regulatorio desde la fuente. No dependemos de terceros."),
        ("Trazabilidad", "Cada afirmación cita su fuente oficial. Cero dato sin respaldo, cero alucinación."),
    ]
    hdr = Table([[Paragraph("EL DIFERENCIAL EN CINCO PIEZAS", st_box_h)]], colWidths=[USABLE])
    hdr.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),BRAND),
        ("LEFTPADDING",(0,0),(-1,-1),12),("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    rows = [[Paragraph(h, st_dif_h), Paragraph(t, st_dif_b)] for h,t in diff]
    bt = Table(rows, colWidths=[4.8*cm, USABLE-4.8*cm])
    bt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),WARM),
        ("LEFTPADDING",(0,0),(-1,-1),12),("RIGHTPADDING",(0,0),(-1,-1),12),
        ("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9),
        ("VALIGN",(0,0),(-1,-1),"TOP"),("LINEBELOW",(0,0),(-1,-2),0.5,LINE),("LINEBEFORE",(0,0),(0,-1),3.5,BRAND)]))
    return KeepTogether([hdr, bt])


def alert_cards():
    def card(title, reading, ref, accent):
        inner = [Paragraph(title, S("ac_t", fontName=BODY_B, fontSize=10.5, textColor=accent, leading=14)),
                 Paragraph(reading, S("ac_r", fontName=BODY, fontSize=9.8, textColor=INK, leading=13.8, spaceBefore=3)),
                 Paragraph(ref, S("ac_f", fontName=BODY_I, fontSize=8.8, textColor=GRAY, leading=12, spaceBefore=4))]
        t = Table([[inner]], colWidths=[USABLE])
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),WARM),
            ("LEFTPADDING",(0,0),(-1,-1),14),("RIGHTPADDING",(0,0),(-1,-1),14),
            ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),
            ("LINEBEFORE",(0,0),(0,-1),3,accent)]))
        return t
    c1 = card("Proyecto de Ley 123 de 2026 — habilitación de IPS",
              "Modifica el régimen de habilitación de las IPS. El ponente es afín a esa empresa y hay ventana de "
              "incidencia en primer debate. Riesgo medio, oportunidad alta.",
              "Fuente: Gaceta del Congreso 228 de 2026   ·   Acción: preparar concepto técnico para la Comisión Séptima.", BRAND)
    c2 = card("Circular externa — Superintendencia de Salud",
              "Crea un nuevo reporte obligatorio para EPS e IPS, con plazo de 30 días.",
              "Fuente: Supersalud, circular reciente   ·   Acción: activar al área de cumplimiento.", ACCENT)
    return KeepTogether([c1, Spacer(1,8), c2])


def matrix():
    P = lambda t: Paragraph(t, st_mx); U = lambda t: Paragraph(t, st_mx_us)
    D = lambda t: Paragraph(t, st_mx_dim); H = lambda t: Paragraph(t, st_mx_h)
    dims = [
        ("Naturaleza", "SaaS self-serve con IA propia", "Govtech híbrida: producto + asesor", "Consultoría enterprise con herramienta", "Motor de datos + IA + analista de AP"),
        ("Fuentes declaradas", "Más de 500", "No las declara", "No las declara", "Más de 600, mapeadas y priorizadas"),
        ("Modelo de IA", "Propio, entrenado y opaco (caja negra)", "Modelo predictivo propio", "Marginal; pesa lo humano", "Frontera: Claude y DeepSeek + function calling"),
        ("Precisión / relevancia", "Amplia pero ruidosa", "Fuerte en predicción, floja en filtrado", "Alta, pero lenta y cara", "El eje del producto: señal filtrada por relevancia"),
        ("Análisis + humano", "No — puro software", "Parcial (asesor)", "Sí — es el core", "Sí — analista de Cauce sobre el motor"),
        ("Data propia", "Sí", "No — depende de La Silla Datos", "Mixta", "Sí — histórico legislativo y regulatorio propio"),
        ("Le vende a", "Corporativo / multinacional", "Corporativo regulado", "Gran empresa (compliance)", "Sector privado, cooperación y congresistas"),
        ("Le habla al congresista", "No", "No", "No", "Sí — espacio sin competencia"),
        ("Trazabilidad de la fuente", "Declarada, no verificable de a poco", "Parcial", "Alta (revisión humana)", "Total: cada alerta cita su norma"),
        ("Su flanco", "Volumen sin lectura; sin analista", "Data de un tercero; solo regulatorio", "Caro y lento; no hace política ni lobby", "Por construir: de eso trata la alianza"),
    ]
    data = [[H(""), H("DAPPER"), H("SONAR (ORZA)"), H("DELOITTE"), H("NOSOTROS")]]
    for dim,a,b,c,d in dims: data.append([D(dim), P(a), P(b), P(c), U(d)])
    lc = 2.9*cm; pc = (USABLE-lc)/4.0
    t = Table(data, colWidths=[lc,pc,pc,pc,pc], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),INK),("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LINEBELOW",(0,0),(-1,-1),0.5,LINE),("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, WARM]),
        ("BACKGROUND",(4,1),(4,-1),BRAND_LT),("LINEBEFORE",(4,0),(4,-1),2.5,BRAND),
        ("BACKGROUND",(0,1),(0,-1),colors.HexColor("#F1F3F6"))]))
    return t


def build():
    doc = BaseDocTemplate(OUT, pagesize=letter, leftMargin=MX, rightMargin=MX,
                          topMargin=2.0*cm, bottomMargin=1.9*cm,
                          title="Inteligencia legislativa y regulatoria de precisión — Cauce", author="Ricardo Ruiz")
    fc = Frame(MX, 2.9*cm, USABLE, PAGE_H-2.9*cm-3.0*cm, id="cover")
    fk = Frame(MX, 1.6*cm, USABLE, PAGE_H-1.6*cm-2.0*cm, id="content")
    doc.addPageTemplates([PageTemplate(id="cover", frames=[fc], onPage=on_cover),
                          PageTemplate(id="content", frames=[fk], onPage=on_content)])
    E = []
    B = lambda t: E.append(Paragraph(t, st_body))
    SP = lambda h: E.append(Spacer(1, h))

    # ===== PORTADA =====
    SP(1.7*cm)
    E.append(Paragraph("DOCUMENTO ESTRATÉGICO&nbsp;&nbsp;·&nbsp;&nbsp;CONFIDENCIAL", st_kicker))
    E.append(Paragraph('<font name="Arima" size="19">Cauce</font>&nbsp;&nbsp;<font size="10.5" color="#59636E">powered by Ricardo.Ruiz</font>',
                       S("prod", fontName=BODY, fontSize=10.5, textColor=BRAND, leading=23, spaceBefore=8, spaceAfter=0)))
    E.append(Paragraph("Inteligencia legislativa y regulatoria de precisión", st_ctitle))
    E.append(Paragraph("Una plataforma de alertas para el sector privado y de acompañamiento a congresistas. "
                       "Estado del mercado, diferencial competitivo y hoja de ruta.", st_csub))
    SP(0.5*cm); E.append(HRule(USABLE)); SP(0.5*cm)
    meta = Table([
        [Paragraph("Preparado para", st_meta_lt), Paragraph("Equipo de Cauce", st_meta)],
        [Paragraph("Autor", st_meta_lt), Paragraph("Ricardo Ruiz", st_meta)],
        [Paragraph("Fecha", st_meta_lt), Paragraph("Julio de 2026", st_meta)],
        [Paragraph("Propósito", st_meta_lt), Paragraph("Insumo para posicionar el producto ante los primeros clientes", st_meta)],
    ], colWidths=[3.6*cm, USABLE-3.6*cm])
    meta.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),5),
        ("BOTTOMPADDING",(0,0),(-1,-1),5),("LEFTPADDING",(0,0),(-1,-1),0)]))
    E.append(meta)
    E.append(NextPageTemplate("content")); E.append(PageBreak())

    # ===== 01 =====
    E.append(Paragraph("01", st_secnum))
    E.append(Paragraph("El punto de partida: sobra información, falta criterio", st_h2))
    B("Las empresas, los gremios y los congresistas deciden en un entorno donde el Estado produce más señales de las que un "
      "equipo humano puede leer. En Colombia operan más de doscientas entidades con capacidad regulatoria, que "
      "emiten decenas de documentos al día; a eso se suma un Congreso que radica cientos de proyectos por "
      "legislatura, de los cuales apenas una fracción mínima llega a convertirse en ley. Seguir todo eso a mano "
      "es imposible, y seguirlo mal es costoso: una norma que pasa desapercibida puede cambiarle las reglas del "
      "juego a un sector entero.")
    SP(2)
    E.append(stat_strip([("200+", "entidades con capacidad de emitir normas"),
                         ("~5", "documentos regulatorios al día, por entidad"),
                         ("0,1%", "de los proyectos de ley llegan a ser ley")]))
    SP(10)
    B("El mercado ya reaccionó a esa necesidad. Existen plataformas conocidas que prometen resolverlo con tableros, "
      "alertas automáticas e inteligencia artificial. Tienen marca, clientes grandes y visibilidad. Pero su promesa "
      "tiene una grieta, y es justo ahí donde está nuestra oportunidad.")
    SP(3)
    E.append(callout(
        "Cuando una organización abandona una de estas plataformas no está rechazando el monitoreo: está rechazando el "
        "ruido. Recibe un volumen de alertas que no alcanza a leer, sin la precisión ni el análisis que exige una "
        "decisión. Se paga por cobertura y se cancela por falta de criterio.", "LA RAZÓN DE FONDO"))
    SP(12)
    B("Ese es el hueco del mercado, y es un hueco de <b>calidad, no de cantidad</b>. No se cierra con más fuentes "
      "ni con más automatización. Se cierra con criterio: la capacidad de decir qué importa, por qué le importa a "
      "ese cliente en particular, y qué debería hacer al respecto. Ese es exactamente el terreno donde tenemos "
      "ventaja demostrada.")
    # ===== 02 =====
    E.append(Paragraph("02", st_secnum))
    E.append(Paragraph("La tesis: precisión sobre volumen", st_h2))
    B("Nuestra plataforma parte de una convicción opuesta a la de los incumbentes: el objetivo no es acumular la "
      "mayor cantidad de información posible, sino entregar la información <b>correcta</b>, ya interpretada. Un "
      "organización no necesita mil alertas al día; necesita las tres que cambian su juego, explicadas. Todo el diseño "
      "del producto se ordena alrededor de esa idea, como un embudo que convierte volumen en criterio:")
    SP(6)
    E.append(funnel_drawing())
    E.append(Paragraph("El producto no compite por cuántas señales captura, sino por cuántas descarta bien.", st_cap))
    SP(10)
    B("No incorporamos inteligencia artificial como argumento de venta. La usamos donde agrega valor real —filtrar "
      "por relevancia, resumir con fidelidad, rastrear un trámite— y siempre con <b>trazabilidad</b>: cada alerta "
      "cita su fuente oficial. El diferencial de fondo es la <b>capacidad analítica</b>: los competidores entregan "
      "el dato; nosotros lo interpretamos. Es la misma capacidad que hemos demostrado en cada herramienta que hemos "
      "construido, donde el dato no se muestra, se lee.")
    # ===== 03 FUENTES =====
    E.append(Paragraph("03", st_secnum))
    E.append(Paragraph("El motor y sus fuentes: volumen con criterio", st_h2))
    B("La pregunta obligada es cuántas fuentes cubrimos, porque es la métrica con la que los incumbentes buscan "
      "impresionar. La respuesta corta: <b>más de 600 en el mapa inicial</b>, y el techo es mayor. Absorbemos "
      "desde el Congreso y la Gaceta hasta las superintendencias, las altas cortes, los diarios oficiales, los "
      "medios nacionales y regionales, las redes sociales de las entidades y las plataformas de datos abiertos "
      "y contratación del Estado. Y ese conteo es conservador: una sola de esas puertas —el portal de datos "
      "abiertos— reúne a su vez miles de conjuntos de datos de cientos de entidades, así que cada barra del "
      "mapa esconde, por dentro, muchas más fuentes.")
    SP(4)
    E.append(sources_bar_drawing())
    E.append(Paragraph("Mapa inicial de fuentes por categoría. Escalable; el número crece con cada cliente y sector.", st_cap))
    SP(10)
    B("Pero el número, por sí solo, es la métrica equivocada. Mil fuentes sin jerarquía son mil maneras de perderse; "
      "seiscientas bien mapeadas y filtradas por el tema de cada cliente son una ventaja. <b>El volumen lo tenemos; "
      "lo que los demás no tienen es el criterio para ordenarlo.</b> Sabemos cuál de esas seiscientas fuentes le "
      "importa a una empresa de salud, a un gremio de energía o a un congresista de la Comisión Quinta, y descartamos "
      "el resto antes de que llegue a su bandeja.")
    # ===== 04 IA =====
    E.append(Paragraph("04", st_secnum))
    E.append(Paragraph("La inteligencia artificial: de frontera y con criterio", st_h2))
    B("Toda plataforma de este tipo dice usar inteligencia artificial. La diferencia no está en tenerla, sino en "
      "qué modelo se usa, cómo se controla y quién entiende lo que hace. Los incumbentes operan con modelos propios, "
      "entrenados sobre un corpus fijo y presentados como caja negra. Ese enfoque envejece —un modelo entrenado hoy "
      "no mejora solo—, es opaco y es caro de mantener al día.")
    B("Esa opacidad no es un detalle técnico: es un riesgo para el cliente. Un modelo de caja negra puede sonar "
      "convincente y estar equivocado, y nadie —ni siquiera quien lo vende— sabría distinguirlo. Cuando lo que está "
      "en juego es una decisión regulatoria o una jugada legislativa, adivinar bien no basta; hace falta poder "
      "rastrear de dónde salió cada afirmación.")
    B("Nuestra apuesta es la contraria: orquestamos los <b>modelos de frontera</b> del mercado —Claude, de Anthropic, "
      "y DeepSeek— con tres controles que garantizan que la IA sume y no invente. Así se ve la cadena completa, de la "
      "fuente a la alerta:")
    SP(6)
    E.append(arch_drawing())
    SP(10)
    for t in [
        "<b>Function calling estricto</b> — el modelo solo responde a partir de datos que consulta en nuestro índice de fuentes. No improvisa cifras ni cita de memoria.",
        "<b>Trazabilidad total</b> — cada alerta cita la norma o el documento oficial de donde sale. Cero alucinación.",
        "<b>La IA asiste, no decide</b> — filtra, resume y rastrea a escala; el criterio final lo pone el analista.",
    ]:
        E.append(Paragraph(t, st_bull, bulletText="•"))
    SP(6)
    B("Ventaja estructural: los modelos de frontera mejoran cada trimestre sin que tengamos que reentrenar nada, y "
      "podemos elegir el mejor para cada tarea según costo y calidad. No dependemos de un modelo congelado que su "
      "propio dueño no sabe explicar.")
    B("A esa base le sumamos una rutina que casi nadie tiene: <b>cada quince días recalibramos el sistema</b> —qué "
      "temas pesan más, qué señales cambiaron de significado, qué supuestos dejaron de ser ciertos—. Es la "
      "diferencia entre una lectura viva y una congelada. Un modelo sin recalibrar puede sonar seguro y equivocarse "
      "feo: puede dar por segura la aprobación de una reforma que, semanas después, se cae por una movilización "
      "social que el modelo nunca vio venir. Nosotros ajustamos antes de que eso pase.")
    B("Y hay una parte que ninguna IA cubre: los documentos que aparecen <b>antes</b> de ser públicos —una "
      "radicación que todavía no se difunde, un texto que circula de mano en mano— no llegan por automatización, "
      "llegan por relacionamiento. Eso lo aporta Cauce, y siempre por vías legítimas: nunca vulneramos sitios ni "
      "forzamos accesos. La IA nos da alcance y velocidad sobre lo público; el criterio humano nos consigue lo que "
      "todavía no lo es.")
    # ===== 05 PLATAFORMA =====
    E.append(Paragraph("05", st_secnum))
    E.append(Paragraph("La plataforma: dos perfiles sobre un mismo motor", st_h2))
    B("El motor que acabamos de describir —fuentes, ingesta e IA— se construye una vez y alimenta dos productos "
      "afinados a dos compradores distintos. Encima del mismo dato, dos lecturas.")
    E.append(sku_box("SKU A", "Alertas de precisión para el sector privado y organizaciones", [
        ("Para quién", "Empresas y multinacionales, gremios, agencias de cooperación y consultorías especializadas por sector (salud, educación, jurídico). El sector privado y sus asesores."),
        ("Qué resuelve", "Seguimiento de los temas específicos que le importan a esa organización a lo largo de todo el Estado, filtrado por relevancia real."),
        ("Qué recibe", "Alertas priorizadas y, sobre todo, <b>interpretadas</b>: qué pasó, por qué importa para su sector y qué implica. El acompañamiento del analista de Cauce cierra el círculo."),
        ("Contra qué", "Los tableros que ya existen en el mercado. Entramos exactamente donde ellos pierden clientes: la precisión."),
    ], BRAND))
    E.append(sku_box("SKU B", "Inteligencia para el congresista y su equipo", [
        ("Qué resuelve", "El trabajo legislativo del senador o representante y su UTL: cómo vota su partido, cómo se mueven los intereses de su comisión, el estado de sus proyectos y dónde posicionarse."),
        ("Por qué importa", "La oferta actual le habla al corporativo que <b>vigila</b> al gobierno. Nadie construye la herramienta <b>para</b> el congresista. Es un espacio sin competencia frontal."),
    ], ACCENT))
    B("Y hacia adelante, un tercer perfil —<b>SKU C</b>— sobre el Plan Nacional de Desarrollo: cómo migran las metas "
      "de gobierno, qué entidad sube o baja presupuesto y cómo se traduce en contratación. Un ángulo estratégico que "
      "ningún monitor ofrece hoy.")

    # ===== 06 EJEMPLO =====
    E.append(Paragraph("06", st_secnum))
    E.append(Paragraph("Cómo se ve una alerta de precisión", st_h2))
    B("Un ejemplo vale más que una lista de funciones. Tomemos una empresa del sector salud. Un martes cualquiera, "
      "el Estado produce sobre su radar decenas de señales: una circular de la Superintendencia de Salud, tres "
      "proyectos radicados en la Comisión Séptima, una resolución del Ministerio, dos noticias regionales y el "
      "trino de un ponente. Un tablero tradicional se las manda todas como alertas y le deja al cliente la tarea "
      "de decidir cuáles importan. Nosotros hacemos lo contrario: filtramos, leemos y entregamos solo lo que mueve "
      "la aguja.")
    SP(4)
    E.append(stat_strip([("9", "señales sobre el radar ese martes"),
                         ("6", "descartadas por irrelevantes a esa empresa"),
                         ("2", "alertas que de verdad importan")]))
    SP(10)
    E.append(alert_cards())
    E.append(Paragraph("Ejemplo ilustrativo; las referencias normativas son hipotéticas.", st_cap))
    SP(8)
    B("La diferencia no es cosmética. No le entregamos nueve alertas para que el cliente haga el trabajo de "
      "leerlas; le entregamos las dos que importan, ya interpretadas, con la fuente citada y una acción sugerida. "
      "Eso es precisión, y es exactamente lo que un tablero genérico no puede dar.")
    B("Y esa lectura no sale de una plantilla igual para todos. Cada cliente parte del mismo motor de IA, pero "
      "recibe un <b>perfil especializado</b> —sus temas, sus actores, sus umbrales, su sector—. No es un tablero "
      "genérico. Un producto del mercado, en el mejor de los casos, le filtra fuentes y sitios según su sector; el "
      "consejo específico para su situación, más el acompañamiento humano que lo interpreta, no se lo da nadie. En "
      "la práctica, este producto todavía no existe.")

    # ===== 07 ASESOR =====
    E.append(Paragraph("07", st_secnum))
    E.append(Paragraph("El asesor especializado: criterio humano que cuida al cliente", st_h2))
    B("Ya explicamos cómo se produce una alerta de precisión. Falta la otra mitad del producto, la que ningún "
      "tablero tiene: el asesor especializado que acompaña al cliente. Conviene ser claro en algo —el cliente no "
      "pierde su tablero ni sus alertas; los tiene siempre, en vivo. Lo que ponemos encima es una capa humana que "
      "convierte el monitoreo en acompañamiento.")
    SP(6)
    E.append(humanloop_drawing())
    SP(12)
    E.append(Paragraph("Cómo cuida al cliente", st_h3))
    care = [
        ("Onboarding a la medida", "Al inicio definimos con el cliente sus temas, los actores que le importan y los umbrales que disparan una alerta. El filtro nace ajustado a su realidad."),
        ("Contacto proactivo", "Cuando algo de verdad importa, el asesor lo llama o le escribe: esto salió, esto significa para usted, esto le sugiero. No espera a que el cliente revise un tablero."),
        ("Lectura periódica", "Un resumen interpretado cada semana: qué pasó en su sector, qué vigilamos y qué viene. El cliente arranca informado, no reaccionando."),
        ("Soporte cuando lo necesita", "Si ve algo y quiere entenderlo, pregunta y el asesor responde. Hay un humano detrás, no solo un sistema."),
        ("Especialista en su sector", "El asesor conoce el terreno del cliente —salud, educación, energía, jurídico—. La lectura es de especialista, no genérica."),
    ]
    crows = []
    for i,(h,t) in enumerate(care,1):
        crows.append([Paragraph(str(i), S("cn", fontName=DISP, fontSize=14, textColor=BRAND, leading=16)),
                      [Paragraph(h, st_h3), Paragraph(t, st_body_l)]])
    ct = Table(crows, colWidths=[1.0*cm, USABLE-1.0*cm])
    ct.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(0,-1),0),("RIGHTPADDING",(0,0),(0,-1),6),("LEFTPADDING",(1,0),(1,-1),4),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),("LINEBELOW",(0,0),(-1,-2),0.5,LINE)]))
    E.append(ct)
    SP(8)
    B("Ese es el criterio humano en el proceso: la IA filtra y resume el volumen; el asesor decide qué escalar, cómo "
      "interpretarlo y qué recomendar. La máquina nunca toma sola las decisiones que importan. Por eso el cliente no "
      "cambia una herramienta por otra: gana un equipo.")

    # ===== 08 ESCALABILIDAD =====
    E.append(Paragraph("08", st_secnum))
    E.append(Paragraph("Cómo escala el modelo sin perder el criterio", st_h2))
    B("La pregunta natural es si un modelo con acompañamiento humano puede crecer. Sí, y por una razón concreta: la "
      "IA absorbe el volumen, así que un asesor cubre muchos más clientes sin perder profundidad, y la red de Cauce "
      "aporta el especialista por sector. Crecemos cliente a cliente y sector a sector, en tres niveles:")
    SP(10)
    E.append(stairs_drawing())
    SP(14)
    P2 = lambda t,s: Paragraph(t, s)
    tier = [
        [P2("Nivel 1 · Arranque", st_dif_h), P2("Tablero + alertas interpretadas + asesor compartido. Cobertura inmediata y sin fricción para el cliente que entra.", st_dif_b)],
        [P2("Nivel 2 · Dedicado", st_dif_h), P2("Asesor dedicado a la cuenta, resúmenes a la medida y más temas bajo vigilancia. Para el cliente que quiere profundidad.", st_dif_b)],
        [P2("Nivel 3 · Célula de sector", st_dif_h), P2("Un equipo por sector —salud, energía, educación, jurídico— con analista especialista, fuentes ampliadas e inteligencia comparada entre clientes del mismo vertical.", st_dif_b)],
    ]
    tt = Table(tier, colWidths=[4.7*cm, USABLE-4.7*cm])
    tt.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
        ("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9),
        ("LINEBELOW",(0,0),(-1,-2),0.5,LINE),("BACKGROUND",(0,0),(0,-1),BRAND_LT)]))
    E.append(tt)
    SP(8)
    B("Cada nivel suma criterio, no solo capacidad. Y como el motor de datos es el mismo, sumar un cliente o un "
      "sector nuevo no obliga a reconstruir nada: se afina el filtro y se asigna el especialista. Así el producto "
      "crece sin diluir lo que lo hace distinto.")

    # ===== 09 MATRIZ =====
    E.append(Paragraph("09", st_secnum))
    E.append(Paragraph("El mapa competitivo, dimensión por dimensión", st_h2))
    B("Competimos contra jugadores serios; conviene mirarlos de frente. Ninguno es débil en todo, pero ninguno "
      "reúne la combinación que proponemos, y todos comparten el mismo punto ciego: entregan información sin la "
      "lectura que la vuelve decisión.")
    B("Conviene describir a cada jugador, porque conocerlos es parte del pitch. <b>Dapper</b> es el líder: SaaS "
      "con IA propia y clientes grandes; su fuerza es la cobertura y la marca, su debilidad es que entrega volumen "
      "sin lectura y no tiene analista. <b>Sonar</b>, de Orza, apuesta por predecir si un proyecto se vuelve ley; "
      "es un ángulo potente, pero su data legislativa la toma de un tercero y solo cubre lo regulatorio. "
      "<b>Deloitte</b> y las grandes consultoras hacen vigilancia regulatoria dentro de servicios enterprise: "
      "caros, lentos y ajenos al lobby por conflicto de interés. La matriz los pone lado a lado:")
    SP(2); E.append(matrix()); SP(8)
    B("La conclusión estratégica: no entramos a imitar a nadie en su propia cancha. Entramos por donde los "
      "incumbentes son estructuralmente débiles —la precisión, el análisis y el acompañamiento humano— y por el "
      "comprador que nadie atiende: el congresista.")
    # ===== 07 POR QUE GANAMOS =====
    E.append(Paragraph("10", st_secnum))
    E.append(Paragraph("Por qué ganamos", st_h2))
    B("Más allá de los nombres del mercado, el producto se define por lo que el cliente realmente usa: información "
      "valiosa, interpretada, con respaldo humano. Es una pelea de posicionamiento, no de recursos. Los incumbentes "
      "son grandes y tienen acceso, pero su producto es operativo: acumula y entrega. El nuestro razona. Esa "
      "distancia no se cierra contratando más ingenieros; se cierra con criterio, y el criterio es nuestro punto de "
      "partida.")
    for t in [
        "<b>Precisión sobre volumen</b> — resolvemos el problema real del mercado, no el que el marketing dice tener.",
        "<b>Capacidad analítica, no operativa</b> — leemos el dato; los competidores solo lo entregan.",
        "<b>IA de frontera, no caja negra</b> — Claude y DeepSeek con fuente citada, no un modelo propietario congelado.",
        "<b>Humano + IA</b> — el analista de Cauce sobre el motor de datos. Ese matrimonio nadie lo tiene.",
        "<b>Data propia y trazable</b> — construimos la fuente desde el crudo; no dependemos de terceros.",
        "<b>El congresista</b> — el comprador que la oferta actual ignora por completo.",
    ]:
        E.append(Paragraph(t, st_bull, bulletText="•"))
    SP(8)
    B("Ninguna de estas piezas es exclusiva por separado; hay quien tiene datos, quien tiene IA y quien tiene "
      "analistas. Lo que nadie ha juntado es <b>las seis a la vez</b>, y esa combinación es difícil de copiar "
      "porque exige, al mismo tiempo, músculo de datos y criterio de asuntos públicos. Justo lo que esta alianza "
      "pone sobre la mesa.")
    # ===== 09 VENTANA =====
    E.append(Paragraph("11", st_secnum))
    E.append(Paragraph("Por qué ahora: la ventana", st_h2))
    B("El momento no es casual. Tres relojes se alinean en el segundo semestre de 2026, y cada uno abre demanda "
      "para una parte del producto:")
    PV = lambda t,s: Paragraph(t, s)
    ven = [
        [PV("20 de julio", st_dif_h), PV("Se instala el nuevo Congreso", st_dif_h),
         PV("Arranca una legislatura entera de proyectos por seguir. Enciende el SKU B y alimenta el SKU A.", st_dif_b)],
        [PV("7 de agosto", st_dif_h), PV("Se posesiona el nuevo gobierno", st_dif_h),
         PV("Reestructuración de entidades, nuevos ministros y nuevas agendas regulatorias que cada organización necesita leer a tiempo.", st_dif_b)],
        [PV("Tercer y cuarto trimestre", st_dif_h), PV("Se construye el Plan Nacional de Desarrollo", st_dif_h),
         PV("La hoja de ruta de cuatro años. Enciende el SKU C: hacia dónde migran las metas y el presupuesto.", st_dif_b)],
    ]
    vt = Table(ven, colWidths=[3.3*cm, 4.3*cm, USABLE-3.3*cm-4.3*cm])
    vt.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
        ("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9),
        ("LINEBELOW",(0,0),(-1,-2),0.5,LINE),("BACKGROUND",(0,0),(0,-1),BRAND_LT)]))
    E.append(vt)
    SP(8)
    B("Quien tenga la herramienta lista antes de que estos relojes marquen la hora, lee la transición en vivo; "
      "quien llegue después, la lee en los periódicos. La charla del 23 de julio cae justo en el arranque de esa "
      "ventana.")

    # ===== 10 CHARLA =====
    E.append(Paragraph("12", st_secnum))
    E.append(Paragraph("Puntos de partida para la charla del 23 de julio", st_h2))
    B("Seis ideas para abrir la conversación con los primeros clientes. El objetivo no es describir el producto, "
      "sino que el cliente sienta que por fin alguien entiende su frustración.")
    pts = [
        ("Abre por el dolor, no por el producto.",
         "Arranca preguntando: de las alertas que le llegaron esta semana, cuántas abrió y cuántas le sirvieron para decidir algo. El diagnóstico lo pone el cliente solo."),
        ("Habla de la categoría, no de las marcas.",
         "Basta con referirse a los tableros que ya conocen; el cliente sabe cuáles son. Se critica el problema —el ruido, la falta de lectura—, nunca a un competidor por su nombre."),
        ("Muestra una lectura, no una lista.",
         "Un solo ejemplo real donde el análisis cambia la decisión vale más que cualquier demo de funciones. Llévalo preparado."),
        ("Reencuadra la IA.",
         "No es otro tablero con IA. Es criterio asistido por modelos de frontera, con fuente citada y un analista que responde. La IA escala el juicio; no lo reemplaza."),
        ("Cierra con el congresista.",
         "Es el producto que nadie más ofrece. Guarda esa carta para el final: abre una conversación que ninguna otra herramienta puede tener."),
        ("Pide el piloto.",
         "Propón arrancar con un cliente que ya se cansó del ruido. No vendes una promesa: ofreces resolver una frustración que el cliente ya tiene."),
    ]
    rows = []
    for i,(h,t) in enumerate(pts, 1):
        rows.append([Paragraph(str(i), S("n", fontName=DISP, fontSize=15, textColor=BRAND, leading=17)),
                     [Paragraph(h, st_h3), Paragraph(t, st_body_l)]])
    pt = Table(rows, colWidths=[1.0*cm, USABLE-1.0*cm])
    pt.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(0,-1),0),("RIGHTPADDING",(0,0),(0,-1),6),("LEFTPADDING",(1,0),(1,-1),4),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),("LINEBELOW",(0,0),(-1,-2),0.5,LINE)]))
    E.append(pt)
    # ===== 11 RUTA =====
    E.append(Paragraph("13", st_secnum))
    E.append(Paragraph("Hoja de ruta y próximos pasos", st_h2))
    P = lambda t,s: Paragraph(t, s)
    ruta = [
        [P("Fase 1", st_dif_h), P("Ahora — charla del 23 de julio", st_dif_h),
         P("Definir y demostrar el diferencial de SKU A y SKU B ante los primeros clientes. El objetivo de la charla: que quede claro que el producto es de otra categoría.", st_dif_b)],
        [P("Fase 2", st_dif_h), P("Piloto", st_dif_h),
         P("Arrancar con un cliente ancla de la red de Cauce, idealmente uno que ya haya dejado un tablero por falta de precisión. El cliente insatisfecho es nuestro mejor mercado.", st_dif_b)],
        [P("Fase 3", st_dif_h), P("Tercer y cuarto trimestre", st_dif_h),
         P("Encender el SKU C sobre el Plan Nacional de Desarrollo: cómo migran las metas, qué entidad sube o baja presupuesto, cómo se traduce en contratación.", st_dif_b)],
    ]
    rt = Table(ruta, colWidths=[2.0*cm, 4.0*cm, USABLE-6.0*cm])
    rt.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
        ("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9),
        ("LINEBELOW",(0,0),(-1,-2),0.5,LINE),("BACKGROUND",(0,0),(1,-1),BRAND_LT)]))
    E.append(rt)
    SP(14)
    E.append(Paragraph("Pendientes por definir juntos", st_h3))
    B("Alcance y cliente del piloto  ·  modelo comercial y reparto de la alianza  ·  metas de crecimiento por sector  ·  "
      "acceso a una demo de las plataformas actuales para mapear con precisión sus vacíos.")
    SP(16); E.append(HRule(USABLE, BRAND, 1.4)); SP(10)
    E.append(Paragraph("Navegar la complejidad no es ver más datos. Es leerlos mejor.",
                       S("close", fontName=DISP, fontSize=16, textColor=BRAND, leading=20, alignment=TA_LEFT)))

    doc.build(E)
    print("OK ->", OUT)


if __name__ == "__main__":
    build()
