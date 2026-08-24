#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prueba directa: DENTRO del mismo puesto, la edad de los votantes de cada mesa
predice el voto de esa mesa. 2V 2022, las dos variables OBSERVADAS.

Une Edadygenero (RNEC, votantes por mesa x banda de edad) con el escrutinio
2V 2022 por mesa. Efectos fijos de puesto: solo se compara mesa contra mesa
DEL MISMO puesto, asi que no hay confusion territorial ni socioeconomica.

Si la correlacion es alta, el "patron de bloques" es el orden de cedula.
"""
import csv, math, collections, unicodedata, statistics as st

BASE = '/Users/ricardoruiz/ricardoruiz.co'
BOG_LOC = {'USAQUEN': '01', 'CHAPINERO': '02', 'SANTA FE': '03', 'SAN CRISTOBAL': '04',
           'USME': '05', 'TUNJUELITO': '06', 'BOSA': '07', 'KENNEDY': '08',
           'FONTIBON': '09', 'ENGATIVA': '10', 'SUBA': '11', 'BARRIOS UNIDOS': '12',
           'TEUSAQUILLO': '13', 'LOS MARTIRES': '14', 'ANTONIO NARINO': '15',
           'PUENTE ARANDA': '16', 'LA CANDELARIA': '17', 'RAFAEL URIBE URIBE': '18',
           'CIUDAD BOLIVAR': '19', 'SUMAPAZ': '20', 'CORFERIAS': '90', 'CARCELES': '98'}


def nm(s):
    s = unicodedata.normalize('NFD', str(s))
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').upper().strip()


def key(dep, mun, zona, puesto, mesa):
    z = nm(zona)
    z = BOG_LOC.get(z, z)
    return (str(int(dep)), str(int(mun)), str(int(z)) if z.isdigit() else z,
            str(int(puesto)), str(int(mesa)))


print('leyendo edad por mesa (2V 2022) ...')
edad = {}
with open(f'{BASE}/Bases de datos/output_edad_1v/cache/p2v-2022.csv', encoding='utf-8') as f:
    rd = csv.reader(f); next(rd)
    for row in rd:
        try:
            k = key(row[1], row[5], row[6], row[7], row[8])
            tot = int(row[10] or 0)
            if tot < 40:
                continue
            jov = sum(int(row[i] or 0) for i in (12, 13, 14))
            muj = int(row[23] or 0)
        except (ValueError, IndexError):
            continue
        edad[k] = (100 * jov / tot, 100 * muj / tot, tot)
print(f'  {len(edad):,} mesas con edad')

print('leyendo escrutinio 2V 2022 por mesa ...')
voto = collections.defaultdict(lambda: [0, 0])
with open(f'{BASE}/Bases de datos/FINAL SUBIDA GCS/GCS_2022PRES2V.csv', encoding='latin-1') as f:
    rd = csv.reader(f, delimiter=';'); next(rd)
    for row in rd:
        if row[13] not in ('1', '2'):
            continue
        try:
            k = key(row[6], row[7], row[8], row[9], row[10])
            v = int(row[15] or 0)
        except (ValueError, IndexError):
            continue
        voto[k][0 if row[13] == '2' else 1] += v      # petro, rodolfo
print(f'  {len(voto):,} mesas con voto')

filas = []
for k, (pjov, pmuj, tot) in edad.items():
    if k in voto:
        p, r = voto[k]
        if p + r >= 40:
            filas.append((k[:4], pjov, pmuj, 100 * p / (p + r)))
print(f'  {len(filas):,} mesas cruzadas ({100*len(filas)/len(edad):.0f}% de las de edad)')


def corr(xs, ys):
    n = len(xs)
    if n < 3: return None
    mx = sum(xs)/n; my = sum(ys)/n
    sx = math.sqrt(sum((x-mx)**2 for x in xs)); sy = math.sqrt(sum((y-my)**2 for y in ys))
    return sum((x-mx)*(y-my) for x, y in zip(xs, ys))/(sx*sy) if sx*sy else None


print()
print('=' * 70)
print('CORRELACION DENTRO DEL PUESTO (efectos fijos de puesto)')
print('=' * 70)
por_puesto = collections.defaultdict(list)
for pc, pjov, pmuj, ppetro in filas:
    por_puesto[pc].append((pjov, pmuj, ppetro))

cs, cs_muj, pesos = [], [], []
for pc, v in por_puesto.items():
    if len(v) < 6:
        continue
    c = corr([x[0] for x in v], [x[2] for x in v])
    cm = corr([x[1] for x in v], [x[2] for x in v])
    if c is not None:
        cs.append(c); pesos.append(len(v))
    if cm is not None:
        cs_muj.append(cm)
print(f'  puestos con >=6 mesas cruzadas: {len(cs):,}')
print(f'  correlacion MEDIA dentro del puesto (% 18-30 vs % Petro): {st.mean(cs):+.3f}')
print(f'  mediana: {st.median(cs):+.3f}  |  puestos con correlacion positiva: '
      f'{100*sum(1 for c in cs if c>0)/len(cs):.1f}%')
print(f'  correlacion MEDIA (% mujeres vs % Petro): {st.mean(cs_muj):+.3f}')

# variacion intra-puesto: cuanto se mueve el voto de la mesa mas joven a la mas vieja
saltos, saltos_edad = [], []
for pc, v in por_puesto.items():
    if len(v) < 8:
        continue
    v2 = sorted(v)
    k = max(1, len(v2)//4)
    bajo = v2[:k]; alto = v2[-k:]
    saltos.append(st.mean(x[2] for x in alto) - st.mean(x[2] for x in bajo))
    saltos_edad.append(st.mean(x[0] for x in alto) - st.mean(x[0] for x in bajo))
print()
print(f'  en el puesto tipico, del cuartil de mesas MAS VIEJAS al de mas JOVENES:')
print(f'     la edad cambia {st.mean(saltos_edad):+.1f} pp de votantes 18-30')
print(f'     y el voto por Petro cambia {st.mean(saltos):+.1f} pp (mediana {st.median(saltos):+.1f})')
print(f'     puestos donde el salto es >= +10 pp: {100*sum(1 for s in saltos if s>=10)/len(saltos):.1f}%')
