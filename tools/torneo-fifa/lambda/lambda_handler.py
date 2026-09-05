"""Publica marcadores del torneo FIFA desde cualquier celular.

POST {"id":"A0","i":0,"v":"3","por":"Ricardo"}  -> aplica UN cambio al JSON de S3.
Lee el estado actual, mezcla el cambio y lo vuelve a escribir, de modo que dos
telefonos que registran partidos distintos al tiempo no se pisan. La escritura va
condicionada al ETag leido (If-Match): si alguien mas escribio en el intermedio,
reintenta sobre el estado nuevo.

Solo toca la llave del torneo; no expone borrado ni resorteo.
"""
import json, os, re, time
import boto3
from botocore.exceptions import ClientError, ParamValidationError

BUCKET = 'elecciones-2026'
KEY = 'ricardoruiz.co/congreso-2026/output/torneo-fifa/resultados.json'
s3 = boto3.client('s3')

IDS_GRUPO = {g + str(r) for g in 'ABCD' for r in range(6)}
IDS_KO = {'Q1', 'Q2', 'Q3', 'Q4', 'S1', 'S2', 'F'}
IDS = IDS_GRUPO | IDS_KO
NOMBRE_RE = re.compile(r'^[\w .\'/áéíóúñÁÉÍÓÚÑ-]{1,20}$')

CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
}


def _resp(code, obj):
    return {'statusCode': code, 'headers': {'Content-Type': 'application/json', **CORS},
            'body': json.dumps(obj, ensure_ascii=False)}


def _valida(d):
    """Devuelve (id, i, v, por) o lanza ValueError con un mensaje legible."""
    mid = str(d.get('id', ''))
    if mid not in IDS:
        raise ValueError('partido desconocido')
    try:
        i = int(d.get('i'))
    except (TypeError, ValueError):
        raise ValueError('casilla invalida')
    if i not in (0, 1, 2):
        raise ValueError('casilla invalida')
    v = d.get('v', '')
    v = '' if v is None else str(v).strip()
    if i == 2:                                    # ganador por penales
        if v not in ('', 'h', 'a'):
            raise ValueError('penales invalidos')
        if mid not in IDS_KO:
            raise ValueError('los penales solo aplican en eliminatorias')
    else:
        if v != '':
            if not v.isdigit() or not (0 <= int(v) <= 20):
                raise ValueError('el marcador va de 0 a 20')
            v = str(int(v))
    por = str(d.get('por', '')).strip()
    if por and not NOMBRE_RE.match(por):
        por = ''
    return mid, i, v, por


def _valida_bracket(b):
    if not isinstance(b, list) or len(b) != 4:
        raise ValueError('el sorteo debe traer 4 llaves')
    planos = []
    for par in b:
        if not isinstance(par, list) or len(par) != 2:
            raise ValueError('cada llave son dos equipos')
        for t in par:
            if not isinstance(t, int) or not (0 <= t <= 15):
                raise ValueError('equipo invalido en el sorteo')
            planos.append(t)
    if len(set(planos)) != 8:
        raise ValueError('un equipo aparece dos veces en el sorteo')
    return b


def _leer():
    try:
        o = s3.get_object(Bucket=BUCKET, Key=KEY)
        return json.loads(o['Body'].read()), o.get('ETag')
    except ClientError as e:
        if e.response['Error']['Code'] in ('NoSuchKey', '404'):
            return None, None
        raise


def _escribir(estado, etag):
    """Escribe condicionado al ETag. Devuelve False si alguien escribio primero."""
    kw = dict(Bucket=BUCKET, Key=KEY, Body=json.dumps(estado, ensure_ascii=False).encode(),
              ContentType='application/json', CacheControl='no-cache, max-age=0')
    if etag:
        kw['IfMatch'] = etag
    try:
        s3.put_object(**kw)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] in ('PreconditionFailed', 'ConditionalRequestConflict'):
            return False                          # alguien escribio primero
        raise
    except ParamValidationError:                  # boto3 sin soporte de IfMatch
        kw.pop('IfMatch', None)
        s3.put_object(**kw)
        return True


def handler(event, context):
    metodo = (event.get('requestContext', {}).get('http', {}).get('method') or '').upper()
    if metodo == 'OPTIONS':
        return {'statusCode': 204, 'headers': CORS, 'body': ''}
    if metodo != 'POST':
        return _resp(405, {'ok': False, 'error': 'usa POST'})

    cuerpo = event.get('body') or ''
    if len(cuerpo) > 2000:
        return _resp(413, {'ok': False, 'error': 'peticion demasiado grande'})
    try:
        datos = json.loads(cuerpo)
        bracket = _valida_bracket(datos['bracket']) if 'bracket' in datos else None
        if bracket is None:
            mid, i, v, por = _valida(datos)
        else:
            por = str(datos.get('por', '')).strip()
            por = por if NOMBRE_RE.match(por or ' ') else ''
    except ValueError as e:
        return _resp(400, {'ok': False, 'error': str(e)})
    except Exception:
        return _resp(400, {'ok': False, 'error': 'JSON invalido'})

    for intento in range(4):
        estado, etag = _leer()
        if estado is None:
            return _resp(409, {'ok': False, 'error': 'el torneo aun no esta publicado'})
        scores = estado.setdefault('scores', {})
        meta = estado.setdefault('meta', {})
        ahora = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        if bracket is not None:
            estado['bracket'] = bracket
            for k in IDS_KO:                      # sorteo nuevo, eliminatoria en blanco
                scores.pop(k, None)
                meta.pop(k, None)
            meta['_sorteo'] = {'por': por, 'ts': ahora}
        else:
            fila = scores.get(mid) or ['', '', '']
            while len(fila) < 3:
                fila.append('')
            fila[i] = v
            scores[mid] = fila
            meta[mid] = {'por': por, 'ts': ahora}
        estado['ts'] = ahora
        if _escribir(estado, etag):
            return _resp(200, {'ok': True, 'scores': scores, 'meta': meta,
                               'bracket': estado.get('bracket'), 'ts': ahora})
        time.sleep(0.15 * (intento + 1))
    return _resp(503, {'ok': False, 'error': 'varios telefonos escribiendo al tiempo, intenta otra vez'})
