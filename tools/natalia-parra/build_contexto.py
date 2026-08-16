#!/usr/bin/env python3
"""
Contexto territorial de la ficha de Barrios Unidos (Bogotá): seguridad + mujer.

Fuentes (ya publicadas, no se recalcula nada):
  · congreso-2026/output/ponal/{meta,nacional,ciudades/11001}.json   PONAL 2015-2024
  · bases de datos/output_observatorio_mujer/violencia-{meta,ciudades}.json

En Bogotá la clave `comunas` del hub de policía son LOCALIDADES (1..20);
Barrios Unidos es la 12.

⚠️⚠️ HUECO DE 2023 (medido, no supuesto). En la desagregación por localidad de
Bogotá, 2023 da CERO EXACTO en homicidios, lesiones y delitos sexuales — en las
20 localidades a la vez —, mientras el nacional de ese año es normal (13.430
homicidios). No es una caída: son hechos que ese año llegaron sin barrio
parseable y cayeron a `sin_comuna`. Se emite `null`, nunca 0, y la página lo
declara. Dibujar el 0 diría que Barrios Unidos no tuvo un solo homicidio en
2023 y que en 2024 se disparó — las dos cosas falsas.

⚠️ Los vertederos de registro (BELLA SUIZA en Bogotá) ya vienen EXCLUIDOS del
hub; se copia su declaración a la salida para poder mostrarla.

⚠️ El nombre de barrio de la Policía NO casa con el barrio catastral del mapa
(~64% en Bogotá) → los barrios van como LISTA rankeada, nunca como polígono.

Salida (gitignored) en `Bases de datos/natalia-parra/`:
    nsp-seguridad.json   ·   nsp-mujer.json

Correr:  python3 tools/natalia-parra/build_contexto.py
"""
import json
import os
import urllib.parse
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(RAIZ, 'Bases de datos', 'natalia-parra')
RAW = os.path.join(OUT, 'raw')

BUCKET = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co'
PONAL = f'{BUCKET}/congreso-2026/output/ponal'
MUJER = f'{BUCKET}/{urllib.parse.quote("bases de datos")}/output_observatorio_mujer'

LOC = '12'
LOC_NOMBRE = 'Barrios Unidos'
BOG = '11001'

# Los que le sirven a una JAL: convivencia y patrimonio del vecindario.
DELITOS_FICHA = ['hurto_personas', 'hurto_celulares', 'hurto_residencias',
                 'hurto_comercios', 'hurto_motos', 'hurto_bicicletas',
                 'violencia_intra', 'lesiones', 'amenazas', 'homicidios',
                 'delitos_sexuales', 'extorsiones']

NOMBRE_DELITO = {
    'homicidios': 'Homicidios', 'lesiones': 'Lesiones personales',
    'violencia_intra': 'Violencia intrafamiliar', 'delitos_sexuales': 'Delitos sexuales',
    'amenazas': 'Amenazas', 'extorsiones': 'Extorsión', 'secuestros': 'Secuestro',
    'hurto_personas': 'Hurto a personas', 'hurto_celulares': 'Hurto de celulares',
    'hurto_comercios': 'Hurto a comercios', 'hurto_residencias': 'Hurto a residencias',
    'hurto_motos': 'Hurto de motos', 'hurto_autos': 'Hurto de vehículos',
    'hurto_bicicletas': 'Hurto de bicicletas', 'del_informaticos': 'Delitos informáticos',
}


def baja(url, destino):
    if os.path.exists(destino):
        return json.load(open(destino, encoding='utf-8'))
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=180) as r:
        datos = json.loads(r.read().decode('utf-8'))
    json.dump(datos, open(destino, 'w', encoding='utf-8'), ensure_ascii=False)
    return datos


def seguridad():
    meta = baja(f'{PONAL}/meta.json', os.path.join(RAW, 'ponal-meta.json'))
    nac = baja(f'{PONAL}/nacional.json', os.path.join(RAW, 'ponal-nacional.json'))
    bog = baja(f'{PONAL}/ciudades/{BOG}.json', os.path.join(RAW, f'ponal-{BOG}.json'))

    anios = bog['anios']
    comunas = bog['comunas']

    # Suma de TODAS las localidades por delito y año → detecta el hueco.
    ciudad = {}
    for c in comunas.values():
        for k, s in c['d'].items():
            acc = ciudad.setdefault(k, [0] * len(anios))
            for i, x in enumerate(s['y']):
                acc[i] += x
    # Año con 0 en toda la ciudad = sin asignación de barrio ese año, no un cero real.
    huecos = {k: [anios[i] for i, v in enumerate(serie) if v == 0]
              for k, serie in ciudad.items()}

    mia = comunas.get(LOC, {}).get('d', {})

    # Los delitos que la fuente solo empezó a reportar en 2024 (bicicletas, ganado,
    # piratería…) tienen ceros previos que NO son el hueco de 2023: son "no medido".
    # Se distinguen para que la UI no dibuje una tendencia inexistente.
    solo_2024 = {x['id'] for x in meta.get('delitos', []) if x.get('solo_2024')}

    series = []
    for d in DELITOS_FICHA:
        if d not in mia:
            continue
        cruda = mia[d]['y']
        hoyos = set(huecos.get(d, []))
        serie = [None if anios[i] in hoyos else v for i, v in enumerate(cruda)]
        ciu = [None if anios[i] in hoyos else v for i, v in enumerate(ciudad.get(d, []))]
        # Ranking entre las 20 localidades por total del delito.
        totales = sorted(((c, sum(v['d'][d]['y'])) for c, v in comunas.items() if d in v['d']),
                         key=lambda x: -x[1])
        pos = next((i + 1 for i, (c, _) in enumerate(totales) if c == LOC), None)
        series.append({
            'id': d,
            'nombre': NOMBRE_DELITO.get(d, d),
            'total': mia[d]['t'],
            'y': serie,
            'ciudad_y': ciu,
            'ciudad_total': sum(ciudad.get(d, [])),
            'pct_ciudad': round(100 * mia[d]['t'] / sum(ciudad[d]), 2) if sum(ciudad.get(d, [0])) else 0,
            'rank_localidad': pos,
            'n_localidades': len(totales),
            'anios_sin_dato': sorted(hoyos),
            'solo_2024': d in solo_2024,
            'tendencia': not (d in solo_2024),
        })
    series.sort(key=lambda s: -s['total'])

    # Barrios de la localidad (lista, NO mapa: el barrio PONAL no casa con el catastral).
    barrios = [{'n': b['n'], 't': b['t'], 'd': b['d']}
               for b in bog['barrios'] if str(b.get('c', '')) == LOC]
    barrios.sort(key=lambda b: -b['t'])

    # Ranking de localidades por total de hechos (contexto de ciudad).
    tot_loc = sorted(((c, sum(sum(s['y']) for s in v['d'].values()))
                      for c, v in comunas.items()), key=lambda x: -x[1])
    rank_general = next((i + 1 for i, (c, _) in enumerate(tot_loc) if c == LOC), None)

    datos = {
        'v': meta.get('v', ''),
        'fuente': meta.get('fuente', 'Policía Nacional'),
        'anios': anios,
        'localidad': {'codigo': LOC, 'nombre': LOC_NOMBRE,
                      'total': sum(sum(s['y']) for s in mia.values()),
                      'rank': rank_general, 'n_localidades': len(tot_loc)},
        'series': series,
        'barrios': barrios[:40],
        'n_barrios': len(barrios),
        'ranking_localidades': [{'cod': c, 'total': t} for c, t in tot_loc],
        'nacional_por_anio': {k: nac['por_anio'][k] for k in DELITOS_FICHA if k in nac['por_anio']},
        'avisos': {
            'hueco_2023': ('En la desagregación por localidad de Bogotá, 2023 llega en cero '
                           'exacto en varios delitos y en las 20 localidades a la vez, mientras '
                           'el total nacional de ese año es normal. Son hechos sin barrio '
                           'asignado en la fuente: se muestran como sin dato, no como cero.'),
            'huecos': {k: v for k, v in huecos.items()
                       if v and k in DELITOS_FICHA and k not in solo_2024},
            'solo_2024': sorted(solo_2024 & set(DELITOS_FICHA)),
            'vertederos': meta.get('vertederos', {}),
            'barrio_no_es_poligono': ('El nombre de barrio de la Policía no coincide con el '
                                      'barrio catastral del mapa: los barrios van como lista, '
                                      'no como polígono coloreado.'),
        },
    }
    ruta = os.path.join(OUT, 'nsp-seguridad.json')
    json.dump(datos, open(ruta, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'  nsp-seguridad.json  {os.path.getsize(ruta)/1024:.0f} KB · '
          f'{len(series)} delitos · {len(barrios)} barrios · '
          f'huecos {sorted({a for v in datos["avisos"]["huecos"].values() for a in v})}')
    return datos


def mujer():
    meta = baja(f'{MUJER}/violencia-meta.json', os.path.join(RAW, 'mujer-meta.json'))
    ciu = baja(f'{MUJER}/violencia-ciudades.json', os.path.join(RAW, 'mujer-ciudades.json'))

    bog = ciu['ciudades'][BOG]
    mia = bog['comunas'].get(LOC, {})

    # Ciudad entera (suma de localidades) para comparar la brecha.
    tot = {}
    for c in bog['comunas'].values():
        for k, (f, m) in c.items():
            a = tot.setdefault(k, [0, 0])
            a[0] += f
            a[1] += m

    filas = []
    for k, (f, m) in mia.items():
        t = f + m
        cf, cm = tot.get(k, [0, 0])
        ct = cf + cm
        filas.append({
            'id': k,
            'nombre': NOMBRE_DELITO.get(k, k),
            'mujeres': f,
            'hombres': m,
            'total': t,
            'pct_mujeres': round(100 * f / t, 1) if t else None,
            'ciudad_pct_mujeres': round(100 * cf / ct, 1) if ct else None,
            'ciudad_mujeres': cf,
        })
    filas.sort(key=lambda x: -x['mujeres'])

    # Ranking de localidades por víctimas mujeres de violencia intrafamiliar.
    vif = sorted(((c, v.get('violencia_intra', [0, 0])[0]) for c, v in bog['comunas'].items()),
                 key=lambda x: -x[1])
    rank_vif = next((i + 1 for i, (c, _) in enumerate(vif) if c == LOC), None)

    datos = {
        'v': meta.get('v', ''),
        'fuente': meta.get('fuente', 'Policía Nacional · derivada del observatorio de MxD'),
        'localidad': {'codigo': LOC, 'nombre': LOC_NOMBRE},
        'delitos': filas,
        'rank_vif': rank_vif,
        'n_localidades': len(vif),
        'ranking_vif': [{'cod': c, 'mujeres': v} for c, v in vif],
        'avisos': {
            'sin_localidad': bog.get('sin_comuna', 0),
            'victima_no_agresor': ('Todo el bloque describe a la VÍCTIMA, no al agresor. '
                                   'La fuente no registra la relación entre los dos: con estos '
                                   'datos no se puede afirmar qué porcentaje fue la pareja.'),
            'serie': ('Delitos sexuales y amenazas tienen más del 15% de registros sin año: '
                      'se muestran como total del periodo, sin tendencia.'),
            'fuente_avisos': meta.get('avisos', {}),
        },
    }
    ruta = os.path.join(OUT, 'nsp-mujer.json')
    json.dump(datos, open(ruta, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    vi = next((f for f in filas if f['id'] == 'violencia_intra'), None)
    print(f'  nsp-mujer.json      {os.path.getsize(ruta)/1024:.0f} KB · '
          f'{len(filas)} delitos · VIF {vi["pct_mujeres"] if vi else "?"}% mujeres · '
          f'sin localidad en la ciudad: {datos["avisos"]["sin_localidad"]:,}')
    return datos


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    seguridad()
    mujer()
