#!/usr/bin/env python3
"""
Caudal · COALICIONES — quién vota con quién, y cómo cambió con el gobierno.

La vista de bancadas (build_bancadas_s3.py) mide cada bancada por dentro
(cohesión) y contra el gobierno (alineación). Falta el eje entre ellas: qué
bancadas votan juntas, si eso forma bloques, y si el bloque se rompió cuando
cambió el gobierno.

Emite metadata/coaliciones.json con, para la Cámara:
  · matriz       coincidencia entre cada par de bancadas, por periodo
  · orden        el espectro, DERIVADO del dato (seriación por similitud)
  · bloques      agrupamiento jerárquico (average linkage) cortado en CORTE
  · realineamiento  qué pares se juntaron o se rompieron entre Duque y Petro

Decisiones medidas (cada una responde a algo que se comprobó, no a un supuesto):

OJO 1 · LA UNIDAD ES LA MAYORÍA DE LA BANCADA, no el voto individual. Dos
  bancadas «coinciden» en una votación cuando la mayoría de una votó lo mismo
  que la mayoría de la otra. Una bancada partida por la mitad exacta no tiene
  mayoría que comparar y esa votación no entra a sus pares (no se desempata a
  favor de nadie).

OJO 2 · SOLO VOTACIONES DE FONDO Y CONTESTADAS. Se hereda entero el criterio de
  build_bancadas_s3 (contestada = min lado ≥15%; piso de quórum; un voto por
  persona) y ADEMÁS se exige que la votación decida el proyecto —ponencia,
  articulado, título, conciliación, aplazamiento, archivo— vía
  votacion_tipo.clasificar. Medido: sin ese filtro, el 61% de las contestadas
  de Cámara son impedimentos, donde la bancada se suelta por rutina.
  Con el filtro NO hace falta corregir por azar: la coincidencia va de 7,8%
  (Pacto–Centro Democrático) a 89,5% (Liberal–La U), un rango que se lee solo.
  Si algún día se quita el filtro, revisar esto: con votaciones casi unánimes
  dentro, dos bancadas cualesquiera coinciden alto sin ser aliadas.

OJO 3 · EL PACTO NO EXISTE COMO BANCADA ANTES DE 2022. Medido: 24 votaciones de
  fondo con mayoría propia en la era Duque, contra 231 en la de Petro (antes
  eran Colombia Humana, Polo y MAIS, con muy pocos representantes). Por eso
  cualquier par suyo queda por debajo de MIN_PAR en Duque y **no entra al
  realineamiento**: su ausencia ahí no es que no se moviera, es que no había a
  quién medir. Se reporta en `excluidas` para que el hueco se vea.

OJO 4 · EL SENADO NO SE PUEDE MEDIR AQUÍ. Tras deduplicar sus votaciones
  republicadas quedan 23 contestadas y su fuente no dice QUÉ se votó, así que
  ni siquiera se pueden restringir a las de fondo: medido, CERO pares llegan a
  MIN_PAR (el mayor n posible es 23). Se emite `medible: false` con el motivo,
  en vez de dibujar una matriz sobre un puñado de votos.

OJO 5 · EL ORDEN DE LAS BANCADAS SALE DEL DATO. No se escribe a mano un eje
  izquierda-derecha: se agrupan por similitud (average linkage) y el recorrido
  del árbol da el orden. Que el resultado se parezca al eje ideológico conocido
  es un hallazgo, no un supuesto de entrada.

Uso:  python3 tools/caudal/build_coaliciones_s3.py
      # → Bases de datos/leyes-senado/dist/s3/coaliciones.json
"""
import collections
import itertools
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DIST = REPO / 'Bases de datos' / 'leyes-senado' / 'dist'
OUT = DIST / 's3'
sys.path.insert(0, str(Path(__file__).resolve().parent))

# se reusan enteros los criterios de la vista de bancadas — no bifurcar
from build_bancadas_s3 import (                              # noqa: E402
    _rows_camara, _rows_senado, _key_camara, _persona_camara, _persona_senado,
    agrupar, dedup, canon_bancada, NO_BANCADA, MIN_MIEMBROS, CONTESTADA,
    MIN_VOTANTES, PETRO,
)
from votacion_tipo import clasificar, FONDO                  # noqa: E402

MIN_PAR = 25      # votaciones compartidas para publicar la coincidencia de un par
MIN_ERA = 25      # ídem dentro de una era, para entrar al realineamiento
CORTE = 0.60      # coincidencia media ≥60% para quedar en el mismo bloque
CAMBIO_MIN = 10   # pp de cambio para llamarlo realineamiento


def mayorias(V, tipos, min_votantes, proy=None):
    """[(fecha, {bancada: 'Si'|'No'})] de las votaciones de fondo contestadas.
    Aplica los mismos descartes que build_bancadas_s3.analizar (OJO 2)."""
    limpias = {}
    desc = collections.Counter()
    for k, vs in V.items():
        c = collections.Counter(x[0] for x in vs)
        if max(c.values()) > 1:
            desc['repetido'] += 1
            continue
        if len(vs) < min_votantes:
            desc['sin_quorum'] += 1
            continue
        limpias[k] = vs
    if proy:
        n0 = len(limpias)
        limpias = dedup(limpias, proy)
        desc['republicada'] = n0 - len(limpias)

    out = []
    for k, vs in limpias.items():
        t = collections.Counter(x[1] for x in vs)
        si, no = t.get('Si', 0), t.get('No', 0)
        if si + no == 0 or min(si, no) < CONTESTADA * (si + no):
            desc['unanime'] += 1
            continue
        if tipos is not None:
            if tipos.get(k) not in FONDO:
                desc['no_fondo'] += 1
                continue
        b = collections.defaultdict(lambda: [0, 0])
        for (p, resp, banc, f) in vs:
            if banc in NO_BANCADA:
                continue
            if resp == 'Si':
                b[banc][0] += 1
            elif resp == 'No':
                b[banc][1] += 1
        # OJO 1: empate exacto = sin mayoría, no entra
        m = {banc: ('Si' if s > n else 'No')
             for banc, (s, n) in b.items() if s + n >= MIN_MIEMBROS and s != n}
        if len(m) >= 2:
            fecha = next((x[3] for x in vs if x[3]), '')
            out.append((fecha, m))
        else:
            desc['sin_mayorias'] += 1
    return out, desc


def matriz(mays, sel=None):
    """{(a,b): [coincidencias, n]} sobre las votaciones que pasan `sel(fecha)`."""
    p = collections.defaultdict(lambda: [0, 0])
    n = 0
    for fecha, m in mays:
        if sel and not sel(fecha):
            continue
        n += 1
        for a, b in itertools.combinations(sorted(m), 2):
            p[(a, b)][1] += 1
            if m[a] == m[b]:
                p[(a, b)][0] += 1
    return p, n


def _sim(p, a, b):
    v = p.get((a, b)) or p.get((b, a))
    if not v or v[1] < MIN_PAR:
        return None
    return v[0] / v[1]


def agrupar_bloques(bancadas, p):
    """Devuelve (orden, bloques) a partir de la matriz de coincidencia.

    El ORDEN sale de un average linkage: bancadas parecidas quedan contiguas y
    de ahí emerge el espectro sin escribirlo a mano (OJO 5).

    Los BLOQUES usan un criterio ESTRICTO distinto (OJO 6): un bloque es un
    conjunto donde TODOS los pares llegan al corte, no donde el promedio llega.
    Con el promedio, el average linkage encadena — metía al Conservador en el
    bloque de gobierno de la era Petro porque su media daba 62%, aunque con el
    Pacto coincide 52,8%. Decir que dos bancadas están en el mismo bloque
    cuando discrepan en la mitad de las votaciones es afirmar de más; con el
    criterio estricto el Conservador queda suelto, que es lo que muestra el dato:
    es la bisagra entre los dos bloques, no parte de uno.

    Se implementa a mano —son 7 bancadas— para no traer scipy a un build que
    hoy corre solo con la stdlib."""
    clusters = [[b] for b in bancadas]

    def dist(c1, c2):
        vs = [_sim(p, a, b) for a in c1 for b in c2]
        vs = [v for v in vs if v is not None]
        return sum(vs) / len(vs) if vs else None

    merges = []
    while len(clusters) > 1:
        mejor = None
        for i, j in itertools.combinations(range(len(clusters)), 2):
            d = dist(clusters[i], clusters[j])
            if d is None:
                continue
            if mejor is None or d > mejor[0]:
                mejor = (d, i, j)
        if mejor is None:
            break                       # sin datos para seguir uniendo
        d, i, j = mejor
        # ⚠️ Al unir hay que ORIENTAR: se prueban las cuatro combinaciones y se
        # deja la que hace que los extremos que quedan pegados sean los más
        # parecidos. Sin esto el orden final es el de los merges y no el del
        # árbol — daba «Centro Democrático · Pacto», los dos polos opuestos
        # (7,8% de coincidencia) contiguos.
        c1, c2 = clusters[i], clusters[j]
        best, nuevo = None, c1 + c2
        for x in (c1, c1[::-1]):
            for y in (c2, c2[::-1]):
                v = _sim(p, x[-1], y[0])
                if v is not None and (best is None or v > best):
                    best, nuevo = v, x + y
        merges.append((d, list(nuevo)))
        clusters = [c for k, c in enumerate(clusters) if k not in (i, j)] + [nuevo]

    orden = [b for c in clusters for b in c]
    # BLOQUES por criterio estricto: todos los pares del grupo ≥ CORTE.
    # Se crece cada bloque desde el par más afín, admitiendo una bancada solo
    # si llega al corte con TODAS las que ya están dentro.
    pares = sorted(((_sim(p, a, b), a, b) for a, b in itertools.combinations(bancadas, 2)
                    if _sim(p, a, b) is not None), reverse=True)
    bloques, usados = [], set()
    for v, a, b in pares:
        if v < CORTE or a in usados or b in usados:
            continue
        grupo = [a, b]
        # ⚠️ Los candidatos se prueban por AFINIDAD con el grupo, no en el orden
        # del espectro: admitir al más parecido primero. Con el orden del
        # espectro entraba el Conservador (65% con Liberal) antes que el Pacto
        # (86%), y una vez dentro el Conservador cerraba la puerta al Pacto
        # —coinciden 52,8%—, dejando al Pacto solo pese a votar con ese grupo
        # 8 de cada 10 veces. Se re-ordena en cada vuelta porque el grupo cambia.
        while True:
            libres = [x for x in bancadas if x not in usados and x not in grupo]
            afines = sorted(((sum(_sim(p, x, g) or 0 for g in grupo) / len(grupo), x)
                             for x in libres), reverse=True)
            for _, cand in afines:
                if all((_sim(p, cand, g) or 0) >= CORTE for g in grupo):
                    grupo.append(cand)
                    break
            else:
                break
        bloques.append([x for x in orden if x in grupo])
        usados |= set(grupo)
    sueltas = [[b] for b in bancadas if b not in usados]
    return orden, sorted(bloques, key=len, reverse=True) + sueltas


def _periodo(etiqueta, n, p, emitir, bloque_de, con_material):
    orden, bloques = bloque_de(p, con_material(p))
    return {'etiqueta': etiqueta, 'n_votaciones': n, 'matriz': emitir(p),
            'orden': orden, 'bloques': bloques}


def analizar_camara():
    Vc, cobc, _, _, tipc = agrupar(_rows_camara(), _key_camara, _persona_camara,
                                   tipar=True)
    mays, desc = mayorias(Vc, tipc, MIN_VOTANTES['camara'])
    p_all, n_all = matriz(mays)
    p_d, n_d = matriz(mays, lambda f: bool(f) and f < PETRO)
    p_p, n_p = matriz(mays, lambda f: bool(f) and f >= PETRO)

    # bancadas con material suficiente en el periodo completo
    bancadas = sorted({b for _, m in mays for b in m})
    bancadas = [b for b in bancadas
                if sum(v[1] for (x, y), v in p_all.items() if b in (x, y)) >= MIN_PAR]

    def emitir(p):
        return {f'{a}|{b}': {'pct': round(100 * v[0] / v[1], 1), 'n': v[1]}
                for (a, b), v in p.items()
                if v[1] >= MIN_PAR and a in bancadas and b in bancadas}

    # ⚠️⚠️ ORDEN Y BLOQUES VAN POR PERIODO, NO SOBRE TODO. Calcularlos sobre
    # 2014-2026 promedia dos configuraciones políticas opuestas y fabrica un
    # bloque que nunca existió: el realineamiento de 2022 mueve pares hasta 62
    # pp, y con el promedio salía un «bloque» de cinco bancadas que metía al
    # Pacto junto al Conservador (47% de coincidencia). Cada periodo trae los
    # suyos y el frontend pinta los del periodo que el usuario esté viendo.
    def bloque_de(p, periodo_bancadas):
        return agrupar_bloques(periodo_bancadas, p)

    def con_material(p):
        return [b for b in bancadas
                if sum(v[1] for (x, y), v in p.items()
                       if b in (x, y) and v[1] >= MIN_PAR) >= MIN_PAR]

    # realineamiento: pares con material en LAS DOS eras (OJO 3)
    real, excl = [], []
    for a, b in itertools.combinations(bancadas, 2):
        vd, vp = p_d.get((a, b)), p_p.get((a, b))
        nd = vd[1] if vd else 0
        np_ = vp[1] if vp else 0
        if nd < MIN_ERA or np_ < MIN_ERA:
            excl.append({'par': f'{a}|{b}', 'n_duque': nd, 'n_petro': np_})
            continue
        pd, pp = 100 * vd[0] / nd, 100 * vp[0] / np_
        real.append({'a': a, 'b': b, 'duque': round(pd, 1), 'petro': round(pp, 1),
                     'cambio': round(pp - pd, 1), 'n_duque': nd, 'n_petro': np_})
    real.sort(key=lambda x: -abs(x['cambio']))

    orden, bloques = agrupar_bloques(con_material(p_p), p_p)   # el actual manda
    return {
        'nombre': 'Cámara de Representantes',
        'medible': True,
        'periodo_default': 'petro',
        'orden': orden,
        'bloques': bloques,
        'periodos': {k: _periodo(et, nn, pp, emitir, bloque_de, con_material)
                     for k, et, nn, pp in (
                         ('petro', 'Gobierno Petro · desde ago-2022', n_p, p_p),
                         ('duque', 'Gobierno Duque · hasta ago-2022', n_d, p_d),
                         ('todo',  'Todo el periodo 2014-2026', n_all, p_all))},
        'realineamiento': real,
        'excluidas': excl,
        'cobertura': {
            'n_votaciones_fondo': len(mays),
            'n_duque': n_d, 'n_petro': n_p,
            'descartes': dict(desc),
            'n_votos': cobc['n_votos'],
            'min_par': MIN_PAR, 'corte_bloque': CORTE,
        },
    }


def analizar_senado():
    """OJO 4: se corre igual para MEDIR que no alcanza, en vez de suponerlo."""
    Vs, cobs, _, proys, _ = agrupar(_rows_senado(), lambda r: r['votacion_id'],
                                    _persona_senado,
                                    lambda r: r.get('senado_proyecto_id'))
    mays, _ = mayorias(Vs, None, MIN_VOTANTES['senado'], proy=proys)
    p, n = matriz(mays)
    mx = max((v[1] for v in p.values()), default=0)
    ok = sum(1 for v in p.values() if v[1] >= MIN_PAR)
    return {
        'nombre': 'Senado',
        'medible': False,
        'n_votaciones': n,
        'n_pares_suficientes': ok,
        'n_max_par': mx,
        'motivo': (f'Tras deduplicar las votaciones que la fuente republica en varias '
                   f'fechas quedan {n} contestadas, y su API no publica QUÉ se votó, '
                   f'así que tampoco se pueden restringir a las que deciden el proyecto. '
                   f'Ningún par de bancadas llega a las {MIN_PAR} votaciones compartidas '
                   f'que exige esta vista (el mayor llega a {mx}). Se deja sin medir en '
                   f'vez de dibujar una matriz sobre un puñado de votos.'),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cam = analizar_camara()
    sen = analizar_senado()
    out = {
        'meta': {
            'v': '2026-08-21',
            'que_mide': 'coincidencia entre las MAYORÍAS de dos bancadas en las '
                        'votaciones de fondo contestadas (las que deciden el proyecto)',
            'fuente': 'actas de plenaria de Cámara · voto nominal electrónico + OCR DCN-SW',
            'corte_gobierno': PETRO,
        },
        'camara': cam,
        'senado': sen,
    }
    f = OUT / 'coaliciones.json'
    json.dump(out, open(f, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'→ {f.relative_to(REPO)} ({f.stat().st_size/1024:.1f} KB)\n')

    c = cam['cobertura']
    print(f"=== Cámara · {c['n_votaciones_fondo']} votaciones de fondo con mayorías "
          f"(Duque {c['n_duque']} · Petro {c['n_petro']})")
    print(f"  descartes: {c['descartes']}")
    print(f"  orden derivado del dato: {' · '.join(cam['orden'])}")
    print(f"  bloques (coincidencia media ≥{int(CORTE*100)}%):")
    for b in cam['bloques']:
        print(f"    {' + '.join(b)}")
    print(f"\n  realineamiento (|cambio| ≥ {CAMBIO_MIN}pp):")
    for r in cam['realineamiento']:
        if abs(r['cambio']) < CAMBIO_MIN:
            continue
        print(f"    {r['a']:20s} — {r['b']:20s} {r['duque']:5.1f}% → {r['petro']:5.1f}%  "
              f"{r['cambio']:+6.1f}pp   n {r['n_duque']}/{r['n_petro']}")
    if cam['excluidas']:
        # ¿qué bancada aparece en TODOS los pares excluidos? esa es la que falta
        sets = [set(p['par'].split('|')) for p in cam['excluidas']]
        comun = set.intersection(*sets) if sets else set()
        print(f"\n  fuera del realineamiento: {len(cam['excluidas'])} pares"
              + (f" — todos de {', '.join(sorted(comun))} (sin bancada propia antes de 2022)" if comun else ''))
    print(f"\n=== Senado · NO medible: {sen['n_votaciones']} contestadas, "
          f"{sen['n_pares_suficientes']} pares suficientes (máx n={sen['n_max_par']})")


if __name__ == '__main__':
    main()
