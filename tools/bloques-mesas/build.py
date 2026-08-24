#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prueba de rachas (runs test) mesa por mesa dentro de cada puesto de votacion.

Replica el estadistico que se presento como "prueba de fraude" en 2026
(bloques de mesas consecutivas ganadas por el mismo candidato, z-score muy
negativo) y lo corre contra:

  1. 2V 2026  (Cepeda vs Abelardo)      <- la eleccion acusada
  2. 2V 2022  (Petro vs Rodolfo)        <- control: la eleccion que gano Petro
  3. 2V 2018  (Duque vs Petro)          <- control
  4. La COMPOSICION ETARIA de las mesas (Edadygenero, dato oficial RNEC)
     -> si la edad de los votantes muestra el MISMO patron de bloques,
        el estadistico esta midiendo el orden de cedula, no fraude.

La mesa NO es una muestra aleatoria del puesto: la RNEC asigna por rango de
cedula, que ordena por edad (cedulas viejas = votantes viejos) y por sexo
(las cedulas de mujeres arrancan en 20.000.000). El runs test asume
intercambiabilidad; aqui esa premisa es falsa por diseno del sistema.

Salida: Bases de datos/output_bloques/
"""
import csv, json, math, os, collections, statistics as st

BASE = '/Users/ricardoruiz/ricardoruiz.co'
OUT = f'{BASE}/Bases de datos/output_bloques'
Z_CUT = -2.0        # el umbral que usaron
MIN_MESAS = 8       # descartan puestos chicos


def runs_z(seq):
    """z de la prueba de rachas de Wald-Wolfowitz sobre una secuencia binaria."""
    n1 = sum(1 for x in seq if x == 1)
    n2 = len(seq) - n1
    if n1 < 1 or n2 < 1:
        return None
    N = n1 + n2
    runs = 1 + sum(1 for a, b in zip(seq, seq[1:]) if a != b)
    mu = 2 * n1 * n2 / N + 1
    var = 2 * n1 * n2 * (2 * n1 * n2 - N) / (N * N * (N - 1))
    if var <= 0:
        return None
    return (runs - mu) / math.sqrt(var)


def evaluar(puestos, etiqueta):
    """puestos: {pcode: [(mesa_num, valA, valB), ...]}"""
    zs, det = [], []
    for pc, mesas in puestos.items():
        if len(mesas) < MIN_MESAS:
            continue
        mesas = sorted(mesas, key=lambda m: m[0])
        seq = [1 if a > b else 0 for _, a, b in mesas if a != b]
        if len(seq) < MIN_MESAS:
            continue
        z = runs_z(seq)
        if z is None:            # puesto unanime -> descartado, como ellos
            continue
        zs.append(z)
        det.append((pc, len(seq), z))
    n = len(zs)
    flag = sum(1 for z in zs if z < Z_CUT)
    esperados = n * 0.0228        # P(Z < -2) bajo la hipotesis de azar
    return dict(etiqueta=etiqueta, puestos_evaluados=n, con_bloques=flag,
                esperados_por_azar=round(esperados, 1),
                razon=round(flag / esperados, 1) if esperados else None,
                z_medio=round(st.mean(zs), 3) if zs else None,
                pct=round(100 * flag / n, 1) if n else 0), det


# ---------------------------------------------------------------- 2026 2V
def cargar_2026():
    p = collections.defaultdict(dict)
    with open(f'{BASE}/Bases de datos/output_2v/PRECONTEO_2V_2026_MESA.csv', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            pc = f"{r['COD_DEP']}-{r['COD_MUN']}-{r['COD_ZONA']}-{r['COD_PUESTO']}"
            try:
                mesa = int(r['COD_MESA']); v = int(r['VOTOS'] or 0)
            except ValueError:
                continue
            d = p[pc].setdefault(mesa, [0, 0])
            if r['COD_CAN'] == '2': d[0] += v          # Cepeda
            elif r['COD_CAN'] == '3': d[1] += v        # Abelardo
    return {pc: [(m, v[0], v[1]) for m, v in ms.items()] for pc, ms in p.items()}


# ---------------------------------------------------------------- GCS 2V
def cargar_gcs(archivo, cod_a, cod_b):
    p = collections.defaultdict(dict)
    with open(f'{BASE}/Bases de datos/FINAL SUBIDA GCS/{archivo}', encoding='latin-1') as f:
        rd = csv.reader(f, delimiter=';'); next(rd)
        for row in rd:
            if row[13] not in (cod_a, cod_b):
                continue
            pc = f"{row[6]}-{row[7]}-{row[8]}-{row[9]}"
            try:
                mesa = int(row[10]); v = int(row[15] or 0)
            except ValueError:
                continue
            d = p[pc].setdefault(mesa, [0, 0])
            d[0 if row[13] == cod_a else 1] += v
    return {pc: [(m, v[0], v[1]) for m, v in ms.items()] for pc, ms in p.items()}


# ------------------------------------------------- composicion etaria 2022
COLS_JOVEN = [12, 13, 14]          # 18-20, 21-25, 26-30
COLS_VIEJO = [20, 21]              # 56-60, mayor a 60


def cargar_edad():
    """Devuelve puestos con (mesa, jovenes, viejos) y (mesa, hombres, mujeres)."""
    edad = collections.defaultdict(dict)
    sexo = collections.defaultdict(dict)
    perfil = []
    with open(f'{BASE}/Bases de datos/output_edad_1v/cache/p2v-2022.csv', encoding='utf-8') as f:
        rd = csv.reader(f); next(rd)
        for row in rd:
            try:
                mesa = int(row[8])
                jov = sum(int(row[i] or 0) for i in COLS_JOVEN)
                vie = sum(int(row[i] or 0) for i in COLS_VIEJO)
                hom = int(row[22] or 0); muj = int(row[23] or 0)
                tot = int(row[10] or 0)
            except (ValueError, IndexError):
                continue
            pc = f"{row[1]}-{row[5]}-{row[6]}-{row[7]}"
            edad[pc][mesa] = [jov, vie]
            sexo[pc][mesa] = [hom, muj]
            perfil.append((pc, mesa, tot, jov, vie, hom, muj))
    return ({pc: [(m, v[0], v[1]) for m, v in ms.items()] for pc, ms in edad.items()},
            {pc: [(m, v[0], v[1]) for m, v in ms.items()] for pc, ms in sexo.items()},
            perfil)


def gradiente(perfil):
    """% jovenes, % >56 y % mujeres por posicion relativa de la mesa en el puesto."""
    porpc = collections.defaultdict(list)
    for pc, mesa, tot, jov, vie, hom, muj in perfil:
        porpc[pc].append((mesa, tot, jov, vie, hom, muj))
    dec = collections.defaultdict(lambda: [0, 0, 0, 0])
    for pc, ms in porpc.items():
        if len(ms) < 10:
            continue
        ms.sort()
        n = len(ms)
        for i, (mesa, tot, jov, vie, hom, muj) in enumerate(ms):
            d = min(9, int(10 * i / n))
            dec[d][0] += tot; dec[d][1] += jov; dec[d][2] += vie; dec[d][3] += muj
    return {d: dict(pct_joven=round(100*v[1]/v[0], 1), pct_56mas=round(100*v[2]/v[0], 1),
                    pct_mujer=round(100*v[3]/v[0], 1)) for d, v in sorted(dec.items()) if v[0]}


def gradiente_voto(puestos):
    """% del candidato A por decil de posicion de mesa dentro del puesto."""
    dec = collections.defaultdict(lambda: [0, 0])
    for pc, mesas in puestos.items():
        if len(mesas) < 10:
            continue
        mesas = sorted(mesas, key=lambda m: m[0])
        n = len(mesas)
        for i, (mesa, a, b) in enumerate(mesas):
            d = min(9, int(10 * i / n))
            dec[d][0] += a; dec[d][1] += b
    return {d: round(100*v[0]/(v[0]+v[1]), 1) for d, v in sorted(dec.items()) if v[0]+v[1]}


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    res, grads = [], {}

    print('cargando 2V 2026 ...', flush=True)
    p26 = cargar_2026()
    r, det26 = evaluar(p26, '2V 2026 · Cepeda vs Abelardo')
    res.append(r); grads['voto_2026_pct_cepeda'] = gradiente_voto(p26)

    print('cargando 2V 2022 ...', flush=True)
    p22 = cargar_gcs('GCS_2022PRES2V.csv', '2', '1')      # Petro / Rodolfo
    r22, _ = evaluar(p22, '2V 2022 · Petro vs Rodolfo')
    res.append(r22); grads['voto_2022_pct_petro'] = gradiente_voto(p22)

    print('cargando 2V 2018 ...', flush=True)
    p18 = cargar_gcs('GCS_2018PRES2V.csv', '2', '1')
    r18, _ = evaluar(p18, '2V 2018 · candidato 2 vs 1')
    res.append(r18)

    print('cargando composicion etaria 2022 (Edadygenero, RNEC) ...', flush=True)
    ed, sx, perfil = cargar_edad()
    re_, _ = evaluar(ed, 'EDAD de los votantes 2022 (jovenes vs mayores)')
    rs_, _ = evaluar(sx, 'SEXO de los votantes 2022 (hombres vs mujeres)')
    res.append(re_); res.append(rs_)
    grads['perfil_mesa_2022'] = gradiente(perfil)

    print()
    print('=' * 88)
    print(f"{'serie':46s} {'puestos':>8s} {'con bloques':>12s} {'esperados':>10s} {'razon':>7s}")
    print('=' * 88)
    for x in res:
        print(f"  {x['etiqueta']:44s} {x['puestos_evaluados']:8,} {x['con_bloques']:12,} "
              f"{x['esperados_por_azar']:10.1f} {x['razon']:6.1f}x")
    print()
    print('gradiente dentro del puesto (decil de posicion de la mesa):')
    print(f"  {'decil':6s} {'% 18-30':>9s} {'% 56+':>8s} {'% mujeres':>10s} | {'% Petro 22':>11s} {'% Cepeda 26':>12s}")
    for d in range(10):
        p = grads['perfil_mesa_2022'].get(d, {})
        print(f"  {d+1:6d} {p.get('pct_joven',0):8.1f}% {p.get('pct_56mas',0):7.1f}% {p.get('pct_mujer',0):9.1f}% |"
              f" {grads['voto_2022_pct_petro'].get(d,0):10.1f}% {grads['voto_2026_pct_cepeda'].get(d,0):11.1f}%")

    json.dump(dict(resumen=res, gradientes=grads), open(f'{OUT}/bloques.json', 'w'),
              ensure_ascii=False, indent=1)
    with open(f'{OUT}/puestos-z-2026.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, delimiter=';'); w.writerow(['pcode', 'mesas', 'z'])
        for pc, n, z in sorted(det26, key=lambda x: x[2]):
            w.writerow([pc, n, round(z, 3)])
    print(f'\n-> {OUT}/')
