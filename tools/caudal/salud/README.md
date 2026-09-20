# `tools/caudal/salud/` — ¿está vivo Caudal?

Tres archivos, un objetivo: poder responder por el pipeline delante de alguien
que paga.

| archivo | qué hace |
|---|---|
| `catalogo.py` | **la parte opinable**: qué archivo tiene que estar fresco, con qué umbral y por qué; qué acciones de la Lambda tienen que responder y con qué forma |
| `check.py` | aplica el catálogo → escribe `Bases de datos/leyes-senado/diario/estado.json` |
| `etapa.py` | corre UNA etapa del cron con timeout y deja constancia (lo usa `run_diario.sh`) |
| `latido.py` | arma el **latido** público y reducido de `estado.json`, que `run_diario.sh` sube a S3 para el vigilante de afuera |
| `espera_red.py` | ¿esta máquina tiene red? Primera etapa de la corrida; espera hasta 4 min a que vuelva |
| `prueba_etapa.py` | pruebas de `etapa.py` (veredicto, reserva, tope al hijo) — no tocan la red |
| `prueba_espera_red.py` | pruebas de `espera_red.py` (curl y reloj sustituidos) |
| `PLAN-salir-del-mac.md` | evaluación y recomendación para dejar de depender del portátil |

## Uso

```bash
# el chequeo completo (frescura + Lambda) — escribe estado.json
python3 tools/caudal/salud/check.py

# sin pings a terceros (SECOP/Google News) ni lectura de fechas internas
python3 tools/caudal/salud/check.py --rapido

# solo una mitad
python3 tools/caudal/salud/check.py --solo s3
python3 tools/caudal/salud/check.py --solo lambda

# el JSON crudo, sin tocar disco
python3 tools/caudal/salud/check.py --json --sin-escribir
```

Códigos de salida, para no tener que parsear nada:
`0` ok · `1` aviso · `2` error · `3` el chequeo mismo se rompió.

`run_diario.sh` lo llama al final de cada corrida con `--etapas`, y así
`estado.json` queda con las tres capas: **qué corrió**, **qué tan fresco está el
dato** y **si la Lambda responde**.

## La primera etapa es preguntar si hay red

`launchd` dispara la corrida a las 8:00 mientras el Mac todavía está despertando,
y el wifi tarda en volver. Medido sobre 114 corridas del `cron.log`: **8 (7 %)
arrancaron sin red, y 6 de esas 8 son de la mañana**. La peor —11-sep— dejó 38
`Could not connect to the endpoint URL` y tumbó la corrida entera.

Lo malo no era perder la corrida, era **cómo se reportaba**: fuente por fuente,
como si el Estado colombiano se hubiera caído a la vez. `sucop_fetch` con
`curl rc=6`, `secop_upload` sin poder hablar con S3, los manifiestos sin subir.
Tres síntomas distintos para una sola causa que además se arregla sola en un par
de minutos.

Ahora `red_lista` va de primera y espera hasta **~4 min** (5, 10, 20, 30, 60, 60,
60 s). Si la red vuelve, la corrida sigue como si nada y en el log queda dicho
cuánto tardó. Si no vuelve, **se aborta antes de correr las 60 etapas
condenadas**: sin red ninguna puede funcionar, y sesenta fallos en fila no dicen
lo único cierto, que esta máquina está incomunicada.

Dos decisiones que conviene no deshacer:

- **Se consultan dos destinos** (S3 y un host neutro) y basta con que *uno*
  responda. Si S3 está caído pero el otro contesta, **hay red** y lo de S3 es
  asunto de las etapas que lo usan, no de este chequeo.
- **Sin red no se avisa por correo, y está bien.** Sin red tampoco se puede
  publicar el latido, así que no hay forma de gritar. El mecanismo que cubre esto
  ya existe: si la corrida siguiente también falla, el latido pasa de 26 h y el
  vigilante avisa por envejecimiento. Una corrida perdida de dos no es una
  emergencia; dos seguidas sí.

⚠️ Las esperas y el `--timeout 480` de la etapa están atados: el peor caso son
373 s (245 de espera + 128 de sondeos). Si se tocan las esperas hay que mover ese
timeout, y `prueba_espera_red.py` falla si dejan de cuadrar.

## Cuándo una etapa es «falla» y cuándo solo es «parcial»

`etapa.py` marca `ok` si el rc es 0 y `error` si no. Con una excepción: los
códigos que el cron declara en `--rc-aviso` se registran como **`warn`**, y eso
cambia dos cosas — `check.py` los pone en `avisaron` (no en `fallaron`) y el
vigilante de afuera **no manda correo**, porque solo mira `estado == "error"`.

Es para la degradación PREVISTA: un script que hizo su trabajo, quedó a medias y
lo dejó dicho. Hoy la usa una sola etapa:

```
etapa --nombre senado_radicados --rc-aviso 75 ...
```

El harvester del Senado sale con 75 cuando no alcanzó a refrescar todas las
fichas: conserva el dato anterior y pone las que faltaron de primeras en la
corrida siguiente, así que el ciclo se cierra igual. Si la parcial es GRAVE
—más de la mitad sin refrescar, o sea que dos corridas al día ya no alcanzan—
el propio harvester sale con 1 y entonces sí es falla y sí suena.

La regla para agregar otro `--rc-aviso`: el rc tiene que **elegirlo el script**
a sabiendas, y el script tiene que dejar el dato utilizable. Un rc que salga de
un traceback, de un `curl` o del timeout no califica (de hecho una etapa colgada
se registra como `error` aunque su 124 esté declarado).

⚠ Candidata pendiente: `sucop_fetch` sale con 1 cuando una página de las ~8
falla, aunque el resto sirva y el build siga adelante. Hoy manda correo por eso.

## Quién avisa si esto no corre

`check.py` corre en la misma máquina que el cron, así que no puede avisar de su
propia caída. Al final de cada corrida `run_diario.sh` publica `estado.json` al
bucket privado (`metadata/estado.json`) y el **latido** al prefijo público
(`congreso-2026/output/legislativo/caudal-latido.json`), sin mirar el rc del
chequeo. El cron trigger del worker `rr-auth` lo lee cada hora y escribe a
reruizc@gmail.com si pasa de 26 h / 50 h o si la corrida terminó en error; si el
latido desaparece sigue midiendo desde el último que vio. Detalle y por qué así:
`PLAN-salir-del-mac.md` §5.

Ninguno de los dos archivos está en `catalogo.py`, a propósito: el chequeo
vigilándose a sí mismo no detecta nada.

## Qué chequea, en concreto

**Frescura (24 archivos).** Cada uno con su umbral, no uno global: los cuatro que
refresca el cron avisan a las 26 h (ya se saltó una corrida) y dan error a las
50 h (se saltó un día); la normativa del Ejecutivo, cuya fuente publica una vez
al mes, avisa a los 45 días; el histórico 1990-2026 **no tiene umbral de edad** —
de ese solo se verifica que exista y no llegue truncado (`min_bytes`).

Donde el archivo trae una fecha por dentro (`secop-stats.generado`,
`en-vivo.actualizado`, `ritmo.v`) también se mira esa, porque un `aws s3 cp` de un
archivo viejo se ve fresco por `LastModified` y no lo es. Solo se baja el archivo
para eso si pesa menos de 256 KB.

**Lambda (12 acciones).** No basta con HTTP 200: se valida la **forma** de cada
respuesta. Un 200 con `{}` o con `{"error": ...}` adentro es el modo de falla
peligroso — el frontend lo pinta como "sin resultados" y nadie se entera.

Ningún ping cuesta dinero: `tema` va con `lectura:false` y `expandir_ia:false`,
y las acciones que llaman a DeepSeek (`contexto`, `gaceta`, `cliente` con lectura)
no se pinchan. Los dos pings que dependen de un tercero en vivo (SECOP vía
Socrata, medios vía Google News) van marcados `externa` y su falla es **aviso**,
no error: el pipeline nuestro puede estar impecable y el tercero caído.

## Al tocar el catálogo

- Si agregas un archivo a `metadata/`, agrégalo también a `catalogo.archivos()`
  con su clase. Lo que no está en el catálogo, no se vigila.
- **Un archivo que se re-sube en cada corrida no se puede juzgar por su
  `LastModified`.** Si es JSON chico, dale `campo_fecha`. Si es grande o JSONL
  (los `pl-radicados-*`), el builder sube al lado un **sello** `….meta.json` de
  <1 KB y se vigila ese (`tools/leyes-senado/meta_radicados.py`). El campo tiene
  que medir si NOSOTROS estamos mirando (`visto_max`), no si la fuente publica
  (`presentacion_max`): la fuente tiene silencios legítimos. Salió de que del 15
  al 17-sep-2026 el Senado murió 4 corridas seguidas con la frescura en 29/29.
- Los `min_bytes` son ~40-50% del tamaño real de ago-2026. Si un archivo crece
  mucho, súbelos; si un archivo legítimamente encoge, bájalos antes de que el
  chequeo grite.
- `legislatura_actual()` calcula el nombre de los `pl-radicados-*` con el corte
  del 20 de julio. Los harvesters todavía traen `2026-2027` hardcodeado como
  default: el 20-jul-2027 el chequeo va a reportar el archivo como FALTANTE, que
  es justo el aviso que hace falta para ir a mover ese default.
