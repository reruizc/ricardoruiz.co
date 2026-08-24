#!/usr/bin/env python3
"""Paso 2 — arma la tabla por PUESTO (Bogotá) que cruza Cámara 8-mar con
Presidencial 1V 31-may sobre la MISMA base (censo del puesto).

Salida: out/puestos_bogota.csv con, por puesto (localidad, puesto):
  censo, n_mesas,                          (COMUNAS_DATA 2026)
  cam_turnout,                             (todas las papeletas Cámara)
  <10 electos lista abierta por cédula>,   (voto preferente)
  pacto_list,                              (lista cerrada Pacto = sus 8 electos)
  pres_turnout, cepeda, abelardo,          (preconteo 1V)
  m_cam, m_pres                            (# mesas reportadas, QA)
"""
import csv, json, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
BD = "/Users/ricardoruiz/ricardoruiz.co/Bases de datos"
MMV = os.path.join(BD, "DEPTOS_DECLARADOS", "MMV_XXX_16_000_XXX_XX_XX_XXX_1009.csv")
PRES = os.path.join(BD, "nuevos archivos 1v 2026",
                    "PRECONTEO_1V_2026_MESA_con_Claudia.csv")
COM = os.path.join(BD, "COMUNAS_DATA.csv")

# 10 electos de lista abierta: cédula -> slug
OPEN = {
    '1010199050': 'briceno',   '80089333':  'uscategui',
    '80928007':   'cote',      '52704488':  'mosquera',
    '1136883552': 'lorduy',    '20389932':  'gordillo',
    '22698997':   'juvinao',   '16918687':  'toro',
    '32675115':   'bleidy',    '1026582159':'borda',
}
PACTO = 'MOVIMIENTO POLÍTICO PACTO HISTÓRICO'
# voto FULL de lista por partido (todos sus candidatos + logo) — unidad que la
# EI sí identifica. slug -> PARNOMBRE (normalizado mayúsculas)
PARTY_FULL = {
    'cd':        'PARTIDO CENTRO DEMOCRÁTICO',
    'verde':     'PARTIDO ALIANZA VERDE',
    'liberal':   'PARTIDO LIBERAL COLOMBIANO',
    'salvacion': 'MOVIMIENTO SALVACIÓN NACIONAL',
}
# voto FULL de lista al SENADO (cor=01, cir=0 territorial) por partido. Los 10
# senadores más votados de Bogotá caen en 4 listas; +Pacto y CD como polos.
SEN_LISTS = {
    'sen_pacto':     'PACTO HISTÓRICO SENADO',
    'sen_cd':        'PARTIDO CENTRO DEMOCRÁTICO',
    'sen_alianza':   'ALIANZA POR COLOMBIA',
    'sen_ahora':     'AHORA COLOMBIA',
    'sen_salvacion': 'MOVIMIENTO SALVACIÓN NACIONAL',
    'sen_liberal':   'PARTIDO LIBERAL COLOMBIANO',
}

def n2(s):
    s = (s or '').strip().upper()
    return f"{int(s):02d}" if s.isdigit() else s

def key(zz, pp):
    return (n2(zz), n2(pp))

# ---------- censo por puesto ----------
censo = {}          # (zz,pp) -> {censo, mesas}
with open(COM, newline='', encoding='utf-8', errors='replace') as f:
    r = csv.reader(f, delimiter=';'); next(r)
    for row in r:
        if row[0] != '16':
            continue
        censo[key(row[2], row[3])] = {'censo': int(row[14]), 'mesas': int(row[15])}
print(f"censo: {len(censo)} puestos Bogotá")

# ---------- Cámara por puesto ----------
cam_turn = defaultdict(int)
cam_prof = defaultdict(lambda: defaultdict(int))   # (zz,pp) -> slug -> votos
cam_mesas = defaultdict(set)
with open(MMV, newline='', encoding='utf-8', errors='replace') as f:
    r = csv.reader(f, delimiter=';'); h = next(r)
    ix = {n: i for i, n in enumerate(h)}
    iCOR, iCIR = ix['CORCODIGO'], ix['CIR']
    iZ, iP, iM = ix['ZONA'], ix['PUESTO'], ix['MESA']
    iPARN, iCED, iV = ix['PARNOMBRE'], ix['CANCEDULA'], ix['VOTOS']
    for row in r:
        if len(row) <= iV or row[iCOR] not in ('01', '02'):
            continue
        try: v = int(row[iV])
        except ValueError: v = 0
        k = key(row[iZ], row[iP])
        if row[iCOR] == '01':                   # SENADO: listas territoriales (cir=0)
            if row[iCIR] == '0':
                parn = row[iPARN].strip().upper()
                for slug, pn in SEN_LISTS.items():
                    if parn == pn:
                        cam_prof[k][slug] += v
            continue
        cam_turn[k] += v                       # toda papeleta Cámara (incl. CIR 4/5, blanco/nulo)
        cam_mesas[k].add(row[iM])
        if row[iCIR] != '1':                   # perfiles solo territorial
            continue
        ced = row[iCED]
        parn = row[iPARN].strip().upper()
        if ced in OPEN:
            cam_prof[k][OPEN[ced]] += v
        if parn == PACTO:
            cam_prof[k]['pacto_list'] += v
        for slug, pn in PARTY_FULL.items():
            if parn == pn:
                cam_prof[k][slug] += v
print(f"cámara: {len(cam_turn)} puestos · {sum(cam_turn.values()):,} papeletas")

# ---------- Presidencial por puesto ----------
pres_turn = defaultdict(int); cep = defaultdict(int); abe = defaultdict(int)
pres_mesas = defaultdict(set)
with open(PRES, newline='', encoding='utf-8-sig', errors='replace') as f:
    r = csv.DictReader(f)
    for row in r:
        if row['cod_departamento'].strip('"') != '16':
            continue
        k = key(row['zona'].strip('"'), row['puesto'].strip('"'))
        pres_turn[k] += int(row['total_votos_urna'])
        cep[k] += int(row['Iván Cepeda'])
        abe[k] += int(row['Abelardo De La Espriella'])
        pres_mesas[k].add(row['num_mesa'].strip('"'))
print(f"presi: {len(pres_turn)} puestos · {sum(pres_turn.values()):,} votos")

# ---------- join + escribir ----------
allk = set(censo) | set(cam_turn) | set(pres_turn)
PARTY_SLUGS = ['pacto_list'] + list(PARTY_FULL.keys()) + list(SEN_LISTS.keys())
cols = ['zz', 'pp', 'censo', 'n_mesas', 'cam_turnout'] + list(OPEN.values()) + \
       PARTY_SLUGS + ['pres_turnout', 'cepeda', 'abelardo', 'm_cam', 'm_pres']
rows_out = []
miss_censo = matched = 0
for k in sorted(allk):
    if k[0] in ('90', '98'):      # excluir Corferias / cárceles
        continue
    c = censo.get(k)
    if not c:
        miss_censo += 1
        continue
    if k in cam_turn and k in pres_turn:
        matched += 1
    pr = cam_prof[k]
    rows_out.append([k[0], k[1], c['censo'], c['mesas'], cam_turn.get(k, 0)] +
                    [pr.get(s, 0) for s in OPEN.values()] +
                    [pr.get(s, 0) for s in PARTY_SLUGS] +
                    [pres_turn.get(k, 0), cep.get(k, 0), abe.get(k, 0),
                     len(cam_mesas.get(k, ())), len(pres_mesas.get(k, ()))])
with open(os.path.join(OUT, 'puestos_bogota.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(cols); w.writerows(rows_out)

print(f"\nescrito: {len(rows_out)} puestos (excl 90/98) · matched cam&pres: {matched}"
      f" · sin censo: {miss_censo}")
# sanity totals
tc = sum(r[4] for r in rows_out); tp = sum(r[-5] for r in rows_out)
tcep = sum(r[-4] for r in rows_out); tabe = sum(r[-3] for r in rows_out)
tcen = sum(r[2] for r in rows_out)
print(f"censo(excl90/98)={tcen:,} · cam_turnout={tc:,} · pres_turnout={tp:,}")
print(f"Cepeda Bogotá={tcep:,} · Abelardo Bogotá={tabe:,}")
# perfiles citywide (control vs paso 1)
import collections
agg = collections.defaultdict(int)
prof_slugs = list(OPEN.values()) + PARTY_SLUGS
for r in rows_out:
    for i, s in enumerate(prof_slugs):
        agg[s] += r[5 + i]
print("electos (control):", {k: f"{v:,}" for k, v in agg.items() if k in OPEN.values()})
print("blocs partido (control):", {k: f"{v:,}" for k, v in agg.items() if k in PARTY_SLUGS})
