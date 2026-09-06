#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Candidato 360 · Briefing cada 3 días — el push del CRM.

Para cada cuenta vinculada con el briefing ENCENDIDO (worker rr-auth,
`/c360/briefing/*`), arma un correo con lo que pasó en SU territorio desde el
último envío y lo manda. Tres secciones, las tres sobre fuentes que ya
funcionan en Caudal (Lambda caudal-analiza), leyendo el territorio del vínculo:

  · La conversación · prensa nacional y regional del municipio o la localidad,
    separada entre lo que NOMBRA al candidato y lo que habla del territorio.
  · La plata · contratos firmados por entidades de su municipio (SECOP II),
    los más grandes de la ventana, con el total.
  · Las reglas · normativa nacional del Ejecutivo que menciona su territorio.

Reglas del motor:
  · La cadencia es por vínculo: se manda si el último envío tiene 3 días o más.
    El workflow corre a diario y el motor decide a quién le toca.
  · No se repite: cada titular, contrato y norma ya enviados quedan en el
    snapshot `visto` del vínculo (en el worker, porque esto corre en GitHub
    Actions sin disco).
  · Sin nada que decir no se manda y NO se mueve la fecha: al día siguiente se
    vuelve a intentar con una ventana más larga. Un correo vacío mata el canal.
  · Ningún dato se inventa. Si una fuente no responde, su sección lo dice.

Uso:
  CAUDAL_ALERTAS_TOKEN=… python3 motor.py                # corrida real
  python3 motor.py --dry-run                             # arma todo, no manda ni sella
  python3 motor.py --dry-run --guardar-html /tmp/b       # deja el HTML por vínculo
  python3 motor.py --solo correo@dominio.co              # una sola cuenta
  python3 motor.py --forzar                              # ignora la cadencia
  python3 motor.py --inventario prueba.json --dry-run    # sin worker (misma forma que /inventario)
  python3 motor.py --worker http://localhost:8788        # contra un wrangler dev
"""
import argparse
import datetime as dt
import hashlib
import html as _html
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

WORKER = os.environ.get('C360_WORKER_URL', 'https://rr-auth.reruizc.workers.dev')
API = os.environ.get('CAUDAL_API_URL', 'https://l3kmprdjkl.execute-api.us-east-1.amazonaws.com')
HEADER = 'X-Caudal-Service'
UA = 'candidato-360-briefing/1.0 (+ricardoruiz.co)'
SITIO = 'https://ricardoruiz.co/candidato-360.html?abrir=1'
SOPORTE = 'hola@ricardoruiz.co'
BOGOTA = ZoneInfo('America/Bogota')
ELECCION = dt.date(2027, 10, 31)          # último domingo de octubre de 2027

CADENCIA_DIAS = 3
VENTANA_MAX_DIAS = 10                     # si un vínculo lleva mucho sin envío, no se rasca más atrás
VENTANA_NORMATIVA_DIAS = 30               # el dataset de Presidencia es mensual
TOPE_PRENSA_USTED = 5
TOPE_PRENSA_TERRITORIO = 8
TOPE_CONTRATOS = 8
TOPE_NORMAS = 5
MAX_VISTO_POR_SECCION = 300

CORP_LABEL = {'jal': 'Junta Administradora Local', 'concejo': 'Concejo', 'alcaldia': 'Alcaldía',
              'asamblea': 'Asamblea Departamental', 'gobernacion': 'Gobernación'}
CORP_DEPARTAMENTAL = {'asamblea', 'gobernacion'}
# El nombre del departamento en SECOP no siempre es el del GeoJSON del sitio.
SECOP_DEP = {'BOGOTA D C': 'Distrito Capital de Bogotá', 'DISTRITO CAPITAL DE BOGOTA': 'Distrito Capital de Bogotá',
             'SAN ANDRES Y PROVIDENCIA': 'San Andrés, Providencia y Santa Catalina'}

# Paleta del producto (verde bosque / papel / coral), en estilos inline: es correo.
INK, FOREST, GREEN, PAPER, CREAM, CORAL, MUTED, LINE = '#17251c', '#173f2c', '#1a7049', '#f4f0e8', '#fffdf7', '#ee745e', '#667068', '#e1ddd3'


# ─── helpers ────────────────────────────────────────────────────────────────
def norm(s):
    s = unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', re.sub(r'[^A-Za-z0-9 ]+', ' ', s)).strip().upper()


def toks(s, minlen=4):
    return [t for t in norm(s).split() if len(t) >= minlen and t not in _RUIDO]


_RUIDO = {'PARA', 'DE', 'DEL', 'LA', 'EL', 'LOS', 'LAS', 'MUNICIPIO', 'DISTRITO', 'CAPITAL', 'SANTA', 'SAN', 'JOSE', 'MARIA',
          'LOCALIDAD', 'COMUNA', 'BOGOTA', 'CIUDAD', 'CANDIDATO', 'CANDIDATA'}


def e(s):
    return _html.escape(str(s if s is not None else ''), quote=True)


def recortar(s, n):
    s = re.sub(r'\s+', ' ', str(s or '')).strip()
    if len(s) <= n:
        return s
    corte = s[:n].rsplit(' ', 1)[0]
    return corte + '…'


def oracion(s):
    """SECOP escribe en MAYÚSCULA SOSTENIDA; en un correo se lee como un grito."""
    s = re.sub(r'\s+', ' ', str(s or '')).strip()
    letras = [c for c in s if c.isalpha()]
    if letras and sum(c.isupper() for c in letras) / len(letras) < .7:
        return s
    return s[:1].upper() + s[1:].lower()


_SIGLAS = {'SA', 'SAS', 'ESE', 'ESP', 'EICE', 'IDU', 'IDRD', 'UNP', 'DIAN', 'ICBF', 'SENA', 'ANI', 'ANLA', 'IDT', 'IDPAC', 'DADEP', 'UAESP', 'EAAB', 'ETB', 'CENAC', 'FONCEP', 'IPES', 'ICA', 'INS', 'EPM', 'EMCALI', 'UPS', 'IPS', 'EPS', 'UT', 'LTDA', 'EU', 'CTA', 'ESAL'}
_PARTICULAS = {'DE', 'DEL', 'LA', 'LAS', 'LOS', 'EL', 'Y', 'E', 'PARA', 'EN', 'POR', 'CON', 'AL'}
_NO_SIGLA = {'SAN', 'SUR', 'RIO', 'MAR', 'PAZ', 'LUZ', 'SOL', 'FE', 'PIE', 'ORO', 'VIA', 'RED'}   # palabras cortas que NO son siglas
def nombre_entidad(s):
    """"IDRD - ENTIDAD OFICIAL." → "IDRD · Entidad Oficial"; conserva siglas y baja partículas."""
    s = re.sub(r'\s*\(oficial\)\s*', '', str(s or ''), flags=re.I)
    s = re.sub(r'\s*-\s*ENTIDAD OFICIAL\.?\s*$', '', s, flags=re.I).strip(' .-')
    out = []
    for i, w in enumerate(re.split(r'\s+', s)):
        if not w:
            continue
        u = norm(w)
        if u in _SIGLAS or (len(u) <= 3 and w.isupper() and u.isalpha() and i > 0 and u not in _PARTICULAS and u not in _NO_SIGLA):
            out.append(w.upper())
        elif u in _PARTICULAS and i > 0:
            out.append(w.lower())
        else:
            out.append(w[:1].upper() + w[1:].lower())
    return ' '.join(out)


def cop(v):
    try:
        v = float(v or 0)
    except (TypeError, ValueError):
        v = 0
    if v >= 1e9:
        return f'${v / 1e9:,.1f} mil millones'.replace(',', 'X').replace('.', ',').replace('X', '.')
    if v >= 1e6:
        return f'${v / 1e6:,.0f} millones'.replace(',', '.')
    return f'${v:,.0f}'.replace(',', '.')


def hoy_bogota():
    return dt.datetime.now(BOGOTA)


def fecha_larga(d):
    meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    return f'{d.day} de {meses[d.month - 1]} de {d.year}'


def h(*partes):
    return hashlib.sha1('|'.join(str(p or '') for p in partes).encode('utf-8')).hexdigest()[:16]


def http_json(url, data=None, headers=None, timeout=90):
    hd = {'Accept': 'application/json', 'User-Agent': UA}
    if headers:
        hd.update(headers)
    body = None
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        hd['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=body, headers=hd, method='POST' if data is not None else 'GET')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8') or '{}')


def token():
    t = (os.environ.get('CAUDAL_ALERTAS_TOKEN') or '').strip()
    if len(t) < 24:
        sys.exit('Falta CAUDAL_ALERTAS_TOKEN (mínimo 24 caracteres): es el secreto de servicio del worker.')
    return t


def worker(path, data=None):
    return http_json(WORKER.rstrip('/') + path, data, {HEADER: token()})


def api(payload, timeout=90):
    """Lambda caudal-analiza. Un fallo devuelve None: la sección lo declara."""
    try:
        return http_json(API, payload, timeout=timeout)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError, TimeoutError) as ex:
        print(f'   ! api {payload.get("action")}: {type(ex).__name__} {str(ex)[:120]}')
        return None


# ─── territorio ─────────────────────────────────────────────────────────────
def territorio_de(v):
    c = v.get('campana') or {}
    corp = (c.get('corp') or '').lower()
    dep_nombre = c.get('departamentoNombre') or ''
    mun = c.get('municipio') or ''
    loc = c.get('localidad') or ''
    if not (mun or dep_nombre) and v.get('candidato'):
        # Ruta «misma corporación»: la campaña no trae territorio explícito y se
        # deriva del corp del historial: "JAL · TEUSAQUILLO · BOGOTÁ D.C. · 2015",
        # "CONCEJO · MEDELLIN · 2023", "ASAMBLEA · VALLE DEL CAUCA · 2023".
        cand = v['candidato']
        corp = corp or next((k for k in CORP_LABEL if k in norm(cand.get('corp')).lower()), '')
        partes = [p.strip() for p in (cand.get('corp') or '').split('·') if p.strip() and not re.fullmatch(r'20\d\d', p.strip())]
        if corp in CORP_DEPARTAMENTAL:
            dep_nombre = partes[1] if len(partes) > 1 else ''
        elif corp == 'jal':
            loc = loc or (partes[1] if len(partes) > 1 else '')
            mun = partes[2] if len(partes) > 2 else ''
        else:
            mun = partes[1] if len(partes) > 1 else ''
        if not dep_nombre and 'BOGOTA' in norm(mun):
            dep_nombre = 'Bogotá D.C.'
    mun_limpio = re.sub(r',?\s*D\.?\s*C\.?$', '', mun, flags=re.I).strip()
    es_bogota = 'BOGOTA' in norm(mun) or 'BOGOTA' in norm(dep_nombre)
    departamental = corp in CORP_DEPARTAMENTAL
    # Etiqueta legible del territorio y el nombre de lo que "gobierna" ahí.
    if departamental:
        etiqueta = dep_nombre
        entidad = f'Gobernación de {dep_nombre}'
        cuerpo = f'Asamblea de {dep_nombre}'
    else:
        etiqueta = (f'{oracion(loc)} · ' if corp == 'jal' and loc else '') + (oracion(mun_limpio) if not es_bogota else 'Bogotá')
        base = 'Bogotá' if es_bogota else oracion(mun_limpio)
        entidad = f'Alcaldía de {base}'
        cuerpo = f'Concejo de {base}'
    secop_dep = SECOP_DEP.get(norm(dep_nombre), dep_nombre)
    return {'corp': corp, 'corp_label': CORP_LABEL.get(corp, corp or 'Candidatura'), 'dep_nombre': dep_nombre,
            'mun': mun, 'mun_limpio': mun_limpio, 'loc': loc, 'es_bogota': es_bogota, 'departamental': departamental,
            'etiqueta': etiqueta, 'entidad': entidad, 'cuerpo': cuerpo, 'secop_dep': secop_dep, 'meta': int(c.get('meta') or 0)}


def terminos_locales(t, v):
    """Palabras que un titular tiene que traer para contar como local."""
    base = []
    if t['departamental']:
        base += toks(t['dep_nombre'])
    else:
        base += ['BOGOTA'] if t['es_bogota'] else toks(t['mun_limpio'])
        if t['corp'] == 'jal' and t['loc']:
            base += toks(t['loc'])
    return [x for x in base if x]


def terminos_persona(v):
    nombres = [v.get('nombre') or '', v.get('nombrePublico') or '']
    out = []
    for n in nombres:
        tk = toks(n, 3)
        if len(tk) >= 2:
            out.append(tk)
    return out


def menciona_persona(titulo, personas):
    t = norm(titulo)
    for tk in personas:
        # nombre + apellido (o los dos apellidos) en el mismo titular
        if sum(1 for x in tk if x in t) >= 2:
            return True
    return False


_INSTITUCIONAL = ('ALCALD', 'CONCEJO', 'CONCEJAL', 'GOBERN', 'ASAMBLEA', 'DIPUTAD', 'DISTRIT', 'SECRETAR', 'EDIL', ' JAL', 'PLAN DE DESARROLLO',
                  'PRESUPUESTO', 'CONTRAT', 'LICITA', 'PERSONER', 'CONTRALOR', 'OBRA', 'VIA ', 'VIAS ', 'TRANSMILENIO', 'METRO', 'ACUEDUCTO', 'HOSPITAL',
                  'COLEGIO', 'SEGURIDAD', 'HOMICID', 'HURTO', 'PROTESTA', 'PARO', 'ELECCI', 'CANDIDAT', 'CAMPAÑA', 'CAMPANA', 'PARTIDO ')
_RUIDO_TITULAR = re.compile(r'\b(CLIMA|LOTER|HOROSCOP|CORTES? DE LUZ|PICO Y PLACA|SORTEO|BALOTO|VACANTES|PRONOSTICO|TEMPERATURA|RESULTADOS? DE LA LOTER|CHANCE|MILLONARIOS VS|VS MILLONARIOS)\b')


def puntaje_local(titulo, t, locales):
    """Cuánto le importa el titular a ESTE territorio. 0 = no cuenta.

    En Bogotá, Medellín o Cali «Bogotá» aparece en cualquier cosa (clima, vacantes,
    un puente), así que ahí exige la localidad o un actor institucional; en un
    municipio chico basta el nombre."""
    n = ' ' + norm(titulo) + ' '
    if _RUIDO_TITULAR.search(n):
        return 0
    p = 0
    if t['corp'] == 'jal' and t['loc'] and any(x in n for x in toks(t['loc'])):
        p += 3
    if any(k in n for k in _INSTITUCIONAL):
        p += 2
    if any(x in n for x in locales):
        p += 1
    grande = t['es_bogota'] or norm(t['mun_limpio']) in ('MEDELLIN', 'CALI', 'BARRANQUILLA', 'CARTAGENA')
    if not any(x in n for x in locales):
        return 0
    return p if (p >= 2 or not grande) else 0


# ─── fuentes ────────────────────────────────────────────────────────────────
def prensa(v, t, dias, visto):
    consultas = []
    if t['departamental']:
        consultas += [f'"{t["dep_nombre"]}"', f'"{t["entidad"]}"', f'"{t["cuerpo"]}"']
    else:
        base = 'Bogotá' if t['es_bogota'] else t['mun_limpio']
        if t['corp'] == 'jal' and t['loc']:
            consultas.append(f'"{oracion(t["loc"])}" {base}')
        consultas += [f'"{t["entidad"]}"', f'"{t["cuerpo"]}"']
        if not t['es_bogota']:
            consultas.append(f'"{base}"')
    for n in (v.get('nombre'), v.get('nombrePublico')):
        if n and len(toks(n, 3)) >= 2:
            consultas.append(f'"{n}"')
    locales = terminos_locales(t, v)
    personas = terminos_persona(v)
    vistos = set(visto.get('prensa') or [])
    usted, territorio, seen = [], [], set()
    fallos = 0
    for q in consultas:
        d = api({'action': 'medios', 'query': q, 'dias': dias}, timeout=60)
        if not d or d.get('error'):
            fallos += 1
            continue
        for r in d.get('resultados') or []:
            titulo = r.get('titulo') or ''
            k = norm(titulo)[:90]
            if not k or k in seen:
                continue
            seen.add(k)
            hid = h('p', k)
            if hid in vistos:
                continue
            item = {'id': hid, 'titulo': titulo, 'medio': r.get('medio') or '', 'alcance': r.get('alcance') or '',
                    'url': r.get('url') or '', 'fecha': r.get('fecha') or ''}
            if menciona_persona(titulo, personas):
                usted.append(item)
            else:
                pts = puntaje_local(titulo, t, locales)
                if pts:
                    item['pts'] = pts
                    territorio.append(item)
    usted.sort(key=lambda x: x['fecha'], reverse=True)
    territorio.sort(key=lambda x: (x['pts'], x['fecha']), reverse=True)
    return {'usted': usted[:TOPE_PRENSA_USTED], 'territorio': territorio[:TOPE_PRENSA_TERRITORIO],
            'n_usted': len(usted), 'n_territorio': len(territorio), 'fallos': fallos, 'consultas': len(consultas)}


def contratos(v, t, desde, visto):
    """Contratos firmados en la ventana por entidades del ORDEN TERRITORIAL del
    municipio (alcaldía, secretarías, institutos, empresas públicas). Sin ese
    filtro salían la UNP o la Fuerza Aérea solo por estar ubicadas en Bogotá.
    Para una JAL se consulta además la localidad: la Alcaldía Local firma
    contratos propios y son los que más le importan a un edil."""
    q = t['dep_nombre'] if t['departamental'] else ('Bogotá' if t['es_bogota'] else t['mun_limpio'])
    consultas = [(q, False)]
    if t['corp'] == 'jal' and t['loc']:
        consultas.insert(0, (t['loc'], True))
    vistos = set(visto.get('contratos') or [])
    ciudad_ok = None if t['departamental'] else norm('Bogotá' if t['es_bogota'] else t['mun_limpio'])
    out, seen, fallos, recortado = [], set(), 0, False
    for q, es_local in consultas:
        payload = {'action': 'contratacion', 'query': q, 'limit': 200, 'orden': 'reciente', 'orden_entidad': 'Territorial'}
        if t['secop_dep']:
            payload['departamento'] = t['secop_dep']
        d = api(payload)
        if not d or d.get('error'):
            fallos += 1
            continue
        filas = d.get('resultados') or []
        if not es_local and len(filas) >= 200:
            recortado = True
        for r in filas:
            f = r.get('fecha') or ''
            if not f or f < desde:
                continue
            if ciudad_ok and norm(r.get('ciudad') or '') != ciudad_ok:
                continue
            cid = r.get('id') or h('c', r.get('entidad'), r.get('objeto'), r.get('valor'), f)
            if cid in vistos or cid in seen:
                continue
            seen.add(cid)
            out.append({'id': cid, 'entidad': nombre_entidad(r.get('entidad')), 'proveedor': nombre_entidad(r.get('proveedor')),
                        'objeto': oracion(r.get('objeto')), 'valor': float(r.get('valor') or 0), 'fecha': f,
                        'modalidad': r.get('modalidad') or '', 'url': r.get('url') or '', 'local': es_local})
    total_valor = sum(x['valor'] for x in out)
    out.sort(key=lambda x: (x['local'], x['valor']), reverse=True)
    return {'items': out[:TOPE_CONTRATOS], 'n': len(out), 'valor': total_valor, 'fallo': fallos >= len(consultas),
            'recortado': recortado, 'n_local': sum(1 for x in out if x['local'])}


def normativa(v, t, visto):
    desde = (hoy_bogota().date() - dt.timedelta(days=VENTANA_NORMATIVA_DIAS)).isoformat()
    consultas = [t['dep_nombre']] if t['departamental'] else (['Bogotá'] if t['es_bogota'] else [t['mun_limpio'], t['dep_nombre']])
    vistos = set(visto.get('normas') or [])
    out, seen = [], set()
    fallo = False
    for q in consultas:
        if not q:
            continue
        d = api({'action': 'ejecutivo', 'query': q}, timeout=60)
        if not d or d.get('error'):
            fallo = True
            continue
        for r in d.get('resultados') or []:
            f = r.get('fecha') or ''
            if not f or f < desde:
                continue
            nid = h('n', r.get('tipo'), r.get('numero'), r.get('anio'))
            if nid in seen or nid in vistos:
                continue
            seen.add(nid)
            out.append({'id': nid, 'tipo': oracion(r.get('tipo')), 'numero': r.get('numero') or '', 'fecha': f,
                        'titulo': oracion(r.get('titulo')), 'descripcion': oracion(r.get('descripcion')), 'url': r.get('url') or ''})
    out.sort(key=lambda x: x['fecha'], reverse=True)
    return {'items': out[:TOPE_NORMAS], 'n': len(out), 'fallo': fallo}


# ─── render ─────────────────────────────────────────────────────────────────
def _fila(titulo, meta, url=''):
    tt = f'<a href="{e(url)}" style="color:{INK};text-decoration:none;font-weight:700;">{e(titulo)}</a>' if url else f'<span style="font-weight:700;color:{INK};">{e(titulo)}</span>'
    return f'<tr><td style="padding:10px 0;border-bottom:1px solid {LINE};font-size:14px;line-height:1.45;">{tt}<br><span style="font-size:12px;color:{MUTED};">{meta}</span></td></tr>'


def _bloque(num, kicker, titulo, filas, nota=''):
    cuerpo = ''.join(filas) if filas else f'<tr><td style="padding:8px 0;font-size:13px;color:{MUTED};">{e(nota)}</td></tr>'
    pie = f'<p style="font-size:12px;color:{MUTED};margin:10px 0 0;">{e(nota)}</p>' if (filas and nota) else ''
    return (f'<div style="margin:0 0 30px;"><p style="font:600 10px/1 monospace;letter-spacing:.16em;text-transform:uppercase;color:{GREEN};margin:0 0 6px;">{num} · {e(kicker)}</p>'
            f'<h2 style="font-size:20px;line-height:1.1;margin:0 0 12px;color:{INK};">{e(titulo)}</h2>'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid {LINE};">{cuerpo}</table>{pie}</div>')


def render(v, t, P, C, N, desde, hasta, primera):
    ahora = hoy_bogota()
    faltan = (ELECCION - ahora.date()).days
    nombre = v.get('nombre') or 'su candidatura'
    corto = nombre.split()[0].title() if nombre else ''
    rango = f'{fecha_larga(desde)} al {fecha_larga(hasta)}' if desde != hasta else fecha_larga(hasta)
    filas_u = [_fila(p['titulo'], f'{e(p["medio"])}{" · regional" if p["alcance"] == "regional" else ""} · {e(p["fecha"])}', p['url']) for p in P['usted']]
    filas_t = [_fila(p['titulo'], f'{e(p["medio"])}{" · regional" if p["alcance"] == "regional" else ""} · {e(p["fecha"])}', p['url']) for p in P['territorio']]
    filas_c = [_fila(f'{cop(c["valor"])} · {recortar(c["entidad"], 60)}', ('<span style="color:' + CORAL + ';font-weight:700;">En su localidad · </span>' if c.get('local') else '') + f'{e(recortar(c["objeto"], 140))}<br>{e(c["modalidad"])} · firmado el {e(c["fecha"])}' + (f' · {e(recortar(c["proveedor"], 50))}' if c['proveedor'] else ''), c['url']) for c in C['items']]
    filas_n = [_fila(f'{n["tipo"]} {n["numero"]} · {n["fecha"]}', e(recortar(n['descripcion'] or n['titulo'], 200)), n['url']) for n in N['items']]

    nota_p = ''
    if P['fallos'] >= P['consultas']:
        nota_p = 'La fuente de prensa no respondió en esta corrida.'
    elif not (filas_u or filas_t):
        nota_p = f'Ningún titular nuevo nombró a {t["etiqueta"]} ni a {corto} en estos días.'
    extra_p = ''
    if P['n_territorio'] > len(filas_t) or P['n_usted'] > len(filas_u):
        extra_p = f'Se muestran los más recientes; hubo {P["n_usted"] + P["n_territorio"]} titulares locales en total.'
    cuantos = f'más de {C["n"]}' if C.get('recortado') else str(C['n'])
    nota_c = ('La fuente de contratación no respondió en esta corrida.' if C['fallo'] else
              (f'{cuantos} contratos firmados por entidades de {t["etiqueta"]} en la ventana, por {cop(C["valor"])}.' + (' Se muestran los más grandes' + (f' y los {C["n_local"]} de su localidad' if C.get('n_local') else '') + '.' if C['n'] > len(filas_c) else '')) if C['n'] else
              f'No se firmaron contratos nuevos de entidades de {t["etiqueta"]} en estos días.')
    nota_n = ('La fuente de normativa no respondió en esta corrida.' if N['fallo'] else
              ('' if N['items'] else f'Ninguna norma del Ejecutivo de los últimos {VENTANA_NORMATIVA_DIAS} días menciona su territorio.'))

    prensa_html = ''
    if filas_u:
        prensa_html += _bloque('01', 'La conversación · sobre usted', f'{len(filas_u)} titular{"es" if len(filas_u) != 1 else ""} lo nombra{"n" if len(filas_u) != 1 else ""}', filas_u)
    prensa_html += _bloque('01' if not filas_u else '02', f'La conversación · {t["etiqueta"]}', 'Lo que se publicó de su territorio', filas_t, nota_p if not filas_t else extra_p)
    num_c = '03' if filas_u else '02'
    num_n = '04' if filas_u else '03'
    meta_html = f'<p style="font-size:12px;color:{MUTED};margin:6px 0 0;">Meta de campaña: <b style="color:{INK};">{t["meta"]:,}</b> votos.</p>'.replace(',', '.') if t['meta'] else ''
    primera_html = (f'<div style="border-left:3px solid {CORAL};padding:10px 14px;background:#fff4f1;font-size:13px;line-height:1.5;margin:0 0 24px;">'
                    f'Este es su primer briefing. A partir de ahora llega cada {CADENCIA_DIAS} días con lo nuevo de {e(t["etiqueta"])}; lo que ya vio no se repite.</div>') if primera else ''

    html = f'''<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;background:{PAPER};font-family:Helvetica,Arial,sans-serif;color:{INK};">
<div style="max-width:600px;margin:0 auto;padding:28px 18px 40px;">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:22px;"><span style="font-weight:800;font-size:17px;letter-spacing:-.02em;">Ricardo<span style="color:#0047FF;">.</span>Ruiz</span><span style="font:600 10px/1 monospace;letter-spacing:.16em;text-transform:uppercase;color:{MUTED};">Candidato 360 · briefing</span></div>
<div style="background:{FOREST};color:#fff;padding:22px 22px 18px;margin-bottom:26px;">
<p style="font:600 10px/1 monospace;letter-spacing:.16em;text-transform:uppercase;color:#91d5a9;margin:0 0 10px;">{e(t["corp_label"])} · {e(t["etiqueta"])} · 2027</p>
<h1 style="font-size:24px;line-height:1.05;margin:0 0 10px;letter-spacing:-.02em;">{e(nombre)}, así va su territorio.</h1>
<p style="margin:0;font-size:13px;color:#cbe9d5;">Del {e(rango)} · faltan <b style="color:#fff;">{faltan}</b> días para la elección.</p>{meta_html.replace(MUTED, "#cbe9d5").replace(INK, "#fff")}
</div>
{primera_html}
{prensa_html}
{_bloque(num_c, f'La plata · entidades de {t["etiqueta"]}', 'Lo que se contrató en su territorio', filas_c, nota_c)}
{_bloque(num_n, 'Las reglas · Ejecutivo nacional', 'Normas que mencionan su territorio', filas_n, nota_n) if (filas_n or N['fallo']) else ''}
<div style="margin-top:30px;padding-top:16px;border-top:1px solid {LINE};font-size:12px;color:{MUTED};line-height:1.5;">
<p style="margin:0 0 6px;"><a href="{SITIO}" style="color:{GREEN};font-weight:700;text-decoration:none;">Abrir mi CRM en Candidato 360 →</a></p>
<p style="margin:0;">Este briefing sale del territorio de su campaña. Para cambiar el correo o dejar de recibirlo, use el interruptor en su CRM. Fuentes: Google News (prensa nacional y regional), SECOP II (contratación), Presidencia (normativa). Soporte: {SOPORTE}.</p>
</div></div></body></html>'''

    lineas = [f'CANDIDATO 360 · BRIEFING · {t["corp_label"]} · {t["etiqueta"]}', f'{nombre} · del {rango} · faltan {faltan} días para la elección', '']
    if filas_u:
        lineas.append('SOBRE USTED'); lineas += [f'- {p["titulo"]} ({p["medio"]}, {p["fecha"]}) {p["url"]}' for p in P['usted']]; lineas.append('')
    lineas.append(f'LA CONVERSACIÓN · {t["etiqueta"]}')
    lineas += [f'- {p["titulo"]} ({p["medio"]}, {p["fecha"]}) {p["url"]}' for p in P['territorio']] or [f'  {nota_p or extra_p}']
    lineas += ['', f'LA PLATA · {nota_c}']
    lineas = [l for l in lineas]
    lineas += [f'- {cop(c["valor"])} · {c["entidad"]} · {recortar(c["objeto"], 120)} ({c["fecha"]}) {c["url"]}' for c in C['items']]
    if filas_n or N['fallo']:
        lineas += ['', 'LAS REGLAS · Ejecutivo nacional', nota_n] + [f'- {n["tipo"]} {n["numero"]} ({n["fecha"]}): {recortar(n["descripcion"] or n["titulo"], 160)} {n["url"]}' for n in N['items']]
    lineas += ['', f'Abrir mi CRM: {SITIO}', f'Soporte: {SOPORTE}']
    texto = '\n'.join(lineas)

    n_items = len(filas_u) + len(filas_t) + len(filas_c) + len(filas_n)
    if filas_u:
        asunto = f'{corto}, lo nombraron {len(filas_u)} {"vez" if len(filas_u) == 1 else "veces"} · briefing de {t["etiqueta"]}'
    elif filas_c and C['n']:
        asunto = f'{t["etiqueta"]}: {cuantos} contratos por {cop(C["valor"])} y {len(filas_t)} titulares'
    else:
        asunto = f'Briefing de {t["etiqueta"]} · {fecha_larga(hasta)}'
    return asunto, html, texto, n_items


# ─── motor ──────────────────────────────────────────────────────────────────
def le_toca(v, forzar):
    b = v.get('briefing') or {}
    if forzar or not b.get('ultimoEnvio'):
        return True, None
    try:
        ultimo = dt.datetime.fromisoformat(b['ultimoEnvio'].replace('Z', '+00:00')).astimezone(BOGOTA).date()
    except ValueError:
        return True, None
    dias = (hoy_bogota().date() - ultimo).days
    return dias >= int(b.get('cadenciaDias') or CADENCIA_DIAS), ultimo


def procesar(v, args):
    t = territorio_de(v)
    b = v.get('briefing') or {}
    visto = b.get('visto') or {}
    toca, ultimo = le_toca(v, args.forzar)
    etiqueta = f'{v["email"]} → {v.get("nombre") or "?"} · {t["corp_label"]} · {t["etiqueta"]}'
    if not toca:
        print(f'· {etiqueta}: no le toca (último envío {ultimo})')
        return 'no-toca'
    if not (t['departamental'] or t['mun'] or t['es_bogota']):
        print(f'· {etiqueta}: sin territorio en la campaña, se salta')
        return 'sin-territorio'
    hoy = hoy_bogota().date()
    primera = not b.get('ultimoEnvio')
    dias = min(VENTANA_MAX_DIAS, max(CADENCIA_DIAS, (hoy - ultimo).days if ultimo else CADENCIA_DIAS))
    desde = hoy - dt.timedelta(days=dias)
    print(f'· {etiqueta}: ventana {dias} días ({desde} → {hoy}){" · primera vez" if primera else ""}')

    P = prensa(v, t, dias, visto)
    C = contratos(v, t, desde.isoformat(), visto)
    N = normativa(v, t, visto)
    print(f'   prensa {len(P["usted"])}+{len(P["territorio"])} (de {P["n_usted"]}+{P["n_territorio"]}, {P["fallos"]}/{P["consultas"]} fallos) · contratos {len(C["items"])} de {C["n"]} ({cop(C["valor"])}) · normas {len(N["items"])}')

    asunto, html, texto, n_items = render(v, t, P, C, N, desde, hoy, primera)
    if args.guardar_html:
        os.makedirs(args.guardar_html, exist_ok=True)
        base = os.path.join(args.guardar_html, re.sub(r'[^a-z0-9]+', '-', v['email'].lower()))
        open(base + '.html', 'w', encoding='utf-8').write(html)
        open(base + '.txt', 'w', encoding='utf-8').write(texto)
        print(f'   html → {base}.html')
    if n_items == 0:
        print('   nada que decir: no se manda ni se mueve la fecha')
        return 'silencio'
    if args.dry_run:
        print(f'   [dry-run] asunto: {asunto}')
        return 'dry-run'

    r = worker('/c360/briefing/enviar', {'email': v['email'], 'para': v.get('correo') or v['email'], 'asunto': asunto, 'html': html, 'texto': texto})
    if not r.get('ok'):
        print(f'   ✗ envío rechazado: {r.get("error")}')
        return 'error'
    print(f'   ✓ enviado a {r.get("para")} · {r.get("id") or ""} · asunto: {asunto}')

    nuevo_visto = {
        'prensa': (list(visto.get('prensa') or []) + [p['id'] for p in P['usted'] + P['territorio']])[-MAX_VISTO_POR_SECCION:],
        'contratos': (list(visto.get('contratos') or []) + [c['id'] for c in C['items']])[-MAX_VISTO_POR_SECCION:],
        'normas': (list(visto.get('normas') or []) + [n['id'] for n in N['items']])[-MAX_VISTO_POR_SECCION:],
    }
    rs = worker('/c360/briefing/estado', {'email': v['email'], 'visto': nuevo_visto, 'ultimoEnvio': dt.datetime.now(dt.timezone.utc).isoformat()})
    if not rs.get('ok'):
        print(f'   ! no se pudo sellar el estado: {rs.get("error")} (el próximo briefing puede repetir items)')
    return 'enviado'


def main():
    global WORKER
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--forzar', action='store_true', help='ignora la cadencia de 3 días')
    ap.add_argument('--solo', help='solo esta cuenta (correo)')
    ap.add_argument('--guardar-html', help='carpeta donde dejar el HTML y el texto de cada briefing')
    ap.add_argument('--inventario', help='JSON con la forma de /c360/briefing/inventario (pruebas sin worker)')
    ap.add_argument('--worker', help=f'URL del worker (default {WORKER})')
    args = ap.parse_args()
    if args.worker:
        WORKER = args.worker

    if args.inventario:
        inv = json.load(open(args.inventario, encoding='utf-8'))
    else:
        inv = worker('/c360/briefing/inventario')
    vinculos = inv.get('vinculos') or []
    res = inv.get('resumen') or {}
    print(f'Inventario: {len(vinculos)} vínculos con briefing encendido (total {res.get("total", "?")}, apagados {res.get("apagados", "?")}, sin acceso {res.get("sinAcceso", "?")}) · {hoy_bogota():%Y-%m-%d %H:%M} Bogotá')
    if args.solo:
        vinculos = [v for v in vinculos if v.get('email', '').lower() == args.solo.lower()]
        if not vinculos:
            print(f'No hay vínculo con briefing encendido para {args.solo}')
    conteo = {}
    for v in vinculos:
        try:
            r = procesar(v, args)
        except Exception as ex:   # un vínculo roto no puede tumbar a los demás
            print(f'   ✗ {v.get("email")}: {type(ex).__name__}: {str(ex)[:200]}')
            r = 'excepcion'
        conteo[r] = conteo.get(r, 0) + 1
    print('Resumen:', ', '.join(f'{k} {n}' for k, n in sorted(conteo.items())) or 'nada que hacer')
    return 1 if conteo.get('excepcion') else 0


if __name__ == '__main__':
    sys.exit(main())
