#!/usr/bin/env python3
# Motor 2: completa municipio (todos los bloques), ciudades por comuna/barrio (todos los bloques),
# y el cruce Cepeda-crece + abstención-sube (participación 2022 vs 2026).
import json,re,unicodedata,csv
OUT='Bases de datos/output_pacto_1v_2026'; B='Bases de datos'
M26=json.load(open(f'{OUT}/master_2026_puesto.json')); M22=json.load(open(f'{OUT}/master_2022_puesto.json'))
def c9(p): return f"{int(p['dep']):02d}{int(p['mun']):03d}{int(p['zona']):02d}{int(p['puesto']):02d}"
CAN=['cepeda','abelardo','paloma','fajardo','botero','lizcano','miguel_uribe','macollins','roy','murillo','caicedo','matamoros']
i22={c9(p):p for p in M22}
def norm(s): return unicodedata.normalize('NFD',s or '').encode('ascii','ignore').decode().upper().strip()
def cln(s): s=re.sub(r'^\d+','',(s or '')).strip(); return re.sub(r'(?i)\b(comuna|localidad)\b','',s).strip().title() or 'Sin dato'
DEP={'16':'Bogotá','01':'Antioquia','03':'Atlántico','05':'Bolívar','07':'Boyacá','09':'Caldas','11':'Cauca','12':'Cesar','13':'Córdoba','15':'Cundinamarca','17':'Chocó','19':'Huila','21':'Magdalena','23':'Nariño','24':'Risaralda','25':'Norte de Santander','26':'Quindío','27':'Santander','28':'Sucre','29':'Tolima','31':'Valle del Cauca','40':'Arauca','44':'Caquetá','46':'Casanare','48':'La Guajira','50':'Guainía','52':'Meta','54':'Guaviare','56':'San Andrés','60':'Amazonas','64':'Putumayo','68':'Vaupés','72':'Vichada','88':'Exterior'}
# nombre de municipio (electoral) desde georef
MUNI={}
with open(f'{B}/PUESTOS_GEOREF.csv',newline='',encoding='utf-8',errors='ignore') as f:
    for row in csv.DictReader(f,delimiter=';'):
        cc=(row.get('CÓDIGO COMPLETO') or '').strip()
        if len(cc)>=5: MUNI[cc[:5]]=(row.get('MUNICIPIO') or '').strip().title()
# join por puesto
J=[]
for p in M26:
    q=i22.get(c9(p))
    J.append({'dep':p['dep'].zfill(2),'mun':p['mun'].zfill(3),'zona':p['zona'].zfill(2),'comuna':p.get('comuna',''),'barrio':(p.get('barrio') or '').strip(),
        'cep':p['cepeda'],'abe':p['abelardo'],'pal':p['paloma'],'faj':p['fajardo'],'base':sum(p[c] for c in CAN)+p['votos_blanco'],'pot':p.get('pot',0),'urna':p['total_votos_urna'],
        'p1':q['petro1v'] if q else 0,'fic':q['fico1v'] if q else 0,'rod':q['rodolfo1v'] if q else 0,'b1':q['base1v'] if q else 0,'p2':q['petro2v'] if q else 0,'b2':q['base2v'] if q else 0})
def met(x):
    pc=lambda a,b: round(x[a]/x[b]*100,1) if x[b] else None
    der26=x['abe']+x['pal']; der22=x['fic']+x['rod']
    return {'cep26':pc('cep','base'),'petro1v':pc('p1','b1'),'dif_cep':round((x['cep']/x['base']-x['p1']/x['b1'])*100,1) if x['base'] and x['b1'] else None,
      'petro2v':pc('p2','b2'),'dif_petro2v1v':round((x['p2']/x['b2']-x['p1']/x['b1'])*100,1) if x['b2'] and x['b1'] else None,
      'centro26':pc('faj','base'),'der26':round(der26/x['base']*100,1) if x['base'] else None,'der22':round(der22/x['b1']*100,1) if x['b1'] else None,
      'dif_der':round((der26/x['base']-der22/x['b1'])*100,1) if x['base'] and x['b1'] else None,
      'part26':round(x['urna']/x['pot']*100,1) if x['pot'] else None,'base':x['base']}
def agg(keyfn,minbase,filt=None):
    g={}
    for r in J:
        if filt and not filt(r): continue
        k=keyfn(r)
        if not k: continue
        d=g.setdefault(k,{f:0 for f in ['cep','abe','pal','faj','base','p1','fic','rod','b1','p2','b2','pot','urna']})
        for f in d: d[f]+=r[f]
    return {k:met(v) for k,v in g.items() if v['base']>=minbase}

# municipio (todos los bloques)
muni=agg(lambda r:(None if r['dep']=='88' else r['dep']+r['mun']),300)
CITYNM={'16001':'Bogotá D.C.','01001':'Medellín','31001':'Cali','03001':'Barranquilla'}
for code,v in muni.items(): v['muni']=CITYNM.get(code,MUNI.get(code,code)); v['dep']=DEP.get(code[:2],code[:2])
# ciudades comuna + barrio (todos los bloques)
CITY={'Bogotá':('16','001'),'Medellín':('01','001'),'Cali':('31','001'),'Barranquilla':('03','001')}
city_barrio={}
for nm,(dp,mn) in CITY.items():
    bar=agg(lambda r:r['barrio'] or None,150,filt=(lambda r,dp=dp,mn=mn: r['dep']==dp and r['mun']==mn and r['zona'] not in ('90','98') and r['barrio']))
    # comuna por barrio
    bc={}
    for r in J:
        if r['dep']==dp and r['mun']==mn and r['barrio']: bc[r['barrio']]=cln(r['comuna'])
    city_barrio[nm]=[{'barrio':b,'comuna':bc.get(b,''), **v} for b,v in bar.items()]

# ---- abstención: participación 2022 vs 2026 por depto y municipio ----
h22=json.load(open(f'{OUT}/_h22_pormun.json'))
cen22=json.load(open(f'{B}/puestos-censos-agg-2022.json'))['porMun']  # key '01-001'
def keyhy(code): return code[:2]+'-'+code[2:5]
muni_abst=[]
for code,v in muni.items():
    if v['dif_cep'] is None or v['part26'] is None: continue
    k=keyhy(code); blk=h22.get(k); cz=cen22.get(k)
    if not blk or not cz: continue
    part22=blk.get('votos_totales',0)/cz*100 if cz else None
    if part22 is None: continue
    if v['dif_cep']>0 and v['part26']<part22:  # crece izquierda Y sube abstención
        muni_abst.append({'muni':v['muni'],'dep':v['dep'],'dif_cep':v['dif_cep'],'part22':round(part22,1),'part26':v['part26'],'caida_part':round(v['part26']-part22,1),'base':v['base']})
muni_abst.sort(key=lambda r:r['caida_part'])

# depto abstención (agrega)
dep=agg(lambda r:r['dep'],5000)
dep_abst=[]
depcen={}; deptot={}
for code,blk in h22.items():
    d=code.split('-')[0]; deptot[d]=deptot.get(d,0)+blk.get('votos_totales',0)
for k,c in cen22.items():
    d=k.split('-')[0]; depcen[d]=depcen.get(d,0)+c
for dc,v in dep.items():
    if v['dif_cep'] is None or v['part26'] is None: continue
    if dc in deptot and depcen.get(dc):
        p22=deptot[dc]/depcen[dc]*100
        dep_abst.append({'dep':DEP.get(dc,dc),'dif_cep':v['dif_cep'],'part22':round(p22,1),'part26':v['part26'],'caida':round(v['part26']-p22,1),'cae':v['part26']<p22 and v['dif_cep']>0})

out={'muni':{c:v for c,v in muni.items()},'city_barrio':city_barrio,'muni_abst':muni_abst,'dep_abst':dep_abst}
json.dump(out,open(f'{OUT}/blocks_full.json','w'),ensure_ascii=False)
print(f"municipios: {len(muni)} · barrios ciudades: {sum(len(v) for v in city_barrio.values())}")
print(f"\n### Cepeda CRECE y abstención SUBE — deptos:")
for r in sorted([d for d in dep_abst if d['cae']],key=lambda x:x['caida'])[:8]:
    print(f"  {r['dep']:<16} Cepeda {r['dif_cep']:+.1f}  · participación {r['part22']:.0f}%→{r['part26']:.0f}% ({r['caida']:+.1f})")
print(f"  (municipios que cumplen ambas: {len(muni_abst)})")
print("\n✓ blocks_full.json")
