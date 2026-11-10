#!/usr/bin/env python3
"""Módulo 02 · El inventario — arma los datos del mapa municipal por partido.

Entradas (todas locales):
  Bases de datos/nuevo-liberalismo/ter2023-agg.json      (agrega_ter2023.py · GCS_2023TER)
  Bases de datos/nuevo-liberalismo/congreso-puesto.json  (agrega_congreso.py · MMV comisiones 2026)
  Bases de datos/indices-s3-backup/jal-2023__index-jal-2023.json + output_hvp/curules-jal.json
  Bases de datos/output_jal_2023/resultados-jal-2023.json (blanco por localidad)
  Bases de datos/output_pacto_1v_2026/geo/mps/{cod}.json  (polígonos municipales, llave electoral)
  Bases de datos/output_ponal/poblacion.json              (DANE, proyección municipal)
  Bases de datos/legislativo/fuerzas-internas-2026.json   (bancada oficial: API del Senado y camara.gov.co)
  legislativo-electos.js                                  (285 electos 2026 con su lista)

Salidas en Propuestas/nuevo-liberalismo/datos/:
  municipios.geojson   polígonos simplificados, props {k:'DDMMM', n, d}
  inventario.json      capas por municipio y partido + bloque fijo del Nuevo Liberalismo

Reglas (ver la nota de método de inventario.html):
  · una lista cuenta para cada partido que NOMBRA; el nombre genérico de una coalición no se
    le atribuye a nadie (cae en 'otros').
  · «Ahora Colombia» al Senado 2026 es la coalición nacional de MIRA, Nuevo Liberalismo y
    Dignidad: en esa capa cuenta para los tres. En Cámara la lista se llama igual pero su
    composición cambia por departamento, así que solo lleva la llave 'ahora'.
  · curules de concejo ESTIMADAS: número por población (art. 22, Ley 136 de 1994; Bogotá 45) y
    reparto del art. 263 con la misma lógica de vote-target.js (umbral = medio cuociente sobre
    válidos con blanco; una curul se reserva al Estatuto de la Oposición y se reparten n − 1).
"""
import json, os, re, sys, glob, unicodedata, collections

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(AQUI, '..', '..'))
BD = os.path.join(REPO, 'Bases de datos')
OUT = os.path.join(REPO, 'Propuestas', 'nuevo-liberalismo', 'datos')
os.makedirs(OUT, exist_ok=True)
SOLO_DATOS = '--sin-geo' in sys.argv

def J(*p): return json.load(open(os.path.join(BD, *p), encoding='utf-8'))
def norm(s):
    s = unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode().upper()
    return re.sub(r'\s+', ' ', re.sub(r'[^A-Z0-9&+ ]+', ' ', s)).strip()

# ───────────────────────── partidos: nombre de lista → llaves ─────────────────────────
REGLAS = [  # (llave, regex sobre el nombre normalizado)
    ('nl',         r'NUEVO LIBERALISMO'),
    ('liberal',    r'\bLIBERAL\b'),
    ('conservador',r'\bCONSERVADOR\b'),
    ('cd',         r'CENTRO DEMOCRATICO|\bCD\b'),
    ('cr',         r'CAMBIO RADICAL|\bCR\b'),
    ('u',          r'PARTIDO DE LA U\b|UNION POR LA GENTE|\bLA U\b|\bLAU\b|^U\b|\bU Y\b'),
    ('verde',      r'ALIANZA VERDE|PACTO VERDE|\bVERDE\b(?! OXIGENO)'),
    ('pacto',      r'PACTO HISTORICO|PACTO VERDE|PACTO FRENTE AMPLIO|FRENTE AMPLIO PACTO'),
    ('ch',         r'COLOMBIA HUMANA'),
    ('polo',       r'POLO DEMOCRATICO|\bPOLO\b'),
    ('up',         r'UNION PATRIOTICA|\bUP\b'),
    ('comunes',    r'\bCOMUNES\b'),
    ('mais',       r'\bMAIS\b|ALTERNATIVO INDIGENA'),
    ('aico',       r'\bAICO\b|AUTORIDADES INDIGENAS DE COLOMBIA'),
    ('asi',        r'\bASI\b(?! ES\b)|ALIANZA SOCIAL INDEPENDIENTE'),
    ('mira',       r'(?<!ALTO )\bMIRA\b'),
    ('dignidad',   r'DIGNIDAD\s*(&|Y|\+)?\s*COMPROMISO'),
    ('salvacion',  r'SALVACION NACIONAL|\bMSN\b|DEMOCRATICO Y SALVACION'),
    ('marcha',     r'\bEN MARCHA\b'),
    ('creemos',    r'PARTIDO (POLITICO )?CREEMOS|^CREEMOS$|DEMOCRATICO CREEMOS|^(COALICION )?CREEMOS MIRA$'),
    ('liga',       r'LIGA (DE )?GOBERNANTES|\bLIGA\b'),
    ('renaciente', r'COLOMBIA RENACIENTE'),
    ('justa',      r'JUSTAS? LIBRES|\bCJL\b'),
    ('fuerza',     r'FUERZA CIUDADANA'),
    ('ahora',      r'AHORA COLOMBIA'),
    ('alianza',    r'ALIANZA POR COLOMBIA'),
    ('frente',     r'FRENTE AMPLIO'),
]
REGLAS = [(k, re.compile(rx)) for k, rx in REGLAS]
_cache = {}
def llaves(nombre, capa=''):
    ck = (nombre, capa)
    if ck in _cache: return _cache[ck]
    n = norm(nombre)
    n = n.replace('PARTIDO VERDE OXIGENO', 'OXIGENO').replace('PARTIDO ECOLOGISTA', 'ECOLOGISTA')
    ks = [k for k, rx in REGLAS if rx.search(n)]
    # «En Marcha» es también una frase corriente («Putumayo en marcha»): solo cuenta con su nombre
    # completo o junto a otro partido.
    if 'marcha' in ks and len(ks) == 1 and not re.search(r'AGRUPACION POLITICA EN MARCHA|PARTIDO EN MARCHA', n):
        ks = []
    # marcas que nacen en 2026: en 2023 esas palabras eran nombres locales
    if capa not in ('senado26', 'camara26'):
        ks = [k for k in ks if k not in ('ahora', 'alianza', 'frente')]
    if capa == 'senado26' and 'ahora' in ks:   # coalición nacional documentada
        ks = ['ahora', 'nl', 'mira', 'dignidad']
    if not ks: ks = ['otros']
    _cache[ck] = ks
    return ks

class Nombres:
    def __init__(self, capa): self.capa, self.ix, self.nom, self.key = capa, {}, [], []
    def i(self, nombre):
        nombre = re.sub(r'\s+', ' ', nombre).strip()
        if nombre not in self.ix:
            self.ix[nombre] = len(self.nom); self.nom.append(nombre); self.key.append(llaves(nombre, self.capa))
        return self.ix[nombre]

# ───────────────────────── reparto (art. 263, como vote-target.js) ─────────────────────────
def reparto(votos, curules, blanco, oposicion):
    """votos: {id: votos}. Devuelve ({id: curules}, umbral, cifra)."""
    validos = sum(votos.values())
    if curules < 1 or validos <= 0: return {}, 0, 0
    umbral = (validos + blanco) / curules / 2
    eleg = {k: v for k, v in votos.items() if v >= umbral} or dict(votos)
    n = max(1, curules - (1 if oposicion else 0))
    q = sorted(((v / d, k) for k, v in eleg.items() for d in range(1, n + 1)), reverse=True)[:n]
    asig = collections.Counter(k for _, k in q)
    return dict(asig), umbral, (q[-1][0] if q else 0)

def escala_136(pob):   # art. 22, Ley 136 de 1994 (verificado en secretariasenado.gov.co)
    for tope, n in ((5000, 7), (10000, 9), (20000, 11), (50000, 13), (100000, 15), (250000, 17), (1000000, 19)):
        if pob <= tope: return n
    return 21

CERRADA = 0.15   # criterio del proyecto: voto nominal < 15 % del voto de la lista
def total_lista(e): return e['l'] + sum(c[1] for c in e['c'].values())
def es_cerrada(e):
    t = total_lista(e)
    return (not e['c']) or (t - e['l']) < CERRADA * t
def top(e, k): return [c[0] for c in sorted(e['c'].values(), key=lambda c: -c[1])[:k]]

# ───────────────────────── geometría y catálogo de municipios ─────────────────────────
MUN = {}          # k → {n, d, p}
DANE2K = {}
geo_feats = []
for f in sorted(glob.glob(os.path.join(BD, 'output_pacto_1v_2026', 'geo', 'mps', '[0-9][0-9].json'))):
    g = json.load(open(f, encoding='utf-8'))
    for ft in g['features']:
        p = ft['properties']
        k = str(p['dep_electoral']).zfill(2) + str(p['mun_elec']).zfill(3)
        MUN[k] = {'n': p['mpio_cnmbr'], 'd': p['dpto_cnmbr']}
        DANE2K[p['mpio_cdpmp']] = k
        geo_feats.append((k, ft))
DEPN = {}
for k, m in MUN.items(): DEPN.setdefault(k[:2], m['d'])
DEPN['16'] = 'BOGOTÁ, D.C.'; DEPN['56'] = 'SAN ANDRÉS'
dv = J('test-presidencial', 'divipola.json')
for d in dv['deptos']:
    DEPN.setdefault(d['cod'], d['nombre'].upper())
    for m in d['muns']:
        MUN.setdefault(d['cod'] + m['cod'], {'n': m['nombre'].upper(), 'd': DEPN[d['cod']], 'sg': 1})
pob = J('output_ponal', 'poblacion.json'); i23 = pob['anios'].index(2023)
for dane, v in pob['muns'].items():
    k = DANE2K.get(dane)
    if k: MUN[k]['p'] = v['p'][i23]
def munk(k):
    if k not in MUN:
        MUN[k] = ({'n': 'CONSULADO ' + k[2:], 'd': 'EXTERIOR', 'sg': 1} if k[:2] == '88'
                  else {'n': 'MUNICIPIO ' + k[2:], 'd': DEPN.get(k[:2], k[:2]), 'sg': 1})
    return MUN[k]

if not SOLO_DATOS:
    import geopandas as gpd
    from shapely.geometry import shape, mapping
    gdf = gpd.GeoDataFrame({'k': [k for k, _ in geo_feats]}, geometry=[shape(ft['geometry']) for _, ft in geo_feats], crs='EPSG:4326')
    gdf['geometry'] = gdf.geometry.simplify(0.0045, preserve_topology=True)
    def r(o):
        if isinstance(o, (list, tuple)): return [r(x) for x in o]
        return round(o, 3) if isinstance(o, float) else o
    feats = []
    for k, geom in zip(gdf.k, gdf.geometry):
        if geom is None or geom.is_empty: continue
        gj = mapping(geom); gj = {'type': gj['type'], 'coordinates': r(gj['coordinates'])}
        feats.append({'type': 'Feature', 'properties': {'k': k, 'n': MUN[k]['n'], 'd': MUN[k]['d']}, 'geometry': gj})
    pth = os.path.join(OUT, 'municipios.geojson')
    json.dump({'type': 'FeatureCollection', 'features': feats}, open(pth, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('geo:', len(feats), 'polígonos ·', round(os.path.getsize(pth) / 1e6, 2), 'MB')
    # contorno de departamentos (solo para orientarse; no es interactivo)
    gd = gpd.GeoDataFrame({'d': [k[:2] for k, _ in geo_feats]}, geometry=[shape(ft['geometry']).buffer(0) for _, ft in geo_feats], crs='EPSG:4326')
    dep = gd.dissolve(by='d'); dep['geometry'] = dep.geometry.simplify(0.01, preserve_topology=True)
    df = []
    for dd, geom in zip(dep.index, dep.geometry):
        gj = mapping(geom); df.append({'type': 'Feature', 'properties': {'d': dd, 'n': DEPN.get(dd, dd)}, 'geometry': {'type': gj['type'], 'coordinates': r(gj['coordinates'])}})
    pth = os.path.join(OUT, 'deptos.geojson')
    json.dump({'type': 'FeatureCollection', 'features': df}, open(pth, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('deptos:', len(df), '·', round(os.path.getsize(pth) / 1e3), 'KB')

# ───────────────────────── territoriales 2023 ─────────────────────────
T = J('nuevo-liberalismo', 'ter2023-agg.json')
capas = {}
NLB = {'congreso': [], 'alcaldes': [], 'diputados': [], 'concejales': [], 'ediles': []}

# — Concejo —
N = Nombres('concejo23'); M = {}
st = collections.Counter()
for key, d in T['concejo'].items():
    k = key.replace('-', '')
    m = munk(k)
    tot = {par: total_lista(e) for par, e in d['p'].items()}
    maxlen = max((len(e['c']) for e in d['p'].values()), default=0)
    if k == '16001': cur = 45; st['bogota'] += 1
    elif m.get('p'):
        cur = escala_136(m['p'])
        if maxlen > cur and maxlen in (7, 9, 11, 13, 15, 17, 19, 21): cur = maxlen; st['sube_por_lista'] += 1
        elif maxlen == cur: st['coincide'] += 1
        else: st['lista_mas_corta' if maxlen < cur else 'lista_mas_larga_rara'] += 1
    else:
        cur = maxlen if maxlen >= 7 else 0; st['sin_poblacion'] += 1
    asig, umbral, cifra = reparto(tot, cur, d['b'], True) if cur else ({}, 0, 0)
    M[k] = {'v': sum(tot.values()) + d['b'], 's': cur,
            'l': sorted(([N.i(e['n']), tot[par], asig.get(par, 0)] for par, e in d['p'].items() if tot[par] > 0), key=lambda x: -x[1])}
    if k == '16001': bog = (asig, cifra, d)
    for par, e in d['p'].items():
        kk = llaves(e['n'], 'concejo23')
        if 'nl' in kk and asig.get(par, 0):
            c = es_cerrada(e)
            NLB['concejales'].append({'k': k, 'mun': m['n'], 'dep': m['d'], 'lista': e['n'], 'coal': len(kk) > 1,
                'cur': asig[par], 'de': cur, 'votos': tot[par], 'pct': round(tot[par] / M[k]['v'], 4),
                'cerrada': c, 'nombres': [] if c else top(e, asig[par])})
capas['concejo23'] = {'t': 'Concejo 2023', 'nom': N.nom, 'key': N.key, 'm': M}
print('concejo: curules por población vs lista más larga →', dict(st))
asig, cifra, d = bog
porn = {d['p'][par]['n']: n for par, n in asig.items()}
print('control Bogotá concejo (44 por cifra):', sorted(porn.items(), key=lambda x: -x[1]), '· cifra', round(cifra))
assert abs(cifra - 49481) < 60, 'la cifra repartidora de Bogotá 2023 debe dar ~49.481'
assert sum(asig.values()) == 44

# — Asamblea —
CUR_ASAM = {'01':26,'03':14,'05':14,'07':16,'09':14,'11':13,'12':11,'13':13,'15':16,'17':11,'19':12,'21':13,'23':14,'24':12,'25':13,'26':11,
            '27':16,'28':11,'29':15,'31':21,'40':11,'44':11,'46':11,'48':11,'50':11,'52':11,'54':11,'56':11,'60':11,'64':11,'68':11,'72':11}  # Decreto 1312 de 2023
SIN_OPOSICION = {'01'}   # Antioquia: Luis Pérez rechazó la curul (Valora Analitik, 11-nov-2023)
N = Nombres('asamblea23'); M = {}; DEP = {}
for dd, d in T['asamblea'].items():
    tot = {par: total_lista(e) for par, e in d['p'].items()}
    cur = CUR_ASAM.get(dd, 0)
    asig, umbral, cifra = reparto(tot, cur, d['b'], dd not in SIN_OPOSICION)
    DEP[dd] = {'s': cur, 'op': 0 if dd in SIN_OPOSICION else 1, 'n': DEPN.get(dd, dd),
               'l': sorted(([N.i(e['n']), tot[par], asig.get(par, 0)] for par, e in d['p'].items() if tot[par] > 0), key=lambda x: -x[1])}
    for par, e in d['p'].items():
        kk = llaves(e['n'], 'asamblea23')
        if 'nl' in kk and asig.get(par, 0):
            c = es_cerrada(e)
            NLB['diputados'].append({'dep': DEPN.get(dd, dd), 'lista': e['n'], 'coal': len(kk) > 1, 'cur': asig[par], 'de': cur,
                'votos': tot[par], 'cerrada': c, 'nombres': [] if c else top(e, asig[par])})
    for mm, pv in d['m'].items():
        k = dd + mm; munk(k)
        M[k] = {'v': sum(pv.values()) + d['mb'].get(mm, 0),
                'l': sorted(([N.i(d['p'][par]['n']), v] for par, v in pv.items() if v > 0), key=lambda x: -x[1])}
capas['asamblea23'] = {'t': 'Asamblea 2023', 'nom': N.nom, 'key': N.key, 'm': M, 'dep': DEP}

# — Alcaldía —
N = Nombres('alcaldia23'); M = {}
for key, d in T['alcaldia'].items():
    k = key.replace('-', ''); m = munk(k)
    v = sum(c[2] for c in d['c']) + d['b']
    M[k] = {'v': v, 'l': [[N.i(c[1]), c[2], 1 if i == 0 else 0, c[0]] for i, c in enumerate(d['c']) if c[2] > 0]}
    if d['c']:
        g = d['c'][0]; kk = llaves(g[1], 'alcaldia23')
        if 'nl' in kk:
            NLB['alcaldes'].append({'k': k, 'mun': m['n'], 'dep': m['d'], 'n': g[0], 'aval': g[1], 'coal': len(kk) > 1,
                                    'votos': g[2], 'pct': round(g[2] / v, 4)})
capas['alcaldia23'] = {'t': 'Alcaldía 2023', 'nom': N.nom, 'key': N.key, 'm': M}
gal = T['alcaldia']['16-001']['c'][0]
assert gal[2] == 1499734 and 'GALAN' in gal[0], 'control Galán'

# — JAL de Bogotá —
jal = J('indices-s3-backup', 'jal-2023__index-jal-2023.json')
curj = J('output_hvp', 'curules-jal.json')['curules']
rj = J('output_jal_2023', 'resultados-jal-2023.json')['data']['16-001']['comunas']
blancoj = {norm(c['name']): c['blanco'] for c in rj.values()}
porloc = collections.defaultdict(dict); candj = collections.defaultdict(list)
for l in jal['listas']:
    if l['circunscripcion'].endswith('· BOGOTÁ D.C.'):
        porloc[l['circunscripcion'].split('·')[0].strip()][l['partido']] = l
for c in jal['candidatos']:
    if c['circunscripcion'].endswith('· BOGOTÁ D.C.'):
        candj[(c['circunscripcion'].split('·')[0].strip(), c['partido'])].append((c['nombre'], c['votos']))
JAL_TOT = 0
for loc, ls in sorted(porloc.items()):
    cur = curj.get(norm(loc) + '|BOGOTA D C')
    if not cur: print('  JAL sin curules oficiales:', loc); continue
    JAL_TOT += cur
    asig, umbral, cifra = reparto({p: l['total'] for p, l in ls.items()}, cur, blancoj.get(norm(loc), 0), False)
    for p, l in ls.items():
        if 'nl' in llaves(p, 'jal23') and asig.get(p, 0):
            cs = sorted(candj.get((loc, p), []), key=lambda x: -x[1])
            NLB['ediles'].append({'loc': loc, 'lista': p, 'coal': len(llaves(p, 'jal23')) > 1, 'cur': asig[p], 'de': cur, 'votos': l['total'],
                                  'cerrada': bool(l.get('cerrada')), 'nombres': [] if l.get('cerrada') else [c[0] for c in cs[:asig[p]]]})

# ───────────────────────── Congreso 2026 ─────────────────────────
C = J('nuevo-liberalismo', 'congreso-puesto.json')
for capa, kv, kb, noms in (('senado26', 's', 'sb', C['partidos_sen']), ('camara26', 'c', 'cb', C['partidos_cam'])):
    agg = collections.defaultdict(collections.Counter); bl = collections.Counter()
    for pc, e in C['puestos'].items():
        k = pc[:5]
        for i, v in e[kv].items(): agg[k][int(i)] += v
        bl[k] += e[kb]
    N = Nombres(capa); M = {}
    for k, cnt in agg.items():
        munk(k)
        ls = []
        for i, v in cnt.items():
            nom = noms[i]
            if capa == 'senado26' and '[CIR' in nom: continue     # la circunscripción indígena va aparte
            ls.append([N.i(re.sub(r'\s*\[CIR \d\]', lambda m_: {' [CIR 4]': ' (indígena)', ' [CIR 5]': ' (afro)'}.get(m_.group(0), ''), nom)), v])
        M[k] = {'v': sum(x[1] for x in ls) + bl[k], 'l': sorted(ls, key=lambda x: -x[1])}
    capas[capa] = {'t': 'Senado 2026' if capa == 'senado26' else 'Cámara 2026', 'nom': N.nom, 'key': N.key, 'm': M}
cam = capas['camara26']; inl = cam['nom'].index('PARTIDO NUEVO LIBERALISMO')
vb = next(v for i, v in cam['m']['16001']['l'] if i == inl)
assert vb == 105616, f'NL Cámara Bogotá debe dar 105.616 y dio {vb}'
sen = capas['senado26']; iac = sen['nom'].index('AHORA COLOMBIA')
tot_ac = sum(v for m in sen['m'].values() for i, v in m['l'] if i == iac)
assert tot_ac == 891907, tot_ac

# electos 2026 (lista por la que entraron) y bancada oficial
js = open(os.path.join(REPO, 'legislativo-electos.js'), encoding='utf-8').read()
raw = json.loads(re.search(r'ELECTOS_RAW=(\[\[.*?\]\]);', js, re.S).group(1))
electos = [[e[0], e[1], e[2], e[3]] for e in raw]
fi = J('legislativo', 'fuerzas-internas-2026.json')
B2K = {'Pacto Histórico': 'pacto', 'Centro Democrático': 'cd', 'Partido Liberal': 'liberal', 'Partido Conservador': 'conservador',
       'Partido de la U': 'u', 'Alianza Verde': 'verde', 'Cambio Radical': 'cr', 'Salvación Nacional': 'salvacion', 'MIRA': 'mira',
       'ASI': 'asi', 'AICO': 'aico', 'Alianza por Colombia': 'alianza', 'Dignidad y Compromiso': 'dignidad', 'MAIS': 'mais',
       'Nuevo Liberalismo': 'nl', 'Creemos': 'creemos', 'Colombia Renaciente': 'renaciente'}
banc = {'senado26': collections.Counter(), 'camara26': collections.Counter()}
for corp, capa in (('senado', 'senado26'), ('camara', 'camara26')):
    for m in fi[corp]['miembros']: banc[capa][B2K.get(m['b'], 'otros')] += 1
porlista = {'senado26': collections.Counter(), 'camara26': collections.Counter()}
for e in raw:
    capa = 'senado26' if e[0] == 'S' else 'camara26'
    for kk in llaves(e[2], capa): porlista[capa][kk] += 1
end = J('indices-s3-backup', 'endoso__index.json')
vot = {norm(x['nombre']): x for x in end if x.get('tipo') == 'candidato'}
def toks(s): return set(norm(s).split())
for corp, etq in (('senado', 'Senado'), ('camara', 'Cámara')):
    for m in fi[corp]['miembros']:
        if m['b'] != 'Nuevo Liberalismo': continue
        t = toks(m['n']); x = next((v for n, v in vot.items() if toks(n) == t), None) or next((v for n, v in vot.items() if len(toks(n) & t) >= 3 and v['corp'].startswith(corp.upper()[:3])), None)
        el = next((e for e in raw if x and norm(e[1]) == norm(x['nombre'])), None)
        NLB['congreso'].append({'n': (x or {}).get('nombre', m['n']), 'corp': etq, 'lista': (x or {}).get('partido', ''),
                                'votos': (x or {}).get('votos'), 'dep': el[3] if el else '', 'com': m.get('c', '')})

# ───────────────────────── salida ─────────────────────────
NLB['concejales'].sort(key=lambda x: (-x['cur'], -x['votos']))
NLB['diputados'].sort(key=lambda x: (-x['cur'], -x['votos']))
NLB['alcaldes'].sort(key=lambda x: -x['votos'])
NLB['ediles'].sort(key=lambda x: (-x['cur'], -x['votos']))
resumen = {
    'congresistas': len(NLB['congreso']),
    'alcaldes': len(NLB['alcaldes']), 'alcaldes_coal': sum(1 for a in NLB['alcaldes'] if a['coal']),
    'diputados': sum(d['cur'] for d in NLB['diputados']), 'diputados_deps': len(NLB['diputados']),
    'concejales': sum(c['cur'] for c in NLB['concejales']), 'concejales_muns': len({c['k'] for c in NLB['concejales']}),
    'concejales_propias': sum(c['cur'] for c in NLB['concejales'] if not c['coal']),
    'ediles': sum(e['cur'] for e in NLB['ediles']), 'ediles_de': JAL_TOT,
}
# cuántas listas de concejo no nombran a ningún partido conocido
cc = capas['concejo23']; gen = sum(1 for m in cc['m'].values() for l in m['l'] if cc['key'][l[0]] == ['otros'])
resumen['concejo_listas'] = sum(len(m['l']) for m in cc['m'].values()); resumen['concejo_listas_otros'] = gen
resumen['concejo_curules_metodo'] = dict(st)
out = {'v': '2026-11-09', 'mun': {k: {kk: vv for kk, vv in m.items()} for k, m in MUN.items()}, 'capas': capas,
       'bancada26': {k: dict(v) for k, v in banc.items()}, 'porlista26': {k: dict(v) for k, v in porlista.items()}, 'nl': NLB, 'resumen': resumen}
pth = os.path.join(OUT, 'inventario.json')
json.dump(out, open(pth, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('inventario.json', round(os.path.getsize(pth) / 1e6, 2), 'MB')
print(json.dumps(resumen, ensure_ascii=False, indent=1))
for a in NLB['alcaldes']: print('  alcalde:', a['mun'], '·', a['dep'], '·', a['n'], '·', a['aval'], a['votos'])
for d in NLB['diputados']: print('  diputado:', d['dep'], d['cur'], '/', d['de'], d['lista'], d['nombres'])
for c in NLB['concejales'][:12]: print('  concejo:', c['mun'], c['dep'], c['cur'], '/', c['de'], c['lista'], f"{c['pct']:.1%}")
for e in NLB['ediles'][:25]: print('  edil:', e['loc'], e['cur'], '/', e['de'], e['nombres'])
for c in NLB['congreso']: print('  congreso:', c)
