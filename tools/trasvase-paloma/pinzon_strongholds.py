#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""¿Restringiendo a las mesas donde Pinzón concentró su voto se identifica mejor
su trasvase a Paloma? Concentración + cotas por subconjunto + descriptivo 1V."""
import csv, json, os, glob
import numpy as np
csv.field_size_limit(1<<24)
ROOT="/Users/ricardoruiz/ricardoruiz.co"
PRE=os.path.join(ROOT,"Bases de datos/nuevos archivos 1v 2026/PRECONTEO_1V_2026_MESA_nombres_corregidos.csv")
MMVDIR=os.path.join(ROOT,"Bases de datos/DEPTOS_DECLARADOS")
CENSO=os.path.join(ROOT,"Bases de datos/censos-puesto-2026.json")
def nz(x):
    x=str(x).strip(); return str(int(x)) if x.isdigit() else x.upper()
def mk(d,m,z,p,me): return f"{d}-{m}-{nz(z)}-{nz(p)}-{nz(me)}"
def pp(d,m,z,p):
    z=f"{int(z):02d}" if str(z).strip().isdigit() else z
    p=f"{int(p):02d}" if str(p).strip().isdigit() else p
    return f"{d}-{m}-{z}-{p}"
PALOMA='PALOMA SUSANA VALENCIA LASERNA'; PINZON='JUAN CARLOS PINZON BUENO'
pres={}; nmesas={}
with open(PRE,encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        k=mk(r['cod_departamento'],r['cod_municipio'],r['zona'],r['puesto'],r['num_mesa'])
        pres[k]=dict(ab=int(r['Abelardo De La Espriella']or 0),pa=int(r['Paloma Valencia']or 0),
                     ce=int(r['Iván Cepeda']or 0),sf=int(r['Sergio Fajardo']or 0),
                     urna=int(r['total_votos_urna']or 0),
                     candp=sum(int(r[c]or 0) for c in ['Iván Cepeda','Santiago Botero','Abelardo De La Espriella','Mauricio Lizcano','Miguel Uribe','Sondra Macollins','Roy Barreras','Carlos Caicedo','Gustavo Matamoros','Paloma Valencia','Sergio Fajardo','Gilberto Murillo','Claudia López'])+int(r['votos_blanco']or 0))
        k2=pp(r['cod_departamento'],r['cod_municipio'],r['zona'],r['puesto']); nmesas[k2]=nmesas.get(k2,0)+1
cons={}
for fp in sorted(glob.glob(os.path.join(MMVDIR,"MMV_XXX_*.csv"))):
    if "CITREP" in fp: continue
    with open(fp,encoding='utf-8-sig',newline='') as f:
        rd=csv.reader(f,delimiter=';'); next(rd,None)
        for c in rd:
            if len(c)<19 or c[10]!='06' or c[13]!='0200': continue
            k=mk(c[0],c[2],c[4],c[5],c[7]); v=int(c[18]or 0); d=cons.setdefault(k,{'pal':0,'pin':0,'otg':0})
            if c[17]==PALOMA: d['pal']+=v
            elif c[17]==PINZON: d['pin']+=v
            else: d['otg']+=v
censo=json.load(open(CENSO))['porPuesto']
keys=sorted(set(pres)&set(cons))
rows=[]
for k in keys:
    c=cons[k]; pr=pres[k]; dep,mun,z,p,m=k.split('-')
    if c['pin']<=0: continue
    ppk=pp(dep,mun,z,p) if z.isdigit() and p.isdigit() else None
    cens=censo.get(ppk); nm=nmesas.get(ppk,1) if ppk else 1
    N=cens/max(nm,1) if cens else None
    if N is None or N<max(pr['candp'],c['pal']+c['pin']+c['otg']): N=max(pr['candp'],c['pal']+c['pin']+c['otg'])
    gran=c['pal']+c['pin']+c['otg']
    rows.append(dict(pin=c['pin'],share=c['pin']/gran if gran else 0,N=N,
                     ab=pr['ab'],pa=pr['pa'],ce=pr['ce'],sf=pr['sf'],urna=pr['urna'],
                     plur=(c['pin']>=c['pal'] and c['pin']>=c['otg'])))
totPin=sum(r['pin'] for r in rows)
print(f"Mesas con voto de Pinzón: {len(rows):,} | total Pinzón {totPin:,}")
# concentración
bypin=sorted(rows,key=lambda r:-r['pin']); cum=0; n70=0
for i,r in enumerate(bypin):
    cum+=r['pin']
    if cum>=0.7*totPin: n70=i+1; break
print(f"Concentración: el 70% de sus votos está en sus {n70:,} mesas más fuertes ({100*n70/len(rows):.1f}% de las mesas).")
shares=sorted(r['share'] for r in rows)
print(f"Share de Pinzón en la consulta de cada mesa: mediana {100*shares[len(shares)//2]:.1f}% · máx {100*max(shares):.1f}%")
plur=sum(1 for r in rows if r['plur'])
print(f"Mesas donde Pinzón fue 1° de la Gran Consulta: {plur:,} ({100*plur/len(rows):.2f}%)")
print(f"Mesas donde Pinzón ≥20% de la consulta: {sum(1 for r in rows if r['share']>=0.20):,} | ≥30%: {sum(1 for r in rows if r['share']>=0.30):,}\n")
def bounds(sub,label):
    if not sub: print(f"  {label}: (vacío)"); return
    tp=sum(r['pin'] for r in sub)
    lo=sum(max(0,r['pin']+r['pa']-r['N']) for r in sub)/tp
    hi=sum(min(r['pin'],r['pa']) for r in sub)/tp
    A=sum(r['ab'] for r in sub);P=sum(r['pa'] for r in sub);C=sum(r['ce'] for r in sub);U=sum(r['urna'] for r in sub)
    print(f"  {label:<34} cota Pinzón→Paloma [{100*lo:4.1f}% – {100*hi:4.1f}%] | 1V de la mesa: Abel {100*A/U:.0f}% Palo {100*P/U:.0f}% Cep {100*C/U:.0f}%  (n={len(sub):,})")
print("Cota Pinzón→Paloma + voto 1V de la mesa, por subconjunto:")
bounds(rows,"todas las mesas con Pinzón")
bounds([r for r in rows if r['share']>=0.10],"Pinzón ≥10% de la consulta")
bounds([r for r in rows if r['share']>=0.20],"Pinzón ≥20% de la consulta")
bounds([r for r in rows if r['share']>=0.30],"Pinzón ≥30% de la consulta")
bounds(bypin[:n70],"top mesas = 70% de su voto")
