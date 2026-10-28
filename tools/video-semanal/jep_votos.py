#!/usr/bin/env python3
"""Video semanal · cierre de la JEP en 2028 (Acto Legislativo 018 de 2026 Senado).

Quién decide el primer debate en la Comisión Primera del Senado y qué dice su historial:
  · firmantes del proyecto (orden del día de la Comisión Primera, 28-oct-2026);
  · coincidencia de voto con el autor (Enrique Gómez, Salvación Nacional) en las votaciones
    disputadas de esta legislatura (fuerzas-internas-2026.json: persona a persona si comparten
    ≥8 votaciones; si no, bancada contra bancada);
  · quién de los 103 senadores actuales votó en 2017 el acto legislativo que creó la JEP
    (API de voto nominal del Senado, AL 002 de 2016 Cámara · 02 de 2017 Senado).

  python3 tools/video-semanal/jep_votos.py 2026-10-28
Salida: Bases de datos/video-semanal/<semana>/jep.json
"""
import csv, collections, io, json, re, sys, unicodedata, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SEMANA = sys.argv[1] if len(sys.argv) > 1 else '2026-10-28'
OUT = REPO / 'Bases de datos/video-semanal' / SEMANA / 'jep.json'
INT = json.load(open(REPO / 'Bases de datos/legislativo/fuerzas-internas-2026.json'))
SEN_VOTES = 'https://app.senado.gov.co/backend/api/public/v1/votes?format=csv'

AUTORES_SEN = ('Enrique Gómez Martínez|Sara Jimena Castellanos Rodríguez|Germán Andrés Rodríguez Prieto|'
               'Alfredo Rafael Deluque Zuleta|John Alejandro Bermeo Rodríguez|Selmen David Arana Cano|'
               'Jonathan Ferney Pulido Hernández|Edgardo Miguel Espitia Cabrales|Gonzalo Dimas Baute González|'
               'José Nicolás Gómez Medina|Luis Eduardo Díaz Mateus|Claudia Margarita Zuleta Murgas|'
               'María Clara Posada Caicedo|Juan Carlos García Gómez|Didier Lobo Chinchilla').split('|')
AUTORES_CAM = ['Carol Stefanny Borda Acevedo', 'Simón Molina Gómez']
AUTOR = 'Gómez Martínez Enrique'
# Falsos positivos del cruce por nombre: el senador de 2017 era Eduardo Enrique Pulgar, no Yessid.
NO_ES = {('Pulgar Daza Yessid Enrique', 'Pulgar Daza Eduardo Enrique')}


def norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper()
    return re.sub(r'\s+', ' ', re.sub(r'[^A-Z ]', ' ', s)).strip()


def toks(s):
    return frozenset(t for t in norm(s).split() if len(t) > 2)


def misma(a, b):
    i = a & b
    return len(i) >= 3 or (len(i) >= 2 and (a <= b or b <= a))


sen, cam = INT['senado']['miembros'], INT['camara']['miembros']
pares, banc = INT['senado']['pares'], INT['bancadas']
ia = next(i for i, m in enumerate(sen) if m['n'] == AUTOR)


def par(i, j):
    return pares.get(f'{min(i, j)}|{max(i, j)}')


def par_banc(a, b):
    return banc.get('|'.join(sorted([a, b])))


firm = collections.Counter()
for lst, aut in ((sen, AUTORES_SEN), (cam, AUTORES_CAM)):
    for a in aut:
        m = next((m for m in lst if misma(toks(a), toks(m['n']))), None)
        firm[m['b'] if m else 'sin cruce'] += 1

primera = []
for i, m in enumerate(sen):
    if m.get('c') != 'PRIMERA':
        continue
    f = {'nombre': m['n'], 'bancada': m['b'], 'firmo': any(misma(toks(a), toks(m['n'])) for a in AUTORES_SEN)}
    if m['n'] == AUTOR:
        f['coincide'] = None
    elif (p := par(i, ia)):
        f['coincide'], f['n_votos'], f['base'] = p[0], p[1], 'persona'
    elif m['b'] == 'Salvación Nacional':
        f['coincide'], f['base'] = 100.0, 'misma bancada'
    elif (p := par_banc(m['b'], 'Salvación Nacional')):
        f['coincide'], f['n_votos'], f['base'] = p[0], p[1], 'bancada'
    else:
        f['coincide'], f['base'] = None, 'sin dato'
    primera.append(f)

req = urllib.request.Request(SEN_VOTES, headers={'User-Agent': 'Mozilla/5.0 video-semanal'})
rows = list(csv.DictReader(io.StringIO(urllib.request.urlopen(req, timeout=120).read().decode('utf-8-sig'))))
jep17 = [r for r in rows if r['Fecha de la Plenaria'] in ('2017-03-08', '2017-03-13', '2017-03-22')
         and '002 de 2016' in r['Proyecto de ley']]
tot17 = {d: collections.Counter(r['Resultado'] for r in jep17 if r['Fecha de la Plenaria'] == d)
         for d in ('2017-03-08', '2017-03-13', '2017-03-22')}
votos17 = collections.defaultdict(dict)
nom17 = {}
for r in jep17:
    k = toks(r['Nombre del Senador'])
    votos17[k][r['Fecha de la Plenaria']] = r['Resultado']
    nom17[k] = r['Nombre del Senador'].strip()
repiten = []
for m in sen:
    for k, v in votos17.items():
        if misma(toks(m['n']), k) and (m['n'], nom17[k]) not in NO_ES:
            repiten.append({'nombre': m['n'], 'bancada': m['b'], 'comision': m.get('c'), 'nombre_2017': nom17[k], 'votos': v})

res = {
    'semana': SEMANA,
    'proyecto': 'Acto Legislativo 018 de 2026 Senado',
    'primera_senado': primera,
    'firmantes_por_bancada': dict(firm.most_common()),
    'n_firmantes': sum(firm.values()),
    'jep_2017': {'totales': {d: dict(c) for d, c in tot17.items()}, 'senadores_actuales_que_votaron': repiten},
    'cobertura_coincidencia': INT['senado']['cobertura'],
}
OUT.parent.mkdir(parents=True, exist_ok=True)
json.dump(res, open(OUT, 'w'), ensure_ascii=False, indent=1)
for f in primera:
    print(f"  {f['nombre'][:34]:34} {f['bancada'][:20]:20} {'FIRMÓ' if f['firmo'] else '     '} {f.get('coincide')} {f.get('base', '')}")
print('Firmantes:', res['n_firmantes'], res['firmantes_por_bancada'])
print('2017:', res['jep_2017']['totales'])
print('Senadores actuales que votaron en 2017:', [(x['nombre'], x['votos']) for x in repiten])
print('→', OUT)
