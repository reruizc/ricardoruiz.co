#!/usr/bin/env python3
"""
Fragmenta los dep-{cod}.json de cámara en dos niveles:

1. dep-{cod}.json (slim/nav): dep root + mun (con candidatos) + com/zon + puestos
   SIN candidatos ni por_circunscripcion a nivel com/pue, SIN mesas.
   Tamaño: 1.6–3.6 MB por dep.

2. dep-{cod}/com-{mun_cod}-{com_cod}.json: com/zona completa con candidatos,
   puestos con candidatos y mesas. Máx ~21 MB (Suba), promedio 0.5–7 MB.

Uso: python3 slim_camara_deps.py
"""

import json, os, glob

BASE = os.path.dirname(os.path.abspath(__file__))


def mb(size_bytes):
    return size_bytes / 1024 / 1024


def make_nav(d):
    """Versión nav del dep: mun con candidatos, com/pue sin candidatos, sin mesas."""
    out = {k: v for k, v in d.items() if k != 'municipios'}
    out['municipios'] = []
    for mun in d.get('municipios', []):
        # Municipio: conservar TODO (incluyendo candidatos y por_circunscripcion)
        m2 = {k: v for k, v in mun.items() if k not in ('comunas', 'zonas')}
        areas_key = 'comunas' if 'comunas' in mun else 'zonas'
        m2[areas_key] = []
        for com in mun.get(areas_key, []):
            # Com: quitar candidatos/por_circunscripcion
            c2 = {k: v for k, v in com.items()
                  if k not in ('puestos', 'candidatos', 'por_circunscripcion')}
            # Puestos: quitar candidatos/por_circunscripcion y mesas
            c2['puestos'] = [
                {k: v for k, v in p.items()
                 if k not in ('mesas', 'candidatos', 'por_circunscripcion')}
                for p in com.get('puestos', [])
            ]
            m2[areas_key].append(c2)
        out['municipios'].append(m2)
    return out


def split_dep(dep_path):
    dep_cod = os.path.basename(dep_path).replace('dep-', '').replace('.json', '')
    orig_mb = mb(os.path.getsize(dep_path))
    print(f'\nProcesando dep-{dep_cod}.json ({orig_mb:.0f} MB)...')

    with open(dep_path, encoding='utf-8') as f:
        d = json.load(f)

    # 1. Generar archivos per-com
    out_dir = os.path.join(BASE, f'dep-{dep_cod}')
    os.makedirs(out_dir, exist_ok=True)

    total_com_files = 0
    total_com_mb = 0.0
    for mun in d.get('municipios', []):
        mun_cod = mun.get('cod', '')
        areas_key = 'comunas' if 'comunas' in mun else 'zonas'
        for com in mun.get(areas_key, []):
            com_cod = com.get('cod', com.get('com_cod', ''))
            fname = f'com-{mun_cod}-{com_cod}.json'
            fpath = os.path.join(out_dir, fname)
            raw = json.dumps(com, ensure_ascii=False, separators=(',', ':'))
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(raw)
            total_com_files += 1
            total_com_mb += len(raw) / 1024 / 1024

    print(f'  -> {total_com_files} archivos com escritos en dep-{dep_cod}/ ({total_com_mb:.1f} MB total)')

    # 2. Generar slim nav
    nav = make_nav(d)
    nav_raw = json.dumps(nav, ensure_ascii=False, separators=(',', ':'))
    nav_mb = len(nav_raw) / 1024 / 1024
    print(f'  -> Versión nav: {nav_mb:.1f} MB (era {orig_mb:.0f} MB)')

    ans = input(f'  Sobreescribir dep-{dep_cod}.json con versión slim? [s/N] ')
    if ans.strip().lower() == 's':
        with open(dep_path, 'w', encoding='utf-8') as f:
            f.write(nav_raw)
        print(f'  dep-{dep_cod}.json reemplazado.')
    else:
        print(f'  dep-{dep_cod}.json conservado (original).')


if __name__ == '__main__':
    dep_files = sorted(glob.glob(os.path.join(BASE, 'dep-*.json')))
    if not dep_files:
        print('No se encontraron archivos dep-*.json en', BASE)
    else:
        print(f'Encontrados {len(dep_files)} archivos dep-*.json')
        print('Para cada uno: genera dep-{cod}/com-{mun}-{com}.json y ofrece reemplazar el original.')
        for path in dep_files:
            split_dep(path)
        print('\nListo. Sube a S3: camara/dep-{cod}.json slim + carpetas camara/dep-{cod}/')
