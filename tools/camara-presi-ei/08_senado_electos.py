#!/usr/bin/env python3
"""Pass 1 — determina los senadores ELECTOS más votados (preferente, nacional).
Senado: 100 curules, D'Hondt nacional, umbral 3%. Pacto y CD son listas CERRADAS
(sin preferente). En listas ABIERTAS los electos = top-(curules del partido) por
voto preferente. Salida: top senadores electos + sus cédulas (para el EI)."""
import csv, glob, os, json
from collections import defaultdict
BD = "/Users/ricardoruiz/ricardoruiz.co/Bases de datos"
MMVS = sorted(glob.glob(os.path.join(BD, "DEPTOS_DECLARADOS", "MMV_XXX_*_000_*.csv")))
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "out")

CLOSED = {'PACTO HISTÓRICO SENADO', 'PARTIDO CENTRO DEMOCRÁTICO', 'PARTIDO POLÍTICO OXÍGENO',
          'LA LISTA DE OVIEDO - CON TODA POR COLOMBIA', 'COLOMBIA SEGURA Y PRÓSPERA', 'PATRIOTAS'}
def bad(s): return ('BLANCO' in s or 'NULO' in s or 'NO MARCAD' in s or 'CANDIDATOS TOTALES' in s)

lst = defaultdict(int)                       # PARNOMBRE -> votos (lista completa)
cand = defaultdict(int)                       # (PARNOMBRE, ced, nombre) -> preferente
for fp in MMVS:
    with open(fp, newline='', encoding='utf-8', errors='replace') as f:
        r = csv.reader(f, delimiter=';'); h = next(r); ix = {x: i for i, x in enumerate(h)}
        iCOR, iCIR = ix['CORCODIGO'], ix['CIR']
        iPARN, iCAN, iCED, iCANN, iV = ix['PARNOMBRE'], ix['CAN'], ix['CANCEDULA'], ix['CANNOMBRE'], ix['VOTOS']
        for row in r:
            if len(row) <= iV or row[iCOR] != '01' or row[iCIR] != '0': continue
            parn = row[iPARN].strip().upper(); cann = row[iCANN].strip().upper()
            if bad(parn) or bad(cann): continue
            try: v = int(row[iV])
            except ValueError: continue
            lst[parn] += v
            if row[iCAN] != '000' and cann:
                cand[(parn, row[iCED], cann)] += v
    print(f"  {os.path.basename(fp)[:22]}")

valid = sum(lst.values()); umbral = valid * 0.03
elig = {p: t for p, t in lst.items() if t >= umbral}
seats = {p: 0 for p in elig}
for _ in range(100):
    best, who = -1, None
    for p, t in elig.items():
        q = t / (seats[p] + 1)
        if q > best: best, who = q, p
    if who: seats[who] += 1

print(f"\nválidos senado: {valid:,} · umbral 3% = {umbral:,.0f}")
print("Curules por lista (D'Hondt 100):")
for p, s in sorted(seats.items(), key=lambda x: -x[1]):
    if s: print(f"  {s:>2}  {p[:48]}{'  [CERRADA]' if p in CLOSED else ''}")

# electos: abiertas -> top-seats por preferente
electos = []   # (nombre, partido, cedula, votos)
for p, s in seats.items():
    if s == 0 or p in CLOSED: continue
    cc = sorted([(nm, ced, v) for (pp, ced, nm), v in cand.items() if pp == p], key=lambda x: -x[2])
    for nm, ced, v in cc[:s]:
        electos.append((nm, p, ced, v))
electos.sort(key=lambda x: -x[3])

print(f"\n=== TOP 12 SENADORES ELECTOS MÁS VOTADOS (preferente, listas abiertas) ===")
for i, (nm, p, ced, v) in enumerate(electos[:12], 1):
    print(f"{i:>2}. {v:>9,}  {nm[:36]:36} [{p[:28]}] ced={ced}")

# ¿Forero electo? (control)
forero = [(nm, p, v, 'ELECTO' if (nm, p, ced) in {(e[0], e[1], e[2]) for e in electos} else 'NO ELECTO')
          for (p, ced, nm), v in cand.items() if 'FORERO BOLIVAR' in nm]
print("\ncontrol Forero:", forero[:2])

json.dump([{'rank': i, 'nombre': nm, 'partido': p, 'cedula': ced, 'votos': v}
           for i, (nm, p, ced, v) in enumerate(electos[:8], 1)],
          open(os.path.join(OUT, 'senado_electos_top8.json'), 'w'), ensure_ascii=False, indent=1)
print("\n[out/senado_electos_top8.json]")
