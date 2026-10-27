#!/usr/bin/env python3
"""
Caudal · Superintendencia de Sociedades · conceptos jurídicos (fase 2, oct-2026).

Sus sanciones y normas ya entran por el pilar Regulatorio. Esto suma la
doctrina: el Tesauro (tesauro.supersociedades.gov.co) se alimenta de un
Elasticsearch abierto,

  POST https://admin.es.prod.ssociedades.nuvu.cc/index_thesaurus/_search

que mezcla 13.002 «Conceptos jurídicos» con sentencias (1.526) y «Temas y
problemas» (209). Se piden solo los conceptos, ordenados por
`informacion.fecha_sentencia` y paginados con `search_after` (el índice no deja
pasar de 10.000 con from/size). El detalle público de cada uno está en
`tesauro.supersociedades.gov.co/jsonviewer/{id_relatoria}`.

⚠️ El calendario de eventos (`micro-calendario-evento/…/consultarEventosMes`)
responde 500 «Ha ocurrido un error» en todos los meses (medido el 27-oct-2026):
no se usa.
⚠️ La relatoría va con rezago: el concepto más reciente es del 24-mar-2026.

Salida: `Bases de datos/caudal-entidades/raw/supersociedades/normas.json`
(acumulado por id; sin `--todo`, solo lo de los últimos 120 días).
Uso: python3 tools/caudal/entidades/harvest_supersociedades.py fetch [--todo]
"""
import argparse
import datetime
import json
import subprocess
import sys

import comun as C

ES = 'https://admin.es.prod.ssociedades.nuvu.cc/index_thesaurus/_search'
OUT = C.RAW / 'supersociedades'
VISOR = 'https://tesauro.supersociedades.gov.co/jsonviewer/'


def _post(cuerpo):
    r = subprocess.run(['/usr/bin/curl', '-s', '--max-time', '90', '-A', C.UA, '-H', 'Content-Type: application/json',
                        '-X', 'POST', ES, '-d', json.dumps(cuerpo)], capture_output=True, timeout=120)
    d = json.loads(r.stdout.decode('utf-8', 'replace') or '{}')
    if 'error' in d:
        raise RuntimeError(str(d['error'])[:200])
    return d


def conceptos(desde=None):
    q = {'bool': {'filter': [{'term': {'informacion.tipo_contenido.keyword': 'Conceptos jurídicos'}}]}}
    if desde:
        q['bool']['filter'].append({'range': {'informacion.fecha_sentencia': {'gte': desde}}})
    base = {'size': 1000, 'query': q,
            '_source': ['titulo', 'informacion', 'id_relatoria', 'descriptores', 'fuentes_juridicas'],
            'sort': [{'informacion.fecha_sentencia': {'order': 'desc'}}, {'id_relatoria.keyword': {'order': 'desc'}}]}
    out, after = [], None
    for _ in range(40):
        cuerpo = dict(base)
        if after:
            cuerpo['search_after'] = after
        hits = _post(cuerpo).get('hits', {}).get('hits', [])
        if not hits:
            break
        for h in hits:
            s = h['_source']
            inf = s.get('informacion') or {}
            fecha = (inf.get('fecha_sentencia') or '')[:10]
            desc = [d.get('descriptor_principal', '') + (': ' + ', '.join(d.get('descriptores_secundarios') or [])
                                                         if d.get('descriptores_secundarios') else '')
                    for d in (s.get('descriptores') or [])]
            fuentes = [f.get('fuente') for f in (s.get('fuentes_juridicas') or []) if f.get('fuente')]
            titulo = C.limpio(s.get('titulo') or '')
            out.append({'id': s.get('id_relatoria'), 'tipo': 'CONCEPTOS', 'subtipo': 'Concepto jurídico',
                        'numero': (inf.get('consecutivo') or '').strip(), 'anio': fecha[:4], 'fecha': fecha,
                        'titulo': f"Concepto {inf.get('consecutivo') or ''}".strip(),
                        'descripcion': titulo[:1].upper() + titulo[1:].lower() if titulo.isupper() else titulo,
                        'subtema': ' · '.join(desc + fuentes[:4]),
                        'url': VISOR + str(s.get('id_relatoria')) if s.get('id_relatoria') else ''})
        after = hits[-1].get('sort')
        if len(hits) < base['size']:
            break
    return out


def fetch(todo):
    OUT.mkdir(parents=True, exist_ok=True)
    prev = {str(x['id']): x for x in ((C.leer(OUT / 'normas.json', {}) or {}).get('items') or [])}
    desde = None if (todo or not prev) else (datetime.date.today() - datetime.timedelta(days=120)).isoformat()
    try:
        nuevos = conceptos(desde)
    except Exception as e:
        print(f'  supersociedades · FALLÓ ({e}) — se conserva el archivo anterior', file=sys.stderr)
        return False
    for x in nuevos:
        prev[str(x['id'])] = x
    if len(prev) < 5000:
        print(f'  supersociedades · solo {len(prev)} conceptos: no se escribe', file=sys.stderr)
        return False
    items = sorted(prev.values(), key=lambda x: x['fecha'], reverse=True)
    C.escribir(OUT / 'normas.json', {'generado': datetime.datetime.now().isoformat(timespec='seconds'), 'items': items})
    print(f"  supersociedades · {len(items)} conceptos ({len(nuevos)} leídos hoy) · el más reciente del {items[0]['fecha']}")
    return True


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('fetch')
    f.add_argument('--todo', action='store_true')
    a = ap.parse_args()
    if a.cmd == 'fetch':
        sys.exit(0 if fetch(a.todo) else 1)


if __name__ == '__main__':
    main()
