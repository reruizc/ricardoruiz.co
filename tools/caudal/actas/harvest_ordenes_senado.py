#!/usr/bin/env python3
"""
Caudal · Fase 3 — harvester de ÓRDENES DEL DÍA del SENADO (agendamientos).

Fuente: DOCman (Joomla) — vista JSON global de documentos, sin auth ni JSF:
    GET https://www.senado.gov.co/index.php/documentos?format=json&view=documents
        &limit=100&offset=N
7.249 documentos (medido 2026-07-30). Cada uno trae `links.file.href` con
descarga DIRECTA (sin postback) y el breadcrumb de categoría — de ahí se
deriva el ÁMBITO (qué comisión) sin resolver categorías por separado.

Cobertura real medida (1.351 candidatos "orden del día" del total):
  buena:  Cuarta (256 docs, 2019-2026) · Quinta (~380, 2019-2026) ·
          Sexta (~355, 2018-2026, en 3 carpetas por período)
  parcial: Séptima (2019-2024) · Tercera (2019-2022) · Primera (2020-2023,
          verificado que su web no enlaza otra fuente)
  casi nula: Segunda (1 doc)
  Plenaria: NO está en ESTE DOCman (senado.gov.co) — solo ~55 docs sueltos
          2018-2022 bajo 'senado-prensa'. PERO SÍ EXISTE, en el sitio HERMANO
          (ver abajo): secretariasenado.gov.co, 833 documentos, vigente.
Este harvester corre por defecto sobre 'buenas'; las 'debiles' se pueden
correr igual con 'todas' (dan lo que dan, sin inventar cobertura que no hay).

Formato del documento: ~70% .docx / ~30% .pdf. Los .docx se leen con
`zipfile` puro (stdlib): texto nativo, sin OCR. Los .pdf en su mayoría son
digitales, PERO un puñado son ESCANEADOS ("PaperStream Capture" en los
metadatos del PDF) — 0 texto extraíble. Medido por muestreo: ~12% en Cuarta,
0% en Quinta/Sexta (muestra chica, no exhaustivo). Se detectan por longitud
de texto (<50 chars) y se cuentan aparte (`n_escaneado`); NO se OCRea en este
pase — mismo backlog que las Gacetas pre-2006 y las actas DCN-SW de Cámara.

Diferencias clave frente a harvest_ordenes.py (Cámara), todas ya resueltas:
  - El proyecto se cita "Proyecto de Ley No. NNN de AAAA Senado." — el mismo
    PROJ_BLOCK_RE de Cámara YA lo cubre (admite "Senado" al final); se REUSA
    por import, no se duplica. cut_anuncio/ANUNCIO_RE/GACETA_REF_RE ídem.
  - El token de cruce es NÚMERO DE SENADO (`numero_senado` en
    proyectos.jsonl), NO `numero_camara` → load_numero_senado_map() y
    load_gaceta_map_senado() son nuevas (mismo patrón, otro campo).
  - Fecha de sesión: el título casi siempre la trae en texto plano ("ORDEN
    DEL DIA 05 DE DICIEMBRE DE 2023" / "Orden del Día martes 10 de
    septiembre de 2019") y el cuerpo también ("Día: martes 05 de diciembre
    de 2023"). PERO a diferencia de Cámara (que a veces reusa un título con
    año viejo CERCA de la fecha de publicación — bug que el filtro ±14 días
    de harvest_ordenes.fecha_sesion() ataja), el Senado hace BACKFILL
    LEGÍTIMO: medido en Sexta, sesiones de 2019 publicadas hasta un año
    después. Un filtro relativo a pub_date rechazaría estas fechas BUENAS.
    Por eso aquí NO se usa el filtro relativo: se valida solo que la fecha
    caiga en un rango absoluto sano [2018-01-01, hoy].
  - Algunos hrefs del listado bulk son un LINK ROTO propio de DOCman: la
    ficha individual del documento (?format=json sin /file) da el MISMO
    href incorrecto — no es problema de caché de la vista bulk, es que el
    SEF-router de esa categoría quedó desincronizado de `storage_path`
    (verificado 1 caso real en Sexta). Probadas bases alternativas de
    almacenamiento directo (`/images/documentos/`, `/media/docman/`,
    `/component/docman/?task=doc_download`) — todas 404, no hay atajo. Se
    trata igual que cualquier 404: la respuesta llega como HTML → se cuenta
    (`n_link_roto`) y se salta, sin intentar reconstruir la URL.

════════════════════════════════════════════════════════════════════════════
PLENARIA del Senado — está en secretariasenado.gov.co (SITIO HERMANO)
════════════════════════════════════════════════════════════════════════════
Hallazgo jul-2026, tras dar la plenaria por perdida en este DOCman. El enlace
sale de la home de senado.gov.co: `secretariasenado.gov.co/index.php/
orden-del-dia-senado`. Es OTRO Joomla+DOCman, con la misma API JSON:
    GET http://www.secretariasenado.gov.co/index.php/orden-del-dia-senado
        ?format=json&limit=20&offset=N
`meta.total` = 833 documentos, el más reciente del 2026-07-29 (vigente, no
un archivo muerto). Los documentos vienen en `linked.documents`, mismo shape
que el DOCman de senado.gov.co (title/publish_date/storage_path/links.file).

⚠️ DOS GOTCHAS de este servidor (medidos, no teóricos):
  1. IGNORA el parámetro `limit`: pidas lo que pidas devuelve 20 por página.
     Paginar de a 100 (como en senado.gov.co) hace que se pierda el 78% de
     los documentos SILENCIOSAMENTE — el loop sigue avanzando el offset de
     a 100 pero solo cosecha 20 de cada 100. El paso DEBE ser 20.
  2. Es LENTO e intermitente (timeouts esporádicos que devuelven cuerpo
     vacío → JSONDecodeError). Requiere reintentos con backoff; un solo
     intento por página aborta la corrida a mitad.
Este sitio es el mismo que ya conocíamos por el árbol DOCman de documentos de
trámite (ver docstring de harvest_actas_plenaria_senado.py) — pero esa
exploración anterior miró las carpetas de trámite por proyecto, no esta
sección de órdenes del día, y por eso no apareció entonces.

════════════════════════════════════════════════════════════════════════════
LAS 4 COMISIONES DÉBILES vía GACETA — MEDIDO Y DESCARTADO (jul-2026)
════════════════════════════════════════════════════════════════════════════
Para Primera/Segunda/Tercera/Séptima (cuya cobertura DOCman se corta entre
2022 y 2024) se evaluó reconstruir los agendamientos desde las ACTAS de la
Gaceta del Congreso, que sí transcriben el orden del día leído en sesión
("El Secretario: Por instrucciones del Presidente, da lectura al orden del
día: I Llamado a lista… II… III…" — verificado en Gaceta 847/2026).

**No es viable en la práctica.** Tres mediciones sobre gacetas reales:
  1. REZAGO DE PUBLICACIÓN de 11 a 16 meses: Gaceta 847/2026 publicada el
     2026-07-17 transcribe la sesión del 2025-08-06 (11,4 meses); Gaceta
     186/2026 publicada el 2026-03-20 transcribe una del 2024-11-06 (499
     días). O sea: la legislatura EN CURSO no existe en la Gaceta, que es
     justo donde el índice de bloqueo tiene valor para un cliente.
  2. LAS ACTAS SON MINORÍA y no se pueden aislar por filtro: de 6 gacetas
     de Senado tomadas al azar en 2026, 5 NO eran actas (ponencias/otros).
     El filtro "Documento" del portal JSF es fuzzy e inservible (ya
     documentado en harvest_actas_plenaria_senado.py) → habría que bajar y
     clasificar por masthead cientos de PDFs.
  3. COSTO POR DOCUMENTO ALTO: esas 6 gacetas pesaron ~35 MB en total, una
     sola de 27,4 MB. Un barrido exhaustivo es de gigas.
Conclusión: el orden del día de esas 4 comisiones queda como HUECO DECLARADO,
no como dato a inventar. Si algún día hace falta, la vía razonable es
TARGETED (un proyecto concreto → su comisión y fechas → las pocas gacetas de
esa ventana), no un barrido masivo.

⚠️ Ojo con el spam SEO: secretariasenado.gov.co tiene contenido basura
inyectado en menú/footer (vulnerabilidad Joomla clásica, ya documentada).
No es nuestro problema, pero al scrapear HTML de ese sitio hay que ignorar
esos enlaces. La API JSON de DOCman no los trae, así que por esta vía no
afecta.

Uso:
  python3 tools/caudal/actas/harvest_ordenes_senado.py cuarta --limit 40
  python3 tools/caudal/actas/harvest_ordenes_senado.py cuarta
  python3 tools/caudal/actas/harvest_ordenes_senado.py buenas        # cuarta+quinta+sexta
  python3 tools/caudal/actas/harvest_ordenes_senado.py plenaria --workers 6   # ← la cola de 2º debate
  python3 tools/caudal/actas/harvest_ordenes_senado.py todas         # + las débiles + plenaria
  python3 tools/caudal/actas/harvest_ordenes_senado.py buenas --offline    # re-parseo sin red
  python3 tools/caudal/actas/harvest_ordenes_senado.py --refrescar-indice # re-baja el índice DOCman
                                                                          # completo (7.249 docs, ~75 requests)
Es incremental y resumible: PDFs/DOCX/TXT se cachean por id de documento; el
índice DOCman se cachea aparte y solo se refresca con --refrescar-indice.

Salida: Bases de datos/leyes-senado/actas/ordenes-senado/agendamientos-{ambito}.json
(mismo shape que el de Cámara — ver analiza_bloqueo.py --dir ordenes-senado).
Vive en subcarpeta APARTE a propósito: build_bloqueo_s3.py hace
`CACHE.glob('agendamientos-*.json')` NO recursivo sobre 'actas/', así que
estos archivos quedan invisibles para el pipeline de Cámara hasta que se
diseñe a propósito el merge (Paso D pendiente: los tokens 'NNN/YY' de Senado
pueden coincidir numéricamente con los de Cámara — son proyectos DISTINTOS,
nunca deben compartir el mismo `por_proyecto` sin distinguir cámara).
"""
import json, re, sys, time, zipfile, html, datetime
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harvest_ordenes import (  # noqa: E402
    REPO, SRC, DIST, PROJ_RE, GACETA_REF_RE, ANUNCIO_RE,
    cut_anuncio, extract_text as extract_text_pdf, norm, curl, MESES,
)

DOCMAN_URL = 'https://www.senado.gov.co/index.php/documentos'
# La PLENARIA vive en el sitio HERMANO, con su propio DOCman (ver docstring).
PLENARIA_URL = 'http://www.secretariasenado.gov.co/index.php/orden-del-dia-senado'
PLENARIA_PAGE = 20    # este servidor IGNORA `limit`: siempre pagina de a 20
BASE = SRC / 'actas' / 'ordenes-senado'
IDX_CACHE = BASE / 'docman-index.json'
IDX_CACHE_PLEN = BASE / 'docman-index-plenaria.json'

BUENAS = ['cuarta', 'quinta', 'sexta']
DEBILES = ['primera', 'segunda', 'tercera', 'septima']
PLENARIA = 'plenaria'
AMBITOS = {a: f'comision-{a}' for a in BUENAS + DEBILES}

# La carpeta de plenaria MEZCLA órdenes del día con comunicados de prensa,
# cronogramas y avisos de cambio de hora (191 de 833 son comunicados). Se
# filtra por EXCLUSIÓN, no por inclusión: los títulos vienen con erratas de
# tipeo frecuentes ("OREN DEL DÍA", "ODEN DEL DÍA", "COMNUNICADO") y un filtro
# positivo por "orden del dia" perdería ~8 órdenes reales mal escritas. Se
# descarta lo que claramente NO es agenda y se deja que el parser decida el
# resto (un documento sin proyectos simplemente no aporta agendamientos).
PLEN_EXCLUIR_RE = re.compile(
    r'com[un]*nicado|cronograma|correcci[oó]n|cambio de hora|elecci[oó]n\s+', re.I)

ORDEN_RE = re.compile(r'orden(es)?[- ]del[- ]dia')
FECHA_LARGA_RE = re.compile(r'(\d{1,2})\s+de\s+(' + '|'.join(MESES) + r')\s+de\s+(20\d{2})', re.I)

# Citación de proyecto: NO se reusa harvest_ordenes.PROJ_BLOCK_RE (pensado para
# Cámara, siempre asume que el PRIMER número citado es "el bueno"). Aquí eso es
# falso ~22% de las veces: Comisión Cuarta corre muchas sesiones CONJUNTAS con
# Cámara, y el orden de los dos números (Cámara/Senado) varía por sesión —
# medido: "No. 073/24 Senado" (solo Senado), "No. 259/24 Senado- 399/24 Cámara"
# (Senado primero), pero también "Nº 594 2021 CÁMARA - 439 DE 2021 SENADO" y
# "No. 550 de 2026 Cámara, 369 de 2026 Senado" (¡Cámara PRIMERO!). Asumir
# "grupo 1 = Senado" mal-atribuiría un número de CÁMARA como si fuera de Senado
# en esos casos — peor que perderlo. Por eso el diseño es en 2 pasos:
#   1) CITA_RE aísla el bloque completo "Proyecto de Ley/AL ... hasta la
#      comilla de apertura del título" (header) + el título mismo.
#   2) NUM_LABELED_RE busca DENTRO del header TODOS los pares (número, año,
#      cámara) sin asumir orden, y se toma el que esté explícitamente
#      etiquetado "Senado" — el que NO lo esté (soltero o solo "Cámara") se
#      descarta en vez de adivinar.
# Cubre ambos estilos de año: "087 de 2023" (verboso) y "311/25" (corto, el
# mismo formato de numero_senado). Límites conocidos y ACEPTADOS (no vale la
# pena perseguirlos, son ruido de PDF, no de lógica):
#   - números con el separador "/" o la palabra "de" comidos por la extracción
#     del PDF ("311125" en vez de "311/25", "594 2021" sin "de") → no matchea,
#     se pierde ESE agendamiento puntual (el proyecto igual se captura en las
#     sesiones donde el PDF sí extrae bien).
#   - títulos sin comilla de apertura en absoluto, solo un apodo entre
#     comillas más adelante (ej. Planes Nacionales de Desarrollo: el nombre
#     largo va sin comillas, solo el apodo "…POTENCIA MUNDIAL DE LA VIDA” sí
#     las lleva) → el header y el título capturados corresponden al apodo, no
#     al nombre completo. El NÚMERO (lo que importa para el conteo de
#     bloqueo) sigue siendo correcto; solo el título mostrado queda corto.
CITA_RE = re.compile(
    r'Proyecto\s+de\s+(?:Ley|Acto Legislativo)(?:\s+Org[aá]nica)?'
    r'(?P<header>[^"“”]{1,160})'
    r'["“”](?P<titulo>.+?)(?:["”]|(?=\n\s*(?:•|Ponencia|Autores|Coordinadores|Ponentes|Presidente\s*:))|\Z)',
    re.I | re.S)
NUM_LABELED_RE = re.compile(
    r'(\d{1,4})\s*(?:de\s*(?:20)?\s?\d?\s?(\d{2})|/\s*(\d{2}))\s*(C[aá]mara|Senado)', re.I)


def resolver_num_senado(header):
    """Del header de una cita, el (número, año-2díg) etiquetado 'Senado'
    explícitamente — None si no hay ninguno así etiquetado (p.ej. cita
    solo-Cámara sin equivalente Senado dado, o números sin 'de'/'/' que el
    regex no pudo aislar)."""
    for m in NUM_LABELED_RE.finditer(header):
        if m.group(4).lower() == 'senado':
            return m.group(1), (m.group(2) or m.group(3))
    return None


def norm_txt(s):
    import unicodedata
    s = unicodedata.normalize('NFD', s or '')
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').lower()


def es_error_html(fn):
    """Detecta la página 404 de DOCman guardada con extensión .pdf/.docx.

    BUG encontrado jul-31: el cuerpo HTTP a veces trae un byte de más (un
    '\\n' suelto) ANTES de '<!doctype html>' — el check ingenuo
    `head[:1] == b'<'` no lo ve, así que ~174 documentos (168 en Sexta, 6 en
    Cuarta, medido) quedaban mal contados como `n_escaneado` (pypdf tira
    'Stream has ended unexpectedly' sobre el HTML, texto <50 chars) cuando en
    realidad son 404 GENUINOS de DOCman, ya documentados como irrecuperables
    (ver docstring del módulo: probadas rutas alternativas, todas 404). No
    hay nada que OCRear ahí — un 404 no tiene imagen. Este check mira los
    primeros 300 bytes buscando '<!doctype html' o '<html' en cualquier
    posición, no solo en el byte 0."""
    try:
        head = fn.read_bytes()[:300].lower()
    except Exception:
        return False
    return b'<!doctype html' in head or b'<html' in head


def es_candidato(doc):
    return bool(ORDEN_RE.search(norm_txt(doc.get('category_slug')) + ' ' + norm_txt(doc.get('title'))))


def ambito_de(doc):
    """Deriva el ámbito (qué comisión) del breadcrumb en links.file.href.
    Exige 'comisiones'+'constitucionales' en el path para excluir el espejo
    'camara-de-representantes/comision-X-constitucional' que este mismo
    DOCman también aloja (documentos de la OTRA cámara, no del Senado)."""
    href = ((doc.get('links') or {}).get('file') or {}).get('href', '') or ''
    segs = [s for s in href.split('/index.php/documentos/')[-1].split('/') if s]
    if 'comisiones' not in segs or 'constitucionales' not in segs:
        return None
    for name, slug in AMBITOS.items():
        if slug in segs:   # membresía exacta de segmento, no substring
            return name
    return None


def fetch_plenaria_docman(force=False, incremental=False):
    """Índice de órdenes del día de PLENARIA (secretariasenado.gov.co).
    Dos cuidados propios de ese servidor: pagina SIEMPRE de a 20 (ignora
    `limit`, y avanzar de a 100 pierde el 78% en silencio) y es lento e
    intermitente (timeouts que devuelven cuerpo vacío) → reintentos.

    `incremental=True` (el modo del cron diario): este listado viene ESTRICTO
    de más nuevo a más viejo (verificado: 832 de 832 pares en orden DESC), así
    que basta pedir páginas hasta topar con una donde ya conocíamos todos los
    ids y fusionar lo nuevo al caché. Sin esto, el caché haría que la corrida
    diaria nunca viera una sesión nueva; con esto son 1-2 páginas en vez de 42
    contra un servidor lento."""
    previo = json.load(open(IDX_CACHE_PLEN, encoding='utf-8')) if IDX_CACHE_PLEN.exists() else []
    if previo and not force and not incremental:
        return previo
    if incremental and previo:
        conocidos = {d.get('id') for d in previo}
        print('· actualizando índice de PLENARIA (incremental, más nuevo primero)…')
        nuevos, off = [], 0
        while True:
            d = None
            for intento in range(3):
                raw = curl(f'{PLENARIA_URL}?format=json&limit={PLENARIA_PAGE}&offset={off}')
                try:
                    d = json.loads(raw)
                    break
                except Exception:
                    time.sleep(2 * (intento + 1))
            if d is None:
                print(f'  ! sin respuesta en offset {off}; me quedo con lo que haya')
                break
            lk = (d.get('linked') or {}).get('documents') or []
            if not lk:
                break
            frescos = [x for x in lk if x.get('id') not in conocidos]
            nuevos += frescos
            if len(frescos) < len(lk):      # la página ya trae conocidos → alcanzamos lo viejo
                break
            off += PLENARIA_PAGE
            time.sleep(0.4)
        if nuevos:
            docs = nuevos + previo
            json.dump(docs, open(IDX_CACHE_PLEN, 'w', encoding='utf-8'), ensure_ascii=False)
            print(f'  + {len(nuevos)} órdenes del día nuevas (total {len(docs)})')
            return docs
        print('  sin novedades')
        return previo
    print('· descargando índice DOCman de PLENARIA (paginado de a 20)…')
    docs, off = [], 0
    while True:
        d = None
        for intento in range(4):
            raw = curl(f'{PLENARIA_URL}?format=json&limit={PLENARIA_PAGE}&offset={off}')
            try:
                d = json.loads(raw)
                break
            except Exception:
                time.sleep(2 * (intento + 1))
        if d is None:
            print(f'  ! sin respuesta en offset {off} tras 4 intentos; corto acá')
            break
        lk = (d.get('linked') or {}).get('documents') or []
        total = (d.get('meta') or {}).get('total')
        docs += lk
        print(f'  offset {off} -> +{len(lk)} (acum {len(docs)}/{total})')
        off += PLENARIA_PAGE
        if not lk or off >= (total or 0):
            break
        time.sleep(0.4)
    BASE.mkdir(parents=True, exist_ok=True)
    json.dump(docs, open(IDX_CACHE_PLEN, 'w', encoding='utf-8'), ensure_ascii=False)
    return docs


def fetch_all_docman(force=False):
    if IDX_CACHE.exists() and not force:
        return json.load(open(IDX_CACHE, encoding='utf-8'))
    print('· descargando índice DOCman completo (paginado)…')
    docs, off = [], 0
    while True:
        raw = curl(f'{DOCMAN_URL}?format=json&view=documents&limit=100&offset={off}')
        try:
            d = json.loads(raw)
        except Exception:
            break
        ents = d.get('entities') or []
        total = (d.get('meta') or {}).get('total')
        docs += ents
        print(f'  offset {off} -> +{len(ents)} (acum {len(docs)}/{total})')
        off += 100
        if not ents or off >= (total or 0):
            break
        time.sleep(0.25)
    BASE.mkdir(parents=True, exist_ok=True)
    json.dump(docs, open(IDX_CACHE, 'w', encoding='utf-8'), ensure_ascii=False)
    return docs


def prefetch(cand, outdir, workers):
    """Descarga en PARALELO los archivos que falten, antes del parseo.

    El parseo sigue siendo secuencial (barato: es CPU local); lo caro es la
    red — secretariasenado.gov.co tarda ~30s por PDF, así que en serie los
    ~635 órdenes del día de plenaria son ~6 horas y en paralelo bajan a ~1.
    Solo baja lo que no está en disco, así que es idempotente y resumible:
    matar y relanzar no re-descarga nada. NO extrae texto ni parsea — de eso
    se encarga el loop principal leyendo del caché."""
    from concurrent.futures import ThreadPoolExecutor
    faltan = []
    for doc in cand:
        ext = (doc.get('storage_path') or '').rsplit('.', 1)[-1].lower()
        if ext not in ('docx', 'pdf'):
            continue
        href = ((doc.get('links') or {}).get('file') or {}).get('href')
        if not href:
            continue
        fn = outdir / f"{doc['id']}.{ext}"
        tf = outdir / f"{doc['id']}.txt"
        if tf.exists() or (fn.exists() and fn.stat().st_size >= 300):
            continue
        faltan.append((href, fn))
    if not faltan:
        return 0
    print(f'  ↓ descargando {len(faltan)} archivos con {workers} obreros…')
    hecho = [0]

    def bajar(par):
        href, fn = par
        curl(href, str(fn))
        hecho[0] += 1
        if hecho[0] % 25 == 0:
            print(f'    …{hecho[0]}/{len(faltan)}')

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(bajar, faltan))
    return len(faltan)


def extract_text_docx(path):
    try:
        z = zipfile.ZipFile(path)
        xml = z.read('word/document.xml').decode('utf-8', 'replace')
    except Exception as e:
        return f'[docx-err {str(e)[:40]}]'
    xml = re.sub(r'</w:p>', '\n', xml)
    txt = html.unescape(re.sub(r'<[^>]+>', '', xml))
    return re.sub(r'[ \t]+', ' ', txt)


def fecha_de_texto(texto):
    if not texto:
        return None
    m = FECHA_LARGA_RE.search(texto)
    if not m:
        return None
    d_, mo_, y_ = int(m.group(1)), MESES.get(m.group(2).lower()), m.group(3)
    if mo_ and 1 <= d_ <= 31:
        return f'{y_}-{mo_:02d}-{d_:02d}'
    return None


def fecha_de_titulo_flex(titulo, pub):
    """Fecha desde el TÍTULO con formato laxo — necesario para plenaria, cuyos
    títulos omiten preposiciones de forma inconsistente: "22 DE JULIO 2026"
    (sin el 2º 'de'), "16 SEPTIEMBRE 2025" (sin ninguno) y hasta "20 MARZO"
    (¡sin año!). Solo se aplica al título, NO al cuerpo: en el cuerpo un
    patrón tan laxo levantaría fechas de leyes citadas ("Ley 1508 de 2012").
    Si falta el año se toma el de la publicación (la agenda se publica pocos
    días antes; el riesgo real es solo el cruce de fin de año, que se acota
    exigiendo que la fecha no quede a más de 60 días de la publicación)."""
    if not titulo:
        return None
    t = re.sub(r'<[^>]+>', ' ', titulo)
    m = re.search(r'(\d{1,2})\s+(?:de\s+)?(' + '|'.join(MESES) + r')(?:\s+de)?\s*(20\d{2})?', t, re.I)
    if not m:
        return None
    d_, mo_, y_ = int(m.group(1)), MESES.get(m.group(2).lower()), m.group(3)
    if not mo_ or not (1 <= d_ <= 31):
        return None
    if y_:
        return f'{y_}-{mo_:02d}-{d_:02d}'
    if not pub:
        return None
    try:
        pd = datetime.date.fromisoformat(pub)
    except ValueError:
        return None
    for y_try in (pd.year, pd.year + 1, pd.year - 1):   # cubre el cruce de año
        try:
            cand = datetime.date(y_try, mo_, d_)
        except ValueError:
            continue
        if abs((cand - pd).days) <= 60:
            return cand.isoformat()
    return None


def fecha_sesion_senado(titulo, texto, pub, titulo_flex=False):
    """Fecha de la SESIÓN. A diferencia de Cámara, NO se valida contra una
    ventana relativa a pub_date (ver docstring del módulo: el Senado hace
    backfill legítimo meses/un año después). Solo se exige que la fecha
    parseada caiga en un rango absoluto sano [2018-01-01, hoy]."""
    cand = fecha_de_texto(re.sub(r'<[^>]+>', ' ', titulo or ''))
    if cand is None and titulo_flex:
        cand = fecha_de_titulo_flex(titulo, pub)
    if cand is None:
        cand = fecha_de_texto(texto or '')
    if cand:
        try:
            fd = datetime.date.fromisoformat(cand)
        except ValueError:
            return pub, False
        if datetime.date(2018, 1, 1) <= fd <= datetime.date.today():
            return cand, True
    return pub, False


def load_numero_senado_map():
    """token 'NNN/YY' (número de Senado) → registro del dataset."""
    p = DIST / 'proyectos.jsonl'
    if not p.exists():
        return {}
    mp = {}
    for line in open(p, encoding='utf-8'):
        r = json.loads(line)
        ns = (r.get('numero_senado') or '').strip()
        m = PROJ_RE.search(ns)
        if m:
            mp[norm(m.group(1), m.group(2))] = r
    return mp


def load_gaceta_map_senado():
    """gaceta 'NNNN/AAAA' → (tok 'NNN/YY' número Senado, título)."""
    p = DIST / 'proyectos.jsonl'
    if not p.exists():
        return {}
    mp = {}
    for line in open(p, encoding='utf-8'):
        r = json.loads(line)
        ns = (r.get('numero_senado') or '').strip()
        m = PROJ_RE.search(ns)
        if not m:
            continue
        tok = norm(m.group(1), m.group(2))
        for g in r.get('gacetas', []):
            gk = g.get('gaceta')
            if gk and gk not in mp:
                mp[gk] = (tok, r.get('titulo', ''))
    return mp


_GMAP = None
_NMAP = None


def gaceta_map_cached():
    global _GMAP
    if _GMAP is None:
        _GMAP = load_gaceta_map_senado()
    return _GMAP


def num_map_cached():
    global _NMAP
    if _NMAP is None:
        _NMAP = load_numero_senado_map()
    return _NMAP


def run(ambito, limit=None, offline=False, workers=1):
    es_plen = ambito == PLENARIA
    outdir = BASE / ambito
    outdir.mkdir(parents=True, exist_ok=True)

    rot = 'PLENARIA' if es_plen else f'Comisión {ambito.title()}'
    print(f'· órdenes del día de {rot} (Senado){" · offline" if offline else ""}…')
    n_comunicado = 0
    if es_plen:
        docs = fetch_plenaria_docman()
        cand = [d for d in docs if not PLEN_EXCLUIR_RE.search(d.get('title') or '')]
        n_comunicado = len(docs) - len(cand)
    else:
        docs = fetch_all_docman()
        cand = [d for d in docs if es_candidato(d) and ambito_de(d) == ambito]
    if limit:
        cand = cand[:limit]
    print(f'  {len(cand)} documentos candidatos'
          + (f' ({n_comunicado} comunicados/avisos descartados)' if es_plen else ''))
    gaceta_map = gaceta_map_cached()
    if workers > 1 and not offline:
        prefetch(cand, outdir, workers)

    agend = defaultdict(list)
    titulos = {}
    n_nuevos, n_ok, n_fs, n_link_roto, n_escaneado, n_otro_formato = 0, 0, 0, 0, 0, 0
    n_ocr_ok, n_ocr_sin_match = 0, 0

    for i, doc in enumerate(cand):
        ext = (doc.get('storage_path') or '').rsplit('.', 1)[-1].lower()
        if ext not in ('docx', 'pdf'):
            n_otro_formato += 1
            continue
        href = ((doc.get('links') or {}).get('file') or {}).get('href')
        if not href:
            continue
        pub = (doc.get('publish_date') or '')[:10]
        fn = outdir / f"{doc['id']}.{ext}"
        tf = outdir / f"{doc['id']}.txt"
        of = outdir / f"{doc['id']}.ocr.txt"
        if tf.exists():
            txt = tf.read_text(encoding='utf-8')
            # re-validación (self-heal): texto corto cacheado ANTES del fix de
            # es_error_html() podía ser en realidad un 404 mal contado como
            # 'escaneado' — se corrige sin red, releyendo el archivo ya en disco.
            if 0 < len(txt.strip()) < 50 and fn.exists() and es_error_html(fn):
                txt = ''
                tf.write_text('', encoding='utf-8')
        elif offline:
            continue
        else:
            if not fn.exists() or fn.stat().st_size < 300:
                curl(href, str(fn))
                n_nuevos += 1
            if fn.exists() and es_error_html(fn):   # 404/redirect (o link roto de DOCman)
                n_link_roto += 1
                tf.write_text('', encoding='utf-8')
                continue
            txt = extract_text_docx(str(fn)) if ext == 'docx' else extract_text_pdf(str(fn))
            tf.write_text(txt, encoding='utf-8')
        fuente_txt = 'nativo'
        if len(txt.strip()) < 50:
            # .txt vacío = el archivo nunca llegó (link roto de DOCman, se cacheó
            # como ''); .txt corto pero no vacío = PDF genuinamente escaneado sin
            # capa de texto nativa (ya descartado que sea un 404 mal detectado,
            # arriba). Antes de descartarlo, ver si ya hay OCR cacheado
            # (ocr_ordenes_senado.py lo deja en {id}.ocr.txt) y usarlo.
            if txt == '':
                n_link_roto += 1
                continue
            if of.exists():
                ocr_txt = of.read_text(encoding='utf-8')
                if len(ocr_txt.strip()) >= 50:
                    txt = ocr_txt
                    fuente_txt = 'ocr'
                    n_ocr_ok += 1
                else:
                    n_escaneado += 1
                    continue
            else:
                n_escaneado += 1
                continue
        fecha, es_sesion = fecha_sesion_senado(doc.get('title'), txt, pub, titulo_flex=es_plen)
        n_fs += es_sesion

        # cut_anuncio() usa el PROJ_BLOCK_RE/GACETA_REF_RE de Cámara (importados)
        # SOLO para anclar dónde empieza el contenido real y no cortar de más;
        # no matchean el formato corto NNN/YY, pero eso es inocuo: verificado
        # (jul-2026) que ningún documento de Cuarta con sección ANUNCIO pierde
        # citas por esto — los que tienen ANUNCIO siempre traen además alguna
        # cita verbosa que ancla bien. Revisar de nuevo si aparece en Quinta/Sexta.
        body = cut_anuncio(txt)
        orden, seen = [], set()
        es_ocr = fuente_txt == 'ocr'
        for m in CITA_RE.finditer(body):
            hit = resolver_num_senado(m.group('header'))
            if not hit:
                continue
            num, anio2 = hit
            if int(num) == 0:   # "Proyecto de Ley No. 0 de …" no existe: artefacto de extracción
                continue
            tok = norm(num, anio2)
            # texto OCR: el dígito puede venir garabateado por el escáner. En vez
            # de confiar en la cita tal cual (como con texto nativo), se exige que
            # el número resuelto EXISTA en el dataset (proyectos.jsonl) — si no,
            # se descarta en vez de contaminar el conteo con un número inventado
            # por el OCR. Esto es justo lo que se valida al hacer QA de la
            # cobertura ("98-100% de los números casan con proyectos reales"),
            # aquí convertido en filtro duro para lo recuperado por OCR.
            if es_ocr and tok not in num_map_cached():
                n_ocr_sin_match += 1
                continue
            t = re.sub(r'\s+', ' ', m.group('titulo')).strip(' "“”«»')
            if 12 <= len(t) <= 180 and tok not in titulos:
                titulos[tok] = t
            if tok not in seen:
                seen.add(tok); orden.append(tok)
        for m in GACETA_REF_RE.finditer(body):
            gk = f'{int(m.group(1))}/{m.group(2)}'
            hit = gaceta_map.get(gk)
            if not hit:
                continue
            tok, tit = hit
            if tit and tok not in titulos:
                titulos[tok] = tit
            if tok not in seen:
                seen.add(tok); orden.append(tok)
        if orden:
            n_ok += 1
        n_dia = len(orden)
        # confianza del OCR (solo se marca cuando fuente_txt=='ocr'; ver docstring
        # del módulo/CLAUDE.md, mismo criterio de 3 niveles que parse_dcnsw_camara.py):
        # 'alta' si además la fecha de sesión se leyó del documento (es_sesion),
        # 'media' si la fecha cayó al fallback de publicación. Los 'baja' (número
        # sin match en el dataset) YA fueron descartados arriba — nunca llegan a
        # `orden`, así que nunca entran a los agregados.
        conf_ocr = ('alta' if es_sesion else 'media') if es_ocr else None
        for pos, tok in enumerate(orden, 1):
            ev = {'fecha': fecha, 'pos': pos, 'n_dia': n_dia, 'fuente': fuente_txt}
            if conf_ocr:
                ev['confianza'] = conf_ocr
            agend[tok].append(ev)
        if (i + 1) % 50 == 0:
            print(f'  …{i + 1}/{len(cand)}')

    # Relleno de títulos desde el propio dataset: ~40% de los agendamientos no
    # traen título usable en el PDF (el orden del día a veces solo cita el
    # número, o el título va sin comillas y solo el apodo entre comillas — ej.
    # "Ana Cecilia Niño"). Como ya tenemos numero_senado→titulo en
    # proyectos.jsonl, se completa de ahí en vez de dejar la fila en blanco en
    # la UI. Solo rellena lo que falta; NO pisa el título leído del documento.
    nmap = num_map_cached()
    n_titulo_dataset = 0
    for tok in agend:
        if not (titulos.get(tok) or '').strip():
            r = nmap.get(tok)
            t = (r.get('titulo') or '').strip() if r else ''
            if t:
                titulos[tok] = t
                n_titulo_dataset += 1

    index = {}
    for tok, evs in agend.items():
        por_fecha = {}
        for e in evs:
            prev = por_fecha.get(e['fecha'])
            if prev is None or e['pos'] < prev['pos']:
                por_fecha[e['fecha']] = e
        evs = sorted(por_fecha.values(), key=lambda e: e['fecha'])
        fuentes = [e.get('fuente', 'nativo') for e in evs]
        index[tok] = {
            'titulo': titulos.get(tok, ''), 'n': len(evs),
            'primera': evs[0]['fecha'], 'ultima': evs[-1]['fecha'],
            'fechas': [e['fecha'] for e in evs],
            'posiciones': [e['pos'] for e in evs],
            'fuentes': fuentes,
            'n_ocr': sum(1 for f in fuentes if f == 'ocr'),
        }
    rows = sorted(index.items(), key=lambda kv: -kv[1]['n'])

    out = {'comision': ambito, 'camara': 'senado',
           'ambito': PLENARIA if es_plen else 'comision',
           'fuente': PLENARIA_URL if es_plen else DOCMAN_URL,
           'n_sesiones': len(cand), 'n_sesiones_con_proyectos': n_ok,
           'n_con_fecha_sesion': n_fs, 'n_link_roto': n_link_roto,
           'n_escaneado': n_escaneado, 'n_otro_formato': n_otro_formato,
           'n_comunicado_descartado': n_comunicado,
           'n_titulo_desde_dataset': n_titulo_dataset,
           'n_ocr_ok': n_ocr_ok, 'n_ocr_sin_match': n_ocr_sin_match,
           'n_proyectos_agendados': len(index), 'agendamientos': index}
    outf = BASE / f'agendamientos-{ambito}.json'
    json.dump(out, open(outf, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    print(f'\n  {n_nuevos} descargas nuevas · {n_ok} sesiones con proyectos · '
          f'{len(index)} proyectos distintos · {len(titulos)} con título')
    print(f'  n_link_roto={n_link_roto} · n_escaneado={n_escaneado} · n_otro_formato={n_otro_formato} '
          f'· n_con_fecha_sesion={n_fs} · n_ocr_ok={n_ocr_ok} · n_ocr_sin_match={n_ocr_sin_match}')
    print(f'  → {outf.relative_to(REPO)}')
    print('\n  Proyectos más AGENDADOS (nº veces en orden del día):')
    for tok, info in rows[:15]:
        print(f'  {info["n"]:>3}×  [{info["primera"]}→{info["ultima"]}]  {tok:>8}  {info["titulo"][:52]}')


if __name__ == '__main__':
    if '--refrescar-indice' in sys.argv:      # completo (primera vez / reparación)
        fetch_all_docman(force=True)
        fetch_plenaria_docman(force=True)
        sys.argv.remove('--refrescar-indice')
        if len(sys.argv) == 1:
            sys.exit(0)
    if '--actualizar-indice' in sys.argv:     # el del cron: barato e incremental
        # comisiones: el listado NO viene ordenado por fecha (los documentos
        # nuevos no quedan al principio), así que no hay parada temprana posible
        # y se re-baja entero — son ~73 páginas rápidas contra senado.gov.co.
        fetch_all_docman(force=True)
        # plenaria: sí viene DESC → solo las páginas nuevas.
        fetch_plenaria_docman(incremental=True)
        sys.argv.remove('--actualizar-indice')
        if len(sys.argv) == 1:
            sys.exit(0)
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None
    workers = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 1
    offline = '--offline' in sys.argv
    arg = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else 'buenas'
    if arg == 'todas':
        ambitos = BUENAS + DEBILES + [PLENARIA]
    elif arg == 'buenas':
        ambitos = BUENAS
    else:
        ambitos = [arg]
    validos = set(AMBITOS) | {PLENARIA}
    desconocidos = [a for a in ambitos if a not in validos]
    if desconocidos:
        sys.exit(f'ámbito desconocido: {", ".join(desconocidos)}\n'
                 f'válidos: {", ".join(sorted(validos))} · buenas · todas')
    for a in ambitos:
        run(a, limit, offline=offline, workers=workers)
