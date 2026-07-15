#!/usr/bin/env python3
"""
build_asamblea_2023.py — genera los JSONs por candidato de ASAMBLEA DEPARTAMENTAL
2023 en el MISMO formato mesa-a-mesa de endoso/{slug}.json que consume
analisis-candidato.html, más un index-asamblea-2023.json para el buscador.

Asamblea es circunscripción DEPARTAMENTAL: cada candidato compite solo en su
departamento (COD_DDE), así que su mapa colorea un único departamento y su drill
baja a los municipios de ese depto. No hay Bogotá (no tiene asamblea).

Fuentes (locales):
  Bases de datos/FINAL SUBIDA GCS/GCS_2023TER.csv   (COD_COR='2' = ASAMBLEA)
  Bases de datos/PUESTOS_GEOREF.csv                 (nombres mun/puesto/comuna)

Salida:
  Bases de datos/output_asamblea_2023/
    index-asamblea-2023.json
    ASAM2023-{dde}-{par}-{can}.json   (uno por candidato · ~3.3k)

Códigos: COD_DDE es Registraduría (Antioquia=1) → coincide con el electoral_id
del mapa vía normalizeDepCode. Se padea a 2 díg para casar con PUESTOS_GEOREF.

Subida a S3 (manual, pedir luz verde):
  aws s3 cp "Bases de datos/output_asamblea_2023/" \
    "s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/asamblea-2023/" \
    --recursive --content-type "application/json" --cache-control "public, max-age=300"
"""
import csv, json, os, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BD   = os.path.join(ROOT, 'Bases de datos')
SRC  = os.path.join(BD, 'FINAL SUBIDA GCS', 'GCS_2023TER.csv')
GEOREF = os.path.join(BD, 'PUESTOS_GEOREF.csv')
OUT_DIR = os.path.join(BD, 'output_asamblea_2023')

# Nombres de depto correctos (georef trae "NORTE DE SAN" truncado, etc.).
DEP_NAMES = {
    '01': 'ANTIOQUIA', '03': 'ATLÁNTICO', '05': 'BOLÍVAR', '07': 'BOYACÁ',
    '09': 'CALDAS', '11': 'CAUCA', '12': 'CESAR', '13': 'CÓRDOBA',
    '15': 'CUNDINAMARCA', '17': 'CHOCÓ', '19': 'HUILA', '21': 'MAGDALENA',
    '23': 'NARIÑO', '24': 'RISARALDA', '25': 'NORTE DE SANTANDER',
    '26': 'QUINDÍO', '27': 'SANTANDER', '28': 'SUCRE', '29': 'TOLIMA',
    '31': 'VALLE DEL CAUCA', '40': 'ARAUCA', '44': 'CAQUETÁ', '46': 'CASANARE',
    '48': 'LA GUAJIRA', '50': 'GUAINÍA', '52': 'META', '54': 'GUAVIARE',
    '56': 'SAN ANDRÉS', '60': 'AMAZONAS', '64': 'PUTUMAYO', '68': 'VAUPÉS',
    '72': 'VICHADA',
}
SPECIAL_CAN = {'0', '996', '997', '998', '999'}  # partido/blanco/nulos/no-marcados

# Correcciones de nombre mal digitado en la fuente RNEC (slug → nombre correcto).
# Vacío por ahora: los nombres se dejan tal cual los trae la Registraduría.
NAME_FIXES = {}


def strip(s):
    return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper().strip()


def load_georef():
    """9 díg (dd+mmm+zz+pp) → (mun, puesto, comCode, comNom); 5 díg → mun."""
    by9, muns = {}, {}
    with open(GEOREF, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f, delimiter=';'):
            code = (row.get('CÓDIGO COMPLETO') or '').strip()
            if len(code) != 9:
                continue
            mun = (row.get('MUNICIPIO') or '').strip()
            pue = (row.get('NOMBRE PUESTO') or '').strip()
            comC = (row.get('CÓDIGO COMUNA') or '').strip()
            comN = (row.get('NOMBRE COMUNA') or '').strip()
            if comN.upper() in ('NULL', ''):
                comC, comN = '000', 'NACIONAL'
            by9[code] = (mun, pue, comC or '000', comN or 'NACIONAL')
            muns.setdefault(code[:5], mun)
    return by9, muns


def fmt(x):
    return f'{x:,}'.replace(',', '.')


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    by9, munNames = load_georef()
    print(f'GEOREF: {len(by9)} puestos · {len(munNames)} muns')

    # candidato (dde,par,can) → {meta, votos, mesas[]}
    cands = {}
    n = 0
    with open(SRC, encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f, delimiter=';'):
            if row.get('COD_COR') != '2':
                continue
            can = row['COD_CAN']
            if can in SPECIAL_CAN:
                continue
            try:
                v = int(row['NUM_VOT'] or 0)
            except ValueError:
                v = 0
            if v <= 0:
                continue
            dde = row['COD_DDE'].strip()
            par = row['COD_PAR'].strip()
            dd = dde.zfill(2)
            mm = (row['COD_MME'] or '').strip().zfill(3)
            zz = (row['COD_ZZ'] or '').strip().zfill(2)
            pp = (row['COD_PP'] or '').strip().zfill(2)
            key = (dde, par, can)
            c = cands.get(key)
            if c is None:
                c = cands[key] = {
                    'nombre': strip(row['DES_CAN']) or f'CANDIDATO {can}',
                    'partido': (row['DES_PAR'] or '').strip() or f'PARTIDO {par}',
                    'dd': dd, 'votos': 0, 'mesas': [],
                }
            g = by9.get(f'{dd}{mm}{zz}{pp}')
            munNom = (g[0] if g else munNames.get(f'{dd}{mm}', f'MUN {mm}'))
            pueNom = (g[1] if g else f'PUESTO {zz}-{pp}')
            comC, comN = (g[2], g[3]) if g else ('000', 'NACIONAL')
            c['votos'] += v
            c['mesas'].append({
                'dep': dd, 'depNom': DEP_NAMES.get(dd, f'DEP {dd}'),
                'mun': mm, 'munNom': munNom, 'zon': zz, 'pue': pp, 'pueNom': pueNom,
                'mesa': (row['DES_MS'] or '').strip().zfill(3),
                'com': comC, 'comNom': comN, 'v': v,
            })
            n += 1
    print(f'{n:,} filas mesa-candidato · {len(cands):,} candidatos')

    # Escribir un JSON por candidato + índice
    index = []
    total_bytes = 0
    for (dde, par, can), c in cands.items():
        dd = c['dd']
        slug = f'ASAM2023-{dde}-{par}-{can}'
        nombre = NAME_FIXES.get(slug, c['nombre'])
        depNom = DEP_NAMES.get(dd, f'DEP {dd}')
        data = {
            'nombre': nombre, 'corp': f'ASAMBLEA · {depNom}',
            'circunscripcion': depNom, 'partido': c['partido'],
            'votos': c['votos'], 'mesas': c['mesas'],
        }
        path = os.path.join(OUT_DIR, f'{slug}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        total_bytes += os.path.getsize(path)
        index.append({
            'slug': slug, 'nombre': nombre,
            'corp': f'ASAMBLEA · {depNom} · 2023', 'circunscripcion': depNom,
            'partido': c['partido'], 'votos': c['votos'],
        })

    index.sort(key=lambda x: -x['votos'])
    idx_path = os.path.join(OUT_DIR, 'index-asamblea-2023.json')
    with open(idx_path, 'w', encoding='utf-8') as f:
        json.dump({'v': '2026-07-14', 'eleccion': 'Asamblea Departamental 2023',
                   'candidatos': index}, f, ensure_ascii=False, separators=(',', ':'))

    print(f'→ {len(index):,} JSONs de candidato · {total_bytes/1e6:.0f} MB total')
    print(f'→ index-asamblea-2023.json ({os.path.getsize(idx_path)//1024} KB)')
    print('Top 5:', [(x['nombre'][:24], x['circunscripcion'], fmt(x['votos'])) for x in index[:5]])


if __name__ == '__main__':
    main()
