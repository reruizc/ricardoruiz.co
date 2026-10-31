#!/usr/bin/env python3
"""
Caudal · Servicio Nacional de Aprendizaje (tanda 2, oct-2026).

  proyectos  www.sena.edu.co/api/cms/page/proyectos-normativos          (JSON)
  normas     normograma.sena.edu.co/compilacion/novedades_*.html        (por mes)

⚠️ El normograma va con un mes de rezago, y es una compilación: casi todo lo que
trae es de otras entidades. Solo entran las páginas `*_sena.html` de cada mes.
⚠️ Las filas del normograma no traen fecha: se usa el último día del mes de la
novedad, que es la de incorporación y no la de expedición.
⚠️ Casi todas sus circulares son internas (permisos, jornadas): solo las que hablan
de aprendices, monetización o formación quedan fuera de lo administrativo.
⚠️ La descripción de los proyectos trae correos de funcionarios: se quitan siempre.

Salida: `Bases de datos/caudal-entidades/raw/sena/{proyectos,normas}.json`.
Uso: python3 tools/caudal/entidades/harvest_sena.py fetch [--desde 2025]
"""
import argparse
import datetime
import hashlib
import html
import json
import re
import sys

import comun as C

WWW = 'https://www.sena.edu.co'
NORMO = 'https://normograma.sena.edu.co/compilacion'
OUT = C.RAW / 'sena'
_EXTERNA = re.compile(r'(?i)aprendiz|monetiz|cuota de|formaci[oó]n profesional|empresa|empleador|certificaci[oó]n de competencias|'
                      r'fondo emprender|fic\b|contrato de aprendizaje')
_MES = re.compile(r'1_a_(\d+)_([a-z]+)_(20\d{2})\.html')
TIPOS = {'resolucion': ('RESOLUCIONES', 'Resolución'), 'acuerdo': ('RESOLUCIONES', 'Acuerdo'), 'circular': ('CIRCULARES', 'Circular')}


def _txt(s):
    return C.limpio(html.unescape(re.sub(r'<!--.*?-->', '', s or '', flags=re.S)))


def proyectos(prev):
    d = json.loads(C.curl(f'{WWW}/api/cms/page/proyectos-normativos', timeout=60))['data']
    hoy = datetime.date.today().isoformat()
    vivos = {}
    for r in d.get('proyectos') or []:
        titulo = _txt(r.get('title'))
        if not titulo:
            continue
        desc = re.sub(r'\S+@\S+(?:\s+[,y]\s+\S+@\S+)*', ' ', _txt(r.get('description')))
        desc = re.sub(r'\s+', ' ', desc).strip()
        ini, fin = C.ventana(desc)
        p = re.match(r'(\d{2})/(\d{2})/(\d{4})', r.get('date') or '')
        creado = f'{p.group(3)}-{p.group(2)}-{p.group(1)}' if p else ''
        u = r.get('href') or ''
        k = hashlib.sha1((r.get('id') or titulo).encode()).hexdigest()[:16]
        t = C.fold(titulo)
        vivos[k] = {'id': k, 'tipo_norma': ('Proyecto de Acuerdo' if 'acuerdo' in t[:40] else 'Proyecto de Resolución' if 'resoluc' in t[:40]
                                            else 'Proyecto normativo'),
                    'titulo': titulo, 'dependencia': '', 'fecha_inicio': ini or creado, 'fecha_fin': fin, 'comentarios_a': '',
                    'objeto': desc[:500], 'url': WWW + u if u.startswith('/') else u, 'anexos': [], 'creado': creado, 'visto': hoy,
                    'vigente_en_fuente': True}
    out = dict(prev)
    for k, v in out.items():
        if k not in vivos:
            v['vigente_en_fuente'] = False
    out.update(vivos)
    return out, len(vivos)


def _mes(pagina):
    m = C.curl(f'{NORMO}/{pagina}', timeout=60)
    salida = []
    p = _MES.search(pagina)
    fecha = C.fecha_larga(f'{p.group(1)} de {p.group(2)} de {p.group(3)}') if p else ''
    for sub in sorted(set(re.findall(r'href="(1_a_[^"]+_sena\.html)"', m))):
        h = C.curl(f'{NORMO}/{sub}', timeout=60)
        for b in re.split(r'<div class="opcion-nueva">', h)[1:]:
            u = re.search(r'href="(docs/([a-z]+)_sena_0*(\d+)_(20\d{2})\.htm)"', b)
            if not u or u.group(2) not in TIPOS:
                continue
            d = re.search(r'class="descripcion-documento">(.*?)</div>', b, re.S)
            desc = _txt(d.group(1)) if d else ''
            ide = re.search(r'class="id-documento">(.*?)</div>', b, re.S)
            titulo = re.sub(r'\s+SENA$', '', _txt(ide.group(1))) if ide else ''
            n = re.search(r'(\d[\d-]*)\s+de\s+20\d{2}', titulo)
            tipo = TIPOS[u.group(2)]
            interna = tipo[1] == 'Circular' and not _EXTERNA.search(desc)
            salida.append({'tipo': tipo[0], 'subtipo': tipo[1], 'numero': n.group(1) if n else u.group(3), 'anio': u.group(4), 'fecha': fecha,
                           'titulo': titulo or f'{tipo[1]} {u.group(3)} de {u.group(4)}', 'descripcion': desc or titulo,
                           'administrativo': interna or not desc or C.es_administrativo(desc), 'url': f'{NORMO}/{u.group(1)}'})
    return salida


def normas(prev, desde):
    out = {x['url']: x for x in prev}
    h = C.curl(f'{NORMO}/novedades_normativas_jurisprudenciales.html', timeout=60)
    meses = [x for x in dict.fromkeys(re.findall(r'href="(novedades_1_a_\d+_[a-z]+_(20\d{2})\.html)"', h)) if int(x[1]) >= desde]
    for pag, _ in (meses if not prev else meses[:3]):
        for x in _mes(pag):
            out[x['url']] = x
    return list(out.values())


def fetch(desde):
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    ok = True
    try:
        prev = (C.leer(OUT / 'proyectos.json', {}) or {}).get('items', {})
        items, n = proyectos(prev)
        C.escribir(OUT / 'proyectos.json', {'generado': gen, 'items': items})
        print(f'  sena · {n} proyectos · {len(items)} acumulados')
    except Exception as e:
        ok = False
        print(f'  sena · proyectos FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)
    try:
        prev = (C.leer(OUT / 'normas.json', {}) or {}).get('items', [])
        xs = normas(prev, desde or datetime.date.today().year - 1)
        C.escribir(OUT / 'normas.json', {'generado': gen, 'items': xs})
        print(f'  sena · {len(xs)} normas')
    except Exception as e:
        ok = False
        print(f'  sena · normas FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('fetch')
    p.add_argument('--desde', type=int, help='primer año del normograma (por defecto, el anterior)')
    a = ap.parse_args()
    sys.exit(0 if fetch(a.desde) else 1)


if __name__ == '__main__':
    main()
