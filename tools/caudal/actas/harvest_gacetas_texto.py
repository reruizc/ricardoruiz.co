#!/usr/bin/env python3
"""
Caudal · Fase 3 — cosecha MASIVA de texto de Gaceta del Congreso.

Lee Bases de datos/leyes-senado/actas/gacetas-index.jsonl (enumerar_gacetas.py)
y para cada gaceta que falte en S3: la descarga (mecanismo de descargar_gaceta.py,
2 pasos curl contra el portal JSF de la Imprenta), extrae texto con pypdf, sube
el .txt a s3://caudal-legislativo/gacetas-texto/{num}-{año}.txt y BORRA el PDF
local (solo nos interesa el texto — el PDF pesa ~5MB en promedio, el texto ~250KB).

Resumible: al arrancar lista lo que YA está en S3 y lo salta. Si se corta a la
mitad, correr de nuevo retoma donde iba. Fallos (PDF vacío/escaneado, descarga
rota) quedan en gacetas-fallos.jsonl para revisar/OCR después, no frenan el resto.

--ocr (jul-2026) — el tramo viejo del corpus viene ESCANEADO (imagen sin capa
de texto): pypdf devuelve vacío y la gaceta caía a `fail_empty`, dejando esos
proyectos fuera del índice. Con --ocr, cuando el texto nativo sale vacío se
rasteriza a 300dpi (pymupdf) y se pasa por Tesseract `spa` — mismo toolchain ya
probado en ocr_pilot.py / parse_dcnsw_camara.py. El texto OCR es MÁS RUIDOSO que
el digital, así que cada gaceta se marca con su procedencia y calidad:
  · s3 metadata  fuente=pypdf|ocr, ocr-conf=NN.N, ocr-calidad=alta|media|baja
  · manifiesto local gacetas-ocr-calidad.jsonl (una fila por gaceta OCR-eada)
La calidad sale de la confianza media que reporta Tesseract por palabra:
≥85 alta · 70-85 media · <70 baja (esas NO se suben: a esa confianza el texto
es sopa de letras y solo mete ruido al índice invertido).

⚠️ El OCR es ~100× más lento que pypdf (minutos por gaceta vs décimas), por eso
solo entra como FALLBACK del texto vacío, nunca como primera opción.

Uso:
  python3 tools/caudal/actas/harvest_gacetas_texto.py --workers 8
  python3 tools/caudal/actas/harvest_gacetas_texto.py --workers 8 --desde 2024-01-01
  # tramo viejo escaneado (ritmo sano, el OCR quema CPU):
  python3 tools/caudal/actas/harvest_gacetas_texto.py --ocr --indexables \
      --desde 1990-01-01 --hasta 2006-01-01 --workers 3
"""
import argparse
import json
import re
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

REPO = Path(__file__).resolve().parents[3]
GDIR = REPO / 'Bases de datos' / 'leyes-senado' / 'gacetas'
BASE_URL = 'http://svrpubindc.imprenta.gov.co/senado'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120 Safari/537.36')
IDX = REPO / 'Bases de datos' / 'leyes-senado' / 'actas' / 'gacetas-index.jsonl'
FALLOS = REPO / 'Bases de datos' / 'leyes-senado' / 'actas' / 'gacetas-fallos.jsonl'
LOG = REPO / 'Bases de datos' / 'leyes-senado' / 'actas' / 'harvest-gacetas.log'
STATUS = REPO / 'Bases de datos' / 'leyes-senado' / 'actas' / 'harvest-gacetas-status.json'
OCRCAL = REPO / 'Bases de datos' / 'leyes-senado' / 'actas' / 'gacetas-ocr-calidad.jsonl'
BUCKET = 'caudal-legislativo'
TIMEOUT = 300   # curl timeout por request (s) — subido de 180: las gacetas
                # recientes son enormes (verificado hasta 109 MB) y 180s las cortaba,
                # ése fue el grueso de los 2.5k "fallos" transitorios del barrido inicial.

_lock = Lock()
_counts = {'ok': 0, 'ok_ocr': 0, 'skip': 0, 'fail_download': 0, 'fail_extract': 0,
           'fail_empty': 0, 'fail_ocr': 0, 'fail_ocr_calidad': 0, 'fail_upload': 0}
_t0 = time.time()

# --- OCR (fallback para gacetas escaneadas) ---------------------------------
OCR_DPI = 300           # igual que ocr_pilot / parse_dcnsw_camara
OCR_MAX_PAGES = 120     # backstop: una gaceta de 400 págs a 300dpi es ~1h de CPU
OCR_MIN_CONF = 70.0     # por debajo de esto el texto es ilegible → no se sube
OCR_CONF_ALTA = 85.0


def _ocr_calidad(conf):
    return 'alta' if conf >= OCR_CONF_ALTA else ('media' if conf >= OCR_MIN_CONF else 'baja')


def ocr_pdf(path):
    """Rasteriza a OCR_DPI y pasa Tesseract spa. Devuelve (texto, conf_media, n_pags).
    La confianza media (que Tesseract da por palabra) es la señal de calidad:
    en el piloto una gaceta digital-limpia dio ~95; una escaneada mala baja de 70."""
    import fitz                      # pymupdf
    import pytesseract
    from pytesseract import Output
    from PIL import Image
    import io as _io

    doc = fitz.open(str(path))
    partes, confs = [], []
    for i, page in enumerate(doc):
        if i >= OCR_MAX_PAGES:
            break
        pix = page.get_pixmap(dpi=OCR_DPI)
        img = Image.open(_io.BytesIO(pix.tobytes('png')))
        d = pytesseract.image_to_data(img, lang='spa', output_type=Output.DICT)
        palabras = []
        for w, c in zip(d['text'], d['conf']):
            w = w.strip()
            if not w:
                continue
            palabras.append(w)
            try:
                c = float(c)
            except (TypeError, ValueError):
                c = -1.0
            if c >= 0:
                confs.append(c)
        if palabras:
            partes.append(' '.join(palabras))
    n_pags = len(doc)
    doc.close()
    conf = (sum(confs) / len(confs)) if confs else 0.0
    return '\n'.join(partes), conf, n_pags


def _log(msg):
    line = f'{time.strftime("%H:%M:%S")} {msg}'
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def existing_keys():
    r = subprocess.run(['aws', 's3', 'ls', f's3://{BUCKET}/gacetas-texto/', '--recursive'],
                       capture_output=True, text=True)
    keys = set()
    for line in r.stdout.splitlines():
        parts = line.split()
        if parts and parts[-1].endswith('.txt'):
            keys.add(Path(parts[-1]).stem)
    return keys


DIST = REPO / 'Bases de datos' / 'leyes-senado' / 'dist'
MAX_COMPARTIDA = 4   # idéntico a build_texto_index: una gaceta referenciada por
                     # >4 proyectos es un boletín de radicación masiva (contamina
                     # el índice) → se excluye allá, así que bajarla es doble
                     # desperdicio (además son los PDFs gigantes que hacen timeout).


def indexable_keys():
    """Set de gaceta_key 'NNN-AAAA' que el índice SÍ va a usar: referenciadas por
    ≤MAX_COMPARTIDA proyectos y NO como exposición de motivos. Mismo criterio que
    build_texto_index.build_gaceta_to_proyectos, para no cosechar lo que se descarta."""
    from collections import defaultdict
    mp = defaultdict(int)
    for fn in ('proyectos.jsonl', 'actos-legis.jsonl'):
        p = DIST / fn
        if not p.exists():
            continue
        for line in open(p, encoding='utf-8'):
            r = json.loads(line)
            for g in r.get('gacetas', []):
                gk = g.get('gaceta')
                if gk and g.get('tipo') != 'exposicion_motivos':
                    mp[gk.replace('/', '-')] += 1
    return {k for k, n in mp.items() if n <= MAX_COMPARTIDA}


def _curl(args, cookie, out=None):
    cmd = ['/usr/bin/curl', '-s', '-A', UA, '-b', cookie, '-c', cookie] + args
    if out:
        cmd += ['-o', out]
        subprocess.run(cmd, timeout=TIMEOUT)
        return None
    return subprocess.run(cmd, capture_output=True, timeout=TIMEOUT).stdout


def descargar_ts(ent, fec, num):
    """Copia thread-safe de descargar_gaceta.descargar(): cada llamada usa su
    PROPIO archivo de cookies (uuid) — con workers en paralelo, compartir un solo
    archivo de cookies pisa el jsessionid/ViewState de otro hilo a mitad de vuelo
    y arruina la descarga (bug real, encontrado antes de lanzar el harvester)."""
    ent = ent.capitalize()
    anio = fec.split('-')[-1]
    cookie = f'/tmp/_caudal_gac_{uuid.uuid4().hex}.txt'
    try:
        page = _curl([f'{BASE_URL}/index2.xhtml?ent={ent}&fec={fec}&num={num}'], cookie).decode('utf-8', 'replace')
        vs = re.search(r'name="javax.faces.ViewState"[^>]*value="([^"]+)"', page)
        js = re.search(r'jsessionid=([a-f0-9]+)', page)
        if not vs:
            return None
        GDIR.mkdir(parents=True, exist_ok=True)
        dest = GDIR / f'gaceta_{num}_{anio}_{threading.get_ident()}.pdf'
        _curl(['-X', 'POST', f'{BASE_URL}/index2.xhtml' + (f';jsessionid={js.group(1)}' if js else ''),
               '--data', 'dldFile=dldFile',
               '--data-urlencode', 'pdfIr=pdfIr',
               '--data-urlencode', f'javax.faces.ViewState={vs.group(1)}'],
              cookie, out=str(dest))
        head = dest.read_bytes()[:5] if dest.exists() else b''
        if head[:4] != b'%PDF':
            dest.unlink(missing_ok=True)
            return None
        return dest
    finally:
        Path(cookie).unlink(missing_ok=True)


def process_one(entry, use_ocr=False):
    num, anio, entidad, fecha = entry['num'], entry['anio'], entry['entidad'], entry['fecha']
    key = f'{num}-{anio}'
    ent = 'Camara' if 'mara' in entidad else 'Senado'
    y, m, d = fecha.split('-')
    fec = f'{int(d)}-{int(m)}-{y}'

    # el campo "Entidad" del listado NO siempre coincide con la que pide el
    # deep-link de descarga (confirmado jul-2026: 3/3 gacetas probadas a mano
    # necesitaban la entidad CONTRARIA a la del listado) — probar la listada
    # primero, y si falla, la otra, antes de darse por vencido.
    otra_ent = 'Senado' if ent == 'Camara' else 'Camara'
    dest = None
    for try_ent in (ent, ent, otra_ent, otra_ent):
        try:
            dest = descargar_ts(try_ent, fec, str(num))
        except Exception:
            dest = None
        if dest:
            break
        time.sleep(1.0)
    if not dest:
        return ('fail_download', key, None)

    try:
        import pypdf
        r = pypdf.PdfReader(str(dest))
        txt = ' '.join((p.extract_text() or '') for p in r.pages)
    except Exception as e:
        dest.unlink(missing_ok=True)
        return ('fail_extract', key, str(e)[:120])

    fuente, conf, calidad = 'pypdf', None, None
    if len(txt.strip()) < 80:
        # sin capa de texto → escaneada. Sin --ocr se reporta como antes.
        if not use_ocr:
            dest.unlink(missing_ok=True)
            return ('fail_empty', key, 'texto casi vacío — probable escaneada, requiere OCR')
        try:
            txt, conf, n_pags = ocr_pdf(dest)
        except Exception as e:
            dest.unlink(missing_ok=True)
            return ('fail_ocr', key, str(e)[:120])
        finally:
            dest.unlink(missing_ok=True)
        fuente, calidad = 'ocr', _ocr_calidad(conf)
        if len(txt.strip()) < 80:
            return ('fail_ocr', key, f'OCR no sacó texto (conf {conf:.0f}, {n_pags} págs)')
        if conf < OCR_MIN_CONF:
            # texto ilegible: subirlo mete ruido al índice invertido (palabras
            # inventadas que harían match con búsquedas reales) → se descarta.
            return ('fail_ocr_calidad', key,
                    f'confianza OCR {conf:.1f} < {OCR_MIN_CONF} — se descarta')
        with _lock:
            with open(OCRCAL, 'a', encoding='utf-8') as f:
                f.write(json.dumps({'gaceta': key, 'anio': anio, 'fecha': fecha,
                                    'conf': round(conf, 1), 'calidad': calidad,
                                    'chars': len(txt), 'paginas': n_pags,
                                    'paginas_ocr': min(n_pags, OCR_MAX_PAGES)},
                                   ensure_ascii=False) + '\n')
    else:
        dest.unlink(missing_ok=True)

    tmp = Path(f'/tmp/_gac_txt_{key.replace("/", "_")}.txt')
    tmp.write_text(txt, encoding='utf-8')
    # la procedencia viaja como metadata del objeto: quien consuma el texto
    # (índice, LLM) puede degradar confianza sin volver a mirar el PDF.
    meta = f'fuente={fuente}'
    if fuente == 'ocr':
        meta += f',ocr-conf={conf:.1f},ocr-calidad={calidad}'
    up = subprocess.run(
        ['aws', 's3', 'cp', str(tmp), f's3://{BUCKET}/gacetas-texto/{key}.txt',
         '--content-type', 'text/plain; charset=utf-8', '--metadata', meta],
        capture_output=True, text=True)
    tmp.unlink(missing_ok=True)
    if up.returncode != 0:
        return ('fail_upload', key, up.stderr[:160])
    return ('ok_ocr' if fuente == 'ocr' else 'ok', key, len(txt))


def write_status(total, done):
    elapsed = time.time() - _t0
    rate = done / elapsed if elapsed > 0 else 0
    eta_min = (total - done) / rate / 60 if rate > 0 else None
    STATUS.write_text(json.dumps({
        'total': total, 'procesadas': done, 'restantes': total - done,
        'elapsed_min': round(elapsed / 60, 1),
        'eta_min': round(eta_min, 1) if eta_min else None,
        **_counts,
    }, ensure_ascii=False, indent=1), encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=3,
                    help='paralelo (bajado de 8: 8 workers + PDFs enormes saturaban → timeouts)')
    ap.add_argument('--desde', default='2020-01-01')
    ap.add_argument('--hasta', default='', help='corte superior (exclusivo), p.ej. 2006-01-01')
    ap.add_argument('--ocr', action='store_true',
                    help='si el texto nativo sale vacío (gaceta escaneada), rasterizar '
                         '300dpi + Tesseract spa en vez de reportar fail_empty')
    ap.add_argument('--timeout', type=int, default=0, help='override del curl timeout (s)')
    ap.add_argument('--indexables', action='store_true',
                    help='solo gacetas que el índice usará (≤4 proyectos, sin expo-motivos) — '
                         'salta boletines gigantes, ~mitad del trabajo')
    ap.add_argument('--limit', type=int, default=0, help='solo para pruebas')
    args = ap.parse_args()

    global TIMEOUT
    if args.timeout:
        TIMEOUT = args.timeout

    if args.ocr:
        try:
            import fitz, pytesseract      # noqa: F401
            pytesseract.get_tesseract_version()
        except Exception as e:
            _log(f'--ocr pedido pero el toolchain no está listo: {e}')
            sys.exit(1)

    entries = [json.loads(l) for l in open(IDX, encoding='utf-8')]
    entries = [e for e in entries if e['fecha'] >= args.desde]
    if args.hasta:
        entries = [e for e in entries if e['fecha'] < args.hasta]
    if args.indexables:
        idxset = indexable_keys()
        antes = len(entries)
        entries = [e for e in entries if f"{e['num']}-{e['anio']}" in idxset]
        _log(f'--indexables: {len(entries)} de {antes} enumeradas son indexables '
             f'(≤{MAX_COMPARTIDA} proyectos, sin expo-motivos)')
    # más recientes PRIMERO: son las que más importan para "profundizar" temas
    # calientes (Lambda action tema?profundo=true) — que se puedan usar cuanto
    # antes, no al final de un barrido de 4+ horas.
    entries.sort(key=lambda e: e['fecha'], reverse=True)
    if args.limit:
        entries = entries[:args.limit]
    _log(f'{len(entries)} gacetas en el índice desde {args.desde} (recientes primero)')

    have = existing_keys()
    _log(f'{len(have)} ya están en S3 (se saltan)')
    pending = [e for e in entries if f"{e['num']}-{e['anio']}" not in have]
    _log(f'{len(pending)} por procesar · {args.workers} workers')

    fallos_f = open(FALLOS, 'a', encoding='utf-8')
    total = len(entries)
    done = len(entries) - len(pending)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process_one, e, args.ocr): e for e in pending}
        for fut in as_completed(futs):
            e = futs[fut]
            try:
                status, key, extra = fut.result()
            except Exception as ex2:
                status, key, extra = 'fail_download', f"{e['num']}-{e['anio']}", str(ex2)[:120]
            with _lock:
                _counts[status] = _counts.get(status, 0) + 1
                done += 1
                if status.startswith('fail'):
                    fallos_f.write(json.dumps({**e, 'motivo': status, 'detalle': extra},
                                              ensure_ascii=False) + '\n')
                    fallos_f.flush()
                if done % 25 == 0 or done == total:
                    write_status(total, done)
                    _log(f'{done}/{total} · ok={_counts["ok"]} ocr={_counts["ok_ocr"]} '
                         f'fail={sum(v for k,v in _counts.items() if k.startswith("fail"))} '
                         f'· {(done-len(entries)+len(pending))/max(time.time()-_t0,1)*60:.0f}/min')

    write_status(total, done)
    fallos_f.close()
    _log(f'TERMINADO · {_counts}')


if __name__ == '__main__':
    main()
