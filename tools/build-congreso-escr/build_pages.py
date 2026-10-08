#!/usr/bin/env python3
"""Genera senado-2014/2018/2022.html y camara-2014/2018/2022.html a partir de las páginas de 2026.

  python3 tools/build-congreso-escr/build_pages.py                 # las seis
  python3 tools/build-congreso-escr/build_pages.py senado 2022     # una corporación / un año

Cada reemplazo es una cadena EXACTA de la plantilla y el script aborta si alguna no aparece:
si cambias senado-2026.html en esas líneas, ajusta aquí la cadena. Los datos los genera
build.py en Bases de datos/output_congreso_escr/senado-<año>/ (S3: congreso-2026/output/senado-<año>/).
"""
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DATOS = RAIZ / 'Bases de datos' / 'output_congreso_escr'
ANIOS = {
    '2022': {'es': '13 mar 2022', 'en': 'Mar 13, 2022', 'zh': '2022年3月13日'},
    '2018': {'es': '11 mar 2018', 'en': 'Mar 11, 2018', 'zh': '2018年3月11日'},
    '2014': {'es': '9 mar 2014', 'en': 'Mar 9, 2014', 'zh': '2014年3月9日'},
}
TODOS = ['2014', '2018', '2022', '2026']

# colores de partidos que no existen en 2026 (la plantilla los pinta gris)
COLORES_EXTRA = ("if(/polo democr/i.test(n))return'#F5C400';if(/decencia/i.test(n))return'#CC00CC';"
                 "if(/opci[oó]n ciudadana/i.test(n))return'#D4AA00';if(/justa libres/i.test(n))return'#A95A33';"
                 "if(/\\bMAIS\\b|alternativo ind/i.test(n))return'#D35F5F';if(/\\bAICO\\b|autoridades ind/i.test(n))return'#6F917C';"
                 "if(/alianza social indep/i.test(n))return'#F2BC0F';if(/fuerza ciudadana/i.test(n))return'#EA760D';")


def selector(actual, corp='senado', span='sn-meta-anio'):
    links = ' · '.join(f'<b>{a}</b>' if a == actual else f'<a href="{corp}-{a}.html" style="color:inherit">{a}</a>'
                       for a in TODOS)
    return f'<span class="meta-item" id="{span}">Año: {links}</span>'


def restos_2026(t):
    return [m.group(0) for m in re.finditer(r'.{0,40}2026.{0,40}', t)
            if not re.search(r'elecciones-2026|congreso-2026|mapas-2026|endoso-2026|camara-2026|senado-2026\.html|'
                             r'SENADO_2026|Electos 2026', m.group(0))]


def reemplazar(t, a, b, n=None):
    c = t.count(a)
    if c == 0 or (n is not None and c != n):
        raise SystemExit(f'la plantilla no trae {a[:70]!r} ({c} veces)')
    return t.replace(a, b)


def generar(anio, plantilla):
    f = ANIOS[anio]
    cerradas = json.loads((DATOS / f'senado-{anio}' / 'listas_cerradas.json').read_text())
    t = plantilla
    pares = [
        # títulos y textos
        ('Escrutinio Senado 2026', f'Escrutinio Senado {anio}'),
        ('Senate Scrutiny 2026', f'Senate Scrutiny {anio}'),
        ('Senate Official Count 2026', f'Senate Official Count {anio}'),
        ('参议院计票 2026', f'参议院计票 {anio}'),
        ('参议院官方计票 2026', f'参议院官方计票 {anio}'),
        ('Escrutinio · 2026', f'Escrutinio · {anio}'),
        ('Congreso · Declaratoria CNE 13 jul 2026', f"Congreso · Escrutinio · {f['es']}"),
        ('Congress · CNE declaration Jul 13, 2026', f"Congress · Official count · {f['en']}"),
        ('国会 · 全国选举委员会宣告 2026年7月13日', f"国会 · 官方计票 · {f['zh']}"),
        ('Fuente: <b>CNE · Res. E-3328</b>', 'Fuente: <b>Registraduría · Escrutinio</b>'),
        ('Source: <b>CNE · Res. E-3328</b>', 'Source: <b>Registraduría · Official count</b>'),
        ('来源: <b>CNE · E-3328号决议</b>', '来源: <b>国家民事登记处 · 官方计票</b>'),
        ('ricardoruiz.co · Elecciones Colombia 2026', f'ricardoruiz.co · Elecciones Colombia {anio}'),
        ('ricardoruiz.co · Colombia Elections 2026', f'ricardoruiz.co · Colombia Elections {anio}'),
        ('ricardoruiz.co · 哥伦比亚选举 2026', f'ricardoruiz.co · 哥伦比亚选举 {anio}'),
        ('Totales nacionales: CNE, Res. E-3328 (13 jul 2026) · Detalle territorial: comisiones escrutadoras, Registraduría',
         'Escrutinio de la Registraduría (consolidado mesa a mesa) · Electos: voto preferente del escrutinio; '
         'pueden diferir de la declaratoria por fallos posteriores'),
        ('National totals: CNE, Res. E-3328 (Jul 13, 2026) · Territorial detail: scrutiny commissions, Registraduría',
         'Registraduría official count (station-level consolidated file) · Elected: preferential vote in the count; '
         'later court rulings may differ'),
        ('全国总数：全国选举委员会 E-3328号决议（2026年7月13日）· 地区明细：计票委员会，国家民事登记处',
         '国家民事登记处官方计票（逐投票站汇总）· 当选者按优先票计算，后续裁决可能不同'),
        # datos de ese año
        ('${S3}/senado/${nivel}.json', f'${{S3}}/senado-{anio}/${{nivel}}.json'),
        ('${S3}/senado/departamentos/${depCod}/${nivel}.json', f'${{S3}}/senado-{anio}/departamentos/${{depCod}}/${{nivel}}.json'),
        ('const COMUNAS_CSV_URL = `${S3}/Divipole-actualizado/COMUNAS_DATA.csv`;',
         f'const COMUNAS_CSV_URL = `${{S3}}/senado-{anio}/censo.csv`;   // censo de esa elección; 2014 no tiene'),
        ('login.html?redirect=senado-2026.html', f'login.html?redirect=senado-{anio}.html'),
        ("if(/nuevo liberalismo/i.test(n))return'#E53935';return'#555';}",
         "if(/nuevo liberalismo/i.test(n))return'#E53935';" + COLORES_EXTRA + "return'#555';}"),
    ]
    for a, b in pares:
        t = reemplazar(t, a, b)
    # selector de año en la barra superior
    t, n = re.subn(r'<span class="meta-item" id="sn-meta-anio">.*?</span>', lambda m: selector(anio), t, count=1)
    if n != 1:
        raise SystemExit('la plantilla no trae el selector de año (sn-meta-anio)')
    # el endoso es solo de 2026
    t, n = re.subn(r'\n        <div class="endoso-cta">.*?</a>\n        </div>', '', t, count=1, flags=re.S)
    if n != 1:
        raise SystemExit('no encontré el bloque del endoso')
    # listas cerradas del año
    i = t.index('    const CLOSED_LISTS = {')
    j = t.index('\n    };', i) + len('\n    };')
    nuevo = '    const CLOSED_LISTS = {\n' + ''.join(
        f'      {json.dumps(k, ensure_ascii=False)}:{json.dumps(v, ensure_ascii=False)},\n' for k, v in cerradas.items()) + '    };'
    t = t[:i] + nuevo + t[j:]
    restos = restos_2026(t)
    out = RAIZ / f'senado-{anio}.html'
    out.write_text(t)
    print(f'{out.name}: {len(t) // 1024} KB · listas cerradas {list(cerradas)} · restos de 2026: {len(restos)}')
    for r in restos[:12]:
        print('    ', r.strip())


# ─── Cámara ────────────────────────────────────────────────────────────────────────────────
# curules que se eligen con el voto de estas circunscripciones (territorial, exterior, indígena, afro)
CAM_CURULES = {'2022': (162, 165), '2018': (162, 165), '2014': (163, 166)}   # (territoriales, total)
CAM_NOTA = {
    '2022': ('No incluye las 16 curules CITREP, las 5 de Comunes ni la del estatuto de oposición. '
             '<b>San Andrés:</b> con el consolidado del escrutinio la segunda curul es de Cambio Radical '
             '(6.725 votos contra 6.612 de la coalición La U–Colombia Justa Libres), pero en la lista oficial de '
             'electos esa curul es de la coalición (Carlos Alberto Bryan Uribe).'),
    '2018': 'No incluye las 5 curules del partido FARC (Acuerdo de Paz) ni la del estatuto de oposición.',
    '2014': ('En 2014 el exterior elegía 2 representantes; desde 2018 elige 1. <b>Afro:</b> ese año rigió el umbral '
             'del 30 % del cuociente y FUNECO, la única lista que lo pasó, se quedó con las dos curules.'),
}
NOTA_COMUN = ('Escrutinio de la Registraduría (consolidado mesa a mesa). Los electos de lista abierta salen del '
              'voto preferente de ese consolidado y pueden diferir de la declaratoria por recuentos y decisiones '
              'posteriores; los de lista cerrada, de la lista oficial de electos. ')


def generar_camara(anio, plantilla):
    f = ANIOS[anio]
    terr, total = CAM_CURULES[anio]
    cerradas = json.loads((DATOS / f'camara-{anio}' / 'listas_cerradas.json').read_text())['territorial']
    t = plantilla
    pares = [
        ('Escrutinio Cámara 2026', f'Escrutinio Cámara {anio}'),
        ('House of Representatives 2026', f'House of Representatives {anio}'),
        ('House Official Count 2026', f'House Official Count {anio}'),
        ('众议院计票 2026', f'众议院计票 {anio}'),
        ('众议院官方计票 2026', f'众议院官方计票 {anio}'),
        ('Escrutinio · 2026', f'Escrutinio · {anio}'),
        ('Congreso · Declaratorias 2026 (CNE jul)', f"Congreso · Escrutinio · {f['es']}"),
        ('Congress · 2026 declarations (CNE Jul)', f"Congress · Official count · {f['en']}"),
        ('国会 · 2026年当选宣告（7月全国选举委员会）', f"国会 · 官方计票 · {f['zh']}"),
        ('Curules: <b>166</b>', f'Curules: <b>{total}</b>'),
        ('Seats: <b>166</b>', f'Seats: <b>{total}</b>'),
        ('席位: <b>166</b>', f'席位: <b>{total}</b>'),
        ("Partidos · Cámara · Nacional · 166 curules · D'Hondt por depto.",
         f"Partidos · Cámara · Nacional · {terr} curules · D'Hondt por depto."),
        ('const CURULES_TOTAL = 166;', f'const CURULES_TOTAL = {total};'),
        ('Fuente: <b>Registraduría · CNE</b>', 'Fuente: <b>Registraduría · Escrutinio</b>'),
        ('Source: <b>Registraduría · CNE</b>', 'Source: <b>Registraduría · Official count</b>'),
        ('来源: <b>Registraduría · 全国选举委员会</b>', '来源: <b>国家民事登记处 · 官方计票</b>'),
        ('ricardoruiz.co · Elecciones Colombia 2026', f'ricardoruiz.co · Elecciones Colombia {anio}'),
        ('ricardoruiz.co · Colombia Elections 2026', f'ricardoruiz.co · Colombia Elections {anio}'),
        ('ricardoruiz.co · 哥伦比亚选举 2026', f'ricardoruiz.co · 哥伦比亚选举 {anio}'),
        ('Fuente: E-26 de las comisiones escrutadoras (Registraduría) · Chocó, Cundinamarca y Afro: E-26 del CNE (jul 2026)',
         'Registraduría · consolidado del escrutinio (mesa a mesa) · Electos de lista abierta: voto preferente'),
        ('Source: E-26 forms of the scrutiny commissions (Registraduría) · Chocó, Cundinamarca and Afro: CNE E-26 (Jul 2026)',
         'Registraduría · official count (station-level consolidated file) · Open lists: preferential vote'),
        ('来源：计票委员会 E-26 表（国家民事登记处）· 乔科、昆迪纳马卡和非裔选区：全国选举委员会 E-26（2026年7月）',
         '来源：国家民事登记处官方计票（逐投票站汇总）· 开放名单按优先票'),
        ('${S3}/camara/${nivel}.json', f'${{S3}}/camara-{anio}/${{nivel}}.json'),
        ('${S3}/camara/dep-${depCod}/com-${munCod}-${comCod}.json',
         f'${{S3}}/camara-{anio}/dep-${{depCod}}/com-${{munCod}}-${{comCod}}.json'),
        ('const COMUNAS_CSV_URL = `${S3}/Divipole-actualizado/COMUNAS_DATA.csv`;',
         f'const COMUNAS_CSV_URL = `${{S3}}/camara-{anio}/censo.csv`;   // censo de esa elección; 2014 no tiene'),
        ('login.html?redirect=camara-2026.html', f'login.html?redirect=camara-{anio}.html'),
        ("if(/nuevo liberalismo/i.test(n))return'#E53935';return'#555';}",
         "if(/nuevo liberalismo/i.test(n))return'#E53935';" + COLORES_EXTRA + "return'#555';}"),
    ]
    if anio == '2014':
        pares.append(("'CONSULADOS':1,", "'CONSULADOS':2,"))
        pares.append(('const AFRO_UMBRAL = false;', 'const AFRO_UMBRAL = true;'))
    for a, b in pares:
        t = reemplazar(t, a, b)
    t, n = re.subn(r'<span class="meta-item" id="cam-meta-anio">.*?</span>',
                   lambda m: selector(anio, 'camara', 'cam-meta-anio'), t, count=1)
    if n != 1:
        raise SystemExit('la plantilla no trae el selector de año (cam-meta-anio)')
    t, n = re.subn(r'\n        <div class="endoso-cta">.*?</a>\n        </div>', '', t, count=1, flags=re.S)
    if n != 1:
        raise SystemExit('no encontré el bloque del endoso')
    # nota del año, debajo de la barra de datos
    nota = (f'\n    <div class="cam-nota-anio" style="margin:.2rem 2.5rem 1rem;font-size:.8rem;line-height:1.55;'
            f'color:rgba(255,255,255,.5);max-width:62rem">{NOTA_COMUN}{CAM_NOTA[anio]}</div>')
    t = reemplazar(t, '\n    <div class="content-area">', nota + '\n    <div class="content-area">', n=1)
    # listas cerradas del año: por departamento y de la circunscripción afro
    i = t.index('    const CLOSED_LISTS = {')
    j = t.index('\n    };', i) + len('\n    };')
    cuerpo = ''.join(f'      {json.dumps(dep)}: {{\n' + ''.join(
        f'        {json.dumps(p, ensure_ascii=False)}:{json.dumps(v, ensure_ascii=False)},\n' for p, v in ls.items()) + '      },\n'
        for dep, ls in sorted(cerradas.items()))
    t = t[:i] + ('    // Elegidos de listas cerradas: lista oficial de electos (ver tools/build-congreso-escr/'
                 'camara_listas_cerradas.json)\n    const CLOSED_LISTS = {\n') + cuerpo + '    };' + t[j:]
    lc = json.loads((Path(__file__).with_name('camara_listas_cerradas.json')).read_text())
    afro = {k.split('|', 1)[1]: v for k, v in lc.get('afro', {}).items() if k.startswith(anio + '|')}
    i = t.index('    const AFRO_CLOSED_LISTS = {')
    j = t.index('\n    };', i) + len('\n    };')
    t = t[:i] + '    const AFRO_CLOSED_LISTS = ' + json.dumps(afro, ensure_ascii=False) + ';' + t[j:]
    restos = restos_2026(t)
    out = RAIZ / f'camara-{anio}.html'
    out.write_text(t)
    print(f'{out.name}: {len(t) // 1024} KB · listas cerradas en {len(cerradas)} departamentos · restos de 2026: {len(restos)}')
    for r in restos[:12]:
        print('    ', r.strip())


def main():
    corps = [c for c in ('senado', 'camara') if c in sys.argv[1:]] or ['senado', 'camara']
    anios = [a for a in sys.argv[1:] if a in ANIOS] or list(ANIOS)
    for c in corps:
        plantilla = (RAIZ / f'{c}-2026.html').read_text()
        for a in anios:
            (generar if c == 'senado' else generar_camara)(a, plantilla)


if __name__ == '__main__':
    main()
