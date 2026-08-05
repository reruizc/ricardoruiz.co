#!/usr/bin/env python3
"""Compila los eventos de tutelas-registros (S3) en UN CSV de diligenciamientos.

S3 no permite append, así que la Lambda tutela-registro escribe un JSON por
EVENTO (genera / pdf / word / copy / print / save) bajo:
  s3://elecciones-2026/ricardoruiz.co/tutelas-registros/eventos/yyyy=/mm=/dd=/

Este script:
  1. `aws s3 sync` de los eventos a  Bases de datos/tutelas-salud/registros/eventos/
     (incremental: solo baja lo nuevo).
  2. Agrupa por `sid` (una carga de página = un diligenciamiento). La fila base es
     el ÚLTIMO evento 'genera' del sid (la versión final del formulario); los demás
     eventos se vuelven columnas bandera (descargo_pdf, descargo_word, ...).
  3. Escribe  registros.csv  local y, con --upload, lo sube a
     s3://elecciones-2026/ricardoruiz.co/tutelas-registros/registros.csv  (privado).

Uso:
  python3 tools/tutela-analiza/build_registros_csv.py            # compila local
  python3 tools/tutela-analiza/build_registros_csv.py --upload   # y sube el CSV

Los eventos NO traen PII por diseño (whitelist en frontend y en la Lambda):
no hay nombre, documento, contacto ni IP. Aun así el prefijo es privado.
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LOCAL = REPO / 'Bases de datos' / 'tutelas-salud' / 'registros'
EVENTOS_DIR = LOCAL / 'eventos'
CSV_PATH = LOCAL / 'registros.csv'

S3_EVENTOS = 's3://elecciones-2026/ricardoruiz.co/tutelas-registros/eventos/'
S3_CSV = 's3://elecciones-2026/ricardoruiz.co/tutelas-registros/registros.csv'

COLS = [
    'sid', 'ts_server', 'ts', 'v', 'caso', 'rol', 'zona', 'estrato',
    'regimen', 'calidad', 'eps', 'ips', 'depto', 'ciudad',
    'prepagada', 'poliza', 'urgente', 'pqr', 'pqr_resp', 'ninguna',
    'sujetos', 'diag',
    'c_item', 'c_dosis', 'c_respuesta', 'c_estado', 'c_fecha', 'c_fechadada',
    'c_veces', 'dias',
    'via_p', 'via_n', 'via_nivel', 'adm_global',
    'anexos_n', 'anexos_tipos',
    'descargo_pdf', 'descargo_word', 'copio_texto', 'imprimio', 'guardo_borrador',
    'n_eventos',
]
FLAG = {'pdf': 'descargo_pdf', 'word': 'descargo_word', 'copy': 'copio_texto',
        'print': 'imprimio', 'save': 'guardo_borrador'}


def sync():
    EVENTOS_DIR.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(['aws', 's3', 'sync', S3_EVENTOS, str(EVENTOS_DIR)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit('aws s3 sync falló:\n' + r.stderr)
    nuevos = r.stdout.count('download:')
    print(f'sync: {nuevos} eventos nuevos')


def cargar():
    eventos = []
    for p in sorted(EVENTOS_DIR.rglob('*.json')):
        try:
            eventos.append(json.loads(p.read_text(encoding='utf-8')))
        except Exception as e:
            print(f'  ⚠ ilegible {p.name}: {e}', file=sys.stderr)
    return eventos


def compilar(eventos):
    por_sid = {}
    for ev in eventos:
        sid = ev.get('sid')
        if not sid:
            continue
        por_sid.setdefault(sid, []).append(ev)

    filas = []
    for sid, evs in por_sid.items():
        evs.sort(key=lambda e: e.get('ts_server', ''))
        generas = [e for e in evs if e.get('evento') == 'genera']
        base = dict(generas[-1] if generas else evs[-1])
        for e in evs:
            col = FLAG.get(e.get('evento'))
            if col:
                base[col] = True
        base['n_eventos'] = len(evs)
        for k in ('sujetos', 'anexos_tipos'):
            if isinstance(base.get(k), list):
                base[k] = '|'.join(base[k])
        filas.append({c: base.get(c, '') for c in COLS})

    filas.sort(key=lambda f: f.get('ts_server', ''))
    return filas


def main():
    upload = '--upload' in sys.argv
    sync()
    eventos = cargar()
    filas = compilar(eventos)
    with open(CSV_PATH, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(filas)
    print(f'{len(filas)} diligenciamientos ({len(eventos)} eventos) → {CSV_PATH}')
    if upload:
        r = subprocess.run(['aws', 's3', 'cp', str(CSV_PATH), S3_CSV,
                            '--content-type', 'text/csv'], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit('upload falló:\n' + r.stderr)
        print(f'subido → {S3_CSV}')


if __name__ == '__main__':
    main()
