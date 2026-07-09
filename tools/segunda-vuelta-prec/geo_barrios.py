#!/usr/bin/env python3
"""
Resolución barrio/comuna por puesto para las ciudades principales, extraída de
build_ciudades_barrios_xlsx.py (2V) para reusarla en los Excel de 1V y de edad.

Regla del proyecto: coordenadas > nombre. Un puesto cuyo BARRIO concatena varios
("Dindalito, Ciudad de Cali, ...") o es basura ("N/A"), o cuya COMUNA llega
"NULL", se reasigna por lat/lon al puesto LIMPIO más cercano.

API:
  CITIES(list[(cod5,ciudad)])  ->  build(cities) -> objeto con:
     .M         pcode -> {barrio,comuna,censo,lat,lon}   (master)
     .G         pcode -> {barrio,comuna,censo,lat,lon}   (georef, fallback)
     .RESOLVE   pcode -> (ccode:int, cdisp:str, barrio:str)
     .CITY      cod5 -> ciudad
     .cod5_of(dep,mun) -> cod5|None
     .canon(ciudad, cdisp) -> display canónico de la comuna (grafía con tildes)
     .titlecase(s), .nrm(s)
"""
import json, os, csv, re, unicodedata
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
BD   = os.path.join(ROOT, 'Bases de datos')
OUT  = os.path.join(BD, 'output_2v')
MASTER = os.path.join(OUT, 'master_unificado_puesto.json')
GEOREF = os.path.join(BD, 'PUESTOS_GEOREF.csv')

# ---- las 17 ciudades (orden por votación 2V, igual que el Excel 2V) ----
CITIES = [
    ('16001', 'Bogotá'),       ('01001', 'Medellín'),    ('31001', 'Cali'),
    ('03001', 'Barranquilla'), ('05001', 'Cartagena'),   ('25001', 'Cúcuta'),
    ('27001', 'Bucaramanga'),  ('29001', 'Ibagué'),      ('24001', 'Pereira'),
    ('52001', 'Villavicencio'),('15247', 'Soacha'),      ('21001', 'Santa Marta'),
    ('13001', 'Montería'),     ('23001', 'Pasto'),       ('09001', 'Manizales'),
    ('03052', 'Soledad'),      ('11001', 'Popayán'),
]

# ---------------- normalización ----------------
def nrm(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', str(s or '').upper().strip())
                if unicodedata.category(c) != 'Mn')
    return ' '.join(s.split())

def normm(s):
    return ' '.join(nrm(s).replace('(', ' ').replace(')', ' ').replace('.', ' ').split())

SMALL = {'DE', 'DEL', 'LA', 'LAS', 'LOS', 'EL', 'Y', 'EN', 'A', 'PARA', 'POR', 'CON'}
ROMAN = {'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X'}
def titlecase(s):
    s = ' '.join(str(s or '').split())
    out = []
    for i, w in enumerate(s.split(' ')):
        u = nrm(w)
        if i > 0 and u in SMALL: out.append(w.lower())
        elif u in ROMAN:         out.append(u)
        else:                    out.append(w.lower().capitalize())
    return ' '.join(out)

def clean_comuna(raw):
    s = ' '.join(str(raw or '').split())
    if not s: return (999, 'Sin comuna asignada')
    m = re.match(r'^(\d{2,3})\s*(.+)$', s)
    code, name = (int(m.group(1)), m.group(2)) if m else (900, s)
    if nrm(name) in ('NULL', 'NAN', 'NONE', 'SN', ''): return (999, 'Sin comuna asignada')
    return (code, titlecase(name))

def pcode(cod5, zona, puesto):
    return f"{cod5}{str(zona).strip().zfill(2)}{str(puesto).strip().zfill(2)}"

def fnum(x):
    try: return float(x)
    except: return None

BAD_B = {'N/A', 'NA', 'SN', 'S/N', 'NULL', 'NAN', 'NONE', 'NO REGISTRA', 'SIN BARRIO',
         'SIN BARRIO ASIGNADO', 'SIN DATO', '-', ''}
BAD_C = {'NULL', 'NAN', 'NONE', 'SN', 'SIN COMUNA', 'SIN COMUNA ASIGNADA', '-', ''}
def bad_barrio(b):
    bn = nrm(b)
    return (bn in BAD_B) or (',' in b) or bool(re.search(r'\s[-/]\s', b)) or bn.startswith('ENTRE ')
def bad_comuna(c):
    return nrm(c) in BAD_C


class Geo:
    def __init__(self, cities):
        self.CITY = dict(cities)
        self._load_master()
        self._load_georef()
        self._resolve()

    def _load_master(self):
        self.M = {}
        self.master = json.load(open(MASTER))
        for p in self.master:
            self.M[p['pcode']] = {'barrio': (p.get('barrio') or '').strip(),
                                  'comuna': (p.get('comuna') or '').strip(),
                                  'censo':  int(p.get('pot') or 0),
                                  'lat': p.get('lat'), 'lon': p.get('lon')}

    def _load_georef(self):
        self.name2cod5 = {}
        self.G = {}
        with open(GEOREF, encoding='utf-8-sig') as f:
            for r in csv.DictReader(f, delimiter=';'):
                cc = (r['CÓDIGO COMPLETO'] or '').strip()
                if len(cc) < 9: continue
                self.name2cod5.setdefault((normm(r['DEPARTAMENTO']), normm(r['MUNICIPIO'])), cc[:5])
                try: censo = int(r['MUJERES'] or 0) + int(r['HOMBRES'] or 0)
                except: censo = 0
                self.G[cc] = {'barrio': (r['BARRIO'] or '').strip(),
                              'comuna': (r.get('NOMBRE COMUNA') or '').strip(), 'censo': censo,
                              'lat': r.get('LATITUD'), 'lon': r.get('LONGITUD')}

    def cod5_of(self, dep, mun):
        nd, nm = normm(dep), normm(mun)
        if nd.startswith('BOGOTA') or nm.startswith('BOGOTA'): return '16001'
        return self.name2cod5.get((nd, nm))

    def _resolve(self):
        CITYP = defaultdict(list)
        for code in set(self.M) | set(self.G):
            if code[:5] not in self.CITY: continue
            g = self.M.get(code) or self.G.get(code)
            CITYP[code[:5]].append((code, fnum(g.get('lat')), fnum(g.get('lon')),
                                    (g.get('comuna') or ''), (g.get('barrio') or '')))

        def _nearest(la, lo, pool):
            best, bd = None, 1e18
            for xla, xlo, xc in pool:
                d = (xla - la) ** 2 + (xlo - lo) ** 2
                if d < bd: bd, best = d, xc
            return best

        self.RESOLVE = {}
        self.reasign = {'barrio': 0, 'comuna': 0}
        for c5, plist in CITYP.items():
            rawmap = {code: (c, b) for code, la, lo, c, b in plist}
            cleanB = [(la, lo, code) for code, la, lo, c, b in plist
                      if la is not None and not bad_barrio(b) and not bad_comuna(c)]
            cleanC = [(la, lo, code) for code, la, lo, c, b in plist
                      if la is not None and not bad_comuna(c)]
            for code, la, lo, c, b in plist:
                bb, bc = bad_barrio(b), bad_comuna(c)
                if not bb and not bc:
                    cc, cd = clean_comuna(c); self.RESOLVE[code] = (cc, cd, b.strip())
                elif bb:
                    tgt = _nearest(la, lo, cleanB) if (la is not None and cleanB) else None
                    if tgt:
                        tc, tb = rawmap[tgt]; cc, cd = clean_comuna(tc)
                        self.RESOLVE[code] = (cc, cd, tb.strip()); self.reasign['barrio'] += 1
                    else:
                        self.RESOLVE[code] = (999, 'Sin comuna asignada', 'Sin barrio asignado')
                else:
                    tgt = _nearest(la, lo, cleanC) if (la is not None and cleanC) else None
                    if tgt:
                        tc, _ = rawmap[tgt]; cc, cd = clean_comuna(tc)
                        self.RESOLVE[code] = (cc, cd, b.strip()); self.reasign['comuna'] += 1
                    else:
                        self.RESOLVE[code] = (900, 'Sin comuna asignada', b.strip())
        # display canónico de la comuna (una sola grafía, prefiere tildes) se calcula on the fly
        self._canon = {}

    def register_canon(self, ciudad, cdisp):
        def _dscore(s): return (1 if any(ord(c) > 127 for c in s) else 0, len(s))
        ck = nrm(cdisp)
        cur = self._canon.get((ciudad, ck))
        if cur is None or _dscore(cdisp) > _dscore(cur):
            self._canon[(ciudad, ck)] = cdisp

    def canon(self, ciudad, cdisp):
        return self._canon.get((ciudad, nrm(cdisp)), cdisp)

    nrm = staticmethod(nrm)
    titlecase = staticmethod(titlecase)


def build(cities=CITIES):
    return Geo(cities)


if __name__ == '__main__':
    g = build()
    print('ciudades:', len(g.CITY), '| puestos resueltos:', len(g.RESOLVE),
          '| reasignados:', g.reasign)
