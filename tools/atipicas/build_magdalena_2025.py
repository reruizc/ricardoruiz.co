#!/usr/bin/env python3
"""Atípica a la Gobernación del Magdalena · 23-nov-2025 → atipicas/magdalena-2025.json

Fuentes:
  Bases de datos/FINAL SUBIDA GCS/GCS_2025ATIP_MAG.csv   votos mesa a mesa (consolidado RNEC)
  Bases de datos/censos-registraduria/2025_datos_censo-electoral-min.json
      censo de ESA elección por puesto (tipo «GOBERNADOR MAGDALENA»), con sexo y edad

⚠ El CSV llega con el texto en doble codificación («POLÃTICO»): se repara con
  latin-1 → utf-8 solo cuando la reparación es válida.
⚠ Los códigos del GCS vienen sin ceros (`8` y no `008`): se rellenan para casar con el
  censo y con el GeoJSON (`mun_elec`).
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
GCS = RAIZ / 'Bases de datos/FINAL SUBIDA GCS/GCS_2025ATIP_MAG.csv'
CENSO = RAIZ / 'Bases de datos/censos-registraduria/2025_datos_censo-electoral-min.json'
OUT = RAIZ / 'atipicas/magdalena-2025.json'

COLOR = {'3': '#f08c00', '4': '#7048e8', '1': '#e64980', '2': '#2f9e44'}
# cómo los nombra la prensa (el acta trae el nombre completo, sin tildes)
CORTO = {'3': 'Margarita Guerra', '4': 'Rafael Noya', '1': 'Miguel Martínez', '2': 'Luis Santana'}
ESPECIALES = {'996': 'blanco', '997': 'nulos', '998': 'nomarc'}


def fix(s):
    try:
        return s.encode('latin-1').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return s


def nice(s):
    minus = {'DE', 'DEL', 'LA', 'LAS', 'LOS', 'Y', 'EL', 'EN'}
    return ' '.join(w.lower() if i and w in minus else w.capitalize() for i, w in enumerate(' '.join(s.split()).split()))


censo = json.load(open(CENSO))
filas = next(iter(censo.values()))
puestos = {}
for r in filas:
    if r['tipo_eleccion'] != 'GOBERNADOR MAGDALENA':
        continue
    k = (r['cod_mun'].zfill(3), r['zona'].zfill(2), r['cod_puesto'].zfill(2))
    puestos[k] = {'nombre': r['puesto_votacion'].strip(), 'mun': r['municipio'].strip(),
                  'censo': r['potencial_electoral'], 'm': r['sexo']['mujeres'], 'h': r['sexo']['hombres']}

cands = {}
votos = defaultdict(lambda: defaultdict(int))
mesas = defaultdict(set)
with open(GCS, encoding='utf-8-sig') as f:
    for r in csv.DictReader(f, delimiter=';'):
        k = (r['COD_MME'].zfill(3), r['COD_ZZ'].zfill(2), r['COD_PP'].zfill(2))
        can = r['COD_CAN']
        v = int(r['NUM_VOT'])
        clave = ESPECIALES.get(can, can)
        votos[k][clave] += v
        mesas[k].add(r['DES_MS'])
        if can not in ESPECIALES and can not in cands:
            cands[can] = {'cod': can, 'nombre': nice(fix(r['DES_CAN'])), 'partido': nice(fix(r['DES_PAR'])),
                          'color': COLOR.get(can, '#868e96'), 'corto': CORTO.get(can, nice(fix(r['DES_CAN'])))}

orden = sorted(cands, key=lambda c: -sum(v.get(c, 0) for v in votos.values()))
sin_censo = [k for k in votos if k not in puestos]
out_puestos = []
for k in sorted(votos):
    p = puestos.get(k, {})
    out_puestos.append({
        'mun': k[0], 'zona': k[1], 'pue': k[2], 'nombre': p.get('nombre', f'Zona {k[1]} · puesto {k[2]}'),
        'censo': p.get('censo'), 'm': p.get('m'), 'h': p.get('h'), 'mesas': len(mesas[k]),
        'v': [votos[k].get(c, 0) for c in orden],
        'blanco': votos[k]['blanco'], 'nulos': votos[k]['nulos'], 'nomarc': votos[k]['nomarc'],
    })
muns = {}
for k, p in puestos.items():
    muns.setdefault(k[0], nice(p['mun']))

res = {
    'eleccion': 'Gobernación del Magdalena · elección atípica',
    'fecha': '2025-11-23',
    'fuente': 'Registraduría Nacional · consolidado mesa a mesa (GCS) · censo por puesto de la elección',
    'candidatos': [cands[c] for c in orden],
    'municipios': muns,
    'puestos': out_puestos,
    'censo_total': sum(p['censo'] for p in puestos.values()),
    'puestos_sin_censo': len(sin_censo),
}
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(res, ensure_ascii=False, separators=(',', ':')))
tot = [sum(p['v'][i] for p in out_puestos) for i in range(len(orden))]
blanco = sum(p['blanco'] for p in out_puestos)
nul = sum(p['nulos'] for p in out_puestos)
nm = sum(p['nomarc'] for p in out_puestos)
votantes = sum(tot) + blanco + nul + nm
print({cands[c]['nombre']: t for c, t in zip(orden, tot)}, 'blanco', blanco, 'nulos', nul, 'no marcados', nm)
print('votantes', votantes, 'censo', res['censo_total'], f"participación {votantes / res['censo_total']:.2%}")
print('puestos', len(out_puestos), 'sin censo', len(sin_censo), 'municipios', len(muns), '→', OUT, OUT.stat().st_size, 'bytes')
