#!/usr/bin/env python3
"""
One page: intención de voto en las Comisiones Terceras (Senado 15 · Cámara 31) sobre la Ley de
Rescate, persona por persona. Molde visual del one-pager de Caudal, SIN el logo de Caudal × Cauce.

  /opt/homebrew/bin/python3.14 tools/ley-rescate/onepager_tercera.py
  → Bases de datos/ley-rescate/Onepager-Tercera-<fecha>.pdf y .png

La lista de integrantes sale de votos.json (plantilla oficial de cada comisión, build_personas.py) y
el script aborta si alguien queda sin clasificar. Lo que dijo cada uno va en DICHO, con su fuente; quien
no ha hablado se muestra con la postura de su bancada, y así se rotula: nunca se le atribuye a la persona.
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(AQUI, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'caudal', 'brief'))
import onepager as op                                            # noqa: E402

OUT_DIR = os.path.join(REPO, 'Bases de datos', 'ley-rescate')
e = op.e
FECHA = '2026-11-11'

# Estados: si = dice que la apoya · sic = la apoya con cambios · cond = condiciona · no = en contra · sin = sin postura propia
EST = {'si': ('Dice que la apoya', '#1f6b45'), 'sic': ('La apoya con cambios', '#5fa37a'),
       'cond': ('Condiciona su voto', '#c98a1c'), 'sin': ('No ha dicho cómo votará', '#b9bdc5'),
       'no': ('En contra', '#b4361f')}
ORD = ['si', 'sic', 'cond', 'sin', 'no']
SIG = {'sn': 'SN', 'cd': 'CD', 'con': 'Cons.', 'cr': 'CR', 'u': 'La U', 'lib': 'Lib.', 'asi': 'ASI', 'verde': 'Verde',
       'paz': 'Paz', 'pacto': 'Pacto'}
# Postura de la bancada para quien no ha hablado (votos.json: «post» declarado; si no hay, «sin»).
BANC = {'sn': 'si', 'con': 'sic', 'pacto': 'no'}

# Lo que dijo cada integrante, con su fuente. Clave = slug de personas.json.
DICHO = {
    'sara-jimena-castellanos-rodriguez': ('si', 'Apoyará: «Si no se hace algo drástico, como un rescate, el país va a entrar en una recesión». No al IVA a los alimentos.', 'El Tiempo, 10-nov'),
    'david-alejandro-barguil-assis': ('sic', 'Ponente. No ha dicho su voto; su partido la respalda con ajustes (sin IVA a la canasta, a insumos ni a la prepagada).', 'El Tiempo, 10-nov', True),
    'christian-munir-garces-aljure': ('cond', 'Apoyo solo si el recorte alcanza a todo el Estado, no solo al Gobierno central. No al IVA a la prepagada.', 'Blu Radio, 6-nov'),
    'juan-fernando-caicedo-callejas': ('cond', 'Sí a achicar el Estado; no a pasarle el ajuste al bolsillo de la gente.', 'La Libertad, 31-oct'),
    'david-ricardo-racero-mayorca': ('no', '«Esta ley de rescate económico es peor que la reforma tributaria de Carrasquilla».', 'Noticias Caracol, 30-oct'),
    'jorge-alejandro-ocampo-giraldo': ('no', 'Cuestiona las facultades extraordinarias del art. 7 y que el Pacto no fuera invitado a las mesas.', 'La Silla Vacía, 30-oct · El Espectador, 9-nov'),
    'gustavo-adolfo-moreno-hurtado': ('sin', 'Fue a la reunión del Gobierno con sus aliados: «Hemos quedado en el compromiso de instalar unas mesas de trabajo». No ha dicho su voto.', 'El Espectador, 9-nov'),
    'jorge-rodrigo-tovar-velez': ('sic', 'Apoyará «la mayoría del articulado» y los recortes; no el IVA a frutas, verduras y café, la gasolina ni la prepagada.', 'Radio Guatapurí, 5-nov'),
    'oscar-dario-perez-pineda': ('cond', 'Rechaza el alza a licores: «los únicos que están de fiesta son los contrabandistas». Duda que alcancen los tiempos.', 'Caracol Radio, 6-nov'),
    'catherine-juvinao-clavijo': ('cond', 'Lo primero que quitaría es el IVA a verduras y alimentos; rechaza duplicar la retención a los CDT.', 'Caracol Radio, 4-nov'),
    'yamit-noe-hurtado-neira': ('cond', 'No respalda encarecer los insumos del campo. Está en las mesas con el Gobierno: «Hay cosas en que estamos de acuerdo».', 'Boyacá 7 Días, 3-nov · Infobae, 8-nov'),
    'alfredo-ape-cuello-baute': ('sic', 'Preside la comisión. No ha dicho su voto; su partido la respalda con ajustes.', 'Ficha de la Cámara', True),
}
# Lo que ha dicho la bancada de quienes no han hablado, una línea por partido.
BANC_TX = [
    ('Liberal · 8 votos', 'Sin voto definido. Pide aplazar la rebaja de renta a empresas, mantener el patrimonio y no subir al 19 % alimentos ni insumos del campo (comunicado del 10-nov).'),
    ('Centro Democrático · 5 sin hablar', 'Sin posición oficial: su subcomisión la fija el jueves 12. Uribe: no al IVA a la canasta. Propuso un borrador alterno el 9-nov.'),
    ('Cambio Radical · 4', 'Sin posición de bancada. Su senador Farelo es ponente en la Cuarta; Triana: el ajuste del gasto sí, el café al 19 % no.'),
    ('La U · 4', 'Sin posición de bancada. Norma Hurtado no acompaña el alza de aportes a salud.'),
]


# Nombre corto para la página (nombre + primer apellido). Si entra alguien nuevo a la comisión, el script avisa.
ESPECIAL = {'alfredo-ape-cuello-baute': 'Alfredo Ape Cuello', 'jorge-rodrigo-tovar-velez': 'Jorge Rodrigo Tovar',
                'maria-del-mar-pizarro-garcia': 'María del Mar Pizarro', 'jorge-alejandro-ocampo-giraldo': 'Alejandro Ocampo',
                'juan-fernando-caicedo-callejas': 'Juan Fernando Caicedo', 'juan-carlos-garces-rojas': 'Juan Carlos Garcés Rojas',
                'oscar-dario-perez-pineda': 'Óscar Darío Pérez', 'juan-loreto-gomez-soto': 'Juan Loreto Gómez',
                'maria-angelica-guerra-lopez': 'María Angélica Guerra', 'jose-ricardo-ardila-pinedo': 'Ricardo Ardila',
                'francy-natalia-moreno-puin': 'Natalia Moreno', 'jaime-arturo-santamaria-acosta': 'Jaime Santamaría',
                'maria-camila-salas-salas': 'Camila Salas', 'kelyn-johana-gonzalez-duarte': 'Kelyn González',
                'karen-juliana-lopez-salazar': 'Karen López', 'deisy-johana-osorio-marquez': 'Deisy Osorio',
                'martin-alonso-caicedo-carabali': 'Martín Caicedo', 'alix-yirley-vargas-torrado': 'Alix Vargas',
                'yessid-enrique-pulgar-daza': 'Yessid Pulgar', 'edgardo-miguel-espitia-cabrales': 'Edgardo Espitia',
                'christian-munir-garces-aljure': 'Christian Garcés', 'david-alejandro-barguil-assis': 'David Barguil',
                'david-ricardo-racero-mayorca': 'David Racero', 'sara-jimena-castellanos-rodriguez': 'Sara Castellanos',
                'gustavo-adolfo-moreno-hurtado': 'Gustavo Moreno', 'andrea-padilla-villarraga': 'Andrea Padilla',
                'catherine-juvinao-clavijo': 'Catherine Juvinao', 'yamit-noe-hurtado-neira': 'Yamit Hurtado',
                'diego-fran-ariza-perez': 'Diego Ariza', 'camilo-esteban-avila-morales': 'Camilo Ávila',
                'camilo-andres-gomez-mosquera': 'Camilo Gómez', 'hector-david-chaparro-chaparro': 'Héctor Chaparro',
                'pedro-antonio-paternina-gulfo': 'Pedro Paternina', 'jorge-hernan-bastidas-rosero': 'Jorge Bastidas',
                'carlos-edward-osorio-aguiar': 'Carlos Osorio', 'jhon-jairo-berrio-lopez': 'Jhon Jairo Berrío',
                'carlos-alberto-cuenca-chaux': 'Carlos Cuenca', 'jose-luis-abdalla-olivera': 'José Luis Abdalla',
                'estefanel-gutierrez-perez': 'Estefanel Gutiérrez', 'fernando-arias-cardona': 'Fernando Arias',
                'mello-castro-gonzalez': 'Mello Castro', 'amaury-julio-perez': 'Amaury Julio', 'santiago-castro-gomez': 'Santiago Castro',
                'juliana-aray-franco': 'Juliana Aray', 'milene-jarava-diaz': 'Milene Jarava', 'yolanda-wong-baldiris': 'Yolanda Wong'}


def integrantes():
    v = json.load(open(os.path.join(AQUI, 'votos.json'), encoding='utf-8'))
    per = json.load(open(os.path.join(AQUI, 'personas.json'), encoding='utf-8'))
    out = {}
    for k in ('senado', 'camara'):
        lista = []
        for b in v['bloques']:
            for s in b['plantilla'][k]:
                d = DICHO.get(s)
                if d:
                    lista.append({'s': s, 'b': b['id'], 'est': d[0], 'tx': d[1], 'f': d[2], 'banc': len(d) > 3})
                else:
                    lista.append({'s': s, 'b': b['id'], 'est': BANC.get(b['id'], 'sin'), 'tx': '', 'f': '', 'banc': True})
        for x in lista:
            x['n'] = ESPECIAL.get(x['s']) or per[x['s']]['n']
            x['foto'] = per[x['s']].get('foto')
        tot = v['camaras'][k]['total']
        if len(lista) != tot:
            raise SystemExit(f'{k}: {len(lista)} integrantes y la comisión tiene {tot}')
        sin_nombre = [x['s'] for x in lista if x['s'] not in ESPECIAL]
        if sin_nombre:
            raise SystemExit(f'sin nombre corto: {sin_nombre}')
        lista.sort(key=lambda x: (ORD.index(x['est']), x['banc'], x['b']))
        out[k] = {'lista': lista, 'tot': tot, 'may': v['camaras'][k]['mayoria']}
    usados = {x['s'] for c in out.values() for x in c['lista']}
    sobra = set(DICHO) - usados
    if sobra:
        raise SystemExit(f'DICHO trae gente que no está en la Tercera: {sobra}')
    return out


def puntos(c):
    # Una fila de círculos en orden de postura: lleno = lo dijo la persona · anillo = es la postura de su bancada.
    r, gap = 5.2, 2.4
    w = len(c['lista']) * (2 * r + gap)
    s = []
    for i, x in enumerate(c['lista']):
        col = EST[x['est']][1]
        cx = r + i * (2 * r + gap)
        if x['banc'] and x['est'] != 'sin':
            s.append(f'<circle cx="{cx:.1f}" cy="{r + 1:.1f}" r="{r - 1.1:.1f}" fill="#fdfdfc" stroke="{col}" stroke-width="2.2"/>')
        else:
            s.append(f'<circle cx="{cx:.1f}" cy="{r + 1:.1f}" r="{r:.1f}" fill="{col}"/>')
    mx = c['may'] * (2 * r + gap) - gap / 2
    s.append(f'<line x1="{mx:.1f}" x2="{mx:.1f}" y1="0" y2="{2 * r + 2:.1f}" stroke="#15171c" stroke-width="1.1" stroke-dasharray="2 1.6"/>')
    return f'<svg viewBox="0 0 {w:.0f} {2 * r + 2:.0f}" style="width:100%;height:auto;display:block">{"".join(s)}</svg>'


def bloque(titulo, c):
    cnt = {k: sum(1 for x in c['lista'] if x['est'] == k) for k in ORD}
    afin = cnt['si'] + cnt['sic'] + cnt['cond']
    falta = max(0, c['may'] - afin)
    cab = (f'<div class="cb"><div><div class="ct">{e(titulo)}</div><div class="cm">{c["tot"]} integrantes · mayoría {c["may"]}</div></div>'
           f'<div class="cf"><b>{falta}</b>votos más necesita el Gobierno, aun contando a favor a quienes condicionan</div></div>')
    filas = []
    for k in ORD:
        g = [x for x in c['lista'] if x['est'] == k]
        if not g:
            continue
        propios = [x for x in g if x['tx']]
        resto = [x for x in g if not x['tx']]
        fl = ''.join(f'<div class="p"><b>{e(x["n"])}</b> <span class="sg">{SIG[x["b"]]}</span> {e(x["tx"])} <span class="fu">{e(x["f"])}</span></div>'
                     for x in propios)
        if resto:
            nombres = ', '.join(f'{e(x["n"])} <span class="sg">{SIG[x["b"]]}</span>' for x in resto)
            pref = 'Por su bancada: ' if k != 'sin' else ''
            fl += f'<div class="p r">{pref}{nombres}</div>'
        filas.append(f'<div class="gr" style="border-left-color:{EST[k][1]}"><div class="gt" style="color:{EST[k][1] if k != "sin" else "#6b7280"}">{e(EST[k][0])} · {len(g)}</div>{fl}</div>')
    return f'<div class="com">{cab}{puntos(c)}{"".join(filas)}</div>'


def construir(d):
    css = op.CSS + """
@page { margin:8mm 10mm 7mm 10mm; }
body { font-size:7.7pt; line-height:1.32; }
.top { align-items:center; }
.top .nombre { font-size:14pt; font-weight:700; letter-spacing:-.3px; color:#0b0d11; line-height:1.1; }
.top .nombre small { display:block; font-size:7.2pt; font-weight:400; letter-spacing:1.4px; text-transform:uppercase; color:#5a6070; margin-top:3px; }
.hero { padding:8px 12px 7px; margin:7px 0 7px; }
h1 { font-size:16.5pt; margin-bottom:4px; }
.lead { font-size:8.7pt; }
.dos { display:flex; gap:8px; margin-bottom:7px; }
.com { flex:1; background:#fdfdfc; border:1px solid #e2e5ea; border-radius:2px; padding:7px 9px 6px; }
.cb { display:flex; justify-content:space-between; align-items:flex-start; gap:8px; margin-bottom:5px; }
.com svg { margin-bottom:5px; }
.ct { font-size:10.5pt; font-weight:700; color:#0b0d11; letter-spacing:-.1px; }
.cm { font-size:7pt; text-transform:uppercase; letter-spacing:1px; color:#5a6070; }
.cf { text-align:right; font-size:6.9pt; color:#3d434f; max-width:44%; line-height:1.25; }
.cf b { display:block; font-size:16pt; color:#9b3b2a; letter-spacing:-.4px; line-height:1; }
.cnt { display:flex; flex-wrap:wrap; gap:3px 9px; font-size:6.8pt; color:#3d434f; margin:4px 0 5px; }
.cnt i { display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:3px; vertical-align:-0.5px; }
.gr { border-left:3px solid; padding:1px 0 2px 6px; margin-bottom:4px; }
.gt { font-size:6.8pt; text-transform:uppercase; letter-spacing:1px; font-weight:700; margin-bottom:1px; }
.p { font-size:7.2pt; color:#2b303a; line-height:1.3; margin-bottom:1.5px; }
.p b { color:#0b0d11; }
.p.r { color:#3d434f; }
.sg { font-size:5.9pt; font-weight:700; letter-spacing:.3px; color:#4b5260; border:1px solid #c8ccd4; border-radius:2px; padding:0 2px; white-space:nowrap; }
.fu { color:#7a808c; font-size:6.5pt; white-space:nowrap; }
.ley { font-size:6.6pt; color:#5a6070; margin-top:4px; border-top:1px solid #eceef2; padding-top:3px; }
.banc { display:grid; grid-template-columns:1.25fr 1.25fr 1fr 0.8fr; gap:6px; margin-bottom:7px; }
.banc div { background:#fdfdfc; border:1px solid #e2e5ea; border-radius:2px; padding:5px 8px 6px; font-size:7.1pt; color:#3d434f; line-height:1.3; }
.banc b { display:block; font-size:7pt; text-transform:uppercase; letter-spacing:.9px; color:#2b5672; margin-bottom:1px; }
.centro { padding:7px 12px 8px; margin-bottom:7px; }
.centro p { font-size:9.6pt; }
.fechas { margin-bottom:6px; }
.fechas .t { font-size:7.4pt; }
.fuentes { font-size:6.3pt; color:#6b7280; line-height:1.35; }
"""
    sen, cam = d['senado'], d['camara']
    sin_total = sum(1 for c in (sen, cam) for x in c['lista'] if x['est'] == 'sin')
    tot = sen['tot'] + cam['tot']
    ley = ('Círculo lleno: lo dijo la persona. Anillo: no ha hablado y se toma la postura que anunció su bancada. '
           'La raya marca la mayoría.')
    fe = ''.join(f'<div class="f"><div class="d">{e(a)}</div><div class="t">{e(b)}</div></div>' for a, b in [
        ('Jue 12', 'El Centro Democrático fija postura'), ('Esta semana', 'Mesas técnicas con el Gobierno'),
        ('Pendiente', 'Ponentes de la Cámara y si votan solo las Terceras'), ('Jue 19', 'Paro de la CUT y marcha de Petro'),
        ('Fin de nov.', 'Primer debate, según La República'), ('Mié 16 dic', 'Cierra el primer periodo')])
    bt = ''.join(f'<div><b>{e(a)}</b>{e(b)}</div>' for a, b in BANC_TX)
    return f"""<html><head><meta charset="utf-8"><style>{css}</style></head><body>
<div class="top"><div class="nombre">Ley de Rescate<small>Intención de voto en las Comisiones Terceras</small></div>
  <div class="meta">Voto por voto<br>11 de noviembre de 2026 · 9 a. m.</div></div>
<div class="hero"><div class="marca">PL 477 de 2026 Cámara · primer debate</div>
<h1>La Tercera no tiene dueño: <span class="hl">{sin_total} de sus {tot} integrantes</span> no han dicho cómo votarán</h1>
<p class="lead">El Pacto suma 10 votos en contra y no le alcanzan para hundirla. Del lado del Gobierno, solo Sara Castellanos ha dicho sin rodeos
que la apoya, y aun ella rechaza el IVA a los alimentos. Los demás aliados que han hablado ponen condiciones, y casi todas coinciden: que no haya IVA a la comida.</p></div>
<div class="dos">{bloque('Tercera del Senado', sen)}{bloque('Tercera de la Cámara', cam)}</div>
<div class="sec">Lo que ha dicho la bancada de quienes no han hablado</div>
<div class="banc">{bt}</div>
<div class="centro"><div class="dir">Lo que hay que mirar</div><p>Aun contando a favor a quienes condicionan, al Gobierno le faltan 4 votos en el Senado y 8 en la
Cámara. En la Cámara le bastan los 6 liberales y los 4 del Centro Democrático que no han hablado; en el Senado, sus 3 (dos liberales y María Angélica Guerra) no alcanzan: necesita uno más de
Cambio Radical, La U, ASI o Verde.</p></div>
<div class="sec">Lo que viene</div>
<div class="fechas">{fe}</div>
<div class="fuentes">{e(ley)} Integrantes según la página oficial de cada comisión (Senado y Cámara, 11-nov). Si el primer debate lo votan las
cuatro comisiones económicas se suman las Cuartas (44 más): están en ricardoruiz.co/ley-de-rescate-votos.html. Fuentes: El Tiempo, Caracol Radio,
Blu Radio, El Espectador, Radio Guatapurí, Boyacá 7 Días, Infobae, La Libertad, La Silla Vacía, Noticias Caracol, Portafolio, El Nuevo Siglo.</div>
</body></html>"""


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    d = integrantes()
    out = os.path.join(OUT_DIR, f'Onepager-Tercera-{FECHA}.pdf')
    from weasyprint import HTML
    HTML(string=construir(d), base_url=REPO).write_pdf(out)
    import pymupdf
    pdf = pymupdf.open(out)
    png = out[:-4] + '.png'
    pdf[0].get_pixmap(dpi=170).save(png)
    for k, c in d.items():
        print(k, {s: sum(1 for x in c['lista'] if x['est'] == s) for s in ORD})
    print(f'OK · {out} · {pdf.page_count} página(s) · {png}')


if __name__ == '__main__':
    main()
