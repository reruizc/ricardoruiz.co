#!/usr/bin/env python3
"""Escrutinio del Senado 2014 · 2018 · 2022 desde el GCS, en el MISMO formato que lee senado-2026.html.

  python3 tools/build-congreso-escr/build.py senado 2022 [2018 2014]

Entrada: Bases de datos/FINAL SUBIDA GCS/GCS_<año>CON.csv (escrutinio, mesa a mesa).
Salida:  Bases de datos/output_congreso_escr/senado-<año>/
           resumen.json · circunscripciones.json · departamentos.json · censo.csv
           departamentos/<dep>/{municipios,comunas,puestos,mesas}.json
         → s3://…/congreso-2026/output/senado-<año>/   (la página es senado-<año>.html)

Formato: cada nivel trae votval (votos por listas) · votblan · votnul · votnma · votant ·
partidos {partido: votos} · candidatos {partido: [{nombre, votos, codigo}]} y
por_circunscripcion {NACIONAL|INDIGENAS: ídem}. El voto por la lista (COD_CAN 0) suma al
partido y no aparece como candidato. El de 2026 lo generó otro script, que no está en el repo:
este lo reproduce campo por campo (comparado contra congreso-2026/output/senado/).

⚠ Los códigos de circunscripción CAMBIAN por año: 2014 y 2018 Senado nacional = 0 e indígena = 4;
  2022 nacional = 1 e indígena = 6.
⚠ Especiales: solo 996 (blanco), 997 (nulos), 998 (no marcados). Los COD_CAN 96-99 son candidatos
  reales en las listas largas del Senado.
⚠ En 2014 y 2018 los nulos y no marcados vienen solo en la circunscripción nacional (es un único
  tarjetón); la indígena trae solo el blanco.
⚠ Comuna: el GCS no la trae. Solo se asigna donde la zona electoral la define sin ambigüedad:
  Bogotá (zona = localidad) y Medellín (tabla fija zona → comuna, estable 2015-2026). En el resto
  va «SIN COMUNA»: asignarla por la zonificación de 2026 la cambiaría en ciudades rezonificadas.
⚠ Nombre de puesto: Divipol 2021 primero (es de la época) y el georreferenciado de 2026 solo de
  respaldo; lo que ninguno nombra lleva un rótulo entre corchetes derivado del código.
"""
import csv
import importlib.util
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BD = RAIZ / 'Bases de datos'
GCS = BD / 'FINAL SUBIDA GCS'
OUT = BD / 'output_congreso_escr'
TMP = OUT / '_tmp'

# nombres y rótulos: los mismos del CSV de descargas
_spec = importlib.util.spec_from_file_location('csvnames', RAIZ / 'tools' / 'build-csv-names' / 'build.py')
csvnames = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(csvnames)

CFG = {
    'senado': {
        '2022': {'NACIONAL': '1', 'INDIGENAS': '6'},
        '2018': {'NACIONAL': '0', 'INDIGENAS': '4'},
        '2014': {'NACIONAL': '0', 'INDIGENAS': '4'},
    },
}
CIRC_META = {'NACIONAL': {'codigo': '0', 'curules': 100, 'umbral_pct': 0.03},
             'INDIGENAS': {'codigo': '4', 'curules': 2, 'umbral_pct': 0.0}}
ESP = {'996': 'votblan', '997': 'votnul', '998': 'votnma', '999': 'votnma'}
# Listas cerradas que el GCS no trae con nombres (sin catálogo). Fuente: «Elecciones legislativas de
# Colombia de <año>», Wikipedia en español, sección «Senadores electos» (consultada el 8-oct-2026).
# CJL 2018: su votación en ese artículo (463.521) coincide al voto con el GCS.
LISTAS_MANUALES = {
    ('2018', 'G.S.C. COLOMBIA JUSTA LIBRES'): [
        'JHON MILTON RODRIGUEZ GONZALEZ', 'EDUARDO EMILIO PACHECO CUELLO', 'EDGAR ENRIQUE PALACIO MIZRAHI'],
    ('2014', 'CENTRO DEMOCRÁTICO MANO FIRME CORAZÓN GRANDE'): [
        'ALVARO URIBE VELEZ', 'MARIA DEL ROSARIO GUERRA DE LA ESPRIELLA', 'PALOMA SUSANA VALENCIA LASERNA',
        'ANA MERCEDES GOMEZ MARTINEZ', 'SUSANA CORREA BORRERO', 'ALFREDO RANGEL SUAREZ', 'IVAN DUQUE MARQUEZ',
        'FERNANDO NICOLAS ARAUJO RUMIE', 'JOSE OBDULIO GAVIRIA VELEZ', 'ORLANDO CASTAÑEDA SERRANO',
        'DANIEL ALBERTO CABRALES CASTILLO', 'EVERTH BUSTAMANTE GARCIA', 'ALFREDO RAMOS MAYA',
        'JAIME ALEJANDRO AMIN HERNANDEZ', 'ERNESTO MACIAS TOVAR', 'RUBY THANIA VEGA DE PLAZA',
        'CARLOS FELIPE MEJIA MEJIA', 'PAOLA ANDREA HOLGUIN MORENO', 'NOHORA STELLA TOVAR REY',
        'HONORIO MIGUEL HENRIQUEZ PINEDO'],
}
FECHA = {'2022': '13 de marzo de 2022', '2018': '11 de marzo de 2018', '2014': '9 de marzo de 2014'}

# nombres de departamento iguales a los de 2026 (la página los casa con el GeoJSON)
DEP_NOM = {'60': 'AMAZONAS', '01': 'ANTIOQUIA', '40': 'ARAUCA', '03': 'ATLANTICO', '16': 'BOGOTA D.C.',
           '05': 'BOLIVAR', '07': 'BOYACA', '09': 'CALDAS', '44': 'CAQUETA', '46': 'CASANARE', '11': 'CAUCA',
           '12': 'CESAR', '17': 'CHOCO', '88': 'CONSULADOS', '13': 'CORDOBA', '15': 'CUNDINAMARCA',
           '50': 'GUAINIA', '54': 'GUAVIARE', '19': 'HUILA', '48': 'LA GUAJIRA', '21': 'MAGDALENA', '52': 'META',
           '23': 'NARIÑO', '25': 'NORTE DE SAN', '64': 'PUTUMAYO', '26': 'QUINDIO', '24': 'RISARALDA',
           '56': 'SAN ANDRES', '27': 'SANTANDER', '28': 'SUCRE', '29': 'TOLIMA', '31': 'VALLE', '68': 'VAUPES',
           '72': 'VICHADA'}

# Comunas (ver aviso arriba). Nombres tal como los escribe el escrutinio de 2026.
BOG_LOC = ['USAQUEN', 'CHAPINERO', 'SANTA FE', 'SAN CRISTOBAL', 'USME', 'TUNJUELITO', 'BOSA', 'KENNEDY',
           'FONTIBON', 'ENGATIVA', 'SUBA', 'BARRIOS UNIDOS', 'TEUSAQUILLO', 'MARTIRES', 'ANTONIO NARIÑO',
           'PUENTE ARANDA', 'CANDELARIA', 'RAFAEL URIBE URIB', 'CIUDAD BOLIVAR', 'SUMAPAZ']
MDE_COM = ['POPULAR', 'SANTA CRUZ', 'MANRIQUE', 'ARANJUEZ', 'CASTILLA', 'DOCE DE OCTUBRE', 'ROBLEDO',
           'VILLA HERMOSA', 'BUENOS AIRES', 'LA CANDELARIA', 'LAURELES', 'LA AMERICA', 'SAN JAVIER',
           'EL POBLADO', 'GUAYABAL', 'BELEN']
MDE_ZONA = {}
for z in range(1, 33):
    MDE_ZONA[f'{z:02d}'] = 15 if z == 29 else (16 if z >= 30 else (z + 1) // 2)


def comuna(dep, mun, zona):
    if dep == '16' and mun == '001' and zona.isdigit() and 1 <= int(zona) <= 20:
        return f'{int(zona):03d}', f'LOCALIDAD {int(zona)} {BOG_LOC[int(zona) - 1]}'
    if dep == '01' and mun == '001' and zona in MDE_ZONA:
        c = MDE_ZONA[zona]
        return f'{c:03d}', f'COMUNA {c} {MDE_COM[c - 1]}'
    return '000', 'SIN COMUNA'


def cargar_nombres():
    div = json.loads(csvnames.DIVIPOLA.read_text(encoding='utf-8'))
    mun_nom = {}
    for d in div['deptos']:
        for m in d.get('muns', []):
            mun_nom[f"{d['cod'].zfill(2)}-{m['cod'].zfill(3)}"] = m['nombre'].upper()
    for k, v in csvnames.MUN_HISTORICOS.items():
        mun_nom.setdefault(k, v.upper())
    pue = {}
    with csvnames.GEOREF.open(encoding='utf-8-sig', newline='') as f:            # respaldo: 2026
        for row in csv.DictReader(f, delimiter=';'):
            c, n = (row.get('CÓDIGO COMPLETO') or '').strip(), (row.get('NOMBRE PUESTO') or '').strip()
            if c and n:
                pue[c.zfill(9)] = n
    import openpyxl                                                                # primario: 2021
    wb = openpyxl.load_workbook(csvnames.DIVIPOL21, read_only=True)
    for i, r in enumerate(wb.active.iter_rows(values_only=True), 1):
        if i <= 5 or r[0] is None or r[6] is None:
            continue
        pue[str(r[0]).zfill(2) + str(r[1]).zfill(3) + str(r[2]).zfill(2) + str(r[3]).zfill(2)] = str(r[6]).strip()
    wb.close()
    return mun_nom, pue


# ─── acumuladores ────────────────────────────────────────────────────────────
def nuevo():
    return {}


def sumar(acc, circ, par, can, v):
    c = acc.get(circ)
    if c is None:
        c = acc[circ] = {'p': {}, 'e': {}}
    if can in ESP:
        c['e'][ESP[can]] = c['e'].get(ESP[can], 0) + v
    else:
        p = c['p'].get(par)
        if p is None:
            p = c['p'][par] = {}
        p[can] = p.get(can, 0) + v


def dhondt(votos, curules, umbral):
    ok = {p: v for p, v in votos.items() if v >= umbral and v > 0}
    if not ok:
        return {}, 0
    cocs = sorted(((v / d, p) for p, v in ok.items() for d in range(1, curules + 1)), reverse=True)[:curules]
    cur = defaultdict(int)
    for _, p in cocs:
        cur[p] += 1
    return dict(cur), round(cocs[-1][0])


def nodo_circ(c, nom_par, nom_can, con_cifra, circ):
    partidos, candidatos = {}, {}
    for par, cands in c['p'].items():
        n = nom_par[(circ, par)]
        partidos[n] = partidos.get(n, 0) + sum(cands.values())
        lista = [{'nombre': nom_can[(circ, par, k)], 'votos': v, 'codigo': k.zfill(3)}
                 for k, v in cands.items() if k != '0' and v > 0]
        if lista:
            candidatos.setdefault(n, []).extend(lista)
    partidos = dict(sorted(partidos.items(), key=lambda x: -x[1]))
    candidatos = {p: sorted(l, key=lambda x: -x['votos']) for p, l in
                  sorted(candidatos.items(), key=lambda x: -partidos.get(x[0], 0))}
    e = c['e']
    votval = sum(partidos.values())
    out = {'votval': votval, 'votblan': e.get('votblan', 0), 'votnul': e.get('votnul', 0),
           'votnma': e.get('votnma', 0)}
    out['votant'] = votval + out['votblan'] + out['votnul'] + out['votnma']
    if con_cifra:
        meta = CIRC_META[circ]
        umbral = round(meta['umbral_pct'] * (votval + out['votblan']))
        _, cifra = dhondt(partidos, meta['curules'], umbral)
        out['cifra'], out['umbral'] = cifra, umbral
    else:
        out['cifra'] = out['umbral'] = 0
    out['partidos'], out['candidatos'] = partidos, candidatos
    return out


def nodo(acc, nom_par, nom_can, con_cifra=False, **ident):
    pc = {circ: nodo_circ(acc[circ], nom_par, nom_can, con_cifra, circ) for circ in ('NACIONAL', 'INDIGENAS') if circ in acc}
    root = dict(ident)
    for k in ('votval', 'votblan', 'votnul', 'votnma', 'votant'):
        root[k] = sum(x[k] for x in pc.values())
    root['cifra'] = root['umbral'] = 0
    partidos, candidatos = {}, {}
    for x in pc.values():
        for p, v in x['partidos'].items():
            partidos[p] = partidos.get(p, 0) + v
        for p, l in x['candidatos'].items():
            candidatos.setdefault(p, []).extend(l)
    root['partidos'] = dict(sorted(partidos.items(), key=lambda x: -x[1]))
    root['candidatos'] = {p: sorted(l, key=lambda x: -x['votos']) for p, l in candidatos.items()}
    root['por_circunscripcion'] = pc
    return root


def escribe(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(',', ':')))


# ─── Senado ──────────────────────────────────────────────────────────────────
def senado(anio, mun_nom, pue_nom):
    t0 = time.time()
    cir = {v: k for k, v in CFG['senado'][anio].items()}
    out = OUT / f'senado-{anio}'
    tmp = TMP / f'senado-{anio}'
    tmp.mkdir(parents=True, exist_ok=True)
    for f in tmp.glob('*.tsv'):
        f.unlink()
    nom_par, nom_can, cod_par, catalogo = {}, {}, {}, {}
    # 1 · partir por departamento (la memoria queda acotada a uno)
    fhs = {}
    with open(GCS / f'GCS_{anio}CON.csv', encoding='utf-8-sig', newline='') as fh:
        rd = csv.reader(fh, delimiter=';')
        next(rd)
        for r in rd:
            if r[2] != '1' or r[4] not in cir:
                continue
            circ = cir[r[4]]
            dep = r[6].zfill(2)
            par, can = r[11], r[13]
            nom_par.setdefault((circ, par), r[12].strip())
            cod_par.setdefault((circ, par), par.zfill(4))
            if can not in ESP:
                nom_can.setdefault((circ, par, can), r[14].strip())
            if dep == '00':          # catálogo sin territorio, todo en 0: solo sirve para los nombres
                if can not in ESP and can != '0':
                    catalogo.setdefault((circ, par), {})[int(can)] = r[14].strip()
                continue
            w = fhs.get(dep)
            if w is None:
                w = fhs[dep] = open(tmp / f'{dep}.tsv', 'w')
            w.write('\t'.join((r[7].zfill(3), r[8].zfill(2), r[9].zfill(2), r[10].zfill(3), circ, par, can, r[15])) + '\n')
    for w in fhs.values():
        w.close()
    print(f'  senado {anio}: partido en {len(fhs)} departamentos ({time.time() - t0:.0f} s)')

    nac = nuevo()
    deps = []
    censo = censo_por_puesto(anio)
    for dep in sorted(fhs):
        acc_dep = nuevo()
        muns, coms, pues, mesas = {}, {}, {}, {}
        with open(tmp / f'{dep}.tsv') as f:
            for line in f:
                mun, zona, pue, mesa, circ, par, can, v = line.rstrip('\n').split('\t')
                v = int(v)
                com = comuna(dep, mun, zona)[0]
                for acc in (nac, acc_dep, muns.setdefault(mun, {}), coms.setdefault((mun, com), {}),
                            pues.setdefault((mun, zona, pue), {}), mesas.setdefault((mun, zona, pue, mesa), {})):
                    sumar(acc, circ, par, can, v)
        dn = DEP_NOM.get(dep, dep)

        def mn(m):
            return mun_nom.get(f'{dep}-{m}') or f'MUNICIPIO {m}'

        def pn(m, z, p):
            return pue_nom.get(dep + m + z + p) or csvnames.rotulo_puesto(dep, m, z, p, dn, mn(m))

        base = {'dep_cod': dep, 'dep_nom': dn}
        L_mun = [nodo(a, nom_par, nom_can, True, **base, cod=m, nombre=mn(m)) for m, a in sorted(muns.items())]
        L_com = []
        com_nom = {}
        for (m, z, _p) in pues:
            c, cn = comuna(dep, m, z)
            com_nom[(m, c)] = cn
        for (m, c), a in sorted(coms.items()):
            cn = com_nom[(m, c)]
            L_com.append(nodo(a, nom_par, nom_can, **base, mun_cod=m, mun_nom=mn(m), cod=c, nombre=cn, com_cod=c, com_nom=cn))
        L_pue = []
        for (m, z, p), a in sorted(pues.items()):
            c, cn = comuna(dep, m, z)
            pc = f'{c}-{z}-{p}'
            L_pue.append(nodo(a, nom_par, nom_can, **base, mun_cod=m, mun_nom=mn(m), com_cod=c, com_nom=cn,
                              zon_cod=z, cod=pc, pue_cod=pc, pue_cod_raw=p, nombre=pn(m, z, p)))
        L_mes = []
        for (m, z, p, me), a in sorted(mesas.items()):
            c, cn = comuna(dep, m, z)
            pc = f'{c}-{z}-{p}'
            L_mes.append(nodo(a, nom_par, nom_can, **base, mun_cod=m, mun_nom=mn(m), com_cod=c, com_nom=cn,
                              zon_cod=z, pue_cod=pc, pue_cod_raw=p, pue_nom=pn(m, z, p), mesa=me))
        d = out / 'departamentos' / dep
        escribe(d / 'municipios.json', L_mun)
        escribe(d / 'comunas.json', L_com)
        escribe(d / 'puestos.json', L_pue)
        escribe(d / 'mesas.json', L_mes)
        deps.append(nodo(acc_dep, nom_par, nom_can, True, cod=dep, nombre=dn))
    escribe(out / 'departamentos.json', sorted(deps, key=lambda x: x['nombre']))

    # nacional: curules por cifra repartidora sobre los válidos con blanco
    resumen_circ, partidos_lista, circ_json = {}, [], {}
    for circ in ('NACIONAL', 'INDIGENAS'):
        x = nodo_circ(nac[circ], nom_par, nom_can, True, circ)
        meta = CIRC_META[circ]
        cur, cifra = dhondt(x['partidos'], meta['curules'], x['umbral'])
        resumen_circ[circ] = {'codigo': meta['codigo'], 'nombre': circ, 'curules': meta['curules'],
                              **{k: x[k] for k in ('votval', 'votblan', 'votnul', 'votnma', 'votant')},
                              'cifra': cifra, 'umbral': x['umbral'], 'validos_con_blanco': x['votval'] + x['votblan']}
        n2c = {nom_par[k]: v for k, v in cod_par.items() if k[0] == circ}
        for p, v in x['partidos'].items():
            partidos_lista.append({'partido': p, 'codigo': n2c.get(p, ''), 'votos': v, 'curules': cur.get(p, 0),
                                   'candidatos': x['candidatos'].get(p, [])})
        circ_json[circ] = {'codigo': meta['codigo'], 'nombre': circ, 'curules': meta['curules'],
                           'umbral_pct': meta['umbral_pct'],
                           'partidos': [{'partido': p, 'codigo': n2c.get(p, '')} for p in x['partidos']]}
    n = resumen_circ['NACIONAL']
    resumen = {'corporacion': 'SENADO', 'generado_en': datetime.now(timezone.utc).isoformat(),
               **{k: n[k] for k in ('votval', 'votblan', 'votnul', 'votnma', 'votant', 'cifra', 'umbral')},
               'partidos': partidos_lista, 'por_circunscripcion': resumen_circ,
               'validos_con_blanco': n['validos_con_blanco'],
               'fuente_nacional': f'Registraduría · consolidado del escrutinio (GCS) · elecciones del {FECHA[anio]}',
               'nota_territorial': 'Departamento, municipio, puesto y mesa: el mismo consolidado del escrutinio.'}
    escribe(out / 'resumen.json', resumen)
    # listas cerradas con curul: el orden de la lista es el COD_CAN del catálogo (dep 00); si el GCS no
    # trae el catálogo de esa lista, se usa LISTAS_MANUALES (fuente anotada al lado de cada una)
    cerradas = {}
    for p in partidos_lista:
        if p['curules'] and not p['candidatos']:
            k = next((k for k in catalogo if nom_par[k] == p['partido']), None)
            nombres = [catalogo[k][c] for c in sorted(catalogo[k])] if k else LISTAS_MANUALES.get((anio, p['partido']))
            if not nombres:
                raise SystemExit(f"falta la lista cerrada de {p['partido']} ({anio})")
            cerradas[p['partido']] = nombres
    escribe(out / 'listas_cerradas.json', cerradas)
    escribe(out / 'circunscripciones.json', circ_json)
    # sin censo (2014) el archivo va solo con el encabezado: la página pasa sola a «% de válidos»
    with open(out / 'censo.csv', 'w', newline='') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['dd', 'mm', 'zz', 'pp', 'mujeres', 'hombres', 'total'])
        w.writerows(censo)
    for f in tmp.glob('*.tsv'):
        f.unlink()
    print(f'  senado {anio}: listo en {time.time() - t0:.0f} s · válidos con blanco {n["validos_con_blanco"]:,} '
          f'· umbral {n["umbral"]:,} · cifra {n["cifra"]:,}')
    for p in partidos_lista:
        if p['curules']:
            print(f"     {p['curules']:3d}  {p['partido']}")


def censo_por_puesto(anio):
    """Censo de ESA elección por puesto (2018 y 2022); 2014 no tiene → la página muestra % de válidos."""
    f = BD / 'censos-registraduria' / f'{anio}_datos_censo-electoral-min.json'
    if not f.exists():
        return []
    d = json.load(open(f))
    filas = []
    for r in next(iter(d.values())):
        if r['tipo_eleccion'] != 'CONGRESO DE LA REPÚBLICA':
            continue
        filas.append([r['cod_depto'].zfill(2), r['cod_mun'].zfill(3), r['zona'].zfill(2), r['cod_puesto'].zfill(2),
                      r['sexo']['mujeres'], r['sexo']['hombres'], r['potencial_electoral']])
    return filas


def main():
    corp, anios = sys.argv[1], sys.argv[2:]
    if corp != 'senado':
        raise SystemExit('por ahora: senado')
    mun_nom, pue_nom = cargar_nombres()
    for a in anios:
        senado(a, mun_nom, pue_nom)


if __name__ == '__main__':
    main()
