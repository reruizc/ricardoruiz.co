#!/usr/bin/env python3
"""
Caudal · Departamento Nacional de Planeación (tanda 2, oct-2026).

  normas     colaboracion.dnp.gov.co/CDT/_api/web/lists/getbytitle('Normatividad')/items
  proyectos  www.dnp.gov.co/normativa/proyectos-de-normatividad

⚠️ La biblioteca mezcla normas con notificaciones judiciales, tutelas, revistas y
actas de conciliación: solo entra lo que está bajo `Normatividad-DNP/` o `Resoluciones/`.
⚠️ Las circulares casi siempre son escaneadas: quedan con el título. Solo las internas
se marcan como administrativas.
⚠️ `Modified` es la fecha de subida, no la de expedición: se prefiere la del título.
El objeto sale del PDF («Por el cual…»), una sola vez.
⚠️ Los proyectos no tienen filas: es un texto corrido por año, un aviso por proyecto.
⚠️ Más de la mitad de sus proyectos ya están en SUCOP: solo entra lo que SUCOP no tiene.
⚠️ `/Prensa_/Eventos` es un archivo de seminarios viejos: no sirve como calendario.

Salida: `Bases de datos/caudal-entidades/raw/dnp/{proyectos,normas}.json`.
Uso: python3 tools/caudal/entidades/harvest_dnp.py fetch
"""
import argparse
import datetime
import hashlib
import html
import json
import re
import subprocess
import sys
import urllib.parse

import comun as C

COLAB = 'https://colaboracion.dnp.gov.co'
WWW = 'https://www.dnp.gov.co'
OUT = C.RAW / 'dnp'
TXT = OUT / 'txt'
DESDE = '2025-01-01'
TIPOS = {'circular': ('CIRCULARES', 'Circular'), 'resolucion': ('RESOLUCIONES', 'Resolución')}   # los decretos entran por Presidencia
_NUM = re.compile(r'(?i)(decreto|circular|resoluci[oó]n)(?:\s+(?:externa|interna|conjunta))?\s*(?:no\.?|n[°º.]*|nro\.?)?\s*0*([\d-]{1,10})')
_OBJETO = re.compile(r'(?is)((?:por\s+(?:la|el|medio\s+de\s+la|medio\s+del)\s+cual)\b.+?)(?:\n\s*\n|\bCONSIDERANDO\b|\bEL\s+DIRECTOR\b|\bLA\s+DIRECTORA\b)')
_ASUNTO = re.compile(r'(?is)\b(?:ASUNTO|REFERENCIA|REF\.?)\s*:\s*(.+?)(?:\n\s*\n|Respetad|Cordial|Apreciad)')


def normas(prev):
    out = {x['url']: x for x in prev}
    u = (f"{COLAB}/CDT/_api/web/lists/getbytitle('Normatividad')/items?$select=FileRef,Modified,Title"
         f"&$orderby=Modified%20desc&$top=600").replace(' ', '%20').replace("'", '%27')
    TXT.mkdir(parents=True, exist_ok=True)
    for r in json.loads(C.curl(u, accept='application/json;odata=nometadata', timeout=120))['value']:
        ref = r.get('FileRef') or ''
        if (r.get('Modified') or '')[:10] < DESDE or not re.search(r'/Normatividad/(?:Normatividad-DNP|Resoluciones)/', ref):
            continue
        if '/Anexos/' in ref or not ref.lower().endswith('.pdf'):
            continue
        titulo = C.limpio(html.unescape(r.get('Title') or ''))
        nombre = urllib.parse.unquote(ref.rsplit('/', 1)[-1]).rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ')
        m = _NUM.search(titulo) or _NUM.search(nombre)
        if not m:
            continue
        tipo = TIPOS.get(C.fold(m.group(1)))
        url = COLAB + urllib.parse.quote(ref)
        if url in out or not tipo:
            continue
        f = C.fecha_larga(titulo)
        a = re.search(r'(20\d{2})', titulo or nombre)
        txt = C.pdf_texto(url, TXT / (hashlib.sha1(url.encode()).hexdigest()[:16] + '.txt'))
        o = _OBJETO.search(txt) or _ASUNTO.search(txt)
        desc = re.sub(r'\s+', ' ', o.group(1)).strip()[:600] if o else ''
        if re.search(r'[~\\|]', desc):        # capa de texto dañada: mejor el título
            desc = ''
        interna = 'interna' in C.fold(titulo + ' ' + nombre)
        out[url] = {'tipo': tipo[0], 'subtipo': tipo[1], 'numero': m.group(2), 'anio': (f[:4] or (a.group(1) if a else r['Modified'][:4])),
                    'fecha': f or r['Modified'][:10], 'titulo': titulo or f'{tipo[1]} {m.group(2)}', 'descripcion': desc or titulo,
                    'administrativo': interna or (bool(desc) and C.es_administrativo(desc)), 'url': url}
    return [x for x in out.values() if x['tipo'] != 'DECRETOS']


def _palabras(s):
    return {x for x in re.findall(r'[a-z0-9]{4,}', C.fold(s))
            if x not in ('proyecto', 'decreto', 'resolucion', 'cual', 'para', 'acuerdo', 'articulo', 'medio', 'sobre')}


def _en_sucop():
    """Títulos del DNP en SUCOP. Si S3 no responde se sigue sin filtrar: un repetido
    estorba menos que un proyecto perdido."""
    try:
        r = subprocess.run(['aws', 's3', 'cp', 's3://caudal-legislativo/metadata/sucop.jsonl', '-'],
                           capture_output=True, check=True, timeout=120)
        filas = [json.loads(x) for x in r.stdout.decode().splitlines()]
    except Exception as e:
        print(f'  dnp · no se leyó SUCOP ({e}): van todos', file=sys.stderr)
        return []
    return [p for p in (_palabras(x.get('titulo')) for x in filas if 'Planeaci' in (x.get('entidad') or '')) if p]


def _repetido(titulo, sucop):
    a = _palabras(titulo)
    return bool(a) and any(len(a & p) / len(a | p) >= .55 for p in sucop)


def proyectos(prev):
    h = C.curl(f'{WWW}/normativa/proyectos-de-normatividad', timeout=90)
    hoy = datetime.date.today().isoformat()
    vivos = {}
    for b in re.split(r'(?=El Departamento Nacional de Planeaci[oó]n,?\s+en\s+cumplimiento)', h)[1:]:
        t = C.limpio(html.unescape(b)).replace('​', '')
        m = re.search(r'publica el proyecto de ([A-Za-zÁÉÍÓÚáéíóú]+)\s*["“]?\s*(.+?)(?:["”]\s*,?\s*(?:para conocimiento|Lo anterior)|,?\s*para conocimiento|Lo anterior)', t)
        if not m:
            continue
        clase = m.group(1).capitalize()
        cuerpo = re.split(r'(?i)\s+(?:al correo|a los correos|a trav[eé]s del?|los comentarios)\b', m.group(2))[0]
        cuerpo = re.sub(r'\S+@\S+', ' ', cuerpo).strip(' “”"')       # los avisos traen correos de funcionarios
        titulo = f'Proyecto de {clase}: {cuerpo}'[:400]
        cola = t[m.end():]
        ini, fin = C.ventana(cola)
        links = [html.unescape(x).replace('&#58;', ':') for x in re.findall(r'href="([^"]+)"', b)]
        links = [x for x in links if x.lower().split('?')[0].endswith('.pdf') and 'colaboracion.dnp' in x]
        if not links:
            continue
        k = hashlib.sha1(titulo.encode()).hexdigest()[:16]
        if k not in vivos:
            vivos[k] = {'id': k, 'tipo_norma': f'Proyecto de {clase}', 'titulo': titulo, 'dependencia': '', 'fecha_inicio': ini,
                        'fecha_fin': fin, 'comentarios_a': '', 'url': links[0], 'anexos': links[1:4], 'creado': ini, 'visto': hoy,
                        'vigente_en_fuente': True}
    n = len(vivos)
    sucop = _en_sucop()
    vivos = {k: v for k, v in vivos.items() if not _repetido(v['titulo'], sucop)}
    out = {k: v for k, v in prev.items() if not _repetido(v['titulo'], sucop)}
    for k, v in out.items():
        if k not in vivos:
            v['vigente_en_fuente'] = False
    out.update(vivos)
    return out, n


def fetch():
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    ok = True
    try:
        prev = (C.leer(OUT / 'proyectos.json', {}) or {}).get('items', {})
        items, n = proyectos(prev)
        if not n:
            raise RuntimeError('ningún proyecto en la página')
        C.escribir(OUT / 'proyectos.json', {'generado': gen, 'items': items})
        print(f'  dnp · {n} proyectos en su página · {len(items)} que SUCOP no tiene')
    except Exception as e:
        ok = False
        print(f'  dnp · proyectos FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)
    try:
        xs = normas((C.leer(OUT / 'normas.json', {}) or {}).get('items', []))
        C.escribir(OUT / 'normas.json', {'generado': gen, 'items': xs})
        print(f'  dnp · {len(xs)} normas')
    except Exception as e:
        ok = False
        print(f'  dnp · normas FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('fetch')
    ap.parse_args()
    sys.exit(0 if fetch() else 1)


if __name__ == '__main__':
    main()
