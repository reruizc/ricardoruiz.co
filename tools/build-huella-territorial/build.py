#!/usr/bin/env python3
"""
tools/build-huella-territorial/build.py

Construye huella-territorial.json — bias por barrio (ciudades) / municipio (rural)
para los 6 candidatos presidenciales 2026, aplicando la formula del ponderador
sobre 9 senales historicas:

  pres-2010, pres-2014, pres-2018, pres-2022             (CSV crudos GCS)
  consulta-2025-pacto                                    (CSV crudo GCS)
  consulta-2026-{gran,frente,soluciones}                 (por-puesto.json en S3)
  senado-2026                                            (puestos.json por depto en S3)

Cruce puesto -> barrio via PUESTOS_GEOREF.csv. Cascada de matching:
  A = match exacto (DD,MMM,ZZ,PP)
  B = match por zona (DD,MMM,ZZ) -> barrio modal de la zona
  C = solo municipio

Uso:
  python3 tools/build-huella-territorial/build.py
  -> escribe Bases de datos/output_huella/huella-territorial.json

Cache S3 en /tmp/huella-cache (md5 de la URL).
"""

import csv
import json
import os
import re
import sys
import unicodedata
import urllib.request
import hashlib
from collections import defaultdict, Counter

# === PATHS ===
ROOT = '/Users/ricardoruiz/ricardoruiz.co'
GEO_CSV = f'{ROOT}/Bases de datos/PUESTOS_GEOREF.csv'
GCS_DIR = f'{ROOT}/Bases de datos/FINAL SUBIDA GCS'
OUT_DIR = f'{ROOT}/Bases de datos/output_huella'
OUT_FILE = f'{OUT_DIR}/huella-territorial.json'
CACHE_DIR = '/tmp/huella-cache'

S3_HIST = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/historicos'
S3_CONG = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output'

# Ciudades con desagregacion por barrio. (DD electoral, MMM electoral) -> nombre canonico.
# Resto del pais cae a nivel municipio.
CIUDADES_BARRIO = {
    ('16', '001'): 'Bogotá',          # 19 localidades agrupadas bajo dep 16 mun 001
    ('01', '001'): 'Medellín',
    ('31', '001'): 'Cali',
    ('03', '001'): 'Barranquilla',
    ('05', '001'): 'Cartagena',
    ('29', '001'): 'Ibagué',
    ('13', '001'): 'Montería',
    ('52', '001'): 'Villavicencio',
    ('09', '001'): 'Manizales',
    ('25', '001'): 'Cúcuta',
    ('27', '001'): 'Bucaramanga',
    ('24', '001'): 'Pereira',
    ('23', '001'): 'Pasto',
    ('21', '001'): 'Santa Marta',
    ('11', '001'): 'Popayán',
    ('12', '001'): 'Valledupar',
    ('48', '001'): 'Riohacha',
    ('19', '001'): 'Neiva',
    ('26', '001'): 'Armenia',
    ('31', '079'): 'Palmira',
    ('31', '019'): 'Buenaventura',
    ('27', '019'): 'Barrancabermeja',
    ('31', '106'): 'Tuluá',
    ('01', '049'): 'Bello',
    ('03', '052'): 'Soledad',
    ('15', '247'): 'Soacha',
    ('23', '139'): 'Tumaco',
}

# === SENALES ===
SENALES = [
    {'id': 'pres-2010',           'tipo': 'gcs', 'archivo': 'GCS_2010PRES1V.csv'},
    {'id': 'pres-2014',           'tipo': 'gcs', 'archivo': 'GCS_2014PRES1V.csv'},
    {'id': 'pres-2018',           'tipo': 'gcs', 'archivo': 'GCS_2018PRES1V.csv'},
    {'id': 'pres-2022',           'tipo': 'gcs', 'archivo': 'GCS_2022PRES1V.csv'},
    {'id': 'consulta-2025-pacto', 'tipo': 'gcs', 'archivo': 'GCS_2025CONSU.csv'},
    {'id': 'consulta-2026-gran',       'tipo': 's3-por-puesto', 'url': f'{S3_HIST}/consulta-2026-gran/por-puesto.json'},
    {'id': 'consulta-2026-frente',     'tipo': 's3-por-puesto', 'url': f'{S3_HIST}/consulta-2026-frente/por-puesto.json'},
    {'id': 'consulta-2026-soluciones', 'tipo': 's3-por-puesto', 'url': f'{S3_HIST}/consulta-2026-soluciones/por-puesto.json'},
    {'id': 'senado-2026',         'tipo': 's3-senado'},
]

# === EQUIVALENCIAS (de previa-1v.html lineas 1636-1685) ===
EQUIV = {
    'ic': {
        'consulta-2025-pacto': {'cands': ['IVAN CEPEDA CASTRO'], 'peso': 0.38},
        'senado-2026':         {'partidos': ['PACTO HISTÓRICO SENADO'], 'peso': 0.18},
        'pres-2022':           {'cands': ['GUSTAVO PETRO'], 'peso': 0.17},
        'pres-2018':           {'cands': ['GUSTAVO PETRO'], 'peso': 0.10},
        'pres-2014':           {'cands': ['CLARA LOPEZ'], 'peso': 0.05},
        'pres-2010':           {'cands': ['GUSTAVO FRANCISCO PETRO URREGO', 'AURELIJUS RUTENIS ANTANAS MOCKUS SIVICKAS'], 'peso': 0.02},
    },
    'ae': {
        'senado-2026':  {'partidos': ['MOVIMIENTO SALVACIÓN NACIONAL'], 'peso': 0.30},
        'pres-2022':    {'cands': ['FEDERICO GUTIERREZ', 'RODOLFO HERNANDEZ'], 'peso': 0.25},
        'pres-2018':    {'cands': ['IVAN DUQUE'], 'peso': 0.15},
        'pres-2014':    {'cands': ['OSCAR IVAN ZULUAGA'], 'peso': 0.10},
        'pres-2010':    {'cands': ['JUAN MANUEL SANTOS CALDERON'], 'peso': 0.05},
    },
    'pv': {
        'consulta-2026-gran': {'cands': ['PALOMA SUSANA VALENCIA LASERNA'], 'peso': 0.40},
        'senado-2026':  {'partidos': ['PARTIDO CENTRO DEMOCRÁTICO'], 'peso': 0.20},
        'pres-2022':    {'cands': ['FEDERICO GUTIERREZ'], 'peso': 0.18},
        'pres-2018':    {'cands': ['IVAN DUQUE'], 'peso': 0.10},
        'pres-2014':    {'cands': ['OSCAR IVAN ZULUAGA'], 'peso': 0.04},
    },
    'sf': {
        'pres-2022':    {'cands': ['SERGIO FAJARDO'], 'peso': 0.30},
        'pres-2018':    {'cands': ['SERGIO FAJARDO'], 'peso': 0.25},
        'senado-2026':  {'partidos': ['ALIANZA POR COLOMBIA', 'AHORA COLOMBIA'], 'peso': 0.15},
        'pres-2014':    {'cands': ['ENRIQUE PENALOSA', 'MARTHA LUCIA RAMIREZ'], 'peso': 0.07},
        'pres-2010':    {'cands': ['AURELIJUS RUTENIS ANTANAS MOCKUS SIVICKAS'], 'peso': 0.05},
    },
    'cl': {
        'consulta-2026-soluciones': {'cands': ['CLAUDIA NAYIBE LOPEZ HERNANDEZ'], 'peso': 0.35},
        'senado-2026':  {'partidos': ['AHORA COLOMBIA'], 'peso': 0.15},
        'pres-2022':    {'cands': ['SERGIO FAJARDO'], 'peso': 0.18},
        'pres-2018':    {'cands': ['SERGIO FAJARDO'], 'peso': 0.08},
        'pres-2014':    {'cands': ['ENRIQUE PENALOSA'], 'peso': 0.04},
    },
    'rb': {
        'consulta-2026-frente': {'cands': ['ROY LEONARDO BARRERAS MONTEALEGRE'], 'peso': 0.40},
        'senado-2026':  {'partidos': ['FRENTE AMPLIO UNITARIO'], 'peso': 0.20},
        'pres-2022':    {'cands': ['GUSTAVO PETRO'], 'peso': 0.15},
        'pres-2018':    {'cands': ['HUMBERTO DE LA CALLE'], 'peso': 0.08},
    },
}
CAND_LIST = ['ic', 'ae', 'pv', 'sf', 'cl', 'rb']

# COD_CAN especiales en GCS — fuera del agregado
ESPECIALES_CAN = {'996', '997', '998', '999'}

VERSION = '2026-05-18'


# === HELPERS ===

def norm_text(s):
    """uppercase, sin tildes, sin double-spaces — para comparar nombres."""
    if not s:
        return ''
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', s).upper().strip()


def slug(s):
    """slug url-safe: lower, sin tildes, alfanumerico + guion."""
    if not s:
        return ''
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-zA-Z0-9]+', '-', s).strip('-').lower()


def pad2(s):
    s = str(s or '').strip()
    if not s:
        return '00'
    return s.zfill(2)


def pad3(s):
    s = str(s or '').strip()
    if not s:
        return '000'
    return s.zfill(3)


# === STEP 1: LOOKUP DESDE PUESTOS_GEOREF ===

def build_lookup():
    """
    Carga PUESTOS_GEOREF.csv y construye:
      - lookup: (dd,mmm,zz,pp) -> {barrio_key, mun_key, ciudad, censo}
      - barrio_meta: barrio_key -> {nombre, ciudad, subloc, mun_cod, dep, n_puestos, censo}
      - mun_meta: (dd,mmm) -> {nombre, dep, ciudad_canon, n_puestos, censo}
      - barrio_modal_zona: (dd,mmm,zz) -> barrio_key mas frecuente (fallback B)
    """
    lookup = {}
    barrio_meta = {}
    mun_meta = {}
    barrios_por_zona = defaultdict(list)

    with open(GEO_CSV, encoding='utf-8-sig') as f:
        r = csv.DictReader(f, delimiter=';')
        for row in r:
            c = (row.get('CÓDIGO COMPLETO') or '').strip()
            if len(c) < 9:
                continue
            dd, mmm, zz, pp = c[0:2], c[2:5], c[5:7], c[7:9]
            dep = (row.get('DEPARTAMENTO') or '').strip()
            mun_raw = (row.get('MUNICIPIO') or '').strip()
            barrio_raw = (row.get('BARRIO') or '').strip()
            comuna_raw = (row.get('NOMBRE COMUNA') or '').strip()

            try:
                muj = int(row.get('MUJERES') or 0)
                hom = int(row.get('HOMBRES') or 0)
            except ValueError:
                muj = hom = 0
            censo = muj + hom

            ciudad_canon = CIUDADES_BARRIO.get((dd, mmm))

            # Sub-localizacion
            if ciudad_canon == 'Bogotá':
                # En Bogota el MUNICIPIO de PUESTOS_GEOREF es la localidad
                subloc_label = mun_raw
                subloc_slug = slug(mun_raw)
            elif ciudad_canon:
                # Comuna como subloc; si vacia, usar zona ZZ
                if comuna_raw:
                    # PUESTOS_GEOREF pega el codigo al nombre: "01COMUNA 1 POPULAR" -> "COMUNA 1 POPULAR"
                    comuna_clean = re.sub(r'^\d+\s*', '', comuna_raw).strip()
                    subloc_label = comuna_clean or comuna_raw
                    subloc_slug = slug(comuna_clean or comuna_raw)
                else:
                    subloc_label = f'Zona {zz}'
                    subloc_slug = f'zona-{zz}'
            else:
                subloc_label = comuna_raw or ''
                subloc_slug = slug(comuna_raw) if comuna_raw else ''

            barrio_slug_v = slug(barrio_raw) if barrio_raw else ''
            bk = None
            if ciudad_canon and barrio_slug_v:
                bk = f'{slug(ciudad_canon)}::{subloc_slug or "_"}::{barrio_slug_v}'
                meta = barrio_meta.setdefault(bk, {
                    'nombre': barrio_raw,
                    'ciudad': ciudad_canon,
                    'subloc': subloc_label,
                    'mun_cod': f'{dd}-{mmm}',
                    'dep': dep,
                    'n_puestos': 0,
                    'censo': 0,
                })
                meta['n_puestos'] += 1
                meta['censo'] += censo

            mun_key = (dd, mmm)
            mm = mun_meta.setdefault(mun_key, {
                'nombre': 'Bogotá D.C.' if ciudad_canon == 'Bogotá' else mun_raw,
                'dep': dep,
                'ciudad_canon': ciudad_canon,
                'n_puestos': 0,
                'censo': 0,
            })
            mm['n_puestos'] += 1
            mm['censo'] += censo

            lookup[(dd, mmm, zz, pp)] = {
                'barrio_key': bk,
                'mun_key': mun_key,
                'ciudad': ciudad_canon,
                'censo': censo,
            }
            if bk:
                barrios_por_zona[(dd, mmm, zz)].append((bk, censo or 1))

    # Modal por zona
    barrio_modal_zona = {}
    for k, lst in barrios_por_zona.items():
        cnt = Counter()
        for bk, w in lst:
            cnt[bk] += w
        if cnt:
            barrio_modal_zona[k] = cnt.most_common(1)[0][0]

    return lookup, barrio_meta, mun_meta, barrio_modal_zona


def resolve_terr(dd, mmm, zz, pp, lookup, barrio_modal_zona):
    """(barrio_key | None, mun_key | None, level)."""
    rec = lookup.get((dd, mmm, zz, pp))
    if rec:
        return rec['barrio_key'], rec['mun_key'], 'A'
    bk = barrio_modal_zona.get((dd, mmm, zz))
    if bk:
        return bk, (dd, mmm), 'B'
    return None, (dd, mmm), 'C'


# === STEP 2: STREAMING GCS ===

def proc_gcs(senal, lookup, barrio_modal_zona, agreg_barrio, agreg_mun, agreg_nac, stats):
    path = os.path.join(GCS_DIR, senal['archivo'])
    sid = senal['id']
    counts = Counter()
    seen_cands = Counter()

    with open(path, encoding='utf-8-sig') as f:
        r = csv.DictReader(f, delimiter=';')
        for row in r:
            cod_can = (row.get('COD_CAN') or '').strip()
            if cod_can in ESPECIALES_CAN:
                continue
            dd = pad2(row.get('COD_DDE'))
            mmm = pad3(row.get('COD_MME'))
            zz = pad2(row.get('COD_ZZ'))
            pp = pad2(row.get('COD_PP'))
            des_can = (row.get('DES_CAN') or '').strip()
            try:
                votos = int(row.get('NUM_VOT') or 0)
            except ValueError:
                votos = 0
            if not des_can or votos <= 0:
                if not des_can:
                    continue

            cand_norm = norm_text(des_can)
            seen_cands[cand_norm] += votos

            bk, mk, level = resolve_terr(dd, mmm, zz, pp, lookup, barrio_modal_zona)
            counts[level] += 1

            if bk:
                agreg_barrio[bk][(sid, cand_norm)] += votos
                agreg_barrio[bk][(sid, '__VV__')] += votos
            if mk:
                agreg_mun[mk][(sid, cand_norm)] += votos
                agreg_mun[mk][(sid, '__VV__')] += votos
            agreg_nac[(sid, cand_norm)] += votos
            agreg_nac[(sid, '__VV__')] += votos

    stats[sid] = {
        'niveles': dict(counts),
        'top_cands': seen_cands.most_common(8),
    }
    a = counts.get('A', 0); b = counts.get('B', 0); cn = counts.get('C', 0)
    tot = a + b + cn or 1
    print(f"  [{sid}] A={100*a/tot:.1f}% B={100*b/tot:.1f}% C={100*cn/tot:.1f}%  filas={tot}")
    print(f"     top: {', '.join(f'{n} ({v:,})' for n, v in seen_cands.most_common(4))}")


# === STEP 3: FETCH S3 ===

def fetch_cached(url):
    os.makedirs(CACHE_DIR, exist_ok=True)
    h = hashlib.md5(url.encode()).hexdigest()
    p = f'{CACHE_DIR}/{h}.json'
    if os.path.exists(p):
        with open(p, 'rb') as f:
            return json.loads(f.read().decode('utf-8'))
    print(f"     fetch: {url}")
    req = urllib.request.Request(url, headers={'User-Agent': 'huella-build/1.0'})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    with open(p, 'wb') as f:
        f.write(data)
    return json.loads(data.decode('utf-8'))


def proc_s3_por_puesto(senal, lookup, barrio_modal_zona, agreg_barrio, agreg_mun, agreg_nac, stats):
    """Consultas 2026: por-puesto.json en S3. Format con wrapper:
       {nombre, anio, n_puestos, candidatos:{...}, puestos:{DD-MMM-ZZ-PP: {vv, v:{nombre:votos}}}}"""
    sid = senal['id']
    try:
        raw = fetch_cached(senal['url'])
    except Exception as e:
        print(f"  ERROR {sid}: {e}")
        stats[sid] = {'error': str(e)}
        return

    # Soporta tanto el formato con wrapper como dict directo
    data = raw.get('puestos') if isinstance(raw, dict) and 'puestos' in raw else raw

    counts = Counter()
    seen_cands = Counter()
    for key, rec in data.items():
        parts = key.split('-')
        if len(parts) != 4:
            continue
        dd = pad2(parts[0]); mmm = pad3(parts[1]); zz = pad2(parts[2]); pp = pad2(parts[3])
        v_map = rec.get('v') or {}
        bk, mk, level = resolve_terr(dd, mmm, zz, pp, lookup, barrio_modal_zona)
        counts[level] += 1
        for nombre, votos in v_map.items():
            try:
                votos = int(votos)
            except (TypeError, ValueError):
                continue
            if votos <= 0:
                continue
            cn = norm_text(nombre)
            seen_cands[cn] += votos
            if bk:
                agreg_barrio[bk][(sid, cn)] += votos
                agreg_barrio[bk][(sid, '__VV__')] += votos
            if mk:
                agreg_mun[mk][(sid, cn)] += votos
                agreg_mun[mk][(sid, '__VV__')] += votos
            agreg_nac[(sid, cn)] += votos
            agreg_nac[(sid, '__VV__')] += votos

    stats[sid] = {
        'niveles': dict(counts),
        'top_cands': seen_cands.most_common(8),
    }
    a = counts.get('A', 0); b = counts.get('B', 0); cn = counts.get('C', 0)
    tot = a + b + cn or 1
    print(f"  [{sid}] A={100*a/tot:.1f}% B={100*b/tot:.1f}% C={100*cn/tot:.1f}%  puestos={tot}")
    print(f"     top: {', '.join(f'{n} ({v:,})' for n, v in seen_cands.most_common(4))}")


DEPS_ELECTORALES = [
    '01','03','05','07','09','11','12','13','15','16','17','19','21','23','24','25',
    '26','27','28','29','31','40','44','46','48','50','52','54','56','60','64','68','72','88',
]


def proc_senado_2026(lookup, barrio_modal_zona, agreg_barrio, agreg_mun, agreg_nac, stats):
    sid = 'senado-2026'
    counts = Counter()
    seen_parts = Counter()
    deps_ok = 0; deps_fail = 0
    for dep_cod in DEPS_ELECTORALES:
        url = f'{S3_CONG}/senado/departamentos/{dep_cod}/puestos.json'
        try:
            data = fetch_cached(url)
            deps_ok += 1
        except Exception as e:
            deps_fail += 1
            continue
        for p in data:
            dd = pad2(p.get('dep_cod'))
            mmm = pad3(p.get('mun_cod'))
            zz = pad2(p.get('zon_cod'))
            pp_raw = p.get('pue_cod_raw') if p.get('pue_cod_raw') is not None else p.get('pue_cod')
            pp = pad2(pp_raw)
            partidos = p.get('partidos') or {}
            bk, mk, level = resolve_terr(dd, mmm, zz, pp, lookup, barrio_modal_zona)
            counts[level] += 1
            for nombre, votos in partidos.items():
                try:
                    votos = int(votos)
                except (TypeError, ValueError):
                    continue
                if votos <= 0:
                    continue
                pn = norm_text(nombre)
                seen_parts[pn] += votos
                if bk:
                    agreg_barrio[bk][(sid, pn)] += votos
                    agreg_barrio[bk][(sid, '__VV__')] += votos
                if mk:
                    agreg_mun[mk][(sid, pn)] += votos
                    agreg_mun[mk][(sid, '__VV__')] += votos
                agreg_nac[(sid, pn)] += votos
                agreg_nac[(sid, '__VV__')] += votos

    stats[sid] = {
        'niveles': dict(counts),
        'top_partidos': seen_parts.most_common(12),
        'deps_ok': deps_ok, 'deps_fail': deps_fail,
    }
    a = counts.get('A', 0); b = counts.get('B', 0); cn = counts.get('C', 0)
    tot = a + b + cn or 1
    print(f"  [{sid}] A={100*a/tot:.1f}% B={100*b/tot:.1f}% C={100*cn/tot:.1f}%  puestos={tot}  deps OK={deps_ok} fail={deps_fail}")
    print(f"     top: {', '.join(f'{n} ({v:,})' for n, v in seen_parts.most_common(5))}")


# === STEP 4: COMPUTO afin + bias ===

def afin(agreg_terr, equiv_c):
    """afin = sum_s peso_s * (votos_equivalentes / vv)."""
    total = 0.0
    for sid, regla in equiv_c.items():
        peso = regla['peso']
        nombres = [norm_text(n) for n in (regla.get('cands') or regla.get('partidos') or [])]
        votos = sum(agreg_terr.get((sid, n), 0) for n in nombres)
        vv = agreg_terr.get((sid, '__VV__'), 0)
        if vv > 0:
            total += peso * (votos / vv)
    return total


def bias_cand(agreg_terr, equiv_c, afin_nac_c):
    if afin_nac_c <= 0:
        return None
    af_loc = afin(agreg_terr, equiv_c)
    if af_loc <= 0:
        return 0.0
    return round(af_loc / afin_nac_c, 3)


def top_cand_senal(agreg_terr, sid):
    """Top candidato/partido en una senal sobre el agregado del territorio."""
    cands = [(k[1], v) for k, v in agreg_terr.items() if k[0] == sid and k[1] != '__VV__']
    if not cands:
        return None
    cands.sort(key=lambda x: -x[1])
    top_n, top_v = cands[0]
    vv = agreg_terr.get((sid, '__VV__'), 0)
    if vv <= 0:
        return None
    return {'n': top_n, 'pct': round(100 * top_v / vv, 1)}


def consulta_2026_ganadora(agreg_terr):
    totales = {}
    for cid in ['gran', 'frente', 'soluciones']:
        sid = f'consulta-2026-{cid}'
        vv = agreg_terr.get((sid, '__VV__'), 0)
        if vv > 0:
            totales[cid] = vv
    if not totales:
        return None
    return max(totales, key=totales.get)


# === STEP 5: BUILD OUTPUT ===

def build_output(barrio_meta, mun_meta, agreg_barrio, agreg_mun, agreg_nac):
    afin_nac = {c: round(afin(agreg_nac, EQUIV[c]), 6) for c in CAND_LIST}

    senal_ids = [s['id'] for s in SENALES]

    barrios_out = {}
    for bk, meta in barrio_meta.items():
        terr = agreg_barrio.get(bk, {})
        if all(terr.get((sid, '__VV__'), 0) == 0 for sid in senal_ids):
            continue
        bias = {c: bias_cand(terr, EQUIV[c], afin_nac[c]) for c in CAND_LIST}
        hechos = {
            'p22':  top_cand_senal(terr, 'pres-2022'),
            'c25p': top_cand_senal(terr, 'consulta-2025-pacto'),
            'c26':  consulta_2026_ganadora(terr),
            's26':  top_cand_senal(terr, 'senado-2026'),
        }
        barrios_out[bk] = {
            'n': meta['nombre'],
            'ciudad': meta['ciudad'],
            'subloc': meta['subloc'],
            'mun': meta['mun_cod'],
            'dep': meta['dep'],
            'puestos': meta['n_puestos'],
            'censo': meta['censo'],
            'b': bias,
            'h': hechos,
        }

    muns_out = {}
    for mk, meta in mun_meta.items():
        terr = agreg_mun.get(mk, {})
        if all(terr.get((sid, '__VV__'), 0) == 0 for sid in senal_ids):
            continue
        mun_id = f'{mk[0]}-{mk[1]}'
        bias = {c: bias_cand(terr, EQUIV[c], afin_nac[c]) for c in CAND_LIST}
        hechos = {
            'p22':  top_cand_senal(terr, 'pres-2022'),
            'c25p': top_cand_senal(terr, 'consulta-2025-pacto'),
            'c26':  consulta_2026_ganadora(terr),
            's26':  top_cand_senal(terr, 'senado-2026'),
        }
        muns_out[mun_id] = {
            'n': meta['nombre'],
            'dep': meta['dep'],
            'ciudad': meta['ciudad_canon'],
            'puestos': meta['n_puestos'],
            'censo': meta['censo'],
            'b': bias,
            'h': hechos,
        }

    return {
        'v': VERSION,
        'cands': CAND_LIST,
        'afin_nac': afin_nac,
        'n_barrios': len(barrios_out),
        'n_muns': len(muns_out),
        'barrios': barrios_out,
        'muns': muns_out,
    }


# === MAIN ===

def main():
    print(f"=== huella-territorial build v{VERSION} ===\n")

    print(f"-> Lookup desde PUESTOS_GEOREF.csv")
    lookup, barrio_meta, mun_meta, barrio_modal_zona = build_lookup()
    print(f"   {len(lookup):,} puestos, {len(barrio_meta):,} barrios canonicos, {len(mun_meta):,} muns")

    agreg_barrio = defaultdict(lambda: defaultdict(int))
    agreg_mun = defaultdict(lambda: defaultdict(int))
    agreg_nac = defaultdict(int)
    stats = {}

    for senal in SENALES:
        print(f"\n-> {senal['id']}  [{senal['tipo']}]")
        if senal['tipo'] == 'gcs':
            proc_gcs(senal, lookup, barrio_modal_zona, agreg_barrio, agreg_mun, agreg_nac, stats)
        elif senal['tipo'] == 's3-por-puesto':
            proc_s3_por_puesto(senal, lookup, barrio_modal_zona, agreg_barrio, agreg_mun, agreg_nac, stats)
        elif senal['tipo'] == 's3-senado':
            proc_senado_2026(lookup, barrio_modal_zona, agreg_barrio, agreg_mun, agreg_nac, stats)

    print(f"\n-> Computando bias + output")
    out = build_output(barrio_meta, mun_meta, agreg_barrio, agreg_mun, agreg_nac)
    print(f"   barrios emitidos: {out['n_barrios']:,}")
    print(f"   muns emitidos:    {out['n_muns']:,}")
    print(f"   afin_nac: {json.dumps(out['afin_nac'])}")

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    sz = os.path.getsize(OUT_FILE) / 1024 / 1024
    print(f"   -> {OUT_FILE}  ({sz:.2f} MB)")

    # Stats por senal
    print(f"\n=== STATS DETALLE POR SENAL ===")
    for sid, st in stats.items():
        print(f"\n  [{sid}]")
        for k, v in st.items():
            if k == 'top_cands' or k == 'top_partidos':
                print(f"    {k}:")
                for n, vot in v[:6]:
                    print(f"       {n}: {vot:,}")
            else:
                print(f"    {k}: {v}")


if __name__ == '__main__':
    main()
