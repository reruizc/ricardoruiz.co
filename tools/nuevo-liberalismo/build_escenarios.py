#!/usr/bin/env python3
"""Módulo 04 · Reglas y escenarios 2027 -> Propuestas/nuevo-liberalismo/datos/escenarios.json

Entradas (todas locales):
  Bases de datos/nuevo-liberalismo/ter2023-agg.json        (tools/nuevo-liberalismo/agrega_ter2023.py:
                                                            Concejo 2023 por municipio, con voto de lista y blanco)
  Bases de datos/nuevo-liberalismo/raw/concejo-2023-index.json  (índice S3: nombre de cada municipio)
  Bases de datos/output_concejo_2023/resultados-concejo-2023.json (Bogotá por localidad)
  Bases de datos/DEPTOS_DECLARADOS/MMV_XXX_16_*.csv         (Cámara 2026 en Bogotá, mesa a mesa)
  Bases de datos/output_pacto_1v_2026/geo/mps/*.json        (código electoral -> DANE)
  Bases de datos/output_ponal/poblacion.json                (población DANE 2023)

Reparto: art. 263 C.P. con la MISMA lógica de vote-target.js (reconstructedCutoff):
umbral = 50 % del cuociente sobre válidos CON blanco; cifra repartidora sobre n-1
curules (la otra es la del estatuto de oposición, Ley 1909 de 2018 art. 25).
"""
import csv, glob, json, os, re, sys, unicodedata, collections

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(AQUI, '..', '..')
BD = os.path.join(REPO, 'Bases de datos')
NLD = os.path.join(BD, 'nuevo-liberalismo')
OUT = os.path.join(REPO, 'Propuestas', 'nuevo-liberalismo', 'datos', 'escenarios.json')


def norm(s):
    s = unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', re.sub(r'[^A-Z0-9 ]+', ' ', s.upper())).strip()


# ───────────────────────── reparto (espejo de vote-target.js) ─────────────────────────
def reparto(listas, blanco, curules, oposicion=True):
    """listas: {nombre: votos}. Devuelve dict con asignación, cifra, umbral."""
    rep = max(1, curules - (1 if oposicion else 0))
    validos = sum(listas.values())
    umbral = (validos + blanco) / curules / 2
    eleg = {k: v for k, v in listas.items() if v >= umbral} or dict(listas)
    q = []
    for k, v in eleg.items():
        for d in range(1, rep + 1):
            q.append((v / d, k))
    q.sort(key=lambda x: -x[0])
    asig = collections.Counter(k for _, k in q[:rep])
    cifra = q[min(rep, len(q)) - 1][0]
    return {'asig': dict(asig), 'cifra': cifra, 'umbral': umbral, 'repartidas': rep,
            'validos': validos, 'cuociente': (validos + blanco) / curules}


def curules_de(listas, blanco, curules, oposicion, nombre, votos):
    l = dict(listas); l[nombre] = votos
    return reparto(l, blanco, curules, oposicion)['asig'].get(nombre, 0)


def minimo_para(listas, blanco, curules, oposicion, nombre, k):
    """Menor votación de `nombre` (los demás fijos) con la que alcanza k curules."""
    if k <= 0: return 0
    lo, hi = 0, max(sum(listas.values()) * 3, 1000)
    if curules_de(listas, blanco, curules, oposicion, nombre, hi) < k: return None
    while lo < hi:
        m = (lo + hi) // 2
        if curules_de(listas, blanco, curules, oposicion, nombre, m) >= k: hi = m
        else: lo = m + 1
    return lo


# ───────────────────────── tamaño del concejo (Ley 136 de 1994, art. 22) ─────────────────────────
ESCALA = [(5000, 7), (10000, 9), (20000, 11), (50000, 13), (100000, 15), (250000, 17), (1000000, 19), (10**12, 21)]


def curules_por_poblacion(p):
    for tope, n in ESCALA:
        if p <= tope: return n


def cerca_de_umbral(p, tol=0.05):
    return any(abs(p - t) / t <= tol for t, _ in ESCALA[:-1])


# ───────────────────────── llaves de color ─────────────────────────
def llave(nombre):
    n = norm(nombre)
    if 'NUEVO LIBERALISMO' in n: return 'nl'
    if 'PACTO HISTORICO' in n: return 'pacto'
    if 'ALIANZA VERDE' in n: return 'verde'
    if 'CENTRO DEMOCRATICO' in n: return 'cd'
    if 'PARTIDO LIBERAL' in n: return 'liberal'
    if 'CAMBIO RADICAL' in n: return 'cr'
    if 'CONSERVADOR' in n: return 'conservador'
    if 'LARA' in n: return 'lara'
    if 'BOGOTA MAS FUERTE' in n: return 'bmf'
    if 'DIGNIDAD' in n: return 'dignidad'
    if 'FUERZA CIUDADANA' in n: return 'fuerza'
    if 'CREEMOS' in n: return 'creemos'
    if 'LIGA' in n: return 'liga'
    if 'AICO' in n: return 'aico'
    if 'SALVACION' in n: return 'salvacion'
    if 'MIRA' in n: return 'mira'
    return 'otros'


CORTO = {
    'nl': 'Nuevo Liberalismo – En Marcha', 'pacto': 'Pacto Histórico', 'verde': 'Alianza Verde',
    'cd': 'Centro Democrático', 'liberal': 'Partido Liberal', 'cr': 'Cambio Radical – MIRA – La U',
    'conservador': 'Conservador – Colombia Justa Libres', 'lara': 'LARA Bogotá', 'bmf': 'Bogotá Más Fuerte',
    'dignidad': 'Dignidad y Compromiso', 'fuerza': 'Fuerza Ciudadana', 'creemos': 'Creemos',
    'liga': 'Liga de Gobernantes', 'aico': 'AICO', 'otros': 'Esperanza Democrática',
}

# Composición con la que se instaló el Concejo el 1-ene-2024 (bogota.gov.co, leído el 9-nov-2026).
DECLARADA_BOG = {'verde': 8, 'nl': 8, 'pacto': 7, 'cd': 7, 'liberal': 6, 'cr': 4, 'lara': 2, 'conservador': 1, 'bmf': 1}

LOCALIDADES = {'01': 'Usaquén', '02': 'Chapinero', '03': 'Santa Fe', '04': 'San Cristóbal', '05': 'Usme',
               '06': 'Tunjuelito', '07': 'Bosa', '08': 'Kennedy', '09': 'Fontibón', '10': 'Engativá',
               '11': 'Suba', '12': 'Barrios Unidos', '13': 'Teusaquillo', '14': 'Los Mártires',
               '15': 'Antonio Nariño', '16': 'Puente Aranda', '17': 'La Candelaria', '18': 'Rafael Uribe Uribe',
               '19': 'Ciudad Bolívar', '20': 'Sumapaz'}

# ───────────────────────── calendario ─────────────────────────
# estado se calcula contra HOY. `fuente`: 'res' = Resolución 12338 de 2026 leída en prensa del 28-oct-2026
# (el comunicado de la Registraduría no abre sin navegador) · 'ley' = cálculo propio desde la norma.
HOY = '2026-11-09'
PRENSA = [
    ['El Nuevo Siglo, 28-oct-2026', 'https://www.elnuevosiglo.com.co/politica/registraduria-define-calendario-electoral-para-los-comicios-territoriales-de-2027'],
    ['Asuntos Legales, 28-oct-2026', 'https://www.asuntoslegales.com.co/actualidad/la-registraduria-nacional-establecio-calendario-para-las-elecciones-territoriales-de-2027-4513228'],
    ['MiOriente, 28-oct-2026', 'https://mioriente.com/nacionales/calendario-elecciones-regionales-2027/'],
    ['Infobae, 28-oct-2026', 'https://www.infobae.com/colombia/2026/10/28/este-sera-el-calendario-electoral-para-los-comicios-regionales-de-2027-se-elegiran-alcaldes-gobernadores-concejales-diputados-y-juntas-administradoras-locales/'],
]
CALENDARIO = [
    {'f': '2026-06-30', 'h': 'Doble militancia: último día para renunciar a la curul',
     'd': 'Quien fue elegido por un partido y quiera inscribirse en 2027 por otro debía renunciar a su curul doce meses antes del primer día de inscripciones. Los directivos, doce meses antes de ser inscritos.',
     'n': 'Ley 1475 de 2011, art. 2', 'src': 'ley', 'tipo': 'partido'},
    {'f': '2026-10-28', 'h': 'La Registraduría fija el calendario',
     'd': 'Resolución 12338 del 28 de octubre de 2026.', 'n': 'Resolución 12338 de 2026', 'src': 'res', 'tipo': 'oficial'},
    {'f': '2026-10-31', 'h': 'Inhabilidad por haber ejercido autoridad',
     'd': 'Queda inhabilitado para alcalde, concejal, gobernador o diputado quien haya ejercido autoridad como empleado público en el territorio dentro de los doce meses anteriores a la elección. Quien seguía en el cargo este día ya no puede aspirar. El mismo año cuenta para contratos con entidades públicas.',
     'n': 'Ley 617 de 2000, arts. 30, 33, 37 y 40', 'src': 'ley', 'tipo': 'candidato'},
    {'f': '2026-10-31', 'h': 'Abre la inscripción de cédulas y el registro de comités de firmas',
     'd': 'Quien cambió de residencia puede inscribir su cédula. Empieza la recolección de firmas de los grupos significativos de ciudadanos.',
     'n': 'Ley 1475 de 2011, arts. 28 y 49', 'src': 'res', 'tipo': 'oficial', 'hasta': '2027-08-31'},
    {'f': None, 'h': 'Consultas de los partidos', 'pend': True,
     'd': 'El CNE fija una fecha por año para consultas internas e interpartidistas. Para 2027 no encontramos resolución. En el ciclo anterior fueron el 4 de junio de 2023 (Resolución 0644 de 2023 del CNE).',
     'n': 'Ley 1475 de 2011, arts. 5 y 6', 'src': 'pend', 'tipo': 'partido'},
    {'f': '2027-06-30', 'h': 'Abre la inscripción de candidatos y listas',
     'd': 'Un mes de plazo. Ese día vence el registro de comités de firmas. Desde cuatro meses antes de la elección, alcaldes y gobernadores no pueden modificar la nómina ni firmar convenios interadministrativos.',
     'n': 'Ley 1475 de 2011, art. 30 · Ley 996 de 2005, art. 38', 'src': 'res', 'tipo': 'candidato'},
    {'f': '2027-07-31', 'h': 'Cierra la inscripción de candidatos',
     'd': 'Último día para inscribir listas, coaliciones y firmas. Empieza la propaganda en espacio público (tres meses antes).',
     'n': 'Ley 1475 de 2011, arts. 30 y 35', 'src': 'res', 'tipo': 'candidato',
     'ojo': 'Una de las cuatro notas pone el inicio de la propaganda en espacio público el 30 de junio.'},
    {'f': '2027-08-02', 'f2': '2027-08-06', 'h': 'Modificación de listas',
     'd': 'Cinco días hábiles para reemplazar a quien renuncie o no acepte la candidatura.',
     'n': 'Ley 1475 de 2011, art. 31', 'src': 'res', 'tipo': 'candidato'},
    {'f': '2027-08-05', 'h': 'Propaganda en medios de comunicación',
     'd': 'Tres notas de prensa dan esta fecha.', 'n': 'Ley 1475 de 2011, art. 35', 'src': 'res', 'tipo': 'candidato',
     'ojo': 'El art. 35 habla de sesenta días antes de la votación, que sería el 1 de septiembre. Por verificar en el texto de la resolución.'},
    {'f': '2027-08-08', 'h': 'Lista oficial de candidatos inscritos',
     'd': 'La Registraduría publica quién quedó inscrito.', 'n': 'Ley 1475 de 2011, art. 33', 'src': 'res', 'tipo': 'oficial'},
    {'f': '2027-08-31', 'h': 'Cierra la inscripción de cédulas',
     'd': 'Dos meses antes de la elección.', 'n': 'Ley 1475 de 2011, art. 49', 'src': 'res', 'tipo': 'oficial'},
    {'f': '2027-09-30', 'h': 'Último cambio por revocatoria o inhabilidad',
     'd': 'Hasta un mes antes se puede reemplazar a un candidato al que le revoquen la inscripción o le sobrevenga una inhabilidad.',
     'n': 'Ley 1475 de 2011, art. 31', 'src': 'res', 'tipo': 'candidato'},
    {'f': '2027-10-16', 'h': 'Jurados de votación', 'd': 'Último día para sortear y publicar las listas de jurados.',
     'n': 'Resolución 12338 de 2026', 'src': 'res', 'tipo': 'oficial'},
    {'f': '2027-10-31', 'h': 'Elección', 'd': 'Gobernadores, alcaldes, diputados, concejales y ediles. Periodo 2028-2031.',
     'n': 'Ley 163 de 1994, art. 1', 'src': 'res', 'tipo': 'jornada'},
    {'f': '2027-11-02', 'h': 'Escrutinios generales', 'd': 'Los municipales empiezan el mismo domingo a las 4 de la tarde.',
     'n': 'Resolución 12338 de 2026', 'src': 'res', 'tipo': 'oficial'},
]
for c in CALENDARIO:
    c['paso'] = bool(c['f'] and c['f'] <= HOY)

# ───────────────────────── 1. Concejo de Bogotá 2023 ─────────────────────────
ter = json.load(open(os.path.join(NLD, 'ter2023-agg.json')))
bog = ter['concejo']['16-001']
listas_bog, detalle = {}, []
for par, e in bog['p'].items():
    cands = sorted(e['c'].values(), key=lambda x: -x[1])
    personal = sum(v for _, v in cands)
    total = e['l'] + personal
    listas_bog[e['n']] = total
    detalle.append({'nombre': e['n'], 'k': llave(e['n']), 'total': total, 'lista': e['l'], 'personal': personal,
                    'cands': cands, 'cerrada': personal < 0.15 * total})
R = reparto(listas_bog, bog['b'], 45, True)
R45 = reparto(listas_bog, bog['b'], 45, False)
assert sum(listas_bog.values()) == 2437317, sum(listas_bog.values())
assert bog['b'] == 368831
assert round(R['cifra']) == 49481, R['cifra']                       # CLAUDE.md, corrección del 19-oct-2026
asig_k = {llave(n): k for n, k in R['asig'].items()}
assert asig_k == DECLARADA_BOG, (asig_k, DECLARADA_BOG)              # 44 curules, igual a la instalada el 1-ene-2024
assert sum(R['asig'].values()) == 44

bog_listas = []
for d in sorted(detalle, key=lambda x: -x['total']):
    k = R['asig'].get(d['nombre'], 0)
    ult = None
    if k and not d['cerrada'] and len(d['cands']) >= k:
        ult = {'nombre': d['cands'][k - 1][0].title(), 'votos': d['cands'][k - 1][1]}
    bog_listas.append({'nombre': CORTO.get(d['k'], d['nombre'].title()), 'oficial': d['nombre'], 'k': d['k'],
                       'total': d['total'], 'lista': d['lista'], 'personal': d['personal'], 'cerrada': d['cerrada'],
                       'curules': k, 'curules45': R45['asig'].get(d['nombre'], 0), 'ultimo': ult,
                       'cabeza': ({'nombre': d['cands'][0][0].title(), 'votos': d['cands'][0][1]} if d['cands'] and not d['cerrada'] else None),
                       'pasa_umbral': d['total'] >= R['umbral']})
NLB = next(x for x in bog_listas if x['k'] == 'nl')
VB = sum(listas_bog.values()) + bog['b']          # válidos con blanco
assert NLB['total'] == 404399 and NLB['curules'] == 8
logo = sorted(((x['lista'] / x['total'], x['nombre']) for x in bog_listas if not x['cerrada'] and x['curules']), reverse=True)
assert logo[0][1] == NLB['nombre'], logo                          # el voto «solo logo» más alto entre las listas abiertas con curul

# ───────────────────────── 2. Cámara 2026 en Bogotá (lista propia) ─────────────────────────
cam_tot = collections.Counter(); cam_zona = collections.defaultdict(collections.Counter)
for f in glob.glob(os.path.join(BD, 'DEPTOS_DECLARADOS', 'MMV_XXX_16_*.csv')):
    with open(f, encoding='utf-8-sig', newline='') as fh:
        for r in csv.DictReader(fh, delimiter=';'):
            if not r['CORNOMBRE'].strip().upper().startswith(('CAMARA', 'CÁMARA')): continue
            if r['CIR'].strip() != '1': continue                 # solo la circunscripción territorial
            try: v = int(r['VOTOS'])
            except Exception: continue
            can = r['CAN'].strip()
            if can in ('997', '998'): continue
            key = 'BLANCO' if can == '996' else r['PARNOMBRE'].strip()
            cam_tot[key] += v; cam_zona[r['ZONA'].zfill(2)][key] += v
NLCAM = 'PARTIDO NUEVO LIBERALISMO'
assert cam_tot[NLCAM] == 105616, cam_tot[NLCAM]
cam_den = sum(cam_tot.values())                    # listas + blanco
cam_listas = sorted(((v, k) for k, v in cam_tot.items() if k != 'BLANCO'), reverse=True)

# ───────────────────────── 3. Bogotá por localidad ─────────────────────────
resb = json.load(open(os.path.join(BD, 'output_concejo_2023', 'resultados-concejo-2023.json')))['data']['16-001']['comunas']
locs = []
for z, nom in LOCALIDADES.items():
    c = resb.get(z)
    if not c: continue
    v23 = sum(v for n, v in c['partidos'] if 'NUEVO LIBERALISMO' in norm(n))
    den23 = c['validos'] + c['blanco']
    cz = cam_zona.get(z, {})
    v26 = cz.get(NLCAM, 0); den26 = sum(cz.values())
    locs.append({'z': z, 'n': nom, 'v23': v23, 'd23': den23, 'v26': v26, 'd26': den26})
assert len(locs) == 20
cob23 = sum(l['v23'] for l in locs) / NLB['total']; cob26 = sum(l['v26'] for l in locs) / cam_tot[NLCAM]
assert cob23 > 0.97 and cob26 > 0.9, (cob23, cob26)

# ───────────────────────── 4. Escenarios del simulador ─────────────────────────
otros = {x['oficial']: x['total'] for x in bog_listas if x['k'] != 'nl'}
S0 = NLB['total'] / VB


def simula(share, oposicion=True):
    """NL con `share` de los válidos con blanco; los demás (y el blanco) en la proporción de 2023."""
    f = (1 - share) / (1 - S0)
    l = {k: v * f for k, v in otros.items()}
    l['NL'] = share * VB
    r = reparto(l, bog['b'] * f, 45, oposicion)
    return r['asig'].get('NL', 0), r


piso = cam_tot[NLCAM] / cam_den
base = NLB['personal'] / VB
techo = S0
esc = {}
for nom, s in (('piso', piso), ('base', base), ('techo', techo)):
    k, r = simula(s)
    esc[nom] = {'pct': s, 'votos': round(s * VB), 'curules': k, 'cifra': round(r['cifra']), 'curules_sin_opos': simula(s, False)[0]}
assert esc['techo']['curules'] == 8
# tabla del simulador: menor % con el que se alcanza cada curul (con y sin curul de oposición)
escalones = {}
for opos in (True, False):
    arr = []
    for k in range(1, 13):
        lo, hi = 0.0, 0.5
        for _ in range(40):
            m = (lo + hi) / 2
            if simula(m, opos)[0] >= k: hi = m
            else: lo = m
        arr.append(round(hi, 5))
    escalones['con' if opos else 'sin'] = arr

# ───────────────────────── 5. Fuera de Bogotá ─────────────────────────
idx = json.load(open(os.path.join(NLD, 'raw', 'concejo-2023-index.json')))
nombre_mun = {}
for c in idx['candidatos']:
    m = re.match(r'CONC2023-(\d+)-(\d+)-', c['slug'])
    if m: nombre_mun.setdefault(m.group(1).zfill(2) + '-' + m.group(2).zfill(3), c['circunscripcion'])
dane = {}
for f in glob.glob(os.path.join(BD, 'output_pacto_1v_2026', 'geo', 'mps', '*.json')):
    g = json.load(open(f))
    if not isinstance(g, dict): continue          # hay un archivo que no es FeatureCollection
    for ft in g.get('features', []):
        p = ft['properties']
        dane[str(p['dep_electoral']).zfill(2) + '-' + str(p['mun_elec']).zfill(3)] = p['mpio_cdpmp']
pob = json.load(open(os.path.join(BD, 'output_ponal', 'poblacion.json')))
i23 = pob['anios'].index(2023)
CAPITALES_NO = {'25001'}       # Agua de Dios: el 001 de Cundinamarca no es capital
# Concejos cuyo tamaño conocemos y no coincide con la proyección DANE 2023 (la Registraduría fija el número
# con la población certificada): Cartagena elige 19.
CURULES_FIJAS = {'05-001': 19}

fuera, sin_pob = [], 0
for key, m in ter['concejo'].items():
    if key == '16-001': continue
    nl = [(par, e) for par, e in m['p'].items() if 'NUEVO LIBERALISMO' in norm(e['n'])]
    if not nl: continue
    listas = {}; maxlen = 0
    for par, e in m['p'].items():
        listas[par] = e['l'] + sum(v for _, v in e['c'].values()); maxlen = max(maxlen, len(e['c']))
    cd = dane.get(key); p = pob['muns'].get(cd, {}).get('p', [None] * 9)[i23] if cd else None
    if p is None: sin_pob += 1
    n_pob = curules_por_poblacion(p) if p else None
    n = n_pob or min((x for _, x in ESCALA if x >= maxlen), default=maxlen)
    dudas = []
    if key in CURULES_FIJAS: n = CURULES_FIJAS[key]
    elif n_pob is None: dudas.append('sin población DANE: curules por la lista más larga')
    elif maxlen > n_pob:
        n = min((x for _, x in ESCALA if x >= maxlen), default=maxlen); dudas.append('hay listas más largas que la escala por población')
    elif cerca_de_umbral(p): dudas.append('población a menos de 5 % de un corte de la escala')
    r = reparto(listas, m['b'], n, True)
    den = sum(listas.values()) + m['b']
    nombre = nombre_mun.get(key, key); mm = re.match(r'(.+?)\s*\((.+)\)\s*$', nombre)
    for par, e in nl:
        v = listas[par]; k = r['asig'].get(par, 0)
        rest = {a: b for a, b in listas.items() if a != par}
        sig = minimo_para(rest, m['b'], n, True, par, k + 1)
        act = minimo_para(rest, m['b'], n, True, par, k) if k else 0
        cands = sorted(e['c'].values(), key=lambda x: -x[1])
        fuera.append({'key': key, 'mun': (mm.group(1) if mm else nombre).title(), 'dep': (mm.group(2) if mm else '').title(),
                      'lista': e['n'], 'sola': norm(e['n']) == 'PARTIDO NUEVO LIBERALISMO',
                      'votos': v, 'pct': v / den if den else 0, 'n': n, 'k': k,
                      'falta': (sig - v) if sig is not None else None, 'colchon': (v - act) if k else None,
                      'cifra': round(r['cifra']), 'umbral': round(r['umbral']), 'pasa': v >= r['umbral'],
                      'cabeza': cands[0][1] if cands else 0, 'pob': p, 'capital': bool(cd and cd.endswith('001') and cd not in CAPITALES_NO),
                      'dudas': dudas})
fuera.sort(key=lambda x: -x['votos'])
assert len(fuera) >= 380, len(fuera)
res_fuera = {'listas': len(fuera), 'municipios': len({x['key'] for x in fuera}), 'votos': sum(x['votos'] for x in fuera),
             'con_curul': sum(1 for x in fuera if x['k']), 'curules': sum(x['k'] for x in fuera),
             'solas': sum(1 for x in fuera if x['sola']), 'coalicion': sum(1 for x in fuera if not x['sola']),
             'a_500': sum(1 for x in fuera if x['falta'] is not None and x['falta'] <= 500),
             'sin_curul_a_300': sum(1 for x in fuera if not x['k'] and x['falta'] is not None and x['falta'] <= 300),
             'con_dudas': sum(1 for x in fuera if x['dudas'])}

# ───────────────────────── salida ─────────────────────────
out = {
    'v': HOY, 'hoy': HOY,
    'calendario': {'resolucion': 'Resolución 12338 del 28 de octubre de 2026 (Registraduría)', 'prensa': PRENSA, 'hitos': CALENDARIO},
    'bogota': {
        'curules': 45, 'repartidas': 44, 'oposicion': 'Juan Daniel Oviedo', 'blanco': bog['b'], 'nulos': bog['nu'],
        'votos_listas': sum(listas_bog.values()), 'validos_con_blanco': VB,
        'cuociente': round(R['cuociente']), 'umbral': round(R['umbral']), 'cifra': round(R['cifra']), 'cifra45': round(R45['cifra']),
        'listas': bog_listas,
        'declarada': {'fuente': 'Alcaldía de Bogotá, «Así quedó conformado el Concejo de Bogotá para el periodo de 2024-2027», 1-ene-2024',
                      'url': 'https://bogota.gov.co/mi-ciudad/gobierno/como-quedo-conformado-el-concejo-de-bogota-del-periodo-2024-2027',
                      'curules': DECLARADA_BOG, 'coincide': True},
    },
    'comparacion': {
        'concejo2023': {'votos': NLB['total'], 'den': VB, 'pct': S0, 'pct_listas': NLB['total'] / sum(listas_bog.values()),
                        'lista': NLB['lista'], 'personal': NLB['personal'], 'nombre': NLB['oficial']},
        'camara2026': {'votos': cam_tot[NLCAM], 'den': cam_den, 'pct': piso, 'blanco': cam_tot['BLANCO'],
                       'puesto': 1 + [k for _, k in cam_listas].index(NLCAM), 'listas': [[k, v] for v, k in cam_listas[:10]]},
        'localidades': locs, 'cobertura': {'c23': cob23, 'c26': cob26},
        'logo': [{'nombre': n, 'pct': p} for p, n in logo],
    },
    'escenarios': esc, 'escalones': escalones,
    'sim': {'VB': VB, 'S0': S0, 'blanco': bog['b'], 'otros': [{'nombre': x['nombre'], 'k': x['k'], 'total': x['total']} for x in bog_listas if x['k'] != 'nl']},
    'fuera': {'resumen': res_fuera, 'filas': fuera, 'escala': [[t if t < 10**11 else None, n] for t, n in ESCALA]},
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
txt = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
open(OUT, 'w', encoding='utf-8').write(txt)
# mismo envoltorio que tools/nuevo-liberalismo/empaqueta.py: la página abre con doble clic, sin servidor
open(OUT[:-5] + '.js', 'w', encoding='utf-8').write(f"window.NLD=window.NLD||{{}};window.NLD['escenarios']={txt};\n")

print('Bogotá 2023 · cifra', round(R['cifra']), '· umbral', round(R['umbral']), '· válidos con blanco', VB)
for x in bog_listas[:10]:
    print(f"  {x['total']:>8,} {x['curules']:>2} {x['nombre'][:34]:34} logo {x['lista'] / x['total']:.1%}", x['ultimo'] or ('cerrada' if x['cerrada'] else ''))
print('Concejo 2023', f"{S0:.2%}", '· Cámara 2026', f"{piso:.2%}", f"(den {cam_den:,}, puesto {out['comparacion']['camara2026']['puesto']})")
print('escenarios', json.dumps(esc))
print('escalones con oposición', [f'{x:.2%}' for x in escalones['con']])
print('fuera de Bogotá', res_fuera, '· sin población', sin_pob)
for x in fuera[:12]:
    print(f"  {x['mun'][:22]:22} {x['votos']:>6,} {x['pct']:.1%} n={x['n']} k={x['k']} falta={x['falta']} {x['lista'][:40]} {x['dudas']}")
print('cobertura localidades', round(cob23, 4), round(cob26, 4), '·', os.path.getsize(OUT) // 1024, 'KB')
