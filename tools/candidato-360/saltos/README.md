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
| `lift` | `arraigo ÷` el peso que ese mismo territorio tiene en la base con la que reparte la web (la huella de su partido, o su bloque, o la participación). Es decir: **cuántas veces pesa el origen frente a lo que pesaría sin arraigo**. Es el número que consume `repartoSalto`, porque no depende del tamaño del territorio |
| `gap` | votos de destino ÷ votos de origen |

El neutro se calcula llamando a la **misma** `baseDestino` de `candidato-360.js`
(el script la carga del archivo con `vm`): si se midiera contra otra cosa, el
lift no sería el multiplicador que la web necesita. Existe solo para destinos
2023, que es cuando hay resultados por área.

Se agregan por **departamento** (código electoral, sin ceros) y `_nacional`,
con medianas y cuartiles. La web usa el departamento si tiene ≥ 5 casos, si no
el nacional, si no nada (`arraigoEmpirico`). Si el partido cambió entre las dos
elecciones el caso igual entra (`mismoPartido` queda en el CSV para filtrarlo
después si conviene): el reparto sigue el patrón del partido **de destino**.

Filtros para no emparejar homónimos: nombre de ≥ 3 palabras, **único** en cada
índice, y el destino tiene que votar ≥ 90 % en el municipio (JAL → Concejo) o
departamento (→ Asamblea / Gobernación) del origen.

## Lo que salió (corrida del 10-sep-2026, 2011→2015, 2015→2019, 2019→2023)

| Salto | Casos | Arraigo mediana | Lift mediana | Gap mediana |
|---|---|---|---|---|
| JAL → Concejo | 1.283 | 0,28 [0,13–0,42] | **2,16** (n=157) | 0,77 [0,35–1,70] |
| Concejo → Asamblea | 1.115 | 0,47 [0,29–0,65] | **2,61** (n=364) | 5,65 [2,90–10,90] |
| Alcaldía → Gobernación | 18 | 0,29 [0,24–0,67] | **1,63** (n=11) | 5,48 [2,13–24,50] |

Tres lecturas que valen para el producto:

- **El arraigo existe y es fuerte, pero no lo es todo.** Quien salta pesa entre
  dos y tres veces más en su territorio de origen de lo que pesaría solo por
  la huella de su partido. Ese es el bono que aplica la web. Pero la mediana de
  votación que se queda ahí es el 28 % (JAL → Concejo): **siete de cada diez
  votos nuevos salen del territorio viejo**, que es justo lo que el mapa no
  estaba mostrando.
- **Saltar de la JAL al Concejo cuesta votos, no los multiplica**: la mediana
  del gap es 0,77, o sea que la mitad de quienes lo intentan sacan *menos*
  votos que en la JAL. Ese `x1,5` fijo que estaba en discusión iba en la
  dirección contraria. En cambio, el salto de Concejo a Asamblea sí multiplica
  (mediana 5,6), porque la circunscripción pasa de un municipio a todo el
  departamento.
- **Alcaldía → Gobernación casi no ocurre**: 18 casos en doce años, ninguno con
  cinco casos en un mismo departamento. Ahí la web usa el nacional y la nota lo
  dice.

El lift solo se puede medir donde hay resultados por área de 2023: las 11
ciudades con `resultados-concejo-2023.json` para JAL → Concejo (11 departamentos
con estudio propio, encabezados por Bogotá con 36 casos) y todos los
departamentos para Concejo → Asamblea (28 con estudio propio). En el resto, la
web cae al lift nacional.

### Correrlo (Node 18+)

```
node tools/candidato-360/saltos/estudio.mjs
```

Baja los índices y las mesas de cada par (cacheado en `~/.cache/rr-saltos`, la
segunda corrida no pide nada; la primera tarda unos minutos). Para un ensayo
corto:

```
node tools/candidato-360/saltos/estudio.mjs --salto "jal>concejo" --limite 40
```

Deja `salida/saltos-arraigo.json` (la tabla) y `salida/saltos-casos.csv` (cada
caso, para revisarlo en Excel). Los tres saltos se pueden correr por separado
en paralelo y luego fundir los JSON: es lo que se hizo para la tabla publicada.

### Publicarla

La tabla **viaja con el sitio**: son 22 KB versionados en
`candidato-360-data/saltos-arraigo.json`. Regenerarla es copiar el archivo ahí
y hacer commit. Los casos crudos quedan en `casos/` para poder auditarlos.

La web pide primero la copia de S3 —para poder refrescar el estudio sin
desplegar— y si no está, usa la del sitio:

```
aws s3 cp candidato-360-data/saltos-arraigo.json s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/candidato-360/saltos-arraigo.json --content-type application/json --cache-control max-age=3600
```

Si no existe ninguna de las dos, el reparto sigue funcionando: el origen pesa
lo que pesa en la huella y la nota del mapa lo dice.

## Pruebas

```
node tools/candidato-360/prueba-salto.mjs          # el motor puro y la tabla publicada (23)
node tools/candidato-360/prueba-salto-crm.mjs      # el CRM con Leaflet, sin red (13)
```

`estudio.mjs` se puede probar sin S3 apuntando `--base` a una carpeta servida
localmente con la misma estructura (`jal-2019/index-jal-2019.json`, mesas por slug…).
