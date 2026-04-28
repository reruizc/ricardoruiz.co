#!/usr/bin/env python3
"""
build-seguridad-medellin.py

Procesa los CSVs de seguridad de la Policía Nacional (un archivo por
tipología) y genera JSONs agregados para Medellín.

Uso:
    python3 tools/build-seguridad-medellin.py <input-dir> <out-dir> <periodo>

Ejemplo:
    python3 tools/build-seguridad-medellin.py \\
        "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/Seguridad/Enero 2026/clean" \\
        "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/output_seguridad/2026-01" \\
        2026-01

Salida:
    {out-dir}/resumen.json    nacional + Medellín por tipología, % del nacional
    {out-dir}/por-comuna.json comuna × tipología × conteo
    {out-dir}/por-dia.json    serie temporal diaria
    {out-dir}/por-hora.json   distribución horaria
    {out-dir}/por-genero.json género × tipología
    {out-dir}/por-clase-sitio.json  tipo de lugar

Notas:
- Filtro Medellín: MUNICIPIO_HECHO == "Medellín (CT)"
- Comunas: regex sobre COMUNAS_ZONAS_DESCRIPCION ("COMUNA No. X NOMBRE")
  · 1-16  → comunas políticas (codes 01-16)
  · 50,60,70,80,90 → corregimientos (codes 50/60/70/80/90)
  · otros → "OTROS" (errores de captura, p.ej. "COMUNA NORORIENTAL")
- Cada fila es 1 incidente (CANTIDAD generalmente = 1)
"""

import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Las 19 tipologías esperadas (match con nombres de archivo sin .csv)
TIPOLOGIAS = [
    'amenazas', 'delitos-informaticos', 'delitos-sexuales', 'extorsion',
    'homicidios', 'homicidios-en-at', 'hurto-a-comercio', 'hurto-a-motos',
    'hurto-a-personas', 'hurto-a-residencias', 'hurto-automotores',
    'hurto-bicicletas', 'hurto-celular', 'lesiones-en-at',
    'lesiones-personales', 'pirateria-terrestre', 'secuestro', 'terrorismo',
    'violencia-intrafamiliar',
]

# Comunas y corregimientos de Medellín (codes alineados con GeoJSON
# mapas-2026/Ciudades-COM-LOC/MEDELLINX.json).
COMUNAS = {
    '01': 'Popular', '02': 'Santa Cruz', '03': 'Manrique', '04': 'Aranjuez',
    '05': 'Castilla', '06': 'Doce de Octubre', '07': 'Robledo',
    '08': 'Villa Hermosa', '09': 'Buenos Aires', '10': 'La Candelaria',
    '11': 'Laureles Estadio', '12': 'La América', '13': 'San Javier',
    '14': 'El Poblado', '15': 'Guayabal', '16': 'Belén',
    '50': 'Palmitas', '60': 'San Cristóbal', '70': 'Altavista',
    '80': 'San Antonio de Prado', '90': 'Santa Elena',
    'OTROS': 'Otros / sin clasificar',
}

# Población estimada (placeholder, mismo dataset que módulo pobreza-ipm).
# Reemplazar con DANE oficial cuando esté disponible.
POBLACION = {
    '01': 130000, '02': 110000, '03': 165000, '04': 165000,
    '05': 145000, '06': 195000, '07': 175000, '08': 140000,
    '09': 135000, '10':  85000, '11': 120000, '12':  95000,
    '13': 145000, '14': 135000, '15':  95000, '16': 200000,
    '50':   8500, '60':  74000, '70':  43000, '80': 130000, '90': 18000,
}

RE_COMUNA = re.compile(r'COMUNA\s+(?:No\.?\s+)?(\d+)', re.IGNORECASE)


def extract_comuna(desc: str) -> str:
    """Extrae código de comuna desde COMUNAS_ZONAS_DESCRIPCION.
    Devuelve '01'..'16' / '50'/'60'/'70'/'80'/'90' / 'OTROS'."""
    if not desc:
        return 'OTROS'
    m = RE_COMUNA.search(desc)
    if not m:
        return 'OTROS'
    n = int(m.group(1))
    if 1 <= n <= 16:
        return f'{n:02d}'
    if n in (50, 60, 70, 80, 90):
        return str(n)
    return 'OTROS'


def process_csv(path: Path, tipologia: str, agg: dict) -> int:
    """Procesa un CSV y acumula en agg. Devuelve filas Medellín leídas."""
    rows_med = 0
    rows_total = 0
    with open(path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows_total += 1
            qty = int(row.get('CANTIDAD') or 1) or 1
            agg['nacional']['por_tipologia'][tipologia] += qty
            agg['nacional']['total'] += qty

            mun = (row.get('MUNICIPIO_HECHO') or '').strip()
            if mun != 'Medellín (CT)':
                continue
            rows_med += qty

            agg['medellin']['por_tipologia'][tipologia] += qty
            agg['medellin']['total'] += qty

            comuna = extract_comuna(row.get('COMUNAS_ZONAS_DESCRIPCION') or '')
            agg['por_comuna'][comuna]['total'] += qty
            agg['por_comuna'][comuna]['por_tipologia'][tipologia] += qty

            fecha = (row.get('FECHA_HECHO') or '').strip()
            if fecha:
                agg['por_dia'][fecha]['total'] += qty
                agg['por_dia'][fecha]['por_tipologia'][tipologia] += qty

            hora_str = (row.get('HORA_HECHO') or '').strip()
            if hora_str and ':' in hora_str:
                hora = hora_str.split(':')[0].zfill(2)
                if len(hora) == 2 and hora.isdigit():
                    agg['por_hora'][hora]['total'] += qty
                    agg['por_hora'][hora]['por_tipologia'][tipologia] += qty

            genero = (row.get('GENERO') or 'NO REPORTADO').strip().upper() or 'NO REPORTADO'
            agg['por_genero'][genero]['total'] += qty
            agg['por_genero'][genero]['por_tipologia'][tipologia] += qty

            sitio = (row.get('CLASE_SITIO') or 'NO REPORTADO').strip().upper() or 'NO REPORTADO'
            agg['por_clase_sitio'][sitio]['total'] += qty
            agg['por_clase_sitio'][sitio]['por_tipologia'][tipologia] += qty

            dia_sem = (row.get('DIA_SEMANA') or '').strip()
            if dia_sem:
                agg['por_dia_semana'][dia_sem]['total'] += qty
                agg['por_dia_semana'][dia_sem]['por_tipologia'][tipologia] += qty

    return rows_med, rows_total


def make_agg():
    return {
        'nacional': {
            'total': 0,
            'por_tipologia': defaultdict(int),
        },
        'medellin': {
            'total': 0,
            'por_tipologia': defaultdict(int),
        },
        'por_comuna': defaultdict(lambda: {'total': 0, 'por_tipologia': defaultdict(int)}),
        'por_dia': defaultdict(lambda: {'total': 0, 'por_tipologia': defaultdict(int)}),
        'por_hora': defaultdict(lambda: {'total': 0, 'por_tipologia': defaultdict(int)}),
        'por_genero': defaultdict(lambda: {'total': 0, 'por_tipologia': defaultdict(int)}),
        'por_clase_sitio': defaultdict(lambda: {'total': 0, 'por_tipologia': defaultdict(int)}),
        'por_dia_semana': defaultdict(lambda: {'total': 0, 'por_tipologia': defaultdict(int)}),
    }


def to_serializable(obj):
    """Convert defaultdicts → dicts recursively."""
    if isinstance(obj, defaultdict) or isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    return obj


def main():
    if len(sys.argv) < 4:
        print('Uso: build-seguridad-medellin.py <input-dir> <out-dir> <periodo>')
        sys.exit(1)
    in_dir = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    periodo = sys.argv[3]
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f'\n[seguridad] periodo {periodo}')
    print(f'  input:  {in_dir}')
    print(f'  output: {out_dir}\n')

    agg = make_agg()
    found = []
    for tip in TIPOLOGIAS:
        path = in_dir / f'{tip}.csv'
        if not path.exists():
            print(f'  · {tip:25s} NO EXISTE — skip')
            continue
        t0 = datetime.now()
        med, tot = process_csv(path, tip, agg)
        dt = (datetime.now() - t0).total_seconds()
        print(f'  · {tip:25s} {tot:>7,} nac · {med:>5,} Med ({dt:4.1f}s)')
        found.append(tip)

    # ─── Build outputs ────────────────────────────────────────────────
    pob_total = sum(POBLACION.values())

    # resumen.json
    nacional = to_serializable(agg['nacional'])
    medellin = to_serializable(agg['medellin'])
    share = {}
    for tip, n_med in medellin['por_tipologia'].items():
        n_nac = nacional['por_tipologia'].get(tip, 0)
        share[tip] = round((n_med / n_nac * 100) if n_nac else 0, 3)
    medellin['share_nacional_pct'] = share
    medellin['poblacion_estimada'] = pob_total
    medellin['tasa_por_100k'] = {
        tip: round(n / pob_total * 100000, 2)
        for tip, n in medellin['por_tipologia'].items()
    }

    resumen = {
        'meta': {
            'periodo': periodo,
            'generado_en': datetime.now().isoformat(),
            'tipologias': found,
            'fuente': 'Policía Nacional · CSVs limpios por tipología',
        },
        'nacional': nacional,
        'medellin': medellin,
    }
    (out_dir / 'resumen.json').write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

    # por-comuna.json
    por_comuna = {}
    for cod, scope in agg['por_comuna'].items():
        scope_dict = to_serializable(scope)
        pob = POBLACION.get(cod, 0)
        por_comuna[cod] = {
            'nombre': COMUNAS.get(cod, cod),
            'poblacion_estimada': pob,
            'total': scope_dict['total'],
            'por_tipologia': scope_dict['por_tipologia'],
            'tasa_por_100k': round(scope_dict['total'] / pob * 100000, 2) if pob else None,
        }
    (out_dir / 'por-comuna.json').write_text(
        json.dumps(por_comuna, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

    # por-dia.json
    por_dia = to_serializable(agg['por_dia'])
    por_dia_sorted = dict(sorted(por_dia.items()))
    (out_dir / 'por-dia.json').write_text(
        json.dumps(por_dia_sorted, ensure_ascii=False),
        encoding='utf-8'
    )

    # por-hora.json
    por_hora = to_serializable(agg['por_hora'])
    por_hora_sorted = dict(sorted(por_hora.items()))
    (out_dir / 'por-hora.json').write_text(
        json.dumps(por_hora_sorted, ensure_ascii=False),
        encoding='utf-8'
    )

    # por-genero.json
    (out_dir / 'por-genero.json').write_text(
        json.dumps(to_serializable(agg['por_genero']), ensure_ascii=False),
        encoding='utf-8'
    )

    # por-clase-sitio.json
    (out_dir / 'por-clase-sitio.json').write_text(
        json.dumps(to_serializable(agg['por_clase_sitio']), ensure_ascii=False),
        encoding='utf-8'
    )

    # por-dia-semana.json
    (out_dir / 'por-dia-semana.json').write_text(
        json.dumps(to_serializable(agg['por_dia_semana']), ensure_ascii=False),
        encoding='utf-8'
    )

    # Sanity print
    print(f'\n[resumen]')
    print(f'  Nacional total: {nacional["total"]:>10,}')
    print(f'  Medellín total: {medellin["total"]:>10,} ({medellin["total"]/nacional["total"]*100:.2f}% del nacional)')
    print(f'  Tipologías procesadas: {len(found)}/{len(TIPOLOGIAS)}')
    top_med = sorted(medellin['por_tipologia'].items(), key=lambda x: -x[1])[:5]
    print(f'  Top Medellín:')
    for t, n in top_med:
        s = share.get(t, 0)
        print(f'    {t:25s} {n:>6,}  ({s}% del nacional)')
    top_com = sorted(por_comuna.items(), key=lambda x: -x[1]['total'])[:5]
    print(f'  Top comunas:')
    for c, d in top_com:
        print(f'    {d["nombre"]:25s} {d["total"]:>6,}  (tasa {d["tasa_por_100k"]}/100k)')

    # File sizes
    print(f'\n[archivos]')
    for fn in sorted(out_dir.glob('*.json')):
        size_kb = fn.stat().st_size / 1024
        print(f'  · {fn.name:25s} {size_kb:>7,.0f} KB')


if __name__ == '__main__':
    main()
