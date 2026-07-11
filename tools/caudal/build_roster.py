#!/usr/bin/env python3
"""
Caudal · roster clave-canónica → partido/bancada.

Los autores de proyectos de ley SON congresistas electos, así que aparecen en
los resultados de Congreso con su partido. Este script extrae cada candidato→
partido de las elecciones de Congreso (GCS 2014/2018/2022 + preconteo 2026) y
los canoniza con la MISMA clave de normalize_autores, para poder unir por
`autores_keys` de cada proyecto.

Un congresista puede cambiar de partido entre años → guardamos todas las
apariciones (partido, año) y elegimos `partido_principal` = el más reciente.

Salida: Bases de datos/leyes-senado/dist/roster-autores.json
  { "v":..., "n":..., "roster": { "<canon_key>": {
        "display": "...", "partido_principal": "...", "anio_ultimo": 2022,
        "partidos": [{"partido":"...","anios":[2018,2022]}, ...] } } }

Uso: python3 tools/caudal/build_roster.py
"""
import csv
import json
import sys
from pathlib import Path
from collections import defaultdict

# Override manual curado para legisladores prolíficos que NO caen en los datos
# de Congreso 2014+ (casi todos pre-2014, del Polo/MIRA/etc.). Partido = el de
# su periodo legislativo principal. SOLO casos de alta confianza. via='manual'.
MANUAL = {
    'GLORIA INES RAMIREZ RIOS': 'POLO DEMOCRÁTICO ALTERNATIVO',
    'ALEXANDRA MORENO PIRAQUIVE': 'MIRA',
    'GLORIA STELLA DIAZ': 'MIRA',
    'GERMAN VARGAS LLERAS': 'CAMBIO RADICAL',
    'VICTORIA SANDINO SIMANCA HERRERA': 'COMUNES (FARC)',
    'SAMUEL MORENO ROJAS': 'POLO DEMOCRÁTICO ALTERNATIVO',
    'JORGE ENRIQUE ROBLEDO CASTILLO': 'POLO DEMOCRÁTICO ALTERNATIVO',
    'GUSTAVO PETRO URREGO': 'PACTO HISTÓRICO',
}

sys.path.insert(0, str(Path(__file__).resolve().parent))
import normalize_autores as na

REPO = Path(__file__).resolve().parents[2]
GCS = REPO / 'Bases de datos' / 'FINAL SUBIDA GCS'
C2026 = REPO / 'Bases de datos' / 'csv_con_nombres_2026' / 'congreso_2026.csv'
DIST = REPO / 'Bases de datos' / 'leyes-senado' / 'dist'

csv.field_size_limit(10**7)

# fuentes: (archivo, año, delimitador, col_nombre, col_partido)
FUENTES = [
    (GCS / 'GCS_2014CON.csv', 2014, ';', 'DES_CAN', 'DES_PAR'),
    (GCS / 'GCS_2018CON.csv', 2018, ';', 'DES_CAN', 'DES_PAR'),
    (GCS / 'GCS_2022CON.csv', 2022, ';', 'DES_CAN', 'DES_PAR'),
    (C2026,                   2026, ',', 'nom_candidato', 'partido'),
]

# ruido en el campo candidato (no son personas)
_RUIDO_CAN = {'VOTOS EN BLANCO', 'VOTO EN BLANCO', 'NULO', 'NULOS',
              'NO MARCADO', 'NO MARCADOS', 'VOTOS NULOS'}


def extraer(path, anio, delim, cn, cp):
    """Set de (canon_key, display, partido) distintos del archivo (streaming)."""
    vistos = set()
    out = []
    with open(path, encoding='utf-8-sig', errors='replace', newline='') as f:
        r = csv.DictReader(f, delimiter=delim)
        for row in r:
            nombre = (row.get(cn) or '').strip()
            partido = (row.get(cp) or '').strip()
            if not nombre or not partido or nombre.upper() in _RUIDO_CAN:
                continue
            k = na.canon_key(nombre)
            if len(k) < 4:
                continue
            sig = (k, partido)
            if sig in vistos:
                continue
            vistos.add(sig)
            out.append((k, na.limpiar(nombre), partido))
    return out


def main():
    reuse = '--reuse' in sys.argv     # reusa roster-autores.json sin re-escanear los 4GB
    if reuse and (DIST / 'roster-autores.json').exists():
        out = json.load(open(DIST / 'roster-autores.json', encoding='utf-8'))['roster']
        print(f'(--reuse) roster cargado de disco → {len(out)} congresistas')
    else:
        roster = defaultdict(lambda: {'displays': {}, 'partidos': defaultdict(set)})
        for path, anio, delim, cn, cp in FUENTES:
            if not path.exists():
                print(f'  (falta {path.name}, lo salto)')
                continue
            filas = extraer(path, anio, delim, cn, cp)
            for k, disp, partido in filas:
                e = roster[k]
                e['displays'][disp] = e['displays'].get(disp, 0) + 1
                e['partidos'][partido].add(anio)
            print(f'  {path.name} ({anio}): {len(filas)} pares candidato-partido distintos')

        out = {}
        for k, e in roster.items():
            display = max(e['displays'].items(),
                          key=lambda x: (sum(1 for c in x[0] if ord(c) > 127), x[1]))[0]
            partidos = sorted(
                ({'partido': p, 'anios': sorted(anios)} for p, anios in e['partidos'].items()),
                key=lambda x: -max(x['anios']))
            out[k] = {'display': display,
                      'partido_principal': partidos[0]['partido'],
                      'anio_ultimo': partidos[0]['anios'][-1],
                      'partidos': partidos}
        DIST.mkdir(parents=True, exist_ok=True)
        json.dump({'v': '2026-07-11', 'n': len(out), 'roster': out},
                  open(DIST / 'roster-autores.json', 'w', encoding='utf-8'), ensure_ascii=False)
        print(f'\nroster-autores.json → {len(out)} congresistas con partido')

    # --- índice por token para matching por subconjunto ---------------------
    roster_toks = {k: frozenset(k.split()) for k in out}
    tok_index = defaultdict(set)
    for k, toks in roster_toks.items():
        for t in toks:
            tok_index[t].add(k)

    def match(akey):
        """clave de autor → (roster_key, via) por exacto o subconjunto de tokens."""
        if akey in out:
            return akey, 'exacto'
        atoks = frozenset(akey.split())
        if len(atoks) < 3:            # 2 tokens: subset es arriesgado, solo exacto
            return None, None
        cand = None
        for t in atoks:               # roster keys que contienen TODOS los tokens del autor
            s = tok_index.get(t, set())
            cand = s if cand is None else (cand & s)
            if not cand:
                break
        supersets = [k for k in (cand or ()) if atoks <= roster_toks[k]]
        if not supersets:
            return None, None
        partidos = {out[k]['partido_principal'] for k in supersets}
        best = max(supersets, key=lambda k: out[k]['anio_ultimo'])
        return best, 'subset' if len(partidos) == 1 else 'subset-ambiguo'

    # --- join contra el registro de autores → autor-partido.json ------------
    autores = json.load(open(DIST / 'autores.json', encoding='utf-8'))['autores']
    personas = [a for a in autores if a['tipo'] == 'persona']
    join = {}
    vias = defaultdict(int)
    for a in personas:
        rk, via = match(a['key'])
        if rk:
            e = out[rk]
            join[a['key']] = {'partido': e['partido_principal'],
                              'anio': e['anio_ultimo'], 'via': via,
                              'roster_key': rk,
                              'historial': e['partidos'] if len(e['partidos']) > 1 else None}
            vias[via] += 1
        elif a['key'] in MANUAL:
            join[a['key']] = {'partido': MANUAL[a['key']], 'anio': None,
                              'via': 'manual', 'roster_key': None, 'historial': None}
            vias['manual'] += 1
    json.dump({'v': '2026-07-11', 'n': len(join), 'autor_partido': join},
              open(DIST / 'autor-partido.json', 'w', encoding='utf-8'), ensure_ascii=False)

    con = len(join)
    tot_p = sum(a['n_proyectos'] for a in personas)
    con_p = sum(a['n_proyectos'] for a in personas if a['key'] in join)
    print(f'\nautor-partido.json → {con}/{len(personas)} personas con partido '
          f'({100*con/len(personas):.0f}%) · {100*con_p/tot_p:.0f}% ponderado por proyectos')
    print('  vías de match:', dict(vias))
    print('\ntop autores AÚN sin partido:')
    faltan = [a for a in sorted(personas, key=lambda x: -x['n_proyectos']) if a['key'] not in join][:8]
    for a in faltan:
        print(f"  {a['n_proyectos']:4}  {a['display']}")


if __name__ == '__main__':
    main()
