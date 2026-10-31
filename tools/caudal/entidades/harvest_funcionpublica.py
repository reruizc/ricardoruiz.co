#!/usr/bin/env python3
"""
Caudal · Departamento Administrativo de la Función Pública (tanda 1, oct-2026).

  proyectos   www1.funcionpublica.gov.co/proyectos-normativos-de-la-funcion-publica
              tarjetas con título, documentos, publicación y plazo de observaciones
  normas      dafpIndexerBGN/norma/index?filtroTipoDocumento=…&filtroAnio=…
              el Gestor Normativo: 10 por página, con resumen. La fecha de
              expedición no está en la lista: sale de la ficha norma.php?i=N, que
              se lee una sola vez (fechas.json).
  agenda      /agenda-regulatoria (se guarda el archivo más nuevo)

⚠️ El Gestor reúne normas de TODO el Estado: de Resolución y Circular solo entra
lo que dice «Función Pública» en el título. Sus conceptos son todos propios.
⚠️ Sus páginas pesan 170 KB y algunas 12 MB: se pide por tipo y año, no todo junto.
⚠️ Las capacitaciones viven en un widget de la portada: no se leen todavía.

Salida: `Bases de datos/caudal-entidades/raw/funcionpublica/{proyectos,normas}.json`.
Uso: python3 tools/caudal/entidades/harvest_funcionpublica.py fetch [--desde 2025]
"""
import argparse
import datetime
import hashlib
import html
import re
import sys
import time
import urllib.parse

import comun as C

WWW1 = 'https://www1.funcionpublica.gov.co'
IDX = 'https://www.funcionpublica.gov.co/dafpIndexerBGN/norma/index'
OUT = C.RAW / 'funcionpublica'
TIPOS = {'Concepto': 'CONCEPTOS', 'Circular': 'CIRCULARES', 'Circular Externa': 'CIRCULARES',
         'Circular Conjunta': 'CIRCULARES', 'Resolución': 'RESOLUCIONES'}


def proyectos(prev):
    h = C.curl(f'{WWW1}/proyectos-normativos-de-la-funcion-publica', timeout=60)
    hoy = datetime.date.today().isoformat()
    vivos = {}
    for b in re.findall(r'<div class="col-md-5 card-box-nor1">(.*?)(?=<div class="col-md-5 card-box-nor1">|</div>\s*</div>\s*</div>)', h, re.S):
        m = re.search(r'<h3><a href="\s*([^"]*?)\s*">(.*?)</a></h3>', b, re.S)
        if not m:
            continue
        titulo = C.limpio(html.unescape(m.group(2)))
        url = (WWW1 + m.group(1).strip()) if m.group(1).strip().startswith('/') else m.group(1).strip()
        pub = re.search(r'Fecha de publicaci[oó]n:\s*</strong>\s*([^<]+)', b)
        plazo = re.search(r'Fecha env[ií]o de observaciones:\s*</strong>\s*([^<]+)', b)
        fechas = re.findall(r'\d{1,2} de [a-zA-Z]+ de \d{4}', plazo.group(1)) if plazo else []
        anexos = [WWW1 + u.strip() for u in re.findall(r'href="\s*(/documents/[^"]+?)\s*"', b)]
        k = hashlib.sha1(titulo.encode()).hexdigest()[:16]
        t = C.fold(titulo)
        vivos[k] = {'id': k, 'tipo_norma': ('Proyecto de Decreto' if 'decreto' in t else 'Proyecto de Resolución' if 'resoluc' in t
                                            else 'Proyecto de Circular' if 'circular' in t else 'Proyecto normativo'),
                    'titulo': titulo, 'dependencia': '', 'fecha_inicio': C.fecha_larga(fechas[0]) if fechas else '',
                    'fecha_fin': C.fecha_larga(fechas[1]) if len(fechas) > 1 else '', 'comentarios_a': '', 'url': url,
                    'anexos': [a for a in dict.fromkeys(anexos) if a != url],
                    'creado': C.fecha_larga(pub.group(1)) if pub else '', 'visto': hoy, 'vigente_en_fuente': True}
    out = dict(prev)
    for k, v in out.items():
        if k not in vivos:
            v['vigente_en_fuente'] = False
    out.update(vivos)
    return out, len(vivos)


def lista(tipo, anio):
    filas, offset = [], 0
    while True:
        u = (f'{IDX}?find=FindNext&query=&filtroTipoDocumento={urllib.parse.quote(tipo)}&filtroNumero=&filtroAnio={anio}&filtroEntidad='
             f'&filtroTema=&filtroSubtema=&ordenarPor=&offset={offset}&max=10')
        h = C.curl(u, timeout=90)
        hallados = re.findall(r'class="norma-titulo"><a href="[^"]*norma\.php\?i=(\d+)"[^>]*>\s*(.*?)\s*</a></p>\s*'
                              r'(?:<p class="norma-resumen">(.*?)</p>)?', h, re.S)
        filas += hallados
        if len(hallados) < 10 or 'nextLink' not in h:
            return filas
        offset += 10
        time.sleep(.2)


def fecha_ficha(i, cache):
    if i in cache:                       # una ficha trae 2026 por 2025: fecha futura = sin fecha
        return cache[i] if cache[i] <= datetime.date.today().isoformat() else ''
    h = C.curl(f'https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i={i}', timeout=60, intentos=2)
    m = re.search(r'Fecha de Expedici[^:]{1,10}:\s*(\d{1,2} de [^<\s]+ de \d{4})', h)
    cache[i] = C.fecha_larga(m.group(1)) if m else ''
    time.sleep(.1)
    return cache[i] if cache[i] <= datetime.date.today().isoformat() else ''


def normas(anios):
    fechas = C.leer(OUT / 'fechas.json', {}) or {}
    prev = {str(x['i']): x for x in (C.leer(OUT / 'normas.json', {}) or {}).get('items', []) if x.get('i')}
    for anio in anios:
        for tipo, t in TIPOS.items():
            for i, titulo, resumen in lista(tipo, anio):
                titulo = C.limpio(html.unescape(titulo))
                if tipo != 'Concepto' and 'funcion publica' not in C.fold(titulo):
                    continue
                try:
                    f = fecha_ficha(i, fechas)
                except RuntimeError:
                    f = ''
                m = re.search(r'(\d[\d-]*)\s+de\s+(20\d{2})', titulo)
                desc = C.limpio(html.unescape(resumen or ''))
                prev[i] = {'i': i, 'tipo': t, 'subtipo': tipo, 'numero': m.group(1) if m else '',
                           'anio': m.group(2) if m else str(anio), 'fecha': f, 'titulo': titulo,
                           'descripcion': desc[:700] or titulo,
                           # un concepto sobre vacaciones o encargos no es un acto de personal
                           'administrativo': tipo != 'Concepto' and C.es_administrativo(desc),
                           'url': f'https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i={i}'}
        C.escribir(OUT / 'fechas.json', fechas)
    return list(prev.values())


def agenda():
    h = C.curl(f'{WWW1}/agenda-regulatoria', timeout=60)
    docs = re.findall(r'href="(/documents/[^"]+)"', h)
    anios = lambda u: max([int(a) for a in re.findall(r'20[12]\d', html.unescape(u).split('?')[0])] or [0])
    if not docs:
        return None
    u = max(docs, key=anios)
    a = anios(u)
    return {'tipo': 'AGENDA REGULATORIA', 'subtipo': 'Agenda regulatoria', 'numero': '', 'anio': str(a), 'fecha': '',
            'titulo': f'Agenda regulatoria {a} · Función Pública', 'descripcion': f'Agenda regulatoria {a} de la Función Pública',
            'administrativo': False, 'url': WWW1 + html.unescape(u)}


def fetch(desde):
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    ok = True
    try:
        prev = (C.leer(OUT / 'proyectos.json', {}) or {}).get('items', {})
        items, vivos = proyectos(prev)
        if not vivos:
            raise RuntimeError('ninguna tarjeta de proyecto')
        C.escribir(OUT / 'proyectos.json', {'generado': gen, 'items': items})
        print(f'  funcionpublica · {vivos} proyectos · {len(items)} acumulados')
    except Exception as e:
        ok = False
        print(f'  funcionpublica · proyectos FALLÓ ({e})', file=sys.stderr)
    try:
        anio = datetime.date.today().year
        ns = normas(range(desde or anio, anio + 1))
        ag = agenda()
        ns = [n for n in ns if n['tipo'] != 'AGENDA REGULATORIA'] + ([ag] if ag else [])
        if len(ns) < 50:
            raise RuntimeError(f'solo {len(ns)} normas')
        C.escribir(OUT / 'normas.json', {'generado': gen, 'items': ns})
        print(f'  funcionpublica · {len(ns)} conceptos, circulares y resoluciones · {sum(1 for n in ns if n["fecha"])} con fecha')
    except Exception as e:
        ok = False
        print(f'  funcionpublica · normas FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('fetch')
    p.add_argument('--desde', type=int, help='año desde el que se relee (por defecto, el actual)')
    a = ap.parse_args()
    if a.cmd == 'fetch':
        sys.exit(0 if fetch(a.desde) else 1)


if __name__ == '__main__':
    main()
