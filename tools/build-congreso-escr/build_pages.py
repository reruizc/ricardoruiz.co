#!/usr/bin/env python3
"""Genera senado-2014/2018/2022.html a partir de senado-2026.html (la plantilla).

  python3 tools/build-congreso-escr/build_pages.py

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


def selector(actual):
    links = ' · '.join(f'<b>{a}</b>' if a == actual else f'<a href="senado-{a}.html" style="color:inherit">{a}</a>'
                       for a in TODOS)
    return f'<span class="meta-item" id="sn-meta-anio">Año: {links}</span>'


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
    restos = [m.group(0) for m in re.finditer(r'.{0,40}2026.{0,40}', t)
              if not re.search(r'elecciones-2026|congreso-2026|mapas-2026|endoso-2026|camara-2026|senado-2026\.html|SENADO_2026|Electos 2026', m.group(0))]
    out = RAIZ / f'senado-{anio}.html'
    out.write_text(t)
    print(f'{out.name}: {len(t) // 1024} KB · listas cerradas {list(cerradas)} · restos de 2026: {len(restos)}')
    for r in restos[:12]:
        print('    ', r.strip())


def main():
    plantilla = (RAIZ / 'senado-2026.html').read_text()
    for a in (sys.argv[1:] or ANIOS):
        generar(a, plantilla)


if __name__ == '__main__':
    main()
