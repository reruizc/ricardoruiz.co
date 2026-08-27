"""Recolector y API administrativa de Brújula Asunción.

POST /respuesta: guarda un registro anónimo saneado por finalización.
GET /admin/respuestas: devuelve registros solo a usuarios isAdmin de rr-auth.
"""
import base64
import datetime as dt
import json
import os
import uuid
import urllib.request
import urllib.error

import boto3

BUCKET = os.environ.get("BUCKET", "elecciones-2026")
PREFIX = os.environ.get("PREFIX", "ricardoruiz.co/brujula-asuncion/respuestas")
AUTH_ME = os.environ.get("AUTH_ME", "https://rr-auth.reruizc.workers.dev/auth/me")
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "https://ricardoruiz.co")
MAX_ADMIN_ROWS = int(os.environ.get("MAX_ADMIN_ROWS", "10000"))
s3 = boto3.client("s3")

CANDIDATOS = {"camilo", "soledad", "none"}
LENGUAJES = {"informada", "popular"}
EDADES = {"18_24", "25_34", "35_44", "45_59", "60_mas"}
CANALES = {"ig", "x", "fb", "tt", "rd"}


def response(code, body, origin=None):
    allow = origin if origin == ALLOWED_ORIGIN else ALLOWED_ORIGIN
    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Access-Control-Allow-Origin": allow,
            "Access-Control-Allow-Methods": "POST,GET,OPTIONS",
            "Access-Control-Allow-Headers": "Authorization,Content-Type",
            "Vary": "Origin",
            "Cache-Control": "no-store",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }


def clean_str(value, allowed=None, cap=100):
    if not isinstance(value, str):
        return None
    value = value.strip()[:cap]
    return value if value and (allowed is None or value in allowed) else None


def sanitize(data):
    if not isinstance(data, dict):
        return None
    answers = data.get("respuestas")
    if not isinstance(answers, dict):
        return None
    clean_answers = {}
    for code, value in list(answers.items())[:120]:
        if isinstance(code, str) and len(code) <= 6 and isinstance(value, int) and 0 <= value <= 5:
            clean_answers[code] = value
    if not clean_answers:
        return None
    affinities = {}
    raw_aff = data.get("afinidades")
    if isinstance(raw_aff, dict):
        for candidate in ("camilo", "soledad"):
            value = raw_aff.get(candidate)
            if isinstance(value, (int, float)) and 0 <= value <= 100:
                affinities[candidate] = round(float(value), 1)
    topics = data.get("temas")
    topics = [x for x in topics[:2] if isinstance(x, int) and 1 <= x <= 12] if isinstance(topics, list) else []
    zone = data.get("zona")
    zone = zone if isinstance(zone, int) and 1 <= zone <= 20 else None
    out = {
        "schema": 1,
        "version": clean_str(data.get("version"), cap=30),
        "lenguaje": clean_str(data.get("lenguaje"), LENGUAJES),
        "candidato_declarado": clean_str(data.get("candidato_declarado"), CANDIDATOS),
        "edad": clean_str(data.get("edad"), EDADES),
        "canal": clean_str(data.get("canal"), CANALES),
        "temas": topics,
        "zona": zone,
        "barrio": clean_str(data.get("barrio"), cap=80),
        "respuestas": clean_answers,
        "afinidades": affinities,
        "candidato_afin": clean_str(data.get("candidato_afin"), {"camilo", "soledad"}),
        "empate": bool(data.get("empate")),
    }
    return out


def is_admin(token):
    if not token:
        return False
    req = urllib.request.Request(AUTH_ME, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            body = json.loads(res.read().decode("utf-8"))
        return bool((body.get("user") or {}).get("isAdmin"))
    except (urllib.error.URLError, ValueError, TimeoutError):
        return False


def list_records():
    rows, token = [], None
    while len(rows) < MAX_ADMIN_ROWS:
        kwargs = {"Bucket": BUCKET, "Prefix": PREFIX.rstrip("/") + "/"}
        if token:
            kwargs["ContinuationToken"] = token
        page = s3.list_objects_v2(**kwargs)
        for obj in page.get("Contents", []):
            if len(rows) >= MAX_ADMIN_ROWS:
                break
            try:
                raw = s3.get_object(Bucket=BUCKET, Key=obj["Key"])["Body"].read()
                row = json.loads(raw)
                rows.append(row)
            except Exception:
                continue
        if not page.get("IsTruncated"):
            break
        token = page.get("NextContinuationToken")
    rows.sort(key=lambda x: x.get("ts_server", ""), reverse=True)
    return rows


def handler(event, context):
    http = (event.get("requestContext") or {}).get("http") or {}
    method = http.get("method", "POST")
    path = http.get("path") or event.get("rawPath") or "/respuesta"
    headers = {str(k).lower(): v for k, v in (event.get("headers") or {}).items()}
    origin = headers.get("origin")
    if method == "OPTIONS":
        return response(204, {}, origin)

    if method == "POST" and path.endswith("/respuesta"):
        raw = event.get("body") or ""
        if event.get("isBase64Encoded"):
            raw = base64.b64decode(raw).decode("utf-8", "replace")
        if len(raw) > 30000:
            return response(413, {"ok": False, "error": "too_big"}, origin)
        try:
            clean = sanitize(json.loads(raw))
        except (ValueError, TypeError):
            clean = None
        if not clean:
            return response(400, {"ok": False, "error": "bad_payload"}, origin)
        now = dt.datetime.now(dt.timezone.utc)
        clean["ts_server"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        key = f"{PREFIX.rstrip('/')}/{now:%Y/%m/%d}/{now:%Y%m%dT%H%M%SZ}_{uuid.uuid4().hex[:10]}.json"
        s3.put_object(Bucket=BUCKET, Key=key,
                      Body=json.dumps(clean, ensure_ascii=False).encode("utf-8"),
                      ContentType="application/json")
        return response(200, {"ok": True}, origin)

    if method == "GET" and path.endswith("/admin/respuestas"):
        auth = headers.get("authorization", "")
        token = auth[7:] if auth.lower().startswith("bearer ") else ""
        if not is_admin(token):
            return response(403, {"ok": False, "error": "forbidden"}, origin)
        rows = list_records()
        return response(200, {"ok": True, "total": len(rows), "respuestas": rows}, origin)

    return response(404, {"ok": False, "error": "not_found"}, origin)
