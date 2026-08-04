# Pilar SUCOP · el borrador antes de que sea norma

**SUCOP = Sistema Único de Consulta Pública** (`www.sucop.gov.co`, operado por el
**DNP**). Es donde las entidades publican sus **proyectos de norma** —decretos,
resoluciones, circulares— para comentarios del público **antes de expedirlos**, y
también sus **agendas regulatorias** anuales. Marco: **Decreto 1081 de 2015**
(art. 2.1.2.1.14) y **Decreto 1273 de 2020**.

Verificado ago-2026 contra la fuente, no supuesto: el sitio está **vivo** (se
cosecharon procesos creados el mismo día de la corrida) y trae **3.895 procesos**
desde **dic-2020**.

## Por qué este pilar es distinto

El pilar Ejecutivo trae 10.193 decretos **ya expedidos**: cuando aparecen ahí, la
pelea se perdió. SUCOP es el borrador **en la ventana de comentarios**, que es el
momento —y el único— en que un gremio puede incidir. Es la señal más temprana de
todo Caudal, más incluso que la radicación de un proyecto de ley.

Y trae un campo que **no existe en ningún otro pilar: la consulta VENCE**. Todo lo
demás en Caudal es histórico y no caduca; acá un borrador cuyo plazo cerró es
arqueología, y uno que cierra en cinco días es una alerta urgente.

## Qué vía resultó, y por qué se descartaron las otras

Se probaron las tres del método del pilar Regulatorio, en orden:

| Vía | Resultado | Detalle |
|---|---|---|
| **1 · Socrata (datos.gov.co)** | ✗ **No existe** | El catálogo devuelve **0** para `SUCOP`. Las variantes (`consulta publica normativa`, `proyectos normativos`) solo traen esquemas de publicación de alcaldías y registros de activos de información — nada del registro de consulta pública. |
| **2 · API interna del sitio** | ✓ **La que sirvió** | SUCOP es **SharePoint** y su `_api` REST responde **anónima** (mismo patrón que ya destapó el registro de Supersalud). |
| **3 · Scraping HTML** | – innecesario | — |

**Cómo se encontró la vía 2** (el rastro, por si hay que rehacerlo): el buscador
público `/Paginas/busqueda-beta.aspx` carga
`/Style Library/SUCOP-v2/js/busqueda/search-beta.js`, que usa JSOM contra
`SP.ClientContext('/formulacion_/')` → lista **`Procesos SUCOP`**. De ese archivo
salen el subsitio, la lista, los nombres exactos de los campos y —lo más valioso—
la **tabla oficial de traducción de estados** (`translateEstado()`), que se copió
tal cual para que Caudal diga lo mismo que la fuente.

## La estructura de la fuente (la parte que cuesta descubrir)

`Procesos SUCOP` es una **biblioteca de documentos** (BaseTemplate 101) con ~17.800
items = **~3.900 carpetas** (una por proceso, content types `0x0120D52000…`) +
~13.900 documentos **adentro** de esas carpetas. **Los procesos son las carpetas.**

Tres trampas, todas resueltas en el harvester:

- ⚠️ `/items` **sin `$select` explícito revienta** por el límite de columnas de
  búsqueda de SharePoint (`SPQueryThrottledException`).
- ⚠️ `/items?$filter=FSObjType eq 1` **revienta contra el list view threshold**
  (5.000) porque la columna no está indexada. `FileSystemObjectType` ni siquiera
  existe como columna filtrable.
- ⚠️ La vía que **sí** aguanta es `rootfolder/folders?$expand=ListItemAllFields`,
  que además devuelve las **taxonomías ya resueltas a texto** (`Decreto`,
  `Gobernación de Antioquia`). Por `/items` llegan como `WssId` numérico y habría
  que cruzar `TaxonomyHiddenList` a mano.
- ⚠️ `$expand` **no admite el campo `Agenda`** en `$select` (exige expandirlo
  aparte); se omite, no aporta.
- ⚠️ `$skip` no garantiza orden estable entre páginas → **se deduplica por `id`**
  al construir.

## El estado de la consulta es un campo del dato, no un cálculo del frontend

`estado_consulta` ∈ `abierta · cierra_pronto · cerrada · por_abrir · planeacion ·
cancelada · sin_fechas`. Se decide por la **fecha** (que es el hecho); el estado
que declara la fuente solo desempata cuando no hay fechas.

⚠️ **Es un estado con fecha de vencimiento.** Se calcula al construir y
`stats.json` lo declara en `calculado_a`. Quien quiera el estado de **hoy** debe
recalcularlo con `estado_consulta_de(ini, fin, estado, hoy)` — que es exactamente
lo que hace la Lambda en cada request. `fecha_inicio` y `fecha_fin` viajan crudas
para que eso siempre sea posible.

`cierra_pronto` = quedan ≤ 7 días. Es lo que permite que el motor de alertas diga
*"quedan 7 días para comentar"*, la señal más accionable que Caudal haya producido.

## Verificación (ago-2026, contra la fuente)

- **3.895 procesos** · rango **2020-12-11 → 2026-08-04** (el día de la corrida) ·
  3.714 proyectos de norma + 181 agendas regulatorias.
- **42 abiertos ahora**, de los cuales **25 cierran en ≤ 7 días** y 5 cerraban ese
  mismo día (MinJusticia, MinEducación, DIMAR, Gobernación de Boyacá, Duitama).
- **Concordancia perfecta del estado**: los 42 que la fuente declara `Activa` son
  exactamente los 42 que la lógica de fechas marca abiertos. **Cero discrepancias.**
- **`codigo` validado contra una lista independiente del sitio** (`Comentarios`, en
  el sitio raíz): **384/384 exacto**, 0 discrepancias, y `entidad` **384/384**. Los
  16 que no cruzaron son exactamente los de `Entidad Ejemplo` — los datos de prueba
  que el propio SUCOP esconde en su buscador y que el harvester filtra.

## Cruce con el diccionario de empresas — la cara de TEMA

El Estado regula **actividades**, no marcas: un borrador nunca dice «AngloGold»
pero sí «minería». Cada proceso se etiqueta con los tópicos del tesauro que toca
(`topicos`), y `empresas.topicos_de()` lleva de la marca del cliente a sus
borradores. Medido:

| Consulta | Vía texto libre | Vía diccionario (TEMA) |
|---|---|---|
| `anglogold` | 20 | **68** |
| `ecopetrol` | — | **84** |
| `rappi` | — | **66** |
| `bancolombia` | — | **21** (1 abierto) |
| `avianca` | — | **5** (1 abierto) |

⚠️ **Cobertura de tópicos declarada: 854 de 3.895 (21%).** El 79% restante son en
buena parte procesos territoriales (alcaldías, gobernaciones) con títulos genéricos
que el tesauro no toca; siguen siendo hallables por texto libre. Una fuente flaca
declarada es útil; una inflada quema al cliente.

## Uso

```bash
python3 tools/caudal/sucop/harvest_sucop.py test           # smoke test, no escribe
python3 tools/caudal/sucop/harvest_sucop.py fetch          # ~8 requests, ~100 s
python3 tools/caudal/sucop/harvest_sucop.py fetch --reuse  # resume una corrida rota
python3 tools/caudal/sucop/harvest_sucop.py build          # -> dist/ (JSONL + stats)

aws s3 cp "Bases de datos/leyes-senado/sucop/dist/sucop.jsonl" \
  "s3://caudal-legislativo/metadata/sucop.jsonl" \
  --content-type "application/json" --cache-control "no-cache"
aws s3 cp "Bases de datos/leyes-senado/sucop/dist/stats.json" \
  "s3://caudal-legislativo/metadata/sucop-stats.json" \
  --content-type "application/json" --cache-control "no-cache"
```

Salida local (gitignored): `Bases de datos/leyes-senado/sucop/{raw,dist}/`
— 5,6 MB de crudo, 4,8 MB de JSONL (667 KB gzip) y 70 KB de stats.

## Pendientes

- **Refresco diario**: el harvester es barato (~8 requests, ~100 s) y la fuente se
  mueve todos los días hábiles. Debe entrar a `tools/leyes-senado/run_diario.sh`
  como etapa propia (`sucop_fetch` → `sucop_build` → `aws s3 cp`), y al catálogo de
  `tools/caudal/salud/catalogo.py` en clase **`diario`** (26 h / 50 h). Sin eso, un
  `estado_consulta` viejo miente por definición.
- **Los documentos del proceso** (~13.900 dentro de las carpetas: borrador de
  articulado, memoria justificativa, AIN, respuesta a comentarios) quedan **on
  demand**, igual que las gacetas: hoy el pilar es el índice navegable con la
  ventana y el enlace oficial.
- **17 procesos** cargan un estado que la tabla oficial de SUCOP no traduce
  (`Ajustes de caracterización de norma` 9 · `Aprobación` 5 · `En ajustes` 3). Se
  conserva la etiqueta cruda de la fuente en `estado_fuente` en vez de inventar un
  mapeo.
