#!/usr/bin/env python3
"""
build-mde-barrios-prec/build.py

Espejo de Bogotá (bogota-1v-barrios.html) para Medellín: cruza el preconteo
1ª vuelta 2026 por mesa con los 332 barrios oficiales de Medellín
(MEDELLIN_BARRIOS_OFICIAL.json, DAP) vía PIP del puesto de votación.

Pipeline:
  1. PIP de cada puesto de Medellín (PUESTOS_GEOREF.csv, lat/lon) → barrio CODIGO.
  2. Agrega votos del preconteo (dep 01, mun 001; excluye zona 90/98) por barrio.
  3. BARRIOS = barrios con dato directo. FILL = vecino por centroide más cercano.
  4. Emite medellin-1v-barrios.html en la raíz del repo.

Sin dependencias externas — stdlib pura. NO rota la geometría (solo Bogotá rota).
"""
import csv, json, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEO   = ROOT / "Bases de datos" / "MEDELLIN_BARRIOS_OFICIAL.json"
GEOREF= ROOT / "Bases de datos" / "PUESTOS_GEOREF.csv"
PREC  = ROOT / "Bases de datos" / "nuevos archivos 1v 2026" / "PRECONTEO_1V_2026_MESA_con_Claudia.csv"
OUT   = ROOT / "medellin-1v-barrios.html"
GEO_URL = "https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/bases+de+datos/MEDELLIN_BARRIOS_OFICIAL.json"

CMAP = [('Abelardo De La Espriella','ab'), ('Iván Cepeda','ce'), ('Paloma Valencia','pa'),
        ('Sergio Fajardo','sf'), ('Claudia López','cl'), ('Santiago Botero','bo'),
        ('Mauricio Lizcano','li'), ('Miguel Uribe','mu'), ('Sondra Macollins','ma'),
        ('Roy Barreras','ro'), ('Gilberto Murillo','gm'), ('Carlos Caicedo','ca'),
        ('Gustavo Matamoros','mt')]
CAND = {'ab':'Abelardo','ce':'Cepeda','pa':'Paloma','sf':'Fajardo','cl':'Claudia','bo':'Botero'}

def rings_of(g):
    polys = [g['coordinates']] if g['type'] == 'Polygon' else (g['coordinates'] if g['type'] == 'MultiPolygon' else [])
    return [poly[0] for poly in polys]

def pip(lon, lat, ring):
    inside = False; n = len(ring); j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]; xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def main():
    geo = json.loads(GEO.read_text(encoding='utf-8'))
    B = []
    for f in geo['features']:
        p = f['properties']; ext = rings_of(f['geometry'])
        xs = [c[0] for r in ext for c in r]; ys = [c[1] for r in ext for c in r]
        if not xs: continue
        B.append({'cod': p['CODIGO'], 'nom': p['NOMBRE'], 'com': p.get('COMUNA'), 'ext': ext,
                  'bb': (min(xs), min(ys), max(xs), max(ys)),
                  'cx': sum(xs) / len(xs), 'cy': sum(ys) / len(ys)})
    bmeta = {b['cod']: (b['nom'], b['com']) for b in B}

    def barrio_pip(lon, lat):
        for b in B:
            x0, y0, x1, y1 = b['bb']
            if lon < x0 or lon > x1 or lat < y0 or lat > y1: continue
            for ring in b['ext']:
                if pip(lon, lat, ring): return b['cod']
        best = None; bd = 1e18
        for b in B:
            d = (lon - b['cx'])**2 + (lat - b['cy'])**2
            if d < bd: bd = d; best = b['cod']
        return best

    # ── georef Medellín → key zona-puesto → barrio PIP ──
    gmap = {}
    with open(GEOREF, encoding='utf-8-sig', errors='replace') as f:
        rd = csv.reader(f, delimiter=';'); h = [c.strip() for c in next(rd)]; ix = {c: i for i, c in enumerate(h)}
        for r in rd:
            if len(r) <= ix['LONGITUD']: continue
            if (r[ix['MUNICIPIO']] or '').upper().strip() != 'MEDELLIN': continue
            if not (r[ix['DEPARTAMENTO']] or '').upper().startswith('ANTIO'): continue
            try:
                key = f"{int(r[ix['ZONA']]):02d}-{int(r[ix['PUESTO']]):02d}"
                lon = float(r[ix['LONGITUD']]); lat = float(r[ix['LATITUD']])
            except: continue
            if not lon or not lat: continue
            gmap[key] = barrio_pip(lon, lat)

    # ── agrega preconteo (dep 01, mun 001; excluye zona 90/98) ──
    agg = collections.defaultdict(lambda: {k: 0 for _, k in CMAP} | {'urna': 0})
    city = {k: 0 for _, k in CMAP}; city['urna'] = 0
    with open(PREC, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if r['cod_departamento'] != '01' or r['cod_municipio'] != '001': continue
            try: zi = int(r['zona'])
            except: zi = -1
            if zi in (90, 98): continue
            try: key = f"{int(r['zona']):02d}-{int(r['puesto']):02d}"
            except: continue
            bc = gmap.get(key)
            urna = int(r['total_votos_urna'] or 0)
            city['urna'] += urna
            for col, k in CMAP:
                v = int(r[col] or 0); city[k] += v
                if bc: agg[bc][k] += v
            if bc: agg[bc]['urna'] += urna

    # ── BARRIOS con dato directo ──
    BARRIOS = {}; wins = collections.Counter()
    for bc, a in agg.items():
        if a['urna'] < 1: continue
        cv = {k: a[k] for k in CAND}; win = max(cv, key=cv.get)
        BARRIOS[bc] = {'n': bmeta.get(bc, ('?', ''))[0], 'loc': bmeta.get(bc, ('', '?'))[1],
                       'ab': a['ab'], 'ce': a['ce'], 'pa': a['pa'], 'sf': a['sf'], 'cl': a['cl'],
                       'urna': a['urna'], 'win': CAND[win], 'winpct': round(100 * cv[win] / a['urna'], 1)}
        wins[CAND[win]] += 1

    # ── FILL: barrios sin dato → vecino directo más cercano por centroide ──
    direct = [b for b in B if b['cod'] in BARRIOS]
    FILL = {}
    for b in B:
        if b['cod'] in BARRIOS: continue
        best = None; bd = 1e18
        for d in direct:
            dd = (b['cx'] - d['cx'])**2 + (b['cy'] - d['cy'])**2
            if dd < bd: bd = dd; best = d
        if best:
            v = BARRIOS[best['cod']]
            FILL[b['cod']] = {'w': v['win'], 'p': v['winpct']}

    # ── ganadores para el titular: SOLO barrios con dato directo (como Bogotá) ──
    tot = city['urna'] or 1
    pct = lambda k: round(100 * city[k] / tot, 1)
    located = sum(v['urna'] for v in BARRIOS.values())
    cov = round(100 * located / tot, 1)

    stats = dict(
        ab=pct('ab'), ce=pct('ce'), pa=pct('pa'), sf=pct('sf'),
        votos=city['urna'], direct=len(BARRIOS), nb=len(B),
        win_ab=wins['Abelardo'], win_ce=wins['Cepeda'], cov=cov)
    print("Medellín ciudad: Abelardo %.1f%% · Cepeda %.1f%% · Fajardo %.1f%% · Paloma %.1f%%" % (
        stats['ab'], stats['ce'], stats['sf'], stats['pa']))
    print("barrios directos:", len(BARRIOS), "| fill:", len(FILL), "| total polígonos:", len(B))
    print("ganados (solo dato directo): Abelardo %d · Cepeda %d" % (stats['win_ab'], stats['win_ce']))
    print("cobertura de votos en barrio con dato directo: %.1f%%" % cov)

    html = build_html(BARRIOS, FILL, stats)
    OUT.write_text(html, encoding='utf-8')
    print("\n✓", OUT.relative_to(ROOT), f"({OUT.stat().st_size/1024:.0f} KB)")


def build_html(BARRIOS, FILL, s):
    barrios_json = json.dumps(BARRIOS, ensure_ascii=False, separators=(',', ':'))
    fill_json = json.dumps(FILL, ensure_ascii=False, separators=(',', ':'))
    nf = lambda n: f"{n:,}".replace(',', '.')
    tpl = TEMPLATE
    repl = {
        '__BARRIOS__': barrios_json, '__FILL__': fill_json, '__GEO_URL__': GEO_URL,
        '__AB__': f"{s['ab']:.1f}".replace('.', ','), '__CE__': f"{s['ce']:.1f}".replace('.', ','),
        '__SF__': f"{s['sf']:.1f}".replace('.', ','), '__PA__': f"{s['pa']:.1f}".replace('.', ','),
        '__WIN_AB__': nf(s['win_ab']), '__WIN_CE__': nf(s['win_ce']),
        '__DIRECT__': nf(s['direct']), '__NB__': nf(s['nb']),
        '__VOTOS__': nf(s['votos']), '__COV__': f"{s['cov']:.1f}".replace('.', ','),
    }
    for k, v in repl.items():
        tpl = tpl.replace(k, str(v))
    return tpl


TEMPLATE = r'''<!DOCTYPE html>
<html lang="es"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>El mapa de Medellín: barrio por barrio en la primera vuelta 2026 · ricardoruiz.co</title>
<meta name="description" content="Mapa de Medellín por barrios (1ª vuelta presidencial 2026). Abelardo ganó __WIN_AB__ barrios; Cepeda, __WIN_CE__. La ciudad de Abelardo, barrio a barrio, con datos del preconteo por mesa.">
<meta property="og:title" content="El mapa de Medellín barrio por barrio — primera vuelta 2026">
<meta property="og:description" content="Abelardo arrasó Medellín con 54,5%; Cepeda, segundo. El mapa barrio a barrio, con datos por mesa.">
<meta property="og:type" content="article">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;700;800&family=Arima:wght@400;500;700&family=DM+Mono:wght@400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#060810;--border:rgba(255,255,255,.08);--white:#f4f3ef;--blue:#0047FF;--green:#4ade80;--orange:#fb923c;--muted:rgba(255,255,255,.55);--abel:#3d7dff;--cepe:#a78bfa}
body{background:var(--bg);color:var(--white);font-family:Avenir,sans-serif;min-height:100vh;line-height:1.55}
a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}
.nav{padding:.9rem 2rem;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:rgba(4,6,16,.6)}
.e-btn-back{font-family:Avenir,sans-serif;font-weight:500;font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--green);border:1.5px solid rgba(74,222,128,.4);padding:.3rem .8rem}
.e-btn-back:hover{color:#060810;background:var(--green);text-decoration:none}
.logo-link{display:flex;align-items:center;gap:.55rem;opacity:.85}.logo-bars{display:flex;align-items:flex-end;gap:3px;height:20px}
.logo-bar{width:5px;background:var(--blue)}.logo-text{font-family:'Syne',sans-serif;font-weight:800;font-size:1.2rem;letter-spacing:-.03em;color:var(--white)}.logo-text span{color:var(--blue)}
.container{max-width:1000px;margin:0 auto;padding:2.5rem 2rem 4rem}
.kicker{font-family:'Syne',sans-serif;font-size:.78rem;letter-spacing:.18em;text-transform:uppercase;color:var(--orange);margin-bottom:.7rem;font-weight:500}
h1{font-family:'Syne',sans-serif;font-weight:800;font-size:clamp(1.8rem,4vw,2.9rem);letter-spacing:-.025em;line-height:1.05;margin-bottom:.7rem}
h1 span{color:var(--blue)}
.subhead{font-family:'Arima',sans-serif;font-size:clamp(1rem,1.6vw,1.18rem);color:var(--muted);line-height:1.5;max-width:800px;margin-bottom:1.6rem}
.byline{font-family:'DM Mono',monospace;font-size:.7rem;letter-spacing:.1em;color:rgba(255,255,255,.4);margin-bottom:2rem;padding-bottom:1.2rem;border-bottom:1px solid var(--border)}
.lead{font-size:1.05rem;line-height:1.65;margin-bottom:1.6rem;color:rgba(255,255,255,.85)}.lead b{color:var(--white)}
.legend{display:flex;gap:1.5rem;flex-wrap:wrap;font-family:Avenir,sans-serif;font-size:.85rem;color:rgba(255,255,255,.75);margin:.4rem 0 1rem}
.legend span{display:flex;align-items:center;gap:.45rem}.legend i{width:14px;height:14px;border-radius:3px;display:inline-block}
#map{width:100%;height:74vh;min-height:560px;border:1px solid var(--border);background:#0a0d18}
.mapcap{font-family:Avenir,sans-serif;font-size:.8rem;color:rgba(255,255,255,.55);margin:.7rem 0 2rem;line-height:1.5}
h2{font-family:'Syne',sans-serif;font-weight:700;font-size:1.35rem;margin:2.4rem 0 1rem}h2::before{content:'';display:inline-block;width:6px;height:1.15rem;background:var(--blue);margin-right:.6rem;vertical-align:-3px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:1.4rem}@media(max-width:640px){.cols{grid-template-columns:1fr}}
.col h3{font-family:'Syne',sans-serif;font-size:.95rem;margin-bottom:.6rem}.col.ab h3{color:var(--abel)}.col.ce h3{color:var(--cepe)}
.col ol{list-style:none;counter-reset:n}.col li{font-family:Avenir,sans-serif;font-size:.9rem;padding:.32rem 0;border-bottom:1px solid rgba(255,255,255,.05);display:flex;justify-content:space-between;gap:1rem}
.col li b{font-variant-numeric:tabular-nums}
.method{margin-top:2.5rem;padding:1.2rem;background:rgba(255,255,255,.025);border:1px solid var(--border);font-size:.88rem;color:rgba(255,255,255,.72);line-height:1.6}
.method b{color:var(--white)}.method code{font-family:'DM Mono',monospace;font-size:.82rem;background:rgba(255,255,255,.06);padding:.06rem .3rem}
.dl{margin-top:2.2rem;padding:1.3rem 1.4rem;border:1px solid var(--border);background:rgba(255,255,255,.02)}
.dl-title{font-family:'Syne',sans-serif;font-weight:700;font-size:1.05rem;margin-bottom:.5rem}
.dl-title .tag{font-family:'DM Mono',monospace;font-size:.62rem;letter-spacing:.12em;color:#f0c040;border:1px solid rgba(240,192,64,.5);padding:.1rem .4rem;border-radius:3px;vertical-align:middle;margin-left:.5rem}
.dl-body{font-size:.92rem;color:rgba(255,255,255,.8);line-height:1.65}
.dl-btn{display:inline-block;margin:.55rem .5rem 0 0;background:rgba(0,71,255,.12);color:var(--white);font-family:Avenir,sans-serif;font-weight:600;font-size:.82rem;padding:.5rem .9rem;border:1px solid rgba(0,71,255,.5)}
.dl-btn:hover{background:var(--blue);color:#fff;text-decoration:none}
.dl-lock{display:inline-block;margin-top:.6rem;background:var(--blue);color:#fff;font-family:Avenir,sans-serif;font-weight:600;font-size:.78rem;letter-spacing:.04em;text-transform:uppercase;padding:.5rem 1rem;border:1px solid var(--blue)}
.dl-lock:hover{background:transparent;color:var(--blue);text-decoration:none}
.cta{margin-top:2.4rem;padding:1.4rem;background:linear-gradient(135deg,rgba(0,71,255,.12),rgba(0,71,255,.04));border:1px solid rgba(0,71,255,.4)}
.cta-title{font-family:'Syne',sans-serif;font-weight:700;font-size:1.05rem;color:var(--blue);margin-bottom:.5rem}.cta-body{font-size:.92rem;color:rgba(255,255,255,.85);margin-bottom:.8rem}
.cta-btn{display:inline-block;background:var(--blue);color:#fff;font-family:Avenir,sans-serif;font-weight:600;font-size:.75rem;letter-spacing:.06em;text-transform:uppercase;padding:.55rem 1.1rem;border:1px solid var(--blue);margin-right:.5rem}.cta-btn.alt{background:transparent;color:var(--white);border-color:rgba(255,255,255,.2)}
.foot{margin-top:3rem;padding-top:1.5rem;border-top:1px solid var(--border);font-size:.78rem;color:rgba(255,255,255,.45);text-align:center;line-height:1.55}.foot a{color:var(--blue)}
.leaflet-tooltip{font-family:Avenir,sans-serif!important;font-size:.82rem!important;background:rgba(6,8,16,.97)!important;border:1px solid rgba(0,71,255,.4)!important;color:#f4f3ef!important;border-radius:0!important;padding:.45rem .65rem!important;width:230px!important;white-space:normal!important}
.leaflet-tooltip:before{display:none!important}.leaflet-tooltip b{color:#fff}
</style></head>
<body>
<nav class="nav">
<a href="noticias.html" class="e-btn-back">← Noticias</a>
<a href="index.html" class="logo-link"><div class="logo-bars"><div class="logo-bar" style="height:20px"></div><div class="logo-bar" style="height:15px"></div><div class="logo-bar" style="height:9px"></div><div class="logo-bar" style="height:4px"></div></div><span class="logo-text">Ricardo<span>.</span>Ruiz</span></a>
</nav>
<main class="container">
<div class="kicker">Mapa · primera vuelta 2026 · 3 de junio de 2026</div>
<h1>El mapa de Medellín, <span>barrio por barrio</span></h1>
<p class="subhead">La primera vuelta presidencial del 31 de mayo en Medellín, llevada al nivel más fino: el barrio. Abelardo arrasó la ciudad; Cepeda resistió en pocos focos del centro y la ladera. Acá está el mapa, polígono a polígono.</p>
<div class="byline">Ricardo Ruiz · ricardoruiz.co · Preconteo Registraduría 1ª vuelta por mesa · barrios oficiales (DAP, 332)</div>
<p class="lead">Medellín votó <b>Abelardo __AB__ %</b> y <b>Cepeda __CE__ %</b> en primera vuelta, con Fajardo (__SF__ %) y Paloma (__PA__ %) más atrás. Abelardo se llevó la ciudad con más del doble de votos que Cepeda: cruzando el preconteo por mesa con la cartografía de barrios, de los <b>__DIRECT__ barrios con dato directo Abelardo ganó __WIN_AB__ y Cepeda __WIN_CE__</b>. El azul cubre casi todo el valle; el rojo de Cepeda aparece en focos del centro, Manrique, Popular y la ladera nororiental. Pasa el cursor sobre cualquier barrio para ver su resultado.</p>
<div class="legend"><span>Abelardo<span style="display:inline-flex;gap:2px;margin-left:6px"><i style="background:#9db4f5"></i><i style="background:#5b82ef"></i><i style="background:#3a5bd0"></i><i style="background:#1f2a8c"></i></span></span><span>Cepeda<span style="display:inline-flex;gap:2px;margin-left:6px"><i style="background:#f2a59d"></i><i style="background:#e2685c"></i><i style="background:#cf4135"></i><i style="background:#9c1e15"></i></span></span><span style="color:rgba(255,255,255,.55)">claro → oscuro = mayor % del ganador</span><span><i style="background:#2a2f3e"></i>sin puesto = vecino (translúcido)</span></div>
<div id="map"></div>
<div class="mapcap"><b>__DIRECT__ barrios con dato directo</b> de __NB__. Los barrios sin puesto propio se colorean con la tendencia del barrio vecino más cercano, en tono más claro — su voto se cuenta en el puesto donde efectivamente votan. Incluye los 5 corregimientos (Palmitas, San Cristóbal, Altavista, San Antonio de Prado y Santa Elena), de cobertura rural más rala.</div>
<h2>Los extremos de cada lado</h2>
<div class="cols">
<div class="col ab"><h3>Barrios más Abelardo</h3><ol id="top-ab"></ol></div>
<div class="col ce"><h3>Barrios más Cepeda</h3><ol id="top-ce"></ol></div>
</div>
<div class="method">
<p><b>Datos:</b> preconteo Registraduría 1ª vuelta (31-may-2026) por mesa. <b>Mesa→barrio:</b> cada puesto de votación se asigna por punto-en-polígono (su lat/lon de <code>PUESTOS_GEOREF</code>) al barrio oficial que lo contiene. <b>Cartografía:</b> 332 barrios y veredas oficiales de Medellín (Departamento Administrativo de Planeación).</p>
<p><b>Cobertura:</b> el cruce ubica el <b>__COV__ %</b> de los votos de Medellín en un barrio con dato directo. Las zonas especiales 90 (puesto censo) y 98 (cárceles/atípicos) se excluyen por no ser barrios reales.</p>
<p><b>Límite:</b> un puesto sirve a votantes de varios barrios vecinos, pero se asigna al barrio donde está físicamente. El mapa muestra dónde votó cada puesto, no el domicilio exacto del votante. Es preconteo (preliminar).</p>
</div>
<div class="dl">
<div class="dl-title">Descarga los datos <span class="tag">REGISTRADOS</span></div>
<div class="dl-body" id="dl-body">Verificando tu plan…</div>
</div>
<div class="cta">
<div class="cta-title">Datos electorales hasta el barrio y la mesa</div>
<div class="cta-body">Este cruce mesa→barrio es el motor de los módulos de ricardoruiz.co para Medellín: voto histórico, seguridad, arquetipos territoriales y escenarios 2027. Para equipos de campaña, medios y gremios.</div>
<a href="bogota-1v-barrios.html" class="cta-btn">Ver el mapa de Bogotá</a><a href="noticias.html" class="cta-btn alt">Volver a Noticias</a>
</div>
<div class="foot">© Ricardo Ruiz · <a href="index.html">ricardoruiz.co</a> · Mapa publicado el 3 de junio de 2026 · preconteo Registraduría 1ª vuelta + cartografía de barrios oficiales de Medellín.</div>
</main>
<script>
const BARRIOS=__BARRIOS__;
const FILL=__FILL__;
const GEO_URL='__GEO_URL__';
function fillFor(win,pct){const r=win==='Abelardo'?['#9db4f5','#5b82ef','#3a5bd0','#1f2a8c']:(win==='Cepeda'?['#f2a59d','#e2685c','#cf4135','#9c1e15']:['#fb923c','#fb923c','#fb923c','#fb923c']);return r[pct<40?0:pct<50?1:pct<60?2:3];}
const map=L.map('map',{center:[6.25,-75.58],zoom:12,scrollWheelZoom:true,zoomControl:true,attributionControl:false});
fetch(GEO_URL).then(r=>r.json()).then(geo=>{
 const layer=L.geoJSON(geo,{style:f=>{const code=f.properties.CODIGO;const v=BARRIOS[code];
   if(v)return{fillColor:fillFor(v.win,v.winpct),fillOpacity:.95,color:'rgba(255,255,255,.18)',weight:.5};
   if(FILL[code])return{fillColor:fillFor(FILL[code].w,FILL[code].p),fillOpacity:.62,color:'rgba(255,255,255,.18)',weight:.5};
   return{fillColor:'#2a2f3e',fillOpacity:.5,color:'rgba(255,255,255,.18)',weight:.5};},
  onEachFeature:(f,l)=>{const p=f.properties;const code=p.CODIGO;const v=BARRIOS[code];
   let html=`<b>${p.NOMBRE}</b><br><span style="color:rgba(255,255,255,.55)">${p.COMUNA||''}</span>`;
   if(v){const tot=v.urna||1;const pc=x=>Math.round(1000*x/tot)/10;
    html+=`<br>Ganó <b>${v.win}</b> · ${v.winpct}%<br>Abelardo ${pc(v.ab)}% · Cepeda ${pc(v.ce)}%<br>Fajardo ${pc(v.sf)}% · Paloma ${pc(v.pa)}% · <span style="color:rgba(255,255,255,.55)">${tot.toLocaleString('es')} votos</span>`;}
   else if(FILL[code]) html+=`<br><span style="color:rgba(255,255,255,.55)">Sin puesto propio · tendencia del vecino: <b>${FILL[code].w}</b> (~${Math.round(FILL[code].p)} %)</span>`;
   else html+=`<br><span style="color:rgba(255,255,255,.5)">sin puesto de votación</span>`;
   l.bindTooltip(html,{sticky:true});
   l.on('mouseover',()=>l.setStyle({weight:2,color:'#fff'}));l.on('mouseout',()=>l.setStyle({weight:.5,color:'rgba(255,255,255,.18)'}));}
 }).addTo(map);
 map.fitBounds(layer.getBounds(),{padding:[10,10]});
}).catch(e=>{document.getElementById('map').innerHTML='<div style="padding:2rem;color:#fb923c;font-family:Avenir">No se pudo cargar la cartografía: '+e.message+'</div>';});
// tops
const arr=Object.values(BARRIOS).filter(v=>v.urna>200);
const byAb=[...arr].sort((a,b)=>b.ab/b.urna-a.ab/a.urna).slice(0,8);
const byCe=[...arr].sort((a,b)=>b.ce/b.urna-a.ce/a.urna).slice(0,8);
const li=(v,k)=>`<li><span>${v.n} <span style="color:rgba(255,255,255,.4);font-size:.8em">· ${v.loc}</span></span><b>${Math.round(1000*v[k]/v.urna)/10}%</b></li>`;
document.getElementById('top-ab').innerHTML=byAb.map(v=>li(v,'ab')).join('');
document.getElementById('top-ce').innerHTML=byCe.map(v=>li(v,'ce')).join('');
// descargas: gratis para usuarios registrados
(async function(){
 const AUTH='https://rr-auth.reruizc.workers.dev/auth/me';
 const FILES=[['Resultados 1V por mesa · país · nombres (.xlsx)','https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/DESCARGAS/Resultados_1V_2026_por_mesa.xlsx'],
 ['Preconteo 1V por mesa · país · con Claudia (.csv)','https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/DESCARGAS/PRECONTEO_1V_2026_MESA_con_Claudia.csv']];
 let plan='anonymous';
 try{const raw=localStorage.getItem('rr-user'); if(raw) plan=(JSON.parse(raw).plan)||'free';
  const tok=localStorage.getItem('rr-token');
  if(tok){const r=await fetch(AUTH,{headers:{Authorization:'Bearer '+tok}}); if(r.ok){const d=await r.json(); if(d&&d.ok&&d.user) plan=d.user.plan||'free';}}
 }catch(e){}
 const el=document.getElementById('dl-body'); if(!el)return;
 if(plan!=='anonymous'){
  el.innerHTML='El preconteo de 1ª vuelta <b>completo, mesa a mesa, de todo el país</b> (121.863 mesas · los 13 candidatos con votación bruta por mesa). El Excel trae nombres de departamento, municipio y puesto; el CSV los códigos crudos.<br>'+FILES.map(f=>`<a class="dl-btn" href="${f[1]}" download>↓ ${f[0]}</a>`).join('');
 } else {
  el.innerHTML='El preconteo de 1ª vuelta <b>completo, mesa a mesa, de todo el país</b> (121.863 mesas · los 13 candidatos, en Excel y CSV) es gratis para usuarios <b>registrados</b>.<br><a class="dl-lock" href="register.html">🔒 Regístrate gratis para descargar</a>';
 }
})();
</script>
</body></html>
'''

if __name__ == "__main__":
    main()
