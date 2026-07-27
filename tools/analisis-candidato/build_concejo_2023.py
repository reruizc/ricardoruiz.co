#!/usr/bin/env python3
"""
build_concejo_2023.py — genera los JSONs por candidato de CONCEJO MUNICIPAL 2023
en el MISMO formato mesa-a-mesa de endoso/{slug}.json que consume
analisis-candidato.html / comparar-candidatos.html, + index-concejo-2023.json.

Concejo es circunscripción MUNICIPAL: cada candidato compite solo en su
municipio (COD_DDE + COD_MME), así que su mapa colorea un único municipio (dentro
de un departamento) y su drill baja a los puestos de ese municipio. La llave
(dde, mme, par, can) resuelve a UN candidato (verificado: 0 conflictos de nombre).

Fuentes (locales):
  Bases de datos/FINAL SUBIDA GCS/GCS_2023TER.csv   (COD_COR='4' = CONCEJO · 7,4M filas)
  Bases de datos/PUESTOS_GEOREF.csv                 (nombres mun/puesto/comuna)

Salida (gitignored):
  Bases de datos/output_concejo_2023/
    index-concejo-2023.json
    CONC2023-{dde}-{mme}-{par}-{can}.json   (~94k)

Memoria: la máquina tiene 8 GB y son 7,4M filas → NO se cargan todas a memoria.
Se extraen las filas COD_COR=4 y se ORDENAN por (dde,mme) a un temporal; luego se
procesa municipio por municipio (streaming), escribiendo los JSONs de cada
municipio y liberando memoria antes del siguiente. Cota de memoria = 1 municipio.

Subida a S3 (manual, luz verde del usuario):
  aws s3 cp "Bases de datos/output_concejo_2023/" \
    "s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/concejo-2023/" \
    --recursive --content-type "application/json" --cache-control "public, max-age=300"
"""
import csv, json, os, subprocess, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BD   = os.path.join(ROOT, 'Bases de datos')
SRC  = os.path.join(BD, 'FINAL SUBIDA GCS', 'GCS_2023TER.csv')
GEOREF = os.path.join(BD, 'PUESTOS_GEOREF.csv')
OUT_DIR = os.path.join(BD, 'output_concejo_2023')
SCRATCH = os.environ.get('SCRATCH_DIR',
    '/private/tmp/claude-501/-Users-ricardoruiz-ricardoruiz-co/9416b8e0-fd95-4229-aeaa-f8a817241616/scratchpad')
SORTED = os.path.join(SCRATCH, 'concejo_2023_sorted.csv')

COD_COR_CONCEJO = '4'

DEP_NAMES = {
    '01': 'ANTIOQUIA', '03': 'ATLÁNTICO', '05': 'BOLÍVAR', '07': 'BOYACÁ',
    '09': 'CALDAS', '11': 'CAUCA', '12': 'CESAR', '13': 'CÓRDOBA',
    '15': 'CUNDINAMARCA', '17': 'CHOCÓ', '19': 'HUILA', '21': 'MAGDALENA',
    '23': 'NARIÑO', '24': 'RISARALDA', '25': 'NORTE DE SANTANDER',
    '26': 'QUINDÍO', '27': 'SANTANDER', '28': 'SUCRE', '29': 'TOLIMA',
    '31': 'VALLE DEL CAUCA', '40': 'ARAUCA', '44': 'CAQUETÁ', '46': 'CASANARE',
    '48': 'LA GUAJIRA', '50': 'GUAINÍA', '52': 'META', '54': 'GUAVIARE',
    '56': 'SAN ANDRÉS', '60': 'AMAZONAS', '64': 'PUTUMAYO', '68': 'VAUPÉS',
    '72': 'VICHADA', '88': 'EXTERIOR', '16': 'BOGOTÁ D.C.',
}
SPECIAL_CAN = {'0', '996', '997', '998', '999'}

# Columnas GCS (0-based) tras split(';')
C_COR, C_DDE, C_MME, C_ZZ, C_PP = 2, 6, 7, 8, 9
C_MS, C_PAR, C_DESPAR, C_CAN, C_DESCAN, C_VOT = 10, 11, 12, 13, 14, 15


def strip(s):
    return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper().strip()


def load_georef():
    """9 díg (dd+mmm+zz+pp) → (mun, puesto, comCode, comNom); 5 díg → mun."""
    by9, muns = {}, {}
    with open(GEOREF, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f, delimiter=';'):
            code = (row.get('CÓDIGO COMPLETO') or '').strip()
            if len(code) != 9:
                continue
            mun = (row.get('MUNICIPIO') or '').strip()
            pue = (row.get('NOMBRE PUESTO') or '').strip()
            comC = (row.get('CÓDIGO COMUNA') or '').strip()
            comN = (row.get('NOMBRE COMUNA') or '').strip()
            if comN.upper() in ('NULL', ''):
                comC, comN = '000', 'NACIONAL'
            by9[code] = (mun, pue, comC or '000', comN or 'NACIONAL')
            muns.setdefault(code[:5], mun)
    return by9, muns


def ensure_sorted():
    """Extrae COD_COR=4 y ordena por (dde,mme) a un temporal. Idempotente."""
    if os.path.exists(SORTED) and os.path.getsize(SORTED) > 0:
        print(f'· usando temporal ya ordenado: {SORTED}')
        return
    os.makedirs(SCRATCH, exist_ok=True)
    print('· extrayendo COD_COR=4 y ordenando por (dde,mme)…')
    # awk extrae; sort agrupa por depto(k7) y municipio(k8). String-sort agrupa OK.
    awk = ["awk", "-F;", 'NR>1 && $3=="%s"' % COD_COR_CONCEJO, SRC]
    with open(SORTED, 'wb') as out:
        p1 = subprocess.Popen(awk, stdout=subprocess.PIPE)
        p2 = subprocess.Popen(
            ["sort", "-t;", "-k7,7", "-k8,8", "-S", "1G"],
            stdin=p1.stdout, stdout=out,
            env={**os.environ, "LC_ALL": "C", "TMPDIR": SCRATCH})
        p1.stdout.close()
        p2.communicate()
        if p2.returncode != 0:
            sys.exit('sort falló')
    print(f'· temporal listo: {os.path.getsize(SORTED)/1e9:.2f} GB')


def fmt(x):
    return f'{x:,}'.replace(',', '.')


def flush_group(cands, by9, munNames, index):
    """Escribe los JSONs de un municipio y agrega sus entradas al índice."""
    for (dde, mme, par, can), c in cands.items():
        dd = dde.zfill(2)
        mm = mme.zfill(3)
        depNom = DEP_NAMES.get(dd, f'DEP {dd}')
        # Bogotá D.C. es municipio único (mme=001) para el Concejo; el georef guarda
        # el nombre de la LOCALIDAD en MUNICIPIO, así que se fuerza el nombre correcto.
        munNom = 'BOGOTÁ D.C.' if dd == '16' else munNames.get(f'{dd}{mm}', c['munNom'] or f'MUN {mm}')
        mesas = []
        for (zz, pp, ms, v) in c['mesas']:
            g = by9.get(f'{dd}{mm}{zz}{pp}')
            pueNom = g[1] if g else f'PUESTO {zz}-{pp}'
            comC, comN = (g[2], g[3]) if g else ('000', 'NACIONAL')
            mesas.append({
                'dep': dd, 'depNom': depNom, 'mun': mm, 'munNom': munNom,
                'zon': zz, 'pue': pp, 'pueNom': pueNom, 'mesa': ms,
                'com': comC, 'comNom': comN, 'v': v,
            })
        slug = f'CONC2023-{dde}-{mme}-{par}-{can}'
        circ = munNom if munNom == depNom else f'{munNom} ({depNom})'
        data = {
            'nombre': c['nombre'], 'corp': f'CONCEJO · {munNom}',
            'circunscripcion': circ, 'partido': c['partido'],
            'votos': c['votos'], 'mesas': mesas,
        }
        with open(os.path.join(OUT_DIR, f'{slug}.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        index.append({
            'slug': slug, 'nombre': c['nombre'],
            'corp': f'CONCEJO · {munNom} · 2023', 'circunscripcion': circ,
            'partido': c['partido'], 'votos': c['votos'],
        })


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    by9, munNames = load_georef()
    print(f'GEOREF: {len(by9)} puestos · {len(munNames)} muns')
    ensure_sorted()

    index = []
    cands = {}
    cur_group = None   # (dde, mme)
    n_rows = 0
    with open(SORTED, encoding='utf-8', errors='replace', newline='') as f:
        for row in csv.reader(f, delimiter=';'):
            if len(row) < 16:
                continue
            can = row[C_CAN]
            if can in SPECIAL_CAN:
                continue
            try:
                v = int(row[C_VOT] or 0)
            except ValueError:
                v = 0
            if v <= 0:
                continue
            dde = row[C_DDE].strip()
            mme = row[C_MME].strip()
            grp = (dde, mme)
            if grp != cur_group:
                if cur_group is not None:
                    flush_group(cands, by9, munNames, index)
                    cands = {}
                cur_group = grp
            par = row[C_PAR].strip()
            key = (dde, mme, par, can)
            c = cands.get(key)
            if c is None:
                c = cands[key] = {
                    'nombre': strip(row[C_DESCAN]) or f'CANDIDATO {can}',
                    'partido': (row[C_DESPAR] or '').strip() or f'PARTIDO {par}',
                    'munNom': None, 'votos': 0, 'mesas': [],
                }
            zz = (row[C_ZZ] or '').strip().zfill(2)
            pp = (row[C_PP] or '').strip().zfill(2)
            ms = (row[C_MS] or '').strip().zfill(3)
            if c['munNom'] is None:
                dd = dde.zfill(2); mm = mme.zfill(3)
                gg = by9.get(f'{dd}{mm}{zz}{pp}')
                if gg:
                    c['munNom'] = gg[0]
            c['votos'] += v
            c['mesas'].append((zz, pp, ms, v))
            n_rows += 1
    if cur_group is not None:
        flush_group(cands, by9, munNames, index)

    index.sort(key=lambda x: -x['votos'])
    idx_path = os.path.join(OUT_DIR, 'index-concejo-2023.json')
    with open(idx_path, 'w', encoding='utf-8') as f:
        json.dump({'v': '2026-07-26', 'eleccion': 'Concejo Municipal 2023',
                   'candidatos': index}, f, ensure_ascii=False, separators=(',', ':'))

    print(f'{n_rows:,} filas mesa-candidato · {len(index):,} candidatos')
    print(f'→ index-concejo-2023.json ({os.path.getsize(idx_path)//1024} KB)')
    print('Top 5:', [(x['nombre'][:22], x['circunscripcion'][:22], fmt(x['votos'])) for x in index[:5]])


if __name__ == '__main__':
    main()
