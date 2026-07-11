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
PROMPT_VERSION = 'v3'            # bumpear para invalidar cache de síntesis
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
                  str(resumen['n_intentos']) + '|' + str(resumen['n_leyes']))
    cached = _cache_get(key)
    if cached:
        return cached
    intentos_txt = '\n'.join(
        f"- [{it['anio']}] {it['resultado_txt']}: {it['titulo'][:90]}"
        for it in resumen['intentos'][:20])
    autores_txt = ', '.join(f"{a} ({n})" for a, n in resumen['top_autores'][:6])
    bancadas_txt = ', '.join(f"{p} ({n} proyectos)" for p, n in resumen.get('bancadas', [])[:6]) or 'sin dato'
    cob = resumen.get('cobertura_partido', {})
    user = (
        f"Tema consultado: «{resumen['query']}»\n"
        f"Intentos totales: {resumen['n_intentos']} · convertidos en ley: "
        f"{resumen['n_leyes']} ({resumen['pct_exito']}%) · caídos: "
        f"{resumen['n_caidos']} (de esos, {resumen['n_muerte_por_tiempo']} "
        f"murieron por vencimiento de términos, Art. 190 Ley 5ª).\n"
        f"Periodo: {resumen.get('periodo')}\n"
        f"Embudo del trámite: {json.dumps(resumen['embudo'], ensure_ascii=False)}\n"
        f"Quiénes más lo intentan: {autores_txt}\n"
        f"Bancadas que lo impulsan (por partido de los autores, "
        f"cobertura {cob.get('con')}/{cob.get('con',0)+cob.get('sin',0)} intentos): {bancadas_txt}\n"
        f"Línea de intentos:\n{intentos_txt}\n\n"
        "Escribe el análisis en JSON. `titular`: una frase potente y precisa. "
        "`hallazgo`: 2-3 frases con el patrón central. `por_que_caen`: la causa "
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
