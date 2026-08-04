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
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import features as F   # noqa: E402


# ===========================================================================
# EJE 1 · AVANCE
# ===========================================================================
# BANDAS, NO PORCENTAJES.
#
# El modelo ORDENA bien y EXAGERA el nivel: en la validación out-of-time el
# decil superior predice 0,69 y observa 0,57. Se probó recalibración isotónica
# ajustada en 2015-2019 y medida en 2020-2024: arregla el decil alto (0,65/0,56
# → 0,52/0,55) pero invierte los bajos (el primer decil pasa de 0,021/0,009 a
# 0,006/0,023) y el Brier no se mueve (0,1455 → 0,1454). O sea que no endereza
# el nivel: mueve el error de sitio. Así que no se publica un porcentaje que no
# se sostiene.
#
# Lo que SÍ se sostiene son las bandas. Medidas sobre los 3.653 proyectos del
# test out-of-time, con la tasa real de cada una:
#
#     alto       n=  511   llegaron a ley  51,9%
#     medio      n=  868                   28,6%
#     bajo       n= 1495                   15,2%
#     casi nulo  n=  779                    5,6%
#
# Monótonas, bien separadas y con n grande en las cuatro. El porcentaje sigue
# viajando en `p_ley` para quien quiera el detalle técnico, pero la cifra que
# se muestra es la banda.
BANDAS = [(0.40, 'alto', 51.9), (0.20, 'medio', 28.6),
          (0.08, 'bajo', 15.2), (0.0, 'casi nulo', 5.6)]


def banda_de(p):
    for corte, nombre, observado in BANDAS:
        if p >= corte:
            return {'banda': nombre, 'corte_inferior': corte,
                    'observado_historico': observado,
                    'dice': f'de los proyectos que el modelo puso en «{nombre}» '
                            f'entre 2015 y 2024, llegó a ley el {observado:.1f}%'}
    return {'banda': 'casi nulo', 'corte_inferior': 0.0,
            'observado_historico': 5.6, 'dice': ''}


def eje_avance(rec, modelo, autores_idx=None, bloqueo=None, ref=None):
    """→ {banda, p_ley, factores, bloqueo}

    La salida pública es `banda`. `p_ley` va como detalle técnico y `score`
    se conserva para poder ordenar, no para mostrarse como cifra.
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
    out['banda'] = banda_de(out['score'] / 100.0)
    out['aviso_nivel'] = ('el modelo ordena mejor de lo que calibra: use la '
                          'banda, no el porcentaje')
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
    'respaldo_de_bloque': 28,  # ¿cuánta maquinaria hay detrás de la radicación?
    'cohesion_bancada': 18,    # ¿la firma es de un bloque o es transversal?
    'persistencia': 24,        # re-radicado sin pasar = lo sostienen por lo que dice
    'agenda_ejecutivo': 16,    # lo radica el Gobierno: es programa, no iniciativa suelta
    'rango_normativo': 14,     # cambiar las reglas del juego, no una regla
}
# Honores, conmemoraciones y leyes aprobatorias de tratado no son política de
# bloque aunque las firmen veinte o las radique un ministro: son trámite.
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
    # Cuánta maquinaria hay detrás de la radicación. Se expresa de dos formas
    # distintas según quién radique, y las dos son la MISMA señal:
    #   · un congresista → cuántos colegas firmaron (1 firma = 0 · 10 = 0,5 · 30+ = 1)
    #   · el Ejecutivo   → máximo, porque radicar como Gobierno ES el acto de
    #                      bloque más grande que existe.
    #
    # Esto se corrigió con el test retrospectivo sobre 2022-2026 y era un fallo,
    # no un matiz: `autoria()` deja n_firmantes en 0 para autor institucional, así
    # que las reformas del Gobierno sacaban CERO en el componente que más pesa. La
    # reforma pensional —la bandera del cuatrienio, y además aprobada— quedaba en
    # el puesto 1.629 de 3.053. Con el arreglo sube al 169, y la laboral que se
    # volvió ley pasa del 982 al 52.
    if inst:
        c['respaldo_de_bloque'] = 1.0
    else:
        c['respaldo_de_bloque'] = (0.0 if nf <= 1 else
                                   min(1.0, (nf - 1) / 29.0 * 0.55
                                       + min(nf, 12) / 12.0 * 0.45))

    coh = _cohesion(rec, partidos)
    # Si no es calculable, el componente NO aporta cero disimulado: se saca del
    # score y el total se renormaliza sobre los componentes que sí se midieron.
    # Contarlo como cero castigaría a los proyectos por un hueco del registro
    # autor→partido, no por lo que hicieron.
    calc = bool(coh and coh.get('calculable'))
    if calc:
        c['cohesion_bancada'] = coh['valor']

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

    disponible = sum(POLITICO_PESOS[k] for k in c)
    score = sum(POLITICO_PESOS[k] * v for k, v in c.items())
    if disponible < 100:            # renormaliza sobre lo que sí se pudo medir
        score = score * 100.0 / disponible
    # Sin esta línea, dar respaldo máximo al Gobierno llenaba el top de leyes
    # aprobatorias de tratado: el Ejecutivo radica decenas al año y son trámite,
    # no bandera. Se midió en el test retrospectivo antes de dejarlo así.
    es_tramite = tip == 'honores' or _es_tratado(rec)
    if es_tramite:
        score *= PENALIZACION_TRAMITE_MENOR

    return {
        'score': round(min(100.0, score), 1),
        'componentes': {k: round(POLITICO_PESOS[k] * v, 1) for k, v in c.items()},
        'n_firmantes': nf, 'radicaciones_previas': ant['n_previos'],
        'antecedentes_via': via,
        'antecedentes': ant.get('ejemplos') or [],
        'cohesion': coh,
        'componentes_medidos': sorted(c),
        'componentes_no_medidos': ([] if calc else ['cohesion_bancada']),
        'base_del_score': round(disponible, 1),
        'etiqueta': ('tramite_menor' if es_tramite
                     else _etiqueta(c, coh if calc else None, inst, tip, ant)),
        'metodo': 'heuristica declarada — no validada contra desenlace (ver README)',
    }


_TRATADO_EXTRA = re.compile(
    r'\b(se aprueba|aprobatoria)\b.{0,90}'
    r'\b(acuerdo|convenio|tratado|protocolo|estatuto|memorando|enmienda|carta)\b')


def _es_tratado(rec):
    """Ley aprobatoria de instrumento internacional. Se usa el detector de
    features y además una forma más laxa: el registro escribe «se aprueba el
    "Estatuto de la Conferencia..."» y esa variante se colaba al top."""
    t = F._n(rec.get('titulo'))
    return bool(F._TRATADO.search(t) or _TRATADO_EXTRA.search(t))


MIN_FIRMAS_COHESION = 3


def _cohesion(rec, partidos):
    """Fracción de firmantes del partido más frecuente.

    Alta con muchas firmas = bloque cerrando filas. Baja = coalición amplia, que
    en Colombia suele leerse como consenso o como reparto, no como bandera.

    NUNCA devuelve None en silencio. «No se pudo calcular» y «la firma es
    transversal» son cosas distintas y confundirlas es un error caro: hoy solo
    77 de 214 proyectos vivos tienen partido conocido para al menos tres
    firmantes, así que si el componente aportara cero sin decirlo, 137
    proyectos parecerían medidos como transversales cuando en realidad no se
    midieron. Se devuelve siempre un dict con `calculable`, y el que no lo es
    trae el motivo.
    """
    ks = rec.get('autores_keys') or []
    if not partidos:
        return {'calculable': False, 'motivo': 'sin_registro_de_partidos',
                'dice': 'no se pudo calcular: falta el registro autor→partido',
                'n_firmantes': len(ks)}
    if rec.get('autor_tipo') == 'institucional':
        return {'calculable': False, 'motivo': 'autor_institucional',
                'dice': 'no aplica: lo radica una entidad, no una bancada',
                'n_firmantes': 0}
    if len(ks) < MIN_FIRMAS_COHESION:
        return {'calculable': False, 'motivo': 'pocos_firmantes',
                'dice': f'no aplica: {len(ks)} firmante(s), se necesitan '
                        f'{MIN_FIRMAS_COHESION}',
                'n_firmantes': len(ks)}
    ps = [partidos[k].get('partido') for k in ks
          if k in partidos and partidos[k].get('partido')]
    if len(ps) < MIN_FIRMAS_COHESION:
        return {'calculable': False, 'motivo': 'partido_desconocido',
                'dice': f'no se pudo calcular: de {len(ks)} firmantes solo se '
                        f'conoce el partido de {len(ps)}',
                'n_firmantes': len(ks), 'n_con_partido': len(ps)}
    top = max(set(ps), key=ps.count)
    frac = ps.count(top) / len(ps)
    return {'calculable': True, 'valor': round(frac, 3), 'partido_dominante': top,
            'n_con_partido': len(ps), 'n_firmantes': len(ks),
            'partidos_distintos': len(set(ps)),
            'cobertura': round(len(ps) / len(ks), 2),
            'lectura': ('bancada cerrando filas' if frac >= 0.7 else
                        'coalición estrecha' if frac >= 0.45 else
                        'firma transversal entre partidos'),
            'dice': (f'{ps.count(top)} de los {len(ps)} firmantes con partido '
                     f'conocido son de {top}')}


def _etiqueta(c, coh, inst, tip, ant):
    c = {'respaldo_de_bloque': 0.0, 'persistencia': 0.0, **c}
    if tip == 'honores':
        return 'tramite_menor'
    if inst:
        return 'agenda_de_gobierno'
    if c['persistencia'] >= 0.45 and c['respaldo_de_bloque'] >= 0.35:
        return 'bandera_sostenida'
    if c['respaldo_de_bloque'] >= 0.6 and coh and coh['valor'] >= 0.6:
        return 'bandera_de_bloque'
    if c['respaldo_de_bloque'] >= 0.5 and coh and coh['valor'] < 0.45:
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


def _firma_razones(it):
    return tuple(sorted(f['factor'] for f in it['avance']['factores']))


def _desempatar(rank, k=4):
    """Cuando dos vecinos del ranking traen EXACTAMENTE las mismas razones, la
    explicación deja de explicar: es el defecto que criticamos del motor de
    alertas, reproducido acá. Pasaba con los tres primeros del lente de riesgo,
    que decían palabra por palabra 'está en Tercera… lo firma alguien que
    radica mucho'.

    El arreglo es bajar a lo que sí los distingue. Cuando un grupo comparte
    razones, se busca la diferencia real —impacto, obligaciones, sanciones,
    peso político, agendamientos— y se dice cuál es, incluyendo el caso honesto
    de que la diferencia sea mínima.
    """
    grupos = {}
    for it in rank:
        grupos.setdefault(_firma_razones(it), []).append(it)

    for firma, grupo in grupos.items():
        if len(grupo) < 2:
            continue
        for i, it in enumerate(grupo):
            otros = [o for o in grupo if o is not it]
            it['razones_compartidas_con'] = len(otros)
            it['distingue'] = _distingue(it, otros, grupo, i)


def _cmp_campos(it):
    im = it.get('impacto') or {}
    po = it.get('politico') or {}
    return {
        'impacto': im.get('score'),
        'obligaciones': im.get('n_obligaciones'),
        'sanciones': im.get('n_sanciones'),
        'vigilancia': im.get('n_vigilancia'),
        'politico': po.get('score'),
        'firmantes': po.get('n_firmantes'),
        'radicaciones_previas': po.get('radicaciones_previas'),
        'agendamientos': (it['avance'].get('bloqueo') or {}).get('n'),
    }


# Cada campo con sus DOS lecturas: la diferencia puede ir en cualquier
# dirección, y una frase que solo sirva para arriba produce sinsentidos del
# tipo "trae régimen sancionatorio y el otro no (0 contra 3)".
_COMO_SE_DICE = {
    'impacto': ('su articulado pesa más ({a} contra {b})',
                'su articulado pesa menos ({a} contra {b})'),
    'obligaciones': ('crea más obligaciones nuevas ({a} contra {b})',
                     'crea menos obligaciones nuevas ({a} contra {b})'),
    'sanciones': ('trae régimen sancionatorio y los otros casi no ({a} contra {b})',
                  'no trae régimen sancionatorio y los otros sí ({a} contra {b})'),
    'vigilancia': ('crea más vigilancia ({a} contra {b})',
                   'crea menos vigilancia ({a} contra {b})'),
    'politico': ('carga más peso político ({a} contra {b})',
                 'carga menos peso político ({a} contra {b})'),
    'firmantes': ('lo firman más congresistas ({a} contra {b})',
                  'lo firman menos congresistas ({a} contra {b})'),
    'radicaciones_previas': ('lo han vuelto a radicar más veces ({a} contra {b})',
                             'no lo habían radicado antes y a los otros sí ({a} contra {b})'),
    'agendamientos': ('ya lo agendaron más veces ({a} contra {b})',
                      'lo han agendado menos veces ({a} contra {b})'),
}


def _distingue(it, otros, grupo, pos):
    """La diferencia más grande entre este proyecto y sus empatados."""
    mio = _cmp_campos(it)
    mejor = None
    for campo in _COMO_SE_DICE:
        v = mio.get(campo)
        if v is None:
            continue
        vecinos = [_cmp_campos(o).get(campo) for o in otros]
        vecinos = [x for x in vecinos if x is not None]
        if not vecinos:
            continue
        ref = sum(vecinos) / len(vecinos)
        if ref == v:
            continue
        # magnitud relativa, para comparar campos de escalas distintas
        rel = abs(v - ref) / max(abs(v), abs(ref), 1.0)
        if mejor is None or rel > mejor[0]:
            mejor = (rel, campo, v, ref)
    if mejor is None or mejor[0] < 0.12:
        return {'hay_diferencia': False,
                'dice': ('casi empatados: comparten las razones y ninguna otra '
                         'medida los separa de forma apreciable; el orden entre '
                         'ellos no es informativo')}
    _rel, campo, v, ref = mejor
    fmt = (lambda x: f'{x:.0f}' if isinstance(x, float) else str(x))
    arriba, abajo = _COMO_SE_DICE[campo]
    frase = (arriba if v > ref else abajo).format(a=fmt(v), b=fmt(ref))
    return {'hay_diferencia': True, 'campo': campo, 'mayor': v > ref,
            'dice': ('va arriba porque ' if pos == 0 and v > ref
                     else 'se separa porque ') + frase}


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
    _desempatar(rank)
    # los pendientes se ordenan por lo único que sí sabemos de ellos: qué tan
    # probable es que avancen y qué tanto peso político cargan
    pend.sort(key=lambda it: -(_p_efectiva(it) * 100 + it['politico']['score']))
    return {'ranking': rank, 'pendientes': pend, 'fuera': fuera}
