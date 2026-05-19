#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera el PDF de reglas del concurso "Tu Pronóstico · Primera Vuelta 2026".
Cubre: en qué consiste, sistema de elección del ganador (objetivo, replicable),
cláusula de que NO es una apuesta, y tratamiento de datos personales (Ley 1581
de 2012 — habeas data Colombia).

Salida: Bases de datos/pronostico-1v/reglas-pronostico-1v-2026.pdf
Subir a: s3://elecciones-2026/ricardoruiz.co/DESCARGAS/reglas-pronostico-1v-2026.pdf
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, ListFlowable, ListItem
)

OUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Bases de datos", "pronostico-1v", "reglas-pronostico-1v-2026.pdf",
)

BLUE = colors.HexColor("#0047FF")
INK = colors.HexColor("#0d1120")
SOFT = colors.HexColor("#444444")

styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=styles["Title"], fontName="Helvetica-Bold",
                     fontSize=20, leading=24, textColor=INK, spaceAfter=4)
SUB = ParagraphStyle("SUB", parent=styles["Normal"], fontName="Helvetica",
                      fontSize=10, leading=14, textColor=SOFT, alignment=TA_CENTER,
                      spaceAfter=2)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold",
                     fontSize=12.5, leading=16, textColor=BLUE,
                     spaceBefore=16, spaceAfter=6)
BODY = ParagraphStyle("BODY", parent=styles["Normal"], fontName="Helvetica",
                       fontSize=10, leading=15, textColor=INK,
                       alignment=TA_JUSTIFY, spaceAfter=7)
LI = ParagraphStyle("LI", parent=BODY, spaceAfter=4)
FOOT = ParagraphStyle("FOOT", parent=styles["Normal"], fontName="Helvetica",
                       fontSize=8, leading=11, textColor=SOFT, alignment=TA_CENTER)


def bullets(items):
    return ListFlowable(
        [ListItem(Paragraph(t, LI), leftIndent=10, value="•") for t in items],
        bulletType="bullet", start="•", leftIndent=14,
    )


def build():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    doc = SimpleDocTemplate(
        OUT, pagesize=A4,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm,
        topMargin=2.0 * cm, bottomMargin=1.8 * cm,
        title="Reglas — Tu Pronóstico Primera Vuelta 2026",
        author="ricardoruiz.co",
    )
    s = []
    s.append(Paragraph("Tu Pronóstico · Primera Vuelta 2026", H1))
    s.append(Paragraph("Reglas del concurso y tratamiento de datos personales", SUB))
    s.append(Paragraph("ricardoruiz.co — actualizado: mayo de 2026", SUB))
    s.append(Spacer(1, 6))
    s.append(HRFlowable(width="100%", thickness=1, color=BLUE))

    s.append(Paragraph("1. En qué consiste", H2))
    s.append(Paragraph(
        "Es un ejercicio ciudadano y gratuito: parte del ponderador propio de "
        "encuestas de ricardoruiz.co y te invita a ajustar las cifras a lo que "
        "tú crees que será el resultado de la primera vuelta presidencial de "
        "Colombia del <b>31 de mayo de 2026</b>: porcentaje de participación "
        "sobre el censo electoral, porcentaje de cada candidato y voto en "
        "blanco. Tu pronóstico se guarda para compararlo con el resultado "
        "oficial.", BODY))

    s.append(Paragraph("2. Premio y cómo se elige al ganador", H2))
    s.append(Paragraph(
        "Quien más se acerque al resultado oficial recibe <b>cien mil pesos "
        "colombianos (COP $100.000) más seis (6) meses gratis del plan "
        "Premium</b> de la plataforma. El criterio es objetivo, público y "
        "replicable por cualquiera:", BODY))
    s.append(bullets([
        "Se toma el resultado oficial publicado por la Registraduría Nacional "
        "del Estado Civil para la primera vuelta presidencial 2026.",
        "El pronóstico se compara sobre <b>los seis candidatos modelados, el "
        "voto en blanco y la participación</b>. Como en una elección real no "
        "existe el «no sabe / no responde», ese porcentaje de las encuestas se "
        "reparte de forma proporcional entre esos renglones antes de empezar; "
        "las candidaturas por debajo del 1% («Otros») se mantienen fijas en su "
        "valor del ponderador. El resultado oficial se normaliza igual para "
        "que la comparación sea simétrica.",
        "Para cada participante se calcula el <b>error absoluto medio (MAE)</b>: "
        "el promedio de la diferencia absoluta, en puntos porcentuales, entre "
        "lo que pronosticó y el porcentaje real de cada candidato, más el voto "
        "en blanco y la participación.",
        "Gana el participante con el <b>menor MAE</b>. Si hay empate a dos "
        "decimales, gana quien haya enviado primero su pronóstico (se usa la "
        "fecha de creación del registro).",
        "Solo cuenta el <b>último pronóstico guardado por cada correo</b> antes "
        "del cierre. Puedes ajustarlo cuantas veces quieras hasta el "
        "30 de mayo de 2026 a las 23:59 (hora de Colombia).",
    ]))
    s.append(Paragraph(
        "El cálculo y la lista ordenada de resultados se publican después de la "
        "primera vuelta para que cualquiera pueda verificar al ganador.", BODY))

    s.append(Paragraph("3. Esto NO es una apuesta", H2))
    s.append(Paragraph(
        "La participación es <b>totalmente gratuita</b>. No se exige ni se "
        "recibe dinero, depósito, pago ni contraprestación de ningún tipo para "
        "participar, y el resultado no depende del azar sino del criterio del "
        "participante. Por lo tanto <b>no constituye un juego de suerte y azar "
        "ni una apuesta</b> en los términos de la Ley 643 de 2001. Es un "
        "concurso de pronóstico basado en conocimiento y análisis, con un "
        "incentivo simbólico. El premio es una mera liberalidad de "
        "ricardoruiz.co.", BODY))

    s.append(Paragraph("4. Tratamiento de datos personales", H2))
    s.append(Paragraph(
        "ricardoruiz.co actúa como responsable del tratamiento. Conforme a la "
        "Ley 1581 de 2012 y el Decreto 1377 de 2013 (habeas data, Colombia):", BODY))
    s.append(bullets([
        "<b>Qué datos pedimos:</b> nombre, apellido, departamento, municipio "
        "(y comuna o localidad si aplica), correo electrónico y número de "
        "WhatsApp.",
        "<b>Para qué los usamos:</b> única y exclusivamente para contactarte "
        "si resultas ganador y para entregarte el premio. No se usan para "
        "publicidad ni se cruzan con otros fines.",
        "<b>No los compartimos:</b> no se venden, alquilan ni ceden a terceros. "
        "Se almacenan cifrados en infraestructura propia (Cloudflare KV).",
        "<b>Cuánto los guardamos:</b> hasta 60 días después de la primera "
        "vuelta; luego se eliminan, salvo obligación legal de conservarlos.",
        "<b>Tus derechos:</b> puedes conocer, actualizar, rectificar o solicitar "
        "la supresión de tus datos, o revocar esta autorización, escribiendo a "
        "reruizc@gmail.com. Atendemos la solicitud en los plazos de ley.",
    ]))
    s.append(Paragraph(
        "Al enviar tu pronóstico marcando la casilla de autorización, declaras "
        "ser mayor de edad y autorizas de manera libre, previa, expresa e "
        "informada el tratamiento de tus datos para los fines aquí descritos.", BODY))

    s.append(Paragraph("5. Condiciones generales", H2))
    s.append(bullets([
        "Pueden participar personas mayores de edad residentes en Colombia.",
        "Un premio por persona; el correo es el identificador único.",
        "ricardoruiz.co puede ajustar fechas o aclarar reglas por causas de "
        "fuerza mayor, informándolo en esta misma página.",
        "La participación implica la aceptación de estas reglas.",
    ]))

    s.append(Spacer(1, 16))
    s.append(HRFlowable(width="100%", thickness=0.5, color=SOFT))
    s.append(Spacer(1, 6))
    s.append(Paragraph(
        "ricardoruiz.co · Proyecto independiente de análisis electoral · "
        "Contacto y habeas data: reruizc@gmail.com", FOOT))

    doc.build(s)
    print("PDF generado:", OUT, "·", os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    build()
