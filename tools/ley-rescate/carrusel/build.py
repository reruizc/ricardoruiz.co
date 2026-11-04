#!/usr/bin/env python3
"""Carrusel de Instagram de la Ley de Rescate: 13 cuadros cuadrados (1080×1080) con los datos del día.

  python3 tools/ley-rescate/carrusel/build.py            # los 13
  python3 tools/ley-rescate/carrusel/build.py 04 07       # solo esos

Lee ley-rescate-data/estado.json (el mismo que pinta la página), así que se puede rehacer cualquier día. Mismo
sistema visual de las páginas: Caudal × Cauce, papel claro con curvas de nivel, azul #3d6eb8, Helvetica del repo.
Cada cuadro es un HTML que Chrome sin ventana captura a PNG. Sale a rrss/instagram/carrusel-ley-rescate/.
Instagram recorta a cuadrado en la cuadrícula del perfil: por eso 1:1 y no 4:5.
"""
import json
import math
import subprocess
import sys
from datetime import date, timedelta
from html import escape
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / 'rrss/instagram/carrusel-ley-rescate'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
E = json.loads((REPO / 'ley-rescate-data/estado.json').read_text())
HOY = date.fromisoformat(E['hoy'])
CIERRE = date(2026, 12, 16)
ULT_NORMAL, ULT_URG = CIERRE - timedelta(days=8 + 15 + 8 + 1), CIERRE - timedelta(days=8 + 1)
TOTAL = 13
MES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
DIA = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
U = REPO.as_uri()
fl = lambda d: f'{DIA[d.weekday()]} {d.day} de {MES[d.month - 1]}'
fc = lambda d: f'{d.day} de {MES[d.month - 1]}'
num = lambda n: f'{n:,}'.replace(',', '.')
dec = lambda x, k=1: f'{x:.{k}f}'.replace('.', ',')
esc = lambda s: escape(str(s), quote=True)
AZUL, ROJO, AMBAR, VERDE, GRIS = '#3d6eb8', '#c8553d', '#d9a441', '#1c8046', '#b9c0cb'

CSS = f"""
@font-face{{font-family:H;src:url("{U}/fonts/helveticaneue-light.woff2");font-weight:300}}
@font-face{{font-family:H;src:url("{U}/fonts/helveticaneue.woff2");font-weight:400}}
@font-face{{font-family:H;src:url("{U}/fonts/helveticaneue-medium.woff2");font-weight:500}}
@font-face{{font-family:H;src:url("{U}/fonts/helveticaneue-bold.woff2");font-weight:700}}
@font-face{{font-family:Syne;src:url("{U}/tools/build-cotizacion-campana/fonts/Syne-ExtraBold.ttf");font-weight:800}}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1080px;height:1080px;overflow:hidden}}
body{{font-family:H,sans-serif;color:#14161c;background:#f0f0f0 url("{U}/caudalxcauce/img/topo-claro.webp") center/cover;position:relative}}
.c{{position:absolute;inset:0;padding:54px 64px 0;display:flex;flex-direction:column}}
.top{{display:flex;justify-content:space-between;align-items:center}}
.top img{{height:46px}}
.pag{{font-size:20px;font-weight:500;color:#667085;letter-spacing:.06em}}
.k{{font-size:20px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:{AZUL};margin-top:40px}}
h1{{font-size:88px;line-height:1.0;letter-spacing:-.035em;font-weight:700;margin-top:18px}}
h2{{font-size:56px;line-height:1.04;letter-spacing:-.03em;font-weight:700;margin-top:14px}}
.sub{{font-size:27px;line-height:1.35;color:#4d5462;font-weight:300;margin-top:16px;max-width:930px}}
.sub b{{color:#14161c;font-weight:500}}
.panel{{background:#fff;border:1px solid rgba(17,20,28,.1);border-radius:24px;padding:30px 34px;box-shadow:0 10px 40px rgba(17,20,28,.06)}}
.nota{{font-size:18px;line-height:1.4;color:#667085}}
.pie{{position:absolute;left:64px;right:64px;bottom:40px;display:flex;justify-content:space-between;align-items:center;font-size:19px;color:#667085}}
.pie b{{color:{AZUL};font-weight:700}}
.marca{{display:flex;align-items:center;gap:9px;color:#14161c}}.marca>span{{font-family:Syne,sans-serif;font-weight:800;font-size:22px;letter-spacing:-.03em}}
.marca i{{display:flex;align-items:flex-end;gap:3px;height:20px}}.marca i span{{width:5px;background:{AZUL};border-radius:2px}}
.marca em{{font-style:normal;color:{AZUL}}}
"""
MARCA = ('<span class="marca"><i><span style="height:20px"></span><span style="height:15px"></span><span style="height:10px"></span>'
         '<span style="height:5px"></span></i><span>Ricardo<em>.</em>Ruiz</span></span>')


def pagina(n, cuerpo, estilo=''):
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>{CSS}{estilo}</style></head><body><div class="c">
<div class="top"><img src="{U}/caudalxcauce.png" alt=""><span class="pag">{n}/{TOTAL}</span></div>{cuerpo}</div>
<div class="pie"><span>Seguimiento diario en <b>ricardoruiz.co</b> · corte del {fl(HOY)}</span>{MARCA}</div></body></html>"""


def suma(t):
    o = {'n': 0, 'apoya': 0, 'rechaza': 0, 'mixta': 0}
    for v in (t.get('por') or {}).values():
        for k in o:
            o[k] += v.get(k, 0)
    o['post'] = o['apoya'] + o['rechaza'] + o['mixta']
    return o


# ── Rampa del velocímetro: 0 todo apoya (azul frío) → 100 todo rechaza (rojo caliente), la misma de la página ──
RAMPA = [(0, (61, 110, 184)), (25, (154, 184, 222)), (50, (240, 194, 75)), (75, (240, 122, 46)), (100, (209, 38, 43))]


def color(v):
    k = 0
    while k < len(RAMPA) - 2 and v > RAMPA[k + 1][0]:
        k += 1
    (v0, a), (v1, b) = RAMPA[k], RAMPA[k + 1]
    t = min(1, max(0, (v - v0) / (v1 - v0)))
    return 'rgb(%d,%d,%d)' % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def idx(o):
    p = o.get('a', 0) + o.get('r', 0) + o.get('m', 0)
    return (round(100 * (o.get('r', 0) + o.get('m', 0) / 2) / p) if p else None), p


def tramo(v):
    return 'Mayoría apoya' if v < 20 else 'Más apoyo que rechazo' if v < 40 else 'Dividido' if v <= 60 else 'Más rechazo que apoyo' if v <= 80 else 'Mayoría rechaza'


def velo(v, gid):
    cx, cy, R, r = 110, 112, 100, 66
    pt = lambda q, rad: (cx + rad * math.cos(math.pi * (1 - q / 100)), cy - rad * math.sin(math.pi * (1 - q / 100)))
    defs, paths = [], []
    for n, q0 in enumerate([0, 20, 40, 60, 80]):
        q1 = q0 + 20; g0 = q0 + (0.9 if n else 0); g1 = q1 - (0.9 if n < 4 else 0)
        (x1, y1), (x2, y2), (x3, y3), (x4, y4) = pt(g0, R), pt(g1, R), pt(g1, r), pt(g0, r)
        (ax, ay), (bx, by) = pt(q0, R), pt(q1, R)
        defs.append(f'<linearGradient id="{gid}{n}" gradientUnits="userSpaceOnUse" x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}"><stop offset="0" stop-color="{color(q0)}"/><stop offset="1" stop-color="{color(q1)}"/></linearGradient>')
        paths.append(f'<path d="M{x1:.1f} {y1:.1f}A{R} {R} 0 0 1 {x2:.1f} {y2:.1f}L{x3:.1f} {y3:.1f}A{r} {r} 0 0 0 {x4:.1f} {y4:.1f}Z" fill="url(#{gid}{n})"/>')
    a = math.pi * (1 - v / 100); nx, ny = pt(v, 86); hx, hy = nx - 11 * math.cos(a), ny + 11 * math.sin(a); px, py = 5 * math.sin(a), 5 * math.cos(a)
    return (f'<svg viewBox="0 0 220 134"><defs>{"".join(defs)}</defs>{"".join(paths)}'
            f'<line x1="{cx}" y1="{cy}" x2="{hx:.1f}" y2="{hy:.1f}" stroke="#1f2430" stroke-width="3.2" stroke-linecap="round"/>'
            f'<path d="M{nx:.1f} {ny:.1f}L{hx + px:.1f} {hy + py:.1f}L{hx - px:.1f} {hy - py:.1f}Z" fill="#1f2430"/>'
            f'<circle cx="{cx}" cy="{cy}" r="8" fill="#fff" stroke="#1f2430" stroke-width="3"/>'
            f'<text x="27" y="130" text-anchor="middle" font-size="10" fill="#667085" font-family="H">0</text><text x="193" y="130" text-anchor="middle" font-size="10" fill="#667085" font-family="H">100</text></svg>')


# ── 01 · Portada ─────────────────────────────────────────────────────────────────────────────────────────────
def c01():
    falta = (CIERRE - HOY).days
    return pagina(1, f"""
<div class="k" style="margin-top:56px">Ley de Rescate · PL 477 de 2026 Cámara</div>
<h1 style="font-size:112px">¿En qué va la Ley de Rescate?</h1>
<p class="sub" style="font-size:34px;margin-top:30px">La reforma del Gobierno para recortar el Estado y recaudar más. Lo que dice, quién la pone, quién la apoya y cuánto tiempo le queda, a {fl(HOY)}.</p>
<div class="kp">
  <div><b>106</b><span>artículos</span></div><div><b>4</b><span>debates por delante</span></div><div><b>{falta}</b><span>días para el 16 de diciembre</span></div>
</div>
<p class="desl">Desliza →</p>""", f"""
.kp{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:56px}}
.kp div{{background:#fff;border:1px solid rgba(17,20,28,.1);border-radius:22px;padding:30px 30px}}
.kp b{{display:block;font-size:92px;letter-spacing:-.04em;line-height:1}}.kp span{{display:block;font-size:22px;color:#4d5462;margin-top:8px}}
.desl{{font-size:28px;font-weight:700;color:{AZUL};margin-top:44px}}""")


# ── 02 · Dónde va ────────────────────────────────────────────────────────────────────────────────────────────
def c02():
    U = E['proyecto'].get('urgencia')
    T = E.get('tramite') or {}
    ponentes = sum(len(d.get('ponentes') or []) for d in T.get('debates') or [])
    etapas = [('Radicado', '29 de octubre', 'hecho'), ('Primer debate', 'Comisiones Terceras', 'ahora'), ('Segundo debate', 'Plenaria de Cámara', ''),
              ('Tercero y cuarto', 'Senado', ''), ('Sanción', 'Presidente', '')]
    ruta = ''.join(f'<div class="et {c}"><i></i><b>{t}</b><span>{s}</span></div>' for t, s, c in etapas)
    pon = f'{ponentes} ponentes' if ponentes else 'Sin ponentes publicados'
    return pagina(2, f"""
<div class="k">El camino</div>
<h2>Va en la primera estación de cinco</h2>
<p class="sub" style="font-size:30px">Una ley necesita cuatro debates: dos en la Cámara y dos en el Senado. Esta todavía no ha tenido el primero.</p>
<div class="panel" style="margin-top:40px;padding:40px 36px"><div class="ruta">{ruta}</div></div>
<div class="hoy"><div><b>{esc(T.get('estado') or 'Trámite en comisión')}</b><span>Estado en la ficha oficial de la Cámara</span></div>
<div class="al"><b>{pon}</b><span>en la ficha oficial</span></div>{'<div class="ok"><b>Con urgencia</b><span>mensaje radicado el ' + fc(date.fromisoformat(U['fecha'])) + ': comisiones de Cámara y Senado juntas</span></div>' if U else '<div class="al"><b>Sin fecha</b><span>de primer debate en los órdenes del día</span></div>'}</div>""", f"""
.ruta{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;position:relative}}
.ruta:before{{content:"";position:absolute;left:30px;right:30px;top:27px;height:4px;background:#d7dbe2;border-radius:2px}}
.et{{position:relative;display:flex;flex-direction:column;gap:5px}}
.et i{{width:58px;height:58px;border-radius:50%;background:#fff;border:4px solid #d7dbe2;margin-bottom:10px}}
.et.hecho i{{background:{VERDE};border-color:{VERDE}}}.et.ahora i{{background:{AZUL};border-color:{AZUL};box-shadow:0 0 0 9px rgba(61,110,184,.18)}}
.et b{{font-size:27px;line-height:1.15}}.et span{{font-size:20px;color:#667085;line-height:1.25}}.et.ahora b{{color:{AZUL}}}
.hoy{{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:14px;margin-top:26px}}
.hoy div{{background:#fff;border:1px solid rgba(17,20,28,.1);border-radius:20px;padding:28px 26px;min-height:190px}}
.hoy b{{display:block;font-size:36px;letter-spacing:-.02em;line-height:1.1}}.hoy span{{display:block;font-size:21px;color:#4d5462;margin-top:10px;line-height:1.3}}
.hoy .al b{{color:{ROJO}}}.hoy .ok b{{color:{VERDE}}}""")


# ── 03 · El tiempo que le queda ──────────────────────────────────────────────────────────────────────────────
def c03():
    U = E['proyecto'].get('urgencia')
    falta = (CIERRE - HOY).days
    ini, fin = HOY, CIERRE
    rad = date(2026, 10, 29)
    aprob = [t for t in E['tributarias'] if t['res'] == 'aprobada']
    rapida = min(aprob, key=lambda t: (date.fromisoformat(t['fin']) - date.fromisoformat(t['rad'])).days)
    d_rap = (date.fromisoformat(rapida['fin']) - date.fromisoformat(rapida['rad'])).days
    span = (fin - ini).days
    x = lambda d: 100 * (d - ini).days / span
    fila = lambda t, d, txt: f"""<div class="fila"><div class="ft"><b>{t}</b><span>{txt}</span></div><div class="barra"><i style="width:{x(d):.1f}%"></i><em style="left:{x(d):.1f}%"><s></s>{d.day} {MES[d.month - 1][:3]}</em></div></div>"""
    return pagina(3, f"""
<div class="k">El tiempo que le queda</div>
<h2>{falta} días para el 16 de diciembre</h2>
<p class="sub">{'El Gobierno radicó mensaje de urgencia el ' + fc(date.fromisoformat(U['fecha'])) + ': las comisiones de Cámara y Senado votan juntas y la Constitución les pide decidir en 30 días.' if U else 'Ese día termina este periodo de sesiones. Entre debate y debate la Constitución exige plazos mínimos: 8 días, y 15 entre una cámara y otra.'}</p>
<div class="panel" style="margin-top:30px">
  <p class="esc"><span>Hoy · {HOY.day} nov</span><span>16 dic</span></p>
  {fila('Con mensaje de urgencia (ya radicado)', ULT_URG, f'el primer debate conjunto puede ser hasta el {fl(ULT_URG)}') if U else fila('Trámite normal', ULT_NORMAL, f'el primer debate tendría que ser a más tardar el {fl(ULT_NORMAL)}')}
  {fila('Así habría sido sin urgencia', ULT_NORMAL, f'el primer debate tendría que ser a más tardar el {fl(ULT_NORMAL)}') if U else fila('Con mensaje de urgencia', ULT_URG, f'las comisiones de Cámara y Senado votan juntas: aguanta hasta el {fl(ULT_URG)}')}
</div>
<div class="rap"><b>{(CIERRE - rad).days}</b><span>días van del 29 de octubre, cuando se radicó, al 16 de diciembre. La tributaria aprobada más rápida desde 2016 tardó <b>{d_rap} días</b> ({esc(rapida['ley'])}, {esc(rapida['gobierno'])}). Si esta pasa a tiempo, sería un récord.</span></div>
<p class="sub" style="font-size:22px;margin-top:18px"><b>Si no alcanza, no se archiva:</b> sigue en febrero. Pero lo que cobra por año, como la renta, arrancaría en 2028 y no en 2027.</p>""", f"""
.esc{{display:flex;justify-content:space-between;font-size:18px;color:#667085;margin-bottom:6px}}
.rap{{display:grid;grid-template-columns:auto 1fr;gap:22px;align-items:center;margin-top:18px;background:#fff;border:1px solid rgba(17,20,28,.1);border-radius:20px;padding:20px 26px}}
.rap>b{{font-size:72px;letter-spacing:-.04em;color:{AZUL}}}.rap span{{font-size:21px;line-height:1.35;color:#2b303b}}
.fila{{margin-top:22px}}.ft b{{font-size:26px}}.ft span{{display:block;font-size:19px;color:#4d5462;margin-top:4px}}
.barra{{position:relative;height:30px;background:#eef0f3;border-radius:15px;margin-top:14px}}
.barra i{{position:absolute;left:0;top:0;bottom:0;background:linear-gradient(90deg,rgba(61,110,184,.25),rgba(61,110,184,.55));border-radius:15px}}
.barra em{{position:absolute;top:-2px;transform:translateX(-50%);font-style:normal;font-size:18px;font-weight:700;color:#fff;background:{ROJO};border-radius:8px;padding:5px 9px;white-space:nowrap}}
.barra:after{{content:"";position:absolute;right:0;top:-6px;bottom:-6px;width:4px;background:#14161c;border-radius:2px}}""")


# ── 04 · Termómetro (velocímetro) ────────────────────────────────────────────────────────────────────────────
def c04():
    T = E['termometro']
    (vt, pt_), (vp, pp), (vr, pr) = idx(T['todo']), idx(T['prensa']), idx(T['redes'])
    chico = lambda v, p, t, g: f'<div class="vg"><div class="svgc">{velo(v, g)}</div><span>{t}</span><b>{v}</b><em><i style="background:{color(v)}"></i>{tramo(v)}</em><small>{num(p)} textos con postura</small></div>'
    return pagina(4, f"""
<div class="k">Termómetro de medios y redes</div>
<h2>¿Qué tan caliente está la discusión?</h2>
<div class="cuerpo">
  <div class="velo-g"><div class="svgc">{velo(vt, 'g')}</div><b>{vt}</b><em><i style="background:{color(vt)}"></i>{tramo(vt)}</em><span>{num(pt_)} textos que toman postura</span></div>
  <div class="lado">{chico(vp, pp, 'Prensa', 'p')}{chico(vr, pr, 'Redes', 'r')}</div>
</div>
<p class="nota" style="margin-top:34px;font-size:21px">0 es todo apoyo; 100, todo rechazo. Los reparos cuentan como medio rechazo. Mide lo que se publica, no lo que piensa el país.</p>""", f"""
.cuerpo{{display:grid;grid-template-columns:1.25fr 1fr;gap:24px;align-items:center;margin-top:44px}}
.velo-g{{display:flex;flex-direction:column;align-items:center}}
.velo-g .svgc{{width:100%}}.velo-g svg,.vg svg{{width:100%;height:auto;display:block}}
.velo-g b{{font-size:150px;font-weight:700;letter-spacing:-.05em;line-height:.9}}
.velo-g em,.vg em{{display:inline-flex;align-items:center;gap:10px;font-style:normal;font-weight:700;font-size:28px;margin-top:8px}}
.velo-g em i,.vg em i{{width:20px;height:20px;border-radius:50%}}
.velo-g span{{font-size:20px;color:#667085;margin-top:6px}}
.lado{{display:flex;flex-direction:column;gap:20px}}
.vg{{display:grid;grid-template-columns:170px 1fr;column-gap:14px;align-items:center;background:#fff;border:1px solid rgba(17,20,28,.1);border-radius:20px;padding:26px 22px}}
.vg .svgc{{width:170px;grid-row:1/5}}.vg b{{font-size:64px;letter-spacing:-.04em;line-height:1}}.vg em{{font-size:18px;gap:7px;margin-top:2px}}.vg em i{{width:12px;height:12px}}
.vg span{{font-size:22px;font-weight:700;margin-top:2px}}.vg small{{font-size:16px;color:#667085;margin-top:2px}}""")


# ── 05 · Cómo entran y cómo salen ────────────────────────────────────────────────────────────────────────────
def c05():
    H = E['historico']
    trib = E['tributarias']
    leyes = sum(1 for r in H['reformas'] if r.get('paso'))
    # temas de la Ley de Rescate con su historia (se cuentan en la sección «Entran y salen»)
    cuenta = {}
    for ref in H['reformas']:
        for it in ref['temas']:
            c = cuenta.setdefault(it['t'], [0, 0]); c[0] += 1; c[1] += it['r'] in ('aprobado', 'recortado')
    tot = sum(c[0] for c in cuenta.values()) or 84
    vivos = sum(c[1] for c in cuenta.values())
    pct = round(100 * vivos / tot) if cuenta else 49
    destac = [(k, H['temas'][k]['n']) for k in ('iva_base', 'renta_personas', 'patrimonio', 'renta_empresas_baja', 'ambientales', 'iva_devolucion') if k in H['temas']]
    filas = ''
    for k, nom in destac:
        prop, qued = cuenta.get(k, [0, 0])
        if not prop:
            continue
        filas += f'<div class="tr"><span>{nom}</span><div class="pts">{"".join(f"<i class={chr(34)}{"s" if j < qued else ""}{chr(34)}></i>" for j in range(prop))}</div><b>{qued} de {prop}</b></div>'
    return pagina(5, f"""
<div class="k">Cómo entran y cómo salen</div>
<h2>Las tributarias cambian mucho en el Congreso</h2>
<p class="sub">Desde 2016 se han radicado {len(trib)} reformas tributarias y {leyes} fueron ley. De todo lo que propusieron, el <b>{pct}%</b> quedó en una ley.</p>
<div class="panel" style="margin-top:26px">
  <p class="nota" style="margin-bottom:12px;font-size:20px">Temas que también trae la Ley de Rescate: cuántas veces se propusieron antes y cuántas quedaron</p>
  {filas}
</div>
<p class="nota" style="margin-top:18px;font-size:20px">Cada punto es una vez que un gobierno lo propuso; en azul, las veces que quedó en la ley. La historia no predice el voto.</p>""", f"""
.tr{{display:grid;grid-template-columns:360px 1fr 100px;align-items:center;gap:14px;padding:13px 0;border-top:1px solid rgba(17,20,28,.08)}}
.tr span{{font-size:27px;font-weight:500}}.tr b{{font-size:26px;text-align:right}}
.pts{{display:flex;gap:8px}}.pts i{{width:34px;height:34px;border-radius:50%;background:#e1e4e9;border:2px solid #cfd4dc}}.pts i.s{{background:{AZUL};border-color:{AZUL}}}""")


# ── 06 · Qué es un decil ─────────────────────────────────────────────────────────────────────────────────────
def c06():
    D = E['analisis']['propia']['deciles_gasto']['d']
    m = lambda v: f'${dec(v / 1e6, 2)} M' if v >= 1e6 else f'${round(v / 1e3)} mil'
    caja = ''
    for n, lo, hi, *_ in D:
        rango = f'hasta {m(hi)}' if n == 1 else f'más de {m(lo)}' if n == 10 else f'{m(lo)} a {m(hi)}'
        caja += f'<div class="d" style="--h:{30 + 7 * n}%"><b>{n}</b><span>{rango}</span></div>'
    return pagina(6, f"""
<div class="k">Antes de las cuentas</div>
<h2>¿Qué es un decil?</h2>
<p class="sub">Pon a todas las personas del país en fila, de la que menos gasta a la que más gasta al mes, y parte la fila en <b>diez grupos del mismo tamaño</b>. Cada grupo es un decil.</p>
<div class="panel deciles" style="margin-top:26px">{caja}</div>
<p class="sub" style="font-size:23px;margin-top:22px">El <b>decil 1</b> es el 10% que menos gasta; el <b>decil 10</b>, el 10% que más gasta. Se cuenta el gasto del hogar dividido entre quienes viven en él: una familia de cinco con $2 millones no vive igual que una persona sola con $2 millones.</p>""", f"""
.deciles{{display:grid;grid-template-columns:repeat(10,1fr);gap:8px;align-items:end;height:400px;padding:24px 22px 20px}}
.d{{height:var(--h);background:linear-gradient(180deg,rgba(61,110,184,.85),rgba(61,110,184,.55));border-radius:10px 10px 4px 4px;display:flex;flex-direction:column;justify-content:space-between;align-items:center;padding:10px 4px;color:#fff;position:relative}}
.d b{{font-size:34px}}.d span{{font-size:15px;line-height:1.15;text-align:center;font-weight:500}}""")


# ── 07 · Quién gana y quién pierde ───────────────────────────────────────────────────────────────────────────
def c07():
    P = E['analisis']['propia']
    neto, plena = P['neto'], P['neto_plena']
    lo, hi = -3.6, 1.6
    y = lambda v: 100 * (hi - v) / (hi - lo)
    cero = y(0)
    barras = ''
    for i, (a, b) in enumerate(zip(neto, plena)):
        top_a, h_a = (y(a), y(0)) if a < 0 else (y(a), y(0))
        barras += (f'<div class="col"><div class="zona">'
                   f'<i class="b1" style="top:{min(y(a), cero):.1f}%;height:{abs(y(a) - cero):.1f}%"></i>'
                   f'<i class="b2" style="top:{min(y(b), cero):.1f}%;height:{abs(y(b) - cero):.1f}%"></i>'
                   f'<em class="v1" style="top:{(y(a) + 1.5) if a < 0 else (y(a) - 7):.1f}%">{dec(a)}</em></div><b>{i + 1}</b></div>')
    return pagina(7, f"""
<div class="k">Quién la pone · cálculo propio</div>
<h2>Pierden todos los deciles, más los de arriba</h2>
<p class="sub" style="font-size:24px">Efecto de toda la ley en cada decil, en % de lo que gasta el hogar. Con la devolución que dice el artículo 39, solo del IVA comprado con factura.</p>
<div class="panel graf" style="margin-top:20px">
  <div class="cols" style="--cero:{cero:.1f}%">{barras}</div>
  <div class="ley"><span><i style="background:{ROJO}"></i>Devolución solo con factura (art. 39)</span><span><i style="background:rgba(61,110,184,.45)"></i>Si se devolviera todo el IVA</span></div>
</div>
<p class="nota" style="margin-top:16px;font-size:19px">Decil 1: el 10% que menos gasta. Si se devolviera todo el IVA, como supone el Gobierno, los deciles 1 a 3 saldrían ganando. Cálculo propio con la encuesta de gastos de los hogares del DANE (87.201 hogares).</p>""", f"""
.graf{{padding:22px 28px 16px}}
.cols{{display:grid;grid-template-columns:repeat(10,1fr);gap:10px;height:450px;position:relative}}
.cols:before{{content:"";position:absolute;left:0;right:0;top:var(--cero);height:2px;background:#14161c;opacity:.6}}
.col{{display:flex;flex-direction:column}}.col .zona{{position:relative;flex:1}}.col>b{{text-align:center;font-size:20px;margin-top:6px}}
.zona i{{position:absolute;border-radius:4px}}.b1{{left:6%;width:52%;background:{ROJO}}}.b2{{left:44%;width:50%;background:rgba(61,110,184,.45)}}
.v1{{position:absolute;left:-4px;right:0;text-align:left;font-style:normal;font-size:19px;font-weight:700;color:{ROJO}}}
.ley{{display:flex;gap:26px;font-size:18px;color:#4d5462;margin-top:12px}}.ley i{{display:inline-block;width:16px;height:16px;border-radius:4px;margin-right:8px;vertical-align:-2px}}""")


# ── 08 · Los votos que necesita ──────────────────────────────────────────────────────────────────────────────
def c08():
    V = E['votos']
    cuenta = {'senado': {'a': 0, 'r': 0}, 'camara': {'a': 0, 'r': 0}}
    for b in V['bloques']:
        for cam in ('senado', 'camara'):
            if b['post'] == 'si':
                cuenta[cam]['a'] += b[cam]
            elif b['post'] == 'no':
                cuenta[cam]['r'] += b[cam]

    def hemi(cam):
        c = V['camaras'][cam]; tot, may = c['total'], c['mayoria']
        a, r = cuenta[cam]['a'], cuenta[cam]['r']; s = tot - a - r
        pts = ''.join(f'<i class="{x}"></i>' for x in ['a'] * a + ['s'] * s + ['r'] * r)
        return f"""<div class="cam"><h3>{c['nombre']}</h3><p class="big"><b>{a}</b> de <b>{may}</b> votos necesarios</p>
<div class="pts" style="grid-template-columns:repeat({16 if tot > 20 else 13},1fr)">{pts}</div>
<p class="cnt"><span class="ca">{a} apoyan</span> · <span class="cr">{r} rechazan</span> · {s} sin definir</p></div>"""
    pc = {'si': (VERDE, 'Apoya'), 'no': (ROJO, 'Rechaza')}
    banc = ''.join(f'<span style="--c:{pc.get(b["post"], ("#8b93a1", ""))[0]}"><i></i>{esc(b["nombre"])} <small>{b["senado"]} · {b["camara"]}</small></span>'
                   for b in sorted(V['bloques'], key=lambda b: ({'si': 0, 'no': 2}.get(b['post'], 1), -(b['senado'] + b['camara']))))
    return pagina(8, f"""
<div class="k">Los votos</div>
<h2>Primero tiene que pasar las Comisiones Terceras</h2>
<p class="sub" style="font-size:24px">Así está cada comisión si se cuenta solo a quien ya habló como bancada. Nadie ha votado todavía.</p>
<div class="dos">{hemi('senado')}{hemi('camara')}</div>
<div class="banc">{banc}</div>
<p class="nota" style="margin-top:14px">Número de integrantes en la Tercera de Senado · Cámara. Haz tu propia cuenta en la página.</p>""", f"""
.dos{{display:grid;grid-template-columns:1fr 1.45fr;gap:16px;margin-top:26px}}
.cam{{background:#fff;border:1px solid rgba(17,20,28,.1);border-radius:22px;padding:22px 24px}}
.cam h3{{font-size:22px;line-height:1.2}}.big{{font-size:22px;color:#4d5462;margin-top:10px}}.big b{{font-size:44px;color:#14161c;letter-spacing:-.03em}}
.pts{{display:grid;gap:7px;margin-top:16px}}.pts i{{aspect-ratio:1;border-radius:50%;background:#d7dbe2}}.pts i.a{{background:{VERDE}}}.pts i.r{{background:{ROJO}}}
.cnt{{font-size:18px;color:#4d5462;margin-top:14px}}
.banc{{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}}.banc span{{display:inline-flex;align-items:center;gap:8px;background:#fff;border:1px solid rgba(17,20,28,.1);border-radius:999px;padding:8px 14px;font-size:18px;font-weight:500}}
.banc i{{width:12px;height:12px;border-radius:50%;background:var(--c)}}.banc small{{color:#667085;font-size:16px}}.ca{{color:{VERDE};font-weight:700}}.cr{{color:{ROJO};font-weight:700}}""")


# ── 09 · Esquema de fuerzas ──────────────────────────────────────────────────────────────────────────────────
def c09():
    V = E['voces']
    grupos = [('a', 'Empujan', VERDE), ('m', 'Con reparos', AMBAR), ('i', 'Sin definir', '#8b93a1'), ('r', 'En contra', ROJO)]
    cols = ''
    for k, t, col in grupos:
        g = sorted([v for v in V if v['p'] == k], key=lambda v: (-(v.get('n') or 0), -(v.get('men') or 0)))
        nombres = ''.join(f'<li>{esc(v["q"])}<small>{esc(v["c"])}</small></li>' for v in g[:6])
        cols += f'<div class="fc" style="--c:{col}"><h3><b>{len(g)}</b>{t}</h3><ul>{nombres}</ul>{f"<p>y {len(g) - 6} más</p>" if len(g) > 6 else ""}</div>'
    return pagina(9, f"""
<div class="k">Esquema de fuerzas</div>
<h2>{len(V)} voces que mueven la discusión</h2>
<p class="sub" style="font-size:24px">Congresistas, Gobierno, gremios, sindicatos y expertos, según lo que han dicho en público. Una declaración no es un voto.</p>
<div class="fuerzas">{cols}</div>""", f"""
.fuerzas{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:24px}}
.fc{{background:#fff;border:1px solid rgba(17,20,28,.1);border-top:8px solid var(--c);border-radius:18px;padding:18px 18px 14px}}
.fc h3{{font-size:22px;display:flex;align-items:baseline;gap:10px}}.fc h3 b{{font-size:48px;color:var(--c);letter-spacing:-.03em}}
.fc ul{{list-style:none;margin-top:10px}}.fc li{{font-size:18px;font-weight:500;padding:6px 0;border-top:1px solid rgba(17,20,28,.07);line-height:1.2}}
.fc li small{{display:block;font-size:14px;color:#667085;font-weight:400;margin-top:2px}}.fc p{{font-size:15px;color:#667085;margin-top:6px}}""")


# ── 10 · Lo que más se discute ───────────────────────────────────────────────────────────────────────────────
def c10():
    ts = [t for t in E['temas'] if t['id'] != 'general']
    ts = sorted(ts, key=lambda t: -suma(t)['n'])[:8]
    mx = max(suma(t)['n'] for t in ts)
    filas = ''
    for t in ts:
        o = suma(t)
        if o['post'] >= 6:
            rp = round(100 * (o['rechaza'] + o['mixta'] / 2) / o['post'])
            lab = f'{round(100 * o["rechaza"] / o["post"])}% rechaza'
        else:
            rp, lab = None, 'casi todo informa'
        filas += (f'<div class="tm"><span>{esc(t["nombre"])}</span><div class="bar"><i style="width:{100 * o["n"] / mx:.1f}%;background:{color(rp) if rp is not None else GRIS}"></i></div>'
                  f'<b>{num(o["n"])}</b><em>{lab}</em></div>')
    return pagina(10, f"""
<div class="k">La discusión</div>
<h2>Lo que más se discute: la renta y el IVA a la comida</h2>
<p class="sub" style="font-size:24px">Textos de prensa y redes sobre cada tema. El color dice cómo se recibe, con la misma escala del termómetro.</p>
<div class="panel" style="margin-top:22px;padding:20px 28px">{filas}</div>""", f"""
.tm{{display:grid;grid-template-columns:350px 1fr 74px 180px;align-items:center;gap:12px;padding:15px 0;border-top:1px solid rgba(17,20,28,.07)}}
.tm:first-child{{border-top:0}}.tm span{{font-size:23px;font-weight:500;line-height:1.15}}
.bar{{height:28px;background:#f1f2f5;border-radius:6px;overflow:hidden}}.bar i{{display:block;height:100%;border-radius:6px}}
.tm b{{font-size:23px;text-align:right}}.tm em{{font-style:normal;font-size:19px;color:#4d5462}}""")


# ── 11 · Los 106 artículos ───────────────────────────────────────────────────────────────────────────────────
def c11():
    tema = {t['id']: t for t in E['temas']}
    mx = max(suma(t)['n'] for t in E['temas'] if t['id'] != 'general') or 1
    celdas = ''
    for a in E['articulos']:
        t = next((tema[i] for i in a['temas'] if i in tema), None)
        o = suma(t) if t else None
        if o and o['post'] >= 6:
            rp = 100 * (o['rechaza'] + o['mixta'] / 2) / o['post']
            fondo, op = color(rp), .5 + .5 * min(1, math.sqrt(o['n'] / mx))
        else:
            fondo, op = '#dfe2e7', 1
        celdas += f'<i style="background:{fondo};opacity:{op:.2f}">{a["n"]}</i>'
    return pagina(11, f"""
<div class="k">El proyecto, artículo por artículo</div>
<h2>106 artículos: dónde está el rechazo</h2>
<p class="sub" style="font-size:23px">Cada cuadro es un artículo, pintado según cómo se recibe su tema. En la página puedes leer cada uno y bajarlo en Word.</p>
<div class="panel mosaico" style="margin-top:20px">{celdas}</div>
<div class="esc"><span><i style="background:{color(0)}"></i>Más apoyo</span><span><i style="background:{color(50)}"></i>Dividido</span><span><i style="background:{color(100)}"></i>Más rechazo</span><span><i style="background:#dfe2e7"></i>Sin postura suficiente</span></div>""", f"""
.mosaico{{display:grid;grid-template-columns:repeat(14,1fr);gap:6px;padding:22px}}
.mosaico i{{aspect-ratio:1;border-radius:6px;display:flex;align-items:center;justify-content:center;font-style:normal;font-size:16px;font-weight:700;color:rgba(20,22,28,.75)}}
.esc{{display:flex;gap:24px;font-size:18px;color:#4d5462;margin-top:14px}}.esc i{{display:inline-block;width:16px;height:16px;border-radius:4px;margin-right:8px;vertical-align:-2px}}""")


# ── 12 · Las voces ───────────────────────────────────────────────────────────────────────────────────────────
ELEGIDAS = ['José Manuel Restrepo', 'Álvaro Uribe', 'María Clara Posada', 'Andrés Forero']


def c12():
    V, P = E['voces'], E['personas']
    pref = [v for nom in ELEGIDAS for v in V if v['q'] == nom]
    otros = [v for v in V if v not in pref and v.get('s') and (P.get(v['s']) or {}).get('foto') and not (P.get(v['s']) or {}).get('logo')]
    # una de cada postura que falte, con foto
    for k in ('r', 'a', 'm'):
        if sum(1 for v in pref if v['p'] == k) < 2:
            pref += [v for v in sorted(otros, key=lambda v: -(v.get('men') or 0)) if v['p'] == k and v not in pref][:1]
    pref = pref[:6]
    col = {'a': VERDE, 'm': AMBAR, 'r': ROJO, 'i': '#8b93a1'}
    lab = {'a': 'Empuja', 'm': 'Con reparos', 'r': 'En contra', 'i': 'Sin definir'}
    tarj = ''
    for v in pref:
        f = (P.get(v.get('s')) or {}).get('foto')
        img = f'<img src="{U}/{f}" alt="">' if f else f'<span class="ini">{esc("".join(w[0] for w in v["q"].split()[:2]))}</span>'
        tarj += (f'<div class="vz" style="--c:{col[v["p"]]}">{img}<div><b>{esc(v["q"])}</b><small>{esc(v["c"])} · {esc(v["b"])}</small>'
                 f'<em>{lab[v["p"]]}</em><p>{esc(v["x"])}</p></div></div>')
    return pagina(12, f"""
<div class="k">Las voces</div>
<h2>Lo que dicen los que deciden</h2>
<div class="voces">{tarj}</div>""", f"""
.voces{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:22px}}
.vz{{display:grid;grid-template-columns:84px 1fr;gap:16px;background:#fff;border:1px solid rgba(17,20,28,.1);border-left:7px solid var(--c);border-radius:18px;padding:18px 20px}}
.vz img,.vz .ini{{width:84px;height:84px;border-radius:50%;object-fit:cover;background:#e6e9ee;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:26px;color:#4d5462}}
.vz b{{font-size:21px;display:block}}.vz small{{font-size:15px;color:#667085;display:block;margin-top:2px}}
.vz em{{display:inline-block;font-style:normal;font-size:14px;font-weight:700;color:#fff;background:var(--c);border-radius:999px;padding:2px 10px;margin-top:6px}}
.vz p{{font-size:17px;line-height:1.35;color:#2b303b;margin-top:8px}}""")


# ── 13 · Cierre ──────────────────────────────────────────────────────────────────────────────────────────────
def c13():
    return pagina(13, f"""
<div class="k" style="margin-top:110px">Síguelo a diario</div>
<h1 style="font-size:92px">Todo esto se actualiza cada día</h1>
<p class="sub" style="font-size:30px;margin-top:24px">La ficha oficial de la Cámara, los órdenes del día, la prensa y las redes, en un solo lugar. Con el texto de los 106 artículos, la calculadora de cuánto te cuesta y la cuenta de votos para hacerla tú mismo.</p>
<div class="url"><span>ricardoruiz.co/ley-de-rescate-avance.html</span></div>
<p class="sub" style="font-size:24px;margin-top:26px">Un seguimiento de <b>Caudal × Cauce</b>. Mide lo que se publica, no lo que piensa el país.</p>""", f"""
.url{{margin-top:44px;background:{AZUL};color:#fff;border-radius:22px;padding:28px 32px;font-size:36px;font-weight:700;letter-spacing:-.01em}}""")


CUADROS = {f'{i:02d}': f for i, f in enumerate([c01, c02, c03, c04, c05, c06, c07, c08, c09, c10, c11, c12, c13], 1)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / '_html'; tmp.mkdir(exist_ok=True)
    for k in (sys.argv[1:] or list(CUADROS)):
        h = tmp / f'{k}.html'; h.write_text(CUADROS[k]())
        png = OUT / f'{k}.png'
        subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1',
                        '--window-size=1080,1080', '--virtual-time-budget=3000', f'--screenshot={png}', h.as_uri()],
                       check=True, capture_output=True)
        print('→', png.relative_to(REPO))


if __name__ == '__main__':
    main()
