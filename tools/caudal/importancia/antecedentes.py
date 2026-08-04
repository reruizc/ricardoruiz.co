#!/usr/bin/env python3
"""
Caudal · Importancia — antecedentes por parecido de título.

POR QUÉ EXISTE. `clasificar.py` agrupa las re-radicaciones por firma EXACTA de
tokens significativos, y es conservador a propósito: prefiere sub-agrupar antes
que fusionar iniciativas distintas y colgarle a alguien un 'vitrina' que no le
toca. Correcto para lo que hace. Pero tiene un efecto secundario medido y grave
para el eje político: `titulo_signature()` devuelve None cuando quedan menos de
tres tokens significativos, y entonces el proyecto queda en un cluster de uno
solo.

Justo eso le pasa a la reforma a la salud. Los tres títulos

    216/23   POR MEDIO DE LA CUAL SE TRANSFORMA EL SISTEMA DE SALUD EN COLOMBIA…
    410/25   POR MEDIO DEL CUAL SE TRANSFORMA EL SISTEMA DE SALUD Y SE DICTAN…
    024/2026 POR MEDIO DEL CUAL SE TRANSFORMA EL SISTEMA DE SALUD EN COLOMBIA…

reducen a {transform, salud}: dos tokens, bajo el mínimo. Resultado: clusters
12290, 12301 y 12311 — la misma reforma contada tres veces como si fuera nueva,
y persistencia cero en el eje político justo en el proyecto que un experto
señaló como el que más importa. La consecuencia es sistemática, no anecdótica:
los títulos genéricos son los de las reformas grandes.

Esto no reemplaza el clustering: lo complementa por otra vía (parecido, no
identidad) y SOLO alimenta el eje 3, que es heurística declarada. El eje 1
sigue usando `historial_reradicacion` tal cual, para no invalidar una
calibración ya validada con una señal nueva sin volver a medirla.
"""
import re
import unicodedata
from collections import defaultdict

# Boilerplate de titulación legislativa: aparece en casi todos los títulos y no
# distingue una iniciativa de otra.
_STOP = set("""
de la el los las del y o se en a por para con un una que al su sus este esta ese
esa cual cuales medio dicta dictan dictase otra otras otro otros disposicion
disposiciones norma normas ley leyes proyecto articulo articulos numeral literal
paragrafo adiciona adicionan adicionase modifica modifican modificase reglamenta
reglamentan establece establecen crea crean crease deroga derogan sobre e u como
mediante nacional nacionales republica colombia estado gobierno mismo demas asi
ademas tal sancion sanciona expide expiden adopta adoptan adoptase fin fines
objeto asunto general vez toda todos todas entre segun cada ser tener hacer
""".split())

_SUF = ('idades', 'ciones', 'amiento', 'imiento', 'idad', 'cion', 'aje', 'ismo',
        'ista', 'mente', 'ales', 'ico', 'ica', 'las', 'os', 'as', 'es', 'al',
        'o', 'a')

# Umbrales. Deliberadamente estrictos: un falso positivo aquí le inventa una
# historia a un proyecto que no la tiene, y eso es peor que perder una.
MIN_TOKENS = 2        # títulos con menos no se emparejan con nada
MIN_COMUNES = 2       # hay que compartir al menos dos raíces distintivas
MIN_JACCARD = 0.55


def _stem(w):
    for s in _SUF:
        if w.endswith(s) and len(w) - len(s) >= 4:
            return w[:-len(s)]
    return w


def firma(titulo):
    t = unicodedata.normalize('NFD', titulo or '').encode('ascii', 'ignore').decode()
    t = re.sub(r'\s+', ' ', t.lower())
    sig = {'#' + n for n in re.findall(r'\d{1,4}', t)}
    for w in re.findall(r'[a-z]{4,}', t):
        if w not in _STOP:
            sig.add(_stem(w))
    return sig


def _parecidos(sig, sig_otro):
    inter = sig & sig_otro
    if len(inter) < MIN_COMUNES:
        return 0.0
    union = sig | sig_otro
    return len(inter) / len(union) if union else 0.0


def construir(rows, objetivos):
    """{tok: antecedentes} para cada proyecto de `objetivos`.

    Solo entran radicaciones de años ESTRICTAMENTE anteriores: el corte es el
    mismo que usa `features.antecedentes`, para que las dos vías cuenten lo
    mismo y ninguna mire el futuro.
    """
    # invertido raíz → proyectos, para no comparar todos contra todos
    porRaiz = defaultdict(list)
    firmas = {}
    for r in rows:
        if not r.get('anio'):
            continue
        s = firma(r.get('titulo'))
        if len(s) < MIN_TOKENS:
            continue
        firmas[id(r)] = s
        for tk in s:
            porRaiz[tk].append(r)

    out = {}
    for o in objetivos:
        so = firmas.get(id(o)) or firma(o.get('titulo'))
        if len(so) < MIN_TOKENS:
            continue
        anio = o.get('anio') or 0
        cand = {}
        for tk in so:
            for r in porRaiz.get(tk, ()):
                if r is o or (r.get('anio') or 0) >= anio:
                    continue
                cand[id(r)] = r
        prev = []
        for r in cand.values():
            j = _parecidos(so, firmas.get(id(r)) or firma(r.get('titulo')))
            if j >= MIN_JACCARD:
                prev.append({'anio': r['anio'], 'etapa': r.get('etapa_max') or 0,
                             'res': r.get('resultado'), 'jaccard': round(j, 2),
                             'numero': r.get('numero_senado') or r.get('numero_camara'),
                             'titulo': (r.get('titulo') or '')[:90]})
        if not prev:
            continue
        prev.sort(key=lambda x: x['anio'])
        anios = sorted({p['anio'] for p in prev})
        out[f"{o.get('tabla', 'pdly')}:{o.get('id')}"] = {
            'n_previos': len(anios),          # se cuenta por AÑO, no por ficha:
            'n_fichas': len(prev),            # un proyecto acumulado sale dos veces
            'max_etapa_previa': max(p['etapa'] for p in prev),
            'alguno_fue_ley': any(p['res'] == 'LEY' for p in prev),
            'anios': anios,
            'ejemplos': prev[-3:],
            'via': 'parecido de titulo',
        }
    return out
