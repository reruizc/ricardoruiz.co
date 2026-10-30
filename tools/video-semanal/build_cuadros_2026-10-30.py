#!/usr/bin/env python3
"""Video semanal · cuadros del 30-oct-2026 · Ley de Rescate Económico (PL 477 de 2026 Cámara).

Dos videos: «¿Quién paga?» (cuadros 01-08) y «¿Cómo le pega a usted?» (cuadros 11-17).
Todo dato lleva su página del PDF radicado (334 págs., SHA-256 4a7e5293…, idéntico al que
sirve camara.gov.co) o su fuente de prensa. Mismo chasis y paleta de build_cuadros_2026-10-28.py.

  python3 tools/video-semanal/build_cuadros_2026-10-30.py

Salida: rrss/video/semana-2026-10-30/cuadros/{html,png}/
"""
import html
import math
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SEMANA = '2026-10-30'
OUT = REPO / f'rrss/video/semana-{SEMANA}/cuadros'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
FONTS = '../../../fuente-congreso-60s/fonts'
FECHA = '30 oct 2026'
PL = 'PL 477 de 2026 Cámara'

FAVOR, CONTRA, MEDIO, SIN, NUEVO = '#3987e5', '#d95926', '#199e70', '#5b6275', '#161b2b'
NARANJA = '#f97316'
e = html.escape
UVT = 52374          # UVT 2026, p. 104 del proyecto
SM = 1750905         # salario mínimo 2026, Tabla 1 del proyecto (p. 56)

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
.k {{ font-size: 24px; letter-spacing: .18em; font-weight: 700; color: {NARANJA}; text-transform: uppercase; }}
.k span {{ color: #7d8396; }}
h1 {{ font-size: 62px; line-height: 1.04; font-weight: 700; letter-spacing: -.02em; margin-top: 22px; }}
.sub {{ font-size: 29px; line-height: 1.32; color: #b9bdc9; font-weight: 300; margin-top: 20px; max-width: 930px; }}
.body {{ margin-top: 40px; }}
.foot {{ position: absolute; left: 72px; right: 72px; bottom: 150px; border-top: 1px solid #1c2233; padding-top: 18px;
  display: flex; justify-content: space-between; gap: 30px; font-size: 19px; color: #7d8396; line-height: 1.35; }}
.foot b {{ color: #f4f3ef; font-weight: 700; }}
.foot > div:last-child {{ white-space: nowrap; }}
.card {{ background: rgba(13,17,32,.85); border: 1px solid #1c2233; border-radius: 14px; }}
.leg {{ display: flex; flex-wrap: wrap; gap: 14px 28px; font-size: 22px; color: #b9bdc9; margin-top: 26px; }}
.leg i {{ display: inline-block; width: 22px; height: 22px; border-radius: 5px; vertical-align: -4px; margin-right: 10px; }}
.big {{ font-size: 112px; font-weight: 700; letter-spacing: -.045em; line-height: 1; }}
.bigt {{ font-size: 27px; color: #b9bdc9; margin-top: 8px; line-height: 1.3; }}
.aviso {{ font-size: 26px; color: #c8ccd6; border-left: 4px solid {NARANJA}; padding-left: 16px; margin-top: 30px; line-height: 1.35; }}
.aviso b {{ color: #f4f3ef; }}
.it {{ margin-top: 16px; background: rgba(13,17,32,.9); border: 1px solid #1c2233; border-left: 6px solid {MEDIO}; border-radius: 12px; padding: 16px 24px; }}
.it b {{ font-size: 30px; }} .it small {{ display: block; font-size: 23px; color: #b9bdc9; margin-top: 4px; line-height: 1.3; }}
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ padding: 12px 14px; font-size: 26px; text-align: left; border-bottom: 1px solid #1c2233; }}
th {{ font-size: 21px; letter-spacing: .08em; text-transform: uppercase; color: #7d8396; font-weight: 700; }}
td.n, th.n {{ text-align: right; white-space: nowrap; }}
.cols {{ display: flex; gap: 20px; }}
.col {{ flex: 1; min-width: 0; }}
.ch {{ font-size: 22px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; margin-bottom: 14px; }}
.ch i {{ display: inline-block; width: 18px; height: 18px; border-radius: 4px; margin-right: 10px; vertical-align: -2px; }}
.li {{ font-size: 25px; line-height: 1.3; padding: 8px 0; border-bottom: 1px solid #1c2233; color: #e4e6ec; }}
.li small {{ color: #7d8396; font-size: 20px; }}
"""


def pagina(n, total, kicker, titulo, sub, cuerpo, fuente):
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{e(titulo)}</title>
<style>{CSS}</style></head><body><div class="f">
<div class="k">{e(kicker)} <span>· {e(FECHA)}</span></div>
<h1>{titulo}</h1>{f'<div class="sub">{sub}</div>' if sub else ''}
<div class="body">{cuerpo}</div></div>
<div class="foot"><div>Fuente: {e(fuente)}</div><div><b>Ricardo.Ruiz</b> · {n}/{total}</div></div>
</body></html>"""


def leyenda(items):
    return '<div class="leg">' + ''.join(f'<span><i style="background:{c}"></i>{e(t)}</span>' for c, t in items) + '</div>'


def waffle(grupos, por_fila=16, lado=23, gap=5, etiqueta=270):
    out = []
    for nombre, celdas, nota in grupos:
        filas = math.ceil(len(celdas) / por_fila)
        alto = filas * (lado + gap) - gap
        sq = ''.join(f'<rect x="{(i % por_fila) * (lado + gap)}" y="{(i // por_fila) * (lado + gap)}" width="{lado}" height="{lado}" rx="6" fill="{c}"/>'
                     for i, c in enumerate(celdas))
        out.append(f'<div style="display:flex;align-items:flex-start;gap:20px;margin-bottom:5px">'
                   f'<div style="width:{etiqueta}px;font-size:21px;line-height:1.1;padding-top:2px">{e(nombre)}'
                   f'<div style="font-size:17px;color:#7d8396;margin-top:1px">{e(nota)}</div></div>'
                   f'<svg width="{por_fila * (lado + gap)}" height="{alto}">{sq}</svg></div>')
    return ''.join(out)


def barras_h(filas, ancho=520, alto=42, color=CONTRA, fmt=lambda v: f'{v:,.0f}', etiqueta=250, paso=60, colores=None):
    maxv = max(v for _, v in filas)
    W, H = etiqueta + 24 + ancho + 240, paso * len(filas)
    g = ''
    for i, (nombre, v) in enumerate(filas):
        y = i * paso
        w = max(4, ancho * v / maxv)
        x0 = etiqueta + 24
        c = colores[i] if colores else color
        g += (f'<text x="{etiqueta}" y="{y + alto / 2 + 9}" text-anchor="end" font-size="26" fill="#f4f3ef">{e(nombre)}</text>'
              f'<rect x="{x0}" y="{y}" width="{w:.1f}" height="{alto}" rx="4" fill="{c}"/>'
              f'<text x="{x0 + w + 14:.1f}" y="{y + alto / 2 + 9}" font-size="25" font-weight="700" fill="#f4f3ef">{e(fmt(v))}</text>')
    return f'<svg width="{W}" height="{H}" style="font-family:H,Helvetica Neue,sans-serif">{g}</svg>'


def apiladas(filas, ancho=560, alto=44, etiqueta=120, paso=62):
    maxt = max(sum(v for v, _ in segs) for _, segs, _ in filas)
    W, H = etiqueta + 24 + ancho + 200, paso * len(filas)
    g = ''
    for i, (nombre, segs, texto) in enumerate(filas):
        y, x = i * paso, etiqueta + 24
        g += f'<text x="{etiqueta}" y="{y + alto / 2 + 9}" text-anchor="end" font-size="26" font-weight="700" fill="#f4f3ef">{e(nombre)}</text>'
        for v, c in segs:
            w = ancho * v / maxt
            if w > 0:
                g += f'<rect x="{x:.1f}" y="{y}" width="{max(w - 3, 1):.1f}" height="{alto}" rx="4" fill="{c}"/>'
            x += w
        g += f'<text x="{etiqueta + 24 + ancho + 18}" y="{y + alto / 2 + 9}" font-size="24" fill="#b9bdc9">{e(texto)}</text>'
    return f'<svg width="{W}" height="{H}" style="font-family:H,Helvetica Neue,sans-serif">{g}</svg>'


def tabla(cab, filas, numericas=()):
    th = ''.join(f'<th class="{"n" if i in numericas else ""}">{e(c)}</th>' for i, c in enumerate(cab))
    tr = ''.join('<tr>' + ''.join(f'<td class="{"n" if i in numericas else ""}">{c}</td>' for i, c in enumerate(f)) + '</tr>' for f in filas)
    return f'<table><tr>{th}</tr>{tr}</table>'


def columnas(cols):
    """cols = [(titulo, color, [(texto, nota)])]."""
    out = ''
    for t, c, items in cols:
        li = ''.join(f'<div class="li">{e(a)}{f"<br><small>{e(b)}</small>" if b else ""}</div>' for a, b in items)
        out += f'<div class="col"><div class="ch"><i style="background:{c}"></i>{e(t)}</div>{li}</div>'
    return f'<div class="cols">{out}</div>'


def posturas(arb, cols):
    def col(titulo, color, items):
        cards = ''.join(
            f'<div class="card" style="padding:18px 18px 20px;margin-bottom:14px;border-top:5px solid {color}">'
            f'<div style="font-size:24px;font-weight:700;line-height:1.15">{e(a)}</div>'
            f'<div style="font-size:20px;color:#b9bdc9;line-height:1.3;margin-top:8px">{e(b)}</div></div>' for a, b in items)
        return (f'<div style="flex:1;min-width:0"><div style="font-size:21px;font-weight:700;letter-spacing:.06em;'
                f'text-transform:uppercase;margin-bottom:14px;color:#f4f3ef"><i style="display:inline-block;width:18px;height:18px;'
                f'border-radius:4px;background:{color};margin-right:10px;vertical-align:-2px"></i>{e(titulo)}</div>{cards}</div>')
    return (f'<div class="card" style="padding:18px 24px;margin-bottom:22px;display:flex;gap:18px;align-items:baseline">'
            f'<div style="font-size:21px;letter-spacing:.12em;font-weight:700;color:#7d8396;white-space:nowrap">DECIDE</div>'
            f'<div style="font-size:23px;line-height:1.3"><b>{e(arb[0])}</b> · <span style="color:#b9bdc9">{e(arb[1])}</span></div></div>'
            f'<div style="display:flex;gap:16px">' + ''.join(col(t, c, items) for t, c, items in cols) + '</div>')


# ─────────────────────────────────────────────────────────── datos (con su página del PDF)
# Tabla 14, p. 204 · % del PIB · efecto de la ley sobre el balance primario.
T14 = {  # concepto: [2027, 2028, 2029, 2030]
    'eficiencia': [0.39, 0.31, 0.31, 0.31],      # fondos, transferencias
    'personal': [0.00, 0.24, 0.47, 0.52],        # facultades extraordinarias
    'ops': [0.19, 0.19, 0.18, 0.18],             # contratos de prestación de servicios
    'exoneracion': [0.56, 0.41, 0.44, 0.45],     # empleadores vuelven a pagar SENA, ICBF, salud
    'cotizaciones': [0.27, 0.23, 0.24, 0.24],    # empleados e independientes
    'cajas': [0.14, 0.14, 0.15, 0.15],
    'licores_tabaco': [0.49, 0.53, 0.54, 0.54],
    'iva': [0.17, 1.05, 1.05, 1.06],
    'saludables': [0.00, 0.08, 0.08, 0.08],
    'renta_pn': [0.13, 0.57, 0.56, 0.57],
    'carbono': [0.03, 0.04, 0.05, 0.06],
    'sobretasa': [0.00, 0.03, 0.03, 0.03],
    'total_ley': [2.35, 3.58, 3.87, 4.09],
}
RECORTE = [sum(T14[k][i] for k in ('eficiencia', 'personal', 'ops')) for i in range(4)]
TRASLADO = [sum(T14[k][i] for k in ('exoneracion', 'cotizaciones', 'cajas')) for i in range(4)]
IMPUESTOS = [sum(T14[k][i] for k in ('licores_tabaco', 'iva', 'saludables', 'renta_pn', 'carbono', 'sobretasa')) for i in range(4)]
PART_RECORTE = [RECORTE[i] / T14['total_ley'][i] for i in range(4)]

# Cotización a salud del empleado, art. 21 (p. 230) · del independiente (p. 231).
SALUD_DEP = [('Hasta 2 salarios mínimos', '4 %', 'igual que hoy'), ('De 2 a 4', '5,5 %', '+1,5'), ('De 4 a 5', '6 %', '+2'),
             ('De 5 a 10', '6,5 %', '+2,5'), ('De 10 a 15', '7 %', '+3'), ('De 15 a 20', '7,5 %', '+3,5'), ('De 20 a 25', '8 %', '+4')]
SALUD_IND = [('Hasta 2 salarios mínimos', '12,5 %', 'igual que hoy'), ('De 2 a 4', '13 %', '+0,5'), ('De 4 a 5', '13,5 %', '+1'),
             ('De 5 a 10', '14 %', '+1,5'), ('De 10 a 15', '14,5 %', '+2'), ('De 15 a 20', '15 %', '+2,5'), ('De 20 a 25', '15,5 %', '+3')]


def salud_dep(S):
    r = S / SM
    for top, t in [(2, .04), (4, .055), (5, .06), (10, .065), (15, .07), (20, .075), (25, .08)]:
        if r <= top:
            return t
    return .08


def renta_act(u):   # art. 241 vigente
    for lo, hi, t, b in [(0, 95, 0, 0), (95, 150, .19, 0), (150, 360, .28, 10), (360, 640, .33, 69), (640, 945, .35, 162), (945, 2300, .37, 268), (2300, 1e9, .39, 770)]:
        if u <= hi:
            return (u - lo) * t + b


def renta_nue(u):   # art. 50 del proyecto (tabla de retención, p. 259-260)
    for lo, hi, t, b in [(0, 65, 0, 0), (65, 95, .09, 0), (95, 150, .19, 3), (150, 360, .28, 13), (360, 640, .33, 72), (640, 1e9, .39, 164)]:
        if u <= hi:
            return (u - lo) * t + b


def fsp(S):
    r = S / SM
    return 0 if r < 4 else .01 if r < 16 else .012


def extra_mes(S):
    """Cuánto más retienen al mes a un asalariado: salud nueva + retención nueva − retención actual.
    Solo con la renta exenta del 25 % (tope 790 → 630 UVT); sin otras deducciones ni IVA."""
    def calc(sal, tope, tabla):
        ap = S * (.04 + sal + fsp(S))
        b = S - ap
        ex = min(b * .25, tope / 12 * UVT)
        return tabla((b - ex) / UVT) * UVT
    r0 = calc(.04, 790, renta_act)
    r1 = calc(salud_dep(S), 630, renta_nue)
    return S * (salud_dep(S) - .04) + (r1 - r0)


IMPACTO = [(S, extra_mes(S)) for S in (3.5e6, 4e6, 6e6, 8e6, 10e6, 15e6, 20e6)]

# Comisiones Terceras (roster oficial: camara.gov.co/representantes · API del Senado, oct-2026).
# Clasificación por lo que cada bancada o persona ha DICHO sobre esta ley (prensa 29-30 oct), no por adivinar.
SEN3 = [('Salvación Nacional', 1, FAVOR, 'partido del presidente'),
        ('Centro Democrático', 3, MEDIO, 'sí al recorte, no a los impuestos'),
        ('Conservador', 1, SIN, 'sin postura pública'), ('Cambio Radical', 1, SIN, 'sin postura pública'),
        ('La U', 1, SIN, 'sin postura pública'), ('Liberal', 2, SIN, 'sin postura pública'),
        ('ASI', 1, SIN, 'sin postura pública'), ('Pacto Histórico', 3, CONTRA, '«golpe al bolsillo»')]
CAM3 = [('Centro Democrático', 5, MEDIO, 'sí al recorte, no a los impuestos'),
        ('Conservador', 4, SIN, 'preside la comisión (Ape Cuello)'), ('Cambio Radical', 3, SIN, 'sin postura pública'),
        ('La U', 3, SIN, 'sin postura pública'), ('Liberal', 6, SIN, 'sin postura pública'),
        ('Alianza Verde', 2, MEDIO, 'Juvinao: «excesivamente dura»'), ('Paz y étnicas', 2, SIN, 'sin postura pública'),
        ('Pacto Histórico', 6, CONTRA, '«golpe al bolsillo»')]
assert sum(n for _, n, _, _ in SEN3) == 13 and sum(n for _, n, _, _ in CAM3) == 31


def cuadros():
    q = []
    pesos = lambda v: f'${v:,.0f}'.replace(',', '.')

    # ══════════════════════════════════════ VIDEO 1 · ¿Quién paga?
    q.append(('01-portada', 'Ley de Rescate Económico', '¿Quién paga el rescate?',
              'El Gobierno radicó el jueves su ajuste fiscal: 334 páginas, 106 artículos. Esto es lo que dice el texto, no lo que dicen de él.',
              f'''<div class="card" style="padding:28px 32px;margin-top:10px"><div class="big" style="font-size:96px">106</div><div class="bigt">artículos · Proyecto de Ley 477 de 2026 Cámara · radicado el 29 de octubre por el ministro de Hacienda, Miguel Gómez Martínez</div></div>
<div class="cols" style="margin-top:26px">
<div class="card col" style="padding:22px 26px"><div class="big" style="font-size:72px">4,7 %</div><div class="bigt">del PIB de ajuste al año en 2030 (2,4 % en 2027)</div></div>
<div class="card col" style="padding:22px 26px"><div class="big" style="font-size:72px">2028</div><div class="bigt">arranca el grueso del IVA, después de las elecciones regionales de 2027</div></div></div>
<div class="aviso"><b>Es un proyecto.</b> Nada de esto es ley: empieza su trámite en las comisiones económicas y puede cambiar.</div>''',
              f'{PL} · pp. 1, 203-204 · ficha camara.gov.co'))

    filas = [(str(2027 + i), [(RECORTE[i], FAVOR), (TRASLADO[i], MEDIO), (IMPUESTOS[i], CONTRA)],
              f'{PART_RECORTE[i] * 100:.0f} % recorte') for i in range(4)]
    q.append(('02-recorte-vs-impuestos', '¿Quién paga? · de dónde sale la plata', 'El Gobierno dice que 7 de cada 10 pesos son recorte. Su propia tabla dice 1 de cada 4.',
              'La Tabla 14 del proyecto desagrega el ajuste. Lo que es recorte de gasto del Estado (fondos, nómina, contratistas) pesa un cuarto. El resto lo pagan empresas, trabajadores y consumidores.',
              f'''{apiladas(filas)}
{leyenda([(FAVOR, 'Recorte de gasto del Estado'), (MEDIO, 'Empresas y trabajadores vuelven a pagar aportes a salud, SENA e ICBF'), (CONTRA, 'Impuestos: IVA, renta, licores, tabaco, carbono')])}
<div class="aviso"><b>Por qué la cuenta no cuadra con el 70 %:</b> el Gobierno suma como «reducción del Estado» los aportes que vuelven a pagar empresas y trabajadores, y cuenta medidas que van en otros decretos, no en esta ley (p. 203).</div>''',
              f'{PL} · Tabla 14, p. 204 · cálculo propio sobre esa tabla · en % del PIB'))

    q.append(('03-quien-gana-quien-pierde', '¿Quién paga? · según el Gobierno', '«Paga el 10 % más rico.» Ese 10 % es un hogar de 14 millones al mes.',
              'Las tres cifras grandes son del proyecto. El ingreso de cada grupo sale de dividirlas por el porcentaje que el mismo texto les asigna.',
              f'''<div class="cols">
<div class="card col" style="padding:24px 26px;border-top:6px solid {CONTRA}"><div class="k" style="color:{CONTRA}">El 10 % de mayores ingresos</div><div class="big" style="font-size:84px;margin-top:14px">−$500.000</div><div class="bigt">al mes por hogar · 3,6 % de su ingreso</div><div style="font-size:27px;line-height:1.25;margin-top:16px;padding-top:14px;border-top:1px solid rgba(255,255,255,.1)">Hogar promedio de <b>$13,9 M</b> al mes. Se entra a pagar renta desde <b>$5,5 M</b> por persona.</div></div>
<div class="card col" style="padding:24px 26px;border-top:6px solid {FAVOR}"><div class="k" style="color:{FAVOR}">El 68 % de menores ingresos</div><div class="big" style="font-size:84px;margin-top:14px">+$65.000</div><div class="bigt">al mes por persona · 4,7 % más de ingreso</div><div style="font-size:27px;line-height:1.25;margin-top:16px;padding-top:14px;border-top:1px solid rgba(255,255,255,.1)">Hogar promedio de <b>$1,4 M</b> al mes. Lo recibe por la devolución del IVA, desde 2028.</div></div></div>
<div class="card" style="padding:22px 26px;margin-top:20px;border-top:6px solid {SIN}"><div class="k" style="color:#7d8396">El 22 % del medio · hogares de ~$2 M a ~$5 M</div><div style="font-size:30px;line-height:1.3;margin-top:10px">El resumen no les da cifra. Están por encima del decil 6, el último con devolución del IVA, y por debajo del umbral de renta: no reciben nada y sí pagan el IVA al mercado y la salud más cara desde dos mínimos.</div></div>
<div class="aviso">«El 10 % de los hogares de mayores recursos asumirán el 97 % del esfuerzo tributario total de los hogares» (p. 194). Deciles 1 a 6: +10,2 % · +6,3 % · +2,5 % · … · +1,2 %. Deciles 7 a 9: sin cifra.</div>''',
              f'{PL} · resumen p. 3 · pp. 105-107, 194 · ingreso por grupo: cálculo propio ($500.000 ÷ 3,6 % · $65.000 ÷ 4,7 %)'))

    q.append(('04-iva-comida', '¿Quién paga? · IVA desde 2028', 'La comida que pasa a pagar IVA del 19 %',
              'Comparación del artículo 424 vigente (Estatuto Tributario, Secretaría del Senado) con el artículo 42 del proyecto. Lo que no está en la lista nueva, paga.',
              columnas([
                  ('Hoy sin IVA → 19 %', CONTRA, [('Tomate, cebolla, zanahoria, lechuga, repollo', 'y las demás hortalizas frescas'), ('Frutas: banano, plátano, mango, cítricos, manzana, uva', 'todas las partidas 08.03 a 08.10'), ('Fríjol, lenteja, garbanzo', 'legumbres secas, 07.13'), ('Sal, miel, maíz, café en grano', ''), ('Queso fresco', 'hoy exento'), ('Abonos, plaguicidas, tractores', ''), ('Celulares hasta $1,15 M y computadores hasta $2,6 M', 'hoy excluidos')]),
                  ('Hoy al 5 % → 19 %', MEDIO, [('Café', ''), ('Azúcar y panela industrial', ''), ('Aceites, harina de trigo, avena, pasta', ''), ('Chocolate de mesa', ''), ('Alimento para animales', ''), ('Medicina prepagada y planes complementarios', 'pasan a excluidos'), ('Carros híbridos y eléctricos', 'desde que se apruebe la ley')]),
                  ('Siguen sin IVA', FAVOR, [('Arroz, papa, yuca', ''), ('Pan y arepa', ''), ('Panela artesanal', ''), ('Carne, pollo, pescado', ''), ('Leche y huevos', ''), ('Medicamentos', ''), ('Servicios públicos, transporte público, arriendo, salud, educación', '')])]) +
              '<div class="aviso"><b>Ojo:</b> la exposición de motivos (p. 92) dice que no se gravan «la sal» ni «los granos». El artículo no los salva: fríjol, lenteja y sal quedan por fuera de la lista.</div>',
              f'{PL} · arts. 42, 45, 46 y 106 (pp. 248-258, 333) · ET arts. 424, 468-1 y 477 vigentes'))

    q.append(('05-efectiva', '¿Quién paga? · la compensación', 'EfectIVA: le devuelven el IVA a 35 millones de personas',
              'Es la pieza que sostiene toda la cuenta del Gobierno. Arranca en 2028, el mismo día que el IVA nuevo.',
              f'''{barras_h([('Pobreza (deciles 1-3)', 100), ('Vulnerable · decil 4', 50), ('Vulnerable · decil 5', 40), ('Vulnerable · decil 6', 30)], fmt=lambda v: f'{v:.0f} % del IVA', etiqueta=330, ancho=420, color=FAVOR)}
<div class="cols" style="margin-top:28px">
<div class="card col" style="padding:20px 24px"><div class="big" style="font-size:66px">$288.000</div><div class="bigt">tope al mes por persona (5,5 UVT)</div></div>
<div class="card col" style="padding:20px 24px"><div class="big" style="font-size:66px">15 días</div><div class="bigt">cada cuánto se paga, por DPS</div></div>
<div class="card col" style="padding:20px 24px"><div class="big" style="font-size:66px">dic-2027</div><div class="bigt">un anticipo antes de que suba el IVA</div></div></div>
<div class="aviso"><b>La condición:</b> solo cuenta el IVA de compras con factura electrónica a nombre de la persona. Quien compre en la tienda sin factura no recibe nada, salvo un monto mínimo para la pobreza extrema.</div>''',
              f'{PL} · arts. 38-40, pp. 241-247 · exposición pp. 81-84'))

    q.append(('06-reloj', '¿Quién paga? · el reloj', 'Tiene hasta el 16 de diciembre, o se cae',
              'Calendario que el presidente de la Comisión Tercera de la Cámara le dio a El Tiempo antes de la radicación. Lo tributario arranca en 2027; el IVA, en 2028.',
              ''.join(f'<div style="display:flex;gap:24px;padding:13px 0;border-bottom:1px solid #1c2233"><div style="width:230px;font-size:25px;font-weight:700;color:{c}">{e(f)}</div><div style="font-size:27px;line-height:1.3">{e(t)}<div style="font-size:21px;color:#7d8396;margin-top:3px">{e(s)}</div></div></div>' for f, t, s, c in [
                  ('29 oct 2026', 'Radicada en la Cámara', '106 artículos · autor: MinHacienda', '#f4f3ef'),
                  ('nov · 3.ª y 4.ª semana', 'Comisiones económicas', 'Terceras de Cámara y Senado; juntas si hay mensaje de urgencia', NARANJA),
                  ('dic · 1.ª quincena', 'Plenarias de Cámara y Senado', 'cuatro debates si va con urgencia', NARANJA),
                  ('16 dic 2026', 'Termina la legislatura', 'si no está aprobada, se archiva', CONTRA),
                  ('1 ene 2027', 'Salud, renta, aportes de empresas, licores', 'arts. 20-21, 27, 47-50, 57', '#f4f3ef'),
                  ('oct 2027', 'Elecciones regionales', '', '#7d8396'),
                  ('1 ene 2028', 'Arranca el IVA nuevo y EfectIVA', 'arts. 38, 42, 45, 46', '#f4f3ef')]),
              f'{PL} · El Tiempo (Ape Cuello, presidente de la Tercera de Cámara) · art. 138 C.P.'))

    def waf(grupos):
        return waffle([(n, [c] * k, nota) for n, k, c, nota in grupos])
    q.append(('07-fuerzas-internas', '¿Quién paga? · quién la vota primero', 'Senado: 7 de 13. Cámara: 16 de 31. Nadie los tiene todavía.',
              None,
              f'''<div style="font-size:24px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;margin-bottom:12px">Comisión Tercera del Senado · 13</div>{waf(SEN3)}
<div style="font-size:24px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;margin:22px 0 12px">Comisión Tercera de la Cámara · 31</div>{waf(CAM3)}
{leyenda([(FAVOR, 'Apoya'), (MEDIO, 'Con reparos: sí al recorte, no a los impuestos'), (CONTRA, 'En contra'), (SIN, 'Sin postura pública')])}
<div class="aviso" style="margin-top:16px">Sin voto nominal todavía: el color es lo que cada bancada ha dicho. <b>La llave:</b> liberales, conservadores, La U y Cambio Radical (5 de 13 y 16 de 31), sin postura. En dic-2024 estas comisiones hundieron la tributaria de Petro.</div>''',
              'Rosters oficiales (camara.gov.co · API del Senado) · declaraciones en El Tiempo, Semana, Vanguardia, Infobae (29-30 oct) · Senado, 11-dic-2024'))

    q.append(('08-fuerzas-externas', '¿Quién paga? · fuera del Congreso', 'Quién empuja y quién frena',
              None,
              posturas(('Comisiones Terceras de Cámara y Senado', 'preside la de Cámara Alfredo Ape Cuello, conservador; la plenaria del Senado, Honorio Henríquez, del Centro Democrático'), [
                  ('Empujan', FAVOR, [('Gobierno De la Espriella', 'Restrepo: «El Estado se aprieta el cinturón, aportan más los que más tienen».'),
                                      ('Mauricio Cárdenas · exministro', '«Era algo absolutamente necesario». Apoya recortar $40 billones y mejorar el recaudo.'),
                                      ('Luis Fernando Mejía · ex Fedesarrollo', '«Lo que está en juego es la sostenibilidad de las finanzas públicas».'),
                                      ('Gremios petroleros (ACP)', 'Piden quitar la sobretasa y un régimen de estabilidad. El proyecto trae el RUGE.')]),
                  ('Matizan', MEDIO, [('Honorio Henríquez · presidente del Senado', '«Los colombianos no aguantan un impuesto más». Garantiza el debate.'),
                                      ('Lisandro Junco · ex DIAN', '«Más clase media entra a declarar y pagar».'),
                                      ('Andrés Valencia · ex MinAgricultura', 'IVA a insumos del agro: más costos, informalidad y contrabando.'),
                                      ('ANDI, Fenalco, Fedesarrollo, Asobancaria', 'Sin pronunciamiento encontrado al 30 de octubre.')]),
                  ('Lo critican', CONTRA, [('María Clara Posada · Centro Democrático', '«No cuenten conmigo para aumentar impuestos a la clase media».'),
                                           ('Gabriel Vallejo · director del CD', '«Los colombianos esperan una reducción o incluso eliminación de impuestos».'),
                                           ('Gabriel Becerra · Pacto Histórico', '«Un golpe al bolsillo de las familias trabajadoras y la clase media».'),
                                           ('Catherine Juvinao · Verde, Comisión Tercera', '«Parece una medida excesivamente dura»: IVA a frutas, verduras e internet de estratos 1 a 3.')])]),
              'El Tiempo · Semana · Vanguardia · Infobae · La FM (29-30 oct 2026) · roster de comisiones'))

    # ══════════════════════════════════════ VIDEO 2 · ¿Cómo le pega a usted?
    q.append(('11-portada', 'Ley de Rescate Económico', '¿Y a usted cómo le pega?',
              'Seis perfiles, con los artículos del proyecto en la mano. Si gana menos de dos salarios mínimos, la ley no le toca el sueldo.',
              ''.join(f'<div class="it" style="border-left-color:{c}"><b>{e(a)}</b><small>{e(b)}</small></div>' for a, b, c in [
                  ('Asalariado que gana más de $3,5 millones', 'más cotización a salud y renta desde más abajo', CONTRA),
                  ('Independiente', 'cotiza más a salud desde 2 salarios mínimos', CONTRA),
                  ('Pequeña empresa', 'vuelve a pagar SENA, ICBF y salud; baja la renta', MEDIO),
                  ('Hogar pobre o vulnerable', 'le devuelven el IVA, si compra con factura', FAVOR),
                  ('Cualquiera que haga mercado', 'IVA a frutas, verduras, café, azúcar', CONTRA),
                  ('Patrimonios de más de $5.000 millones', 'el impuesto al patrimonio sube de umbral y se acaba en 2030', FAVOR)]),
              f'{PL} · arts. 20-21, 38-50, 57, 66-68'))

    q.append(('12-asalariado', '¿Cómo le pega? · asalariado', 'Desde 2 salarios mínimos, más salud. Desde $5,5 millones, renta.',
              'Hoy el empleado aporta 4 % a salud sin importar cuánto gane. El proyecto lo vuelve escalonado desde enero de 2027, y baja el piso desde el que se paga renta.',
              tabla(['Salario (en mínimos)', 'Salud', 'Cambio'], [(a, b, f'<span style="color:{"#b9bdc9" if c.startswith("igual") else CONTRA}">{c}</span>') for a, b, c in SALUD_DEP], numericas=(1, 2)) +
              f'''<div class="cols" style="margin-top:26px">
<div class="card col" style="padding:18px 22px"><div class="big" style="font-size:58px">$5,5 M</div><div class="bigt">ingreso mensual desde el que se empieza a pagar renta (hoy ~$9 M), con un tramo nuevo del 9 %</div></div>
<div class="card col" style="padding:18px 22px"><div class="big" style="font-size:58px">−160 UVT</div><div class="bigt">baja el tope de la renta exenta del 25 % (de 790 a 630 UVT) y se acaba la deducción extra por dependiente</div></div></div>''',
              f'{PL} · art. 21 (p. 230) · arts. 47-50 (pp. 258-260) · exposición pp. 101-105'))

    q.append(('13-cuanto-mas', '¿Cómo le pega? · asalariado', 'Cuánto más le descontarían cada mes',
              'Estimación propia con las tablas del proyecto: cotización a salud nueva más retención en la fuente nueva, menos la retención de hoy. Solo con la renta exenta del 25 %; sin otras deducciones ni el IVA.',
              barras_h([(f'Gana {pesos(S)}', v) for S, v in IMPACTO], fmt=lambda v: '$0' if v < 1 else f'+{pesos(round(v, -3))}', etiqueta=300, color=CONTRA) +
              f'''<div class="aviso"><b>La Silla Vacía llega a cifras parecidas:</b> $2,1 millones más al año con $6 millones de sueldo, y $4,3 millones con $10 millones. Quien tenga dependientes o deducciones de vivienda paga algo más de lo que muestra la barra, porque esas también se recortan.</div>''',
              f'{PL} · arts. 21, 47, 49, 50 · cálculo propio · salario mínimo 2026 $1.750.905 · UVT $52.374'))

    q.append(('14-independiente', '¿Cómo le pega? · independiente', 'El independiente cotiza sobre el 40 % de lo que gana, y esa tarifa también sube',
              'Hoy paga 12,5 % sobre el 40 % de sus ingresos. Desde 2027 la tarifa sube medio punto por tramo. El proyecto lo presenta como menos que a los asalariados, para corregir la asimetría entre los dos.',
              tabla(['Ingreso (en mínimos)', 'Salud', 'Cambio'], [(a, b, f'<span style="color:{"#b9bdc9" if c.startswith("igual") else CONTRA}">{c}</span>') for a, b, c in SALUD_IND], numericas=(1, 2)) +
              '<div class="aviso"><b>Ejemplo del proyecto (Tabla 3, p. 57):</b> con $5,25 millones de ingreso, un independiente pasaría de pagar $262.636 a $273.141 al mes. Un asalariado con el mismo sueldo pasa de $210.109 a $288.899.</div>',
              f'{PL} · art. 21 (p. 231) · exposición pp. 55-58'))

    q.append(('15-empresa', '¿Cómo le pega? · pequeña empresa', 'Vuelve a pagar aportes por quien gane más de 2 mínimos. A cambio, baja la renta.',
              'Desde 2012 las empresas no pagan SENA, ICBF ni salud por trabajadores de menos de 10 salarios mínimos. El proyecto baja ese techo a 2.',
              tabla(['Trabajador que gana', 'SENA + ICBF', 'Salud (empleador)', 'Total'], [
                  ('Hasta 2 mínimos', '0 %', '0 %', '<b>0 %</b> · igual que hoy'),
                  ('De 2 a 3 mínimos', '1 % + 1 %', '4 %', f'<b style="color:{CONTRA}">6 %</b> · hoy 0 %'),
                  ('Más de 3 mínimos', '2 % + 3 %', '8,5 %', f'<b style="color:{CONTRA}">13,5 %</b> · hoy 0 % hasta 10 mínimos')], numericas=(1, 2)) +
              f'''<div class="cols" style="margin-top:26px">
<div class="card col" style="padding:18px 22px;border-top:6px solid {FAVOR}"><div class="big" style="font-size:58px">35 → 31 %</div><div class="bigt">renta de las empresas: 33 % en 2027 y 31 % desde 2028. Bancos y aseguradoras siguen con 5 puntos más hasta 2030</div></div>
<div class="card col" style="padding:18px 22px;border-top:6px solid {FAVOR}"><div class="big" style="font-size:58px">2 a 5</div><div class="bigt">trabajadores: si el empleador es persona natural, sigue exonerado de todo</div></div></div>
<div class="aviso">El propio proyecto estima que el 83,5 % de los asalariados queda con la exoneración completa y el 7,2 % con exoneración parcial (p. 47).</div>''',
              f'{PL} · art. 20 (pp. 228-230) · art. 57 (p. 267) · exposición pp. 46-47, 128'))

    q.append(('16-mercado', '¿Cómo le pega? · el mercado', 'Lo que sube de precio y lo que no',
              'Desde 2028, salvo donde se dice otra cosa. Para los hogares de los deciles 1 a 6, EfectIVA devuelve parte o todo, si compran con factura electrónica.',
              columnas([
                  ('Sube por el IVA', CONTRA, [('Frutas y verduras', 'salvo papa, yuca y hortalizas de vaina frescas'), ('Fríjol, lenteja, sal, miel, maíz', ''), ('Café, azúcar, aceite, pasta, chocolate', 'del 5 % al 19 %'), ('Queso fresco', ''), ('Celular de menos de $1,15 M', 'y computador de menos de $2,6 M'), ('Cine, boletas de eventos, nube, apuestas por internet', ''), ('Medicina prepagada', 'deja de pagar 5 %: pasa a excluida')]),
                  ('Sube por otros impuestos', MEDIO, [('Cigarrillos: +47 %', 'vapeadores +53 % · desde 2027'), ('Cerveza', 'impuesto nuevo: $330 por grado de alcohol + 10 % · desde 2027'), ('Licores y vinos', 'IVA del 19 % apenas se apruebe la ley'), ('Gasolina y gas', 'sube el impuesto al carbono en 2027, 2028 y 2029'), ('Bebidas azucaradas y con edulcorante', 'desde 2028'), ('Loterías y apuestas', 'el impuesto al premio pasa de 20 % a 30 %')]),
                  ('No cambia', FAVOR, [('Arroz, papa, yuca, pan, arepa, panela', ''), ('Carne, pollo, pescado, leche, huevos', ''), ('Medicamentos', ''), ('Luz, agua, gas domiciliario', ''), ('Transporte público', ''), ('Arriendo de vivienda', ''), ('Salud y educación', ''), ('ACPM', 'queda excluido')])]),
              f'{PL} · arts. 27-37, 42-46, 52-56, 106 · exposición pp. 66, 92-93'))

    q.append(('17-rentas-altas', '¿Cómo le pega? · rentas y patrimonios altos', 'Más renta por arriba, menos impuesto al patrimonio',
              'El 39 % marginal, que hoy empieza en 31.000 UVT, pasa a empezar en 8.670. El impuesto al patrimonio sube de umbral y tiene fecha de muerte.',
              f'''<div class="cols">
<div class="card col" style="padding:22px 26px;border-top:6px solid {CONTRA}"><div class="k" style="color:{CONTRA}">Renta</div><div class="big" style="font-size:64px;margin-top:12px">39 %</div><div class="bigt">para toda renta líquida sobre 8.670 UVT al año ($454 millones). Hoy ese tramo paga 35 % y 37 %. El Gobierno dice que cambia solo desde ~$50 millones mensuales</div></div>
<div class="card col" style="padding:22px 26px;border-top:6px solid {FAVOR}"><div class="k" style="color:{FAVOR}">Patrimonio</div><div class="big" style="font-size:64px;margin-top:12px">$5.000 M</div><div class="bigt">nuevo umbral (95.500 UVT; hoy 72.000 UVT, $3.771 millones). Tarifas de 0,5 % y 1 %. Solo hasta 2030</div></div></div>
<div class="cols" style="margin-top:20px">
<div class="card col" style="padding:20px 24px"><div class="big" style="font-size:56px">20 → 30 %</div><div class="bigt">ganancia ocasional de loterías y apuestas</div></div>
<div class="card col" style="padding:20px 24px"><div class="big" style="font-size:56px">Normalización</div><div class="bigt">impuesto para declarar activos omitidos, incluidos criptoactivos (arts. 70-71)</div></div></div>
<div class="aviso">El resumen ejecutivo pone al 10 % más rico un aporte neto de ~$500.000 al mes por hogar. Las empresas, en cambio, bajan su renta de 35 % a 31 %.</div>''',
              f'{PL} · arts. 48, 52, 66-68, 70-71 · exposición pp. 103-104, 139-142'))
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
    print('recorte real / total de la ley:', [f'{p * 100:.0f} %' for p in PART_RECORTE])
    print('impacto/mes:', [(int(S), int(v)) for S, v in IMPACTO])


if __name__ == '__main__':
    main()
