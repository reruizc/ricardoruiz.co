#!/usr/bin/env python3
"""
Genera los JSON de resultados definitivos de Consultas Presidenciales 2026.

Fuente: output_declarados/CONSULTAS/NACIONAL/candidatos/*.json
Salida:
  output_agregados/consultas/resumen.json   — totales nacionales por consulta
  output_agregados/consultas/deps.json      — totales por departamento por consulta

Uso: python3 generar_consultas.py
"""

import json, glob, os
from collections import defaultdict

BASE   = os.path.dirname(os.path.abspath(__file__))
INPUT  = os.path.join(BASE, 'output_declarados', 'CONSULTAS', 'NACIONAL', 'candidatos')
OUTPUT = os.path.join(BASE, 'output_agregados', 'consultas')
os.makedirs(OUTPUT, exist_ok=True)

# ── Mapeo partido → clave interna ───────────────────────────────────────────
CLAVE = {
    'LA GRAN CONSULTA POR COLOMBIA':                                     'gran',
    'FRENTE POR LA VIDA':                                                'frente',
    'CONSULTA DE LAS SOLUCIONES: SALUD, SEGURIDAD Y EDUCACIÓN':          'soluciones',
}

NOMBRES_CONSULTA = {
    'gran':       'La Gran Consulta por Colombia',
    'frente':     'Frente por la Vida',
    'soluciones': 'Consulta de Soluciones',
}

# Nombre largo para mostrar en UI
NOMBRES_LARGO = {
    'gran':       'La Gran Consulta por Colombia',
    'frente':     'Frente por la Vida',
    'soluciones': 'Consulta de Soluciones: Salud, Seguridad y Educación',
}

# Nombres de deps corregidos (algunos están truncados en los JSONs)
DEP_NOMBRES = {
    '01': 'Antioquia',       '03': 'Atlántico',         '05': 'Bolívar',
    '07': 'Boyacá',          '09': 'Caldas',             '11': 'Cauca',
    '12': 'Cesar',           '13': 'Córdoba',            '15': 'Cundinamarca',
    '16': 'Bogotá D.C.',     '17': 'Chocó',              '19': 'Huila',
    '21': 'Magdalena',       '23': 'Nariño',             '24': 'Risaralda',
    '25': 'Norte de Santander','26': 'Quindío',          '27': 'Santander',
    '28': 'Sucre',           '29': 'Tolima',             '31': 'Valle del Cauca',
    '40': 'Arauca',          '44': 'Caquetá',            '46': 'Casanare',
    '48': 'La Guajira',      '50': 'Guainía',            '52': 'Meta',
    '54': 'Guaviare',        '56': 'San Andrés',         '60': 'Amazonas',
    '64': 'Putumayo',        '68': 'Vaupés',             '72': 'Vichada',
    '88': 'Circunscripción Exterior',
}

def title_name(s):
    """Convierte 'NOMBRE APELLIDO' → 'Nombre Apellido'."""
    return ' '.join(w.capitalize() for w in s.strip().split())

# ── Acumuladores ─────────────────────────────────────────────────────────────
# nacional[clave] = {partido, candidatos: [{nombre, votos, codigo}]}
nacional = {}
# dep_data[dep_cod][clave] = {cands: {nombre → votos}}
dep_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
dep_cands_meta = defaultdict(dict)  # dep_cod → {nombre: {codigo, partido}}

files = sorted(glob.glob(os.path.join(INPUT, '*.json')))
print(f'Procesando {len(files)} candidatos...')

for fpath in files:
    with open(fpath, encoding='utf-8') as f:
        d = json.load(f)

    partido_raw  = d.get('partido', '')
    clave        = None
    for k, v in CLAVE.items():
        if k.upper() in partido_raw.upper():
            clave = v
            break
    if not clave:
        print(f'  ⚠ Partido no reconocido: {partido_raw}')
        continue

    nombre_raw   = d.get('nombre', '')
    nombre       = title_name(nombre_raw)
    codigo       = d.get('candidatoCodigo', '')
    votos_nac    = d.get('votos', 0)

    if clave not in nacional:
        nacional[clave] = {
            'clave':    clave,
            'nombre':   NOMBRES_CONSULTA[clave],
            'nombre_largo': NOMBRES_LARGO[clave],
            'votos':    0,
            'candidatos': [],
        }

    nacional[clave]['votos'] += votos_nac
    nacional[clave]['candidatos'].append({
        'nombre':  nombre,
        'partido': NOMBRES_LARGO[clave],
        'votos':   votos_nac,
        'codigo':  codigo,
    })

    # Agregar por dep
    for mesa in d.get('mesas', []):
        dep_cod = mesa.get('dep', '')
        v       = mesa.get('v', 0)
        if not dep_cod or not v:
            continue
        dep_data[dep_cod][clave][nombre] += v
        if nombre not in dep_cands_meta[dep_cod]:
            dep_cands_meta[dep_cod][nombre] = {'codigo': codigo, 'partido': NOMBRES_LARGO[clave], 'clave': clave}

# Ordenar candidatos por votos (desc)
for clave, data in nacional.items():
    data['candidatos'].sort(key=lambda c: -c['votos'])
    print(f"  {data['nombre']}: {data['votos']:,} votos · {len(data['candidatos'])} candidatos")
    for c in data['candidatos']:
        print(f"    {c['nombre']}: {c['votos']:,}")

# ── resumen.json ─────────────────────────────────────────────────────────────
# Orden canónico de consultas
ORDER = ['gran', 'frente', 'soluciones']
resumen = {
    'consultas': [nacional[k] for k in ORDER if k in nacional],
    'fecha': '2026-04-13',
    'fuente': 'Resultados Definitivos · Registraduría Nacional',
}

out_resumen = os.path.join(OUTPUT, 'resumen.json')
with open(out_resumen, 'w', encoding='utf-8') as f:
    json.dump(resumen, f, ensure_ascii=False, separators=(',', ':'))
print(f'\nresumen.json → {os.path.getsize(out_resumen)/1024:.0f} KB')

# ── deps.json ────────────────────────────────────────────────────────────────
deps_list = []
for dep_cod in sorted(dep_data.keys()):
    dep_nom = DEP_NOMBRES.get(dep_cod, dep_cod)
    dep_obj = {'cod': dep_cod, 'nombre': dep_nom}
    for clave in ORDER:
        if clave not in dep_data[dep_cod]:
            continue
        cands_dict = dep_data[dep_cod][clave]
        cands = []
        for nombre, votos in sorted(cands_dict.items(), key=lambda x: -x[1]):
            meta = dep_cands_meta[dep_cod].get(nombre, {})
            cands.append({'nombre': nombre, 'votos': votos, 'codigo': meta.get('codigo','')})
        dep_obj[clave] = {
            'votos': sum(c['votos'] for c in cands),
            'candidatos': cands,
        }
    deps_list.append(dep_obj)

out_deps = os.path.join(OUTPUT, 'deps.json')
with open(out_deps, 'w', encoding='utf-8') as f:
    json.dump(deps_list, f, ensure_ascii=False, separators=(',', ':'))
print(f'deps.json → {os.path.getsize(out_deps)/1024:.0f} KB')
print(f'\nListo. Sube a S3: consultas/resumen.json + consultas/deps.json')
