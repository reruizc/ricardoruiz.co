#!/usr/bin/env python3
"""Archivos descargables con las cifras oficiales del CNE (Congreso 2026).

  Senado_2026_oficial_CNE.xlsx / .csv   votos por partido y candidato según la
      declaratoria (Res. E-3328), al lado del escrutinio de comisiones, con la diferencia.
  Congreso_2026_elegidos.xlsx / .csv     los 102 senadores y 165 representantes que
      declararon los E-26 (Senado: CNE · Cámara: actas departamentales, CNE en Chocó,
      Cundinamarca y Afro).

Entradas: lo que dejó aplicar_cne.py (salida/), la copia previa de S3 (backup/) y
electos_camara.json. Uso:
  python3 build_descargas_oficiales.py BASE_DIR SALIDA_DIR
  BASE_DIR = Bases de datos/escrutinio-congreso-2026
"""
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo

BASE, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

nuevo = json.loads((BASE / 'salida/senado/resumen.json').read_text())
viejo = json.loads((BASE / 'backup-s3-2026-04/senado/resumen.json').read_text())
cam_deps = json.loads((BASE / 'salida/camara/departamentos.json').read_text())
actas = json.loads((BASE / 'electos_camara.json').read_text())
INDIG = {'0012', '0005', '6018', '6156', '6175', '6083', '6181', '6253', '6110', '6088'}

LEEME_SEN = [
    ('Qué es', 'Votos del Senado 2026 según la declaratoria del Consejo Nacional Electoral '
               '(Resolución E-3328 de 2026, 13 de julio), por partido y por candidato.'),
    ('Comparación', 'Al lado va el escrutinio de las comisiones generales (abril 2026), que es lo '
                    'que traen los archivos mesa a mesa. La diferencia es el ajuste que hizo el CNE '
                    'en el escrutinio nacional; no cambió ninguna curul ni ningún elegido.'),
    ('Totales nacionales', 'Votos por listas 18.856.590 · en blanco 622.149 · válidos 19.478.739 · '
                           'nulos 580.701 · no marcados 495.785 · umbral 584.362 · cifra repartidora 173.185.'),
    ('Circunscripción indígena', 'Votos por listas 242.387. El CNE dejó en 0 al Cabildo Indígena TEVIS.'),
    ('Cómo se leyó', 'El E-26 del CNE es un PDF escaneado. Cada voto se tomó por OCR y se validó contra la '
                     'columna «votos en letras»; 17 filas que el OCR no leyó se leyeron a ojo en el PDF. '
                     'Cada partido concilia al voto: voto de lista + candidatos = total del E-26.'),
    ('Mesa a mesa', 'El CNE no publicó su ajuste mesa a mesa. Para departamento, municipio, puesto y mesa '
                    'usa los archivos de la pestaña «Resultados Declarados» (comisiones escrutadoras).'),
    ('Fuente', 'https://www.cne.gov.co/elecciones/elecciones-2026/elecciones-congreso-2026'),
]


def estilo(ws, ncols, ref=None, nombre=None):
    for c in ws[1]:
        c.font = Font(bold=True, color='FFFFFF')
        c.fill = PatternFill('solid', fgColor='1F3A8A')
    ws.freeze_panes = 'A2'
    for i in range(1, ncols + 1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = 16
    if ref and nombre:
        t = Table(displayName=nombre, ref=ref)
        t.tableStyleInfo = TableStyleInfo(name='TableStyleMedium2', showRowStripes=True)
        ws.add_table(t)


def leeme(wb, filas):
    ws = wb.active
    ws.title = 'Léeme'
    ws.column_dimensions['A'].width = 24
    ws.column_dimensions['B'].width = 110
    for k, v in filas:
        ws.append([k, v])
        ws.cell(ws.max_row, 1).font = Font(bold=True)
        ws.cell(ws.max_row, 2).alignment = Alignment(wrap_text=True, vertical='top')


def norm(s):
    s = unicodedata.normalize('NFD', (s or '').upper())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')


# ── Senado: partidos y candidatos ─────────────────────────────
viejo_p = {p['codigo'] + '|' + p['partido']: p for p in viejo['partidos']}
elegidos_sen = []
filas_p, filas_c = [], []
for p in nuevo['partidos']:
    v = viejo_p.get(p['codigo'] + '|' + p['partido'], {})
    circ = 'INDÍGENA' if p['codigo'] in INDIG else 'NACIONAL'
    filas_p.append([circ, p['codigo'], p['partido'], v.get('votos'), p['votos'],
                    p['votos'] - (v.get('votos') or 0), p.get('curules') or 0])
    vc = {c['codigo'] + '|' + c['nombre']: c['votos'] for c in v.get('candidatos') or []}
    cands = sorted(p.get('candidatos') or [], key=lambda c: -c['votos'])
    n = p.get('curules') or 0
    for i, c in enumerate(cands):
        antes = vc.get(c['codigo'] + '|' + c['nombre'])
        electo = i < n
        filas_c.append([circ, p['codigo'], p['partido'], c['codigo'], c['nombre'], antes, c['votos'],
                        c['votos'] - (antes or 0), 'Sí' if electo else ''])
        if electo:
            elegidos_sen.append(['SENADO', circ, 'NACIONAL', p['partido'], c['nombre'], 'CNE · Res. E-3328'])

# listas cerradas del Senado: los elegidos salen de la declaratoria (ya verificados 100/100)
html = (Path(__file__).resolve().parents[2] / 'senado-2026.html').read_text(encoding='utf-8')
m = re.search(r'const CLOSED_LISTS\s*=\s*\{(.*?)\n\s*\};', html, re.S)
closed = {pm.group(1): re.findall(r"'([^']+)'", pm.group(2))
          for pm in re.finditer(r"'([^']+)'\s*:\s*\[(.*?)\]", m.group(1), re.S)}
for p in nuevo['partidos']:
    if not p.get('candidatos') and (p.get('curules') or 0) and p['partido'] in closed:
        for nom in closed[p['partido']][:p['curules']]:
            elegidos_sen.append(['SENADO', 'NACIONAL', 'NACIONAL', p['partido'], nom.upper(), 'CNE · Res. E-3328'])

wb = Workbook()
leeme(wb, LEEME_SEN)
ws = wb.create_sheet('Partidos')
cab_p = ['Circunscripción', 'Código', 'Partido', 'Votos comisiones (abr)', 'Votos CNE (jul)', 'Diferencia', 'Curules']
ws.append(cab_p)
for f in filas_p:
    ws.append(f)
estilo(ws, len(cab_p), f'A1:G{ws.max_row}', 'Partidos')
ws.column_dimensions['C'].width = 55
ws = wb.create_sheet('Candidatos')
cab_c = ['Circunscripción', 'Código partido', 'Partido', 'Código candidato', 'Candidato',
         'Votos comisiones (abr)', 'Votos CNE (jul)', 'Diferencia', 'Elegido']
ws.append(cab_c)
for f in filas_c:
    ws.append(f)
estilo(ws, len(cab_c), f'A1:I{ws.max_row}', 'Candidatos')
ws.column_dimensions['C'].width = 45
ws.column_dimensions['E'].width = 40
for sh in ('Partidos', 'Candidatos'):
    for row in wb[sh].iter_rows(min_row=2):
        for c in row:
            if isinstance(c.value, int):
                c.number_format = '#,##0'
wb.save(OUT / 'Senado_2026_oficial_CNE.xlsx')
with open(OUT / 'Senado_2026_oficial_CNE.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(cab_c)
    w.writerows(filas_c)

# ── Cámara: los elegidos ──────────────────────────────────────
# Mismo criterio que camara-2026.html: curules por la regla del art. 263 y nombre del
# voto preferente; las listas cerradas, de la declaratoria. Aquí se toma directo el acta.
nombre_dep = {d['cod']: d['nombre'] for d in cam_deps if d.get('circ_nom') == 'TERRITORIAL'}


def toks(x):
    return set(re.findall(r'[A-Z]+', norm(x))) - {'DE', 'DEL', 'LA', 'LOS', 'Y'}


# nombres limpios por departamento: candidatos de nuestros datos + las listas cerradas que la
# página de Cámara tomó de las actas (camara-2026.html · CLOSED_LISTS)
pool = {}
for d in cam_deps:
    if d.get('circ_nom') == 'TERRITORIAL':
        pool.setdefault(d['cod'], []).extend(c['nombre'] for l in (d.get('candidatos') or {}).values() for c in l)
html_c = (Path(__file__).resolve().parents[2] / 'camara-2026.html').read_text(encoding='utf-8')
bloque = html_c[html_c.index('const CLOSED_LISTS = {'):html_c.index('const AFRO_CLOSED_LISTS')]
for mdep in re.finditer(r"'(\d\d)': \{(.*?)\n      \},", bloque, re.S):
    pool.setdefault(mdep.group(1), []).extend(re.findall(r"'((?:[^'\\]|\\.)+)'", mdep.group(2)))
elegidos_cam = []
for cod, v in sorted(actas.items()):
    for e in v['electos']:
        partido = e['partido'] or ''
        nom = e['nombre']
        if not partido:    # línea de OCR: «PARTIDO … NOMBRE»; el partido se resuelve con los datos
            for p in sorted((nombre_dep and [x for d in cam_deps if d.get('cod') == cod
                             and d.get('circ_nom') == 'TERRITORIAL' for x in d['partidos']]) or [], key=len, reverse=True):
                if norm(nom).startswith(norm(p)[:30]):
                    partido, nom = p, nom[len(p):].strip()
                    break
        fuente = 'CNE · E-26' if 'CNE' in v['fuente'] else 'Registraduría · E-26 comisión general'
        # el nombre del acta llega en orden APELLIDOS NOMBRES y, en las escaneadas, con errores de
        # OCR («SALAMANGA»): se reemplaza por el de nuestros datos o el roster cuando casa
        t = toks(nom)
        mejor = max(pool.get(cod, []), key=lambda x: len(toks(x) & t), default=None)
        if mejor and len(toks(mejor) & t) >= max(2, len(toks(mejor)) - 1):
            nom = mejor.upper()
        elegidos_cam.append(['CÁMARA', 'TERRITORIAL', nombre_dep.get(cod, cod), partido, nom, fuente])
elegidos_cam += [
    ['CÁMARA', 'INDÍGENA', 'NACIONAL', 'MOVIMIENTO UNIDAD EN MINGA POR COLOMBIA', 'CARLOS MARIO CALVO LARGO', 'CNE'],
    ['CÁMARA', 'AFRODESCENDIENTE', 'NACIONAL', 'PARTIDO DEMÓCRATA COLOMBIANO', 'SANDOVAL IBAÑEZ WINSNER NESSIR', 'CNE · Res. E-3401'],
    ['CÁMARA', 'AFRODESCENDIENTE', 'NACIONAL', 'CONSEJO COMUNITARIO EL NARANJO', 'BENAVIDES ANGULO OSCAR DAVID', 'CNE · Res. E-3401'],
]

wb = Workbook()
leeme(wb, [
    ('Qué es', 'Los congresistas 2026-2030 declarados en los formularios E-26: 102 senadores (100 nacionales '
               '+ 2 indígenas) y 165 representantes (161 territoriales + 1 exterior + 1 indígena + 2 afro).'),
    ('No incluye', 'Las 16 curules CITREP ni las curules del Estatuto de la Oposición (Senado y Cámara).'),
    ('Nombres', 'Tal como los imprime cada acta: en las de la Registraduría van como APELLIDOS NOMBRES.'),
    ('Fuente', 'Senado: CNE, Res. E-3328 (13-jul-2026). Cámara: E-26 de las 34 comisiones generales '
               '(Registraduría); Chocó, Cundinamarca y Afro: E-26 del CNE (jul-2026).'),
])
ws = wb.create_sheet('Elegidos')
cab_e = ['Corporación', 'Circunscripción', 'Departamento', 'Partido', 'Nombre', 'Fuente']
ws.append(cab_e)
for f in elegidos_sen + elegidos_cam:
    ws.append(f)
estilo(ws, len(cab_e), f'A1:F{ws.max_row}', 'Elegidos')
ws.column_dimensions['D'].width = 55
ws.column_dimensions['E'].width = 42
ws.column_dimensions['F'].width = 34
wb.save(OUT / 'Congreso_2026_elegidos.xlsx')
with open(OUT / 'Congreso_2026_elegidos.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(cab_e)
    w.writerows(elegidos_sen + elegidos_cam)

print('senado candidatos', len(filas_c), '· partidos', len(filas_p))
print('elegidos senado', len(elegidos_sen), '· cámara', len(elegidos_cam))
sin_partido = [e for e in elegidos_cam if not e[3]]
print('cámara sin partido resuelto:', sin_partido)
