#!/usr/bin/env python3
"""
build_presidenciales.py — genera los JSONs por candidato presidencial (1V + 2V)
en el MISMO formato mesa-a-mesa de endoso/{slug}.json que consume
analisis-candidato.html, más un index-presidencial.json con el agrupador
por persona (para la barra de histórico electoral).

Fuentes (locales, no tocan S3):
  Bases de datos/nuevos archivos 1v 2026/PRECONTEO_1V_2026_MESA_con_Claudia.csv
  Bases de datos/output_2v/PRECONTEO_2V_2026_MESA.csv
  Bases de datos/PUESTOS_GEOREF.csv          (nombres dep/mun/puesto/comuna por código 9 díg)

Salida:
  Bases de datos/output_presidencial_endoso/
    index-presidencial.json
    PRES1V_<SLUG>.json  × 13
    PRES2V_<SLUG>.json  × 2   (Cepeda · Abelardo)

Subida a S3 (manual, pedir luz verde):
  aws s3 cp "Bases de datos/output_presidencial_endoso/" \
    "s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/presidencial/" \
    --recursive --content-type "application/json" --cache-control "public, max-age=300"
"""
import csv, json, os, sys, unicodedata, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BD   = os.path.join(ROOT, 'Bases de datos')
SRC_1V  = os.path.join(BD, 'nuevos archivos 1v 2026', 'PRECONTEO_1V_2026_MESA_con_Claudia.csv')
SRC_2V  = os.path.join(BD, 'output_2v', 'PRECONTEO_2V_2026_MESA.csv')
GEOREF  = os.path.join(BD, 'PUESTOS_GEOREF.csv')
OUT_DIR = os.path.join(BD, 'output_presidencial_endoso')
ENDOSO_INDEX_URL = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/endoso/index.json'
FOTO_BASE = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/Fotos-presidenciales'

# ── Personas: columna del CSV 1V → identidad completa ─────────────────────
# ideol: 0 = izquierda … 100 = derecha (posición del thumb en el espectro).
# foto: archivo en Fotos-presidenciales/ (los 6 grandes existen en S3;
#       el resto queda null → cae al placeholder / carpeta fotos-candidatos).
PERSONAS = [
    # (col CSV 1V,                  persona,        nombre completo,                 partido,                                ideol, foto)
    ('Iván Cepeda',                 'cepeda',       'IVÁN CEPEDA CASTRO',            'PACTO HISTÓRICO',                          8, 'cepeda.jpg'),
    ('Abelardo De La Espriella',    'abelardo',     'ABELARDO DE LA ESPRIELLA',      'DEFENSORES DE LA PATRIA (INDEPENDIENTE)', 95, 'espriella.jpg'),
    ('Paloma Valencia',             'paloma',       'PALOMA VALENCIA LASERNA',       'CENTRO DEMOCRÁTICO',                      88, 'valencia.jpg'),
    ('Sergio Fajardo',              'fajardo',      'SERGIO FAJARDO VALDERRAMA',     'COALICIÓN DE CENTRO',                     50, 'fajardo.jpg'),
    ('Claudia López',               'claudia',      'CLAUDIA LÓPEZ HERNÁNDEZ',       'CENTRO / CENTROIZQUIERDA URBANA',         42, 'lopez.jpg'),
    ('Roy Barreras',                'roy',          'ROY BARRERAS MONTEALEGRE',      'FRENTE POR LA VIDA',                      35, 'barreras.jpg'),
    ('Santiago Botero',             'botero',       'SANTIAGO BOTERO',               'INDEPENDIENTE',                           70, None),
    ('Mauricio Lizcano',            'lizcano',      'MAURICIO LIZCANO',              'INDEPENDIENTE',                           55, None),
    ('Miguel Uribe',                'miguel-uribe', 'MIGUEL URIBE',                  'INDEPENDIENTE',                           85, None),
    ('Sondra Macollins',            'macollins',    'SONDRA MACOLLINS',              'INDEPENDIENTE',                           50, None),
    ('Carlos Caicedo',              'caicedo',      'CARLOS CAICEDO OMAR',           'FUERZA CIUDADANA',                        25, None),
    ('Gustavo Matamoros',           'matamoros',    'GUSTAVO MATAMOROS',             'INDEPENDIENTE',                           75, None),
    ('Gilberto Murillo',            'murillo',      'LUIS GILBERTO MURILLO',         'INDEPENDIENTE',                           45, None),
]

# 2V: NOM_CAN del CSV → persona
CAND_2V = {'IVAN CEPEDA CASTRO': 'cepeda', 'ABELARDO DE LA ESPRIELLA': 'abelardo'}
PRESIDENTE = 'abelardo'   # ganador 2V → puntaje 100 dorado en el frontend

def norm(s):
    return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper().strip()

def slug_of(nombre):
    return norm(nombre).replace(' ', '_').replace("'", '')

# ── GEOREF: nombres por código ─────────────────────────────────────────────
def load_georef():
    """9 díg (dd+mmm+zz+pp) → (dep, mun, puesto, comCode, comNom). También dd→dep y dd+mmm→mun."""
    by9, deps, muns = {}, {}, {}
    with open(GEOREF, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f, delimiter=';'):
            code = (row.get('CÓDIGO COMPLETO') or '').strip()
            if len(code) != 9:
                continue
            dep = (row.get('DEPARTAMENTO') or '').strip()
            mun = (row.get('MUNICIPIO') or '').strip()
            pue = (row.get('NOMBRE PUESTO') or '').strip()
            comC = (row.get('CÓDIGO COMUNA') or '').strip()
            comN = (row.get('NOMBRE COMUNA') or '').strip()
            if comN.upper() in ('NULL', ''):
                comC, comN = '000', 'NACIONAL'
            by9[code] = (dep, mun, pue, comC or '000', comN or 'NACIONAL')
            deps.setdefault(code[:2], dep)
            muns.setdefault(code[:5], mun)
    return by9, deps, muns

def fmt_num(x):
    return f'{x:,}'.replace(',', '.')

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    by9, depNames, munNames = load_georef()
    print(f'GEOREF: {len(by9)} puestos · {len(depNames)} deptos · {len(munNames)} muns')

    # ── 1V: acumular mesas por candidato ──────────────────────────────────
    cand_cols = [p[0] for p in PERSONAS]
    mesas_1v = {p[1]: [] for p in PERSONAS}
    tot_1v   = {p[1]: 0 for p in PERSONAS}
    n_rows = 0
    with open(SRC_1V, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            n_rows += 1
            dd = row['cod_departamento'].strip()
            mm = row['cod_municipio'].strip()
            zz = row['zona'].strip()
            pp = row['puesto'].strip()
            mesa = row['num_mesa'].strip()
            key9 = f'{dd}{mm}{zz}{pp}' if len(dd) == 2 and len(mm) == 3 else None
            g = by9.get(key9) if key9 else None
            if g:
                depNom, munNom, pueNom, comC, comN = g
            else:
                depNom = depNames.get(dd, 'EXTERIOR - CONSULADOS' if dd == '88' else f'DEP {dd}')
                munNom = munNames.get(f'{dd}{mm}', f'MUN {mm}')
                pueNom, comC, comN = f'PUESTO {zz}-{pp}', '000', 'NACIONAL'
            for col, persona, *_ in [(p[0], p[1]) for p in PERSONAS]:
                try:
                    v = int(row[col] or 0)
                except ValueError:
                    v = 0
                if v > 0:
                    tot_1v[persona] += v
                    mesas_1v[persona].append({
                        'dep': dd, 'depNom': depNom, 'mun': mm, 'munNom': munNom,
                        'zon': zz, 'pue': pp, 'pueNom': pueNom,
                        'mesa': mesa, 'com': comC, 'comNom': comN, 'v': v,
                    })
    print(f'1V: {n_rows} mesas leídas')
    for _, persona, nombre, *_ in [(p[0], p[1], p[2]) for p in PERSONAS]:
        print(f'  {nombre:32s} {fmt_num(tot_1v[persona]):>12s} votos · {fmt_num(len(mesas_1v[persona]))} mesas')

    # ── 2V: acumular mesas Cepeda/Abelardo ────────────────────────────────
    mesas_2v = {p: [] for p in CAND_2V.values()}
    tot_2v   = {p: 0 for p in CAND_2V.values()}
    with open(SRC_2V, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            persona = CAND_2V.get(norm(row['NOM_CAN']))
            if not persona:
                continue
            try:
                v = int(row['VOTOS'] or 0)
            except ValueError:
                v = 0
            if v <= 0:
                continue
            dd = row['COD_DEP'].strip().zfill(2)
            mm = row['COD_MUN'].strip().zfill(3)
            zz = row['COD_ZONA'].strip().zfill(2)
            pp = row['COD_PUESTO'].strip().zfill(2)
            g = by9.get(f'{dd}{mm}{zz}{pp}')
            comC, comN = (g[3], g[4]) if g else ('000', 'NACIONAL')
            tot_2v[persona] += v
            mesas_2v[persona].append({
                'dep': dd, 'depNom': (row['NOM_DEP'] or '').strip() or (g[0] if g else f'DEP {dd}'),
                'mun': mm, 'munNom': (row['NOM_MUN'] or '').strip() or (g[1] if g else f'MUN {mm}'),
                'zon': zz, 'pue': pp,
                'pueNom': (row['NOM_PUESTO'] or '').strip() or (g[2] if g else f'PUESTO {zz}-{pp}'),
                'mesa': row['COD_MESA'].strip().zfill(3), 'com': comC, 'comNom': comN, 'v': v,
            })
    for persona, t in tot_2v.items():
        print(f'2V: {persona:10s} {fmt_num(t):>12s} votos · {fmt_num(len(mesas_2v[persona]))} mesas')

    # Controles duros (cifras oficiales del preconteo 0247 + 2V)
    CONTROL = {'cepeda': 9680095, 'abelardo': 10346010, 'paloma': 1637665,
               'fajardo': 1007627, 'botero': 206024, 'lizcano': 53828, 'claudia': 225287}
    for persona, esperado in CONTROL.items():
        got = tot_1v[persona]
        assert got == esperado, f'1V {persona}: {got} != control {esperado}'
    print('Controles 1V OK (7/7 contra cifras oficiales)')

    # ── Consultas vinculadas (histórico): busca en el índice endoso vivo ──
    consulta_links = {}
    try:
        with urllib.request.urlopen(ENDOSO_INDEX_URL, timeout=30) as r:
            endoso_idx = json.load(r)
        for _, persona, nombre, *_ in [(p[0], p[1], p[2]) for p in PERSONAS]:
            toks = set(norm(nombre).split())
            for e in endoso_idx:
                if e.get('corp') != 'CONSULTAS' or e.get('tipo') != 'candidato':
                    continue
                etoks = set(norm(e.get('nombre', '')).split())
                if toks <= etoks or etoks <= toks:
                    consulta_links[persona] = {
                        'slug': e['slug'], 'nombre': e['nombre'],
                        'votos': e.get('votos', 0), 'partido': e.get('partido', ''),
                    }
                    break
        print('Consultas vinculadas:', {k: v['slug'] for k, v in consulta_links.items()})
    except Exception as ex:
        print(f'AVISO: no se pudo leer el índice endoso ({ex}) — sin links de consulta')

    # ── Escribir JSONs por candidato ──────────────────────────────────────
    def write_cand(fname, nombre, partido, votos, mesas, ronda):
        data = {
            'nombre': nombre, 'corp': f'PRESIDENCIA {ronda}', 'circunscripcion': 'NACIONAL',
            'partido': partido, 'votos': votos, 'mesas': mesas,
        }
        path = os.path.join(OUT_DIR, fname)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        print(f'  → {fname} ({os.path.getsize(path)//1024} KB)')

    index = {'v': '2026-07-14', 'presidente': PRESIDENTE,
             'vmax': tot_2v[PRESIDENTE], 'personas': []}
    for col, persona, nombre, partido, ideol, foto in PERSONAS:
        slug = slug_of(nombre)
        elecciones = []
        f1 = f'PRES1V_{slug}.json'
        write_cand(f1, nombre, partido, tot_1v[persona], mesas_1v[persona], '· 1ª VUELTA')
        elecciones.append({'ronda': '1V', 'label': 'Presidencia 2026 · 1ª vuelta',
                           'file': f1, 'votos': tot_1v[persona]})
        if persona in mesas_2v:
            f2 = f'PRES2V_{slug}.json'
            write_cand(f2, nombre, partido, tot_2v[persona], mesas_2v[persona], '· 2ª VUELTA')
            elecciones.append({'ronda': '2V', 'label': 'Presidencia 2026 · 2ª vuelta',
                               'file': f2, 'votos': tot_2v[persona],
                               'presidente': persona == PRESIDENTE})
        p = {'persona': persona, 'nombre': nombre, 'partido': partido, 'ideol': ideol,
             'foto': f'{FOTO_BASE}/{foto}' if foto else None,
             'presidente': persona == PRESIDENTE, 'elecciones': elecciones}
        if persona in consulta_links:
            p['consulta'] = consulta_links[persona]
        index['personas'].append(p)

    idx_path = os.path.join(OUT_DIR, 'index-presidencial.json')
    with open(idx_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, separators=(',', ':'))
    print(f'→ index-presidencial.json ({os.path.getsize(idx_path)} bytes) · {len(index["personas"])} personas')

if __name__ == '__main__':
    main()
