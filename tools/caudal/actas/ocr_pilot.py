#!/usr/bin/env python3
"""
Caudal · piloto de OCR para actas de plenaria de Cámara pre-nov-2020 (imágenes
escaneadas, sin texto nativo). Corre Tesseract (spa) sobre una muestra chica
para decidir si vale la pena el run completo (~928 actas) antes de lanzarlo.

Uso:
  python3 tools/caudal/actas/ocr_pilot.py
"""
import json, zipfile, time, sys
from pathlib import Path

import fitz          # pymupdf
import pytesseract
from PIL import Image
import io

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / 'Bases de datos' / 'leyes-senado' / 'actas' / 'plenaria-camara'
RAW_DIR = SRC / 'raw'
OUT_DIR = SRC / 'ocr-piloto'
OUT_DIR.mkdir(parents=True, exist_ok=True)

DPI = 300  # buena resolución para OCR de tablas


def render_and_ocr(pdf_bytes, max_pages=2):
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    texts = []
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        pix = page.get_pixmap(dpi=DPI)
        img = Image.open(io.BytesIO(pix.tobytes('png')))
        t0 = time.time()
        txt = pytesseract.image_to_string(img, lang='spa')
        texts.append((i + 1, txt, time.time() - t0))
    return texts, len(doc)


def pick_internal_pdfs(path, limit=3):
    """De un zip, elige hasta `limit` PDFs internos (prioriza los que
    parecen 'asistencia' y los que traen un número de proyecto)."""
    if path.suffix.lower() == '.pdf':
        return [(path.name, path.read_bytes())]
    out = []
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.lower().endswith('.pdf') and not n.startswith('__MACOSX')]
        names.sort()
        # OJO: matchear solo el NOMBRE DE ARCHIVO, no el path completo — la
        # carpeta interna suele llamarse "Asistencia y Votaciones (fecha)/"
        # y contaminaba el match si se comparaba contra `n` completo.
        base = lambda n: Path(n).name.lower()
        asis = [n for n in names if 'asistenc' in base(n) or 'certi' in base(n)]
        votos = [n for n in names if n not in asis]
        chosen = (asis[:1] + votos[:max(0, limit - 1)])[:limit]
        for n in chosen:
            out.append((n, z.read(n)))
    return out


def main():
    picks = json.load(open('/tmp/ocr_pilot_picks.json', encoding='utf-8'))
    resumen = []
    for fecha, rid, ext, numero in picks:
        raws = list(RAW_DIR.glob(f'{rid}.*'))
        if not raws:
            print(f'{fecha} [{rid}] SIN ARCHIVO')
            continue
        path = raws[0]
        print(f'\n{"=" * 70}\n{fecha}  acta {numero}  ({path.name}, {path.stat().st_size/1024:.0f} KB)')
        try:
            internos = pick_internal_pdfs(path)
        except Exception as e:
            print('  ERROR abriendo:', e)
            continue
        outf = OUT_DIR / f'{rid}.txt'
        chunks = []
        for nombre_pdf, data in internos:
            print(f'  → {nombre_pdf}')
            try:
                textos, npag = render_and_ocr(data, max_pages=2)
            except Exception as e:
                print('    ERROR OCR:', e)
                continue
            for pageno, txt, dt in textos:
                nchars = len(txt.strip())
                print(f'    pág {pageno}/{npag} · {dt:.1f}s · {nchars} chars')
                preview = ' '.join(txt.split())[:220]
                print(f'    preview: {preview}')
                chunks.append(f'--- {nombre_pdf} pág {pageno} ---\n{txt}')
                resumen.append({'fecha': fecha, 'acta': rid, 'archivo': nombre_pdf,
                                 'pagina': pageno, 'chars': nchars, 'segundos': round(dt, 1)})
        outf.write_text('\n\n'.join(chunks), encoding='utf-8')

    json.dump(resumen, open(OUT_DIR / '_resumen-piloto.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'\n\n→ {OUT_DIR.relative_to(REPO)}/ ({len(resumen)} páginas OCR-eadas)')


if __name__ == '__main__':
    main()
