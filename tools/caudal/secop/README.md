# Caudal · pilar "Datos abiertos y contratación" (SECOP)

Extractor del pilar de contratación pública de **Caudal**. Fuente: **SECOP II ·
Contratos Electrónicos** (`jbjy-vk9h` en datos.gov.co, Colombia Compra Eficiente),
**5,87 M contratos, actualizado A DIARIO**.

## Por qué este pilar NO es como los otros

Los demás pilares (Congreso, Regulatorio, Ejecutivo) cargan su dataset entero en
memoria de la Lambda y filtran ahí. **SECOP no cabe** (5,87 M filas). La
arquitectura, verificada jul-2026 contra el dataset real, se parte en dos:

| Necesidad | Cómo se resuelve | Latencia |
|---|---|---|
| **Landing / dashboards** (totales, por depto, por año, top entidades…) | **Agregados precomputados 1x/día** por este harvester → `secop-stats.json` en S3 | instantáneo (lee 27 KB) |
| **Búsqueda de contratos** ("dime los contratos de X entidad / con Y objeto") | **En vivo contra Socrata** (`$q` full-text, la Lambda proxynea) | ~1 s |

### La frontera real: `$q` (indexado) vs `like` (escaneo) — medido jul-2026

El límite **no** es "traer filas vs agregar". Es **qué operador filtra**. `$q` usa el
índice full-text de Socrata; `like` fuerza un escaneo de las 5,87 M filas:

| Query | Latencia | Veredicto |
|---|---|---|
| `count(1)` + `$q=transporte` | 3,0 s | ✅ se puede |
| `sum(valor)` + `$q=transporte` | 1,3 s | ✅ se puede |
| `group by departamento` + `$q=transporte` | 2,5 s | ✅ se puede |
| `count(1)` + `like` sobre `objeto_del_contrato` | **>65 s** | ❌ TIMEOUT |
| traer 50 filas con `like` | 2,6 s | ⚠️ ver nota |

> ⚠️ **Corrección medida al cablear la Lambda (jul-2026): `like` NO es usable en
> producción.** Los 2,6 s de arriba no se reproducen con una frase real: traer 10
> filas con `like '%COMANDO CONJUNTO CARIBE%'` tarda **31 s sin `$order`** y
> **>70 s con `$order=fecha_de_firma DESC`** (ordenar obliga a escanear todo antes
> de recortar). Las dos cifras superan el **techo de 30 s de API Gateway**, así que
> `like` queda fuera del camino de la Lambda. El toggle "solo en el objeto" se
> implementó en su lugar como **filtro post-`$q`**: se piden 4× filas por `$q`
> (indexado, ~1 s) y se filtra la frase en Python. Cuesta cobertura (solo filtra lo
> traído), no el conteo — el `total` del universo `$q` se conserva.

**Consecuencias para el diseño:**
1. **Sobre `$q` SÍ se puede agregar en vivo** → la búsqueda puede devolver el
   **total real de coincidencias** y hasta un **desglose por dimensión** de esa
   búsqueda (ver modo B del contrato). No hay que conformarse con "una página".
2. **`like` solo para traer filas, nunca para agregar.** Sirve cuando se quiere
   precisión sobre una columna concreta (p. ej. la frase exacta en el objeto),
   pero pierde el conteo.
3. Los agregados de `secop-stats.json` siguen siendo **dimensiones cerradas** sin
   texto: son el landing (sin búsqueda), y precomputarlos evita 11 queries por visita.

## FASE 1 — este directorio (solo datos)

`harvest_secop.py` corre ~11 queries de agregado (group-by, todas <60 s;
verificado: la más lenta, `por_anio` con `date_trunc_y`, ~44 s) y emite un único
`secop-stats.json`. **No hay lista slim en S3** (a diferencia de Regulatorio):
la búsqueda es en vivo, no hay nada que precargar en memoria.

```bash
python3 tools/caudal/secop/harvest_secop.py test        # 1 query chica, valida endpoint + app token
python3 tools/caudal/secop/harvest_secop.py fetch        # corre las ~11 queries de agregado
python3 tools/caudal/secop/harvest_secop.py fetch --force # re-baja aunque el raw ya sea de hoy
python3 tools/caudal/secop/harvest_secop.py build        # raw -> dist/s3/secop-stats.json
```

Salidas (gitignored, como todo dato de Caudal):
```
Bases de datos/leyes-senado/secop/
  raw/agg-{nombre}.json      crudo por agregado (resumible: los de HOY no se re-piden)
  dist/s3/secop-stats.json   agregados para el landing (el ÚNICO artefacto que va a S3)
```

**Deploy** (subir a S3; verificado en prod jul-2026):
```bash
aws s3 cp "Bases de datos/leyes-senado/secop/dist/s3/secop-stats.json" \
  "s3://caudal-legislativo/metadata/secop-stats.json" \
  --content-type "application/json" --cache-control "public, max-age=300"
```

**Refresh diario** (recomendado, ya que la fuente es diaria): un cron/launchd que
corra `fetch --force` → `build` → el `aws s3 cp` de arriba. La Lambda relee el JSON
en cold start (mismo patrón que el resto de metadata de Caudal); el `max-age=300`
del cache-control basta para que el landing se refresque sin invalidación manual.

### App token de datos.gov.co (recomendado)

`export SOCRATA_APP_TOKEN=...` antes de `fetch` → se manda como header
`X-App-Token` y sube el límite de rate (evita el throttling anónimo bajo carga).
Sin token también corre. **La misma variable debe existir en la Lambda** (ver
contrato abajo) para que la búsqueda en vivo no la throttle Socrata.

---

## FASE 2 — ✅ CABLEADA (jul-30-2026)

> **Ya implementada y en producción.** Acción `contratacion` en
> `tools/caudal/lambda/lambda_handler.py` (bloque "pilar Datos abiertos y
> contratación") + vista `view-contratacion` en `caudal.html`; la card
> "Datos abiertos y contratación" del home pasó a `status:'live'`. Lo que sigue es
> el contrato tal como quedó — **con 3 desvíos respecto de lo planeado**, todos
> documentados en su sitio:
> 1. **`like` fuera** (ver la corrección de la tabla arriba): "solo en el objeto"
>    es filtro post-`$q`, no `$where … like`.
> 2. **Orden por defecto `fecha_de_firma DESC`** ("lo más reciente"), no por valor
>    — y con `fecha_de_firma IS NOT NULL` **solo en las filas mostradas**: 421 k
>    contratos sin fecha encabezaban la lista con filas "No definido" y valor 0.
>    Los agregados NO llevan ese filtro, para que `total` siga siendo el universo real.
> 3. **`doc_proveedor` no se devuelve** (está en `columnas_pii_excluidas`; manda la
>    regla PII sobre el ejemplo de respuesta de más abajo).
>
> Sigue el patrón **aditivo** de los pilares existentes (`sanciones`, `ejecutivo`,
> `medios`): agregar la acción no tocó ninguna ruta existente.
>
> **Pendiente operativo:** la Lambda NO tiene `SOCRATA_APP_TOKEN` seteada — corre
> con el rate limit anónimo de Socrata. Bajo carga real conviene:
> `aws lambda update-function-configuration --function-name caudal-analiza --environment …`

### Acción Lambda `contratacion`

`POST` JSON al endpoint de `caudal-analiza`. Dos modos según venga `query`:

#### Modo A — landing (sin `query`)
```jsonc
// request
{ "action": "contratacion" }
```
Devuelve tal cual el `secop-stats.json` de S3 (`metadata/secop-stats.json`),
cacheado warm en el contenedor (mismo patrón que `_ejecutivo_stats()` /
`_sanciones()`). Rápido, no toca Socrata.
```jsonc
// response  (= contenido de secop-stats.json, forma abajo)
{ "v":"2026-07-28", "generado":"…Z", "fuente":{…}, "total":{…},
  "por_anio":[…], "por_departamento":[…], "por_estado":[…], "por_modalidad":[…],
  "por_tipo":[…], "por_orden":[…], "por_sector":[…],
  "top_entidades_valor":[…], "top_entidades_n":[…], "top_categorias":[…], "nota":"…" }
```

#### Modo B — búsqueda en vivo (con `query` y/o filtros)
```jsonc
// request
{ "action":"contratacion",
  "query":"interventoria vias",   // texto libre -> Socrata $q (opcional)
  "departamento":"Antioquia",     // filtro exacto opcional
  "anio":"2025",                  // filtro por año de fecha_de_firma (opcional)
  "estado":"En ejecución",        // filtro exacto opcional
  "modalidad":"Licitación pública",// filtro exacto opcional
  "limit":50 }                    // default 50, tope 200
```
La Lambda arma una URL Socrata y la trae (NO carga el dataset en memoria):
```
https://www.datos.gov.co/resource/jbjy-vk9h.json
  ?$q={query}                                   (si hay query)
  &$where=departamento='…' AND date_extract_y(fecha_de_firma)=2025 AND estado_contrato='…' AND modalidad_de_contratacion='…'
  &$select=id_contrato,nombre_entidad,nit_entidad,proveedor_adjudicado,documento_proveedor,
           objeto_del_contrato,valor_del_contrato,departamento,ciudad,estado_contrato,
           modalidad_de_contratacion,tipo_de_contrato,codigo_de_categoria_principal,
           fecha_de_firma,urlproceso
  &$order=valor_del_contrato desc
  &$limit={limit}
```
- Header `X-App-Token: <SOCRATA_APP_TOKEN env>` (misma var que el harvester).
- `$q` es el full-text indexado (rápido); `$where` con `=` sobre columnas
  indexadas también. **Nunca** combinar `sum()`/`count()` con `$q`/`like` (timeout).
- Escapar comillas simples de los valores de filtro (`'` → `''`) antes de armar
  el `$where`. `date_extract_y(fecha_de_firma)=<anio>` para el filtro de año.
- Cache S3 opcional `analisis-cache/contratacion-{hash24(query+filtros)}.json` con
  bucket de tiempo (como el pilar Medios) para no repegarle a Socrata en repetidas.
**Además de las filas, se puede pedir el resumen de la búsqueda** (2 queries extra
en paralelo, ~3 s c/u; ver la tabla de la frontera arriba):
```
&$select=count(1) as n,sum(valor_del_contrato) as v          -> total real de la búsqueda
&$select=departamento,count(1) as n&$group=departamento…      -> desglose de la búsqueda
```
Esto solo vale con `$q` (indexado). **Si el filtro usa `like`, omitir el resumen**
(timeout) y devolver `total:null` — el frontend debe tolerar el null.
```jsonc
// response
{ "contratos": [
    { "id_contrato":"CO1.PCCNTR.…", "entidad":"…", "nit":"…",
      "proveedor":"…", "doc_proveedor":"…", "objeto":"…",
      "valor": 8959088, "departamento":"…", "ciudad":"…",
      "estado":"…", "modalidad":"…", "tipo":"…", "categoria":"V1.80111701",
      "fecha":"2022-11-01", "url":"https://community.secop.gov.co/…" }
  ],
  "n": 50,                        // filas devueltas en esta página
  "total": { "contratos": 310423, "valor_cop": 193396109065818 },  // universo de la búsqueda (null si se usó like)
  "por_departamento": [ { "departamento":"Distrito Capital de Bogotá", "n":123704 }, … ], // opcional
  "query":"transporte", "filtros":{…},
  "fuente":{ "id":"jbjy-vk9h", "nombre":"SECOP II · Contratos Electrónicos", "portal":"…" } }
```

### ⚠️ `$q` matchea CUALQUIER columna — incluidas las que no se muestran

Verificado con `$q=transporte` (jul-2026). De los primeros 10 resultados:
- unos matchean por **objeto** ("…RECOLECCIÓN; TRANSPORTE Y APROVECHAMIENTO…"),
- otros por **nombre de entidad** (`MINISTERIO DE TRANSPORTE`),
- otros por **`sector`** = `Transporte` (INVIAS, Secretaría de Movilidad de Cali —
  su objeto no dice "transporte" por ningún lado),
- y al menos uno (`MUNICIPIO DE COGUA`, un box-culvert) por
  **`descripcion_documentos_tipo` = "Infraestructura de transporte"**, una columna
  que ni siquiera va en el `$select`.

**Al usuario esto se le lee como ruido** ("¿por qué me sale un puente si busqué
transporte?"). **FASE 1 deja las dos mitigaciones listas como DATOS** dentro de
`secop-stats.json` — el otro chat solo las consume, no tiene que investigar nada.
Ambas están probadas con `verify_busqueda.py` (ver abajo).

#### Mitigación 1 · chips de dimensión → `stats.chips`

**116 chips** derivados de las dimensiones cerradas (sin queries extra). Cada uno:
```jsonc
{ "dim":"por_sector", "campo":"sector", "etiqueta":"Sector",
  "valor":"Transporte", "norm":"transporte", "n":152543 }
```
**Uso:** normalizar lo que el usuario escribe (minúsculas sin tildes) y buscar
`norm` por substring. Si hay chip, ofrecerlo *antes* de mandar todo a `$q`:

> escribe `transporte` → **[Sector: Transporte · 152.543 contratos]** →
> al aceptarlo, filtro **exacto** `$where=sector='Transporte'` (1,6 s, cero ruido)

Casos verificados: `salud`→Sector Salud y Protección Social (855.218) ·
`antioquia`→Departamento (553.312) · `licitacion`→3 modalidades ·
`interventoria`→Tipo de contrato (12.936). `chips` viene ordenado por `n` desc.

#### Mitigación 2 · badge "matchea por" → `stats.columnas_match`

Lista **ordenada por prioridad de atribución** de las columnas que la Lambda debe
traer en el `$select` y probar. Algoritmo: normalizar término y celda; **la primera
columna de la lista que lo contenga, gana**; pintar su `etiqueta` como badge.

```
METROLINEA S.A            -> matchea por: Sector
MINISTERIO DE TRANSPORTE  -> matchea por: Objeto
MUNICIPIO DE COGUA        -> matchea por: Tipo de documentos   ← el box-culvert, explicado
```
Verificado: 10/10 resultados atribuidos con `transporte` y con `salud`. Si alguno
queda sin atribuir, es que `$q` matcheó una columna fuera de la lista (o PII) —
pintar el badge como opcional, nunca romper la fila.

#### 🔒 PII — `stats.columnas_pii_excluidas`

De las 82 columnas, varias son **datos personales**: `domicilio_representante_legal`
es la *dirección de residencia* del representante legal, y hay cédulas en
`documento_proveedor` / `identificaci_n_representante_legal`, más nombres de
supervisor y ordenador del gasto.

**`$q` las matchea igual** (buscar un nombre propio trae su domicilio), pero eso no
obliga a mostrarlas. Mismo criterio que `build_s3.py` de supers, que excluye cédulas
del slim. **Regla: no van en el `$select` de display ni en el probe de match_reason.**
La lista está en el JSON para que el otro chat no tenga que re-derivarla. Si en algún
momento se quiere búsqueda por proveedor persona natural, es una decisión de producto
y de habeas data (Ley 1581) — no un default.

#### 3 · Búsqueda precisa (opcional)
`like` sobre `objeto_del_contrato` como toggle "solo en el objeto" — recordando que
ahí **se pierde el conteo total** (ver la tabla de la frontera).

#### `$q` multi-palabra es **AND** (medido)
`transporte escolar` → 7.666, contra `transporte` 310.423 y `escolar` 56.680.
Agregar palabras **restringe**. Útil para afinar, pero el usuario que escribe de
más se queda sin resultados sin entender por qué — conviene avisar en la UI
("mostrando contratos que contienen *todas* las palabras").

#### Hueco de vocabulario (fase 2, **sin AI**)
El mismo problema que el pilar Congreso ya resolvió con el dict `SINONIMOS` de
`caudal_core.py` (ahí: el Congreso no titula "aborto", titula "derechos sexuales y
reproductivos"). En SECOP pasa igual — medido:

| término | contratos |
|---|---|
| `transporte escolar` | 7.666 |
| `ruta escolar` | 1.646 |
| `alimentacion escolar` | 4.980 |
| `PAE` (Programa de Alimentación Escolar) | 14.577 |

Quien busca *"alimentación escolar"* **no ve** los 14.577 que dicen `PAE`. La
solución es la misma que ya usa Caudal: un **diccionario curado** de tópicos
(`{k, terms}`) que expande la consulta a OR sobre el vocabulario del tópico.
**No requiere LLM** — y ser consistente con el pilar Congreso vale más que innovar.

#### Sesgo del orden
El `$select` de arriba ordena por `valor_del_contrato desc`: lo primero que se ve
son los contratos **más caros**, no los más relevantes al término (Socrata no da
relevance ranking sobre `$q`). Decidir el default de producto — `fecha_de_firma desc`
("lo más reciente") cambia bastante la lectura del pilar.

### Smoke test de la búsqueda

```bash
python3 tools/caudal/secop/verify_busqueda.py            # transporte
python3 tools/caudal/secop/verify_busqueda.py salud
```
Corre las dos mitigaciones contra Socrata en vivo e imprime los chips sugeridos +
el badge de cada resultado. **Es la referencia ejecutable del comportamiento que la
Lambda y la vista deben reproducir.**

Reglas duras (heredadas del pitch de Cauce): cada contrato cita su fuente
(`url` = `urlproceso.url` de SECOP) y **cero cifra inventada** — todo sale del dato.

### Vista `view-contratacion` (frontend `caudal.html`)

Cuarto/quinto pilar `live` del router `showView`. Espejo de `view-regulatorio` /
`view-ejecutivo` (reusa `.sanc`/`.kpis`/`.reg-sectors-grid`/`.doc-badge`, sin CSS
nuevo). Se entra por la card "Datos abiertos y contratación" del home (`PILLARS`).

- **Landing** (`action:contratacion` sin query): KPIs (contratos totales · valor
  COP total · nº entidades · actualización "Diaria") + tira por año + grid por
  depto/sector/modalidad + top entidades (por valor y por nº) + top categorías
  UNSPSC. Todo del `secop-stats.json`.
- **Búsqueda** (input + chips de ejemplo: "interventoría vías", "dotación
  hospitalaria", una entidad, una modalidad): dispara modo B → lista de contratos
  (entidad · proveedor · objeto · valor · depto · fecha · link a SECOP). Filtros
  opcionales (depto/año/estado/modalidad) como pills sobre la búsqueda.
- Al pintar valores COP: son crudos del dataset — SECOP trae **outliers de
  digitación** en `valor_del_contrato` (y un bucket "sin fecha" con valor
  astronómico); mostrar magnitudes con nota, no como cifra exacta auditada
  (lo dice el campo `nota` del stats).
- **Cruce con Vista Cliente / Radar (SIGA)**: natural v2 — un `_secop_para_sector`
  que corra el modo B con los `temas`/UNSPSC del sector y devuelva los contratos
  recientes relevantes, como ya hace `_medios_para_sector`. No es parte de FASE 1.

---

## Forma de `secop-stats.json` (lo que produce este harvester)

```jsonc
{
  "v": "2026-07-28",                       // día de generación (fecha)
  "generado": "2026-07-28T23:24:00+00:00", // timestamp ISO UTC
  "fuente": { "id":"jbjy-vk9h",
              "nombre":"SECOP II · Contratos Electrónicos",
              "portal":"datos.gov.co · Colombia Compra Eficiente",
              "url":"https://www.datos.gov.co/resource/jbjy-vk9h.json",
              "frecuencia":"Diaria" },
  "total": { "contratos": 5878648, "valor_cop": 2488304012819255 },
  "por_anio":          [ { "anio":"2026", "n":674067, "valor":73859116999886 }, … ],  // desc; incluye bucket "sin fecha"
  "por_departamento":  [ { "departamento":"Distrito Capital de Bogotá", "n":1985787, "valor":899092793938470 }, … ],
  "por_estado":        [ { "estado":"En ejecución", "n":1700305 }, … ],               // sin valor (solo conteo)
  "por_modalidad":     [ { "modalidad":"Contratación directa", "n":4477536, "valor":… }, … ],
  "por_tipo":          [ { "tipo":"Prestación de servicios", "n":…, "valor":… }, … ],
  "por_orden":         [ { "orden":"Territorial", "n":3792896, "valor":… }, … ],
  "por_sector":        [ { "sector":"Salud y Protección Social", "n":…, "valor":… }, … ],
  "top_entidades_valor":[ { "entidad":"…", "nit":"…", "n":…, "valor":… }, … ],         // top 50 por valor
  "top_entidades_n":    [ { "entidad":"…", "nit":"…", "n":…, "valor":… }, … ],         // top 50 por nº contratos
  "top_categorias":     [ { "codigo":"V1.80111600", "n":2094416, "valor":… }, … ],     // top 40 UNSPSC (mapear código→nombre en fase 2)
  "nota": "Agregados precomputados 1x/día. La búsqueda es en vivo…"
}
```

### Gotchas de datos (verificados jul-2026)
- **Valores COP crudos, con outliers.** El bucket `"sin fecha"` de `por_anio` trae
  un valor astronómico (~1,58 e15) por contratos con fecha nula + digitaciones
  erradas. `valor_del_contrato` no está depurado — es la cifra que publica SECOP.
  El campo `nota` lo dice; el frontend debe presentarlo como magnitud, no auditoría.
- **Precisión JS.** Los `valor` grandes (>2^53) pueden perder precisión al
  parsearse en el navegador; son magnitudes de display, no montos exactos. Python
  los escribe completos (enteros de precisión arbitraria).
- **`top_categorias` son códigos UNSPSC crudos** (`V1.80111600`). El mapeo
  código→nombre legible es de fase 2 (no hay tabla UNSPSC embebida todavía).
- **Cardinalidad OK.** El group-by de mayor riesgo (entidades, ~miles de grupos)
  responde ~9 s; todos los agregados quedan holgados bajo el timeout de 60 s.

## Cómo agregar un agregado nuevo
Una entrada al array `AGGREGATES` de `harvest_secop.py` (con `raw` = clave del
archivo y `soql` = querystring SoQL cruda, dimensión CERRADA nunca texto libre) +
armar su sección en `build()`. Correr `fetch` (baja solo el nuevo si los demás son
de hoy) → `build`. Antes de sumar uno de alta cardinalidad, medir su latencia (debe
quedar <60 s); si se acerca, acotarlo con `$limit` o `$where` de rango.

## ② Búsqueda por identificador · ③ el campo `adjudicado` (ago-2026)

Del caso **PAF-MENIES-O-134-2024**. El detalle completo, con las cifras medidas,
está en `CLAUDE.md` (sección del pilar). Resumen operativo:

- El pilar consulta **contratos** (`jbjy-vk9h`, 5,97 M). Los **procesos**
  (`p6dx-8zbt`, 9,02 M) son la otra mitad y hoy solo entran **por radicado**.
- ⚠️⚠️ Join proceso→contrato: **`id_del_portafolio` (`CO1.BDOS.*`) →
  `proceso_de_compra`**. NO `id_del_proceso` (`CO1.REQ.*`).
- ⚠️⚠️ `adjudicado` de `p6dx-8zbt` es basura en régimen especial (38% de los
  marcados «No» tienen contrato firmado; Findeter reporta 0 de 5.089). Se
  resuelve por cruce; sin cruce se dice **«la fuente no lo informa»**.
- ⚠️ `referencia_del_contrato` NO es única (`CPS-3548-2022` → 2 entidades).
- El noticeUID **no es full-text searchable**: se busca por igualdad sobre
  `urlproceso.url`, armando la URL canónica (contratos llevan
  `&isFromPublicArea=True&isModal=true&asPopupView=true`; procesos no).

Sondas por igualdad medidas (todas <1 s), útiles para depurar a mano:

```bash
curl -s -G "https://www.datos.gov.co/resource/p6dx-8zbt.json" \
  --data-urlencode "\$where=referencia_del_proceso='PAF-MENIES-O-134-2024'" \
  --data-urlencode '$limit=1' | python3 -m json.tool
```
