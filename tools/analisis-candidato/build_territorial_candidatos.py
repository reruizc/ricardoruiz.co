#!/usr/bin/env python3
"""
build_territorial_candidatos.py — genera los JSONs por candidato de las
elecciones territoriales 2015 y 2019 (ASAMBLEA · CONCEJO · JAL) en el MISMO
formato mesa-a-mesa endoso/{slug}.json que consumen analisis-candidato.html,
comparar-candidatos.html y endoso-2026.html, + un índice por elección.

Es la versión parametrizada de build_asamblea_2023.py / build_concejo_2023.py /
build_jal_2023.py (mismas llaves, mismos gotchas), con dos diferencias de fuente:

  · GCS_2011TER: 4=GOBERNACION · 5=ASAMBLEA · 6=ALCALDIA · 7=CONCEJO · 8=JAL
      (JAL adentro). ⚠️ **17 columnas y el orden más raro de todos**: campo EXTRA
      `DES_MM` (nombre de municipio) en la col 8, que corre toda la geografía, y
      **NUM_VOT en la col 12, ANTES de partido y candidato** — al revés que en
      cualquier otro año:
      FUENTE;FEC_ELEC;COD_COR;DES_COR;COD_CIR;DES_CIR;COD_DDE;COD_MME;DES_MM;
      COD_ZZ;COD_PP;DES_MS;NUM_VOT;COD_PAR;DES_PAR;COD_CAN;DES_CAN
  · GCS_2015TER trae las 5 corporaciones INTERCALADAS con códigos propios:
      1=GOBERNACION · 2=ASAMBLEA · 3=ALCALDIA · 4=CONCEJO · 5=JAL  (JAL adentro)
  · GCS_2019TER usa OTROS códigos: 4=GOBERNADOR · 5=ASAMBLEA · 6=ALCALDE · 7=CONCEJO
  · GCS_2019JAL es archivo aparte (COD_COR=5) y con LAS COLUMNAS EN OTRO ORDEN:
      FUENTE;FEC_ELEC;COD_DDE;COD_MME;COD_ZZ;COD_PP;DES_MS;COD_COR;DES_COR;...

Llaves (idénticas a 2023):
  asamblea → (dde, par, can)                circunscripción DEPARTAMENTAL
  concejo  → (dde, mme, par, can)           circunscripción MUNICIPAL
  jal      → (dde, mme, par, can, nombre)   ⚠️ COD_CAN se reinicia por comuna

Memoria (8 GB): streaming — se extrae la corporación con awk, se ordena por
(dde,mme) a un temporal en el scratchpad y se procesa grupo por grupo.

Uso:
  python3 tools/analisis-candidato/build_territorial_candidatos.py asam2015
  python3 tools/analisis-candidato/build_territorial_candidatos.py conc2019
  ... claves: asam2011 asam2015 asam2019 · conc2011 conc2015 conc2019
             jal2011 jal2015 jal2019

Subida a S3 (manual, luz verde del usuario):
  aws s3 cp "Bases de datos/output_asamblea_2015/" \
    "s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/asamblea-2015/" \
    --recursive --content-type "application/json" --cache-control "public, max-age=300"
"""
import csv, hashlib, json, os, re, subprocess, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BD   = os.path.join(ROOT, 'Bases de datos')
GEOREF = os.path.join(BD, 'PUESTOS_GEOREF.csv')
SCRATCH = os.environ.get('SCRATCH_DIR', '/tmp')

# Layout de columnas (0-based tras split(';')). NCOL = mínimo de columnas que
# debe traer la fila para que todos los índices existan.
LAYOUT_TER = dict(COR=2, DDE=6, MME=7, ZZ=8, PP=9, MS=10, PAR=11, DESPAR=12,
                  CAN=13, DESCAN=14, VOT=15, NCOL=16, SORT=('-k7,7', '-k8,8'))
LAYOUT_JAL19 = dict(COR=7, DDE=2, MME=3, ZZ=4, PP=5, MS=6, PAR=11, DESPAR=12,
                    CAN=13, DESCAN=14, VOT=15, NCOL=16, SORT=('-k3,3', '-k4,4'))
# ⚠️ 2011 es el más raro de todos: 17 columnas, un campo EXTRA `DES_MM` (nombre
# del municipio) en la 8 que corre toda la geografía, y sobre todo **NUM_VOT va
# ANTES de partido/candidato** (col 12) — al revés que en cualquier otro año.
LAYOUT_2011 = dict(COR=2, DDE=6, MME=7, ZZ=9, PP=10, MS=11, PAR=13, DESPAR=14,
                   CAN=15, DESCAN=16, VOT=12, NCOL=17, SORT=('-k7,7', '-k8,8'))

CFG = {
    'gob2011':  dict(src='GCS_2011TER.csv', cor='4', layout=LAYOUT_2011, scope='dep',
                     slug='GOB2011', anio='2011', corp='GOBERNACIÓN',
                     dir='gobernacion-2011', eleccion='Gobernación 2011'),
    'alc2011':  dict(src='GCS_2011TER.csv', cor='6', layout=LAYOUT_2011, scope='mun',
                     slug='ALC2011', anio='2011', corp='ALCALDÍA',
                     dir='alcaldia-2011', eleccion='Alcaldía 2011'),
    'gob2015':  dict(src='GCS_2015TER.csv', cor='1', layout=LAYOUT_TER, scope='dep',
                     slug='GOB2015', anio='2015', corp='GOBERNACIÓN',
                     dir='gobernacion-2015', eleccion='Gobernación 2015'),
    'alc2015':  dict(src='GCS_2015TER.csv', cor='3', layout=LAYOUT_TER, scope='mun',
                     slug='ALC2015', anio='2015', corp='ALCALDÍA',
                     dir='alcaldia-2015', eleccion='Alcaldía 2015'),
    'gob2019':  dict(src='GCS_2019TER.csv', cor='4', layout=LAYOUT_TER, scope='dep',
                     slug='GOB2019', anio='2019', corp='GOBERNACIÓN',
                     dir='gobernacion-2019', eleccion='Gobernación 2019'),
    'alc2019':  dict(src='GCS_2019TER.csv', cor='6', layout=LAYOUT_TER, scope='mun',
                     slug='ALC2019', anio='2019', corp='ALCALDÍA',
                     dir='alcaldia-2019', eleccion='Alcaldía 2019'),
    'gob2023':  dict(src='GCS_2023TER.csv', cor='1', layout=LAYOUT_TER, scope='dep',
                     slug='GOB2023', anio='2023', corp='GOBERNACIÓN',
                     dir='gobernacion-2023', eleccion='Gobernación 2023'),
    'alc2023':  dict(src='GCS_2023TER.csv', cor='3', layout=LAYOUT_TER, scope='mun',
                     slug='ALC2023', anio='2023', corp='ALCALDÍA',
                     dir='alcaldia-2023', eleccion='Alcaldía 2023'),
    'asam2011': dict(src='GCS_2011TER.csv', cor='5', layout=LAYOUT_2011, scope='dep',
                     slug='ASAM2011', anio='2011', corp='ASAMBLEA',
                     dir='asamblea-2011', eleccion='Asamblea Departamental 2011'),
    'conc2011': dict(src='GCS_2011TER.csv', cor='7', layout=LAYOUT_2011, scope='mun',
                     slug='CONC2011', anio='2011', corp='CONCEJO',
                     dir='concejo-2011', eleccion='Concejo Municipal 2011'),
    'jal2011':  dict(src='GCS_2011TER.csv', cor='8', layout=LAYOUT_2011, scope='jal',
                     slug='JAL2011', anio='2011', corp='JAL',
                     dir='jal-2011', eleccion='JAL (Ediles) 2011'),
    'asam2015': dict(src='GCS_2015TER.csv', cor='2', layout=LAYOUT_TER, scope='dep',
                     slug='ASAM2015', anio='2015', corp='ASAMBLEA',
                     dir='asamblea-2015', eleccion='Asamblea Departamental 2015'),
    'asam2019': dict(src='GCS_2019TER.csv', cor='5', layout=LAYOUT_TER, scope='dep',
                     slug='ASAM2019', anio='2019', corp='ASAMBLEA',
                     dir='asamblea-2019', eleccion='Asamblea Departamental 2019'),
    'conc2015': dict(src='GCS_2015TER.csv', cor='4', layout=LAYOUT_TER, scope='mun',
                     slug='CONC2015', anio='2015', corp='CONCEJO',
                     dir='concejo-2015', eleccion='Concejo Municipal 2015'),
    'conc2019': dict(src='GCS_2019TER.csv', cor='7', layout=LAYOUT_TER, scope='mun',
                     slug='CONC2019', anio='2019', corp='CONCEJO',
                     dir='concejo-2019', eleccion='Concejo Municipal 2019'),
    'jal2015':  dict(src='GCS_2015TER.csv', cor='5', layout=LAYOUT_TER, scope='jal',
                     slug='JAL2015', anio='2015', corp='JAL',
                     dir='jal-2015', eleccion='JAL (Ediles) 2015'),
    'jal2019':  dict(src='GCS_2019JAL.csv', cor='5', layout=LAYOUT_JAL19, scope='jal',
                     slug='JAL2019', anio='2019', corp='JAL',
                     dir='jal-2019', eleccion='JAL (Ediles) 2019'),
}

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
SPECIAL_CAN = {'0', '996', '997', '998', '999'}


def strip(s):
    return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper().strip()


def clean_com(comN):
    """'01COMUNA 1 POPULAR' → 'COMUNA 1 POPULAR' · '16USAQUEN' → 'USAQUEN'."""
    c = re.sub(r'^\d+', '', (comN or '').strip()).strip()
    return c or 'LOCAL'


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


def ensure_sorted(cfg, sorted_path):
    """Extrae la corporación y ordena por (dde,mme) a un temporal. Idempotente."""
    if os.path.exists(sorted_path) and os.path.getsize(sorted_path) > 0:
        print(f'· usando temporal ya ordenado: {sorted_path}')
        return
    os.makedirs(SCRATCH, exist_ok=True)
    src = os.path.join(BD, 'FINAL SUBIDA GCS', cfg['src'])
    cor_field = cfg['layout']['COR'] + 1   # awk es 1-based
    print(f"· extrayendo COD_COR={cfg['cor']} de {cfg['src']} y ordenando…")
    awk = ["awk", "-F;", f'NR>1 && ${cor_field}=="{cfg["cor"]}"', src]
    with open(sorted_path, 'wb') as out:
        p1 = subprocess.Popen(awk, stdout=subprocess.PIPE)
        p2 = subprocess.Popen(
            ["sort", "-t;", *cfg['layout']['SORT'], "-S", "1G"],
            stdin=p1.stdout, stdout=out,
            env={**os.environ, "LC_ALL": "C", "TMPDIR": SCRATCH})
        p1.stdout.close()
        p2.communicate()
        if p2.returncode != 0:
            sys.exit('sort falló')
    print(f'· temporal listo: {os.path.getsize(sorted_path)/1e9:.2f} GB')


def fmt(x):
    return f'{x:,}'.replace(',', '.')


def flush_group(cfg, cands, by9, munNames, index, out_dir):
    anio, scope = cfg['anio'], cfg['scope']
    for key, c in cands.items():
        if scope == 'dep':
            dde, par, can = key
            mme = None
        elif scope == 'mun':
            dde, mme, par, can = key
        else:
            dde, mme, par, can, nkey = key
        dd = dde.zfill(2)
        depNom = DEP_NAMES.get(dd, f'DEP {dd}')

        if scope == 'dep':
            slug = f"{cfg['slug']}-{dde}-{par}-{can}"
            corp = f"{cfg['corp']} · {depNom}"
            circ = depNom
            corpIdx = f"{cfg['corp']} · {depNom} · {anio}"
        else:
            mm = mme.zfill(3)
            munNom = 'BOGOTÁ D.C.' if dd == '16' else munNames.get(f'{dd}{mm}', c['munNom'] or f'MUN {mm}')
            if scope == 'mun':
                slug = f"{cfg['slug']}-{dde}-{mme}-{par}-{can}"
                corp = f"{cfg['corp']} · {munNom}"
                circ = munNom if munNom == depNom else f'{munNom} ({depNom})'
                corpIdx = f"{cfg['corp']} · {munNom} · {anio}"
            else:
                comNom = 'LOCAL'
                if c['comVotes']:
                    comNom = clean_com(max(c['comVotes'].items(), key=lambda kv: kv[1])[0])
                h6 = hashlib.md5(nkey.encode('utf-8')).hexdigest()[:6]
                slug = f"{cfg['slug']}-{dde}-{mme}-{par}-{can}-{h6}"
                corp = f'JAL · {comNom} · {munNom}'
                circ = f'{comNom} · {munNom}'
                corpIdx = f'JAL · {comNom} · {munNom} · {anio}'

        mesas = []
        for (mmx, zz, pp, ms, v) in c['mesas']:
            mm2 = (mme if scope != 'dep' else mmx).zfill(3)
            g = by9.get(f'{dd}{mm2}{zz}{pp}')
            if scope == 'dep':
                mNom = g[0] if g else munNames.get(f'{dd}{mm2}', f'MUN {mm2}')
            else:
                mNom = munNom
            pueNom = g[1] if g else f'PUESTO {zz}-{pp}'
            comC, comN = (g[2], g[3]) if g else ('000', 'NACIONAL')
            mesas.append({
                'dep': dd, 'depNom': depNom, 'mun': mm2, 'munNom': mNom,
                'zon': zz, 'pue': pp, 'pueNom': pueNom, 'mesa': ms,
                'com': comC, 'comNom': comN, 'v': v,
            })
        data = {
            'nombre': c['nombre'], 'corp': corp, 'circunscripcion': circ,
            'partido': c['partido'], 'votos': c['votos'], 'mesas': mesas,
        }
        with open(os.path.join(out_dir, f'{slug}.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        index.append({
            'slug': slug, 'nombre': c['nombre'], 'corp': corpIdx,
            'circunscripcion': circ, 'partido': c['partido'], 'votos': c['votos'],
        })


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in CFG:
        sys.exit(f'uso: build_territorial_candidatos.py <{"|".join(CFG)}>')
    clave = sys.argv[1]
    cfg = CFG[clave]
    L = cfg['layout']
    scope = cfg['scope']
    out_dir = os.path.join(BD, f"output_{cfg['dir'].replace('-', '_')}")
    sorted_path = os.path.join(SCRATCH, f'{clave}_sorted.csv')

    os.makedirs(out_dir, exist_ok=True)
    by9, munNames = load_georef()
    print(f'GEOREF: {len(by9)} puestos · {len(munNames)} muns')
    ensure_sorted(cfg, sorted_path)

    index = []
    cands = {}
    cur_group = None
    n_rows = 0
    with open(sorted_path, encoding='utf-8', errors='replace', newline='') as f:
        for row in csv.reader(f, delimiter=';'):
            if len(row) < L['NCOL']:
                continue
            can = row[L['CAN']].strip()
            if can in SPECIAL_CAN:
                continue
            try:
                v = int(row[L['VOT']] or 0)
            except ValueError:
                v = 0
            if v <= 0:
                continue
            dde = row[L['DDE']].strip()
            mme = row[L['MME']].strip()
            grp = dde if scope == 'dep' else (dde, mme)
            if grp != cur_group:
                if cur_group is not None:
                    flush_group(cfg, cands, by9, munNames, index, out_dir)
                    cands = {}
                cur_group = grp
            par = row[L['PAR']].strip()
            if scope == 'dep':
                key = (dde, par, can)
            elif scope == 'mun':
                key = (dde, mme, par, can)
            else:
                nombre = strip(row[L['DESCAN']]) or f'CANDIDATO {can}'
                key = (dde, mme, par, can, nombre)
            zz = (row[L['ZZ']] or '').strip().zfill(2)
            pp = (row[L['PP']] or '').strip().zfill(2)
            ms = (row[L['MS']] or '').strip().zfill(3)
            c = cands.get(key)
            if c is None:
                c = cands[key] = {
                    'nombre': strip(row[L['DESCAN']]) or f'CANDIDATO {can}',
                    'partido': (row[L['DESPAR']] or '').strip() or f'PARTIDO {par}',
                    'munNom': None, 'votos': 0, 'mesas': [],
                }
                if scope == 'jal':
                    c['comVotes'] = {}
            dd = dde.zfill(2); mm = mme.zfill(3)
            gg = by9.get(f'{dd}{mm}{zz}{pp}')
            if gg:
                if c['munNom'] is None:
                    c['munNom'] = gg[0]
                if scope == 'jal':
                    c['comVotes'][gg[3]] = c['comVotes'].get(gg[3], 0) + v
            c['votos'] += v
            c['mesas'].append((mme, zz, pp, ms, v))
            n_rows += 1
    if cur_group is not None:
        flush_group(cfg, cands, by9, munNames, index, out_dir)

    index.sort(key=lambda x: -x['votos'])
    idx_path = os.path.join(out_dir, f"index-{cfg['dir']}.json")
    with open(idx_path, 'w', encoding='utf-8') as f:
        json.dump({'v': '2026-07-30', 'eleccion': cfg['eleccion'],
                   'candidatos': index}, f, ensure_ascii=False, separators=(',', ':'))

    print(f'{n_rows:,} filas mesa-candidato · {len(index):,} candidatos')
    print(f'→ {idx_path} ({os.path.getsize(idx_path)//1024} KB)')
    print('Top 5:', [(x['nombre'][:22], x['circunscripcion'][:24], fmt(x['votos'])) for x in index[:5]])


if __name__ == '__main__':
    main()
