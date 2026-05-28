#!/usr/bin/env python3
"""
build-votacion-arquetipo-2027/build.py

Procesa "VOTACIÓN ESPERADA POR ARQUETIPO 2027.xlsx" (entrega de Nury,
versión definitiva 2027) y produce un JSON por barrio DAP con:

  - votos base 2023
  - votos esperados 2027 (suma de los 5 arquetipos del xlsx)
  - factor de crecimiento 2027/2023
  - arquetipo 2023 (familia base, espejo del módulo 05)
  - arquetipo proyectado 2027 (modelo tendencial)
  - **arquetipo ajustado 2027** ← versión definitiva que la clienta consolidó
  - arquetipo alterno 2027
  - probabilidad proyectado y alterno
  - riesgo de cambio
  - votos esperados por cada uno de los 5 arquetipos

Output:
  Bases de datos/proyecto-dc/votacion-arquetipo-2027/votacion-2027.json

Sube a S3 bajo Proyecto DC para que módulos 05 y 08 consuman.

ENTRADA: /Users/ricardoruiz/ricardoruiz.co/proyecto-dc/Actualizacion-2027/
         VOTACIÓN ESPERADA POR ARQUETIPO 2027.xlsx
"""
import json
import math
import os
import sys
import warnings
from datetime import datetime, timezone

warnings.filterwarnings('ignore')

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
XLSX = os.path.join(ROOT, 'proyecto-dc', 'Actualizacion-2027', 'VOTACIÓN ESPERADA POR ARQUETIPO 2027.xlsx')
OUT_DIR = os.path.join(ROOT, 'Bases de datos', 'proyecto-dc', 'votacion-arquetipo-2027')
OUT_FILE = os.path.join(OUT_DIR, 'votacion-2027.json')

# Mapeo nombres de arquetipo (texto en xlsx) → slug interno
SLUG_BY_NAME = {
    # versión base 2023 (label_corto del paquete arquetipos del módulo 05)
    'Protección y orden cotidiano':                'proteccion',
    'Estabilidad y continuidad':                   'continuidad',
    'Supervivencia económica y servicios básicos': 'supervivencia',
    'Desconfianza y castigo':                      'castigo',
    'Pertenencia y dignidad territorial':          'pertenencia',
    # versión evol 2027 (label_corto del paquete arquetipos del módulo 05)
    'Protección con resultados y orden competente':       'proteccion',
    'Castigo a la restauración y demanda de alternancia': 'castigo',
    'Continuidad pragmática y gestión barrial':           'continuidad',
    'Supervivencia económica y servicios cotidianos':     'supervivencia',
    'Pertenencia comunitaria y autonomía territorial':    'pertenencia',
}

def to_slug(name):
    if name is None:
        return None
    s = str(name).strip()
    return SLUG_BY_NAME.get(s)

def _r2(x, n=2):
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return None
        return round(float(x), n)
    except (TypeError, ValueError):
        return None

def _ri(x):
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return None
        return int(round(float(x)))
    except (TypeError, ValueError):
        return None

def main():
    import pandas as pd
    print(f'[1] Leyendo {XLSX}', file=sys.stderr)
    df = pd.read_excel(XLSX, sheet_name=0)
    df = df.dropna(subset=['Código DAP'])
    print(f'   {len(df)} barrios DAP', file=sys.stderr)

    out_barrios = {}
    diff_count = 0  # cuántos barrios tienen ajustado != proyectado

    for _, row in df.iterrows():
        dap = str(row['Código DAP']).strip()
        # Si DAP viene como float (e.g. 413.0) o int, normalizar
        if dap.endswith('.0'):
            dap = dap[:-2]
        # Pad a 4 dígitos si es necesario
        try:
            dap = str(int(dap)).zfill(4)
        except ValueError:
            pass

        votos_arq = {
            'proteccion':    _r2(row['Votos esperados · Protección con resultados y orden competente']),
            'castigo':       _r2(row['Votos esperados · Castigo a la restauración y demanda de alternancia']),
            'continuidad':   _r2(row['Votos esperados · Continuidad pragmática y gestión barrial']),
            'supervivencia': _r2(row['Votos esperados · Supervivencia económica y servicios cotidianos']),
            'pertenencia':   _r2(row['Votos esperados · Pertenencia comunitaria y autonomía territorial']),
        }
        votos_2027_total = sum(v for v in votos_arq.values() if v is not None)
        votos_base_2023  = _ri(row['Votos base 2023'])
        factor = (votos_2027_total / votos_base_2023) if (votos_base_2023 and votos_2027_total) else None

        slug_proy   = to_slug(row['Arquetipo proyectado 2027'])
        slug_ajust  = to_slug(row['Arquetipo ajustado 2027'])
        slug_alt    = to_slug(row['Arquetipo alterno 2027'])
        slug_base23 = to_slug(row['Arquetipo 2023'])

        if slug_proy != slug_ajust:
            diff_count += 1

        out_barrios[dap] = {
            'barrio': str(row['Barrio']).strip(),
            'comuna': str(row['Comuna']).strip(),
            'votos_base_2023':           votos_base_2023,
            'votos_2027':                _ri(votos_2027_total),
            'factor_crecimiento':        _r2(factor, 4),
            'arquetipo_2023':            slug_base23,
            'arquetipo_proy_2027':       slug_proy,
            'arquetipo_ajustado_2027':   slug_ajust,
            'arquetipo_alterno_2027':    slug_alt,
            'prob_proy_2027':            _r2(row['Prob arquetipo proyectado 2027'], 4),
            'prob_alterno_2027':         _r2(row['Prob arquetipo alterno 2027'], 4),
            'riesgo_cambio':             _r2(row['Riesgo de cambio 2023→2027'], 4),
            'tipo_evolucion':            str(row['Tipo evolución histórica']).strip(),
            'nivel_riesgo':              str(row['Nivel riesgo cambio']).strip(),
            'votos_por_arquetipo':       votos_arq,
        }

    # Agregados por comuna: sumar votos por arquetipo de los barrios de la comuna
    comunas = {}
    for dap, b in out_barrios.items():
        com = b['comuna']
        if not com:
            continue
        c = comunas.setdefault(com, {
            'comuna': com, 'n_barrios': 0,
            'votos_base_2023': 0, 'votos_2027': 0,
            'votos_por_arquetipo': { k: 0.0 for k in ['proteccion','castigo','continuidad','supervivencia','pertenencia'] },
        })
        c['n_barrios'] += 1
        c['votos_base_2023'] += (b['votos_base_2023'] or 0)
        c['votos_2027']      += (b['votos_2027'] or 0)
        for k, v in b['votos_por_arquetipo'].items():
            c['votos_por_arquetipo'][k] += (v or 0)
    # Redondear comunas y agregar arquetipo dominante (mayor votos)
    for com, c in comunas.items():
        v = c['votos_por_arquetipo']
        c['votos_por_arquetipo'] = { k: round(val, 2) for k, val in v.items() }
        c['arquetipo_dominante_2027'] = max(v.items(), key=lambda kv: kv[1])[0] if v else None
        c['votos_base_2023'] = int(c['votos_base_2023'])
        c['votos_2027']      = int(c['votos_2027'])

    out = {
        'version': datetime.now(timezone.utc).strftime('%Y%m%d'),
        'fuente': 'VOTACIÓN ESPERADA POR ARQUETIPO 2027.xlsx · Nury · entrega 2026-05-28',
        'metodologia': (
            'Cada barrio DAP de Medellín trae los votos base 2023 (alcaldía) y '
            'los votos esperados 2027 distribuidos entre los 5 arquetipos '
            'psicopolíticos. La proyección 2027 oficial usa "arquetipo_ajustado_2027" '
            f'(48 de 152 barrios tienen ajuste distinto al proyectado tendencial).'
        ),
        'totales': {
            'n_barrios': len(out_barrios),
            'n_comunas': len(comunas),
            'barrios_con_ajuste_distinto': diff_count,
        },
        'barrios': out_barrios,
        'comunas': comunas,
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f'\n✓ Escrito: {OUT_FILE}', file=sys.stderr)
    print(f'  ({os.path.getsize(OUT_FILE):,} bytes · {len(out_barrios)} barrios · {len(comunas)} comunas)', file=sys.stderr)
    print(f'  Ajustes distintos al proyectado: {diff_count} de 152', file=sys.stderr)

    # Spot checks
    sample_dap = '0413'
    if sample_dap in out_barrios:
        b = out_barrios[sample_dap]
        print(f'\nSample DAP {sample_dap} ({b["barrio"]}, {b["comuna"]}):', file=sys.stderr)
        print(f'  votos_base_2023: {b["votos_base_2023"]:,}', file=sys.stderr)
        print(f'  votos_2027:      {b["votos_2027"]:,}', file=sys.stderr)
        print(f'  factor:          {b["factor_crecimiento"]}', file=sys.stderr)
        print(f'  arq 2023:        {b["arquetipo_2023"]}', file=sys.stderr)
        print(f'  arq proy 2027:   {b["arquetipo_proy_2027"]}', file=sys.stderr)
        print(f'  arq AJUSTADO 27: {b["arquetipo_ajustado_2027"]}', file=sys.stderr)
        print(f'  votos por arq:   {b["votos_por_arquetipo"]}', file=sys.stderr)


if __name__ == '__main__':
    main()
