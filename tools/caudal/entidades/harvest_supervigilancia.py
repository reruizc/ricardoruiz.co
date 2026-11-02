#!/usr/bin/env python3
"""
Caudal · Superintendencia de Vigilancia y Seguridad Privada (tanda 4, nov-2026).

Sitio en Odoo, sin antibots: cada documento es una tarjeta `s_dl_item` con su tipo,
su nombre y sus fechas.

  resoluciones  /2-1-3-2-resoluciones y -paginaNN (las viejas van al final)
  circulares    /circulares (una página por circular) y /2-1-3-3-circulares
  proyectos     lo que enlaza /participa y /2-3-1-proyectos-normativos
  noticias      /blog/noticias-2/feed (Atom, solo las 15 últimas: se acumulan)

⚠️ «Publicación: Hace 10 horas» y «Hoy» son texto de la plantilla, no la fecha. Tampoco
sirve la «Expedición» si contradice el radicado: 20263100041307CS trae 15/09/2025. El
año del radicado (sus 4 primeras cifras) manda.
⚠️ Hay filas repetidas con PDF distinto y PDF repetido con nombre distinto: se llavea
por el radicado cuando existe.
⚠️ El feed trae el nombre de quien subió la noticia en `<author>`: no se guarda.
⚠️ Conceptos congelados en 2018 y eventos vacíos: no se cosechan.
⚠️ Los proyectos no siempre publican plazo: sin ventana legible quedan como consulta cerrada.
⚠️ SUCOP no tiene ninguna fila de la Supervigilancia: no hay nada que deduplicar.
⚠️ Parte del texto viene en Unicode descompuesto (NFD): se recompone antes de leerlo.
⚠️ Hay filas que enlazan otro documento: «Lineamientos… UAS» abre la resolución de plazos del
reporte financiero 2026. Sin radicado no hay cómo cruzar, así que en esas filas manda el PDF.

Salida: `Bases de datos/caudal-entidades/raw/supervigilancia/{proyectos,normas,noticias}.json`.
Uso: python3 tools/caudal/entidades/harvest_supervigilancia.py fetch
"""
import argparse
import datetime
import hashlib
import html
import re
import sys
import time
import unicodedata

import comun as C

WWW = 'https://www.supervigilancia.gov.co'
OUT = C.RAW / 'supervigilancia'
TXT = OUT / 'txt'
DESDE = '2025-01-01'
PAUSA = 1.0
MAX_PAGINAS = 30
MINIMO = .7                  # una corrida por debajo del 70 % de la anterior no se publica
_RADICADO = re.compile(r'\b(20\d{2})\d{7,11}(?:CS|C)?\b', re.I)
_CORTA = re.compile(r'(?i)^(?:circular(?:\s+(?:externa|interna|conjunta))?|resoluci[oó]n)\s*(?:n[o°º.]*\s*)?(\d{1,6})\s+de\s+(20\d{2})')
_INTERNA = re.compile(r'(?i)comit[eé]s?\s+(?:de\s+convivencia|internos)|manual\s+(?:espec[ií]fico\s+)?de\s+funciones|teletrabajo|'
                      r'desconexi[oó]n\s+laboral|vi[aá]ticos|honorarios|prima\s+t[eé]cnica|pol[ií]ticas?\s+contables?|'
                      r'd[ií]a\s+c[ií]vico|distribuci[oó]n\s+presupuesto|daño\s+antijur[ií]dico|'
                      r'auditor[ií]a\s+interna|gesti[oó]n\s+del\s+conocimiento')
_OBJETO = re.compile(r'(?is)\bpor\s+(?:la|el|medio\s+de\s+la|medio\s+del)\s+cual\b.+?(?=["”]|\n\s*\n|CONSIDERANDO|EL\s+SUPERINTENDENTE)')
_PROYECTO = re.compile(r'(?i)\bproyecto\s+(?:de\s+)?(resoluci[oó]n|decreto|circular|acuerdo)\b|\bprotocolo\b')


def _pag(ruta):
    time.sleep(PAUSA)
    return C.curl(f'{WWW}{ruta}', timeout=60)


def _texto(s):
    s = unicodedata.normalize('NFC', C.limpio(html.unescape(s or '')))
    return re.sub(r'(?i)\.pdf\b', '', s).strip(' "“”')


def _fecha_meta(meta):
    """Expedición primero; lo relativo («Hace 2 días», «Hoy») no es una fecha."""
    for campo in ('Expedición', 'Publicación'):
        m = re.search(rf'{campo}:\s*([^|]+)', meta or '')
        if not m:
            continue
        v = C.limpio(html.unescape(m.group(1)))
        d = re.fullmatch(r'(\d{2})/(\d{2})/(\d{4})', v)
        if d:
            return f'{d.group(3)}-{d.group(2)}-{d.group(1)}'
        f = C.fecha_larga(v)
        if f:
            return f
    return ''


def documentos(h):
    """Tarjetas `s_dl_item` de una página: tipo, nombre, fecha y enlace."""
    out = []
    for b in re.split(r'(?=<div class="s_dl_item )', h)[1:]:
        n = re.search(r'class="s_dl_doc_name"[^>]*>(.*?)</div>', b, re.S)
        t = re.search(r'class="s_dl_doc_type"[^>]*>(.*?)</div>', b, re.S)
        f = re.search(r'class="s_dl_doc_meta"[^>]*>(.*?)</div>', b, re.S)
        u = re.search(r'data-href="([^"]+)"', b)
        if n and u:
            out.append({'tipo': _texto(t.group(1)) if t else '', 'nombre': _texto(n.group(1)),
                        'fecha': _fecha_meta(C.limpio(html.unescape(f.group(1))) if f else ''),
                        'url': WWW + html.unescape(u.group(1)).replace('?download=true', ''),
                        'pdf': bool(re.search(r'data-format="pdf"', b))})
    return out


def _pdf(url):
    try:
        return C.pdf_texto(url, TXT / (hashlib.sha1(url.encode()).hexdigest()[:16] + '.txt'))
    except Exception:
        return ''


def _fecha_pdf(url, anio):
    """La fila contradice al radicado: la fecha sale del PDF, una sola vez. Si no se
    lee, el 1.º de enero del año del radicado."""
    fechas = [f for f in (C.fecha_larga(x) for x in re.findall(r'\d{1,2}\s+(?:de\s+)?[A-Za-zÁÉÍÓÚáéíóú]+\s+(?:de\s+|del\s+)?\d{4}', _pdf(url)))
              if f[:4] == anio]
    return fechas[0] if fechas else f'{anio}-01-01'


def _acto(d, tipo, subtipo):
    """Un documento → una norma. None si es de antes de `DESDE`."""
    nombre = re.sub(r'(?i)^(?:resoluci[oó]n|circular(?:\s+(?:externa|interna|conjunta))?)\s*(?:n[o°º.]*\s*)?-?\s*', '', d['nombre']).strip()
    r = _RADICADO.search(d['nombre'])
    c = _CORTA.search(d['nombre'])
    numero = r.group(0).upper() if r else (c.group(1) if c else '')
    anio = r.group(1) if r else (c.group(2) if c else d['fecha'][:4])
    fecha = d['fecha'] if d['fecha'][:4] == anio else _fecha_pdf(d['url'], anio)
    if (anio or '0') < DESDE[:4]:
        return None
    desc = re.sub(r'^\W+', '', nombre.replace(numero, '', 1) if numero else nombre).strip() or d['nombre']
    titulo = f'{subtipo} {numero} de {anio}' if numero else d['nombre']
    if not numero and d['pdf']:
        o = _OBJETO.search(_pdf(d['url']))
        if o:
            t = C.limpio(o.group(0)).rstrip(' .')
            desc = titulo = t[:1].upper() + t[1:]
    return {'tipo': tipo, 'subtipo': subtipo, 'numero': numero, 'anio': anio, 'fecha': fecha, 'titulo': titulo[:300],
            'descripcion': desc[:600], 'administrativo': C.es_administrativo(desc) or bool(_INTERNA.search(desc)), 'url': d['url']}


def resoluciones():
    docs, pag = [], 1
    while pag <= MAX_PAGINAS:
        ruta = '/2-1-3-2-resoluciones' + (f'-pagina{pag:02d}' if pag > 1 else '')
        try:
            filas = documentos(_pag(ruta))
        except RuntimeError:
            if pag == 1:
                raise
            break                        # el sitio responde 404 al pasarse de la última
        actos = [a for a in (_acto(d, 'RESOLUCIONES', 'Resolución') for d in filas) if a]
        if not actos:
            break                        # lo nuevo va adelante: de aquí en más es histórico
        docs += actos
        pag += 1
    return docs


def circulares():
    h = _pag('/circulares')
    t = h[h.find('<main'):]
    docs = []
    # las recientes tienen una página propia; solo se abren las que no son históricas
    for u, txt in re.findall(r'<a [^>]*href="((?:https://www\.supervigilancia\.gov\.co)?/[^"#]*circular[^"#]*)"[^>]*>(.*?)</a>', t, re.S):
        nombre = _texto(txt)
        if not nombre or re.search(r'\b(?:de|[-/])\s*(?:19\d\d|20(?:0\d|1\d|2[0-4]))\b', nombre) or re.search(r'-(?:0\d|1\d)\b', nombre):
            continue
        ruta = u.replace(WWW, '')
        filas = documentos(_pag(ruta))
        pdf = next((d for d in filas if d['pdf'] and 'circular' in C.fold(d['tipo'] + ' ' + d['nombre'])), None) or (filas[0] if filas else None)
        if pdf:
            docs.append({**pdf, 'nombre': nombre})
    docs += documentos(_pag('/2-1-3-3-circulares'))
    out = []
    for d in docs:
        if 'anexo' in C.fold(d['nombre'])[:12]:
            continue
        if not _RADICADO.search(d['nombre']) and (d['fecha'] or '0') < DESDE:
            continue
        a = _acto(d, 'CIRCULARES', 'Circular')
        if a:
            out.append(a)
    return out


def normas():
    por = {}
    for a in resoluciones() + circulares():
        k = (a['tipo'], a['numero'] or a['url'])
        v = por.get(k)
        # entre dos filas del mismo acto se queda la de objeto más completo
        if not v or len(a['descripcion']) > len(v['descripcion']):
            por[k] = a
    return list(por.values())


def _doc_principal(docs):
    pdfs = [d for d in docs if d['pdf'] and not re.search(r'(?i)memoria|anexo|respuesta|matriz|estudio', d['nombre'])]
    return next((d for d in pdfs if _PROYECTO.search(d['nombre'])), None) or (pdfs[0] if pdfs else None) or (docs[0] if docs else None)


def _clase(texto):
    m = _PROYECTO.search(texto)
    return f'Proyecto de {m.group(1).lower().replace("resolucion", "resolución")}' if m and m.group(1) else 'Proyecto de protocolo'


def _llave(titulo):
    return hashlib.sha1(' '.join(sorted(set(re.findall(r'[a-z0-9]{4,}', C.fold(titulo))))).encode()).hexdigest()[:16]


def proyectos(prev):
    hoy = datetime.date.today().isoformat()
    h = _pag('/participa')
    t = h[h.find('<main'):h.find('<footer')]
    vivos = {}
    for ruta, txt in sorted(set(re.findall(r'<a [^>]*href="((?:https://www\.supervigilancia\.gov\.co)?/[^"#]+)"[^>]*>(.*?)</a>', t, re.S))):
        nombre = _texto(txt)
        if not _PROYECTO.search(nombre):
            continue
        pagina = ruta.replace(WWW, '')
        p = _pag(pagina)
        docs = documentos(p)
        doc = _doc_principal(docs)
        if not doc:
            continue
        cuerpo = C.limpio(html.unescape(p[p.find('<main'):p.find('<footer')]))
        ini, fin = C.ventana(cuerpo)
        fechas = sorted(d['fecha'] for d in docs if d['fecha'])
        ini = ini or (fechas[0] if fechas else '')
        titulo = doc['nombre'] if re.search(r'(?i)por\s+(?:la|el|medio)\b', doc['nombre']) and _PROYECTO.search(doc['nombre']) else nombre
        k = _llave(re.sub(r'(?i)supervigilancia|proyecto|resoluci[oó]n', ' ', titulo))
        vivos[k] = {'id': k, 'tipo_norma': _clase(titulo), 'titulo': titulo[:400], 'dependencia': '', 'fecha_inicio': ini,
                    'fecha_fin': fin, 'comentarios_a': '', 'url': doc['url'], 'anexos': [d['url'] for d in docs if d is not doc][:4],
                    'creado': ini, 'visto': hoy, 'vigente_en_fuente': True}
    # la lista de transparencia es casi toda de 2022; solo entra lo reciente
    for d in documentos(_pag('/2-3-1-proyectos-normativos')):
        if (d['fecha'] or '0') < DESDE:
            continue
        k = _llave(d['nombre'])
        vivos.setdefault(k, {'id': k, 'tipo_norma': _clase(d['nombre']), 'titulo': d['nombre'][:400], 'dependencia': '',
                             'fecha_inicio': d['fecha'], 'fecha_fin': '', 'comentarios_a': '', 'url': d['url'], 'anexos': [],
                             'creado': d['fecha'], 'visto': hoy, 'vigente_en_fuente': True})
    out = dict(prev)
    for k, v in out.items():
        if k not in vivos:
            v['vigente_en_fuente'] = False
    out.update(vivos)
    return out, len(vivos)


def noticias(prev):
    x = C.curl(f'{WWW}/blog/noticias-2/feed', timeout=60)
    out = {r['url']: r for r in prev}
    n = 0
    for b in re.findall(r'<entry>(.*?)</entry>', x, re.S):
        t = re.search(r'<title[^>]*>(.*?)</title>', b, re.S)
        u = re.search(r'<link href="([^"]+)"', b)
        f = re.search(r'<updated>(\d{4}-\d{2}-\d{2})', b)
        s = re.search(r'<summary[^>]*>(.*?)</summary>', b, re.S)
        if not (t and u and f):
            continue
        n += 1
        res = C.limpio(html.unescape(s.group(1) if s else '')).rstrip('.… ')
        out[u.group(1)] = C.comunicado(C.limpio(html.unescape(t.group(1))), f.group(1), u.group(1), res)
    return list(out.values()), n


def _guarda(nombre, nuevos, anteriores):
    """Guarda de Caudal: si una corrida trae mucho menos que la anterior, se levanta
    la mano y no se publica. La fuente pudo cambiar de plantilla sin avisar."""
    if anteriores and nuevos < anteriores * MINIMO:
        raise RuntimeError(f'{nombre}: {nuevos} contra {anteriores} de la corrida anterior')
    if not nuevos:
        raise RuntimeError(f'{nombre}: la corrida no trajo nada')


def fetch():
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    ok = True
    try:
        prev = C.leer(OUT / 'normas.json', {}) or {}
        ns = normas()
        _guarda('normas', len(ns), prev.get('n_fuente') or 0)
        # lo ya visto no se pierde si la fuente lo retira
        llave = lambda n: (n['tipo'], n['numero'] or n['url'])
        items = {llave(n): n for n in prev.get('items', [])}
        items.update({llave(n): n for n in ns})
        C.escribir(OUT / 'normas.json', {'generado': gen, 'n_fuente': len(ns), 'items': list(items.values())})
        print(f'  supervigilancia · {len(ns)} normas ({sum(1 for n in ns if not n["administrativo"])} de alcance general)')
    except Exception as e:
        ok = False
        print(f'  supervigilancia · normas FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)
    try:
        prev = C.leer(OUT / 'proyectos.json', {}) or {}
        items, n = proyectos(prev.get('items', {}))
        _guarda('proyectos', n, prev.get('n_fuente') or 0)
        C.escribir(OUT / 'proyectos.json', {'generado': gen, 'n_fuente': n, 'items': items})
        print(f'  supervigilancia · {n} proyectos en su sitio · {len(items)} acumulados')
    except Exception as e:
        ok = False
        print(f'  supervigilancia · proyectos FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)
    try:
        prev = C.leer(OUT / 'noticias.json', {}) or {}
        xs, n = noticias(prev.get('items', []))
        _guarda('noticias', n, prev.get('n_fuente') or 0)
        C.escribir(OUT / 'noticias.json', {'generado': gen, 'n_fuente': n, 'items': xs})
        print(f'  supervigilancia · {len(xs)} noticias')
    except Exception as e:
        ok = False
        print(f'  supervigilancia · noticias FALLÓ ({e}) — queda el archivo anterior', file=sys.stderr)
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('fetch')
    ap.parse_args()
    sys.exit(0 if fetch() else 1)


if __name__ == '__main__':
    main()
