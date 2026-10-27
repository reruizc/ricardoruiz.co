#!/usr/bin/env python3
"""Video semanal · cuadros verticales (1080×1920) para «Lo que se decide mañana».

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
SEMANA = sys.argv[1] if len(sys.argv) > 1 else '2026-10-27'
C = json.load(open(REPO / f'tools/video-semanal/contenido-{SEMANA}.json'))
DATOS = REPO / 'Bases de datos/video-semanal' / SEMANA
PV = json.load(open(DATOS / 'pensional-votos.json'))
ESC = json.load(open(DATOS / 'escenarios.json'))
# Quién votó algo en la Cámara 2022-2026: separa «llegó este año» de «estaba y no votó».
PRESENTES = set(json.load(open(DATOS / 'camara-2022-2026-presentes.json')))
OUT = REPO / f'rrss/video/semana-{SEMANA}/cuadros'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
FONTS = '../../../fuente-congreso-60s/fonts'

FAVOR, CONTRA, MEDIO, SIN, NUEVO = '#3987e5', '#d95926', '#199e70', '#5b6275', '#161b2b'
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
        f'<span><i style="background:{c};{"border:1px solid #2a3146;" if c == NUEVO else ""}"></i>{e(t)}</span>'
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
            f'fill="{c}" {"stroke=\"#2a3146\"" if c == NUEVO else ""}/>' for i, c in enumerate(celdas))
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
     'Autor de 5 de las proposiciones. En 2025 fue de los 11 que pidieron reabrir el articulado y votó en contra de acoger la reforma.'),
    ('Nicolás Barguil', 'Partido Conservador · presidente de la Cámara', FAVOR,
     'Mañana conduce la sesión. En 2025 votó por acoger la reforma y en contra de reabrirla.'),
    ('Juan Carlos Wills', 'Conservador · ya no está en la Cámara', SIN,
     'Presentó en 2025 la proposición para reabrir el articulado. Según el registro manual de la sesión, votó en contra de ella.')]
AUTORES_CUIDADO = [('Pacto Histórico', 32), ('Alianza Verde', 2), ('Movimiento Libres', 1),
                   ('Dignidad y Compromiso', 1), ('Sin cruce con el listado', 1)]

# ─────────────────────────────────────────────────────────── cuadros
def cuadros():
    P, F, L = C['pensional'], C['fiscal'], C['laboral']
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
              filas, 'órdenes del día de Senado y Cámara · prensa nacional 24-26 oct · Caudal'))

    # 1 · pensional · qué se vota
    grupos = ''
    for g in P['proposiciones']:
        items = ''.join(
            f'<div style="display:flex;gap:18px;padding:11px 0;border-top:1px solid #1c2233">'
            f'<div style="width:130px;font-size:23px;font-weight:700;color:{CONTRA if a == "Art. 36" else "#f4f3ef"}">{e(a)}</div>'
            f'<div style="flex:1;font-size:24px;line-height:1.3;color:{"#f4f3ef" if a == "Art. 36" else "#b9bdc9"}">{e(t)}</div></div>'
            for a, t in g['items'])
        grupos += (f'<div class="card" style="padding:20px 26px 10px;margin-bottom:20px">'
                   f'<div style="font-size:27px;font-weight:700">Proposiciones de {e(g["autor"])} '
                   f'<span style="font-weight:400;color:#7d8396;font-size:22px">· {e(g["nota"])}</span></div>'
                   f'<div style="margin-top:12px">{items}</div></div>')
    q.append(('01-pensional-que-se-vota', 'Reforma pensional', 'Mañana la Cámara vota 10 cambios a la reforma',
              'La Corte dejó en pie cerca del 90 % de la ley y devolvió 9 artículos. Si la Cámara no los vota, esos artículos pueden caer.',
              grupos, fuentes['pensional'][0] + ' · La Silla Vacía · La República'))

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
    q.append(('02-pensional-reloj', 'Reforma pensional', 'Dos años y tres votaciones después, otra vez a la Cámara',
              None, cuerpo, 'Corte Constitucional (C-264 de 2026, Auto 841 de 2025) · actas de la Cámara · La República · Valora Analitik'))

    # 3 · pensional · quién vota mañana
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
    personas = PUENTE
    tarjetas = ''.join(
        f'<div class="card" style="padding:22px 26px;margin-bottom:18px;border-left:6px solid {c}">'
        f'<div style="font-size:30px;font-weight:700">{e(n)}</div><div style="font-size:21px;color:#7d8396;margin-top:4px">{e(p)}</div>'
        f'<div style="font-size:25px;line-height:1.33;color:#b9bdc9;margin-top:12px">{e(t)}</div></div>' for n, p, c, t in personas)
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
    q.append(('04-pensional-puente', 'Reforma pensional', 'Lo que se vota mañana ya se negó a debatir una vez',
              None, barra + tarjetas + ej,
              'votación nominal de la Cámara, 28-jun-2025, acta 43742 (incluye el voto manual escaneado) · La Silla Vacía'))

    # 5 · pensional · fuerzas externas
    q.append(('05-pensional-fuerzas', 'Reforma pensional', 'Quién empuja y quién frena fuera del Congreso', None,
              posturas(P['externos']), 'La Silla Vacía · Valora Analitik · Cambio · La FM · Forbes'))

    # 6 · fiscal · cifras
    tiles = ''.join(
        f'<div class="card" style="padding:28px 30px;margin-bottom:22px">'
        f'<div style="font-size:72px;font-weight:700;letter-spacing:-.02em;color:{"#f97316" if i == 3 else "#f4f3ef"}">{e(v)}</div>'
        f'<div style="font-size:30px;font-weight:500;margin-top:6px">{e(t)}</div>'
        f'<div style="font-size:23px;color:#7d8396;margin-top:8px;line-height:1.3">{e(s)}</div></div>'
        for i, (v, t, s) in enumerate(F['cifras']))
    q.append(('06-fiscal-cifras', 'Presupuesto y ajuste fiscal', 'Un presupuesto por decreto y una semana de recortes',
              'Mañana el ministro Miguel Gómez presenta ante las comisiones económicas la modificación del presupuesto de 2026 y el de regalías 2027-2028.',
              tiles, fuentes['fiscal'][1] + ' · ' + fuentes['fiscal'][3]))

    # 7 · fiscal · recorte por entidad
    cuerpo = barras_h(F['recorte_entidades'], ancho=440, alto=44, paso=62, color=CONTRA, fmt=lambda v: f'${v:,.1f} mil M'.replace(',', 'X').replace('.', ',').replace('X', '.'))
    cuerpo += '<div style="font-size:23px;color:#7d8396;margin-top:20px">Miles de millones de pesos recortados al presupuesto de 2026. El total es $13,81 billones.</div>'
    q.append(('07-fiscal-recorte', 'Presupuesto y ajuste fiscal', 'Dónde pegó el recorte de 2026',
              'Las doce entidades más afectadas por el Decreto 1585, según El País.', cuerpo,
              'Decreto 1585 de 2026 · El País'))

    # 8 · fiscal · fuerzas internas (voto del presupuesto en el Senado)
    pg = ESC['senado_pgn2027_19oct']['por_bancada']
    filas = []
    for b, x in pg.items():
        si, sr = x.get('Sí', 0), x.get('sin registro', 0)
        if si + sr >= 3:
            filas.append((b, [(si, FAVOR), (sr, SIN)], f'{si} de {si + sr}'))
    otras = [(b, x) for b, x in pg.items() if sum(x.values()) < 3]
    si_o = sum(x.get('Sí', 0) for _, x in otras)
    tot_o = sum(sum(x.values()) for _, x in otras)
    filas.append((f'Otras {len(otras)} bancadas', [(si_o, FAVOR), (tot_o - si_o, SIN)], f'{si_o} de {tot_o}'))
    eco = ESC['economicas_conjuntas']
    n_eco = len(eco['miembros'])
    cuerpo = (apiladas(filas) + leyenda([(FAVOR, 'Votó sí al Presupuesto 2027'), (SIN, 'Sin voto registrado')])
              + f'<div class="card" style="padding:22px 26px;margin-top:30px;font-size:25px;line-height:1.38;color:#b9bdc9">'
                f'Mañana se sientan <b style="color:#f4f3ef">{n_eco} congresistas</b> de las comisiones terceras y cuartas. '
                f'El Pacto Histórico es la bancada más grande en las dos cámaras ({eco["por_bancada_camara"]["Pacto Histórico"]["total"]} representantes y '
                f'{eco["por_bancada_senado"]["Pacto Histórico"]["total"]} senadores), y ninguno de sus 7 senadores en esas comisiones votó el presupuesto.</div>')
    q.append(('08-fiscal-fuerzas-internas', 'Presupuesto y ajuste fiscal',
              'En el Senado, el presupuesto pasó sin un solo voto del Pacto',
              f'Plenaria del 19 de octubre: {ESC["senado_pgn2027_19oct"]["total_si"]} votos por el sí y ninguno por el no. Los demás senadores no registraron voto.',
              cuerpo, fuentes['fiscal'][4] + ' · listado oficial de comisiones'))

    # 9 · fiscal · fuerzas externas
    q.append(('09-fiscal-fuerzas', 'Presupuesto y ajuste fiscal', 'Quién empuja y quién frena fuera del Congreso', None,
              posturas(F['externos']), 'El País · Valora Analitik · Revista C-Level · El Espectador · El Tiempo · Senado (Pacto Histórico)'))

    # 10 · laboral · qué se vota
    ag = ''.join(
        f'<div style="padding:16px 0;border-top:1px solid #1c2233"><div style="font-size:23px;color:#f97316;font-weight:700">{e(a)}</div>'
        f'<div style="font-size:28px;line-height:1.28;margin-top:5px">{e(b)}</div>'
        f'{f"<div style=\"font-size:22px;color:#7d8396;margin-top:5px\">{e(c)}</div>" if c else ""}</div>'
        for a, b, c in L['agenda'])
    ant = ''.join(
        f'<div style="display:flex;justify-content:space-between;gap:20px;padding:12px 0;border-top:1px solid #1c2233;font-size:24px">'
        f'<span>{e(a)} · <span style="color:#7d8396">{e(b)}</span></span><b style="color:{CONTRA}">{e(c)}</b></div>' for a, b, c in L['antecedentes'])
    cuerpo = (f'<div class="card" style="padding:18px 26px 6px">{ag}</div>'
              f'<div class="card" style="padding:20px 26px 8px;margin-top:24px"><div style="font-size:26px;font-weight:700">No es el primer intento</div>'
              f'<div style="font-size:22px;color:#b9bdc9;margin:6px 0 10px">Proyectos anteriores con el mismo objetivo</div>{ant}</div>')
    q.append(('10-laboral-que-se-vota', 'Trabajo y cuidado', 'La Comisión Séptima vota el Sistema Nacional de Cuidado',
              None, cuerpo, fuentes['laboral'][0] + ' · Caudal'))

    # 11 · laboral · decretos del Gobierno
    filas = ''.join(
        f'<div style="display:flex;gap:22px;padding:15px 0;border-top:1px solid #1c2233">'
        f'<div style="width:300px"><div style="font-size:25px;font-weight:700">{e(a)}</div><div style="font-size:21px;color:#7d8396;margin-top:3px">{e(b)}</div></div>'
        f'<div style="flex:1;font-size:24px;line-height:1.3;color:#b9bdc9">{e(c)}</div></div>' for a, b, c in L['decretos'])
    q.append(('11-laboral-decretos', 'Trabajo y cuidado', 'Mientras tanto, el Gobierno revisa 8 decretos laborales',
              'El Ministerio del Trabajo los tiene en consulta hasta el 9 de noviembre. Dice que no cambia la Ley 2466 de 2025.',
              f'<div class="card" style="padding:8px 26px 4px">{filas}</div>', fuentes['laboral'][1]))

    # 12 · laboral · quién decide
    sep = ESC['septima_camara']['miembros']
    pb7 = {b: [c for c, _ in v] for b, v in clasifica_septima().items()}
    grupos = [(b, sorted(cs, key=[FAVOR, CONTRA, SIN, NUEVO].index), f'{len(cs)} {"miembro" if len(cs) == 1 else "miembros"}')
              for b, cs in sorted(pb7.items(), key=lambda kv: -len(kv[1]))]
    votaron = sum(cs.count(FAVOR) for cs in pb7.values())
    autores = AUTORES_CUIDADO
    cuerpo = (waffle(grupos, por_fila=6, lado=40, gap=8, etiqueta=330)
              + leyenda([(FAVOR, f'Votó sí a la reforma laboral en 2024 o 2025 ({votaron})'),
                        (SIN, f'Estaba en la Cámara, sin voto en esas sesiones ({sum(cs.count(SIN) for cs in pb7.values())})'),
                        (NUEVO, f'Llegó a la Cámara este año ({sum(cs.count(NUEVO) for cs in pb7.values())})')])
              + f'<div style="font-size:27px;font-weight:700;margin-top:40px">Quién firma el Sistema de Cuidado (37 congresistas)</div>'
              + '<div style="margin-top:18px">' + barras_h(autores, ancho=420, alto=34, color=FAVOR, fmt=lambda v: str(v), etiqueta=320, paso=48) + '</div>')
    q.append(('12-laboral-fuerzas-internas', 'Trabajo y cuidado', f'Solo {votaron} de los {len(sep)} miembros de la Séptima votaron la reforma laboral',
              f'{sum(cs.count(NUEVO) for cs in pb7.values())} de sus miembros llegaron este año. El proyecto de cuidado es, en la práctica, del Pacto Histórico.',
              cuerpo, fuentes['laboral'][4] + ' · orden del día de la Comisión Séptima'))

    # 13 · laboral · fuerzas externas
    q.append(('13-laboral-fuerzas', 'Trabajo y cuidado', 'Quién empuja y quién frena fuera del Congreso', None,
              posturas(L['externos']), 'Portafolio · El Universal · La Opinión · Blu Radio'))
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
