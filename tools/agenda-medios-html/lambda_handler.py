#!/usr/bin/env python3
"""
agenda-medios-html · lambda_handler.py

Bloque C del módulo 07: medios sin RSS ni sitemap utilizable, pero con
HTML estable de listado. Cubre:
- qhubomedellin (página /actualidad/local con cards)
- semana (sección /nacion/medellin/)
- lafm (regional /noticias/antioquia)

NO cubre (movidos a "no aplica" por arquitectura del sitio):
- adn.com.co — devuelve 500 incluso con UA real
- rcnradio.com — SPA OTT (mdstrm), no portal de noticias texto
- caracol.com.co/medellin — bloqueado por Cloudflare
- teleantioquia.co — SPA con render JS

Pipeline:
1. Fetch listing URL del medio.
2. Regex extrae URLs de artículos (patrón configurado por medio).
3. Filtra dedup vs state, cap MAX_URLS_PER_RUN más recientes.
4. Fetch cada artículo en paralelo, extrae meta tags og:* / twitter:*.
5. Escribe JSONL al MISMO prefijo S3 que RSS / sitemap, mismo schema.

El agregador existente recoge estos eventos sin tocar nada.
"""

import os
import re
import sys
import json
import hashlib
import urllib.request
import urllib.parse
import urllib.error
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
MAX_URLS_PER_RUN = 30
MAX_SEEN_PER_FEED = 600
ARTICLE_FETCH_WORKERS = 8

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "scrapers.json"), encoding="utf-8") as _f:
    SCRAPERS = json.load(_f)

_s3 = None
def _s3_client():
    global _s3
    if _s3 is None:
        import boto3  # type: ignore
        _s3 = boto3.client("s3")
    return _s3


# ---- URL helpers ----
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


# ---- HTTP ----
def fetch_text(url, timeout=HTTP_TIMEOUT):
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CO,es;q=0.9,en;q=0.5",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


# ---- Date parsing ----
def parse_iso_date(s):
    if not s:
        return None
    try:
        s2 = s.strip().replace("Z", "+00:00")
        return datetime.fromisoformat(s2).isoformat()
    except (ValueError, AttributeError):
        try:
            dt = parsedate_to_datetime(s)
            if dt is not None and dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat() if dt else None
        except (TypeError, ValueError):
            return None


# ---- HTML meta extraction (regex puro, idéntico al sitemap reader) ----
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)

def _meta_search(html, prop, attr):
    a = re.search(
        rf'<meta\s+(?:[^>]*?\s)?{attr}\s*=\s*["\']{re.escape(prop)}["\'][^>]*?\scontent\s*=\s*["\']([^"\']*)["\']',
        html, re.IGNORECASE | re.DOTALL,
    )
    if a:
        return a.group(1)
    b = re.search(
        rf'<meta\s+(?:[^>]*?\s)?content\s*=\s*["\']([^"\']*)["\'][^>]*?\s{attr}\s*=\s*["\']{re.escape(prop)}["\']',
        html, re.IGNORECASE | re.DOTALL,
    )
    return b.group(1) if b else None

_HTML_ENTS = {
    "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"',
    "&#39;": "'", "&apos;": "'", "&nbsp;": " ", "&#160;": " ",
    "&ndash;": "–", "&mdash;": "—", "&hellip;": "…",
}
def _decode_html(s):
    if not s:
        return s
    out = s
    for k, v in _HTML_ENTS.items():
        out = out.replace(k, v)
    return out.strip()

def extract_meta(html, prop, attr="property"):
    raw = _meta_search(html, prop, attr)
    return _decode_html(raw) if raw else None

def extract_title(html):
    title = (
        extract_meta(html, "og:title")
        or extract_meta(html, "twitter:title", "name")
    )
    if title:
        return title
    m = TITLE_RE.search(html)
    if not m:
        return None
    txt = _decode_html(m.group(1))
    return re.split(r"\s+[—\-\|]\s+[A-ZÁ-Úa-zá-ú0-9 ]+$", txt, 1)[0].strip()

def extract_description(html):
    return (
        extract_meta(html, "og:description")
        or extract_meta(html, "twitter:description", "name")
        or extract_meta(html, "description", "name")
    )

JSONLD_DATE_RE = re.compile(r'"datePublished"\s*:\s*"([^"]+)"', re.IGNORECASE)

def extract_jsonld_date(html):
    """Fallback para sitios que solo exponen fecha en JSON-LD Schema.org
    (ej. Q'Hubo Medellín). Acepta formatos 'YYYY-MM-DD HH:MM:SS ±ZZZZ' o ISO."""
    m = JSONLD_DATE_RE.search(html)
    if not m:
        return None
    raw = m.group(1).strip()
    # Normalizar 'YYYY-MM-DD HH:MM:SS ±ZZZZ' → 'YYYY-MM-DDTHH:MM:SS±ZZZZ'
    if " " in raw and "T" not in raw:
        parts = raw.split(" ")
        if len(parts) >= 2:
            raw = parts[0] + "T" + parts[1]
            if len(parts) >= 3:
                raw += parts[2]
    return parse_iso_date(raw)

def extract_pub_date(html):
    raw = (
        extract_meta(html, "article:published_time")
        or extract_meta(html, "publication-date", "name")
        or extract_meta(html, "date", "name")
        or extract_meta(html, "DC.date", "name")
    )
    parsed = parse_iso_date(raw)
    if parsed:
        return parsed
    return extract_jsonld_date(html)

def extract_author(html):
    return (
        extract_meta(html, "author", "name")
        or extract_meta(html, "article:author")
    )


# ---- Section / article heuristic ----
SECTION_TITLE_RE = re.compile(
    r"^(noticias de |últim[ao]s noticias|portada|inicio|home$)",
    re.IGNORECASE,
)

def looks_like_article(url: str, title: str) -> bool:
    """Es artículo si ALGÚN segmento del path tiene slug largo (>=20 chars con
    guion/underscore). Acepta tanto URLs tipo /seccion/.../slug-ID (último seg
    es slug) como /seccion/articulo/slug/ID/ (slug en penúltimo)."""
    path = urllib.parse.urlsplit(url).path.rstrip("/")
    if not path:
        return False
    segs = [s for s in path.split("/") if s]
    has_slug = any(len(s) >= 20 and ("-" in s or "_" in s) for s in segs)
    if not has_slug:
        return False
    if title and SECTION_TITLE_RE.match(title.strip()):
        return False
    return True


# ---- Listing → article URLs ----
def extract_article_urls(html: str, cfg: dict):
    """Aplica el regex configurado y devuelve URLs absolutas únicas."""
    pattern = cfg["article_url_re"]
    base = cfg["base_url"].rstrip("/")
    matches = re.findall(pattern, html)
    out = []
    seen = set()
    for m in matches:
        url = m if m.startswith("http") else (base + m)
        if url in seen:
            continue
        seen.add(url)
        out.append(url)
    return out


# ---- State ----
def state_key():
    return f"{S3_PREFIX}/state/html.json"

def load_state():
    try:
        obj = _s3_client().get_object(Bucket=S3_BUCKET, Key=state_key())
        return json.loads(obj["Body"].read())
    except Exception as e:
        msg = str(e)
        if "NoSuchKey" in msg or "404" in msg:
            return {}
        print(f"[state] load failed: {e}; starting empty")
        return {}

def save_state(state):
    body = json.dumps(state, ensure_ascii=False, indent=2).encode("utf-8")
    _s3_client().put_object(
        Bucket=S3_BUCKET, Key=state_key(),
        Body=body, ContentType="application/json",
    )


# ---- Per-medio pipeline ----
def fetch_article(url, run_iso, run_id, medio):
    try:
        html = fetch_text(url)
    except Exception as e:
        print(f"[{medio}] fetch FAIL {url}: {type(e).__name__}: {e}")
        return None
    canon = canonical_url(url)
    titulo = extract_title(html) or ""
    if not titulo:
        return None
    if not looks_like_article(url, titulo):
        return None
    return {
        "id": hash_id(canon),
        "medio": medio,
        "fuente": "html",
        "url": url,
        "url_canonica": canon,
        "titulo": titulo,
        "resumen": extract_description(html) or "",
        "fecha_pub": extract_pub_date(html),
        "fecha_capturada": run_iso,
        "autor": extract_author(html),
        "categorias": [],
        "raw_id": canon,
        "run_id": run_id,
    }


def process_medio(cfg, prev_slice, run_iso, run_id):
    medio = cfg["medio"]
    seen_set = set(prev_slice.get("seen", []))
    error = None
    new_events = []
    listing_count = 0

    try:
        listing_html = fetch_text(cfg["listing_url"])
        urls = extract_article_urls(listing_html, cfg)
        listing_count = len(urls)
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        print(f"[{medio}] FAIL listing: {error}")
        urls = []

    # Dedup
    candidates = []
    for u in urls:
        eid = hash_id(canonical_url(u))
        if eid in seen_set:
            continue
        candidates.append(u)

    # Listing devuelve en orden de aparición → "más recientes primero" en la mayoría de medios
    candidates = candidates[:MAX_URLS_PER_RUN]
    print(f"[{medio}] {len(candidates)} URLs nuevas (de {listing_count} en listing)")

    if candidates:
        with ThreadPoolExecutor(max_workers=min(ARTICLE_FETCH_WORKERS, len(candidates))) as pool:
            fut_to_url = {
                pool.submit(fetch_article, u, run_iso, run_id, medio): u
                for u in candidates
            }
            for fut in as_completed(fut_to_url):
                ev = fut.result()
                if ev is None:
                    continue
                new_events.append(ev)
                seen_set.add(ev["id"])

    seen_list = list(seen_set)
    if len(seen_list) > MAX_SEEN_PER_FEED:
        seen_list = seen_list[-MAX_SEEN_PER_FEED:]

    return {
        "medio": medio,
        "new_events": new_events,
        "state_slice": {
            "seen": seen_list,
            "last_run": run_iso,
            "last_count": len(new_events),
            "last_listing_count": listing_count,
            "last_error": error,
        },
    }


def write_outputs(events, run_id, now):
    if not events:
        return []
    by_medio = {}
    for ev in events:
        by_medio.setdefault(ev["medio"], []).append(ev)
    paths = []
    for medio, evs in by_medio.items():
        key = (
            f"{S3_PREFIX}/raw/medios/yyyy={now:%Y}/mm={now:%m}/dd={now:%d}/"
            f"{medio}__{run_id}.jsonl"
        )
        body = "\n".join(json.dumps(e, ensure_ascii=False) for e in evs).encode("utf-8")
        _s3_client().put_object(
            Bucket=S3_BUCKET, Key=key,
            Body=body, ContentType="application/x-ndjson",
        )
        paths.append(f"s3://{S3_BUCKET}/{key} ({len(evs)})")
    return paths


def run(dry_run=False):
    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%dT%H%M%SZ")
    run_iso = now.isoformat()

    state = {} if dry_run else load_state()
    all_new = []
    summary = {}

    with ThreadPoolExecutor(max_workers=len(SCRAPERS)) as pool:
        futures = {
            pool.submit(
                process_medio, cfg, state.get(cfg["medio"], {}), run_iso, run_id
            ): cfg["medio"]
            for cfg in SCRAPERS
        }
        for fut in as_completed(futures):
            r = fut.result()
            medio = r["medio"]
            summary[medio] = r["state_slice"]["last_count"]
            all_new.extend(r["new_events"])
            state[medio] = r["state_slice"]

    if dry_run:
        print(json.dumps({
            "run_id": run_id,
            "total": len(all_new),
            "per_medio": summary,
            "sample": all_new[:2],
        }, ensure_ascii=False, indent=2))
        return {"run_id": run_id, "total": len(all_new), "per_medio": summary}

    paths = write_outputs(all_new, run_id, now)
    save_state(state)
    print(f"[run {run_id}] total={len(all_new)} per_medio={summary}")
    return {
        "run_id": run_id,
        "total": len(all_new),
        "per_medio": summary,
        "paths": paths,
    }


def handler(event, context):
    return run()


if __name__ == "__main__":
    if "--dry-run" in sys.argv:
        run(dry_run=True)
    else:
        print("Usage: lambda_handler.py --dry-run")
        sys.exit(1)
