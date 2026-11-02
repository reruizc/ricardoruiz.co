#!/usr/bin/env python3
"""
Caudal · Ministerio de las Culturas, las Artes y los Saberes (tanda 3, nov-2026).

  noticias       /noticias/_api/web/lists/getbytitle('Páginas')/items   (SharePoint anónimo)
  convocatorias  sistemaconvocatorias.mincultura.gov.co/avisosinformativos?page=N  (20 por página)

⚠️ Sin `$orderby=Created desc` la lista de SharePoint sale desordenada.
⚠️ `Created` va en UTC: la fecha de la nota es `notaCiudadFecha` («3-08-2026»).
⚠️ `Visible=false` NO es «despublicada»: el sitio muestra esas notas (87). No se filtra por ese campo.
⚠️ Las novedades de convocatorias no traen enlace estable: el PDF va por una URL de Azure con
firma, y `build.py` decodifica las URL, así que la firma se daña y da 403. Se enlaza la
página de avisos.
⚠️⚠️ La misma lista publica tutelas por orden judicial, con el nombre de quien la interpone
en el rótulo: no entran, ni se guarda su texto (`_FUERA`). También hay convocatorias de prueba del propio sistema («test 5», «Beca de prueba Z»): no entran.
⚠️ La lista entera son 70 avisos en 4 páginas: se lee toda cada día.
⚠️ Sus resoluciones de 2026 no están en el sitio y no publica conceptos: lo expedido sigue
llegando por el Diario Oficial. SUCOP ya trae sus borradores.

Salida: `Bases de datos/caudal-entidades/raw/mincultura/noticias.json`.
Uso: python3 tools/caudal/entidades/harvest_mincultura.py fetch
"""
import argparse
import datetime
import hashlib
import html
import json
import re
import sys

import comun as C

BASE = 'https://www.mincultura.gov.co'
AVISOS = 'https://sistemaconvocatorias.mincultura.gov.co/avisosinformativos'
OUT = C.RAW / 'mincultura'
DESDE = '2025-01-01'
CAIDA = .5          # una corrida con menos de la mitad de la anterior no se publica
TOPE = 40           # páginas: evita un bucle si la paginación se enreda
_FUERA = re.compile(r'(?i)\btutela\b|\bjuzgado\b|\bauto admisorio\b|cendoj|\bdesacato\b|\bse[nñ]or(?:a)?\b')
_PRUEBA = re.compile(r'(?i)\b(?:test|prueba|convocatoria \d+)\b')
_CORREO = re.compile(r'\S+@\S+')


def _guarda(nombre, leidos, previo):
    """Mide lo que dio la fuente, no lo acumulado: si cae a menos de la mitad
    de la corrida anterior, o a cero, se conserva el archivo que había."""
    antes = (previo or {}).get(nombre) or 0
    if not leidos or leidos < antes * CAIDA:
        raise RuntimeError(f'guarda: {nombre} trae {leidos} contra {antes} de la corrida anterior')


def noticias(prev):
    """Las notas publicadas, de la más nueva a la más vieja."""
    u = (f"{BASE}/noticias/_api/web/lists/getbytitle('P%C3%A1ginas')/items"
         "?$select=Id,Title,Created,FileRef,Resumen,notaCiudadFecha&$orderby=Created%20desc&$top=2000")
    filas = json.loads(C.curl(u, accept='application/json;odata=nometadata', timeout=120))['value']
    _guarda('leidos_noticias', len(filas), prev)
    out = {}
    for r in filas:
        titulo = C.limpio(html.unescape(r.get('Title') or ''))
        m = re.fullmatch(r'(\d{1,2})-(\d{1,2})-(\d{4})', (r.get('notaCiudadFecha') or '').strip())
        creada = (r.get('Created') or '')[:19]
        if m:
            fecha = f'{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}'
        elif creada:             # UTC: las 2 a. m. del 3 son las 9 p. m. del 2 en Bogotá
            fecha = (datetime.datetime.fromisoformat(creada) - datetime.timedelta(hours=5)).date().isoformat()
        else:
            fecha = ''
        if not titulo or fecha < DESDE:
            continue
        url = BASE + r['FileRef']
        out[url] = C.comunicado(titulo, fecha, url, C.limpio(html.unescape(r.get('Resumen') or '')))
    return out, len(filas)


def _columnas(b):
    """Las cuatro columnas de una fila: número, convocatoria y rótulo, texto y fecha."""
    partes = re.split(r'!w-full md:!w-\[(?:5|25|50|20)%\]', b)
    return partes[1:] if len(partes) >= 5 else None


def _aviso(b):
    c = _columnas(b)
    if not c:
        return None
    spans = [C.limpio(html.unescape(x)) for x in re.findall(r'<span[^>]*>(.*?)</span>', c[1], re.S)]
    spans = [x for x in spans if x]
    cuerpo = C.limpio(html.unescape(c[2].split('>', 1)[-1]))
    fecha = C.fecha_larga(C.limpio(c[3].split('>', 1)[-1]))
    return {'nombres': spans[:-1], 'rotulo': spans[-1] if spans else '', 'cuerpo': cuerpo, 'fecha': fecha}


def convocatorias(prev):
    anteriores = {x['url']: x for x in prev.get('items', []) if x.get('subtipo') == 'Aviso de convocatoria'}
    hoy = datetime.date.today().isoformat()
    out, leidos, fuera = {}, 0, 0
    for n in range(1, TOPE):
        h = re.sub(r'<(script|style|svg)[^>]*>.*?</\1>', '', C.curl(f'{AVISOS}?page={n}', timeout=90), flags=re.S)
        h = re.sub(r'base64,[^"]+', '', h)
        filas = re.split(r'(?=<(?:a|div)\s[^>]*class="!block !bg-gray-100)', h)[1:]
        if not filas:
            break
        leidos += len(filas)
        for b in filas:
            a = _aviso(b)
            if not a:
                continue
            texto = ' '.join(a['nombres'] + [a['rotulo'], a['cuerpo']])
            if _FUERA.search(texto) or any(_PRUEBA.search(x) for x in a['nombres']) or (a['fecha'] and a['fecha'] < DESDE):
                fuera += 1
                continue
            conv = a['nombres'][0] if a['nombres'] else 'Convocatorias'
            titulo = f"{a['rotulo'] or 'Aviso informativo'} · {conv}"[:300]
            k = hashlib.sha1(f"{titulo}|{a['fecha']}|{a['cuerpo'][:120]}".encode()).hexdigest()[:16]
            resumen = _CORREO.sub('', a['cuerpo'])[:400]
            url = f'{AVISOS}#aviso-{k}'          # sin ancla, todas las novedades tendrían la misma URL
            out[url] = {**C.comunicado(titulo, a['fecha'] or hoy, url, resumen), 'subtipo': 'Aviso de convocatoria'}
    _guarda('leidos_avisos', leidos, prev)
    return {**anteriores, **out}, leidos, fuera


def fetch():
    OUT.mkdir(parents=True, exist_ok=True)
    prev = C.leer(OUT / 'noticias.json', {}) or {}
    vieja = {x['url']: x for x in prev.get('items', [])}
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    ok = True
    notas = {u: x for u, x in vieja.items() if x.get('subtipo') != 'Aviso de convocatoria'}
    avisos = {u: x for u, x in vieja.items() if x.get('subtipo') == 'Aviso de convocatoria'}
    conteos = {k: prev.get(k) or 0 for k in ('leidos_noticias', 'leidos_avisos')}
    try:
        nuevas, n = noticias(prev)
        notas.update(nuevas)
        conteos['leidos_noticias'] = n
        print(f'  mincultura · noticias: {n} en SharePoint · {len(notas)} desde {DESDE}')
    except Exception as e:
        ok = False
        print(f'  mincultura · noticias FALLÓ ({e}) — quedan las anteriores', file=sys.stderr)
    try:
        avisos, n, fuera = convocatorias(prev)
        conteos['leidos_avisos'] = n
        print(f'  mincultura · convocatorias: {n} avisos en la lista · {len(avisos)} quedan · {fuera} fuera (tutelas, pruebas o viejos)')
    except Exception as e:
        ok = False
        print(f'  mincultura · convocatorias FALLÓ ({e}) — quedan las anteriores', file=sys.stderr)
    if notas or avisos:
        C.escribir(OUT / 'noticias.json', {'generado': gen, **conteos, 'items': list(notas.values()) + list(avisos.values())})
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('fetch')
    ap.parse_args()
    sys.exit(0 if fetch() else 1)


if __name__ == '__main__':
    main()
