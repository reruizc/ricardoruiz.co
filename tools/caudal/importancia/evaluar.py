#!/usr/bin/env python3
"""
Caudal · Importancia — corre las tres coordenadas sobre la legislatura viva.

    python3 tools/caudal/importancia/evaluar.py [--top 12] [--reporte x.md]
    python3 tools/caudal/importancia/evaluar.py --caso fracking

Sirve de dos cosas: es la prueba de que el modelo resuelve el problema que lo
originó (el fracking tiene que caer en el lente de riesgo y sostenerse en el
político) y es el arnés para revisar el ranking a ojo antes de exponerlo.
"""
import argparse
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import features as F      # noqa: E402
import ejes as E          # noqa: E402
from modelo import Logistica   # noqa: E402

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
BD = os.path.join(RAIZ, 'Bases de datos', 'leyes-senado')
DIST = os.path.join(BD, 'dist')
LEG_VIVA = '2026-2027'


def _n(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', s.lower())


def num_token(num):
    m = re.search(r'(\d{1,4})\s*/\s*(?:20)?(\d{2})', num or '')
    return f'{int(m.group(1))}/{m.group(2)}' if m else None


def cargar():
    rows = []
    for a in ('proyectos.jsonl', 'actos-legis.jsonl'):
        p = os.path.join(DIST, a)
        with open(p) as fh:
            for ln in fh:
                if ln.strip():
                    rows.append(json.loads(ln))
    modelo = Logistica.de_dict(json.load(
        open(os.path.join(DIST, 's3', 'importancia-modelo.json'))))
    aut = json.load(open(os.path.join(DIST, 's3', 'importancia-autores.json')))
    art = json.load(open(os.path.join(DIST, 's3', 'articulado.json')))['por_proyecto']
    try:
        bl = json.load(open(os.path.join(BD, 'actas', 'bloqueo.json')))
    except Exception:
        bl = {'por_proyecto': {}, 'senado': {'por_proyecto': {}}}
    ap = json.load(open(os.path.join(DIST, 'autor-partido.json')))
    try:
        antec = json.load(open(os.path.join(DIST, 's3', 'importancia-antecedentes.json')))['por_proyecto']
    except Exception:
        antec = {}
    return rows, modelo, aut, art, bl, ap.get('autor_partido', ap), antec


def bloqueo_de(rec, bl):
    """Cruce con el índice de agendamientos. Cámara contra el índice de Cámara
    y Senado contra el de Senado: el número se reinicia por cámara y 1.012
    tokens existen en los dos para proyectos distintos."""
    t = num_token(rec.get('numero_camara'))
    if t:
        b = (bl.get('por_proyecto') or {}).get(t)
        if b:
            return b
    t = num_token(rec.get('numero_senado'))
    if t:
        b = ((bl.get('senado') or {}).get('por_proyecto') or {}).get(t)
        if b:
            return b
    return None


def evaluar_todo(perfil=None):
    rows, modelo, aut, art, bl, partidos, antec = cargar()
    viva = [r for r in rows if r.get('legislatura') == LEG_VIVA]
    # la explicación se compara contra los pares de la misma legislatura, no
    # contra 36 años de histórico (ver features.referencia)
    ref = F.referencia(viva, aut)
    items = []
    for r in viva:
        tok = f"{r.get('tabla', 'pdly')}:{r.get('id')}"
        items.append(E.coordenadas(
            r, modelo, aut, art.get(tok), partidos, bloqueo_de(r, bl), perfil,
            ref, antec))
    return items, viva


def _linea(i, it, mostrar='todo'):
    a, im, po = it['avance'], it['impacto'], it['politico']
    ims = f"{im['score']:5.1f}" if im else '  n/d'
    tit = (it['titulo'] or '')[:76].replace('\n', ' ')
    L = [f"{i:2d}. [{it['numero'] or '—':>9}] {tit}",
         f"     avance {a['score']:5.1f}%   impacto {ims}   político {po['score']:5.1f}"
         f"   · {po['etiqueta']}"]
    if it.get('orden') is not None:
        L[1] += f"   [orden {it['orden']}]"
    if mostrar == 'todo':
        for f in a['factores'][:3]:
            sig = '+' if f['sentido'] == 'a favor' else '−'
            L.append(f"       {sig} {f['dice']}")
        if im and im.get('aviso'):
            L.append(f"     ⚠ {im['aviso']}")
        if a.get('ajuste_bloqueo'):
            L.append(f"     cola: {a['ajuste_bloqueo']['nota']}")
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--top', type=int, default=10)
    ap.add_argument('--caso', default=None, help='buscar por texto en el título')
    ap.add_argument('--reporte', default=None)
    args = ap.parse_args()
    log = []

    def P(*a):
        s = ' '.join(str(x) for x in a)
        print(s)
        log.append(s)

    items, viva = evaluar_todo()
    P(f'CAUDAL · importancia sobre la legislatura {LEG_VIVA}')
    P('=' * 78)
    con_art = sum(1 for it in items if it['impacto'])
    P(f'{len(items)} proyectos · {con_art} con articulado extraído '
      f'({100*con_art/max(len(items),1):.0f}%)')

    if args.caso:
        q = _n(args.caso)
        hits = [it for it in items if q in _n(it['titulo'])]
        P(f'\nCasos que coinciden con "{args.caso}": {len(hits)}')
        for it in hits:
            P('\n' + _linea(0, it))
            P(f'     componentes político: {it["politico"]["componentes"]}')
            if it['politico'].get('cohesion'):
                P(f'     cohesión: {it["politico"]["cohesion"]}')
            if it['impacto']:
                P(f'     componentes impacto: {it["impacto"]["componentes"]}')
        return 0

    for lente in ('riesgo', 'politico', 'agenda'):
        res = E.ordenar([dict(x) for x in items], lente)
        meta = E.LENTES[lente]
        P(f'\n\n{"─"*78}\nLENTE «{meta["nombre"]}» — {meta["para"]}')
        P(f'ordena por: {meta["ordena"]}')
        P('')
        for i, it in enumerate(res['ranking'][:args.top], 1):
            P(_linea(i, it, 'corto' if lente != 'riesgo' else 'todo'))
        if res['pendientes']:
            P(f'\n  ── Pendientes de leer el articulado ({len(res["pendientes"])}) '
              '— fuera del ranking a propósito: de estos solo tenemos el título,')
            P('     así que su impacto sería un piso y no una medida. Van aparte, '
              'ordenados por avance y peso político.')
            for i, it in enumerate(res['pendientes'][:5], 1):
                P('  ' + _linea(i, it, 'corto'))
        if res['fuera']:
            P(f'\n  ({len(res["fuera"])} proyectos no evaluables en este lente: '
              'sin articulado extraído)')

    if args.reporte:
        with open(args.reporte, 'w') as fh:
            fh.write('```\n' + '\n'.join(log) + '\n```\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
