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
import re
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone

# ---- Config ----
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = os.environ.get("DEEPSEEK_URL", "https://api.deepseek.com/chat/completions")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
S3_BUCKET = os.environ.get("S3_BUCKET", "elecciones-2026")
CACHE_PREFIX = os.environ.get("CACHE_PREFIX", "ricardoruiz.co/test-presidencial-2026/cache")
HUELLA_KEY = os.environ.get("HUELLA_KEY", "ricardoruiz.co/test-presidencial-2026/huella/huella-territorial.json")
CACHE_TTL_DIAS = int(os.environ.get("CACHE_TTL_DIAS", "14"))
HTTP_TIMEOUT = 55

# Nombre canonico de los 6 candidatos (para la huella)
CAND_NOMBRES = {
    "ic": "Iván Cepeda",
    "ae": "Abelardo de la Espriella",
    "pv": "Paloma Valencia",
    "sf": "Sergio Fajardo",
    "cl": "Claudia López",
    "rb": "Roy Barreras",
}

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json; charset=utf-8",
}

# Tono por registro.
TONO = {
    "popular": "coloquial colombiano, frases cortas. Muletillas suaves OK ('pues', 'la verdad').",
    "digital": "irónico, formato POV, máximo 1 emoji por párrafo.",
    "analitico": "neutro elevado, vocabulario político preciso, frases completas.",
}

# Tono regional según el departamento. Sobrepone el default del registro.
TONO_REGIONAL = {
    "voseo_paisa": "voseo paisa colombiano ('vos pensás', 'sabés', 'querés'). Paisa de Medellín/Eje Cafetero.",
    "voseo_caleño": "voseo caleño/vallecaucano ('vos sabés', 'mirá vos', 've').",
    "ustedeo_boyacense": "ustedeo formal boyacense ('usted dice', 'lo que usted siente'). NO tutees.",
    "tuteo_costeño": "tuteo costeño relajado ('tú dices', 'ajá').",
    "tuteo_neutro": "tuteo neutro colombiano de Bogotá ('tú dices', 'tú sientes').",
}

SYSTEM_PROMPT = """Eres un analista electoral colombiano que ayuda a un ciudadano a entender el resultado de un test de arquetipo emocional para la presidencial 2026. Recibes un STATE con candidato declarado, demografía, ubicación con tono regional, prioridad temática y arquetipo dominante.

Tu trabajo: REDACTAR una lectura diagnóstica honesta. No inventas datos. No mencionas otros candidatos. No recomiendas voto.

Devuelves JSON estricto:
{
  "lectura": "Dos párrafos de 70-90 palabras cada uno, separados por \\n\\n. (1) Lo que el usuario declaró + lo que arrojó su arquetipo. (2) El contraste con su barrio: cómo se compara su declaración con la huella histórica del territorio. Sin alarmar.",
  "mensaje_corto": "Frase de 12-18 palabras para meme o redes.",
  "alineacion": "alineado" | "vientos_cruzados" | "neutro"
}

REGLAS:
1. Adapta el lenguaje al 'tono_regional' del STATE. NUNCA uses voseo argentino, 'che' ni vocabulario argentino.
2. Honra el REGISTRO (popular/digital/analítico).
3. Si el candidato fue 'sugerido' por el mini-test, dilo.
4. Si hay arquetipo secundario fuerte (>20%), menciónalo como matiz.
5. Solo el JSON, sin markdown ni texto extra.
6. Si hay bloque HUELLA TERRITORIAL en el STATE, INCORPÓRALO como evidencia objetiva en el segundo párrafo. Son datos REALES de elecciones pasadas + la consulta más reciente, agregados al barrio del usuario. NO los presentes como predicción ni los inventes. Cita 1-2 hechos concretos del bloque (ej: "tu barrio votó por X en 2022" o "tu candidato tiene huella Y× en tu barrio"). Si la huella del candidato declarado es < 0.85, es un barrio menos afín; si es > 1.20, es un barrio más afín; entre ambas, es neutro."""


# ---- AWS clients (lazy) ----
_s3 = None
def _s3_client():
    global _s3
    if _s3 is None:
        import boto3  # type: ignore
        _s3 = boto3.client("s3")
    return _s3


# ---- Huella territorial (cache por contenedor warm) ----
_huella = None

def _slug(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()


def _pad2(s):
    s = str(s or "").strip()
    return s.zfill(2) if s else "00"


def _pad3(s):
    s = str(s or "").strip()
    return s.zfill(3) if s else "000"


def _load_huella():
    """Carga huella-territorial.json desde S3, cachea en memoria del contenedor warm."""
    global _huella
    if _huella is not None:
        return _huella
    try:
        obj = _s3_client().get_object(Bucket=S3_BUCKET, Key=HUELLA_KEY)
        _huella = json.loads(obj["Body"].read().decode("utf-8"))
        print(f"[huella] cargada: {_huella.get('n_barrios')} barrios, {_huella.get('n_muns')} muns")
    except Exception as e:
        print(f"[huella] WARN no cargo: {e}")
        _huella = {}
    return _huella


def _resolver_huella(huella, ubi):
    """Dado state.ubicacion, devuelve (entry | None, level)."""
    if not huella or not ubi:
        return None, None
    dep_cod = ubi.get("dep_cod")
    mun_cod = ubi.get("mun_cod")
    if not dep_cod:
        return None, None
    mun_key = f"{_pad2(dep_cod)}-{_pad3(mun_cod)}"

    barrio_raw = (ubi.get("barrio") or "").strip()
    comuna_raw = (ubi.get("comuna") or "").strip()
    barrios = huella.get("barrios") or {}

    if barrio_raw and barrios:
        barrio_slug = _slug(barrio_raw)
        comuna_slug = _slug(comuna_raw) if comuna_raw else None
        candidates = []
        for bk, entry in barrios.items():
            if entry.get("mun") != mun_key:
                continue
            parts = bk.split("::")
            if len(parts) != 3:
                continue
            _, sub_slug, bar_slug = parts
            if bar_slug != barrio_slug:
                continue
            score = 2 if (comuna_slug and sub_slug == comuna_slug) else 1
            candidates.append((score, bk, entry))
        if candidates:
            candidates.sort(reverse=True, key=lambda x: x[0])
            return candidates[0][2], "barrio"

    mun_entry = (huella.get("muns") or {}).get(mun_key)
    if mun_entry:
        return mun_entry, "mun"
    return None, None


def _interpretar_bias(b):
    if b is None:
        return "sin huella"
    if b > 1.20:
        return f"{b:.2f}× (barrio MÁS afín que el promedio nacional)"
    if b < 0.85:
        return f"{b:.2f}× (barrio MENOS afín que el promedio nacional)"
    return f"{b:.2f}× (barrio neutro)"


def _format_huella_block(entry, level, candidato_id):
    """Convierte la entry de huella en un bloque de texto para el prompt."""
    if not entry:
        return ""
    bias = entry.get("b") or {}
    h = entry.get("h") or {}
    nombre = entry.get("n") or "(sin nombre)"
    subloc = entry.get("subloc") or ""
    ciudad = entry.get("ciudad") or ""
    dep = entry.get("dep") or ""
    censo = entry.get("censo") or 0
    puestos = entry.get("puestos") or 0

    if level == "barrio":
        ubic_str = f"{nombre} ({subloc} · {ciudad}, {dep})" if subloc else f"{nombre} ({ciudad}, {dep})"
        unidad = "barrio"
    else:
        ubic_str = f"{nombre} ({dep})"
        unidad = "municipio"

    p22 = h.get("p22") or {}
    c25p = h.get("c25p") or {}
    s26 = h.get("s26") or {}
    c26 = h.get("c26")
    consulta_nombres = {"gran": "Gran Consulta (derecha)", "frente": "Frente por la Vida (centro-izq)", "soluciones": "Consulta de Soluciones (centro)"}

    lines = [
        f"HUELLA TERRITORIAL del {unidad} del usuario (datos reales agregados a su zona, no inventes nada de aquí):",
        f"- Ubicación: {ubic_str}",
        f"- Censo electoral: {censo:,} electores en {puestos} puestos",
    ]
    if p22.get("n"):
        lines.append(f"- Top presidencial 2022 en su {unidad}: {p22['n']} con {p22.get('pct',0)}%")
    if c25p.get("n"):
        lines.append(f"- Top consulta Pacto Histórico 2025: {c25p['n']} con {c25p.get('pct',0)}%")
    if c26 and c26 in consulta_nombres:
        lines.append(f"- Consulta 2026 más votada en su zona: {consulta_nombres[c26]}")
    if s26.get("n"):
        lines.append(f"- Top partido senado 2026: {s26['n']} con {s26.get('pct',0)}%")

    lines.append("")
    lines.append("Huella afín de los 6 candidatos (1.00 = igual al promedio nacional; >1 = MÁS afín; <1 = MENOS afín):")
    for cid in ["ic", "ae", "pv", "sf", "cl", "rb"]:
        b = bias.get(cid)
        nombre_c = CAND_NOMBRES[cid]
        marcador = " ← CANDIDATO DECLARADO" if cid == candidato_id else ""
        if b is None:
            lines.append(f"- {nombre_c}: sin dato{marcador}")
        else:
            lines.append(f"- {nombre_c}: {b:.2f}×{marcador}")

    b_declarado = bias.get(candidato_id)
    if b_declarado is not None:
        lines.append("")
        lines.append(f"Lectura del candidato declarado en su {unidad}: {_interpretar_bias(b_declarado)}")

    return "\n".join(lines)


# ---- Cache ----
def _cache_key(state):
    """Hash determinista del state, ignorando órdenes irrelevantes (lista de prio).
    Incluye tono_regional + barrio/mun para que dos usuarios en barrios distintos
    del mismo dep no compartan cache (cada uno recibe su huella territorial)."""
    ubi = state.get("ubicacion") or {}
    canon = {
        "registro": state.get("registro"),
        "candidato_id": (state.get("candidato") or {}).get("id"),
        "candidato_origen": state.get("candidato_origen"),
        "edad": (state.get("demografia") or {}).get("edad"),
        "identidad": (state.get("demografia") or {}).get("identidad"),
        "tono_regional": ubi.get("tono_regional") or "tuteo_neutro",
        "dep_cod": ubi.get("dep_cod"),
        "mun_cod": ubi.get("mun_cod"),
        "barrio": _slug(ubi.get("barrio") or ""),
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
    ubi = state.get("ubicacion") or {}
    tono_reg_key = ubi.get("tono_regional") or "tuteo_neutro"
    tono_regional_instr = TONO_REGIONAL.get(tono_reg_key, TONO_REGIONAL["tuteo_neutro"])
    arq_dom = state.get("arquetipo_dominante") or {}
    arq_sec = state.get("arquetipo_secundario") or {}
    arq_score = state.get("arq_score") or {}
    prio = state.get("prio") or []

    ubi_linea = (
        f"{ubi.get('mun_nombre')}, {ubi.get('dep_nombre')}"
        if ubi.get("mun_nombre") else "sin declarar"
    )
    if ubi.get("barrio"):
        ubi_linea = f"{ubi.get('barrio')} · {ubi_linea}"

    # Resolver huella territorial del usuario
    huella = _load_huella()
    entry, level = _resolver_huella(huella, ubi)
    huella_block = _format_huella_block(entry, level, (cand.get("id") or "").lower()) if entry else ""

    user_msg = f"""STATE:
- Registro (tono): {registro} → {tono}
- Tono regional: {tono_reg_key} → {tono_regional_instr}
- Candidato declarado: {cand.get('nombre')} ({cand.get('partido')})
- Origen del candidato: {state.get('candidato_origen', 'declarado')}
- Edad: {demo.get('edad', 'sin dato')}
- Identidad cotidiana: {demo.get('identidad', 'sin dato')}
- Ubicación: {ubi_linea}
- Prioridades temáticas: {', '.join(prio) if prio else 'sin declarar'}
- Arquetipo dominante: {arq_dom.get('nombre')} ({arq_dom.get('pct')}%)
- Arquetipo secundario: {arq_sec.get('nombre')} ({arq_sec.get('pct')}%)
- Distribución completa: {json.dumps(arq_score, ensure_ascii=False)}
"""
    if huella_block:
        user_msg += "\n" + huella_block + "\n"
    user_msg += "\nRedacta la lectura en JSON estricto. RECUERDA: usa el tono regional indicado arriba (NO voseo argentino). Si hay HUELLA TERRITORIAL arriba, úsala en el segundo párrafo como evidencia objetiva."

    body = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
        # DeepSeek V4 consume tokens en reasoning_content interno antes
        # de generar el content. El bloque de huella territorial sumó
        # ~400 tokens al prompt; en casos de vientos cruzados el reasoning
        # llega a 4000-5000. 8000 cubre con margen reasoning + content.
        "max_tokens": 8000,
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
