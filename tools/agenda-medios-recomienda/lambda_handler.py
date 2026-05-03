#!/usr/bin/env python3
"""
agenda-medios-recomienda · lambda_handler.py

Capa de recomendación táctica del módulo 07. Para cada combinación de
arquetipo operativo × ventana, llama a DeepSeek con el paquete actual
de noticias (top 20 con tema/sentimiento ya enriquecidos por la
Lambda agenda-medios-enrich) y le pide:
  - lectura del momento desde el lente del arquetipo
  - 3-5 acciones concretas
  - 2-3 riesgos a evitar
  - mensaje sugerido (1-2 frases)

Trigger: EventBridge cada 6 horas.

Total llamadas: 4 arquetipos × 3 ventanas = 12 calls/run × 4 runs/día
              = ~1.440 calls/mes ≈ $2/mes en DeepSeek.

Output (todas en agregados/):
  recomendaciones-{arquetipo_slug}-{ventana}.json   (12 archivos)

ENV requerida:
  DEEPSEEK_API_KEY: misma key que usa agenda-medios-enrich
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ---- Config ----
S3_BUCKET = os.environ.get("AGENDA_S3_BUCKET", "elecciones-2026")
S3_PREFIX = os.environ.get("AGENDA_S3_PREFIX", "ricardoruiz.co/proyecto-dc/agenda")
AGG_PREFIX = f"{S3_PREFIX}/agregados"
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = os.environ.get("DEEPSEEK_URL", "https://api.deepseek.com/chat/completions")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
HTTP_TIMEOUT = 60

WINDOWS = ["6h", "24h", "5d"]
TOP_NOTICIAS_INPUT = 20  # cuántas noticias usar como contexto

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "arquetipos.json"), encoding="utf-8") as _f:
    ARQUETIPOS = json.load(_f)

_s3 = None
def _s3_client():
    global _s3
    if _s3 is None:
        import boto3  # type: ignore
        _s3 = boto3.client("s3")
    return _s3


# ---- Prompt construction ----
SYSTEM_PROMPT = """Eres un estratega político especializado en Medellín, Colombia. Te paso:
1. Un ARQUETIPO operativo (un perfil de movilizador electoral con sus características).
2. Un PAQUETE DE NOTICIAS recientes (con tema y sentimiento ya clasificados).

Devuelves recomendaciones tácticas en JSON estricto con esta estructura exacta:
{
  "lectura": "1 párrafo (max 80 palabras) sobre qué está pasando ahora desde el lente de este arquetipo. Específico al paquete de noticias, no genérico.",
  "acciones": ["acción 1 concreta", "acción 2 concreta", "acción 3 concreta"],
  "riesgos": ["riesgo 1", "riesgo 2"],
  "mensaje_sugerido": "1-2 frases listas para usar como mensaje en su canal típico"
}

REGLAS:
1. CONCRETO Y ACCIONABLE: nada de consejos genéricos tipo "comparte tu opinión". Específico al momento ("hoy hablan de X, tu mejor jugada es Y").
2. COHERENTE CON EL ARQUETIPO: usa sus canales específicos (no le pidas a un Confirmador Silencioso que haga TikTok), su intensidad y su radio de influencia.
3. SI HAY NARRATIVA ADVERSARIA o riesgos virales, indícalo en "riesgos".
4. TONO PROFESIONAL, NO PARTIDISTA. Habla como consultor estratégico, no como militante.
5. NO menciones a Carvalho ni a un candidato específico. Habla de "tu candidato" o el contexto general.

Responde SOLO el JSON, sin texto adicional ni markdown."""


def call_deepseek(arquetipo, titulares, ventana):
    """Llama DeepSeek con el contexto de un arquetipo + paquete de noticias."""
    arq = arquetipo
    canales = arq.get("canales", "—")
    descripcion = arq.get("descripcion", "")
    sesgo = arq.get("sesgo_dominante", "—")

    notes_lines = []
    for i, t in enumerate(titulares[:TOP_NOTICIAS_INPUT], 1):
        sent = (t.get("sentimiento") or "neutro")[0].upper()  # P/N/N
        actores = ", ".join(t.get("actores") or []) or "sin actores claros"
        tema = t.get("tema") or "otros"
        titulo = t.get("titulo") or ""
        notes_lines.append(f"{i}. [{sent}] {titulo} — tema: {tema} — actores: {actores}")
    paquete = "\n".join(notes_lines) if notes_lines else "(sin noticias en esta ventana)"

    user_msg = f"""ARQUETIPO: {arq['nombre']}
Tagline: {arq.get('tagline','—')}
Intensidad: {arq.get('intensidad','—')}
Radio de influencia: {arq.get('radio','—')}
Canales típicos: {canales}
Sesgo dominante: {sesgo}
Descripción: {descripcion}

PAQUETE DE NOTICIAS — últimas {ventana}, top {len(titulares)}:
{paquete}

JSON:"""

    body = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.3,  # algo de variabilidad para respuestas más naturales
        "response_format": {"type": "json_object"},
        "max_tokens": 700,
    }).encode("utf-8")

    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
        resp = json.loads(r.read())
    content = resp["choices"][0]["message"]["content"]
    return json.loads(content)


# ---- S3 helpers ----
def get_titulares(s3, ventana):
    key = f"{AGG_PREFIX}/titulares-{ventana}.json"
    try:
        obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
        data = json.loads(obj["Body"].read())
        return data.get("titulares", [])
    except Exception as e:
        print(f"[get_titulares] FAIL {key}: {e}")
        return []


def write_recomendacion(s3, arq, ventana, payload):
    key = f"{AGG_PREFIX}/recomendaciones-{arq['slug']}-{ventana}.json"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
        CacheControl="public, max-age=300",
    )
    return key


# ---- Pipeline ----
def run():
    if not DEEPSEEK_API_KEY:
        return {"error": "DEEPSEEK_API_KEY env var no configurada"}

    s3 = _s3_client()
    now = datetime.now(timezone.utc)
    summary = {}
    out_paths = []

    for ventana in WINDOWS:
        titulares = get_titulares(s3, ventana)
        if not titulares:
            print(f"[{ventana}] sin titulares — skip")
            summary[ventana] = {"skip": "sin titulares"}
            continue

        for arq in ARQUETIPOS:
            try:
                rec = call_deepseek(arq, titulares, ventana)
            except Exception as e:
                print(f"[deepseek] FAIL {arq['slug']}-{ventana}: {type(e).__name__}: {e}")
                continue

            payload = {
                "ventana": ventana,
                "arquetipo": arq["nombre"],
                "arquetipo_slug": arq["slug"],
                "tagline": arq.get("tagline"),
                "generado_en": now.isoformat(),
                "n_noticias_input": len(titulares[:TOP_NOTICIAS_INPUT]),
                "lectura": rec.get("lectura", ""),
                "acciones": rec.get("acciones", []) or [],
                "riesgos": rec.get("riesgos", []) or [],
                "mensaje_sugerido": rec.get("mensaje_sugerido", ""),
                "modelo": DEEPSEEK_MODEL,
            }
            path = write_recomendacion(s3, arq, ventana, payload)
            out_paths.append(path)
            print(f"[{ventana}] {arq['slug']} OK")

        summary[ventana] = {"arquetipos": len(ARQUETIPOS), "titulares_input": len(titulares[:TOP_NOTICIAS_INPUT])}

    result = {
        "generado_en": now.isoformat(),
        "ventanas": summary,
        "salidas": out_paths,
    }
    print(f"[run] {result}")
    return result


def handler(event, context):
    return run()


if __name__ == "__main__":
    if "--show-prompt" in sys.argv:
        print(SYSTEM_PROMPT)
    elif "--dry-run" in sys.argv:
        # Sintético: testea una llamada con un arquetipo y noticias inventadas
        ev_titulares = [
            {"titulo": "Federico Gutiérrez anuncia plan de seguridad por alza de homicidios",
             "actores": ["Federico Gutiérrez"], "tema": "seguridad", "sentimiento": "neutro"},
            {"titulo": "Daniel Quintero responde críticas sobre Aguas Vivas en audiencia",
             "actores": ["Daniel Quintero"], "tema": "corrupcion", "sentimiento": "negativo"},
        ]
        rec = call_deepseek(ARQUETIPOS[0], ev_titulares, "6h")
        print(json.dumps(rec, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(run(), ensure_ascii=False, indent=2))
