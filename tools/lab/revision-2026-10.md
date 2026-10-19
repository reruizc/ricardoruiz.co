# Lab de Políticas Públicas · revisión de fondo (18-oct-2026)

Qué corregir, qué hacer más fácil de entender y qué hacer más explorable.
Recorrido hecho sobre el repo y en el navegador (hub + los 8 módulos, desktop y
375 px). Todo lo que está aquí se verificó con archivo:línea o en pantalla; lo
que es propuesta va rotulado como tal. El brief para la parte visual (transiciones,
estados, hub como recorrido) está aparte en `tools/lab/brief-gpt-visual.md`.

Los 8 módulos no se tocan desde el **18-jul-2026** (solo el hub, el 10-oct, por
enlaces de entrada). Es decir: se construyeron en 11 sprints entre mayo y julio y
nadie ha vuelto a usarlos con ojos de usuario. Eso se nota, y es lo que este
documento ordena.

---

## 0. Lo que más pesa (si solo se hace una cosa)

1. **El Lab no tiene «ver un ejemplo».** En Problema Público, Evaluación, AIN,
   Prospectiva y Comunicar el usuario llega a un formulario vacío y tiene que
   inventar un caso para entender qué hace el módulo. Solo MicMac (19
   plantillas), Mactor (4) y Alternativas (6) traen arranque con un clic. Un
   **caso demo completo y coherente** (el mismo en los 8 módulos: p. ej.
   deserción escolar 9-11 en Bogotá, que ya es el ejemplo de los placeholders)
   cargable desde el hub con «Explorar con un caso de ejemplo» es la mejora de
   explorabilidad más grande y la más barata: no toca la lógica, solo escribe
   un STATE en `localStorage` y abre el módulo.
2. **El hub habla con números viejos y jerga interna.** «Siete herramientas»,
   «seis módulos», «cinco módulos», «los 3 módulos», «los cuatro son módulos»,
   «Sprint G», «Sprint E» están a la vista del usuario (detalle en §1). Se
   corrige en una hora y es lo primero que ve cualquiera.
3. **El wizard «Ayúdame a escoger» solo puede recomendar 4 de los 8 módulos.**
   Las preguntas 1-4 puntúan únicamente problema/estructural/mactor/evaluación;
   alternativas y AIN entran por «empujones» sueltos, y **prospect y comunicar
   no pueden salir nunca** (`computeHubRecommendation`, `analisis-estructural.html:4005-4030`).
4. **No hay URL por módulo ni por paso dentro del hub.** El hub y el módulo
   MicMac son el mismo archivo y navegan con `showStage()` sin tocar la URL
   (no hay `pushState`/`hashchange`): el botón Atrás del navegador saca del
   sitio, no se puede compartir «estoy en el paso 3» y Google ve una sola
   página de 310 KB. Lo mismo dentro de cada módulo.
5. **Topbar y FAB rotos en pantallas angostas, y sin progreso en móvil.** A
   375 px el botón «Modo día» queda cortado a la derecha en todas las páginas;
   el botón flotante «Recursos» tapa campos de formulario a 800 px y el pie en
   móvil (capturas del 18-oct); y en cinco módulos las pastillas de paso se
   ocultan a ≤720 px, así que en el teléfono nadie sabe en qué paso va.
6. **El «Volver» del hub y de Mactor apunta a `index.html#proyectos`, que no
   existe** (la pestaña de proyectos del índice no responde al hash). Dos clics
   de salida que aterrizan en la portada equivocada.

---

## 1. Hub (`analisis-estructural.html`, sección `#stage-hub`)

### Texto desactualizado o interno (corregir ya)
| Dónde | Dice | Debería |
|---|---|---|
| `:1817` hero | «Siete herramientas conectadas» | ocho (el eyebrow de arriba ya dice «8 módulos integrados») |
| `:1981` «Mi informe del lab» | «en los seis módulos» | ocho |
| `:1976` eyebrow visible | «Sprint G» | «Informe combinado» o nada; «Sprint» es jerga de desarrollo |
| `:2334` ayuda del selector territorial | «Sprint E habilitó 1.108 municipios…» | «Datos oficiales para 1.108 municipios…» |
| `:4032` frase de espera del wizard | «Cruzando tus respuestas con los 3 módulos…» | «con los 8 módulos» |
| `modal-why` (`:2769+`) | «Cada uno de los cinco módulos…» y solo lista 5 | listar los 8 o quitar el conteo |
| `:2159` welcome de MicMac | «Los cuatro son módulos complementarios» | ocho |
| footer | «Composición: Familjen · Petrona · Mono» | es una nota de diseño, no información para el usuario |
| `index.html:626` tarjeta de proyectos | «Análisis Estructural de Sistemas» | el hub se llama «Laboratorio de Políticas»; quien entra desde el índice llega a otro nombre |

El mismo defecto («Sprint E») está en `problema-publico.html:1310`,
`evaluacion.html:1097` y `ain.html:1171`.

### Estructura
- **El hub vive dentro del módulo MicMac.** `analisis-estructural.html` pesa
  310 KB (76 KB gzip) y carga Chart.js desde CDN en el `<head>` (`:11`) para
  todos los que solo quieren ver la portada del Lab. Propuesta: `lab.html` como
  hub propio (ligero, con su URL y su `<title>`), y `analisis-estructural.html`
  pasa a ser un módulo más, con «← Volver al lab» como los otros siete. Hoy el
  botón Volver del hub va a `index.html#proyectos` y, dentro de MicMac, el
  mismo botón saca del Lab en vez de volver al hub (`:1755`).
- **Las tarjetas son un catálogo, no un recorrido.** El párrafo de abajo
  (`:1960-1972`) explica la ruta lógica, pero la grilla no la muestra: sin
  número, sin conector, sin «empieza por aquí». Y el `mod-tag` de cada tarjeta
  es una lista de apellidos («Zwicky · Lempert · Ritchey · MVPF», «OCDE 2021 ·
  CLAD · MIPG · Ganz · Lakoff · EAST») que intimida al usuario nuevo y no le
  dice qué va a hacer. Propuesta: el tag pasa a ser la **pregunta que responde
  el módulo** («¿Qué problema resuelvo?», «¿Quién apoya y quién bloquea?») y
  los apellidos van al modal «¿En qué se basa?». La parte visual del recorrido
  está en el brief de GPT (§5).
- **«Mi informe del lab» aparece antes de haber hecho nada.** Para el visitante
  nuevo son 8 tarjetas «Sin contenido — clic para abrir el módulo» y dos
  botones de descarga de un PDF vacío. Propuesta: mostrar el bloque completo
  solo cuando `countActiveModules() ≥ 1`; antes, una sola línea.
- **El wizard** (ver §0.3) además arranca con «Pregunta 1 de 5» sin decir cuánto
  dura ni que se puede saltar. Con 8 módulos, la pregunta 1 debería tener 8
  opciones (o agrupar: diseñar · entender el sistema · actores · decidir entre
  opciones · regular · evaluar · anticipar · comunicar) y cada pregunta puntuar
  a los 8.
- **Mi análisis en progreso** (`#hub-inprogress-chip`) solo detecta MicMac. Si
  el usuario dejó algo a medias en Problema Público o en Comunicar, el hub no
  se lo dice (aunque «Mi informe» sí lo lee). Propuesta: un chip por módulo con
  contenido, derivado del mismo `LabInforme.getLabState()`.

---

## 2. Problema Público (`problema-publico.html`)

Es el módulo de entrada («el paso 0 antes de cualquier matriz») y el que
mejor flujo tiene: pastillas de paso, wizard de síntoma, árbol del problema,
seeds de evidencia y criterios. Aun así:

### Correcciones
- **Memo con «No hacer nada» como recomendación.** Si el usuario llega al paso
  06 sin calificar la matriz (que es lo que pasa la primera vez), el memo dice
  «Alternativa con mayor score ponderado: No hacer nada (baseline) · 0.00/5.00»
  y enunciado «(sin definir)» (`renderResults`, `:2495-2545`; captura del
  18-oct). Debe decir «Aún no has calificado la matriz» y mandar al paso 05.
  Igual el ranking del paso 05: tres barras en 0.00 no son un ranking.
- **Se puede avanzar hasta el final sin escribir el problema.** `goToStep()`
  (`:2057`) no valida nada; está bien no bloquear, pero el paso 01 debería
  marcar el enunciado como pendiente en las pastillas (hoy el ✓ de «Definir»
  aparece solo por haber pasado por ahí).
- **La nota metodológica del final promete lo que ya existe:** «Próximas
  versiones incorporarán copiloto IA para sugerir alternativas y validar el
  conjunto de criterios, plantillas seed por sector y respaldo PDF descargable»
  (`:1556-1558`), justo debajo de la barra de IA que ya hace eso y del modal
  que ya descarga los dos PDF.
- **El welcome remite a «los cuatro» módulos** (`:1046`) y solo enlaza 3.
- **Kicker «Sprint E · evidencia oficial municipal»** (`:1310`).
- **«Alternativa A» / «Alternativa B»** como nombres por defecto
  (`ensureBaseAlternativas`, `:2259`) llegan así al memo y al CSV si el usuario
  no los cambia. Mejor dejarlas vacías con placeholder y no contarlas como
  alternativas hasta que tengan nombre.

### Más fácil de entender
- Cada paso abre con un párrafo de `stage-intro` en negrilla + itálica que
  repite la idea del acordeón del welcome. Está bien escrito, pero son 5
  pantallas de «por qué» antes del «qué hago»: la caja podría colapsarse tras
  la primera visita (`localStorage`) o ir en un «?» al lado del título.
- El paso 00 (síntoma) y los sub-pasos 01·b y 01·c (Rittel-Webber y marco)
  **no aparecen en las pastillas** (`STEP_LABELS` tiene 5), así que el usuario
  que entra ahí no sabe en qué parte del flujo está ni cómo volver sin el botón
  de abajo. Propuesta: pastilla «00 Síntoma» opcional y los sub-pasos como
  «01 Definir · diagnóstico» dentro de la misma pastilla.
- El resultado se llama «Memo de política» en el paso 06 pero «memo final» en
  el botón del 05 y «memo .md» en la descarga; y el «Issue Paper Bardach» no
  se explica en ninguna parte antes del botón.

### Más explorable
- Caso demo (ver §0.1): el placeholder de deserción 9-11 ya está escrito en
  los `placeholder` de 6 campos; falta convertirlo en un botón «Cargar
  ejemplo» que llene síntoma, definición, 3 evidencias, 3 alternativas, 5
  criterios y la matriz calificada, para que el memo se vea lleno en 10 s.
- El paso 02 tiene «Cargar 3 fuentes típicas» y el 04 «Restaurar 5 criterios»;
  el 03 no tiene seed de alternativas sin IA (la IA es Pro+). Tres alternativas
  genéricas por tipo de política (regular · subsidiar · informar) bastarían.
- Sin «Empezar de cero» para el anónimo: `newProject()` (`:3051`) solo existe
  en el disclosure de proyectos, que requiere sesión. Quien quiere borrar el
  estado tiene que vaciar `localStorage` a mano.

---

## 3. Los otros seis módulos — consistencia

Auditoría archivo por archivo (mactor · evaluacion · alternativas · ain ·
prospect-escenarios · comunicar). Lo bueno primero: en los seis, **todas las
funciones llamadas desde `onclick` existen**, `loadState` es defensivo, no hay
placeholders vacíos ni enlaces a archivos inexistentes, y auth · cloud · polling
· invitaciones están completos (la única pieza que falta es la `cloud-bar-flow`
de Mactor). Los problemas son de coherencia entre hermanos, no de código roto.

### Lo que rompe la navegación
- **`index.html#proyectos` no existe.** `index.html` no tiene `id="proyectos"`
  (la pestaña es `tab-proyectos` / `pan-proyectos` y no lee `location.hash`),
  así que el «Volver» del hub (`analisis-estructural.html:1755`) y el de Mactor
  (`mactor.html:678`) caen en la portada sin abrir la pestaña de proyectos.
  Mactor es además el único módulo cuyo «Volver» no vuelve al lab.
- **`alternativas.html#robustez`** desde `ain.html:1292`: en Alternativas no hay
  `id="robustez"` ni manejo de hash; aterriza en la bienvenida.
- **La barra de pasos desaparece en móvil**: `.steps-row{display:none}` a ≤720 px
  en evaluacion:236, alternativas:236, ain:236, prospect:237 y comunicar:117.
  En el teléfono no queda ningún indicador de en qué paso se está. Mactor no la
  tiene en ninguna pantalla (solo los números «— 01…06» de cada sección).
- Numeración de la pantalla final distinta en cada módulo: «— 07» (alt, ain),
  «— 08» (ev), «— 05» (prospect), «— 06» (pp), «— ∑» (comunicar).

### Lo que confunde
- **El informe combinado salta de la sección 6 a la 8** (`lab-informe.js:837 →
  861`; no existe «## 7.»), y comunicar dice que entra como «sección 9»
  (`comunicar.html:1022`) mientras el hub lo numera 8. Un lector del PDF ve una
  numeración con hueco.
- **Anglicismos sueltos** en interfaz: «seed» (evaluacion:1031, 2026),
  «Pre-Analysis Plan» (evaluacion:1377), «CONPES light» (alternativas:1456),
  «Cross-impact» y «no-regret» (prospect:964-1269), «Framing» y «Backup»
  (comunicar:469, 741). O se traducen o se explican la primera vez.
- **Comunicar va por libre en varias cosas**: pastillas de paso como `<div
  onclick>` y no `<button>` (1364), FAB sin `id="lab-fab"` e icono ✦ en vez de ↗
  (1119), es el único con «Reiniciar plan» para anónimos (1039), con autosave en
  la nube (2424) y con «↓ Backup .json» (469) que **ningún módulo puede volver a
  importar** (no hay `input type=file`). Dos botones «×» sin tooltip (1481,
  1784). Es el módulo con menos `@media` (solo topbar y FAB).
- **Mactor solo descarga `.json`** (1093); los demás dan .md/.csv/.pdf. Y su
  bienvenida no tiene «← Volver al lab».
- **Reset:** fuera de Comunicar, `newProject()` solo existe dentro de «Mis
  proyectos», que exige sesión. En Evaluación además **no reinicia
  `STATE.economico`** ni `tipo_sinergia`/`tratamiento_escalonado`
  (evaluacion:3654-3668): un «nuevo proyecto» arrastra el análisis económico del
  anterior.
- **Banderas muertas:** `contexto.importedFromPP` existe en alternativas (1680)
  y prospect pero nunca se pone en `true`; Alternativas no lee
  `pp-current-v1` aunque el hub dice que es «la versión profunda del paso 3 de
  Problema Público».
- **El handoff alt→ain es manual**: `ain.html` no lee `?import=alt` de la URL;
  muestra un banner y hay que pulsar «Importar». Los otros dos handoffs (alt→pp,
  ain→ev) sí son automáticos. Debería ser uno u otro en los tres.
- **Cross-links incompletos y sin criterio**: Mactor no enlaza alternativas,
  AIN ni prospect; Evaluación no enlaza alternativas ni AIN; Prospect no enlaza
  AIN, evaluación ni PP; Comunicar no enlaza prospect. AIN es el único que
  enlaza a los otros siete. Propuesta: un bloque «Siguiente en el ciclo» único,
  generado desde una tabla en `lab-recursos.js` (ya cargado por los 8), que
  muestre el anterior, el siguiente y «todos los módulos».

### Bienvenidas
Las seis siguen el mismo patrón: 93-133 palabras visibles + botón «¿En qué se
basa?» + 3 acordeones cerrados + CTA al final. Ninguna ofrece un ejemplo
completo de un clic. Los seeds que existen son parciales: Mactor (4 plantillas
en el wizard) y Alternativas (6 plantillas de variables) son los únicos con
arranque real; Evaluación tiene teoría + indicadores de educación; Prospect
ejes + escenarios; Comunicar solo audiencias; **AIN ninguno** (solo importar).

### Tabla comparativa

| | mactor | evaluación | alternativas | ain | prospect | comunicar |
|---|---|---|---|---|---|---|
| Volver al lab | ✗ (index#proyectos) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Link al informe | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ («sección 9») |
| Pastillas de paso | ✗ | ✓ oculto ≤720 | ✓ oculto ≤720 | ✓ oculto ≤720 | ✓ oculto ≤720 | ✓ oculto ≤720 (div) |
| Reset sin sesión | ✗ | ✗ (y bug) | ✗ | ✗ | ✗ | ✓ |
| Ejemplo/seed | ✓ | parcial | ✓ | ✗ | parcial | parcial |
| Cloud bar en flujo | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ + autosave |
| Exports | solo .json | .md .md .csv | .md .csv .pdf | .md .csv .pdf | .md .csv .pdf | .md .csv .md |
| @media móvil | ✓ | ✓ | ✓ | ✓ | ✓ | mínimo |

---

## 4. Revisión técnica transversal

Medido con comandos sobre los 8 HTML y los 3 JS compartidos.

### Sano
- **Cero errores de sintaxis** en los 8 bloques `<script>` inline y en los 3 JS
  (`vm.Script` / `node --check`). Cero `TODO`/`FIXME`, cero `console.log`, cero
  nombres de modelo de IA a la vista del usuario, cero precios escritos en el Lab
  (los únicos COP son placeholders de ejemplo).
- Misma versión de jsPDF (2.5.1) en los 4 sitios que lo cargan; mismas claves
  de sesión y tema (`rr-token`, `rr-user`, `rr-theme`) en los 8.
- Endpoints del worker: los 8 usan el mismo patrón `/<prefijo>/{list, save,
  load, delete, invite, accept, copiloto}`; 26 acciones IA en total.

### Para corregir
- **`lab-recursos.js`, `lab-indicadores.js` y `lab-informe.js` se cargan sin
  `?v=`.** Al cambiarlos (p. ej. para el bloque «Siguiente en el ciclo»), el
  navegador servirá la copia vieja. Misma regla que `cand-index.js`.
- **Chart.js síncrono en el `<head>`** de analisis-estructural:11 y mactor:11,
  bloqueando el render de la portada del Lab. Debería ir con `defer` o cargarse
  on-demand al entrar a resultados, como ya se hace con jsPDF.
- **`ain.html` descarga `indicadores-mun.json` (980 KB, ~150 KB gzip) en cada
  carga** (`init → renderAll → renderProblema → ainTerrPobDeptos → load()`,
  ain:1842-1935), aunque el usuario no haya elegido territorio. Los otros tres
  módulos lo piden solo al entrar al paso que lo usa.
- **Ningún `<script>` lleva `defer`/`async`** en los 8 archivos.
- **Google Fonts bloqueante** (11 variantes: Familjen ×4, Petrona ×4, Space
  Mono ×2, Syne) en la línea 10 de los 8. Si la decisión de §5.1 es quedarse
  con esta paleta, conviene al menos autoalojar los woff2 como se hizo con
  Helvetica en el resto del sitio.
- **Accesibilidad:** 33 botones «×» de cierre de modal sin `aria-label` (todos
  los módulos); 19 `select` sin `label` (p. ej. `#terri-select`
  analisis-estructural:2352, `#msg-valores-select` comunicar:651); `outline:none`
  70 veces y **`:focus-visible` cero veces** en todo el Lab, con `cursor:none`
  encima: quien navega con teclado no ve dónde está. El texto `--ink-3` no llega
  a 4,5:1 en ningún modo (día 2,94:1, noche 4,22:1) y se usa 49-90 veces por
  archivo para ayudas y metadatos.
- Restos de un estado que ya no existe: CSS `.is-soon` / `.mod-badge-soon`
  (analisis-estructural:556-617) con todos los módulos en `soon:false`;
  placeholder «En construcción · D.7» en ain:1434 (lo pisa `renderResults`,
  pero se ve si el render falla).

### Duplicación (la deuda estructural)
El chasis está copiado ocho veces y ya divergió:
- **~31 funciones de infraestructura** (auth, cloud, polling, invitaciones,
  tema, cursor, toast, modal, gate de plan, jsPDF, modal de recursos) suman
  **~17,5 KB por archivo, ~140 KB repetidos**. De `renderProjectsList`,
  `cloudSave`, `cloudLoad` y `startPolling` hay **8 variantes distintas**; de
  `renderCloudBars` 4; de `initCursor` 7. Solo 4 funciones son idénticas en los
  8.
- **140 reglas CSS idénticas** en 7-8 archivos (~15 KB por copia): tokens,
  cursor, modal, toast, FAB y barras de nube. AIN además copió el CSS de
  tarjetas de Alternativas (ain:469-610).
- Consecuencia práctica: cualquier arreglo de los de arriba (topbar móvil,
  FAB, `:focus-visible`, aria-label) hay que hacerlo ocho veces y verificarlo
  ocho veces. Extraer `lab-base.css` (tokens, cursor, topbar, modal, toast,
  FAB, cloud bar, pastillas de paso) y `lab-base.js` (auth, cloud con prefijo
  por parámetro, tema, cursor, toast, modal, gate, jsPDF, recursos) es el
  punto 9 de la lista de §6: es el que más paga a largo plazo y el de más
  riesgo, así que va al final y módulo por módulo. El precedente en el repo es
  `legislativo-base.{css,js}`.

---

## 5. Decisiones que son de Ricardo (no se pueden tomar desde el código)

0. **Decidido el 19-oct (Ricardo):** la barra superior pasa al sistema v2 del sitio
   (`lab-nav.css`, misma barra que electoral/noticias: Volver verde, sesión naranja,
   registro azul, logo Syne) en los 8 archivos; el cuerpo del Lab conserva su paleta.
   El inicio del hub se reescribió en lenguaje llano (para alcaldes y concejales de
   municipios de categorías 4-6): el tag de cada tarjeta es la pregunta que responde y
   los autores bajan a una línea «Método». Se quitó el bloque «Más del Lab» (tutela,
   juez, pensamiento investigativo): no son módulos del ciclo. Cada tarjeta tiene un
   hueco de imagen opcional `imagenes/lab-{problema,estructural,mactor,evaluacion,
   alternativas,ain,prospect,comunicar}.jpg` (1200×600 aprox.; si falta, no se ve).
0b. **Decidido el 19-oct (Ricardo): identidad propia.** El Lab deja la paleta del
   dashboard (papel oscuro · salmón · Familjen/Petrona, «la letra tan Claude») y pasa a
   **«la mesa de planeación»** en `lab-theme.css`: tablero claro con trama de puntos
   (`#f2efe6`), tinta de marcador índigo (`#1f1b3a`), notas adhesivas como acentos
   (caléndula `#f5c518` · azul `#4f7ee8` · rosa `#ef7c8e` · verde `#5cb37f`), tarjetas
   con pestaña de color y número, Bricolage Grotesque en titulares, Public Sans en texto,
   JetBrains Mono en etiquetas. Siempre clara: el botón día/noche queda oculto. Se aplica
   a los 8 módulos redefiniendo las variables que ya usaban (un solo archivo). Las 8
   imágenes de tarjeta (`imagenes/lab-*.jpg`, 1200×605) se generaron con Canva con la
   misma escena —mesas, mapas y notas adhesivas en municipios colombianos, luz de día— y
   quedan también en el diseño de Canva «Lienzo blanco horizontal» (DAHYbZIQ4-I) por si
   hay que reexportarlas.
1. **Sistema visual del cuerpo.** ~~El Lab sigue en el chasis del dashboard de mayo~~ (resuelto arriba). Antes:
   (Familjen Grotesk · Petrona · Space Mono, papel #1a1610, salmón), mientras
   `index.html`, `dashboard.html` y el resto migraron en julio al sistema v2
   (Helvetica Neue embebida, #060810, azul). Hoy el Lab es la única familia de
   páginas con tipografía de Google Fonts y paleta propia. Es defendible
   (identidad editorial, modo día) pero hay que decidirlo: o se declara
   «sub-marca Lab» y se deja, o se migra. El brief de GPT asume que **se
   queda** y pide pulir dentro de esa paleta; si la decisión es migrar, el
   brief cambia.
2. **Hub propio (`lab.html`) o seguir dentro de `analisis-estructural.html`.**
   Afecta enlaces ya publicados (`index.html`, memoria, PT-BR); se resuelve
   con una redirección o dejando el archivo viejo como hub y moviendo MicMac a
   `analisis-estructural-modulo.html`, pero alguien tiene que escoger.
3. **Caso demo único para los 8 módulos.** Requiere escoger el caso y
   escribirlo con cifras reales (deserción tiene datos en `lab-indicadores`).
4. **Qué hacer con el wizard:** rehacerlo para 8 módulos o reemplazarlo por
   la grilla ordenada + una línea «si no sabes por dónde empezar, empieza por
   Problema público».

---

## 6. Orden sugerido de ejecución

**Estado (18-oct-2026, misma sesión):** pasos 1-4 hechos (ver tabla: ✅). Al hacerlos
salió un bug que no estaba en el diagnóstico: `lab-informe.js` leía MicMac y Mactor
con un shape que esos módulos nunca tuvieron (`matrix['i-j']`, `actores[].nombre`),
así que **el informe combinado nunca incluyó las secciones 2 y 3**; corregido con un
lector que acepta `string[][]` y strings. Lo nuevo:
- `lab-demo.js` (caso «deserción escolar 9-11 · Bogotá», cifras ilustrativas,
  8 estados) + botón «Explorar con un caso de ejemplo» en el hub y una línea
  «Carga el caso de ejemplo» en el welcome de cada módulo; «Borrar» cuando está activo.
- Bloque CSS móvil idéntico al final del `<style>` de los 8 archivos (topbar que no
  se corta, FAB como icono compacto abajo a la derecha en ≤1100 px).
- `?v=20261018` en `lab-recursos.js`, `lab-indicadores.js`, `lab-informe.js`, `lab-demo.js`.
- Numeración del informe 1-9 sin hueco; «sección 8» en comunicar; `index.html`
  nombra el proyecto «Laboratorio de Políticas Públicas» en los 4 idiomas.
No se tocaron: footer «Composición», pastillas de paso en móvil, wizard a 8 módulos,
hash por paso, `lab.html`, `:focus-visible`/aria (pasos 5-9).


| # | Qué | Esfuerzo | Toca lógica |
|---|---|---|---|
| ✅ 1 | Textos viejos y «Sprint» en los 8 archivos (§1, §2, §3) | 1 h | no |
| ✅ 2 | Topbar en móvil + FAB recursos (ver §4 y brief §4) | 2 h | no |
| ✅ 3 | Memo/ranking vacíos con mensaje honesto en PP | 1 h | mínima |
| ✅ 4 | Caso demo cargable desde el hub (8 STATE escritos a mano) | 1 día | no (solo datos) |
| 5 | Wizard a 8 módulos (preguntas y puntajes) | medio día | sí, acotada |
| 6 | Hash por paso (`#paso-3`) y `pushState` en los 8 módulos | 1 día | sí |
| 7 | `lab.html` como hub ligero | 1 día | sí |
| 8 | Pulido visual con lo que devuelva GPT (`lab-motion.css`) | 1 día de integración | no |
| 9 | Extraer chasis común a `lab-base.{css,js}` (ver §4) | 2-3 días | sí, de riesgo |

Los puntos 1-4 se pueden hacer en una sesión sin pedir permiso para nada; del
5 en adelante conviene ir módulo por módulo y verificar en el navegador.
