#!/usr/bin/env python3
"""
Candidato 360 · el briefing del ciclo de 3 días, con el formato del correo de Caudal.

El briefing viejo (`motor.py`) es dato ordenado: titulares, contratos, normas.
Este es la LECTURA de la tarjeta 03 del CRM puesta en el correo: qué movió la
agenda en estos tres días (prensa + redes), a qué arquetipos le habla, en qué
localidades conviene estar y qué barrios faltan por visitar.

La forma es la del correo de Caudal (`tools/caudal/brief/enviar_brief.py`):
saludo, portada oscura con la lectura de la ventana, tres cifras, «si solo tiene
tiempo para una cosa», el párrafo, los temas en una línea cada uno y lo que
viene. Solo tablas y estilos en línea: Gmail y Outlook ignoran <style>, flexbox
y grid.

Entra un JSON `ciclo` con lo que calcula `candidato-360-ciclo.js` (prensa
analizada, redes, arquetipos con su relevancia y prioridades por localidad),
más la captura de redes (para las citas) y el vínculo (nombre, territorio,
meta). Nada de un cliente vive en este archivo: el repo es público.

  python3 correo_ciclo.py --ciclo ciclo.json --captura captura.json \\
      --vinculo vinculo.json --desde 2026-10-16 --hasta 2026-10-19 --out borrador.html
  … --enviar correo@dominio.co      (por el transporte de las alertas de Caudal)

⚠️ Describe el territorio, nunca a las personas: dice dónde viven los arquetipos
que la agenda de estos días mueve, no quién vota por quién.
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys

ELECCION = dt.date(2027, 10, 31)
CADENCIA = 3
SITIO = 'https://ricardoruiz.co/candidato-360.html?abrir=1'
ESCUCHA = 'https://ricardoruiz.co/candidato-360-escucha.html'

MESES = ('enero febrero marzo abril mayo junio julio agosto septiembre '
         'octubre noviembre diciembre').split()
DIAS = ('lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo')
# Mismos colores del correo de Caudal, con el verde de Candidato 360 de acento.
TINTA, GRIS, AZUL, PAPEL, LINEA = '#0b0d11', '#5a6070', '#2b5672', '#fbfaf8', '#e2e5ea'
VERDE, CORAL, AMBAR = '#1f6b45', '#d9480f', '#8a6d1c'
RAMPA = ['#e7e2d6', '#f3d9a4', '#f0b45f', '#e07b39', '#b9431f']
NOMBRE_RED = {'x': 'X', 'instagram': 'Instagram', 'tiktok': 'TikTok', 'facebook': 'Facebook'}
TILDES = {'ENGATIVA': 'Engativá', 'FONTIBON': 'Fontibón', 'USAQUEN': 'Usaquén', 'CIUDAD BOLIVAR': 'Ciudad Bolívar',
          'SAN CRISTOBAL': 'San Cristóbal', 'LOS MARTIRES': 'Los Mártires', 'MARTIRES': 'Los Mártires',
          'ANTONIO NARINO': 'Antonio Nariño', 'BOGOTA': 'Bogotá'}


def e(s):
    return html.escape(str(s if s is not None else ''))


def sin_tilde(s):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', str(s or '')) if unicodedata.category(c) != 'Mn')


def titulo(s):
    """«VILLA ELISA» → «Villa Elisa», con la tilde de las localidades y los romanos."""
    k = sin_tilde(s).upper().strip()
    if k in TILDES:
        return TILDES[k]
    t = re.sub(r"(^|[\s(\-])([a-záéíóúñü])", lambda m: m.group(1) + m.group(2).upper(), str(s or '').lower())
    t = re.sub(r'\b(De|Del|La|Las|Los|Y|El|En)\b', lambda m: m.group(0).lower(), t)
    t = re.sub(r'\b(Ii|Iii|Iv|Vi|Vii|Viii|Ix|Xi|Xii)\b', lambda m: m.group(0).upper(), t)
    return t[:1].upper() + t[1:]


def lista(xs):
    xs = [x for x in xs if x]
    return xs[0] if len(xs) == 1 else (', '.join(xs[:-1]) + ' y ' + xs[-1] if xs else '')


def num(n):
    return f'{int(round(n or 0)):,}'.replace(',', '.')


def pct(x):
    return f'{round((x or 0) * 100)} %'


def dec(x, n=2):
    return f'{x:.{n}f}'.replace('.', ',')


def fecha(d, dia=False):
    d = d if isinstance(d, dt.date) else dt.date.fromisoformat(str(d)[:10])
    txt = f'{d.day} de {MESES[d.month - 1]}'
    return f'{DIAS[d.weekday()]} {txt}' if dia else txt


def limpio(t):
    """El titular sin el «| Medio» que Google News a veces le pega al final."""
    return re.sub(r'\s+[|\-–]\s+[^|\-–]{2,40}$', '', str(t or '')).strip()


def rango(d1, d2):
    d1, d2 = (x if isinstance(x, dt.date) else dt.date.fromisoformat(str(x)[:10]) for x in (d1, d2))
    return f'Del {d1.day} al {fecha(d2)}' if d1.month == d2.month else f'Del {fecha(d1)} al {fecha(d2)}'


def cop(v):
    try:
        v = float(v or 0)
    except (TypeError, ValueError):
        return '—'
    if v >= 1e9:
        return f'${dec(v / 1e9, 1)} mil millones'
    if v >= 1e6:
        return f'${dec(v / 1e6, 0 if v >= 1e8 else 1)} millones'
    return f'${num(v)}'


def corto(txt, n):
    txt = str(txt or '').strip()
    return txt if len(txt) <= n else txt[:n].rsplit(' ', 1)[0].rstrip(',.;:') + '…'


# ─── Del cálculo al brief ───────────────────────────────────────────────────
def postura_propia(cap):
    """Lo que le comentan en SUS publicaciones, por red y en total."""
    tot = {'a_favor': 0, 'en_contra': 0, 'ataque': 0, 'neutro': 0}
    por_red = []
    for red, R in (cap or {}).get('redes', {}).items():
        if not R or R.get('estado') != 'ok':
            continue
        C = R.get('comentarios_propios') or {}
        p = C.get('postura') or {}
        for k in tot:
            tot[k] += int(p.get(k) or 0)
        n = int(C.get('n') or 0)
        if n:
            por_red.append({'red': red, 'nombre': NOMBRE_RED.get(red, red), 'n': n,
                            'hostil': int(p.get('en_contra') or 0) + int(p.get('ataque') or 0),
                            'favor': int(p.get('a_favor') or 0)})
    return tot, por_red


FECHA_EN_TITULAR = re.compile(r'del?\s+(\d{1,2})\s+(?:al|y)\s+(?:el\s+)?(\d{1,2})\s+de\s+(' + '|'.join(MESES) + r')', re.I)


def agenda_de_titulares(filas, hoy):
    """Fechas que vienen ESCRITAS en un titular («del 20 al 25 de octubre»).
    No se infiere nada que el titular no diga: sin fecha explícita no entra."""
    out = []
    for f in filas:
        m = FECHA_EN_TITULAR.search(f.get('titulo') or '')
        if not m:
            continue
        mes = MESES.index(m.group(3).lower()) + 1
        anio = hoy.year + (1 if mes < hoy.month - 6 else 0)
        try:
            ini, fin = dt.date(anio, mes, int(m.group(1))), dt.date(anio, mes, int(m.group(2)))
        except ValueError:
            continue
        if fin < hoy:
            continue
        que = limpio(FECHA_EN_TITULAR.sub('', f['titulo'])).rstrip(' ,.:;')
        out.append({'iso': ini.isoformat(), 'cuando': f'Del {ini.day} al {fin.day} de {MESES[mes - 1]}',
                    'que': corto(que, 140), 'fuente': f.get('medio', ''),
                    'url': f.get('url', '')})
    return out


def armar(ciclo, cap, vinculo, desde, hasta, visitas=None, extra_prensa=None, contratos=None, normas=None, primera=False):
    """El brief en un dict, con el mismo espíritu del JSON de Caudal:
    lectura (título + párrafo + «una cosa»), cifras, temas, zonas y agenda."""
    visitas = visitas or {}
    dias = max(1, (hasta - desde).days)
    ventana = {3: 'tres', 4: 'cuatro', 5: 'cinco', 6: 'seis', 7: 'siete'}.get(dias, str(dias))
    nombre = (vinculo.get('candidato') or {}).get('nombre') or vinculo.get('nombre') or ''
    corto_nombre = titulo(nombre.split()[0]) if nombre else ''
    camp = vinculo.get('campana') or {}
    terr = ciclo.get('territorio') or titulo(camp.get('municipio', ''))
    cuerpo = {'concejo': f'Concejo de {terr}', 'jal': 'Junta Administradora Local', 'alcaldia': f'Alcaldía de {terr}',
              'asamblea': 'Asamblea', 'gobernacion': 'Gobernación'}.get(camp.get('corp'), terr)

    pz = ciclo.get('prensa') or {}
    R = ciclo.get('redes') or {}
    arq = [a for a in (ciclo.get('arquetipos') or []) if a.get('act') is not None]
    uni = ciclo.get('unidades') or []
    tot, por_red = postura_propia(cap)
    n_com = sum(tot.values())

    # ── Zonas: top 3, con los barrios que faltan por visitar ────────────────
    zonas = []
    for u in uni[:3]:
        # La lectura marca `visitado` con las visitas del worker; el CLI viejo pasaba nombres.
        vis = lambda b: b.get('visitado') or bool(visitas.get(b.get('code')) or visitas.get(b['nombre']))
        libres = [b for b in u['barrios'] if not vis(b)]
        hechos = [b for b in u['barrios'] if vis(b)]
        zonas.append({'nombre': titulo(u['nombre']), 'share': u['share'],
                      'por_visitar': [titulo(b['nombre']) for b in libres[:3]],
                      'visitados': len(hechos),
                      'arq': [b['top'] for b in u['barrios'][:3]]})
    nombre_arq = {a['id']: a['nombre'] for a in ciclo.get('arquetipos') or []}

    # ── La lectura ──────────────────────────────────────────────────────────
    a1 = arq[0] if arq else None
    a2 = arq[1] if len(arq) > 1 else None
    z3 = [z['nombre'] for z in zonas]
    if a1 and z3:
        tit = f'La agenda de estos días le habla a «{a1["nombre"]}»: esta semana, {lista(z3)}.'
    elif z3:
        tit = f'Esta semana conviene estar en {lista(z3)}.'
    elif (ciclo.get('prensa') or {}).get('temas'):
        tit = f'En {terr}, la agenda de estos días la mueve {ciclo["prensa"]["temas"][0]["corto"]}.'
    else:
        tit = f'Lo que pasó en {terr} en estos {ventana} días.'

    partes = []
    temas = pz.get('temas') or []
    suyos = sum(1 for f in pz.get('filas') or [] if f.get('suyo'))
    if pz.get('N'):
        t1 = temas[0] if temas else None
        t2 = temas[1] if len(temas) > 1 else None
        s = f'En los últimos {ventana} días salieron {num(pz["N"])} titulares sobre {terr}'
        if t1:
            s += f'; manda {t1["corto"]} ({pct(t1["pct"])})'
            if t2:
                s += f' y le sigue {t2["corto"]} ({pct(t2["pct"])})'
        s += '.'
        s += (f' {num(suyos)} lo {"nombra" if suyos == 1 else "nombran"} a usted.' if suyos else
              ' Ninguno lo nombra a usted en el titular.')
        partes.append(s)
    else:
        partes.append(f'En los últimos {ventana} días la prensa casi no habló de {terr}: la agenda la pone la conversación de redes.')
    ideas = R.get('ideas') or []
    if ideas:
        idea, n = ideas[0]
        partes.append(f'En redes, de sus temas el que más conversación tiene es «{idea}» ({num(n)} publicaciones encontradas).')
    if a1:
        conecta = [a for a in (a1, a2) if a and (a.get('afin') or 0) >= 1]
        if a2 and a2.get('temaNombre') and a2['temaNombre'] != a1.get('temaNombre'):
            s = (f'Esa agenda le habla sobre todo a «{a1["nombre"]}», que se mueve por {a1["temaNombre"]}, '
                 f'y a «{a2["nombre"]}», por {a2["temaNombre"]}')
        else:
            s = f'Esa agenda le habla sobre todo a {lista([f"«{a1["nombre"]}»"] + ([f"«{a2["nombre"]}»"] if a2 else []))}'
            if a1.get('temaNombre'):
                s += f', que se {"mueven" if a2 else "mueve"} por {a1["temaNombre"]}'
        if len(conecta) == 2:
            s += f', y con los dos usted rinde por encima de la ciudad ({dec(a1["afin"])} y {dec(a2["afin"])} veces su promedio)'
        elif conecta:
            s += f', y con «{conecta[0]["nombre"]}» usted rinde por encima de la ciudad'
        partes.append(s + '.')
    parrafo = ' '.join(partes)

    una = ''
    if zonas:
        z = zonas[0]
        una = f'Ir a {z["nombre"]}'
        if z['por_visitar']:
            una += f': {lista(z["por_visitar"])} son los barrios que más pesan y aún no tiene visita marcada'
        if a1:
            una += f'. Ahí vive «{a1["nombre"]}», el arquetipo que esta agenda más mueve'
            if a1.get('temaNombre'):
                una += f'; el tema que lo abre hoy es {a1["temaNombre"]}'
        una += '.'

    # ── Lo que se movió: una línea por cosa, con su rótulo ──────────────────
    temas_lin = []
    claves_z = {sin_tilde(z['nombre']).upper(): z['nombre'] for z in zonas}
    for f in (pz.get('filas') or [])[:5]:
        tt = limpio(f['titulo'])
        en = [n for k, n in claves_z.items() if re.search(r'\b' + re.escape(k) + r'\b', sin_tilde(tt).upper())]
        if f.get('suyo'):
            temas_lin.append({'tipo': 'usted', 'rotulo': f'Lo nombra · {f.get("medio", "")}', 'titulo': tt, 'url': f.get('url', '')})
            continue
        rot = f'Prensa · {f.get("medio", "")}' + (f' · {en[0]} es zona prioritaria' if en else '')
        temas_lin.append({'tipo': 'zona' if en else 'prensa', 'rotulo': rot, 'titulo': tt, 'url': f.get('url', '')})
    temas_lin.sort(key=lambda x: x['tipo'] != 'usted')        # lo que lo nombra, primero
    for x in extra_prensa or []:
        temas_lin.append({**x, 'titulo': limpio(x.get('titulo', ''))})
    if por_red:
        dura = max(por_red, key=lambda r: (r['hostil'] / r['n'], r['n']))
        grandes = [r for r in por_red if r['n'] >= 20] or por_red     # 11 de 13 no dice nada
        amable = max(grandes, key=lambda r: (r['favor'] / r['n'], -r['hostil'] / r['n']))
        if dura['hostil']:
            temas_lin.append({'tipo': 'redes', 'rotulo': f'Redes · {dura["nombre"]}',
                              'titulo': f'En {dura["nombre"]} le comentan duro: {num(dura["hostil"])} de {num(dura["n"])} comentarios en contra o en ataque, {num(dura["favor"])} a favor.'})
        if amable is not dura and amable['favor']:
            temas_lin.append({'tipo': 'redes', 'rotulo': f'Redes · {amable["nombre"]}',
                              'titulo': f'En {amable["nombre"]}, al revés: {num(amable["favor"])} de {num(amable["n"])} comentarios a favor.'})

    # La plata y las reglas: las mismas fuentes del briefing de siempre (SECOP y
    # Presidencia), en una línea cada cosa, como los temas del correo de Caudal.
    for c in (contratos or [])[:3]:
        temas_lin.append({'tipo': 'plata', 'rotulo': 'La plata · ' + ('en su localidad · ' if c.get('local') else '') + corto(titulo(c.get('entidad', '')), 50),
                          'titulo': f'{cop(c.get("valor"))} · {corto(c.get("objeto", ""), 150)}', 'url': c.get('url', '')})
    for n in (normas or [])[:2]:
        temas_lin.append({'tipo': 'reglas', 'rotulo': f'Las reglas · {n.get("tipo", "")} {n.get("numero", "")}',
                          'titulo': corto(n.get('descripcion') or n.get('titulo', ''), 160), 'url': n.get('url', '')})
    agenda = agenda_de_titulares(pz.get('filas') or [], hasta)
    proximo = hasta + dt.timedelta(days=CADENCIA)
    primera_txt = f'Este es su primer briefing con la lectura del ciclo. Llega cada {CADENCIA} días; lo que ya vio no se repite.' if primera else ''
    agenda.append({'iso': proximo.isoformat(), 'cuando': fecha(proximo, dia=True).capitalize(), 'que': 'Próximo briefing, con lo nuevo de estos días.'})

    oficio = ciclo.get('oficio') or ''
    return {
        '_meta': {'nombre': nombre, 'corto': corto_nombre, 'territorio': terr, 'cuerpo': cuerpo,
                  'desde': desde.isoformat(), 'hasta': hasta.isoformat(), 'meta': camp.get('meta'),
                  'faltan': (ELECCION - hasta).days, 'redes_fecha': R.get('fecha', ''), 'ventana': ventana, 'primera': primera_txt},
        'lectura': {'titulo': tit, 'parrafo': parrafo, 'una': una,
                    'llevar': (f'{oficio} Hoy el tema que lo abre es {a1["temaNombre"]}.' if oficio and a1 and a1.get('temaNombre') else oficio)},
        'cifras': [(num(pz.get('N') or 0), f'titulares de {terr}'),
                   (num(n_com), 'comentarios leídos en sus redes'),
                   (num((ELECCION - hasta).days), 'días para la elección')],
        'redes': {'favor': tot['a_favor'], 'hostil': tot['en_contra'] + tot['ataque'], 'n': n_com},
        'arquetipos': [{'nombre': a['nombre'], 'color': a.get('color'), 'tema': a.get('temaNombre'), 'afin': a.get('afin')} for a in arq[:3]],
        'zonas': zonas, 'nombre_arq': nombre_arq,
        'sin_zonas': '' if zonas else ('El mapa de zonas a priorizar sale en las ciudades con arquetipos por barrio (hoy Bogotá, Medellín y Cartagena). '
                                       'Cuando existan para la suya, este correo dirá también en qué barrios estar.'),
        'temas': temas_lin, 'agenda': agenda,
        'visitas': len(visitas),
    }


# ─── El correo ──────────────────────────────────────────────────────────────
def asunto(b):
    m = b['_meta']
    z = [x['nombre'] for x in b.get('zonas') or []][:3]
    base = f'Candidato 360 · Lo de estos {m.get("ventana", "tres")} días · {fecha(m["hasta"])}'
    return f'{base} · {lista(z)}' if z else base


def cuerpo_html(b, borrador=False):
    m, lec = b['_meta'], b['lectura']

    def cifra(n, rotulo, color=VERDE):
        return (f'<td align="center" width="33%" style="padding:0 6px">'
                f'<div style="background:{color};color:#fff;border-radius:10px;'
                f'padding:10px 4px;font-size:22px;font-weight:bold">{e(n)}</div>'
                f'<div style="font-size:12px;color:{GRIS};padding-top:6px">{e(rotulo)}</div></td>')
    cifras = ''.join(cifra(n, r, c) for (n, r), c in zip(b['cifras'], (VERDE, AZUL, TINTA)))

    # Zonas: barra proporcional a la prioridad + barrios por visitar.
    mx = max([z['share'] for z in b['zonas']] or [1])
    filas_z = ''
    for i, z in enumerate(b['zonas'], 1):
        ancho = max(8, round(100 * z['share'] / mx))
        color = RAMPA[min(4, 5 - i)]
        arqs = []
        for a in z['arq']:
            n = b['nombre_arq'].get(a)
            if n and n not in arqs:
                arqs.append(n)
        sub = (f'Barrios por visitar: <b style="color:{TINTA}">{e(lista(z["por_visitar"]))}</b>.' if z['por_visitar']
               else 'Ya visitó sus barrios clave.')
        if z['visitados']:
            sub += f' {num(z["visitados"])} visitado{"s" if z["visitados"] != 1 else ""} hace poco.'
        if arqs:
            sub += f' Pesan ahí {e(lista([f"«{x}»" for x in arqs[:2]]))}.'
        filas_z += (
            f'<tr><td style="padding:12px 0;border-top:1px solid {LINEA}">'
            f'<span style="font-size:11px;font-weight:bold;letter-spacing:.06em;text-transform:uppercase;color:{CORAL}">'
            f'Prioridad {i} · {pct(z["share"])} del peso de la ciudad</span><br>'
            f'<span style="font-size:17px;font-weight:bold;color:{TINTA}">{e(z["nombre"])}</span>'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:6px 0 6px"><tr>'
            f'<td width="{ancho}%" style="background:{color};height:8px;border-radius:4px;font-size:0;line-height:0">&nbsp;</td>'
            f'<td style="font-size:0;line-height:0">&nbsp;</td></tr></table>'
            f'<span style="font-size:13px;color:{GRIS}">{sub}</span></td></tr>')

    filas_t = ''
    for t in b['temas']:
        color = {'redes': VERDE, 'usted': CORAL, 'zona': CORAL, 'plata': AMBAR, 'reglas': GRIS}.get(t['tipo'], AZUL)
        tt = (f'<a href="{e(t["url"])}" style="color:{TINTA};text-decoration:none">{e(t["titulo"])}</a>' if t.get('url')
              else e(t['titulo']))
        filas_t += (
            f'<tr><td style="padding:10px 0;border-top:1px solid {LINEA}">'
            f'<span style="font-size:11px;font-weight:bold;letter-spacing:.06em;text-transform:uppercase;color:{color}">{e(t["rotulo"])}</span><br>'
            f'<span style="font-size:15px;color:{TINTA}">{tt}</span></td></tr>')

    filas_a = ''.join(
        f'<tr><td style="padding:6px 12px 6px 0;font-size:13px;font-weight:bold;color:{AZUL};white-space:nowrap;vertical-align:top">{e(x["cuando"])}</td>'
        f'<td style="padding:6px 0;font-size:14px;color:{TINTA}">{e(x["que"])}'
        + (f' <span style="color:{GRIS};font-size:12px">({e(x["fuente"])})</span>' if x.get('fuente') else '') + '</td></tr>'
        for x in b['agenda'])

    arq_pills = ''.join(
        f'<span style="display:inline-block;margin:0 6px 6px 0;padding:4px 10px;border-radius:999px;background:{PAPEL};'
        f'border:1px solid {LINEA};font-size:12px;color:{TINTA}"><span style="color:{a["color"] or GRIS}">●</span> '
        f'{e(a["nombre"])}{f" · rinde {dec(a["afin"])}×" if a.get("afin") else ""}</span>'
        for a in b['arquetipos'])

    rd = b['redes']
    redes_txt = ''
    if rd['n']:
        redes_txt = (f'En lo que le comentan en sus publicaciones ({num(rd["n"])} comentarios leídos): '
                     f'<b>{pct(rd["hostil"] / rd["n"])}</b> en contra o en ataque y <b>{pct(rd["favor"] / rd["n"])}</b> a favor. '
                     f'<a href="{ESCUCHA}" style="color:{VERDE}">Ver la escucha →</a>')

    aviso = (f'<tr><td style="padding:0 28px 18px"><div style="padding:10px 12px;background:#fbf9f2;border-left:3px solid {AMBAR};'
             f'font-size:12px;color:{GRIS}">Es un <b>borrador para revisión</b>: así llegaría el briefing al candidato. '
             f'</div></td></tr>') if borrador else ''

    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0;padding:0;background:#f1f2f4">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f2f4">
<tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:620px;background:#ffffff;border-radius:14px;font-family:Helvetica,Arial,sans-serif;color:{TINTA};line-height:1.5">

<tr><td style="padding:26px 28px 6px;font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:{GRIS}">
<b style="color:{TINTA}">Candidato 360</b> &nbsp;×&nbsp; {e(titulo(m['nombre']))}</td></tr>

<tr><td style="padding:4px 28px 0">
<div style="font-size:30px;font-weight:bold;color:{TINTA}">¡Hola, {e(m['corto'])}!</div>
<div style="font-size:17px;font-style:italic;color:{VERDE};padding-top:2px">Lo de estos {e(m.get('ventana', 'tres'))} días · {e(m['cuerpo'])}</div>
</td></tr>

{f'<tr><td style="padding:14px 28px 0"><div style="padding:10px 12px;background:#fff4f1;border-left:3px solid {CORAL};font-size:13px">{e(m["primera"])}</div></td></tr>' if m.get('primera') else ''}
<tr><td style="padding:18px 28px 0">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{TINTA};border-radius:12px">
<tr><td style="padding:22px 24px 24px">
<div style="font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#91d5a9">
{e(rango(m['desde'], m['hasta']))} · faltan {num(m['faltan'])} días</div>
<div style="font-size:22px;font-weight:bold;color:#ffffff;line-height:1.3;padding-top:8px">{e(lec['titulo'])}</div>
</td></tr></table></td></tr>

<tr><td style="padding:22px 22px 4px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{cifras}</tr></table></td></tr>

{f'<tr><td style="padding:18px 28px 0"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAPEL};border-left:4px solid {VERDE};border-radius:6px"><tr><td style="padding:14px 16px"><div style="font-size:11px;font-weight:bold;letter-spacing:.08em;text-transform:uppercase;color:{VERDE}">Si solo tiene tiempo para una cosa</div><div style="font-size:15px;padding-top:4px">{e(lec["una"])}</div></td></tr></table></td></tr>' if lec.get('una') else ''}

<tr><td style="padding:18px 28px 0;font-size:15px">{e(lec['parrafo'])}</td></tr>

{f'<tr><td style="padding:14px 28px 0">{arq_pills}</td></tr>' if arq_pills else ''}

{f'<tr><td style="padding:26px 28px 0;font-size:19px;font-weight:bold">Dónde estar esta semana</td></tr><tr><td style="padding:6px 28px 0"><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{filas_z}</table></td></tr>' if filas_z else ''}

{f'<tr><td style="padding:12px 28px 0"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAPEL};border-radius:6px"><tr><td style="padding:12px 16px;font-size:14px"><b>Qué llevar a esas zonas.</b> {e(lec["llevar"])}</td></tr></table></td></tr>' if lec.get('llevar') else ''}

{f'<tr><td style="padding:22px 28px 0;font-size:13px;color:{GRIS}">{e(b["sin_zonas"])}</td></tr>' if b.get('sin_zonas') else f'<tr><td style="padding:12px 28px 0;font-size:13px"><a href="{SITIO}" style="color:{VERDE};font-weight:bold;text-decoration:none">Ver el mapa de barrios y marcar visitas en su CRM →</a></td></tr>'}

{f'<tr><td style="padding:26px 28px 0;font-size:19px;font-weight:bold">Lo que se movió</td></tr><tr><td style="padding:6px 28px 0"><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{filas_t}</table></td></tr>' if filas_t else ''}

{f'<tr><td style="padding:12px 28px 0;font-size:13px;color:{GRIS}">{redes_txt}</td></tr>' if redes_txt else ''}

{f'<tr><td style="padding:24px 28px 0;font-size:19px;font-weight:bold">Lo que viene</td></tr><tr><td style="padding:6px 28px 0"><table role="presentation" cellpadding="0" cellspacing="0">{filas_a}</table></td></tr>' if filas_a else ''}

<tr><td style="padding:24px 28px 16px;font-size:12px;color:{GRIS}">
La prioridad junta tres cosas: dónde viven los arquetipos que la agenda de estos días mueve, cuánto rinde usted con cada uno
y si ya visitó el barrio. Describe el territorio, no a las personas. Fuentes: prensa nacional y regional (Google News), SECOP II,
Presidencia y la lectura de sus redes{f" del {e(fecha(m['redes_fecha']))}" if m.get('redes_fecha') else ''}. Para cambiar el correo o dejar de recibirlo, use el interruptor de la tarjeta 03 en su CRM.</td></tr>
{aviso}
</table></td></tr></table></body></html>"""


def texto(b):
    m, lec = b['_meta'], b['lectura']
    L = [f'CANDIDATO 360 · Lo de estos {m.get("ventana", "tres")} días · {m["cuerpo"]}', f'{rango(m["desde"], m["hasta"])} · faltan {m["faltan"]} días', '',
         lec['titulo'], '']
    if lec.get('una'):
        L += ['SI SOLO TIENE TIEMPO PARA UNA COSA', lec['una'], '']
    L.append(lec['parrafo'])
    if b['zonas']:
        L += ['', 'DÓNDE ESTAR ESTA SEMANA'] + [f'{i}. {z["nombre"]} ({pct(z["share"])}) · por visitar: {lista(z["por_visitar"]) or "—"}' for i, z in enumerate(b['zonas'], 1)]
    elif b.get('sin_zonas'):
        L += ['', b['sin_zonas']]
    if lec.get('llevar'):
        L += ['', f'Qué llevar: {lec["llevar"]}']
    L += ['', 'LO QUE SE MOVIÓ'] + [f'- {t["rotulo"]}: {t["titulo"]}' + (f' {t["url"]}' if t.get('url') else '') for t in b['temas']]
    L += ['', 'LO QUE VIENE'] + [f'- {x["cuando"]}: {x["que"]}' for x in b['agenda']]
    L += ['', f'Su CRM: {SITIO}']
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ciclo', required=True)
    ap.add_argument('--captura')
    ap.add_argument('--vinculo', required=True)
    ap.add_argument('--extra', help='JSON con líneas extra para «Lo que se movió» ([{tipo, rotulo, titulo, url}])')
    ap.add_argument('--desde', required=True)
    ap.add_argument('--hasta', required=True)
    ap.add_argument('--out', help='HTML de salida')
    ap.add_argument('--borrador', action='store_true', help='agrega la franja de «borrador para revisión»')
    ap.add_argument('--enviar', help='correo de destino (transporte de las alertas de Caudal)')
    a = ap.parse_args()

    ciclo = json.load(open(a.ciclo, encoding='utf-8'))
    cap = json.load(open(a.captura, encoding='utf-8')) if a.captura else {}
    vin = json.load(open(a.vinculo, encoding='utf-8'))
    extra = json.load(open(a.extra, encoding='utf-8')) if a.extra else None
    b = armar(ciclo, cap, vin, dt.date.fromisoformat(a.desde), dt.date.fromisoformat(a.hasta), extra_prensa=extra)
    h, t, s = cuerpo_html(b, a.borrador), texto(b), asunto(b)
    if a.borrador:
        s = '[Borrador] ' + s
    if a.out:
        open(a.out, 'w', encoding='utf-8').write(h)
        open(re.sub(r'\.html?$', '', a.out) + '.txt', 'w', encoding='utf-8').write(t)
        print(f'→ {a.out}')
    print('asunto:', s)
    if a.enviar:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'caudal', 'alertas'))
        import sender  # noqa: E402
        r = sender.enviar(s, h, t, [a.enviar], etiqueta='c360-ciclo-borrador')
        print(r.get('estado'), '·', r.get('detalle', ''))


if __name__ == '__main__':
    main()
