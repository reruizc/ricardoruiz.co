#!/usr/bin/env python3
"""
build_pres_2018.py — genera los JSONs mesa-a-mesa de la PRESIDENCIAL 2018
(1ª y 2ª vuelta) en formato endoso/{slug}.json + index-pres-2018.json, para el
buscador de analisis-candidato.html (fuente regular de cand-index.js, NO el
modelo por-persona de 2026).

Fuentes:
  Bases de datos/FINAL SUBIDA GCS/GCS_2018PRES1V.csv  (COD_COR=3 · ~1M filas)
  Bases de datos/FINAL SUBIDA GCS/GCS_2018PRES2V.csv

⚠️ En estos archivos los especiales van con COD_CAN 96/97/98 (no 996-999) y
COD_PAR 996/997/998 → se filtra por COD_PAR ≥ 996.

Slugs: PRES2018-1V-{par}-{can} · PRES2018-2V-{par}-{can}
Circunscripción NACIONAL (mapa de los 33 deptos, como Senado).

Validación (oficial): Duque 1V 7.616.857 · Petro 1V 4.855.069 · Fajardo 4.602.916.

Salida (gitignored): Bases de datos/output_pres_2018/
Subida a S3 (manual, luz verde):
  aws s3 cp "Bases de datos/output_pres_2018/" \
    "s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/pres-2018/" \
    --recursive --content-type "application/json" --cache-control "public, max-age=300"
"""
import csv, json, os, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BD   = os.path.join(ROOT, 'Bases de datos')
GEOREF = os.path.join(BD, 'PUESTOS_GEOREF.csv')
OUT_DIR = os.path.join(BD, 'output_pres_2018')

DEP_NAMES = {
    '01': 'ANTIOQUIA', '03': 'ATLÁNTICO', '05': 'BOLÍVAR', '07': 'BOYACÁ',
    '09': 'CALDAS', '11': 'CAUCA', '12': 'CESAR', '13': 'CÓRDOBA',
    '15': 'CUNDINAMARCA', '17': 'CHOCÓ', '19': 'HUILA', '21': 'MAGDALENA',
    '23': 'NARIÑO', '24': 'RISARALDA', '25': 'NORTE DE SANTANDER',
    '26': 'QUINDÍO', '27': 'SANTANDER', '28': 'SUCRE', '29': 'TOLIMA',
    '31': 'VALLE DEL CAUCA', '40': 'ARAUCA', '44': 'CAQUETÁ', '46': 'CASANARE',
    '48': 'LA GUAJIRA', '50': 'GUAINÍA', '52': 'META', '54': 'GUAVIARE',
    '56': 'SAN ANDRÉS', '60': 'AMAZONAS', '64': 'PUTUMAYO', '68': 'VAUPÉS',
    '72': 'VICHADA', '88': 'EXTERIOR', '16': 'BOGOTÁ D.C.',
}


def strip(s):
    return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper().strip()


def load_georef():
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


def procesar(vuelta, src, by9, munNames, index):
    cands = {}
    n = 0
    with open(src, encoding='utf-8-sig', errors='replace', newline='') as f:
        for row in csv.reader(f, delimiter=';'):
            if len(row) < 16 or row[0] == 'FUENTE':
                continue
            par = row[11].strip()
            try:
                if int(par) >= 996:      # blanco / nulos / no marcados
                    continue
            except ValueError:
                pass
            try:
                v = int(row[15] or 0)
            except ValueError:
                v = 0
            if v <= 0:
                continue
            can = row[13].strip()
            key = (par, can)
            c = cands.get(key)
            if c is None:
                c = cands[key] = {
                    'nombre': strip(row[14]) or f'CANDIDATO {can}',
                    'partido': (row[12] or '').strip() or f'PARTIDO {par}',
                    'votos': 0, 'mesas': [],
                }
            dd = row[6].strip().zfill(2)
            mm = row[7].strip().zfill(3)
            zz = (row[8] or '').strip().zfill(2)
            pp = (row[9] or '').strip().zfill(2)
            ms = (row[10] or '').strip().zfill(3)
            c['votos'] += v
            c['mesas'].append((dd, mm, zz, pp, ms, v))
            n += 1
    print(f'  {vuelta}: {n:,} filas · {len(cands)} candidatos')

    for (par, can), c in cands.items():
        mesas = []
        for (dd, mm, zz, pp, ms, v) in c['mesas']:
            g = by9.get(f'{dd}{mm}{zz}{pp}')
            munNom = g[0] if g else munNames.get(f'{dd}{mm}', f'MUN {mm}')
            pueNom = g[1] if g else f'PUESTO {zz}-{pp}'
            comC, comN = (g[2], g[3]) if g else ('000', 'NACIONAL')
            mesas.append({
                'dep': dd, 'depNom': DEP_NAMES.get(dd, f'DEP {dd}'),
                'mun': mm, 'munNom': munNom, 'zon': zz, 'pue': pp,
                'pueNom': pueNom, 'mesa': ms, 'com': comC, 'comNom': comN, 'v': v,
            })
        slug = f'PRES2018-{vuelta}-{par}-{can}'
        corp = f'PRESIDENCIA {vuelta}'
        data = {
            'nombre': c['nombre'], 'corp': corp, 'circunscripcion': 'NACIONAL',
            'partido': c['partido'], 'votos': c['votos'], 'mesas': mesas,
        }
        with open(os.path.join(OUT_DIR, f'{slug}.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        index.append({
            'slug': slug, 'nombre': c['nombre'],
            'corp': f'PRESIDENCIA {vuelta} · 2018', 'circunscripcion': 'NACIONAL',
            'partido': c['partido'], 'votos': c['votos'],
        })


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    by9, munNames = load_georef()
    print(f'GEOREF: {len(by9)} puestos · {len(munNames)} muns')
    index = []
    procesar('1V', os.path.join(BD, 'FINAL SUBIDA GCS', 'GCS_2018PRES1V.csv'), by9, munNames, index)
    procesar('2V', os.path.join(BD, 'FINAL SUBIDA GCS', 'GCS_2018PRES2V.csv'), by9, munNames, index)

    index.sort(key=lambda x: -x['votos'])
    idx_path = os.path.join(OUT_DIR, 'index-pres-2018.json')
    with open(idx_path, 'w', encoding='utf-8') as f:
        json.dump({'v': '2026-07-30', 'eleccion': 'Presidencia 2018 (1V + 2V)',
                   'candidatos': index}, f, ensure_ascii=False, separators=(',', ':'))
    print(f'→ {len(index)} JSONs · index-pres-2018.json ({os.path.getsize(idx_path)//1024} KB)')
    print('Top 5:', [(x['nombre'][:24], x['corp'], fmt(x['votos'])) for x in index[:5]])


if __name__ == '__main__':
    main()
