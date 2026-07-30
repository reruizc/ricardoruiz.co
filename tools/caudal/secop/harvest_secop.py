#!/usr/bin/env python3
"""
Caudal · harvester del pilar "Datos abiertos y contratación" (SECOP).

FASE 1 — solo AGREGADOS. La búsqueda de contratos NO vive aquí: es en vivo,
contra Socrata ($q full-text, ~1 s), la resuelve la Lambda (acción `contratacion`).
Este script solo precomputa los agregados del landing/dashboards y los sube a S3.

Por qué esta arquitectura (verificada jul-2026 contra jbjy-vk9h, 5,87M contratos):
  · $q full-text sobre el dataset es RÁPIDO (~0,8 s) → búsqueda en vivo, no cabe
    en memoria como los otros pilares (5,87M filas).
  · Los agregados group-by (count/sum SIN like) también son rápidos (2-10 s) →
    se pueden precomputar 1x/día con estas ~10 queries.
  · Lo que hace TIMEOUT (>60 s) es sum()/count() con `like`/`$q` — un agregado
    filtrado por texto libre. Eso NUNCA se hace aquí; por eso los agregados son
    dimensiones cerradas (depto, año, estado, modalidad…), no texto libre.

Fuente única, vía 1 (Socrata / datos.gov.co):
  Dataset "SECOP II · Contratos Electrónicos"  ->  jbjy-vk9h
  Actualización DIARIA (a diferencia del pilar Ejecutivo, que es mensual).
  Campos ricos: nombre_entidad/nit_entidad · proveedor_adjudicado/documento_proveedor
  · objeto_del_contrato · valor_del_contrato · departamento · estado_contrato ·
  codigo_de_categoria_principal (UNSPSC) · modalidad_de_contratacion · orden · sector.

Todo stdlib. curl por subprocess (esquiva el TLS de python 3.14, igual que
scrape_cne.py / harvest_supers.py). Resumible: los agregados ya bajados HOY no se
re-piden (así una corrida que muere a mitad se retoma sin repetir lo hecho).

App token (opcional pero recomendado): exporta SOCRATA_APP_TOKEN=... y se manda
como header X-App-Token — sube el límite de rate de datos.gov.co y evita el
throttling anónimo. Sin token también corre (más lento / más frágil bajo carga).

Uso:
  python3 tools/caudal/secop/harvest_secop.py test      # 1 query chica, valida el endpoint
  python3 tools/caudal/secop/harvest_secop.py fetch      # corre las ~10 queries de agregado
  python3 tools/caudal/secop/harvest_secop.py fetch --force   # re-baja aunque ya estén de hoy
  python3 tools/caudal/secop/harvest_secop.py build      # raw -> dist/s3/secop-stats.json
  # deploy: aws s3 cp "Bases de datos/leyes-senado/secop/dist/s3/secop-stats.json" \
  #   "s3://caudal-legislativo/metadata/secop-stats.json" \
  #   --content-type application/json --cache-control "public, max-age=300"
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = REPO / 'Bases de datos' / 'leyes-senado' / 'secop'
RAW = OUT / 'raw'
DIST_S3 = OUT / 'dist' / 's3'

SOCRATA_DOMAIN = 'www.datos.gov.co'
SOCRATA_ID = 'jbjy-vk9h'
FUENTE_NOMBRE = 'SECOP II · Contratos Electrónicos'
FUENTE_PORTAL = 'datos.gov.co · Colombia Compra Eficiente'
FRECUENCIA = 'Diaria'

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')
APP_TOKEN = os.environ.get('SOCRATA_APP_TOKEN', '').strip()

VALOR = 'valor_del_contrato'
BASE = f'https://{SOCRATA_DOMAIN}/resource/{SOCRATA_ID}.json'

# Cada agregado = una query SoQL group-by (dimensión CERRADA, nunca texto libre).
# `raw` = clave del archivo raw/agg-{raw}.json. `soql` = querystring SoQL cruda.
# `limit` alto en los de alta cardinalidad (entidades/categorías) para el top-N.
# Verificado jul-2026: la más lenta (top entidades) ~9 s; todas <60 s.
AGGREGATES = [
    {'raw': 'total',
     'soql': f'$select=count(1) as n,sum({VALOR}) as v'},
    {'raw': 'por_anio',
     'soql': f'$select=date_trunc_y(fecha_de_firma) as y,count(1) as n,sum({VALOR}) as v'
             '&$group=y&$order=y desc'},
    {'raw': 'por_departamento',
     'soql': f'$select=departamento,count(1) as n,sum({VALOR}) as v'
             '&$group=departamento&$order=n desc&$limit=60'},
    {'raw': 'por_estado',
     'soql': '$select=estado_contrato,count(1) as n'
             '&$group=estado_contrato&$order=n desc&$limit=40'},
    {'raw': 'por_modalidad',
     'soql': f'$select=modalidad_de_contratacion,count(1) as n,sum({VALOR}) as v'
             '&$group=modalidad_de_contratacion&$order=n desc&$limit=40'},
    {'raw': 'por_tipo',
     'soql': f'$select=tipo_de_contrato,count(1) as n,sum({VALOR}) as v'
             '&$group=tipo_de_contrato&$order=n desc&$limit=40'},
    {'raw': 'por_orden',
     'soql': f'$select=orden,count(1) as n,sum({VALOR}) as v'
             '&$group=orden&$order=n desc&$limit=20'},
    {'raw': 'por_sector',
     'soql': f'$select=sector,count(1) as n,sum({VALOR}) as v'
             '&$group=sector&$order=n desc&$limit=60'},
    {'raw': 'top_entidades_valor',
     'soql': f'$select=nombre_entidad,nit_entidad,count(1) as n,sum({VALOR}) as v'
             '&$group=nombre_entidad,nit_entidad&$order=v desc&$limit=50'},
    {'raw': 'top_entidades_n',
     'soql': f'$select=nombre_entidad,nit_entidad,count(1) as n,sum({VALOR}) as v'
             '&$group=nombre_entidad,nit_entidad&$order=n desc&$limit=50'},
    {'raw': 'top_categorias',
     'soql': f'$select=codigo_de_categoria_principal,count(1) as n,sum({VALOR}) as v'
             '&$group=codigo_de_categoria_principal&$order=n desc&$limit=40'},
]


# ---------------------------------------------------------------------------
# Mitigación 1 · CHIPS de dimensión (filtro exacto, sin falsos positivos)
# Cada dimensión cerrada del stats se puede ofrecer como chip. `campo` es la
# columna Socrata para el $where; `dim` es la clave de la sección del stats.
# El frontend matchea lo que el usuario escribe contra `norm` y sugiere el chip
# ("¿buscabas el SECTOR Transporte?") en vez de mandar todo a $q.
CHIP_DIMS = [
    {'dim': 'por_sector',       'campo': 'sector',                    'etiqueta': 'Sector',        'key': 'sector'},
    {'dim': 'por_departamento', 'campo': 'departamento',              'etiqueta': 'Departamento',  'key': 'departamento'},
    {'dim': 'por_modalidad',    'campo': 'modalidad_de_contratacion', 'etiqueta': 'Modalidad',     'key': 'modalidad'},
    {'dim': 'por_tipo',         'campo': 'tipo_de_contrato',          'etiqueta': 'Tipo',          'key': 'tipo'},
    {'dim': 'por_estado',       'campo': 'estado_contrato',           'etiqueta': 'Estado',        'key': 'estado'},
    {'dim': 'por_orden',        'campo': 'orden',                     'etiqueta': 'Orden',         'key': 'orden'},
]

# Mitigación 2 · POR QUÉ MATCHEÓ. $q busca en las 82 columnas, incluidas varias
# que no se muestran (verificado: un box-culvert matcheó 'transporte' por
# `descripcion_documentos_tipo`). Para pintar el badge "matchea por: Sector", la
# Lambda debe traer estas columnas y ver en cuál aparece el término.
# ORDEN = prioridad de atribución (la primera que contenga el término, gana).
COLUMNAS_MATCH = [
    {'campo': 'objeto_del_contrato',           'etiqueta': 'Objeto'},
    {'campo': 'descripcion_del_proceso',       'etiqueta': 'Descripción del proceso'},
    {'campo': 'nombre_entidad',                'etiqueta': 'Entidad'},
    {'campo': 'proveedor_adjudicado',          'etiqueta': 'Proveedor'},
    {'campo': 'sector',                        'etiqueta': 'Sector'},
    {'campo': 'tipo_de_contrato',              'etiqueta': 'Tipo de contrato'},
    {'campo': 'modalidad_de_contratacion',     'etiqueta': 'Modalidad'},
    {'campo': 'descripcion_documentos_tipo',   'etiqueta': 'Tipo de documentos'},
    {'campo': 'departamento',                  'etiqueta': 'Departamento'},
    {'campo': 'ciudad',                        'etiqueta': 'Ciudad'},
    {'campo': 'rama',                          'etiqueta': 'Rama'},
    {'campo': 'referencia_del_contrato',       'etiqueta': 'Referencia'},
]

# NO probar ni mostrar: datos personales. $q SÍ los matchea (buscar un nombre
# propio trae su domicilio), pero publicarlos es otra cosa — mismo criterio que
# build_s3.py de supers, que excluye cédulas del slim. Documentado en el README.
COLUMNAS_PII_EXCLUIDAS = [
    'documento_proveedor', 'identificaci_n_representante_legal',
    'nombre_representante_legal', 'domicilio_representante_legal',
    'nacionalidad_representante_legal', 'g_nero_representante_legal',
    'tipo_de_identificaci_n_representante_legal',
    'nombre_ordenador_del_gasto', 'n_mero_de_documento_ordenador_del_gasto',
    'nombre_supervisor', 'n_mero_de_documento_supervisor',
    'tipo_de_documento_supervisor', 'tipo_de_documento_ordenador_del_gasto',
    'direcci_n_de_ejecuci_n_del_contrato', 'n_mero_de_cuenta', 'nombre_del_banco',
]


def _norm(s):
    """minúsculas sin tildes — para matchear lo que el usuario escribe vs un chip."""
    s = (s or '').lower().strip()
    for a, b in (('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u'),
                 ('ü', 'u'), ('ñ', 'n')):
        s = s.replace(a, b)
    return s


def _encode(soql):
    """SoQL crudo -> querystring URL-safe (espacios y coma; el resto ya es ascii)."""
    return soql.replace(' ', '%20').replace(',', '%2C')


def curl_json(url, timeout=90):
    cmd = ['/usr/bin/curl', '-s', '-A', UA, '--max-time', str(timeout)]
    if APP_TOKEN:
        cmd += ['-H', f'X-App-Token: {APP_TOKEN}']
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout + 10)
    except subprocess.TimeoutExpired:
        return None, 'timeout'
    if r.returncode != 0:
        return None, f'curl rc={r.returncode}'
    body = r.stdout.decode('utf-8', errors='replace')
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        return None, f'json: {e} · body[:120]={body[:120]!r}'
    if isinstance(data, dict) and data.get('error'):
        return None, f"socrata: {data.get('message', data)}"
    return data, None


def _today():
    return datetime.date.today().isoformat()


def _raw_path(name):
    return RAW / f'agg-{name}.json'


def _is_fresh(name):
    """True si el raw existe y fue generado HOY (para la resumibilidad diaria)."""
    p = _raw_path(name)
    if not p.exists():
        return False
    try:
        return json.loads(p.read_text(encoding='utf-8')).get('generado_dia') == _today()
    except (json.JSONDecodeError, OSError):
        return False


def fetch(force=False):
    RAW.mkdir(parents=True, exist_ok=True)
    ok, skip, fail = 0, 0, 0
    for agg in AGGREGATES:
        name = agg['raw']
        if not force and _is_fresh(name):
            print(f"  = {name:24s} (fresco de hoy, se salta)")
            skip += 1
            continue
        url = f"{BASE}?{_encode(agg['soql'])}"
        t0 = time.time()
        data, err = curl_json(url)
        if err:
            print(f"  ! {name:24s} {err}", file=sys.stderr)
            fail += 1
            continue
        _raw_path(name).write_text(json.dumps(
            {'generado_dia': _today(),
             'generado': datetime.datetime.now(datetime.timezone.utc)
                         .replace(microsecond=0).isoformat(),
             'soql': agg['soql'], 'rows': data},
            ensure_ascii=False), encoding='utf-8')
        print(f"  ok {name:24s} {len(data):>4d} filas · {time.time()-t0:4.1f}s")
        ok += 1
        time.sleep(0.3)
    print(f"\nfetch: {ok} bajadas · {skip} frescas · {fail} fallidas")
    if fail:
        print("  (rerun para reintentar las fallidas; las frescas no se repiten)",
              file=sys.stderr)
    return fail == 0


def _rows(name):
    """Filas crudas de un agregado (o [] si no está — build es tolerante)."""
    p = _raw_path(name)
    if not p.exists():
        print(f"  ! falta raw de {name} (corre fetch)", file=sys.stderr)
        return []
    return json.loads(p.read_text(encoding='utf-8')).get('rows', [])


def _i(v):
    """Socrata devuelve números como string; a int (round). None -> 0."""
    if v in (None, ''):
        return 0
    try:
        return round(float(v))
    except (TypeError, ValueError):
        return 0


def build():
    if not RAW.exists():
        print("no hay raw; corre 'fetch' primero", file=sys.stderr)
        sys.exit(1)
    DIST_S3.mkdir(parents=True, exist_ok=True)

    # total (una fila)
    tot_rows = _rows('total')
    tot = tot_rows[0] if tot_rows else {}
    total = {'contratos': _i(tot.get('n')), 'valor_cop': _i(tot.get('v'))}

    def dim(name, key, label, con_valor=True):
        out = []
        for r in _rows(name):
            item = {label: (r.get(key) or '').strip() or '—', 'n': _i(r.get('n'))}
            if con_valor:
                item['valor'] = _i(r.get('v'))
            out.append(item)
        return out

    # por_anio: date_trunc_y da 'YYYY-01-01T...'; sin fecha -> bucket 'sin fecha'
    por_anio = []
    for r in _rows('por_anio'):
        y = (r.get('y') or '')[:4]
        por_anio.append({'anio': y or 'sin fecha', 'n': _i(r.get('n')), 'valor': _i(r.get('v'))})

    def top_entidades(name):
        out = []
        for r in _rows(name):
            out.append({'entidad': (r.get('nombre_entidad') or '—').strip(),
                        'nit': (r.get('nit_entidad') or '').strip(),
                        'n': _i(r.get('n')), 'valor': _i(r.get('v'))})
        return out

    top_categorias = [{'codigo': (r.get('codigo_de_categoria_principal') or '—').strip(),
                       'n': _i(r.get('n')), 'valor': _i(r.get('v'))}
                      for r in _rows('top_categorias')]

    # --- Mitigación 1: índice plano de chips (derivado, sin queries nuevas) ---
    # El frontend lo recorre comparando `norm` con lo que escribe el usuario y
    # ofrece el chip; al aceptarlo manda {campo}={valor} como filtro EXACTO en
    # vez de $q (1,6 s, cero falsos positivos).
    secciones = {'por_departamento': dim('por_departamento', 'departamento', 'departamento'),
                 'por_estado': dim('por_estado', 'estado_contrato', 'estado', con_valor=False),
                 'por_modalidad': dim('por_modalidad', 'modalidad_de_contratacion', 'modalidad'),
                 'por_tipo': dim('por_tipo', 'tipo_de_contrato', 'tipo'),
                 'por_orden': dim('por_orden', 'orden', 'orden'),
                 'por_sector': dim('por_sector', 'sector', 'sector')}
    chips = []
    for cd in CHIP_DIMS:
        for item in secciones.get(cd['dim'], []):
            valor = item.get(cd['key'], '')
            if not valor or valor == '—':
                continue
            chips.append({'dim': cd['dim'], 'campo': cd['campo'],
                          'etiqueta': cd['etiqueta'], 'valor': valor,
                          'norm': _norm(valor), 'n': item.get('n', 0)})
    chips.sort(key=lambda c: c['n'], reverse=True)

    stats = {
        'v': _today(),
        'generado': datetime.datetime.now(datetime.timezone.utc)
                    .replace(microsecond=0).isoformat(),
        'fuente': {
            'id': SOCRATA_ID,
            'nombre': FUENTE_NOMBRE,
            'portal': FUENTE_PORTAL,
            'url': f'https://{SOCRATA_DOMAIN}/resource/{SOCRATA_ID}.json',
            'frecuencia': FRECUENCIA,
        },
        'total': total,
        'por_anio': por_anio,
        'por_departamento': secciones['por_departamento'],
        'por_estado': secciones['por_estado'],
        'por_modalidad': secciones['por_modalidad'],
        'por_tipo': secciones['por_tipo'],
        'por_orden': secciones['por_orden'],
        'por_sector': secciones['por_sector'],
        'chips': chips,                        # mitigación 1 (ver README)
        'columnas_match': COLUMNAS_MATCH,      # mitigación 2 (ver README)
        'columnas_pii_excluidas': COLUMNAS_PII_EXCLUIDAS,
        'top_entidades_valor': top_entidades('top_entidades_valor'),
        'top_entidades_n': top_entidades('top_entidades_n'),
        'top_categorias': top_categorias,
        'nota': ('Agregados precomputados 1x/día. La búsqueda de contratos es en '
                 'vivo (Socrata $q). Los valores COP son crudos del dataset (SECOP '
                 'trae outliers de digitación en valor_del_contrato — no depurados).'),
    }
    out = DIST_S3 / 'secop-stats.json'
    out.write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding='utf-8')

    print(f"stats -> {out.relative_to(REPO)}")
    print(f"  total: {total['contratos']:,} contratos · "
          f"COP {total['valor_cop']:,}")
    print(f"  deptos: {len(stats['por_departamento'])} · años: {len(por_anio)} · "
          f"top entidades: {len(stats['top_entidades_valor'])}")
    faltan = [a['raw'] for a in AGGREGATES if not _raw_path(a['raw']).exists()]
    if faltan:
        print(f"  ! agregados sin raw (secciones vacías): {faltan}", file=sys.stderr)


def test():
    """Query chica: valida endpoint + app token + parseo (no toca raw/dist)."""
    if APP_TOKEN:
        print(f"  app token: presente (…{APP_TOKEN[-4:]})")
    else:
        print("  app token: AUSENTE (corre anónimo; exporta SOCRATA_APP_TOKEN para subir el rate)")
    url = f"{BASE}?{_encode('$select=count(1) as n')}"
    t0 = time.time()
    data, err = curl_json(url, timeout=60)
    if err or not data:
        print(f"FALLA: {err or 'sin filas'}")
        return False
    n = _i(data[0].get('n'))
    print(f"  count total = {n:,} contratos · {time.time()-t0:.1f}s")
    ok = n > 1_000_000
    print('\nTEST OK' if ok else '\nTEST: count sospechosamente bajo — revisar dataset')
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    fp = sub.add_parser('fetch')
    fp.add_argument('--force', action='store_true',
                    help='re-baja aunque el raw ya sea de hoy')
    sub.add_parser('build')
    sub.add_parser('test')
    a = ap.parse_args()
    if a.cmd == 'fetch':
        if fetch(force=a.force):
            print("\nlisto. corre 'build' para emitir dist/s3/secop-stats.json.")
    elif a.cmd == 'build':
        build()
    elif a.cmd == 'test':
        sys.exit(0 if test() else 1)


if __name__ == '__main__':
    main()
