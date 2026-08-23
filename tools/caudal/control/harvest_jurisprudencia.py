#!/usr/bin/env python3
"""Cosecha trazable de jurisprudencia para Caudal.

Fuentes primarias, sin LLM: Mi Relatoría/SAMAI del Consejo de Estado y el
buscador oficial de la Corte Constitucional. ``fetch`` guarda el crudo
normalizado; ``build`` produce el JSONL slim y los agregados para la Lambda.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import unicodedata
from collections import Counter
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DATA = REPO / 'Bases de datos' / 'leyes-senado' / 'control'
RAW = DATA / 'raw' / 'jurisprudencia.jsonl'
OUT = DATA / 'dist' / 's3'
SAMAI = 'https://samai.consejodeestado.gov.co/TitulacionRelatoria/BuscadorProvidenciasTituladas.aspx'
CORTE = 'https://www.corteconstitucional.gov.co/relatoria/buscador_new/index.php'
DEFAULT_QUERIES = ('contratación estatal', 'salud', 'pensiones', 'ambiente', 'elecciones')
HEADERS = {'User-Agent': 'Caudal/1.0 (+https://ricardoruiz.co)'}


def clean(value: str) -> str:
    return ' '.join(unescape(value or '').split())


def fold(value: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', (value or '').lower())
                   if unicodedata.category(c) != 'Mn')


def fecha(value: str) -> str:
    for pat in (r'(\d{4}-\d{2}-\d{2})', r'(\d{2}/\d{2}/\d{4})'):
        m = re.search(pat, value or '')
        if m:
            try:
                return dt.datetime.strptime(m.group(1), '%Y-%m-%d' if '-' in m.group(1) else '%d/%m/%Y').date().isoformat()
            except ValueError:
                pass
    return ''


def corte(query: str, session: requests.Session) -> list[dict]:
    payload = {'accion': 'search', 'verform': 'si', 'slop': '1', 'buscador': 'buscador',
               'qu': '286', 'maxprov': '100', 'OrderbyOption': 'des__score',
               'searchOption': 'texto', 'buscar_por': query, 'fini': '2021-01-01',
               'ffin': dt.date.today().isoformat()}
    response = session.post(CORTE, data=payload, timeout=75)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    rows = []
    for tr in soup.select('#div_resultado_tabla tr'):
        link = tr.select_one('a[href*="/relatoria/"][title*="providencia"]')
        cells = [clean(x.get_text(' ', strip=True)) for x in tr.select('td')]
        if not link or len(cells) < 3:
            continue
        titulo = clean(link.get_text())
        rows.append({'fuente': 'corte_constitucional', 'fuente_nombre': 'Corte Constitucional',
                     'tipo': 'Auto' if titulo.upper().startswith('A') else 'Sentencia',
                     'identificador': titulo, 'fecha': fecha(' '.join(cells)),
                     'tema': query, 'titulo': f'{titulo} · Corte Constitucional',
                     'resumen': clean(' · '.join(cells[2:]))[:700],
                     'url': urljoin(CORTE, link.get('href', '')), 'consulta': query})
    return rows


def consejo(query: str, session: requests.Session) -> list[dict]:
    initial = session.get(SAMAI, timeout=35)
    initial.raise_for_status()
    form = BeautifulSoup(initial.text, 'html.parser')
    payload = {i['name']: i.get('value', '') for i in form.select('input[type="hidden"][name]')}
    payload.update({'ctl00$MainContent$BusquedaRapidaTextBox': query,
                    '__EVENTTARGET': 'ctl00$MainContent$BusquedaRapidaLinkButton'})
    response = session.post(SAMAI, data=payload, timeout=75)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    rows = []
    for node in soup.select('[id*="HypRadicado_"]'):
        index = re.search(r'_(\d+)$', node.get('id', ''))
        if not index:
            continue
        n = index.group(1)
        document = soup.find(id=re.compile(rf'documentlink_{n}$'))
        found = re.search(r"CargarVentana\('([^']+)'", document.get('onclick', '') if document else '')
        if not found:
            continue
        problema = soup.find(id=re.compile(rf'ProblemaJuridicoLabel_{n}_'))
        f = soup.find(id=re.compile(rf'Label1_{n}$'))
        sala = soup.find(id=re.compile(rf'LbNombreSalaDecision_{n}$'))
        radicado = clean(node.get_text())
        rows.append({'fuente': 'consejo_estado', 'fuente_nombre': 'Consejo de Estado',
                     'tipo': 'Providencia', 'identificador': f'Rad. {radicado}', 'fecha': fecha(clean(f.get_text()) if f else ''),
                     'tema': query, 'titulo': f'Rad. {radicado} · {clean(sala.get_text()) if sala else "Consejo de Estado"}',
                     'resumen': clean(problema.get_text(' ', strip=True) if problema else '')[:700],
                     'url': urljoin(SAMAI, found.group(1)), 'consulta': query})
    return rows


def fetch(queries: tuple[str, ...], sources: tuple[str, ...]) -> None:
    records, failures = [], []
    with requests.Session() as session:
        session.headers.update(HEADERS)
        available = {'corte': ('Corte Constitucional', corte), 'consejo': ('Consejo de Estado', consejo)}
        for key in sources:
            source, fn = available[key]
            for query in queries:
                try:
                    got = fn(query, session)
                    records.extend(got)
                    print(f'{source:22s} {query!r}: {len(got)}')
                except requests.RequestException as exc:
                    failures.append(f'{source} · {query}: {type(exc).__name__}: {exc}')
                    print(f'ERROR {failures[-1]}')
    unique = {(r['fuente'], r['identificador'], r['url']): r for r in records}
    RAW.parent.mkdir(parents=True, exist_ok=True)
    with RAW.open('w', encoding='utf-8') as fh:
        for rec in unique.values():
            fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
    (DATA / 'fetch-errors.txt').write_text('\n'.join(failures) + ('\n' if failures else ''), encoding='utf-8')
    print(f'{len(unique)} providencias -> {RAW.relative_to(REPO)}')


def build() -> None:
    if not RAW.exists():
        raise SystemExit(f'No existe {RAW}. Corre fetch primero.')
    recs = [json.loads(line) for line in RAW.read_text(encoding='utf-8').split('\n') if line.strip()]
    for r in recs:
        r['q'] = fold(' '.join(str(r.get(k, '')) for k in ('fuente_nombre', 'tipo', 'identificador', 'tema', 'titulo', 'resumen')))
    recs.sort(key=lambda r: r.get('fecha', ''), reverse=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'control.jsonl').open('w', encoding='utf-8') as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    dates = sorted(r['fecha'] for r in recs if r.get('fecha'))
    stats = {'total': len(recs), 'por_fuente': [{'fuente': k, 'n': v} for k, v in Counter(r['fuente_nombre'] for r in recs).most_common()],
             'por_tipo': [{'tipo': k, 'n': v} for k, v in Counter(r['tipo'] for r in recs).most_common()],
             'rango_fechas': [dates[0], dates[-1]] if dates else ['', ''],
             'recientes': [{k: v for k, v in r.items() if k != 'q'} for r in recs[:15]]}
    (OUT / 'control-stats.json').write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{len(recs)} providencias -> {OUT.relative_to(REPO)}')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('fetch', 'build'))
    parser.add_argument('--queries', default=','.join(DEFAULT_QUERIES))
    parser.add_argument('--sources', default='corte,consejo',
                        help='lista separada por coma: corte,consejo')
    args = parser.parse_args()
    if args.command == 'fetch':
        sources = tuple(x.strip() for x in args.sources.split(',') if x.strip())
        if not sources or any(x not in {'corte', 'consejo'} for x in sources):
            raise SystemExit('--sources acepta corte,consejo')
        fetch(tuple(x.strip() for x in args.queries.split(',') if x.strip()), sources)
    else:
        build()


if __name__ == '__main__':
    main()
