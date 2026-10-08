#!/usr/bin/env python3
"""CITREP 2026 · cuadra lo publicado en citrep-2026.html contra los E-26 de las 16 comisiones generales.

Insumos (Bases de datos/escrutinio-congreso-2026/citrep/):
  E26_CTP_*_<comisión>.pdf + .ocr.txt   un acta por circunscripción, comisiones 1034-1049, del portal
                                        escrutinioscongreso2026 (/docs/E26/…). OCR con
                                        tools/pliegos-choco/ocr_vision.swift (también las digitales,
                                        para leerlas todas con el mismo formato de línea).
  ⚠ La circunscripción 4 (Catatumbo, comisión 1037) tiene DOS actas publicadas.

Lectura: cada organización trae «000» (voto a la organización), «501» y «502» (sus dos
candidatos) y «TOTAL VOTOS». Cada cifra se valida contra «votos en letras»: si la cifra del
OCR y las letras no coinciden, manda la que cuadre con el total de la organización.

Salida: citrep/oficial.json (lo que dicen las actas) + informe por consola de las diferencias
con s3://…/congreso-2026/output/citrep/circunscripciones.json.
  python3 tools/escrutinio-congreso-2026/verificar_citrep.py [circunscripciones.json]
"""
import glob
import json
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DIR = RAIZ / 'Bases de datos' / 'escrutinio-congreso-2026' / 'citrep'

UNI = {'CERO': 0, 'UN': 1, 'UNO': 1, 'DOS': 2, 'TRES': 3, 'CUATRO': 4, 'CINCO': 5, 'SEIS': 6, 'SIETE': 7, 'OCHO': 8,
       'NUEVE': 9, 'DIEZ': 10, 'ONCE': 11, 'DOCE': 12, 'TRECE': 13, 'CATORCE': 14, 'QUINCE': 15, 'DIECISEIS': 16,
       'DIECISIETE': 17, 'DIECIOCHO': 18, 'DIECINUEVE': 19, 'VEINTE': 20, 'VEINTIUN': 21, 'VEINTIUNO': 21,
       'VEINTIDOS': 22, 'VEINTITRES': 23, 'VEINTICUATRO': 24, 'VEINTICINCO': 25, 'VEINTISEIS': 26,
       'VEINTISIETE': 27, 'VEINTIOCHO': 28, 'VEINTINUEVE': 29, 'TREINTA': 30, 'CUARENTA': 40, 'CINCUENTA': 50,
       'SESENTA': 60, 'SETENTA': 70, 'OCHENTA': 80, 'NOVENTA': 90, 'CIEN': 100, 'CIENTO': 100,
       'DOSCIENTOS': 200, 'TRESCIENTOS': 300, 'CUATROCIENTOS': 400, 'QUINIENTOS': 500, 'SEISCIENTOS': 600,
       'SETECIENTOS': 700, 'OCHOCIENTOS': 800, 'NOVECIENTOS': 900}


def sin_tilde(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def norm(s):
    s = sin_tilde(s).upper().replace('Ñ', 'N')
    return ' '.join(re.sub(r'[^A-Z0-9 ]', ' ', s).split())


def letras(txt):
    """'VEINTIUN MIL QUINIENTOS OCHENTA Y UNO' → 21581; None si alguna palabra no se reconoce."""
    pal = [w for w in norm(txt).split() if w != 'Y']
    if not pal:
        return None
    total, parcial = 0, 0
    for w in pal:
        if w == 'MIL':
            total += (parcial or 1) * 1000
            parcial = 0
        elif w in UNI:
            parcial += UNI[w]
        else:
            return None
    return total + parcial


NUM = r'(\d{1,3}(?:[.,]\d{3})*|\d+)'
LINEA = re.compile(r'^\[?(000|50\d)?\s*(.*?)\s+' + NUM + r'[|.\]/ ]*\s*([A-ZÁÉÍÓÚÑ ]{3,})$')


def cifra(s):
    return int(re.sub(r'[.,]', '', s))


def mejor(num_txt, let_txt):
    """Valor de una línea: la cifra y las letras deben coincidir; si no, se devuelven las dos."""
    a = cifra(num_txt) if num_txt else None
    b = letras(let_txt) if let_txt else None
    return a, b


def leer(path):
    lineas = [l.strip() for l in Path(path).read_text().splitlines() if l.strip()]
    circ = None
    orgs, org = [], None
    nulos = nomarc = None
    electo = None
    pend_total = False
    for i, l in enumerate(lineas):
        m = re.match(r'^CIRCUNSCRIPCI[OÓ]N (\d+)', l)
        if m and circ is None:
            circ = int(m.group(1))
        if re.match(r'^RESUMEN DE LA VOTACI', l):
            org = None
        m = re.match(r'^(\d{4})\s+(.+)$', l)
        if m and i + 1 < len(lineas) and norm(lineas[i + 1]).startswith('CODIGO'):
            org = {'cod': m.group(1), 'nombre': m.group(2).strip(' |'), 'c': {}, 'total': None}
            orgs.append(org)
            continue
        nl = norm(l)
        if nl.startswith('VOTOS NULOS CITREP'):
            m = re.search(NUM + r'\W*\s*([A-Z ]+)$', l)
            if m:
                nulos = mejor(m.group(1), m.group(2))
        if nl.startswith('VOTOS NO MARCADOS CITREP'):
            m = re.search(NUM + r'\W*\s*([A-Z ]+)$', l)
            if m:
                nomarc = mejor(m.group(1), m.group(2))
        m = re.match(r'^(\d{4})\s*-\s*(.+)$', l)
        if m and electo is None and ('CEDULA' in norm(lineas[i - 1]) or 'CANDIDATO' in norm(lineas[i - 1])):
            electo = {'cod_org': m.group(1), 'texto': m.group(2)}
        if org is None or org.get('cerrada'):
            continue
        if nl.startswith('TOTAL VOTOS'):
            m = re.search(NUM + r'\W*\s*([A-Z ]+)$', l)
            if not m and i + 1 < len(lineas):
                m = re.search(r'^' + NUM + r'\W*\s*([A-Z ]+)$', lineas[i + 1])
            if m:
                org['total'] = mejor(m.group(1), m.group(2))
            org['cerrada'] = True
            continue
        m = LINEA.match(l)
        if m and not nl.startswith('CODIGO'):
            cod = m.group(1) or ('000' if '000' not in org['c'] and norm(m.group(2))[:12] == norm(org['nombre'])[:12] else None)
            if cod is None:
                cod = '501' if '501' not in org['c'] else '502'
            org['c'][cod] = {'nombre': m.group(2).strip(' |[]'), 'v': mejor(m.group(3), m.group(4))}
    return {'circ': circ, 'orgs': orgs, 'nulos': nulos, 'nomarc': nomarc, 'electo': electo}


def resolver(o):
    """Decide la cifra de cada línea: coincide cifra-letras → esa; si no, la que cuadre con el total."""
    tot = o['total'] or (None, None)
    total = tot[0] if tot[0] == tot[1] or tot[1] is None else (tot[1] if tot[0] is None else None)
    if total is None and tot[0] is not None and tot[1] is not None:
        total = tot  # se resuelve abajo
    dudas = []
    vals = {}
    for k, c in o['c'].items():
        a, b = c['v']
        if a == b or b is None:
            vals[k] = a
        elif a is None:
            vals[k] = b
        else:
            vals[k] = (a, b)
            dudas.append(k)
    # combinaciones que cuadran con el total
    import itertools
    opciones = [[v] if not isinstance(v, tuple) else list(v) for v in vals.values()]
    totales = [total] if not isinstance(total, tuple) else list(total)
    sol = None
    for comb in itertools.product(*opciones):
        for t in totales:
            if t is not None and sum(comb) == t:
                sol = (dict(zip(vals.keys(), comb)), t)
                break
        if sol:
            break
    if sol:
        return sol[0], sol[1], True
    return {k: (v if not isinstance(v, tuple) else v[0]) for k, v in vals.items()}, (totales[0] if totales else None), False


def main():
    actas = sorted(glob.glob(str(DIR / 'E26_CTP_*.ocr.txt')))
    oficial = {}
    for a in actas:
        r = leer(a)
        com = re.search(r'_(\d{4})\.ocr', a).group(1)
        circ = r['circ']
        orgs = []
        for o in r['orgs']:
            vals, total, ok = resolver(o)
            orgs.append({'cod': o['cod'], 'nombre': o['nombre'], 'v000': vals.get('000'),
                         'c501': (o['c'].get('501') or {}).get('nombre'), 'v501': vals.get('501'),
                         'c502': (o['c'].get('502') or {}).get('nombre'), 'v502': vals.get('502'),
                         'total': total, 'cuadra': ok})
        clave = f'{circ:02d}' if circ else com
        if clave in oficial:
            clave = f'{clave}-{com}'
        oficial[clave] = {'comision': com, 'acta': Path(a).name.replace('.ocr.txt', '.pdf'), 'orgs': orgs,
                          'nulos': r['nulos'], 'nomarc': r['nomarc'], 'electo': r['electo']}
        malos = [o['nombre'] for o in orgs if not o['cuadra']]
        print(f"circ {clave:8s} com {com} · {len(orgs):2d} organizaciones · total {sum((o['total'] or 0) for o in orgs):7,} "
              f"· nulos {r['nulos']} · no marcados {r['nomarc']} · electo {r['electo']}"
              + (f" · NO CUADRAN: {malos}" if malos else ''))
    (DIR / 'oficial.json').write_text(json.dumps(oficial, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()


def comparar(s3_path):
    """Cada línea del acta contra circunscripciones.json de S3. Vale si S3 coincide con la cifra o con las letras."""
    import difflib
    of = json.loads((DIR / 'oficial.json').read_text())
    s3 = {c['cod']: c for c in json.load(open(s3_path))}
    actas = {}
    for p in sorted(glob.glob(str(DIR / 'E26_CTP_*.ocr.txt'))):
        r = leer(p)
        actas.setdefault(f"{r['circ']:02d}", []).append(r)
    resumen = {}
    for cc, lista in sorted(actas.items()):
        cand = {norm(k): v for k, v in s3[cc]['candidatos'].items()}
        keys = list(cand)
        for n_acta, r in enumerate(lista):
            ok = dif = 0
            difs = []
            for o in r['orgs']:
                lineas = [(c['nombre'], c['v'], k) for k, c in o['c'].items()]
                for nombre, (a, b), k in lineas:
                    q = norm(nombre)
                    m = difflib.get_close_matches(q, keys, n=1, cutoff=.72)
                    if not m:
                        difs.append((o['nombre'], k, nombre, (a, b), 'SIN PAR EN S3'))
                        dif += 1
                        continue
                    v = cand[m[0]]
                    if v in (a, b):
                        ok += 1
                    else:
                        dif += 1
                        difs.append((o['nombre'], k, nombre, (a, b), v))
            tot_s3 = s3[cc]['votos']
            tot_acta = sum((o['total'][0] if o['total'] else 0) for o in r['orgs'])
            print(f'circ {cc} acta {n_acta + 1}/{len(lista)} · líneas que cuadran {ok} · no cuadran {dif} · total S3 {tot_s3:,} · acta {tot_acta:,}')
            for d in difs:
                print('    ', d)
            resumen[cc] = (ok, dif)
    return resumen


if __name__ == '__main__' and len(sys.argv) > 1:
    comparar(sys.argv[1])
