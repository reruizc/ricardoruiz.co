#!/usr/bin/env python3
"""
Caudal · Ministerio de Vivienda, Ciudad y Territorio (tanda 2, oct-2026).

  normativa  /normativa?f[0]=tipo_normativa:X&f[1]=fecha_norma:AAAA   (Drupal, 20 por página)
  conceptos  /ministerio/conceptos-juridicos?page=N                   (tabla, ~680)
  prensa     /comunicaciones?page=N

⚠️⚠️ El 96 % de las resoluciones son de Fonvivienda: asignan, renuncian o revocan
subsidios a personas con nombre. Son actos particulares y no entran, salvo las que
fijan reglas generales (_GENERAL).
⚠️ La «Fecha de Norma» trae errores de captura (27/12/2026 publicada en octubre):
si cae en el futuro, se usa la fecha de publicación.
⚠️ La agenda regulatoria vive en SUCOP: no se lee acá.

Salida: `Bases de datos/caudal-entidades/raw/minvivienda/{normas,noticias}.json`.
Uso: python3 tools/caudal/entidades/harvest_minvivienda.py fetch [--todo]
"""
import argparse
import datetime
import html
import re
import sys
import urllib.parse

import comun as C

BASE = 'https://minvivienda.gov.co'
OUT = C.RAW / 'minvivienda'
TIPOS = {'Resolución': 'RESOLUCIONES', 'Circular': 'CIRCULARES'}   # los decretos ya entran por Presidencia
# de Fonvivienda solo entra lo que fija reglas para muchos, nunca lo que resuelve casos
_GENERAL = re.compile(r'(?i)\b(?:convocatoria|apertura|cupos?|lineamientos?|reglament\w+|distribuci[oó]n de)\b')
_PARTICULAR = re.compile(r'(?i)renuncia|revoca|asigna|legaliza|ejecutoriedad|ejecutoria|recurso de reposici|'
                         r'pr[oó]rroga|vigencia del subsidio|caducidad|restitu|aclara|condici[oó]n resolutoria|'
                         r'desagregaci[oó]n|da[nñ]o antijur[ií]dico|subsidios? familiar')


def _fuera(x):
    return x.get('subtema') == 'Fonvivienda' and (_PARTICULAR.search(x.get('descripcion') or '')
                                                  or not _GENERAL.search(x.get('descripcion') or ''))


def _pagina(tipo, anio, n):
    q = urllib.parse.urlencode({'f[0]': f'tipo_normativa:{tipo}', 'f[1]': f'fecha_norma:{anio}', 'page': n})
    return C.curl(f'{BASE}/normativa?{q}', timeout=90)


def _filas(h):
    return re.split(r'<div class="[^"]*\bviews-row\b[^"]*">', h)[1:]


def _ultima(h):
    ns = [int(x) for x in re.findall(r'[?&;]page=(\d+)', h)]
    return max(ns) if ns else 0


def _fila(b, tipo):
    m = re.search(r'listing-title"><span><a href="([^"]+)"[^>]*>(.*?)</a>', b, re.S)
    if not m:
        return None
    titulo = C.limpio(html.unescape(m.group(2)))
    nu = re.search(r'(\d+)\s*-\s*(20\d{2})', titulo)
    fn = re.search(r'field-legal-regulation-date.*?datetime="(\d{4}-\d{2}-\d{2})', b, re.S)
    fp = re.search(r'views-field-created.*?datetime="(\d{4}-\d{2}-\d{2})', b, re.S)
    hoy = datetime.date.today().isoformat()
    fecha = fn.group(1) if fn and fn.group(1) <= hoy else (fp.group(1) if fp else '')
    tema = re.search(r'views-field-field-topic"><span class="field-content">([^<]*)', b)
    desc = re.search(r'views-field-field-summary"><span class="field-content">(.*?)</span>', b, re.S)
    desc = C.limpio(html.unescape(desc.group(1))) if desc else ''
    tema = html.unescape(tema.group(1)).strip() if tema else ''
    return {'tipo': TIPOS[tipo], 'subtipo': tipo, 'numero': nu.group(1).lstrip('0') if nu else '',
            'anio': nu.group(2) if nu else fecha[:4], 'fecha': fecha, 'titulo': titulo,
            'descripcion': desc or titulo, 'subtema': tema, 'administrativo': not desc or C.es_administrativo(desc),
            'url': BASE + m.group(1)}


def normas(prev, todo):
    out = {x['url']: x for x in prev}
    anio = datetime.date.today().year
    for tipo in TIPOS:
        for a in ([anio - 1, anio] if todo else [anio]):
            h, n, ult = _pagina(tipo, a, 0), 0, 0
            ult = _ultima(h) if todo else min(_ultima(h), 3)
            while True:
                for b in _filas(h):
                    f = _fila(b, tipo)
                    if f and not _fuera(f):
                        out[f['url']] = f
                n += 1
                if n > ult:
                    break
                h = _pagina(tipo, a, n)
    return list(out.values())


def conceptos(prev, todo):
    out = {x['url']: x for x in prev}
    n, ult = 0, 0
    hoy = datetime.date.today().isoformat() if prev else ''   # la tabla no trae fecha: lo nuevo, el día en que aparece
    while True:
        h = C.curl(f'{BASE}/ministerio/conceptos-juridicos?page={n}', timeout=90)
        ult = _ultima(h) if todo else min(_ultima(h), 2)
        anio_tabla = ''
        for parte in re.split(r'(<caption>[^<]*</caption>)', h):
            cap = re.search(r'<caption>\s*Conceptos\s+(20\d{2})', parte)
            if cap:
                anio_tabla = cap.group(1)
                continue
            for tr in re.findall(r'<tr>(.*?)</tr>', parte, re.S):
                m = re.search(r'<a href="(/sites/default/files/conceptos_juridicos/[^"]+)"[^>]*>(.*?)</a></p>(.*?)</td>', tr, re.S)
                if not m:
                    continue
                c = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)
                rad = C.limpio(c[0]) if c else ''
                tema = C.limpio(html.unescape(c[2])) if len(c) > 2 else ''
                t = C.limpio(html.unescape(m.group(2)))
                r = C.limpio(html.unescape(m.group(3)))
                ra = re.match(r'(20\d{2})', rad)
                u = BASE + m.group(1)
                if u not in out:
                    out[u] = {'tipo': 'CONCEPTOS', 'subtipo': 'Concepto', 'numero': rad, 'anio': (ra.group(1) if ra else anio_tabla),
                              'fecha': hoy, 'titulo': f'Concepto {rad}: {t}' if rad else f'Concepto: {t}',
                              'descripcion': f'{t}. {r}' if r else t, 'subtema': tema, 'administrativo': False, 'url': u}
        n += 1
        if n > ult:
            break
    return list(out.values())


def noticias(prev):
    out = {x['url']: x for x in prev}
    for n in range(3):
        h = re.sub(r'base64,[^"]+', '', C.curl(f'{BASE}/comunicaciones?page={n}', timeout=90))
        for b in _filas(h):
            m = re.search(r'<a href="(/sala-de-prensa/[^"]+)"[^>]*>', b)
            f = re.search(r'\|\s*(\d{1,2}\s+[A-Za-zéáó]+\s+de\s+20\d{2})', C.limpio(b))
            if not m:
                continue
            ts = [C.limpio(html.unescape(x)) for x in re.findall(r'<a href="' + re.escape(m.group(1)) + r'"[^>]*>(.*?)</a>', b, re.S)]
            t = next((x for x in ts if len(x) > 20), '')
            if t and f:
                u = BASE + m.group(1)
                out[u] = C.comunicado(t, C.fecha_larga(f.group(1)), u)
    return list(out.values())


def fetch(todo):
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    ok = True
    prev = (C.leer(OUT / 'normas.json', {}) or {}).get('items', [])
    previas = [x for x in prev if x['tipo'] != 'CONCEPTOS']
    conc = [x for x in prev if x['tipo'] == 'CONCEPTOS']
    try:
        previas = [x for x in normas(previas, todo) if not _fuera(x) and x['tipo'] != 'DECRETOS']
    except Exception as e:
        ok = False
        print(f'  minvivienda · normativa FALLÓ ({e}) — queda la anterior', file=sys.stderr)
    try:
        conc = conceptos(conc, todo or not conc)
    except Exception as e:
        ok = False
        print(f'  minvivienda · conceptos FALLÓ ({e}) — quedan los anteriores', file=sys.stderr)
    if previas or conc:
        C.escribir(OUT / 'normas.json', {'generado': gen, 'items': previas + conc})
    print(f'  minvivienda · {len(previas)} normas · {len(conc)} conceptos')
    try:
        xs = noticias((C.leer(OUT / 'noticias.json', {}) or {}).get('items', []))
        C.escribir(OUT / 'noticias.json', {'generado': gen, 'items': xs})
        print(f'  minvivienda · {len(xs)} noticias')
    except Exception as e:
        ok = False
        print(f'  minvivienda · noticias FALLÓ ({e})', file=sys.stderr)
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('fetch')
    p.add_argument('--todo', action='store_true', help='recorre todas las páginas desde el año pasado (primera carga)')
    a = ap.parse_args()
    sys.exit(0 if fetch(a.todo) else 1)


if __name__ == '__main__':
    main()
