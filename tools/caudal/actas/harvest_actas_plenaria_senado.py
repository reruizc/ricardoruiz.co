#!/usr/bin/env python3
"""
Caudal · Fase 3 — enumerador de ACTAS DE PLENARIA del SENADO (voto nominal).

A diferencia de Cámara (que tiene un índice AJAX limpio en camara.gov.co con
export electrónico de votación), el Senado NO exporta un registro electrónico:
sus votos nominales viven en el ACTA NARRATIVA publicada en la Gaceta del
Congreso (formato "Por el Sí: N … Honorables Senadores por el SÍ: [apellidos]",
como el acta 1069/2019 que la acción `gaceta` del Lambda parseó — 84 senadores).

**MECÁNICA CRACKEADA pero FILTRO INSERVIBLE (verificado jul-2026):**
El buscador (svrpubindc.imprenta.gov.co/senado/index.xhtml) es una dataTable
PrimeFaces lazy (31k gacetas). El POST parcial de filtro/paginación SÍ se scripta
(Entidad="Senado de la República" + `_filtering=true`, luego `_pagination=true`
+`_first`, fecha DESC). PERO:
  - La columna "Documento" se renderiza VACÍA en el listado → desde la lista solo
    hay (num, entidad, fecha), NO el tipo de documento.
  - El filtro Documento es FUZZY e inservible para aislar actas de plenaria: con
    `plenaria` devuelve mayormente PONENCIAS y órdenes del día; con `acta de
    plenaria` devuelve hasta gacetas de "ACTAS DE COMISIÓN" (verificado: gaceta
    787/2026 sale de primera con ese filtro y es comisión, 0 roll-call).
  - O sea: NO hay un filtro que dé limpio las actas de sesión de plenaria con
    votación nominal. El `index` de abajo produce CANDIDATOS ruidosos, no actas.

**Conclusión operativa:** para Senado la vía realista es TARGETED, no bulk. Para
un voto concreto (una reforma, un senador): saber la FECHA de la sesión → bajar
las gacetas candidatas de esa ventana → quedarse con la de masthead "ACTAS DE
PLENARIA" que traiga el patrón "Por el Sí"/"Honorables Senadores" → parsear con
la acción `gaceta` del Lambda → cruzar con `electos-2026-2030.json`. La
clasificación (acta vs ponencia vs comisión) exige DESCARGAR y leer el masthead
de la página 1, porque el listado no lo dice. Un harvest exhaustivo sería bajar
cientos de gacetas grandes y clasificarlas a mano — caro y ruidoso; no vale la
pena vs. el cross-check que ya da Congreso a la mano para preguntas puntuales.

Uso (produce CANDIDATOS, requiere descarga+clasificación posterior):
  python3 tools/caudal/actas/harvest_actas_plenaria_senado.py index [--desde D-M-YYYY] [--filtro plenaria]
"""
import subprocess, re, json, sys, time
from pathlib import Path
from datetime import date

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / 'Bases de datos' / 'leyes-senado' / 'actas' / 'plenaria-senado' / 'index'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120 Safari/537.36')
BASE = 'http://svrpubindc.imprenta.gov.co/senado'
DT = 'formResumen:dataTableResumen'
CK = '/tmp/_caudal_senado_ck.txt'
ENTIDAD = 'Senado de la República'


def curl(args):
    return subprocess.run(['/usr/bin/curl', '-s', '-A', UA] + args,
                          capture_output=True, timeout=120).stdout.decode('utf-8', 'replace')


def _fresh_viewstate():
    page = curl(['-c', CK, f'{BASE}/index.xhtml'])
    m = re.search(r'name="javax.faces.ViewState"[^>]*value="([^"]+)"', page)
    return m.group(1) if m else None


def _post(vs, doc, extra):
    """POST parcial de PrimeFaces preservando el filtro Entidad+Documento."""
    data = extra + [
        ('javax.faces.partial.ajax', 'true'),
        ('javax.faces.source', DT),
        ('javax.faces.partial.execute', DT),
        ('javax.faces.partial.render', DT),
        (DT, DT),
        (f'{DT}:j_idt13:filter', ''),
        (f'{DT}:j_idt16_input', ENTIDAD),
        (f'{DT}:calFechaGaceta_input', ''),
        (f'{DT}:j_idt22:filter', doc),
        ('formResumen', 'formResumen'),
        ('javax.faces.ViewState', vs),
    ]
    args = ['-b', CK, '-X', 'POST', f'{BASE}/index.xhtml',
            '-H', 'Faces-Request: partial/ajax',
            '-H', 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8']
    for k, v in data:
        args += ['--data-urlencode', f'{k}={v}']
    return curl(args)


ROW_RE = re.compile(
    r'<label[^>]*>(\d+)</label></td><td[^>]*><label[^>]*>Senado de la República'
    r'</label></td><td[^>]*><label[^>]*>([\d/]+)</label>')


def _parse_rows(html):
    return ROW_RE.findall(html)  # [(num, 'DD/MM/YYYY'), ...]


def _to_iso(dmy):
    d, m, y = dmy.split('/')
    return f'{y}-{m}-{d}'


def cmd_index(desde_iso='2022-07-20', doc='plenaria'):
    OUT.mkdir(parents=True, exist_ok=True)
    vs = _fresh_viewstate()
    if not vs:
        print('no pude leer ViewState (¿portal caído?)'); return
    # aplicar filtro (primera vez)
    _post(vs, doc, [(f'{DT}_filtering', 'true'), (f'{DT}_encodeFeature', 'true')])
    seen, out, first = set(), [], 0
    while True:
        html = _post(vs, doc, [(f'{DT}_pagination', 'true'), (f'{DT}_first', str(first)),
                               (f'{DT}_rows', '10'), (f'{DT}_encodeFeature', 'true')])
        rows = _parse_rows(html)
        if not rows:
            break
        stop = False
        for num, dmy in rows:
            iso = _to_iso(dmy)
            key = (num, iso)
            if key in seen:
                continue
            seen.add(key)
            if iso < desde_iso:
                stop = True
                continue
            out.append({'gaceta': num, 'fecha': dmy, 'fecha_iso': iso, 'entidad': 'Senado'})
        if stop:
            break
        first += 10
        if first > 2000:      # backstop
            break
        time.sleep(0.3)
    out.sort(key=lambda r: r['fecha_iso'])
    outf = OUT / f'index-senado-{doc}.json'
    json.dump(out, open(outf, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    yrs = {}
    for r in out:
        yrs[r['fecha_iso'][:4]] = yrs.get(r['fecha_iso'][:4], 0) + 1
    print(f'{len(out)} gacetas de "{doc}" del Senado desde {desde_iso}')
    print('por año:', yrs)
    print(f'→ {outf.relative_to(REPO)}')


if __name__ == '__main__':
    desde = sys.argv[sys.argv.index('--desde') + 1] if '--desde' in sys.argv else '20-7-2022'
    d, m, y = desde.split('-')
    desde_iso = f'{y}-{int(m):02d}-{int(d):02d}'
    doc = sys.argv[sys.argv.index('--filtro') + 1] if '--filtro' in sys.argv else 'plenaria'
    cmd_index(desde_iso, doc)
