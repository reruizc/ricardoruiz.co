#!/usr/bin/env python3
"""
Caudal · empaqueta el voto nominal de SENADO para S3 + Lambda.

Espejo de build_votaciones_camara_s3.py + build_congresista_s3.py, pero sobre
dist/votaciones-senado-api.jsonl (harvest_senado_api.py). Emite los DOS ejes con
el MISMO shape que Cámara, para que Lambda y frontend los consuman igual:

  metadata/votaciones-senado-nominal.json      por proyecto  (ficha del proyecto)
  metadata/votaciones-senado-congresista.json  por senador   (ficha de la persona)

Diferencias con Cámara, heredadas de la fuente (van en `meta`):
  · solo Sí/No — sin abstención ni "no votó";
  · la llave (fecha, ID Proyecto) agrupa varias votaciones del mismo día sobre el
    mismo proyecto, así que una "votación" aquí puede ser un bloque de ellas;
  · desde 2017.

Uso: python3 tools/caudal/build_votaciones_senado_s3.py
"""
import collections
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DIST = REPO / 'Bases de datos' / 'leyes-senado' / 'dist'
OUT = DIST / 's3'
SRC = DIST / 'votaciones-senado-api.jsonl'

MIN_VOTOS_PERSONA = 3      # igual que Cámara: menos de 3 votos no dice nada


def canon_bancada(p):
    """Misma taxonomía que Cámara para que las dos cámaras se puedan comparar."""
    p = (p or '').upper()
    if 'CENTRO DEMOCR' in p: return 'Centro Democrático'
    if 'CONSERVADOR' in p: return 'Conservador'
    if 'CAMBIO RADICAL' in p: return 'Cambio Radical'
    if 'DE LA U' in p or 'UNIÓN POR LA GENTE' in p or 'UNIDAD NACIONAL' in p: return 'La U'
    if 'LIBERAL' in p and 'NUEVO' not in p: return 'Liberal'
    if 'PACTO' in p or 'COLOMBIA HUMANA' in p or 'POLO' in p or 'COMUNES' in p \
       or 'MAIS' in p or 'PATRI' in p or 'UP' == p.strip(): return 'Pacto/izq'
    if 'VERDE' in p or 'ESPERANZA' in p: return 'Verde/Centro'
    if not p: return 'Sin bancada'
    return 'Otro'


def _short(t):
    t = re.sub(r'\s+', ' ', t or '').strip()
    t = re.sub(r'^(Ponencia\s+(para|Para)\s+\w+\s+[Dd]ebate\s+al\s+)', '', t)
    # ojo: el prefijo de número debe ser palabra completa — 'N[oº°]?' suelto se
    # come la N de "número" y deja títulos tipo "úmero 089 de 2024 Senado".
    t = re.sub(r'^Proyecto\s+de\s+(?:Ley|Acto\s+Legislativo)\s*'
               r'(?:\b(?:n[uú]mero|N[oº°]\.?|No\.?)\s*)?', '', t, flags=re.I)
    return t[:90]


def main():
    if not SRC.exists():
        raise SystemExit(f'falta {SRC} — corre antes harvest_senado_api.py')
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(l) for l in open(SRC, encoding='utf-8')]

    # ---------- 1) agrupar por votación ----------
    votac = collections.defaultdict(lambda: {'fecha': '', 'nombre': '', 'tok': None, 'votos': []})
    for r in rows:
        tok = r.get('proyecto_numero_senado')
        if not tok or not r.get('respuesta'):
            continue
        v = votac[r['votacion_id']]
        v['fecha'] = r.get('fecha') or ''
        v['nombre'] = r.get('proyecto_titulo') or ''
        v['tok'] = tok
        # k = roster_key si existe; si no, el nombre (para no perder al senador)
        v['votos'].append((r['congresista'], r['respuesta'],
                           canon_bancada(r.get('partido')), r.get('roster_key') or ''))

    # ---------- 2) eje PROYECTO ----------
    por_proyecto, n_votac, n_votos = {}, 0, 0
    for vid, v in votac.items():
        resumen = collections.Counter(x[1] for x in v['votos'])
        banc = collections.defaultdict(lambda: collections.Counter())
        for c, resp, b, k in v['votos']:
            banc[b][resp] += 1
        obj = {
            'votacion_id': vid, 'fecha': v['fecha'], 'nombre': _short(v['nombre']),
            'resumen': dict(resumen),
            'por_bancada': {b: dict(c) for b, c in sorted(banc.items())},
            'votos': [{'c': c, 'r': resp, 'b': b, 'k': k} for c, resp, b, k in sorted(v['votos'])],
        }
        d = por_proyecto.setdefault(v['tok'], {'numero_senado': v['tok'], 'votaciones': []})
        d['votaciones'].append(obj)
        n_votac += 1
        n_votos += len(v['votos'])
    for tok, d in por_proyecto.items():
        d['votaciones'].sort(key=lambda x: x['fecha'])
        d['n_votaciones'] = len(d['votaciones'])

    meta_comun = {
        'v': '2026-07-28',
        'fuente': 'API pública app.senado.gov.co (/backend/api/public/v1/votes)',
        'rango': '2017-02 a 2026-06',
        'limites': 'la fuente solo registra Sí/No (sin abstención ni no-votó); una '
                   '"votación" agrupa las del mismo día sobre el mismo proyecto',
    }
    out1 = {'meta': {**meta_comun, 'n_proyectos': len(por_proyecto),
                     'n_votaciones': n_votac, 'n_votos': n_votos},
            'por_proyecto': por_proyecto}
    f1 = OUT / 'votaciones-senado-nominal.json'
    json.dump(out1, open(f1, 'w', encoding='utf-8'), ensure_ascii=False)

    # ---------- 3) eje SENADOR ----------
    # posición de gobierno (mayoría del Pacto ≥60%) + "contestada" (min lado ≥15%)
    gov, contest = {}, {}
    for vid, v in votac.items():
        pacto = [resp for (c, resp, b, k) in v['votos'] if b == 'Pacto/izq']
        cc = collections.Counter(pacto)
        if cc:
            top = cc.most_common(1)[0]
            if top[1] >= 0.6 * sum(cc.values()):
                gov[vid] = top[0]
        t = collections.Counter(resp for (c, resp, b, k) in v['votos'])
        si, no = t.get('Si', 0), t.get('No', 0)
        contest[vid] = (si + no) > 0 and min(si, no) >= 0.15 * (si + no)

    titulos = {}
    for vid, v in votac.items():
        titulos.setdefault(v['tok'], _short(v['nombre']))

    pers = collections.defaultdict(lambda: {
        'nombre': '', 'bancada': None, 'resumen': collections.Counter(),
        'aligned': 0, 'n_contest': 0,
        'por_proyecto': collections.defaultdict(lambda: collections.Counter())})
    for vid, v in votac.items():
        gp, cont = gov.get(vid), contest.get(vid)
        for (c, resp, b, k) in v['votos']:
            pk = k or c.upper()          # roster_key, o el nombre si no matcheó
            p = pers[pk]
            p['nombre'] = p['nombre'] or c
            if b and b not in ('Sin bancada', 'Otro'):
                p['bancada'] = b
            elif p['bancada'] is None:
                p['bancada'] = b
            p['resumen'][resp] += 1
            p['por_proyecto'][v['tok']][resp] += 1
            if cont and gp:
                p['n_contest'] += 1
                if resp == gp:
                    p['aligned'] += 1

    por_congresista = {}
    for pk, p in pers.items():
        total = sum(p['resumen'].values())
        if total < MIN_VOTOS_PERSONA:
            continue
        proys = [{'tk': tok, 'numero_senado': tok, 'titulo': titulos.get(tok, ''),
                  'n': sum(c.values()), 'r': dict(c)}
                 for tok, c in p['por_proyecto'].items()]
        proys.sort(key=lambda x: -x['n'])
        por_congresista[pk] = {
            'nombre': p['nombre'], 'bancada': p['bancada'], 'camara': 'Senado',
            'n_votos': total, 'n_proyectos': len(proys), 'resumen': dict(p['resumen']),
            'alineacion_gob': round(100 * p['aligned'] / p['n_contest']) if p['n_contest'] else None,
            'n_contestadas': p['n_contest'], 'por_proyecto': proys,
        }
    out2 = {'meta': {**meta_comun, 'n_congresistas': len(por_congresista),
                     'alineacion': 'alineación con la bancada de gobierno (Pacto) en votaciones '
                                   'CONTESTADAS (min lado ≥15%); las unánimes se excluyen'},
            'por_congresista': por_congresista}
    f2 = OUT / 'votaciones-senado-congresista.json'
    json.dump(out2, open(f2, 'w', encoding='utf-8'), ensure_ascii=False)

    print(f'proyectos: {len(por_proyecto)} · votaciones: {n_votac} · votos: {n_votos:,}')
    print(f'  → {f1.relative_to(REPO)} ({f1.stat().st_size/1024/1024:.2f} MB)')
    print(f'senadores: {len(por_congresista)}')
    print(f'  → {f2.relative_to(REPO)} ({f2.stat().st_size/1024/1024:.2f} MB)')
    # muestra: un senador conocido
    for pk, p in por_congresista.items():
        if 'CEPEDA CASTRO' in pk.upper():
            print(f"\nejemplo · {p['nombre']} ({p['bancada']}) · {p['n_votos']} votos · "
                  f"alineación gob {p['alineacion_gob']}% (de {p['n_contestadas']} contestadas)")
            for pr in p['por_proyecto'][:4]:
                print(f"    {pr['numero_senado']:9s} {pr['titulo'][:46]:46s} {pr['r']}")
            break


if __name__ == '__main__':
    main()
