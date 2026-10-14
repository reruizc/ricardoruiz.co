#!/usr/bin/env python3
"""Capa X de una batalla · cuentas, velocidad y nodos de dispersión vía Apify.

  python3 tools/batalla/x_capa.py marcha-14oct-2026              # ENSAYO: consultas y costo, no gasta
  python3 tools/batalla/x_capa.py marcha-14oct-2026 --gastar     # trae publicaciones (cuesta)

Reusa el actor, el freno de gasto y la normalización de la escucha de Caudal
(`tools/caudal/redes/escucha_perfil.py`): ~US$0,22 por 1.000 publicaciones, piso
de ~64 por consulta. Con las 6 consultas de la marcha son ~400 publicaciones por
corrida ≈ US$0,09. El tope por corrida es TOPE_TOTAL.

Escribe `Bases de datos/batalla/<id>/x.json`; `batalla.py` lo lee y lo publica en
la sección 13 del tablero. Las publicaciones se clasifican con el MISMO libro de
códigos que los titulares (marcos y voz), así que el marcador de X es comparable:
N = cuentas distintas que llevan el marco del bando, q = interacción media
normalizada (log).
"""
import argparse
import datetime as dt
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parents[1]
sys.path.insert(0, str(REPO / 'tools' / 'caudal' / 'redes'))
sys.path.insert(0, str(AQUI))
import escucha_perfil as ep          # noqa: E402  actor, freno, normalización
import batalla as bt                 # noqa: E402  libro de códigos, clasificador

TOPE_TOTAL = 450


def consultas(cfg):
    desde = dt.datetime.fromisoformat(cfg['inicio']).date().isoformat()
    return [{'tema': c['tema'], 'q': f"{c['q']} lang:es -filter:retweets since:{desde}"} for c in cfg.get('consultas_x', [])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('batalla')
    ap.add_argument('--gastar', action='store_true')
    a = ap.parse_args()
    cfg = json.loads((AQUI / 'batallas' / f'{a.batalla}.json').read_text())
    carpeta = bt.DATOS / cfg['id']
    carpeta.mkdir(parents=True, exist_ok=True)
    qs = consultas(cfg)
    estimado = min(TOPE_TOTAL, len(qs) * ep.POR_CONSULTA)
    print(f'[x] {len(qs)} consultas · ~{estimado} publicaciones · ~US${estimado * ep.PRECIO_1K / 1000:.2f} por corrida')
    for q in qs:
        print('   ', q['q'])
    tok = ep.token()
    if not a.gastar or not tok:
        print('[x] ENSAYO: no se gastó nada' + ('' if tok else ' (sin APIFY_TOKEN)'))
        return

    f_corpus = carpeta / 'x-corpus.json'
    corpus = json.loads(f_corpus.read_text()) if f_corpus.exists() else {}
    entrada = {'searchTerms': [q['q'] for q in qs], 'maxItems': 40, 'sort': 'Latest'}
    items, usd, run_id = ep.correr(tok, entrada)
    pubs, descartes = ep.normalizar(items, qs, solo_colombia=True)
    nuevos = 0
    for p in pubs:
        if p['id'] not in corpus:
            corpus[p['id']] = p
            nuevos += 1
        else:
            corpus[p['id']].update({k: p[k] for k in ('likes', 'rts', 'respuestas', 'citas', 'vistas', 'interaccion')})
    f_corpus.write_text(json.dumps(corpus, ensure_ascii=False))
    print(f'[x] {len(items)} ítems · {nuevos} nuevas · corpus {len(corpus)} · US${usd or 0:.3f} · {descartes}')

    # clasificar con el libro de códigos (el texto hace de titular)
    pseudo = {k: {'titulo': v['texto'][:280], 'medio': '@' + v['autor']} for k, v in corpus.items()}
    # caché aparte para X: no se mezcla con la de titulares
    tmp = carpeta / 'x-clas'
    tmp.mkdir(exist_ok=True)
    lab, _ = bt.clasificar_llm(cfg, pseudo, tmp, bt.deepseek_key())
    marcos = {m['id']: m['bando'] for m in cfg['marcos']}
    for k, v in corpus.items():
        x = lab.get(k) or {'rel': 0, 'm': [], 'h': 0, 'v': ''}
        v['c'] = {'rel': x['rel'], 'm': x['m'], 'v': x.get('v', ''),
                  'b': ''.join(sorted({marcos[m] for m in x['m'] if marcos.get(m) in 'GO'}))}
    rel = [v for v in corpus.values() if v['c']['rel']]

    def fuerza(b):
        cuentas = {}
        for v in rel:
            if b in v['c']['b']:
                cuentas[v['autor']] = max(cuentas.get(v['autor'], 0), v['interaccion'])
        n = len(cuentas)
        q = sum(math.log10(1 + i) for i in cuentas.values()) / n if n else 0
        return {'N': n, 'q': round(q, 2), 'F': round(n * n * q, 1)}
    fG, fO = fuerza('G'), fuerza('O')
    nodos = defaultdict(Counter)
    for v in rel:
        for b in v['c']['b'] or 'N':
            nodos[b][v['autor']] += v['interaccion']
    top = {b: [{'cuenta': c, 'interaccion': i} for c, i in cnt.most_common(10)] for b, cnt in nodos.items()}
    ritmo = Counter()
    for v in rel:
        if v['fecha']:
            t = dt.datetime.fromisoformat(v['fecha'] + ':00+00:00')
            ritmo[(t.replace(minute=t.minute // 15 * 15)).isoformat(timespec='minutes') + '|' + (v['c']['b'] or 'N')] += 1
    out = {'generado': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'), 'publicaciones': len(rel),
           'costo_usd': round(usd or 0, 3), 'G': fG, 'O': fO,
           'choque': sum(1 for v in rel if v['c']['b'] == 'GO'), 'nodos': top,
           'ritmo': [{'t': k.split('|')[0], 'b': k.split('|')[1], 'n': n} for k, n in sorted(ritmo.items())],
           'destacadas': [{k: v[k] for k in ('autor', 'texto', 'url', 'fecha', 'interaccion')} | {'b': v['c']['b']}
                          for v in sorted(rel, key=lambda v: -v['interaccion'])[:12]]}
    (carpeta / 'x.json').write_text(json.dumps(out, ensure_ascii=False))
    print(f"[x] Gobierno F={fG['F']} (N={fG['N']}) · Oposición F={fO['F']} (N={fO['N']})")


if __name__ == '__main__':
    main()
