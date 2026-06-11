#!/usr/bin/env python3
"""
Unifica los 32 CSV del escrutinio 1V 2026 (MMV por mesa, uno por depto)
en un solo CSV agregado POR PUESTO + un Excel amigable.

Entradas:  Bases de datos/ESCRUTINIO-1V/MMV_*.csv
           (DEP;DEPNOMBRE;MUN;MUNNOMBRE;ZONA;PUESTO;PUESNOMBRE;MESA;
            COMUCODIGO;COMUNOMBRE;CORCODIGO;CORNOMBRE;CIR;PAR;PARNOMBRE;
            CAN;CANCEDULA;CANNOMBRE;VOTOS)
Salidas:   Bases de datos/ESCRUTINIO-1V/ESCRUTINIO_1V_2026_PUESTO.csv
           Bases de datos/ESCRUTINIO-1V/Resultados_Escrutinio_1V_2026_por_puesto.xlsx

Notas:
- Las filas vienen sparse (solo candidatos con votos en la mesa);
  el agregado rellena con 0.
- Cobertura del lote actual: 32 deptos. FALTAN Santander (27, archivo
  consecutivo 1017 ausente) y Exterior/Consulados (88). Documentado en
  la hoja Instrucciones del Excel.
"""
import csv, glob, os, sys
from collections import defaultdict

BASE = '/Users/ricardoruiz/ricardoruiz.co/Bases de datos/ESCRUTINIO-1V'
OUT_CSV  = os.path.join(BASE, 'ESCRUTINIO_1V_2026_PUESTO.csv')
OUT_XLSX = os.path.join(BASE, 'Resultados_Escrutinio_1V_2026_por_puesto.xlsx')

# Candidatos en orden de votación nacional (escrutinio) + especiales
CANDS = [
    ('004', 'Abelardo De La Espriella'),
    ('001', 'Iván Cepeda Castro'),
    ('011', 'Paloma Valencia Laserna'),
    ('012', 'Sergio Fajardo Valderrama'),
    ('002', 'Claudia López'),
    ('003', 'Raúl Santiago Botero Jaramillo'),
    ('005', 'Óscar Mauricio Lizcano Arango'),
    ('006', 'Miguel Uribe Londoño'),
    ('007', 'Sondra Macollins Garvin Pinto'),
    ('008', 'Roy Leonardo Barreras Montealegre'),
    ('010', 'Gustavo Matamoros Camacho'),
]
SPECIALS = [('996', 'Votos en blanco'), ('997', 'Votos nulos'), ('998', 'Votos no marcados')]
ALL_CODES = [c for c, _ in CANDS] + [c for c, _ in SPECIALS]

def title_es(s):
    """Title-case suave para nombres en MAYÚSCULAS, respetando conectores."""
    minor = {'DE', 'DEL', 'LA', 'LAS', 'LOS', 'Y', 'EL', 'D.C.'}
    out = []
    for i, w in enumerate(s.split()):
        if w in minor and i > 0:
            out.append(w.lower() if w != 'D.C.' else w)
        else:
            out.append(w.capitalize())
    return ' '.join(out)

def main():
    files = sorted(glob.glob(os.path.join(BASE, 'MMV_*.csv')))
    print(f'{len(files)} archivos MMV')
    # key puesto = (dep, mun, zona, puesto)
    votos = defaultdict(lambda: defaultdict(int))   # key -> can -> votos
    mesas = defaultdict(set)                         # key -> set(mesa)
    meta  = {}                                       # key -> (depnom, munnom, puesnom, comucod, comunom)
    deps_seen = {}

    for f in files:
        with open(f, encoding='utf-8-sig', newline='') as fh:
            rd = csv.reader(fh, delimiter=';')
            header = next(rd)
            for row in rd:
                if len(row) < 19:
                    continue
                dep, depnom, mun, munnom, zona, pue, puenom, mesa = row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]
                comucod, comunom = row[8], row[9]
                can, vot = row[15], row[18]
                key = (dep, mun, zona, pue)
                try:
                    v = int(vot)
                except ValueError:
                    continue
                votos[key][can] += v
                mesas[key].add(mesa)
                if key not in meta:
                    meta[key] = (depnom, munnom, puenom, comucod, comunom)
                deps_seen[dep] = depnom

    print(f'{len(votos)} puestos · {sum(len(m) for m in mesas.values())} mesas · {len(deps_seen)} deptos')

    # sanity: candidatos no mapeados
    unmapped = set()
    for key, cv in votos.items():
        for c in cv:
            if c not in ALL_CODES:
                unmapped.add(c)
    if unmapped:
        print('⚠️ códigos de candidato no mapeados:', unmapped)
        sys.exit(1)

    header = (['cod_departamento', 'departamento', 'cod_municipio', 'municipio',
               'zona', 'cod_puesto', 'puesto', 'cod_comuna', 'comuna', 'mesas']
              + [n for _, n in CANDS]
              + [n for _, n in SPECIALS]
              + ['total_votos'])

    rows = []
    for key in sorted(votos.keys()):
        dep, mun, zona, pue = key
        depnom, munnom, puenom, comucod, comunom = meta[key]
        cv = votos[key]
        vals = [cv.get(c, 0) for c, _ in CANDS] + [cv.get(c, 0) for c, _ in SPECIALS]
        total = sum(vals)
        comunom_clean = '' if comunom.strip().upper() in ('NACIONAL', 'NULL', '') else title_es(comunom.strip())
        rows.append([dep, title_es(depnom), mun, title_es(munnom), zona, pue,
                     puenom.strip(), comucod, comunom_clean, len(mesas[key])]
                    + vals + [total])

    # ── CSV (BOM utf-8, códigos quoted para preservar ceros) ──
    with open(OUT_CSV, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_NONNUMERIC)
        w.writerow(header)
        for r in rows:
            w.writerow(r)
    print(f'CSV → {OUT_CSV} ({len(rows)} filas)')

    # totales de control
    tot_by_cand = [sum(r[10 + i] for r in rows) for i in range(len(CANDS) + len(SPECIALS))]
    for (c, n), t in zip(CANDS + SPECIALS, tot_by_cand):
        print(f'  {n:42s} {t:>12,}')
    print(f'  {"TOTAL":42s} {sum(tot_by_cand):>12,}')

    # ── XLSX ──
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.table import Table, TableStyleInfo

    wb = Workbook(write_only=False)

    # Hoja 1 · Instrucciones
    ws = wb.active
    ws.title = 'Instrucciones'
    ws.sheet_view.showGridLines = False
    ws.column_dimensions['A'].width = 110
    ox = Font(bold=True, size=14, color='8A1E16')
    bold = Font(bold=True, size=11)
    body = Font(size=11)
    L = [
        ('Escrutinio · Elección Presidencial 2026 · Primera vuelta (31 de mayo de 2026)', ox),
        ('Resultados oficiales del escrutinio, agregados por puesto de votación.', body),
        ('', None),
        ('Fuente', bold),
        ('Archivos MMV de escrutinio de la Registraduría Nacional del Estado Civil (un archivo por departamento,', body),
        ('nivel mesa), unificados y agregados por puesto por ricardoruiz.co.', body),
        ('', None),
        ('Qué contiene', bold),
        ('Una fila por puesto de votación. Columnas: códigos y nombres de departamento, municipio, zona,', body),
        ('puesto y comuna/localidad (cuando aplica), número de mesas escrutadas del puesto, votos por cada', body),
        ('uno de los 11 candidatos, votos en blanco, nulos, no marcados y total.', body),
        ('', None),
        ('Cobertura de esta versión', bold),
        ('32 departamentos del territorio nacional. NO incluye todavía Santander (cód. 27) ni la', body),
        ('circunscripción Exterior/Consulados (cód. 88): la Registraduría no había publicado esos archivos', body),
        ('al momento del corte. Los totales nacionales de esta tabla son parciales por esa razón.', body),
        ('', None),
        ('Notas de lectura', bold),
        ('· Los códigos territoriales son los de la Registraduría (no DANE) y conservan ceros a la izquierda.', body),
        ('· Zona 90 = puesto censo (ej. Corferias) · zona 98 = cárceles. Son agregados especiales sin', body),
        ('  geografía de barrio; inclúyelos o descártalos según tu análisis.', body),
        ('· En el escrutinio solo aparecen los 11 candidatos en contienda (las renuncias previas no suman votos).', body),
        ('· El % de cada candidato se calcula normalmente sobre votos válidos (candidatos + blanco).', body),
        ('', None),
        ('ricardoruiz.co · análisis electoral · datos: Registraduría Nacional', Font(size=10, italic=True, color='666666')),
    ]
    for i, (txt, ft) in enumerate(L, start=1):
        c = ws.cell(row=i, column=1, value=txt)
        if ft:
            c.font = ft
        c.alignment = Alignment(wrap_text=False, vertical='top')

    # Hoja 2 · Datos
    ws2 = wb.create_sheet('Datos por puesto')
    ws2.append(header)
    for r in rows:
        ws2.append(r)

    n_rows = len(rows) + 1
    n_cols = len(header)
    ref = f'A1:{get_column_letter(n_cols)}{n_rows}'
    tbl = Table(displayName='EscrutinioPuesto', ref=ref)
    tbl.tableStyleInfo = TableStyleInfo(name='TableStyleMedium4', showRowStripes=True)
    ws2.add_table(tbl)
    ws2.freeze_panes = 'G2'

    widths = [8, 18, 8, 22, 6, 8, 34, 8, 22, 7] + [14] * (len(CANDS) + len(SPECIALS)) + [12]
    for i, wd in enumerate(widths, start=1):
        ws2.column_dimensions[get_column_letter(i)].width = wd
    for col in range(11, n_cols + 1):
        for row in range(2, n_rows + 1):
            ws2.cell(row=row, column=col).number_format = '#,##0'

    wb.save(OUT_XLSX)
    print(f'XLSX → {OUT_XLSX}')

if __name__ == '__main__':
    main()
