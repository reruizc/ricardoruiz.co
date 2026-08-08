#!/usr/bin/env python3
"""
Caudal · harvester del pilar SUCOP (Sistema Único de Consulta Pública).

QUÉ ES (verificado ago-2026, no supuesto): www.sucop.gov.co, operado por el DNP.
Es donde las entidades publican sus PROYECTOS DE NORMA para comentarios del
público ANTES de expedirlos (Decreto 1081/2015 art. 2.1.2.1.14 + Decreto 1273/2020),
y también sus AGENDAS REGULATORIAS anuales. Es la señal más TEMPRANA del sistema:
el pilar Ejecutivo trae decretos ya expedidos —cuando salen ahí la pelea se
perdió—; acá el borrador está en la ventana en que todavía se puede incidir.

EL CAMPO QUE LO HACE DISTINTO A TODO LO DEMÁS EN CAUDAL: **la consulta VENCE**.
Un borrador cuyo plazo cerró es arqueología; uno que cierra en 5 días es una
alerta urgente. Por eso `fecha_inicio`/`fecha_fin` son ciudadanas de primera
clase y `estado_consulta` es un CAMPO DEL DATO, no algo que el frontend calcule.
Ojo: es un estado con fecha de vencimiento — se calcula al construir y el
stats.json declara `calculado_a`. Todo consumidor que quiera el estado de HOY
debe recalcularlo con `estado_consulta_de(fecha_ini, fecha_fin, estado, hoy)`,
que es justo lo que hace la Lambda en cada request.

VÍA DE EXTRACCIÓN — se probaron las tres del método del pilar Regulatorio:
  ✗ (1) Socrata / datos.gov.co: NO existe dataset de SUCOP. El catálogo devuelve
        0 para 'SUCOP' y las variantes ('consulta publica normativa',
        'proyectos normativos') solo traen esquemas de publicación de alcaldías.
  ✓ (2) API interna del sitio: SUCOP es SharePoint y su `_api` REST responde
        ANÓNIMA (mismo patrón que ya destapó el registro de Supersalud). El
        buscador público (/Paginas/busqueda-beta.aspx) carga
        /Style Library/SUCOP-v2/js/busqueda/search-beta.js, que usa JSOM contra
        `SP.ClientContext('/formulacion_/')` → lista **"Procesos SUCOP"**.
        De ahí salen el subsitio, la lista y los nombres exactos de los campos.
  – (3) Scraping HTML: innecesario.

ESTRUCTURA DE LA FUENTE (la parte que cuesta descubrir):
  `Procesos SUCOP` es una BIBLIOTECA de documentos (BaseTemplate 101) con ~17.800
  items = ~3.900 CARPETAS (una por proceso, content types `0x0120D52000…`) +
  ~13.900 documentos ADENTRO de esas carpetas. Los procesos son las carpetas.
  ⚠ `/items` con `$filter=FSObjType eq 1` revienta contra el list view threshold
    (5.000) porque la columna no está indexada, y sin `$select` explícito revienta
    antes por el límite de columnas de búsqueda. La vía que SÍ aguanta es
    `rootfolder/folders?$expand=ListItemAllFields`, que además devuelve las
    taxonomías ya RESUELTAS a texto ('Decreto', 'Gobernación de Antioquia') —
    por `/items` llegan como WssId numérico y habría que cruzar TaxonomyHiddenList.
  ⚠ `$expand` NO admite el campo `Agenda` en `$select` (pide expandirlo aparte);
    se omite, no aporta.

Todo stdlib. curl por subprocess (esquiva el TLS de python 3.14, igual que
scrape_cne.py y harvest_decretos.py).

Uso:
  python3 tools/caudal/sucop/harvest_sucop.py fetch            # baja los ~3.900 procesos
  python3 tools/caudal/sucop/harvest_sucop.py fetch --reuse    # resume (salta páginas en disco)
  python3 tools/caudal/sucop/harvest_sucop.py build            # raw -> dist (JSONL + stats)
  python3 tools/caudal/sucop/harvest_sucop.py test             # smoke test (no escribe nada)
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = REPO / 'Bases de datos' / 'leyes-senado' / 'sucop'
RAW = OUT / 'raw'
DIST = OUT / 'dist'

HOST = 'www.sucop.gov.co'
WEB = '/formulacion_'          # subsitio donde vive la lista (lo dice search-beta.js)
LISTA = 'Procesos SUCOP'
FUENTE_NOMBRE = 'SUCOP · Sistema Único de Consulta Pública (DNP)'
FUENTE_URL = 'https://www.sucop.gov.co/Paginas/busqueda-beta.aspx'
MARCO_LEGAL = ('Decreto 1081 de 2015 (art. 2.1.2.1.14) y Decreto 1273 de 2020 · '
               'consulta pública de proyectos de regulación')

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')
PAGE = 500          # folders por request (8 páginas ≈ 3.900)
MAX_PAGES = 60      # tope de seguridad
DIAS_CIERRA_PRONTO = 7

# Entidad de prueba que el propio SUCOP esconde en su buscador (search-beta.js
# línea ~771). Si no se filtra, entran procesos "Lorem ipsum" como si fueran reales.
ENTIDAD_TEST = 'entidad ejemplo'
CT_PROCESO = '0x0120D52000'    # prefijo de los content types de proceso (carpeta)

_SEL_LI = ','.join('ListItemAllFields/' + f for f in (
    'Id', 'Title', 'nombreProyecto', 'Objeto', 'comisionObjeto', 'Created',
    'Modified', 'FechaInicioComentarios', 'FechaFinComentarios', 'Mensajes',
    'likes', 'estadoView', 'MostrarLink', 'Entidad', 'Sector', 'TipoNormativa',
    'Anio', 'EstadoNormativa', 'EstadoAgenda', 'ContentTypeId'))
SELECT = _SEL_LI + ',Name,ItemCount,TimeLastModified'

# --- estados -----------------------------------------------------------------
# Traducción OFICIAL del propio SUCOP (translateEstado() de search-beta.js). No se
# inventa: se copia, para que lo que Caudal muestre diga lo mismo que la fuente.
ESTADO_OFICIAL = {
    ('norma', 'en consulta publica'): 'Activa',
    ('norma', 'ajustes posteriores a consulta publica'): 'Cerrada',
    ('norma', 'aprobacion posterior a consulta publica'): 'Cerrada',
    ('norma', 'aprobacion de ajustes posteriores a consulta publica'): 'Cerrada',
    ('norma', 'respuesta a comentarios de consulta publica'): 'Cerrada',
    ('norma', 'completada'): 'Finalizada',
    ('norma', 'en planeacion'): 'Planeación de la consulta',
    ('norma', 'aprobacion caracterizacion de norma'): 'Aprobación de la consulta pública',
    ('norma', 'aprobacion de ajustes de caracterizacion de norma'): 'Aprobación de la consulta pública',
    ('agenda', 'en consulta publica'): 'Activa',
    ('agenda', 'respuesta a comentarios'): 'Cerrada',
    ('agenda', 'aprobacion final'): 'Cerrada',
    ('agenda', 'publicada'): 'Finalizada',
    ('agenda', 'formulacion'): 'Planeación de la consulta',
}

_FECHA_MAX = (datetime.date.today() + datetime.timedelta(days=400)).isoformat()


def _norm(s):
    s = (s or '').lower()
    for a, b in (('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u'), ('ñ', 'n')):
        s = s.replace(a, b)
    return re.sub(r'\s+', ' ', s).strip()


def curl_json(url, timeout=120):
    cmd = ['/usr/bin/curl', '-s', '-A', UA,
           '-H', 'Accept: application/json;odata=nometadata',
           '--max-time', str(timeout), url]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout + 15)
    except subprocess.TimeoutExpired:
        return None, 'timeout'
    if r.returncode != 0:
        return None, f'curl rc={r.returncode}'
    try:
        d = json.loads(r.stdout.decode('utf-8', errors='replace'))
    except json.JSONDecodeError as e:
        return None, f'json: {e}'
    if isinstance(d, dict) and 'odata.error' in d:
        msg = d['odata.error'].get('message', {})
        return None, 'sharepoint: ' + str(msg.get('value', msg))[:160]
    return d, None


def _url_pagina(skip):
    base = f'https://{HOST}{WEB}/_api/web/lists/getbytitle(%27{LISTA.replace(" ", "%20")}%27)/rootfolder/folders'
    return f'{base}?$expand=ListItemAllFields&$select={SELECT}&$top={PAGE}&$skip={skip}'


def fetch(reuse=False):
    """Pagina rootfolder/folders. Cachea cada página en raw/ (resumible con --reuse)."""
    RAW.mkdir(parents=True, exist_ok=True)
    total, pagina = 0, 0
    while pagina < MAX_PAGES:
        skip = pagina * PAGE
        dest = RAW / f'procesos-{pagina:03d}.json'
        if reuse and dest.exists():
            try:
                n = len(json.loads(dest.read_text(encoding='utf-8')))
            except json.JSONDecodeError:
                n = -1
            if n >= 0:
                print(f'  ·   pág {pagina:>2d}  {n:>5d} (caché)')
                total += n
                pagina += 1
                if n < PAGE:
                    break
                continue
        data, err = curl_json(_url_pagina(skip))
        if err:
            print(f'  !   pág {pagina}: {err}', file=sys.stderr)
            return None
        rows = data.get('value', []) if isinstance(data, dict) else []
        dest.write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
        print(f'  ok  pág {pagina:>2d}  {len(rows):>5d}')
        total += len(rows)
        pagina += 1
        if len(rows) < PAGE:
            break
        time.sleep(0.3)
    print(f'  ok  {total} carpetas -> {RAW.relative_to(REPO)}')
    return total


# --- normalización -----------------------------------------------------------
def _lab(v):
    """Campo de taxonomía -> su texto. Por rootfolder/folders llega resuelto."""
    if isinstance(v, dict):
        return (v.get('Label') or '').strip()
    return (v or '').strip() if isinstance(v, str) else ''


def _fecha(v):
    """'2025-12-16T16:14:50' -> '2025-12-16' (descarta lo absurdo)."""
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', str(v or ''))
    if not m:
        return ''
    f = m.group(0)
    return f if '2015-01-01' <= f <= _FECHA_MAX else ''


def estado_consulta_de(ini, fin, estado, hoy):
    """El campo que define este pilar: ¿todavía se puede comentar?

    Se decide por la FECHA (que es el hecho), y el estado de la fuente solo
    desempata cuando no hay fechas. Devuelve (estado_consulta, dias_restantes).
      abierta       · la ventana está corriendo
      cierra_pronto · abierta y le quedan <= 7 días  -> esto es lo accionable
      cerrada       · la ventana venció
      por_abrir     · la ventana aún no arranca
      planeacion    · la entidad la anunció pero no fijó fechas
      cancelada     · la entidad desistió del proceso
      sin_fechas    · no hay ventana publicada
    """
    if _norm(estado) == 'cancelada':      # desistida: nunca va a abrir
        return 'cancelada', None
    if fin:
        dias = (datetime.date.fromisoformat(fin) - hoy).days
        if dias < 0:
            return 'cerrada', dias
        if ini and datetime.date.fromisoformat(ini) > hoy:
            return 'por_abrir', dias
        return ('cierra_pronto' if dias <= DIAS_CIERRA_PRONTO else 'abierta'), dias
    if estado in ('Planeación de la consulta', 'Aprobación de la consulta pública'):
        return 'planeacion', None
    return 'sin_fechas', None


def slim(f, hoy, topicos_fn):
    li = f.get('ListItemAllFields') or {}
    ct = str(li.get('ContentTypeId') or '')
    if not ct.startswith(CT_PROCESO):
        return None                       # no es una carpeta de proceso

    entidad = _lab(li.get('Entidad'))
    if _norm(entidad) == ENTIDAD_TEST:
        return None                       # datos de prueba del propio SUCOP

    est_norma = _lab(li.get('EstadoNormativa'))
    est_agenda = _lab(li.get('EstadoAgenda'))
    tipo = 'norma' if est_norma else 'agenda'
    est_fuente = est_norma or est_agenda
    vista = (li.get('estadoView') or '').strip()
    # el propio SUCOP mapea este caso de agenda a 'Aprobación final'
    clave = 'aprobacion final' if (
        tipo == 'agenda' and vista == 'Aprobación de la respuesta de los comentarios'
    ) else _norm(est_fuente)
    estado = ESTADO_OFICIAL.get((tipo, clave), vista or est_fuente or '—')

    ini = _fecha(li.get('FechaInicioComentarios'))
    fin = _fecha(li.get('FechaFinComentarios'))
    ec, dias = estado_consulta_de(ini, fin, estado, hoy)

    titulo = (li.get('nombreProyecto') or li.get('Title') or '').strip()
    objeto = re.sub(r'\s+', ' ', (li.get('Objeto') or li.get('comisionObjeto') or '')).strip()
    anio = _lab(li.get('Anio'))
    link = li.get('MostrarLink') or {}
    url = (link.get('Url') or '').strip() if isinstance(link, dict) else ''
    pid = li.get('Id')

    def _int(v):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return 0

    rec = {
        'id': pid,
        # el código público del proceso: confirmado contra la lista `Comentarios`
        # del sitio raíz (cCodigo='PN-2025-23141' con cIdProceso=23141, cAnio=2025)
        'codigo': f'PN-{anio}-{pid}' if (tipo == 'norma' and anio) else '',
        'tipo': tipo,                          # norma | agenda (regulatoria)
        'titulo': titulo or '—',
        'objeto': objeto,
        'entidad': entidad,
        'sector': _lab(li.get('Sector')),
        'tipo_norma': _lab(li.get('TipoNormativa')) or 'No especificado',
        'anio': anio,
        'estado': estado,                      # traducción oficial de SUCOP
        'estado_fuente': est_fuente,           # el crudo, para poder auditar
        'estado_vista': vista,
        'fecha_inicio': ini,
        'fecha_fin': fin,
        'estado_consulta': ec,                 # <- el campo que define el pilar
        'dias_restantes': dias,
        'comentarios': _int(li.get('Mensajes')),
        'likes': _int(li.get('likes')),
        'n_documentos': _int(f.get('ItemCount')),
        'url': url,                            # ficha oficial del proceso
        'creado': _fecha(li.get('Created')),
    }
    rec['topicos'] = topicos_fn(f"{titulo} {objeto}")
    rec['q'] = _norm(f'{titulo} {objeto} {entidad} {rec["tipo_norma"]} {rec["codigo"]}')
    return rec


def _tesauro():
    """Etiqueta cada borrador con los tópicos del tesauro que toca.

    Es la cara de TEMA del diccionario de empresas: el Estado regula ACTIVIDADES,
    no marcas, así que un borrador nunca dice 'AngloGold' pero sí 'minería'. Con
    esto, `empresas.topicos_de()` lleva de la marca del cliente a sus borradores.
    Import defensivo: si caudal_core no está importable, el harvester sigue y solo
    deja `topicos` vacío (nunca aborta la cosecha por esto).
    """
    try:
        sys.path.insert(0, str(HERE.parent))
        from caudal_core import SINONIMOS, _phrase_match, _norm as cnorm
    except Exception as e:                                   # noqa: BLE001
        print(f'  ! tesauro no disponible ({e}); topicos vacíos', file=sys.stderr)
        return (lambda _t: []), False

    def fn(texto):
        tn = cnorm(texto or '')
        if not tn:
            return []
        return [t['k'] for t in SINONIMOS
                if any(_phrase_match(term, tn) for term in t['terms'])]
    return fn, True


def build():
    """raw/procesos-*.json -> dist/sucop.jsonl (slim) + dist/stats.json."""
    paginas = sorted(RAW.glob('procesos-*.json'))
    if not paginas:
        print("no hay raw; corre 'fetch' primero", file=sys.stderr)
        sys.exit(1)

    hoy = datetime.date.today()
    topicos_fn, con_tesauro = _tesauro()

    recs, vistos, descartados = [], set(), Counter()
    for p in paginas:
        for f in json.loads(p.read_text(encoding='utf-8')):
            r = slim(f, hoy, topicos_fn)
            if r is None:
                descartados['no-proceso / entidad de prueba'] += 1
                continue
            if r['id'] in vistos:        # $skip no garantiza orden estable
                descartados['duplicado'] += 1
                continue
            vistos.add(r['id'])
            recs.append(r)

    recs.sort(key=lambda r: (r['fecha_inicio'] or r['creado'] or ''), reverse=True)
    DIST.mkdir(parents=True, exist_ok=True)
    with (DIST / 'sucop.jsonl').open('w', encoding='utf-8') as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')

    abiertos = [r for r in recs if r['estado_consulta'] in ('abierta', 'cierra_pronto')]
    pronto = [r for r in recs if r['estado_consulta'] == 'cierra_pronto']
    por_ec = Counter(r['estado_consulta'] for r in recs)
    por_tipo = Counter(r['tipo'] for r in recs)
    por_tnorma = Counter(r['tipo_norma'] for r in recs)
    por_sector = Counter(r['sector'] or '—' for r in recs)
    por_entidad = Counter(r['entidad'] or '—' for r in recs)
    por_anio = Counter(r['anio'] for r in recs if r['anio'])
    por_topico = Counter(t for r in recs for t in r['topicos'])
    fechas = sorted(r['fecha_inicio'] for r in recs if r['fecha_inicio'])

    def _card(r):
        return {k: r[k] for k in (
            'id', 'codigo', 'tipo', 'titulo', 'entidad', 'sector', 'tipo_norma',
            'estado', 'estado_consulta', 'dias_restantes', 'fecha_inicio',
            'fecha_fin', 'comentarios', 'n_documentos', 'url')}

    stats = {
        'total': len(recs),
        # ⚠ estado con fecha de vencimiento: es el corte de ESTE build
        'calculado_a': hoy.isoformat(),
        'generado': datetime.datetime.now().replace(microsecond=0).isoformat(),
        'abiertos_ahora': len(abiertos),
        'cierran_en_7_dias': len(pronto),
        'con_tesauro': con_tesauro,
        'por_estado_consulta': dict(por_ec.most_common()),
        'por_tipo': dict(por_tipo.most_common()),
        'por_tipo_norma': [{'tipo': t, 'n': n} for t, n in por_tnorma.most_common()],
        'por_sector': [{'sector': s, 'n': n} for s, n in por_sector.most_common()],
        'por_entidad': [{'entidad': e, 'n': n} for e, n in por_entidad.most_common(40)],
        'por_anio': dict(sorted(por_anio.items())),
        'por_topico': [{'topico': t, 'n': n} for t, n in por_topico.most_common()],
        'rango_fechas': [fechas[0], fechas[-1]] if fechas else ['', ''],
        # lo accionable primero: lo que cierra ya, y lo abierto
        'cerrando': [_card(r) for r in sorted(
            pronto, key=lambda r: r['dias_restantes'])][:25],
        'abiertos': [_card(r) for r in sorted(
            abiertos, key=lambda r: r['dias_restantes'])][:40],
        'recientes': [_card(r) for r in recs[:20]],
        'fuente': {
            'nombre': FUENTE_NOMBRE, 'url': FUENTE_URL,
            'via': 'API interna SharePoint (_api REST anónima) · lista "Procesos SUCOP"',
            'marco_legal': MARCO_LEGAL,
            'frecuencia': 'Diaria (la fuente se mueve todos los días hábiles)',
        },
        'descartados': dict(descartados),
    }
    (DIST / 'stats.json').write_text(
        json.dumps(stats, ensure_ascii=False, indent=1), encoding='utf-8')

    print(f"slim: {len(recs)} procesos -> {(DIST / 'sucop.jsonl').relative_to(REPO)}")
    print(f"  rango: {stats['rango_fechas'][0]} .. {stats['rango_fechas'][1]}"
          f"   ·   corte: {hoy}")
    print(f"  ABIERTOS AHORA: {len(abiertos)}   (cierran en <= "
          f"{DIAS_CIERRA_PRONTO} días: {len(pronto)})")
    for k, n in por_ec.most_common():
        print(f"    {k:16s} {n:>6d}")
    print(f"  tipo: " + ' · '.join(f'{k}={n}' for k, n in por_tipo.most_common()))
    print(f"  descartados: {dict(descartados) or 'ninguno'}")
    return stats


def test():
    """Smoke test: pega una página de 1 y valida el mapeo. No escribe nada."""
    data, err = curl_json(_url_pagina(0).replace(f'$top={PAGE}', '$top=1'), timeout=60)
    if err or not (data or {}).get('value'):
        print(f'FALLA: {err or "sin filas"}')
        return False
    fn, _ = _tesauro()
    r = slim(data['value'][0], datetime.date.today(), fn)
    if r is None:
        print('FALLA: la primera carpeta no mapeó a proceso')
        return False
    for k in ('id', 'tipo', 'titulo', 'entidad', 'estado', 'estado_consulta'):
        print(f'  {k} = {str(r[k])[:80]}')
    print(f'  ventana = {r["fecha_inicio"] or "—"} .. {r["fecha_fin"] or "—"}'
          f'  ({r["dias_restantes"]} días)')
    ok = bool(r['id'] and r['titulo'] != '—' and r['entidad'] and r['estado_consulta'])
    print('\nTEST OK' if ok else '\nTEST: revisar mapeo')
    return ok


def main():
    ap = argparse.ArgumentParser(description='Harvester del pilar SUCOP de Caudal')
    sub = ap.add_subparsers(dest='cmd', required=True)
    fp = sub.add_parser('fetch')
    fp.add_argument('--reuse', action='store_true',
                    help='salta páginas ya en disco (resume una corrida rota)')
    sub.add_parser('build')
    sub.add_parser('test')
    a = ap.parse_args()
    if a.cmd == 'fetch':
        # rc distinto de 0 cuando la cosecha se cae: el cron decide con esto si
        # sube o no. Antes salía 0 siempre y una cosecha rota se habría publicado
        # como si fuera buena.
        if fetch(reuse=a.reuse) is None:
            sys.exit(1)
        print("\nlisto. corre 'build' para consolidar.")
    elif a.cmd == 'build':
        build()
    elif a.cmd == 'test':
        sys.exit(0 if test() else 1)


if __name__ == '__main__':
    main()
