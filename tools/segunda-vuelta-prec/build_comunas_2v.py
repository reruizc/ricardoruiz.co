#!/usr/bin/env python3
# Agrega el voto 1V/2V por COMUNA/LOCALIDAD de cada ciudad principal (desde el
# master, que ya trae la comuna por puesto). -> output_2v/comunas_2v.json
import json, collections, re
OUT='Bases de datos/output_2v'
M=json.load(open(f'{OUT}/master_unificado_puesto.json'))
CITIES={'01001':'Medellín','16001':'Bogotá','31001':'Cali','03001':'Barranquilla','05001':'Cartagena',
 '27001':'Bucaramanga','25001':'Cúcuta','24001':'Pereira','09001':'Manizales','23001':'Pasto',
 '21001':'Santa Marta','03052':'Soledad','11001':'Popayán','31019':'Buenaventura','17001':'Quibdó',
 '23139':'Tumaco','31079':'Palmira','28001':'Sincelejo'}
def cln(raw):
    s=re.sub(r'^\d+','',(raw or '')).strip(); s=re.sub(r'(?i)\b(comuna|localidad|corregimiento)\b','',s).strip()
    return (s.title() or 'Sin dato')
def noise(s): return s.upper() in ('SIN DATO','OTROS','CORR','CIUDAD','NULL','SN','NO APLICA','')
agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0,0,0]))
for r in M:
    if r['cod5'] not in CITIES or r['cep2'] is None: continue
    com=cln(r.get('comuna',''))
    a=agg[r['cod5']][com]; a[0]+=r['cep1']; a[1]+=r['abe1']; a[2]+=r['cep2']; a[3]+=r['abe2']
OUTd={}
for code,coms in agg.items():
    rows=[]
    for com,(c1,a1,c2,a2) in coms.items():
        if c2+a2<300 or noise(com): continue
        m2=100*(a2-c2)/(a2+c2) if (a2+c2) else 0; m1=100*(a1-c1)/(a1+c1) if (a1+c1) else 0
        rows.append({'comuna':com,'cep2':int(c2),'abe2':int(a2),'m2':round(m2,1),'swing':round(m2-m1,1),'gana':'A' if a2>=c2 else 'C'})
    rows.sort(key=lambda r:-(r['cep2']+r['abe2']))
    OUTd[CITIES[code]]=rows
    print(f'  {CITIES[code]:14s} {len(rows)} comunas/localidades')
json.dump(OUTd,open(f'{OUT}/comunas_2v.json','w'),ensure_ascii=False,indent=1)
print(f'-> {OUT}/comunas_2v.json')
