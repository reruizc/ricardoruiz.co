#!/usr/bin/env python3
"""
mirar_hoja.py — enseña qué trae una hoja de un Excel sin sacar datos de nadie.

Para decidir si una fuente nueva sirve hace falta ver sus COLUMNAS, no sus
filas. Esto imprime los nombres de las columnas, cuántas filas hay, y de cada
columna su tipo, cuántos valores distintos tiene y un par de ejemplos —pero
solo cuando la columna parece una categoría o un número, nunca cuando parece
identificar a una persona (cédula, nombre, dirección, teléfono, correo).

    python3 tools/analisis-candidato/mirar_hoja.py archivo.xlsx                 # lista las hojas
    python3 tools/analisis-candidato/mirar_hoja.py archivo.xlsx nombre_de_hoja
    python3 tools/analisis-candidato/mirar_hoja.py archivo.xlsx hoja --filas=5000

Necesita openpyxl (pip install openpyxl), que ya usan los otros generadores.
"""
import sys, unicodedata
from collections import Counter

SENSIBLES = ('CEDULA', 'CÉDULA', 'DOCUMENTO', 'NUIP', 'NOMBRE', 'APELLIDO',
             'DIRECCION', 'DIRECCIÓN', 'TELEFONO', 'TELÉFONO', 'CELULAR',
             'CORREO', 'EMAIL', 'MAIL')
# «NOMBRE» solo delata a una persona cuando no va seguido de un lugar: el
# nombre de un PUESTO es una escuela, no alguien.
LUGARES = ('PUESTO', 'COMUNA', 'MUNICIPIO', 'DEPARTAMENTO', 'ZONA', 'BARRIO',
           'LOCALIDAD', 'CORREGIMIENTO', 'VEREDA', 'CIUDAD', 'SEDE', 'PARTIDO',
           'LISTA', 'CIRCUNSCRIPCION')


def nrm(s):
    return unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode().upper()


def sensible(nombre):
    n = nrm(nombre)
    if any(l in n for l in LUGARES):
        return False
    return any(p in n for p in (nrm(x) for x in SENSIBLES))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ruta = sys.argv[1]
    hoja = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else None
    tope = next((int(a.split('=')[1]) for a in sys.argv[1:] if a.startswith('--filas=')), 3000)

    import openpyxl
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    if not hoja:
        print('Hojas del archivo:')
        for h in wb.sheetnames:
            print(f'  · {h}')
        return
    if hoja not in wb.sheetnames:
        sys.exit(f'no existe la hoja «{hoja}». Hay: {", ".join(wb.sheetnames)}')

    ws = wb[hoja]
    filas = ws.iter_rows(values_only=True)
    cab = [str(c).strip() if c is not None else '' for c in next(filas)]
    print(f'Hoja «{hoja}» · {len(cab)} columnas · {ws.max_row:,} filas (aprox.)\n')

    muestras = [Counter() for _ in cab]
    nulos = [0] * len(cab)
    numerica = [True] * len(cab)
    n = 0
    for fila in filas:
        n += 1
        for i, v in enumerate(fila[:len(cab)]):
            if v is None or v == '':
                nulos[i] += 1
                continue
            if not isinstance(v, (int, float)):
                numerica[i] = False
            if len(muestras[i]) < 600:
                muestras[i][str(v)[:40]] += 1
        if n >= tope:
            break

    print(f'{"#":>3}  {"columna":38} {"tipo":9} {"vacías":>7} {"distintos":>10}  ejemplos')
    for i, c in enumerate(cab):
        dis = len(muestras[i])
        tipo = 'número' if numerica[i] and dis else 'texto'
        if sensible(c):
            ej = '— (columna con datos personales: no se muestra)'
        else:
            ej = ', '.join(v for v, _ in muestras[i].most_common(3))[:70]
        print(f'{i:>3}  {c[:38]:38} {tipo:9} {nulos[i]:>7} {dis if dis < 600 else "600+":>10}  {ej}')
    print(f'\n(leídas {n:,} filas para la muestra; --filas= para más)')


if __name__ == '__main__':
    main()
