#!/usr/bin/env python3
"""construir-censo-2026.py — quién PUEDE votar en cada puesto, con sexo y edad.

Reemplaza tres fuentes del perfil del votante (sep-2026):
  · el censo por puesto de PUESTOS_GEOREF (un corte viejo: 38,6 M, le faltan
    2,65 M de electores);
  · CENSO_EDAD_PUESTO.json (edad PROYECTADA a 2026 desde los votantes de 2022:
    se equivocaba 5 a 7 puntos por banda y puesto contra el censo real);
  · PERFIL_SEXO_EDAD_PUESTO.json (sufragantes de 2022).

Fuente: el censo electoral por puesto que publica la Registraduría detrás del
tablero «Consulta los censos históricos» ({año}_datos_censo-electoral-min.json,
en `Bases de datos/censos-registraduria/`). Se usa el corte del CONGRESO 2026,
que suma exactamente 41.287.084 —la cifra oficial—. El exterior (depto 88) no
entra: el producto no lo usa.

⚠️ Esa fuente trae sexo y edad por SEPARADO, nunca cruzados. Los seis perfiles
de la página del electorado (mujer joven, hombre mayor…) necesitan el cruce,
así que se ESTIMA con raking (ajuste proporcional iterativo): la semilla es el
cruce de los sufragantes de 2022 del mismo puesto (Edadygenero) y los márgenes
son el sexo y la edad del censo de 2026. La forma del cruce viene de 2022; los
totales, del censo. Sin semilla propia se usa la del municipio y, si tampoco
hay, la nacional.

⚠️ «Bloque de edad»: en ~870 puestos (la mayoría en ciudades grandes) un solo
rango de edad pesa 2,5 veces o más lo que pesa en su municipio. Así viene el
censo —así está asignado ese puesto—, no es un cálculo nuestro, pero ahí la
edad describe a quienes quedaron inscritos más que al barrio. Se marca el
rango para que la página lo declare.

⚠️ Comparación con 2023 (censo de las territoriales): el código de puesto NO es
estable entre elecciones (se renumera). Se cruza por código Y nombre; si el
código no calza, por nombre único dentro del municipio. Lo que no calza es
puesto nuevo, y los de 2023 que no aparecen, cerrados.

Salida (CENSO_PUESTO_2026.json):
  { version, fuente, total, bandas:[10], perfiles:{sexos, edades},
    puestos: { code9: [potencial, mujeres, hombres, b0..b9, h1,h2,h3, m1,m2,m3,
                       bloque(-1 o índice de banda), censo2023(-1 si nuevo), cruce2023(0 nuevo·1 código·2 nombre)] },
    cerrados2023: { mun5: [puestos, censo] } }

Uso: python3 tools/candidato-360/perfil/construir-censo-2026.py [--salida=X.json]
"""
import csv, json, os, re, sys, unicodedata
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
D = os.path.join(ROOT, 'Bases de datos', 'censos-registraduria')
SEMILLA = os.path.join(ROOT, 'Bases de datos', 'output_edad_1v', 'cache', 'p1v-2022.csv')
SALIDA = next((a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--salida=')),
              os.path.join(ROOT, 'Bases de datos', 'output_censo_2026', 'CENSO_PUESTO_2026.json'))
OFICIAL = 41287084

BANDAS = ['18-20', '21-25', '26-30', '31-35', '36-40', '41-45', '46-50', '51-55', '56-60', 'mas de 60']
ROTULOS = ['18-20', '21-25', '26-30', '31-35', '36-40', '41-45', '46-50', '51-55', '56-60', '61+']
GRUPOS = [[0, 1, 2], [3, 4, 5, 6, 7, 8], [9]]           # 18-30 · 31-60 · 61+
BLOQUE_RAZON, BLOQUE_MIN = 2.5, 400


def carga(anio, tipo):
    with open(os.path.join(D, f'{anio}_datos_censo-electoral-min.json'), encoding='utf-8') as f:
        return {r['cod_depto'] + r['cod_mun'] + r['zona'] + r['cod_puesto']: r
                for r in json.load(f)['data'] if r['tipo_eleccion'] == tipo}


todo26 = carga(2026, 'CONGRESO DE LA REPÚBLICA')
total_con_exterior = sum(r['potencial_electoral'] for r in todo26.values())
if total_con_exterior != OFICIAL:
    raise SystemExit(f'El censo del Congreso 2026 suma {total_con_exterior:,} y el oficial es {OFICIAL:,}: no se sigue.')
c26 = {k: r for k, r in todo26.items() if r['cod_depto'] != '88'}
t23 = {k: r for k, r in carga(2023, 'AUTORIDADES TERRITORIALES').items() if r['cod_depto'] != '88'}

# ── Semilla del cruce sexo × edad: sufragantes 2022 (Edadygenero) ──────────
BOG_LOC = {'USAQUEN': '01', 'CHAPINERO': '02', 'SANTA FE': '03', 'SAN CRISTOBAL': '04', 'USME': '05', 'TUNJUELITO': '06',
           'BOSA': '07', 'KENNEDY': '08', 'FONTIBON': '09', 'ENGATIVA': '10', 'SUBA': '11', 'BARRIOS UNIDOS': '12',
           'TEUSAQUILLO': '13', 'LOS MARTIRES': '14', 'ANTONIO NARINO': '15', 'PUENTE ARANDA': '16', 'LA CANDELARIA': '17',
           'CANDELARIA': '17', 'RAFAEL URIBE URIBE': '18', 'RAFAEL URIBE': '18', 'CIUDAD BOLIVAR': '19', 'SUMAPAZ': '20',
           'CORFERIAS': '90', 'CARCELES': '98'}


def nrm(s):
    return unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode().upper().strip()


def zf(s, w):
    s = str(s or '').strip()
    return s.zfill(w) if s.isdigit() else s


H = [['Hombres entre 18 a 20 años', 'Hombres entre 21 a 25 años', 'Hombres entre 26 a 30 años'],
     ['Hombres entre 31 a 35 años', 'Hombres entre 36 a 40 años', 'Hombres entre 41 a 45 años',
      'Hombres entre 46 a 50 años', 'Hombres entre 51 a 55 años', 'Hombres entre 56 a 60 años'],
     ['Hombres Mayores a 60 años']]
M = [[c.replace('Hombres entre', 'Mujeres entre').replace('Hombres Mayores', 'Mujeres mayores') for c in g] for g in H]
semilla = defaultdict(lambda: [0.0] * 6)
with open(SEMILLA, newline='', encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        z = str(r['Cód. Comuna / Localidad']).strip()
        zona = zf(z, 2) if z.isdigit() else BOG_LOC.get(nrm(z))
        if not zona:
            continue
        code = zf(r['Cód. Depto'], 2) + zf(r['Cód. Municipio'], 3) + zona + zf(r['Cód. Puesto de Votación'], 2)
        acc = semilla[code]
        for i in range(3):
            acc[i] += sum(float(r[c] or 0) for c in H[i])
            acc[3 + i] += sum(float(r[c] or 0) for c in M[i])
sem_mun, sem_nac = defaultdict(lambda: [0.0] * 6), [0.0] * 6
for k, v in semilla.items():
    for i in range(6):
        sem_mun[k[:5]][i] += v[i]; sem_nac[i] += v[i]


def raking(seed, filas, cols, vueltas=60):
    """2 × 3: filas = [hombres, mujeres], columnas = los tres grupos de edad."""
    x = [max(s, 1e-6) for s in seed]
    for _ in range(vueltas):
        for f in range(2):
            s = sum(x[f * 3:f * 3 + 3]); k = filas[f] / s if s else 0
            for j in range(3): x[f * 3 + j] *= k
        for j in range(3):
            s = x[j] + x[3 + j]; k = cols[j] / s if s else 0
            x[j] *= k; x[3 + j] *= k
    return x


def redondea(x, total):
    """Enteros que suman `total` (resto mayor)."""
    base = [int(v) for v in x]
    faltan = total - sum(base)
    for i in sorted(range(len(x)), key=lambda i: x[i] - base[i], reverse=True)[:max(0, faltan)]:
        base[i] += 1
    return base


# ── Bloques de edad: contra el perfil de su municipio ───────────────────────
mun_bandas = defaultdict(lambda: [0] * 10)
for k, r in c26.items():
    for i, b in enumerate(BANDAS): mun_bandas[k[:5]][i] += r['rango_etario'][b]


def bloque(k, v):
    t = sum(v); m = mun_bandas[k[:5]]; mt = sum(m)
    if t < BLOQUE_MIN or not mt: return -1
    mejor, razon = -1, 0
    for i in range(1, 9):                          # las bandas cerradas de 5 años
        sm = m[i] / mt
        if sm and v[i] >= BLOQUE_MIN and (v[i] / t) / sm >= BLOQUE_RAZON and (v[i] / t) / sm > razon:
            mejor, razon = i, (v[i] / t) / sm
    return mejor


# ── Cruce con 2023 ─────────────────────────────────────────────────────────
def palabras(s):
    return set(re.sub(r'[^A-Z0-9 ]', ' ', nrm(s)).split()) - {'DE', 'LA', 'EL', 'LOS', 'LAS', 'Y', 'NO', 'SEDE', 'IE', 'I', 'E'}


def mismo(a, b):
    x, y = palabras(a), palabras(b)
    return bool(x and y) and len(x & y) / min(len(x), len(y)) >= .5


usados, cruce = set(), {}
for k, r in c26.items():
    a = t23.get(k)
    if a and mismo(r['puesto_votacion'], a['puesto_votacion']):
        cruce[k] = (a['potencial_electoral'], 1); usados.add(k)
por_nombre = defaultdict(list)
for k, a in t23.items():
    if k not in usados: por_nombre[(k[:5], ' '.join(sorted(palabras(a['puesto_votacion']))))].append(k)
for k, r in c26.items():
    if k in cruce: continue
    cand = por_nombre.get((k[:5], ' '.join(sorted(palabras(r['puesto_votacion'])))), [])
    if len(cand) == 1 and cand[0] not in usados:
        cruce[k] = (t23[cand[0]]['potencial_electoral'], 2); usados.add(cand[0])
cerrados = defaultdict(lambda: [0, 0])
for k, a in t23.items():
    if k not in usados:
        cerrados[k[:5]][0] += 1; cerrados[k[:5]][1] += a['potencial_electoral']

# ── Salida ─────────────────────────────────────────────────────────────────
puestos, sin_semilla, n_bloque = {}, 0, 0
for k, r in c26.items():
    v = [r['rango_etario'][b] for b in BANDAS]
    muj, hom, pot = r['sexo']['mujeres'], r['sexo']['hombres'], r['potencial_electoral']
    g = [sum(v[i] for i in grupo) for grupo in GRUPOS]
    tg = sum(g)
    cols = [x * (hom + muj) / tg for x in g] if tg else [0, 0, 0]
    seed = semilla.get(k)
    if not seed or sum(seed) < 30:
        sin_semilla += 1
        seed = sem_mun.get(k[:5]) if sum(sem_mun.get(k[:5], [0])) >= 30 else sem_nac
    celdas = redondea(raking(seed, [hom, muj], cols), hom + muj) if hom + muj else [0] * 6
    b = bloque(k, v)
    n_bloque += b >= 0
    p23, tipo = cruce.get(k, (-1, 0))
    puestos[k] = [pot, muj, hom] + v + celdas + [b, p23, tipo]

total = sum(p[0] for p in puestos.values())
salida = {
    'version': __import__('datetime').date.today().isoformat(),
    'fuente': 'Censo electoral por puesto del Congreso 2026 (Registraduría, «Consulta los censos históricos»): sexo y edad observados. '
              'El cruce sexo × edad se estima con raking: forma de los sufragantes de 2022 del puesto, totales del censo de 2026. '
              'Comparación con el censo de las territoriales de 2023.',
    'total': total, 'bandas': ROTULOS,
    'perfiles': {'sexos': ['H', 'M'], 'edades': ['18-30', '31-60', '61+']},
    'campos': ['potencial', 'mujeres', 'hombres'] + [f'b{r}' for r in ROTULOS] + ['h18-30', 'h31-60', 'h61+', 'm18-30', 'm31-60', 'm61+', 'bloque', 'censo2023', 'cruce2023'],
    'puestos': puestos,
    'cerrados2023': {k: v for k, v in cerrados.items()},
}
os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
with open(SALIDA, 'w', encoding='utf-8') as f:
    json.dump(salida, f, ensure_ascii=False, separators=(',', ':'))

por_tipo = defaultdict(int)
for p in puestos.values(): por_tipo[p[-1]] += 1
print(f'{len(puestos):,} puestos · {total:,} electores (sin exterior) · {os.path.getsize(SALIDA)/1e6:.2f} MB → {SALIDA}')
print(f'cruce sexo×edad: {len(puestos)-sin_semilla:,} con semilla propia, {sin_semilla:,} con la del municipio o la nacional')
print(f'bloques de edad: {n_bloque:,} puestos')
print(f'2023: {por_tipo[1]:,} por código · {por_tipo[2]:,} por nombre · {por_tipo[0]:,} nuevos · '
      f'{sum(v[0] for v in cerrados.values()):,} puestos de 2023 que ya no están ({sum(v[1] for v in cerrados.values()):,} electores)')
# control: las celdas suman el censo con sexo, y sus márgenes de edad cuadran
mal = [k for k, p in puestos.items() if sum(p[13:19]) != p[1] + p[2]]
print('celdas que no suman el censo:', len(mal))
