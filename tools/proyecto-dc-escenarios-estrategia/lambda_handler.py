#!/usr/bin/env python3
"""
proyecto-dc-escenarios-estrategia · lambda_handler.py

Endpoint POST del módulo 08 (simulador what-if Escenarios 2027 del
Proyecto DC privado). Recibe el state actual del simulador (11 sliders +
nivel del mapa + territorio opcional + arquetipos afectados) y devuelve
recomendaciones tácticas redactadas por DeepSeek V4 Flash.

La Lambda NUNCA inventa datos territoriales ni infiere por su cuenta.
Recibe el state ya calculado (arquetipo base, proyectado, scores) y
solo redacta sobre eso usando la matriz psicopolítica 2027.

Body JSON esperado (POST):
{
  "level": "comuna" | "barrio",
  "territorio": "Robledo" | "12 de Octubre" | null,
  "sliders": { "seguridad": -3, "electoral": -5, ... },
  "arquetipo_base":  "proteccion",            # global o del territorio
  "arquetipo_proyectado": "castigo",          # global o del territorio
  "scores":  { "proteccion": 5.1, "castigo": 7.3, ... },
  "migraciones_top": [
    { "lugar": "Robledo", "de": "proteccion", "a": "castigo" },
    { "lugar": "Castilla", "de": "continuidad", "a": "supervivencia" }
  ],
  "afinidad_carvalho_promedio": 1.2          # opcional, -5..+5
}

Response JSON:
{
  "lectura_general": "1 párrafo (max 100 palabras) sobre qué pasa.",
  "escenario_resumido": "Línea corta para header.",
  "recomendaciones": {
    "proteccion":    { "lectura": "...", "acciones": ["...","...","..."], "riesgo": "..." },
    "castigo":       { ... },
    "continuidad":   { ... },
    "supervivencia": { ... },
    "pertenencia":   { ... }
  },
  "modelo": "deepseek-v4-flash",
  "generado_en": "ISO 8601 UTC",
  "cache_hit": true | false
}

ENV vars:
  DEEPSEEK_API_KEY  · clave de DeepSeek (la misma de test-presidencial-explica)
  DEEPSEEK_URL      · default https://api.deepseek.com/chat/completions
  DEEPSEEK_MODEL    · default deepseek-v4-flash
  S3_BUCKET         · default elecciones-2026
  CACHE_PREFIX      · default ricardoruiz.co/proyecto-dc/escenarios-cache
  CACHE_TTL_DIAS    · default 7
  ALLOWED_ORIGINS_EXTRA  · csv de orígenes extra (https://...)
  STRICT_ORIGIN     · default true
  PROMPT_VERSION    · default v1 (bumpear para invalidar cache al cambiar prompt)
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
CACHE_PREFIX = os.environ.get("CACHE_PREFIX", "ricardoruiz.co/proyecto-dc/escenarios-cache")
CACHE_TTL_DIAS = int(os.environ.get("CACHE_TTL_DIAS", "7"))
HTTP_TIMEOUT = 55
MAX_BODY_BYTES = int(os.environ.get("MAX_BODY_BYTES", "20000"))
PROMPT_VERSION = os.environ.get("PROMPT_VERSION", "v1")

# CORS — proyecto-dc es privado pero el frontend vive en ricardoruiz.co
ALLOWED_ORIGINS = {
    "https://ricardoruiz.co",
    "https://www.ricardoruiz.co",
    "http://localhost:8765",  # preview local
}
ALLOWED_ORIGINS |= {
    o.strip() for o in os.environ.get("ALLOWED_ORIGINS_EXTRA", "").split(",")
    if o.strip().startswith(("https://", "http://localhost"))
}
STRICT_ORIGIN = os.environ.get("STRICT_ORIGIN", "true").lower() == "true"

_s3 = None
def _s3_client():
    global _s3
    if _s3 is None:
        import boto3
        _s3 = boto3.client("s3")
    return _s3

# ---- Matriz de sensibilidad (espejo del frontend para que el prompt no la invente) ----
SENS = {
    "proteccion":    {"seguridad":5,"corrupcion":3,"empleo":4,"servicios_publicos":4,"movilidad":4,"salud_educacion":3,"participacion_jal":2,"cultura_identidad":2},
    "castigo":       {"seguridad":4,"corrupcion":5,"empleo":4,"servicios_publicos":3,"movilidad":3,"salud_educacion":3,"participacion_jal":4,"cultura_identidad":3},
    "continuidad":   {"seguridad":3,"corrupcion":2,"empleo":3,"servicios_publicos":5,"movilidad":4,"salud_educacion":4,"participacion_jal":5,"cultura_identidad":3},
    "supervivencia": {"seguridad":3,"corrupcion":2,"empleo":5,"servicios_publicos":5,"movilidad":4,"salud_educacion":4,"participacion_jal":2,"cultura_identidad":2},
    "pertenencia":   {"seguridad":4,"corrupcion":3,"empleo":3,"servicios_publicos":4,"movilidad":3,"salud_educacion":3,"participacion_jal":5,"cultura_identidad":5},
}

ARQUETIPOS = {
    "proteccion":    {"nombre":"Protección con resultados y orden competente", "emocion":"Seguridad condicionada por resultados", "canales":"WhatsApp, Facebook, Radio local, TV local, vocería institucional, líderes de seguridad/comercio", "tono":"Firme, serio, ejecutivo, verificable y territorial"},
    "castigo":       {"nombre":"Castigo a la restauración y demanda de alternancia", "emocion":"Frustración, sospecha y sanción retrospectiva", "canales":"WhatsApp, YouTube, Facebook, medios digitales, debates, vocerías ciudadanas", "tono":"Crítico, documentado, vigilante, cívico y argumentativo"},
    "continuidad":   {"nombre":"Continuidad pragmática y gestión barrial", "emocion":"Confianza práctica y aversión a perder canales", "canales":"WhatsApp, reuniones pequeñas, llamadas, líderes comunitarios, casa a casa, JAL", "tono":"Cercano, funcional, barrial, concreto y continuista con mejoras"},
    "supervivencia": {"nombre":"Supervivencia económica y servicios cotidianos", "emocion":"Ansiedad material y necesidad inmediata", "canales":"WhatsApp, TikTok, radio popular, activaciones territoriales, puntos barriales, voz a voz", "tono":"Directo, sencillo, útil, empático y resolvedor"},
    "pertenencia":   {"nombre":"Pertenencia comunitaria y autonomía territorial", "emocion":"Orgullo barrial, reconocimiento y protección de liderazgos", "canales":"WhatsApp comunitario, Facebook, Instagram, encuentros barriales, asambleas, colectivos culturales", "tono":"Comunitario, reconocedor, participativo, identitario y esperanzador con arraigo"},
}

SLIDER_LABEL = {
    "seguridad":         "seguridad percibida",
    "electoral":         "presidente nacional (neg=izquierda, pos=derecha)",
    "costo_vida":        "costo de vida (neg=más caro, pos=alivio)",
    "empleo":            "empleo e ingresos",
    "afinidad_carvalho": "presencia del equipo Carvalho",
    "riesgo_cambio":     "volatilidad emocional del barrio",
    "mediatico":         "saliencia mediática local",
    "obras":             "obras y mantenimiento",
    "favorabilidad":     "favorabilidad del alcalde actual",
    "movilidad":         "movilidad cotidiana",
    "ambiente":          "calidad ambiental",
}

# ---- Prompt ----
SYSTEM_PROMPT = """Eres un consultor estratégico senior especializado en política electoral local de Medellín, Colombia. Te paso:

1. Un ESCENARIO 2027 definido por 11 palancas bipolares (−5 a +5) que mueven el contexto político-electoral.
2. Un TERRITORIO opcional (comuna o barrio) o el global de la ciudad.
3. ARQUETIPO BASE 2023 y ARQUETIPO PROYECTADO 2027 bajo el escenario, con SCORES de los 5 arquetipos psicopolíticos (la migración entre arquetipos ya está calculada por un motor determinista; vos no la reescribís).
4. Las MIGRACIONES TOP (barrios o comunas que cambian de arquetipo bajo este escenario).
5. AFINIDAD del equipo Carvalho en el territorio (huella histórica Carvalho 2019 + Quintero 2026), opcional.

Los 5 ARQUETIPOS PSICOPOLÍTICOS 2027 son:
- proteccion: orden con resultados verificables. Canales WhatsApp, Facebook, Radio. Tono firme y ejecutivo.
- castigo: desencanto activo, demanda alternancia. Canales YouTube, debates. Tono crítico y documentado.
- continuidad: vínculo que funciona, gestión barrial. Canales casa a casa, JAL. Tono cercano y funcional.
- supervivencia: ansiedad material, soluciones inmediatas. Canales TikTok, radio popular. Tono directo y útil.
- pertenencia: orgullo barrial, autonomía territorial. Canales asambleas, colectivos. Tono comunitario y reconocedor.

Devolvés recomendaciones tácticas en JSON estricto con esta estructura:
{
  "lectura_general": "1 párrafo (max 100 palabras) sobre qué pasa en este escenario: qué palancas pesan, qué migración es la clave, en qué territorio focal.",
  "escenario_resumido": "Línea corta de 8-12 palabras para el header (ej: 'Crisis económica con presidente de izquierda fortalece castigo')",
  "recomendaciones": {
    "proteccion":    { "lectura": "1-2 frases sobre cómo este arquetipo procesa el escenario", "acciones": ["acción 1 concreta", "acción 2 concreta"], "riesgo": "1 frase sobre riesgo de fuga o narrativa adversaria" },
    "castigo":       { ... idéntica estructura ... },
    "continuidad":   { ... },
    "supervivencia": { ... },
    "pertenencia":   { ... }
  }
}

REGLAS:
1. CONCRETO Y ACCIONABLE. Nada genérico. Específico al escenario y al territorio si lo hay.
2. COHERENTE CON CADA ARQUETIPO: canales, tono, sesgos. No le pidas a Protección hacer TikTok ni a Supervivencia hilos de Twitter argumentativos.
3. RESPETAR el motor: no inventes una migración distinta a la que te paso. Vos solo redactás sobre la migración existente.
4. NEUTRAL POLÍTICAMENTE: no nombres a Carvalho, Quintero, Federico Gutiérrez ni a ningún candidato específico. Habla de "tu candidato", "tu equipo", "el alcalde actual", "el presidente nacional".
5. TUTEO NEUTRO (sin voseo argentino, sin paisa marcado).
6. Si el escenario es neutral (todas las palancas en 0), retorná lectura_general indicando que sin escenario activo no hay recomendación táctica diferenciada.

Responde SOLO el JSON, sin texto adicional ni markdown."""

# ---- Helpers ----
def _hash24(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:24]

def _cache_key(payload):
    """Hash determinista del payload + PROMPT_VERSION para invalidar al cambiar prompt."""
    parts = [PROMPT_VERSION]
    # Sliders ordenados
    sl = payload.get("sliders") or {}
    parts.append(",".join(f"{k}={sl.get(k, 0)}" for k in sorted(sl.keys())))
    parts.append(f"level={payload.get('level','')}")
    parts.append(f"terr={payload.get('territorio','')}")
    parts.append(f"base={payload.get('arquetipo_base','')}")
    parts.append(f"proy={payload.get('arquetipo_proyectado','')}")
    return _hash24("|".join(parts))

def _cors_headers(origin):
    """Devuelve headers CORS para la respuesta."""
    allowed = origin if (origin in ALLOWED_ORIGINS) else (
        "" if STRICT_ORIGIN else "*"
    )
    return {
        "Access-Control-Allow-Origin": allowed,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Max-Age": "300",
        "Vary": "Origin",
        "Content-Type": "application/json",
    }

def _resp(status, body, origin):
    return {
        "statusCode": status,
        "headers": _cors_headers(origin),
        "body": json.dumps(body, ensure_ascii=False),
    }

def _user_msg(payload):
    """Construye el user message para DeepSeek."""
    sl = payload.get("sliders") or {}
    activos = [(k, v) for k, v in sl.items() if isinstance(v, (int, float)) and v != 0]
    activos.sort(key=lambda kv: abs(kv[1]), reverse=True)
    lines = []
    lines.append(f"NIVEL DEL MAPA: {payload.get('level','—')}")
    terr = payload.get("territorio")
    if terr:
        lines.append(f"TERRITORIO: {terr}")
    else:
        lines.append("TERRITORIO: global (toda Medellín)")
    lines.append("")
    lines.append("PALANCAS ACTIVAS (ordenadas por magnitud):")
    if not activos:
        lines.append("  (todas en 0 · escenario neutral)")
    for k, v in activos:
        sign = "+" if v > 0 else ""
        lines.append(f"  · {SLIDER_LABEL.get(k, k)}: {sign}{v}")
    lines.append("")
    base = payload.get("arquetipo_base")
    proy = payload.get("arquetipo_proyectado")
    lines.append(f"ARQUETIPO BASE 2023: {base or '—'}")
    lines.append(f"ARQUETIPO PROYECTADO 2027 bajo el escenario: {proy or '—'}")
    if base and proy and base != proy:
        lines.append(f"  → MIGRACIÓN detectada: {base} → {proy}")
    scores = payload.get("scores") or {}
    if scores:
        lines.append("")
        lines.append("SCORES por arquetipo (mayor = más probable):")
        for k in sorted(scores.keys(), key=lambda x: -scores[x]):
            lines.append(f"  · {k}: {scores[k]:+.2f}")
    migs = payload.get("migraciones_top") or []
    if migs:
        lines.append("")
        lines.append(f"MIGRACIONES TOP (territorios que cambian):")
        for m in migs[:8]:
            lines.append(f"  · {m.get('lugar','?')}: {m.get('de','?')} → {m.get('a','?')}")
    af = payload.get("afinidad_carvalho_promedio")
    if af is not None:
        lines.append("")
        lines.append(f"AFINIDAD EQUIPO CARVALHO en el territorio: {af:+.2f} (−5 sin presencia, +5 base sólida)")
    lines.append("")
    lines.append("Devuelve recomendaciones para los 5 arquetipos.\nJSON:")
    return "\n".join(lines)

def _call_deepseek(payload):
    user_msg = _user_msg(payload)
    body = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
        "max_tokens": 2400,
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
    return json.loads(resp["choices"][0]["message"]["content"])

# ---- Handler ----
def handler(event, context):
    origin = (event.get("headers") or {}).get("origin") or (event.get("headers") or {}).get("Origin") or ""
    method = (event.get("requestContext", {}).get("http", {}) or {}).get("method") or event.get("httpMethod") or "POST"
    # Preflight
    if method == "OPTIONS":
        return _resp(204, {}, origin)
    # Origin check
    if STRICT_ORIGIN and origin and origin not in ALLOWED_ORIGINS:
        return _resp(403, {"error": "origin not allowed"}, origin)
    # Body
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64
        raw = base64.b64decode(raw).decode("utf-8")
    if len(raw) > MAX_BODY_BYTES:
        return _resp(413, {"error": "body too large"}, origin)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return _resp(400, {"error": "invalid json"}, origin)
    if not DEEPSEEK_API_KEY:
        return _resp(500, {"error": "DEEPSEEK_API_KEY no configurada"}, origin)
    # Cache check
    ck = _cache_key(payload)
    s3 = _s3_client()
    cache_path = f"{CACHE_PREFIX}/{ck}.json"
    try:
        obj = s3.get_object(Bucket=S3_BUCKET, Key=cache_path)
        cached = json.loads(obj["Body"].read())
        cached["cache_hit"] = True
        return _resp(200, cached, origin)
    except Exception:
        pass
    # Llamar DeepSeek
    try:
        rec = _call_deepseek(payload)
    except urllib.error.HTTPError as e:
        return _resp(502, {"error": "deepseek http error", "status": e.code}, origin)
    except Exception as e:
        return _resp(502, {"error": "deepseek failed", "detail": type(e).__name__}, origin)
    now = datetime.now(timezone.utc).isoformat()
    out = {
        "lectura_general": rec.get("lectura_general", ""),
        "escenario_resumido": rec.get("escenario_resumido", ""),
        "recomendaciones": rec.get("recomendaciones", {}),
        "modelo": DEEPSEEK_MODEL,
        "generado_en": now,
        "cache_hit": False,
        "prompt_version": PROMPT_VERSION,
    }
    # Write cache
    try:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=cache_path,
            Body=json.dumps(out, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
            CacheControl="public, max-age=600",
        )
    except Exception:
        pass
    return _resp(200, out, origin)


# ---- CLI helpers ----
if __name__ == "__main__":
    import sys
    if "--dry-run" in sys.argv:
        sample = {
            "level": "comuna",
            "territorio": "Robledo",
            "sliders": {"seguridad": -3, "electoral": -5, "costo_vida": -2, "empleo": -3, "afinidad_carvalho": 2},
            "arquetipo_base": "proteccion",
            "arquetipo_proyectado": "castigo",
            "scores": {"proteccion": 3.1, "castigo": 7.6, "continuidad": 1.2, "supervivencia": 4.1, "pertenencia": 0.8},
            "migraciones_top": [
                {"lugar": "Robledo", "de": "proteccion", "a": "castigo"},
                {"lugar": "Castilla", "de": "continuidad", "a": "supervivencia"},
            ],
            "afinidad_carvalho_promedio": 1.5,
        }
        if "--show-prompt" in sys.argv:
            print("=== SYSTEM ===")
            print(SYSTEM_PROMPT)
            print("\n=== USER ===")
            print(_user_msg(sample))
        else:
            r = _call_deepseek(sample)
            print(json.dumps(r, ensure_ascii=False, indent=2))
