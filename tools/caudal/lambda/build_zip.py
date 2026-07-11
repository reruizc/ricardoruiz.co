#!/usr/bin/env python3
"""
Empaqueta la Lambda caudal-analiza. Toma el caudal_core.py CANÓNICO
(tools/caudal/caudal_core.py) para que no haya drift entre el motor local y el
de la Lambda. Salida: tools/caudal/lambda/caudal-analiza.zip (stdlib, sin deps).

  python3 tools/caudal/lambda/build_zip.py
"""
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORE = HERE.parent / 'caudal_core.py'          # fuente única de verdad
HANDLER = HERE / 'lambda_handler.py'
OUT = HERE / 'caudal-analiza.zip'

with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    z.write(HANDLER, 'lambda_handler.py')
    z.write(CORE, 'caudal_core.py')
print(f'{OUT.name} · {OUT.stat().st_size/1024:.1f} KB '
      f'(lambda_handler.py + caudal_core.py)')
