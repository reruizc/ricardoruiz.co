#!/usr/bin/env python3
"""Top-N senadores más votados en Bogotá (voto preferente, CORCODIGO=01 SENADO,
CIR=1 territorial). Imprime cédula, nombre, partido, votos Bogotá."""
import csv, os, json
from collections import defaultdict

MMV = ("/Users/ricardoruiz/ricardoruiz.co/Bases de datos/DEPTOS_DECLARADOS/"
       "MMV_XXX_16_000_XXX_XX_XX_XXX_1009.csv")
cand = defaultdict(int)   # (ced, nombre, partido) -> votos
party = defaultdict(int)
with open(MMV, newline='', encoding='utf-8', errors='replace') as f:
    r = csv.reader(f, delimiter=';'); h = next(r)
    ix = {n: i for i, n in enumerate(h)}
    iCOR, iCIR = ix['CORCODIGO'], ix['CIR']
    iPARN, iCAN, iCED, iCANN, iV = ix['PARNOMBRE'], ix['CAN'], ix['CANCEDULA'], ix['CANNOMBRE'], ix['VOTOS']
    for row in r:
        if len(row) <= iV or row[iCOR] != '01' or row[iCIR] != '0':  # senado territorial
            continue
        try: v = int(row[iV])
        except ValueError: v = 0
        parn = row[iPARN].strip().upper(); cann = row[iCANN].strip().upper()
        bad = lambda s: ('BLANCO' in s or 'NULO' in s or 'NO MARCAD' in s
                         or 'CANDIDATOS TOTALES' in s)
        if bad(parn) or bad(cann):
            continue
        party[parn] += v
        if row[iCAN] != '000' and cann:
            cand[(row[iCED], cann, parn)] += v

top = sorted(cand.items(), key=lambda kv: -kv[1])[:12]
print("TOP SENADORES MÁS VOTADOS EN BOGOTÁ (voto preferente, territorial):\n")
for i, ((ced, nom, pn), v) in enumerate(top, 1):
    print(f"{i:>2}. {v:>9,}  {nom[:40]:40} [{pn[:34]}]  ced={ced}")
print("\nTOP 12 LISTAS SENADO por voto total en Bogotá:")
for pn, v in sorted(party.items(), key=lambda kv: -kv[1])[:12]:
    print(f"   {v:>9,}  {pn}")
json.dump([{'rank': i, 'cedula': ced, 'nombre': nom, 'partido': pn, 'votos_bogota': v}
           for i, ((ced, nom, pn), v) in enumerate(top, 1)],
          open(os.path.join(os.path.dirname(__file__), 'out', 'senado_top.json'), 'w'),
          ensure_ascii=False, indent=1)
print("\n[out/senado_top.json]")
