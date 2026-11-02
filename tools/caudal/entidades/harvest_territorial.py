#!/usr/bin/env python3
"""
Caudal · Entidades territoriales · Asamblea de Antioquia y Concejo de Medellín
(fase 2 del plan de Comfama, oct-2026).

Asamblea de Antioquia · WordPress con API REST abierta. Cada documento es un
post con categoría:
    216  Proyecto de ordenanza          (361)
    225  Informes de ponencia           (694)  → en qué debate va cada proyecto
      6  Ordenanzas                     (1.180)
    217  Actas de sesión                (702)  → plenaria y comisiones, con PDF
  El número y la fecha salen del título («PROYECTO DE ORDENANZA No. 41 DEL 15 DE
  OCTUBRE DE 2026 “POR MEDIO DE LA CUAL…”»). Un proyecto pasa a «ordenanza»
  cuando una ordenanza tiene el mismo epígrafe (los números no coinciden).
  Agenda: la categoría 227 «Agenda semanal» murió en nov-2022 (imágenes de WhatsApp).
  La vigente es el Google Calendar público que embebe /agenda/: su ICS trae cada
  sesión con su tema, hasta dos semanas adelante.

Concejo de Medellín · SIMI (PrimeFaces, sin login, `simi.concejodemedellin.gov.co/
simi3/invitados/…`). Paginación por AJAX de a 10 filas (⚠️ con más rows da
IllegalArgumentException):
    proyectos/proyectos     proyectos de acuerdo (número · título · estado)
    proyectos/acuerdos      acuerdos (número · proyecto de origen · título · estado)
    proposiciones/citaciones  control político (fecha · sesión · código · tema · estado)
    plenaria/debates        sesiones de plenaria, ya programadas a futuro → eventos
    proyectos/permanente    reuniones de las comisiones permanentes → eventos
  SIMI no da enlace por registro. El `data-rk` de cada fila es el `simi_id` de la ficha
  pública del sitio del Concejo (www…/interna-proyectos-de-acuerdo?simi_id=N), con
  proponentes y ponentes, ⚠️ pero solo existe para los proyectos abiertos a
  participación: a los demás les responde 200 con una página genérica. Se enlaza solo
  si la ficha trae ese número de proyecto; `sin_ficha` evita repreguntar hasta que cambie
  de estado.
  ⚠️ El PDF y la ponencia viven en las pestañas de SIMI. La petición que las carga
  la frena la regla de Cloudflare del sitio («Sorry, you have been blocked»; medido
  el 1-nov-2026): NO se reintenta ni se disfraza. Falta, y se declara.

Salida: `Bases de datos/caudal-entidades/raw/territorial/{asamblea,concejo}.json`.
Asamblea suma `actas` y `eventos`; cada proyecto del Concejo suma `simi_id`.
Uso: python3 tools/caudal/entidades/harvest_territorial.py fetch [--todo]
"""
import argparse
import datetime
import html
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse

import comun as C

OUT = C.RAW / 'territorial'
ASAMBLEA = 'https://asambleadeantioquia.gov.co/wp-json/wp/v2'
SIMI = 'https://simi.concejodemedellin.gov.co/simi3/invitados'
FICHA_CONCEJO = 'https://www.concejodemedellin.gov.co/interna-proyectos-de-acuerdo?simi_id='
AGENDA_ASAMBLEA = 'https://asambleadeantioquia.gov.co/agenda/'
ICS_ASAMBLEA = ('https://calendar.google.com/calendar/ical/4b90b2a17d7ffe4eb0fad78c30ca45ec1175f914438bd08901652537b'
                '078a954%40group.calendar.google.com/public/basic.ics')
MESES = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 'julio': 7,
         'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12}
_M = '(' + '|'.join(MESES) + ')'


def _txt(h):
    return C.limpio(html.unescape(re.sub(r'<[^>]+>', ' ', h or '')))


def _fecha_es(s):
    m = re.search(rf'(?i)(\d{{1,2}})\s+de\s+{_M}\s+(?:de|del)\s+(\d{{4}})', s or '')
    if not m:
        return ''
    try:
        return datetime.date(int(m.group(3)), MESES[m.group(2).lower()], int(m.group(1))).isoformat()
    except ValueError:
        return ''


def _clave(t):
    f = C.fold(t or '')
    m = re.search(r'\bpor (?:medio de )?(?:la|el) cual\b', f)
    return re.sub(r'[^a-z0-9]', '', f[m.start():] if m else f)[:90]


# ─────────────────────────── Asamblea ───────────────────────────

def _posts(cat, desde=None):
    out, p = [], 1
    while p < 60:
        q = f'{ASAMBLEA}/posts?categories={cat}&per_page=100&page={p}&_fields=id,date,link,title,content'
        if desde:
            q += f'&after={desde}T00:00:00'
        try:
            lote = json.loads(C.curl(q, timeout=90))
        except RuntimeError as e:
            if 'http=400' in str(e):
                break
            raise
        if not lote:
            break
        out += lote
        if len(lote) < 100:
            break
        p += 1
    return out


_NUM = re.compile(r'(?i)(?:ORDENANZA)\s+(?:No\.?|N[°º]\.?|n[uú]mero)?\s*0*(\d{1,4})\s+(?:DEL?\s+)?(.{0,40}?\d{4})')


def _doc(post):
    tit = _txt(post['title']['rendered'])
    m = _NUM.search(tit)
    num = m.group(1) if m else ''
    fecha = _fecha_es(m.group(2) if m else tit) or post['date'][:10]
    me = re.search(r'[“"«](.+?)[”"»]', tit)
    epi = (me.group(1) if me else tit).strip(' .,')
    pdf = re.search(r'href="([^"]+\.pdf)"', post['content']['rendered'] or '')
    return {'id': post['id'], 'numero': num, 'anio': fecha[:4], 'fecha': fecha, 'publicado': post['date'][:10],
            'titulo_original': tit, 'titulo': epi[:1].upper() + epi[1:].lower() if epi.isupper() else epi,
            'url': pdf.group(1) if pdf else post['link'], 'pagina': post['link']}


def _instancia(s):
    f = C.fold(s)
    return ('Sesión ordinaria' if 'ordinari' in f and 'extra' not in f else 'Sesión extraordinaria' if 'extra' in f
            else s.capitalize().replace('Comision', 'Comisión'))


def _acta(post):
    tit = _txt(post['title']['rendered'])
    fecha = _fecha_es(tit) or post['date'][:10]
    n = re.search(r'(?i)ACTA\s+(?:No\.?|N[°º]\.?)?\s*0*(\d{1,4})', tit)
    org = re.search(r'(?i)(COMISI[ÓO]N\s+\w+|SESI[ÓO]N(?:ES)?\s+\w+|PLENARIA)', tit)
    pdf = re.search(r'href="([^"]+\.pdf)"', post['content']['rendered'] or '')
    return {'id': post['id'], 'numero': n.group(1) if n else '', 'anio': fecha[:4], 'fecha': fecha,
            'publicado': post['date'][:10], 'titulo': tit,
            'instancia': _instancia(org.group(1)) if org else '',
            'url': pdf.group(1) if pdf else post['link'], 'pagina': post['link']}


def agenda_asamblea():
    """Sesiones del calendario público: las de 60 días atrás en adelante."""
    t = C.curl(ICS_ASAMBLEA, timeout=60).replace('\r\n ', '').replace('\n ', '')
    lim = (datetime.date.today() - datetime.timedelta(days=60)).isoformat()
    corp = 'Asamblea de Antioquia'
    des = lambda x: x.replace('\\n', ' ').replace('\\,', ',').replace('\\;', ';').strip()
    out = []
    for e in re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', t, re.S):
        g = lambda k: (re.search(rf'(?m)^{k}[^:\n]*:(.*)$', e) or [None, ''])[1].strip()
        d = re.sub(r'\D', '', g('DTSTART'))[:8]
        if len(d) < 8:
            continue
        dia = f'{d[:4]}-{d[4:6]}-{d[6:]}'
        tit = des(g('SUMMARY'))
        if dia < lim or not tit:
            continue
        out.append({'id': f"asamblea-{g('UID')[:40]}", 'titulo': tit[:200], 'dia': dia, 'fecha_inicio': dia,
                    'fecha_fin': '', 'lugar': des(g('LOCATION')) or corp, 'descripcion': des(g('DESCRIPTION'))[:600] or tit,
                    'categorias': ['Comisión' if C.fold(tit).startswith('comision') else 'Plenaria'],
                    'url': AGENDA_ASAMBLEA})
    return sorted(out, key=lambda x: x['dia'])


def asamblea(prev, todo):
    """Proyectos de ordenanza con su estado (ponencia y ordenanza), ordenanzas,
    actas de sesión y agenda."""
    desde = None
    if prev and not todo:
        desde = (datetime.date.today() - datetime.timedelta(days=120)).isoformat()
    proy = {str(x['id']): x for x in (prev or {}).get('proyectos', [])}
    ords = {str(x['id']): x for x in (prev or {}).get('ordenanzas', [])}
    pon = {str(x['id']): x for x in (prev or {}).get('ponencias', [])}
    actas = {str(x['id']): x for x in (prev or {}).get('actas', [])}
    if not actas:                     # primera vez: el archivo entero, no 120 días
        for p in _posts(217):
            d = _acta(p)
            actas[str(d['id'])] = d
    else:
        for p in _posts(217, desde):
            d = _acta(p)
            actas[str(d['id'])] = d
    for p in _posts(216, desde):
        d = _doc(p)
        proy[str(d['id'])] = d
    for p in _posts(225, desde):
        d = _doc(p)
        t = C.fold(d['titulo_original'])
        d['debate'] = ('segundo debate' if 'segundo' in t else 'primer debate' if 'primer' in t else 'ponencia')
        pon[str(d['id'])] = d
    for p in _posts(6, desde):
        d = _doc(p)
        ords[str(d['id'])] = d
    # estado de cada proyecto: la ponencia más avanzada que lo cita y, si una
    # ordenanza tiene su mismo epígrafe, «ordenanza N»
    por_num = {}
    for x in pon.values():
        por_num.setdefault((x['numero'], x['anio']), []).append(x)
    # ⚠️ los epígrafes genéricos («vigencias futuras», «modificaciones al
    # presupuesto») se repiten cada año: la ordenanza tiene que ser POSTERIOR al
    # proyecto y de menos de un año después, o se enlazaba con una de 2017
    ord_por_clave = {}
    for o in ords.values():
        if o['titulo']:
            ord_por_clave.setdefault(_clave(o['titulo']), []).append(o)

    def _ord_de(x):
        try:
            f0 = datetime.date.fromisoformat(x['fecha'])
        except ValueError:
            return None
        cands = []
        for o in ord_por_clave.get(_clave(x['titulo']), []):
            try:
                d = (datetime.date.fromisoformat(o['fecha']) - f0).days
            except ValueError:
                continue
            if 0 <= d <= 365:
                cands.append((d, o))
        return min(cands, key=lambda t: t[0])[1] if cands else None
    for x in proy.values():
        ps = por_num.get((x['numero'], x['anio']), [])
        x['ponencias'] = sorted({p['debate'] for p in ps})
        o = _ord_de(x)
        if o:
            x['estado'] = f"Aprobado · Ordenanza {o['numero']} de {o['anio']}"
            x['ordenanza'] = {'numero': o['numero'], 'anio': o['anio'], 'url': o['url']}
        elif 'segundo debate' in x['ponencias']:
            x['estado'] = 'Ponencia para segundo debate'
        elif 'primer debate' in x['ponencias'] or 'ponencia' in x['ponencias']:
            x['estado'] = 'Ponencia para primer debate'
        else:
            x['estado'] = 'Radicado'
    return {'proyectos': sorted(proy.values(), key=lambda x: x['fecha'], reverse=True),
            'ponencias': sorted(pon.values(), key=lambda x: x['fecha'], reverse=True),
            'ordenanzas': sorted(ords.values(), key=lambda x: x['fecha'], reverse=True),
            'actas': sorted(actas.values(), key=lambda x: x['fecha'], reverse=True),
            'eventos': agenda_asamblea()}


# ─────────────────────────── Concejo (SIMI) ───────────────────────────

class Simi:
    def __init__(self, pagina):
        self.url = f'{SIMI}/{pagina}.xhtml'
        self.jar = tempfile.NamedTemporaryFile(prefix='simi-', suffix='.jar', delete=False).name
        h = self._curl()
        m = re.search(r'name="jakarta\.faces\.ViewState"[^>]*value="([^"]+)"', h)
        if not m:
            raise RuntimeError(f'{pagina}: sin ViewState')
        self.vs = m.group(1)
        t = re.search(r'pf\.cw\("DataTable","[^"]+",\{id:"([^"]+)".*?rowCount:(\d+)', h, re.S)
        if not t:
            raise RuntimeError(f'{pagina}: sin tabla')
        self.tabla, self.total = t.group(1), int(t.group(2))
        f = re.search(r'<form id="([^"]+)"[^>]*>(?:(?!</form>).)*?id="' + re.escape(self.tabla) + '"', h, re.S)
        self.form = f.group(1) if f else 'formappList'
        self.primera = h

    def _curl(self, data=None):
        cmd = ['/usr/bin/curl', '-s', '--max-time', '60', '-A', C.UA, '-c', self.jar, '-b', self.jar, self.url]
        if data:
            cmd += ['-H', 'Faces-Request: partial/ajax', '-H', 'X-Requested-With: XMLHttpRequest',
                    '--data', urllib.parse.urlencode(data)]
        r = subprocess.run(cmd, capture_output=True, timeout=90)
        time.sleep(0.6)
        return r.stdout.decode('utf-8', 'replace')

    def pagina(self, primero):
        if primero == 0:
            return self.primera
        T = self.tabla
        d = {self.form: self.form, 'jakarta.faces.partial.ajax': 'true', 'jakarta.faces.source': T,
             'jakarta.faces.partial.execute': T, 'jakarta.faces.partial.render': T, T: T,
             T + '_pagination': 'true', T + '_first': str(primero), T + '_rows': '10',
             T + '_skipChildren': 'true', T + '_encodeFeature': 'true', 'jakarta.faces.ViewState': self.vs}
        return self._curl(d)

    def filas(self, hasta=None, para=None):
        """Filas como listas de celdas de texto, y en `self.claves` el `data-rk` de
        cada una. `para(celdas)` True corta."""
        out = []
        self.claves = []
        for primero in range(0, min(self.total, hasta or self.total), 10):
            h = self.pagina(primero)
            rows = re.findall(r'<tr[^>]*data-ri="\d+"(?:[^>]*data-rk="(\d+)")?[^>]*>(.*?)</tr>', h, re.S)
            if not rows:
                break
            corta = False
            for rk, r in rows:
                r = re.sub(r'<script.*?</script>', '', r, flags=re.S)
                celdas = [_txt(c) for c in re.findall(r'<td[^>]*>(.*?)</td>', r, re.S)]
                out.append(celdas)
                self.claves.append(rk)
                if para and para(celdas):
                    corta = True
            if corta:
                break
        return out


def _num_anio(s):
    m = re.search(r'(\d{1,4})\s*-\s*(\d{4})', s or '')
    return (m.group(1), m.group(2)) if m else ('', '')


def ficha_concejo(simi_id, numero, anio):
    """Proponentes y ponentes de la ficha pública. None si la ficha no es de ese
    proyecto: la página responde 200 igual, con otros proyectos debajo."""
    h = C.curl(FICHA_CONCEJO + simi_id, timeout=40)
    t = _txt(re.sub(r'<script.*?</script>|<style.*?</style>', '', h, flags=re.S))
    m = re.search(rf'No\. proyecto:\s*{numero}-{anio}\s+Proponentes:\s*(.*?)\s+Ponentes:\s*(.*?)\s+Ver proyecto', t)
    time.sleep(1)
    return {'proponentes': m.group(1)[:200], 'ponentes': m.group(2)[:300]} if m else None


def concejo(prev=None):
    hoy = datetime.date.today()
    corte = str(hoy.year - 2)
    s = Simi('proyectos/proyectos')
    proyectos = []
    previos = {x.get('simi_id'): x for x in (prev or {}).get('proyectos', []) if x.get('simi_id')}
    consultas = 0
    for c, rk in zip(s.filas(), s.claves):
        if len(c) < 3:
            continue
        n, a = _num_anio(c[0])
        x = {'numero': n, 'anio': a, 'titulo': c[1], 'estado': c[2], 'pagina': s.url, 'simi_id': rk}
        p = previos.get(rk) or {}
        x.update({k: p[k] for k in ('proponentes', 'ponentes', 'sin_ficha') if k in p})
        # solo lo vivo, y solo si cambió de estado: los archivados ya no cambian de ponentes
        vivo = a >= str(hoy.year - 1) and not re.search(r'(?i)archiv|retirad|negad|sancionad', c[2])
        if rk and vivo and consultas < 60 and (p.get('estado') != c[2] or not ('ponentes' in p or 'sin_ficha' in p)):
            consultas += 1
            x.pop('sin_ficha', None)
            try:
                f = ficha_concejo(rk, n, a)
                x.update(f or {'sin_ficha': True})
            except RuntimeError as e:
                print(f'    ! ficha {n}-{a}: {str(e)[:80]}', file=sys.stderr)
        if 'ponentes' in x and 'sin_ficha' not in x:
            x['pagina'] = FICHA_CONCEJO + rk
        proyectos.append(x)
    s = Simi('proyectos/acuerdos')
    acuerdos = []
    for c in s.filas(para=lambda c: _num_anio(c[0])[1] and _num_anio(c[0])[1] < corte):
        if len(c) < 4:
            continue
        n, a = _num_anio(c[0])
        pn, pa = _num_anio(c[1])
        acuerdos.append({'numero': n, 'anio': a, 'proyecto': f'{pn}-{pa}' if pn else '', 'titulo': c[2],
                         'estado': c[3], 'pagina': s.url})
    s = Simi('proposiciones/citaciones')
    citaciones = []
    for c in s.filas(para=lambda c: (_fecha_es(c[0]) or '9999') < f'{corte}-01-01'):
        if len(c) < 4:
            continue
        resto = [x for x in c[4:] if x and x != 'ui-button']
        citaciones.append({'fecha': _fecha_es(c[0]), 'sesion': c[1], 'codigo': c[2], 'titulo': c[3].strip(' “”"'),
                           'estado': resto[0] if resto else '', 'pagina': s.url})
    eventos = []
    s = Simi('plenaria/debates')
    lim = (hoy - datetime.timedelta(days=60)).isoformat()
    for c in s.filas(para=lambda c: (_fecha_es(c[1]) or '9999') < lim):
        if len(c) < 3:
            continue
        dia = _fecha_es(c[1])
        cuerpo = ' '.join(x for x in c[3:] if x and x != 'ui-button')
        tipo = next((x for x in c[3:] if x in ('Citación', 'Invitación', 'Proyecto de acuerdo', 'Debate')), '')
        tema = re.sub(r'^(Citación|Invitación)\s*', '', cuerpo).strip()
        eventos.append({'id': f'plenaria-{c[0]}', 'titulo': f'Sesión plenaria {c[0]}' + (f' · {tema[:160]}' if tema else ''),
                        'dia': dia, 'fecha_inicio': dia, 'fecha_fin': '', 'lugar': f'Concejo de Medellín · {c[2]}',
                        'descripcion': tema[:600], 'categorias': ['Plenaria'] + ([tipo] if tipo else []),
                        'url': s.url})
    s = Simi('proyectos/permanente')
    for c in s.filas():
        if len(c) < 6:
            continue
        dia = _fecha_es(c[3])
        eventos.append({'id': f'comision-{C.fold(c[0])[:40]}-{dia}', 'titulo': f'{c[1]} · {c[0]}', 'dia': dia,
                        'fecha_inicio': dia, 'fecha_fin': '', 'lugar': f'{c[2]} · {c[4]} a {c[5]}',
                        'descripcion': c[0], 'categorias': ['Comisión permanente'] + ([c[6]] if len(c) > 6 else []),
                        'url': s.url})
    return {'proyectos': proyectos, 'acuerdos': acuerdos, 'citaciones': citaciones, 'eventos': eventos}


def fetch(todo):
    OUT.mkdir(parents=True, exist_ok=True)
    gen = datetime.datetime.now().isoformat(timespec='seconds')
    ok = True
    try:
        prev = C.leer(OUT / 'asamblea.json', None)
        a = asamblea(prev, todo)
        if len(a['proyectos']) < 50 or len(a['ordenanzas']) < 50 or len(a['actas']) < 50:
            raise RuntimeError(f"solo {len(a['proyectos'])} proyectos, {len(a['ordenanzas'])} ordenanzas "
                               f"y {len(a['actas'])} actas")
        C.escribir(OUT / 'asamblea.json', {'generado': gen, **a})
        print(f"  asamblea · {len(a['proyectos'])} proyectos · {len(a['ponencias'])} ponencias · "
              f"{len(a['ordenanzas'])} ordenanzas · {len(a['actas'])} actas · {len(a['eventos'])} sesiones "
              f"({sum(1 for e in a['eventos'] if e['dia'] >= datetime.date.today().isoformat())} por venir)")
    except Exception as e:
        ok = False
        print(f'  asamblea · FALLÓ ({e}) — se conserva el archivo anterior', file=sys.stderr)
    try:
        c = concejo(C.leer(OUT / 'concejo.json', None))
        if len(c['proyectos']) < 100:
            raise RuntimeError(f"solo {len(c['proyectos'])} proyectos (SIMI tiene más de 300)")
        C.escribir(OUT / 'concejo.json', {'generado': gen, **c})
        hoy = datetime.date.today().isoformat()
        print(f"  concejo · {len(c['proyectos'])} proyectos · {len(c['acuerdos'])} acuerdos · "
              f"{len(c['citaciones'])} citaciones · {len(c['eventos'])} sesiones y reuniones "
              f"({sum(1 for e in c['eventos'] if e['dia'] >= hoy)} por venir)")
    except Exception as e:
        ok = False
        print(f'  concejo · FALLÓ ({e}) — se conserva el archivo anterior', file=sys.stderr)
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('fetch')
    f.add_argument('--todo', action='store_true', help='Asamblea: relee todo, no solo 120 días')
    a = ap.parse_args()
    if a.cmd == 'fetch':
        sys.exit(0 if fetch(a.todo) else 1)


if __name__ == '__main__':
    main()
