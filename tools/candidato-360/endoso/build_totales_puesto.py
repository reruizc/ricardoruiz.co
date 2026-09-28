#!/usr/bin/env python3
"""build_totales_puesto.py — votos válidos y votantes por puesto, por elección.

Los JSON mesa a mesa de cada candidatura traen SOLO sus votos: no dicen cuántos
votaron en ese puesto. Sin ese total no hay participación de nadie, y sin
participación no hay regresión ecológica (fase 4 del endoso, ver PLAN.md): un
puesto donde el aliado sacó cero votos también es información, y no existe en
ningún archivo de candidatura.

Una pasada por cada GCS de la Registraduría, juntando todas las corporaciones a
la vez. Por puesto:
    [válidos, votantes, blanco]
  · válidos  = todo menos nulos (997), no marcados (998) y 999. El voto en
               blanco (996) SÍ es válido, y el voto al logo (COD_CAN 0) también.
  · votantes = todo, incluidos nulos y no marcados.
  · blanco   = el 996, aparte: hay cifras del proyecto que dicen «válidos» sin
               contarlo. Verificado en el Concejo de Bogotá 2023: 2.806.148
               válidos con blanco − 368.831 de blanco = 2.437.317, la cifra que
               usa la meta de votos.
Verificado que 2011 → 2023 y Congreso 2014 → 2022 usan esos mismos códigos
(2011, 2015 y la JAL de 2019 escriben distinto el texto, no el código).

El código de puesto es el de la hoja de vida: departamento (2) + municipio (3) +
zona (2) + puesto (2, con la letra que traen 187 puestos del país). Igual que
`codigoPuesto` de candidato-360-endoso.js: si una cambia sin la otra, los
puestos dejan de casar y la regresión se queda sin datos sin dar error.

⚠️ El orden de columnas cambia por archivo: se toman los layouts del
constructor territorial (build_territorial_candidatos.py), que ya los resolvió
año por año. 2011 lleva los votos ANTES del candidato.

Salida: Bases de datos/output_totales_puesto/{corp}-{año}.json
    {"v", "eleccion", "puestos": {"160011001": [válidos, votantes, blanco], …}}

  python3 tools/candidato-360/endoso/build_totales_puesto.py            (todo)
  python3 tools/candidato-360/endoso/build_totales_puesto.py 2023TER    (un archivo)

Subir (comprimido, como los índices):
  for f in "Bases de datos/output_totales_puesto/"*.json; do
    gzip -9 -c "$f" | aws s3 cp - "s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/totales-puesto/$(basename "$f")" \
      --content-encoding gzip --content-type application/json --cache-control "public, max-age=3600"
  done
"""
import csv, importlib.util, json, os, sys, time
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(AQUI)))
GCS = os.path.join(ROOT, 'Bases de datos', 'FINAL SUBIDA GCS')
SALIDA = os.path.join(ROOT, 'Bases de datos', 'output_totales_puesto')

_spec = importlib.util.spec_from_file_location('terr', os.path.join(ROOT, 'tools', 'analisis-candidato', 'build_territorial_candidatos.py'))
_terr = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_terr)
TER, JAL19, T2011 = _terr.LAYOUT_TER, _terr.LAYOUT_JAL19, _terr.LAYOUT_2011

# Archivo → (layout, año, {COD_COR: corporación}). Los códigos de corporación
# cambian por año: los mismos que usa build_territorial_candidatos.py.
ARCHIVOS = {
    '2011TER': (T2011, 2011, {'4': 'gobernacion', '5': 'asamblea', '6': 'alcaldia', '7': 'concejo', '8': 'jal'}),
    '2015TER': (TER,   2015, {'1': 'gobernacion', '2': 'asamblea', '3': 'alcaldia', '4': 'concejo', '5': 'jal'}),
    '2019TER': (TER,   2019, {'4': 'gobernacion', '5': 'asamblea', '6': 'alcaldia', '7': 'concejo'}),
    '2019JAL': (JAL19, 2019, {'5': 'jal'}),
    '2023TER': (TER,   2023, {'1': 'gobernacion', '2': 'asamblea', '3': 'alcaldia', '4': 'concejo'}),
    '2023JAL': (TER,   2023, {'5': 'jal'}),
    '2014CON': (TER,   2014, {'1': 'senado', '2': 'camara'}),
    '2018CON': (TER,   2018, {'1': 'senado', '2': 'camara'}),
    '2022CON': (TER,   2022, {'1': 'senado', '2': 'camara'}),
}
NO_VALIDOS = {'997', '998', '999'}


def pad(v, n):
    d = ''.join(c for c in (v or '') if c.isdigit())
    return d.zfill(n)


def codigo(dep, mun, zon, pue):
    return pad(dep, 2) + pad(mun, 3) + pad(zon, 2) + (pue or '').strip().upper().zfill(2)


def procesar(nombre):
    L, ano, cors = ARCHIVOS[nombre]
    ruta = os.path.join(GCS, f'GCS_{nombre}.csv')
    t0 = time.time()
    acc = {c: defaultdict(lambda: [0, 0, 0]) for c in cors.values()}
    filas = sin_cor = 0
    with open(ruta, encoding='utf-8-sig', errors='replace', newline='') as f:
        lector = csv.reader(f, delimiter=';')
        next(lector, None)
        for r in lector:
            if len(r) < L['NCOL']:
                continue
            corp = cors.get(r[L['COR']].strip())
            if corp is None:
                sin_cor += 1
                continue
            try:
                v = int(r[L['VOT']] or 0)
            except ValueError:
                continue
            if v <= 0:
                continue
            filas += 1
            p = acc[corp][codigo(r[L['DDE']], r[L['MME']], r[L['ZZ']], r[L['PP']])]
            p[1] += v
            can = r[L['CAN']].strip()
            if can not in NO_VALIDOS:
                p[0] += v
            if can == '996':
                p[2] += v
    print(f'· {nombre}: {filas:,} filas en {time.time() - t0:.0f} s' + (f' ({sin_cor:,} de otras corporaciones)' if sin_cor else ''))
    os.makedirs(SALIDA, exist_ok=True)
    for corp, puestos in acc.items():
        if not puestos:
            continue
        salida = os.path.join(SALIDA, f'{corp}-{ano}.json')
        datos = {'v': time.strftime('%Y-%m-%d'), 'eleccion': f'{corp} {ano}', 'fuente': f'GCS_{nombre}.csv',
                 'puestos': {k: puestos[k] for k in sorted(puestos)}}
        with open(salida, 'w') as g:
            json.dump(datos, g, separators=(',', ':'))
        val = sum(x[0] for x in puestos.values()); vot = sum(x[1] for x in puestos.values())
        print(f'    {corp}-{ano}: {len(puestos):,} puestos · {val:,} válidos · {vot:,} votantes · {os.path.getsize(salida) / 1e3:.0f} KB')


if __name__ == '__main__':
    claves = sys.argv[1:] or list(ARCHIVOS)
    for c in claves:
        if c not in ARCHIVOS:
            sys.exit(f'archivo desconocido: {c} (válidos: {", ".join(ARCHIVOS)})')
    for c in claves:
        procesar(c)
