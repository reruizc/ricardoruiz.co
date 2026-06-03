import json, re
geo=json.load(open('/tmp/bogbar.json'))
res=json.load(open('Bases de datos/output_trasvase/bogota-1v-por-barrio.json'))
cx,cy=-74.08,4.65
def rc(lo,la): return (cx-(la-cy), cy+(lo-cx))
# recolectar polígonos (excluir Sumapaz) + bbox
polys=[]; xs=[]; ys=[]
for f in geo['features']:
    p=f['properties']
    loc=(p.get('loc_nombre') or '')+ (p.get('loc_codigo') or '')
    if 'SUMAPAZ' in loc.upper() or p.get('loc_codigo')=='20': continue
    g=f['geometry']; rings=[]
    geoms = g['coordinates'] if g['type']=='Polygon' else [r for poly in g['coordinates'] for r in poly] if g['type']=='MultiPolygon' else []
    if g['type']=='Polygon': geoms=g['coordinates']
    elif g['type']=='MultiPolygon': geoms=[r for poly in g['coordinates'] for r in poly]
    else: continue
    rr=[]
    for ring in geoms:
        pts=[rc(c[0],c[1]) for c in ring]
        rr.append(pts)
        for x,y in pts: xs.append(x); ys.append(y)
    v=res.get(p['codigo'])
    col = '#1d1d6e' if (v and v['win']=='Abelardo') else ('#534a8f' if (v and v['win']=='Cepeda') else '#d6d0c0')
    polys.append((rr,col))
minx,maxx=min(xs),max(xs); miny,maxy=min(ys),max(ys)
W,H=920,640
sx=W/(maxx-minx); sy=H/(maxy-miny); s=min(sx,sy)
offx=(W-(maxx-minx)*s)/2; offy=(H-(maxy-miny)*s)/2
def proj(x,y): return ( offx+(x-minx)*s, offy+(maxy-y)*s )  # flip Y
paths=[]
for rr,col in polys:
    d=''
    for ring in rr:
        pts=[proj(x,y) for x,y in ring]
        d+='M'+' '.join(f'{px:.1f},{py:.1f}' for px,py in pts)+'Z'
    paths.append(f'<path d="{d}" fill="{col}" stroke="#f1eee4" stroke-width="0.4"/>')
svg=f'<svg viewBox="0 0 {W} {H}" width="100%" style="display:block">{"".join(paths)}</svg>'
section=f'''<!-- 2 · MAPA -->
<section class="slide">
  <div class="eyebrow">El mapa · 557 barrios</div><div class="rule"></div>
  <h1 class="headline" style="font-size:58px;margin-bottom:8px">Dos Bogotás en un mapa.</h1>
  <div style="flex:1;display:flex;align-items:center;justify-content:center;margin:6px 0">{svg}</div>
  <div style="font-family:var(--hel);font-weight:700;font-size:26px;color:var(--ink);display:flex;gap:30px;justify-content:center;margin-bottom:6px">
    <span><span style="display:inline-block;width:20px;height:20px;background:#1d1d6e;vertical-align:-3px;border-radius:3px"></span> Abelardo</span>
    <span><span style="display:inline-block;width:20px;height:20px;background:#534a8f;vertical-align:-3px;border-radius:3px"></span> Cepeda</span>
    <span style="color:var(--ink3)"><span style="display:inline-block;width:20px;height:20px;background:#d6d0c0;vertical-align:-3px;border-radius:3px"></span> sin puesto</span>
  </div>
  <div class="foot"><span><b>@ricardoeruiz_</b></span><span>557 barrios · sin Sumapaz · mapa interactivo en ricardoruiz.co</span></div>
</section>'''
# insertar tras la portada (primera </section>)
html=open('rrss/instagram/carousel-bogota-barrios.html',encoding='utf-8').read()
idx=html.find('</section>')+len('</section>')
html=html[:idx]+'\n\n'+section+html[idx:]
open('rrss/instagram/carousel-bogota-barrios.html','w',encoding='utf-8').write(html)
print('insertada slide de mapa · paths:',len(paths),'· con dato:',sum(1 for _,c in polys if c!='#d6d0c0'))
