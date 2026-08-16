#!/usr/bin/env python3
"""
Ficha electoral de NATALIA SOPHIA PARRA ROJAS — JAL Barrios Unidos, Bogotá 2023.

Arma un JSON autocontenido (electoral + geo) para `natalia-parra.html`, cruzando:

  · congreso-2026/output/jal-2023/comuna/16-001-12.json   detalle de la localidad
      (barrios · puestos con lat/lon · MESAS, con votos por candidato)
  · Bases de datos/output_pacto_1v_2026/geo/BOG-BARRIOS-CATASTRALES.json
  · Bases de datos/output_pacto_1v_2026/geo/BOG-LOCALIDADX.json

⚠️ En el JSON de comuna, `cands` es [nombre, indice_de_partido] — NO votos. Los
votos viven en los arrays `v` = [[idx_candidato, votos], ...] de barrio/puesto/mesa.
El total se SUMA de ahí (verificado: 709 por las tres vías).

⚠️ `feat` de cada barrio es el ÍNDICE del feature en el geojson catastral, no un
código. Se resuelve por posición.

Salida (gitignored) en `Bases de datos/natalia-parra/`:
    nsp-electoral.json   (~120 KB)  ficha + puestos + mesas + barrios
    nsp-geo.json         (~40 KB)   barrios de la localidad + polígono localidad

Correr:  python3 tools/natalia-parra/build_electoral.py
"""
import json
import os
import sys
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASES = os.path.join(RAIZ, 'Bases de datos')
GEO = os.path.join(BASES, 'output_pacto_1v_2026', 'geo')
OUT = os.path.join(BASES, 'natalia-parra')
RAW = os.path.join(OUT, 'raw')

S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output'
COMUNA_URL = f'{S3}/jal-2023/comuna/16-001-12.json'

CANDIDATA = 'NATALIA SOPHIA PARRA ROJAS'
LOC_COD = '12'          # Barrios Unidos
LOC_NOMBRE = 'BARRIOS UNIDOS'


def baja(url, destino):
    """Descarga con caché en disco (el detalle de comuna no cambia)."""
    if os.path.exists(destino):
        return json.load(open(destino, encoding='utf-8'))
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=120) as r:
        datos = json.loads(r.read().decode('utf-8'))
    json.dump(datos, open(destino, 'w', encoding='utf-8'), ensure_ascii=False)
    return datos


def main():
    com = baja(COMUNA_URL, os.path.join(RAW, 'comuna-16-001-12.json'))

    cands = com['cands']
    partidos = com['partidos']
    try:
        idx = next(i for i, c in enumerate(cands) if c[0] == CANDIDATA)
    except StopIteration:
        sys.exit(f'ERROR: {CANDIDATA} no está en el detalle de la comuna')

    # Totales por candidato: se suman de los puestos (única fuente de votos).
    tot_cand = {}
    for p in com['puestos']:
        for i, v in p['v']:
            tot_cand[i] = tot_cand.get(i, 0) + v
    mios = tot_cand.get(idx, 0)

    orden = sorted(tot_cand, key=lambda i: -tot_cand[i])
    ranking = orden.index(idx) + 1

    # Compañeros de lista (mismo partido) — quién más votos sacó de la lista.
    par_idx = cands[idx][1]
    lista = [{
        'nombre': cands[i][0],
        'votos': tot_cand.get(i, 0),
        'yo': i == idx,
    } for i in orden if cands[i][1] == par_idx]

    # ── PUESTOS + MESAS ────────────────────────────────────────────────
    puestos = []
    for p in com['puestos']:
        pv = dict(p['v'])
        mias = pv.get(idx, 0)
        val = p.get('validos', 0) or 0
        # ganador del puesto (para contexto competitivo)
        gan_i = max(pv, key=lambda i: pv[i]) if pv else None
        mesas = []
        for m in p.get('mesas', []):
            num, mval, mv = m[0], m[1], dict(m[2])
            mesas.append({
                'mesa': num,
                'v': mv.get(idx, 0),
                'validos': mval,
                'pct': round(100 * mv.get(idx, 0) / mval, 2) if mval else 0,
            })
        mesas.sort(key=lambda x: (-x['v'], x['mesa']))
        puestos.append({
            'code': p['code'],
            'nombre': p['nombre'],
            'barrio': p.get('barrio') or '',
            'lat': p.get('lat'),
            'lon': p.get('lon'),
            'v': mias,
            'validos': val,
            'blanco': p.get('blanco', 0),
            'nulos': p.get('nulos', 0),
            'pct': round(100 * mias / val, 2) if val else 0,
            'ganador': cands[gan_i][0] if gan_i is not None else '',
            'ganador_v': pv.get(gan_i, 0) if gan_i is not None else 0,
            'ganador_partido': partidos[cands[gan_i][1]][0] if gan_i is not None else '',
            'mesas': mesas,
        })
    puestos.sort(key=lambda x: -x['v'])

    # ── BARRIOS ────────────────────────────────────────────────────────
    barrios = []
    for b in com['barrios']:
        bv = dict(b['v'])
        mias = bv.get(idx, 0)
        val = b.get('validos', 0) or 0
        barrios.append({
            'name': b['name'],
            'feat': b['feat'],
            'v': mias,
            'validos': val,
            'pct': round(100 * mias / val, 2) if val else 0,
            'puestos': [p['code'] for p in puestos if p['barrio'] == b['name']],
        })
    barrios.sort(key=lambda x: -x['v'])

    # Barrios sin puesto propio: se listan aparte, NUNCA suman a totales
    # (mismo criterio que los tableros territoriales 2023).
    fills = [{'name': f['name'], 'feat': f['feat'], 'from': f.get('from', '')}
             for f in com.get('fills', [])]

    electoral = {
        'v': '2026-08-16',
        'meta': {
            'nombre': CANDIDATA,
            'corp': 'JAL · BARRIOS UNIDOS · BOGOTÁ D.C.',
            'localidad': LOC_NOMBRE,
            'loc_codigo': LOC_COD,
            'anio': 2023,
            'partido': partidos[par_idx][0],
            'partido_votos': partidos[par_idx][1],
            'votos': mios,
            'ranking': ranking,
            'n_candidatos': len(cands),
            'n_puestos': len(puestos),
            'n_puestos_con_voto': sum(1 for p in puestos if p['v'] > 0),
            'n_mesas': sum(len(p['mesas']) for p in puestos),
            'n_mesas_con_voto': sum(1 for p in puestos for m in p['mesas'] if m['v'] > 0),
            'validos_localidad': com['totals']['validos'],
            'blanco_localidad': com['totals']['blanco'],
            'nulos_localidad': com['totals']['nulos'],
            'pct_localidad': round(100 * mios / com['totals']['validos'], 3),
            'mejor_puesto': puestos[0]['nombre'] if puestos else '',
            'mejor_puesto_v': puestos[0]['v'] if puestos else 0,
        },
        'partidos': [{'nombre': n, 'votos': v} for n, v in partidos],
        'lista': lista,
        'top_candidatos': [{'nombre': cands[i][0],
                            'partido': partidos[cands[i][1]][0],
                            'votos': tot_cand[i]} for i in orden[:15]],
        'puestos': puestos,
        'barrios': barrios,
        'fills': fills,
    }

    # ── GEO: barrios de la localidad + polígono de la localidad ────────
    cat = json.load(open(os.path.join(GEO, 'BOG-BARRIOS-CATASTRALES.json'), encoding='utf-8'))
    locs = json.load(open(os.path.join(GEO, 'BOG-LOCALIDADX.json'), encoding='utf-8'))

    quiero = {b['feat'] for b in barrios} | {f['feat'] for f in fills}
    feats = []
    for i in sorted(quiero):
        f = cat['features'][i]
        props = dict(f['properties'])
        props['feat'] = i
        feats.append({'type': 'Feature', 'properties': props, 'geometry': f['geometry']})

    # Todos los barrios catastrales de la localidad, aunque no tengan dato:
    # el mapa debe dibujar la localidad completa, no un queso suizo.
    for i, f in enumerate(cat['features']):
        if i in quiero:
            continue
        if str(f['properties'].get('loc_codigo', '')).lstrip('0') == LOC_COD.lstrip('0'):
            props = dict(f['properties'])
            props['feat'] = i
            feats.append({'type': 'Feature', 'properties': props, 'geometry': f['geometry']})

    loc_feat = next((f for f in locs['features']
                     if str(f['properties'].get('LocCodigo', '')).lstrip('0') == LOC_COD.lstrip('0')), None)

    geo = {
        'v': electoral['v'],
        'barrios': {'type': 'FeatureCollection', 'features': feats},
        'localidad': {'type': 'FeatureCollection', 'features': [loc_feat] if loc_feat else []},
    }

    os.makedirs(OUT, exist_ok=True)
    for nombre, datos in (('nsp-electoral.json', electoral), ('nsp-geo.json', geo)):
        ruta = os.path.join(OUT, nombre)
        json.dump(datos, open(ruta, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        print(f'  {nombre}  {os.path.getsize(ruta)/1024:.0f} KB')

    m = electoral['meta']
    print(f"\n{m['nombre']} · {m['votos']} votos · puesto {m['ranking']} de {m['n_candidatos']}")
    print(f"  {m['pct_localidad']}% de los válidos de la localidad ({m['validos_localidad']:,})")
    print(f"  votos en {m['n_puestos_con_voto']}/{m['n_puestos']} puestos y "
          f"{m['n_mesas_con_voto']}/{m['n_mesas']} mesas")
    print(f"  mejor puesto: {m['mejor_puesto']} ({m['mejor_puesto_v']})")
    print(f"  geo: {len(feats)} barrios de {LOC_NOMBRE}")


if __name__ == '__main__':
    main()
