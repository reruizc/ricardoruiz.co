#!/usr/bin/env python3
"""
build_territorial_resultados.py — agrega una corporación LOCAL de 2023 por
CIUDAD → COMUNA/LOCALIDAD para los tableros resultados-{jal,concejo}-2023.html.
NO es por-candidato (eso lo hacen build_jal_2023 / build_concejo_2023); esto es el
resumen agregado que colorea el mapa de comunas y llena la tabla.

    python3 build_territorial_resultados.py jal [AÑO]      # JAL / ediles   (default)
    python3 build_territorial_resultados.py concejo [AÑO]  # Concejo distrital / municipal

AÑO = 2023 (default, no cambia nada de lo que ya existe) o 2019. Los códigos de
corporación cambian por año: 2023 → JAL en GCS_2023JAL (COR 5) y concejo en
GCS_2023TER (COR 4); 2019 → JAL en GCS_2019JAL (COR 5, con las columnas en OTRO
orden: la geografía va antes de COD_COR) y concejo en GCS_2019TER (COR 7). Las
columnas se leen por NOMBRE (gcs_columnas), así que el orden distinto de
GCS_2019JAL no exige un layout aparte.

⚠️⚠️ El georef es de 2026 y el código de puesto NO es estable entre elecciones
(Villavicencio 2019: solo un tercio de los códigos nombra el mismo lugar en
2026). Para años distintos de 2023 la comuna de cada puesto sale de la cascada
de `puestos_historicos.resolver` (nombre del puesto en el censo del año contra
el georef 2026 y el Divipol 2021). Lo que no se puede ubicar queda fuera del
mapa y se cuenta por ciudad en `fuera_mapa` (no se esconde).

Ciudades soportadas: las 11 con GeoJSON de comuna/localidad de código numérico
limpio en S3 (mapas-2026/Ciudades-COM-LOC/{CITY}X.json), que casa con el
`CÓDIGO COMUNA` del georef. Bogotá va por LOCALIDAD (LocCodigo 01-20).

Por comuna: votos válidos, blanco, nulos/no-marcados, potencial (censo actual del
georef, aprox.), mesas, partido ganador (más votos), top partidos, top candidato.

⚠️ El CSV de JAL es mono-corporación, pero **GCS_2023TER trae las 4 corporaciones
INTERCALADAS** (1=gobernador · 2=asamblea · 3=alcalde · 4=concejo) → el filtro por
`COD_COR` es obligatorio, no decorativo.

Fuentes:
  Bases de datos/FINAL SUBIDA GCS/GCS_2023{JAL,TER}.csv
  Bases de datos/PUESTOS_GEOREF.csv                 (comuna + censo MUJERES/HOMBRES)

Salida (gitignored):
  Bases de datos/output_{jal,concejo}_2023/resultados-{corp}-2023.json  (se sube a S3)

Subida a S3:
  aws s3 cp "Bases de datos/output_jal_2023/resultados-jal-2023.json" \
    "s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/jal-2023/resultados-jal-2023.json" \
    --content-type "application/json" --cache-control "public, max-age=300"
"""
import csv, datetime, json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BD   = os.path.join(ROOT, 'Bases de datos')
GEOREF = os.path.join(BD, 'PUESTOS_GEOREF.csv')

# corporación → CSV crudo · COD_COR · carpeta de salida · rótulos, POR AÑO
CORPS = {
    'jal': {
        2023: {'csv': 'GCS_2023JAL.csv', 'cor': '5'},
        2019: {'csv': 'GCS_2019JAL.csv', 'cor': '5'},
        'eleccion': 'JAL (Ediles) {año}',
    },
    'concejo': {
        2023: {'csv': 'GCS_2023TER.csv', 'cor': '4'},
        2019: {'csv': 'GCS_2019TER.csv', 'cor': '7'},
        'eleccion': 'Concejo Distrital / Municipal {año}',
    },
}
CORP = sys.argv[1] if len(sys.argv) > 1 else 'jal'
if CORP not in CORPS:
    sys.exit(f'corporación desconocida: {CORP} (usa {" | ".join(CORPS)})')
AÑO = int(sys.argv[2]) if len(sys.argv) > 2 else 2023
if AÑO not in CORPS[CORP]:
    sys.exit(f'año sin configurar para {CORP}: {AÑO}')
CFG = dict(CORPS[CORP][AÑO], dir=f'output_{CORP}_{AÑO}',
           file=f'resultados-{CORP}-{AÑO}.json',
           eleccion=CORPS[CORP]['eleccion'].format(año=AÑO))
SRC = os.path.join(BD, 'FINAL SUBIDA GCS', CFG['csv'])
OUT = os.path.join(BD, CFG['dir'], CFG['file'])

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
    ('05', '001'): ('CARTAGENA',     'BOLÍVAR',            'comuna'),
}
# Cartagena no tiene su unidad en el georef —ahí solo van sus 3 localidades— y
# su división operativa son las 15 UCG más la 20 rural. El mapa puesto → UCG lo
# produce build_cartagena_ucg.py y lo comparte con el detalle por comuna, para
# que la misma cuenta no viva en dos builders.
# ⚠️⚠️ Va por CORPORACIÓN: las JAL de Cartagena se eligen por LOCALIDAD, no por
# UCG (medido sobre sus 347 candidatos de 2023: tres bloques de zonas que son
# sus 3 localidades). Para JAL manda el «CÓDIGO COMUNA» del georef.
COMUNA_EXTERNA = {
    'concejo': {('05', '001'): os.path.join(BD, 'output_hvp', 'cartagena-puesto-ucg.json')},
    'jal': {},
}.get(CORP, {})
# Cómo se llama la unidad de las ciudades resueltas por archivo externo.
COM_LABEL = {('05', '001'): 'UCG'} if CORP == 'concejo' else {}
VERSION = datetime.date.today().isoformat()
SPECIAL = {'996', '997', '998', '999'}   # blanco, nulos, no-marcados, no-marcados
# Columnas por NOMBRE: el archivo territorial trae 19 columnas y el de JAL 16.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gcs_columnas import columnas                                    # noqa: E402
_C = columnas(SRC)
C_COR = _C['COD_COR']
C_CAN, C_VOT, C_DDE, C_MME, C_ZZ, C_PP = _C['COD_CAN'], _C['NUM_VOT'], _C['COD_DDE'], _C['COD_MME'], _C['COD_ZZ'], _C['COD_PP']
C_MS, C_PAR, C_DESPAR, C_DESCAN = _C['DES_MS'], _C['COD_PAR'], _C['DES_PAR'], _C['DES_CAN']
C_ANCHO = _C['_ancho']


def strip(s):
    return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper().strip()


def clean_com(comN):
    # Espacios internos colapsados: el georef trae nombres con doble espacio
    # ('COMUNA  5') que si no partirían la misma comuna en dos.
    c = re.sub(r'\s+', ' ', re.sub(r'^\d+', '', (comN or '').strip())).strip()
    return c or 'ND'


def load_georef():
    """(dd,mm,zz,pp) → comCode · potencial por (dd,mm,comCode)."""
    by9 = {}
    _EXTERNA = {}
    for keyc, ruta in COMUNA_EXTERNA.items():
        if os.path.exists(ruta):
            with open(ruta, encoding='utf-8') as fh:
                _EXTERNA[keyc] = json.load(fh)
        else:
            print(f'· ⚠ sin {os.path.basename(ruta)}: esa ciudad se queda sin comuna')
    pot = {}   # (dd,mm,comCode) → censo (M+H)
    comN = {}  # (dd,mm,comCode) → nombre limpio
    nom26 = {}  # code26 → nombre del puesto (para ubicar puestos de años viejos)
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
            keyc = (code[:2], code[2:5])
            ext = _EXTERNA.get(keyc)
            if ext is not None:
                comC = ext.get(code, 'ND')
                # El nombre del georef es el de la LOCALIDAD y ya no corresponde
                # a esta unidad: las 16 UCG de Cartagena caen dentro de solo 3
                # localidades, así que dejarlo repetía «LOC. 3 INDUSTRIAL DE LA
                # BAHÍA» en cinco comunas distintas.
                name = f"{COM_LABEL.get(keyc, 'COMUNA')} {int(comC)}" if comC.isdigit() else ''
            by9[code] = comC
            nom26[code] = (row.get('NOMBRE PUESTO') or '').strip()
            k = (code[:2], code[2:5], comC)
            try:
                m = int((row.get('MUJERES') or '0').strip() or 0)
                h = int((row.get('HOMBRES') or '0').strip() or 0)
            except ValueError:
                m = h = 0
            pot[k] = pot.get(k, 0) + m + h
            if k not in comN and name.upper() not in ('NULL', ''):
                comN[k] = clean_com(name)
    return by9, pot, comN, nom26


def main():
    by9, pot, comN, nom26 = load_georef()
    HIST = None
    if AÑO != 2023:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from puestos_historicos import resolver                          # noqa: E402
        HIST = resolver(AÑO, set(CITIES), by9, nom26, set(COMUNA_EXTERNA))
        print(f'· {AÑO}: {len(HIST)} puestos ubicados por nombre (cascada B·A·C)')
    # data[(dde,mme)] = { comCode: {name, validos, blanco, nulos, mesas:set,
    #                     parties:{p:v}, cands:{(par,can,name):v}} }
    data = {}
    for (dde, mme) in CITIES:
        data[(dde, mme)] = {}
    # Lo que no entra al mapa por comuna, por ciudad: votos de puestos que el
    # georef 2026 no conoce (en años viejos, puestos que ya no existen) y votos
    # de puestos que sí conoce pero sin comuna (corregimientos, zona rural).
    # Todos son votos totales (válidos + blanco + nulos + no marcados).
    fuera = {k: {'sin_georef': 0, 'puestos_sin_georef': set(), 'sin_comuna': 0,
                 'total_csv': 0, 'regla': {}} for k in CITIES}
    n = 0
    with open(SRC, encoding='utf-8', errors='replace', newline='') as f:
        rd = csv.reader(f, delimiter=';')
        next(rd, None)  # header
        for row in rd:
            if len(row) < C_ANCHO:
                continue
            if row[C_COR].strip() != CFG['cor']:   # GCS_2023TER mezcla las 4 corporaciones
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
            pcode = f'{dd}{mm}{zz}{pp}'
            fz = fuera[keyc]
            fz['total_csv'] += v
            if HIST is None:
                ubicado = pcode in by9
                comC = by9.get(pcode, 'ND')
            else:
                h = HIST.get(pcode)
                ubicado = h is not None
                comC = h[0] if h else 'ND'
                if h:
                    fz['regla'][h[3]] = fz['regla'].get(h[3], 0) + v
            if not ubicado:
                fz['sin_georef'] += v
                fz['puestos_sin_georef'].add(pcode)
            elif comC == 'ND':
                fz['sin_comuna'] += v
            cd = data[keyc]
            c = cd.get(comC)
            if c is None:
                c = cd[comC] = {'validos': 0, 'blanco': 0, 'nulos': 0,
                                'mesas': set(), 'parties': {}, 'cands': {},
                                'partyOf': {}, 'listas': {}}
            ms = (row[C_MS] or '').strip().zfill(3)
            c['mesas'].add((zz, pp, ms))
            if can == '996':
                c['blanco'] += v
            elif can in SPECIAL:
                c['nulos'] += v
            else:
                # can == '0' es el voto SOLO POR LA LISTA (y, en lista cerrada,
                # todo su voto). Es un voto válido por ese partido aunque no sea
                # de ningún candidato: ignorarlo dejaba fuera el ~30 % de los
                # válidos y borraba del mapa a las listas cerradas.
                c['validos'] += v
                par = row[C_PAR].strip()
                party = (row[C_DESPAR] or '').strip() or 'SIN PARTIDO'
                c['parties'][party] = c['parties'].get(party, 0) + v
                c['partyOf'][par] = party
                if can == '0':
                    c['listas'][party] = c['listas'].get(party, 0) + v
                else:
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
                'listas': [[p, vv] for p, vv in sorted(c['listas'].items(), key=lambda kv: -kv[1])],
                'cands': cand_list,                            # top edil = cands[0]
            }
            tot_val += c['validos']; tot_bl += c['blanco']; tot_pot += potc
            for p, vv in c['parties'].items():
                city_parties[p] = city_parties.get(p, 0) + vv
        if not comunas:
            continue
        top_city_parties = sorted(city_parties.items(), key=lambda kv: -kv[1])[:8]
        key = f'{dde}-{mme}'
        fz = fuera[(dde, mme)]
        out_cities.append({
            'key': key, 'name': name, 'dep': dep, 'nivel': nivel,
            'dde': dde, 'mme': mme, 'n_comunas': len(comunas),
            'validos': tot_val, 'blanco': tot_bl, 'potencial': tot_pot,
            # votos_sin_ubicar: puesto que no se pudo ubicar (2023: código que el
            # georef 2026 no tiene; años viejos: sin par por nombre en la cascada).
            'fuera_mapa': {'votos_sin_ubicar': fz['sin_georef'],
                           'puestos_sin_ubicar': len(fz['puestos_sin_georef']),
                           'votos_sin_comuna': fz['sin_comuna'],
                           'votos_total_csv': fz['total_csv'],
                           **({'votos_por_regla': fz['regla']} if HIST is not None else {})},
        })
        out_data[key] = {'comunas': comunas,
                         'totals': {'validos': tot_val, 'blanco': tot_bl,
                                    'potencial': tot_pot,
                                    'top_partidos': [[p, vv] for p, vv in top_city_parties]}}

    out_cities.sort(key=lambda x: -x['validos'])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'v': VERSION, 'anio': AÑO, 'eleccion': CFG['eleccion'],
                   'cities': out_cities, 'data': out_data},
                  f, ensure_ascii=False, separators=(',', ':'))
    print(f'{n:,} filas · {len(out_cities)} ciudades → {OUT}')
    print(f'  ({os.path.getsize(OUT)//1024} KB)')
    for cc in out_cities:
        fz = cc['fuera_mapa']
        pct = 100 * fz['votos_sin_ubicar'] / fz['votos_total_csv'] if fz['votos_total_csv'] else 0
        print(f"  {cc['name']:14} {cc['n_comunas']:2} {cc['nivel']:9} · {cc['validos']:>9,} válidos"
              f" · sin ubicar: {fz['puestos_sin_ubicar']} puestos, {fz['votos_sin_ubicar']:,} votos ({pct:.2f} %)"
              f" · sin comuna: {fz['votos_sin_comuna']:,}"
              + (f" · por regla {fz['votos_por_regla']}" if 'votos_por_regla' in fz else ''))


if __name__ == '__main__':
    main()
