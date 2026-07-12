#!/usr/bin/env python3
"""
Caudal · Fase 3 — análisis de bloqueo NACIONAL (agrega las 14 comisiones).

Lee todos los agendamientos-{com}.json y produce:
  - P(tratado | posición) agregada de todas las comisiones.
  - Ranking de comisiones por "cementerio" (mediana de agendamientos, % 1º tratado).
  - Top proyectos más agendados sin resolver de todo el Congreso (Cámara).

Uso: python3 tools/caudal/actas/analiza_nacional.py
"""
import json, datetime
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parents[3]
CACHE = REPO / 'Bases de datos' / 'leyes-senado' / 'actas'
GAP_MAX = 45
BUCKETS = [(1, 1, '1º'), (2, 3, '2º-3º'), (4, 6, '4º-6º'),
           (7, 10, '7º-10º'), (11, 15, '11º-15º'), (16, 9999, '16º+')]


def d(s):
    return datetime.date.fromisoformat(s)


def stats_com(idx):
    """Devuelve (buckets[label]->[tratados,total], mediana_veces, rows)."""
    sesiones = defaultdict(list)
    for tok, info in idx.items():
        for f, p in zip(info['fechas'], info['posiciones']):
            sesiones[f].append((p, tok))
    fechas = sorted(sesiones)
    toks_f = {f: {t for _, t in sesiones[f]} for f in fechas}
    nxt = {fechas[i]: fechas[i + 1] for i in range(len(fechas) - 1)
           if (d(fechas[i + 1]) - d(fechas[i])).days <= GAP_MAX}
    perseguido = {t for t, i in idx.items() if i['n'] >= 2}
    b = {lab: [0, 0] for _, _, lab in BUCKETS}
    for f in fechas:
        if f not in nxt:
            continue
        after = toks_f[nxt[f]]
        for pos, tok in sesiones[f]:
            if tok not in perseguido:
                continue
            tr = tok not in after
            for lo, hi, lab in BUCKETS:
                if lo <= pos <= hi:
                    b[lab][0] += tr; b[lab][1] += 1
                    break
    ns = sorted(i['n'] for i in idx.values() if i['n'] >= 2)
    med = ns[len(ns) // 2] if ns else 0
    return b, med


def main():
    files = sorted(CACHE.glob('agendamientos-*.json'))
    nat = {lab: [0, 0] for _, _, lab in BUCKETS}
    top = []
    per_com = []
    for f in files:
        com = f.stem.replace('agendamientos-', '')
        data = json.load(open(f, encoding='utf-8'))
        idx = data['agendamientos']
        if not idx:
            continue
        b, med = stats_com(idx)
        for lab in nat:
            nat[lab][0] += b[lab][0]; nat[lab][1] += b[lab][1]
        p1 = round(100 * b['1º'][0] / b['1º'][1], 1) if b['1º'][1] else 0
        per_com.append({'com': com, 'proyectos': len(idx),
                        'sesiones': data.get('n_sesiones_con_proyectos', 0),
                        'mediana_agend': med, 'pct_1o_tratado': p1})
        for tok, info in idx.items():
            if info['n'] >= 8:
                top.append({'com': com, 'tok': tok, 'n': info['n'],
                            'titulo': info['titulo'], 'ultima': info['ultima']})

    print(f"\n=== BLOQUEO NACIONAL · {len(per_com)} comisiones de Cámara ===")
    tot_proy = sum(c['proyectos'] for c in per_com)
    print(f"{tot_proy} proyectos-comisión agendados · {sum(c['sesiones'] for c in per_com)} sesiones\n")

    print("P(tratado | posición) agregada:")
    for lo, hi, lab in BUCKETS:
        tr, tot = nat[lab]
        pct = round(100 * tr / tot, 1) if tot else 0
        print(f"   {lab:>7}  {pct:>5}%  {'█' * int(pct / 4)}  (n={tot})")

    print("\nComisiones por 'cementerio' (mediana de veces agendado · % 1º tratado):")
    for c in sorted(per_com, key=lambda x: -x['mediana_agend']):
        print(f"   {c['com']:<13} {c['proyectos']:>4} proy · mediana {c['mediana_agend']:>2}× · 1º tratado {c['pct_1o_tratado']:>5}%")

    print("\nTop proyectos más agendados de todo el Congreso (Cámara):")
    for r in sorted(top, key=lambda x: -x['n'])[:15]:
        print(f"   {r['n']:>3}×  {r['com']:<10} {r['tok']:>8}  {(r['titulo'] or '(sin título)')[:44]}")

    out = {'p_tratado_nacional': {lab: {'pct': round(100 * nat[lab][0] / nat[lab][1], 1) if nat[lab][1] else 0,
                                        'n': nat[lab][1]} for _, _, lab in BUCKETS},
           'comisiones': per_com,
           'top_agendados': sorted(top, key=lambda x: -x['n'])[:60]}
    json.dump(out, open(CACHE / 'bloqueo-nacional.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f"\n→ {(CACHE / 'bloqueo-nacional.json').relative_to(REPO)}")


if __name__ == '__main__':
    main()
