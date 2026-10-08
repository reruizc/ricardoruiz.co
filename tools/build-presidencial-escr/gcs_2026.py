#!/usr/bin/env python3
"""Arma GCS_2026PRES1V.csv y GCS_2026PRES2V.csv para el visor de escrutinio.

La RNEC todavía no publica el GCS de 2026. Lo que sí hay es el mesa a mesa (MMV)
de las 33 comisiones generales de cada vuelta, que es el escrutinio oficial por
mesa. Este script lo lleva al formato GCS de 16 columnas que lee build.py, para
que 2026 salga por el mismo camino que 2018 y 2022.

  Bases de datos/ESCRUTINIO-1V/MMV_*.csv                    1V, 33 comisiones
  Bases de datos/escrutinio-2026/raw-2v/MMV_*.csv           2V, 33 comisiones
  + EXTERIOR (dep 88) desde el preconteo por mesa: las comisiones generales no
    lo traen (la 1033 de Consulados salió vacía en el sitio presidencial).

⚠ En el exterior de la 1V el preconteo trae a Murillo y Caicedo, que renunciaron
  antes de la elección y no existen en el escrutinio: se excluyen, como en
  tools/escrutinio-1v/build.py.
⚠ Los códigos de candidato del preconteo NO son los del escrutinio
  (2V: preconteo Cepeda=2 / Abelardo=3 · escrutinio Cepeda=001 / Abelardo=002).
⚠ MMV_1027 de la 2V llegó con `=/;HttpOnly` antes del encabezado: se busca el
  encabezado en vez de saltar la primera línea a ciegas.

Salida: Bases de datos/escrutinio-2026/GCS_2026PRES{1V,2V}.csv
"""
import csv
import glob
import os
from collections import Counter

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BD = os.path.join(RAIZ, 'Bases de datos')
OUT = os.path.join(BD, 'escrutinio-2026')
FUENTES = {
    '1V': os.path.join(BD, 'ESCRUTINIO-1V'),
    '2V': os.path.join(BD, 'escrutinio-2026', 'raw-2v'),
}
PRE_1V = os.path.join(BD, 'nuevos archivos 1v 2026', 'PRECONTEO_1V_2026_MESA_con_Claudia.csv')
PRE_2V = os.path.join(BD, 'output_2v', 'PRECONTEO_2V_2026_MESA.csv')

# columna del preconteo 1V → código CAN del escrutinio (None = renunció, se excluye)
PRE1V_COL = {
    'Iván Cepeda': '001', 'Claudia López': '002', 'Santiago Botero': '003',
    'Abelardo De La Espriella': '004', 'Mauricio Lizcano': '005', 'Miguel Uribe': '006',
    'Sondra Macollins': '007', 'Roy Barreras': '008', 'Carlos Caicedo': None,
    'Gustavo Matamoros': '010', 'Paloma Valencia': '011', 'Sergio Fajardo': '012',
    'Gilberto Murillo': None,
    'votos_blanco': '996', 'votos_nulos': '997', 'votos_no_marcados': '998',
}
PRE2V_CAN = {'2': '001', '3': '002', '996': '996', '997': '997', '998': '998'}
CAB = ['FUENTE', 'FEC_ELEC', 'COD_COR', 'DES_COR', 'COD_CIR', 'DES_CIR', 'COD_DDE', 'COD_MME', 'COD_ZZ',
       'COD_PP', 'DES_MS', 'COD_PAR', 'DES_PAR', 'COD_CAN', 'DES_CAN', 'NUM_VOT']


def filas_mmv(path):
    texto = open(path, encoding='utf-8-sig').read()
    i = texto.find('DEP;DEPNOMBRE')
    return csv.reader(texto[i:].splitlines()[1:], delimiter=';')


def nombres_exterior():
    """Consulados: (mun, zona, puesto) → 'País · puesto', del MMV de Congreso 2026 (mismos códigos)."""
    look = {}
    for f in glob.glob(os.path.join(BD, 'DEPTOS_DECLARADOS', 'MMV_XXX_88_*.csv')):
        with open(f, encoding='utf-8-sig', newline='') as fh:
            rd = csv.reader(fh, delimiter=';')
            next(rd)
            for r in rd:
                if len(r) >= 8:
                    look.setdefault('88' + r[2] + r[4] + r[5], f'{r[3].title()} · {r[6].strip()}')
    return look


def main():
    pue_nom = nombres_exterior()
    for vuelta, carpeta in FUENTES.items():
        fecha = '31/05/2026' if vuelta == '1V' else '21/06/2026'
        nombres = {}
        filas = []
        tot = Counter()
        for f in sorted(glob.glob(os.path.join(carpeta, 'MMV_*.csv'))):
            for r in filas_mmv(f):
                if len(r) < 19 or not r[18].strip().isdigit():
                    continue
                v = int(r[18])
                can = r[15].strip()
                nombres.setdefault(can, r[17].strip())
                pue_nom.setdefault(r[0] + r[2] + r[4] + r[5], r[6].strip())
                filas.append(['ESCRUTINIO_COMISIONES', fecha, '1', 'PRESIDENTE', '0', 'NACIONAL',
                              r[0], r[2], r[4], r[5], r[7], r[13], r[14], can, r[17].strip(), v])
                tot['escrutinio'] += v
        # exterior desde el preconteo
        if vuelta == '1V':
            with open(PRE_1V, encoding='utf-8-sig', newline='') as fh:
                for r in csv.DictReader(fh):
                    if r['cod_departamento'] != '88':
                        continue
                    for col, can in PRE1V_COL.items():
                        v = int(r.get(col) or 0)
                        if can is None:
                            tot['excluidos (renunciaron)'] += v
                            continue
                        if v:
                            filas.append(['PRECONTEO_EXTERIOR', fecha, '1', 'PRESIDENTE', '0', 'NACIONAL', '88',
                                          r['cod_municipio'], r['zona'], r['puesto'], r['num_mesa'], '', '',
                                          can, nombres[can], v])
                            tot['exterior'] += v
        else:
            with open(PRE_2V, encoding='utf-8-sig', newline='') as fh:
                for r in csv.DictReader(fh):
                    if r['COD_DEP'] != '88':
                        continue
                    can = PRE2V_CAN[r['COD_CAN']]
                    v = int(r['VOTOS'] or 0)
                    if v:
                        filas.append(['PRECONTEO_EXTERIOR', fecha, '1', 'PRESIDENTE', '0', 'NACIONAL', '88',
                                      r['COD_MUN'], r['COD_ZONA'], r['COD_PUESTO'], r['COD_MESA'], '', '',
                                      can, nombres[can], v])
                        tot['exterior'] += v
        out = os.path.join(OUT, f'GCS_2026PRES{vuelta}.csv')
        with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
            w = csv.writer(fh, delimiter=';')
            w.writerow(CAB)
            w.writerows(filas)
        print(f'{vuelta}: {len(filas):,} filas · {dict(tot)} → {out}')
    # nombre oficial de cada puesto en 2026 (el georef no trae los consulados)
    import json
    with open(os.path.join(OUT, 'puestos_nombres_2026.json'), 'w', encoding='utf-8') as fh:
        json.dump(pue_nom, fh, ensure_ascii=False)
    print(f'nombres de puesto: {len(pue_nom):,}')


if __name__ == '__main__':
    main()
