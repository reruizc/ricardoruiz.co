#!/usr/bin/env python3
"""
agenda-medios-rss · lambda_handler.py

Fase 1 del módulo 07 (agenda pública) — Proyecto DC.

Lee los 10 feeds RSS de medios antioqueños / con cobertura local
(definidos en feeds.json), deduplica contra un state.json en S3 y
escribe eventos normalizados como JSONL particionado por fecha.

Trigger esperado: EventBridge cada 30 min.

Layout S3 (bucket+prefix configurable por env):
    raw/medios/yyyy=YYYY/mm=MM/dd=DD/{medio}__{run_id}.jsonl
    state/medios.json

Esquema del evento (una línea JSON por artículo):
    {
      "id":              "hash24 de la url canónica",
      "medio":           "minuto30",
      "fuente":          "rss",
      "url":             "https://...",
      "url_canonica":    "https://... sin utm/fbclid/fragment",
      "titulo":          "...",
      "resumen":         "texto plano sin tags HTML",
      "fecha_pub":       "ISO 8601 con tz, o null",
      "fecha_capturada": "ISO 8601 UTC",
      "autor":           "...|null",
      "categorias":      ["..."],
      "raw_id":          "guid original del feed",
      "run_id":          "YYYYMMDDTHHMMSSZ"
    }

Test local:
    python3 lambda_handler.py --dry-run    # imprime eventos, no toca S3
    python3 lambda_handler.py --local      # escribe a ./_local_out/
"""

import os
import re
import sys
import json
import hashlib
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# ---- Config ----
S3_BUCKET = os.environ.get("AGENDA_S3_BUCKET", "elecciones-2026")
S3_PREFIX = os.environ.get("AGENDA_S3_PREFIX", "ricardoruiz.co/proyecto-dc/agenda")
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
HTTP_TIMEOUT = 15
MAX_SEEN_PER_FEED = 600  # IDs retenidos por feed en el state file

ATOM_NS = "{http://www.w3.org/2005/Atom}"
DC_NS = "{http://purl.org/dc/elements/1.1/}"
CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}"

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "feeds.json"), encoding="utf-8") as _f:
    FEEDS = json.load(_f)

# boto3 sólo se importa cuando vamos a tocar S3 (no en --dry-run)
_s3 = None
def _s3_client():
    global _s3
    if _s3 is None:
        import boto3  # type: ignore
        _s3 = boto3.client("s3")
    return _s3


# ---- Helpers ----
TRACKING_PARAMS = {
    "fbclid", "gclid", "mc_cid", "mc_eid", "igshid", "yclid",
    "_ga", "ref", "ref_src", "ref_url",
}

def canonical_url(u: str) -> str:
    if not u:
        return u
    p = urllib.parse.urlsplit(u.strip())
    q = urllib.parse.parse_qsl(p.query, keep_blank_values=False)
    q = [(k, v) for k, v in q
         if not k.lower().startswith("utm_") and k.lower() not in TRACKING_PARAMS]
    return urllib.parse.urlunsplit(p._replace(
        query=urllib.parse.urlencode(q),
        fragment="",
    ))

def hash_id(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:24]

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
def strip_tags(html: str) -> str:
    if not html:
        return ""
    txt = _TAG_RE.sub(" ", html)
    txt = (txt.replace("&nbsp;", " ")
              .replace("&amp;", "&")
              .replace("&lt;", "<")
              .replace("&gt;", ">")
              .replace("&quot;", '"')
              .replace("&#39;", "'"))
    return _WS_RE.sub(" ", txt).strip()

def parse_date(raw):
    if not raw:
        return None
    raw = raw.strip()
    # Intento RFC 2822 (RSS pubDate)
    try:
        dt = parsedate_to_datetime(raw)
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
    except (TypeError, ValueError):
        pass
    # Intento ISO 8601 (Atom)
    try:
        s = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt.isoformat()
    except ValueError:
        return None

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8",
        "Accept-Language": "es-CO,es;q=0.9,en;q=0.5",
    })
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
        return r.read()


# ---- Parser ----
def _parse_rss(channel):
    out = []
    for item in channel.findall("item"):
        link = (item.findtext("link") or "").strip()
        if not link:
            continue
        guid_el = item.find("guid")
        guid = (guid_el.text if guid_el is not None else None) or link
        desc = item.findtext("description") or ""
        content = item.findtext(CONTENT_NS + "encoded") or ""
        author = (item.findtext(DC_NS + "creator")
                  or item.findtext("author")
                  or None)
        cats = [c.text for c in item.findall("category") if (c.text or "").strip()]
        out.append({
            "link": link,
            "title": (item.findtext("title") or "").strip(),
            "desc": content if content else desc,
            "fecha_pub": parse_date(item.findtext("pubDate")),
            "autor": author,
            "categorias": cats,
            "raw_id": guid.strip(),
        })
    return out

def _parse_atom(root):
    out = []
    for entry in root.findall(ATOM_NS + "entry"):
        # Buscar link rel=alternate o el primero
        link = ""
        for l in entry.findall(ATOM_NS + "link"):
            rel = l.get("rel") or "alternate"
            if rel == "alternate":
                link = l.get("href") or ""
                break
        if not link:
            l = entry.find(ATOM_NS + "link")
            if l is not None:
                link = l.get("href") or ""
        if not link:
            continue
        guid = (entry.findtext(ATOM_NS + "id") or link).strip()
        title = (entry.findtext(ATOM_NS + "title") or "").strip()
        summary = (entry.findtext(ATOM_NS + "summary")
                   or entry.findtext(ATOM_NS + "content")
                   or "")
        updated = (entry.findtext(ATOM_NS + "published")
                   or entry.findtext(ATOM_NS + "updated"))
        author = entry.findtext(ATOM_NS + "author/" + ATOM_NS + "name")
        cats = [c.get("term") for c in entry.findall(ATOM_NS + "category") if c.get("term")]
        out.append({
            "link": link,
            "title": title,
            "desc": summary,
            "fecha_pub": parse_date(updated),
            "autor": author,
            "categorias": cats,
            "raw_id": guid,
        })
    return out

def parse_feed(xml_bytes: bytes):
    root = ET.fromstring(xml_bytes)
    if root.tag.lower() == "rss":
        ch = root.find("channel")
        if ch is not None:
            return _parse_rss(ch)
    if root.tag == ATOM_NS + "feed" or root.tag.endswith("feed"):
        return _parse_atom(root)
    # rdf:RDF (RSS 1.0) — best-effort: tratar items como en RSS 2.0
    items = root.findall(".//item")
    if items:
        # Fabricar canal sintético
        class _C:
            def findall(self, _): return items
        return _parse_rss(_C())
    return []


# ---- State ----
def state_key():
    return f"{S3_PREFIX}/state/medios.json"

def load_state(local_dir=None):
    if local_dir:
        p = os.path.join(local_dir, "medios_state.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        return {}
    try:
        obj = _s3_client().get_object(Bucket=S3_BUCKET, Key=state_key())
        return json.loads(obj["Body"].read())
    except Exception as e:
        msg = str(e)
        if "NoSuchKey" in msg or "404" in msg:
            return {}
        print(f"[state] load failed: {e}; starting empty")
        return {}

def save_state(state, local_dir=None):
    body = json.dumps(state, ensure_ascii=False, indent=2).encode("utf-8")
    if local_dir:
        os.makedirs(local_dir, exist_ok=True)
        with open(os.path.join(local_dir, "medios_state.json"), "wb") as f:
            f.write(body)
        return
    _s3_client().put_object(
        Bucket=S3_BUCKET, Key=state_key(),
        Body=body, ContentType="application/json",
    )


# ---- Pipeline ----
def process_feed(cfg, prev_seen, run_iso, run_id):
    """Procesa un feed. Función pura (sin mutar state global), apta para
    correr en paralelo. Devuelve dict con eventos nuevos y nuevo state-slice."""
    medio = cfg["medio"]
    seen = list(prev_seen)
    seen_set = set(seen)
    new_events = []
    error = None

    try:
        xml_bytes = fetch(cfg["url"])
        items = parse_feed(xml_bytes)
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        print(f"[{medio}] FAIL fetch/parse: {error}")
        items = []

    for it in items:
        canon = canonical_url(it["link"])
        eid = hash_id(canon)
        if eid in seen_set:
            continue
        new_events.append({
            "id": eid,
            "medio": medio,
            "fuente": "rss",
            "url": it["link"],
            "url_canonica": canon,
            "titulo": it["title"],
            "resumen": strip_tags(it["desc"]),
            "fecha_pub": it["fecha_pub"],
            "fecha_capturada": run_iso,
            "autor": it["autor"],
            "categorias": it["categorias"],
            "raw_id": it["raw_id"],
            "run_id": run_id,
        })
        seen.append(eid)
        seen_set.add(eid)

    if len(seen) > MAX_SEEN_PER_FEED:
        seen = seen[-MAX_SEEN_PER_FEED:]

    return {
        "medio": medio,
        "new_events": new_events,
        "seen": seen,
        "last_run": run_iso,
        "last_count": len(new_events),
        "last_error": error,
    }


def write_outputs(events, run_id, now, local_dir=None):
    if not events:
        return []
    by_medio = {}
    for ev in events:
        by_medio.setdefault(ev["medio"], []).append(ev)

    paths = []
    for medio, evs in by_medio.items():
        rel = (f"raw/medios/yyyy={now:%Y}/mm={now:%m}/dd={now:%d}/"
               f"{medio}__{run_id}.jsonl")
        body = "\n".join(json.dumps(e, ensure_ascii=False) for e in evs).encode("utf-8")
        if local_dir:
            p = os.path.join(local_dir, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(body)
            paths.append(p + f" ({len(evs)})")
        else:
            key = f"{S3_PREFIX}/{rel}"
            _s3_client().put_object(
                Bucket=S3_BUCKET, Key=key,
                Body=body, ContentType="application/x-ndjson",
            )
            paths.append(f"s3://{S3_BUCKET}/{key} ({len(evs)})")
    return paths


def run(local_dir=None, dry_run=False):
    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%dT%H%M%SZ")
    run_iso = now.isoformat()

    state = {} if dry_run else load_state(local_dir)
    all_new = []
    summary = {}

    # Fetch en paralelo (I/O bound, urllib libera GIL).
    # Tiempo total ≈ feed más lento, no la suma.
    with ThreadPoolExecutor(max_workers=len(FEEDS)) as pool:
        futures = {
            pool.submit(
                process_feed,
                cfg,
                state.get(cfg["medio"], {}).get("seen", []),
                run_iso,
                run_id,
            ): cfg["medio"]
            for cfg in FEEDS
        }
        for fut in as_completed(futures):
            r = fut.result()
            medio = r["medio"]
            summary[medio] = r["last_count"]
            all_new.extend(r["new_events"])
            state[medio] = {
                "seen": r["seen"],
                "last_run": r["last_run"],
                "last_count": r["last_count"],
                "last_error": r["last_error"],
            }

    if dry_run:
        print(json.dumps({
            "run_id": run_id,
            "total": len(all_new),
            "per_medio": summary,
            "sample": all_new[:3],
        }, ensure_ascii=False, indent=2))
        return {"run_id": run_id, "total": len(all_new), "per_medio": summary}

    paths = write_outputs(all_new, run_id, now, local_dir=local_dir)
    save_state(state, local_dir=local_dir)
    print(f"[run {run_id}] total={len(all_new)} per_medio={summary}")
    return {
        "run_id": run_id,
        "total": len(all_new),
        "per_medio": summary,
        "paths": paths,
    }


# ---- Lambda entry ----
def handler(event, context):
    return run()


# ---- CLI ----
if __name__ == "__main__":
    args = sys.argv[1:]
    if "--dry-run" in args:
        run(dry_run=True)
    elif "--local" in args:
        run(local_dir=os.path.join(_HERE, "_local_out"))
    else:
        print("Usage: lambda_handler.py [--dry-run | --local]")
        print("  --dry-run : fetch + parse + print sample, no escribe nada")
        print("  --local   : escribe a ./_local_out/ (sin S3)")
        sys.exit(1)
