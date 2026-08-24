#!/usr/bin/env python3
"""
Envía la propuesta OE3 por correo vía Resend, con el PDF adjunto.
La API key se lee de la variable de entorno RESEND_API_KEY (nunca se guarda).

Uso:
    RESEND_API_KEY='re_xxx' python3 tools/send-propuesta/send.py          # envía
    RESEND_API_KEY='re_xxx' python3 tools/send-propuesta/send.py --dry    # prueba sin enviar
"""
import os
import sys
import json
import base64
import urllib.request

# --- Configuración (editar si hace falta) ----------------------------------
FROM      = "Ricardo Ruiz <contacto@ricardoruiz.co>"
TO        = ["Carloshrodriquez10@hotmail.com"]
REPLY_TO  = "reruizc@gmail.com"
SUBJECT   = "Propuesta — Objetivo 3 de tu tesis (social listening + análisis de sentimiento)"
PDF_PATH  = ("/Users/ricardoruiz/ricardoruiz.co/Propuestas/"
             "Propuesta-OE3-Social-Listening-Petro.pdf")
PDF_NAME  = "Propuesta-OE3-Social-Listening-Petro.pdf"

TEXT_BODY = """Hola Carlos, ¿cómo vas?

Como quedamos, te adjunto la propuesta para la ejecución técnica completa de tu \
tercer objetivo específico (OE3): la extracción del histórico de X, el análisis \
de sentimiento (PLN) en español colombiano y la entrega de todo listo para SPSS. \
La acoté a las tres crisis que definiste: la UNGRD, la postura frente al conflicto \
Palestina–Israel, y el choque con las Altas Cortes por la tributaria vía decreto.

En resumen, encontrarás tres planes (Esencial, Completo y un acompañamiento \
opcional a la sustentación). El Esencial ya incluye todo lo que blinda la defensa: \
extracción gestionada y verificable, sentimiento auditable, validación con Kappa \
de Cohen, la matriz diligenciada + archivo SPSS con el Spearman corrido, y el \
memorando metodológico reproducible. El Completo le suma el tablero interactivo. \
En la propuesta también te dejé una tabla comparándolo con lo que ofrece un \
freelancer o una herramienta de IA genérica, para que veas por qué este enfoque \
sí aguanta las preguntas de un jurado.

Un par de detalles prácticos: el plazo es de 7 días hábiles desde que cerremos las \
fechas de las tres crisis, y el pago es en línea (tarjeta de crédito/débito, PSE, \
Nequi o Bancolombia; con tarjeta incluso puedes diferirlo a cuotas con tu banco).

Para arrancar solo necesito que definamos juntos las ventanas de fecha de cada \
crisis. Cualquier duda sobre el alcance o el método, con gusto la resolvemos por \
aquí o en una llamada corta.

Quedo atento. Un abrazo,

Ricardo Ruiz
ricardoruiz.co
"""

HTML_BODY = """<div style="font-family:Arial,Helvetica,sans-serif;font-size:15px;line-height:1.6;color:#1a1a2e;max-width:560px">
<p>Hola Carlos, ¿cómo vas?</p>
<p>Como quedamos, te adjunto la propuesta para la <b>ejecución técnica completa de tu tercer objetivo específico (OE3)</b>: la extracción del histórico de X, el análisis de sentimiento (PLN) en español colombiano y la entrega de todo listo para SPSS. La acoté a las <b>tres crisis</b> que definiste: la UNGRD, la postura frente al conflicto Palestina–Israel, y el choque con las Altas Cortes por la tributaria vía decreto.</p>
<p>En resumen, encontrarás <b>tres planes</b> (Esencial, Completo y un acompañamiento opcional a la sustentación). El <b>Esencial</b> ya incluye todo lo que blinda la defensa: extracción gestionada y verificable, sentimiento auditable, <b>validación con Kappa de Cohen</b>, la matriz diligenciada + archivo SPSS con el Spearman corrido, y el memorando metodológico reproducible. El <b>Completo</b> le suma el tablero interactivo. En la propuesta también te dejé una tabla comparándolo con lo que ofrece un freelancer o una herramienta de IA genérica, para que veas por qué este enfoque sí aguanta las preguntas de un jurado.</p>
<p>Un par de detalles prácticos: el <b>plazo es de 7 días hábiles</b> desde que cerremos las fechas de las tres crisis, y el <b>pago es en línea</b> (tarjeta de crédito/débito, PSE, Nequi o Bancolombia; con tarjeta incluso puedes diferirlo a cuotas con tu banco).</p>
<p>Para arrancar solo necesito que <b>definamos juntos las ventanas de fecha de cada crisis</b>. Cualquier duda sobre el alcance o el método, con gusto la resolvemos por aquí o en una llamada corta.</p>
<p>Quedo atento. Un abrazo,</p>
<p><b>Ricardo Ruiz</b><br><a href="https://ricardoruiz.co" style="color:#0047FF">ricardoruiz.co</a></p>
</div>"""


def main():
    dry = "--dry" in sys.argv
    key = os.environ.get("RESEND_API_KEY", "").strip()
    if not key:
        sys.exit("ERROR: falta RESEND_API_KEY. Uso: RESEND_API_KEY='re_xxx' python3 ...")
    if not os.path.exists(PDF_PATH):
        sys.exit(f"ERROR: no encuentro el PDF en {PDF_PATH}")

    with open(PDF_PATH, "rb") as f:
        pdf_b64 = base64.b64encode(f.read()).decode("ascii")

    payload = {
        "from": FROM,
        "to": TO,
        "reply_to": REPLY_TO,
        "subject": SUBJECT,
        "text": TEXT_BODY,
        "html": HTML_BODY,
        "attachments": [{"filename": PDF_NAME, "content": pdf_b64}],
    }

    print(f"De:        {FROM}")
    print(f"Para:      {TO}")
    print(f"Reply-To:  {REPLY_TO}")
    print(f"Asunto:    {SUBJECT}")
    print(f"Adjunto:   {PDF_NAME} ({len(pdf_b64)//1024} KB base64)")
    if dry:
        print("\n[--dry] No se envió nada. Quita --dry para enviar.")
        return

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/126.0 Safari/537.36",
                 "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode("utf-8")
            print(f"\n✅ Enviado. Respuesta Resend: {body}")
    except urllib.error.HTTPError as e:
        print(f"\n❌ Error {e.code}: {e.read().decode('utf-8')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
