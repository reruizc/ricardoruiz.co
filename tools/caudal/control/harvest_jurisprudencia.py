#!/usr/bin/env python3
"""Cosecha de jurisprudencia para el pilar Control de Caudal.

Fuente activa: buscador público de la relatoría de la Corte Constitucional.
Sin LLM y sin inventar: cada fila conserva su identificador y su URL oficial.

  fetch  → consulta el buscador y guarda el crudo normalizado (resumible)
  build  → produce el JSONL slim y los agregados que lee la Lambda

⚠️ STDLIB PURA + curl POR SUBPROCESS, a propósito y por dos razones medidas:
   (1) `requests`/`bs4` no están en la Mac M5 y una dependencia más es una
       corrida del cron que falla sin avisar;
   (2) el TLS de python 3.14 de esta máquina no valida el certificado de
       corteconstitucional.gov.co (CERTIFICATE_VERIFY_FAILED) y curl sí.
   Es el mismo patrón de `scrape_cne.py` y `tools/leyes-senado/harvest.py`.

⚠️ LA COBERTURA ES POR CONSULTA TEMÁTICA, NO EL FLUJO COMPLETO de la Corte.
   El buscador no expone "todo lo publicado entre dos fechas": exige un texto
   de búsqueda. Así que el índice es la unión de las consultas de `CONSULTAS`,
   y eso viaja en el JSON (`cobertura`) para que la interfaz pueda decirlo. Un
   tema que no esté en la lista devuelve cero, y cero NO significa "no hay
   jurisprudencia": significa "no lo hemos cosechado".
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import unicodedata
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DATA = REPO / 'Bases de datos' / 'leyes-senado' / 'control'
RAW = DATA / 'raw' / 'jurisprudencia.jsonl'
CACHE = DATA / 'raw' / 'corte'
OUT = DATA / 'dist' / 's3'

CORTE = 'https://www.corteconstitucional.gov.co/relatoria/buscador_new/index.php'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')

# Medido: `maxprov` no está capado del lado del servidor. Con 100 una consulta
# amplia como "salud" devuelve 98 providencias; con 1000 devuelve 894, en 2,2 s
# y 3,3 MB. El tope alto es lo que separa "una muestra por tema" de "el tema".
MAXPROV = 1000
DESDE = '2021-01-01'

# Las consultas SON el alcance del pilar. Están alineadas con los sectores del
# radar (caudal_core.SECTORES_CLIENTE) y con los tópicos del tesauro que de
# verdad producen jurisprudencia constitucional: el cliente busca por su
# sector, no por el nombre de una sala.
# ⚠️ Al agregar una, correr `fetch --solo <consulta>` y mirar cuánto rinde: una
#    consulta que devuelve 3 filas ensucia el índice sin aportar cobertura.
CONSULTAS = (
    # — Estado, contratación y función pública —
    'contratación estatal', 'contratación pública', 'función pública',
    'presupuesto público', 'regalías', 'entidades territoriales',
    # — Seguridad social y trabajo —
    'salud', 'sistema de salud', 'EPS', 'medicamentos',
    'pensiones', 'régimen pensional', 'derecho laboral', 'estabilidad laboral',
    'seguridad social', 'trabajo',
    # — Economía y regulación sectorial —
    'servicios públicos domiciliarios', 'energía eléctrica', 'gas natural',
    'telecomunicaciones', 'sector financiero', 'crédito', 'seguros',
    'libre competencia', 'protección al consumidor', 'tributario',
    'impuestos', 'aduanas', 'comercio exterior', 'transporte',
    'minería', 'hidrocarburos', 'juegos de suerte y azar',
    # — Territorio, ambiente y comunidades —
    'ambiente', 'licencia ambiental', 'consulta previa', 'páramos',
    'ordenamiento territorial', 'vivienda', 'agua potable',
    'desarrollo rural', 'tierras',
    # — Derechos y garantías con efecto regulatorio —
    'datos personales', 'habeas data', 'libertad de expresión',
    'debido proceso administrativo', 'elecciones', 'participación ciudadana',
    'educación', 'víctimas del conflicto', 'discriminación',
)


def norm_txt(v: str) -> str:
    return ' '.join(unescape(v or '').split())


def fold(v: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', (v or '').lower())
                   if unicodedata.category(c) != 'Mn')


def slug(v: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', fold(v)).strip('-')


def fecha_iso(v: str) -> str:
    for pat, fmt in ((r'(\d{4}-\d{2}-\d{2})', '%Y-%m-%d'), (r'(\d{2}/\d{2}/\d{4})', '%d/%m/%Y')):
        m = re.search(pat, v or '')
        if m:
            try:
                return dt.datetime.strptime(m.group(1), fmt).date().isoformat()
            except ValueError:
                pass
    return ''


# "Sin información" / "No aplica" son los marcadores de ausencia de la Corte.
# Se guardan como vacío: un campo que dice "Sin información" ocupa el lugar del
# dato y hace creer que se leyó algo.
_AUSENTE = re.compile(r'^\s*(sin\s+informaci[oó]n|no\s+aplica|n/?a|-+|\.+)\s*$', re.I)


def _sin_marcador(v: str) -> str:
    return '' if (not v or _AUSENTE.match(v)) else v


def _curl(query: str, hasta: str) -> str:
    campos = {
        'accion': 'search', 'verform': 'si', 'slop': '1', 'buscador': 'buscador',
        'qu': '286', 'maxprov': str(MAXPROV), 'OrderbyOption': 'des__score',
        'searchOption': 'texto', 'buscar_por': query, 'fini': DESDE, 'ffin': hasta,
    }
    cmd = ['/usr/bin/curl', '-s', '-m', '180', '-A', UA, '-X', 'POST', CORTE]
    for k, v in campos.items():
        cmd += ['--data-urlencode', f'{k}={v}']
    # bytes + decode tolerante: la relatoría mezcla utf-8 con restos latin-1 y
    # `text=True` revienta la corrida entera por un byte suelto.
    return subprocess.run(cmd, capture_output=True, timeout=200).stdout.decode('utf-8', 'replace')


def _parse(html: str, query: str) -> list[dict]:
    """Filas de la tabla de resultados → registros normalizados.

    ⚠️ Tres trampas de esta fuente, las tres medidas sobre el HTML real:
      1. La primera celda NO es solo el identificador: trae el enlace a la
         providencia, un "Ver ficha" de adorno y, en los autos de seguimiento,
         el NOMBRE DEL CASO pegado ("A. 1201/26 Departamento de la Guajira -
         Wayuu (T-302/17)"). El identificador es el texto del <a> con
         title="Ver providencia"; el resto es el caso, que se guarda aparte
         porque para un auto de seguimiento es lo único que lo identifica.
      2. La tercera celda son DOS campos en uno, separados por <br>:
         "<b>TEMA: </b>… <b>RESUMEN: </b>…".
      3. **"Sin información" es el marcador de ausencia de la Corte**, no un
         texto. Sin filtrarlo, 8 de cada 10 autos quedan con el resumen
         "Sin información RESUMEN: Sin información" — el mismo modo de falla
         del `sancionado: "—"` de la ANLA. Ausencia se guarda como vacío.
    """
    i = html.find('div_resultado_tabla')
    if i < 0:
        return []
    filas, seg = [], html[i:]
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', seg, re.S):
        celdas = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)
        enlace = re.search(r'<a[^>]+href="([^"]*/relatoria/[^"]+\.htm[^"]*)"[^>]*'
                           r'title="Ver providencia"[^>]*>(.*?)</a>', tr, re.S | re.I)
        if len(celdas) < 3 or not enlace:
            continue
        url = unescape(enlace.group(1))
        ident = norm_txt(re.sub(r'<[^>]+>', ' ', enlace.group(2)))
        if not ident:
            continue
        # lo que queda de la celda 0 tras quitar el identificador y "Ver ficha"
        crudo0 = norm_txt(re.sub(r'<[^>]+>', ' ', celdas[0]))
        caso = crudo0.replace(ident, '', 1).replace('Ver ficha', '').strip(' -·')
        # El identificador dice el tipo: A = auto, C/T/SU = sentencia.
        tipo = 'Auto' if re.match(r'^A\.?\s*\d', ident) else 'Sentencia'
        # TEMA y RESUMEN son dos campos, no uno
        cel2 = re.sub(r'<br\s*/?>', '\n', celdas[2], flags=re.I)
        partes = re.split(r'<b>\s*RESUMEN\s*:?\s*</b>', cel2, flags=re.I)
        tema_txt = _sin_marcador(norm_txt(re.sub(r'<[^>]+>', ' ',
                                partes[0]).replace('TEMA:', '', 1)))
        resumen = _sin_marcador(norm_txt(re.sub(r'<[^>]+>', ' ', partes[1]))) if len(partes) > 1 else ''
        filas.append({
            'fuente': 'corte_constitucional', 'fuente_nombre': 'Corte Constitucional',
            'tipo': tipo, 'identificador': ident, 'caso': caso[:200],
            'fecha': fecha_iso(norm_txt(re.sub(r'<[^>]+>', ' ', celdas[1]))),
            'tema': query,
            'titulo': f'{ident} · Corte Constitucional' + (f' · {caso[:90]}' if caso else ''),
            'sintesis': tema_txt[:400], 'resumen': resumen[:700],
            'url': url, 'consulta': query,
        })
    return filas


def fetch(consultas: tuple[str, ...], workers: int, refrescar: bool) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    hasta = dt.date.today().isoformat()

    def una(q: str):
        destino = CACHE / f'{slug(q)}.json'
        if destino.exists() and not refrescar:
            filas = json.loads(destino.read_text(encoding='utf-8'))
            return q, filas, 'caché'
        try:
            filas = _parse(_curl(q, hasta), q)
        except Exception as exc:                                   # noqa: BLE001
            return q, [], f'ERROR {type(exc).__name__}: {exc}'
        # ⚠️ Cero no se cachea: una consulta vacía casi siempre es un tropiezo
        #    de red, y guardarla la deja muerta para todas las corridas futuras.
        if filas:
            destino.write_text(json.dumps(filas, ensure_ascii=False), encoding='utf-8')
        return q, filas, 'ok' if filas else 'VACÍA'

    todo, fallos = [], []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for q, filas, estado in pool.map(una, consultas):
            print(f'  {q[:34]:34s} {len(filas):5d}  {estado}')
            if estado.startswith('ERROR') or estado == 'VACÍA':
                fallos.append(f'{q}: {estado}')
            todo.extend(filas)

    # Dedup por URL: la misma sentencia sale en varias consultas, y esa es la
    # señal de que el tema es transversal — se conserva la primera y las demás
    # consultas quedan registradas en `temas`.
    unicas: dict[str, dict] = {}
    for r in todo:
        k = r['url']
        if k in unicas:
            unicas[k].setdefault('temas', [unicas[k]['tema']])
            if r['tema'] not in unicas[k]['temas']:
                unicas[k]['temas'].append(r['tema'])
        else:
            unicas[k] = dict(r, temas=[r['tema']])

    RAW.parent.mkdir(parents=True, exist_ok=True)
    with RAW.open('w', encoding='utf-8') as fh:
        for r in unicas.values():
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    (DATA / 'fetch-errors.txt').write_text('\n'.join(fallos) + ('\n' if fallos else ''),
                                           encoding='utf-8')
    (DATA / 'consultas.json').write_text(json.dumps({
        'v': hasta, 'desde': DESDE, 'maxprov': MAXPROV,
        'consultas': list(consultas), 'sin_resultado': [f.split(':')[0] for f in fallos],
    }, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'\n{len(unicas)} providencias únicas de {len(todo)} filas '
          f'({len(consultas)} consultas) -> {RAW.relative_to(REPO)}')


def build() -> None:
    if not RAW.exists():
        raise SystemExit(f'No existe {RAW}. Corre fetch primero.')
    recs = [json.loads(l) for l in RAW.read_text(encoding='utf-8').split('\n') if l.strip()]
    for r in recs:
        r['q'] = fold(' '.join(str(r.get(k, '')) for k in
                               ('fuente_nombre', 'tipo', 'identificador', 'titulo', 'resumen'))
                      + ' ' + ' '.join(r.get('temas') or [r.get('tema', '')]))
    recs.sort(key=lambda r: r.get('fecha', ''), reverse=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'control.jsonl').open('w', encoding='utf-8') as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')

    cons = {}
    p = DATA / 'consultas.json'
    if p.exists():
        cons = json.loads(p.read_text(encoding='utf-8'))
    fechas = sorted(r['fecha'] for r in recs if r.get('fecha'))
    temas = Counter(t for r in recs for t in (r.get('temas') or []))
    stats = {
        'total': len(recs),
        'por_fuente': [{'fuente': k, 'n': v} for k, v in
                       Counter(r['fuente_nombre'] for r in recs).most_common()],
        'por_tipo': [{'tipo': k, 'n': v} for k, v in
                     Counter(r['tipo'] for r in recs).most_common()],
        'por_anio': [{'anio': k, 'n': v} for k, v in
                     sorted(Counter(r['fecha'][:4] for r in recs if r.get('fecha')).items())],
        'rango_fechas': [fechas[0], fechas[-1]] if fechas else ['', ''],
        # EL ALCANCE VIAJA CON EL DATO: la interfaz no puede decir "no hay
        # providencias" cuando lo cierto es "no cosechamos ese tema".
        'cobertura': {
            'modo': 'consultas_tematicas',
            'n_consultas': len(cons.get('consultas') or []),
            'consultas': sorted(temas, key=lambda t: -temas[t]),
            'desde': cons.get('desde', DESDE),
            'fuentes_activas': ['Corte Constitucional'],
            'fuentes_pendientes': ['Consejo de Estado', 'Corte Suprema de Justicia',
                                   'Procuraduría General de la Nación'],
            'nota': ('El índice es la unión de {} consultas temáticas sobre la relatoría '
                     'de la Corte Constitucional desde {}, no el flujo completo de la '
                     'Corte. Un tema fuera de esa lista devuelve cero porque no se ha '
                     'cosechado, no porque no exista jurisprudencia.'
                     ).format(len(cons.get('consultas') or []), cons.get('desde', DESDE)),
        },
        'recientes': [{k: v for k, v in r.items() if k != 'q'} for r in recs[:15]],
    }
    (OUT / 'control-stats.json').write_text(json.dumps(stats, ensure_ascii=False, indent=1),
                                            encoding='utf-8')
    print(f'{len(recs)} providencias -> {OUT.relative_to(REPO)}')
    print(f'  rango {stats["rango_fechas"][0]} a {stats["rango_fechas"][1]} · '
          f'{len(stats["por_tipo"])} tipos · {stats["cobertura"]["n_consultas"]} consultas')


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=('fetch', 'build'))
    ap.add_argument('--solo', default='', help='una o varias consultas separadas por coma')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--refrescar', action='store_true',
                    help='ignora el caché por consulta y vuelve a pedir todo')
    a = ap.parse_args()
    if a.command == 'fetch':
        qs = tuple(x.strip() for x in a.solo.split(',') if x.strip()) or CONSULTAS
        fetch(qs, max(1, a.workers), a.refrescar)
    else:
        build()


if __name__ == '__main__':
    main()
