#!/usr/bin/env python3
"""
Caudal · Ministerio del Trabajo (tanda 1, oct-2026). Sus borradores ya entran por
SUCOP y lo expedido por el Diario Oficial; esto suma lo que solo está en su sitio.

  resoluciones  /atencion-al-ciudadano/transparencia/resoluciones   tabla completa
  circulares    /normatividad/circulares-generales                  tabla completa
                (⚠️ `/transparencia/circulares` se quedó en 2017)
  conceptos     /normatividad/conceptos-institucionales   biblioteca Liferay con una
                carpeta por año (`CARPETAS`). El tema va en el nombre del archivo:
                «05EE2026…-EMPRESAS DE SERVICIO TEMPORALES». La fecha no: la lista
                dice «Modificado hace 13 días por…» y se convierte una sola vez (queda aproximada).
  agenda        /normatividad/agenda-regulatoria   el archivo vigente de la carpeta
  comunicados   el menú de cualquier página los trae todos, por año y mes

⚠️ Las páginas pesan 1-5 MB. ⚠️ Al cambiar el año hay que sumar la carpeta nueva a
CARPETAS: el cosechador falla si no encuentra conceptos del año en curso.

Salida: `Bases de datos/caudal-entidades/raw/mintrabajo/{normas,noticias}.json`.
Uso: python3 tools/caudal/entidades/harvest_mintrabajo.py fetch
"""
import argparse
import datetime
import html
import re
import sys

import comun as C

BASE = 'https://www.mintrabajo.gov.co'
WEB = f'{BASE}/web/guest'
OUT = C.RAW / 'mintrabajo'
PORTLET = '_com_liferay_document_library_web_portlet_DLPortlet_INSTANCE_'
CARPETAS = {2026: ('ibTq83AtGipJ', '88560537'), 2025: ('ek3IkHhzBrmv', '88487541')}
AGENDA = 'pus168hhEuFt'


def tabla(url, tipo, subtipo):
    """Las dos tablas del chasis: Tipo · Norma · Epígrafe · Fecha · Acceso."""
    h = C.curl(url, timeout=90)
    out = []
    for r in re.findall(r'<tr[^>]*>(.*?)</tr>', h, re.S):
        c = {k: C.limpio(html.unescape(v)) for k, v in re.findall(r'data-label="([^"]+)"[^>]*>(.*?)</td>', r, re.S)}
        norma, ep = c.get('Norma', ''), c.get('Epígrafe', '')
        if not norma or not ep:
            continue
        fecha = C.fecha_larga(c.get('Fecha de Expedición', ''))
        m = re.search(r'(\d[\d-]*)', norma)
        a = re.search(r'\b((?:19|20)\d{2})\b', norma) or re.search(r'((?:19|20)\d{2})', fecha)
        href = re.search(r'href="([^"]+)"', r)
        u = html.unescape(href.group(1)) if href else url
        out.append({'tipo': tipo, 'subtipo': subtipo, 'numero': (m.group(1).lstrip('0') or '0') if m else '',
                    'anio': a.group(1) if a else '', 'fecha': fecha, 'titulo': f'{subtipo} {norma}'.strip(),
                    'descripcion': ep, 'administrativo': C.es_administrativo(ep),
                    'url': BASE + u if u.startswith('/') else u})
    return out


def _hace(txt, hoy):
    m = re.search(r'(?i)Modificado hace\s+(\d+|un|una)\s+(minuto|hora|d[ií]a|semana|mes|año)', txt or '')
    if not m:
        return ''
    n = 1 if m.group(1).lower() in ('un', 'una') else int(m.group(1))
    dias = {'minuto': 0, 'hora': 0, 'semana': 7, 'mes': 30, 'año': 365}.get(m.group(2).lower(), 1) * n
    return (hoy - datetime.timedelta(days=dias)).isoformat()


def conceptos(prev):
    hoy = datetime.date.today()
    previos = {x['numero']: x for x in prev}
    out, vistos_anio = {}, {}
    for anio, (inst, folder) in CARPETAS.items():
        vistos, pag = set(), 1
        while True:
            p = PORTLET + inst
            u = (f'{WEB}/normatividad/conceptos-institucionales/-/document_library/{inst}/view/{folder}'
                 f'?{p}_folderId={folder}&{p}_curEntry={pag}&{p}_deltaEntry=20&{p}_orderByCol=modifiedDate&{p}_orderByType=desc')
            h = C.curl(u, timeout=120)
            trozos = re.split(rf'(?=id="{p}_entries_\d+")', h)[1:]
            nuevos = 0
            for t in trozos:
                m = re.search(r'data-title="([^"]+)"', t[:600])
                if not m:
                    continue
                nombre = C.limpio(html.unescape(html.unescape(m.group(1))))
                nombre = re.sub(r'(?i)\.pdf$', '', nombre)
                r = re.search(r'(\d{2}[A-Z]{2}(20\d{2})\d{6,})', nombre)
                if not r or r.group(1) in vistos:
                    continue
                vistos.add(r.group(1))
                nuevos += 1
                tema = C.limpio(re.sub(r'\d{2}[A-Z]{2}20\d{2}\d{6,}', ' ', nombre))
                tema = re.sub(r'(?i)^radicado no\.?|\(\d+\)$', ' ', tema)
                tema = C.limpio(re.sub(r'^[\s\-–&;#\d]*(?:y\s+)?', '', tema)).strip(' -–')
                pdf = re.search(r"url\('(https://www\.mintrabajo\.gov\.co/documents/[^?']+)", t)
                ant = previos.get(r.group(1))
                out[r.group(1)] = {'tipo': 'CONCEPTOS', 'subtipo': 'Concepto', 'numero': r.group(1), 'anio': r.group(2),
                                   'fecha': (ant or {}).get('fecha') or _hace(t, hoy), 'titulo': f'Concepto {r.group(1)}',
                                   'descripcion': tema.capitalize() or f'Concepto {r.group(1)}', 'administrativo': False,
                                   'url': pdf.group(1) if pdf else f'{WEB}/normatividad/conceptos-institucionales'}
            if not nuevos or pag >= 10:
                break
            pag += 1
        vistos_anio[anio] = len(vistos)
    actual = hoy.year
    if not vistos_anio.get(actual):
        raise RuntimeError(f'sin conceptos de {actual}: ¿falta su carpeta en CARPETAS?')
    return list({**previos, **out}.values()), vistos_anio


def agenda():
    h = C.curl(f'{WEB}/normatividad/agenda-regulatoria', timeout=90)
    m = re.search(r'data-title="(AGENDA REGULATORIA[^"]+)"', h)
    if not m:
        return None
    t = C.limpio(html.unescape(m.group(1)))
    u = re.search(r"url\('(https://www\.mintrabajo\.gov\.co/documents/[^?']+)", h[m.start():m.start() + 4000])
    f = re.search(r'(\d{2})-(\d{2})-(20\d{2})', t)
    return {'tipo': 'AGENDA REGULATORIA', 'subtipo': 'Agenda regulatoria', 'numero': '', 'anio': f.group(3) if f else '',
            'fecha': f'{f.group(3)}-{f.group(2)}-{f.group(1)}' if f else '', 'titulo': t.capitalize(),
            'descripcion': f'{t.capitalize()} · Ministerio del Trabajo', 'administrativo': False,
            'url': u.group(1) if u else f'{WEB}/normatividad/agenda-regulatoria'}


def comunicados(prev):
    """Del menú: «Comunicados 2026» → mes → títulos. Sin día: lo que ya existía
    queda con el primero del mes; lo nuevo, con el día en que se vio."""
    hoy = datetime.date.today().isoformat()
    previos = {x['url']: x for x in prev}
    primera = not previos
    h = C.curl(f'{WEB}/prensa/comunicados', timeout=90)
    anio, mes = None, None
    out = {}
    for u, t in re.findall(r'class="dropdown-item[^"]*"\s+href="([^"]+)"\s+title="([^"]*)"', h):
        t = C.limpio(html.unescape(t))
        y = re.match(r'Comunicados (20\d{2})$', t)
        if y:
            anio, mes = y.group(1), None
            continue
        if anio is None:
            continue
        if int(anio) < datetime.date.today().year:
            break
        if C.fold(t) in C.MESES:
            mes = C.MESES[C.fold(t)]
            continue
        if mes is None:
            continue
        ant = previos.get(u)
        f = (ant or {}).get('fecha') or (f'{anio}-{mes:02d}-01' if primera else hoy)
        out[u] = C.comunicado(t, f, u)
    return list({**previos, **out}.values())


def fetch():
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    ok = True
    prev = (C.leer(OUT / 'normas.json', {}) or {}).get('items', [])
    try:
        res = tabla(f'{WEB}/atencion-al-ciudadano/transparencia/resoluciones', 'RESOLUCIONES', 'Resolución')
        cir = tabla(f'{WEB}/normatividad/circulares-generales', 'CIRCULARES', 'Circular')
        if len(res) < 300 or len(cir) < 50:
            raise RuntimeError(f'{len(res)} resoluciones y {len(cir)} circulares: ¿cambió la tabla?')
        con, por_anio = conceptos([x for x in prev if x['tipo'] == 'CONCEPTOS'])
        ag = agenda()
        items = res + cir + con + ([ag] if ag else [])
        C.escribir(OUT / 'normas.json', {'generado': gen, 'items': items})
        print(f'  mintrabajo · {len(res)} resoluciones · {len(cir)} circulares · {len(con)} conceptos {por_anio}'
              f' · agenda {"sí" if ag else "NO"}')
    except Exception as e:
        ok = False
        print(f'  mintrabajo · normas FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)
    try:
        pn = (C.leer(OUT / 'noticias.json', {}) or {}).get('items', [])
        xs = comunicados(pn)
        if not xs:
            raise RuntimeError('ningún comunicado en el menú')
        C.escribir(OUT / 'noticias.json', {'generado': gen, 'items': xs})
        print(f'  mintrabajo · {len(xs)} comunicados del año')
    except Exception as e:
        ok = False
        print(f'  mintrabajo · comunicados FALLÓ ({e})', file=sys.stderr)
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('fetch')
    if ap.parse_args().cmd == 'fetch':
        sys.exit(0 if fetch() else 1)


if __name__ == '__main__':
    main()
