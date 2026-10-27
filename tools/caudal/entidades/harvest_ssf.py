#!/usr/bin/env python3
"""
Caudal · Superintendencia del Subsidio Familiar (Supersubsidio).

El regulador directo de las cajas de compensación NO publica en SUCOP ni en
datos.gov.co. Su sitio (Liferay) trae tablas armadas a mano, una por vigencia:

  proyectos     /web/guest/proyectos-normativos1
                Documento · enlaces · observación (fechas «dd-mm-aaaa» y
                correos). Las filas «Respuesta a comentarios…» no son
                borradores: se cuelgan como anexo del proyecto anterior.
  circulares    /web/guest/normativa-circulares     número · fecha · asunto · PDF
  resoluciones  /web/guest/resoluciones2            documento · asunto · PDF
                (la vieja /resoluciones1 se quedó en 2024-2025)
  calendario    ICS público de Google (se dejó de alimentar el 26-jun-2026;
                se lee igual por si lo reactivan)

La relatoría jurídica (conceptos) va aparte, en la fase 4.

Salida: `Bases de datos/caudal-entidades/raw/ssf/{proyectos,normas,eventos}.json`.
Uso: python3 tools/caudal/entidades/harvest_ssf.py fetch
"""
import argparse
import datetime
import hashlib
import html
import re
import sys

import comun as C

ENTIDAD = 'Superintendencia del Subsidio Familiar'
BASE = 'https://www.ssf.gov.co'
ICS = ('https://calendar.google.com/calendar/ical/supersubsidiofamiliar2014%40gmail.com'
       '/public/basic.ics')
OUT = C.RAW / 'ssf'
MESES = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 'julio': 7,
         'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12}


def _t(frag):
    return C.limpio(html.unescape(re.sub(r'<br\s*/?>', ' ', frag or '')))


def _abs(u):
    return u if u.startswith('http') else BASE + u


def fecha_libre(s):
    """«23-10-26» · «13/05/2026» · «13 de mayo de 2026» · «13 mayo de 2026» → ISO."""
    s = s or ''
    m = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})', s)
    if m:
        d, mth, a = m.groups()
        a = int(a) + (2000 if len(a) == 2 else 0)
        try:
            return datetime.date(a, int(mth), int(d)).isoformat()
        except ValueError:
            return ''
    m = re.search(r'(\d{1,2})\s+(?:de\s+)?([a-záéíóú]+)\s+(?:de|del)\s+(\d{4})', s, re.I)
    if m and m.group(2).lower() in MESES:
        try:
            return datetime.date(int(m.group(3)), MESES[m.group(2).lower()], int(m.group(1))).isoformat()
        except ValueError:
            return ''
    return ''


def _filas(h):
    return [re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S)
            for r in re.findall(r'<tr>(.*?)</tr>', h, re.S) if '<td' in r]


def proyectos(prev):
    h = C.curl(f'{BASE}/web/guest/proyectos-normativos1', timeout=60)
    hoy = datetime.date.today().isoformat()
    vivos, ultimo = {}, None
    for tds in _filas(h):
        if len(tds) < 2:
            continue
        doc = _t(tds[0])
        if not doc or doc.lower() in ('documento',):
            continue
        # 2026 trae Documento · Enlace · Observación; 2024-2025 suman «Asunto»
        # en la segunda columna y corren las demás una posición
        con_asunto = len(tds) >= 4
        celda_links = tds[2] if con_asunto else tds[1]
        links = [_abs(u) for u in re.findall(r'href="([^"]+)"', celda_links) if not u.startswith('mailto')]
        obs = (tds[3] if con_asunto else tds[2] if len(tds) > 2 else '')
        if doc.lower().startswith('respuesta a comentarios'):
            if ultimo:                    # respuesta de la entidad: anexo del proyecto anterior
                ultimo['anexos'] = ultimo['anexos'] + links
            continue
        fechas = re.findall(r'\d{1,2}-\d{1,2}-\d{4}', _t(obs))
        mails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', _t(obs))
        asunto = _t(tds[1]) if con_asunto else ''
        titulo = (asunto if len(asunto) > len(doc) + 10 else doc).strip(' "“”')
        url = links[0] if links else ''
        item = {'id': hashlib.sha1((url or titulo).encode()).hexdigest()[:16],
                'tipo_norma': ('Proyecto de Circular' if 'circular' in doc.lower() else
                               'Proyecto de Resolución' if 'resoluci' in doc.lower() else 'Proyecto normativo'),
                'titulo': titulo, 'dependencia': '',
                'fecha_inicio': fecha_libre(fechas[0]) if fechas else '',
                'fecha_fin': fecha_libre(fechas[1]) if len(fechas) > 1 else '',
                'comentarios_a': '; '.join(dict.fromkeys(mails)), 'url': url, 'anexos': links[1:],
                'creado': fecha_libre(fechas[0]) if fechas else '', 'visto': hoy, 'vigente_en_fuente': True}
        vivos[item['id']] = item
        ultimo = item
    out = dict(prev)
    for k, v in out.items():
        if k not in vivos:
            v['vigente_en_fuente'] = False
    out.update(vivos)
    return out, len(vivos)


def circulares():
    h = C.curl(f'{BASE}/web/guest/normativa-circulares', timeout=90)
    out = []
    for tds in _filas(h):
        if len(tds) < 3 or _t(tds[0]).lower() in ('número', 'numero'):
            continue
        num = re.sub(r'\D', '', _t(tds[0])).lstrip('0')
        fecha = fecha_libre(_t(tds[1]))
        asunto = _t(tds[2])
        link = re.search(r'href="([^"]+)"', tds[3] if len(tds) > 3 else '')
        if not asunto:
            continue
        out.append({'tipo': 'CIRCULARES', 'subtipo': 'Circular externa', 'numero': num,
                    'anio': fecha[:4], 'fecha': fecha, 'titulo': f'Circular externa {_t(tds[0])}',
                    'descripcion': asunto[:1].upper() + asunto[1:].lower() if asunto.isupper() else asunto,
                    'url': _abs(link.group(1)) if link else ''})
    return out


def resoluciones():
    h = C.curl(f'{BASE}/web/guest/resoluciones2', timeout=90)
    out = []
    for tds in _filas(h):
        if len(tds) < 2:
            continue
        doc, asunto = _t(tds[0]), _t(tds[1])
        if not asunto or doc.lower().startswith(('documento', 'descripci')):
            continue
        if re.search(r'(?i)tutela|auto\s+admisorio|notificaci[óo]n', doc + ' ' + asunto[:80]):
            continue                      # la página también cuelga tutelas y notificaciones
        mn = re.search(r'(?:RES\.?\s*|No\.?\s*|RESOLUCI[ÓO]N\s+)0*(\d{2,5})', doc, re.I) or \
            re.search(r'0*(\d{2,5})', doc)
        fecha = fecha_libre(doc) or fecha_libre(asunto)
        me = re.search(r'[«"“](.+?)[»"”]', asunto)
        epi = (me.group(1) if me else asunto).strip()
        link = re.search(r'href="([^"]+)"', tds[2] if len(tds) > 2 else tds[1])
        out.append({'tipo': 'RESOLUCIONES', 'subtipo': 'Resolución', 'numero': mn.group(1) if mn else '',
                    'anio': fecha[:4], 'fecha': fecha, 'titulo': doc, 'descripcion': epi,
                    'administrativo': C.es_administrativo(epi),
                    'url': _abs(link.group(1)) if link else ''})
    return out


def eventos():
    ics = C.curl(ICS, timeout=60)
    out = []
    for blk in re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', ics, re.S):
        blk = re.sub(r'\r?\n[ \t]', '', blk)          # líneas plegadas del ICS
        g = lambda k: (re.search(rf'^{k}[^:\n]*:(.*)$', blk, re.M) or [None, ''])[1].strip()
        ini = g('DTSTART')
        dia = f'{ini[:4]}-{ini[4:6]}-{ini[6:8]}' if len(ini) >= 8 else ''
        desc = g('DESCRIPTION').replace('\\n', ' ').replace('\\,', ',')
        out.append({'id': g('UID'), 'titulo': g('SUMMARY').replace('\\,', ','), 'fecha_inicio': ini,
                    'fecha_fin': g('DTEND'), 'dia': dia, 'lugar': g('LOCATION').replace('\\,', ','),
                    'descripcion': C.limpio(desc)[:800], 'categorias': [], 'url': ''})
    return out


def fetch():
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    res, ok = {}, True
    prev = (C.leer(OUT / 'proyectos.json', {}) or {}).get('items', {})
    try:
        items, vivos = proyectos(prev)
        C.escribir(OUT / 'proyectos.json', {'generado': gen, 'entidad': ENTIDAD, 'items': items})
        res['proyectos'] = f'{vivos} en la página · {len(items)} acumulados'
    except Exception as e:
        ok, res['proyectos'] = False, f'FALLÓ ({e})'
    normas, fallas = [], []
    for nombre, fn in (('circulares', circulares), ('resoluciones', resoluciones)):
        try:
            xs = fn()
            normas += xs
            res[nombre] = f'{len(xs)}'
        except Exception as e:
            fallas.append(nombre)
            res[nombre] = f'FALLÓ ({e})'
    if normas and not fallas:            # a medias no se escribe: queda el archivo bueno
        C.escribir(OUT / 'normas.json', {'generado': gen, 'entidad': ENTIDAD, 'items': normas})
    elif fallas:
        ok = False
    try:
        ev = eventos()
        C.escribir(OUT / 'eventos.json', {'generado': gen, 'entidad': ENTIDAD, 'items': ev})
        res['eventos'] = f'{len(ev)} (último {max((e["dia"] for e in ev), default="—")})'
    except Exception as e:
        ok, res['eventos'] = False, f'FALLÓ ({e})'
    for k, v in res.items():
        print(f'  ssf · {k}: {v}')
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('fetch')
    if ap.parse_args().cmd == 'fetch':
        sys.exit(0 if fetch() else 1)


if __name__ == '__main__':
    main()
