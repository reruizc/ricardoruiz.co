#!/usr/bin/env python3
"""¿La votación de un candidato al Concejo de Bogotá 2023 se concentra cerca de
iglesias cristianas no católicas?

    python3 tools/candidato-360/iglesias/analisis.py            # usa el crudo guardado
    python3 tools/candidato-360/iglesias/analisis.py --bajar    # vuelve a pedir OSM y Catastro

Describe TERRITORIO, no votantes (candidato-360.md §3): mide la participación del
candidato en cada puesto (sus votos / válidos del puesto) y la cruza con cuántos
templos hay cerca del puesto. Es correlación ecológica; nada aquí dice quién votó
por quién.

Entradas
  · OSM (Overpass) amenity=place_of_worship en un recuadro que cubre Bogotá
      → Bases de datos/iglesias-bogota/osm-place-of-worship-raw.json
  · Catastro Bogotá, Nombre Geográfico, clase CULT (solo para AUDITAR cobertura)
      → Bases de datos/iglesias-bogota/catastro-nombregeografico-cult.json
  · Votos por mesa de cada candidato: S3 concejo-2023/<slug>.json (gzip)
      → caché en Bases de datos/iglesias-bogota/candidatos/
  · Válidos del Concejo por puesto: Bases de datos/arquetipos-bogota/raw/ter2023.json
      (sale de GCS_2023TER.csv con tools/candidato-360/arquetipos-bogota/extraer.py;
       válidos = candidatos + voto de lista COD_CAN 0; sin 996-999)
  · Coordenadas: Bases de datos/PUESTOS_GEOREF.csv (Bogotá 16-001)
  · Estrato: candidato-360-data/bogota-puesto-barrio.js + Bases de datos/arquetipos-bogota/barrios.csv
  · Límite de Bogotá: CIUDADES/BOGOTA/BOG-LOCALIDAD.json (solo para contar templos «en Bogotá»)

Salida
  · candidato-360-data/iglesias-concejo-bogota-2023.json
"""
import csv, gzip, io, json, math, re, sys, time, unicodedata, urllib.parse, urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import spearmanr

RAIZ = Path(__file__).resolve().parents[3]
BD = RAIZ / 'Bases de datos'
CRUDO = BD / 'iglesias-bogota'
OSM_RAW = CRUDO / 'osm-place-of-worship-raw.json'
CAT_RAW = CRUDO / 'catastro-nombregeografico-cult.json'
CAND_DIR = CRUDO / 'candidatos'
TER = BD / 'arquetipos-bogota' / 'raw' / 'ter2023.json'
GEOREF = BD / 'PUESTOS_GEOREF.csv'
PB_JS = RAIZ / 'candidato-360-data' / 'bogota-puesto-barrio.js'
BARRIOS = BD / 'arquetipos-bogota' / 'barrios.csv'
LIMITE = RAIZ / 'CIUDADES' / 'BOGOTA' / 'BOG-LOCALIDAD.json'
SALIDA = RAIZ / 'candidato-360-data' / 'iglesias-concejo-bogota-2023.json'

S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/concejo-2023'
UA = 'ricardoruiz.co-analisis/1.0 (hola@ricardoruiz.co)'
BBOX = (3.70, -74.50, 4.85, -73.90)  # sur, oeste, norte, este
OVERPASS = ['https://overpass-api.de/api/interpreter',
            'https://maps.mail.ru/osm/tools/overpass/api/interpreter',
            'https://overpass.kumi.systems/api/interpreter']
CATASTRO = 'https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services/sitiosinteres/nombregeografico/MapServer/0'

# slug · grupo · por qué está
CANDIDATOS = [
    ('CONC2023-16-1-5443-2', 'cristiano', 'Bogotá Más Fuerte'),
    ('CONC2023-16-1-5410-5', 'cristiano', 'MIRA (coalición CR-MIRA-U)'),
    ('CONC2023-16-1-5410-2', 'cristiano', 'MIRA (coalición CR-MIRA-U)'),
    ('CONC2023-16-1-7733-5', 'cristiano', 'Colombia Justa Libres (coalición Conservador-CJL)'),
    ('CONC2023-16-1-7733-1', 'cristiano', 'Colombia Justa Libres (coalición Conservador-CJL)'),
    ('CONC2023-16-1-11-7', 'control', 'Centro Democrático'),
    ('CONC2023-16-1-1-12', 'control', 'Partido Liberal'),
    ('CONC2023-16-1-7751-5', 'control', 'Nuevo Liberalismo'),
    ('CONC2023-16-1-4-7', 'control', 'Alianza Verde'),
    ('CONC2023-16-1-1-7', 'control', 'Partido Liberal'),
]
ZONAS_FUERA = {'90', '98'}  # puesto censo (Corferias) y cárceles: no son un lugar de residencia
RADIOS = (500, 1000)
BOOT = 1000

# ---------------------------------------------------------------- clasificación

DEN_CATOLICA = {'catholic', 'roman_catholic'}
DEN_NO_CATOLICA = {'protestant', 'evangelical', 'pentecostal', 'baptist', 'seventh_day_adventist',
                   'adventist', 'mennonite', 'presbyterian', 'lutheran', 'anglican', 'methodist',
                   'quaker', 'foursquare', 'cristiano', 'cristiana', 'church_of_god', 'charismatic',
                   'nondenominational', 'reformed', 'christian'}
# cristianas que NO son del bloque evangélico/protestante (otra tradición, otra relación con lo electoral)
DEN_OTRA_CRISTIANA = {'jehovahs_witness', 'mormon', 'greek_orthodox', 'orthodox', 'christ_scientist',
                      'russian_orthodox', 'new_apostolic'}

# Iglesias grandes: redes con muchas sedes y, varias, con estructura electoral
# propia. No son terreno a disputar para una candidatura cristiana de otra red
# (el G12 es de los Castellanos; la Iglesia de Dios Ministerial, del MIRA).
GRANDES = [
    (r'mision carismatica|\bg12\b|\bmci\b', 'G12 · Misión Carismática Internacional'),
    (r'ministerial', 'Iglesia de Dios Ministerial · MIRA'),
    (r'manantial de vida eterna', 'Manantial de Vida Eterna'),
    (r'lugar de su presencia', 'El Lugar de su Presencia'),
    (r'casa sobre la roca', 'Casa sobre la Roca'),
    (r'bethesda|betesda', 'Centro Misionero Bethesda'),
    (r'universal', 'Iglesia Universal del Reino de Dios'),
]


def red_grande(nombre):
    n = norm(nombre)
    for rx, red in GRANDES:
        if re.search(rx, n):
            return [1, red]
    return [0, '']


def titulo_lugar(s):
    s = str(s or '').strip()
    if not s or s.upper() == 'NULL':
        return ''
    return ' '.join(w if w in ('de', 'del', 'la', 'las', 'los', 'y', 'el') else w.capitalize() for w in s.lower().split())


def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()

CAT_FUERTE = re.compile(r'\b(parroquia|parroquial|capilla|basilica|catedral|santuario|ermita|'
                        r'nuestra senora|diocesis|arquidiocesis|seminario|convento|monasterio|'
                        r'carmelitas|franciscan|jesuita|salesian|agustin|beato|casa cural|hermanas|minuto de dios)', re.I)
NO_CAT = re.compile(r'(cristian[ao]|evangelic|pentecost|\bipuc\b|cuadrangular|\bmira\b|'
                    r'iglesia de dios|centro cristiano|carismatic|tabernaculo|adventista|bautista|'
                    r'asambleas? de dios|menonita|presbiterian|luteran|wesleyan|metodista|'
                    r'alianza cristiana|ministerios?\b|comunidad cristiana|avivamiento|'
                    r'casa sobre la roca|lugar de su presencia|mision paz|iglesia universal|'
                    r'\belim\b|\bbet[h]?el\b|manantial|apostolic|\bmci\b|\bg12\b|rios de vida|'
                    r'filadelfia|renuevo|amor viviente|cruzada|\bteusaquillo cristiana)', re.I)
OTRA_CRISTIANA = re.compile(r'(testigos de jehova|salon del reino|santos de los ultimos dias|'
                            r'mormon|ortodox)', re.I)
CAT_DEBIL = re.compile(r'(\bsan |\bsanta |\bsanto |sagrad|divino nino|virgen|cristo rey|'
                       r'inmaculada|milagrosa|del carmen|espiritu santo|\biglesia de la |'
                       r'\biglesia de (san|santa|santo)\b|perpetuo socorro|eucarist)', re.I)

def clasificar(tags):
    """→ (tipo, regla) con tipo ∈ catolica · no_catolica · otra_cristiana · otra_religion · desconocida"""
    rel = norm(tags.get('religion'))
    den = norm(tags.get('denomination')).replace(' ', '_')
    nom = norm(tags.get('name') or tags.get('official_name') or '')
    if rel and rel not in ('christian', 'catholic', 'cristiana', 'cristiano'):
        return 'otra_religion', 'religion'
    if nom and OTRA_CRISTIANA.search(nom):  # antes que la denominación: hay SUD etiquetados «evangelical»
        return 'otra_cristiana', 'nombre'
    if rel == 'catholic' or den in DEN_CATOLICA:
        return 'catolica', 'denomination'
    if den in DEN_OTRA_CRISTIANA:
        return 'otra_cristiana', 'denomination'
    if den in DEN_NO_CATOLICA and den != 'christian':
        return 'no_catolica', 'denomination'
    if nom:
        if CAT_FUERTE.search(nom):
            return 'catolica', 'nombre'
        if NO_CAT.search(nom):
            return 'no_catolica', 'nombre'
        if CAT_DEBIL.search(nom):
            return 'catolica', 'nombre'
    if den == 'christian':  # «cristiana» genérica en OSM casi siempre es una iglesia evangélica
        return 'no_catolica', 'denomination'
    return 'desconocida', 'sin datos'

# ---------------------------------------------------------------- utilidades

def http(url, data=None, timeout=200):
    req = urllib.request.Request(url, data=data, headers={'User-Agent': UA, 'Accept-Encoding': 'gzip'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        b = r.read()
        if r.headers.get('Content-Encoding') == 'gzip' or b[:2] == b'\x1f\x8b':
            b = gzip.decompress(b)
        return b

def bajar_osm():
    s, w, n, e = BBOX
    q = f'[out:json][timeout:180];(nwr["amenity"="place_of_worship"]({s},{w},{n},{e}););out center tags;'
    for intento in range(4):
        for url in OVERPASS:
            try:
                b = http(url, urllib.parse.urlencode({'data': q}).encode())
                if b[:1] == b'{':
                    OSM_RAW.write_bytes(b)
                    print('OSM:', url)
                    return
            except Exception as ex:
                print('  falla', url, ex)
        time.sleep(20 * (2 ** intento))
    sys.exit('Overpass no respondió')

def bajar_catastro():
    out, off = [], 0
    while True:
        q = urllib.parse.urlencode({'where': "NGECLASIFI='CULT'", 'outFields': 'NGENOMBRE,NGENALTERN,NGEFUENTE',
                                    'outSR': 4326, 'resultOffset': off, 'resultRecordCount': 1000, 'f': 'json'})
        r = json.loads(http(CATASTRO + '/query?' + q))
        fs = r.get('features', [])
        out += fs
        off += len(fs)
        if not fs or not r.get('exceededTransferLimit'):
            break
    CAT_RAW.write_text(json.dumps(out, ensure_ascii=False))

def candidato(slug):
    CAND_DIR.mkdir(parents=True, exist_ok=True)
    f = CAND_DIR / f'{slug}.json'
    if not f.exists():
        f.write_bytes(http(f'{S3}/{slug}.json'))
    return json.loads(f.read_text())

def punto_en_poligono(x, y, anillo):
    dentro = False
    j = len(anillo) - 1
    for i in range(len(anillo)):
        xi, yi = anillo[i][0], anillo[i][1]
        xj, yj = anillo[j][0], anillo[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-15) + xi:
            dentro = not dentro
        j = i
    return dentro

def en_bogota(lon, lat, polis):
    for p in polis:
        if punto_en_poligono(lon, lat, p[0]) and not any(punto_en_poligono(lon, lat, h) for h in p[1:]):
            return True
    return False

def poligonos(geo):
    out = []
    for f in geo['features']:
        g = f['geometry']
        out += [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
    return out

def distancias_m(lat1, lon1, lat2, lon2):
    """matriz de distancias haversine (m) entre dos conjuntos de puntos"""
    R = 6371008.8
    p1, p2 = np.radians(lat1)[:, None], np.radians(lat2)[None, :]
    dphi = p2 - p1
    dl = np.radians(lon2)[None, :] - np.radians(lon1)[:, None]
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))

def cod2(x):
    x = (x or '').strip()
    return f'{int(x):02d}' if x.isdigit() else x

# ---------------------------------------------------------------- main

def main():
    if '--bajar' in sys.argv or not OSM_RAW.exists():
        bajar_osm()
    if '--bajar' in sys.argv or not CAT_RAW.exists():
        bajar_catastro()

    osm = json.loads(OSM_RAW.read_text())
    fecha_osm = osm.get('osm3s', {}).get('timestamp_osm_base')
    polis = poligonos(json.loads(LIMITE.read_text()))

    templos = []
    for e in osm['elements']:
        lat = e.get('lat', e.get('center', {}).get('lat'))
        lon = e.get('lon', e.get('center', {}).get('lon'))
        if lat is None:
            continue
        t = e.get('tags', {})
        tipo, regla = clasificar(t)
        templos.append({'id': f"{e['type'][0]}{e['id']}", 'lat': lat, 'lon': lon, 'tipo': tipo, 'regla': regla,
                        'nombre': t.get('name') or '', 'den': t.get('denomination') or '',
                        'bog': en_bogota(lon, lat, polis),
                        'idmji': bool(re.search(r'ministerial|\bmira\b', norm(t.get('name'))))})
    tm = pd.DataFrame(templos)
    conteo_bbox = tm['tipo'].value_counts().to_dict()
    conteo_bog = tm[tm.bog]['tipo'].value_counts().to_dict()
    reglas_nc = tm[tm.bog & (tm.tipo == 'no_catolica')]['regla'].value_counts().to_dict()
    sin_nombre = int((tm.bog & (tm.nombre == '')).sum())
    print('Templos OSM en el recuadro:', len(tm), conteo_bbox)
    print('  dentro de Bogotá:', int(tm.bog.sum()), conteo_bog, '· no católicas por regla', reglas_nc)

    # --- auditoría de cobertura contra Catastro (fuente independiente de OSM)
    cat = json.loads(CAT_RAW.read_text())
    cat_t = []
    for f in cat:
        a = f['attributes']
        if (a.get('NGEFUENTE') or '').lower() == 'openstreetmap':
            continue  # no es independiente
        nom = a.get('NGENOMBRE') or ''
        n = norm(nom)
        if re.match(r'(placa|escultura|mural|conjunto|reloj|busto|monumento)', n):
            continue
        if not re.search(r'(iglesia|parroquia|capilla|templo|basilica|catedral|santuario|ermita|cristian|evangel|pentecost)', n):
            continue
        tipo, _ = clasificar({'name': nom})
        cat_t.append({'nombre': nom, 'lat': f['geometry']['y'], 'lon': f['geometry']['x'], 'tipo': tipo})
    ct = pd.DataFrame(cat_t)
    d_cat = distancias_m(ct.lat.values, ct.lon.values, tm.lat.values, tm.lon.values)
    ct['en_osm_150m'] = (d_cat <= 150).any(axis=1)
    cobertura = {}
    for tipo in ('catolica', 'no_catolica'):
        sub = ct[ct.tipo == tipo]
        cobertura[tipo] = {'catastro_templos': int(len(sub)), 'con_templo_osm_a_150m': int(sub.en_osm_150m.sum()),
                           'pct': round(float(sub.en_osm_150m.mean()) * 100, 1) if len(sub) else None}
    print('  cobertura vs Catastro:', cobertura)

    # --- puestos de Bogotá con coordenada
    coords = {}
    with open(GEOREF, encoding='utf-8-sig', newline='') as fh:
        for r in csv.DictReader(fh, delimiter=';'):
            cc = r['CÓDIGO COMPLETO'].strip()
            if not cc.startswith('16001'):
                continue
            try:
                lat, lon = float(r['LATITUD']), float(r['LONGITUD'])
            except ValueError:
                continue
            if not (3.7 < lat < 4.9 and -74.5 < lon < -73.9):
                continue
            k = f"{cod2(r['ZONA'])}-{cod2(r['PUESTO'])}"
            coords[k] = (lat, lon, r['NOMBRE PUESTO'].strip(), r['NOMBRE COMUNA'].strip())

    ter = json.loads(TER.read_text())['conc']
    validos = {p: sum(v for k, v in d.items() if int(k.split('|')[1]) < 996) for p, d in ter.items()}
    pb = json.loads(re.search(r'=\s*(\{.*\})', PB_JS.read_text(), re.S).group(1))
    estr = {}
    with open(BARRIOS, encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh):
            if r['estrato']:
                estr[r['codigo']] = float(r['estrato'])

    filas = []
    for p, val in validos.items():
        z = p.split('-')[0]
        if z in ZONAS_FUERA or p not in coords or val <= 0:
            continue
        lat, lon, nom, com = coords[p]
        filas.append({'puesto': p, 'zona': z, 'lat': lat, 'lon': lon, 'nombre': nom, 'com': com, 'validos': val,
                      'estrato': estr.get(pb.get(p))})
    P = pd.DataFrame(filas)
    val_tot = sum(validos.values())
    val_cubierto = int(P.validos.sum())
    print(f'Puestos con coordenada: {len(P)} de {len(validos)} · válidos cubiertos {val_cubierto:,} de {val_tot:,} '
          f'({val_cubierto / val_tot:.1%}) · con estrato {P.estrato.notna().sum()}')

    # --- templos cerca de cada puesto (se cuenta todo el recuadro: un templo al otro lado del límite también es vecino)
    D = distancias_m(P.lat.values, P.lon.values, tm.lat.values, tm.lon.values)
    for tipo, et in (('nc', 'no_catolica'), ('cat', 'catolica'), ('desc', 'desconocida')):
        m = (tm.tipo == et).values
        for r in RADIOS:
            P[f'{tipo}_{r}'] = (D[:, m] <= r).sum(axis=1)
    # densidad continua (núcleo gaussiano σ = 500 m, corte a 2 km) para partir en cuartiles sin empates
    mnc = (tm.tipo == 'no_catolica').values
    Dn = D[:, mnc]
    P['nc_kernel'] = np.where(Dn <= 2000, np.exp(-0.5 * (Dn / 500) ** 2), 0).sum(axis=1)
    P['ncd_1000'] = P.nc_1000 + P.desc_1000  # sensibilidad: las desconocidas cuentan como no católicas
    P['idmji_1000'] = (D[:, tm.idmji.values & mnc] <= 1000).sum(axis=1)
    print('  no católicas a 1 km por puesto: media', round(P.nc_1000.mean(), 2), '· cuantiles',
          P.nc_1000.quantile([.25, .5, .75, .9]).tolist(), '· puestos con 0:', int((P.nc_1000 == 0).sum()))

    # --- candidatos
    idx_nombres = ter  # solo para validar totales
    resultados = []
    rng = np.random.default_rng(2023)
    q75 = P.nc_kernel.quantile(.75)
    q25 = P.nc_kernel.quantile(.25)
    alto = P.nc_kernel >= q75
    bajo = P.nc_kernel <= q25
    print(f'  cuartil alto: {int(alto.sum())} puestos (media {P.nc_1000[alto].mean():.1f} no católicas a 1 km) · '
          f'cuartil bajo: {int(bajo.sum())} puestos (media {P.nc_1000[bajo].mean():.2f})')
    cerca_idmji = P.idmji_1000 > 0

    votos_mapa = {}
    for slug, grupo, nota in CANDIDATOS:
        c = candidato(slug)
        porp = defaultdict(int)
        for m in c['mesas']:
            porp[f"{cod2(m['zon'])}-{cod2(m['pue'])}"] += int(m['v'])
        par, can = slug.split('-')[-2:]
        crudo = sum(d.get(f'{par}|{can}', 0) for d in ter.values())
        if crudo != c['votos']:
            print(f'  ⚠ {slug}: S3 {c["votos"]} vs GCS {crudo}')
        X = P.copy()
        X['v'] = X.puesto.map(porp).fillna(0)
        X['part'] = X.v / X.validos * 100  # en puntos porcentuales
        votos_mapa[slug] = {p: int(v) for p, v in zip(X.puesto, X.v) if v > 0}
        cubre = X.v.sum() / c['votos']

        rho5, p5 = spearmanr(X.part, X.nc_500)
        rho1, p1 = spearmanr(X.part, X.nc_1000)
        rhoc, _ = spearmanr(X.part, X.cat_1000)

        R = X.dropna(subset=['estrato'])
        Xm = pd.DataFrame({'nc_1k': R.nc_1000, 'cat_1k': R.cat_1000, 'estrato': R.estrato,
                           'estrato2': R.estrato ** 2})
        mod = sm.WLS(R.part, sm.add_constant(Xm), weights=R.validos).fit(cov_type='HC1')
        b, se = mod.params['nc_1k'], mod.bse['nc_1k']
        # robustez: efectos fijos de localidad (zona electoral = localidad en Bogotá)
        Xf = pd.concat([Xm, pd.get_dummies(R.zona, prefix='z', drop_first=True, dtype=float)], axis=1)
        modf = sm.WLS(R.part, sm.add_constant(Xf), weights=R.validos).fit(cov_type='HC1')
        bf, sef = modf.params['nc_1k'], modf.bse['nc_1k']
        part_media = X.v.sum() / X.validos.sum() * 100
        Xd = pd.DataFrame({'ncd_1k': R.ncd_1000, 'cat_1k': R.cat_1000, 'estrato': R.estrato,
                           'estrato2': R.estrato ** 2})
        modd = sm.WLS(R.part, sm.add_constant(Xd), weights=R.validos).fit(cov_type='HC1')
        rhod, _ = spearmanr(X.part, X.ncd_1000)
        ci_ = cerca_idmji.values
        r_idmji = (X.v[ci_].sum() / X.validos[ci_].sum()) / (X.v[~ci_].sum() / X.validos[~ci_].sum())

        def razon(ix):
            Y = X.iloc[ix]
            a, bb = alto.values[ix], bajo.values[ix]
            pa = Y.v.values[a].sum() / Y.validos.values[a].sum()
            pb_ = Y.v.values[bb].sum() / Y.validos.values[bb].sum()
            return pa / pb_ if pb_ > 0 else np.nan

        r0 = razon(np.arange(len(X)))
        boots = [razon(rng.integers(0, len(X), len(X))) for _ in range(BOOT)]
        lo, hi = np.nanpercentile(boots, [2.5, 97.5])
        pa = X.v[alto].sum() / X.validos[alto].sum() * 100
        pbj = X.v[bajo].sum() / X.validos[bajo].sum() * 100

        res = {'slug': slug, 'nombre': c['nombre'], 'partido': c['partido'], 'grupo': grupo, 'nota': nota,
               'votos': c['votos'], 'cobertura_votos': round(float(cubre), 4),
               'part_media_pp': round(part_media, 3),
               'spearman_500': round(float(rho5), 3), 'p_500': float(f'{p5:.2g}'),
               'spearman_1k': round(float(rho1), 3), 'p_1k': float(f'{p1:.2g}'),
               'spearman_cat_1k': round(float(rhoc), 3),
               'coef_reg': round(float(b), 4), 'ee': round(float(se), 4),
               'ic95_reg': [round(float(b - 1.96 * se), 4), round(float(b + 1.96 * se), 4)],
               'coef_reg_rel_pct': round(float(b / part_media * 100), 1) if part_media else None,
               'coef_reg_fe_localidad': round(float(bf), 4), 'ee_fe_localidad': round(float(sef), 4),
               'coef_cat_1k': round(float(mod.params['cat_1k']), 4), 'ee_cat_1k': round(float(mod.bse['cat_1k']), 4),
               'spearman_1k_incl_desconocidas': round(float(rhod), 3),
               'coef_reg_incl_desconocidas': round(float(modd.params['ncd_1k']), 4),
               'ee_incl_desconocidas': round(float(modd.bse['ncd_1k']), 4),
               'ratio_cerca_idmji_1k': round(float(r_idmji), 2),
               'r2_reg': round(float(mod.rsquared), 3), 'n_reg': int(mod.nobs),
               'part_cuartil_alto_pp': round(pa, 3), 'part_cuartil_bajo_pp': round(pbj, 3),
               'ratio_cuartil': round(float(r0), 2), 'ratio_ic95': [round(float(lo), 2), round(float(hi), 2)],
               'n_puestos': int(len(X)), 'n_puestos_con_votos': int((X.v > 0).sum())}
        resultados.append(res)
        print(f"  {c['nombre'][:30]:30s} {grupo:9s} ρ500={rho5:+.3f} ρ1k={rho1:+.3f} "
              f"β={b:+.4f}±{se:.4f} (FE {bf:+.4f}±{sef:.4f} · c/desc {modd.params['ncd_1k']:+.4f}±{modd.bse['ncd_1k']:.4f}) "
              f"razón={r0:.2f} [{lo:.2f},{hi:.2f}] idmji={r_idmji:.2f} media={part_media:.2f}pp n={mod.nobs:.0f}")

    # --- salida
    nc = tm[(tm.tipo == 'no_catolica')]
    salida = {
        'v': time.strftime('%Y-%m-%d'),
        'meta': {
            'pregunta': '¿La votación de cada candidato al Concejo de Bogotá 2023 se concentra en puestos con más '
                        'iglesias cristianas no católicas cerca?',
            'regla': 'Describe el territorio de los puestos, nunca a los votantes. Correlación ecológica: cercanía '
                     'de templos no es voto religioso.',
            'fuentes': {
                'templos': f'OpenStreetMap vía Overpass, amenity=place_of_worship, recuadro {BBOX}, base OSM {fecha_osm}',
                'auditoria_cobertura': 'Catastro Bogotá · Nombre Geográfico (clase CULT, sin los registros que vienen de OSM)',
                'votos': 'Registraduría GCS_2023TER (Concejo, COD_COR 4) · fichas por candidato en S3 concejo-2023/',
                'coordenadas': 'PUESTOS_GEOREF.csv (Registraduría, corte 2026)',
                'estrato': 'Estrato medio del barrio del puesto (SDP/IDECA), barrios.csv de arquetipos-bogota',
            },
            'templos_osm': {'en_recuadro': int(len(tm)), 'en_bogota': int(tm.bog.sum()),
                            'por_tipo_en_bogota': {k: int(v) for k, v in conteo_bog.items()},
                            'por_tipo_en_recuadro': {k: int(v) for k, v in conteo_bbox.items()},
                            'no_catolicas_por_regla': {k: int(v) for k, v in reglas_nc.items()},
                            'sin_nombre_en_bogota': sin_nombre,
                            'idmji_en_recuadro': int((tm.idmji & (tm.tipo == 'no_catolica')).sum()),
                            'puestos_a_1km_de_idmji': int(cerca_idmji.sum())},
            'cobertura_osm_vs_catastro': cobertura,
            'puestos': {'con_coordenada_y_votos': int(len(P)), 'puestos_concejo_2023': len(validos),
                        'validos_cubiertos': val_cubierto, 'validos_bogota': val_tot,
                        'pct_validos_cubiertos': round(val_cubierto / val_tot * 100, 1),
                        'con_estrato': int(P.estrato.notna().sum()),
                        'excluidos': 'zonas 90 (puesto censo) y 98 (cárceles), y puestos sin coordenada',
                        'no_catolicas_1k': {'media': round(float(P.nc_1000.mean()), 2),
                                            'mediana': float(P.nc_1000.median()),
                                            'p75': float(q75), 'p25': float(q25),
                                            'puestos_con_cero': int((P.nc_1000 == 0).sum())},
                        'no_catolicas_500': {'media': round(float(P.nc_500.mean()), 2),
                                             'puestos_con_cero': int((P.nc_500 == 0).sum())}},
            'metodo': {
                'participacion': 'votos del candidato en el puesto / válidos del Concejo en el puesto (candidatos + '
                                 'voto de lista; sin blanco, nulos ni no marcados), en puntos porcentuales',
                'densidad': 'número de templos de cada tipo a 500 m y a 1 km del puesto (distancia en línea recta)',
                'spearman': 'correlación de rangos entre participación y templos no católicos cercanos, todos los puestos',
                'regresion': 'mínimos cuadrados ponderados por válidos del puesto: participación ~ no_católicas_1km + '
                             'católicas_1km + estrato + estrato²; errores robustos HC1. coef_reg = puntos porcentuales '
                             'de participación por cada templo no católico adicional a 1 km. Robustez con efectos fijos '
                             'de localidad (zona electoral).',
                'ratio_cuartil': 'participación agregada del candidato en el 25 % de puestos con más templos no '
                                 'católicos cerca dividida por la del 25 % con menos. La cercanía se mide con una '
                                 'densidad continua (núcleo gaussiano σ = 500 m, hasta 2 km) para que los cuartiles no '
                                 f'se empaten en ceros; IC 95 % por bootstrap de puestos ({BOOT} réplicas). Cuartil alto: '
                                 f'{int(alto.sum())} puestos, en promedio {P.nc_1000[alto].mean():.1f} templos no católicos '
                                 f'a 1 km; cuartil bajo: {int(bajo.sum())} puestos, {P.nc_1000[bajo].mean():.2f}.',
                'sensibilidad': 'coef_reg_incl_desconocidas: la misma regresión contando como no católicos los templos '
                                'sin nombre ni denominación. ratio_cerca_idmji_1k: participación en puestos con un templo '
                                'de la Iglesia de Dios Ministerial de Jesucristo Internacional a ≤1 km contra el resto '
                                '(pocos templos mapeados: indicativo).',
                'clasificacion': 'católica: denomination catholic/roman_catholic o nombre (Parroquia, Capilla, Nuestra '
                                 'Señora, San/Santa…). No católica: denomination evangélica/pentecostal/protestante/'
                                 'bautista/adventista/menonita… o nombre (Cristiana, Evangélica, Pentecostal, IPUC, '
                                 'Cuadrangular, MIRA, Iglesia de Dios, Centro Cristiano, Carismática, Tabernáculo…). '
                                 'Testigos de Jehová, Santos de los Últimos Días y ortodoxas van aparte («otra '
                                 'cristiana») y no entran a la medida. Sin nombre ni denominación: desconocida.',
            },
        },
        'candidatos': resultados,
        'iglesias_no_catolicas': [[round(r.lat, 5), round(r.lon, 5), r.nombre] for r in nc.itertuples()],
        'puestos_nc_500': {r.puesto: int(r.nc_500) for r in P.itertuples()},
        # Capa del mapa (oct-27-2026, pedido de Ricardo para Emel Rojas): las
        # iglesias no católicas de Bogotá marcadas grande/pequeña, y los votos de
        # cada candidato por puesto, para que el panel cruce en el navegador
        # cuánto rinde cada candidatura alrededor de cada iglesia pequeña.
        'mapa': {
            'puestos': [[r.puesto, round(r.lat, 5), round(r.lon, 5), int(r.validos), titulo_lugar(r.com)] for r in P.itertuples()],
            'votos': votos_mapa,
            'iglesias': [[round(r.lat, 5), round(r.lon, 5), r.nombre, *red_grande(r.nombre)]
                         for r in nc.itertuples() if r.bog and not re.search(r'\bcolegio\b', norm(r.nombre))],
            'nota_grandes': 'Grandes: redes con muchas sedes y estructura electoral propia (Misión Carismática '
                            'Internacional-G12, Iglesia de Dios Ministerial-MIRA, Manantial de Vida Eterna, El Lugar de '
                            'su Presencia, Casa sobre la Roca, Centro Misionero Bethesda, Iglesia Universal). El resto, '
                            'congregaciones de barrio. Criterio del equipo, por nombre.',
        },
    }
    txt = json.dumps(salida, ensure_ascii=False, separators=(',', ':'))
    SALIDA.write_text(txt)
    print(f'→ {SALIDA.relative_to(RAIZ)} · {len(txt.encode()) / 1024:.0f} KB')


if __name__ == '__main__':
    main()
