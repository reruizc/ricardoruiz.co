#!/usr/bin/env python3
"""Video semanal · composición de los escenarios donde se decide cada tema y su
historial de voto.

  · Comisión Séptima de Cámara (cuidado, contrato sindical): miembros por bancada y
    cómo votaron la reforma laboral de Petro en la plenaria (título y pregunta del
    17-oct-2024 y conciliación del 20-jun-2025), solo los que ya eran representantes.
  · Comisiones económicas conjuntas (Terceras y Cuartas de las dos cámaras): miembros
    por bancada y, para los senadores, si votaron el Presupuesto 2027 el 19-oct-2026
    (API de voto nominal del Senado; solo registra los Sí).
Salida: Bases de datos/video-semanal/<semana>/escenarios.json
"""
import collections, csv, io, json, re, sys, unicodedata, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SEMANA = sys.argv[1] if len(sys.argv) > 1 else '2026-10-27'
OUT = REPO / 'Bases de datos/video-semanal' / SEMANA / 'escenarios.json'
INT = json.load(open(REPO / 'Bases de datos/legislativo/fuerzas-internas-2026.json'))
VOT = REPO / 'Bases de datos/leyes-senado/dist/votaciones-camara-nominal.jsonl'
SEN_VOTES = 'https://app.senado.gov.co/backend/api/public/v1/votes?format=csv'


def norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper()
    return re.sub(r'\s+', ' ', re.sub(r'[^A-Z ]', ' ', s)).strip()


def toks(s):
    return frozenset(t for t in norm(s).split() if len(t) > 2)


def misma(a, b):
    i = a & b
    return len(i) >= 3 or (len(i) >= 2 and (a <= b or b <= a))


LABORAL = {('2024-10-17', '43572', 8): 'laboral_titulo_2024', ('2025-06-20', '43227', 1): 'laboral_conciliacion_2025'}
lab = {v: {} for v in LABORAL.values()}
for line in open(VOT, encoding='utf-8'):
    r = json.loads(line)
    k = LABORAL.get((r['fecha'], r['acta_id'], r['votacion_numero']))
    n = r.get('roster_key') or r.get('congresista')
    if k and n:
        lab[k][toks(n)] = r['respuesta']

cam = INT['camara']['miembros']
sen = INT['senado']['miembros']
septima = []
for m in cam:
    if m.get('c') != 'SEPTIMA':
        continue
    t = toks(m['n'])
    f = {'nombre': m['n'], 'bancada': m['b']}
    for k, d in lab.items():
        hit = next((v for kk, v in d.items() if misma(t, kk)), None)
        if hit:
            f[k] = hit
    septima.append(f)

req = urllib.request.Request(SEN_VOTES, headers={'User-Agent': 'Mozilla/5.0 video-semanal'})
rows = list(csv.DictReader(io.StringIO(urllib.request.urlopen(req, timeout=120).read().decode('utf-8-sig'))))
pgn = {toks(r['Nombre del Senador']): r['Resultado'] for r in rows
       if r['Fecha de la Plenaria'] == '2026-10-19' and '111 de 2026' in r['Proyecto de ley']}

economicas = []
for corp, lista in (('Senado', sen), ('Cámara', cam)):
    for m in lista:
        if m.get('c') not in ('TERCERA', 'CUARTA'):
            continue
        f = {'nombre': m['n'], 'bancada': m['b'], 'corp': corp, 'comision': m['c']}
        if corp == 'Senado':
            f['pgn2027_19oct'] = next((v for kk, v in pgn.items() if misma(toks(m['n']), kk)), 'sin registro')
        economicas.append(f)

pgn_senado = collections.defaultdict(collections.Counter)
for m in sen:
    v = next((v for kk, v in pgn.items() if misma(toks(m['n']), kk)), 'sin registro')
    pgn_senado[m['b']][v] += 1


def por_bancada(lista, campo=None):
    c = collections.defaultdict(collections.Counter)
    for f in lista:
        c[f['bancada']]['total'] += 1
        if campo:
            c[f['bancada']][f.get(campo, 'no estaba')] += 1
    return {b: dict(x) for b, x in sorted(c.items(), key=lambda kv: -kv[1]['total'])}


res = {
    'semana': SEMANA,
    'septima_camara': {'miembros': septima, 'por_bancada': por_bancada(septima, 'laboral_conciliacion_2025')},
    'economicas_conjuntas': {'miembros': economicas,
                             'por_bancada_senado': por_bancada([f for f in economicas if f['corp'] == 'Senado'], 'pgn2027_19oct'),
                             'por_bancada_camara': por_bancada([f for f in economicas if f['corp'] == 'Cámara'])},
    'senado_pgn2027_19oct': {'total_si': sum(1 for v in pgn.values() if v.startswith('S')),
                             'por_bancada': {b: dict(x) for b, x in sorted(pgn_senado.items(), key=lambda kv: -sum(kv[1].values()))}},
}
OUT.parent.mkdir(parents=True, exist_ok=True)
json.dump(res, open(OUT, 'w'), ensure_ascii=False, indent=1)
print('Séptima Cámara:', len(septima)); [print('  ', b, x) for b, x in res['septima_camara']['por_bancada'].items()]
print('Económicas conjuntas:', len(economicas))
print(' Senado', res['economicas_conjuntas']['por_bancada_senado'])
print(' Cámara', res['economicas_conjuntas']['por_bancada_camara'])
print('PGN Senado 19-oct:', res['senado_pgn2027_19oct'])
print('→', OUT)
