#!/usr/bin/env python3
"""
subir_2023.py — sube a S3 los índices y agregados de 2023 ya verificados.

Existe porque el entorno de trabajo remoto no trae la CLI de `aws` y porque sus
variables AWS_* están ocupadas por el proxy de red (su AWS_ACCESS_KEY_ID vale
literalmente «proxy…»). Este script NO las usa: lee las suyas, con otro nombre,
para no pelear con el proxy.

    export RR_S3_KEY_ID=…            # de un usuario IAM que solo pueda PutObject
    export RR_S3_SECRET=…            #   sobre …/output/{concejo,jal,asamblea}-2023/*
    python3 tools/analisis-candidato/subir_2023.py --dir "Bases de datos"

Antes de subir nada vuelve a correr la verificación: un índice malo en S3 le da
metas equivocadas a todos los clientes a la vez, y deshacerlo es volver a subir.
Después de subir comprueba que el archivo quedó legible sin credenciales, que es
como lo lee el sitio: si el bucket publica por ACL y no por política, un objeto
nuevo saldría privado y la página se rompería en silencio.

    --seco       no sube: dice qué subiría
    --sin-verificar   salta la verificación (para reintentar una subida a medias)
"""
import argparse, hashlib, os, subprocess, sys, urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUCKET = 'elecciones-2026'
PREFIJO = 'ricardoruiz.co/congreso-2026/output'
PUBLICO = f'https://{BUCKET}.s3.us-east-1.amazonaws.com/{PREFIJO}'
CARPETAS = [('output_concejo_2023', 'concejo-2023'),
            ('output_jal_2023', 'jal-2023'),
            ('output_asamblea_2023', 'asamblea-2023')]


def archivos(base):
    """(ruta local, clave en S3) de cada JSON a subir, en orden estable."""
    out = []
    for carpeta, destino in CARPETAS:
        raiz = os.path.join(base, carpeta)
        if not os.path.isdir(raiz):
            continue
        for dirpath, _dirs, files in os.walk(raiz):
            for f in sorted(files):
                if not f.endswith('.json'):
                    continue
                local = os.path.join(dirpath, f)
                rel = os.path.relpath(local, raiz).replace(os.sep, '/')
                out.append((local, f'{PREFIJO}/{destino}/{rel}'))
    return sorted(out, key=lambda x: x[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=os.path.join(RAIZ, 'Bases de datos'))
    ap.add_argument('--seco', action='store_true')
    ap.add_argument('--sin-verificar', action='store_true')
    args = ap.parse_args()

    pares = archivos(args.dir)
    if not pares:
        sys.exit(f'no hay nada que subir en {args.dir}: ¿corrió regenerar_2023.sh?')
    peso = sum(os.path.getsize(p) for p, _ in pares)
    print(f'{len(pares):,} archivos · {peso / 1e6:.1f} MB')

    if not args.sin_verificar:
        print('\n══ verificación')
        v = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                         'verificar_listas_2023.py'), '--dir', args.dir])
        if v.returncode != 0:
            sys.exit('\n✗ la verificación no pasó: no se sube nada.')

    if args.seco:
        print('\n══ subiría (--seco)')
        for _l, k in pares[:5]:
            print(f'  {k}')
        print(f'  … y {len(pares) - 5:,} más' if len(pares) > 5 else '')
        return 0

    key, secret = os.environ.get('RR_S3_KEY_ID'), os.environ.get('RR_S3_SECRET')
    if not key or not secret:
        sys.exit('faltan RR_S3_KEY_ID y RR_S3_SECRET en el entorno '
                 '(no se usan las AWS_*: las tiene tomadas el proxy).')
    import boto3
    from botocore.exceptions import ClientError
    s3 = boto3.client('s3', region_name='us-east-1',
                      aws_access_key_id=key, aws_secret_access_key=secret)

    print('\n══ subiendo')
    subidos = 0
    for local, clave in pares:
        cuerpo = open(local, 'rb').read()
        try:
            s3.put_object(Bucket=BUCKET, Key=clave, Body=cuerpo,
                          ContentType='application/json',
                          CacheControl='public, max-age=300')
        except ClientError as e:
            err = e.response['Error']
            sys.exit(f'\n✗ {clave}: {err["Code"]} · {err.get("Message", "")[:120]}\n'
                     f'  Se subieron {subidos:,} de {len(pares):,}. Repita con --sin-verificar.')
        subidos += 1
        if subidos % 200 == 0 or subidos == len(pares):
            print(f'  {subidos:,}/{len(pares):,}')

    # Que el sitio lo pueda leer: se comprueba SIN credenciales, como un visitante.
    print('\n══ comprobación pública')
    fallos = 0
    for local, clave in [p for p in pares if p[1].endswith('index-concejo-2023.json')
                         or p[1].endswith('resultados-jal-2023.json')] or pares[:2]:
        url = f'https://{BUCKET}.s3.us-east-1.amazonaws.com/{clave}'
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                remoto = hashlib.sha256(r.read()).hexdigest()
            igual = remoto == hashlib.sha256(open(local, 'rb').read()).hexdigest()
            print(f'  {"✓" if igual else "✗"} {clave.split("/")[-1]} legible y {"idéntico" if igual else "DISTINTO"}')
            fallos += 0 if igual else 1
        except Exception as e:
            print(f'  ✗ {clave.split("/")[-1]}: {type(e).__name__} {str(e)[:80]}')
            print('    Si es 403, el bucket publica por ACL y no por política: '
                  'hay que subir con --acl public-read (y permitir s3:PutObjectAcl).')
            fallos += 1
    if fallos:
        return 1
    print('\nListo. El índice manda sobre candidato-360-data/listas-2023.json en cuanto '
          'trae «listas», así que ese archivo ya se puede quitar del repo.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
