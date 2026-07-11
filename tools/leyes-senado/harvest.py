#!/usr/bin/env python3
"""
Harvester de leyes.senado.gov.co — proyectos de ley, leyes sancionadas,
proyectos de acto legislativo y actos legislativos (histórico 1990-hoy).

El sitio no tiene API documentada pero su frontend habla con endpoints PHP
que devuelven JSON (búsquedas) y HTML estructurado (detalles):

  POST api/search_pdly.php   (proyectos de ley · filtra por legislatura → SIN cap)
  POST api/search_pal.php    (proyectos de acto legislativo · idem)
  POST api/search_lys.php    (leyes sancionadas · cap 100, NO filtra legislatura)
  POST api/search_actos.php  (actos legislativos · idem)
  GET  api/get_detalle_{pdly,lys,pal,actos}.php?id=N   (IDs secuenciales)

Estrategia:
  fase listas   → pdly + pal por las 36 legislaturas (1990-1991..2025-2026).
  fase detalles → enumeración de IDs 1..max por tabla (max detectado por
                  bisección; --max-id para override). lys/actos SOLO se
                  pueden completar así por el cap de 100.
  fase dataset  → parsea el HTML de detalles a JSONL + CSV consolidado.

Todo stdlib. curl por subprocess (mismo patrón que scrape_cne.py: esquiva
el TLS de python 3.14). Resumible: los raw ya bajados no se re-piden.

Uso:
  python3 tools/leyes-senado/harvest.py listas
  python3 tools/leyes-senado/harvest.py detalles [--tabla pdly,lys] [--max-id 9999] [--delay 0.25]
  python3 tools/leyes-senado/harvest.py dataset
  python3 tools/leyes-senado/harvest.py test      # slice chico de validación
"""
import argparse
import csv
import html as htmllib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

BASE = 'https://leyes.senado.gov.co/api'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / 'Bases de datos' / 'leyes-senado'
RAW = OUT / 'raw'
LISTAS = OUT / 'listas'

# max id por tabla, medido por bisección el 2026-07-10 (+margen de crecimiento)
MAX_ID_DEFAULT = {'pdly': 10100, 'lys': 2800, 'pal': 820, 'actos': 90}
TABLAS = ['pdly', 'lys', 'pal', 'actos']
LEGISLATURAS = [f'{y}-{y+1}' for y in range(1990, 2026)]


def curl(url, post_fields=None, timeout=30):
    cmd = ['/usr/bin/curl', '-s', '-A', UA, '--max-time', str(timeout), url]
    if post_fields:
        cmd.insert(1, '-X'); cmd.insert(2, 'POST')
        for k, v in post_fields.items():
            cmd += ['-F', f'{k}={v}']
    # bytes crudos: algunas fichas traen encoding mixto utf-8/latin-1 que
    # rompe el decode estricto de subprocess(text=True). Decodifica tolerante.
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        return None
    try:
        return r.stdout.decode('utf-8')
    except UnicodeDecodeError:
        return r.stdout.decode('utf-8', errors='replace')


# ---------------------------------------------------------------- listas
def fase_listas(delay):
    LISTAS.mkdir(parents=True, exist_ok=True)
    for tabla in ('pdly', 'pal'):
        for leg in LEGISLATURAS:
            dest = LISTAS / f'{tabla}-{leg}.json'
            if dest.exists():
                continue
            body = curl(f'{BASE}/search_{tabla}.php', {'legislatura': leg}, timeout=60)
            try:
                d = json.loads(body)
                n = d.get('total_results', len(d.get('data', [])))
            except Exception:
                print(f'  !! {tabla} {leg}: respuesta no-JSON, reintento en 5s', file=sys.stderr)
                time.sleep(5)
                body = curl(f'{BASE}/search_{tabla}.php', {'legislatura': leg}, timeout=60)
                try:
                    d = json.loads(body); n = d.get('total_results', 0)
                except Exception:
                    print(f'  XX {tabla} {leg}: falló dos veces, sigo', file=sys.stderr)
                    continue
            dest.write_text(body, encoding='utf-8')
            print(f'  {tabla} {leg}: {n} registros')
            time.sleep(delay)


# -------------------------------------------------------------- detalles
def fase_detalles(tablas, max_ids, delay):
    for tabla in tablas:
        rdir = RAW / tabla
        rdir.mkdir(parents=True, exist_ok=True)
        max_id = max_ids[tabla]
        ya = {int(p.stem) for p in rdir.glob('*.html')}
        pendientes = [i for i in range(1, max_id + 1) if i not in ya]
        print(f'{tabla}: {len(ya)} en cache, {len(pendientes)} por bajar (max_id {max_id})')
        vacios = errores = consec_err = 0
        bajados = 0
        for n, i in enumerate(pendientes, 1):
            body = curl(f'{BASE}/get_detalle_{tabla}.php?id={i}', timeout=25)
            if body is None:
                errores += 1
                consec_err += 1
                if consec_err > 40:
                    print(f'  XX {tabla}: 40 errores de red seguidos, abortando tabla', file=sys.stderr)
                    break
                time.sleep(min(30, 3 * consec_err))  # backoff creciente
                continue
            consec_err = 0
            if len(body) < 500 or 'No se encontr' in body:
                vacios += 1
                (rdir / f'{i}.html').write_text('', encoding='utf-8')  # marca gap
            else:
                (rdir / f'{i}.html').write_text(body, encoding='utf-8')
                bajados += 1
            if n % 200 == 0:
                print(f'  {tabla}: {n}/{len(pendientes)} ({vacios} gaps)')
            time.sleep(delay)
        print(f'  {tabla} listo: {bajados} con contenido, {vacios} ids vacíos, {errores} errores')


def fase_detalles_par(tablas, max_ids, workers):
    """Igual que fase_detalles pero con N obreros concurrentes (curl es
    subprocess → libera el GIL). Cada id se baja con hasta 3 reintentos y su
    propio backoff; los gaps se marcan con archivo vacío. Resumible igual."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading
    for tabla in tablas:
        rdir = RAW / tabla
        rdir.mkdir(parents=True, exist_ok=True)
        ya = {int(p.stem) for p in rdir.glob('*.html')}
        pend = [i for i in range(1, max_ids[tabla] + 1) if i not in ya]
        print(f'{tabla}: {len(ya)} en cache, {len(pend)} por bajar · {workers} obreros', flush=True)
        lock = threading.Lock()
        done = {'n': 0, 'ok': 0, 'gap': 0, 'err': 0}

        def fetch(i):
            for intento in range(3):
                body = curl(f'{BASE}/get_detalle_{tabla}.php?id={i}', timeout=25)
                if body is not None:
                    if len(body) < 500 or 'No se encontr' in body:
                        (rdir / f'{i}.html').write_text('', encoding='utf-8')
                        return 'gap'
                    (rdir / f'{i}.html').write_text(body, encoding='utf-8')
                    return 'ok'
                time.sleep(2 * (intento + 1))  # backoff por id, no global
            return 'err'

        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(fetch, i): i for i in pend}
            for fut in as_completed(futs):
                r = fut.result()
                with lock:
                    done['n'] += 1
                    done['ok' if r == 'ok' else 'gap' if r == 'gap' else 'err'] += 1
                    if done['n'] % 200 == 0:
                        print(f"  {tabla}: {done['n']}/{len(pend)} "
                              f"({done['ok']} ok · {done['gap']} gaps · {done['err']} err)", flush=True)
        print(f"  {tabla} listo: {done['ok']} con contenido, {done['gap']} vacíos, {done['err']} errores", flush=True)


# --------------------------------------------------------------- parseo
CELL_RE = re.compile(r'<t[dh]([^>]*)>(.*?)</t[dh]>', re.S)


def _clean_cell(raw):
    # si trae span short/full (Ver más), quedarse con el full
    full = re.search(r"<span id='full[^']*'[^>]*>(.*?)</span>", raw, re.S)
    if full:
        raw = full.group(1)
    # quita solo los anchors de UI (Ver más/menos); conserva texto de otros links
    raw = re.sub(r'<a\b[^>]*>\s*Ver\s+m[áa]s\s*</a>', '', raw, flags=re.S | re.I)
    raw = re.sub(r'<a\b[^>]*>\s*Ver\s+menos\s*</a>', '', raw, flags=re.S | re.I)
    txt = re.sub(r'<[^>]+>', ' ', raw)
    return htmllib.unescape(re.sub(r'\s+', ' ', txt)).strip()


def _cell_ref(raw):
    """Extrae cross-link detalle-btn (id + tipo) si la celda lo trae."""
    m = re.search(r"detalle-btn[^>]*data-id='(\d+)'[^>]*data-type='(\w+)'", raw)
    return (int(m.group(1)), m.group(2)) if m else None


def _cell_gaceta(raw):
    """Filas de documentos (Exposición de motivos, Ponencias, Texto Plenaria,
    Conciliación…) enlazan a la Gaceta del Congreso. El href suele ser genérico
    (imprenta.gov.co) pero el TEXTO del link trae el número: 'Gaceta 258/08'.
    Devuelve (texto_gaceta, url) o None si la celda no tiene documento."""
    for attrs, body in re.findall(r"<a\b([^>]*)>(.*?)</a>", raw, re.S):
        inner = _clean_cell_txt(body)
        href_m = re.search(r"href=['\"]([^'\"]+)['\"]", attrs)
        href = href_m.group(1) if href_m else ''
        # ignora toggles de UI ("Ver más/menos") y links sin texto
        if not inner or re.fullmatch(r'Ver m[áa]s|Ver menos', inner, re.I):
            continue
        # documento real: texto tipo "Gaceta 258/08" o href a la imprenta
        if re.search(r'gaceta', inner, re.I) or 'imprenta.gov.co' in href:
            return (inner, '' if href in ('#', '') else href)
    return None


def _clean_cell_txt(raw):
    txt = re.sub(r'<[^>]+>', ' ', raw)
    return htmllib.unescape(re.sub(r'\s+', ' ', txt)).strip()


def parse_detalle(html_text, tabla, rec_id):
    t = re.sub(r'<style.*?</style>', '', html_text, flags=re.S)
    t = re.sub(r'<script.*?</script>', '', t, flags=re.S)
    titulo_m = re.search(r"<th[^>]*colspan[^>]*>(.*?)</th>", t, re.S)
    rec = {'id': rec_id, 'tabla': tabla,
           'titulo': _clean_cell(titulo_m.group(1)) if titulo_m else ''}
    cells = CELL_RE.findall(t)  # [(attrs, contenido), ...]
    # pares etiqueta(bold) → valor: recorre celdas en orden
    i = 0
    while i < len(cells) - 1:
        attrs, raw = cells[i]
        if 'font-weight: bold' in attrs or 'celda-etiqueta' in attrs or '<strong' in raw:
            label = _clean_cell(raw)
            valcell = cells[i + 1][1]
            value = _clean_cell(valcell)
            ref = _cell_ref(valcell)
            gaceta = _cell_gaceta(valcell)
            if label and label != value:
                key = re.sub(r'[^a-z0-9]+', '_',
                             label.lower()
                             .translate(str.maketrans('áéíóúñ', 'aeioun'))).strip('_')
                if key and key not in rec:
                    if gaceta:  # fila de documento → guarda nº de gaceta + url
                        rec[key] = gaceta[0]
                        if gaceta[1]:
                            rec[f'{key}_url'] = gaceta[1]
                    else:
                        rec[key] = value
                    if ref:
                        rec[f'{key}_ref_id'], rec[f'{key}_ref_tipo'] = ref
            i += 2
        else:
            i += 1
    return rec


def fase_dataset():
    OUT.mkdir(parents=True, exist_ok=True)
    for tabla in TABLAS:
        rdir = RAW / tabla
        if not rdir.exists():
            continue
        recs = []
        for p in sorted(rdir.glob('*.html'), key=lambda x: int(x.stem)):
            body = p.read_text(encoding='utf-8')
            if not body.strip():
                continue
            recs.append(parse_detalle(body, tabla, int(p.stem)))
        if not recs:
            continue
        # jsonl
        with open(OUT / f'{tabla}.jsonl', 'w', encoding='utf-8') as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        # csv con unión de columnas
        cols = ['id', 'tabla', 'titulo']
        for r in recs:
            for k in r:
                if k not in cols:
                    cols.append(k)
        with open(OUT / f'{tabla}.csv', 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(recs)
        print(f'{tabla}: {len(recs)} registros → {tabla}.jsonl + {tabla}.csv ({len(cols)} columnas)')


# ----------------------------------------------------------------- test
def fase_test():
    print('· lista pdly 2025-2026:')
    body = curl(f'{BASE}/search_pdly.php', {'legislatura': '2025-2026'}, timeout=60)
    d = json.loads(body)
    print(f'  {d["total_results"]} registros, ejemplo: {d["data"][0]["numero_senado"]} · {d["data"][0]["titulo"][:60]}…')
    print('· detalle pdly id 9540:')
    det = curl(f'{BASE}/get_detalle_pdly.php?id=9540')
    rec = parse_detalle(det, 'pdly', 9540)
    print(json.dumps(rec, ensure_ascii=False, indent=2)[:1200])
    print('· detalle lys id 2000:')
    det = curl(f'{BASE}/get_detalle_lys.php?id=2000')
    print(json.dumps(parse_detalle(det, 'lys', 2000), ensure_ascii=False, indent=2)[:800])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('fase', choices=['listas', 'detalles', 'dataset', 'test'])
    ap.add_argument('--tabla', default=','.join(TABLAS))
    ap.add_argument('--max-id', type=int, default=None)
    ap.add_argument('--delay', type=float, default=0.2)
    ap.add_argument('--workers', type=int, default=1,
                    help='obreros concurrentes en la fase detalles (1 = secuencial)')
    a = ap.parse_args()

    tablas = [t.strip() for t in a.tabla.split(',') if t.strip() in TABLAS]
    max_ids = dict(MAX_ID_DEFAULT)
    if a.max_id:
        for t in tablas:
            max_ids[t] = a.max_id

    if a.fase == 'listas':
        fase_listas(a.delay)
    elif a.fase == 'detalles':
        if a.workers > 1:
            fase_detalles_par(tablas, max_ids, a.workers)
        else:
            fase_detalles(tablas, max_ids, a.delay)
    elif a.fase == 'dataset':
        fase_dataset()
    else:
        fase_test()


if __name__ == '__main__':
    main()
