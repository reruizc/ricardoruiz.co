"""
Lambda `descarga-barrio` — entrega paga de los Excel electorales por barrio.

Flujo:
  1) El cliente paga en un Link de Pago de Wompi (850.000 COP, uno por producto).
  2) Wompi lo devuelve a  descarga-entrega.html?p=<producto>&id=<tx>&env=prod
  3) Esa página hace POST {producto, tx} a esta Lambda (API Gateway).
  4) La Lambda:
       - consulta la API PÚBLICA de Wompi  GET /v1/transactions/{tx}
       - exige status == APPROVED  y  amount_in_cents >= PRECIO_MIN_CENTS
       - AMARRA la transacción a UN producto (marcador en S3):
           · primera redención -> guarda tx -> producto
           · redención posterior -> debe coincidir el producto y estar dentro de la
             ventana de 30 días  (permite re-descargar lo comprado, no comprar otro)
       - devuelve una URL FIRMADA de S3 (TTL 10 min) del archivo privado.

No pone credenciales AWS en ningún front: el IAM role de la Lambda tiene el
s3:GetObject/PutObject sobre el prefijo privado.  No toca el worker rr-auth.

Env vars:
  BUCKET        = elecciones-2026
  PREFIX        = ricardoruiz.co/productos-barrio/           (privado)
  MARKER_PREFIX = ricardoruiz.co/productos-barrio/_redenciones/
  WOMPI_BASE    = https://production.wompi.co/v1             (sandbox para pruebas)
  PRECIO_MIN    = 85000000                                   (850.000 * 100)
  URL_TTL       = 600
  VENTANA_DIAS  = 30
"""
import json, os, time, urllib.request, urllib.error
import boto3
from botocore.client import Config

BUCKET        = os.environ.get('BUCKET', 'elecciones-2026')
PREFIX        = os.environ.get('PREFIX', 'ricardoruiz.co/productos-barrio/')
MARKER_PREFIX = os.environ.get('MARKER_PREFIX', 'ricardoruiz.co/productos-barrio/_redenciones/')
WOMPI_BASE    = os.environ.get('WOMPI_BASE', 'https://production.wompi.co/v1')
PRECIO_MIN    = int(os.environ.get('PRECIO_MIN', '85000000'))     # 850.000 COP en centavos
URL_TTL       = int(os.environ.get('URL_TTL', '600'))            # 10 min
VENTANA_DIAS  = int(os.environ.get('VENTANA_DIAS', '30'))
HTTP_TIMEOUT  = 12

# producto_id -> archivo real en S3 (bajo PREFIX) + título humano
PRODUCTOS = {
    'resultados-1v': {'file': 'Resultados_1V_2026_por_barrio_ciudades.xlsx', 'titulo': 'Resultados 1ª vuelta 2026 por barrio · 17 ciudades'},
    'resultados-2v': {'file': 'Resultados_2V_2026_por_barrio_ciudades.xlsx', 'titulo': 'Resultados 2ª vuelta 2026 por barrio · 17 ciudades'},
    'genero-1v':     {'file': 'Genero_1V_2026_por_barrio_ciudades.xlsx',     'titulo': 'Género 1ª vuelta 2026 por barrio · 17 ciudades'},
    'genero-2v':     {'file': 'Genero_2V_2026_por_barrio_ciudades.xlsx',     'titulo': 'Género 2ª vuelta 2026 por barrio · 17 ciudades'},
    'edad-1v':       {'file': 'Edad_1V_2026_por_barrio_ciudades.xlsx',       'titulo': 'Composición etaria 1ª vuelta 2026 por barrio · 17 ciudades'},
    'edad-2v':       {'file': 'Edad_2V_2026_por_barrio_ciudades.xlsx',       'titulo': 'Composición etaria 2ª vuelta 2026 por barrio · 17 ciudades'},
}

_s3 = boto3.client('s3', config=Config(signature_version='s3v4', region_name='us-east-1'))

CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST,OPTIONS',
    'Content-Type': 'application/json',
}

def _resp(code, body):
    return {'statusCode': code, 'headers': CORS, 'body': json.dumps(body, ensure_ascii=False)}

def _wompi_tx(tx_id):
    url = f'{WOMPI_BASE}/transactions/{tx_id}'
    req = urllib.request.Request(url, headers={'User-Agent': 'ricardoruiz.co/descarga-barrio'})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
        return json.loads(r.read().decode('utf-8')).get('data', {})

def _marker_key(tx_id):
    safe = ''.join(c for c in str(tx_id) if c.isalnum() or c in '-_')
    return f'{MARKER_PREFIX}{safe}.json'

def _get_marker(tx_id):
    try:
        o = _s3.get_object(Bucket=BUCKET, Key=_marker_key(tx_id))
        return json.loads(o['Body'].read().decode('utf-8'))
    except _s3.exceptions.NoSuchKey:
        return None
    except Exception:
        return None

def _put_marker(tx_id, producto, tx):
    _s3.put_object(
        Bucket=BUCKET, Key=_marker_key(tx_id),
        Body=json.dumps({'producto': producto, 'ts': int(time.time()),
                         'amount': tx.get('amount_in_cents'), 'email': (tx.get('customer_email') or '')},
                        ensure_ascii=False).encode('utf-8'),
        ContentType='application/json')

def handler(event, context):
    if (event.get('requestContext', {}).get('http', {}).get('method') or event.get('httpMethod')) == 'OPTIONS':
        return _resp(200, {'ok': True})
    try:
        body = json.loads(event.get('body') or '{}')
    except Exception:
        return _resp(400, {'ok': False, 'error': 'body inválido'})

    producto = (body.get('producto') or '').strip()
    tx_id = (body.get('tx') or '').strip()
    if producto not in PRODUCTOS:
        return _resp(400, {'ok': False, 'error': 'producto desconocido'})
    if not tx_id:
        return _resp(400, {'ok': False, 'error': 'falta la transacción'})

    # 1) verificar pago con Wompi
    try:
        tx = _wompi_tx(tx_id)
    except urllib.error.HTTPError as e:
        return _resp(404, {'ok': False, 'error': f'transacción no encontrada ({e.code})'})
    except Exception:
        return _resp(502, {'ok': False, 'error': 'no se pudo verificar el pago; reintenta'})

    if tx.get('status') != 'APPROVED':
        return _resp(402, {'ok': False, 'error': f"pago no aprobado (estado: {tx.get('status') or 'desconocido'})",
                           'status': tx.get('status')})
    if int(tx.get('amount_in_cents') or 0) < PRECIO_MIN:
        return _resp(402, {'ok': False, 'error': 'monto insuficiente para este producto'})

    # 2) amarrar tx -> producto (una compra = un producto), permitir re-descarga 30 días
    m = _get_marker(tx_id)
    if m is None:
        _put_marker(tx_id, producto, tx)
    else:
        if m.get('producto') != producto:
            return _resp(409, {'ok': False, 'error': 'esta compra corresponde a otro producto'})
        if (time.time() - int(m.get('ts') or 0)) > VENTANA_DIAS * 86400:
            return _resp(410, {'ok': False, 'error': f'la ventana de descarga ({VENTANA_DIAS} días) expiró; escríbenos'})

    # 3) URL firmada del archivo privado
    info = PRODUCTOS[producto]
    try:
        url = _s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET, 'Key': PREFIX + info['file'],
                    'ResponseContentDisposition': f'attachment; filename="{info["file"]}"'},
            ExpiresIn=URL_TTL)
    except Exception:
        return _resp(500, {'ok': False, 'error': 'no se pudo generar el enlace de descarga'})

    return _resp(200, {'ok': True, 'url': url, 'titulo': info['titulo'],
                       'archivo': info['file'], 'ttl': URL_TTL})
