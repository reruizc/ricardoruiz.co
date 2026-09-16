# Escucha social · qué cuesta y qué se cobra

El precio de venta de Candidato 360 sale de esta cuenta, así que la cuenta se
escribe. Tres archivos:

| Archivo | Qué hace |
|---|---|
| `perfil.mjs` | Deriva el perfil de escucha **del vínculo**: los temas que escribió el candidato (`escucha.ideas`), la escala según la corporación (`campana`) y las cuentas que validó. Trae los **topes**, el actor de Apify de cada red y las páginas de Facebook verificadas por territorio. Lo comparten el modelo y el medidor. |
| `ejemplo-vinculo.json` | Un vínculo con la forma que guarda el worker, para correr todo sin una cuenta real. Los dos temas que trae son de la agenda real de Tunjuelito, pero en producción salen del panel, no de acá. |
| `medir.mjs` | Corre el perfil contra Apify **una vez** y le pregunta qué cobró. Escribe `precios-medidos.json`. |
| `costos.mjs` | El modelo: volumen, costo marginal, el escalón del plan y el precio sugerido. Prefiere los precios medidos; si no hay, avisa que está estimando. |

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

## Cuándo volver acá

Cuando cambie el catálogo de Apify (se mueve seguido), cuando se cambie de
actor, cuando entre una red nueva o cuando la TRM se mueva lo suficiente para
comerse el margen. La tarifa que no se vuelve a calcular se vuelve falsa sola.
