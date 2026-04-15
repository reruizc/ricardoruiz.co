#!/usr/bin/env python3
"""
Genera archivos JSON por departamento para Consultas Presidenciales 2026
con jerarquía completa: dep → municipio → zona → puesto → mesa.

Fuente:  output_declarados/CONSULTAS/NACIONAL/candidatos/*.json
Aux:     output_agregados/camara/dep-*.json  (para nombres de zonas)
Salida:  output_agregados/consultas/dep-{cod}.json  (uno por dep)
         Actualiza también resumen.json y deps.json

Uso: python3 generar_consultas_deps.py
"""

import json, glob, os, math
from collections import defaultdict

BASE      = os.path.dirname(os.path.abspath(__file__))
INPUT     = os.path.join(BASE, 'output_declarados', 'CONSULTAS', 'NACIONAL', 'candidatos')
CAMARA    = os.path.join(BASE, 'output_agregados', 'camara')
OUTPUT    = os.path.join(BASE, 'output_agregados', 'consultas')
os.makedirs(OUTPUT, exist_ok=True)

# ── Mapeo partido → clave ────────────────────────────────────────────────────
CLAVE = {
    'LA GRAN CONSULTA POR COLOMBIA':                                    'gran',
    'FRENTE POR LA VIDA':                                               'frente',
    'CONSULTA DE LAS SOLUCIONES: SALUD, SEGURIDAD Y EDUCACIÓN':         'soluciones',
}
ORDER = ['gran', 'frente', 'soluciones']
NOMBRE_CONSULTA = {
    'gran':       'La Gran Consulta por Colombia',
    'frente':     'Frente por la Vida',
    'soluciones': 'Consulta de Soluciones',
}
NOMBRE_LARGO = {
    'gran':       'La Gran Consulta por Colombia',
    'frente':     'Frente por la Vida',
    'soluciones': 'Consulta de Soluciones: Salud, Seguridad y Educación',
}
DEP_NOMBRES = {
    '01':'Antioquia','03':'Atlántico','05':'Bolívar','07':'Boyacá','09':'Caldas',
    '11':'Cauca','12':'Cesar','13':'Córdoba','15':'Cundinamarca','16':'Bogotá D.C.',
    '17':'Chocó','19':'Huila','21':'Magdalena','23':'Nariño','24':'Risaralda',
    '25':'Norte de Santander','26':'Quindío','27':'Santander','28':'Sucre',
    '29':'Tolima','31':'Valle del Cauca','40':'Arauca','44':'Caquetá',
    '46':'Casanare','48':'La Guajira','50':'Guainía','52':'Meta','54':'Guaviare',
    '56':'San Andrés','60':'Amazonas','64':'Putumayo','68':'Vaupés','72':'Vichada',
    '88':'Circunscripción Exterior',
}

def title_name(s):
    return ' '.join(w.capitalize() for w in s.strip().split())

def mb(path):
    return os.path.getsize(path) / 1024 / 1024

# ── Cargar nombres de zonas desde archivos de cámara ────────────────────────
# Clave: dep_cod → {mun_cod+'_'+zon_cod → nombre}
print('Cargando nombres de zonas desde camara...')
zone_names = {}
for fpath in glob.glob(os.path.join(CAMARA, 'dep-*.json')):
    dep_cod = os.path.basename(fpath).replace('dep-','').replace('.json','')
    try:
        with open(fpath) as f:
            d = json.load(f)
    except Exception:
        continue
    dep_zones = {}
    for mun in d.get('municipios', []):
        mun_cod = mun.get('cod', '')
        areas_key = 'comunas' if 'comunas' in mun else 'zonas'
        for a in mun.get(areas_key, []):
            dep_zones[mun_cod + '_' + a['cod']] = a['nombre']
    zone_names[dep_cod] = dep_zones
print(f'  {len(zone_names)} deps con nombres de zonas')

def get_zone_name(dep_cod, mun_cod, zon_cod):
    """Obtiene el nombre de zona del archivo de cámara; fallback a 'Zona XX'."""
    zon_padded = zon_cod.zfill(3)
    dz = zone_names.get(dep_cod, {})
    name = dz.get(mun_cod + '_' + zon_padded)
    if name and name.upper() not in ('SIN COMUNA', 'NACIONAL'):
        return name.title()
    if zon_padded == '000':
        return 'Zona Centro'
    if zon_padded == '099':
        return 'Zona Rural / Exterior'
    if zon_padded == '098':
        return 'Zona Especial'
    if zon_padded == '090':
        return 'Zona Corregimientos'
    return f'Zona {zon_cod.zfill(2)}'

# ── Leer todos los candidatos ────────────────────────────────────────────────
# Estructura: dep_cod → mun_cod → zon_cod → pue_cod →
#   {mesas: {mesa_cod → {clave → {nombre_cand: votos}}},
#    pue_nombre: str}
print('Leyendo candidatos...')

# Global accumulators
all_data = {}  # dep → mun → zon → pue → {mesas, pue_nom, mun_nom, dep_nom}
nac_votos = defaultdict(lambda: defaultdict(int))   # clave → nombre_cand → votos
nac_codigo = {}   # nombre_cand → codigo

files = sorted(glob.glob(os.path.join(INPUT, '*.json')))
print(f'  {len(files)} archivos de candidatos')

for fpath in files:
    with open(fpath) as f:
        d = json.load(f)

    partido_raw = d.get('partido', '')
    clave = None
    for k, v in CLAVE.items():
        if k.upper() in partido_raw.upper():
            clave = v
            break
    if not clave:
        print(f'  ⚠ Partido no reconocido: {partido_raw}')
        continue

    nombre = title_name(d.get('nombre', ''))
    codigo = d.get('candidatoCodigo', '')
    nac_codigo[nombre] = codigo

    for mesa in d.get('mesas', []):
        v = mesa.get('v', 0)
        if not v:
            continue
        dep = mesa.get('dep', '')
        mun = mesa.get('mun', '')
        zon = mesa.get('zon', '00')
        pue = mesa.get('pue', '00')
        pue_nom = mesa.get('pueNom', '')
        mun_nom = mesa.get('munNom', '')
        dep_nom = mesa.get('depNom', '')
        mesa_cod = mesa.get('mesa', '')

        nac_votos[clave][nombre] += v

        if dep not in all_data: all_data[dep] = {'dep_nom': dep_nom}
        dep_d = all_data[dep]
        if 'muns' not in dep_d: dep_d['muns'] = {}
        if mun not in dep_d['muns']: dep_d['muns'][mun] = {'nom': mun_nom, 'zons': {}}
        mun_d = dep_d['muns'][mun]
        if zon not in mun_d['zons']: mun_d['zons'][zon] = {'pues': {}}
        zon_d = mun_d['zons'][zon]
        if pue not in zon_d['pues']: zon_d['pues'][pue] = {'nom': pue_nom, 'mesas': {}}
        pue_d = zon_d['pues'][pue]
        if mesa_cod not in pue_d['mesas']: pue_d['mesas'][mesa_cod] = {}
        mesa_d = pue_d['mesas'][mesa_cod]
        if clave not in mesa_d: mesa_d[clave] = {}
        mesa_d[clave][nombre] = mesa_d[clave].get(nombre, 0) + v

print(f'  Deps encontrados: {sorted(all_data.keys())}')

# ── Helper: agregar votos de mesas a nivel superior ──────────────────────────
def agg_votos(mesas_dict):
    """Suma votos de un dict {mesa_cod: {clave: {nombre: votos}}} → {clave: {nombre: votos}}."""
    agg = defaultdict(lambda: defaultdict(int))
    for mesa_d in mesas_dict.values():
        for clave, cands in mesa_d.items():
            for nombre, v in cands.items():
                agg[clave][nombre] += v
    return {k: dict(v) for k, v in agg.items()}

def agg_from_pues(pues_dict):
    agg = defaultdict(lambda: defaultdict(int))
    for pue_d in pues_dict.values():
        for clave, cands in agg_votos(pue_d['mesas']).items():
            for nombre, v in cands.items():
                agg[clave][nombre] += v
    return {k: dict(v) for k, v in agg.items()}

def agg_from_zons(zons_dict):
    agg = defaultdict(lambda: defaultdict(int))
    for zon_d in zons_dict.values():
        for clave, cands in agg_from_pues(zon_d['pues']).items():
            for nombre, v in cands.items():
                agg[clave][nombre] += v
    return {k: dict(v) for k, v in agg.items()}

def votos_obj(vdict):
    """Convierte {clave: {nombre: votos}} → {clave: {votos: N, cands: [{nombre, votos}]}}"""
    out = {}
    for clave in ORDER:
        cands_raw = vdict.get(clave, {})
        cands = sorted([{'nombre': n, 'votos': v} for n, v in cands_raw.items()],
                       key=lambda x: -x['votos'])
        out[clave] = {'votos': sum(c['votos'] for c in cands), 'cands': cands}
    return out

# ── Generar dep-{cod}.json ────────────────────────────────────────────────────
print('\nGenerando archivos por dep...')
deps_index = []  # para deps.json ligero

for dep_cod in sorted(all_data.keys()):
    dep_d   = all_data[dep_cod]
    dep_nom = DEP_NOMBRES.get(dep_cod, dep_d['dep_nom'])

    zons_agg = agg_from_zons({
        zon: zd for mun_d in dep_d['muns'].values()
             for zon, zd in mun_d['zons'].items()
    })
    dep_votos = votos_obj(zons_agg)

    municipios = []
    for mun_cod in sorted(dep_d['muns'].keys()):
        mun_d   = dep_d['muns'][mun_cod]
        mun_nom = mun_d['nom']
        mun_agg = agg_from_zons(mun_d['zons'])
        mun_votos = votos_obj(mun_agg)

        zonas = []
        for zon_cod in sorted(mun_d['zons'].keys()):
            zon_d   = mun_d['zons'][zon_cod]
            zon_nom = get_zone_name(dep_cod, mun_cod, zon_cod)
            zon_agg = agg_from_pues(zon_d['pues'])
            zon_votos = votos_obj(zon_agg)

            puestos = []
            for pue_cod in sorted(zon_d['pues'].keys()):
                pue_d   = zon_d['pues'][pue_cod]
                pue_agg = agg_votos(pue_d['mesas'])
                pue_votos = votos_obj(pue_agg)

                mesas = []
                for mesa_cod in sorted(pue_d['mesas'].keys()):
                    mesa_entry = {'mesa': mesa_cod}
                    for cl in ORDER:
                        cands_raw = pue_d['mesas'][mesa_cod].get(cl, {})
                        if cands_raw:
                            mesa_entry[cl] = cands_raw
                    mesas.append(mesa_entry)

                puestos.append({
                    'cod': pue_cod,
                    'nombre': pue_d['nom'],
                    **pue_votos,
                    'mesas': mesas,
                })

            zonas.append({
                'cod': zon_cod,
                'nombre': zon_nom,
                **zon_votos,
                'puestos': puestos,
            })

        municipios.append({
            'cod': mun_cod,
            'nombre': mun_nom,
            **mun_votos,
            'zonas': zonas,
        })

    dep_obj = {
        'cod': dep_cod,
        'nombre': dep_nom,
        **dep_votos,
        'municipios': municipios,
    }

    out_path = os.path.join(OUTPUT, f'dep-{dep_cod}.json')
    raw = json.dumps(dep_obj, ensure_ascii=False, separators=(',', ':'))
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(raw)
    size = mb(out_path)
    mun_count = len(municipios)
    print(f'  dep-{dep_cod}.json ({dep_nom}): {size:.1f} MB · {mun_count} muns')

    # Entrada ligera para deps.json
    dep_entry = {'cod': dep_cod, 'nombre': dep_nom}
    for cl in ORDER:
        dep_entry[cl] = {
            'votos': dep_votos[cl]['votos'],
            'candidatos': [{'nombre': c['nombre'], 'votos': c['votos'], 'codigo': nac_codigo.get(c['nombre'],'')}
                           for c in dep_votos[cl]['cands']],
        }
    deps_index.append(dep_entry)

# ── Actualizar deps.json ─────────────────────────────────────────────────────
out_deps = os.path.join(OUTPUT, 'deps.json')
with open(out_deps, 'w', encoding='utf-8') as f:
    json.dump(deps_index, f, ensure_ascii=False, separators=(',', ':'))
print(f'\ndeps.json actualizado → {mb(out_deps):.0f} KB')

# ── Actualizar resumen.json ──────────────────────────────────────────────────
nac_consultas = []
for cl in ORDER:
    cands = sorted([{'nombre': n, 'votos': v, 'codigo': nac_codigo.get(n,''), 'partido': NOMBRE_LARGO[cl]}
                    for n, v in nac_votos[cl].items()], key=lambda x: -x['votos'])
    nac_consultas.append({
        'clave': cl,
        'nombre': NOMBRE_CONSULTA[cl],
        'nombre_largo': NOMBRE_LARGO[cl],
        'votos': sum(c['votos'] for c in cands),
        'candidatos': cands,
    })
resumen = {'consultas': nac_consultas, 'fecha': '2026-04-13',
           'fuente': 'Resultados Definitivos · Registraduría Nacional'}
out_res = os.path.join(OUTPUT, 'resumen.json')
with open(out_res, 'w', encoding='utf-8') as f:
    json.dump(resumen, f, ensure_ascii=False, separators=(',', ':'))
print(f'resumen.json actualizado → {mb(out_res):.0f} KB')
print('\nListo. Sube a S3:')
print('  consultas/resumen.json')
print('  consultas/deps.json')
print('  consultas/dep-{cod}.json  (34 archivos)')
