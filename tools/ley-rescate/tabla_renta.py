#!/usr/bin/env python3
"""Media página (carta apaisada) con el comparativo de posiciones sobre la renta a personas naturales.

Uso: /opt/homebrew/bin/python3.14 tools/ley-rescate/tabla_renta.py
Salida: Bases de datos/ley-rescate/Renta-personas-<FECHA>.{pdf,png}
Cada cita está verificada en la nota original (ver FUENTES).
"""
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(AQUI, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'caudal', 'brief'))
import onepager as op                                            # noqa: E402

OUT_DIR = os.path.join(REPO, 'Bases de datos', 'ley-rescate')
e = op.e
FECHA = '2026-11-12'

# (actor, al radicar, hoy, cambio) · cambio: igual · endurece · gira
FILAS = [
    ('El proyecto', 'Nuevo escalón del 9 % desde unos $37,7 millones al año de renta, ya descontado lo exento. '
     'Baja el 25 % exento y el tope de deducciones (arts. 47-50).', 'Igual. Todavía no hay texto nuevo ni ponencia.', 'igual'),
    ('Gobierno', 'Gómez: «el pago efectivo empieza con ingresos de cerca de $5 millones al mes».',
     'Abre la puerta a cambios («bienvenidas sean las alternativas»), sin nada específico sobre renta.', 'gira'),
    ('Centro Democrático', 'Voces sueltas en contra. Posada: «No cuenten conmigo». Briceño: «no pienso apoyarlos».',
     'Postura de bancada. Berrío: no a ampliar quiénes declaran y pagan. S. Castro: nada que afecte «los ingresos de los sectores de clase media».', 'endurece'),
    ('Paloma Valencia', 'En contra de subir impuestos, en general.',
     '«El IVA y la renta a las personas afectan la capacidad de la clase media». Critica quitar la deducción por dependientes.', 'endurece'),
    ('Salvación Nacional', 'Castellanos: «No apoyaremos […] más cargas tributarias a la clase media».', 'Sin cambio conocido.', 'igual'),
    ('Presidente del Senado', 'Henríquez: «Los colombianos no aguantan un impuesto más».', 'Sin cambio conocido.', 'igual'),
    ('Liberal, CR, Conservador, La U', 'Según El País, no acompañan subir la renta a quien gana entre $5 y $9 millones al mes.',
     'Sus contrapropuestas se centran en el IVA a la comida y en la renta de empresas.', 'igual'),
    ('Verde y Pacto', 'En contra por otra razón. Ávila: baja impuestos «a los grandes ricos» y los sube «a los pobres y la clase media».',
     'Padilla (senadora Verde, Tercera) prioriza el IVA a alimentos y mascotas, el ambiente y el gasto. No menciona la renta.', 'igual'),
]
ETQ = {'igual': ('Igual', '#8a8f99'), 'endurece': ('Se endurece', '#b4361f'), 'gira': ('Se abre', '#c98a1c')}

FUENTES = ('Articulado del PL 477 de 2026 · El País (1-nov) · La FM (1 y 12-nov) · Infobae (31-oct, 11 y 12-nov) · '
           'Semana y La Razón (30-oct) · El Tiempo (11-nov) · El Nuevo Siglo (9-nov) · X de Andrea Padilla (5-nov).')


def construir():
    css = op.CSS + """
@page { size: 8.5in 5.5in; margin:6mm 9mm 5mm 9mm; }
body { font-size:7.6pt; line-height:1.3; }
.top { align-items:center; }
.top .nombre { font-size:13pt; font-weight:700; letter-spacing:-.3px; color:#0b0d11; line-height:1.1; }
.top .nombre small { display:block; font-size:6.9pt; font-weight:400; letter-spacing:1.4px; text-transform:uppercase; color:#5a6070; margin-top:2px; }
.hero { padding:6px 11px 5px; margin:5px 0 6px; }
h1 { font-size:13.5pt; margin-bottom:3px; }
.lead { font-size:8pt; }
table.cmp { width:100%; border-collapse:collapse; font-size:7.3pt; }
.cmp th { text-align:left; font-size:6.4pt; text-transform:uppercase; letter-spacing:1px; color:#5a6070; font-weight:700; padding:2px 6px; border-bottom:1.5px solid #15171c; }
.cmp td { padding:3px 6px; border-bottom:1px solid #eceef2; vertical-align:top; line-height:1.28; color:#2b303a; }
.cmp td:first-child { font-weight:700; color:#0b0d11; width:17%; }
.cmp td:nth-child(2) { width:36%; color:#3d434f; }
.cmp td:nth-child(4) { width:11%; text-align:right; }
.ch { display:inline-block; font-size:6pt; font-weight:700; text-transform:uppercase; letter-spacing:.5px; padding:1px 5px; border-radius:2px; color:#fff; white-space:nowrap; }
.fuentes { font-size:6.1pt; color:#6b7280; line-height:1.35; margin-top:5px; }
"""
    filas = ''.join(
        f'<tr><td>{e(a)}</td><td>{e(b)}</td><td>{e(c)}</td>'
        f'<td><span class="ch" style="background:{ETQ[k][1]}">{ETQ[k][0]}</span></td></tr>'
        for a, b, c, k in FILAS)
    return f"""<html><head><meta charset="utf-8"><style>{css}</style></head><body>
<div class="top"><div class="nombre">Ley de Rescate<small>Renta a personas naturales</small></div>
  <div class="meta">Cómo empezó y cómo va<br>12 de noviembre de 2026</div></div>
<div class="hero"><div class="marca">PL 477 de 2026 Cámara · artículos 47 a 50</div>
<h1>Fuera del Gobierno, <span class="hl">nadie defiende en público subir la renta a las personas</span></h1>
<p class="lead">Empezó con críticas sueltas y hoy el Centro Democrático la rechaza como bancada. Con el IVA a la comida, es de lo primero
que el Congreso pide quitar. Lo que aún no existe es una propuesta de cómo quedaría la tabla.</p></div>
<table class="cmp"><tr><th>Quién</th><th>Al radicar (29-oct a 1-nov)</th><th>Hoy (12-nov)</th><th></th></tr>{filas}</table>
<div class="fuentes">Los $37,7 millones son renta anual después de descuentos, no salario; el ministro ubica el pago efectivo desde ingresos
de unos $5 millones al mes. Se sentiría en la declaración de 2028. Fuentes: {e(FUENTES)}</div>
</body></html>"""


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f'Renta-personas-{FECHA}.pdf')
    from weasyprint import HTML
    HTML(string=construir(), base_url=REPO).write_pdf(out)
    import pymupdf
    pdf = pymupdf.open(out)
    png = out[:-4] + '.png'
    pdf[0].get_pixmap(dpi=200).save(png)
    print(f'OK · {out} · {pdf.page_count} página(s) · {png}')


if __name__ == '__main__':
    main()
