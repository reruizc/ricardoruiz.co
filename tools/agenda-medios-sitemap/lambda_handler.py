#!/usr/bin/env python3
"""
agenda-medios-sitemap · lambda_handler.py

Bloque B del módulo 07: medios sin RSS pero con sitemap.xml utilizable.
- elcolombiano (sitemap simple, 557+ URLs)
- bluradio (sitemap-latest, ~400 URLs)
- pulzo (sitemap-index → sub-sitemap mensual)
- qhubomedellin (sitemap simple, ~40 URLs limitado a secciones)

Trigger: EventBridge cada 30 min (offset a :15 / :45 para no chocar con el RSS).

Pipeline:
1. Listar sitemap del medio (resolver sitemap-index si aplica)
2. Filtrar URLs con lastmod > state.last_lastmod (o todas si first-run)
3. Cap MAX_URLS_PER_RUN URLs más recientes
4. Fetch en paralelo de cada URL → extraer meta tags (titulo, resumen, fecha_pub)
5. Escribir JSONL al MISMO prefijo que el RSS reader, así el agregador los recoge

Output schema idéntico al RSS reader, solo cambia `fuente: "sitemap"`.
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
MAX_URLS_PER_RUN = 30
MAX_SEEN_PER_FEED = 600
ARTICLE_FETCH_WORKERS = 8

SM_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
NEWS_NS = "{http://www.google.com/schemas/sitemap-news/0.9}"

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "sitemaps.json"), encoding="utf-8") as _f:
    SITEMAPS = json.load(_f)

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
def fetch_bytes(url, timeout=HTTP_TIMEOUT):
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-CO,es;q=0.9,en;q=0.5",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


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


# ---- Sitemap parsing ----
def parse_sitemap_xml(xml_bytes):
    """Devuelve (is_index, items) donde items = [{loc, lastmod}, ...].
    Para sitemaps de noticias (Google News namespace), usa
    <news:publication_date> como lastmod si no hay <lastmod> estándar."""
    root = ET.fromstring(xml_bytes)
    is_index = "sitemapindex" in root.tag.lower()
    selector = "sitemap" if is_index else "url"
    items = []
    for entry in root.findall(SM_NS + selector):
        loc = entry.findtext(SM_NS + "loc")
        lastmod = entry.findtext(SM_NS + "lastmod")
        if not lastmod:
            news_el = entry.find(NEWS_NS + "news")
            if news_el is not None:
                lastmod = news_el.findtext(NEWS_NS + "publication_date")
        if loc:
            items.append({"loc": loc.strip(), "lastmod": (lastmod or "").strip()})
    return is_index, items


# Para sub-sitemaps tipo "sitemap-pt-post-2026-04.xml" o "sitemap-2026-04.xml"
_YYYY_MM_RE = re.compile(r"(\d{4})[-_/](\d{2})")

def resolve_sitemap_index(items):
    """Para sitemap-index: devolver el sub-sitemap más reciente.
    Estrategia: 1) lastmod si existe; 2) extraer YYYY-MM del nombre del
    archivo; 3) último de la lista como fallback."""
    if not items:
        return None
    with_lastmod = [it for it in items if it.get("lastmod")]
    if with_lastmod:
        with_lastmod.sort(key=lambda x: x["lastmod"], reverse=True)
        return with_lastmod[0]["loc"]
    # Sin lastmod: extraer fecha del filename y tomar el más reciente
    dated = []
    for it in items:
        m = _YYYY_MM_RE.search(it["loc"])
        if m:
            dated.append((m.group(1) + "-" + m.group(2), it["loc"]))
    if dated:
        dated.sort(reverse=True)
        return dated[0][1]
    return items[-1]["loc"]


# ---- HTML meta extraction (sin BeautifulSoup, regex puro) ----
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)

def _meta_search(html, prop, attr):
    """Busca <meta {attr}="prop" content="..."> en cualquier orden de atributos."""
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
    # Limpiar sufijos típicos como " — El Colombiano" o " | Pulzo"
    return re.split(r"\s+[—\-\|]\s+[A-ZÁ-Úa-zá-ú0-9 ]+$", txt, 1)[0].strip()

def extract_description(html):
    return (
        extract_meta(html, "og:description")
        or extract_meta(html, "twitter:description", "name")
        or extract_meta(html, "description", "name")
    )

def extract_pub_date(html):
    raw = (
        extract_meta(html, "article:published_time")
        or extract_meta(html, "publication-date", "name")
        or extract_meta(html, "date", "name")
        or extract_meta(html, "DC.date", "name")
    )
    return parse_iso_date(raw)

def extract_author(html):
    return (
        extract_meta(html, "author", "name")
        or extract_meta(html, "article:author")
    )


# ---- State ----
def state_key():
    return f"{S3_PREFIX}/state/sitemap.json"

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
SECTION_TITLE_RE = re.compile(
    r"^(noticias de |últim[ao]s noticias|portada|inicio|home$)",
    re.IGNORECASE,
)

def looks_like_article(url: str, title: str) -> bool:
    """Heurística general: artículo de noticia vs página de sección.
    - URL: último segmento del path >= 20 chars y contiene `-` o `_` (slug).
    - Título: no empieza con patrones genéricos de sección."""
    path = urllib.parse.urlsplit(url).path.rstrip("/")
    if not path:
        return False
    last_seg = path.rsplit("/", 1)[-1]
    if len(last_seg) < 20:
        return False
    if "-" not in last_seg and "_" not in last_seg:
        return False
    if title and SECTION_TITLE_RE.match(title.strip()):
        return False
    return True


def fetch_article(url, run_iso, run_id, medio, lastmod_hint):
    try:
        html_bytes = fetch_bytes(url)
        html = html_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[{medio}] fetch FAIL {url}: {type(e).__name__}: {e}")
        return None
    canon = canonical_url(url)
    titulo = extract_title(html) or ""
    if not titulo:
        return None
    if not looks_like_article(url, titulo):
        # Página de sección o hub, no artículo
        return None
    return {
        "id": hash_id(canon),
        "medio": medio,
        "fuente": "sitemap",
        "url": url,
        "url_canonica": canon,
        "titulo": titulo,
        "resumen": extract_description(html) or "",
        "fecha_pub": extract_pub_date(html) or parse_iso_date(lastmod_hint),
        "fecha_capturada": run_iso,
        "autor": extract_author(html),
        "categorias": [],
        "raw_id": canon,
        "run_id": run_id,
    }


def process_medio(cfg, prev_slice, run_iso, run_id):
    medio = cfg["medio"]
    seen_set = set(prev_slice.get("seen", []))
    last_lastmod = prev_slice.get("last_lastmod") or ""
    error = None
    new_events = []

    # Resolver sitemap (con fallback a sitemap-index)
    items = []
    try:
        sm_bytes = fetch_bytes(cfg["url"])
        is_index, items = parse_sitemap_xml(sm_bytes)
        if is_index:
            sub_url = resolve_sitemap_index(items)
            if not sub_url:
                raise RuntimeError("sitemap-index sin sub-sitemaps utilizables")
            print(f"[{medio}] index → sub-sitemap: {sub_url}")
            sm_bytes = fetch_bytes(sub_url)
            _, items = parse_sitemap_xml(sm_bytes)
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        print(f"[{medio}] FAIL sitemap: {error}")

    # Filtro keyword opcional (configurable por medio)
    if cfg.get("url_must_contain"):
        kw = cfg["url_must_contain"].lower()
        items = [it for it in items if kw in it["loc"].lower()]

    # Filtrar dedup + lastmod
    candidates = []
    for it in items:
        loc = it.get("loc")
        if not loc:
            continue
        eid = hash_id(canonical_url(loc))
        if eid in seen_set:
            continue
        if last_lastmod and it.get("lastmod") and it["lastmod"] <= last_lastmod:
            continue
        candidates.append(it)

    # Más recientes primero, cap
    candidates.sort(key=lambda x: x.get("lastmod") or "", reverse=True)
    candidates = candidates[:MAX_URLS_PER_RUN]
    print(f"[{medio}] {len(candidates)} URLs nuevas (de {len(items)} en sitemap)")

    # Fetch artículos en paralelo
    new_lastmod = last_lastmod
    if candidates:
        with ThreadPoolExecutor(max_workers=min(ARTICLE_FETCH_WORKERS, len(candidates))) as pool:
            fut_to_item = {
                pool.submit(fetch_article, it["loc"], run_iso, run_id, medio, it.get("lastmod")): it
                for it in candidates
            }
            for fut in as_completed(fut_to_item):
                it = fut_to_item[fut]
                ev = fut.result()
                if ev is None:
                    continue
                new_events.append(ev)
                seen_set.add(ev["id"])
                lm = it.get("lastmod") or ""
                if lm > new_lastmod:
                    new_lastmod = lm

    seen_list = list(seen_set)
    if len(seen_list) > MAX_SEEN_PER_FEED:
        seen_list = seen_list[-MAX_SEEN_PER_FEED:]

    return {
        "medio": medio,
        "new_events": new_events,
        "state_slice": {
            "seen": seen_list,
            "last_lastmod": new_lastmod,
            "last_run": run_iso,
            "last_count": len(new_events),
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

    with ThreadPoolExecutor(max_workers=len(SITEMAPS)) as pool:
        futures = {
            pool.submit(
                process_medio, cfg, state.get(cfg["medio"], {}), run_iso, run_id
            ): cfg["medio"]
            for cfg in SITEMAPS
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
        print("  --dry-run : fetch + parse + sample, sin escribir a S3")
        sys.exit(1)
