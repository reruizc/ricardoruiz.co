# Caudal · Alertas

El motor que convierte Caudal de **pull** a **push**.

Hasta ahora Caudal era una plataforma a la que había que entrar a preguntar. El
pitch de Cauce promete lo contrario: *"llega una alerta de precisión sobre una
circular de Supersalud"*. Esto es esa pieza.

Corre después del rastreo diario, compara el estado de hoy contra el de ayer
sobre las fuentes ya publicadas, clasifica lo nuevo por sector y nivel, y manda
un digest por sector — **solo si hay algo que decir**.

---

## Cómo se corre

```bash
python3 tools/caudal/alertas/motor.py                    # corrida normal de hoy
python3 tools/caudal/alertas/motor.py --dry-run          # calcula y escribe, no envía ni guarda estado
python3 tools/caudal/alertas/motor.py --fecha 2026-07-29 # reproducir un día concreto
python3 tools/caudal/alertas/motor.py --sin-api          # sin prensa ni contratación (offline)
python3 tools/caudal/alertas/motor.py --sectores salud,trabajo
python3 tools/caudal/alertas/motor.py --baseline         # sella el estado sin enviar nada
python3 tools/caudal/alertas/motor.py --estado           # qué sabe el motor hasta ahora
```

**La primera corrida es siempre baseline y no manda nada.** Sin estado previo
las 18.526 llaves del universo (7.019 actos regulatorios + 11.500 normas)
contarían como "nuevo" y el primer correo llegaría con dieciocho mil items. El
motor lo detecta solo, sella el estado y avisa.

---

## Las cinco fuentes

Ninguna es nueva: todas estaban ya publicadas y nadie las estaba mirando junto.
**Contra `leyes.senado.gov.co` no se hace ni una petición** (hay WAF y ese host
es del rastreo diario).

| Pilar | De dónde sale | Cómo se detecta lo nuevo |
|---|---|---|
| Congreso | `diario/novedades/*.json` y `diario-camara/novedades/*.json` | el rastreo ya calculó el diff; acá solo se lee |
| Regulatorio | `s3://caudal-legislativo/metadata/sanciones.jsonl` | llave de contenido contra el estado |
| Ejecutivo | `s3://caudal-legislativo/metadata/normativa.jsonl` | ídem |
| Contratación | acción `cliente` de la Lambda (SOLO LECTURA) | ídem |
| Prensa | acción `medios` de la Lambda (SOLO LECTURA) | ídem |
| Operación | `diario/estado.json` del chequeo de salud | se evalúa entero cada corrida |

Los S3 solo se re-bajan si cambió el ETag: 5 MB que no cambiaron no se
descargan dos veces.

---

## Las tres decisiones que hacen que esto sea usable

Un motor de alertas se muere de dos formas: por ruido (nadie lo abre) o por
silencio (nadie sabe que se rompió). Las tres reglas de abajo son las que
sostienen el filo.

### 1. La prensa es corroboración, no disparador

Medido: cuando la prensa disparaba alertas propias, metía **79 de 84 señales**
en el sector salud. Eso no es un radar, es un lector de RSS.

Un titular no es un hecho nuevo del Estado — es el eco de uno. Entonces:

- Si el titular habla de algo que **hoy** se movió en el Congreso, en un
  regulador o en el Ejecutivo, se **cuelga de esa señal** como cobertura
  (*"esto ya lo reportaron 4 medios"*), y le sube el nivel: un proyecto que
  además tiene prensa encima se mueve distinto.
- **Única excepción que dispara sola:** un titular que nombra una empresa
  vigilada **y** describe un hecho accionable (sanción, investigación, orden
  judicial, intervención…) **y** no tiene acto del Estado que le corresponda.
  Ahí la prensa va por delante del registro y esperar al acto es llegar tarde.
- Todo lo demás se descarta **y se cuenta** en el pie del digest.

Los dos filtros de la excepción son necesarios. Solo *"nombra empresa"* daba 26
alertas altas en un día en financiero, casi todas noticia comercial rutinaria.
Solo *"hecho accionable"* deja pasar la crisis genérica del sector, que no es de
nadie en particular.

La contratación **no ancla cobertura**: un contrato no es algo que la prensa
cubra, y cruzarlo con titulares producía coincidencias de vocabulario
administrativo (un contrato de vigilancia en Bogotá "corroborado" por prensa de
México, España e Indonesia).

### 2. Los contratos se juzgan por quién y por novedad, nunca por monto

El monto no discrimina: la Lambda ya devuelve el top del sector **ordenado por
valor**, así que "contrato grande" describe al 100% de lo que llega. Un umbral
solo repartiría la etiqueta «alto» a todos por igual — que es exactamente lo que
pasaba (5 de 5 contratos en «alto», en todos los sectores, todos los días).

Lo que sí distingue:

- **Quién** — el proveedor es una empresa de `tools/caudal/empresas.py`. Se usa
  `es_razon_social`, la regla **estricta**, no el match por alias: en SECOP el
  proveedor son millones de filas dominadas por personas naturales y las marcas
  son apellidos corrientes (medido: 42/42 de los que casaban por alias con
  «uber» eran gente llamada Uber).
- **Novedad** — una entidad aparece comprando en una categoría en la que no la
  habíamos visto. La categoría se deriva del objeto (obra, dotación,
  tecnología, interventoría…) porque el feed no trae UNSPSC.

**Sin histórico no se afirma novedad.** "Nunca lo había visto" y "nunca había
mirado" no son lo mismo; confundirlos genera una alerta falsa por cada entidad
nueva del universo. El histórico arranca vacío y se llena solo — la detección de
novedad **se calienta con el uso**, y el digest lo dice explícitamente mientras
tanto.

### 3. "Sin novedades" es una salida legítima y silenciosa

Si no hay nada de nivel suficiente, **no se manda correo**. Un digest vacío
semanal mata el canal: a la tercera semana de correos que no dicen nada, el que
sí importa tampoco se abre.

Está implementado explícitamente en `motor.py` (buscar el comentario
`SILENCIO LEGÍTIMO`), no como un efecto colateral de que la lista quede vacía.

El riesgo obvio de esto es confundir *"no pasó nada"* con *"el rastreo se
cayó"*. Por eso existe el **canal de operación**: lee el `estado.json` del
chequeo de salud y avisa aparte cuando la maquinaria falló. Si el rastreo se
cae, el silencio deja de ser silencio y se vuelve una alerta.

---

## Canal de operación (interno)

Va a Ricardo, no a clientes. Lee `Bases de datos/leyes-senado/diario/estado.json`
(lo escribe `tools/caudal/salud/check.py`) y aplica cuatro reglas que vienen del
handoff de esa pieza, puestas para **no despertar a nadie en falso**:

1. `corrida` puede estar **ausente** → nunca se lee como "el cron falló".
2. `corrida.arrastrada` = el bloque es de una corrida vieja conservada para no
   borrar historia → se juzga por `corrida.fin`, no por su presencia.
3. Un ping con `externa: true` (SECOP vía Socrata, prensa vía Google News) que
   degrada a `warn` o `error` es **un tercero caído, no nosotros** → se registra
   en "mirado y descartado", no se alerta.
4. Un archivo `clase: "estatico"` (los 14 del histórico 1990-2026) **no
   envejece** → de él solo importa que exista y que no se haya truncado.

---

## Niveles

Cada señal viaja con un campo `porque` que explica en una línea qué la disparó.
No es decoración: un digest que dice "alto" sin justificarlo no se puede llevar
a una reunión, y el nivel es una **regla determinista**, no una opinión de un
modelo.

| | Congreso | Regulatorio | Ejecutivo | Contratación |
|---|---|---|---|---|
| **alto** | aprobación en debate · conciliación · reforma estructural · radicado en la comisión del sector | circular o resolución (cambia la regla para todos los vigilados) · multa ≥ $100M | decreto o ley sancionada | proveedor vigilado · categoría nueva para la entidad |
| **medio** | ponente designado · asignación de comisión · toca el sector de refilón | sanción del sector · apertura de investigación | resolución · circular · directiva | resto |
| **bajo** *(no se envía)* | honores y conmemorativos | actos procesales y de recaudo | normativa general | — |

Las señales de nivel bajo **no entran al digest pero se cuentan** en el pie.

---

## Cómo se monta el cron

Es un agente de launchd **propio**. No toca `run_diario.sh` ni su plist: el
rastreo y las alertas son dos procesos con dueños distintos.

```bash
# 1. destinatarios (el archivo real está gitignored)
cp tools/caudal/alertas/destinatarios.ejemplo.json \
   tools/caudal/alertas/destinatarios.json
$EDITOR tools/caudal/alertas/destinatarios.json

# 2. la key de Resend, FUERA del repo
mkdir -p ~/.config/caudal
printf 'RESEND_API_KEY=re_xxxxxxxxxxxx\n' > ~/.config/caudal/alertas.env
chmod 600 ~/.config/caudal/alertas.env

# 3. sellar el estado (esto NO manda nada)
python3 tools/caudal/alertas/motor.py --baseline

# 4. instalar el agente
cp tools/caudal/alertas/co.ricardoruiz.caudal-alertas.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/co.ricardoruiz.caudal-alertas.plist
```

Operar:

```bash
launchctl list | grep caudal-alertas                                  # ¿cargado? (last exit debe ser 0)
launchctl kickstart -k gui/$(id -u)/co.ricardoruiz.caudal-alertas     # forzar una corrida ya
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/co.ricardoruiz.caudal-alertas.plist
tail -f tools/caudal/alertas/datos/alertas.log
```

Dispara **08:45 y 20:15**, ~45 min después de cada corrida del rastreo (08:00 y
19:30). Si el Mac estaba dormido, launchd corre la agendada perdida al
despertar; el estado del motor evita que eso reenvíe nada.

---

## Envío

Por Resend, desde `contacto@ricardoruiz.co` (el dominio ya está verificado).

**Sin `RESEND_API_KEY` el motor no falla y no se calla:** escribe los digests en
disco y deja una cola en `pendientes.json`. Cuando la key exista:

```bash
RESEND_API_KEY=... python3 tools/caudal/alertas/sender.py \
  --pendientes tools/caudal/alertas/datos/digests/2026-08-02
```

Eso importa porque **el estado del motor ya avanzó**: si un correo se pierde por
falta de key, esas señales no vuelven a aparecer mañana.

Prueba de cableado: `RESEND_API_KEY=... python3 sender.py --probar tu@correo.com`

---

## Archivos

```
reglas.py       sectores, vocabulario, niveles, salud operativa — TODO el criterio editorial
fuentes.py      lectores de las 6 fuentes → eventos con forma común
motor.py        orquestador: diff contra estado, clasificación, armado, silencio
render.py       HTML de correo (tablas + estilos inline, sin fuentes web ni JS) + texto plano
sender.py       Resend, con cola cuando falta la key
run_alertas.sh  runner del cron (candado, timeout, log rotado)
co.ricardoruiz.caudal-alertas.plist   agente de launchd
destinatarios.ejemplo.json            plantilla; el real va gitignored
datos/          estado, cache de S3 y digests (gitignored)
```

`datos/` vive bajo `tools/` porque era el único árbol que la sesión que lo
construyó podía escribir. Para moverlo a `Bases de datos/leyes-senado/alertas/`
—que es donde el proyecto guarda datos— basta exportar `CAUDAL_ALERTAS_DIR`.

## Dependencias con el resto de Caudal

Se importan **en modo lectura** y con fallback: si alguno cambia, el motor
degrada pero no se cae.

- `caudal_core.py` → `SECTORES_CLIENTE` y el tesauro `SINONIMOS`. Mapear los
  sectores a tópicos del tesauro (en vez de escribir vocabulario nuevo) hace
  que un cambio allá se herede solo, igual que hace `empresas.py`.
- `clasificar.py` → `clasificar_titulo`, que detecta honores y reformas.
- `empresas.py` → las 388 empresas y gremios, y las reglas de match por nombre.
