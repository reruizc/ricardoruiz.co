#!/usr/bin/env python3
"""
test-presidencial-explica · lambda_handler.py

Endpoint POST que recibe el state del usuario del test presidencial 2026
y devuelve una lectura personalizada redactada por DeepSeek V3.

Reglas:
- La Lambda NUNCA inventa datos sobre el candidato. Recibe el state ya
  calculado (arquetipo dominante, candidato declarado, demografía, prio)
  y solo redacta sobre eso.
- Plantilla cerrada, temperature baja (0.3), max_tokens limitado.
- Response_format JSON para forzar estructura.
- Cache opcional en S3 bajo cache/{hash}.json — si dos personas con la
  misma combinación piden la lectura, devuelve el cache.

Body JSON esperado (POST):
{
  "registro": "popular" | "digital" | "analitico",
  "candidato": { "id": "ic", "nombre": "Iván Cepeda", "partido": "Pacto Histórico" },
  "candidato_origen": "declarado" | "sugerido",
  "demografia": { "edad": "36-50", "identidad": "barrio" },
  "prio": ["salud", "costo_vida"],
  "arquetipo_dominante": { "id": "castigo", "nombre": "Castigo a la restauración y demanda de alternancia", "pct": 42 },
  "arquetipo_secundario": { "id": "pertenencia", "nombre": "Pertenencia comunitaria y autonomía territorial", "pct": 24 },
  "arq_score": { "proteccion": 0, "estabilidad": 4, "supervivencia": 2, "castigo": 14, "pertenencia": 8 }
}

Response JSON:
{
  "lectura": "3 párrafos de 60-80 palabras c/u sobre lo dijo / lo que muestran las respuestas / el contraste.",
  "mensaje_corto": "Una frase de 12-18 palabras lista para meme o redes.",
  "alineacion": "alineado" | "vientos_cruzados" | "neutro",
  "modelo": "deepseek-chat",
  "generado_en": "ISO 8601 UTC",
  "cache_hit": true | false
}

ENV vars:
  DEEPSEEK_API_KEY  · clave de DeepSeek (la misma que ya usas en agenda-medios-recomienda)
  DEEPSEEK_URL      · default https://api.deepseek.com/chat/completions
  DEEPSEEK_MODEL    · default deepseek-chat (DeepSeek V3)
  S3_BUCKET         · default elecciones-2026
  CACHE_PREFIX      · default ricardoruiz.co/test-presidencial-2026/cache
  CACHE_TTL_DIAS    · default 14
"""

import hashlib
import json
import os
import re
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone

# ---- Config ----
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = os.environ.get("DEEPSEEK_URL", "https://api.deepseek.com/chat/completions")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
S3_BUCKET = os.environ.get("S3_BUCKET", "elecciones-2026")
CACHE_PREFIX = os.environ.get("CACHE_PREFIX", "ricardoruiz.co/test-presidencial-2026/cache")
RESPONSES_PREFIX = os.environ.get("RESPONSES_PREFIX", "ricardoruiz.co/test-presidencial-2026/responses")
HUELLA_KEY = os.environ.get("HUELLA_KEY", "ricardoruiz.co/congreso-2026/output/huella/huella-territorial.json")
PROGRAMAS_KEY = os.environ.get("PROGRAMAS_KEY", "ricardoruiz.co/congreso-2026/output/test-presidencial/programas-candidatos.json")

# Temas de PRIO del test → palabras clave para casar con el "tema" de un eje
PRIO_KEYWORDS = {
    "seguridad": ["segur", "justicia", "crimen", "orden", "paz"],
    "economia": ["econom", "fiscal", "empleo", "trabajo", "macro", "tribut"],
    "salud": ["salud"],
    "costo_vida": ["costo", "pobreza", "social", "cuidado", "vivienda", "ingreso"],
    "anticorrupcion": ["corrup", "transparen"],
    "exterior": ["exterior", "internacional", "política exterior"],
    "agraria": ["campo", "agrar", "rural", "tierra"],
    "instituciones": ["instituc", "constitu", "estado", "descentral", "democra"],
    "educacion": ["educ", "ciencia", "tecnolog"],
    "ambiente": ["ambient", "energ", "climá", "transición"],
}
CACHE_TTL_DIAS = int(os.environ.get("CACHE_TTL_DIAS", "14"))
HTTP_TIMEOUT = 55

# Nombre canonico de los 6 candidatos (para la huella)
CAND_NOMBRES = {
    "ic": "Iván Cepeda",
    "ae": "Abelardo de la Espriella",
    "pv": "Paloma Valencia",
    "sf": "Sergio Fajardo",
    "cl": "Claudia López",
    "rb": "Roy Barreras",
}

# Ponderador nacional (% intencion 1a vuelta) — sincronizado con
# previa-1v.html / POND_NAC del frontend. Si cambia el ponderador, actualizar.
POND_NAC = {"ic": 38.75, "ae": 23.94, "pv": 19.55, "sf": 3.03, "cl": 2.58, "rb": 0.37}

# Lente posicional + tono de cada candidato (de candidatos.json). NO es un
# programa de gobierno: es el marco ideologico para que el modelo conecte
# las prioridades del usuario con el candidato sin inventar propuestas.
LENTE_CAND = {
    "ic": {"lente": "Heredero del cambio. Lectura de clase, denuncia de las élites, defensa del legado del actual gobierno, perspectiva del pueblo y los movimientos sociales.",
           "tono": "continuar la transformación, no entregarle el país a los mismos de siempre, defender lo conquistado."},
    "ae": {"lente": "Anti-establishment desde la derecha. Mano dura, anti-élite política tradicional, defensa de la propiedad y la familia, rabia frente al gobierno actual.",
           "tono": "acabar con la mermelada, recuperar el país, sacar a los corruptos sin importar el bando."},
    "pv": {"lente": "Uribismo estructurado. Seguridad democrática, confianza inversionista, oposición frontal al Pacto, institucionalidad conservadora.",
           "tono": "orden, autoridad, libertad económica, devolver el rumbo al país."},
    "sf": {"lente": "Educación primero, consensos antes que confrontación, evitación de los extremos, talante académico antioqueño.",
           "tono": "no caer en la polarización, educación, juntar a los moderados de todos los lados."},
    "cl": {"lente": "Tecnocrática, ex-alcaldesa de Bogotá, anti-Petro pero también anti-uribismo, derechos con gestión eficiente.",
           "tono": "gestión con resultados, ni populismos de izquierda ni corrupción de la vieja derecha, modernización."},
    "rb": {"lente": "Ex-petrista conciliador, paz total con matices, puente entre el cambio y la institucionalidad sin romper con ninguno.",
           "tono": "cerrar el ciclo de violencia, juntar a quienes quieren paz sin sectarismo, gobernar con todos."},
}

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json; charset=utf-8",
}

# Tono por registro.
TONO = {
    "popular": "coloquial colombiano, frases cortas. Muletillas suaves OK ('pues', 'la verdad').",
    "digital": "irónico, formato POV, máximo 1 emoji por párrafo.",
    "analitico": "neutro elevado, vocabulario político preciso, frases completas.",
}

# Tono regional según el departamento. Sobrepone el default del registro.
TONO_REGIONAL = {
    "voseo_paisa": "voseo paisa colombiano ('vos pensás', 'sabés', 'querés'). Paisa de Medellín/Eje Cafetero.",
    "voseo_caleño": "voseo caleño/vallecaucano ('vos sabés', 'mirá vos', 've').",
    "ustedeo_boyacense": "ustedeo formal boyacense ('usted dice', 'lo que usted siente'). NO tutees.",
    "tuteo_costeño": "tuteo costeño relajado ('tú dices', 'ajá').",
    "tuteo_neutro": "tuteo neutro colombiano de Bogotá ('tú dices', 'tú sientes').",
}

SYSTEM_PROMPT = """Eres un analista electoral colombiano que le explica a un ciudadano el resultado de su test para la presidencial 2026. Recibes un STATE con candidato declarado, demografía, ubicación con tono regional, prioridades y un perfil emocional interno.

Tu trabajo: REDACTAR una lectura cercana y honesta. No inventas datos. No mencionas otros candidatos. No recomiendas voto.

Devuelves JSON estricto:
{
  "lectura": "Dos párrafos de 70-90 palabras cada uno, separados por \\n\\n. (1) Lo que el usuario declaró + lo que su perfil revela, EXPLICADO en lenguaje cotidiano (qué lo mueve, con qué conecta) — sin etiquetas técnicas. (2) Cómo le va a su candidato en su zona y por qué, conectando con lo que el usuario prioriza.",
  "mensaje_corto": "Frase de 12-18 palabras para meme o redes.",
  "alineacion": "alineado" | "vientos_cruzados" | "neutro"
}

REGLAS:
1. Adapta el lenguaje al 'tono_regional' del STATE. NUNCA uses voseo argentino, 'che' ni vocabulario argentino.
2. Honra el REGISTRO (popular/digital/analítico).
3. Si el candidato fue 'sugerido' por el mini-test, dilo.
4. PROHIBIDO nombrar el arquetipo emocional o decir porcentajes de arquetipo. El perfil es señal interna: tradúcelo a lenguaje natural sobre lo que al usuario lo mueve.
   ✗ MAL: "Tu arquetipo principal es Pertenencia comunitaria y autonomía territorial (43%), con matiz de Continuidad pragmática (29%)".
   ✓ BIEN: "conectás con la idea de fortalecer la comunidad local desde una gestión cercana, pero con los pies en la tierra en lo económico".
5. PROHIBIDO citar cifras electorales crudas (votación pasada, consultas, "huella 0.95×", nombres de quién ganó en su zona). Para el territorio usa SOLO el veredicto cualitativo y la intención proyectada del CONTEXTO DE LA ZONA, fraseados como ahí se indica.
   ✗ MAL: "tu municipio votó Petro 42.8%, Cepeda sacó 59.1% en la consulta 2025, huella 0.95×".
   ✓ BIEN: "a tu candidato le va regular porque, con el histórico y las encuestas, proyecta cerca de 18% en tu barrio".
6. Hay un bloque PROGRAMA OFICIAL con propuestas REALES del plan de gobierno del candidato. En el 2º párrafo, conecta lo que el usuario priorizó con 1-2 propuestas concretas de ese bloque (cítalas en lenguaje natural, ej: "su plan propone X"). Es la única fuente de propuestas: lo que NO esté en ese bloque NO existe — jamás inventes una propuesta.
7. Solo el JSON, sin markdown ni texto extra."""


# ---- AWS clients (lazy) ----
_s3 = None
def _s3_client():
    global _s3
    if _s3 is None:
        import boto3  # type: ignore
        _s3 = boto3.client("s3")
    return _s3


# ---- Huella territorial (cache por contenedor warm) ----
_huella = None

def _slug(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()


def _pad2(s):
    s = str(s or "").strip()
    return s.zfill(2) if s else "00"


def _pad3(s):
    s = str(s or "").strip()
    return s.zfill(3) if s else "000"


def _load_huella():
    """Carga huella-territorial.json desde S3, cachea en memoria del contenedor warm."""
    global _huella
    if _huella is not None:
        return _huella
    try:
        obj = _s3_client().get_object(Bucket=S3_BUCKET, Key=HUELLA_KEY)
        _huella = json.loads(obj["Body"].read().decode("utf-8"))
        print(f"[huella] cargada: {_huella.get('n_barrios')} barrios, {_huella.get('n_muns')} muns")
    except Exception as e:
        print(f"[huella] WARN no cargo: {e}")
        _huella = {}
    return _huella


_programas = None
def _load_programas():
    """Carga programas-candidatos.json (destilado de los PDFs oficiales),
    cachea en memoria del contenedor warm."""
    global _programas
    if _programas is not None:
        return _programas
    try:
        obj = _s3_client().get_object(Bucket=S3_BUCKET, Key=PROGRAMAS_KEY)
        data = json.loads(obj["Body"].read().decode("utf-8"))
        _programas = data.get("candidatos") or data
        print(f"[programas] cargados: {list(_programas.keys())}")
    except Exception as e:
        print(f"[programas] WARN no cargo: {e}")
        _programas = {}
    return _programas


def _format_programa_block(candidato_id, prio):
    """Bloque del PROGRAMA REAL del candidato declarado. Compacto: slogan +
    banderas + los ejes que casan con lo que el usuario priorizó. Estas SÍ
    son propuestas oficiales — el modelo puede citarlas; lo que no esté aquí
    no existe. Fallback a LENTE_CAND si el programa no cargó."""
    progs = _load_programas()
    p = (progs or {}).get(candidato_id)
    cand_nom = CAND_NOMBRES.get(candidato_id, "el candidato")
    if not p:
        lente = LENTE_CAND.get(candidato_id, {})
        if not lente:
            return ""
        return (f"PROGRAMA de {cand_nom} (marco posicional, sin propuestas "
                f"específicas — NO inventes): {lente.get('lente','')} "
                f"Habla de {lente.get('tono','')}")

    lines = [f"PROGRAMA OFICIAL de {cand_nom} (propuestas REALES de su plan de "
             f"gobierno — puedes citar las que conecten; lo que no esté aquí, NO existe):"]
    if p.get("slogan"):
        lines.append(f"- Lema: {p['slogan']}")
    bands = (p.get("banderas") or [])[:5]
    if bands:
        lines.append("- Banderas: " + " | ".join(bands))
    # Ejes que casan con la PRIO del usuario (lo que de verdad le importa)
    ejes = p.get("ejes") or []
    prio_kw = []
    for t in (prio or []):
        prio_kw += PRIO_KEYWORDS.get(t, [t])
    elegidos = []
    for e in ejes:
        tema = (e.get("tema") or "").lower()
        if any(kw in tema for kw in prio_kw):
            elegidos.append(e)
    for e in elegidos[:3]:
        prop = e.get("propuestas", "")
        if len(prop) > 360:
            prop = prop[:360].rsplit(";", 1)[0] + "…"
        lines.append(f"- En {e.get('tema')}: {prop}")
    if not elegidos and ejes:
        # Sin match con prio: dar los 2 primeros ejes como muestra
        for e in ejes[:2]:
            prop = e.get("propuestas", "")
            if len(prop) > 280:
                prop = prop[:280].rsplit(";", 1)[0] + "…"
            lines.append(f"- En {e.get('tema')}: {prop}")
    return "\n".join(lines)


def _resolver_huella(huella, ubi):
    """Dado state.ubicacion, devuelve (entry | None, level)."""
    if not huella or not ubi:
        return None, None
    dep_cod = ubi.get("dep_cod")
    mun_cod = ubi.get("mun_cod")
    if not dep_cod:
        return None, None
    mun_key = f"{_pad2(dep_cod)}-{_pad3(mun_cod)}"

    barrio_raw = (ubi.get("barrio") or "").strip()
    comuna_raw = (ubi.get("comuna") or "").strip()
    barrios = huella.get("barrios") or {}

    if barrio_raw and barrios:
        barrio_slug = _slug(barrio_raw)
        comuna_slug = _slug(comuna_raw) if comuna_raw else None
        candidates = []
        for bk, entry in barrios.items():
            if entry.get("mun") != mun_key:
                continue
            parts = bk.split("::")
            if len(parts) != 3:
                continue
            _, sub_slug, bar_slug = parts
            if bar_slug != barrio_slug:
                continue
            score = 2 if (comuna_slug and sub_slug == comuna_slug) else 1
            candidates.append((score, bk, entry))
        if candidates:
            candidates.sort(reverse=True, key=lambda x: x[0])
            return candidates[0][2], "barrio"

    mun_entry = (huella.get("muns") or {}).get(mun_key)
    if mun_entry:
        return mun_entry, "mun"
    return None, None


def _veredicto(b):
    """Traduce el bias del candidato declarado a un veredicto cualitativo.
    El bias compara la afinidad de la zona vs el promedio nacional."""
    if b is None:
        return "sin dato suficiente"
    if b >= 1.15:
        return "le va muy bien"
    if b >= 1.00:
        return "le va bien"
    if b >= 0.85:
        return "le va regular"
    return "la tiene difícil"


def _pct_proyectado(bias, candidato_id):
    """Intención proyectada del candidato declarado en su zona:
    POND_NAC × bias renormalizado a 100% sobre los 6. Mismo cálculo que
    calcularIntencionBarrio() del frontend."""
    raw = {}
    tot = 0.0
    for cid in ("ic", "ae", "pv", "sf", "cl", "rb"):
        base = POND_NAC.get(cid, 0)
        b = bias.get(cid)
        v = base if b is None else base * b
        v = max(0.0, v)
        raw[cid] = v
        tot += v
    if tot <= 0 or candidato_id not in raw:
        return None
    return round(100 * raw[candidato_id] / tot, 1)


def _format_huella_block(entry, level, candidato_id):
    """Bloque de zona para el prompt. NO expone cifras electorales crudas:
    solo veredicto cualitativo + intención proyectada + microdato (censo)
    + lente del candidato. El modelo lo traduce, no lo cita literal."""
    if not entry:
        return ""
    bias = entry.get("b") or {}
    nombre = entry.get("n") or "(sin nombre)"
    subloc = entry.get("subloc") or ""
    ciudad = entry.get("ciudad") or ""
    dep = entry.get("dep") or ""
    censo = entry.get("censo") or 0

    if level == "barrio":
        ubic_str = f"{nombre} ({subloc} · {ciudad}, {dep})" if subloc else f"{nombre} ({ciudad}, {dep})"
        unidad = "barrio"
    else:
        ubic_str = f"{nombre} ({dep})"
        unidad = "municipio"

    b_declarado = bias.get(candidato_id)
    veredicto = _veredicto(b_declarado)
    pct = _pct_proyectado(bias, candidato_id)
    cand_nom = CAND_NOMBRES.get(candidato_id, "el candidato")

    lines = [
        "CONTEXTO DE LA ZONA (señal interna — NO cites números crudos, tradúcelos a lenguaje natural):",
        f"- Zona del usuario: {ubic_str}",
    ]
    if censo:
        lines.append(f"- Tamaño del {unidad}: ~{censo:,} votantes habilitados (microdato real, puedes mencionarlo en redondo).")
    lines.append(
        f"- Veredicto del candidato declarado ({cand_nom}) en su {unidad}: {veredicto.upper()} "
        f"— combinando el histórico electoral y las encuestas del ponderador propio."
    )
    if pct is not None:
        lines.append(
            f"- Intención de voto PROYECTADA de {cand_nom} en su {unidad}: ~{pct:.0f}%. "
            f"Frasea exactamente así: \"a tu candidato {veredicto} porque, con el histórico y las encuestas, "
            f"proyecta cerca de {pct:.0f}% de intención en tu {unidad}\"."
        )

    return "\n".join(lines)


# ---- Cache ----
# Bumpear cuando cambie el prompt/estructura de la lectura: invalida todo el
# cache viejo sin tener que borrar S3 (las keys nuevas no colisionan con las
# viejas, y las viejas expiran solas por TTL).
PROMPT_VERSION = "v3-2026-05-19-prog"


def _cache_key(state):
    """Hash determinista del state, ignorando órdenes irrelevantes (lista de prio).
    Incluye tono_regional + barrio/mun para que dos usuarios en barrios distintos
    del mismo dep no compartan cache, y PROMPT_VERSION para invalidar al cambiar
    el prompt."""
    ubi = state.get("ubicacion") or {}
    canon = {
        "pv": PROMPT_VERSION,
        "registro": state.get("registro"),
        "candidato_id": (state.get("candidato") or {}).get("id"),
        "candidato_origen": state.get("candidato_origen"),
        "edad": (state.get("demografia") or {}).get("edad"),
        "identidad": (state.get("demografia") or {}).get("identidad"),
        "tono_regional": ubi.get("tono_regional") or "tuteo_neutro",
        "dep_cod": ubi.get("dep_cod"),
        "mun_cod": ubi.get("mun_cod"),
        "barrio": _slug(ubi.get("barrio") or ""),
        "prio": sorted(state.get("prio") or []),
        "arq_dom_id": (state.get("arquetipo_dominante") or {}).get("id"),
        "arq_sec_id": (state.get("arquetipo_secundario") or {}).get("id"),
    }
    blob = json.dumps(canon, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:24]


def _cache_get(key):
    try:
        obj = _s3_client().get_object(Bucket=S3_BUCKET, Key=f"{CACHE_PREFIX}/{key}.json")
        data = json.loads(obj["Body"].read().decode("utf-8"))
        # validar TTL
        gen = data.get("generado_en")
        if gen:
            t = datetime.fromisoformat(gen.replace("Z", "+00:00"))
            dias = (datetime.now(timezone.utc) - t).days
            if dias > CACHE_TTL_DIAS:
                return None
        return data
    except Exception:
        return None


def _emit_event(state, alineacion):
    """Escribe un evento anónimo por completación del test, listable por fecha.
    SIN PII: no email (nunca se recibe), no lat/lon, no cod_puesto, no lectura.
    Solo señales agregables para el dashboard. Se llama también en cache-hit
    (dos personas con el mismo perfil = dos completaciones reales)."""
    try:
        import uuid
        now = datetime.now(timezone.utc)
        cand = state.get("candidato") or {}
        ubi = state.get("ubicacion") or {}
        arq_dom = state.get("arquetipo_dominante") or {}
        arq_sec = state.get("arquetipo_secundario") or {}
        canal = state.get("canal") or {}
        ev = {
            "ts": now.isoformat(),
            "canal": {
                "embed": bool(canal.get("embed")),
                "brand": (canal.get("brand") or None),
                "territorio": (canal.get("territorio") or None),
            },
            "registro": state.get("registro"),
            "candidato": cand.get("id"),
            "candidato_origen": state.get("candidato_origen"),
            "arq_dom": arq_dom.get("id"),
            "arq_dom_pct": arq_dom.get("pct"),
            "arq_sec": arq_sec.get("id"),
            "dep_cod": ubi.get("dep_cod"),
            "mun_cod": ubi.get("mun_cod"),
            "dep_nombre": ubi.get("dep_nombre"),
            "mun_nombre": ubi.get("mun_nombre"),
            "barrio": _slug(ubi.get("barrio") or "") or None,
            "alineacion": alineacion,
        }
        key = (
            f"{RESPONSES_PREFIX}/"
            f"yyyy={now:%Y}/mm={now:%m}/dd={now:%d}/"
            f"{now:%Y%m%dT%H%M%S}_{uuid.uuid4().hex[:12]}.json"
        )
        _s3_client().put_object(
            Bucket=S3_BUCKET, Key=key,
            Body=json.dumps(ev, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )
    except Exception as e:
        print(f"[event] WARN no se escribió evento: {e}")


def _cache_put(key, data):
    try:
        _s3_client().put_object(
            Bucket=S3_BUCKET,
            Key=f"{CACHE_PREFIX}/{key}.json",
            Body=json.dumps(data, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
            CacheControl="private, max-age=86400",
        )
    except Exception as e:
        print(f"[cache] WARN put falló: {e}")


# ---- DeepSeek ----
def _call_deepseek(state):
    """Llama a DeepSeek con el state ya validado. Devuelve el dict parseado del JSON."""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY no configurada")

    registro = state.get("registro") or "analitico"
    tono = TONO.get(registro, TONO["analitico"])

    cand = state.get("candidato") or {}
    demo = state.get("demografia") or {}
    ubi = state.get("ubicacion") or {}
    tono_reg_key = ubi.get("tono_regional") or "tuteo_neutro"
    tono_regional_instr = TONO_REGIONAL.get(tono_reg_key, TONO_REGIONAL["tuteo_neutro"])
    arq_dom = state.get("arquetipo_dominante") or {}
    arq_sec = state.get("arquetipo_secundario") or {}
    arq_score = state.get("arq_score") or {}
    prio = state.get("prio") or []

    ubi_linea = (
        f"{ubi.get('mun_nombre')}, {ubi.get('dep_nombre')}"
        if ubi.get("mun_nombre") else "sin declarar"
    )
    if ubi.get("barrio"):
        ubi_linea = f"{ubi.get('barrio')} · {ubi_linea}"

    # Resolver huella territorial del usuario
    huella = _load_huella()
    entry, level = _resolver_huella(huella, ubi)
    cand_id = (cand.get("id") or "").lower()
    huella_block = _format_huella_block(entry, level, cand_id) if entry else ""
    programa_block = _format_programa_block(cand_id, prio)

    user_msg = f"""STATE:
- Registro (tono): {registro} → {tono}
- Tono regional: {tono_reg_key} → {tono_regional_instr}
- Candidato declarado: {cand.get('nombre')} ({cand.get('partido')})
- Origen del candidato: {state.get('candidato_origen', 'declarado')}
- Edad: {demo.get('edad', 'sin dato')}
- Identidad cotidiana: {demo.get('identidad', 'sin dato')}
- Ubicación: {ubi_linea}
- Prioridades temáticas: {', '.join(prio) if prio else 'sin declarar'}
- Perfil emocional interno (NO lo nombres ni des %, EXPLÍCALO en lenguaje natural): dominante="{arq_dom.get('nombre')}", matiz="{arq_sec.get('nombre')}"
"""
    if huella_block:
        user_msg += "\n" + huella_block + "\n"
    if programa_block:
        user_msg += "\n" + programa_block + "\n"
    user_msg += ("\nRedacta la lectura en JSON estricto. RECUERDA: tono regional indicado (NO voseo argentino); "
                 "NO nombres el arquetipo ni des porcentajes (regla 4); NO cites cifras electorales crudas — "
                 "usa el veredicto y la intención proyectada del CONTEXTO DE LA ZONA tal como se frasea ahí (regla 5); "
                 "en el 2º párrafo conecta lo que el usuario prioriza con 1-2 propuestas REALES del PROGRAMA OFICIAL (regla 6).")

    body = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
        # DeepSeek V4 consume tokens en reasoning_content interno antes
        # de generar el content. El bloque de huella territorial sumó
        # ~400 tokens al prompt; en casos de vientos cruzados el reasoning
        # llega a 4000-5000. 8000 cubre con margen reasoning + content.
        "max_tokens": 8000,
    }).encode("utf-8")

    req = urllib.request.Request(
        DEEPSEEK_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        raw = resp.read().decode("utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(f"[deepseek] respuesta no es JSON. raw[:400]={raw[:400]}")
        raise

    choice = data["choices"][0]
    content = choice["message"].get("content") or ""
    finish = choice.get("finish_reason")
    usage = data.get("usage", {})
    if not content:
        # Cuando V4 se queda sin tokens en el reasoning, content queda vacío.
        print(f"[deepseek] content vacío. finish_reason={finish}, usage={usage}")
        raise ValueError(f"DeepSeek devolvió content vacío (finish_reason={finish}). Sube max_tokens.")

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        print(f"[deepseek] content no es JSON. content[:400]={content[:400]}")
        raise

    # Validación mínima
    for k in ("lectura", "mensaje_corto", "alineacion"):
        if k not in parsed:
            raise ValueError(f"DeepSeek devolvió JSON sin campo '{k}'")
    if parsed["alineacion"] not in ("alineado", "vientos_cruzados", "neutro"):
        parsed["alineacion"] = "neutro"

    return parsed


# ---- Handler ----
def handler(event, context):
    # Preflight CORS
    method = (event.get("requestContext", {}).get("http", {}).get("method")
              or event.get("httpMethod") or "POST").upper()
    if method == "OPTIONS":
        return {"statusCode": 204, "headers": CORS_HEADERS, "body": ""}

    if method != "POST":
        return _err(405, "method_not_allowed", "Solo POST")

    # Body
    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64
        body = base64.b64decode(body).decode("utf-8")
    try:
        state = json.loads(body) if isinstance(body, str) else body
    except Exception as e:
        return _err(400, "bad_json", f"Body no es JSON válido: {e}")

    # Validación mínima del state
    required = ["registro", "candidato", "arquetipo_dominante"]
    missing = [k for k in required if not state.get(k)]
    if missing:
        return _err(400, "missing_fields", f"Faltan campos: {missing}")

    # Cache check
    key = _cache_key(state)
    cached = _cache_get(key)
    if cached:
        cached["cache_hit"] = True
        _emit_event(state, cached.get("alineacion"))
        return _ok(cached)

    # DeepSeek call
    try:
        parsed = _call_deepseek(state)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        print(f"[deepseek] HTTPError {e.code}: {body}")
        return _err(502, "deepseek_http_error", f"DeepSeek devolvió {e.code}")
    except Exception as e:
        print(f"[deepseek] FAIL: {type(e).__name__}: {e}")
        return _err(500, "deepseek_failed", str(e))

    out = {
        **parsed,
        "modelo": DEEPSEEK_MODEL,
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "cache_hit": False,
    }
    _cache_put(key, out)
    _emit_event(state, out.get("alineacion"))
    return _ok(out)


def _ok(payload):
    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps(payload, ensure_ascii=False),
    }


def _err(code, kind, msg):
    return {
        "statusCode": code,
        "headers": CORS_HEADERS,
        "body": json.dumps({"error": kind, "message": msg}, ensure_ascii=False),
    }


# ---- CLI test ----
if __name__ == "__main__":
    import sys
    sample = {
        "registro": "popular",
        "candidato": {"id": "ic", "nombre": "Iván Cepeda", "partido": "Pacto Histórico"},
        "candidato_origen": "declarado",
        "demografia": {"edad": "36-50", "identidad": "barrio"},
        "prio": ["salud", "costo_vida"],
        "arquetipo_dominante": {"id": "castigo", "nombre": "Castigo a la restauración y demanda de alternancia", "pct": 42},
        "arquetipo_secundario": {"id": "pertenencia", "nombre": "Pertenencia comunitaria y autonomía territorial", "pct": 24},
        "arq_score": {"proteccion": 2, "estabilidad": 4, "supervivencia": 2, "castigo": 14, "pertenencia": 8},
    }
    event = {"httpMethod": "POST", "body": json.dumps(sample)}
    result = handler(event, None)
    print(json.dumps(json.loads(result["body"]), indent=2, ensure_ascii=False))
    sys.exit(0 if result["statusCode"] == 200 else 1)
