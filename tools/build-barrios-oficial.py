#!/usr/bin/env python3
"""
build-barrios-oficial.py

Descarga el GeoJSON OFICIAL de barrios y veredas de Medellín desde el
servidor de mapas de la Alcaldía (DAP/POT-48), simplifica la geometría
para reducir tamaño y normaliza nombres para hacer match con los datos
del voto histórico (que usan BARRIO de PUESTOS_GEOREF).

URL fuente: https://www.medellin.gov.co/servidormapas/rest/services/
            ordenamiento_ter/VM_POT48_Base/MapServer/4/query

Uso:
    python3 tools/build-barrios-oficial.py

Salida:
    /Users/ricardoruiz/ricardoruiz.co/Bases de datos/MEDELLIN_BARRIOS_OFICIAL.json
"""

import json
import sys
import csv
import unicodedata
from pathlib import Path
from urllib.request import urlopen, Request

import numpy as np
from shapely.geometry import shape, mapping
from shapely.validation import make_valid

URL = ('https://www.medellin.gov.co/servidormapas/rest/services/'
       'ordenamiento_ter/VM_POT48_Base/MapServer/4/query'
       '?where=1%3D1&outFields=*&returnGeometry=true&outSR=4326&f=geojson')

ROOT = Path('/Users/ricardoruiz/ricardoruiz.co/Bases de datos')
PUESTOS_CSV = ROOT / 'PUESTOS_GEOREF.csv'
OUT = ROOT / 'MEDELLIN_BARRIOS_OFICIAL.json'

# Tolerancia para simplificación (grados). 1 grado de lat ≈ 111 km en el ecuador.
# 0.00003 ≈ 3.3 m — invisible al ojo en zoom de ciudad, gran reducción de tamaño.
SIMPLIFY_TOLERANCE = 0.00003


import re

def normalize_name(s):
    """Normalización básica: upper, sin acentos, espacios colapsados."""
    if not s:
        return ''
    s = str(s).upper()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return ' '.join(s.split())


def normalize_name_aggressive(s):
    """Normalización agresiva para hacer match entre nombres del voto
    histórico (PUESTOS_GEOREF) y nombres oficiales (DAP).

    Reglas observadas:
    - voto usa `BARRIO #N`, oficial usa `BARRIO NO.N` (y viceversa) → ambos
      colapsan a `BARRIO N`
    - voto usa `POBLADO`, oficial `EL POBLADO` → quitar artículos iniciales
    - voto usa `CAICEDO`, oficial `BARRIO CAICEDO` → quitar prefijo "BARRIO"
    - voto usa `CORREGIMIENTO X`, oficial usa "X SECTOR CENTRAL" o varios
      → no son intercambiables 1:1 (los corregimientos se subdividen)
    - puntuación: `-`, `.`, `#` → espacio
    """
    if not s:
        return ''
    n = normalize_name(s)
    # Reemplazar #N por N
    n = re.sub(r'#\s*(\d+)', r'\1', n)
    # Reemplazar NO.N (o NO N o N°N) por N
    n = re.sub(r'\bNO\.?\s*(\d+)', r'\1', n)
    n = re.sub(r'N[°º]\s*(\d+)', r'\1', n)
    # Puntuación que estorba
    n = re.sub(r'[-.]', ' ', n)
    # Espacios colapsados
    n = ' '.join(n.split())
    # Quitar prefijos
    for p in ('CORREGIMIENTO ', 'BARRIO ', 'AREA DE EXPANSION ', 'CABECERA URBANA '):
        if n.startswith(p):
            n = n[len(p):]
    # Quitar artículos iniciales (con cuidado: solo si la palabra siguiente
    # es alfa, no si es solo el artículo)
    for art in ('EL ', 'LA ', 'LOS ', 'LAS '):
        if n.startswith(art) and len(n) > len(art) + 2:
            n = n[len(art):]
    return n.strip()


def fetch_official():
    print('[barrios-oficial] descargando GeoJSON oficial…')
    req = Request(URL, headers={'User-Agent': 'Mozilla/5.0 (proyecto-dc)'})
    with urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    print(f'  · {len(data["features"])} features descargados')
    return data


def load_puestos_barrios():
    """Lee PUESTOS_GEOREF y devuelve diccionario {nombre_norm: nombre_agg}."""
    barrios = {}
    with open(PUESTOS_CSV, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter=';'):
            if row.get('DEPARTAMENTO') != 'ANTIOQUIA':
                continue
            if row.get('MUNICIPIO') != 'MEDELLIN':
                continue
            b = (row.get('BARRIO') or '').strip()
            if b:
                barrios[normalize_name(b)] = normalize_name_aggressive(b)
    return barrios


def simplify_geometry(geom):
    """Aplica simplificación + valida y limpia."""
    try:
        if not geom.is_valid:
            geom = make_valid(geom)
        return geom.simplify(SIMPLIFY_TOLERANCE, preserve_topology=True)
    except Exception:
        return geom


def main():
    raw = fetch_official()
    barrios_voto = load_puestos_barrios()
    print(f'  · {len(barrios_voto)} barrios distintos en PUESTOS_GEOREF para match')

    out_features = []
    nombres_oficiales_basic = set()
    nombres_oficiales_agg = set()
    sizes_before = 0
    sizes_after = 0

    for feat in raw['features']:
        props = feat.get('properties', {})
        nombre = (props.get('nombre') or '').strip()
        codigo = (props.get('codigo') or '').strip()
        comuna = (props.get('nombre_comuna_corregimiento') or '').strip()
        subtipo = props.get('subtipo_barriovereda', 0)

        nombre_norm = normalize_name(nombre)
        nombre_agg = normalize_name_aggressive(nombre)
        if nombre:
            nombres_oficiales_basic.add(nombre_norm)
            nombres_oficiales_agg.add(nombre_agg)

        geom = shape(feat['geometry'])
        sizes_before += len(json.dumps(mapping(geom)))
        geom_simple = simplify_geometry(geom)
        if geom_simple.is_empty:
            continue
        sizes_after += len(json.dumps(mapping(geom_simple)))

        out_features.append({
            'type': 'Feature',
            'properties': {
                'CODIGO':  codigo,
                'NOMBRE':  nombre,
                'NOMBRE_NORM': nombre_norm,
                'NOMBRE_AGG':  nombre_agg,
                'COMUNA':  comuna,
                'SUBTIPO': int(subtipo) if subtipo is not None else None,
            },
            'geometry': mapping(geom_simple),
        })

    # Reporte de match
    voto_basic_keys = set(barrios_voto.keys())
    voto_agg_keys = set(barrios_voto.values())
    matched = voto_basic_keys & nombres_oficiales_basic
    matched_agg = voto_agg_keys & nombres_oficiales_agg
    only_voto = {k for k in voto_basic_keys
                 if k not in nombres_oficiales_basic
                 and barrios_voto[k] not in nombres_oficiales_agg}
    print(f'\n  · barrios en voto histórico:                    {len(barrios_voto)}')
    print(f'  · barrios oficiales (total):                    {len(nombres_oficiales_basic)}')
    print(f'  · MATCH directo (NOMBRE_NORM):                  {len(matched)}')
    print(f'  · MATCH agresivo (NOMBRE_AGG):                  {len(matched_agg)}')
    print(f'  · solo en voto (sin match en ningún modo):      {len(only_voto)}')
    if only_voto:
        print('\n  Barrios del voto sin polígono oficial:')
        for b in sorted(only_voto)[:30]:
            print(f'    - {b}')
        if len(only_voto) > 30:
            print(f'    ... ({len(only_voto) - 30} más)')

    fc = {
        'type': 'FeatureCollection',
        'name': 'MEDELLIN_BARRIOS_OFICIAL',
        'metadata': {
            'fuente': 'Alcaldía de Medellín · DAP · POT-48 Base · MapServer/4',
            'url': URL,
            'n_features': len(out_features),
            'simplify_tolerance_deg': SIMPLIFY_TOLERANCE,
            'match_voto_historico_directo': len(matched),
            'match_voto_historico_agresivo': len(matched_agg),
            'sin_poligono_oficial': sorted(list(only_voto)),
        },
        'features': out_features,
    }

    OUT.write_text(json.dumps(fc, ensure_ascii=False))
    size_kb = OUT.stat().st_size / 1024
    reduction = (1 - sizes_after / sizes_before) * 100 if sizes_before else 0
    print(f'\n  ✓ {OUT.name} escrito: {size_kb:,.0f} KB · {len(out_features)} features')
    print(f'  · simplificación reduce geometría {reduction:.1f}%')


if __name__ == '__main__':
    main()
