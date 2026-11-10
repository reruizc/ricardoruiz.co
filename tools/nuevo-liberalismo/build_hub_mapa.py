#!/usr/bin/env python3
"""Mapa liviano para la portada (index.html): los 1.122 municipios como trazos SVG ya proyectados,
con la votación del Nuevo Liberalismo al Concejo en 2023 (share y concejales estimados).
Lee datos/municipios.geojson e inventario.json; escribe datos/hub-mapa.json (empaqueta.py lo vuelve .js).
Correr después de build_inventario.py."""
import json, math, os

D = os.path.join(os.path.dirname(__file__), '..', '..', 'Propuestas', 'nuevo-liberalismo', 'datos')
geo = json.load(open(os.path.join(D, 'municipios.geojson'), encoding='utf-8'))
inv = json.load(open(os.path.join(D, 'inventario.json'), encoding='utf-8'))

cap = inv['capas']['concejo23']
es_nl = [('nl' in k) for k in cap['key']]
share = {}
for mk, m in cap['m'].items():
    v = sum(x[1] for x in m['l'] if es_nl[x[0]])
    c = sum(x[2] for x in m['l'] if es_nl[x[0]])
    if v:
        share[mk] = (v / m['v'] if m['v'] else 0, c, v)

# proyección equirectangular con corrección de latitud media (Colombia ~ 4,5°N)
LAT0 = math.radians(4.5)
def P(lon, lat):
    return lon * math.cos(LAT0), -lat

def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    n = math.hypot(dx, dy) or 1e-12
    imax, dmax = 0, 0
    for i in range(1, len(pts) - 1):
        x, y = pts[i]
        d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / n
        if d > dmax:
            imax, dmax = i, d
    if dmax > eps:
        return rdp(pts[:imax + 1], eps)[:-1] + rdp(pts[imax:], eps)
    return [pts[0], pts[-1]]

feats = []
xs, ys = [], []
for f in geo['features']:
    k = f['properties']['k']
    if k.startswith('88'):   # San Andrés queda fuera del encuadre continental
        continue
    g = f['geometry']
    polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
    rings = []
    for poly in polys:
        ring = [P(*c) for c in poly[0]]
        # anillo cerrado: se parte en dos mitades para que RDP no lo colapse a dos puntos
        h = len(ring) // 2
        ring = rdp(ring[:h + 1], 0.012)[:-1] + rdp(ring[h:], 0.012)
        if len(ring) >= 4:
            rings.append(ring)
            for x, y in ring:
                xs.append(x); ys.append(y)
    if rings:
        feats.append((k, f['properties']['n'], f['properties']['d'], rings))

x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
W = 600.0
s = W / (x1 - x0)
H = (y1 - y0) * s
out = []
for k, n, d, rings in feats:
    path = ''
    for r in rings:
        pts = [(round((x - x0) * s, 1), round((y - y0) * s, 1)) for x, y in r]
        path += 'M' + 'L'.join(f'{a:g},{b:g}' for a, b in pts) + 'Z'
    sh = share.get(k)
    out.append([k, n, d, path] + ([round(sh[0], 4), sh[1], sh[2]] if sh else []))

res = {'v': '2026-11-10', 'w': W, 'h': round(H, 1), 'capa': 'Concejo 2023', 'm': out,
       'n_con_votos': sum(1 for o in out if len(o) > 4), 'n_con_curul': sum(1 for o in out if len(o) > 4 and o[5] > 0)}
json.dump(res, open(os.path.join(D, 'hub-mapa.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(len(out), 'municipios ·', res['n_con_votos'], 'con votos NL ·', res['n_con_curul'], 'con concejal ·',
      round(os.path.getsize(os.path.join(D, 'hub-mapa.json')) / 1024), 'KB')
