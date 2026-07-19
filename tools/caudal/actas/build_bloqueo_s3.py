#!/usr/bin/env python3
"""
Caudal · Fase 3 — arma el dataset de bloqueo para S3 (consume la Lambda/frontend).

Combina los 14 agendamientos-{com}.json en un solo bloqueo.json con:
  - sistema: P(tratado|posición), hazard/supervivencia por nº de agendamiento,
    distribución, ranking de comisiones (para el dashboard/landing).
  - por_proyecto: lookup por número Cámara "NNN/YY" → {agendado, pos_prom,
    primera, ultima, titulo, comisiones} (para la ficha del proyecto).

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


def d(s):
    return datetime.date.fromisoformat(s)


def main():
    nat = {lab: [0, 0] for _, _, lab in BUCKETS}
    tot_k, para_k, dist = defaultdict(int), defaultdict(int), defaultdict(int)
    per_com, por_proy = [], {}

    for f in sorted(CACHE.glob('agendamientos-*.json')):
        com = f.stem.replace('agendamientos-', '')
        idx = json.load(open(f, encoding='utf-8'))['agendamientos']
        if not idx:
            continue
        data = json.load(open(f, encoding='utf-8'))
        # posición → tratado
        sesiones = defaultdict(list)
        for tok, info in idx.items():
            for fe, p in zip(info['fechas'], info['posiciones']):
                sesiones[fe].append((p, tok))
            # hazard + distribución + lookup por proyecto
            dist[info['n']] += 1
            para_k[info['n']] += 1
            for k in range(1, info['n'] + 1):
                tot_k[k] += 1
            prev = por_proy.get(tok)
            entry = {'n': info['n'], 'pos_prom': round(sum(info['posiciones']) / len(info['posiciones']), 1),
                     'primera': info['primera'], 'ultima': info['ultima'],
                     'titulo': info['titulo'], 'com': [com]}
            if prev:                       # mismo número en 2 comisiones → suma
                prev['n'] += entry['n']; prev['com'].append(com)
                prev['ultima'] = max(prev['ultima'], entry['ultima'])
                if not prev['titulo']:
                    prev['titulo'] = entry['titulo']
            else:
                por_proy[tok] = entry
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
                        b[lab][0] += tr; b[lab][1] += 1; nat[lab][0] += tr; nat[lab][1] += 1
                        break
        ns = sorted(i['n'] for i in idx.values() if i['n'] >= 2)
        per_com.append({'com': com, 'proyectos': len(idx),
                        'sesiones': data.get('n_sesiones_con_proyectos', 0),
                        'mediana_agend': ns[len(ns) // 2] if ns else 0,
                        'pct_1o_tratado': round(100 * b['1º'][0] / b['1º'][1], 1) if b['1º'][1] else 0,
                        'p_tratado_por_posicion': {lab: {'pct': round(100 * b[lab][0] / b[lab][1], 1) if b[lab][1] else 0,
                                                         'n': b[lab][1]} for _, _, lab in BUCKETS}})

    sistema = {
        'p_tratado_por_posicion': {lab: {'pct': round(100 * nat[lab][0] / nat[lab][1], 1) if nat[lab][1] else 0,
                                         'n': nat[lab][1]} for _, _, lab in BUCKETS},
        'hazard_agendamiento': [{'k': k, 'sigue_pct': round(100 * (1 - para_k[k] / tot_k[k]), 1),
                                 'n': tot_k[k]} for k in range(1, 13) if tot_k[k]],
        'distribucion': {str(n): dist[n] for n in sorted(dist)},
        'comisiones': sorted(per_com, key=lambda x: -x['mediana_agend']),
        'totales': {'proyectos': sum(c['proyectos'] for c in per_com),
                    'sesiones': sum(c['sesiones'] for c in per_com),
                    'comisiones': len(per_com)},
    }
    out = {'v': '2026-07-11', 'fuente': 'Cámara · órdenes del día (wp-json)',
           'sistema': sistema, 'por_proyecto': por_proy}
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
    kb = OUT.stat().st_size / 1024
    print(f'bloqueo.json · {len(por_proy)} proyectos · {len(per_com)} comisiones · {kb:.0f} KB')
    print(f'→ {OUT.relative_to(REPO)}')
    print('subir: aws s3 cp "%s" s3://caudal-legislativo/metadata/bloqueo.json' % OUT)


if __name__ == '__main__':
    main()
