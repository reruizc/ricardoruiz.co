#!/usr/bin/env python3
"""Arranques de gobierno comparados: Duque 2018 · Petro 2022 · De La Espriella 2026.

Ventana = 7-ago a 7-oct del año de cada posesión (los dos primeros meses), sobre la tabla maestra.
`--cierre MM-DD` corre la misma comparación con otro cierre para los tres años (p.ej. 10-27); con un
cierre distinto del 7-oct las salidas llevan sufijo (resultados-al-10-27.json, por-*-{año}-al-10-27.csv).
Universo: SOLO gobierno nacional (Rama Ejecutiva); CAR aparte. Contratista = OPS (prestación de
servicios por contratación directa) con persona natural.

Definiciones (decisiones de Ricardo, 20-oct-2026):
  · COHORTE = gobierno del PRIMER contrato de la persona con el gobierno nacional (cualquier tipo,
    cualquier entidad del universo, SECOP I desde 2008 + SECOP II). Quien entró en 2021 es cohorte Duque
    aunque haya seguido con Petro. Lo anterior a 2008 no se ve: «Uribe» es un piso.
  · ANTIGÜEDAD = años entre ese primer contrato y el 7-ago de la posesión.
  · COHORTE EN LA ENTIDAD = lo mismo, pero contando solo la entidad que lo contrata ahora.
  · HONORARIO MENSUAL = valor ÷ duración (inicio→fin) × 30,44, solo contratos de 15 a 730 días.
  · SALIDA = contrato OPS firmado ANTES de la posesión cuyo fin cae en la ventana.
      renovado  = la misma cédula firma con la MISMA entidad entre (fin − 30 días) y el cierre de la ventana.
      reubicado = no renueva ahí pero firma con OTRA entidad nacional en ese lapso.
      afuera    = no firma nada con el gobierno nacional en ese lapso.
Sale: v2/resultados.json · v2/por-entidad-{año}.csv · v2/por-sector-{año}.csv
"""
import bisect, collections, csv, datetime as dt, json, os, pickle, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nacion import D, gobierno
from finreal import fin_real, terminaciones

POSESIONES = {2018: 'Duque', 2022: 'Petro', 2026: 'De La Espriella'}
CIERRE = sys.argv[sys.argv.index('--cierre') + 1] if '--cierre' in sys.argv else '10-07'
SUF = '' if CIERRE == '10-07' else f'-al-{CIERRE}'
ORDEN_COH = ['Antes de 2002', 'Uribe', 'Santos', 'Duque', 'Petro', 'De La Espriella']


def d(s):
    return dt.date.fromisoformat(s)


def mediana(xs):
    return round(st.median(xs), 2) if xs else None


def media(xs):
    return round(sum(xs) / len(xs), 2) if xs else None


def honorario(r):
    if not (r['ini'] and r['fin']) or r['valor'] <= 0:
        return None
    dias = (d(r['fin']) - d(r['ini'])).days + 1
    return r['valor'] / dias * 30.44 if 15 <= dias <= 730 else None


def cargar():
    M = pickle.load(open(os.path.join(D, 'maestra.pkl'), 'rb'))
    C = M['cols']
    filas = [dict(zip(C, f)) for f in M['filas']]
    return filas


def main():
    filas = cargar()
    E = json.load(open(os.path.join(D, 'entidades.json')))
    nac = [r for r in filas if r['cat'] == 'nacional' and r['firma'] and r['firma'] >= '2008-01-01' and r['ced']]
    por_ced = collections.defaultdict(list)
    for r in nac:
        por_ced[r['ced']].append(r)
    for v in por_ced.values():
        v.sort(key=lambda r: r['firma'])
    primero = {c: v[0]['firma'] for c, v in por_ced.items()}
    primero_ent = {}
    for c, v in por_ced.items():
        for r in v:
            primero_ent.setdefault((c, r['nit']), r['firma'])
    firmas_ops = collections.defaultdict(list)     # (ced) → [(firma, nit)] solo OPS, ordenado
    for c, v in por_ced.items():
        firmas_ops[c] = [(r['firma'], r['nit']) for r in v if r['ops']]

    res = {'generado': dt.date.today().isoformat(), 'cierre': CIERRE, 'definiciones': __doc__, 'arranques': {}}
    for Y, gob in POSESIONES.items():
        w0, w1 = f'{Y}-08-07', f'{Y}-{CIERRE}'
        y0 = dt.date(Y, 8, 7)
        # ---------- contrataciones de la ventana
        nuevos = [r for r in nac if r['ops'] and w0 <= r['firma'] <= w1 + 'T']
        nuevos = [r for r in nuevos if r['firma'] <= w1]
        prev = [r for r in nac if r['ops'] and f'{Y-1}-08-07' <= r['firma'] <= f'{Y-1}-{CIERRE}']
        personas = {}
        for r in nuevos:
            personas.setdefault(r['ced'], []).append(r)
        coh, coh_ent, ant, ant_ent, hon, previos_12m = collections.Counter(), collections.Counter(), [], [], [], 0
        filas_p, valor_p = [], []
        for c, rs in personas.items():
            f1 = primero[c]
            g = gobierno(f1) if f1 < w0 else 'nuevo'
            coh[g] += 1
            a = max(0.0, (y0 - d(f1)).days / 365.25)
            ant.append(a)
            r0 = rs[0]
            fe = primero_ent.get((c, r0['nit']))
            ge = gobierno(fe) if fe and fe < w0 else 'nuevo'
            coh_ent[ge] += 1
            ant_ent.append(max(0.0, (y0 - d(fe)).days / 365.25) if fe else 0.0)
            h = [x for x in (honorario(x) for x in rs) if x]
            if h:
                hon.append(sum(h) / len(h))
            hace12 = f'{Y-1}-08-07'
            if any(hace12 <= x['firma'] < w0 for x in por_ced[c]):
                previos_12m += 1
            filas_p.append((c, r0['nit'], g, ge, a, h[0] if h else None))
            valor_p.append((g == 'nuevo', sum(x['valor'] for x in rs), (sum(h) / len(h)) if h else None, r0['nit']))
        n = len(personas)

        def tramo(x):
            return '<1' if x < 1 else '1-2' if x < 2 else '2-4' if x < 4 else '4-8' if x < 8 else '8+'
        tramos = collections.Counter(tramo(a) for a in ant)
        # ---------- salidas
        sal = [r for r in nac if r['ops'] and r['firma'] < w0 and r['fin'] and w0 <= r['fin'] <= w1]
        est = collections.Counter()
        sal_por_ent = collections.defaultdict(collections.Counter)
        salientes = {}
        for r in sal:
            lim0 = (d(r['fin']) - dt.timedelta(days=30)).isoformat()
            fo = firmas_ops[r['ced']]
            i = bisect.bisect_left(fo, (lim0, ''))
            nuevas = [(f, nt) for f, nt in fo[i:] if f <= w1 and f > r['firma']]
            if any(nt == r['nit'] for _, nt in nuevas):
                k = 'renovado'
            elif nuevas:
                k = 'reubicado'
            else:
                k = 'afuera'
            est[k] += 1
            sal_por_ent[r['nit']][k] += 1
            if k == 'afuera':
                salientes[r['ced']] = r
        coh_sal, ant_sal = collections.Counter(), []
        for c, r in salientes.items():
            f1 = primero[c]
            coh_sal[gobierno(f1)] += 1
            ant_sal.append((y0 - d(f1)).days / 365.25)
        # ---------- stock por fechas
        def stock(fecha, real=False):
            return len({r['ced'] for r in nac if r['ops'] and r['ini'] and r['fin'] and r['ini'] <= fecha <=
                        (fin_real(r, w1) if real else r['fin'])})
        # ---------- terminaciones anticipadas (solo SECOP II: 2018 queda incompleto)
        T = terminaciones()
        vig = [r for r in nac if r['ops'] and r['src'] == 's2' and r['ini'] and r['fin'] and r['ini'] < w0 <= r['fin']]
        term = [(r, T[r['id']]) for r in vig if r['id'] in T and w0 <= T[r['id']]['aprobada'] <= w1]
        quien = collections.Counter(t['quien'] for _, t in term)
        term_ent = collections.Counter(r['nit'] for r, _ in term)
        RV = [(0, 10e6, 'menos de 10 M'), (10e6, 30e6, '10 a 30 M'), (30e6, 60e6, '30 a 60 M'), (60e6, 100e6, '60 a 100 M'),
              (100e6, 200e6, '100 a 200 M'), (200e6, 1e15, 'más de 200 M')]
        RH = [(0, 3e6, 'menos de 3 M'), (3e6, 5e6, '3 a 5 M'), (5e6, 8e6, '5 a 8 M'), (8e6, 12e6, '8 a 12 M'),
              (12e6, 20e6, '12 a 20 M'), (20e6, 1e15, 'más de 20 M')]

        def rangos(xs, R):
            n_ = max(1, len(xs))
            return {lbl: round(sum(a <= x < b for x in xs) / n_, 4) for a, b, lbl in R}

        def perfil(sel):
            vt = [v for nu, v, h, _ in valor_p if sel(nu)]
            hm = [h for nu, v, h, _ in valor_p if sel(nu) and h]
            return {'personas': len(vt), 'valor_total_mediana': round(mediana(vt)) if vt else None,
                    'valor_total_media': round(media(vt)) if vt else None, 'valor_total_suma': round(sum(vt)),
                    'honorario_mediana': round(mediana(hm)) if hm else None, 'honorario_media': round(media(hm)) if hm else None,
                    'rangos_valor_total': rangos(vt, RV), 'rangos_honorario': rangos(hm, RH)}
        ent_nuevos = collections.Counter(nit for nu, _, _, nit in valor_p if nu)
        nuevos_blk = {'nuevos': perfil(lambda nu: nu), 'ya_venian': perfil(lambda nu: not nu),
                      'top_entidades_nuevos': [(E[k]['nombre'], v, round(v / max(1, agg_ent_total[k]), 3))
                                               for k, v in ent_nuevos.most_common(15)] if False else None}
        bloque = {
            'gobierno': gob, 'ventana': [w0, w1],
            'contratos_firmados': len(nuevos), 'personas_contratadas': n,
            'personas_misma_ventana_anio_anterior': len({r['ced'] for r in prev}),
            'variacion_vs_anio_anterior': round(n / max(1, len({r['ced'] for r in prev})) - 1, 4),
            'cohorte': {k: coh[k] for k in ORDEN_COH + ['nuevo'] if coh[k]},
            'cohorte_pct': {k: round(coh[k] / n, 4) for k in ORDEN_COH + ['nuevo'] if coh[k]},
            'cohorte_en_la_entidad_pct': {k: round(coh_ent[k] / n, 4) for k in ORDEN_COH + ['nuevo'] if coh_ent[k]},
            'con_contrato_12m_previos_pct': round(previos_12m / n, 4),
            'antiguedad_anios': {'media': media(ant), 'mediana': mediana(ant), 'media_sin_nuevos': media([a for a in ant if a > 0]),
                                 'mediana_sin_nuevos': mediana([a for a in ant if a > 0])},
            'antiguedad_en_la_entidad_anios': {'media': media(ant_ent), 'mediana': mediana(ant_ent)},
            'antiguedad_tramos_pct': {k: round(tramos[k] / n, 4) for k in ['<1', '1-2', '2-4', '4-8', '8+']},
            'honorario_mensual': {'media': round(media(hon)) if hon else None, 'mediana': round(mediana(hon)) if hon else None, 'n': len(hon)},
            'salidas_contratos': len(sal), 'salidas': dict(est),
            'tasa_renovacion_misma_entidad': round(est['renovado'] / max(1, len(sal)), 4),
            'tasa_reemplazo': round(len(nuevos) / max(1, len(sal)) * 100, 1),
            'salientes_personas': len(salientes),
            'salientes_cohorte_pct': {k: round(coh_sal[k] / max(1, len(salientes)), 4) for k in ORDEN_COH if coh_sal[k]},
            'salientes_antiguedad': {'media': media(ant_sal), 'mediana': mediana(ant_sal),
                                     '4_o_mas_pct': round(sum(a >= 4 for a in ant_sal) / max(1, len(ant_sal)), 4)},
            'stock_personas': {w0: stock(w0), w1: stock(w1)},
            'nuevos_y_veteranos': nuevos_blk,
            'top_entidades_nuevos': [(E[k]['nombre'], v) for k, v in ent_nuevos.most_common(15)],
            'stock_personas_fin_real': {w0: stock(w0, True), w1: stock(w1, True)},
            'terminaciones_anticipadas': {'contratos': len(term), 'vigentes_al_inicio_secop2': len(vig),
                                          'por_mil_vigentes': round(1000 * len(term) / max(1, len(vig)), 1),
                                          'quien_pct': {k: round(v / max(1, len(term)), 3) for k, v in quien.items()},
                                          'top_entidades': [(E[k]['nombre'], v) for k, v in term_ent.most_common(12)],
                                          'completo': Y >= 2020},
        }
        res['arranques'][str(Y)] = bloque
        # ---------- por entidad y por sector
        agg = collections.defaultdict(lambda: {'personas': 0, 'coh': collections.Counter(), 'ant': [], 'hon': []})
        prev_ent = collections.Counter()
        for r in {(r['ced'], r['nit']): r for r in prev}.values():
            prev_ent[r['nit']] += 1
        for c, nit, g, ge, a, h in filas_p:
            x = agg[nit]; x['personas'] += 1; x['coh'][g] += 1; x['ant'].append(a)
            if h: x['hon'].append(h)
        for nombre_arch, llave in [('entidad', lambda nit: nit), ('sector', lambda nit: E[nit]['sector'])]:
            G = collections.defaultdict(lambda: {'personas': 0, 'coh': collections.Counter(), 'ant': [], 'hon': [], 'prev': 0,
                                                 'sal': collections.Counter()})
            nits = set(agg) | set(sal_por_ent) | set(prev_ent)
            for nit in nits:
                k = llave(nit); g = G[k]; a = agg.get(nit)
                if a:
                    g['personas'] += a['personas']; g['coh'] += a['coh']; g['ant'] += a['ant']; g['hon'] += a['hon']
                g['prev'] += prev_ent.get(nit, 0); g['sal'] += sal_por_ent.get(nit, collections.Counter())
            out = []
            for k, g in G.items():
                s = sum(g['sal'].values())
                if g['personas'] + s + g['prev'] < 20:
                    continue
                p = max(1, g['personas'])
                out.append({nombre_arch: E[k]['nombre'] if nombre_arch == 'entidad' else k,
                            **({'nit': k, 'sector': E[k]['sector']} if nombre_arch == 'entidad' else {}),
                            'contratados': g['personas'], 'contratados_anio_anterior': g['prev'],
                            'variacion': round(g['personas'] / g['prev'] - 1, 3) if g['prev'] else None,
                            'vencidos': s, 'renovados': g['sal']['renovado'], 'reubicados': g['sal']['reubicado'],
                            'salieron': g['sal']['afuera'],
                            'tasa_renovacion': round(g['sal']['renovado'] / s, 3) if s else None,
                            'tasa_reemplazo': round(g['personas'] / s * 100, 1) if s else None,
                            **{f'cohorte_{c.lower().replace(" ", "_")}': round(g['coh'][c] / p, 3)
                               for c in ['nuevo', 'Petro', 'Duque', 'Santos', 'Uribe']},
                            'antiguedad_media': media(g['ant']), 'antiguedad_mediana': mediana(g['ant']),
                            'honorario_mensual_mediana': round(mediana(g['hon'])) if g['hon'] else None})
            out.sort(key=lambda x: -(x['contratados'] + x['vencidos']))
            with open(os.path.join(D, f'por-{nombre_arch}-{Y}{SUF}.csv'), 'w', newline='', encoding='utf-8') as fh:
                if out:
                    w = csv.DictWriter(fh, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    json.dump(res, open(os.path.join(D, f'resultados{SUF}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for Y, b in res['arranques'].items():
        print(f"\n== {Y} {b['gobierno']} · {b['personas_contratadas']} personas ({b['variacion_vs_anio_anterior']:+.0%} vs año anterior)")
        print('  cohorte:', {k: f'{v:.1%}' for k, v in b['cohorte_pct'].items()})
        print('  cohorte en la entidad:', {k: f'{v:.1%}' for k, v in b['cohorte_en_la_entidad_pct'].items()})
        print('  antigüedad:', b['antiguedad_anios'], '· tramos', b['antiguedad_tramos_pct'])
        print('  honorario mensual:', b['honorario_mensual'])
        print(f"  salidas {b['salidas_contratos']} → {b['salidas']} · renovación misma entidad {b['tasa_renovacion_misma_entidad']:.1%} · reemplazo {b['tasa_reemplazo']}")
        print('  salientes cohorte:', {k: f'{v:.1%}' for k, v in b['salientes_cohorte_pct'].items()}, b['salientes_antiguedad'])
        nv = b['nuevos_y_veteranos']
        for k in ('nuevos', 'ya_venian'):
            x = nv[k]; print(f"  {k}: {x['personas']} · valor mediano {x['valor_total_mediana']} · honorario mediano {x['honorario_mediana']}")
            print('     valor', x['rangos_valor_total']); print('     honor', x['rangos_honorario'])
        print('  stock:', b['stock_personas'], '· con fin real:', b['stock_personas_fin_real'])
        print('  terminaciones:', {k: v for k, v in b['terminaciones_anticipadas'].items() if k != 'top_entidades'})
        print('    ', b['terminaciones_anticipadas']['top_entidades'][:8])


if __name__ == '__main__':
    main()
