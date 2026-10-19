#!/usr/bin/env python3
"""Arraigo de cada candidatura al Concejo de Bogotá 2023 → candidato-360-data/arraigo-concejo-bogota-2023.json

El motor de estrategia decide «figura de ciudad o trabajo de barrio» con el
arraigo que ya midió el estudio de arquetipos de Bogotá
(tools/candidato-360/arquetipos-bogota/medir.py): cuánto de la votación de una
candidatura se aparta de la geografía de su propia lista, descontado lo que se
apartaría por azar. Se mide a escala de localidad y de barrio y se toma la
mayor (es lo que hace el estudio para el total de la ciudad).

Ese dato vivía solo en un CSV local. Aquí se publica por SLUG (el mismo del
índice de candidaturas que usa el CRM), sin nombres: el slug es un código.

    python3 tools/candidato-360/estrategia/build_arraigo.py
"""
import csv, gzip, json, re, sys, unicodedata, urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
CSV = RAIZ / 'Bases de datos/arquetipos-bogota/candidatos-concejo-2023.csv'
INDICE = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/concejo-2023/index-concejo-2023.json'
SALIDA = RAIZ / 'candidato-360-data/arraigo-concejo-bogota-2023.json'


def norm(s):
    s = unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode()
    return re.sub(r'[^A-Z0-9]+', ' ', s.upper()).strip()


def bajar(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'candidato-360/estrategia', 'Accept-Encoding': 'gzip'})
    with urllib.request.urlopen(req, timeout=60) as r:
        crudo = r.read()
    if crudo[:2] == b'\x1f\x8b':   # los índices de S3 van comprimidos
        crudo = gzip.decompress(crudo)
    return json.loads(crudo)


def main():
    filas = list(csv.DictReader(CSV.open(encoding='utf-8')))
    indice = [c for c in bajar(INDICE)['candidatos'] if c['slug'].startswith('CONC2023-16-1-')]
    por_par = {(norm(c['nombre']), norm(c['partido'])): c['slug'] for c in indice}
    por_nombre = {}
    for c in indice:
        por_nombre.setdefault(norm(c['nombre']), []).append(c['slug'])
    out, sin = {}, []
    tot_v = tot_a = 0.0
    for f in filas:
        a_loc, a_bar, votos = float(f['arraigo_localidad']), float(f['arraigo_barrio']), int(f['votos'])
        slug = por_par.get((norm(f['candidato']), norm(f['partido'])))
        if not slug and len(por_nombre.get(norm(f['candidato']), [])) == 1:
            slug = por_nombre[norm(f['candidato'])][0]
        tot_v += votos
        tot_a += votos * max(a_loc, a_bar)
        if not slug:
            sin.append(f['candidato'])
            continue
        out[slug] = [round(a_loc, 3), round(a_bar, 3)]
    if sin:
        sys.exit(f'{len(sin)} candidaturas sin slug en el índice: {sin[:5]}')
    datos = {
        'v': '2026-10-19',
        'que': 'Arraigo de cada candidatura al Concejo de Bogotá 2023: [localidad, barrio], la parte de su votación que se aparta de la geografía de su propia lista descontado el azar. Se usa la mayor de las dos.',
        'fuente': 'tools/candidato-360/arquetipos-bogota/medir.py sobre resultados oficiales del Concejo 2023 (Registraduría); fuera las zonas 90 y 98.',
        # La referencia: la ciudad, ponderada por votos, con la misma regla (la mayor de las dos escalas).
        'referencia': round(tot_a / tot_v, 4),
        'slugs': dict(sorted(out.items())),
    }
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'{SALIDA.relative_to(RAIZ)}: {len(out)} candidaturas · referencia de la ciudad {datos["referencia"]:.1%} · {SALIDA.stat().st_size // 1024} KB')


if __name__ == '__main__':
    main()
