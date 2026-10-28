#!/usr/bin/env python3
"""Terminaciones anticipadas y fin real de los contratos OPS, desde las modificaciones de SECOP II.

Bajar u8cx-r425 por fecha es inviable (cada versión es una fila: 3,9 M en dos meses), pero por
id_contrato responde en <1 s. Se piden las modificaciones Publicadas/Aprobadas de los contratos OPS
del gobierno nacional que corrieron en 2026 o entre el 7-ago y el 31-oct de 2022 (comparación con Petro).
⚠ La caché de lotes va por posición en la lista ordenada de ids: al cambiar la maestra hay que vaciar
raw/modificaciones/ o los lotes viejos quedan asignados a ids que ya no les corresponden.

Terminación = modificación aprobada cuyo propósito habla de terminar el contrato, o que deja la fecha de
fin por debajo de la que hoy muestra el contrato. Quién la pide, por el texto: contratista · mutuo
acuerdo · entidad (unilateral) · sin dato.
Sale: v2/raw/modificaciones/*.json y v2/terminaciones.json {id_contrato: {...}}
"""
import concurrent.futures as cf, glob, json, os, pickle, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nacion import socrata, RAW, D

OUT = os.path.join(RAW, 'modificaciones'); os.makedirs(OUT, exist_ok=True)
LOTE = 150
TERM = re.compile(r'TERMINACI[OÓ]N ANTICIPADA|TERMINAR ANTICIPADAMENTE|TERMINA(R|CI[OÓ]N)\W+(\w+\W+){0,6}(DE |POR )?(MUTUO|COM[UÚ]N) ACUERDO|'
                  r'TERMINACI[OÓ]N BILATERAL|TERMINACI[OÓ]N UNILATERAL|TERMINACI[OÓ]N (DEL CONTRATO )?POR RENUNCIA|RENUNCIA (DEL|DE LA) CONTRATISTA|'
                  r'PRESENT[OÓ] RENUNCIA|ACEPTA(CI[OÓ]N DE)? (LA )?RENUNCIA', re.I)
NO_TERM = re.compile(r'VENCIMIENTO DEL PLAZO|CULMINACI[OÓ]N|POR ERROR|ERROR DE DIGITACI|CORRECCI[OÓ]N|SE AJUSTA LA FECHA', re.I)
QUIEN = [('contratista', re.compile(r'RENUNCI|SOLICITUD (ELEVADA |PRESENTADA |REALIZADA )?(POR )?(EL|LA) CONTRATISTA|SOLICITUD DE(L| LA) CONTRATISTA|'
                                    r'SOLICITADA POR (EL|LA) CONTRATISTA|NOMBRAMIENTO EN OTRA|'
                                    r'A SOLICITUD DEL CONTRATISTA|CONTRATISTA SOLICIT|MOTIVOS PERSONALES', re.I)),
         ('mutuo acuerdo', re.compile(r'MUTUO ACUERDO|COM[UÚ]N ACUERDO|BILATERAL', re.I)),
         ('entidad', re.compile(r'UNILATERAL', re.I))]


def ids_objetivo():
    M = pickle.load(open(os.path.join(D, 'maestra.pkl'), 'rb'))
    C = M['cols']; ix = {c: i for i, c in enumerate(C)}
    ids = set()
    for f in M['filas']:
        if f[ix['src']] != 's2' or f[ix['cat']] != 'nacional' or not f[ix['ops']] or not (f[ix['ini']] and f[ix['fin']]):
            continue
        ini, fin = f[ix['ini']], f[ix['fin']]
        if (fin >= '2026-01-01') or (fin >= '2022-08-07' and ini <= '2022-10-31'):
            ids.add(f[ix['id']])
    return sorted(ids), {f[ix['id']]: f for f in M['filas'] if f[ix['src']] == 's2'}, ix


def lote(i, ids):
    p = os.path.join(OUT, f'm-{i:05d}.json')
    if os.path.exists(p):
        return 0
    inn = ','.join(f"'{x}'" for x in ids)
    filas = socrata('u8cx-r425', {'$select': 'id_contrato,fecha_de_aprobacion,fecha_fin_contrato,dias_extendidos,'
                                             'valor_modificacion,estado_modificacion,proposito_modificacion',
                                  '$where': f"id_contrato in ({inn}) AND estado_modificacion in ('Publicado','Aprobado')",
                                  '$limit': 50000}, timeout=120)
    for r in filas:
        r['proposito_modificacion'] = (r.get('proposito_modificacion') or '')[:400]
    json.dump(filas, open(p, 'w'), ensure_ascii=False)
    return len(filas)


def main():
    ids, contratos, ix = ids_objetivo()
    lotes = [ids[i:i + LOTE] for i in range(0, len(ids), LOTE)]
    print(f'{len(ids)} contratos en {len(lotes)} lotes', file=sys.stderr, flush=True)
    with cf.ThreadPoolExecutor(int(sys.argv[sys.argv.index('--hilos') + 1]) if '--hilos' in sys.argv else 6) as ex:
        for k, n in enumerate(ex.map(lambda a: lote(*a), enumerate(lotes)), 1):
            if k % 100 == 0:
                print(f'  {k}/{len(lotes)}', file=sys.stderr, flush=True)
    por = {}
    for p in glob.glob(os.path.join(OUT, 'm-*.json')):
        for r in json.load(open(p)):
            por.setdefault(r['id_contrato'], {})[(r.get('fecha_de_aprobacion'), r.get('proposito_modificacion')[:120],
                                                  r.get('fecha_fin_contrato'))] = r
    term = {}
    for cid, mods in por.items():
        f = contratos.get(cid)
        if not f:
            continue
        fin = f[ix['fin']]
        cands = []
        for r in mods.values():
            texto = r.get('proposito_modificacion') or ''
            if not TERM.search(texto) or (NO_TERM.search(texto) and not re.search(r'ANTICIPAD|MUTUO|RENUNCI', texto, re.I)):
                continue
            ap = (r.get('fecha_de_aprobacion') or '')[:10]
            fm = (r.get('fecha_fin_contrato') or '')[:10] or None
            quien = next((q for q, rx in QUIEN if rx.search(texto)), 'sin dato')
            efectiva = fm if fm and fm <= fin else (ap if ap and ap < fin else fin)
            cands.append((ap, efectiva, quien, texto[:300]))
        if cands:
            cands.sort()
            ap, ef, quien, texto = cands[0]
            term[cid] = {'aprobada': ap, 'fin_nuevo': ef, 'fin_original': fin, 'quien': quien, 'texto': texto}
    json.dump(term, open(os.path.join(D, 'terminaciones.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'{len(por)} contratos con modificaciones · {len(term)} con terminación', file=sys.stderr)


if __name__ == '__main__':
    main()
