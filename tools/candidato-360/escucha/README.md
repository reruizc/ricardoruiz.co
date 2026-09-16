# Escucha social · qué cuesta y qué se cobra

El precio de venta de Candidato 360 sale de esta cuenta, así que la cuenta se
escribe. Tres archivos:

| Archivo | Qué hace |
|---|---|
| `perfil.mjs` | Deriva el perfil de escucha **del vínculo**: los temas que escribió el candidato (`escucha.ideas`), la escala según la corporación (`campana`) y las cuentas que validó. Trae los **topes**, el actor de Apify de cada red y las páginas de Facebook verificadas por territorio. Lo comparten el modelo y el medidor. |
| `ejemplo-vinculo.json` | Un vínculo con la forma que guarda el worker, para correr todo sin una cuenta real. Los dos temas que trae son de la agenda real de Tunjuelito, pero en producción salen del panel, no de acá. |
| `medir.mjs` | Corre el perfil contra Apify **una vez** y le pregunta qué cobró. Escribe `precios-medidos.json`. |
| `costos.mjs` | El modelo: volumen, costo marginal, el escalón del plan y el precio sugerido. Prefiere los precios medidos; si no hay, avisa que está estimando. |
| `apify.mjs` | El cliente de Apify que comparten medidor y recolector: token desde el entorno o `.env`, errores con el mensaje de Apify tal cual, costo leído de la respuesta. |
| `capturar.mjs` | **El recolector.** Una lectura completa: las dos capas por Apify, postura/tema/tono con el modelo, y la captura escrita con el contrato que pinta el panel. Sin `--gastar` solo dice qué haría. |
| `ejemplo-captura.json` | Una captura de mentiras con el contrato de abajo, para probar el panel sin gastar (`prueba-captura.mjs`). |

## El perfil no se escribe: sale del vínculo

Los temas los pone **el candidato** en el panel de escucha; nosotros no. El
territorio y la corporación vienen de la campaña guardada. Quien se lanza a la
JAL de Tunjuelito escucha Tunjuelito y Bogotá; si el mismo vínculo cambia a
Concejo de Tunja, el mismo código escucha Tunja y nada más. La escala la decide
`territorioDe` de `candidato-360-panel.js` —la misma regla del panel y del
briefing—, cargada acá con `vm` para que no haya dos.

| Corporación | Escalas que escucha |
|---|---|
| JAL | la localidad **y** su ciudad |
| Concejo · Alcaldía | el municipio |
| Asamblea · Gobernación | el departamento |

Para medir o costear a un candidato real se le pasa su vínculo —el JSON que
devuelve `/c360/me → vinculo`—: `--vinculo=su-vinculo.json`. Sin temas escritos
la escucha por palabra no se mide y se dice por qué; sin páginas de Facebook
verificadas para ese territorio, Facebook no se mide y se dice por qué.

## Dónde va el token

En Apify: **Settings → API & Integrations → Personal API token**. Empieza por
`apify_api_`. En su terminal, una de dos:

```bash
export APIFY_TOKEN=apify_api_xxx                        # solo esta sesión
echo 'APIFY_TOKEN=apify_api_xxx' >> .env                # queda puesto · .env ya está en .gitignore
```

Nunca en el repo, nunca en un chat, nunca en un pantallazo. Si el token se
escapa, se revoca en esa misma pantalla de Apify y se genera otro.

Para el worker (`rr-auth`), que es donde vivirá en producción, es otro camino y
no este archivo: `npx wrangler secret put APIFY_TOKEN`.

## Medir antes de fijar tarifa

```bash
node tools/candidato-360/escucha/medir.mjs              # ensayo: imprime las consultas, no gasta
node tools/candidato-360/escucha/medir.mjs --temas="hurto al comercio|Portal Tunal"
node tools/candidato-360/escucha/medir.mjs --gastar --tope=10
node tools/candidato-360/escucha/costos.mjs             # ya con los precios reales
```

`--tope=10` mide el precio por resultado igual y gasta una décima parte. Es lo
que ya advertía `tools/radar-mujer-medios/social.json`: **50 ítems de prueba
antes de escalar**, porque los nombres de campo del input varían por actor.

Otras banderas: `--vinculo=archivo.json` mide a un candidato real; `--red=x,facebook`
mide solo esas; `--espera=600` sube el tope de paciencia por actor; `--temas` y
`--paginas` fuerzan valores para probar sin editar nada; en `costos.mjs`,
además `--corridas=1`, `--dias` y `--trm`.

## Las páginas de Facebook están comprobadas una por una

Una URL de Facebook mal escrita **no falla**: el actor corre, no encuentra nada
y cobra igual. De los seis handles que se pusieron de memoria la primera vez,
cuatro estaban mal (`Bogota` en vez de `AlcaldiaBogota`, `CanalCapital` en vez
de `CanalCapitalOficial`…). Las que están en `PAGINAS_FACEBOOK` se verificaron
en septiembre de 2026, por ciudad y por localidad. Un territorio sin entrada no
adivina: Facebook no se mide ahí hasta que alguien verifique sus páginas y las
añada a la tabla. Es el único pedazo del perfil que no sale solo del vínculo, y
la salida honesta a largo plazo es preguntarle al candidato qué páginas locales
sigue —él las conoce mejor que nosotros—.

## Dos capas, dentro del mismo módulo

| Capa | Qué trae | Cómo | Se cobra |
|---|---|---|---|
| **1 · Posts** | *lo que se dice*: de qué se habla, quién, cuánto rinde | búsqueda por palabra (X), hashtag (Instagram, TikTok), páginas (Facebook) | base |
| **2 · Comentarios** | *lo que se siente*: postura, tono, quién amplifica | las respuestas a los `postsPorCorrida` posts con más reacción de cada red, más los propios | escalón aparte |

El sentimiento no vive en los posts: el post de la Alcaldía es neutro por
definición, la opinión está debajo. Pero raspar comentarios es otro actor y
otro precio —más que las cuatro redes de posts juntas—, así que es una capa
**aparte**: se mide aparte (`--capa=posts|comentarios|todo`), se cuesta aparte
y aparece como su propio escalón en «Qué cobrar». El análisis (postura, tema,
tono) lo hace el modelo sobre lo que llegue de las dos capas y cuesta menos de
un dólar al mes: Apify es el 97 % de la factura, con o sin comentarios.

En la salida del medidor, cada actor imprime **los campos que devuelve** en la
primera corrida. Es lo que dice si de ahí salen métricas, URLs para seguir los
comentarios o solo texto; no se adivina. Si un actor de posts no trae una URL
con un nombre conocido, la capa 2 lo dice y muestra los campos que sí
vinieron, para añadir el nombre a `referenciaDePost`.

## Las tres cosas que hay que saber antes de mirar la tabla

- **La palanca es el tope, no el modelo.** Apify cobra por resultado entregado:
  el gasto es `tope × consultas × corridas`, no «lo que traiga». El modelo de
  lenguaje es el 2 % de la factura; optimizar prompts acá no ahorra nada.
- **Cero resultados NO es «no hay conversación».** Puede ser el actor caído, el
  input con otro nombre de campo o una consulta vacía. `medir.mjs` lo dice en
  vez de dejar pasar un cero que después se lee como hallazgo.
- **Las cuatro redes no escuchan igual.** Solo X busca por palabra. Instagram y
  TikTok buscan por hashtag —que no es lo mismo— y Facebook solo trae las
  páginas que uno ya eligió seguir. A escala de localidad eso importa más que
  el precio: se puede vender «escucha de su localidad» en X, no en las cuatro.

## La captura en el panel: montada y APAGADA

`candidato-360-escucha.html` ya sabe pintar una lectura de las cuatro redes en
«Lo que se publica en sus cuentas»: por red, lo que publicó, quién lo menciona,
quién amplifica y —capa 2— la postura de los comentarios como barra con sus
citas. Cada red trae su estado: `ok`, `sin_datos` (con motivo: cero no es cero
conversación), `sin_temas`, `error`. Facebook muestra las páginas que sigue.

Está apagada a propósito: `CAPTURA_ENCENDIDA = false` en la página hace que ni
siquiera pregunte por la lectura, y todo se ve como hasta hoy. Para verla antes
de encenderla, `candidato-360-escucha.html?captura=1` (o `#captura`).

**Encenderla son tres cosas, en este orden:**

1. **El recolector corriendo dos veces al día** con `APIFY_TOKEN` y
   `DEEPSEEK_API_KEY` como secretos —el patrón es el de
   `.github/workflows/candidato-360-briefing.yml`: a las 6 a. m. y 6 p. m. de
   Bogotá (11:00 y 23:00 UTC, fuera del pico de DeepSeek)—, un vínculo por
   cliente con escucha contratada: `capturar.mjs --vinculo=… --gastar --salida=…`.
2. **El worker sirviendo `GET /c360/captura`** para la sesión: la última captura
   del vínculo de esa cuenta, o `{ ok:true, encendida:false }` si no hay. Un 404
   también vale: la página lo pinta como apagada, no como error.
3. `CAPTURA_ENCENDIDA = true` en la página.

Lo que falta del lado del worker y no de acá: aceptar `facebook` en
`POST /c360/redes` (hoy valida X, TikTok e Instagram) para que el candidato
pueda registrar su página; mientras tanto Facebook entra por las páginas del
territorio, que es su modo real.

## Contrato · `GET /c360/captura`

```jsonc
{ "ok": true, "encendida": true, "generadoEn": "2026-09-16T11:02:00Z", "modelo": "deepseek-v4-flash",
  "vinculo": { "candidato": "Junta Administradora Local · Tunjuelito · Bogotá", "nombre": "…", "temas": ["…"], "escalas": ["Tunjuelito", "Bogotá"] },
  "costo": { "apifyUsd": 0.21, "modeloUsd": 0.004 },       // lo que costó ESTA lectura
  "redes": {
    "x": { "estado": "ok" | "sin_datos" | "sin_temas" | "error", "motivo": "", "modo": "búsqueda por palabra", "handle": "…",
           "publicados": [{ "texto", "autor", "fecha", "url", "reaccion", "comentarios" }],   // lo suyo, por reacción
           "menciones":  [ /* misma ficha */ ],                                              // lo de otros sobre sus temas o su nombre
           "amplifican": [{ "autor", "veces", "alcance" }],
           "temas": { "<tema>": n },
           "comentarios": null | { "n", "posts", "clasificados", "postura": { "a_favor", "en_contra", "neutro", "ataque" },
                                   "tono": { … }, "temas": { … }, "citas": [{ "texto", "postura", "autor", "url" }], "motivo"? } },
    "instagram": { … }, "tiktok": { … },
    "facebook": { …, "paginas": ["https://www.facebook.com/…"] }
  } }
```

`ejemplo-captura.json` es una instancia completa. Reglas: una red que no
respondió sale `sin_datos` con motivo; la postura nunca viaja sin `citas`; el
panel dice que los comentarios no son la localidad.

## Cuándo volver acá

Cuando cambie el catálogo de Apify (se mueve seguido), cuando se cambie de
actor, cuando entre una red nueva o cuando la TRM se mueva lo suficiente para
comerse el margen. La tarifa que no se vuelve a calcular se vuelve falsa sola.
