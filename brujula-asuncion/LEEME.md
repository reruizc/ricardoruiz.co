# Brújula Asunción 2026

Test de afinidad programática para la **Intendencia de Asunción** (elección del 4 de
octubre de 2026). Doce preguntas → afinidad con Camilo Pérez y Soledad Núñez + brújula de tres
bloques + mapa de los 68 barrios + cómo votó tu zona en seis elecciones. Al final, una pregunta
de contexto nacional que no cuenta para el resultado (ver abajo).

Es el mismo patrón del `test-presidencial-2026.html` de Colombia, adaptado a Paraguay:
página única, sin backend, sin datos personales. **La diferencia grande: acá no hay
Lambda ni LLM.** Todo el resultado es determinista y se calcula en el navegador, así que
se puede abrir con doble clic y funciona igual.

```
brujula-asuncion/            ← en el repo · https://ricardoruiz.co/brujula-asuncion/
  index.html            la página (single-file salvo los 2 scripts de abajo)
  contenido.js          candidatos, ejes y arquetipos
  banco.js              120 preguntas, dos versiones de lenguaje y posiciones de los dos candidatos
  datos/datos.js        bundle de zonas + puestos + barrios (lo genera el builder)
  datos/geo.js          los 68 polígonos del INE, recortados a código+nombre (lo genera el builder)
  datos/{zonas,puestos,barrios}.json   los mismos datos sueltos, por si otro módulo los usa
  img/arq-*.jpg         los 5 pósters de arquetipo
  tools/build_datos.py  el builder
  (el .docx fuente de las posiciones vive en Proyecto BL Paraguay/, fuera de git)
```

Abrir: `open index.html` (funciona con `file://` gracias a `datos/datos.js`) o servirlo.

## Lo que NO ve quien responde

⚠️ **El arquetipo de votante se calcula y no se muestra.** Es una etiqueta de segmentación
—dice cómo suele decidir un segmento, no quién sos— y devolvérsela al votante convierte un
test de afinidad en una clasificación. `calcArquetipo()` lo deja en `STATE.arq` y viaja en el
payload anónimo; el cruce **perfil × candidato** vive en `admin.html`. Por la misma razón
salieron de la vista del usuario el reparto de *Perfiles de votante estimados en la zona*, la
capa **Perfil de votante** del mapa y la etiqueta socioeconómica del barrio (`perfil_2026`,
que producía rótulos como "POPULAR-OBRERO" sobre el nombre del barrio).

⚠️ Al tocar esto, recordar que **la etiqueta sigue existiendo en el dato** (`b.arquetipos`,
`b.perfil_2026`): lo que se quitó es la superficie, no la fuente. Sigue visible la *Lectura
del barrio* (`arquetipo_preocupacion`), que describe el reclamo del barrio, no a quien vota.

## La pregunta de contexto nacional

`B.extra.presidente` en `contenido.js`: percepción de la gestión de Santiago Peña, **1** muy
mala … **5** muy buena. `prepQ` la agrega al final del cuestionario con `extra:true`, y esa
bandera la excluye de `afinidad()`, de los ejes y del contador ("Pregunta N de 12" no la
cuenta; ella se anuncia como *"Una última, fuera del test"*). No tiene posiciones de
candidato porque no es una pregunta municipal.

⚠️ Va en su **propio campo** del payload (`presidente`), no dentro de `respuestas`: metida
ahí ensuciaría el promedio por pregunta del panel, que asume escala programática.
⚠️ `orden:[5,4,3,2,1]` cumple dos funciones: presenta la escala de mejor a peor y, al venir
preasignado, **impide que `renderQ` la baraje** — una escala de valoración no se baraja.

## Cache-buster

Los cinco scripts locales se cargan con `?v=YYYYMMDD` desde `index.html` (y `config.js`
desde `admin.html`). **Bumpearlo cada vez que se toque `contenido.js`, `banco.js` o los
`datos/*.js`**, o el navegador sirve la copia vieja sin dar ningún error — pasó al probar
esta tanda: la página seguía sin la pregunta nueva porque el `contenido.js` cacheado no la
traía.

## Regenerar los datos

```bash
cd /Users/ricardoruiz/ricardoruiz.co
python3 brujula-asuncion/tools/build_datos.py   # lee los CSV/xlsx de 'Proyecto BL Paraguay/' (fuera de git)
```

Tarda ~20 s. Lee los CSV del TSJE y los Excel de `ASUNCIÓN/`, y reescribe
`datos/*.json` + `datos/datos.js`. Imprime al final los controles de validación —
**mirarlos**: dicen cuántos puestos quedaron sin resultado y cuáles perdieron la
comparación con 2018.

## Actualizar el banco electoral

La fuente es `Proyecto BL Paraguay/BRUJULA ASUNCIÓN AJUSTADA 2 CANDIDATOS.docx`.
Para regenerar `banco.js`:

```bash
python3 brujula-asuncion/tools/build_banco.py \
  'Proyecto BL Paraguay/BRUJULA ASUNCIÓN AJUSTADA 2 CANDIDATOS.docx' \
  brujula-asuncion/banco.js
```

- `pos` 1-5 en la escala de esa pregunta.
- `evidencia`: `E` explícita o `I` inferencia sustentada, según el documento.
- El importador traduce `E` a confianza alta y `I` a confianza media.

⚠️ **`conf:'B'` no es un 3, es un hueco.** Esa pregunta **no entra** al cálculo de ese
candidato: ni lo favorece ni lo perjudica, y el ranking lo declara ("2 pendientes").
El 3 que lleva es solo para dibujar la brújula. Hoy hay **6 posiciones pendientes**
(desagües en Camilo y Arlene; densificación en Soledad y Arlene; titulación en Soledad
y Rodri). El foro "Siete compromisos por Asunción" del 20 de agosto es la ocasión de
reemplazar varias por posiciones verificadas: al hacerlo, cambiar `conf` a `'A'` o `'M'`
y el porcentaje se recalcula solo.

## Cómo se calcula la afinidad

`distancia = |respuesta − posición|` por pregunta; `afinidad % = 100 × [1 − Σd / (4·n)]`,
donde `n` son las preguntas respondidas **y verificadas para ese candidato**. Las 10 pesan
igual. La ponderación por temas prioritarios del barrio existe pero **está apagada por
defecto y es una decisión del usuario**: la intensidad mediática mide cuánto se habla de
algo, no cuánto debería importarle a cada votante.

Autotest del motor (cada candidato respondiendo como él mismo da 100% consigo mismo):

```bash
cd brujula-asuncion && node -e "global.window={};require('./banco.js');const B=window.BRUJULA_BANCO;
const a=(ans,c)=>{let s=0,m=0;for(const q of B){const p=q.pos[c];if(p.conf==='B')continue;s+=Math.abs(ans[q.codigo]-p.pos);m+=4}return Math.round(100*(1-s/m))};
for(const c of ['camilo','soledad']){const ans={};B.forEach(q=>ans[q.codigo]=q.pos[c].pos);
console.log(c,['camilo','soledad'].map(k=>k+':'+a(ans,k)).join(' '))}"
```

## El ajuste ideológico de los temas 3, 7, 9 y 11

`AJUSTE BRUJULA ASUNCIÓN.docx` (en `Proyecto BL Paraguay/`) reescribe las cinco respuestas
de las 40 preguntas de esos cuatro temas, en las dos versiones de lenguaje, con una escala
ideológica uniforme: **1 derecha marcada … 5 izquierda marcada**, siempre `D-D-N-I-I`. Las
preguntas no cambian. Cada pregunta ajustada lleva ahora `ideo` (las etiquetas por opción).

```bash
python3 tools/parse_ajuste.py '../Proyecto BL Paraguay/AJUSTE BRUJULA ASUNCIÓN.docx' /tmp/ajuste.json
python3 tools/aplicar_ajuste.py /tmp/ajuste.json banco.js
```

⚠️⚠️ **La escala nueva NO es la vieja invertida, y por eso el remapeo de posiciones no se
puede automatizar.** En unas preguntas conserva la dirección (3.1, 11.1), en otras la
invierte (7.1, 9.1) y en otras **cambia de eje**: 3.3 pasa de "mantenimiento vs obra nueva"
a "austeridad vs inversión pública", que no es lo mismo. Aplicar el documento sin tocar las
posiciones dejaba a Soledad como la más privatizadora de plazas y a Camilo como el más
anti-densificación — al revés de lo que dicen sus programas, sin que nada fallara.

Se intentó detectarlo por similitud de texto y **no sirve**: el documento reescribió todo,
los ratios quedaron en ~0,3 y empatados. `MAPEO` en `aplicar_ajuste.py` se armó leyendo las
40 preguntas y comparando el **contenido** de la opción que ocupaba cada candidato con las
opciones nuevas. La etiqueta ideológica no interviene en ese mapeo: la afinidad se calcula
sobre contenido, y la etiqueta es metadato de análisis.

**16 posiciones se movieron y 9 quedaron en `conf:'B'`** (3.5, 7.5, 7.10 y 11.7 en los dos
candidatos, y 9.9 en Soledad): son las preguntas donde el eje cambió de naturaleza y la
posición vieja no tiene equivalente. El motor las excluye del cálculo y lo declara. Para
cerrarlas hace falta una posición verificada, no una inferencia.

⚠️ Al regenerar: `aplicar_ajuste.py` es **idempotente** y solo toca los 4 temas; se verificó
que las 80 preguntas restantes quedan byte a byte idénticas.

## El pentágono

`B.bloques` en `contenido.js`: los 5 bloques del documento (Ciudad en Movimiento · Ciudad
que Cuida · Muni que Funciona · Barrios Vivos · Oportunidades Urbanas) agrupan los 12 temas
sin repetir ni omitir. Cada vértice promedia, en la escala 1-5 del banco normalizada a 0-1,
las preguntas del cuestionario que caen en sus temas. Se dibujan **dos polígonos sobre los
mismos ejes y las mismas preguntas**: el de quien responde y el del candidato elegido en el
ranking, que se cambia con los chips de arriba del gráfico.

⚠️ **`inv:true` en movilidad (tema 6).** En once de los doce temas el 1 es
mercado/control/ajuste y el 5 público/comunitario; en movilidad corre al revés (1 es
transporte público y 5 el automóvil). Sin invertirlo, ese tema tira del vértice hacia el
lado contrario al que dice la respuesta. Al sumar temas nuevos, **mirar la dirección de la
escala antes de meterlos a un bloque.**

⚠️ **El pentágono no se rotula izquierda/derecha, y no es un descuido.** Solo 4 de los 12
temas tienen la escala ideológica del ajuste; los otros 8 son ejes programáticos. Los polos
de cada barra describen lo que de verdad separa a las opciones. Si algún día se ajustan los
8 temas restantes, ahí sí el pentágono puede leerse como un mapa ideológico.

Cobertura del ajuste por bloque: Movimiento 1/3 · Cuida **0/2** · Funciona **0/2** ·
Barrios 1/2 · Oportunidades 2/3.

⚠️ El bloque del tema que el usuario elige como prioritario queda sobre-representado (le
tocan 2-3 preguntas de ese tema en vez de 1). Es consecuencia del cuestionario
personalizado, no del pentágono; la nota al pie lo dice.

## Los datos territoriales y sus trampas

**Fuentes.** Seis elecciones por mesa del TSJE (vía datos.gov.py): municipales **2010 ·
2015 · 2021** y presidenciales **2013 · 2018 · 2023**; padrón 2026 y arquetipos desde los
Excel de `ASUNCIÓN/`; preocupaciones por barrio desde las tablas del .docx. El inventario
de archivos, con el resultado de Asunción de cada uno y sus trampas, está en
`../Proyecto BL Paraguay/DATOS-ELECTORALES.md` (fuera de git). Agregar una elección = una entrada en `ELECCIONES` del builder
(archivo + listas con nombre verificado); el frontend lee `meta.elecciones` y no hay que
tocarlo.

**Lo que muestra la página:** las tres municipales completas, las presidenciales
plegadas, y una serie del voto ANR municipal vs presidencial — la brecha entre las dos
(52-58% en presidenciales contra 40-47% en municipales) es el dato que más dice de una
zona.

**Validado contra el resultado oficial.** 2021 Asunción: ANR 122.358 y JA 108.487 contra
los **122.353 / 108.485** publicados (diferencia de 5 y 2 votos), 47,5% para Nenecho
Rodríguez, y APT 12.044 exacto = Alianza **Asunción para Todos** de Johanna Ortega — que
NO es Patria Querida, error fácil de cometer con la sigla. 2018: el archivo reproduce el
nacional al decimal (ANR 46,42% · GANAR 42,74% contra 46,49 / 42,73 oficiales), así que su
Asunción es confiable.

⚠️ **`Resultados-por-mesa-2015.csv` es una copia byte a byte del de 2021** (mismo md5).
Está mal nombrado: su contenido es municipal y lo gana ANR, cuando en 2015 ganó Mario
Ferreiro. **No usarlo como 2015.** El builder solo lee el de 2021.

⚠️⚠️ **Cinco locales cambiaron de sede conservando el mismo código** en algún año
(`SEDE_CAMBIADA` en el builder, con los años afectados por cada uno: p. ej. el código que
hasta 2018 era "Universidad Católica" en 2021 es "Esc. Básica Nº 2 Celsa Speratti", y
`(3,24)` cambió recién en 2023). Cruzarlos por código mostraría el resultado de otro
colegio con cara de dato exacto. El builder excluye **solo los años no comparables** de
ese local, y la página dice cuáles y por qué. ⚠️ Hay renombres que SÍ son el mismo sitio
("Corazón de Jesús"→"Sagrado Corazón de Jesús", "Nac. de Niñas"→"Asunción Escalada (ex
Nac. de Niñas)", "Rca. de Haití"→"ex Col. Haití"): no van en la lista. Al sumar un año
nuevo, comparar nombres contra 2021 antes de confiar en el código.

⚠️ **El tamaño de mesa cambia por año** (2.049 mesas en 2018, 1.398 en 2015, 1.125 en
2021). No hay duplicados — se verificó que las 2.049 llaves
`(zona, local, mesa)` son únicas. Comparar **porcentajes**, nunca conteos de mesas.

**Hallazgo que vale mirar:** entre 2018 y 2021 el mapa se invierte. La Recoleta pasa de
ser la zona **más** colorada (57,9% ANR presidencial) a la **menos** (42,6%), y Zeballos
Cué al revés (50,9% → 60,5%). El voto nacional-partidario y el voto municipal de castigo
no se mueven igual.

**Lo inferencial va rotulado como tal.** Los 5 arquetipos y las preocupaciones por barrio
son modelo y rastreo de prensa, no encuesta ni escrutinio; la página lo dice en cada
bloque y en la metodología.

## El mapa

Polígonos oficiales: **INE Paraguay, cartografía censal 2012**, 68 barrios, bajados de
`ine.gov.py` (URLs exactas y alternativas en `geo/LEEME.md`). El builder los cruza con
los 68 barrios del Atlas **por código `BAR_LOC`** tras una tabla de 9 alias de abreviatura
(Mcal./Mariscal, Gral./General, Linch/Lynch, Kue/Cue, Murucuyá/Mburucuya) — 68 de 68
casan; el frontend nunca compara texto. Se emite `datos/geo.js` con coordenadas a 5
decimales (~1 m) para no cargar los 420 KB del original.

Leaflet va por CDN (unpkg); sin internet la página sigue funcionando y solo oculta el
mapa. El mapa aparece dos veces: en el paso de ubicación (tocar un barrio fija zona y
barrio) y en el resultado, con 5 capas.

⚠️ **Las capas de voto son por ZONA electoral, no por barrio.** El TSJE publica por mesa y
local, y el local no se mapea a barrio sin georreferenciar los 145 locales — eso no está
hecho. Cada barrio pinta el dato de su zona (6 colores, no 68) y la nota del mapa lo dice.
Las capas de perfil y prioridad sí son por barrio, y son modelo.

⚠️ El INE tiene también la versión **2022** (`geo/ASUNCION-BARRIOS-INE2022.geojson`): mismos
68 códigos, pero el `032` cambió de polígono y de nombre (De la Residenta en 2012 → San Juan
en 2022) y eso redibujó Botánico, Loma Pytã, Jara y San Blas. Se usa 2012 porque el Atlas
y la matriz de arquetipos son 2012; para cruzar con el censo 2022 hay que cambiar de archivo.

## Pendientes

1. **Fotos de los candidatos**: dejar `img/cand-{camilo,soledad}.jpg`
   (cuadradas, ~300 px) y poner `foto:true` en `contenido.js`. Mientras tanto el avatar
   muestra las iniciales — y **no se pide la imagen**, para no dejar 404 en consola.
2. Mantener actualizado el banco desde el documento editorial de dos candidatos.
2b. ~~Mapa por barrio~~ ✅ hecho con la cartografía censal del INE (ver abajo).
3. Decidir dónde se publica y con qué marca. Hoy lleva `noindex,nofollow` y no está
   enlazada desde ningún lado.
4. ~~Captura y administrador de respuestas~~ ✅ implementados y desplegados.
   ⚠️ **`arquetipo` y `presidente` exigen redesplegar la Lambda**: `sanitize()` descarta
   todo campo que no esté en su whitelist, así que hasta ese despliegue los dos llegan y se
   pierden **en silencio** (la respuesta se guarda igual, sin esos dos campos).
5. **Georreferenciar los 145 locales de votación** (lat/lon) para pasar las capas de voto
   de zona a barrio por punto-en-polígono — el salto de 6 a 68 colores. El TSJE no publica
   coordenadas; habría que geocodificar por nombre/dirección y validar a mano.
6. Publicación: la app está en el repo público; los insumos (CSV del TSJE, Excel de
   arquetipos, docx) quedan en `Proyecto BL Paraguay/`, que está en `.gitignore`.
