#!/usr/bin/env python3
"""
Mi Congreso · Fuerzas internas de la legislatura VIVA.

Arma lo que la página «Fuerzas» (mi-congreso-fuerzas.html) necesita para la
cuenta en la comisión, con datos de ESTA legislatura y no de un gobierno
anterior:

  1. BANCADA OFICIAL de cada congresista. La lista con la que se eligió no es su
     bancada: María Lucía Villalba entró por «Ahora Colombia» y su bancada es
     Nuevo Liberalismo; Guevara y Agudelo entraron por la misma lista y son
     MIRA; Pedraza es Dignidad. Fuentes oficiales:
       · Senado:  app.senado.gov.co/backend/api/public/v1/senators (party_name,
                  commission_id = número de la comisión constitucional)
       · Cámara:  www.camara.gov.co/representantes (JSON embebido: Partido,
                  Comision)
  2. COINCIDENCIA DE VOTO en las plenarias de la legislatura viva (desde el 20
     de julio), persona a persona y por bancada. Hoy solo el Senado publica el
     voto nominal al día (API /votes); el de Cámara sale de las actas de
     plenaria, que llegan con meses de rezago, y por eso Cámara se lee con la
     coincidencia ENTRE BANCADAS medida en el Senado (declarado en la página).

Reglas de la medición:
  · Una «votación» es el bloque (fecha, proyecto) de la API: el Senado agrupa
    varias votaciones del mismo proyecto el mismo día. Dentro del bloque se toma
    el sentido mayoritario de cada senador.
  · Solo cuentan las votaciones DISPUTADAS (el lado minoritario ≥ 10 % de los
    votos): en una votación casi unánime todos coinciden y la cifra no dice nada.
  · Un par de personas necesita ≥ 8 votaciones disputadas compartidas; un par
    de bancadas, ≥ 10. Por debajo no se publica.

Salida: Bases de datos/legislativo/fuerzas-internas-2026.json
S3:     congreso-2026/output/legislativo/fuerzas-internas-2026.json (público)

  python3 tools/mi-congreso/build_fuerzas_internas.py            # baja y arma
  python3 tools/mi-congreso/build_fuerzas_internas.py --subir    # y sube a S3
"""
import collections
import csv
import io
import json
import re
import subprocess
import sys
import unicodedata
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / 'Bases de datos' / 'legislativo' / 'fuerzas-internas-2026.json'
S3_KEY = 's3://elecciones-2026/ricardoruiz.co/congreso-2026/output/legislativo/fuerzas-internas-2026.json'
API = 'https://app.senado.gov.co/backend/api/public/v1'
CAMARA = 'https://www.camara.gov.co/representantes'
DESDE = '2026-07-20'
MIN_MINORIA = 0.10
MIN_PAR = 8
MIN_BANC = 10
COM = {1: 'PRIMERA', 2: 'SEGUNDA', 3: 'TERCERA', 4: 'CUARTA', 5: 'QUINTA', 6: 'SEXTA', 7: 'SEPTIMA'}


def curl(url):
    r = subprocess.run(['curl', '-s', '-L', '--max-time', '240', '-A',
                        'Mozilla/5.0 (Macintosh) Chrome/130', url], capture_output=True, check=True)
    return r.stdout


def norm(s):
    s = unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', s)).strip()


# partido oficial → bancada canónica (la misma en las dos cámaras)
BANCADAS = [
    (r'pacto historico|colombia humana', 'Pacto Histórico'),
    (r'centro democratico', 'Centro Democrático'),
    (r'nuevo liberalismo', 'Nuevo Liberalismo'),
    (r'liberal', 'Partido Liberal'),
    (r'conservador', 'Partido Conservador'),
    (r'partido de la u\b|union por la gente', 'Partido de la U'),
    (r'cambio radical', 'Cambio Radical'),
    (r'alianza verde', 'Alianza Verde'),
    (r'\bmira\b', 'MIRA'),
    (r'salvacion nacional', 'Salvación Nacional'),
    (r'alianza social independiente|\basi\b', 'ASI'),
    (r'dignidad', 'Dignidad y Compromiso'),
    (r'democrata colombiano', 'Partido Demócrata'),
    (r'creemos', 'Creemos'),
    (r'colombia renaciente', 'Colombia Renaciente'),
    (r'la fuerza', 'La Fuerza'),
    (r'\blibres\b', 'Movimiento Libres'),
    (r'\bmais\b|alternativo indigena', 'MAIS'),
    (r'\baico\b|autoridades indigenas', 'AICO'),
    (r'minga', 'Unidad en Minga'),
    (r'alianza por colombia', 'Alianza por Colombia'),
    (r'oposicion|1909 de 2018', 'Estatuto de Oposición'),
]
CITREP = r'consejo comunitario|asociacion|asoprocacao|asomontemaria|asoambeima|uraba|ganaderos|resguardo|aprocasur|pa vida|paz es vida'


def bancada(partido):
    p = norm(partido)
    for rx, b in BANCADAS:
        if re.search(rx, p):
            return b
    if re.search(CITREP, p):
        return 'Curules de paz y étnicas'
    return partido.strip() or 'Sin dato'


def senado():
    sens = json.loads(curl(f'{API}/senators?format=json'))
    miembros = []
    for s in sens:
        if not s.get('name'):
            continue
        try:
            c = COM.get(int(s.get('commission_id') or 0))
        except ValueError:
            c = None
        miembros.append({'n': s['name'], 'k': norm(s['name']), 'p': s.get('party_name') or '',
                         'b': bancada(s.get('party_name') or ''), 'c': c})
    votes = list(csv.DictReader(io.StringIO(curl(f'{API}/votes?format=csv').decode('utf-8-sig'))))
    return miembros, votes


def camara():
    h = curl(CAMARA).decode('utf-8', 'ignore')
    objs = []
    for o in re.findall(r'\{[^{}]*"Partido":"[^"]*"[^{}]*\}', h):
        try:
            objs.append(json.loads(o))
        except json.JSONDecodeError:
            pass
    miembros = []
    for o in objs:
        m = re.search(r'(primera|segunda|tercera|cuarta|quinta|sexta|septima)', norm(o.get('Comision')))
        miembros.append({'n': o['Nombre'], 'k': norm(o['Nombre']), 'p': (o.get('Partido') or '').strip(),
                         'b': bancada(o.get('Partido') or ''), 'c': m.group(1).upper() if m else None})
    return miembros


def coincidencias(miembros, votes):
    """Pares de personas y de bancadas en las votaciones disputadas desde DESDE."""
    por_k = {m['k']: m for m in miembros}
    bloques = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in votes:
        f = (r.get('Fecha de la Plenaria') or '')[:10]
        if f < DESDE:
            continue
        resp = (r.get('Resultado') or '').strip()
        if resp not in ('Sí', 'Si', 'No'):
            continue
        bloques[(f, r.get('ID Proyecto'))][norm(r.get('Nombre del Senador'))].append(resp in ('Sí', 'Si'))
    disputadas = []
    for key, por in bloques.items():
        sent = {k: (sum(v) * 2 >= len(v)) for k, v in por.items() if k in por_k}
        if len(sent) < 10:
            continue
        si = sum(sent.values())
        if min(si, len(sent) - si) / len(sent) < MIN_MINORIA:
            continue
        disputadas.append((key, sent))
    # personas
    idx = {m['k']: i for i, m in enumerate(miembros)}
    iguales, juntos = collections.Counter(), collections.Counter()
    for _, sent in disputadas:
        ks = sorted(sent, key=lambda k: idx[k])
        for a in range(len(ks)):
            for b in range(a + 1, len(ks)):
                p = (idx[ks[a]], idx[ks[b]])
                juntos[p] += 1
                if sent[ks[a]] == sent[ks[b]]:
                    iguales[p] += 1
    pares = {f'{a}|{b}': [round(100 * iguales[(a, b)] / n, 1), n]
             for (a, b), n in juntos.items() if n >= MIN_PAR}
    # bancadas: coincidencia entre MAYORÍAS (una bancada partida por la mitad no entra)
    biguales, bjuntos = collections.Counter(), collections.Counter()
    for _, sent in disputadas:
        por_b = collections.defaultdict(list)
        for k, v in sent.items():
            por_b[por_k[k]['b']].append(v)
        may = {}
        for b, vs in por_b.items():
            si = sum(vs)
            if si * 2 != len(vs):
                may[b] = si * 2 > len(vs)
        bs = sorted(may)
        for a in range(len(bs)):
            for c in range(a + 1, len(bs)):
                bjuntos[(bs[a], bs[c])] += 1
                if may[bs[a]] == may[bs[c]]:
                    biguales[(bs[a], bs[c])] += 1
    bpares = {f'{a}|{c}': [round(100 * biguales[(a, c)] / n, 1), n]
              for (a, c), n in bjuntos.items() if n >= MIN_BANC}
    fechas = sorted({k[0] for k, _ in disputadas})
    return pares, bpares, {'votaciones': len(bloques), 'disputadas': len(disputadas),
                           'desde': fechas[0] if fechas else None, 'hasta': fechas[-1] if fechas else None}


def main():
    sen_m, votes = senado()
    cam_m = camara()
    pares, bpares, cob = coincidencias(sen_m, votes)
    out = {
        'v': date.today().isoformat(), 'legislatura': '2026-2027', 'desde': DESDE,
        'reglas': {'minoria_min': MIN_MINORIA, 'min_par': MIN_PAR, 'min_bancada': MIN_BANC},
        'fuentes': {'senado': f'{API}/senators · /votes', 'camara': CAMARA},
        'senado': {'miembros': [{k: m[k] for k in ('n', 'p', 'b', 'c')} for m in sen_m],
                   'pares': pares, 'cobertura': cob},
        'camara': {'miembros': [{k: m[k] for k in ('n', 'p', 'b', 'c')} for m in cam_m],
                   'pares': None,
                   'nota': 'El voto nominal de Cámara sale de las actas de plenaria, que llegan con meses de rezago; '
                           'mientras tanto se usa la coincidencia entre bancadas medida en el Senado.'},
        'bancadas': bpares,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'senado {len(sen_m)} miembros · cámara {len(cam_m)} · votaciones {cob["votaciones"]} '
          f'(disputadas {cob["disputadas"]}, {cob["desde"]} → {cob["hasta"]}) · pares {len(pares)} · '
          f'pares de bancada {len(bpares)} · {OUT.stat().st_size // 1024} KB')
    for k, v in sorted(bpares.items(), key=lambda x: -x[1][0])[:8]:
        print('  ', k, v)
    if '--subir' in sys.argv:
        subprocess.run(['aws', 's3', 'cp', str(OUT), S3_KEY, '--content-type', 'application/json',
                        '--cache-control', 'public, max-age=3600'], check=True)
        print('subido a', S3_KEY)


if __name__ == '__main__':
    main()
