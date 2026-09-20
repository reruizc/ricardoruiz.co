# Candidato 360 · perfil del votante (tarjeta 06)

El voto es secreto: **nadie** puede decir quién votó por una persona. Lo que sí
se puede es describir el **electorado de los puestos donde están sus votos**,
ponderado por cuántos votos sacó en cada uno, y compararlo con el promedio del
municipio —que es lo que hace que el número signifique algo—. La tarjeta lo dice
con esas palabras: es una lectura del terreno, no de sus votantes.

| Dimensión | Fuente | Estado |
|---|---|---|
| **Sexo** | `PUESTOS_GEOREF.csv`, columnas MUJERES y HOMBRES (censo electoral por puesto) | publicado |
| **Rural / urbano** | zona electoral de cada mesa: `99` es la zona rural del municipio; `90` y `98` (censo consolidado y cárceles) no son ni lo uno ni lo otro | publicado |
| **Edad** | `CENSO_EDAD_PUESTO.json` (lo produce `construir-edad.mjs`) | publicado (19-sep-2026) |
| **Sexo × edad** | `PERFIL_SEXO_EDAD_PUESTO.json` (lo produce `construir-sexo-edad.py`) | publicado (19-sep-2026) |
| **El territorio** | el censo de TODOS los puestos del municipio + `asamblea-2023/dep/<dep>.json` (potencial y votantes) | publicado |
| **Cómo vota el territorio** | `asamblea-2023/dep/<dep>.json`, con cada partido puesto en su familia por `partidos-bloques.js` | publicado |
| **La que debería buscar** | la meta de votos (tarjeta 02) contra su base de hoy | publicado |

## Las tres lecturas que decide una campaña

Describir el electorado de sus puestos responde «cómo es el terreno donde ya
tengo votos». Faltaban las tres que se usan para decidir:

1. **El territorio.** El censo completo del municipio, su participación en 2023
   y su composición: el tablero entero, no el pedazo que ya ocupa.
2. **Cómo vota.** La Asamblea de 2023 es la única elección que baja a **todos**
   los municipios del país con el voto por partido —el concejo por comuna existe
   en once ciudades—, así que de ahí sale la historia ideológica del territorio,
   agrupada en familias (`PartidosBloques.bloqueDePartido`). Se marcan dos: la
   familia de ESTA campaña —el espectro que eligió si va por firmas, el bloque
   de su partido si va con aval— y la de su aval anterior, cuando son distintas.
   «Sin clasificar» son los movimientos locales y las coaliciones, que en un
   municipio pequeño pesan tanto como los partidos nacionales.
3. **La que debería buscar.** Los votos que le faltan para la meta **no se
   parecen a su base** —esos ya los tiene—: se parecen al territorio del que los
   va a sacar. Por eso el perfil objetivo es el promedio de los dos, pesado por
   cuántos votos pone cada uno:

   ```
   objetivo = (base × perfil de sus puestos + faltantes × perfil del municipio) / meta
   ```

   Con eso la ficha dice cuántos votos ya tiene en ese territorio, cuántos le
   faltan, cuánto pesa su familia política ahí y si le alcanza sola. Quien se
   muda de territorio empieza en cero: su votación anterior no cuenta donde no
   la sacó.

El objetivo se calcula **al abrir la ficha** y no al pintar la tarjeta, porque
la meta de votos llega después (es una estimación con su propia consulta). Si
todavía no está, la ficha muestra el territorio y calla el objetivo.

El archivo de edad ya está en
`congreso-2026/output/mapas-2026/CENSO_EDAD_PUESTO.json` (13.239 puestos, bandas
18-25 · 26-40 · 41-60 · 61+). Si algún día no estuviera, el modal dice que falta
en vez de estimar la edad con el promedio del municipio y presentarla como suya.
Para regenerarlo:

```
node tools/candidato-360/perfil/construir-edad.mjs \
  --w26="Bases de datos/output_edad_1v/w26-puesto.csv"
```

`w26-puesto.csv` sale de `tools/edad-1v-2026/build_w26.py` (perfil etario 2022
por puesto de la Registraduría + deriva DANE 2022→2026, con raking IPF a los
votantes reales de 2026). El JSON publicable son cuatro bandas por puesto
—18-25, 26-40, 41-60 y 61+— y pesa ~700 KB.

## Dónde vive cada cosa

| Archivo | Qué hace |
|---|---|
| `candidato-360-electorado.js` | **las cuentas**: perfil del censo de sus puestos, ideología del territorio y votación objetivo |
| `candidato-360.js` (tarjeta 07) | el resumen de una línea y el botón |
| `candidato-360-electorado.html` | el análisis completo, con figuras y gráficos |

Las cuentas están en un módulo aparte porque las usan las dos pantallas: si la
tarjeta y la página dieran números distintos, ninguna serviría. El módulo
devuelve **datos**, no texto; cómo se escriben los nombres (tipo oración) y los
porcentajes es cosa de cada pantalla.

La página resuelve el JSON mesa a mesa de cada candidatura **desde el slug**
(`ALC2023-…` → `alcaldia-2023/…`) en vez de bajar los índices completos: son 40
MB para averiguar una URL que el propio slug ya contiene.

La prueba es `tools/candidato-360/prueba-perfil.mjs` (16), que abre la página
con todo lo remoto simulado.
