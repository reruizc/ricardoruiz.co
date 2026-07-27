#!/usr/bin/env python3
"""
build_jal_resultados.py — agrega los resultados de JAL 2023 por CIUDAD → COMUNA/
LOCALIDAD para el tablero resultados-jal-2023.html (que luego se embebe en
electoral.html · sección 2023). NO es por-candidato (eso lo hace build_jal_2023);
esto es el resumen agregado que colorea el mapa de comunas y llena la tabla.

Ciudades soportadas: las 11 con GeoJSON de comuna/localidad de código numérico
limpio en S3 (mapas-2026/Ciudades-COM-LOC/{CITY}X.json), que casa con el
`CÓDIGO COMUNA` del georef. Bogotá va por LOCALIDAD (LocCodigo 01-20).

Por comuna: votos válidos, blanco, nulos/no-marcados, potencial (censo actual del
georef, aprox.), mesas, partido ganador (más votos JAL), top partidos, top edil.

Fuentes:
  Bases de datos/FINAL SUBIDA GCS/GCS_2023JAL.csv   (COD_COR='5')
  Bases de datos/PUESTOS_GEOREF.csv                 (comuna + censo MUJERES/HOMBRES)

Salida (gitignored):
  Bases de datos/output_jal_2023/resultados-jal-2023.json  (se sube a S3)

Subida a S3:
  aws s3 cp "Bases de datos/output_jal_2023/resultados-jal-2023.json" \
    "s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/jal-2023/resultados-jal-2023.json" \
    --content-type "application/json" --cache-control "public, max-age=300"
"""
import csv, json, os, re, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BD   = os.path.join(ROOT, 'Bases de datos')
SRC  = os.path.join(BD, 'FINAL SUBIDA GCS', 'GCS_2023JAL.csv')
GEOREF = os.path.join(BD, 'PUESTOS_GEOREF.csv')
OUT  = os.path.join(BD, 'output_jal_2023', 'resultados-jal-2023.json')

# (dde, mme) → (nombre, depto, nivel)  ·  nivel = 'localidad' (Bogotá) o 'comuna'
CITIES = {
    ('16', '001'): ('BOGOTÁ D.C.',   'BOGOTÁ D.C.',        'localidad'),
    ('01', '001'): ('MEDELLÍN',      'ANTIOQUIA',          'comuna'),
    ('31', '001'): ('CALI',          'VALLE DEL CAUCA',    'comuna'),
    ('27', '001'): ('BUCARAMANGA',   'SANTANDER',          'comuna'),
    ('25', '001'): ('CÚCUTA',        'NORTE DE SANTANDER', 'comuna'),
    ('29', '001'): ('IBAGUÉ',        'TOLIMA',             'comuna'),
    ('09', '001'): ('MANIZALES',     'CALDAS',             'comuna'),
    ('13', '001'): ('MONTERÍA',      'CÓRDOBA',            'comuna'),
    ('19', '001'): ('NEIVA',         'HUILA',              'comuna'),
    ('11', '001'): ('POPAYÁN',       'CAUCA',              'comuna'),
    ('52', '001'): ('VILLAVICENCIO', 'META',               'comuna'),
}
SPECIAL = {'996', '997', '998', '999'}   # blanco, nulos, no-marcados, no-marcados
C_CAN, C_VOT, C_DDE, C_MME, C_ZZ, C_PP = 13, 15, 6, 7, 8, 9
C_MS, C_PAR, C_DESPAR, C_DESCAN = 10, 11, 12, 14


def strip(s):
    return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper().strip()


def clean_com(comN):
    c = re.sub(r'^\d+', '', (comN or '').strip()).strip()
    return c or 'ND'


def load_georef():
    """(dd,mm,zz,pp) → comCode · potencial por (dd,mm,comCode)."""
    by9 = {}
    pot = {}   # (dd,mm,comCode) → censo (M+H)
    comN = {}  # (dd,mm,comCode) → nombre limpio
    keys = {f'{dd}{mm}' for (dd, mm) in [(d.zfill(2), m.zfill(3)) for (d, m) in CITIES]}
    with open(GEOREF, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f, delimiter=';'):
            code = (row.get('CÓDIGO COMPLETO') or '').strip()
            if len(code) != 9 or code[:5] not in keys:
                continue
            comC = (row.get('CÓDIGO COMUNA') or '').strip()
            name = (row.get('NOMBRE COMUNA') or '').strip()
            if comC.upper() in ('NULL', ''):
                comC = 'ND'
            by9[code] = comC
            k = (code[:2], code[2:5], comC)
            try:
                m = int((row.get('MUJERES') or '0').strip() or 0)
                h = int((row.get('HOMBRES') or '0').strip() or 0)
            except ValueError:
                m = h = 0
            pot[k] = pot.get(k, 0) + m + h
            if k not in comN and name.upper() not in ('NULL', ''):
                comN[k] = clean_com(name)
    return by9, pot, comN


def main():
    by9, pot, comN = load_georef()
    # data[(dde,mme)] = { comCode: {name, validos, blanco, nulos, mesas:set,
    #                     parties:{p:v}, cands:{(par,can,name):v}} }
    data = {}
    for (dde, mme) in CITIES:
        data[(dde, mme)] = {}
    n = 0
    with open(SRC, encoding='utf-8', errors='replace', newline='') as f:
        rd = csv.reader(f, delimiter=';')
        next(rd, None)  # header
        for row in rd:
            if len(row) < 16:
                continue
            dde = row[C_DDE].strip(); mme = row[C_MME].strip().zfill(3)
            keyc = (dde.zfill(2), mme)   # CITIES usa dde con cero a la izquierda
            if keyc not in CITIES:
                continue
            can = row[C_CAN].strip()
            try:
                v = int(row[C_VOT] or 0)
            except ValueError:
                v = 0
            if v <= 0:
                continue
            dd = dde.zfill(2); mm = mme
            zz = (row[C_ZZ] or '').strip().zfill(2); pp = (row[C_PP] or '').strip().zfill(2)
            comC = by9.get(f'{dd}{mm}{zz}{pp}', 'ND')
            cd = data[keyc]
            c = cd.get(comC)
            if c is None:
                c = cd[comC] = {'validos': 0, 'blanco': 0, 'nulos': 0,
                                'mesas': set(), 'parties': {}, 'cands': {}, 'partyOf': {}}
            ms = (row[C_MS] or '').strip().zfill(3)
            c['mesas'].add((zz, pp, ms))
            if can == '0':                 # fila de partido (encabezado) — ignorar
                continue
            if can == '996':
                c['blanco'] += v
            elif can in SPECIAL:
                c['nulos'] += v
            else:
                c['validos'] += v
                par = row[C_PAR].strip()
                party = (row[C_DESPAR] or '').strip() or 'SIN PARTIDO'
                c['parties'][party] = c['parties'].get(party, 0) + v
                c['partyOf'][par] = party
                nom = strip(row[C_DESCAN]) or f'CAND {can}'
                ck = (par, can, nom)
                c['cands'][ck] = c['cands'].get(ck, 0) + v
            n += 1

    out_cities = []
    out_data = {}
    for (dde, mme), (name, dep, nivel) in CITIES.items():
        cd = data[(dde, mme)]
        comunas = {}
        tot_val = tot_bl = tot_pot = 0
        city_parties = {}
        for comC, c in cd.items():
            if comC == 'ND':
                continue   # corregimientos/sin-comuna fuera del mapa de comunas
            # partidos ordenados desc + índice para comprimir la lista de candidatos
            parties = sorted(c['parties'].items(), key=lambda kv: -kv[1])
            pidx = {p: i for i, (p, _) in enumerate(parties)}
            # TODOS los candidatos de la comuna, ordenados por votos desc.
            # cada uno = [nombre, índice-de-partido, votos]  (partyIdx apunta a partidos[])
            cands = sorted(c['cands'].items(), key=lambda kv: -kv[1])
            cand_list = [[nom, pidx.get(c['partyOf'].get(par), 0), v]
                         for (par, can, nom), v in cands]
            potc = pot.get((dde, mme, comC), 0)
            votantes = c['validos'] + c['blanco'] + c['nulos']
            comunas[comC] = {
                'name': comN.get((dde, mme, comC), f'COMUNA {int(comC)}' if comC.isdigit() else comC),
                'validos': c['validos'], 'blanco': c['blanco'], 'nulos': c['nulos'],
                'votantes': votantes, 'potencial': potc, 'mesas': len(c['mesas']),
                'partidos': [[p, vv] for p, vv in parties],   # ganador = partidos[0]
                'cands': cand_list,                            # top edil = cands[0]
            }
            tot_val += c['validos']; tot_bl += c['blanco']; tot_pot += potc
            for p, vv in c['parties'].items():
                city_parties[p] = city_parties.get(p, 0) + vv
        if not comunas:
            continue
        top_city_parties = sorted(city_parties.items(), key=lambda kv: -kv[1])[:8]
        key = f'{dde}-{mme}'
        out_cities.append({
            'key': key, 'name': name, 'dep': dep, 'nivel': nivel,
            'dde': dde, 'mme': mme, 'n_comunas': len(comunas),
            'validos': tot_val, 'blanco': tot_bl, 'potencial': tot_pot,
        })
        out_data[key] = {'comunas': comunas,
                         'totals': {'validos': tot_val, 'blanco': tot_bl,
                                    'potencial': tot_pot,
                                    'top_partidos': [[p, vv] for p, vv in top_city_parties]}}

    out_cities.sort(key=lambda x: -x['validos'])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'v': '2026-07-26', 'eleccion': 'JAL (Ediles) 2023',
                   'cities': out_cities, 'data': out_data},
                  f, ensure_ascii=False, separators=(',', ':'))
    print(f'{n:,} filas · {len(out_cities)} ciudades → {OUT}')
    print(f'  ({os.path.getsize(OUT)//1024} KB)')
    for cc in out_cities:
        print(f"  {cc['name']:14} {cc['n_comunas']:2} {cc['nivel']:9} · {cc['validos']:>9,} válidos")


if __name__ == '__main__':
    main()
