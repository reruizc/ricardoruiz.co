#!/usr/bin/env python3
"""Lee el OCR de un E-26 del CNE (Senado nacional, Senado indígena o Cámara) a filas.

El E-26 trae cada voto dos veces: en cifras y en letras. El OCR se equivoca con
frecuencia en una de las dos (`116.719` contra «ciento quince mil setecientos
diecinueve»), así que cada fila se valida cruzándolas y queda marcada:

  ok        cifra == letras
  letras    la cifra no se leyó o no casa; manda el número en letras
  cifra     las letras no se leyeron; manda la cifra (menos confiable)
  ninguno   no se pudo leer el voto

Uso:  python3 leer_e26_cne.py E26_SEN_NAC.txt > filas.json
El .txt sale de tools/pliegos-choco/ocr_vision.swift.
"""
import json
import re
import sys
import unicodedata

UNIDADES = {
    'CERO': 0, 'UN': 1, 'UNO': 1, 'UNA': 1, 'DOS': 2, 'TRES': 3, 'CUATRO': 4, 'CINCO': 5,
    'SEIS': 6, 'SIETE': 7, 'OCHO': 8, 'NUEVE': 9, 'DIEZ': 10, 'ONCE': 11, 'DOCE': 12,
    'TRECE': 13, 'CATORCE': 14, 'QUINCE': 15, 'DIECISEIS': 16, 'DIECISIETE': 17,
    'DIECIOCHO': 18, 'DIECINUEVE': 19, 'VEINTE': 20, 'VEINTIUN': 21, 'VEINTIUNO': 21,
    'VEINTIDOS': 22, 'VEINTITRES': 23, 'VEINTICUATRO': 24, 'VEINTICINCO': 25,
    'VEINTISEIS': 26, 'VEINTISIETE': 27, 'VEINTIOCHO': 28, 'VEINTINUEVE': 29,
    'TREINTA': 30, 'CUARENTA': 40, 'CINCUENTA': 50, 'SESENTA': 60, 'SETENTA': 70,
    'OCHENTA': 80, 'NOVENTA': 90, 'CIEN': 100, 'CIENTO': 100, 'DOSCIENTOS': 200,
    'TRESCIENTOS': 300, 'CUATROCIENTOS': 400, 'QUINIENTOS': 500, 'SEISCIENTOS': 600,
    'SETECIENTOS': 700, 'OCHOCIENTOS': 800, 'NOVECIENTOS': 900,
}
# grafías que el OCR produce a menudo y no son ambiguas
ALIAS = {'QUINENTOS': 'QUINIENTOS', 'VENTISIETE': 'VEINTISIETE', 'VENTIDOS': 'VEINTIDOS',
         'UNC': 'UNO', 'TRSCIENTOS': 'TRESCIENTOS', 'CUARENTAY': 'CUARENTA'}


def sin_tildes(s):
    s = unicodedata.normalize('NFD', s)
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').upper()


def letras_a_num(txt):
    """Convierte «UN MILLON NOVECIENTOS CINCO MIL TREINTA Y NUEVE» → 1905039.

    Devuelve None si aparece una palabra que no es número: preferimos no leer a leer mal.
    """
    pal = [ALIAS.get(w, w) for w in re.findall(r'[A-Z]+', sin_tildes(txt)) if w != 'Y']
    if not pal:
        return None
    total, actual, vio = 0, 0, False
    for w in pal:
        if w in UNIDADES:
            actual += UNIDADES[w]; vio = True
        elif w == 'MIL':
            total += (actual or 1) * 1000; actual = 0; vio = True
        elif w in ('MILLON', 'MILLONES'):
            total += (actual or 1) * 1_000_000; actual = 0; vio = True
        else:
            return None
    return total + actual if vio else None


def cifra_a_num(txt):
    t = txt.strip().strip('|[]').replace(',', '.')
    if t in ('O', 'o'):          # el OCR lee el cero de la columna como letra O
        return 0
    if not re.fullmatch(r'\d{1,3}(\.\d{3})*|\d+', t):
        return None
    return int(t.replace('.', ''))


FILA = re.compile(
    r'^[|\[\s_,.T]*(?P<cod>\d{5})[-. ]?(?P<can>\d{0,3})\s+(?P<nom>.+?)\s+'
    r'(?P<cifra>[\d.,]{1,11}|O)[|\s]+(?P<letras>[A-ZÁÉÍÓÚÑ ]{3,}).*$')
TOTAL = re.compile(
    r'^[|\[\s]*TOTAL VOTOS (?P<nom>.+?)\s+(?P<cifra>[\d.,]{1,13}|O)[|\s]+(?P<letras>[A-ZÁÉÍÓÚÑ ]{3,}).*$')


def leer(path):
    filas = []
    for linea in open(path, encoding='utf-8'):
        linea = linea.rstrip('\n')
        m = TOTAL.match(linea) or FILA.match(linea)
        if not m:
            continue
        d = m.groupdict()
        c, l = cifra_a_num(d['cifra']), letras_a_num(d['letras'])
        if c is not None and c == l:
            v, fuente = c, 'ok'
        elif l is not None:
            v, fuente = l, 'letras'
        elif c is not None:
            v, fuente = c, 'cifra'
        else:
            v, fuente = None, 'ninguno'
        filas.append({
            'tipo': 'total' if 'cod' not in d else 'candidato',
            'cod': d.get('cod'), 'can': d.get('can') or None,
            'nombre': re.sub(r'^[|\[_,.]+', '', d['nom']).strip(),
            'votos': v, 'fuente': fuente, 'cifra': c, 'letras': l,
        })
    return filas


if __name__ == '__main__':
    json.dump(leer(sys.argv[1]), sys.stdout, ensure_ascii=False, indent=1)
