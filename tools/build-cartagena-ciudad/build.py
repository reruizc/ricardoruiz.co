#!/usr/bin/env python3
"""Cartagena para Veleta y Oportunidad: las 10 señales por unidad + el censo.

Las otras catorce ciudades de esos módulos tienen su carpeta en
`output_ciudades/{ciudad}/` con una votación por comuna por señal. Cartagena no
la tenía, y por eso no estaba en el mapa de ninguno de los dos.

⚠️⚠️ **La unidad es la UCG, no la que trae el archivo.** El georef y los CSV de
la Registraduría solo le ponen a Cartagena sus 3 LOCALIDADES (`COMUCODIGO`
01/02/03), y con tres polígonos no hay mapa: su división operativa son las 15
Unidades Comuneras de Gobierno más la 20 (corregimientos e islas). La UCG de
cada puesto se lee de `output_hvp/cartagena-puesto-ucg.json` —el mismo archivo
que usan el CRM y los tableros— para que la cuenta no viva en dos sitios.
Con `--unidad localidad` se emite la versión de 3, que es lo que el dato trae.

Salidas (gitignored, se suben a S3 bajo `bases+de+datos/output_ciudades/`):
  cartagena/historicos-comuna/pres-{2010,2014,2018,2022}/por-comuna.json
  cartagena/historicos-comuna/consulta-2025-pacto/por-comuna.json
  cartagena/2026/{senado,camara,consultas-gran,consultas-frente,consultas-soluciones}/por-comuna.json
  cartagena/censo-comuna.json

Después:  node tools/bloques-historicos/build-comunas.js   (arma el archivo que
lee Veleta desde los cuatro presidenciales).

Correr:  python3 tools/build-cartagena-ciudad/build.py [--unidad ucg|localidad]
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BD = os.path.join(RAIZ, 'Bases de datos')
GCS = os.path.join(BD, 'FINAL SUBIDA GCS')
MMV = os.path.join(BD, 'DEPTOS_DECLARADOS', 'MMV_XXX_05_000_XXX_XX_XX_XXX_1002.csv')
UCG_PUESTOS = os.path.join(BD, 'output_hvp', 'cartagena-puesto-ucg.json')
UCG_GEO = os.path.join(BD, 'output_hvp', 'CARTAGENA-UCG.json')
LOC_GEO = os.path.join(BD, 'output_hvp', 'CARTAGENA-LOCALIDADES.json')
GEOREF = os.path.join(BD, 'PUESTOS_GEOREF.csv')
CENSO = os.path.join(BD, 'COMUNAS_DATA.csv')
# El censo de la época, por puesto, que ya emitió `build-censo-divipole.py`:
# es el denominador de la abstención 2018 y 2022 del módulo Oportunidad.
CENSO_VIEJO = {'2022': os.path.join(BD, 'censos-puesto-2022.json'),
               '2018': os.path.join(BD, 'censos-puesto-2018.json')}
SALIDA = os.path.join(BD, 'output_ciudades', 'cartagena')

DEP, MUN = 5, 1
# Los presidenciales y la consulta del Pacto: se leen por NOMBRE de columna
# porque el orden cambia entre años (2010 trae la geografía primero y 2025
# arranca por la circunscripción); por nombre los seis archivos son iguales.
HISTORICOS = [
    ('historicos-comuna/pres-2010', 'GCS_2010PRES1V.csv'),
    ('historicos-comuna/pres-2014', 'GCS_2014PRES1V.csv'),
    ('historicos-comuna/pres-2018', 'GCS_2018PRES1V.csv'),
    ('historicos-comuna/pres-2022', 'GCS_2022PRES1V.csv'),
    ('historicos-comuna/consulta-2025-pacto', 'GCS_2025CONSU.csv'),
]
# 2026: un solo archivo por departamento. La corporación separa Senado de
# Cámara, y dentro de consultas el PARTIDO separa las tres.
CONSULTAS_2026 = {'0200': '2026/consultas-gran', '0300': '2026/consultas-frente',
                  '0100': '2026/consultas-soluciones'}
ESPECIAL = {'996': 'blanco', '997': 'nulos', '998': 'no_marcados', '999': 'no_marcados'}


def pad(v, n):
    return str(v or '').strip().upper().rjust(n, '0')[-n:] if str(v or '').strip() else '0' * n


def clave_puesto(zona, puesto):
    """El pcode de 9 que usan el georef y el mapa de UCG."""
    return f'{DEP:02d}{MUN:03d}{pad(zona, 2)}{pad(puesto, 2)}'


def mapa_unidades(unidad):
    """{pcode: (código de unidad, nombre)} y el rótulo del nivel."""
    if unidad == 'ucg':
        with open(UCG_PUESTOS, encoding='utf-8') as f:
            puestos = json.load(f)
        with open(UCG_GEO, encoding='utf-8') as f:
            nombres = {ft['properties']['CODIGO']: ft['properties']['NOMBRE']
                       for ft in json.load(f)['features']}
        return {k: (v, nombres.get(v, f'UCG {int(v)}')) for k, v in puestos.items()}, 'UCG'
    # Localidad: viene en el georef, que es de donde la toman los CSV.
    with open(LOC_GEO, encoding='utf-8') as f:
        nombres = {ft['properties']['CODIGO']: ft['properties']['NOMBRE']
                   for ft in json.load(f)['features']}
    out = {}
    with open(GEOREF, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f, delimiter=';'):
            code = (row.get('CÓDIGO COMPLETO') or '').strip()
            if code[:5] != '05001':
                continue
            cod = pad(row.get('CÓDIGO COMUNA'), 2)
            if cod in nombres:
                out[code] = (cod, nombres[cod])
    return out, 'localidad'


def vacio():
    return {'candidatos': {}, 'partidos': {}, 'especiales': {'blanco': 0, 'nulos': 0, 'no_marcados': 0}}


def volcar(acc, unidades, ruta, fuente, señal):
    """Del acumulado al shape que leen Veleta y Oportunidad."""
    por_comuna = {}
    for cod, datos in sorted(acc.items()):
        cands = sorted(datos['candidatos'].items(), key=lambda kv: -kv[1])
        validos = sum(v for _, v in cands)
        esp = datos['especiales']
        total = validos + sum(esp.values())
        por_comuna[cod] = {
            'cod': cod, 'nombre': unidades[cod],
            'votos_validos': validos, 'votos_totales': total, 'especiales': esp,
            'candidatos': [{'nombre': n, 'partido': datos['partidos'].get(n, ''), 'votos': v,
                            'pct': round(v / validos * 100, 3) if validos else 0}
                           for n, v in cands],
        }
    destino = os.path.join(SALIDA, ruta)
    os.makedirs(destino, exist_ok=True)
    archivo = os.path.join(destino, 'por-comuna.json')
    with open(archivo, 'w', encoding='utf-8') as f:
        json.dump({'meta': {'fuente': fuente, 'generado': datetime.now(timezone.utc).isoformat(),
                            'ciudad': 'cartagena', 'signal': señal}, 'por_comuna': por_comuna},
                  f, ensure_ascii=False, separators=(',', ':'))
    votos = sum(c['votos_validos'] for c in por_comuna.values())
    print(f'  {señal:<32} {len(por_comuna):>2} unidades · {votos:>9,} válidos · '
          f'{os.path.getsize(archivo)/1024:>6.0f} KB')
    return votos


def suma(acc, cod, nombre, partido, votos, especial=None):
    d = acc.setdefault(cod, vacio())
    if especial:
        d['especiales'][especial] += votos
    else:
        d['candidatos'][nombre] = d['candidatos'].get(nombre, 0) + votos
        d['partidos'].setdefault(nombre, partido)


def historico(mapa, archivo, ruta, señal):
    acc, sin_unidad = {}, 0
    with open(os.path.join(GCS, archivo), encoding='utf-8-sig', errors='replace') as f:
        for row in csv.DictReader(f, delimiter=';'):
            try:
                if int(row['COD_DDE']) != DEP or int(row['COD_MME']) != MUN:
                    continue
            except (TypeError, ValueError):
                continue
            par = mapa.get(clave_puesto(row['COD_ZZ'], row['COD_PP']))
            votos = int(row['NUM_VOT'] or 0)
            if not par:
                sin_unidad += votos
                continue
            can = str(row['COD_CAN'] or '').strip()
            suma(acc, par[0], (row['DES_CAN'] or '').strip(), (row['DES_PAR'] or '').strip(),
                 votos, ESPECIAL.get(can))
    unidades = {c: mapa_nombres[c] for c in acc}
    total = volcar(acc, unidades, ruta, archivo, señal)
    return total, sin_unidad


def de_2026(mapa, filtro, ruta, señal):
    acc, sin_unidad = {}, 0
    with open(MMV, encoding='utf-8-sig', errors='replace') as f:
        for row in csv.DictReader(f, delimiter=';'):
            if (row.get('MUN') or '').strip() != f'{MUN:03d}' or not filtro(row):
                continue
            par = mapa.get(clave_puesto(row['ZONA'], row['PUESTO']))
            votos = int(row['VOTOS'] or 0)
            if not par:
                sin_unidad += votos
                continue
            can = str(row['CAN'] or '').strip().lstrip('0') or '0'
            especial = ESPECIAL.get(can.rjust(3, '0'))
            # CAN 000 es el voto por la LISTA (el logo): se nombra con el
            # partido, como en las otras catorce ciudades.
            nombre = (row['CANNOMBRE'] or '').strip() if can != '0' else (row['PARNOMBRE'] or '').strip()
            suma(acc, par[0], nombre, (row['PARNOMBRE'] or '').strip(), votos, especial)
    unidades = {c: mapa_nombres[c] for c in acc}
    total = volcar(acc, unidades, ruta, os.path.basename(MMV), señal)
    return total, sin_unidad


def censo(mapa, unidad):
    acc = {}
    with open(CENSO, encoding='utf-8-sig', errors='replace') as f:
        for row in csv.DictReader(f, delimiter=';'):
            try:
                if int(row['dd']) != DEP or int(row['mm']) != MUN:
                    continue
            except (TypeError, ValueError):
                continue
            par = mapa.get(clave_puesto(row['zz'], row['pp']))
            if not par:
                continue
            d = acc.setdefault(par[0], {'comCod': par[0], 'nombre': par[1], 'tipo': unidad,
                                        'censo': 0, 'mujeres': 0, 'hombres': 0, 'n_puestos': 0})
            d['censo'] += int(row['total'] or 0)
            d['mujeres'] += int(row['mujeres'] or 0)
            d['hombres'] += int(row['hombres'] or 0)
            d['n_puestos'] += 1
    archivo = os.path.join(SALIDA, 'censo-comuna.json')
    total = sum(d['censo'] for d in acc.values())
    with open(archivo, 'w', encoding='utf-8') as f:
        json.dump({'por_comuna': dict(sorted(acc.items())), 'ciudad_total': total},
                  f, ensure_ascii=False, separators=(',', ':'))
    print(f'  {"censo-comuna":<32} {len(acc):>2} unidades · {total:>9,} electores')
    return total


def censo_viejo(mapa, unidad, año):
    """El censo de 2018 y 2022 por unidad. Solo trae el total: el desglose por
    sexo vive en el xlsx del Divipole y no en este agregado, y Oportunidad no
    lo usa para esos dos años (sí para el actual)."""
    with open(CENSO_VIEJO[año], encoding='utf-8') as f:
        por_puesto = json.load(f)['porPuesto']
    acc, fuera = {}, 0
    for llave, censo in por_puesto.items():
        partes = llave.split('-')
        if len(partes) != 4 or int(partes[0]) != DEP or int(partes[1]) != MUN:
            continue
        par = mapa.get(clave_puesto(partes[2], partes[3]))
        if not par:
            fuera += censo
            continue
        d = acc.setdefault(par[0], {'comCod': par[0], 'nombre': par[1], 'tipo': unidad,
                                    'censo': 0, 'n_puestos': 0})
        d['censo'] += censo
        d['n_puestos'] += 1
    archivo = os.path.join(SALIDA, f'censo-comuna-{año}.json')
    total = sum(d['censo'] for d in acc.values())
    with open(archivo, 'w', encoding='utf-8') as f:
        json.dump({'city': 'cartagena', 'depCod': f'{DEP:02d}', 'munCod': f'{MUN:03d}',
                   'year': int(año), 'ciudad_total': total, 'n_comunas': len(acc),
                   'por_comuna': dict(sorted(acc.items())),
                   'fuente': os.path.basename(CENSO_VIEJO[año])},
                  f, ensure_ascii=False, separators=(',', ':'))
    print(f'  {"censo-comuna-" + año:<32} {len(acc):>2} unidades · {total:>9,} electores'
          f' · {fuera:,} sin unidad')
    return total


ap = argparse.ArgumentParser()
ap.add_argument('--unidad', choices=['ucg', 'localidad'], default='ucg')
args = ap.parse_args()

mapa, nivel = mapa_unidades(args.unidad)
mapa_nombres = {cod: nombre for cod, nombre in mapa.values()}
print(f'Cartagena por {nivel} · {len(set(c for c, _ in mapa.values()))} unidades '
      f'· {len(mapa)} puestos mapeados')

fuera = {}
for ruta, archivo in HISTORICOS:
    señal = ruta.split('/')[-1]
    total, sin_u = historico(mapa, archivo, ruta, señal)
    fuera[señal] = (total, sin_u)

for cor, ruta, señal in [('01', '2026/senado', '2026/senado'), ('02', '2026/camara', '2026/camara')]:
    total, sin_u = de_2026(mapa, lambda r, c=cor: (r.get('CORCODIGO') or '').strip() == c, ruta, señal)
    fuera[señal] = (total, sin_u)
for par, ruta in CONSULTAS_2026.items():
    señal = ruta
    total, sin_u = de_2026(mapa, lambda r, p=par: (r.get('CORCODIGO') or '').strip() == '06'
                           and (r.get('PAR') or '').strip() == p, ruta, señal)
    fuera[señal] = (total, sin_u)

censo(mapa, nivel)
for año in ('2022', '2018'):
    censo_viejo(mapa, nivel, año)

# Lo que queda fuera son los puestos sin unidad (censo consolidado, cárceles y
# los que ya no existen en el georef de 2026). Se declara, no se esconde.
print('\nVotos sin unidad (puestos que el mapa no cubre):')
for señal, (total, sin_u) in fuera.items():
    pct = sin_u / (total + sin_u) * 100 if total + sin_u else 0
    marca = ' ⚠️' if pct > 2 else ''
    print(f'  {señal:<32} {sin_u:>7,} de {total + sin_u:>9,} ({pct:.2f} %){marca}')
