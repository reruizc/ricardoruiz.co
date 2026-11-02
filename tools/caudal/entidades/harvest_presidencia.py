#!/usr/bin/env python3
"""
Caudal · Presidencia de la República: prensa y PDF de `dapre` (tanda 4, nov-2026).

⚠️⚠️ `dapre.presidencia.gov.co` va detrás de un F5/TSPD y su `robots.txt` prohíbe
`/*/Forms/`, `/*?` y `/_*`. Ahí están el listado de normativa (`Forms/AllItems.aspx`) y su
RSS (`_layouts/15/listfeed.aspx`): aunque respondan, NO se usan. Las páginas
`Paginas/decretos-*.aspx` devuelven el reto de F5. NO se evade nada. Lo que el `robots.txt`
sí deja es el PDF directo, `/normativa/normativa/<nombre>.pdf`.

  prensa   www.presidencia.gov.co/sitemap0.xml: las 500 URL más recientes de /prensa,
           ventana móvil de unos 50 días, por eso se acumulan
  pdf      el Diario Oficial dice qué se expidió (número y fecha); con eso se arma el
           nombre del archivo y se pide solo su cabecera. El nombre que no casa se
           vuelve a intentar unas corridas y luego se abandona

Salida en `Bases de datos/caudal-entidades/raw/presidencia/`:
  noticias.json  comunicados de prensa, en el formato de `comun.comunicado`
  normas.json    directivas, circulares y resoluciones ejecutivas de alcance general con PDF
  pdfs.json      PDF de los decretos y leyes. No van a normas: esas filas ya están en el
                 pilar Ejecutivo (Diario Oficial) y saldrían dos veces. Ver integrar/bloqueados.md

⚠️ El título de prensa sale de la dirección, sin tildes y a veces recortado. Cuando la
nota abre, se cambia por el real. Si no, queda marcado y lo dice en la descripción.
⚠️ `datos.gov.co` (88h2-dykw) está parado desde el 31-ago-2026: de ahí la falta de PDF.
⚠️ Lo administrativo (extradiciones, nombramientos) no se busca: pesa y no le sirve al radar.

Uso: python3 tools/caudal/entidades/harvest_presidencia.py fetch
"""
import argparse
import datetime
import html
import json
import re
import subprocess
import sys
import time
import urllib.parse

import comun as C

WWW = 'https://www.presidencia.gov.co'
DAPRE = 'https://dapre.presidencia.gov.co/normativa/normativa/'
OUT = C.RAW / 'presidencia'
DESDE_PDF = '2026-08-01'     # lo anterior ya trae su PDF desde datos.gov.co
PAUSA = 1.5
MINIMO = .7                  # una corrida por debajo del 70 % de la anterior no se publica
MAX_NOTAS = 60               # notas que se abren por corrida
MAX_SONDEOS = 140            # cabeceras de PDF que se piden por corrida
MAX_INTENTOS = 5             # corridas que se insiste en un PDF que no aparece
AVISO_TITULO = 'Título reconstruido desde la dirección web de la nota.'
_MES = {v: k.upper() for k, v in C.MESES.items() if k != 'setiembre'}


def _reto(h):
    """¿Es la página de reto del antibots y no la nota?"""
    return 'TSPD' in h[:6000] or 'window.location.replace' in h[:800] or len(h) < 8000


def reconstruir(slug):
    """Presidente-ordeno-el-traslado-261031.aspx → ('Presidente ordeno el traslado', '2026-10-31')."""
    s = urllib.parse.unquote(slug)
    s = re.sub(r'(?i)\.aspx$', '', s)
    m = re.search(r'-(\d{2})(\d{2})(\d{2})$', s)
    fecha = ''
    if m:
        try:
            fecha = datetime.date(2000 + int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
        except ValueError:
            pass
        s = s[:m.start()]
    s = re.sub(r'(\d+)-porciento\b', r'\1 %', s)
    s = re.sub(r'^Video-', 'Video: ', s)
    return C.limpio(s.replace('-', ' ')), fecha


def _nota_real(url):
    """(título, resumen) de la nota, o None si no abre o sale el reto."""
    time.sleep(PAUSA)
    try:
        h = C.curl(url, timeout=45, intentos=1)
    except RuntimeError:
        return None
    if _reto(h):
        return None
    m = re.search(r'<meta name="og:title"[^>]*content="([^"]+)"', h) or re.search(r'<title>(.*?)</title>', h, re.S)
    if not m:
        return None
    t = C.limpio(html.unescape(m.group(1)))
    cuerpo = re.search(r'id="ctl00_PlaceHolderMain[^"]*__ControlWrapper_RichHtmlField"[^>]*>(.*?)</div>', h, re.S)
    res = C.limpio(html.unescape(cuerpo.group(1)))[:400] if cuerpo else ''
    return t, res


def noticias(prev):
    x = C.curl(f'{WWW}/sitemap0.xml', timeout=60)
    if '<urlset' not in x:
        raise RuntimeError('el sitemap no respondió XML')
    filas = re.findall(r'<loc>(.*?)</loc>\s*<lastmod>(.*?)</lastmod>', x)
    out = {r['url']: r for r in prev}
    n, abiertas, cerrado = 0, 0, False
    for loc, lastmod in sorted(filas, key=lambda f: f[1], reverse=True):
        url = loc.replace(':443', '')
        if '/prensa/' not in url or not url.lower().endswith('.aspx'):
            continue
        n += 1
        ya = out.get(url)
        if ya and not ya.get('titulo_reconstruido'):
            continue
        titulo, fecha = reconstruir(url.rsplit('/', 1)[-1])
        fecha = fecha or lastmod[:10]
        real = None
        if not cerrado and abiertas < MAX_NOTAS:
            abiertas += 1
            real = _nota_real(url)
            cerrado = real is None           # se detiene: reintentar sería insistirle al antibots
        if real:
            r = C.comunicado(real[0], fecha, url, real[1])
            r.update(titulo_reconstruido=False, titulo_url=titulo)
        else:
            r = C.comunicado(titulo, fecha, url, AVISO_TITULO)
            r.update(titulo_reconstruido=True, titulo_url=titulo)
        out[url] = r
    return list(out.values()), n, cerrado


def _s3(clave):
    r = subprocess.run(['aws', 's3', 'cp', f's3://caudal-legislativo/metadata/{clave}', '-'],
                       capture_output=True, check=True, timeout=180)
    return [json.loads(x) for x in r.stdout.decode().splitlines() if x.strip()]


def _nombres(tipo, numero, fecha):
    """Los nombres de archivo que usa la Presidencia para un acto, del más común al raro."""
    a, m, d = fecha.split('-')
    mes, dd, n = _MES[int(m)], str(int(d)), str(int(numero))
    n4 = n.zfill(2)
    fechas = [f'DEL {dd} DE {mes} DE {a}'] + ([f'DEL {d} DE {mes} DE {a}'] if d != dd else [])
    if tipo == 'DECRETOS':
        return [f'DECRETO No. {n} {f}' for f in fechas] + [f'DECRETO {n.zfill(4)} {fechas[0]}']
    if tipo == 'LEYES':
        return [f'LEY No. {n} {f}' for f in fechas] + [f'LEY {n} {fechas[0]}']
    if tipo == 'DIRECTIVAS':
        return [f'DIRECTIVA PRESIDENCIAL No. {n4} {f}' for f in fechas] + [f'DIRECTIVA PRESIDENCIAL {n4} {fechas[0]}']
    if tipo == 'CIRCULARES':
        return [f'CIRCULAR EXTERNA No. {n4} DE {a}', f'CIRCULAR INTERNA No. {n4} DE {a}']
    return [f'RESOLUCIÓN EJECUTIVA {n} {f}' for f in fechas]


def _url(nombre):
    return DAPRE + urllib.parse.quote(nombre + '.pdf')


def _sondeo(url):
    """'pdf' · 'no' · 'cerrada'. Solo se pide la cabecera: 8 bytes bastan para saber."""
    time.sleep(PAUSA)
    r = subprocess.run(['/usr/bin/curl', '-s', '-L', '--max-time', '40', '-A', C.UA, '-r', '0-7', '-w', '\n%{http_code}', url],
                       capture_output=True, timeout=55)
    cuerpo, _, code = r.stdout.rpartition(b'\n')
    if cuerpo.startswith(b'%PDF'):
        return 'pdf'
    return 'no' if code in (b'404', b'400') else 'cerrada'


def candidatos(prev_pdfs):
    """Actos que ya están en el Diario Oficial y todavía no tienen PDF."""
    ya = prev_pdfs.get('items', {})
    sin = prev_pdfs.get('sin_pdf', {})
    out = []
    for r in _s3('normativa.jsonl'):
        if r.get('tipo') in ('DECRETOS', 'LEYES') and not r.get('url') and (r.get('fecha') or '') >= DESDE_PDF:
            out.append((r['tipo'], r['numero'], r['fecha'], r.get('descripcion') or ''))
    extra = []
    for r in _s3('diario-oficial-actos.jsonl'):
        if ('residencia' not in (r.get('entidad') or '') or (r.get('fecha') or '') < DESDE_PDF
                or r.get('fecha') > datetime.date.today().isoformat() or r.get('administrativo')):
            continue
        tipo = {'Directiva Presidencial': 'DIRECTIVAS', 'Circular': 'CIRCULARES', 'Circular Externa': 'CIRCULARES',
                'Resolución Ejecutiva': 'RESOLUCIONES'}.get(r.get('subtipo'))
        if tipo and re.fullmatch(r'\d+', str(r.get('numero'))):
            extra.append((tipo, r['numero'], r['fecha'], r.get('descripcion') or ''))
    pendientes = [c for c in out + extra if f'{c[0]}-{c[1]}-{c[2][:4]}' not in ya
                  and sin.get(f'{c[0]}-{c[1]}-{c[2][:4]}', 0) < MAX_INTENTOS]
    pendientes.sort(key=lambda c: c[2], reverse=True)
    return pendientes


def pdfs(prev):
    items = dict(prev.get('items', {}))
    sin = dict(prev.get('sin_pdf', {}))
    sondeos, hallados, cerrada = 0, 0, False
    for tipo, numero, fecha, desc in candidatos(prev):
        k = f'{tipo}-{numero}-{fecha[:4]}'
        hallado = None
        for nombre in _nombres(tipo, numero, fecha):
            if sondeos >= MAX_SONDEOS:
                break
            sondeos += 1
            u = _url(nombre)
            e = _sondeo(u)
            if e == 'pdf':
                hallado = u
                break
            if e == 'cerrada':
                cerrada = True
                break
        if cerrada or sondeos >= MAX_SONDEOS:
            break
        if hallado:
            hallados += 1
            items[k] = {'tipo': tipo, 'numero': str(int(numero)), 'anio': fecha[:4], 'fecha': fecha, 'url': hallado, 'descripcion': desc}
            sin.pop(k, None)
        else:
            sin[k] = sin.get(k, 0) + 1
    return items, sin, sondeos, hallados, cerrada


def normas(items):
    sub = {'DIRECTIVAS': 'Directiva Presidencial', 'CIRCULARES': 'Circular', 'RESOLUCIONES': 'Resolución Ejecutiva'}
    out = []
    for r in items.values():
        if r['tipo'] not in sub:
            continue
        titulo = f"{sub[r['tipo']]} {r['numero']} de {r['anio']}"
        out.append({'tipo': r['tipo'], 'subtipo': sub[r['tipo']], 'numero': r['numero'], 'anio': r['anio'], 'fecha': r['fecha'],
                    'titulo': titulo, 'descripcion': r['descripcion'] or titulo,
                    'administrativo': C.es_administrativo(r['descripcion']), 'url': r['url']})
    return out


def fetch():
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    ok = True
    try:
        prev = C.leer(OUT / 'noticias.json', {}) or {}
        xs, n, cerrado = noticias(prev.get('items', []))
        previos = prev.get('n_fuente') or 0
        if not n or (previos and n < previos * MINIMO):
            raise RuntimeError(f'{n} enlaces contra {previos} de la corrida anterior')
        C.escribir(OUT / 'noticias.json', {'generado': gen, 'n_fuente': n, 'items': xs})
        rec = sum(1 for x in xs if x.get('titulo_reconstruido'))
        print(f'  presidencia · {n} enlaces de prensa en el sitemap · {len(xs)} acumulados · {rec} con título reconstruido')
        if cerrado:
            print('  presidencia · una nota no abrió: se dejó de abrir por hoy, los títulos quedan reconstruidos', file=sys.stderr)
    except Exception as e:
        ok = False
        print(f'  presidencia · prensa FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)
    try:
        prev = C.leer(OUT / 'pdfs.json', {}) or {}
        items, sin, sondeos, hallados, cerrada = pdfs(prev)
        # guarda: la ruta directa dejó de servir aunque el Diario Oficial tenga actos nuevos
        if sondeos >= 10 and not hallados and not cerrada:
            raise RuntimeError(f'{sondeos} nombres probados y ningún PDF')
        if cerrada:
            print('  presidencia · dapre dejó de entregar el PDF directo: se detiene por hoy', file=sys.stderr)
            ok = False
        C.escribir(OUT / 'pdfs.json', {'generado': gen, 'items': items, 'sin_pdf': sin})
        ns = normas(items)
        C.escribir(OUT / 'normas.json', {'generado': gen, 'items': ns})
        print(f'  presidencia · {len(items)} PDF de dapre ({hallados} nuevos, {sondeos} sondeos) · {len(ns)} normas · '
              f'{len(sin)} sin PDF por ahora')
    except Exception as e:
        ok = False
        print(f'  presidencia · PDF FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('fetch')
    ap.parse_args()
    sys.exit(0 if fetch() else 1)


if __name__ == '__main__':
    main()
