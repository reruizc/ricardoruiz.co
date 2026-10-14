#!/usr/bin/env python3
"""
validar_tableros.py — concilia los tableros territoriales de un año contra el
CSV crudo de la Registraduría y contra los índices de candidatos de S3.

    python3 tools/analisis-candidato/validar_tableros.py 2019 --indices <dir>

<dir> tiene index-{alcaldia,asamblea,concejo,jal}-{año}.json bajados de S3
(pueden venir en gzip). Sale con código 1 si algo no cuadra.

Qué comprueba:
  1. JAL y Concejo, por ciudad: válidos, blanco y nulos+no marcados del tablero
     == los del CSV en los puestos que el tablero muestra, y lo que queda fuera
     del mapa explica EXACTAMENTE la diferencia con el total del CSV.
  2. Por candidato y ciudad: tablero == CSV en los puestos del tablero, y
     CSV completo == índice de S3 (la diferencia es solo lo que está fuera del mapa).
  3. Asamblea, por departamento: válidos/blanco/nulos == CSV; por candidato == índice.
  4. Alcaldía, por municipio y candidato == índice; válidos/especiales == CSV.
  5. Controles fijos del año (CONTROLES).
"""
import argparse, csv, glob, gzip, json, os, sys, unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BD = os.path.join(RAIZ, 'Bases de datos')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gcs_columnas import columnas                                    # noqa: E402

COR = {2019: {'alcaldia': '6', 'asamblea': '5', 'concejo': '7', 'jal': '5'},
       2015: {'alcaldia': '3', 'asamblea': '2', 'concejo': '4', 'jal': '5'},
       2011: {'alcaldia': '6', 'asamblea': '5', 'concejo': '7', 'jal': '8'}}
CSV_JAL = {2019: 'GCS_2019JAL.csv', 2015: 'GCS_2015TER.csv', 2011: 'GCS_2011TER.csv'}
# Controles fijos por año (cifras oficiales ya validadas en CLAUDE.md):
#   alcalde de Bogotá y votos · depto y apellido del diputado más votado
CONTROLES = {2019: ('CLAUDIA', 1109362, '31', 'GARCES ROJAS'),
             2015: ('PENALOSA', 906058, '31', 'GARCES ROJAS'),
             2011: ('PETRO', 723157, '03', 'MERLANO')}
ESP = {'996': 'blanco', '997': 'nulos', '998': 'nulos', '999': 'nulos'}
FALLAS = []
# Defectos de la FUENTE, medidos y explicados: no son del tablero.
# Concejo Bogotá 2019: filas con COD_PAR 13 · COD_CAN 13 (Hubert Zamora) rotuladas
# con el nombre de Marlene Puentes (46 votos). El índice agrupa por código y da
# 305/512; el tablero y este validador agrupan por nombre y dan 259/558.
CONOCIDOS = {(2019, 'concejo', '16-001'): {'HUBERT ARTURO ZAMORA PINEDA', 'MARLENE PUENTES JARAMILLO'}}


def n(s):
    return ' '.join(unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper().split())


def falla(msg):
    FALLAS.append(msg)
    print('  ✗', msg)


def leer_idx(d, corp, año):
    b = open(os.path.join(d, f'index-{corp}-{año}.json'), 'rb').read()
    if b[:2] == b'\x1f\x8b':
        b = gzip.decompress(b)
    return json.loads(b)['candidatos']


def leer_csv(ruta, cors, ciudades=None):
    """{cor: {(dd,mm): {'pue': {pcode: {cat: v}}, 'cand': {pcode: {(nom,can): v}}}}}"""
    C = columnas(ruta)
    out = {}
    with open(ruta, encoding='utf-8', errors='replace', newline='') as f:
        rd = csv.reader(f, delimiter=';'); next(rd, None)
        for row in rd:
            if len(row) < C['_ancho']:
                continue
            cor = row[C['COD_COR']].strip()
            if cor not in cors:
                continue
            dd, mm = row[C['COD_DDE']].strip().zfill(2), row[C['COD_MME']].strip().zfill(3)
            if ciudades is not None and (dd, mm) not in ciudades:
                continue
            try:
                v = int(row[C['NUM_VOT']] or 0)
            except ValueError:
                continue
            if v <= 0:
                continue
            pc = dd + mm + row[C['COD_ZZ']].strip().zfill(2) + row[C['COD_PP']].strip().zfill(2)
            can = row[C['COD_CAN']].strip()
            x = out.setdefault(cor, {}).setdefault((dd, mm), {'pue': {}, 'cand': {}})
            cat = ESP.get(can, 'validos')
            p = x['pue'].setdefault(pc, {})
            p[cat] = p.get(cat, 0) + v
            if cat == 'validos' and can != '0':
                k = (n(row[C['DES_CAN']]), row[C['COD_PAR']].strip(), can)
                c = x['cand'].setdefault(pc, {})
                c[k] = c.get(k, 0) + v
    return out


def suma(dic_por_pc, pcs):
    out = {}
    for pc in pcs:
        for k, v in dic_por_pc.get(pc, {}).items():
            out[k] = out.get(k, 0) + v
    return out


def validar_local(corp, año, crudo, idx):
    print(f'\n══ {corp} {año}')
    res = json.load(open(os.path.join(BD, f'output_{corp}_{año}', f'resultados-{corp}-{año}.json'), encoding='utf-8'))
    idx_por = {}
    for c in idx:
        p = c['slug'].split('-')
        idx_por.setdefault((p[1].zfill(2), p[2].zfill(3)), {}).setdefault(n(c['nombre']), 0)
        idx_por[(p[1].zfill(2), p[2].zfill(3))][n(c['nombre'])] += c['votos']
    for city in res['cities']:
        key = (city['dde'], city['mme'])
        cr = crudo.get(key)
        if not cr:
            falla(f"{city['name']}: sin filas en el CSV"); continue
        # puestos que muestra el tablero = los del detalle por comuna
        incl = set()
        tab_c = {}
        for ruta in glob.glob(os.path.join(BD, f'output_{corp}_{año}', 'comuna', f"{city['dde']}-{city['mme']}-*.json")):
            d = json.load(open(ruta, encoding='utf-8'))
            for p in d['puestos']:
                zz, pp = p['code'].split('-')
                incl.add(city['dde'] + city['mme'] + zz + pp)
        com = res['data'][city['key']]['comunas']
        tab = {'validos': 0, 'blanco': 0, 'nulos': 0}
        for c in com.values():
            for k in tab:
                tab[k] += c[k]
            for nom, _pi, v in c['cands']:
                tab_c[n(nom)] = tab_c.get(n(nom), 0) + v
        csv_in = suma(cr['pue'], incl)
        csv_all = suma(cr['pue'], cr['pue'].keys())
        ok = all(tab[k] == csv_in.get(k, 0) for k in tab)
        fuera = sum(csv_all.values()) - sum(csv_in.values())
        fz = city['fuera_mapa']
        ok2 = fuera == fz['votos_sin_ubicar'] + fz['votos_sin_comuna']
        print(f"  {city['name'][:13]:13} válidos {tab['validos']:>9,} · blanco {tab['blanco']:>7,} · nulos+nm {tab['nulos']:>7,}"
              f" {'= CSV' if ok else '≠ CSV ' + str(csv_in)} · fuera del mapa {fuera:,} {'= declarado' if ok2 else '≠ declarado'}")
        if not ok: falla(f"{corp} {city['name']}: totales ≠ CSV")
        if not ok2: falla(f"{corp} {city['name']}: fuera del mapa {fuera} ≠ {fz}")
        # candidatos: tablero == CSV en puestos del tablero; CSV completo == índice
        cin = {}
        for (nom, _par, _can), v in suma(cr['cand'], incl).items():
            cin[nom] = cin.get(nom, 0) + v
        call = {}
        for (nom, _par, _can), v in suma(cr['cand'], cr['cand'].keys()).items():
            call[nom] = call.get(nom, 0) + v
        malos_tab = [k for k in set(tab_c) | set(cin) if tab_c.get(k, 0) != cin.get(k, 0)]
        ix = idx_por.get(key, {})
        conocidos = CONOCIDOS.get((año, corp, city['key']), set())
        malos_idx = [k for k in set(call) | set(ix) if call.get(k, 0) != ix.get(k, 0) and k not in conocidos]
        print(f"      {len(tab_c):,} candidatos · tablero=CSV(puestos del mapa): {len(malos_tab)} diferencias"
              f" · CSV completo=índice S3: {len(malos_idx)} diferencias")
        if malos_tab: falla(f"{corp} {city['name']}: {len(malos_tab)} candidatos tablero≠CSV, ej {malos_tab[:3]}")
        if malos_idx: falla(f"{corp} {city['name']}: {len(malos_idx)} candidatos CSV≠índice, ej {[(k, call.get(k), ix.get(k)) for k in malos_idx[:3]]}")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('año', type=int)
    ap.add_argument('--indices', required=True)
    a = ap.parse_args()
    año = a.año
    cors = COR[año]
    ter = os.path.join(BD, 'FINAL SUBIDA GCS', f'GCS_{año}TER.csv')
    print('· leyendo', os.path.basename(ter))
    # JAL y Concejo solo si el año ya tiene su tablero por comuna.
    hay = {c: os.path.exists(os.path.join(BD, f'output_{c}_{año}', f'resultados-{c}-{año}.json'))
           for c in ('jal', 'concejo')}
    T = leer_csv(ter, {cors['alcaldia'], cors['asamblea']} | ({cors['concejo']} if hay['concejo'] else set()))
    rc = None
    if hay['jal']:
        print('· leyendo', CSV_JAL[año])
        J = leer_csv(os.path.join(BD, 'FINAL SUBIDA GCS', CSV_JAL[año]), {cors['jal']})
        validar_local('jal', año, J[cors['jal']], leer_idx(a.indices, 'jal', año))
    if hay['concejo']:
        rc = validar_local('concejo', año, T[cors['concejo']], leer_idx(a.indices, 'concejo', año))

    # ── Asamblea por departamento
    print(f'\n══ asamblea {año}')
    A = T[cors['asamblea']]
    idx = leer_idx(a.indices, 'asamblea', año)
    ix = {}
    for c in idx:
        dd = c['slug'].split('-')[1].zfill(2)
        ix.setdefault(dd, {})[n(c['nombre'])] = ix.setdefault(dd, {}).get(n(c['nombre']), 0) + c['votos']
    malos = 0
    for ruta in sorted(glob.glob(os.path.join(BD, f'output_asamblea_{año}', 'dep', '*.json'))):
        d = json.load(open(ruta, encoding='utf-8'))
        dd = d['key']
        tab = {'validos': 0, 'blanco': 0, 'nulos': 0}; tc = {}
        for m in d['comunas'].values():
            for k in tab: tab[k] += m[k]
            for nom, _p, v in m['cands']: tc[n(nom)] = tc.get(n(nom), 0) + v
        csvd = {}
        for (d2, _m), x in A.items():
            if d2 != dd: continue
            for pc, cats in x['pue'].items():
                for k, v in cats.items(): csvd[k] = csvd.get(k, 0) + v
        if any(tab[k] != csvd.get(k, 0) for k in tab):
            falla(f'asamblea {dd}: {tab} ≠ CSV {csvd}'); malos += 1
        bad = [k for k in set(tc) | set(ix.get(dd, {})) if tc.get(k, 0) != ix.get(dd, {}).get(k, 0)]
        if bad:
            falla(f'asamblea {dd}: {len(bad)} candidatos ≠ índice, ej {[(k, tc.get(k), ix[dd].get(k)) for k in bad[:3]]}'); malos += 1
    print(f'  {len(glob.glob(os.path.join(BD, f"output_asamblea_{año}", "dep", "*.json")))} departamentos · {malos} con diferencias')

    # ── Alcaldía por municipio
    print(f'\n══ alcaldía {año}')
    L = T[cors['alcaldia']]
    idx = leer_idx(a.indices, 'alcaldia', año)
    ix = {}
    for c in idx:
        p = c['slug'].split('-')
        ix[(p[1].zfill(2), p[2].zfill(3), p[4])] = c['votos']
    malos = munis = 0
    for ruta in sorted(glob.glob(os.path.join(BD, f'output_alcaldias_{año}', 'departamentos', '*', 'municipios.json'))):
        dd = os.path.basename(os.path.dirname(ruta))
        for m in json.load(open(ruta, encoding='utf-8')):
            munis += 1
            tab = {(dd, m['mun'], c['cod']): c['votos'] for c in m['candidatos']}
            idm = {k: v for k, v in ix.items() if k[0] == dd and k[1] == m['mun']}
            csvm = {}
            for cats in L.get((dd, m['mun']), {'pue': {}})['pue'].values():
                for k, v in cats.items(): csvm[k] = csvm.get(k, 0) + v
            esp = m['especiales']
            ok = (tab == idm and m['votos_validos'] == csvm.get('validos', 0)
                  and esp.get('blanco', 0) == csvm.get('blanco', 0)
                  and esp.get('nulos', 0) + esp.get('no_marcados', 0) == csvm.get('nulos', 0))
            if not ok:
                malos += 1
                if malos <= 3: falla(f"alcaldía {dd}-{m['mun']} {m['nombre']}: tablero≠índice/CSV")
    print(f'  {munis} municipios · {malos} con diferencias')

    # ── Controles fijos
    print(f'\n══ controles {año}')
    alc_nom, alc_v, dep_asam, diputado = CONTROLES[año]
    bog = [m for m in json.load(open(os.path.join(BD, f'output_alcaldias_{año}', 'departamentos', '16', 'municipios.json'))) if m['mun'] == '001'][0]
    top = bog['candidatos'][0]
    print(f"  Alcaldía Bogotá: {top['nombre']} {top['votos']:,}")
    if not (alc_nom in top['nombre'] and top['votos'] == alc_v): falla(f'alcalde de Bogotá ≠ {alc_nom} {alc_v:,}')
    tc = {}
    for c in (rc['data']['16-001']['comunas'].values() if rc else []):
        for nom, _p, v in c['cands']: tc[nom] = tc.get(nom, 0) + v
    # El tablero no cuenta Corferias y cárceles (sin comuna), así que el control es
    # de ORDEN: mismo top 3 que el índice, con Abisambra y Cancino adentro.
    t3 = [nom for nom, _ in sorted(tc.items(), key=lambda kv: -kv[1])[:3]]
    ixb = [] if not rc else sorted((c for c in leer_idx(a.indices, 'concejo', año) if c['slug'].startswith(f'CONC{año}-16-1-')),
                 key=lambda c: -c['votos'])[:3]
    print(f"  Concejo Bogotá top 3 · tablero: {t3}")
    print(f"                        índice:  {[(c['nombre'], c['votos']) for c in ixb]}")
    if rc and (t3 != [n(c['nombre']) for c in ixb] or (año == 2019 and not ({'ABISAMBRA', 'CANCINO'} <= {w for nom in t3 for w in nom.split()}))):
        falla('top 3 Concejo Bogotá: tablero ≠ índice (o, en 2019, sin Abisambra/Cancino)')
    d = json.load(open(os.path.join(BD, f'output_asamblea_{año}', 'dep', f'{dep_asam}.json'), encoding='utf-8'))
    tv = {}
    for m in d['comunas'].values():
        for nom, _p, v in m['cands']: tv[nom] = tv.get(nom, 0) + v
    t1 = max(tv.items(), key=lambda kv: kv[1])
    print(f"  Asamblea {dep_asam} top (tablero): {t1}")
    if diputado not in t1[0]: falla(f'top Asamblea {dep_asam} no es {diputado}')

    print(f'\n{"✓ TODO CUADRA" if not FALLAS else f"✗ {len(FALLAS)} fallas"}')
    sys.exit(1 if FALLAS else 0)


if __name__ == '__main__':
    main()
