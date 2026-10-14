#!/usr/bin/env python3
"""
build_curules_2023.py — complemento del tablero de ASAMBLEA 2023 para el
reparto de curules (hemiciclo + WHAT IF) de resultados-asamblea-2023.html.

Va APARTE de build_asamblea_resultados.py a propósito: ese builder emite el
dato que comparten las tres páginas territoriales (JAL · Concejo · Asamblea) y
el reparto es solo de asamblea. Lo que este archivo agrega, sin tocar nada de
lo existente:

  listas-puesto/{dde}-{mme}.json
      {"p": {"zz-pp": [[partido, votos]]}, "m": {"zz-pp": {"mesa": [[partido, votos]]}},
       "b": {"zz-pp": {"mesa": votos_en_blanco}}}
      el voto SOLO POR LA LISTA por puesto y mesa. Los `v` de mun/{dde}-{mme}.json
      son por candidato: sin esto, en el WHAT IF por puesto una lista cerrada
      (Pacto Histórico en Medellín: 51.482 votos, todos de lista) saldría en CERO.

Además imprime (no escribe) dos controles que se copiaron a mano a la página:
  · el SEGUNDO en gobernación por departamento → SEGUNDO_GOB_2023 (curul del
    Estatuto de Oposición, Ley 1909/2018 art. 25);
  · los COD_CIR de asamblea: todos llegan en '1' (una sola circunscripción).
⚠️ Los candidatos de las listas CERRADAS no existen en el GCS (ni con 0 votos):
la fuente solo trae el voto al logo. Por eso la página no puede nombrar a sus
electos y deja el hueco declarado.

Fuente: Bases de datos/FINAL SUBIDA GCS/GCS_2023TER.csv
        COD_COR=2 (asamblea) y COD_COR=1 (gobernador, para el segundo).
Salida: Bases de datos/output_asamblea_2023/ (gitignored)
S3:     congreso-2026/output/asamblea-2023/listas-puesto/
"""
import csv, json, os, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BD = os.path.join(ROOT, 'Bases de datos')
SRC = os.path.join(BD, 'FINAL SUBIDA GCS', 'GCS_2023TER.csv')
OUT = os.path.join(BD, 'output_asamblea_2023')
sys.path.insert(0, os.path.join(ROOT, 'tools', 'analisis-candidato'))
from gcs_columnas import columnas                                    # noqa: E402

SPECIAL = {'996', '997', '998', '999'}
BOGOTA = '16'


def strip(s):
    return unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().upper().strip()


def main():
    C = columnas(SRC)
    asam = {}     # dde → {'cands': {(par,can,nom): [partido, votos]}, 'cir': {}}
    gob = {}      # dde → {(nom, partido): votos}
    lp = {}       # (dde, mme) → {'p': {pk: {partido: v}}, 'm': {pk: {ms: {partido: v}}}}
    with open(SRC, encoding='utf-8', errors='replace', newline='') as f:
        rd = csv.reader(f, delimiter=';')
        next(rd)
        for row in rd:
            if len(row) < C['_ancho']:
                continue
            cor = row[C['COD_COR']].strip()
            if cor not in ('1', '2'):
                continue
            dde = row[C['COD_DDE']].strip().zfill(2)
            if dde == BOGOTA:
                continue
            can = row[C['COD_CAN']].strip()
            try:
                v = int(row[C['NUM_VOT']] or 0)
            except ValueError:
                v = 0
            partido = (row[C['DES_PAR']] or '').strip() or 'SIN PARTIDO'
            if cor == '1':
                if can in SPECIAL or can == '0':
                    continue
                g = gob.setdefault(dde, {})
                k = (strip(row[C['DES_CAN']]), partido)
                g[k] = g.get(k, 0) + v
                continue
            d = asam.setdefault(dde, {'cands': {}, 'cir': {}})
            cir = row[C['COD_CIR']].strip()
            d['cir'][cir] = d['cir'].get(cir, 0) + v
            if can == '996' and v > 0:
                mme = row[C['COD_MME']].strip().zfill(3)
                pk = f"{row[C['COD_ZZ']].strip().zfill(2)}-{row[C['COD_PP']].strip().zfill(2)}"
                ms = row[C['DES_MS']].strip().zfill(3)
                xb = lp.setdefault((dde, mme), {'p': {}, 'm': {}, 'b': {}})['b'].setdefault(pk, {})
                xb[ms] = xb.get(ms, 0) + v       # mun/*.json no trae el blanco por mesa
            if can in SPECIAL:
                continue
            if can != '0':
                k = (row[C['COD_PAR']].strip(), can, strip(row[C['DES_CAN']]))
                c = d['cands'].setdefault(k, [partido, 0])
                c[1] += v           # se registra aunque v sea 0: la lista cerrada trae filas en 0
                continue
            if v <= 0:
                continue
            mme = row[C['COD_MME']].strip().zfill(3)
            pk = f"{row[C['COD_ZZ']].strip().zfill(2)}-{row[C['COD_PP']].strip().zfill(2)}"
            ms = row[C['DES_MS']].strip().zfill(3)
            x = lp.setdefault((dde, mme), {'p': {}, 'm': {}, 'b': {}})
            xp = x['p'].setdefault(pk, {})
            xp[partido] = xp.get(partido, 0) + v
            xm = x['m'].setdefault(pk, {}).setdefault(ms, {})
            xm[partido] = xm.get(partido, 0) + v

    os.makedirs(os.path.join(OUT, 'listas-puesto'), exist_ok=True)
    srt = lambda dct: [[p, v] for p, v in sorted(dct.items(), key=lambda kv: -kv[1])]
    for dde in sorted(asam):
        d = asam[dde]
        g = sorted(gob.get(dde, {}).items(), key=lambda kv: -kv[1])
        seg = g[1] if len(g) > 1 else None
        en_cero = sum(1 for (_, v) in d['cands'].values() if v == 0)
        print(dde, 'cir', d['cir'], '· cands', len(d['cands']), '· en 0:', en_cero,
              '· segundo gob:', [seg[0][0], seg[0][1], seg[1]] if seg else None)
    n = 0
    for (dde, mme), x in lp.items():
        out = {'p': {pk: srt(dd) for pk, dd in x['p'].items()},
               'm': {pk: {ms: srt(dd) for ms, dd in mm.items()} for pk, mm in x['m'].items()},
               'b': x['b']}
        with open(os.path.join(OUT, 'listas-puesto', f'{dde}-{mme}.json'), 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
        n += 1
    print(f'listas-puesto: {n} municipios')

if __name__ == '__main__':
    main()
