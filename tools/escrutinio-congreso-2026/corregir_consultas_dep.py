#!/usr/bin/env python3
"""Consultas 2026 · rehace el total de cada DEPARTAMENTO sumando sus municipios.

⚠ Bug encontrado el 8-oct-2026: en consultas/dep-XX.json y consultas/deps.json el bloque de
cada departamento no era la suma de sus municipios (Antioquia: Gran Consulta 480.645 contra
1.105.479 de sus 125 municipios). La suma de los departamentos daba entre 38 y 69 % del total
nacional, según el candidato. Los municipios y el resumen nacional SÍ estaban bien:
  · la suma de los 34 departamentos por municipio da exacto el resumen nacional;
  · en los 25 E-24 generales con texto digital, la suma por municipio cuadra AL VOTO
    (tools/escrutinio-congreso-2026/verificar_consultas.py).
Bogotá y San Andrés salían bien porque su bloque coincidía con el único municipio o casi.

Este script reescribe solo los bloques de departamento ('gran', 'frente', 'soluciones' del
nivel superior de cada dep-XX.json y las entradas de deps.json, conservando el `codigo`),
y aborta si la suma nueva no da exacto el resumen nacional.

  python3 tools/escrutinio-congreso-2026/corregir_consultas_dep.py            # revisa
  python3 tools/escrutinio-congreso-2026/corregir_consultas_dep.py --escribe  # escribe
"""
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

DIR = Path(__file__).resolve().parents[2] / 'Bases de datos' / 'output_agregados' / 'consultas'
CONS = ('gran', 'frente', 'soluciones')


def bloque(municipios, k):
    suma = defaultdict(int)
    orden = []
    for m in municipios:
        for c in m.get(k, {}).get('cands', []):
            if c['nombre'] not in suma:
                orden.append(c['nombre'])
            suma[c['nombre']] += c['votos']
    cands = sorted(({'nombre': n, 'votos': suma[n]} for n in orden), key=lambda c: -c['votos'])
    return {'votos': sum(suma.values()), 'cands': cands}


def main():
    escribe = '--escribe' in sys.argv
    resumen = json.load(open(DIR / 'resumen.json'))
    nac = {c['clave']: {x['nombre']: x['votos'] for x in c['candidatos']} for c in resumen['consultas']}
    codigos = {c['clave']: {x['nombre']: x['codigo'] for x in c['candidatos']} for c in resumen['consultas']}
    deps = json.load(open(DIR / 'deps.json'))
    por_cod = {d['cod']: d for d in deps}
    total = defaultdict(lambda: defaultdict(int))
    nuevos = {}
    for f in sorted(glob.glob(str(DIR / 'dep-*.json'))):
        d = json.load(open(f))
        antes = {k: d[k]['votos'] for k in CONS if k in d}
        for k in CONS:
            if k not in d:
                continue
            b = bloque(d['municipios'], k)
            d[k] = b
            for c in b['cands']:
                total[k][c['nombre']] += c['votos']
            if d['cod'] in por_cod:
                por_cod[d['cod']][k] = {'votos': b['votos'], 'candidatos': [
                    {'nombre': c['nombre'], 'votos': c['votos'], 'codigo': codigos[k].get(c['nombre'])} for c in b['cands']]}
        nuevos[f] = d
        despues = {k: d[k]['votos'] for k in CONS if k in d}
        if antes != despues:
            print(f"dep {d['cod']} {d['nombre']:22s} " + ' · '.join(f'{k} {antes[k]:,} → {despues[k]:,}' for k in despues))
    malos = [(k, n, v, total[k][n]) for k in nac for n, v in nac[k].items() if total[k][n] != v]
    if malos:
        raise SystemExit(f'la suma de departamentos no da el nacional: {malos}')
    print('\nla suma de los departamentos da exacto el resumen nacional en los', sum(len(v) for v in nac.values()), 'candidatos')
    if not escribe:
        print('(revisión: no se escribió nada; pasar --escribe)')
        return
    for f, d in nuevos.items():
        Path(f).write_text(json.dumps(d, ensure_ascii=False, separators=(',', ':')))
    (DIR / 'deps.json').write_text(json.dumps(deps, ensure_ascii=False, separators=(',', ':')))
    print(f'escritos {len(nuevos)} dep-*.json + deps.json en {DIR}')


if __name__ == '__main__':
    main()
