#!/usr/bin/env python3
"""Arma tools/ley-rescate/fuerzas-historicas.json: la postura de cada actor en cada reforma tributaria 2016-2026.

Tres fuentes, de la más sólida a la más débil, y cada celda guarda su evidencia:
  1. voto nominal en plenaria (Cámara 2016 y 2022, de Bases de datos/congreso-claro/votos) · solo partidos
  2. ponencias de la Gaceta del Congreso leídas con el modelo local (2016 y 2018), frase verificada literal
  3. titulares de prensa de cada época, clasificados con el modelo local
2026 sale de lo ya curado a mano: voces.json (gremios) y votos.json (bancadas, con su inclinación)."""
import json, glob, hashlib, collections, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from actores import REFORMAS, ACTORES

RAIZ = Path(__file__).resolve().parents[3]
H = RAIZ / 'Bases de datos' / 'ley-rescate' / 'historia'
LR = RAIZ / 'tools' / 'ley-rescate'
leer = lambda p, d=None: json.loads(Path(p).read_text()) if Path(p).exists() else d

# Postura de la bancada en plenaria: número del proyecto en el registro de votos → reforma
VOTOS = {'178/16 Cámara': 'r2016', '118/22 Cámara': 'r2022'}
BANC = {'Liberal': 'lib', 'La U': 'u', 'Conservador': 'con', 'Centro Democrático': 'cd', 'Cambio Radical': 'cr', 'Verde/Centro': 'verde', 'Pacto/izq': 'pacto'}
# 2026: rótulo corto de voces.json → actor
VOZ26 = {'ANDI': 'andi', 'Fenalco': 'fenalco', 'Anif': 'anif', 'Fedesarrollo': 'fedesarrollo', 'Asobancaria': 'asobancaria', 'Consejo Gremial': 'consejo-gremial',
         'Cafeteros': 'cafeteros', 'CUT · Arias': 'cut', 'CGT': 'cgt', 'AmCham': 'amcham', 'Fecoljuegos': 'fecoljuegos'}
TIENDE = {'si': 'a', 'aj': 'm', 'no': 'r'}
# Titulares clasificados con postura que, revisados a mano (6-nov-2026), no hablan de la reforma.
EXCLUIR = ['impuesto de guerra', 'Prima extra (de Álvaro Uribe)', 'les está saliendo tan cara la declaración', 'contrarreloj del Presupuesto General 2025']

def postura(c):
    """a/m/r por mayoría de evidencias; empate entre a y r → m (dividido)."""
    if not c: return None
    (p1, n1), *resto = c.most_common()
    if resto and resto[0][1] == n1: return 'm'
    return p1

def agrega_2026(celda, voces, votos):
    """La columna 2026 sale de lo curado a mano: voces.json (gremios) y votos.json (bancadas)."""
    for v in voces:
        a = VOZ26.get(v.get('k'))
        if not a: continue
        p, inf = (v['t'], True) if v['p'] == 'i' and v.get('t') else (v['p'], False)
        if p == 'i': continue
        c = celda(a, 'r2026'); c['c'][p] += 1; c['inferida'] = inf
        c['ev'].append({'src': 'curada', 'p': p, 't': v['x'], 'f': v['f'], 'u': v.get('u', '')})
    for b in votos.get('bloques', []):
        a = b['id']
        if a not in {x[0] for x in ACTORES}: continue
        p = {'si': 'm' if 'ajust' in b.get('nota', '') else 'a', 'no': 'r'}.get(b['post']) or TIENDE.get(b.get('tiende'))
        if not p: continue
        c = celda(a, 'r2026'); c['c'][p] += 1; c['inferida'] = b['post'] == 'sin'
        c['ev'].append({'src': 'curada', 'p': p, 't': b['nota'] + (' Inclinación: ' + b['por'] if b.get('por') else ''), 'f': 'Seguimiento de la Ley de Rescate'})


def refrescar_2026(fh, voces, votos):
    """Rehace solo la columna 2026 de un fuerzas-historicas.json ya armado. La llama rastreo.py en cada corrida,
    porque las épocas anteriores necesitan los archivos de Bases de datos/ y el modelo local, y 2026 no:
    sin esto, la columna se quedaba con lo del día en que se corrió build_historia.py (pasó entre el 6 y el 12-nov)."""
    celdas = collections.defaultdict(dict)
    def celda(a, r): return celdas[a].setdefault(r, {'ev': [], 'c': collections.Counter()})
    agrega_2026(celda, voces, votos)
    for a, rs in fh.get('celdas', {}).items():
        rs.pop('r2026', None)
    for a, rs in celdas.items():
        c = rs['r2026']; p = postura(c['c'])
        if not p: continue
        fh.setdefault('celdas', {}).setdefault(a, {})['r2026'] = {k: v for k, v in {'p': p, 'n': dict(c['c']), 'inferida': c.get('inferida') or None, 'ev': c['ev'][:8]}.items() if v}
    nombres = {x['id'] for x in fh.get('actores', [])}
    fh['actores'] = fh.get('actores', []) + [{'id': x[0], 'nombre': x[1], 'g': x[2]} for x in ACTORES if x[0] in celdas and x[0] not in nombres]
    return fh


def main():
    clas = leer(H / 'prensa-clas.json', {}); prensa = leer(H / 'prensa.json', {}); gac = leer(H / 'gacetas.json', {})
    celdas = collections.defaultdict(dict)
    def celda(a, r): return celdas[a].setdefault(r, {'ev': [], 'c': collections.Counter(), 'asistio': False})

    # 1. voto nominal
    vot = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for f in glob.glob(str(RAIZ / 'Bases de datos' / 'congreso-claro' / 'votos' / '*.json')):
        if f.endswith('indice.json'): continue
        for b in json.loads(Path(f).read_text())['bloques']:
            for pr in b.get('proyectos', []):
                if pr[1] in VOTOS and pr[7] and b['bancada'] in BANC:
                    vot[VOTOS[pr[1]]][BANC[b['bancada']]][pr[7]] += 1
    votos_out = {}
    for r, bs in vot.items():
        votos_out[r] = {a: dict(c) for a, c in bs.items() if sum(c.values()) >= 3}
        for a, c in bs.items():
            n = sum(c.values()); fav, con = c.get('a_favor', 0), c.get('en_contra', 0)
            if n < 3: continue  # una bancada de uno o dos no es una postura de partido (la izquierda de 2016)
            p = 'a' if fav / n >= .7 else 'r' if con / n >= .7 else 'm'
            x = celda(a, r); x['voto'] = {'p': p, **dict(c)}
    # 2. gacetas
    for r, g in gac.items():
        grupo = {x[0]: x[2] for x in ACTORES}
        for a in g.get('asistentes', []):
            if grupo.get(a) != 'par': celda(a, r)['asistio'] = True  # a un partido lo nombran los congresistas del foro: no interviene
        for x in g.get('posturas', []):
            if not x.get('verificada'): continue
            p = {'apoya': 'a', 'apoya con reparos': 'm', 'reparos': 'm', 'rechaza': 'r'}.get(x.get('postura'))
            for a in x.get('actores', []):
                if p:
                    c = celda(a, r); c['c'][p] += 2  # un resumen oficial pesa como dos titulares
                    c['ev'].append({'src': 'gaceta', 'p': p, 't': x.get('frase', ''), 'f': g['gaceta'], 'esp': g['espacio'], 'temas': x.get('temas', [])[:4]})
    # 3. prensa
    for r, L in prensa.items():
        for it in L:
            k = r + ':' + hashlib.sha1(it['t'].encode()).hexdigest()[:12]
            if any(x in it['t'] for x in EXCLUIR): continue
            for a, p in (clas.get(k) or {}).items():
                if p in ('a', 'm', 'r'):
                    c = celda(a, r); c['c'][p] += 1
                    c['ev'].append({'src': 'prensa', 'p': p, 't': it['t'], 'f': it['f'], 'u': it['url'], 'fecha': it['fecha']})
    agrega_2026(celda, leer(LR / 'voces.json', []), leer(LR / 'votos.json', {}))

    out = {}
    for a, rs in celdas.items():
        for r, c in rs.items():
            p = c['voto']['p'] if 'voto' in c else postura(c['c'])
            ev = sorted(c['ev'], key=lambda e: ({'gaceta': 0, 'curada': 0, 'prensa': 1}[e['src']], e.get('fecha', '')))[:8]
            if not p and not c['asistio']: continue
            out.setdefault(a, {})[r] = {k: v for k, v in {'p': p, 'n': dict(c['c']), 'asistio': c['asistio'] or None, 'voto': c.get('voto'),
                                       'inferida': c.get('inferida') or None, 'ev': ev}.items() if v}
    tl = leer(LR / 'tributarias.json', {}).get('lista', [])
    ref = [{'id': r[0], 'nombre': r[1], 'desde': r[3], 'hasta': r[4]} for r in REFORMAS] + [{'id': 'r2026', 'nombre': 'Ley de Rescate 2026', 'desde': '2026-10-29', 'hasta': ''}]
    for x, t in zip(ref, tl + [{}]):
        x.update({k: t.get(k) for k in ('gobierno', 'res', 'ley') if t.get(k)})
    res = {'v': 1, 'reformas': ref, 'actores': [{'id': a[0], 'nombre': a[1], 'g': a[2]} for a in ACTORES if a[0] in out],
           'celdas': out, 'votos': votos_out,
           'fuentes': {'prensa': {r: len(L) for r, L in prensa.items()}, 'gacetas': {r: g['gaceta'] + ' · ' + g['espacio'] for r, g in gac.items()}}}
    (LR / 'fuerzas-historicas.json').write_text(json.dumps(res, ensure_ascii=False, indent=0))
    print('actores', len(out), 'celdas', sum(len(v) for v in out.values()))

if __name__ == '__main__':
    if '--solo-2026' in sys.argv:
        fh = leer(LR / 'fuerzas-historicas.json', {})
        refrescar_2026(fh, leer(LR / 'voces.json', []), leer(LR / 'votos.json', {}))
        (LR / 'fuerzas-historicas.json').write_text(json.dumps(fh, ensure_ascii=False, indent=0))
        print('2026 rehecho:', sum(1 for rs in fh['celdas'].values() if 'r2026' in rs), 'actores')
    else:
        main()
