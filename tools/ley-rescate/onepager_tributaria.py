#!/usr/bin/env python3
"""
One page de la tributaria (Ley de Rescate) con el molde visual del one-pager de
Caudal (tools/caudal/brief/onepager.py), pero SIN el logo de Caudal × Cauce.

  /opt/homebrew/bin/python3.14 tools/ley-rescate/onepager_tributaria.py
  → Bases de datos/ley-rescate/Onepager-Tributaria-<fecha>.pdf y .png

El contenido va en el dict C de abajo: cada edición se edita a mano y cada dato
lleva su fuente en el pie. La gráfica sale de verificaciones.json (Tabla 14 del
proyecto), así que no se escribe dos veces.
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(AQUI, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'caudal', 'brief'))
import onepager as op                                            # noqa: E402  (CSS y fuentes del molde)

OUT_DIR = os.path.join(REPO, 'Bases de datos', 'ley-rescate')
e = op.e

C = {
    'fecha': '2026-11-10',
    'meta': ['La tributaria en una página', '10 de noviembre de 2026'],
    'marca': 'Ley de Rescate · PL 477 de 2026 Cámara · desde la tarde del lunes 9',
    'titulo': 'Liberales, conservadores y uribistas cierran la puerta al IVA a los alimentos; el Gobierno negocia con el FMI',
    'hl': 'el Gobierno negocia con el FMI',
    'lead': 'Lo que pasó entre la tarde del lunes 9 y el martes 10. Primer movimiento del trámite: el Senado designó ponentes '
            'a David Barguil (Conservador) y Carlos Mario Farelo (Cambio Radical). En la Cámara todavía no hay.',
    'frentes': [
        {'dir': 'En el Congreso', 'color': '#d9480f', 'que': 'Nadie pone la cara por el IVA a la canasta',
         'tx': 'Liberales y conservadores piden no pasar alimentos ni insumos del campo al 19 %; los conservadores proponen '
               'vender ISA. El borrador del Centro Democrático quita 10 impuestos y lo compensa con un «bono forzoso».'},
        {'dir': 'En el Gobierno', 'color': '#2b5672', 'que': '«Operación Rescate» y crédito del FMI',
         'tx': 'Gómez promete un recorte de 1 punto del PIB; según la tabla del proyecto ese punto llega en 2030. '
               'Bloomberg: se negocia un stand-by de unos US$15.000 millones; Hacienda dice que no se han discutido montos.'},
        {'dir': 'Las alertas', 'color': '#8a6d1c', 'que': 'El CARF dice que no alcanza',
         'tx': 'Pide un ajuste de 4 puntos del PIB y ve un déficit de hasta 9,5 % en 2027. Petro le ofreció '
               'al Centro Democrático una alianza contra la ley; Uribe la rechazó.'},
    ],
    'cifras': [
        {'n': '$15–20 billones', 't': 'Lo que recaudaría el texto que salga del Congreso, según congresistas. El Gobierno busca unos $80 billones (Infobae)'},
        {'n': 'US$15.000 M', 't': 'Crédito stand-by que se negocia con el FMI, según Bloomberg. No hay decisión en semanas (Reuters)'},
        {'n': '$11 billones/año', 't': 'Lo que conservaría no rebajar la renta ni quitar el patrimonio, según el Partido Liberal (2028-2030)'},
    ],
    'centro_dir': 'Lo que hay que mirar',
    'centro': 'Las mesas técnicas de esta semana definen el texto que llega al primer debate. Con el IVA a los '
              'alimentos sin quién lo vote, la pregunta es con qué se reemplaza ese recaudo.',
    'fechas': [
        {'d': 'Esta semana', 't': 'Mesas técnicas Gobierno y comisiones económicas'},
        {'d': 'Jue 12', 't': 'La subcomisión del Centro Democrático fija postura'},
        {'d': 'Jue 19', 't': 'Paro de la CUT; Petro también llama a marchar'},
        {'d': 'Fin de noviembre', 't': 'Debate conjunto de las comisiones, según La República'},
        {'d': 'Mié 16 dic', 't': 'Cierra el primer periodo de sesiones'},
    ],
    'fuentes': 'Fuentes: Portafolio (9 y 10-nov) · Infobae (10-nov) · La República (9-nov, CARF y FMI vía Bloomberg) · '
               'Valora Analitik (9-nov) · El Nuevo Siglo (9 y 10-nov) · El Tiempo y Minuto60 (10-nov) · Tabla 14 del PL 477, p. 204',
}


def grafica(ruta):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    vf = json.load(open(os.path.join(AQUI, 'verificaciones.json'), encoding='utf-8'))['lista'][-1]
    anios, comp = vf['anios'], vf['componentes']
    cols = ['#2b5672', '#d9480f', '#c9a227']
    plt.rcParams['font.family'] = ['Helvetica Neue', 'Helvetica', 'Arial']
    fig, ax = plt.subplots(figsize=(6.2, 3.05), dpi=220)
    base = [0.0] * len(anios)
    for c, col in zip(comp, cols):
        ax.bar(anios, c['v'], bottom=base, color=col, width=0.56, label=c['k'], zorder=2)
        base = [b + x for b, x in zip(base, c['v'])]
    for i, t in enumerate(base):
        y = 1.05 if 0.9 <= t <= 1.0 else t + 0.03   # que la cifra no pise la línea del «1 punto»
        ax.text(i, y, f'{t:.2f}'.replace('.', ','), ha='center', va='bottom', fontsize=10, fontweight='bold', color='#0b0d11')
    ax.axhline(1, color='#15171c', lw=1, ls=(0, (4, 3)), zorder=3)
    ax.text(-0.42, 1.04, '«1 punto del PIB» que anuncia Hacienda', fontsize=7.6, color='#15171c', va='bottom')
    ax.set_ylim(0, 1.28)
    ax.set_yticks([0, 0.5, 1])
    ax.set_yticklabels(['0', '0,5', '1,0'], fontsize=8, color='#5a6070')
    ax.tick_params(axis='x', labelsize=9, colors='#3d434f', length=0)
    ax.tick_params(axis='y', length=0)
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color('#c8ccd4')
    ax.grid(axis='y', color='#eceef2', zorder=0)
    ax.legend(loc='upper left', bbox_to_anchor=(0, -0.11), ncol=3, frameon=False, fontsize=7.4, handlelength=1, columnspacing=1.2)
    ax.set_title('El «1 punto del PIB» llega en 2030, no en 2027', loc='left', fontsize=11, fontweight='bold', color='#0b0d11', pad=16)
    ax.text(0, 1.04, 'Recortes de gasto que el proyecto cuantifica, % del PIB', transform=ax.transAxes, fontsize=7.6, color='#5a6070')
    fig.tight_layout()
    fig.savefig(ruta, facecolor='#fdfdfc')
    plt.close(fig)


def construir(c, g):
    fr = ''.join(f'<div class="rumbo" style="border-top-color:{f["color"]}"><div class="dir" style="color:{f["color"]}">{e(f["dir"])}</div>'
                 f'<div class="que">{e(f["que"])}</div><p>{e(f["tx"])}</p></div>' for f in c['frentes'])
    kp = ''.join(f'<div class="kpi"><div class="n">{e(k["n"])}</div><div class="t">{e(k["t"])}</div></div>' for k in c['cifras'])
    fe = ''.join(f'<div class="f"><div class="d">{e(f["d"])}</div><div class="t">{e(f["t"])}</div></div>' for f in c['fechas'])
    tit = e(c['titulo']).replace(e(c['hl']), f'<span class="hl">{e(c["hl"])}</span>', 1)
    css = op.CSS + """
.top { align-items:center; }
.top .nombre { font-size:15pt; font-weight:700; letter-spacing:-.3px; color:#0b0d11; line-height:1.1; }
.top .nombre small { display:block; font-size:7.6pt; font-weight:400; letter-spacing:1.4px; text-transform:uppercase; color:#5a6070; margin-top:3px; }
.kpi .n { font-size:15pt; }
.fuentes { font-size:6.9pt; color:#6b7280; line-height:1.4; margin-top:2px; }
"""
    return f"""<html><head><meta charset="utf-8"><style>{css}</style></head><body>
<div class="top"><div class="nombre">Ley de Rescate<small>Seguimiento de la tributaria</small></div>
  <div class="meta">{e(c['meta'][0])}<br>{e(c['meta'][1])}</div></div>
<div class="hero"><div class="marca">{e(c['marca'])}</div><h1>{tit}</h1><p class="lead">{e(c['lead'])}</p></div>
<div class="sec">Los tres frentes desde ayer</div>
<div class="rosa">{fr}</div>
<div class="mid"><div class="g"><img src="file://{e(g)}"><div class="pie">Tabla 14 del PL 477 de 2026 Cámara (p. 204). La venta de activos no entra: el proyecto dice que no mejora el balance fiscal (p. 76).</div></div><div class="kpis">{kp}</div></div>
<div class="centro"><div class="dir">{e(c['centro_dir'])}</div><p>{e(c['centro'])}</p></div>
<div class="sec">Lo que viene</div>
<div class="fechas">{fe}</div>
<div class="fuentes">{e(c['fuentes'])}</div>
</body></html>"""


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    g = os.path.join(OUT_DIR, f'onepager-tributaria-grafica-{C["fecha"]}.png')
    grafica(g)
    out = os.path.join(OUT_DIR, f'Onepager-Tributaria-{C["fecha"]}.pdf')
    from weasyprint import HTML
    HTML(string=construir(C, g), base_url=REPO).write_pdf(out)
    import pymupdf
    pdf = pymupdf.open(out)
    png = out[:-4] + '.png'
    pdf[0].get_pixmap(dpi=200).save(png)
    print(f'OK · {out} · {pdf.page_count} página(s) · {png}')


if __name__ == '__main__':
    main()
