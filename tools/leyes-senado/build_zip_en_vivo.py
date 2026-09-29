#!/usr/bin/env python3
"""Empaqueta la Lambda leyes-en-vivo (stdlib + boto3 del runtime).

Van los módulos de ambos feeds, el redactor del resumen ciudadano y pypdf para
leer las órdenes del día. El explicador de proyectos corre EN MODO POBRE — no
tiene los .txt del rastreo diario, así que su mejor fuente es el objeto o el título — y solo
actúa si la función tiene DEEPSEEK_API_KEY en su entorno. No hay riesgo de que
degrade lo publicado: reusa el resumen anterior cuando venía de mejor fuente
(ver la guarda RANK en explica_en_vivo.explicar).
"""
import importlib.util
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'leyes-en-vivo.zip'

with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    z.write(HERE / 'leyes_en_vivo.py', 'leyes_en_vivo.py')
    z.write(HERE / 'explica_en_vivo.py', 'explica_en_vivo.py')
    z.write(HERE / 'ordenes_cloud.py', 'ordenes_cloud.py')
    # La Lambda necesita leer los PDF oficiales para poblar la banda roja.
    # Se incluye pypdf completo para no depender de una layer externa.
    spec = importlib.util.find_spec('pypdf')
    if spec is None or not spec.submodule_search_locations:
        raise RuntimeError('pypdf no está instalado en el Python que empaqueta')
    package = Path(next(iter(spec.submodule_search_locations)))
    for path in package.rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            z.write(path, Path('pypdf') / path.relative_to(package))

print(f'· {OUT.relative_to(HERE.parents[1])}  ({OUT.stat().st_size} bytes)')
