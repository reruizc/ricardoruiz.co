#!/usr/bin/env python3
"""
Caudal · Ministerio de Comercio, Industria y Turismo · borradores fuera de SUCOP.

MinComercio publica sus proyectos de decreto, resolución y circular en su
propio sitio (Kentico), una página por tipo y año:

  /normatividad/proyectos-de-normatividad/proyectos-de-{decreto|resolucion|circular}-{AAAA}

Cada proyecto es una fila de tabla: en la primera celda un párrafo libre con
el epígrafe entre comillas, el correo para comentarios y la ventana escrita en
palabras («desde el 20 de octubre y hasta el 3 de noviembre de 2026»); en la
segunda, los enlaces «Ver documento» y «Memoria justificativa» (.aspx que
redirige al PDF). Se leen el año en curso y el anterior.

Salida: `Bases de datos/caudal-entidades/raw/mincomercio/proyectos.json`,
acumulado por id (si un proyecto desaparece de la página se conserva con
`vigente_en_fuente: false`, igual que MinSalud).

Uso: python3 tools/caudal/entidades/harvest_mincomercio.py fetch
"""
import argparse
import datetime
import hashlib
import html
import re
import sys

import comun as C

ENTIDAD = 'Ministerio de Comercio, Industria y Turismo'
BASE = 'https://www.mincit.gov.co'
OUT = C.RAW / 'mincomercio'
TIPOS = {'decreto': 'Proyecto de Decreto', 'resolucion': 'Proyecto de Resolución',
         'circular': 'Proyecto de Circular'}
MESES = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 'julio': 7,
         'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12}
_M = '(' + '|'.join(MESES) + ')'
# «desde el 20 de octubre y hasta el 3 de noviembre de 2026» · «desde el 3 y hasta
# el 7 de octubre de 2026» · «desde el 27 de junio hasta el 3 de julio de 2026»
_VENTANA = re.compile(rf'(?i)desde\s+el\s+(\d{{1,2}})(?:\s+de\s+{_M})?(?:\s+de\s+(\d{{4}}))?\s*,?\s*'
                      rf'(?:y\s+)?hasta\s+el\s+(\d{{1,2}})\s+de\s+{_M}\s+(?:de|del)\s+(\d{{4}})')
_PUBLICADO = re.compile(rf'(?i)publicad[oa].{{0,120}}?desde\s+el\s+(\d{{1,2}})\s+de\s+{_M}\s+de\s+(\d{{4}})')
_EPI = re.compile(r'[«"“]\s*(.+?)\s*[»"”]', re.S)


def _fecha(a, m, d):
    try:
        return datetime.date(int(a), MESES[m.lower()], int(d)).isoformat()
    except (KeyError, ValueError, TypeError):
        return ''


def ventana(txt):
    m = _VENTANA.search(txt)
    if not m:
        return '', ''
    d1, m1, a1, d2, m2, a2 = m.groups()
    fin = _fecha(a2, m2, d2)
    m1 = m1 or m2
    a1 = a1 or a2
    # cruce de año: «desde el 22 de diciembre y hasta el 5 de enero de 2026»
    if not m.group(3) and MESES[m1.lower()] > MESES[m2.lower()]:
        a1 = str(int(a2) - 1)
    return _fecha(a1, m1, d1), fin


def _texto(frag):
    return C.limpio(html.unescape(re.sub(r'<br\s*/?>', ' ', frag)))


def filas(tipo, anio):
    h = C.curl(f'{BASE}/normatividad/proyectos-de-normatividad/proyectos-de-{tipo}-{anio}', timeout=60)
    hoy = datetime.date.today().isoformat()
    out = []
    for r in re.findall(r'<tr>(.*?)</tr>', h, re.S):
        tds = re.findall(r'<td[^>]*>(.*?)</td>', r, re.S)
        if len(tds) < 1:
            continue
        txt = _texto(tds[0])
        if len(txt) < 40:
            continue
        me = _EPI.search(txt)
        epi = (me.group(1) if me else txt.split('. Se publica')[0]).strip(' .')
        epi = epi[:1].upper() + epi[1:]
        ini, fin = ventana(txt)
        mp = _PUBLICADO.search(txt)
        pub = _fecha(mp.group(3), mp.group(2), mp.group(1)) if mp else ''
        mail = re.search(r'mailto:([^"\s>]+)', r)
        links = re.findall(r'href="([^"]+\.aspx)"[^>]*>(?:\s*<[^>]+>)*\s*([^<]+)', r)
        doc = next((BASE + u for u, t in links if 'documento' in t.lower()), '')
        anexos = [BASE + u for u, t in links if 'documento' not in t.lower()]
        if not doc and links:
            doc = BASE + links[0][0]
        clave = doc or epi
        out.append({
            'id': hashlib.sha1(clave.encode()).hexdigest()[:16], 'tipo_norma': TIPOS[tipo],
            'titulo': epi, 'dependencia': '', 'fecha_inicio': ini, 'fecha_fin': fin,
            'comentarios_a': mail.group(1) if mail else '', 'url': doc, 'anexos': anexos,
            'creado': pub or ini, 'visto': hoy, 'vigente_en_fuente': True,
            'pagina': f'{BASE}/normatividad/proyectos-de-normatividad/proyectos-de-{tipo}-{anio}',
        })
    return out


def fetch():
    OUT.mkdir(parents=True, exist_ok=True)
    prev = (C.leer(OUT / 'proyectos.json', {}) or {}).get('items', {})
    hoy = datetime.date.today()
    vivos, fallos = {}, []
    for anio in (hoy.year - 1, hoy.year):
        for tipo in TIPOS:
            try:
                for f in filas(tipo, anio):
                    vivos[f['id']] = f
            except Exception as e:           # una página caída no tumba las otras
                fallos.append(f'{tipo}-{anio}: {e}')
                print(f'  ! {tipo}-{anio}: {e}', file=sys.stderr)
    if not vivos:
        print('  ninguna página respondió: se conserva el archivo anterior', file=sys.stderr)
        return False
    items = dict(prev)
    for k, v in items.items():
        if k not in vivos:
            v['vigente_en_fuente'] = False
    items.update(vivos)
    C.escribir(OUT / 'proyectos.json', {'generado': datetime.datetime.now().isoformat(timespec='seconds'),
                                        'entidad': ENTIDAD, 'items': items, 'fallos': fallos})
    sin_v = sum(1 for v in vivos.values() if not v['fecha_fin'])
    abiertos = sum(1 for v in vivos.values() if v['fecha_fin'] >= hoy.isoformat())
    print(f'  mincomercio · {len(vivos)} proyectos leídos · {abiertos} abiertos · {sin_v} sin ventana'
          f' · {len(items)} acumulados · {len(fallos)} páginas fallidas')
    return len(fallos) < 3


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('fetch')
    a = ap.parse_args()
    if a.cmd == 'fetch':
        sys.exit(0 if fetch() else 1)


if __name__ == '__main__':
    main()
