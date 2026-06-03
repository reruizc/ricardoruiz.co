import json, re, math
geo=json.load(open('/tmp/bogbar.json'))
res=json.load(open('Bases de datos/output_trasvase/bogota-1v-por-barrio.json'))
AB,CE,GRAY='#1d1d6e','#c0392b','#d6d0c0'
AIRPORT='005624'  # Aeropuerto El Dorado → gris
cx,cy=-74.08,4.65
def rot(lo,la): return (cx-(la-cy), cy+(lo-cx))
feats=[]
for f in geo['features']:
    p=f['properties']; g=f['geometry']
    if g['type']=='Polygon': rings=g['coordinates']
    elif g['type']=='MultiPolygon': rings=[r for poly in g['coordinates'] for r in poly]
    else: continue
    # centroide (anillo exterior del primer polígono, en lon/lat)
    ext=g['coordinates'][0] if g['type']=='Polygon' else g['coordinates'][0][0]
    cxx=sum(c[0] for c in ext)/len(ext); cyy=sum(c[1] for c in ext)/len(ext)
    v=res.get(p['codigo'])
    win = v['win'] if v else None
    feats.append({'cod':p['codigo'],'rings':rings,'cx':cxx,'cy':cyy,'win':win})
data=[f for f in feats if f['win'] in ('Abelardo','Cepeda')]
# relleno por vecino más cercano para los sin dato (excepto aeropuerto)
for f in feats:
    if f['cod']==AIRPORT: f['col']=GRAY; continue
    if f['win'] in ('Abelardo','Cepeda'): f['col']=AB if f['win']=='Abelardo' else CE; continue
    # nearest data barrio
    best=None;bd=1e9
    for d in data:
        dd=(f['cx']-d['cx'])**2+(f['cy']-d['cy'])**2
        if dd<bd: bd=dd; best=d
    f['col']=AB if best['win']=='Abelardo' else CE
# bbox sobre coords rotadas
xs=[];ys=[]
for f in feats:
    for ring in f['rings']:
        for c in ring:
            x,y=rot(c[0],c[1]); xs.append(x);ys.append(y)
minx,maxx=min(xs),max(xs);miny,maxy=min(ys),max(ys)
W,H=920,640
s=min(W/(maxx-minx),H/(maxy-miny))
offx=(W-(maxx-minx)*s)/2; offy=(H-(maxy-miny)*s)/2
def proj(lo,la):
    x,y=rot(lo,la); return (offx+(x-minx)*s, offy+(maxy-y)*s)
paths=[]
for f in feats:
    d=''
    for ring in f['rings']:
        pts=[proj(c[0],c[1]) for c in ring]
        d+='M'+' '.join(f'{px:.1f},{py:.1f}' for px,py in pts)+'Z'
    paths.append(f'<path d="{d}" fill="{f["col"]}" stroke="#f1eee4" stroke-width="0.4"/>')
svg=f'<svg viewBox="0 0 {W} {H}" width="100%" style="display:block">{"".join(paths)}</svg>'
nfill=sum(1 for f in feats if f['win'] not in ('Abelardo','Cepeda') and f['cod']!=AIRPORT)
section=f'''<!-- 2 · MAPA -->
<section class="slide">
  <div class="eyebrow">El mapa · Bogotá completa</div><div class="rule"></div>
  <h1 class="headline" style="font-size:58px;margin-bottom:8px">Dos Bogotás en un mapa.</h1>
  <div style="flex:1;display:flex;align-items:center;justify-content:center;margin:6px 0">{svg}</div>
  <div style="font-family:var(--hel);font-weight:700;font-size:26px;color:var(--ink);display:flex;gap:34px;justify-content:center;margin-bottom:6px">
    <span><span style="display:inline-block;width:20px;height:20px;background:{AB};vertical-align:-3px;border-radius:3px"></span> Abelardo</span>
    <span><span style="display:inline-block;width:20px;height:20px;background:{CE};vertical-align:-3px;border-radius:3px"></span> Cepeda</span>
    <span style="color:var(--ink3)"><span style="display:inline-block;width:20px;height:20px;background:{GRAY};vertical-align:-3px;border-radius:3px"></span> aeropuerto</span>
  </div>
  <div class="foot"><span><b>@ricardoeruiz_</b></span><span>Ganador por barrio · sin puesto = color del vecino · mapa interactivo en ricardoruiz.co</span></div>
</section>'''
html=open('rrss/instagram/carousel-bogota-barrios.html',encoding='utf-8').read()
if '<!-- 2 · MAPA -->' in html:
    html=re.sub(r'<!-- 2 · MAPA -->.*?</section>', section.replace('\\','\\\\'), html, count=1, flags=re.S)
else:
    i=html.find('</section>')+len('</section>'); html=html[:i]+'\n\n'+section+html[i:]
open('rrss/instagram/carousel-bogota-barrios.html','w',encoding='utf-8').write(html)
print(f'mapa actualizado · barrios {len(feats)} · con dato {len(data)} · rellenados {nfill} · aeropuerto gris')
