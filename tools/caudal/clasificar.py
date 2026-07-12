#!/usr/bin/env python3
"""
Caudal · Fase 1 — clasificación de intención legislativa desde metadata.

Deriva, SOLO del título + trámite (sin gaceta, sin fuente nueva), las señales
que los expertos legislativos piden para leer un proyecto:

  - tipologia          honores | fondos | reforma | presupuestal | ordinaria
  - crea_fondo         bandera: el proyecto crea un fondo (donde se pierde plata)
  - jala_presupuesto   bandera: honor/conmemoración que arrastra recursos a una región
  - clusters de re-radicación (misma iniciativa presentada en varios términos)
  - empuje / vitrina   veces_presentado × debates alcanzados → ¿lo empujaron o era paja?

Diseño conservador (rigor-primero): el clustering agrupa por firma EXACTA de
tokens significativos del título. Prefiere sub-agrupar (perder alguna re-radicación
con título muy cambiado) antes que fusionar iniciativas distintas y colgarle a
alguien una etiqueta "vitrina" que no le toca. Refinamiento fuzzy queda para v2.

Todo esto corre en build-time (build_dataset.py). La Lambda solo lee el resultado.
"""
import re
import unicodedata
from collections import defaultdict

# ---- umbrales tuneables (Ricardo pidió poder ajustar la severidad) ----------
VITRINA_MIN_VECES = 2   # re-radicado en ≥N términos distintos para marcar vitrina
VITRINA_MAX_ETAPA = 1   # ...y sin superar nunca el 1er debate (etapa ≤ 1)


def _norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', s.lower()).strip()


# ---------------------------------------------------------------------------
# 1) TIPOLOGÍA  (clasificador de título, prioridad ordenada)
# ---------------------------------------------------------------------------
_HONOR = re.compile(
    r'\b('
    r'dia (nacional|internacional|departamental|del|de la|de los)|'
    r'semana (nacional|de|del)|'
    r'festival|homenaj|conmemora|aniversario|natalicio|centenari|bicentenari|'
    r'exalta|enaltec|rinde honor|honores a|reconocimiento a|reconozcase|'
    r'declara(se|nse)? patrimonio|patrimonio (cultural|historico|inmaterial)|'
    r'monumento|condecora|medalla|orden de|se rinde|se exalta|'
    r'se vincula (la nacion|el estado)|la nacion se (asocia|vincula|suma)'
    r')\b')

_FONDO = re.compile(r'\b(cre(a|ase|ese)?\s+(el|un)?\s*fondo|fondo (nacional|de|para|especial|cuenta)|fondo-cuenta)\b')

_REFORMA = re.compile(
    r'\b(reforma|se reforma|codig|estatutari|acto legislativo|'
    r'reforma constitucional|modifica la constitucion|constitucion politica)\b')

# recursos / apropiaciones que delatan el "pork" regional
_PLATA = re.compile(
    r'\b(apropiacion|apropriacion|recursos|vigencias futuras|autoriza(se|nse|r)? '
    r'(al gobierno|a la nacion|apropiac)|se asocia|se vincula|presupuest|'
    r'destina(se|nse|r|cion)|financiacion|cofinanciacion|inversion)\b')

# nombre propio de lugar (heurística: honor que aterriza en un municipio/depto)
_LUGAR = re.compile(
    r'\b(municipio de|departamento de|ciudad de|corregimiento de|distrito de|'
    r'en el municipio|del municipio)\b')


def clasificar_titulo(titulo):
    """titulo crudo → {tipologia, crea_fondo, jala_presupuesto_regional}."""
    t = _norm(titulo)
    crea_fondo = bool(_FONDO.search(t))
    es_honor = bool(_HONOR.search(t))
    tiene_plata = bool(_PLATA.search(t))
    tiene_lugar = bool(_LUGAR.search(t))
    # honor que además menciona recursos/lugar = vehículo de presupuesto regional
    jala = es_honor and (tiene_plata or tiene_lugar)

    if es_honor:
        tipologia = 'honores'
    elif crea_fondo:
        tipologia = 'fondos'
    elif _REFORMA.search(t):
        tipologia = 'reforma'
    elif tiene_plata and tiene_lugar:
        tipologia = 'presupuestal'
    else:
        tipologia = 'ordinaria'
    return {'tipologia': tipologia, 'crea_fondo': crea_fondo,
            'jala_presupuesto_regional': jala}


# ---------------------------------------------------------------------------
# 2) FIRMA DE TÍTULO  (para clustering de re-radicación)
# ---------------------------------------------------------------------------
# boilerplate + palabras función que NO distinguen una iniciativa de otra
_STOP = set("""
de la el los las del y o se en a por para con un una que al su sus este esta ese esa
cual cuales medio dicta dictan dictase otra otras otro otros disposicion disposiciones
norma normas ley leyes proyecto articulo articulos numeral literal paragrafo
adiciona adicionan adicionase modifica modifican modificase reglamenta reglamentan
establece establecen crea crean crease deroga derogan sobre e u como mediante cuales
nacional nacionales republica colombia estado gobierno mismo demas asi ademas tal
sancion sanciona expide expiden adopta adoptan adoptase fin fines objeto asunto
sistema general disposicion vez toda todos todas entre segun cada ser tener hacer
""".split())


def titulo_signature(titulo):
    """frozenset de tokens significativos (stem ligero) — clave de cluster.
    <3 tokens significativos → devuelve None (título demasiado genérico para agrupar)."""
    t = _norm(titulo)
    sig = set()
    # números (artículo/ley que se reforma) DISTINGUEN iniciativas: "reforma el
    # art. 180" ≠ "reforma el art. 160". Sin ellos, todas las reformas de un solo
    # artículo colapsan a {reforma, constitucion} y se sobre-agrupan.
    for num in re.findall(r'\d{1,4}', t):
        sig.add('#' + num)
    for w in re.findall(r'[a-z]{4,}', t):
        if w in _STOP:
            continue
        sig.add(_stem(w))
    return frozenset(sig) if len(sig) >= 3 else None


_SUF = ('idades', 'ciones', 'amiento', 'imiento', 'idad', 'cion', 'aje', 'ismo',
        'ista', 'mente', 'ales', 'ico', 'ica', ' los', 'las', 'os', 'as', 'es',
        'al', 'o', 'a')


def _stem(w):
    for s in _SUF:
        if w.endswith(s) and len(w) - len(s) >= 4:
            return w[:-len(s)]
    return w


# ---------------------------------------------------------------------------
# 3) CLUSTERS + EMPUJE / VITRINA
# ---------------------------------------------------------------------------
def empuje_de(veces, max_etapa, es_ley):
    """Etiqueta interpretable + score de vitrina 0-100.

    veces      = nº de términos (legislaturas) distintos en que se intentó
    max_etapa  = etapa máxima alcanzada por CUALQUIER intento del cluster
                 (0 presentado … 2 = 2º debate … 5 ley)
    """
    if es_ley:
        return {'empuje': 'exitoso', 'vitrina_score': 0}
    if max_etapa >= 2:
        # llegó a 2º debate en algún intento → genuinamente empujado
        return {'empuje': 'empujado', 'vitrina_score': 0}
    if veces >= VITRINA_MIN_VECES and max_etapa <= VITRINA_MAX_ETAPA:
        score = 45 + (veces - VITRINA_MIN_VECES) * 20 + (1 - max_etapa) * 15
        return {'empuje': 'vitrina', 'vitrina_score': min(100, score)}
    if max_etapa == 1:
        return {'empuje': 'un_debate', 'vitrina_score': 0}
    return {'empuje': 'sin_traccion', 'vitrina_score': 0}   # 1 intento, 0 debates


def construir_clusters(records):
    """records: lista de dicts con al menos {id, tabla, titulo, legislatura,
    etapa_max, es_ley}. Devuelve dict (tabla,id) → info de cluster/empuje.

    Clusteriza DENTRO de cada tabla (pdly con pdly, pal con pal): una misma
    iniciativa casi nunca cambia de tipo entre términos, y mezclar arriesga
    falsos positivos. Título sin firma (muy genérico) = cluster propio (veces=1).
    """
    buckets = defaultdict(list)          # (tabla, sig) → [records]
    singles = []
    for r in records:
        sig = titulo_signature(r.get('titulo', ''))
        if sig is None:
            singles.append(r)
        else:
            buckets[(r.get('tabla', 'pdly'), sig)].append(r)

    out = {}
    cid = 0
    for (tabla, _sig), grp in buckets.items():
        cid += 1
        legs = {g.get('legislatura') for g in grp if g.get('legislatura')}
        veces = max(len(legs), 1)
        max_etapa = max((g.get('etapa_max') or 0) for g in grp)
        es_ley = any(g.get('es_ley') for g in grp)
        emp = empuje_de(veces, max_etapa, es_ley)
        # línea de tiempo de intentos (para la ficha): año → resultado
        hist = sorted(({'id': g['id'], 'tb': g.get('tabla', 'pdly'),
                        'leg': g.get('legislatura'), 'anio': g.get('anio'),
                        'etapa': g.get('etapa_max'), 'res': g.get('resultado')}
                       for g in grp), key=lambda x: (x['anio'] or 0))
        for g in grp:
            out[(g.get('tabla', 'pdly'), g['id'])] = {
                'cluster_id': cid, 'veces_presentado': veces,
                'n_registros': len(grp), 'max_etapa_cluster': max_etapa,
                **emp, 'historial': hist,
            }
    for r in singles:
        cid += 1
        emp = empuje_de(1, r.get('etapa_max') or 0, r.get('es_ley'))
        out[(r.get('tabla', 'pdly'), r['id'])] = {
            'cluster_id': cid, 'veces_presentado': 1, 'n_registros': 1,
            'max_etapa_cluster': r.get('etapa_max') or 0, **emp, 'historial': [],
        }
    return out


# ---------------------------------------------------------------------------
# 4) AUTORÍA  (verdadero autor vs firmones; actos legislativos = colectiva)
# ---------------------------------------------------------------------------
# un acto legislativo de iniciativa congresal exige ~10 firmas → los firmantes
# SON coautores reales, no firmones. Umbral con holgura (el parser no siempre
# captura las 10).
AUTORIA_COLECTIVA_MIN = 8


def autoria(tabla, autores, autor_tipo):
    """Devuelve {autor_principal, coautores, n_firmantes, autoria_colectiva}.
    - pdly ordinario: 1º = principal, resto = firmones (apoyo).
    - pal (acto legislativo): si hay ≥8 firmas, es autoría colectiva real.
    """
    autores = autores or []
    n = len(autores)
    colectiva = (tabla == 'pal' and n >= AUTORIA_COLECTIVA_MIN)
    if autor_tipo == 'institucional':
        return {'autor_principal': None, 'coautores': [], 'n_firmantes': 0,
                'autoria_colectiva': False}
    return {
        'autor_principal': autores[0] if autores else None,
        'coautores': autores[1:],
        'n_firmantes': n,
        'autoria_colectiva': colectiva,
    }


# reloj de trámite por tipo (Carolina: AL 1 año, ordinaria 2)
RELOJ = {
    'pdly': {'tipo': 'ordinaria', 'ventana_legislaturas': 2, 'debates': 4},
    'pal':  {'tipo': 'acto_legislativo', 'ventana_legislaturas': 1, 'debates': 8},
}


def reloj_de(tabla):
    return RELOJ.get(tabla, RELOJ['pdly'])


if __name__ == '__main__':
    # smoke test
    casos = [
        "POR MEDIO DE LA CUAL SE INSTITUYE EL DIA NACIONAL DEL SOMBRERO VUELTAO",
        "POR LA CUAL LA NACION SE ASOCIA A LA CONMEMORACION DE LOS 200 AÑOS DEL MUNICIPIO DE ZARAGOZA Y SE AUTORIZAN APROPIACIONES",
        "POR LA CUAL SE CREA EL FONDO NACIONAL DE TURISMO PARA VILLAVICENCIO",
        "POR MEDIO DE LA CUAL SE TIPIFICA EL FEMINICIDIO COMO DELITO AUTONOMO",
        "POR EL CUAL SE REFORMA EL ARTICULO 197 DE LA CONSTITUCION POLITICA",
    ]
    for c in casos:
        print(clasificar_titulo(c), '·', c[:50])
