#!/usr/bin/env python3
"""Consultas presidenciales 2026 (8-mar) · cuadra consultas/deps.json de S3 contra los E-24 generales.

Las consultas no tienen E-26: el resultado oficial de cada departamento es el E-24 CON de su
comisión general (1000-1032 + exterior), en el portal escrutinioscongreso2026 (/docs/E24/…).
Copia local en Bases de datos/escrutinio-congreso-2026/consultas/.

El E-24 digital trae, por página, los rótulos de columna («Zona NN» o municipios, y a veces
«Total …») y por cada candidato una cifra por columna. El total del departamento es la columna
«Total» si existe; si no, la suma de las columnas de todas las páginas.
Los E-24 escaneados (sin texto) se reportan aparte: hay que leerlos por OCR o a ojo.

  python3 tools/escrutinio-congreso-2026/verificar_consultas.py deps.json
"""
import glob
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import pymupdf

DIR = Path(__file__).resolve().parents[2] / 'Bases de datos' / 'escrutinio-congreso-2026' / 'consultas'
CONSULTA = {'01': 'soluciones', '02': 'gran', '03': 'frente'}   # 0100 · 0200 · 0300 en el E-24


def norm(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return ' '.join(re.sub(r'[^A-Z ]', ' ', s.upper()).split())


def leer(path):
    """→ {consulta: {cod_candidato: votos}}, {'nomarc':…, 'nulos':…}, columnas_por_pagina"""
    d = pymupdf.open(path)
    filas = []        # (página, clave, valores, hay_total)
    paginas = []
    for page in d:
        lineas = [l.strip() for l in page.get_text().splitlines() if l.strip()]
        try:
            i0 = lineas.index('PP') + 1
        except ValueError:
            continue
        cols = []
        j = i0
        while j < len(lineas) and not re.match(r'^0[123]00 ', lineas[j]):
            cols.append(lineas[j])
            j += 1
        # columnas = cifras que siguen a la fila «0x00 CONSULTA…» (todas en cero); los rótulos de
        # municipio ocupan a veces dos líneas, así que contarlos no sirve
        k = j + 1
        while k < len(lineas) and re.fullmatch(r'\d+', lineas[k]):
            k += 1
        n = k - j - 1
        hay_total = any(c.upper().startswith('TOTAL') for c in cols)
        paginas.append(cols)
        cons = None
        while j < len(lineas):
            l = lineas[j]
            m = re.match(r'^0([123])00 ', l)
            if m:
                cons = CONSULTA['0' + m.group(1)]
                j += 1 + n           # la fila del voto a la consulta trae ceros
                continue
            m = re.match(r'^(\d{3}) (.+)$', l)
            clave = None
            if m and cons:
                clave = (cons, m.group(1))
            elif l.startswith('VOTOS NO MARCADOS'):
                clave = ('otros', 'nomarc')
            elif l.startswith('VOTOS NULOS'):
                clave = ('otros', 'nulos')
            elif l == 'TOTAL':
                j += 1 + n
                continue
            if clave:
                vals = lineas[j + 1:j + 1 + n]
                if not all(re.fullmatch(r'\d+', v) for v in vals):
                    raise SystemExit(f'{path}: fila {l!r} con valores raros {vals}')
                filas.append((len(paginas), clave, [int(v) for v in vals], hay_total))
                j += 1 + n
                continue
            j += 1
    # Si alguna página trae la columna «Total», el total del departamento es solo esa columna
    # (las demás páginas son el detalle por municipio o zona); si ninguna la trae, se suman todas.
    con_total = any(f[3] for f in filas)
    votos = defaultdict(lambda: defaultdict(int))
    otros = defaultdict(int)
    for pag, clave, vals, hay_total in filas:
        if con_total and not hay_total:
            continue
        v = vals[-1] if con_total else sum(vals)
        if clave[0] == 'otros':
            otros[clave[1]] += v
        else:
            votos[clave[0]][clave[1]] += v
    return votos, otros, paginas


def main(deps_path):
    s3 = {d['cod']: d for d in json.load(open(deps_path))}
    escaneados = []
    ok = mal = 0
    for f in sorted(glob.glob(str(DIR / 'E24_CON_*.pdf'))):
        dep = re.search(r'E24_CON_(\d+)_', Path(f).name).group(1).zfill(2)
        if dep == '01' and '_88_' in f:
            dep = '88'
        votos, otros, pags = leer(f)
        if not votos:
            escaneados.append((dep, Path(f).name))
            continue
        difs = []
        for cons, cands in votos.items():
            ref = {c['codigo']: c['votos'] for c in s3.get(dep, {}).get(cons, {}).get('candidatos', [])}
            for cod, v in cands.items():
                if ref.get(cod) != v:
                    difs.append((cons, cod, v, ref.get(cod)))
        if difs:
            mal += 1
            print(f'✗ dep {dep} · {len(difs)} diferencias: {difs[:6]}')
        else:
            ok += 1
            tot = {c: sum(v.values()) for c, v in votos.items()}
            print(f'✓ dep {dep} · {sum(len(v) for v in votos.values())} candidatos cuadran al voto · {tot} · '
                  f'nulos {otros["nulos"]:,} · no marcados {otros["nomarc"]:,}')
    print(f'\ndigitales: {ok} cuadran, {mal} con diferencias · escaneados (sin texto): {[d for d, _ in escaneados]}')


if __name__ == '__main__':
    main(sys.argv[1])
