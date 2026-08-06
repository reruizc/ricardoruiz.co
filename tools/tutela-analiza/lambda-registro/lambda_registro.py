"""Lambda tutela-registro — estadística anónima de cada diligenciamiento de tutelas-salud.html.

Recibe un POST (sendBeacon, body text/plain con JSON) y guarda UN objeto JSON por evento en
S3 privado:  s3://elecciones-2026/ricardoruiz.co/tutelas-registros/eventos/yyyy=/mm=/dd=/...

Principios (no romperlos al iterar):
- WHITELIST dura de campos: lo que no está en el esquema se descarta en silencio.
  Es la defensa en profundidad contra PII: aunque el frontend cambie, aquí jamás
  entra nombre, documento, dirección, teléfono, correo ni nombre de médico.
- No se guarda IP, ni User-Agent, ni ningún header. El objeto es solo el payload saneado
  + ts_server. "Anónimo" tiene que ser verdad.
- Los eventos se agrupan por `sid` (id aleatorio por carga de página). El CSV se compila
  aparte con tools/tutela-analiza/build_registros_csv.py (S3 no permite append).

Deploy:
  cd tools/tutela-analiza/lambda-registro && zip -j tutela-registro.zip lambda_registro.py
  aws lambda update-function-code --function-name tutela-registro --zip-file fileb://tutela-registro.zip
"""
import json
import uuid
import base64
import datetime

import boto3

BUCKET = 'elecciones-2026'
PREFIX = 'ricardoruiz.co/tutelas-registros/eventos/'

s3 = boto3.client('s3')

CASOS = {'medicamentos', 'citas', 'procedimientos'}
EVENTOS = {'genera', 'pdf', 'word', 'copy', 'print', 'save'}
SUJETOS = {'menor', 'mayor', 'discap', 'gestante', 'cronica', 'catastrofica',
           'huerfana', 'victima', 'indigena', 'afro', 'vulnerable', 'rural'}

# clave -> (tipo, tope de longitud si es str)
STR = {
    'sid': 40, 'evento': 12, 'v': 12, 'ts': 40,
    'caso': 20, 'rol': 12, 'zona': 12, 'estrato': 8,
    'regimen': 30, 'calidad': 30, 'eps': 80, 'ips': 160,
    'depto': 60, 'ciudad': 80,
    'diag': 300,
    'c_item': 300, 'c_dosis': 200, 'c_respuesta': 200, 'c_estado': 200,
    'c_fecha': 12, 'c_fechadada': 12, 'c_veces': 8,
    'via_nivel': 30, 'adm_global': 12,
}
BOOL = {'prepagada', 'poliza', 'urgente', 'pqr', 'pqr_resp', 'ninguna'}
INT = {'dias', 'anexos_n', 'via_n'}
FLOAT = {'via_p'}
ACCESORIAS = {'transporte', 'acompanante', 'cuidador', 'integral', 'insumos'}
LISTS = {'sujetos': 14, 'anexos_tipos': 20, 'adm': 12, 'accesorias': 6}


def _sanitize(data):
    if not isinstance(data, dict):
        return None
    out = {}
    for k, cap in STR.items():
        v = data.get(k)
        if isinstance(v, (int, float)):
            v = str(v)
        if isinstance(v, str) and v.strip():
            out[k] = v.strip()[:cap]
    for k in BOOL:
        if k in data:
            out[k] = bool(data[k])
    for k in INT:
        v = data.get(k)
        if isinstance(v, (int, float)):
            out[k] = int(v)
    for k in FLOAT:
        v = data.get(k)
        if isinstance(v, (int, float)):
            out[k] = round(float(v), 4)
    for k, cap in LISTS.items():
        v = data.get(k)
        if isinstance(v, list):
            vals = [str(x)[:60] for x in v[:cap] if isinstance(x, (str, int, float))]
            if k == 'sujetos':
                vals = [x for x in vals if x in SUJETOS]
            if k == 'accesorias':
                vals = [x for x in vals if x in ACCESORIAS]
            if vals:
                out[k] = vals
    if out.get('caso') not in CASOS:
        return None
    if out.get('evento') not in EVENTOS:
        return None
    if not out.get('sid'):
        return None
    return out


def _resp(code, body):
    return {'statusCode': code,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(body)}


def handler(event, context):
    body = event.get('body') or ''
    if event.get('isBase64Encoded'):
        try:
            body = base64.b64decode(body).decode('utf-8', 'replace')
        except Exception:
            return _resp(400, {'error': 'bad body'})
    if len(body) > 60000:
        return _resp(413, {'error': 'too big'})
    try:
        data = json.loads(body)
    except Exception:
        return _resp(400, {'error': 'bad json'})

    out = _sanitize(data)
    if not out:
        return _resp(400, {'error': 'bad payload'})

    now = datetime.datetime.now(datetime.timezone.utc)
    out['ts_server'] = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    key = (PREFIX + now.strftime('yyyy=%Y/mm=%m/dd=%d/')
           + now.strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:10] + '.json')
    s3.put_object(Bucket=BUCKET, Key=key,
                  Body=json.dumps(out, ensure_ascii=False).encode('utf-8'),
                  ContentType='application/json')
    return _resp(200, {'ok': True})
