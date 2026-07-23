#!/usr/bin/env python3
"""Empaqueta la Lambda leyes-en-vivo (solo leyes_en_vivo.py; stdlib + boto3 del runtime)."""
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'leyes-en-vivo.zip'

with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    z.write(HERE / 'leyes_en_vivo.py', 'leyes_en_vivo.py')

print(f'· {OUT.relative_to(HERE.parents[1])}  ({OUT.stat().st_size} bytes)')
