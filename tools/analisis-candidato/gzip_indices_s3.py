#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Re-sube los índices de candidatos a S3 COMPRIMIDOS con gzip.

El problema: S3 no comprime nada por su cuenta. Los 29 índices que
`cand-index.js` baja al abrir analisis-candidato.html suman ~90 MB en claro
(8,5 MB de arranque + 82 MB de Concejo y JAL), y por eso la página tardaba
minutos: el contador saltaba de 31 mil a 400 mil candidatos varios minutos
después de abrir.

El arreglo no cambia NI UN BYTE del contenido: se sube el mismo JSON con
`Content-Encoding: gzip`, que el navegador descomprime solo. Medido sobre
`index-concejo-2023.json`: 19,4 MB → 2,87 MB (6,7×). El total baja de ~90 MB
a ~13 MB.

  python3 tools/analisis-candidato/gzip_indices_s3.py --dry-run   # qué haría
  python3 tools/analisis-candidato/gzip_indices_s3.py --solo concejo-2023/index-concejo-2023.json
  python3 tools/analisis-candidato/gzip_indices_s3.py            # todos

⚠️ Quien lea estos índices FUERA del navegador tiene que descomprimir: urllib
   no lo hace solo. `tools/fotos-candidatos/sync.py` ya está adaptado.
   Para volver atrás: `--revertir` re-sube el JSON en claro desde el respaldo
   local que esta misma herramienta deja en `Bases de datos/indices-s3-backup/`.
"""
import argparse, gzip, io, json, os, subprocess, sys, tempfile, urllib.request

BUCKET = 's3://elecciones-2026/ricardoruiz.co/congreso-2026/output'
HTTP   = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output'
ROOT   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKUP = os.path.join(ROOT, 'Bases de datos', 'indices-s3-backup')

# Los mismos que SOURCES + LOCAL_SOURCES de cand-index.js, más el presidencial.
INDICES = [
    'endoso/index.json',
    'presidencial/index-presidencial.json',
] + [f'{d}/index-{d}.json' for d in [
    'asamblea-2023', 'asamblea-2019', 'asamblea-2015', 'asamblea-2011',
    'gobernacion-2023', 'gobernacion-2019', 'gobernacion-2015', 'gobernacion-2011',
    'alcaldia-2023', 'alcaldia-2019', 'alcaldia-2015', 'alcaldia-2011',
    'congreso-2014', 'congreso-2018', 'congreso-2022',
    'pres-2010', 'pres-2014', 'pres-2018', 'pres-2022', 'consu-2022',
    'concejo-2023', 'concejo-2019', 'concejo-2015', 'concejo-2011',
    'jal-2023', 'jal-2019', 'jal-2015', 'jal-2011',
]]


def baja(key):
    """Descarga cruda, descomprimiendo si ya viene en gzip (re-corridas)."""
    req = urllib.request.Request(f'{HTTP}/{key}', headers={'Accept-Encoding': 'gzip'})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = r.read()
        ce = (r.headers.get('Content-Encoding') or '').lower()
    if ce == 'gzip' or data[:2] == b'\x1f\x8b':
        data = gzip.decompress(data)
    json.loads(data.decode('utf-8'))     # garantiza que lo subido es JSON válido
    return data


def sube(key, data, encoding=None):
    cmd = ['aws', 's3', 'cp', '-', f'{BUCKET}/{key}',
           '--content-type', 'application/json',
           '--cache-control', 'public, max-age=300']
    if encoding:
        cmd += ['--content-encoding', encoding]
    p = subprocess.run(cmd, input=data, capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.decode('utf-8', 'replace').strip())


def verifica(key, esperado_bytes):
    """Relee lo subido y confirma que un cliente que descomprime ve el MISMO JSON."""
    req = urllib.request.Request(f'{HTTP}/{key}', headers={'Accept-Encoding': 'gzip'})
    with urllib.request.urlopen(req, timeout=300) as r:
        crudo = r.read()
        ce = (r.headers.get('Content-Encoding') or '').lower()
    plano = gzip.decompress(crudo) if (ce == 'gzip' or crudo[:2] == b'\x1f\x8b') else crudo
    if plano != esperado_bytes:
        raise RuntimeError('el contenido servido NO coincide con el original')
    return len(crudo), ce


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--solo', action='append', help='una key concreta (repetible)')
    ap.add_argument('--revertir', action='store_true', help='re-sube el JSON en claro desde el respaldo')
    a = ap.parse_args()

    keys = a.solo or INDICES
    os.makedirs(BACKUP, exist_ok=True)
    tot_antes = tot_despues = 0
    fallos = []

    for i, key in enumerate(keys, 1):
        try:
            local = os.path.join(BACKUP, key.replace('/', '__'))
            if a.revertir:
                if not os.path.exists(local):
                    print(f'  {i:2}/{len(keys)}  {key:46} SIN RESPALDO — se salta'); continue
                data = open(local, 'rb').read()
                if not a.dry_run:
                    sube(key, data, encoding=None)
                    verifica(key, data)
                print(f'  {i:2}/{len(keys)}  {key:46} revertido a claro ({len(data)/1e6:.2f} MB)')
                continue

            data = baja(key)
            open(local, 'wb').write(data)            # respaldo del claro, para --revertir
            comp = gzip.compress(data, 9)
            tot_antes += len(data); tot_despues += len(comp)
            marca = f'{len(data)/1e6:7.2f} MB → {len(comp)/1e6:6.2f} MB  ({len(data)/max(len(comp),1):.1f}×)'
            if a.dry_run:
                print(f'  {i:2}/{len(keys)}  {key:46} {marca}   [dry-run]')
                continue
            sube(key, comp, encoding='gzip')
            servido, ce = verifica(key, data)
            ok = '✓' if ce == 'gzip' and servido == len(comp) else '⚠'
            print(f'  {i:2}/{len(keys)}  {key:46} {marca}   {ok} verificado')
        except Exception as e:
            fallos.append((key, str(e)))
            print(f'  {i:2}/{len(keys)}  {key:46} ✗ {e}')

    if tot_antes:
        print(f'\n  TOTAL  {tot_antes/1e6:.1f} MB → {tot_despues/1e6:.1f} MB '
              f'({tot_antes/max(tot_despues,1):.1f}× menos transferencia)')
    if fallos:
        print(f'\n  {len(fallos)} con error:')
        for k, e in fallos: print(f'    {k}: {e}')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
