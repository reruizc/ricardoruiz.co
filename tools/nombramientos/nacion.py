#!/usr/bin/env python3
"""Utilidades compartidas de la medición v2 (oct-2026): Socrata, NIT y gobiernos.

Universo (decisión de Ricardo, 20-oct-2026): SOLO gobierno nacional, Rama Ejecutiva.
La clasificación de cada entidad vive en universo.py → v2/entidades.json.
"""
import json, os, subprocess, time, urllib.parse, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, 'Bases de datos', 'nombramientos', 'v2')
RAW = os.path.join(D, 'raw')
os.makedirs(RAW, exist_ok=True)

SECOP2 = 'jbjy-vk9h'      # SECOP II · contratos electrónicos (2016→, fechas de inicio/fin, sector)
INTEGRADO = 'rpmr-utcd'   # SECOP I + II (2008→), para la historia de cada persona

GOBIERNOS = [('Uribe', '2002-08-07'), ('Santos', '2010-08-07'), ('Duque', '2018-08-07'),
             ('Petro', '2022-08-07'), ('De La Espriella', '2026-08-07')]


def socrata(recurso, params, intentos=6, timeout=300):
    q = f'https://www.datos.gov.co/resource/{recurso}.json?' + urllib.parse.urlencode(params)
    ultimo = ''
    for i in range(intentos):
        try:
            r = subprocess.run(['curl', '-s', '--max-time', str(timeout), '-A', 'Mozilla/5.0 (ricardoruiz.co)', q],
                               capture_output=True, text=True, timeout=timeout + 20)
            ultimo = r.stdout
            d = json.loads(r.stdout)
            if isinstance(d, list):
                return d
        except (ValueError, subprocess.TimeoutExpired):
            pass
        time.sleep(5 * (i + 1))
    raise RuntimeError(f'Socrata no respondió ({recurso}): {ultimo[:300]}')


def paginado(recurso, params, pagina=50000):
    out, off = [], 0
    while True:
        filas = socrata(recurso, {**params, '$limit': pagina, '$offset': off})
        out += filas
        if len(filas) < pagina:
            return out
        off += pagina


def nit9(x):
    """NIT de entidad a 9 dígitos: SECOP lo trae a veces con el dígito de verificación pegado."""
    d = re.sub(r'\D', '', str(x or '').split('-')[0])
    return d[:9] if len(d) >= 9 else d


def gobierno(f):
    if not f:
        return None
    f = str(f)[:10]
    actual = 'Antes de 2002'
    for nombre, desde in GOBIERNOS:
        if f >= desde:
            actual = nombre
    return actual


def cargar_json(nombre, defecto=None):
    p = os.path.join(D, nombre)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else defecto


def guardar_json(nombre, obj, indent=None):
    json.dump(obj, open(os.path.join(D, nombre), 'w', encoding='utf-8'), ensure_ascii=False, indent=indent)
