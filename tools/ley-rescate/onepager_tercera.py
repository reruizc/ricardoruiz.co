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
FECHA = '2026-11-12'

# Estados: si = dice que la apoya · sic = la apoya con cambios · cond = condiciona · no = en contra · sin = sin postura propia
EST = {'si': ('Dice que la apoya', '#1f6b45'), 'sic': ('La apoya con cambios', '#5fa37a'),
       'cond': ('Condiciona su voto', '#c98a1c'), 'sin': ('No ha dicho cómo votará', '#b9bdc5'),
       'no': ('En contra', '#b4361f')}
ORD = ['si', 'sic', 'cond', 'sin', 'no']
SIG = {'sn': 'SN', 'cd': 'CD', 'con': 'Cons.', 'cr': 'CR', 'u': 'La U', 'lib': 'Lib.', 'asi': 'ASI', 'verde': 'Verde',
       'paz': 'Paz', 'pacto': 'Pacto'}
# Postura de la bancada para quien no ha hablado (votos.json: «post» declarado; si no hay, «sin»).
BANC = {'sn': 'si', 'con': 'sic', 'cd': 'cond', 'pacto': 'no'}  # cd: condiciones de bancada presentadas por Uribe el 12-nov

# Lo que dijo cada integrante, con su fuente. Clave = slug de personas.json.
DICHO = {
    'sara-jimena-castellanos-rodriguez': ('si', 'Apoyará; no el IVA a los alimentos.', 'El Tiempo, 10-nov'),
    'david-alejandro-barguil-assis': ('sic', 'Ponente; no ha dicho su voto.', 'El Tiempo, 10-nov', True),
    'christian-munir-garces-aljure': ('cond', '«Soy optimista»; nada que afecte a las familias de menos ingresos.', 'Blu Radio, 12-nov'),
    'juan-fernando-caicedo-callejas': ('cond', 'Sí a achicar el Estado, no a pasar el ajuste al bolsillo.', 'La Libertad, 31-oct'),
    'david-ricardo-racero-mayorca': ('no', '«Peor que la reforma de Carrasquilla».', 'Noticias Caracol, 30-oct'),
    'jorge-alejandro-ocampo-giraldo': ('no', 'Cuestiona las facultades del art. 7.', 'La Silla Vacía, 30-oct'),
    'gustavo-adolfo-moreno-hurtado': ('sin', 'En las mesas con el Gobierno; sin voto anunciado.', 'El Espectador, 9-nov'),
    'jorge-rodrigo-tovar-velez': ('sic', 'Apoyará «la mayoría del articulado», sin IVA a la canasta.', 'Radio Guatapurí, 5-nov'),
    'oscar-dario-perez-pineda': ('cond', 'No al alza a licores.', 'Caracol Radio, 6-nov'),
    'santiago-castro-gomez': ('cond', '«No apoyaríamos nada que grave en mayor medida la canasta familiar».', 'La FM, 12-nov'),
    'catherine-juvinao-clavijo': ('cond', 'Quitaría el IVA a alimentos; no a la retención de CDT.', 'Caracol Radio, 4-nov'),
    'yamit-noe-hurtado-neira': ('cond', 'No a encarecer los insumos del campo; está en las mesas.', 'Boyacá 7 Días, 3-nov'),
    'alfredo-ape-cuello-baute': ('sic', 'Preside la comisión; no ha dicho su voto.', 'Ficha de la Cámara', True),
}
# Lo que ha dicho la bancada de quienes no han hablado, una línea por partido.
BANC_TX = [
    ('Liberal · 8 votos', 'Sin voto definido. Pide aplazar la rebaja de renta a empresas, mantener el patrimonio y no subir al 19 % alimentos ni insumos (10-nov).'),
    ('Cambio Radical · 4', 'Sin posición de bancada. Farelo es ponente en la Cuarta; Triana: el ajuste del gasto sí, el café al 19 % no.'),
    ('La U · 4', 'Sin posición de bancada. Norma Hurtado no acompaña el alza de aportes a salud.'),
]
# Proyecto del Gobierno contra la propuesta del Centro Democrático (12-nov). Gobierno: articulado del PL 477. CD: prensa del 12-nov.
CD_VS = [
    ('IVA a la canasta familiar', 'Pasa al 19 % desde 2028, con devolución a hogares pobres', 'no', 'No'),
    ('IVA a insumos del campo', 'Pasa al 19 % desde 2028', 'no', 'No'),
    ('Medicina prepagada', 'Deja de estar excluida del IVA desde 2028 (art. 45)', 'no', 'No'),
    ('Compras en plataformas del exterior', 'Les cobra IVA', 'si', 'Sí: todo paquete al 19 %'),
    ('Híbridos y eléctricos', 'Sube su IVA', 'si', 'Sí, con capítulo para transporte público'),
    ('Renta de empresas', '33 % en 2027 y 31 % desde 2028 (art. 57)', 'cambia', '30 % desde 2027'),
    ('Impuesto al patrimonio', 'Sigue 2027-2030: 0,5 % y 1 % desde 95.500 UVT (arts. 66-68)', 'cambia', 'Eliminarlo desde 2027'),
    ('Impuestos saludables', 'Los reestructura desde 2028 (art. 56)', 'cambia', 'Derogarlos desde 2027'),
    ('4x1.000 y timbre', 'No los toca', 'nuevo', '4x1.000 a 3, 2 y 1 por mil y a 0 en 2030; timbre fuera desde 2027'),
]
CD_PONE = ('Para compensar: bonos de hasta $80 billones al año (2027-2031), inversión forzosa del 20 % de la renta que pase de $500 millones, '
           'vender el 8,91 % de Ecopetrol y estudiar ISA y las electrificadoras, y eliminar hasta 200 entidades. Aún no se conoce su impacto fiscal (El Espectador).')


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
           f'<div class="cf"><b>{falta}</b>votos más necesita el Gobierno si cumple las condiciones</div></div>')
    filas = []
    for k in ORD:
        g = [x for x in c['lista'] if x['est'] == k]
        if not g:
            continue
        propios = [x for x in g if x['tx']]
        resto = [x for x in g if not x['tx']]
        fl = ''.join(f'<div class="p"><b>{e(x["n"])}</b> <span class="sg">{SIG[x["b"]]}</span> {e(x["tx"])}</div>'
                     for x in propios)
        if resto:
            nombres = ', '.join(f'{e(x["n"])} <span class="sg">{SIG[x["b"]]}</span>' for x in resto)
            pref = 'Por su bancada: ' if k != 'sin' else ''
            fl += f'<div class="p r">{pref}{nombres}</div>'
        filas.append(f'<div class="gr" style="border-left-color:{EST[k][1]}"><div class="gt" style="color:{EST[k][1] if k != "sin" else "#6b7280"}">{e(EST[k][0])} · {len(g)}</div>{fl}</div>')
    return f'<div class="com">{cab}{"".join(filas)}</div>'


def construir(d):
    css = op.CSS + """
@page { margin:7mm 10mm 6mm 10mm; }
body { font-size:7.7pt; line-height:1.32; }
.top { align-items:center; }
.top .nombre { font-size:14pt; font-weight:700; letter-spacing:-.3px; color:#0b0d11; line-height:1.1; }
.top .nombre small { display:block; font-size:7.2pt; font-weight:400; letter-spacing:1.4px; text-transform:uppercase; color:#5a6070; margin-top:3px; }
.hero { padding:7px 12px 6px; margin:6px 0 6px; }
h1 { font-size:15pt; margin-bottom:4px; }
.lead { font-size:8.7pt; }
.dos { display:flex; gap:8px; margin-bottom:5px; }
.com { flex:1; background:#fdfdfc; border:1px solid #e2e5ea; border-radius:2px; padding:6px 9px 4px; }
.cb { display:flex; justify-content:space-between; align-items:flex-start; gap:8px; margin-bottom:3px; }
.com svg { margin-bottom:5px; }
.ct { font-size:10.5pt; font-weight:700; color:#0b0d11; letter-spacing:-.1px; }
.cm { font-size:7pt; text-transform:uppercase; letter-spacing:1px; color:#5a6070; }
.cf { text-align:right; font-size:6.9pt; color:#3d434f; max-width:44%; line-height:1.25; }
.cf b { display:block; font-size:16pt; color:#9b3b2a; letter-spacing:-.4px; line-height:1; }
.cnt { display:flex; flex-wrap:wrap; gap:3px 9px; font-size:6.8pt; color:#3d434f; margin:4px 0 5px; }
.cnt i { display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:3px; vertical-align:-0.5px; }
.gr { border-left:3px solid; padding:0 0 1px 6px; margin-bottom:3px; }
.gt { font-size:6.8pt; text-transform:uppercase; letter-spacing:1px; font-weight:700; margin-bottom:1px; }
.p { font-size:6.9pt; color:#2b303a; line-height:1.26; margin-bottom:1px; }
.p b { color:#0b0d11; }
.p.r { color:#3d434f; }
.sg { font-size:5.9pt; font-weight:700; letter-spacing:.3px; color:#4b5260; border:1px solid #c8ccd4; border-radius:2px; padding:0 2px; white-space:nowrap; }
.fu { color:#7a808c; font-size:6.2pt; white-space:nowrap; }
.ley { font-size:6.6pt; color:#5a6070; margin-top:4px; border-top:1px solid #eceef2; padding-top:3px; }
.banc { display:grid; grid-template-columns:1.2fr 1fr 1fr; gap:6px; margin-bottom:7px; }
.banc div { background:#fdfdfc; border:1px solid #e2e5ea; border-radius:2px; padding:5px 8px 6px; font-size:7.1pt; color:#3d434f; line-height:1.3; }
.banc b { display:block; font-size:7pt; text-transform:uppercase; letter-spacing:.9px; color:#2b5672; margin-bottom:1px; }
.vs { width:100%; border-collapse:collapse; background:#fdfdfc; border:1px solid #e2e5ea; margin-bottom:4px; font-size:7.3pt; }
.vs th { text-align:left; font-size:6.6pt; text-transform:uppercase; letter-spacing:1px; color:#5a6070; font-weight:700; padding:3px 7px; border-bottom:1.5px solid #15171c; }
.vs td { padding:2px 7px; border-bottom:1px solid #eceef2; vertical-align:top; line-height:1.28; color:#2b303a; }
.vs td:first-child { font-weight:700; color:#0b0d11; width:24%; }
.vs td:nth-child(2) { width:38%; color:#3d434f; }
.ch { display:inline-block; font-size:6.2pt; font-weight:700; text-transform:uppercase; letter-spacing:.6px; padding:1px 5px; border-radius:2px; margin-right:5px; color:#fff; }
.ch.no { background:#b4361f; } .ch.si { background:#1f6b45; } .ch.cambia { background:#c98a1c; } .ch.nuevo { background:#2b5672; }
.bl { font-size:6.9pt; color:#3d434f; line-height:1.32; margin:-2px 0 7px; } .bl i { font-style:normal; font-weight:700; color:#2b5672; }
.pone { font-size:7.1pt; color:#3d434f; line-height:1.32; margin:0 0 7px; }
.centro { padding:7px 12px 8px; margin-bottom:7px; }
.centro p { font-size:8.8pt; }
.fechas { margin-bottom:4px; } .fechas .f { padding:4px 8px 5px; }
.fechas .t { font-size:7.4pt; }
.fuentes { font-size:6.3pt; color:#6b7280; line-height:1.35; }
"""
    sen, cam = d['senado'], d['camara']
    def falta(c):
        n = sum(1 for x in c['lista'] if x['est'] in ('si', 'sic', 'cond'))
        return max(0, c['may'] - n)
    def grupo(c, b, est):
        return [x for x in c['lista'] if x['b'] == b and x['est'] == est and not x['tx']]
    fs, fc = falta(sen), falta(cam)
    lib_s, lib_c = len([x for x in sen['lista'] if x['b'] == 'lib']), len([x for x in cam['lista'] if x['b'] == 'lib'])
    sin_s = sum(1 for x in sen['lista'] if x['est'] == 'sin')
    sin_c = sum(1 for x in cam['lista'] if x['est'] == 'sin')
    ETQ = {'no': 'Rechaza', 'si': 'Acepta', 'cambia': 'Cambia', 'nuevo': 'Agrega'}
    vs = ''.join(f'<tr><td>{e(m)}</td><td>{e(g)}</td><td><span class="ch {k}">{ETQ[k]}</span>{e(t)}</td></tr>' for m, g, k, t in CD_VS)
    ley = ('En cada comisión, quien no ha hablado aparece con la postura que anunció su bancada, y así se rotula. '
           '«Condiciona» cuenta las condiciones que ha puesto en público, no un voto anunciado.')
    fe = ''.join(f'<div class="f"><div class="d">{e(a)}</div><div class="t">{e(b)}</div></div>' for a, b in [
        ('Hoy · 5 p. m.', 'Consejo Gremial con el ministro Gómez'), ('Pendiente', 'Nombres de los nuevos ponentes'),
        ('Jue 19', 'Paro de la CUT y marcha de Petro'), ('Fin de nov.', 'Primer debate, según La República'), ('Mié 16 dic', 'Cierra el primer periodo')])
    bt = ' · '.join(f'<i>{e(a)}</i>: {e(b)}' for a, b in BANC_TX)
    return f"""<html><head><meta charset="utf-8"><style>{css}</style></head><body>
<div class="top"><div class="nombre">Ley de Rescate<small>Intención de voto en las Comisiones Terceras</small></div>
  <div class="meta">Voto por voto<br>12 de noviembre de 2026 · 4 p. m.</div></div>
<div class="hero"><div class="marca">PL 477 de 2026 Cámara · primer debate en las cuatro comisiones económicas</div>
<h1>El Centro Democrático pone sus condiciones: <span class="hl">sí a recortar y a gravar las compras por internet, no al IVA a la comida</span></h1>
<p class="lead">Uribe presentó hoy lo que el partido acepta y lo que rechaza, y prepara una ponencia sustitutiva por si el Gobierno no acoge sus cambios. No anunció
voto. Con el CD condicionando en vez de oponerse, al Gobierno le faltarían {fs} votos en la Tercera del Senado y {fc} en la de la Cámara, si cumple las condiciones.
En la Cámara le bastarían los {lib_c} liberales, que no han dicho cómo votarán; en el Senado sus {lib_s} no alcanzan. Si el CD radica su ponencia alterna, la cuenta se complica.</p></div>
<div class="sec">El proyecto del Gobierno frente a la propuesta del Centro Democrático</div>
<table class="vs"><tr><th>Tema</th><th>Lo que dice el proyecto</th><th>Lo que propone el CD</th></tr>{vs}</table>
<p class="pone">{e(CD_PONE)}</p>
<div class="dos">{bloque('Tercera del Senado', sen)}{bloque('Tercera de la Cámara', cam)}</div>
<div class="bl"><b>Bancadas sin postura:</b> {bt}</div>

<div class="sec">Lo que viene</div>
<div class="fechas">{fe}</div>
<div class="fuentes">{e(ley)} Las Cuartas (44 más) también votan: ricardoruiz.co/ley-de-rescate-votos.html. El proyecto: articulado del PL 477; la propuesta del CD:
borrador conocido por prensa (El Espectador habla de 23 artículos y La FM de 76). Lo dicho por cada congresista: El Tiempo, Blu Radio, La FM, El Heraldo, La Razón, Caracol Radio,
La Libertad, Noticias Caracol, La Silla Vacía, Radio Guatapurí, Boyacá 7 Días, El Espectador, Infobae, Portafolio.</div>
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
