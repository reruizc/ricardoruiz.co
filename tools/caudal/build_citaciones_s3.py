#!/usr/bin/env python3
"""
Caudal · empaqueta las CITACIONES DE CONTROL POLÍTICO para S3 + Lambda.

Consolida los citaciones-{camara}-{ambito}.json que emite
tools/caudal/actas/harvest_citaciones.py y produce, en un solo archivo:

  por_congresista : qué citó cada persona, a quién y sobre qué (keyed por
                    roster_key, la misma llave que el récord de voto → la ficha
                    del congresista muestra las dos cosas sin resolver nada)
  por_citado      : a quién se cita más (los ministros con más citaciones)
  sistema         : agregados para el landing + la COBERTURA declarada

⚠️ La cobertura NO es pareja y por eso viaja en el JSON, no en un comentario:
hay comisiones que sencillamente no agendan control político en su orden del día
publicado (medido: la Primera de Cámara, 0 de 572 documentos) y ámbitos del
Senado sin serie completa. Un consumidor que vea "0 citaciones" tiene que poder
distinguir "no citó" de "esta comisión no publica eso".

Uso:
  python3 tools/caudal/actas/harvest_citaciones.py todas   # primero
  python3 tools/caudal/build_citaciones_s3.py
  # → Bases de datos/leyes-senado/dist/s3/citaciones.json
"""
import json, glob, re, collections
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / 'Bases de datos' / 'leyes-senado'
ACTAS = SRC / 'actas'
DIST = SRC / 'dist'
OUT = DIST / 's3'


def canon_bancada(p):
    """Mismo colapso de partidos que build_congresista_s3.py — para que la
    bancada que muestra el panel de citaciones sea la misma que la del voto."""
    p = (p or '').upper()
    if 'CENTRO DEMOCR' in p: return 'Centro Democrático'
    if 'CONSERVADOR' in p: return 'Conservador'
    if 'CAMBIO RADICAL' in p: return 'Cambio Radical'
    if 'DE LA U' in p or 'UNIÓN POR LA GENTE' in p or 'UNIDAD NACIONAL' in p: return 'La U'
    if 'LIBERAL' in p and 'NUEVO' not in p: return 'Liberal'
    if ('PACTO' in p or 'COLOMBIA HUMANA' in p or 'POLO' in p or 'COMUNES' in p
            or 'MAIS' in p or 'PATRI' in p): return 'Pacto/izq'
    if 'VERDE' in p or 'ESPERANZA' in p: return 'Verde/Centro'
    if not p: return 'Sin bancada'
    return 'Otro'


def norm_ent(s):
    return re.sub(r'\s+', ' ', (s or '').strip()).upper()


# El wrap de columna del PDF parte palabras ("Contralor General de la R epública",
# "Ministro de Minas y Ene rgía"). Se repara SOLO contra un vocabulario cerrado de
# cargos: unir dos tokens cualesquiera porque el segundo arranque en minúscula
# rompería "Minas y Energía" → "yEnergía".
_VOCAB = set("""republica nacion nacional energia hacienda publico publica credito
ambiente sostenible general ministro ministra viceministro viceministra
superintendente director directora presidente presidenta gerente procurador
procuradora contralor contralora defensor registrador agricultura transporte
desarrollo rural interior justicia salud educacion trabajo comercio vivienda
cultura deporte ciencia tecnologia igualdad colombia instituto agencia
departamento planeacion ejecutivo delegado comision regulacion servicios
domiciliarios infraestructura ejecutiva""".split())


def _plain(w):
    import unicodedata
    w = unicodedata.normalize('NFD', w.lower())
    return ''.join(c for c in w if c.isalpha() and unicodedata.category(c) != 'Mn')


def dewrap(s):
    toks = (s or '').split()
    out = []
    i = 0
    while i < len(toks):
        if i + 1 < len(toks) and _plain(toks[i] + toks[i + 1]) in _VOCAB:
            out.append(toks[i] + toks[i + 1])
            i += 2
        else:
            out.append(toks[i])
            i += 1
    return ' '.join(out).strip(' ,.;:')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    roster = json.load(open(DIST / 'roster-autores.json', encoding='utf-8'))['roster']

    per = collections.defaultdict(lambda: {
        'citaciones': [], 'citados': collections.Counter(), 'n_agend': 0})
    citados = collections.defaultdict(lambda: {
        'cargos': collections.Counter(), 'n': 0, 'n_agend': 0, 'citantes': set()})
    cobertura, por_anio, por_ambito = [], collections.Counter(), collections.Counter()
    n_cit = n_sin_citante = 0

    for f in sorted(glob.glob(str(ACTAS / 'citaciones-*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        cam, amb = d['camara'], d['ambito']
        cobertura.append({
            'camara': cam, 'ambito': amb, 'n_docs': d['n_docs'],
            'n_docs_cp': d['n_docs_cp'], 'n_citaciones': d['n_citaciones'],
            # sin esto, "0 citaciones" se leería como "nadie citó" cuando en
            # realidad la comisión no publica control político en su agenda
            'publica_control_politico': d['n_docs_cp'] > 0,
        })
        for k, r in d['citaciones'].items():
            n_cit += 1
            por_ambito[f'{cam}/{amb}'] += 1
            if r.get('primera'):
                por_anio[r['primera'][:4]] += 1
            if not r['citantes']:
                n_sin_citante += 1

            cit_nom = [c for c in r['citados'] if c.get('nombre')]
            etiqueta = dewrap(cit_nom[0]['nombre'] if cit_nom
                              else (r['citados'][0]['cargo'] if r['citados'] else '—'))
            item = {
                'k': k, 'camara': cam, 'ambito': amb,
                'proposicion': r.get('proposicion'),
                'tema': r.get('tema') or '',
                'citados': [{'nombre': dewrap(c['nombre']) if c.get('nombre') else None,
                             'cargo': dewrap(c.get('cargo'))}
                            for c in r['citados'][:4]],
                'n': r['n'], 'primera': r.get('primera'), 'ultima': r.get('ultima'),
            }
            # Una persona puede venir DOS VECES en la misma citación: el wrap del
            # PDF parte el nombre ("Manuel"→"Manu") y las dos variantes casan al
            # mismo roster_key. Sin deduplicar por rk, su citación aparecía
            # repetida en la ficha y `n_agendamientos` salía inflado.
            for rk in dict.fromkeys(c['rk'] for c in r['citantes']):
                p = per[rk]
                p['citaciones'].append(item)
                p['citados'][etiqueta] += 1
                p['n_agend'] += r['n']
            for c in r['citados']:
                key = norm_ent(c.get('nombre') or c.get('cargo'))
                if not key:
                    continue
                e = citados[key]
                e['nombre'] = dewrap(c.get('nombre') or c.get('cargo'))
                if c.get('cargo'):
                    # el cargo MÁS FRECUENTE, no el más largo: tomando el más
                    # largo, un solo mal emparejamiento cargo↔nombre le cambiaba
                    # la cartera a un ministro (Carrasquilla salía de Ambiente)
                    e['cargos'][dewrap(c['cargo'])] += 1
                e['n'] += 1
                e['n_agend'] += r['n']
                e['citantes'].update(x['rk'] for x in r['citantes'])

    por_congresista = {}
    for rk, p in per.items():
        info = roster.get(rk, {})
        cs = sorted(p['citaciones'], key=lambda x: (x['primera'] or ''), reverse=True)
        por_congresista[rk] = {
            'nombre': info.get('display', rk.title()),
            'partido': info.get('partido_principal'),
            'bancada': canon_bancada(info.get('partido_principal')),
            'n_citaciones': len(cs),
            'n_agendamientos': p['n_agend'],
            'citados_top': [{'nombre': n, 'n': c} for n, c in p['citados'].most_common(6)],
            'citaciones': cs[:60],
        }

    por_citado = {}
    for k, e in sorted(citados.items(), key=lambda kv: -kv[1]['n'])[:400]:
        cargo = e['cargos'].most_common(1)[0][0] if e['cargos'] else ''
        por_citado[k] = {'nombre': e['nombre'], 'cargo': cargo, 'n': e['n'],
                         'n_agendamientos': e['n_agend'], 'n_citantes': len(e['citantes'])}

    top_cit = sorted(por_congresista.items(), key=lambda kv: -kv[1]['n_citaciones'])[:40]
    out = {
        'meta': {
            'v': '2026-08-05',
            'fuente': 'órdenes del día de comisiones y plenarias (Cámara wp-json · Senado DOCman + secretariasenado)',
            'unidad': 'citación agendada en el orden del día',
            'ojo': 'es la citación AGENDADA, no el debate realizado; `n` es cuántas '
                   'sesiones la agendaron (una citación agendada muchas veces y nunca '
                   'realizada es la señal, no un error)',
            'n_citaciones': n_cit,
            'n_congresistas': len(por_congresista),
            'n_citados': len(citados),
            'n_citaciones_sin_citante_identificado': n_sin_citante,
        },
        'sistema': {
            'cobertura': sorted(cobertura, key=lambda c: -c['n_citaciones']),
            'por_ambito': [{'ambito': k, 'n': v} for k, v in por_ambito.most_common()],
            'por_anio': [{'anio': a, 'n': por_anio[a]} for a in sorted(por_anio)],
            'top_citantes': [{'rk': k, 'nombre': v['nombre'], 'bancada': v['bancada'],
                              'n': v['n_citaciones']} for k, v in top_cit],
            'top_citados': [{'nombre': v['nombre'], 'cargo': v['cargo'], 'n': v['n']}
                            for v in list(por_citado.values())[:25]],
        },
        'por_congresista': por_congresista,
        'por_citado': por_citado,
    }
    outf = OUT / 'citaciones.json'
    json.dump(out, open(outf, 'w', encoding='utf-8'), ensure_ascii=False)
    kb = outf.stat().st_size / 1024
    print(f'{n_cit} citaciones · {len(por_congresista)} congresistas · '
          f'{len(citados)} citados · {kb:.0f} KB → {outf.relative_to(REPO)}')
    print(f'  citaciones sin citante identificado: {n_sin_citante} '
          f'({n_sin_citante * 100 // max(n_cit, 1)}%)')
    print('\n  top citantes:')
    for k, v in top_cit[:12]:
        print(f'    {v["n_citaciones"]:3d}  {v["nombre"]:38s} {v["bancada"]}')
    print('\n  más citados:')
    for v in list(por_citado.values())[:8]:
        print(f'    {v["n"]:3d}  {(v["nombre"] or "")[:40]:40s} {v["cargo"][:40]}')


if __name__ == '__main__':
    main()
