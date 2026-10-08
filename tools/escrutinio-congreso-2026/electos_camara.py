#!/usr/bin/env python3
"""Representantes a la Cámara 2026 declarados en los E-26 (territorial, 34 circunscripciones).

Lee la sección «DECLARATORIA DE ELECCIÓN» de cada E-26 CAM departamental de la
Registraduría y, para Chocó y Cundinamarca, la del E-26 que rehízo el CNE. Emite
electos-camara-2026.json: {cod_dep: {partido: [nombres en el orden del acta]}}.

Los nombres llegan como APELLIDOS NOMBRES (así los imprime el acta). La página los
usa para rotular el hemiciclo, en vez de adivinar el elegido por voto preferente,
que no sirve para las listas cerradas.

Uso: python3 electos_camara.py DIR_E26 DIR_CNE salida.json
     DIR_E26  E26_CAM_*.pdf de la Registraduría (+ .ocr.txt de los escaneados)
     DIR_CNE  E26_CAM_CHOCO.txt y E26_CAM_CUND.txt (OCR de los del CNE)
"""
import json
import re
import sys
from pathlib import Path

import pymupdf

CNE = {'17': 'E26_CAM_CHOCO.txt', '15': 'E26_CAM_CUND.txt'}


def texto(pdf):
    ocr = pdf.with_suffix('.ocr.txt')
    if ocr.exists():
        return ocr.read_text()
    return '\n'.join(p.get_text() for p in pymupdf.open(pdf))


def declaratoria(t):
    """Devuelve [(cod_partido, partido, nombre)] de la(s) página(s) de declaratoria."""
    i = t.find('DECLARATORIA DE ELECCI')
    if i < 0:
        return []
    sec = t[i:]
    out = []
    # 1) PDF digital: tres líneas por electo (partido / nombre / cédula)
    for m in re.finditer(r'^(\d{4,5})-\s*([^\n]+)\n([A-ZÁÉÍÓÚÑÜ .\'-]{5,})\n(\d{5,11})\s*$', sec, re.M):
        out.append((m.group(1).zfill(5), m.group(2).strip(), m.group(3).strip()))
    if out:
        return out
    # 2) OCR: una línea «00001-PARTIDO … NOMBRE CÉDULA»; el nombre no se puede separar del
    #    partido con certeza, así que se guarda la línea entera y se casa por palabras.
    for m in re.finditer(r'^[|\[\s(_]*(\d{3,5})\s*[-.]\s*(.+?)\s+(\d{6,11})\s*$', sec, re.M):
        out.append((m.group(1).zfill(5), '', m.group(2).strip()))
    return out


def main():
    d_e26, d_cne, salida = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    res = {}
    for pdf in sorted(d_e26.glob('E26_CAM_*.pdf')):
        m = re.match(r'E26_CAM_(\d\d)_', pdf.name)
        dep = m.group(1)
        t = (d_cne / CNE[dep]).read_text() if dep in CNE else texto(pdf)
        res[dep] = {'fuente': f'CNE {CNE[dep]}' if dep in CNE else pdf.name,
                    'electos': [{'cod_partido': c, 'partido': p, 'nombre': n} for c, p, n in declaratoria(t)]}
    salida.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for dep, v in res.items():
        print(dep, len(v['electos']), v['fuente'])


if __name__ == '__main__':
    main()
