# Caudal · lo que falta

Inventario de los pendientes que ya estaban escritos en los docs del proyecto,
reunidos en un solo lugar y **verificados contra el código de hoy** (sep-2026).
Cada fila dice dónde está la fuente, para que el detalle viva donde siempre
vivió y esto no se convierta en una segunda verdad que se desactualiza sola.

Regla al cerrar uno: se tacha acá **y** en su README, con fecha. Un pendiente
que el código ya resolvió pero el doc sigue anunciando es peor que no tenerlo
escrito — ver «Vencidos» al final.

Los números son **identificadores estables**: se citan en commits y en encargos,
así que uno nuevo se agrega al final de su sección con el siguiente número libre
y nunca se renumera el resto. Por eso no van en orden dentro de la tabla.

## Operación e infraestructura

| # | Pendiente | Fuente | Qué falta exactamente | Depende de |
|---|---|---|---|---|
| 1 | **Salir de la Mac → EC2** | `ec2/README.md` · `salud/PLAN-salir-del-mac.md` | Lanzar la instancia (rol `ec2-caudal-cron`, llave, SG, `t4g.small` · 50 GB). Después: `sync-estado.sh` (~8 GB), **Fase 0** piloto de WAF 3-4 días, **Fase 1** (Cámara, órdenes, SECOP, SUCOP, ANLA, dataset, gacetas), **Fase 2** (Senado, solo si el piloto pasa). **Ojo (17-sep-2026):** el piloto de WAF hay que medirlo con el harvester ya corregido — hasta ese día CADA corrida se provocaba su propio ban intentando bajar el PDF de 218 MB de 119/26 (76 corridas, 31-jul → 17-sep), y un piloto anterior habría medido ese ban, no el trato del WAF a la IP. Lo que sí es de la Mac y refuerza salir: en las últimas 45 corridas, **4 arrancaron sin red** (la lista llegó vacía al despertar: 23-ago, 24-ago, 11-sep, 12-sep) y **1 no corrió** (15-sep 08:00) | Ricardo, cuenta **admin**: `ricardo-mac-cli` no crea roles ni instancias |
| 2 | **Apagar los launchd de la Mac** de escucha de redes y brief | commit `92e1210` | Se apagan cuando quede **verificada** la primera corrida del workflow del repo privado `caudal-briefs` (escucha 05:30, brief lunes y jueves). Ojo: `run_escucha.sh` sin `APIFY_TOKEN` hace ensayo y sale rc 0, y `publicar_brief.py` no toca lo publicado si falla — un check verde y un botón que responde no prueban la corrida | Una corrida verificada, no solo verde |
| 3 | ~~**Publicar `estado.json` y alertar desde afuera**~~ · **cerrado 16-sep-2026** | `salud/PLAN-salir-del-mac.md` §5 | `run_diario.sh` sube `estado.json` a `metadata/` (privado) y un latido reducido al prefijo público, sin mirar el rc del chequeo; el cron trigger de `rr-auth` (cada hora, `caudalVigia`) avisa por correo a 26 h / 50 h o si la corrida terminó en error, y grita aunque no se publique nada. Probado en producción: llegaron los tres correos (sin latido · corrida con error · latido de 51 h). En `main` y con la Mac actualizada desde el 17-sep, así que publica desde la primera corrida de ese día | — |
| 4 | **`DEEPSEEK_API_KEY` en `caudal-analiza`** | `lambda/setup-lambda.md:21` | Sin la key los endpoints de datos responden pero la **lectura** (síntesis) no. Claude no toca llaves en texto plano | Ricardo · *no verificable desde el repo* |
| 5 | **`SOCRATA_APP_TOKEN` en `caudal-analiza`** | `secop/README.md:113` y `:415` · `lambda/lambda_handler.py:1425` | La Lambda consulta SECOP con el **rate limit anónimo** de Socrata; con token se sube el tope de consultas en paralelo | Ricardo · *no verificable desde el repo* |
| 6 | **Trigger EventBridge `leyes-en-vivo-3x`** | `../leyes-senado/DEPLOY-en-vivo.md` §4 | La Lambda `leyes-en-vivo` existe, corre y siembra S3; falta la regla 3×/día. Hoy se refresca a mano con `lambda invoke` | Identidad admin: `events:*` está bloqueado para `ricardo-mac-cli` (guardarraíl anti-escalada) |
| 7 | **El default `2026-2027` hardcodeado** | `salud/README.md` (final) · `importancia/evaluar.py:27` · `lambda/lambda_handler.py:355` | El 20-jul-2027 el chequeo va a reportar los `pl-radicados-*` como FALTANTES. Ese aviso es a propósito; mover el default, no | Nadie. Tiene fecha de vencimiento conocida |
| 18 | **Frescura POR DENTRO de `pl-radicados-*`** · *propuesto, sin implementar* | `salud/catalogo.py:80` · `../leyes-senado/build_diario_s3.py` | Del 15 al 17-sep `senado_radicados` murió 4 corridas seguidas sin escribir snapshot y la frescura dio 29/29: `senado_upload` re-sube el manifiesto viejo cada día y el catálogo solo le mira el `LastModified`. El manifiesto pesa 455 KB y es JSONL, así que no cabe en el mecanismo `campo_fecha` (tope 256 KB, JSON). Propuesta: que `build_diario_s3.py` suba al lado un `pl-radicados-{leg}.meta.json` (`visto_max` = el `_visto` más reciente, `n`, `n_sin_detalle`, `presentacion_max`) y el catálogo lo vigile con `campo_fecha='visto_max'`, clase `diario`. **`_visto` y no `fecha_de_presentacion`**: del 9 al 14-sep el Senado no publicó radicados y eso era legítimo; una alarma sobre la fecha de presentación sonaría en cada receso | Ricardo: cambia qué cuenta como «vivo» |
| 19 | **Bajar a mano el radicado de 119/26** (Sistema General de Participaciones · 218 MB) | `../leyes-senado/harvest_diario.py` (`MAX_PDF_MB`) | El harvester ya no lo intenta (no cabe en 180 s y cada intento era un ban). Es una reforma grande y hoy va sin texto en el manifiesto. Una sola vez, desde un navegador: guardarlo como `Bases de datos/leyes-senado/diario/2026-2027/textos/PL-119-26.pdf`; la corrida siguiente le saca el texto y `senado_upload` lo sube | Ricardo (o Claude con permiso explícito de descarga) |

## Fuentes por conectar o completar

| # | Pendiente | Fuente | Qué falta exactamente |
|---|---|---|---|
| 8 | **Consejo de Estado** | `control/README.md:64` | Está todo medido menos la **ApiKey** de `samaicore`: el endpoint es `POST /api/ProvidenciasTituladas`, `corporacion=1100103`, header `ApiKey` (probado contra los otros cuatro nombres). Próximo paso concreto: abrir el portal con navegador y capturar las peticiones a `samaicore`, como se consiguieron la key de la SFC y el authkey del GeoServer de Cúcuta |
| 9 | **Procuraduría** | `control/README.md` (final) | Fuera hasta validar una fuente con identificador y enlace público estable |
| 10 | **OCR del registro de Supersalud** | `supers/README.md:289` · `supers/harvest_supersalud_registro.py:243` | `download` marca los PDFs escaneados (`len(txt) < 500`) y `extract` los salta. Reusar Tesseract como en `actas/parse_dcnsw_camara.py` |
| 11 | **El registro real de sanciones de Supersalud** | `supers/fuentes.json` (nota de la fuente) | Hoy hay 16 sanciones individuales, y salen de la **sala de prensa**. El registro real (~600-800 resoluciones en Notificaciones/Por Aviso y Jurídica) tiene títulos opacos —números de resolución— así que exige leer el PDF: cosecha **vía 3**, el mismo pipeline de Supersociedades |
| 12 | **Extender el reencuadre regulatorio a las demás supers** | `supers/README.md:292` | Solo Supersalud aporta actos no-sancionatorios. SIC, Supertransporte y Superfinanciera publican circulares y resoluciones que caben en el mismo esquema con `tipo_acto` |
| 13 | **Doctrina y conceptos de la DIAN** | `supers/harvest_dian.py:66` y `:118` | Resoluciones y circulares ya entran; los **conceptos** viven en otro backend (`type=Doctrine`) y no están cosechados |
| 14 | **SUCOP · documentos y estados sin traducir** | `sucop/README.md:131` | Los ~13.900 documentos del proceso quedan **on demand**, igual que las gacetas (decisión, no bug). Y 17 procesos cargan un estado que la tabla oficial de SUCOP no traduce: se conserva la etiqueta cruda en `estado_fuente` en vez de inventar el mapeo |
| 17 | **Encender el pilar Redes** | `redes/harvest_redes.py` (docstring) · `redes/cuentas.json` | No es una cosecha huérfana: está **en pausa deliberada** desde ago-2026 — la fuente queda cableada y no se le paga a Apify hasta la salida al público. Los dos candados son a propósito: sin `APIFY_TOKEN` hace dry-run y sale rc=0, y la cadencia mensual vive en un plist que se instala aparte, fuera de `run_diario.sh`. Para encenderlo faltan dos cosas concretas: **curar `cuentas.json`** —hoy son las 12 cuentas de oficio (Presidencia, MinHacienda, MinSalud, Supersalud…), no las de los clientes activos; el propio archivo lo pide— e **instalar el disparador**, que hoy no existe ni en la Mac (el plist no está cargado) ni en `ec2/crontab`. Costo al encender: ~500 items al mes ≈ centavos de USD, con `MAX_POR_CUENTA=40` como techo duro que no se sube sin mirar la factura | Una decisión, no un arreglo: el disparador es la salida al público |

## Modelo y analítica

| # | Pendiente | Fuente | Qué falta exactamente |
|---|---|---|---|
| 15 | **`historial_reradicacion` al eje 1 + recalibrar** | `importancia/README.md:194` | La reradicación se muestra pero no entra al modelo, para no meterle una señal nueva a una calibración ya validada sin volver a medirla. Es «la mejora pendiente más clara» |
| 16 | **Los 34 «pendientes de leer el articulado»** | `importancia/reportes/legislatura-viva.md:42` | Van fuera del ranking a propósito: de esos solo se tiene el título, así que su impacto sería un piso y no una medida. Baja cuando se publique el texto, y el sesgo no es aleatorio — las reformas grandes llegan tarde |

## Vencidos (el doc lo pedía, el código ya lo hizo)

- **Cablear el frontend del acceso** — `acceso/README.md` anunciaba que `caudal.html`
  seguía con su lista `ALLOWED` hardcodeada. Ya no: `caudal-base.js:86` consulta
  `/caudal/acceso/me` y lo que queda es la lista `EMERGENCIA`, que solo entra si
  el worker **no** responde. Corregido en el README (sep-2026).
- **Refresco diario de SUCOP** — `sucop/README.md` lo pedía como pendiente. Ya está:
  etapas `sucop_fetch` / `sucop_build` / `sucop_upload_*` en `run_diario.sh:199-233`
  y las dos llaves en `salud/catalogo.py:99-107`, clase `diario` (26 h / 50 h).
  Corregido en el README (sep-2026).
