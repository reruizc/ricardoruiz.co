#!/usr/bin/env python3
"""
Caudal · junta lo que cosechan las entidades con sitio propio en tres índices
que la Lambda lee sin saber de qué entidad vienen.

  dist/entidades-borradores.jsonl  formato de SUCOP (lo mezcla `_sucop()`):
                                   borradores que la entidad publica FUERA de SUCOP
  dist/entidades-normas.jsonl      formato de normativa (lo mezcla `_ejecutivo()`):
                                   normas y conceptos con PDF permanente
  dist/entidades-eventos.jsonl     eventos del calendario oficial (Norte del radar)
  dist/entidades-stats.json        conteos por entidad y fuente

Cada entidad nueva es una función `fuente_*` más en FUENTES: lee su raw y
devuelve las tres listas. Los decretos y leyes NO entran a normas: ya los trae
el pilar Ejecutivo desde Presidencia y el Diario Oficial.

Uso:  python3 tools/caudal/entidades/build.py           (arma)
      python3 tools/caudal/entidades/build.py --subir   (arma y sube a S3)
"""
import argparse
import datetime
import json
import subprocess
import sys
import urllib.parse

import comun as C

BUCKET = 'caudal-legislativo'
NO_NORMAS = {'DECRETOS', 'LEYES', 'RETIRO', 'NORMOGRAMAS', 'OTRAS'}


def _u(url):
    """URL legible (sin %20): las tarjetas la codifican con encodeURI, como
    hacen con las de SUCOP; guardarla ya codificada daría %2520."""
    return urllib.parse.unquote(url or '')


def _q(*partes):
    return C.fold(' '.join(p for p in partes if p))


def borrador_sucop(r, ent, sector, fuente, hoy):
    """Un borrador cosechado → el formato de SUCOP que espera la Lambda."""
    abierta = r.get('vigente_en_fuente') and (r.get('fecha_fin') or '') >= hoy
    return {
        'id': f"{fuente}-{r['id']}", 'codigo': '', 'tipo': 'norma',
        'titulo': r['titulo'], 'objeto': r['titulo'], 'entidad': ent, 'sector': sector,
        'tipo_norma': r.get('tipo_norma') or '', 'anio': (r.get('fecha_inicio') or r.get('creado') or '')[:4],
        'estado': 'Activa' if abierta else 'Finalizada',
        'estado_fuente': ('En consulta pública' if abierta else
                          'Ya no está publicado por la entidad' if not r.get('vigente_en_fuente') else 'Cerrada'),
        'estado_vista': 'En consulta pública' if abierta else 'Consulta cerrada',
        'fecha_inicio': r.get('fecha_inicio') or '', 'fecha_fin': r.get('fecha_fin') or '',
        'comentarios': 0, 'likes': 0, 'n_documentos': 1 + len(r.get('anexos') or []),
        'url': _u(r.get('url')), 'creado': r.get('creado') or '', 'topicos': [],
        'fuente': fuente, 'fuera_de_sucop': True, 'dependencia': r.get('dependencia') or '',
        'comentarios_a': r.get('comentarios_a') or '', 'anexos': r.get('anexos') or [],
        'q': _q(r['titulo'], ent, r.get('dependencia'), r.get('tipo_norma')),
    }


def norma_ejecutivo(r, ent, fuente):
    """Una norma cosechada → el formato de normativa que mezcla el Ejecutivo."""
    desc = r.get('descripcion') or r.get('titulo')
    return {'tipo': r['tipo'], 'subtipo': r.get('subtipo') or '', 'numero': r.get('numero') or '',
            'anio': r.get('anio') or '', 'fecha': r.get('fecha') or '', 'titulo': r.get('titulo') or '',
            'descripcion': desc, 'url': _u(r.get('url')), 'entidad': ent, 'fuente': fuente,
            'administrativo': bool(r.get('administrativo', C.es_administrativo(desc))),
            'q': _q(r.get('titulo'), desc, r.get('subtema'), ent, r.get('subtipo'))}


def fuente_minsalud():
    raw = C.RAW / 'minsalud'
    ent, sector, fuente = 'Ministerio de Salud y Protección Social', 'Salud y Protección Social', 'minsalud'
    hoy = datetime.date.today().isoformat()
    borr = []
    for nombre in ('proyectos', 'ain'):
        items = (C.leer(raw / f'{nombre}.json', {}) or {}).get('items', {})
        borr += [borrador_sucop(r, ent, sector, fuente, hoy) for r in items.values()]
    normas = []
    for r in (C.leer(raw / 'normas.json', {}) or {}).get('items', []):
        if r['tipo'] in NO_NORMAS or not (r.get('titulo') or r.get('descripcion')):
            continue
        normas.append(norma_ejecutivo(r, ent, fuente))
    eventos = []
    for r in (C.leer(raw / 'eventos.json', {}) or {}).get('items', []):
        eventos.append({**r, 'entidad': ent, 'fuente': fuente,
                        'q': _q(r.get('titulo'), r.get('descripcion'), ' '.join(r.get('categorias') or []))})
    return borr, normas, eventos


def fuente_mincomercio():
    """Solo borradores por ahora (punto 3 de la fase 1); sus normas expedidas
    ya llegan por el Diario Oficial."""
    ent, sector, fuente = 'Ministerio de Comercio, Industria y Turismo', 'Comercio, Industria y Turismo', 'mincomercio'
    hoy = datetime.date.today().isoformat()
    items = (C.leer(C.RAW / 'mincomercio' / 'proyectos.json', {}) or {}).get('items', {})
    return [borrador_sucop(r, ent, sector, fuente, hoy) for r in items.values()], [], []


def fuente_ssf():
    """Supersubsidio: borradores (pocos, tabla a mano), circulares, resoluciones,
    conceptos de la relatoría, noticias y el calendario ICS."""
    raw = C.RAW / 'ssf'
    ent, sector, fuente = 'Superintendencia del Subsidio Familiar', 'Trabajo', 'ssf'
    hoy = datetime.date.today().isoformat()
    items = (C.leer(raw / 'proyectos.json', {}) or {}).get('items', {})
    borr = [borrador_sucop(r, ent, sector, fuente, hoy) for r in items.values()]
    normas = [norma_ejecutivo(r, ent, fuente) for r in (C.leer(raw / 'normas.json', {}) or {}).get('items', [])
              if r.get('descripcion') and (r.get('numero') or r.get('fecha'))]
    for nombre in ('conceptos', 'noticias'):
        normas += [norma_ejecutivo(r, ent, fuente) for r in (C.leer(raw / f'{nombre}.json', {}) or {}).get('items', [])]
    eventos = [{**e, 'entidad': ent, 'fuente': fuente,
                'q': _q(e.get('titulo'), e.get('descripcion'))}
               for e in (C.leer(raw / 'eventos.json', {}) or {}).get('items', [])]
    return borr, normas, eventos


def fuente_cce():
    """Colombia Compra: convocatorias de participación ciudadana (las que ya
    enlazan a SUCOP no se repiten), circulares, conceptos de la relatoría y
    capacitaciones."""
    raw = C.RAW / 'cce'
    ent, sector, fuente = 'Agencia Nacional de Contratación Pública · Colombia Compra Eficiente', 'Planeación', 'cce'
    hoy = datetime.date.today().isoformat()
    items = (C.leer(raw / 'proyectos.json', {}) or {}).get('items', {})
    borr = []
    for r in items.values():
        if r.get('sucop_id'):
            continue
        b = borrador_sucop(r, ent, sector, fuente, hoy)
        if r.get('objeto'):
            b['objeto'] = r['objeto']
        borr.append(b)
    # Todo lo de Colombia Compra trata de contratación estatal: un concepto sobre
    # «seguridad social» del contratista no es del tema «seguridad social» de una
    # caja de compensación. `ambito` le dice al radar que solo lo use con clientes
    # que siguen la contratación pública (ver _ambito_ok en la Lambda).
    normas = [{**norma_ejecutivo(r, ent, fuente), 'ambito': 'contratacion_publica'}
              for r in (C.leer(raw / 'normas.json', {}) or {}).get('items', []) if r.get('descripcion')]
    eventos = [{**e, 'entidad': ent, 'fuente': fuente, 'ambito': 'contratacion_publica',
                'q': _q(e.get('titulo'), e.get('descripcion'))}
               for e in (C.leer(raw / 'eventos.json', {}) or {}).get('items', [])]
    return borr, normas, eventos


def fuente_sic():
    """SIC: sus proyectos propios (los de SUCOP los deduplica la Lambda), los
    conceptos de abogacía de la competencia y sus eventos. Las circulares y
    resoluciones generales ya van por el pilar Regulatorio."""
    raw = C.RAW / 'sic'
    ent, sector, fuente = 'Superintendencia de Industria y Comercio', 'Comercio, Industria y Turismo', 'sic'
    hoy = datetime.date.today().isoformat()
    items = (C.leer(raw / 'proyectos.json', {}) or {}).get('items', {})
    borr = []
    for r in items.values():
        b = borrador_sucop(r, ent, sector, fuente, hoy)
        if r.get('objeto'):
            b['objeto'] = r['objeto']
        borr.append(b)
    normas = []
    for r in (C.leer(raw / 'normas.json', {}) or {}).get('items', []):
        n = norma_ejecutivo(r, ent, fuente)
        n['entidad_regulada'] = r.get('entidad_regulada') or ''
        normas.append(n)
    eventos = [{**e, 'entidad': ent, 'fuente': fuente, 'q': _q(e.get('titulo'), e.get('descripcion'),
                                                               ' '.join(e.get('categorias') or []))}
               for e in (C.leer(raw / 'eventos.json', {}) or {}).get('items', [])]
    return borr, normas, eventos


# Estados del Concejo que cierran el trámite (lo demás sigue vivo)
_FIN_CONCEJO = ('archiv', 'retirad', 'negad', 'sancionad', 'acumulad', 'desistid', 'hundid')


def territorial():
    """Asamblea de Antioquia y Concejo de Medellín → un índice propio
    (entidades-territorial.jsonl) para la tarjeta de Entidades territoriales y el
    radar; las sesiones del Concejo van además a los eventos."""
    raw = C.RAW / 'territorial'
    out, eventos = [], []
    hoy = datetime.date.today()
    a = C.leer(raw / 'asamblea.json', {}) or {}
    corp = 'Asamblea de Antioquia'
    for x in a.get('proyectos', []):
        try:
            viejo = (hoy - datetime.date.fromisoformat(x['fecha'])).days > 200
        except ValueError:
            viejo = True
        vivo = not x['estado'].startswith('Aprobado') and not viejo
        out.append({'corporacion': corp, 'fuente': 'asamblea-antioquia', 'tipo': 'proyecto',
                    'tipo_nombre': 'Proyecto de ordenanza', 'numero': x['numero'], 'anio': x['anio'],
                    'fecha': x['fecha'], 'titulo': x['titulo'], 'estado': x['estado'], 'en_tramite': vivo,
                    'url': _u(x['url']), 'pagina': x.get('pagina') or '', 'ordenanza': x.get('ordenanza'),
                    'q': _q(x['titulo'], x['estado'], corp)})
    for x in a.get('ordenanzas', []):
        out.append({'corporacion': corp, 'fuente': 'asamblea-antioquia', 'tipo': 'norma',
                    'tipo_nombre': 'Ordenanza', 'numero': x['numero'], 'anio': x['anio'], 'fecha': x['fecha'],
                    'titulo': x['titulo'], 'estado': 'Expedida', 'en_tramite': False, 'url': _u(x['url']),
                    'pagina': x.get('pagina') or '', 'q': _q(x['titulo'], corp, 'ordenanza')})
    c = C.leer(raw / 'concejo.json', {}) or {}
    corp = 'Concejo de Medellín'
    for x in c.get('proyectos', []):
        vivo = not any(k in C.fold(x['estado']) for k in _FIN_CONCEJO) and x['anio'] >= str(hoy.year - 1)
        out.append({'corporacion': corp, 'fuente': 'concejo-medellin', 'tipo': 'proyecto',
                    'tipo_nombre': 'Proyecto de acuerdo', 'numero': x['numero'], 'anio': x['anio'],
                    'fecha': '', 'titulo': x['titulo'], 'estado': x['estado'], 'en_tramite': vivo,
                    'url': '', 'pagina': x.get('pagina') or '', 'q': _q(x['titulo'], x['estado'], corp)})
    for x in c.get('acuerdos', []):
        out.append({'corporacion': corp, 'fuente': 'concejo-medellin', 'tipo': 'norma', 'tipo_nombre': 'Acuerdo',
                    'numero': x['numero'], 'anio': x['anio'], 'fecha': '', 'titulo': x['titulo'],
                    'estado': x['estado'], 'en_tramite': False, 'proyecto': x.get('proyecto') or '',
                    'url': '', 'pagina': x.get('pagina') or '', 'q': _q(x['titulo'], corp, 'acuerdo')})
    for x in c.get('citaciones', []):
        out.append({'corporacion': corp, 'fuente': 'concejo-medellin', 'tipo': 'citacion',
                    'tipo_nombre': 'Citación de control político', 'numero': x['codigo'], 'anio': x['fecha'][:4],
                    'fecha': x['fecha'], 'titulo': x['titulo'], 'estado': x['estado'], 'en_tramite': False,
                    'url': '', 'pagina': x.get('pagina') or '', 'q': _q(x['titulo'], corp, 'control politico')})
    for e in c.get('eventos', []):
        eventos.append({**e, 'entidad': corp, 'fuente': 'concejo-medellin',
                        'q': _q(e.get('titulo'), e.get('descripcion'), ' '.join(e.get('categorias') or []))})
    return out, eventos


def _fuente_simple(clave, ent, sector):
    """Entidad con proyectos.json (borradores), normas.json (normas y conceptos)
    y noticias.json (comunicados, sin número)."""
    def f():
        raw = C.RAW / clave
        hoy = datetime.date.today().isoformat()
        items = (C.leer(raw / 'proyectos.json', {}) or {}).get('items', {})
        borr = []
        for r in items.values():
            b = borrador_sucop(r, ent, sector, clave, hoy)
            if r.get('objeto'):
                b['objeto'] = r['objeto']
            borr.append(b)
        normas = [norma_ejecutivo(r, ent, clave)
                  for nombre in ('normas', 'noticias')
                  for r in (C.leer(raw / f'{nombre}.json', {}) or {}).get('items', []) if r.get('descripcion')]
        return borr, normas, []
    return f


fuente_supersociedades = _fuente_simple('supersociedades', 'Superintendencia de Sociedades', 'Comercio, Industria y Turismo')
fuente_superfinanciera = _fuente_simple('superfinanciera', 'Superintendencia Financiera de Colombia', 'Hacienda y Crédito Público')
fuente_supersalud = _fuente_simple('supersalud', 'Superintendencia Nacional de Salud', 'Salud y Protección Social')
fuente_mintrabajo = _fuente_simple('mintrabajo', 'Ministerio del Trabajo', 'Trabajo')
fuente_funcionpublica = _fuente_simple('funcionpublica', 'Departamento Administrativo de la Función Pública', 'Función Pública')
fuente_spe = _fuente_simple('spe', 'Unidad del Servicio Público de Empleo', 'Trabajo')
fuente_ugpp = _fuente_simple('ugpp', 'Unidad de Gestión Pensional y Parafiscales (UGPP)', 'Hacienda y Crédito Público')


FUENTES = [('minsalud', fuente_minsalud), ('mincomercio', fuente_mincomercio), ('ssf', fuente_ssf),
           ('cce', fuente_cce), ('sic', fuente_sic), ('supersociedades', fuente_supersociedades),
           ('superfinanciera', fuente_superfinanciera), ('supersalud', fuente_supersalud),
           ('mintrabajo', fuente_mintrabajo), ('funcionpublica', fuente_funcionpublica), ('spe', fuente_spe),
           ('ugpp', fuente_ugpp)]


def _es_de(alias, nombre):
    """Las siglas cortas («dian», «sena») solo como palabra completa."""
    import re
    n = C.fold(nombre)
    if not n:
        return False
    for a in alias:
        if len(a) <= 6:
            if re.search(r'\b' + re.escape(a) + r'\b', n):
                return True
        elif a in n or (len(n) >= 8 and n in a):
            return True
    return False


def catalogo(borr, normas, eventos, terr=()):
    """El catálogo de cobertura con sus conteos de hoy (ver catalogo.py)."""
    import catalogo as K
    hoy = datetime.date.today().isoformat()
    anio = hoy[:4]
    do = []
    p = C.REPO / 'Bases de datos' / 'leyes-senado' / 'ejecutivo' / 'dist' / 'diario-oficial-actos.jsonl'
    if p.exists():
        for l in p.open(encoding='utf-8'):
            r = json.loads(l)
            if r.get('anio') == anio and not r.get('administrativo') and r.get('seccion') == 'oficial':
                do.append(r.get('entidad') or '')
    out = []
    for e in K.CATALOGO:
        al = [C.fold(a) for a in e['alias']]
        c = {'diario_oficial_anio': sum(1 for x in do if _es_de(al, x)),
             'borradores_abiertos': sum(1 for b in borr if _es_de(al, b['entidad'])
                                        and b['estado'] == 'Activa'),
             'normas_anio': sum(1 for n in normas if _es_de(al, n['entidad']) and n.get('anio') == anio
                                and not n.get('administrativo')),
             'eventos_por_venir': sum(1 for v in eventos if _es_de(al, v['entidad']) and (v.get('dia') or '') >= hoy),
             'proyectos_en_tramite': sum(1 for t in terr if _es_de(al, t['corporacion']) and t['en_tramite'])}
        e = dict(e)
        # si lo único que la cubre es el Diario Oficial y este año no publicó
        # nada ahí, decir «parcial» sería prometer una cobertura que no existe
        if e['cubre'] == [K.DO] and c['diario_oficial_anio'] == 0:
            e['estado'], e['cubre'] = 'sin_fuente', []
            e['nota'] = (e['nota'] + ' ' if e['nota'] else '') + f'No publicó actos en el Diario Oficial en {anio}.'
        out.append({**e, 'alias': al, 'conteos': c})
    return {'generado': datetime.datetime.now().isoformat(timespec='seconds'), 'anio': anio, 'entidades': out}


def build():
    borr, normas, eventos, por = [], [], [], {}
    for k, fn in FUENTES:
        try:
            b, n, e = fn()
        except Exception as ex:              # una entidad rota no tumba las demás
            print(f'  ! {k}: {ex}', file=sys.stderr)
            continue
        borr += b
        normas += n
        eventos += e
        por[k] = {'borradores': len(b), 'normas': len(n), 'eventos': len(e),
                  'borradores_abiertos': sum(1 for x in b if x['estado'] == 'Activa')}
    try:
        terr, ev_terr = territorial()
    except Exception as ex:
        print(f'  ! territorial: {ex}', file=sys.stderr)
        terr, ev_terr = [], []
    eventos += ev_terr
    por['territorial'] = {'items': len(terr), 'en_tramite': sum(1 for x in terr if x['en_tramite']),
                          'eventos': len(ev_terr)}
    C.DIST.mkdir(parents=True, exist_ok=True)
    for nombre, filas, orden in (('borradores', borr, 'fecha_inicio'), ('normas', normas, 'fecha'),
                                 ('eventos', eventos, 'fecha_inicio'), ('territorial', terr, 'anio')):
        filas.sort(key=lambda r: r.get(orden) or '', reverse=True)
        with (C.DIST / f'entidades-{nombre}.jsonl').open('w', encoding='utf-8') as fh:
            for r in filas:
                fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    C.escribir(C.DIST / 'entidades-catalogo.json', catalogo(borr, normas, eventos, terr))
    stats = {'generado': datetime.datetime.now().isoformat(timespec='seconds'), 'por_fuente': por,
             'n_borradores': len(borr), 'n_normas': len(normas), 'n_eventos': len(eventos)}
    C.escribir(C.DIST / 'entidades-stats.json', stats)
    print(f"  {len(borr)} borradores · {len(normas)} normas · {len(eventos)} eventos · {len(terr)} territoriales"
          f" · fuentes: {', '.join(por)}")
    return stats


def subir(stats):
    """Sube los cuatro archivos. Cada índice tiene que traer al menos la mitad
    de lo que ya está en S3: una corrida a medias no lo encoge."""
    try:
        prev = json.loads(subprocess.run(['aws', 's3', 'cp', f's3://{BUCKET}/metadata/entidades-stats.json', '-'],
                                         capture_output=True, check=True).stdout)
    except Exception:
        prev = {}
    for k in ('n_normas', 'n_eventos'):
        if prev.get(k) and stats.get(k, 0) < prev[k] // 2:
            print(f'  ✗ {k}: {stats.get(k)} contra {prev[k]} en S3 — no se sube', file=sys.stderr)
            return False
    pt = ((prev.get('por_fuente') or {}).get('territorial') or {}).get('items', 0)
    nt = ((stats.get('por_fuente') or {}).get('territorial') or {}).get('items', 0)
    if pt and nt < pt // 2:
        print(f'  ✗ territorial: {nt} contra {pt} en S3 — no se sube', file=sys.stderr)
        return False
    for nombre in ('borradores', 'normas', 'eventos', 'territorial'):
        subprocess.run(['aws', 's3', 'cp', str(C.DIST / f'entidades-{nombre}.jsonl'),
                        f's3://{BUCKET}/metadata/entidades-{nombre}.jsonl', '--content-type', 'application/json',
                        '--cache-control', 'private, max-age=300', '--only-show-errors'], check=True)
    subprocess.run(['aws', 's3', 'cp', str(C.DIST / 'entidades-catalogo.json'),
                    f's3://{BUCKET}/metadata/entidades-catalogo.json', '--content-type', 'application/json',
                    '--cache-control', 'private, max-age=300', '--only-show-errors'], check=True)
    subprocess.run(['aws', 's3', 'cp', str(C.DIST / 'entidades-stats.json'),
                    f's3://{BUCKET}/metadata/entidades-stats.json', '--content-type', 'application/json',
                    '--cache-control', 'private, max-age=300', '--only-show-errors'], check=True)
    print('  subido a S3')
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--subir', action='store_true')
    a = ap.parse_args()
    st = build()
    if a.subir and not subir(st):
        sys.exit(1)


if __name__ == '__main__':
    main()
