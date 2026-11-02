#!/usr/bin/env python3
"""
Caudal · Ministerio del Deporte (tanda 3, nov-2026).

  proyectos     .../2-1-normatividad/consulta-publica-de-proyectos-normativos/AAAA + ficha de cada uno
  resoluciones  .../2-1-normatividad/normatividad-general-y-reglamentaria/resoluciones/AAAA  (50 por página)
  convocatorias /mindeporte/convocatorias + noticias con «convocatoria» en la ruta (sitemap)

⚠️ Desde 2025 no publica borradores en SUCOP (allí quedan 5 viejos). La ventana no está en la lista: va en la ficha, y ahí
hay dos «Fecha de publicación»; la de la consulta es la que viene en palabras («2 de febrero de
2026»), la otra, en dd/mm/aaaa, es la de las respuestas.
⚠️ La lista de un año que aún no existe da 404: en enero se sigue con la del año anterior.
⚠️ La página de convocatorias no se toca desde el 18-feb-2025: dos circulares y un enlace a
una ficha fija. Además se miran las noticias con «convocatoria» en la ruta (hoy ninguna en
`noticias-mindeporte`; las de `archivo-noticias` son históricas). `lastmod` del sitemap es de la
migración del sitio y no sirve para ordenar.
⚠️ La agenda regulatoria es de la línea de agendas 2027: no se lee acá.

Salida: `Bases de datos/caudal-entidades/raw/mindeporte/{proyectos,normas,noticias}.json`.
Uso: python3 tools/caudal/entidades/harvest_mindeporte.py fetch
"""
import argparse
import datetime
import hashlib
import html
import re
import sys
import urllib.parse

import comun as C

BASE = 'https://www.mindeporte.gov.co'
RAIZ = f'{BASE}/transparencia-y-acceso-a-informacion-publica/2-normativa/2-1-normatividad'
OUT = C.RAW / 'mindeporte'
TXT = OUT / 'txt'
CAIDA = .5          # una corrida con menos de la mitad de la anterior no se publica
MAX_PDF = 15        # PDF nuevos por corrida
_F = r'(\d{1,2}\s+de\s+[a-záéíóú]+\s+(?:de\s+|del\s+)?\d{4})'
_PUB = re.compile(rf'(?i)fecha de publicaci[oó]n[^:]{{0,30}}:\s*{_F}')
_PLAZO = re.compile(rf'(?i)plazo[^:.]{{0,60}}:\s*(?:hasta el\s+)?{_F}')
_OBJETO = re.compile(r'(?is)((?:por\s+(?:la|el|medio\s+de\s+la|medio\s+del)\s+cual)\b.+?)(?:\n\s*\n|\bCONSIDERANDO\b|\bEL\s+MINISTR|\bLA\s+MINISTR|\bEL\s+DIRECTOR\b)')
# 8 de cada 10 de 2025 pagan sentencias o conciliaciones: se marcan, no se borran
_PARTICULAR = re.compile(r'(?i)ordena (?:el|un) pago|providencia judicial|acuerdo conciliatorio|cumplimiento a (?:un|una) (?:fallo|sentencia)')
_MES_DIA = re.compile(r'([a-záéíóú]+)\s+(\d{1,2})\s+de\s+(\d{4})')


def _guarda(nombre, leidos, previo):
    """Mide lo que dio la fuente, no lo acumulado: si cae a menos de la mitad
    de la corrida anterior, o a cero, se conserva el archivo que había."""
    antes = (previo or {}).get('leidos') or 0
    if not leidos or leidos < antes * CAIDA:
        raise RuntimeError(f'guarda: {nombre} trae {leidos} contra {antes} de la corrida anterior')


def _txt(frag):
    return C.limpio(html.unescape(frag))


def _abs(u):
    return u if u.startswith('http') else BASE + (u if u.startswith('/') else '/' + u)


def _anios():
    a = datetime.date.today().year
    return a - 1, a


def _tarjetas(url):
    """Todas las tarjetas de un listado: enlace, título, subtítulo, fecha y primer PDF."""
    out, n = [], 1
    while True:
        h = C.curl(url + (f'?page={n}' if n > 1 else ''), timeout=90)
        for a in re.findall(r'<article.*?</article>', h, re.S):
            m = re.search(r'<a href="([^"]+)"[^>]*>\s*<p class="text-base[^>]*>(.*?)</p>(.*?)<p class="mt-1 text-xs text-gray-400">([^<]*)</p>', a, re.S)
            if not m:
                continue
            pdf = re.search(r'href="([^"]+\.pdf)"', a)
            out.append({'href': _abs(html.unescape(m.group(1))), 'titulo': _txt(m.group(2)), 'sub': _txt(m.group(3)).strip(' "“”.'),
                        'dia': _txt(m.group(4)), 'pdf': _abs(html.unescape(pdf.group(1))) if pdf else ''})
        n += 1
        if f'page={n}' not in h:
            return out


def _listas(ruta):
    """Las tarjetas del año pasado y del actual, que puede no existir todavía."""
    pasado, actual = _anios()
    out = []
    for a in (pasado, actual):
        try:
            out += [{**t, 'anio': str(a)} for t in _tarjetas(f'{RAIZ}/{ruta}/{a}')]
        except RuntimeError as e:
            if a != actual or 'http=404' not in str(e):
                raise
            print(f'  mindeporte · {ruta}/{a} aún no existe', file=sys.stderr)
    return out


def _dia(s):
    """«viernes, julio 24 de 2026» → ISO."""
    m = _MES_DIA.search((s or '').lower())
    return C.fecha_larga(f'{m.group(2)} de {m.group(1)} de {m.group(3)}') if m else ''


def _clase(t):
    t = C.fold(t)
    for k, v in (('decreto', 'Proyecto de Decreto'), ('resolucion', 'Proyecto de Resolución'), ('circular', 'Proyecto de Circular')):
        if k in t:
            return v
    return 'Documento en consulta'


def _ficha(t, hoy):
    h = re.sub(r'<(script|style|svg)[^>]*>.*?</\1>', '', C.curl(t['href'], timeout=90), flags=re.S)
    texto = C.limpio(html.unescape(h))
    pub, plazo = _PUB.search(texto), _PLAZO.search(texto)
    ini = C.fecha_larga(pub.group(1)) if pub else ''
    fin = C.fecha_larga(plazo.group(1)) if plazo else ''
    docs = [_abs(html.unescape(u)) for u in dict.fromkeys(re.findall(r'href="([^"]*/files/[^"]+\.(?:pdf|docx?|xlsx?|zip))"', h))]
    utiles = [d for d in docs if not re.search(r'(?i)respuesta|memoria', d.rsplit('/', 1)[-1])]   # el cierre deja las respuestas de primeras
    doc = next((d for d in utiles if re.search(r'(?i)proyecto|borrador', d.rsplit('/', 1)[-1])), utiles[0] if utiles else '')
    resp = re.search(r'Responsable:\s*(.+?)\.', texto)
    titulo = re.sub(r'(?i)^consulta p[uú]blica:\s*', '', t['titulo']).strip()
    titulo = titulo[:1].upper() + titulo[1:]
    return {'id': hashlib.sha1(t['href'].encode()).hexdigest()[:16], 'tipo_norma': _clase(titulo), 'titulo': titulo[:400],
            'dependencia': resp.group(1)[:120] if resp else '', 'fecha_inicio': ini, 'fecha_fin': fin, 'comentarios_a': '',
            'url': doc or t['href'], 'anexos': [d for d in docs if d != doc][:4], 'creado': ini or _dia(t['dia']), 'visto': hoy,
            'vigente_en_fuente': True, 'pagina': t['href']}


def proyectos(prev):
    tarjetas = [t for t in _listas('consulta-publica-de-proyectos-normativos') if 'agenda regulatoria' not in C.fold(t['titulo'])]
    _guarda('proyectos', len(tarjetas), prev)
    hoy = datetime.date.today().isoformat()
    vivos = {}
    for t in tarjetas:
        f = _ficha(t, hoy)
        vivos[f['id']] = f
    out = dict(prev.get('items', {}))
    for k, v in out.items():
        if k not in vivos:
            v['vigente_en_fuente'] = False
    out.update(vivos)
    return out, len(tarjetas)


def _objeto(url, cupo):
    """Epígrafe del PDF cuando la tarjeta no lo trae (6 de cada 10 en 2025); una sola
    vez. Cada PDF tarda ~9 s: `cupo` limita los nuevos por corrida para no agotar la etapa."""
    if not url.lower().endswith('.pdf'):
        return ''
    cache = TXT / (hashlib.sha1(url.encode()).hexdigest()[:16] + '.txt')
    if not cache.exists():
        if not cupo[0]:
            return ''
        cupo[0] -= 1
    try:
        txt = C.pdf_texto(url, cache)
    except Exception:
        return ''
    o = _OBJETO.search(txt)
    return re.sub(r'\s+', ' ', o.group(1)).strip(' "“”')[:600] if o else ''


def normas(prev):
    previas = {x['url']: x for x in prev.get('items', [])}
    tarjetas = _listas('normatividad-general-y-reglamentaria/resoluciones')
    _guarda('resoluciones', len(tarjetas), prev)
    cupo = [MAX_PDF]
    for t in tarjetas:
        n = re.search(r'(?i)resoluci[oó]n\s*(?:no\.?\s*)?0*(\d+)', t['titulo'])
        url = t['pdf'] or t['href']
        vieja = (previas.get(url) or {}).get('descripcion')
        desc = t['sub'] or (vieja if vieja and vieja != t['titulo'] else _objeto(url, cupo)) or t['titulo']
        fecha = C.fecha_larga(t['titulo']) or _dia(t['dia'])
        previas[url] = {'tipo': 'RESOLUCIONES', 'subtipo': 'Resolución', 'numero': n.group(1) if n else '',
                        'anio': fecha[:4] or t['anio'], 'fecha': fecha, 'titulo': t['titulo'], 'descripcion': desc,
                        'administrativo': desc == t['titulo'] or C.es_administrativo(desc) or bool(_PARTICULAR.search(desc)), 'url': url}
    return list(previas.values()), len(tarjetas)


def _noticia(url):
    h = C.curl(url, timeout=90)
    t = re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S)
    d = re.search(r'Última actualización:\s*([^<]+)', h)
    return _txt(t.group(1)) if t else '', _dia(d.group(1)) if d else ''


def convocatorias(prev):
    out = {x['url']: x for x in prev.get('items', [])}
    pag = f'{BASE}/mindeporte/convocatorias'
    h = C.curl(pag, timeout=90)
    act = re.search(r'Última actualización:\s*([^<]+)', h)
    fecha = _dia(act.group(1)) if act else ''
    leidos = 0
    docs = dict.fromkeys(re.findall(r'href="(https://www\.mindeporte\.gov\.co/files/[^"]+\.pdf)"', h))
    for u in docs:
        leidos += 1
        nombre = urllib.parse.unquote(u.rsplit('/', 1)[-1]).rsplit('.', 1)[0].replace('-', ' ')
        out[u] = {**C.comunicado(nombre, fecha, u), 'subtipo': 'Convocatoria'}
    sm = C.curl(f'{BASE}/sitemap.xml', timeout=120)
    rutas = dict.fromkeys(re.findall(r'<loc>(https://www\.mindeporte\.gov\.co/sala-de-prensa/noticias-mindeporte/[^<]*convoca[^<]*)</loc>', sm))
    leidos += len(rutas)
    _guarda('convocatorias', leidos, prev)
    for u in rutas:
        if u in out:
            continue
        titulo, dia = _noticia(u)
        if titulo:
            out[u] = {**C.comunicado(titulo, dia, u), 'subtipo': 'Convocatoria'}
    return list(out.values()), leidos


def fetch():
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    hoy = datetime.date.today().isoformat()
    ok = True

    def etapa(nombre, archivo, fn, resumen):
        nonlocal ok
        try:
            xs, leidos = fn(C.leer(OUT / archivo, {}) or {})
            C.escribir(OUT / archivo, {'generado': gen, 'leidos': leidos, 'items': xs})
            print(f'  mindeporte · {nombre}: {resumen(xs, leidos)}')
        except Exception as e:
            ok = False
            print(f'  mindeporte · {nombre} FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)

    etapa('proyectos', 'proyectos.json', proyectos,
          lambda xs, n: f"{n} leídos · {sum(1 for v in xs.values() if v['fecha_fin'] >= hoy)} abiertos · "
                        f"{sum(1 for v in xs.values() if not v['fecha_fin'])} sin ventana")
    etapa('resoluciones', 'normas.json', normas, lambda xs, n: f'{n} leídas · {len(xs)} acumuladas')
    etapa('convocatorias', 'noticias.json', convocatorias, lambda xs, n: f'{n} enlaces · {len(xs)} acumuladas')
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('fetch')
    ap.parse_args()
    sys.exit(0 if fetch() else 1)


if __name__ == '__main__':
    main()
