#!/usr/bin/env python3
"""
Caudal · UGPP (tanda 1, oct-2026).

⚠️ `/normas/` pinta con AJAX (`mdw_norma_ajax_filter`) y ese endpoint rechaza
todo lo que no venga de un navegador real (403 «-1», con nonce fresco y cookies):
no se usa. La lista completa sale del mapa del sitio de Yoast y cada ficha trae
título y objeto en sus metas:

  normas-sitemap{1,2,3}.xml   529 fichas /normas/<slug>/ con lastmod
  /feed/                      noticias (acumuladas: el feed solo trae 10)

⚠️ La biblioteca de /normas/ NO es solo de la UGPP: reúne lo que le aplica, con
circulares del Archivo General o resoluciones de MinSalud y MinTIC. Entra como norma
de la UGPP solo lo que se identifica como suyo; leyes y decretos ya llegan por otras vías.
⚠️ Las fichas no traen fecha. `fecha` queda vacía para lo que ya existía y se
pone el día en que se vio por primera vez para lo nuevo: inventar el 1 de enero
daría señales falsas en el radar.
⚠️ `/events/` responde «No hay eventos programados» y la API de eventos está
cerrada; no publica conceptos (la categoría existe y está vacía).

Salida: `Bases de datos/caudal-entidades/raw/ugpp/{fichas,proyectos,normas}.json`.
Uso: python3 tools/caudal/entidades/harvest_ugpp.py fetch
"""
import argparse
import datetime
import hashlib
import html
import re
import sys
import time

import comun as C

BASE = 'https://www.ugpp.gov.co'
OUT = C.RAW / 'ugpp'
MAX_DIA = 120                # fichas por corrida; la primera se hace con --todo
_SUYA = re.compile(r'(?i)\bugpp\b|gesti[oó]n pensional|contribuciones parafiscales de la protecci[oó]n social')
_TIPOS = (('proyecto', None), ('resolucion', 'RESOLUCIONES'), ('circular', 'CIRCULARES'), ('acuerdo', 'ACUERDOS'))
_SUB = {'RESOLUCIONES': 'Resolución', 'CIRCULARES': 'Circular', 'ACUERDOS': 'Acuerdo'}


def mapa():
    out = {}
    for i in (1, 2, 3, 4):
        try:
            x = C.curl(f'{BASE}/normas-sitemap{i}.xml', timeout=60, intentos=2)
        except RuntimeError:
            if i == 1:
                raise
            break
        for u, f in re.findall(r'<loc>([^<]+/normas/[^<]+)</loc>\s*<lastmod>([^<]+)', x):
            out[u] = f[:10]
    return out


def ficha(url):
    h = C.curl(url, timeout=45)
    t = re.search(r'<title>([^<]*)', h)
    d = re.search(r'property="og:description" content="([^"]*)', h)
    titulo = html.unescape(t.group(1)).split(' - UGPP')[0].strip() if t else ''
    return {'titulo': titulo, 'objeto': C.limpio(html.unescape(d.group(1))) if d else ''}


def fichas(todo):
    mp = mapa()
    guard = C.leer(OUT / 'fichas.json', {}) or {}
    previas = guard.get('items', {})
    hoy = datetime.date.today().isoformat()
    primera = not previas
    pend = [u for u, f in mp.items() if u not in previas or previas[u].get('lastmod') != f]
    pend.sort(key=lambda u: u in previas)        # primero lo que nunca se ha visto
    if not todo:
        pend = pend[:MAX_DIA]
    for i, u in enumerate(pend):
        try:
            x = ficha(u)
        except RuntimeError as e:
            print(f'  ! ugpp · {u}: {e}', file=sys.stderr)
            continue
        nueva = u not in previas
        previas[u] = {**previas.get(u, {}), **x, 'lastmod': mp[u],
                      'primera_vez': previas.get(u, {}).get('primera_vez') or ('' if primera or todo else hoy)}
        if nueva and i % 40 == 39:
            C.escribir(OUT / 'fichas.json', {'items': previas})
        time.sleep(.15)
    for u, v in previas.items():
        v['vigente'] = u in mp
    C.escribir(OUT / 'fichas.json', {'generado': datetime.datetime.now().isoformat(timespec='seconds'), 'items': previas})
    return previas, len(pend)


def clasificar(previas):
    prevb = (C.leer(OUT / 'proyectos.json', {}) or {}).get('items', {})
    hoy = datetime.date.today().isoformat()
    normas, borr = [], {}
    for u, v in previas.items():
        slug = u.rstrip('/').rsplit('/', 1)[-1]
        tipo = next((t for k, t in _TIPOS if slug.startswith(k)), 'X')
        if tipo == 'X':
            continue
        titulo, obj = v.get('titulo') or '', v.get('objeto') or ''
        if tipo is None:
            k = hashlib.sha1(u.encode()).hexdigest()[:16]
            borr[k] = {'id': k, 'tipo_norma': 'Proyecto de Resolución', 'titulo': obj or titulo, 'dependencia': '',
                       'fecha_inicio': v.get('primera_vez') or '', 'fecha_fin': '', 'comentarios_a': '', 'url': u,
                       'anexos': [], 'creado': v.get('primera_vez') or '', 'visto': hoy,
                       'vigente_en_fuente': bool(v.get('vigente'))}
            continue
        interno = 'interna' in slug
        # solo lo que se dice de la Unidad: la 2710 (IPv6) es de MinTIC y la 611 de
        # 2026 de MinSalud, y las dos están en esta biblioteca sin decir de quién son
        if not _SUYA.search(f'{titulo} {obj} {slug}'):
            continue
        m = re.search(r'(\d{1,6})(?:-\d+)?\s+(?:de|del)\b.*?(20\d{2}|19\d{2})', titulo) or re.search(r'(\d{2,6})-de-(?:[a-z-]*-)?(\d{4})', slug)
        solo = re.search(r'\b(\d{2,6})\b', titulo)
        num, anio = (m.group(1).lstrip('0') or '0', m.group(2)) if m else (solo.group(1) if solo else '', '')
        normas.append({'tipo': tipo, 'subtipo': _SUB[tipo] + (' interna' if interno else ''), 'numero': num, 'anio': anio,
                       'fecha': v.get('primera_vez') or '', 'titulo': titulo, 'descripcion': obj or titulo,
                       'administrativo': interno or C.es_administrativo(obj), 'url': u})
    for k, v in prevb.items():
        if k not in borr:
            borr[k] = {**v, 'vigente_en_fuente': False}
    return normas, borr


def fetch(todo=False):
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    ok = True
    try:
        previas, n = fichas(todo)
        if len(previas) < 400:
            raise RuntimeError(f'solo {len(previas)} fichas')
        normas, borr = clasificar(previas)
        C.escribir(OUT / 'normas.json', {'generado': gen, 'items': normas})
        C.escribir(OUT / 'proyectos.json', {'generado': gen, 'items': borr})
        print(f'  ugpp · {len(previas)} fichas ({n} leídas hoy) · {len(normas)} normas suyas · {len(borr)} proyectos')
    except Exception as e:
        ok = False
        print(f'  ugpp · normas FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)
    try:
        prev = {x['url']: x for x in (C.leer(OUT / 'noticias.json', {}) or {}).get('items', [])}
        for r in C.rss(f'{BASE}/feed/'):
            prev[r['url']] = C.comunicado(r['titulo'], r['fecha'], r['url'], r['resumen'][:400])
        C.escribir(OUT / 'noticias.json', {'generado': gen, 'items': list(prev.values())})
        print(f'  ugpp · {len(prev)} noticias acumuladas')
    except Exception as e:
        ok = False
        print(f'  ugpp · noticias FALLÓ ({e})', file=sys.stderr)
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('fetch')
    p.add_argument('--todo', action='store_true', help='lee todas las fichas pendientes, sin tope diario')
    a = ap.parse_args()
    if a.cmd == 'fetch':
        sys.exit(0 if fetch(a.todo) else 1)


if __name__ == '__main__':
    main()
