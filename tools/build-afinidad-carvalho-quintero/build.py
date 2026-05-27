#!/usr/bin/env python3
"""
build-afinidad-carvalho-quintero/build.py

Construye la huella territorial del equipo Carvalho por barrio DAP en
Medellín. Combina dos señales electorales:

  1. Daniel Carvalho Mejía · Concejo Medellín 2019 (Alianza Verde)
     Fuente: Bases de datos/FINAL SUBIDA GCS/GCS_2019TER.csv
     ~5.298 votos · candidato concejal electo en 2019

  2. Cristian Camilo Quintero Giraldo · Cámara Antioquia 2026 (AHORA COLOMBIA)
     Fuente: Bases de datos/output_declarados/CAMARA/TERRITORIAL/candidatos/
             CRISTIAN_CAMILO_QUINTERO_GIRALDO_2026-CAMARA.json
     ~10.955 votos totales · ~6.590 en Medellín · co-líder del equipo
     en la elección legislativa 2026

Output:
  Bases de datos/afinidad-carvalho-quintero/afinidad-carvalho-quintero.json
  shape:
    {
      "version": "20260527",
      "metodologia": "...",
      "totales": {
        "carvalho_2019_concejo_mde": int,
        "quintero_2026_camara_mde": int,
        "total_voto_concejo_2019_mde": int,
        "total_voto_camara_2026_mde": int
      },
      "barrios": {
        "<DAP>": {
          "nombre": "...",
          "comuna": "...",
          "votos_carvalho_2019": int,
          "votos_quintero_2026": int,
          "pct_carvalho_2019": float,
          "pct_quintero_2026": float,
          "afinidad_combo": float,        # promedio normalizado 0..1
          "afinidad_slider": float        # mapeado a escala -5..+5 para slider
        }
      }
    }

Sube a S3 con:
  aws s3 cp "Bases de datos/afinidad-carvalho-quintero/afinidad-carvalho-quintero.json" \
    "s3://elecciones-2026/ricardoruiz.co/bases de datos/Proyecto DC/afinidad-carvalho-quintero/afinidad-carvalho-quintero.json" \
    --content-type "application/json" --cache-control "public, max-age=300"
"""
import csv
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone

# --------- Paths ---------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GCS_2019_TER = os.path.join(ROOT, 'Bases de datos', 'FINAL SUBIDA GCS', 'GCS_2019TER.csv')
QUINTERO_JSON = os.path.join(
    ROOT, 'Bases de datos', 'output_declarados', 'CAMARA', 'TERRITORIAL', 'candidatos',
    'CRISTIAN_CAMILO_QUINTERO_GIRALDO_2026-CAMARA.json'
)
PUESTOS_GEOREF = os.path.join(ROOT, 'Bases de datos', 'PUESTOS_GEOREF.csv')
BARRIOS_OFICIAL = os.path.join(ROOT, 'Bases de datos', 'MEDELLIN_BARRIOS_OFICIAL.json')
OUT_DIR = os.path.join(ROOT, 'Bases de datos', 'afinidad-carvalho-quintero')
OUT_FILE = os.path.join(OUT_DIR, 'afinidad-carvalho-quintero.json')


def norm(s):
    """Normalize string: uppercase, sin acentos, sin espacios extras."""
    if not s:
        return ''
    n = unicodedata.normalize('NFD', str(s)).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'\s+', ' ', n).upper().strip()


def norm_agg(s):
    """Normalización agresiva (mismo patrón que voto-historico.html)."""
    n = norm(s)
    n = re.sub(r'#\s*(\d+)', r'\1', n)
    n = re.sub(r'\bNO\.?\s*(\d+)', r'\1', n)
    n = re.sub(r'[-.]', ' ', n)
    n = re.sub(r'\s+', ' ', n).strip()
    for p in ('CORREGIMIENTO ', 'BARRIO ', 'AREA DE EXPANSION ', 'CABECERA URBANA '):
        if n.startswith(p):
            n = n[len(p):]
    for a in ('EL ', 'LA ', 'LOS ', 'LAS '):
        if n.startswith(a) and len(n) > len(a) + 2:
            n = n[len(a):]
    return n.strip()


def pad2(s):
    """Pad to 2-char string (zones, codes)."""
    if s is None or s == '':
        return ''
    try:
        return str(int(s)).zfill(2)
    except (ValueError, TypeError):
        return str(s).zfill(2)


# --------- 1. Mapa puesto → barrio + comuna desde PUESTOS_GEOREF ---------
print(f'[1] Loading PUESTOS_GEOREF ({PUESTOS_GEOREF})...', file=sys.stderr)
puesto_meta = {}  # (zona_2c, puesto_2c) -> { barrio, comuna_cod, comuna_nom, mesas }

# El CSV viene con encoding UTF-8 BOM y separador ;
with open(PUESTOS_GEOREF, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        if (row.get('DEPARTAMENTO') or '').strip().upper() != 'ANTIOQUIA':
            continue
        if (row.get('MUNICIPIO') or '').strip().upper() != 'MEDELLIN':
            continue
        zona = pad2(row.get('ZONA'))
        puesto = pad2(row.get('PUESTO'))
        barrio = (row.get('BARRIO') or '').strip()
        comuna_cod = (row.get('CÓDIGO COMUNA') or '').strip()
        comuna_nom = (row.get('NOMBRE COMUNA') or '').strip()
        # Mujeres + Hombres = censo aprox del puesto
        try:
            mujeres = int(row.get('MUJERES') or 0)
        except ValueError:
            mujeres = 0
        try:
            hombres = int(row.get('HOMBRES') or 0)
        except ValueError:
            hombres = 0
        try:
            mesas = int(row.get('MESAS') or 0)
        except ValueError:
            mesas = 0
        puesto_meta[(zona, puesto)] = {
            'barrio': barrio,
            'barrio_norm': norm(barrio),
            'barrio_agg': norm_agg(barrio),
            'comuna_cod': comuna_cod,
            'comuna_nom': comuna_nom,
            'censo_aprox': mujeres + hombres,
            'mesas': mesas,
        }
print(f'  puestos Medellín indexados: {len(puesto_meta)}', file=sys.stderr)


# --------- 2. Mapa barrio → DAP desde MEDELLIN_BARRIOS_OFICIAL ---------
print(f'[2] Loading MEDELLIN_BARRIOS_OFICIAL...', file=sys.stderr)
with open(BARRIOS_OFICIAL, 'r', encoding='utf-8') as f:
    barrios_geo = json.load(f)

# Construir índice por nombre normalizado + comuna (key compuesto)
barrio_by_name = {}     # NOMBRE_NORM -> { CODIGO, NOMBRE, COMUNA }
barrio_by_agg = {}      # NOMBRE_AGG  -> idem
barrio_by_code = {}     # CODIGO     -> { NOMBRE, COMUNA }

for feat in barrios_geo.get('features', []):
    props = feat.get('properties') or {}
    codigo = props.get('CODIGO')
    nombre = props.get('NOMBRE')
    comuna = props.get('COMUNA')
    if not codigo:
        continue
    entry = {'codigo': codigo, 'nombre': nombre, 'comuna': comuna}
    barrio_by_code[codigo] = entry
    if nombre:
        barrio_by_name[norm(nombre)] = entry
        barrio_by_agg[norm_agg(nombre)] = entry

# Aliases manuales que aparecen en PUESTOS_GEOREF pero con grafía distinta al DAP oficial.
# Se llenan reactivamente abajo si faltan.
print(f'  features GeoJSON: {len(barrios_geo.get("features", []))}', file=sys.stderr)
print(f'  índice por nombre normalizado: {len(barrio_by_name)}', file=sys.stderr)


def resolve_barrio_dap(barrio_norm, barrio_agg):
    """Resuelve nombre de barrio del PUESTOS_GEOREF a CODIGO DAP del GeoJSON."""
    if barrio_norm in barrio_by_name:
        return barrio_by_name[barrio_norm]
    if barrio_agg in barrio_by_agg:
        return barrio_by_agg[barrio_agg]
    return None


# --------- 3. Votos Quintero 2026 por puesto (Medellín) ---------
print(f'[3] Loading Quintero 2026 Cámara JSON...', file=sys.stderr)
with open(QUINTERO_JSON, 'r', encoding='utf-8') as f:
    quintero = json.load(f)

quintero_por_puesto = defaultdict(int)
quintero_total_mde = 0
for m in quintero.get('mesas', []):
    if m.get('dep') != '01' or m.get('mun') != '001':
        continue
    z = pad2(m.get('zon'))
    p = pad2(m.get('pue'))
    v = int(m.get('v') or 0)
    quintero_por_puesto[(z, p)] += v
    quintero_total_mde += v
print(f'  votos Quintero Medellín: {quintero_total_mde:,} en {len(quintero_por_puesto)} puestos', file=sys.stderr)


# --------- 4. Votos Carvalho 2019 Concejo Medellín por puesto ---------
print(f'[4] Streaming GCS_2019TER.csv para Carvalho...', file=sys.stderr)
carvalho_por_puesto = defaultdict(int)
carvalho_total_mde = 0
total_concejo_mde_por_puesto = defaultdict(int)  # denominador

with open(GCS_2019_TER, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        # Solo Concejo Medellín (depto=1, mun=1)
        if row.get('COD_DDE') != '1' or row.get('COD_MME') != '1':
            continue
        # CONCEJO o ALCALDIA/ALCALDE etc — solo concejo aquí
        des_cor = (row.get('DES_COR') or '').strip().upper()
        if des_cor != 'CONCEJO':
            continue
        # COD_CAN especiales 996/997/998/999 excluidos
        try:
            cod_can = int(row.get('COD_CAN') or 0)
        except ValueError:
            cod_can = 0
        if cod_can >= 996:
            continue
        try:
            votos = int(row.get('NUM_VOT') or 0)
        except ValueError:
            votos = 0
        z = pad2(row.get('COD_ZZ'))
        p = pad2(row.get('COD_PP'))
        total_concejo_mde_por_puesto[(z, p)] += votos
        nombre_can = (row.get('DES_CAN') or '').strip().upper()
        if nombre_can == 'DANIEL CARVALHO MEJIA':
            carvalho_por_puesto[(z, p)] += votos
            carvalho_total_mde += votos

print(f'  votos Carvalho Concejo MDE 2019: {carvalho_total_mde:,} en {len(carvalho_por_puesto)} puestos', file=sys.stderr)
print(f'  total Concejo MDE 2019 (denominador): {sum(total_concejo_mde_por_puesto.values()):,}', file=sys.stderr)


# --------- 5. Total Cámara Antioquia 2026 por puesto (denominador Quintero) ---------
# Para tener pct correcto necesitamos cuántos votaron en Cámara desde cada puesto MDE.
# El JSON de Quintero solo trae sus mesas, así que para denominador agregamos por puesto el censo aprox.
# Alternativa: leer otro candidato cualquiera de Cámara Antioquia (todos comparten universo de mesas).
# Por simplicidad y honestidad, usamos el censo aprox del puesto como base.
total_camara_aprox_por_puesto = {k: v.get('censo_aprox', 0) for k, v in puesto_meta.items()}
# Aproximación: participación típica 50% del censo en Cámara Antioquia 2026
PARTIC_CAMARA = 0.50
total_camara_aprox_por_puesto = {k: int(v * PARTIC_CAMARA) for k, v in total_camara_aprox_por_puesto.items()}


# --------- 6. Agregación por barrio DAP ---------
print(f'[5] Agregando por barrio DAP...', file=sys.stderr)
# Acumulador por DAP
barrios_acc = defaultdict(lambda: {
    'votos_carvalho_2019': 0,
    'votos_quintero_2026': 0,
    'denom_concejo_2019': 0,
    'denom_camara_2026': 0,
    'puestos': 0,
    'sin_match': 0,
})
sin_match_log = []  # puestos sin barrio resoluble

# Union de claves para iterar todos los puestos visitados
all_puestos = set(carvalho_por_puesto.keys()) | set(quintero_por_puesto.keys()) | set(puesto_meta.keys())
for (z, p) in all_puestos:
    meta = puesto_meta.get((z, p))
    if not meta:
        # Puesto que aparece en GCS pero no en PUESTOS_GEOREF — probablemente zona especial.
        sin_match_log.append((z, p, 'no en PUESTOS_GEOREF'))
        continue
    dap_entry = resolve_barrio_dap(meta['barrio_norm'], meta['barrio_agg'])
    if not dap_entry:
        sin_match_log.append((z, p, meta['barrio']))
        continue
    dap = dap_entry['codigo']
    acc = barrios_acc[dap]
    acc['votos_carvalho_2019'] += carvalho_por_puesto.get((z, p), 0)
    acc['votos_quintero_2026'] += quintero_por_puesto.get((z, p), 0)
    acc['denom_concejo_2019'] += total_concejo_mde_por_puesto.get((z, p), 0)
    acc['denom_camara_2026'] += total_camara_aprox_por_puesto.get((z, p), 0)
    acc['puestos'] += 1

print(f'  barrios con datos: {len(barrios_acc)}', file=sys.stderr)
print(f'  puestos sin match: {len(sin_match_log)} (zona/corr especiales o nombres no DAP)', file=sys.stderr)

# Calcular pct y afinidad por barrio
out_barrios = {}
for dap, acc in barrios_acc.items():
    entry = barrio_by_code[dap]
    vc = acc['votos_carvalho_2019']
    vq = acc['votos_quintero_2026']
    dc = acc['denom_concejo_2019']
    dq = acc['denom_camara_2026']
    pct_c = (vc / dc * 100) if dc > 0 else 0.0
    pct_q = (vq / dq * 100) if dq > 0 else 0.0

    # afinidad_combo: promedio ponderado en [0, 1]
    # Carvalho 5.298 / Concejo total ~720k → ~0.7% promedio · barrios altos ~3%
    # Quintero 6.590 / Cámara total ~720k × 0.5 = ~360k → ~1.8% promedio · barrios altos ~6%
    # Normalizamos cada uno por percentil 95 implícito (3% y 6%) y promediamos.
    NORM_CARVALHO = 3.0
    NORM_QUINTERO = 6.0
    norm_c = min(pct_c / NORM_CARVALHO, 1.0)
    norm_q = min(pct_q / NORM_QUINTERO, 1.0)
    afinidad_combo = (norm_c + norm_q) / 2.0  # 0..1

    # afinidad_slider: re-escalado a -5..+5 con 0 = ausencia (afinidad ≈ 0.1)
    # Para que la mayoría de barrios queden en rango -3..+3 y los pocos
    # bastiones del equipo en +4..+5.
    afinidad_slider = round((afinidad_combo - 0.10) * 10, 2)  # -1..+9, clamp a [-5,5]
    afinidad_slider = max(-5.0, min(5.0, afinidad_slider))

    out_barrios[dap] = {
        'nombre': entry['nombre'],
        'comuna': entry['comuna'],
        'votos_carvalho_2019': vc,
        'votos_quintero_2026': vq,
        'pct_carvalho_2019': round(pct_c, 4),
        'pct_quintero_2026': round(pct_q, 4),
        'afinidad_combo': round(afinidad_combo, 4),
        'afinidad_slider': afinidad_slider,
        'puestos': acc['puestos'],
    }


# --------- 7. Escribir output ---------
os.makedirs(OUT_DIR, exist_ok=True)
out = {
    'version': datetime.now(timezone.utc).strftime('%Y%m%d'),
    'metodologia': (
        'Huella territorial del equipo Carvalho por barrio DAP. Combina '
        '(1) Daniel Carvalho Mejía en Concejo Medellín 2019 (Alianza Verde, '
        '5.298 votos) y (2) Cristian Camilo Quintero Giraldo en Cámara '
        'Antioquia 2026 (AHORA COLOMBIA, ~6.590 votos en Medellín). Se '
        'cruzan votos por puesto contra PUESTOS_GEOREF.csv para obtener '
        'el barrio DAP de cada voto. pct_carvalho_2019 = votos/total '
        'Concejo MDE en ese puesto; pct_quintero_2026 = votos/censo_aprox '
        'del puesto × 0.5 (participación estimada Cámara 2026). '
        'afinidad_combo promedia ambos pct normalizados por percentil 95 '
        '(3% Carvalho, 6% Quintero). afinidad_slider re-escala a -5..+5 '
        'para uso directo en el simulador del módulo 08.'
    ),
    'totales': {
        'carvalho_2019_concejo_mde': carvalho_total_mde,
        'quintero_2026_camara_mde': quintero_total_mde,
        'total_concejo_2019_mde': sum(total_concejo_mde_por_puesto.values()),
        'total_camara_aprox_2026_mde': sum(total_camara_aprox_por_puesto.values()),
        'puestos_indexados': len(puesto_meta),
        'puestos_sin_match': len(sin_match_log),
        'barrios_con_datos': len(out_barrios),
    },
    'barrios': out_barrios,
}
with open(OUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f'\n✓ Escrito: {OUT_FILE}', file=sys.stderr)
print(f'  ({os.path.getsize(OUT_FILE):,} bytes · {len(out_barrios)} barrios)', file=sys.stderr)

# Pequeño dump de top-10 por afinidad
print('\nTop 10 barrios por afinidad_combo:', file=sys.stderr)
top = sorted(out_barrios.items(), key=lambda kv: kv[1]['afinidad_combo'], reverse=True)[:10]
for dap, b in top:
    print(f"  {dap} {b['nombre']:35} {b['comuna']:25} "
          f"carv={b['pct_carvalho_2019']:.2f}% quint={b['pct_quintero_2026']:.2f}% "
          f"afin={b['afinidad_combo']:.3f} slider={b['afinidad_slider']:+.2f}",
          file=sys.stderr)
