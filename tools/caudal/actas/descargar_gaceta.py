#!/usr/bin/env python3
"""
Caudal · Fase 3 — descarga de gacetas de la Imprenta POR CURL (sin el portal manual).

El portal JSF de la Imprenta (svrpubindc.imprenta.gov.co) parecía exigir clic a
clic en el navegador. NO: el deep-link `index2.xhtml?ent=&fec=&num=` renderiza una
página que, al cargar, hace un postback PrimeFaces (`pdfIr`) que devuelve el PDF.
Eso es reproducible con curl en 2 pasos:
  1. GET index2.xhtml?ent=Senado&fec=D-M-YYYY&num=NNN  → jsessionid (cookie) + ViewState
  2. POST index2.xhtml;jsessionid=...  con dldFile+pdfIr+ViewState  → application/pdf

`fec` = fecha EXACTA de la gaceta (D-M-YYYY, sin ceros a la izquierda), que sale
del portal al filtrar por número (columna Fecha Gaceta). `ent` = Senado | Camara.
El PDF cae en `Bases de datos/leyes-senado/gacetas/` con nombre `gaceta_{num}_{año}.pdf`
(lo que espera `procesar_gacetas.py` para armar la key {num}-{año}).

Uso:
  python3 tools/caudal/actas/descargar_gaceta.py Senado 4-6-2025 870
  python3 tools/caudal/actas/descargar_gaceta.py Camara 10-10-2016 870
"""
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
GDIR = REPO / 'Bases de datos' / 'leyes-senado' / 'gacetas'
BASE = 'http://svrpubindc.imprenta.gov.co/senado'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120 Safari/537.36')
COOKIE = '/tmp/_caudal_gaceta_cookies.txt'


def _curl(args, out=None):
    cmd = ['/usr/bin/curl', '-s', '-A', UA] + args
    if out:
        cmd += ['-o', out]
        subprocess.run(cmd, timeout=180)
        return None
    return subprocess.run(cmd, capture_output=True, timeout=180).stdout


def descargar(ent, fec, num):
    ent = ent.capitalize()                    # Senado | Camara
    anio = fec.split('-')[-1]
    page = _curl(['-c', COOKIE, f'{BASE}/index2.xhtml?ent={ent}&fec={fec}&num={num}']).decode('utf-8', 'replace')
    vs = re.search(r'name="javax.faces.ViewState"[^>]*value="([^"]+)"', page)
    js = re.search(r'jsessionid=([a-f0-9]+)', page)
    if not vs:
        print(f'  ✗ {num}/{anio}: no encontré ViewState (¿fecha/entidad mal?)', file=sys.stderr)
        return None
    GDIR.mkdir(parents=True, exist_ok=True)
    dest = GDIR / f'gaceta_{num}_{anio}.pdf'
    _curl(['-b', COOKIE, '-X', 'POST',
           f'{BASE}/index2.xhtml' + (f';jsessionid={js.group(1)}' if js else ''),
           '--data', 'dldFile=dldFile',
           '--data-urlencode', 'pdfIr=pdfIr',
           '--data-urlencode', f'javax.faces.ViewState={vs.group(1)}'],
          out=str(dest))
    head = dest.read_bytes()[:5]
    if head[:4] != b'%PDF':
        print(f'  ✗ {num}/{anio}: la respuesta no es PDF ({head})', file=sys.stderr)
        dest.unlink(missing_ok=True)
        return None
    mb = dest.stat().st_size / 1024 / 1024
    print(f'  ✓ {num}/{anio} ({ent}) → {dest.relative_to(REPO)} ({mb:.1f} MB)')
    return dest


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('uso: descargar_gaceta.py <Senado|Camara> <D-M-YYYY> <num>')
        sys.exit(1)
    descargar(sys.argv[1], sys.argv[2], sys.argv[3])
