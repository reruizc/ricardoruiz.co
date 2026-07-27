#!/usr/bin/env python3
"""
build_jal_comuna_detalle.py — detalle POR COMUNA/LOCALIDAD de JAL 2023 para el
drill de resultados-jal-2023.html (barrio · puesto · mesa). Un JSON por comuna,
cargado LAZY al abrir la comuna (no entra al JSON principal, que es liviano).

Cada comuna trae:
  - partidos[]  (master, ordenado desc)   · cands[] = [nombre, partyIdx]  (master)
  - barrios[]   = {name, validos, blanco, nulos, v:[[cidx,votos]], feat}
                  (agrupado por polígono de barrio [PIP] en las 7 ciudades con
                   GeoJSON de barrio; por nombre de barrio del georef en el resto)
  - fills[]     = {name, feat, winner_heredado, from, fill:true}   ← SIN datos
  - puestos[]   = {code, nombre, barrio, lat, lon, validos, blanco, nulos,
                   v:[[cidx,votos]], mesas:[[mesa, validos, [[cidx,votos]]]]}
  cidx → cands[] · pidx → partidos[]  (compresión: los nombres no se repiten).

PIP: para las ciudades con GeoJSON de barrio se asigna cada puesto (lat/lon) al
polígono que lo contiene → `feat` = índice de feature en el GeoJSON (el frontend
colorea ese polígono). Bogotá se hace con la geometría SIN rotar (lat/lon reales);
el frontend rota solo para mostrar.

RELLENO DE VECINO (`fills`): los barrios de la comuna que no tienen puesto propio
quedaban como hueco en el mapa. Se emiten aparte —nunca dentro de `barrios`— con
el ganador HEREDADO del barrio con dato más cercano por centroide, mismo criterio
que `_fill_neighbors` de tools/pacto-1v-2026/build_maps.py y que el FILL de
bogota-1v-barrios.html. La membresía barrio→comuna sale del PIP del centroide del
barrio contra el polígono de comuna/localidad que ya usa el mapa superior. Van en
un array propio para que NO puedan entrar a totales, al selector de barrio ni a la
votación por candidato: solo pintan el polígono en tono translúcido. Un barrio con
dato en otra comuna nunca se rellena (se pintaría dos veces con distinto sentido).

Fuentes: GCS_2023JAL.csv (COD_COR=5) · PUESTOS_GEOREF.csv · GeoJSON de barrios (S3).
Salida (gitignored): Bases de datos/output_jal_2023/comuna/{dde}-{mme}-{com}.json
S3: congreso-2026/output/jal-2023/comuna/
"""
import csv, json, os, re, sys, unicodedata, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BD   = os.path.join(ROOT, 'Bases de datos')
SRC  = os.path.join(BD, 'FINAL SUBIDA GCS', 'GCS_2023JAL.csv')
GEOREF = os.path.join(BD, 'PUESTOS_GEOREF.csv')
OUT_DIR = os.path.join(BD, 'output_jal_2023', 'comuna')
SCRATCH = os.environ.get('SCRATCH_DIR',
    '/private/tmp/claude-501/-Users-ricardoruiz-ricardoruiz-co/9416b8e0-fd95-4229-aeaa-f8a817241616/scratchpad')
SORTED = os.path.join(SCRATCH, 'jal_2023_sorted.csv')
GEO_S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/mapas-2026/Ciudades-COM-LOC'
MDE_GEO = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/bases+de+datos/MEDELLIN_BARRIOS_OFICIAL.json'

CITIES = {
    ('16', '001'): 'BOGOTÁ D.C.', ('01', '001'): 'MEDELLÍN', ('31', '001'): 'CALI',
    ('27', '001'): 'BUCARAMANGA', ('25', '001'): 'CÚCUTA', ('29', '001'): 'IBAGUÉ',
    ('09', '001'): 'MANIZALES', ('13', '001'): 'MONTERÍA', ('19', '001'): 'NEIVA',
    ('11', '001'): 'POPAYÁN', ('52', '001'): 'VILLAVICENCIO',
}
# Ciudades con GeoJSON de barrio → mapa de barrios (PIP). url + candidatos a campo nombre.
BARRIO_GEO = {
    ('16', '001'): f'{GEO_S3}/BOG-BARRIOS-CATASTRALES.json',
    ('01', '001'): MDE_GEO,
    ('31', '001'): f'{GEO_S3}/CALI-BARRIOS.json',
    ('27', '001'): f'{GEO_S3}/BUCARAMANGA-BARRIOS.json',
    ('25', '001'): f'{GEO_S3}/CUCUTA-BARRIOS.json',
    ('09', '001'): f'{GEO_S3}/MANIZALES-BARRIOS.json',
    ('11', '001'): f'{GEO_S3}/POPAYAN-BARRIOS.json',
}
# Polígonos de comuna/localidad — LOS MISMOS del mapa superior (CITY_GEO del HTML).
# Se usan para saber a qué comuna pertenece cada barrio (PIP de su centroide).
COMUNA_GEO = {
    ('16', '001'): (f'{GEO_S3}/BOG-LOCALIDADX.json', lambda p: p.get('LocCodigo')),
    ('01', '001'): (f'{GEO_S3}/MEDELLINX.json',      lambda p: p.get('CODIGO')),
    ('31', '001'): (f'{GEO_S3}/CALIX.json',          lambda p: p.get('comuna')),
    ('27', '001'): (f'{GEO_S3}/BUCARAMANGAX.json',   lambda p: p.get('COD_COMUNA')),
    ('25', '001'): (f'{GEO_S3}/CUCUTAX.json',        lambda p: p.get('Comuna')),
    ('09', '001'): (f'{GEO_S3}/MANIZALESX.json',     lambda p: p.get('ID_COMUNA')),
    ('11', '001'): (f'{GEO_S3}/POPAYANX.json',
                    lambda p: p.get('ACAD_TEXT') if p.get('ACAD_TEXT') is not None else p.get('COMUNAS')),
}
NAME_FIELDS = ['nombre', 'NOMBRE', 'barrio', 'BARRIO', 'BARRIOS', 'Barrio', 'NOMBRE_BAR', 'name', 'NOM_BARRIO']
SPECIAL = {'996', '997', '998', '999'}
C_CAN, C_VOT, C_DDE, C_MME, C_ZZ, C_PP = 13, 15, 6, 7, 8, 9
C_MS, C_PAR, C_DESPAR, C_DESCAN = 10, 11, 12, 14


def strip(s):
    return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper().strip()


def clean_com(comN):
    c = re.sub(r'^\d+', '', (comN or '').strip()).strip()
    return c or 'ND'


def load_georef():
    """pcode(9) → dict con barrio, lat, lon, pueNom, comC."""
    g = {}
    with open(GEOREF, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f, delimiter=';'):
            code = (row.get('CÓDIGO COMPLETO') or '').strip()
            if len(code) != 9 or (code[:2], code[2:5]) not in CITIES:
                continue
            comC = (row.get('CÓDIGO COMUNA') or '').strip()
            if comC.upper() in ('NULL', ''):
                comC = 'ND'
            try:
                lat = float((row.get('LATITUD') or '').replace(',', '.'))
                lon = float((row.get('LONGITUD') or '').replace(',', '.'))
            except ValueError:
                lat = lon = None
            g[code] = {
                'barrio': (row.get('BARRIO') or '').strip() or 'SIN BARRIO',
                'lat': lat, 'lon': lon,
                'pueNom': (row.get('NOMBRE PUESTO') or '').strip() or 'PUESTO',
                'comC': comC,
            }
    return g


_GEO_CACHE = {}


def load_geo(url):
    """Baja el GeoJSON una sola vez por corrida (el de barrio lo piden PIP y fills)."""
    if url not in _GEO_CACHE:
        with urllib.request.urlopen(url, timeout=180) as r:
            _GEO_CACHE[url] = json.load(r)
    return _GEO_CACHE[url]


def com_num(v):
    """Código de comuna del GeoJSON → entero ('COMUNA 7' → 7, '03' → 3)."""
    if v is None:
        return None
    d = ''.join(ch for ch in str(v) if ch.isdigit())
    return int(d) if d else None


def pick_name_field(props):
    for f in NAME_FIELDS:
        if f in props and str(props[f]).strip():
            return f
    return None


def build_pip(url):
    """Devuelve (assign(lat,lon)->(featIdx,name)) usando STRtree de shapely."""
    from shapely.geometry import shape, Point
    from shapely.strtree import STRtree
    geo = load_geo(url)
    feats = geo['features']
    namef = None
    for ft in feats:
        namef = pick_name_field(ft.get('properties') or {})
        if namef:
            break
    geoms, idxs, names = [], [], []
    for i, ft in enumerate(feats):
        try:
            gm = shape(ft['geometry'])
        except Exception:
            continue
        if gm.is_empty:
            continue
        geoms.append(gm)
        idxs.append(i)
        props = ft.get('properties') or {}
        names.append(str(props.get(namef, '')).strip() if namef else f'BARRIO {i}')
    tree = STRtree(geoms)

    def assign(lat, lon):
        if lat is None or lon is None:
            return (None, None)
        p = Point(lon, lat)
        for j in tree.query(p):                      # candidatos por bbox
            if geoms[j].covers(p):
                return (idxs[j], names[j])
        # fallback: polígono más cercano (evita huérfanos por puntos en borde/hueco)
        try:
            nj = tree.nearest(p)
            return (idxs[nj], names[nj])
        except Exception:
            return (None, None)
    return assign


def build_fill_ctx(barrio_url, comuna_url, code_fn):
    """Membresía barrio→comuna por PIP del centroide del barrio.

    Devuelve {'members': {comNum: [featIdx…]}, 'name': {featIdx: nombre},
              'pt': {featIdx: (x, y)}}  ·  pt = representative_point (siempre dentro).
    """
    from shapely.geometry import shape
    from shapely.strtree import STRtree
    bgeo = load_geo(barrio_url)
    cgeo = load_geo(comuna_url)

    namef = None
    for ft in bgeo['features']:
        namef = pick_name_field(ft.get('properties') or {})
        if namef:
            break

    cg, cn = [], []
    for ft in cgeo['features']:
        n = com_num(code_fn(ft.get('properties') or {}))
        if n is None:
            continue
        try:
            gm = shape(ft['geometry'])
        except Exception:
            continue
        if not gm.is_empty:
            cg.append(gm)
            cn.append(n)
    tree = STRtree(cg)

    members, names, pts = {}, {}, {}
    sin_comuna = 0
    for i, ft in enumerate(bgeo['features']):
        try:
            gm = shape(ft['geometry'])
        except Exception:
            continue
        if gm.is_empty:
            continue
        p = gm.representative_point()
        props = ft.get('properties') or {}
        names[i] = (str(props.get(namef, '')).strip() if namef else '') or f'BARRIO {i}'
        pts[i] = (p.x, p.y)
        hit = None
        for j in tree.query(p):
            if cg[j].covers(p):
                hit = cn[j]
                break
        if hit is None:               # barrio fuera de la capa de comunas → no se rellena
            sin_comuna += 1
            continue
        members.setdefault(hit, []).append(i)
    return {'members': members, 'name': names, 'pt': pts, 'sin_comuna': sin_comuna}


def barrio_winner(b, cd):
    """Partido más votado del barrio (b['cands'] = {(par,can,nom): votos})."""
    by = {}
    for ck, v in b['cands'].items():
        info = cd['cands'].get(ck)
        if info:
            by[info['par_name']] = by.get(info['par_name'], 0) + v
    if not by:
        return None
    return max(by.items(), key=lambda kv: kv[1])[0]


def add(d, k, v):
    d[k] = d.get(k, 0) + v


def flush_city(cands, key_city, pip, index_rows, fill_ctx=None):
    """Escribe un JSON por comuna de la ciudad."""
    dde, mme = key_city
    # Feats con dato REAL en cualquier comuna de la ciudad: nunca se rellenan.
    # (un barrio puede tener su puesto asignado a la comuna A y caer geométricamente
    #  en la B; pintarlo también en B con tendencia heredada lo contaría dos veces)
    have_city = set()
    if fill_ctx:
        for cd in cands.values():
            for b in cd['barrios'].values():
                if b['feat'] is not None:
                    have_city.add(b['feat'])
    for comC, cd in cands.items():
        if comC == 'ND':
            continue
        # master de partidos y candidatos
        parties = sorted(cd['parties'].items(), key=lambda kv: -kv[1])
        pidx = {p: i for i, (p, _) in enumerate(parties)}
        cand_master = sorted(cd['cands'].items(), key=lambda kv: (-kv[1]['v'], kv[0]))
        cidx = {}
        cands_out = []
        for i, (ckey, info) in enumerate(cand_master):
            cidx[ckey] = i
            cands_out.append([info['nom'], pidx.get(info['par_name'], 0)])

        def vlist(cvotes):
            return sorted(([cidx[k], v] for k, v in cvotes.items()), key=lambda x: -x[1])

        # barrios (por feat PIP si hay; si no, por nombre georef)
        barrios_out = []
        for bkey, b in sorted(cd['barrios'].items(), key=lambda kv: -kv[1]['validos']):
            barrios_out.append({
                'name': b['name'], 'feat': b['feat'],
                'validos': b['validos'], 'blanco': b['blanco'], 'nulos': b['nulos'],
                'v': vlist(b['cands']),
            })
        # relleno de vecino: barrios de ESTA comuna sin puesto propio (sin datos).
        # Heredan el ganador del barrio CON DATO más cercano de la misma comuna.
        fills_out = []
        if fill_ctx and comC.isdigit():
            src = [(b['feat'], fill_ctx['pt'][b['feat']], barrio_winner(b, cd))
                   for b in cd['barrios'].values()
                   if b['feat'] is not None and b['feat'] in fill_ctx['pt']]
            src = [s for s in src if s[2]]
            if src:
                for fi in fill_ctx['members'].get(int(comC), []):
                    if fi in have_city or fi not in fill_ctx['pt']:
                        continue
                    x, y = fill_ctx['pt'][fi]
                    nf, npt, nw = min(src, key=lambda s: (s[1][0] - x) ** 2 + (s[1][1] - y) ** 2)
                    fills_out.append({
                        'name': fill_ctx['name'].get(fi, f'BARRIO {fi}'), 'feat': fi,
                        'winner_heredado': nw,
                        'from': fill_ctx['name'].get(nf, ''), 'fill': True,
                    })
                fills_out.sort(key=lambda f: f['name'])
        # puestos + mesas
        puestos_out = []
        for pk, p in sorted(cd['puestos'].items(), key=lambda kv: -kv[1]['validos']):
            mesas = [[m, mm['validos'], vlist(mm['cands'])]
                     for m, mm in sorted(p['mesas'].items())]
            puestos_out.append({
                'code': pk, 'nombre': p['nombre'], 'barrio': p['barrio'],
                'lat': p['lat'], 'lon': p['lon'],
                'validos': p['validos'], 'blanco': p['blanco'], 'nulos': p['nulos'],
                'v': vlist(p['cands']), 'mesas': mesas,
            })
        out = {
            'dde': dde, 'mme': mme, 'comuna': comC, 'name': cd['name'],
            'has_barrio_map': pip is not None,
            'partidos': [[p, v] for p, v in parties],
            'cands': cands_out,
            'totals': {'validos': cd['validos'], 'blanco': cd['blanco'], 'nulos': cd['nulos']},
            'barrios': barrios_out, 'fills': fills_out, 'puestos': puestos_out,
        }
        path = os.path.join(OUT_DIR, f'{dde}-{mme}-{comC}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
        index_rows.append((f'{dde}-{mme}-{comC}', cd['name'], len(puestos_out),
                           len(barrios_out), os.path.getsize(path), len(fills_out)))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if not (os.path.exists(SORTED) and os.path.getsize(SORTED) > 0):
        sys.exit('Falta el temporal ordenado; corre build_jal_2023.py primero.')
    georef = load_georef()
    print(f'GEOREF (11 ciudades): {len(georef)} puestos')

    # PIP por ciudad (una sola vez): asigna barrio a cada pcode de esa ciudad
    pip_by_city = {}
    fill_by_city = {}    # membresía barrio→comuna para el relleno de vecino
    puesto_barrio = {}   # pcode → (featIdx, name)
    for keyc, url in BARRIO_GEO.items():
        try:
            print(f'· PIP {CITIES[keyc]} …', end=' ', flush=True)
            assign = build_pip(url)
            pip_by_city[keyc] = assign
            n = 0
            for pcode, gi in georef.items():
                if (pcode[:2], pcode[2:5]) != keyc:
                    continue
                fi, nm = assign(gi['lat'], gi['lon'])
                puesto_barrio[pcode] = (fi, nm)
                if fi is not None:
                    n += 1
            print(f'{n} puestos asignados', end='')
        except Exception as e:
            print(f'FALLÓ ({e}) → esta ciudad va sin mapa de barrio')
            pip_by_city[keyc] = None
            continue
        cg = COMUNA_GEO.get(keyc)
        if not cg:
            print()
            continue
        try:
            ctx = build_fill_ctx(url, cg[0], cg[1])
            fill_by_city[keyc] = ctx
            nb = sum(len(v) for v in ctx['members'].values())
            print(f' · {nb} barrios ubicados en comuna ({ctx["sin_comuna"]} fuera de la capa)')
        except Exception as e:
            print(f' · membresía de comuna FALLÓ ({e}) → sin relleno de vecino')

    index_rows = []
    cur = None
    cands = {}

    def comuna(cd_map, comC, name):
        c = cd_map.get(comC)
        if c is None:
            c = cd_map[comC] = {'name': name, 'validos': 0, 'blanco': 0, 'nulos': 0,
                                'parties': {}, 'cands': {}, 'barrios': {}, 'puestos': {}}
        return c

    with open(SORTED, encoding='utf-8', errors='replace', newline='') as f:
        # el temporal ya viene SIN encabezado (awk NR>1 en build_jal_2023.py)
        rd = csv.reader(f, delimiter=';')
        for row in rd:
            if len(row) < 16:
                continue
            dde, mme = row[C_DDE].strip().zfill(2), row[C_MME].strip().zfill(3)
            keyc = (dde, mme)
            if keyc not in CITIES:
                continue
            if keyc != cur:
                if cur is not None:
                    flush_city(cands, cur, pip_by_city.get(cur), index_rows,
                               fill_by_city.get(cur))
                    cands = {}
                cur = keyc
            can = row[C_CAN].strip()
            try:
                v = int(row[C_VOT] or 0)
            except ValueError:
                v = 0
            if v <= 0:
                continue
            zz, pp = (row[C_ZZ] or '').strip().zfill(2), (row[C_PP] or '').strip().zfill(2)
            pcode = f'{dde}{mme}{zz}{pp}'
            gi = georef.get(pcode)
            comC = gi['comC'] if gi else 'ND'
            if comC == 'ND':
                continue
            c = comuna(cands, comC, clean_com(''))   # name se fija abajo con georef comuna
            # nombre de comuna: usar el de resultados (número); dejamos genérico
            if c['name'] == 'ND' or not c['name']:
                c['name'] = f'COMUNA {int(comC)}' if comC.isdigit() else comC
            ms = (row[C_MS] or '').strip().zfill(3)
            # totales de puesto (incluye blanco/nulos para participación local)
            pk = f'{zz}-{pp}'
            p = c['puestos'].get(pk)
            if p is None:
                fi, bnm = puesto_barrio.get(pcode, (None, None))
                barrio_label = bnm or (gi['barrio'] if gi else 'SIN BARRIO')
                p = c['puestos'][pk] = {
                    'nombre': gi['pueNom'] if gi else f'PUESTO {zz}-{pp}',
                    'barrio': barrio_label, 'feat': fi,
                    'lat': gi['lat'] if gi else None, 'lon': gi['lon'] if gi else None,
                    'validos': 0, 'blanco': 0, 'nulos': 0, 'cands': {}, 'mesas': {}}
            mm = p['mesas'].get(ms)
            if mm is None:
                mm = p['mesas'][ms] = {'validos': 0, 'blanco': 0, 'nulos': 0, 'cands': {}}
            # barrio bucket (por feat si hay PIP, si no por nombre)
            bkey = p['feat'] if p['feat'] is not None else strip(p['barrio'])
            b = c['barrios'].get(bkey)
            if b is None:
                b = c['barrios'][bkey] = {'name': p['barrio'], 'feat': p['feat'],
                                          'validos': 0, 'blanco': 0, 'nulos': 0, 'cands': {}}
            if can == '0':
                continue
            if can == '996':
                c['blanco'] += v; p['blanco'] += v; mm['blanco'] += v; b['blanco'] += v
            elif can in SPECIAL:
                c['nulos'] += v; p['nulos'] += v; mm['nulos'] += v; b['nulos'] += v
            else:
                c['validos'] += v; p['validos'] += v; mm['validos'] += v; b['validos'] += v
                par = row[C_PAR].strip()
                party = (row[C_DESPAR] or '').strip() or 'SIN PARTIDO'
                nom = strip(row[C_DESCAN]) or f'CAND {can}'
                ck = (par, can, nom)
                add(c['parties'], party, v)
                cc = c['cands'].get(ck)
                if cc is None:
                    cc = c['cands'][ck] = {'nom': nom, 'par_name': party, 'v': 0}
                cc['v'] += v
                add(p['cands'], ck, v); add(mm['cands'], ck, v); add(b['cands'], ck, v)
    if cur is not None:
        flush_city(cands, cur, pip_by_city.get(cur), index_rows, fill_by_city.get(cur))

    total_bytes = sum(r[4] for r in index_rows)
    total_fill = sum(r[5] for r in index_rows)
    print(f'\n→ {len(index_rows)} comunas · {total_bytes/1e6:.1f} MB total · '
          f'{total_fill} barrios de relleno (vecino más cercano)')
    big = sorted(index_rows, key=lambda r: -r[4])[:5]
    for k, nm, npu, nba, sz, nfl in big:
        print(f'  {k:12} {nm:22} {npu:3} puestos · {nba:3} barrios · {nfl:3} relleno · {sz//1024} KB')


if __name__ == '__main__':
    main()
