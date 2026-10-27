#!/usr/bin/env python3
"""
Caudal · Superintendencia Financiera de Colombia (fase 2, oct-2026).

Del pilar Regulatorio ya venían sus sanciones del mercado de valores. Esto suma
lo normativo, que su CMS publica en tablas (`/publicaciones/{id}/`):

  proyectos      10082380 (proyectos de norma) y 10088401 (documentos técnicos
                 para comentarios): número · objeto · documentos · plazo
                 («Viernes 30 de octubre hasta las 05:00 p.m», sin año: el año
                 sale del número «20_2026») · correo.
  normas del año circulares externas, cartas circulares y resoluciones: número
                 · fecha («Octubre 23», sin año) · descripción · boletín. ⚠️ Los
                 id de estas páginas CAMBIAN cada año: van en NORMAS_POR_ANIO y
                 hay que sumar el del año nuevo (el índice /publicaciones/20149/
                 los enlaza).
  descargas      loader.php?…&idFile=N (enlace permanente al PDF).

⚠️ Los conceptos (catálogo ABCD, `buscar_integrada.php`) no se usan: la búsqueda
ignora la expresión y devuelve siempre la colección completa (18.901), y lo más
reciente que muestra es de 2021. Queda como faltante en el catálogo.
⚠️ El sitio da 502 sueltos: `comun.curl` reintenta.

Salida: `Bases de datos/caudal-entidades/raw/superfinanciera/{proyectos,normas}.json`.
Uso: python3 tools/caudal/entidades/harvest_superfinanciera.py fetch
"""
import argparse
import datetime
import hashlib
import html
import re
import sys

import comun as C

BASE = 'https://www.superfinanciera.gov.co'
OUT = C.RAW / 'superfinanciera'
PROYECTOS = {'10082380': 'Proyecto de norma', '10088401': 'Documento técnico para comentarios'}
NORMAS_POR_ANIO = {
    2026: {'10115974': ('CIRCULARES', 'Circular externa'),
           '10115975': ('CIRCULARES', 'Carta circular'),
           '10115976': ('RESOLUCIONES', 'Resolución')},
}
MESES = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 'julio': 7,
         'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12}


def _filas(h):
    out = []
    for r in re.findall(r'<tr[^>]*>(.*?)</tr>', h, re.S):
        tds = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S)
        celdas = [C.limpio(html.unescape(re.sub(r'<[^>]+>', ' ', c))) for c in tds]
        links = [BASE + html.unescape(u) if u.startswith('/') else html.unescape(u)
                 for u in re.findall(r'href="([^"]+)"', r) if 'loader.php' in u or u.endswith('.pdf')]
        mails = re.findall(r'[\w.+-]+@superfinanciera\.gov\.co', r)
        out.append((celdas, links, mails))
    return out


def _fecha(anio, txt):
    """«Viernes 30 de octubre hasta…» o «Octubre 23», sin año. Primero día+mes,
    después mes+día: al revés, «Viernes 30» se leía como el mes «viernes»."""
    t = txt or ''
    for rx, dg, mg in ((r'(?i)(\d{1,2})\s+(?:de\s+)?([a-záéíóú]+)', 1, 2), (r'(?i)([a-záéíóú]+)\s+(\d{1,2})', 2, 1)):
        for m in re.finditer(rx, t):
            mes = m.group(mg).lower()
            if mes in MESES:
                try:
                    return datetime.date(int(anio), MESES[mes], int(m.group(dg))).isoformat()
                except ValueError:
                    return ''
    return ''


def proyectos(prev):
    hoy = datetime.date.today().isoformat()
    vivos = {}
    for pid, tipo in PROYECTOS.items():
        h = C.curl(f'{BASE}/publicaciones/{pid}/', timeout=90)
        for celdas, links, mails in _filas(h):
            if len(celdas) < 4 or not re.search(r'\d', celdas[0]) or celdas[0].lower().startswith('proyecto'):
                continue
            m = re.search(r'(\d{1,3})\s*[-_]\s*(20\d{2})', celdas[0])
            if not m:
                continue
            num, anio = m.group(1).lstrip('0') or '0', m.group(2)
            fin = _fecha(anio, celdas[3])
            k = hashlib.sha1(f'{pid}-{num}-{anio}'.encode()).hexdigest()[:16]
            vivos[k] = {'id': k, 'tipo_norma': f'{tipo} {num} de {anio}', 'titulo': celdas[1],
                        'dependencia': '', 'fecha_inicio': '', 'fecha_fin': fin,
                        'comentarios_a': '; '.join(dict.fromkeys(mails)), 'url': links[0] if links else '',
                        'anexos': links[1:], 'creado': fin[:4] and f'{anio}-01-01', 'visto': hoy,
                        'vigente_en_fuente': True, 'numero': num, 'anio': anio}
    out = dict(prev)
    for k, v in out.items():
        if k not in vivos:
            v['vigente_en_fuente'] = False
    out.update(vivos)
    return out, len(vivos)


def normas():
    out = []
    for anio, paginas in NORMAS_POR_ANIO.items():
        for pid, (tipo, subtipo) in paginas.items():
            h = C.curl(f'{BASE}/publicaciones/{pid}/', timeout=90)
            if str(anio) not in h[:4000] and str(anio) not in h:
                raise RuntimeError(f'la página {pid} no dice {anio}: ¿cambió el id?')
            for celdas, links, _ in _filas(h):
                if len(celdas) < 3 or not re.match(r'\d', celdas[0]):
                    continue
                desc = celdas[2]
                out.append({'tipo': tipo, 'subtipo': subtipo, 'numero': celdas[0].lstrip('0') or '0',
                            'anio': str(anio), 'fecha': _fecha(anio, celdas[1]),
                            'titulo': f'{subtipo} {celdas[0]} de {anio}', 'descripcion': desc,
                            'administrativo': C.es_administrativo(desc),
                            'url': links[0] if links else f'{BASE}/publicaciones/{pid}/'})
    return out


def fetch():
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    ok = True
    try:
        prev = (C.leer(OUT / 'proyectos.json', {}) or {}).get('items', {})
        items, vivos = proyectos(prev)
        C.escribir(OUT / 'proyectos.json', {'generado': gen, 'items': items})
        hoy = datetime.date.today().isoformat()
        print(f'  superfinanciera · {vivos} proyectos · '
              f'{sum(1 for v in items.values() if v["fecha_fin"] >= hoy)} abiertos')
    except Exception as e:
        ok = False
        print(f'  superfinanciera · proyectos FALLÓ ({e})', file=sys.stderr)
    try:
        ns = normas()
        if len(ns) < 50:
            raise RuntimeError(f'solo {len(ns)} normas')
        C.escribir(OUT / 'normas.json', {'generado': gen, 'items': ns})
        print(f'  superfinanciera · {len(ns)} circulares, cartas circulares y resoluciones del año '
              f'({sum(1 for n in ns if n["administrativo"])} trámites internos)')
    except Exception as e:
        ok = False
        print(f'  superfinanciera · normas FALLÓ ({e}) — se conserva el archivo anterior', file=sys.stderr)
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('fetch')
    if ap.parse_args().cmd == 'fetch':
        sys.exit(0 if fetch() else 1)


if __name__ == '__main__':
    main()
