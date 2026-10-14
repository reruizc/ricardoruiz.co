#!/usr/bin/env python3
"""Ciudades detectables en titulares, con su centro (mediana de puestos urbanos).

  python3 tools/batalla/build_ciudades.py   → tools/batalla/ciudades.json

Entran las capitales y los municipios con 100.000 electores o más. Se dejan
fuera los nombres que en un titular significan otra cosa (Madrid = España,
Ciénaga = sustantivo, Florida = EE. UU.): detectarlos daría ciudades falsas.
"""
import csv, json, re, statistics, unicodedata
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GEO = REPO / 'Bases de datos' / 'PUESTOS_GEOREF.csv'

CAPITALES = {'BOGOTA. D.C.','MEDELLIN','CALI','BARRANQUILLA','CARTAGENA','BUCARAMANGA','CUCUTA',
  'PEREIRA','MANIZALES','IBAGUE','SANTA MARTA','VILLAVICENCIO','PASTO','MONTERIA','NEIVA',
  'ARMENIA','POPAYAN','SINCELEJO','VALLEDUPAR','TUNJA','RIOHACHA','QUIBDO','FLORENCIA','YOPAL',
  'ARAUCA','MOCOA','LETICIA','SAN JOSE DEL GUAVIARE','INIRIDA','MITU','PUERTO CARRENO','SAN ANDRES'}
FUERA = {'MADRID','CIENAGA','FLORIDA','LA PAZ','BOLIVAR','CORDOBA','CALDAS','SANTANDER','GUAMO',
  'TURBO','LA DORADA','SABANALARGA','EL CARMEN DE BOLIVAR','PLATO'}
NOMBRE = {'BOGOTA. D.C.':'Bogotá','CUCUTA':'Cúcuta','IBAGUE':'Ibagué','POPAYAN':'Popayán',
  'MONTERIA':'Montería','QUIBDO':'Quibdó','MEDELLIN':'Medellín','PUERTO CARRENO':'Puerto Carreño',
  'SAN JOSE DEL GUAVIARE':'San José del Guaviare','INIRIDA':'Inírida','MITU':'Mitú',
  'ITAGUI':'Itagüí','FACATATIVA':'Facatativá','FUSAGASUGA':'Fusagasugá','CHIA':'Chía','ZIPAQUIRA':'Zipaquirá',
  'JAMUNDI':'Jamundí','TULUA':'Tuluá','GIRON':'Girón','APARTADO':'Apartadó','MAGANGUE':'Magangué',
  'OCANA':'Ocaña','SAHAGUN':'Sahagún','SOGAMOSO':'Sogamoso','GIRARDOT':'Girardot','BUENAVENTURA':'Buenaventura'}
# las localidades de Bogotá también ubican un titular («disturbios en Suba» = Bogotá);
# fuera las que son nombre de persona o de equipo (Kennedy, Santa Fe, Rafael Uribe)
ALIAS = {'BOGOTA. D.C.':['bogota','suba','usme','bosa','engativa','fontibon','chapinero','usaquen',
                         'ciudad bolivar','tunjuelito','barrios unidos','puente aranda','teusaquillo',
                         'plaza de bolivar','parque nacional'],'CARTAGENA':['cartagena'],'SAN ANDRES':['san andres'],
  'GUADALAJARA DE BUGA':['buga'],'SAN JUAN DE PASTO':['pasto'],'PASTO':['pasto']}

def norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii','ignore').decode().upper()
    return re.sub(r'\s+',' ', s).strip()

pts, censo, depto = defaultdict(list), defaultdict(int), {}
with open(GEO, encoding='utf-8-sig', errors='replace') as f:
    r = csv.DictReader(f, delimiter=';')
    for row in r:
        m = norm(row.get('MUNICIPIO')); d = norm(row.get('DEPARTAMENTO'))
        # el georef guarda la LOCALIDAD de Bogotá en MUNICIPIO: se juntan en una sola ciudad
        if d.startswith('BOGOTA'): m = 'BOGOTA. D.C.'
        k = (d, m)
        try: censo[k] += int(row.get('MUJERES') or 0) + int(row.get('HOMBRES') or 0)
        except ValueError: pass
        if (row.get('ZONA') or '').strip() in ('99','90','98'): continue
        try:
            la = float((row.get('LATITUD') or '').replace(',','.')); lo = float((row.get('LONGITUD') or '').replace(',','.'))
        except ValueError: continue
        if -5 < la < 14 and -82 < lo < -66: pts[k].append((la, lo))
        depto[k] = d

# nombre del departamento tal como lo trae DEPARTAMENTOS2.json (el mapa casa por ese nombre)
GEO_DEP = ['Amazonas','Antioquia','Arauca','Atlántico','Bolívar','Boyacá','Caldas','Caquetá','Casanare','Cauca',
  'Cesar','Chocó','Cundinamarca','Córdoba','Distrito Capital de Bogotá','Guainía','Guaviare','Huila','La Guajira',
  'Magdalena','Meta','Nariño','Norte de Santander','Putumayo','Quindío','Risaralda','San Andrés y Providencia',
  'Santander','Sucre','Tolima','Valle del Cauca','Vaupés','Vichada']
ESPECIAL = {'BOGOTA D.C.':'Distrito Capital de Bogotá','NORTE DE SAN':'Norte de Santander',
            'SAN ANDRES':'San Andrés y Providencia','VALLE':'Valle del Cauca'}
def dep_geo(d):
    if d in ESPECIAL: return ESPECIAL[d]
    for g in GEO_DEP:
        if norm(g) == d: return g
    raise SystemExit(f'departamento sin casar con el mapa: {d}')

out = []
for k, v in pts.items():
    d, m = k
    if m in FUERA: continue
    if m not in CAPITALES and censo[k] < 100000: continue
    if m in CAPITALES and m in ('ARAUCA','ARMENIA') and censo[k] < 20000: continue
    nombre = NOMBRE.get(m, m.title().replace(' De ',' de ').replace(' Del ',' del '))
    claves = ALIAS.get(m, [norm(m).lower().replace('.','')])
    out.append({'id': norm(m).lower().replace(' ','-').replace('.',''), 'nombre': nombre, 'depto': dep_geo(d),
                'claves': claves, 'lat': round(statistics.median(x[0] for x in v), 4),
                'lon': round(statistics.median(x[1] for x in v), 4), 'censo': censo[k],
                'capital': m in CAPITALES})
# un nombre repetido entre departamentos no se puede ubicar por titular: se queda el de mayor censo
vistos = {}
for c in sorted(out, key=lambda c: -c['censo']):
    for cl in c['claves']:
        vistos.setdefault(cl, c)
final = sorted({id(c): c for c in vistos.values()}.values(), key=lambda c: -c['censo'])
(Path(__file__).parent / 'ciudades.json').write_text(json.dumps(final, ensure_ascii=False, indent=0))
print(len(final), 'ciudades ·', ', '.join(c['nombre'] for c in final[:12]), '…')
