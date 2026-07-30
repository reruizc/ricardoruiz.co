#!/usr/bin/env python3
"""
Caudal · Fase 3 — enumerador COMPLETO de Gaceta del Congreso (Senado + Cámara
combinados: es UNA sola numeración compartida por año, "Gaceta del Congreso
No. N de AAAA", confirmado jul-2026 — no hace falta pasar por Entidad).

Pagina el buscador JSF de la Imprenta (mismo mecanismo que
harvest_actas_plenaria_senado.py) SIN filtro de Entidad ni Documento, ordenado
por fecha DESC, y para hasta cruzar la fecha de corte (--desde). Escribe
{num, entidad, fecha_iso} por fila a un JSONL resumible.

MERGE-SAFE (jul-2026): ya NO clobbea el índice. Al escribir, fusiona con las
filas que ya estaban en OUT (dedup por (num, fecha)). Así una corrida truncada
—p.ej. el WAF de la Imprenta banea ~10 min a mitad del barrido de 300 páginas
que hace falta para llegar a pre-2006— nunca pierde lo ya enumerado. Checkpointea
cada CHECKPOINT_PAGES páginas. Para reanudar tras un corte, `--first N` arranca
la paginación en la fila N (la portada del listado es date-DESC, así que un N
alto = más viejo).

Uso:
  python3 tools/caudal/actas/enumerar_gacetas.py --desde 2020-01-01
  # extender a pre-2006 (baja hasta el piso real del portal, ~2001):
  python3 tools/caudal/actas/enumerar_gacetas.py --desde 1990-01-01
  python3 tools/caudal/actas/enumerar_gacetas.py --desde 1990-01-01 --first 24000  # reanudar
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
CHECKPOINT_PAGES = 20   # cada cuántas páginas se vuelca el índice a disco

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


def load_existing():
    """Filas ya enumeradas, keyeadas por (num, fecha) — base del merge."""
    out = {}
    if OUT.exists():
        for line in open(OUT, encoding='utf-8'):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue          # línea truncada por un corte a mitad de write
            out[(r['num'], r['fecha'])] = r
    return out


def flush(acc):
    """Vuelca el acumulado (dict (num,fecha)->fila) ordenado. Escritura atómica:
    a un .tmp y luego replace — si el proceso muere a mitad, el índice viejo
    sobrevive intacto en vez de quedar truncado."""
    rows = sorted(acc.values(), key=lambda r: (r['fecha'], r['num']))
    tmp = OUT.with_suffix('.jsonl.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    tmp.replace(OUT)
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--desde', default='2020-01-01')
    ap.add_argument('--sleep', type=float, default=0.3)
    ap.add_argument('--first', type=int, default=0,
                    help='fila inicial de la paginación (para reanudar tras un corte; '
                         'el listado es fecha-DESC → N alto = más viejo)')
    ap.add_argument('--max-empty', type=int, default=3,
                    help='páginas vacías seguidas antes de rendirse (el portal devuelve '
                         'vacío transitorio bajo WAF, no siempre es el fondo del listado)')
    args = ap.parse_args()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    acc = load_existing()
    if acc:
        print(f'· {len(acc)} filas ya en el índice (se fusionan, no se pisan)')
    n_antes = len(acc)

    vs = fresh_vs()
    if not vs:
        print('no pude leer ViewState (¿portal caído?)', file=sys.stderr)
        sys.exit(1)
    post(vs, [(f'{DT}_filtering', 'true'), (f'{DT}_encodeFeature', 'true')])

    first = args.first
    under_cutoff_streak = 0
    empty_streak = 0
    pages = 0
    try:
        while True:
            html = post(vs, [(f'{DT}_pagination', 'true'), (f'{DT}_first', str(first)),
                             (f'{DT}_rows', str(ROWS)), (f'{DT}_encodeFeature', 'true')])
            rows = ROW_RE.findall(html)
            if not rows:
                # una página vacía puede ser el fondo real O un hipo del portal
                # (WAF / ViewState expirado). Reintentar con ViewState fresco
                # antes de declarar terminado.
                empty_streak += 1
                if empty_streak >= args.max_empty:
                    print(f'\n· {empty_streak} páginas vacías seguidas en first={first} → fin')
                    break
                print(f'\n· página vacía en first={first} ({empty_streak}/{args.max_empty}), '
                      'renovando sesión y reintentando…')
                time.sleep(5)
                nvs = fresh_vs()
                if nvs:
                    vs = nvs
                    post(vs, [(f'{DT}_filtering', 'true'), (f'{DT}_encodeFeature', 'true')])
                continue
            empty_streak = 0
            page_min_iso = None
            for num, entidad, dmy in rows:
                iso = to_iso(dmy)
                page_min_iso = iso if page_min_iso is None or iso < page_min_iso else page_min_iso
                acc[(int(num), iso)] = {'num': int(num), 'entidad': entidad.strip(),
                                        'fecha': iso, 'anio': int(iso[:4])}
            first += ROWS
            pages += 1
            print(f'  …{len(acc)} filas · first={first} · página hasta {page_min_iso}', end='\r')
            if pages % CHECKPOINT_PAGES == 0:
                flush(acc)
            if page_min_iso and page_min_iso < args.desde:
                under_cutoff_streak += 1
                if under_cutoff_streak >= 2:   # 2 páginas seguidas bajo el corte → paramos
                    break
            else:
                under_cutoff_streak = 0
            time.sleep(args.sleep)
    except KeyboardInterrupt:
        print('\n· interrumpido — volcando lo enumerado hasta aquí')

    total = flush(acc)
    por_anio = {}
    for r in acc.values():
        por_anio[r['fecha'][:4]] = por_anio.get(r['fecha'][:4], 0) + 1

    print()
    print(f'\n{total} gacetas en el índice ({total - n_antes} nuevas) → {OUT.relative_to(REPO)}')
    for a in sorted(por_anio):
        print(f'  {a}: {por_anio[a]}')
    n_desde = sum(1 for r in acc.values() if r['fecha'] >= args.desde)
    print(f'\n{n_desde} gacetas desde {args.desde}')
    print(f'última página: first={first} (para reanudar: --first {first})')


if __name__ == '__main__':
    main()
