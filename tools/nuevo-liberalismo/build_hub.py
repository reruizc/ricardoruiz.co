#!/usr/bin/env python3
"""Cifras de portada del hub (index.html) leídas de los datos de cada módulo.
Correr DESPUÉS de build_tablero / build_inventario / build_clima / build_escenarios, y luego empaqueta.py."""
import json, os
D = os.path.join(os.path.dirname(__file__), '..', '..', 'Propuestas', 'nuevo-liberalismo', 'datos')
L = lambda n: json.load(open(os.path.join(D, n + '.json'), encoding='utf-8'))
t, inv, cl, es = L('tablero'), L('inventario'), L('clima'), L('escenarios')

c1 = t['bogota_camara']['c1']; j = c1['cols'].index('paloma')
qn = t['quintiles']['v1_v2']; nuevos = sum(q['nuevos'] for q in qn)
s1 = t['territorios']['Colombia']['s1']; v12 = t['territorios']['Colombia']['v12']
pc = lambda M, r, c: M['flujo'][M['filas'].index(r)][M['cols'].index(c)] / M['tot_filas'][M['filas'].index(r)]
ep = cl['episodios']['todos']
fz = {g['k']: g for g in cl['fuerzas']['lista']}
out = {
    'v': '2026-11-09',
    'tablero': {'nl_paloma': round(c1['flujo'][0][j] / c1['tot_filas'][0], 4), 'lo': c1['lo'][0][j], 'hi': c1['hi'][0][j],
                'nl_votos': c1['tot_filas'][0], 'nuevos': nuevos, 'nuevos_arriba': round((qn[3]['nuevos'] + qn[4]['nuevos']) / nuevos, 4),
                'pacto_cepeda': round(pc(s1, 'pacto', 'cepeda'), 4), 'cd_abelardo': round(pc(s1, 'cd', 'abelardo'), 4),
                'paloma_abelardo': round(pc(v12, 'paloma', 'abelardo'), 4),
                'liberal_casa': round(pc(s1, 'liberal', 'novoto'), 4), 'ahora_abelardo': round(pc(s1, 'ahora', 'abelardo'), 4),
                'fajardo_cepeda': round(pc(v12, 'fajardo', 'cepeda'), 4)},
    'inventario': {k: inv['resumen'][k] for k in ('congresistas', 'alcaldes', 'diputados', 'concejales', 'concejales_muns', 'concejales_propias', 'ediles')},
    'clima': {'titulares': cl['cobertura']['unicos'], 'dias': cl['cobertura']['dias'], 'ini': cl['cobertura']['ini'], 'fin': cl['cobertura']['fin'],
              'episodios': ep['n'], 'mediana': ep['mediana'], 'mas7': ep['mas7'], 'mas14': ep['mas14'],
              'nl_titulares': fz['nl']['total'] if 'nl' in fz else None, 'pacto_titulares': fz['pacto']['total'], 'cd_titulares': fz['cd']['total'],
              'galan_cf': next((g['total'] for g in cl['galanes']['lista'] if g['k'] == 'galan_cf'), None),
              'hist': ep.get('hist'), 'seg': [round(x, 4) for x in cl['agenda']['part'].get('seguridad', [])]},
    'escenarios': {k: {'pct': es['escenarios'][k]['pct'], 'votos': es['escenarios'][k]['votos'], 'curules': es['escenarios'][k]['curules']} for k in ('piso', 'base', 'techo')},
    'fuera': {k: es['fuera']['resumen'][k] for k in ('municipios', 'curules', 'con_curul', 'sin_curul_a_300')},
    'resolucion': es['calendario']['resolucion'],
}
json.dump(out, open(os.path.join(D, 'hub.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
