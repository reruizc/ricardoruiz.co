#!/usr/bin/env python3
"""
Caudal · Fase 3 — clasifica y enruta las gacetas descargadas.

El portal JSF de la Imprenta es lento y estatal (no sirve para bulk automatizado):
la descarga se hace con el navegador y cae a `gacetas/`. Este script es el otro
lado: toma los PDFs del folder, los clasifica (ACTA / PONENCIA / otro), extrae el
texto y lo sube a S3 (gacetas-texto/), de modo que:
  - PONENCIAS → el botón "analizar ponencia" de la ficha responde instantáneo.
  - ACTAS     → quedan listas para la extracción de aplazamiento + voto nominal.

Maneja el gotcha del servidor sin Content-Length: si hay un .crdownload estable
con %%EOF, lo finaliza a .pdf.

Uso: python3 tools/caudal/actas/procesar_gacetas.py
"""
import subprocess, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
GDIR = REPO / 'Bases de datos' / 'leyes-senado' / 'gacetas'
S3 = 's3://caudal-legislativo/gacetas-texto/'

ACTA_RE = re.compile(r'\bACTAS?\b|\bACTA\s+(?:N[ÚU]MERO|No\.?|DE\s+(?:COMISI|PLENARIA|SESI))', re.I)
PON_RE = re.compile(r'\bPONENCIAS?\b|INFORME\s+DE\s+PONENCIA', re.I)


def finalize_crdownloads():
    for f in GDIR.glob('*.crdownload'):
        data = f.read_bytes()
        if data[:4] == b'%PDF' and b'%%EOF' in data[-2000:]:
            # nombre real desconocido → deja como pendiente para renombrar a mano
            (GDIR / f'pendiente_{f.stat().st_size}.pdf').write_bytes(data)
            print(f'  finalizado {f.name} → pendiente_{f.stat().st_size}.pdf')


def key_of(fname):
    m = re.search(r'(\d{2,4})[_-](\d{4})', fname)
    return f'{m.group(1)}-{m.group(2)}' if m else fname.replace('.pdf', '')


def extract(pdf):
    import pypdf
    r = pypdf.PdfReader(str(pdf))
    return '\n'.join((p.extract_text() or '') for p in r.pages), len(r.pages)


def clasificar(txt):
    # el tipo de boletín se define en la 1ª sección (tras el masthead de directores)
    head = txt[:3000]
    a, p = bool(ACTA_RE.search(head)), bool(PON_RE.search(head))
    if a and not p:
        return 'acta'
    if p and not a:
        return 'ponencia'
    # ambos/ninguno → mira cuál aparece primero
    ma, mp = ACTA_RE.search(txt), PON_RE.search(txt)
    if ma and (not mp or ma.start() < mp.start()):
        return 'acta'
    if mp:
        return 'ponencia'
    return 'otro'


def main():
    finalize_crdownloads()
    pdfs = sorted(GDIR.glob('*.pdf'))
    print(f'{len(pdfs)} PDFs en gacetas/')
    rutas = {'acta': [], 'ponencia': [], 'otro': []}
    for pdf in pdfs:
        try:
            txt, npag = extract(pdf)
        except Exception as e:
            print(f'  ✗ {pdf.name}: {str(e)[:50]}'); continue
        tipo = clasificar(txt)
        key = key_of(pdf.name)
        tf = GDIR / f'texto_{key}.txt'
        tf.write_text(txt, encoding='utf-8')
        subprocess.run(['aws', 's3', 'cp', str(tf), f'{S3}{key}.txt',
                        '--content-type', 'text/plain', '--only-show-errors'])
        rutas[tipo].append(key)
        print(f'  {tipo.upper():9} {key:>10} · {npag:>3} pág → S3 gacetas-texto/{key}.txt')
    print(f'\n  actas: {rutas["acta"]}\n  ponencias: {rutas["ponencia"]}\n  otro: {rutas["otro"]}')
    print('\n  → ACTAS listas para extraer aplazamiento+voto (acción gaceta de la Lambda)')
    print('  → PONENCIAS: el botón "analizar ponencia" de la ficha ya responde instantáneo')


if __name__ == '__main__':
    main()
