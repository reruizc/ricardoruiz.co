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
CFG['camara'] = {
    '2022': {'2': 'TERRITORIAL', '0': 'TERRITORIAL', '6': 'INDIGENAS', '5': 'AFRO-DESCENDIENTES'},   # 0 = Internacional
    '2018': {'1': 'TERRITORIAL', '4': 'INDIGENAS', '5': 'AFRO-DESCENDIENTES'},
    '2014': {'1': 'TERRITORIAL', '4': 'INDIGENAS', '5': 'AFRO-DESCENDIENTES'},
}
CAM_CIRCS = ('TERRITORIAL', 'INDIGENAS', 'AFRO-DESCENDIENTES')
# Curules territoriales por departamento (igual 2014-2026, salvo el exterior: 2 hasta 2014, 1 desde 2018)
CUR_DEP = {'60': 2, '01': 17, '40': 2, '03': 7, '16': 18, '05': 6, '07': 6, '09': 5, '44': 2, '46': 2, '11': 4,
           '12': 4, '17': 2, '88': 1, '13': 5, '15': 7, '50': 2, '54': 2, '19': 4, '48': 2, '21': 5, '52': 3,
           '23': 5, '25': 5, '64': 2, '26': 3, '24': 4, '56': 2, '27': 7, '28': 3, '29': 6, '31': 13, '68': 2,
           '72': 2}
CUR_ESP = {'INDIGENAS': 1, 'AFRO-DESCENDIENTES': 2}
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
# Elegidos de listas cerradas de Cámara por (año, departamento, partido), en orden de lista.
# Se llena desde camara_listas_cerradas.json (fuente anotada en ese archivo).
_LC = Path(__file__).with_name('camara_listas_cerradas.json')
_LCJ = json.loads(_LC.read_text()) if _LC.exists() else {}
LISTAS_CAMARA = {tuple(k.split('|')): v for k, v in _LCJ.get('listas', {}).items()}
LISTAS_AFRO = {tuple(k.split('|', 1)): v for k, v in _LCJ.get('afro', {}).items()}
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
    if con_cifra is None:          # Cámara: sus nodos no llevan cifra ni umbral
        pass
    elif con_cifra:
        meta = CIRC_META[circ]
        umbral = round(meta['umbral_pct'] * (votval + out['votblan']))
        _, cifra = dhondt(partidos, meta['curules'], umbral)
        out['cifra'], out['umbral'] = cifra, umbral
    else:
        out['cifra'] = out['umbral'] = 0
    out['partidos'], out['candidatos'] = partidos, candidatos
    return out


def nodo(acc, nom_par, nom_can, con_cifra=False, circs=('NACIONAL', 'INDIGENAS'), **ident):
    pc = {circ: nodo_circ(acc[circ], nom_par, nom_can, con_cifra, circ) for circ in circs if circ in acc}
    root = dict(ident)
    for k in ('votval', 'votblan', 'votnul', 'votnma', 'votant'):
        root[k] = sum(x[k] for x in pc.values())
    if con_cifra is not None:
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


# ─── Cámara ──────────────────────────────────────────────────────────────────
def curules_camara(partidos, blancos, s):
    """Art. 263: 1 curul → mayoría · 2 → cuociente con umbral del 30 % · 3+ → cifra repartidora con umbral
    del 50 % del cuociente. El cuociente va sobre los válidos (listas + blanco)."""
    vot = {p: v for p, v in partidos.items() if v > 0}
    if not vot:
        return {}
    if s == 1:
        return {max(vot, key=vot.get): 1}
    q = (sum(vot.values()) + blancos) / s
    if s == 2:
        el = {p: v for p, v in vot.items() if v >= 0.3 * q}
        cur = {p: int(v // q) for p, v in el.items()}
        orden = sorted(el, key=lambda p: -(el[p] - cur[p] * q))
        for i in range(s - sum(cur.values())):     # si solo una lista pasa el umbral, se queda con las dos
            cur[orden[i % len(orden)]] += 1
        return {p: n for p, n in cur.items() if n}
    cur, _ = dhondt({p: v for p, v in vot.items() if v >= 0.5 * q}, s, 0)
    return cur


def curules_afro(partidos, blancos, anio):
    """Afro (2 curules). 2014: umbral del 30 % (FUNECO, única lista que lo pasó, se quedó con las dos).
    2018-2026: cuociente y mayor residuo sin umbral (así salen las declaratorias). Igual que la página."""
    if anio == '2014':
        return curules_camara(partidos, blancos, 2)
    vot = {p: v for p, v in partidos.items() if v > 0}
    if not vot:
        return {}
    q = (sum(vot.values()) + blancos) / 2
    cur = {p: int(v // q) for p, v in vot.items()}
    for p in sorted(vot, key=lambda p: -(vot[p] - cur[p] * q))[:max(0, 2 - sum(cur.values()))]:
        cur[p] += 1
    return {p: n for p, n in cur.items() if n}


def slim(nodo_):
    return {k: v for k, v in nodo_.items() if k not in ('candidatos', 'por_circunscripcion', 'puestos', 'mesas')}


def camara(anio, mun_nom, pue_nom):
    t0 = time.time()
    cir = CFG['camara'][anio]
    out = OUT / f'camara-{anio}'
    tmp = TMP / f'camara-{anio}'
    tmp.mkdir(parents=True, exist_ok=True)
    for f in tmp.glob('*.tsv'):
        f.unlink()
    nom_par, nom_can, cod_par, catalogo = defaultdict(dict), defaultdict(dict), {}, {}
    fhs = {}
    with open(GCS / f'GCS_{anio}CON.csv', encoding='utf-8-sig', newline='') as fh:
        rd = csv.reader(fh, delimiter=';')
        next(rd)
        for r in rd:
            if r[2] != '2' or r[4] not in cir:
                continue
            circ = cir[r[4]]
            dep = '88' if (anio == '2022' and r[4] == '0' and r[6] != '0') else r[6].zfill(2)
            par, can = r[11], r[13]
            if dep == '00':            # catálogo sin territorio (solo algunas listas, solo 2022)
                if can not in ESP and can != '0':
                    catalogo.setdefault((circ, r[12].strip()), {})[int(can)] = r[14].strip()
                continue
            nom_par[dep].setdefault((circ, par), r[12].strip())
            cod_par[(dep, circ, r[12].strip())] = par.zfill(4)
            if can not in ESP:
                nom_can[dep].setdefault((circ, par, can), r[14].strip())
            w = fhs.get(dep)
            if w is None:
                w = fhs[dep] = open(tmp / f'{dep}.tsv', 'w')
            w.write('\t'.join((r[7].zfill(3), r[8].zfill(2), r[9].zfill(2), r[10].zfill(3), circ, par, can, r[15])) + '\n')
    for w in fhs.values():
        w.close()
    print(f'  camara {anio}: partido en {len(fhs)} departamentos ({time.time() - t0:.0f} s)')

    dep_entries, nac_circ = [], {c: {'votval': 0, 'votblan': 0, 'votnul': 0, 'votnma': 0, 'votant': 0} for c in CAM_CIRCS}
    nac_part, nac_cand, especial = {}, defaultdict(list), {c: defaultdict(int) for c in ('INDIGENAS', 'AFRO-DESCENDIENTES')}
    especial_cand, cerradas, pendientes = {c: defaultdict(list) for c in especial}, {'territorial': {}}, []
    especial_blan = {c: 0 for c in especial}
    esp_cand = defaultdict(lambda: defaultdict(int))
    for dep in sorted(fhs):
        NP, NC = nom_par[dep], nom_can[dep]
        acc_dep, muns, coms, pues, mesas = {}, {}, {}, {}, {}
        with open(tmp / f'{dep}.tsv') as f:
            for line in f:
                mun, zona, pue, mesa, circ, par, can, v = line.rstrip('\n').split('\t')
                v = int(v)
                com = comuna(dep, mun, zona)[0]
                for acc in (acc_dep, muns.setdefault(mun, {}), coms.setdefault((mun, com), {}),
                            pues.setdefault((mun, com, zona, pue), {}), mesas.setdefault((mun, com, zona, pue, mesa), {})):
                    sumar(acc, circ, par, can, v)
        dn = DEP_NOM.get(dep, dep)

        def mn(m):
            return mun_nom.get(f'{dep}-{m}') or f'MUNICIPIO {m}'

        def pn(m, z, p):
            return pue_nom.get(dep + m + z + p) or csvnames.rotulo_puesto(dep, m, z, p, dn, mn(m))

        def N(a, **ident):
            return nodo(a, NP, NC, None, CAM_CIRCS, **ident)

        base = {'dep_cod': dep, 'dep_nom': dn}
        com_nom = {(m, comuna(dep, m, z)[0]): comuna(dep, m, z)[1] for (m, _c, z, _p) in pues}
        L_mun = []
        (out / f'dep-{dep}').mkdir(parents=True, exist_ok=True)
        # índices hijo por padre: recorrer todas las mesas por cada puesto era cuadrático (Bogotá: 15 min)
        pues_por_com, mesas_por_pue = defaultdict(list), defaultdict(list)
        for k in sorted(pues):
            pues_por_com[k[:2]].append(k)
        for k in sorted(mesas):
            mesas_por_pue[k[:4]].append(k)
        for m, am in sorted(muns.items()):
            nm = N(am, **base, cod=m, nombre=mn(m))
            nm['comunas'] = []
            for (mm, c), ac in sorted(coms.items()):
                if mm != m:
                    continue
                cn = com_nom[(m, c)]
                ident_c = dict(**base, mun_cod=m, mun_nom=mn(m), cod=c, nombre=cn, com_cod=c, com_nom=cn)
                nc = N(ac, **ident_c)
                nc['puestos'] = []
                nav = slim(nc)
                nav['puestos'] = []
                for (m2, c2, z, p) in pues_por_com[(m, c)]:
                    ap = pues[(m2, c2, z, p)]
                    pc = f'{c}-{z}-{p}'
                    ident_p = dict(**base, mun_cod=m, mun_nom=mn(m), com_cod=c, com_nom=cn, zon_cod=z, cod=pc,
                                   pue_cod=pc, pue_cod_raw=p, nombre=pn(m, z, p))
                    np_ = N(ap, **ident_p)
                    np_['mesas'] = [N(amz, **base, mun_cod=m, mun_nom=mn(m), com_cod=c, com_nom=cn, zon_cod=z,
                                      cod=me, nombre=f'Mesa {me}', mesa=me, pue_cod=pc, pue_cod_raw=p, pue_nom=pn(m, z, p))
                                    for (m3, c3, z3, p3, me) in mesas_por_pue[(m, c, z, p)] for amz in (mesas[(m3, c3, z3, p3, me)],)]
                    nc['puestos'].append(np_)
                    nav['puestos'].append(slim(np_))
                escribe(out / f'dep-{dep}' / f'com-{m}-{c}.json', nc)
                nm['comunas'].append(nav)
            L_mun.append(nm)
        nd = N(acc_dep, cod=dep, nombre=dn)
        nd['municipios'] = L_mun
        escribe(out / f'dep-{dep}.json', nd)
        for circ, x in nd['por_circunscripcion'].items():
            dep_entries.append({'cod': dep, 'nombre': dn, 'circ_nom': circ,
                                **{k: x[k] for k in ('votval', 'votblan', 'votnul', 'votnma', 'votant')},
                                'partidos': x['partidos'], 'candidatos': x['candidatos']})
            for k in nac_circ[circ]:
                nac_circ[circ][k] += x[k]
            for pn_, v in x['partidos'].items():
                e = nac_part.setdefault(pn_, {'partido': pn_, 'codigo': cod_par.get((dep, circ, pn_), ''), 'votos': 0})
                e['votos'] += v
            for pn_, l in x['candidatos'].items():
                if circ in especial:     # nacional: el mismo candidato aparece en cada departamento → sumar
                    for c in l:
                        esp_cand[pn_][(c['nombre'], c.get('codigo', ''))] += c['votos']
                else:
                    nac_cand[pn_].extend(l)
            if circ in especial:
                especial_blan[circ] += x['votblan']
                for pn_, v in x['partidos'].items():
                    especial[circ][pn_] += v
                for pn_, l in x['candidatos'].items():
                    especial_cand[circ][pn_].extend(l)
        # curules territoriales y listas cerradas de este departamento
        t_ = nd['por_circunscripcion']['TERRITORIAL']
        s = CUR_DEP[dep] if not (dep == '88' and anio == '2014') else 2
        for pn_, n in curules_camara(t_['partidos'], t_['votblan'], s).items():
            # ⚠ el catálogo (dep 00) de Cámara 2022 trae nombres sueltos SIN departamento: usarlo mezclaba
            # la lista del Pacto de Bogotá con la de Antioquia. Las listas cerradas salen de LISTAS_CAMARA.
            if not t_['candidatos'].get(pn_):
                nombres = LISTAS_CAMARA.get((anio, dep, pn_))
                if nombres and len(nombres) == n:
                    cerradas['territorial'].setdefault(dep, {})[pn_] = nombres
                else:
                    pendientes.append({'circ': 'TERRITORIAL', 'dep': dep, 'dep_nom': dn, 'partido': pn_, 'curules': n,
                                       'nombres_cargados': len(nombres or [])})
    for circ, vot in especial.items():
        cur = (curules_afro(dict(vot), especial_blan[circ], anio) if circ == 'AFRO-DESCENDIENTES'
               else curules_camara(dict(vot), 0, CUR_ESP[circ]))
        for pn_, n in cur.items():
            if especial_cand[circ].get(pn_):
                continue
            nombres = LISTAS_AFRO.get((anio, pn_)) if circ == 'AFRO-DESCENDIENTES' else None
            if nombres and len(nombres) == n:
                cerradas.setdefault('afro', {})[pn_] = nombres
            else:
                pendientes.append({'circ': circ, 'partido': pn_, 'curules': n})
    escribe(out / 'departamentos.json', sorted(dep_entries, key=lambda x: (x['nombre'], x['circ_nom'])))
    partidos = sorted(nac_part.values(), key=lambda x: -x['votos'])
    for e in partidos:
        esp = [{'nombre': n, 'votos': v, 'codigo': c} for (n, c), v in esp_cand.get(e['partido'], {}).items()]
        e['candidatos'] = sorted(nac_cand.get(e['partido'], []) + esp, key=lambda x: -x['votos'])
    t_ = nac_circ['TERRITORIAL']
    escribe(out / 'resumen.json', {
        'corporacion': 'CAMARA', 'generado_en': datetime.now(timezone.utc).isoformat(), **t_,
        'partidos': partidos, 'por_circunscripcion': nac_circ,
        'fuente_nacional': f'Registraduría · consolidado del escrutinio (GCS) · elecciones del {FECHA[anio]}',
        'nota_territorial': 'Departamento, municipio, puesto y mesa: el mismo consolidado del escrutinio.'})
    escribe(out / 'listas_cerradas.json', cerradas)
    escribe(out / 'listas_cerradas_pendientes.json', pendientes)
    with open(out / 'censo.csv', 'w', newline='') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['dd', 'mm', 'zz', 'pp', 'mujeres', 'hombres', 'total'])
        w.writerows(censo_por_puesto(anio))
    for f in tmp.glob('*.tsv'):
        f.unlink()
    print(f'  camara {anio}: listo en {time.time() - t0:.0f} s · territorial votantes {t_["votant"]:,} · '
          f'listas cerradas resueltas {sum(len(v) for v in cerradas["territorial"].values())} · pendientes {len(pendientes)}')


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
    if corp not in ('senado', 'camara'):
        raise SystemExit('uso: build.py senado|camara <año>…')
    mun_nom, pue_nom = cargar_nombres()
    for a in anios:
        (senado if corp == 'senado' else camara)(a, mun_nom, pue_nom)


if __name__ == '__main__':
    main()
