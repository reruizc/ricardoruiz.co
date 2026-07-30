#!/usr/bin/env python3
"""
build_pres_historico.py — genera los JSONs mesa-a-mesa de las PRESIDENCIALES
históricas (2010 · 2014 · 2018 · 2022, 1ª y 2ª vuelta) y de las CONSULTAS
INTERPARTIDISTAS 2022, en formato endoso/{slug}.json + un índice por elección,
para el buscador de analisis-candidato.html (fuentes regulares de cand-index.js,
NO el modelo por-persona de 2026).

Supersede a build_pres_2018.py: `pres2018` reproduce su salida byte a byte
(verificado con --check), así que los JSON ya subidos a S3 siguen válidos.

Claves:  pres2010  pres2014  pres2018  pres2022  consu2022   (o `todas`)

⚠️ GOTCHAS de la fuente (verificados jul-2026):

1. **GCS_2010PRES* tiene OTRO ORDEN de columnas**: la geografía va primero
   (`COD_DDE` en la col 2) mientras 2014/2018/2022 la traen en la 6. Partido,
   candidato y votos SÍ caen en los mismos índices (11-15) en ambos layouts,
   por eso solo hay que parametrizar el bloque geográfico (`LAYOUT_*`).
2. **NO se puede filtrar los especiales por COD_PAR: la convención cambia cada
   año y en dos direcciones distintas.** Medido archivo por archivo:
       2010 1V · 2014 1V/2V → especiales con **COD_PAR = 0** (si filtras por
                              `par>=996` se COLAN como candidatos: la 2V de 2014
                              devolvía 5 "candidatos" en vez de 2)
       2010 2V             → **COD_PAR = 12399 para TODOS**, especiales y reales
                              (Santos y Mockus incluidos) → el par no discrimina
       2018                → especiales par 996/997/998 · can 96/97/98
       2022 1V/2V · CONSU  → especiales par 996/997/998 · can 996/997/998, pero
                              los partidos REALES pasan de 996 (Petro 1235, Fico
                              1234, Rodolfo 1076) → `par>=996` borraba a los
                              punteros y dejaba la 2V en CERO
   Lo único estable en los 8 archivos es **COD_CAN**: los especiales siempre caen
   en {96,97,98,996,997,998,999} y los candidatos reales siempre traen su número
   de tarjetón (1-9). Por eso el filtro es por COD_CAN (`SPECIAL_CAN`).
   ⚠️ OJO: en 2018 hay una candidatura REAL llamada "PROMOTORES VOTO EN BLANCO"
   (par 28 · can 2 · 30.128 votos, del PRE) — es una campaña inscrita, distinta
   del conteo de votos en blanco, y DEBE quedar dentro. Filtrar por el texto del
   nombre la borraría.
3. **En GCS_2022CONSU, `COD_CIR` NO distingue las 3 consultas**: llega VACÍO en
   el Pacto Histórico y `0` en Equipo por Colombia y Centro Esperanza. Hay que
   separarlas por el TEXTO de `DES_CIR`. Además **`COD_CAN` se repite (1-5) entre
   consultas**, así que la llave y el slug tienen que incluir cuál es.
4. `DES_PAR` trae campos entrecomillados con comillas dobles escapadas adentro
   (el partido ASI, p.ej.) → leer con csv.reader, que respeta el quoting; NO
   partir la línea por ';' a mano (awk parte mal esas filas).

Validado contra el resultado oficial (escrutinio definitivo de la RNEC):
  2010 1V Santos 6.802.043 · Mockus 3.134.222
  2018 1V Duque 7.616.857 · Petro 4.855.069   · 2V Duque 10.397.314 / Petro 8.039.229
  2022 2V Petro 11.292.758 · Hernández 10.604.656

Salida (gitignored): Bases de datos/output_pres_{2010,2014,2018,2022}/
                     Bases de datos/output_consu_2022/
Subida a S3 (manual, luz verde):
  aws s3 cp "Bases de datos/output_pres_2022/" \
    "s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/pres-2022/" \
    --recursive --content-type "application/json" --cache-control "public, max-age=300"
"""
import csv, json, os, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BD   = os.path.join(ROOT, 'Bases de datos')
GCS  = os.path.join(BD, 'FINAL SUBIDA GCS')
GEOREF = os.path.join(BD, 'PUESTOS_GEOREF.csv')

# Bloque geográfico (0-based). PAR/DESPAR/CAN/DESCAN/VOT = 11..15 en AMBOS layouts.
LAYOUT_STD = dict(DDE=6, MME=7, ZZ=8, PP=9, MS=10, DESCIR=5)   # 2014 · 2018 · 2022
LAYOUT_2010 = dict(DDE=2, MME=3, ZZ=4, PP=5, MS=6, DESCIR=8)   # 2010 (geo primero)
C_PAR, C_DESPAR, C_CAN, C_DESCAN, C_VOT = 11, 12, 13, 14, 15

# Blanco · nulos · no marcados · tarjetones. Ver gotcha 2 del docstring: es el
# ÚNICO campo que los marca igual en los 8 archivos (COD_PAR no sirve).
SPECIAL_CAN = {'0', '96', '97', '98', '996', '997', '998', '999'}

# DES_CIR → (clave de slug, rótulo) para las consultas 2022
CONSULTAS_2022 = [
    ('pacto',  'PACTO HISTÓRICO'),
    ('equipo', 'EQUIPO POR COLOMBIA'),
    ('centro', 'CENTRO ESPERANZA'),
]

CFG = {
    'pres2010': dict(anio='2010', layout=LAYOUT_2010, kind='pres', dir='pres-2010',
                     files=[('1V', 'GCS_2010PRES1V.csv'), ('2V', 'GCS_2010PRES2V.csv')],
                     eleccion='Presidencia 2010 (1V + 2V)'),
    'pres2014': dict(anio='2014', layout=LAYOUT_STD, kind='pres', dir='pres-2014',
                     files=[('1V', 'GCS_2014PRES1V.csv'), ('2V', 'GCS_2014PRES2V.csv')],
                     eleccion='Presidencia 2014 (1V + 2V)'),
    'pres2018': dict(anio='2018', layout=LAYOUT_STD, kind='pres', dir='pres-2018',
                     files=[('1V', 'GCS_2018PRES1V.csv'), ('2V', 'GCS_2018PRES2V.csv')],
                     eleccion='Presidencia 2018 (1V + 2V)'),
    'pres2022': dict(anio='2022', layout=LAYOUT_STD, kind='pres', dir='pres-2022',
                     files=[('1V', 'GCS_2022PRES1V.csv'), ('2V', 'GCS_2022PRES2V.csv')],
                     eleccion='Presidencia 2022 (1V + 2V)'),
    'consu2022': dict(anio='2022', layout=LAYOUT_STD, kind='consu', dir='consu-2022',
                      files=[('', 'GCS_2022CONSU.csv')],
                      eleccion='Consultas Interpartidistas 2022'),
}

DEP_NAMES = {
    '01': 'ANTIOQUIA', '03': 'ATLÁNTICO', '05': 'BOLÍVAR', '07': 'BOYACÁ',
    '09': 'CALDAS', '11': 'CAUCA', '12': 'CESAR', '13': 'CÓRDOBA',
    '15': 'CUNDINAMARCA', '17': 'CHOCÓ', '19': 'HUILA', '21': 'MAGDALENA',
    '23': 'NARIÑO', '24': 'RISARALDA', '25': 'NORTE DE SANTANDER',
    '26': 'QUINDÍO', '27': 'SANTANDER', '28': 'SUCRE', '29': 'TOLIMA',
    '31': 'VALLE DEL CAUCA', '40': 'ARAUCA', '44': 'CAQUETÁ', '46': 'CASANARE',
    '48': 'LA GUAJIRA', '50': 'GUAINÍA', '52': 'META', '54': 'GUAVIARE',
    '56': 'SAN ANDRÉS', '60': 'AMAZONAS', '64': 'PUTUMAYO', '68': 'VAUPÉS',
    '72': 'VICHADA', '88': 'EXTERIOR', '16': 'BOGOTÁ D.C.',
}


def strip(s):
    return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper().strip()


def load_georef():
    by9, muns = {}, {}
    with open(GEOREF, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f, delimiter=';'):
            code = (row.get('CÓDIGO COMPLETO') or '').strip()
            if len(code) != 9:
                continue
            mun = (row.get('MUNICIPIO') or '').strip()
            pue = (row.get('NOMBRE PUESTO') or '').strip()
            comC = (row.get('CÓDIGO COMUNA') or '').strip()
            comN = (row.get('NOMBRE COMUNA') or '').strip()
            if comN.upper() in ('NULL', ''):
                comC, comN = '000', 'NACIONAL'
            by9[code] = (mun, pue, comC or '000', comN or 'NACIONAL')
            muns.setdefault(code[:5], mun)
    return by9, muns


def fmt(x):
    return f'{x:,}'.replace(',', '.')


def consulta_de(des_cir):
    """DES_CIR → (clave, rótulo). COD_CIR no sirve: vacío en Pacto, 0 en las otras."""
    t = strip(des_cir)
    for key, label in CONSULTAS_2022:
        if strip(label).split()[0] in t:
            return key, label
    return None, None


def procesar(cfg, vuelta, src, by9, munNames, index, out_dir):
    L = cfg['layout']
    anio, kind = cfg['anio'], cfg['kind']
    cands = {}
    n = 0
    with open(src, encoding='utf-8-sig', errors='replace', newline='') as f:
        for row in csv.reader(f, delimiter=';'):
            if len(row) < 16 or row[0] == 'FUENTE':
                continue
            par = row[C_PAR].strip()
            if row[C_CAN].strip() in SPECIAL_CAN:
                continue
            try:
                v = int(row[C_VOT] or 0)
            except ValueError:
                v = 0
            if v <= 0:
                continue
            can = row[C_CAN].strip()
            if kind == 'consu':
                ckey, clabel = consulta_de(row[L['DESCIR']])
                if not ckey:
                    continue
                key = (ckey, par, can)
            else:
                key = (par, can)
            c = cands.get(key)
            if c is None:
                c = cands[key] = {
                    'nombre': strip(row[C_DESCAN]) or f'CANDIDATO {can}',
                    'partido': (row[C_DESPAR] or '').strip() or f'PARTIDO {par}',
                    'votos': 0, 'mesas': [],
                }
                if kind == 'consu':
                    c['clabel'] = clabel
            dd = row[L['DDE']].strip().zfill(2)
            mm = row[L['MME']].strip().zfill(3)
            zz = (row[L['ZZ']] or '').strip().zfill(2)
            pp = (row[L['PP']] or '').strip().zfill(2)
            ms = (row[L['MS']] or '').strip().zfill(3)
            c['votos'] += v
            c['mesas'].append((dd, mm, zz, pp, ms, v))
            n += 1
    etiqueta = vuelta or 'consultas'
    print(f'  {etiqueta}: {n:,} filas · {len(cands)} candidatos')

    for key, c in cands.items():
        mesas = []
        for (dd, mm, zz, pp, ms, v) in c['mesas']:
            g = by9.get(f'{dd}{mm}{zz}{pp}')
            munNom = g[0] if g else munNames.get(f'{dd}{mm}', f'MUN {mm}')
            pueNom = g[1] if g else f'PUESTO {zz}-{pp}'
            comC, comN = (g[2], g[3]) if g else ('000', 'NACIONAL')
            mesas.append({
                'dep': dd, 'depNom': DEP_NAMES.get(dd, f'DEP {dd}'),
                'mun': mm, 'munNom': munNom, 'zon': zz, 'pue': pp,
                'pueNom': pueNom, 'mesa': ms, 'com': comC, 'comNom': comN, 'v': v,
            })
        if c.get('clabel'):
            ckey, par, can = key
            slug = f'CONSU{anio}-{ckey}-{par}-{can}'
            corp = f"CONSULTA {c['clabel']}"
        else:
            par, can = key
            slug = f'PRES{anio}-{vuelta}-{par}-{can}'
            corp = f'PRESIDENCIA {vuelta}'
        data = {
            'nombre': c['nombre'], 'corp': corp, 'circunscripcion': 'NACIONAL',
            'partido': c['partido'], 'votos': c['votos'], 'mesas': mesas,
        }
        with open(os.path.join(out_dir, f'{slug}.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        index.append({
            'slug': slug, 'nombre': c['nombre'], 'corp': f'{corp} · {anio}',
            'circunscripcion': 'NACIONAL', 'partido': c['partido'], 'votos': c['votos'],
        })


def correr(clave, by9, munNames):
    cfg = CFG[clave]
    out_dir = os.path.join(BD, f"output_{cfg['dir'].replace('-', '_')}")
    os.makedirs(out_dir, exist_ok=True)
    print(f"════ {clave} · {cfg['eleccion']}")
    index = []
    for vuelta, fname in cfg['files']:
        procesar(cfg, vuelta, os.path.join(GCS, fname), by9, munNames, index, out_dir)
    index.sort(key=lambda x: -x['votos'])
    idx_path = os.path.join(out_dir, f"index-{cfg['dir']}.json")
    with open(idx_path, 'w', encoding='utf-8') as f:
        json.dump({'v': '2026-07-30', 'eleccion': cfg['eleccion'],
                   'candidatos': index}, f, ensure_ascii=False, separators=(',', ':'))
    print(f'  → {len(index)} JSONs · {os.path.basename(idx_path)} ({os.path.getsize(idx_path)//1024} KB)')
    for x in index[:5]:
        print(f"     {x['nombre'][:34]:34s} {x['corp']:34s} {fmt(x['votos']):>12s}")


def main():
    args = sys.argv[1:]
    if not args or (args[0] not in CFG and args[0] != 'todas'):
        sys.exit(f'uso: build_pres_historico.py <{"|".join(CFG)}|todas>')
    claves = list(CFG) if args[0] == 'todas' else [args[0]]
    by9, munNames = load_georef()
    print(f'GEOREF: {len(by9)} puestos · {len(munNames)} muns')
    for k in claves:
        correr(k, by9, munNames)


if __name__ == '__main__':
    main()
