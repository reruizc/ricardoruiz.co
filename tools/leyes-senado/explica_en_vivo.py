#!/usr/bin/env python3
"""
Resumen ciudadano de los proyectos de ley del feed "En vivo" (legislativo.html).

Toma los items que arma `leyes_en_vivo.py` y les agrega un campo `explica` con
una lectura en lenguaje llano: qué haría la ley en la práctica, a quién le
aplica y qué cambia. El frontend lo muestra en el modal que se abre al hacer
clic en un proyecto.

POR QUÉ SE GENERA AQUÍ Y NO EN EL NAVEGADOR
  El feed son 3 proyectos por cámara y se reconstruye 2×/día: generar el
  resumen en el builder cuesta unas décimas de centavo al día, queda cacheado
  por número y el visitante no paga latencia ni nosotros exponemos la API key
  en una página pública. Un proyecto ya explicado NO se vuelve a pedir.

DE DÓNDE SALE EL TEXTO QUE SE RESUME (en orden de calidad, `base` lo declara)
  1. `texto`  — el radicado completo que ya bajó `harvest_diario.py` a
                diario/{leg}/textos-txt/PL-NNN-YY.txt (Senado). Es lo mejor:
                trae objeto y articulado.
  2. `pdf`    — el PDF re-alojado en S3 por el propio feed (ambas cámaras),
                leído con pypdf.
  3. `objeto` — la columna "Objeto" del XLSX de Cámara (texto legal, 300-650
                caracteres). Suficiente para explicar bien.
  4. `titulo` — último recurso: en Senado el objeto no existe como campo y el
                PDF tarda días en publicarse. El prompt OBLIGA a quedarse en
                lo que el título sostiene y el frontend lo rotula como tal.

  Regla dura del prompt: prohibido inventar artículos, cifras, plazos o
  sanciones que no estén en el texto recibido. Es preferible un resumen corto
  a uno inventado — la página es pública y cita fuente.

Uso:
  python3 tools/leyes-senado/explica_en_vivo.py            # explica el en-vivo.json del staging
  python3 tools/leyes-senado/explica_en_vivo.py --force    # ignora la caché
  # normalmente no se llama solo: leyes_en_vivo.py lo invoca al construir el feed.

Necesita DEEPSEEK_API_KEY en el entorno. Si no está (o si la API falla), los
items se quedan SIN campo `explica` y el frontend degrada al objeto/título:
nunca rompe el feed.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

DEEPSEEK_MODEL = 'deepseek-v4-flash'
DEEPSEEK_URL = 'https://api.deepseek.com/chat/completions'

REPO = Path(__file__).resolve().parents[2]
STAGE = REPO / 'Bases de datos' / 'leyes-senado' / 'en-vivo'
CACHE = STAGE / 'explica-cache.json'
TEXTOS = REPO / 'Bases de datos' / 'leyes-senado' / 'diario' / '2026-2027' / 'textos-txt'

# ventana de texto que se manda al modelo. El objeto y los primeros artículos
# viven al principio del radicado; más allá es exposición de motivos y anexos,
# que encarecen sin mejorar el resumen.
MAX_CHARS = 16000
PROMPT_VERSION = 'v1'          # súbelo al cambiar SYSTEM → invalida la caché

# calidad de la fuente del resumen. Se usa para no degradar lo ya publicado
# (ver la guarda en explicar(): la Lambda no tiene los .txt del rastreo ni
# pypdf, así que su mejor fuente suele ser peor que la del cron del Mac).
RANK = {'texto': 3, 'pdf': 3, 'objeto': 2, 'titulo': 1}

SYSTEM = """Eres redactor de servicio público en un medio de datos colombiano. Traduces proyectos de ley al lenguaje de una persona sin formación jurídica: qué cambiaría en su vida diaria si la ley se aprueba.

REGLAS
1. Prohibido inventar. Solo puedes afirmar lo que esté en el texto que te dan. Nada de cifras, plazos, sanciones, entidades ni artículos que no aparezcan ahí.
2. Si el texto que recibes es solo el título del proyecto, quédate en lo que el título sostiene: di qué se propone crear o modificar, sin detallar mecanismos que no conoces. Es correcto ser breve.
3. Nada de lenguaje jurídico. No escribas "la presente ley tiene por objeto", "de conformidad con", "el legislador". Escribe como le explicarías a un vecino.
4. Concreto sobre abstracto: qué pasa, para quién, desde cuándo. Evita "busca fortalecer", "promueve", "garantiza" sin decir cómo.
5. Neutral: describe lo que propone, no si es buena o mala idea, ni quién gana o pierde políticamente.
6. Español de Colombia, tuteo neutro, sin regionalismos.

Devuelve SOLO un objeto JSON con esta forma:
{
  "titular": "una frase de máximo 18 palabras: qué haría esta ley, en llano",
  "cambia": ["2 a 4 viñetas de máximo 25 palabras, cada una un cambio concreto y verificable en el texto"],
  "afecta": "a quién le aplica, máximo 20 palabras",
  "ojo": "opcional, máximo 25 palabras: una salvedad útil (que apenas se radicó, que modifica una ley existente, etc). Cadena vacía si no aplica."
}"""


# ─────────────────────────────────────────────────────────────── LLM
def _api_key():
    """La key vive en la config de la Lambda caudal-analiza (mismo patrón que
    harvest_supersalud_registro.py). Se lee del entorno y, si no está, se
    intenta con el AWS CLI — así el cron del Mac no necesita un .env aparte."""
    k = os.environ.get('DEEPSEEK_API_KEY')
    if k:
        return k.strip()
    try:
        r = subprocess.run(
            ['aws', 'lambda', 'get-function-configuration',
             '--function-name', 'caudal-analiza',
             '--query', 'Environment.Variables.DEEPSEEK_API_KEY', '--output', 'text'],
            capture_output=True, text=True, timeout=30)
        k = (r.stdout or '').strip()
        return k if k and k != 'None' else ''
    except Exception:                                   # noqa: BLE001
        return ''


def _deepseek(key, user, max_tokens=3000, timeout=90):
    body = json.dumps({
        'model': DEEPSEEK_MODEL,
        'messages': [{'role': 'system', 'content': SYSTEM},
                     {'role': 'user', 'content': user}],
        'temperature': 0.3, 'max_tokens': max_tokens,
        'response_format': {'type': 'json_object'},
    }).encode('utf-8')
    req = urllib.request.Request(
        DEEPSEEK_URL, data=body,
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    ch = d['choices'][0]
    return ch['message']['content'], (d.get('usage') or {}), ch.get('finish_reason')


def _pedir(key, user):
    """Una explicación, con reintento de presupuesto si el modelo se trunca.
    V4 gasta tokens en reasoning y con presupuesto corto devuelve el JSON a
    medias (finish_reason='length') — mismo gotcha ya documentado en Caudal."""
    for max_tok in (3000, 6000):
        raw, usage, fin = _deepseek(key, user, max_tokens=max_tok)
        raw = (raw or '').strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1].lstrip('json').strip()
        if fin == 'length' and not raw.endswith('}'):
            continue
        return json.loads(raw), usage
    raise ValueError('el modelo se truncó dos veces')


# ───────────────────────────────────────────────────── fuentes de texto
def _num_slug(numero):
    """'135/26' o '077/2026C' → ('135','26') / ('077','26') para casar con los
    .txt del rastreo diario, que se nombran PL-NNN-YY.txt."""
    m = re.match(r'\s*(\d+)\s*[/-]\s*(\d{2,4})', str(numero or ''))
    if not m:
        return None, None
    return m.group(1).zfill(3), m.group(2)[-2:]


def _texto_local(numero):
    """Radicado completo que ya bajó harvest_diario.py (solo Senado)."""
    n, yy = _num_slug(numero)
    if not n:
        return ''
    p = TEXTOS / f'PL-{n}-{yy}.txt'
    if not p.exists():
        return ''
    try:
        return p.read_text(encoding='utf-8', errors='replace')
    except Exception:                                   # noqa: BLE001
        return ''


def _texto_pdf(url):
    """Texto del PDF re-alojado en S3 (los radicados traen capa de texto)."""
    if not url:
        return ''
    try:
        import io
        from pypdf import PdfReader
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=90) as r:
            blob = r.read()
        if blob[:4] != b'%PDF':
            return ''
        reader = PdfReader(io.BytesIO(blob))
        out = []
        for pg in reader.pages:
            out.append(pg.extract_text() or '')
            if sum(len(x) for x in out) > MAX_CHARS * 2:
                break                                   # ya hay de sobra
        return '\n'.join(out)
    except Exception:                                   # noqa: BLE001
        return ''


def _limpiar(txt):
    """El OCR del escáner del Senado mete ruido (guiones sueltos, números de
    línea, espacios dobles). Se normaliza sin intentar 'arreglar' palabras:
    el modelo tolera bien el ruido, lo que no tolera es un muro sin saltos."""
    txt = re.sub(r'[ \t]+', ' ', str(txt or ''))
    txt = re.sub(r'\n{3,}', '\n\n', txt)
    return txt.strip()


def fuente_texto(it, base_pdf='', camara='senado'):
    """Mejor texto disponible para este proyecto → (texto, base).
    `base` viaja al JSON para que el frontend sea honesto sobre de dónde salió.

    ⚠️ El caché de textos-txt es SOLO de Senado (lo llena harvest_diario.py) y
    el número de radicado NO es identificador único: se reinicia por cámara,
    así que existe un 077 de Senado y un 077/2026C de Cámara que son proyectos
    distintos. Buscar el .txt para un item de Cámara devuelve el articulado
    equivocado — medido: el 077 de Cámara (registro de SIM) salía resumido
    como el 077 de Senado (cadena perpetua). Por eso el filtro por cámara."""
    t = _limpiar(_texto_local(it.get('numero'))) if camara == 'senado' else ''
    if len(t) > 1200:
        return t[:MAX_CHARS], 'texto'
    pdf = it.get('pdf') or ''
    if pdf:
        url = pdf if re.match(r'^https?:', pdf) else (base_pdf or '') + pdf
        t = _limpiar(_texto_pdf(url))
        if len(t) > 1200:
            return t[:MAX_CHARS], 'pdf'
    obj = _limpiar(it.get('resumen'))
    if len(obj) > 120:
        return obj, 'objeto'
    return _limpiar(it.get('titulo')), 'titulo'


# ────────────────────────────────────────────────────────────── caché
def _load_cache():
    try:
        return json.loads(CACHE.read_text(encoding='utf-8'))
    except Exception:                                   # noqa: BLE001
        return {}


def _save_cache(c):
    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding='utf-8')
    except Exception as e:                              # noqa: BLE001
        print(f'  ! no pude guardar la caché de explicaciones: {e}', file=sys.stderr)


def _clave(camara, numero):
    return f'{camara}:{numero}'


def _huella(texto, base):
    return f'{PROMPT_VERSION}:{base}:' + hashlib.sha1(texto.encode('utf-8')).hexdigest()[:16]


# ──────────────────────────────────────────────────────────── público
def _valida(d, base):
    """Normaliza la respuesta del modelo. Si no trae lo mínimo, se descarta:
    mejor sin resumen que con uno vacío o malformado."""
    if not isinstance(d, dict):
        return None
    tit = str(d.get('titular') or '').strip()
    cam = [str(x).strip() for x in (d.get('cambia') or []) if str(x).strip()]
    if not tit or not cam:
        return None
    out = {'titular': tit, 'cambia': cam[:4], 'base': base}
    af = str(d.get('afecta') or '').strip()
    oj = str(d.get('ojo') or '').strip()
    if af:
        out['afecta'] = af
    if oj:
        out['ojo'] = oj
    return out


def explicar(items, camara, base_pdf='', force=False, cache=None, key=None,
             previos=None, verbose=True):
    """Agrega `explica` a cada item (in place). Devuelve (n_nuevos, n_cache).

    `previos` es {numero: explica} del en-vivo.json que ya está en S3. Sirve de
    segunda caché para la ruta Lambda, donde el archivo local no persiste: si
    un proyecto sigue en el feed y su fuente no mejoró, se reusa lo publicado
    en vez de volver a pagarle al modelo."""
    if not items:
        return 0, 0
    cache = _load_cache() if cache is None else cache
    previos = previos or {}
    if key is None:
        key = _api_key()
    nuevos = cacheados = 0
    for it in items:
        ck = _clave(camara, it.get('numero'))
        texto, base = fuente_texto(it, base_pdf, camara)
        if not texto:
            continue
        hu = _huella(texto, base)
        prev = cache.get(ck)
        # se reusa si la fuente NO cambió; si llegó el radicado y antes solo
        # había título, la huella cambia y se re-explica con el texto bueno.
        if prev and prev.get('huella') == hu and prev.get('explica') and not force:
            it['explica'] = prev['explica']
            cacheados += 1
            continue
        # Sin caché local: se reusa lo YA PUBLICADO si venía de una fuente
        # igual de buena o mejor. Esto no es solo ahorro — es lo que evita una
        # regresión real: este builder corre en dos sitios (el cron del Mac,
        # que tiene el radicado completo y pypdf, y la Lambda, que no tiene
        # ninguno de los dos). Sin esta guarda, la corrida de la Lambda
        # pisaría un resumen hecho con el texto del proyecto por uno hecho
        # solo con el título.
        vieja = previos.get(str(it.get('numero')))
        if vieja and not force and RANK.get(vieja.get('base'), 0) >= RANK.get(base, 0):
            it['explica'] = vieja
            cache[ck] = {'huella': hu, 'explica': vieja}
            cacheados += 1
            continue
        if not key:
            continue                                    # sin key: se deja sin explica
        user = (f'PROYECTO DE LEY {it.get("numero", "")} '
                f'({"Senado" if camara == "senado" else "Cámara de Representantes"})\n'
                f'TÍTULO: {it.get("titulo", "")}\n\n'
                + ('TEXTO DEL PROYECTO RADICADO:\n' if base in ('texto', 'pdf')
                   else 'OBJETO DECLARADO:\n' if base == 'objeto'
                   else 'NO HAY MÁS TEXTO DISPONIBLE QUE EL TÍTULO. '
                        'Explica solo lo que el título sostiene.\n')
                + (texto if base != 'titulo' else ''))
        try:
            d, _ = _pedir(key, user)
            ex = _valida(d, base)
        except Exception as e:                          # noqa: BLE001
            print(f'  ! no pude explicar {ck}: {e}', file=sys.stderr)
            ex = None
        if ex:
            it['explica'] = ex
            cache[ck] = {'huella': hu, 'explica': ex}
            nuevos += 1
            if verbose:
                print(f'  ✦ {ck} ({base}): {ex["titular"][:70]}')
    _save_cache(cache)
    return nuevos, cacheados


# ────────────────────────────────────────────────────────────── CLI
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true', help='ignora la caché')
    ap.add_argument('--json', default=str(STAGE / 'en-vivo.json'))
    args = ap.parse_args()
    p = Path(args.json)
    if not p.exists():
        sys.exit(f'no existe {p} — corre antes leyes_en_vivo.py')
    feed = json.loads(p.read_text(encoding='utf-8'))
    key = _api_key()
    if not key:
        print('! sin DEEPSEEK_API_KEY: nada que hacer', file=sys.stderr)
    cache = _load_cache()
    tot_n = tot_c = 0
    for cam in ('senado', 'camara'):
        n, c = explicar(feed.get(cam) or [], cam, feed.get('base_pdf', ''),
                        force=args.force, cache=cache, key=key)
        tot_n += n
        tot_c += c
    p.write_text(json.dumps(feed, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'· {tot_n} explicados · {tot_c} desde caché → {p}')


if __name__ == '__main__':
    main()
