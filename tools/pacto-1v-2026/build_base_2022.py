#!/usr/bin/env python3
# Capa base 2022: GCS 1V y 2V -> por puesto (Petro, Fico, Rodolfo, Fajardo + base) -> une a georef.
import csv,json,os
BASE='Bases de datos'; G=f'{BASE}/FINAL SUBIDA GCS'; OUT=f'{BASE}/output_pacto_1v_2026'
def key(row):
    return f"{int(row['COD_DDE']):02d}{int(row['COD_MME']):03d}{int(row['COD_ZZ']):02d}{int(row['COD_PP']):02d}"
def des(row): return (row.get('DES_CAN') or '').upper()
def stream(fn,want):  # want: dict des_substr->campo
    agg={}
    with open(fn,newline='',encoding='utf-8',errors='ignore') as f:
        r=csv.DictReader((l.replace('﻿','') for l in f),delimiter=';')
        for row in r:
            try: k=key(row)
            except: continue
            try: v=int(row['NUM_VOT'] or 0)
            except: v=0
            cod=row.get('COD_CAN','')
            d=agg.setdefault(k,{})
            # base = candidatos reales (cod<900) + blanco(996)
            if cod not in ('997','998','999'):
                d['base']=d.get('base',0)+v
            n=des(row)
            for sub,campo in want.items():
                if sub in n: d[campo]=d.get(campo,0)+v
    return agg

print('1V…'); a1=stream(f'{G}/GCS_2022PRES1V.csv',{'PETRO':'petro','GUTIERREZ':'fico','RODOLFO':'rodolfo','FAJARDO':'fajardo'})
print('2V…'); a2=stream(f'{G}/GCS_2022PRES2V.csv',{'PETRO':'petro','RODOLFO':'rodolfo'})
print(f'puestos 1V {len(a1):,} · 2V {len(a2):,}')

# georef
geo={}
with open(f'{BASE}/PUESTOS_GEOREF.csv',newline='',encoding='utf-8',errors='ignore') as f:
    for row in csv.DictReader(f,delimiter=';'):
        cc=(row.get('CÓDIGO COMPLETO') or '').strip()
        if len(cc)>=9: geo[cc]={'barrio':(row.get('BARRIO') or '').strip(),'comuna':(row.get('NOMBRE COMUNA') or '').strip()}

out={}
allk=set(a1)|set(a2)
for k in allk:
    d1=a1.get(k,{}); d2=a2.get(k,{}); g=geo.get(k,{})
    out[k]={'dep':k[:2],'mun':k[2:5],'zona':k[5:7],'puesto':k[7:9],
            'petro1v':d1.get('petro',0),'fico1v':d1.get('fico',0),'rodolfo1v':d1.get('rodolfo',0),'fajardo1v':d1.get('fajardo',0),'base1v':d1.get('base',0),
            'petro2v':d2.get('petro',0),'rodolfo2v':d2.get('rodolfo',0),'base2v':d2.get('base',0),
            'barrio':g.get('barrio',''),'comuna':g.get('comuna','')}
# verificación nacional
P1=sum(d['petro1v'] for d in out.values()); P2=sum(d['petro2v'] for d in out.values())
B1=sum(d['base1v'] for d in out.values()); B2=sum(d['base2v'] for d in out.values())
print(f'\nPetro 1V {P1:,} ({P1/B1*100:.1f}% de {B1:,})  [oficial ~8,54M / 40,3%]')
print(f'Petro 2V {P2:,} ({P2/B2*100:.1f}% de {B2:,})  [oficial ~11,29M / 50,4%]')
mj=sum(1 for d in out.values() if d['barrio'])
print(f'join georef: {mj}/{len(out)} ({mj/len(out)*100:.1f}%)')
json.dump(list(out.values()),open(f'{OUT}/master_2022_puesto.json','w'))
print(f'✓ master_2022_puesto.json ({len(out)} puestos)')
