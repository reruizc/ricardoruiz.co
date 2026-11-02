#!/usr/bin/env python3
"""
Caudal · agendas regulatorias 2027 (tanda 0, 1-nov-2026).

Los ministerios y departamentos administrativos debían publicar a más tardar el
31-oct-2026 el proyecto de agenda con lo que piensan regular en 2027 (Decreto 1081
de 2015, art. 2.1.2.2.3; Circular 04 de 2026 de Presidencia). Lo que se agregue
después de esa foto es justo lo que vale avisar, así que cada corrida deja una foto
inmutable y la primera queda como línea base.

  SUCOP      rootfolder/folders?$filter=substringof('2027',Name) → las carpetas de
             agenda; cada una lista sus normas hijas por el campo `Agenda_x003a_ID`
             (la misma consulta CAML de proceso-scripts.js)
  Sitios     MinSalud (ZIP), MinComercio y Función Pública (XLSX) no están en SUCOP,
             aunque la circular lo pide. MinAmbiente y MinDeporte se vigilan en su
             página y en sus sitemaps: su agenda 2026 salió primero como consulta.

⚠️ Una agenda que no se pudo leer NO es una agenda vacía. `leida` lo distingue y
`comparar()` deja esas entidades en `sin_comparar`: nunca salen como normas retiradas.
⚠️ La carpeta de SUCOP también guarda CSV de suscripciones: de ahí solo se listan los
`Agenda*.pdf`, y ninguno se baja.
⚠️ El nombre del responsable técnico no se copia a las filas: es una persona, no un
dato de la norma. Sí queda en el XLSX original, que nunca sale de `raw/`.
⚠️ Los XLSX repiten filas y cabeceras (MinComercio pegó 3 decretos arriba del título)
y `tipo` trae texto libre en MinSalud. Se declara lo que se descarta; `tipo_fuente`
conserva el crudo.
⚠️ Un sitio no tiene id de norma: la clave es un hash de tipo + nombre, y `comparar()`
empareja por parecido antes de llamar entrada y salida a un simple cambio de redacción.

Salida en `Bases de datos/caudal-entidades/raw/agendas/`:
  fotos/agendas-2027-AAAAMMDDTHHMMSS.json   una por corrida, solo lectura
  linea-base.json                           qué foto es la base y su sha256
  originales/<sha>-<nombre>                 lo que respondió cada fuente, sin tocar
  agendas.json                              vista vigente para build.py

Uso: python3 tools/caudal/entidades/harvest_agendas.py fetch [--ensayo]
     python3 tools/caudal/entidades/harvest_agendas.py comparar [--desde F] [--hasta F]
     python3 tools/caudal/entidades/harvest_agendas.py reporte
"""
import argparse
import collections
import datetime
import hashlib
import html
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import warnings
import zipfile
from pathlib import Path

import comun as C

ANIO = '2027'
CORTE = '2026-10-31'
OUT = C.RAW / 'agendas'
FOTOS = OUT / 'fotos'
ORIGINALES = OUT / 'originales'
BASE = OUT / 'linea-base.json'
VISTA = OUT / 'agendas.json'
BOGOTA = datetime.timezone(datetime.timedelta(hours=-5))

SUCOP = 'https://www.sucop.gov.co'
LISTA = f"{SUCOP}/formulacion_/_api/web/lists/getbytitle('Procesos%20SUCOP')"
CT_NORMA = '0x0120D52000ADC5B5AEE85442498F26457AA2D1B36F00'
JSON_SP = 'application/json;odata=nometadata'
CAMPOS_NORMA = ('nombreProyecto', 'Title', 'Codigo', 'TipoNormativa', 'EstadoNormativa', 'estadoView', 'Objeto',
                'comisionTema', 'comisionObjeto', 'NormativaConcreta', 'OrigenIniciativa', 'DependenciaTecnica',
                'FechadePublicacion', 'FechaInicioComentarios', 'FechaFinComentarios', 'Created', 'Modified', 'ID')

# Las 13 obligadas: `k` es la misma clave de catalogo.py.
OBLIGADAS = [
    dict(k='mintrabajo', nombre='Ministerio del Trabajo', alias='ministerio del trabajo'),
    dict(k='minvivienda', nombre='Ministerio de Vivienda, Ciudad y Territorio', alias='ministerio de vivienda'),
    dict(k='minsalud', nombre='Ministerio de Salud y Protección Social', alias='ministerio de salud'),
    dict(k='mineducacion', nombre='Ministerio de Educación Nacional', alias='ministerio de educacion'),
    dict(k='mincultura', nombre='Ministerio de las Culturas, las Artes y los Saberes', alias='ministerio de las culturas'),
    dict(k='mincomercio', nombre='Ministerio de Comercio, Industria y Turismo', alias='ministerio de comercio'),
    dict(k='minagricultura', nombre='Ministerio de Agricultura y Desarrollo Rural', alias='ministerio de agricultura'),
    dict(k='minambiente', nombre='Ministerio de Ambiente y Desarrollo Sostenible', alias='ministerio de ambiente'),
    dict(k='mindeporte', nombre='Ministerio del Deporte', alias='ministerio del deporte'),
    dict(k='minhacienda', nombre='Ministerio de Hacienda y Crédito Público', alias='ministerio de hacienda'),
    dict(k='dnp', nombre='Departamento Nacional de Planeación', alias='nacional de planeacion'),
    dict(k='funcionpublica', nombre='Departamento Administrativo de la Función Pública', alias='funcion publica'),
    dict(k='presidencia', nombre='Departamento Administrativo de la Presidencia de la República', alias='presidencia de la republica'),
]
PUBLICADA = ('publicada', 'publicada_sin_normas', 'publicada_sin_leer')


def _ahora():
    return datetime.datetime.now(BOGOTA).replace(microsecond=0)


def _agenda(k, entidad, obligada, estado, via, url, nota='', **extra):
    """Estados: publicada · publicada_sin_normas (se leyó y no trae filas) ·
    publicada_sin_leer (existe, pero no se pudo extraer) · en_formulacion (SUCOP aún no la
    abre a consulta) · no_publicada (se leyó la fuente y no está) · no_leida."""
    return {'k': k, 'entidad': entidad, 'obligada': obligada, 'estado': estado, 'leida': estado not in ('no_leida', 'publicada_sin_leer'),
            'publicada': estado in PUBLICADA, 'via': via, 'url': url, 'n_normas': 0, 'nota': nota, 'estado_fuente': '',
            'consulta_inicio': '', 'consulta_fin': '', 'version': '', 'originales': [], 'descartes': {}, **extra}


def _original(datos, nombre):
    """Guarda lo que respondió la fuente, una sola vez: el nombre lleva su hash."""
    sha = hashlib.sha256(datos).hexdigest()
    limpio = re.sub(r'[^A-Za-z0-9._-]+', '-', nombre)[-80:]
    p = ORIGINALES / f'{sha[:16]}-{limpio}'
    if not p.exists():
        ORIGINALES.mkdir(parents=True, exist_ok=True)
        p.write_bytes(datos)
        p.chmod(0o444)
    return {'archivo': p.name, 'sha256': sha, 'bytes': len(datos)}


def _texto(s):
    """Sin correos: los avisos y formatos a veces traen el de un funcionario."""
    return C.limpio(re.sub(r'\S+@\S+', ' ', html.unescape(str(s or ''))))


def _clave_sitio(k, tipo, nombre):
    return f"{k}:{hashlib.sha1(C.fold(f'{tipo}|{nombre}').encode()).hexdigest()[:16]}"


# ── SUCOP ──────────────────────────────────────────────────────────────────────
def _lab(v):
    return ((v.get('Label') if isinstance(v, dict) else v) or '').strip()


def _post(url, cuerpo=None, digest=''):
    cmd = ['/usr/bin/curl', '-s', '--max-time', '90', '-A', C.UA, '-X', 'POST', '-H', f'Accept: {JSON_SP}', '-w', '\n%{http_code}']
    cmd += ['-H', f'Content-Type: {JSON_SP}', '-H', f'X-RequestDigest: {digest}', '--data', cuerpo] if cuerpo else ['-H', 'Content-Length: 0']
    ultimo = ''
    for i in range(3):
        r = subprocess.run(cmd + [url], capture_output=True, timeout=110)
        cuerpo_r, _, code = r.stdout.decode('utf-8', 'replace').rpartition('\n')
        if r.returncode == 0 and code == '200':
            return json.loads(cuerpo_r)
        ultimo = f'rc={r.returncode} http={code}'
        time.sleep(3 * (i + 1))
    raise RuntimeError(f'{ultimo} en {url[:100]}')


def procesos_sucop():
    """Las carpetas de agenda 2027. `substringof` también trae las normas (PN-2027-…) y
    las descarta `EstadoAgenda`."""
    li = ','.join('ListItemAllFields/' + f for f in ('Id', 'Entidad', 'Anio', 'EstadoNormativa', 'EstadoAgenda', 'estadoView',
                                                      'FechaInicioComentarios', 'FechaFinComentarios', 'MostrarLink', 'Modified'))
    u = (f"{LISTA}/rootfolder/folders?$expand=ListItemAllFields&$select=Name,{li}"
         f"&$filter=substringof('{ANIO}',Name)&$top=3000")
    out = []
    for f in json.loads(C.curl(u, accept=JSON_SP, timeout=150))['value']:
        x = f.get('ListItemAllFields') or {}
        if f['Name'].startswith('PN-') or _lab(x.get('Anio')) != ANIO or _lab(x.get('EstadoNormativa')) or not _lab(x.get('EstadoAgenda')):
            continue
        if C.fold(_lab(x.get('Entidad'))) == 'entidad ejemplo':      # datos de prueba del propio SUCOP
            continue
        link = x.get('MostrarLink') or {}
        out.append({'id': x['Id'], 'carpeta': f['Name'], 'entidad': _lab(x.get('Entidad')), 'estado': _lab(x.get('EstadoAgenda')),
                    'vista': (x.get('estadoView') or '').strip(), 'inicio': (x.get('FechaInicioComentarios') or '')[:10],
                    'fin': (x.get('FechaFinComentarios') or '')[:10], 'url': (link.get('Url') or '').strip() if isinstance(link, dict) else ''})
    return out


def normas_sucop(id_agenda, digest):
    vista = ''.join(f"<FieldRef Name='{c}'/>" for c in CAMPOS_NORMA)
    xml = (f'<View><Query><Where><And><Eq><FieldRef Name="Agenda_x003a_ID"/><Value Type="Lookup">{id_agenda}</Value></Eq>'
           f'<BeginsWith><FieldRef Name="ContentTypeId"/><Value Type="ContentTypeId">{CT_NORMA}</Value></BeginsWith></And></Where></Query>'
           f'<ViewFields>{vista}</ViewFields></View>')
    return _post(f'{LISTA}/getitems', json.dumps({'query': {'ViewXml': xml}}), digest)['value']


def versiones_sucop(id_agenda):
    """Solo nombres y fechas de los `Agenda*.pdf`: cada modificación sube una versión."""
    u = f"{LISTA}/items({id_agenda})/Folder/Files?$select=Name,TimeLastModified,ServerRelativeUrl"
    xs = [x for x in json.loads(C.curl(u, accept=JSON_SP, timeout=60))['value'] if x['Name'].startswith('Agenda')]
    nums = [int(n) for x in xs for n in re.findall(r'versi[oó]n (\d+)', x['Name'])]
    return (str(max(nums)) if nums else ('consulta pública' if xs else '')), len(xs)


def fila_sucop(r, ag, base):
    tema = _texto(r.get('Objeto') or r.get('comisionObjeto') or r.get('comisionTema'))
    return {**base, 'clave': f"sucop:{r['Id']}", 'nombre': _texto(r.get('nombreProyecto') or r.get('Title')).strip('"“” '),
            'tema': tema, 'tipo_norma': _lab(r.get('TipoNormativa')) or 'No especificado', 'tipo_fuente': _lab(r.get('TipoNormativa')),
            'fecha_prevista': (r.get('FechadePublicacion') or '')[:10], 'fecha_texto': '', 'norma_concreta': _texto(r.get('NormativaConcreta')),
            'dependencia': _texto(r.get('DependenciaTecnica')), 'origen': _lab(r.get('OrigenIniciativa')), 'estado': (r.get('estadoView') or '').strip(),
            'codigo': r.get('Codigo') or '', 'via': 'sucop', 'url': f"{SUCOP}/entidades/{ag['carpeta'][:-4]}/Normativa?IDNorma={r['Id']}"}


def leer_sucop(p, k, obligada, digest, capturado):
    crudas = normas_sucop(p['id'], digest)
    base = {'k': k, 'entidad': p['entidad'], 'obligada': obligada, 'anio': ANIO, 'capturado': capturado}
    filas = [fila_sucop(r, p, base) for r in crudas]
    formulacion = C.fold(p['estado']) in ('formulacion', 'en ajustes')
    estado = 'en_formulacion' if formulacion else 'publicada' if filas else 'publicada_sin_normas'
    version, n_pdf = versiones_sucop(p['id'])
    a = _agenda(k, p['entidad'], obligada, estado, 'sucop', p['url'], f'{n_pdf} PDF en SUCOP' if n_pdf else '',
                id_sucop=p['id'], estado_fuente=p['vista'] or p['estado'], consulta_inicio=p['inicio'], consulta_fin=p['fin'], version=version,
                n_normas=len(filas), originales=[_original(json.dumps(crudas, ensure_ascii=False, sort_keys=True).encode(), f"sucop-{p['id']}.json")])
    return a, filas


# ── libros de Excel ────────────────────────────────────────────────────────────
COLS = {'nombre': 'nombre del proyecto', 'dependencia': 'dependencia tecnica', 'tema': 'tema u objeto', 'norma_concreta': 'norma concreta',
        'tipo': 'tipo de instrumento', 'origen': 'origen de la iniciativa', 'fecha': 'fecha de inicio del proceso de consulta'}
_TIPOS = (('decreto', 'Decreto'), ('resolucion', 'Resolución'), ('circular', 'Circular'), ('directiva', 'Directiva'), ('acuerdo', 'Acuerdo'),
          ('acto administrativo', 'Acto administrativo'), ('ley', 'Ley'), ('concepto', 'Concepto'))


def tipo_norma(s):
    t = C.fold(s)
    pos = [(t.find(p), n) for p, n in _TIPOS if p in t]
    return min(pos)[1] if pos else 'No especificado'


def fecha_celda(v):
    """(ISO, texto): el texto se conserva cuando la entidad escribió otra cosa que una fecha."""
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.strftime('%Y-%m-%d'), ''
    t = _texto(v)
    if not t or C.fold(t) in ('n/a', 'na', 'no aplica'):
        return '', ''
    m = re.search(r'\b(\d{1,2})/(\d{1,2})/(20\d{2})\b', t)
    return (f'{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}' if m else C.fecha_larga(t)), t[:160]


def _hojas(datos):
    if datos[:4] == b'\xd0\xcf\x11\xe0':
        import xlrd                       # .xls: MinDeporte. Si falta, la agenda queda no_leida
        wb = xlrd.open_workbook(file_contents=datos)
        for s in wb.sheets():
            if s.visibility == 0:
                yield [[xlrd.xldate_as_datetime(c.value, wb.datemode) if c.ctype == 3 else c.value for c in s.row(i)] for i in range(s.nrows)]
        return
    import openpyxl
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')   # «Data Validation extension is not supported»
        wb = openpyxl.load_workbook(io.BytesIO(datos), data_only=True)
    for s in wb.worksheets:
        if s.sheet_state == 'visible':
            yield [list(f) for f in s.iter_rows(values_only=True)]


def filas_de_libro(datos):
    """Filas crudas del formato de la Resolución 371 de 2020, en cualquier hoja visible y
    con cabeceras repetidas. ValueError si no aparece el formato: eso no es una agenda vacía."""
    out, hubo_cabecera, sin_nombre = [], False, 0
    for hoja in _hojas(datos):
        mapa = None
        for fila in hoja:
            txt = [C.fold(str(x)) if x not in (None, '') else '' for x in fila]
            if any(t.startswith('nombre del proyecto') for t in txt):
                mapa = {k: next((i for i, t in enumerate(txt) if pat in t), None) for k, pat in COLS.items()}
                hubo_cabecera = True
                continue
            if mapa is None:
                continue
            g = lambda c: fila[mapa[c]] if mapa[c] is not None and mapa[c] < len(fila) else None
            nombre, tipo, tema = _texto(g('nombre')), _texto(g('tipo')), _texto(g('tema'))
            if not tipo and not tema:     # bloque del título, notas y filas en blanco
                continue
            if not nombre:
                sin_nombre += 1
                continue
            iso, texto = fecha_celda(g('fecha'))
            out.append({'nombre': nombre, 'tema': tema, 'tipo_fuente': tipo[:120], 'tipo_norma': tipo_norma(tipo), 'fecha_prevista': iso, 'fecha_texto': texto,
                        'norma_concreta': _texto(g('norma_concreta')), 'dependencia': _texto(g('dependencia')), 'origen': _texto(g('origen'))})
    if not hubo_cabecera:
        raise ValueError('el libro no trae el formato de agenda')
    return out, sin_nombre


def libros_de(datos):
    """XLSX, XLS o ZIP de ellos. [] si es otra cosa (un PDF, por ejemplo)."""
    if datos[:4] == b'\xd0\xcf\x11\xe0':
        return [datos]
    if datos[:2] != b'PK':
        return []
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        nombres = z.namelist()
        if 'xl/workbook.xml' in nombres:
            return [datos]
        return [z.read(n) for n in nombres if re.search(r'(?i)\.xlsx?$', n) and '__MACOSX' not in n]


def _bajar(url):
    with tempfile.NamedTemporaryFile() as t:
        C.curl(url.replace(' ', '%20'), salida=t.name, timeout=120)
        return Path(t.name).read_bytes()


def _pagina(url):
    """HTML o None si responde 404. Otro error sube: eso es no haber podido leer."""
    try:
        return html.unescape(C.curl(url, timeout=90, intentos=2))
    except RuntimeError as e:
        if 'http=404' in str(e):
            return None
        raise


def _enlaces(h, base):
    out = []
    for attrs, dentro in re.findall(r'(?is)<a\b([^>]*)>(.*?)</a>', h):
        m = re.search(r'''href=["']([^"']+)["']''', attrs)
        t = re.search(r'''title=["']([^"']*)["']''', attrs)
        if m and not m.group(1).startswith(('mailto:', '#', 'javascript:')):
            out.append((urllib.parse.urljoin(base, m.group(1)), C.limpio(f"{t.group(1) if t else ''} {dentro}")))
    return out


def desde_archivo(ob, url, pagina, capturado, nota=''):
    """Baja el archivo de la agenda y lo vuelve filas. Si es un PDF la agenda existe, pero
    no se pudo extraer: se guarda el archivo y no se dice que esté vacía."""
    k = ob['k']
    datos = _bajar(url)
    orig = [_original(datos, urllib.parse.unquote(url.split('?')[0].rstrip('/').rsplit('/', 1)[-1]))]
    libros = libros_de(datos)
    if not libros:
        return _agenda(k, ob['nombre'], True, 'publicada_sin_leer', 'sitio', pagina, f'{nota} No es un libro de Excel: falta leerlo.'.strip(),
                       archivo=url, originales=orig), []
    base = {'k': k, 'entidad': ob['nombre'], 'obligada': True, 'anio': ANIO, 'capturado': capturado}
    vistas, cuenta = {}, collections.Counter()
    for libro in libros:
        crudas, s = filas_de_libro(libro)
        cuenta['sin_nombre'] += s
        for r in crudas:
            raiz, n = _clave_sitio(k, r['tipo_norma'], r['nombre']), 1
            clave = raiz
            while clave in vistas and vistas[clave]['tema'] != r['tema']:      # mismo título con otro objeto: son dos normas
                n += 1
                clave = f'{raiz}-{n}'
            if clave not in vistas:
                vistas[clave] = {**base, **r, 'clave': clave, 'estado': '', 'codigo': '', 'via': 'sitio', 'url': pagina}
                continue
            # MinSalud pegó un bloque dos veces, y solo la segunda copia trae la fecha.
            cuenta['repetidas'] += 1
            f = vistas[clave]
            if not _fecha(f) and _fecha(r):
                f['fecha_prevista'], f['fecha_texto'] = r['fecha_prevista'], r['fecha_texto']
                cuenta['fecha_de_la_repetida'] += 1
            elif _fecha(r) and _fecha(r) != _fecha(f):
                f['fecha_alterna'] = r['fecha_prevista'] or r['fecha_texto']
                cuenta['fechas_en_conflicto'] += 1
    filas = list(vistas.values())
    return _agenda(k, ob['nombre'], True, 'publicada' if filas else 'publicada_sin_normas', 'sitio', pagina, nota, archivo=url,
                   n_normas=len(filas), originales=orig, descartes=dict(cuenta)), filas


# ── sitios propios: cada uno devuelve (agenda, filas) ──────────────────────────
def minsalud(ob, capturado):
    u = 'https://www.minsalud.gov.co/Normativa/Paginas/agenda-regulatoria.aspx'
    h = _pagina(u)
    if h is None:
        raise RuntimeError('la página de agenda dio 404')
    xs = [l for l in _enlaces(h, u) if ANIO in l[0] + l[1] and re.search(r'(?i)\.(zip|xlsx?|pdf)$', l[0])]
    if not xs:
        return _agenda('minsalud', ob['nombre'], True, 'no_publicada', 'sitio', u, 'Su página de agenda no lista 2027.'), []
    return desde_archivo(ob, xs[0][0], u, capturado, f'«{xs[0][1]}» en su página.')


def mincomercio(ob, capturado):
    u = f'https://www.mincit.gov.co/normatividad/agenda-regulatoria/agenda-regulatoria-{ANIO}'
    h = _pagina(u)
    if h is None:
        return _agenda('mincomercio', ob['nombre'], True, 'no_publicada', 'sitio', u, f'Su página de agenda {ANIO} da 404.'), []
    xs = [l[0] for l in _enlaces(h, u) if re.search(rf'agenda-regulatoria-{ANIO}/[^/]+\.\w+', l[0])]
    if not xs:
        raise RuntimeError('la página 2027 existe, pero no se encontró el archivo')
    return desde_archivo(ob, xs[0], u, capturado, 'En su página; no está en SUCOP.')


def funcionpublica(ob, capturado):
    u = 'https://www1.funcionpublica.gov.co/agenda-regulatoria'
    h = _pagina(u)
    if h is None:
        raise RuntimeError('la página de agenda dio 404')
    m = re.search(rf'(?s)Año {ANIO}(.*?)(?:Año 20\d\d|$)', h)
    if not m:
        return _agenda('funcionpublica', ob['nombre'], True, 'no_publicada', 'sitio', u, f'Su página no tiene el bloque Año {ANIO}.'), []
    xs = [l for l in _enlaces(m.group(1), u) if '/documents/' in l[0]]
    if not xs:
        raise RuntimeError(f'el bloque Año {ANIO} no trae archivos')
    url, texto = max(xs, key=lambda l: int((re.search(r'[?&]t=(\d+)', l[0]) or [0, 0])[1]))   # el más reciente
    return desde_archivo(ob, url, u, capturado, f'«{texto}» en su página; no está en SUCOP.')


def minambiente(ob, capturado):
    u = 'https://www.minambiente.gov.co/normativa/agenda-regulatoria/'
    h = _pagina(u)
    if h is None:
        raise RuntimeError('la página de agenda dio 404')
    xs = [l[0] for l in _enlaces(h, u) if ANIO in l[0] + l[1] and re.search(r'(?i)\.(xlsx?|pdf)$', l[0])]
    if xs:
        return desde_archivo(ob, xs[0], u, capturado)
    consultas = [x for x in re.findall(r'<loc>([^<]+)</loc>', C.curl('https://www.minambiente.gov.co/consulta-sitemap.xml', timeout=60))
                 if re.search(rf'agenda-regulatoria.*{ANIO}', x)]
    if not consultas:
        return _agenda('minambiente', ob['nombre'], True, 'no_publicada', 'sitio', u,
                       f'Ni su página de agenda ni su sitemap de consultas traen {ANIO}. La última es la V4 de 2026.'), []
    h = _pagina(consultas[0]) or ''
    xs = [l[0] for l in _enlaces(h, consultas[0]) if re.search(r'(?i)\.(xlsx?|pdf)$', l[0])]
    if not xs:
        raise RuntimeError(f'hay consulta {consultas[0]}, pero sin archivo')
    return desde_archivo(ob, xs[0], consultas[0], capturado, 'En consulta en su sitio; no está en SUCOP.')


def mindeporte(ob, capturado):
    raiz = 'https://www.mindeporte.gov.co/transparencia-y-acceso-a-informacion-publica/2-normativa/2-1-normatividad'
    candidatas = [f'{raiz}/agenda-regulatoria/{ANIO}']
    candidatas += [x for x in re.findall(r'<loc>([^<]+)</loc>', C.curl('https://www.mindeporte.gov.co/sitemap.xml', timeout=120))
                   if re.search(rf'agenda-regulatoria[/-]{ANIO}', x) and x not in candidatas]
    for u in candidatas:
        h = _pagina(u)
        if h is None:
            continue
        xs = [l[0] for l in _enlaces(h, u) if re.search(r'(?i)/files/.+\.(xlsx?|pdf)$', l[0])]
        if not xs:
            raise RuntimeError(f'{u} existe, pero sin archivo')
        return desde_archivo(ob, xs[0], u, capturado, 'En su sitio; no está en SUCOP.')
    return _agenda('mindeporte', ob['nombre'], True, 'no_publicada', 'sitio', f'{raiz}/agenda-regulatoria',
                   f'Su página {ANIO} da 404 y su sitemap no la trae. Su página de agenda llega hasta 2026.'), []


SITIOS = {'minsalud': minsalud, 'mincomercio': mincomercio, 'funcionpublica': funcionpublica, 'minambiente': minambiente, 'mindeporte': mindeporte}


# ── captura ────────────────────────────────────────────────────────────────────
def _obligada(entidad):
    f = C.fold(entidad)
    return next((o for o in OBLIGADAS if o['alias'] in f), None)


def aplicar_guarda(agendas, prev):
    """La guarda de Caudal, por entidad: si trae mucho menos que la corrida anterior la
    agenda deja de contar como leída. Sus filas quedan en la foto, pero la vista conserva
    las anteriores. Si la caída es real, la corrida siguiente ya no la frena y aparece
    contra la línea base."""
    antes = {a['k']: a for a in (prev or {}).get('agendas', [])}
    for a in agendas:
        p = antes.get(a['k'])
        if not p or not p['leida'] or not a['leida'] or not p['n_normas']:
            continue
        if a['n_normas'] == 0 or (p['n_normas'] >= 4 and a['n_normas'] < p['n_normas'] * .5):
            a['leida'] = False
            a['guarda'] = True
            a['nota'] = f"Guarda: trajo {a['n_normas']} normas y la corrida anterior {p['n_normas']}. {a['nota']}".strip()
    return agendas


def capturar(prev=None):
    capturado = _ahora().isoformat()
    agendas, filas, sucop_ok = {}, [], True
    try:
        procesos = procesos_sucop()
        digest = _post(f'{SUCOP}/formulacion_/_api/contextinfo')['FormDigestValue']
        print(f'  sucop · {len(procesos)} agendas {ANIO}')
    except Exception as e:
        procesos, digest, sucop_ok = [], '', False
        print(f'  sucop · FALLÓ el listado ({e})', file=sys.stderr)
    for p in procesos:
        ob = _obligada(p['entidad'])
        k = ob['k'] if ob else re.sub(r'\W+', '', p['carpeta'][:-4]).lower()
        try:
            a, fs = leer_sucop(p, k, bool(ob), digest, capturado)
        except Exception as e:
            a, fs = _agenda(k, p['entidad'], bool(ob), 'no_leida', 'sucop', p['url'], f'Falló la lectura: {e}'[:200], id_sucop=p['id']), []
            print(f"  {k} · FALLÓ ({e})", file=sys.stderr)
        agendas[k] = a
        filas += fs
    for ob in OBLIGADAS:
        k = ob['k']
        if k in agendas and agendas[k]['estado'] not in ('en_formulacion',):
            continue
        if k in SITIOS:
            try:
                a, fs = SITIOS[k](ob, capturado)
            except Exception as e:
                a, fs = _agenda(k, ob['nombre'], True, 'no_leida', 'sitio', '', f'Falló la lectura: {e}'[:200]), []
                print(f'  {k} · FALLÓ ({e})', file=sys.stderr)
            if k in agendas and a['estado'] in ('no_publicada', 'no_leida'):
                continue                  # lo poco que hay está en SUCOP
            if k in agendas:
                filas = [f for f in filas if f['k'] != k]
            agendas[k], filas = a, filas + fs
        elif k not in agendas:
            agendas[k] = _agenda(k, ob['nombre'], True, 'no_publicada' if sucop_ok else 'no_leida', 'sucop', f'{SUCOP}/Paginas/busqueda-beta.aspx',
                                 f'SUCOP no tiene proceso de agenda {ANIO}.' if sucop_ok else 'SUCOP no respondió.')
    # Lo que estaba en la foto anterior y esta vez no apareció no se da por retirado.
    for a in (prev or {}).get('agendas', []):
        if a['k'] not in agendas:
            agendas[a['k']] = _agenda(a['k'], a['entidad'], a['obligada'], 'no_leida', a['via'], a['url'], 'No apareció en esta corrida.')
    orden = sorted(agendas.values(), key=lambda a: (not a['obligada'], C.fold(a['entidad'])))
    return {'esquema': 1, 'anio': ANIO, 'corte_legal': CORTE, 'capturado': capturado, 'sucop_ok': sucop_ok,
            'agendas': aplicar_guarda(orden, prev), 'filas': filas}


def fotos():
    return sorted(FOTOS.glob(f'agendas-{ANIO}-*.json'))


def guardar_foto(foto):
    """Una foto nunca se reescribe: se abre en modo exclusivo y queda en solo lectura. La
    primera con SUCOP en pie es la línea base; una vez creada, `linea-base.json` no cambia."""
    base = C.leer(BASE)
    foto['linea_base'] = base is None and foto['sucop_ok']
    FOTOS.mkdir(parents=True, exist_ok=True)
    nombre = f"agendas-{ANIO}-{re.sub(r'[-:]', '', foto['capturado'][:19])}.json"
    cuerpo = json.dumps(foto, ensure_ascii=False, indent=1).encode()
    with open(FOTOS / nombre, 'xb') as f:
        f.write(cuerpo)
    (FOTOS / nombre).chmod(0o444)
    if foto['linea_base']:
        with open(BASE, 'x', encoding='utf-8') as f:
            json.dump({'foto': nombre, 'capturado': foto['capturado'], 'sha256': hashlib.sha256(cuerpo).hexdigest()}, f, ensure_ascii=False, indent=1)
        BASE.chmod(0o444)
    return nombre


def cargar_base():
    b = C.leer(BASE)
    if not b:
        return None
    datos = (FOTOS / b['foto']).read_bytes()
    if hashlib.sha256(datos).hexdigest() != b['sha256']:
        raise RuntimeError(f"la línea base {b['foto']} cambió: no coincide su sha256")
    return json.loads(datos)


# ── comparación ────────────────────────────────────────────────────────────────
_VACIAS = {'proyecto', 'decreto', 'resolucion', 'cual', 'para', 'articulo', 'medio', 'sobre', 'como', 'esta', 'este', 'modifica', 'adiciona'}


def _palabras(s):
    return {x for x in re.findall(r'[a-z0-9]{4,}', C.fold(s)) if x not in _VACIAS}


def parecido(a, b):
    """Jaccard de palabras. Si citan números distintos son normas distintas, aunque el
    resto del título sea igual («modifica la Resolución 2335» y «… la Resolución 1211»)."""
    if set(re.findall(r'\d{2,}', a)) != set(re.findall(r'\d{2,}', b)):
        return 0
    x, y = _palabras(a), _palabras(b)
    return len(x & y) / len(x | y) if x | y else 0


def _fecha(f):
    return f.get('fecha_prevista') or C.fold(f.get('fecha_texto'))


def _dias(a, b):
    try:
        return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days
    except (TypeError, ValueError):
        return None


def _resumen_fila(f):
    return {k: f.get(k, '') for k in ('clave', 'k', 'entidad', 'nombre', 'tipo_norma', 'url')}


def _emparejar(viejas, nuevas, umbral=.7):
    """Parejas de filas que son la misma norma con otra clave. Dos id de SUCOP nunca se
    emparejan: ese id es la identidad. Solo aplica si una de las claves es un hash."""
    candidatas = sorted(((parecido(v['nombre'], n['nombre']), v['clave'], n['clave']) for v in viejas for n in nuevas
                         if not (v['clave'].startswith('sucop:') and n['clave'].startswith('sucop:'))), reverse=True)
    usadas, parejas = set(), {}
    for p, v, n in candidatas:
        if p >= umbral and v not in usadas and n not in usadas:
            usadas |= {v, n}
            parejas[v] = n
    return parejas


def _comparar_filas(fa, fb, r):
    a, b = {f['clave']: f for f in fa}, {f['clave']: f for f in fb}
    parejas = _emparejar([f for c, f in a.items() if c not in b], [f for c, f in b.items() if c not in a])
    for c, f in a.items():
        destino = c if c in b else parejas.get(c)
        if destino is None:
            r['salen'].append(_resumen_fila(f))
            continue
        g = b[destino]
        if _fecha(f) != _fecha(g):
            d = _dias(f.get('fecha_prevista'), g.get('fecha_prevista'))
            r['cambian_fecha'].append({**_resumen_fila(g), 'de': _fecha(f), 'a': _fecha(g), 'dias': d,
                                       'sentido': '' if d is None else 'se aplaza' if d > 0 else 'se adelanta'})
        campos = {x: [f.get(x, ''), g.get(x, '')] for x in ('nombre', 'tema', 'tipo_norma', 'estado')
                  if f.get(x, '') != g.get(x, '') and not (f['clave'] != g['clave'] and x == 'estado')}
        if campos or destino != c:
            r['cambian_otro'].append({**_resumen_fila(g), 'clave_antes': c, 'campos': campos})
    destinos = set(parejas.values())
    r['entran'] += [{**_resumen_fila(f), 'motivo': 'agregada'} for c, f in b.items() if c not in a and c not in destinos]


def comparar(a, b):
    """Qué cambió de la foto `a` a la `b`. Una entidad solo se compara si se leyó en las
    dos: lo no leído va a `sin_comparar`, sin inventar entradas ni salidas."""
    ea, eb = {x['k']: x for x in a['agendas']}, {x['k']: x for x in b['agendas']}
    fa, fb = collections.defaultdict(list), collections.defaultdict(list)
    for f in a['filas']:
        fa[f['k']].append(f)
    for f in b['filas']:
        fb[f['k']].append(f)
    r = {'desde': a['capturado'], 'hasta': b['capturado'], 'entran': [], 'salen': [], 'cambian_fecha': [], 'cambian_otro': [],
         'agendas_nuevas': [], 'agendas_cambian': [], 'sin_comparar': []}

    def aparte(k, motivo):
        r['sin_comparar'].append({'k': k, 'motivo': motivo, 'normas_desde': len(fa[k]), 'normas_hasta': len(fb[k])})

    for k in sorted(set(ea) | set(eb)):
        xa, xb = ea.get(k), eb.get(k)
        if xb is None:
            aparte(k, 'no aparece en la foto nueva')
        elif not xb['leida']:
            aparte(k, xb['nota'] or 'no se pudo leer en la foto nueva')
        elif xa is not None and not xa['leida']:
            aparte(k, 'no se pudo leer en la foto vieja: no se sabe qué tenía')
        elif not fb[k] and fa[k]:
            aparte(k, 'la agenda ya no aparece en la fuente: no se dan sus normas por retiradas')
        elif not fa[k]:
            if fb[k]:
                nueva = xa is None or not xa['publicada']
                if nueva:
                    r['agendas_nuevas'].append(k)
                r['entran'] += [{**_resumen_fila(f), 'motivo': 'agenda_nueva' if nueva else 'agregada'} for f in fb[k]]
        else:
            _comparar_filas(fa[k], fb[k], r)
        if xa and xb and xa['leida'] and xb['leida']:
            cambios = {c: [xa.get(c, ''), xb.get(c, '')] for c in ('estado', 'estado_fuente', 'version', 'via') if xa.get(c, '') != xb.get(c, '')}
            if cambios:
                r['agendas_cambian'].append({'k': k, 'entidad': xb['entidad'], 'campos': cambios})
    r['resumen'] = {c: len(r[c]) for c in ('entran', 'salen', 'cambian_fecha', 'cambian_otro', 'agendas_nuevas', 'agendas_cambian', 'sin_comparar')}
    return r


def armar_vista(foto, nombre, base, anterior, vista_prev):
    """Lo vigente para build.py. Si una agenda no se leyó se conservan sus filas de la
    última vista, marcadas, para que un sitio caído no borre la agenda del panel."""
    leidas = {a['k'] for a in foto['agendas'] if a['leida']}
    filas = [dict(f) for f in foto['filas'] if f['k'] in leidas]
    filas += [{**f, 'conservada': True} for f in (vista_prev or {}).get('filas', []) if f['k'] not in leidas]
    vs_base = comparar(base, foto) if base else None
    vs_prev = comparar(anterior, foto) if anterior else None
    if vs_base:
        marca = {f['clave']: {'novedad': f['motivo']} for f in vs_base['entran']}
        marca.update({f['clave']: {'novedad': 'fecha_cambiada', 'fecha_base': f['de']} for f in vs_base['cambian_fecha']})
        filas = [{**f, **marca.get(f['clave'], {})} for f in filas]
    return {'generado': foto['capturado'], 'foto': nombre, 'linea_base': (C.leer(BASE) or {}).get('foto', ''), 'agendas': foto['agendas'], 'filas': filas,
            'vs_linea_base': vs_base, 'vs_anterior': vs_prev}


# ── reporte y CLI ──────────────────────────────────────────────────────────────
ESTADOS = {'publicada': 'Publicada', 'publicada_sin_normas': 'Publicada, sin normas', 'publicada_sin_leer': 'Publicada, NO se pudo leer',
           'en_formulacion': 'En formulación (sin publicar)', 'no_publicada': 'No publicada', 'no_leida': 'NO se pudo leer'}


def reporte(foto, solo_obligadas=False):
    filas = ['| Entidad | Estado | Normas | Con fecha | Fuente | Nota |', '|---|---|---:|---:|---|---|']
    conf = collections.Counter(f['k'] for f in foto['filas'] if f.get('fecha_prevista'))
    for a in foto['agendas']:
        if solo_obligadas and not a['obligada']:
            continue
        estado = ESTADOS[a['estado']] + (' (guarda)' if a.get('guarda') else '')
        cuenta = str(a['n_normas']) if a['leida'] or a['n_normas'] else '—'
        filas.append(f"| {a['entidad']} | {estado} | {cuenta} | {conf[a['k']] if a['n_normas'] else '—'} | {a['via']} | {a['nota']} |")
    return '\n'.join(filas)


def fetch(ensayo=False):
    anterior = json.loads(fotos()[-1].read_bytes()) if fotos() else None
    foto = capturar(anterior)
    print(reporte(foto))
    if ensayo:
        print('\n(ensayo: no se guardó foto)')
        return foto['sucop_ok']
    nombre = guardar_foto(foto)
    base = cargar_base()
    C.escribir(VISTA, armar_vista(foto, nombre, base, anterior, C.leer(VISTA)))
    n = sum(a['n_normas'] for a in foto['agendas'] if a['leida'])
    print(f"\n  agendas · {nombre}{' · LÍNEA BASE' if foto['linea_base'] else ''} · {len(foto['agendas'])} entidades · {n} normas")
    return foto['sucop_ok']


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('fetch').add_argument('--ensayo', action='store_true', help='lee y reporta sin guardar foto')
    c = sub.add_parser('comparar')
    c.add_argument('--desde', help='nombre de la foto; por defecto, la línea base')
    c.add_argument('--hasta', help='nombre de la foto; por defecto, la última')
    sub.add_parser('reporte')
    a = ap.parse_args()
    if a.cmd == 'fetch':
        sys.exit(0 if fetch(a.ensayo) else 1)
    ultima = json.loads(fotos()[-1].read_bytes())
    if a.cmd == 'reporte':
        print(reporte(ultima))
        return
    x = json.loads((FOTOS / a.desde).read_bytes()) if a.desde else cargar_base()
    y = json.loads((FOTOS / a.hasta).read_bytes()) if a.hasta else ultima
    r = comparar(x, y)
    print(json.dumps(r, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
