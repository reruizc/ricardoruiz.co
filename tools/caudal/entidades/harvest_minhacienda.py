#!/usr/bin/env python3
"""
Caudal · Ministerio de Hacienda: los títulos de sus borradores (tanda 4, nov-2026).

⚠️⚠️ Todo el sitio está detrás de un antibots (Radware Bot Manager). Abrir un borrador
con curl responde su página «Block» por `validate.perfdrive.com`, medido el 1-nov-2026.
NO se evade: el cosechador solo lee `sitemap.xml`, que el `robots.txt` del sitio deja abierto.
De un borrador se sabe que existe, su dirección y su última modificación. NO se tiene su
texto, su plazo de comentarios ni su título real.

  sitemap.xml                 índice de 1.077 sub-sitemaps, uno por página de Liferay
  sitemap.xml?p_l_id=3441&... todos los borradores: el barrido completo del 1-nov-2026
                              (2.551 URL) no halló ninguno en otro sub-sitemap

Por eso el título sale de la dirección y queda marcado: `titulo_reconstruido`,
`sin_texto` y un `objeto` que se lo dice al lector. Un slug puede ser una sigla sin
contexto («pd-cuipo») o venir cortado en 255 caracteres (se marca con «…»).

⚠️ `lastmod` no es la fecha del borrador. El de 2024 es la migración del sitio: solo
entra lo modificado desde `DESDE`.
⚠️ La misma entidad duplica entradas con «-copiar-» o «-1»: se juntan.
⚠️ Lo que ya está en SUCOP no entra: allá sí tiene texto y plazo.
⚠️ `visto` marca lo nuevo. En la primera corrida (la línea base) es el `lastmod`, para
que el histórico no salga como novedad.

Salida: `Bases de datos/caudal-entidades/raw/minhacienda/proyectos.json`.
Uso: python3 tools/caudal/entidades/harvest_minhacienda.py fetch
     python3 tools/caudal/entidades/harvest_minhacienda.py fetch --todo     (repasa los 1.077, ~30 min)
"""
import argparse
import datetime
import hashlib
import html
import json
import re
import subprocess
import sys
import time
import urllib.parse

import comun as C

WWW = 'https://www.minhacienda.gov.co'
OUT = C.RAW / 'minhacienda'
DESDE = '2025-01-01'
PAUSA = 1.5
MINIMO = .7                  # una corrida por debajo del 70 % de la anterior no se publica
SEMILLA = ('3441',)          # el p_l_id de la página que lista los borradores
AVISO = ('Título reconstruido desde la dirección web del borrador. Caudal no tiene el texto ni el plazo de '
         'comentarios: el sitio de MinHacienda está detrás de un antibots.')
_BORRADOR = re.compile(r'^(?:(p\.?d)(?:\.-?|-)|(p\.?r)(?:\.-?|-)|(p\.\s*circular)\.?-?)(?=[^/])', re.I)
_FUERA = re.compile(r'(?i)manual[- ](?:espec[ií]fico[- ])?de[- ]funciones|^agenda')    # actos internos
_CORTE = 250                 # Liferay corta la dirección en 255 caracteres


class Cerrado(RuntimeError):
    """Respondió HTML donde va XML: el antibots llegó al sitemap. Se para, no se insiste."""


def _pag(url):
    time.sleep(PAUSA)
    x = C.curl(url, timeout=120, intentos=2)
    if x.strip() and '<urlset' not in x and '<sitemapindex' not in x:
        raise Cerrado(f'no respondió XML: {url[:90]}')
    return x


def _filas(xml):
    return re.findall(r'<url><loc>(.*?)</loc>(?:<lastmod>(.*?)</lastmod>)?', xml)


def es_borrador(slug):
    return _BORRADOR.match(slug)


def reconstruir(slug):
    """pd.-por-el-cual-se-modifica%C3%A1… → ('Proyecto de decreto', 'Por el cual…', cortado)."""
    m = _BORRADOR.match(slug)
    clase = 'Proyecto de decreto' if m.group(1) else 'Proyecto de resolución' if m.group(2) else 'Proyecto de circular'
    cortado = len(slug) >= _CORTE
    t = urllib.parse.unquote(html.unescape(slug[m.end():]))
    t = re.sub(r'(?i)\.pdf$', '', t).strip('-. ')
    t = re.sub(r'-(?:copiar-?|\d)$', '', t).strip('-. ')
    t = C.limpio(t.replace('-', ' '))
    t = re.sub(r'\bpor ia cual\b', 'por la cual', t)     # el slug trae una errata recurrente
    t = t[:1].upper() + t[1:]
    if re.match(r'Por (?:medio de )?la cual\b', t):      # los decretos son «por el cual», sin importar el prefijo
        clase = 'Proyecto de resolución'
    return clase, (t.rstrip(' ,;') + '…') if cortado else t, cortado


def _llave(slug):
    """El mismo borrador con «-copiar-», «-1» o sin el punto del prefijo."""
    s = urllib.parse.unquote(html.unescape(slug))
    s = re.sub(r'(?i)^p\.?d\.?-?', 'pd-', s)
    s = re.sub(r'(?i)^p\.?r\.?-', 'pr-', s)
    s = re.sub(r'-(?:copiar-?|\d)$', '', s.strip('-'))
    return hashlib.sha1(C.fold(s).encode()).hexdigest()[:16]


def _palabras(s):
    return {x for x in re.findall(r'[a-z0-9]{4,}', C.fold(s))
            if x not in ('proyecto', 'decreto', 'resolucion', 'cual', 'para', 'medio', 'sobre', 'articulo', 'articulos',
                         'modifica', 'adiciona', 'relacionado', 'capitulo', 'titulo', 'parte', 'libro')}


def _en_sucop():
    """Títulos de MinHacienda en SUCOP. Sin S3 se sigue sin filtrar: un repetido
    estorba menos que un borrador perdido."""
    try:
        r = subprocess.run(['aws', 's3', 'cp', 's3://caudal-legislativo/metadata/sucop.jsonl', '-'],
                           capture_output=True, check=True, timeout=120)
        filas = [json.loads(x) for x in r.stdout.decode().splitlines()]
    except Exception as e:
        print(f'  minhacienda · no se leyó SUCOP ({e}): van todos', file=sys.stderr)
        return []
    return [p for p in (_palabras(x.get('titulo')) for x in filas
                        if 'Hacienda' in (x.get('entidad') or '') and x.get('tipo') == 'norma') if p]


def _repetido(titulo, sucop):
    a = _palabras(titulo)
    return len(a) >= 4 and any(len(a & p) / len(a | p) >= .6 for p in sucop)


def sub_sitemaps(todo, mapa):
    """Qué sub-sitemaps pedir: la semilla y los que ya trajeron borradores. `--todo`
    los repasa todos, a ritmo prudente: es para cuando la guarda salte."""
    locs = {}
    for u in re.findall(r'<loc>(.*?)</loc>', _pag(f'{WWW}/sitemap.xml')):
        u = html.unescape(u)
        m = re.search(r'p_l_id=(\d+)', u)
        if m:
            locs[m.group(1)] = u
    if len(locs) < 100:
        raise RuntimeError(f'el índice solo trajo {len(locs)} sub-sitemaps')
    if todo:
        return locs, locs
    return locs, {k: u for k, u in locs.items() if k in SEMILLA or mapa.get(k)}


def fetch_borradores(prev, mapa, todo):
    hoy = datetime.date.today().isoformat()
    _, elegidos = sub_sitemaps(todo, mapa)
    vivos, slugs = {}, {}
    for pid, u in elegidos.items():
        n = 0
        try:
            xml = _pag(u)
        except Cerrado:
            raise
        except RuntimeError:             # hay páginas viejas con 404: solo importan las semillas
            if pid in SEMILLA or mapa.get(pid):
                raise
            mapa[pid] = 0
            continue
        for loc, lastmod in _filas(xml):
            if '/w/' not in loc:
                continue
            slug = loc.split('/w/', 1)[1]
            if not es_borrador(slug):
                continue
            n += 1
            if not _FUERA.search(urllib.parse.unquote(slug)):
                slugs[slug] = lastmod[:10]
        mapa[pid] = n
    for slug, lastmod in slugs.items():
        if lastmod < DESDE:
            continue
        k = _llave(slug)
        if k in vivos and vivos[k]['creado'] >= lastmod:
            continue
        clase, titulo, cortado = reconstruir(slug)
        vivos[k] = {'id': k, 'tipo_norma': clase, 'titulo': f'{clase}: {titulo}'[:400], 'objeto': AVISO, 'dependencia': '',
                    'fecha_inicio': '', 'fecha_fin': '', 'comentarios_a': '', 'url': f'{WWW}/w/{slug}', 'anexos': [],
                    'creado': lastmod, 'vigente_en_fuente': True, 'titulo_reconstruido': True, 'sin_texto': True,
                    'titulo_cortado': cortado}
    n = len(vivos)
    sucop = _en_sucop()
    fuera = {k for k, v in vivos.items() if _repetido(v['titulo'], sucop)}
    vivos = {k: v for k, v in vivos.items() if k not in fuera}
    base = not prev
    out = {k: v for k, v in prev.items() if k not in fuera}
    for k, v in out.items():
        if k not in vivos:
            v['vigente_en_fuente'] = False
    nuevos = [k for k in vivos if k not in out]
    for k, v in vivos.items():
        v['visto'] = out[k].get('visto', v['creado']) if k in out else (v['creado'] if base else hoy)
    out.update(vivos)
    return out, n, len(fuera), [] if base else [vivos[k] for k in nuevos]


def fetch(todo=False):
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    try:
        prev = C.leer(OUT / 'proyectos.json', {}) or {}
        mapa = C.leer(OUT / 'sitemaps.json', {}) or {}
        items, n, en_sucop, nuevos = fetch_borradores(prev.get('items', {}), mapa, todo)
        # la guarda compara lo que vino de la fuente, no lo acumulado
        previos = prev.get('n_fuente') or 0
        if not n or (previos and n < previos * MINIMO):
            raise RuntimeError(f'{n} borradores contra {previos} de la corrida anterior')
        C.escribir(OUT / 'sitemaps.json', mapa)
        C.escribir(OUT / 'proyectos.json', {'generado': gen, 'n_fuente': n, 'items': items})
        print(f'  minhacienda · {n} borradores desde {DESDE} en el sitemap · {en_sucop} ya en SUCOP · '
              f'{len(items)} acumulados · {len(nuevos)} nuevos')
        for v in nuevos:
            print(f'    nuevo · {v["titulo"][:120]}')
        return True
    except Exception as e:
        print(f'  minhacienda · proyectos FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)
        return False


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('fetch')
    p.add_argument('--todo', action='store_true')
    a = ap.parse_args()
    sys.exit(0 if fetch(a.todo) else 1)


if __name__ == '__main__':
    main()
