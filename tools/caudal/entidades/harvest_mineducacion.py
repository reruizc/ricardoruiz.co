#!/usr/bin/env python3
"""
Caudal · Ministerio de Educación Nacional (tanda 2, oct-2026).

  normas      /portal/Normatividad/Ultimas-publicaciones;anos-normatividad/AAAA/
  comunicados /portal/salaprensa/Comunicados/   (solo los 5 últimos: se acumulan)

⚠️ Sin el sufijo `;anos-normatividad/AAAA/` la página responde un meta refresh.
⚠️ La fecha de la lista es la de actualización: la de expedición sale del título
cuando viene ahí («Circular 052 del 9 de octubre del 2026»).
⚠️ La agenda regulatoria vive en SUCOP: no se lee acá.

Salida: `Bases de datos/caudal-entidades/raw/mineducacion/{normas,noticias}.json`.
Uso: python3 tools/caudal/entidades/harvest_mineducacion.py fetch
"""
import argparse
import datetime
import html
import re
import sys

import comun as C

BASE = 'https://www.mineducacion.gov.co'
OUT = C.RAW / 'mineducacion'
TIPOS = {'circular': ('CIRCULARES', 'Circular'), 'resoluci': ('RESOLUCIONES', 'Resolución'), 'directiva': ('DIRECTIVAS', 'Directiva'),
         'acuerdo': ('RESOLUCIONES', 'Acuerdo')}   # decretos y leyes ya entran por Presidencia y el Congreso
_NUM = re.compile(r'(?i)^(?:\W*)(circular|resoluci[oó]n|directiva(?: emergencia)?|decreto|ley|acuerdo)\s*(?:externa\s*)?'
                  r'(?:n[°ºo.]*|nro\.?|no\.?|numero|número)?\s*[.:\s]*0*(\d{1,6})')
_ISO = re.compile(r'iso8601-(\d{4})(\d{2})(\d{2})')


def normas(anio):
    h = C.curl(f'{BASE}/portal/Normatividad/Ultimas-publicaciones;anos-normatividad/{anio}/', timeout=90)
    out = []
    for b in re.split(r'<div class="recuadro my-5">', h)[1:]:
        t = re.search(r'<h3 class="h4 titulo[^"]*">(.*?)</h3>', b, re.S)
        if not t:
            continue
        titulo = C.limpio(html.unescape(t.group(1)))
        m = _NUM.search(titulo)
        clave = C.fold(m.group(1)) if m else C.fold(titulo)
        tipo = next((v for k, v in TIPOS.items() if clave.startswith(k)), None)
        if not tipo:
            continue
        iso = _ISO.search(b)
        act = '-'.join(iso.groups()) if iso else ''
        f = C.fecha_larga(titulo)
        ab = re.search(r'<p class="abstract[^"]*">(.*?)</p>', b, re.S)
        desc = C.limpio(html.unescape(ab.group(1))) if ab else ''
        pdf = re.search(r'href="(articles-[^"]+)"', b)
        url = f'{BASE}/1780/{pdf.group(1)}' if pdf else f'{BASE}/portal/Normatividad/Ultimas-publicaciones/'
        out.append({'tipo': tipo[0], 'subtipo': tipo[1], 'numero': m.group(2) if m else '', 'anio': (f or act or str(anio))[:4],
                    'fecha': f or act, 'titulo': titulo, 'descripcion': desc or titulo,
                    'administrativo': not desc or C.es_administrativo(desc), 'url': url})
    return out


def noticias(prev):
    out = {x['url']: x for x in prev}
    h = C.curl(f'{BASE}/portal/salaprensa/Comunicados/', timeout=90)
    for u, t, cola in re.findall(r'<a href="(/portal/salaprensa/Comunicados/\d+:[^"]+)"[^>]*>([^<]{15,})</a></h\d>(.{0,900})', h, re.S):
        iso = _ISO.search(cola)
        ab = re.search(r'<p class="abstract[^"]*">(.*?)</p>', cola, re.S)
        url = BASE + u
        out[url] = C.comunicado(C.limpio(html.unescape(t)), '-'.join(iso.groups()) if iso else '', url,
                                C.limpio(html.unescape(ab.group(1)))[:400] if ab else '')
    return list(out.values())


def fetch(desde):
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    ok = True
    anio = datetime.date.today().year
    out = {x['titulo']: x for x in (C.leer(OUT / 'normas.json', {}) or {}).get('items', []) if x['tipo'] != 'DECRETOS'}
    try:
        n = 0
        for a in range(desde or anio, anio + 1):
            for x in normas(a):
                out[x['titulo']] = x
                n += 1
        if not n:
            raise RuntimeError('ninguna norma en la lista')
        C.escribir(OUT / 'normas.json', {'generado': gen, 'items': list(out.values())})
        print(f'  mineducacion · {len(out)} normas')
    except Exception as e:
        ok = False
        print(f'  mineducacion · normas FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)
    try:
        xs = noticias((C.leer(OUT / 'noticias.json', {}) or {}).get('items', []))
        C.escribir(OUT / 'noticias.json', {'generado': gen, 'items': xs})
        print(f'  mineducacion · {len(xs)} comunicados')
    except Exception as e:
        ok = False
        print(f'  mineducacion · comunicados FALLÓ ({e})', file=sys.stderr)
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('fetch')
    p.add_argument('--desde', type=int, help='año desde el que se relee (por defecto, el actual)')
    a = ap.parse_args()
    sys.exit(0 if fetch(a.desde) else 1)


if __name__ == '__main__':
    main()
