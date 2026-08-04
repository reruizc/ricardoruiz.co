#!/usr/bin/env python3
"""
Caudal · Importancia — las tres coordenadas.

No hay un score único. Un proyecto tiene tres coordenadas independientes y
quien consulta elige el lente:

  1. AVANCE     ¿va a pasar?           modelo calibrado contra 1990-2026
  2. IMPACTO    ¿qué me hace si pasa?  del articulado ya extraído
  3. POLÍTICO   ¿qué significa?        heurística declarada, no medición

Van separadas por una razón concreta, no por prolijidad: la misma señal se lee
al revés según quién pregunte. Un proyecto radicado once veces sin pasar nunca
es basura para un gremio que gestiona riesgo regulatorio y es el mejor
indicador disponible de qué defiende un bloque político para quien lee la
política. Vitrina y bandera son el MISMO dato con dos lentes. Si se penalizara
la importancia por la probabilidad, se borraría justo lo que hace visible el
segundo caso.

Los pesos del eje 2 y del eje 3 están arriba de sus funciones, en un diccionario
editable, y viajan en la respuesta. No son "el modelo": son un criterio
editorial explícito que se puede discutir renglón por renglón.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import features as F   # noqa: E402


# ===========================================================================
# EJE 1 · AVANCE
# ===========================================================================
def eje_avance(rec, modelo, autores_idx=None, bloqueo=None, ref=None):
    """→ {p_ley, score, factores, bloqueo}

    `score` es la probabilidad en porcentaje, no un índice inventado: 12
    significa "12% de probabilidad de llegar a ley", que es lo que el modelo
    fue calibrado para decir.
    """
    p = modelo.prob(F.vector(rec, autores_idx))
    out = {
        'p_ley': round(p, 4),
        'score': round(100 * p, 1),
        'factores': F.explicacion(rec, modelo, autores_idx, ref=ref),
    }
    if bloqueo:
        out['bloqueo'] = bloqueo
        aj = _ajuste_bloqueo(bloqueo)
        if aj:
            out['p_ley_ajustada'] = round(min(0.97, max(0.005, p * aj['factor'])), 4)
            out['score'] = round(100 * out['p_ley_ajustada'], 1)
            out['ajuste_bloqueo'] = aj
    return out


# Curva P(tratado | posición en el orden del día), ya medida sobre las órdenes
# del día de las dos cámaras y publicada en bloqueo.json. NO se reajusta aquí:
# se usa como observación externa. El factor es el cociente contra la posición
# de referencia (1º), así que un proyecto que solo aparece de séptimo en la
# agenda pesa menos que uno que encabeza.
_POS_REF = 52.8
_POS_CURVA = [(1, 52.8), (3, 41.2), (6, 28.4), (10, 25.1), (15, 23.8), (99, 27.4)]


def _p_pos(pos):
    for lim, pct in _POS_CURVA:
        if pos <= lim:
            return pct
    return _POS_CURVA[-1][1]


def _ajuste_bloqueo(b):
    """Actualiza el avance con lo que YA se observó en la cola de la agenda.

    Dos efectos opuestos y ambos reales: aparecer en el orden del día es más
    que no aparecer nunca, pero acumular agendamientos sin ser tratado es la
    definición operativa de estar bloqueado. El tope de 1,25 evita que "lo
    agendaron" se convierta por sí solo en "va a pasar".
    """
    n = b.get('n') or 0
    if not n:
        return None
    pos = b.get('pos_prom') or 1
    f_pos = _p_pos(pos) / _POS_REF
    # decaimiento por reincidencia: el 5º agendamiento vale menos que el 1º
    f_rep = 1.0 if n <= 2 else max(0.55, 1.0 - 0.09 * (n - 2))
    factor = min(1.25, max(0.4, 1.15 * f_pos * f_rep))
    return {'factor': round(factor, 3), 'n_agendamientos': n,
            'posicion_promedio': round(pos, 1),
            'nota': f'agendado {n} vez(ces), posición promedio {pos:.1f} '
                    f'en el orden del día'}


# ===========================================================================
# EJE 2 · IMPACTO — qué te hace si pasa
# ===========================================================================
# Criterio editorial explícito. Suman 100. Editables.
IMPACTO_PESOS = {
    'obligaciones': 30,   # cuántos deberes nuevos crea y sobre cuántos sujetos
    'sanciones': 22,      # si hay régimen sancionatorio, deja de ser declarativo
    'modifica': 18,       # tocar una norma viva pesa más que crear una figura
    'vigilancia': 15,     # crear supervisión implica reportar, pedir permiso
    'alcance': 15,        # a cuánta gente y cuántos sectores aplica
}

# Rango de la norma que se toca: cambiar la Constitución o un código no es lo
# mismo que adicionar un artículo suelto.
_RANGO_ALTO = ('constitucion', 'codigo', 'estatuto tributario', 'estatuto')


def eje_impacto(art, perfil=None):
    """art = entrada de articulado.json (o None) → coordenadas de impacto.

    Devuelve None si el proyecto no tiene articulado extraído. NO devuelve 0:
    "no lo hemos leído" y "no te toca" son cosas distintas y confundirlas es
    exactamente el error que originó este encargo.
    """
    if not art:
        return None
    obl = art.get('obligaciones') or []
    san = art.get('sanciones') or []
    mod = art.get('modifica') or []
    vig = art.get('vigilancia') or []
    ap = art.get('aplica_a') or {}
    sujetos = ap.get('sujetos') or []
    sectores = ap.get('sectores') or []

    c = {}
    c['obligaciones'] = min(1.0, len(obl) / 6.0)
    # una sanción con cuantía muerde más que una genérica
    con_cuantia = sum(1 for s in san if s.get('cuantia'))
    c['sanciones'] = min(1.0, (len(san) + con_cuantia) / 4.0) if san else 0.0
    rango = 0.0
    for m in mod:
        n = (m.get('norma') or '').lower()
        rango = max(rango, 1.0 if any(k in n for k in _RANGO_ALTO) else 0.6)
    c['modifica'] = rango
    c['vigilancia'] = min(1.0, len(vig) / 3.0)
    c['alcance'] = min(1.0, (len(sujetos) / 5.0) * 0.6 + (len(sectores) / 4.0) * 0.4)

    score = sum(IMPACTO_PESOS[k] * v for k, v in c.items())
    out = {
        'score': round(score, 1),
        'componentes': {k: round(IMPACTO_PESOS[k] * v, 1) for k, v in c.items()},
        'n_obligaciones': len(obl), 'n_sanciones': len(san),
        'n_vigilancia': len(vig), 'sectores': sectores,
        'confianza': art.get('confianza'),
        'base': art.get('base_txt') or art.get('base'),
    }
    # El extractor marca 'baja' cuando solo tuvo el título. Ese score no es una
    # medición del impacto: es un PISO. Y el sesgo no es aleatorio — las
    # reformas grandes llegan con el texto tarde, así que ordenar por este
    # número las manda al fondo justo cuando más importan. Se marca `parcial`
    # para que el lente de riesgo las saque a un bloque aparte en vez de
    # rankearlas contra proyectos que sí tienen articulado leído.
    if art.get('confianza') == 'baja':
        out['parcial'] = True
        out['aviso'] = ('leído solo del título, no del articulado: esto es un '
                        'piso, no una medida — el impacto real puede ser mucho '
                        'mayor cuando llegue el texto')
    if perfil:
        out['para_ti'] = _impacto_para_perfil(art, perfil, score)
    return out


def _impacto_para_perfil(art, perfil, score):
    """Cruce con lo que el cliente vigila. Sube el impacto si le toca su
    sector, y mucho más si el articulado nombra algo que él vigila."""
    ap = art.get('aplica_a') or {}
    sect_art = {s.lower() for s in (ap.get('sectores') or [])}
    sect_cli = {s.lower() for s in (perfil.get('sectores') or [])}
    coincide = sorted(sect_art & sect_cli)
    texto = ' '.join([art.get('resumen') or ''] +
                     [str(s.get('sobre_quien') or '') for s in (art.get('obligaciones') or [])] +
                     [str(x) for x in (ap.get('sujetos') or [])]).lower()
    nombradas = [e for e in (perfil.get('empresas') or [])
                 if e and len(e) >= 4 and e.lower() in texto]
    mult = 1.0
    if coincide:
        mult += 0.35
    if 'multisectorial' in sect_art and not coincide:
        mult += 0.10
    if nombradas:
        mult += 0.5
    return {'score': round(min(100.0, score * mult), 1),
            'sectores_en_comun': coincide, 'vigiladas_nombradas': nombradas,
            'multiplicador': round(mult, 2)}


# ===========================================================================
# EJE 3 · POLÍTICO — qué significa
# ===========================================================================
# HEURÍSTICA, no medición. Ninguna de estas señales fue validada contra un
# desenlace observable, porque "peso político" no tiene desenlace observable:
# no existe un registro de qué proyecto fue bandera de quién. Lo que hay son
# proxies del comportamiento de la firma, y van declarados como tales.
#
# El eje 1 se puede validar y por eso se validó. Este no, y por eso se firma
# como criterio y no se disfraza de medición.
POLITICO_PESOS = {
    'firma_colectiva': 28,   # 60 firmas no son 60 autores: son un acto de bloque
    'cohesion_bancada': 18,  # ¿la firma es de un bloque o es transversal?
    'persistencia': 24,      # re-radicado sin pasar = lo sostienen por lo que dice
    'agenda_ejecutivo': 16,  # lo radica el Gobierno: es programa, no iniciativa suelta
    'rango_normativo': 14,   # cambiar las reglas del juego, no una regla
}
# los honores y conmemoraciones no son política de bloque aunque los firmen 20
PENALIZACION_TRAMITE_MENOR = 0.35


def eje_politico(rec, partidos=None, art=None, antec=None):
    """→ {score, componentes, lectura, etiqueta}

    `antec` es el índice de antecedentes por parecido de título (opcional, ver
    antecedentes.py). Se toma el máximo entre esa vía y el cluster exacto,
    porque el cluster deja fuera precisamente las reformas de título genérico
    —la de salud entre ellas— y en el eje político la persistencia es la señal
    más limpia que hay.
    """
    nf = rec.get('n_firmantes') or 0
    ant = F.antecedentes(rec)
    via = 'cluster de re-radicación'
    if antec:
        a2 = antec.get(f"{rec.get('tabla', 'pdly')}:{rec.get('id')}")
        if a2 and a2.get('n_previos', 0) > ant['n_previos']:
            ant = {'n_previos': a2['n_previos'],
                   'max_etapa_previa': a2['max_etapa_previa'],
                   'previo_fue_ley': a2.get('alguno_fue_ley', False),
                   'anios_desde_ultimo': None,
                   'ejemplos': a2.get('ejemplos', [])}
            via = 'parecido de título (el cluster exacto no los agrupaba)'
    inst = rec.get('autor_tipo') == 'institucional'
    tabla = rec.get('tabla') or 'pdly'
    tip = rec.get('tipologia') or 'ordinaria'

    c = {}
    # 1 firma = 0 · 10 = 0,5 · 30+ = 1
    c['firma_colectiva'] = 0.0 if nf <= 1 else min(1.0, (nf - 1) / 29.0 * 0.55 + min(nf, 12) / 12.0 * 0.45)

    coh = _cohesion(rec, partidos)
    c['cohesion_bancada'] = coh['valor'] if coh else 0.0

    # sostener una iniciativa que nunca pasa es la señal más limpia de que lo
    # que importa es lo que dice, no lo que logra
    if ant['n_previos'] >= 1:
        base = min(1.0, 0.45 + 0.22 * (ant['n_previos'] - 1))
        c['persistencia'] = base if ant['max_etapa_previa'] <= 1 else base * 0.55
    else:
        c['persistencia'] = 0.0

    c['agenda_ejecutivo'] = 1.0 if inst else 0.0

    rango = 0.0
    if tabla == 'pal':
        rango = 1.0
    elif tip == 'reforma':
        rango = 0.65
    if art:
        for m in (art.get('modifica') or []):
            if 'constitucion' in (m.get('norma') or '').lower():
                rango = 1.0
    c['rango_normativo'] = rango

    score = sum(POLITICO_PESOS[k] * v for k, v in c.items())
    if tip == 'honores':
        score *= PENALIZACION_TRAMITE_MENOR

    return {
        'score': round(min(100.0, score), 1),
        'componentes': {k: round(POLITICO_PESOS[k] * v, 1) for k, v in c.items()},
        'n_firmantes': nf, 'radicaciones_previas': ant['n_previos'],
        'antecedentes_via': via,
        'antecedentes': ant.get('ejemplos') or [],
        'cohesion': coh,
        'etiqueta': _etiqueta(c, coh, inst, tip, ant),
        'metodo': 'heuristica declarada — no validada contra desenlace (ver README)',
    }


def _cohesion(rec, partidos):
    """Fracción de firmantes del partido más frecuente.

    Alta con muchas firmas = bloque cerrando filas. Baja = coalición amplia, que
    en Colombia suele leerse como consenso o como reparto, no como bandera.
    """
    if not partidos:
        return None
    ks = rec.get('autores_keys') or []
    ps = [partidos[k].get('partido') for k in ks
          if k in partidos and partidos[k].get('partido')]
    if len(ps) < 3:
        return None
    top = max(set(ps), key=ps.count)
    frac = ps.count(top) / len(ps)
    return {'valor': round(frac, 3), 'partido_dominante': top,
            'n_con_partido': len(ps), 'n_firmantes': len(ks),
            'partidos_distintos': len(set(ps)),
            'lectura': ('bancada cerrando filas' if frac >= 0.7 else
                        'coalición estrecha' if frac >= 0.45 else
                        'firma transversal entre partidos')}


def _etiqueta(c, coh, inst, tip, ant):
    if tip == 'honores':
        return 'tramite_menor'
    if inst:
        return 'agenda_de_gobierno'
    if c['persistencia'] >= 0.45 and c['firma_colectiva'] >= 0.35:
        return 'bandera_sostenida'
    if c['firma_colectiva'] >= 0.6 and coh and coh['valor'] >= 0.6:
        return 'bandera_de_bloque'
    if c['firma_colectiva'] >= 0.5 and coh and coh['valor'] < 0.45:
        return 'acuerdo_transversal'
    if c['persistencia'] >= 0.45:
        return 'insistencia_individual'
    return 'iniciativa_sectorial'


# ===========================================================================
# COORDENADAS + LENTES
# ===========================================================================
def coordenadas(rec, modelo, autores_idx=None, art=None, partidos=None,
                bloqueo=None, perfil=None, ref=None, antec=None):
    av = eje_avance(rec, modelo, autores_idx, bloqueo, ref)
    im = eje_impacto(art, perfil)
    po = eje_politico(rec, partidos, art, antec)
    return {
        'tok': f"{rec.get('tabla', 'pdly')}:{rec.get('id')}",
        'numero': rec.get('numero_senado') or rec.get('numero_camara'),
        'titulo': rec.get('titulo'),
        'comision': rec.get('comision'),
        'autor': rec.get('autor_principal') or rec.get('entidad'),
        'legislatura': rec.get('legislatura'),
        'avance': av, 'impacto': im, 'politico': po,
    }


# Cada lente ordena por una cosa distinta y lo dice. El de riesgo es el único
# que combina, y lo hace por una razón que no es un peso a ojo: el riesgo
# esperado de una norma es lo que te hace multiplicado por la probabilidad de
# que llegue a hacértelo. Es una esperanza, no una ponderación arbitraria.
LENTES = {
    'riesgo': {
        'nombre': 'Riesgo regulatorio',
        'para': 'gremio o empresa que gestiona exposición normativa',
        'ordena': 'impacto × probabilidad de que pase (valor esperado)',
        'requiere_articulado': True,
    },
    'politico': {
        'nombre': 'Lectura política',
        'para': 'quien necesita saber qué se está jugando, pase o no pase',
        'ordena': 'carga política, IGNORANDO la probabilidad de avance',
        'requiere_articulado': False,
    },
    'agenda': {
        'nombre': 'Lo que se va a mover',
        'para': 'quien planea la agenda de las próximas semanas',
        'ordena': 'probabilidad de avance',
        'requiere_articulado': False,
    },
    'impacto': {
        'nombre': 'Lo que más cambia',
        'para': 'quien quiere el articulado más pesado, pase o no',
        'ordena': 'impacto del articulado',
        'requiere_articulado': True,
    },
}


def _p_efectiva(it):
    a = it['avance']
    return a.get('p_ley_ajustada', a['p_ley'])


def ordenar(items, lente='riesgo'):
    """Ordena por el lente pedido → {ranking, pendientes, fuera}.

    Tres listas y no una porque el lente no puede desaparecer nada en silencio.
    `pendientes` son los que todavía no tenemos leídos completos: van visibles y
    aparte, nunca mezclados en el ranking con un impacto que sabemos que es un
    piso. `fuera` son los que ese lente no puede evaluar.
    """
    def key_riesgo(it):
        im = it.get('impacto')
        if not im:
            return None
        base = (im.get('para_ti') or {}).get('score', im['score'])
        return base * _p_efectiva(it)

    keys = {
        'riesgo': key_riesgo,
        'politico': lambda it: it['politico']['score'],
        'agenda': lambda it: it['avance']['score'],
        'impacto': lambda it: (it['impacto'] or {}).get('score'),
    }
    kf = keys.get(lente, key_riesgo)
    requiere = LENTES.get(lente, {}).get('requiere_articulado', False)

    rank, pend, fuera = [], [], []
    for it in items:
        im = it.get('impacto')
        if requiere and not im:
            fuera.append({'tok': it['tok'], 'titulo': it['titulo'],
                          'motivo': 'sin articulado extraído'})
            continue
        v = kf(it)
        if v is None:
            fuera.append({'tok': it['tok'], 'titulo': it['titulo'],
                          'motivo': 'sin dato para este lente'})
            continue
        it['orden'] = round(v, 2)
        if requiere and im and im.get('parcial'):
            pend.append(it)
        else:
            rank.append(it)

    rank.sort(key=lambda it: -it['orden'])
    # los pendientes se ordenan por lo único que sí sabemos de ellos: qué tan
    # probable es que avancen y qué tanto peso político cargan
    pend.sort(key=lambda it: -(_p_efectiva(it) * 100 + it['politico']['score']))
    return {'ranking': rank, 'pendientes': pend, 'fuera': fuera}
