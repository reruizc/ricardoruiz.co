#!/usr/bin/env python3
"""
Caudal · TEMAS DEL MOMENTO — los chips que sugiere la búsqueda de caudal.html.

POR QUÉ EXISTE (sep-2026). La gente llega a Caudal a buscar «lo que se está
discutiendo» y la caja vacía no ayuda. La primera idea fue Google Trends; medido
el 6-sep, su RSS para Colombia traía sinuano, Claudia Bahamón, Racing y Cruz
Azul contra Santos Laguna: de 10 tendencias, 2 eran de política, y además no
hay API oficial. Los temas salen entonces de lo que Caudal YA recoge, en tres
capas, mezcladas a propósito (decisión de Ricardo): quien busca acá viene a
cruzar la conversación pública con lo que se mueve en el Estado.

  · PRENSA POLÍTICA   acción `medios` de la Lambda (Google News, 3 días):
                      landing + consultas de gobierno/Congreso/regulación.
  · RADICADOS         en-vivo.json (los últimos proyectos de Senado y Cámara).
  · CONSULTAS SUCOP   borradores de norma abiertos a comentarios hoy.

El modelo (DeepSeek) NO inventa temas: recibe los ítems numerados y debe citar
de cuáles sale cada tema. Se valida que (1) cite ítems que existan, (2) alguna
palabra del tema aparezca en ellos, y (3) el tema devuelva algo en el propio
Caudal (acción `tema`: título o articulado) o tenga ≥3 titulares en el corpus.
Un chip que devuelve cero es peor que ninguno. Si quedan menos de MIN_TEMAS, el
script sale con rc=1 y NO escribe: en S3 se queda el JSON anterior (última
copia buena, mismo principio que el resto del pipeline).

Uso:
  python3 tools/caudal/temas/build_temas.py                # construye el JSON local
  python3 tools/caudal/temas/build_temas.py --upload-only  # sube el JSON local a S3
  python3 tools/caudal/temas/build_temas.py --dry-run      # todo menos escribir
Necesita DEEPSEEK_API_KEY en el entorno o, si no está, la lee de la config de la
Lambda caudal-analiza con el AWS CLI (mismo patrón que explica_en_vivo.py).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT_DIR = REPO / 'Bases de datos' / 'leyes-senado' / 'temas'
OUT = OUT_DIR / 'temas-del-momento.json'
S3_DEST = 's3://elecciones-2026/ricardoruiz.co/congreso-2026/output/legislativo/temas-del-momento.json'

API = 'https://l3kmprdjkl.execute-api.us-east-1.amazonaws.com'
EN_VIVO = ('https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/'
           'congreso-2026/output/legislativo/en-vivo.json')
DEEPSEEK_URL = 'https://api.deepseek.com/chat/completions'
DEEPSEEK_MODEL = 'deepseek-v4-flash'
UA = 'caudal-temas/1.0 (+ricardoruiz.co)'

CONSULTAS_PRENSA = [
    'Congreso proyecto de ley', 'reforma Gobierno', 'ministerio decreto',
    'superintendencia', 'Corte Constitucional', 'presupuesto general nación',
    'gremios empresarios Gobierno', 'regulación',
]
DIAS_PRENSA = 3
N_TEMAS = 8
MULETILLAS = {'ya', 'hoy', 'ahora', 'de', 'del', 'la', 'el', 'los', 'las', 'y', 'en', 'que'}
MIN_TEMAS = 4

SYSTEM = """Eres el editor de Caudal, una plataforma colombiana de inteligencia legislativa y regulatoria. Te doy una lista numerada de titulares de prensa política, proyectos de ley radicados esta semana y borradores de norma en consulta pública. Tu tarea: proponer los %d TEMAS que alguien buscaría hoy en Caudal.

Reglas duras:
- Cada tema es una CONSULTA DE BÚSQUEDA de 2 a 4 palabras, en minúsculas, sin tildes, como la escribiría alguien en un buscador (ej. "reforma pensional", "presupuesto general 2027", "tarifas de energia"). Sustantivos de política pública, no titulares ni frases.
- Solo política pública, Gobierno, Congreso, regulación o economía regulada en Colombia. Nada de deportes, farándula ni internacional sin efecto en Colombia.
- PROHIBIDO inventar: cada tema sale de ítems de la lista y debes citar sus números en "evidencia" (mínimo 2 ítems). Si un tema no tiene 2 ítems, no va.
- Prefiere temas que aparezcan en más de una capa (prensa + radicados, o prensa + consulta).
- Sin repetir temas ni variantes del mismo.
Devuelve SOLO JSON: {"temas":[{"tema":"...","por_que":"una frase de máximo 18 palabras, en tuteo neutro, que diga por qué importa hoy","evidencia":[n, n, ...]}]}""" % N_TEMAS


def _n(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9 ]+', ' ', s)


def _post(payload, timeout=60):
    req = urllib.request.Request(
        API, data=json.dumps(payload).encode('utf-8'), method='POST',
        headers={'Content-Type': 'application/json', 'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8') or '{}')


def _get(url, timeout=60):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8') or '{}')


# ---------------------------------------------------------------- corpus
def prensa():
    items, vistos = [], set()

    def _absorb(d):
        for t in (d.get('titulares') or d.get('resultados') or []):
            tit = (t.get('titulo') or '').strip()
            k = _n(tit)[:80]
            if not tit or k in vistos:
                continue
            vistos.add(k)
            items.append({'capa': 'prensa', 'texto': tit, 'medio': t.get('medio') or '',
                          'fecha': (t.get('fecha') or '')[:10]})
    jobs = [{'action': 'medios'}] + [{'action': 'medios', 'query': q, 'dias': DIAS_PRENSA}
                                     for q in CONSULTAS_PRENSA]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for d in pool.map(lambda p: _safe(_post, p), jobs):
            if d:
                _absorb(d)
    return items


def radicados():
    try:
        d = _get(EN_VIVO)
    except Exception as e:                                  # noqa: BLE001
        print(f'  ! en-vivo.json: {e}', file=sys.stderr)
        return []
    out = []
    for cam in ('senado', 'camara'):
        for r in d.get(cam) or []:
            ex = r.get('explica') or {}
            tit = (ex.get('titular') or r.get('titulo') or '').strip()
            if tit:
                out.append({'capa': 'radicados', 'texto': tit, 'numero': r.get('numero'),
                            'camara': cam, 'fecha': (r.get('fecha') or '')[:10]})
    return out


def consultas():
    d = _safe(_post, {'action': 'sucop', 'estado': 'abiertas'})
    out = []
    for r in (d or {}).get('resultados') or []:
        tit = (r.get('titulo') or '').strip()
        if tit:
            out.append({'capa': 'consultas', 'texto': tit, 'entidad': r.get('entidad') or '',
                        'cierra': r.get('fecha_fin') or r.get('cierra') or ''})
    return out


def _safe(fn, *a):
    try:
        return fn(*a)
    except Exception as e:                                  # noqa: BLE001
        print(f'  ! {fn.__name__}{a[:1]}: {str(e)[:120]}', file=sys.stderr)
        return None


# ---------------------------------------------------------------- LLM
def _api_key():
    k = os.environ.get('DEEPSEEK_API_KEY')
    if k:
        return k.strip()
    try:
        r = subprocess.run(['aws', 'lambda', 'get-function-configuration',
                            '--function-name', 'caudal-analiza',
                            '--query', 'Environment.Variables.DEEPSEEK_API_KEY',
                            '--output', 'text'], capture_output=True, text=True, timeout=30)
        k = (r.stdout or '').strip()
        return k if k and k != 'None' else ''
    except Exception:                                       # noqa: BLE001
        return ''


def _deepseek(key, user, max_tokens):
    body = json.dumps({
        'model': DEEPSEEK_MODEL,
        'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': user}],
        'temperature': 0.3, 'max_tokens': max_tokens,
        'response_format': {'type': 'json_object'},
    }).encode('utf-8')
    req = urllib.request.Request(DEEPSEEK_URL, data=body, headers={
        'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read())
    ch = d['choices'][0]
    return (ch['message'].get('content') or '').strip(), ch.get('finish_reason')


def proponer(key, corpus):
    lineas = [f'{i+1}. [{c["capa"]}] {c["texto"][:160]}' for i, c in enumerate(corpus)]
    user = 'ÍTEMS DE HOY:\n' + '\n'.join(lineas)
    # V4 gasta presupuesto en razonamiento: con techo corto devuelve vacío
    # (gotcha ya documentado en todo el proyecto) → 6000 y reintento a 12000.
    for mt in (6000, 12000):
        raw, fin = _deepseek(key, user, mt)
        if raw.startswith('```'):
            raw = raw.split('```')[1].lstrip('json').strip()
        if fin == 'length' and not raw.endswith('}'):
            continue
        try:
            return json.loads(raw).get('temas') or []
        except ValueError:
            continue
    raise ValueError('el modelo se truncó o devolvió JSON inválido dos veces')


# ---------------------------------------------------------------- validación
def _tokens_tema(tema):
    return [t for t in _n(tema).split() if len(t) >= 5 or t.isdigit()]


def validar(props, corpus):
    out, vistos = [], set()
    for p in props:
        tema = re.sub(r'\s+', ' ', _n(p.get('tema') or '')).strip()
        # muletillas en los bordes («plan de energia ya», «hoy reforma…»): no
        # son parte del tema y ensucian el chip
        pal = tema.split()
        while pal and pal[0] in MULETILLAS: pal.pop(0)
        while pal and pal[-1] in MULETILLAS: pal.pop()
        tema = ' '.join(pal)
        if not (2 <= len(tema.split()) <= 5) or tema in vistos:
            continue
        ev = [int(i) for i in (p.get('evidencia') or []) if str(i).isdigit()]
        ev = [i for i in ev if 1 <= i <= len(corpus)]
        toks = _tokens_tema(tema)
        # (2) alguna palabra del tema debe estar en la evidencia citada
        ev_ok = [i for i in ev if any(t in _n(corpus[i-1]['texto']) for t in toks)]
        if len(ev_ok) < 2:
            continue
        # cuántos ítems del corpus lo mencionan, por capa (no solo los citados)
        capas = {'prensa': 0, 'radicados': 0, 'consultas': 0}
        for c in corpus:
            if any(t in _n(c['texto']) for t in toks):
                capas[c['capa']] += 1
        vistos.add(tema)
        out.append({'tema': tema, 'por_que': (p.get('por_que') or '').strip()[:160],
                    'capas': capas,
                    'evidencia': [corpus[i-1]['texto'][:120] for i in ev_ok[:3]]})
    return out


def verificar_en_caudal(temas):
    """(3) un chip tiene que devolver algo en Caudal: se pregunta a la acción
    `tema` (título + articulado, sin lectura → barata) por cada uno."""
    def _uno(t):
        d = _safe(_post, {'action': 'tema', 'query': t['tema'], 'lectura': False})
        r = (d or {}).get('resumen') or {}
        t['n_congreso'] = int(r.get('n_titulo') or 0) + int(r.get('n_texto') or 0)
        return t
    with ThreadPoolExecutor(max_workers=3) as pool:
        temas = list(pool.map(_uno, temas))
    ok = [t for t in temas if t['n_congreso'] >= 1 or t['capas']['prensa'] >= 3]
    return ok, [t for t in temas if t not in ok]


# ---------------------------------------------------------------- main
def build(dry_run=False):
    t0 = time.time()
    print('· corpus')
    corpus = prensa() + radicados() + consultas()
    n = {k: sum(1 for c in corpus if c['capa'] == k) for k in ('prensa', 'radicados', 'consultas')}
    print(f'    prensa {n["prensa"]} · radicados {n["radicados"]} · consultas {n["consultas"]}')
    if n['prensa'] < 10:
        print('! muy poca prensa: no se construye (¿la Lambda responde?)', file=sys.stderr)
        return 1
    key = _api_key()
    if not key:
        print('! sin DEEPSEEK_API_KEY: no se construye', file=sys.stderr)
        return 1
    print('· modelo')
    props = proponer(key, corpus)
    print(f'    propuso {len(props)}')
    temas = validar(props, corpus)
    print(f'    con evidencia válida {len(temas)}')
    temas, fuera = verificar_en_caudal(temas)
    for t in fuera:
        print(f'    ✗ {t["tema"]!r}: cero en Caudal y prensa {t["capas"]["prensa"]}')
    temas = temas[:N_TEMAS]
    for t in temas:
        print(f'    ✓ {t["tema"]:<32} congreso {t["n_congreso"]:>4} · prensa {t["capas"]["prensa"]:>3}'
              f' · radicados {t["capas"]["radicados"]} · consultas {t["capas"]["consultas"]}')
    if len(temas) < MIN_TEMAS:
        print(f'! solo {len(temas)} temas válidos (mínimo {MIN_TEMAS}): no se escribe, '
              f'en S3 queda el anterior', file=sys.stderr)
        return 1
    payload = {
        'generado': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'hoy': time.strftime('%Y-%m-%d'),
        'metodo': ('Prensa política (Google News, 3 días) + proyectos radicados esta semana + '
                   'consultas SUCOP abiertas → temas propuestos por el modelo con evidencia '
                   'citada y verificados contra el propio Caudal.'),
        'fuentes': n,
        'temas': temas,
    }
    if dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=1)[:1500])
        return 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'→ {OUT.relative_to(REPO)} · {len(temas)} temas · {time.time()-t0:.0f}s')
    return 0


def upload():
    if not OUT.exists():
        print('! no hay JSON local que subir', file=sys.stderr)
        return 1
    r = subprocess.run(['aws', 's3', 'cp', str(OUT), S3_DEST, '--content-type', 'application/json',
                        '--cache-control', 'public, max-age=300', '--only-show-errors'])
    print('subido' if r.returncode == 0 else '! falló la subida')
    return r.returncode


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--upload-only', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    sys.exit(upload() if a.upload_only else build(a.dry_run))
