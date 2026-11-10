#!/usr/bin/env python3
"""Tablero · inferencia ecológica Senado (mar-2026) -> 1V (may) -> 2V (jun), por PUESTO.

Unidad: puesto de votación (13.489 con Senado, presidencial y censo; sin exterior).
Cada puesto se describe como reparto de su CENSO: quien no votó es una categoría más,
así que la movilización entre elecciones se estima igual que el trasvase entre opciones.

Modelo (uno por estrato): Y = X·B, con B fila-estocástica y no negativa (mínimos
cuadrados restringidos, ponderado por censo). Estratos = región × urbano/rural, y en
Bogotá por estrato socioeconómico del puesto. Los flujos del estrato se ajustan por
raking a los dos márgenes reales (lo que sale de cada partido y lo que recibe cada
candidato son datos, no modelo). Incertidumbre: bootstrap por municipio (B réplicas).

Salida: Propuestas/nuevo-liberalismo/datos/tablero.json
"""
import json, os, csv, collections, sys, re
import numpy as np
from scipy.optimize import lsq_linear

RAIZ = os.path.join(os.path.dirname(__file__), '..', '..')
BD = os.path.join(RAIZ, 'Bases de datos')
OUT = os.path.join(RAIZ, 'Propuestas', 'nuevo-liberalismo', 'datos')
os.makedirs(OUT, exist_ok=True)
NB = int(os.environ.get('NB', '200'))
rng = np.random.default_rng(2027)

# ── categorías ──────────────────────────────────────────────────────────────
SEN = ['pacto', 'cd', 'liberal', 'alianza', 'conservador', 'u', 'cr', 'ahora', 'salvacion', 'frente', 'otros', 'blanco', 'novoto']
V1 = ['cepeda', 'abelardo', 'paloma', 'fajardo', 'otrosp', 'blanco', 'novoto']
V2 = ['cepeda', 'abelardo', 'blanco', 'novoto']
CAM_BOG = ['nl', 'miradig', 'pacto', 'cd', 'verde', 'salvacion', 'liberal', 'otros', 'blanco', 'novoto']

def grupo_sen(n):
    u = n.upper()
    if '[CIR' in u: return 'otros'
    if 'PACTO HIST' in u: return 'pacto'
    if 'CENTRO DEMOCR' in u: return 'cd'
    if 'LIBERAL COLOMBIANO' in u: return 'liberal'
    if 'ALIANZA POR COLOMBIA' in u: return 'alianza'
    if 'CONSERVADOR' in u: return 'conservador'
    if 'PARTIDO DE LA U' in u: return 'u'
    if 'CAMBIO RADICAL' in u: return 'cr'
    if 'AHORA COLOMBIA' in u: return 'ahora'
    if 'SALVACI' in u: return 'salvacion'
    if 'FRENTE AMPLIO' in u: return 'frente'
    return 'otros'

def grupo_cam_bog(n):
    u = n.upper()
    if '[CIR' in u: return 'otros'
    if 'NUEVO LIBERALISMO' in u: return 'nl'
    if 'MIRA' in u and 'DIGNIDAD' in u: return 'miradig'
    if 'PACTO HIST' in u: return 'pacto'
    if 'CENTRO DEMOCR' in u: return 'cd'
    if 'ALIANZA VERDE' in u: return 'verde'
    if 'SALVACI' in u: return 'salvacion'
    if 'LIBERAL COLOMBIANO' in u: return 'liberal'
    return 'otros'

REGION = {
    'Caribe': ['03', '05', '12', '13', '21', '28', '48', '56'],
    'Antioquia y Eje Cafetero': ['01', '09', '24', '26'],
    'Bogotá': ['16'],
    'Centro-Oriente': ['07', '15', '19', '25', '27', '29'],
    'Pacífico': ['11', '17', '23', '31'],
    'Llanos y Amazonía': ['40', '44', '46', '50', '52', '54', '60', '64', '68', '72'],
}
DEP_REG = {d: r for r, ds in REGION.items() for d in ds}

# ── carga ───────────────────────────────────────────────────────────────────
cong = json.load(open(os.path.join(BD, 'nuevo-liberalismo', 'congreso-puesto.json')))
pres = json.load(open(os.path.join(BD, 'nuevo-liberalismo', 'pres-puesto.json')))
censo = {k.replace('-', ''): v for k, v in json.load(open(os.path.join(BD, 'censos-puesto-2026.json')))['porPuesto'].items()}
estrato = {r['pcode']: r['estrato'] for r in csv.DictReader(open(os.path.join(BD, 'estrato-ciudades', 'puestos-estrato.csv'))) if r['ciudad'].startswith('Bogot')}
gs = [grupo_sen(n) for n in cong['partidos_sen']]
gc = [grupo_cam_bog(n) for n in cong['partidos_cam']]

filas = []
recorte = 0
for p, e in cong['puestos'].items():
    if p[:2] == '88' or p not in pres or p not in censo or p[:2] not in DEP_REG: continue
    s = collections.Counter()
    for i, v in e['s'].items(): s[gs[int(i)]] += v
    s['blanco'] = e['sb'] + e['sn']
    c = collections.Counter()
    for i, v in e['c'].items(): c[gc[int(i)]] += v
    c['blanco'] = e['cb'] + e['cn']
    a, b = pres[p]['v1'], pres[p]['v2']
    y1 = {'cepeda': a.get('cepeda', 0), 'abelardo': a.get('abelardo', 0), 'paloma': a.get('paloma', 0), 'fajardo': a.get('fajardo', 0),
          'otrosp': a.get('otros', 0), 'blanco': a.get('blanco', 0) + a.get('nulos', 0)}
    y2 = {'cepeda': b.get('cepeda', 0), 'abelardo': b.get('abelardo', 0), 'blanco': b.get('blanco', 0) + b.get('nulos', 0)}
    vs, vc, t1, t2 = sum(s.values()), sum(c.values()), sum(y1.values()), sum(y2.values())
    if min(vs, t1, t2) == 0: continue
    pot = censo[p]
    m = max(vs, vc, t1, t2)
    if m > pot: pot = m; recorte += 1          # puestos con más votantes que censo (traslados, jurados)
    if pot < 80: continue
    s['novoto'] = pot - vs; c['novoto'] = pot - vc; y1['novoto'] = pot - t1; y2['novoto'] = pot - t2
    if p[:2] == '16':
        es = estrato.get(p, '')
        st = 'Bogotá · estratos 1-2' if es in ('1', '2') else 'Bogotá · estrato 3' if es == '3' else 'Bogotá · estratos 4-6' if es in ('4', '5', '6') else 'Bogotá · sin estrato'
    else:
        st = DEP_REG[p[:2]] + (' · rural' if p[5:7] == '99' else ' · urbano')
    filas.append({'p': p, 'mun': p[:5], 'reg': DEP_REG[p[:2]], 'st': st, 'pot': pot,
                  's': [s.get(k, 0) for k in SEN], 'c': [c.get(k, 0) for k in CAM_BOG],
                  'y1': [y1[k] for k in V1], 'y2': [y2[k] for k in V2]})
print('puestos en el modelo', len(filas), '· censo', sum(f['pot'] for f in filas), '· con censo recortado', recorte, file=sys.stderr)

# ── motor ───────────────────────────────────────────────────────────────────
def ajusta(X, Y, w):
    """B fila-estocástica (R×C) que minimiza sum_u w_u ||y_u - x_u B||^2. X,Y en proporciones del censo."""
    R, C = X.shape[1], Y.shape[1]
    G = (X * w[:, None]).T @ X + 1e-9 * np.eye(R)          # X'WX
    L = np.linalg.cholesky(G)
    Z = np.linalg.solve(L, (X * w[:, None]).T @ Y)         # L^-1 X'W Y  (R×C)
    A = np.zeros((R * C + R, R * C)); b = np.zeros(R * C + R)
    for c in range(C):
        A[c * R:(c + 1) * R, c * R:(c + 1) * R] = L.T
        b[c * R:(c + 1) * R] = Z[:, c]
    lam = 1e3 * np.sqrt(np.trace(G) / R)
    for r in range(R):
        A[R * C + r, [c * R + r for c in range(C)]] = lam
        b[R * C + r] = lam
    sol = lsq_linear(A, b, bounds=(0, 1), method='bvls' if R * C <= 60 else 'trf', tol=1e-10, max_iter=400)
    B = sol.x.reshape(C, R).T
    B = np.clip(B, 0, None); B /= B.sum(1, keepdims=True)
    return B

def raking(F, filas_tot, cols_tot, it=200):
    """Ajusta la matriz de flujos a los dos márgenes reales."""
    F = F.copy() + 1e-12
    for _ in range(it):
        F *= (filas_tot / F.sum(1))[:, None]
        F *= (cols_tot / F.sum(0))[None, :]
    F *= (filas_tot / F.sum(1))[:, None]
    return F

def flujos(idx, kx, ky):
    """Flujos absolutos (personas) de un conjunto de puestos, ya con raking."""
    Xa = np.array([filas[i][kx] for i in idx], float); Ya = np.array([filas[i][ky] for i in idx], float)
    pot = np.array([filas[i]['pot'] for i in idx], float)
    B = ajusta(Xa / pot[:, None], Ya / pot[:, None], pot)
    return raking(B * Xa.sum(0)[:, None], Xa.sum(0), Ya.sum(0))

def cotas(idx, kx, ky):
    """Cotas deterministas de Duncan-Davis (lo que la aritmética permite, sin modelo), en personas."""
    Xa = np.array([filas[i][kx] for i in idx], float); Ya = np.array([filas[i][ky] for i in idx], float)
    pot = np.array([filas[i]['pot'] for i in idx], float)
    R, C = Xa.shape[1], Ya.shape[1]
    lo = np.zeros((R, C)); hi = np.zeros((R, C))
    for r in range(R):
        for c in range(C):
            lo[r, c] = np.maximum(0, Ya[:, c] - (pot - Xa[:, r])).sum()
            hi[r, c] = np.minimum(Xa[:, r], Ya[:, c]).sum()
    return lo, hi

estratos = collections.defaultdict(list)
for i, f in enumerate(filas): estratos[f['st']].append(i)
print({k: len(v) for k, v in estratos.items()}, file=sys.stderr)

MODELOS = {'s1': ('s', 'y1'), 's2': ('s', 'y2'), 'v12': ('y1', 'y2')}

def corre(muestra=None):
    """Devuelve {modelo: {estrato: F}}. muestra = dict estrato -> lista de índices (bootstrap)."""
    res = {}
    for m, (kx, ky) in MODELOS.items():
        res[m] = {}
        for st, idx in estratos.items():
            ii = muestra[st] if muestra else idx
            F = flujos(ii, kx, ky)
            if muestra:   # reescala al total real del estrato para que las réplicas sean comparables
                real = np.array([filas[i][kx] for i in idx], float).sum(0)
                F *= (real / np.maximum(F.sum(1), 1e-9))[:, None]
            res[m][st] = F
    return res

def remuestra():
    out = {}
    for st, idx in estratos.items():
        if st.startswith('Bogot'):
            out[st] = list(rng.choice(idx, len(idx), replace=True))
        else:
            por_mun = collections.defaultdict(list)
            for i in idx: por_mun[filas[i]['mun']].append(i)
            muns = list(por_mun)
            out[st] = [i for m in rng.choice(muns, len(muns), replace=True) for i in por_mun[m]]
    return out

base = corre()
reps = []
for b in range(NB):
    reps.append(corre(remuestra()))
    if b % 25 == 0: print('bootstrap', b, file=sys.stderr)

TERR = {'Colombia': list(estratos)}
for r in REGION: TERR[r] = [s for s in estratos if s.startswith(r)]
for s in estratos:
    if s.startswith('Bogot'): TERR[s] = [s]
# el país sin la capital: lo usa el selector General · Bogotá · Resto del país
TERR['Resto del país'] = [s for s in estratos if not s.startswith('Bogot')]

def junta(res, m, sts): return sum(res[m][s] for s in sts)

def empaca(m, sts, filas_k, cols_k):
    F = junta(base, m, sts)
    R = np.stack([junta(r, m, sts) for r in reps]) if reps else F[None]
    sh = R / np.maximum(R.sum(2, keepdims=True), 1e-9)
    lo, hi = np.percentile(sh, 5, 0), np.percentile(sh, 95, 0)
    idx = [i for s in sts for i in estratos[s]]
    dlo, dhi = cotas(idx, MODELOS[m][0], MODELOS[m][1])
    tot = F.sum(1)
    return {'filas': filas_k, 'cols': cols_k, 'tot_filas': [round(x) for x in tot], 'tot_cols': [round(x) for x in F.sum(0)],
            'flujo': [[round(x) for x in row] for row in F],
            'lo': [[round(float(x), 4) for x in row] for row in lo], 'hi': [[round(float(x), 4) for x in row] for row in hi],
            'cota_lo': [[round(float(x), 4) for x in row] for row in dlo / np.maximum(tot, 1)[:, None]],
            'cota_hi': [[round(float(x), 4) for x in row] for row in dhi / np.maximum(tot, 1)[:, None]]}

salida = {'v': '2026-11-09', 'nb': NB, 'puestos': len(filas), 'censo': int(sum(f['pot'] for f in filas)), 'territorios': {}}
for t, sts in TERR.items():
    if not sts: continue
    n = sum(len(estratos[s]) for s in sts)
    salida['territorios'][t] = {'puestos': n, 'censo': int(sum(filas[i]['pot'] for s in sts for i in estratos[s])),
                                's1': empaca('s1', sts, SEN, V1), 's2': empaca('s2', sts, SEN, V2), 'v12': empaca('v12', sts, V1, V2)}

# ── Bogotá con la lista propia del Nuevo Liberalismo a la Cámara ─────────────
bog = [s for s in estratos if s.startswith('Bogot')]
MODELOS.update({'c1': ('c', 'y1'), 'c2': ('c', 'y2')})
def corre_bog(muestra=None):
    res = {}
    for m in ('c1', 'c2'):
        kx, ky = MODELOS[m]; res[m] = {}
        for st in bog:
            idx = estratos[st]; ii = muestra[st] if muestra else idx
            F = flujos(ii, kx, ky)
            if muestra:
                real = np.array([filas[i][kx] for i in idx], float).sum(0)
                F *= (real / np.maximum(F.sum(1), 1e-9))[:, None]
            res[m][st] = F
    return res
base_b = corre_bog()
reps_b = [corre_bog({st: list(rng.choice(estratos[st], len(estratos[st]), replace=True)) for st in bog}) for _ in range(NB)]
def empaca_b(m, cols_k):
    global base, reps
    b0, r0 = base, reps
    base, reps = base_b, reps_b
    out = empaca(m, bog, CAM_BOG, cols_k)
    base, reps = b0, r0
    return out
salida['bogota_camara'] = {'c1': empaca_b('c1', V1), 'c2': empaca_b('c2', V2)}

# ── Descriptivo: dónde vive el voto del Nuevo Liberalismo en Bogotá ──────────
ib = [i for s in bog for i in estratos[s]]
def tabla(clave_grupo):
    g = collections.defaultdict(lambda: collections.Counter())
    for i in ib:
        f = filas[i]; k = clave_grupo(f)
        vc = sum(f['c'][:-1])
        g[k]['nl'] += f['c'][0]; g[k]['miradig'] += f['c'][1]; g[k]['cam'] += vc - f['c'][8]   # válidos por listas
        g[k]['cep1'] += f['y1'][0]; g[k]['abe1'] += f['y1'][1]; g[k]['pal1'] += f['y1'][2]; g[k]['faj1'] += f['y1'][3]
        g[k]['t1'] += sum(f['y1'][:5])
        g[k]['cep2'] += f['y2'][0]; g[k]['abe2'] += f['y2'][1]; g[k]['pot'] += f['pot']
        g[k]['vot1'] += sum(f['y1'][:-1]); g[k]['vot2'] += sum(f['y2'][:-1]); g[k]['vots'] += sum(f['s'][:-1]); g[k]['n'] += 1
    return {k: dict(v) for k, v in g.items()}
LOC = {'01': 'Usaquén', '02': 'Chapinero', '03': 'Santa Fe', '04': 'San Cristóbal', '05': 'Usme', '06': 'Tunjuelito', '07': 'Bosa', '08': 'Kennedy',
       '09': 'Fontibón', '10': 'Engativá', '11': 'Suba', '12': 'Barrios Unidos', '13': 'Teusaquillo', '14': 'Los Mártires', '15': 'Antonio Nariño',
       '16': 'Puente Aranda', '17': 'La Candelaria', '18': 'Rafael Uribe Uribe', '19': 'Ciudad Bolívar', '20': 'Sumapaz'}
salida['bogota_perfil'] = {
    'estrato': tabla(lambda f: estrato.get(f['p'], '') or 'sin dato'),
    'localidad': tabla(lambda f: LOC.get(f['p'][5:7], 'Puesto censo y cárceles')),
}
# correlación puesto a puesto (ponderada por censo) entre el % del partido a la Cámara y cada candidato de 1V
w = np.array([filas[i]['pot'] for i in ib], float)
def wcorr(a, b):
    ma, mb = np.average(a, weights=w), np.average(b, weights=w)
    return float(np.average((a - ma) * (b - mb), weights=w) / np.sqrt(np.average((a - ma) ** 2, weights=w) * np.average((b - mb) ** 2, weights=w)))
nlsh = np.array([filas[i]['c'][0] / max(1, sum(filas[i]['c'][:8])) for i in ib])
corr = {}
for j, k in enumerate(V1[:5]):
    corr[k] = round(wcorr(nlsh, np.array([filas[i]['y1'][j] / max(1, sum(filas[i]['y1'][:5])) for i in ib])), 3)
corr['cepeda_2v'] = round(wcorr(nlsh, np.array([filas[i]['y2'][0] / max(1, filas[i]['y2'][0] + filas[i]['y2'][1]) for i in ib])), 3)
salida['bogota_perfil']['corr_nl'] = corr
# puesto a puesto (para el diagrama de dispersión): [%NL de las listas a Cámara, %Paloma, %Abelardo, %Cepeda (1V), %Cepeda 2V, censo, estrato, localidad]
sc = []
for i in ib:
    f = filas[i]; vl = sum(f['c'][:8]); v1 = sum(f['y1'][:5]); v2 = f['y2'][0] + f['y2'][1]
    if vl < 50 or v1 < 50 or v2 < 50: continue
    sc.append([round(f['c'][0] / vl, 4), round(f['y1'][2] / v1, 4), round(f['y1'][1] / v1, 4), round(f['y1'][0] / v1, 4),
               round(f['y2'][0] / v2, 4), f['pot'], estrato.get(f['p'], '') or '-', f['p'][5:7]])
salida['bogota_puestos'] = sc


# ── Participación por territorio (dato, no modelo) ──────────────────────────
part = {}
for t, sts in TERR.items():
    idx = [i for s in sts for i in estratos[s]]
    pot = sum(filas[i]['pot'] for i in idx)
    part[t] = {'censo': int(pot), 'senado': int(sum(sum(filas[i]['s'][:-1]) for i in idx)),
               'v1': int(sum(sum(filas[i]['y1'][:-1]) for i in idx)), 'v2': int(sum(sum(filas[i]['y2'][:-1]) for i in idx))}
salida['participacion'] = part

# ── Dónde creció la participación (descriptivo, sin modelo) ─────────────────
# Puestos ordenados por cuánto creció su participación entre dos elecciones y partidos en quintiles
# de censo igual. Para cada quintil: qué pesaba en el Senado, qué ganó en 1V y 2V.
def quintiles(ka, kb, nombre):
    ordn = sorted(range(len(filas)), key=lambda i: (sum(filas[i][kb][:-1]) - sum(filas[i][ka][:-1])) / filas[i]['pot'])
    tot = sum(filas[i]['pot'] for i in ordn); acum = 0; q = [[] for _ in range(5)]
    for i in ordn:
        q[min(4, int(5 * acum / tot))].append(i); acum += filas[i]['pot']
    res = []
    for g in q:
        pot = sum(filas[i]['pot'] for i in g)
        sen = np.sum([filas[i]['s'] for i in g], 0).astype(float)
        y1 = np.sum([filas[i]['y1'] for i in g], 0).astype(float); y2 = np.sum([filas[i]['y2'] for i in g], 0).astype(float)
        va = sum(sum(filas[i][ka][:-1]) for i in g); vb = sum(sum(filas[i][kb][:-1]) for i in g)
        res.append({'puestos': len(g), 'censo': int(pot), 'part_a': round(va / pot, 4), 'part_b': round(vb / pot, 4),
                    'nuevos': int(vb - va),
                    'senado': [round(float(x) / max(1, sen[:-1].sum()), 4) for x in sen[:-1]],
                    'v1': [round(float(x) / max(1, y1[:5].sum()), 4) for x in y1[:5]],
                    'v2': [round(float(x) / max(1, y2[:2].sum()), 4) for x in y2[:2]]})
    return res
salida['quintiles'] = {'senado_1v': quintiles('s', 'y1', 'Senado a 1V'), 'v1_v2': quintiles('y1', 'y2', '1V a 2V')}

# ── Validación: apartar 20 % de municipios, ajustar con el resto, predecir lo apartado ──
def validacion(kx, ky, reps=5):
    maes, maes0 = [], []
    for _ in range(reps):
        err = np.zeros(len(filas[0][ky])); err0 = np.zeros(len(filas[0][ky])); wsum = 0.0
        for st, idx in estratos.items():
            muns = sorted({filas[i]['mun'] for i in idx})
            test_m = set(rng.choice(muns, max(1, len(muns) // 5), replace=False)) if len(muns) > 4 else set()
            te = [i for i in idx if filas[i]['mun'] in test_m]; tr = [i for i in idx if filas[i]['mun'] not in test_m]
            if len(te) < 3 or len(tr) < 20: continue
            Xt = np.array([filas[i][kx] for i in tr], float); Yt = np.array([filas[i][ky] for i in tr], float); pt = np.array([filas[i]['pot'] for i in tr], float)
            B = ajusta(Xt / pt[:, None], Yt / pt[:, None], pt)
            Xe = np.array([filas[i][kx] for i in te], float); Ye = np.array([filas[i][ky] for i in te], float); pe = np.array([filas[i]['pot'] for i in te], float)
            pred = (Xe / pe[:, None]) @ B; real = Ye / pe[:, None]
            base0 = (Yt.sum(0) / pt.sum())[None, :]                       # sin modelo: el reparto medio del estrato
            err += (np.abs(pred - real) * pe[:, None]).sum(0); err0 += (np.abs(base0 - real) * pe[:, None]).sum(0); wsum += pe.sum()
        maes.append(err / wsum); maes0.append(err0 / wsum)
    return {'mae_modelo': [round(float(x) * 100, 2) for x in np.mean(maes, 0)], 'mae_base': [round(float(x) * 100, 2) for x in np.mean(maes0, 0)]}
salida['validacion'] = {'s1': validacion('s', 'y1'), 's2': validacion('s', 'y2'), 'v12': validacion('y1', 'y2')}
salida['categorias'] = {'sen': SEN, 'v1': V1, 'v2': V2, 'cam_bog': CAM_BOG}

json.dump(salida, open(os.path.join(OUT, 'tablero.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
print('escrito', os.path.getsize(os.path.join(OUT, 'tablero.json')), 'bytes', file=sys.stderr)

# ── resumen legible ─────────────────────────────────────────────────────────
def imprime(t, m, filas_k, cols_k):
    d = salida['territorios'][t][m]
    print(f'\n== {t} · {m}  (% de cada fila; [IC90])')
    print(' ' * 13 + ''.join(f'{c:>17}' for c in cols_k))
    for i, r in enumerate(filas_k):
        tot = d['tot_filas'][i]
        print(f'{r:>12} ' + ''.join(f"{100 * d['flujo'][i][j] / max(tot, 1):6.1f} [{100 * d['lo'][i][j]:3.0f}-{100 * d['hi'][i][j]:3.0f}]" for j in range(len(cols_k))) + f'  {tot:>11,}')
imprime('Colombia', 's1', SEN, V1); imprime('Colombia', 's2', SEN, V2); imprime('Colombia', 'v12', V1, V2)
d = salida['bogota_camara']['c1']
print('\n== Bogotá · Cámara -> 1V')
for i, r in enumerate(CAM_BOG):
    print(f'{r:>12} ' + ''.join(f"{100 * d['flujo'][i][j] / max(d['tot_filas'][i], 1):6.1f} [{100 * d['lo'][i][j]:3.0f}-{100 * d['hi'][i][j]:3.0f}]" for j in range(len(V1))) + f"  {d['tot_filas'][i]:>10,}")
d = salida['bogota_camara']['c2']
print('\n== Bogotá · Cámara -> 2V')
for i, r in enumerate(CAM_BOG):
    print(f'{r:>12} ' + ''.join(f"{100 * d['flujo'][i][j] / max(d['tot_filas'][i], 1):6.1f} [{100 * d['lo'][i][j]:3.0f}-{100 * d['hi'][i][j]:3.0f}]" for j in range(len(V2))) + f"  {d['tot_filas'][i]:>10,}")
print('\ncorr NL', corr); print('participación', part['Colombia'])
