#!/usr/bin/env python3
"""Diagnóstico: ¿por qué solo ~50% de mesas hacen match a nivel nacional?
Compara Antioquia (01): mesas senado (MMV) vs mesas presidencial (preconteo),
CIR del senado, nombres de lista. Y calcula la línea base nacional REAL."""
import csv, os
from collections import defaultdict
BD = "/Users/ricardoruiz/ricardoruiz.co/Bases de datos"
PRES = os.path.join(BD, "nuevos archivos 1v 2026", "PRECONTEO_1V_2026_MESA_con_Claudia.csv")
ANT = os.path.join(BD, "DEPTOS_DECLARADOS", "MMV_XXX_01_000_XXX_XX_XX_XXX_1000.csv")
def n(s):
    s=(s or '').strip().upper(); return str(int(s)) if s.isdigit() else s

# baseline nacional real + mesas presidencial por dep
cep=abe=tot=0; pres_mesas=defaultdict(set); pres01=set()
with open(PRES,encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        d=row['cod_departamento'].strip('"'); t=int(row['total_votos_urna'])
        cep+=int(row['Iván Cepeda']); abe+=int(row['Abelardo De La Espriella']); tot+=t
        pres_mesas[d].add((n(row['zona'].strip('"')),n(row['puesto'].strip('"')),n(row['num_mesa'].strip('"'))))
        if d=='01': pres01.add((n(row['zona'].strip('"')),n(row['puesto'].strip('"')),n(row['num_mesa'].strip('"'))))
print(f"NACIONAL real (todas las mesas preconteo): Cepeda {cep/tot*100:.1f}% / Abelardo {abe/tot*100:.1f}%")
print(f"total mesas preconteo: {sum(len(v) for v in pres_mesas.values()):,} · Antioquia(01): {len(pres01):,}\n")

# Antioquia senado
cir=defaultdict(int); names=defaultdict(int); sen_mesas=set(); cam_mesas=set()
with open(ANT,encoding='utf-8',errors='replace') as f:
    r=csv.reader(f,delimiter=';'); h=next(r); ix={x:i for i,x in enumerate(h)}
    iCOR,iCIR,iZ,iP,iM,iPARN,iV=ix['CORCODIGO'],ix['CIR'],ix['ZONA'],ix['PUESTO'],ix['MESA'],ix['PARNOMBRE'],ix['VOTOS']
    for row in r:
        if len(row)<=iV: continue
        if row[iCOR]=='01':
            cir[row[iCIR]]+=1
            if row[iCIR]=='0':
                try: v=int(row[iV])
                except: v=0
                names[row[iPARN].strip().upper()]+=v
                sen_mesas.add((n(row[iZ]),n(row[iP]),n(row[iM])))
        elif row[iCOR]=='02':
            cam_mesas.add((n(row[iZ]),n(row[iP]),n(row[iM])))
print(f"Antioquia SENADO cir distinct: {dict(cir)}")
print(f"Antioquia mesas: senado(cir0)={len(sen_mesas):,} · cámara={len(cam_mesas):,} · presi={len(pres01):,}")
print(f"  match senado∩presi: {len(sen_mesas & pres01):,}")
print("Top 12 listas senado Antioquia (nombre exacto · votos):")
for nm,v in sorted(names.items(),key=lambda x:-x[1])[:12]:
    print(f"   {v:>9,}  '{nm}'")
