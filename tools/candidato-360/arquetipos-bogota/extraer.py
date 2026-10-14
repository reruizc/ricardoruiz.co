#!/usr/bin/env python3
"""Extrae de los GCS de la Registraduría la votación de Bogotá por PUESTO.

    python3 tools/candidato-360/arquetipos-bogota/extraer.py <clave>

Claves: ter2023 · ter2019 · jal2023 · jal2019 · pres2022

Salida: Bases de datos/arquetipos-bogota/raw/<clave>.json
    {corp: {"zz-pp": {"par|can": votos}}, "_nombres": {"corp|par|can": nombre},
     "_partidos": {"corp|par": nombre}}

El voto por la lista (COD_CAN 0) se guarda como un candidato más ("par|0"):
sin él las listas cerradas desaparecen enteras. Los especiales van con
COD_PAR del archivo y COD_CAN 996-999.
"""
import csv, io, json, sys, time
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
GCS = RAIZ / 'Bases de datos' / 'FINAL SUBIDA GCS'
OUT = RAIZ / 'Bases de datos' / 'arquetipos-bogota' / 'raw'

# archivo · filtro rápido de línea · corporaciones que interesan {COD_COR: corp}
FUENTES = {
    'ter2023': ('GCS_2023TER.csv', ';MUNICIPAL;16;1;', {'3': 'alc', '4': 'conc'}),
    'ter2019': ('GCS_2019TER.csv', ';16;1;', {'6': 'alc', '7': 'conc'}),
    'jal2023': ('GCS_2023JAL.csv', ';LOCAL;16;1;', {'5': 'jal'}),
    'jal2019': ('GCS_2019JAL.csv', '0:00:00;16;1;', {'5': 'jal'}),
    'pres2022': ('GCS_2022PRES1V.csv', ';16;1;', {'3': 'pres'}),
}


def cod(x):
    x = (x or '').strip()
    return f'{int(x):02d}' if x.isdigit() else x


def main(clave):
    archivo, filtro, cors = FUENTES[clave]
    ruta = GCS / archivo
    t0 = time.time()
    with open(ruta, encoding='utf-8-sig', newline='') as fh:
        cab = next(csv.reader([fh.readline()], delimiter=';'))
        ix = {c: i for i, c in enumerate(cab)}
        need = ['COD_COR', 'COD_DDE', 'COD_MME', 'COD_ZZ', 'COD_PP', 'COD_PAR', 'DES_PAR', 'COD_CAN', 'DES_CAN', 'NUM_VOT']
        falta = [c for c in need if c not in ix]
        if falta:
            sys.exit(f'{archivo}: faltan columnas {falta}')
        agg = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        nombres, partidos = {}, {}
        n = 0
        for linea in fh:
            if filtro not in linea:
                continue
            row = next(csv.reader(io.StringIO(linea), delimiter=';'))
            if row[ix['COD_DDE']].strip() != '16' or row[ix['COD_MME']].strip().lstrip('0') != '1':
                continue
            corp = cors.get(row[ix['COD_COR']].strip())
            if not corp:
                continue
            try:
                v = int(row[ix['NUM_VOT']])
            except ValueError:
                continue
            p = f"{cod(row[ix['COD_ZZ']])}-{cod(row[ix['COD_PP']])}"
            par, can = row[ix['COD_PAR']].strip(), row[ix['COD_CAN']].strip()
            # En JAL el COD_CAN se reinicia por localidad (= zona en Bogotá):
            # la llave del candidato lleva la zona o se fusionan personas.
            ck = f"{cod(row[ix['COD_ZZ']])}|{par}|{can}" if corp == 'jal' else f'{par}|{can}'
            agg[corp][p][ck] += v
            nombres.setdefault(f'{corp}|{ck}', row[ix['DES_CAN']].strip())
            partidos.setdefault(f'{corp}|{par}', row[ix['DES_PAR']].strip())
            n += 1
    out = {c: {p: dict(d) for p, d in pp.items()} for c, pp in agg.items()}
    out['_nombres'] = nombres
    out['_partidos'] = partidos
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'{clave}.json').write_text(json.dumps(out, ensure_ascii=False))
    tot = {c: sum(sum(d.values()) for d in out[c].values()) for c in agg}
    print(f'{clave}: {n:,} filas · {time.time()-t0:.0f} s · puestos', {c: len(out[c]) for c in agg}, '· votos', tot)


if __name__ == '__main__':
    main(sys.argv[1])
