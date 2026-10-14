#!/usr/bin/env python3
"""Valida los archivos mesas/{vuelta}-{dep}.json releyéndolos del disco (no confía en
los acumuladores de build.py):

  1. por puesto: suma de mesas (candidato a candidato + blanco) = puesto en dep-{cod}.json
  2. por depto:  suma de mesas = deps.json
  3. nacional:   suma de mesas = resumen.json (candidatos y los tres especiales)
  4. contra el oficial: CONTROL de build.py + escrutinio de comisiones 2026

  python3 tools/build-presidencial-escr/validar_mesas.py [clave …]   (sin clave: todas)
Sale con código 1 si algo no cuadra.
"""
import collections, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402

BASE = build.OUT_BASE
# 2026: total de las 33 comisiones generales (sin exterior), CLAUDE.md «Escrutinio oficial 2026».
OFICIAL_2026 = {('2026', '1v'): {'Abelardo De La Espriella': 10045330, 'Iván Cepeda Castro': 9536162},
                ('2026', '2v'): {'Iván Cepeda Castro': 12495109, 'Abelardo De La Espriella': 12569192}}


def validar(clave_anio):
    d = os.path.join(BASE, clave_anio)
    resumen = json.load(open(os.path.join(d, 'resumen.json'), encoding='utf-8'))
    deps = {x['cod']: x for x in json.load(open(os.path.join(d, 'deps.json'), encoding='utf-8'))}
    malos = 0
    for cons in resumen['consultas']:
        v = cons['clave']
        nac, nac_sin88 = collections.Counter(), collections.Counter()
        esp = collections.Counter()
        n_mesas = n_pue = 0
        solo_esp = [0]
        for dep in sorted(deps):
            depf = json.load(open(os.path.join(d, f'dep-{dep}.json'), encoding='utf-8'))
            mpath = os.path.join(d, 'mesas', f'{v}-{dep}.json')
            if not os.path.exists(mpath):
                # el depto existe por la otra vuelta/consulta y en esta no tuvo ni una fila
                if deps[dep][v]['votos']:
                    malos += 1; print(f'    [MAL] {clave_anio} {v} dep {dep}: falta {mpath}')
                continue
            mf = json.load(open(mpath, encoding='utf-8'))
            cands = mf['cands']
            dep_sum = collections.Counter()
            vistos = set()
            for m in depf['municipios']:
                for z in m['zonas']:
                    for p in z['puestos']:
                        k = f"{m['cod']}-{z['cod']}-{p['cod']}"
                        b = p.get(v) or {'votos': 0, 'cands': []}
                        esperado = collections.Counter({c['nombre']: c['votos'] for c in b['cands']})
                        esperado['__b'] = b.get('blanco', 0)
                        got = collections.Counter()
                        for mes, vs, bl, nu, nm in mf['p'].get(k, []):
                            for i in range(0, len(vs), 2):
                                got[cands[vs[i]]] += vs[i + 1]
                            got['__b'] += bl
                            esp['b'] += bl; esp['n'] += nu; esp['x'] += nm
                            n_mesas += 1
                        if k in mf['p']:
                            vistos.add(k); n_pue += 1
                        if +got != +esperado:
                            malos += 1
                            if malos < 6:
                                print(f'    [MAL] {clave_anio} {v} puesto {dep}-{k}: mesas {dict(+got)} vs puesto {dict(+esperado)}')
                        dep_sum.update(got)
            # Puestos sin un solo voto por candidato (solo blanco/nulos/no marcados): dep-*.json
            # no los lista, porque su árbol nace de los votos por candidato. Sus mesas sí van en
            # el archivo; entran a la suma del depto y se reportan aparte.
            for k in sorted(set(mf['p']) - vistos):
                solo_esp[0] += 1
                for mes, vs, bl, nu, nm in mf['p'][k]:
                    if vs:
                        malos += 1; print(f'    [MAL] {clave_anio} {v} puesto {dep}-{k} con votos por candidato y sin par')
                    dep_sum['__b'] += bl
                    esp['b'] += bl; esp['n'] += nu; esp['x'] += nm
            esp_dep = collections.Counter({c['nombre']: c['votos'] for c in deps[dep][v]['candidatos']})
            cand_dep = +collections.Counter({k: x for k, x in dep_sum.items() if k != '__b'})
            if cand_dep != +esp_dep or sum(dep_sum.values()) != deps[dep][v]['votos']:
                malos += 1
                print(f'    [MAL] {clave_anio} {v} dep {dep}: mesas {sum(dep_sum.values()):,} vs deps.json {deps[dep][v]["votos"]:,}')
            nac.update(cand_dep)
            if dep != '88':
                nac_sin88.update(cand_dep)
        res_c = collections.Counter({c['nombre']: c['votos'] for c in cons['candidatos']})
        ok_nac = +nac == +res_c
        res_esp = {build.tipo_especial(n)[2:]: x for n, x in cons['especiales'].items()}
        ok_esp = all(esp[k] == res_esp.get(k, 0) for k in ('b', 'n', 'x'))
        print(f"  [{'OK ' if ok_nac and ok_esp else 'MAL'}] {clave_anio} {v}: {n_mesas:,} mesas en {n_pue:,} puestos · "
              f"candidatos {sum(nac.values()):,} = resumen · blanco {esp['b']:,} nulos {esp['n']:,} no marcados {esp['x']:,}"
              + (f" · {solo_esp[0]} puestos solo con especiales" if solo_esp[0] else ''))
        malos += (not ok_nac) + (not ok_esp)
        ctrl = {build.norm_cand(k): x for k, x in build.CONTROL.get((clave_anio, v), {}).items()}
        for n, x in ctrl.items():
            st = 'OK ' if nac[n] == x else 'MAL'; malos += st == 'MAL'
            print(f'    [{st}] oficial {n}: {nac[n]:,} (esperado {x:,})')
        for n, x in OFICIAL_2026.get((clave_anio, v), {}).items():
            st = 'OK ' if nac_sin88[n] == x else 'MAL'; malos += st == 'MAL'
            print(f'    [{st}] comisiones (sin exterior) {n}: {nac_sin88[n]:,} (esperado {x:,})')
    return malos


if __name__ == '__main__':
    claves = sys.argv[1:] or ['2010', '2014', '2018', '2022', '2026', 'pacto2025']
    total = sum(validar(k) for k in claves)
    print('\nTODO CUADRA' if not total else f'\n{total} PROBLEMAS')
    sys.exit(1 if total else 0)
