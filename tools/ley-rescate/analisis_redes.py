#!/usr/bin/env python3
"""Temas de la Ley de Rescate en prensa y en redes, por semana, y quién lleva la conversación digital.

Uso: python3 tools/ley-rescate/analisis_redes.py <dir con corpus.json y clasif.json>
Salida: imprime el resumen y deja <dir>/analisis-redes.json para el onepager.
Semana 1 = radicación hasta el 4-nov · semana 2 = 5-nov en adelante (Colombia, UTC-5).
"""
import collections
import datetime as dt
import json
import math
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
D = Path(sys.argv[1])
corpus = json.loads((D / 'corpus.json').read_text())
clas = json.loads((D / 'clasif.json').read_text())
TEMAS = {t['id']: t['nombre'] for t in json.loads((AQUI / 'temas.json').read_text())['temas']}
TEMAS['general'] = 'La ley en conjunto'
REDES = {'x', 'tiktok', 'instagram', 'facebook'}
CORTE = dt.datetime(2026, 11, 5, 5, tzinfo=dt.timezone.utc)   # 5-nov 00:00 en Colombia
INI = dt.datetime(2026, 10, 29, 5, tzinfo=dt.timezone.utc)


def fecha(v):
    try:
        return dt.datetime.fromisoformat((v.get('pub') or '').replace('Z', '+00:00'))
    except ValueError:
        return None


filas = []
for k, v in corpus.items():
    c = clas.get(k)
    f = fecha(v)
    if not c or not c.get('rel') or not f or f < INI:
        continue
    fuente = 'redes' if v['f'] in REDES else 'prensa'
    sem = 1 if f < CORTE else 2
    # En redes pesa la interacción (log, para que un viral no borre todo lo demás); en prensa, cada titular cuenta 1.
    w = 1 + math.log1p(max(0, v.get('inter') or 0)) if fuente == 'redes' else 1
    filas.append({'k': k, 'fuente': fuente, 'red': v['f'], 'sem': sem, 'w': w, 't': c.get('t') or [], 'v': c.get('v'),
                  'autor': v.get('autor') or '', 'inter': max(0, v.get('inter') or 0), 'txt': v['txt'], 'url': v.get('url') or '',
                  'pub': v.get('pub'), 'tipo': v.get('tipo') or ''})

print('Textos pertinentes desde la radicación:', len(filas))
print(collections.Counter((r['fuente'], r['sem']) for r in filas))
print(collections.Counter(r['red'] for r in filas if r['fuente'] == 'redes'))


def reparto(fuente, sem, sin_general=True):
    tot = collections.Counter()
    pos = collections.defaultdict(collections.Counter)
    for r in filas:
        if r['fuente'] != fuente or (sem and r['sem'] != sem):
            continue
        ts = [t for t in r['t'] if not (sin_general and t[0] == 'general')]
        for tema, p in ts:
            tot[tema] += r['w'] / len(ts)
            pos[tema][p] += r['w'] / len(ts)
    s = sum(tot.values()) or 1
    return {t: round(100 * n / s, 1) for t, n in tot.most_common()}, pos


out = {'n': collections.Counter(f"{r['fuente']}{r['sem']}" for r in filas)}
for fuente in ('prensa', 'redes'):
    for sem in (1, 2):
        rep, pos = reparto(fuente, sem)
        out[f'{fuente}{sem}'] = rep
        out[f'{fuente}{sem}_pos'] = {t: {p: round(n, 1) for p, n in c.items()} for t, c in pos.items()}
        print(f'\n{fuente} semana {sem}:', ', '.join(f'{TEMAS.get(t, t)} {p}%' for t, p in list(rep.items())[:9]))

for fuente in ('prensa', 'redes'):
    rep, pos = reparto(fuente, None)
    out[fuente] = rep
    out[f'{fuente}_pos'] = {t: {p: round(n, 1) for p, n in c.items()} for t, c in pos.items()}

# Postura en redes, sin el tema: ¿a favor o en contra de la ley?
for fuente in ('prensa', 'redes'):
    for sem in (1, 2):
        c = collections.Counter()
        for r in filas:
            if r['fuente'] == fuente and r['sem'] == sem:
                for _, p in r['t']:
                    c[p] += r['w'] / max(1, len(r['t']))
        s = sum(c.values()) or 1
        out[f'tono_{fuente}{sem}'] = {p: round(100 * n / s, 1) for p, n in c.items()}
        print(f'tono {fuente} {sem}:', out[f'tono_{fuente}{sem}'])

# Quién lleva la conversación: cuentas públicas (las únicas con nombre en el corpus), por interacción total.
au = collections.defaultdict(lambda: {'inter': 0, 'n': 0, 'p': collections.Counter(), 'red': collections.Counter(), 'v': collections.Counter(), 'top': None})
for r in filas:
    if r['fuente'] != 'redes' or not r['autor']:
        continue
    a = au[r['autor']]
    a['inter'] += r['inter']
    a['n'] += 1
    a['red'][r['red']] += 1
    a['v'][r['v']] += 1
    for _, p in r['t']:
        a['p'][p] += (r['inter'] + 1) / max(1, len(r['t']))
    if not a['top'] or r['inter'] > a['top']['inter']:
        a['top'] = {'inter': r['inter'], 'txt': r['txt'][:280], 'url': r['url'], 'pub': r['pub'], 'red': r['red']}
lider = []
for nombre, a in au.items():
    tot = sum(a['p'].values()) or 1
    fav, con = a['p']['a'] / tot, (a['p']['r'] + 0.5 * a['p']['m']) / tot
    lado = 'favor' if fav > 0.5 else 'contra' if con > 0.5 else 'mixto'
    lider.append({'autor': nombre, 'inter': a['inter'], 'n': a['n'], 'lado': lado, 'fav': round(fav, 2), 'con': round(con, 2),
                  'red': a['red'].most_common(1)[0][0], 'v': a['v'].most_common(1)[0][0], 'top': a['top']})
lider.sort(key=lambda x: -x['inter'])
out['lideres'] = lider[:60]
for lado in ('favor', 'contra', 'mixto'):
    print(f'\nTop {lado}:')
    for x in [l for l in lider if l['lado'] == lado][:6]:
        print(f"  {x['autor']:<22} {x['inter']:>8} inter · {x['n']} textos · {x['red']} · {x['v']} · «{x['top']['txt'][:120]}»")

(D / 'analisis-redes.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))
print('\n→', D / 'analisis-redes.json')
