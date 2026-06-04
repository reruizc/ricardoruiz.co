#!/usr/bin/env python3
"""
build-mde-barrios-prec/build_carousel.py

Carrusel de Instagram (8 slides 1080x1080) del mapa de Medellín por barrios,
espejo del de Bogotá (rrss/instagram/carousel-bogota-barrios.html). Mismo
formato/CSS (Helvetica + Arima, paper + oxblood) — NO se toca esa estética.

- Lee BARRIOS + FILL ya verificados desde medellin-1v-barrios.html.
- Arma el SVG del mapa (proyección simple, SIN rotar — solo Bogotá rota).
- Emite rrss/instagram/carousel-medellin-barrios.html.

Export a PNG (Chrome headless), igual que Bogotá:
  python3 tools/trasvase-paloma/export_slides.py \
    rrss/instagram/carousel-medellin-barrios.html \
    rrss/instagram/medellin-barrios-png medellin-barrio
"""
import json, re, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEO  = ROOT / "Bases de datos" / "MEDELLIN_BARRIOS_OFICIAL.json"
PAGE = ROOT / "medellin-1v-barrios.html"
OUT  = ROOT / "rrss" / "instagram" / "carousel-medellin-barrios.html"

AB, CE, GRAY = '#1d1d6e', '#c0392b', '#d6d0c0'

def rings_of(g):
    if g['type'] == 'Polygon': return g['coordinates']
    if g['type'] == 'MultiPolygon': return [r for poly in g['coordinates'] for r in poly]
    return []

def main():
    page = PAGE.read_text(encoding='utf-8')
    BAR = json.loads(re.search(r'const BARRIOS=(\{.*?\});', page, re.S).group(1))
    FILL = json.loads(re.search(r'const FILL=(\{.*?\});', page, re.S).group(1))
    geo = json.loads(GEO.read_text(encoding='utf-8'))

    # color por barrio: dato directo -> ganador; sin dato -> vecino (FILL); resto gris
    def colof(cod):
        v = BAR.get(cod)
        if v: return AB if v['win'] == 'Abelardo' else (CE if v['win'] == 'Cepeda' else GRAY)
        f = FILL.get(cod)
        if f: return AB if f['w'] == 'Abelardo' else (CE if f['w'] == 'Cepeda' else GRAY)
        return GRAY

    feats = []
    for f in geo['features']:
        rings = rings_of(f['geometry'])
        if not rings: continue
        feats.append({'cod': f['properties']['CODIGO'], 'rings': rings, 'col': colof(f['properties']['CODIGO'])})

    # proyección equirectangular con corrección cos(lat); sin rotar; flip Y
    allpts = [c for f in feats for ring in f['rings'] for c in ring]
    latm = sum(c[1] for c in allpts) / len(allpts)
    K = math.cos(math.radians(latm))
    P = lambda lo, la: (lo * K, la)
    xs = [P(c[0], c[1])[0] for c in allpts]; ys = [P(c[0], c[1])[1] for c in allpts]
    minx, maxx = min(xs), max(xs); miny, maxy = min(ys), max(ys)
    scale = 900 / max(maxx - minx, maxy - miny)
    VW = round((maxx - minx) * scale); VH = round((maxy - miny) * scale)
    def proj(lo, la):
        x, y = P(lo, la)
        return ((x - minx) * scale, (maxy - y) * scale)
    paths = []
    for f in feats:
        d = ''
        for ring in f['rings']:
            pts = [proj(c[0], c[1]) for c in ring]
            d += 'M' + ' '.join(f'{px:.1f},{py:.1f}' for px, py in pts) + 'Z'
        paths.append(f'<path d="{d}" fill="{f["col"]}" stroke="#f1eee4" stroke-width="0.4"/>')
    svg = (f'<svg viewBox="0 0 {VW} {VH}" width="{VW}" height="{VH}" '
           f'style="display:block;max-width:100%;max-height:600px;width:auto;height:auto">'
           f'{"".join(paths)}</svg>')

    n_ab = sum(1 for v in BAR.values() if v['win'] == 'Abelardo')
    n_ce = sum(1 for v in BAR.values() if v['win'] == 'Cepeda')
    print(f"map svg {VW}x{VH} · barrios {len(feats)} · directos {len(BAR)} (Abelardo {n_ab} / Cepeda {n_ce})")

    html = HEAD + build_slides(svg) + "\n</body></html>\n"
    OUT.write_text(html, encoding='utf-8')
    print("✓", OUT.relative_to(ROOT))


HEAD = r'''<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Arima:wght@500;600;700&display=swap" rel="stylesheet">
<style>
  :root{
    --paper:#f1eee4;--paper2:#e7e2d4;--ink:#1a1510;--ink2:#6b6354;--ink3:#9a9180;
    --ox:#8a1e16;--navy:#1d1d6e;--purp:#534a8f;--cepeda:#c0392b;--green:#2e7d46;--gold:#b8862f;
    --hel:'Helvetica Neue',Helvetica,Arial,sans-serif;--ar:'Arima',sans-serif;
  }
  *{margin:0;padding:0;box-sizing:border-box;}
  body{background:#cfc8b8;}
  .slide{position:relative;width:1080px;height:1080px;background:var(--paper);
    padding:84px 86px 80px;display:flex;flex-direction:column;overflow:hidden;
    background-image:radial-gradient(rgba(26,21,16,.05) 1px,transparent 1.5px);background-size:7px 7px;}
  .slide::after{content:"";position:absolute;left:0;top:0;width:14px;height:100%;background:var(--ox);}
  .eyebrow{font-family:var(--hel);font-weight:700;font-size:23px;letter-spacing:.22em;text-transform:uppercase;color:var(--ox);}
  .rule{width:96px;height:5px;background:var(--ink);margin:24px 0 30px;}
  .headline{font-family:var(--ar);font-weight:700;font-size:74px;line-height:1.02;letter-spacing:-.015em;color:var(--ink);}
  .headline.sm{font-size:60px;}
  .spacer{flex:1;}
  .hero{display:flex;align-items:baseline;gap:18px;}
  .big{font-family:var(--ar);font-weight:700;font-size:236px;line-height:.86;letter-spacing:-.03em;color:var(--ox);}
  .big.navy{color:var(--navy);}.big.purp{color:var(--cepeda);}.big.gray{color:var(--ink2);}
  .unit{font-family:var(--ar);font-weight:600;font-size:48px;color:var(--ink2);}
  .body{font-family:var(--hel);font-weight:400;font-size:35px;line-height:1.42;color:var(--ink);max-width:880px;}
  .body b{font-weight:700;color:var(--ox);}
  .foot{display:flex;justify-content:space-between;align-items:center;font-family:var(--hel);font-size:24px;color:var(--ink3);border-top:1.5px solid rgba(26,21,16,.18);padding-top:22px;margin-top:30px;}
  .foot b{color:var(--ink2);font-weight:700;}
  .cover .kicker{font-family:var(--hel);font-weight:700;font-size:25px;letter-spacing:.18em;text-transform:uppercase;color:var(--ox);}
  .cover .title{font-family:var(--ar);font-weight:700;font-size:120px;line-height:.94;letter-spacing:-.03em;color:var(--ink);margin-top:18px;}
  .cover .vs{margin-top:auto;}
  .row{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;}
  .cand{font-family:var(--ar);font-weight:700;}
  .cand .nm{font-size:34px;letter-spacing:.01em;}
  .cand .pc{font-size:100px;line-height:.9;letter-spacing:-.03em;}
  .cn-l .nm,.cn-l .pc{color:var(--navy);}.cn-r .nm,.cn-r .pc{color:var(--cepeda);}
  .vsmid{font-family:var(--ar);font-weight:600;font-size:38px;color:var(--ink2);padding-bottom:14px;}
  .balota{font-family:var(--hel);font-weight:700;font-size:29px;color:var(--ink);margin-top:30px;letter-spacing:.01em;}
  .balota span{color:var(--ox);}
  .bars{margin-top:10px;}
  .barL{display:flex;align-items:center;gap:20px;margin-bottom:22px;}
  .barL .nm{font-family:var(--ar);font-weight:700;font-size:32px;color:var(--ink);width:300px;line-height:1.05;}
  .barL .nm small{display:block;font-family:var(--hel);font-weight:600;font-size:18px;color:var(--ink3);text-transform:uppercase;letter-spacing:.04em;}
  .barL .tr{flex:1;height:40px;background:rgba(26,21,16,.07);position:relative;}
  .barL .fl{height:100%;}
  .barL .pc{font-family:var(--ar);font-weight:700;font-size:40px;width:110px;text-align:right;}
</style></head>
<body>
'''


def build_slides(svg):
    return f'''
<!-- 1 · PORTADA -->
<section class="slide cover">
  <div class="kicker">Elecciones · Medellín · 1ª vuelta 2026</div>
  <div class="title">Medellín,<br>barrio<br>por barrio</div>
  <div class="vs">
    <div class="row">
      <div class="cand cn-l"><div class="nm">ABELARDO</div><div class="pc">54,5%</div></div>
      <div class="vsmid">vs</div>
      <div class="cand cn-r" style="text-align:right"><div class="nm">CEPEDA</div><div class="pc">24,1%</div></div>
    </div>
    <div class="balota">Abelardo se llevó la ciudad. <span>Y se ve barrio a barrio.</span></div>
  </div>
  <div class="foot"><span><b>@ricardoeruiz_</b></span><span>ricardoruiz.co</span></div>
</section>

<!-- 2 · MAPA -->
<section class="slide">
  <div class="eyebrow">El mapa · Medellín completa</div><div class="rule"></div>
  <h1 class="headline" style="font-size:58px;margin-bottom:8px">Un valle azul, una grieta roja.</h1>
  <div style="flex:1;display:flex;align-items:center;justify-content:center;margin:6px 0">{svg}</div>
  <div style="font-family:var(--hel);font-weight:700;font-size:26px;color:var(--ink);display:flex;gap:40px;justify-content:center;margin-bottom:6px">
    <span><span style="display:inline-block;width:20px;height:20px;background:{AB};vertical-align:-3px;border-radius:3px"></span> Abelardo</span>
    <span><span style="display:inline-block;width:20px;height:20px;background:{CE};vertical-align:-3px;border-radius:3px"></span> Cepeda</span>
  </div>
  <div class="foot"><span><b>@ricardoeruiz_</b></span><span>Ganador por barrio · sin puesto = color del vecino · mapa interactivo en ricardoruiz.co</span></div>
</section>

<!-- 3 · EL MARCO -->
<section class="slide">
  <div class="eyebrow">01 · El marco</div><div class="rule"></div>
  <h1 class="headline">Medellín se entregó a Abelardo.</h1>
  <div class="spacer"></div>
  <div class="hero"><span class="big navy">54,5</span><span class="unit">%</span></div>
  <p class="body" style="margin-top:26px">Abelardo se llevó la capital antioqueña con <b>más del doble de votos que Cepeda</b> (24,1%). Fajardo (8,6%) y Paloma (8,3%) quedaron muy atrás.</p>
  <div class="foot"><span><b>@ricardoeruiz_</b></span><span>Presidencial 1V 2026 · Medellín</span></div>
</section>

<!-- 4 · EL BARRIDO -->
<section class="slide">
  <div class="eyebrow">02 · El barrido</div><div class="rule"></div>
  <h1 class="headline">No fue una victoria: fue un barrido.</h1>
  <div class="spacer"></div>
  <div class="hero"><span class="big navy">137</span><span class="unit">barrios</span></div>
  <p class="body" style="margin-top:26px">De los <b>154 barrios con dato directo</b>, Abelardo ganó 137 y Cepeda 17. El azul cubre casi todo el valle; el rojo se aprieta en una sola franja.</p>
  <div class="foot"><span><b>@ricardoeruiz_</b></span><span>154 barrios con dato directo · resto = vecino</span></div>
</section>

<!-- 5 · LA ZONA ALTA = ABELARDO -->
<section class="slide">
  <div class="eyebrow">03 · La zona alta</div><div class="rule"></div>
  <h1 class="headline">Donde el metro cuadrado es más caro, arrasó Abelardo.</h1>
  <div class="spacer"></div>
  <div class="bars">
    <div class="barL"><div class="nm">El Tesoro<small>El Poblado</small></div><div class="tr"><div class="fl" style="width:79%;background:var(--navy)"></div></div><div class="pc" style="color:var(--navy)">79%</div></div>
    <div class="barL"><div class="nm">El Castillo<small>El Poblado</small></div><div class="tr"><div class="fl" style="width:79%;background:var(--navy)"></div></div><div class="pc" style="color:var(--navy)">79%</div></div>
    <div class="barL"><div class="nm">Las Palmas<small>Corr. Santa Elena</small></div><div class="tr"><div class="fl" style="width:79%;background:var(--navy)"></div></div><div class="pc" style="color:var(--navy)">79%</div></div>
  </div>
  <p class="body" style="margin-top:14px">El Poblado y la parte alta de la ciudad: Abelardo <b>por encima del 78%</b>.</p>
  <div class="foot"><span><b>@ricardoeruiz_</b></span><span>Top barrios Abelardo · % del barrio</span></div>
</section>

<!-- 6 · LA LADERA = CEPEDA -->
<section class="slide">
  <div class="eyebrow">04 · La ladera</div><div class="rule"></div>
  <h1 class="headline">Cepeda resiste en el centro y la montaña nororiental.</h1>
  <div class="spacer"></div>
  <div class="bars">
    <div class="barL"><div class="nm">El Chagualo<small>La Candelaria</small></div><div class="tr"><div class="fl" style="width:53%;background:var(--cepeda)"></div></div><div class="pc" style="color:var(--cepeda)">53%</div></div>
    <div class="barL"><div class="nm">Santo Domingo Savio<small>Popular</small></div><div class="tr"><div class="fl" style="width:50%;background:var(--cepeda)"></div></div><div class="pc" style="color:var(--cepeda)">50%</div></div>
    <div class="barL"><div class="nm">Trece de Noviembre<small>Villa Hermosa</small></div><div class="tr"><div class="fl" style="width:44%;background:var(--cepeda)"></div></div><div class="pc" style="color:var(--cepeda)">44%</div></div>
  </div>
  <p class="body" style="margin-top:14px">Popular, Manrique, Villa Hermosa, Moravia: la <b>Medellín popular de la ladera</b>.</p>
  <div class="foot"><span><b>@ricardoeruiz_</b></span><span>Top barrios Cepeda · % del barrio</span></div>
</section>

<!-- 7 · LA TESIS -->
<section class="slide" style="justify-content:center">
  <div class="eyebrow">05 · La tesis</div><div class="rule"></div>
  <h1 class="headline" style="font-size:108px;line-height:.98">Es un mapa<br>de ladera.</h1>
  <p class="body" style="margin-top:36px;font-size:37px">El valle y la zona alta → <b style="color:var(--navy)">Abelardo</b>. El centro y la ladera nororiental popular → <b style="color:var(--cepeda)">Cepeda</b>. La vieja división social de Medellín, dibujada con votos.</p>
  <div class="spacer"></div>
  <div class="foot"><span><b>@ricardoeruiz_</b></span><span>Medellín · 1ª vuelta 2026</span></div>
</section>

<!-- 8 · CIERRE -->
<section class="slide" style="justify-content:center">
  <div class="eyebrow">06 · El mapa</div><div class="rule"></div>
  <h1 class="headline">154 barrios con dato. Pasa el cursor y ves cada uno.</h1>
  <p class="body" style="margin-top:36px;font-size:38px">Publicamos el <b>mapa interactivo</b> de Medellín barrio por barrio, con la metodología completa (preconteo por mesa × barrios oficiales del DAP).</p>
  <div class="spacer"></div>
  <div class="balota" style="font-size:34px">👉 ricardoruiz.co/medellin-1v-barrios.html</div>
  <div class="foot"><span><b>@ricardoeruiz_</b></span><span>Mapa interactivo → ricardoruiz.co</span></div>
</section>
'''


if __name__ == "__main__":
    main()
