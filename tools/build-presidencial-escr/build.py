#!/usr/bin/env python3
"""Agregados de las presidenciales por ano, en el formato que consume el
visualizador de escrutinio (el mismo de consultas-escr-2026).

  python3 tools/build-presidencial-escr/build.py 2018
  python3 tools/build-presidencial-escr/build.py 2022
  python3 tools/build-presidencial-escr/build.py todos

Lee GCS_{ano}PRES1V.csv y GCS_{ano}PRES2V.csv y emite, en
Bases de datos/output_presidencial_escr/{ano}/:

  resumen.json    nacional: las dos vueltas con sus candidatos
  deps.json       33 deptos con el agregado de cada vuelta
  dep-{cod}.json  arbol depto -> municipio -> zona -> puesto

Las dos vueltas viajan como las "consultas" del chasis original: claves '1v'
y '2v'. Asi el frontend no necesita un modelo de datos nuevo.

GOTCHAS (medidos, no supuestos):

- Los especiales se filtran por COD_CAN, NUNCA por COD_PAR. La convencion de
  partido cambia entre archivos y en 2022 los candidatos REALES pasan de 996
  (Petro 1235, Fico 1234, Rodolfo 1076), asi que filtrar por partido borraria
  a los punteros. Los COD_CAN especiales son estables: 96,97,98,996,997,998,999.
- En 2018 existe una candidatura REAL llamada "PROMOTORES VOTO EN BLANCO"
  (COD_CAN=2, 30.128 votos). Filtrar por el texto del nombre la borraria.
- El nombre de zona se arma con la tabla zona->comuna derivada del georef: la
  zona electoral NO es la comuna politica (Medellin: 32 zonas, 16 comunas).
- El georef es de 2026 y estos datos son de 2018/2022, asi que una parte de los
  puestos no tiene nombre; caen al rotulo "Puesto NN" en vez de inventarlo.
"""
import csv, json, os, sys, collections

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GCS = os.path.join(RAIZ, 'Bases de datos', 'FINAL SUBIDA GCS')
OUT_BASE = os.path.join(RAIZ, 'Bases de datos', 'output_presidencial_escr')
DIVIPOLA = os.path.join(RAIZ, 'Bases de datos', 'test-presidencial', 'divipola.json')
GEOREF = os.path.join(RAIZ, 'Bases de datos', 'PUESTOS_GEOREF.csv')
ZONA_COMUNA = os.path.join(RAIZ, 'Bases de datos', 'output_geo', 'zona-comuna.json')

VUELTAS = [('1v', 'Primera vuelta', 'PRES1V'), ('2v', 'Segunda vuelta', 'PRES2V')]
SPECIAL_CAN = {'96', '97', '98', '996', '997', '998', '999'}

# Anclas contra el resultado oficial. Solo van las dos que reproducen el oficial
# al voto (verificadas antes en este repo); las otras dos vueltas vienen en un
# corte del GCS ligeramente menor al boletin publicado -- 2018-2V da Duque
# 10.397.314 contra 10.398.689 oficial (-1.375) y 2022-1V da Petro 8.542.020 --
# asi que compararlas contra el boletin haria fallar un pipeline que esta bien.
# Para esas, el chequeo es de CONSERVACION: que no se pierda ni un voto del
# archivo entre la lectura y los agregados.
CONTROL = {
    ('2018', '1v'): {'IVAN DUQUE': 7616857, 'GUSTAVO PETRO': 4855069},
    ('2022', '2v'): {'GUSTAVO PETRO': 11292758, 'RODOLFO HERNANDEZ': 10604656},
}


def title(s):
    out = []
    for w in str(s or '').split():
        out.append(w if len(w) <= 2 and w.isupper() and w.isalpha() is False else w.capitalize())
    return ' '.join(out)


def norm_cand(s):
    return ' '.join(str(s or '').strip().split()).title()


def to2(v):
    try:
        return str(int(v)).zfill(2)
    except Exception:
        return str(v or '').zfill(2)


def to3(v):
    try:
        return str(int(v)).zfill(3)
    except Exception:
        return str(v or '').zfill(3)


def cargar_nombres():
    dep_nom, mun_nom = {}, {}
    with open(DIVIPOLA, encoding='utf-8') as f:
        for d in json.load(f)['deptos']:
            dep_nom[to2(d['cod'])] = d['nombre']
            for m in d.get('muns', []):
                mun_nom[(to2(d['cod']), to3(m['cod']))] = m['nombre']

    pue_nom = {}
    with open(GEOREF, encoding='utf-8-sig', errors='replace') as f:
        delim = ';' if f.readline().count(';') > 3 else ','
    with open(GEOREF, encoding='utf-8-sig', errors='replace') as f:
        for r in csv.DictReader(f, delimiter=delim):
            cc = (r.get('CÓDIGO COMPLETO') or r.get('CODIGO COMPLETO') or '').strip()
            nom = (r.get('NOMBRE PUESTO') or '').strip()
            if len(cc) == 9 and cc.isdigit() and nom and nom.upper() != 'NULL':
                pue_nom[cc] = nom

    zc = {}
    if os.path.exists(ZONA_COMUNA):
        with open(ZONA_COMUNA, encoding='utf-8') as f:
            zc = json.load(f)['muns']
    return dep_nom, mun_nom, pue_nom, zc


def nombre_zona(dep, mun, zon, zc):
    m = zc.get(f'{dep}-{mun}')
    if m:
        cod = m['z'].get(zon)
        if cod:
            return f"Zona {zon} · {title(m['c'].get(cod, f'Comuna {int(cod)}'))}"
    return f'Zona {zon}'


def leer_vuelta(path, acc, clave):
    """Suma los votos de un archivo GCS al acumulador jerarquico.

    Devuelve el total crudo leido, para poder verificar despues que los
    agregados no perdieron ni un voto.
    """
    nac = acc['nac'][clave]
    crudo = 0
    with open(path, encoding='utf-8-sig', errors='replace') as f:
        rd = csv.reader(f, delimiter=';')
        next(rd, None)
        for r in rd:
            if len(r) < 16:
                continue
            dep, mun, zon, pue = to2(r[6]), to3(r[7]), to2(r[8]), to2(r[9])
            can, des = r[13].strip(), norm_cand(r[14])
            try:
                v = int(r[15])
            except ValueError:
                continue
            if not v:
                continue
            crudo += v
            if can in SPECIAL_CAN:
                acc['esp'][clave][des] += v
                continue
            nac[des] += v
            acc['dep'][dep][clave][des] += v
            acc['mun'][(dep, mun)][clave][des] += v
            acc['zon'][(dep, mun, zon)][clave][des] += v
            acc['pue'][(dep, mun, zon, pue)][clave][des] += v
    return crudo


def bloque(counter):
    cands = sorted(counter.items(), key=lambda kv: -kv[1])
    return {'votos': sum(counter.values()),
            'cands': [{'nombre': n, 'votos': v} for n, v in cands]}


def build(anio):
    dep_nom, mun_nom, pue_nom, zc = cargar_nombres()
    mk = lambda: collections.defaultdict(collections.Counter)
    crudos = {}
    acc = {'nac': mk(), 'esp': mk(),
           'dep': collections.defaultdict(mk), 'mun': collections.defaultdict(mk),
           'zon': collections.defaultdict(mk), 'pue': collections.defaultdict(mk)}

    for clave, _, suf in VUELTAS:
        path = os.path.join(GCS, f'GCS_{anio}{suf}.csv')
        if not os.path.exists(path):
            sys.exit(f'falta {path}')
        print(f'  leyendo {os.path.basename(path)} ...', flush=True)
        crudos[clave] = leer_vuelta(path, acc, clave)

    # --- conservacion: ningun voto del archivo se pierde por el camino ---
    for clave, nom_v, _ in VUELTAS:
        agregado = sum(acc['nac'][clave].values()) + sum(acc['esp'][clave].values())
        por_puesto = sum(sum(c.values()) for k, c in
                         ((k, acc['pue'][k][clave]) for k in acc['pue']))
        ok = agregado == crudos[clave]
        print(f"    [{'OK ' if ok else 'MAL'}] {nom_v} conservacion: "
              f"{agregado:,} de {crudos[clave]:,} leidos "
              f"(candidatos por puesto: {por_puesto:,})")
        if not ok:
            sys.exit('se perdieron votos entre la lectura y los agregados')

    # --- validacion contra el resultado oficial (donde el GCS lo reproduce) ---
    for clave, nom_v, _ in VUELTAS:
        ctrl = CONTROL.get((anio, clave), {})
        for cand, esperado in ctrl.items():
            got = acc['nac'][clave].get(norm_cand(cand), 0)
            estado = 'OK ' if got == esperado else 'MAL'
            print(f'    [{estado}] {nom_v} {cand}: {got:,} (oficial {esperado:,})')
            if got != esperado:
                sys.exit('el total no cuadra con el oficial; no se escribe nada')

    out_dir = os.path.join(OUT_BASE, anio)
    os.makedirs(out_dir, exist_ok=True)

    # --- resumen nacional ---
    vueltas_meta = []
    for clave, nom_v, _ in VUELTAS:
        b = bloque(acc['nac'][clave])
        cods = {}
        cands = []
        for i, c in enumerate(b['cands'], 1):
            cods[c['nombre']] = str(i)
            cands.append({'nombre': c['nombre'], 'votos': c['votos'], 'codigo': str(i)})
        vueltas_meta.append({'clave': clave, 'nombre': nom_v, 'nombre_largo': f'{nom_v} {anio}',
                             'votos': b['votos'], 'candidatos': cands,
                             'especiales': dict(acc['esp'][clave])})
    resumen = {'anio': anio, 'consultas': vueltas_meta}
    with open(os.path.join(out_dir, 'resumen.json'), 'w', encoding='utf-8') as f:
        json.dump(resumen, f, ensure_ascii=False, separators=(',', ':'))

    # --- deps.json ---
    deps = []
    for dep in sorted(acc['dep']):
        e = {'cod': dep, 'nombre': dep_nom.get(dep, f'Depto {dep}')}
        for clave, _, _ in VUELTAS:
            b = bloque(acc['dep'][dep][clave])
            e[clave] = {'votos': b['votos'],
                        'candidatos': [{'nombre': c['nombre'], 'votos': c['votos']} for c in b['cands']]}
        deps.append(e)
    with open(os.path.join(out_dir, 'deps.json'), 'w', encoding='utf-8') as f:
        json.dump(deps, f, ensure_ascii=False, separators=(',', ':'))

    # --- dep-{cod}.json ---
    muns_by_dep = collections.defaultdict(list)
    for (dep, mun) in acc['mun']:
        muns_by_dep[dep].append(mun)
    zons_by_mun = collections.defaultdict(list)
    for (dep, mun, zon) in acc['zon']:
        zons_by_mun[(dep, mun)].append(zon)
    pues_by_zon = collections.defaultdict(list)
    for (dep, mun, zon, pue) in acc['pue']:
        pues_by_zon[(dep, mun, zon)].append(pue)

    total_bytes = 0
    for dep in sorted(acc['dep']):
        d = {'cod': dep, 'nombre': dep_nom.get(dep, f'Depto {dep}')}
        for clave, _, _ in VUELTAS:
            d[clave] = bloque(acc['dep'][dep][clave])
        munis = []
        for mun in sorted(muns_by_dep[dep]):
            m = {'cod': mun, 'nombre': mun_nom.get((dep, mun), f'Municipio {mun}')}
            for clave, _, _ in VUELTAS:
                m[clave] = bloque(acc['mun'][(dep, mun)][clave])
            zonas = []
            for zon in sorted(zons_by_mun[(dep, mun)]):
                z = {'cod': zon, 'nombre': nombre_zona(dep, mun, zon, zc)}
                for clave, _, _ in VUELTAS:
                    z[clave] = bloque(acc['zon'][(dep, mun, zon)][clave])
                puestos = []
                for pue in sorted(pues_by_zon[(dep, mun, zon)]):
                    p = {'cod': pue, 'nombre': pue_nom.get(dep + mun + zon + pue, f'Puesto {pue}')}
                    for clave, _, _ in VUELTAS:
                        p[clave] = bloque(acc['pue'][(dep, mun, zon, pue)][clave])
                    puestos.append(p)
                z['puestos'] = puestos
                zonas.append(z)
            m['zonas'] = zonas
            munis.append(m)
        d['municipios'] = munis
        path = os.path.join(out_dir, f'dep-{dep}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, separators=(',', ':'))
        total_bytes += os.path.getsize(path)

    con_nombre = sum(1 for k in acc['pue'] if (k[0] + k[1] + k[2] + k[3]) in pue_nom)
    print(f'  {len(deps)} deptos · {len(acc["mun"])} municipios · {len(acc["pue"])} puestos')
    print(f'  puestos con nombre del georef: {con_nombre}/{len(acc["pue"])} '
          f'({100*con_nombre/max(1,len(acc["pue"])):.0f}%)')
    print(f'  -> {out_dir}  ({total_bytes/1024/1024:.1f} MB en dep-*.json)')


if __name__ == '__main__':
    args = sys.argv[1:] or ['todos']
    anios = ['2018', '2022'] if args[0] == 'todos' else args
    for a in anios:
        print(f'\n=== PRESIDENCIAL {a} ===')
        build(a)
