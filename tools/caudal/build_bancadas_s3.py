#!/usr/bin/env python3
"""
Caudal · DISCIPLINA DE BANCADA — el agregado por partido del voto nominal.

Hoy el voto nominal existe por proyecto (build_votaciones_{camara,senado}_s3.py)
y por persona (build_congresista_s3.py). Falta el eje del medio: ¿qué tan en
bloque vota cada bancada, con quién se alinea, y quién se le sale?

Emite metadata/bancadas.json (chico, cabe entero en la Lambda) con, por cámara:
  · cohesión      índice de Rice |Sí−No|/(Sí+No) por bancada y votación, promediado
  · bloque %      votaciones donde ≥90% de la bancada votó del mismo lado
  · alineación    coincidencia con la posición del Pacto (ver OJO 3)
  · disidentes    quién vota contra la mayoría de su propia bancada
  · serie         evolución (Cámara por año · Senado por era, ver OJO 2)
  · cobertura     votos sin partido y bancadas excluidas, en números

Decisiones que NO son cosméticas (cada una responde a algo medido):

OJO 1 · UNA VOTACIÓN = UN VOTO POR PERSONA. Se descartan las votaciones donde
  alguien aparece dos veces. En Senado es estructural: la llave de la API
  (fecha, ID Proyecto) AGRUPA las votaciones del mismo día sobre el mismo
  proyecto — medido: 249 de 1.780 grupos (14%) repiten senador, uno hasta 6
  veces. En Cámara son 51 de 5.202 y parecen artefactos de parseo. El Rice
  exige un voto por miembro, así que en los dos casos se excluye y se reporta.
  Se verificó que el resto NO viene mezclado: ningún grupo del Senado supera
  los 108 votos (el Senado entero) y los contestados son incluso más chicos
  (mediana 70) que los no contestados (83) — o sea el filtro deja votaciones
  de tamaño plausible, no bloques pegados.

OJO 1b · EL SENADO REPUBLICA LA MISMA VOTACIÓN EN VARIAS FECHAS. Medido: sus
  1.531 votaciones limpias tienen solo 248 firmas distintas (misma lista exacta
  de senador→voto, mismo proyecto, fechas distintas); una se repite 14 veces
  entre abril y julio de 2025. Contarlas como independientes multiplica por 4 el
  peso de un puñado de votos reales y fabrica precisión. Se deduplica por
  (proyecto, firma) conservando la fecha más temprana. NO se hace lo mismo en
  Cámara: ahí cada votación viene numerada por el acta (`votacion_numero`) —
  marcador de distinción que el Senado no tiene — y las firmas repetidas son
  76 de 4.133 (1,8%), plausiblemente votos consecutivos reales donde todos
  repitieron su voto. La diferencia de trato es la diferencia de fuente.
  Efecto: las contestadas del Senado pasan de 98 a 23, y el Rice del Pacto sube
  de 0,558 a 0,662 — la corrección no es cosmética.

OJO 2 · LAS DOS CÁMARAS NO SE PROMEDIAN. Coberturas distintas: Cámara 2012-2026
  con el hueco 2010-2013 (actas narrativas, sin nominal que extraer) y con
  Sí/No/Abstención; Senado 2017-2026 y SOLO Sí/No — sin abstención ni «no votó»,
  así que un senador que se abstiene es invisible. Cada cámara va en su bloque
  con su alcance a la vista. Y el volumen no da lo mismo: Cámara tiene ~1.734
  votaciones contestadas (serie por AÑO); el Senado, tras deduplicar, 23 — el
  97,7% de sus votos registrados son «Sí» —, que no aguantan ninguna serie: se
  emite vacía a propósito y el frontend explica por qué, en vez de dibujar una
  línea sobre 10 puntos.

OJO 3 · «ALINEACIÓN CON GOBIERNO» ES COINCIDENCIA CON EL PACTO. Se mide igual
  que en la ficha de persona (posición = mayoría del Pacto ≥60%), así que el
  Pacto se alinea consigo mismo por definición (~94%): ese número no dice nada
  de él y así se rotula. Además el Pacto solo ES gobierno desde ago-2022 → se
  emiten las dos: `alineacion` de todo el periodo (comparable con la ficha) y
  `alineacion_petro` desde 2022-08-07, que es la que de verdad significa
  «con el gobierno». El frontend titula la segunda.

OJO 3b · PISO DE QUÓRUM: HAY AÑOS DE CÁMARA QUE NO SON VOTACIONES. Medido, la
  mediana de votantes por votación: 2014-2017 y 2020-2026 rondan 84-115 (una
  plenaria de verdad, la Cámara tiene ~172 miembros), pero 2012 da 2 votantes,
  2018 da 5 y 2019 da 12. Esas actas quedaron parseadas a medias y son
  fragmentos, no plenarias: sacar un Rice de 2 votantes, o declarar «contestada»
  una votación de 12, es ruido con apariencia de dato. Se exige un piso de
  votantes por votación (40 en Cámara, 30 en Senado, cuyo mínimo observado es
  52). Esto retira 2012, 2018 y 2019 casi enteros — 608 votaciones — y por eso
  esos años no salen en la serie.

OJO 4 · SOLO VOTACIONES CONTESTADAS (min lado ≥15%, misma regla que la ficha).
  En una votación unánime el Rice de todos da 1,0 y el bloque 100%: no mide
  disciplina, la simula.

OJO 5 · «Otro» Y «Sin bancada» NO SON BANCADAS. `Otro` es una bolsa de 54
  etiquetas sin relación entre sí (organizaciones CITREP de un solo
  representante, MIRA, Opción Ciudadana, coaliciones). Medir su cohesión, o
  la disidencia contra «su» mayoría, es ruido: sin excluirlas la lista de
  disidentes la encabezaban representantes de CITREP con 50-67%. Se excluyen
  de todo cálculo y su volumen se reporta en `cobertura` para que el hueco se
  vea en vez de taparse. Se conserva la taxonomía exacta de
  build_votaciones_senado_s3.canon_bancada (no se bifurca) para que la bancada
  que muestra la ficha de una persona sea la misma que muestra esta vista.

Uso:  python3 tools/caudal/build_bancadas_s3.py
      # → Bases de datos/leyes-senado/dist/s3/bancadas.json
"""
import collections
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DIST = REPO / 'Bases de datos' / 'leyes-senado' / 'dist'
OUT = DIST / 's3'

# taxonomía compartida con los builds de voto nominal — no bifurcar (OJO 5)
from build_votaciones_senado_s3 import canon_bancada           # noqa: E402

NO_BANCADA = {'Otro', 'Sin bancada'}
MIN_MIEMBROS = 5      # miembros votando Sí/No para calcular Rice de esa bancada
MIN_VOTACIONES = 15   # votaciones con quórum de bancada para listarla
MIN_SERIE = 25        # votaciones contestadas para que un periodo entre a la serie
# votos evaluables para entrar al ranking de disidentes. En Cámara sobra material
# (1.734 contestadas); en Senado el techo es 23, así que un umbral común dejaría
# la lista vacía. Se baja para el Senado y la UI muestra siempre "d de n".
MIN_DISIDENTE = {'camara': 60, 'senado': 12}
# piso de votantes para que una votación cuente como plenaria (OJO 3b)
MIN_VOTANTES = {'camara': 40, 'senado': 30}
BLOQUE = 0.90         # ≥90% del mismo lado = "votó en bloque"
CONTESTADA = 0.15     # min(Sí,No) ≥ 15% del total Sí+No
GOB_MAY = 0.60        # mayoría del Pacto que fija la posición de gobierno
PETRO = '2022-08-07'  # posesión — desde aquí «Pacto» = gobierno


# ---------------------------------------------------------------- carga
def _rows_camara():
    """Voto nominal de Cámara: nativo + OCR DCN-SW (descarta confianza baja)."""
    for line in open(DIST / 'votaciones-camara-nominal.jsonl', encoding='utf-8'):
        yield json.loads(line)
    ocr = DIST / 'votaciones-camara-nominal-ocr.jsonl'
    if ocr.exists():
        for line in open(ocr, encoding='utf-8'):
            r = json.loads(line)
            if r.get('confianza') != 'baja':
                yield r


def _rows_senado():
    for line in open(DIST / 'votaciones-senado-api.jsonl', encoding='utf-8'):
        yield json.loads(line)


def _key_camara(r):
    # el OCR no trae votacion_numero → keyear por 'archivo' (único por voto)
    vk = r.get('votacion_numero')
    if vk is None:
        vk = r.get('archivo') or r.get('votacion_nombre')
    return f"{r['acta_id']}|{vk}"


def _persona_camara(r):
    return r.get('roster_key') or r.get('congresista') or r.get('email') or ''


def _persona_senado(r):
    # mismo criterio que build_votaciones_senado_s3: roster_key, o el nombre
    return r.get('roster_key') or (r.get('congresista') or '').upper()


def agrupar(rows, keyf, personaf, proyectof=None):
    """{votacion → [(persona, respuesta, bancada, fecha)]} + cobertura.
    `proyectof` marca el proyecto de cada votación; si viene, se usa para
    deduplicar votaciones republicadas (OJO 1b)."""
    V = collections.defaultdict(list)
    proy = {}
    cob = {'n_votos': 0, 'sin_partido': 0, 'por_bancada': collections.Counter(),
           'personas': collections.defaultdict(set), 'fechas': []}
    nombres = {}
    for r in rows:
        resp = r.get('respuesta')
        if not resp:
            continue
        p = personaf(r)
        if not p:
            continue
        raw = (r.get('partido') or '').strip()
        b = canon_bancada(raw)
        f = (r.get('fecha') or '')[:10]
        cob['n_votos'] += 1
        if not raw:
            cob['sin_partido'] += 1
        cob['por_bancada'][b] += 1
        cob['personas'][b].add(p)
        if f:
            cob['fechas'].append(f)
        nombres.setdefault(p, r.get('congresista') or p)
        k = keyf(r)
        V[k].append((p, resp, b, f))
        if proyectof:
            proy[k] = proyectof(r)
    return V, cob, nombres, proy


def dedup(limpias, proy):
    """Colapsa votaciones con la MISMA firma (proyecto + lista exacta
    persona→voto), conservando la más antigua. Solo para fuentes que republican
    la misma votación en varias fechas — hoy, el Senado (OJO 1b)."""
    best = {}
    for vid, vs in limpias.items():
        firma = (proy.get(vid), frozenset((p, resp) for (p, resp, b, f) in vs))
        if firma not in best or vid < best[firma]:
            best[firma] = vid
    keep = set(best.values())
    return {k: v for k, v in limpias.items() if k in keep}


# ---------------------------------------------------------------- métricas
def analizar(V, cob, nombres, roster, serie_de, min_disidente, min_votantes, proy=None):
    """serie_de(fecha) → etiqueta de periodo (año o era), o None para omitir.
    `proy` no vacío activa la deduplicación de votaciones republicadas."""
    n_total = len(V)
    n_sucia = n_chica = 0
    limpias = {}
    for k, vs in V.items():
        c = collections.Counter(x[0] for x in vs)
        if max(c.values()) > 1:     # OJO 1
            n_sucia += 1
            continue
        if len(vs) < min_votantes:  # OJO 3b — fragmento, no plenaria
            n_chica += 1
            continue
        limpias[k] = vs
    n_limpias = len(limpias)
    if proy:
        limpias = dedup(limpias, proy)      # OJO 1b
    n_dup = n_limpias - len(limpias)

    banc = collections.defaultdict(lambda: {
        'rice': [], 'bloque': 0, 'n': 0,
        'ali_a': 0, 'ali_n': 0, 'ali_ap': 0, 'ali_np': 0})
    serie = collections.defaultdict(lambda: collections.defaultdict(list))
    serie_n = collections.Counter()
    dis = collections.defaultdict(lambda: {'n': 0, 'd': 0, 'b': collections.Counter()})
    n_cont = 0

    for k, vs in limpias.items():
        tally = collections.Counter(x[1] for x in vs)
        si, no = tally.get('Si', 0), tally.get('No', 0)
        if si + no == 0 or min(si, no) < CONTESTADA * (si + no):
            continue                                            # OJO 4
        n_cont += 1
        fecha = next((x[3] for x in vs if x[3]), '')
        per = serie_de(fecha)
        if per:
            serie_n[per] += 1

        # posición de gobierno = mayoría del Pacto ≥60% (misma regla que la ficha)
        pc = collections.Counter(x[1] for x in vs
                                 if x[2] == 'Pacto/izq' and x[1] in ('Si', 'No'))
        gob = None
        if pc:
            top = pc.most_common(1)[0]
            if top[1] >= GOB_MAY * sum(pc.values()):
                gob = top[0]

        mayoria = {}
        for b in {x[2] for x in vs}:
            if b in NO_BANCADA:                                 # OJO 5
                continue
            t = collections.Counter(x[1] for x in vs
                                    if x[2] == b and x[1] in ('Si', 'No'))
            s, n = t.get('Si', 0), t.get('No', 0)
            if s + n < MIN_MIEMBROS:
                continue
            st = banc[b]
            rice = abs(s - n) / (s + n)
            st['rice'].append(rice)
            st['n'] += 1
            if max(s, n) >= BLOQUE * (s + n):
                st['bloque'] += 1
            if per:
                serie[per][b].append(rice)
            if s != n:      # empate exacto → sin mayoría contra la cual disentir
                mayoria[b] = 'Si' if s > n else 'No'

        for (p, resp, b, f) in vs:
            if b in mayoria and resp in ('Si', 'No'):
                d = dis[p]
                d['n'] += 1
                d['b'][b] += 1
                if resp != mayoria[b]:
                    d['d'] += 1
            if gob and b not in NO_BANCADA:
                st = banc[b]
                st['ali_n'] += 1
                if resp == gob:
                    st['ali_a'] += 1
                if f >= PETRO:                                  # OJO 3
                    st['ali_np'] += 1
                    if resp == gob:
                        st['ali_ap'] += 1

    bancadas = []
    for b, st in banc.items():
        if st['n'] < MIN_VOTACIONES:
            continue
        bancadas.append({
            'bancada': b,
            'n_votaciones': st['n'],
            'rice': round(sum(st['rice']) / st['n'], 3),
            'bloque_pct': round(100 * st['bloque'] / st['n'], 1),
            'alineacion': round(100 * st['ali_a'] / st['ali_n']) if st['ali_n'] else None,
            'n_alineacion': st['ali_n'],
            'alineacion_petro': round(100 * st['ali_ap'] / st['ali_np']) if st['ali_np'] else None,
            'n_alineacion_petro': st['ali_np'],
            'n_miembros': len(cob['personas'][b]),
            'n_votos': cob['por_bancada'][b],
            'es_gobierno': b == 'Pacto/izq',
        })
    bancadas.sort(key=lambda x: -x['rice'])

    listadas = {x['bancada'] for x in bancadas}
    out_serie = []
    for per in sorted(serie_n):
        if serie_n[per] < MIN_SERIE:                            # OJO 2
            continue
        pts = {b: round(sum(v) / len(v), 3)
               for b, v in serie[per].items()
               if b in listadas and len(v) >= 8}
        if pts:
            out_serie.append({'periodo': per, 'n_contestadas': serie_n[per], 'rice': pts})

    disidentes = []
    for p, d in dis.items():
        if d['n'] < min_disidente or not d['b']:
            continue
        b = d['b'].most_common(1)[0][0]
        disidentes.append({
            'key': p,
            'nombre': (roster.get(p, {}) or {}).get('display') or nombres.get(p, p).title(),
            'bancada': b,
            'n': d['n'], 'd': d['d'],
            'pct': round(100 * d['d'] / d['n'], 1),
        })
    disidentes.sort(key=lambda x: -x['pct'])
    evaluables = len(disidentes)
    medianas = sorted(x['pct'] for x in disidentes)
    mediana = medianas[len(medianas) // 2] if medianas else None

    fechas = sorted(cob['fechas'])
    nv = cob['n_votos'] or 1
    no_asig = sum(cob['por_bancada'][b] for b in NO_BANCADA)
    return {
        'cobertura': {
            'n_votos': cob['n_votos'],
            'n_votaciones': n_total,
            'n_descartadas_repetido': n_sucia,
            'n_descartadas_sin_quorum': n_chica,
            'min_votantes': min_votantes,
            'n_descartadas_duplicado': n_dup,
            'n_analizadas': len(limpias),
            'n_contestadas': n_cont,
            'pct_contestadas': round(100 * n_cont / max(1, len(limpias)), 1),
            'sin_partido': cob['sin_partido'],
            'pct_sin_partido': round(100 * cob['sin_partido'] / nv, 1),
            'no_asignado': no_asig,
            'pct_no_asignado': round(100 * no_asig / nv, 1),
            'desde': fechas[0] if fechas else '',
            'hasta': fechas[-1] if fechas else '',
        },
        'bancadas': bancadas,
        'serie': out_serie,
        'disidentes': disidentes[:20],
        'disidentes_meta': {'n_evaluables': evaluables, 'mediana_pct': mediana,
                            'min_votos': MIN_DISIDENTE},
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        roster = json.load(open(DIST / 'roster-autores.json', encoding='utf-8'))['roster']
    except Exception:
        roster = {}

    # --- Cámara: serie por AÑO (~1.734 contestadas lo aguantan). Sin dedup: el
    # acta numera cada votación, así que sus firmas repetidas son votos reales.
    Vc, cobc, nomc, _ = agrupar(_rows_camara(), _key_camara, _persona_camara)
    camara = analizar(Vc, cobc, nomc, roster, lambda f: f[:4] if f else None,
                      MIN_DISIDENTE['camara'], MIN_VOTANTES['camara'])
    camara.update({
        'nombre': 'Cámara de Representantes',
        'fuente': 'actas de plenaria · voto nominal electrónico + OCR DCN-SW (2014-2017)',
        'alcance': 'Registra Sí / No / Abstención. Sin cobertura 2010-2013: '
                   'esas actas son resúmenes narrativos, no listan el voto por '
                   'representante.',
        'serie_tipo': 'anio',
    })

    # --- Senado: deduplicado (OJO 1b) y sin serie — 23 contestadas no la aguantan
    def era(f):
        if not f:
            return None
        return 'Duque 2017-2022' if f < PETRO else 'Petro 2022-2026'

    Vs, cobs, noms, proys = agrupar(_rows_senado(), lambda r: r['votacion_id'],
                                    _persona_senado, lambda r: r.get('senado_proyecto_id'))
    senado = analizar(Vs, cobs, noms, roster, era, MIN_DISIDENTE['senado'],
                      MIN_VOTANTES['senado'], proy=proys)
    senado.update({
        'nombre': 'Senado',
        'fuente': 'API pública app.senado.gov.co (/backend/api/public/v1/votes)',
        'alcance': 'Desde 2017 y SOLO Sí/No: la fuente no registra abstención ni '
                   '«no votó», así que quien se abstiene es invisible. Su llave '
                   '(fecha, proyecto) agrupa las votaciones del mismo día y '
                   'republica la misma votación en varias fechas, así que se '
                   'descartan las que repiten senador y las firmas duplicadas.',
        'serie_tipo': 'era',
        'nota_serie': 'Sin serie temporal: tras deduplicar quedan muy pocas '
                      'votaciones contestadas para medir evolución sin inventar '
                      'precisión.',
    })

    out = {
        'meta': {
            'v': '2026-07-31',
            'que_mide': 'Disciplina de bancada: qué tan en bloque vota cada partido, '
                        'con quién coincide y quién se le sale.',
            'rice': 'Índice de Rice por votación: |Sí−No| / (Sí+No) dentro de la '
                    'bancada. 1,0 = votó en bloque perfecto; 0 = partida por la '
                    'mitad. Se promedia sobre las votaciones contestadas en que la '
                    f'bancada puso al menos {MIN_MIEMBROS} votantes.',
            'bloque': f'Votaciones donde ≥{int(BLOQUE*100)}% de la bancada votó del mismo lado.',
            'contestada': f'min(Sí,No) ≥ {int(CONTESTADA*100)}% del total. Las unánimes '
                          'se excluyen: ahí el Rice da 1,0 para todos y no mide nada.',
            'alineacion': 'Coincidencia con la posición del Pacto (mayoría ≥60%), misma '
                          'regla que la ficha de cada congresista. El Pacto coincide '
                          'consigo mismo por definición. `alineacion_petro` la restringe '
                          f'a {PETRO} en adelante, que es cuando el Pacto es gobierno.',
            'disidente': 'Porcentaje de votaciones contestadas en que la persona votó '
                         'contra la mayoría de su propia bancada. El mínimo de '
                         'votaciones evaluables para entrar al ranking va en '
                         '`disidentes_meta.min_votos` de cada cámara: '
                         f"{MIN_DISIDENTE['camara']} en Cámara y {MIN_DISIDENTE['senado']} "
                         'en Senado, donde el techo son las pocas votaciones '
                         'contestadas que quedan tras deduplicar.',
            'excluidos': '«Otro» y «Sin bancada» no entran a ningún cálculo: la primera '
                         'es una bolsa de partidos sin relación entre sí (CITREP, MIRA, '
                         'coaliciones) y no tiene una mayoría contra la cual medir. Su '
                         'volumen va en `cobertura.no_asignado`.',
            'no_comparable': 'Las dos cámaras no se promedian entre sí: cubren periodos '
                             'distintos, el Senado no registra abstención y su volumen '
                             'de votaciones contestadas es un orden de magnitud menor.',
            'duplicados': 'El Senado republica la misma votación (lista idéntica de '
                          'senador→voto) en varias fechas; se conserva solo la primera. '
                          'En Cámara no aplica: ahí cada votación viene numerada por el acta.',
        },
        'camara': camara,
        'senado': senado,
    }
    f = OUT / 'bancadas.json'
    json.dump(out, open(f, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'→ {f.relative_to(REPO)} ({f.stat().st_size/1024:.1f} KB)')
    for k in ('camara', 'senado'):
        d = out[k]
        c = d['cobertura']
        print(f"\n=== {d['nombre']} · {c['desde']} → {c['hasta']}")
        print(f"  {c['n_votaciones']} votaciones − {c['n_descartadas_repetido']} con voto repetido "
              f"− {c['n_descartadas_sin_quorum']} sin quórum (<{c['min_votantes']} votantes) "
              f"− {c['n_descartadas_duplicado']} republicadas = {c['n_analizadas']} analizadas "
              f"· {c['n_contestadas']} contestadas ({c['pct_contestadas']}%)")
        print(f"  {c['n_votos']:,} votos · sin partido {c['pct_sin_partido']}% · fuera de bancada {c['pct_no_asignado']}%")
        print(f"  {'bancada':20s} {'n':>5s} {'Rice':>6s} {'bloque':>8s} {'alin.Petro':>11s}")
        for b in d['bancadas']:
            ap = f"{b['alineacion_petro']}%" if b['alineacion_petro'] is not None else '—'
            print(f"  {b['bancada']:20s} {b['n_votaciones']:5d} {b['rice']:6.3f} "
                  f"{b['bloque_pct']:7.1f}% {ap:>11s}{'  (es el gobierno)' if b['es_gobierno'] else ''}")
        print(f"  serie ({d['serie_tipo']}): {[s['periodo'] for s in d['serie']]}")
        dm = d['disidentes_meta']
        print(f"  disidentes: {dm['n_evaluables']} evaluables · mediana {dm['mediana_pct']}%")
        for x in d['disidentes'][:5]:
            print(f"    {x['pct']:5.1f}%  {x['d']:3d}/{x['n']:3d}  {x['bancada']:20s} {x['nombre'][:38]}")


if __name__ == '__main__':
    main()
