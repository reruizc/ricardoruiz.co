# Caudal · actos regulatorios de superintendencias (el "dapper interno")

> **Reencuadre jul-2026 — el pilar dejó de ser "sanciones" y pasó a "actos
> regulatorios".** El cliente quiere ver toda la actividad del Estado sobre su
> sector, no solo las multas: una apertura de investigación o una liquidación de
> contribución especial también son inteligencia. Cada registro lleva ahora
> **`tipo_acto`** ∈ `sancion · apertura_investigacion · archivo ·
> contribucion_especial · resolucion · circular · otro`.
>
> **La vista de sanciones no se diluyó:** el default de la acción `sanciones` de
> la Lambda y del frontend sigue siendo `tipo_acto='sancion'` (7.019 registros,
> idénticos a antes — regresión verificada). Lo demás entra con el toggle
> *"ver toda la actividad regulatoria"*, y el conteo de lo que quedó fuera se
> muestra explícitamente para no esconder el universo. La Vista Cliente (SIGA)
> sigue priorizando **solo sanciones** como señal, con los otros actos contados
> aparte en `kpis.n_otros_actos_sector`.

Extractor de actos de superintendencias y entidades reguladoras para
**Cauce**. Cumple una promesa que ya está escrita en el documento estratégico
(`Propuestas/Cauce-Estado-de-Cosas-Inteligencia-Legislativa.pdf`): las
superintendencias son una de las 9 categorías del "mapa inicial de fuentes"
(18 en "Superintendencias y comisiones"), y el ejemplo estrella del pitch —la
alerta de precisión para una empresa de salud— usa justamente una **circular de
la Supersalud** como una de las dos alertas que importan.

## Estado (piloto vía 1 · LISTO)

`harvest_supers.py` baja **6 fuentes vía Socrata** y las normaliza a un esquema
común de sanción. Verificado end-to-end (2026-07): **6.084 sanciones a nivel
entidad** consolidadas.

```bash
python3 tools/caudal/supers/harvest_supers.py list       # mapa de fuentes
python3 tools/caudal/supers/harvest_supers.py test       # valida mapeos (1 fila/fuente)
python3 tools/caudal/supers/harvest_supers.py fetch       # baja todas las vía 1
python3 tools/caudal/supers/harvest_supers.py fetch --desde 2024-01-01
python3 tools/caudal/supers/harvest_supers.py normalize   # raw -> dist (JSONL + CSV + stats)
```

Salidas (gitignored, como el resto de datos de Caudal):
```
Bases de datos/leyes-senado/supers/
  raw/{slug}.json        crudo por fuente (resumible)
  dist/sanciones.jsonl   consolidado, esquema común
  dist/sanciones.csv     idem (Excel, BOM utf-8)
  dist/stats.json        conteo por fuente
```

## Esquema normalizado

Todo acto, venga de donde venga, se mapea a estos campos (definidos en
`fuentes.json._schema_normalizado`):

`fuente · fuente_nombre · sector · sancionado · identificacion · **tipo_acto** ·
tipo_sancion · motivo · monto · resolucion · fecha_firmeza · estado ·
descripcion · url · _id · _raw`

**`tipo_acto`** es el filtro (qué CLASE de acto es); **`tipo_sancion`** es su
rótulo legible ("Multa", "Apertura de investigación", "Contribución especial").
Las fuentes cuyo dataset entero es de una sola clase lo declaran en
`tipo_acto_default` (todas las de sanciones lo tienen en `"sancion"`); solo
`supersalud-registro` lo trae **por fila**, porque su registro mezcla clases y
el tipo lo determina el modelo leyendo el PDF.

⚠️ **`sancionado` conserva el nombre por compatibilidad** (Lambda + frontend +
build lo usan), pero su semántica pasó a ser *"entidad destinataria del acto"*:
la sancionada, la investigada, o el contribuyente al que se le liquida.

`_raw` conserva la fila original (trazabilidad — cada alerta cita su fuente,
regla dura del pitch). `url` (jul-2026) apunta a la fuente oficial del acto o
comunicado cuando existe; el frontend lo pinta como link.

**Ojo semántica de las fuentes de comunicados** (supertransporte · sic ·
supersalud): el registro es el ANUNCIO oficial de la sanción, `fecha_firmeza`
trae la fecha del comunicado (no la firmeza del acto) y `motivo` es el titular
completo. Lo dice la nota de cada fuente en `fuentes.json`.

## Las tres vías de extracción

| Vía | Qué es | Dificultad | Ejemplos |
|---|---|---|---|
| **1 · Socrata** | dataset JSON directo en datos.gov.co | baja | INVIMA, SECOP I/II, Contraloría, Junta de Contadores |
| **2 · API interna** | endpoint no documentado del portal | media | Superfinanciera (SiriWeb), Supertransporte (WP), SIC (RSS) |
| **3 · Normograma/PDF** | resoluciones/circulares en PDF | alta | Supersalud, Supersociedades |

### Vía 1 — Socrata (implementada)
El patrón de `lab-indicadores` / ponderador. Query directa
`https://www.datos.gov.co/resource/{id}.json?$where=...`. Cero scraping. **Ojo:**
cuatro datasets de Min. Trabajo son **agregados** (por territorial/sector, solo
conteos) → `granularidad: agregado` en el registro, no entran al consolidado por
entidad (sirven de contexto).

### Vía 2 — API interna del portal
Mismo enfoque que la "API oculta" de `leyes.senado.gov.co`.

- **Superfinanciera — IMPLEMENTADA (`harvest_sfc.py`, jul-2026).** El buscador
  SiriWeb es una app Angular que habla con
  `.../api-siri-casillero/.../api/actoAdmin/listarSancionesMercadoValores`. La
  **api-key vive en texto plano en el bundle JS público** (`SiriWeb/main.js`,
  `const Qt = {...apiKey:"..."}`) — se re-extrae en cada corrida con regex
  (`harvest_sfc.py get_api_key()`), tolera rotación (falla claro si el bundle
  cambia de forma o si la key ya no sirve). **Header correcto: `api-key` o
  `Api-Key` — `apiKey`/`x-api-key` dan 401.** 805 sanciones, todas
  `estadoSancion:"En firme"`. Fechas en epoch-millis → ISO (`_epoch_to_iso`,
  descarta año fuera de [2000, hoy+1] en vez de adivinar — la fuente trae un
  typo real, año 3022). `numeroActoAdmin` llega como int → se fuerza a string
  antes de que `build_s3.py` le haga `.strip()`.
  ```bash
  python3 tools/caudal/supers/harvest_sfc.py test    # valida la key + 1 fila
  python3 tools/caudal/supers/harvest_sfc.py fetch   # -> raw/sfc-mercado-valores.json
  ```
  Endpoints hermanos sin implementar: `listaSancionesGeneral`, `listaReporteSanciones`
  (esperan otro payload).
- **Supertransporte / SIC / Supersalud — IMPLEMENTADAS (`harvest_comunicados.py`,
  jul-2026).** Las tres anuncian sanciones en comunicados oficiales con titulares
  muy estructurados; el harvester extrae sancionado/monto/tipo/estado **por regex
  del titular** (determinista, sin LLM; si el regex no saca el nombre, queda None
  y el titular completo va en `motivo`).
  - *Supertransporte*: WP REST paginado (BOM utf-8-sig). La página 9 con
    per_page=100 da **500 persistente** (post corrupto del lado del servidor) →
    esa ventana se rescata en sub-bloques de 10 vía `offset`.
  - *SIC*: el `rss.xml` NO sirve (radicados de abogacía de la competencia) y el
    filtro expuesto del view Drupal está roto → se paginan las ~180 páginas de
    `/noticias?page=N` (título en `<div class="titulo"><a>`, items con rutas
    `/noticias/` `/slider/` `/node/`) y la fecha se saca del detalle (dc:date)
    solo para los hits.
  - *Supersalud*: **la `_api` de SharePoint responde ANÓNIMA** (hallazgo
    jul-2026, misma clase que la api-key de la SFC). Sanciones = comunicados PDF
    en `docs.supersalud.gov.co/PortalWeb/Comunicaciones/Comunicados`, cazados
    con `/es-co/_api/search/query` + filtro `path:` (la búsqueda matchea el
    CUERPO del PDF; el corte fino es keyword sobre el título). El normograma
    (Avance Jurídico, HTML) solo trae normativa general — NO sanciones
    individuales; y la biblioteca "Procesos" del SharePoint son mapas Bizagi
    internos, no expedientes.
  ```bash
  python3 tools/caudal/supers/harvest_comunicados.py test    # parseo de titulares
  python3 tools/caudal/supers/harvest_comunicados.py fetch   # las 3 fuentes
  ```
- **ANLA · Gaceta Ambiental — IMPLEMENTADA (`harvest_anla.py`, ago-2026).**
  Motivación comercial directa: para una minera/petrolera la ANLA ES el
  regulador, y Caudal no tenía nada ambiental. El buscador público de la Gaceta
  (`gaceta.anla.gov.co:8443/Consultar-gaceta/consultar`) es un GET sin auth ni
  token que devuelve fragmentos HTML de a 20 (fijo — ignora `por_pagina`/
  `limit`): **el registro COMPLETO de actos administrativos de la ANLA**
  (~57.800: 28,3k autos · 28,5k resoluciones · 955 certificados · 118
  permisos), con descripción completa ("Por la cual se impone una sanción…
  Declara responsable a la empresa ANGLOGOLD ASHANTI COLOMBIA S.A…") y PDF de
  descarga directa (`descargar?q=ID`, sin postback).
  - Harvest **por slices de fecha de publicación** (pre-2016 + año a año):
    caché resumible por slice, y el refresco re-baja solo el año en curso
    (~185 páginas, 1-2 min). Dedup global por id. ~42 registros sin fecha de
    publicación no caen en ningún slice — hueco declarado.
  - `tipo_acto` POR FILA por regex sobre la descripción (whitelist dura, nunca
    inventa): sanción→`sancion` · inicio de sancionatorio/pliego→
    `apertura_investigacion` · archivo/cesación/exoneración/revocatoria→
    `archivo` · **medida preventiva→`otro`** (rótulo "Medida preventiva" — la
    whitelist no tiene ese valor y el frontend tiene chips fijos) ·
    RESOLUCIÓN/PERMISO restantes→`resolucion` (rótulo fino: licencia
    otorgada/negada/modificada · plan de manejo · permiso) · AUTO/CERTIFICADO
    restantes→`otro`.
  - `sancionado` = razón social extraída de la descripción (run de MAYÚSCULAS
    terminado en sufijo societario S.A./S.A.S./LTDA/LIMITED/LLC/E.S.P…).
    Conservadora: sin match queda null — la búsqueda funciona igual porque la
    descripción completa entra al blob `q`.
  - Título del acto con variantes reales: `1481 DEL 30 DE JULIO DE 2010` ·
    `NO. 003141 DEL 25 DE NOVIEMBRE DE 2025` · `003661 DEL 05 MAYO DE 2026`
    (sin el DE) → el regex de fecha los cubre los tres.
  - **Sector nuevo `ambiental`**: el chip del frontend queda para después; la
    búsqueda por texto y los stats lo sirven desde ya.
  - Descartadas como fuente primaria: **Socrata** (todo lo de ANLA son capas
    geográficas `federated_href`, sin registro de actos) y **RUIA/VITAL**
    (`ConsultarSancion.aspx`, ASP.NET WebForms con ViewState — cubre todas las
    autoridades ambientales pero es notoriamente incompleto; registrable como
    fuente aparte si algún día se quiere el universo de las CARs).
  ```bash
  python3 tools/caudal/supers/harvest_anla.py test     # 1 página + clasificación
  python3 tools/caudal/supers/harvest_anla.py fetch    # slices faltantes + año en curso
  python3 tools/caudal/supers/harvest_anla.py build    # caché -> raw/anla-gaceta.json
  ```
  - **Memo del cruce contra el diccionario de empresas** (`raw/anla-dict-memo.json`,
    gitignored). Cruzar los ~52k actos sin razón social contra las 500 empresas
    del diccionario son ~26 millones de regex: medido, **283s de los 369s** que
    tardaba `build`, todos los días, sobre documentos que ya no cambian. El
    resultado se memoiza por id de documento y `build` bajó a **~4s**
    (346s → 3,3s, verificado byte a byte contra un build en frío).
    La llave del memo es una **huella de lo que `casa_registro` realmente mira**
    (`entidad` y `excluir` de cada empresa, más los vetos locales `NO_DICT` y
    `VETO_CONTEXTO`): el diccionario es de otro frente y crece seguido
    (388 → 500 → 529 → 589 en un mes), así que un cambio real invalida el memo
    entero y se recalcula, mientras que una edición de docstring o de tópicos
    —que no puede cambiar un match— no cuesta nada. Cada entrada guarda además
    el hash del texto, por si la ANLA reescribiera un acto ya publicado.

### El pilar se refresca solo (ago-2026)

ANLA entró al **cron diario** (`tools/leyes-senado/run_diario.sh`, launchd 2x/día).
Etapas nuevas al final de la corrida: `anla_fetch` → `anla_build` →
`supers_consolida` → `supers_build_s3` → `supers_verifica` → `supers_upload_*`.
Medido end-to-end: **~76s** (46s de red contra la ANLA + 4s de build + 5s de
consolidación + 23s de subida), sobre una corrida de ~43 min con tope de 4 h.

⚠️ **`normalize` y `build_s3` consolidan las DOCE fuentes, no solo ANLA** — leen
todos los `raw/*.json` que haya en disco. Eso es lo correcto (el pilar es un solo
dataset y la Lambda lee un solo archivo), pero **`normalize` salta en silencio la
fuente cuyo raw falte**. Con el pilar regenerándose a mano eso era inofensivo
porque alguien miraba la salida; desatendido, un `raw/invima.json` borrado o a
medio escribir publicaría un `sanciones.jsonl` sin INVIMA y nadie se enteraría
hasta que un cliente buscara y no encontrara.

Por eso **nada se sube sin pasar `verificar_consolidado.py`**, que corre entre
`build_s3` y el `aws s3 cp`: integridad del JSONL, piso por fuente, pisos
globales y coherencia con los raw en disco. Si falla, la subida se omite y en S3
se queda el archivo bueno del día anterior — perder un refresco es barato,
publicar un pilar mutilado no.

```bash
python3 tools/caudal/supers/verificar_consolidado.py --verboso
```

Los pisos viven en el propio script (no en un archivo de estado): así están en
git, se revisan en un diff y sobreviven a un disco nuevo. Están al ~90% de lo
medido. **Probado borrando `raw/invima.json`**: el guardarraíl lo detecta y
devuelve rc=1 — y vale notar que el piso del TOTAL por sí solo no lo habría
atrapado (57.462 actos seguían por encima de 55.000); lo salvaron el piso por
fuente y el de sanciones. Si un piso hay que bajarlo, primero mirar el raw de esa
fuente y si `normalize` la listó.

### Vía 3 — PDF → DeepSeek

- **Supersalud registro — IMPLEMENTADA (`harvest_supersalud_registro.py`,
  jul-2026).** Reusa el pipeline de gacetas de Caudal fase 3: SharePoint Search
  enumera → PDF → pypdf → DeepSeek estructura el acto. Es el REGISTRO REAL,
  distinto de la fuente `supersalud` (sala de prensa, 16 sanciones publicitadas).
  ```bash
  python3 tools/caudal/supers/harvest_supersalud_registro.py enumerate   # manifest (771 candidatos)
  python3 tools/caudal/supers/harvest_supersalud_registro.py download    # PDF -> texto (resumible)
  export DEEPSEEK_API_KEY=$(aws lambda get-function-configuration \
    --function-name caudal-analiza \
    --query 'Environment.Variables.DEEPSEEK_API_KEY' --output text)
  python3 tools/caudal/supers/harvest_supersalud_registro.py extract [--limit N]
  ```
  **Gotchas medidos:**
  - **`max_tokens` 6000, no 2000.** V4 gasta el presupuesto en *reasoning* y con
    2000 devolvía `content` vacío con `finish_reason=length` en **7 de 20** docs
    (mismo gotcha que la síntesis de la Lambda). Aun con 6000 se trunca ~10% →
    `_extraer_doc()` reintenta con 12000 antes de darlo por perdido. Subir el
    techo no encarece: solo se cobran los tokens generados.
  - **`PROMPT_VERSION`**: la caché por doc guarda `_pv`; al cambiar
    `SNS_REG_SYSTEM` hay que subirla y las extracciones viejas se re-piden solas.
  - Los `Path` de SharePoint traen espacios/acentos literales → `quote(path,
    safe=':/%')` o el PDF llega en 0 bytes.
- **Supersociedades — DESCARTADA** (ver la nota de su entrada en `fuentes.json`).
  El bloqueo declarado ("landing Liferay dinámico") era falso: el AssetPublisher
  de `/web/supervision-societaria/avisos` es server-rendered y perfectamente
  scrapeable. El problema es otro y es definitivo: **su contenido no son
  sanciones** sino avisos de notificación de oficios de respuesta a derechos de
  petición (art. 69 CPACA), verificado leyendo los PDFs. Ni el portal, ni su
  buscador, ni Socrata publican un registro sancionatorio.

## Cómo agregar una fuente

**Vía 1 (Socrata):** una entrada en `fuentes.json.fuentes` con `via:1`,
`socrata_id`, `fecha_col` y el `map` (campo_normalizado → columna_del_dataset).
Descubrir el id y columnas:
```bash
curl -s "https://api.us.socrata.com/api/catalog/v1?domains=www.datos.gov.co&q=sanciones+<entidad>&limit=10"
curl -s "https://www.datos.gov.co/resource/<id>.json?\$limit=1"   # ver columnas
```
Corre `test` para validar el mapeo, luego `fetch <slug>` + `normalize`.

**Vía 2/3:** harvester hermano (`harvest_sfc.py`, `harvest_pdf.py`) que emite
`raw/{slug}.json` con la fila cruda; `normalize_all()` de este script lo
consolida si la fuente tiene `map` en el registro.

## Siguiente sprint (recomendado)

1. ✅ HECHO — `harvest_sfc.py` (Superfinanciera vía 2).
2. ✅ HECHO — `dist/sanciones.jsonl` enganchado a la Lambda (acción `sanciones`)
   y al Radar del cliente (acción `cliente`, sector `financiero` ahora con
   datos reales).
3. ✅ HECHO (jul-2026) — `harvest_comunicados.py`: Supersalud (SharePoint search
   anónima), Supertransporte (WP REST) y SIC (listado Drupal). El sector `salud`
   del Radar ahora trae las multas de Supersalud a EPS — el ejemplo del pitch
   con datos reales.
4. ✅ HECHO (jul-2026) — **reencuadre a actos regulatorios**: `tipo_acto` en el
   esquema, filtro en la Lambda con default `sancion` + toggle en el frontend,
   y `harvest_supersalud_registro.py` conservando TODOS los actos.
5. ❌ DESCARTADA — Supersociedades (no publica sanciones; ver arriba).
6. **Pendiente · OCR del registro de Supersalud.** `download` marca los PDFs
   escaneados (`len(txt) < 500`) y `extract` los salta. Reusar Tesseract como en
   `parse_dcnsw_camara.py`.
7. **Pendiente · extender el reencuadre a las demás supers**: hoy solo
   Supersalud aporta actos no-sancionatorios. SIC, Supertransporte y
   Superfinanciera publican circulares y resoluciones que caben en el mismo
   esquema con `tipo_acto` 'circular'/'resolucion'.

Ver el mapa completo de las 18+ fuentes y su estado en `fuentes.json`.
