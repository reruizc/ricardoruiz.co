#!/usr/bin/env python3
"""
match-puestos-barrios.py

Hace point-in-polygon de cada puesto de votación (PUESTOS_GEOREF) contra
los polígonos oficiales de barrios y veredas (MEDELLIN_BARRIOS_OFICIAL).
Genera un mapping JSON: (ZZ-PP) → {codigo, nombre, comuna} oficial.

Esto resuelve el problema de naming inconsistente entre PUESTOS_GEOREF
(nombres aproximados: "AURES #1") y el GeoJSON oficial ("AURES NO.1"),
y además asegura que cada puesto se asigne al barrio oficial donde
geográficamente cae (no donde el operador escribió el nombre).

Uso:
    python3 tools/match-puestos-barrios.py

Salida:
    tools/puestos_to_barrios.json   { "01-01": { "codigo": "0101", "nombre": "Popular", "comuna": "Popular" }, ... }
"""

import csv
import json
from pathlib import Path

from shapely.geometry import shape, Point
from shapely.strtree import STRtree

ROOT = Path('/Users/ricardoruiz/ricardoruiz.co/Bases de datos')
REPO = Path('/Users/ricardoruiz/ricardoruiz.co/.claude/worktrees/clever-mclaren-9f6cfb')
PUESTOS_CSV = ROOT / 'PUESTOS_GEOREF.csv'
BARRIOS_GEO = ROOT / 'MEDELLIN_BARRIOS_OFICIAL.json'
OUT = REPO / 'tools' / 'puestos_to_barrios.json'


def main():
    print('[match-puestos] cargando GeoJSON oficial…')
    geo = json.loads(BARRIOS_GEO.read_text())
    features = geo['features']
    polys = []
    metas = []
    for f in features:
        g = shape(f['geometry'])
        polys.append(g)
        p = f['properties']
        metas.append({
            'codigo': p.get('CODIGO'),
            'nombre': p.get('NOMBRE'),
            'comuna': p.get('COMUNA'),
            'subtipo': p.get('SUBTIPO'),
        })
    print(f'  · {len(polys)} polígonos oficiales')

    # STRtree para búsqueda espacial rápida
    tree = STRtree(polys)

    print('[match-puestos] cargando PUESTOS_GEOREF…')
    puestos = []
    with open(PUESTOS_CSV, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter=';'):
            if row.get('DEPARTAMENTO') != 'ANTIOQUIA':
                continue
            if row.get('MUNICIPIO') != 'MEDELLIN':
                continue
            try:
                lat = float(row['LATITUD'])
                lon = float(row['LONGITUD'])
            except (KeyError, ValueError, TypeError):
                continue
            if not (5.9 < lat < 6.5 and -76 < lon < -75):
                continue
            try:
                zz = str(int(row['ZONA'] or 0)).zfill(2)
                pp = str(int(row['PUESTO'] or 0)).zfill(2)
            except (ValueError, TypeError):
                # Algunos puestos tienen códigos no numéricos (ej. "A1"); los
                # ignoramos porque no van a coincidir con el TER tampoco
                continue
            puestos.append({
                'key': f'{zz}-{pp}',
                'zz': zz, 'pp': pp,
                'lat': lat, 'lon': lon,
                'barrio_csv': (row.get('BARRIO') or '').strip(),
            })
    print(f'  · {len(puestos)} puestos con coordenadas válidas')

    # Point-in-polygon
    mapping = {}
    sin_match = []
    for p in puestos:
        pt = Point(p['lon'], p['lat'])
        # STRtree devuelve índices de polígonos candidatos (bbox match)
        candidates = tree.query(pt)
        hit_meta = None
        for idx in candidates:
            if polys[idx].contains(pt):
                hit_meta = metas[idx]
                break
        if hit_meta is None:
            # Fallback: el polígono más cercano (puede pasar por imprecisión
            # de la coordenada o borde exacto)
            nearest_idx = None
            nearest_dist = float('inf')
            for idx, poly in enumerate(polys):
                d = poly.distance(pt)
                if d < nearest_dist:
                    nearest_dist = d
                    nearest_idx = idx
            if nearest_idx is not None and nearest_dist < 0.001:  # ~110m
                hit_meta = metas[nearest_idx]
                hit_meta = {**hit_meta, 'nearest_distance_deg': nearest_dist}
            else:
                sin_match.append(p)
                continue
        # Si ya hay otro puesto en esta misma celda, conservar — clave única por puesto
        mapping[p['key']] = {
            'codigo': hit_meta.get('codigo'),
            'nombre': hit_meta.get('nombre'),
            'comuna': hit_meta.get('comuna'),
            'subtipo': hit_meta.get('subtipo'),
            'lat': p['lat'],
            'lon': p['lon'],
            'barrio_csv': p['barrio_csv'],
        }

    # Sanity: cuántos barrios distintos cubre el mapping
    barrios_cubiertos = set(m['codigo'] for m in mapping.values() if m['codigo'])
    print(f'\n  · {len(mapping)} puestos mapeados a barrio oficial')
    print(f'  · {len(barrios_cubiertos)} barrios oficiales distintos con al menos 1 puesto')
    print(f'  · {len(sin_match)} puestos sin match (fuera de cualquier polígono y >110m del más cercano)')
    if sin_match:
        for p in sin_match[:10]:
            print(f'    - {p["key"]}: {p["barrio_csv"]} ({p["lat"]:.5f}, {p["lon"]:.5f})')

    # Reportar cambios entre nombre CSV y nombre oficial (sanity)
    cambios = 0
    for k, m in mapping.items():
        csv_barrio = m['barrio_csv']
        oficial = m['nombre']
        if csv_barrio.upper().replace('#','').replace(' ','') != (oficial or '').upper().replace('NO.','').replace(' ',''):
            cambios += 1
    print(f'\n  · {cambios} puestos donde nombre CSV ≠ nombre oficial (esperado, el match geométrico corrige)')

    OUT.write_text(json.dumps(mapping, ensure_ascii=False, indent=2))
    print(f'\n  ✓ {OUT.name} escrito: {OUT.stat().st_size/1024:.0f} KB · {len(mapping)} puestos')


if __name__ == '__main__':
    main()
