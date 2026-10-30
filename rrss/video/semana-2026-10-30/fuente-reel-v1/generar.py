#!/usr/bin/env python3
"""Reel de Instagram · Ley de Rescate · video 1 «¿Quién paga el rescate?» · 30 de octubre de 2026.

Arma index.html (HyperFrames) a partir de la grabación recortada y acelerada a 1,15
(assets/base.mp4, la hace cortar.py) y de su transcripción palabra por palabra
(transcripcion.json, whisper.cpp modelo small). Arriba va el video; abajo, un panel de datos por
bloque; en el empalme, subtítulos palabra por palabra. Cuando se nombra a alguien, su foto entra
como transición sobre la cámara (~2,4 s).

  python3 cortar.py "Bases de datos/30-oct.mov" && python3 generar.py
  npx --yes hyperframes@0.7.101 check
  npx --yes hyperframes@0.7.101 render --quality high --crf 16 --video-frame-format png

Datos: los del guion (../guion-v1-quien-paga.md) y de tools/video-semanal/build_cuadros_2026-10-30.py,
todos verificados contra el PDF radicado (PL 477 de 2026 Cámara).
Fotos: Juvinao (camara.gov.co) · Posada (app.senado.gov.co) · Cárdenas y Restrepo (Wikimedia Commons).
"""
import html
import json
import re
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BASE_DUR = 160.1
FIN = 2.0
TOTAL = round(BASE_DUR + FIN, 3)
e = html.escape

# ── Subtítulos: lo que dice el audio, bien escrito ─────────────────────────────────────────────
POR_IDX = {5: 'Gobierno', 20: 'Leyéndolas', 31: 'Gobierno', 60: '5 %', 128: 'Gobierno', 133: '10 %',
           176: 'sueldo,', 191: '68 %', 206: 'devolución', 215: '22 %', 244: 'sí', 264: 'fríjol,',
           272: 'pagarían', 275: '19 %.', 318: 'EfectIVA,', 331: '100 %', 360: 'de ley', 377: 'archiva.',
           403: 'Pacto', 445: 'de Petro.', 451: 'externas,', 455: 'Gobierno,', 462: 'Fedesarrollo.',
           475: 'Pacto', 477: 'Catherine', 478: 'Juvinao.', 485: 'ANDI,', 488: 'Asobancaria,', 495: 'video,'}
SALTAR = {21, 463}
crudas = [[x['offsets']['from'] / 1000, x['offsets']['to'] / 1000, x['text'].strip()]
          for x in json.load(open(AQUI / 'transcripcion.json'))['transcription'] if x['text'].strip()]
palabras = [[a, b, POR_IDX.get(i, t)] for i, (a, b, t) in enumerate(crudas) if i not in SALTAR]
W = {i: a for i, (a, _, _) in enumerate(crudas)}       # índice original → segundo


def cuando(texto, desde=0.0):
    for a, _, t in palabras:
        if a >= desde and t.strip('.,¿?').lower() == texto.lower():
            return a
    raise KeyError(texto)


# ── Tiempos, anclados a la transcripción ───────────────────────────────────────────────────────
T = {}
T['q'] = W[30] - 0.2            # «El Gobierno dice que es para evitar…»
T['tres'] = W[41]               # «uno de cada 3 pesos»
T['pib'] = W[56]                # «El ajuste llega…»
T['proy'] = W[65]               # «Y ojo, es un proyecto»
T['r'] = W[85] - 0.2            # «El vicepresidente dijo…»
T['vp'] = W[86]
T['siete'] = W[89]
T['tabla'] = W[98]
T['cuatro'] = W[115]            # «uno de cada 4»
T['resto'] = W[119]
T['g'] = W[127] - 0.2           # «El Gobierno dice que paga el 10 % más rico»
T['catorce'] = W[152]
T['cinco5'] = W[165]
T['quinientos'] = W[180]
T['pobre'] = W[187]
T['sesenta5'] = W[201]
T['medio'] = W[209]
T['iva'] = W[247] - 0.2         # «Lo que va a sonar más»
T['tomate'] = W[258]
T['nocambia'] = W[276]
T['contra'] = W[287]
T['ef'] = W[310] - 0.2          # «Y ahora hablamos de la compensación»
T['cien'] = W[330]
T['tope'] = W[337]
T['factura'] = W[344]
T['rel'] = W[353] - 0.2         # «Y cuando…»
T['nov'] = W[363]
T['dic'] = W[365]
T['dieciseis'] = W[368]
T['archiva'] = W[376]
T['fi'] = W[378] - 0.2          # «Ahora, ¿quién la vota primero?»
T['sen'] = W[386]
T['cam'] = W[395]
T['pacto'] = W[402]
T['cd'] = W[408]
T['bis'] = W[418]
T['prec'] = W[434]
T['fe'] = W[446] - 0.2          # «Ahora, respecto a las fuerzas…»
T['emp'] = W[452]
T['card'] = W[456]
T['fren'] = W[464]
T['pos'] = W[468]
T['juv'] = W[477]
T['call'] = W[479]
T['ci'] = W[492] - 0.2          # «En el próximo video…»
CORTES = {'ap': (0, T['q']), 'q': (T['q'], T['r']), 'r': (T['r'], T['g']), 'g': (T['g'], T['iva']),
          'iva': (T['iva'], T['ef']), 'ef': (T['ef'], T['rel']), 'rel': (T['rel'], T['fi']),
          'fi': (T['fi'], T['fe']), 'fe': (T['fe'], T['ci']), 'ci': (T['ci'], BASE_DUR)}

trozos, cur = [], []
for w in palabras:
    cur.append(w)
    txt = ' '.join(p[2] for p in cur)
    if re.search(r'[.,?]$', w[2]) or len(cur) >= 4 or len(txt) > 22:
        trozos.append(cur)
        cur = []
if cur:
    trozos.append(cur)

caps, cap_js = '', []
for i, tz in enumerate(trozos):
    ini = max(0.0, tz[0][0] - 0.05)
    fin = trozos[i + 1][0][0] - 0.05 if i + 1 < len(trozos) else BASE_DUR
    if fin - ini < 0.15:
        continue
    spans = ' '.join(f'<span id="w{i}_{j}">{e(p[2])}</span>' for j, p in enumerate(tz))
    caps += (f'<div class="cap clip" id="c{i}" data-start="{ini:.2f}" data-duration="{fin - ini:.2f}" '
             f'data-track-index="{60 + i % 2}"><div class="capt">{spans}</div></div>\n')
    for j, p in enumerate(tz):
        cap_js.append(f'tl.to("#w{i}_{j}",{{color:"#f97316",duration:.08}},{p[0]:.2f});')

NARANJA, AZUL, VERDE, GRIS, NUEVO = '#d95926', '#3987e5', '#199e70', '#5b6275', '#161b2b'


def clip(id_, ini, fin, track, inner, cls='panel'):
    return (f'<div class="{cls} clip" id="{id_}" data-start="{ini:.2f}" data-duration="{fin - ini:.2f}" '
            f'data-track-index="{track}">{inner}</div>\n')


# ── Datos (Tabla 14, p. 204 · % del PIB) ───────────────────────────────────────────────────────
T14 = {'eficiencia': [0.39, 0.31, 0.31, 0.31], 'personal': [0.00, 0.24, 0.47, 0.52], 'ops': [0.19, 0.19, 0.18, 0.18],
       'exoneracion': [0.56, 0.41, 0.44, 0.45], 'cotizaciones': [0.27, 0.23, 0.24, 0.24], 'cajas': [0.14, 0.14, 0.15, 0.15],
       'licores_tabaco': [0.49, 0.53, 0.54, 0.54], 'iva': [0.17, 1.05, 1.05, 1.06], 'saludables': [0.00, 0.08, 0.08, 0.08],
       'renta_pn': [0.13, 0.57, 0.56, 0.57], 'carbono': [0.03, 0.04, 0.05, 0.06], 'sobretasa': [0.00, 0.03, 0.03, 0.03],
       'total_ley': [2.35, 3.58, 3.87, 4.09]}
REC = [sum(T14[k][i] for k in ('eficiencia', 'personal', 'ops')) for i in range(4)]
TRA = [sum(T14[k][i] for k in ('exoneracion', 'cotizaciones', 'cajas')) for i in range(4)]
IMP = [sum(T14[k][i] for k in ('licores_tabaco', 'iva', 'saludables', 'renta_pn', 'carbono', 'sobretasa')) for i in range(4)]
maxt = max(REC[i] + TRA[i] + IMP[i] for i in range(4))

# ── Paneles ────────────────────────────────────────────────────────────────────────────────────
P = ''
P += clip('p-ap', *CORTES['ap'], 10, '''
  <div class="pk">Ley de Rescate Económico · PL 477 de 2026 Cámara</div>
  <div class="dosb"><div class="bx" id="ap1"><b>334</b><small>páginas</small></div><div class="bx" id="ap2"><b>106</b><small>artículos</small></div></div>
  <div class="fi" id="ap3"><b>Radicada el jueves 29 de octubre</b><small>por el Ministerio de Hacienda. Empieza en las comisiones económicas.</small></div>''')

P += clip('p-q', *CORTES['q'], 11, '''
  <div class="pk">Según el Gobierno · para qué es</div>
  <div class="tres">
    <div class="bx" id="q1"><b>1 de 3</b><small>pesos de impuestos se va a pagar deuda</small></div>
    <div class="bx" id="q2"><b>4,7 %</b><small>del PIB de ajuste al año en 2030</small></div>
    <div class="bx" id="q3"><b>2028</b><small>arranca el grueso del IVA</small></div></div>
  <div class="aviso" id="q4"><b>Es un proyecto.</b> Nada de esto es ley: el Congreso puede cambiarlo entero.</div>''')

barras = ''
for i, y in enumerate(['2027', '2028', '2029', '2030']):
    w = lambda v: 640 * v / maxt
    barras += (f'<div class="fila"><span class="yr">{y}</span><div class="seg"><i class="s-rec" id="rec{i}" style="width:{w(REC[i]):.0f}px"></i>'
               f'<i class="s-tra" id="tra{i}" style="width:{w(TRA[i]):.0f}px"></i><i class="s-imp" id="imp{i}" style="width:{w(IMP[i]):.0f}px"></i></div>'
               f'<span class="pct" id="pct{i}">{REC[i] / (REC[i] + TRA[i] + IMP[i]) * 100:.0f} %</span></div>')
P += clip('p-r', *CORTES['r'], 12, f'''
  <div class="pk">De dónde sale la plata · Tabla 14 del proyecto</div>
  <div class="ph" id="rph">«7 de cada 10 pesos son recorte»</div>
  <div class="stk" id="stk">{barras}</div>
  <div class="ley2" id="rley"><span><i style="background:{AZUL}"></i>Recorte de gasto del Estado</span><span><i style="background:{VERDE}"></i>Empresas y trabajadores vuelven a pagar aportes</span><span><i style="background:{NARANJA}"></i>Impuestos: IVA, renta, licores, tabaco</span></div>
  <div class="aviso" id="r4"><b>El recorte real es 1 de cada 4.</b> El Gobierno suma como «recorte» los aportes que vuelven a pagar empresas y trabajadores.</div>''')

P += clip('p-g', *CORTES['g'], 13, f'''
  <div class="pk">Quién gana y quién pierde · según el Gobierno</div>
  <div class="dos">
    <div class="gc" id="g1" style="border-top-color:{NARANJA}"><div class="gk" style="color:{NARANJA}">El 10 % de mayores ingresos</div><div class="gb">−$500.000</div><div class="gs">al mes por hogar · 3,6 % de su ingreso</div>
      <div class="gn" id="g1b">Hogar promedio de <b>$13,9 M</b> al mes. Renta desde <b>$5,5 M</b> por persona.</div></div>
    <div class="gc" id="g2" style="border-top-color:{AZUL}"><div class="gk" style="color:{AZUL}">El 68 % de menores ingresos</div><div class="gb">+$65.000</div><div class="gs">al mes por persona · 4,7 % más</div>
      <div class="gn" id="g2b">Hogar promedio de <b>$1,4 M</b>. Por la devolución del IVA, desde 2028.</div></div></div>
  <div class="gm" id="g3"><b>El 22 % del medio</b> · hogares de ~$2 M a ~$5 M: sin devolución, con IVA al mercado y salud más cara.</div>
  <div class="nota2">$13,9 M y $1,4 M: cálculo propio ($500.000 ÷ 3,6 % · $65.000 ÷ 4,7 %), con las cifras de la p. 3.</div>''')

P += clip('p-iva', *CORTES['iva'], 14, f'''
  <div class="pk">IVA del 19 % desde el 1 de enero de 2028</div>
  <div class="dos">
    <div class="col" id="iv1"><div class="ch"><i style="background:{NARANJA}"></i>Hoy sin IVA → 19 %</div>
      <div class="li">Tomate, cebolla, lechuga, zanahoria</div><div class="li">Frutas: banano, mango, cítricos…</div><div class="li">Fríjol, lenteja, garbanzo</div><div class="li">Sal, miel, maíz, café en grano</div><div class="li">Queso fresco</div></div>
    <div class="col" id="iv2"><div class="ch"><i style="background:{AZUL}"></i>Sigue sin IVA</div>
      <div class="li">Arroz, papa, yuca</div><div class="li">Pan, arepa, panela</div><div class="li">Carne, pollo, pescado</div><div class="li">Leche y huevos</div><div class="li">Medicamentos, servicios públicos</div></div></div>
  <div class="aviso" id="iv3"><b>Contradicción:</b> la exposición (p. 92) dice que no se gravan la sal ni los granos. El artículo 42 no los trae.</div>''')

ef = ''.join(f'<div class="fila"><span class="yr2">{n}</span><div class="seg"><i class="s-ef" id="ef{i}" style="width:{530 * v / 100:.0f}px"></i></div><span class="pct">{v} %</span></div>'
             for i, (n, v) in enumerate([('Pobreza · deciles 1-3', 100), ('Vulnerable · decil 4', 50), ('Vulnerable · decil 5', 40), ('Vulnerable · decil 6', 30)]))
P += clip('p-ef', *CORTES['ef'], 15, f'''
  <div class="pk">EfectIVA · la compensación · art. 38</div>
  <div class="ph">Le devuelven el IVA a 35 millones de personas</div>
  <div class="stk" id="efstk">{ef}</div>
  <div class="dosb" style="margin-top:22px"><div class="bx" id="ef5"><b>$288.000</b><small>tope al mes por persona (5,5 UVT)</small></div><div class="bx" id="ef6"><b>Desde 2028</b><small>el mismo día que sube el IVA</small></div></div>
  <div class="aviso" id="ef7"><b>Solo con factura electrónica</b> a nombre de la persona. En la tienda sin factura, no hay devolución.</div>''')

P += clip('p-rel', *CORTES['rel'], 16, f'''
  <div class="pk">El reloj</div>
  <div class="ph">Si el 16 de diciembre no está aprobada, se archiva</div>
  <div class="linea">
    <div class="paso" id="rl1"><i style="background:{AZUL}"></i><b>Noviembre</b><small>comisiones terceras, Cámara y Senado</small></div>
    <div class="paso" id="rl2"><i style="background:{VERDE}"></i><b>Diciembre</b><small>plenarias</small></div>
    <div class="paso" id="rl3"><i style="background:{NARANJA}"></i><b>16 de diciembre</b><small>cierran las sesiones ordinarias</small></div></div>
  <div class="nota2" id="rl4">Calendario según el presidente de la Comisión Tercera de Cámara a El Tiempo. El mensaje de urgencia no está confirmado.</div>''')

SEN = [(1, AZUL), (3, VERDE), (6, GRIS), (3, NARANJA)]
CAM = [(7, VERDE), (18, GRIS), (6, NARANJA)]


def waf(grupos, mayoria, pref, lado=52, gap=6):
    out, k = '', 0
    for n, c in grupos:
        for _ in range(n):
            out += f'<i class="sq {pref}" id="{pref}{k}" style="left:{k * (lado + gap)}px;width:{lado}px;background:{c}"></i>'
            k += 1
    x = mayoria * (lado + gap) - gap / 2 - 2
    return f'<div class="waf" style="width:{k * (lado + gap)}px"><div class="mk" id="{pref}mk" style="left:{x:.0f}px"><span>{mayoria}</span></div>{out}</div>'


P += clip('p-fi', *CORTES['fi'], 17, f'''
  <div class="pk">Quién la vota primero · comisiones terceras</div>
  <div class="wt" id="fis">Senado · 7 de 13</div>{waf(SEN, 7, 'sn', 60, 8)}
  <div class="wt" id="fic">Cámara · 16 de 31</div>{waf(CAM, 16, 'cm', 24, 5)}
  <div class="ley" id="fil">
    <span><i style="background:{AZUL}"></i>Apoya · Salvación Nacional</span><span><i style="background:{VERDE}"></i>Con reparos · Centro Democrático, Verde</span>
    <span><i style="background:{GRIS}"></i>Sin postura · liberales, conservadores, La U, Cambio Radical</span><span><i style="background:{NARANJA}"></i>En contra · Pacto Histórico</span></div>
  <div class="aviso" id="fip"><b>Precedente:</b> el 11 de diciembre de 2024 estas comisiones hundieron la tributaria de Petro (Tercera del Senado 8-6, Cuarta de Cámara 16-10).</div>
  <div class="nota2">Color = lo dicho en público entre el 29 y el 30 de octubre. No hay voto nominal todavía.</div>''')

P += clip('p-fe', *CORTES['fe'], 18, f'''
  <div class="pk">Fuera del Congreso · quién empuja y quién frena</div>
  <div class="tresc">
    <div class="col" id="fe1"><div class="ch"><i style="background:{AZUL}"></i>Empujan</div><div class="li">Gobierno De la Espriella</div><div class="li">Mauricio Cárdenas<small>exministro de Hacienda</small></div><div class="li">Luis Fernando Mejía<small>exdirector de Fedesarrollo</small></div><div class="li">Gremios petroleros (ACP)</div></div>
    <div class="col" id="fe2"><div class="ch"><i style="background:{NARANJA}"></i>Frenan</div><div class="li">María Clara Posada<small>Centro Democrático</small></div><div class="li">Gabriel Vallejo<small>director del CD</small></div><div class="li">Pacto Histórico<small>Gabriel Becerra</small></div><div class="li">Catherine Juvinao<small>Verde · Comisión Tercera</small></div></div>
    <div class="col" id="fe3"><div class="ch"><i style="background:{GRIS}"></i>Callados</div><div class="li">ANDI</div><div class="li">Fenalco</div><div class="li">Asobancaria</div><div class="li">Fedesarrollo</div></div></div>
  <div class="nota2">Posturas con cita en prensa (El Tiempo · Semana · Vanguardia · Infobae · La FM, 29-30 oct). Quien no ha hablado va como «callado».</div>''')

P += clip('p-ci', *CORTES['ci'], 19, f'''
  <div class="pk">Segunda parte</div>
  <div class="ph">¿Y a usted cómo le pega?</div>
  <div class="fi" id="ci1" style="border-left:6px solid {NARANJA}"><b>Si gana más de $3,5 millones</b><small>cuánto más le descontarían cada mes, perfil por perfil</small></div>
  <div class="fi" id="ci2" style="border-left:6px solid {AZUL}"><b>Y la calculadora</b><small>ricardoruiz.co/ley-de-rescate</small></div>''')

# ── Caras: entran sobre la cámara cuando se nombra a alguien ───────────────────────────────────
CARAS = [('restrepo', 'José Manuel Restrepo', 'Vicepresidente · «7 de cada 10 pesos son recorte del Estado»', T['vp'] - 0.1, 2.4),
         ('cardenas', 'Mauricio Cárdenas', 'Exministro de Hacienda · «era algo absolutamente necesario»', T['card'] - 0.1, 2.4),
         ('posada', 'María Clara Posada', 'Centro Democrático · «no cuenten conmigo para subirle impuestos a la clase media»', T['pos'] - 0.1, 2.5),
         ('juvinao', 'Catherine Juvinao', 'Alianza Verde · Comisión Tercera · «una medida excesivamente dura»', T['juv'] - 0.05, 2.4)]
caras = ''
for k_, (f, n, r, ini, d) in enumerate(CARAS):
    caras += clip(f'cara-{f}', ini, ini + d, 40 + k_, f'''
  <div class="cw"><img src="assets/caras/{f}.jpg" alt=""><div class="cn">{e(n)}</div><div class="cr">{e(r)}</div></div>''', 'cara')

cortes_barrido = [CORTES[k][0] for k in ('q', 'r', 'g', 'iva', 'ef', 'rel', 'fi', 'fe', 'ci')]
barridos = ''.join(clip(f'bw{i}', t - 0.25, t + 0.35, 30 + i, '', 'barrido') for i, t in enumerate(cortes_barrido))

CSS = """
@font-face { font-family: "HN"; src: url("fonts/helveticaneue-light.woff2") format("woff2"); font-weight: 300; font-display: block; }
@font-face { font-family: "HN"; src: url("fonts/helveticaneue.woff2") format("woff2"); font-weight: 400; font-display: block; }
@font-face { font-family: "HN"; src: url("fonts/helveticaneue-medium.woff2") format("woff2"); font-weight: 500; font-display: block; }
@font-face { font-family: "HN"; src: url("fonts/helveticaneue-bold.woff2") format("woff2"); font-weight: 700; font-display: block; }
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: 1080px; height: 1920px; overflow: hidden; background: #060810; }
body { font-family: "HN"; color: #f4f3ef; -webkit-font-smoothing: antialiased; }
#fondo { position: absolute; inset: 0; background:
  radial-gradient(900px 700px at 85% 75%, rgba(61,111,255,.16), transparent 60%),
  radial-gradient(700px 600px at 0% 100%, rgba(249,115,22,.08), transparent 60%), #060810; }
#cam { position: absolute; left: 0; top: 0; width: 1080px; height: 980px; overflow: hidden; }
#base { position: absolute; left: 0; top: 0; width: 1080px; height: 980px; object-fit: cover;
  object-position: 50% 30%; transform-origin: 50% 32%; }
#vig { position: absolute; left: 0; top: 0; width: 1080px; height: 980px; background:
  linear-gradient(180deg, rgba(6,8,16,.70) 0%, rgba(6,8,16,0) 20%, rgba(6,8,16,0) 66%, rgba(6,8,16,.92) 100%); }
#kick { position: absolute; left: 70px; top: 150px; background: rgba(6,8,16,.82); padding: 12px 20px; border-radius: 10px; display: flex; gap: 14px; align-items: center;
  font-size: 26px; font-weight: 700; letter-spacing: .2em; text-transform: uppercase; }
#kick i { width: 14px; height: 14px; border-radius: 50%; background: #f97316; display: block; }
#kick span { color: #f4f3ef; font-weight: 500; }
.cap { position: absolute; left: 60px; right: 60px; top: 800px; text-align: center; }
.capt { display: inline-block; font-size: 54px; font-weight: 700; letter-spacing: -.015em; line-height: 1.12;
  background: rgba(6,8,16,.86); border-radius: 14px; padding: 12px 24px; }
.panel { position: absolute; left: 80px; top: 1020px; width: 920px; height: 600px; }
.pk { font-size: 24px; font-weight: 700; letter-spacing: .18em; text-transform: uppercase; color: #f97316; }
.ph { font-size: 46px; font-weight: 700; letter-spacing: -.025em; line-height: 1.06; margin-top: 14px; }
.dos { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 18px; }
.tres { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-top: 20px; }
.tresc { display: grid; grid-template-columns: 1fr 1.15fr 1fr; gap: 22px; margin-top: 16px; }
.dosb { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }
.bx { background: rgba(13,17,32,.9); border: 1px solid #1c2233; border-radius: 12px; padding: 18px 22px; }
.bx b { display: block; font-size: 68px; font-weight: 700; letter-spacing: -.04em; line-height: 1; }
.bx small { display: block; font-size: 24px; color: #9aa0b1; margin-top: 8px; line-height: 1.25; }
.fi { margin-top: 18px; background: rgba(13,17,32,.9); border: 1px solid #1c2233; border-radius: 12px; padding: 16px 22px; }
.fi b { display: block; font-size: 31px; } .fi small { display: block; font-size: 24px; color: #9aa0b1; margin-top: 4px; line-height: 1.3; }
.aviso { font-size: 25px; color: #c8ccd6; border-left: 4px solid #f97316; padding-left: 16px; margin-top: 24px; line-height: 1.32; }
.aviso b { color: #f4f3ef; }
.nota2 { margin-top: 16px; font-size: 20px; color: #7d8396; line-height: 1.3; }
.stk { margin-top: 22px; display: grid; gap: 12px; }
.fila { display: flex; align-items: center; gap: 14px; }
.yr { width: 70px; font-size: 26px; font-weight: 700; } .yr2 { width: 250px; font-size: 23px; color: #c8ccd6; }
.seg { display: flex; gap: 3px; height: 40px; flex: 1; }
.seg i { display: block; height: 100%; border-radius: 5px; transform-origin: 0 50%; }
.s-rec { background: #3987e5; } .s-tra { background: #199e70; } .s-imp { background: #d95926; } .s-ef { background: #3987e5; }
.pct { width: 96px; text-align: right; font-size: 24px; font-weight: 700; color: #f4f3ef; white-space: nowrap; }
.ley2 { display: grid; gap: 8px; font-size: 22px; color: #c8ccd6; margin-top: 16px; }
.ley2 i, .ley i { display: inline-block; width: 20px; height: 20px; border-radius: 5px; margin-right: 12px; vertical-align: -3px; }
.gc { background: rgba(13,17,32,.9); border: 1px solid #1c2233; border-top: 6px solid; border-radius: 12px; padding: 16px 20px; }
.gk { font-size: 20px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
.gb { font-size: 62px; font-weight: 700; letter-spacing: -.04em; line-height: 1; margin-top: 10px; }
.gs { font-size: 21px; color: #9aa0b1; margin-top: 6px; line-height: 1.25; }
.gn { font-size: 23px; line-height: 1.25; margin-top: 12px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,.1); }
.gm { margin-top: 16px; background: rgba(13,17,32,.9); border: 1px solid #1c2233; border-left: 6px solid #5b6275; border-radius: 12px; padding: 14px 20px; font-size: 24px; line-height: 1.3; }
.ch { font-size: 21px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; margin-bottom: 10px; }
.ch i { display: inline-block; width: 16px; height: 16px; border-radius: 4px; margin-right: 10px; vertical-align: -1px; }
.li { font-size: 24px; line-height: 1.25; padding: 7px 0; border-bottom: 1px solid #1c2233; color: #e4e6ec; }
.li small { display: block; color: #7d8396; font-size: 19px; }
.linea { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 18px; margin-top: 28px; }
.paso { background: rgba(13,17,32,.9); border: 1px solid #1c2233; border-radius: 12px; padding: 16px 18px; }
.paso i { display: block; width: 100%; height: 10px; border-radius: 5px; margin-bottom: 14px; }
.paso b { display: block; font-size: 30px; } .paso small { display: block; font-size: 21px; color: #9aa0b1; margin-top: 4px; line-height: 1.25; }
.wt { font-size: 26px; font-weight: 700; margin-top: 18px; }
.waf { position: relative; margin-top: 30px; height: 44px; }
.sq { position: absolute; top: 0; height: 44px; border-radius: 5px; }
.mk { position: absolute; top: -18px; height: 80px; width: 4px; background: #f4f3ef; }
.mk span { position: absolute; top: -30px; left: -12px; font-size: 24px; font-weight: 700; }
.ley { margin-top: 20px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; font-size: 20px; color: #c8ccd6; }
.barrido { position: absolute; left: 0; top: 980px; width: 1080px; height: 8px; background: #f97316; transform-origin: 0 50%; }
.cara { position: absolute; left: 0; top: 0; width: 1080px; height: 980px; }
.cw { position: absolute; inset: 0; background: #060810; display: flex; flex-direction: column; align-items: center; padding-top: 236px; }
.cara img { width: 400px; height: 400px; border-radius: 50%; object-fit: cover; border: 6px solid #f97316; }
.cn { margin-top: 24px; font-size: 52px; font-weight: 700; letter-spacing: -.02em; }
.cr { margin-top: 10px; font-size: 27px; color: #b9bdc9; max-width: 900px; text-align: center; line-height: 1.25; }
#fin { position: absolute; inset: 0; background: #060810; display: flex; flex-direction: column;
  align-items: center; justify-content: center; text-align: center; gap: 26px; opacity: 0; }
#fin .logo { display: flex; align-items: flex-end; gap: 6px; height: 60px; }
#fin .logo i { display: block; width: 14px; background: #0047FF; border-radius: 2px; }
#fin .t1 { font-size: 58px; font-weight: 700; letter-spacing: -.02em; }
#fin .t2 { font-size: 34px; color: #b9bdc9; }
#fin .t3 { font-size: 36px; font-weight: 700; color: #3d6fff; }
"""

J = lambda v: f'{v:.2f}'
JS = f"""
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
{''.join(f'tl.set("#base", {{scale: {1.12 if i % 2 else 1}}}, {J(t)});' for i, t in enumerate([0] + cortes_barrido))}
tl.from("#kick", {{opacity: 0, x: -24, duration: .5}}, .1);
// apertura
tl.from("#ap1", {{opacity: 0, y: 24, duration: .4}}, {J(W[14] - 0.1)})
  .from("#ap2", {{opacity: 0, y: 24, duration: .4}}, {J(W[18] - 0.1)})
  .from("#ap3", {{opacity: 0, x: -24, duration: .4}}, {J(W[22])});
// barridos entre bloques
{json.dumps([round(t, 2) for t in cortes_barrido])}.forEach((t,i) => {{
  tl.fromTo("#bw"+i, {{scaleX: 0}}, {{scaleX: 1, duration: .3, ease: "power2.in"}}, t-.25)
    .to("#bw"+i, {{opacity: 0, duration: .25}}, t+.08);
}});
// entradas y salidas de paneles
{json.dumps([[f'#p-{k}', round(a, 2), round(b, 2)] for k, (a, b) in CORTES.items()])}.forEach(([s,a,b]) => {{
  if (a > 0) tl.from(s, {{opacity: 0, y: 60, duration: .45, ease: "power3.out"}}, a);
  if (b < {BASE_DUR - 0.5}) tl.to(s, {{opacity: 0, y: -30, duration: .28, ease: "power2.in"}}, b - .28);
}});
// para qué es
tl.from("#q1", {{opacity: 0, y: 24, duration: .4}}, {J(T['tres'])})
  .from("#q2", {{opacity: 0, y: 24, duration: .4}}, {J(T['pib'])})
  .from("#q3", {{opacity: 0, y: 24, duration: .4}}, {J(T['pib'] + 1.6)})
  .from("#q4", {{opacity: 0, x: -20, duration: .4}}, {J(T['proy'])});
// recorte vs impuestos
tl.from(".s-rec,.s-tra,.s-imp", {{scaleX: 0, duration: .5, ease: "power3.out", stagger: .05}}, {J(T['tabla'])})
  .from(".pct", {{opacity: 0, duration: .3}}, {J(T['cuatro'] - 0.2)})
  .to(".s-tra,.s-imp", {{opacity: .45, duration: .3}}, {J(T['cuatro'])})
  .to(".s-tra,.s-imp", {{opacity: 1, duration: .3}}, {J(T['resto'])})
  .from("#rley", {{opacity: 0, duration: .3}}, {J(T['resto'])})
  .from("#r4", {{opacity: 0, x: -20, duration: .4}}, {J(T['cuatro'] + 0.4)});
// quién gana y quién pierde
tl.from("#g1", {{opacity: 0, x: -30, duration: .4}}, {J(W[131])})
  .from("#g1b", {{opacity: 0, duration: .35}}, {J(T['catorce'] - 0.2)})
  .from("#g2", {{opacity: 0, x: 30, duration: .4}}, {J(T['pobre'])})
  .from("#g2b", {{opacity: 0, duration: .35}}, {J(T['sesenta5'])})
  .from("#g3", {{opacity: 0, y: 20, duration: .4}}, {J(T['medio'])});
// IVA
tl.from("#iv1 .li", {{opacity: 0, x: -20, duration: .3, stagger: .25}}, {J(T['tomate'])})
  .from("#iv2 .li", {{opacity: 0, x: 20, duration: .3, stagger: .18}}, {J(T['nocambia'])})
  .from("#iv3", {{opacity: 0, x: -20, duration: .4}}, {J(T['contra'])});
// EfectIVA
tl.from(".s-ef", {{scaleX: 0, duration: .5, ease: "power3.out", stagger: .12}}, {J(T['cien'] - 0.2)})
  .from("#ef5", {{opacity: 0, y: 20, duration: .4}}, {J(T['tope'])})
  .from("#ef6", {{opacity: 0, y: 20, duration: .4}}, {J(T['tope'] + 0.4)})
  .from("#ef7", {{opacity: 0, x: -20, duration: .4}}, {J(T['factura'])});
// reloj
tl.from("#rl1", {{opacity: 0, y: 20, duration: .35}}, {J(T['nov'] - 0.2)})
  .from("#rl2", {{opacity: 0, y: 20, duration: .35}}, {J(T['dic'] - 0.1)})
  .from("#rl3", {{opacity: 0, y: 20, duration: .35}}, {J(T['dieciseis'] - 0.1)})
  .fromTo("#rl3", {{scale: 1}}, {{scale: 1.04, duration: .2, yoyo: true, repeat: 1}}, {J(T['archiva'])})
  .from("#rl4", {{opacity: 0, duration: .3}}, {J(T['archiva'] + 0.5)});
// fuerzas internas
tl.set(".sn,.cm", {{opacity: .16}}, {J(CORTES['fi'][0])})
  .from("#fis", {{opacity: 0, duration: .3}}, {J(T['sen'] - 0.2)})
  .from("#snmk", {{opacity: 0, scaleY: 0, duration: .3}}, {J(W[391] - 0.1)})
  .from("#fic", {{opacity: 0, duration: .3}}, {J(T['cam'] - 0.1)})
  .from("#cmmk", {{opacity: 0, scaleY: 0, duration: .3}}, {J(W[399] - 0.1)})
  .to("#sn10,#sn11,#sn12,#cm25,#cm26,#cm27,#cm28,#cm29,#cm30", {{opacity: 1, duration: .3, stagger: .04}}, {J(T['pacto'])})
  .to("#sn1,#sn2,#sn3,#cm0,#cm1,#cm2,#cm3,#cm4,#cm5,#cm6,#sn0", {{opacity: 1, duration: .3, stagger: .04}}, {J(T['cd'])})
  .to(".sn,.cm", {{opacity: 1, duration: .4}}, {J(T['bis'])})
  .fromTo("#sn4,#sn5,#sn6,#sn7,#sn8,#sn9,#cm7,#cm8,#cm9,#cm10,#cm11,#cm12,#cm13,#cm14,#cm15,#cm16,#cm17,#cm18,#cm19,#cm20,#cm21,#cm22,#cm23,#cm24", {{y: 0}}, {{y: -8, duration: .2, yoyo: true, repeat: 3}}, {J(T['bis'] + 0.3)})
  .from("#fil", {{opacity: 0, duration: .35}}, {J(T['bis'])})
  .from("#fip", {{opacity: 0, x: -20, duration: .4}}, {J(T['prec'])});
// fuerzas externas
tl.from("#fe1 .li", {{opacity: 0, x: -20, duration: .3, stagger: .2}}, {J(T['emp'])})
  .from("#fe2 .li", {{opacity: 0, x: -20, duration: .3, stagger: .2}}, {J(T['fren'])})
  .from("#fe3 .li", {{opacity: 0, x: -20, duration: .3, stagger: .2}}, {J(T['call'])});
// cierre
tl.from("#ci1", {{opacity: 0, x: -24, duration: .4}}, {J(W[499])})
  .from("#ci2", {{opacity: 0, x: -24, duration: .4}}, {J(W[508])});
// caras: entran con un círculo que se abre y salen con un fundido
{json.dumps([[f'#cara-{f}', round(ini, 2), round(d, 2)] for f, _, _, ini, d in CARAS])}.forEach(([s,a,d]) => {{
  tl.fromTo(s + " .cw", {{clipPath: "circle(0% at 50% 44%)"}}, {{clipPath: "circle(120% at 50% 44%)", duration: .5, ease: "power2.out"}}, a)
    .from(s + " img", {{scale: .85, duration: .6, ease: "power3.out"}}, a)
    .from(s + " .cn", {{opacity: 0, y: 20, duration: .35}}, a + .25)
    .from(s + " .cr", {{opacity: 0, y: 14, duration: .35}}, a + .4)
    .to(s + " .cw", {{opacity: 0, duration: .3}}, a + d - .4).set(s + " .cw", {{opacity: 0}}, a + d - .05);
}});
tl.to("#fin", {{opacity: 1, duration: .35}}, {BASE_DUR});
{chr(10).join(cap_js)}
window.__timelines["main"] = tl;
"""

pagina = f"""<!doctype html>
<html lang="es" data-resolution="portrait">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1080, height=1920" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>{CSS}</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{TOTAL}" data-width="1080" data-height="1920">
<div id="fondo" class="clip" data-start="0" data-duration="{TOTAL}" data-track-index="0"></div>
<div id="cam"><video id="base" class="clip" src="assets/base.mp4" data-start="0" data-duration="{BASE_DUR}" data-track-index="1" data-volume="1" data-has-audio="true"></video></div>
<div id="vig" class="clip" data-start="0" data-duration="{BASE_DUR}" data-track-index="2"></div>
{P}{barridos}{caras}<div id="kick" class="clip" data-start="0" data-duration="{BASE_DUR}" data-track-index="3"><i></i>Ley de Rescate <span>· 1 · ¿quién paga?</span></div>
{caps}
<div id="fin" class="clip" data-start="{BASE_DUR}" data-duration="{FIN}" data-track-index="70">
  <div class="logo"><i style="height:60px"></i><i style="height:45px"></i><i style="height:27px"></i><i style="height:12px"></i></div>
  <div class="t1">Ricardo.Ruiz</div>
  <div class="t2">¿Cómo le pega a usted? Calcúlelo:</div>
  <div class="t3">ricardoruiz.co/ley-de-rescate</div>
</div>
</div>
<script>{JS}</script>
</body>
</html>
"""
(AQUI / 'index.html').write_text(pagina, encoding='utf-8')
print('✓ index.html ·', len(trozos), 'subtítulos ·', TOTAL, 's')
print({k: round(v, 2) for k, v in T.items()})
