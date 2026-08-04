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
EMPRESAS = HERE.parent / 'empresas.py'         # diccionario marca → tema (④)
IMPORTANCIA = HERE.parent / 'importancia'      # las tres coordenadas
HANDLER = HERE / 'lambda_handler.py'
OUT = HERE / 'caudal-analiza.zip'

# del módulo de importancia solo viaja lo que la Lambda ejecuta: calibrar y
# evaluar son herramientas de línea de comandos y no tienen nada que hacer ahí
IMP_MODS = ('features.py', 'modelo.py', 'ejes.py')
# antecedentes.py NO viaja: su índice se precomputa y se lee de S3

with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    z.write(HANDLER, 'lambda_handler.py')
    z.write(CORE, 'caudal_core.py')
    z.write(EMPRESAS, 'empresas.py')
    for m in IMP_MODS:
        z.write(IMPORTANCIA / m, f'importancia/{m}')
print(f'{OUT.name} · {OUT.stat().st_size/1024:.1f} KB '
      f'(lambda_handler + caudal_core + empresas + importancia/{{'
      f'{",".join(m[:-3] for m in IMP_MODS)}}})')
