#!/usr/bin/env python3
"""
Caudal · empaqueta el récord de voto POR CONGRESISTA para S3 + Lambda.

Espejo de build_votaciones_camara_s3.py, pero indexado por persona: dado un
congresista, cómo votó. Toma dist/votaciones-camara-nominal.jsonl y produce
metadata/votaciones-camara-congresista.json keyed por roster_key (canónico).

Por persona: bancada · participación · alineación con la bancada de gobierno
(Pacto) en votaciones CONTESTADAS (donde min(Sí,No) ≥ 15% — las que dividen a
la plenaria; las unánimes no revelan alineación) · récord por proyecto (Sí/No/
Abstención en cada uno). Solo votos ligados a un proyecto.

La Lambda (acción `congresista`) resuelve un nombre tecleado o clickeado a su
roster_key por subconjunto de tokens, así el frontend pasa el nombre y ya.

Uso:
  python3 tools/caudal/build_congresista_s3.py
  # → Bases de datos/leyes-senado/dist/s3/votaciones-camara-congresista.json
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
    """Filas nativas + OCR DCN-SW (descarta OCR confianza 'baja')."""
    for line in open(DIST / 'votaciones-camara-nominal.jsonl', encoding='utf-8'):
        yield json.loads(line)
    ocr = DIST / 'votaciones-camara-nominal-ocr.jsonl'
    if ocr.exists():
        for line in open(ocr, encoding='utf-8'):
            r = json.loads(line)
            if r.get('confianza') == 'baja':
                continue
            yield r


def _short_titulo(t):
    t = re.sub(r'\s+', ' ', t or '').strip()
    t = re.sub(r'^POR\s+(MEDIO\s+DE\s+LA\s+CUAL|LA\s+CUAL|EL\s+CUAL|MEDIO\s+DEL\s+CUAL)\s+SE\s+', '', t, flags=re.I)
    return t[:90]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    roster = json.load(open(DIST / 'roster-autores.json', encoding='utf-8'))['roster']

    # 1) agrupar votos por votación (para calcular posición de gobierno + contestada)
    votac = collections.defaultdict(list)   # (acta,vnum) -> [(rk, resp, banc, pnc, nombre, fecha)]
    titulos = {}
    for r in _iter_rows():
        pnc = r.get('proyecto_numero_camara')
        rk = r.get('roster_key')
        if not pnc or not rk or not r.get('respuesta'):
            continue
        tok = num_token(pnc)
        if not tok:
            continue
        # OCR no trae votacion_numero → keyear por 'archivo' (único por voto)
        vkey = r.get('votacion_numero')
        if vkey is None:
            vkey = r.get('archivo') or r.get('votacion_nombre')
        votac[(r['acta_id'], vkey)].append(
            (rk, r['respuesta'], canon_bancada(r.get('partido')), tok, r.get('proyecto_titulo') or ''))
        titulos.setdefault(tok, {'numero_camara': pnc, 'id': r.get('proyecto_id'),
                                 'titulo': _short_titulo(r.get('proyecto_titulo'))})

    # 2) posición de gobierno + "contestada" por votación
    gov = {}          # (acta,vnum) -> 'Si'|'No'  (mayoría Pacto ≥60%)
    contestada = {}   # (acta,vnum) -> bool
    for key, votos in votac.items():
        pacto = [resp for (rk, resp, b, tk, ti) in votos if b == 'Pacto/izq']
        c = collections.Counter(pacto)
        if c:
            top = c.most_common(1)[0]
            if top[1] >= 0.6 * sum(c.values()):
                gov[key] = top[0]
        tally = collections.Counter(resp for (rk, resp, b, tk, ti) in votos)
        si, no = tally.get('Si', 0), tally.get('No', 0)
        contestada[key] = (si + no) > 0 and min(si, no) >= 0.15 * (si + no)

    # 3) por persona
    pers = collections.defaultdict(lambda: {
        'bancada': None, 'resumen': collections.Counter(),
        'aligned': 0, 'n_contest': 0,
        'por_proyecto': collections.defaultdict(lambda: collections.Counter()),
    })
    for key, votos in votac.items():
        gp = gov.get(key)
        cont = contestada.get(key)
        for (rk, resp, banc, tok, ti) in votos:
            p = pers[rk]
            if banc and banc not in ('Sin bancada', 'Otro'):
                p['bancada'] = banc
            elif p['bancada'] is None:
                p['bancada'] = banc
            p['resumen'][resp] += 1
            p['por_proyecto'][tok][resp] += 1
            if cont and gp:
                p['n_contest'] += 1
                if resp == gp:
                    p['aligned'] += 1

    por_congresista = {}
    for rk, p in pers.items():
        total = sum(p['resumen'].values())
        if total < 3:
            continue
        proys = []
        for tok, c in p['por_proyecto'].items():
            meta = titulos.get(tok, {})
            proys.append({'tk': tok, 'numero_camara': meta.get('numero_camara', tok),
                          'id': meta.get('id'), 'titulo': meta.get('titulo', ''),
                          'n': sum(c.values()), 'r': dict(c)})
        proys.sort(key=lambda x: -x['n'])
        por_congresista[rk] = {
            'nombre': roster.get(rk, {}).get('display', rk.title()),
            'bancada': p['bancada'],
            'n_votos': total, 'n_proyectos': len(proys),
            'resumen': dict(p['resumen']),
            'alineacion_gob': round(100 * p['aligned'] / p['n_contest']) if p['n_contest'] else None,
            'n_contestadas': p['n_contest'],
            'por_proyecto': proys,
        }

    out = {
        'meta': {
            'v': '2026-07-24', 'fuente': 'actas de plenaria de Cámara (voto nominal electrónico + OCR DCN-SW 2014-2017)',
            'rango': '2014-12 a 2026-06', 'n_congresistas': len(por_congresista),
            'alineacion': 'alineación con la bancada de gobierno (Pacto) en votaciones '
                          'CONTESTADAS (min lado ≥15%); las unánimes se excluyen',
        },
        'por_congresista': por_congresista,
    }
    outf = OUT / 'votaciones-camara-congresista.json'
    json.dump(out, open(outf, 'w', encoding='utf-8'), ensure_ascii=False)
    mb = outf.stat().st_size / 1024 / 1024
    print(f'{len(por_congresista)} congresistas · {mb:.2f} MB → {outf.relative_to(REPO)}')
    # muestra
    for rk in list(por_congresista):
        if 'BARGUIL CUBILLOS' in rk:
            p = por_congresista[rk]
            print(f'\nejemplo · {p["nombre"]} ({p["bancada"]})')
            print(f'  {p["n_votos"]} votos · alineación con gobierno {p["alineacion_gob"]}% (de {p["n_contestadas"]} contestadas)')
            print(f'  resumen: {p["resumen"]}')
            for pr in p['por_proyecto'][:5]:
                print(f'    {pr["numero_camara"]:10s} {pr["titulo"][:42]:42s} {pr["r"]}')
            break


if __name__ == '__main__':
    main()
