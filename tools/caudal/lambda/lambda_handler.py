#!/usr/bin/env python3
"""
Caudal · Lambda `caudal-analiza` (módulo de Cauce · inteligencia legislativa).

Envuelve el motor de consulta (caudal_core) sobre el dataset del bucket privado
`caudal-legislativo` y le añade una capa de síntesis por LLM. Patrón calcado de
`test-presidencial-explica`: handler + LLM por HTTP + cache S3 hash24 + CORS.

Acciones (POST JSON):
  {"action":"tema","query":"feminicidio","lectura":true}
      → resumen de supervivencia del tema (embudo, línea de intentos, autores)
        + `lectura`: síntesis LLM opcional (cacheada), tuteo neutro.
  {"action":"proyecto","id":4177}
      → ficha del proyecto + punteros de gaceta (para la fase DeepSeek de texto).
  {"action":"buscar","query":"agua","limit":25,"anio_min":2010}
      → lista cruda de coincidencias del índice.
  {"action":"medios","query":"reforma pensional","dias":30}
      → pilar Medios: titulares de prensa nacional y regional vía Google News RSS
        (gratis, sin key). Sin `query` → landing con el pulso político nacional.

MODELO POR PASO (el switch a Claude es cambiar env vars, sin tocar código):
  CAUDAL_SINTESIS_PROVIDER  deepseek | anthropic     (default deepseek)
  CAUDAL_SINTESIS_MODEL     deepseek-v4-flash | claude-sonnet-5 | …
Secretos:
  DEEPSEEK_API_KEY   (mismo secreto que las otras Lambdas)
  ANTHROPIC_API_KEY  (solo si el paso usa provider=anthropic)
  SERPER_API_KEY     (rastreo de medios · https://serper.dev, resultados Google)
Bucket:
  CAUDAL_BUCKET      default 'caudal-legislativo'
"""
import json
import os
import hashlib
import urllib.request
import urllib.error
from collections import Counter

import boto3
import caudal_core

BUCKET = os.environ.get('CAUDAL_BUCKET', 'caudal-legislativo')
PROMPT_VERSION = 'v6'            # bumpear para invalidar cache de síntesis
CACHE_PREFIX = 'analisis-cache/'
HTTP_TIMEOUT = 55

_s3 = boto3.client('s3')

# --- modelo por paso (override por env var → switch sin código) -------------
STEP_MODELS = {
    'sintesis': {
        'provider': os.environ.get('CAUDAL_SINTESIS_PROVIDER', 'deepseek'),
        'model': os.environ.get('CAUDAL_SINTESIS_MODEL', 'deepseek-v4-flash'),
    },
    # la extracción de texto de gaceta (fase 3) usará este paso
    'extraccion': {
        'provider': os.environ.get('CAUDAL_EXTRACCION_PROVIDER', 'deepseek'),
        'model': os.environ.get('CAUDAL_EXTRACCION_MODEL', 'deepseek-v4-flash'),
    },
    # rastreo de medios: interpreta titulares → controversia/impopularidad
    'contexto': {
        'provider': os.environ.get('CAUDAL_CONTEXTO_PROVIDER', 'deepseek'),
        'model': os.environ.get('CAUDAL_CONTEXTO_MODEL', 'deepseek-v4-flash'),
    },
}

# --- carga de datos (cache por contenedor warm) -----------------------------
_CAUDAL = None
_FULL = None


def _get_json(key):
    obj = _s3.get_object(Bucket=BUCKET, Key=key)
    return json.loads(obj['Body'].read())


def _get_jsonl(key, tb):
    """Devuelve {"tb:id": registro} — pdly y pal comparten espacio de ids."""
    obj = _s3.get_object(Bucket=BUCKET, Key=key)
    out = {}
    for line in obj['Body'].read().decode('utf-8').splitlines():
        if line.strip():
            r = json.loads(line)
            out[f"{tb}:{r['id']}"] = r
    return out


def _caudal():
    """Motor con índice + roster autor→partido (lazy, cache warm)."""
    global _CAUDAL
    if _CAUDAL is None:
        indice = _get_json('metadata/indice.json')['proyectos']
        try:
            ap = _get_json('metadata/autor-partido.json')['autor_partido']
        except Exception:
            ap = {}
        _CAUDAL = caudal_core.Caudal(indice=indice, autor_partido=ap)
    return _CAUDAL


def _full():
    """Registros completos por 'tb:id' (lazy — solo cuando se pide un proyecto)."""
    global _FULL
    if _FULL is None:
        _FULL = _get_jsonl('metadata/proyectos.jsonl', 'pdly')
        _FULL.update(_get_jsonl('metadata/actos-legis.jsonl', 'pal'))
    return _FULL


_BLOQUEO = None


def _bloqueo():
    """Índice de bloqueo (órdenes del día por comisión). Cache warm."""
    global _BLOQUEO
    if _BLOQUEO is None:
        try:
            _BLOQUEO = _get_json('metadata/bloqueo.json')
        except Exception:
            _BLOQUEO = {'sistema': {}, 'por_proyecto': {}}
    return _BLOQUEO


def _num_token(num):
    """'397/2024' | '022/91' → '397/24' (llave del índice de bloqueo)."""
    import re as _re
    m = _re.search(r'(\d{1,4})\s*/\s*(?:20)?(\d{2})', num or '')
    return f'{int(m.group(1))}/{m.group(2)}' if m else None


_VOTAC = None


def _votaciones():
    """Capa de outcome (Congreso Visible): debates/aplazamientos/votos. Cache warm."""
    global _VOTAC
    if _VOTAC is None:
        try:
            _VOTAC = _get_json('metadata/votaciones.json')
        except Exception:
            _VOTAC = {'por_proyecto': {}}
    return _VOTAC


_VOTAC_NOM = None


def _votaciones_nominal():
    """Voto NOMINAL de la plenaria de Cámara (por proyecto: tally + por bancada
    + lista nominal). Distinto de _votaciones() (tally de Congreso Visible).
    Cache warm."""
    global _VOTAC_NOM
    if _VOTAC_NOM is None:
        try:
            _VOTAC_NOM = _get_json('metadata/votaciones-camara-nominal.json')
        except Exception:
            _VOTAC_NOM = {'por_proyecto': {}}
    return _VOTAC_NOM


_VOTAC_CONG = None
_VOTAC_CONG_IDX = None


def _congresistas():
    """Récord de voto POR CONGRESISTA (keyed por roster_key). Cache warm."""
    global _VOTAC_CONG, _VOTAC_CONG_IDX
    if _VOTAC_CONG is None:
        try:
            _VOTAC_CONG = _get_json('metadata/votaciones-camara-congresista.json')
        except Exception:
            _VOTAC_CONG = {'por_congresista': {}}
        # índice token → keys (para resolver un nombre tecleado/clickeado)
        _VOTAC_CONG_IDX = {}
        for k in _VOTAC_CONG.get('por_congresista', {}):
            for t in k.split():
                _VOTAC_CONG_IDX.setdefault(t, set()).add(k)
    return _VOTAC_CONG


def _canon_tokens(s):
    import re as _re, unicodedata as _u
    s = _u.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper()
    return frozenset(t for t in _re.split(r'[^A-Z0-9]+', s) if len(t) > 1)


def _resolver_congresista(q):
    """Devuelve (key exacto|None, [candidatos]) resolviendo q por subconjunto de tokens."""
    pc = _congresistas().get('por_congresista', {})
    if q in pc:
        return q, []
    atoks = _canon_tokens(q)
    if not atoks:
        return None, []
    cand = None
    for t in atoks:
        s = _VOTAC_CONG_IDX.get(t, set())
        cand = s if cand is None else (cand & s)
        if not cand:
            break
    keys = sorted(cand or [], key=lambda k: -pc[k].get('n_votos', 0))
    if len(keys) == 1:
        return keys[0], []
    return None, keys[:12]


# --- pilar Regulatorio · sanciones de superintendencias ---------------------
_SANC = None
_SANC_STATS = None


def _sanciones_stats():
    """Agregados chicos precalculados para el landing del pilar. Cache warm."""
    global _SANC_STATS
    if _SANC_STATS is None:
        try:
            _SANC_STATS = _get_json('metadata/sanciones-stats.json')
        except Exception:
            _SANC_STATS = {'total': 0, 'por_sector': [], 'por_fuente': [],
                           'por_tipo': [], 'recientes': [], 'monto': {}}
    return _SANC_STATS


def _sanciones():
    """Lista slim de sanciones (lazy — solo cuando se busca). Cache warm."""
    global _SANC
    if _SANC is None:
        try:
            obj = _s3.get_object(Bucket=BUCKET, Key='metadata/sanciones.jsonl')
            _SANC = [json.loads(l) for l in obj['Body'].read().decode('utf-8').splitlines() if l.strip()]
        except Exception:
            _SANC = []
    return _SANC


# --- LLM (ruteo por paso) ---------------------------------------------------
def _hash24(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()[:24]


def _cache_get(key):
    try:
        return _get_json(CACHE_PREFIX + key + '.json')
    except _s3.exceptions.NoSuchKey:
        return None
    except Exception:
        return None


def _cache_put(key, data):
    try:
        _s3.put_object(Bucket=BUCKET, Key=CACHE_PREFIX + key + '.json',
                       Body=json.dumps(data, ensure_ascii=False).encode('utf-8'),
                       ContentType='application/json')
    except Exception:
        pass


def _call_deepseek(model, system, user, max_tokens):
    body = json.dumps({
        'model': model,
        'messages': [{'role': 'system', 'content': system},
                     {'role': 'user', 'content': user}],
        'temperature': 0.4, 'max_tokens': max_tokens,
        'response_format': {'type': 'json_object'},
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://api.deepseek.com/chat/completions', data=body,
        headers={'Content-Type': 'application/json',
                 'Authorization': 'Bearer ' + os.environ['DEEPSEEK_API_KEY']})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
        d = json.loads(r.read())
    return d['choices'][0]['message']['content']


def _call_anthropic(model, system, user, max_tokens):
    # switch de calidad para la síntesis (Sonnet 5 / Opus 4.8). Sin thinking
    # config: Sonnet 5 corre adaptive por defecto al omitirlo.
    body = json.dumps({
        'model': model, 'max_tokens': max_tokens, 'system': system,
        'messages': [{'role': 'user', 'content': user}],
    }).encode('utf-8')
    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages', data=body,
        headers={'Content-Type': 'application/json',
                 'x-api-key': os.environ['ANTHROPIC_API_KEY'],
                 'anthropic-version': '2023-06-01'})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
        d = json.loads(r.read())
    return ''.join(b.get('text', '') for b in d.get('content', []) if b.get('type') == 'text')


def _call_llm(step, system, user, max_tokens=1200):
    cfg = STEP_MODELS[step]
    if cfg['provider'] == 'anthropic':
        return _call_anthropic(cfg['model'], system, user, max_tokens)
    return _call_deepseek(cfg['model'], system, user, max_tokens)


# --- síntesis de tema (lectura interpretativa del resumen) ------------------
SINT_SYSTEM = (
    "Eres analista legislativo de Cauce. Escribes en español, tuteo neutro de "
    "Bogotá (sin voseo, sin regionalismos). Analizas trámite legislativo del "
    "Congreso de Colombia. REGLA DURA: solo usas los datos del resumen que se "
    "te entrega; NO inventas cifras, nombres ni hechos que no estén ahí. Si un "
    "dato no está, no lo menciones. Devuelves SIEMPRE un JSON válido con las "
    "claves: titular, hallazgo, por_que_caen, quien_propone, veredicto."
)


def _sintesis_tema(resumen):
    key = _hash24(PROMPT_VERSION + '|tema|' + resumen['query'] + '|' +
                  str(resumen['n_intentos']) + '|' + str(resumen['n_leyes']) +
                  '|' + str(resumen.get('n_vitrina', 0)))
    cached = _cache_get(key)
    if cached:
        return cached
    intentos_txt = '\n'.join(
        f"- [{it['anio']}] {it['resultado_txt']} · {it.get('empuje_txt','')}: {it['titulo'][:85]}"
        for it in resumen['intentos'][:20])
    autores_txt = ', '.join(f"{a} ({n})" for a, n in resumen['top_autores'][:6])
    bancadas_txt = ', '.join(f"{p} ({n} proyectos)" for p, n in resumen.get('bancadas', [])[:6]) or 'sin dato'
    cob = resumen.get('cobertura_partido', {})
    emp = resumen.get('empuje', {})
    user = (
        f"Tema consultado: «{resumen['query']}»\n"
        f"Intentos totales: {resumen['n_intentos']} · convertidos en ley: "
        f"{resumen['n_leyes']} ({resumen['pct_exito']}%) · caídos: "
        f"{resumen['n_caidos']} (de esos, {resumen['n_muerte_por_tiempo']} "
        f"murieron por vencimiento de términos, Art. 190 Ley 5ª).\n"
        f"Periodo: {resumen.get('periodo')}\n"
        f"Embudo del trámite: {json.dumps(resumen['embudo'], ensure_ascii=False)}\n"
        f"LECTURA DE INTENCIÓN (metadata): {resumen.get('n_vitrina',0)} intentos "
        f"({resumen.get('pct_vitrina',0)}%) son de VITRINA (re-radicados sin superar "
        f"el 1er debate — se radican para figurar, no para empujar). "
        f"{resumen.get('n_honores',0)} son de honores/conmemoración. "
        f"Desglose de empuje: {json.dumps(emp, ensure_ascii=False)}.\n"
        f"Quiénes más lo intentan: {autores_txt}\n"
        f"Bancadas que lo impulsan (por partido de los autores, "
        f"cobertura {cob.get('con')}/{cob.get('con',0)+cob.get('sin',0)} intentos): {bancadas_txt}\n"
        f"Línea de intentos:\n{intentos_txt}\n\n"
        "Escribe el análisis en JSON. `titular`: una frase potente y precisa. "
        "`hallazgo`: 2-3 frases con el patrón central; si hay proporción alta de "
        "vitrina o de honores, dilo sin rodeos (distingue quién de verdad empujó el "
        "tema de quién solo lo radicó para figurar). `por_que_caen`: la causa "
        "de muerte dominante (si mueren por tiempo, dilo claro: se hunden en el "
        "orden del día, no por votación). `quien_propone`: usa las BANCADAS para "
        "decir qué partidos empujan el tema (¿transversal o de un solo bloque?); "
        "si la cobertura de partido es parcial, acláralo. `veredicto`: cierre de "
        "1-2 frases.")
    try:
        # max_tokens alto: DeepSeek V4 gasta tokens en reasoning y con presupuesto
        # bajo deja content vacío (finish_reason=length) — gotcha documentado.
        raw = _call_llm('sintesis', SINT_SYSTEM, user, max_tokens=6000)
        raw = raw.strip()
        if raw.startswith('```'):                    # por si envuelve en fences
            raw = raw.split('```')[1].lstrip('json').strip()
        data = json.loads(raw)
    except Exception as e:
        data = {'titular': '', 'hallazgo': '', 'por_que_caen': '',
                'quien_propone': '', 'veredicto': '', 'error': str(e)[:200]}
    data['_model'] = STEP_MODELS['sintesis']['model']
    if 'error' not in data:          # no cachear fallos
        _cache_put(key, data)
    return data


# --- Radar del cliente · lectura interpretada (SKU A · Vista Cliente) --------
CLIENTE_SYSTEM = (
    "Eres analista de asuntos públicos de Cauce. Escribes en español, tuteo "
    "neutro de Bogotá (sin voseo, sin regionalismos). Te doy el RADAR de un "
    "cliente de un sector: las señales del Estado (proyectos de ley y sanciones) "
    "que tocan su sector, ya filtradas y con su estado real y nivel de prioridad. "
    "Tu trabajo: decir qué DE VERDAD mueve su aguja y qué hacer — precisión sobre "
    "volumen. REGLA DURA: usa SOLO las señales que te doy; NO inventes proyectos, "
    "cifras, entidades ni nombres. Si algo no está, no lo menciones. Devuelves "
    "SIEMPRE un JSON válido con: titular (una frase potente y precisa), "
    "lo_que_importa (2-3 frases: las 2-3 señales que priorizarías y por qué mueven "
    "la aguja de este sector), acciones (lista de 2-4 acciones concretas), "
    "riesgo_oportunidad (1-2 frases sobre el riesgo o la oportunidad dominante).")


def _lectura_cliente(s, senales, kpis):
    key = _hash24(PROMPT_VERSION + '|cliente|' + s['k'] + '|' + str(kpis['n_radar'])
                  + '|' + str(kpis['alto']) + '|' + str(kpis['en_tramite']))
    cached = _cache_get('cliente-' + key)
    if cached:
        return cached
    lines = []
    for x in senales[:14]:
        if x['tipo'] == 'congreso':
            lines.append(f"- [LEGISLATIVO · prioridad {x['nivel']}] ({x['anio']}, "
                         f"{x.get('resultado_txt', x.get('resultado'))}) {x['titulo'][:95]}")
        else:
            lines.append(f"- [REGULATORIO · prioridad {x['nivel']}] {x.get('fecha', '')} "
                         f"{x.get('fuente', '')}: {x.get('sancionado', '')} — {x.get('motivo', '')[:75]}")
    user = (f"Cliente: sector {s['nombre']} (sus proyectos suelen ir a la Comisión "
            f"{s['comision']}).\n"
            f"Radar: {kpis['n_radar']} señales priorizadas · {kpis['alto']} de alta "
            f"prioridad · {kpis['en_tramite']} proyectos EN TRÁMITE (ventana de "
            f"incidencia abierta), de {kpis['n_proyectos_sector']} proyectos que han "
            f"tocado el sector en 36 años"
            + (f" · {kpis['n_sanciones_sector']} sanciones del sector"
               if kpis.get('n_sanciones_sector') else '') + ".\n\n"
            f"SEÑALES DEL RADAR:\n" + '\n'.join(lines) + "\n\nEscribe el análisis en JSON.")
    try:
        raw = _call_llm('sintesis', CLIENTE_SYSTEM, user, max_tokens=6000).strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1].lstrip('json').strip()
        data = json.loads(raw)
    except Exception as e:
        data = {'titular': '', 'lo_que_importa': '', 'acciones': [],
                'riesgo_oportunidad': '', 'error': str(e)[:200]}
    data['_model'] = STEP_MODELS['sintesis']['model']
    if 'error' not in data:
        _cache_put('cliente-' + key, data)
    return data


# --- fase 3 · extracción del texto de una gaceta ----------------------------
GACETA_SYSTEM = (
    "Eres analista legislativo de Cauce. Te doy el TEXTO de una Gaceta del "
    "Congreso de Colombia (un boletín que puede traer varios documentos). "
    "Enfócate SOLO en el documento del proyecto indicado en el contexto. "
    "REGLA DURA: extrae únicamente lo que está en el texto; NO inventes nombres, "
    "fechas ni argumentos. Si algo no aparece, ponlo en null o lista vacía. "
    "Devuelves SIEMPRE un JSON válido con estas claves: tipo_documento (p.ej. "
    "'ponencia', 'acta de comisión', 'acta de plenaria'), "
    "ponentes (lista de nombres que firman), sentido (uno de: 'favorable', "
    "'archivo', 'mixto', 'desconocido' — ¿recomienda dar debate o archivar?), "
    "sentido_detalle (frase que lo justifica), argumentos (lista de 3-6 bullets "
    "con los argumentos centrales), en_contra (texto si hay ponencia de archivo "
    "u oposición explícita, si no null). SI EL DOCUMENTO ES UN ACTA de sesión, "
    "agrega además: aplazamiento (objeto {hubo: true/false, propuesto_por: nombre "
    "de quien propuso aplazar o null, detalle: frase}), y votacion (objeto "
    "{hubo: true/false, motivo: qué se votó, favor: nº, contra: nº, abstencion: "
    "nº, nominal: lista de {nombre, voto} SOLO si el acta trae el listado nominal "
    "de cada congresista, si no lista vacía}). Si no es acta o no hay votación/"
    "aplazamiento, esos objetos van con hubo:false."
)


def _ventana(texto, contexto, size=60000):
    """Actas de plenaria largas: el roll-call nominal vive DESPUÉS del preámbulo
    (asistencia/quórum), lejos de los primeros 60k. En vez de cortar por el
    inicio, centra la ventana en la votación relevante — ancla en las palabras
    distintivas del contexto y, si no, en la primera 'votación nominal'."""
    if len(texto) <= size:
        return texto
    low = texto.lower()
    anchor = -1
    # ancla SOLO en palabras distintivas (≥7 chars) — NO en números sueltos: un
    # número del contexto (nº de proyecto) aparece en cualquier parte del acta y
    # manda la ventana a un lugar sin votación.
    for tok in re.findall(r'[a-záéíóúñ]{8,}', (contexto or '').lower())[:8]:
        if tok in ('proyecto', 'senado', 'camara', 'plenaria', 'congreso', 'republica'):
            continue                     # palabras ubicuas en toda acta → no anclan
        p = low.find(tok)
        if p > size // 2:                # solo salta si el ancla está lejos del inicio
            anchor = p
            break
    if anchor < 0:
        for kw in ('votación nominal', 'votacion nominal', 'por el sí', 'por el si'):
            p = low.find(kw)
            if p >= 0:
                anchor = p
                break
    if anchor < 0:
        return texto[:size]
    start = max(0, anchor - 2500)        # un poco de contexto antes del voto
    return texto[start:start + size]


def _extraer_gaceta(key, contexto):
    """Lee gacetas-texto/{key}.txt de S3 y saca la estructura vía LLM (cache)."""
    try:
        obj = _s3.get_object(Bucket=BUCKET, Key=f'gacetas-texto/{key}.txt')
        texto = obj['Body'].read().decode('utf-8', errors='replace')
    except Exception as e:
        return {'error': f'no hay texto de la gaceta {key} en S3: {str(e)[:120]}'}
    ck = _hash24(PROMPT_VERSION + '|gaceta|' + key + '|' + (contexto or ''))
    cached = _cache_get('gaceta-' + ck)
    if cached:
        return cached
    # el texto puede ser largo; recorta a ~60k chars (≈ una gaceta grande)
    user = (f"Contexto (proyecto de interés): {contexto or 'el proyecto principal del documento'}\n\n"
            f"TEXTO DE LA GACETA {key}:\n{_ventana(texto, contexto)}")
    try:
        raw = _call_llm('extraccion', GACETA_SYSTEM, user, max_tokens=6000).strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1].lstrip('json').strip()
        data = json.loads(raw)
    except Exception as e:
        return {'error': f'extracción falló: {str(e)[:160]}'}
    data['_model'] = STEP_MODELS['extraccion']['model']
    data['gaceta'] = key
    _cache_put('gaceta-' + ck, data)
    return data


# --- rastreo de medios (Serper/Google → controversia/impopularidad) ---------
import re

_TITULO_PREF = re.compile(
    r'^\s*por\s+(?:medio\s+de\s+|el\s+medio\s+de\s+)?(?:la|el|los|las)?\s*cual(?:es)?\s+se\s+',
    re.I)


def _query_medios(titulo, autor, anio, numero):
    """Arma una query de prensa desde la ficha (limpia el formulismo legal)."""
    t = _TITULO_PREF.sub('', titulo or '').strip()
    t = re.sub(r'\s+', ' ', t)[:90]
    partes = ['proyecto de ley', t]
    if numero:
        partes.append(str(numero))
    if anio:
        partes.append(str(anio))
    if autor:
        partes.append(autor.split()[0] if ' ' in autor else autor)
    partes.append('Colombia')
    return ' '.join(p for p in partes if p)


def _serper(q, num=10):
    key = os.environ.get('SERPER_API_KEY')
    if not key:
        raise RuntimeError('SERPER_API_KEY no configurada')
    body = json.dumps({'q': q, 'gl': 'co', 'hl': 'es', 'num': num}).encode('utf-8')
    req = urllib.request.Request('https://google.serper.dev/search', data=body,
                                 headers={'X-API-KEY': key, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read())
    out = []
    for o in d.get('organic', [])[:num]:
        out.append({'titulo': o.get('title', ''), 'url': o.get('link', ''),
                    'fuente': (o.get('link', '').split('/')[2] if '://' in o.get('link', '') else ''),
                    'fecha': o.get('date', ''), 'snippet': o.get('snippet', '')})
    return out


CTX_SYSTEM = (
    "Eres analista legislativo de Cauce. Te doy TITULARES DE PRENSA sobre un "
    "proyecto de ley/acto legislativo del Congreso de Colombia. Tu tarea: decir "
    "si el proyecto tuvo controversia, oposición pública o impopularidad que "
    "ayude a explicar su trámite (muchos se dejan caer por tiempo cuando se "
    "vuelven impopulares o un gremio los frena). Escribes en tuteo neutro de "
    "Bogotá. REGLA DURA: usa SOLO lo que dicen los titulares; si no hay señal "
    "clara, dilo (no inventes controversia). Devuelves SIEMPRE un JSON válido con "
    "las claves: tuvo_controversia ('si'|'no'|'sin_senal'), nivel "
    "('alta'|'media'|'baja'|'sin_senal'), resumen (2-4 frases), quien_se_opuso "
    "(lista de gremios/sectores/actores que aparezcan, o vacía), "
    "murio_por_impopularidad ('probable'|'poco_probable'|'sin_senal'), "
    "veredicto (1-2 frases). NO inventes URLs ni fechas: esas van aparte.")


def _contexto_medios(payload):
    titulo = payload.get('titulo', '')
    q = _query_medios(titulo, payload.get('autor'), payload.get('anio'),
                      payload.get('numero'))
    ck = _hash24(PROMPT_VERSION + '|contexto|' + str(payload.get('id')) + '|' +
                 str(payload.get('tb')) + '|' + titulo[:60])
    cached = _cache_get('contexto-' + ck)
    if cached:
        return cached
    try:
        fuentes = _serper(q)
    except Exception as e:
        return {'error': f'búsqueda no disponible: {str(e)[:140]}', 'query': q}
    if not fuentes:
        return {'query': q, 'tuvo_controversia': 'sin_senal', 'nivel': 'sin_senal',
                'resumen': 'No se encontró cobertura de prensa localizable para este '
                           'proyecto (frecuente en iniciativas anteriores a ~2010).',
                'quien_se_opuso': [], 'murio_por_impopularidad': 'sin_senal',
                'veredicto': '', 'fuentes': []}
    titulares_txt = '\n'.join(
        f"- [{f.get('fecha') or 's/f'}] {f.get('fuente')}: {f.get('titulo')} — {f.get('snippet','')[:160]}"
        for f in fuentes)
    user = (f"Proyecto: «{titulo}»\n"
            f"Resultado del trámite: {payload.get('resultado') or 's/d'}\n\n"
            f"TITULARES ENCONTRADOS:\n{titulares_txt}\n\n"
            "Analiza SOLO con base en estos titulares. Devuelve el JSON pedido.")
    try:
        raw = _call_llm('contexto', CTX_SYSTEM, user, max_tokens=3000).strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1].lstrip('json').strip()
        data = json.loads(raw)
    except Exception as e:
        data = {'tuvo_controversia': 'sin_senal', 'nivel': 'sin_senal', 'resumen': '',
                'quien_se_opuso': [], 'murio_por_impopularidad': 'sin_senal',
                'veredicto': '', 'error': str(e)[:160]}
    data['query'] = q
    data['fuentes'] = fuentes           # URLs/fechas REALES (no del LLM)
    data['_model'] = STEP_MODELS['contexto']['model']
    if 'error' not in data:
        _cache_put('contexto-' + ck, data)
    return data


# --- pilar Medios · prensa nacional y regional (Google News RSS · gratis) ---
# Mismo mecanismo que tools/radar-mujer-medios/collect.py (monitor de medios de
# Radar Mujer/MxD): Google News RSS es gratis, sin API key, y cubre TODO el
# ecosistema de prensa colombiano (nacional + regional) por query temática, sin
# mantener un conector por medio. Aquí se reusa para el pilar Medios de Caudal.
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
import time as _time
from datetime import timezone
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

MEDIOS_UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')

# consultas amplias para el landing (sin tema puntual): pulso político/legislativo
# nacional. Se amplía fácil agregando más queries — cada una ya trae el ecosistema
# completo de medios que cubrió ese ángulo, gratis.
MEDIOS_LANDING_Q = [
    'Congreso de la República Colombia',
    'Gobierno Nacional Colombia',
    'Corte Constitucional Colombia',
    'reforma Colombia',
]

# medios regionales conocidos (forma "compacta": sin tildes/espacios/puntos) —
# match por substring sobre el nombre del medio que trae Google News. Lo que NO
# matchea cae a 'nacional' (la mayoría de la prensa digital colombiana es de
# alcance nacional) — no pretende ser exhaustivo, solo dar un desglose útil.
_MEDIOS_REGIONALES = [
    'elcolombiano', 'elmundo', 'minuto30', 'minuto60', 'vivirenelpoblado',
    'telemedellin', 'teleantioquia', 'elpais', 'qhubo', 'extra',
    'elheraldo', 'elmeridianodecordoba', 'diariolalibertad', 'eluniversal',
    'vanguardia', 'laopinion', 'lapatria', 'cronicadelquindio', 'elquindiano',
    'elnuevodia', 'diariodelhuila', 'llano7dias', 'elpilon',
    'hoydiariodelmagdalena', 'diariodelnorte', 'proclamadelcauca', 'latarde',
    'diariodelotun', 'diariodelcauca', 'telecaribe', 'telepacifico', 'citytv',
    'notipacifico', 'primiciadiario', 'hsbnoticias',
]

# plataformas sociales que Google News a veces manda como <source> cuando el
# resultado es un post/caption compartido, no una nota editorial (ej. un post
# de Facebook con texto largo). Se descartan ANTES de agregar — es justo el
# tipo de ruido que Caudal promete filtrar, no sumarlo junto a medios reales.
_MEDIOS_FUENTES_EXCLUIR = {
    'facebookcom', 'facebook', 'twittercom', 'twitter', 'xcom',
    'instagramcom', 'instagram', 'tiktokcom', 'tiktok', 'youtubecom',
    'youtube', 'threadsnet', 'threads', 'linkedincom', 'linkedin',
    'redditcom', 'reddit', 'tme', 'telegram', 'whatsappcom', 'whatsapp',
    'tco',
}

# TLDs comunes a recortar cuando Google News manda el dominio en vez de la
# marca como <source> (ver _medios_group_key). Ordenados de más largo a más
# corto para que '.com.co' se pruebe antes que '.co'.
_DOMAIN_TLDS_SORTED = sorted(
    ('com.co', 'com.mx', 'com.ar', 'com.ve', 'com.pe', 'com.ec', 'com',
     'co', 'net', 'org', 'info', 'tv', 'la', 'news'),
    key=len, reverse=True)

# fuentes institucionales (gobierno, entes de control, academia pública):
# Google News las trae como si fueran prensa independiente, pero un comunicado
# oficial no es "cobertura mediática" — mezclarlo con Infobae/El Tiempo infla
# la sensación de que hay ruido de prensa cuando en realidad es la propia
# entidad hablando de sí misma. Heurística no exhaustiva, mismo criterio que
# _MEDIOS_REGIONALES: palabra-raíz institucional sobre el nombre COMPACTO
# (sin puntos/espacios); el dominio .gov.co/.edu.co se chequea aparte, sobre
# el string crudo, porque _medios_compact() se come los puntos.
_MEDIOS_INSTITUCIONAL_RE = re.compile(
    r'gobernacion|alcaldia|ministerio|universidad|camaradecomercio'
    r'|personeria|contraloria|procuraduria|defensoria|^concejo|^asamblea'
    r'|^sena$|^dian$|presidenciadelarepublica|^super(intendencia|salud'
    r'|financiera|sociedades|transporte|servicios)|policianacional'
    r'|ejercitonacional|unidadnacional|agencianacional|registraduria')


def _medios_es_institucional(medio):
    if not medio:
        return False
    low = _medios_strip_accents(medio.lower())
    if low.endswith('.gov.co') or low.endswith('.edu.co'):
        return True
    return bool(_MEDIOS_INSTITUCIONAL_RE.search(_medios_compact(medio)))


def _medios_strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def _medios_norm(s):
    return re.sub(r'\s+', ' ', _medios_strip_accents((s or '').lower())).strip()


def _medios_compact(s):
    return re.sub(r'[^a-z0-9]', '', _medios_strip_accents((s or '').lower()))


def _medios_es_fuente_social(medio):
    return _medios_compact(medio) in _MEDIOS_FUENTES_EXCLUIR


def _medios_looks_domain(medio):
    return bool(medio) and '.' in medio and ' ' not in medio


def _medios_domain_slug(medio):
    """'elpais.com.co' -> 'elpais'; 'ElUniversal.com.co' -> 'eluniversal'."""
    s = medio.lower()
    s = re.sub(r'^https?://', '', s)
    s = re.sub(r'^www\.', '', s)
    for tld in _DOMAIN_TLDS_SORTED:
        suf = '.' + tld
        if s.endswith(suf):
            return s[:-len(suf)]
    return s


def _medios_group_key(medio):
    """Llave de agrupación agnóstica de la FORMA en que llega el medio: Google
    News manda a veces el dominio ('elpais.com.co') y a veces la marca ('El
    País') como <source> para el MISMO periódico — sin esto, 'por_medio' infla
    el conteo de medios distintos con el mismo medio contado dos veces."""
    base = _medios_domain_slug(medio) if _medios_looks_domain(medio) else medio
    return _medios_compact(base)


def _medios_alcance(medio):
    c = _medios_compact(medio)
    return 'regional' if any(t in c for t in _MEDIOS_REGIONALES) else 'nacional'


_GN_SUFFIX_RE = re.compile(r'\s+-\s+([^-]+)$')


def _medios_split_title(title, source):
    """Título de Google News = 'Titular real - Nombre del Medio'."""
    if source:
        m = _GN_SUFFIX_RE.search(title)
        if m and _medios_norm(m.group(1)) == _medios_norm(source):
            return title[:m.start()].strip(), source
        return title, source
    m = _GN_SUFFIX_RE.search(title)
    if m:
        return title[:m.start()].strip(), m.group(1).strip()
    return title, None


def _medios_parse_date(raw):
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw.strip())
    except Exception:
        return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _medios_gn_url(q, dias):
    # `gl=CO` solo SESGA el resultado a Colombia, no lo restringe — términos
    # genéricos (p.ej. "sistema financiero", "salario minimo") matchean prensa
    # de cualquier país hispanohablante. Forzar "Colombia" en la query (si el
    # término no la trae ya) lo vuelve un AND real, sin tocar búsquedas ya
    # específicas ("seguridad Catatumbo", "reforma pensional Colombia"...).
    if 'colombia' not in q.lower():
        q = f'{q} Colombia'
    qq = f'{q} when:{dias}d' if dias else q
    qs = urllib.parse.urlencode({'q': qq, 'hl': 'es-419', 'gl': 'CO', 'ceid': 'CO:es'})
    return f'https://news.google.com/rss/search?{qs}'


def _medios_fetch_xml(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': MEDIOS_UA,
        'Accept': 'application/rss+xml, application/xml;q=0.9, */*;q=0.8',
        'Accept-Language': 'es-CO,es;q=0.9'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()


def _medios_parse_feed(xml_bytes):
    root = ET.fromstring(xml_bytes)
    ch = root.find('channel')
    items = ch.findall('item') if ch is not None else root.findall('.//item')
    out = []
    for it in items:
        link = (it.findtext('link') or '').strip()
        if not link:
            continue
        src_el = it.find('source')
        source = src_el.text.strip() if src_el is not None and src_el.text else None
        out.append({'link': link, 'title': (it.findtext('title') or '').strip(),
                    'fecha_pub': _medios_parse_date(it.findtext('pubDate')), 'source': source})
    return out


def _medios_query_events(query, dias):
    try:
        items = _medios_parse_feed(_medios_fetch_xml(_medios_gn_url(query, dias)))
    except Exception as e:
        print(f'[medios] FAIL "{query}": {type(e).__name__}: {e}')
        return []
    events = []
    for it in items:
        titulo, medio = _medios_split_title(it['title'], it['source'])
        if not medio or _medios_es_fuente_social(medio) or _medios_es_institucional(medio):
            continue
        events.append({'medio': medio, 'alcance': _medios_alcance(medio), 'titulo': titulo,
                       'url': it['link'], 'fecha': (it['fecha_pub'] or '')[:10],
                       '_fp': it['fecha_pub'] or ''})
    return events


def _medios_aggregate(events, cap):
    # dedup por (titulo normalizado, LLAVE de medio) — no por el string crudo
    # del medio, que puede venir en dos formas distintas para el mismo outlet.
    seen, dedup = set(), []
    for e in events:
        e['_gk'] = _medios_group_key(e['medio'])
        k = (_medios_norm(e['titulo']), e['_gk'])
        if k in seen:
            continue
        seen.add(k)
        dedup.append(e)
    dedup.sort(key=lambda e: e['_fp'], reverse=True)

    # nombre canónico por grupo: preferir la forma que NO parece dominio (la
    # marca real, 'El País') sobre 'elpais.com.co'; si todas las variantes del
    # grupo parecen dominio, usar la más frecuente tal cual.
    variantes = {}
    for e in dedup:
        variantes.setdefault(e['_gk'], Counter())[e['medio']] += 1
    canon = {}
    for gk, vc in variantes.items():
        marca = {m: n for m, n in vc.items() if not _medios_looks_domain(m)}
        pool = marca or vc
        canon[gk] = max(pool.items(), key=lambda kv: kv[1])[0]
    for e in dedup:
        e['medio'] = canon[e['_gk']]

    por_medio = Counter(e['medio'] for e in dedup)
    por_alcance = Counter(e['alcance'] for e in dedup)
    return {
        'n': len(dedup), 'n_medios': len(por_medio),
        'por_medio': [{'medio': m, 'n': n} for m, n in por_medio.most_common(20)],
        'por_alcance': [{'alcance': a, 'n': n} for a, n in por_alcance.most_common()],
        'resultados': [{k: v for k, v in e.items() if k not in ('_fp', '_gk')} for e in dedup[:cap]],
    }


def _medios_cache_bucket(hours=3):
    return int(_time.time() // (hours * 3600))


def _medios_landing():
    ck = f'medios-landing-{_medios_cache_bucket()}'
    cached = _cache_get(ck)
    if cached:
        return cached
    events = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for fut in as_completed([pool.submit(_medios_query_events, q, 3) for q in MEDIOS_LANDING_Q]):
            events.extend(fut.result())
    out = dict(_medios_aggregate(events, cap=24), mode='landing')
    _cache_put(ck, out)
    return out


def _medios_buscar(query, dias):
    dias = dias or 30
    ck = f'medios-q-{_hash24(_medios_norm(query))}-{dias}-{_medios_cache_bucket()}'
    cached = _cache_get(ck)
    if cached:
        return cached
    out = dict(_medios_aggregate(_medios_query_events(query, dias), cap=60),
               mode='search', query=query, dias=dias)
    _cache_put(ck, out)
    return out


def _medios_para_sector(temas, dias=14, cap=6):
    """Pulso de prensa para el Radar del cliente (Vista Cliente · SKU A): una
    query de Google News por cada tema del sector, en paralelo, con el mismo
    filtro de ruido y dedup del pilar Medios. Cache de 3h por combinación de
    temas (mismo criterio que _medios_landing/_medios_buscar)."""
    if not temas:
        return {'n': 0, 'resultados': []}
    ck = f'medios-sector-{_hash24("|".join(sorted(temas)))}-{dias}-{_medios_cache_bucket()}'
    cached = _cache_get(ck)
    if cached:
        return cached
    events = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for fut in as_completed([pool.submit(_medios_query_events, t, dias) for t in temas]):
            events.extend(fut.result())
    out = _medios_aggregate(events, cap=cap)
    _cache_put(ck, out)
    return out


# --- handler ----------------------------------------------------------------
CORS = {'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Content-Type': 'application/json'}


def _resp(code, payload):
    return {'statusCode': code, 'headers': CORS,
            'body': json.dumps(payload, ensure_ascii=False)}


def handler(event, context):
    if (event.get('requestContext', {}).get('http', {}).get('method')
            or event.get('httpMethod')) == 'OPTIONS':
        return {'statusCode': 204, 'headers': CORS, 'body': ''}
    try:
        body = json.loads(event.get('body') or '{}')
    except Exception:
        return _resp(400, {'error': 'body no es JSON'})

    action = body.get('action', 'tema')
    caudal = _caudal()

    if action == 'buscar':
        q = body.get('query', '')
        hits = caudal.buscar(q, anio_min=body.get('anio_min'),
                             anio_max=body.get('anio_max'),
                             comision=body.get('comision'),
                             resultado=body.get('resultado'),
                             tipologia=body.get('tipologia'),
                             empuje=body.get('empuje'),
                             limit=body.get('limit', 50))
        return _resp(200, {'query': q, 'n': len(hits), 'resultados': hits})

    if action == 'stats':          # agregados globales precalculados (para gráficas)
        try:
            return _resp(200, _get_json('metadata/stats.json'))
        except Exception as e:
            return _resp(500, {'error': f'no se pudo leer stats: {str(e)[:120]}'})

    if action == 'bloqueo':        # sistema de bloqueo (posición, hazard, comisiones)
        return _resp(200, _bloqueo().get('sistema', {}))

    if action == 'proyecto':
        pid = body.get('id')
        caudal._full = _full()          # inyecta registros completos (keyed tb:id)
        ficha = caudal.proyecto(pid, body.get('tb', 'pdly'))
        if not ficha:
            return _resp(404, {'error': f'proyecto {pid} no encontrado'})
        # bloqueo por número Cámara (órdenes del día de comisión)
        tok_c = _num_token(ficha.get('numero_camara'))
        if tok_c:
            bl = _bloqueo().get('por_proyecto', {}).get(tok_c)
            if bl:
                ficha['bloqueo'] = bl
        # outcome (Congreso Visible): match por número Senado o Cámara
        vp = _votaciones().get('por_proyecto', {})
        for tk in (_num_token(ficha.get('numero_senado')), tok_c):
            if tk and tk in vp:
                ficha['votaciones'] = vp[tk]
                break
        # voto NOMINAL de plenaria Cámara (aditivo): match por número Cámara
        if tok_c:
            vn = _votaciones_nominal().get('por_proyecto', {}).get(tok_c)
            if vn:
                ficha['voto_nominal'] = vn
        return _resp(200, ficha)

    if action == 'congresista':
        # récord de voto de una persona. {key} exacto (click-through) o {q}/{nombre}
        # (nombre tecleado o clickeado, resuelto por subconjunto de tokens).
        q = (body.get('key') or body.get('q') or body.get('nombre') or '').strip()
        if not q:
            return _resp(400, {'error': 'falta key/q/nombre del congresista'})
        pc = _congresistas().get('por_congresista', {})
        key, cands = _resolver_congresista(q)
        if key:
            return _resp(200, dict(pc[key], key=key, encontrado=True))
        if cands:   # ambiguo: devolver candidatos para desambiguar
            return _resp(200, {'encontrado': False, 'candidatos': [
                {'key': k, 'nombre': pc[k]['nombre'], 'bancada': pc[k].get('bancada'),
                 'n_votos': pc[k].get('n_votos')} for k in cands]})
        return _resp(404, {'encontrado': False, 'error': f'sin récord de voto para «{q}»'})

    if action == 'gaceta':
        key = body.get('key')          # ej '857-2013'
        if not key:
            return _resp(400, {'error': 'falta key de gaceta (num-año)'})
        return _resp(200, _extraer_gaceta(key, body.get('contexto', '')))

    if action == 'contexto':           # rastreo de medios de un proyecto
        if not body.get('titulo'):
            return _resp(400, {'error': 'falta titulo del proyecto'})
        return _resp(200, _contexto_medios(body))

    if action == 'sanciones':      # pilar Regulatorio · sanciones de superintendencias
        q = (body.get('query') or '').strip().lower()
        sector = body.get('sector') or ''
        if not q and not sector:               # landing: agregados precalculados (rápido)
            return _resp(200, dict(_sanciones_stats(), mode='stats'))
        recs = _sanciones()
        hits = [r for r in recs
                if (not sector or r.get('sector') == sector)
                and (not q or q in r.get('q', ''))]
        secc = Counter(r.get('sector', '') for r in hits)
        fuc = Counter(r.get('fuente_nombre', '') for r in hits)
        montos = [r['monto'] for r in hits if r.get('monto')]
        hits_sorted = sorted(hits, key=lambda r: r.get('fecha', ''), reverse=True)
        out = [{k: v for k, v in r.items() if k != 'q'} for r in hits_sorted[:120]]
        return _resp(200, {
            'mode': 'search', 'query': body.get('query', ''), 'sector': sector,
            'n': len(hits), 'mostrados': len(out),
            'por_sector': [{'sector': s, 'n': n} for s, n in secc.most_common()],
            'por_fuente': [{'fuente': f, 'n': n} for f, n in fuc.most_common()],
            'monto_total_cop': round(sum(montos)) if montos else 0,
            'con_monto': len(montos),
            'resultados': out,
        })

    if action == 'medios':      # pilar Medios · prensa nacional y regional (Google News RSS)
        q = (body.get('query') or '').strip()
        if not q:
            return _resp(200, _medios_landing())
        try:
            dias = int(body.get('dias')) if body.get('dias') else None
        except Exception:
            dias = None
        return _resp(200, _medios_buscar(q, dias))

    if action == 'cliente':        # Vista Cliente · radar SIGA sobre los pilares
        sk = body.get('sector')
        s = caudal_core.sector_cliente(sk)
        sectores = [{'k': x['k'], 'nombre': x['nombre'],
                     'regulatorio': bool(x.get('sector_sanciones'))}
                    for x in caudal_core.SECTORES_CLIENTE]
        if not s:
            return _resp(400, {'error': f'sector desconocido: {sk}', 'sectores': sectores})
        rc = caudal.radar_congreso(sector_key=sk)
        reg, n_sanc = [], 0
        if s.get('sector_sanciones'):
            sanc = [r for r in _sanciones() if r.get('sector') == s['sector_sanciones']]
            n_sanc = len(sanc)
            sanc.sort(key=lambda r: r.get('fecha', ''), reverse=True)
            for r in sanc[:6]:
                yr = (r.get('fecha') or '')[:4]
                reciente = yr.isdigit() and int(yr) >= caudal_core.REF_YEAR - 1
                reg.append({'tipo': 'regulatorio', 'sancionado': r.get('sancionado'),
                            'fuente': r.get('fuente_nombre'), 'tipo_sancion': r.get('tipo'),
                            'motivo': (r.get('motivo') or '')[:170], 'fecha': r.get('fecha'),
                            'monto': r.get('monto'), 'nivel': 'alto' if reciente else 'medio',
                            'accion': ('Sanción reciente en tu sector — revisar exposición y activar '
                                       'cumplimiento') if reciente else
                                      'Antecedente sancionatorio — referencia de riesgo del sector'})
        med, n_med = [], 0
        med_agg = _medios_para_sector(s.get('temas', []))
        n_med = med_agg['n']
        cutoff = _time.strftime('%Y-%m-%d', _time.gmtime(_time.time() - 5 * 86400))
        for r in med_agg['resultados'][:5]:
            reciente = (r.get('fecha') or '') >= cutoff
            med.append({'tipo': 'medios', 'medio': r.get('medio'), 'titulo': r.get('titulo'),
                        'url': r.get('url'), 'fecha': r.get('fecha'), 'alcance': r.get('alcance'),
                        'nivel': 'alto' if reciente else 'medio',
                        'accion': ('Cobertura reciente — revisar si necesita respuesta o vocería'
                                   if reciente else
                                   'Tema en el radar de prensa — monitoreo pasivo')})
        senales = rc['senales'] + reg + med
        kpis = {'n_radar': len(senales),
                'alto': sum(1 for x in senales if x['nivel'] == 'alto'),
                'medio': sum(1 for x in senales if x['nivel'] == 'medio'),
                'bajo': sum(1 for x in senales if x['nivel'] == 'bajo'),
                'en_tramite': sum(1 for x in rc['senales'] if x['resultado'] == 'EN_TRAMITE'),
                'n_proyectos_sector': rc['n_tocados'], 'n_sanciones_sector': n_sanc,
                'n_medios_sector': n_med}
        out = {'cliente': {'sector': sk, 'nombre': s['nombre'], 'comision': s['comision'],
                           'sector_sanciones': s.get('sector_sanciones', ''), 'temas': s.get('temas', [])},
               'congreso': rc['senales'], 'regulatorio': reg, 'medios': med, 'kpis': kpis, 'sectores': sectores}
        if body.get('lectura', False):
            out['lectura'] = _lectura_cliente(s, senales, kpis)
        return _resp(200, out)

    if action == 'tema':
        q = body.get('query', '')
        if not q.strip():
            return _resp(400, {'error': 'falta query'})
        resumen = caudal.resumen_tema(
            q, anio_min=body.get('anio_min'), anio_max=body.get('anio_max'),
            comision=body.get('comision'))
        out = {'query': q, 'resumen': resumen,
               'model_info': {'sintesis': STEP_MODELS['sintesis']}}
        if body.get('lectura', True) and resumen['n_intentos'] > 0:
            out['lectura'] = _sintesis_tema(resumen)
        return _resp(200, out)

    return _resp(400, {'error': f'action desconocida: {action}'})
