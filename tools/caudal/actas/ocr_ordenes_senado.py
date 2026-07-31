#!/usr/bin/env python3
"""
Caudal · Fase 3 (OCR) — recupera las órdenes del día del SENADO que son PDF
genuinamente ESCANEADO (sin capa de texto nativa), para que
harvest_ordenes_senado.py deje de perderlas.

Contexto (jul-31-2026): la nota original hablaba de "47% de la Comisión
Sexta / ~19% de la Cuarta" escaneados. Al investigar se encontró que ese
`n_escaneado` estaba INFLADO por un bug de detección de 404 (ver
`es_error_html` en harvest_ordenes_senado.py: el cuerpo HTTP del 404 de
DOCman a veces trae un '\\n' suelto antes de '<!doctype html>', que el check
viejo `head[:1]==b'<'` no detectaba → esos 404 se contaban como "escaneado"
en vez de "link_roto"). Tras el fix:
  - Comisión Sexta: **0 escaneados reales** (los 168 eran 100% 404 de DOCman,
    stub HTML de 1.515 bytes — irrecuperables, ya documentado que no hay
    atajo de URL alterna). NO hay nada que OCRear ahí.
  - Comisión Cuarta: **26 escaneados reales** (PDFs de 68 KB a 486 KB con
    header %PDF válido, cuya extracción nativa da solo espacios en blanco —
    scans genuinos, probablemente "PaperStream Capture").
  - Comisión Quinta: 1. Plenaria: 4.
Ese es el universo real a OCRear — mucho más chico que el "47%" original,
pero real y recuperable.

Método: mismo patrón que ocr_pilot.py / parse_dcnsw_camara.py — pymupdf
renderiza cada página a 300dpi, pytesseract (spa) extrae el texto. A
diferencia del parser de voto nominal (que reconstruye una tabla por
geometría), acá basta el texto corrido: se alimenta tal cual al MISMO
parser de citas de proyecto que ya usa harvest_ordenes_senado.py
(CITA_RE/GACETA_REF_RE), así que no se duplica ninguna lógica de extracción
de número/título — solo se le da al harvester un texto mejor.

Salida: {id}.ocr.txt junto al {id}.pdf ya cacheado (mismo outdir que usa
harvest_ordenes_senado.py). harvest_ordenes_senado.py lo recoge solo en su
próxima corrida (revisa `{id}.ocr.txt` cuando el texto nativo es corto) y
marca cada agendamiento resultante con fuente:'ocr' + confianza — y exige
que el número resuelto exista en proyectos.jsonl antes de contarlo (los
'baja' — sin match — nunca entran al índice).

Uso:
  python3 tools/caudal/actas/ocr_ordenes_senado.py cuarta
  python3 tools/caudal/actas/ocr_ordenes_senado.py cuarta --workers 4
  python3 tools/caudal/actas/ocr_ordenes_senado.py buenas          # cuarta+quinta+sexta
  python3 tools/caudal/actas/ocr_ordenes_senado.py todas           # + débiles + plenaria
  python3 tools/caudal/actas/ocr_ordenes_senado.py cuarta --limit 5 --workers 1  # smoke test
Resumible: solo procesa lo que no tenga ya {id}.ocr.txt en disco.
"""
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harvest_ordenes_senado as H  # noqa: E402

DPI = 300
MAX_PAGES = 6   # una orden del día no debería pasar de unas pocas páginas;
                # tope defensivo para no quemar horas en un PDF anómalo.


def candidatos_escaneados(ambito):
    """Docs de un ámbito cuyo .pdf ya está cacheado, NO es la página 404 de
    DOCman (es_error_html), y cuyo texto nativo cacheado sigue siendo corto
    (<50 chars tras strip) — el universo real a OCRear. No re-descarga nada:
    depende de que harvest_ordenes_senado.py ya haya corrido (al menos
    --offline) para tener {id}.pdf + {id}.txt en disco."""
    es_plen = ambito == H.PLENARIA
    if es_plen:
        docs = H.fetch_plenaria_docman()
        cand = [d for d in docs if not H.PLEN_EXCLUIR_RE.search(d.get('title') or '')]
    else:
        docs = H.fetch_all_docman()
        cand = [d for d in docs if H.es_candidato(d) and H.ambito_de(d) == ambito]
    outdir = H.BASE / ambito
    out = []
    for doc in cand:
        ext = (doc.get('storage_path') or '').rsplit('.', 1)[-1].lower()
        if ext != 'pdf':          # los .docx nunca son escaneados (texto nativo o corrupto)
            continue
        fn = outdir / f"{doc['id']}.pdf"
        tf = outdir / f"{doc['id']}.txt"
        of = outdir / f"{doc['id']}.ocr.txt"
        if of.exists() or not fn.exists() or not tf.exists():
            continue
        txt = tf.read_text(encoding='utf-8')
        if txt == '' or len(txt.strip()) >= 50:
            continue                # link-roto (ya '') o texto nativo ya usable
        if H.es_error_html(fn):     # 404 mal cacheado de una corrida vieja: no OCRear un error
            continue
        out.append((ambito, doc['id']))
    return out, outdir


def ocr_uno(par):
    """Worker: renderiza + OCR de un PDF. Devuelve (ambito, id, n_chars) o
    (ambito, id, None) si falló."""
    ambito, doc_id = par
    import fitz
    import pytesseract
    from PIL import Image
    import io
    outdir = H.BASE / ambito
    fn = outdir / f'{doc_id}.pdf'
    of = outdir / f'{doc_id}.ocr.txt'
    try:
        doc = fitz.open(str(fn))
    except Exception as e:
        of.write_text('', encoding='utf-8')
        return ambito, doc_id, None, str(e)[:60]
    chunks = []
    for i, page in enumerate(doc):
        if i >= MAX_PAGES:
            break
        try:
            pix = page.get_pixmap(dpi=DPI)
            img = Image.open(io.BytesIO(pix.tobytes('png')))
            txt = pytesseract.image_to_string(img, lang='spa')
        except Exception:
            continue
        chunks.append(txt)
    full = '\n'.join(chunks)
    of.write_text(full, encoding='utf-8')
    return ambito, doc_id, len(full.strip()), None


def run(ambitos, limit=None, workers=4):
    todos = []
    for amb in ambitos:
        cand, outdir = candidatos_escaneados(amb)
        print(f'· {amb}: {len(cand)} PDFs escaneados pendientes de OCR (de los ya cacheados)')
        todos += cand
    if limit:
        todos = todos[:limit]
    if not todos:
        print('  nada que hacer — o ya está todo OCR-eado, o no hay escaneados genuinos.')
        return
    print(f'\n→ OCR de {len(todos)} PDFs con {workers} obreros (300dpi + tesseract spa)…')

    ok, vacio, err = 0, 0, 0
    if workers <= 1:
        results = [ocr_uno(p) for p in todos]
    else:
        results = []
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(ocr_uno, p): p for p in todos}
            done = 0
            for fut in as_completed(futs):
                results.append(fut.result())
                done += 1
                if done % 5 == 0 or done == len(todos):
                    print(f'  …{done}/{len(todos)}')
    for ambito, doc_id, nchars, errmsg in results:
        if nchars is None:
            err += 1
            print(f'  ! {ambito}/{doc_id}: error OCR ({errmsg})')
        elif nchars < 50:
            vacio += 1
            print(f'  · {ambito}/{doc_id}: OCR corrió pero dio {nchars} chars (imagen ilegible / en blanco)')
        else:
            ok += 1
    print(f'\n=== OCR terminado: {ok} con texto usable · {vacio} en blanco/ilegible · {err} error ===')
    print('  Corré de nuevo harvest_ordenes_senado.py sobre los mismos ámbitos para que')
    print('  recoja los {id}.ocr.txt y los sume al índice (fuente=\'ocr\', filtrado contra')
    print('  proyectos.jsonl).')


if __name__ == '__main__':
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None
    workers = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 4
    arg = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else 'buenas'
    if arg == 'todas':
        ambitos = H.BUENAS + H.DEBILES + [H.PLENARIA]
    elif arg == 'buenas':
        ambitos = H.BUENAS
    else:
        ambitos = [arg]
    validos = set(H.AMBITOS) | {H.PLENARIA}
    desconocidos = [a for a in ambitos if a not in validos]
    if desconocidos:
        sys.exit(f'ámbito desconocido: {", ".join(desconocidos)}\n'
                 f'válidos: {", ".join(sorted(validos))} · buenas · todas')
    run(ambitos, limit=limit, workers=workers)
