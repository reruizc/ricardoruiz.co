#!/usr/bin/env python3
"""
test-presidencial-dashboard-agg · lambda_handler.py

Lambda agregadora del Test Presidencial 2026. Corre por EventBridge cada
5 min. Lee los eventos anónimos que escribe `test-presidencial-explica`
en S3 (responses/yyyy=Y/mm=M/dd=D/*.json) y produce un único
`dashboard/aggregates.json` (público) con los conteos segmentados por
scope: global, por medio (brand) y por territorio.

Privacy: los eventos NO traen PII (sin email, sin lat/lon, sin la lectura).
Solo señales: candidato, arquetipo, dep/mun, alineación, canal, ts.

Ventana: por defecto agrega los últimos VENTANA_DIAS=30 días + un
"stream" con los últimos STREAM_N=40 eventos (más recientes primero).

ENV:
  S3_BUCKET          default elecciones-2026
  RESPONSES_PREFIX   default ricardoruiz.co/test-presidencial-2026/responses
  OUT_KEY            default ricardoruiz.co/test-presidencial-2026/dashboard/aggregates.json
  VENTANA_DIAS       default 30
  STREAM_N           default 40
"""

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

S3_BUCKET = os.environ.get("S3_BUCKET", "elecciones-2026")
RESPONSES_PREFIX = os.environ.get("RESPONSES_PREFIX", "ricardoruiz.co/test-presidencial-2026/responses")
# Bajo congreso-2026/output/* — ese prefijo ya es público en la bucket policy
# (los prefijos privados de test-presidencial-2026/* dan 403 a anónimos).
OUT_KEY = os.environ.get("OUT_KEY", "ricardoruiz.co/congreso-2026/output/test-presidencial/dashboard/aggregates.json")
# Archivo geo separado — pesado/granular, el dashboard lo carga solo al
# pulsar "Ver mapa de Colombia" (lazy). Mantiene aggregates.json liviano.
OUT_KEY_GEO = os.environ.get("OUT_KEY_GEO", "ricardoruiz.co/congreso-2026/output/test-presidencial/dashboard/aggregates-geo.json")
VENTANA_DIAS = int(os.environ.get("VENTANA_DIAS", "30"))
STREAM_N = int(os.environ.get("STREAM_N", "40"))

CANDS = ["ic", "ae", "pv", "sf", "cl", "rb"]
ARQS = ["proteccion", "estabilidad", "supervivencia", "castigo", "pertenencia"]

_s3 = None
def _s3c():
    global _s3
    if _s3 is None:
        import boto3  # type: ignore
        _s3 = boto3.client("s3")
    return _s3


def _list_keys_for_window():
    """Lista las keys de los últimos VENTANA_DIAS, prefijo por día."""
    s3 = _s3c()
    keys = []
    today = datetime.now(timezone.utc).date()
    for d in range(VENTANA_DIAS):
        day = today - timedelta(days=d)
        prefix = f"{RESPONSES_PREFIX}/yyyy={day:%Y}/mm={day:%m}/dd={day:%d}/"
        token = None
        while True:
            kw = {"Bucket": S3_BUCKET, "Prefix": prefix, "MaxKeys": 1000}
            if token:
                kw["ContinuationToken"] = token
            resp = s3.list_objects_v2(**kw)
            for o in resp.get("Contents", []):
                keys.append(o["Key"])
            if resp.get("IsTruncated"):
                token = resp.get("NextContinuationToken")
            else:
                break
    return keys


def _read_event(key):
    try:
        obj = _s3c().get_object(Bucket=S3_BUCKET, Key=key)
        return json.loads(obj["Body"].read().decode("utf-8"))
    except Exception as e:
        print(f"[agg] WARN no se leyó {key}: {e}")
        return None


def _blank_scope():
    return {
        "total": 0,
        "candidato": Counter(),
        "arquetipo": Counter(),
        "cruce": defaultdict(Counter),       # cand -> arq -> n
        "vientos_cruzados": 0,
        "alineado": 0,
        "neutro": 0,
        "registro": Counter(),
        "por_mun": Counter(),                 # "dep-mun" -> n  (para top zonas)
        "mun_nombre": {},                     # "dep-mun" -> nombre
        "serie_dia": Counter(),               # YYYY-MM-DD -> n
        # Detalle geográfico completo (alimenta aggregates-geo.json / mapa)
        "geo_dep": {},                        # dep_cod -> {n,total,cand,arq}
        "geo_mun": {},                        # "dep-mun" -> {n,dep,total,cand,arq}
    }


def _accumulate(scope, ev):
    scope["total"] += 1
    c = ev.get("candidato")
    a = ev.get("arq_dom")
    if c:
        scope["candidato"][c] += 1
    if a:
        scope["arquetipo"][a] += 1
    if c and a:
        scope["cruce"][c][a] += 1
    al = ev.get("alineacion")
    if al == "vientos_cruzados":
        scope["vientos_cruzados"] += 1
    elif al == "alineado":
        scope["alineado"] += 1
    elif al == "neutro":
        scope["neutro"] += 1
    if ev.get("registro"):
        scope["registro"][ev["registro"]] += 1
    dep, mun = ev.get("dep_cod"), ev.get("mun_cod")
    if dep and mun:
        mk = f"{dep}-{mun}"
        scope["por_mun"][mk] += 1
        if ev.get("mun_nombre"):
            scope["mun_nombre"][mk] = ev["mun_nombre"]
    # Geo detallado por depto y municipio (para el mapa)
    if dep:
        gd = scope["geo_dep"].setdefault(
            dep, {"n": None, "total": 0, "cand": Counter(), "arq": Counter()})
        gd["total"] += 1
        if ev.get("dep_nombre"):
            gd["n"] = ev["dep_nombre"]
        if c:
            gd["cand"][c] += 1
        if a:
            gd["arq"][a] += 1
        if mun:
            mk = f"{dep}-{mun}"
            gm = scope["geo_mun"].setdefault(
                mk, {"n": None, "dep": dep, "total": 0, "cand": Counter(), "arq": Counter()})
            gm["total"] += 1
            if ev.get("mun_nombre"):
                gm["n"] = ev["mun_nombre"]
            if c:
                gm["cand"][c] += 1
            if a:
                gm["arq"][a] += 1
    ts = ev.get("ts") or ""
    if len(ts) >= 10:
        scope["serie_dia"][ts[:10]] += 1


def _finalize(scope):
    total = scope["total"] or 0

    def pct(counter):
        s = sum(counter.values()) or 1
        return {k: round(100 * v / s, 1) for k, v in counter.items()}

    cand_top = scope["candidato"].most_common(1)
    arq_top = scope["arquetipo"].most_common(1)
    cross_total = scope["vientos_cruzados"] + scope["alineado"] + scope["neutro"]
    top_muns = scope["por_mun"].most_common(12)

    return {
        "total": total,
        "candidato_counts": dict(scope["candidato"]),
        "candidato_pct": pct(scope["candidato"]),
        "candidato_top": (cand_top[0][0] if cand_top else None),
        "arquetipo_counts": dict(scope["arquetipo"]),
        "arquetipo_pct": pct(scope["arquetipo"]),
        "arquetipo_top": (arq_top[0][0] if arq_top else None),
        "cruce": {c: dict(scope["cruce"][c]) for c in scope["cruce"]},
        "alineacion": {
            "vientos_cruzados": scope["vientos_cruzados"],
            "alineado": scope["alineado"],
            "neutro": scope["neutro"],
            "vientos_cruzados_pct": round(100 * scope["vientos_cruzados"] / cross_total, 1) if cross_total else 0,
        },
        "registro_counts": dict(scope["registro"]),
        "top_municipios": [
            {"mun": mk, "nombre": scope["mun_nombre"].get(mk, mk), "n": n}
            for mk, n in top_muns
        ],
        "serie_dia": dict(sorted(scope["serie_dia"].items())),
    }


def _finalize_geo(scope):
    """Detalle geográfico completo para el mapa: TODOS los deptos y muns
    (no solo el top 12). cand_top/arq_top pre-calculados."""
    def pack(d):
        out = {}
        for code, v in d.items():
            cand = v["cand"]; arq = v["arq"]
            ct = cand.most_common(1)
            at = arq.most_common(1)
            row = {
                "n": v.get("n") or code,
                "total": v["total"],
                "cand_top": ct[0][0] if ct else None,
                "arq_top": at[0][0] if at else None,
                "cand": dict(cand),
                "arq": dict(arq),
            }
            if "dep" in v:
                row["dep"] = v["dep"]
            out[code] = row
        return out
    return {
        "por_dep": pack(scope["geo_dep"]),
        "por_mun": pack(scope["geo_mun"]),
    }


def handler(event, context):
    keys = _list_keys_for_window()
    print(f"[agg] {len(keys)} eventos en ventana de {VENTANA_DIAS} días")

    g = _blank_scope()
    by_brand = defaultdict(_blank_scope)
    by_terr = defaultdict(_blank_scope)
    stream = []

    for k in keys:
        ev = _read_event(k)
        if not ev:
            continue
        _accumulate(g, ev)
        canal = ev.get("canal") or {}
        brand = canal.get("brand")
        terr = canal.get("territorio")
        if brand:
            _accumulate(by_brand[brand], ev)
        if terr:
            _accumulate(by_terr[terr], ev)
        stream.append({
            "ts": ev.get("ts"),
            "candidato": ev.get("candidato"),
            "arq_dom": ev.get("arq_dom"),
            "mun_nombre": ev.get("mun_nombre"),
            "barrio": ev.get("barrio"),
            "brand": brand,
            "territorio": terr,
            "alineacion": ev.get("alineacion"),
        })

    stream.sort(key=lambda x: x.get("ts") or "", reverse=True)

    out = {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "ventana_dias": VENTANA_DIAS,
        "cands": CANDS,
        "arqs": ARQS,
        "all": _finalize(g),
        "por_brand": {b: _finalize(s) for b, s in by_brand.items()},
        "por_territorio": {t: _finalize(s) for t, s in by_terr.items()},
        "stream": stream[:STREAM_N],
    }

    body = json.dumps(out, ensure_ascii=False)
    try:
        _s3c().put_object(
            Bucket=S3_BUCKET, Key=OUT_KEY,
            Body=body.encode("utf-8"),
            ContentType="application/json",
            CacheControl="public, max-age=120",
        )
    except Exception as e:
        print(f"[agg] WARN no se escribió S3 (aggregates): {e}")

    # Archivo geo separado (lazy en el dashboard)
    geo_out = {
        "generado_en": out["generado_en"],
        "ventana_dias": VENTANA_DIAS,
        "cands": CANDS,
        "arqs": ARQS,
        **_finalize_geo(g),
    }
    try:
        _s3c().put_object(
            Bucket=S3_BUCKET, Key=OUT_KEY_GEO,
            Body=json.dumps(geo_out, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
            CacheControl="public, max-age=120",
        )
    except Exception as e:
        print(f"[agg] WARN no se escribió S3 (geo): {e}")
    print(f"[agg] total={out['all']['total']} "
          f"brands={list(out['por_brand'])} terrs={list(out['por_territorio'])} "
          f"deps={len(geo_out['por_dep'])} muns={len(geo_out['por_mun'])}")

    # Si fue invocada por Function URL (HTTP) devolver el JSON con CORS;
    # EventBridge ignora la respuesta.
    is_http = isinstance(event, dict) and (
        "requestContext" in event or "rawPath" in event or "http" in (event.get("requestContext") or {})
    )
    if is_http:
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=120",
            },
            "body": body,
        }
    return {"ok": True, "total": out["all"]["total"], "keys": len(keys)}


if __name__ == "__main__":
    print(json.dumps(handler({}, None), indent=2, ensure_ascii=False))
