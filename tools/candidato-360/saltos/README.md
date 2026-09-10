# Candidato 360 · el salto de corporación

Cuando una persona con historial se lanza a una corporación **distinta** —de la
JAL al Concejo, del Concejo a la Asamblea, de la Alcaldía a la Gobernación—, el
modo «Proyectado» del mapa del CRM no puede poner la meta donde cayó su
historial: el Concejo no se elige por localidad ni la Asamblea por municipio.
Antes lo hacía (una edil de Teusaquillo con 6.770 votos «proyectados», todos en
Teusaquillo). Ahora la meta se **reparte por cómo vota el territorio de destino**
por su partido, y el territorio de origen pesa lo que midió un estudio empírico.

## Cómo reparte (candidato-360.js · sección 8 ter)

1. **La base**: dónde votó su partido en la corporación de destino en 2023
   (`resultados-concejo-2023.json` por localidad/comuna en 11 ciudades;
   `asamblea-2023/dep/{dep}.json` por municipio). Una coalición se parte en sus
   partidos y se suma. Si el partido no tiene huella suficiente (≥ 60 % de las
   áreas y ≥ 1 % de los válidos), cae al **bloque ideológico** (`partidos-bloques.js`,
   el mismo diccionario que usa `alcaldias-2023.html`), y si tampoco, a la
   **participación**. La nota del mapa dice cuál capa se usó.
2. **El origen**: la fracción `a` de la meta que se queda en su territorio de
   origen. Con el estudio publicado, `a = lift × peso del origen en la base`
   (acotado al 95 %); sin lift, `a = arraigo_mediana`; sin estudio, `a` es el
   peso del origen en la base (cero bono: nadie lo midió). Dentro del origen la
   forma la pone su propia huella; fuera, la base re-normalizada.
3. La suma da exactamente la meta (`distributeVotes`).

En Concejo → Concejo (o cualquier no-salto) no cambia nada: reparto proporcional
al historial, como siempre. «Total» tampoco se toca.

## El estudio (`estudio.mjs`)

Mide, con candidaturas reales que dieron el salto **cuatro años después**:

| Medida | Qué es |
|---|---|
| `arraigo` | fracción de la votación de destino que cayó en el territorio de origen |
| `lift` | `arraigo ÷` lo mismo para la **lista del partido** en el destino (cuántas veces pesa el origen frente a lo que pesa para su partido). Es lo que consume la web. `lift_participacion` lo mide frente a los válidos por área (2023), como referencia |
| `gap` | votos de destino ÷ votos de origen |

Se agregan por **departamento** (código electoral, sin ceros) y `_nacional`,
con medianas y cuartiles. La web usa el departamento si tiene ≥ 5 casos, si no
el nacional, si no nada (`arraigoEmpirico`). Si el partido cambió entre las dos
elecciones el caso igual entra (`mismoPartido` queda en el CSV para filtrarlo
después si conviene): el reparto sigue el patrón del partido **de destino**.

Filtros para no emparejar homónimos: nombre de ≥ 3 palabras, **único** en cada
índice, y el destino tiene que votar ≥ 90 % en el municipio (JAL → Concejo) o
departamento (→ Asamblea / Gobernación) del origen.

### Correrlo (Mac, Node 18+)

```
node tools/candidato-360/saltos/estudio.mjs
```

Baja ~100 MB de índices y las mesas de cada par (cacheado en `~/.cache/rr-saltos`,
la segunda corrida no pide nada). Para un ensayo corto:

```
node tools/candidato-360/saltos/estudio.mjs --salto "jal>concejo" --limite 40
```

Deja `salida/saltos-arraigo.json` (la tabla) y `salida/saltos-casos.csv` (cada
caso, para revisarlo en Excel). Publicar la tabla:

```
aws s3 cp tools/candidato-360/saltos/salida/saltos-arraigo.json s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/candidato-360/saltos-arraigo.json --content-type application/json --cache-control max-age=3600
```

La web la busca en esa ruta; mientras no exista, reparte sin bono y la nota lo
dice («Sin estudio de saltos publicado…»).

## Pruebas

```
node tools/candidato-360/prueba-salto.mjs          # el motor puro (20 casos)
node tools/candidato-360/prueba-salto-crm.mjs      # el CRM con Leaflet, sin red (13)
```

`estudio.mjs` se puede probar sin S3 apuntando `--base` a una carpeta servida
localmente con la misma estructura (`jal-2019/index-jal-2019.json`, mesas por slug…).
