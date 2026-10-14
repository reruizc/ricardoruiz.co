#!/usr/bin/env python3
"""Sube mesas/{vuelta}-{dep}.json del visor de escrutinio a S3, COMPRIMIDOS.

  python3 tools/build-presidencial-escr/subir_mesas_s3.py --dry-run   # solo dice qué subiría
  python3 tools/build-presidencial-escr/subir_mesas_s3.py [clave …]   # sin clave: las 6

S3 no comprime nada por su cuenta: sin `Content-Encoding: gzip` el navegador baja el
JSON en claro (4× más). Destino: congreso-2026/output/pres-escr/<clave>/mesas/.
Después de subir, relee cada archivo por la URL PÚBLICA, lo descomprime y lo compara
byte a byte con el local; sale con código 1 si alguno no cuadra.
"""
import gzip, os, subprocess, sys, tempfile, urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.join(RAIZ, 'Bases de datos', 'output_presidencial_escr')
BUCKET = 's3://elecciones-2026/ricardoruiz.co/congreso-2026/output/pres-escr'
HTTP = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/pres-escr'
CLAVES = ['2010', '2014', '2018', '2022', '2026', 'pacto2025']


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry = '--dry-run' in sys.argv
    claves = args or CLAVES
    malos = 0
    for k in claves:
        src = os.path.join(BASE, k, 'mesas')
        fs = sorted(f for f in os.listdir(src) if f.endswith('.json'))
        with tempfile.TemporaryDirectory() as tmp:
            gz = 0
            for f in fs:
                data = open(os.path.join(src, f), 'rb').read()
                comp = gzip.compress(data, 9)
                gz += len(comp)
                open(os.path.join(tmp, f), 'wb').write(comp)
            print(f'{k}: {len(fs)} archivos · {gz/1e6:.2f} MB gzip → {BUCKET}/{k}/mesas/')
            if dry:
                continue
            subprocess.run(['aws', 's3', 'cp', tmp + '/', f'{BUCKET}/{k}/mesas/', '--recursive', '--only-show-errors',
                            '--content-type', 'application/json', '--content-encoding', 'gzip',
                            '--cache-control', 'public, max-age=300'], check=True)
        if dry:
            continue
        for f in fs:
            req = urllib.request.Request(f'{HTTP}/{k}/mesas/{f}', headers={'User-Agent': 'rr-verifica-mesas'})
            with urllib.request.urlopen(req) as r:
                body = r.read()
                enc = r.headers.get('Content-Encoding')
            if enc == 'gzip' or body[:2] == b'\x1f\x8b':
                body = gzip.decompress(body)
            if enc != 'gzip' or body != open(os.path.join(src, f), 'rb').read():
                malos += 1
                print(f'  [MAL] {k}/mesas/{f} (Content-Encoding={enc})')
        print(f'  verificado: {len(fs)} archivos, HTTP 200 anónimo + gzip + idéntico al local')
    sys.exit(1 if malos else 0)


if __name__ == '__main__':
    main()
