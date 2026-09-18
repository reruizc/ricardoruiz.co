"""
gcs_columnas.py — resuelve las columnas de un CSV GCS de la Registraduría por
NOMBRE, no por posición.

Hace falta porque el mismo proceso electoral circula en dos anchos distintos:

    GCS_2023JAL.csv   16 columnas
    GCS_2023TER.csv   19 columnas  (trae además DES_DDE, DES_MME y DES_PP)

Los generadores estaban escritos contra el de 16 y leían por índice fijo, así
que sobre el de 19 tomaban `DES_DDE` como si fuera el código de municipio y
`DES_PAR` como si fuera el de candidato: no fallaban, simplemente producían
basura. Leer la cabecera cuesta una línea y quita esa clase entera de error.

    from gcs_columnas import columnas
    C = columnas(ruta)
    dde = row[C['COD_DDE']]

Si el archivo no trae cabecera reconocible se usa el orden de 16 columnas, que
es el que tenían los generadores.
"""
import os

# El orden de 16 columnas, que es el que asumían los generadores.
LEGADO = ['FUENTE', 'FEC_ELEC', 'COD_COR', 'DES_COR', 'COD_CIR', 'DES_CIR',
          'COD_DDE', 'COD_MME', 'COD_ZZ', 'COD_PP', 'DES_MS', 'COD_PAR',
          'DES_PAR', 'COD_CAN', 'DES_CAN', 'NUM_VOT']

NECESARIAS = ('COD_COR', 'COD_DDE', 'COD_MME', 'COD_ZZ', 'COD_PP', 'DES_MS',
              'COD_PAR', 'DES_PAR', 'COD_CAN', 'DES_CAN', 'NUM_VOT')


def columnas(path):
    """{nombre: índice 0-based} leyendo la cabecera del CSV."""
    nombres = []
    if os.path.exists(path):
        with open(path, encoding='utf-8-sig', errors='replace') as f:
            nombres = [c.strip().upper().lstrip('﻿') for c in (f.readline() or '').split(';')]
    if 'COD_COR' not in nombres:
        nombres = LEGADO
    idx = {n: i for i, n in enumerate(nombres)}
    faltan = [n for n in NECESARIAS if n not in idx]
    if faltan:
        raise SystemExit(f'{os.path.basename(path)}: faltan columnas {", ".join(faltan)}')
    idx['_ancho'] = len(nombres)
    return idx
