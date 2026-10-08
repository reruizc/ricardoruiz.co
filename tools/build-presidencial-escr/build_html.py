#!/usr/bin/env python3
"""Genera presidencial-2018.html y presidencial-2022.html desde el chasis de
consultas-escr-2026.html.

Mismo patron que los tres tableros territoriales 2023: las paginas son EL MISMO
archivo salvo un bloque de configuracion. Si tocas la logica del chasis, vuelve
a correr esto para propagarla.

  python3 tools/build-presidencial-escr/build_html.py
"""
import os, re, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHASIS = os.path.join(RAIZ, 'consultas-escr-2026.html')

ANIOS = {
    '2010': {'fecha1v': '30 May 2010', 'fecha2v': '20 Jun 2010'},
    '2014': {'fecha1v': '25 May 2014', 'fecha2v': '15 Jun 2014'},
    '2018': {'fecha1v': '27 May 2018', 'fecha2v': '17 Jun 2018'},
    '2022': {'fecha1v': '29 May 2022', 'fecha2v': '19 Jun 2022'},
    # 2026: escrutinio de las comisiones (mesa a mesa) + exterior del preconteo. Conserva el
    # CTA de endoso: aquí sí aplica (compara la presidencial con el Congreso 2026).
    '2026': {'fecha1v': '31 May 2026', 'fecha2v': '21 Jun 2026', 'endoso': True,
             'meta': 'Presidencia · 31 May y 21 Jun 2026',
             'fuente': 'Registraduría · Escrutinio de comisiones · exterior del preconteo'},
    # Consultas internas del Pacto Histórico para ordenar sus listas al Congreso.
    'pacto2025': {
        'salida': 'consultas-pacto-2025.html', 's3': 'pres-escr/pacto2025',
        'titulo': 'Consultas Pacto Histórico 2025', 'linea1': 'Consultas', 'linea2': 'Pacto 2025',
        'pagina': 'Consultas Pacto Histórico<br/><span>Senado y Cámara 2025</span>',
        'miga': 'Consultas Pacto Histórico · Senado y Cámara 2025',
        'meta': 'Consultas internas · 26 Oct 2025', 'sublabel': 'Consulta', 'kpi': 'Votos en la consulta',
        'activa': 'senado',
        'color': {'senado': '#6B2D8B', 'camara': '#c0392b'},
        'corto': {'senado': 'Consulta Senado', 'camara': 'Consulta Cámara'},
        'paleta': {'senado': ['#6B2D8B','#c0392b','#e0803a','#0047FF','#3d8b3d','#7c3aed','#06b6d4','#d9db24','#0d9488','#C8102E','#F7941D','#0067B1'],
                   'camara': ['#c0392b','#6B2D8B','#e0803a','#0047FF','#3d8b3d','#7c3aed','#06b6d4','#d9db24','#0d9488','#C8102E','#F7941D','#0067B1']},
    },
}


def genera(anio, cfg):
    src = open(CHASIS, encoding='utf-8').read()
    pres = 'titulo' not in cfg          # presidencial (1V/2V) o consulta
    titulo = cfg.get('titulo', f'Presidencial {anio}')
    s3 = cfg.get('s3', f'pres-escr/{anio}')
    meta = cfg.get('meta', f'Presidencia · {cfg.get("fecha1v")} y {cfg.get("fecha2v")}')
    subs = [
        # --- identidad de la pagina ---
        ('<title>Consultas Presidenciales 2026 · Escrutinio · Ricardo Ruiz</title>',
         f'<title>{titulo} · Escrutinio · Ricardo Ruiz</title>'),
        ('<span class="curtain-sub">Consultas Presidenciales · Escrutinio</span>',
         f'<span class="curtain-sub">{titulo} · Escrutinio</span>'),
        ('<span class="curtain-line"><span class="curtain-word from-left white">Consultas</span></span>\n'
         '        <span class="curtain-line"><span class="curtain-word from-right blue">2026</span></span>',
         f'<span class="curtain-line"><span class="curtain-word from-left white">{cfg.get("linea1", "Presidencial")}</span></span>\n'
         f'        <span class="curtain-line"><span class="curtain-word from-right blue">{cfg.get("linea2", anio)}</span></span>'),
        ('<div class="page-title">Consultas<br/><span>Presidenciales 2026</span></div>',
         f'<div class="page-title">{cfg.get("pagina", f"Presidencial<br/><span>{anio}</span>")}</div>'),
        ('&nbsp;/&nbsp; Consultas Presidenciales · Escrutinio 2026',
         f'&nbsp;/&nbsp; {cfg.get("miga", f"Presidencial · Escrutinio {anio}")}'),
        ('<span class="meta-item">Elección: <b>Consultas · 13 Mar 2026</b></span>',
         f'<span class="meta-item">Elección: <b>{meta}</b></span>'),
        ('<span class="sub-label">Consulta presidencial</span>',
         f'<span class="sub-label">{cfg.get("sublabel", "Vuelta")}</span>'),
        ('<div class="kpi-label">Votos en la consulta</div>',
         f'<div class="kpi-label">{cfg.get("kpi", "Votos válidos")}</div>'),

        # La vuelta que se abre por defecto.
        ("      activeCons: 'gran',", f"      activeCons: '{cfg.get('activa', '1v')}',"),
        ('<div class="source-badge">Fuente: <b>Registraduría · Escrutinio Definitivo</b></div>',
         f'<div class="source-badge">Fuente: <b>{cfg.get("fuente", "Registraduría · Escrutinio Definitivo")}</b></div>'),

        # --- datos ---
        ("const r = await fetch(`${S3}/consultas/${path}.json`);",
         "const r = await fetch(`${S3}/%s/${path}.json`);" % s3),
        ("const r = await fetch(`${S3}/consultas/dep-${code}.json`);",
         "const r = await fetch(`${S3}/%s/dep-${code}.json`);" % s3),

        # --- las dos vueltas reemplazan a las tres consultas ---
        ("""    const CONS_COLOR = {
      gran:       '#1866DF',
      frente:     '#3d8b3d',
      soluciones: '#d9db24',
    };
    const CONS_SHORT = {
      gran:       'La Gran Consulta',
      frente:     'Frente por la Vida',
      soluciones: 'Consulta de Soluciones',
    };""",
         """    const CONS_COLOR = {
      '1v': '#0047FF',
      '2v': '#e0803a',
    };
    const CONS_SHORT = {
      '1v': 'Primera vuelta',
      '2v': 'Segunda vuelta',
    };"""),
        ("""    const CONS_PALETTE = {
      gran: ['#1866DF','#06b6d4','#E53935','#003580','#7c3aed','#0067B1','#C8102E','#F7941D','#0d9488'],
      frente: ['#3d8b3d','#22c55e','#65a30d','#15803d','#4d7c0f'],
      soluciones: ['#d9db24','#eab308','#facc15'],
    };""",
         """    // Los colores siguen el orden de votacion de cada vuelta. NO son fijos por
    // persona: un mismo candidato puede tener otro color entre 1V y 2V si cambio
    // de posicion. La leyenda y el mapa siempre leen del mismo sitio, asi que
    // dentro de una vuelta son consistentes.
    const CONS_PALETTE = {
      '1v': ['#0047FF','#c0392b','#e0803a','#3d8b3d','#7c3aed','#06b6d4','#d9db24','#0d9488','#C8102E','#F7941D','#0067B1','#003580','#64748b'],
      '2v': ['#0047FF','#c0392b','#e0803a','#3d8b3d','#7c3aed','#06b6d4'],
    };"""),
    ]

    for a, b in subs:
        if src.count(a) != 1:
            sys.exit(f'[{anio}] patron no unico ({src.count(a)}x): {a[:70]!r}')
        src = src.replace(a, b)

    # Consultas: sus claves y colores en vez de las dos vueltas
    if not pres:
        js = lambda d: ',\n'.join(f"      '{k}': {v!r}".replace('"', "'") for k, v in d.items())
        src = re.sub(r"    const CONS_COLOR = \{.*?\n    \};", "    const CONS_COLOR = {\n" + js(cfg['color']) + ",\n    };", src, count=1, flags=re.S)
        src = re.sub(r"    const CONS_SHORT = \{.*?\n    \};", "    const CONS_SHORT = {\n" + js(cfg['corto']) + ",\n    };", src, count=1, flags=re.S)
        src = re.sub(r"    const CONS_PALETTE = \{.*?\n    \};", "    const CONS_PALETTE = {\n" + js(cfg['paleta']) + ",\n    };", src, count=1, flags=re.S)
        for k in cfg['color']:
            if f"'{k}':" not in src:
                sys.exit(f'[{anio}] no quedó la clave {k} en los colores')

    # El CTA de endoso es de 2026 (compara presidencial con Congreso mesa a mesa)
    # y no aplica a un historico. Se corta por coincidencia LITERAL del bloque:
    # un regex .*? con re.S se salta hasta el siguiente </div></div> del archivo
    # y se lleva por delante el contenedor del mapa.
    cta = """        <div class="endoso-cta">
          <div class="endoso-cta-text"><b>\u00bfQuieres medir el endoso?</b><br/>Compara la votaci\u00f3n de un candidato presidencial con uno al Congreso mesa por mesa.</div>
          <a href="endoso-2026.html" class="endoso-btn" id="endoso-cta-btn">Calcular endoso \u2192</a>
        </div>

"""
    if src.count(cta) != 1:
        sys.exit(f'[{anio}] el bloque del CTA de endoso no aparece exactamente una vez')
    quitado = 0 if cfg.get('endoso') else 2
    if quitado:
        src = src.replace(cta, '')

    # El HTML tiene que quedar balanceado: si no, el contenedor del mapa
    # desaparece y Leaflet falla con "Map container not found".
    base = open(CHASIS, encoding="utf-8").read()
    if src.count('<div') != base.count('<div') - quitado or src.count('</div>') != base.count('</div>') - quitado:
        sys.exit(f'[{anio}] el HTML quedo desbalanceado tras quitar el CTA')

    out = os.path.join(RAIZ, cfg.get('salida', f'presidencial-{anio}.html'))
    open(out, 'w', encoding='utf-8').write(src)
    print(f'  {os.path.basename(out)}  ({len(src)/1024:.0f} KB)')


if __name__ == '__main__':
    print('generando desde consultas-escr-2026.html:')
    for anio, cfg in ANIOS.items():
        genera(anio, cfg)
