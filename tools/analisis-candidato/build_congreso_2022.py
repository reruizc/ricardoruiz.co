#!/usr/bin/env python3
"""
build_congreso_2022.py — genera los JSONs por candidato del CONGRESO 2022-2026
(Senado + Cámara) en el MISMO formato mesa-a-mesa de endoso/{slug}.json que
consume analisis-candidato.html, más un index-congreso-2022.json.

Gemelo de build_congreso_2018.py. ⚠️ OJO — 2022 NO usa los mismos códigos de
circunscripción que 2018 (verificado sobre el CSV):

    Circunscripción        2018 (COR,CIR)   2022 (COR,CIR)
    Senado nacional        (1,0)            (1,1)
    Senado indígena        (1,4)            (1,6)
    Cámara territorial     (2,1)            (2,2)
    Cámara afro            (2,5)            (2,5)
    Cámara indígena        (2,4)            (2,6)
    Cámara CITREP (paz)    —                (2,7)   ← nueva en 2022
    Cámara internacional   —                (2,0)   ← 2 curules exterior

Alcances (igual que 2018): los NACIONALES (Senado nac/indígena, Cámara afro/
indígena) recogen voto en todo el país → llave SIN depto, mapa de los 33 deptos.
La Cámara TERRITORIAL compite en UN depto → llave CON depto, mapa de un depto.

CITREP (curules de paz) e Internacional (exterior) también entran, keyeados
NACIONAL: en CITREP cada candidato es una organización (COD_PAR único) cuyo
distrito abarca varios departamentos → (COD_PAR, COD_CAN) los agrega en un solo
JSON con prefijo CT; Internacional es exterior (COD_DDE=88) con prefijo CE.

Fuentes (locales):
  Bases de datos/FINAL SUBIDA GCS/GCS_2022CON.csv   (1,2 GB)
  Bases de datos/PUESTOS_GEOREF.csv                 (nombres mun/puesto/comuna)

Salida (gitignored, ~1 GB):
  Bases de datos/output_congreso_2022/
    index-congreso-2022.json
    CON2022-S-{par}-{can}.json          senado nacional
    CON2022-SI-{par}-{can}.json         senado indígena
    CON2022-C-{dde}-{par}-{can}.json    cámara territorial
    CON2022-CA-{par}-{can}.json         cámara afro
    CON2022-CI-{par}-{can}.json         cámara indígena
    CON2022-CT-{dde}-{par}-{can}.json   cámara CITREP (paz)
    CON2022-CE-{par}-{can}.json         cámara internacional (exterior)

Subida a S3 (manual, pedir luz verde):
  aws s3 cp "Bases de datos/output_congreso_2022/" \\
    "s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/congreso-2022/" \\
    --recursive --content-type "application/json" --cache-control "public, max-age=300"

Uso:
  python3 tools/analisis-candidato/build_congreso_2022.py [--limit N]
"""
import csv, json, os, sys, unicodedata

csv.field_size_limit(10 ** 7)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BD = os.path.join(ROOT, 'Bases de datos')
SRC = os.path.join(BD, 'FINAL SUBIDA GCS', 'GCS_2022CON.csv')
GEOREF = os.path.join(BD, 'PUESTOS_GEOREF.csv')
OUT_DIR = os.path.join(BD, 'output_congreso_2022')

DEP_NAMES = {
    '01': 'ANTIOQUIA', '03': 'ATLÁNTICO', '05': 'BOLÍVAR', '07': 'BOYACÁ',
    '09': 'CALDAS', '11': 'CAUCA', '12': 'CESAR', '13': 'CÓRDOBA',
    '15': 'CUNDINAMARCA', '17': 'CHOCÓ', '19': 'HUILA', '21': 'MAGDALENA',
    '23': 'NARIÑO', '24': 'RISARALDA', '25': 'NORTE DE SANTANDER',
    '26': 'QUINDÍO', '27': 'SANTANDER', '28': 'SUCRE', '29': 'TOLIMA',
    '31': 'VALLE DEL CAUCA', '40': 'ARAUCA', '44': 'CAQUETÁ', '46': 'CASANARE',
    '48': 'LA GUAJIRA', '50': 'GUAINÍA', '52': 'META', '54': 'GUAVIARE',
    '56': 'SAN ANDRÉS', '60': 'AMAZONAS', '64': 'PUTUMAYO', '68': 'VAUPÉS',
    '72': 'VICHADA', '16': 'BOGOTÁ D.C.', '88': 'EXTERIOR',
}
SPECIAL_CAN = {'0', '996', '997', '998', '999'}

# (COD_COR, COD_CIR) → (prefijo de slug, etiqueta de corporación, ¿nacional?)
# Códigos de 2022 (distintos a 2018 — ver docstring).
SCOPES = {
    ('1', '1'): ('S',  'SENADO',            True),
    ('1', '6'): ('SI', 'SENADO INDÍGENA',   True),
    ('2', '2'): ('C',  'CÁMARA',            False),
    ('2', '5'): ('CA', 'CÁMARA AFRO',       True),
    ('2', '6'): ('CI', 'CÁMARA INDÍGENA',   True),
    # Internacional (exterior): 2 curules, voto de consulados (COD_DDE=88) →
    # nacional, una sola llave por candidato.
    ('2', '0'): ('CE', 'CÁMARA INTERNACIONAL', True),
    # CITREP (curules de paz, COD_CIR=7): 16 circunscripciones especiales. En el
    # crudo, cada candidato = una ORGANIZACIÓN (COD_PAR único, p.ej. Jorge Tovar
    # = 428 'Paz es Vida'), COD_CAN es un marcador constante (501/502), y sus
    # votos se reparten en VARIOS COD_DDE (los deptos que cubre su distrito:
    # Tovar en Cesar+Magdalena+Guajira, Salazar en Cauca+Nariño+Valle). Por eso
    # se keyea NACIONAL por (COD_PAR, COD_CAN): agrega el distrito en un solo JSON
    # y el mapa colorea justo los deptos donde compitió.
    ('2', '7'): ('CT', 'CÁMARA · CITREP',   True),
}


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


def main():
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None
    os.makedirs(OUT_DIR, exist_ok=True)
    by9, munNames = load_georef()
    print(f'GEOREF: {len(by9)} puestos · {len(munNames)} muns', flush=True)

    cands = {}
    n = 0
    with open(SRC, encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f, delimiter=';'):
            scope = SCOPES.get((row.get('COD_COR'), row.get('COD_CIR')))
            if not scope:
                continue
            pref, corp, nacional = scope
            can = (row.get('COD_CAN') or '').strip()
            if can in SPECIAL_CAN:
                continue
            try:
                v = int(row['NUM_VOT'] or 0)
            except ValueError:
                v = 0
            if v <= 0:
                continue
            dde = (row.get('COD_DDE') or '').strip()
            par = (row.get('COD_PAR') or '').strip()
            dd = dde.zfill(2)
            mm = (row.get('COD_MME') or '').strip().zfill(3)
            zz = (row.get('COD_ZZ') or '').strip().zfill(2)
            pp = (row.get('COD_PP') or '').strip().zfill(2)
            # nacional → la llave NO lleva depto (el candidato recoge voto en todo el país)
            key = (pref, '', par, can) if nacional else (pref, dde, par, can)
            c = cands.get(key)
            if c is None:
                c = cands[key] = {
                    'nombre': strip(row.get('DES_CAN')) or f'CANDIDATO {can}',
                    'partido': (row.get('DES_PAR') or '').strip() or f'PARTIDO {par}',
                    'corp': corp, 'nacional': nacional, 'dd': dd,
                    'votos': 0, 'mesas': [],
                }
            g = by9.get(f'{dd}{mm}{zz}{pp}')
            munNom = (g[0] if g else munNames.get(f'{dd}{mm}', f'MUN {mm}'))
            pueNom = (g[1] if g else f'PUESTO {zz}-{pp}')
            comC, comN = (g[2], g[3]) if g else ('000', 'NACIONAL')
            c['votos'] += v
            c['mesas'].append({
                'dep': dd, 'depNom': DEP_NAMES.get(dd, f'DEP {dd}'),
                'mun': mm, 'munNom': munNom, 'zon': zz, 'pue': pp, 'pueNom': pueNom,
                'mesa': (row.get('DES_MS') or '').strip().zfill(3),
                'com': comC, 'comNom': comN, 'v': v,
            })
            n += 1
            if n % 2_000_000 == 0:
                print(f'  …{n:,} filas · {len(cands):,} candidatos', flush=True)
            if limit and n >= limit:
                break
    print(f'{n:,} filas mesa-candidato · {len(cands):,} candidatos', flush=True)

    index = []
    total_bytes = 0
    for (pref, dde, par, can), c in cands.items():
        slug = f'CON2022-{pref}-{par}-{can}' if c['nacional'] else f'CON2022-{pref}-{dde}-{par}-{can}'
        depNom = DEP_NAMES.get(c['dd'], f'DEP {c["dd"]}')
        circ = 'NACIONAL' if c['nacional'] else depNom
        corp_full = c['corp'] if c['nacional'] else f'{c["corp"]} · {depNom}'
        data = {
            'nombre': c['nombre'], 'corp': corp_full,
            'circunscripcion': circ, 'partido': c['partido'],
            'votos': c['votos'], 'mesas': c['mesas'],
        }
        path = os.path.join(OUT_DIR, f'{slug}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        total_bytes += os.path.getsize(path)
        index.append({
            'slug': slug, 'nombre': c['nombre'],
            'corp': f'{corp_full} · 2022', 'circunscripcion': circ,
            'partido': c['partido'], 'votos': c['votos'],
        })

    index.sort(key=lambda x: -x['votos'])
    idx_path = os.path.join(OUT_DIR, 'index-congreso-2022.json')
    with open(idx_path, 'w', encoding='utf-8') as f:
        json.dump({'v': '2022-2026', 'n': len(index), 'candidatos': index},
                  f, ensure_ascii=False, separators=(',', ':'))
    print(f'{len(index):,} candidatos · {total_bytes/1024/1024:.0f} MB → {OUT_DIR}', flush=True)
    print(f'índice → {idx_path}', flush=True)
    for t in index[:8]:
        print(f'  {t["votos"]:>9,}  {t["nombre"][:38]:38s} {t["corp"]}')


if __name__ == '__main__':
    main()
