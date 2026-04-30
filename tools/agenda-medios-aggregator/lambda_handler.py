#!/usr/bin/env python3
"""
agenda-medios-aggregator · lambda_handler.py

Lee los .jsonl crudos producidos por agenda-medios-rss y genera
agregados pequeños para que el frontend (proyecto-dc/agenda.html)
los consuma con un solo fetch por ventana.

Trigger: EventBridge cada 1 hora.

Salidas (todas en s3://elecciones-2026/ricardoruiz.co/proyecto-dc/agenda/agregados/):
    nube-{6h|24h|5d}.json       top 50 palabras + count
    medios-{6h|24h|5d}.json     volumen por medio
    titulares-{6h|24h|5d}.json  últimos 20 titulares de la ventana
"""

import os
import re
import sys
import json
import unicodedata
from collections import Counter
from datetime import datetime, timezone, timedelta

S3_BUCKET = os.environ.get("AGENDA_S3_BUCKET", "elecciones-2026")
S3_PREFIX = os.environ.get("AGENDA_S3_PREFIX", "ricardoruiz.co/proyecto-dc/agenda")
RAW_PREFIX = f"{S3_PREFIX}/raw/medios"
OUT_PREFIX = f"{S3_PREFIX}/agregados"

WINDOWS = {
    "6h":  timedelta(hours=6),
    "24h": timedelta(hours=24),
    "5d":  timedelta(days=5),
}
TOP_WORDS = 50
TOP_HEADLINES = 20
MIN_WORD_LEN = 4

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "stopwords-es.txt"), encoding="utf-8") as _f:
    STOPWORDS = {
        line.strip().lower()
        for line in _f
        if line.strip() and not line.lstrip().startswith("#")
    }

# Letras ES (con tildes y ñ). Tokens = secuencias de letras.
TOKEN_RE = re.compile(r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü]+")

_s3 = None
def _s3_client():
    global _s3
    if _s3 is None:
        import boto3
        _s3 = boto3.client("s3")
    return _s3


def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

def is_stopword(w: str) -> bool:
    if w in STOPWORDS:
        return True
    return strip_accents(w) in STOPWORDS

def tokenize(text: str):
    if not text:
        return []
    return [m.group().lower() for m in TOKEN_RE.finditer(text)]

def good_token(t: str) -> bool:
    if len(t) < MIN_WORD_LEN:
        return False
    if t.isdigit():
        return False
    if is_stopword(t):
        return False
    return True


def list_jsonl_for_days(s3, days):
    """Lista los keys .jsonl de raw/medios para los días dados (date objects)."""
    keys = []
    for d in days:
        prefix = f"{RAW_PREFIX}/yyyy={d.year:04d}/mm={d.month:02d}/dd={d.day:02d}/"
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


def read_events(s3, keys, cutoff_iso):
    """Lee y filtra eventos cuyo fecha_pub (o fecha_capturada como fallback)
    sea >= cutoff_iso. Deduplica por id."""
    seen_ids = set()
    out = []
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
            ts = ev.get("fecha_pub") or ev.get("fecha_capturada") or ""
            if ts < cutoff_iso:
                continue
            eid = ev.get("id")
            if not eid or eid in seen_ids:
                continue
            seen_ids.add(eid)
            out.append(ev)
    return out


def compute_words(events):
    """Top palabras: título cuenta x2, resumen cuenta x1."""
    counter = Counter()
    for ev in events:
        for tok in tokenize(ev.get("titulo") or ""):
            if good_token(tok):
                counter[tok] += 2
        for tok in tokenize(ev.get("resumen") or ""):
            if good_token(tok):
                counter[tok] += 1
    return counter.most_common(TOP_WORDS)


def compute_medios(events):
    c = Counter(ev.get("medio") for ev in events if ev.get("medio"))
    total = sum(c.values()) or 1
    return [
        {"medio": m, "n": n, "pct": round(n / total * 100, 1)}
        for m, n in c.most_common()
    ]


def compute_titulares(events):
    sorted_evs = sorted(
        events,
        key=lambda e: e.get("fecha_pub") or e.get("fecha_capturada") or "",
        reverse=True,
    )[:TOP_HEADLINES]
    return [
        {
            "titulo": e.get("titulo"),
            "medio":  e.get("medio"),
            "url":    e.get("url"),
            "fecha_pub": e.get("fecha_pub"),
        }
        for e in sorted_evs
    ]


def write_json(s3, name, body):
    key = f"{OUT_PREFIX}/{name}"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
        CacheControl="public, max-age=300",
    )
    return key


def run():
    s3 = _s3_client()
    now = datetime.now(timezone.utc)
    summary = {}

    # Días candidatos para listar S3: hoy + 5 hacia atrás (cubre 5d).
    today = now.date()
    days = [today - timedelta(days=i) for i in range(6)]
    keys = list_jsonl_for_days(s3, days)
    print(f"[run] {len(keys)} archivos jsonl en {len(days)} días")

    # Leer una sola vez todo lo que cae dentro de la ventana 5d
    cutoff_5d_iso = (now - WINDOWS["5d"]).isoformat()
    all_events = read_events(s3, keys, cutoff_5d_iso)
    print(f"[run] {len(all_events)} eventos únicos en últimos 5d")

    out_paths = []
    for win, delta in WINDOWS.items():
        cutoff_iso = (now - delta).isoformat()
        events = [
            e for e in all_events
            if (e.get("fecha_pub") or e.get("fecha_capturada") or "") >= cutoff_iso
        ]
        n_eventos = len(events)
        n_medios  = len({e.get("medio") for e in events})

        nube = {
            "ventana": win,
            "generado_en": now.isoformat(),
            "n_eventos": n_eventos,
            "n_medios": n_medios,
            "palabras": [{"w": w, "n": n} for w, n in compute_words(events)],
        }
        medios = {
            "ventana": win,
            "generado_en": now.isoformat(),
            "n_eventos": n_eventos,
            "medios": compute_medios(events),
        }
        titulares = {
            "ventana": win,
            "generado_en": now.isoformat(),
            "titulares": compute_titulares(events),
        }

        out_paths.append(write_json(s3, f"nube-{win}.json", nube))
        out_paths.append(write_json(s3, f"medios-{win}.json", medios))
        out_paths.append(write_json(s3, f"titulares-{win}.json", titulares))
        summary[win] = {"eventos": n_eventos, "palabras": len(nube["palabras"])}
        print(f"[{win}] eventos={n_eventos} top_words={len(nube['palabras'])}")

    return {
        "generado_en": now.isoformat(),
        "ventanas": summary,
        "salidas": out_paths,
    }


def handler(event, context):
    return run()


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
