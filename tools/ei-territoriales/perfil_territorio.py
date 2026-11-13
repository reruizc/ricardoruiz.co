#!/usr/bin/env python3
"""Perfil por sexo y edad de cada territorio en las territoriales de 2023.

Dos cifras por puesto, que la página suma al nivel que se mire (país, depto,
municipio, zona/localidad, puesto):

  * ELECTORADO (exacto): censo electoral de 2023 por puesto (Registraduría),
    mujeres/hombres y 18-35 · 36-60 · 61+.
  * VOTANTES (estimado): mismo método de tools/edad-1v-2026 (build_w26):
    perfil observado de una elección anterior × cambio demográfico × ajuste
    a los votantes reales. Aquí:
        votantes_g ∝ censo2023_g × tasa2019_g,  y Σ_g = votantes 2023 del puesto
    con tasa2019_g = sufragantes 2019 del grupo (Edadygenero, mesa a mesa,
    Autoridades Locales) / censo 2019 del grupo, en el mismo puesto.
    Solo cuentan las tasas RELATIVAS entre grupos: el nivel lo pone el voto
    real de 2023. Si el puesto no casa (código distinto o cambió de nombre
    entre 2019 y 2023) o tiene poco dato, la tasa sale de su zona, luego del
    municipio, del departamento y del país.

Salida: Bases de datos/output_alcaldias_2023/perfil/{nacional,dep-XX}.json
"""
import csv, json, os, re, sys, unicodedata
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB = os.path.join(ROOT, 'Bases de datos')
AÑO = int(sys.argv[1]) if len(sys.argv) > 1 else 2023
COR_ALC = {2023: '3', 2019: '6'}[AÑO]   # código de ALCALDE en el GCS de cada año
OUT = os.path.join(DB, f'output_alcaldias_{AÑO}', 'perfil')
EDAD = [['18-20', '21-25', '26-30', '31-35'], ['36-40', '41-45', '46-50', '51-55', '56-60'], ['mas de 60']]
EG_BANDS = [['18 a 20 años', '21 a 25 años', '26 a 30 años', '31 a 35 años'],
            ['36 a 40 años', '41 a 45 años', '46 a 50 años', '51 a 55 años', '56 a 60 años'],
            ['Mayor a 60 años']]
MIN_VOT = 150      # sufragantes 2019 mínimos para usar la tasa de un nivel
ESPECIALES = {'996', '997', '998', '999'}


def nrm(s):
    s = unicodedata.normalize('NFD', str(s or ''))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^A-Z0-9 ]', ' ', s.upper()).split()


def mismo_lugar(a, b):
    """¿El nombre del puesto en 2019 y en 2023 es el mismo lugar?"""
    A, B = set(nrm(a)), set(nrm(b))
    if not A or not B:
        return False
    return len(A & B) / min(len(A), len(B)) >= 0.6


def censo(año):
    out = {}
    for r in json.load(open(os.path.join(DB, 'censos-registraduria', f'{año}_datos_censo-electoral-min.json')))['data']:
        k = f"{r['cod_depto']}-{r['cod_mun']}-{r['zona']}-{r['cod_puesto']}"
        sx, ed = r['sexo'], r['rango_etario']
        out[k] = {'s': [sx.get('mujeres', 0), sx.get('hombres', 0)],
                  'e': [sum(ed.get(b, 0) for b in g) for g in EDAD],
                  'nom': r['puesto_votacion'], 'dep': r['departamento'], 'mun': r['municipio']}
    return out


def main():
    c23, c19 = censo(AÑO), censo(2019)   # en 2019 el perfil de votantes es el observado
    # sufragantes 2019 por puesto (Edadygenero)
    eg = {}
    with open(os.path.join(DB, 'output_edad_1v', 'edad-al2019-puesto.csv')) as f:
        for r in csv.DictReader(f):
            eg[r['pcode']] = {'s': [int(r['Cantidad de Mujeres']), int(r['Cantidad Hombres'])],
                              'e': [sum(int(r[b]) for b in g) for g in EG_BANDS]}
    # votantes 2023 por puesto (alcaldía, incluye blanco/nulos/no marcados)
    vot = defaultdict(int)
    with open(os.path.join(DB, 'FINAL SUBIDA GCS', f'GCS_{AÑO}TER.csv'), encoding='utf-8-sig') as f:
        rd = csv.reader(f, delimiter=';'); h = next(rd); ix = {c: i for i, c in enumerate(h)}
        for row in rd:
            if row[ix['COD_COR']] != COR_ALC:
                continue
            k = f"{row[ix['COD_DDE']].zfill(2)}-{row[ix['COD_MME']].zfill(3)}-{row[ix['COD_ZZ']].zfill(2)}-{row[ix['COD_PP']].zfill(2)}"
            vot[k] += int(row[ix['NUM_VOT']] or 0)

    # tasas 2019 por nivel: numerador (sufragantes) y denominador (censo) por grupo
    niveles = [lambda k: k, lambda k: k.rsplit('-', 1)[0], lambda k: k[:6], lambda k: k[:2], lambda k: '']
    num = [defaultdict(lambda: [0.0] * 5) for _ in niveles]
    den = [defaultdict(lambda: [0.0] * 5) for _ in niveles]
    for k, e in eg.items():
        c = c19.get(k)
        if not c or sum(c['s']) <= 0:
            continue
        vv, cc = e['s'] + e['e'], c['s'] + c['e']
        if sum(e['s']) > 1.15 * sum(c['s']):      # más sufragantes que censo: dato roto
            continue
        for L, f in enumerate(niveles):
            key = f(k)
            for i in range(5):
                num[L][key][i] += vv[i]; den[L][key][i] += cc[i]

    def tasas(k, nom23):
        for L, f in enumerate(niveles):
            key = f(k)
            if L == 0 and not (k in c19 and mismo_lugar(c19[k]['nom'], nom23)):
                continue
            n, d = num[L].get(key), den[L].get(key)
            if not n or sum(n[:2]) < MIN_VOT or min(d) <= 0:
                continue
            return [n[i] / d[i] for i in range(5)], L
        return None, None

    def repartir(cen, t, total):
        """votantes_g ∝ cen_g·t_g, Σ=total, sin pasar del censo del grupo."""
        w = [c * x for c, x in zip(cen, t)]
        out = [0.0] * len(cen); libre = list(range(len(cen))); resto = float(total)
        for _ in range(len(cen)):
            sw = sum(w[i] for i in libre)
            if sw <= 0:
                break
            tope = [i for i in libre if resto * w[i] / sw > cen[i]]
            if not tope:
                for i in libre: out[i] = resto * w[i] / sw
                break
            for i in tope:
                out[i] = cen[i]; resto -= cen[i]; libre.remove(i)
        return out

    deps = defaultdict(lambda: {'puestos': {}, 'muns': {}})
    fuente = [0] * 5; sinvot = 0
    for k, c in sorted(c23.items()):
        dep, mun, zz, pp = k.split('-')
        V = vot.get(k, 0)
        cs, ce = c['s'], c['e']
        V = min(V, sum(cs))
        t, L = tasas(k, c['nom'])
        if t is None or V == 0:
            vs = [0, 0]; ve = [0, 0, 0]
            if V == 0: sinvot += 1
        else:
            vs = repartir(cs, t[:2], V); ve = repartir(ce, t[2:], V)
            fuente[L] += V
        d = deps[dep]
        d['nombre'] = c['dep']
        d['muns'].setdefault(mun, c['mun'])
        d['puestos'][f'{mun}-{zz}-{pp}'] = [*cs, *ce, *[round(x) for x in vs], *[round(x) for x in ve], V]

    os.makedirs(OUT, exist_ok=True)
    nac = {'v': AÑO, 'campos': ['c_muj', 'c_hom', 'c_18_35', 'c_36_60', 'c_61', 'v_muj', 'v_hom', 'v_18_35', 'v_36_60', 'v_61', 'votantes'],
           'deps': {}}
    tot = [0] * 11
    for dep, d in sorted(deps.items()):
        s = [0] * 11
        for row in d['puestos'].values():
            for i, x in enumerate(row): s[i] += x
        tot = [a + b for a, b in zip(tot, s)]
        nac['deps'][dep] = {'nombre': d['nombre'], 'suma': s}
        json.dump({'v': AÑO, 'dep': dep, 'nombre': d['nombre'], 'muns': d['muns'], 'puestos': d['puestos']},
                  open(os.path.join(OUT, f'dep-{dep}.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    nac['suma'] = tot
    V = sum(fuente)
    nac['fuente_tasa'] = {n: round(100 * x / V, 1) for n, x in zip(['puesto', 'zona', 'municipio', 'departamento', 'pais'], fuente)}
    json.dump(nac, open(os.path.join(OUT, 'nacional.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    pc = lambda a, b: f'{100*a/b:.1f}%'
    print('electorado:', 'mujeres', pc(tot[0], tot[0]+tot[1]), '· 18-35', pc(tot[2], sum(tot[2:5])), '· 61+', pc(tot[4], sum(tot[2:5])))
    print('votantes  :', 'mujeres', pc(tot[5], tot[5]+tot[6]), '· 18-35', pc(tot[7], sum(tot[7:10])), '· 61+', pc(tot[9], sum(tot[7:10])), f'· {tot[10]:,} votantes')
    print('tasa desde:', nac['fuente_tasa'], '· puestos sin votos 2023:', sinvot)


if __name__ == '__main__':
    main()
