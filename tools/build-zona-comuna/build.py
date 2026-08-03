#!/usr/bin/env python3
"""Tabla zona electoral -> comuna/localidad politica, derivada de PUESTOS_GEOREF.

El drill cartografico de las paginas de escrutinio pinta poligonos de COMUNA,
pero los datos vienen agregados por ZONA ELECTORAL. En varias ciudades la
relacion no es 1:1 (Medellin: 32 zonas -> 16 comunas), asi que un join por
numero atribuye los votos a la comuna equivocada.

Salida: Bases de datos/output_geo/zona-comuna.json
  { "v": "YYYY-MM-DD",
    "muns": { "01-001": { "nombre": "MEDELLIN",
                          "z": { "01": "01", "02": "01", ... },   # zona -> cod comuna
                          "c": { "01": "COMUNA 1 POPULAR", ... }  # cod comuna -> nombre
                        } } }

Solo entran municipios donde el georef trae CODIGO COMUNA util. Las zonas 90
(puesto censo) y 98 (carceles) no pertenecen a ninguna comuna: quedan fuera.
"""
import csv, json, collections, datetime, os, re, sys

GEOREF = 'Bases de datos/PUESTOS_GEOREF.csv'
OUT_DIR = 'Bases de datos/output_geo'
OUT = os.path.join(OUT_DIR, 'zona-comuna.json')

# Zonas que no mapean a comuna politica.
ZONAS_ESPECIALES = {'90', '98'}


def limpia_nombre(s):
    """'01COMUNA 1 POPULAR' -> 'COMUNA 1 POPULAR'. El georef pega el codigo delante."""
    s = (s or '').strip()
    if s.upper() in ('NULL', 'NONE', ''):
        return ''
    s = re.sub(r'^\d{2}', '', s).strip()
    return s


def main():
    if not os.path.exists(GEOREF):
        sys.exit(f'falta {GEOREF}')
    with open(GEOREF, encoding='utf-8-sig', errors='replace') as f:
        head = f.readline()
    delim = ';' if head.count(';') > head.count(',') else ','

    # (dep,mun) -> zona -> Counter de cod comuna ; y cod comuna -> Counter de nombre
    zc = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    cn = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    munnom = {}

    with open(GEOREF, encoding='utf-8-sig', errors='replace') as f:
        for r in csv.DictReader(f, delimiter=delim):
            cc = (r.get('CÓDIGO COMPLETO') or r.get('CODIGO COMPLETO') or '').strip()
            if len(cc) != 9 or not cc.isdigit():
                continue
            dep, mun, zon = cc[:2], cc[2:5], cc[5:7]
            if zon in ZONAS_ESPECIALES:
                continue
            cod = (r.get('CÓDIGO COMUNA') or r.get('CODIGO COMUNA') or '').strip()
            if not cod or cod.upper() == 'NULL' or not cod.isdigit():
                continue
            cod = cod.zfill(2)
            key = f'{dep}-{mun}'
            zc[key][zon][cod] += 1
            nom = limpia_nombre(r.get('NOMBRE COMUNA'))
            if nom:
                cn[key][cod][nom] += 1
            munnom.setdefault(key, (r.get('MUNICIPIO') or '').strip())

    muns = {}
    for key, zonas in zc.items():
        # moda por zona: el georef trae erratas sueltas (un puesto mal codificado)
        z = {zon: c.most_common(1)[0][0] for zon, c in sorted(zonas.items())}
        # Si la relacion es 1:1 y la identidad (zona N -> comuna N), el join por
        # numero ya era correcto y la entrada no aporta nada: se omite.
        if all(zon == cod for zon, cod in z.items()):
            continue
        c = {cod: cc.most_common(1)[0][0] for cod, cc in sorted(cn[key].items()) if cc}
        muns[key] = {'nombre': munnom.get(key, ''), 'z': z, 'c': c}

    os.makedirs(OUT_DIR, exist_ok=True)
    payload = {'v': datetime.date.today().isoformat(),
               'fuente': 'PUESTOS_GEOREF.csv',
               'nota': 'zona electoral -> comuna politica. Solo municipios donde NO es identidad.',
               'muns': muns}
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))

    print(f'{OUT}  ({os.path.getsize(OUT)/1024:.1f} KB)')
    print(f'municipios con mapeo no trivial: {len(muns)}')
    for key in ['01-001', '16-001', '31-001', '08-001', '03-001', '09-001', '73-001', '66-001']:
        if key in muns:
            m = muns[key]
            inv = collections.defaultdict(list)
            for zon, cod in m['z'].items():
                inv[cod].append(zon)
            print(f"  {key} {m['nombre']}: {len(m['z'])} zonas -> {len(inv)} comunas")


if __name__ == '__main__':
    main()
