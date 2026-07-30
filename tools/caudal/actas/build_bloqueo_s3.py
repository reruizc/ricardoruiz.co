#!/usr/bin/env python3
"""
Caudal · Fase 3 — arma el dataset de bloqueo para S3 (consume la Lambda/frontend).

Combina los agendamientos-{ambito}.json en un solo bloqueo.json con:
  - sistema: P(tratado|posición), hazard/supervivencia por nº de agendamiento,
    distribución, ranking de comisiones (para el dashboard/landing).
  - sistema.plenaria: lo MISMO calculado sobre la cola de la plenaria de Cámara
    (segundo debate). Va aparte a propósito: no es una comisión y mezclarla
    contaminaría tanto el P(tratado|posición) nacional como el ranking.
  - por_proyecto: lookup por número Cámara "NNN/YY" → {n, pos_prom, primera,
    ultima, titulo, com} de comisión + bloque `plen` con lo de plenaria
    (para la ficha del proyecto). Un proyecto puede tener solo plenaria (n=0).

Uso: python3 tools/caudal/actas/build_bloqueo_s3.py
Sube: aws s3 cp .../bloqueo.json s3://caudal-legislativo/metadata/bloqueo.json
"""
import json, datetime
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parents[3]
CACHE = REPO / 'Bases de datos' / 'leyes-senado' / 'actas'
OUT = CACHE / 'bloqueo.json'
GAP_MAX = 45
BUCKETS = [(1, 1, '1º'), (2, 3, '2º-3º'), (4, 6, '4º-6º'),
           (7, 10, '7º-10º'), (11, 15, '11º-15º'), (16, 9999, '16º+')]
PLENARIA = 'plenaria'


def d(s):
    return datetime.date.fromisoformat(s)


def pct(a, b):
    return round(100 * a / b, 1) if b else 0


def p_tratado(idx):
    """P(tratado|posición) de un ámbito: 'tratado' = no reaparece en la sesión
    siguiente (proxy, gap<=45d), medido solo sobre los perseguidos (n>=2) para
    no contaminar con los que se agendaron una única vez."""
    sesiones = defaultdict(list)
    for tok, info in idx.items():
        for fe, p in zip(info['fechas'], info['posiciones']):
            sesiones[fe].append((p, tok))
    fechas = sorted(sesiones)
    toks_f = {fe: {t for _, t in sesiones[fe]} for fe in fechas}
    nxt = {fechas[i]: fechas[i + 1] for i in range(len(fechas) - 1)
           if (d(fechas[i + 1]) - d(fechas[i])).days <= GAP_MAX}
    perseguido = {t for t, i in idx.items() if i['n'] >= 2}
    b = {lab: [0, 0] for _, _, lab in BUCKETS}
    for fe in fechas:
        if fe not in nxt:
            continue
        after = toks_f[nxt[fe]]
        for pos, tok in sesiones[fe]:
            if tok not in perseguido:
                continue
            tr = tok not in after
            for lo, hi, lab in BUCKETS:
                if lo <= pos <= hi:
                    b[lab][0] += tr
                    b[lab][1] += 1
                    break
    return b


def bloque_sistema(b, tot_k, para_k, dist, aportantes=None):
    """`aportantes` = cuántos ámbitos distintos alimentan cada bucket. Sirve
    para no leer como propiedad del sistema lo que es composición de UNA sola
    fuente: en Senado, p.ej., el bucket 16º+ sale ÍNTEGRO de la Comisión Sexta
    (la única con agendas largas: máx. 38 ítems, vs 15 en Quinta y 3 en
    Cuarta), así que su porcentaje describe a Sexta, no al Senado. El
    frontend puede atenuar o anotar los buckets con un solo aportante."""
    return {
        'p_tratado_por_posicion': {lab: {'pct': pct(b[lab][0], b[lab][1]), 'n': b[lab][1],
                                         **({'ambitos': len(aportantes.get(lab, ()))}
                                            if aportantes is not None else {})}
                                   for _, _, lab in BUCKETS},
        'hazard_agendamiento': [{'k': k, 'sigue_pct': round(100 * (1 - para_k[k] / tot_k[k]), 1),
                                 'n': tot_k[k]} for k in range(1, 13) if tot_k[k]],
        'distribucion': {str(n): dist[n] for n in sorted(dist)},
    }


def acumular(idx, tot_k, para_k, dist):
    for info in idx.values():
        dist[info['n']] += 1
        para_k[info['n']] += 1
        for k in range(1, info['n'] + 1):
            tot_k[k] += 1


def agregar(files):
    """Agrega los agendamientos de UNA cámara → (sistema, por_proyecto).

    Se factorizó para poder correr lo mismo sobre Cámara y sobre Senado sin
    duplicar la lógica. CLAVE: cada cámara produce su PROPIO `por_proyecto`
    y nunca se fusionan — el token es 'NNN/YY' y ese número se REINICIA en
    cada cámara, así que '259/24' es un proyecto en Cámara y otro distinto
    en Senado. Mezclarlos sumaría agendamientos de proyectos que no tienen
    nada que ver (mismo bug de identidad que ya nos mordió al deduplicar el
    histórico por número, ver CLAUDE.md 'EL NÚMERO DE RADICADO NO ES
    IDENTIFICADOR ÚNICO')."""
    nat = {lab: [0, 0] for _, _, lab in BUCKETS}
    aportantes = defaultdict(set)      # bucket → comisiones que lo alimentan
    tot_k, para_k, dist = defaultdict(int), defaultdict(int), defaultdict(int)
    per_com, por_proy = [], {}
    plen_meta = None

    for f in files:
        com = f.stem.replace('agendamientos-', '')
        data = json.load(open(f, encoding='utf-8'))
        idx = data['agendamientos']
        if not idx:
            continue
        es_plen = com == PLENARIA or data.get('ambito') == PLENARIA

        if es_plen:
            # la plenaria va a su propio bloque, con sus propios acumuladores
            p_tot, p_para, p_dist = defaultdict(int), defaultdict(int), defaultdict(int)
            acumular(idx, p_tot, p_para, p_dist)
            plen_meta = {
                **bloque_sistema(p_tratado(idx), p_tot, p_para, p_dist),
                'totales': {'proyectos': len(idx),
                            'sesiones': data.get('n_sesiones_con_proyectos', 0),
                            'sesiones_publicadas': data.get('n_sesiones', 0),
                            'mediana_agend': _mediana(idx)},
            }
            for tok, info in idx.items():
                entry = por_proy.setdefault(tok, {'n': 0, 'pos_prom': 0, 'primera': '',
                                                  'ultima': '', 'titulo': '', 'com': []})
                entry['plen'] = {
                    'n': info['n'],
                    'pos_prom': round(sum(info['posiciones']) / len(info['posiciones']), 1),
                    'primera': info['primera'], 'ultima': info['ultima'],
                }
                if not entry['titulo']:
                    entry['titulo'] = info['titulo']
            continue

        acumular(idx, tot_k, para_k, dist)
        b = p_tratado(idx)
        for _, _, lab in BUCKETS:
            nat[lab][0] += b[lab][0]
            nat[lab][1] += b[lab][1]
            if b[lab][1]:
                aportantes[lab].add(com)
        for tok, info in idx.items():
            entry = {'n': info['n'],
                     'pos_prom': round(sum(info['posiciones']) / len(info['posiciones']), 1),
                     'primera': info['primera'], 'ultima': info['ultima'],
                     'titulo': info['titulo'], 'com': [com]}
            prev = por_proy.get(tok)
            if prev and prev['n']:             # mismo número en 2 comisiones → suma
                prev['n'] += entry['n']
                prev['com'].append(com)
                prev['ultima'] = max(prev['ultima'], entry['ultima'])
                prev['primera'] = min(prev['primera'], entry['primera'])
                if not prev['titulo']:
                    prev['titulo'] = entry['titulo']
            elif prev:                         # ya venía de plenaria (n=0)
                plen = prev.get('plen')
                prev.update(entry)
                if plen:
                    prev['plen'] = plen
            else:
                por_proy[tok] = entry
        per_com.append({'com': com, 'proyectos': len(idx),
                        'sesiones': data.get('n_sesiones_con_proyectos', 0),
                        'mediana_agend': _mediana(idx),
                        # nº total de observaciones de la curva: con muestras
                        # chicas (p.ej. Cuarta del Senado: 40 obs, 4 de 6
                        # buckets vacíos) el porcentaje por posición es ruido y
                        # no debe graficarse como curva.
                        'n_obs': sum(b[lab][1] for _, _, lab in BUCKETS),
                        'pct_1o_tratado': pct(b['1º'][0], b['1º'][1]),
                        'p_tratado_por_posicion': {lab: {'pct': pct(b[lab][0], b[lab][1]),
                                                         'n': b[lab][1]} for _, _, lab in BUCKETS}})

    sistema = {
        **bloque_sistema(nat, tot_k, para_k, dist, aportantes),
        'comisiones': sorted(per_com, key=lambda x: -x['mediana_agend']),
        'totales': {'proyectos': sum(c['proyectos'] for c in per_com),
                    'sesiones': sum(c['sesiones'] for c in per_com),
                    'comisiones': len(per_com)},
    }
    if plen_meta:
        sistema['plenaria'] = plen_meta
    return sistema, por_proy


def main():
    sistema, por_proy = agregar(sorted(CACHE.glob('agendamientos-*.json')))
    out = {'v': datetime.date.today().isoformat(),
           'fuente': 'Cámara · órdenes del día de comisión y plenaria (wp-json)',
           'sistema': sistema, 'por_proyecto': por_proy}

    # SENADO — bloque namespaceado aparte (nunca fusionado con el de Cámara,
    # ver docstring de agregar()). Alcance declarado: solo 3 de las 7
    # comisiones constitucionales tienen serie usable en el DOCman del Senado
    # (Cuarta/Quinta/Sexta); Primera/Segunda/Tercera/Séptima son un hueco
    # conocido y la Gaceta no es vía viable para llenarlo (rezago de 11-16
    # meses, medido — ver harvest_ordenes_senado.py). La PLENARIA sí está
    # completa 2018-2026 y sale de OTRO sitio (secretariasenado.gov.co).
    sen_files = sorted((CACHE / 'ordenes-senado').glob('agendamientos-*.json'))
    sistema_sen, por_proy_sen = agregar(sen_files) if sen_files else (None, {})
    if sistema_sen:
        out['senado'] = {
            'fuente': 'Senado · órdenes del día de comisión (DOCman senado.gov.co) '
                      'y plenaria (DOCman secretariasenado.gov.co)',
            'alcance': 'comisiones constitucionales Cuarta/Quinta/Sexta + plenaria; '
                       'Primera/Segunda/Tercera/Séptima sin serie publicada',
            'sistema': sistema_sen, 'por_proyecto': por_proy_sen,
        }

    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
    kb = OUT.stat().st_size / 1024
    n_plen = sum(1 for v in por_proy.values() if v.get('plen'))
    print(f'bloqueo.json · CÁMARA {len(por_proy)} proyectos ({n_plen} con plenaria) · '
          f'{sistema["totales"]["comisiones"]} comisiones · {kb:.0f} KB')
    if sistema.get('plenaria'):
        t = sistema['plenaria']['totales']
        print(f'  plenaria Cámara: {t["proyectos"]} proyectos en {t["sesiones"]} sesiones '
              f'con agenda (de {t["sesiones_publicadas"]} publicadas)')
    if sistema_sen:
        n_ps = sum(1 for v in por_proy_sen.values() if v.get('plen'))
        print(f'  SENADO {len(por_proy_sen)} proyectos ({n_ps} con plenaria) · '
              f'{sistema_sen["totales"]["comisiones"]} comisiones')
        if sistema_sen.get('plenaria'):
            t = sistema_sen['plenaria']['totales']
            print(f'  plenaria Senado: {t["proyectos"]} proyectos en {t["sesiones"]} sesiones '
                  f'con agenda (de {t["sesiones_publicadas"]} publicadas)')
    print(f'→ {OUT.relative_to(REPO)}')
    print('subir: aws s3 cp "%s" s3://caudal-legislativo/metadata/bloqueo.json' % OUT)


def _mediana(idx):
    ns = sorted(i['n'] for i in idx.values() if i['n'] >= 2)
    return ns[len(ns) // 2] if ns else 0


if __name__ == '__main__':
    main()
