#!/usr/bin/env python3
"""
Caudal · Fase 3 (piloto) — análisis de bloqueo desde los órdenes del día.

Lee agendamientos-{com}.json (de harvest_ordenes.py) y computa, SOLO con la
secuencia de órdenes del día (sin actas):

  1. Proyectos más agendados que NO se resolvieron (bloqueo): cuántas veces
     los pusieron en el orden del día sin que avanzaran.
  2. P(tratado | posición): "si eres el proyecto Nº X del día, tu probabilidad
     de que te traten es Y%". Proxy de 'tratado' = NO reaparece en la sesión
     siguiente (se resolvió/salió de la agenda); si reaparece, no se alcanzó.

Uso: python3 tools/caudal/actas/analiza_bloqueo.py primera
"""
import json, sys, datetime
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parents[3]
CACHE = REPO / 'Bases de datos' / 'leyes-senado' / 'actas'
GAP_MAX = 45   # días: si la sesión siguiente está más lejos, no se cuenta (hueco de legislatura)


def d(s):
    return datetime.date.fromisoformat(s)


def main():
    com = sys.argv[1] if len(sys.argv) > 1 else 'primera'
    data = json.load(open(CACHE / f'agendamientos-{com}.json', encoding='utf-8'))
    idx = data['agendamientos']

    # reconstruye sesiones: fecha → [(pos, tok)]
    sesiones = defaultdict(list)
    for tok, info in idx.items():
        for f, p in zip(info['fechas'], info['posiciones']):
            sesiones[f].append((p, tok))
    fechas = sorted(sesiones)
    toks_por_fecha = {f: {t for _, t in sesiones[f]} for f in fechas}
    next_of = {}
    for i, f in enumerate(fechas):
        if i + 1 < len(fechas) and (d(fechas[i + 1]) - d(f)).days <= GAP_MAX:
            next_of[f] = fechas[i + 1]

    # --- 2) P(tratado | posición) ---
    buckets = [(1, 1, '1º'), (2, 3, '2º-3º'), (4, 6, '4º-6º'),
               (7, 10, '7º-10º'), (11, 15, '11º-15º'), (16, 9999, '16º+')]
    stat = {b[2]: [0, 0] for b in buckets}   # label → [tratados, total]
    per_pos = defaultdict(lambda: [0, 0])
    # solo proyectos REALMENTE perseguidos (agendados ≥2 veces): un proyecto
    # mencionado una sola vez "no reaparece" pero no fue tratado — contamina.
    perseguido = {t for t, i in idx.items() if i['n'] >= 2}
    for f in fechas:
        nf = next_of.get(f)
        if not nf:
            continue
        nxt = toks_por_fecha[nf]
        for pos, tok in sesiones[f]:
            if tok not in perseguido:
                continue
            tratado = tok not in nxt          # no reaparece = se resolvió
            for lo, hi, lab in buckets:
                if lo <= pos <= hi:
                    stat[lab][0] += tratado; stat[lab][1] += 1
                    break
            per_pos[pos][0] += tratado; per_pos[pos][1] += 1

    # --- 1) bloqueo: agendados sin resolverse ---
    ult = fechas[-1] if fechas else None
    rows = []
    for tok, info in idx.items():
        # "sigue vivo/atascado" si su última aparición está entre las 6 sesiones finales
        stuck = info['ultima'] in fechas[-6:]
        rows.append({'tok': tok, 'n': info['n'], 'titulo': info['titulo'],
                     'primera': info['primera'], 'ultima': info['ultima'],
                     'pos_prom': round(sum(info['posiciones']) / len(info['posiciones']), 1),
                     'stuck': stuck})
    rows.sort(key=lambda r: -r['n'])
    reag = [r for r in rows if r['n'] >= 2]
    ns = sorted(r['n'] for r in reag)
    mediana = ns[len(ns) // 2] if ns else 0

    print(f"\n=== BLOQUEO · Comisión {com.title()} ===")
    print(f"{data['n_sesiones_con_proyectos']} sesiones con proyectos · "
          f"{data['n_proyectos_agendados']} proyectos distintos agendados")
    print(f"Re-agendados (≥2 veces): {len(reag)} · mediana de veces agendado: {mediana}")
    print("\n1) Más agendados sin resolverse (⚠ = seguía en agenda al cierre):")
    for r in rows[:14]:
        w = ' ⚠' if r['stuck'] else ''
        print(f"  {r['n']:>3}×  posprom {r['pos_prom']:>4}  {r['titulo'][:50]:<50}{w}")

    print("\n2) P(tratado | posición en el orden del día):")
    print("   (proxy: 'tratado' = no reaparece la sesión siguiente)")
    for lo, hi, lab in buckets:
        tr, tot = stat[lab]
        pct = round(100 * tr / tot, 1) if tot else 0
        bar = '█' * int(pct / 4)
        print(f"   {lab:>7}  {pct:>5}%  {bar}  (n={tot})")

    out = {'comision': com,
           'p_tratado_por_posicion': {lab: {'pct': round(100 * stat[lab][0] / stat[lab][1], 1) if stat[lab][1] else 0,
                                            'n': stat[lab][1]} for _, _, lab in buckets},
           'mediana_veces_agendado': mediana,
           'bloqueados': rows[:60]}
    outf = CACHE / f'bloqueo-{com}.json'
    json.dump(out, open(outf, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"\n→ {outf.relative_to(REPO)}")


if __name__ == '__main__':
    main()
