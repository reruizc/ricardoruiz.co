#!/usr/bin/env python3
# Motor: une 2026+2022 por puesto y produce los 4 bloques a depto + 4 ciudades (comuna) + Bogotá localidad.
import json,re,unicodedata
OUT='Bases de datos/output_pacto_1v_2026'
M26=json.load(open(f'{OUT}/master_2026_puesto.json')); M22=json.load(open(f'{OUT}/master_2022_puesto.json'))
def c9(p): return f"{int(p['dep']):02d}{int(p['mun']):03d}{int(p['zona']):02d}{int(p['puesto']):02d}"
CAN=['cepeda','abelardo','paloma','fajardo','botero','lizcano','miguel_uribe','macollins','roy','murillo','caicedo','matamoros']
i22={c9(p):p for p in M22}
DEP={'16':'Bogotá','01':'Antioquia','03':'Atlántico','05':'Bolívar','07':'Boyacá','09':'Caldas','11':'Cauca','12':'Cesar','13':'Córdoba','15':'Cundinamarca','17':'Chocó','19':'Huila','21':'Magdalena','23':'Nariño','24':'Risaralda','25':'Norte de Santander','26':'Quindío','27':'Santander','28':'Sucre','29':'Tolima','31':'Valle del Cauca','40':'Arauca','44':'Caquetá','46':'Casanare','48':'La Guajira','50':'Guainía','52':'Meta','54':'Guaviare','56':'San Andrés','60':'Amazonas','64':'Putumayo','68':'Vaupés','72':'Vichada','88':'Exterior'}
def norm(s): return unicodedata.normalize('NFD',s or '').encode('ascii','ignore').decode().upper().strip()
def cn(raw):
    s=re.sub(r'^\d+','',(raw or '')).strip(); s=re.sub(r'(?i)\b(comuna|localidad)\b','',s).strip()
    return s.title() or 'Sin dato'
J=[]
for p in M26:
    q=i22.get(c9(p))
    J.append({'dep':p['dep'].zfill(2),'mun':p['mun'].zfill(3),'zona':p['zona'].zfill(2),'comuna':p.get('comuna',''),'barrio':p.get('barrio',''),
        'cep':p['cepeda'],'abe':p['abelardo'],'pal':p['paloma'],'faj':p['fajardo'],'base':sum(p[c] for c in CAN)+p['votos_blanco'],'pot':p.get('pot',0),'urna':p['total_votos_urna'],
        'p1':q['petro1v'] if q else 0,'fic':q['fico1v'] if q else 0,'rod':q['rodolfo1v'] if q else 0,'fj22':q['fajardo1v'] if q else 0,'b1':q['base1v'] if q else 0,'p2':q['petro2v'] if q else 0,'b2':q['base2v'] if q else 0})

FIELDS=['cep','abe','pal','faj','base','p1','fic','rod','fj22','b1','p2','b2','pot','urna']
def metrics(x):
    pc=lambda a,b: round(x[a]/x[b]*100,1) if x[b] else None
    der26=x['abe']+x['pal']; der22=x['fic']+x['rod']
    return {
      'cep26':pc('cep','base'),'petro1v':pc('p1','b1'),'dif_cep':round((x['cep']/x['base']-x['p1']/x['b1'])*100,1) if x['base'] and x['b1'] else None,
      'petro2v':pc('p2','b2'),'dif_petro2v1v':round((x['p2']/x['b2']-x['p1']/x['b1'])*100,1) if x['b2'] and x['b1'] else None,
      'centro26':pc('faj','base'),
      'der26':round(der26/x['base']*100,1) if x['base'] else None,'der22':round(der22/x['b1']*100,1) if x['b1'] else None,
      'dif_der':round((der26/x['base']-der22/x['b1'])*100,1) if x['base'] and x['b1'] else None,
      'abst26':round((1-x['urna']/x['pot'])*100,1) if x['pot'] else None,
      'cep_votos':x['cep'],'base_votos':x['base']}
def aggregate(keyfn,minbase=2000,filt=None):
    g={}
    for r in J:
        if filt and not filt(r): continue
        k=keyfn(r)
        if k is None: continue
        d=g.setdefault(k,{f:0 for f in FIELDS})
        for f in FIELDS: d[f]+=r[f]
    return {k:dict(metrics(v),**{'_v':v}) for k,v in g.items() if v['base']>=minbase}

# por depto
dep=aggregate(lambda r:r['dep'],5000)
# ciudades por comuna
CITY={'Medellín':('01','001'),'Cali':('31','001'),'Barranquilla':('03','001'),'Bogotá':('16','001')}
city_comuna={nm:aggregate(lambda r:cn(r['comuna']),800,filt=(lambda dp,mn: (lambda r: r['dep']==dp and r['mun']==mn))(dp,mn)) for nm,(dp,mn) in CITY.items()}

out={'depto':{DEP.get(k,k):v|{'cod':k} for k,v in dep.items()},'city_comuna':{c:{kk:vv for kk,vv in d.items()} for c,d in city_comuna.items()}}
# limpiar _v (no serializar dict interno pesado) -> dejar solo votos clave
for sec in (out['depto'],):
    for k,v in sec.items(): v.pop('_v',None)
for c,d in out['city_comuna'].items():
    for k,v in d.items(): v.pop('_v',None)
json.dump(out,open(f'{OUT}/blocks_all.json','w'),ensure_ascii=False)

# ---- imprimir hallazgos bloques 3 y 4 (los que faltan por ver) ----
print("### BLOQUE 4 — DERECHA (Abelardo+Paloma 26) vs (Fico+Rodolfo 22 1V) — dónde AVANZÓ por depto")
rows=[(DEP.get(k,k),v['der26'],v['der22'],v['dif_der']) for k,v in dep.items() if v['dif_der'] is not None]
for nm,d26,d22,dif in sorted(rows,key=lambda r:-r[3])[:8]:
    print(f"  {nm:<16} Der26 {d26:5.1f}  (Fico+Rodolfo22 {d22:5.1f})  ({dif:+.1f})")
print("  ...donde retrocedió:")
for nm,d26,d22,dif in sorted(rows,key=lambda r:r[3])[:4]:
    print(f"  {nm:<16} Der26 {d26:5.1f}  ({d22:5.1f})  ({dif:+.1f})")
nat_der26=sum(J[i]['abe']+J[i]['pal'] for i in range(len(J)))/sum(r['base'] for r in J)*100
nat_der22=sum(r['fic']+r['rod'] for r in J)/sum(r['b1'] for r in J)*100
print(f"  NACIONAL: derecha 2026 {nat_der26:.1f}% vs Fico+Rodolfo 1V-22 {nat_der22:.1f}%")

print("\n### BLOQUE 3 — CENTRO (Fajardo 2026, a puesto) por depto · top")
rows=[(DEP.get(k,k),v['centro26'],v['_v']['faj'] if '_v' in v else None) for k,v in dep.items()]
# faj votos
fajv={}; 
for r in J: fajv[r['dep']]=fajv.get(r['dep'],0)+r['faj']
for k,v in sorted(dep.items(),key=lambda x:-(x[1]['centro26'] or 0))[:8]:
    print(f"  {DEP.get(k,k):<16} Fajardo {v['centro26']:.1f}%   ({fajv.get(k,0):,} votos)")
print(f"  (Claudia ~225k, solo a municipio; se suma aparte. Centro total nacional ≈ Fajardo 4,3% + Claudia 0,95%)")

print("\n### CIUDADES — Cepeda26 vs Petro22 + techo 2V (resumen)")
for c,(dp,mn) in CITY.items():
    agg=aggregate(lambda r:'X',1, filt=(lambda r,dp=dp,mn=mn: r['dep']==dp and r['mun']==mn)).get('X')
    if agg: print(f"  {c:<13} Cep26 {agg['cep26']}  Petro1V22 {agg['petro1v']}  dif {agg['dif_cep']:+}  · techo(Petro2V) {agg['petro2v']}  · espacio +{round((agg['petro2v'] or 0)-(agg['cep26'] or 0),1)}")
print("\n✓ blocks_all.json")
