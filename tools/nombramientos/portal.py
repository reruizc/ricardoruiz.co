#!/usr/bin/env python3
"""Datos del portal de contratación (contratistas.html): solo agregados, ningún nombre ni cédula.

Universo = el de la medición v2: gobierno nacional (Rama Ejecutiva), contratos de prestación de
servicios por contratación directa con persona natural (cédula). Las CAR van aparte, como cifra suelta.

  · VIGENTE al corte = inicio ≤ corte ≤ fin real (fin de SECOP, recortado por una terminación anticipada
    aprobada en modificaciones). SECOP no cierra los contratos solos, así que esto es un techo.
  · COHORTE = gobierno del PRIMER contrato de la persona con el gobierno nacional (cualquier tipo, SECOP I
    desde 2008 + SECOP II). «Nuevo» = su primer contrato es de este gobierno. Igual que analisis.py.
  · NIVEL = cómo tipificó la entidad el servicio en el objeto del contrato (nivel.py). No es la formación
    de la persona: SECOP no la publica.
  · HONORARIO MENSUAL = valor ÷ duración × 30,44, contratos de 15 a 730 días.
Uso:  python3 tools/nombramientos/portal.py [--corte AAAA-MM-DD]
Sale: contratistas/datos.json (lo sirve GitHub Pages junto a la página)
"""
import collections, datetime as dt, json, os, pickle, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nacion import D, ROOT, gobierno
from finreal import fin_real
from nivel import nivel, NIVELES

CORTE = sys.argv[sys.argv.index('--corte') + 1] if '--corte' in sys.argv else dt.date.today().isoformat()
POSESION = '2026-08-07'
COHORTES = ['Uribe o antes', 'Santos', 'Duque', 'Petro', 'Nuevo con este gobierno']
RANGOS = [(0, 3e6, 'Menos de 3 M'), (3e6, 5e6, '3 a 5 M'), (5e6, 8e6, '5 a 8 M'), (8e6, 12e6, '8 a 12 M'),
          (12e6, 1e15, 'Más de 12 M')]
SIN_H = 'Sin honorario calculable'
TOP_SECTORES = 9


def d(s):
    return dt.date.fromisoformat(s)


def honorario(r):
    if not (r['ini'] and r['fin']) or r['valor'] <= 0:
        return None
    dias = (d(r['fin']) - d(r['ini'])).days + 1
    return r['valor'] / dias * 30.44 if 15 <= dias <= 730 else None


def rango(h):
    if h is None:
        return SIN_H
    for a, b, l in RANGOS:
        if a <= h < b:
            return l


def coh(f1):
    if f1 >= POSESION:
        return 'Nuevo con este gobierno'
    g = gobierno(f1)
    return g if g in ('Santos', 'Duque', 'Petro') else 'Uribe o antes'


def med(xs):
    return round(st.median(xs)) if xs else None


def main():
    M = pickle.load(open(os.path.join(D, 'maestra.pkl'), 'rb'))
    filas = [dict(zip(M['cols'], f)) for f in M['filas']]
    nac = [r for r in filas if r['cat'] == 'nacional' and r['firma'] and r['firma'] >= '2008-01-01' and r['ced']]
    car = [r for r in filas if r['cat'] == 'car' and r['ops'] and r['firma']]
    primero = {}
    for r in nac:
        if r['ced'] not in primero or r['firma'] < primero[r['ced']]:
            primero[r['ced']] = r['firma']
    ops = [r for r in nac if r['ops'] and r['firma'] <= CORTE]
    for r in ops:
        r['fin_r'] = fin_real(r, CORTE) if r['fin'] else None

    vig = [r for r in ops if r['ini'] and r['fin_r'] and r['ini'] <= CORTE <= r['fin_r']]
    dle = [r for r in ops if POSESION <= r['firma'] <= CORTE]

    sector_cnt = collections.Counter(r['sector'] for r in vig)
    top = [s for s, _ in sector_cnt.most_common(TOP_SECTORES)]
    sec = lambda s: s if s in top else 'Otros sectores'

    def bloque(rs):
        """Un universo de contratos → resumen, Sankey de origen (personas) y Sankey de nivel (contratos)."""
        por_p = {}
        for r in sorted(rs, key=lambda r: r['firma']):
            por_p[r['ced']] = r          # el contrato más reciente de la persona manda el sector
        o = collections.Counter((coh(primero[c]), sec(r['sector'])) for c, r in por_p.items())
        hs = [(r, honorario(r)) for r in rs]
        n = collections.Counter((nivel(r['objeto']), rango(h)) for r, h in hs)
        hn = collections.defaultdict(list)
        for r, h in hs:
            if h:
                hn[nivel(r['objeto'])].append(h)
        cn = collections.Counter(coh(primero[c]) for c in por_p)
        return {
            'contratos': len(rs), 'personas': len(por_p), 'entidades': len({r['nit'] for r in rs}),
            'valor_total': round(sum(r['valor'] for r in rs)),
            'honorario_mediana': med([h for _, h in hs if h]),
            'cohorte': {k: cn[k] for k in COHORTES},
            'origen': [[a, b, v] for (a, b), v in sorted(o.items(), key=lambda x: -x[1])],
            'nivel': [[a, b, v] for (a, b), v in sorted(n.items(), key=lambda x: -x[1])],
            'nivel_honorario_mediana': {k: med(v) for k, v in hn.items()},
        }

    V, N = bloque(vig), bloque(dle)
    V['valor_mensual'] = round(sum(h for h in (honorario(r) for r in vig) if h))

    # ritmo de firma por semana desde el 7-ago, este año contra los mismos días de 2025 y 2022
    def semanas(Y):
        w0 = dt.date(Y, 8, 7); fin = dt.date(Y, d(CORTE).month, d(CORTE).day)
        c = collections.Counter()
        for r in nac:
            if r['ops'] and str(Y) == r['firma'][:4]:
                f = d(r['firma'])
                if w0 <= f <= fin:
                    c[(f - w0).days // 7] += 1
        return [c[i] for i in range((fin - w0).days // 7 + 1)]
    ritmo = {str(Y): semanas(Y) for Y in (2026, 2025, 2022)}

    # sectores: vigentes, firmados por este gobierno, cohorte y honorario
    S = collections.defaultdict(lambda: {'vig': set(), 'dle': set(), 'coh': collections.Counter(), 'h': []})
    for r in vig:
        x = S[r['sector']]; x['vig'].add(r['ced']); x['h'].append(honorario(r))
    for r in dle:
        S[r['sector']]['dle'].add(r['ced'])
    for s, x in S.items():
        for c in x['vig']:
            x['coh'][coh(primero[c])] += 1
    sectores = sorted(({'sector': s, 'vigentes': len(x['vig']), 'nuevos_contratos_dle': len(x['dle']),
                        **{f'pct_{k}': round(x['coh'][k] / max(1, len(x['vig'])), 4) for k in COHORTES},
                        'honorario_mediana': med([h for h in x['h'] if h])}
                       for s, x in S.items()), key=lambda z: -z['vigentes'])

    arr = None
    p = os.path.join(D, f'resultados-al-{CORTE[5:]}.json')
    if os.path.exists(p):
        R = json.load(open(p))['arranques']
        arr = {Y: {k: b[k] for k in ('gobierno', 'ventana', 'contratos_firmados', 'personas_contratadas',
                                     'personas_misma_ventana_anio_anterior', 'variacion_vs_anio_anterior',
                                     'cohorte_pct', 'con_contrato_12m_previos_pct', 'tasa_renovacion_misma_entidad',
                                     'salidas_contratos', 'salientes_personas', 'honorario_mensual')}
               for Y, b in R.items()}

    car_dle = [r for r in car if POSESION <= r['firma'] <= CORTE]
    out = {'corte': CORTE, 'generado': dt.date.today().isoformat(), 'posesion': POSESION,
           'definiciones': __doc__, 'cohortes': COHORTES, 'niveles': NIVELES,
           'rangos': [l for _, _, l in RANGOS] + [SIN_H],
           'vigentes': V, 'este_gobierno': N, 'ritmo_semanal': ritmo, 'sectores': sectores, 'arranques': arr,
           'car_aparte': {'contratos_este_gobierno': len(car_dle), 'personas_este_gobierno': len({r['ced'] for r in car_dle})}}
    dst = os.path.join(ROOT, 'contratistas', 'datos.json')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    json.dump(out, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if not isinstance(vv, list)})
                      for k, v in out.items() if k in ('corte', 'vigentes', 'este_gobierno', 'car_aparte')},
                     ensure_ascii=False, indent=1))
    print(f'→ {dst} · {os.path.getsize(dst) // 1024} KB')


if __name__ == '__main__':
    main()
