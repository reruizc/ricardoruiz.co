#!/usr/bin/env python3
"""Agregado multi-año del reporte.json para el trino/post."""
import json
from statistics import mean, stdev

with open('reporte.json', encoding='utf-8') as f:
    rep = json.load(f)

# Para cada (delito, scope, dia), agregar observados y baselines de 2010+2014+2018+2022
agg = {}
for b in rep:
    y = b['year']
    for delito in ['homicidios', 'lesiones']:
        for scope in ['nacional', 'bogota']:
            d = b['detalle'][delito][scope]
            for r in d['dias']:
                key = (delito, scope, r['dia'])
                a = agg.setdefault(key, {'obs': [], 'base': [], 'std': [], 'n_base': []})
                a['obs'].append(r['cant'])
                a['base'].append(r['baseline_mean'])
                a['std'].append(r['baseline_std'])
                a['n_base'].append(r['baseline_n'])

print('AGREGADO 4 ELECCIONES (2010 + 2014 + 2018 + 2022)\n')
print(f'{"delito":<10} {"scope":<8} {"día":<8} | obs Σ4yr | base Σ4yr | Δ%      | dispersión obs')
print('-' * 92)
for delito in ['homicidios', 'lesiones']:
    for scope in ['nacional', 'bogota']:
        for dia in ['viernes', 'sabado', 'domingo', 'lunes']:
            a = agg[(delito, scope, dia)]
            obs = sum(a['obs'])
            base = sum(a['base'])
            pct = (obs - base) / base * 100 if base else 0
            disp = f"{min(a['obs'])}–{max(a['obs'])}"
            print(f'{delito:<10} {scope:<8} {dia:<8} | {obs:>8} | {base:>9.1f} | {pct:>+6.1f}% | {disp}')
        # fin semana total
        obs_w = sum(sum(agg[(delito, scope, d)]['obs']) for d in ['sabado', 'domingo', 'lunes'])
        base_w = sum(sum(agg[(delito, scope, d)]['base']) for d in ['sabado', 'domingo', 'lunes'])
        pct_w = (obs_w - base_w) / base_w * 100 if base_w else 0
        print(f'{delito:<10} {scope:<8} sáb+dom+lun (con ley seca histórica) | obs {obs_w}  base {base_w:.1f}  Δ {pct_w:+.1f}%')
        # viernes solo
        a = agg[(delito, scope, 'viernes')]
        obs_v = sum(a['obs'])
        base_v = sum(a['base'])
        pct_v = (obs_v - base_v) / base_v * 100 if base_v else 0
        print(f'{delito:<10} {scope:<8} VIERNES (SIN ley seca histórica) ----- | obs {obs_v}  base {base_v:.1f}  Δ {pct_v:+.1f}%')
        print()
