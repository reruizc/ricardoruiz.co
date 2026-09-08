#!/usr/bin/env python3
"""
candidato-360-redes · lambda_handler.py

El paso 2 del wizard de `candidato-360.html`: la persona escribe su usuario,
marca en qué redes está (X, TikTok, Instagram) y esta Lambda **busca y valida**
antes de dejar construir el punto de partida.

Validar es lo contrario de adivinar. La secuencia es:

  1. SONDEO de cada red por su endpoint público (sin llave, sin scraping de
     sesión). Es la única fuente que dice si la cuenta EXISTE y con qué nombre.
  2. SEÑALES ABIERTAS: Google News RSS con el nombre (y el nombre público) para
     saber si esa persona ya aparece en prensa y con qué rol.
  3. DeepSeek V4 Flash **lee esa evidencia y solo esa**: cruza el nombre del
     perfil con el nombre de la candidatura y devuelve un veredicto por red.
     No navega, no completa lo que falta y no puede subir de `no_verificable`
     cuando el sondeo no respondió — está en el system prompt y se vuelve a
     imponer al armar la respuesta (`_sellar_veredictos`).

Un sondeo que no responde NO es un perfil falso: las tres redes bloquean
tráfico de datacenter de forma intermitente, así que la Lambda distingue
«no existe» (404 limpio) de «no pude comprobarlo» (bloqueo, timeout, login
wall). El frontend deja continuar en los dos casos, pero marca cuál es cuál.

Body JSON (POST):
{
  "nombre": "Alejandra Palacio Restrepo",
  "alias": "La Profe",                        # opcional · nombre público o mote
  "corp": "concejo",                          # opcional · corporación a la que aspira
  "territorio": "Bogotá D.C.",                # opcional
  "redes": [{"red": "x", "handle": "apalacio"},
            {"red": "tiktok", "handle": "laprofe"}]
}

Respuesta:
{
  "ok": true,
  "perfiles": [{
     "red": "x", "handle": "apalacio", "url": "https://x.com/apalacio",
     "veredicto": "confirmado|probable|dudoso|no_encontrado|no_verificable",
     "confianza": 0-100,
     "existe": true|false|null,               # null = no se pudo comprobar
     "nombre_perfil": "…", "seguidores": 1234, "verificada": true,
     "sondeo": "ok|no_encontrado|bloqueado|error",
     "motivo": "una frase con POR QUÉ ese veredicto"
  }],
  "resumen": "…", "riesgo_homonimo": "…", "alertas": ["…"],
  "titulares": [{"titulo": "…", "medio": "…", "fecha": "…", "link": "…"}],
  "modelo": "deepseek-v4-flash", "generado_en": "ISO 8601", "cache_hit": false
}

ENV:
  DEEPSEEK_API_KEY   clave de DeepSeek (la misma de las otras Lambdas)
  DEEPSEEK_URL       default https://api.deepseek.com/chat/completions
  DEEPSEEK_MODEL     default deepseek-v4-flash
  C360_SERVICE_TOKEN si está, EXIGE la cabecera X-C360-Service con ese valor
                     (lo manda el worker rr-auth; sin él la Lambda es abierta
                     y cualquiera puede quemar DeepSeek — ver README)
  S3_BUCKET          default elecciones-2026
  CACHE_PREFIX       default ricardoruiz.co/candidato-360/redes-cache
  CACHE_TTL_DIAS     default 7
  ALLOWED_ORIGINS_EXTRA / STRICT_ORIGIN   igual que las demás Lambdas del repo
  PROMPT_VERSION     default v1 (bumpear invalida el cache)
"""
import hashlib
import json
import os
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = os.environ.get("DEEPSEEK_URL", "https://api.deepseek.com/chat/completions")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
SERVICE_TOKEN = os.environ.get("C360_SERVICE_TOKEN", "")
S3_BUCKET = os.environ.get("S3_BUCKET", "elecciones-2026")
CACHE_PREFIX = os.environ.get("CACHE_PREFIX", "ricardoruiz.co/candidato-360/redes-cache")
CACHE_TTL_DIAS = int(os.environ.get("CACHE_TTL_DIAS", "7"))
PROMPT_VERSION = os.environ.get("PROMPT_VERSION", "v1")
MAX_BODY_BYTES = int(os.environ.get("MAX_BODY_BYTES", "8000"))
MAX_REDES = 3
SONDEO_TIMEOUT = 8
NOTICIAS_TIMEOUT = 12
DEEPSEEK_TIMEOUT = 45

# Un User-Agent de navegador no es evasión: los tres endpoints devuelven 403 a
# urllib por defecto y con eso NINGÚN sondeo se podría comprobar nunca.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

ALLOWED_ORIGINS = {
    "https://ricardoruiz.co",
    "https://www.ricardoruiz.co",
    "http://localhost:8765",
}
ALLOWED_ORIGINS |= {
    o.strip() for o in os.environ.get("ALLOWED_ORIGINS_EXTRA", "").split(",")
    if o.strip().startswith(("https://", "http://localhost"))
}
STRICT_ORIGIN = os.environ.get("STRICT_ORIGIN", "true").lower() == "true"

REDES = {
    "x": {"nombre": "X (antes Twitter)", "url": "https://x.com/{h}"},
    "tiktok": {"nombre": "TikTok", "url": "https://www.tiktok.com/@{h}"},
    "instagram": {"nombre": "Instagram", "url": "https://www.instagram.com/{h}/"},
}

_s3 = None


def _s3_client():
    global _s3
    if _s3 is None:
        import boto3
        _s3 = boto3.client("s3")
    return _s3


# ── Normalización ──────────────────────────────────────────────────────────
_HANDLE_OK = re.compile(r"^[A-Za-z0-9._]{1,30}$")


def _limpiar_handle(valor):
    """'https://www.instagram.com/la.profe/?hl=es' → 'la.profe'. El usuario
    pega la URL completa tan seguido como escribe el @; las dos entran."""
    s = str(valor or "").strip()
    s = re.sub(r"^https?://", "", s, flags=re.I)
    s = re.sub(r"^www\.", "", s, flags=re.I)
    s = re.sub(r"^(x|twitter|tiktok|instagram)\.com/", "", s, flags=re.I)
    s = s.split("?")[0].split("#")[0].strip("/")
    s = s.split("/")[0]
    return s.lstrip("@").strip()


def _sin_tildes(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s or ""))
                   if unicodedata.category(c) != "Mn")


def _fetch(url, timeout, accept="*/*"):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": accept, "Accept-Language": "es-CO,es;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


# ── 1. Sondeo por red ──────────────────────────────────────────────────────
# Cada sondeo devuelve el mismo dict: estado del sondeo + lo que la red dijo.
# `existe: None` es «no me dejaron comprobar», y NO se puede confundir con False.
def _vacio(estado, detalle=""):
    return {"sondeo": estado, "existe": None, "nombre_perfil": None,
            "seguidores": None, "verificada": None, "detalle": detalle}


def _sondeo_x(handle):
    """Endpoint del botón «Follow» de X: JSON público, sin llave. Devuelve
    lista vacía cuando el usuario no existe."""
    url = ("https://cdn.syndication.twimg.com/widgets/followbutton/info.json"
           f"?screen_names={urllib.parse.quote(handle)}")
    try:
        status, raw = _fetch(url, SONDEO_TIMEOUT, "application/json")
    except urllib.error.HTTPError as e:
        return _vacio("bloqueado" if e.code in (401, 403, 429) else "error", f"HTTP {e.code}")
    except Exception as e:
        return _vacio("error", type(e).__name__)
    if status != 200:
        return _vacio("error", f"HTTP {status}")
    try:
        datos = json.loads(raw)
    except Exception:
        return _vacio("bloqueado", "respuesta no-JSON (X sirvió una página, no el widget)")
    if not isinstance(datos, list) or not datos:
        return {"sondeo": "no_encontrado", "existe": False, "nombre_perfil": None,
                "seguidores": None, "verificada": None,
                "detalle": "X respondió sin cuenta para ese usuario"}
    d = datos[0] or {}
    return {"sondeo": "ok", "existe": True,
            "nombre_perfil": d.get("name"),
            "seguidores": d.get("followers_count"),
            "verificada": bool(d.get("verified")),
            "detalle": "widget público de X"}


def _sondeo_tiktok(handle):
    """oEmbed oficial de TikTok: público y estable. 400/404 = no existe."""
    perfil = f"https://www.tiktok.com/@{urllib.parse.quote(handle)}"
    url = "https://www.tiktok.com/oembed?url=" + urllib.parse.quote(perfil, safe="")
    try:
        status, raw = _fetch(url, SONDEO_TIMEOUT, "application/json")
    except urllib.error.HTTPError as e:
        if e.code in (400, 404):
            return {"sondeo": "no_encontrado", "existe": False, "nombre_perfil": None,
                    "seguidores": None, "verificada": None,
                    "detalle": f"oEmbed de TikTok respondió {e.code}"}
        return _vacio("bloqueado" if e.code in (403, 429) else "error", f"HTTP {e.code}")
    except Exception as e:
        return _vacio("error", type(e).__name__)
    try:
        d = json.loads(raw)
    except Exception:
        return _vacio("bloqueado", "respuesta no-JSON")
    if not d.get("author_name") and not d.get("author_unique_id"):
        return _vacio("bloqueado", "oEmbed sin autor")
    return {"sondeo": "ok", "existe": True,
            "nombre_perfil": d.get("author_name"),
            "seguidores": None, "verificada": None,
            "detalle": "oEmbed público de TikTok (el conteo de seguidores no viene en esta fuente)"}


_IG_TITULO = re.compile(r'<meta property="og:title" content="([^"]+)"', re.I)
_IG_DESC = re.compile(r'<meta property="og:description" content="([^"]+)"', re.I)
_IG_SEGUIDORES = re.compile(r"([\d.,]+)\s*(K|M|mil|millones)?\s*(?:Followers|seguidores)", re.I)


def _sondeo_instagram(handle):
    """Instagram no tiene endpoint público sin token. Se lee la página del
    perfil: si sirve el `og:title` hay cuenta; si redirige al login, el sondeo
    queda en «bloqueado» — que no es lo mismo que «no existe»."""
    url = f"https://www.instagram.com/{urllib.parse.quote(handle)}/"
    try:
        status, raw = _fetch(url, SONDEO_TIMEOUT, "text/html")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"sondeo": "no_encontrado", "existe": False, "nombre_perfil": None,
                    "seguidores": None, "verificada": None,
                    "detalle": "Instagram respondió 404"}
        return _vacio("bloqueado" if e.code in (401, 403, 429) else "error", f"HTTP {e.code}")
    except Exception as e:
        return _vacio("error", type(e).__name__)
    html = raw.decode("utf-8", "ignore")
    if ("loginForm" in html or "accounts/login" in html) and "og:title" not in html:
        return _vacio("bloqueado", "Instagram sirvió el muro de login")
    m = _IG_TITULO.search(html)
    if not m:
        return _vacio("bloqueado", "la página no trajo metadatos de perfil")
    titulo = m.group(1)
    desc = (_IG_DESC.search(html).group(1) if _IG_DESC.search(html) else "")
    seg = _IG_SEGUIDORES.search(desc)
    return {"sondeo": "ok", "existe": True,
            "nombre_perfil": titulo.split("(")[0].split("•")[0].strip(),
            "seguidores": seg.group(0).strip() if seg else None,
            "verificada": None,
            "detalle": f"metadatos públicos del perfil · {desc[:160]}" if desc else "metadatos públicos del perfil"}


SONDEOS = {"x": _sondeo_x, "tiktok": _sondeo_tiktok, "instagram": _sondeo_instagram}


# ── 2. Señales abiertas (Google News RSS) ──────────────────────────────────
def _noticias(nombre, alias, territorio):
    """Las mismas reglas del briefing: comillas para que sea la persona y no
    sus palabras sueltas. Sin titulares NO pasa nada: es una señal más."""
    consultas = [f'"{nombre}"']
    if alias and _sin_tildes(alias).lower() != _sin_tildes(nombre).lower():
        consultas.append(f'"{alias}"' + (f" {territorio}" if territorio else ""))
    vistos, salida = set(), []
    for q in consultas:
        qs = urllib.parse.urlencode({"q": f"{q} when:365d", "hl": "es-419",
                                     "gl": "CO", "ceid": "CO:es-419"})
        try:
            _, raw = _fetch(f"https://news.google.com/rss/search?{qs}",
                            NOTICIAS_TIMEOUT, "application/rss+xml")
            root = ET.fromstring(raw)
        except Exception:
            continue
        ch = root.find("channel")
        items = ch.findall("item") if ch is not None else root.findall(".//item")
        for it in items[:12]:
            titulo = (it.findtext("title") or "").strip()
            if not titulo or titulo in vistos:
                continue
            vistos.add(titulo)
            src = it.find("source")
            salida.append({"titulo": titulo.rsplit(" - ", 1)[0],
                           "medio": (src.text.strip() if src is not None and src.text else ""),
                           "fecha": (it.findtext("pubDate") or "").strip(),
                           "link": (it.findtext("link") or "").strip()})
    return salida[:14]


# ── 3. Veredicto (DeepSeek) ────────────────────────────────────────────────
SYSTEM_PROMPT = """Eres el verificador de identidad de Candidato 360, la plataforma electoral de Ricardo Ruiz (Colombia).

Recibes: el nombre de una persona que va a inscribir una candidatura, su nombre público si lo dio, el territorio y la corporación a la que aspira, el SONDEO TÉCNICO de cada red social que declaró, y titulares de prensa abierta sobre ese nombre.

Tu único trabajo es decir, red por red, si la cuenta que esa persona escribió parece ser la suya.

REGLAS INNEGOCIABLES
1. NO tienes acceso a internet. Solo puedes usar la evidencia del mensaje. Si algo no está ahí, no existe para ti.
2. NUNCA inventes seguidores, biografías, publicaciones, fechas ni verificaciones. Si un dato no vino en el sondeo, no lo menciones.
3. El sondeo manda sobre tu intuición:
   · sondeo "no_encontrado" → veredicto OBLIGATORIO "no_encontrado".
   · sondeo "bloqueado" o "error" → veredicto OBLIGATORIO "no_verificable" (la red no dejó comprobar; NO es una cuenta falsa).
   · sondeo "ok" → eliges entre "confirmado", "probable" o "dudoso" comparando el nombre del perfil con el nombre de la candidatura.
4. "confirmado" exige que el nombre del perfil contenga el nombre y un apellido de la persona, o exactamente su nombre público. Si el perfil trae otro nombre propio, es "dudoso" y lo dices.
5. Homonimia: en Colombia los nombres se repiten. Si los titulares hablan de alguien con ese nombre pero con otro oficio o en otra ciudad, adviértelo en riesgo_homonimo.
6. Escribe en español de Colombia, en usted, sin adjetivos de marketing. Cada motivo es UNA frase que dice en qué te apoyaste.

Devuelve SOLO este JSON:
{
  "perfiles": [{"red": "x|tiktok|instagram", "veredicto": "confirmado|probable|dudoso|no_encontrado|no_verificable", "confianza": 0-100, "motivo": "una frase"}],
  "resumen": "2 frases máximo: qué identidad pública vamos a monitorear y con qué certeza",
  "riesgo_homonimo": "una frase, o cadena vacía si no hay riesgo",
  "alertas": ["lo que la persona debería corregir antes de seguir (máximo 3, puede ir vacío)"]
}"""


def _user_msg(payload, sondeos, titulares):
    L = []
    L.append(f"CANDIDATURA: {payload.get('nombre') or '—'}")
    if payload.get("alias"):
        L.append(f"NOMBRE PÚBLICO O MOTE: {payload['alias']}")
    if payload.get("corp"):
        L.append(f"ASPIRA A: {payload['corp']}")
    if payload.get("territorio"):
        L.append(f"TERRITORIO: {payload['territorio']}")
    L.append("")
    L.append("SONDEO TÉCNICO POR RED (fuente pública de cada plataforma, hecho hace segundos):")
    for s in sondeos:
        L.append(f"  · {REDES[s['red']]['nombre']} — usuario declarado: @{s['handle']} ({s['url']})")
        L.append(f"      estado del sondeo: {s['sondeo']}")
        L.append(f"      la cuenta existe: {'sí' if s['existe'] else ('no' if s['existe'] is False else 'no se pudo comprobar')}")
        if s.get("nombre_perfil"):
            L.append(f"      nombre que muestra el perfil: {s['nombre_perfil']}")
        if s.get("seguidores") is not None:
            L.append(f"      seguidores según la fuente: {s['seguidores']}")
        if s.get("verificada"):
            L.append("      la plataforma la marca como verificada")
        if s.get("detalle"):
            L.append(f"      nota técnica: {s['detalle']}")
    L.append("")
    if titulares:
        L.append(f"TITULARES DE PRENSA ABIERTA CON ESE NOMBRE (últimos 12 meses, {len(titulares)}):")
        for t in titulares:
            L.append(f"  · {t['titulo']} — {t['medio'] or 'medio sin identificar'}")
    else:
        L.append("TITULARES DE PRENSA ABIERTA: ninguno. No concluyas nada de esto: la mayoría de las candidaturas nuevas no tienen prensa.")
    L.append("")
    L.append("Devuelve el JSON con un objeto por cada red listada arriba, en el mismo orden.\nJSON:")
    return "\n".join(L)


def _call_deepseek(payload, sondeos, titulares):
    body = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                     {"role": "user", "content": _user_msg(payload, sondeos, titulares)}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "max_tokens": 1400,
    }).encode("utf-8")
    req = urllib.request.Request(DEEPSEEK_URL, data=body, headers={
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=DEEPSEEK_TIMEOUT) as r:
        resp = json.loads(r.read())
    return json.loads(resp["choices"][0]["message"]["content"])


VEREDICTOS = {"confirmado", "probable", "dudoso", "no_encontrado", "no_verificable"}


def _sellar_veredictos(sondeos, lectura):
    """El sondeo es el hecho; el modelo solo lo interpreta. Si DeepSeek se sale
    del carril (dice «confirmado» sobre una red que no respondió), acá se
    corrige: la regla 3 del prompt se vuelve a aplicar en código."""
    por_red = {}
    for p in (lectura.get("perfiles") or []):
        if isinstance(p, dict) and p.get("red"):
            por_red[str(p["red"]).lower()] = p
    salida = []
    for s in sondeos:
        p = por_red.get(s["red"], {})
        veredicto = str(p.get("veredicto") or "").lower()
        motivo = str(p.get("motivo") or "").strip()
        try:
            confianza = max(0, min(100, int(p.get("confianza"))))
        except (TypeError, ValueError):
            confianza = 0
        if s["sondeo"] == "no_encontrado":
            veredicto, confianza = "no_encontrado", 0
            motivo = motivo or f"{REDES[s['red']]['nombre']} respondió que ese usuario no tiene cuenta."
        elif s["sondeo"] in ("bloqueado", "error"):
            veredicto, confianza = "no_verificable", 0
            motivo = motivo or f"{REDES[s['red']]['nombre']} no dejó comprobar la cuenta desde el servidor; revísela usted."
        elif veredicto not in VEREDICTOS or veredicto in ("no_encontrado", "no_verificable"):
            veredicto = "probable"
            motivo = motivo or "La cuenta existe; el nombre del perfil no alcanzó para confirmarla."
        salida.append({
            "red": s["red"], "handle": s["handle"], "url": s["url"],
            "veredicto": veredicto, "confianza": confianza, "motivo": motivo,
            "existe": s["existe"], "sondeo": s["sondeo"],
            "nombre_perfil": s.get("nombre_perfil"), "seguidores": s.get("seguidores"),
            "verificada": s.get("verificada"),
        })
    return salida


# ── Cache ──────────────────────────────────────────────────────────────────
def _cache_key(payload, sondeos):
    """El sondeo entra en la llave: si mañana la cuenta aparece o cambia de
    nombre, es otra pregunta y no puede contestarla el cache de ayer."""
    base = {
        "n": _sin_tildes(payload.get("nombre", "")).lower(),
        "a": _sin_tildes(payload.get("alias", "")).lower(),
        "t": _sin_tildes(payload.get("territorio", "")).lower(),
        "c": payload.get("corp", ""),
        "s": [[s["red"], s["handle"].lower(), s["sondeo"],
               str(s.get("nombre_perfil") or "")] for s in sondeos],
        "v": PROMPT_VERSION,
    }
    return hashlib.sha256(json.dumps(base, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:32]


def _cache_leer(key):
    try:
        obj = _s3_client().get_object(Bucket=S3_BUCKET, Key=f"{CACHE_PREFIX}/{key}.json")
        datos = json.loads(obj["Body"].read())
        nacido = datetime.fromisoformat(datos.get("generado_en", "").replace("Z", "+00:00"))
        if datetime.now(timezone.utc) - nacido > timedelta(days=CACHE_TTL_DIAS):
            return None
        return datos
    except Exception:
        return None


def _cache_escribir(key, datos):
    try:
        _s3_client().put_object(
            Bucket=S3_BUCKET, Key=f"{CACHE_PREFIX}/{key}.json",
            Body=json.dumps(datos, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json", CacheControl="private, max-age=600")
    except Exception:
        pass


# ── HTTP ───────────────────────────────────────────────────────────────────
def _cors(origin):
    permitido = origin if origin in ALLOWED_ORIGINS else ("" if STRICT_ORIGIN else "*")
    return {"Access-Control-Allow-Origin": permitido,
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, X-C360-Service",
            "Access-Control-Max-Age": "300", "Vary": "Origin",
            "Content-Type": "application/json"}


def _resp(status, body, origin=""):
    return {"statusCode": status, "headers": _cors(origin),
            "body": json.dumps(body, ensure_ascii=False)}


def _leer_redes(payload):
    """Normaliza y descarta lo que no es un usuario. Máximo tres: cada red es
    una llamada de red y el wizard no ofrece más."""
    salida, vistos = [], set()
    for item in (payload.get("redes") or [])[:6]:
        if not isinstance(item, dict):
            continue
        red = str(item.get("red") or "").lower().strip()
        handle = _limpiar_handle(item.get("handle"))
        if red not in REDES or not handle or red in vistos:
            continue
        if not _HANDLE_OK.match(handle):
            continue
        vistos.add(red)
        salida.append({"red": red, "handle": handle,
                       "url": REDES[red]["url"].format(h=handle)})
        if len(salida) >= MAX_REDES:
            break
    return salida


def handler(event, context):
    headers = {str(k).lower(): v for k, v in (event.get("headers") or {}).items()}
    origin = headers.get("origin", "")
    method = ((event.get("requestContext", {}).get("http", {}) or {}).get("method")
              or event.get("httpMethod") or "POST")
    if method == "OPTIONS":
        return _resp(204, {}, origin)
    # Con secreto configurado, esta Lambda solo habla con el worker: sin la
    # cabecera responde 404, como una ruta que no existe (patrón de Caudal).
    if SERVICE_TOKEN and headers.get("x-c360-service") != SERVICE_TOKEN:
        return _resp(404, {"error": "not found"}, origin)
    if not SERVICE_TOKEN and STRICT_ORIGIN and origin and origin not in ALLOWED_ORIGINS:
        return _resp(403, {"error": "origin not allowed"}, origin)

    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64
        raw = base64.b64decode(raw).decode("utf-8")
    if len(raw) > MAX_BODY_BYTES:
        return _resp(413, {"error": "body too large"}, origin)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return _resp(400, {"error": "invalid json"}, origin)

    nombre = str(payload.get("nombre") or "").strip()
    if len(nombre) < 3:
        return _resp(400, {"error": "falta_nombre"}, origin)
    redes = _leer_redes(payload)
    if not redes:
        return _resp(400, {"error": "sin_redes",
                           "detalle": "Marque al menos una red y escriba el usuario."}, origin)
    if not DEEPSEEK_API_KEY:
        return _resp(500, {"error": "DEEPSEEK_API_KEY no configurada"}, origin)

    sondeos = []
    for r in redes:
        s = SONDEOS[r["red"]](r["handle"])
        s.update({"red": r["red"], "handle": r["handle"], "url": r["url"]})
        sondeos.append(s)

    key = _cache_key(payload, sondeos)
    cacheado = _cache_leer(key)
    if cacheado:
        cacheado["cache_hit"] = True
        return _resp(200, cacheado, origin)

    titulares = _noticias(nombre, payload.get("alias"), payload.get("territorio"))
    try:
        lectura = _call_deepseek(payload, sondeos, titulares)
    except urllib.error.HTTPError as e:
        return _resp(502, {"error": "deepseek_http", "status": e.code,
                           "detalle": "El modelo no contestó. Intente de nuevo en un minuto."}, origin)
    except Exception as e:
        return _resp(502, {"error": "deepseek_falló", "detalle": type(e).__name__}, origin)

    salida = {
        "ok": True,
        "perfiles": _sellar_veredictos(sondeos, lectura),
        "resumen": str(lectura.get("resumen") or "").strip(),
        "riesgo_homonimo": str(lectura.get("riesgo_homonimo") or "").strip(),
        "alertas": [str(a) for a in (lectura.get("alertas") or [])][:3],
        "titulares": titulares[:6],
        "modelo": DEEPSEEK_MODEL,
        "prompt_version": PROMPT_VERSION,
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "cache_hit": False,
    }
    _cache_escribir(key, salida)
    return _resp(200, salida, origin)


# ── CLI ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    ejemplo = {
        "nombre": "Alejandra Palacio Restrepo",
        "alias": "La Profe",
        "corp": "Concejo municipal o distrital",
        "territorio": "Bogotá D.C.",
        "redes": [{"red": "x", "handle": "@petrogustavo"},
                  {"red": "tiktok", "handle": "tiktok"},
                  {"red": "instagram", "handle": "instagram"}],
    }
    if "--sondeo" in sys.argv:
        for r in _leer_redes(ejemplo):
            s = SONDEOS[r["red"]](r["handle"])
            print(f"{r['red']:>10} @{r['handle']:<18} {json.dumps(s, ensure_ascii=False)}")
    elif "--prompt" in sys.argv:
        sondeos = []
        for r in _leer_redes(ejemplo):
            s = SONDEOS[r["red"]](r["handle"])
            s.update(r)
            sondeos.append(s)
        print("=== SYSTEM ===\n" + SYSTEM_PROMPT)
        print("\n=== USER ===\n" + _user_msg(ejemplo, sondeos, _noticias(ejemplo["nombre"], ejemplo["alias"], ejemplo["territorio"])))
    else:
        print(json.dumps(json.loads(handler({"body": json.dumps(ejemplo)}, None)["body"]),
                         ensure_ascii=False, indent=2))
