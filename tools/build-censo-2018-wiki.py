#!/usr/bin/env python3
"""
tools/build-censo-2018-wiki.py

Reconstruye el censo electoral 2018 (pres 1V) por municipio y por comuna
de las 14 capitales, usando:

  1) Tabla de Wikipedia (% participación por depto) → censo_depto_2018
     = votos_totales_depto / (participacion/100). 34 deptos incl. Consulados.
     Validado: 36.78M nacional vs oficial 36.7M (off-by-1%).
  2) Censo 2022 (Divipole sept-2021) ya procesado por mun y comuna →
     usado como SHAPE de proporciones internas. Asume que la geografía
     relativa cambió marginalmente entre 2018 y 2022 (error <2pp por mun).

Output:
  - puestos-censos-agg-2018.json (nacional por mun)
  - output_ciudades/<city>/censo-comuna-2018.json (14 ciudades por comuna)

Es un PROXY, no censo medido. Se documenta en CLAUDE.md y en el footer
del módulo Oportunidad. Reemplazar por Divipole 2018 oficial si llega
de la Registraduría.
"""

import json, os, sys

# Nombre Wikipedia → código electoral (mismos códigos que el índice S3)
DEPTO_CODE = {
    'Amazonas':                  '60',
    'Antioquia':                 '01',
    'Arauca':                    '40',
    'Atlántico':                 '03',
    'Bogotá':                    '16',
    'Bolívar':                   '05',
    'Boyacá':                    '07',
    'Caldas':                    '09',
    'Caquetá':                   '44',
    'Casanare':                  '46',
    'Cauca':                     '11',
    'Cesar':                     '12',
    'Chocó':                     '17',
    'Consulados':                '88',
    'Córdoba':                   '13',
    'Cundinamarca':              '15',
    'Guainía':                   '50',
    'Guaviare':                  '54',
    'Huila':                     '19',
    'La Guajira':                '48',
    'Magdalena':                 '21',
    'Meta':                      '52',
    'Nariño':                    '23',
    'Norte de Santander':        '25',
    'Putumayo':                  '64',
    'Quindío':                   '26',
    'Risaralda':                 '24',
    'San Andrés y Providencia':  '56',
    'Santander':                 '27',
    'Sucre':                     '28',
    'Tolima':                    '29',
    'Valle del Cauca':           '31',
    'Vaupés':                    '68',
    'Vichada':                   '72',
}

CITIES = {
    'medellin':      {'depCod':'01'}, 'bogota':        {'depCod':'16'},
    'cali':          {'depCod':'31'}, 'barranquilla':  {'depCod':'03'},
    'ibague':        {'depCod':'29'}, 'manizales':     {'depCod':'09'},
    'pereira':       {'depCod':'24'}, 'monteria':      {'depCod':'13'},
    'bucaramanga':   {'depCod':'27'}, 'cucuta':        {'depCod':'25'},
    'neiva':         {'depCod':'19'}, 'popayan':       {'depCod':'11'},
    'sincelejo':     {'depCod':'28'}, 'villavicencio': {'depCod':'52'},
}


def main():
    if len(sys.argv) < 4:
        print('Uso: build-censo-2018-wiki.py <wiki-deptos.json> <censo-2022-nac.json> <base-out>', file=sys.stderr)
        sys.exit(1)
    wiki_path, censo22_path, base_out = sys.argv[1], sys.argv[2], sys.argv[3]

    # Censo 2018 por depto (de Wikipedia)
    wiki = json.load(open(wiki_path))
    by_dep_2018 = {}
    nacional_2018 = 0
    for d in wiki:
        cod = DEPTO_CODE.get(d['depto'])
        if not cod:
            print(f'[warn] depto no mapeado: {d["depto"]}', file=sys.stderr); continue
        by_dep_2018[cod] = d['censo']
        nacional_2018 += d['censo']
    print(f'[wiki] {len(by_dep_2018)} deptos, censo nacional 2018 = {nacional_2018:,}')

    # Censo 2022 por mun (shape interno)
    c22 = json.load(open(censo22_path))
    porMun22 = c22['porMun']
    by_dep_2022 = {}
    for k, v in porMun22.items():
        dep = k.split('-')[0]
        by_dep_2022[dep] = by_dep_2022.get(dep, 0) + v
    print(f'[2022] {len(porMun22)} muns en {len(by_dep_2022)} deps · nacional {sum(by_dep_2022.values()):,}')

    # Reconstruir censo 2018 por mun
    porMun18 = {}
    huérfanos = 0
    for k, v22 in porMun22.items():
        dep = k.split('-')[0]
        dep18 = by_dep_2018.get(dep)
        dep22 = by_dep_2022.get(dep, 0)
        if dep18 is None or dep22 <= 0:
            huérfanos += 1
            continue
        porMun18[k] = round(dep18 * v22 / dep22)
    # Y los muns del depto 88 (Consulados) — si por_mun_2022 los tiene
    print(f'[mun] {len(porMun18)} muns reconstruidos · huérfanos (sin depto 2018): {huérfanos}')

    out_nac = {'year': 2018, 'nacional': nacional_2018, 'porMun': porMun18,
               'fuente': 'wikipedia es · % participación por depto × votos pres-2018 1V',
               'shape': 'proporciones internas tomadas del censo 2022 (Divipole 23-09-2021)'}
    nac_path = os.path.join(base_out, 'puestos-censos-agg-2018.json')
    json.dump(out_nac, open(nac_path, 'w'))
    print(f'✓ {nac_path}')

    # Para las 14 ciudades: por_comuna 2018 = por_comuna_2022 escalado al
    # nuevo total de la ciudad en 2018.
    cities_dir = os.path.join(base_out, 'output_ciudades')
    for city_key, cfg in CITIES.items():
        c22p = os.path.join(cities_dir, city_key, 'censo-comuna-2022.json')
        if not os.path.exists(c22p):
            print(f'[skip] {city_key}: sin censo-comuna-2022'); continue
        j22 = json.load(open(c22p))
        city_total_22 = j22['ciudad_total']
        # Total 2018 de la ciudad = porMun18[depCod-001]
        mun_key = f'{cfg["depCod"]}-001'
        city_total_18 = porMun18.get(mun_key, 0)
        if city_total_18 <= 0:
            print(f'[skip] {city_key}: sin total 2018 (mun {mun_key})'); continue
        ratio = city_total_18 / city_total_22
        por_comuna_18 = {}
        for cod, e in j22['por_comuna'].items():
            por_comuna_18[cod] = {
                'comCod': cod, 'nombre': e['nombre'], 'tipo': e['tipo'],
                'censo': round(e['censo'] * ratio),
                'mujeres': round(e['mujeres'] * ratio),
                'hombres': round(e['hombres'] * ratio),
                'n_puestos': e['n_puestos'],
            }
        n_urb = sum(1 for c in por_comuna_18.values() if c['tipo'] != 'corregimiento')
        n_corr = len(por_comuna_18) - n_urb
        out = {'city': city_key, 'depCod': cfg['depCod'], 'munCod': '001', 'year': 2018,
               'ciudad_total': city_total_18, 'n_comunas': n_urb, 'n_corregimientos': n_corr,
               'por_comuna': por_comuna_18,
               'fuente': 'escalado proporcional desde censo-comuna-2022 con ratio = censo_2018_ciudad / censo_2022_ciudad'}
        out_path = os.path.join(cities_dir, city_key, 'censo-comuna-2018.json')
        json.dump(out, open(out_path, 'w'))
        print(f'✓ {city_key:14s} {n_urb:3d} comunas · censo total {city_total_18:,} (ratio vs 2022 = {ratio:.3f})')


if __name__ == '__main__':
    main()
