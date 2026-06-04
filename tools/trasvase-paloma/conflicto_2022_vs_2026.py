#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zonas de conflicto (CITREP) — Petro 2022 vs Cepeda 2026 por región.
Extrae los municipios de conflicto de los CITREP*-MMV (escrutinio Cámara de paz)
y compara la participación de Petro 1V-2022 (GCS) con Cepeda 1V-2026 (preconteo)."""
import csv, glob, collections
def k(d,m): return f"{int(d)}-{int(m)}"
# municipios de conflicto (CITREP) con código electoral + depto
conflict={}
for fp in glob.glob('Bases de datos/DEPTOS_DECLARADOS/CITREP*-MMV*.csv'):
    with open(fp,encoding='utf-8-sig',newline='') as f:
        rd=csv.reader(f,delimiter=';'); h=next(rd); ix={c.strip():i for i,c in enumerate(h)}
        for r in rd:
            if len(r)<=ix.get('MUNNOMBRE',5): continue
            try: conflict[k(r[ix['DEP']],r[ix['MUN']])]=(r[ix['DEPNOMBRE']],r[ix['MUNNOMBRE']])
            except: pass
# Petro 2022
p22=collections.defaultdict(lambda:{'petro':0,'val':0})
with open('Bases de datos/FINAL SUBIDA GCS/GCS_2022PRES1V.csv',encoding='utf-8-sig',errors='replace') as f:
    rd=csv.reader(f,delimiter=';');h=next(rd);ix={c.strip():i for i,c in enumerate(h)}
    for r in rd:
        if len(r)<=ix['NUM_VOT']: continue
        try: key=k(r[ix['COD_DDE']],r[ix['COD_MME']])
        except: continue
        if key not in conflict: continue
        cod=r[ix['COD_CAN']]; v=int(r[ix['NUM_VOT']]or 0)
        if cod and cod.isdigit() and int(cod)>=996: continue
        p22[key]['val']+=v
        if 'PETRO' in r[ix['DES_CAN']].upper(): p22[key]['petro']+=v
# Cepeda 2026
CANDS=['Iván Cepeda','Santiago Botero','Abelardo De La Espriella','Mauricio Lizcano','Miguel Uribe','Sondra Macollins','Roy Barreras','Carlos Caicedo','Gustavo Matamoros','Paloma Valencia','Sergio Fajardo','Gilberto Murillo','Claudia López']
c26=collections.defaultdict(lambda:{'ce':0,'ab':0,'val':0})
with open('Bases de datos/nuevos archivos 1v 2026/PRECONTEO_1V_2026_MESA_nombres_corregidos.csv',encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        try: key=k(r['cod_departamento'],r['cod_municipio'])
        except: continue
        if key not in conflict: continue
        c26[key]['ce']+=int(r['Iván Cepeda']or 0); c26[key]['ab']+=int(r['Abelardo De La Espriella']or 0)
        c26[key]['val']+=sum(int(r[c]or 0) for c in CANDS)
REGION={'CAUCA':'Cauca','NARIÑO':'Nariño','NORTE DE SAN':'Catatumbo','ARAUCA':'Arauca','PUTUMAYO':'Putumayo',
'ANTIOQUIA':'Bajo Cauca/Nordeste','CAQUETA':'Caquetá','CHOCO':'Chocó','BOLIVAR':'Sur de Bolívar','META':'Meta',
'GUAVIARE':'Guaviare','SUCRE':'Montes de María','TOLIMA':'Sur del Tolima','VALLE':'Valle','HUILA':'Huila'}
agg=collections.defaultdict(lambda:{'petro':0,'pv':0,'ce':0,'ab':0,'cv':0})
for key,(dn,mn) in conflict.items():
    reg=REGION.get(dn,dn)
    agg[reg]['petro']+=p22[key]['petro'];agg[reg]['pv']+=p22[key]['val']
    agg[reg]['ce']+=c26[key]['ce'];agg[reg]['ab']+=c26[key]['ab'];agg[reg]['cv']+=c26[key]['val']
print(f"{'Región':<24}{'Petro22':>9}{'%':>5}{'Cepeda26':>10}{'%':>5}{'Δpp':>6}{'Δvotos':>9}  gana26")
for reg,a in sorted(agg.items(),key=lambda x:(100*x[1]['ce']/x[1]['cv']-100*x[1]['petro']/x[1]['pv']) if x[1]['pv'] and x[1]['cv'] else 0):
    if a['pv']<500 or a['cv']<500: continue
    pp=100*a['petro']/a['pv'];cp=100*a['ce']/a['cv']
    print(f"{reg:<24}{a['petro']:>9,}{pp:>4.0f}%{a['ce']:>10,}{cp:>4.0f}%{cp-pp:>+5.0f}{a['ce']-a['petro']:>+9,}  {'Cepeda' if a['ce']>=a['ab'] else 'Abelardo'}")
