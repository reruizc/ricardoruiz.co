#!/usr/bin/env python3
"""
Enriquece el crudo de harvest.py (pdly/lys/pal/actos .jsonl) al dataset que
consume el producto Cauce. Deriva campos que el frontend/Lambda necesitan y
que sería caro recalcular en cada request:

  - fechas parseadas + validadas (descarta typos con años imposibles)
  - resultado normalizado: LEY | ARCHIVADO_TIEMPO | ARCHIVADO_OTRO | RETIRADO
                           | EN_TRAMITE | OTRO
  - es_ley, murio_por_tiempo (Art. 190)
  - etapa_max: hasta dónde llegó en el trámite (0 presentado … 5 ley)
  - dias_a_primer_debate
  - autores: lista separada + n_autores (para el futuro join autor→partido)
  - gacetas: lista estructurada [{tipo, numero, url}] desde las 6 filas de docs

Salidas (en Bases de datos/leyes-senado/dist/, listo para S3 privado):
  proyectos.jsonl   pdly enriquecido, 1 registro/línea  (backend/Lambda)
  leyes.jsonl       lys enriquecido
  actos-legis.jsonl pal + actos enriquecido
  indice.json       índice compacto de TODO (búsqueda rápida en memoria)
  stats.json        agregados precalculados (embudo, resultados por año/comisión)

Uso: python3 tools/leyes-senado/build_dataset.py
"""
import json
import re
import sys
import datetime
from pathlib import Path
from collections import Counter, defaultdict

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / 'Bases de datos' / 'leyes-senado'
DIST = SRC / 'dist'

sys.path.insert(0, str(REPO / 'tools' / 'caudal'))
import normalize_autores as na  # noqa: E402

# registro global de autores (clave→display); se llena en main() antes de enrich
AUTOR_REG = {}

MESES = 366 * 250  # sanity cap irrelevante; placeholder


def pdate(s):
    if not s:
        return None
    s = s.strip()
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            d = datetime.datetime.strptime(s[:10], fmt).date()
            if 1985 <= d.year <= 2027:
                return d
        except ValueError:
            pass
    return None


def norm_resultado(estado):
    e = (estado or '').upper()
    if e.startswith('LEY') or 'SANCION' in e:
        return 'LEY'
    if 'RETIR' in e:
        return 'RETIRADO'
    if 'ARCHIV' in e and '190' in e:
        return 'ARCHIVADO_TIEMPO'
    if 'ARCHIV' in e:
        return 'ARCHIVADO_OTRO'
    if any(k in e for k in ('PENDIENTE', 'TRAMITE', 'PONENCIA', 'DEBATE', 'DISCUTIR')):
        return 'EN_TRAMITE'
    return 'OTRO' if e else 'SIN_DATO'


# separa "H.S. NOMBRE UNO, NOMBRE DOS, H.R. NOMBRE TRES." en nombres individuales
AUTOR_PREF = re.compile(r'\b(H\.?\s?[SR]\.?|HONORABLE|SENADOR(?:A)?|REPRESENTANTE|MIN(?:ISTRO|ISTERIO)?(?:\s+DE[^,]*)?)\.?\s*', re.I)


def split_autores(autor):
    if not autor:
        return []
    txt = autor.strip().rstrip('.')
    # corta por coma o " Y " pero deja nombres compuestos razonables
    partes = re.split(r'\s*,\s*|\s+Y\s+(?=[A-ZÁÉÍÓÚÑ])', txt)
    out = []
    for p in partes:
        p = AUTOR_PREF.sub('', p).strip(' .')
        p = re.sub(r'\s+', ' ', p)
        if len(p) >= 4 and not p.isdigit():
            out.append(p.title())
    # dedup preservando orden
    seen = set()
    return [x for x in out if not (x in seen or seen.add(x))]


DOC_FIELDS = [
    ('exposicion_de_motivos', 'exposicion_motivos'),
    ('primera_ponencia', 'ponencia_1'),
    ('segunda_ponencia', 'ponencia_2'),
    ('texto_plenaria', 'texto_plenaria'),
    ('conciliacion', 'conciliacion'),
    ('objeciones', 'objeciones'),
]
GACETA_RE = re.compile(r'(\d{1,4})\s*/\s*(\d{2,4})')


def extract_gacetas(rec):
    out = []
    for field, tipo in DOC_FIELDS:
        val = (rec.get(field) or '').strip()
        if not val:
            continue
        m = GACETA_RE.search(val)
        numero = None
        if m:
            yy = m.group(2)
            anio = ('20' if int(yy) <= 27 else '19') + yy if len(yy) == 2 else yy
            numero = f'{int(m.group(1))}/{anio}'
        out.append({'tipo': tipo, 'gaceta': numero, 'texto': val,
                    'url': rec.get(f'{field}_url', '')})
    return out


def _autores_canon(raw):
    """Campo autor crudo → autores canónicos + keys + tipo, usando AUTOR_REG."""
    p = na.procesar_campo(raw)
    if p['tipo'] == 'institucional':
        return {'autor_tipo': 'institucional', 'entidad': p['entidad'],
                'autores': [], 'autores_keys': []}
    disp = [AUTOR_REG.get(k, {}).get('display', d) for k, d in p['personas']]
    return {'autor_tipo': 'persona', 'entidad': None,
            'autores': disp, 'autores_keys': [k for k, _ in p['personas']]}


ETAPAS = [
    ('presentado', 'fecha_de_presentacion'),
    ('1er_debate_senado', 'fecha_de_aprobacion_primer_debate'),
    ('2do_debate_senado', 'fecha_de_aprobacion_segundo_debate'),
    ('1er_debate_camara', 'fecha_de_aprobacion_primer_debate_camara'),
    ('2do_debate_camara', 'fecha_de_aprobacion_segundo_debate_camara'),
]


def enrich_pdly(rec):
    res = norm_resultado(rec.get('estado', ''))
    fpres = pdate(rec.get('fecha_de_presentacion', ''))
    f1 = pdate(rec.get('fecha_de_aprobacion_primer_debate', ''))
    etapa_max = 0
    for idx, (_, k) in enumerate(ETAPAS):
        if pdate(rec.get(k, '')):
            etapa_max = idx
    if res == 'LEY':
        etapa_max = 5
    leg = rec.get('legislatura', '')
    anio = int(leg[:4]) if leg[:4].isdigit() else (fpres.year if fpres else None)
    return {
        'id': rec['id'],
        'titulo': rec.get('titulo', ''),
        'numero_senado': rec.get('numero_senado', ''),
        'numero_camara': rec.get('numero_camara', ''),
        'legislatura': leg,
        'cuatrienio': rec.get('cuatrenio', ''),
        'anio': anio,
        'origen': rec.get('origen', ''),
        'tipo_de_ley': rec.get('tipo_de_ley', ''),
        'comision': rec.get('comision', ''),
        'autor_raw': rec.get('autor', ''),
        **_autores_canon(rec.get('autor', '')),
        'estado': rec.get('estado', ''),
        'resultado': res,
        'es_ley': res == 'LEY',
        'murio_por_tiempo': res == 'ARCHIVADO_TIEMPO',
        'etapa_max': etapa_max,
        'fecha_presentacion': fpres.isoformat() if fpres else None,
        'fecha_primer_debate': f1.isoformat() if f1 else None,
        'dias_a_primer_debate': (f1 - fpres).days if (fpres and f1 and f1 >= fpres) else None,
        'ponentes': [rec.get(k, '') for k in
                     ('ponente_primer_debate', 'ponente_segundo_debate',
                      'ponente_primer_debate_camara', 'ponente_segundo_debate_camara')
                     if rec.get(k, '').strip()],
        'gacetas': extract_gacetas(rec),
    }


def enrich_pal(rec):
    """Proyectos de acto legislativo (reformas constitucionales, doble vuelta).
    Enriquecido más liviano que pdly — comparten título/autor/estado."""
    res = norm_resultado(rec.get('estado', ''))
    leg = rec.get('legislatura', '')
    anio = int(leg[:4]) if leg[:4].isdigit() else None
    return {
        'id': rec['id'], 'tabla': 'pal',
        'titulo': rec.get('titulo', ''),
        'numero_senado': rec.get('numero_senado', ''),
        'numero_camara': rec.get('numero_camara', ''),
        'legislatura': leg, 'anio': anio,
        'origen': rec.get('origen', ''),
        'autor_raw': rec.get('autor', ''),
        **_autores_canon(rec.get('autor', '')),
        'estado': rec.get('estado', ''),
        'resultado': res, 'es_ley': res == 'LEY',
        'murio_por_tiempo': res == 'ARCHIVADO_TIEMPO',
        'gacetas': extract_gacetas(rec),
    }


def enrich_lys(rec):
    return {
        'id': rec['id'], 'tipo': 'ley_sancionada',
        'titulo': rec.get('titulo', ''),
        'numero_ley': rec.get('numero_ley', ''),
        'numero_senado': rec.get('numero_senado', ''),
        'numero_camara': rec.get('numero_camara', ''),
        'origen': rec.get('origen', ''),
        'fecha_sancion': (pdate(rec.get('fecha_de_sancion', '')) or '') and
                         pdate(rec.get('fecha_de_sancion', '')).isoformat(),
        'presidente_congreso': rec.get('presidente_del_congreso', ''),
        'proyecto_ref_id': rec.get('numero_senado_ref_id') or rec.get('numero_camara_ref_id'),
    }


def load(name):
    p = SRC / f'{name}.jsonl'
    return [json.loads(l) for l in open(p, encoding='utf-8')] if p.exists() else []


def main():
    DIST.mkdir(parents=True, exist_ok=True)
    raw_pdly, raw_pal = load('pdly'), load('pal')

    # 1) registro global de autores (dedup por clave canónica) ANTES de enrich
    global AUTOR_REG
    AUTOR_REG = na.construir_registro(raw_pdly + raw_pal)

    pdly = [enrich_pdly(r) for r in raw_pdly]
    pal = [enrich_pal(r) for r in raw_pal]
    lys = [enrich_lys(r) for r in load('lys')]

    # registro de autores como salida propia (para el join autor→partido)
    autores_out = sorted(
        ({'key': k, 'display': v['display'], 'tipo': v['tipo'],
          'n_proyectos': v['n_proyectos'], 'n_variantes': v['n_variantes']}
         for k, v in AUTOR_REG.items()),
        key=lambda x: -x['n_proyectos'])
    json.dump({'v': '2026-07-11', 'n': len(autores_out), 'autores': autores_out},
              open(DIST / 'autores.json', 'w', encoding='utf-8'), ensure_ascii=False)

    # proyectos enriquecidos
    with open(DIST / 'proyectos.jsonl', 'w', encoding='utf-8') as f:
        for r in pdly:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    with open(DIST / 'actos-legis.jsonl', 'w', encoding='utf-8') as f:
        for r in pal:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    with open(DIST / 'leyes.jsonl', 'w', encoding='utf-8') as f:
        for r in lys:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    # índice compacto (búsqueda en memoria · frontend/Lambda) — pdly + pal
    indice = [{
        'id': r['id'], 'tb': 'pdly', 't': r['titulo'], 'a': r['anio'], 'leg': r['legislatura'],
        'com': r['comision'], 'res': r['resultado'], 'ley': r['es_ley'],
        'et': r['etapa_max'], 'aut': r['autores'][:6], 'ak': r['autores_keys'][:6],
        'ng': len(r['gacetas']),
    } for r in pdly] + [{
        'id': r['id'], 'tb': 'pal', 't': r['titulo'], 'a': r['anio'], 'leg': r['legislatura'],
        'com': '', 'res': r['resultado'], 'ley': r['es_ley'],
        'et': 5 if r['es_ley'] else 0, 'aut': r['autores'][:6], 'ak': r['autores_keys'][:6],
        'ng': len(r['gacetas']),
    } for r in pal]
    json.dump({'v': '2026-07-10', 'n': len(indice), 'proyectos': indice},
              open(DIST / 'indice.json', 'w', encoding='utf-8'), ensure_ascii=False)

    # stats precalculadas
    res_count = Counter(r['resultado'] for r in pdly)
    por_anio = defaultdict(lambda: Counter())
    for r in pdly:
        if r['anio']:
            por_anio[r['anio']][r['resultado']] += 1
    por_comision = defaultdict(lambda: {'total': 0, 'ley': 0})
    for r in pdly:
        c = (r['comision'] or 'SIN COMISIÓN').upper().strip()
        por_comision[c]['total'] += 1
        por_comision[c]['ley'] += r['es_ley']
    # embudo
    embudo = {name: sum(1 for r in pdly if r['etapa_max'] >= idx)
              for idx, (name, _) in enumerate(ETAPAS)}
    embudo['ley'] = sum(1 for r in pdly if r['es_ley'])
    # días a primer debate
    dias = sorted(r['dias_a_primer_debate'] for r in pdly if r['dias_a_primer_debate'] is not None)
    stats = {
        'v': '2026-07-10', 'n_proyectos': len(pdly), 'n_leyes': len(lys),
        'resultados': dict(res_count),
        'embudo': embudo,
        'dias_a_primer_debate': {
            'n': len(dias),
            'mediana': dias[len(dias) // 2] if dias else None,
            'p25': dias[len(dias) // 4] if dias else None,
            'p75': dias[3 * len(dias) // 4] if dias else None,
        },
        'por_comision': {k: v for k, v in sorted(
            por_comision.items(), key=lambda x: -x[1]['total'])},
        'por_anio': {str(a): dict(c) for a, c in sorted(por_anio.items())},
    }
    json.dump(stats, open(DIST / 'stats.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    n_pers = sum(1 for a in autores_out if a['tipo'] == 'persona')
    print(f'proyectos.jsonl : {len(pdly)} enriquecidos')
    print(f'leyes.jsonl     : {len(lys)}')
    print(f'indice.json     : {len(indice)} (compacto)')
    print(f'autores.json    : {n_pers} personas canónicas + {len(autores_out)-n_pers} entidades')
    print(f'stats.json      : embudo + {len(por_comision)} comisiones + {len(por_anio)} años')
    for k in ('proyectos.jsonl', 'leyes.jsonl', 'indice.json', 'autores.json', 'stats.json'):
        sz = (DIST / k).stat().st_size
        print(f'  {k:16} {sz/1024:7.1f} KB')


if __name__ == '__main__':
    main()
