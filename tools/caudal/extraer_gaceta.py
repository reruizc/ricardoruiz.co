#!/usr/bin/env python3
"""
Caudal · fase 3 — extrae el texto de un PDF de gaceta y lo sube a S3.

La DESCARGA de la gaceta es semi-manual (portal JSF de la Imprenta, vía Chrome
— guarda el PDF donde puedas leerlo, p.ej. la carpeta del repo). Este script
toma ese PDF, extrae el texto (pypdf; digital 2006+ sale limpio, años viejos
pueden requerir OCR aparte) y lo deja en el bucket privado listo para que la
Lambda `caudal-analiza` (acción `gaceta`) lo pase por DeepSeek.

  python3 tools/caudal/extraer_gaceta.py <pdf> <key>        # key = 'num-año', p.ej 857-2013
  python3 tools/caudal/extraer_gaceta.py <pdf> <key> --no-upload   # solo extrae local

Luego, para el análisis (necesita DEEPSEEK_API_KEY en la Lambda):
  aws lambda invoke ... {"action":"gaceta","key":"857-2013","contexto":"Proyecto 107/2013 feminicidio"}
"""
import subprocess
import sys
from pathlib import Path

BUCKET = 'caudal-legislativo'


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    pdf, key = sys.argv[1], sys.argv[2]
    upload = '--no-upload' not in sys.argv

    import pypdf
    r = pypdf.PdfReader(pdf)
    txt = '\n'.join((p.extract_text() or '') for p in r.pages)
    digital = len(txt) > 2000
    out = Path(pdf).with_suffix('.txt')
    out.write_text(txt, encoding='utf-8')
    print(f'{Path(pdf).name}: {len(r.pages)} pág · {len(txt)} chars · '
          f'{"DIGITAL ✓" if digital else "ESCANEADO → necesita OCR aparte"}')
    if not digital:
        print('  ⚠ texto vacío/corto: PDF escaneado. Corre OCR (Tesseract) antes de subir.')

    if upload:
        dest = f's3://{BUCKET}/gacetas-texto/{key}.txt'
        subprocess.run(['aws', 's3', 'cp', str(out), dest,
                        '--content-type', 'text/plain; charset=utf-8'], check=True)
        print(f'→ {dest}')
        print(f'  ahora: invocar Lambda {{"action":"gaceta","key":"{key}","contexto":"…"}}')


if __name__ == '__main__':
    main()
