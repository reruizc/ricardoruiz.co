#!/usr/bin/env python3
"""
El JSON del brief → el PDF, con el chasis visual de los briefs escritos a mano.

Reusa el CSS, el logo y el papel de `build_brief_binance.py`, que es lo que hace
que el documento generado se vea como el del 7 de septiembre y no como otra
cosa. Lo único que cambia frente a aquel es que el contenido viene de un JSON en
vez de estar escrito dentro del archivo.

  python3 tools/caudal/brief/render_brief.py brief.json --out Brief.pdf
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
import build_brief_binance as base                               # noqa: E402

ROOT = base.ROOT
MESES = ('enero febrero marzo abril mayo junio julio agosto septiembre '
         'octubre noviembre diciembre').split()


def e(s):
    return html.escape(str(s or ''))


def fecha_larga(f):
    try:
        a, m, d = str(f)[:10].split('-')
        return f'{int(d)} de {MESES[int(m) - 1]} de {a}'
    except Exception:                                            # noqa: BLE001
        return str(f or '')


DIAS = ('lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo')


def fecha_agenda(x):
    """La fila de la agenda, con el día de la semana CALCULADO.

    ⚠️⚠️ El día de la semana NO lo escribe el modelo. Pasó y llegó al PDF: el
    brief del 14 de septiembre decía «Lunes 15» y «Martes 16» cuando el 15 era
    martes y el 16 miércoles — el patrón venía copiado del brief de la semana
    anterior, donde sí calzaba. Es el error más barato de cometer y el más caro
    de que lo vea un cliente: si el día de la semana está mal, toda fecha del
    documento queda bajo sospecha. Con `iso` en la evidencia, el día se deriva
    aquí y es imposible equivocarlo; sin `iso` se publica el texto tal cual,
    porque inventar una fecha sería peor.
    """
    iso = (x.get('iso') or '').strip()
    txt = (x.get('cuando') or '').strip()
    if not iso:
        return txt
    try:
        import datetime
        d = datetime.date.fromisoformat(iso[:10])
    except Exception:                                            # noqa: BLE001
        return txt
    dia = DIAS[d.weekday()]
    larga = f'{dia.capitalize()} {d.day} de {MESES[d.month - 1]}'
    # si el texto del modelo trae un rango o una aclaración, se conserva
    if txt and not re.match(r'^\s*(?:' + '|'.join(DIAS) + r')\b', txt, re.I):
        return f'{larga} · {txt}' if len(txt) < 40 else larga
    return larga


def fecha_corta(f):
    """«11 de septiembre», sin el año: lo lleva la fecha de cierre al lado."""
    try:
        _, m, d = str(f)[:10].split('-')
        return f'{int(d)} de {MESES[int(m) - 1]}'
    except Exception:                                            # noqa: BLE001
        return str(f or '')


def hora_legible(h):
    """«08:50» → «8:50 a. m.», que es como se escribe en el documento."""
    try:
        hh, mm = str(h).split(':')[:2]
        hh = int(hh)
        suf = 'a. m.' if hh < 12 else 'p. m.'
        h12 = hh if 1 <= hh <= 12 else (hh - 12 if hh > 12 else 12)
        return f'{h12}:{mm} {suf}'
    except Exception:                                            # noqa: BLE001
        return str(h)


def construir_html(b):
    meta = b.get('_meta') or {}
    v = meta.get('ventana') or {}
    cliente = meta.get('cliente') or 'Cliente'
    horas = (v.get('dias_prensa') or 3) * 24
    corte = v.get('corte')
    # ⚠️ El alcance no es siempre «Colombia»: un cliente regional lee el mismo
    # documento y decir Colombia a secas le sugiere que eso es todo lo que se
    # miró. Sale de la ficha, y lo que está fuera de cobertura va declarado en
    # «qué no se movió», no escondido en el pie.
    fuera = (meta.get('fuera_de_alcance') or [])
    alcance = 'Colombia y región' if fuera else 'Colombia'
    # La banda del hero va a UNA línea: con dos, el salto cae en mitad del
    # alcance («… · COLOMBIA / Y REGIÓN») y se lee como si el documento se
    # hubiera cortado. Se escriben los meses en corto y sin repetir el año.
    ventana_txt = (f"{fecha_corta(v.get('desde'))} – {fecha_larga(v.get('hasta'))}"
                   f" · últimas {horas} horas"
                   + (f" · corte {hora_legible(corte)}" if corte else '')
                   + f" · {alcance}")

    top = f"""
<div class="top">
  <img src="file://{base.LOGO}" alt="Caudal">
  <div class="meta">Brief de asuntos públicos · {e(cliente)}<br>
  {e(fecha_larga(v.get('hasta')))}</div>
</div>"""

    L = [f'<html><head><meta charset="utf-8"><style>{base.CSS}',
         # tres clases propias, mismas que usaba el brief escrito a mano
         '.item.med { border-left-color:#8a6d1c; background:#fbf9f2; '
         'border-color:#eadfbf; }',
         '.item.med .porque .et { color:#8a6d1c; }',
         '.area { font-size:7.2pt; letter-spacing:1.1px; text-transform:uppercase; '
         'color:#8a6d1c; font-weight:700; }',
         'table.ag td:first-child { white-space:nowrap; color:#0b0d11; '
         'font-weight:700; width:26%; }',
         '</style></head><body>', top]

    # hero
    tit = e(b.get('titular', ''))
    L.append(f"""
<div class="hero">
  <h1>{tit}</h1>
  <p class="lead">{e(b.get('bajada', ''))}</p>
  <div class="window">{e(ventana_txt)}</div>
</div>""")

    # lectura de la ventana
    lec = b.get('lectura') or {}
    parr = ''.join(f'<p>{e(x)}</p>' for x in (lec.get('parrafos') or []))
    L.append(f"""
<div class="item resumen">
  <div class="num">Lectura de estas {horas} horas</div>
  <h2>{e(lec.get('titulo', ''))}</h2>
  {parr}
  <div class="porque"><span class="et">Si solo hay tiempo para una cosa</span>
  {e(lec.get('si_solo_hay_tiempo', ''))}</div>
</div>""")

    # temas
    for i, t in enumerate(b.get('temas') or [], 1):
        # la urgencia decide el color del bloque, igual que en el brief manual
        cls = 'item urg' if t.get('urgencia') == 'alta' else 'item med'
        # ⚠️ El encabezado del brief manual es «NN · TEMA · ÁREA», tres partes.
        # Si el rótulo ya nombra la línea, repetirla da «06 · Landing LATAM ·
        # inversión · LANDING LATAM», que es lo que salió la primera vez.
        rot = (t.get('rotulo') or '').strip()
        lin = (t.get('linea') or '').strip()
        repetida = lin and lin.lower() in rot.lower()
        area = (f' · <span class="area">{e(lin)}</span>'
                if lin and not repetida else '')
        parr = ''.join(f'<p>{e(x)}</p>' for x in (t.get('parrafos') or []))
        L.append(f"""
<div class="{cls}">
  <div class="num">{i:02d} · {e(rot)}{area}</div>
  <h2>{e(t.get('titulo', ''))}</h2>
  {parr}
  <div class="porque"><span class="et">Por qué le importa a {e(cliente)}</span>
  {e(t.get('por_que', ''))}</div>
  <div class="porque"><span class="et">Qué hacer con esto</span>
  {e(t.get('que_hacer', ''))}</div>
</div>""")

    # agenda
    if b.get('agenda'):
        # Ordenada por fecha: una agenda desordenada obliga al lector a
        # reconstruir el calendario, que es justo el trabajo que le quita.
        # Lo que no trae fecha (un rango, «esta semana») va al final.
        ag = sorted(b['agenda'],
                    key=lambda x: (x.get('iso') or '9999-12-31', x.get('cuando') or ''))
        filas = ''.join(f'<tr><td>{e(fecha_agenda(x))}</td>'
                        f'<td class="q">{e(x.get("que"))}</td></tr>'
                        for x in ag)
        L.append(f'<h3 class="sec">Agenda de lo que viene</h3>'
                 f'<table class="ag">{filas}</table>')

    # qué no se movió
    if b.get('no_se_movio'):
        filas = ''.join(f'<tr><td>{e(x.get("fuente"))}</td>'
                        f'<td class="q">{e(x.get("estado"))}</td></tr>'
                        for x in b['no_se_movio'])
        L.append('<h3 class="sec">Qué no se movió — verificado, no asumido</h3>'
                 f'<table><tr><th style="width:26%">Fuente</th>'
                 f'<th>En la ventana</th></tr>{filas}</table>')

    modelo = meta.get('modelo', '')
    L.append(f"""
<div class="foot">
  <b>Fuentes.</b> Registro de proyectos de ley del Senado y la Cámara y órdenes
  del día de sus comisiones; normativa de Presidencia; consulta pública de
  proyectos de norma (SUCOP); registro regulatorio de las superintendencias y la
  ANLA; contratación del Estado (SECOP); prensa nacional y regional. Cada
  afirmación es verificable contra el acto o la nota que la respalda, y la
  sección «qué no se movió» dice hasta qué fecha llega cada registro.<br>
  <b>Ventana.</b> {e(ventana_txt)}<br>
  <b>Cómo se produjo.</b> Barrido automático de los pilares de Caudal sobre la
  ficha de {e(cliente)}, redacción asistida por modelo{f' ({e(modelo)})' if modelo else ''}
  y revisión humana antes de enviar.<br>
  <b>Alcance.</b> Insumo de monitoreo; no constituye asesoría legal.<br>
  Caudal · módulo de inteligencia regulatoria de Cauce.
</div>
</body></html>""")
    return '\n'.join(L)


def render(doc, out):
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    try:
        from weasyprint import HTML
        HTML(string=doc, base_url=ROOT).write_pdf(out)
        return 'weasyprint'
    except ImportError:
        pass
    tmp = out[:-4] + '.html'
    open(tmp, 'w', encoding='utf-8').write(doc)
    chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    subprocess.run([chrome, '--headless=new', '--disable-gpu',
                    '--no-pdf-header-footer', '--print-to-pdf=' + out,
                    'file://' + tmp], check=True, capture_output=True, timeout=180)
    os.remove(tmp)
    return 'chrome'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('json', help='el brief en JSON')
    ap.add_argument('--out', help='ruta del PDF')
    a = ap.parse_args()
    b = json.load(open(a.json, encoding='utf-8'))
    meta = b.get('_meta') or {}
    out = a.out or os.path.join(
        ROOT, 'caudalxcauce', (meta.get('cliente') or 'Cliente'),
        f"Brief-{(meta.get('cliente') or 'Cliente')}-"
        f"{(meta.get('ventana') or {}).get('hasta', '')}.pdf")
    motor = render(construir_html(b), out)
    print(f'OK ({motor}) · {out} · {os.path.getsize(out) / 1024:.0f} KB')


if __name__ == '__main__':
    main()
