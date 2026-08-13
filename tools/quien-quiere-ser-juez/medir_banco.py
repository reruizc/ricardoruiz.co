#!/usr/bin/env python3
"""Auditoría del banco de ¿Quién quiere ser juez?  ·  python3 tools/quien-quiere-ser-juez/medir_banco.py

Mide las tres cosas que se han dañado solas en versiones anteriores:
  1. Preguntas duplicadas (mismo contenido, distinta redacción) DENTRO y ENTRE pools.
     Entre pools importa porque la sala Promiscuo mezcla civil+penal+laboral+familia.
  2. El delator de longitud: si la opción correcta es la más larga, el aspirante
     acierta leyendo el formato y no el derecho. En v4 pasaba en el 77 % del banco.
  3. Reparto de dificultad por pool, para que el sorteo no tenga que repetir.
Sale con código 1 si encuentra duplicados o si el delator supera el 40 %.
"""
import json, re, subprocess, sys, pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
js = subprocess.run(
    ['node', '-e', 'global.window={};require(process.argv[1]);'
     'process.stdout.write(JSON.stringify(window.BANCO_JUDICIAL))',
     str(REPO / 'banco-judicial.js')],
    capture_output=True, text=True, check=True).stdout
B = json.loads(js)
POOLS = ['general', 'aptitudes', 'actualidad', 'comportamental', 'civil', 'penal',
         'laboral', 'administrativo', 'disciplinario', 'ejecucion', 'familia']

fallos = 0
print('POOL              tot   n1   n2   n3')
for p in POOLS:
    L = B.get(p, [])
    c = {1: 0, 2: 0, 3: 0}
    for q in L: c[q['n']] += 1
    print(f'{p:<16}{len(L):>5}{c[1]:>5}{c[2]:>5}{c[3]:>5}')

# 1 · duplicados
vistos, ids = {}, {}
norm = lambda t: re.sub(r'\W+', ' ', t.lower()).strip()[:55]
for p in POOLS:
    for q in B.get(p, []):
        if q['id'] in ids:
            print(f'  ⚠️ ID REPETIDO {q["id"]} ({p} y {ids[q["id"]]})'); fallos += 1
        ids[q['id']] = p
        k = norm(q['p'])
        if k in vistos:
            print(f'  ⚠️ DUPLICADA {q["id"]} ≈ {vistos[k]}'); fallos += 1
        vistos[k] = q['id']
        if len({o.strip().lower() for o in q['o']}) != 4:
            print(f'  ⚠️ OPCIONES REPETIDAS en {q["id"]}'); fallos += 1
        if not q.get('cita') or not q.get('pista'):
            print(f'  ⚠️ SIN CITA O PISTA {q["id"]}'); fallos += 1

# 2 · delator de longitud
tot = larga = 0
for p in POOLS:
    for q in B.get(p, []):
        tot += 1
        lens = [len(o) for o in q['o']]
        mx = max(lens)
        if lens[q['r']] == mx and lens.count(mx) == 1: larga += 1
pct = round(100 * larga / tot)
print(f'\ntotal {tot} preguntas · correcta = única más larga en {pct} % (azar ≈ 25 %)')
if pct > 40:
    print('  ⚠️ DELATOR DE LONGITUD: emparejar longitudes antes de publicar'); fallos += 1

print('\n✅ sin hallazgos' if not fallos else f'\n❌ {fallos} hallazgo(s)')
sys.exit(1 if fallos else 0)
