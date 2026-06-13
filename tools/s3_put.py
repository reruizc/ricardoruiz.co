#!/usr/bin/env python3.10
"""
Subida mínima a S3 vía SigV4 con stdlib pura (sin boto3, sin awscli).
Workaround cuando `aws` se rompe (p.ej. python@3.14 con pyexpat incompatible).
Correr con un python que tenga expat sano: python3.10.

Uso:
  python3.10 tools/s3_put.py <archivo_local> <s3_key> [content-type] [cache-control]

s3_key es la llave dentro del bucket (sin 's3://bucket/'), con espacios
literales si la ruta los tiene (ej: 'ricardoruiz.co/bases de datos/...').
"""
import sys, os, hashlib, hmac, datetime, configparser
import urllib.request, urllib.parse, urllib.error

REGION = 'us-east-1'
SERVICE = 's3'
BUCKET = 'elecciones-2026'
HOST = f'{BUCKET}.s3.{REGION}.amazonaws.com'


def _creds():
    cp = configparser.ConfigParser()
    cp.read(os.path.expanduser('~/.aws/credentials'))
    s = cp['default']
    return s['aws_access_key_id'], s['aws_secret_access_key'], s.get('aws_session_token')


def _sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()


def _sigkey(secret, datestamp):
    k = _sign(('AWS4' + secret).encode('utf-8'), datestamp)
    k = _sign(k, REGION)
    k = _sign(k, SERVICE)
    k = _sign(k, 'aws4_request')
    return k


def put(local, key, ctype='application/json', cache='public, max-age=300'):
    ak, sk, token = _creds()
    with open(local, 'rb') as f:
        body = f.read()
    payload_hash = hashlib.sha256(body).hexdigest()
    t = datetime.datetime.utcnow()
    amzdate = t.strftime('%Y%m%dT%H%M%SZ')
    datestamp = t.strftime('%Y%m%d')
    canonical_uri = '/' + urllib.parse.quote(key, safe='/~')

    headers = {
        'host': HOST,
        'x-amz-content-sha256': payload_hash,
        'x-amz-date': amzdate,
    }
    if token:
        headers['x-amz-security-token'] = token
    signed_headers = ';'.join(sorted(headers))
    canonical_headers = ''.join(f'{h}:{headers[h]}\n' for h in sorted(headers))
    canonical_request = '\n'.join(['PUT', canonical_uri, '', canonical_headers, signed_headers, payload_hash])
    scope = f'{datestamp}/{REGION}/{SERVICE}/aws4_request'
    sts = '\n'.join(['AWS4-HMAC-SHA256', amzdate, scope,
                     hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()])
    signature = hmac.new(_sigkey(sk, datestamp), sts.encode('utf-8'), hashlib.sha256).hexdigest()
    auth = (f'AWS4-HMAC-SHA256 Credential={ak}/{scope}, '
            f'SignedHeaders={signed_headers}, Signature={signature}')

    url = f'https://{HOST}' + canonical_uri
    req = urllib.request.Request(url, data=body, method='PUT')
    req.add_header('Authorization', auth)
    req.add_header('x-amz-content-sha256', payload_hash)
    req.add_header('x-amz-date', amzdate)
    if token:
        req.add_header('x-amz-security-token', token)
    req.add_header('Content-Type', ctype)
    req.add_header('Cache-Control', cache)
    req.add_header('Content-Length', str(len(body)))
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.status


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    local = sys.argv[1]
    key = sys.argv[2]
    ctype = sys.argv[3] if len(sys.argv) > 3 else 'application/json'
    cache = sys.argv[4] if len(sys.argv) > 4 else 'public, max-age=300'
    try:
        st = put(local, key, ctype, cache)
        print(f'OK {st}  {key}  ({os.path.getsize(local)} bytes)')
    except urllib.error.HTTPError as e:
        sys.stderr.write(f'HTTP {e.code} {key}\n{e.read().decode()[:600]}\n')
        sys.exit(2)
