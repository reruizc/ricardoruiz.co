# Candidato 360

> Documento de trabajo del producto. Está escrito para que alguien —persona o
> modelo— pueda entender **qué es, por qué está hecho así y dónde tocar** sin
> leer 4.000 líneas de JavaScript primero. Si va a proponer cambios, lea
> primero «Las reglas que no se negocian»: casi todo lo demás es discutible.
>
> Última revisión: septiembre de 2026.

---

## 1. Qué es

Un **CRM electoral para candidaturas territoriales colombianas de 2027**
(concejo, alcaldía, JAL, asamblea, gobernación), construido sobre el historial
electoral público. La persona se busca por su nombre, encuentra sus
candidaturas anteriores, dice a qué se lanza ahora y el producto arma un punto
de partida: mapa de su votación, meta de votos, perfil del electorado, lectura
del territorio y seguimiento.

No es una encuesta ni un predictor. Todo sale de **resultados oficiales y censo
electoral**, y cuando algo se estima, se dice que se estima y con qué.

- Vive en `https://ricardoruiz.co/candidato-360.html` (GitHub Pages, rama `main`).
- Datos públicos en S3 (`elecciones-2026/ricardoruiz.co/congreso-2026/output/`).
- Lo privado (sesión, vínculo, briefing) lo resuelve un Worker de Cloudflare
  aparte, **rr-auth**, en `/c360/*`.

## 2. El recorrido

```
Portada
  ├── «Ya me he lanzado»  →  buscar nombre  →  su historial  →  ruta (paso 2)
  └── «Es mi primera vez» →  wizard de 6 pasos
                                        ↓
                                  CRM (tablero)
                                        ↓
        paneles propios: 04 medios · 05 redes · 07 electorado
```

**La ruta (paso 2)** hace *una pregunta por tarjeta*, con salto de animación y
botón «Atrás»:

```
¿misma corporación?
   ├── sí  → ¿con qué partido?
   └── no  → ¿a cuál?  →  ¿dónde?  →  ¿con qué partido o por firmas?
```

**El CRM** son ocho tarjetas: 01 mapa del historial, 02 meta de votos,
03 briefing, 04 lectura de noticias, 05 redes, 06 arquetipos, 07 perfil del
votante, 08 recolección de firmas (solo si va por firmas). *(Desactualizado: hoy
son 01-10, con 08 endoso, 09 Día D y 10 contendientes; ver `candidato-360.html`.)*

## 3. Las reglas que no se negocian

1. **El voto es secreto.** Nada dice ni insinúa quién votó por alguien. Se
   describe el **censo de los puestos** donde están sus votos, ponderado por
   cuántos sacó en cada uno, y se compara con el territorio. La página
   `candidato-360-perfil.html` explica el método (inferencia ecológica) y por
   qué eso no viola el secreto.
2. **Nada estimado se presenta como propio.** Si falta la fuente, la tarjeta lo
   dice. Ejemplo vivo: la edad del electorado espera `CENSO_EDAD_PUESTO.json`;
   mientras no esté, la sección dice «todavía no» en vez de usar el promedio
   del municipio.
3. **Se dice de dónde sale cada número.** Cada ficha termina en su fuente y en
   su cobertura («cubre el 76 % de su votación»).
4. **El índice electoral es la vitrina.** Un visitante sin cuenta busca, entra
   y ve su historial completo; el muro cae en el CRM, que es lo que se cobra.
5. **Una cuenta, una candidatura.** El vínculo se guarda en el Worker y no se
   cambia desde la plataforma.
6. **Heurística declarada.** Donde hay una regla discutible (bloques
   ideológicos, arquetipos, arraigo) se marca como heurística, se documenta el
   criterio y existe la salida «no sabemos».

## 4. Decisiones de producto que explican el código

| Decisión | Por qué |
|---|---|
| **Una tarjeta por persona**, no por candidatura | La base tiene 439.015 candidaturas. Se unifican por nombre: cuatro componentes iguales siempre; tres componentes solo si todas sus candidaturas territoriales caen en el mismo departamento («Daniel Carvalho Mejía» sí, «Juan Carlos López» no). Los casos dudosos se revisan a mano con `personas/homonimos-xlsx.py`. |
| **Una pregunta por tarjeta** en la ruta | El paso 2 mostraba todo a la vez con la mitad de los campos deshabilitados esperando que alguien adivinara el orden. |
| **El territorio manda** sobre el historial | La meta, las firmas y la lectura ideológica se calculan sobre el territorio de la **campaña**. |
| **Historial fuera del destino = dos mapas, no uno** (27-sep-2026, pedido de Ricardo) | Edil de Teusaquillo 2015 → Alcaldía de Cartagena: **«Total» (y cada año) es su votación histórica, donde estuvo** (Bogotá, 342 votos); **«Proyectado» es el territorio al que aspira** (Cartagena con Localidad · UCG · Barrio y la meta repartida por su familia política). Antes el destino tapaba el historial y «Total» mostraba el censo de Cartagena. Código: `DESTINO_FUERA` (se fija en `loadHistoricalMap` con `historialEnCiudad`), `EN_DESTINO`, `pintarDestino()`; el despacho entre los dos mapas está al inicio de `refreshCRMMapMode` y en `showElectionView('projected')`. ⚠️ `pintarTerritorioCiudad` sube `pintandoDestino` mientras pinta: su `pintarCiudad` interno refresca en modo total y, sin la guarda, ese refresco devolvía al historial. El salto a departamento sigue su rama propia (`pintarProyeccionDepartamental`); sin capa de ciudad ni departamento, «Proyectado» cae a `renderTerritorioDeCampana`. |
| **«Barrio» sin localidad abierta = la ciudad entera por barrio** | Antes el botón estaba apagado hasta tocar una unidad. Ahora `renderBarriosForArea('*')` carga todas las partes, pinta todos los barrios con una escala, bordes finos por unidad y sin foco; tocar un barrio abre su zona. Sin cartografía barrial cae a todos los puestos de la ciudad. Vale en Total y en Proyectado. |
| **Mapa con drill down** en la pregunta del lugar | Elegir «Boyacá» entre 33 nombres parecidos no confirma nada. Sin departamento: Colombia apagada; con departamento: su silueta con municipios; con municipio: el municipio encendido. Los municipios se pueden tocar. |
| **Wizard nuevo, paso 2: ¿tiene redes? y cuáles, sin usuario** (30-sep-2026, pedido de Ricardo) | Pedir cada @ y validarlo en la segunda pregunta era demasiado para quien apenas conoce la plataforma. Ahora: «Sí, tengo / Todavía no» y, con sí, casillas Facebook · X · Instagram · TikTok. Al decir sí, **Candi explica** (`Candi.decir`) que sirven para la huella, el cálculo electoral y la escucha social, y que el usuario se pide después. Lo marcado viaja como `escucha.preferencias.redes` (con `medios: []`), así el panel de escucha abre su cuestionario con esas redes ya marcadas — ⚠️ allá `prefsGuardadas` solo da por respondido el cuestionario si trae **medios**; con solo redes lo sigue mostrando (`prefsDelAlta`). La validación con DeepSeek (`/c360/redes`) sigue viviendo en el panel de escucha. Código: `tieneRedes` · `redesElegidas` · `redesRespondidas` · `textoRedesCRM(n)`. |
| **El lugar del wizard nuevo = el de la ruta con historial, + la ciudad** (30-sep-2026) | Misma escalera en las dos rutas: Colombia apagada (se toca el departamento) → departamento con municipios (se tocan) → municipio encendido → **en JAL, la ciudad por localidad/comuna** si hay capa en `CITY_JAL_LAYERS` (se toca y elige en el desplegable). Mapa al lado del formulario (`.lugar-grid`) y municipio escondido hasta tener departamento. Código: `pintarMapaDepto({selectDepto, local})` · `pintarMapaCiudad` · `casaLocal`. ⚠️ **`casaLocal` cruza por NOMBRE si los dos lados lo traen y solo si no por número**: el número no es estable (la «localidad No. 4» de Barranquilla no es el polígono 4) y un corregimiento nunca casa con una comuna por número (Ibagué, Manizales, Villavicencio numeran los dos desde 1). Por prefijo, no «contiene»: ORIENTAL cabe en NORORIENTAL (Bucaramanga). ⚠️ **`localidadesDe` no encontraba las comunas de Cali, Cartagena ni Cúcuta** (en las DOS rutas): el formulario trae el nombre DANE («SANTIAGO DE CALI») y `COMUNAS_DATA` el de la Registraduría («CALI»), y el departamento viene recortado («VALLE», «NORTE DE SAN»). Arreglado con `mismoMunicipio` (termina en, empieza por + «DE», o + «DC»), que además deja a **CALIMA fuera de Cali**. Medido: Bogotá 20/20 · Cali 22/22 · Cúcuta 10/10 · Cartagena 3/3 · Barranquilla 5/5 · Ibagué 26/26 · Pereira 19/19, cero cruces dobles. Sin cruce: Palmitas en Medellín y 2 comunas de Bucaramanga (se eligen igual en el desplegable). |
| **Candi se presenta una vez por pestaña y comenta cada pantalla una sola vez** (30-sep-2026, pedido de Ricardo) | Cada módulo es una página aparte, así que entraba caminando y decía «¡Hola! Soy Candi…» en cada clic del tablero y al volver a la portada. Ahora `sessionStorage['candi-sesion-v1']` guarda `{presentada, dichas[]}`: la primera carga de la pestaña hace la entrada completa con presentación; las siguientes arrancan con `mascota.idle()` (ya sentada, sin caminar) y el globo dice el **`saludo` de esa vista** —una frase complementaria al HTML, no lo que ya dice el título— solo si no se dijo antes en la sesión; si ya se dijo, callada. Dentro de `candidato-360.html` el cambio de pantalla (`showScreen`) también dispara el comentario de la nueva vista (`alCambiarVista`, colgado del `MutationObserver` de `.screen`) y oculta el de la anterior. Todas las vistas de `VISTAS` traen `saludo` (portada, buscador, ruta, wizard, CRM, electorado, arquetipos, Día D, endoso, contendientes). `sessionStorage` a propósito y no `localStorage`: otro día o en otra pestaña merece la entrada otra vez. ⚠️ `idle()` no emite `candi:complete`, así que en la carga «ya sentada» el descanso del hueso (`montarDescanso`) y el globo se enganchan a mano. |
| **Aval: partido o firmas** | A alcaldía y gobernación se llega de las dos maneras. Por firmas no hay partido: se pregunta el espectro (5 posiciones) y con eso se ordena la recolección. |
| **La capital, de primeras** en el desplegable de municipios | Concentra las candidaturas. La regla sale del dato (código Divipola `001`), no de una tabla de 33 capitales. |
| **Nombres de lugar en tipo oración** | La Registraduría escribe «MEDELLÍN» y los departamentos llegan «Antioquia»: media línea gritando. Solo cambia la presentación; el valor guardado sigue siendo el original, que es la llave contra la Divipola. |
| **Logos de partido** en la elección del aval | Un nombre en mayúsculas no se reconoce; el logo sí. |
| **La meta en tres escenarios** (inminente · probable · posible), no un número | Un candidato no sabe si 21.000 es mucho o poco. Los tres salen de la misma proyección (censo × participación) y van **de menor a mayor esfuerzo**: *inminente* (rojo) es lo que ya casi pasa con el trabajo mínimo —el piso de la corporación sin margen, o empatar al ganador en un cargo uninominal—; *probable* (amarillo) es nuestra medición, la que se guarda como meta por defecto; *posible* (verde) es lo que exige un gran trabajo: la cifra repartidora con el margen, con la que la lista gana una curul solo con los votos propios (sin reparto, referencia × 1,15). La fórmula NO va en la tarjeta —ahí va un mensaje que motive— sino en la ⓘ. El escenario elegido vive en `localStorage['c360-meta-escenario']` y **su número es el que se guarda en `campana.meta`** (el worker no conoce el escenario: `_c360NormalizarCampana` botaría un campo nuevo). Código: `META_ESCENARIOS` · `escenariosDe` · `mensajeMeta` · `elegirEscenario`. |
| **El electorado en tres paneles: perfiles · lectura · mapa** (`candidato-360-electorado.html`, 19-sep-2026) | La página vieja era una lista de secciones que nadie usaba para decidir. Ahora responde una sola pregunta: *¿a qué perfil de votante le hablo y dónde?* **Panel 01**: seis perfiles sexo × edad (H/M × 18-30 · 31-50 · 51+) con un índice **rinde** = peso del perfil entre quienes votan en las unidades donde la familia política de la campaña sacó más votos en 2023 ÷ su peso en el territorio entero; los tres más altos van marcados como viables. **Panel 02**: lectura del perfil elegido, sus cinco unidades donde más *le pega* y una sugerencia de canal por edad, rotulada como criterio de oficio y no como dato. **Panel 03**: el mapa del territorio (localidades en Bogotá, comunas en las 14 ciudades con cartografía, municipios si la corporación es departamental, puestos como círculos en el resto) coloreado por **le pega** = (concentración del perfil ÷ territorio) × (voto de la familia ÷ su promedio); lo ≥ ×1,15 **parpadea**. En Bogotá y Cali un clic baja a los barrios (mismos `.js` de `candidato-360-data/`, sin rotar y con callejero). Fuentes: `PERFIL_SEXO_EDAD_PUESTO.json` + `resultados-concejo-2023.json` (ciudades) · `asamblea-2023/dep/<dep>.json` (departamento) · `asamblea-2023/mun/<dep>-<mun>.json` (puestos, coordenadas del georef). ⚠️ **Si la familia exacta no tiene lista en el territorio se mide con sus vecinas del espectro** (`VECINAS` en `candidato-360-electorado.js`) y la página lo dice: el centro-derecha no existe en el Concejo de Bogotá 2023 porque Cambio Radical y La U quedan en el centro. ⚠️ El índice *rinde* sale cerca de ×1,00 en ciudades grandes con familias amplias (medido: 0,99-1,02 en Bogotá con cd+c+d); lo que discrimina es el mapa por unidad, no el ranking nacional de perfiles. ⚠️ Bogotá usa la misma ventana fija del CRM (`ventana` en `CIUDADES`): con Sumapaz en el encuadre, las 19 localidades urbanas quedaban en una uña. Las lecturas viejas (sexo, edad, campo/ciudad, familias, objetivo) siguen debajo, plegadas. |
| **Con qué se mide «dónde saca votos»: primero la LISTA del partido** (`armarPerfiles` en `candidato-360-electorado.html`, 29-sep-2026) | Quien se lanzaba al Concejo de Bogotá por la lista de Oviedo veía «Todavía no»: su partido no estaba en `PARTIDO_BLOQUE` (caía en `sc`) y la página solo sabía medir por familia. Ahora hay cascada, y cada paso se declara bajo el título de perfiles: **1)** la lista del partido en la misma corporación de 2023 (`E.calzaPartido`, mismo criterio que `huellaPartido` del CRM: nombre, contenido o todas las palabras propias; coalición por cualquiera de sus partes) · **2)** si no tuvo lista o no llegó al 1 %, **su lista a Cámara 2026 puesto por puesto** (`camara/partidos-puesto/{dep}.json`, de `tools/candidato-360/partidos/build_camara_puesto.py` — el mismo dato con el que el catálogo de partidos del CRM ofrece esa lista) · **3)** la familia: la del partido, la del espectro si va por firmas o, si el partido no tiene línea nacional, **la de su historial desde 2018** (partido de cada candidatura con slug ≥2018, bloque más repetido, desempate por la más reciente) · **4)** vecinas del espectro, como antes. Si el historial desde 2018 va por otra familia que la de ahora, se dice. Medido en Bogotá: lista de Oviedo 74.131 votos a Cámara = 2,6 %, más fuerte en Usaquén, Chapinero y Teusaquillo; Nuevo Liberalismo se mide con su lista del Concejo 2023 (16,6 %). ⚠️ La medida puede ser un `Set` de familias o una **función** nombre→sí/no (`esDe` en `candidato-360-electorado.js`); barrios y localidades leen los votos con `votosPuesto`, que sabe de las dos fuentes. ⚠️ La lista de Oviedo quedó en **centro** en `partidos-bloques.js` (compitió en la consulta de la derecha, pero su voto de 1V 2026 se fue dos tercios a Cepeda y un quinto a Fajardo). Otros partidos nuevos de 2026 siguen en `sc` (Alianza por Colombia, Ahora Colombia, Colombia Segura y Próspera, Patriotas): con el paso 2 ya no hace falta clasificarlos para medir su lista, pero sí para la familia. |
| **El copy del briefing vende, por corporación y familia** | Apagado, el panel 03 no describe el producto: lo vende con un párrafo por corporación (`BRIEFING_COPY_CORP`, con el territorio de la campaña) y una frase por familia política (`copyBriefing`: izq/ci como oposición al gobierno nacional, d/cd como cercanos a él, centro con el argumento del dato, firmas o sin línea con la información como ventaja). Encendido vuelve al copy descriptivo. ⚠️ Asume presidente de derecha en 2026-2030; si cambia el mapa político hay que reescribir las frases. |

## 5. Arquitectura

### Páginas

| Archivo | Qué es |
|---|---|
| `candidato-360.html` / `.js` / `.css` | La aplicación: portada, búsqueda, ruta, wizard y CRM. El `.js` es el grueso (~3.400 líneas) y está dividido en secciones numeradas con comentarios de cabecera. |
| `candidato-360-medios.html` | Panel 04: sus tres ideas contra la prensa de su territorio. |
| `candidato-360-redes.html` | Panel 05: sus cuentas, buscadas y validadas. |
| `candidato-360-arquetipos.html` | Panel 05 (sep-29-2026; antes era un modal del CRM): los arquetipos del territorio en Medellín y Cartagena. El que manda en su votación (ficha con la tarjeta gráfica, palancas y temas en Cartagena), el reparto de su voto 2023 → 2027, el mapa de barrios por arquetipo dominante (con «solo donde tiene votos» si los tiene), tablas por comuna/localidad y por barrio, y todos los arquetipos de la ciudad. Sin votos propios en la ciudad describe la ciudad y lo dice. ⚠️ En Cartagena 2023 es proyección retrospectiva y 2027 simulación: se rotula en cada control. ⚠️ El mapa de Cartagena encuadra la ventana urbana (`zoomSnap .25`), no el bounds con las islas. **Tres lentes** (barra «Leer desde»): sus votos (si tiene en la ciudad) · **su partido o familia** (`C360ArqLectura.huella`: lista al Concejo 2023 → si no, su lista a Cámara 2026 → si no, la familia y sus vecinas; mismo criterio del panel del electorado) · la ciudad entera. Sin votos propios abre en la de su partido. Con una lente de votos sale **el arquetipo más afín** (`afinidad`: peso en esa votación ÷ peso en la ciudad, mínimo 8 % del voto — con 5 % ganaba un arquetipo de 6 % contra 5 %, que es ruido) y cada tarjeta lleva su afinidad. Medido: Pacto en Cartagena, sin lista al Concejo 2023 → Cámara 2026 (28 %), más afín productivo-pragmático ×1,18. |
| `candidato-360-electorado.html` | Panel 07: el análisis del electorado, con figuras y gráficos. |
| `candidato-360-endoso.html` | Panel 08: endoso de aliados. Suma excandidatos (tasa contra a quién apoyaron) y líderes sin candidatura (zona marcada en el mapa, rendimiento de quien apoyaron contra su comuna), sin contar dos veces a quien votó por varios. La lista vive solo en el navegador —los nombres de los líderes son datos de terceros— y Candi lo dice al guardar. Muestra cuánto cubre de cada escalón de la meta (el CRM deja los escalones en el navegador), dónde le suma votos nuevos y baja un CSV; el plan del Día D marca los puestos donde pesan los aliados. |
| `candidato-360-contendientes.html` | Panel 10: sus rivales probables hasta la inscripción de 2027. Plano de familia política contra afinidad territorial (cuánto rinde cada rival en los puestos de su base), la escalera dentro de su lista, el mapa de disputa (comunas, barrios, municipios o puestos, con la segunda capa de «todo el territorio» en un salto), la tabla y una ficha por rival con su historial y la meta de su lista. La tarjeta 10 del CRM pinta el mismo plano (en vitrina, solo los tres primeros con nombre). Plan en `tools/candidato-360/contendientes/PLAN.md`. |
| `admin-c360-contendientes.html` | La bandeja de la revisión mensual de contendientes (solo administrador, tarjeta RR-ADMIN-004 del dashboard): aspirantes nuevos y cambios de aval que el proceso del día 1 encontró en prensa, territorio por territorio, con sus titulares; aprobar, descartar y sellar la revisión del mes. Nada de prensa entra a una tarjeta sin pasar por aquí. |
| `candidato-360-perfil.html` | El método: cómo se lee un electorado sin violar el secreto del voto. |

**Mapas: el globo en una línea, el detalle en una ficha fija** (electorado y arquetipos, sep-29-2026). Con siete renglones en el tooltip, Leaflet lo apretaba a una columna de dos palabras y no se leía. Ahora el globo dice nombre y el valor de lo que se pinta (`white-space:nowrap`), y todo lo demás va en `.mapa-ficha` / `.aq-ficha`, arriba a la derecha del mapa (debajo en ≤640 px), que se llena al pasar el cursor o al tocar. ⚠️ En el electorado, el clic en una unidad con barrios sigue bajando a sus barrios: ahí la ficha sale solo con el cursor. Si se agrega un mapa nuevo con mucho dato por zona, mismo patrón.

### Módulos compartidos

| Archivo | Qué resuelve |
|---|---|
| `cand-index.js` | El índice de candidaturas: baja las fuentes de S3, normaliza nombres, agrupa personas y resuelve `slug → URL` del JSON mesa a mesa. |
| `partidos-bloques.js` | **Un solo diccionario** partido/coalición/movimiento → familia ideológica (izq, ci, c, cd, d, sc). Lo usan el mapa de alcaldías y Candidato 360: dos diccionarios serían dos opiniones. |
| `candidato-360-electorado.js` | Las cuentas del electorado (perfil del censo, ideología del territorio, votación objetivo). Compartido por la tarjeta 07 y su página: si cada pantalla calculara por su lado, darían cifras distintas sobre lo mismo. Devuelve **datos**, no texto. |
| `candidato-360-endoso.js` | El endoso de aliados (`window.C360Endoso`): recorta los votos del aliado al territorio, mide la tasa contra a quién apoyó y suma. Lo usan la tarjeta 08 y su panel; no conoce el CRM ni el DOM (el recorte y el nombre de las zonas se le pasan). Prueba: `node tools/candidato-360/prueba-endoso.mjs` (`--sin-red` para solo la lógica). |
| `candidato-360-contendientes.js` | Los contendientes (`window.C360Contendientes`, fases 1-5 de `tools/candidato-360/contendientes/PLAN.md`; lo usan la tarjeta 10 y su panel): rivales probables por fuente (A ganó la curul en 2023 · B compitió ahí · C tiene votos ahí de otra elección), familia política con la franja «no sabemos», afinidad territorial con su base, presión competitiva en tres niveles, la escalera dentro de su lista y el mapa de disputa por puesto. `leer` es la entrada única (tarjeta y panel la llaman con las mismas entradas), `cargar` hace la IO, `evaluar` el cálculo, `disputaPorUnidad` el mapa por barrio, comuna o municipio y `planoSVG` el dibujo, sin DOM. Usa `VoteTarget.reparto` (el mismo reparto de la meta) y `C360DiaD.puestosDestino`; sin archivos por comuna lee la matriz nacional `matriz-puesto/{corp}-{año}/{dde}[-{mme}].json` (fase 4, `tools/candidato-360/contendientes/build_matriz_puesto.py`; si no está, baja el archivo de cada rival). Prueba: `node tools/candidato-360/prueba-contendientes.mjs` (`--sin-red` para solo la lógica, `MATRIZ_LOCAL=1` para leer la matriz del disco). |
| `candidato-360-arq-lectura.js` | La lectura de arquetipos (`window.C360ArqLectura`): qué ciudad (`ciudadDe`, con la campaña guardada — ⚠️ una candidatura NUEVA no pasa por el formulario de la ruta con historial y antes la tarjeta salía apagada: Nury en la Alcaldía de Cartagena, sep-29), el reparto de sus votos por arquetipo (Medellín por coordenada del puesto en el polígono DAP; Cartagena por nombre de barrio y con la MEZCLA de ocho) y la geometría para el mapa. La usan la tarjeta 05 y su página: salió de `candidato-360.js` para que las dos no digan cifras distintas. |
| `candidato-360-panel.js` | El chasis de los paneles: sesión, vínculo, muro, territorio y helpers de formato. |
| `candidato-360-candi.js` (+ `assets/candidato-360/candi/`) | Candi, la guía (Luna): dock, globo, panel de preguntas (`POST /c360/candi`) y el adaptador de los reproductores de Astra (`candi-atletica.js` v4 · `candi-hueso.js` v2). **Pensando** (gafas, 6 s) para la espera de un cálculo de la página (`Candi.calculo`); **investigando** (lupa, 4,8 s, 29-sep) solo mientras una pregunta escrita va al worker: una por pregunta, sin bucle, nunca junto con pensando (la segunda espera a `cuandoAtenta`), y si la respuesta llega antes se la deja terminar. **Descanso**: tras 20 s sin actividad cruza la pantalla de lado a lado y alterna derecha → izquierda → derecha; sale desde la Candi visible (dock, echada o sentada en la franja) y, si despierta lejos de casa, se queda sentada ahí (`rincon`). Panel abierto, pregunta en vuelo, cálculo o pantalla baja lo inhiben con `enable(false)`; un solo temporizador, el del reproductor. ⚠️ El adaptador sobreescribe `layout`/`play`/`stop` de la instancia: la casa es el extremo derecho; si ya está en el extremo de destino se invierte el lado (si no, camina en el sitio); y `stop` solo restaura el sprite si de verdad caminaba — la restauración hace `seek(4800)` y pisaba la lupa recién arrancada. ⚠️ `candi:complete` solo sale al terminar la ENTRADA: esperar solo ese evento tras una reacción colgaba para siempre. ⚠️ En el panel del navegador la pestaña va oculta: rAF, `resize` y el `change` de las media queries no llegan; se verifica con un rAF de mentira y `document.hidden` forzado. Pruebas: `node assets/candidato-360/candi/test-hueso.cjs` y `node tools/candidato-360/prueba-candi.mjs`. |
| `vote-target.js` | La meta de votos: referencia territorial, censo, participación y margen. Reparte las curules como el art. 263 (umbral, cifra repartidora) contando el **voto de lista** y las **listas cerradas**, y reservando la curul del estatuto de oposición en concejos y asambleas. Sin partido la referencia no es el piso de la corporación sino lo que costó entrar por una lista típica, o por una de la familia política elegida. |
| `partidos-bloques.js` + `candidato-360-data/partidos/<dep>.js` | Catálogo de organizaciones por departamento para el sugeridor. |
| `data-client.js`, `platform-config.js` | Dónde viven los datos públicos y la API privada. Ningún secreto en el navegador: este repo es público. |

### Datos

Base pública: `https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output/`

| Ruta | Qué trae |
|---|---|
| `<corp>-<año>/index-*.json` | Índice de candidaturas (nombre, slug, corporación, partido, votos) y, desde 2026-09, `listas[]` por circunscripción: `lista` (voto solo por el partido), `personal`, `total` y `cerrada`. Sin eso una lista cerrada no existe en el reparto de curules: ver §regenerar. |
| `<corp>-<año>/<slug>.json` | Una candidatura mesa a mesa (`mesas[]` con dep, mun, zona, puesto, votos). |
| `mapas-2026/DEPARTAMENTOS2.json` | Colombia por departamentos. |
| `totales-puesto/<corp>-<año>.json` | Votos válidos, votantes y blanco por puesto de las 26 elecciones con candidaturas (2011-2023 y Congreso 2014-2022), comprimidos. Los usa la regresión del endoso; los genera `tools/candidato-360/endoso/build_totales_puesto.py`. |
| `mapas-2026/Departamentos-mps/<dep>.json` | Un departamento por municipios (trae `mun_elec`, el código **electoral**, y `mpio_cnmbr`). |
| `mapas-2026/Ciudades-COM-LOC/` | Comunas y localidades de las ciudades con cartografía. |
| `mapas-2026/PUESTOS_GEOREF.csv` | Cada puesto de votación: coordenada, barrio, comuna y **censo por sexo**. El nombre de comuna viene con variantes («CIUDAD BOLÍVAR» y «CIUDAD BOLIVAR», «COMUNA 7 NORESTE» y «COMUNA 7 NOR ESTE»): los generadores las unifican, si no una JAL sale partida en dos. |
| `DESCARGAS/raw/<corp>/<año>/GCS_*.csv` | Los archivos crudos de la Registraduría, mesa a mesa. De ahí salen todos los índices. |
| `mapas-2026/CENSO_EDAD_PUESTO.json` | Censo por edad y puesto (cuatro bandas). Publicado el 19-sep-2026 con `construir-edad.mjs`. |
| `mapas-2026/PERFIL_SEXO_EDAD_PUESTO.json` | **Sexo × edad por puesto** (H/M × 18-30 · 31-50 · 51+): sufragantes de la 1V de 2022 (`Edadygenero` de la Registraduría). Lo produce `tools/candidato-360/perfil/construir-sexo-edad.py`. Es lo que arma los perfiles de votante de la página del electorado. |

#### Regenerar los datos de 2023 (el voto de lista)

Los índices que están hoy en S3 se construyeron descartando la fila `COD_CAN=0`
del archivo de la Registraduría, que es **el voto solo por la lista** y, en una
lista cerrada, todo su voto. Con eso el Pacto Histórico no existía en el Concejo
de Bogotá y sus 7 curules se les repartían a las demás listas. Los generadores
ya lo corrigen; falta volver a correrlos:

```
bash tools/analisis-candidato/regenerar_2023.sh          # genera y verifica
bash tools/analisis-candidato/regenerar_2023.sh --subir  # y sube a S3
```

Necesita los CSV crudos en `Bases de datos/` (`FINAL SUBIDA GCS/GCS_2023TER.csv`,
`GCS_2023JAL.csv` y `PUESTOS_GEOREF.csv`): son varios GB, no están en el repo ni
en S3. `verificar_listas_2023.py` es la prueba de aceptación: cuadra cada lista
con sus candidatos y exige que el reparto de Bogotá dé la composición real del
cabildo 2024-2027. Si no pasa, el script no sube nada.

**Hecho.** Los índices de S3 ya traen `listas`, subidos por el workflow el
2026-09-20. En todo el país hay **888 listas cerradas en concejo, 591 en JAL y
48 en asamblea**, el reparto de Bogotá reproduce el cabildo real y la
participación quedó corregida (Bogotá 2023: 51,6 % donde antes decía 38,9 %).

`vote-target.js` conserva el respaldo de leer el voto de lista de un archivo
aparte (`LISTAS_2023_URL`) por si alguna vez se sirve un índice viejo, pero ya
no hay archivo que leer: `candidato-360-data/listas-2023.json` se borró cuando
dejó de hacer falta.

Para volver a hacerlo (otra elección, o una corrección), el camino está montado:

La subida necesita credenciales de escritura en el bucket, que el entorno de
trabajo remoto no tiene: ahí las variables `AWS_*` están tomadas por el proxy de
red (`AWS_ACCESS_KEY_ID` vale literalmente «proxy…») y un PUT responde
`InvalidAccessKeyId`. Hay dos caminos:

**GitHub Actions** (la credencial vive en los secretos del repositorio y no pasa
por ninguna otra máquina). El workflow «Regenerar índices de 2023» baja los CSV
crudos, genera, verifica, guarda lo generado como artefacto y sube. Necesita los
secretos `RR_S3_KEY_ID` y `RR_S3_SECRET` de un usuario IAM cuya política es
`tools/analisis-candidato/politica-iam-subida.json`: solo `s3:PutObject` sobre
los tres prefijos de 2023, sin borrado y sin tocar nada más del bucket.

**Desde la máquina**, con `aws` configurado:

```
bash tools/analisis-candidato/regenerar_2023.sh --solo-indice --subir
```

Los JSON por candidato no cambian con esto, así que no hay que resubir los
94 mil.

`--solo-indice` reconstruye solo los índices, sin reescribir los 94 mil JSON por
candidato, que no cambian.

`gcs_columnas.py` resuelve las columnas por nombre: el GCS territorial trae 19
columnas y el de JAL 16, y leerlas por posición fija tomaba `DES_DDE` como
código de municipio sin fallar, solo produciendo basura.
| `asamblea-2023/dep/<dep>.json` | Resultados de asamblea por **municipio**: la única elección que baja a todos los municipios del país con voto por partido. |
| `concejo-2023/resultados-concejo-2023.json` | Concejo por **comuna**, solo en once ciudades. |
| `candidato-360-data/` (en el repo) | Logos de partido, barrios aproximados, catálogos por departamento y los Excel de homónimos. |

⚠️ **Dos sistemas de códigos.** El *electoral* (el de la Registraduría, el que
viene en los slugs y en las mesas) y el *DANE/Divipola* (el de la cartografía).
No coinciden: Antioquia es `01` electoral y `05` DANE. Los archivos de
`Departamentos-mps` traen los dos, y por eso son los que traducen.

### El Worker (`rr-auth`, repo aparte)

`/c360/me` sesión y vínculo · `/c360/vinculo` crear · `/c360/campana` guardar la
campaña · `/c360/escucha` ideas y redes · `/c360/briefing` · `/c360/redes`
validación de cuentas · `/c360/planes`. Los administradores (`ADMIN_EMAILS`)
pueden abrir cualquier candidatura sin vincularse.

**Contendientes · revisión mensual** (fase 5; lógica en `src/c360-contendientes.js`,
prueba `node test/c360-contendientes.test.mjs`): `GET /c360/contendientes?t=`
la revisión sellada del territorio (sesión + acceso; la revisión es del
territorio, no de la cuenta) · `POST /c360/contendientes/conocidos` el panel le
cuenta qué rivales del registro calculó (acceso + vínculo, una vez al día, no
escribe si nada cambió) · tres de servicio en la tabla `SERVICIO` con el
secreto del briefing: `/c360/contendientes/{inventario,propuesta,sellar}` ·
`GET|POST /c360/admin/contendientes` la bandeja (aprobar, descartar, sellar).
El cron es `tools/candidato-360/contendientes/revisar.py` en
`.github/workflows/candidato-360-contendientes.yml`, el día 1 a las 07:00.
KV: `c360:cont:{conocidos,prop,ver,ultima}:<territorio>[:<AAAA-MM>]`.

## 6. Las piezas con método propio

Cada una tiene su README en `tools/candidato-360/<tema>/`:

| Tema | Qué decide | Dónde |
|---|---|---|
| **personas** | Cuándo dos candidaturas son la misma persona | `personas/` |
| **meta** | Cuántos votos se necesitan para ganar o para una curul | `meta/` |
| **mapas** | Las escalas del mapa (municipio, comuna, barrio, puesto) y el mapita del lugar | `mapas/` |
| **saltos** | Cómo se reparte la meta cuando se cambia de corporación (arraigo empírico) | `saltos/` |
| **partidos** | Familias ideológicas, coaliciones y movimientos regionales | `partidos/` |
| **firmas** | Cuántas firmas y dónde recogerlas | `firmas/` |
| **perfil** | El electorado: sexo, edad, campo y ciudad, y la votación objetivo | `perfil/` |
| **arquetipos** | Qué mueve el voto en cada barrio (Medellín, Proyecto DC) | `arquetipos/` |
| **endoso** | Cuántos votos le pueden pasar sus aliados (excandidatos y líderes de zona). La retención del voto propio se mide con `endoso/calibrar.mjs`, que reescribe la tabla del motor | `endoso/PLAN.md` |
| **contendientes** *(fases 1-5: motor, tarjeta 10, panel, mapa, matriz nacional, prensa y revisión mensual)* | Contra quién compite (plano familia × afinidad territorial), dónde se pelea el voto (mapa de disputa por puesto), el rival dentro de la propia lista y la revisión mensual | `contendientes/PLAN.md` |
| **equipo** *(plan, sin construir)* | Cómo la meta se vuelve zonas, sub-metas y tareas de un equipo sin custodiar su base de contactos (cuentas solo para quien coordina; testigos y líderes fuera del servidor) | `equipo/PLAN.md` |
| **barrios-voronoi** | Barrios aproximados donde no hay cartografía oficial | `barrios-voronoi/` |
| **logos** | Los logos de partido y su manifiesto | `logos/` |
| **briefing / redes** | El correo cada tres días y la validación de cuentas | `briefing/`, `redes/` |

Tres que conviene conocer antes de tocar nada:

- **Familias políticas.** El diccionario clasifica partidos; las coaliciones se
  resuelven por sus partes y los movimientos regionales se **miden** (de dónde
  vienen los candidatos que llevaron ese aval en otras elecciones). ASI, MAIS y
  AICO entran por la identidad del partido, pero están marcados como *aval
  amplio*: prestan su aval y sus listas vienen de todas las familias —el bloque
  más repetido entre las otras candidaturas de quienes se lanzaron con la ASI
  en 2023 reúne apenas el 35 %—, y la ficha lo advierte. Sin bloque queda el
  9,1 % de los votos de asamblea 2023 (era 22,3 %).
- **Firmas.** 20 % del censo del territorio dividido por los cargos a proveer
  (uno, en alcaldía y gobernación), con tope de 50.000 (Ley 130/1994 art. 9 y
  las resoluciones de la Registraduría). En municipios pequeños **piden más
  firmas que los votos con los que se gana**, y la tarjeta lo dice en vez de
  dejar pensando que el cálculo está mal.
- **Votación objetivo.** Los votos que faltan para la meta no se parecen a la
  base —esos ya los tiene— sino al territorio del que van a salir, así que el
  perfil objetivo es el promedio de los dos pesado por votos.

## 7. Convenciones del código

- **Sin framework, sin build.** HTML + CSS + JS plano servido por GitHub Pages.
  Todo lo pesado se pide a S3 y se cachea en memoria por sesión.
- **Los comentarios explican el POR QUÉ**, no el qué. Si un `if` existe por un
  caso real (los corregimientos de Medellín van 17-21 en la Registraduría y
  50-90 en la cartografía del DAP), eso se escribe ahí.
- **En español**, incluidos los nombres de funciones nuevas. Conviven con los
  nombres viejos en inglés; no se renombra por renombrar.
- **Nada de secretos en el navegador**: el repo es público. Las llaves viven en
  el Worker.
- **Cache busting a mano**: al tocar un `.js` o `.css` hay que subir el `?v=`
  en todas las páginas que lo cargan.
- **Cada cambio con prueba.** Las pruebas son Playwright contra el HTML real
  con **todo lo remoto simulado** (`page.route`), así que corren sin red y sin
  servidor. Están en `tools/candidato-360/prueba-*.mjs` y se corren una por
  una: `node tools/candidato-360/prueba-ruta.mjs`.
- **Git**: mensajes que cuentan la decisión, no el diff.

### Las pruebas (27 suites)

```
prueba-ruta (26)        la ruta paso a paso, el mapa del lugar, la capital
prueba-perfil (17)      la página del electorado y sus cinco lecturas
prueba-partido (27)     sugeridor, logos, filtro por departamento
prueba-meta (31)        la meta de votos en sus escenarios
prueba-listas (15)      voto de lista, listas cerradas y curul de oposición
prueba-contendientes (89)  el motor de contendientes: 63 sin red + 26 contra S3 (MATRIZ_LOCAL=1 lee la matriz del disco); Node
prueba-contendientes-panel (40) el panel 10 (mapa, prensa, revisión, agregar a mano) y la tarjeta 10 en vitrina; CAPTURAS=<carpeta> guarda la página
prueba-firmas (16)      cuántas firmas y dónde
prueba-frases (18)      el banco de frases del punto de partida
prueba-mapa (15)        Bogotá: ventana urbana, callejero, censo
prueba-arquetipos (15)  las tarjetas 06 y 07
prueba-vitrina (14)     lo que ve un visitante sin cuenta
prueba-puestos (11)     el nivel de puestos y su desglose
prueba-jal-localidad (15) la JAL se elige por localidad, no por ciudad
prueba-captura (13)     la captura de redes, apagada y forzada
prueba-pais (7)         el selector de país en la portada
…y otras once (ciudades, colores, salto, territorio, paneles, wizard, nacional)
```

## 8. Frentes abiertos

1. ~~`CENSO_EDAD_PUESTO.json` sin publicar~~ **Publicado (19-sep-2026)**, junto con
   `PERFIL_SEXO_EDAD_PUESTO.json`. Regenerar los dos:
   ```
   node tools/candidato-360/perfil/construir-edad.mjs --w26="Bases de datos/output_edad_1v/w26-puesto.csv"
   python3 tools/candidato-360/perfil/construir-sexo-edad.py
   aws s3 cp <archivo> s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/mapas-2026/<archivo> --content-type application/json --cache-control "public, max-age=3600"
   ```
2. **Homónimos.** 131 casos en Antioquia y 83 en Bogotá esperan revisión
   humana (`candidato-360-data/homonimos/`). Con eso se corrige la unificación
   por nombre de tres componentes.
3. **Logos fuera de Bogotá.** Solo existe la carpeta `16`, que hace de catálogo
   nacional. Un departamento con logos propios manda sobre ella.
4. **Arquetipos solo en Medellín.** La cartografía emocional del Proyecto DC
   cubre 152 barrios de Medellín; fuera de ahí la tarjeta se apaga y lo dice.
5. **Movimientos regionales sin clasificar (9,1 %).** Los que no dejan rastro
   suficiente. Bajar el umbral de `clasificar-locales.mjs` sube la cobertura y
   baja la confianza: es una decisión, no un bug.
6. **`saltos-arraigo.json`** (el estudio empírico del salto de corporación)
   está calculado pero no publicado; sin él, el reparto usa el respaldo.

## 9. Si va a proponer cambios

Lo que más ayuda, en orden:

1. **Discutir los métodos**, no el estilo: la clasificación ideológica, la
   fórmula de la meta, el reparto de firmas, el perfil objetivo. Cada uno tiene
   su README con el criterio y sus números.
2. **Traer datos que falten**: censo por edad, cartografía barrial de otras
   ciudades, logos por departamento, resultados por comuna fuera de las once.
3. **Buscar el caso que rompe**: un municipio sin comunas, una candidatura sin
   mesas, un departamento con un solo municipio, una coalición escrita de otra
   forma. Casi todos los bugs de este producto han sido eso.

Lo que no: convertirlo en un predictor, estimar lo que no está publicado, o
presentar como dato de la persona lo que es del territorio.
