#!/usr/bin/env python3
"""
Caudal · Colombia Compra Eficiente (Agencia Nacional de Contratación Pública).

Dos WordPress con la API REST abierta:

  www.colombiacompra.gov.co/wp-json/wp/v2/
    convocatoria   «Participación ciudadana» de borradores (guías, documentos
                   tipo, manuales). Fechas en el texto: «Fecha de inicio:
                   15/10/2026 · Fecha de cierre: 29/10/2026». Las que traen
                   «Enlace SUCOP» ya están en SUCOP: se marcan y el armador
                   no las repite.
    circular       circulares externas.
    mec-events     capacitaciones. ⚠️ La API NO trae la fecha del evento (el
                   plugin la guarda en meta privada y /mec/v1/events responde
                   vacío): se lee de la página de cada evento, solo de los 40
                   más recientes.
  relatoria.colombiacompra.gov.co/wp-json/wp/v2/conceptos
                   7.712 conceptos jurídicos. El año va en el título
                   («C-1557 de 2026»); la fecha de la API es la de carga (todo
                   se subió desde 2024). El resumen es el primer <strong>
                   («ADICIÓN – Concepto – Prohibición – Adición en más del 50%»)
                   y los descriptores van en `class_list`.
                   Primera corrida: todo (~78 páginas). Después, solo lo cargado
                   desde la última fecha vista menos 7 días.

Salida: `Bases de datos/caudal-entidades/raw/cce/{proyectos,normas,eventos}.json`.
Uso: python3 tools/caudal/entidades/harvest_cce.py fetch [--todo]
"""
import argparse
import datetime
import hashlib
import html
import json
import re
import sys

import comun as C

ENTIDAD = 'Agencia Nacional de Contratación Pública · Colombia Compra Eficiente'
WWW = 'https://www.colombiacompra.gov.co/wp-json/wp/v2'
REL = 'https://relatoria.colombiacompra.gov.co/wp-json/wp/v2'
OUT = C.RAW / 'cce'
MESES_EN = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
            'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12, 'ene': 1, 'abr': 4, 'ago': 8, 'dic': 12}


def _txt(h):
    h = re.sub(r'\[/?vc_[^\]]*\]', ' ', h or '')      # códigos del maquetador (WPBakery)
    return C.limpio(html.unescape(re.sub(r'<[^>]+>', ' ', h)))


def _api(url):
    return json.loads(C.curl(url, timeout=90))


def _paginas(base, params, maxp=200):
    out, p = [], 1
    while p <= maxp:
        sep = '&' if '?' in base else '?'
        try:
            lote = _api(f'{base}{sep}{params}&per_page=100&page={p}')
        except RuntimeError as e:
            if 'http=400' in str(e):          # página fuera de rango: WordPress da 400
                break
            raise
        if not isinstance(lote, list) or not lote:
            break
        out += lote
        if len(lote) < 100:
            break
        p += 1
    return out


def _dmy(s):
    m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', s or '')
    if not m:
        return ''
    try:
        return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
    except ValueError:
        return ''


def convocatorias(prev):
    hoy = datetime.date.today().isoformat()
    vivos = {}
    for c in _paginas(f'{WWW}/convocatoria', '_fields=id,date,link,title,content'):
        t = _txt(c['content']['rendered'])
        ini = _dmy((re.search(r'(?i)fecha de inicio\s*:?\s*([\d/]+)', t) or [None, ''])[1])
        fin = _dmy((re.search(r'(?i)fecha de cierre\s*:?\s*([\d/]+)', t) or [None, ''])[1])
        obj = (re.search(r'(?i)objetivo\s*:?\s*(.+?)(?:Fecha de inicio|$)', t) or [None, ''])[1].strip()
        sucop = re.search(r'sucop\.gov\.co/[^\s"<]*IDNorma=(\d+)', c['content']['rendered'])
        titulo = _txt(c['title']['rendered'])
        vivos[str(c['id'])] = {
            'id': str(c['id']), 'tipo_norma': 'Borrador para participación ciudadana',
            'titulo': titulo, 'objeto': obj, 'dependencia': '', 'fecha_inicio': ini, 'fecha_fin': fin,
            'comentarios_a': 'formulario en la página de la convocatoria', 'url': c['link'], 'anexos': [],
            'creado': c['date'][:10], 'visto': hoy, 'vigente_en_fuente': True,
            'sucop_id': int(sucop.group(1)) if sucop else None}
    out = dict(prev)
    for k, v in out.items():
        if k not in vivos:
            v['vigente_en_fuente'] = False
    out.update(vivos)
    return out, len(vivos)


def circulares():
    out = []
    for c in _paginas(f'{WWW}/circular', '_fields=id,date,link,title,content'):
        tit = _txt(c['title']['rendered'])
        m = re.search(r'(?i)(\d{1,4})\s+de\s+(\d{4})', tit)
        cuerpo = _txt(c['content']['rendered'])
        # fórmula fija de apertura: se salta hasta el propósito
        mp = re.search(r'(?i)con el (?:prop[óo]sito|objeto|fin) de\s+(.*)', cuerpo)
        if mp:
            cuerpo = mp.group(1)[:1].upper() + mp.group(1)[1:]
        pdf = re.search(r'href="([^"]+\.pdf)"', c['content']['rendered'] or '')
        out.append({'tipo': 'CIRCULARES', 'subtipo': 'Circular externa',
                    'numero': m.group(1).lstrip('0') if m else '', 'anio': m.group(2) if m else c['date'][:4],
                    'fecha': c['date'][:10], 'titulo': tit, 'descripcion': cuerpo[:500] or tit,
                    'url': pdf.group(1) if pdf else c['link']})
    return out


def _resumen_concepto(h):
    m = re.search(r'<strong>(.*?)</strong>', h or '', re.S)
    return _txt(m.group(1)) if m else _txt(h)[:220]


def conceptos(prev, todo):
    """Acumulado por id. Sin `--todo`, pide solo lo cargado desde la última
    fecha vista menos 7 días (la relatoría corrige fichas recién subidas)."""
    items = dict(prev)
    desde = ''
    if items and not todo:
        ult = max(v['cargado'] for v in items.values())
        desde = (datetime.date.fromisoformat(ult[:10]) - datetime.timedelta(days=7)).isoformat()
    params = '_fields=id,date,link,title,class_list,content' + (f'&after={desde}T00:00:00' if desde else '')
    nuevos = 0
    for c in _paginas(f'{REL}/conceptos', params, maxp=120):
        tit = _txt(c['title']['rendered'])
        m = re.search(r'C-?\s*(\d{1,5})\s+de\s+(\d{4})', tit)
        desc = [x.replace('descriptor-', '').replace('-', ' ') for x in c.get('class_list', [])
                if x.startswith('descriptor-')]
        k = str(c['id'])
        nuevos += k not in items
        items[k] = {'tipo': 'CONCEPTOS', 'subtipo': 'Concepto jurídico',
                    'numero': m.group(1) if m else '', 'anio': m.group(2) if m else '',
                    'fecha': c['date'][:10], 'cargado': c['date'][:10], 'titulo': tit,
                    'descripcion': _resumen_concepto(c['content']['rendered'])[:500],
                    'subtema': ' · '.join(desc), 'url': c['link']}
    return items, nuevos


_EV_FECHA = re.compile(r'mec-start-date-label">\s*([A-Za-z]{3})\w*\s+(\d{1,2})\s+(\d{4})')


def eventos(n=40):
    out = []
    for e in _api(f'{WWW}/mec-events?per_page={n}&_fields=id,date,link,title,content'):
        try:
            h = C.curl(e['link'], timeout=45)
        except RuntimeError:
            continue
        m = _EV_FECHA.search(h)
        dia = ''
        if m and m.group(1).lower()[:3] in MESES_EN:
            try:
                dia = datetime.date(int(m.group(3)), MESES_EN[m.group(1).lower()[:3]], int(m.group(2))).isoformat()
            except ValueError:
                dia = ''
        hora = re.search(r'class="mec-time"[^>]*>.*?<dd>\s*<abbr[^>]*>(.*?)</abbr>', h, re.S)
        out.append({'id': e['id'], 'titulo': _txt(e['title']['rendered']), 'fecha_inicio': dia,
                    'fecha_fin': '', 'dia': dia, 'lugar': f'Horario {_txt(hora.group(1))}' if hora else '',
                    'descripcion': _txt(e['content']['rendered'])[:600], 'categorias': ['Capacitación'],
                    'url': e['link']})
    return out


def fetch(todo):
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    res, ok = {}, True
    try:
        prev = (C.leer(OUT / 'proyectos.json', {}) or {}).get('items', {})
        items, vivos = convocatorias(prev)
        C.escribir(OUT / 'proyectos.json', {'generado': gen, 'entidad': ENTIDAD, 'items': items})
        res['convocatorias'] = f'{vivos} en la API · {sum(1 for v in items.values() if v.get("sucop_id"))} ya en SUCOP'
    except Exception as e:
        ok, res['convocatorias'] = False, f'FALLÓ ({e})'
    try:
        circ = circulares()
        prevc = (C.leer(OUT / 'conceptos.json', {}) or {}).get('items', {})
        conc, nuevos = conceptos(prevc, todo)
        C.escribir(OUT / 'conceptos.json', {'generado': gen, 'items': conc})
        C.escribir(OUT / 'normas.json', {'generado': gen, 'entidad': ENTIDAD,
                                         'items': circ + list(conc.values())})
        res['normas'] = f'{len(circ)} circulares · {len(conc)} conceptos ({nuevos} nuevos)'
    except Exception as e:
        ok, res['normas'] = False, f'FALLÓ ({e}) — se conserva el archivo anterior'
    try:
        ev = eventos()
        C.escribir(OUT / 'eventos.json', {'generado': gen, 'entidad': ENTIDAD, 'items': ev})
        res['eventos'] = f'{len(ev)} leídos · {sum(1 for e in ev if e["dia"] >= datetime.date.today().isoformat())} por venir'
    except Exception as e:
        ok, res['eventos'] = False, f'FALLÓ ({e})'
    for k, v in res.items():
        print(f'  cce · {k}: {v}')
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('fetch')
    f.add_argument('--todo', action='store_true', help='rehace todos los conceptos')
    a = ap.parse_args()
    if a.cmd == 'fetch':
        sys.exit(0 if fetch(a.todo) else 1)


if __name__ == '__main__':
    main()
