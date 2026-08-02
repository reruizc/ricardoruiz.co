#!/usr/bin/env python3
"""Empaqueta la Lambda leyes-en-vivo (stdlib + boto3 del runtime).

Van dos módulos: el builder del feed y el redactor del resumen ciudadano. En
la Lambda el explicador corre EN MODO POBRE — no tiene los .txt del rastreo
diario ni pypdf, así que su mejor fuente es el objeto o el título — y solo
actúa si la función tiene DEEPSEEK_API_KEY en su entorno. No hay riesgo de que
degrade lo publicado: reusa el resumen anterior cuando venía de mejor fuente
(ver la guarda RANK en explica_en_vivo.explicar).
"""
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'leyes-en-vivo.zip'

with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    z.write(HERE / 'leyes_en_vivo.py', 'leyes_en_vivo.py')
    z.write(HERE / 'explica_en_vivo.py', 'explica_en_vivo.py')

print(f'· {OUT.relative_to(HERE.parents[1])}  ({OUT.stat().st_size} bytes)')
