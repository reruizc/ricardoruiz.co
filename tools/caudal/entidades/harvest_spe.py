#!/usr/bin/env python3
"""
Caudal · Unidad del Servicio Público de Empleo (tanda 1, oct-2026).

Su WordPress tiene la API abierta, pero no publica las normas como páginas: son
PDF sueltos en la biblioteca de medios, mezclados con hojas de vida, respuestas a
peticiones y formatos de talento humano.

  medios    /wp-json/wp/v2/media?mime_type=application/pdf  (desde 2025)
  noticias  /wp-json/wp/v2/posts

⚠️⚠️ El NOMBRE del archivo no se publica como texto: muchos terminan en el nombre
de quien lo subió y las respuestas a peticiones traen a personas particulares. Del
archivo solo se usa el tipo y el número. El objeto sale del PDF («Por la cual…»,
«ASUNTO:»). Lo que tenga cara de petición o de talento humano ni se baja.

Salida: `Bases de datos/caudal-entidades/raw/spe/{normas,noticias}.json`.
Uso: python3 tools/caudal/entidades/harvest_spe.py fetch
"""
import argparse
import datetime
import html
import json
import re
import sys

import comun as C

BASE = 'https://www.serviciodeempleo.gov.co'
OUT = C.RAW / 'spe'
TXT = OUT / 'txt'
DESDE = '2025-01-01T00:00:00'
# ni siquiera se abren: peticiones, hojas de vida y formatos internos
_FUERA = re.compile(r'(?i)petici|respue|radicado|^(th|gf|gbs|gd|hv)[-_]|hoja.de.vida|sigep|declaraci|conflicto|'
                    r'aceptaci|postulad|ampliaci|listado|encargo|comisiones?.de.servicio|vacaciones')
_ACTO = re.compile(r'(?i)^(?:\d+\.\s*)?(resoluci[oó]n|res|circular)\b[-_. ]*(?:no\.?|n[°º])?[-_. ]*0*(\d{1,5})')
_ACTO_PEGADO = re.compile(r'(?i)^(resolucion)0*(\d{2,5})')
_ANIO = re.compile(r'(20\d{2})')
_OBJETO = re.compile(r'(?is)((?:por\s+(?:la|el|medio\s+de\s+la)\s+cual|por\s+medio\s+del?\s+cual)\b.+?)(?:\n\s*\n|\bCONSIDERANDO\b|\bLA\s+DIRECTORA?\b|\bEL\s+DIRECTOR\b)')
_ASUNTO = re.compile(r'(?is)\b(?:ASUNTO|REFERENCIA)\s*:\s*(.+?)(?:\n\s*\n|Respetad|Cordial|Apreciad)')


def medios():
    out, pag = [], 1
    while True:
        u = (f'{BASE}/wp-json/wp/v2/media?mime_type=application/pdf&per_page=100&page={pag}'
             f'&after={DESDE}&orderby=date&order=desc&_fields=id,date,source_url')
        try:
            filas = json.loads(C.curl(u, timeout=90, intentos=2))
        except RuntimeError:
            break                        # WordPress responde 400 al pasarse de la última página
        out += filas
        if len(filas) < 100:
            break
        pag += 1
    return out


def es_acto(nombre):
    n = nombre.replace('.pdf', '').replace('.PDF', '')
    if _FUERA.search(n):
        return None
    m = _ACTO.match(n) or _ACTO_PEGADO.match(n)
    if not m:
        return None
    return ('CIRCULARES', 'Circular') if m.group(1).lower().startswith('c') else ('RESOLUCIONES', 'Resolución'), m.group(2)


def objeto(texto):
    t = re.sub(r'[ \t]+', ' ', texto or '')
    m = _OBJETO.search(t) or _ASUNTO.search(t)
    return C.limpio(m.group(1)).rstrip(' .–-')[:500] if m else ''


def normas():
    out = {}
    for r in medios():
        url = r['source_url']
        nombre = url.rsplit('/', 1)[-1]
        a = es_acto(nombre)
        if not a:
            continue
        (tipo, subtipo), num = a
        anio = (_ANIO.search(nombre) or [None, r['date'][:4]])[1]
        try:
            texto = C.pdf_texto(url, TXT / f"{r['id']}.txt", paginas=1)
        except Exception as e:
            print(f'  ! spe · {r["id"]}: {e}', file=sys.stderr)
            texto = ''
        desc = objeto(texto)
        titulo = f'{subtipo} {num.lstrip("0") or "0"} de {anio}'
        k = f'{tipo}-{num}-{anio}'
        if k in out and not desc:
            continue
        out[k] = {'tipo': tipo, 'subtipo': subtipo, 'numero': num.lstrip('0') or '0', 'anio': anio,
                  'fecha': r['date'][:10], 'titulo': titulo, 'descripcion': desc or titulo,
                  'administrativo': not desc or C.es_administrativo(desc), 'url': url}
    return list(out.values())


def noticias(prev):
    out = {x['url']: x for x in prev}
    for r in json.loads(C.curl(f'{BASE}/wp-json/wp/v2/posts?per_page=50&after={DESDE}&_fields=date,link,title,excerpt', timeout=90)):
        out[r['link']] = C.comunicado(C.limpio(html.unescape(r['title']['rendered'])), r['date'][:10], r['link'],
                                      C.limpio(html.unescape(r['excerpt']['rendered']))[:400])
    return list(out.values())


def fetch():
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    ok = True
    try:
        ns = normas()
        if not ns:
            raise RuntimeError('ningún acto entre los PDF')
        C.escribir(OUT / 'normas.json', {'generado': gen, 'items': ns})
        print(f'  spe · {len(ns)} resoluciones y circulares ({sum(1 for n in ns if not n["administrativo"])} con objeto general)')
    except Exception as e:
        ok = False
        print(f'  spe · normas FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)
    try:
        prev = (C.leer(OUT / 'noticias.json', {}) or {}).get('items', [])
        xs = noticias(prev)
        C.escribir(OUT / 'noticias.json', {'generado': gen, 'items': xs})
        print(f'  spe · {len(xs)} noticias')
    except Exception as e:
        ok = False
        print(f'  spe · noticias FALLÓ ({e})', file=sys.stderr)
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('fetch')
    if ap.parse_args().cmd == 'fetch':
        sys.exit(0 if fetch() else 1)


if __name__ == '__main__':
    main()
