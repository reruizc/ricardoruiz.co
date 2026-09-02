#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mi Congreso · Alertas — el push del tablero del congresista.

Para cada suscripción confirmada (worker rr-auth, `/micongreso/alertas/*`)
compara lo que hoy dicen las fuentes públicas contra lo que ya se le avisó, y
manda UN correo solo si hay algo nuevo:

  · un proyecto que firma CAMBIÓ DE ESTADO (o apareció por primera vez),
  · uno de sus proyectos ENTRÓ A UN ORDEN DEL DÍA vigente,
  · su comisión (o la plenaria de su cámara) tiene sesión publicada.

La primera corrida de cada suscripción manda un «así va tu curul hoy» con la
foto completa y sella el snapshot; desde ahí solo se avisa lo que se mueve.
Sin novedades no hay correo: un digest vacío mata el canal.

Fuentes (todas públicas, ninguna depende del disco local):
  · action:'radicados' de la Lambda caudal-analiza   → proyectos + estado
  · ordenes-vigentes.json (S3)                        → sesiones publicadas
  · comisiones-2026.json (S3)                         → la comisión de cada quien
  · legislativo-electos.js (este repo)                → nombre canónico y cámara

El snapshot por suscripción (`visto`) vive en el registro del worker, no en
disco, porque esto corre en GitHub Actions (ver .github/workflows/mi-congreso-
alertas.yml) y ahí no hay disco entre corridas.

Uso:
  CAUDAL_ALERTAS_TOKEN=… python3 motor.py                 # corrida real
  python3 motor.py --dry-run                              # no manda ni sella
  python3 motor.py --dry-run --inventario prueba.json     # sin worker (pruebas)
  python3 motor.py --dry-run --guardar-html /tmp/out      # deja los HTML
  python3 motor.py --solo correo@dominio.co               # una sola suscripción
"""
import argparse
import datetime as dt
import html as _html
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
WORKER = os.environ.get('CAUDAL_WORKER_URL', 'https://rr-auth.reruizc.workers.dev')
API = os.environ.get('CAUDAL_API_URL', 'https://l3kmprdjkl.execute-api.us-east-1.amazonaws.com')
S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output'
URL_ORDENES = S3 + '/legislativo/ordenes-vigentes.json'
URL_COMISIONES = S3 + '/legislativo/comisiones-2026.json'
HEADER = 'X-Caudal-Service'
UA = 'mi-congreso-alertas/1.0 (+ricardoruiz.co)'
BOGOTA = ZoneInfo('America/Bogota')
SITIO = 'https://ricardoruiz.co/mi-congreso.html'
MAX_AGENDA_VISTA = 400      # ids de sesiones recordadas por suscripción
MESES = ['', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


# ── utilidades de texto ─────────────────────────────────────────────────────
def norm(s):
    s = unicodedata.normalize('NFD', str(s or ''))
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()


_STOP = {'de', 'del', 'la', 'los', 'las', 'y', 'e'}


def toks(s):
    """Tokens de un nombre, sin partículas ni prefijos de cámara (H.S./H.R.)."""
    out = []
    for t in re.split(r'[^a-z0-9ñ]+', norm(s)):
        if len(t) > 2 and t not in _STOP and not re.fullmatch(r'h\.?[sr]\.?', t):
            out.append(t)
    return out


def misma_persona(a, b):
    """Mismo criterio que mi-congreso.html: el nombre más corto cabe entero en
    el largo y comparten al menos dos tokens (un apellido solo casa homónimos)."""
    A, B = toks(a), toks(b)
    if len(A) < 2 or len(B) < 2:
        return False
    corto, largo = (A, B) if len(A) <= len(B) else (B, A)
    return all(t in largo for t in corto)


_SOLO_CARGO = re.compile(r'^(?:ministr|viceministr|director|superintendent|defensor|'
                         r'procurador|fiscal|contralor|registrador|presidenta?\b|'
                         r'gobernador|alcald)', re.I)


def autores_de(txt):
    """Port de autoresDe() de legislativo-base.js: el campo `autor` no tiene
    convención estable (Senado pega el prefijo H.R. sin coma; Cámara antepone el
    cargo separado por coma)."""
    s = re.sub(r'\s+', ' ', str(txt or '')).strip()
    if not s:
        return []
    s = re.sub(r'\s(H\.?\s?[SR]\.?)\s', r', \1 ', s, flags=re.I)
    out = []
    for p in [x.strip() for x in s.split(',') if x.strip()]:
        limpio = re.sub(r'^H\.?\s?[SR]\.?\s*', '', p, flags=re.I).strip()
        if not limpio:
            continue
        if _SOLO_CARGO.match(limpio):
            out.append({'cargo': limpio, 'nombre': ''})
            continue
        if out and out[-1]['cargo'] and not out[-1]['nombre']:
            out[-1]['nombre'] = limpio
            continue
        out.append({'cargo': '', 'nombre': limpio})
    return [a['nombre'] or a['cargo'] for a in out]


def nice(n):
    n = str(n or '')
    return n.title() if n == n.upper() else n


_PREF = re.compile(r'^\s*por\s+(?:medio\s+de\s+)?(?:el\s+medio\s+de\s+)?(?:la|el|los|las)?\s*cual(?:es)?\s+se\s+', re.I)


def titulo_corto(t):
    s = re.sub(r'\s+', ' ', _PREF.sub('', str(t or ''))).strip()
    if len(s) < 6:
        s = re.sub(r'\s+', ' ', str(t or '')).strip()
    if re.match(r'^\d+\s+de\s+\d{4}', s, re.I):
        return s
    return s[:1].upper() + s[1:].lower()


def recortar(s, n):
    s = (s or '').strip()
    if len(s) <= n:
        return s
    c = s[:n]
    i = c.rfind(' ')
    if i > n * 0.6:
        c = c[:i]
    return c.rstrip(' ,;:.-·') + '…'


def e(s):
    return _html.escape(str(s or ''), quote=True)


def fecha_larga(f):
    try:
        d = dt.date.fromisoformat(str(f)[:10].replace('/', '-'))
        return f'{d.day} de {MESES[d.month]}'
    except (ValueError, IndexError):
        return str(f or '')


# ── números de proyecto ─────────────────────────────────────────────────────
def num_norm(s):
    """'152 de 2026 Cámara' · '276/2026C' · '213/26' · '232 de 2025' →
    ('152','26','C') · ('276','26','C') · ('213','26',None) · ('232','25',None).
    El número se lleva sin ceros a la izquierda; el año a dos dígitos."""
    s = norm(s)
    m = re.search(r'(\d{1,4})\s*(?:/|de)\s*(\d{2,4})\s*([a-z]*)', s)
    if not m:
        return None
    n = str(int(m.group(1)))
    y = m.group(2)[-2:]
    c = m.group(3)
    cam = 'C' if c.startswith('c') else 'S' if c.startswith('s') else None
    return (n, y, cam)


def num_casa(a, b):
    """Mismo proyecto si coinciden número y año, y la cámara no se contradice."""
    if not a or not b:
        return False
    return a[0] == b[0] and a[1] == b[1] and (a[2] is None or b[2] is None or a[2] == b[2])


# ── red ─────────────────────────────────────────────────────────────────────
def http_json(url, data=None, headers=None, timeout=60):
    h = {'User-Agent': UA, 'Accept': 'application/json'}
    if headers:
        h.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data).encode('utf-8')
        h['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=body, headers=h, method='POST' if data is not None else 'GET')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def token():
    return os.environ.get('CAUDAL_ALERTAS_TOKEN', '').strip()


def worker(path, data=None):
    return http_json(WORKER + path, data=data, headers={HEADER: token()})


# ── fuentes ─────────────────────────────────────────────────────────────────
def cargar_electos():
    src = open(os.path.join(REPO, 'legislativo-electos.js'), encoding='utf-8').read()
    m = re.search(r'const ELECTOS_RAW=(\[.*?\]);', src, re.S)
    arr = json.loads(m.group(1))
    return [{'corp': 'SENADO' if r[0] == 'S' else 'CAMARA', 'nombre': r[1], 'partido': r[2], 'dep': r[3]} for r in arr]


def electo_de(sub, electos):
    """El nombre guardado en la suscripción se canoniza contra el listado."""
    n = norm(sub.get('congresista'))
    corp = sub.get('corp')
    for x in electos:
        if x['corp'] == corp and norm(x['nombre']) == n:
            return x
    for x in electos:
        if x['corp'] == corp and misma_persona(x['nombre'], sub.get('congresista')):
            return x
    return None


def cargar_radicados():
    d = http_json(API, data={'action': 'radicados'})
    out = []
    for r in d.get('radicados', []):
        out.append(dict(r, _cam='Senado', _num=r.get('numero_senado') or r.get('numero_camara') or ''))
    for r in d.get('radicados_camara', []):
        out.append(dict(r, _cam='Cámara', _num=r.get('numero_camara') or r.get('numero_senado') or ''))
    return out


def cargar_ordenes():
    d = http_json(URL_ORDENES + '?v=' + str(int(dt.datetime.now().timestamp() // 300)))
    return d.get('ordenes', [])


def cargar_comisiones():
    try:
        return http_json(URL_COMISIONES + '?v=' + str(int(dt.datetime.now().timestamp() // 3600))).get('comisiones', {})
    except Exception:
        return {}


def comision_de(electo, comisiones):
    corp = 'senado' if electo['corp'] == 'SENADO' else 'camara'
    for k, v in comisiones.items():
        if any(misma_persona(m.get('nombre'), electo['nombre']) for m in (v or {}).get(corp, [])):
            return k
    return None


# ── el cálculo ──────────────────────────────────────────────────────────────
def proyectos_de(electo, radicados):
    """Los proyectos donde firma, con marca de primera firma."""
    out = []
    for r in radicados:
        auts = autores_de(r.get('autor'))
        idx = next((i for i, a in enumerate(auts) if misma_persona(a, electo['nombre'])), -1)
        if idx < 0:
            continue
        tok = ('S:' if r['_cam'] == 'Senado' else 'C:') + str(r['_num'])
        out.append({
            'tok': tok, 'num': r['_num'], 'cam': r['_cam'],
            'titulo': titulo_corto(r.get('titulo')), 'estado': (r.get('estado') or '').strip(),
            'comision': (r.get('comision') or '').strip(), 'fecha': r.get('fecha') or '',
            'primero': idx == 0, 'n_firmas': len(auts), 'fuente': r.get('fuente_url') or '',
            '_numn': num_norm(r['_num']),
        })
    return out


def hoy_bogota():
    return dt.datetime.now(BOGOTA).date()


def eventos_de(sub, electo, proyectos, ordenes, comision):
    """Devuelve (eventos, visto_nuevo, es_primera). Los eventos van agrupados en
    tres listas: proyectos (nuevo/cambio), agenda_propia (mis proyectos en un
    orden del día) y agenda_comision (sesiones de mi comisión/plenaria)."""
    visto = sub.get('visto') or {}
    v_proy = visto.get('proyectos') or {}
    v_agenda = set(visto.get('agenda') or [])
    primera = not v_proy and not v_agenda

    ev_proy = []
    for p in proyectos:
        prev = v_proy.get(p['tok'])
        if prev is None:
            ev_proy.append(dict(p, tipo='nuevo'))
        elif (prev.get('estado') or '') != p['estado']:
            ev_proy.append(dict(p, tipo='cambio', estado_previo=prev.get('estado') or ''))

    hoy = hoy_bogota().isoformat()
    corp_re = re.compile('senado' if electo['corp'] == 'SENADO' else r'c[aá]mara', re.I)
    com_re = re.compile(comision.lower().replace('septima', 'séptima|septima'), re.I) if comision else None
    ev_propia, ev_com = [], []
    for o in ordenes:
        if (o.get('fecha_fin') or o.get('fecha') or '') < hoy or not o.get('url'):
            continue
        if not corp_re.search(o.get('corporacion') or ''):
            continue
        oid = o.get('id') or (o.get('url') + o.get('fecha', ''))
        mios = []
        for pr in o.get('proyectos') or []:
            nn = num_norm(pr.get('numero'))
            for p in proyectos:
                if num_casa(nn, p['_numn']):
                    mios.append(p)
        ambito = o.get('ambito') or ''
        es_mia = bool(com_re and com_re.search(ambito)) or bool(re.search(r'plenaria', ambito, re.I))
        if mios:
            k = oid + '|' + ','.join(sorted(set(p['tok'] for p in mios)))
            if k not in v_agenda:
                ev_propia.append({'orden': o, 'proyectos': mios, 'k': k})
        elif es_mia:
            if oid not in v_agenda:
                ev_com.append({'orden': o, 'k': oid})

    # snapshot nuevo: todo lo que existe hoy + lo avisado
    visto_nuevo = {
        'proyectos': {p['tok']: {'estado': p['estado'], 't': recortar(p['titulo'], 80)} for p in proyectos},
        'agenda': (list(v_agenda) + [x['k'] for x in ev_propia] + [x['k'] for x in ev_com])[-MAX_AGENDA_VISTA:],
        'sellado': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
    }
    return {'proyectos': ev_proy, 'agenda_propia': ev_propia, 'agenda_comision': ev_com}, visto_nuevo, primera


# ── render ──────────────────────────────────────────────────────────────────
BG, CARD, BORDE, TEXTO, TENUE, VERDE, AZUL, AMBAR = (
    '#060810', '#0d1018', '#1c2130', '#e8eaf0', '#8d93a6', '#4ade80', '#3d6fff', '#e0a03a')


def _fila(titulo, meta, marca=''):
    return (f'<tr><td style="padding:10px 0;border-bottom:1px solid {BORDE};vertical-align:top;">'
            f'<div style="font-size:14px;line-height:1.45;color:{TEXTO};">{marca}{titulo}</div>'
            f'<div style="font-size:11px;line-height:1.5;color:{TENUE};margin-top:3px;">{meta}</div></td></tr>')


def _bloque(kicker, filas, nota=''):
    if not filas:
        return ''
    return (f'<div style="margin-top:26px;"><p style="font-size:11px;letter-spacing:.16em;text-transform:uppercase;'
            f'color:{VERDE};margin:0 0 6px;">{e(kicker)}</p><table role="presentation" cellpadding="0" cellspacing="0" '
            f'style="width:100%;border-collapse:collapse;">{"".join(filas)}</table>'
            + (f'<p style="font-size:11px;color:{TENUE};line-height:1.55;margin:8px 0 0;">{nota}</p>' if nota else '')
            + '</div>')


def _proy_meta(p):
    partes = [e(p['cam'])]
    if p['comision']:
        partes.append('Comisión ' + e(p['comision'].title()))
    if p['estado']:
        partes.append(e(p['estado']))
    partes.append('firma solo' if p['n_firmas'] == 1 else f"{p['n_firmas']} firmantes")
    if p['fuente']:
        partes.append(f'<a href="{e(p["fuente"])}" style="color:{AZUL};text-decoration:none;">fuente ↗</a>')
    return ' · '.join(partes)


def render(sub, electo, eventos, proyectos, primera, comision):
    nombre = nice(electo['nombre'])
    hoy = hoy_bogota()
    fecha = f'{hoy.day} de {MESES[hoy.month]} de {hoy.year}'
    n_proy, n_prop, n_com = (len(eventos['proyectos']), len(eventos['agenda_propia']), len(eventos['agenda_comision']))

    if primera:
        titulo, kicker = 'Así va tu curul hoy', 'Primer resumen · desde aquí solo te avisamos lo que se mueva'
    else:
        partes = []
        if n_proy:
            partes.append(f'{n_proy} proyecto{"s" if n_proy > 1 else ""} con movimiento')
        if n_prop:
            partes.append(f'{n_prop} sesión{"es" if n_prop > 1 else ""} con un proyecto tuyo')
        if n_com:
            partes.append(f'{n_com} sesión{"es" if n_com > 1 else ""} de tu comisión')
        titulo, kicker = ' · '.join(partes).capitalize(), f'Alerta · {fecha}'

    filas = []
    for p in (proyectos if primera else eventos['proyectos']):
        marca = '<span style="color:%s;">★</span> ' % AMBAR if p['primero'] else ''
        if not primera and p.get('tipo') == 'cambio':
            marca += f'<span style="font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:{AMBAR};">cambió de estado</span> '
            meta = f'antes: {e(p["estado_previo"] or "—")} → ahora: <b style="color:{TEXTO};">{e(p["estado"])}</b> · ' + _proy_meta(p)
        else:
            if not primera:
                marca += f'<span style="font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:{VERDE};">nuevo en el registro</span> '
            meta = _proy_meta(p)
        filas.append(_fila(f'<span style="color:{TENUE};">{e(p["num"])}</span> · {e(recortar(p["titulo"], 170))}', meta, marca))
    if primera:
        b1 = _bloque(f'Los {len(proyectos)} proyectos que firmas en esta legislatura' if proyectos else 'Tus proyectos', filas,
                     'Sin proyectos a tu nombre en el registro todavía: te avisamos apenas aparezca el primero.' if not proyectos else
                     '★ = primera firma (autor principal).')
    else:
        b1 = _bloque('Tus proyectos', filas, '★ = primera firma (autor principal).')

    filas = []
    for x in eventos['agenda_propia']:
        o = x['orden']
        nums = ', '.join(e(p['num']) for p in x['proyectos'])
        filas.append(_fila(f'{e(fecha_larga(o.get("fecha")))} · {e(o.get("ambito") or o.get("corporacion"))}',
                           f'En el orden del día va{"n" if len(x["proyectos"]) > 1 else ""} <b style="color:{TEXTO};">{nums}</b>' +
                           f' · <a href="{e(o.get("url"))}" style="color:{AZUL};text-decoration:none;">documento oficial ↗</a>'))
    b2 = _bloque('Un proyecto tuyo en el orden del día', filas)

    filas = []
    for x in eventos['agenda_comision']:
        o = x['orden']
        ps = [pr for pr in (o.get('proyectos') or []) if pr.get('titulo')]
        det = ' · '.join(e(recortar(titulo_corto(pr['titulo']), 90)) for pr in ps[:3]) + (f' · y {len(ps) - 3} más' if len(ps) > 3 else '')
        filas.append(_fila(f'{e(fecha_larga(o.get("fecha")))} · {e(o.get("ambito") or o.get("corporacion"))}' + (f' · {len(ps)} proyecto{"s" if len(ps) != 1 else ""}' if ps else ''),
                           (det + ' · ' if det else '') + f'<a href="{e(o.get("url"))}" style="color:{AZUL};text-decoration:none;">documento oficial ↗</a>'))
    b3 = _bloque('Sesiones publicadas de tu comisión y la plenaria', filas)

    com_txt = f'Comisión {comision.title()}' if comision and comision != 'ACUSACIONES' else ('Investigación y Acusación' if comision else 'sin comisión en nuestro registro')
    cuerpo = (f'<p style="font-size:14px;line-height:1.7;color:#a9aec0;margin:0;">'
              f'<strong style="color:{TEXTO};">{e(nombre)}</strong> · {"Senado" if electo["corp"] == "SENADO" else "Cámara"} · {e(com_txt)}.</p>'
              + b1 + b2 + b3 +
              f'<p style="margin:30px 0 0;"><a href="{SITIO}" style="display:inline-block;background:{VERDE};color:#06210f;padding:12px 22px;'
              f'text-decoration:none;font-size:12px;letter-spacing:.1em;text-transform:uppercase;font-weight:700;">Abrir mi tablero →</a></p>'
              f'<p style="font-size:11px;color:#5a6070;line-height:1.6;margin:24px 0 0;">Fuentes: registros de radicados de Senado y Cámara y órdenes del día publicados por las secretarías, '
              f'leídos por el rastreo diario. Cámara publica con rezago de días. '
              f'<a href="{e(sub.get("baja_url") or SITIO)}" style="color:{TENUE};">Dejar de recibir estas alertas</a>.</p>')

    html_doc = (f'<!DOCTYPE html><html><head><meta charset="UTF-8"/></head><body style="background:{BG};color:{TEXTO};font-family:Helvetica,Arial,sans-serif;padding:40px 20px;margin:0;">'
                f'<div style="max-width:560px;margin:0 auto;"><div style="margin-bottom:26px;"><span style="font-weight:800;font-size:18px;letter-spacing:-0.02em;">Ricardo<span style="color:#0047FF;">.</span>Ruiz</span>'
                f' <span style="font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:{TENUE};margin-left:10px;">Mi Congreso</span></div>'
                f'<div style="border-left:3px solid {VERDE};padding-left:18px;margin-bottom:24px;"><p style="font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:{VERDE};margin:0 0 8px;">{e(kicker)}</p>'
                f'<h1 style="font-weight:800;font-size:26px;letter-spacing:-0.03em;margin:0;line-height:1.05;">{e(titulo)}</h1></div>{cuerpo}'
                f'<div style="margin-top:36px;padding-top:18px;border-top:1px solid {BORDE};"><p style="font-size:10px;letter-spacing:.1em;color:#4a5060;text-transform:uppercase;margin:0;">ricardoruiz.co · Mi Congreso · Bogotá, Colombia</p></div></div></body></html>')

    # texto plano
    lineas = [f'Mi Congreso · {titulo}', f'{nombre} · {com_txt}', '']
    for p in (proyectos if primera else eventos['proyectos']):
        tag = '' if primera else ('[cambió de estado] ' if p.get('tipo') == 'cambio' else '[nuevo] ')
        lineas.append(f'- {tag}{p["num"]} · {recortar(p["titulo"], 120)} · {p["estado"]}')
    for x in eventos['agenda_propia']:
        o = x['orden']
        lineas.append(f'- {fecha_larga(o.get("fecha"))} · {o.get("ambito")} · va {", ".join(p["num"] for p in x["proyectos"])} · {o.get("url")}')
    for x in eventos['agenda_comision']:
        o = x['orden']
        lineas.append(f'- {fecha_larga(o.get("fecha"))} · {o.get("ambito")} · {o.get("url")}')
    lineas += ['', f'Tablero: {SITIO}', f'Dejar de recibir: {sub.get("baja_url") or SITIO}']
    asunto = f'Mi Congreso · {titulo}'
    return asunto, html_doc, '\n'.join(lineas)


# ── corrida ─────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dry-run', action='store_true', help='no manda correos ni sella el snapshot')
    ap.add_argument('--inventario', help='JSON local con {suscripciones:[…]} en vez del worker')
    ap.add_argument('--guardar-html', help='carpeta donde dejar cada correo renderizado')
    ap.add_argument('--solo', help='solo la suscripción con este correo')
    ap.add_argument('--forzar-primera', action='store_true', help='trata cada suscripción como primera corrida (ignora el snapshot)')
    a = ap.parse_args()

    if a.inventario:
        inv = json.load(open(a.inventario, encoding='utf-8'))
    else:
        if not token():
            print('ERROR: falta CAUDAL_ALERTAS_TOKEN en el entorno', file=sys.stderr)
            return 2
        inv = worker('/micongreso/alertas/inventario')
    subs = inv.get('suscripciones', [])
    if a.solo:
        subs = [s for s in subs if (s.get('correo') or '').lower() == a.solo.lower()]
    print(f'suscripciones confirmadas: {len(subs)} · {inv.get("resumen", {})}')
    if not subs:
        return 0

    electos = cargar_electos()
    radicados = cargar_radicados()
    ordenes = cargar_ordenes()
    comisiones = cargar_comisiones()
    print(f'fuentes: {len(radicados)} radicados · {len(ordenes)} órdenes vigentes · {len(comisiones)} comisiones')

    enviados = silencios = errores = 0
    for sub in subs:
        etiqueta = f'{sub.get("correo")} → {sub.get("congresista")}'
        electo = electo_de(sub, electos)
        if not electo:
            print(f'  ✗ {etiqueta}: el congresista no está en el listado de electos, se omite')
            errores += 1
            continue
        if a.forzar_primera:
            sub = dict(sub, visto={})
        comision = comision_de(electo, comisiones) or ''
        proyectos = proyectos_de(electo, radicados)
        eventos, visto_nuevo, primera = eventos_de(sub, electo, proyectos, ordenes, comision)
        hay = primera or any(eventos.values())
        if not hay:
            silencios += 1
            print(f'  · {etiqueta}: sin novedades ({len(proyectos)} proyectos, snapshot al día)')
            continue
        asunto, html_doc, texto = render(sub, electo, eventos, proyectos, primera, comision)
        resumen = (f'primera corrida · {len(proyectos)} proyectos' if primera else
                   f'{len(eventos["proyectos"])} proy · {len(eventos["agenda_propia"])} propias · {len(eventos["agenda_comision"])} comisión')
        if a.guardar_html:
            os.makedirs(a.guardar_html, exist_ok=True)
            ruta = os.path.join(a.guardar_html, re.sub(r'[^a-z0-9]+', '-', norm(sub.get('correo'))) + '.html')
            open(ruta, 'w', encoding='utf-8').write(html_doc)
            print(f'    html → {ruta}')
        if a.dry_run:
            print(f'  ○ {etiqueta}: [dry-run] "{asunto}" · {resumen}')
            continue
        try:
            r = worker('/micongreso/alertas/enviar', {'id': sub['id'], 'asunto': asunto, 'html': html_doc, 'texto': texto})
        except urllib.error.HTTPError as ex:
            print(f'  ✗ {etiqueta}: envío HTTP {ex.code} {ex.read()[:200]!r}')
            errores += 1
            continue
        except Exception as ex:
            print(f'  ✗ {etiqueta}: envío falló: {ex}')
            errores += 1
            continue
        if not r.get('ok'):
            print(f'  ✗ {etiqueta}: {r.get("error")}')
            errores += 1
            continue
        # el snapshot solo se sella cuando Resend aceptó el correo: si se
        # pierde, la señal vuelve a salir mañana en vez de perderse
        try:
            worker('/micongreso/alertas/estado', {'id': sub['id'], 'visto': visto_nuevo,
                                                  'ultimoEnvio': visto_nuevo['sellado']})
        except Exception as ex:
            print(f'  ! {etiqueta}: correo enviado pero el snapshot no se guardó ({ex}) — mañana puede repetir')
        enviados += 1
        print(f'  ✓ {etiqueta}: "{asunto}" · {resumen} · resend {r.get("id")}')

    print(f'listo · enviados {enviados} · en silencio {silencios} · errores {errores}')
    return 1 if errores and not enviados and not silencios else 0


if __name__ == '__main__':
    sys.exit(main())
