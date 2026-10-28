#!/usr/bin/env python3
"""Video semanal · cuadros del 28-oct-2026 (pensional · JEP · plata del metro).

Copia de build_cuadros.py (edición del 27, atada a pensional/fiscal/laboral) con los temas
de esta edición. Mismo estilo y misma paleta.

  python3 tools/video-semanal/jep_votos.py 2026-10-28
  python3 tools/video-semanal/build_cuadros_2026-10-28.py 2026-10-28

Original:

Lee el contenido verificado de la semana (contenido-<semana>.json, escrito a mano con
sus fuentes) y los datos calculados (pensional_votos.py · escenarios.py), arma un HTML
por cuadro con la Helvetica Neue del repo y lo captura a PNG con Chrome headless.

  python3 tools/video-semanal/pensional_votos.py 2026-10-27
  python3 tools/video-semanal/escenarios.py 2026-10-27
  python3 tools/video-semanal/build_cuadros.py 2026-10-27

Salida: rrss/video/semana-<semana>/cuadros/{html,png}/
Los cuadros son material para el editor o para HyperFrames: cada uno lleva la
identidad de los videos de datos (fondo #060810, Helvetica Neue, azul y naranja).
Paleta de posturas validada con el validador de dataviz sobre #060810 (todos los
pares pasan): apoya #3987e5 · quiere cambiar #d95926 · intermedio #199e70.
"""
import html
import json
import math
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SEMANA = sys.argv[1] if len(sys.argv) > 1 else '2026-10-28'
C = json.load(open(REPO / f'tools/video-semanal/contenido-{SEMANA}.json'))
DATOS = REPO / 'Bases de datos/video-semanal' / SEMANA
PV = json.load(open(DATOS / 'pensional-votos.json'))
ESC = json.load(open(DATOS / 'escenarios.json'))
JEP = json.load(open(DATOS / 'jep.json'))
# Quién votó algo en la Cámara 2022-2026: separa «llegó este año» de «estaba y no votó».
PRESENTES = set(json.load(open(DATOS / 'camara-2022-2026-presentes.json')))
OUT = REPO / f'rrss/video/semana-{SEMANA}/cuadros'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
FONTS = '../../../fuente-congreso-60s/fonts'

FAVOR, CONTRA, MEDIO, SIN, NUEVO = '#3987e5', '#d95926', '#199e70', '#5b6275', '#161b2b'
# Cuadro vacío con borde naranja: no firmó, pero su voto suele coincidir con el del autor.
HUECO = 'hueco'
e = html.escape

CSS = f"""
@font-face {{ font-family: H; src: url("{FONTS}/helveticaneue-light.woff2"); font-weight: 300; }}
@font-face {{ font-family: H; src: url("{FONTS}/helveticaneue.woff2"); font-weight: 400; }}
@font-face {{ font-family: H; src: url("{FONTS}/helveticaneue-medium.woff2"); font-weight: 500; }}
@font-face {{ font-family: H; src: url("{FONTS}/helveticaneue-bold.woff2"); font-weight: 700; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: #060810; }}
body {{ font-family: H, 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #f4f3ef;
  background: radial-gradient(ellipse 900px 700px at 85% 0%, rgba(61,111,255,.16), transparent 60%),
              radial-gradient(ellipse 700px 600px at 0% 100%, rgba(249,115,22,.08), transparent 60%), #060810; }}
.f {{ position: absolute; inset: 0; padding: 150px 72px 0; }}
.k {{ font-size: 24px; letter-spacing: .18em; font-weight: 700; color: #f97316; text-transform: uppercase; }}
.k span {{ color: #7d8396; }}
h1 {{ font-size: 64px; line-height: 1.04; font-weight: 700; letter-spacing: -.02em; margin-top: 22px; }}
.sub {{ font-size: 30px; line-height: 1.32; color: #b9bdc9; font-weight: 300; margin-top: 20px; max-width: 930px; }}
.body {{ margin-top: 44px; }}
.foot {{ position: absolute; left: 72px; right: 72px; bottom: 150px; border-top: 1px solid #1c2233; padding-top: 18px;
  display: flex; justify-content: space-between; gap: 30px; font-size: 19px; color: #7d8396; line-height: 1.35; }}
.foot b {{ color: #f4f3ef; font-weight: 700; }}
.foot > div:last-child {{ white-space: nowrap; }}
.card {{ background: rgba(13,17,32,.85); border: 1px solid #1c2233; border-radius: 14px; }}
.leg {{ display: flex; flex-wrap: wrap; gap: 14px 28px; font-size: 22px; color: #b9bdc9; margin-top: 26px; }}
.leg i {{ display: inline-block; width: 22px; height: 22px; border-radius: 5px; vertical-align: -4px; margin-right: 10px; }}
"""


def pagina(n, total, kicker, titulo, sub, cuerpo, fuente):
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{e(titulo)}</title>
<style>{CSS}</style></head><body><div class="f">
<div class="k">{e(kicker)} <span>· {e(C['fecha_corta'])}</span></div>
<h1>{titulo}</h1>{f'<div class="sub">{sub}</div>' if sub else ''}
<div class="body">{cuerpo}</div></div>
<div class="foot"><div>Fuente: {e(fuente)}</div><div><b>Ricardo.Ruiz</b> · {n}/{total}</div></div>
</body></html>"""


def leyenda(items):
    return '<div class="leg">' + ''.join(
        (f'<span><i style="background:{NUEVO};border:3px solid {CONTRA};box-sizing:border-box"></i>{e(t)}</span>' if c == HUECO else f'<span><i style="background:{c};{"border:1px solid #2a3146;" if c == NUEVO else ""}"></i>{e(t)}</span>')
        for c, t in items) + '</div>'


# ─────────────────────────────────────────────────────────── piezas de gráfico
def waffle(grupos, por_fila=20, lado=30, gap=6, etiqueta=250):
    """grupos = [(nombre, [color, …], nota)] → filas de cuadritos con la bancada a la izquierda."""
    out = []
    for nombre, celdas, nota in grupos:
        filas = math.ceil(len(celdas) / por_fila)
        alto = filas * (lado + gap) - gap
        sq = ''.join(
            f'<rect x="{(i % por_fila) * (lado + gap)}" y="{(i // por_fila) * (lado + gap)}" width="{lado}" height="{lado}" rx="5" '
            + (f'fill="{NUEVO}" stroke="{CONTRA}" stroke-width="3"/>' if c == HUECO else f'fill="{c}" {"stroke=\"#2a3146\"" if c == NUEVO else ""}/>') for i, c in enumerate(celdas))
        out.append(
            f'<div style="display:flex;align-items:flex-start;gap:20px;margin-bottom:16px">'
            f'<div style="width:{etiqueta}px;font-size:23px;line-height:1.15;padding-top:3px">{e(nombre)}'
            f'<div style="font-size:19px;color:#7d8396;margin-top:3px">{e(nota)}</div></div>'
            f'<svg width="{por_fila * (lado + gap)}" height="{alto}">{sq}</svg></div>')
    return ''.join(out)


def barras_h(filas, ancho=560, alto=40, color=CONTRA, fmt=lambda v: f'{v:,.0f}', etiqueta=300, paso=56):
    """Barras horizontales en un solo SVG: etiqueta a la izquierda, valor al final de la barra."""
    maxv = max(v for _, v in filas)
    W, H = etiqueta + 24 + ancho + 220, paso * len(filas)
    g = ''
    for i, (nombre, v) in enumerate(filas):
        y = i * paso
        w = max(4, ancho * v / maxv)
        x0 = etiqueta + 24
        g += (f'<text x="{etiqueta}" y="{y + alto / 2 + 9}" text-anchor="end" font-size="25" fill="#f4f3ef">{e(nombre)}</text>'
              f'<rect x="{x0}" y="{y}" width="{w:.1f}" height="{alto}" rx="4" fill="{color}"/>'
              f'<text x="{x0 + w + 14:.1f}" y="{y + alto / 2 + 9}" font-size="24" fill="#b9bdc9">{e(fmt(v))}</text>')
    return f'<svg width="{W}" height="{H}" style="font-family:H,Helvetica Neue,sans-serif">{g}</svg>'


def apiladas(filas, ancho=520, alto=38, etiqueta=270, paso=52):
    """filas = [(nombre, [(valor, color), …], texto)] con escala común, en un solo SVG."""
    maxt = max(sum(v for v, _ in segs) for _, segs, _ in filas)
    W, H = etiqueta + 24 + ancho + 160, paso * len(filas)
    g = ''
    for i, (nombre, segs, texto) in enumerate(filas):
        y, x = i * paso, etiqueta + 24
        g += f'<text x="{etiqueta}" y="{y + alto / 2 + 9}" text-anchor="end" font-size="24" fill="#f4f3ef">{e(nombre)}</text>'
        for v, c in segs:
            w = ancho * v / maxt
            if w > 0:
                g += f'<rect x="{x:.1f}" y="{y}" width="{max(w - 2, 1):.1f}" height="{alto}" rx="4" fill="{c}"/>'
            x += w
        g += f'<text x="{etiqueta + 24 + ancho + 18}" y="{y + alto / 2 + 9}" font-size="23" fill="#b9bdc9">{e(texto)}</text>'
    return f'<svg width="{W}" height="{H}" style="font-family:H,Helvetica Neue,sans-serif">{g}</svg>'


def posturas(ext):
    def col(titulo, color, items):
        cards = ''.join(
            f'<div class="card" style="padding:20px 20px 22px;margin-bottom:16px;border-top:5px solid {color}">'
            f'<div style="font-size:25px;font-weight:700;line-height:1.15">{e(a)}</div>'
            f'<div style="font-size:21px;color:#b9bdc9;line-height:1.32;margin-top:9px">{e(b)}</div></div>' for a, b in items)
        return (f'<div style="flex:1;min-width:0"><div style="font-size:22px;font-weight:700;letter-spacing:.06em;'
                f'text-transform:uppercase;margin-bottom:16px;color:#f4f3ef"><i style="display:inline-block;width:18px;height:18px;'
                f'border-radius:4px;background:{color};margin-right:10px;vertical-align:-2px"></i>{e(titulo)}</div>{cards}</div>')
    arb = ext['arbitro']
    return (f'<div class="card" style="padding:20px 24px;margin-bottom:26px;display:flex;gap:18px;align-items:baseline">'
            f'<div style="font-size:21px;letter-spacing:.12em;font-weight:700;color:#7d8396;white-space:nowrap">DECIDE</div>'
            f'<div style="font-size:24px;line-height:1.3"><b>{e(arb[0])}</b> · <span style="color:#b9bdc9">{e(arb[1])}</span></div></div>'
            f'<div style="display:flex;gap:18px">'
            + col(ext['titulos'][0], CONTRA, ext['cambiar'])
            + col(ext['titulos'][1], MEDIO, ext['tiempo'])
            + col(ext['titulos'][2], FAVOR, ext['defender']) + '</div>')



# ─────────────────────────────────────────────────────────── clasificación (cuadros y web)
ORDEN = [FAVOR, CONTRA, SIN, NUEVO]


def clasifica_pensional():
    """Cada curul de la Cámara actual según lo que hizo su ocupante en junio de 2025."""
    import collections
    rep = {f['nombre']: f for f in PV['repitentes']}
    INT = json.load(open(REPO / 'Bases de datos/legislativo/fuerzas-internas-2026.json'))
    por_b = collections.defaultdict(list)
    for m in INT['camara']['miembros']:
        f = rep.get(m['n'], {})
        if f.get('acoger_2025') == 'Si' and f.get('reabrir_2025') != 'Si':
            c = FAVOR
        elif f.get('acoger_2025') == 'No' or f.get('reabrir_2025') == 'Si':
            c = CONTRA
        elif f or m['n'] in PRESENTES:
            c = SIN
        else:
            c = NUEVO
        por_b[m['b']].append((c, m['n']))
    return por_b


def clasifica_septima():
    """Miembros de la Comisión Séptima de Cámara según su voto en la reforma laboral."""
    import collections
    pb7 = collections.defaultdict(list)
    for m in ESC['septima_camara']['miembros']:
        if m.get('laboral_conciliacion_2025') == 'Si' or m.get('laboral_titulo_2024') == 'Si':
            c = FAVOR
        elif m.get('laboral_conciliacion_2025') or m.get('laboral_titulo_2024'):
            c = CONTRA
        elif m['nombre'] in PRESENTES:
            c = SIN
        else:
            c = NUEVO
        pb7[m['bancada']].append((c, m['nombre']))
    return pb7


PUENTE = [
    ('Víctor Manuel Salcedo', 'Partido de la U', CONTRA,
     'Autor de 5 de las proposiciones y, según El Tiempo, ponente de la subsanación. En 2025 fue de los 11 que pidieron reabrir el articulado y votó en contra de acoger la reforma.'),
    ('Nicolás Barguil', 'Partido Conservador · presidente de la Cámara', FAVOR,
     'Preside la Cámara que hoy debe subsanar. En 2025 votó por acoger la reforma y en contra de reabrirla.'),
    ('Juan Carlos Wills', 'Conservador · ya no está en la Cámara', SIN,
     'Presentó en 2025 la proposición para reabrir el articulado. Según el registro manual de la sesión, votó en contra de ella.')]
AUTORES_CUIDADO = [('Pacto Histórico', 32), ('Alianza Verde', 2), ('Movimiento Libres', 1),
                   ('Dignidad y Compromiso', 1), ('Sin cruce con el listado', 1)]

# ─────────────────────────────────────────────────────────── cuadros
def clasifica_jep():
    """Miembros de la Comisión Primera del Senado: firmó el cierre o cuánto coincide con el autor."""
    import collections
    pb = collections.defaultdict(list)
    for m in JEP['primera_senado']:
        k = m.get('coincide')
        if m['firmo']:
            c = CONTRA
        elif k is None:
            c = SIN
        elif k >= 60:
            c = HUECO
        elif k >= 40:
            c = MEDIO
        else:
            c = FAVOR
        pb[m['bancada']].append((c, m['nombre']))
    return pb


ORDEN_JEP = [CONTRA, HUECO, MEDIO, FAVOR, SIN]
ESTADO_JEP = {CONTRA: 'Firmó el cierre de la JEP', HUECO: 'No firmó; suele votar con el autor (60 % o más)',
              MEDIO: 'Coincide a veces con el autor (40 a 60 %)', FAVOR: 'Suele votar distinto al autor (menos de 40 %)',
              SIN: 'Sin dato de coincidencia'}


def cuadros():
    P, J, F = C['pensional'], C['jep'], C['fiscal']
    fuentes = C['fuentes']
    q = []

    # 0 · portada
    filas = ''.join(
        f'<div class="card" style="padding:30px 32px;margin-bottom:24px;display:flex;gap:28px">'
        f'<div style="font-size:88px;font-weight:700;color:#3d6fff;line-height:.9;width:70px">{t["n"]}</div>'
        f'<div><div style="font-size:44px;font-weight:700;line-height:1.08">{e(t["tema"])}</div>'
        f'<div style="font-size:25px;color:#f97316;font-weight:500;margin-top:10px">{e(t["donde"])}</div>'
        f'<div style="font-size:26px;color:#b9bdc9;line-height:1.32;margin-top:10px">{e(t["porque"])}</div></div></div>'
        for t in C['temas'])
    q.append(('00-portada', 'Lo que se decide mañana', 'Lo que se decide mañana en el Congreso',
              'Tres temas, elegidos por lo que hay en el orden del día y por cuánto pesan en la prensa de los últimos tres días.',
              filas, 'órdenes del día de Senado y Cámara · prensa nacional 25-27 oct · Caudal'))

    # 1 · pensional · qué se vota
    ESTADO_TXT = {'negada': 'NEGADA EL MARTES', 'pacto': 'PACTO: APROBARLA (SEGÚN EL TIEMPO)', 'pendiente': 'PENDIENTE'}
    ESTADO_COLOR = {'negada': '#7d8396', 'pacto': MEDIO, 'pendiente': '#f97316'}
    grupos = ''
    for g in P['proposiciones']:
        items = ''.join(
            f'<div style="display:flex;gap:18px;padding:7px 0;border-top:1px solid #1c2233;{"opacity:.45" if it[2:] == ["negada"] else ""}">'
            f'<div style="width:130px;font-size:23px;font-weight:700;color:{CONTRA if it[0] == "Art. 36" else "#f4f3ef"}">{e(it[0])}</div>'
            f'<div style="flex:1;font-size:23px;line-height:1.25;color:{"#f4f3ef" if it[0] == "Art. 36" else "#b9bdc9"}">{e(it[1])}'
            f'{f"<div style=margin-top:3px;font-size:19px;font-weight:700;letter-spacing:.04em;color:{ESTADO_COLOR[it[2]]}>{ESTADO_TXT[it[2]]}</div>" if len(it) > 2 else ""}</div></div>'
            for it in g['items'])
        grupos += (f'<div class="card" style="padding:20px 26px 10px;margin-bottom:20px">'
                   f'<div style="font-size:27px;font-weight:700">Proposiciones de {e(g["autor"])} '
                   f'<span style="font-weight:400;color:#7d8396;font-size:22px">· {e(g["nota"])}</span></div>'
                   f'<div style="margin-top:12px">{items}</div></div>')
    q.append(('01-pensional-que-se-vota', 'Reforma pensional', 'Quedan 7 cambios por votar en 6 artículos',
              'El martes se negaron los 3 de Zabaraín y la sesión se cayó sin quórum. Según El Tiempo, las bancadas pactaron aprobar 2 y negar el resto.',
              grupos, 'orden del día de la Plenaria de Cámara del 27-oct-2026 · El Tiempo · Semana · El País'))

    # 2 · pensional · el reloj
    hitos = ''
    for i, (f, t, d) in enumerate(P['reloj']):
        hoy = d == 'mañana'
        hitos += (f'<div style="display:flex;gap:28px;position:relative;padding-bottom:30px">'
                  f'<div style="width:210px;text-align:right;font-size:25px;font-weight:700;color:{"#f97316" if hoy else "#f4f3ef"}">{e(f)}</div>'
                  f'<div style="width:22px;display:flex;justify-content:center"><div style="width:20px;height:20px;border-radius:50%;'
                  f'margin-top:6px;background:{"#f97316" if hoy else "#3d6fff"};box-shadow:0 0 0 5px #060810"></div></div>'
                  f'<div style="flex:1"><div style="font-size:27px;line-height:1.28">{e(t)}</div>'
                  f'<div style="font-size:22px;color:#7d8396;margin-top:5px">{e(d)}</div></div></div>')
    cuerpo = (f'<div style="position:relative"><div style="position:absolute;left:248px;top:10px;bottom:40px;width:2px;background:#1c2233"></div>'
              f'{hitos}</div>')
    q.append(('02-pensional-reloj', 'Reforma pensional', 'Mañana puede ser el último día, o no',
              'Si la Corte concede la prórroga, la Cámara gana tiempo. Si no, debe votar antes de que venza el plazo.',
              cuerpo, 'Corte Constitucional (C-264 de 2026) · actas de la Cámara · Caracol Radio · Cambio · Valora Analitik'))

    # 3 · pensional · quién vota
    por_b = {b: [c for c, _ in v] for b, v in clasifica_pensional().items()}
    orden = sorted(por_b.items(), key=lambda kv: -len(kv[1]))
    grandes = [(b, sorted(cs, key=[FAVOR, CONTRA, SIN, NUEVO].index)) for b, cs in orden if len(cs) >= 4]
    chicas = [c for b, cs in orden if len(cs) < 4 for c in cs]
    n_chicas = sum(1 for b, cs in orden if len(cs) < 4)
    grupos = [(b, cs, f'{len(cs)} curules') for b, cs in grandes]
    grupos.append((f'Otras {n_chicas} bancadas', sorted(chicas, key=[FAVOR, CONTRA, SIN, NUEVO].index), f'{len(chicas)} curules'))
    total = sum(len(cs) for cs in por_b.values())
    nuevos = sum(cs.count(NUEVO) for cs in por_b.values())
    fav = sum(cs.count(FAVOR) for cs in por_b.values())
    con = sum(cs.count(CONTRA) for cs in por_b.values())
    sin = sum(cs.count(SIN) for cs in por_b.values())
    cuerpo = (waffle(grupos) + leyenda([
        (FAVOR, f'En 2025 votó por acoger la reforma ({fav})'),
        (CONTRA, f'En 2025 votó en contra o pidió reabrirla ({con})'),
        (SIN, f'Estaba en la Cámara, no votó en 2025 ({sin})'),
        (NUEVO, f'Llegó a la Cámara este año ({nuevos})')]))
    q.append(('03-pensional-quien-vota', 'Reforma pensional', f'{nuevos} de {total} representantes llegaron después de la reforma',
              'Cada cuadro es una curul de la Cámara actual, con lo que hizo su ocupante en la votación de junio de 2025.',
              cuerpo, 'votación nominal de la Cámara, 28-jun-2025 (electrónica y manual) · listado oficial de representantes 2026-2030'))

    # 4 · pensional · el puente con 2025
    tarjetas = ''.join(
        f'<div class="card" style="padding:22px 26px;margin-bottom:18px;border-left:6px solid {c}">'
        f'<div style="font-size:30px;font-weight:700">{e(n)}</div><div style="font-size:21px;color:#7d8396;margin-top:4px">{e(p)}</div>'
        f'<div style="font-size:25px;line-height:1.33;color:#b9bdc9;margin-top:12px">{e(t)}</div></div>' for n, p, c, t in PUENTE)
    barra = (f'<div class="card" style="padding:26px 28px;margin-bottom:28px">'
             f'<div style="font-size:24px;color:#b9bdc9">28 de junio de 2025 · ¿reabrir el articulado para votar estas proposiciones?</div>'
             f'<svg width="900" height="54" style="margin-top:18px"><rect x="0" y="0" width="{900 * 100 / 111 - 3:.0f}" height="54" rx="6" fill="{CONTRA}"/>'
             f'<rect x="{900 * 100 / 111:.0f}" y="0" width="{900 * 11 / 111:.0f}" height="54" rx="6" fill="{FAVOR}"/></svg>'
             f'<div style="display:flex;justify-content:space-between;font-size:30px;font-weight:700;margin-top:12px">'
             f'<span>100 votaron no</span><span>11 votaron sí</span></div>'
             f'<div style="font-size:23px;color:#7d8396;margin-top:10px">Por esa negativa la Corte encontró el vicio que hoy hay que corregir.</div></div>')
    ej = (f'<div style="font-size:25px;line-height:1.38;color:#b9bdc9;margin-top:10px">'
          f'<b style="color:#f4f3ef">Un ejemplo concreto:</b> hoy la ley descuenta 50 semanas por cada hijo, hasta tres, '
          f'sin bajar de 850. La proposición de Salcedo sube ese piso a 1.000 y deja fuera a quienes están en el régimen de transición.</div>')
    q.append(('04-pensional-puente', 'Reforma pensional', 'Lo que se vota ya se negó a debatir una vez',
              None, barra + tarjetas + ej,
              'votación nominal de la Cámara, 28-jun-2025, acta 43742 (incluye el voto manual escaneado) · La Silla Vacía'))

    # 5 · pensional · fuerzas externas
    q.append(('05-pensional-fuerzas', 'Reforma pensional', 'Quién empuja y quién frena fuera del Congreso', None,
              posturas(P['externos']), 'Caracol Radio · Procuraduría · El Colombiano · Chica Noticias · Valora Analitik · La Silla Vacía'))

    # 6 · JEP · qué se vota
    cols = ''
    for i, (titulo, base, items) in enumerate(J['hoy_vs_proyecto']):
        color = '#7d8396' if i == 0 else CONTRA
        lis = ''.join(f'<div style="display:flex;gap:14px;padding:12px 0;border-top:1px solid #1c2233;font-size:25px;line-height:1.32;'
                      f'color:{"#b9bdc9" if i == 0 else "#f4f3ef"}"><span style="color:{color};font-weight:700">—</span><span>{e(t)}</span></div>'
                      for t in items)
        cols += (f'<div class="card" style="padding:22px 26px 12px;margin-bottom:22px;border-top:5px solid {color}">'
                 f'<div style="font-size:29px;font-weight:700">{e(titulo)}</div>'
                 f'<div style="font-size:21px;color:#7d8396;margin:4px 0 10px">{e(base)}</div>{lis}</div>')
    q.append(('06-jep-que-se-vota', 'Cierre de la JEP', 'El Senado vota ponerle fecha de cierre a la JEP',
              'Es una reforma a la Constitución. Mañana sería su primer debate de ocho.',
              cols, 'orden del día de la Comisión Primera del Senado, 28-oct-2026 · Acto Legislativo 01 de 2017 · Infobae'))

    # 7 · JEP · reloj + cifras en disputa
    hitos = ''
    for f, t, d in J['reloj']:
        hoy = d == 'mañana'
        hitos += (f'<div style="display:flex;gap:24px;padding-bottom:20px">'
                  f'<div style="width:190px;text-align:right;font-size:24px;font-weight:700;color:{"#f97316" if hoy else "#f4f3ef"}">{e(f)}</div>'
                  f'<div style="width:22px;display:flex;justify-content:center"><div style="width:18px;height:18px;border-radius:50%;'
                  f'margin-top:6px;background:{"#f97316" if hoy else "#3d6fff"};box-shadow:0 0 0 5px #060810"></div></div>'
                  f'<div style="flex:1"><div style="font-size:25px;line-height:1.26">{e(t)}</div>'
                  f'{f"<div style=\"font-size:21px;color:#7d8396;margin-top:3px\">{e(d)}</div>" if d else ""}</div></div>')
    reloj = (f'<div style="position:relative"><div style="position:absolute;left:224px;top:10px;bottom:30px;width:2px;background:#1c2233"></div>'
             f'{hitos}</div>')
    tiles = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:20px">' + ''.join(
        f'<div class="card" style="padding:20px 22px;border-top:5px solid {CONTRA if i < 2 else FAVOR}">'
        f'<div style="font-size:46px;font-weight:700;letter-spacing:-.02em">{e(v)}</div>'
        f'<div style="font-size:23px;line-height:1.25;margin-top:6px">{e(t)}</div>'
        f'<div style="font-size:19px;color:#7d8396;margin-top:8px;line-height:1.3">{e(s)}</div></div>'
        for i, (v, t, s) in enumerate(J['cifras'])) + '</div>'
    rep17 = JEP['jep_2017']['senadores_actuales_que_votaron']
    nota17 = (f'<div class="card" style="padding:20px 24px;margin-top:18px;font-size:24px;line-height:1.36;color:#b9bdc9">'
              f'En 2017 el Senado creó la JEP con 57 votos contra 4. De los 103 senadores de hoy solo '
              f'<b style="color:#f4f3ef">{len(rep17)} votaron entonces</b>, los {len(rep17)} por el sí (Iván Cepeda, Antonio José Correa y Lidio García). '
              f'Ninguno está en la Comisión Primera.</div>')
    q.append(('07-jep-reloj-y-cifras', 'Cierre de la JEP', 'Ocho años después, dos maneras de contar la JEP',
              None, reloj + tiles + nota17,
              'Acto Legislativo 01 de 2017 · voto nominal del Senado, marzo de 2017 · Infobae · Diario La Libertad'))

    # 8 · JEP · fuerzas internas
    pb = clasifica_jep()
    grupos = [(b, sorted([c for c, _ in v], key=ORDEN_JEP.index), f'{len(v)} {"miembro" if len(v) == 1 else "miembros"}')
              for b, v in sorted(pb.items(), key=lambda kv: (-len(kv[1]), kv[0]))]
    todos = [c for v in pb.values() for c, _ in v]
    n = {c: todos.count(c) for c in ORDEN_JEP}
    firm = [(b, v) for b, v in JEP['firmantes_por_bancada'].items() if v > 1]
    sueltos = [b for b, v in JEP['firmantes_por_bancada'].items() if v == 1]
    if sueltos:
        firm.append((f'{", ".join(sueltos[:-1])} y {sueltos[-1]}' if len(sueltos) > 1 else sueltos[0], len(sueltos)))
    cuerpo = (waffle(grupos, por_fila=6, lado=42, gap=8, etiqueta=330)
              + leyenda([(c, f'{ESTADO_JEP[c]} ({n[c]})') for c in ORDEN_JEP if n[c]])
              + f'<div style="font-size:27px;font-weight:700;margin-top:36px">Quién firma el cierre ({JEP["n_firmantes"]} congresistas)</div>'
              + '<div style="margin-top:16px">' + barras_h(firm[:-1], ancho=380, alto=32, color=CONTRA, fmt=str, etiqueta=320, paso=44) + '</div>'
              + f'<div style="font-size:22px;color:#7d8396;margin-top:6px">Además, uno de cada uno: {e(firm[-1][0])}.</div>')
    q.append(('08-jep-fuerzas-internas', 'Cierre de la JEP', f'{n[CONTRA]} de los {len(todos)} que votan mañana firmaron el cierre',
              f'Con los {n[HUECO]} del Centro Democrático suman {n[CONTRA] + n[HUECO]}. Los {n[MEDIO]} liberales quedan en el medio. '
              'La coincidencia sale de 15 votaciones disputadas de este año: es una pista, no un pronóstico.',
              cuerpo, 'voto nominal del Senado, API app.senado.gov.co (2017 y 2026) · orden del día de la Comisión Primera'))

    # 9 · JEP · fuerzas externas
    q.append(('09-jep-fuerzas', 'Cierre de la JEP', 'Quién empuja y quién frena fuera del Congreso', None,
              posturas(J['externos']), 'El Heraldo · El Universal · Infobae · Vanguardia · Valora Analitik · La FM'))

    # 10 · fiscal · cifras
    tiles = ''.join(
        f'<div class="card" style="padding:28px 30px;margin-bottom:22px">'
        f'<div style="font-size:72px;font-weight:700;letter-spacing:-.02em;color:{"#f97316" if i == 3 else "#f4f3ef"}">{e(v)}</div>'
        f'<div style="font-size:30px;font-weight:500;margin-top:6px">{e(t)}</div>'
        f'<div style="font-size:23px;color:#7d8396;margin-top:8px;line-height:1.3">{e(s)}</div></div>'
        for i, (v, t, s) in enumerate(F['cifras']))
    q.append(('10-metro-cifras', 'Plata del metro para la luz', 'El ajuste de 2026 toca dos obras de Bogotá',
              'Mañana Hacienda, Planeación, Minas y Superservicios van a las comisiones económicas. El proyecto se anuncia para votarlo después.',
              tiles, 'orden del día de las Comisiones Económicas Conjuntas, 28-oct-2026 · La República · Portafolio · El Espectador'))

    # 11 · fiscal · de dónde sale el $1,2 billones
    orig = F['origen']
    tot = sum(v for _, v in orig)
    W = 900
    x = 0
    seg = ''
    lbl = ''
    for (nombre, v), c in zip(orig, [CONTRA, SIN, CONTRA]):
        w = W * v / tot
        seg += f'<rect x="{x:.1f}" y="0" width="{w - 3:.1f}" height="70" rx="6" fill="{c}"/>'
        lbl += (f'<div style="width:{w:.0f}px;padding-right:10px"><div style="font-size:34px;font-weight:700">${v}.000 M</div>'
                f'<div style="font-size:22px;color:#b9bdc9;line-height:1.25;margin-top:4px">{e(nombre)}</div></div>')
        x += w
    flujo = (f'<div class="card" style="padding:28px 28px 30px">'
             f'<div style="font-size:26px;font-weight:700">De dónde sale el $1,2 billones para el sector eléctrico</div>'
             f'<svg width="{W}" height="70" style="margin-top:22px">{seg}</svg>'
             f'<div style="display:flex;margin-top:14px">{lbl}</div>'
             f'<div style="font-size:23px;color:#7d8396;margin-top:22px;line-height:1.35">En naranja, lo que sale de Bogotá: $750.000 millones, el 62 %. '
             f'El resto sale de los subsidios de energía del Ministerio de Minas.</div></div>')
    ver = ''.join(
        f'<div class="card" style="padding:20px 24px;margin-top:18px;border-left:6px solid {c}">'
        f'<div style="font-size:24px;font-weight:700">{e(a)}</div><div style="font-size:23px;color:#b9bdc9;line-height:1.34;margin-top:8px">{e(b)}</div></div>'
        for a, b, c in [
            ('Lo que dice Hacienda', 'Esas obras no alcanzan a ejecutar la plata en 2026; el cambio no toca 2027. Y fue el gobierno Petro el que movió los desembolsos del metro en el otrosí de octubre de 2025.', CONTRA),
            ('Lo que dice El Tiempo', 'La plata no se pierde: pasa de 2026 a 2027. El profesor Darío Hidalgo dice que la financiación del metro no está en riesgo.', MEDIO)])
    q.append(('11-metro-origen', 'Plata del metro para la luz', 'El 62 % de la plata para la luz sale de Bogotá',
              None, flujo + ver, 'La República · La FM · El Tiempo (27-oct-2026)'))

    # 12 · fiscal · fuerzas internas (voto del presupuesto en el Senado)
    pg = ESC['senado_pgn2027_19oct']['por_bancada']
    filas = []
    for b, xx in pg.items():
        si, sr = xx.get('Sí', 0), xx.get('sin registro', 0)
        if si + sr >= 3:
            filas.append((b, [(si, FAVOR), (sr, SIN)], f'{si} de {si + sr}'))
    otras = [(b, xx) for b, xx in pg.items() if sum(xx.values()) < 3]
    si_o = sum(xx.get('Sí', 0) for _, xx in otras)
    tot_o = sum(sum(xx.values()) for _, xx in otras)
    filas.append((f'Otras {len(otras)} bancadas', [(si_o, FAVOR), (tot_o - si_o, SIN)], f'{si_o} de {tot_o}'))
    eco = ESC['economicas_conjuntas']
    n_eco = len(eco['miembros'])
    cuerpo = (apiladas(filas) + leyenda([(FAVOR, 'Votó sí al Presupuesto 2027'), (SIN, 'Sin voto registrado')])
              + f'<div class="card" style="padding:22px 26px;margin-top:30px;font-size:25px;line-height:1.38;color:#b9bdc9">'
                f'Mañana se sientan <b style="color:#f4f3ef">{n_eco} congresistas</b> de las comisiones terceras y cuartas. '
                f'El Pacto Histórico es la bancada más grande en las dos ({eco["por_bancada_camara"]["Pacto Histórico"]["total"]} representantes y '
                f'{eco["por_bancada_senado"]["Pacto Histórico"]["total"]} senadores), y ninguno de sus 7 senadores en esas comisiones votó el presupuesto de 2027.</div>')
    q.append(('12-metro-fuerzas-internas', 'Plata del metro para la luz',
              'Las mismas comisiones que vieron pasar el presupuesto sin el Pacto',
              f'Plenaria del Senado, 19 de octubre: {ESC["senado_pgn2027_19oct"]["total_si"]} votos por el sí al Presupuesto 2027 y ninguno por el no.',
              cuerpo, fuentes['fiscal'][4] + ' · listado oficial de comisiones'))

    # 13 · fiscal · fuerzas externas
    q.append(('13-metro-fuerzas', 'Plata del metro para la luz', 'Quién empuja y quién frena fuera del Congreso', None,
              posturas(F['externos']), 'Prensa Cámara (27-oct) · La FM · La República · El Tiempo · Portafolio'))
    return q


def main():
    (OUT / 'html').mkdir(parents=True, exist_ok=True)
    (OUT / 'png').mkdir(parents=True, exist_ok=True)
    q = cuadros()
    for i, (slug, kicker, titulo, sub, cuerpo, fuente) in enumerate(q):
        h = OUT / 'html' / f'{slug}.html'
        h.write_text(pagina(i + 1, len(q), kicker, e(titulo), e(sub) if sub else '', cuerpo, fuente), encoding='utf-8')
        png = OUT / 'png' / f'{slug}.png'
        subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1',
                        '--window-size=1080,1920', '--virtual-time-budget=3000', f'--screenshot={png}', h.as_uri()],
                       check=True, capture_output=True)
        print('✓', png.relative_to(REPO))


if __name__ == '__main__':
    main()
