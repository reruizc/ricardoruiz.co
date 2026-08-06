"""Lambda tutela-analiza — lectura narrativa del caso con citas verificadas de
sentencias reales ("por qué se caen casos como el tuyo") para tutelas-salud.html.

Arquitectura (decisiones firmes, no re-litigar sin razón nueva):
- El conocimiento vive PRE-COMPUTADO en ratio-decidendi.json (build_ratio.py):
  la ratio decidendi de cada negativa de instancia, con cita textual verificada
  en build-time contra el corpus. En runtime el modelo NO genera citas — la
  Lambda las selecciona determinísticamente y las adjunta ya verificadas.
- Entrada: SOLO campos estructurados (whitelist dura, como tutela-registro).
  JAMÁS nombre/documento/contacto/texto libre. c_respuesta y c_estado son
  selects de opciones fijas → cuentan como estructurados.
- CACHE por celda estructurada (hash24 sin texto libre) en S3, TTL 14 días +
  PROMPT_VERSION. Casi todo el tráfico real cae en cache.
- TOPE DIARIO de generaciones no-cacheadas (contador en S3). Superado el tope,
  o si el LLM falla, responde el FALLBACK DETERMINISTA (taxonomía + citas) —
  el panel nunca depende del modelo para existir.
- ANTI-ALUCINACIÓN post-hoc: toda mención "T-NNN/AA" en el texto del modelo
  que no esté en el set entregado se reescribe; toda frase con un % que no sea
  el dato de contexto entregado se elimina. Cifras solo del JSON de tasas.
- Nada de promesas de resultado (reference_legaltech_riesgo_score): descriptivo,
  frecuencias empíricas, disclaimer fijo. Tuteo neutro bogotano, nunca voseo.

Deploy:
  cd tools/tutela-analiza/lambda-analiza && zip -j tutela-analiza.zip lambda_analiza.py
  aws lambda update-function-code --function-name tutela-analiza --zip-file fileb://tutela-analiza.zip

Env vars:
  DEEPSEEK_API_KEY   (la misma de caudal-analiza)
  DEEPSEEK_MODEL     default deepseek-chat — NO v4-flash: la redacción no
                     necesita reasoning y el reasoning multiplica costo y
                     latencia (medido en build_ratio: 10x costo, 20x tiempo)
  TUTELA_CAP_DIA     default 150 generaciones no-cacheadas por día
"""
import datetime
import hashlib
import json
import os
import re
import urllib.request

import boto3

BUCKET = 'elecciones-2026'
PREFIX = 'ricardoruiz.co/tutelas-privado/'
RATIO_KEY = PREFIX + 'ratio-decidendi.json'
CAUSAS_KEY = PREFIX + 'causas-fracaso.json'
CACHE_PREFIX = PREFIX + 'cache-lectura/'
CAP_PREFIX = PREFIX + 'cap/'

PROMPT_VERSION = 'l1-2026-08-05'
CACHE_TTL_DIAS = 14

DEEPSEEK_URL = os.environ.get('DEEPSEEK_URL', 'https://api.deepseek.com/chat/completions')
DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
CAP_DIA = int(os.environ.get('TUTELA_CAP_DIA', '150'))
HTTP_TIMEOUT = 40

s3 = boto3.client('s3')
_warm = {}

CASOS = {'medicamentos', 'citas', 'procedimientos'}
SUJETOS = {'menor', 'mayor', 'discap', 'gestante', 'cronica', 'catastrofica',
           'huerfana', 'victima', 'indigena', 'afro', 'vulnerable', 'rural'}

DISCLAIMER = ('Esta lectura describe cómo han fallado los jueces en casos con características '
              'similares, según sentencias públicas de la Corte Constitucional. No es asesoría '
              'jurídica ni una predicción sobre tu caso.')

CASO_TXT = {
    'medicamentos': 'entrega de medicamentos o insumos ya formulados',
    'citas': 'asignación oportuna de citas o consultas médicas',
    'procedimientos': 'práctica oportuna de un procedimiento ya ordenado',
}

SYSTEM = """Eres el analista jurídico de una herramienta gratuita que ayuda a personas en Colombia a preparar tutelas de salud. Escribes para un ciudadano sin formación jurídica. Tuteo neutro bogotano (tú), NUNCA voseo.

Recibes: (a) las características estructuradas de un caso, (b) un dato empírico de contexto (opcional), (c) los RIESGOS detectados (causas por las que jueces de instancia han negado casos similares, según sentencias reales de la Corte Constitucional que se te listan como MATERIAL).

Devuelve JSON estricto:
{
 "lectura": ["párrafo 1 (60-90 palabras)", "párrafo 2 (60-90 palabras)"],
 "riesgos": [ { "causa": "<id tal cual te lo di>", "texto": "1-2 frases aterrizadas a ESTE caso: por qué ese riesgo aplica aquí y qué lo neutraliza" } ]
}

Párrafo 1: qué caracteriza los casos como este (pretensión, situación) y qué muestra el contexto empírico si se entregó. Párrafo 2: por qué se caen casos como este ante los jueces de instancia (ancla en las causas del MATERIAL) y la idea general de que el expediente bien soportado es lo que evita esas caídas.

Reglas duras:
1. NO prometas resultados, NO digas que la tutela "va a ganar", "será concedida" ni nada equivalente. Todo descriptivo: "casos como el tuyo", "los jueces han negado cuando…".
2. NO inventes sentencias, artículos, cifras ni porcentajes. Solo puedes mencionar sentencias que estén en el MATERIAL (formato T-NNN/AA). El único porcentaje permitido es el del dato de contexto, si se entregó.
3. NO menciones EPS específicas ni datos personales. El caso es anónimo.
4. Un objeto en "riesgos" por cada causa entregada, mismo orden, misma id.
5. Español claro, sin jerga procesal sin explicar. Sin markdown."""


# ── carga warm de los JSON de conocimiento ──
def _get_json(key):
    if key in _warm:
        return _warm[key]
    obj = s3.get_object(Bucket=BUCKET, Key=key)
    data = json.loads(obj['Body'].read().decode('utf-8'))
    _warm[key] = data
    return data


# ── whitelist de entrada ──
def _sanitize(data):
    if not isinstance(data, dict):
        return None
    out = {}
    caso = data.get('caso')
    if caso not in CASOS:
        return None
    out['caso'] = caso
    for k, cap in (('depto', 60), ('rol', 12), ('c_respuesta', 200), ('c_estado', 200),
                   ('via_nivel', 30)):
        v = data.get(k)
        if isinstance(v, str) and v.strip():
            out[k] = v.strip()[:cap]
    for k in ('urgente', 'pqr', 'pqr_resp'):
        out[k] = bool(data.get(k))
    for k, lo, hi in (('dias', 0, 4000), ('anexos_n', 0, 30), ('via_n', 0, 10**7)):
        v = data.get(k)
        if isinstance(v, (int, float)):
            out[k] = max(lo, min(hi, int(v)))
    v = data.get('via_p')
    if isinstance(v, (int, float)) and 0 <= v <= 1:
        out['via_p'] = round(float(v), 4)
    suj = data.get('sujetos')
    if isinstance(suj, list):
        out['sujetos'] = sorted({str(x) for x in suj[:14] if str(x) in SUJETOS})
    else:
        out['sujetos'] = []
    return out


# ── motor de riesgos (determinista) ──
def _elegir_causas(inp):
    """Puntúa las causas de la taxonomía contra las banderas del caso.
    Devuelve hasta 3 ids ordenadas por relevancia."""
    caso = inp['caso']
    dias = inp.get('dias')
    sc = {}
    # No probar los hechos es la causa #1 del corpus y aplica a casi todo caso;
    # pesa más si no hay reclamo previo radicado ni anexos.
    sc['falta_prueba'] = 2 + (2 if not inp.get('pqr') else 0) + (1 if inp.get('anexos_n', 1) == 0 else 0)
    sc['sin_orden_medica'] = 2 if caso in ('medicamentos', 'procedimientos') else 1
    sc['subsidiariedad'] = 1 + (1 if not inp.get('urgente') else 0)
    if isinstance(dias, int):
        if dias >= 180:
            sc['inmediatez'] = 4
        elif dias >= 120:
            sc['inmediatez'] = 2
    rol = inp.get('rol', '')
    if rol == 'agente':
        sc['legitimacion'] = 3
    elif rol and rol not in ('propio', 'menor'):
        sc['legitimacion'] = 2
    if inp.get('c_respuesta', '').startswith('que solo hay entrega parcial'):
        sc['hecho_superado'] = 2
    if caso == 'medicamentos':
        sc['no_pbs_sin_prueba'] = 1
    top = sorted(sc.items(), key=lambda kv: -kv[1])
    return [k for k, v in top[:3] if v > 0]


def _citas_para(causas, caso):
    """Selecciona citas del pre-cómputo: por causa, con overlap de caso,
    recientes primero, cita textual verificada preferida. Máx 2 por causa."""
    ratio = _get_json(RATIO_KEY)
    out = []
    vistos = set()  # global: una sentencia no se repite entre causas
    for causa in causas:
        cands = []
        for e in ratio.get('entradas', []):
            for r in e.get('ratios', []):
                if r.get('causa') != causa:
                    continue
                cands.append({
                    'sentencia': e['sentencia'], 'ano': e.get('ano', ''),
                    'url': e.get('url', ''), 'causa': causa,
                    'pretension': e.get('pretension', ''),
                    'razon': r.get('razon', ''), 'cita': r.get('cita'),
                    '_caso': caso in (e.get('casos') or []),
                })
        # prioridad: (mismo caso, con cita textual) → recientes primero
        ordered = sorted(cands, key=lambda c: (not c['_caso'], not c['cita'], -int(c['ano'] or 0)))
        for c in ordered:
            if c['sentencia'] in vistos:
                continue
            vistos.add(c['sentencia'])
            c.pop('_caso', None)
            out.append(c)
            if len([x for x in out if x['causa'] == causa]) >= 2:
                break
    return out


# ── cache + tope diario ──
def _cache_key(inp):
    dias = inp.get('dias')
    banda = ('0-15' if dias is None or dias <= 15 else
             '16-60' if dias <= 60 else '61-179' if dias < 180 else '180+')
    sep = bool(inp.get('sujetos'))
    celda = {
        'pv': PROMPT_VERSION, 'caso': inp['caso'], 'depto': inp.get('depto', ''),
        'sep': sep, 'banda': banda, 'urgente': inp.get('urgente'), 'pqr': inp.get('pqr'),
        'pqr_resp': inp.get('pqr_resp'), 'rol': inp.get('rol', ''),
        'resp': inp.get('c_respuesta', ''), 'estado': inp.get('c_estado', ''),
        'via_nivel': inp.get('via_nivel', ''),
    }
    h = hashlib.sha256(json.dumps(celda, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]
    return CACHE_PREFIX + h + '.json'


def _cache_get(key):
    try:
        obj = s3.get_object(Bucket=BUCKET, Key=key)
        data = json.loads(obj['Body'].read().decode('utf-8'))
        ts = datetime.datetime.fromisoformat(data['ts'])
        edad = (datetime.datetime.now(datetime.timezone.utc) - ts).days
        if edad <= CACHE_TTL_DIAS:
            return data['resp']
    except Exception:
        pass
    return None


def _cache_put(key, resp):
    try:
        s3.put_object(Bucket=BUCKET, Key=key, ContentType='application/json',
                      Body=json.dumps({'ts': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                       'resp': resp}, ensure_ascii=False).encode('utf-8'))
    except Exception as e:
        print(f'[cache] WARN put: {e}')


def _cap_ok():
    """Tope diario de generaciones no-cacheadas. Lectura-incremento no atómico:
    con este tráfico es suficiente como freno grueso."""
    hoy = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d')
    key = CAP_PREFIX + hoy + '.json'
    n = 0
    try:
        n = json.loads(s3.get_object(Bucket=BUCKET, Key=key)['Body'].read())['n']
    except Exception:
        pass
    if n >= CAP_DIA:
        print(f'[cap] tope diario alcanzado: {n}')
        return False
    try:
        s3.put_object(Bucket=BUCKET, Key=key, ContentType='application/json',
                      Body=json.dumps({'n': n + 1}).encode())
    except Exception:
        pass
    return True


# ── fallback determinista (sin LLM) ──
def _fallback(inp, causas, causas_info):
    caso_txt = CASO_TXT.get(inp['caso'], 'atención en salud')
    p1 = (f'Tu caso es una tutela por {caso_txt}, el tipo de reclamo de salud más frecuente en el país. '
          'En estos casos el servicio ya está reconocido en el plan de beneficios: lo que se discute ante '
          'el juez no es la cobertura sino la demora de la EPS en cumplir.')
    p2 = ('Cuando los jueces niegan tutelas como esta, casi siempre es por el expediente, no por el fondo: '
          'no se aportó la orden médica, no quedó rastro del reclamo a la EPS o no se probó lo que se afirma. '
          'Adjuntar cada soporte y relatar fechas concretas es lo que evita esas caídas.')
    riesgos = []
    for cid in causas:
        info = causas_info.get(cid, {})
        texto = (info.get('explica', '') + ' ' + info.get('como_se_arregla', '')).strip()
        riesgos.append({'causa': cid, 'titulo': info.get('titulo', cid), 'texto': texto})
    return {'lectura': [p1, p2], 'riesgos': riesgos}


# ── LLM ──
def _call_deepseek(user_msg, max_tokens=2500):
    body = json.dumps({
        'model': DEEPSEEK_MODEL,
        'messages': [{'role': 'system', 'content': SYSTEM},
                     {'role': 'user', 'content': user_msg}],
        'temperature': 0.3,
        'response_format': {'type': 'json_object'},
        'max_tokens': max_tokens,
    }).encode('utf-8')
    req = urllib.request.Request(DEEPSEEK_URL, data=body, method='POST', headers={
        'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
        'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
        data = json.loads(r.read().decode('utf-8'))
    choice = data['choices'][0]
    content = choice['message'].get('content') or ''
    if not content:
        # gotcha V4: si algún día se cambia el modelo a uno con reasoning,
        # el presupuesto se va en reasoning y content llega vacío
        raise ValueError(f"content vacío (finish_reason={choice.get('finish_reason')})")
    print(f"[deepseek] usage={data.get('usage')}")
    return json.loads(content), data.get('usage', {})


SENT_RE = re.compile(r'T-\d{1,4}\s*[/-]\s*\d{2,4}')
PCT_RE = re.compile(r'\d+(?:[.,]\d+)?\s*%')


def _post_verifica(texto, permitidas, pct_ok):
    """Anti-alucinación sobre el texto del modelo: sentencias fuera del set
    entregado se generalizan; frases con % no permitidos se eliminan."""
    def _norm_sent(s):
        return re.sub(r'\s', '', s).replace('-', '/', 1).replace('T/','T-')
    perm = {_norm_sent(p) for p in permitidas}
    def sub_sent(m):
        return m.group(0) if _norm_sent(m.group(0)) in perm else 'la jurisprudencia de la Corte'
    texto = SENT_RE.sub(sub_sent, texto)
    frases = re.split(r'(?<=[.!?])\s+', texto)
    keep = []
    for f in frases:
        malos = [m for m in PCT_RE.findall(f) if not (pct_ok and m.replace(' ', '').rstrip('%').replace(',', '.') == pct_ok)]
        if malos:
            print(f'[verifica] frase eliminada por % no permitido: {f[:120]}')
            continue
        keep.append(f)
    return ' '.join(keep).strip()


def _lectura_llm(inp, causas, citas, causas_info):
    caso_txt = CASO_TXT.get(inp['caso'], '')
    lineas = [f"CASO (anónimo, estructurado):",
              f"- Tipo: {inp['caso']} ({caso_txt})",
              f"- Departamento: {inp.get('depto', 'sin dato')}"]
    if inp.get('sujetos'):
        lineas.append(f"- Condiciones de especial protección: {', '.join(inp['sujetos'])}")
    if isinstance(inp.get('dias'), int):
        lineas.append(f"- Días de espera desde la orden/fórmula: {inp['dias']}")
    lineas.append(f"- ¿Reclamó antes a la EPS?: {'sí' if inp.get('pqr') else 'no'}"
                  + (' (con respuesta)' if inp.get('pqr_resp') else ''))
    if inp.get('urgente'):
        lineas.append('- La persona declara urgencia médica')
    if inp.get('c_respuesta'):
        lineas.append(f"- Respuesta que recibe de la entidad: {inp['c_respuesta']}")
    if inp.get('c_estado'):
        lineas.append(f"- Estado del trámite: {inp['c_estado']}")

    pct_ok = None
    if isinstance(inp.get('via_p'), float) and inp.get('via_n'):
        pct = round(inp['via_p'] * 100)
        pct_ok = str(pct)
        lineas.append(f"\nDATO EMPÍRICO DE CONTEXTO (única cifra que puedes usar): entre {inp['via_n']:,} "
                      f"tutelas similares resueltas en el último año, el {pct}% terminó a favor de quien tuteló.".replace(',', '.'))

    lineas.append('\nRIESGOS DETECTADOS (causas de negativa en casos similares):')
    for cid in causas:
        info = causas_info.get(cid, {})
        lineas.append(f"- id={cid} · {info.get('titulo', cid)}: {info.get('explica', '')} "
                      f"Cómo se evita: {info.get('como_se_arregla', '')}")
    lineas.append('\nMATERIAL (sentencias reales; las únicas que puedes mencionar):')
    for c in citas:
        lineas.append(f"- {c['sentencia']} ({c['ano']}) · causa={c['causa']} · el juez de instancia negó porque: {c['razon']}")
    lineas.append('\nRedacta el JSON. Recuerda: descriptivo, sin promesas, tuteo neutro, '
                  'solo sentencias del MATERIAL, ningún porcentaje distinto del dato de contexto.')

    out, usage = _call_deepseek('\n'.join(lineas))
    permitidas = [c['sentencia'] for c in citas]
    lectura = out.get('lectura')
    if isinstance(lectura, str):
        lectura = [lectura]
    if not isinstance(lectura, list) or not lectura:
        raise ValueError('JSON sin lectura')
    lectura = [_post_verifica(str(p), permitidas, pct_ok) for p in lectura[:3]]
    lectura = [p for p in lectura if len(p) > 40]
    if not lectura:
        raise ValueError('lectura vacía tras verificación')

    riesgos = []
    modelo_r = {r.get('causa'): r.get('texto', '') for r in out.get('riesgos', []) if isinstance(r, dict)}
    for cid in causas:
        info = causas_info.get(cid, {})
        texto = _post_verifica(str(modelo_r.get(cid, '') or ''), permitidas, pct_ok)
        if len(texto) < 30:
            texto = (info.get('explica', '') + ' ' + info.get('como_se_arregla', '')).strip()
        riesgos.append({'causa': cid, 'titulo': info.get('titulo', cid), 'texto': texto})
    return {'lectura': lectura, 'riesgos': riesgos}, usage


# ── handler ──
CORS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST,OPTIONS',
    'Access-Control-Allow-Headers': 'content-type',
}


def _resp(code, body):
    return {'statusCode': code, 'headers': CORS, 'body': json.dumps(body, ensure_ascii=False)}


def handler(event, context):
    method = ((event.get('requestContext') or {}).get('http') or {}).get('method', 'POST')
    if method == 'OPTIONS':
        return {'statusCode': 204, 'headers': CORS, 'body': ''}

    body = event.get('body') or ''
    if event.get('isBase64Encoded'):
        import base64
        try:
            body = base64.b64decode(body).decode('utf-8', 'replace')
        except Exception:
            return _resp(400, {'error': 'bad body'})
    if len(body) > 20000:
        return _resp(413, {'error': 'too big'})
    try:
        data = json.loads(body)
    except Exception:
        return _resp(400, {'error': 'bad json'})

    if data.get('action', 'lectura') != 'lectura':
        return _resp(400, {'error': 'unknown action'})
    inp = _sanitize(data)
    if not inp:
        return _resp(400, {'error': 'bad payload'})

    try:
        causas_doc = _get_json(CAUSAS_KEY)
        causas_info = {c['id']: c for c in causas_doc.get('causas', [])}
    except Exception as e:
        print(f'[s3] causas: {e}')
        causas_info = {}

    causas = _elegir_causas(inp)
    try:
        citas = _citas_para(causas, inp['caso'])
    except Exception as e:
        print(f'[s3] ratio: {e}')
        citas = []

    key = _cache_key(inp)
    cached = _cache_get(key)
    if cached:
        cached['fuente'] = 'cache'
        return _resp(200, cached)

    resp = None
    if DEEPSEEK_API_KEY and citas and _cap_ok():
        try:
            core, usage = _lectura_llm(inp, causas, citas, causas_info)
            resp = {'ok': True, 'fuente': 'llm', 'usage': usage}
            resp.update(core)
        except Exception as e:
            print(f'[llm] fallo → fallback: {e}')
    if resp is None:
        resp = {'ok': True, 'fuente': 'fallback'}
        resp.update(_fallback(inp, causas, causas_info))

    # las citas van SIEMPRE adjuntadas por la Lambda (verificadas en build)
    resp['citas'] = [{'sentencia': c['sentencia'], 'ano': c['ano'], 'url': c['url'],
                      'causa': c['causa'], 'razon': c['razon'], 'cita': c['cita']}
                     for c in citas]
    resp['disclaimer'] = DISCLAIMER
    resp['pv'] = PROMPT_VERSION
    if resp['fuente'] == 'llm':
        _cache_put(key, resp)
    return _resp(200, resp)
