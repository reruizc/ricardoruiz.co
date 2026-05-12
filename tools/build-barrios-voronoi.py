#!/usr/bin/env python3
"""
build-barrios-voronoi.py

Genera un GeoJSON aproximado de barrios de Medellín a partir de los
puestos de votación georreferenciados (PUESTOS_GEOREF.csv) usando
Voronoi + clip contra el contorno de Medellín + disolución por barrio.

NO es la cartografía oficial de barrios. Es una aproximación geométrica
donde cada celda representa el área "más cercana" al puesto de votación.
Los límites NO coinciden con los límites administrativos reales.

Uso:
    python3 tools/build-barrios-voronoi.py

Salida:
    /Users/ricardoruiz/ricardoruiz.co/Bases de datos/MEDELLIN_BARRIOS_VORONOI.json

Lógica:
1. Cargar PUESTOS_GEOREF.csv → filtrar Medellín → 239 puestos con lat/lon
2. Filtrar puestos sin coords (zona 99 = corregimiento exterior)
3. Calcular Voronoi sobre los puntos (lon, lat)
4. Convertir cada celda a polígono Shapely
5. Clipear contra el contorno = unión de los 21 polígonos de MEDELLINX.json
6. Unir celdas del mismo barrio → polígono por barrio
7. Escribir GeoJSON con properties: nombre, comuna, n_puestos
"""

import csv
import json
import sys
from pathlib import Path
from collections import defaultdict

import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import Polygon, MultiPolygon, shape, mapping
from shapely.ops import unary_union

ROOT = Path('/Users/ricardoruiz/ricardoruiz.co/Bases de datos')
PUESTOS_CSV = ROOT / 'PUESTOS_GEOREF.csv'
MEDELLIN_GEO = ROOT.parent / '.claude/worktrees/clever-mclaren-9f6cfb/temp_medellinx.json'
S3_GEO_URL = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/mapas-2026/Ciudades-COM-LOC/MEDELLINX.json'
OUT = ROOT / 'MEDELLIN_BARRIOS_VORONOI.json'


def normalize_barrio(name):
    return ' '.join(str(name or '').strip().upper().split())


def load_puestos():
    """Devuelve lista de dicts con lat, lon, barrio normalizado, comuna."""
    puestos = []
    with open(PUESTOS_CSV, encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
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
                # Coordenadas fuera del rango válido para Medellín
                continue
            barrio = row.get('BARRIO', '').strip()
            if not barrio:
                continue
            cod_com = row.get('CÓDIGO COMUNA', '').strip().zfill(2)
            puestos.append({
                'lat': lat,
                'lon': lon,
                'barrio': barrio,
                'barrio_key': normalize_barrio(barrio),
                'comuna': cod_com or '99',
            })
    return puestos


def load_medellin_contour():
    """Carga MEDELLINX.json desde S3 y devuelve un Polygon/MultiPolygon
    unión de las 21 comunas/corregimientos."""
    import urllib.request
    req = urllib.request.Request(S3_GEO_URL, headers={'User-Agent': 'curl/8.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    geoms = []
    for f in data.get('features', []):
        try:
            g = shape(f['geometry'])
            geoms.append(g)
        except Exception:
            continue
    contour = unary_union(geoms)
    print(f'  · contorno Medellín cargado: {len(geoms)} polígonos → bounds {contour.bounds}')
    return contour


def voronoi_finite_polygons(points, bbox):
    """Calcula Voronoi y devuelve celdas finitas recortadas al bbox.

    Para puntos en el borde el Voronoi tiene celdas infinitas. Truco:
    agregar 4 puntos "fantasma" muy lejos en cada esquina del bbox
    para forzar que todas las celdas reales sean finitas.
    """
    bx0, by0, bx1, by1 = bbox
    dx = bx1 - bx0
    dy = by1 - by0
    pad = max(dx, dy) * 5
    fantasmas = np.array([
        [bx0 - pad, by0 - pad],
        [bx1 + pad, by0 - pad],
        [bx1 + pad, by1 + pad],
        [bx0 - pad, by1 + pad],
    ])
    aug = np.vstack([points, fantasmas])
    vor = Voronoi(aug)
    polys = []
    for i in range(len(points)):  # solo los puntos reales, no las fantasmas
        region_idx = vor.point_region[i]
        region = vor.regions[region_idx]
        if not region or -1 in region:
            polys.append(None)
            continue
        coords = [vor.vertices[v] for v in region]
        polys.append(Polygon(coords))
    return polys


def main():
    print('[barrios-voronoi] iniciando…')
    puestos = load_puestos()
    print(f'  · {len(puestos)} puestos con coordenadas válidas')

    contour = load_medellin_contour()
    bx0, by0, bx1, by1 = contour.bounds

    # NOTA: Voronoi trabaja en coordenadas geográficas (lon, lat). Para
    # aproximaciones locales pequeñas (Medellín ~10km × 15km) la
    # distorsión angular es aceptable. Suficiente para visualización.
    points = np.array([[p['lon'], p['lat']] for p in puestos])

    print(f'  · calculando Voronoi sobre {len(points)} puntos…')
    cells = voronoi_finite_polygons(points, (bx0, by0, bx1, by1))

    # Agrupar celdas por barrio
    barrio_to_cells = defaultdict(list)
    barrio_to_meta = {}
    for i, p in enumerate(puestos):
        cell = cells[i]
        if cell is None or not cell.is_valid:
            continue
        clipped = cell.intersection(contour)
        if clipped.is_empty:
            continue
        barrio_to_cells[p['barrio_key']].append(clipped)
        if p['barrio_key'] not in barrio_to_meta:
            barrio_to_meta[p['barrio_key']] = {
                'nombre': p['barrio'],
                'comuna': p['comuna'],
                'n_puestos': 0,
            }
        barrio_to_meta[p['barrio_key']]['n_puestos'] += 1

    print(f'  · {len(barrio_to_cells)} barrios distintos')

    # Unir celdas del mismo barrio
    features = []
    for bk, geoms in barrio_to_cells.items():
        try:
            merged = unary_union(geoms)
        except Exception as e:
            print(f'  ! error uniendo barrio {bk}: {e}')
            continue
        if merged.is_empty:
            continue
        # Si quedó como GeometryCollection, filtrar a (Multi)Polygon
        if merged.geom_type == 'GeometryCollection':
            polys = [g for g in merged.geoms if g.geom_type in ('Polygon', 'MultiPolygon')]
            if not polys:
                continue
            merged = unary_union(polys)

        meta = barrio_to_meta[bk]
        feat = {
            'type': 'Feature',
            'properties': {
                'NOMBRE': meta['nombre'],
                'BARRIO_KEY': bk,
                'COMUNA': meta['comuna'],
                'N_PUESTOS': meta['n_puestos'],
            },
            'geometry': mapping(merged),
        }
        features.append(feat)

    fc = {
        'type': 'FeatureCollection',
        'name': 'MEDELLIN_BARRIOS_VORONOI',
        'metadata': {
            'fuente': 'Aproximación Voronoi sobre PUESTOS_GEOREF.csv',
            'disclaimer': 'NO es cartografía oficial. Cada polígono es el área más cercana a uno o más puestos de votación del barrio. Los límites no coinciden con los límites administrativos reales.',
            'n_features': len(features),
            'n_puestos_origen': len(puestos),
        },
        'features': features,
    }

    OUT.write_text(json.dumps(fc, ensure_ascii=False))
    size_kb = OUT.stat().st_size / 1024
    print(f'  ✓ {OUT.name} escrito: {size_kb:,.0f} KB · {len(features)} barrios')

    # Sanity: barrios con mayor área aproximada
    feats_sorted = sorted(features, key=lambda f: -shape(f['geometry']).area)
    print(f'  · top 5 barrios por área aproximada:')
    for f in feats_sorted[:5]:
        p = f['properties']
        area = shape(f['geometry']).area
        print(f"     {p['NOMBRE']:35s} comuna {p['COMUNA']}  {p['N_PUESTOS']} puestos  area={area:.5f}")


if __name__ == '__main__':
    main()
