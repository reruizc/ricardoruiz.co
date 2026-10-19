#!/usr/bin/env python3
"""
gzip_json_s3.py — comprime en su sitio los JSON grandes de S3 (Content-Encoding: gzip).

Hermano de tools/analisis-candidato/gzip_indices_s3.py, pero para MILES de
archivos: las fichas mesa a mesa por candidato (endoso/{slug}.json y demás) y
los datos de Policía. S3 no comprime nada solo; una ficha de senador pesaba
12-22 MB en claro y baja ~30 veces con gzip, sin cambiar un byte del JSON.

    python3 tools/s3/gzip_json_s3.py --prefijo congreso-2026/output/endoso/ --dry-run
    python3 tools/s3/gzip_json_s3.py --prefijo congreso-2026/output/endoso/ --min-kb 200
    python3 tools/s3/gzip_json_s3.py --prefijo congreso-2026/output/endoso/ --revertir
    python3 tools/s3/gzip_json_s3.py --prefijo congreso-2026/output/endoso/ --verificar

Por cada archivo: se salta si ya está en gzip · guarda el ORIGINAL en
`Bases de datos/s3-gzip-backup/<key>` · valida que sea JSON · sube la versión
comprimida conservando Content-Type, Cache-Control y metadatos · la RELEE por
la URL pública y exige que, descomprimida, sea idéntica byte a byte al
original. Si algo falla, restaura el original en el acto. Bitácora en
`Bases de datos/s3-gzip-backup/bitacora.jsonl`.

⚠ Quien lea estos JSON FUERA del navegador tiene que descomprimir (urllib no
lo hace solo): mirar los bytes mágicos 1f 8b, como hace _get_json en
tools/fotos-candidatos/sync.py.
⚠ Al regenerar y re-subir un archivo con `aws s3 cp` vuelve a quedar en claro,
sin error. Hay que volver a correr esta herramienta sobre su prefijo.
"""
import argparse, gzip, json, os, sys, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3
from botocore.config import Config

BUCKET = 'elecciones-2026'
RAIZ = 'ricardoruiz.co/'
HTTP = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/'
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKUP = os.path.join(ROOT, 'Bases de datos', 's3-gzip-backup')
BITACORA = os.path.join(BACKUP, 'bitacora.jsonl')

# reintentos: con varias tandas a la vez S3 corta conexiones y da read timeouts
s3 = boto3.client('s3', region_name='us-east-1',
                  config=Config(retries={'max_attempts': 8, 'mode': 'adaptive'}, read_timeout=180, connect_timeout=30))
_lock = threading.Lock()


def url_publica(key):
    from urllib.parse import quote
    return HTTP + quote(key)


def listar(prefijo, min_bytes):
    out = []
    for pag in s3.get_paginator('list_objects_v2').paginate(Bucket=BUCKET, Prefix=prefijo):
        for o in pag.get('Contents', []):
            if o['Key'].endswith('.json') and o['Size'] >= min_bytes:
                out.append((o['Key'], o['Size']))
    return out


def anota(reg):
    with _lock:
        with open(BITACORA, 'a', encoding='utf-8') as f:
            f.write(json.dumps(reg, ensure_ascii=False) + '\n')


def sube(key, cuerpo, head, gz):
    kw = dict(Bucket=BUCKET, Key=key, Body=cuerpo,
              ContentType=head.get('ContentType') or 'application/json',
              CacheControl=head.get('CacheControl') or 'public, max-age=300',
              Metadata=head.get('Metadata') or {})
    if gz:
        kw['ContentEncoding'] = 'gzip'
    s3.put_object(**kw)


def relee(key, intentos=4):
    for k in range(intentos):
        try:
            return _relee(key)
        except Exception:
            if k == intentos - 1:
                raise
            time.sleep(2 + 3 * k)


def _relee(key):
    req = urllib.request.Request(url_publica(key), headers={'Accept-Encoding': 'gzip',
                                 'User-Agent': 'gzip_json_s3/1.0 (+https://ricardoruiz.co)'})
    with urllib.request.urlopen(req, timeout=300) as r:
        crudo = r.read()
        ce = (r.headers.get('Content-Encoding') or '').lower()
    return (gzip.decompress(crudo) if crudo[:2] == b'\x1f\x8b' else crudo), ce, len(crudo)


def comprime(key, dry):
    head = s3.head_object(Bucket=BUCKET, Key=key)
    if (head.get('ContentEncoding') or '').lower() == 'gzip':
        return ('ya', key, head['ContentLength'], head['ContentLength'])
    if dry:
        return ('dry', key, head['ContentLength'], None)
    orig = s3.get_object(Bucket=BUCKET, Key=key)['Body'].read()
    json.loads(orig.decode('utf-8'))                       # JSON válido o no se toca
    dest = os.path.join(BACKUP, key)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if not os.path.exists(dest):
        with open(dest, 'wb') as f:
            f.write(orig)
    gz = gzip.compress(orig, compresslevel=9, mtime=0)
    sube(key, gz, head, True)
    try:
        plano, ce, n = relee(key)
        if plano != orig or ce != 'gzip':
            raise RuntimeError(f'verificación fallida (ce={ce!r})')
    except Exception as e:
        sube(key, orig, head, False)                     # vuelve al original
        anota({'key': key, 'estado': 'restaurado', 'error': str(e)})
        return ('error', key, len(orig), str(e))
    anota({'key': key, 'estado': 'gzip', 'antes': len(orig), 'despues': len(gz),
           'cache': head.get('CacheControl'), 'ts': time.strftime('%Y-%m-%dT%H:%M:%S')})
    return ('ok', key, len(orig), len(gz))


def revierte(key, dry):
    dest = os.path.join(BACKUP, key)
    if not os.path.exists(dest):
        return ('sin-respaldo', key, 0, None)
    head = s3.head_object(Bucket=BUCKET, Key=key)
    if (head.get('ContentEncoding') or '').lower() != 'gzip':
        return ('ya', key, head['ContentLength'], None)
    if dry:
        return ('dry', key, head['ContentLength'], None)
    orig = open(dest, 'rb').read()
    sube(key, orig, head, False)
    anota({'key': key, 'estado': 'revertido'})
    return ('ok', key, len(orig), len(orig))


def verifica(key, dry):
    """Lo servido, descomprimido, debe ser idéntico al respaldo. Si difiere,
    se restaura el original (nunca debería pasar; es la red de seguridad)."""
    dest = os.path.join(BACKUP, key)
    if not os.path.exists(dest):
        return ('sin-respaldo', key, 0, None)
    orig = open(dest, 'rb').read()
    plano, ce, n = relee(key)
    if plano == orig:
        return ('identico-gzip' if ce == 'gzip' else 'identico-claro', key, len(orig), n)
    if not dry:
        sube(key, orig, s3.head_object(Bucket=BUCKET, Key=key), False)
        anota({'key': key, 'estado': 'restaurado-por-verificacion'})
    return ('error', key, len(orig), 'DIFIERE del respaldo · restaurado')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prefijo', action='append', required=True,
                    help='relativo a ricardoruiz.co/ (se puede repetir)')
    ap.add_argument('--min-kb', type=int, default=200)
    ap.add_argument('--hilos', type=int, default=12)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--revertir', action='store_true')
    ap.add_argument('--verificar', action='store_true',
                    help='compara todo lo que tiene respaldo contra lo servido')
    a = ap.parse_args()
    os.makedirs(BACKUP, exist_ok=True)

    objetos = []
    for p in a.prefijo:
        p = p if p.startswith(RAIZ) else RAIZ + p
        objetos += listar(p, 0 if a.verificar else a.min_kb * 1024)
    if a.verificar:
        objetos = [(k, n) for k, n in objetos if os.path.exists(os.path.join(BACKUP, k))]
    total_mb = sum(s for _, s in objetos) / 1e6
    print(f'{len(objetos)} archivos ≥ {a.min_kb} KB · {total_mb:,.0f} MB listados', flush=True)

    fn = verifica if a.verificar else (revierte if a.revertir else comprime)
    cuenta = {}
    antes = despues = 0
    t0 = time.time()
    with ThreadPoolExecutor(a.hilos) as ex:
        futs = [ex.submit(fn, k, a.dry_run) for k, _ in objetos]
        for i, f in enumerate(as_completed(futs), 1):
            try:
                estado, key, b0, b1 = f.result()
            except Exception as e:
                estado, key, b0, b1 = 'error', '?', 0, str(e)
            cuenta[estado] = cuenta.get(estado, 0) + 1
            if estado == 'ok' and isinstance(b1, int):
                antes += b0; despues += b1
            if estado == 'error':
                print(f'  ✗ {key}: {b1}', flush=True)
            if i % 100 == 0 or i == len(futs):
                print(f'  {i}/{len(futs)} · {cuenta} · {antes/1e6:,.0f} → {despues/1e6:,.0f} MB'
                      f' · {time.time()-t0:,.0f} s', flush=True)
    print('listo:', cuenta)
    sys.exit(1 if cuenta.get('error') else 0)


if __name__ == '__main__':
    main()
