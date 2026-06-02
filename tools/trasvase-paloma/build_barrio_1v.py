import csv, json
p2b=json.load(open('Bases de datos/output_ciudades/bogota/bog-puesto-to-barrio.json'))
geo=json.load(open('/tmp/bogbar.json'))
bmeta={f['properties']['codigo']:(f['properties']['nombre'],f['properties'].get('loc_nombre','')) for f in geo['features']}
CMAP=[('Abelardo De La Espriella','ab'),('Iván Cepeda','ce'),('Paloma Valencia','pa'),('Sergio Fajardo','sf'),
('Santiago Botero','bo'),('Mauricio Lizcano','li'),('Miguel Uribe','mu'),('Sondra Macollins','ma'),
('Roy Barreras','ro'),('Gilberto Murillo','gm'),('Carlos Caicedo','ca'),('Gustavo Matamoros','mt')]
agg={}; mapped=0; unmapped=0; mv=0; uv=0
with open('Bases de datos/nuevos archivos 1v 2026/PRECONTEO_1V_2026_MESA_nombres_corregidos.csv',encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if r['cod_departamento']!='16': continue
        try: key=f"{int(r['zona']):02d}-{int(r['puesto']):02d}"
        except: key=None
        urna=int(r['total_votos_urna']or 0)
        bc=p2b.get(key)
        if not bc:
            unmapped+=1; uv+=urna; continue
        mapped+=1; mv+=urna
        a=agg.setdefault(bc,{k:0 for _,k in CMAP}|{'bl':0,'nu':0,'nm':0,'urna':0})
        for col,k in CMAP: a[k]+=int(r[col]or 0)
        a['bl']+=int(r['votos_blanco']or 0); a['nu']+=int(r['votos_nulos']or 0); a['nm']+=int(r['votos_no_marcados']or 0); a['urna']+=urna
for bc,a in agg.items(): a['cl']=a['urna']-(sum(a[k] for _,k in CMAP)+a['bl']+a['nu']+a['nm'])
print(f"Mesas mapeadas a barrio: {mapped:,} ({mv:,} votos) | sin mapear: {unmapped:,} ({uv:,} votos)")
print(f"Cobertura de votos: {100*mv/(mv+uv):.1f}%  | barrios con datos: {len(agg)} de {len(bmeta)}")
# ganador por barrio
CAND={'ab':'Abelardo','ce':'Cepeda','pa':'Paloma','sf':'Fajardo','cl':'Claudia','bo':'Botero'}
import collections
wins=collections.Counter(); out={}
for bc,a in agg.items():
    if a['urna']<1: continue
    cand_votes={k:a[k] for k in CAND}
    win=max(cand_votes,key=cand_votes.get); wins[CAND[win]]+=1
    out[bc]={'n':bmeta.get(bc,('?',''))[0],'loc':bmeta.get(bc,('','?'))[1],
             'ab':a['ab'],'ce':a['ce'],'pa':a['pa'],'sf':a['sf'],'cl':a['cl'],'urna':a['urna'],
             'win':CAND[win],'winpct':round(100*cand_votes[win]/a['urna'],1)}
print("Barrios ganados:",dict(wins))
json.dump(out,open('Bases de datos/output_trasvase/bogota-1v-por-barrio.json','w'),ensure_ascii=False)
print("escrito bogota-1v-por-barrio.json ·",len(out),"barrios")
# extremos
top_ab=sorted([(v['ab']/v['urna'],v['n'],v['urna']) for v in out.values() if v['urna']>200],reverse=True)[:5]
top_ce=sorted([(v['ce']/v['urna'],v['n'],v['urna']) for v in out.values() if v['urna']>200],reverse=True)[:5]
print("Top Abelardo:",[(f'{100*s:.0f}%',n) for s,n,u in top_ab])
print("Top Cepeda:",[(f'{100*s:.0f}%',n) for s,n,u in top_ce])
