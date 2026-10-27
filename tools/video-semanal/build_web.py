#!/usr/bin/env python3
"""Video semanal · versión web: «Los temas de hoy en el Congreso, analizados».

Usa el mismo contenido verificado y los mismos datos que los cuadros del video
(build_cuadros.py), así la página y el video no pueden decir cosas distintas.

  python3 tools/video-semanal/build_web.py 2026-10-27

Escribe congreso-hoy.html en la raíz del repo y actualiza la tarjeta del hub
del Legislativo (entre las marcas HOY:INICIO y HOY:FIN de legislativo.html).
El contenido está escrito para «mañana» (el video sale la víspera); aquí se
lee en presente con hoy().
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_cuadros as B  # noqa: E402  (lee contenido y datos de la semana de sys.argv)

C, ESC, REPO, e = B.C, B.ESC, B.REPO, B.e
FAVOR, CONTRA, MEDIO, SIN, NUEVO = B.FAVOR, B.CONTRA, B.MEDIO, B.SIN, B.NUEVO
ESTADO_P = {FAVOR: 'En 2025 votó por acoger la reforma', CONTRA: 'En 2025 votó en contra o pidió reabrirla',
            SIN: 'Estaba en la Cámara, no votó en 2025', NUEVO: 'Llegó a la Cámara este año'}
ESTADO_S = {FAVOR: 'Votó sí a la reforma laboral en 2024 o 2025', CONTRA: 'Votó no a la reforma laboral',
            SIN: 'Estaba en la Cámara, sin voto en esas sesiones', NUEVO: 'Llegó a la Cámara este año'}


def hoy(s):
    return s.replace('Mañana', 'Hoy').replace('mañana', 'hoy') if s else s


def leyenda(items):
    return '<div class="ch-leg">' + ''.join(
        f'<span><i style="background:{c}"{" class=nuevo" if c == NUEVO else ""}></i>{e(t)}</span>' for c, t in items) + '</div>'


def waffle(por_b, estados, por_fila=20, minimo=4, unidad='curules'):
    orden = sorted(por_b.items(), key=lambda kv: -len(kv[1]))
    grandes = [(b, v) for b, v in orden if len(v) >= minimo]
    chicas = [(b, x) for b, v in orden if len(v) < minimo for x in v]
    n_ch = sum(1 for b, v in orden if len(v) < minimo)
    filas = [(b, [(c, n, b) for c, n in v]) for b, v in grandes]
    if chicas:
        filas.append((f'Otras {n_ch} bancadas', [(c, n, b) for b, (c, n) in chicas]))
    out = ''
    L, G = 16, 4
    for nombre, celdas in filas:
        celdas = sorted(celdas, key=lambda t: B.ORDEN.index(t[0]))
        nf = -(-len(celdas) // por_fila)
        W, H = por_fila * (L + G) - G, nf * (L + G) - G
        sq = ''.join(
            f'<rect x="{(i % por_fila) * (L + G)}" y="{(i // por_fila) * (L + G)}" width="{L}" height="{L}" rx="3" fill="{c}"'
            f'{" class=nuevo" if c == NUEVO else ""} data-tip="{e(n)}|{e(b)}|{e(estados[c])}"/>' for i, (c, n, b) in enumerate(celdas))
        u = unidad if len(celdas) != 1 else unidad.rstrip('s')
        out += (f'<div class="wf-row"><div class="wf-lbl">{e(nombre)}<small>{len(celdas)} {u}</small></div>'
                f'<svg class="wf" viewBox="0 0 {W} {H}" style="max-width:{W}px" role="img" '
                f'aria-label="{e(nombre)}: {len(celdas)} {u}">{sq}</svg></div>')
    return out


def barras(filas, fmt, color):
    m = max(v for _, v in filas)
    return '<div class="hb">' + ''.join(
        f'<div class="hb-row" data-tip="{e(n)}|{e(fmt(v))}"><span class="hb-l">{e(n)}</span>'
        f'<span class="hb-t"><i style="width:{max(1.2, 100 * v / m):.1f}%;background:{color}"></i></span>'
        f'<span class="hb-v">{e(fmt(v))}</span></div>' for n, v in filas) + '</div>'


def apiladas(filas):
    m = max(sum(v for v, _, _ in segs) for _, segs, _ in filas)
    out = '<div class="hb">'
    for n, segs, txt in filas:
        seg = ''.join(f'<i style="width:{100 * v / m:.2f}%;background:{c}" data-tip="{e(n)}|{e(lbl)}: {v}"></i>'
                      for v, c, lbl in segs if v)
        out += (f'<div class="hb-row"><span class="hb-l">{e(n)}</span><span class="hb-t stack">{seg}</span>'
                f'<span class="hb-v">{e(txt)}</span></div>')
    return out + '</div>'


def posturas(ext):
    def col(t, c, items):
        return (f'<div class="ps-col"><div class="ps-h"><i style="background:{c}"></i>{e(t)}</div>' + ''.join(
            f'<div class="ps-card" style="border-top-color:{c}"><b>{e(a)}</b><p>{e(hoy(b))}</p></div>' for a, b in items) + '</div>')
    a = ext['arbitro']
    return (f'<div class="ps-arb"><span>Decide</span><div><b>{e(a[0])}</b> · {e(hoy(a[1]))}</div></div><div class="ps">'
            + col(ext['titulos'][0], CONTRA, ext['cambiar']) + col(ext['titulos'][1], MEDIO, ext['tiempo'])
            + col(ext['titulos'][2], FAVOR, ext['defender']) + '</div>')


def bloque(kicker, titulo, intro, cuerpo, fuente):
    return (f'<div class="blk"><div class="blk-k">{e(kicker)}</div><h3>{e(titulo)}</h3>'
            f'{f"<p class=intro>{intro}</p>" if intro else ""}{cuerpo}'
            f'<div class="blk-src">Fuente: {e(fuente)}</div></div>')


def pensional():
    P, F = C['pensional'], C['fuentes']['pensional']
    props = ''.join(
        f'<div class="pp"><div class="pp-h">{e(g["autor"])} <span>· {e(g["nota"])}</span></div>' + ''.join(
            f'<div class="pp-i{" hl" if a == "Art. 36" else ""}"><b>{e(a)}</b><span>{e(t)}</span></div>' for a, t in g['items'])
        + '</div>' for g in P['proposiciones'])
    reloj = '<ol class="tl">' + ''.join(
        f'<li class="{"now" if d == "mañana" else ""}"><span class="tl-f">{e(f)}</span><span class="tl-t">{e(t)}'
        f'<small>{e(hoy(d))}</small></span></li>' for f, t, d in P['reloj']) + '</ol>'
    por_b = B.clasifica_pensional()
    todos = [c for v in por_b.values() for c, _ in v]
    n = {c: todos.count(c) for c in B.ORDEN}
    wf = waffle(por_b, ESTADO_P) + leyenda([(c, f'{ESTADO_P[c]} ({n[c]})') for c in B.ORDEN])
    barra = (f'<div class="vote"><div class="vote-q">28 de junio de 2025 · ¿reabrir el articulado para votar estas proposiciones?</div>'
             f'<div class="vote-bar"><i style="width:{100 * 100 / 111:.1f}%;background:{CONTRA}" data-tip="No|100 votos"></i>'
             f'<i style="width:{100 * 11 / 111:.1f}%;background:{FAVOR}" data-tip="Sí|11 votos"></i></div>'
             f'<div class="vote-n"><span>100 votaron no</span><span>11 votaron sí</span></div>'
             f'<p>Por esa negativa la Corte encontró el vicio que hoy hay que corregir.</p></div>')
    gente = '<div class="ppl">' + ''.join(
        f'<div class="ppl-c" style="border-left-color:{c}"><b>{e(nm)}</b><small>{e(pa)}</small><p>{e(hoy(t))}</p></div>'
        for nm, pa, c, t in B.PUENTE) + '</div>'
    ej = ('<p class="note"><b>Un ejemplo concreto.</b> Hoy la ley descuenta 50 semanas por cada hijo, hasta tres, sin bajar de 850. '
          'La proposición de Salcedo sube ese piso a 1.000 y deja fuera a quienes están en el régimen de transición.</p>')
    return (bloque('Qué se vota', 'La Cámara vota 10 cambios a la reforma',
                   'La Corte dejó en pie cerca del 90 % de la ley y devolvió 9 artículos. Si la Cámara no los vota, esos artículos pueden caer.',
                   f'<div class="pp-grid">{props}</div>', F[0] + ' · La Silla Vacía · La República')
            + bloque('El reloj', 'Dos años y tres votaciones después, otra vez a la Cámara', None, reloj,
                     'Corte Constitucional (C-264 de 2026, Auto 841 de 2025) · actas de la Cámara · La República · Valora Analitik')
            + bloque('Lo que ya se votó', 'Lo que se vota hoy ya se negó a debatir una vez',
                     'Las proposiciones de hoy son las mismas que la Cámara no quiso discutir en junio de 2025. Tres personas conectan ese voto con la sesión de hoy.',
                     barra + gente + ej, 'votación nominal de la Cámara, 28-jun-2025, acta 43742 (incluye el voto manual escaneado) · La Silla Vacía')
            + bloque('Fuerzas internas', f'{n[NUEVO]} de {len(todos)} representantes llegaron después de la reforma',
                     'Cada cuadro es una curul de la Cámara actual, con lo que hizo su ocupante en la votación de junio de 2025. Pasa el cursor para ver quién es.',
                     wf, 'votación nominal de la Cámara, 28-jun-2025 (electrónica y manual) · listado oficial de representantes 2026-2030')
            + bloque('Fuerzas externas', 'Quién empuja y quién frena fuera del Congreso', None, posturas(P['externos']),
                     'La Silla Vacía · Valora Analitik · Cambio · La FM · Forbes'))


def fiscal():
    Fi, F = C['fiscal'], C['fuentes']['fiscal']
    tiles = '<div class="tiles">' + ''.join(
        f'<div class="tile{" hl" if i == 3 else ""}"><div class="n">{e(v)}</div><div class="t">{e(hoy(t))}</div><div class="s">{e(s)}</div></div>'
        for i, (v, t, s) in enumerate(Fi['cifras'])) + '</div>'
    fmt = lambda v: f'${v:,.1f} mil M'.replace(',', 'X').replace('.', ',').replace('X', '.')
    rec = barras(Fi['recorte_entidades'], fmt, CONTRA) + '<p class="note">Miles de millones de pesos recortados al presupuesto de 2026. El total es $13,81 billones.</p>'
    pg = ESC['senado_pgn2027_19oct']['por_bancada']
    filas, otras = [], []
    for b, x in pg.items():
        si, sr = x.get('Sí', 0), x.get('sin registro', 0)
        if si + sr >= 3:
            filas.append((b, [(si, FAVOR, 'Votó sí'), (sr, SIN, 'Sin voto registrado')], f'{si} de {si + sr}'))
        else:
            otras.append(x)
    si_o, tot_o = sum(x.get('Sí', 0) for x in otras), sum(sum(x.values()) for x in otras)
    filas.append((f'Otras {len(otras)} bancadas', [(si_o, FAVOR, 'Votó sí'), (tot_o - si_o, SIN, 'Sin voto registrado')], f'{si_o} de {tot_o}'))
    eco = ESC['economicas_conjuntas']
    sen = (apiladas(filas) + leyenda([(FAVOR, 'Votó sí al Presupuesto 2027'), (SIN, 'Sin voto registrado')])
           + f'<p class="note">Hoy se sientan <b>{len(eco["miembros"])} congresistas</b> de las comisiones terceras y cuartas. '
             f'El Pacto Histórico es la bancada más grande en las dos cámaras ({eco["por_bancada_camara"]["Pacto Histórico"]["total"]} representantes y '
             f'{eco["por_bancada_senado"]["Pacto Histórico"]["total"]} senadores), y ninguno de sus 7 senadores en esas comisiones votó el presupuesto.</p>')
    return (bloque('Qué se presenta', 'Un presupuesto por decreto y una semana de recortes',
                   'El ministro de Hacienda, Miguel Gómez, presenta hoy ante las comisiones económicas la modificación del presupuesto de 2026 y el de regalías 2027-2028.',
                   tiles, F[1] + ' · ' + F[3])
            + bloque('El recorte', 'Dónde pegó el recorte de 2026', 'Las doce entidades más afectadas por el Decreto 1585, según El País.',
                     rec, 'Decreto 1585 de 2026 · El País')
            + bloque('Fuerzas internas', 'En el Senado, el presupuesto pasó sin un solo voto del Pacto',
                     f'Plenaria del 19 de octubre: {ESC["senado_pgn2027_19oct"]["total_si"]} votos por el sí y ninguno por el no. Los demás senadores no registraron voto.',
                     sen, F[4] + ' · listado oficial de comisiones')
            + bloque('Fuerzas externas', 'Quién empuja y quién frena fuera del Congreso', None, posturas(Fi['externos']),
                     'El País · Valora Analitik · Revista C-Level · El Espectador · El Tiempo · Senado (Pacto Histórico)')
            + '<a class="more" href="pgn-2027.html">El análisis completo del Presupuesto 2027 <b>→</b></a>')


def laboral():
    L, F = C['laboral'], C['fuentes']['laboral']
    ag = '<div class="list">' + ''.join(
        f'<div class="list-i"><b>{e(a)}</b><span>{e(b)}</span>{f"<small>{e(c)}</small>" if c else ""}</div>' for a, b, c in L['agenda']) + '</div>'
    ant = ('<div class="ant"><div class="ant-h">No es el primer intento</div>' + ''.join(
        f'<div class="ant-i"><span>{e(a)} · <em>{e(b)}</em></span><b>{e(c)}</b></div>' for a, b, c in L['antecedentes']) + '</div>')
    dec = '<div class="list">' + ''.join(
        f'<div class="list-i two"><div><b>{e(a)}</b><small>{e(b)}</small></div><span>{e(c)}</span></div>' for a, b, c in L['decretos']) + '</div>'
    pb7 = B.clasifica_septima()
    todos = [c for v in pb7.values() for c, _ in v]
    n = {c: todos.count(c) for c in B.ORDEN}
    wf = (waffle(pb7, ESTADO_S, por_fila=8, minimo=1, unidad='miembros')
          + leyenda([(c, f'{ESTADO_S[c]} ({n[c]})') for c in B.ORDEN if n[c]])
          + '<div class="sub-h">Quién firma el Sistema de Cuidado (37 congresistas)</div>'
          + barras(B.AUTORES_CUIDADO, str, FAVOR))
    return (bloque('Qué se vota', 'La Comisión Séptima vota el Sistema Nacional de Cuidado', None, ag + ant, F[0] + ' · Caudal')
            + bloque('Mientras tanto', 'El Gobierno revisa 8 decretos laborales',
                     'El Ministerio del Trabajo los tiene en consulta hasta el 9 de noviembre. Dice que no cambia la Ley 2466 de 2025.', dec, F[1])
            + bloque('Fuerzas internas', f'Solo {n[FAVOR]} de los {len(todos)} miembros de la Séptima votaron la reforma laboral',
                     f'{n[NUEVO]} de sus miembros llegaron este año. El proyecto de cuidado es, en la práctica, del Pacto Histórico.',
                     wf, F[4] + ' · orden del día de la Comisión Séptima')
            + bloque('Fuerzas externas', 'Quién empuja y quién frena fuera del Congreso', None, posturas(L['externos']),
                     'Portafolio · El Universal · La Opinión · Blu Radio'))


CSS = """
.hy-hero{max-width:1080px;margin:3rem auto 0;padding:0 2rem;display:grid;grid-template-columns:minmax(0,1.3fr) minmax(260px,.7fr);gap:1.4rem;align-items:end}
.hy-k{font-size:.66rem;letter-spacing:.18em;text-transform:uppercase;color:var(--orange);margin-bottom:.7rem}
.hy-t{font-size:clamp(2rem,4.4vw,3.9rem);letter-spacing:-.05em;line-height:1;max-width:14ch}
.hy-lead{font-size:1rem;line-height:1.66;color:var(--gray);max-width:62ch;margin-top:1rem}.hy-lead b{color:var(--white)}
.hy-st{border:1px solid rgba(249,115,22,.35);background:linear-gradient(145deg,rgba(249,115,22,.10),rgba(255,255,255,.03));padding:1.15rem 1.25rem;font-size:.76rem;line-height:1.55;color:var(--gray)}
.hy-st b{display:block;color:var(--white);font-size:.95rem;margin-bottom:.35rem}
.hy-nav{max-width:1080px;margin:1.4rem auto 0;padding:0 2rem;display:flex;gap:.4rem;flex-wrap:wrap}
.hy-nav a{font:500 .64rem var(--hn);letter-spacing:.08em;text-transform:uppercase;text-decoration:none;color:var(--gray);border:1px solid var(--gray-light);padding:.42rem .6rem}
.hy-nav a:hover{border-color:var(--orange);color:var(--white)}
.temas{max-width:1080px;margin:1.6rem auto 0;padding:0 2rem;display:grid;grid-template-columns:repeat(3,1fr);gap:.8rem}
.tema{display:block;text-decoration:none;color:var(--white);background:var(--card-bg);border:1px solid var(--card-border);padding:1.1rem 1.15rem;transition:border-color .18s}
.tema:hover{border-color:rgba(61,111,255,.6)}
.tema .num{font-size:2.4rem;font-weight:800;color:var(--blue-light);line-height:.9}
.tema h2{font-size:1.15rem;letter-spacing:-.02em;margin-top:.55rem}
.tema .d{font-size:.68rem;color:var(--orange);letter-spacing:.06em;text-transform:uppercase;margin-top:.4rem}
.tema p{font-size:.78rem;line-height:1.55;color:var(--gray);margin-top:.5rem}
.sec{max-width:1080px;margin:0 auto;padding:3.4rem 2rem 0}
.sec>.k{font-size:.66rem;letter-spacing:.18em;text-transform:uppercase;color:var(--blue-light)}
.sec>h2{font-size:clamp(1.6rem,3vw,2.3rem);letter-spacing:-.04em;margin-top:.4rem}
.sec>.d{font-size:.8rem;color:var(--orange);margin-top:.35rem}
.blk{background:var(--card-bg);border:1px solid var(--card-border);padding:1.3rem 1.35rem;margin-top:1rem}
.blk-k{font-size:.6rem;letter-spacing:.14em;text-transform:uppercase;color:var(--gray)}
.blk h3{font-size:1.25rem;letter-spacing:-.025em;line-height:1.2;margin-top:.35rem}
.blk .intro{font-size:.86rem;line-height:1.62;color:var(--gray);max-width:74ch;margin:.55rem 0 0}
.blk-src{font-size:.64rem;color:rgba(255,255,255,.38);line-height:1.5;margin-top:1.1rem;padding-top:.7rem;border-top:1px solid var(--border)}
.note{font-size:.8rem;line-height:1.6;color:var(--gray);margin-top:1rem;max-width:76ch}.note b{color:var(--white)}
.pp-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.8rem;margin-top:1rem}
.pp{background:rgba(255,255,255,.03);padding:.9rem 1rem}.pp-h{font-size:.88rem;font-weight:700}.pp-h span{font-weight:400;color:var(--gray);font-size:.72rem}
.pp-i{display:grid;grid-template-columns:72px 1fr;gap:.6rem;padding:.55rem 0;border-top:1px solid var(--border);font-size:.78rem;line-height:1.45;color:var(--gray)}
.pp-i b{color:var(--white);font-size:.74rem}.pp-i.hl b{color:#d95926}.pp-i.hl span{color:var(--white)}
.tl{list-style:none;margin-top:1.1rem;position:relative}.tl:before{content:'';position:absolute;left:118px;top:.4rem;bottom:.4rem;width:1px;background:rgba(255,255,255,.12)}
.tl li{display:grid;grid-template-columns:104px 1fr;gap:28px;padding:.5rem 0;position:relative}
.tl li:after{content:'';position:absolute;left:113px;top:.85rem;width:11px;height:11px;border-radius:50%;background:var(--blue-light);box-shadow:0 0 0 4px #0a0c16}
.tl li.now:after{background:var(--orange)}.tl .tl-f{font-size:.78rem;font-weight:700;text-align:right;padding-top:.15rem}.tl li.now .tl-f{color:var(--orange)}
.tl .tl-t{font-size:.86rem;line-height:1.45}.tl small{display:block;font-size:.72rem;color:var(--gray);margin-top:.15rem}
.vote{margin-top:1.1rem}.vote-q{font-size:.8rem;color:var(--gray)}.vote-bar{display:flex;gap:2px;height:30px;margin-top:.6rem}.vote-bar i{display:block;height:100%;border-radius:3px}
.vote-n{display:flex;justify-content:space-between;font-weight:700;font-size:.95rem;margin-top:.45rem}.vote p{font-size:.76rem;color:var(--gray);margin-top:.35rem}
.ppl{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.8rem;margin-top:1.1rem}
.ppl-c{background:rgba(255,255,255,.03);border-left:4px solid;padding:.85rem 1rem}.ppl-c b{font-size:.95rem}.ppl-c small{display:block;font-size:.68rem;color:var(--gray);margin-top:.15rem}
.ppl-c p{font-size:.78rem;line-height:1.5;color:var(--gray);margin-top:.5rem}
.wf-row{display:grid;grid-template-columns:190px minmax(0,1fr);gap:1rem;align-items:start;margin-top:.75rem}
.wf-lbl{font-size:.8rem;line-height:1.2}.wf-lbl small{display:block;font-size:.66rem;color:var(--gray);margin-top:.15rem}
.wf{width:100%;height:auto;display:block}.wf rect{cursor:none;transition:opacity .12s}.wf rect.nuevo,.ch-leg i.nuevo{stroke:#2a3146;outline:1px solid #2a3146}
.wf:hover rect{opacity:.55}.wf rect:hover{opacity:1;stroke:#f4f3ef;stroke-width:1.5}
.ch-leg{display:flex;flex-wrap:wrap;gap:.45rem 1.3rem;margin-top:1rem;font-size:.74rem;color:var(--gray)}
.ch-leg i{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:.4rem;vertical-align:-1px}
.hb{margin-top:1rem;display:grid;gap:.45rem}.hb-row{display:grid;grid-template-columns:190px minmax(0,1fr) 120px;gap:.8rem;align-items:center;font-size:.8rem}
.hb-l{text-align:right}.hb-t{height:20px;display:flex;gap:2px}.hb-t i{display:block;height:100%;border-radius:0 3px 3px 0}.hb-t.stack i{border-radius:2px}
.hb-v{color:var(--gray);font-size:.74rem}.hb-row:hover .hb-l{color:var(--orange)}
.tiles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.7rem;margin-top:1rem}
.tile{background:rgba(255,255,255,.03);padding:1rem}.tile .n{font-size:clamp(1.3rem,2.2vw,1.9rem);font-weight:800;letter-spacing:-.04em}.tile.hl .n{color:var(--orange)}
.tile .t{font-size:.8rem;font-weight:500;margin-top:.4rem}.tile .s{font-size:.7rem;color:var(--gray);line-height:1.45;margin-top:.4rem}
.ps-arb{display:flex;gap:1rem;align-items:baseline;background:rgba(255,255,255,.03);padding:.75rem 1rem;margin-top:1rem;font-size:.82rem;line-height:1.45;color:var(--gray)}
.ps-arb span{font-size:.6rem;letter-spacing:.14em;text-transform:uppercase;font-weight:700}.ps-arb b{color:var(--white)}
.ps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.8rem;margin-top:.9rem}
.ps-h{font-size:.66rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin-bottom:.6rem}.ps-h i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:.45rem}
.ps-card{background:rgba(255,255,255,.03);border-top:3px solid;padding:.8rem .9rem;margin-bottom:.6rem}.ps-card b{font-size:.88rem}.ps-card p{font-size:.76rem;line-height:1.5;color:var(--gray);margin-top:.35rem}
.list{margin-top:1rem}.list-i{padding:.7rem 0;border-top:1px solid var(--border);display:grid;gap:.2rem;font-size:.86rem;line-height:1.45}
.list-i b{font-size:.72rem;color:var(--orange);letter-spacing:.04em}.list-i small{font-size:.72rem;color:var(--gray)}
.list-i.two{grid-template-columns:230px 1fr;gap:1rem}.list-i.two b{color:var(--white);font-size:.86rem;letter-spacing:0;display:block}.list-i.two span{color:var(--gray);font-size:.82rem}
.ant{background:rgba(255,255,255,.03);padding:.85rem 1rem;margin-top:1rem}.ant-h{font-weight:700;font-size:.9rem;margin-bottom:.4rem}
.ant-i{display:flex;justify-content:space-between;gap:1rem;padding:.5rem 0;border-top:1px solid var(--border);font-size:.8rem}.ant-i em{font-style:normal;color:var(--gray)}.ant-i b{color:#d95926}
.sub-h{font-weight:700;font-size:.92rem;margin-top:1.6rem}
.more{display:inline-block;margin-top:1rem;font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;color:var(--white);text-decoration:none;border:1px solid rgba(61,111,255,.5);padding:.6rem .8rem}
.more b{color:var(--blue-light)}.more:hover{background:rgba(0,71,255,.14)}
.meta{max-width:1080px;margin:0 auto;padding:3.4rem 2rem 0;display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.meta .blk ul{list-style:none;margin-top:.7rem}.meta li{font-size:.78rem;line-height:1.55;color:var(--gray);padding:.45rem 0;border-top:1px solid var(--border)}
.meta a{color:var(--green);text-decoration:none}.meta a:hover{text-decoration:underline}
#tip{position:fixed;z-index:9000;pointer-events:none;background:rgba(6,8,16,.97);border:1px solid rgba(0,71,255,.4);padding:.5rem .65rem;font-size:.76rem;line-height:1.4;max-width:260px;display:none}
#tip b{display:block}#tip span{display:block;color:var(--gray)}
@media(max-width:860px){.hy-hero,.meta{grid-template-columns:1fr}.temas,.pp-grid,.ppl,.ps{grid-template-columns:1fr}.tiles{grid-template-columns:1fr 1fr}
.wf-row{grid-template-columns:1fr;gap:.35rem}.hb-row{grid-template-columns:110px minmax(0,1fr) 78px;gap:.5rem;font-size:.72rem}.list-i.two{grid-template-columns:1fr;gap:.2rem}}
@media(max-width:560px){.hy-hero,.hy-nav,.temas,.sec,.meta{padding-left:1rem;padding-right:1rem}.blk{padding:1rem}.tl:before{left:84px}.tl li{grid-template-columns:70px 1fr;gap:26px}.tl li:after{left:79px}.tl .tl-f{font-size:.7rem}}
"""

JS = """
(function(){var t=document.getElementById('tip');
document.addEventListener('mouseover',function(ev){var el=ev.target.closest('[data-tip]');if(!el){t.style.display='none';return}
var p=el.getAttribute('data-tip').split('|');t.innerHTML='<b>'+p[0]+'</b>'+p.slice(1).map(function(x){return '<span>'+x+'</span>'}).join('');t.style.display='block'});
document.addEventListener('mousemove',function(ev){if(t.style.display!=='block')return;var x=ev.clientX+16,y=ev.clientY+16;
if(x+t.offsetWidth>innerWidth-8)x=ev.clientX-t.offsetWidth-16;if(y+t.offsetHeight>innerHeight-8)y=ev.clientY-t.offsetHeight-16;t.style.left=x+'px';t.style.top=y+'px'});
})();
"""


def pagina():
    T = C['temas']
    ids = ['pensional', 'fiscal', 'laboral']
    temas = ''.join(
        f'<a class="tema" href="#{ids[i]}"><div class="num">{t["n"]}</div><h2>{e(t["tema"])}</h2>'
        f'<div class="d">{e(t["donde"])}</div><p>{e(hoy(t["porque"]))}</p></a>' for i, t in enumerate(T))
    secs = ''.join(
        f'<section class="sec" id="{ids[i]}"><div class="k">Tema {t["n"]}</div><h2>{e(t["tema"])}</h2>'
        f'<div class="d">{e(t["donde"])}</div>{fn()}</section>' for i, (t, fn) in enumerate(zip(T, [pensional, fiscal, laboral])))
    criterio = ('Se cruzaron dos cosas: qué está en un orden del día de hoy (16 órdenes leídas: Cámara completa y Senado en '
                'plenaria y comisiones Primera, Tercera, Cuarta, Quinta y Sexta) y cuánto pesa cada asunto en la prensa colombiana '
                'de los últimos tres días. Quedaron fuera temas con mucha prensa pero sin decisión hoy: salario mínimo, ley de '
                'sometimiento, decreto de protesta y tasas del Banco de la República, que decide el viernes.')
    adv = ''.join(f'<li>{e(a)}</li>' for a in C['advertencias'])
    enl = ''.join(f'<li><a href="{e(u)}" target="_blank" rel="noopener">{e(t)}</a></li>' for t, u in C['enlaces'])
    enl += (f'<li>Órdenes del día del {e(C["fecha_corta"])} (Caudal, <code>ordenes-vigentes.json</code>) · votación nominal de la Cámara y del Senado · '
            'listado oficial de representantes y senadores 2026-2030.</li>')
    desc = f'Los tres temas que decide hoy el Congreso de Colombia, {C["fecha_larga"].lower()}: qué se vota, quién votó antes y quién empuja afuera.'
    nav_logo = ('<div class="e-nav-right"><a href="index.html" class="logo-link"><div class="logo-bars"><div class="logo-bar" style="height:20px"></div>'
                '<div class="logo-bar" style="height:15px"></div><div class="logo-bar" style="height:9px"></div><div class="logo-bar" style="height:4px"></div></div>'
                '<span class="logo-text">Ricardo<span>.</span>Ruiz</span></a></div>')
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <script defer src="/track.js"></script>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Hoy en el Congreso · {e(C['fecha_corta'])} · Ricardo Ruiz</title>
  <meta name="description" content="{e(desc)}" />
  <meta property="og:title" content="Hoy en el Congreso · los temas analizados" />
  <meta property="og:description" content="{e(desc)}" />
  <meta property="og:type" content="article" />
  <link rel="canonical" href="https://ricardoruiz.co/congreso-hoy.html" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="legislativo-base.css" />
  <style>{CSS}</style>
</head>
<body>
  <div class="bg-layer"></div><div class="cursor" id="cursor"></div><div class="cursor-ring" id="cursorRing"></div>
  <nav class="electoral-nav">
    <div class="e-nav-left"><a href="legislativo.html" class="e-btn-back">← Legislativo</a><a href="pricing.html" class="e-btn-planes">Planes &amp; precios</a><span class="nav-page-tag">Hoy en el Congreso</span><div class="electoral-nav-auth" id="nav-auth-area"></div></div>
    {nav_logo}
  </nav>

  <header class="hy-hero">
    <div>
      <div class="hy-k">Hoy en el Congreso · {e(C['fecha_larga'])}</div>
      <h1 class="hy-t">Tres decisiones que se toman hoy.</h1>
      <p class="hy-lead">En las tres pesa más lo que ya se votó que lo que se diga en el recinto. Para cada tema: <b>qué se vota</b>, <b>cómo votaron antes</b> quienes hoy deciden y <b>quién empuja y quién frena</b> fuera del Congreso.</p>
    </div>
    <aside class="hy-st"><b>Corte de los datos</b>{e(C['corte'].split(': ',1)[-1])}. Lo que se vote hoy no está todavía en esta página.</aside>
  </header>
  <nav class="hy-nav" aria-label="Secciones"><a href="#pensional">Pensional</a><a href="#fiscal">Presupuesto</a><a href="#laboral">Trabajo</a><a href="#metodo">Cómo se eligió</a><a href="#fuentes">Fuentes</a></nav>
  <div class="temas">{temas}</div>

  <main>
    {secs}
    <div class="meta">
      <div class="blk" id="metodo"><div class="blk-k">Método</div><h3>Cómo se eligieron los tres temas</h3><p class="intro">{e(criterio)}</p>
        <div class="blk-k" style="margin-top:1.2rem">Advertencias</div><ul>{adv}</ul></div>
      <div class="blk" id="fuentes"><div class="blk-k">Fuentes</div><h3>De dónde sale cada dato</h3><ul>{enl}</ul></div>
    </div>
  </main>

  <footer><span class="footer-brand">ricardoruiz.co · Legislativo · Hoy en el Congreso</span><a href="legislativo.html" class="e-btn-back" style="font-size:.62rem">← Legislativo</a></footer>
  <div id="tip"></div>
  <script src="legislativo-base.js?v=20260903"></script>
  <script>{JS}</script>
</body>
</html>
"""


TARJETA = """<!-- HOY:INICIO · la escribe tools/video-semanal/build_web.py -->
    <button class="analysis-feature" onclick="location.href='congreso-hoy.html'" aria-label="Abrir el análisis de los temas de hoy en el Congreso">
      <span class="analysis-feature-kicker">Hoy en el Congreso · {fecha}</span>
      <span class="analysis-feature-title">Los temas de hoy, analizados</span>
      <span class="analysis-feature-copy">{temas}: qué se vota, quién votó antes y quién empuja afuera.</span>
      <span class="analysis-feature-cta">Ver el análisis <b>→</b></span>
    </button>
    <!-- HOY:FIN -->"""


def main():
    (REPO / 'congreso-hoy.html').write_text(pagina(), encoding='utf-8')
    print('✓ congreso-hoy.html')
    hub = REPO / 'legislativo.html'
    s = hub.read_text(encoding='utf-8')
    k = [t.get('corto') or t['tema'].lower() for t in C['temas']]
    temas = f'{k[0][0].upper()}{k[0][1:]}, {k[1]} y {k[2]}'
    nueva = TARJETA.format(fecha=e(C['fecha_corta']), temas=e(temas))
    if '<!-- HOY:INICIO' in s:
        s = re.sub(r'<!-- HOY:INICIO.*?<!-- HOY:FIN -->', lambda m: nueva, s, flags=re.S)
    else:
        print('✗ legislativo.html no tiene las marcas HOY:INICIO / HOY:FIN; no se tocó')
        return
    hub.write_text(s, encoding='utf-8')
    print('✓ tarjeta del hub (legislativo.html)')


if __name__ == '__main__':
    main()
