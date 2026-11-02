#!/usr/bin/env python3
"""
Caudal · Alcaldía de Medellín · decretos, resoluciones y circulares por la Gaceta
Oficial (tanda 5, nov-2026).

La página pública es un iframe a una aplicación Laravel sin login, que tiene dos
archivos separados en el 28-ago-2026:

  /statements/innovaciondigital/gacetas/
    consulta-publica?page=N     gacetas desde el 28-ago-2026, de a 15
    consulta-publica/{gaceta}   ficha: acto · tipo · objeto · fecha · dependencia
    consulta-publica/{id}/descargar/pdf   ⚠️ el id NO es el número de gaceta
    historico-mercurio?year=AAAA&page=N   un acto por fila, de a 15, ya congelado
    historico-mercurio/descargar/{doc}    PDF de la gaceta

⚠️ Tres cosas de la ficha, medidas el 1-nov-2026 contra los PDF:
  - 192 de 347 actos traen de objeto «Publicación gaceta oficial decreto N»: el
    título de verdad solo está en el cuerpo del PDF, y de ahí se saca.
  - Un número puede venir cortado (ficha MED_2026_40_00012, documento
    MED_2026_40_000125): los MED_ con menos de 6 dígitos se corrigen con el PDF.
  - La gaceta 5969 tiene ficha y PDF, pero no sale en el listado y dice «Fecha de
    Generación» en vez de «Fecha de Publicación». Se guarda con `listada: false` y
    sus actos no se publican hasta que aparezca.

Más de la mitad de los actos son movimientos presupuestales: se marcan `rutinario`.
La gaceta trae también actos de otras entidades (EPM, Área Metropolitana, ITM) y
acuerdos del Concejo. Se guarda la dependencia que da la ficha; el histórico no la trae.

Salida: `Bases de datos/caudal-entidades/raw/alcaldia-medellin/{gacetas,historico,normas}.json`.
Uso: python3 tools/caudal/entidades/harvest_alcaldia.py fetch [--historico] [--max 20]
"""
import argparse
import datetime
import html
import re
import sys
import tempfile

import comun as C
from harvest_gobernacion import paginas, particular

ENTIDAD = 'Alcaldía de Medellín'
BASE = 'https://www.medellin.gov.co/statements/innovaciondigital/gacetas'
OUT = C.RAW / 'alcaldia-medellin'
_RELLENO = re.compile(r'(?i)^\W*publicaci[óo]n\s+(?:de\s+)?(?:la\s+)?gaceta')
_MED = re.compile(r'MED[\s_]*(\d{4})[\s_]*(\d{2})[\s_]*(\d{5,7})')
_POR = re.compile(r'(?i)\bPor\s+(?:medio\s+de(?:l|\s+la)\s+|(?:la|el)\s+)cual\b')
_FIN = re.compile(r'(?m)^\s*(?:(?:EL|LA)\s+(?:ALCALDE|ALCALDESA|SECRETARI|SUBSECRETARI|DIRECTOR|GERENTE|CONCEJO|JUNTA|CONSEJO)|'
                  r'En uso de|CONSIDERANDO)')
_PRESUPUESTO = re.compile(r'(?i)\bunos?\s+(?:adiciones|modificaciones|traslados|reducciones)\b|'
                         r'\bunas\s+(?:adiciones|modificaciones|reducciones)\s+presupuestales')
_INDICE = re.compile(r'\.{6,}|c{6,}|CONTENIDO')


def _txt(s):
    return C.limpio(html.unescape(html.unescape(re.sub(r'<[^>]+>', ' ', s or ''))))


def _iso(s):
    m = re.search(r'(\d{2})/(\d{2})/(\d{4})', s or '')
    return f'{m.group(3)}-{m.group(2)}-{m.group(1)}' if m else ''


def _epigrafe(s):
    s = s.strip(' ."“”\'”“')
    return s[:1].upper() + s[1:].lower() if s.isupper() else s


def clase(tipo):
    t = C.fold(tipo)
    for pre, c, k in (('decreto', 'Decreto', 'DECRETOS'), ('resoluci', 'Resolución', 'RESOLUCIONES'),
                      ('circular', 'Circular', 'CIRCULARES'), ('acuerdo', 'Acuerdo', 'ACUERDOS')):
        if t.startswith(pre):
            return c, k
    return (tipo or 'Otro').capitalize(), 'OTROS'


def listado():
    """{gaceta: (fecha ISO, id del PDF)} del sistema nuevo."""
    out, p = {}, 1
    while p < 200:
        h = C.curl(f'{BASE}/consulta-publica?page={p}', timeout=60)
        filas = re.findall(r'badge bg-primary">(\d+)</span>.*?<td>[^<]*</td>\s*<td>([\d/]+)</td>.*?consulta-publica/(\d+)/descargar',
                           h, re.S)
        if not filas:
            break
        for n, f, i in filas:
            out[n] = (_iso(f), i)
        p += 1
    return out


def ficha(n):
    """Ficha de una gaceta; None si no existe."""
    try:
        h = C.curl(f'{BASE}/consulta-publica/{n}', timeout=60, intentos=2)
    except RuntimeError as e:
        if 'http=404' in str(e):
            return None
        raise
    h = re.sub(r'<style.*?</style>|<script.*?</script>', '', h, flags=re.S)
    f = re.search(r'Fecha de (Publicación|Generación):</strong>\s*([\d/]+)', h)
    pid = re.search(r'consulta-publica/(\d+)/descargar', h)
    t = h[h.find('Actos Administrativos Incluidos'):]
    actos = []
    for r in re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S)[1:]:
        c = [_txt(x) for x in re.findall(r'<td[^>]*>(.*?)</td>', r, re.S)]
        if len(c) >= 5:
            actos.append({'numero': c[0], 'tipo': c[1], 'objeto': c[2].strip(' "“”'), 'fecha': _iso(c[3]),
                          'dependencia': c[4]})
    return {'gaceta': n, 'fecha': _iso(f.group(2)) if f else '', 'listada': bool(f and f.group(1) == 'Publicación'),
            'id_pdf': pid.group(1) if pid else '', 'actos': actos, 'pdf_leido': False}


def _sospechoso(a):
    """Objeto de relleno, o número MED_ cortado."""
    m = _MED.search(a['numero'])
    return bool(_RELLENO.search(a['objeto'])) or not a['objeto'] or bool(m and len(m.group(3)) < 6)


def _pagina_del_acto(pp, numero):
    m = _MED.search(numero)
    if m:
        pat = rf'MED[\s_]*{m.group(1)}[\s_]*{m.group(2)}[\s_]*{m.group(3)}'
    else:
        pat = r'(?<!\d)0*' + re.escape(numero.lstrip('0') or numero) + r'(?!\d)'
    rx = re.compile(rf'(?im)^.{{0,20}}(?:DECRETO|RESOLUCI[ÓO]N|CIRCULAR|ACUERDO)\b[^\n]{{0,30}}{pat}')
    for t in pp:
        if not _INDICE.search(t[:400]) and not _INDICE.search(t) and rx.search(t):
            return t
    return ''


def completar_con_pdf(g):
    """Corrige con el cuerpo del PDF los títulos de relleno y los números cortados."""
    with tempfile.NamedTemporaryFile(suffix='.pdf') as tmp:
        C.curl(f"{BASE}/consulta-publica/{g['id_pdf']}/descargar/pdf", salida=tmp.name, timeout=240)
        pp = paginas(tmp.name)
    completo = ' '.join(pp)
    for a in g['actos']:
        if not _sospechoso(a):
            continue
        m = _MED.search(a['numero'])
        if m and len(m.group(3)) < 6:
            cands = {x.group(3) for x in _MED.finditer(completo) if x.group(3).startswith(m.group(3)) and len(x.group(3)) >= 6}
            if len(cands) == 1:
                a['numero_ficha'] = a['numero']
                a['numero'] = f'MED_{m.group(1)}_{m.group(2)}_{cands.pop()}'
        if _RELLENO.search(a['objeto']) or not a['objeto']:
            t = _pagina_del_acto(pp, a['numero'])
            p = _POR.search(t)
            if p:
                f = _FIN.search(t, p.end())
                a['objeto'] = _epigrafe(C.limpio(t[p.start():f.start() if f else p.start() + 400])[:500])
                a['titulo_de_pdf'] = True
    g['pdf_leido'] = True


def historico(anio):
    """Actos del archivo viejo, por año. Una fila por acto; el doc es la gaceta."""
    out, p, total = [], 1, None
    while p < 400:
        h = C.curl(f'{BASE}/historico-mercurio?year={anio}&page={p}', timeout=60)
        if total is None:
            m = re.search(r'de\s*<span[^>]*>(\d+)</span>\s*Resultados', h)
            total = int(m.group(1)) if m else 0
        t = h[h.find('<tbody'):h.find('</tbody>')]
        filas = 0
        for r in re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S):
            c = re.findall(r'<td[^>]*>(.*?)</td>', r, re.S)
            if len(c) < 8:
                continue
            filas += 1
            ti = re.search(r'title="([^"]*)"', c[4], re.S)
            doc = re.search(r"descargarDocumento\(this, '([^']+)'", c[7])
            out.append({'gaceta': _txt(c[0]), 'tipo': _txt(c[2]), 'numero': _txt(c[3]),
                        'objeto': _txt(ti.group(1) if ti else c[4]).strip(' "“”'), 'fecha': _iso(_txt(c[5])),
                        'publicado': _iso(_txt(c[6])), 'doc': doc.group(1) if doc else ''})
        if not filas:
            break
        p += 1
    if total and len(out) < total * 0.98:
        raise RuntimeError(f'histórico {anio}: {len(out)} filas de {total}')
    return out


def norma(numero, tipo, objeto, fecha, publicado, gaceta, dep, url, sin_titulo):
    c, k = clase(tipo)
    if not ('1900' <= fecha[:4] and fecha <= publicado):    # el histórico trae años 0002 y 2029
        fecha = publicado
    tit = _epigrafe(objeto) if not sin_titulo else ''
    desc = tit or f'{c} {numero}: la gaceta no trae el título'
    return {'tipo': k, 'subtipo': c, 'numero': numero, 'anio': (fecha or publicado)[:4], 'fecha': fecha or publicado,
            'titulo': tit, 'descripcion': desc, 'dependencia': dep, 'gaceta': gaceta, 'publicado': publicado,
            'sin_texto': sin_titulo, 'administrativo': particular(tit),
            'rutinario': bool(_PRESUPUESTO.search(tit)), 'url': url}


def consolidar(gs, hist):
    vistos, items, ocultos = set(), [], 0
    for g in sorted(gs.values(), key=lambda g: int(g['gaceta']), reverse=True):
        if not g['listada']:
            ocultos += len(g['actos'])
            continue
        url = f"{BASE}/consulta-publica/{g['id_pdf']}/descargar/pdf"
        for a in g['actos']:
            k = (clase(a['tipo'])[0], a['numero'], a['fecha'])
            if k in vistos:
                continue
            vistos.add(k)
            items.append(norma(a['numero'], a['tipo'], a['objeto'], a['fecha'], g['fecha'], g['gaceta'],
                               a['dependencia'], url, bool(_RELLENO.search(a['objeto']) or not a['objeto'])))
    for filas in hist.values():
        for a in filas:
            k = (clase(a['tipo'])[0], a['numero'], a['fecha'])
            if k in vistos or not a['publicado'].startswith(('2025', '2026', '2027')):
                continue
            vistos.add(k)
            items.append(norma(a['numero'], a['tipo'], a['objeto'], a['fecha'], a['publicado'], a['gaceta'], '',
                               f"{BASE}/historico-mercurio/descargar/{a['doc']}", not a['objeto']))
    items.sort(key=lambda x: (x['fecha'], x['numero']), reverse=True)
    return items, ocultos


def fetch(anios_hist, maximo):
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    gs = (C.leer(OUT / 'gacetas.json', {}) or {}).get('gacetas', {})
    hist = (C.leer(OUT / 'historico.json', {}) or {}).get('anios', {})
    previo = (C.leer(OUT / 'normas.json', {}) or {}).get('items', [])
    try:
        lista = listado()
        conocidas = sum(1 for g in gs.values() if g['listada'])
        if not lista or len(lista) < conocidas * 0.8:
            raise RuntimeError(f'{len(lista)} gacetas en el listado, teníamos {conocidas}')
        ns = sorted(map(int, lista))
        for n in range(ns[0], ns[-1] + 1):       # los saltos del listado pueden tener ficha
            n = str(n)
            if n in lista and n in gs and gs[n]['listada']:
                continue
            if n not in gs or n in lista:
                f = ficha(n)
                if f:
                    if n in lista:
                        f['listada'] = True
                    gs[n] = {**gs.get(n, {}), **f} if n not in lista else f
        leidas = fallas = 0
        for g in sorted(gs.values(), key=lambda g: int(g['gaceta']), reverse=True):
            if g['pdf_leido'] or not g['id_pdf'] or not any(_sospechoso(a) for a in g['actos']):
                continue
            if maximo and leidas >= maximo:
                break
            try:
                completar_con_pdf(g)
                leidas += 1
                C.escribir(OUT / 'gacetas.json', {'generado': gen, 'gacetas': gs})
            except Exception as e:
                fallas += 1
                print(f"    ! gaceta {g['gaceta']}: {str(e)[:120]}", file=sys.stderr)
        C.escribir(OUT / 'gacetas.json', {'generado': gen, 'gacetas': gs})
        for a in anios_hist:
            filas = historico(a)
            if len(filas) < len(hist.get(str(a), [])) * 0.8:
                raise RuntimeError(f'histórico {a}: {len(filas)} filas contra {len(hist[str(a)])}')
            hist[str(a)] = filas
            C.escribir(OUT / 'historico.json', {'generado': gen, 'anios': hist})
        items, ocultos = consolidar(gs, hist)
        if len(items) < len(previo) * 0.8:
            raise RuntimeError(f'{len(items)} actos contra {len(previo)} de la corrida anterior')
        C.escribir(OUT / 'normas.json', {'generado': gen, 'items': items})
        ult = max(g['fecha'] for g in gs.values() if g['listada'])
        print(f"  alcaldía · {sum(1 for g in gs.values() if g['listada'])} gacetas nuevas (última {ult}) · "
              f"{len(items)} actos · {sum(1 for x in items if not x['administrativo'] and not x['sin_texto'])} de alcance general · "
              f"{sum(1 for x in items if x['sin_texto'])} sin título · {ocultos} en gacetas no listadas · {leidas} PDF leídos")
        return not fallas
    except Exception as e:
        print(f'  alcaldía · FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)
        return False


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('fetch')
    f.add_argument('--historico', type=int, nargs='*', default=None, help='Años del archivo viejo a releer (sin año: 2026)')
    f.add_argument('--max', type=int, default=20, help='PDF por corrida; 0 = todos')
    a = ap.parse_args()
    if a.cmd == 'fetch':
        anios = [] if a.historico is None else (a.historico or [2026])
        sys.exit(0 if fetch(anios, a.max) else 1)


if __name__ == '__main__':
    main()
