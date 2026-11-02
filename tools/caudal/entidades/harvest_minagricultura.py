#!/usr/bin/env python3
"""
Caudal · Ministerio de Agricultura y Desarrollo Rural (tanda 3, nov-2026).

  resoluciones  /normatividad/resoluciones              (TYPO3, ~1.200 en una sola página de 1,2 MB)
  decretos      /normatividad/decretos                  (~250)
  noticias      /el-ministerio/sala-de-p/noticias/page-N

Cada norma es un `<article class="item_norm">` con `data-title`, `data-info` (el
epígrafe), `data-year` y `data-number`. No hay paginación: la lista completa viene
en el HTML, y por eso no hace falta `--todo`.
⚠️ `data-year` trae errores de captura (un decreto de 2022 figura en 2026): manda el
año del título. `data-link` a veces es un `t3://file?uid=N` sin resolver: se usa el
`href` del enlace.
⚠️ Muchas resoluciones enlazan a un OneDrive personal, no a /fileadmin/: esa es la
ruta pública que da el ministerio y no hay otra.
⚠️ `comun.fecha_larga` no lee «DE OCTUBRE» en mayúsculas: el título se le pasa en minúsculas.
⚠️ Tres de cada cuatro títulos solo traen el año y los PDF son escaneados: lo que ya
existía entra sin fecha y lo nuevo con el día en que aparece, como UGPP y MinVivienda.
⚠️ Los decretos ya entran por Presidencia: solo quedan los que `normativa.jsonl` no
trae, para no duplicarlos en el Ejecutivo.
⚠️ Sus proyectos normativos enlazan a SUCOP y la agenda es de la línea de agendas 2027:
no se leen acá.

Salida: `Bases de datos/caudal-entidades/raw/minagricultura/{normas,noticias}.json`.
Uso: python3 tools/caudal/entidades/harvest_minagricultura.py fetch
"""
import argparse
import datetime
import html
import json
import re
import subprocess
import sys

import comun as C

BASE = 'https://www.minagricultura.gov.co'
OUT = C.RAW / 'minagricultura'
DESDE = '2025'
CAIDA = .5          # una corrida con menos de la mitad de la anterior no se publica
_ART = re.compile(r'<article[^>]*\bitem_norm\b.*?</article>', re.S)
_NUM = re.compile(r'(?i)(?:resoluc?i?[oó]n|decreto)\s*(?:no\.?|n[°º.]*|nro\.?)?\s*0*(\d{1,6})')


def _guarda(nombre, leidos, previo):
    """Mide lo que dio la fuente, no lo acumulado: si cae a menos de la mitad
    de la corrida anterior, o a cero, se conserva el archivo que había."""
    antes = (previo or {}).get('leidos') or 0
    if not leidos or leidos < antes * CAIDA:
        raise RuntimeError(f'guarda: {nombre} trae {leidos} contra {antes} de la corrida anterior')


def _en_presidencia():
    """(año, número) de los decretos que ya trae el pilar Ejecutivo. Si S3 no
    responde se sigue sin filtrar: un repetido estorba menos que uno perdido."""
    try:
        r = subprocess.run(['aws', 's3', 'cp', 's3://caudal-legislativo/metadata/normativa.jsonl', '-'],
                           capture_output=True, check=True, timeout=120)
        filas = [json.loads(x) for x in r.stdout.decode().splitlines()]
    except Exception as e:
        print(f'  minagricultura · no se leyó normativa.jsonl ({e}): van todos los decretos', file=sys.stderr)
        return set()
    return {(str(x.get('anio')), str(x.get('numero')).lstrip('0')) for x in filas if x.get('tipo') == 'DECRETOS'}


def _fecha(titulo):
    """«DEL 27 DE OCTUBRE DE 2026» o «DE JULIO 29 DE 2026» → ISO; '' si solo trae el año."""
    t = titulo.lower()
    m = re.search(r'([a-záéíóú]+)\s+(\d{1,2})\s+de\s+(20\d{2})', t)
    return C.fecha_larga(t) or (C.fecha_larga(f'{m.group(2)} de {m.group(1)} de {m.group(3)}') if m else '')


def _lista(ruta, tipo, subtipo, previas, hoy):
    """Las normas del año pasado en adelante, y cuántas trae la página en total."""
    arts = _ART.findall(C.curl(f'{BASE}/normatividad/{ruta}', timeout=120))
    out = []
    for a in arts:
        g = lambda k: html.unescape((re.search(rf'data-{k}="([^"]*)"', a) or [None, ''])[1]).strip()
        titulo = C.limpio(g('title'))
        if titulo.lower().startswith('anexo'):
            continue
        anios = re.findall(r'\b(20\d{2})\b', titulo)
        anio = anios[-1] if anios else g('year')
        if anio < DESDE:
            continue
        u = re.search(r'<a[^>]*href="([^"]+)"', a)
        url = html.unescape(u.group(1)) if u else ''
        if url.startswith('/'):
            url = BASE + url
        elif not url.startswith('http'):
            continue
        n = _NUM.search(titulo)
        numero = n.group(1) if n else g('number').lstrip('0')
        desc = C.limpio(g('info')).strip(' "“”') or titulo
        # sin fecha en el título: lo que ya existía queda sin fecha y lo nuevo con el día en que aparece
        fecha = _fecha(titulo) or (previas[url]['fecha'] if url in previas else hoy if previas else '')
        clase = 'Acuerdo' if titulo.lower().startswith('acuerdo') else subtipo   # la lista de resoluciones trae acuerdos
        out.append({'tipo': tipo, 'subtipo': clase, 'numero': numero, 'anio': anio, 'fecha': fecha,
                    'titulo': titulo, 'descripcion': desc, 'administrativo': C.es_administrativo(desc), 'url': url})
    return out, len(arts)


def normas(prev):
    previas = {x['url']: x for x in prev.get('items', [])}
    hoy = datetime.date.today().isoformat()
    res, n1 = _lista('resoluciones', 'RESOLUCIONES', 'Resolución', previas, hoy)
    dec, n2 = _lista('decretos', 'DECRETOS', 'Decreto', previas, hoy)
    _guarda('normas', n1 + n2, prev)
    ya = _en_presidencia()
    nuevos = [d for d in dec if (d['anio'], d['numero']) not in ya]
    return res + nuevos, n1 + n2, len(dec)


def noticias(prev):
    out = {x['url']: x for x in prev.get('items', [])}
    leidos = 0
    for p in range(1, 4):
        h = C.curl(f"{BASE}/el-ministerio/sala-de-p/noticias{f'/page-{p}' if p > 1 else ''}", timeout=90)
        for t, u, cuerpo in re.findall(r'<a itemprop="url" title="([^"]*)" href="(/el-ministerio/sala-de-p/noticias/[^"]+)">(.*?)</a>', h, re.S):
            f = re.search(r'txt_(?:side|info)_date">(.*?)</div>', cuerpo, re.S)
            leidos += 1
            url = BASE + u
            out[url] = C.comunicado(C.limpio(html.unescape(t)), C.fecha_larga(C.limpio(f.group(1))) if f else '', url)
    _guarda('noticias', leidos, prev)
    return list(out.values()), leidos


def fetch():
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    ok = True
    try:
        xs, leidos, dec = normas(C.leer(OUT / 'normas.json', {}) or {})
        C.escribir(OUT / 'normas.json', {'generado': gen, 'leidos': leidos, 'items': xs})
        r = sum(1 for x in xs if x['tipo'] == 'RESOLUCIONES')
        print(f'  minagricultura · {leidos} normas en el sitio · {r} resoluciones desde {DESDE}'
              f' · {len(xs) - r} de {dec} decretos que Presidencia no trae')
    except Exception as e:
        ok = False
        print(f'  minagricultura · normas FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)
    try:
        xs, leidos = noticias(C.leer(OUT / 'noticias.json', {}) or {})
        C.escribir(OUT / 'noticias.json', {'generado': gen, 'leidos': leidos, 'items': xs})
        print(f'  minagricultura · {leidos} noticias leídas · {len(xs)} acumuladas')
    except Exception as e:
        ok = False
        print(f'  minagricultura · noticias FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('fetch')
    ap.parse_args()
    sys.exit(0 if fetch() else 1)


if __name__ == '__main__':
    main()
