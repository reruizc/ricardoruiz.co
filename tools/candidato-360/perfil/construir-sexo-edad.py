#!/usr/bin/env python3
"""construir-sexo-edad.py — el cruce SEXO × EDAD del electorado, por puesto.

La página del electorado (candidato-360-electorado.html) arma «perfiles de
votante» —mujer joven, hombre mayor…— y para eso necesita el cruce de las dos
dimensiones en cada puesto, no cada una por su lado: la edad sola vive en
CENSO_EDAD_PUESTO.json y el sexo solo en PUESTOS_GEOREF. El cruce existe en
`Edadygenero.xlsx` de la Registraduría (sufragantes por MESA y sexo × banda de
edad), ya extraído a `Bases de datos/output_edad_1v/cache/p1v-2022.csv`.

Salida: { version, fuente, sexos:['H','M'], edades:['18-30','31-50','51+'],
          puestos: { '160010101': [h1,h2,h3,m1,m2,m3] } }  (sufragantes 2022)

⚠️ Son SUFRAGANTES (quienes votaron en la 1V de 2022), no censo: describen la
composición de quien vota en ese puesto, que es lo que una campaña quiere.
⚠️ En Bogotá la columna «Cód. Comuna / Localidad» trae el NOMBRE de la
localidad, no el código (gotcha documentado en CLAUDE.md) → BOG_LOC.
⚠️ Las mesas se ordenan por cédula (las bajas son de inscritos viejos): por
eso el cruce se agrega a PUESTO y nunca se lee por mesa.

Uso:  python3 tools/candidato-360/perfil/construir-sexo-edad.py [--salida=X.json]
"""
import csv, json, os, sys, unicodedata
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
ENTRADA = os.path.join(ROOT, 'Bases de datos', 'output_edad_1v', 'cache', 'p1v-2022.csv')
SALIDA = next((a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--salida=')), 'PERFIL_SEXO_EDAD_PUESTO.json')

BOG_LOC = {
    'USAQUEN': '01', 'CHAPINERO': '02', 'SANTA FE': '03', 'SAN CRISTOBAL': '04', 'USME': '05', 'TUNJUELITO': '06',
    'BOSA': '07', 'KENNEDY': '08', 'FONTIBON': '09', 'ENGATIVA': '10', 'SUBA': '11', 'BARRIOS UNIDOS': '12',
    'TEUSAQUILLO': '13', 'LOS MARTIRES': '14', 'ANTONIO NARINO': '15', 'PUENTE ARANDA': '16', 'LA CANDELARIA': '17',
    'CANDELARIA': '17', 'RAFAEL URIBE URIBE': '18', 'RAFAEL URIBE': '18', 'CIUDAD BOLIVAR': '19', 'SUMAPAZ': '20',
    'CORFERIAS': '90', 'CARCELES': '98',
}
def nrm(s):
    return unicodedata.normalize('NFD', str(s or '')).encode('ascii', 'ignore').decode().upper().strip()
def zf(s, w):
    s = str(s or '').strip()
    return s.zfill(w) if s.isdigit() else s

# Bandas de la fuente → tres grupos: 18-30 · 31-50 · 51+
H = {'18-30': ['Hombres entre 18 a 20 años', 'Hombres entre 21 a 25 años', 'Hombres entre 26 a 30 años'],
     '31-50': ['Hombres entre 31 a 35 años', 'Hombres entre 36 a 40 años', 'Hombres entre 41 a 45 años', 'Hombres entre 46 a 50 años'],
     '51+':   ['Hombres entre 51 a 55 años', 'Hombres entre 56 a 60 años', 'Hombres Mayores a 60 años']}
M = {k: [c.replace('Hombres entre', 'Mujeres entre').replace('Hombres Mayores', 'Mujeres mayores') for c in v] for k, v in H.items()}
EDADES = ['18-30', '31-50', '51+']

puestos = defaultdict(lambda: [0] * 6)
filas = 0; sin_zona = 0
with open(ENTRADA, newline='', encoding='utf-8-sig') as f:
    rd = csv.DictReader(f)
    faltan = [c for c in sum(H.values(), []) + sum(M.values(), []) if c not in rd.fieldnames]
    if faltan: raise SystemExit(f'Faltan columnas en {ENTRADA}: {faltan}')
    for r in rd:
        z = str(r['Cód. Comuna / Localidad']).strip()
        zona = zf(z, 2) if z.isdigit() else BOG_LOC.get(nrm(z))
        if not zona: sin_zona += 1; continue
        code = zf(r['Cód. Depto'], 2) + zf(r['Cód. Municipio'], 3) + zona + zf(r['Cód. Puesto de Votación'], 2)
        acc = puestos[code]
        for i, e in enumerate(EDADES):
            acc[i] += sum(int(float(r[c] or 0)) for c in H[e])
            acc[3 + i] += sum(int(float(r[c] or 0)) for c in M[e])
        filas += 1

puestos = {k: v for k, v in puestos.items() if sum(v) > 0}
salida = {
    'version': __import__('datetime').date.today().isoformat(),
    'fuente': 'Sufragantes de la primera vuelta presidencial de 2022 por sexo y edad, agregados por puesto (Registraduría, Edadygenero). Describe quién vota en cada puesto, no quién votó por alguien.',
    'sexos': ['H', 'M'], 'edades': EDADES,
    'puestos': puestos,
}
with open(SALIDA, 'w', encoding='utf-8') as f:
    json.dump(salida, f, ensure_ascii=False, separators=(',', ':'))
tot = sum(sum(v) for v in puestos.values())
print(f'{filas:,} mesas → {len(puestos):,} puestos · {tot:,} sufragantes con sexo y edad · {sin_zona} mesas sin zona · → {SALIDA} ({os.path.getsize(SALIDA)/1e6:.2f} MB)')
bog = {k: v for k, v in puestos.items() if k.startswith('16001')}
print(f'Bogotá: {len(bog)} puestos · {sum(sum(v) for v in bog.values()):,} sufragantes')
