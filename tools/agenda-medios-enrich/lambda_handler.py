#!/usr/bin/env python3
"""
agenda-medios-enrich · lambda_handler.py

Capa de inteligencia del módulo 07. Lee los eventos crudos del módulo 07
y los enriquece con:
- actores políticos mencionados (de una lista curada con alias)
- clasificación de tema (taxonomía cerrada)
- sentimiento (positivo / neutro / negativo)

Usa DeepSeek V3 (https://platform.deepseek.com/), ~10× más barato
que Claude Haiku para la misma calidad. Costo esperado: ~$2-5/mes
para 600 eventos/día con prompt caching activo.

Trigger: EventBridge cada 1 hora (offset, p.ej. :20).

Pipeline:
1. Lista raw/medios/.../jsonl de últimos LOOKBACK_DAYS días.
2. Carga state/enrich.json con IDs ya enriquecidos.
3. Por cada evento NUEVO (cap MAX_EVENTS_PER_RUN):
   - Llama DeepSeek con titulo + resumen.
   - Recibe JSON {actores, tema, sentimiento}.
4. Escribe enriched/yyyy=Y/mm=M/dd=D/{run_id}.jsonl.
5. Actualiza state.

ENV requerida:
- DEEPSEEK_API_KEY: API key de https://platform.deepseek.com/api_keys
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

# ---- Config ----
S3_BUCKET = os.environ.get("AGENDA_S3_BUCKET", "elecciones-2026")
S3_PREFIX = os.environ.get("AGENDA_S3_PREFIX", "ricardoruiz.co/proyecto-dc/agenda")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = os.environ.get("DEEPSEEK_URL", "https://api.deepseek.com/chat/completions")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")  # = DeepSeek V3
HTTP_TIMEOUT = 30
LOOKBACK_DAYS = 6
MAX_EVENTS_PER_RUN = 200  # cap por seguridad y para que la Lambda no se cuelgue

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "actores.json"), encoding="utf-8") as _f:
    ACTORES = json.load(_f)
with open(os.path.join(_HERE, "temas.json"), encoding="utf-8") as _f:
    TEMAS = json.load(_f)

_s3 = None
def _s3_client():
    global _s3
    if _s3 is None:
        import boto3  # type: ignore
        _s3 = boto3.client("s3")
    return _s3


# ---- Prompt construction (estable → maximiza cache hits) ----
def _build_system_prompt():
    actores_lines = []
    for a in ACTORES:
        aliases = ", ".join(a.get("alias", []))
        actores_lines.append(f"- {a['nombre_canonico']} — {a['rol']}. Alias: {aliases}")

    temas_lines = []
    for t in TEMAS:
        temas_lines.append(f"- {t['id']}: {t['nombre']} ({t['ejemplos']})")

    return f"""Eres un analista político especializado en Medellín, Colombia. Te paso titulares y resúmenes de noticias.

Devuelves JSON estricto con esta estructura exacta:
{{
  "actores": ["nombre canónico 1", "nombre canónico 2"],
  "tema": "id_tema",
  "sentimiento": "positivo" | "neutro" | "negativo"
}}

REGLAS:
1. "actores" SOLO contiene nombres de la lista de ACTORES CONOCIDOS abajo, usando el "nombre canónico" exacto. Vacío [] si no hay menciones claras. NUNCA inventes nombres.
2. "tema" es UNO solo de los IDs en TEMAS abajo. Usa "otros" si no encaja en ninguno.
3. "sentimiento" sobre el tema o actor principal: cómo presenta la noticia el asunto. Neutro por defecto si no es claro.

ACTORES CONOCIDOS:
{chr(10).join(actores_lines)}

TEMAS:
{chr(10).join(temas_lines)}

Responde SOLO el JSON, sin texto adicional ni markdown."""

SYSTEM_PROMPT = _build_system_prompt()


# ---- DeepSeek call ----
def call_deepseek(titulo: str, resumen: str):
    user_msg = f"TITULAR: {titulo}\nRESUMEN: {(resumen or '')[:600]}\n\nJSON:"
    body = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "max_tokens": 250,
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
def list_raw_for_days(s3, days):
    keys = []
    for d in days:
        prefix = f"{S3_PREFIX}/raw/medios/yyyy={d.year:04d}/mm={d.month:02d}/dd={d.day:02d}/"
        token = None
        while True:
            kw = {"Bucket": S3_BUCKET, "Prefix": prefix}
            if token:
                kw["ContinuationToken"] = token
            resp = s3.list_objects_v2(**kw)
            for obj in resp.get("Contents", []):
                if obj["Key"].endswith(".jsonl"):
                    keys.append(obj["Key"])
            if not resp.get("IsTruncated"):
                break
            token = resp.get("NextContinuationToken")
    return keys


def state_key():
    return f"{S3_PREFIX}/state/enrich.json"

def load_state():
    try:
        obj = _s3_client().get_object(Bucket=S3_BUCKET, Key=state_key())
        data = json.loads(obj["Body"].read())
        return set(data.get("enriched_ids", []))
    except Exception as e:
        msg = str(e)
        if "NoSuchKey" in msg or "404" in msg:
            return set()
        print(f"[state] load failed: {e}")
        return set()

def save_state(enriched_ids):
    body = json.dumps({
        "enriched_ids": sorted(enriched_ids),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }, ensure_ascii=False).encode("utf-8")
    _s3_client().put_object(
        Bucket=S3_BUCKET, Key=state_key(),
        Body=body, ContentType="application/json",
    )

def write_enriched(events, run_id, now):
    if not events:
        return None
    key = (
        f"{S3_PREFIX}/enriched/yyyy={now:%Y}/mm={now:%m}/dd={now:%d}/"
        f"{run_id}.jsonl"
    )
    body = "\n".join(json.dumps(e, ensure_ascii=False) for e in events).encode("utf-8")
    _s3_client().put_object(
        Bucket=S3_BUCKET, Key=key,
        Body=body, ContentType="application/x-ndjson",
    )
    return key


# ---- Pipeline ----
def run():
    if not DEEPSEEK_API_KEY:
        return {"error": "DEEPSEEK_API_KEY env var no configurada"}

    s3 = _s3_client()
    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%dT%H%M%SZ")

    today = now.date()
    days = [today - timedelta(days=i) for i in range(LOOKBACK_DAYS)]
    keys = list_raw_for_days(s3, days)
    print(f"[run] {len(keys)} archivos raw en últimos {LOOKBACK_DAYS}d")

    enriched_ids = load_state()
    print(f"[run] {len(enriched_ids)} eventos ya enriquecidos en state")

    candidates = []
    for key in keys:
        try:
            body = s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"].read()
        except Exception as e:
            print(f"[read] FAIL {key}: {e}")
            continue
        for line in body.decode("utf-8").splitlines():
            if not line.strip():
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            eid = ev.get("id")
            if not eid or eid in enriched_ids:
                continue
            candidates.append(ev)

    print(f"[run] {len(candidates)} candidatos a enriquecer")

    if len(candidates) > MAX_EVENTS_PER_RUN:
        candidates.sort(
            key=lambda e: e.get("fecha_pub") or e.get("fecha_capturada") or "",
            reverse=True,
        )
        candidates = candidates[:MAX_EVENTS_PER_RUN]
        print(f"[run] cap aplicado, procesando {MAX_EVENTS_PER_RUN}")

    enriched = []
    errors = 0
    for ev in candidates:
        try:
            result = call_deepseek(ev.get("titulo", ""), ev.get("resumen", ""))
        except Exception as e:
            errors += 1
            print(f"[deepseek] FAIL {ev.get('id')}: {type(e).__name__}: {e}")
            continue
        enriched.append({
            "id": ev["id"],
            "actores": result.get("actores", []) or [],
            "tema": result.get("tema", "otros") or "otros",
            "sentimiento": result.get("sentimiento", "neutro") or "neutro",
            "enriquecido_en": now.isoformat(),
            "modelo": DEEPSEEK_MODEL,
        })
        enriched_ids.add(ev["id"])

    out_key = write_enriched(enriched, run_id, now)
    save_state(enriched_ids)

    summary = {
        "run_id": run_id,
        "candidatos": len(candidates),
        "enriquecidos": len(enriched),
        "errores": errors,
        "salida": out_key,
        "total_state": len(enriched_ids),
    }
    print(f"[run] {summary}")
    return summary


def handler(event, context):
    return run()


# ---- CLI ----
if __name__ == "__main__":
    if "--dry-run" in sys.argv:
        # Solo testea la llamada a DeepSeek con un evento sintético
        ev_titulo = "Federico Gutiérrez anuncia nuevo plan de seguridad para el centro de Medellín tras alza de homicidios"
        ev_resumen = "El alcalde presentó este lunes un paquete de medidas que incluye 200 nuevos policías, cámaras adicionales y un programa de jóvenes en riesgo. Daniel Quintero criticó el plan."
        print("=== Test prompt ===")
        result = call_deepseek(ev_titulo, ev_resumen)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif "--show-prompt" in sys.argv:
        print(SYSTEM_PROMPT)
    else:
        print(json.dumps(run(), ensure_ascii=False, indent=2))
