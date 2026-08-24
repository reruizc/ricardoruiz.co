#!/usr/bin/env python3
"""
Carta abierta al rector de la UNAL + Anexo (hoja de ruta) — Laboratorio de
Nuevos Liderazgos. Membretados con la identidad Ricardo.Ruiz, fechados
27 de julio de 2026.

Salida:
  Propuestas/carta-unal/Carta-Abierta-Rector-UNAL.pdf
  Propuestas/carta-unal/Anexo-Hoja-de-Ruta-LNL.pdf          (interno, con fechas)
  Propuestas/carta-unal/Anexo-Hoja-de-Ruta-LNL-Publica.pdf  (público, por fases)
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

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = "/Users/ricardoruiz/ricardoruiz.co/Propuestas/carta-unal"
FECHA = "27 de julio de 2026"

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

# Syne 800 (logo de marca) — reusa el TTF ya usado en la cotización de campaña
SYNE_TTF = "/Users/ricardoruiz/ricardoruiz.co/tools/build-cotizacion-campana/fonts/Syne-ExtraBold.ttf"
try:
    pdfmetrics.registerFont(TTFont("Syne", SYNE_TTF))
    SYNE = "Syne"
except Exception:
    SYNE = BOLD

W, H = A4
MX = 20 * mm
CW = W - 2 * MX

ss = getSampleStyleSheet()
def S(name, **kw):
    base = dict(fontName=BASE, fontSize=10.2, leading=15.2, textColor=INK,
                alignment=TA_JUSTIFY, spaceAfter=8)
    base.update(kw)
    return ParagraphStyle(name, parent=ss["Normal"], **base)

st_kick = S("kick", fontName=BOLD, fontSize=8.2, leading=11, textColor=BLUE,
            alignment=TA_LEFT, spaceAfter=4)
st_h1   = S("h1", fontName=BOLD, fontSize=17, leading=20.5, textColor=INK,
            alignment=TA_LEFT, spaceAfter=3)
st_sub  = S("sub", fontName=BASE, fontSize=9.6, leading=13, textColor=SOFT,
            alignment=TA_LEFT, spaceAfter=2)
st_ital = S("ital", fontName=ITAL, fontSize=9.4, leading=13.4, textColor=SOFT,
            alignment=TA_LEFT, spaceAfter=10)
st_sec  = S("sec", fontName=BOLD, fontSize=11.6, leading=14.5, textColor=BLUE_D,
            alignment=TA_LEFT, spaceBefore=13, spaceAfter=6)
st_body = S("body")
st_body_last = S("body_last", spaceAfter=0)
st_sig  = S("sig", spaceAfter=1, alignment=TA_LEFT)
st_num  = S("num", leftIndent=12, spaceAfter=5, alignment=TA_LEFT, leading=14.5)
st_cell = S("cell", fontSize=7.7, leading=10.6, alignment=TA_LEFT, spaceAfter=0)
st_cellb = S("cellb", fontName=BOLD, fontSize=7.9, leading=10.8, textColor=colors.white,
             alignment=TA_LEFT, spaceAfter=0)
st_cell_date = S("cell_date", fontName=BOLD, fontSize=7.7, leading=10.6,
                  textColor=BLUE_D, alignment=TA_LEFT, spaceAfter=0)


def make_header(doctype):
    def header(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(INK)
        canvas.rect(0, H - 22 * mm, W, 22 * mm, stroke=0, fill=1)
        y = H - 12.8 * mm
        bw, bg = 3.6, 2.2
        bx = MX
        canvas.setFillColor(BLUE)
        canvas.setFillAlpha(0.9)
        for hh in (13.5, 10.5, 6.75, 3.75):
            canvas.roundRect(bx, y, bw, hh, 0.6, stroke=0, fill=1)
            bx += bw + bg
        canvas.setFillAlpha(1)
        barsW = 4 * bw + 3 * bg
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
        canvas.drawString(MX, H - 18.2 * mm, "ricardoruiz.co")
        canvas.setFont(BOLD, 8.6)
        canvas.setFillColor(colors.white)
        canvas.drawRightString(W - MX, y, doctype)
        canvas.setFont(BASE, 7.4)
        canvas.setFillColor(colors.HexColor("#a9b0c8"))
        canvas.drawRightString(W - MX, H - 18 * mm, FECHA)
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.6)
        canvas.line(MX, 12.5 * mm, W - MX, 12.5 * mm)
        canvas.setFont(BASE, 7)
        canvas.setFillColor(META)
        canvas.drawString(MX, 9 * mm, "Ricardo Esteban Ruiz  ·  Egresado UNAL  ·  hola@ricardoruiz.co")
        canvas.drawCentredString(W / 2, 9 * mm, "Universidad Nacional de Colombia")
        canvas.drawRightString(W - MX, 9 * mm, f"Página {doc.page}")
        canvas.restoreState()
    return header


def new_doc(path, doctype):
    doc = BaseDocTemplate(path, pagesize=A4, leftMargin=MX, rightMargin=MX,
                          topMargin=27 * mm, bottomMargin=15 * mm)
    frame = Frame(MX, 14 * mm, CW, H - 27 * mm - 14 * mm, id="f")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=make_header(doctype))])
    return doc


# =============================================================================
# PDF 1 — Carta abierta
# =============================================================================
def build_carta():
    out = f"{OUTDIR}/Carta-Abierta-Rector-UNAL.pdf"
    doc = new_doc(out, "CARTA ABIERTA")
    s = []

    s.append(Paragraph("PROPUESTA · UNIVERSIDAD NACIONAL DE COLOMBIA", st_kick))
    s.append(Paragraph("Carta abierta al rector de la Universidad Nacional "
                       "de Colombia, José Ismael Peña", st_h1))
    s.append(Paragraph(f"Bogotá D.C., {FECHA}", st_sub))
    s.append(Spacer(1, 12))

    s.append(Paragraph(
        "Señor rector, estimada comunidad de la Universidad Nacional "
        "—egresados, profesores y estudiantes—:",
        st_body))

    s.append(Paragraph(
        "Dirigir la universidad más importante del país y una de las "
        "mejores de América Latina no se improvisa. Se necesita pensar a "
        "largo plazo y ser capaz de mantener el liderazgo. Esto es la "
        "Universidad Nacional de Colombia.", st_body))

    s.append(Paragraph(
        "En la última década, nos hemos transformado: la séptima "
        "universidad de América Latina y la primera pública de Colombia, "
        "con 39 programas en el ranking mundial, más de 50 mil estudiantes "
        "y siendo la organización más atractiva para trabajar entre los "
        "universitarios del país. Pero, sobre todo, somos la universidad a "
        "la que se entra por la cabeza y no por el apellido: el 86% de "
        "quienes estudian aquí vienen de estratos 1, 2 y 3. Esa es nuestra "
        "grandeza. Aun así, el mundo cambia cada día y el liderazgo no se "
        "puede dar por hecho. Debemos seguir trabajando todos los días.",
        st_body))

    s.append(Paragraph(
        "El mejor ciclo de liderazgo de la Nacional aún no ha terminado: "
        "miles de líderes, empresarios y políticos —entre ellos seis "
        "presidentes de la República, decenas de ministros y generaciones "
        "enteras de científicos y maestros— son el listón para todo lo que "
        "viene. Nuevos descubrimientos que hoy parecen fuera de nuestro "
        "alcance, pero que volveremos a conquistar juntos. Desde Eduardo "
        "Santos hasta Lena Estrada, ninguno llegó solo. Fueron el "
        "resultado de una visión y una determinación que no podemos "
        "perder. La llegada de los mejores talentos del país y la región "
        "a nuestras aulas no será un sueño: seguirá siendo un hecho.",
        st_body))

    s.append(Paragraph(
        "El nuevo Edificio Nuevos Espacios para las Artes es una de las "
        "apuestas de infraestructura pública más ambiciosas del país. La "
        "demostración de que esta universidad piensa en décadas, no en "
        "gobiernos. Cada piedra de la segunda fase de ese edificio lleva "
        "grabado el mismo compromiso: construir el mejor entorno para "
        "formar y para pensar el país.", st_body))

    s.append(Paragraph(
        "La grandeza de la UNAL no se mide solo en nombramientos e "
        "investigaciones: se mide en los niños del IPARM que aprenden, en "
        "los miles de estudiantes de pregrado y posgrado que forma. El "
        "mismo campus en el que se hace ciencia de primer nivel también "
        "enseña a pensar con criterio y a vivir con valores. Eso es el "
        "IPARM, eso es la universidad, eso somos nosotros.", st_body))

    s.append(Paragraph(
        "Seguir siendo la mejor universidad pública del país implica "
        "trabajar constantemente en gestión, en tecnología, en "
        "investigación. Cada año sin pausa, mientras otros se observan. "
        "Nosotros estamos creando nuevas formas de poner el conocimiento "
        "público al servicio del país: en inteligencia artificial y "
        "análisis de datos, aplicados tanto a la política pública como al "
        "sector privado.", st_body))

    s.append(Paragraph(
        "Por eso, en esta carta le proponemos crear el "
        "<b>Laboratorio de Nuevos Liderazgos</b>: un espacio transversal "
        "a todas las facultades que lleve la tecnología, la inteligencia "
        "artificial y el análisis de datos al corazón de las ciencias "
        "humanas y sociales. Un lugar donde nuestros estudiantes se midan "
        "con los desafíos reales de las organizaciones públicas y "
        "privadas del país: que aprendan a definir problemas reales, a "
        "plantear alternativas, a diseñar soluciones y a evaluar lo que "
        "ya se está haciendo. Y que ese talento no se quede en el aula: "
        "que alimente al Estado, a las empresas y a las corporaciones de "
        "innovación que la propia universidad ya ha creado, para que el "
        "conocimiento que producimos vuelva al país convertido en "
        "soluciones, y a la universidad convertido en oportunidades.",
        st_body))

    s.append(Paragraph(
        "No escribo esta carta solo. Somos varios —egresados y "
        "profesionales de distintas áreas— los que queremos poner tiempo "
        "y experiencia al servicio de enseñar en este laboratorio; la "
        "propuesta nace de ese grupo y del deseo de devolverle a la "
        "universidad algo de lo que nos dio.", st_body))

    s.append(Paragraph(
        "La UNAL no pertenece a ningún gobierno: pertenece a sus egresados, "
        "a sus profesores y a sus estudiantes, a los que desde niños "
        "lloran y ríen en las mismas aulas. La Universidad siempre fue "
        "suya y siempre lo será, porque la grandeza no se improvisa ni se "
        "hereda: se gana — y la mejor universidad del país no se detiene.",
        st_body_last))

    s.append(Spacer(1, 16))
    s.append(Paragraph("—", st_sig))
    s.append(Paragraph("<b>Ricardo Esteban Ruiz</b>", st_sig))
    s.append(Paragraph("Egresado de la Universidad Nacional de Colombia",
                       st_sub))

    doc.build(s)
    return out, os.path.getsize(out)


# =============================================================================
# PDF 2 — Anexo · Hoja de ruta
# =============================================================================
def sec(num, title):
    return Paragraph(f"{num}. {title}", st_sec)


def numbered(n, txt):
    return Paragraph(f'<font color="#0047FF"><b>{n}.</b></font>&nbsp;&nbsp;{txt}',
                     st_num)


def build_anexo(publico=False):
    if publico:
        out = f"{OUTDIR}/Anexo-Hoja-de-Ruta-LNL-Publica.pdf"
        doc = new_doc(out, "ANEXO · HOJA DE RUTA")
    else:
        out = f"{OUTDIR}/Anexo-Hoja-de-Ruta-LNL.pdf"
        doc = new_doc(out, "ANEXO · HOJA DE RUTA")
    s = []

    s.append(Paragraph("ANEXO A LA CARTA ABIERTA · UNIVERSIDAD NACIONAL DE "
                       "COLOMBIA", st_kick))
    s.append(Paragraph("Hoja de ruta — Laboratorio de Nuevos Liderazgos "
                       "(LNL)", st_h1))
    if publico:
        s.append(Paragraph(
            "Versión pública de la hoja de ruta que acompaña la carta "
            "abierta al rector, organizada por fases en lugar de fechas "
            "internas de trámite.", st_ital))
    else:
        s.append(Paragraph(
            "Documento de respaldo a la carta abierta al rector. Detalla el "
            "qué, el cómo, los tiempos y lo que se solicita para poner en "
            "marcha la propuesta.", st_ital))
    s.append(Paragraph(f"Bogotá D.C., {FECHA}", st_sub))
    s.append(Spacer(1, 10))

    # 1
    s.append(sec(1, "Qué es y por qué ahora"))
    s1_criterio = (
        "El LNL forma, desde la Universidad Nacional, el criterio para "
        "tomar decisiones complejas: esas que dependen de muchas "
        "variables a la vez y rara vez tienen una respuesta obvia. Ese "
        "criterio se construye en dos capas —la formación humanística y "
        "académica que ya da la universidad, y el manejo de herramientas "
        "de inteligencia artificial e innovación que hoy casi ningún "
        "programa enseña. No es un curso más de estadística ni un "
        "diplomado en IA: es un lugar donde estudiantes de cualquier "
        "facultad enfrentan un problema real —con datos, con método y con "
        "alguien del otro lado esperando resultados— y practican esa "
        "doble capa con un caso concreto, público o privado según el reto "
        "que llegue ese semestre.")
    if publico:
        s1_criterio += (
            " Y como ese trabajo siempre ocurre en equipo, con un cliente "
            "real y una fecha encima, en el camino se forjan las "
            "habilidades que ninguna materia entrega por separado: "
            "comunicar con claridad, colaborar, negociar y sostener el "
            "rumbo cuando el problema todavía está mal definido.")
    s.append(Paragraph(s1_criterio, st_body))
    if publico:
        s.append(Paragraph(
            "La oportunidad tiene urgencia. Si el aval llega pronto, la "
            "cohorte piloto arranca en la Fase 2 de este mismo ciclo y "
            "presenta resultados al cierre de la Fase 4. Esperar más de "
            "lo necesario significa perder el momentum del semestre en "
            "curso y arrancar en el siguiente.", st_body))
    else:
        s.append(Paragraph(
            "La oportunidad tiene fecha. Si el aval llega en las próximas "
            "semanas, la primera cohorte queda seleccionada antes de que "
            "arranque a fondo el semestre 2026-II y presenta resultados en "
            "enero de 2027. Esperar a un “segundo semestre” "
            "indefinido significa perder el ciclo completo y arrancar recién "
            "en 2027-I.", st_body))

    # 2
    s.append(sec(2, "Lo que conecta"))
    s.append(Paragraph(
        "A un lado están los estudiantes, sobre todo de ciencias humanas "
        "y sociales: llegan con criterio y capacidad de análisis, y salen "
        "sin haber tocado casi nada de esto —uso ético de la inteligencia "
        "artificial, automatización de flujos de trabajo, investigación "
        "asistida por IA, o cómo convertir un análisis en un producto que "
        "una empresa pueda usar. No es que no puedan aprenderlo. Es que "
        "nadie se los está enseñando dentro de su propia carrera.",
        st_body))
    s.append(Paragraph(
        "Al otro lado están los gremios y las empresas. Necesitan gente "
        "joven a la que puedan formar durante un año sin que eso sea un "
        "lujo, pero que llegue ya sabiendo integrar IA en procesos "
        "reales, no solo usarla como buscador. Es un perfil que hoy "
        "escasea en el mercado colombiano, y las empresas lo están "
        "buscando activamente.", st_body))
    if publico:
        s.append(Paragraph(
            "Y lo que más les cuesta encontrar no es la destreza técnica "
            "sola. Un analista que no sabe explicarle un hallazgo a quien "
            "decide, que no aguanta el trabajo en equipo o que se "
            "paraliza ante un problema mal planteado, no rinde por bueno "
            "que sea con las herramientas. Esas habilidades blandas "
            "—comunicar, colaborar, negociar, presentarle a alguien que "
            "va a tomar una decisión con lo que uno le diga— se ganan "
            "haciendo, y el laboratorio las cultiva a la fuerza: cada "
            "cohorte defiende su trabajo ante la entidad que lo pidió, "
            "con gente esperando y un plazo que no se mueve.", st_body))
    s.append(Paragraph(
        "El laboratorio es el puente entre esas dos orillas. A la "
        "universidad le da ocupación productiva para sus estudiantes y "
        "visibilidad frente al sector empresarial. A los gremios les da "
        "talento entrenado antes de que la competencia llegue a él. Y al "
        "estudiante le da una ventaja de entrada al mercado laboral, en "
        "un momento de la vida en que tener algo qué hacer —y un ingreso "
        "propio— cambia una trayectoria. Tres beneficios distintos, "
        "verificables cada uno por separado: ese es el argumento que "
        "conviene llevar a la reunión.", st_body))

    # 3
    s.append(sec(3, "Un frente que la Nacional puede ocupar primero"))
    s.append(Paragraph(
        "Hay algo más que gana la universidad, y que gana el estudiante, "
        "que todavía no está en este documento: un marco propio de uso "
        "responsable de inteligencia artificial —ético, ambiental y de "
        "uso académico— que sirva tanto puertas adentro como en el sector "
        "público y privado donde los egresados van a trabajar. Hoy "
        "ninguna universidad colombiana lo ha fijado con claridad.",
        st_body))
    s.append(Paragraph(
        "Lo ético cubre lo esperable: sesgo, transparencia, qué decisión "
        "no se le puede delegar a un modelo. Lo ambiental es lo que casi "
        "nadie está midiendo todavía —cada consulta a un modelo grande "
        "consume energía, y hay una diferencia real entre usar el más "
        "pesado para una tarea trivial o el más liviano para lo que de "
        "verdad lo necesita. Y lo académico es el que más urge puertas "
        "adentro: hoy no hay una postura clara sobre cómo un estudiante "
        "puede apoyarse en IA para investigar sin que eso reemplace el "
        "pensamiento propio, y esa falta de postura ya genera confusión "
        "real en las aulas.", st_body))
    s.append(Paragraph(
        "Publicar ese marco no depende de que la primera cohorte se "
        "gradúe, ni de que un convenio externo esté firmado. Puede salir "
        "antes que cualquier otro producto del laboratorio, y es, en sí "
        "mismo, el segundo entregable ancla del primer año —ver el "
        "punto 8.", st_body))

    # 4
    s.append(sec(4, "Principio rector"))
    s.append(Paragraph(
        "Transversal, no una facultad más. Es cierto que convoca a "
        "estudiantes de pregrado y posgrado de cualquier carrera, a "
        "egresados y profesores —pero el impulso no sale solo de ahí "
        "adentro. Depende igual de los retos y los recursos que traiga el "
        "sector privado, y de lo que la propia universidad decida poner "
        "sobre la mesa: espacio, coordinación, presupuesto semilla. Si el "
        "laboratorio se piensa solo como una convocatoria de estudiantes, "
        "sin ese motor externo, o si queda anclado en una sola facultad, "
        "deja de ser lo que promete ser.", st_body))

    # 5
    s.append(sec(5, "El método"))
    s.append(Paragraph(
        "Cada reto recorre la misma disciplina, así cambie el cliente: "
        "entender el problema con datos y no con intuición, plantear "
        "alternativas reales en vez de una sola salida obvia, decidir con "
        "un criterio explícito, medir después si funcionó. Cuando el "
        "reto viene del sector público, esa disciplina toma la forma que "
        "ya usan los laboratorios de política pública serios —de la "
        "tradición de Bardach a la práctica de CEPAL—, que es donde el "
        "equipo fundador tiene más trayectoria y por eso es el primer "
        "track en arrancar. Cuando el reto viene de una empresa o un "
        "gremio, la lógica de fondo es la misma; cambian el vocabulario y "
        "el tipo de entregable. La política pública es un track del "
        "laboratorio, no todo el laboratorio.", st_body))

    # 6 — cronograma / fases
    def hcell(t):
        return Paragraph(t, st_cellb)
    def dcell(t, date=False):
        return Paragraph(t, st_cell_date if date else st_cell)

    if publico:
        s.append(sec(6, "Fases de implementación"))
        s.append(Paragraph(
            "El plan avanza en cinco fases. No lleva fechas de trámite "
            "interno —esas se acuerdan con la Rectoría— sino la "
            "secuencia lógica de cómo el laboratorio pasa de propuesta "
            "a práctica sostenida:", st_body))
        crono_rows = [
            [hcell("Fase"), hcell("Qué pasa"), hcell("Qué queda")],
            [dcell("Fase 1 — Aval y convocatoria", True),
             dcell("Presentación de la propuesta a la Rectoría, trámite "
                   "institucional (aval, anclaje en una vicerrectoría, "
                   "comité académico) y convocatoria abierta —no solo a "
                   "estudiantes: también a gremios, empresas y una "
                   "eventual universidad aliada"),
             dcell("El laboratorio deja de ser una propuesta y pasa a "
                   "ser un espacio con nombre, comité y convocatoria "
                   "activa")],
            [dcell("Fase 2 — Selección y marco de IA", True),
             dcell("Selección de la cohorte piloto (30–40 estudiantes), "
                   "construcción y publicación del marco de uso "
                   "responsable de IA —ético, ambiental, académico— y "
                   "primeras conversaciones con las entidades y empresas "
                   "interesadas"),
             dcell("Cohorte confirmada y primer producto público del "
                   "laboratorio ya circulando")],
            [dcell("Fase 3 — Trabajo de campo", True),
             dcell("La cohorte trabaja los retos reales —de una entidad "
                   "pública y, si el gremio lo trae a tiempo, también de "
                   "una empresa—, con entregas parciales periódicas"),
             dcell("Avance verificable, no solo un producto al final")],
            [dcell("Fase 4 — Entrega y Demo Day", True),
             dcell("Entrega de los documentos de política, publicación "
                   "del tablero de datos abierto y Demo Day: la cohorte "
                   "presenta junto a sus aliados públicos y, si se "
                   "concretaron, privados"),
             dcell("Productos concretos, públicos y citables; para "
                   "varios estudiantes, la primera conversación seria de "
                   "contratación")],
            [dcell("Fase 5 — Consolidación", True),
             dcell("Segunda cohorte, más convenios, alianza "
                   "universitaria si se concreta, proyectos que escalan "
                   "vía las corporaciones de innovación de la "
                   "universidad"),
             dcell("El laboratorio deja de ser un piloto y se vuelve una "
                   "práctica sostenida")],
        ]
        crono_widths = [34 * mm, CW * 0.38, CW - 34 * mm - CW * 0.38]
    else:
        s.append(sec(6, "Cronograma — de la presentación a la convocatoria "
                        "abierta"))
        s.append(Paragraph(
            "La carta se presenta hoy, lunes 27 de julio. Lo que sigue "
            "asume que el trámite institucional toma su tiempo —tres "
            "semanas, no una— y fija la primera meta visible el 17 de "
            "agosto:", st_body))
        crono_rows = [
            [hcell("Fecha"), hcell("Qué pasa"), hcell("Qué queda")],
            [dcell("Lun 27 jul", True),
             dcell("Presentación de la carta y esta hoja de ruta a la "
                   "Rectoría"),
             dcell("El rector y su equipo tienen el documento completo sobre "
                   "la mesa")],
            [dcell("28 jul – 16 ago", True),
             dcell("Trámite institucional: aval, anclaje en una "
                   "vicerrectoría, primer llamado a profesores para el "
                   "comité académico"),
             dcell("Decisión formal de crear el LNL")],
            [dcell("17 ago (meta)", True),
             dcell("Convocatoria abierta —no solo a estudiantes: también a "
                   "gremios y empresas que quieran traer un reto, y a una "
                   "eventual universidad aliada"),
             dcell("El laboratorio deja de ser una propuesta y pasa a ser un "
                   "espacio con nombre y tres puertas abiertas: academia, "
                   "sector público y sector privado")],
            [dcell("Agosto (resto)", True),
             dcell("Selección de la cohorte piloto (30–40 estudiantes) y "
                   "primeras conversaciones con las entidades y empresas "
                   "interesadas"),
             dcell("Cohorte confirmada, convenios en negociación con al "
                   "menos un aliado público")],
            [dcell("Sep–oct", True),
             dcell("Construcción y publicación del marco de uso responsable "
                   "de IA —ético, ambiental, académico—, con el comité "
                   "académico"),
             dcell("Primer producto público del laboratorio, antes de que "
                   "termine el semestre")],
            [dcell("Sep–nov", True),
             dcell("La cohorte trabaja retos reales —de una entidad pública "
                   "y, si el gremio lo trae a tiempo, también de una "
                   "empresa—, con entregas parciales cada tres semanas"),
             dcell("Avance verificable, no solo un producto al final")],
            [dcell("Diciembre", True),
             dcell("Entrega de los documentos de política y publicación del "
                   "tablero de datos abierto"),
             dcell("Productos concretos, públicos y citables")],
            [dcell("Enero 2027", True),
             dcell("Demo Day: la cohorte presenta junto a sus aliados "
                   "públicos y, si se concretaron, privados"),
             dcell("Cierre con medios y, para varios estudiantes, la primera "
                   "conversación seria de contratación")],
            [dcell("2027-I en adelante", True),
             dcell("Segunda cohorte, más convenios, alianza universitaria si "
                   "se concreta, proyectos que escalan vía las corporaciones "
                   "de innovación"),
             dcell("Consolidación")],
        ]
        crono_widths = [26 * mm, CW * 0.40, CW - 26 * mm - CW * 0.40]
    ct = Table(crono_rows, colWidths=crono_widths, repeatRows=1)
    ct.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("BACKGROUND", (0, 1), (-1, -1), SHELL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [SHELL, colors.white]),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, BLUE),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, LINE),
        ("LINEAFTER", (0, 0), (0, -1), 0.4, LINE),
        ("LINEAFTER", (1, 0), (1, -1), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    s.append(ct)

    # 7
    s.append(sec(7, "Variables que pueden mover el plan"))
    s.append(Paragraph(
        "Dos cosas pueden correr o estirar este cronograma, y conviene "
        "decirlas de una vez.", st_body))
    if publico:
        s.append(Paragraph(
            "La primera es el ritmo propio de una universidad pública: "
            "los trámites de aval y anclaje institucional casi nunca son "
            "instantáneos, y no tiene sentido fingir que sí. La Fase 1 "
            "puede tomar más o menos tiempo del estimado; si se alarga, "
            "lo que hay que proteger no es una fecha exacta sino el "
            "interés de los gremios y las empresas que ya muestren "
            "disposición a participar. Ese es el reloj que de verdad no "
            "perdona.", st_body))
        s.append(Paragraph(
            "La segunda es la posibilidad de hacer esto en alianza con "
            "otra universidad. Puede acelerar el arranque, si esa "
            "universidad ya tiene convenios activos con gremios o "
            "recursos que sumar. O puede complicarlo, si hay que "
            "coordinar dos gobiernos académicos antes de convocar. Por "
            "eso no se fija todavía a qué fase entra: se deja como una "
            "opción que se activa en cuanto haya claridad, sin que eso "
            "bloquee arrancar con la Nacional sola.", st_body))
    else:
        s.append(Paragraph(
            "La primera es el ritmo propio de una universidad pública: los "
            "trámites de aval y anclaje institucional casi nunca son "
            "instantáneos, y no tiene sentido fingir que sí. La meta del 17 "
            "de agosto asume que el trámite no pasa de tres semanas; si se "
            "pasa, lo que hay que proteger no es la fecha exacta sino el "
            "interés de los gremios y las empresas que ya muestren "
            "disposición a participar. Ese es el reloj que de verdad no "
            "perdona.", st_body))
        s.append(Paragraph(
            "La segunda es la posibilidad de hacer esto en alianza con otra "
            "universidad. Puede acelerar el arranque, si esa universidad ya "
            "tiene convenios activos con gremios o recursos que sumar. O "
            "puede complicarlo, si hay que coordinar dos gobiernos académicos "
            "antes de convocar. Por eso no se fija todavía en el cronograma: "
            "se deja como una opción que se activa en cuanto haya claridad, "
            "sin que eso bloquee arrancar con la Nacional sola.", st_body))

    # 8
    s.append(sec(8, "Los entregables ancla del primer año"))
    s.append(Paragraph(
        "Uno, una cohorte piloto: 30 a 40 estudiantes de distintas "
        "facultades, un semestre, formación aplicada a un caso real. Se "
        "mide con algo simple: cada estudiante termina con un proyecto "
        "entregado, no con un certificado de asistencia.", st_body))
    s.append(Paragraph(
        "Dos, un marco propio de uso responsable de inteligencia "
        "artificial —ético, ambiental y académico— que fije la postura "
        "de la universidad frente al tema. No depende de que un convenio "
        "externo esté firmado, así que puede salir antes que los otros "
        "tres. Se mide con que exista, se publique, y que la propia "
        "universidad lo use puertas adentro antes de ofrecérselo a nadie "
        "más.", st_body))
    if publico:
        s.append(Paragraph(
            "Tres, un reto real con una entidad pública —alcaldía, "
            "gobernación, ministerio o una agencia como el DNP— y, en la "
            "medida en que la convocatoria a gremios avance a tiempo, un "
            "segundo reto con una empresa o un gremio. No hace falta que "
            "los dos arranquen en la misma fase: el público puede ir "
            "primero y el privado sumarse en la segunda cohorte si la "
            "primera queda corta de tiempo.", st_body))
    else:
        s.append(Paragraph(
            "Tres, un reto real con una entidad pública —alcaldía, "
            "gobernación, ministerio o una agencia como el DNP— y, en la "
            "medida en que la convocatoria a gremios avance a tiempo, un "
            "segundo reto con una empresa o un gremio. No hace falta que los "
            "dos arranquen el mismo mes: el público puede ir primero y el "
            "privado sumarse en la segunda cohorte si el primer semestre "
            "queda corto de tiempo.", st_body))
    s.append(Paragraph(
        "Cuatro, un tablero de datos abierto sobre un tema de país, "
        "construido por la propia cohorte, que sigue en línea después de "
        "que el semestre termina. No es un ejercicio de clase que se "
        "archiva: es un bien público que cualquiera puede consultar y "
        "que funciona como vitrina del laboratorio hacia afuera.",
        st_body))
    if publico:
        s.append(Paragraph(
            "Los cuatro se presentan juntos en el Demo Day de cierre —el "
            "marco, si todo va bien, ya lleva tiempo publicado.", st_body))
    else:
        s.append(Paragraph(
            "Los cuatro se presentan juntos en el Demo Day de enero —el "
            "marco, si todo va bien, ya lleva meses publicado.", st_body))

    # 9
    s.append(sec(9, "Gobernanza"))
    s.append(Paragraph(
        "El anclaje institucional importa más que el nombre del "
        "laboratorio. Debe vivir en una vicerrectoría académica o en la "
        "dirección nacional de extensión —no en una sola facultad— para "
        "que la transversalidad no dependa de la buena voluntad de un "
        "decano. El comité académico necesita profesores de ciencias "
        "humanas, ingeniería, ciencias económicas y ciencias exactas; sin "
        "esa mezcla, el laboratorio termina pareciéndose a la facultad "
        "que lo alberga. Conviene sumar una silla consultiva para un "
        "representante de gremios o del sector productivo, que ayude a "
        "calibrar qué necesitan las empresas sin capturar la agenda "
        "académica. Ese mismo comité redacta y firma el marco de uso "
        "responsable de IA del punto 3; no hace falta crear una "
        "instancia nueva solo para eso. La coordinación operativa puede "
        "ser pequeña: dos o tres personas que articulen cohortes, "
        "convenios y publicaciones alcanzan para arrancar. Y esa "
        "coordinación no arranca de cero: somos varios —egresados y "
        "profesionales de distintas áreas— los que queremos hacer parte "
        "del proceso de enseñanza y estamos listos para poner el tiempo "
        "desde el primer día.", st_body))

    # 10
    s.append(sec(10, "Cómo se sostiene"))
    s.append(Paragraph(
        "El arranque necesita una semilla institucional mínima: espacio, "
        "coordinación, dotación tecnológica. Nada de eso es costoso "
        "comparado con lo que ya invierte la universidad en otros "
        "laboratorios. La operación, en cambio, se financia con los "
        "propios convenios: cada entidad que trae un reto real trae "
        "también recursos, y en el caso de empresas y gremios ese aporte "
        "puede incluir becas, pasantías remuneradas o el pago del reto "
        "mismo —una fuente de sostenibilidad que no depende del "
        "presupuesto público. Con el tiempo, los proyectos que maduren "
        "pueden convertirse en desarrollos formales a través de las "
        "corporaciones de innovación de la universidad: ahí es donde el "
        "conocimiento vuelve al país convertido en soluciones, y a la "
        "universidad convertida en oportunidades.", st_body))

    # 11
    s.append(sec(11, "Cómo se sabe si funcionó"))
    s.append(Paragraph(
        "El indicador más simple es también el más duro: cuántos "
        "estudiantes terminan con un proyecto real entregado a una "
        "entidad o empresa que lo pidió, y cuántas facultades distintas "
        "representan. A eso se suman los convenios firmados —públicos y "
        "privados—, los documentos de política que la entidad aliada "
        "efectivamente adopta —no solo recibe— y los tableros que siguen "
        "actualizándose meses después de que el semestre terminó. Hay un "
        "indicador propio para el marco de uso de IA: si otra "
        "universidad o una entidad pública lo cita o lo adapta, la "
        "Nacional pasó de tener una postura interna a fijar el estándar "
        "del país. El indicador de largo plazo, el que de verdad "
        "importa, es otro: dónde terminan trabajando los egresados del "
        "LNL cinco años después. Si el laboratorio cumple lo que "
        "promete, esos egresados van a estar tomando decisiones "
        "difíciles tanto dentro del Estado como dentro de una empresa "
        "privada.", st_body))

    # 12
    s.append(sec(12, "Los riesgos que hay que vigilar"))
    s.append(Paragraph(
        "El más probable es que se perciba como tecnocrático, como si "
        "los datos fueran a reemplazar la discusión política. No es así, "
        "y la gobernanza plural —el comité con profesores de ciencias "
        "humanas, no solo de ingeniería— es la forma de evitarlo desde "
        "el diseño, no de corregirlo después.", st_body))
    s.append(Paragraph(
        "El segundo riesgo es más silencioso: que una sola facultad "
        "termine capturando el laboratorio porque fue la que puso el "
        "primer coordinador o el primer espacio físico. El anclaje en "
        "una vicerrectoría, y no en una facultad, es la mitigación "
        "estructural; sin eso, ningún acuerdo verbal alcanza.", st_body))
    s.append(Paragraph(
        "El tercero es depender de un solo gobierno de turno, sea el de "
        "la universidad o el nacional. La respuesta no es un contrato "
        "con una sola entidad, sino un ecosistema de aliados que se "
        "renueva convenio a convenio.", st_body))

    # 13
    s.append(sec(13, "Lo que se pide a la Rectoría"))
    if publico:
        s.append(numbered(1, "Aval institucional y acto de creación del "
                            "Laboratorio de Nuevos Liderazgos, en el "
                            "menor tiempo posible dentro de la Fase 1."))
    else:
        s.append(numbered(1, "Aval institucional y acto de creación del "
                            "Laboratorio de Nuevos Liderazgos, en un plazo "
                            "que no se estire más allá de tres semanas desde "
                            "esta presentación."))
    s.append(numbered(2, "Anclaje en una vicerrectoría que garantice su "
                        "carácter transversal."))
    s.append(numbered(3, "Un comité académico con profesores de "
                        "distintas facultades, con una silla consultiva "
                        "para gremios o sector productivo."))
    if publico:
        s.append(numbered(4, "Apertura de la convocatoria —a estudiantes, "
                            "gremios y empresas— al cierre de la Fase 1."))
    else:
        s.append(numbered(4, "Apertura de la convocatoria —a estudiantes, "
                            "gremios y empresas— con meta el 17 de agosto."))
    s.append(numbered(5, "Una semilla mínima —espacio, coordinación, "
                        "dotación— para arrancar la cohorte piloto."))
    s.append(numbered(6, "Un convenio marco que permita recibir retos "
                        "reales de entidades públicas y privadas desde "
                        "el inicio."))
    s.append(numbered(7, "Un mandato explícito para que el comité "
                        "académico redacte el marco de uso responsable "
                        "de IA, con respaldo de la oficina jurídica y de "
                        "comunicaciones antes de publicarlo."))

    doc.build(s)
    return out, os.path.getsize(out)


if __name__ == "__main__":
    os.makedirs(OUTDIR, exist_ok=True)
    p1, n1 = build_carta()
    print(f"Carta:          {p1}  ({n1/1024:.1f} KB)")
    p2, n2 = build_anexo()
    print(f"Anexo interno:  {p2}  ({n2/1024:.1f} KB)")
    p3, n3 = build_anexo(publico=True)
    print(f"Anexo público:  {p3}  ({n3/1024:.1f} KB)")
