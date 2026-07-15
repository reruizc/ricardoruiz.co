#!/usr/bin/env python3
"""
sync.py — sistematiza las fotos de candidatos de analisis-candidato.html.

Comandos:
  python3 tools/fotos-candidatos/sync.py status
      Cruza el índice de candidatos (endoso + presidenciales) contra las fotos
      que YA están en S3 y escribe fotos-candidatos/pendientes.csv (ordenado
      por votos desc). Imprime el top de faltantes.

  python3 tools/fotos-candidatos/sync.py subir [--dry-run] [--force]
      Toma cada imagen de fotos-candidatos/pendientes/ (nombrada {SLUG}.png|jpg),
      valida el slug contra el índice, la normaliza (JPG, máx 1200 px, sips) y
      la sube a s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/fotos-candidatos/
      con content-type y cache-control. El original pasa a fotos-candidatos/subidas/.
      --force sube aunque el slug no esté en el índice.

Requiere: aws CLI configurado (ricardo-mac-cli) y sips (macOS).
"""
import csv, json, os, shutil, subprocess, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STAGING = os.path.join(ROOT, 'fotos-candidatos')
PEND = os.path.join(STAGING, 'pendientes')
DONE = os.path.join(STAGING, 'subidas')
CSV_OUT = os.path.join(STAGING, 'pendientes.csv')

S3_BUCKET_PREFIX = 's3://elecciones-2026/ricardoruiz.co/congreso-2026/output/fotos-candidatos/'
ENDOSO_INDEX = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/endoso/index.json'
PRES_INDEX_LOCAL = os.path.join(ROOT, 'Bases de datos', 'output_presidencial_endoso', 'index-presidencial.json')
PRES_INDEX_S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/presidencial/index-presidencial.json'
ASAM_INDEX_LOCAL = os.path.join(ROOT, 'Bases de datos', 'output_asamblea_2023', 'index-asamblea-2023.json')
ASAM_INDEX_S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/asamblea-2023/index-asamblea-2023.json'
TARGET_W, TARGET_H = 1248, 864     # tamaño editorial fijo 3:2 (crop-to-fill centrado)
EXTS = ('.png', '.jpg', '.jpeg', '.webp', '.tiff', '.heic')


def load_candidates():
    """Índice completo: endoso (congreso+consultas) + presidenciales."""
    with urllib.request.urlopen(ENDOSO_INDEX, timeout=60) as r:
        endoso = json.load(r)
    cands = [
        {'slug': c['slug'], 'nombre': c['nombre'], 'corp': c.get('corp', ''),
         'partido': c.get('partido', ''), 'votos': c.get('votos', 0)}
        for c in endoso if c.get('tipo') == 'candidato'
    ]
    pres = None
    if os.path.exists(PRES_INDEX_LOCAL):
        pres = json.load(open(PRES_INDEX_LOCAL, encoding='utf-8'))
    else:
        try:
            with urllib.request.urlopen(PRES_INDEX_S3, timeout=30) as r:
                pres = json.load(r)
        except Exception:
            pass
    if pres:
        for p in pres.get('personas', []):
            if p.get('foto'):
                continue  # ya tiene foto oficial en Fotos-presidenciales/
            el = p['elecciones'][0]
            cands.append({
                'slug': el['file'].replace('.json', ''),
                'nombre': p['nombre'], 'corp': 'PRESIDENCIA 2026',
                'partido': p.get('partido', ''),
                'votos': max(e['votos'] for e in p['elecciones']),
            })
    # Asamblea Departamental 2023
    asam = None
    if os.path.exists(ASAM_INDEX_LOCAL):
        asam = json.load(open(ASAM_INDEX_LOCAL, encoding='utf-8'))
    else:
        try:
            with urllib.request.urlopen(ASAM_INDEX_S3, timeout=60) as r:
                asam = json.load(r)
        except Exception:
            pass
    if asam:
        for c in asam.get('candidatos', []):
            cands.append({
                'slug': c['slug'], 'nombre': c['nombre'],
                'corp': c.get('corp', 'ASAMBLEA 2023'),
                'partido': c.get('partido', ''), 'votos': c.get('votos', 0),
            })
    return cands


def s3_existing():
    """Set de slugs con foto ya subida (aws s3 ls)."""
    r = subprocess.run(['aws', 's3', 'ls', S3_BUCKET_PREFIX],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f'AVISO: aws s3 ls falló ({r.stderr.strip()[:200]}) — asumo 0 fotos en S3')
        return set()
    slugs = set()
    for line in r.stdout.splitlines():
        name = line.split()[-1] if line.split() else ''
        if name.lower().endswith('.jpg'):
            slugs.add(name[:-4])
    return slugs


def cmd_status():
    cands = load_candidates()
    existing = s3_existing()
    cands.sort(key=lambda c: -c['votos'])
    faltan = [c for c in cands if c['slug'] not in existing]
    with open(CSV_OUT, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['slug', 'nombre', 'corp', 'partido', 'votos', 'tiene_foto'])
        for c in cands:
            w.writerow([c['slug'], c['nombre'], c['corp'], c['partido'],
                        c['votos'], 'SI' if c['slug'] in existing else ''])
    print(f'{len(cands)} candidatos · {len(existing)} con foto en S3 · {len(faltan)} sin foto')
    print(f'→ {os.path.relpath(CSV_OUT, ROOT)} (ordenado por votos)')
    print('\nTop 20 faltantes (crear como pendientes/{slug}.png):')
    for c in faltan[:20]:
        print(f"  {c['votos']:>10,}  {c['slug']:55s} {c['nombre']}".replace(',', '.'))


def _img_size(path):
    r = subprocess.run(['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', path],
                       capture_output=True, text=True)
    w = h = 0
    for line in r.stdout.splitlines():
        s = line.strip()
        if s.startswith('pixelWidth:'):  w = int(s.split()[-1])
        if s.startswith('pixelHeight:'): h = int(s.split()[-1])
    return w, h


def normalize(src, dst_jpg):
    """Convierte a JPG y recorta al tamaño editorial EXACTO 1248×864 (crop-to-fill
    centrado, sin deformar): escala para cubrir el lado que falta y recorta el sobrante."""
    w, h = _img_size(src)
    # Escala para CUBRIR: fija el lado que se quedaría corto, el otro sobra y se recorta.
    # w*TH >= h*TW  ⇔  el ancho sobra al fijar la altura → resample por altura.
    resample = (['--resampleHeight', str(TARGET_H)] if w * TARGET_H >= h * TARGET_W
                else ['--resampleWidth', str(TARGET_W)])
    r = subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '88',
                        *resample, src, '--out', dst_jpg], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f'sips resample falló: {r.stderr.strip()[:200]}')
    # Recorte centrado al tamaño exacto (sips -c es alto ancho).
    r = subprocess.run(['sips', '-c', str(TARGET_H), str(TARGET_W), dst_jpg],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f'sips crop falló: {r.stderr.strip()[:200]}')


def cmd_subir(dry=False, force=False):
    files = [f for f in sorted(os.listdir(PEND)) if f.lower().endswith(EXTS)] if os.path.isdir(PEND) else []
    if not files:
        print(f'Nada en {os.path.relpath(PEND, ROOT)}/ — deja ahí las imágenes nombradas {{SLUG}}.png')
        return
    slugs = {c['slug'] for c in load_candidates()}
    ok = skip = 0
    for fname in files:
        slug = os.path.splitext(fname)[0]
        src = os.path.join(PEND, fname)
        if slug not in slugs and not force:
            print(f'  ✗ {fname}: slug no está en el índice (¿typo?) — usa --force para subir igual')
            skip += 1
            continue
        key = f'{S3_BUCKET_PREFIX}{slug}.jpg'
        if dry:
            print(f'  [dry-run] {fname} → {key}')
            ok += 1
            continue
        tmp = os.path.join(PEND, f'.__norm_{slug}.jpg')
        try:
            normalize(src, tmp)
            r = subprocess.run(['aws', 's3', 'cp', tmp, key,
                                '--content-type', 'image/jpeg',
                                '--cache-control', 'public, max-age=86400'],
                               capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(r.stderr.strip()[:200])
            os.makedirs(DONE, exist_ok=True)
            shutil.move(src, os.path.join(DONE, fname))
            print(f'  ✓ {slug}.jpg subida ({os.path.getsize(tmp)//1024} KB)')
            ok += 1
        except Exception as e:
            print(f'  ✗ {fname}: {e}')
            skip += 1
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
    print(f'\n{ok} subida(s){" (simuladas)" if dry else ""} · {skip} omitida(s)')
    if ok and not dry:
        print('Las fotos aparecen en la página de inmediato (cache S3 24 h para las ya vistas).')


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args or args[0] == 'status':
        cmd_status()
    elif args[0] == 'subir':
        cmd_subir(dry='--dry-run' in args, force='--force' in args)
    else:
        print(__doc__)
