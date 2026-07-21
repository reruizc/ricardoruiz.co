#!/usr/bin/env python3
"""
Caudal · Fase 3 — enumerador COMPLETO de Gaceta del Congreso (Senado + Cámara
combinados: es UNA sola numeración compartida por año, "Gaceta del Congreso
No. N de AAAA", confirmado jul-2026 — no hace falta pasar por Entidad).

Pagina el buscador JSF de la Imprenta (mismo mecanismo que
harvest_actas_plenaria_senado.py) SIN filtro de Entidad ni Documento, ordenado
por fecha DESC, y para hasta cruzar la fecha de corte (--desde). Escribe
{num, entidad, fecha_iso} por fila a un JSONL resumible.

Uso:
  python3 tools/caudal/actas/enumerar_gacetas.py --desde 2020-01-01
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / 'Bases de datos' / 'leyes-senado' / 'actas' / 'gacetas-index.jsonl'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120 Safari/537.36')
BASE = 'http://svrpubindc.imprenta.gov.co/senado'
DT = 'formResumen:dataTableResumen'
CK = '/tmp/_caudal_enum_ck.txt'
ROWS = 100

ROW_RE = re.compile(
    r'<label[^>]*>(\d+)</label></td><td[^>]*><label[^>]*>([^<]*)'
    r'</label></td><td[^>]*><label[^>]*>([\d/]+)</label>')


def curl(args):
    return subprocess.run(['/usr/bin/curl', '-s', '-A', UA] + args,
                          capture_output=True, timeout=90).stdout.decode('utf-8', 'replace')


def fresh_vs():
    page = curl(['-c', CK, f'{BASE}/index.xhtml'])
    m = re.search(r'name="javax.faces.ViewState"[^>]*value="([^"]+)"', page)
    return m.group(1) if m else None


def post(vs, extra):
    data = extra + [
        ('javax.faces.partial.ajax', 'true'),
        ('javax.faces.source', DT),
        ('javax.faces.partial.execute', DT),
        ('javax.faces.partial.render', DT),
        (DT, DT),
        (f'{DT}:j_idt13:filter', ''),
        (f'{DT}:j_idt16_input', ''),
        (f'{DT}:calFechaGaceta_input', ''),
        (f'{DT}:j_idt22:filter', ''),
        ('formResumen', 'formResumen'),
        ('javax.faces.ViewState', vs),
    ]
    args = ['-b', CK, '-X', 'POST', f'{BASE}/index.xhtml',
            '-H', 'Faces-Request: partial/ajax',
            '-H', 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8']
    for k, v in data:
        args += ['--data-urlencode', f'{k}={v}']
    return curl(args)


def to_iso(dmy):
    d, m, y = dmy.split('/')
    return f'{y}-{m}-{d}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--desde', default='2020-01-01')
    ap.add_argument('--sleep', type=float, default=0.3)
    args = ap.parse_args()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    vs = fresh_vs()
    if not vs:
        print('no pude leer ViewState (¿portal caído?)', file=sys.stderr)
        sys.exit(1)
    post(vs, [(f'{DT}_filtering', 'true'), (f'{DT}_encodeFeature', 'true')])

    seen, rows_out, first = set(), [], 0
    por_anio = {}
    under_cutoff_streak = 0
    while True:
        html = post(vs, [(f'{DT}_pagination', 'true'), (f'{DT}_first', str(first)),
                         (f'{DT}_rows', str(ROWS)), (f'{DT}_encodeFeature', 'true')])
        rows = ROW_RE.findall(html)
        if not rows:
            break
        page_min_iso = None
        for num, entidad, dmy in rows:
            iso = to_iso(dmy)
            page_min_iso = iso if page_min_iso is None or iso < page_min_iso else page_min_iso
            key = (num, iso)
            if key in seen:
                continue
            seen.add(key)
            rows_out.append({'num': int(num), 'entidad': entidad.strip(),
                             'fecha': iso, 'anio': int(iso[:4])})
            por_anio[iso[:4]] = por_anio.get(iso[:4], 0) + 1
        first += ROWS
        print(f'  …{len(rows_out)} filas · página hasta {page_min_iso}', end='\r')
        if page_min_iso and page_min_iso < args.desde:
            under_cutoff_streak += 1
            if under_cutoff_streak >= 2:   # 2 páginas seguidas bajo el corte → paramos
                break
        else:
            under_cutoff_streak = 0
        time.sleep(args.sleep)

    rows_out.sort(key=lambda r: (r['fecha'], r['num']))
    with open(OUT, 'w', encoding='utf-8') as f:
        for r in rows_out:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    print()
    print(f'\n{len(rows_out)} gacetas enumeradas → {OUT.relative_to(REPO)}')
    for a in sorted(por_anio):
        print(f'  {a}: {por_anio[a]}')
    n_desde = sum(1 for r in rows_out if r['fecha'] >= args.desde)
    print(f'\n{n_desde} gacetas desde {args.desde}')


if __name__ == '__main__':
    main()
