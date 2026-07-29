#!/usr/bin/env python3
"""
Cosecha el HISTÓRICO de proyectos de ley y actos legislativos de la CÁMARA
(camara.gov.co), legislatura por legislatura.

Hermano histórico de harvest_camara.py (que es el rastreador DIARIO de la
legislatura viva y solo emite novedades). Este baja el censo completo y lo deja
como insumo de build_dataset.py.

POR QUÉ EXISTE (hallazgo jul-2026)
----------------------------------
El dataset de Caudal venía SOLO del registro del Senado (leyes.senado.gov.co).
Eso deja por fuera los proyectos que nacen en Cámara y mueren ahí sin cruzar:
1.247 solo en el cuatrienio 2022-2026, el 45% del universo real. Con el Senado
solo, el cuatrienio 2022-2026 daba 1.496 proyectos de ley; el universo real
deduplicado es 2.798.

Ojo con la aritmética, que es donde se equivocan los competidores: un proyecto
que cruza de cámara tiene DOS números de radicado (p.ej. 425/2023C y 195/2022S)
y por tanto una ficha en CADA registro. Sumar los dos registros lo cuenta dos
veces (3.447 en vez de 2.798). La unión correcta es:

    proyectos de origen Senado (del registro del Senado)
  + proyectos de origen Cámara (de este registro)

build_dataset.py hace exactamente eso: solo mete los de Cámara que NO están ya
en el registro del Senado, cruzando por número+año.

MECÁNICA (idéntica a harvest_camara.py, sin navegador)
------------------------------------------------------
  1. nonce  GET /proyectos-de-ley/ → PL_CFG.PL_NONCE (caduca ~24h, ligado a IP).
  2. lista  POST wp-admin/admin-ajax.php  action=get_proyectos_ley_page
            {legislatura=<id>, page, per_page}  → {data:{items, total, total_pages}}
            ⚠ per_page está capado a 100 del lado del servidor: pedir 200 devuelve
              100 igual. Hay que paginar por total, no por el per_page pedido.

El item trae nro_camara/nro_senado/titulo/tipo/estado/origen/link_web/
comisiones_pack/autores_pack. NO trae fecha de radicación ni fechas de debate
(eso vive en la ficha individual, un GET por proyecto — pendiente, ver abajo).

Uso:
  python3 tools/leyes-senado/harvest_camara_historico.py              # todas
  python3 tools/leyes-senado/harvest_camara_historico.py --desde 2018-2019
  python3 tools/leyes-senado/harvest_camara_historico.py --legislatura 2025-2026
  python3 tools/leyes-senado/harvest_camara_historico.py --force      # ignora caché

Salidas (gitignored, en Bases de datos/leyes-senado/camara/):
  raw/{legislatura}.json   caché por legislatura (resumible: no re-baja lo que ya está)
  camara.jsonl             consolidado, 1 item por línea + campo 'legislatura'

PENDIENTE conocido: las fechas de radicación y de debates de los proyectos que
nunca cruzaron al Senado. Están en la ficha individual (GET /{link_web}), lo que
implica ~1.250 requests por cuatrienio. Sin eso, build_dataset les infiere la
etapa desde el estado textual (ver _ETAPA_POR_ESTADO allá) y les deja
fecha_presentacion en None.
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

BASE = 'https://www.camara.gov.co'
AJAX = f'{BASE}/wp-admin/admin-ajax.php'
LISTA_PAGE = f'{BASE}/proyectos-de-ley/'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / 'Bases de datos' / 'leyes-senado' / 'camara'

# id interno del dropdown legislaturaField (del HTML de /proyectos-de-ley/).
# Mismo dict que harvest_camara.py — si Cámara agrega una legislatura, va en ambos.
LEG_ID = {
    '2026-2027': '20', '2025-2026': '13', '2024-2025': '3', '2023-2024': '2',
    '2022-2023': '1', '2021-2022': '5', '2020-2021': '6', '2019-2020': '7',
    '2018-2019': '8', '2017-2018': '9', '2016-2017': '10', '2015-2016': '11',
    '2014-2015': '12', '2013-2014': '15', '2012-2013': '16', '2011-2012': '17',
    '2010-2011': '18', '2009-2010': '19', '2008-2009': '14',
}
# orden cronológico descendente (la más nueva primero)
LEGS = sorted(LEG_ID, reverse=True)

RE_NONCE = re.compile(r'PL_CFG\s*=\s*\{[^}]*?PL_NONCE\s*:\s*"([a-f0-9]+)"', re.S)
PER_PAGE = 100  # tope real del servidor; pedir más no sirve


def curl(url, post=None, timeout=90, retries=3):
    for intento in range(retries):
        cmd = ['/usr/bin/curl', '-s', '-A', UA, '--max-time', str(timeout), url]
        for k, v in (post or {}).items():
            cmd += ['--data-urlencode', f'{k}={v}']
        r = subprocess.run(cmd, capture_output=True)
        body = r.stdout.decode('utf-8', 'replace')
        if body.strip():
            return body
        if intento < retries - 1:
            time.sleep(3 * (intento + 1))
    return ''


def get_nonce():
    m = RE_NONCE.search(curl(LISTA_PAGE))
    if not m:
        sys.exit('· no pude leer el nonce de /proyectos-de-ley/ '
                 '(¿sitio caído o rate-limit? reintenta en unos minutos)')
    return m.group(1)


def bajar_legislatura(nonce, leg):
    """Todas las páginas de una legislatura. Devuelve (items, total_reportado)."""
    items, page, total = [], 1, None
    while True:
        body = curl(AJAX, {
            'action': 'get_proyectos_ley_page', 'nonce': nonce,
            'legislatura': LEG_ID[leg], 'page': str(page), 'per_page': str(PER_PAGE),
            'term': '', 'comision': '', 'tipo': '', 'estado': '', 'origen': '',
            'ley_numero': '', 'ley_fecha': '',
        })
        try:
            d = json.loads(body)['data']
        except Exception:
            print(f'  ! {leg} página {page}: respuesta ilegible ({body[:90]!r})')
            break
        total = d.get('total')
        lote = d.get('items') or []
        items += lote
        if not lote or total is None or len(items) >= total:
            break
        page += 1
        time.sleep(0.3)
    return items, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--legislatura', help='una sola (p.ej. 2025-2026)')
    ap.add_argument('--desde', help='la más vieja a bajar (p.ej. 2018-2019)')
    ap.add_argument('--force', action='store_true', help='re-baja aunque haya caché')
    a = ap.parse_args()

    legs = [a.legislatura] if a.legislatura else list(LEGS)
    if a.desde:
        legs = [L for L in legs if L >= a.desde]
    desconocidas = [L for L in legs if L not in LEG_ID]
    if desconocidas:
        sys.exit(f'· legislatura(s) fuera del dropdown de Cámara: {desconocidas}')

    (OUT / 'raw').mkdir(parents=True, exist_ok=True)
    nonce = None
    consolidado, incompletas = [], []

    for leg in legs:
        cache = OUT / 'raw' / f'{leg}.json'
        if cache.exists() and not a.force:
            items = json.loads(cache.read_text(encoding='utf-8'))
            print(f'· {leg}: {len(items):5d} (caché)')
        else:
            if nonce is None:
                nonce = get_nonce()
                print(f'· nonce {nonce}')
            items, total = bajar_legislatura(nonce, leg)
            if total is not None and len(items) != total:
                incompletas.append((leg, len(items), total))
                print(f'· {leg}: {len(items):5d} / {total} ⚠ INCOMPLETA')
            else:
                print(f'· {leg}: {len(items):5d}')
            cache.write_text(json.dumps(items, ensure_ascii=False), encoding='utf-8')
        for it in items:
            consolidado.append({**it, 'legislatura': leg})

    dest = OUT / 'camara.jsonl'
    with open(dest, 'w', encoding='utf-8') as f:
        for it in consolidado:
            f.write(json.dumps(it, ensure_ascii=False) + '\n')

    print(f'\ncamara.jsonl : {len(consolidado)} registros · {len(legs)} legislaturas')
    print(f'               {dest.relative_to(REPO)}')
    if incompletas:
        print('⚠ legislaturas incompletas (re-correr con --force):')
        for leg, n, t in incompletas:
            print(f'    {leg}: {n}/{t}')


if __name__ == '__main__':
    main()
