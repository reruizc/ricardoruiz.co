#!/usr/bin/env python3
"""
radar-mujer-medios · collect_social.py

Capa de REDES de Radar Mujer (MxD) vía Apify. Corre actores pay-per-result
(X / Instagram / TikTok) por query/hashtag, normaliza cada item al esquema
común de eventos, taggea con el léxico mujer (reusa collect.py) y devuelve
la lista para agregar junto a la de prensa.

Requiere la variable de entorno APIFY_TOKEN (nunca va al repo).

Config en social.json: por red, el actor + input_template (con __QUERIES__ y
__MAX__) + map (dot-path del output del actor -> campos comunes).

⚠️ Los esquemas de input/output VARÍAN por actor de Apify. Antes de escalar,
correr `python3 collect_social.py --probe x` (o instagram/tiktok) que hace UNA
query chica y muestra el item crudo para ajustar el `map` en social.json.

Uso:
    python3 collect_social.py --probe x        # 1 query de prueba, imprime crudo
    python3 collect_social.py --dry-run         # todas las redes, resumen sin escribir
    python3 collect_social.py --red x           # solo una red
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import collect  # reusa norm, match_keywords, hash_id, es_ruido, KEYWORDS

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "social.json"), encoding="utf-8") as _f:
    SOCIAL = json.load(_f)

APIFY_BASE = "https://api.apify.com/v2"
APIFY_TIMEOUT = 150


def _token():
    tok = os.environ.get("APIFY_TOKEN")
    if not tok:
        raise RuntimeError("Falta APIFY_TOKEN en el entorno.")
    return tok


def run_actor(actor, run_input, max_wait=APIFY_TIMEOUT, intentos=2):
    """Corre un actor de Apify y devuelve los items del dataset (sync).
    Reintenta ante errores transitorios (502/503/timeout de gateway)."""
    actor_path = actor.replace("/", "~")  # apidojo/tweet-scraper -> apidojo~tweet-scraper
    url = (f"{APIFY_BASE}/acts/{actor_path}/run-sync-get-dataset-items"
           f"?token={_token()}&timeout={max_wait}")
    body = json.dumps(run_input).encode("utf-8")
    last = None
    for i in range(max(1, intentos)):
        req = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=max_wait + 20) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503, 504) and i + 1 < intentos:
                time.sleep(4)
                continue
            raise
        except Exception as e:
            last = e
            if i + 1 < intentos:
                time.sleep(4); continue
            raise
    if last:
        raise last


def _dig(obj, path):
    """Extrae por dot-path: 'author/userName' -> obj['author']['userName']."""
    cur = obj
    for part in path.split("/"):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _to_iso(v):
    """Normaliza fecha a ISO. Acepta ISO string o epoch (s)."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        try:
            return datetime.fromtimestamp(v, tz=timezone.utc).isoformat()
        except Exception:
            return None
    s = str(v)
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).isoformat()
    except Exception:
        return s  # el actor ya la dio en algún formato legible


def _build_input(cfg, queries):
    """Rellena input_template. __QUERIES__ = lista de queries;
    __MAX_PER__ = tope POR query/hashtag (IG resultsLimit, TikTok resultsPerPage);
    __MAX_TOTAL__ = tope TOTAL entre todas las queries (X maxItems)."""
    per = int(cfg.get("max_por_query", 20))
    total = per * len(queries)
    tmpl = json.dumps(cfg["input_template"])
    tmpl = tmpl.replace('"__QUERIES__"', json.dumps(queries))
    tmpl = tmpl.replace('"__MAX_PER__"', str(per))
    tmpl = tmpl.replace('"__MAX_TOTAL__"', str(total))
    return json.loads(tmpl)


def fetch_red(red, cfg, run_iso):
    """Corre una red (todas sus queries en una sola llamada al actor)."""
    use_hashtags = cfg.get("hashtags", False)
    if cfg.get("combined_query"):
        # X es lento con muchos términos (una búsqueda por término) → una sola
        # query con OR es mucho más rápida y no expira el run-sync.
        queries = [cfg["combined_query"]]
    else:
        queries = list(SOCIAL["queries_hashtag"] if use_hashtags else SOCIAL["queries_texto"])
    suffix = cfg.get("query_suffix")
    if suffix and not use_hashtags:
        queries = [q + suffix for q in queries]
    run_input = _build_input(cfg, queries)
    filtrar = cfg.get("filtrar_por_lexico", False)
    events = []
    try:
        items = run_actor(cfg["actor"], run_input)
    except Exception as e:
        print(f"[{red}] FAIL Apify: {type(e).__name__}: {e}")
        return events
    m = cfg["map"]
    for it in items:
        if not isinstance(it, dict) or it.get("noResults"):
            continue  # centinela de "sin resultados" que algunos actores emiten
        texto = _dig(it, m["texto"]) or ""
        if not texto.strip():
            continue
        matched = collect.match_keywords(texto, "")
        # X busca laxo → si el config lo pide, exigir al menos un término del léxico.
        if filtrar and not matched:
            continue
        events.append({
            "fuente": "redes",
            "red": red,
            "tema": None,
            "medio": red,                       # para reusar el agregador
            "autor": _dig(it, m["autor"]),
            "titulo": (texto[:180]).strip(),    # el texto del post como "titular"
            "resumen": texto[:400],
            "url": _dig(it, m["url"]),
            "fecha_pub": _to_iso(_dig(it, m["fecha"])),
            "fecha_capturada": run_iso,
            "metrica": _dig(it, m.get("metrica", "")),
            "matched": matched,
        })
    return events


def collect_social_events(run_iso=None):
    """Corre todas las redes habilitadas y devuelve eventos únicos."""
    if run_iso is None:
        run_iso = datetime.now(timezone.utc).isoformat()
    nets = [(r, c) for r, c in SOCIAL["networks"].items() if c.get("enabled")]
    collected = []
    with ThreadPoolExecutor(max_workers=max(1, len(nets))) as pool:
        futs = {pool.submit(fetch_red, r, c, run_iso): r for r, c in nets}
        for fut in as_completed(futs):
            collected.extend(fut.result())
    # dedup por (red, url) o (red, texto)
    by_key = {}
    for ev in collected:
        base = ev.get("url") or ev.get("titulo")
        key = collect.hash_id(ev["red"] + "|" + collect.norm(base or ""))
        ev["id"] = key
        by_key.setdefault(key, ev)
    return list(by_key.values())


def _probe(red):
    cfg = SOCIAL["networks"][red]
    use_hashtags = cfg.get("hashtags", False)
    q = [(SOCIAL["queries_hashtag"] if use_hashtags else SOCIAL["queries_texto"])[0]]
    run_input = _build_input({**cfg, "max_por_query": 5}, q)
    print(f"[probe {red}] actor={cfg['actor']} input={run_input}")
    items = run_actor(cfg["actor"], run_input)
    print(f"[probe {red}] {len(items)} items. Primer item CRUDO:")
    print(json.dumps(items[0] if items else {}, ensure_ascii=False, indent=1)[:2000])


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--probe" in args:
        _probe(args[args.index("--probe") + 1])
    elif "--red" in args:
        red = args[args.index("--red") + 1]
        cfg = SOCIAL["networks"][red]
        evs = fetch_red(red, cfg, datetime.now(timezone.utc).isoformat())
        print(f"{red}: {len(evs)} eventos")
        for e in evs[:8]:
            print(f"  · [{e['autor']}] {e['titulo'][:90]}  ({(e['fecha_pub'] or '')[:10]})")
    elif "--dry-run" in args:
        evs = collect_social_events()
        from collections import Counter
        print(json.dumps({
            "total": len(evs),
            "por_red": dict(Counter(e["red"] for e in evs)),
            "muestra": [{"red": e["red"], "autor": e["autor"], "titulo": e["titulo"][:80]} for e in evs[:10]],
        }, ensure_ascii=False, indent=2))
    else:
        print("Uso: collect_social.py [--probe x|instagram|tiktok | --red <red> | --dry-run]")
        print("Requiere APIFY_TOKEN en el entorno.")
