#!/usr/bin/env python3
"""
test-presidencial-explica · lambda_handler.py

Endpoint POST que recibe el state del usuario del test presidencial 2026
y devuelve una lectura personalizada redactada por DeepSeek V3.

Reglas:
- La Lambda NUNCA inventa datos sobre el candidato. Recibe el state ya
  calculado (arquetipo dominante, candidato declarado, demografía, prio)
  y solo redacta sobre eso.
- Plantilla cerrada, temperature baja (0.3), max_tokens limitado.
- Response_format JSON para forzar estructura.
- Cache opcional en S3 bajo cache/{hash}.json — si dos personas con la
  misma combinación piden la lectura, devuelve el cache.

Body JSON esperado (POST):
{
  "registro": "popular" | "digital" | "analitico",
  "candidato": { "id": "ic", "nombre": "Iván Cepeda", "partido": "Pacto Histórico" },
  "candidato_origen": "declarado" | "sugerido",
  "demografia": { "edad": "36-50", "identidad": "barrio" },
  "prio": ["salud", "costo_vida"],
  "arquetipo_dominante": { "id": "castigo", "nombre": "Castigo a la restauración y demanda de alternancia", "pct": 42 },
  "arquetipo_secundario": { "id": "pertenencia", "nombre": "Pertenencia comunitaria y autonomía territorial", "pct": 24 },
  "arq_score": { "proteccion": 0, "estabilidad": 4, "supervivencia": 2, "castigo": 14, "pertenencia": 8 }
}

Response JSON:
{
  "lectura": "3 párrafos de 60-80 palabras c/u sobre lo dijo / lo que muestran las respuestas / el contraste.",
  "mensaje_corto": "Una frase de 12-18 palabras lista para meme o redes.",
  "alineacion": "alineado" | "vientos_cruzados" | "neutro",
  "modelo": "deepseek-chat",
  "generado_en": "ISO 8601 UTC",
  "cache_hit": true | false
}

ENV vars:
  DEEPSEEK_API_KEY  · clave de DeepSeek (la misma que ya usas en agenda-medios-recomienda)
  DEEPSEEK_URL      · default https://api.deepseek.com/chat/completions
  DEEPSEEK_MODEL    · default deepseek-chat (DeepSeek V3)
  S3_BUCKET         · default elecciones-2026
  CACHE_PREFIX      · default ricardoruiz.co/test-presidencial-2026/cache
  CACHE_TTL_DIAS    · default 14
"""

import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

# ---- Config ----
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = os.environ.get("DEEPSEEK_URL", "https://api.deepseek.com/chat/completions")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
S3_BUCKET = os.environ.get("S3_BUCKET", "elecciones-2026")
CACHE_PREFIX = os.environ.get("CACHE_PREFIX", "ricardoruiz.co/test-presidencial-2026/cache")
CACHE_TTL_DIAS = int(os.environ.get("CACHE_TTL_DIAS", "14"))
HTTP_TIMEOUT = 25

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json; charset=utf-8",
}

# Tono por registro: el LLM lo recibe como instrucción al redactar.
TONO = {
    "popular": "coloquial colombiano, frases cortas, tuteo de Bogotá, sin tecnicismos, sin argentinismos. Muletillas suaves OK ('la verdad', 'pues', 'uno'). Máximo 2 oraciones por idea.",
    "digital": "irónico, formato POV/'imaginate que', referencias de redes, máximo 1 emoji por párrafo, tono de conversación tuit. Tuteo de Bogotá, sin argentinismos.",
    "analitico": "neutro elevado, vocabulario político preciso, frases completas. Como una columna de opinión seria. Tuteo de Bogotá, sin argentinismos.",
}

SYSTEM_PROMPT = """Eres un analista electoral que ayuda a un ciudadano colombiano a entender el resultado de un test de arquetipo emocional para las presidenciales 2026. Te paso un objeto STATE con: registro de tono, candidato declarado, demografía, prioridad temática y arquetipo dominante calculado.

Tu trabajo es REDACTAR una lectura honesta y diagnóstica del resultado. NO inventas datos. NO mencionas a otros candidatos. NO recomiendas voto. NO usas argentinismos ni voseo: tuteo colombiano.

Devuelves JSON estricto con esta estructura exacta:
{
  "lectura": "Tres párrafos de 60-80 palabras cada uno, separados por \\n\\n. Estructura: (1) 'Lo que dijiste' — recap del candidato declarado y la prioridad temática. (2) 'Lo que muestran tus respuestas' — qué arquetipo dominó y por qué (en términos de emoción, miedo, deseo según el arquetipo). (3) 'El contraste' — si el candidato y el arquetipo van en el mismo sentido o en vientos cruzados, sin alarmar.",
  "mensaje_corto": "Una frase de 12 a 18 palabras, lista para usar como pie de meme o post en redes. Refuerza el insight central.",
  "alineacion": "alineado" o "vientos_cruzados" o "neutro"
}

REGLAS DURAS:
1. Tono diagnóstico, NUNCA veredicto. Nada de 'no te conviene' ni 'deberías votar otra cosa'.
2. Honra el REGISTRO indicado en STATE.tono — popular es coloquial, digital es irónico, analitico es neutro elevado.
3. NO inventes números, propuestas ni cifras del candidato. Solo describe lo que el usuario declaró y lo que arrojó el arquetipo.
4. NO menciones a otros candidatos.
5. Si el usuario eligió un candidato como 'sugerido' (mini-test), reconócelo: 'el mini-test te sugirió X'.
6. La identidad cotidiana del usuario (gremio, barrio, ciudad, familia, etc.) calibra el lenguaje cuando hables de Pertenencia.
7. Si hay un arquetipo secundario fuerte (>20% del puntaje), menciónalo como matiz.
8. Responde SOLO el JSON, sin texto adicional ni markdown."""


# ---- AWS clients (lazy) ----
_s3 = None
def _s3_client():
    global _s3
    if _s3 is None:
        import boto3  # type: ignore
        _s3 = boto3.client("s3")
    return _s3


# ---- Cache ----
def _cache_key(state):
    """Hash determinista del state, ignorando órdenes irrelevantes (lista de prio)."""
    canon = {
        "registro": state.get("registro"),
        "candidato_id": (state.get("candidato") or {}).get("id"),
        "candidato_origen": state.get("candidato_origen"),
        "edad": (state.get("demografia") or {}).get("edad"),
        "identidad": (state.get("demografia") or {}).get("identidad"),
        "prio": sorted(state.get("prio") or []),
        "arq_dom_id": (state.get("arquetipo_dominante") or {}).get("id"),
        "arq_sec_id": (state.get("arquetipo_secundario") or {}).get("id"),
    }
    blob = json.dumps(canon, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:24]


def _cache_get(key):
    try:
        obj = _s3_client().get_object(Bucket=S3_BUCKET, Key=f"{CACHE_PREFIX}/{key}.json")
        data = json.loads(obj["Body"].read().decode("utf-8"))
        # validar TTL
        gen = data.get("generado_en")
        if gen:
            t = datetime.fromisoformat(gen.replace("Z", "+00:00"))
            dias = (datetime.now(timezone.utc) - t).days
            if dias > CACHE_TTL_DIAS:
                return None
        return data
    except Exception:
        return None


def _cache_put(key, data):
    try:
        _s3_client().put_object(
            Bucket=S3_BUCKET,
            Key=f"{CACHE_PREFIX}/{key}.json",
            Body=json.dumps(data, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
            CacheControl="private, max-age=86400",
        )
    except Exception as e:
        print(f"[cache] WARN put falló: {e}")


# ---- DeepSeek ----
def _call_deepseek(state):
    """Llama a DeepSeek con el state ya validado. Devuelve el dict parseado del JSON."""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY no configurada")

    registro = state.get("registro") or "analitico"
    tono = TONO.get(registro, TONO["analitico"])

    cand = state.get("candidato") or {}
    demo = state.get("demografia") or {}
    arq_dom = state.get("arquetipo_dominante") or {}
    arq_sec = state.get("arquetipo_secundario") or {}
    arq_score = state.get("arq_score") or {}
    prio = state.get("prio") or []

    user_msg = f"""STATE:
- Registro (tono): {registro} → {tono}
- Candidato declarado: {cand.get('nombre')} ({cand.get('partido')})
- Origen del candidato: {state.get('candidato_origen', 'declarado')}
- Edad: {demo.get('edad', 'sin dato')}
- Identidad cotidiana: {demo.get('identidad', 'sin dato')}
- Prioridades temáticas: {', '.join(prio) if prio else 'sin declarar'}
- Arquetipo dominante: {arq_dom.get('nombre')} ({arq_dom.get('pct')}%)
- Arquetipo secundario: {arq_sec.get('nombre')} ({arq_sec.get('pct')}%)
- Distribución completa: {json.dumps(arq_score, ensure_ascii=False)}

Redacta la lectura en JSON estricto."""

    body = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
        # DeepSeek V4 usa parte del max_tokens en reasoning_content interno;
        # 1500 deja margen para el reasoning (~200-400 tokens) más los 3
        # párrafos de la respuesta (~500-700 tokens).
        "max_tokens": 1500,
    }).encode("utf-8")

    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        raw = resp.read().decode("utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(f"[deepseek] respuesta no es JSON. raw[:400]={raw[:400]}")
        raise

    choice = data["choices"][0]
    content = choice["message"].get("content") or ""
    finish = choice.get("finish_reason")
    usage = data.get("usage", {})
    if not content:
        # Cuando V4 se queda sin tokens en el reasoning, content queda vacío.
        print(f"[deepseek] content vacío. finish_reason={finish}, usage={usage}")
        raise ValueError(f"DeepSeek devolvió content vacío (finish_reason={finish}). Sube max_tokens.")

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        print(f"[deepseek] content no es JSON. content[:400]={content[:400]}")
        raise

    # Validación mínima
    for k in ("lectura", "mensaje_corto", "alineacion"):
        if k not in parsed:
            raise ValueError(f"DeepSeek devolvió JSON sin campo '{k}'")
    if parsed["alineacion"] not in ("alineado", "vientos_cruzados", "neutro"):
        parsed["alineacion"] = "neutro"

    return parsed


# ---- Handler ----
def handler(event, context):
    # Preflight CORS
    method = (event.get("requestContext", {}).get("http", {}).get("method")
              or event.get("httpMethod") or "POST").upper()
    if method == "OPTIONS":
        return {"statusCode": 204, "headers": CORS_HEADERS, "body": ""}

    if method != "POST":
        return _err(405, "method_not_allowed", "Solo POST")

    # Body
    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64
        body = base64.b64decode(body).decode("utf-8")
    try:
        state = json.loads(body) if isinstance(body, str) else body
    except Exception as e:
        return _err(400, "bad_json", f"Body no es JSON válido: {e}")

    # Validación mínima del state
    required = ["registro", "candidato", "arquetipo_dominante"]
    missing = [k for k in required if not state.get(k)]
    if missing:
        return _err(400, "missing_fields", f"Faltan campos: {missing}")

    # Cache check
    key = _cache_key(state)
    cached = _cache_get(key)
    if cached:
        cached["cache_hit"] = True
        return _ok(cached)

    # DeepSeek call
    try:
        parsed = _call_deepseek(state)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        print(f"[deepseek] HTTPError {e.code}: {body}")
        return _err(502, "deepseek_http_error", f"DeepSeek devolvió {e.code}")
    except Exception as e:
        print(f"[deepseek] FAIL: {type(e).__name__}: {e}")
        return _err(500, "deepseek_failed", str(e))

    out = {
        **parsed,
        "modelo": DEEPSEEK_MODEL,
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "cache_hit": False,
    }
    _cache_put(key, out)
    return _ok(out)


def _ok(payload):
    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps(payload, ensure_ascii=False),
    }


def _err(code, kind, msg):
    return {
        "statusCode": code,
        "headers": CORS_HEADERS,
        "body": json.dumps({"error": kind, "message": msg}, ensure_ascii=False),
    }


# ---- CLI test ----
if __name__ == "__main__":
    import sys
    sample = {
        "registro": "popular",
        "candidato": {"id": "ic", "nombre": "Iván Cepeda", "partido": "Pacto Histórico"},
        "candidato_origen": "declarado",
        "demografia": {"edad": "36-50", "identidad": "barrio"},
        "prio": ["salud", "costo_vida"],
        "arquetipo_dominante": {"id": "castigo", "nombre": "Castigo a la restauración y demanda de alternancia", "pct": 42},
        "arquetipo_secundario": {"id": "pertenencia", "nombre": "Pertenencia comunitaria y autonomía territorial", "pct": 24},
        "arq_score": {"proteccion": 2, "estabilidad": 4, "supervivencia": 2, "castigo": 14, "pertenencia": 8},
    }
    event = {"httpMethod": "POST", "body": json.dumps(sample)}
    result = handler(event, None)
    print(json.dumps(json.loads(result["body"]), indent=2, ensure_ascii=False))
    sys.exit(0 if result["statusCode"] == 200 else 1)
