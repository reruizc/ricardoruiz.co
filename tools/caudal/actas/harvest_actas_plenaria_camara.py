#!/usr/bin/env python3
"""
Caudal · Fase 3 — harvester de ACTAS DE PLENARIA de Cámara (voto nominal).

Fuente real: camara.gov.co/secretaria-general/actas-votaciones-y-otros/ esconde
un widget AJAX (admin-ajax.php, action=get_actas_y_otros_page) que es el índice
sesión→acta→gaceta que el portal JSF de la Imprenta no da. Cada acta trae un
`enlace` de descarga DIRECTA (sin JSF, sin postback) — normalmente un ZIP con
los PDFs de asistencia + voto nominal electrónico de esa sesión.

Cobertura verificada (jul-2026): 1.400 actas 2010-2026. El formato del `enlace`
cambia con los años — ver parse_votaciones_camara.py para el detalle de eras:
  - ~2010-medios 2021: imágenes escaneadas (sin texto extraíble) → requiere OCR.
  - ~ago-2021 a ~sep-2022: ZIP fragmentado, 1 PDF por votación, votantes
    identificados por EMAIL (nombre.apellido@camara.gov.co), no por nombre.
  - ~oct-2022 en adelante: ZIP consolidado, 1 PDF con TODAS las votaciones de
    la sesión, tabla nominal con nombre completo Apellidos-Nombres.

Uso:
  python3 tools/caudal/actas/harvest_actas_plenaria_camara.py index
  python3 tools/caudal/actas/harvest_actas_plenaria_camara.py download [--workers 4] [--desde YYYY-MM-DD]
"""
import subprocess, json, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / 'Bases de datos' / 'leyes-senado' / 'actas' / 'plenaria-camara'
IDX_DIR = SRC / 'index'
RAW_DIR = SRC / 'raw'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
AJAX_URL = 'https://www.camara.gov.co/wp-admin/admin-ajax.php'
HOME_URL = 'https://www.camara.gov.co'
# nonce público de 24h leído de la página; si expira, volver a extraerlo de
# window.AP_CFG en https://www.camara.gov.co/secretaria-general/actas-votaciones-y-otros/
NONCE = '59752ffeba'
COMISION = 'Secretaría General'
PER_PAGE = 50


def curl(*args, out=None, timeout=60):
    a = ['/usr/bin/curl', '-s', '-A', UA, '--max-time', str(timeout)]
    if out:
        a += ['-o', out]
    a += list(args)
    r = subprocess.run(a, capture_output=True)
    return r.stdout.decode('utf-8', errors='replace')


def fetch_page(page):
    body = curl(
        '-X', 'POST', AJAX_URL,
        '--data-urlencode', 'action=get_actas_y_otros_page',
        '--data-urlencode', f'_ajax_nonce={NONCE}',
        '--data-urlencode', f'page={page}',
        '--data-urlencode', f'per_page={PER_PAGE}',
        '--data-urlencode', 'term=',
        '--data-urlencode', 'tipo=All',
        '--data-urlencode', f'comision={COMISION}',
        '--data-urlencode', 'fecha_desde=',
        '--data-urlencode', 'fecha_hasta=',
    )
    return json.loads(body)


def cmd_index():
    IDX_DIR.mkdir(parents=True, exist_ok=True)
    items, page, total_pages = [], 1, None
    while True:
        d = fetch_page(page)
        if not d.get('success'):
            print('fallo página', page, d)
            break
        batch = d['data']['items']
        items += batch
        total_pages = d['data']['total_pages']
        if page == 1 or page % 20 == 0 or page >= total_pages:
            print(f'  página {page}/{total_pages} · acumulado {len(items)}')
        if page >= total_pages or not batch:
            break
        page += 1
    outf = IDX_DIR / 'indice-completo.json'
    json.dump(items, open(outf, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n{len(items)} actas de plenaria → {outf.relative_to(REPO)}')


def _ext_of(enlace):
    e = (enlace or '').lower()
    if '.' in e.rsplit('/', 1)[-1]:
        return e.rsplit('.', 1)[-1].split('?')[0]
    return 'bin'


def _download_one(it):
    aid = it['id']
    enlace = it.get('enlace') or ''
    if not enlace:
        return aid, 'sin-enlace'
    ext = _ext_of(enlace)
    fn = RAW_DIR / f'{aid}.{ext}'
    if fn.exists() and fn.stat().st_size > 200:
        return aid, 'cache'
    url = enlace if enlace.startswith('http') else HOME_URL + enlace
    curl(url, out=str(fn), timeout=120)
    if not fn.exists() or fn.stat().st_size < 200:
        return aid, 'error'
    return aid, 'ok'


def cmd_download(workers=4, desde=None):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    items = json.load(open(IDX_DIR / 'indice-completo.json', encoding='utf-8'))
    if desde:
        items = [it for it in items if (it.get('fecha_iso') or '9999') >= desde]
    print(f'{len(items)} actas a procesar (workers={workers})')
    stats = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_download_one, it): it for it in items}
        done = 0
        for fut in as_completed(futs):
            aid, status = fut.result()
            stats[status] = stats.get(status, 0) + 1
            done += 1
            if done % 100 == 0:
                print(f'  …{done}/{len(items)}  {stats}')
    print('\nresultado:', stats)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'index'
    workers = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 4
    desde = sys.argv[sys.argv.index('--desde') + 1] if '--desde' in sys.argv else None
    if cmd == 'index':
        cmd_index()
    elif cmd == 'download':
        cmd_download(workers=workers, desde=desde)
    else:
        print('uso: index | download [--workers N] [--desde YYYY-MM-DD]')
