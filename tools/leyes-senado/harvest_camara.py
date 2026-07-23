#!/usr/bin/env python3
"""
Rastreo DIARIO de proyectos de ley de la CÁMARA (camara.gov.co).

Hermano de harvest_diario.py (que hace lo mismo con el Senado). La Cámara NO
publica el texto en un PDF propio: su portal es WordPress y cada proyecto CITA
el número de Gaceta del Congreso donde se radicó. O sea:

  Senado  → aloja el escaneo del radicado (inmediato, pero OCR sucio).
  Cámara  → apunta a la Gaceta (born-digital, limpia) — el PDF vive en la
            Imprenta y se baja con tools/caudal/actas/descargar_gaceta.py.

Mecánica (todo curl, sin navegador — openresty de Cámara no filtra por
fingerprint TLS como el WAF del Senado):

  1. nonce   GET /proyectos-de-ley/  → PL_CFG.PL_NONCE (regex; caduca ~24h,
             ligado a IP/sesión anónima → se re-scrapea cada corrida).
  2. lista   POST wp-admin/admin-ajax.php  action=get_proyectos_ley_page
             {legislatura=20 (2026-2027), page, per_page, term, comision,
              tipo, estado, origen, ley_numero, ley_fecha}
             → {data:{items:[...], total, total_pages}}. Item rico:
               nro_camara/nro_senado/titulo/proyecto/tipo/estado/origen/
               vigencia/link_web(slug)/comisiones_pack/autores_pack.
  3. ficha   GET camara.gov.co/{link_web}  → "Gaceta No. N del AAAA" (regex,
             server-rendered; el texto radicado y ponencias van como gacetas).
  4. diff    contra el snapshot anterior → novedades-camara-YYYY-MM-DD.{json,md}

Estado (jul-2026): la legislatura 2026-2027 (id 20) está VACÍA — Cámara aún no
la cargó a su portal. La API funciona (2025-2026 = 579). Este script queda
corriendo para el día que carguen; hoy una corrida real no baja nada.

Uso:
  python3 tools/leyes-senado/harvest_camara.py                    # 2026-2027
  python3 tools/leyes-senado/harvest_camara.py --legislatura 2025-2026 --max 5
  python3 tools/leyes-senado/harvest_camara.py --no-ficha         # solo lista (sin gacetas)
"""
import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

BASE = 'https://www.camara.gov.co'
AJAX = f'{BASE}/wp-admin/admin-ajax.php'
LISTA_PAGE = f'{BASE}/proyectos-de-ley/'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / 'Bases de datos' / 'leyes-senado' / 'diario-camara'

# id interno del dropdown legislaturaField (del HTML de /proyectos-de-ley/)
LEG_ID = {
    '2026-2027': '20', '2025-2026': '13', '2024-2025': '3', '2023-2024': '2',
    '2022-2023': '1', '2021-2022': '5', '2020-2021': '6', '2019-2020': '7',
    '2018-2019': '8', '2017-2018': '9', '2016-2017': '10', '2015-2016': '11',
    '2014-2015': '12', '2013-2014': '15', '2012-2013': '16', '2011-2012': '17',
    '2010-2011': '18', '2009-2010': '19', '2008-2009': '14',
}
LEG_DEFAULT = '2026-2027'

RE_NONCE = re.compile(r'PL_CFG\s*=\s*\{[^}]*?PL_NONCE\s*:\s*"([a-f0-9]+)"', re.S)
RE_GACETA = re.compile(r'Gaceta\s*N[o°.]*\s*\.?\s*(\d+)\s*del?\s*(\d{4})', re.I)

# los campos "pack" vienen como "id||nombre||url" (o varios, separados por ;;)
def _unpack(s):
    out = []
    for chunk in (s or '').split(';;'):
        parts = chunk.split('||')
        if len(parts) >= 2 and parts[1].strip():
            out.append({'id': parts[0], 'nombre': parts[1].strip(),
                        'ref': parts[2] if len(parts) > 2 else ''})
    return out


def curl(url, post=None, timeout=40, retries=3):
    cmd = ['/usr/bin/curl', '-sL', '-A', UA, '--max-time', str(timeout), url]
    if post is not None:
        cmd = cmd[:1] + ['-X', 'POST'] + cmd[1:]
        for k, v in post.items():
            cmd += ['--data-urlencode', f'{k}={v}']
    for i in range(retries):
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode == 0 and r.stdout:
            return r.stdout.decode('utf-8', errors='replace')
        time.sleep(1.5 * (i + 1))
    return ''


def get_nonce():
    html = curl(LISTA_PAGE, timeout=40)
    m = RE_NONCE.search(html)
    return m.group(1) if m else None


def fetch_lista(nonce, leg_id, page, per_page=50):
    body = curl(AJAX, post={
        'action': 'get_proyectos_ley_page', '_ajax_nonce': nonce,
        'page': page, 'per_page': per_page, 'term': '', 'comision': '',
        'tipo': '', 'estado': '', 'origen': '', 'legislatura': leg_id,
        'ley_numero': '', 'ley_fecha': '',
    })
    try:
        d = json.loads(body)
    except json.JSONDecodeError:
        return None
    return d.get('data') if d.get('success') else None


def fetch_gacetas(link_web):
    """Ficha del proyecto → lista de gacetas citadas (dedup, orden de aparición)."""
    if not link_web:
        return []
    html = curl(f'{BASE}/{link_web}', timeout=40)
    vistos, out = set(), []
    for m in RE_GACETA.finditer(html):
        key = f'{m.group(1)}/{m.group(2)}'
        if key not in vistos:
            vistos.add(key)
            out.append({'num': m.group(1), 'anio': m.group(2), 'key': f'{m.group(1)}-{m.group(2)}'})
    return out


def norm_item(it, gacetas):
    return {
        'numero_camara': it.get('nro_camara', ''),
        'numero_senado': it.get('nro_senado') or '',
        'titulo': it.get('titulo', ''),
        'proyecto': it.get('proyecto', ''),
        'tipo': it.get('tipo', ''),
        'estado': it.get('estado', ''),
        'origen': it.get('origen', ''),
        'legislatura': it.get('vigencia', ''),
        'link_web': it.get('link_web', ''),
        'comisiones': _unpack(it.get('comisiones_pack')),
        'autores': _unpack(it.get('autores_pack')),
        'otros_autores': it.get('otros_autores') or '',
        'gacetas': gacetas,          # texto radicado + ponencias, en la Imprenta
    }


CAMPOS_VIGILADOS = ['titulo', 'numero_senado', 'estado', 'gacetas']


def diff(prev, cur):
    nuevos, cambios = [], []
    for k, rec in cur.items():
        old = prev.get(k)
        if old is None:
            nuevos.append(rec)
            continue
        deltas = {}
        for c in CAMPOS_VIGILADOS:
            a, b = old.get(c), rec.get(c)
            if json.dumps(a, ensure_ascii=False, sort_keys=True) != json.dumps(b, ensure_ascii=False, sort_keys=True):
                deltas[c] = {'antes': a, 'ahora': b}
        if deltas:
            cambios.append({'numero_camara': rec['numero_camara'], 'titulo': rec['titulo'], 'deltas': deltas})
    return nuevos, cambios


def escribir_reporte(md, js, leg, nuevos, cambios, total, fecha):
    js.parent.mkdir(parents=True, exist_ok=True)
    js.write_text(json.dumps({'fecha': fecha, 'legislatura': leg, 'total': total,
                              'nuevos': nuevos, 'cambios': cambios}, ensure_ascii=False, indent=1),
                  encoding='utf-8')
    L = [f'# Rastreo Cámara · {fecha}', '',
         f'Legislatura **{leg}** · {total} proyectos de ley', '',
         f'- Nuevos: **{len(nuevos)}** · con movimiento: **{len(cambios)}**', '']
    for r in nuevos:
        aut = ', '.join(a['nombre'] for a in r.get('autores', [])[:2]) or '—'
        gac = ', '.join(g['key'] for g in r.get('gacetas', [])) or '(sin gaceta aún)'
        L += [f"### {r['numero_camara']} · {r.get('tipo','')}", f"**{r['titulo']}**", '',
              f"- Autor: {aut}", f"- Estado: {r.get('estado','') or '—'}",
              f"- Gaceta(s) del texto: {gac}", '']
    if cambios:
        L += ['## Movimiento', '']
        for c in cambios:
            L += [f"### {c['numero_camara']} — {c['titulo'][:80]}"]
            for campo in c['deltas']:
                L.append(f"- cambió `{campo}`")
            L.append('')
    if not nuevos and not cambios:
        L += ['_Sin novedades._', '']
    md.write_text('\n'.join(L), encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--legislatura', default=LEG_DEFAULT)
    ap.add_argument('--no-ficha', action='store_true', help='solo lista (sin gacetas de la ficha)')
    ap.add_argument('--max', type=int, default=0, help='tope de proyectos (0 = todos)')
    ap.add_argument('--delay', type=float, default=0.5, help='pausa entre fichas (s)')
    args = ap.parse_args()

    leg = args.legislatura
    leg_id = LEG_ID.get(leg)
    if not leg_id:
        print(f'legislatura desconocida: {leg}', file=sys.stderr); sys.exit(1)

    hoy = dt.date.today().isoformat()
    base = OUT / leg
    snap_path = base / 'proyectos.json'
    prev = json.loads(snap_path.read_text(encoding='utf-8')) if snap_path.exists() else {}

    nonce = get_nonce()
    if not nonce:
        print('! no pude scrapear el nonce de /proyectos-de-ley/', file=sys.stderr); sys.exit(2)
    print(f'· legislatura {leg} (id {leg_id}) · nonce {nonce} · snapshot previo: {len(prev)}')

    # primera página para saber el total
    d0 = fetch_lista(nonce, leg_id, 1, per_page=50)
    if d0 is None:
        print('! la API no respondió (¿nonce vencido?)', file=sys.stderr); sys.exit(3)
    total = d0.get('total', 0)
    print(f'· total en la legislatura: {total}')
    if total == 0:
        escribir_reporte(OUT / 'novedades' / f'{hoy}.md', OUT / 'novedades' / f'{hoy}.json',
                         leg, [], [], 0, hoy)
        print('  (nada que rastrear — Cámara aún no cargó esta legislatura)')
        return

    items = list(d0.get('items', []))
    pages = d0.get('total_pages', 1)
    for p in range(2, pages + 1):
        dp = fetch_lista(nonce, leg_id, p, per_page=50)
        if dp:
            items += dp.get('items', [])
        time.sleep(args.delay)
    if args.max:
        items = items[:args.max]

    cur = {}
    for i, it in enumerate(items, 1):
        gacetas = [] if args.no_ficha else fetch_gacetas(it.get('link_web'))
        rec = norm_item(it, gacetas)
        rec['_visto'] = hoy
        cur[rec['numero_camara']] = rec
        if not args.no_ficha:
            if i % 25 == 0:
                print(f'  ficha {i}/{len(items)}…')
            time.sleep(args.delay)

    nuevos, cambios = diff(prev, cur)
    base.mkdir(parents=True, exist_ok=True)
    snap_path.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding='utf-8')
    with (base / 'proyectos.jsonl').open('w', encoding='utf-8') as fh:
        for k in cur:
            fh.write(json.dumps(cur[k], ensure_ascii=False) + '\n')
    escribir_reporte(OUT / 'novedades' / f'{hoy}.md', OUT / 'novedades' / f'{hoy}.json',
                     leg, nuevos, cambios, len(cur), hoy)

    con_gaceta = sum(1 for r in cur.values() if r['gacetas'])
    print(f'\n· total: {len(cur)} · nuevos: {len(nuevos)} · con movimiento: {len(cambios)} · con gaceta: {con_gaceta}')
    print(f'· snapshot  → {snap_path.relative_to(REPO)}')


if __name__ == '__main__':
    main()
