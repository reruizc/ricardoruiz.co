#!/usr/bin/env python3
"""
Caudal · normalización de autores legislativos.

El campo `autor` del Senado es un desastre: variantes por tilde y mojibake
("Iván"/"Ivan"/"Ivã¡N"), ruido ("Otros", "Y Otros"), radicaciones del
Ejecutivo con listas enteras de gabinete, y encoding roto. Este módulo resuelve
cada autor a una forma canónica para poder contar y, luego, unir a partido.

Estrategia (conservadora, sin fuzzy arriesgado):
  - limpia mojibake + puntuación + espacios
  - clave canónica = sin tildes + MAYÚSCULAS + solo alfanum → colapsa variantes
    exactas-módulo-acentos ("Iván Cepeda"==="Ivan Cepeda"==="Ivã¡N Cepeda")
  - descarta ruido ("otros", "varios", …)
  - clasifica radicaciones institucionales (Gobierno/ministros/órganos) y NO
    las parte en personas falsas — quedan como una entidad
  - registro global: clave → display más limpio y frecuente + variantes + n

API:
  procesar_campo(raw)      → {'tipo':'persona'|'institucional', 'personas':[(key,disp)], 'entidad':str|None}
  construir_registro(recs) → dict clave→{display, tipo, n_proyectos, variantes}
  resolver_display(reg)    → dict clave→display (para inyectar en build_dataset)
"""
import re
import unicodedata
from collections import Counter, defaultdict

# --- prefijos de título parlamentario a quitar del nombre ------------------
_PREF = re.compile(
    r'\b(H\.?\s?[SR]\.?|HONORABLE|SENADOR(?:A)?|REPRESENTANTE|DR(?:A)?\.?|DOCTOR(?:A)?)\.?\s*',
    re.I)

# --- mojibake frecuente (doble-encoding utf8/latin1) -----------------------
_MOJIBAKE = {
    'ã¡': 'a', 'ã©': 'e', 'ã­': 'i', 'ã³': 'o', 'ãº': 'u', 'ã±': 'n',
    'ã\x81': 'a', 'ã‰': 'e', 'ã\x8d': 'i', 'ã“': 'o', 'ãš': 'u', 'ã‘': 'n',
    'â´': '', 'â\x80\x93': '-', '´': '', '`': '',
}

# --- ruido: no son autores -------------------------------------------------
_RUIDO = re.compile(r'^(y\s+)?(otros?|varios|otras?|etc|[-–\s]*)$', re.I)

# --- radicación institucional / ejecutiva ----------------------------------
_INST_PATRONES = [
    (r'gobierno|ministr|min\.?\s+de\b', 'Gobierno Nacional'),
    (r'defensor(?:[íi]a)?\s+del?\s+pueblo|defensor del pueblo', 'Defensoría del Pueblo'),
    (r'fiscal(?:[íi]a)?\s+general|fiscal general', 'Fiscalía General'),
    (r'procurad', 'Procuraduría General'),
    (r'contralor', 'Contraloría General'),
    (r'registrador', 'Registraduría Nacional'),
    (r'consejo de estado', 'Consejo de Estado'),
    (r'corte (suprema|constitucional)', 'Corte'),
    (r'consejo nacional electoral|\bcne\b', 'Consejo Nacional Electoral'),
    (r'bancada', 'Bancada (colectiva)'),
]


def _sin_tildes(s):
    return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode()


def _fix_mojibake(s):
    low = s
    for bad, good in _MOJIBAKE.items():
        low = low.replace(bad, good).replace(bad.upper(), good.upper())
    # descarta chars de reemplazo y de control
    return ''.join(c for c in low if c == ' ' or unicodedata.category(c)[0] != 'C'
                   and c != '�')


def limpiar(nombre):
    """Nombre de persona listo para mostrar (sin título, sin mojibake)."""
    s = _fix_mojibake(nombre or '')
    s = _PREF.sub('', s)
    s = re.sub(r'[.;:]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip(' -–,')
    return s.title() if s else ''


def canon_key(nombre):
    """Clave que colapsa variantes por tilde/caso/puntuación."""
    s = _sin_tildes(_fix_mojibake(nombre or '')).upper()
    s = _PREF.sub('', s)
    s = re.sub(r'[^A-Z0-9 ]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def es_ruido(nombre):
    return bool(_RUIDO.match((nombre or '').strip())) or len(canon_key(nombre)) < 4


def clasificar_institucional(raw):
    """Si el campo es una radicación institucional/ejecutiva, devuelve el
    nombre canónico de la entidad; si no, None."""
    n = _sin_tildes(raw or '').lower()
    # solo cuenta si el patrón aparece al inicio del campo (primeros 45 chars)
    cabeza = n[:45]
    for pat, entidad in _INST_PATRONES:
        if re.search(pat, cabeza):
            return entidad
    return None


def _split_personas(raw):
    """Parte el campo en menciones individuales (coma o ' Y ' antes de mayús)."""
    txt = _fix_mojibake(raw or '').strip().rstrip('.')
    partes = re.split(r'\s*,\s*|\s+Y\s+(?=[A-ZÁÉÍÓÚÑ])', txt)
    return [p for p in partes if p.strip()]


def procesar_campo(raw):
    """Un campo `autor` → tipo + lista de personas canónicas (key, display)."""
    entidad = clasificar_institucional(raw)
    if entidad:
        return {'tipo': 'institucional', 'entidad': entidad, 'personas': []}
    personas = []
    seen = set()
    for m in _split_personas(raw):
        if es_ruido(m):
            continue
        k = canon_key(m)
        if k and k not in seen:
            seen.add(k)
            personas.append((k, limpiar(m)))
    return {'tipo': 'persona', 'entidad': None, 'personas': personas}


def construir_registro(records):
    """recs (dicts con 'autor') → registro clave→{display, tipo, n, variantes}.
    El display se elige como la variante más frecuente y limpia (con tildes,
    sin mojibake)."""
    variantes = defaultdict(Counter)   # key → Counter(display)
    n_proj = Counter()                 # key → nº proyectos
    entidades = Counter()
    for r in records:
        p = procesar_campo(r.get('autor', ''))
        if p['tipo'] == 'institucional':
            entidades[p['entidad']] += 1
            continue
        for k, disp in p['personas']:
            variantes[k][disp] += 1
            n_proj[k] += 1
    reg = {}
    for k, cnt in variantes.items():
        # display: entre las variantes razonablemente frecuentes (≥40% de la
        # más común), elige la MÁS acentuada — nombres en español van con tilde
        items = cnt.most_common()
        umbral = items[0][1] * 0.4
        cands = [d for d, c in items if c >= umbral]
        display = max(cands, key=lambda d: sum(1 for c in d if ord(c) > 127))
        reg[k] = {'display': display, 'tipo': 'persona',
                  'n_proyectos': n_proj[k], 'n_variantes': len(cnt),
                  'variantes': dict(cnt)}
    for ent, n in entidades.items():
        reg[canon_key(ent)] = {'display': ent, 'tipo': 'institucional',
                               'n_proyectos': n, 'n_variantes': 1, 'variantes': {}}
    return reg


def resolver_display(registro):
    return {k: v['display'] for k, v in registro.items()}
