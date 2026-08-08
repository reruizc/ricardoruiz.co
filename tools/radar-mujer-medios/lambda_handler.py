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


def _digest_dias():
    """Ventana de la LECTURA IA. Es más corta que la del tablero a propósito:
    los volúmenes y la nube quieren una semana para tener masa, pero la lectura
    del analista tiene que hablar de la coyuntura de estos días, no del promedio
    de la semana."""
    try:
        return max(1, int(os.environ.get("RADAR_DIGEST_DIAS", "2")))
    except ValueError:
        return 2


def build_tablero(agg, n_total, digest, ventana_dias, now, digest_dias=None):
    TL = report.TEMA_LABEL
    return {
        "generado_en": now.isoformat(),
        "ventana_dias": ventana_dias,
        "digest_dias": digest_dias or _digest_dias(),
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
    """Escribe tablero['redes'] con una captura nueva. Devuelve True si lo logró.

    ⚠️ El valor de retorno importa: si sale con False, el llamador tiene que
    conservar la sección de la corrida anterior. Sin eso, un día de 0 eventos
    BORRA las redes del tablero para siempre — y como el ciclo siguiente ya no
    encuentra nada que conservar, la pestaña entera desaparece sin avisar. Fue
    exactamente lo que pasó del 3 al 8 de agosto de 2026.
    """
    ventana = int(os.environ.get("RADAR_VENTANA_DIAS", "7"))
    events = collect_social.collect_social_events(now.isoformat())
    if not events:
        print("[redes] 0 eventos → conservo la captura anterior")
        return False
    if os.environ.get("RADAR_PERSIST_RAW", "1") == "1":
        try:
            _persist_raw(events, now, now.strftime("%Y%m%dT%H%M%SZ"))
        except Exception as e:
            print(f"[redes raw] {e}")
    events = report.filter_window(events, ventana)
    agg = report.aggregate_social(events)
    # La lectura IA mira solo la coyuntura; los volúmenes/nube siguen a 7 d.
    dd = _digest_dias()
    ev_dig = report.filter_window(events, dd)
    agg_dig = report.aggregate_social(ev_dig) if ev_dig else agg
    prompt = report.build_digest_prompt_social(agg_dig, len(ev_dig) or len(events), dd, now)
    digest = report.call_deepseek(prompt)
    sent_redes = None
    try:
        sent_redes = report.classify_sentiment(events)
    except Exception as e:
        print(f"[sentimiento redes] falló: {e}")
    RL = report.RED_LABEL
    tablero["redes"] = {
        # Sella CUÁNDO se scrapeó de verdad. Las redes no corren en todos los
        # ciclos (cuestan por resultado), así que sin esta marca la sección
        # conservada de una corrida anterior se lee como si fuera de hoy.
        "capturado": now.isoformat(),
        "n_posts": len(events),
        "digest_dias": dd,
        "n_posts_digest": len(ev_dig),
        "digest": digest,
        "sentimiento": sent_redes,
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
    return True


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

    # Ventana por fecha: Google News ya viene acotado (when:Nd) pero los
    # feeds directos entregan sus últimos posts sin importar antigüedad.
    events = report.filter_window(events, ventana)
    agg = report.aggregate(events)          # incluye cap por medio
    n_total = agg["n"]

    # Lectura IA sobre la COYUNTURA (2 d por defecto), no sobre toda la ventana.
    dd = _digest_dias()
    ev_dig = report.filter_window(events, dd)
    agg_dig = report.aggregate(ev_dig) if ev_dig else agg
    n_dig = agg_dig["n"] if ev_dig else n_total
    prompt = report.build_digest_prompt(agg_dig, n_dig, dd, now)
    digest = report.call_deepseek(prompt)  # usa DEEPSEEK_API_KEY del env
    if not digest:
        print("[digest] sin DeepSeek (¿falta DEEPSEEK_API_KEY?) → tablero sin lectura")

    tablero = build_tablero(agg, n_total, digest, ventana, now, dd)
    tablero["n_titulares_digest"] = n_dig

    # ── Sentimiento prensa (24h + 7d) ──
    try:
        sent = report.classify_sentiment(events)
        if sent:
            tablero["sentimiento"] = sent
            print(f"[sentimiento prensa] 7d={sent['7d']} 24h={sent['24h']}")
    except Exception as e:
        print(f"[sentimiento prensa] falló (sigo): {e}")

    # ── Capa REDES (Apify) · opcional: solo si hay token y el módulo cargó ──
    # RADAR_SOCIAL_HOURS ("12" o "0,12", horas UTC): las redes CUESTAN por
    # resultado, así que solo corren en los ciclos listados; en el resto se
    # conserva la sección redes de la última corrida (desde el propio S3).
    run_social = True
    hrs = os.environ.get("RADAR_SOCIAL_HOURS", "").strip()
    if hrs:
        allowed = {int(h) for h in hrs.split(",") if h.strip().isdigit()}
        run_social = now.hour in allowed
    hay_token = bool(os.environ.get("APIFY_TOKEN"))
    scraped = False
    if collect_social is not None and hay_token and run_social:
        try:
            scraped = bool(_add_redes(tablero, now))
        except Exception as e:
            print(f"[redes] falló (sigo solo con prensa): {e}")

    if not scraped:
        # Por qué no hay captura nueva. Se distingue el ciclo normal (hora fuera
        # de RADAR_SOCIAL_HOURS, varias veces al día) de la desconexión
        # deliberada, porque el tablero las muestra distinto: en la primera el
        # dato es de esta madrugada, en la segunda puede ser de hace semanas.
        if collect_social is None:
            motivo, corte = "modulo", "El módulo de redes no cargó en el Lambda."
        elif not hay_token:
            motivo, corte = "desconectado", ("La conexión con la fuente de redes está "
                                             "pausada. Vuelve a conectarse pronto.")
        elif not run_social:
            motivo, corte = "ciclo", f"Ciclo sin scraping (hora {now.hour} UTC)."
        else:
            motivo, corte = "sin_datos", ("La última consulta a la fuente de redes no "
                                          "devolvió publicaciones.")
        try:
            prev = json.loads(_s3c().get_object(Bucket=S3_BUCKET, Key=TABLERO_KEY)["Body"].read())
            r = dict(prev.get("redes") or {})
            if r:
                # Si venía de antes de que existiera `capturado`, se cae al sello
                # de la corrida anterior: la fecha queda bien aunque la hora no.
                # NUNCA se re-sella con `now`: sería decir que el dato es de ahora.
                r.setdefault("capturado", prev.get("generado_en"))
            r["pausado"] = motivo      # ciclo | desconectado | sin_datos | modulo
            r["pausado_nota"] = corte
            r.setdefault("n_posts", 0)
            tablero["redes"] = r
            print(f"[redes] {motivo} → {r.get('n_posts')} posts, capturados {r.get('capturado')}")
        except Exception as e:
            print(f"[redes] no pude conservar sección previa: {e}")
            tablero["redes"] = {"pausado": motivo, "pausado_nota": corte, "n_posts": 0}

    _s3c().put_object(
        Bucket=S3_BUCKET, Key=TABLERO_KEY,
        Body=json.dumps(tablero, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json", CacheControl="public, max-age=300")

    # ── Módulo de INFORMES (ventana larga) ──
    # Va DESPUÉS de escribir el tablero y en su propio try: lee el histórico ya
    # persistido en S3, así que no vuelve a golpear Google News ni Apify, y si
    # falla no puede dejar el tablero a medias. Se salta con RADAR_INFORME=0.
    informe_ok = False
    if os.environ.get("RADAR_INFORME", "1") == "1":
        try:
            import informe as informe_mod
            data = informe_mod.generar(now)
            informe_mod.escribir(data)
            informe_ok = any(v.get("informe") or v.get("informe_texto")
                             for v in data["ventanas"].values())
        except Exception as e:
            print(f"[informe] falló (sigo, el tablero ya quedó escrito): {type(e).__name__}: {e}")

    print(f"[radar-mujer {run_id}] titulares={n_total} temas={len(agg['por_tema'])} "
          f"medios={len(agg['por_medio'])} digest={'ok' if digest else 'no'} "
          f"(lectura sobre {dd} d) informe={'ok' if informe_ok else 'no'}")
    return {"run_id": run_id, "n_titulares": n_total, "digest": bool(digest),
            "digest_dias": dd, "informe": informe_ok}


if __name__ == "__main__":
    print(handler({}, None))
