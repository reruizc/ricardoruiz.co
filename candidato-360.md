# Candidato 360

> Documento de trabajo del producto. Está escrito para que alguien —persona o
> modelo— pueda entender **qué es, por qué está hecho así y dónde tocar** sin
> leer 4.000 líneas de JavaScript primero. Si va a proponer cambios, lea
> primero «Las reglas que no se negocian»: casi todo lo demás es discutible.
>
> **Si vienes a hacer lo gráfico (Astra): lee §1, §3 y luego §10**, que es tu
> brief: identidad visual, piezas que existen, especificación de Candi, formato
> de entrega y lo que no se puede hacer.
>
> Este archivo es la **única** documentación de Candidato 360: lo que antes
> vivía en `CLAUDE.md` está ahora en §11 (bitácora técnica). Los planes por
> módulo siguen en `tools/candidato-360/<tema>/`.
>
> Última revisión: 22 de octubre de 2026.

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
                                  CRM (tablero, 11 tarjetas)
                                        ↓
   paneles propios: 04 escucha · 05 arquetipos · 06 electorado
                    08 endoso · 09 Día D · 10 contendientes
```

**La ruta (paso 2)** hace *una pregunta por tarjeta*, con salto de animación y
botón «Atrás»:

```
¿misma corporación?
   ├── sí  → ¿con qué partido?
   └── no  → ¿a cuál?  →  ¿dónde?  →  ¿con qué partido o por firmas?
```

**El CRM** abre con «Punto de partida» (el párrafo que conecta el historial con
la campaña) y once tarjetas: **01** mapa del historial electoral · **02**
objetivo de votos · **03** briefing cada 3 días · **04** escucha social ·
**05** arquetipos del territorio · **06** perfil del votante · **07**
recolección de firmas (solo si va por firmas a un cargo uninominal) · **08**
endoso de aliados · **09** el día de la elección · **10** sus contendientes ·
**11** estrategia (con su vista ampliada dentro del mismo CRM).
Sin cuenta pagada el CRM abre en **vitrina** (§11, «La regla del producto»).

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
| **Asamblea y gobernación no preguntan municipio** (2-oct-2026, lo encontró Ricardo probando una gobernación en el Huila) | Se eligen en todo el departamento. Antes, al elegir el departamento `municipioImplicito` destapaba el campo para cualquier corporación (solo lo escondía cuando el departamento tiene un municipio), el mapa decía «Toque su municipio» aunque en una departamental no se puede tocar, y el municipio de un intento anterior por concejo quedaba elegido y se colaba en la campaña guardada («Neiva · Huila» para una gobernación). Ahora `loadCampaignMunicipalities` sale temprano en una departamental (esconde el campo y vacía el desplegable), `updateCampaignTerritory` lo vuelve a llamar al cambiar de corporación, la pista del mapa exige un `select` de municipio, y `campanaActual` solo guarda municipio en concejo · alcaldía · JAL y localidad en JAL. El wizard de candidatura nueva ya lo hacía bien (`updateTerritory` solo carga municipios si la elección es municipal); solo heredaba la pista equivocada del mapa. |
| **Candi se presenta una vez por pestaña y comenta cada pantalla una sola vez** (30-sep-2026, pedido de Ricardo) | Cada módulo es una página aparte, así que entraba caminando y decía «¡Hola! Soy Candi…» en cada clic del tablero y al volver a la portada. Ahora `sessionStorage['candi-sesion-v1']` guarda `{presentada, dichas[]}`: la primera carga de la pestaña hace la entrada completa con presentación; las siguientes arrancan con `mascota.idle()` (ya sentada, sin caminar) y el globo dice el **`saludo` de esa vista** —una frase complementaria al HTML, no lo que ya dice el título— solo si no se dijo antes en la sesión; si ya se dijo, callada. Dentro de `candidato-360.html` el cambio de pantalla (`showScreen`) también dispara el comentario de la nueva vista (`alCambiarVista`, colgado del `MutationObserver` de `.screen`) y oculta el de la anterior. Todas las vistas de `VISTAS` traen `saludo` (portada, buscador, ruta, wizard, CRM, electorado, arquetipos, Día D, endoso, contendientes). `sessionStorage` a propósito y no `localStorage`: otro día o en otra pestaña merece la entrada otra vez. ⚠️ `idle()` no emite `candi:complete`, así que en la carga «ya sentada» el descanso del hueso (`montarDescanso`) y el globo se enganchan a mano. |
| **Aval: partido o firmas** | A alcaldía y gobernación se llega de las dos maneras. Por firmas no hay partido: se pregunta el espectro (5 posiciones) y con eso se ordena la recolección. |
| **Candi comenta según lo que la persona escogió** (`TEMAS` en `candidato-360-candi.js`, 1-oct-2026, pedido de Ricardo) | El `saludo` es uno por vista y fijo; los **temas** dependen de la campaña: `perfil()` lee a demanda corporación, aval (partido · firmas · indeciso), historial, si cambia de corporación (`salto`), la ciudad y qué módulos existen para ella (arquetipos en Medellín, Cartagena y Bogotá, barrios en Bogotá · Medellín · Cali · Cartagena, firmas solo en cargo uninominal por firmas). Lo lee del formulario en la ruta y el wizard, y de `CAMPANA_ACTUAL` / el vínculo después. Tres disparadores: **cambio** de selección en la ruta o el wizard (de una, ~450 ms tras la ráfaga) · en el CRM, **detenerse en una tarjeta** (≥60 % visible 2,5 s, `IntersectionObserver` sobre su `<article>`) · un **tema general** ~30 s después del último globo, máximo tres por carga. Nunca interrumpe (panel abierto, cálculo o globo ocupado), 25 s mínimo entre comentarios, cada tema una vez por pestaña (`memoria.temas` en el mismo `candi-sesion-v1`). Todos salen además en el panel bajo «Para tu campaña» y, con `chip`, como pregunta sugerida. Las preguntas escritas mandan `contexto.seleccion` (solo categorías, sin nombre ni lugar exacto) y el worker la pone en el prompt y en la llave de la caché (`C360_CANDI_PROMPT_V` v8). ⚠️ Los temas afirman cosas del producto: al cambiar un módulo, revisar su tema. Para depurar: `Candi.perfil()` y `Candi.temas()` en la consola. ⚠️ El `IntersectionObserver` no dispara en el panel del navegador (pestaña oculta). |
| **La capital, de primeras** en el desplegable de municipios | Concentra las candidaturas. La regla sale del dato (código Divipola `001`), no de una tabla de 33 capitales. |
| **Nombres de lugar en tipo oración** | La Registraduría escribe «MEDELLÍN» y los departamentos llegan «Antioquia»: media línea gritando. Solo cambia la presentación; el valor guardado sigue siendo el original, que es la llave contra la Divipola. |
| **Logos de partido** en la elección del aval | Un nombre en mayúsculas no se reconoce; el logo sí. |
| **La meta en cuatro escalones** (inminente · probable · posible · deseado), no un número | Un candidato no sabe si 21.000 es mucho o poco. Los cuatro salen de la misma proyección (censo × participación) y van de menor a mayor esfuerzo: *inminente* (rojo) = **la mitad del probable**, «la votación más baja que puede sacar» con una campaña seria (regla de Ricardo); *probable* (amarillo) = nuestra medición —lo que costó entrar por su lista o una típica en 2023, o lo que sacó quien ganó en un cargo uninominal, llevado a 2027— y es la meta por defecto; *posible* (verde) = el último elegido de **la siguiente lista más exigente de 2023** (la primera que supera en 25 % al probable), traído a 2027 con el margen; si ninguna queda en medio, la media geométrica entre probable y deseado; *deseado* (violeta) = **la cifra repartidora**, arrastrar la curul solo con los votos propios (sin reparto, la referencia × 1,15). La fórmula NO va en la tarjeta —ahí va un mensaje que motive— sino en la ⓘ. El escenario elegido vive en `localStorage['c360-meta-escenario']` y **su número es el que se guarda en `campana.meta`** (el worker no conoce el escenario: `_c360NormalizarCampana` botaría un campo nuevo). Código: `META_ESCENARIOS` · `escenariosDe` · `mensajeMeta` · `elegirEscenario`. Cifras medidas en §11, «Meta de votos · cuatro escalones». |
| **El electorado en tres paneles: perfiles · lectura · mapa** (`candidato-360-electorado.html`, 19-sep-2026) | La página vieja era una lista de secciones que nadie usaba para decidir. Ahora responde una sola pregunta: *¿a qué perfil de votante le hablo y dónde?* **Panel 01**: seis perfiles sexo × edad (H/M × 18-30 · 31-50 · 51+) con un índice **rinde** = peso del perfil entre quienes votan en las unidades donde la familia política de la campaña sacó más votos en 2023 ÷ su peso en el territorio entero; los tres más altos van marcados como viables. **Panel 02**: lectura del perfil elegido, sus cinco unidades donde más *le pega* y una sugerencia de canal por edad, rotulada como criterio de oficio y no como dato. **Panel 03**: el mapa del territorio (localidades en Bogotá, comunas en las 14 ciudades con cartografía, municipios si la corporación es departamental, puestos como círculos en el resto) coloreado por **le pega** = (concentración del perfil ÷ territorio) × (voto de la familia ÷ su promedio); lo ≥ ×1,15 **parpadea**. En Bogotá y Cali un clic baja a los barrios (mismos `.js` de `candidato-360-data/`, sin rotar y con callejero). Fuentes: `PERFIL_SEXO_EDAD_PUESTO.json` + `resultados-concejo-2023.json` (ciudades) · `asamblea-2023/dep/<dep>.json` (departamento) · `asamblea-2023/mun/<dep>-<mun>.json` (puestos, coordenadas del georef). ⚠️ **Si la familia exacta no tiene lista en el territorio se mide con sus vecinas del espectro** (`VECINAS` en `candidato-360-electorado.js`) y la página lo dice: el centro-derecha no existe en el Concejo de Bogotá 2023 porque Cambio Radical y La U quedan en el centro. ⚠️ El índice *rinde* sale cerca de ×1,00 en ciudades grandes con familias amplias (medido: 0,99-1,02 en Bogotá con cd+c+d); lo que discrimina es el mapa por unidad, no el ranking nacional de perfiles. ⚠️ Bogotá usa la misma ventana fija del CRM (`ventana` en `CIUDADES`): con Sumapaz en el encuadre, las 19 localidades urbanas quedaban en una uña. Las lecturas viejas (sexo, edad, campo/ciudad, familias, objetivo) siguen debajo, plegadas. ⚠️ **Desde el 27-sep el censo es el de 2026** (`CENSO_PUESTO_2026.json`, quién PUEDE votar) y las bandas pasaron a **18-30 · 31-60 · 61+**; el 28-sep la página ganó barra de control con pestañas y siete capas en el mapa (§11, «El perfil del votante con el censo de 2026»). |
| **Con qué se mide «dónde saca votos»: primero la LISTA del partido** (`armarPerfiles` en `candidato-360-electorado.html`, 29-sep-2026) | Quien se lanzaba al Concejo de Bogotá por la lista de Oviedo veía «Todavía no»: su partido no estaba en `PARTIDO_BLOQUE` (caía en `sc`) y la página solo sabía medir por familia. Ahora hay cascada, y cada paso se declara bajo el título de perfiles: **1)** la lista del partido en la misma corporación de 2023 (`E.calzaPartido`, mismo criterio que `huellaPartido` del CRM: nombre, contenido o todas las palabras propias; coalición por cualquiera de sus partes) · **2)** si no tuvo lista o no llegó al 1 %, **su lista a Cámara 2026 puesto por puesto** (`camara/partidos-puesto/{dep}.json`, de `tools/candidato-360/partidos/build_camara_puesto.py` — el mismo dato con el que el catálogo de partidos del CRM ofrece esa lista) · **3)** la familia: la del partido, la del espectro si va por firmas o, si el partido no tiene línea nacional, **la de su historial desde 2018** (partido de cada candidatura con slug ≥2018, bloque más repetido, desempate por la más reciente) · **4)** vecinas del espectro, como antes. Si el historial desde 2018 va por otra familia que la de ahora, se dice. Medido en Bogotá: lista de Oviedo 74.131 votos a Cámara = 2,6 %, más fuerte en Usaquén, Chapinero y Teusaquillo; Nuevo Liberalismo se mide con su lista del Concejo 2023 (16,6 %). ⚠️ La medida puede ser un `Set` de familias o una **función** nombre→sí/no (`esDe` en `candidato-360-electorado.js`); barrios y localidades leen los votos con `votosPuesto`, que sabe de las dos fuentes. ⚠️ La lista de Oviedo quedó en **centro** en `partidos-bloques.js` (compitió en la consulta de la derecha, pero su voto de 1V 2026 se fue dos tercios a Cepeda y un quinto a Fajardo). Otros partidos nuevos de 2026 siguen en `sc` (Alianza por Colombia, Ahora Colombia, Colombia Segura y Próspera, Patriotas): con el paso 2 ya no hace falta clasificarlos para medir su lista, pero sí para la familia. |
| **El copy del briefing vende, por corporación y familia** | Apagado, el panel 03 no describe el producto: lo vende con un párrafo por corporación (`BRIEFING_COPY_CORP`, con el territorio de la campaña) y una frase por familia política (`copyBriefing`: izq/ci como oposición al gobierno nacional, d/cd como cercanos a él, centro con el argumento del dato, firmas o sin línea con la información como ventaja). Encendido vuelve al copy descriptivo. ⚠️ Asume presidente de derecha en 2026-2030; si cambia el mapa político hay que reescribir las frases. |

## 5. Arquitectura

### Páginas

| Archivo | Qué es |
|---|---|
| `candidato-360.html` / `.js` / `.css` | La aplicación: portada, búsqueda, ruta, wizard y CRM. El `.js` es el grueso (~3.400 líneas) y está dividido en secciones numeradas con comentarios de cabecera. |
| `candidato-360-escucha.html` | Panel 04, escucha social: el cuestionario de entrada (qué redes, qué medios), sus cuentas validadas, la prensa de su territorio y del país, la saliencia mediática, el mapa de dónde pasa lo que se publica y la lectura por arquetipo (§11, «Escucha social»). Fusionó los paneles viejos de medios y redes. |
| `candidato-360-medios.html` · `candidato-360-redes.html` | Ya no son paneles: redirigen a la escucha (los enlaces pudieron quedar en marcadores o correos). |
| `candidato-360-arquetipos.html` | Panel 05 (sep-29-2026; antes era un modal del CRM): los arquetipos del territorio en Medellín, Cartagena y —desde el 14-oct-2026— **Bogotá**, donde son de comportamiento electoral medido y se recorren por **corporación** (Concejo · Alcaldía) en vez de por año, sin «Simulación» (§11, «Arquetipos de Bogotá en el panel 05»). El que manda en su votación (ficha con la tarjeta gráfica, palancas y temas en Cartagena), el reparto de su voto 2023 → 2027, el mapa de barrios por arquetipo dominante (con «solo donde tiene votos» si los tiene), tablas por comuna/localidad y por barrio, y todos los arquetipos de la ciudad. Sin votos propios en la ciudad describe la ciudad y lo dice. ⚠️ En Cartagena 2023 es proyección retrospectiva y 2027 simulación: se rotula en cada control. ⚠️ El mapa de Cartagena encuadra la ventana urbana (`zoomSnap .25`), no el bounds con las islas. **Tres lentes** (barra «Leer desde»): sus votos (si tiene en la ciudad) · **su partido o familia** (`C360ArqLectura.huella`: lista al Concejo 2023 → si no, su lista a Cámara 2026 → si no, la familia y sus vecinas; mismo criterio del panel del electorado) · la ciudad entera. Sin votos propios abre en la de su partido. Con una lente de votos sale **el arquetipo más afín** (`afinidad`: peso en esa votación ÷ peso en la ciudad, mínimo 8 % del voto — con 5 % ganaba un arquetipo de 6 % contra 5 %, que es ruido) y cada tarjeta lleva su afinidad. Medido: Pacto en Cartagena, sin lista al Concejo 2023 → Cámara 2026 (28 %), más afín productivo-pragmático ×1,18. **Barra «Ver» encima de «Leer desde», Cartagena y Medellín (1-oct-2026, `candidato-360-arq-modos.js`):** *Su lectura* (lo de siempre) · **Ver arquetipos** (`#arquetipos`) · **Simulación** (`#simulacion`). Un solo módulo con un **adaptador por ciudad** (`ADAPT.cartagena` / `ADAPT.medellin`): cada uno entrega barrios normalizados (`dom`, `mez`, `peso`, `resp`), arquetipos con su `sens`, el ancla del alcalde y la parte de la ficha propia de su estudio (`FICHA`); sumar otra ciudad es un adaptador más. ⚠️ **Producto general: ningún texto visible nombra a quien hizo la cartografía** (pedido de Ricardo, 1-oct); se dice «el estudio» o «la cartografía emocional». Los comentarios de código sí pueden. **·** **Ver arquetipos**: mapa por año 2015-2027, la leyenda pinta el peso de un arquetipo, y al tocar un barrio una ficha armada SOLO con el dato del estudio. ⚠️ Sin texto de internet: cientos de fichas no se pueden verificar y una que inventa un rasgo del barrio es peor que una que se queda en el dato. Cartagena: mezcla de ocho, emoción e intensidad por ciclo, cómo votó (estructura + % del más votado), volatilidad y sensibilidad; ⚠️ en un barrio heredado (131 de 211) la evidencia electoral es la de su barrio-fuente y la ficha lo dice. Medellín: perfil en los cinco (2015-2023 = puntaje relativo normalizado; 2027 = probabilidades de la proyección), quién ganó Alcaldía y Concejo, agenda y riesgo por elección, comportamiento probable 2027, y la lectura de campaña de `C360Arquetipos.FAMILIAS` (activa, desmoviliza, fuga, tono, canales) — por eso la página carga `candidato-360-arquetipos.js`. **·** ⚠️ **Medellín: el estudio ajustó a mano el arquetipo 2027 de 48 de 152 barrios**; la mezcla 2027 se reordena para que el ajustado quede primero (intercambia su peso con el que el modelo ponía arriba). Sin eso, el mapa con las palancas en cero ya diferiría del de «Ver». **·** **Simulación**: 13 palancas −5..+5 (las que ningún arquetipo de la ciudad califica no se muestran: en Medellín no salen vivienda ni ambiente) y 6 escenarios; `peso' ∝ peso·exp(K·resp·Σ empuje·(sens − media del tema))`, K = 0,085. Se centra en la media del tema a propósito: si todos son sensibles a un tema, moverlo cambia poco quién manda. `resp` crece con la volatilidad del barrio (Cartagena `0,55 + 3·vol`; Medellín `0,25 + 0,7·riesgo_cambio`, más baja porque sus perfiles son más parejos y con la misma respuesta un escenario volteaba tres de cada cuatro barrios). Lee el reparto de la lente activa si tiene votos. **·** **La palanca del alcalde está anclada a la cifra medida** (`ancla` de cada adaptador): el cero es la aprobación de gestión de hoy y cada paso son 6 puntos. Cartagena: **52 %** buena gestión de Dumek Turbay (imagen 74 %), Cartagena Cómo Vamos 2025, Cifras & Conceptos, oct-2025, n = 1.071, ±4,7 %. Medellín: **61 %** buena gestión de Federico Gutiérrez (imagen 74 %), Medellín Cómo Vamos 2025, Invamer, oct-2025, n = 1.800, ±2,31 % (base: quienes lo conocen). Se usa gestión y no imagen porque es lo que un barrio premia o castiga. ⚠️ Ninguna de las dos publica la gestión del alcalde por localidad o comuna (en Cartagena por la Ley 2494 de 2025): el ancla es la misma en toda la ciudad. ⚠️ El 76 % de «mayo de 2026» de Dumek que circula en prensa regional no dice qué firma lo midió: descartado. A quién mueve la palanca es regla nuestra (Medellín: la del simulador de Proyecto DC, continuidad y protección arriba, castigo abajo). **·** Medido (barrios que cambian de dominante): Cartagena, de 211 — escándalo 86 · inseguridad 23 · crisis de agua 18 · golpe económico 17 · alcalde en 22 % 8 · gestión que se ve 1. Medellín, de 152 — escándalo 63 · alcalde en 31 % 43 · inseguridad 15 · golpe económico 15 · crisis de agua 3 · gestión que se ve 0. **·** JSON de Cartagena: `build_cartagena.py` emite por barrio `evidencia`, `cercano`, `pct_dominante`, `trayectoria`, `familia_emocional` y `volumen.2027_rango` (492 KB, 39 KB en gzip; `?v=20261001`). |
| `candidato-360-electorado.html` | Panel 06, perfil del votante: perfiles sexo × edad, lectura, mapa con siete capas y escalas, crecimiento del censo 2023 → 2026. |
| `candidato-360-endoso.html` | Panel 08: endoso de aliados. Suma excandidatos (tasa contra a quién apoyaron) y líderes sin candidatura (zona marcada en el mapa, rendimiento de quien apoyaron contra su comuna), sin contar dos veces a quien votó por varios. La lista vive solo en el navegador —los nombres de los líderes son datos de terceros— y Candi lo dice al guardar. Muestra cuánto cubre de cada escalón de la meta (el CRM deja los escalones en el navegador), dónde le suma votos nuevos y baja un CSV; el plan del Día D marca los puestos donde pesan los aliados. |
| `candidato-360-diad.html` | Panel 09, el día de la elección: en cuántos puestos poner testigo, en cuáles y qué va a encontrar cada uno (hoja de vida del puesto). Nunca pide ni guarda datos del equipo (§11, «Módulo 09»). |
| `candidato-360-brief.html` | El brief comercial (precios y planes); el modal de planes enlaza a `#precios`. |
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
| `candidato-360-estrategia.js` | La estrategia (`window.C360Estrategia`, tarjeta 11 y su vista ampliada; plan en `tools/candidato-360/estrategia/PLAN.md`): la **fase** del calendario 2027, el **orden de los 8 principios** del banco (Σ arquetipo: parte en su votación × afinidad acotada a ×0,5–×2 × celda de la matriz), la **tabla de territorio** (peso del arquetipo × afinidad → retener · retener y crecer · hacerse conocer · movilizar · no gastar, con barrios fuertes y huecos), **figura o barrio** por el arraigo medido y la **competencia en su lista** (lee la escalera del panel 10). Determinista y sin DOM: `evaluar` es la entrada única. La afinidad NO se calcula aquí: es `C360ArqLectura.afinidad` (con `{minimo: 0}`) y, en JAL, contra `C360ArqLectura.recortar(LC, localidad)`. Prueba: `node tools/candidato-360/prueba-estrategia.mjs` (`--sin-red` para solo la lógica). |
| `candidato-360-arq-lectura.js` | La lectura de arquetipos (`window.C360ArqLectura`): qué ciudad (`ciudadDe`, con la campaña guardada — ⚠️ una candidatura NUEVA no pasa por el formulario de la ruta con historial y antes la tarjeta salía apagada: Nury en la Alcaldía de Cartagena, sep-29), el reparto de sus votos por arquetipo (Medellín por coordenada del puesto en el polígono DAP; Cartagena por nombre de barrio y con la MEZCLA de ocho) y la geometría para el mapa. La usan la tarjeta 05 y su página: salió de `candidato-360.js` para que las dos no digan cifras distintas. |
| `candidato-360-panel.js` | El chasis de los paneles: sesión, vínculo, muro, territorio y helpers de formato. |
| `candidato-360-franjas.js` | El rayado de los barrios sin puesto de votación (`window.C360Franjas`): un patrón SVG por color y la distancia en «564 m» o «1,4 km». Lo usan el mapa de barrios del CRM y el del electorado. |
| `candidato-360-diad.js` | El plan del día de la elección (`window.C360DiaD`): `fuente`, `plan`, `testigosPara`, `alertas`, `csv`. Lo usan la tarjeta 09 y su panel, y también el endoso, la meta del salto y la proyección por ciudad (`fuente` es la misma cuenta en todos lados). |
| `candidato-360-frases.js` | El discurso por región (`window.C360Frases`): departamentos, ciudades, partidos y el dato medido de 2023. |
| `candidato-360-saliencia.js` · `candidato-360-geoprensa.js` | La escucha: qué temas, actores y medios dominan los titulares, y en qué lugar del territorio pasa lo que se publica. |
| `candidato-360-arquetipos.js` | Las familias de arquetipos por ciudad (`TERRITORIOS`) con su sensibilidad por tema; lo leen la escucha y la página de arquetipos. |
| `candidato-360-arq-modos.js` | Los modos «Ver arquetipos» y «Simulación» de la página de arquetipos, con un adaptador por ciudad. |
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
| `mapas-2026/CENSO_PUESTO_2026.json` | **La fuente vigente del electorado** (desde el 27-sep-2026): censo del Congreso 2026 por puesto con sexo, 10 rangos de edad y celdas sexo × edad (18-30 · 31-60 · 61+, estimadas por raking). Gzip, 482 KB. Lo produce `tools/candidato-360/perfil/construir-censo-2026.py`. |
| `mapas-2026/CENSO_EDAD_PUESTO.json` · `PERFIL_SEXO_EDAD_PUESTO.json` | Las dos fuentes anteriores (edad proyectada y sufragantes de 2022). Siguen en S3 **sin uso**. |
| `asamblea-2023/dep/<dep>.json` | Resultados de asamblea por **municipio**: la única elección que baja a todos los municipios del país con voto por partido. |
| `concejo-2023/resultados-concejo-2023.json` | Concejo por **comuna**, solo en once ciudades. |
| `hvp/dep/<dep>.json` · `hvp/curules-jal.json` | La hoja de vida de cada puesto (el Día D) y las curules oficiales de cada JAL (la meta). |
| `candidato-360-data/estrategia-banco.json` | El banco de estrategia (capa A): 8 principios, 39 fichas (25 de tronco, 14 de rama) con referencia y DOI, la modulación por arquetipo, 5 ramas, la matriz arquetipo × principio en números (2 · 1 · 0 · −1) para los 6 arquetipos de Concejo de Bogotá y los 5 emocionales de Medellín, más el calendario 2027, los cuadrantes y las acciones por fase. Literatura pública: **ningún candidato real**. Lo genera `tools/candidato-360/estrategia/build_banco.py` desde el anexo A (interno, fuera del repo; ruta en `C360_ESTRATEGIA_ANEXO`) y aborta si queda algo del caso. |
| `candidato-360-data/arraigo-concejo-bogota-2023.json` | El arraigo de las 435 candidaturas al Concejo de Bogotá 2023 por **slug** (sin nombres): `[localidad, barrio]` y la referencia de la ciudad (14,2 %, la mayor de las dos escalas ponderada por votos). Sale del CSV del estudio de arquetipos de Bogotá con `tools/candidato-360/estrategia/build_arraigo.py`. |
| `candidato-360-data/` (en el repo) | Logos de partido, barrios por ciudad (`bogota-` · `cali-` · `cartagena-barrios/`), diccionarios puesto → barrio, catálogos por departamento y los Excel de homónimos. |

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
4. **Arquetipos en Medellín, Cartagena y Bogotá.** Medellín (152 barrios,
   Proyecto DC), Cartagena (211 barrios, ocho arquetipos propios, desde el
   27-sep) y **Bogotá (519 barrios, desde el 14-oct; de comportamiento
   electoral, no emocionales)**; fuera de ahí la tarjeta se apaga y lo dice.
   Sumar otra ciudad es un adaptador en `candidato-360-arq-modos.js`, una
   rama en `candidato-360-arq-lectura.js` y una entrada en `TERRITORIOS`
   (escucha). Bogotá: ver §11, «Arquetipos de Bogotá en el panel 05».
   El prompt de Candi en el worker ya los nombra a los tres
   (`C360_CANDI_PROMPT_V` v9, 14-oct-2026).
5. **Movimientos regionales sin clasificar (9,1 %).** Los que no dejan rastro
   suficiente. Bajar el umbral de `clasificar-locales.mjs` sube la cobertura y
   baja la confianza: es una decisión, no un bug.
6. **`saltos-arraigo.json`** (el estudio empírico del salto de corporación)
   está calculado pero no publicado; sin él, el reparto usa el respaldo.

7. **Competencia y hoja de ruta (30-sep-2026).** Informe para Nury en
   `Propuestas/candidato-360/Candidato-360-Competencia-y-Hoja-de-Ruta.pdf`
   (`python3 tools/candidato-360/competencia/build.py`; el texto vive en ese
   script). 35 productos por categoría, pruebas gratuitas, precios y 16 piezas
   para agregar. Decisión de fondo: **no hay envíos masivos de WhatsApp** (Meta
   los prohíbe a campañas y a quienes les prestan servicios; la Circular 002 de
   2026 de la SIC exige autorización previa); lo que se construye es el mensaje
   listo + enlace `wa.me` que cada líder envía desde su celular. ⚠️ El brief
   comercial todavía dice «arquetipos solo Medellín» y «endoso próximamente».

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

## 10. Lo gráfico · para quien diseña (Astra)

> Esta sección es el brief para producir imágenes, ilustraciones y animaciones
> de Candidato 360. Lo de arriba explica el producto; esto dice cómo se ve, qué
> piezas existen, en qué formato se entregan y qué no se puede hacer. Las
> medidas salen de los archivos que hoy están en el repo (2-oct-2026).

### 10.1 La identidad visual

Candidato 360 tiene **identidad propia y clara (papel)**, a propósito distinta
del resto de ricardoruiz.co, que es oscuro. Seria, de oficina de campaña, con
acentos cálidos; nada de estética de mitin ni de colores de un partido.

**Paleta vigente** (los tokens de `candidato-360.css`, línea 16; pisan una
paleta verde anterior que sigue escrita en la línea 2 y ya no se ve):

| Token | Hex | Dónde se usa |
|---|---|---|
| `--paper` | `#f6f1e8` | fondo de todas las páginas |
| `--cream` | `#fffdf8` | tarjetas y cajas |
| `--ink` | `#102238` | texto (azul noche, no negro) |
| `--forest` | `#102b46` | bloques oscuros: el panel de elección de la portada (degradado `#102b46 → #0b2035`), las tarjetas de corporación, la tarjeta de la meta |
| `--green` | `#147c70` | acento principal (verde azulado): rótulos, enlaces, numeración de tarjetas |
| `--mint` | `#b9ded2` | sombra desplazada de las tarjetas, fondos suaves, hover |
| `--coral` | `#ef705d` | acento cálido: botón de buscar, selección, puntos decorativos |
| `--muted` | `#637080` | texto secundario |
| `--line` | `rgba(16,34,56,.14)` | bordes de 1 px |

**Tipografía** (Google Fonts): **Manrope** 400-800 para todo · **Syne** solo
en el logotipo · **DM Mono** para rótulos pequeños en mayúscula espaciada
(«01 · MAPA DE HISTORIAL ELECTORAL», el kicker de cada pantalla).

**Lenguaje gráfico que ya está en la página** (para que lo nuevo case):
esquinas rectas, sin redondeo · bordes finos de 1 px · **sombra sólida
desplazada** en vez de difuminada (`18px 18px 0` en `--mint`) · manchas
orgánicas con anillos concéntricos muy tenues · tramas de puntos coral y
rayado diagonal verde azulado a baja opacidad · el logo es **cuatro barras
escalonadas** (100 · 72 · 46 · 25 % de alto).

**Colores que significan algo** — no usarlos como decoración, porque en
pantalla ya dicen un dato:

| Qué | Colores |
|---|---|
| Escalones de la meta | inminente `#e0533f` · probable `#f2c14e` · posible `#4ade80` · deseado `#a78bfa` |
| Familias políticas (`partidos-bloques.js`) | izquierda `#B91C1C` · centro-izquierda `#0D9488` · centro `#7C3AED` · centro-derecha `#2563EB` · derecha `#1E40AF` · sin línea nacional `#3E8A5B` |
| Arquetipos | cada ciudad trae los suyos (Medellín 5, Cartagena 8), con su color en el dato del estudio |

**La voz**: el producto le habla a la persona **de usted**; Candi habla **de
tú**. Si una pieza lleva texto, respeta esa diferencia.

### 10.2 Las imágenes que hoy usa el producto

| Pieza | Archivo | Medida | Dónde aparece y cómo se recorta |
|---|---|---|---|
| Portada · «Ya me he lanzado» | `assets/candidato-360/historial-electoral.jpg` | 1693 × 929 | miniatura de 70 × 62 px, recorte `cover` al centro, junto al texto de la opción |
| Portada · «Es mi primera vez» | `assets/candidato-360/primera-candidatura.jpg` | 1747 × 900 | ídem |
| Tarjetas de corporación (5) | `assets/candidato-360/corporacion-{alcaldia,asamblea,concejo,gobernacion,jal}.jpg` | ~1774 × 887 (2:1) | fondo de una tarjeta de ~112 px de alto, `cover` centrado, con un **degradado azul noche que tapa el lado izquierdo** (93 % → 18 % de opacidad) porque ahí va el texto blanco. **El motivo tiene que vivir en la mitad derecha.** |
| Candi | `assets/candidato-360/candi/*.webp` | ver §10.3 | dock abajo a la derecha y franja de descanso |
| Tarjetas de arquetipos de Cartagena (8) | S3 `bases de datos/Proyecto DC/arquetipos-cartagena/escudos/{slug}.jpg` | — | ficha del arquetipo en el panel 05. **Son del estudio de cartografía emocional, no nuestras**: no se rehacen sin que Ricardo lo pida |
| Logos de partido | `candidato-360-data/logos-partidos/16/*.png` (38, catálogo nacional) | — | rejilla para elegir el aval. **Siempre el logo oficial**; nunca se dibuja, se redibuja ni se inventa uno |
| Fotos de candidatos | S3 `congreso-2026/output/fotos-candidatos/{slug}.jpg` | 1248 × 864 | avatar en la ficha de la persona. Tienen su propio flujo (`tools/fotos-candidatos/sync.py`), fuera de este encargo salvo que Ricardo lo pida |

Lo que **no** es imagen y no se dibuja: los mapas (son vectoriales, Leaflet,
pintados con el dato), los gráficos y las cifras.

Lo que **hoy no tiene imagen** (dato, no pedido): las diez tarjetas del CRM y
las páginas de los paneles son solo texto y dato; el brief comercial
(`candidato-360-brief.html`) no lleva ilustraciones, y ninguna página tiene
imagen para compartir en redes (`og:image`). Qué de esto se ilustra lo decide
Ricardo.

### Selector de países · UX del 2-oct-2026

Las tarjetas de Colombia, Ecuador y Paraguay llevan ilustraciones editoriales de
Cartagena, Quito y Asunción, respectivamente. Viven en
`assets/candidato-360/pais-{colombia,ecuador,paraguay}-v1.webp` (600 × 400;
~196 KB entre las tres). Son referencias ilustradas, no fotografías documentales.
Prompts exactos y herramienta: `assets/candidato-360/paises-prompts-v1.md`.
La imagen ocupa una columna propia; nombre y fecha quedan fuera de ella, con
foco visible y ajuste hasta 320 px. Desde el 25-oct-2026 las tarjetas van sin
flecha y con la letra más grande (nombre 25 px, fecha 14,5 px). Al elegir país el foco pasa al
título del siguiente paso; al volver regresa al país elegido. La carga inicial
recordada no roba el foco.

Candi tiene un espacio en el flujo de la portada (`#candiBienvenida`), en el
saludo que sigue al país; desde el 25-oct-2026 no aparece en la pregunta del
punto de partida ni en la búsqueda del nombre. `ubicarEnPortada()`
mueve el mismo dock: abrir el chat o salir de la portada lo devuelve a `body`;
cerrarlo o volver lo trae al espacio reservado. Su paseo del hueso se desactiva
solo en esta portada para evitar que cruce las opciones. Las páginas sin ese
contenedor conservan su comportamiento.

### Incorporación sin flechas y sin scroll (25-oct-2026)

Pedido de Ricardo sobre la portada y los pasos que siguen hasta abrir el CRM:

- **Sin flechas** (→ ←) en cajas ni botones de la incorporación: portada,
  países, punto de partida, búsqueda, ruta y candidatura nueva, incluidos los
  textos que arma `candidato-360.js` (wizard, «Abrir CRM de campaña»). El CRM
  conserva las suyas.
- **«Siguiente»** en mayúscula sostenida, ancho (62 % de la fila) y sin flecha.
  **«Elegir mi punto de partida»** y **«Escribir mi nombre»** son botones.
- **«Volver» vive en la barra superior** (`nav-back`, sin flecha) también en la
  portada: en ella deshace un paso (punto de partida → país → presentación) con
  `volverPasoIntro()`. El «Volver» de dentro de la caja (`.intro-return` y el de
  `#existing`) se oculta.
- **Sin scroll donde cabe**: las pantallas de incorporación miden el alto que
  deja la barra (`--c360-nav`, que fija un `ResizeObserver` en
  `candidato-360.js`, porque en el teléfono la barra pasa de 83 a 113 px cuando
  aparece «Volver») y la caja ya no es un cuadrado fijo. Medido sin scroll en
  1440×900, 1366×768, 375×812 y 375×667. En pantallas bajas se aprieta el aire
  (márgenes, títulos, Candi más pequeña) y, en teléfonos de ≤700 px, se oculta
  la frase bajo «¿Cuál es su punto de partida?».
- Todo en el bloque final de `candidato-360.css` («Incorporación sin flechas…»).
- **Segunda ronda (mismo día): Candi solo saluda.** En la pregunta del punto de
  partida y en la búsqueda del nombre ya no aparece (`ubicarEnPortada()` en
  `candidato-360-candi.js` la monta visible solo en la etapa `greeting`). Las
  tarjetas «Ya fui candidato» y «Es mi primera candidatura» toman ese espacio:
  más altas y con letra más grande. El paso del país va sin la frase «Los
  módulos son los mismos en los tres…» y con el título más grande.
- **Tercera ronda: la búsqueda ya no nombra a Candi** (rótulo «Cómo buscarse» y
  el texto de usted, como el resto del producto) y **la letra de Candi es
  ajustable**. Panel y globo arrancan un 12 % más grandes que el diseño
  original y traen botones A− / A+ (escala 0,9 · 1 · 1,12 · 1,25 · 1,4 · 1,55,
  una sola para los dos, guardada en `localStorage['c360-candi-letra']`). La
  escala es la variable `--candi-esc` del contenedor de Candi y multiplica la
  letra y el ancho del panel y del globo (`candidato-360-candi.css`, al final).
- **Paseo del hueso (26-oct-2026).** Va por el borde de abajo de la pantalla
  (`SUELO_PX`), no por la línea del dock, y su extremo derecho queda a la
  izquierda de «Pregúntame». Si el usuario la interrumpe mientras camina, ya no
  se queda en mitad de la pantalla: termina de caminar hasta el extremo y ahí
  se sienta atenta (se salta recoger y echarse). Abrir el panel, preguntar o un
  cálculo la siguen devolviendo al dock en el acto.
- **Fechas de las fases (26-oct-2026).** Remate desde el 25 de septiembre;
  el Día de la elección se abre el 24 de octubre, una semana antes (también en
  `estrategia-banco.json` y en `build_banco.py`). El texto de la portada del
  plan lo escribió Ricardo y va en tú a propósito.
- **Tarjetas de fase (26-oct-2026).** El rótulo de fechas pasa de 10 a 12,5 px;
  «Abrir» es un botón (sin flecha) y las fases cerradas solo dicen cuándo se
  abren, con un botón «Ver»: lo que trae cada una se ve al abrirla.
- **La candidatura nueva ya no pide cuenta para empezar (26-oct-2026, pedido
  de Ricardo probando como usuario externo).** Antes un muro tapaba el
  formulario. Ahora se llenan los seis pasos sin cuenta y el CRM abre en vista
  previa (`CRM_VITRINA`), igual que la ruta con historial: el registro se pide
  al tocar un módulo. Sin acceso no se vincula ni se guarda nada en el
  worker. La pantalla pasó además a la caja centrada de 720 px de la ruta con
  historial; antes ocupaba todo el ancho.
- **Lo llenado sin cuenta sobrevive al registro (26-oct-2026).** En vista
  previa, las dos rutas guardan en el navegador `localStorage['c360-pendiente']`
  con la forma del vínculo (`{tipo, candidato|nuevo, campana, ts}`; vence a los
  30 días). Al volver con sesión iniciada y sin vínculo, `recuperarPendiente`
  lo reabre con `abrirVinculo(p)`: sin acceso queda en vista previa (con los
  planes encima si llega con `?comprar=1`); con acceso pide la confirmación de
  siempre y vincula (la candidatura nueva por `recuperarPendiente`, la de
  historial por `launchCRM`). Se borra al vincular (`guardarVinculo`) y se
  reabre una sola vez por pestaña (`sessionStorage['c360-pendiente-abierto']`),
  para que quien vuelve a la portada y recarga no quede atrapado. Sin sesión
  no se reabre nada.
- **Candi en el teléfono: barra inferior (26-oct-2026, pedido de Ricardo).**
  En pantallas de 560 px o menos ya no hay «Pregúntame» ni globo: una barra
  abajo, con la piel de la barra superior de Congreso Claro (papel translúcido
  con desenfoque), muestra lo que dice Candi —copia del globo vía
  `MutationObserver`— o «Toca aquí para preguntarle a Candi.», con un piquito
  hacia ella, que se sienta encima. Tocarla abre el chat. Solo existe cuando
  el dock vive en `<body>` (en la portada Candi va dentro de la tarjeta). La
  página reserva 62 px fijos (`--c360-barra`, que también descuenta
  `--c360-alto`): un mensaje largo crece hacia arriba sobre el contenido en
  vez de mover la página. El paseo del hueso va encima de la barra.
- **Recorte de Candi en el saludo, corregido.** En teléfonos de pantalla baja
  el escenario medía 130 px y la figura 160: se le cortaba la cabeza. Ahora la
  figura mide 122 en un escenario de 132.

### 10.3 Candi (Luna)

Candi es la guía de la plataforma y es **Luna, la perrita de Ricardo**, en 3D
suave. Las poses las dibuja Astra; Claude las conecta. Historial completo de
entregas y especificaciones en `assets/candidato-360/candi/`
(`README.md` → v1/v2, `ATLETICA-V3-PARA-CLAUDE.md` → la vigente,
`HUESO-PARA-CLAUDE.md`, `ACTUALIZACION-29-SEP-PARA-CLAUDE.md`).

**Identidad que no cambia**: pelaje blanco y café · franja blanca asimétrica en
la frente · pecas en el hocico · ojos cafés · orejas largas con flecos ·
pañuelo rojo con puntos blancos · **atlética desde la v3** (patas largas,
cuerpo esbelto; la v1/v2 más rechoncha ya no es referencia) · anatomía de
perro, sin manos humanas · cuerpo completo, sin cortar orejas, patas ni cola.
Las manchas van siempre del mismo lado: **no se espeja la imagen para cambiar
de dirección** (hoy hay una excepción, ver huecos).

**Los atlas vigentes** (cuadrícula leída de izquierda a derecha y de arriba
abajo; se sirve el WebP, el PNG es la fuente):

| Estado | Archivo | Cuadrícula | Duración | Cuándo sale en el producto |
|---|---|---|---|---|
| Entrada y saludo | `candi-saludo-atletica-v3` | 5 × 4 (20 poses) | 3,2 s | la primera carga de cada pestaña: entra caminando y saluda |
| Sentarse y atenta | `candi-sentarse-atenta-v3` | 4 × 4 (0-7 sentarse, 8-15 atenta) | 1,6 s + reposo en bucle de 4 s | después del saludo y siempre que espera; la pose 8 es la **miniatura del botón** |
| Pensando (gafas y bombillo) | `candi-pensando-atletica-v3` | 6 × 5 (30) | 6 s | mientras la página calcula algo |
| Investigando (lupa) | `candi-investigando-atletica-v3` | 6 × 4 (24) | 4,8 s | mientras una pregunta escrita va al modelo |
| Curiosa | `candi-curiosa-atletica-v3` | 4 × 3 (12) | 2,8 s | **existe pero no está conectada**: no se ha decidido cuándo va |
| Hueso · caminar | `candi-hueso-caminar-v1` | 6 × 4 (24) | según el ancho | descanso: tras 20 s sin actividad cruza la pantalla |
| Hueso · recoger | `candi-hueso-recoger-v1` | 6 × 4 (24) | — | recoge el hueso con la boca |
| Hueso · echarse | `candi-hueso-echarse-v1` | 6 × 4 (22, dos celdas vacías) | — | se echa con el hueso entre las patas |
| El hueso rosado | `candi-hueso-rosado-v1` | imagen única | — | el juguete suelto antes de recogerlo |

**Dónde y a qué tamaño se ve**: el dock va abajo a la derecha, en una escena de
250 × 190 px (128 × 104 en móvil; en pantallas muy bajas se esconde). La
miniatura del botón es un círculo de 30 px. El descanso corre en una franja del
ancho de la ventana y la mascota mide entre ~100 y 210 px según el ancho. Es
decir: **todo tiene que leerse a 128-180 px de alto**.

**Formato de entrega de un clip nuevo** (lo que funcionó con las entregas
anteriores):
- **PNG RGBA con transparencia real**, sin fondo, sin texto, sin sombras de
  suelo que se corten entre celdas.
- **Una cuadrícula por clip**, poses ordenadas por filas. Cámara fija, misma
  escala y la **misma línea de suelo** en todas las celdas; sin variaciones de
  encuadre entre poses (las celdas fraccionarias de la v2 —280,4 × 280,5—
  obligaron a corregir a mano el origen de cada fila: mejor celdas enteras).
- **Empieza exactamente en la pose donde termina el clip anterior** (por
  ejemplo, «levantarse» empieza en la última pose de «echarse»).
- Junto al PNG: el **prompt exacto** (`prompt-<estado>-atletica-v3.txt`) y un
  `<TEMA>-PARA-CLAUDE.md` con poses, milisegundos por pose, qué celdas forman
  cada tramo y qué eventos espera el reproductor.
- **Nombres**: `candi-<estado>-atletica-v3.png`. Una versión nueva es un
  archivo nuevo (`-v4`), nunca se pisa la anterior.
- Son **poses**, no fotogramas de video: el reproductor cambia de celda de
  golpe (sin interpolar) y mueve el desplazamiento horizontal por su cuenta.
- Con movimiento reducido el producto muestra una pose quieta: cada clip debe
  tener una pose que funcione sola.

Del lado nuestro, al recibirlo: se convierte a WebP
(`cwebp -q 90 -alpha_q 100 -m 6 x.png -o x.webp`; el saludo pasó de 2 MB a
816 KB sin diferencia visible), se registra en `candi-atletica.js` o
`candi-hueso.js`, se sube el `?v=` de esos scripts en las páginas que los
cargan y se prueba sobre el fondo papel, sobre el azul noche y en móvil.

### 10.4 Reglas que también valen para lo gráfico

1. **Ninguna pieza sugiere saber por quién votó alguien.** El voto es secreto
   (§3, regla 1): se muestran territorios y puestos, nunca personas votando.
2. **Nada de cifras inventadas.** Si una pieza muestra números (un mockup del
   tablero, un ejemplo de meta), son reales y con fuente, o se rotulan
   «ejemplo».
3. **El producto es para candidaturas de todas las familias políticas**:
   criterio nuestro, ninguna ilustración se inclina por una (sin colores,
   símbolos ni consignas de partido).
4. **Los logos de partido son los oficiales**, siempre.
5. **No se nombra en ninguna pieza visible a quien hizo la cartografía
   emocional**: se dice «el estudio» (pedido de Ricardo, 1-oct-2026).
6. **No se nombra al proveedor del modelo** que responde las preguntas a Candi.
7. **En pantalla la guía se llama Candi, siempre.** Luna es el nombre de la
   perrita de Ricardo, en la que está basada, y solo aparece en los comentarios
   del código y en esta documentación. Ningún título, rótulo, globo, texto
   alternativo ni prompt dice «Luna». Pasó una vez (oct-2026): el saludo tras
   elegir país decía «¡Hola! Soy Luna» y la búsqueda «Luna · Tu guía de
   campaña», y hubo que corregirlo.

### 10.5 Huecos gráficos conocidos

- **Candi camina hacia la derecha espejada**: el clip de caminar existe solo
  hacia la izquierda y el reproductor lo refleja, así que las manchas cambian
  de lado. Falta un caminar propio hacia la derecha.
- **No hay clip de levantarse desde echada**: hoy se reutiliza el arranque de
  caminar.
- **Continuidad entre poses**: pequeñas variaciones de pelaje, tamaño y
  alineación entre fotogramas y entre atlas; el giro de la entrada y el
  descenso al sentarse todavía muestran saltos.
- **Curiosa** está dibujada y sin usar (decisión de producto pendiente, no
  gráfica).
- Lo que no tiene imagen (§10.2) — se ilustra solo si Ricardo lo pide.
- **Los 11 arquetipos de Bogotá no tienen tarjeta gráfica** (Medellín y
  Cartagena traen la del estudio). Hoy en su lugar va la caja «Lo que lo
  distingue» con sus cifras contra la ciudad. Si se dibujan, los nombres y
  lemas están en `tools/candidato-360/arquetipos-bogota/publicar.py`
  (`TEXTOS`) y ninguna debe sonar a juicio sobre el barrio.

## 11. Bitácora técnica

> Lo que antes vivía en `CLAUDE.md`, por tema y con su fecha. Es la memoria de
> por qué el código está como está: casi cada ⚠️ salió de un caso real que se
> rompió. Los números de tarjeta son los de la fecha de cada entrada y
> cambiaron más de una vez; la numeración vigente está en §2. Donde algo quedó
> desactualizado, la entrada lo dice arriba.

### Archivos (consolidado el 5-sep-2026 · ya NO es un monolito de parches)
```
candidato-360.html      HTML puro: pantallas intro · existing · candidateRoute · crm · new + 3 modales
candidato-360.css       todos los estilos (eran 8 <style> inline)
candidato-360.js        toda la lógica, UN archivo en 10 secciones leíbles de arriba abajo
vote-target.js          meta de votos (Art. 263: umbral + cifra repartidora sobre índices 2023)
candidato-360-data/     polígonos barriales Bogotá (19 localidades) y Cali (22 comunas), .js bajo demanda
```
⚠️ **Al tocar el .css o el .js hay que bumpear su `?v=` en el HTML**, o el navegador sirve la
copia vieja sin dar error (mismo gotcha de `cand-index.js`).
⚠️ Antes había **12 bloques `<script>` que se envolvían unos a otros** (`launchCRM` 4 veces,
`loadHistoricalMap` 5). De ahí salían los bugs: Enter en el buscador abría el dashboard demo
de Julián Rodríguez, `historicalIndex` se leía antes de declararse, y los controles
Municipio/Localidad/Barrio no aparecían en Bogotá porque el último wrapper se saltaba al
anterior. Se eliminó todo el residuo del prototipo (`#dashboard` de Julián, `openJulian`,
el `searchCandidate` demo). **No volver a apilar wrappers**: el punto único de decisión del
mapa es `renderSingleElection` y el de barrios `renderBarriosForArea`.

### La regla del producto: una cuenta = UN candidato (decisión de Ricardo, sep-5-2026)
- **Gate de pago**: la búsqueda y el wizard se VEN (borrosos, `.search-box.locked` +
  `.c360-wall`) hasta que la cuenta tenga acceso. El dato es la vitrina; lo que se cobra es
  abrir el CRM. `openHistoricCandidate` y `createNew` abren el paywall sin acceso.
- **Vitrina del CRM** (sep-18-2026, decisión de Ricardo): sin acceso el CRM **SÍ abre** —mapa,
  histórico por año, promedio, proyección y meta de votos— con una banda "Vista previa". Lo cobrado
  se ve pero no se usa: el detalle por barrio/puesto sale **borroso con candado** (`candadoDetalle`,
  enganchado a `layeradd/layerremove` del mapa: se prende cuando `crmBarrioLayer` está pintado) y
  los botones de los módulos 03-07 abren el paywall (listener en captura). En vitrina **no se
  vincula ni se guarda nada** (`CRM_VITRINA`, ojo: `VITRINA` a secas es la rejilla de partidos).
  - **Los 3 con más votos se ven nítidos** (`VITRINA_MUESTRA`): el blur va polígono por polígono y
    fila por fila (`.vitrina-blur`), no a la capa entera — un mapa todo borroso no vende. Se tapan
    DOS cosas: el detalle (barrios/puestos, en cualquier modo) y la PROYECCIÓN del nivel de arriba
    (localidades/comunas/municipios en «Proyectado»); el historial en «Total» es dato público y se
    ve entero. El top sale del desglose (ya ordenado) y casa con `layer._vitrinaCode`, que se pone
    al crear cada capa. ⚠️ `pointer-events:none` va con `!important`: Leaflet lo fija en
    `path.leaflet-interactive` con más especificidad y el tooltip salía sobre lo borroso.
  - **«Activar mi candidatura» abre el modal de PLANES** (`C360_PLANES_UI`: Esencial · Con escucha
    diaria · Completo, las «tres formas» del brief), precio «Por definir». `elegirPlan(id)`: sin
    cuenta → `register.html?next=candidato-360.html?comprar=1&plan=id` (y `?comprar=1` reabre el
    modal con ese plan marcado); con cuenta → Wompi si está configurado, si no correo a soporte.
- **Vínculo**: al abrir el CRM por primera vez sale el modal de confirmación y se hace
  `POST /c360/vinculo`. **Es irreversible desde la plataforma**: el worker responde **409**
  a un segundo vínculo, y solo soporte (`hola@ricardoruiz.co`) lo borra con
  `DELETE /c360/admin/vinculo?email=` (adminGuard; deja copia 400 días). Vive en KV
  (`c360:vinculo:<email>`), no en el navegador: con localStorage bastaría borrar el sitio.
- **La campaña sí se edita** (corporación + territorio 2027): `POST /c360/campana`.
- **Al volver** (`abrirVinculo`): la portada muestra a quién está vinculada la cuenta y
  cualquiera de las dos tarjetas abre ESA candidatura. Con historial espera al índice, la
  reconstruye por `slugs` con `candidateProfile`, precarga la campaña y abre el CRM; con
  candidatura nueva abre su CRM directo. `?abrir=1` salta la portada.
- **Acceso** (`_c360AccesoDe`, espejo de Caudal): admin → cortesía `c360:acceso:<email>`
  (`POST /c360/acceso/save {email,dias,nota}`) → plan `c360` vigente → vencido.
  `CAUDAL`-style: `C360_PLANES = {full, c360}`. Falla cerrado: si `/c360/me` no responde,
  no hay acceso (ni para admin).
- **SKU**: plan `c360`, links de Wompi como secretos `WOMPI_LINK_C360_MENSUAL` /
  `WOMPI_LINK_C360_ANUAL` (la trampa de `WOMPI_LINKS`+`LINK_PLAN_MAP` no aplica: el frontend
  lee `GET /c360/planes`). ⚠️ **`C360_PRECIO_COP` está en `null`: falta que Ricardo fije el
  precio y cree el Link de Pago** (redirección `pago-confirmado.html`, pago único NO). Hasta
  entonces el muro ofrece «Solicitar acceso por correo». `pago-confirmado.html` y
  `dashboard.html` (chip + card `c360`) ya reconocen el plan.
- Sesión: `rr-token`/`rr-user` de localStorage + `Authorization: Bearer` contra
  `AUTH_API` (`window.RR_RUNTIME_CONFIG.authBase` lo sobreescribe para probar contra un
  `wrangler dev --local` en :8788 — hay entrada `rr-auth-dev` en `.claude/launch.json`).

### Las dos rutas
- **"Ya fui candidato"** → buscador sobre `cand-index.js` (las 29 fuentes, 439.015
  candidaturas, ranking `acRank`, debounce) → ficha de persona → corporación 2027 → CRM.
  «La misma corporación» **solo se ofrece si la última fue territorial** (`corporacionHistorica`);
  a quien viene de Senado o consulta se le pide elegir (antes decía "CONSULTAS" y caía a Concejo).
- **"Es mi primera candidatura"** → wizard de 6 pasos que **mueve los campos del formulario
  original, no los recrea** → CRM propio: `renderTerritorioObjetivo` pinta el territorio al
  que aspira (localidades de Bogotá, comunas de la ciudad si hay capa, o municipios del
  departamento con el objetivo en verde) y `VoteTarget` da la meta desde 2023.

### ⚠️⚠️ La tabla `SALTOS` tiene que cubrir TODO cambio de corporación (sep-19-2026)
Sin entrada en `SALTOS`, `tipoSalto` devuelve null y la meta cae al reparto proporcional al
historial, que la deja ENTERA en el territorio de origen: JAL Teusaquillo → Alcaldía de Bogotá
pintaba 1.567.000 en Teusaquillo y cero en las otras 19 localidades. Antes solo había 5 llaves;
ahora están las 16 combinaciones entre corporaciones distintas (`localidad` si el destino es
ciudad, `municipio` si es departamento). Solo 3 tienen estudio de arraigo; el resto va sin bono.
- `resultadosDestino` toma la ciudad de la CAMPAÑA (`codigoMunicipioObjetivo`), no de la primera
  mesa: quien viene de otro municipio tiene sus mesas en otra parte.
- Con origen departamental (asamblea/gobernación) `origen = []` en la proyección por municipio:
  el «· ANTIOQUIA ·» del corp casaba con cualquier municipio llamado como el departamento.
- **Historial fuera del destino** (edil de Bogotá → Gobernación de Cundinamarca): el mapa es el del
  territorio de campaña, SIN `crmMapState`, y `refreshCRMMapMode` salía temprano → ni toggles ni
  proyección. Ahora `PROYECCION_DEPTAL` + `ensureCRMMapToggles()` en `renderTerritorioDeCampana` y
  tras `prepararSalto` en `launchCRM`; «Proyectado» pinta los municipios con la meta repartida y
  «Total» vuelve al territorio. Verificado: Cundinamarca 116 municipios (Tocancipá · Soacha ·
  Fusagasugá arriba con huella del CD).

### ⚠️⚠️ El recorte territorial: una candidatura de mayor alcance NO se mezcla
Si Claudia López fue candidata al **Senado 2014 (nacional)** y compite en 2027 por Bogotá,
el mapa de 2014 muestra **solo sus votos en Bogotá**. Lo hace `datosCandidatura(candidate)` y
lo declara `notaRecorte()` bajo el mapa. Verificado: Senado 2014 → **42.058 votos en Bogotá**
(Suba 6.962 · Usaquén 5.960 · Engativá 4.317) y *"quedaron por fuera 39.570 votos en 21.890
mesas"*; **42.058 + 39.570 = 81.628 = su total nacional exacto.**
⚠️ **Va por CÓDIGO ELECTORAL, no por nombre** (`includes()` casa `CALI` con `CALIMA`): el
código del municipio sale del `mun_elec` del GeoJSON cacheado (`codigoMunicipioObjetivo`).
⚠️ Lo omitido se declara, no se esconde.

### Gotchas de datos que siguen vigentes
- **El año sale de `corp`** (`candidateYear`); la única fuente sin año es endoso →
  `SRC_YEAR={endoso:2026}`.
- **`Departamentos-mps/{cod}.json` se nombra por código ELECTORAL y adentro trae DANE**:
  `01.json` es Antioquia (DANE 05). `DEP_CODES` es la única tabla; no reintroducir DANE.
- **Los partidos salen del índice en memoria** (`PARTY_SOURCES`), no de descargas aparte.
- **`com:"000"` es marcador de nulo** (circunscripciones nacionales), no una comuna:
  `claveLocal` lo descarta y `completaNombres` pone el nombre desde el GeoJSON.
- **La foto** prueba todos los slugs de la persona en `fotos-candidatos/` y cae al índice
  presidencial (match primer nombre + DOS apellidos).
- **`.app-shell` usa `overflow:clip`, no `hidden`**: con hidden, `focus()`/`scrollIntoView`
  lo desplazaban 309 px de lado (el blob decorativo `.flow:before` infla el scrollWidth) y
  la columna de texto quedaba fuera de pantalla.
- **Los `.json` duplicados de `candidato-360-data/bogota-barrios/` se borraron** (6 MB que
  la página nunca leía; carga solo los `.js`).

### Deudas conocidas
- **PROMEDIO / PROYECTADO promedian elecciones de distinta naturaleza** (para Claudia:
  consulta 2026 + alcaldía 2019 + Senado 2014 recortado). Hay que restringirlo a la misma
  corporación o decir qué se promedia.
- **Meta de votos con supuestos escritos a mano** (`vote-target.js`: censo +1,4%,
  participación +1 pp, margen 3%; `VERIFIED_CUTOFFS` tiene una sola entrada; para alcaldías
  no hay archivo de participación → "participación estable").
- Base vial OSM directa (`tile.openstreetmap.org`) va contra su tile policy en producto
  comercial; solo se pinta donde la geometría no va rotada.
- Móvil: la barra superior se apila en dos filas a ≤850 px (mejorado con `flex-wrap`, no
  rediseñado).
- No está enlazado desde `index.html`/`electoral.html`; solo desde `dashboard.html`.

### El mapa del panel 07 · localidades, barrios y la rotación (sep-2026)

«Barrios» muestra **la ciudad entera**, no la última localidad visitada; el clic
en una localidad del mapa baja a la suya y el chip «Barrios · Suba» dice dónde
está. Son dos preguntas distintas —«dónde le pega en Bogotá, barrio por barrio»
y «cómo se ve este territorio»— y antes solo existía la segunda: el botón no
hacía nada hasta que se entrara por una localidad.

La cartografía barrial viene **partida por localidad** (19 archivos en
`candidato-360-data/bogota-barrios/`, 6,2 MB; Cali en `cali-barrios/`), así que
la ciudad entera se arma uniendo las partes — no bajando los 6,5 MB del
catastral de S3. Son **1.000 barrios, 539 con dato**; Sumapaz no tiene archivo
y el mapa lo declara en vez de callarlo. Tarda ~7 s la primera vez y queda en
`ST.barriosTodos`, así que volver es instantáneo.

⚠️⚠️ **Los barrios se rotan 90° igual que las localidades** (`E.rotar90`).
Bogotá es alta y angosta y la caja del mapa es apaisada: sin rotar cabe por el
alto y la ciudad queda del tamaño de una uña — medido, zoom 10,75 con Chía,
Cota y La Calera en pantalla. Y cambiar de orientación al bajar de nivel
desorienta. **Con la geometría rotada no se pueden poner tiles de OSM**: no
calzan, así que la base vial se pinta solo donde no se rota (Cali), que es la
misma regla que ya estaba por la tile policy.

⚠️ **La ventana urbana fija NO sirve en barrios.** Existe porque las 20
localidades incluyen Sumapaz, que es media Bogotá sin votantes; la cartografía
barrial ya viene sin Sumapaz, así que su propio `getBounds()` es más ajustado.
Usar la ventana ahí deja la ciudad ocupando la mitad de la caja.

⚠️ El título se arma con `.replace(/\.?$/, '.')`: «Bogotá, D.C.» ya termina en
punto y sumarle el de la frase dejaba «D.C..».

**Cartagena ya está enchufada** (sep-2026): 16 unidades, 331.201 válidos, cuadra
al voto con el CSV crudo. Cómo se resolvió, porque no fue como las otras 11:

⚠️⚠️ **El georef solo le pone a Cartagena sus 3 LOCALIDADES** (`CÓDIGO COMUNA`
= 01/02/03 = Histórica y del Caribe · De la Virgen y Turística · Industrial de
la Bahía), y tres unidades no son un mapa. Su división operativa son las **15
Unidades Comuneras de Gobierno más la 20**, que agrupa los corregimientos y las
islas (Barú, Bocachica, Tierra Bomba, Islas del Rosario, Isla Fuerte,
Pasacaballos, Bayunca, La Boquilla, Santa Ana…). La UCG vive en el campo `UCG`
de `CARTAGENAX.json`, cuyos polígonos son barrios.

`tools/analisis-candidato/build_cartagena_ucg.py` (necesita `shapely`) emite:
- **`CARTAGENA-UCG.json`** — los 213 barrios fusionados en 16 UCG, que es la
  capa que el mapa espera: una unidad, un polígono. Va a
  `mapas-2026/Ciudades-COM-LOC/`.
- **`cartagena-puesto-ucg.json`** — `{pcode: UCG}` para los 137 puestos.
  ⚠️ Existe para que la cuenta **no viva en dos builders**: la necesitan
  `build_territorial_resultados.py` (el agregado del mapa) y
  `build_territorial_comuna_detalle.py` (el drill), y resolverla por PIP en
  cada uno es garantizar que un día dejen de coincidir. Los dos lo leen de
  `COMUNA_EXTERNA`.

La cascada para ubicar cada puesto, con lo que rindió cada capa: **PIP exacto
123** · **zona 99 → UCG 20 rural 9** (un corregimiento pertenece ahí por
definición, esté a 200 m o a 3 km de la costa, así que no se le aplica el tope
de distancia) · **barrio vecino a ≤1 km: 4** (caen en un vacío del mapa — un
centro comercial, una vía; medidos entre 39 y 252 m) · **nombre del barrio del
georef: 1**. Ese último es el **Coliseo Bernardo Caraballo, 5.479 votos**,
georreferenciado a 3,5 km de la ciudad: su coordenada está mal pero su barrio,
Torices, lo ubica en la UCG 2. Sin esa capa se perdía entero, y pegarlo al
polígono más cercano lo habría mandado al campo.

⚠️ **Lleva ventana fija en `CIUDADES`**, por lo mismo que Bogotá: la UCG 20
llega hasta Isla Fuerte, 100 km al sur, y encuadrar por el bounds real deja el
casco urbano **8 veces más pequeño** (medido: 1,297° de alto contra 0,167°).
Las islas siguen en el mapa, hay que alejar para verlas.

⚠️ El nombre de la unidad NO puede salir del georef cuando se resuelve por
archivo externo: las 16 UCG caen dentro de solo 3 localidades, así que el mapa
repetía «LOC. 3 INDUSTRIAL DE LA BAHÍA» en cinco comunas distintas. De ahí
`COM_LABEL`, que las rotula «UCG 1», «UCG 2»…

### Cartagena en el mapa: UCG y barrios (sep-27-2026)

Cartagena solo estaba en el panel 06 (la capa de UCG). **En el mapa del CRM no
existía**: `CITY_JAL_LAYERS` no la tenía, así que un concejal de Cartagena veía
el municipio entero como una mancha. Y barrios no había en ninguno de los dos.
Ahora están las dos escalas en los dos mapas.

**Los datos** los arma `tools/candidato-360/mapas/build_cartagena_barrios.py`
desde `CARTAGENAX.json` (213 barrios con `UCG` y `LOC`, en S3 desde siempre):
- `candidato-360-data/cartagena-barrios/{UCG}.js` — los 213 partidos en 16
  archivos (779 KB), con las propiedades de Cali (`barrio` + `comuna`) para que
  el frontend los lea con el mismo código.
- `candidato-360-data/cartagena-puesto-barrio.js` — `{pcode: {barrio, comuna}}`
  de los 137 puestos: **123 por PIP · 10 por vecino ≤1 km · 1 por nombre · 3 sin
  barrio** (quedan con su UCG y sin barrio, no con uno inventado).
⚠️ **La UCG NO se recalcula ahí**: se lee de `output_hvp/cartagena-puesto-ucg.json`
(el que emite `build_cartagena_ucg.py`), y si el barrio que sale por coordenada
cae en otra UCG, el builder lo AVISA en vez de decidir por su cuenta. Tener la
misma cascada en dos archivos es garantizar que un día dejen de coincidir.

**El frontend**, tres cosas que no se deben deshacer:
- ⚠️⚠️ **La unidad de la mesa NO sale del georef.** Ahí Cartagena solo tiene sus
  3 localidades, así que `com` vale 01/02/03 y leer de ahí mandaba la ciudad
  entera a tres unidades de dieciséis —y encima a tres UCG que existen—. La capa
  lleva `prepare` (carga el diccionario) + `mesaKey` (lo consulta). Medido con
  Luz Marina Paria (16.580 votos, Concejo 2023): **los 16.580 caen en las 16
  UCG** y 16.554 (99,8 %) tienen barrio.
- ⚠️ **`nombreDeCapa: true`**: el nombre de la unidad tampoco puede salir de la
  mesa, que trae la localidad — el desglose rotulaba cinco UCG distintas como
  «Loc. 2 la Virgen y Turística». Manda el nombre del polígono.
- ⚠️ **`NOMBRE_BONITO` y `lugar()` dejaban «Ucg 5»**: se les añadió una lista
  CORTA de siglas sin punto (`UCG`, `JAL`). Una regla del tipo «tres letras en
  mayúscula es sigla» dejaría USME y BOSA gritando.
Además la capa lleva **ventana urbana fija** (la UCG 20 llega a Isla Fuerte,
100 km al sur) y el botón del nivel se rotula **UCG** (`nivel` en la capa):
«unidad comunera» no cabe.

El camino de barrios por diccionario (antes solo Cali) quedó en una tabla,
`BARRIOS_DIC` en `candidato-360.js` y `BARRIOS` en `candidato-360-electorado.html`:
**sumar una ciudad es una entrada más y su carpeta en `candidato-360-data/`.**
`candidato-360-geoprensa.js` lista las partes por ciudad en `PARTES` (Cartagena
no es una secuencia: 01-15 y la 20).

Veleta y Oportunidad ya tienen Cartagena por UCG (ver «Cartagena en Veleta y
Oportunidad»).

### Cartagena a tres escalas + el mapa de barrios de la ciudad entera (sep-27-2026)

**Botones Localidad · UCG · Barrio.** Las JAL de Cartagena se eligen por
LOCALIDAD, y el CRM solo sabía de UCG: un edil veía su circunscripción partida en
16 pedazos, y una candidatura NUEVA a JAL no encontraba su localidad en el mapa
(el formulario trae «LOC. 1 HISTORICA Y DEL CARIBE» y el polígono dice
«Localidad 1 · Histórica y del Caribe Norte»; ahora casan **por número**,
`casaLocalidad`). `CARTAGENA_CAPAS` en `candidato-360.js` trae las dos escalas
como familia; `cityLayerFor(nombre, {jal})` abre en la que la persona eligió
(`CAPA_ELEGIDA`, por sesión) o, si no eligió, en localidad para JAL y UCG para
lo demás. Cambiar de escala borra las vistas por año ya guardadas: el promedio
no puede mezclar localidades con UCG. Medido con Luz Marina Paria: los 16.580
votos caen enteros en las 16 UCG **y** en las 3 localidades.
- Cada barrio y cada puesto del diccionario llevan ahora `loc` (01/02/03). El
  del puesto sale del **georef** (es el que define la Junta); 3 puestos de
  frontera caen en un barrio de otra localidad y ahí manda el polígono del
  barrio a escala de barrio: la Localidad 2 suma 8.080 por barrio contra 8.134
  por localidad.
- **Las UCG no tienen nombre oficial** (el Acuerdo 159 de 2014 las numera y así
  las usa hasta Cartagena Cómo Vamos). La capa las rotula con sus barrios de
  más electores: «UCG 1 · Crespo, Centro y Manga». Tabla `UCG_BARRIOS` en
  `build_cartagena_ucg.py`; los sectores de Olaya Herrera van juntos. El nombre
  llega solo al CRM, al panel del electorado, a Veleta y a Oportunidad (estos
  dos después de correr `build-cartagena-ciudad/build.py`). Los tableros de
  2023 siguen con «UCG N» (`COM_LABEL`).
- ⚠️ Los `.js` de barrios de Cartagena van con `?v=` (`BARRIOS_DIC.CARTAGENA.v`):
  una copia vieja sin `loc` deja la escala Localidad vacía sin dar error.

**Al abrir una unidad se ve la ciudad ENTERA por barrio** (pedido de Ricardo:
«se ven en color los barrios de esa localidad y el resto gris o de otro color,
confunde»). Antes se pintaban solo los barrios de la unidad abierta, y
alrededor quedaban las demás comunas **con su color de votos** —otra escala con
la misma rampa— o el callejero en gris. Ahora `renderBarriosForArea` pinta
todos los barrios de la ciudad con UNA escala, la unidad abierta con borde
grueso y las demás con borde fino (`contornoUnidades`, no interactivo), y la
capa de unidades sale del mapa (vuelve al subir de nivel). El desglose de la
derecha sigue siendo de la unidad abierta, y tocar un barrio de otra zona la
abre sin mover el encuadre.
- `fuenteBarrial(state)` unifica los tres caminos (diccionario Cali/Cartagena ·
  Bogotá · capa de ciudad por coordenada): cada polígono sale con `_k` llave,
  `_u` unidad y `_n` nombre. La unidad abierta se pinta primero y el resto de
  la ciudad llega después (en Bogotá son 19 archivos). En Proyectado la meta de
  CADA unidad se reparte entre sus barrios con `valoresBarriales`.
- ⚠️ Bogotá va rotada y los barrios no: su contorno se **des-rota**
  (`desrotarGeoJSON`) para calzar. Verificado a ojo sobre el callejero.
- ⚠️ El contorno vive DENTRO de `crmBarrioLayer` (así toda salida del nivel
  barrio lo limpia) con `_contorno = true`, y `candadoDetalle` lo salta al
  contar y difuminar. Si se agrega otra capa ahí, marcarla igual.
- Medido: Cali 339 barrios (Comuna 13 con 22, desglose = sus 2.244 votos) ·
  Medellín 332 (Belén 14, = 6.661) · Bogotá 1.000 (Kennedy 95; 10.771 de 11.218,
  los 447 son puestos que el diccionario de Bogotá no ubica — brecha anterior).
- `NOMBRE_BONITO` ya no pone en minúscula el artículo que abre un nombre tras
  «·», «:» o «,» («UCG 12 · El Socorro», «Bayunca, La Boquilla»).

### El Pacto en la rejilla, la izquierda en Cartagena y la meta por código (sep-27-2026)

Empezó por «en la Alcaldía de Cartagena no aparece el Pacto». Salieron cuatro cosas:

**1. La rejilla de partidos solo muestra lo que tiene logo, y los logos casaban
por nombre exacto.** Las listas a Cámara 2026 llevan el departamento en el
nombre («PACTO HISTÓRICO BOLÍVAR», «…ANTIOQUIA», «…CÓRDOBA»: el Pacto en 17
departamentos) y ese es el nombre vigente del catálogo, así que el Pacto
quedaba fuera de la rejilla en todo el país menos Bogotá. `logoDePartido` cae
ahora al NÚCLEO (`nucleoLogo`: sin «PARTIDO/MOVIMIENTO POLÍTICO» delante y sin
el departamento EXACTO al final). Medido sobre los 33 catálogos: 23 nombres
ganan logo, los 23 del Pacto, cero falsos. «PACTO HISTÓRICO ALIANZA VERDE» NO
casa a propósito: es coalición. Siguen sin logo organizaciones que no tienen
archivo (Colombia Humana, ASI, Creemos, Ahora Colombia…).

**2. ⚠️⚠️ En 2023 la izquierda NO tuvo lista al Concejo de Cartagena** (0 %;
verificado contra el CSV crudo: 331.201 válidos sin blanco, idéntico al
índice), pero sí candidato a la Alcaldía: Javier Julio Bejarano (Pacto
Histórico Colombia Puede), 56.893 votos, segundo. Y el plan de testigos de
Alcaldía se arma con el CONCEJO de la ciudad: para alguien de izquierda (por
firmas, sin decidir o con el Pacto) caía a las «vecinas» y le armaba el plan con
los puestos de ASI, Verde y Nuevo Liberalismo. Medido en el país: la izquierda
sacó ≥5 % a la Alcaldía sin llegar al 1 % del Concejo en **14 municipios**
(Cartagena, Ciénaga de Oro, Turbaco, Cajibío, Sandoná…) y el centro-izquierda
en 3. `C360DiaD.fuente` ahora usa los candidatos de su familia a la Alcaldía
2023 (`familiaEnAlcaldia`, por slug `ALC2023-dep-mun-`) antes de las vecinas, y
el panel lo declara. En Cartagena: 7 de los 49 puestos del 70 % cambian.
⚠️ La cuenta tiene que sumar el voto DE LISTA: sin él, Bogotá aparecía como
caso (la lista del Pacto al Concejo fue cerrada).

**3. La frase «En lo local» mentía en ese caso**: «la izquierda casi no tuvo
lista propia… y la meta se mide con las familias vecinas». Ahora, si la campaña
es a Alcaldía o Gobernación, `dato()` mira ese cargo en 2023 antes de decirlo
(«…pero sí compitió por la Alcaldía: Javier Julio Bejarano quedó segundo con el
17 %»), y se quitó lo de «la meta se mide con las familias vecinas», que no era
cierto para ningún cargo. `agregarDatoRegional` recibe `corp`.
⚠️ La META de un cargo uninominal no usa partido ni familia: es el ganador de
2023 proyectado. Eso no lo tocaba el Pacto.

**4. ⚠️⚠️ La meta buscaba el territorio POR NOMBRE.** El formulario escribe el
municipio como el mapa del DANE («Cartagena de Indias», «Santiago de Cali», «San
José de Cúcuta») y la Registraduría como «CARTAGENA», «CALI», «CUCUTA». Medido
sobre 1.100 municipios, tal como el formulario arma el texto: **29 se quedaban
SIN meta** (Cali, Cartagena, Cúcuta, Tumaco, Buga, Mompox, Villa de Leyva…) y
**1 recibía la de otro** (Boyacá, el municipio, se medía con Iza). Ahora
`VoteTarget.estimate` recibe `codigo:{dep, mun}` y escoge las filas por el
código del slug (`filasPorCodigo`); el nombre solo elige la localidad dentro del
municipio en la JAL. Medido: 1.100 alcaldías, 1.098 concejos, 32 asambleas y 32
gobernaciones, cero errores. Los dos llamados de `candidato-360.js` pasan el
código (`codigoMunicipioObjetivo()` y `C360Electorado.codigoMunicipio`).

**✅ Resuelto (sep-27):** el salto hacia la Alcaldía ya no cae a la participación
donde la familia no tuvo lista al Concejo: `prepararSalto` pide
`C360DiaD.fuente` y, si trae `deAlcaldia`, `repartoSaltoCiudad` reparte con esos
votos (capa `alcaldia`, declarada en `notaSalto`).

### El territorio de campaña de Alcaldía/Concejo es la CIUDAD, no el departamento (sep-27-2026)

Antes, quien se lanzaba a la Alcaldía o al Concejo de una ciudad con capa de
comunas SIN votos propios allá (edil de Teusaquillo → Alcaldía de Cartagena, o
una candidatura nueva) veía los municipios del departamento con la ciudad en
verde y niveles «Municipio · Puestos»: solo la JAL tenía el mapa de ciudad.
Ahora `renderTerritorioCiudad(c)` (antes de `renderTerritorioObjetivo`, en
`renderTerritorioDeCampana` y en `abrirCRMNuevo`) dibuja la ciudad con
`pintarCiudad` —escalas (Cartagena: Localidad · UCG), barrios y
TOTAL/PROYECTADO— y marca el estado con `censo:true`.
- **«Total» es el CENSO ELECTORAL** (puestos del georef, «835.055 electores» en
  Cartagena) y todo lo dice: título «¿Dónde vota la gente…?», tooltips «personas
  habilitadas», desglose «Censo electoral por…». Mostrarlo como «votos» sería
  inventarle una votación.
- **«Proyectado» = la familia política en 2023** (`proyeccionFamiliar` →
  `C360DiaD.fuente`, la MISMA cuenta del Día D, con su caída a la Alcaldía y a
  las vecinas del espectro). A las mesas del Día D se les pega `com`/`comNom`
  del georef, o `claveLocal` caería a la zona. Por barrio también reparte la
  familia (base `familia` en `notaBarrial`); sin familia, el censo.
- `cambiarCapaCiudad` repinta en modo territorio (`state.territorio`), porque
  ahí no hay `state.candidato`.
- ⚠️ `cityLayerFor` casa por «contiene» y **CALIMA contiene CALI**:
  `renderTerritorioCiudad` exige que el nombre empiece o termine en la ciudad.
- ⚠️ El municipio llega con el nombre DANE («CARTAGENA DE INDIAS», «SANTIAGO DE
  CALI»): la llave de ciudad para barrios es `config.match[0]`, no el nombre.
- La JAL sigue en `renderTerritorioObjetivo` (compite en UNA localidad).

**La rejilla de partidos solo sale con «Con un partido» MARCADO**
(`avalElegidoPartido`). `avalVigente()` sigue suponiendo «partido» cuando no hay
nada marcado —los cálculos lo necesitan—, pero la pantalla no: la rejilla salía
antes de elegir. Sin opción marcada «Abrir CRM» queda deshabilitado, y una
campaña guardada con partido vuelve con el radio marcado.

### El perfil del votante con el censo de 2026 · quién PUEDE votar (sep-27-2026)

El módulo 06 (`candidato-360-electorado.html` + la tarjeta del CRM) describe a
**quien puede votar**, no a quien votó en 2022 — decisión de Ricardo, porque la
participación viene subiendo (58 % en la 1V de 2026, 63,6 % en la 2V; 58 % en la
2V de 2022). Candi lo explica en el saludo de esa página (`VISTAS.electorado.saludo`
en `candidato-360-candi.js`; si la página arranca calculando, el saludo va DESPUÉS
del aviso de cálculo, `decirSaludoDeVista`).

**Fuente única: `mapas-2026/CENSO_PUESTO_2026.json`** (S3, **gzip**, 482 KB),
de `tools/candidato-360/perfil/construir-censo-2026.py` sobre los JSON de censo
por puesto de la Registraduría (`Bases de datos/censos-registraduria/`, ver
«Escrutinio oficial 2026 en CSV + censos…»). Corte **Congreso 2026**, que suma
exactamente 41.287.084 (el builder aborta si no); sin exterior (40.036.238,
13.494 puestos). Fila por puesto: potencial · mujeres · hombres · 10 rangos ·
6 celdas sexo × edad · bloque · censo 2023 · tipo de cruce.
- **Reemplaza tres fuentes**: el censo del georef (38,6 M, corte viejo), la edad
  PROYECTADA (`CENSO_EDAD_PUESTO.json`, erraba 5-7 pp por banda y puesto e inflaba
  41-60 en 3,8 pp nacional) y el cruce de sufragantes 2022
  (`PERFIL_SEXO_EDAD_PUESTO.json`). Los dos archivos viejos siguen en S3 sin uso.
- **Edad**: 10 rangos observados; la página muestra **3 grupos** (jóvenes 18-30 ·
  adultos 31-60 · adultos mayores más de 60, el corte legal) y desglosa los 10 en
  un `<details>`. `E.GRUPOS_EDAD` / `E.agruparEdad`.
- ⚠️ **El cruce sexo × edad sigue siendo ESTIMADO** (la Registraduría publica
  sexo y edad por separado): raking 2×3 con semilla = sufragantes 2022 del puesto
  (Edadygenero, regrupados a 18-30/31-60/61+; sin semilla propia, la del
  municipio o la nacional — 2.208 puestos) y márgenes del censo 2026. Los seis
  perfiles cambiaron de 31-50/51+ a **31-60/61+**; `CANAL` en la página igual.
- ⚠️⚠️ **«Bloque de edad»**: en **866 puestos (5 M de electores)** un solo rango de
  5 años pesa ≥2,5× lo que pesa en su municipio (Bogotá 163 · Medellín 59 ·
  Bucaramanga 26 · Barranquilla 25 · Cartagena 23…). Así viene el censo —así está
  asignado el puesto—; NO atribuirle una causa (el georef tiene columnas de rango
  de cédula, pero solo 124 puestos las traen). La página deja **nota
  metodológica** en perfiles si pesa ≥5 % del censo del territorio y en la sección
  de edad si pesa ≥3 % de los votos de la persona.
- **Sección nueva «06 · Dónde creció el censo»** (`E.cambioCenso(prefijo)`): censo
  territoriales 2023 contra Congreso 2026. ⚠️ Los códigos de puesto se renumeran:
  cruce por código+nombre (12.030), si no por nombre único en el municipio (294);
  1.170 puestos nuevos y 598 de 2023 que desaparecen (2,57 M electores). Por eso
  el número firme es el del **territorio**; el top de puestos va con la
  advertencia de que un puesto puede crecer porque le trasladaron mesas.
  Medido: Medellín +55.470 (+3,1 %) · Cartagena +29.238 (+3,5 %).
- ⚠️ Al tocar `candidato-360-electorado.js` bumpear su `?v=` en las 4 páginas
  (`candidato-360`, `-electorado`, `-escucha`, `-diad`). El worker trae el texto
  nuevo de la vista `electorado` para Candi (`C360_CANDI_PROMPT_V` v4) **sin
  desplegar**.
- De paso: `seccionEdad` llamaba a un `FIGURA_EDAD` que no existía, así que la
  sección de edad reventaba siempre que había dato.

**Rediseño de la página (sep-28-2026)**, pedido de Ricardo («mucha más información
y toggles arriba»):
- **Barra de control arriba** (`#elecControl`): 8 cifras del territorio (censo ·
  mujeres · jóvenes · adultos · adultos mayores · 18-20 años · censo 2023→2026 ·
  su familia en 2023) y **pestañas** (Mapa y perfiles · Sexo · Edad · Campo y
  ciudad · Familias · Votación objetivo · Crecimiento del censo · Todo). Las
  lecturas de fondo ya no van enterradas en un `<details>`: cada sección lleva
  `data-tab` y la pestaña las muestra (`pintarTabs`/`irA`). Ancho 1.320 px.
- **El mapa pinta siete capas** («Qué pinta»): le pega · censo · mujeres ·
  jóvenes · adultos mayores · crecimiento 2023-26 · su familia 2023. Cinco clases
  por cuantiles; el crecimiento con cortes fijos a ambos lados de cero y SOLO con
  puestos comparables (uno nuevo o renumerado no entra). Cada unidad lleva `m =
  metricas(codes)`, y el tooltip lo dice todo junto.
- **Escalas** («Escala»): unidades · barrios, y en **Cartagena Localidades · UCG ·
  Barrios**. Las localidades se arman sumando los puestos del detalle por UCG
  según la `loc` del diccionario (`abrirLocalidades`); no hay archivo por
  localidad del Concejo.
- ⚠️⚠️ **En Cartagena la página asignaba cada puesto a su unidad con la comuna del
  georef**, que ahí es la LOCALIDAD (01/02/03): las 16 UCG recibían el censo de
  tres y el mapa pintaba dos. Ahora la UCG sale de `cartagena-puesto-barrio.js`
  (el mismo diccionario del CRM) y el nombre, del polígono.
- **Barrios de Cartagena con ventana urbana** (`ventanaBarrios` en `E.CIUDADES`):
  sus barrios incluyen las islas y el encuadre por bounds dejaba la ciudad en una
  uña. En Bogotá NO se usa (la cartografía barrial ya viene sin Sumapaz).
- El worker con la vista `electorado` de Candi quedó **desplegado** (prompt v4).
- **Relleno de vecino en barrios** (`rellenos()`): el barrio sin puesto propio
  toma el valor del barrio CON dato más cercano por centroide, punteado y
  translúcido, con tooltip que nombra al vecino y la distancia; nunca entra a un
  total. Tope **3 km** (`RELLENO_MAX_KM`): más lejos queda «sin dato» en vez de
  inventar vecino. Medido: Cartagena 75 con dato + 126 rellenados + 10 sin dato
  (islas); Bogotá 539 + 456 + 5.
- **Lo mismo en el mapa de barrios del CRM** (`rellenosBarrios` en
  `candidato-360.js`, dentro de `pintarCiudadBarrios`): «con puesto» = barrio con
  censo o votos propios (`fuente.censo()` + el historial). El relleno toma el
  valor del vecino en el modo que esté (Total o Proyectado), va punteado, no
  entra al desglose de la derecha y en vitrina se difumina como el resto del
  detalle. Medido con el mapa de la ciudad entera: Cartagena 122 barrios
  rellenados · Bogotá 432.
- **Desde el 14-oct-2026 los barrios sin puesto van RAYADOS, no punteados**
  (`candidato-360-franjas.js`, `C360Franjas.franja(color)`, en el CRM y en el
  electorado). Pedido de Ricardo: con el relleno pálido, un barrio cuyo vecino
  tenía 0 votos se leía como un cero suyo, y el globo decía «que tiene 0 votos».
  Ahora las rayas llevan el color del barrio con puesto más cercano (grises si
  ese vecino no tiene valor) y el globo dice «Sin puesto de votación: quienes
  viven aquí votan cerca. Léalo junto con X (distancia · votos)», sin el cero.
  Los patrones son SVG `<pattern>` en un `<svg>` de 0×0 pegado al body: Leaflet
  copia `fillColor` al atributo `fill`, así que basta pasar `url(#id)`.
  ⚠️ **El globo del mapa del CRM medía más de 1.000 px**: Leaflet trae
  `white-space:nowrap` y el texto largo salía en una sola línea, fuera del mapa.
  `#crmMap .leaflet-tooltip` ahora dobla a 260 px (`width:max-content`). Un globo
  nuevo en ese mapa: una o dos frases; la explicación larga va en la nota.

### Arquetipos de Bogotá en el panel 05 (oct-14-2026)

Bogotá entra a la tarjeta 05 y al panel 05 con arquetipos que **no son
cartografía emocional**: salen solo de cómo vota cada barrio (resultados
oficiales de Alcaldía y Concejo 2019 y 2023 y 1V 2026, censo electoral y
estrato oficial). Método, validación y límites en
`tools/candidato-360/arquetipos-bogota/LEEME.md` y
`Propuestas/candidato-360/arquetipos-bogota/borrador.md`.

- **Dos tipologías, una por corporación**: Concejo (6: clase media de nombre ·
  periferia de partido · norte de figuras · barrio de gestión · periferia que
  vota poco · ciudadela movilizada) y Alcaldía (5: periferia joven alineada ·
  clase media tradicional · clase media que decide · sur popular de voto
  cruzado · norte estratégico). Cada barrio trae **mezcla** y **confianza**
  (en cuántas de 200 re-muestras cae en el mismo arquetipo; «de frontera» si
  es menos de 60 %). JAL usa la de Concejo.
- ⚠️⚠️ **En vez de años hay CORTES.** La lectura de Bogotá trae `L.cortes`
  (`['concejo','alcaldia']`, o al revés si la campaña es a la Alcaldía:
  `leer(ciudad, mesas, { corp })`), `corteNombre`, `corteArt` («el Concejo»)
  y `corteA` («al Concejo»), `idsDe(corte)` y `confianzaDe`. La página y
  `arq-modos` leen `L.cortes || ['2023','2027']`, así que Medellín y
  Cartagena no cambian. Las filas siguen con `a23`/`a27`, que ahora quieren
  decir «primer corte» y «segundo corte».
- **Sin «Simulación»** (`X.sim === false`): sus palancas mueven sensibilidades
  por tema que salen de un estudio emocional, y aquí no lo hay. «Ver
  arquetipos» sí: selector de corporación, ficha del barrio con «Cómo vota el
  barrio» (variables contra la ciudad) y el criterio de oficio.
- **Sin tarjeta gráfica**: en la sección 01 va «Lo que lo distingue» (los
  rasgos medidos del arquetipo contra la ciudad). Los textos «para una
  campaña» van rotulados como criterio de oficio, no dato.
- **Datos** (públicos, gzip): `congreso-2026/output/arquetipos-bogota/`
  `arquetipos-bogota.json` (252 KB · 59 KB) y `barrios-bogota.json` (el
  catastral simplificado a ~4 m: 626 KB · 158 KB; el panel no necesita los
  6,5 MB del completo). `?v=20261014` en `candidato-360-arq-lectura.js`. Se
  regeneran con `python3 tools/candidato-360/arquetipos-bogota/publicar.py`.
- Puesto → barrio con `candidato-360-data/bogota-puesto-barrio.js`, la regla
  del CRM; fuera las zonas 90 y 98. Medido con candidaturas reales: Fabián
  Puentes 28.067 de 28.496 votos ubicados · Álvaro Acevedo 19.384 de 19.808
  y su arquetipo más afín es **«Barrio de gestión», ×2,21** · Oviedo (Alcaldía)
  601.697 de 616.902, más afín **«Clase media que decide», ×1,19**, que es
  donde estuvieron sus bastiones.
- Candi: `p.arquetipos` incluye Bogotá y hay temas propios (`arq-bogota` en
  el CRM, `bogota` en el panel).

### Arquetipos de Bogotá v1 · 8 por corporación, simulador y lectura personal (oct-19-2026)

Pedido de Ricardo al revisar la candidatura de un concejal de Bogotá. Reemplaza
la v0 de 6+5 descrita arriba (respaldo en
`Bases de datos/arquetipos-bogota/respaldo-v6-20261019/`).

- **8 arquetipos en cada corporación** (`arquetipos.py`, k = 8, silueta 0,193
  en Concejo y 0,195 en Alcaldía, contra 0,207 y 0,215 de la v0).
  - **En el Concejo** la «clase media de nombre» se parte en dos: **«Clase
    media sin dueño»** (vota más que el promedio y tiene la menor base propia
    de la ciudad) y la de siempre. El norte también se parte en dos: **«Norte
    de opinión»** (estrato 4, mucha participación, casi sin lista cerrada) y
    «Norte de figuras» (19 barrios de estrato 5-6).
  - **En la Alcaldía** entran **«Norte que busca alternativa»**, **«Barrio
    popular que reparte el voto»** y **«Clase media alineada»**.
  - ⚠️ Los 11 slugs de la v0 **se conservan**; solo se agregan `sin-dueno`,
    `opinion`, `alternativa`, `reparte` y `media-alineada`. La matriz del
    módulo 11 (`estrategia-banco.json`) todavía no tiene fila para los nuevos.
- **Textos en lenguaje de campaña** (`TEXTOS` en `publicar.py`), cuatro por
  arquetipo:
  - `lema`: la frase;
  - `quien`: quién vive ahí;
  - `decide`: cómo vota, dicho simple;
  - `oficio`: cómo ganárselo, rotulado como criterio de oficio.

  Antes eran párrafos de analista que un político no leía.
- **Relleno de vecino:** 474 barrios sin puesto propio toman el arquetipo del
  barrio con dato más cercano (≤ 2 km, por centroide). Van en `barrios` con
  `r: {de, km}` y `w: 0`. Se pintan **tenues y punteados**, y no entran a
  conteos, tablas ni simulación (`relleno` en el adaptador, `rellenoDe` en la
  lectura).
- **Simulador también en Bogotá** (`ADAPT.bogota.sim = true`):
  - ⚠️ **La sensibilidad por tema (`SENS`) es heurística del equipo**: en Bogotá
    no hay estudio emocional, y la página lo dice.
  - `resp` sale del cambio de voto 2019-2023 de la corporación de la campaña.
  - El ancla del alcalde es **Galán, 26 % de buena gestión e imagen 55 %**
    (Bogotá Cómo Vamos, EPC 2025), con paso de 5 puntos por palanca.
  - La base es la corporación (Concejo 2023 / Alcaldía 2023), no un año.
  - Tablas, media de sensibilidad y ficha usan solo los arquetipos de esa
    corporación (`ordenDe`).
- **Portada** (`#aqIntro`): qué es un arquetipo, de dónde sale y cómo se leen
  principal y ascendente. Se ve una vez por pestaña (`sessionStorage`), y el
  botón «¿Qué es un arquetipo?» la reabre. Al cerrarla se repinta el mapa,
  porque nació oculto.
- **Encabezado personal** (`#aqPersonal`): «{Nombre}, su arquetipo principal
  al Concejo es X con ascendente Y», con las razones.
  - Principal = mayor afinidad con al menos 5 % de los votos (`A.afinidad`).
  - Ascendente = la segunda afinidad, si es ≥ ×1.
  - Si el arquetipo con más votos no es el principal, se dice: «es volumen, no
    afinidad».
- **06 · Los arquetipos de la ciudad**: solo los de la **corporación de la
  campaña**, como cards con imagen. Hay un botón para ver los de la otra
  corporación.
  - Imagen: `assets/candidato-360/arquetipos-bogota/{slug}.webp`, con
    `onerror` que la quita si no existe.
  - ⚠️ **Las 16 imágenes no existen todavía**: son trabajo de §10.
- **05 · Sus barrios**: en pantalla, el top 10; el resto se descarga en CSV
  (`descargarBarrios`, separado por `;` y con BOM para Excel). Vale para las
  tres ciudades.
- `?arqlocal=1` lee los JSON de `Bases de datos/arquetipos-bogota/publicar/`
  para revisar antes de subir.

### El mapa del CRM no se gira al pasar a barrios en Bogotá (oct-19-2026)

`pintarCiudadBarrios` des-giraba los barrios para calzar con el callejero real.
Al bajar de localidad a barrio el mapa se volteaba 90°. Ahora, si la ciudad va
girada (`state.rotado`, solo Bogotá), los barrios se giran igual que las
localidades. El callejero se quita porque ya no calzaría, y el contorno de
unidades usa la geometría girada (`contornoUnidades(..., { girado })`). La vista
de puestos (puntos en coordenadas reales) sigue sin girar y con callejero.

### La campaña de «la misma corporación» se completa en los paneles (oct-19-2026)

Con la ruta «misma corporación», el CRM guarda la campaña **sin territorio**.
Los paneles lo derivan del historial (`territorioDe`), pero el del electorado
leía `campana.departamento` directo y respondía «La campaña no tiene territorio
definido»: sexo y edad no cargaban. Ahora `completarCampana(v)` en
`candidato-360-panel.js` completa `departamento`, `departamentoNombre`,
`municipio` y `localidad` al arrancar **cualquier** panel. Bogotá queda como
`16` + «BOGOTÁ, D.C.». Fuera de Bogotá el departamento sale del slug
territorial más reciente.

### Arquetipos de Cartagena en la tarjeta 05 (sep-27-2026)

Nury entregó la cartografía emocional de Cartagena (6 archivos, originales en
`Bases de datos/proyecto-dc/arquetipos-cartagena/insumos/`, gitignored). La
tarjeta 05 del CRM ya no dice «solo Medellín»: lee Cartagena cuando la campaña
es allá (o sus votos están allá). `ciudadDeArquetipos()` decide entre las dos.

⚠️⚠️ **NO son las cinco familias de Medellín: son OCHO arquetipos propios**
(guardián funcional · gestor vigilante · pragmático de servicios · protesta
resolutiva · defensor territorial · guardián insular · productivo-pragmático ·
mediador comunitario). No se homologan con las de Medellín. Y cada barrio trae
una **mezcla** de los ocho (suma 1), así que los votos de la candidatura se
reparten con esa mezcla, no con el dominante.
⚠️ **2015 es ancla; 2019 y 2023 son proyecciones retrospectivas; 2027 es
simulación.** El modal lo dice («lectura 2023, proyectada»); no presentarlo como
dato observado.

- `tools/candidato-360/arquetipos/build_cartagena.py` → `arquetipos-cartagena.json`
  (fichas + mezcla por barrio y año + volatilidad + sensibilidad + volumen) y las
  8 tarjetas gráficas de Nury en `escudos/{slug}.jpg`. Lema, palancas 1-5 y edades
  están transcritos de esas tarjetas en `TARJETA`; el color es nuestro.
- S3 (público, gzip): `bases de datos/Proyecto DC/arquetipos-cartagena/`. Al
  regenerar, volver a subir con `--content-encoding gzip` y bumpear `?v=` de
  `ARQ_CTG_URL`.
- El barrio casa **por nombre normalizado** con `cartagena-puesto-barrio.js`: los
  211 nombres de Nury son exactamente los 211 de la capa (el builder lo verifica y
  avisa si alguno queda sin arquetipo). Solo sobra «rural / insular agregado».
- Medido con Luz Marina Paria (Concejo 2023): 16.554 de 16.580 votos ubicados,
  35 % en barrios de protesta resolutiva, 22 % productivo-pragmático.
- ✅ **Panel de escucha (sep-28)**: `TERRITORIOS` de `candidato-360-arquetipos.js`
  trae Cartagena con sus propias `familias` (las carga del mismo JSON). El panel
  usa esas en las tres vistas y pondera con la simulación 2027 fuera de «El país».
  La **sensibilidad por tema** (`SENS` en el builder) sale de las **palancas
  temáticas 1-5 del INTEGRADO de Nury** (sección 5), traducidas a los temas de
  la saliencia; lo que ella no calificó se completó en 2-3 leyendo su ficha, y
  `sens_nury` dice cuál es cuál (el panel avisa cuando el tema que activa a un
  arquetipo es inferido). El builder también lee del INTEGRADO el perfil, cómo
  decide, sesgos y las cinco palancas emocionales.
- La **lectura con IA** (`/c360/escucha/lectura`) acepta los 8 slugs: el worker
  lee el perfil del JSON de S3 (`_c360FamiliaTerritorial`), nunca del cliente.
  Desplegado sep-28. Para sumar otra ciudad con taxonomía propia: agregar su URL
  a `C360_ARQ_TERRITORIALES` en el worker y su entrada en `TERRITORIOS`.
- Diccionario de temas: se sumaron LANCHA, MARITIM, MUELLE, EMBARCADERO, FERRY,
  TRANSCARIBE (movilidad) y PESCA, PORTUARI (empleo). ⚠️ «PUERTO» a secas NO:
  marcaría Puerto Colombia o Puerto Boyacá como empleo.

### El voto de lista en los índices viejos y en el detalle por comuna (sep-2026)

Hasta septiembre de 2026 varios generadores descartaban el voto solo por la
lista (`COD_CAN = 0`): Congreso 2014-2022, territoriales 2011-2019 y el detalle
por comuna de los tableros 2023. Con eso el Pacto Histórico salía en cero en el
Concejo de Bogotá 2023 (sus 381.804 votos fueron de lista cerrada) y el mapa de
toda la izquierda bogotana quedaba vacío. Ya está corregido y subido; el
detalle vive en `CLAUDE.md` («Voto de lista en los índices viejos y en el
detalle por comuna»), porque esos generadores son del pipeline de datos del
sitio y no solo de este producto. Para Candidato 360 lo que importa:
`votosFamilia()` recibe un quinto argumento con las `listas` (sin él degrada a
lo de antes), y **falta JAL 2011/2015/2019**.

### Candi v3 atlética · la mascota integrada (sep-2026)

> Hoy el reproductor va en `candi-atletica.js?v=4` y el hueso en
> `candi-hueso.js?v=2`. La especificación gráfica vigente está en §10.3.

Astra rediseñó a Luna más atlética (patas largas, cuerpo esbelto). El
reproductor es **`CandiAtletica`** (`assets/candidato-360/candi/candi-atletica.js`,
`?v=2`), independiente del v2 (`CandiSaludo`, que queda como historial y ya no
se carga). Secuencia local: `enter_greet` (0-3,2 s) → `sit_down` (3,2-4,8 s) →
`idle_seated` en bucle, con la cola baja en poses 8,13,14,15,14,13,8,8. La doc
de Astra está en `ATLETICA-V3-PARA-CLAUDE.md`.

⚠️⚠️ **El globo se cuelga de DOS señales y gana la primera.** Con animación,
`sit_down` (fin del saludo) llega antes que `candi:complete`, que en la v3 se
emite a los 4,8 s, ya sentada — colgarse solo de él retrasaba el globo 1,6 s sin
que nadie lo decidiera. Pero con **movimiento reducido** el reproductor salta
directo al reposo y emite `candi:complete` **sin pasar nunca por `sit_down`**
(verificado forzando la preferencia: eventos `idle_seated` y `complete`, nada
más). Colgarse solo de `sit_down` dejaba el globo esperando los 5 s del
respaldo justo a quien no tiene animación que esperar.

⚠️ La miniatura del botón usa el atlas SENTADO (`candi-sentarse-atenta-v3.webp`),
índice 8 de una grilla 4×4 → `0% 66.6667%` y `background-size:400% 400%`. Las
coordenadas de la v2 no sirven: es otro atlas y otra grilla.

Verificado: saludo **una vez por carga** (abrir/cerrar el panel 3 veces no
dispara ningún estado ni duplica el sprite) · transparencia (el WebP da
exactamente el mismo alfa que el PNG fuente; el «opaco 0 %» que sale al medir
es solo la compresión dejando α=254) · móvil sin desborde (en `t=0` está a
`translateX(132px)` porque entra caminando desde la derecha; desde `t=1600`
queda dentro de los 375 px) · la escena con `pointer-events:none`, así que no
tapa los clics de la tarjeta de abajo.

**Descanso con el hueso rosado** (sep-21-2026 · `candi-hueso.js`, `CandiBoneSequence` de
Astra, doc en `HUESO-PARA-CLAUDE.md`): tras **20 s** sin actividad, estando atenta, Candi
cruza la pantalla, recoge el hueso y se echa. Corre en una **tira fija del ancho de la
ventana** (`.candi-bone-strip`, sin clics, z 899) cuyo suelo (`--candi-suelo`) se alinea con
la escena del dock; `layout()` se envuelve para que arranque donde está la Candi del dock.
⚠️ El reproductor escucha `candi:state` en SU escenario y la mascota lo emite en el dock →
se reenvía. Al despertar, si ya se había ido, se queda **sentada y atenta donde esté** (una
segunda `CandiAtletica` en la tira, la del dock escondida: nunca dos visibles); vuelve al
dock al abrir el panel o al pensar. Si el siguiente descanso la encuentra junto al hueso,
salta a recogerlo (`render(times.walk)`). No descansa con el panel abierto ni con alto
≤520 px (ahí el dock esconde la escena). Verificado 1440 · 1024 · 375 y giro a apaisado.

⚠️ **`curious` NO está conectada**, por instrucción de Ricardo: se está
preparando por separado. El reproductor ya la trae (`mascota.curious()`) y la
doc de Astra la describe; no se llama desde ningún lado.

⚠️ En el pane del navegador la pestaña figura oculta, así que
`requestAnimationFrame` no avanza y la mascota se queda en el cuadro 0 — con el
globo entrando por el respaldo. Una **captura** sí reactiva la pestaña y deja
ver la animación. Y ojo: la **rueda del mouse sobre un mapa Leaflet hace zoom**,
no scroll, y lo colapsa: parece un mapa vacío y no lo es.

### Meta de votos · cuatro escalones y curules oficiales de JAL (sep-2026)

**Cuatro escenarios** (antes tres), todos sobre la misma proyección y en
`escenariosDe` de `candidato-360.js`. El de arriba saltaba ×3 —en el Concejo de
Bogotá, 17.600 → 52.700— porque entre la lista típica y la cifra repartidora no
había nada, aunque en 2023 hubo ocho listas con costos de 9 a 24 mil votos.
- **Inminente** = la mitad del probable (regla de Ricardo: «la votación más baja
  que puede sacar»).
- **Probable** = sin cambios, ya dependía del partido.
- **Posible** = el último elegido de la **siguiente lista más exigente** de 2023,
  la primera que supera en 25 % al probable, traída a 2027 con el margen. Es
  dato observado y depende del partido. Si ninguna lista queda entre probable y
  deseado, el punto medio en proporción (`tipo: 'intermedio'`).
- **Deseado** (violeta, nuevo) = la cifra repartidora: arrastrar la curul sola.

Medido: sin partido 8.800 → 17.600 → 22.300 → 52.700 · Nuevo Liberalismo 4.940 →
9.880 → 12.700 → 52.700 · Alianza Verde 10.500 → 20.900 → 33.200 → 52.700 · JAL
Teusaquillo 870 → 1.740 → 2.530 → 5.620. ⚠️ El salto a **deseado** sigue grande
para las listas baratas (×4 en Nuevo Liberalismo) y es verdad: arrastrar una
curul sola cuesta lo mismo sea cual sea su lista.

**Curules oficiales de JAL**: `vote-target.js` carga `hvp/curules-jal.json` y lo
usa en vez de `inferSeats`. La inferencia —la lista más larga inscrita— se
equivocaba en **374 de 578 Juntas (65 %)**: en Pitalito, Palmira o Arjona cada
partido inscribió un solo candidato y daba 1 curul donde hay 9, así que el
reparto ni se hacía. Sumapaz pasa de 280 a **170** (se calculaba con 5 curules en
vez de 7) y Rafael Uribe Uribe de 2.010 a **1.770**. Cubre el 88 % de las
circunscripciones; el resto vuelve a la inferencia.
⚠️ La llave es `«COMUNA · MUNICIPIO»` normalizada IGUAL en `_llave` (Python) y
`llaveCircunscripcion` (JS); si una cambia sin la otra, dejan de casar en
silencio. ⚠️ En Bogotá el georef guarda la LOCALIDAD en la columna MUNICIPIO: sin
forzar `BOGOTA D.C.` por código, la llave salía «SUBA|SUBA» y no casaba ninguna.

### Módulo 09 · El día de la elección (`candidato-360-diad.html` · sep-2026)

Card 09 del CRM + panel propio. Responde **en cuántos puestos hay que poner
testigo, en cuáles, y qué se va a encontrar cada uno al llegar**. Cálculo
compartido en `candidato-360-diad.js` (`window.C360DiaD`), igual que
`C360Electorado`: la tarjeta y el panel no pueden dar cifras distintas.

⚠️⚠️ **NO se le pide ni se le guarda un dato del equipo del candidato, y es una
decisión de producto, no un descuido.** Los candidatos no suben su base de
datos a una plataforma ajena —lo dijo Ricardo y es la razón por la que el
módulo no gestiona testigos—, y custodiar nombres y celulares de terceros nos
pone en el mismo problema que la HVP. El CSV baja con la columna **«Testigo» en
blanco**: los nombres los pone él en su archivo. La página lo dice explícito y
eso además vende con alguien desconfiado.

**Lo que calcula**, todo con dato público (su votación por puesto + la HVP):
- `plan(mesas, hvp)` agrupa sus votos por puesto y los ordena de mayor a menor
  con el acumulado. Ahí se ve que la votación **no se reparte pareja**.
- `testigosPara(plan, .7)` es la pregunta como de verdad se hace: «quiero
  cubrir el 70 %, ¿cuánta gente consigo?». Los atajos de la UI son 50/70/90/100 %.
- `alertas(seleccion)` avisa qué hay que resolver antes del domingo, en orden
  de lo que más estorba: **sin señal móvil** (el testigo no puede reportar),
  sin internet, **sin dónde publicar el E-14**, acceso difícil, orden público,
  no accesible, sin transmisión de datos.
- `csv(seleccion)` para llevárselo. También imprime (hay `@media print`).

**Medido con un caso real** (Héctor David Chaparro, Cámara Boyacá 2026, 29.916
votos): 312 puestos · **62 testigos cubren el 70 %** · esos 62 suman 1.360
mesas · y **37 de los 62 no tienen señal móvil permanente**. Ese último número
es el módulo entero: sin él, 37 testigos salen el domingo sin forma de
reportar y nadie se entera hasta que ya pasó. El total del plan cuadra al voto
con el índice de endoso.

⚠️⚠️ **El plan es del territorio al que se LANZA, no de la elección anterior** (sep-21-2026,
`C360DiaD.fuente`). Antes armaba siempre con su votación histórica: quien fue a la JAL de
Teusaquillo y va al Concejo de Bogotá recibía un plan de 24 puestos de Teusaquillo. Ahora:
**propio** (su votación) solo con «la misma corporación» o una candidatura previa a esa
corporación dentro del territorio; si no, **territorio**: todos los puestos de la
circunscripción ordenados por los votos de SU FAMILIA POLÍTICA en 2023 (Concejo/JAL por
comuna en las ciudades con detalle; Alcaldía con el Concejo; el resto y lo departamental
con la Asamblea, declarado), con vecinas del espectro si la familia no tuvo lista, y sus
votos de antes marcados en el puesto sin mezclarlos en la cifra. Tarjeta y panel usan la
misma función. Caso Ricardo → Concejo: 943 puestos, 343 testigos para el 70 %. Las
candidaturas nuevas también reciben plan ahora. Bogotá baja 20 archivos (~17 s).

⚠️ **El código de puesto lleva letra en 187 puestos** (`0100199A1`), así que
`codigoPuesto` limpia con `\D` el departamento, el municipio y la zona pero
**no los dos últimos caracteres**: hacerlo los despareja de su hoja de vida.
Es la misma trampa que en `build_hvp.py`.

⚠️ Se carga **solo el departamento** donde tiene votos (`hvpDe` mira sus mesas):
561 ms y 448 KB en el peor caso, contra los 5,9 MB del CSV nacional.

⚠️ Sin votación previa la tarjeta y el panel lo dicen y no inventan un plan:
priorizar al azar es peor que no priorizar. Los 253 puestos del censo sin hoja
de vida salen marcados «sin hoja de vida publicada», no con ficha inventada.

### El discurso por región · `candidato-360-frases.js` (sep-22-2026)

Antes el CRM tenía UNA frase por familia política para todo el país (lo mismo
al centro-derecha en Casanare que en Cali). Ahora `window.C360Frases` tiene tres
capas: **(1)** `DEPARTAMENTOS` (33, por código ELECTORAL) + `CIUDADES` (24,
mandan sobre su departamento) con `tema` y una lectura por espectro (izq · ci ·
c · cd · d); **(2)** `PARTIDOS`, una línea de identidad por organización grande;
**(3)** `dato()`, la frase MEDIDA desde la Asamblea 2023 (municipio o depto) o el
Concejo 2023 en Bogotá: puesto y % del partido, o % y puesto de la familia.
Se usa en `fraseDePartida` (párrafo del CRM), `abrirCRMNuevo` y `copyBriefing`
(tema de la región). `regionDeCampana()` resuelve dónde compite; el dato llega
async y se agrega solo si el párrafo no cambió.
⚠️ Las capas 1 y 2 NO llevan cifras ni nombres de personas (envejecen/exponen).
⚠️ Las frases escritas hablan del voto NACIONAL y el dato es LOCAL, y a veces se
contradicen (Casanare: derecha arrasa en presidenciales, queda 3.ª en la
Asamblea): por eso el dato arranca con «En lo local» y las frases de bastión
dicen «en las presidenciales». Con <1 % la familia «casi no tuvo lista propia»
(no se le asigna puesto en el ranking).

### Escucha social · el cuestionario de entrada (`candidato-360-escucha.html` · sep-19-2026)
Con acceso y vínculo, el panel ya no pregunta «¿tiene perfiles?» sino DOS cosas, ambas
multi-selección: **¿qué redes aprovecha?** (Facebook · X · Instagram · TikTok → decide qué
cuentas se validan y qué se conecta a Apify) y **¿qué medios quiere?** (tradicionales ·
alternativos · de una causa/tema · noticias de mi {localidad|comuna|ciudad o municipio|región,
según la corporación: `escalaLabel`} · nacionales → arma la lectura de Google News).
- Se guardan en `escucha.preferencias` del vínculo (**el worker ya lo acepta en el código,
  `normalizarEscucha` en `rr-auth/src/c360-redes.js`, PERO NO ESTÁ DESPLEGADO**) y en
  `localStorage['c360-escucha-prefs:<email>']` como respaldo; hasta el deploy solo vale el local.
  Se mandan junto con `ideas` para que un worker viejo no responda error.
- **Facebook se guarda sin sondeo** (`REDES_GUARDABLES`, veredicto forzado `sin_validar`): el
  validador `/c360/redes` sigue cubriendo X · TikTok · Instagram. Con el worker viejo, Facebook se
  descarta al guardar.
- `tipoMedio(medio)` en `candidato-360-panel.js`: dos listas curadas (tradicionales /
  alternativos); lo desconocido es «otro» y **no se descarta** (la prensa regional chica no está
  en ninguna lista). Si marca solo una clase, se filtra; si marca las dos o ninguna, entra todo.
- Escalas: territorio y/o nacional según lo marcado; si solo marcó clases de medio, las dos.
  «Causa/tema» enciende el panel de las 3 ideas. «Cambiar lo que escucho» reabre las preguntas.
- Cuentas guardadas de antes del cuestionario se dan por respondidas (sus redes + lectura completa).
- **Modo pruebas también en los paneles** (sep-19): la cuenta admin no escribe vínculos en el
  worker, así que `arrancar()` de `candidato-360-panel.js` lee la candidatura de
  `c360-vinculo-pruebas` (sessionStorage, y localStorage como respaldo para pestañas nuevas) y
  `guardarEscucha` escribe ahí en vez de en `/c360/escucha`. Antes el panel le decía «su cuenta
  no tiene candidatura» justo a quien prueba el producto. La cabecera lo declara.
- `oracion()` ahora pone mayúscula a cada palabra («Barrios Unidos», no «Barrios unidos»).
- Los paneles escucha/electorado no cargaban **Syne** y el logo salía en Manrope: ya la cargan.
- **El briefing obedece las preferencias** (`preferencias_de` en `motor.py`, puerto de
  `tipoMedio`/`agruparPorCobertura`): filtra por clase de medio, suma el bloque «De lo que
  habla el país» si marcó nacionales y un bloque «Sus temas» por idea si marcó «de una causa».
  Para eso el inventario del worker ahora trae `escucha`. **Desplegado el 19-sep-2026.**
  ⚠️ **El deploy por GitHub Actions de `rr-auth` SÍ funciona** (cada push a `src/**` despliega
  en ~1 min). Dos trampas al verificarlo, las dos caídas el 19-sep: (1) `wrangler deployments
  list` lista en orden ASCENDENTE — el primer bloque es el más viejo, el último es el vivo; (2) las
  rutas de la tabla `SERVICIO` (`/caudal/briefs/enviar`, `/c360/briefing/*`, `/gastos/ingest`…)
  responden **404 sin el secreto**, igual que una ruta inexistente: un 404 ahí no dice nada
  sobre el deploy. Para comprobar una versión, mirar la cola de `deployments list`.

### Escucha social · la saliencia mediática (`candidato-360-saliencia.js` · sep-20-2026)

Capa de análisis del panel 04, hermana de la saliencia de Proyecto DC
(`proyecto-dc/agenda.html`). Lee JUNTOS los titulares que el panel ya trajo
(su nombre · su territorio · el país · sus ideas) y no hace consultas propias:
lo analizado y lo listado arriba tienen que ser lo mismo. Todo determinista, en
el navegador, sin modelo. Pestañas Su territorio / El país / Todo; tocar un
tema, actor, medio o palabra lista sus titulares.
- **Síntesis** en una frase (tema que domina, qué sube, tono, más nombrado, si
  usted aparece, a qué arquetipo le habla) · **temas** (11, diccionario de
  raíces) · **a quién nombran** · **nube** · **quién publica** · **ritmo 30 días
  + encuadre** conflicto/gestión · **arquetipos**.
- ⚠️ Raíces de ≤4 letras van como palabra ENTERA («VIA» casaba con «viaje»,
  «ARMA» con «Armando»). Y «Concejo/Asamblea/Alcaldía» NO están en el tema
  política: son las anclas de la búsqueda y se llevaban 47 de 71 titulares en
  Bogotá. Por lo mismo las anclas (`t.entidad`, `t.cuerpo` y su cabeza suelta)
  se excluyen de actores y de la nube.
- Actores: ≥2 palabras en mayúscula; una palabra suelta solo cuenta si es
  institución o apellido de un nombre completo visto en otro titular
  («Galán» → «Carlos Fernando Galán»). La puntuación corta la secuencia y se
  quita el « | Medio» que Google News pega al final.
- «Sin tema» se muestra (medido en Bogotá: 17%).

**Arquetipos · `candidato-360-arquetipos.js`**: las 5 familias de Nury con su
`sens` (1-5) por tema — espejo de `tools/agenda-medios-recomienda/arquetipos.json`,
si cambia allá hay que cambiarlo acá — y el registro `TERRITORIOS`. **Para
conectar los arquetipos de un territorio nuevo basta agregar una entrada** con
`calza(t)` y `cargar()` → `{familia: fracción}`; el panel pasa solo de «perfil
de referencia» a «ponderado por su electorado». Hoy solo Medellín
(`proyeccion-2027-resumen.json`, protección 47% · castigo 24% · continuidad 14%).
Sintonía = promedio de `sens` ponderado por titulares por tema; «hueco» = tema
con sens 5 y <6% de la agenda (la «jugada» sale de ahí, sobre la familia que
más pesa). En la vista «El país» NO se pondera. Siguiente paso natural: la
lectura táctica por arquetipo con DeepSeek (como `agenda-medios-recomienda`),
que exige ruta nueva en el worker.

### Escucha · dónde pasa lo que se publica + lectura con IA (sep-20-2026)

**`candidato-360-geoprensa.js`** cruza cada titular con los lugares del
territorio buscando NOMBRES (no geolocaliza la noticia) y pinta el mapa con las
MISMAS capas de `candidato-360-electorado.js` (sexo y edad): parpadea
(`.sal-on`, mismo patrón que `pega-on`) todo lugar con al menos un titular.
- Ciudad con capa (`E.CIUDADES`): localidades/comunas + barrios. Bogotá y Cali
  suman los barrios catastrales de `candidato-360-data/{bogota,cali}-barrios/`;
  el resto sale del georef de puestos (punto medio de sus puestos, comuna por
  moda). Asamblea/gobernación: municipios del depto. Otro municipio: municipios
  vecinos + barrios/veredas propios (su municipio con borde verde).
- ⚠️ En Kennedy el campo BARRIO del georef trae VARIOS barrios pegados sin
  separador; se descarta todo barrio de >45 caracteres. Y muchos municipios
  pequeños traen «no aplica».
- Reglas anti-falso-positivo, cada una salida de un caso medido: STOP de
  nombres comunes, países, departamentos y PERIÓDICOS («La Patria», «El
  Tiempo»); un barrio sin «barrio/sector/vereda» delante solo cuenta si el
  titular nombra también la ciudad o una unidad (sin esto «Unión Europea» era
  barrio); barrios con nombre de pila («Carlos Lleras») o de una palabra exigen
  esa palabra delante; un nombre de una palabra tiene que ir con MAYÚSCULA en el
  titular original («bello», «remedios»); «Los Andes» no es Andes; «Independiente
  Santa Fe» no es la localidad; localidades de 4 letras (Suba, Usme, Bosa) sí.
  Residual conocido: la primera palabra del titular siempre va en mayúscula.
- Bogotá: la capa va girada 90° y los PUNTOS también (`rot90`).

**Lectura táctica por arquetipo · `POST /c360/escucha/lectura`** (worker
`rr-auth`, desplegado sep-20-2026). El navegador manda el resumen determinista
+ hasta 45 titulares numerados; las 5 familias viven EN EL WORKER (el perfil no
puede venir del cliente). El modelo debe citar números en `evidencia` y el
servidor descarta los inexistentes. Sesión + acceso C360 · 30/cuenta/día ·
caché 6 h · `C360_LECT_PROMPT_V` (subirlo al cambiar el prompt). Se pide a mano
(pastilla por familia), no al cargar. Probado contra DeepSeek con titulares
reales de Bogotá: ~9 s, ~4,6k tokens.

### Escucha · arquetipos de Bogotá y ventana de 3 días (oct-19-2026)

- **Arquetipos:** la escucha de una campaña en Bogotá lee los 8 arquetipos de su
  corporación (la JAL usa los del Concejo), no las cinco familias de referencia.
  Es una entrada nueva en `TERRITORIOS` de `candidato-360-arquetipos.js`
  (`clave` = corporación; la caché va por territorio y clave), y los pesos son
  el voto 2023 de la ciudad. La tarjeta avisa que la sensibilidad por tema es
  **criterio del equipo** (`heuristica`), y cada fila trae «Cómo ganárselo».
  El worker (`C360_ARQ_TERRITORIALES`) suma el JSON de Bogotá, así que la
  lectura con IA acepta esos slugs; lee `quien` y `oficio`.
- **Ventana:** `VENTANA` pasa de 30 a **3 días**, la misma cadencia del
  briefing, porque la escucha mide lo que pasó desde el último correo. En
  `candidato-360-saliencia.js`, «reciente» depende de la ventana: con 7 días o
  menos es hoy y ayer contra el día anterior; con más, la última semana contra
  las anteriores. Así Mi Congreso y contendientes, que usan 30, no cambian.
- **Las redes ya están encendidas en el panel** (`CAPTURA_ENCENDIDA = true`).
  El worker sirve `GET /c360/captura` desde KV (`c360:captura:<email>`); sin
  lectura guardada responde `{ encendida: false }` y la cuenta ve lo de siempre.
  Por red el panel pinta **sus publicaciones que más rindieron** (capa 0),
  **lo que le dicen en ellas** (`comentarios_propios`) y, aparte, la
  conversación de sus temas. Una lectura completa de las cuatro redes
  cuesta ~US$0,85.
- **La lectura corre sola desde el 20-oct-2026**
  (`candidato-360-escucha.yml`, a diario a las 05:30 de Bogotá): `recolectar.mjs`
  pide `GET /c360/captura/inventario`, lee cada cuenta con `captura.mjs` y la
  guarda con `POST /c360/captura/guardar` (rutas de servicio, secreto
  `CAUDAL_ALERTAS_TOKEN`). Entra quien tiene acceso vigente, el **módulo
  `escucha`** y algo que escuchar. El módulo vive en el acceso
  (`_c360AccesoDe` devuelve `modulos`; `/c360/me` lo expone): lo tienen
  administradores, el plan `full` y la cortesía que lo liste
  (`POST /c360/acceso/save {…, modulos: ["escucha"]}`); el plan `c360` pagado
  aún no, falta el SKU. Frenos: una lectura cada ~20 h, US$40 por cuenta al mes,
  US$25 por corrida, y una lectura vacía no pisa la anterior. Detalle en
  `tools/candidato-360/escucha/README.md`.

### Tarjeta 03 · qué sugiere el ciclo de 3 días (`candidato-360-ciclo.js` · oct-19-2026)

La tarjeta del briefing ya no solo prende el correo: dice **qué hacer con lo que
pasó en estos 3 días**, con mapa. `window.C360Ciclo.pintar(ctx)`, llamado desde
`pintarCiclo()` en `candidato-360.js` junto a la tarjeta 05.

- **Insumos**, todos ya existentes: la prensa del territorio (mismas consultas
  que el briefing y la escucha, vía `C360Panel`; caché por hora en
  `sessionStorage` por el límite del proxy de Caudal), la lectura de redes de la
  cuenta (`GET /c360/captura`, si existe), los arquetipos de la ciudad y la
  afinidad del candidato con cada uno. Por eso `candidato-360.html` carga ahora
  `candidato-360-panel.js`, `-saliencia.js` y `-arquetipos.js`.
- **Las ideas de la captura** («seguridad en TransMilenio») se llevan a los
  temas de agenda con el diccionario de la saliencia, para sumarse con la
  prensa. Prensa y redes pesan mitad y mitad cuando están las dos.
- **Prioridad:** `relevancia(arquetipo) = e^(1,2·(activación − media)) ×
  afinidad acotada a [0,5; 2]`, con activación = sensibilidad del arquetipo
  ponderada por el peso de cada tema; `prioridad(barrio) = Σ mezcla ×
  relevancia × electorado × castigo de visita`. Se suma por localidad o comuna
  y salen las 3 primeras, cada una con sus barrios por visitar. El mapa pinta
  la prioridad del barrio contra la ciudad por **quintiles** (con cortes fijos
  casi todo quedaba en los tonos claros).
- **Visitas:** se marcan tocando el barrio en el mapa y se guardan en el
  worker (`GET/POST /c360/visitas`, llave `c360:visitas:<email>`), con copia en
  `localStorage['c360-visitas:<slug>']` de respaldo. Las ve todo el equipo y
  las descuenta el briefing por correo. Hasta 7 días el barrio pesa 35 %; de 8
  a 21, 60 %; después vuelve a contar entero.
- **«Qué llevar»** es el `oficio` del arquetipo más relevante y el tema que lo
  abre hoy.
- Con lectura, la tarjeta ocupa el ancho entero y baja a la segunda fila
  (`order` en la grilla, con `:has`), para no dejar huecos junto a 02 y 04.
- Lo dice en pantalla: describe el territorio, no a las personas, y en Bogotá
  qué tema mueve a cada arquetipo es criterio del equipo.
- Sin acceso, en vitrina o sin token no se pinta (`pintar(null)`). Ciudad sin
  arquetipos: sale el resumen de agenda y redes, sin mapa.

### Toggle estratégico · ¿su voto sigue a las iglesias cristianas? (`candidato-360-iglesias.js` · oct-19-2026)

Bloque plegable al final de la pestaña Territorio del módulo 11. Solo aparece si
alguna candidatura de la persona está en
`candidato-360-data/iglesias-concejo-bogota-2023.json`, que arma
`tools/candidato-360/iglesias/analisis.py` (método y límites en su `LEEME.md`):
10 candidaturas al Concejo de Bogotá 2023, 5 de base cristiana y 5 de control.
Por cada una: razón de participación entre el 25 % de puestos con más templos no
católicos cerca y el 25 % con menos, correlación de rangos y regresión ponderada
con católicos, estrato y estrato², con robustez por efectos fijos de localidad.

- **Medido:** de los cristianos, solo un candidato de MIRA sigue el mapa de
  templos (2,39×, y se sostiene con estrato y localidad). Un control liberal
  también sale alto en la razón simple: las iglesias están en barrios
  populares, por eso manda la cifra con controles.
- ⚠ Templos de OpenStreetMap: contra el catastro aparece el 60 % de los no
  católicos notables, y muchos evangélicos funcionan en locales que ningún
  mapa registra. Es correlación ecológica del territorio, no voto religioso.
- La lectura comparada y la conclusión práctica salen de reglas fijas
  (`veredicto` y `comparada`), no de un modelo.

### Candi · la guía de la plataforma (`candidato-360-candi.js` · sep-20-2026)

> ⚠️ Escrita el 20-sep con la v2. Cambiaron cuatro cosas: **(1)** entra una vez
> por **pestaña** y comenta cada vista una sola vez (§4); **(2)** `sit_down` y el
> reposo sentado **ya existen** (v3, §10.3) — la lista `ESTADOS` /
> `C360_CANDI_ESTADOS` sigue teniendo solo `saludo` porque es la de lo que puede
> pedir el MODELO; **(3)** el atlas que se baja en cada carga ya no es el de la
> v2 sino `candi-sentarse-atenta-v3.webp` (la miniatura del botón); **(4)**
> `C360_CANDI_PROMPT_V` va en **v8**. Además comenta según lo que la persona
> escogió (`TEMAS`, §4). Lo demás sigue vigente.

La mascota tipo Clippy del CRM: es **Luna**, la perrita de Ricardo, y el nombre
de producto es **Candi**. Las poses las dibuja Astra (`assets/candidato-360/candi/`,
atlas de 20 poses, reproductor propio sin dependencias); acá se integró el dock,
el panel y el cerebro. Doc del lado del producto en
`assets/candidato-360/candi/INTEGRACION.md`.

**Es una guía de la PÁGINA, no un chat de datos electorales**: sabe en qué
pantalla está el usuario y explica esa pantalla. Las cifras las pinta el CRM.

⚠️⚠️ **Son DOS capas y la separación es el punto.** La **guía** (`VISTAS`, una
entrada por pantalla) es texto nuestro y está **siempre** —sin sesión, sin red,
sin modelo y sin el atlas—; es además la versión accesible de la mascota. Las
**preguntas escritas** van a `POST /c360/candi` (worker `rr-auth`, DeepSeek,
sesión obligatoria, 40 por cuenta y día, caché de 6 h solo para la primera
pregunta de un hilo · **desplegada el 20-sep-2026**). Cuando falta la sesión, la clave o la ruta, **Candi dice
cuál de las tres falta**: no se rellena el hueco con una respuesta inventada y
atribuida al modelo.

- **Candi entra SOLA al cargar la página, una vez**: camina, saluda, se presenta
  en un globo y se queda quieta en su pose final (el reposo animado todavía no
  existe). Abrir el panel ya NO la hace caminar otra vez, ni lo hacen una
  respuesta, un repintado del CRM o un cambio de pantalla interna.
  ⚠️ **`cerrar()` no llama `pause()`**: la mascota vive en la pantalla aunque el
  panel esté cerrado, y pausar ahí congelaba la entrada a mitad de camino.
  `destroy()` sigue en `pagehide` y el reproductor ya se detiene con la pestaña
  oculta.
- **Habla de TÚ**, y el resto del producto de usted: es la voz cercana contra la
  voz seria de la plataforma, a propósito. El prompt se lo dice explícito para
  que no se contagie del contexto que recibe.
- **Saluda por el primer nombre** (candidatura abierta → wizard → vínculo), pasado
  por `NOMBRE_BONITO` porque el índice lo guarda en MAYÚSCULAS. ⚠️ **Ese nombre
  se arma en el navegador y NO viaja al modelo**; el prompt le prohíbe saludar
  por el nombre justamente porque no lo recibe.
- ⚠️ **Al cambiar el prompt hay que subir `C360_CANDI_PROMPT_V`** (hoy `v2`), que
  entra al hash de la caché de 6 h: el paso de usted a tú habría seguido
  respondiendo de usted durante seis horas.
- **No se nombra al proveedor del modelo en la interfaz** (decisión de Ricardo):
  al usuario no le sirve. La honestidad va en el pie del panel, que dice que las
  respuestas escritas las redacta un modelo y que las cifras salen de la página.
- ⚠️ **`sit_down` e `idle_seated` NO existen** (están en el storyboard, no como
  clip): la animación termina de pie con la pata levantada, sin bucle. La lista
  permitida de estados vive en los dos lados (`ESTADOS` en el frontend,
  `C360_CANDI_ESTADOS` en el worker) y hoy solo tiene `saludo`; lo que el modelo
  pida fuera de ella se descarta. **No anunciar esos estados como hechos.**
- ⚠️ **El nombre de la persona NO viaja al modelo.** El contexto es: pantalla,
  la línea de campaña tal como la muestra el encabezado, la meta en pantalla, el
  paso del formulario y si está en vitrina. Probado en `prueba-candi.mjs`.
- ⚠️ **Al agregar una pantalla hay que tocar DOS sitios**: `VISTAS` (frontend) y
  `C360_CANDI_VISTAS` (worker). Si falta uno, Candi describe mal esa pantalla y
  **nada da error**. `node tools/candidato-360/prueba-candi.mjs` lo detecta.
- ⚠️ El dock va en **z-index 900**, por debajo de los modales (1200): el muro de
  pago y la confirmación del vínculo tienen que taparlo a él. El contenedor es
  `pointer-events:none` y solo el botón y el panel reciben clics, así que el
  área transparente de la mascota nunca le roba un clic al CRM.
- ⚠️ **El `?v=` del `.js` y del `.css`** se bumpea igual que el de
  `candidato-360.js`.
- ⚠️ **El atlas se sirve en WebP (561 KB), no en PNG (2,0 MB)**: se baja en CADA
  carga de la página porque el botón usa su pose final. Es el único cambio que se
  le hizo al reproductor de Astra (una línea). Si ella entrega un atlas nuevo
  llega en PNG y **hay que volver a convertirlo** (`cwebp -q 90 -alpha_q 100 -m 6`)
  y subir el `?v=` de `candi-saludo.js` en la página y en la demo.
- ⚠️ **En el preview headless `requestAnimationFrame` va congelado**, así que la
  animación no corre sola ahí (mismo gotcha de `combate-electoral`): se verifica
  con `seek()` y capturas, no esperando a que avance.

### Briefing cada 3 días (`tools/candidato-360/briefing/` · sep-6-2026 · LISTO)
El push del producto: cada 3 días el candidato recibe prensa de su territorio
(separada entre lo que lo NOMBRA y lo que habla del territorio), contratos
firmados por entidades del orden territorial de su municipio (SECOP, y la
Alcaldía Local aparte si es JAL) y normativa del Ejecutivo que lo mencione.
Todo sale de la Lambda `caudal-analiza` (`medios` · `contratacion` · `ejecutivo`)
leyendo el territorio del vínculo. Corre en **GitHub Actions** a diario
(`candidato-360-briefing.yml`, 07:30 Bogotá); el motor decide a quién le toca.
Rutas: `POST /c360/briefing` (interruptor del panel 03 del CRM) + 3 de servicio
`/c360/briefing/{inventario,estado,enviar}` con el mismo secreto de Caudal.
Doc completa en `tools/candidato-360/briefing/README.md`.
- **Desde el 20-oct-2026 el correo trae la lectura de la tarjeta 03** con la forma
  del correo de Caudal: qué movió la agenda (prensa y redes), a qué arquetipos le
  habla, en qué localidades estar y qué barrios faltan por visitar. El cálculo es
  el mismo JavaScript de la tarjeta corrido en Node (`lectura.mjs`); lo arma
  `correo_ciclo.py`. Si la lectura falla sale el formato anterior. Las **visitas
  pasaron al worker** (`GET/POST /c360/visitas`): las ve todo el equipo y las
  descuenta el correo. Sin arquetipos para la ciudad, el correo sale sin zonas y
  lo dice.
- El secreto `CAUDAL_ALERTAS_TOKEN` ya está en GitHub Actions (desde el
  2-sep-2026) y el workflow corre a diario sin errores (verificado el 8-oct).
- ⚠️ Prensa de ciudades grandes exige actor institucional o localidad en el
  titular (puntaje ≥2): sin eso «Bogotá» traía clima, loterías y vacantes.
- ⚠️ SECOP con `orden_entidad: Territorial` siempre: sin eso salían la UNP y la
  Fuerza Aérea por estar ubicadas en Bogotá.
- La meta de votos se guarda en `campana.meta` (la escribe `pintarMeta`).

### Precios y paquetes (decisión de Ricardo, sep-6-2026)
Base por corporación + LEGO. **Cada módulo cuesta un 30% del plan base de su
corporación**; el full lleva descuento. Anclaje: topes CNE 2023 (Alcaldía de
Bogotá 5.257 millones · gobernaciones 1.392-5.414 millones · JAL 10% del tope
del concejo). El plan viejo de 990.000 para alcaldías era el 0,11% del tope.

| Corporación | Base mensual | Full |
|---|---|---|
| JAL, concejo de municipio no capital | 199.000 | 490.000 |
| Concejo de capital, asamblea | 1.200.000 | 2.900.000 |
| Alcaldía, gobernación | 4.900.000 | 11.900.000 |

Módulos: briefing ✓ · cálculo electoral territorial ✓ · tasa de endoso (rehacer
para territoriales 2027) · escucha social (piso de costo: Apify por cuenta) ·
proyectos de acuerdo Bogotá/Medellín (no existe) · **arquetipos: en el plan JAL
sí se ofrecen, en versión simple** (Medellín ya los tiene por barrio, módulo 05
de Proyecto DC; el resto del país hay que construirlos). El precio del worker
(`C360_PRECIO_COP`) sigue en null: la cifra base por corporación aún no se
cableó porque el plan tendría que saber la corporación ANTES del vínculo.

### Módulo 11 · Estrategia (`candidato-360-estrategia.js` · oct-19-2026 · fases 1 y 2 del plan)

La tarjeta 11 del CRM y su vista ampliada, **dentro de `candidato-360.html`**
(decisión de Ricardo: no hay página aparte). Plan, reglas y fases que faltan en
`tools/candidato-360/estrategia/PLAN.md`; el banco de literatura salió de la
primera consultoría hecha a mano.

- **Banco** (`candidato-360-data/estrategia-banco.json`, 60 KB): lo arma
  `C360_ESTRATEGIA_ANEXO=<ruta> python3 tools/candidato-360/estrategia/build_banco.py`
  leyendo el anexo A (interno, fuera del repo: su ruta lleva el nombre del
  cliente y por eso no va escrita en el código). Pasan los principios, las fichas de tronco y de
  rama, la modulación por arquetipo, las ramas y la matriz; **no pasan** las
  líneas «Para …», el Nivel 3 (el caso) ni la capa B. Una frase del tronco que
  hablaba del caso sin nombrarlo se reescribe en general, y el script aborta si
  queda algo del caso: los términos a vigilar están en
  `Bases de datos/candidato-360/estrategia-prohibido.txt` (fuera del repo; sin
  ese archivo no corre). La prueba lo usa si existe. Lo que agrega el equipo va rotulado: el calendario 2027
  (con estado `ley` · `anunciado` · `derivado`: la Registraduría no ha expedido
  la resolución), las fases, los cuadrantes y las acciones, cada una con sus
  fichas o «criterio de oficio».
- **El orden de los principios** = Σ sobre los arquetipos de (parte en su
  votación × afinidad acotada a ×0,5–×2), normalizado, × la celda de la matriz.
  Va de −1 a 2. Empates por id.
- **La tabla de territorio**: grande = peso en el territorio de la mediana para
  arriba; afinidad alta = ×1,05 o más (el umbral del panel 05). Si el arquetipo
  vota 4 pp o más por debajo de la participación de la ciudad y ya lo prefiere o
  pesa mucho → **movilizar** (rama R2). Barrios fuertes (×1,25 o más) y huecos
  (×0,8 o menos) por arquetipo dominante, solo en barrios con 0,06 % o más del
  territorio (≈1.500 votantes en Bogotá).
- **Figura o barrio**: arraigo ÷ el de la ciudad < 0,75 → figura; > 1,25 →
  barrio. El arraigo solo está medido para el Concejo de Bogotá 2023; una JAL
  sin medida sale «barrio» rotulado como criterio de oficio, y el resto no se
  inclina.
- **Competencia en la lista**: lee la escalera y el plano del panel 10
  (`CONT_LECTURA`; `pintarContendientes` dispara `pintarEstrategia` al
  terminar, con o sin rivales). Lista abierta: el rival principal es el de la
  propia lista más cercano por arriba (o por abajo si ya entra).
- **Lentes**: sus votos; si no tiene en la ciudad, los de su partido o familia
  (`C360ArqLectura.huella`, la del panel 05); si tampoco, la ciudad, y entonces
  no hay afinidad ni cuadrantes. En JAL el territorio es su **localidad**
  (`recortar`), que sale de la campaña, de lo que completó el panel 10 o de la
  localidad con más votos en sus mesas.
- **«Todavía no»**: ciudad sin arquetipos, campaña departamental, Cartagena (8
  arquetipos propios sin fila en la matriz) y la Alcaldía de Bogotá (sus
  arquetipos tampoco tienen fila). La tarjeta lo dice y muestra la fase.
- ⚠️⚠️ **Arquetipo SIN fila en la matriz = «igual», nunca se descarta**
  (oct-19-2026, cuando los de Bogotá pasaron de 6 a 8 por corporación). Entra
  con `codigo: null` y `sinFila: true`: pesa en el denominador (diluye los
  puntajes) con celda 0 en todo, y sale en la tabla de territorio con su
  cuadrante pero sin celdas de la matriz. El resultado trae `sinFila` (parte de
  la votación y nombres) y la vista lo dice. Descartarlo borraba su peso sin
  aviso. **Falta darles fila a los 5 nuevos** (Concejo: «sin-dueno» y
  «opinion»; Alcaldía: «alternativa», «reparte» y «media-alineada»): en el
  concejal de referencia se llevan el 39 % de su votación y en la edilesa más
  de la mitad, así que hoy el orden de los principios lo deciden los otros
  seis. Esa fila es hipótesis del equipo y va en el anexo A, no aquí. ⚠️ Ojo
  también: los seis de antes conservan el slug pero se achicaron (clase media
  de nombre pasó de 41 % a 20 % de la ciudad), así que sus filas de la matriz
  se escribieron para un arquetipo más ancho: conviene revisarlas.
- ⚠️⚠️ **La afinidad del panel 05 reparte con la MEZCLA de cada barrio y la del
  caso hecho a mano usó el arquetipo DOMINANTE.** Mismo dato, dos reglas: para el
  concejal de referencia la «ciudadela movilizada» da **×1,20** (9,7 % contra
  8,1 %) en el producto y ×1,76 (9,9 % contra 5,6 %) en el documento. La mezcla
  aplana los cocientes (sus afinidades van de ×0,90 a ×1,20), y por eso en el
  producto «barrio de gestión» le sale ×0,95 («no gastar») donde el caso decía
  «retener». El motor usa la del panel a propósito, para que las dos pantallas
  no se contradigan; si se quiere la otra regla, se cambia en un solo sitio
  (`afinidad`) y cambian las dos.
- **Vista ampliada**: es una sub-vista DENTRO de `#crm` (`#estrategia`;
  `#crm.crm-en-estrategia` esconde el tablero), no un `.screen`: cada pantalla
  tiene su guía en Candi y en el worker (`prueba-candi` exige que coincidan) y
  esto no la necesitaba. El «← Volver» de la barra la cierra antes de salir del
  CRM. Pestañas Posicionamiento y Territorio; «Plan por fase» y «Formatos»
  aparecen apagadas hasta las fases 3 y 4. El plano de territorio ajusta el eje
  de afinidad a los datos (acotado a ×0,5–×2: un arquetipo marginal con ×0,15
  apilaba todo arriba) y las etiquetas se esquivan entre sí.
- **Vitrina**: la tarjeta se ve completa (lugar, fase, tres principios y acción
  de la semana: es el esqueleto del motor) y «Ver la estrategia» abre el
  paywall, por el mismo listener de captura de los demás módulos.
- **Prueba** `node tools/candidato-360/prueba-estrategia.mjs` (51 comprobaciones,
  ~25 s con red): el banco íntegro y sin el caso, una regla por caso del motor, y
  dos candidaturas reales de Bogotá descritas por su papel, con el orden de los
  principios y la tabla de territorio **fijados**:
  · concejal «figura» con arraigo bajo (7,0 % contra 14,2 %): A7 · A6 · A5 · A1 ·
    A8 · A2 · A3 · A4; retener clase media sin dueño y norte de opinión,
    movilizar en periferia de partido, hacerse conocer en clase media de nombre,
    retener y crecer en ciudadela movilizada (×1,25);
  · edilesa de Barrios Unidos (709 votos, contra su localidad): A7 · A1 · A8 · A6
    · A2 · A3 · A4 · A5; retener norte de opinión y clase media sin dueño,
    hacerse conocer en clase media de nombre y ciudadela movilizada; 3.ª de su
    lista a 910 votos del último elegido.
  Fijado con los 8 arquetipos por corporación (19-oct). Con los 6 de antes el
  concejal daba A7 · A1 · A6 · A8 · A5 · A2 · A3 · A4 y ciudadela movilizada ×1,20.
  Verificado en el navegador (modo pruebas de admin simulado en `localhost`) con
  los dos casos: mismas cifras que la prueba, vuelta al tablero, vitrina con
  paywall y teléfono sin desborde.
- ⚠️ Las pruebas de Playwright del repo importan Playwright desde
  `/opt/node22/…` y Leaflet desde `package/dist`, rutas de otra máquina. En la
  Mac M5 corren con un hook de resolución hacia `/opt/homebrew/lib/node_modules`
  y `LEAFLET_DIST` apuntando a un `npm pack leaflet@1.9.4`. Varias fallan igual
  en `HEAD` (la vitrina en el paso del país, arquetipos por la API vieja del
  modal, una del mapa): son anteriores a este módulo.
- **Cartagena (oct-20-2026) · filas del equipo SIN VALIDAR.** El anexo de la consultoría no traía
  filas para sus 8 tipologías, así que la estrategia de Cartagena nunca se armaba («la matriz del
  banco todavía no tiene una fila»). Las 8 filas viven en `FILAS_EQUIPO` de `build_banco.py`
  (códigos OQC · OAP · BQR · CDV · ODT · QMI · PET · EQR, corte `2023`), redactadas desde el
  diccionario del estudio de Nury (decisión de voto, temas, riesgo de fuga y uso de cada
  tipología). Llevan `fuente: 'equipo-sin-validar'`; el motor expone `R.matrizSinValidar` y la
  página lo dice en la sección 02 y en los dos párrafos. Para cambiar una celda: editar
  `FILAS_EQUIPO` y regenerar con `--anexo <ruta del anexo A>` (la ruta no va escrita aquí: lleva el nombre de la clienta).
- ⚠ **Mapas tras la portada del plan.** La portada oculta el CRM y el mapa se armaba sobre una
  caja de 0×0 (zoom de calle, sin polígonos). `encuadrarBounds` guarda el último encuadre y
  `reencuadrarMapas()` lo repite al abrir una fase (también `C360Ciclo.reencuadrar`).

### Candidaturas por lista cerrada en el historial (oct-19-2026)

En una lista cerrada la Registraduría solo registra el voto al logo: los
candidatos **no existen en el GCS, ni con cero votos**. Por eso quien encabezó
o salió por una lista cerrada «no compitió» ese año en la plataforma. El caso
que lo destapó: un concejal de Bogotá aparecía con 2015 y 2023, y faltaba su
2019, cuando encabezó la lista cerrada de Colombia Justa Libres (101.604 votos
y 2 curules).

- **`candidato-360-data/listas-cerradas.js`** (`window.Candidato360ListasCerradas`),
  curada a mano y con fuente por lista. Trae la **declaratoria original** (los
  reemplazos van en `nota`), el renglón (`null` si no está verificado) y el
  `cabeza` aunque la lista no haya sacado curul. Arranca con el Concejo de
  Bogotá 2019 (Colombia Justa Libres, Coalición Colombia Humana, Colombia
  Renaciente) y 2023 (Pacto Histórico, Creemos, Liga).
- **`candidaturasPorListaCerrada(key)`** en `candidato-360.js` las suma al
  historial de la persona como registros **sin slug ni voto propio**
  (`listaCerrada: {…}`), por la misma llave de persona (`fourNameKey`). No
  duplica un año y una corporación que ya estén en el índice.
- **Mapa:** el botón del año aparece, pero `showElectionYear` muestra
  `mostrarListaCerrada` (votos de la lista, curules, renglón y fuentes) en vez
  de un mapa vacío. El CRM abre en la elección más reciente **con** voto propio,
  y el promedio y la proyección las excluyen.
  ⚠️ Mostrar una lista cerrada quita la capa del mapa: el promedio vuelve a
  pintar una elección real antes de promediar (si no, quedaba en blanco).
- **`candidaturaPuntuada`** y la base del perfil saltan los registros de lista
  cerrada: no tienen mesas.
- Medido: el cabeza de Colombia Justa Libres 2019 queda con «3 candidaturas ·
  2015, 2019, 2023» y promedio de 10.204 (solo 2015 y 2023); el renglón 2 de esa
  lista gana su 2019 y la renglón 7 del Pacto 2023, su 2023.
- ⚠️ **Límite:** quien SOLO compitió por listas cerradas (Heidy Sánchez, Clara
  López en 2019) no aparece en el buscador, porque el buscador nace del índice.
  Hacerlo exige entradas sintéticas en el buscador que abran un CRM sin mapa.
- ⚠️ **Concejo de Bogotá: la cifra repartidora va sobre 44 curules**; la 45 es la
  de oposición. Con 45 el Pacto 2023 saldría con 8 curules y la cifra con 47.726;
  la declaratoria le dio 7, con cifra 49.481. `vote-target.js` ya descuenta esa
  curul (`CURUL_OPOSICION`).
- Para ampliar: agregar una entrada por lista, **con fuente**. Las
  declaratorias (E-26) de concejos no están en línea; sirven las sentencias de
  nulidad electoral, las actas y resoluciones del concejo, las páginas de la
  alcaldía y la prensa con la lista en orden.
- De paso, en `partidos-bloques.js` (y en su copia de `alcaldias-2023.html`):
  **«Bogotá Más Fuerte»** (Nueva Fuerza Democrática + Salvación Nacional), que
  caía en `sc`, queda en derecha; **Libres** queda explícito en derecha (ya caía
  ahí, pero por parecido con «Justa Libres»).

### Verificar (casos reales para probar)
```bash
python3 -m http.server 8767   # o preview_start "ricardoruiz-alt2"
node --check candidato-360.js
```
Casos reales: `claudia nayibe lopez` (3 candidaturas, toggles por año y recorte) ·
`ricardo esteban ruiz castro` (JAL Teusaquillo 2015, mapa por localidad). Para probar el gate
sin tocar producción: `preview_start rr-auth-dev` + sembrar `sessions:`/`users:` en el KV
local con `wrangler kv key put --local --binding RR_STORE` y una copia del HTML con
`window.RR_RUNTIME_CONFIG={authBase:'http://localhost:8788'}` (borrarla después).

### Portada del CRM: el plan de campaña por fases (`candidato-360-plan.js` · oct-20-2026)

Antes de los módulos, el CRM saluda («Hola, Emel. Este es su plan de campaña.»)
y muestra cinco fases: **Planeación · Posicionamiento · Campaña · Remate · Día
de la elección**. Solo las dos primeras están abiertas; las otras se ven con su
fecha y lo que van a traer. Al abrir una fase se ocultan los módulos que no le
sirven y **11 · Estrategia va de primera**.

| Fase | Fechas | Módulos |
|---|---|---|
| Planeación | ahora | 11 · punto de partida · 02 · 05 · 06 · 10 · 08 · 07 · 01 (el mapa al final) |
| Posicionamiento | hasta el 28-feb-2027 | 11 · 03 · 04 · 05 · 10 |
| Campaña | 1-mar al 24-sep-2027 (cerrada) | 11 · 03 · 04 · 08 · 10 |
| Remate | 25-sep al 23-oct-2027 (cerrada) | 11 · 03 · 04 |
| Día de la elección | 24 al 31-oct-2027 (cerrada; se prepara una semana antes) | **09** |

Las fechas salen del calendario del banco de estrategia (posicionamiento hasta
febrero, inscripción en junio-julio, propaganda desde el 31-jul). ⚠ Mientras el
Día de la elección esté cerrado, **09 no aparece** en ninguna fase. Abrir una
fase es `C360Plan.abrir(id)`; la portada se pinta en cada apertura del CRM
(`C360Plan.mostrar()` tras `showScreen('crm')`). No toca el cálculo de ningún
módulo: solo muestra u oculta tarjetas (clase `plan-fuera`).
- **Las fases cerradas también se abren (22-oct-2026, pedido de Ricardo)**: la
  tarjeta gris dice «Ver qué trae →» y adentro salen sus módulos **en gris, sin
  color y sin responder al clic** (`#crm.plan-cerrada`: `opacity .45` +
  `grayscale` + `pointer-events:none` sobre la rejilla, el punto de partida, el
  mapa y la estrategia), con un aviso bajo la cabecera («Todavía no se abre.
  Esta fase se abre el 1 de marzo de 2027…» y la lista de lo que trae). El
  Volver de la barra sigue activo. Antes eran `<div aria-disabled>` y no se
  podía ver qué había adentro. Verificado en el navegador con Campaña (5
  módulos en gris) y Día de la elección (solo 09).
- ⚠️⚠️ **El mapa del CRM salía EN BLANCO a veces (22-oct-2026, lo reportó
  Ricardo con el JAL de Teusaquillo).** La portada del plan deja el CRM en
  `display:none` mientras el mapa se arma; `fitBounds` con la caja en 0×0 le
  resta el padding al tamaño, saca un ancho **negativo**, el logaritmo da NaN
  y **el zoom de Leaflet queda en NaN**. Desde ahí cada `invalidateSize` revienta
  con «Invalid LatLng object: (NaN, NaN)» ANTES de llegar al `fitBounds`, así
  que el reencuadre de `C360Plan.abrir` no servía y el mapa quedaba vacío para
  siempre, aunque la caja ya midiera 975×520 (reproducido: `getZoom()` → NaN,
  23 `<path>` en el DOM, nada visible). Arreglo en `encuadrarBounds`
  (`candidato-360.js`) y en `reencuadrar` de `candidato-360-ciclo.js`: no se
  encuadra sin caja, si el zoom ya es NaN se le devuelve una vista válida con
  `setView` antes de medir, y un `ResizeObserver` sobre `#crmMap` vuelve al
  último encuadre cuando la caja pasa de 0 a su tamaño. Era intermitente por
  la carrera entre el fetch de la geometría y la apertura de la fase.
  - **Segunda pasada el mismo día** (los pantallazos de Ricardo seguían
    mostrando el mapa en blanco por barrio y el del ciclo chico): el mapa del
    ciclo (`candidato-360-ciclo.js`) gana su propio `ResizeObserver`,
    `zoomSnap: 0.1` (con 0.25 redondeaba hacia abajo y la ciudad quedaba hasta
    un 19 % más chica) y se encuadra por los **barrios con prioridad**
    (`boundsConDato`), no por todo el catastral. Medido: el catastral
    simplificado de Bogotá va de 4,469 a 4,833 de latitud, sin barrios lejanos
    que estiren el marco; lo que lo dejaba chico era encuadrar con una caja de
    otro tamaño. ⚠ No se pudo reproducir en local: la tarjeta 03 necesita la
    prensa de la Lambda, que desde `localhost` da CORS.
  - **«Proyectado» mostraba Teusaquillo en vez de Bogotá** (JAL → Concejo): en
    local el salto reparte bien (Suba · Kennedy · Engativá). Lo único que lo
    explica es reabrir desde el vínculo con una campaña cuya `ruta` no diga
    `other`: `precargarCampana` caía a «misma corporación», el CRM abría como
    JAL y sin salto. Ahora también es «otra» cuando `campana.corp` difiere de
    la corporación del historial. Por verificar con la cuenta real de Ricardo.
- **Cada fase lleva una ilustración**: desde el **22-oct-2026 son pictogramas
  planos y serios** (figuras tipo señalética, azul noche sobre papel, con un
  acento verde azulado y uno coral; sin texto ni símbolos de partido), porque
  las isométricas pastel estilo Monument Valley del 20-oct **no gustaron**.
  `assets/candidato-360/fases/{planeacion,posicionamiento,campana,remate,dia}.webp`,
  960×640, 12-27 KB. Generadas con Canva (`generate-image`) y guardadas en el
  lienzo «Lienzo blanco horizontal» (DAHYbZIQ4-I), **páginas 39 a 43** (las 34
  a 38 son las Monument Valley, que quedan ahí y en git por si se quieren
  comparar). Para cambiar una: regenerar, meterla como página del lienzo y
  exportar en JPG a 960×640 → `cwebp -q 82`. ⚠ El tool de Canva solo devuelve
  miniaturas de 200 px de lo generado: la resolución completa sale por
  `export-design` de una página del lienzo, por eso el paso intermedio. ⚠ La imagen lleva `width`/`height` en el HTML: el CSS
  necesita `height:auto` o la proporción 3:2 no aplica.
- **Al abrir una fase no hay barra de navegación**: arriba sale la imagen, el
  nombre y un párrafo que explica la fase. Para volver a las fases está el
  «Volver» de la barra superior (desde la estrategia vuelve a la fase; desde la
  fase, a la portada).
- **Tarjeta 11 · Estrategia**: en vez de la lista de principios, un discurso
  personalizado (`discursoEstrategia()` en candidato-360.js) según la
  corporación (lista o uninominal, lista cerrada), la ciudad, el partido o la
  familia política y lo que dicen sus datos (`R.lugar`), sobre por qué la
  estrategia es la parte estructural de la campaña. Debajo sigue «Esta semana».
  La vista ampliada abre con **«Su estrategia, en dos párrafos»**
  (`estrategiaEnDosParrafos()`: el lugar y dónde pesan sus votos; la fase, los
  tres principios que más le sirven, la pelea en su lista y la acción), y el
  panel de la fase trae un párrafo que la explica (`FASE_PARRAFO`, por id del
  calendario del banco). Todo sale de datos ya calculados: sin modelo de
  lenguaje. ⚠ Las frases por familia asumen gobierno nacional de derecha en
  2026-2030 (mismo supuesto que el copy del briefing).

### Contendientes: quien hoy ocupa un cargo no compite (oct-20-2026)

`candidato-360-data/cargos-actuales.js` (de
`tools/candidato-360/contendientes/build_cargos.py`) lista **285 congresistas
2026-2030, 1.132 alcaldes y gobernadores 2024-2027** (el más votado de cada
circunscripción en los índices de 2023) y **218 nombrados del gobierno nacional
desde el 7-ago-2026** (Diario Oficial, sin cédulas). En **Bogotá, Medellín, Cali y
Cartagena** (`revisadas`) quien aparezca ahí —o tenga las marcas
`congresista-2026`, `en-ejercicio` o `titular-no-reelegible`— **sale de la lista y
del plano**; la tarjeta y el panel dicen cuántos y quiénes (`L.excluidos`). En el
resto del país sigue lo de antes (marcados pero dentro). Para sumar una ciudad:
revisar los cruces y agregarla a `REVISADAS` en el builder.
- Revisión del 20-oct (Concejo y Alcaldía 2023/2019 y Congreso 2026): fuera de
  senadores, 18 cruces y todos correctos (Galán, Rodrigo Lara, Briceño, Gordillo,
  Forero, Nicolás Gómez; Fico, Nataly Vélez, Carrasquilla, Simón Molina…).
- ⚠ **La regla de nombre cuenta palabras repetidas.** Con un `Set`, «Santiago
  Montoya Montoya» (senador) casaba con «Santiago Perdomo Montoya»; el
  `esCongresista` de antes tenía el mismo error y ya está corregido.
- ⚠ Pendiente: las atípicas 2025-2026 (Bucaramanga, Tunja, Cartago, Girón…)
  cambiaron al alcalde de 2023 y aquí sigue el de 2023.
- La prueba `prueba-contendientes.mjs` falla en «Concejo · H9» (72 sin familia
  política contra 37 esperados) **desde antes de este cambio**.

### La lectura de redes es de la candidatura, no de la cuenta (oct-20-2026)

La captura vive en `c360:captura:<email>`, pero una cuenta puede probar otra
candidatura (vínculo local) o soporte puede cambiarle el vínculo. Probando con
su propio nombre, Ricardo veía las cuentas de otra candidatura. Ahora la página
de escucha, la tarjeta 03 y el worker (`GET /c360/captura` y el inventario del
briefing) solo usan la lectura si `captura.vinculo.nombre` coincide con la
candidatura abierta (todas las palabras de uno caben en el otro; lecturas viejas
sin nombre pasan).

### Arquetipos de Medellín y Cartagena · nombres nuevos del estudio (oct-20-2026)

> ⚠️⚠️ **CORRECCIÓN DEL 22-OCT-2026 · Los nombres nuevos de Medellín son SOLO de
> Proyecto DC, no de Candidato 360.** Nury lo señaló: «está arrastrando los
> nuevos arquetipos de DC como de Medellín completo». La entrega del 1-oct era
> para Proyecto DC (el hub, su agenda y `escenarios-2027`); los arquetipos que
> Candidato 360 ya tenía para Medellín (`Protección con resultados`, `Castigo y
> alternancia`, `Continuidad pragmática`, `Supervivencia económica`,
> `Pertenencia comunitaria`, con sus textos de activa/desmoviliza/fuga/tono/
> canales) son de aquí y **no había que reemplazarlos**. Deshecho en Candidato
> 360 sin tocar Proyecto DC ni el JSON de S3:
> - `candidato-360-arquetipos.js` · `FAMILIAS` vuelve a los nombres y textos
>   de antes del 20-oct (es lo que leen la escucha, el ciclo y la estrategia).
> - `candidato-360-arq-lectura.js` · el nombre 2027 de Medellín en el panel 05
>   sale de `evol.nombre_anterior` (que el build del 20-oct dejó en el JSON de
>   S3) y solo cae a `evol.nombre` si no existe: `nombre27(f)`.
> - `?v=20261022` en `candidato-360.html`, `-arquetipos.html` y `-escucha.html`.
> - Cartagena NO se tocó: sus ocho tipologías con nombre nuevo siguen en el
>   panel 05 (esa parte de la entrega no era de DC). Si el estudio también las
>   quiere atrás, `build_cartagena.py` dejó `nombre_anterior` en su JSON.
> Lo de abajo describe el cambio del 20-oct tal como se hizo; sigue valiendo
> para Proyecto DC.

Dos entregas del estudio del 1-oct-2026 (en `Bases de datos/proyecto-dc/entrega-nury-*-20261001/`,
fuera del repo). **Las dos son de nombre y de lectura, no de cifras**: se
compararon celda por celda contra los Excel vigentes y ningún voto, mezcla,
dominante, probabilidad ni barrio cambia. Los slugs se quedan (son la llave en
datos, imágenes y código).

| Medellín · slug | Nombre 2027 nuevo | Antes |
|---|---|---|
| `proteccion` | Resultados Primero | Protección con resultados y orden competente |
| `castigo` | Ojo Abierto | Castigo a la restauración y demanda de alternancia |
| `continuidad` | Confianza Cercana | Continuidad pragmática y gestión barrial |
| `supervivencia` | Hogar Seguro | Supervivencia económica y servicios cotidianos |
| `pertenencia` | Orgullo de Barrio | Pertenencia comunitaria y autonomía territorial |

Los nombres base 2015-2023 no cambian. Cartagena pasa a llamar la categoría
«tipología de votante» y renombra las ocho: `guardian-funcional` Orden que
Cumple · `gestor-vigilante` Ojo al Poder · `pragmatico-servicios` Barrio que
Resuelve · `protesta-resolutiva` Cambio de Verdad · `defensor-territorial`
Orgullo de Tierra · `guardian-insular` Que Miren la Isla · `productivo-pragmatico`
Primero el Trabajo · `mediador-comunitario` El que Responde (tabla en el
`README_CAMBIOS_TIPOLOGIAS_CARTAGENA.txt` de la entrega).

- **Medellín.** `build.py` toma la hoja 2027 del Excel nuevo (tercer argumento)
  y escribe la lectura 2027 de la matriz actualizada en `evol` de
  `arquetipos.json`: disposición, demanda, condición de cambio, tipo de
  decisión, temas, registro, perfil, canales, factores cognitivos y hacia dónde
  se mueve; `nombre_anterior` guarda el viejo. Cambian solo `arquetipos.json`
  y `proyeccion-2027-resumen.json`; los otros cinco salen idénticos byte a byte.
  `votacion-2027.json` guarda slugs y sale igual: no se vuelve a subir.
  ⚠️ En el Excel nuevo de evolución las hojas 2015/2019/2023 llegaron con
  fórmulas rotas (`#REF!`); el build no las lee.
- **Cartagena.** `build_cartagena.py` lee la entrega rehecha (los patrones de
  archivo casan con las dos versiones), suma del diccionario nuevo
  `descripcion`, `decision`, `riesgo_fuga` y `uso`, y deja `nombre_anterior`.
  La ficha del panel 05 muestra «Cuándo se aleja».
- **Imágenes.** Emblemas 2027 de Medellín en `arquetipos/escudos/{resultados-primero,…}.jpg`
  (llaves nuevas) y afiches de Cartagena en `arquetipos-cartagena/tipologias/{slug}.jpg`
  (antes `escudos/`, que traen el nombre viejo pintado).
- **En frase**, los nombres de Cartagena van entre comillas y con sus
  mayúsculas («vota desde el arquetipo «Primero el Trabajo»»): en minúscula se
  leían como frase suelta. Medellín y Bogotá siguen igual.
- **`?arqlocal=1`** ahora sirve también para Medellín y Cartagena (panel 05,
  `proyecto-dc/arquetipos.html` y `escenarios-2027.html`): lee los JSON que dejan
  los build en `Bases de datos/` para revisar antes de subir.
- **Sin aplicar, esperan visto bueno: las sensibilidades.** La matriz nueva de
  Medellín recalibra 11 celdas de las 40 y la de Cartagena trae una matriz 8 × 11
  completa del estudio, hecha sobre las palancas de este simulador. Medido con
  la regla de la Simulación (barrios que cambian de dominante): Cartagena,
  escándalo 86 → 15, inseguridad 23 → 3, crisis de agua 18 → 2 (su matriz es
  pareja, 3-5 en casi todo, y el simulador mueve por la diferencia con la media);
  Medellín, crisis de agua 3 → 28, lluvias 0 → 12, golpe económico 15 → 4. Por
  eso `sens` sigue siendo la de antes en `candidato-360-arquetipos.js`,
  `build_cartagena.py` y `escenarios-2027.html`.
- ⚠️ Quedan con los nombres viejos, fuera de este cambio: el worker (`rr-auth`,
  lectura de noticias de la tarjeta 04), `tools/agenda-medios-recomienda/arquetipos.json`,
  `tools/proyecto-dc-escenarios-estrategia/` y `tools/test-presidencial-explica/`
  (lambdas, piden despliegue), y `brujula-2027.html`, `dashboard-general.html` y
  `elpais-cali-dashboard.html`. El banco de estrategia solo usa códigos.
