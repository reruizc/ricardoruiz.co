#!/usr/bin/env python3
"""
Escrutinio 2ª vuelta presidencial 2026 (21-jun-2026) agregado POR PUESTO + Excel.

Hermano de tools/escrutinio-1v/build.py, mismo formato de salida.

Entradas:  Bases de datos/escrutinio-2026/raw-2v/MMV_*.csv   (33 comisiones generales,
           mesa a mesa, bajados del sitio de escrutinios de la 2V en sep-2026)
           Bases de datos/output_2v/PRECONTEO_2V_2026_MESA.csv  (para el exterior)
Salidas:   Bases de datos/escrutinio-2026/ESCRUTINIO_2V_2026_PUESTO.csv
           Bases de datos/escrutinio-2026/Resultados_Escrutinio_2V_2026_por_puesto.xlsx

Notas:
- Igual que en la 1V, las comisiones generales NO traen el exterior (dep 88): se
  integra del PRECONTEO por mesa y la columna `fuente` lo dice fila por fila.
- ⚠ Los códigos de candidato NO son los mismos en las dos fuentes:
  escrutinio Cepeda=001 / Abelardo=002 · preconteo Cepeda=2 / Abelardo=3.
- MMV_1027 llegó con `=/;HttpOnly` pegado antes del encabezado: se busca el
  encabezado en vez de asumir que es la primera línea.
"""
import csv
import glob
import os
import sys
from collections import defaultdict

BASE = '/Users/ricardoruiz/ricardoruiz.co/Bases de datos/escrutinio-2026'
RAW = os.path.join(BASE, 'raw-2v')
PRECONTEO = '/Users/ricardoruiz/ricardoruiz.co/Bases de datos/output_2v/PRECONTEO_2V_2026_MESA.csv'
DECLARADOS_88 = '/Users/ricardoruiz/ricardoruiz.co/Bases de datos/DEPTOS_DECLARADOS'
OUT_CSV = os.path.join(BASE, 'ESCRUTINIO_2V_2026_PUESTO.csv')
OUT_XLSX = os.path.join(BASE, 'Resultados_Escrutinio_2V_2026_por_puesto.xlsx')

CANDS = [('002', 'Abelardo De La Espriella'), ('001', 'Iván Cepeda Castro')]
SPECIALS = [('996', 'Votos en blanco'), ('997', 'Votos nulos'), ('998', 'Votos no marcados')]
ALL_CODES = [c for c, _ in CANDS] + [c for c, _ in SPECIALS]
PRECONTEO_MAP = {'3': '002', '2': '001', '996': '996', '997': '997', '998': '998'}


def title_es(s):
    minor = {'DE', 'DEL', 'LA', 'LAS', 'LOS', 'Y', 'EL', 'D.C.'}
    return ' '.join(w.lower() if (w in minor and i > 0 and w != 'D.C.') else (w if w == 'D.C.' else w.capitalize())
                    for i, w in enumerate(s.split()))


def filas_mmv(path):
    with open(path, encoding='utf-8-sig', newline='') as fh:
        texto = fh.read()
    i = texto.find('DEP;DEPNOMBRE')
    if i < 0:
        raise SystemExit(f'sin encabezado: {path}')
    return csv.reader(texto[i:].splitlines()[1:], delimiter=';')


def load_nombres_exterior():
    look = {}
    for f in glob.glob(os.path.join(DECLARADOS_88, 'MMV_XXX_88_*.csv')):
        with open(f, encoding='utf-8-sig', newline='') as fh:
            rd = csv.reader(fh, delimiter=';')
            next(rd)
            for row in rd:
                if len(row) >= 8:
                    look.setdefault((row[2], row[4], row[5]), (row[3], row[6]))
    return look


def main():
    files = sorted(glob.glob(os.path.join(RAW, 'MMV_*.csv')))
    print(f'{len(files)} archivos MMV')
    votos = defaultdict(lambda: defaultdict(int))
    mesas = defaultdict(set)
    meta = {}
    for f in files:
        for row in filas_mmv(f):
            if len(row) < 19:
                continue
            dep, depnom, mun, munnom, zona, pue, puenom, mesa = row[:8]
            try:
                v = int(row[18])
            except ValueError:
                continue
            key = (dep, mun, zona, pue)
            votos[key][row[15]] += v
            mesas[key].add(mesa)
            meta.setdefault(key, (depnom, munnom, puenom, row[8], row[9]))
    raros = {c for cv in votos.values() for c in cv if c not in ALL_CODES}
    if raros:
        sys.exit(f'códigos de candidato no mapeados: {raros}')
    print(f'{len(votos)} puestos · {sum(len(m) for m in mesas.values())} mesas')

    header = (['cod_departamento', 'departamento', 'cod_municipio', 'municipio', 'zona', 'cod_puesto',
               'puesto', 'cod_comuna', 'comuna', 'mesas', 'fuente']
              + [n for _, n in CANDS] + [n for _, n in SPECIALS] + ['total_votos'])
    rows = []
    for key in sorted(votos):
        dep, mun, zona, pue = key
        depnom, munnom, puenom, comucod, comunom = meta[key]
        vals = [votos[key].get(c, 0) for c in ALL_CODES]
        comu = '' if comunom.strip().upper() in ('NACIONAL', 'NULL', '') else title_es(comunom.strip())
        rows.append([dep, title_es(depnom), mun, title_es(munnom), zona, pue, puenom.strip(), comucod, comu,
                     len(mesas[key]), 'escrutinio'] + vals + [sum(vals)])

    # exterior desde el preconteo
    ext = defaultdict(lambda: defaultdict(int))
    ext_mesas = defaultdict(set)
    with open(PRECONTEO, encoding='utf-8-sig', newline='') as fh:
        for r in csv.DictReader(fh):
            if r['COD_DEP'] != '88':
                continue
            k = (r['COD_MUN'].zfill(3), r['COD_ZONA'].zfill(2), r['COD_PUESTO'].zfill(2))
            ext[k][PRECONTEO_MAP[r['COD_CAN']]] += int(r['VOTOS'] or 0)
            ext_mesas[k].add(r['COD_MESA'])
    nombres = load_nombres_exterior()
    pais = {}
    for (mun, _z, _p), (munnom, _pn) in nombres.items():
        pais.setdefault(mun, munnom)
    for k in sorted(ext):
        mun, zona, pue = k
        munnom, puenom = nombres.get(k, (pais.get(mun, ''), ''))
        vals = [ext[k].get(c, 0) for c in ALL_CODES]
        rows.append(['88', 'Exterior (Consulados)', mun, title_es(munnom), zona, pue, puenom.strip(), '', '',
                     len(ext_mesas[k]), 'preconteo'] + vals + [sum(vals)])
    print(f'exterior: {len(ext)} puestos · {sum(len(m) for m in ext_mesas.values())} mesas')

    with open(OUT_CSV, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_NONNUMERIC)
        w.writerow(header)
        w.writerows(rows)
    tot = [sum(r[11 + i] for r in rows) for i in range(len(ALL_CODES))]
    for (c, n), t in zip(CANDS + SPECIALS, tot):
        print(f'  {n:30s} {t:>12,}')
    print(f'CSV → {OUT_CSV} ({len(rows)} filas)')

    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.table import Table, TableStyleInfo
    wb = Workbook()
    ws = wb.active
    ws.title = 'Instrucciones'
    ws.sheet_view.showGridLines = False
    ws.column_dimensions['A'].width = 110
    ox, bold, body = Font(bold=True, size=14, color='8A1E16'), Font(bold=True, size=11), Font(size=11)
    for i, (txt, ft) in enumerate([
        ('Escrutinio · Elección Presidencial 2026 · Segunda vuelta (21 de junio de 2026)', ox),
        ('Resultados oficiales del escrutinio, agregados por puesto de votación.', body),
        ('', None),
        ('Fuente', bold),
        ('Archivos MMV (mesa a mesa) de las 33 comisiones generales de escrutinio de la Registraduría,', body),
        ('unificados y agregados por puesto por ricardoruiz.co.', body),
        ('', None),
        ('Cobertura', bold),
        ('Los 33 departamentos del territorio nacional con el ESCRUTINIO oficial. El exterior (cód. 88) no viene', body),
        ('en las comisiones generales: sus filas salen del PRECONTEO por mesa. La columna "fuente" lo indica.', body),
        (f'Totales: Abelardo {tot[0]:,} · Cepeda {tot[1]:,} · blanco {tot[2]:,} (escrutinio + exterior en preconteo).'.replace(',', '.'), body),
        ('', None),
        ('Notas de lectura', bold),
        ('· Códigos de la Registraduría (no DANE), con ceros a la izquierda.', body),
        ('· Zona 90 = puesto censo · zona 98 = cárceles: agregados especiales sin barrio.', body),
        ('· El % de cada candidato se calcula sobre votos válidos (candidatos + blanco).', body),
        ('', None),
        ('ricardoruiz.co · análisis electoral · datos: Registraduría Nacional', Font(size=10, italic=True, color='666666')),
    ], start=1):
        c = ws.cell(row=i, column=1, value=txt)
        if ft:
            c.font = ft
        c.alignment = Alignment(vertical='top')
    ws2 = wb.create_sheet('Datos por puesto')
    ws2.append(header)
    for r in rows:
        ws2.append(r)
    ref = f'A1:{get_column_letter(len(header))}{len(rows) + 1}'
    t = Table(displayName='Escrutinio2VPuesto', ref=ref)
    t.tableStyleInfo = TableStyleInfo(name='TableStyleMedium4', showRowStripes=True)
    ws2.add_table(t)
    ws2.freeze_panes = 'G2'
    for i, wd in enumerate([8, 18, 8, 22, 6, 8, 34, 8, 22, 7, 11] + [16] * len(ALL_CODES) + [12], start=1):
        ws2.column_dimensions[get_column_letter(i)].width = wd
    for row in ws2.iter_rows(min_row=2, min_col=12):
        for c in row:
            c.number_format = '#,##0'
    wb.save(OUT_XLSX)
    print(f'XLSX → {OUT_XLSX}')


if __name__ == '__main__':
    main()
