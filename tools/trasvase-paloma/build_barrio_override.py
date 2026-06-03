#!/usr/bin/env python3
"""
build_barrio_override.py

Sobre el cruce PIP puesto→barrio de Bogotá (build_barrio_pip.py), aplica la
regla "llenar barrios huérfanos por nombre": si un puesto se LLAMA como un
barrio catastral (p.ej. "QUINTA PAREDES A") y ese barrio HOY no tiene ningún
puesto (huérfano bajo PIP), se le asigna el puesto por nombre — pero SOLO si
moverlo no deja huérfano a su barrio-fuente PIP (la fuente debe tener >1 puesto).

Reproduce primero el baseline PIP y comprueba que coincide con el BARRIOS
publicado (625 · Cepeda 412 / Abelardo 213) antes de tocar nada. Luego regenera
BARRIOS + FILL y reinyecta en bogota-1v-barrios.html (+ json de output_trasvase).

stdlib pura.
"""
import csv, json, re, collections, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEO   = ROOT / "CIUDADES" / "BOGOTA" / "BOG-BARRIOS-CATASTRALES.geojson"
GEOREF= ROOT / "Bases de datos" / "PUESTOS_GEOREF.csv"
PREC  = ROOT / "Bases de datos" / "nuevos archivos 1v 2026" / "PRECONTEO_1V_2026_MESA_nombres_corregidos.csv"
HTML  = ROOT / "bogota-1v-barrios.html"
OUT_MAP = ROOT / "Bases de datos" / "output_trasvase" / "bog-puesto-to-barrio-pip.json"
OUT_BAR = ROOT / "Bases de datos" / "output_trasvase" / "bogota-1v-por-barrio.json"
AIRPORT = "005624"

CMAP = [('Abelardo De La Espriella','ab'), ('Iván Cepeda','ce'), ('Paloma Valencia','pa'), ('Sergio Fajardo','sf'),
        ('Santiago Botero','bo'), ('Mauricio Lizcano','li'), ('Miguel Uribe','mu'), ('Sondra Macollins','ma'),
        ('Roy Barreras','ro'), ('Gilberto Murillo','gm'), ('Carlos Caicedo','ca'), ('Gustavo Matamoros','mt')]
CAND = {'ab':'Abelardo','ce':'Cepeda','pa':'Paloma','sf':'Fajardo','cl':'Claudia','bo':'Botero'}
SUF = {'A','B','C','D','I','II','III','IV','V','1','2','3'}

def norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii','ignore').decode().upper().strip()
    return ' '.join(s.split())

def strip_suffix(n):
    parts = n.rsplit(' ', 1)
    return parts[0] if len(parts) == 2 and parts[1] in SUF else n

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
    byname = collections.defaultdict(list)
    for f in geo['features']:
        p = f['properties']; ext = rings_of(f['geometry'])
        xs = [c[0] for r in ext for c in r]; ys = [c[1] for r in ext for c in r]
        if not xs: continue
        b = {'cod': p['codigo'], 'nom': p.get('nombre'), 'loc': p.get('loc_nombre'), 'ext': ext,
             'bb': (min(xs), min(ys), max(xs), max(ys)), 'cx': sum(xs)/len(xs), 'cy': sum(ys)/len(ys)}
        B.append(b); byname[norm(b['nom'])].append(b['cod'])
    bidx = {b['cod']: b for b in B}

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

    # ── baseline PIP por key zona-puesto (+ guardo nombre puesto y coords) ──
    baseline = {}; pname = {}; pcoord = {}
    with open(GEOREF, encoding='utf-8-sig', errors='replace') as f:
        rd = csv.reader(f, delimiter=';'); h = [c.strip() for c in next(rd)]; ix = {c: i for i, c in enumerate(h)}
        for r in rd:
            if len(r) <= ix['LONGITUD'] or not (r[ix['DEPARTAMENTO']] or '').upper().startswith('BOGOT'): continue
            try:
                key = f"{int(r[ix['ZONA']]):02d}-{int(r[ix['PUESTO']]):02d}"
                lon = float(r[ix['LONGITUD']]); lat = float(r[ix['LATITUD']])
            except: continue
            if not lon or not lat: continue
            baseline[key] = barrio_pip(lon, lat)
            pname[key] = norm(r[ix['NOMBRE PUESTO']]); pcoord[key] = (lon, lat)

    pcount = collections.Counter(baseline.values())
    running = collections.Counter(baseline.values())  # conteo dinámico para no orfanar fuentes

    # ── override: llenar barrios huérfanos por nombre ──
    # Candidatos ordenados determinísticamente; el conteo corriente garantiza que
    # ninguna fuente quede sin puestos aunque dos puestos compartan barrio-fuente.
    override = {}; moves = []
    cands = []
    for key, npn_raw in pname.items():
        npn = strip_suffix(npn_raw)
        if npn not in byname: continue
        pip_cod = baseline[key]
        tcods = byname[npn]
        if pip_cod in tcods: continue                          # ya coincide
        orphan = [c for c in tcods if pcount.get(c, 0) == 0]    # homónimo sin puestos (baseline)
        if not orphan: continue
        lon, lat = pcoord[key]
        target = min(orphan, key=lambda c: (lon - bidx[c]['cx'])**2 + (lat - bidx[c]['cy'])**2)
        cands.append((key, npn_raw, pip_cod, target))
    for key, npn_raw, pip_cod, target in sorted(cands):
        if running[pip_cod] <= 1: continue                     # no orfanar la fuente (dinámico)
        override[key] = target; running[pip_cod] -= 1; running[target] += 1
        moves.append((key, npn_raw, pip_cod, bidx[pip_cod]['nom'], target, bidx[target]['nom']))

    newmap = {k: override.get(k, v) for k, v in baseline.items()}

    # ── agrega preconteo (dep 16) por barrio; cl = residual de la urna ──
    def aggregate(themap):
        agg = {}
        with open(PREC, encoding='utf-8-sig') as f:
            for r in csv.DictReader(f):
                if r['cod_departamento'] != '16': continue
                try: key = f"{int(r['zona']):02d}-{int(r['puesto']):02d}"
                except: continue
                bc = themap.get(key)
                if not bc: continue
                a = agg.setdefault(bc, {k: 0 for _, k in CMAP} | {'bl': 0, 'nu': 0, 'nm': 0, 'urna': 0})
                for col, k in CMAP: a[k] += int(r[col] or 0)
                a['bl'] += int(r['votos_blanco'] or 0); a['nu'] += int(r['votos_nulos'] or 0)
                a['nm'] += int(r['votos_no_marcados'] or 0); a['urna'] += int(r['total_votos_urna'] or 0)
        for bc, a in agg.items():
            a['cl'] = a['urna'] - (sum(a[k] for _, k in CMAP) + a['bl'] + a['nu'] + a['nm'])
        return agg

    def build_barrios(agg):
        out = {}; wins = collections.Counter()
        for bc, a in agg.items():
            if a['urna'] < 1: continue
            cv = {k: a[k] for k in CAND}; win = max(cv, key=cv.get)
            out[bc] = {'n': bidx.get(bc, {}).get('nom', '?'), 'loc': bidx.get(bc, {}).get('loc', ''),
                       'ab': a['ab'], 'ce': a['ce'], 'pa': a['pa'], 'sf': a['sf'], 'cl': a['cl'],
                       'urna': a['urna'], 'win': CAND[win], 'winpct': round(100 * cv[win] / a['urna'], 1)}
            wins[CAND[win]] += 1
        return out, wins

    # ── 1. reproducir baseline y validar invariante conocido (página original) ──
    base_bar, base_wins = build_barrios(aggregate(baseline))
    assert len(base_bar) == 625 and base_wins['Cepeda'] == 412 and base_wins['Abelardo'] == 213, \
        f"baseline PIP no reproduce la página original (625 · Cepeda 412 / Abelardo 213): {len(base_bar)} {dict(base_wins)}"
    html = HTML.read_text(encoding='utf-8')
    print(f"✓ baseline reproduce la página original: {len(base_bar)} barrios · {dict(base_wins)}")

    # ── 2. versión con override ──
    new_agg = aggregate(newmap)
    new_bar, new_wins = build_barrios(new_agg)

    direct = [bidx[c] for c in new_bar]
    FILL = {}
    for b in B:
        if b['cod'] in new_bar or b['cod'] == AIRPORT: continue
        best = None; bd = 1e18
        for d in direct:
            dd = (b['cx'] - d['cx'])**2 + (b['cy'] - d['cy'])**2
            if dd < bd: bd = dd; best = d
        if best:
            v = new_bar[best['cod']]; FILL[b['cod']] = {'w': v['win'], 'p': v['winpct']}

    print(f"\nMovimientos por nombre (huérfanos llenados): {len(moves)}")
    for key, raw, sc, sn, tc, tn in sorted(moves):
        print(f"  {key:7} '{raw}'  {sc} {sn} → {tc} {tn}")
    print(f"\nBARRIOS directos: {len(base_bar)} → {len(new_bar)} (+{len(new_bar)-len(base_bar)})")
    print(f"winners directo: {dict(new_wins)} | FILL: {len(FILL)}")

    # ── 3. escribir json + reinyectar HTML ──
    OUT_MAP.write_text(json.dumps(newmap), encoding='utf-8')
    OUT_BAR.write_text(json.dumps(new_bar, ensure_ascii=False), encoding='utf-8')

    bj = json.dumps(new_bar, ensure_ascii=False, separators=(',', ':'))
    fj = json.dumps(FILL, ensure_ascii=False, separators=(',', ':'))
    html = re.sub(r'const BARRIOS=\{.*?\};', lambda m: 'const BARRIOS=' + bj + ';', html, count=1, flags=re.S)
    html = re.sub(r'const FILL=\{.*?\};', lambda m: 'const FILL=' + fj + ';', html, count=1, flags=re.S)

    # titular: "Cepeda ganó 412 barrios y Abelardo 213"
    html = re.sub(r'Cepeda ganó \d+ barrios y Abelardo \d+',
                  f"Cepeda ganó {new_wins['Cepeda']} barrios y Abelardo {new_wins['Abelardo']}", html)
    # mapcap: "625 barrios con dato directo"
    html = re.sub(r'\d+ barrios con dato directo',
                  f"{len(new_bar)} barrios con dato directo", html)
    HTML.write_text(html, encoding='utf-8')
    print(f"\n✓ {HTML.name} actualizado (BARRIOS+FILL+titular)")


if __name__ == "__main__":
    main()
