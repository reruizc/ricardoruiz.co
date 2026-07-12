#!/usr/bin/env python3
"""
radar-mujer-medios · collect.py

Colector del monitor de medios de Radar Mujer (MxD). Fork del colector de
proyecto-dc (agenda-medios-rss) reorientado a monitoreo TEMÁTICO (mujer /
participación política) en vez de por-medio.

Dos fuentes (feeds.json):
  1. google_news · queries temáticas a Google News RSS (motor base, gratis,
     nacional, sin mantener conectores). Cada query trae ~50-100 titulares
     de todo el ecosistema con <source> limpio.
  2. feeds · RSS directos. filtrar=true recorta al tema mujer con el léxico
     keywords-mujer.txt; filtrar=false conserva todo (medios feministas).

Cada evento se taggea con los términos del léxico que matchea (matched) y
con el tema (para Google News). Dedup por (título normalizado, medio) para
colapsar el mismo artículo que aparece en varias queries.

Salida (JSONL particionado por fecha, igual que proyecto-dc):
    raw/mujer/yyyy=YYYY/mm=MM/dd=DD/{fuente}__{run_id}.jsonl
    state/mujer.json      (dedup entre corridas)

Test local:
    python3 collect.py --dry-run    # fetch + parse + resumen, no escribe nada
    python3 collect.py --local      # escribe a ./_local_out/ (sin S3)
"""

import os
import re
import sys
import json
import hashlib
import unicodedata
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# ---- Config ----
S3_BUCKET = os.environ.get("RADAR_S3_BUCKET", "elecciones-2026")
S3_PREFIX = os.environ.get("RADAR_S3_PREFIX", "ricardoruiz.co/radar-mujer/medios")
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
HTTP_TIMEOUT = 20
MAX_SEEN = 4000  # IDs retenidos en el state (dedup entre corridas)

ATOM_NS = "{http://www.w3.org/2005/Atom}"
DC_NS = "{http://purl.org/dc/elements/1.1/}"
CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}"

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "feeds.json"), encoding="utf-8") as _f:
    CFG = json.load(_f)

def _load_keywords():
    kws = []
    with open(os.path.join(_HERE, "keywords-mujer.txt"), encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            kws.append(s)
    return kws
KEYWORDS = _load_keywords()

_s3 = None
def _s3_client():
    global _s3
    if _s3 is None:
        import boto3  # type: ignore
        _s3 = boto3.client("s3")
    return _s3


# ---- Helpers ----
TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid", "igshid", "yclid",
                   "_ga", "ref", "ref_src", "ref_url", "oc"}

def canonical_url(u: str) -> str:
    if not u:
        return u
    p = urllib.parse.urlsplit(u.strip())
    q = urllib.parse.parse_qsl(p.query, keep_blank_values=False)
    q = [(k, v) for k, v in q
         if not k.lower().startswith("utm_") and k.lower() not in TRACKING_PARAMS]
    return urllib.parse.urlunsplit(p._replace(query=urllib.parse.urlencode(q), fragment=""))

def hash_id(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:24]

def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", strip_accents((s or "").lower())).strip()

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
def strip_tags(html: str) -> str:
    if not html:
        return ""
    txt = _TAG_RE.sub(" ", html)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                 ("&quot;", '"'), ("&#39;", "'"), ("&#8217;", "'"), ("&hellip;", "…")):
        txt = txt.replace(a, b)
    return _WS_RE.sub(" ", txt).strip()

def parse_date(raw):
    if not raw:
        return None
    raw = raw.strip()
    try:
        dt = parsedate_to_datetime(raw)
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).isoformat()
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

# ---- Léxico ----
# Frases (con espacio) → substring sobre texto normalizado.
# Palabras sueltas → match por token (word boundary) para no pescar "aborto"
# dentro de "laborioso" ni "niña" dentro de otra palabra.
_KW_PHRASES = [norm(k) for k in KEYWORDS if " " in k]
_KW_WORDS = set(norm(k) for k in KEYWORDS if " " not in k)
_WORD_RE = re.compile(r"[a-zñ]+")

_EXCLUIR = [norm(t) for t in CFG.get("excluir", {}).get("terminos", [])]

def match_keywords(title: str, summary: str):
    """Devuelve lista de términos del léxico que aparecen en title+summary."""
    blob = norm((title or "") + " . " + (summary or ""))
    found = []
    for ph in _KW_PHRASES:
        if ph in blob:
            found.append(ph)
    toks = set(_WORD_RE.findall(blob))
    for w in _KW_WORDS:
        if w in toks:
            found.append(w)
    return sorted(set(found))

def es_ruido(title: str, matched) -> bool:
    """True si el titular es ruido deportivo/farándula sin ninguna keyword real."""
    if matched:
        return False
    blob = norm(title or "")
    return any(t in blob for t in _EXCLUIR)


# ---- Parser RSS/Atom ----
def _parse_rss_items(items):
    out = []
    for item in items:
        link = (item.findtext("link") or "").strip()
        if not link:
            continue
        guid_el = item.find("guid")
        guid = (guid_el.text if guid_el is not None else None) or link
        desc = item.findtext("description") or ""
        content = item.findtext(CONTENT_NS + "encoded") or ""
        author = item.findtext(DC_NS + "creator") or item.findtext("author") or None
        src_el = item.find("source")
        source = (src_el.text.strip() if src_el is not None and src_el.text else None)
        out.append({
            "link": link,
            "title": (item.findtext("title") or "").strip(),
            "desc": content if content else desc,
            "fecha_pub": parse_date(item.findtext("pubDate")),
            "autor": author,
            "source": source,
            "raw_id": guid.strip(),
        })
    return out

def _parse_atom(root):
    out = []
    for entry in root.findall(ATOM_NS + "entry"):
        link = ""
        for l in entry.findall(ATOM_NS + "link"):
            if (l.get("rel") or "alternate") == "alternate":
                link = l.get("href") or ""
                break
        if not link:
            l = entry.find(ATOM_NS + "link")
            link = (l.get("href") if l is not None else "") or ""
        if not link:
            continue
        out.append({
            "link": link,
            "title": (entry.findtext(ATOM_NS + "title") or "").strip(),
            "desc": entry.findtext(ATOM_NS + "summary") or entry.findtext(ATOM_NS + "content") or "",
            "fecha_pub": parse_date(entry.findtext(ATOM_NS + "published") or entry.findtext(ATOM_NS + "updated")),
            "autor": entry.findtext(ATOM_NS + "author/" + ATOM_NS + "name"),
            "source": None,
            "raw_id": (entry.findtext(ATOM_NS + "id") or link).strip(),
        })
    return out

def parse_feed(xml_bytes: bytes):
    root = ET.fromstring(xml_bytes)
    if root.tag.lower() == "rss":
        ch = root.find("channel")
        if ch is not None:
            return _parse_rss_items(ch.findall("item"))
    if root.tag == ATOM_NS + "feed" or root.tag.endswith("feed"):
        return _parse_atom(root)
    items = root.findall(".//item")
    if items:
        return _parse_rss_items(items)
    return []

# Título de Google News = "Titular real - Nombre del Medio".
_GN_SUFFIX_RE = re.compile(r"\s+-\s+([^-]+)$")
def split_gn_title(title, source):
    if source:
        # quitar el " - Fuente" del final si coincide
        m = _GN_SUFFIX_RE.search(title)
        if m and norm(m.group(1)) == norm(source):
            return title[:m.start()].strip(), source
        return title, source
    m = _GN_SUFFIX_RE.search(title)
    if m:
        return title[:m.start()].strip(), m.group(1).strip()
    return title, None


# ---- State ----
def state_key():
    return f"{S3_PREFIX}/state/mujer.json"

def load_state(local_dir=None):
    if local_dir:
        p = os.path.join(local_dir, "mujer_state.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        return {"seen": []}
    try:
        obj = _s3_client().get_object(Bucket=S3_BUCKET, Key=state_key())
        return json.loads(obj["Body"].read())
    except Exception as e:
        if "NoSuchKey" in str(e) or "404" in str(e):
            return {"seen": []}
        print(f"[state] load failed: {e}; empezando vacío")
        return {"seen": []}

def save_state(state, local_dir=None):
    body = json.dumps(state, ensure_ascii=False).encode("utf-8")
    if local_dir:
        os.makedirs(local_dir, exist_ok=True)
        with open(os.path.join(local_dir, "mujer_state.json"), "wb") as f:
            f.write(body)
        return
    _s3_client().put_object(Bucket=S3_BUCKET, Key=state_key(),
                            Body=body, ContentType="application/json")


# ---- Fetch tasks ----
def _gn_url(q, gn):
    ventana = gn.get("ventana")
    if ventana and "when:" not in q:
        q = f"{q} when:{ventana}"
    qs = urllib.parse.urlencode({"q": q, "hl": gn["hl"], "gl": gn["gl"], "ceid": gn["ceid"]})
    return f"https://news.google.com/rss/search?{qs}"

def fetch_google_news(query, gn, run_iso):
    tema, q = query["tema"], query["q"]
    events = []
    try:
        items = parse_feed(fetch(_gn_url(q, gn)))
    except Exception as e:
        print(f"[gn:{tema}] FAIL: {type(e).__name__}: {e}")
        return events
    for it in items:
        titulo, medio = split_gn_title(it["title"], it["source"])
        matched = match_keywords(titulo, strip_tags(it["desc"]))
        if es_ruido(titulo, matched):
            continue
        events.append({
            "fuente": "google-news",
            "tema": tema,
            "medio": medio or "desconocido",
            "url": it["link"],
            "titulo": titulo,
            "resumen": "",  # GN description es solo el link; el titular basta
            "fecha_pub": it["fecha_pub"],
            "fecha_capturada": run_iso,
            "autor": None,
            "matched": matched,
        })
    return events

def fetch_direct(feed, run_iso):
    medio = feed["medio"]
    filtrar = feed.get("filtrar", True)
    events = []
    try:
        items = parse_feed(fetch(feed["url"]))
    except Exception as e:
        print(f"[rss:{medio}] FAIL: {type(e).__name__}: {e}")
        return events
    for it in items:
        titulo = it["title"]
        resumen = strip_tags(it["desc"])
        matched = match_keywords(titulo, resumen)
        if filtrar and not matched:
            continue  # feed general → solo tema mujer
        events.append({
            "fuente": "rss",
            "tema": None,
            "medio": medio,
            "url": it["link"],
            "titulo": titulo,
            "resumen": resumen[:400],
            "fecha_pub": it["fecha_pub"],
            "fecha_capturada": run_iso,
            "autor": it["autor"],
            "matched": matched,
        })
    return events


def collect_events(run_iso=None):
    """Recolecta Google News + feeds, dedup por (titulo, medio) dentro de la
    corrida, y devuelve la lista única de eventos (sin estado, sin escribir).
    Es la ventana completa (when:Nd) — apta para agregar de forma stateless."""
    if run_iso is None:
        run_iso = datetime.now(timezone.utc).isoformat()
    gn = CFG["google_news"]
    tasks = []
    for q in gn["queries"]:
        tasks.append(lambda q=q: fetch_google_news(q, gn, run_iso))
    for feed in CFG["feeds"]:
        tasks.append(lambda feed=feed: fetch_direct(feed, run_iso))

    collected = []
    with ThreadPoolExecutor(max_workers=min(16, len(tasks))) as pool:
        for fut in as_completed([pool.submit(fn) for fn in tasks]):
            collected.extend(fut.result())

    by_key = {}
    for ev in collected:
        key = hash_id(norm(ev["titulo"]) + "|" + norm(ev["medio"]))
        ev["id"] = key
        if key in by_key:
            prev = by_key[key]
            temas = set(filter(None, [prev.get("tema"), ev.get("tema")]))
            prev["temas"] = sorted(set(prev.get("temas", []) or ([prev["tema"]] if prev.get("tema") else [])) | temas)
            prev["matched"] = sorted(set(prev.get("matched", [])) | set(ev.get("matched", [])))
        else:
            ev["temas"] = [ev["tema"]] if ev.get("tema") else []
            by_key[key] = ev
    return list(by_key.values())


def run(local_dir=None, dry_run=False):
    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%dT%H%M%SZ")
    run_iso = now.isoformat()

    unique = collect_events(run_iso)
    collected = unique  # para el print de dry-run

    # Dedup entre corridas (state)
    state = {"seen": []} if dry_run else load_state(local_dir)
    seen_set = set(state.get("seen", []))
    fresh = [ev for ev in unique if ev["id"] not in seen_set]

    per_tema = {}
    for ev in fresh:
        for t in (ev.get("temas") or ["(directo)"]):
            per_tema[t] = per_tema.get(t, 0) + 1

    if dry_run:
        print(json.dumps({
            "run_id": run_id,
            "recolectados_brutos": len(collected),
            "unicos_en_corrida": len(unique),
            "nuevos_vs_state": len(fresh),
            "por_tema": per_tema,
            "top_medios": _top_medios(fresh, 12),
            "muestra": [{"medio": e["medio"], "titulo": e["titulo"], "temas": e.get("temas"),
                          "matched": e["matched"][:5]} for e in fresh[:8]],
        }, ensure_ascii=False, indent=2))
        return

    paths = write_outputs(fresh, run_id, now, local_dir=local_dir)
    new_seen = (state.get("seen", []) + [e["id"] for e in fresh])[-MAX_SEEN:]
    save_state({"seen": new_seen, "last_run": run_iso, "last_count": len(fresh)}, local_dir=local_dir)
    print(f"[run {run_id}] brutos={len(collected)} unicos={len(unique)} nuevos={len(fresh)} por_tema={per_tema}")
    return {"run_id": run_id, "nuevos": len(fresh), "por_tema": per_tema, "paths": paths}


def _top_medios(events, n):
    from collections import Counter
    c = Counter(e["medio"] for e in events)
    return [{"medio": m, "n": k} for m, k in c.most_common(n)]


def write_outputs(events, run_id, now, local_dir=None):
    if not events:
        return []
    by_fuente = {}
    for ev in events:
        by_fuente.setdefault(ev["fuente"], []).append(ev)
    paths = []
    for fuente, evs in by_fuente.items():
        rel = (f"raw/mujer/yyyy={now:%Y}/mm={now:%m}/dd={now:%d}/{fuente}__{run_id}.jsonl")
        body = "\n".join(json.dumps(e, ensure_ascii=False) for e in evs).encode("utf-8")
        if local_dir:
            p = os.path.join(local_dir, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(body)
            paths.append(f"{p} ({len(evs)})")
        else:
            key = f"{S3_PREFIX}/{rel}"
            _s3_client().put_object(Bucket=S3_BUCKET, Key=key,
                                    Body=body, ContentType="application/x-ndjson")
            paths.append(f"s3://{S3_BUCKET}/{key} ({len(evs)})")
    return paths


def handler(event, context):
    return run()


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--dry-run" in args:
        run(dry_run=True)
    elif "--local" in args:
        run(local_dir=os.path.join(_HERE, "_local_out"))
    else:
        print("Uso: collect.py [--dry-run | --local]")
        sys.exit(1)
