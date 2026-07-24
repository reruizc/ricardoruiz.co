#!/usr/bin/env python3
"""
Caudal · empaqueta el voto nominal de Cámara para S3 + Lambda.

Toma dist/votaciones-camara-nominal.jsonl (una fila = un voto de un congresista)
y produce metadata/votaciones-camara-nominal.json, keyed por el MISMO token que
usa la Lambda (`_num_token`: "416/24"). La acción `proyecto` lo inyecta como
`ficha['voto_nominal']` de forma aditiva (no toca el `votaciones` de Congreso
Visible ni el `bloqueo`).

Por proyecto: lista de votaciones; por votación: tally global + desglose por
bancada + la lista nominal completa (congresista → Sí/No/Abstención + bancada).
Solo entran los votos LIGADOS a un proyecto (17% del total; el resto es
procedimental — orden del día, etc. — sin proyecto asociado).

Uso:
  python3 tools/caudal/build_votaciones_camara_s3.py
  # → Bases de datos/leyes-senado/dist/s3/votaciones-camara-nominal.json
"""
import json, re, collections
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DIST = REPO / 'Bases de datos' / 'leyes-senado' / 'dist'
OUT = DIST / 's3'


def canon_bancada(p):
    p = (p or '').upper()
    if 'CENTRO DEMOCR' in p: return 'Centro Democrático'
    if 'CONSERVADOR' in p: return 'Conservador'
    if 'CAMBIO RADICAL' in p: return 'Cambio Radical'
    if 'DE LA U' in p or 'UNIÓN POR LA GENTE' in p or 'UNIDAD NACIONAL' in p: return 'La U'
    if 'LIBERAL' in p and 'NUEVO' not in p: return 'Liberal'
    if 'PACTO' in p or 'COLOMBIA HUMANA' in p or 'POLO' in p or 'COMUNES' in p or 'MAIS' in p or 'PATRI' in p: return 'Pacto/izq'
    if 'VERDE' in p or 'ESPERANZA' in p or 'ALIANZA VERDE' in p: return 'Verde/Centro'
    if not p: return 'Sin bancada'
    return 'Otro'


def num_token(num):
    m = re.search(r'(\d{1,4})\s*/\s*(?:20)?(\d{2})', num or '')
    return f'{int(m.group(1))}/{m.group(2)}' if m else None


def _iter_rows():
    """Filas de voto nominal: nativas (parse_votaciones_camara) + OCR DCN-SW
    (parse_dcnsw_camara). Las OCR con confianza 'baja' se descartan; las
    demás entran marcadas con su fuente/confianza."""
    for line in open(DIST / 'votaciones-camara-nominal.jsonl', encoding='utf-8'):
        yield json.loads(line)
    ocr = DIST / 'votaciones-camara-nominal-ocr.jsonl'
    if ocr.exists():
        for line in open(ocr, encoding='utf-8'):
            r = json.loads(line)
            if r.get('confianza') == 'baja':
                continue
            yield r


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # agrupar filas por (proyecto, votación)
    votac = collections.defaultdict(lambda: {'nombre': '', 'fecha': '', 'votos': [],
                                             'fuente': 'nativa', 'confianza': None})
    for r in _iter_rows():
        pnc = r.get('proyecto_numero_camara')
        if not pnc:
            continue
        cong = r.get('congresista') or r.get('email')
        if not cong or not r.get('respuesta'):
            continue
        # OCR no trae votacion_numero → keyear por 'archivo' (único por voto)
        vkey = r.get('votacion_numero')
        if vkey is None:
            vkey = r.get('archivo') or r.get('votacion_nombre')
        key = (pnc, r['acta_id'], vkey)
        v = votac[key]
        v['nombre'] = r.get('votacion_nombre') or ''
        v['fecha'] = r.get('fecha') or ''
        if r.get('fuente', '').startswith('ocr'):
            v['fuente'] = 'ocr'
            v['confianza'] = r.get('confianza')
        v['votos'].append((cong, r['respuesta'], canon_bancada(r.get('partido')), r.get('roster_key') or ''))

    por_proyecto = {}
    n_votac, n_votos, n_votac_ocr = 0, 0, 0
    for (pnc, aid, vnum), v in votac.items():
        tok = num_token(pnc)
        if not tok:
            continue
        resumen = collections.Counter(x[1] for x in v['votos'])
        banc = collections.defaultdict(lambda: collections.Counter())
        for c, resp, b, k in v['votos']:
            banc[b][resp] += 1
        vot_obj = {
            'acta_id': aid, 'fecha': v['fecha'],
            'nombre': re.sub(r'\s+', ' ', v['nombre']).strip(),
            'resumen': dict(resumen),
            'por_bancada': {b: dict(c) for b, c in sorted(banc.items())},
            'votos': [{'c': c, 'r': resp, 'b': b, 'k': k} for c, resp, b, k in sorted(v['votos'])],
        }
        if v['fuente'] == 'ocr':
            vot_obj['fuente'] = 'ocr'          # voto recuperado por OCR (2014-2017)
            vot_obj['confianza'] = v['confianza']
            n_votac_ocr += 1
        por_proyecto.setdefault(tok, {'numero_camara': pnc, 'votaciones': []})
        por_proyecto[tok]['votaciones'].append(vot_obj)
        n_votac += 1
        n_votos += len(v['votos'])

    # ordenar votaciones de cada proyecto por fecha, y sumar contadores
    for tok, d in por_proyecto.items():
        d['votaciones'].sort(key=lambda x: (x['fecha'], x['acta_id']))
        d['n_votaciones'] = len(d['votaciones'])

    out = {
        'meta': {
            'v': '2026-07-24', 'fuente': 'actas de plenaria de Cámara (voto nominal electrónico + OCR DCN-SW 2014-2017)',
            'rango': '2014-12 a 2026-06', 'n_proyectos': len(por_proyecto),
            'n_votaciones': n_votac, 'n_votaciones_ocr': n_votac_ocr, 'n_votos': n_votos,
            'cobertura': 'solo votos de fondo ligados a un proyecto (numero_camara); '
                         'el voto procedimental sin proyecto no se incluye. Las votaciones '
                         'con "fuente":"ocr" se recuperaron por OCR de escaneos DCN-SW '
                         '(2014-2017) y llevan un flag "confianza" (alta/media).',
        },
        'por_proyecto': por_proyecto,
    }
    outf = OUT / 'votaciones-camara-nominal.json'
    json.dump(out, open(outf, 'w', encoding='utf-8'), ensure_ascii=False)
    mb = outf.stat().st_size / 1024 / 1024
    print(f'{len(por_proyecto)} proyectos · {n_votac} votaciones · {n_votos:,} votos')
    print(f'→ {outf.relative_to(REPO)} ({mb:.2f} MB)')
    # muestra
    tok = '416/24' if '416/24' in por_proyecto else next(iter(por_proyecto))
    p = por_proyecto[tok]
    print(f'\nejemplo proyecto {tok} ({p["numero_camara"]}): {p["n_votaciones"]} votaciones')
    v0 = p['votaciones'][-1]
    print(f'  última votación: {v0["nombre"][:60]}  [{v0["fecha"]}]')
    print(f'  resumen: {v0["resumen"]}')
    print(f'  por bancada: {v0["por_bancada"]}')
    print(f'  nominal (2): {v0["votos"][:2]}')


if __name__ == '__main__':
    main()
