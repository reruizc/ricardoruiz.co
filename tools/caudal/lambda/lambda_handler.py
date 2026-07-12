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

import boto3
import caudal_core

BUCKET = os.environ.get('CAUDAL_BUCKET', 'caudal-legislativo')
PROMPT_VERSION = 'v4'            # bumpear para invalidar cache de síntesis
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


# --- fase 3 · extracción del texto de una gaceta ----------------------------
GACETA_SYSTEM = (
    "Eres analista legislativo de Cauce. Te doy el TEXTO de una Gaceta del "
    "Congreso de Colombia (un boletín que puede traer varios documentos). "
    "Enfócate SOLO en el documento del proyecto indicado en el contexto. "
    "REGLA DURA: extrae únicamente lo que está en el texto; NO inventes nombres, "
    "fechas ni argumentos. Si algo no aparece, ponlo en null o lista vacía. "
    "Devuelves SIEMPRE un JSON válido con estas claves: tipo_documento, "
    "ponentes (lista de nombres que firman), sentido (uno de: 'favorable', "
    "'archivo', 'mixto', 'desconocido' — ¿recomienda dar debate o archivar?), "
    "sentido_detalle (frase que lo justifica), argumentos (lista de 3-6 bullets "
    "con los argumentos centrales), en_contra (texto si hay ponencia de archivo "
    "u oposición explícita, si no null)."
)


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
            f"TEXTO DE LA GACETA {key}:\n{texto[:60000]}")
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

    if action == 'proyecto':
        pid = body.get('id')
        caudal._full = _full()          # inyecta registros completos (keyed tb:id)
        ficha = caudal.proyecto(pid, body.get('tb', 'pdly'))
        if not ficha:
            return _resp(404, {'error': f'proyecto {pid} no encontrado'})
        return _resp(200, ficha)

    if action == 'gaceta':
        key = body.get('key')          # ej '857-2013'
        if not key:
            return _resp(400, {'error': 'falta key de gaceta (num-año)'})
        return _resp(200, _extraer_gaceta(key, body.get('contexto', '')))

    if action == 'contexto':           # rastreo de medios de un proyecto
        if not body.get('titulo'):
            return _resp(400, {'error': 'falta titulo del proyecto'})
        return _resp(200, _contexto_medios(body))

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
