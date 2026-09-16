# Escucha social · qué cuesta y qué se cobra

El precio de venta de Candidato 360 sale de esta cuenta, así que la cuenta se
escribe. Tres archivos:

| Archivo | Qué hace |
|---|---|
| `perfil.mjs` | El perfil de escucha: temas, escalas, redes, **topes** y el actor de Apify de cada red. Lo comparten el modelo y el medidor —dos configuraciones serían dos opiniones—. |
| `medir.mjs` | Corre el perfil contra Apify **una vez** y le pregunta qué cobró. Escribe `precios-medidos.json`. |
| `costos.mjs` | El modelo: volumen, costo marginal, el escalón del plan y el precio sugerido. Prefiere los precios medidos; si no hay, avisa que está estimando. |

## Medir antes de fijar tarifa

```bash
node tools/candidato-360/escucha/medir.mjs              # ensayo: dice qué correría, no gasta
export APIFY_TOKEN=...                                  # NUNCA en el repo ni en un chat
node tools/candidato-360/escucha/medir.mjs --gastar --tope=10
node tools/candidato-360/escucha/costos.mjs             # ya con los precios reales
```

`--tope=10` mide el precio por resultado igual y gasta una décima parte. Es lo
que ya advertía `tools/radar-mujer-medios/social.json`: **50 ítems de prueba
antes de escalar**, porque los nombres de campo del input varían por actor.

Otras banderas: `--red=x,facebook` mide solo esas; `--espera=600` sube el tope
de paciencia por actor; en `costos.mjs`, `--corridas=1`, `--temas`, `--trm`.

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
