#!/usr/bin/env python3
"""
Construye dos GeoJSONs para CITREP a partir de:
  - /tmp/citrep-work/municipios.json   (168 muns con com_cod/com_nom/dep_cod/cod)
  - /tmp/citrep-work/deps/{dep_cod}.json (Departamentos-mps/ de los 19 deptos con muns CITREP)

Salida:
  - citrep-municipios.geojson       (168 polígonos, props: dep_cod, mun_cod, com_cod, com_nom, nombre)
  - citrep-circunscripciones.geojson (16 polígonos, unión por com_cod)
"""
import json
from pathlib import Path
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

WORK = Path('/tmp/citrep-work')
muns_meta = json.loads((WORK / 'municipios.json').read_text())

# Index por (dep_cod, mun_elec)
meta_idx = {(x['dep_cod'], x['cod']): x for x in muns_meta}
print(f'CITREP municipios meta: {len(meta_idx)}')

# Cargar todos los Departamentos-mps y filtrar
all_features = []
missing = []
seen_keys = set()

for dep_cod in sorted(set(x['dep_cod'] for x in muns_meta)):
    geo = json.loads((WORK / 'deps' / f'{dep_cod}.json').read_text())
    for feat in geo['features']:
        p = feat['properties']
        dep_e = p.get('dep_electoral') or p.get('dpto_ccdgo')
        mun_e = p.get('mun_elec') or p.get('mun_electoral') or p.get('mpio_ccdgo')
        key = (str(dep_e), str(mun_e))
        if key in meta_idx and key not in seen_keys:
            seen_keys.add(key)
            m = meta_idx[key]
            new_props = {
                'dep_cod': m['dep_cod'],
                'dep_nom': m['dep_nom'],
                'mun_cod': m['cod'],
                'nombre': m['nombre'],
                'com_cod': m['com_cod'],
                'com_nom': m['com_nom'],
                # campos DANE útiles para fallback
                'dane_dep': p.get('dpto_ccdgo'),
                'dane_mpio': p.get('mpio_cdpmp'),
            }
            all_features.append({
                'type': 'Feature',
                'properties': new_props,
                'geometry': feat['geometry'],
            })

# Detectar muns que no encontramos
for k, m in meta_idx.items():
    if k not in seen_keys:
        missing.append(f"{m['dep_nom']} · {m['nombre']} ({k[0]}/{k[1]})")

print(f'Matched: {len(all_features)} / {len(meta_idx)}')
if missing:
    print(f'Missing ({len(missing)}):')
    for x in missing:
        print(f'  - {x}')

# Escribir GeoJSON de municipios
out_muns = {'type': 'FeatureCollection', 'features': all_features}
(WORK / 'citrep-municipios.geojson').write_text(json.dumps(out_muns, ensure_ascii=False))
print(f'\nWrote citrep-municipios.geojson: {len(all_features)} features')

# Construir GeoJSON agregado por circunscripción (16 features)
by_circ = {}
for feat in all_features:
    cc = feat['properties']['com_cod']
    by_circ.setdefault(cc, []).append(feat)

circ_features = []
for com_cod in sorted(by_circ.keys()):
    feats = by_circ[com_cod]
    geoms = [shape(f['geometry']) for f in feats]
    merged = unary_union(geoms)
    # buffer(0) para limpiar self-intersections menores
    if not merged.is_valid:
        merged = merged.buffer(0)
    com_nom = feats[0]['properties']['com_nom']
    # Lista de deps tocados por la circ
    deps_touched = sorted(set(f['properties']['dep_cod'] for f in feats))
    mun_count = len(feats)
    circ_features.append({
        'type': 'Feature',
        'properties': {
            'com_cod': com_cod,
            'com_nom': com_nom,
            'deps': deps_touched,
            'mun_count': mun_count,
        },
        'geometry': mapping(merged),
    })

out_circ = {'type': 'FeatureCollection', 'features': circ_features}
(WORK / 'citrep-circunscripciones.geojson').write_text(json.dumps(out_circ, ensure_ascii=False))
print(f'Wrote citrep-circunscripciones.geojson: {len(circ_features)} features')

# Resumen
for f in circ_features:
    p = f['properties']
    print(f"  {p['com_cod']} · {p['com_nom'][:45]:45} · {p['mun_count']:2d} muns · deps {p['deps']}")
