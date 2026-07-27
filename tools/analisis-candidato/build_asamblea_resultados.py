#!/usr/bin/env python3
"""
build_asamblea_resultados.py — tablero territorial de ASAMBLEA DEPARTAMENTAL 2023
(resultados-asamblea-2023.html). Mismo tablero que JAL/Concejo, un nivel arriba:
la asamblea es circunscripción DEPARTAMENTAL, así que el drill es

    departamento → municipio → puesto → mesa

(en JAL/Concejo era ciudad → comuna → barrio/puesto/mesa).

Salidas — mismo contrato que el tablero de JAL/Concejo, pero partido por depto
porque son 1.101 municipios y el índice único sería pesado en móvil:

  resultados-asamblea-2023.json   índice liviano: 32 deptos con sus totales
  dep/{dde}.json                  municipios del depto (partidos + TODOS los
                                  diputados con sus votos) · lazy al elegir depto
  mun/{dde}-{mme}.json            detalle del municipio: puestos + mesas · lazy

Fuente: Bases de datos/FINAL SUBIDA GCS/GCS_2023TER.csv  (COD_COR='2' · ASAMBLEA)
  ⚠️ El archivo trae las 4 corporaciones INTERCALADAS (1 gobernador · 2 asamblea
  · 3 alcalde · 4 concejo) → el filtro por COD_COR es obligatorio.
Censo/nombres: Bases de datos/PUESTOS_GEOREF.csv

Bogotá (dde 16) NO tiene asamblea (es Distrito Capital) → queda fuera.

S3: congreso-2026/output/asamblea-2023/{resultados-asamblea-2023.json,dep/,mun/}
"""
import csv, json, os, subprocess, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BD   = os.path.join(ROOT, 'Bases de datos')
SRC  = os.path.join(BD, 'FINAL SUBIDA GCS', 'GCS_2023TER.csv')
GEOREF = os.path.join(BD, 'PUESTOS_GEOREF.csv')
OUT_DIR = os.path.join(BD, 'output_asamblea_2023')
SCRATCH = os.environ.get('SCRATCH_DIR', '/tmp')
SORTED = os.path.join(SCRATCH, 'asamblea_2023_sorted.csv')

COD_COR = '2'
SPECIAL = {'996', '997', '998', '999'}
C_COR = 2
C_CAN, C_VOT, C_DDE, C_MME, C_ZZ, C_PP = 13, 15, 6, 7, 8, 9
C_MS, C_PAR, C_DESPAR, C_DESCAN = 10, 11, 12, 14
BOGOTA = '16'          # Distrito Capital: sin asamblea


def strip(s):
    return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper().strip()


def load_georef():
    """pcode(9) → censo · nombres de depto/municipio/puesto por código."""
    pot, depN, munN, pueN = {}, {}, {}, {}
    with open(GEOREF, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f, delimiter=';'):
            code = (row.get('CÓDIGO COMPLETO') or '').strip()
            if len(code) != 9:
                continue
            dd, mm = code[:2], code[2:5]
            try:
                m = int((row.get('MUJERES') or '0').strip() or 0)
                h = int((row.get('HOMBRES') or '0').strip() or 0)
            except ValueError:
                m = h = 0
            pot[(dd, mm)] = pot.get((dd, mm), 0) + m + h
            if dd not in depN:
                d = (row.get('DEPARTAMENTO') or '').strip()
                if d and d.upper() != 'NULL':
                    depN[dd] = d
            if (dd, mm) not in munN:
                mu = (row.get('MUNICIPIO') or '').strip()
                if mu and mu.upper() != 'NULL':
                    munN[(dd, mm)] = mu
            pueN[code] = (row.get('NOMBRE PUESTO') or '').strip() or f'PUESTO {code[5:7]}-{code[7:]}'
    return pot, depN, munN, pueN


def ensure_sorted():
    """Temporal solo con ASAMBLEA, ordenado por (dde,mme) para agrupar depto a depto."""
    if os.path.exists(SORTED) and os.path.getsize(SORTED) > 0:
        print(f'· usando temporal ya ordenado: {SORTED}')
        return
    os.makedirs(SCRATCH, exist_ok=True)
    print(f'· filtrando GCS_2023TER (COD_COR={COD_COR}) y ordenando…')
    with open(SORTED, 'wb') as out:
        p1 = subprocess.Popen(['awk', '-F;', f'NR>1 && $3=="{COD_COR}"', SRC], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['sort', '-t;', '-k7,7', '-k8,8', '-S', '1G'],
                              stdin=p1.stdout, stdout=out,
                              env={**os.environ, 'LC_ALL': 'C', 'TMPDIR': SCRATCH})
        p1.stdout.close()
        p2.communicate()
        if p2.returncode != 0:
            sys.exit('sort falló')
    print(f'· temporal listo: {os.path.getsize(SORTED)/1e6:.0f} MB')


def vlist(cvotes, cidx):
    return sorted(([cidx[k], v] for k, v in cvotes.items()), key=lambda x: -x[1])


def flush_depto(dde, muns, pot, depN, munN, pueN, index_rows):
    """Escribe dep/{dde}.json (municipios) + mun/{dde}-{mme}.json (puestos/mesas)."""
    if not muns:
        return None
    # master de partidos y candidatos del DEPARTAMENTO (la asamblea es depto-wide)
    dep_parties, dep_cands = {}, {}
    for m in muns.values():
        for p, v in m['parties'].items():
            dep_parties[p] = dep_parties.get(p, 0) + v
        for ck, info in m['cands'].items():
            c = dep_cands.get(ck)
            if c is None:
                dep_cands[ck] = {'nom': info['nom'], 'par_name': info['par_name'], 'v': info['v']}
            else:
                c['v'] += info['v']
    parties = sorted(dep_parties.items(), key=lambda kv: -kv[1])
    pidx = {p: i for i, (p, _) in enumerate(parties)}
    cand_master = sorted(dep_cands.items(), key=lambda kv: (-kv[1]['v'], kv[0]))
    cidx = {}
    cands_out = []
    for i, (ck, info) in enumerate(cand_master):
        cidx[ck] = i
        cands_out.append([info['nom'], pidx.get(info['par_name'], 0)])

    munis, tot_val, tot_bl, tot_pot = {}, 0, 0, 0
    for mme, m in sorted(muns.items()):
        mparties = sorted(m['parties'].items(), key=lambda kv: -kv[1])
        mpidx = {p: i for i, (p, _) in enumerate(mparties)}
        cand_list = [[info['nom'], mpidx.get(info['par_name'], 0), info['v']]
                     for ck, info in sorted(m['cands'].items(), key=lambda kv: -kv[1]['v'])]
        potm = pot.get((dde, mme), 0)
        votantes = m['validos'] + m['blanco'] + m['nulos']
        munis[mme] = {
            'name': munN.get((dde, mme), f'MUNICIPIO {mme}'),
            'validos': m['validos'], 'blanco': m['blanco'], 'nulos': m['nulos'],
            'votantes': votantes, 'potencial': potm, 'mesas': len(m['mesas']),
            'partidos': [[p, v] for p, v in mparties],
            'cands': cand_list,
        }
        tot_val += m['validos']; tot_bl += m['blanco']; tot_pot += potm

        # detalle del municipio: puestos + mesas (lazy en el frontend)
        puestos_out = []
        for pk, p in sorted(m['puestos'].items(), key=lambda kv: -kv[1]['validos']):
            mesas = [[ms, mm['validos'], vlist(mm['cands'], cidx)]
                     for ms, mm in sorted(p['mesas'].items())]
            puestos_out.append({
                'code': pk, 'nombre': p['nombre'],
                # el georef no cubre algunos agregados del CSV (p.ej. zona 99 puesto 00);
                # se muestran igual, marcados — no inventamos a qué corresponden.
                'barrio': '' if p['georef'] else 'sin georreferenciar',
                'validos': p['validos'], 'blanco': p['blanco'], 'nulos': p['nulos'],
                'v': vlist(p['cands'], cidx), 'mesas': mesas,
            })
        det = {
            'dde': dde, 'mme': mme, 'name': munis[mme]['name'],
            'dep': depN.get(dde, dde), 'has_barrio_map': False,
            'partidos': [[p, v] for p, v in parties], 'cands': cands_out,
            'totals': {'validos': m['validos'], 'blanco': m['blanco'], 'nulos': m['nulos']},
            'barrios': [], 'fills': [], 'puestos': puestos_out,
        }
        with open(os.path.join(OUT_DIR, 'mun', f'{dde}-{mme}.json'), 'w', encoding='utf-8') as f:
            json.dump(det, f, ensure_ascii=False, separators=(',', ':'))

    top_parties = sorted(dep_parties.items(), key=lambda kv: -kv[1])[:8]
    dep_payload = {
        'key': dde, 'name': depN.get(dde, dde), 'nivel': 'municipio',
        'comunas': munis,
        'totals': {'validos': tot_val, 'blanco': tot_bl, 'potencial': tot_pot,
                   'top_partidos': [[p, v] for p, v in top_parties]},
    }
    with open(os.path.join(OUT_DIR, 'dep', f'{dde}.json'), 'w', encoding='utf-8') as f:
        json.dump(dep_payload, f, ensure_ascii=False, separators=(',', ':'))
    index_rows.append({
        'key': dde, 'name': depN.get(dde, dde), 'dep': depN.get(dde, dde),
        'nivel': 'municipio', 'dde': dde, 'mme': '', 'n_comunas': len(munis),
        'validos': tot_val, 'blanco': tot_bl, 'potencial': tot_pot,
    })
    return len(munis)


def main():
    for sub in ('dep', 'mun'):
        os.makedirs(os.path.join(OUT_DIR, sub), exist_ok=True)
    ensure_sorted()
    pot, depN, munN, pueN = load_georef()
    print(f'GEOREF: {len(munN)} municipios · {len(depN)} deptos')

    index_rows = []
    cur = None
    muns = {}
    n = 0
    with open(SORTED, encoding='utf-8', errors='replace', newline='') as f:
        for row in csv.reader(f, delimiter=';'):   # el temporal viene SIN encabezado
            if len(row) < 16:
                continue
            if row[C_COR].strip() != COD_COR:
                continue
            dde = row[C_DDE].strip().zfill(2)
            mme = row[C_MME].strip().zfill(3)
            if dde == BOGOTA:
                continue
            if dde != cur:
                if cur is not None:
                    flush_depto(cur, muns, pot, depN, munN, pueN, index_rows)
                    muns = {}
                cur = dde
            try:
                v = int(row[C_VOT] or 0)
            except ValueError:
                v = 0
            if v <= 0:
                continue
            zz = (row[C_ZZ] or '').strip().zfill(2)
            pp = (row[C_PP] or '').strip().zfill(2)
            ms = (row[C_MS] or '').strip().zfill(3)
            m = muns.get(mme)
            if m is None:
                m = muns[mme] = {'validos': 0, 'blanco': 0, 'nulos': 0, 'mesas': set(),
                                 'parties': {}, 'cands': {}, 'puestos': {}}
            m['mesas'].add((zz, pp, ms))
            pk = f'{zz}-{pp}'
            p = m['puestos'].get(pk)
            if p is None:
                nom = pueN.get(f'{dde}{mme}{zz}{pp}')
                p = m['puestos'][pk] = {
                    'nombre': nom or f'Zona {zz} · puesto {pp}', 'georef': bool(nom),
                    'validos': 0, 'blanco': 0, 'nulos': 0, 'cands': {}, 'mesas': {}}
            mm = p['mesas'].get(ms)
            if mm is None:
                mm = p['mesas'][ms] = {'validos': 0, 'blanco': 0, 'nulos': 0, 'cands': {}}
            can = row[C_CAN].strip()
            if can == '0':                      # fila de partido (encabezado)
                continue
            if can == '996':
                m['blanco'] += v; p['blanco'] += v; mm['blanco'] += v
            elif can in SPECIAL:
                m['nulos'] += v; p['nulos'] += v; mm['nulos'] += v
            else:
                m['validos'] += v; p['validos'] += v; mm['validos'] += v
                par = row[C_PAR].strip()
                party = (row[C_DESPAR] or '').strip() or 'SIN PARTIDO'
                nom = strip(row[C_DESCAN]) or f'CAND {can}'
                ck = (par, can, nom)
                m['parties'][party] = m['parties'].get(party, 0) + v
                cc = m['cands'].get(ck)
                if cc is None:
                    cc = m['cands'][ck] = {'nom': nom, 'par_name': party, 'v': 0}
                cc['v'] += v
                p['cands'][ck] = p['cands'].get(ck, 0) + v
                mm['cands'][ck] = mm['cands'].get(ck, 0) + v
            n += 1
    if cur is not None:
        flush_depto(cur, muns, pot, depN, munN, pueN, index_rows)

    index_rows.sort(key=lambda r: -r['validos'])
    idx = os.path.join(OUT_DIR, 'resultados-asamblea-2023.json')
    with open(idx, 'w', encoding='utf-8') as f:
        json.dump({'v': '2026-07-27', 'eleccion': 'Asamblea Departamental 2023',
                   'cities': index_rows}, f, ensure_ascii=False, separators=(',', ':'))

    def dirsize(p):
        return sum(os.path.getsize(os.path.join(p, x)) for x in os.listdir(p))
    print(f'\n{n:,} filas · {len(index_rows)} departamentos → {idx} ({os.path.getsize(idx)//1024} KB)')
    print(f'  dep/: {len(os.listdir(os.path.join(OUT_DIR,"dep")))} archivos · {dirsize(os.path.join(OUT_DIR,"dep"))/1e6:.1f} MB')
    print(f'  mun/: {len(os.listdir(os.path.join(OUT_DIR,"mun")))} archivos · {dirsize(os.path.join(OUT_DIR,"mun"))/1e6:.1f} MB')
    for r in index_rows[:6]:
        print(f"  {r['name'][:20]:22} {r['n_comunas']:4} muns · {r['validos']:>9,} válidos")


if __name__ == '__main__':
    main()
