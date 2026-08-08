#!/usr/bin/env python3
"""
Caudal · pilar Regulatorio — UIAF · obligaciones de reporte ALA/CFT (vía 2).

⚠️ LA UIAF TAMPOCO SANCIONA. Es una unidad de inteligencia financiera adscrita
a MinHacienda: recibe reportes, no impone multas (quien sanciona por incumplir
es el supervisor de cada sector). Sus actos son NORMATIVOS → `tipo_acto` ∈
{resolucion, circular, otro}, nunca 'sancion', y `sancionado` va NULL (ver la
nota `interaccion_sancionado_guion` de _pendiente-uiaf.json).

QUÉ TRAE, y por qué esta fuente y no otra:

  A) SECTORES REPORTANTES  — /sector/{slug}, 20 sectores obligados.
     ES EL NÚCLEO. Por cada sector (activos virtuales · notariado · juegos de
     suerte y azar · oro · economía solidaria · vigilancia privada · SFC …) la
     UIAF publica la Resolución que le impone la obligación de reportar, los
     ANEXOS TÉCNICOS de cada reporte (Anexo 1 - ROS · Anexo 2 - Reporte de
     Transacciones en Efectivo · clientes exonerados · operaciones cambiarias)
     y el CALENDARIO DE REPORTE del año en curso. Es literalmente la frontera
     de cumplimiento: quién reporta, qué reporta, con qué formato y cuándo.
     Está VIVO (el listado se declara "cifras actualizadas al 5 de agosto de
     2026") y trae la Resolución 314 de 2021 de PSAV, que es la obligación que
     rige a los exchanges.

  B) COMPILACIÓN ALA/CFT  — /normativa-2, 83 normas del sistema, 1991→2022.
     ⚠️ OJO AL CONSOLIDAR: es una compilación del sistema ENTERO, no actos de
     la UIAF. 26 son Leyes y 21 Decretos —que Caudal YA tiene en los pilares
     Congreso y Ejecutivo— y varias Circulares/Resoluciones son de otras
     entidades (DIAN, Supersociedades, Supersolidaria, MinTIC, SIC,
     Supervigilancia), algunas de las cuales tienen o tendrán su propia fuente
     en este pilar. Por eso este harvester EXCLUYE por defecto ley · decreto ·
     constitución · sentencia · CONPES (`--con-leyes` las incluye) y marca en
     `emisor` la entidad que expide cada acto para que el consolidador pueda
     filtrar. La lista de solapamientos MEDIDOS va en _pendiente-uiaf.json.

  C) TIPOLOGÍAS  — /documentos-de-interes/otros-documentos-de-interes.
     ⚠️ LÍMITE HONESTO: el buscador de tipologías propio de la UIAF está
     detrás de login (hub.uiaf.gov.co/login) y NO es cosechable sin
     credenciales. Lo público son las recopilaciones de GAFI/GAFILAT que la
     UIAF republica (tipologías regionales 2010-2016, red flags de activos
     virtuales, informes de amenazas). Se traen esas, etiquetadas
     `tipo_acto='otro'` y rótulo "Documento de tipologías", sin fingir que son
     el catálogo propio.

Descartadas y por qué:
  · vía 1 (Socrata): la UIAF publica 2 datasets en datos.gov.co y los dos son
    landings informativas SIN columnas ("Conozca qué es la UIAF" y "Conjuntos
    de Datos Obligatorios"). Cero normatividad.
  · JSON:API: el sitio es Drupal 10 y /jsonapi está ABIERTO, pero no sirve
    para esto — no hay content type de norma; todo es node--page/node--article
    con body libre, y los nodos por norma (p.ej. /resolucion-314-de-2021) son
    STUBS VACÍOS: solo título y la fecha de migración del CMS (jun-2024), no
    la fecha de la norma. Usarlos daría 2024 como fecha de una resolución de
    2021. El contenido real vive en las páginas de sector y en la compilación.
  · /2.1.3-Normativa (el ítem de Ley 1712): trae 4 documentos administrativos
    (decretos de estructura y planta). No es el registro sustantivo.

Fechas: ni las páginas de sector ni la compilación publican la fecha de
expedición, así que se deriva en cascada y CADA REGISTRO DECLARA de dónde
salió la suya en `fecha_precision` (ver la función fecha_de): 'dia' del nombre
completo · 'anio' del nombre ("Resolución 314 de 2021" → 2021-01-01) · 'carga'
de la carpeta de subida de Drupal en la ruta del archivo, que NO es la fecha
de la norma y solo sirve para ordenar los anexos técnicos · '' cuando no hay
nada. Nunca se inventa un día: con solo el año, es 01-01 declarado como tal.
Al usar estos datos, filtrar por `fecha_precision` antes de hacer series
temporales.

Comandos:
  python3 tools/caudal/supers/harvest_uiaf.py test    # valida los 3 bloques
  python3 tools/caudal/supers/harvest_uiaf.py fetch   # ~24 peticiones, resumible
  python3 tools/caudal/supers/harvest_uiaf.py build   # caché -> raw/uiaf-reportantes.json
  python3 tools/caudal/supers/harvest_uiaf.py stats
"""
import argparse
import hashlib
import html
import json
import re
import subprocess
import sys
import time
from collections import Counter, OrderedDict
from pathlib import Path
from urllib.parse import quote, unquote

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SUP = REPO / 'Bases de datos' / 'leyes-senado' / 'supers'
RAW = SUP / 'raw'
CACHE = RAW / 'uiaf-cache'
OUT_JSON = RAW / 'uiaf-reportantes.json'

BASE = 'https://www.uiaf.gov.co'
IDX_SECTORES = BASE + '/index.php/reportantes/entidades'
COMPILACION = BASE + '/index.php/normativa-2'
TIPOLOGIAS = BASE + '/index.php/documentos-de-interes/otros-documentos-de-interes'

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0 Safari/537.36')

TIPOS_ACTO = ('sancion', 'apertura_investigacion', 'archivo',
              'contribucion_especial', 'resolucion', 'circular', 'otro')

# Tipos de norma que NO entran: pertenecen a los pilares Congreso y Ejecutivo
# de Caudal, que ya los tienen con mejor metadato.
OTROS_PILARES = re.compile(
    r'^\s*(ley(es)?|decreto|constituci[oó]n|sentencia|conpes|acto\s+legislativo)\b', re.I)

MESES = {'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
         'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
         'septiembre': '09', 'setiembre': '09', 'octubre': '10',
         'noviembre': '11', 'diciembre': '12'}

# Emisor inferido del texto del acto. Solo etiquetas medidas sobre la fuente;
# lo que no casa queda en '' y NO se adivina.
EMISORES = [
    (r'\bUIAF\b|Unidad de Informaci[oó]n y An[aá]lisis Financiero', 'UIAF'),
    (r'\bDIAN\b', 'DIAN'),
    (r'Supersolidaria|Superintendencia de Econom[ií]a Solidaria', 'Superintendencia de Economía Solidaria'),
    (r'Supersociedades|Superintendencia de Sociedades', 'Superintendencia de Sociedades'),
    (r'Superfinanciera|Superintendencia Financiera', 'Superintendencia Financiera de Colombia'),
    (r'Supervigilancia|Vigilancia y Seguridad Privada', 'Superintendencia de Vigilancia y Seguridad Privada'),
    (r'Supersalud|Superintendencia Nacional de Salud', 'Superintendencia Nacional de Salud'),
    (r'Notariado y Registro', 'Superintendencia de Notariado y Registro'),
    (r'Superintendencia de Transporte', 'Superintendencia de Transporte'),
    (r'\bMinTIC\b|Tecnolog[ií]as de la Informaci[oó]n', 'MinTIC'),
    (r'Coljuegos', 'Coljuegos'),
    (r'CNJSA|Juegos de Suerte y Azar', 'Consejo Nacional de Juegos de Suerte y Azar'),
    (r'Ministerio de Cultura|Mincultura', 'Ministerio de Cultura'),
    (r'Ministerio del Deporte', 'Ministerio del Deporte'),
    (r'Consejo Nacional Electoral|\bCNE\b', 'Consejo Nacional Electoral'),
    (r'\bSIC\b|Industria y Comercio', 'Superintendencia de Industria y Comercio'),
    (r'Coldeportes', 'Ministerio del Deporte (Coldeportes)'),
    (r'\bSNR\b', 'Superintendencia de Notariado y Registro'),
    (r'Supertransporte', 'Superintendencia de Transporte'),
]


# --------------------------------------------------------------------- http
def curl(url, timeout=60, retries=3):
    cmd = ['/usr/bin/curl', '-sk', '-m', str(timeout), '-A', UA, '-L', url]
    last = None
    for i in range(retries):
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=timeout + 15)
            if r.returncode == 0 and r.stdout:
                return r.stdout.decode('utf-8', errors='replace').lstrip('﻿')
            last = RuntimeError(f'curl rc={r.returncode}')
        except subprocess.TimeoutExpired:
            last = RuntimeError('timeout')
        time.sleep(1.5 * (i + 1))
    raise last


def _txt(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s or ''))).strip()


def _abs(u):
    """Las páginas de sector usan rutas '../../../../sites/default/files/...'.

    Se percent-encodea al salir: los nombres de archivo de la UIAF traen tildes
    y espacios literales ('Resolución 314 de 2021 AV.pdf') y así viajan
    íntegros por correo y por el frontend. `safe` deja pasar lo ya codificado
    para no romper los enlaces que ya venían con %20.
    """
    u = html.unescape((u or '').strip())
    if not u:
        return ''
    if not u.startswith(('http://', 'https://')):
        u = re.sub(r'^(\.\./)+', '/', u)
        if not u.startswith('/'):
            u = '/' + u
        u = BASE + u
    return quote(u, safe=":/?#[]@!$&'()*+,;=%~")


def _cache(name, url, refetch=False):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f'{name}.html'
    if p.exists() and not refetch and p.stat().st_size > 2000:
        return p.read_text(encoding='utf-8', errors='replace')
    doc = curl(url)
    p.write_text(doc, encoding='utf-8')
    time.sleep(0.6)
    return doc


# ------------------------------------------------------------------ helpers
def clasificar(nombre):
    """tipo_acto + rótulo a partir del nombre del acto. Whitelist dura."""
    n = (nombre or '').lower()
    if re.search(r'\bcalendario\b', n):
        return 'otro', 'Calendario de reporte'
    if re.search(r'genera(r)?\s+plano|utilidad', n):
        # los .xlsm que la UIAF entrega para armar el archivo plano del reporte
        return 'otro', 'Utilidad de generación de reporte'
    if re.search(r'\banexo\b|formato|instructivo|documento t[eé]cnico', n):
        return 'otro', 'Anexo técnico de reporte'
    if re.search(r'tipolog', n):
        return 'otro', 'Documento de tipologías'
    if re.search(r'\bgu[ií]a\b|manual|cartilla|preguntas', n):
        return 'otro', 'Guía / manual'
    if re.search(r'instrucci[oó]n administrativa', n):
        return 'circular', 'Instrucción administrativa'
    if re.search(r'norma t[eé]cnica', n):
        return 'otro', 'Norma técnica'
    if re.search(r'circular', n):
        return 'circular', 'Circular'
    if re.search(r'resoluci', n):
        return 'resolucion', 'Resolución'
    if re.search(r'acuerdo', n):
        return 'resolucion', 'Acuerdo'
    if OTROS_PILARES.match(nombre or ''):
        return 'otro', (nombre or '').split()[0].title()
    return 'otro', 'Documento'


def fecha_de(nombre, texto='', url=''):
    """(fecha ISO, precisión). Cuatro niveles, del más fuerte al más débil:

      'dia'   el nombre trae día/mes/año  ("Resolución No. 010 de 2025 de 13 de enero de 2025")
      'anio'  el nombre trae solo el año  ("Resolución 314 de 2021")  -> se fija 01-01
      'carga' NADA en el nombre, pero la ruta del archivo lleva la carpeta de
              subida de Drupal (/sites/default/files/2024-10/…) -> 2024-10-01.
              ⚠️ ES LA FECHA EN QUE SE SUBIÓ EL ARCHIVO, NO LA DE LA NORMA. Se
              usa para poder ordenar los anexos técnicos (que no llevan fecha
              en ninguna parte), y va etiquetada así justamente para que nadie
              la lea como fecha de expedición.
      ''      ni eso (anexos servidos desde /inline-images/, sin carpeta datada)

    Nunca se inventa el día: con solo el año, es 01-01 DECLARADO como 'anio'.
    """
    nombre = nombre or ''

    def dma(s):
        m = re.search(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})', s, re.I)
        if m and MESES.get(m.group(2).lower()):
            return f'{m.group(3)}-{MESES[m.group(2).lower()]}-{m.group(1).zfill(2)}'
        return None

    # ⚠️ EL NOMBRE MANDA SOBRE LA DESCRIPCIÓN. Mirar los dos a la vez fechaba
    # mal: la descripción de la "Resolución 212 de 2009" cita 2007 y la daba
    # como de 2007. La descripción solo entra cuando el nombre no trae año.
    f = dma(nombre)
    if f:
        return f, 'dia'
    m = re.search(r'\bde\s+(19|20)(\d{2})\b', nombre)
    if m:
        return f'{m.group(1)}{m.group(2)}-01-01', 'anio'
    m = re.search(r'\b(19|20)(\d{2})\b', nombre)
    if m:
        return f'{m.group(1)}{m.group(2)}-01-01', 'anio'
    # radicado largo tipo 'Circular 20180000000045' / 'Resolución 20195100044514':
    # los 4 primeros dígitos son el año. Sin esto caían en la fecha de la
    # descripción, que es de otra norma.
    m = re.search(r'\b((?:19|20)\d{2})\d{6,}\b', nombre)
    if m:
        return f'{m.group(1)}-01-01', 'anio'
    f = dma(texto or '')
    if f:
        return f, 'dia'
    m = re.search(r'/files/(20\d{2})-(0[1-9]|1[0-2])/', url or '')
    if m:
        return f'{m.group(1)}-{m.group(2)}-01', 'carga'
    return '', ''


def emisor_de(*textos):
    """El NOMBRE DEL ARCHIVO es la mejor señal del emisor (medido): el título
    dice "Circular 20 de 2020" pero el PDF se llama
    '2020_Circular_Exterma_20_SUPERSOLIDARIA.pdf'. Por eso quien llama a esta
    función le pasa también la URL. Lo que no casa queda en '' — no se adivina.
    """
    # ⚠️ De la URL SOLO sirve el nombre del archivo: el host es siempre
    # uiaf.gov.co y la primera regla (\bUIAF\b) marcaría los 240 actos como
    # UIAF, borrando a los demás emisores. Medido: pasar la URL entera dejó
    # 239 UIAF + 1 MinTIC.
    archivo, resto = [], []
    for t in textos:
        if not t:
            continue
        if '://' in t or t.startswith('/'):
            archivo.append(t.rsplit('/', 1)[-1])
        else:
            resto.append(t)

    def buscar(s):
        s = unquote(s).replace('_', ' ')
        for pat, nom in EMISORES:
            if re.search(pat, s, re.I):
                return nom
        return ''

    # El nombre del archivo GANA sobre el título y la descripción: casi todos
    # los textos de la compilación mencionan a la UIAF (es a quien se reporta),
    # así que la regla \bUIAF\b se los llevaba todos. El archivo
    # 'resolucion 2679 de 2016 mintic.pdf' dice quién EXPIDE.
    return buscar(' '.join(archivo)) or buscar(' '.join(resto))


def _sid(*parts):
    return hashlib.md5('|'.join(parts).encode('utf-8')).hexdigest()[:10]


# ------------------------------------------------------- parseo: sectores
def parse_indice_sectores(doc):
    out = OrderedDict()
    for u, t in re.findall(r'<a[^>]+href="(/sector/[^"]+)"[^>]*>(.*?)</a>', doc, re.S):
        slug = u.rsplit('/', 1)[-1]
        nom = _txt(t) or slug.replace('-', ' ').title()
        out.setdefault(slug, nom)
    return out


def _paneles(doc):
    """(título de sección, cuerpo) de cada acordeón Gavias de la página."""
    out = []
    for m in re.finditer(
            r'<h4 class="panel-title">\s*<a[^>]*>(.*?)</a>\s*</h4>(.*?)'
            r'(?=<h4 class="panel-title">|</div>\s*</div>\s*</div>\s*</div>\s*</div>\s*$)',
            doc, re.S):
        out.append((_txt(m.group(1)), m.group(2)))
    return out


def parse_sector(doc, slug, nombre):
    """Documentos de un sector, con la sección del acordeón como contexto."""
    recs = []
    vistos = set()
    for seccion, cuerpo in _paneles(doc):
        # cada archivo va en <div class="wp-block-file"><a href=..>nombre</a></div>
        # y su descripción es el <p> inmediatamente posterior
        for m in re.finditer(
                r'<div class="wp-block-file">\s*<a\s+href="([^"]+)"[^>]*>(.*?)</a>\s*</div>'
                r'(?:\s*<p>(.*?)</p>)?', cuerpo, re.S):
            url, nom, desc = _abs(m.group(1)), _txt(m.group(2)), _txt(m.group(3) or '')
            if not url or url in vistos:
                continue
            vistos.add(url)
            # el nombre suele ser el propio archivo: se limpia para leerse
            bonito = re.sub(r'\.(pdf|docx?|xlsx?|zip)$', '', nom, flags=re.I)
            bonito = re.sub(r'[_]+', ' ', bonito).strip()
            recs.append({'seccion': seccion, 'nombre': bonito or nom,
                         'descripcion': desc, 'url': url,
                         'sector_slug': slug, 'sector_nombre': nombre})
        # enlaces sueltos a PDF fuera de wp-block-file (calendarios, anexos)
        for u, t in re.findall(r'<a\s+href="([^"]+\.(?:pdf|docx?|xlsx?))"[^>]*>(.*?)</a>',
                               cuerpo, re.S | re.I):
            url, nom = _abs(u), _txt(t)
            if not nom or url in vistos:
                continue
            vistos.add(url)
            recs.append({'seccion': seccion, 'nombre': nom, 'descripcion': '',
                         'url': url, 'sector_slug': slug, 'sector_nombre': nombre})
    return recs


# ---------------------------------------------------- parseo: compilación
def parse_compilacion(doc):
    """h2 = nombre de la norma; el bloque siguiente trae descripción y PDF.

    ⚠️ La página no tiene <main>, así que los h2 del chasis de Drupal ("Main
    navigation", "Breadcrumb", "Bottom menu", "Contacto") caen en la misma
    lista que las normas. Se descartan por whitelist de forma: una norma
    empieza por su tipo (Ley/Decreto/Resolución/Circular/…). Filtrar solo por
    nombre conocido dejaría entrar cualquier h2 nuevo que agreguen al tema.
    """
    ES_NORMA = re.compile(
        r'^\s*(ley(es)?|decreto|resoluci[oó]n|circular|acuerdo|conpes|sentencia|'
        r'constituci[oó]n|norma\s+t[eé]cnica|instrucci[oó]n|acto\s+legislativo)\b', re.I)
    recs = []
    hs = list(re.finditer(r'<h2[^>]*>(.*?)</h2>', doc, re.S))
    for i, m in enumerate(hs):
        nom = _txt(m.group(1))
        if not nom or not ES_NORMA.match(nom):
            continue
        cuerpo = doc[m.end(): hs[i + 1].start() if i + 1 < len(hs) else m.end() + 2500]
        pdf = re.search(r'href="([^"]+\.pdf[^"]*)"', cuerpo, re.I)
        ext = re.search(r'href="(https?://[^"]*(?:funcionpublica|normograma|suin)[^"]*)"',
                        cuerpo, re.I)
        desc = ''
        for p in re.findall(r'<p[^>]*>(.*?)</p>', cuerpo, re.S):
            t = _txt(p)
            if len(t) > 25 and 'descargar' not in t.lower():
                desc = t
                break
        recs.append({'nombre': nom, 'descripcion': desc,
                     'url': _abs(pdf.group(1)) if pdf else (ext.group(1) if ext else '')})
    return recs


def parse_tipologias(doc):
    recs = []
    for u, t in re.findall(r'<a\s+href="([^"]+\.pdf[^"]*)"[^>]*>(.*?)</a>', doc, re.S | re.I):
        nom = _txt(t)
        if not nom or nom.lower() in ('descargar', 'ver'):
            continue
        recs.append({'nombre': nom, 'url': _abs(u)})
    return recs


# -------------------------------------------------------------------- fetch
def fetch(refetch=False):
    doc = _cache('indice-sectores', IDX_SECTORES, refetch=True)   # siempre fresco
    secs = parse_indice_sectores(doc)
    print(f'  sectores reportantes: {len(secs)}')
    for slug, nom in secs.items():
        try:
            _cache(f'sector-{slug}', f'{BASE}/sector/{slug}', refetch=refetch)
            print(f'    ok  {slug:24} {nom[:48]}')
        except Exception as e:
            print(f'    !   {slug}: {e}', file=sys.stderr)
    _cache('compilacion', COMPILACION, refetch=True)
    _cache('tipologias', TIPOLOGIAS, refetch=True)
    print('  compilación ALA/CFT + documentos de tipologías ok')


# -------------------------------------------------------------------- build
def build(con_leyes=False):
    recs = OrderedDict()
    idx = CACHE / 'indice-sectores.html'
    secs = parse_indice_sectores(idx.read_text(encoding='utf-8', errors='replace')) if idx.exists() else {}

    # --- A) sectores reportantes (el núcleo)
    for slug, nom in secs.items():
        p = CACHE / f'sector-{slug}.html'
        if not p.exists():
            continue
        for r in parse_sector(p.read_text(encoding='utf-8', errors='replace'), slug, nom):
            ta, rot = clasificar(r['nombre'])
            f, prec = fecha_de(r['nombre'], r['descripcion'], r['url'])
            k = r['url']
            if k in recs:
                # el mismo anexo puede colgar de dos sectores: no duplicar
                recs[k]['sectores'] = sorted(set(recs[k]['sectores'] + [nom]))
                continue
            recs[k] = {
                '_id': f'uiaf-{slug}-{_sid(r["url"])}',
                'bloque': 'sector-reportante',
                'tipo_acto': ta,
                'rotulo': rot,
                'resolucion': r['nombre'],
                'motivo': r['descripcion'] or f'{r["seccion"]} · {nom}',
                'seccion': r['seccion'],
                'sectores': [nom],
                'emisor': emisor_de(r['nombre'], r['descripcion'], r['url']) or 'UIAF',
                'fecha': f,
                'fecha_precision': prec,
                'url': r['url'],
            }

    # --- B) compilación ALA/CFT
    p = CACHE / 'compilacion.html'
    if p.exists():
        omitidas = Counter()
        for r in parse_compilacion(p.read_text(encoding='utf-8', errors='replace')):
            if not con_leyes and OTROS_PILARES.match(r['nombre']):
                omitidas[r['nombre'].split()[0].title()] += 1
                continue
            ta, rot = clasificar(r['nombre'])
            f, prec = fecha_de(r['nombre'], r['descripcion'], r['url'])
            k = 'comp::' + r['nombre']
            if k in recs:
                continue
            recs[k] = {
                '_id': f'uiaf-comp-{_sid(r["nombre"])}',
                'bloque': 'compilacion-alacft',
                'tipo_acto': ta,
                'rotulo': rot,
                'resolucion': r['nombre'],
                'motivo': r['descripcion'] or r['nombre'],
                'seccion': 'Normatividad del sistema ALA/CFT',
                'sectores': [],
                'emisor': emisor_de(r['nombre'], r['descripcion'], r['url']),
                'fecha': f,
                'fecha_precision': prec,
                'url': r['url'],
            }
        if omitidas:
            print('  compilación: omitidas por pertenecer a otros pilares de Caudal '
                  f'(Congreso/Ejecutivo): {dict(omitidas)}  [--con-leyes las incluye]')

    # --- C) tipologías
    p = CACHE / 'tipologias.html'
    if p.exists():
        for r in parse_tipologias(p.read_text(encoding='utf-8', errors='replace')):
            k = r['url']
            if k in recs:
                continue
            f, prec = fecha_de(r['nombre'], '', r['url'])
            recs[k] = {
                '_id': f'uiaf-tip-{_sid(r["url"])}',
                'bloque': 'tipologias',
                'tipo_acto': 'otro',
                'rotulo': 'Documento de tipologías',
                'resolucion': r['nombre'],
                'motivo': r['nombre'],
                'seccion': 'Documentos de interés · tipologías',
                'sectores': [],
                'emisor': emisor_de(r['nombre'], '', r['url']),
                'fecha': f,
                'fecha_precision': prec,
                'url': r['url'],
            }

    rows = list(recs.values())
    # `nota_fecha` va mapeada al campo `estado`, que el frontend SÍ pinta: la
    # advertencia sobre de dónde salió la fecha tiene que viajar con el dato,
    # no quedarse en este archivo.
    NOTA = {
        'dia': 'fecha de expedición, leída del nombre del acto',
        'anio': 'solo se conoce el año; el día 01-01 es de relleno',
        'carga': 'fecha de carga del archivo — NO es la fecha de la norma',
        '': 'sin fecha en la fuente',
    }
    for r in rows:
        r['sectores_txt'] = ' · '.join(r['sectores'])
        r['nota_fecha'] = NOTA[r['fecha_precision']]
    rows.sort(key=lambda r: (r['fecha'] or ''), reverse=True)
    RAW.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    print(f'  build: {len(rows)} actos -> {OUT_JSON.relative_to(REPO)}')
    return rows


# -------------------------------------------------------------------- stats
def stats():
    if not OUT_JSON.exists():
        print('  (no hay build todavía)'); return
    rows = json.loads(OUT_JSON.read_text(encoding='utf-8'))
    print(f'  actos: {len(rows)}')
    print('  tipo_acto:', dict(Counter(r['tipo_acto'] for r in rows)))
    print('  bloque   :', dict(Counter(r['bloque'] for r in rows)))
    print('  rótulos:')
    for k, v in Counter(r['rotulo'] for r in rows).most_common():
        print(f'      {v:4d}  {k}')
    print('  emisor:')
    for k, v in Counter(r['emisor'] or '(sin identificar)' for r in rows).most_common():
        print(f'      {v:4d}  {k}')
    print('  precisión de fecha:', dict(Counter(r['fecha_precision'] or '(sin fecha)' for r in rows)))
    reales = [r for r in rows if r['fecha_precision'] in ('dia', 'anio')]
    carga = [r for r in rows if r['fecha_precision'] == 'carga']
    fs = sorted(r['fecha'] for r in reales if r['fecha'])
    if fs:
        print(f'  rango (fecha real de la norma): {fs[0]} .. {fs[-1]}')
    print(f'  sin URL  : {sum(1 for r in rows if not r["url"])}')
    print('  por año — SOLO fecha real de la norma (precisión dia/anio):')
    for a, v in sorted(Counter(r['fecha'][:4] for r in reales if r['fecha']).items()):
        print(f'      {a}  {v:4d}  {"#" * min(60, v)}')
    if carga:
        # ⚠️ no mezclar con lo de arriba: el pico de 2024 es la migración del
        # CMS de la UIAF, no un año de actividad normativa.
        print(f'  aparte · {len(carga)} anexos sin fecha propia, ordenados por fecha '
              f'de CARGA del archivo (NO es la fecha de la norma):')
        for a, v in sorted(Counter(r['fecha'][:4] for r in carga if r['fecha']).items()):
            print(f'      {a}  {v:4d}')
    print('  sectores con más documentos:')
    c = Counter()
    for r in rows:
        for s in r['sectores']:
            c[s] += 1
    for k, v in c.most_common(12):
        print(f'      {v:4d}  {k}')


# --------------------------------------------------------------------- test
def test():
    print('· índice de sectores reportantes')
    doc = curl(IDX_SECTORES)
    secs = parse_indice_sectores(doc)
    assert len(secs) >= 15, f'solo {len(secs)} sectores'
    print(f'  ok · {len(secs)} sectores: {", ".join(list(secs)[:8])} …')

    print('· sector activos virtuales (prueba de fuego: Resolución 314 de 2021 PSAV)')
    d = curl(f'{BASE}/sector/activos-virtuales')
    rs = parse_sector(d, 'activos-virtuales', 'Activos virtuales')
    assert rs, 'no se parseó ningún documento'
    r314 = [r for r in rs if '314' in r['nombre']]
    assert r314, 'no aparece la Resolución 314 de 2021'
    print(f'  ok · {len(rs)} documentos')
    for r in rs[:6]:
        ta, rot = clasificar(r['nombre'])
        f, prec = fecha_de(r['nombre'], r['descripcion'], r['url'])
        print(f'    [{ta}/{rot}] {f or "----":10} ({prec or "-"}) {r["seccion"][:26]:28} {r["nombre"][:44]}')
    print(f'    314 -> {r314[0]["descripcion"][:110]}')
    ros = [r for r in rs if 'ROS' in r['nombre'].upper()]
    print(f'  anexos ROS detectados: {len(ros)}')

    print('· sector SFC (debe traer el Anexo 2 de transacciones en efectivo)')
    d = curl(f'{BASE}/sector/sfc')
    rs = parse_sector(d, 'sfc', 'Superintendencia Financiera de Colombia')
    ef = [r for r in rs if 'efectivo' in (r['nombre'] + r['descripcion']).lower()]
    print(f'  ok · {len(rs)} documentos · con "efectivo": {len(ef)}')
    for r in ef[:3]:
        print(f'    - {r["nombre"][:70]}')

    print('· compilación ALA/CFT')
    rs = parse_compilacion(curl(COMPILACION))
    print(f'  ok · {len(rs)} normas · con URL: {sum(1 for r in rs if r["url"])}')
    print(f'  de otros pilares (ley/decreto/…): '
          f'{sum(1 for r in rs if OTROS_PILARES.match(r["nombre"]))}')

    print('· tipologías')
    rs = parse_tipologias(curl(TIPOLOGIAS))
    print(f'  ok · {len(rs)} documentos')
    for r in rs[:4]:
        print(f'    - {r["nombre"][:78]}')
    print('TEST OK')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['test', 'fetch', 'build', 'stats'])
    ap.add_argument('--refetch', action='store_true', help='ignora el caché de sectores')
    ap.add_argument('--con-leyes', action='store_true',
                    help='incluye leyes/decretos de la compilación (por defecto se '
                         'omiten: viven en los pilares Congreso y Ejecutivo)')
    a = ap.parse_args()
    if a.cmd == 'test':
        test()
    elif a.cmd == 'fetch':
        fetch(refetch=a.refetch)
    elif a.cmd == 'build':
        build(con_leyes=a.con_leyes); stats()
    else:
        stats()


if __name__ == '__main__':
    main()
