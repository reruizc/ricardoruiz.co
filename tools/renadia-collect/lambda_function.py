"""
RENADIA · recolector de respuestas de la zona de juegos.

Recibe por POST (Lambda Function URL) el JSON de cada partida enviada por
RENADIA-unete-mundial-v3.html (sendBeacon → text/plain) y lo guarda en S3,
un objeto por respuesta. Sirve aunque el HTML esté embebido en la web del DNP
(el navegador manda el beacon cross-origin; la respuesta va con CORS abierto).

Salida en S3 (privado):
  renadia-collect/respuestas/YYYY/MM/DD/<juego>/<HHMMSS>_<rand>.json
"""
import json
import os
import uuid
import base64
import datetime
import boto3

s3 = boto3.client("s3")
BUCKET = os.environ.get("BUCKET", "elecciones-2026")
PREFIX = os.environ.get("PREFIX", "renadia-collect/respuestas")

CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Access-Control-Allow-Headers": "*",
}


def _resp(code, body):
    h = {"Content-Type": "application/json"}
    h.update(CORS)
    return {"statusCode": code, "headers": h, "body": json.dumps(body)}


def handler(event, context):
    http = (event.get("requestContext", {}) or {}).get("http", {}) or {}
    method = http.get("method", "POST")
    if method == "OPTIONS":
        return _resp(204, {})

    raw = event.get("body") or ""
    if event.get("isBase64Encoded"):
        try:
            raw = base64.b64decode(raw).decode("utf-8", "replace")
        except Exception:
            pass
    try:
        data = json.loads(raw) if raw else {}
    except Exception:
        data = {"_raw": raw[:5000]}
    if not isinstance(data, dict):
        data = {"_valor": data}

    # --- filtro anti-bot: solo guardamos partidas válidas ---
    # (los escáneres mandan POST vacíos o sin estructura; se responden 200 pero NO se guardan)
    JUEGOS_OK = ("carta", "madurez", "penaltis")
    juego = str(data.get("juego", ""))
    if juego not in JUEGOS_OK or not isinstance(data.get("respuestas"), list):
        return _resp(200, {"ok": True, "skipped": True})

    now = datetime.datetime.utcnow()
    data["_recibido"] = now.isoformat() + "Z"
    data["_ip"] = http.get("sourceIp", "")

    juego = juego[:24].replace("/", "_").replace("..", "")
    key = "{}/{}/{}/{}/{}/{}_{}.json".format(
        PREFIX, now.strftime("%Y"), now.strftime("%m"), now.strftime("%d"),
        juego or "otro", now.strftime("%H%M%S"), uuid.uuid4().hex[:8],
    )
    try:
        s3.put_object(
            Bucket=BUCKET, Key=key,
            Body=json.dumps(data, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )
    except Exception as e:  # noqa
        return _resp(500, {"ok": False, "error": str(e)})
    return _resp(200, {"ok": True})
