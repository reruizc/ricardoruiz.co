#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Caudal · Alertas — render del digest (HTML de correo + texto plano).

El HTML es a la vez el cuerpo del correo y el archivo que se abre en el
navegador, así que juega con las reglas del medio más restrictivo: tablas en
vez de flex/grid, estilos inline, cero fuentes web, cero JS, cero imágenes
externas. La paleta es la del sistema visual v2 del sitio — Helvetica ya es
fuente de sistema, así que el correo se ve igual sin cargar nada.

Cada señal muestra su `porque`. Es deliberado: un digest que dice "alto" sin
justificarlo no se puede llevar a una reunión.
"""

import datetime as dt
import html as _html
import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reglas import pesos                                       # noqa: E402

# --- paleta v2 (valores sólidos: rgba no es confiable en clientes de correo) --
BG = '#060810'
CARD = '#0d1018'
BORDE = '#1c2130'
TEXTO = '#e8eaf0'
TENUE = '#8d93a6'
AZUL = '#3d6fff'
NIVEL = {
    'alto':  {'color': '#ff7a45', 'fondo': '#2a1408', 'label': 'ALTO'},
    'medio': {'color': '#3d6fff', 'fondo': '#0b1430', 'label': 'MEDIO'},
    'bajo':  {'color': '#7a8290', 'fondo': '#12151d', 'label': 'BAJO'},
}
PILAR = {
    'congreso':     'Congreso',
    'regulatorio':  'Regulatorio',
    'ejecutivo':    'Ejecutivo',
    'contratacion': 'Contratación',
    # La prensa ya no es un pilar de señales: se cuelga de cada acto del Estado
    # como cobertura. Aquí solo caen los titulares que hablan de una empresa
    # vigilada SIN acto detrás — la única prensa que es noticia y no eco.
    'medios':       'Prensa sin acto del Estado detrás',
}
PILAR_ORDEN = ['congreso', 'regulatorio', 'ejecutivo', 'contratacion', 'medios']

MESES = ['', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


def e(s):
    return _html.escape(str(s or ''), quote=True)


# Siglas que deben sobrevivir al paso a minúsculas. La lista es corta y curada:
# meter siglas de 2 letras traería falsos ("SE", "LA") y arruinaría el texto.
_SIGLAS = (
    'UPC IPS EPS ESE SENA ICETEX INVIMA SGR IVA ARL POS TEA VIH DIAN CREG UPME '
    'ANLA DNP MEN SISBEN SGP TIC ONU OMS OIT OCDE IPC UVT SMMLV ESAL JAL CAR ANI '
    'ANH UNGRD SIC CNE RUNT SOAT PAE ICBF DANE CAJANAL FOMAG ADRES IPSS UPCM '
    'PGN CGR MIPG CONPES PND POT EOT SGSSS RIPS PQRSD IA'
).split()
_RX_SIGLAS = re.compile(r'(?<![A-Za-zÁÉÍÓÚÑ])(' + '|'.join(_SIGLAS) +
                        r')(?![A-Za-zÁÉÍÓÚÑ])', re.IGNORECASE)
# Nombres propios frecuentes en títulos de proyectos: se capitalizan, no se
# gritan. Lista corta a propósito — esto es un pase de legibilidad, no de estilo.
_PROPIOS = ('colombia colombiano colombiana ecopetrol bogota bogotá medellin '
            'medellín cali barranquilla cartagena antioquia cundinamarca '
            'santander atlantico atlántico bolivar bolívar valle magdalena '
            'amazonia amazonía orinoquia orinoquía pacifico pacífico caribe').split()
_RX_PROPIOS = re.compile(r'(?<![a-záéíóúñ])(' + '|'.join(_PROPIOS) + r')(?![a-záéíóúñ])')


def titulo_legible(t):
    """MAYÚSCULA SOSTENIDA → frase, preservando siglas.

    El registro del Senado guarda los títulos en caps y el de Cámara en frase,
    así que un digest sin esto mezcla las dos formas y se lee peor de lo que
    debería. Solo se toca lo que viene gritado (>60% de mayúsculas): un título
    ya en frase se deja intacto.
    """
    t = (t or '').strip()
    letras = [c for c in t if c.isalpha()]
    if not letras or sum(1 for c in letras if c.isupper()) / len(letras) < 0.6:
        return t
    s = t.lower()
    # Solo la inicial. Capitalizar después de cada punto parece más correcto
    # hasta que aparece una abreviatura: "ECOPETROL S.A. PARA…" salía como
    # "Ecopetrol s.a. Para…". Un título de proyecto no trae frases internas.
    s = re.sub(r'^([a-záéíóúñ])', lambda m: m.group(1).upper(), s)
    s = _RX_SIGLAS.sub(lambda m: m.group(1).upper(), s)
    s = _RX_PROPIOS.sub(lambda m: m.group(1).capitalize(), s)
    # "ley 30 de 1992" → mantener; los romanos solo tras 'artículo/título/capítulo'
    s = re.sub(r'\b(articulo|artículo|titulo|título|capitulo|capítulo|ley)\s+'
               r'([ivx]+)\b',
               lambda m: f'{m.group(1)} {m.group(2).upper()}', s)
    return s


def fecha_larga(f):
    try:
        d = dt.date.fromisoformat(f)
        return f'{d.day} de {MESES[d.month]} de {d.year}'
    except (ValueError, IndexError):
        return f


def asunto(digest, sector):
    altos = sector['altos']
    try:
        d = dt.date.fromisoformat(digest['fecha'])
        dia = f'{d.day} {MESES[d.month][:3]}'
    except (ValueError, IndexError):
        dia = digest['fecha']
    if altos:
        cuerpo = f'{altos} señal{"es" if altos != 1 else ""} alta{"s" if altos != 1 else ""}'
    else:
        cuerpo = f'{sector["total"]} movimientos'
    return f'Caudal · {sector["nombre"]} — {cuerpo} ({dia})'


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

def _chip(nivel):
    n = NIVEL.get(nivel, NIVEL['bajo'])
    return (f'<span style="display:inline-block;padding:2px 7px;border-radius:3px;'
            f'background:{n["fondo"]};color:{n["color"]};font-size:10px;'
            f'font-weight:700;letter-spacing:.08em;">{n["label"]}</span>')


def _meta_linea(ev):
    """Una línea de contexto según el pilar. Solo datos, sin adjetivos."""
    m = ev.get('meta') or {}
    p = ev['pilar']
    partes = []
    if p == 'congreso':
        if m.get('numero'):
            partes.append(f'PL {m["numero"]}')
        if m.get('camara'):
            partes.append(m['camara'].capitalize())
        if m.get('comision'):
            # Cámara ya manda "Comisión Primera Constitucional Permanente";
            # Senado manda "SEPTIMA" pelado. Sin esto sale "Comisión Comisión…".
            c = str(m['comision']).strip()
            partes.append(c if c.lower().startswith('comisi') else f'Comisión {c}')
        if m.get('autor'):
            partes.append(str(m['autor'])[:80])
    elif p == 'regulatorio':
        if m.get('fuente'):
            partes.append(str(m['fuente']))
        if m.get('resolucion'):
            partes.append(f'Res. {m["resolucion"]}')
        if m.get('monto'):
            partes.append(pesos(m['monto']))
    elif p == 'ejecutivo':
        if m.get('tipo_norma'):
            partes.append(f'{m["tipo_norma"]} {m.get("numero", "")}'.strip())
    elif p == 'contratacion':
        if m.get('valor'):
            partes.append(pesos(m['valor']))
        if m.get('departamento'):
            partes.append(str(m['departamento']))
    elif p == 'medios':
        if m.get('medio'):
            partes.append(str(m['medio']))
        if m.get('alcance'):
            partes.append(str(m['alcance']))
    if ev.get('fecha'):
        partes.append(ev['fecha'][:10])
    return ' · '.join(partes)


def _senal_html(ev):
    n = NIVEL.get(ev['nivel'], NIVEL['bajo'])
    titulo = e(titulo_legible(ev['titulo'])[:190])
    if ev.get('url'):
        titulo = (f'<a href="{e(ev["url"])}" style="color:{TEXTO};text-decoration:none;'
                  f'border-bottom:1px solid {BORDE};">{titulo}</a>')
    deltas = ''
    for d in (ev.get('meta') or {}).get('deltas_utiles', [])[:4]:
        valor = e(d['ahora'][:90])
        deltas += (f'<div style="font-size:12px;color:{TENUE};padding-top:3px;">'
                   f'<span style="color:{n["color"]};">▸</span> '
                   f'{e(d["etiqueta"])}: <span style="color:{TEXTO};">{valor}</span></div>')
    detalle = ''
    if ev.get('detalle'):
        detalle = (f'<div style="font-size:12px;color:{TENUE};padding-top:4px;'
                   f'line-height:1.45;">{e(ev["detalle"][:220])}</div>')

    # cobertura: la prensa NO es una señal aparte, es el eco de ésta.
    cobertura = ''
    if ev.get('cobertura'):
        medios = ev.get('cobertura_medios') or len(
            {c.get('medio') for c in ev['cobertura'] if c.get('medio')})
        filas = ''
        for c in ev['cobertura']:
            t = e(c['titulo'][:110])
            if c.get('url'):
                t = (f'<a href="{e(c["url"])}" style="color:{TENUE};'
                     f'text-decoration:underline;">{t}</a>')
            filas += (f'<div style="font-size:11px;color:{TENUE};padding-top:3px;">'
                      f'<b style="color:{TEXTO};">{e(c.get("medio") or "—")}</b> · {t}</div>')
        resto = ev.get('cobertura_total', 0) - len(ev['cobertura'])
        mas = (f'<div style="font-size:11px;color:{TENUE};padding-top:3px;">'
               f'+ {resto} nota{"s" if resto != 1 else ""} más</div>') if resto > 0 else ''
        cobertura = (
            f'<div style="margin-top:9px;padding:8px 10px;background:#0a0d16;'
            f'border-left:2px solid {TENUE};border-radius:3px;">'
            f'<div style="font-size:10px;letter-spacing:.1em;color:{TENUE};'
            f'font-weight:700;">ESTO YA LO REPORTARON {medios} MEDIO'
            f'{"S" if medios != 1 else ""}</div>{filas}{mas}</div>')

    return f'''
      <tr><td style="padding:0 0 10px 0;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
               style="background:{CARD};border:1px solid {BORDE};
                      border-left:3px solid {n["color"]};border-radius:4px;">
          <tr><td style="padding:12px 14px;">
            {_chip(ev['nivel'])}
            <span style="font-size:11px;color:{TENUE};padding-left:8px;">
              {e(_meta_linea(ev))}</span>
            <div style="font-size:14px;color:{TEXTO};line-height:1.45;padding-top:7px;
                        font-weight:500;">{titulo}</div>
            {detalle}
            {deltas}
            <div style="font-size:11px;color:{n["color"]};padding-top:8px;
                        font-style:italic;">por qué: {e(ev.get('porque', ''))}</div>
            {cobertura}
          </td></tr>
        </table>
      </td></tr>'''


def notas_cobertura(digest, sector):
    """Qué se miró y se decidió NO mostrar.

    Va al pie de cada digest a propósito: sin esto, un digest corto se lee como
    "no pasó nada" cuando a veces significa "se filtró mucho". Decir cuánto se
    descartó y por qué es lo que separa un filtro de una caja negra.
    """
    out = []
    pr = sector.get('prensa') or {}
    if pr.get('total'):
        extra = ''
        if pr.get('sueltos_omitidos'):
            extra += f' (+{pr["sueltos_omitidos"]} por encima del tope, ver digest.json)'
        if pr.get('empresa_sin_hecho'):
            extra += (f' · {pr["empresa_sin_hecho"]} nombraban una empresa vigilada pero '
                      f'sin hecho accionable detrás (noticia comercial rutinaria)')
        out.append(
            f'Prensa: se revisaron {pr["total"]} titulares del sector · '
            f'{pr.get("cobertura", 0)} quedaron colgados de una señal como cobertura · '
            f'{pr.get("sueltos", 0)} dispararon solos por nombrar una empresa vigilada '
            f'sin acto del Estado detrás{extra} · {pr.get("descartados", 0)} se '
            f'descartaron por ser eco sin hecho nuevo.')
    if sector.get('bajos'):
        out.append(f'Se omitieron {sector["bajos"]} señales de nivel bajo '
                   f'(honores, conmemorativos, actos procesales y de recaudo).')
    for a in digest.get('avisos') or []:
        out.append(f'{PILAR.get(a["pilar"], a["pilar"])}: {a["texto"]}')
    return out


def digest_html(digest, sector):
    fecha = fecha_larga(digest['fecha'])
    bloques = ''
    for pilar in PILAR_ORDEN:
        items = (sector['pilares'] or {}).get(pilar) or []
        if not items:
            continue
        omitidos = (sector.get('omitidos') or {}).get(pilar, 0)
        nota = ''
        if omitidos:
            nota = (f'<div style="font-size:11px;color:{TENUE};padding:0 0 10px 0;">'
                    f'+ {omitidos} más en este pilar, no mostradas por espacio. '
                    f'Están en el digest.json de la corrida.</div>')
        bloques += f'''
        <tr><td style="padding:16px 0 8px 0;">
          <div style="font-size:11px;letter-spacing:.14em;color:{AZUL};
                      font-weight:700;text-transform:uppercase;">
            {e(PILAR.get(pilar, pilar))}
            <span style="color:{TENUE};font-weight:400;letter-spacing:0;
                         text-transform:none;">· {len(items) + omitidos}</span>
          </div>
        </td></tr>
        {''.join(_senal_html(i) for i in items)}
        <tr><td>{nota}</td></tr>'''

    lineas = list(notas_cobertura(digest, sector))
    avisos = ''
    if lineas:
        filas = ''.join(
            f'<div style="font-size:11px;color:{TENUE};padding:2px 0;">· {e(t)}</div>'
            for t in lineas)
        avisos = f'''
        <tr><td style="padding:18px 0 0 0;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                 style="background:{CARD};border:1px solid {BORDE};border-radius:4px;">
            <tr><td style="padding:11px 14px;">
              <div style="font-size:10px;letter-spacing:.12em;color:{TENUE};
                          font-weight:700;padding-bottom:5px;">
                COBERTURA DE ESTA CORRIDA</div>
              {filas}
            </td></tr>
          </table>
        </td></tr>'''

    return f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(asunto(digest, sector))}</title></head>
<body style="margin:0;padding:0;background:{BG};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="background:{BG};padding:24px 12px;">
<tr><td align="center">
<table role="presentation" width="640" cellpadding="0" cellspacing="0"
       style="max-width:640px;width:100%;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">

  <tr><td style="padding-bottom:4px;">
    <span style="font-size:11px;letter-spacing:.2em;color:{TENUE};font-weight:700;">
      CAUDAL · ALERTAS</span>
  </td></tr>
  <tr><td style="padding-bottom:2px;">
    <div style="font-size:26px;color:{TEXTO};font-weight:700;letter-spacing:-.01em;">
      {e(sector['nombre'])}</div>
  </td></tr>
  <tr><td style="padding-bottom:14px;">
    <div style="font-size:13px;color:{TENUE};">
      {e(fecha)} · <b style="color:{TEXTO};">{sector['total']}</b> señales,
      <b style="color:{NIVEL['alto']['color']};">{sector['altos']}</b> altas
      {f"· Comisión {e(sector['comision'])}" if sector.get('comision') else ''}
    </div>
    <div style="height:2px;background:{AZUL};width:56px;margin-top:12px;"></div>
  </td></tr>

  {bloques}
  {avisos}

  <tr><td style="padding:22px 0 0 0;border-top:1px solid {BORDE};margin-top:18px;">
    <div style="font-size:11px;color:{TENUE};line-height:1.6;padding-top:14px;">
      Generado por el motor de alertas de Caudal a partir de fuentes oficiales ya
      publicadas: registro de proyectos de Senado y Cámara, actos de
      superintendencias, normativa de Presidencia, SECOP y prensa.
      El nivel de cada señal es una regla determinista, no una opinión: la línea
      «por qué» dice exactamente qué la disparó.<br><br>
      <b style="color:{TEXTO};">Ricardo.Ruiz</b> · ricardoruiz.co
    </div>
  </td></tr>

</table>
</td></tr></table>
</body></html>'''


# ---------------------------------------------------------------------------
# TEXTO PLANO
# ---------------------------------------------------------------------------

def digest_texto(digest, sector):
    L = []
    L.append(f'CAUDAL · ALERTAS — {sector["nombre"].upper()}')
    L.append(fecha_larga(digest['fecha']))
    L.append(f'{sector["total"]} señales · {sector["altos"]} altas')
    L.append('=' * 62)
    for pilar in PILAR_ORDEN:
        items = (sector['pilares'] or {}).get(pilar) or []
        if not items:
            continue
        omitidos = (sector.get('omitidos') or {}).get(pilar, 0)
        L.append('')
        L.append(f'{PILAR.get(pilar, pilar).upper()} ({len(items) + omitidos})')
        L.append('-' * 62)
        for ev in items:
            L.append(f'[{ev["nivel"].upper()}] {titulo_legible(ev["titulo"])[:150]}')
            meta = _meta_linea(ev)
            if meta:
                L.append(f'       {meta}')
            for d in (ev.get('meta') or {}).get('deltas_utiles', [])[:4]:
                L.append(f'       > {d["etiqueta"]}: {d["ahora"][:80]}')
            if ev.get('detalle'):
                L.append(f'       {ev["detalle"][:160]}')
            L.append(f'       por qué: {ev.get("porque", "")}')
            if ev.get('cobertura'):
                medios = ev.get('cobertura_medios') or len(
                    {c.get('medio') for c in ev['cobertura'] if c.get('medio')})
                L.append(f'       esto ya lo reportaron {medios} medios:')
                for c in ev['cobertura']:
                    L.append(f'         - {c.get("medio", "—")}: {c["titulo"][:90]}')
                resto = ev.get('cobertura_total', 0) - len(ev['cobertura'])
                if resto > 0:
                    L.append(f'         - (+ {resto} más)')
            if ev.get('url'):
                L.append(f'       {ev["url"][:110]}')
            L.append('')
        if omitidos:
            L.append(f'       (+ {omitidos} más en este pilar, ver digest.json)')
    lineas = notas_cobertura(digest, sector)
    if lineas:
        L.append('')
        L.append('COBERTURA DE ESTA CORRIDA')
        L.append('-' * 62)
        for t in lineas:
            L.append(f'· {t}')
    L.append('')
    L.append('Ricardo.Ruiz · ricardoruiz.co')
    return '\n'.join(L)


# ---------------------------------------------------------------------------
# CANAL DE OPERACIÓN (interno)
# ---------------------------------------------------------------------------

def asunto_operacion(digest):
    op = digest.get('operacion') or {}
    n, altos = len(op.get('problemas') or []), op.get('altos', 0)
    sev = 'CRÍTICO' if altos else 'aviso'
    return f'Caudal · operación [{sev}] — {n} problema{"s" if n != 1 else ""} ({digest["fecha"]})'


def operacion_html(digest):
    op = digest.get('operacion') or {}
    filas = ''
    for p in sorted(op.get('problemas') or [],
                    key=lambda x: 0 if x['nivel'] == 'alto' else 1):
        n = NIVEL.get(p['nivel'], NIVEL['bajo'])
        filas += f'''
        <tr><td style="padding:0 0 10px 0;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                 style="background:{CARD};border:1px solid {BORDE};
                        border-left:3px solid {n["color"]};border-radius:4px;">
            <tr><td style="padding:12px 14px;">
              {_chip(p['nivel'])}
              <span style="font-size:11px;color:{TENUE};padding-left:8px;">
                {e(p.get('origen', ''))}</span>
              <div style="font-size:14px;color:{TEXTO};padding-top:7px;font-weight:500;">
                {e(p['titulo'])}</div>
              <div style="font-size:12px;color:{TENUE};padding-top:4px;">
                {e(p.get('detalle', '')[:240])}</div>
              <div style="font-size:11px;color:{n["color"]};padding-top:8px;
                          font-style:italic;">por qué: {e(p.get('porque', ''))}</div>
            </td></tr>
          </table>
        </td></tr>'''

    ctx = ''
    if op.get('contexto'):
        items = ''.join(f'<div style="font-size:11px;color:{TENUE};padding:2px 0;">'
                        f'· {e(c)}</div>' for c in op['contexto'])
        ctx = f'''
        <tr><td style="padding:18px 0 0 0;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                 style="background:{CARD};border:1px solid {BORDE};border-radius:4px;">
            <tr><td style="padding:11px 14px;">
              <div style="font-size:10px;letter-spacing:.12em;color:{TENUE};
                          font-weight:700;padding-bottom:5px;">
                MIRADO Y DESCARTADO</div>{items}
            </td></tr></table>
        </td></tr>'''

    return f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(asunto_operacion(digest))}</title></head>
<body style="margin:0;padding:0;background:{BG};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="background:{BG};padding:24px 12px;">
<tr><td align="center">
<table role="presentation" width="640" cellpadding="0" cellspacing="0"
       style="max-width:640px;width:100%;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
  <tr><td style="padding-bottom:4px;">
    <span style="font-size:11px;letter-spacing:.2em;color:{TENUE};font-weight:700;">
      CAUDAL · OPERACIÓN</span></td></tr>
  <tr><td style="padding-bottom:2px;">
    <div style="font-size:26px;color:{TEXTO};font-weight:700;">El rastreo</div></td></tr>
  <tr><td style="padding-bottom:14px;">
    <div style="font-size:13px;color:{TENUE};">
      {e(fecha_larga(digest['fecha']))} · estado
      <b style="color:{NIVEL['alto']['color'] if op.get('altos') else TEXTO};">
        {e(op.get('estado', '?'))}</b> · {e(op.get('resumen', ''))}</div>
    <div style="height:2px;background:{NIVEL['alto']['color']};width:56px;
                margin-top:12px;"></div></td></tr>
  {filas}
  {ctx}
  <tr><td style="padding:22px 0 0 0;border-top:1px solid {BORDE};">
    <div style="font-size:11px;color:{TENUE};line-height:1.6;padding-top:14px;">
      Canal interno. Esto no va a ningún cliente: es el estado del rastreo que
      alimenta los digests. Si el rastreo se cae, «sin novedades» dejaría de
      significar «no pasó nada» y pasaría a significar «no sé» — este correo es
      lo que evita esa confusión.<br><br>
      Fuente: <code>tools/caudal/salud/check.py</code> ·
      generado {e(op.get('generado', ''))}
    </div></td></tr>
</table></td></tr></table>
</body></html>'''


def operacion_texto(digest):
    op = digest.get('operacion') or {}
    L = ['CAUDAL · OPERACIÓN', fecha_larga(digest['fecha']),
         f'estado: {op.get("estado")} · {op.get("resumen", "")}', '=' * 62, '']
    for p in sorted(op.get('problemas') or [],
                    key=lambda x: 0 if x['nivel'] == 'alto' else 1):
        L.append(f'[{p["nivel"].upper()}] ({p.get("origen")}) {p["titulo"]}')
        if p.get('detalle'):
            L.append(f'       {p["detalle"][:200]}')
        L.append(f'       por qué: {p.get("porque", "")}')
        L.append('')
    if op.get('contexto'):
        L.append('MIRADO Y DESCARTADO')
        L.append('-' * 62)
        for c in op['contexto']:
            L.append(f'· {c}')
    L.append('')
    L.append('Canal interno · ricardoruiz.co')
    return '\n'.join(L)
