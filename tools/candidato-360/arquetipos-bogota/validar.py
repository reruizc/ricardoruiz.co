#!/usr/bin/env python3
"""Validación del borrador de arquetipos de Bogotá.

    python3 tools/candidato-360/arquetipos-bogota/validar.py

1. ¿El arraigo es del BARRIO o de los candidatos de 2023? Se repite la misma
   medida (voto por encima de la geografía de su lista, sin azar) con el
   Concejo 2019 —otros candidatos, otro alcalde— y se compara barrio a barrio.
2. Casos conocidos: dónde caen los barrios de candidaturas con base territorial
   conocida y los bastiones de cada candidato a la Alcaldía.
3. Qué se cruza en el «voto cruzado»: familias al Concejo contra a la Alcaldía
   en cada arquetipo.
Escribe validacion.md al lado de los datos.
"""
import csv, json, math
from collections import defaultdict
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
BD = RAIZ / 'Bases de datos'
DIR = BD / 'arquetipos-bogota'
_RNG = np.random.default_rng(2027)


def norm(s):
    import re, unicodedata
    s = unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode().upper()
    return re.sub(r'\s+', ' ', re.sub(r'[^A-Z0-9 ]', ' ', s)).strip()
_C = {}


def d_azar(n, p, k):
    b = min(int(round(math.log(max(n, 2), 1.12))), 200)
    if (k, b) not in _C:
        m = max(2, int(round(1.12 ** b)))
        dr = _RNG.multinomial(m, p, size=300) / m
        _C[(k, b)] = float(np.mean(0.5 * np.abs(dr - p).sum(axis=1)))
    return _C[(k, b)]


def arraigo_por_barrio(anio, excluir=frozenset()):
    """Arraigo a escala de barrio desde el detalle por comuna del año."""
    geo = json.loads((BD / 'output_pacto_1v_2026' / 'geo' / 'BOG-BARRIOS-CATASTRALES.json').read_text())
    idx = {i: f['properties']['codigo'] for i, f in enumerate(geo['features'])}
    vc = defaultdict(lambda: defaultdict(float))   # (partido, candidato) → barrio → votos
    vp = defaultdict(lambda: defaultdict(float))   # partido → barrio → votos
    val = defaultdict(float)
    for ruta in sorted((BD / f'output_concejo_{anio}' / 'comuna').glob('16-001-*.json')):
        d = json.loads(ruta.read_text())
        partidos = [p[0] for p in d['partidos']]
        for b in d['barrios']:
            if b.get('feat') is None:
                continue
            cod = idx[b['feat']]
            for ci, v in b['v']:
                nom, pi = d['cands'][ci]
                par = partidos[pi]
                vc[(par, nom)][cod] += v
                vp[par][cod] += v
                val[cod] += v
            for pi, v in b.get('l', []):
                vp[partidos[pi]][cod] += v
                val[cod] += v
    barrios = sorted(val)
    ix = {c: i for i, c in enumerate(barrios)}
    A = np.zeros(len(barrios))
    for (par, nom), dist in vc.items():
        if norm(nom) in excluir:
            continue
        x = np.zeros(len(barrios))
        for c, v in dist.items():
            x[ix[c]] = v
        n = x.sum()
        if n < 50:
            continue
        p = np.zeros(len(barrios))
        for c, v in vp[par].items():
            p[ix[c]] = v
        p /= p.sum()
        D = 0.5 * np.abs(x / n - p).sum()
        exc = np.maximum(0, x - n * p)
        a = n * max(0.0, D - d_azar(n, p, (anio, par)))
        if exc.sum():
            A += np.where(x > 0, a * exc / exc.sum(), 0)
    return {c: A[ix[c]] / val[c] for c in barrios if val[c] >= 300}


def main():
    arq = json.loads((DIR / 'arquetipos-bogota.json').read_text())
    B = arq['barrios']
    nomC = {s: a['nombre'] for s, a in arq['corporaciones']['concejo']['arquetipos'].items()}
    nomA = {s: a['nombre'] for s, a in arq['corporaciones']['alcaldia']['arquetipos'].items()}
    L = ['# Validación del borrador de arquetipos de Bogotá', '']

    # 1. arraigo 2019 contra 2023
    a19 = arraigo_por_barrio(2019)
    a23 = arraigo_por_barrio(2023)
    comunes = [c for c in a23 if c in a19 and c in B]
    x = np.array([a19[c] for c in comunes]); y = np.array([a23[c] for c in comunes])
    r = float(np.corrcoef(x, y)[0, 1])
    L += ['## 1. ¿El arraigo es del barrio o de los candidatos?', '',
          f'Misma medida, a escala de barrio, con el Concejo 2019 y el de 2023: '
          f'**correlación {r:.2f}** en {len(comunes)} barrios con dato en las dos elecciones. '
          f'Arraigo medio de la ciudad: 2019 {x.mean():.1%} · 2023 {y.mean():.1%} del voto a partidos.', '']
    # Sin quien repite: candidaturas de 2023 que no estuvieron en el Concejo 2019
    raw19 = json.loads((DIR / 'raw' / 'ter2019.json').read_text())
    repiten = {norm(n) for k, n in raw19['_nombres'].items() if k.startswith('conc|') and k.split('|')[2] not in ('0', '996', '997', '998', '999')}
    a23n = arraigo_por_barrio(2023, frozenset(repiten))
    c2 = [c for c in comunes if c in a23n]
    r2 = float(np.corrcoef([a19[c] for c in c2], [a23n[c] for c in c2])[0, 1])
    cand23 = list(csv.DictReader(open(DIR / 'candidatos-concejo-2023.csv')))
    rep23 = [c for c in cand23 if norm(c['candidato']) in repiten]
    arr_tot = sum(float(c['arraigo_barrio']) * int(c['votos']) for c in cand23)
    arr_rep = sum(float(c['arraigo_barrio']) * int(c['votos']) for c in rep23)
    L += [f'**Pero buena parte de esa persistencia son las mismas personas.** {len(rep23)} de las {len(cand23)} candidaturas de 2023 '
          f'ya se habían lanzado al Concejo en 2019, y se llevan el {arr_rep/arr_tot:.0%} de los votos de base propia. '
          f'Quitándolas, la correlación con 2019 baja a **{r2:.2f}**. Lectura: el barrio tiene algo propio, pero lo que más pesa es '
          f'que ahí YA hay alguien con red. Para una candidatura nueva, «barrio de gestión» quiere decir territorio ocupado.', '']
    por = defaultdict(list)
    for c in comunes:
        por[B[c]['concejo']['dom']].append((a19[c], a23[c]))
    L += ['| Arquetipo de Concejo (2023) | Barrios | Arraigo 2019 | Arraigo 2023 |', '|---|---:|---:|---:|']
    for s, v in sorted(por.items(), key=lambda kv: -np.mean([t[1] for t in kv[1]])):
        L.append(f'| {nomC[s]} | {len(v)} | {np.mean([t[0] for t in v]):.1%} | {np.mean([t[1] for t in v]):.1%} |')
    # quintiles 2019 → 2023
    q = np.quantile(x, [.2, .4, .6, .8])
    qi = np.searchsorted(q, x)
    L += ['', 'Arraigo 2023 según el quintil de arraigo que el barrio tenía en 2019:', '',
          '| Quintil 2019 | Arraigo 2023 |', '|---|---:|']
    for k in range(5):
        L.append(f'| {k+1} | {y[qi == k].mean():.1%} |')

    # 2. casos conocidos
    L += ['', '## 2. Casos conocidos', '']
    cand = list(csv.DictReader(open(DIR / 'candidatos-concejo-2023.csv')))
    cand.sort(key=lambda c: -float(c['arraigo_barrio']) * int(c['votos']))
    L += ['Candidaturas al Concejo 2023 con más votos de base propia, y el arquetipo de los barrios donde la tienen:', '',
          '| Candidatura | Lista | Votos | Base propia | Localidad fuerte |', '|---|---|---:|---:|---|']
    for c in cand[:12]:
        L.append(f"| {c['candidato'].title()} | {c['partido'].title()[:34]} | {int(c['votos']):,} | {float(c['arraigo_barrio']):.0%} | {c['localidad_top'].title()} |")
    # bastiones de alcaldía
    L += ['', 'Bastiones de cada candidato a la Alcaldía 2023 (25 barrios con su mayor porcentaje) y el arquetipo de Alcaldía en que caen:', '']
    for k, nom in (('alc_galan', 'Galán'), ('alc_oviedo', 'Oviedo'), ('alc_bolivar', 'Bolívar')):
        top = sorted((c for c in B if 'alcaldia' in B[c]), key=lambda c: -(B[c]['vars'][k] or 0))[:25]
        cnt = defaultdict(int)
        for c in top:
            cnt[nomA[B[c]['alcaldia']['dom']]] += 1
        L.append(f"- **{nom}**: " + ' · '.join(f'{n} {v}' for n, v in sorted(cnt.items(), key=lambda x: -x[1])))

    # 3. qué se cruza
    L += ['', '## 3. Qué se cruza en el voto cruzado', '',
          'Familia política del voto al Concejo contra la del voto a la Alcaldía, promedio ponderado por votantes:', '',
          '| Arquetipo de Alcaldía | | Izq. | Centro-izq. | Centro | Centro-der. | Der. | Sin línea |', '|---|---|---:|---:|---:|---:|---:|---:|']
    for s, a in arq['corporaciones']['alcaldia']['arquetipos'].items():
        cods = [c for c in B if B[c].get('alcaldia', {}).get('dom') == s]
        w = np.array([B[c]['vars']['votantes23'] for c in cods])
        fila_c, fila_a = [], []
        for f in ('izq', 'ci', 'c', 'cd', 'd', 'sc'):
            fila_c.append(np.average([B[c]['vars'].get(f'conc_{f}') or 0 for c in cods], weights=w) if f != 'sc' else None)
        # la alcaldía por familia no se guardó por barrio en el json: se relee de barrios.csv
        filas = {r['codigo']: r for r in csv.DictReader(open(DIR / 'barrios.csv'))}
        for f in ('izq', 'ci', 'c', 'cd', 'd', 'sc'):
            fila_a.append(np.average([float(filas[c][f'alc_{f}']) for c in cods], weights=w))
        fila_c[-1] = np.average([float(filas[c]['conc_sc']) for c in cods], weights=w)
        L.append(f"| {a['nombre']} | Concejo | " + ' | '.join(f'{v:.0%}' for v in fila_c) + ' |')
        L.append('| | Alcaldía | ' + ' | '.join(f'{v:.0%}' for v in fila_a) + ' |')
    (DIR / 'validacion.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
