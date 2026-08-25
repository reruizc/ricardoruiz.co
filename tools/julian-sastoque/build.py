#!/usr/bin/env python3
"""Construye la ficha territorial 2023 de Julián Rodríguez Sastoque.

Lee únicamente las filas del candidato en el GCS territorial y las agrega por
localidad, puesto y barrio catastral. La salida la consume
``julian-rodriguez-sastoque.html``.
"""
import csv
import json
import os
import unicodedata
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASES = os.path.join(ROOT, 'Bases de datos')
GCS = os.path.join(BASES, 'FINAL SUBIDA GCS', 'GCS_2023TER.csv')
PIP = os.path.join(BASES, 'output_trasvase', 'bog-puesto-to-barrio-pip.json')
GEO = os.path.join(BASES, 'output_pacto_1v_2026', 'geo', 'BOG-BARRIOS-CATASTRALES.json')
OUT = os.path.join(ROOT, 'julian-rodriguez-sastoque', 'datos', 'jrs-electoral.json')

CANDIDATO = 'JULIAN DAVID RODRIGUEZ SASTOQUE'
LOC = {
    '01':'Usaquén','02':'Chapinero','03':'Santa Fe','04':'San Cristóbal','05':'Usme',
    '06':'Tunjuelito','07':'Bosa','08':'Kennedy','09':'Fontibón','10':'Engativá',
    '11':'Suba','12':'Barrios Unidos','13':'Teusaquillo','14':'Los Mártires',
    '15':'Antonio Nariño','16':'Puente Aranda','17':'La Candelaria',
    '18':'Rafael Uribe Uribe','19':'Ciudad Bolívar','20':'Sumapaz'
}

def clean(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value or '')
                   if unicodedata.category(c) != 'Mn').upper().strip()

def main():
    pip = json.load(open(PIP, encoding='utf-8'))
    geo = json.load(open(GEO, encoding='utf-8'))['features']
    nombres_barrio = {str(f['properties'].get('codigo', '')).zfill(6):
                      f['properties'].get('nombre', 'Sin nombre') for f in geo}
    loc, barrio = Counter(), Counter()
    puestos = defaultdict(lambda: {'v': 0, 'mesas': 0})
    total = 0
    partido = ''
    with open(GCS, encoding='utf-8-sig', errors='replace', newline='') as source:
        rows = csv.reader(source, delimiter=';')
        next(rows, None)
        for row in rows:
            # COR=4 Concejo; Bogotá D.C.; candidato por nombre, sin depender
            # del código nominal de la lista.
            if (len(row) < 16 or row[2] != '4' or row[6].zfill(2) != '16'
                    or row[7].zfill(3) != '001'):
                continue
            if clean(row[14]) != CANDIDATO:
                continue
            try:
                votos = int(row[15] or 0)
            except ValueError:
                continue
            if not votos:
                continue
            zona, puesto, mesa = row[8].zfill(2), row[9].zfill(2), row[10].zfill(3)
            key = zona + '-' + puesto
            total += votos
            loc[zona] += votos
            partido = row[12] or partido
            puestos[key]['v'] += votos
            puestos[key]['mesas'] += 1
            puestos[key].update({'code': key, 'zona': zona, 'puesto': puesto})
            b = pip.get(key)
            if b:
                barrio[b] += votos

    ranking_loc = sorted(loc.items(), key=lambda x: (-x[1], x[0]))
    out = {
        'version': '2026-08-25', 'nombre': 'Julián David Rodríguez Sastoque',
        'partido': partido, 'anio': 2023, 'votos': total, 'localidades': [
            {'codigo': c, 'nombre': LOC.get(c, 'Puesto especial'), 'votos': v,
             'pct': round(v * 100 / total, 2), 'rank': i + 1}
            for i, (c, v) in enumerate(ranking_loc)
        ],
        'puestos': sorted(puestos.values(), key=lambda x: (-x['v'], x['code'])),
        'barrios': [
            {'codigo': c, 'nombre': nombres_barrio.get(c, c),
             'votos': v, 'pct': round(v * 100 / total, 2)}
            for c, v in barrio.most_common()
        ],
        'cobertura_barrios': round(sum(barrio.values()) * 100 / total, 2) if total else 0,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as target:
        json.dump(out, target, ensure_ascii=False, separators=(',', ':'))
    print(f"{total:,} votos · {len(puestos):,} puestos · {len(barrio):,} barrios → {OUT}")

if __name__ == '__main__':
    main()
