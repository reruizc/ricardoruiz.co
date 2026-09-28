"""La foto de portada del correo del brief: la de la nota de prensa que mejor
calza con el tema principal.

La prensa del barrido llega con enlaces de Google News (`news.google.com/rss/
articles/…`), que no son la nota: hay que resolverlos. La página del enlace trae
una firma (`data-n-a-sg`) y una marca de tiempo (`data-n-a-ts`), y con ellas el
endpoint `batchexecute` de Google devuelve la URL original. De la nota se toma
su `og:image`, que es la foto que el propio medio eligió para compartirla.

⚠️ La foto es del medio —o de la agencia que se la vende (Colprensa, AFP, EFE)—,
no nuestra. Va enlazada desde su servidor (no se copia) y con el crédito del
medio debajo, pero eso no equivale a una licencia. `BRIEF_IMAGEN=0` la apaga.

⚠️ Nunca lanza: el brief sale igual sin foto. El decodificador depende de un
formato interno de Google que puede cambiar sin aviso, y cuando cambie la
señal es un correo sin imagen, no un workflow caído.
"""
import html
import json
import os
import re
import unicodedata
import urllib.parse
import urllib.request

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/130.0 Safari/537.36')
# Palabras que están en casi todo titular y no dicen de qué trata.
_VACIAS = set('''para sobre entre desde hasta porque como cuando donde durante
tras según contra segun este esta estos estas pero más mas ante bajo todo toda
todos todas nuevo nueva nuevos gobierno colombia colombiano presidente'''.split())


def _abrir(url, data=None, hdr=None, timeout=15):
    req = urllib.request.Request(url, data=data, headers={'User-Agent': UA, **(hdr or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', 'replace')


def _palabras(txt):
    t = unicodedata.normalize('NFD', str(txt or '').lower())
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    return {w for w in re.findall(r'[a-z0-9]+', t) if len(w) >= 4 and w not in _VACIAS}


def decodificar(gn):
    """Enlace de Google News → URL de la nota. Si no es de Google News, igual."""
    if 'news.google.com' not in gn:
        return gn
    gid = urllib.parse.urlparse(gn).path.rstrip('/').split('/')[-1]
    t = _abrir(gn)
    sg = re.search(r'data-n-a-sg="([^"]+)"', t).group(1)
    ts = re.search(r'data-n-a-ts="([^"]+)"', t).group(1)
    interno = json.dumps(['garturlreq', [['X', 'X', ['X', 'X'], None, None, 1, 1, 'US:en',
                                          None, 1, None, None, None, None, None, 0, 1],
                                         'X', 'X', 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0],
                          gid, int(ts), sg])
    freq = json.dumps([[['Fbv4je', interno, None, 'generic']]])
    r = _abrir('https://news.google.com/_/DotsSplashUi/data/batchexecute',
               urllib.parse.urlencode({'f.req': freq}).encode(),
               {'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'})
    return json.loads(json.loads(r.split('\n\n', 1)[1])[0][2])[1]


def og_image(url):
    t = _abrir(url)
    for pat in (r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image'):
        m = re.search(pat, t, re.I)
        if m:
            src = html.unescape(m.group(1)).strip()
            if src.startswith('//'):
                src = 'https:' + src
            # Solo https: Gmail y Outlook bloquean o marcan las imágenes http.
            return src if src.startswith('https://') else None
    return None


def elegir(brief, medios, intentos=4):
    """La foto de la nota que más se parece al tema principal del brief.

    Exige al menos dos palabras en común con el tema: una foto de otra noticia
    arriba de todo es peor que ninguna foto. Devuelve None si no hay candidata.
    """
    if os.environ.get('BRIEF_IMAGEN', '1') == '0':
        return None
    try:
        temas = brief.get('temas') or []
        if not temas or not medios:
            return None
        clave = _palabras(f"{temas[0].get('titulo', '')} {temas[0].get('rotulo', '')}")
        cand = []
        for x in medios:
            n = len(clave & _palabras(x.get('titulo')))
            if n >= 2 and x.get('url'):
                cand.append((n, x.get('fecha') or '', x))
        cand.sort(key=lambda c: (c[0], c[1]), reverse=True)
        for _, _, x in cand[:intentos]:
            try:
                nota = decodificar(x['url'])
                src = og_image(nota)
            except Exception:                                    # noqa: BLE001
                continue
            if src:
                # Google News pega « | Medio» o « - Medio» al final del titular.
                tit = re.sub(r'\s+[|\-–]\s+[^|\-–]{2,40}$', '', x.get('titulo') or '')
                return {'src': src, 'medio': x.get('medio') or '',
                        'titulo': tit, 'enlace': nota}
    except Exception:                                            # noqa: BLE001
        pass
    return None
