#!/usr/bin/env python3
"""
radar-mujer-medios · lambda_handler.py

Lambda del monitor de medios de Radar Mujer (MxD). En cada corrida:
  1. Recolecta la ventana completa (Google News when:Nd + feeds directos).
  2. (opcional) persiste el crudo JSONL a S3 para histórico.
  3. Agrega: volumen por tema, medios, nube de términos, titulares por tema.
  4. Llama a DeepSeek para la lectura del analista (key en env).
  5. Escribe agenda-mujer.json en el prefijo público del observatorio.

Trigger: EventBridge (cada 6 h sugerido).

Reusa collect.py (collect_events) y report.py (aggregate + build_digest_prompt).
Stateless: cada corrida reconstruye la ventana de N días — el tablero siempre
muestra lo último, sin depender de corridas previas.

Env vars:
  DEEPSEEK_API_KEY    (requerida para el digest; sin ella el tablero sale sin lectura)
  DEEPSEEK_MODEL      (default deepseek-v4-flash)
  RADAR_VENTANA_DIAS  (default 7)
  RADAR_PERSIST_RAW   ("1" para guardar crudo JSONL histórico; default "1")
"""

import os
import json
from datetime import datetime, timezone

import collect
import report
try:
    import collect_social
except Exception:
    collect_social = None

S3_BUCKET = os.environ.get("RADAR_S3_BUCKET", "elecciones-2026")
RAW_PREFIX = os.environ.get("RADAR_S3_PREFIX", "ricardoruiz.co/radar-mujer/medios")
# Prefijo público que lee el tablero (agenda-mujer.html). Espacio literal en la key.
TABLERO_KEY = "ricardoruiz.co/bases de datos/output_observatorio_mujer/agenda-mujer.json"

_s3 = None
def _s3c():
    global _s3
    if _s3 is None:
        import boto3
        _s3 = boto3.client("s3")
    return _s3


def _persist_raw(events, now, run_id):
    by_fuente = {}
    for ev in events:
        by_fuente.setdefault(ev["fuente"], []).append(ev)
    for fuente, evs in by_fuente.items():
        key = (f"{RAW_PREFIX}/raw/mujer/yyyy={now:%Y}/mm={now:%m}/dd={now:%d}/"
               f"{fuente}__{run_id}.jsonl")
        body = "\n".join(json.dumps(e, ensure_ascii=False) for e in evs).encode("utf-8")
        _s3c().put_object(Bucket=S3_BUCKET, Key=key, Body=body,
                          ContentType="application/x-ndjson")


def build_tablero(agg, n_total, digest, ventana_dias, now):
    TL = report.TEMA_LABEL
    return {
        "generado_en": now.isoformat(),
        "ventana_dias": ventana_dias,
        "n_titulares": n_total,
        "n_medios": len(agg["por_medio"]),
        "n_temas": len(agg["por_tema"]),
        "digest": digest,
        "por_tema": [{"tema": t, "label": TL.get(t, t), "n": n}
                     for t, n in agg["por_tema"].most_common() if t != "(directo)"],
        "por_medio": [{"medio": m, "n": n} for m, n in agg["por_medio"].most_common(20)],
        "palabras": [{"w": w, "n": n} for w, n in agg["palabras"].most_common(50)],
        "titulares_por_tema": {
            t: [{"medio": e.get("medio"), "titulo": e.get("titulo"),
                 "fecha": (e.get("fecha_pub") or "")[:10], "url": e.get("url")}
                for e in agg["tema_titulares"][t][:6]]
            for t, _ in agg["por_tema"].most_common() if t != "(directo)"
        },
    }


def _add_redes(tablero, now):
    ventana = int(os.environ.get("RADAR_VENTANA_DIAS", "7"))
    events = collect_social.collect_social_events(now.isoformat())
    if not events:
        print("[redes] 0 eventos"); return
    if os.environ.get("RADAR_PERSIST_RAW", "1") == "1":
        try:
            _persist_raw(events, now, now.strftime("%Y%m%dT%H%M%SZ"))
        except Exception as e:
            print(f"[redes raw] {e}")
    agg = report.aggregate_social(events)
    prompt = report.build_digest_prompt_social(agg, len(events), ventana)
    digest = report.call_deepseek(prompt)
    RL = report.RED_LABEL
    tablero["redes"] = {
        "n_posts": len(events),
        "digest": digest,
        "por_red": [{"red": r, "label": RL.get(r, r), "n": n} for r, n in agg["por_red"].most_common()],
        "palabras": [{"w": w, "n": n} for w, n in agg["palabras"].most_common(50)],
        "por_cuenta": [{"cuenta": c, "n": n} for c, n in agg["por_cuenta"].most_common(15)],
        "top_posts": [
            {"red": e.get("red"), "label": RL.get(e.get("red"), e.get("red")),
             "autor": e.get("autor"), "texto": (e.get("titulo") or "")[:220],
             "url": e.get("url"), "metrica": report._metrica_num(e.get("metrica")),
             "fecha": (e.get("fecha_pub") or "")[:10]}
            for e in agg["top_posts"][:12]
        ],
    }
    print(f"[redes] posts={len(events)} por_red={dict(agg['por_red'])} digest={'ok' if digest else 'no'}")


def handler(event, context):
    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%dT%H%M%SZ")
    ventana = int(os.environ.get("RADAR_VENTANA_DIAS", "7"))

    events = collect.collect_events(now.isoformat())

    if os.environ.get("RADAR_PERSIST_RAW", "1") == "1":
        try:
            _persist_raw(events, now, run_id)
        except Exception as e:
            print(f"[raw] persist falló (sigo): {e}")

    agg = report.aggregate(events)
    n_total = len(events)

    prompt = report.build_digest_prompt(agg, n_total, ventana)
    digest = report.call_deepseek(prompt)  # usa DEEPSEEK_API_KEY del env
    if not digest:
        print("[digest] sin DeepSeek (¿falta DEEPSEEK_API_KEY?) → tablero sin lectura")

    tablero = build_tablero(agg, n_total, digest, ventana, now)

    # ── Capa REDES (Apify) · opcional: solo si hay token y el módulo cargó ──
    if collect_social is not None and os.environ.get("APIFY_TOKEN"):
        try:
            _add_redes(tablero, now)
        except Exception as e:
            print(f"[redes] falló (sigo solo con prensa): {e}")

    _s3c().put_object(
        Bucket=S3_BUCKET, Key=TABLERO_KEY,
        Body=json.dumps(tablero, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json", CacheControl="public, max-age=300")

    print(f"[radar-mujer {run_id}] titulares={n_total} temas={len(agg['por_tema'])} "
          f"medios={len(agg['por_medio'])} digest={'ok' if digest else 'no'}")
    return {"run_id": run_id, "n_titulares": n_total, "digest": bool(digest)}


if __name__ == "__main__":
    print(handler({}, None))
