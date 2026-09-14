#!/usr/bin/env python3
"""
Los hechos duros del CUERPO de las notas — lo que el titular no dice.

POR QUÉ EXISTE. Medido sobre el barrido real de Cauce: solo el **3% de los
titulares trae una cifra** (5 de 152). Las cifras que sostienen un brief bueno
—los $634,9 billones del Presupuesto, el 8,2% de déficit, los $58 billones de
deuda de las EPS— viven en el cuerpo del artículo, y las frases que se citan
después («se levanta la sesión») también. Sin este paso, el brief generado salía
con una cifra en todo el documento contra las trece del escrito a mano.

CÓMO. Tres pasos por nota, todos best-effort: resolver la URL real (los enlaces
de Google News son un token opaco), bajar el artículo, y extraer las frases que
traen una cifra o una cita textual. La extracción es DETERMINISTA —expresiones
regulares sobre el texto— y no cuesta un peso: no hay que pagarle a un modelo
para reconocer un número. Lo que sí hace el modelo, después, es decidir cuáles
de esos hechos entran al brief.

  python3 tools/caudal/brief/enriquecer.py barrido.json            # lo enriquece en sitio
  python3 tools/caudal/brief/enriquecer.py barrido.json --notas 40
  python3 tools/caudal/brief/enriquecer.py barrido.json --out otro.json
"""
import argparse
import gzip
import html as _html
import json
import re
import sys
import urllib.parse
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')
TIMEOUT = 22
# Cuántas notas se abren por brief. No son las 152: abrir todas cuesta minutos y
# la mayoría no aporta un hecho duro. Se abren las que el recorte ya priorizó.
NOTAS_DEFAULT = 32
CONCURRENCIA = 6
MAX_HECHOS = 6          # por nota; más que esto es copiar el artículo
MAX_FRASE = 260


def _leer(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={
        'User-Agent': UA, 'Accept-Language': 'es-CO,es;q=0.9',
        'Accept': 'text/html,application/xhtml+xml'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        enc = (r.headers.get('Content-Encoding') or '').lower()
        if enc == 'gzip':
            raw = gzip.decompress(raw)
        elif enc == 'deflate':
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        ctype = r.headers.get('Content-Type') or ''
        m = re.search(r'charset=([\w-]+)', ctype)
        return raw.decode(m.group(1) if m else 'utf-8', 'replace'), r.url


def resolver_google(url):
    """El enlace de Google News → la URL del medio.

    ⚠️ El identificador de `/rss/articles/<ID>` es un token OPACO: se intentó
    decodificarlo como base64 y por dentro no hay ninguna URL. La resolución
    exige pedírsela a Google con la firma y el sello de tiempo que vienen en el
    HTML de la propia página del artículo.
    """
    if 'news.google.com' not in url:
        return url
    h, _ = _leer(url)
    sg = re.search(r'data-n-a-sg="([^"]+)"', h)
    ts = re.search(r'data-n-a-ts="([^"]+)"', h)
    if not (sg and ts):
        return None
    ident = url.split('/articles/')[1].split('?')[0]
    inner = json.dumps(["garturlreq",
                        [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None,
                          1, None, None, None, None, None, 0, 1],
                         "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0],
                        ident, int(ts.group(1)), sg.group(1)])
    payload = json.dumps([[["Fbv4je", inner, None, "generic"]]])
    req = urllib.request.Request(
        'https://news.google.com/_/DotsSplashUi/data/batchexecute',
        data=urllib.parse.urlencode({'f.req': payload}).encode(),
        headers={'User-Agent': UA,
                 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        resp = r.read().decode('utf-8', 'replace')
    m = re.search(r'https?://(?!news\.google)[^"\\]{15,400}', resp)
    return m.group(0) if m else None


# ── del HTML al texto del artículo ─────────────────────────────────────────
_QUITA = re.compile(
    r'<(script|style|noscript|svg|figure|nav|header|footer|aside|form)\b.*?</\1>',
    re.S | re.I)
_TAG = re.compile(r'<[^>]+>')


def texto_articulo(h):
    """El cuerpo de la nota, en texto plano, y si venía delimitado.

    Se prefiere el <article> cuando existe; si no, el documento entero sin los
    bloques de navegación. No es extracción perfecta —para eso haría falta una
    librería— pero alcanza: lo que se busca después son frases con cifras, y
    esas están en los párrafos, no en el menú.
    """
    m = re.search(r'<article\b.*?</article>', h, re.S | re.I)
    delimitado = bool(m)
    cuerpo = m.group(0) if m else h
    cuerpo = _QUITA.sub(' ', cuerpo)
    cuerpo = re.sub(r'<br\s*/?>|</p>|</div>|</h\d>', '\n', cuerpo, flags=re.I)
    txt = _html.unescape(_TAG.sub(' ', cuerpo))
    txt = re.sub(r'[ \t\xa0]+', ' ', txt)
    return re.sub(r'\n\s*\n+', '\n', txt).strip(), delimitado


# ── qué se considera un hecho duro ─────────────────────────────────────────
# Una cifra con unidad, un porcentaje, una fecha con día y mes, o una cantidad
# de cuatro dígitos o más. El «$» solo no basta: «$» suelto aparece en menús.
_CIFRA = re.compile(
    r'(\$\s?\d[\d.,]*\s?(?:billones|mil millones|millones|mil)?'
    r'|\b\d[\d.]*\s?(?:billones|mil millones|millones)\b'
    r'|\b\d{1,3}(?:[.,]\d+)?\s?%'
    r'|\b\d{1,3}(?:\.\d{3})+\b'
    r'|\b\d{1,2} de (?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|'
    r'septiembre|octubre|noviembre|diciembre)\b)', re.I)
# Una cita textual de largo razonable: lo que alguien dijo y se va a repetir.
_CITA = re.compile(r'[«"“]([^»"”]{18,200})[»"”]')
# Ruido típico de página: cookies, suscripciones, pies de foto, etiquetas.
_RUIDO = re.compile(
    r'(cookie|newsletter|suscr[ií]b|reg[ií]strate|iniciar sesi[óo]n|publicidad'
    r'|derechos reservados|pol[ií]tica de privacidad|t[ée]rminos y condiciones'
    r'|siga a |lea tambi[ée]n|le puede interesar|compartir|whatsapp|facebook'
    r'|instagram|foto:|imagen:|cr[ée]dito:)', re.I)
# El sello de publicación trae fecha y por eso pasaba el filtro de «cifra», pero
# no es un hecho: «Publicado el 13 de septiembre de 2026 a las 03:00 a. m.».
_SELLO = re.compile(
    r'^\s*(?:(?:lunes|martes|mi[ée]rcoles|jueves|viernes|s[áa]bado|domingo)\b'
    r'|publicado|actualizado|[A-Za-zÁÉÍÓÚáéíóúñÑ ]{0,18}•)'
    r'|\b\d{1,2}:\d{2}\s?(?:a\.?\s?m|p\.?\s?m)\b', re.I)


# ⚠️ Un medio regional (Infobae, por ejemplo) publica de varios países bajo el
# mismo nombre, así que el filtro de prensa extranjera del barrido —que mira el
# titular— no alcanza: el CUERPO puede ser de otro país. Medido: una nota de
# Infobae aportó el monotributo y un despido en Necochea a un brief colombiano.
# Este filtro actúa sobre el HECHO, que es la unidad que llega al modelo.
_AJENO = re.compile(
    r'\b(monotributo|necochea|casa rosada|milei|kicillof|sheinbaum|pvem|boric'
    r'|bukele|anses|afip|arca|conurbano|provincia de buenos aires'
    r'|pesos argentinos|peso argentino|real brasileño|sol peruano'
    r'|argentin[ao]s?|mexican[ao]s?|chilen[ao]s?|peruan[ao]s?|brasileñ[ao]s?'
    r'|venezolan[ao]s?|uruguay[ao]s?|boliviano?s?|español[ae]s?)\b', re.I)


def _es_titular(f, titulo):
    """¿La frase es el propio titular? Repetirlo no agrega un hecho."""
    if not titulo:
        return False
    a = re.sub(r'\W+', '', f.lower())
    b = re.sub(r'\W+', '', titulo.lower())
    return bool(b) and (b[:45] in a or a[:45] in b)


def hechos_de(txt, tope=MAX_HECHOS, titulo=''):
    """Las frases del artículo que traen un dato duro o una cita.

    Devuelve la FRASE completa, no el número suelto: una cifra sin su contexto
    no se puede citar en un brief («$634,9 billones» no dice de qué).
    """
    frases = re.split(r'(?<=[.!?])\s+|\n', txt)
    vistos, out = set(), []
    for f in frases:
        f = f.strip()
        if not (40 <= len(f) <= MAX_FRASE):
            continue
        if _RUIDO.search(f) or _SELLO.search(f):
            continue
        # el hecho es de otro país y el titular no lo delataba
        if _AJENO.search(f) and 'colombia' not in f.lower():
            continue
        if _es_titular(f, titulo):
            continue
        tiene_cifra = bool(_CIFRA.search(f))
        tiene_cita = bool(_CITA.search(f))
        if not (tiene_cifra or tiene_cita):
            continue
        k = re.sub(r'\W+', '', f.lower())[:60]
        if k in vistos:
            continue
        vistos.add(k)
        out.append({'frase': f, 'cifra': tiene_cifra, 'cita': tiene_cita})
        if len(out) >= tope:
            break
    # las que traen cifra primero: son las más escasas y las que más pesan
    out.sort(key=lambda x: (not x['cifra'], not x['cita']))
    return out


def enriquecer_nota(m):
    """Una nota → sus hechos. Nunca lanza: lo que falla se reporta y sigue."""
    try:
        real = resolver_google(m.get('url') or '')
        if not real:
            return {'_error': 'no se pudo resolver el enlace'}
        h, final = _leer(real)
        txt, delimitado = texto_articulo(h)
        if len(txt) < 400:
            return {'_error': f'cuerpo demasiado corto ({len(txt)} chars)',
                    'url_real': final}
        # ⚠️ Sin <article> el texto puede traer titulares de OTRAS notas de la
        # página. Medido: una nota sin delimitar aportó «el 67% de los
        # contribuyentes de Santa Marta» y unos huesos de 200 millones de años,
        # nada que ver con el tema. Se recorta el tope y se marca, para que el
        # modelo sepa que ese material es menos confiable.
        tope = MAX_HECHOS if delimitado else 3
        hs = hechos_de(txt, tope, m.get('titulo', ''))
        return {'url_real': final, 'hechos': hs, 'largo_cuerpo': len(txt),
                'cuerpo_delimitado': delimitado}
    except Exception as e:                                       # noqa: BLE001
        return {'_error': str(e)[:110]}


def _prioridad(m):
    """Qué notas se abren primero: el mismo criterio del recorte del prompt."""
    t = m.get('titulo') or ''
    v = 0
    if _CIFRA.search(t):
        v += 3
    if _CITA.search(t):
        v += 2
    o = m.get('_origen', '')
    if o.startswith('interlocutor'):
        v += 2
    if o.startswith('empresa'):
        v += 2
    if m.get('_ruido'):
        v -= 4
    return -v


def enriquecer(b, n_notas=NOTAS_DEFAULT):
    medios = b.get('evidencia', {}).get('medios') or []
    orden = sorted(range(len(medios)), key=lambda i: (_prioridad(medios[i]), i))
    elegidas = orden[:n_notas]
    with ThreadPoolExecutor(max_workers=CONCURRENCIA) as pool:
        res = list(pool.map(lambda i: enriquecer_nota(medios[i]), elegidas))
    ok = con_hechos = n_hechos = n_cifras = 0
    for i, r in zip(elegidas, res):
        medios[i].update(r)
        if not r.get('_error'):
            ok += 1
        hs = r.get('hechos') or []
        if hs:
            con_hechos += 1
            n_hechos += len(hs)
            n_cifras += sum(1 for h in hs if h['cifra'])
    b['enriquecimiento'] = {
        'notas_abiertas': len(elegidas), 'resueltas': ok,
        'con_hechos': con_hechos, 'hechos': n_hechos, 'con_cifra': n_cifras,
    }
    return b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('barrido')
    ap.add_argument('--notas', type=int, default=NOTAS_DEFAULT)
    ap.add_argument('--out')
    a = ap.parse_args()
    b = json.load(open(a.barrido, encoding='utf-8'))
    b = enriquecer(b, a.notas)
    out = a.out or a.barrido
    json.dump(b, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    e = b['enriquecimiento']
    print(f"notas abiertas {e['notas_abiertas']} · resueltas {e['resueltas']} · "
          f"con hechos {e['con_hechos']} · {e['hechos']} hechos, "
          f"{e['con_cifra']} con cifra")
    print(f'[{out}]')


if __name__ == '__main__':
    main()
