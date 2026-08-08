#!/usr/bin/env python3
"""
Caudal · pilar Regulatorio — NORMATIVA y PROYECTOS DE NORMATIVA de la
SUPERINTENDENCIA DE SOCIEDADES (vía 2: dos portlets server-rendered de Liferay).

POR QUÉ SE REABRE ESTA FUENTE. En jul-2026 se auditó el portal buscando
SANCIONES y se cerró como DESCARTADA. La conclusión era correcta y sigue en pie:
Supersociedades **no publica un registro sancionatorio**; sus "avisos" son
notificaciones de respuesta a derechos de petición (art. 69 CPACA). Lo que
estaba mal era la pregunta. Supersociedades es el **supervisor de LA/FT del
sector real** —incluidos los exchanges de criptoactivos, que NO son vigilados de
la Superfinanciera, y por eso existe el proyecto de ley de PSAV—, así que lo que
le cambia la vida a un vigilado no son sus multas: es su **Circular Básica
Jurídica**, sus **circulares externas** y, sobre todo, sus **proyectos de
circular en consulta pública**, que son la alerta antes de que la obligación
exista.

EL CASO QUE LO MOTIVÓ. La matriz normativa de un cliente real (Binance) trae en
su fila 1.6 un "Proyecto de Circular Externa sobre SAGR (Sistema de Autocontrol
y Gestión del Riesgo)" de Supersociedades, en consulta hasta el 08-abr-2026 y
clasificado "adversarial / costosa". No estaba en Caudal ni en SUCOP.

  ⚠️ EL RÓTULO DEL CLIENTE ES APROXIMADO — VERIFICADO CONTRA LA FUENTE. Lo que
  estuvo en consulta pública **del 30-mar-2026 al 08-abr-2026** no se llama
  "Proyecto de Circular Externa sobre SAGR": es el **"Proyecto de nueva Circular
  Básica Jurídica de la Superintendencia de Sociedades"**, que deroga la CBJ
  100-000008 de 2022. El SAGR**ILAFT** vive dentro de esa CBJ, en el **Capítulo
  X** ("Autocontrol y gestión del riesgo integral LA/FT/FPADM y reporte de
  operaciones sospechosas a la UIAF"), y el PTEE en el **Capítulo XIII**. O sea:
  la fecha del cliente es exacta, el nombre no. Y hay un dato que su matriz
  todavía no puede tener: ese proyecto **ya se expidió** como **Circular Externa
  100-000020 del 2 de julio de 2026** — "por medio de la cual se modifica
  integralmente la Circular Básica Jurídica". Dejó de ser borrador.

LAS DOS COLAS. Son dos portlets distintos, con paginación distinta, y hay que
cosechar las dos:

  A · PROYECTOS   /web/nuestra-entidad/proyectos-de-normatividad
      AssetPublisher de Liferay (INSTANCE_gllg), server-rendered. El listado da
      título + descripción + plazo; el NODO de cada proyecto agrega tipo de
      normativa, correos para observaciones, dependencia líder, responsable
      técnico y su cargo, el PDF del borrador y —cuando existe— la **matriz de
      comentarios** recibidos. Es la cola de más valor: es la única que avisa
      ANTES.

  B · NORMATIVA   /web/nuestra-entidad/normativa
      Buscador interno propio (portlet `gov.co.supersociedades.buscador.interno`).
      Pese al `onclick="findByCategory(...)"` NO es AJAX: la función solo hace
      `window.location = ?id=<catId>`, y la página vuelve renderizada del
      servidor con los PDF en `href` directo. 11 categorías, 2.632 actos.

VÍAS DESCARTADAS (medidas, no supuestas):

  Vía 1 · Socrata. `catalog/v1?q=Supersociedades` da 7 datasets y todos son NIIF
    (estados financieros de vigiladas), ninguno normativo. El único índice que
    la cubre es `fiev-nid6` (SUIN-Juriscol, de MinJusticia): **439 normas** de la
    entidad (324 bajo "SUPERINTENDENCIA DE SOCIEDADES" + 115 bajo
    "Superintendencia de Sociedades" — el mismo emisor escrito de dos formas, y
    agrupar por ese campo sin normalizar lo parte en dos). Sirve como control
    cruzado de completitud y nada más: trae tipo/número/año/vigencia **sin
    título, sin fecha, sin descripción y sin PDF**. Es un índice, no la norma.
    (Idéntico al hallazgo del harvester de circulares de la SIC.)

  Vía 3 · PDF+LLM. Innecesaria para el ACTO: el "por medio de la cual…" ya viene
    en texto en el listado. El PDF se referencia en `url` para quien quiera el
    articulado. Extraerlo es trabajo del frente de análisis del articulado, no
    de este harvester.

TRAMPAS MEDIDAS (no las quites sin volver a medir):

  ① NO TODA LA "NORMATIVA" DEL PORTAL ES DE SUPERSOCIEDADES — Y LA CATEGORÍA NO
     BASTA PARA SABERLO. De los 2.632 actos del buscador, **1.931 (73%) NO los
     expide la entidad**: Decretos (303), Leyes (91), Decreto Único Reglamentario
     Sectorial (106) y Constitución (1) son normas AJENAS que le aplican al
     sector, y Actas de Conciliación (1.407) no son normativa sino actos
     particulares. Publicarlas bajo `fuente=supersociedades` mentiría sobre quién
     las expidió **y las contaría dos veces**: los decretos ya están en el pilar
     Ejecutivo (10.193 desde Presidencia) y las leyes en el pilar Congreso.

     ⚠️ Y hay dos categorías que ENGAÑAN si uno se fía del nombre — las dos me
     las corrigió la medición, no la intuición:
       · **"Otra Normativa" (4)** suena a cajón de sastre propio y son las
         CUATRO **Directivas Presidenciales** (03/2026, 02/2025, 04/2025,
         01/2024). Ajenas enteras.
       · **"Escala Salarial" (13)** son 13 **Decretos** de Función Pública.
       · **"Estructura" (10)** es **MIXTA**: conviven Resoluciones propias
         (100-000512 de 2024, 100-000163 de 2021…) con Decretos ajenos
         (1736 de 2020).
     Por eso el emisor **se decide POR FILA, leyendo el encabezado del título**
     (`_emisor`), no por la categoría: una categoría mixta clasificada en bloque
     o borra actos propios o publica decretos ajenos como si fueran de la
     Superintendencia. Lo ajeno se cuenta y se reporta; lo que no encaja en
     ninguna de las dos listas sale por pantalla como `ambiguo` para que lo mire
     un humano — nunca se descarta en silencio.
     Es la trampa ① del harvester de la SIC con otra cara.

  ② EL BUSCADOR POR PALABRA NO SIRVE, Y NO ES SOLO QUE MIRE EL TÍTULO. Medido:
     `sagrilaft`, `cripto`, `virtuales` y `autocontrol` dan **0** — se podía
     explicar porque los títulos son pura numeración ("Circular Externa
     100-000020 de 2 de julio de 2026"). Pero también dan **0** `circular`,
     `Circular Externa`, `Resoluci` y hasta el número exacto de un acto que sí
     existe (`100-000020`), mientras `2026` devuelve 64. Sea lo que sea que
     indexa, no es el título como substring ni la descripción. Es inservible
     para buscar por tema. Por eso se cosecha POR CATEGORÍA, nunca por keyword:
     una cosecha por palabra clave se vería limpia y traería la nada.

  ③ `end` NO AMPLÍA LA PÁGINA. La paginación es `?id=<cat>&start=N&end=N+20`,
     pero pedir `end=200` devuelve 20 igual: el tamaño de página está fijo del
     lado del servidor. Hay que paginar de a 20. (Mismo modo de falla que el
     `items_per_page` de la SIC y el `delta` del AssetPublisher de proyectos,
     que también se ignora.)

  ④ LA FECHA AUTORITATIVA ESTÁ EN EL TÍTULO, NO EN EL ARCHIVO. El `?t=…` de la
     URL del PDF es epoch-ms de **cuándo lo subieron**: los 199 archivos de
     circulares externas comparten `t=1743207447…` (marzo 2026) porque los
     recargaron en bloque, incluidos actos de 2015. Usar esa fecha pondría
     media década de circulares en el mismo día. La fecha sale del título
     ("de 19 de enero de 2024"), que es como la entidad las identifica.

  ⑤ LA CBJ SE SOLAPA CON CIRCULARES EXTERNAS, A PROPÓSITO. La categoría "Circular
     Básica Jurídica" (18) no son 18 circulares distintas: es el **linaje** de la
     CBJ —la vigente más todas las que la modifican—, y 13 de ellas están
     también en "Circulares Externas" (199), con el MISMO PDF subido dos veces a
     carpetas distintas. Se conserva UN registro con `es_cbj=True`, para poder
     filtrar "lo que toca la Circular Básica Jurídica" —que es justo la pregunta
     del cliente de LA/FT— sin inflar el conteo del pilar.

  ⑥ LA PRIMERA FILA DE CADA PÁGINA SE ROBA EL PDF DEL PIE DE PÁGINA si se parte
     el HTML por `<hr>`: el primer trozo arrastra el chrome del portal y su
     primer `href` a `/documents/` es un PDF de accesibilidad del footer. Las
     filas se aíslan por `class="img-modal"` (el icono que abre cada fila) y se
     cortan en el `<hr>` siguiente. Con el corte bueno: 2 filas sin PDF de 734.

  ⑦ HAY TÍTULOS QUE NO SE DEJAN LEER, Y NO SON INTRUSOS. 13 actos vienen
     titulados con la errata de la fuente ("Cirular externa", "Resoución",
     "RESOLUCIÓN100-001063" sin espacio), con el número pelado ("100-000179"),
     con el nombre del archivo ("32944.pdf") o con la descripción en vez del
     título ("Por la cual se da cumplimiento al artículo 238…"). Están dentro de
     los registros que la entidad lleva de SUS PROPIOS actos, donde lo ajeno
     siempre se anuncia ("DECRETO…", "DIRECTIVA…"), así que se emiten con
     `titulo_irregular=True` en vez de perderse. Fuera de esos tres registros,
     un título ilegible queda 'ambiguo' y se imprime para que lo mire un humano.
     ⚠️ Uno de ellos —"\u200bResolución 165-002564"— empieza con un ZERO WIDTH
     SPACE pegado desde Word: un `^\\s*` NO lo salta, porque Python clasifica
     U+200B como formato (Cf), no como espacio. `_limpia()` lo quita.

  ⑧ EL MISMO TÍTULO PUEDE SER UN ACTO O DOS, Y LO DECIDE LA FECHA. Deduplicar
     por título a secas borra 9 actos reales: la fuente reusa títulos cortos
     ("Circular Externa No. 100-000010") entre años distintos. Pero NO
     deduplicar deja 2 actos contados dos veces, que son los que aparecen a la
     vez en Circulares Externas y en CBJ. La llave que separa los dos casos es
     si el título trae FECHA: con fecha el título ya identifica el acto (se
     fusiona), sin fecha no (se separa por URL).

  ⑨ EL SLUG DEL PROYECTO NO BASTA: 7 DE 49 NODOS SE CAEN. Al quitarle el
     querystring al enlace "ver más" se pierde el `assetEntryId`, y los nodos
     cuyo slug amigable llega truncado ("…/proyecto-de-resolución-") devuelven
     la página de Error de Liferay. No falla ruidosamente: devuelve un HTML
     válido del que se extrae el título "Error". Se conserva la URL completa, y
     el nodo que aun así responda "Error" se cuenta y se reporta, nunca se
     emite.

  ⑩ EL NÚMERO DEL ACTO SE REINICIA CADA AÑO — NO ES IDENTIFICADOR. 38 números
     se repiten entre 134 actos: `100-000001` existe **diez veces** (2010, 2016,
     2017, 2018, 2021, 2022, 2023, 2024…). "Circular 100-000008" es ambiguo por
     sí solo — el de 2022 es la Circular Básica Jurídica y el de 2023 es una
     circular de plazos de reporte. La identidad es **(número, año)**, y el
     `_id` lleva además un hash del título+categoría+URL. Es exactamente la
     misma trampa que el número de radicado en el histórico legislativo.

  ⑪ UNA PÁGINA QUE FALLA TRUNCA LA CATEGORÍA EN SILENCIO. Cortar el bucle al
     primer tropiezo dejó una corrida con **180 de 480 resoluciones** y un
     resumen que se veía perfectamente normal. Hay dos redes: reintento por
     página (3 veces), y —porque el portal a veces devuelve una página corta que
     igual trae la marca de fila— comparación contra el `totalArticulos` que
     declara el propio portal, con reintento de la categoría entera y aviso
     `_categorias_incompletas` si aun así queda corta. **No consolides una
     corrida que traiga ese aviso.**

  ⑫ 413 DE 734 ACTOS NO TIENEN FECHA, Y NO ES UN BUG DEL PARSER. Los actos
     viejos se titulan solo con su número ("Circular Externa No. 115-000008") y
     su PDF tampoco la trae: el último tramo de la URL es un UUID, no un nombre
     de archivo. Se verificó uno por uno que **0** son recuperables del nombre
     del PDF. Van con `fecha=None` (y `anio` cuando el título trae el año). Es
     una propiedad de la fuente y hay que declararla, no rellenarla.


QUÉ SE EMITE. `tipo_acto` POR FILA — `circular` · `resolucion` · `otro`. Es muy
probable que esta fuente aporte **CERO sanciones**, y está bien: el pilar dejó de
ser solo sanciones. `sancionado` va en None porque estos actos son de carácter
general y no tienen destinatario individual (ver la nota sobre el guion en
`_pendiente-supersociedades.json`).

SALIDA. `raw/supersociedades.json`. La entrada propuesta para fuentes.json va en
`_pendiente-supersociedades.json` — este harvester NO toca fuentes.json,
harvest_supers.py, build_s3.py ni el cron.

Uso:
  python3 tools/caudal/supers/harvest_supersociedades.py probe   # mapea y mide, no escribe
  python3 tools/caudal/supers/harvest_supersociedades.py fetch   # cosecha (resumible)
  python3 tools/caudal/supers/harvest_supersociedades.py fetch --solo proyectos
  python3 tools/caudal/supers/harvest_supersociedades.py test    # valida CBJ + proyecto SAGR/CBJ
Luego (los corre su dueño, no este script):
  python3 tools/caudal/supers/harvest_supers.py normalize
  python3 tools/caudal/supers/build_s3.py
"""
import argparse
import html
import hashlib
import json
import re
import subprocess
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RAW = REPO / 'Bases de datos' / 'leyes-senado' / 'supers' / 'raw'
SLUG = 'supersociedades'
OUT_JSON = RAW / f'{SLUG}.json'
CACHE_NODOS = RAW / f'{SLUG}-nodos.json'     # nodos de proyecto ya abiertos (resumible)

BASE = 'https://www.supersociedades.gov.co'
URL_NORMATIVA = f'{BASE}/es/web/nuestra-entidad/normativa'
URL_PROYECTOS = f'{BASE}/web/nuestra-entidad/proyectos-de-normatividad'
PORTLET_PROY = 'com_liferay_asset_publisher_web_portlet_AssetPublisherPortlet_INSTANCE_gllg'

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')

PAGINA = 20         # tamaño fijo del servidor en las dos colas (trampa ③)
MAX_PAGES = 40      # cota dura: la categoría más grande (1.407) son 71 páginas… ver COTA
PAUSA = 0.35        # cortesía con el portal

# --- taxonomía del buscador interno (leída de los onclick, ago-2026) ---------
# `cosechar` = ¿vale la pena recorrerla? El EMISOR no se decide acá sino por fila
# (`_emisor`), porque "Estructura" es mixta y "Otra Normativa"/"Escala Salarial"
# resultaron ajenas enteras pese al nombre (trampa ①).
CATEGORIAS = {
    '1256465': dict(nombre='Circulares Externas',                   n=199,  cosechar=True,  tipo_acto='circular'),
    '1256466': dict(nombre='Circular Básica Jurídica',              n=18,   cosechar=True,  tipo_acto='circular'),
    '1256464': dict(nombre='Resoluciones',                          n=480,  cosechar=True,  tipo_acto='resolucion'),
    '1256467': dict(nombre='Estructura',                            n=10,   cosechar=True,  tipo_acto='resolucion',
                    nota='MIXTA: resoluciones propias + decretos ajenos'),
    '8045710': dict(nombre='Otra Normativa',                        n=4,    cosechar=True,  tipo_acto='otro',
                    nota='medida ago-2026: son 4 Directivas Presidenciales, ajenas'),
    # las de abajo NO se recorren: medidas como ajenas enteras o no normativas.
    '1256468': dict(nombre='Escala Salarial',                       n=13,   cosechar=False, tipo_acto='otro',
                    nota='13 decretos de Función Pública'),
    '1256463': dict(nombre='Decretos',                              n=303,  cosechar=False, tipo_acto='otro'),
    '1256462': dict(nombre='Leyes',                                 n=91,   cosechar=False, tipo_acto='otro'),
    '1264225': dict(nombre='Decreto Único Reglamentario Sectorial', n=106,  cosechar=False, tipo_acto='otro'),
    '1256461': dict(nombre='Constitución Política',                 n=1,    cosechar=False, tipo_acto='otro'),
    '1256470': dict(nombre='Actas de Conciliación',                 n=1407, cosechar=False, tipo_acto='otro',
                    nota='actos particulares, no normativa'),
}
CATS_COSECHAR = [c for c, v in CATEGORIAS.items() if v['cosechar']]

# Los tres registros donde la entidad lleva SUS PROPIOS actos. Ahí lo ajeno
# siempre se anuncia con su tipo ("DECRETO…", "DIRECTIVA…"), así que un título
# ilegible es un acto propio mal titulado (trampa ⑦), no un intruso.
CATS_AUTOREGISTRO = {'1256465', '1256466', '1256464'}

# Rótulo legible del acto (va a `tipo_sancion` del esquema del pilar). No es el
# nombre de la categoría: "Circulares Externas" es el estante, "Circular Externa"
# es el acto.
ROTULO = {
    '1256465': 'Circular Externa',
    '1256466': 'Circular Básica Jurídica',
    '1256464': 'Resolución',
    '1256467': 'Resolución',
    '8045710': 'Otra normativa',
}

# Encabezados de título que identifican al emisor. Supersociedades numera sus
# actos 100-XXXXXX / 500-XXXXXX; lo ajeno se presenta con su propio tipo de norma.
_RE_PROPIA = re.compile(
    # incluye las erratas de la propia fuente: "Cirular externa", "Resoución",
    # "RESOLUCIÓN100-001063" (sin espacio) y el prefijo "RE 511-000183".
    r'^\s*(circulare?s?|cirular|resoluci[oó]n|resouci[oó]n|resoluion|instructivo|'
    r'carta circular|re\s+\d{3}-)', re.I)
_RE_AJENA = re.compile(r'^\s*(decreto|ley|acto legislativo|directiva|constituci[oó]n|'
                       r'sentencia|acuerdo|conpes)\b', re.I)

MESES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10,
    'noviembre': 11, 'diciembre': 12,
    'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6, 'jul': 7,
    'ago': 8, 'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dic': 12,
}


# ------------------------------------------------------------------ utilidades

def _curl(url, timeout=60):
    cmd = ['/usr/bin/curl', '-s', '-A', UA, '--max-time', str(timeout), '-L', url]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout + 15)
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0:
        return None
    return r.stdout.decode('utf-8', errors='replace')


_ZERO = dict.fromkeys(map(ord, '\u200b\u200c\u200d\ufeff\u00ad\u2060'), None)


def _limpia(s):
    """Quita los invisibles que la fuente arrastra al pegar desde Word.

    ⚠️ Un ZERO WIDTH SPACE (U+200B) al principio del título rompe cualquier
    `^\\s*` : Python lo clasifica como Cf (formato), no como espacio. Medido:
    "\u200bResolución 165-002564" salía 'ambiguo' y se quedaba sin publicar.
    """
    return (s or '').translate(_ZERO).strip()


def _txt(s):
    """HTML → texto plano colapsado."""
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s or ''))).strip()


def _norm(s):
    """Clave de comparación: sin tildes, sin puntuación, minúsculas."""
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def _fecha_de_texto(s):
    """'19 de enero de 2024' / '08 abr. 2026' / '2016' → ISO (o solo el año).

    Devuelve (iso|None, anio|None). La fecha autoritativa vive en el TÍTULO
    del acto, no en el timestamp del archivo (trampa ④).
    """
    if not s:
        return None, None
    t = html.unescape(s).lower().replace('\xa0', ' ')
    m = re.search(r'(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})', t)
    if not m:
        m = re.search(r'(\d{1,2})\s+([a-záéíóú]{3,10})\.?\s+(\d{4})', t)
    if m:
        dia, mes, anio = int(m.group(1)), _norm(m.group(2)), int(m.group(3))
        mm = MESES.get(mes) or MESES.get(mes[:3])
        if mm and 1990 <= anio <= 2100 and 1 <= dia <= 31:
            return f'{anio:04d}-{mm:02d}-{dia:02d}', anio
    m = re.search(r'\b(19|20)\d{2}\b', t)
    if m:
        return None, int(m.group(0))
    return None, None


def _sid(*partes):
    """_id legible + hash corto: dos títulos largos comparten sus primeros 90
    caracteres y colisionarían (medido: 2 proyectos de la misma circular)."""
    base = _norm(partes[0]).replace(' ', '-')[:80]
    h = hashlib.sha1('||'.join(str(x) for x in partes).encode('utf-8')).hexdigest()[:8]
    return f'{base}-{h}'


def _numero_acto(titulo):
    """'Circular Externa 100-000020 de 2 de julio de 2026' → '100-000020'."""
    m = re.search(r'\b(\d{3}-\d{5,6})\b', titulo or '')
    return m.group(1) if m else None


def _emisor(titulo, cat_id=None):
    """'propia' | 'ajena' | 'ambiguo' — trampa ①, se decide POR FILA.

    La categoría no sirve como criterio principal: "Estructura" mezcla
    resoluciones propias con decretos ajenos. Pero sí sirve de RESPALDO en los
    tres registros que la entidad lleva de sus propios actos (trampa ⑦): ahí lo
    ajeno siempre se anuncia ("DECRETO…", "DIRECTIVA…"), así que un título que
    no se anuncia y no se deja leer es un acto propio mal titulado, no un
    intruso. Lo que quede 'ambiguo' se imprime — nunca se descarta en silencio.
    """
    t = _limpia(titulo)
    if _RE_AJENA.match(t):
        return 'ajena'
    if _RE_PROPIA.match(t):
        return 'propia'
    if cat_id in CATS_AUTOREGISTRO:
        return 'propia_irregular'
    return 'ambiguo'


# ------------------------------------------------- cola B · buscador interno

_ROW_TITULO = re.compile(r'<span title="([^"]+)" class="titulo-articulo">')
_ROW_PDF = re.compile(r'href="(https?://[^"]*?/documents/[^"]+)"')
_ROW_CAT = re.compile(r'class="texto-categoria"[^>]*>([^<]*)<')
_ROW_SIZE = re.compile(r'class="text-info-data">([^<]*)<')
_ROW_P = re.compile(r'<p>(.*?)</p>', re.S)
_TOTAL_RE = re.compile(r"var totalArticulos = '(\d+)'")


def _parse_filas(pagina_html):
    """Aísla las filas por `class="img-modal"` y corta en el `<hr>` (trampa ⑥)."""
    filas = []
    for parte in pagina_html.split('class="img-modal"')[1:]:
        chunk = parte.split('<hr>')[0]
        m = _ROW_TITULO.search(chunk)
        if not m:
            continue
        titulo = _limpia(html.unescape(m.group(1)))
        pdf = _ROW_PDF.search(chunk)
        cat = _ROW_CAT.search(chunk)
        size = _ROW_SIZE.search(chunk)
        ps = _ROW_P.findall(chunk)
        desc = _txt(ps[0]) if ps else ''
        filas.append(dict(
            titulo=titulo,
            descripcion=desc,
            url=html.unescape(pdf.group(1)) if pdf else None,
            categoria_portal=(cat.group(1).strip() if cat else ''),
            tamano=(size.group(1).strip() if size else ''),
        ))
    return filas


def listar_categoria(cat_id, max_pages=MAX_PAGES):
    """Pagina una categoría del buscador interno (de a 20 fijos, trampa ③).

    ⚠️ Cada página se reintenta: el portal falla de vez en cuando y cortar el
    bucle al primer tropiezo TRUNCA la categoría EN SILENCIO (medido: una
    corrida devolvió 180 de 480 resoluciones y el resumen se veía normal). El
    llamador compara contra el `totalArticulos` que declara el propio portal.
    """
    vistos, filas, start, total = set(), [], 0, None
    for _ in range(max_pages):
        url = f'{URL_NORMATIVA}?id={cat_id}&start={start}&end={start + PAGINA}'
        t = None
        for intento in range(3):
            t = _curl(url)
            if t is not None and 'titulo-articulo' in t:
                break
            time.sleep(1.5 * (intento + 1))
        if t is None or 'titulo-articulo' not in t:
            print(f'    ! sin respuesta en start={start} (cat {cat_id}) tras 3 intentos',
                  file=sys.stderr)
            break
        if total is None:
            m = _TOTAL_RE.search(t)
            total = int(m.group(1)) if m else None
        nuevas = 0
        for f in _parse_filas(t):
            k = (_norm(f['titulo']), f['url'])      # trampa ⑧
            if k in vistos:
                continue
            vistos.add(k)
            filas.append(f)
            nuevas += 1
        if nuevas == 0:                      # página vacía o repetida → fin
            break
        start += PAGINA
        if total is not None and start >= total:
            break
        time.sleep(PAUSA)
    return filas, total


# ------------------------------------------------ cola A · proyectos (Liferay)

_VERMAS_RE = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>\s*ver m[aá]s', re.I)


def listar_proyectos(max_pages=MAX_PAGES):
    """Pagina el AssetPublisher y devuelve [(url_completa, clave)].

    ⚠️ La URL se conserva ENTERA, con su querystring: el `assetEntryId` que va
    ahí es lo único que resuelve los 7 nodos (de 49) cuyo slug amigable llega
    truncado (trampa ⑨). `delta` se ignora del lado del servidor.
    """
    vistos, urls = set(), []
    for cur in range(1, max_pages + 1):
        url = (f'{URL_PROYECTOS}?p_p_id={PORTLET_PROY}&p_p_lifecycle=0'
               f'&_{PORTLET_PROY}_cur={cur}&p_r_p_resetCur=false')
        t = _curl(url)
        if t is None:
            print(f'    ! sin respuesta en cur={cur} (proyectos)', file=sys.stderr)
            break
        nuevos = 0
        for href in _VERMAS_RE.findall(t):
            full = html.unescape(href).replace(':443', '')
            clave = full.split('?')[0]              # identidad estable del nodo
            if clave in vistos:
                continue
            vistos.add(clave)
            urls.append((full, clave))
            nuevos += 1
        if nuevos == 0:
            break
        time.sleep(PAUSA)
    return urls


_CAMPOS_NODO = [
    ('tipo_norma', r'Tipo de normativa:'),
    ('descripcion', r'Descripci[oó]n del proyecto:'),
    ('plazo', r'Per[ií]odo de fechas para presentar comentarios:'),
    ('correos', r'Correos para observaciones:'),
    ('dependencia', r'Dependencia al interior de la entidad encargada de liderar el proyecto normativo:'),
    ('responsable', r'Responsable t[eé]cnico:'),
    ('cargo_responsable', r'Cargo del Responsable t[eé]cnico:'),
]


def parse_nodo_proyecto(h, url):
    """Extrae la ficha completa de un proyecto de normativa."""
    t = re.sub(r'<script.*?</script>', '', h, flags=re.S)
    t = re.sub(r'<style.*?</style>', '', t, flags=re.S)
    lineas = [_limpia(x) for x in html.unescape(re.sub(r'<[^>]+>', '\n', t)).split('\n')]
    lineas = [x for x in lineas if x]

    # el título del nodo es la línea que sigue a "Atrás"
    titulo = ''
    for i, l in enumerate(lineas):
        if l == 'Atrás' and i + 1 < len(lineas):
            titulo = lineas[i + 1]
            break

    campos = {}
    for clave, patron in _CAMPOS_NODO:
        rx = re.compile(patron + r'$', re.I)
        for i, l in enumerate(lineas):
            if rx.match(l):
                vals = []
                for j in range(i + 1, min(i + 6, len(lineas))):
                    nl = lineas[j]
                    if any(re.match(p + r'$', nl, re.I) for _, p in _CAMPOS_NODO):
                        break
                    if nl.startswith(('Documentación relacionada', 'Añadir comentarios',
                                      'Por favor identifíquese', 'Oculto')):
                        break
                    vals.append(nl)
                campos[clave] = _limpia(' '.join(vals))
                break

    plazo = campos.get('plazo', '')
    m = re.search(r'Del\s+(.+?)\s+(?:al|hasta el|hasta)\s+(.+?)\s*$', plazo, re.I)
    ini_iso, fin_iso = (None, None)
    if m:
        ini_iso, _ = _fecha_de_texto(m.group(1))
        fin_iso, _ = _fecha_de_texto(m.group(2))

    docs = []
    for href in sorted(set(re.findall(r'href="([^"]*/documents/[^"]+)"', h))):
        u = html.unescape(href)
        if u.startswith('/'):
            u = BASE + u
        # el footer del portal cuela dos PDF de chrome en todas las páginas
        if 'Atenci' in u and 'preferencial' in u:
            continue
        if u.endswith('Decreto-Unico-Reglamentario-Sectorial-1074-de-2015.pdf'):
            continue
        if u.endswith('.xlsx'):
            continue
        docs.append(u)

    fecha_pub, anio_pub = (None, None)
    m = re.search(r'Publicado\s+(\d{1,2})/(\d{1,2})/(\d{2})', h)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), 2000 + int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            fecha_pub, anio_pub = f'{y:04d}-{mo:02d}-{d:02d}', y

    return dict(
        titulo=titulo,
        descripcion=campos.get('descripcion', ''),
        tipo_norma=campos.get('tipo_norma', ''),
        plazo_texto=plazo,
        plazo_inicio=ini_iso,
        plazo_fin=fin_iso,
        correos=campos.get('correos', ''),
        dependencia=campos.get('dependencia', ''),
        responsable=campos.get('responsable', ''),
        cargo_responsable=campos.get('cargo_responsable', ''),
        fecha_publicacion=fecha_pub,
        anio=anio_pub,
        docs=docs,
        url_ficha=url,
    )


# ------------------------------------------------------------------- cosecha

def _registro_normativa(fila, cat_id, irregular=False):
    cat = CATEGORIAS[cat_id]
    iso, anio = _fecha_de_texto(fila['titulo'])
    num = _numero_acto(fila['titulo'])
    return dict(
        _id=f'ss-norm-{_sid(fila["titulo"], cat_id, fila.get("url"))}',
        cola='normativa',
        categoria=cat['nombre'],
        categoria_id=cat_id,
        tipo_acto=cat['tipo_acto'],
        tipo_norma=ROTULO.get(cat_id, cat['nombre']),
        es_cbj=(cat_id == '1256466'),
        numero=num,
        titulo=fila['titulo'],
        descripcion=fila['descripcion'],
        fecha=iso,
        anio=anio,
        url=fila['url'],
        url_ficha=f'{URL_NORMATIVA}?id={cat_id}',
        tamano=fila['tamano'],
        titulo_irregular=irregular,
    )


def _registro_proyecto(n):
    iso = n['plazo_inicio'] or n['fecha_publicacion']
    anio = n['anio']
    if iso and not anio:
        anio = int(iso[:4])
    return dict(
        _id=f'ss-proy-{_sid(n["titulo"], n.get("url_ficha"))}',
        cola='proyectos',
        categoria='Proyectos de Normativa',
        categoria_id=None,
        tipo_acto='otro',
        tipo_norma=n['tipo_norma'] or 'Proyecto de normativa',
        es_cbj=('circular basica juridica' in _norm(n['titulo'])
                or 'circular basica juridica' in _norm(n['descripcion'])),
        numero=None,                       # un proyecto todavía no tiene número
        numero_referenciado=_numero_acto(n['titulo']),
        titulo=n['titulo'],
        descripcion=n['descripcion'],
        fecha=iso,
        anio=anio,
        url=(n['docs'][0] if n['docs'] else None),
        url_ficha=n['url_ficha'],
        tamano='',
        plazo_texto=n['plazo_texto'],
        plazo_inicio=n['plazo_inicio'],
        plazo_fin=n['plazo_fin'],
        correos=n['correos'],
        dependencia=n['dependencia'],
        responsable=n['responsable'],
        cargo_responsable=n['cargo_responsable'],
        docs=n['docs'],
        fecha_publicacion=n['fecha_publicacion'],
    )


def _dedup_cbj(regs):
    """Trampa ⑤: la CBJ y Circulares Externas comparten actos. Un solo registro,
    marcado `es_cbj` si aparece en el linaje de la Circular Básica Jurídica."""
    por_clave, orden, fusionados = {}, [], 0
    for r in regs:
        # ⚠️ los proyectos se deduplican por FICHA, no por título: la misma
        # circular se somete a consulta más de una vez y son eventos distintos
        # (medido: 2 pares con título idéntico y ventanas de comentarios
        # distintas). Deduplicar por título los fusionaría y perdería una.
        # ⚠️ la llave depende de si el título trae FECHA (trampa ⑧):
        #   · con fecha  → el título YA identifica el acto: se fusionan las dos
        #     copias que el portal publica en Circulares Externas y en CBJ (dos
        #     PDF idénticos en carpetas distintas). Medido: 2 casos.
        #   · sin fecha  → "Circular Externa No. 100-000010" es un título que
        #     la fuente reusa entre AÑOS: son actos DISTINTOS y hay que
        #     separarlos por URL o se borran. Medido: 6 casos.
        if r['cola'] == 'proyectos':
            k = ('proyectos', r.get('url_ficha'))
        else:
            k = ('normativa', _norm(r['titulo']), r.get('fecha') or r.get('url'))
        if k in por_clave:
            prev = por_clave[k]
            prev['es_cbj'] = prev['es_cbj'] or r['es_cbj']
            cats = set(prev.get('categorias_portal', [prev['categoria']]))
            cats.add(r['categoria'])
            prev['categorias_portal'] = sorted(cats)
            if not prev.get('descripcion') and r.get('descripcion'):
                prev['descripcion'] = r['descripcion']
            fusionados += 1
            continue
        r['categorias_portal'] = [r['categoria']]
        por_clave[k] = r
        orden.append(r)
    return orden, fusionados


def fetch(solo=None, max_pages=MAX_PAGES):
    RAW.mkdir(parents=True, exist_ok=True)
    regs, descartado = [], {}

    if solo in (None, 'normativa'):
        print('· cola B · buscador interno (emisor por FILA, trampa ①)')
        ajenas, ambiguas, irregulares, incompletas = Counter(), [], [], {}
        for cat_id in CATS_COSECHAR:
            cat = CATEGORIAS[cat_id]
            filas, total = listar_categoria(cat_id, max_pages)
            # el portal a veces devuelve una página corta que igual "se ve" bien
            # (trae la marca de fila), así que el reintento por página no basta:
            # si la cosecha queda por debajo de lo que el propio portal declara,
            # se repite la categoría entera y se conserva la mejor pasada.
            for _ in range(2):
                if total is None or len(filas) >= total:
                    break
                print(f'      · reintento de {cat["nombre"]} '
                      f'({len(filas)}/{total})')
                time.sleep(2)
                otra, total2 = listar_categoria(cat_id, max_pages)
                if len(otra) > len(filas):
                    filas, total = otra, (total2 or total)
            if total is not None and len(filas) < total:
                falta = total - len(filas)
                # puede ser dedup legítimo (mismo acto en dos categorías) o
                # truncamiento por fallo de red: se avisa y se deja constancia.
                print(f'    ⚠ {cat["nombre"]}: cosechadas {len(filas)} de {total} '
                      f'que declara el portal (faltan {falta})')
                incompletas[cat['nombre']] = dict(cosechadas=len(filas), portal=total)
            n_ok = n_irr = 0
            for f in filas:
                em = _emisor(f['titulo'], cat_id)
                if em in ('propia', 'propia_irregular'):
                    irr = (em == 'propia_irregular')
                    regs.append(_registro_normativa(f, cat_id, irregular=irr))
                    n_ok += 1
                    n_irr += irr
                    if irr:
                        irregulares.append((cat['nombre'], f['titulo']))
                elif em == 'ajena':
                    ajenas[cat['nombre']] += 1
                else:
                    ambiguas.append((cat['nombre'], f['titulo']))
            print(f'    {cat["nombre"]:<32} {len(filas):>4} filas → {n_ok:>4} propias '
                  f'({n_irr} de título irregular) · portal dice {total if total is not None else "?"}')
        if ajenas:
            print(f'    ajenas descartadas dentro de lo recorrido: {dict(ajenas)}')
        if irregulares:
            print(f'    · {len(irregulares)} títulos irregulares de la fuente, emitidos '
                  f'con titulo_irregular=True (trampa ⑦):')
            for c, t in irregulares[:8]:
                print(f'        [{c}] {t[:88]}')
        if ambiguas:
            print(f'    ⚠ {len(ambiguas)} títulos AMBIGUOS (no se emiten; revísalos):')
            for c, t in ambiguas[:20]:
                print(f'        [{c}] {t[:90]}')
        if incompletas:
            print(f'    ⚠⚠ categorías incompletas: {incompletas} — NO consolides '
                  f'esta corrida sin volver a correrla')
        descartado = {CATEGORIAS[c]['nombre']: CATEGORIAS[c]['n']
                      for c in CATEGORIAS if not CATEGORIAS[c]['cosechar']}
        if incompletas:
            descartado['_categorias_incompletas'] = incompletas
        descartado.update({f'{k} (ajenas dentro de la categoría)': v for k, v in ajenas.items()})
        if ambiguas:
            descartado['_ambiguos'] = [f'[{c}] {t}' for c, t in ambiguas]
        if irregulares:
            descartado['_irregulares_emitidos'] = [f'[{c}] {t}' for c, t in irregulares]

    if solo in (None, 'proyectos'):
        print('· cola A · proyectos de normativa (AssetPublisher)')
        cache = {}
        if CACHE_NODOS.exists():
            cache = json.loads(CACHE_NODOS.read_text(encoding='utf-8'))
        urls = listar_proyectos(max_pages)
        print(f'    {len(urls)} proyectos en el listado')
        nuevos, fallidos = 0, []
        for i, (full, clave) in enumerate(urls, 1):
            n = cache.get(clave)
            # un nodo cacheado con título 'Error' es una cosecha vieja hecha sin
            # el assetEntryId (trampa ⑨): se reintenta con la URL completa
            if n is None or (n.get('titulo') or '').strip().lower() == 'error':
                h = _curl(full)
                if h is None:
                    print(f'    ! nodo sin respuesta: {clave[:90]}', file=sys.stderr)
                    fallidos.append(clave)
                    continue
                n = parse_nodo_proyecto(h, clave)
                cache[clave] = n
                nuevos += 1
                time.sleep(PAUSA)
            if (n.get('titulo') or '').strip().lower() == 'error':
                fallidos.append(clave)
            if i % 10 == 0:
                print(f'      {i}/{len(urls)}')
        CACHE_NODOS.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding='utf-8')
        print(f'    nodos abiertos ahora: {nuevos} · en caché: {len(cache)}')
        if fallidos:
            print(f'    ⚠ {len(fallidos)} nodos siguen devolviendo la página de Error:')
            for u in fallidos[:10]:
                print(f'        {u[-90:]}')
        for full, clave in urls:
            n = cache.get(clave)
            if n and (n.get('titulo') or '').strip().lower() != 'error':
                regs.append(_registro_proyecto(n))

    regs, fusionados = _dedup_cbj(regs)
    if fusionados:
        print(f'· dedup CBJ↔Circulares Externas: {fusionados} actos fusionados (trampa ⑤)')

    payload = dict(
        _fuente='supersociedades',
        _generado=time.strftime('%Y-%m-%d %H:%M:%S'),
        _base=BASE,
        _descartado_no_propio=descartado,
        _nota=('Solo se emiten las categorías que EXPIDE la Superintendencia de '
               'Sociedades. Decretos, Leyes, DURS, Constitución y Actas de '
               'Conciliación se cuentan en _descartado_no_propio y no se emiten: '
               'no son suyas (o no son normativa) y duplicarían los pilares '
               'Ejecutivo y Congreso.'),
        registros=regs,
    )
    # si la corrida fue parcial (--solo), no pisamos lo que ya había de la otra cola
    if solo and OUT_JSON.exists():
        prev = json.loads(OUT_JSON.read_text(encoding='utf-8'))
        otros = [r for r in prev.get('registros', []) if r.get('cola') != solo]
        payload['registros'] = otros + regs
        payload['_descartado_no_propio'] = (descartado
                                            or prev.get('_descartado_no_propio', {}))
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'\n→ {OUT_JSON.relative_to(REPO)}  ({len(payload["registros"])} registros)')
    _resumen(payload['registros'])
    return payload


def _resumen(regs):
    print('\n  por cola      ', dict(Counter(r['cola'] for r in regs)))
    print('  por tipo_acto ', dict(Counter(r['tipo_acto'] for r in regs)))
    print('  por categoría ', dict(Counter(r['categoria'] for r in regs)))
    fechas = sorted(r['fecha'] for r in regs if r.get('fecha'))
    print(f'  rango fechas   {fechas[0] if fechas else "?"} .. {fechas[-1] if fechas else "?"}'
          f'  | sin fecha ISO: {sum(1 for r in regs if not r.get("fecha"))}'
          f'  | sin año: {sum(1 for r in regs if not r.get("anio"))}')
    print(f'  sin PDF        {sum(1 for r in regs if not r.get("url"))}')
    print(f'  _id únicos     {len({r["_id"] for r in regs})} de {len(regs)}')
    print(f'  linaje CBJ     {sum(1 for r in regs if r.get("es_cbj"))}')


# --------------------------------------------------------------------- probe

def probe():
    """Mapea el portal y MIDE, sin escribir nada."""
    print('=' * 70)
    print('PROBE · Superintendencia de Sociedades')
    print('=' * 70)

    print('\n[1] Categorías del buscador interno (¿siguen siendo las mismas?)')
    h = _curl(URL_NORMATIVA)
    if not h:
        print('  ! el portal no respondió'); return
    vivas = dict(re.findall(r"findByCategory\('(\d+)'\);\" title=\"([^\"]+)\"", h))
    conteos = dict(re.findall(r'id="cont_(\d+)" val="(\d+)"', h))
    total = 0
    for cid, nombre in vivas.items():
        n = int(conteos.get(cid, 0)); total += n
        cfg = CATEGORIAS.get(cid)
        marca = 'recorre' if (cfg and cfg['cosechar']) else 'omite  '
        aviso = ''
        if not cfg:
            aviso = '  ← ¡CATEGORÍA NUEVA, no está en CATEGORIAS!'
        elif cfg['n'] != n:
            aviso = f'  ← cambió: teníamos {cfg["n"]}'
        print(f'  {marca} {n:>5}  {nombre}{aviso}')
    faltan = set(CATEGORIAS) - set(vivas)
    if faltan:
        print('  ! categorías que ya no aparecen:', [CATEGORIAS[c]['nombre'] for c in faltan])
    rec = sum(int(conteos.get(c, 0)) for c in vivas if CATEGORIAS.get(c, {}).get('cosechar'))
    print(f'  TOTAL {total} · se recorre {rec} · se omite {total - rec} '
          f'({100 * (total - rec) // max(total, 1)}%, trampa ①)')

    print('\n[2] ¿El buscador por palabra sirve para temas? (trampa ②)')
    for kw in ('sagrilaft', 'cripto', 'virtuales', 'autocontrol', 'circular'):
        t = _curl(f'{URL_NORMATIVA}?keyword={kw}')
        m = _TOTAL_RE.search(t or '')
        print(f'    keyword={kw:<12} → {m.group(1) if m else "?"} resultados')
    print('    (los títulos son pura numeración; el tema vive en la descripción)')

    print('\n[3] ¿`end` amplía la página? (trampa ③)')
    for end in (20, 100, 200):
        t = _curl(f'{URL_NORMATIVA}?id=1256465&start=0&end={end}')
        print(f'    end={end:<4} → {len(_parse_filas(t or ""))} filas')

    print('\n[4] Muestra de cada categoría que se recorre (título · fecha · PDF)')
    for cid in CATS_COSECHAR:
        t = _curl(f'{URL_NORMATIVA}?id={cid}&start=0&end={PAGINA}')
        filas = _parse_filas(t or '')
        sin_pdf = sum(1 for f in filas if not f['url'])
        em = Counter(_emisor(f['titulo']) for f in filas)
        print(f'  · {CATEGORIAS[cid]["nombre"]} ({len(filas)} en pág. 1, sin PDF: {sin_pdf}) emisor={dict(em)}')
        for f in filas[:2]:
            iso, anio = _fecha_de_texto(f['titulo'])
            print(f'      [{_emisor(f["titulo"])}] {f["titulo"][:66]}')
            print(f'        fecha={iso or anio}  {f["descripcion"][:90]}')

    print('\n[5] Paginación del AssetPublisher de proyectos')
    urls = listar_proyectos()
    print(f'    {len(urls)} proyectos únicos')
    if urls:
        h2 = _curl(urls[0])
        n = parse_nodo_proyecto(h2 or '', urls[0])
        print(f'    nodo más reciente: {n["titulo"][:80]}')
        print(f'      tipo={n["tipo_norma"]} · plazo={n["plazo_inicio"]}..{n["plazo_fin"]}')
        print(f'      dependencia={n["dependencia"]} · responsable={n["responsable"]}')
        print(f'      docs={len(n["docs"])}')

    print('\n[6] Control cruzado SUIN-Juriscol (vía 1, solo índice)')
    t = _curl("https://www.datos.gov.co/resource/fiev-nid6.json?$select=tipo,count(*)%20as%20n"
              "&$group=tipo&$where=upper(entidad)%20like%20'%25SOCIEDADES%25'&$limit=50")
    try:
        print('   ', json.loads(t))
    except Exception:
        print('    (sin respuesta)')
    print('    ⚠ sin título, sin fecha, sin PDF → índice, no norma')


# ---------------------------------------------------------------------- test

def test():
    """Valida los dos objetivos del encargo contra la cosecha en disco."""
    if not OUT_JSON.exists():
        print('! no hay cosecha todavía: corre `fetch` primero'); return 1
    d = json.loads(OUT_JSON.read_text(encoding='utf-8'))
    regs = d['registros']
    ok = True

    print(f'cosecha: {len(regs)} registros · generada {d.get("_generado")}')

    print('\n[A] Circular Básica Jurídica — el linaje completo')
    cbj = [r for r in regs if r.get('es_cbj')]
    print(f'    {len(cbj)} actos tocan la CBJ')
    actos = [r for r in regs if r['cola'] == 'normativa']
    # (número, año): el número SOLO no identifica nada (trampa ⑪)
    vig = [r for r in actos if (r.get('numero'), r.get('anio')) == ('100-000008', 2022)]
    nueva = [r for r in actos if (r.get('numero'), r.get('anio')) == ('100-000020', 2026)]
    for etiqueta, lst in (('CBJ 100-000008 de 2022 (la vigente/derogada)', vig),
                          ('CE 100-000020 de 2026 (la que la modifica integralmente)', nueva)):
        if lst:
            r = lst[0]
            print(f'    ✓ {etiqueta}\n        {r["titulo"]}\n        {r["fecha"]} · {(r["url"] or "")[:95]}')
        else:
            print(f'    ✗ FALTA {etiqueta}'); ok = False

    print('\n[B] Capítulos X (SAGRILAFT) y XIII (PTEE) — actos que los tocan')
    hits = [r for r in regs
            if re.search(r'cap[ií]tulos?\s+(x|xiii)\b', r.get('descripcion', ''), re.I)
            or 'sagrilaft' in _norm(r.get('descripcion', ''))]
    print(f'    {len(hits)} actos mencionan SAGRILAFT o los capítulos X/XIII')
    for r in hits[:5]:
        print(f'      · {r["fecha"]} {r["titulo"][:62]}')
        print(f'        {r["descripcion"][:120]}')
    if not hits:
        print('    ✗ ninguno — revisar el parser de descripción'); ok = False

    print('\n[C] El proyecto en consulta hasta el 08-abr-2026 (fila 1.6 del cliente)')
    proy = [r for r in regs if r['cola'] == 'proyectos' and r.get('plazo_fin') == '2026-04-08']
    if proy:
        r = proy[0]
        print(f'    ✓ {r["titulo"]}')
        print(f'      tipo={r["tipo_norma"]} · plazo {r["plazo_inicio"]} → {r["plazo_fin"]}')
        print(f'      {r["descripcion"][:150]}')
        print(f'      responsable={r["responsable"]} ({r["cargo_responsable"]}) · {r["dependencia"]}')
        print(f'      docs={len(r.get("docs", []))} → {(r.get("url") or "")[:95]}')
        print('      ⚠ el cliente lo llama "Proyecto de Circular Externa sobre SAGR";')
        print('        la fuente lo llama "Proyecto de nueva Circular Básica Jurídica".')
    else:
        print('    ✗ FALTA el proyecto con plazo hasta 2026-04-08'); ok = False

    print('\n[D] Proyectos con consulta abierta o reciente (los 5 más nuevos)')
    abiertos = sorted([r for r in regs if r['cola'] == 'proyectos' and r.get('plazo_fin')],
                      key=lambda r: r['plazo_fin'], reverse=True)[:5]
    for r in abiertos:
        print(f'    {r["plazo_inicio"]} → {r["plazo_fin"]}  {r["titulo"][:78]}')

    print('\n[E] Integridad')
    ids = [r['_id'] for r in regs]
    print(f'    _id únicos      {len(set(ids))} de {len(ids)}')
    print(f'    sin PDF         {sum(1 for r in regs if not r.get("url"))}')
    print(f'    sin fecha ISO   {sum(1 for r in regs if not r.get("fecha"))}')
    print(f'    sin descripción {sum(1 for r in regs if not r.get("descripcion"))}')
    fut = [r for r in regs if r.get('fecha') and r['fecha'] > time.strftime('%Y-%m-%d')]
    print(f'    fecha futura    {len(fut)}')
    if len(set(ids)) != len(ids):
        print('    ✗ hay _id repetidos'); ok = False

    print('\n[F] Dedup contra las otras fuentes del pilar (por URL y por título)')
    choques = 0
    for otro in ('sic-circulares.json', 'sic.json', 'supersalud-registro.json', 'dian-normas.json'):
        p = RAW / otro
        if not p.exists():
            continue
        try:
            od = json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue
        if isinstance(od, list):
            filas = od
        elif isinstance(od, dict):
            filas = od.get('registros') or od.get('rows') or od.get('data') or []
        else:
            filas = []
        if not isinstance(filas, list):
            filas = []
        urls = {x.get('url') for x in filas if isinstance(x, dict) and x.get('url')}
        tits = {_norm(x.get('titulo', '')) for x in filas if isinstance(x, dict)}
        c = sum(1 for r in regs if (r.get('url') and r['url'] in urls) or _norm(r['titulo']) in tits)
        print(f'    vs {otro:<28} {c} colisiones')
        choques += c
    if choques:
        print('    ✗ hay solape con otra fuente — revisar antes de consolidar'); ok = False

    print('\n' + ('PASA' if ok else 'FALLA'))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('cmd', choices=['probe', 'fetch', 'test'])
    ap.add_argument('--solo', choices=['normativa', 'proyectos'],
                    help='cosecha una sola cola (conserva la otra en disco)')
    ap.add_argument('--max-pages', type=int, default=MAX_PAGES)
    a = ap.parse_args()
    if a.cmd == 'probe':
        probe()
    elif a.cmd == 'fetch':
        fetch(solo=a.solo, max_pages=a.max_pages)
    else:
        sys.exit(test())


if __name__ == '__main__':
    main()
