#!/usr/bin/env python3
"""
Caudal · Superintendencia de Industria y Comercio · lo que el pilar Regulatorio
todavía no traía.

Sus circulares y resoluciones de carácter general ya entran por
`tools/caudal/supers/harvest_sic_circulares.py`. Este cosechador suma tres cosas,
y reusa el buscador de normas de aquel (mismo view Drupal):

  proyectos    `field_clasificacion2_target_id` 183 (proyectos de resolución) y
               185 (proyectos de circular): 174 borradores. Solo ~40 de
               2024-2026 están también en SUCOP (la Lambda deduplica por título).
               La ventana va en el cuerpo de la ficha («Término para recibir
               comentarios: Del 31 de diciembre de 2025 al 15 de enero de
               2026»). El HTML de cada ficha se guarda: una ficha ya leída no se
               vuelve a pedir.
  abogacía     datos.gov.co `mdd2-pbuw` (859, al día): las recomendaciones de
               la SIC sobre los borradores de OTRAS entidades (CREG, ministerios,
               comisiones…), artículo por artículo, y si la entidad las acogió.
  eventos      /transparencia/informacion-de-la-entidad/eventos: foros,
               capacitaciones y congresos. La fecha sale del <time datetime> de
               cada página (UTC).

Salida: `Bases de datos/caudal-entidades/raw/sic/{proyectos,normas,eventos}.json`.
Uso: python3 tools/caudal/entidades/harvest_sic.py fetch
"""
import argparse
import datetime
import hashlib
import html
import json
import re
import sys
from pathlib import Path

import comun as C

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'supers'))
import harvest_sic_circulares as S  # noqa: E402  (buscador de normas de la SIC)

ENTIDAD = 'Superintendencia de Industria y Comercio'
SEDE = 'https://sedeelectronica.sic.gov.co'
OUT = C.RAW / 'sic'
NODOS = OUT / 'nodos'
MESES = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 'julio': 7,
         'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12}
_M = '(' + '|'.join(MESES) + ')'
# «Del 31 de diciembre de 2025 al 15 de enero de 2026» · «desde el 3 hasta el 17 de
# marzo de 2026» · «del 3 al 17 de marzo de 2026»
_VENTANA = re.compile(rf'(?i)(?:del|desde\s+el)\s+(\d{{1,2}})(?:\s+de\s+{_M})?(?:\s+de\s+(\d{{4}}))?\s*'
                      rf'(?:al|hasta\s+el|y\s+hasta\s+el)\s+(\d{{1,2}})\s+de\s+{_M}\s+(?:de|del)\s+(\d{{4}})')


def _fecha(a, m, d):
    try:
        return datetime.date(int(a), MESES[m.lower()], int(d)).isoformat()
    except (KeyError, ValueError, TypeError):
        return ''


_CIERRE = re.compile(rf'(?i)t[ée]rmino\s+para\s+recibir\s+comentarios\s*:?\s*(?:hasta\s+el\s+)?(\d{{1,2}})\s+de\s+{_M}\s+(?:de|del)\s+(\d{{4}})')


def ventana(txt):
    m = _VENTANA.search(txt or '')
    if not m:
        c = _CIERRE.search(txt or '')     # «Término para recibir comentarios: 06 de diciembre de 2024»
        return ('', _fecha(c.group(3), c.group(2), c.group(1))) if c else ('', '')
    d1, m1, a1, d2, m2, a2 = m.groups()
    m1 = m1 or m2
    if not a1:
        a1 = str(int(a2) - 1) if MESES[m1.lower()] > MESES[m2.lower()] else a2
    return _fecha(a1, m1, d1), _fecha(a2, m2, d2)


def _nodo_html(path):
    NODOS.mkdir(parents=True, exist_ok=True)
    f = NODOS / (hashlib.sha1(path.encode()).hexdigest()[:16] + '.html')
    if f.exists():
        return f.read_text(encoding='utf-8')
    t = S.nodo(path)
    if t:
        f.write_text(t, encoding='utf-8')
    return t


def proyectos(prev):
    hoy = datetime.date.today().isoformat()
    vivos = {}
    for tid, tipo in ((183, 'Proyecto de Resolución'), (185, 'Proyecto de Circular')):
        for path, fila in S.listar({'field_clasificacion2_target_id': tid}).items():
            t = _nodo_html(path)
            rec = S.parse_nodo(t) if t else {'cuerpo': '', 'fecha_publicacion': '', 'url_pdf': ''}
            texto = ' '.join([fila.get('desc_listado') or '', rec.get('cuerpo') or ''])
            ini, fin = ventana(texto)
            titulo = re.sub(r'^(?:Proyecto(?:\s+Normativo|\s+de\s+(?:Resoluci[óo]n|Circular))?)\s*[:\-–]?\s*', '',
                            fila['titulo']).strip(' ¨"“”')
            m = re.search(r'[«"“]\s*(.+?)\s*[»"”]', fila.get('desc_listado') or '')
            if m and len(m.group(1)) > len(titulo):
                titulo = m.group(1)
            mail = re.search(r'[\w.+-]+@sic\.gov\.co', texto)
            k = hashlib.sha1(path.encode()).hexdigest()[:16]
            vivos[k] = {'id': k, 'tipo_norma': tipo, 'titulo': titulo[:1].upper() + titulo[1:],
                        'objeto': (fila.get('desc_listado') or '')[:600], 'dependencia': '',
                        'fecha_inicio': ini or rec.get('fecha_publicacion') or '', 'fecha_fin': fin,
                        'comentarios_a': mail.group(0) if mail else '', 'url': SEDE + path,
                        'anexos': [rec['url_pdf']] if rec.get('url_pdf') else [],
                        'creado': rec.get('fecha_publicacion') or ini, 'visto': hoy, 'vigente_en_fuente': True}
    out = dict(prev)
    for k, v in out.items():
        if k not in vivos:
            v['vigente_en_fuente'] = False
    out.update(vivos)
    return out, len(vivos)


def abogacia():
    filas = json.loads(C.curl('https://www.datos.gov.co/resource/mdd2-pbuw.json?$limit=5000', timeout=90))
    out = []
    for r in filas:
        ent = C.limpio(r.get('nombre_entidad_reguladora'))
        proy = C.limpio(r.get('nombre_proyecto'))
        if not proy:
            continue
        acoge = C.limpio(r.get('acoge_comentarios_sic'))
        fecha = (r.get('fecha_salida_abogacia') or r.get('fecha_ingreso') or '')[:10]
        rec = C.limpio(r.get('recomendaci_n_sic_y_o_aparte'))
        out.append({'tipo': 'CONCEPTOS', 'subtipo': 'Abogacía de la competencia',
                    'numero': (r.get('radicado_inicial') or '').strip(), 'anio': fecha[:4], 'fecha': fecha,
                    'titulo': f'Abogacía de la competencia sobre un proyecto de {ent}',
                    'descripcion': (f'Comentarios de la SIC al proyecto de {ent}: {proy}'
                                    + (f' · ¿Los acogió? {acoge}' if acoge else ''))[:900],
                    'subtema': ' · '.join(x for x in (C.limpio(r.get('sector')), ent, rec[:400]) if x),
                    'entidad_regulada': ent, 'acoge': acoge,
                    'url': 'https://www.datos.gov.co/d/mdd2-pbuw'})
    return out


def eventos(paginas=3):
    links = []
    for p in range(paginas):
        h = C.curl(f'{SEDE}/transparencia/informacion-de-la-entidad/eventos?page={p}', timeout=60)
        nuevos = [u.strip() for u in re.findall(r'href="(/transparencia/informacion-de-la-entidad/eventos/[^"]+)"', h)
                  if not u.strip().endswith('/calendario')]
        nuevos = [u for u in dict.fromkeys(nuevos) if u not in links]
        if not nuevos:
            break
        links += nuevos
    out = []
    for u in links:
        try:
            h = C.curl(SEDE + u, timeout=45)
        except RuntimeError:
            continue
        campo = lambda n: C.limpio(html.unescape(re.sub(r'<[^>]+>', ' ', (re.search(
            rf'field--name-{n}[^>]*>(.*?)</div>\s*</div>', h, re.S) or [None, ''])[1])))
        tiempos = re.findall(r'<time[^>]*datetime="([^"]+)"', h)
        ini = tiempos[0] if tiempos else ''
        try:
            dia = (datetime.datetime.fromisoformat(ini.replace('Z', '+00:00'))
                   - datetime.timedelta(hours=5)).date().isoformat() if ini else ''
        except ValueError:
            dia = ''
        tit = re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S)
        lugar = re.sub(r'^Lugar\s*', '', campo('field-text1'))
        modal = re.sub(r'^Modalidad\s*', '', campo('field-clasificacion3'))
        tipo_ev = re.sub(r'^Tipo de Evento\s*', '', campo('field-clasificacion2'))
        deleg = re.sub(r'^Delegatura Responsable\s*', '', campo('field-clasificacion'))
        out.append({'id': u, 'titulo': C.limpio(html.unescape(re.sub(r'<[^>]+>', ' ', tit.group(1)))) if tit else u,
                    'fecha_inicio': ini, 'fecha_fin': tiempos[1] if len(tiempos) > 1 else '', 'dia': dia,
                    'lugar': ' · '.join(x for x in (lugar, modal) if x), 'descripcion': deleg,
                    'categorias': [x for x in (tipo_ev,) if x], 'url': SEDE + u})
    return out


def fetch():
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    res, ok = {}, True
    try:
        prev = (C.leer(OUT / 'proyectos.json', {}) or {}).get('items', {})
        items, vivos = proyectos(prev)
        C.escribir(OUT / 'proyectos.json', {'generado': gen, 'entidad': ENTIDAD, 'items': items})
        hoy = datetime.date.today().isoformat()
        res['proyectos'] = (f'{vivos} leídos · {sum(1 for v in items.values() if v["fecha_fin"] >= hoy)} abiertos · '
                            f'{sum(1 for v in items.values() if not v["fecha_fin"])} sin ventana')
    except Exception as e:
        ok, res['proyectos'] = False, f'FALLÓ ({e})'
    try:
        ab = abogacia()
        if len(ab) < 400:
            raise RuntimeError(f'solo {len(ab)} filas: el dataset tiene más de 800')
        C.escribir(OUT / 'normas.json', {'generado': gen, 'entidad': ENTIDAD, 'items': ab})
        res['abogacía'] = f'{len(ab)} conceptos'
    except Exception as e:
        ok, res['abogacía'] = False, f'FALLÓ ({e}) — se conserva el archivo anterior'
    try:
        ev = eventos()
        C.escribir(OUT / 'eventos.json', {'generado': gen, 'entidad': ENTIDAD, 'items': ev})
        res['eventos'] = f'{len(ev)} · {sum(1 for e in ev if e["dia"] >= datetime.date.today().isoformat())} por venir'
    except Exception as e:
        ok, res['eventos'] = False, f'FALLÓ ({e})'
    for k, v in res.items():
        print(f'  sic · {k}: {v}')
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('fetch')
    if ap.parse_args().cmd == 'fetch':
        sys.exit(0 if fetch() else 1)


if __name__ == '__main__':
    main()
