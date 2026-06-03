import csv, json, sys
geo=json.load(open('/tmp/bogbar.json'))
# bbox + rings por barrio para PIP rápido
B=[]
for f in geo['features']:
    p=f['properties']; g=f['geometry']
    polys = [g['coordinates']] if g['type']=='Polygon' else (g['coordinates'] if g['type']=='MultiPolygon' else [])
    ext=[poly[0] for poly in polys]  # anillos exteriores
    xs=[c[0] for ring in ext for c in ring]; ys=[c[1] for ring in ext for c in ring]
    if not xs: continue
    cx=sum(xs)/len(xs); cy=sum(ys)/len(ys)
    B.append({'cod':p['codigo'],'nom':p.get('nombre'),'loc':p.get('loc_nombre'),
              'ext':ext,'bb':(min(xs),min(ys),max(xs),max(ys)),'cx':cx,'cy':cy})
def pip(lon,lat,ring):
    inside=False; n=len(ring); j=n-1
    for i in range(n):
        xi,yi=ring[i][0],ring[i][1]; xj,yj=ring[j][0],ring[j][1]
        if ((yi>lat)!=(yj>lat)) and (lon<(xj-xi)*(lat-yi)/(yj-yi)+xi): inside=not inside
        j=i
    return inside
def barrio_pip(lon,lat):
    for b in B:
        x0,y0,x1,y1=b['bb']
        if lon<x0 or lon>x1 or lat<y0 or lat>y1: continue
        for ring in b['ext']:
            if pip(lon,lat,ring): return b['cod']
    # fuera de todo polígono → barrio más cercano por centroide
    best=None;bd=1e18
    for b in B:
        d=(lon-b['cx'])**2+(lat-b['cy'])**2
        if d<bd: bd=d; best=b['cod']
    return best
# georef Bogotá → key zona-puesto → barrio PIP
newmap={}; ncoord=0; noutside=0
with open('Bases de datos/PUESTOS_GEOREF.csv',encoding='utf-8-sig',errors='replace') as f:
    rd=csv.reader(f,delimiter=';'); h=[c.strip() for c in next(rd)]; ix={c:i for i,c in enumerate(h)}
    for r in rd:
        if len(r)<=ix['LONGITUD'] or not (r[ix['DEPARTAMENTO']] or '').upper().startswith('BOGOT'): continue
        z,p=r[ix['ZONA']],r[ix['PUESTO']]
        try: lon=float(r[ix['LONGITUD']]); lat=float(r[ix['LATITUD']])
        except: continue
        if not lon or not lat: continue
        try: key=f"{int(z):02d}-{int(p):02d}"
        except: continue
        cod=barrio_pip(lon,lat); newmap[key]=cod; ncoord+=1
json.dump(newmap,open('Bases de datos/output_trasvase/bog-puesto-to-barrio-pip.json','w'))
old=json.load(open('Bases de datos/output_ciudades/bogota/bog-puesto-to-barrio.json'))
changed=sum(1 for k in newmap if old.get(k)!=newmap[k])
print(f"Puestos georef mapeados (PIP): {ncoord} | cambian vs name-match: {changed}",file=sys.stderr)
# re-agregar presidencial por el nuevo mapa
CMAP=[('Abelardo De La Espriella','ab'),('Iván Cepeda','ce'),('Paloma Valencia','pa'),('Sergio Fajardo','sf'),
('Santiago Botero','bo'),('Mauricio Lizcano','li'),('Miguel Uribe','mu'),('Sondra Macollins','ma'),
('Roy Barreras','ro'),('Gilberto Murillo','gm'),('Carlos Caicedo','ca'),('Gustavo Matamoros','mt')]
bmeta={b['cod']:(b['nom'],b['loc']) for b in B}
agg={}
with open('Bases de datos/nuevos archivos 1v 2026/PRECONTEO_1V_2026_MESA_nombres_corregidos.csv',encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        if r['cod_departamento']!='16': continue
        try: key=f"{int(r['zona']):02d}-{int(r['puesto']):02d}"
        except: continue
        bc=newmap.get(key)
        if not bc: continue
        a=agg.setdefault(bc,{k:0 for _,k in CMAP}|{'bl':0,'nu':0,'nm':0,'urna':0})
        for col,k in CMAP: a[k]+=int(r[col]or 0)
        a['bl']+=int(r['votos_blanco']or 0);a['nu']+=int(r['votos_nulos']or 0);a['nm']+=int(r['votos_no_marcados']or 0);a['urna']+=int(r['total_votos_urna']or 0)
for bc,a in agg.items(): a['cl']=a['urna']-(sum(a[k] for _,k in CMAP)+a['bl']+a['nu']+a['nm'])
CAND={'ab':'Abelardo','ce':'Cepeda','pa':'Paloma','sf':'Fajardo','cl':'Claudia','bo':'Botero'}
import collections; wins=collections.Counter(); out={}
for bc,a in agg.items():
    if a['urna']<1: continue
    cv={k:a[k] for k in CAND}; win=max(cv,key=cv.get); wins[CAND[win]]+=1
    out[bc]={'n':bmeta.get(bc,('?',''))[0],'loc':bmeta.get(bc,('','?'))[1],'ab':a['ab'],'ce':a['ce'],'pa':a['pa'],'sf':a['sf'],'cl':a['cl'],'urna':a['urna'],'win':CAND[win],'winpct':round(100*cv[win]/a['urna'],1)}
json.dump(out,open('Bases de datos/output_trasvase/bogota-1v-por-barrio.json','w'),ensure_ascii=False)
print(f"Barrios con dato REAL: {len(out)} (antes 558) | ganados: {dict(wins)}",file=sys.stderr)
