#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Censo electoral vs poblacion DANE por municipio (1990s-2026).

Responde a la tesis de "fraude en el censo electoral": municipios donde el censo
electoral supera a la poblacion proyectada por el DANE.

Cruza:
  - censo electoral por puesto 2018/2022/2026  (Bases de datos/censos-puesto-{a}.json)
  - nombres Registraduria                      (CIUDADES/DIVIPOLE-MAR2026.csv)
  - poblacion DANE municipal 2018-2042         (output_observatorio_mujer/dane-pob-mun.json)
  - preconteo 1V+2V 2026 por municipio         (output_2v/agg_municipio.json)
  - escrutinio 2V 2022 (Petro/Rodolfo)         (FINAL SUBIDA GCS/GCS_2022PRES2V.csv)

GOTCHAS (no borrar):
  - El codigo de municipio de la Registraduria NO es el DANE. Se cruza por
    (depto, municipio) normalizado con fuzzy + una tabla FORCE de 6 overrides;
    sin ella el fuzzy pega CUCUTA con CUCUTILLA y la correlacion se destruye.
  - El campo `pot` de agg_municipio.json esta incompleto en 16 municipios
    (Oiba: 443 vs 10.114 reales) -> la participacion SIEMPRE se calcula contra
    el censo del Divipole (c26), nunca contra `pot`.
  - Los votos 2026 son de PRECONTEO: margen 243.210 vs 250.830 del escrutinio
    (3% de diferencia). No mueve ninguna conclusion, pero se declara.
  - Se excluye el dep 88 (exterior/consulados): no tiene poblacion DANE.

Salida: Bases de datos/output_censo_poblacion/censo-vs-poblacion-mun.csv + .json
"""
import json, csv, re, math, collections, difflib, unicodedata, os, statistics as st

BASE = '/Users/ricardoruiz/ricardoruiz.co'
OUT = f'{BASE}/Bases de datos/output_censo_poblacion'
MARGEN_OFICIAL_2V = 250830          # Abelardo - Cepeda, escrutinio


def norm(s):
    s = unicodedata.normalize('NFD', str(s or ''))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn').upper()
    s = re.sub(r'\(.*?\)', ' ', s)
    return re.sub(r'\s+', ' ', re.sub(r'[^A-Z0-9 ]', ' ', s)).strip()


ALIAS_DEP = {
    'BOGOTA': 'BOGOTA D C',
    'VALLE': 'VALLE DEL CAUCA',          # sin este alias se cae el depto entero (42 muns)
    'SAN ANDRES': 'ARCHIPIELAGO DE SAN ANDRES PROVIDENCIA Y SANTA CATALINA',
    'SAN ANDRES Y PROVIDENCIA': 'ARCHIPIELAGO DE SAN ANDRES PROVIDENCIA Y SANTA CATALINA',
}
# el fuzzy se equivoca con nombres casi identicos -> override manual
FORCE = {'15304': '25843', '15301': '25841', '23043': '52258',
         '23046': '52260', '25001': '54001', '25025': '54223'}


def censo_mun(year):
    d = json.load(open(f'{BASE}/Bases de datos/censos-puesto-{year}.json'))
    agg = collections.Counter()
    for k, v in d['porPuesto'].items():
        p = k.split('-')
        agg[p[0] + p[1]] += v
    return agg


def build():
    C = {y: censo_mun(y) for y in (2018, 2022, 2026)}

    regnames = {}
    with open(f'{BASE}/CIUDADES/DIVIPOLE-MAR2026.csv', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f, delimiter=';'):
            cod = r['dd'].zfill(2) + r['mm'].zfill(3)
            regnames.setdefault(cod, (norm(r['departamento']), norm(r['municipio'])))

    dane = json.load(open(f'{BASE}/Bases de datos/output_observatorio_mujer/dane-pob-mun.json'))
    by_dep = collections.defaultdict(dict)
    for cod, v in dane.items():
        by_dep[norm(v['depnom'])][norm(v['nombre'])] = (cod, v)
    dep_dane = list(by_dep)

    dep_map = {}
    for depn in {d for d, _ in regnames.values()}:
        cand = ALIAS_DEP.get(depn, depn)
        if cand in by_dep:
            dep_map[depn] = cand
        else:
            g = difflib.get_close_matches(cand, dep_dane, n=1, cutoff=0.55)
            if g:
                dep_map[depn] = g[0]

    def match(depn, munn):
        pool = by_dep.get(dep_map.get(depn, ''), {})
        if munn in pool:
            return pool[munn]
        g = difflib.get_close_matches(munn, list(pool), n=1, cutoff=0.72)
        if g:
            return pool[g[0]]
        hits = sorted([k for k in pool if k and (k in munn or munn in k)], key=len, reverse=True)
        return pool[hits[0]] if hits else None

    # votos 2022 2V
    p22, r22 = collections.Counter(), collections.Counter()
    with open(f'{BASE}/Bases de datos/FINAL SUBIDA GCS/GCS_2022PRES2V.csv', encoding='latin-1') as f:
        rd = csv.reader(f, delimiter=';'); next(rd)
        for row in rd:
            cod = row[6].zfill(2) + row[7].zfill(3)
            v = int(row[15] or 0)
            if row[13] == '2': p22[cod] += v
            elif row[13] == '1': r22[cod] += v

    agg = {r['cod5']: r for r in json.load(open(f'{BASE}/Bases de datos/output_2v/agg_municipio.json'))}

    rows, sin = [], []
    for cod5, (depn, munn) in sorted(regnames.items()):
        if cod5.startswith('88') or not depn:
            continue
        m = (FORCE[cod5], dane[FORCE[cod5]]) if cod5 in FORCE else match(depn, munn)
        if not m:
            sin.append((cod5, depn, munn)); continue
        dcod, dv = m
        a = agg.get(cod5, {})
        c26 = C[2026].get(cod5, 0)
        r = dict(cod5=cod5, dane=dcod, dep=depn, mun=munn,
                 c18=C[2018].get(cod5, 0), c22=C[2022].get(cod5, 0), c26=c26,
                 p18=dv['2018']['tot'], p22=dv['2022']['tot'], p25=dv['2025']['tot'],
                 cep1=a.get('cep1', 0), abe1=a.get('abe1', 0), urna1=a.get('urna1', 0),
                 cep2=a.get('cep2', 0), abe2=a.get('abe2', 0), urna2=a.get('urna2', 0),
                 petro22=p22.get(cod5, 0), rodo22=r22.get(cod5, 0))
        r['ratio'] = 100 * r['c26'] / r['p25'] if r['p25'] else 0
        r['ratio22'] = 100 * r['c22'] / r['p22'] if r['p22'] else 0
        r['ratio18'] = 100 * r['c18'] / r['p18'] if r['p18'] else 0
        r['dpob'] = 100 * (r['p25'] / r['p18'] - 1) if r['p18'] else 0
        r['part2'] = 100 * r['urna2'] / c26 if c26 else 0       # OJO: nunca contra `pot`
        r['margen26'] = r['abe2'] - r['cep2']
        r['margen22'] = r['rodo22'] - r['petro22']
        r['v26'] = r['abe2'] + r['cep2']
        r['v22'] = r['rodo22'] + r['petro22']
        rows.append(r)
    return rows, sin


def corr(xs, ys):
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs)); sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy) if sx * sy else 0


def ols(X, y):
    k = len(X[0]); n = len(y)
    M = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(k)] + [sum(X[i][a] * y[i] for i in range(n))]
         for a in range(k)]
    for c in range(k):
        p = max(range(c, k), key=lambda r: abs(M[r][c])); M[c], M[p] = M[p], M[c]
        for r in range(k):
            if r != c and M[c][c]:
                f = M[r][c] / M[c][c]
                for j in range(c, k + 1): M[r][j] -= f * M[c][j]
    return [M[i][k] / M[i][i] if M[i][i] else 0 for i in range(k)]


def informe(rows):
    s100 = [r for r in rows if r['ratio'] > 100]
    P = lambda g, k='c26': sum(r[k] for r in g)
    L = []
    A = L.append
    A(f'municipios cruzados: {len(rows)}')
    A(f"censo 2026 (sin exterior) {P(rows):,} | poblacion DANE 2025 {P(rows,'p25'):,} | ratio {100*P(rows)/P(rows,'p25'):.1f}%")
    A('')
    A('1. CONTEO POR UMBRAL (y su historia)')
    for a, k in ((2018, 'ratio18'), (2022, 'ratio22'), (2026, 'ratio')):
        A(f'   {a}: >100% {sum(1 for r in rows if r[k]>100):4d} | >95% {sum(1 for r in rows if r[k]>95):4d} '
          f'| >90% {sum(1 for r in rows if r[k]>90):4d}')
    A('')
    A('2. VOTOS REALES vs POBLACION')
    A(f"   municipios donde los VOTOS de 2V superan la poblacion: {sum(1 for r in rows if r['urna2']>r['p25'])}")
    mx = max(rows, key=lambda r: r['urna2'] / r['p25'] if r['p25'] else 0)
    A(f"   maximo del pais: {mx['mun']} ({mx['dep']}) {100*mx['urna2']/mx['p25']:.1f}% "
      f"-> ADLE {mx['abe2']:,} / Cepeda {mx['cep2']:,}")
    A('')
    A('3. PARTICIPACION POR TRAMO (denominador = censo Divipole)')
    for lo, hi, lb in [(100, 1e9, '>100%'), (95, 100, '95-100%'), (90, 95, '90-95%'), (80, 90, '80-90%'), (0, 80, '<=80%')]:
        g = [r for r in rows if lo < r['ratio'] <= hi]
        A(f"   {lb:9s} n={len(g):4d} partic {100*P(g,'urna2')/P(g):5.1f}%  margen ADLE {100*P(g,'margen26')/P(g,'v26'):+6.1f}pp")
    A(f"   NACIONAL  n={len(rows):4d} partic {100*P(rows,'urna2')/P(rows):5.1f}%  margen ADLE {100*P(rows,'margen26')/P(rows,'v26'):+6.1f}pp")
    A('')
    A('4. EXCEDENTE INERTE')
    exc = P(s100) - P(s100, 'p25'); nov = P(s100) - P(s100, 'urna2')
    A(f'   excedente censo-poblacion en los {len(s100)} muns >100%: {exc:,} cedulas')
    A(f'   cedulas de esos muns que NO votaron: {nov:,} ({nov/exc:.1f}x el excedente)')
    A(f'   crecimiento del censo 2022->2026 alli: +{P(s100)-P(s100,"c22"):,} (nacional +{P(rows)-P(rows,"c22"):,})')
    A('')
    A('5. LOS MISMOS MUNICIPIOS EN 2022 (gano Petro)')
    A(f"   2026 ADLE {P(s100,'margen26'):+,} ({100*P(s100,'margen26')/P(s100,'v26'):+.1f}pp) | "
      f"2022 RODOLFO {P(s100,'margen22'):+,} ({100*P(s100,'margen22')/P(s100,'v22'):+.1f}pp)")
    A('')
    A('6. ES GEOGRAFIA, NO CENSO')
    s = [r for r in rows if r['v26'] > 200 and r['v22'] > 200]
    m26 = [100 * r['margen26'] / r['v26'] for r in s]
    m22 = [100 * r['margen22'] / r['v22'] for r in s]
    A(f"   corr(ratio26, margen ADLE 26) = {corr([r['ratio'] for r in s], m26):+.3f}")
    A(f"   corr(ratio22, margen RODOLFO 22) = {corr([r['ratio22'] for r in s], m22):+.3f}")
    A(f"   corr(margen22, margen26) = {corr(m22, m26):+.3f}")
    b = ols([[1.0, r['ratio'], math.log(r['p25'])] for r in s], m26)
    b2 = ols([[1.0, r['ratio'], math.log(r['p25']), m] for r, m in zip(s, m22)], m26)
    A(f"   coef del ratio: {b[1]:+.3f} -> {b2[1]:+.3f} al controlar por el voto de 2022")
    chicos = sorted([r for r in s if r['p25'] < 20000], key=lambda r: -r['ratio'])
    q = len(chicos) // 4
    A(f'   municipios <20.000 hab (n={len(chicos)}), por cuartil de ratio:')
    for i in range(4):
        g = chicos[i * q:(i + 1) * q] if i < 3 else chicos[3 * q:]
        A(f"      Q{i+1} ratio {st.mean(r['ratio'] for r in g):5.1f}%  ADLE-26 {100*P(g,'margen26')/P(g,'v26'):+6.1f}pp"
          f"  RODOLFO-22 {100*P(g,'margen22')/P(g,'v22'):+6.1f}pp")
    A('')
    A('7. ARITMETICA DEL SUBCONJUNTO')
    A(f"   anulando COMPLETOS los {len(s100)} muns >100% ({P(s100,'v26'):,} votos): "
      f"margen {MARGEN_OFICIAL_2V - P(s100,'margen26'):+,}")
    low = sorted(rows, key=lambda r: r['ratio'])[:len(s100)]
    A(f"   espejo, anulando los {len(low)} de ratio MAS BAJO: margen {MARGEN_OFICIAL_2V - P(low,'margen26'):+,}")
    A('')
    A('8. QUE EXPLICA EL RATIO')
    perd = [r for r in rows if r['dpob'] < 0]; gan = [r for r in rows if r['dpob'] >= 0]
    A(f"   muns que PIERDEN poblacion 18-25 (n={len(perd)}): ratio medio {st.mean(r['ratio'] for r in perd):.1f}%")
    A(f"   muns que GANAN poblacion      (n={len(gan)}): ratio medio {st.mean(r['ratio'] for r in gan):.1f}%")
    A(f"   corr(ratio, log poblacion) = {corr([r['ratio'] for r in s], [math.log(r['p25']) for r in s]):+.3f}")
    A(f"   poblacion mediana de los muns >100%: {st.median(r['p25'] for r in s100):,.0f}")
    A(f"   deptos: {dict(collections.Counter(r['dep'] for r in s100).most_common(6))}")
    return '\n'.join(L)


if __name__ == '__main__':
    rows, sin = build()
    os.makedirs(OUT, exist_ok=True)
    json.dump(rows, open(f'{OUT}/censo-vs-poblacion-mun.json', 'w'), ensure_ascii=False)
    cols = ['cod5', 'dane', 'dep', 'mun', 'p18', 'p22', 'p25', 'c18', 'c22', 'c26',
            'ratio18', 'ratio22', 'ratio', 'dpob', 'urna1', 'urna2', 'part2',
            'cep2', 'abe2', 'margen26', 'petro22', 'rodo22', 'margen22']
    with open(f'{OUT}/censo-vs-poblacion-mun.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore', delimiter=';')
        w.writeheader()
        for r in sorted(rows, key=lambda r: -r['ratio']):
            w.writerow({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items() if k in cols})
    txt = informe(rows)
    open(f'{OUT}/informe.txt', 'w').write(txt)
    print(txt)
    print(f'\nsin cruzar: {sin}')
    print(f'-> {OUT}/')
