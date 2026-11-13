#!/usr/bin/env python3
"""
One page: cómo empezó la Ley de Rescate y cómo va. Lo que el Congreso pide sacar y meter, cómo cambiaron los
temas en redes de una semana a otra, en qué se separan prensa y redes, y quién lleva la conversación digital.
Molde visual del one-pager de Caudal, SIN el logo de Caudal × Cauce.

  python3 tools/ley-rescate/analisis_redes.py "Bases de datos/ley-rescate/gh"   (antes: deja analisis-redes.json)
  /opt/homebrew/bin/python3.14 tools/ley-rescate/onepager_redes.py "Bases de datos/ley-rescate/gh"
  → Bases de datos/ley-rescate/Onepager-Redes-<FECHA>.pdf y .png
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(AQUI, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'caudal', 'brief'))
import onepager as op                                            # noqa: E402

OUT_DIR = os.path.join(REPO, 'Bases de datos', 'ley-rescate')
D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT_DIR, 'gh')
A = json.load(open(os.path.join(D, 'analisis-redes.json')))
TEMAS = {t['id']: t['nombre'] for t in json.load(open(os.path.join(AQUI, 'temas.json')))['temas']}
CORTO = {'iva_alimentos': 'IVA a la comida', 'renta_personas': 'Renta y clase media', 'austeridad': 'Recorte del Estado',
         'facultades': 'Facultades al presidente', 'renta_empresas': 'Baja de renta a empresas', 'nomina': 'Nómina y contratistas',
         'efectiva': 'Devolución del IVA', 'salud_cotizacion': 'Cotización a salud', 'medicina_prepagada': 'Prepagada',
         'patrimonio': 'Patrimonio', 'licores_tabaco': 'Licores y cigarrillos', 'activos': 'Venta de activos',
         'iva_tecnologia': 'IVA a celulares y plataformas', 'juegos': 'Apuestas', 'ruge': 'RUGE (grandes inversiones)',
         'aportes_empresas': 'Aportes de empresas', 'bebidas': 'Bebidas ultraprocesadas', 'combustibles': 'Combustibles'}
e = op.e
FECHA = os.environ.get('LR_FECHA', '2026-11-13')
AZUL, ROJO, GRIS, TINTA = '#2b5672', '#b4361f', '#9aa0aa', '#0b0d11'


def grafica_cambio(ruta, temas):
    """Pendiente: peso de cada tema en redes, semana 1 contra semana 2."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['font.family'] = ['Helvetica Neue', 'Helvetica', 'Arial']
    r1, r2 = A['redes1'], A['redes2']
    fig, ax = plt.subplots(figsize=(4.2, 2.05), dpi=220)
    fig.subplots_adjust(left=0.335, right=0.665, top=0.88, bottom=0.03)
    ys = []
    for t in temas:
        a, b = r1.get(t, 0), r2.get(t, 0)
        d = b - a
        col = AZUL if d >= 2 else ROJO if d <= -2 else GRIS
        ax.plot([0, 1], [a, b], color=col, lw=2.2 if col != GRIS else 1.2, solid_capstyle='round', zorder=2)
        ax.scatter([0, 1], [a, b], color=col, s=16, zorder=3)
        ys.append((t, a, b, col))
    # Etiquetas sin chocar: se reparten con una separación mínima a cada lado.
    def repartir(vals, sep):
        orden = sorted(range(len(vals)), key=lambda i: vals[i])
        pos = [0] * len(vals)
        ult = -1e9
        for i in orden:
            pos[i] = max(vals[i], ult + sep)
            ult = pos[i]
        return pos
    sep = 1.9
    izq = repartir([y[1] for y in ys], sep)
    der = repartir([y[2] for y in ys], sep)
    for (t, a, b, col), yi, yd in zip(ys, izq, der):
        n = CORTO.get(t, TEMAS.get(t, t))
        ax.text(-0.05, yi, f'{n}  {a:.0f} %'.replace('.', ','), ha='right', va='center', fontsize=6.1, color=col if col != GRIS else '#5a6070')
        ax.text(1.05, yd, f'{b:.0f} %  {n}'.replace('.', ','), ha='left', va='center', fontsize=6.1,
                color=col if col != GRIS else '#5a6070', fontweight='bold' if col != GRIS else 'normal')
    ax.set_xlim(0, 1)
    top = max(max(izq), max(der)) + 1.5
    ax.set_ylim(-0.8, top)
    ax.axis('off')
    ax.text(0, top + 0.6, '29-oct a 4-nov', ha='center', va='bottom', fontsize=7, color='#5a6070', fontweight='bold')
    ax.text(1, top + 0.6, '5 a 13-nov', ha='center', va='bottom', fontsize=7, color='#5a6070', fontweight='bold')
    fig.savefig(ruta, facecolor='#fdfdfc')
    plt.close(fig)


def grafica_brecha(ruta, temas):
    """Prensa contra redes: peso de cada tema en todo el periodo (dos puntos por tema)."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['font.family'] = ['Helvetica Neue', 'Helvetica', 'Arial']
    pr, re_ = A['prensa2'], A['redes2']
    fig, ax = plt.subplots(figsize=(4.2, 2.05), dpi=220)
    fig.subplots_adjust(left=0.33, right=0.97, top=0.88, bottom=0.12)
    temas = sorted(temas, key=lambda t: re_.get(t, 0) - pr.get(t, 0))
    for i, t in enumerate(temas):
        a, b = pr.get(t, 0), re_.get(t, 0)
        ax.plot([a, b], [i, i], color='#d4d8de', lw=3, zorder=1, solid_capstyle='round')
        ax.scatter([a], [i], color='#8a8f99', s=22, zorder=2)
        ax.scatter([b], [i], color=AZUL, s=22, zorder=3)
    ax.set_yticks(range(len(temas)))
    ax.set_yticklabels([CORTO.get(t, TEMAS.get(t, t)) for t in temas], fontsize=6.7, color='#2b303a')
    ax.tick_params(axis='y', length=0)
    ax.tick_params(axis='x', labelsize=6.3, colors='#5a6070', length=2)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{v:.0f} %'))
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color('#c9cdd4')
    ax.grid(axis='x', color='#eceef2', lw=0.6)
    ax.set_axisbelow(True)
    ax.text(0, 1.06, '●', transform=ax.transAxes, color='#8a8f99', fontsize=7, va='bottom')
    ax.text(0.05, 1.06, 'Prensa', transform=ax.transAxes, color='#5a6070', fontsize=6.8, va='bottom')
    ax.text(0.28, 1.06, '●', transform=ax.transAxes, color=AZUL, fontsize=7, va='bottom')
    ax.text(0.33, 1.06, 'Redes', transform=ax.transAxes, color=AZUL, fontsize=6.8, va='bottom', fontweight='bold')
    fig.savefig(ruta, facecolor='#fdfdfc')
    plt.close(fig)


# Lo que el Congreso pide sacar y meter. Sale de las posturas de bancada en votos.json y de las voces, con su fuente.
# El texto del proyecto no ha cambiado: no hay ponencia ni pliego de modificaciones.
SACAR = [
    ('IVA a la comida', 'Salvación Nacional, CD, Conservador, Cambio Radical, Liberal, Verde, Pacto y Tovar (paz). Es cerca del 29 % del recaudo.'),
    ('IVA a los insumos del campo', 'CD, Conservador, Liberal, Yamit Hurtado (Verde) y Pizarro (Pacto). También la SAC y Fedearroz.'),
    ('IVA a la medicina prepagada', 'CD, Conservador y Tovar. El CD lo puso entre sus tres líneas rojas el 12-nov.'),
]
METER = [
    ('Más recorte del Estado', 'CD: eliminar hasta 200 entidades. Fenalco: 20 % menos en varios presupuestos. Aliadas: el gasto es apenas un 25 % del ajuste.'),
    ('Vender activos de la Nación', 'CD: el 8,91 % de Ecopetrol y estudiar ISA. Conservador y Anif: estudiar ISA.'),
    ('IVA a todo paquete del exterior', 'CD: todo paquete de plataformas al 19 %. Berrío calcula $8 billones con un arancel a las compras pequeñas.'),
]

# Quién lleva la conversación digital: publicaciones con más interacción (reacciones + comentarios) desde la radicación.
# Solo cuentas públicas (verificadas, con 50.000 seguidores o más, o figuras públicas): la gente común va sin nombre.
CONTRA = [
    ('@alejovergel', 'TikTok · 30-oct', 152578, '«Abelard0 cobrará más impuestos a los más pobres y ayudará a los más ricos con nueva reforma tributaria».'),
    ('@andrespenaranda19', 'TikTok · 30-oct', 120882, '«Nos metieron el cuento en campaña de que no iban a subir impuestos».'),
    ('Duvalier Sánchez, senador Verde', 'TikTok · 31-oct', 100327, '«Quien fuera un Gilinski para que le hicieran una reforma tributaria a la medida».'),
]
FAVOR = [
    ('Ministerio de Hacienda', 'TikTok · 30-oct a 11-nov', 5110, '«¿La #LeyDeRescateEconómico aumentará el IVA para los colombianos? ¡NO! 19 millones recibirán la devolución».'),
    ('@ByViral24', 'X · 30-oct y 1-nov', 3517, 'Cuenta afín al Gobierno: «Los de siempre junto a la oposición salieron a lanzar falsas narrativas».'),
    ('Vicky Dávila, citada por Semana', 'X · 3-nov', 2601, '«¡Aplaudan! Petro dejó el país jodido, sin un peso, es el responsable».'),
]
# Lo nuevo de la segunda semana en redes, verificado contra el articulado cuando hace falta.
NUEVO = [
    ('Las cajas de compensación', 'Un video que dice que la ley «acabará con las cajas de compensación» sumó 19.369 interacciones en TikTok (11-nov). '
     'Lo que dice el articulado es menos: el art. 22 pasa a salud 1 de los 4 puntos del aporte a las cajas.'),
    ('La comida de las mascotas', 'Andrea Padilla (Verde, Tercera del Senado) sumó 5.060 en TikTok el 12-nov: «¡Con la comida de los gatos y perros NO!».'),
    ('Los votantes de De la Espriella', 'Aparece otro argumento: la ley «golpea a los votantes de De La Espriella» (11.627 interacciones, TikTok, 10-nov). '
     'Y la derecha también pide recortar más: Daniel Briceño (CD), 4.416 en X: «solo el 28 % es recorte».'),
]


def construir():
    temas_cambio = ['iva_alimentos', 'austeridad', 'renta_personas', 'facultades', 'activos', 'efectiva', 'nomina', 'medicina_prepagada']
    temas_brecha = ['iva_alimentos', 'austeridad', 'activos', 'licores_tabaco', 'renta_personas', 'facultades', 'efectiva', 'renta_empresas', 'nomina']
    g1 = os.path.join(OUT_DIR, f'onepager-redes-cambio-{FECHA}.png')
    g2 = os.path.join(OUT_DIR, f'onepager-redes-brecha-{FECHA}.png')
    grafica_cambio(g1, temas_cambio)
    grafica_brecha(g2, temas_brecha)
    t_r2, t_p2 = A['tono_redes2'], A['tono_prensa2']
    css = op.CSS + """
@page { margin:7mm 11mm 6mm 11mm; }
body { font-size:8pt; line-height:1.33; }
.top .nombre { font-size:15pt; font-weight:700; letter-spacing:-.3px; color:#0b0d11; line-height:1.1; }
.top .nombre small { display:block; font-size:7.4pt; font-weight:400; letter-spacing:1.4px; text-transform:uppercase; color:#5a6070; margin-top:3px; }
.hero { padding:7px 12px 6px; margin:6px 0 6px; }
h1 { font-size:16pt; margin-bottom:4px; }
.lead { font-size:8.7pt; }
.dos { display:flex; gap:8px; margin-bottom:6px; }
.caja { flex:1; background:#fdfdfc; border:1px solid #e2e5ea; border-radius:2px; padding:6px 9px 6px; }
.caja.s { border-top:3px solid #b4361f; } .caja.m { border-top:3px solid #2b5672; } .caja.n { border-top:3px solid #1f6b45; }
.caja .dir { font-size:6.9pt; text-transform:uppercase; letter-spacing:1.2px; font-weight:700; margin:0 0 4px; }
.caja.s .dir { color:#b4361f; } .caja.m .dir { color:#2b5672; } .caja.n .dir { color:#1f6b45; }
.it { margin:0 0 4px; } .it:last-child { margin:0; }
.it b { display:block; font-size:8.5pt; color:#0b0d11; line-height:1.2; }
.it span { font-size:7.4pt; color:#3d434f; line-height:1.32; }
.g { flex:1; padding:6px 8px 5px; }
.g .tit { font-size:9pt; font-weight:700; color:#0b0d11; margin:0 0 1px; line-height:1.2; }
.g .sub { font-size:7pt; color:#5a6070; margin:0 0 2px; }
.g .pie { font-size:6.6pt; }
.kpis3 { display:flex; gap:8px; margin-bottom:6px; }
.k { flex:1; background:#fdfdfc; border:1px solid #e2e5ea; border-left:3px solid #2b5672; border-radius:2px; padding:5px 9px 6px; }
.k .n { font-size:13.5pt; font-weight:700; letter-spacing:-.4px; line-height:1.05; color:#0b0d11; }
.k .t { font-size:7.2pt; color:#3d434f; margin-top:2px; line-height:1.3; }
.voz { display:flex; gap:6px; margin:0 0 4px; align-items:flex-start; }
.voz:last-child { margin:0; }
.voz .num { flex:0 0 52px; font-size:10pt; font-weight:700; color:#0b0d11; text-align:right; line-height:1.1; }
.voz .num small { display:block; font-size:5.8pt; font-weight:400; color:#6b7280; letter-spacing:.3px; }
.voz .q b { font-size:8pt; color:#0b0d11; } .voz .q em { font-style:normal; font-size:6.6pt; color:#6b7280; }
.voz .q span { display:block; font-size:7.3pt; color:#3d434f; line-height:1.3; }
.fuentes { font-size:6.2pt; color:#6b7280; line-height:1.38; margin-top:5px; }
"""
    fmt = lambda n: f'{n:,}'.replace(',', '.')
    items = lambda L: ''.join(f'<div class="it"><b>{e(a)}</b><span>{e(b)}</span></div>' for a, b in L)
    voces = lambda L: ''.join(f'<div class="voz"><div class="num">{fmt(n)}<small>interacciones</small></div><div class="q"><b>{e(a)}</b> <em>{e(d)}</em><span>{e(q)}</span></div></div>' for a, d, n, q in L)
    r2, p2 = round(t_r2.get('r', 0)), round(t_p2.get('r', 0))
    return f"""<html><head><meta charset="utf-8"><style>{css}</style></head><body>
<div class="top"><div class="nombre">Ley de Rescate<small>Cómo empezó, cómo va y qué se dice en redes</small></div>
  <div class="meta">PL 477 de 2026 Cámara<br>13 de noviembre de 2026</div></div>
<div class="hero"><div class="marca">Dos semanas después de radicada · el texto no ha cambiado</div>
<h1>En redes la ley ya no se discute solo por el IVA: <span class="hl">ahora la pelea es cuánto recorta el Estado</span></h1>
<p class="lead">El IVA a la comida sigue arriba. En redes creció el recorte del Estado y perdió peso la renta de la clase media; en prensa entraron
la venta de activos y los licores, la agenda de la negociación. A favor de la ley, en redes, habla casi solo el Gobierno.</p></div>

<div class="dos">
 <div class="caja s"><div class="dir">Lo que el Congreso pide sacar</div>{items(SACAR)}</div>
 <div class="caja m"><div class="dir">Lo que propone meter</div>{items(METER)}</div>
</div>

<div class="dos">
 <div class="g"><div class="tit">En redes, el recorte del Estado le quitó espacio a la renta</div>
  <div class="sub">Peso de cada tema en lo que se publica en X, TikTok, Instagram y Facebook, semana contra semana</div>
  <img src="file://{g1}"><div class="pie">Azul: ganó al menos 2 puntos. Rojo: perdió al menos 2. Ponderado por interacción.</div></div>
 <div class="g"><div class="tit">Prensa y redes hablan de cosas distintas</div>
  <div class="sub">Peso de cada tema, 5 a 13 de noviembre</div>
  <img src="file://{g2}"><div class="pie">La prensa sigue la negociación (activos, licores); las redes, el bolsillo y las facultades.</div></div>
</div>

<div class="kpis3">
 <div class="k"><div class="n">{r2} % · {p2} %</div><div class="t">de lo publicado esta semana rechaza la ley o una de sus medidas, en redes y en prensa.</div></div>
 <div class="k"><div class="n">26 a 1</div><div class="t">interacciones en contra por cada una a favor, del 5 al 13-nov (10 a 1 la primera semana).</div></div>
 <div class="k"><div class="n">58.008</div><div class="t">interacciones en un solo video de Paloma Valencia contra el IVA a la comida: cinco veces lo que suman las tres cuentas a favor de arriba.</div></div>
</div>

<div class="dos">
 <div class="caja s"><div class="dir">Llevan la conversación en contra</div>{voces(CONTRA)}</div>
 <div class="caja n"><div class="dir">Llevan la conversación a favor</div>{voces(FAVOR)}</div>
</div>

<div class="caja m" style="margin-bottom:0"><div class="dir">Lo nuevo en redes esta semana</div>
 <div class="dos" style="margin:0">{''.join(f'<div class="it" style="flex:1"><b>{e(a)}</b><span>{e(b)}</span></div>' for a, b in NUEVO)}</div></div>

<div class="fuentes"><b>Cómo se midió.</b> {fmt(A['n'].get('redes1', 0) + A['n'].get('redes2', 0))} publicaciones en redes (Apify) y {fmt(A['n'].get('prensa1', 0) + A['n'].get('prensa2', 0))} titulares de prensa desde el 29-oct, clasificados por tema y postura con un modelo de lenguaje.
Interacción = reacciones + comentarios; en redes cada publicación pesa según su interacción, en prensa cada titular igual. Se comparan porcentajes porque las lecturas de redes no tienen el mismo tamaño cada día.
Sacar y meter: posturas de bancada (Uribe 12-nov, Partido Liberal y Efraín Cepeda 10-nov), voces en prensa, Anif, Fenalco y Aliadas.</div>
</body></html>"""


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f'Onepager-Redes-{FECHA}.pdf')
    from weasyprint import HTML
    HTML(string=construir(), base_url=REPO).write_pdf(out)
    import pymupdf
    pdf = pymupdf.open(out)
    png = out[:-4] + '.png'
    pdf[0].get_pixmap(dpi=170).save(png)
    print(f'OK · {out} · {pdf.page_count} página(s) · {png}')


if __name__ == '__main__':
    main()
