# Monitoreo de contendientes · `candidato-360-contendientes.html` — plan de trabajo

Tarjeta **10** del CRM (después de 09 · Día D) y panel propio, con el mismo
patrón que el endoso (08) y el Día D (09): un **motor compartido sin DOM**
(`candidato-360-contendientes.js`, `window.C360Contendientes`) que llaman la
tarjeta y el panel. **Los dos no pueden dar cifras distintas.**

Responde tres preguntas, en este orden:

1. **¿Contra quién compite?** Quiénes son, de qué familia política y cuánto se
   cruzan con su base (el plano).
2. **¿Dónde se va a pelear el voto?** Los puestos, barrios y comunas donde su
   base y la de sus rivales cercanos coinciden (el mapa de disputa).
3. **¿Qué se movió desde el mes pasado?** Quién entró, quién cambió de aval,
   quién apareció en prensa (la revisión mensual).

Estado: **fases 1 y 2 hechas (28-sep-2026)** —ver la bitácora al final—. Las cifras de abajo salen de una
medición hecha el 28-sep-2026 sobre los archivos de S3 que se citan; en la fase
1 quedan fijadas en `prueba-contendientes.mjs`, como las del endoso.

---

## 0. Lo que se midió antes de escribir el plan (y que cambió el diseño)

Dos casos reales con datos completos: la **JAL de Barrios Unidos** y el
**Concejo de Bogotá**, con la misma persona como candidatura de referencia —una
edilesa de Barrios Unidos 2023 (lista abierta de Nuevo Liberalismo, 709 votos,
no elegida) que se relanzaría a la JAL o saltaría al Concejo—. Los rivales se
describen por su papel, no por su nombre: este repositorio es público y un
documento que pone a personas reales en un ranking de «presión» no tiene por
qué nombrarlas.

| # | Hallazgo | Consecuencia para el diseño |
|---|---|---|
| H1 | **Dentro de una JAL el eje territorial casi no separa.** Barrios Unidos: 32 puestos, 67 rivales con ≥50 votos; la afinidad territorial (§3.2) va de **0,76 a 1,11** y **65 de 67** caen en la franja «mismo terreno» (0,85–1,15). Una localidad es un territorio chico y parejo: todos pescan en los mismos puestos. | La tarjeta lo dice en vez de dibujar diferencias que no existen. En la JAL lo que separa a los rivales es **la lista y la familia**, no el territorio. |
| H2 | **En un salto de corporación sí separa.** Concejo de Bogotá con su base de la JAL: 943 puestos, 434 rivales; afinidad de **0 a 10,6**; 118 altos (≥1,15), 140 en el medio, 176 bajos (corregido al verificar: la medición inicial redondeaba a dos decimales y daba 119/175). | El eje Y sirve en concejo, asamblea y cuando la base propia es más chica que el territorio. |
| H3 | **Su rival más fuerte en la JAL es de su propia lista.** Los dos primeros del índice (§6) son los dos elegidos de Nuevo Liberalismo en 2023. Ella fue **3.ª de su lista, a 910 votos del segundo elegido**. | La escalera dentro de la lista (§5) no es un adorno: en lista abierta es la competencia que decide. |
| H4 | **Los dos ejes dicen cosas distintas y los dos hacen falta.** En el Concejo, dos concejales elegidos del Centro Democrático rinden **1,45 y 1,28** en su base (compiten por el mismo territorio) pero están a 3 pasos en el espectro. Los 12 primeros del índice son todos de centro-izquierda (Verde y NL); el primero es una candidata **no elegida** de Alianza Verde con 9.588 votos y afinidad **1,86**. | Un solo eje engaña. Y quien no salió elegido puede ser el rival más directo: por eso el registro entra completo, no solo los que ocupan el cargo. |
| H5 | **La prensa casi no sirve hoy para descubrir aspirantes.** 60 días de Google News (acción `medios`): «"Concejo de Bogotá" precandidato» → 9 titulares, ninguno sobre aspirantes al Concejo; «"Concejo de Bogotá" 2027 aspira» → 2, ninguno; «"JAL de Barrios Unidos"» → 53 titulares de la localidad, ninguno de aspirantes. | Hoy la fuente principal es el **registro**. La prensa se usa para **vigilar nombres ya conocidos**, y crece en 2027. |
| H6 | **Por nombre, la prensa de un concejal es escasa y ruidosa.** 30 días, 7 nombres: el alcalde 64 titulares en 19 medios; dos concejales 5 y 8 titulares (4 medios); 4 de 7 nombres **cero**; y un nombre devolvió **2 falsos positivos** (un futbolista homónimo y un comunicado de la Corte). | La alerta exige el nombre completo en el titular (la regla `menciona_persona` del briefing). En JAL, contar con cero. |
| H7 | **El nombre del partido cambia entre corporaciones.** La misma lista es «NUEVO LIBERALISMO- AGRUPACION POLITICA EN MARCHA» en la JAL y «NUEVO LIBERALISMO EN MARCHA» en el Concejo. `listaDelPartido` de `vote-target.js` **no las casa** (exige todas las palabras del núcleo y sobra «AGRUPACION»). | «Su lista» se resuelve con el partido del **catálogo** que eligió en la ruta, no con el de su candidatura anterior. **Corrección al medir P9:** el catálogo marca ese nombre de la JAL como coalición y no lo ofrece, así que en la práctica el caso es «AGRUPACIÓN POLÍTICA EN MARCHA» (ver la bitácora). |
| H8 | **El reparto reconstruido reproduce el cabildo real.** Concejo de Bogotá: Verde 8 · NL 8 · Pacto 7 · CD 7 · Liberal 6 · CR-MIRA-U 4 · LARA 2 · Conservador 1 · Bogotá Más Fuerte 1 (44 + la curul de oposición = 45). JAL Barrios Unidos (9 curules oficiales): Liberal 2 · CD 2 · NL 2 · Verde 1 · Pacto 1 · CR-MIRA 1. | «Quién ocupa el cargo» sale del reparto que ya calcula la meta, no de una fuente nueva. |
| H9 | **El «no sabemos» pesa.** Concejo de Bogotá: **72 de 434** rivales sin bloque o con aval amplio, **171.499 votos**, incluido el concejal **más votado** de 2023 (movimiento local). JAL: 10 de 67. | La franja «no sabemos» del eje X no es una nota al pie: va dibujada. |
| H10 | **Algunos ya no van a competir por esto.** De los 120 más votados al Concejo de Bogotá 2023, **1** es hoy representante a la Cámara (cruce contra `legislativo-electos.js`). | Marca «hoy es congresista (2026-2030)»: sigue en la lista, pero no en el índice. |

---

## 1. Datos: qué existe y qué falta (verificado abriendo los archivos)

### Existe

| Qué | Dónde | Qué trae | Cobertura |
|---|---|---|---|
| Registro de candidaturas | `cand-index.js` → `<corp>-<año>/index-*.json` | nombre, slug, corp, partido, votos; `listas[]` (voto de lista, personal, total, cerrada) | 2011-2026, 439.015 candidaturas |
| Una candidatura mesa a mesa | `<corp>-<año>/<slug>.json` | `mesas[]` con dep, mun, zon, pue, mesa, com, comNom, `v` | todas |
| **Matriz candidato × puesto (concejo y JAL)** | `concejo-2023/comuna/{dde}-{mme}-{com}.json`, `jal-2023/comuna/…` | `cands[[nombre, idxPartido]]`, `partidos`, y por puesto `v[[idxCand, votos]]` + `l[[idxPartido, votosLista]]` + válidos, lat/lon, barrio; también por barrio y mesa | **11 ciudades**; Bogotá = 20 archivos, 11 MB descomprimidos |
| **Matriz candidato × puesto (asamblea)** | `asamblea-2023/mun/{dde}-{mme}.json` | la misma forma, por municipio | **los 1.118 municipios** |
| Totales por puesto | `totales-puesto/<corp>-<año>.json` | `[válidos, votantes, blanco]` | 26 elecciones 2011-2023 + Congreso |
| Reparto de curules | `vote-target.js` → `reconstructedCutoff` | curules por lista, cifra repartidora, umbral; **internamente** la lista de elegidos | todas las corporaciones plurinominales |
| Curules oficiales de JAL | `hvp/curules-jal.json` | 875 Juntas | 88 % de las circunscripciones |
| Familias políticas | `partidos-bloques.js` | `bloqueDeCandidatura`, `esAvalAmplio`, `BLOQUE_ORDER` | nacional + movimientos regionales medidos |
| Congresistas 2026-2030 | `legislativo-electos.js` | 285 electos | completo |
| Prensa | worker `/caudal/api`, acción `medios` | titulares de Google News por consulta | ver H5 y H6 |
| Temas y actores de prensa | `candidato-360-saliencia.js` | `analizar`, `temasDe` | cualquier lista de titulares |
| Recorte al territorio, georef, comuna | `candidato-360-endoso.js` | `alcanceDe`, `enAlcance`, `areaDe`, `comunaDesde` | todo |
| Base de la familia política | `candidato-360-diad.js` → `C360DiaD.fuente` | votos por puesto de su familia en 2023, con caída a alcaldía y vecinas | todo |
| Capas del mapa | `candidato-360-electorado.js` (`CIUDADES`), `BARRIOS_DIC` del CRM | localidades, comunas, UCG, barrios | Bogotá, Cali, Cartagena + 11 ciudades por comuna |

⚠️ La matriz por comuna pierde ~1 % de los votos: los puestos de 2023 que ya
no están en el georef de 2026 (medido: un concejal pasa de 49.894 votos en el
índice a 49.193 en la matriz). Ya estaba documentado para los tableros de 2023;
el panel lo declara.

### Falta

| # | Qué | Por qué hace falta | Cómo |
|---|---|---|---|
| **D1** | **Matriz candidato × puesto para el resto**: concejo y JAL fuera de las 11 ciudades, alcaldía y gobernación (todas), y 2019 | Sin ella hay que bajar el JSON de cada rival: 435 en Bogotá. En un municipio pequeño son 30-150 archivos chicos, viable pero lento. | `build_matriz_puesto.py`, una pasada por los GCS como `build_totales_puesto.py`: un JSON por circunscripción `{cands, partidos, puestos:{code:[[i,v]…]}, listas}`, comprimido. Prioridad: concejo 2023 fuera de 11 ciudades → alcaldía 2023 → gobernación 2023 → 2019. |
| **D2** | **Elegidos 2023 expuestos** | `reconstructedCutoff` arma la lista de elegidos y no la devuelve. | Exportar un helper `electos()` de `vote-target.js` **sin cambiar cifras** (la prueba de la meta lo cuida). |
| **D3** | **Inscripción oficial de 2027** (RNEC) | Es la única fuente que dice quién compite. Llega a mediados de 2027. | Cuando exista: reemplaza la inferencia (fase 7). Hoy no existe. |
| **D4** | **Cambios después de 2023** (renuncias, reemplazos en el cargo, sanciones, fallecimientos) | El reparto reconstruido dice quién ganó, no quién ocupa hoy la curul. | No hay fuente estructurada. Se declara («ganó la curul en 2023»), y la revisión mensual permite corregirlo a mano. |
| **D5** | **Snapshot mensual por territorio** | Para decir «revisado el …» y qué se movió. | Worker `rr-auth`, KV (§8). |

---

## 2. Quién es contendiente antes de la inscripción

Hasta mediados de 2027 nadie está inscrito: todo lo que la tarjeta muestre es
**una lista de rivales probables**, y el nombre de la sección lo dice.

### Las fuentes y su confianza

| Fuente | Regla | Sello en la ficha | Automática |
|---|---|---|---|
| **A · Ocupa el cargo** | Elegido en 2023 en la misma corporación y circunscripción (reparto reconstruido, D2). En alcaldía y gobernación: **el titular no puede ser reelegido para el período siguiente** (C.P. arts. 314 y 303), así que sale del índice y queda como referencia («su sucesor natural es su partido»). | «Ganó la curul en 2023» | sí |
| **B · Compitió ahí en 2023** | Misma corporación y circunscripción, con votación ≥ **50 % del último elegido de su lista** (en lista cerrada: la lista, no la persona). Umbral a decidir (P7). | «Compitió aquí en 2023» | sí |
| **C · Tiene base en el territorio** | Candidatura 2015-2026 de otra corporación o año, con votos **recortados al territorio** (`enAlcance`) ≥ el mismo umbral. Es el edil que sube al concejo o el representante que baja a la alcaldía. | «Tiene votos aquí (Cámara 2026)» | sí |
| **D · Nombrado en prensa como aspirante** | Nombre completo en un titular con vocabulario de aspiración (aspira, precandidato, se lanza, aval, inscribe) y el territorio; **≥ 2 medios distintos**; revisado por una persona antes de publicarse (§8). | «Dicho en prensa · N medios» + enlaces | no, revisado |
| **E · Lo agregó usted** | Buscador del registro (`acRank`) o nombre libre. | «Lo agregó usted» | — |

**La unión** va por persona: `CandRegistry.personaKey` (con `ALIAS_PERSONA`) y
las reglas de `agruparPersonas` del CRM (cuatro componentes iguales; tres solo
en el mismo departamento). Una persona con varias fuentes muestra todas, y el
sello de mayor confianza manda. Los homónimos dudosos (los mismos 131 + 83 casos
de `candidato-360-data/homonimos/`) no se funden: salen como dos, con aviso.

**Marcas, no filtros** (quedan en la lista, salen del índice):
- «Hoy es congresista (2026-2030)» — cruce con `legislativo-electos.js` (H10).
- «Compitió en 2023 por otra lista» — cambió de partido; el eje X usa el aval
  **más reciente** y la ficha lo muestra.
- «Lista cerrada» — el orden lo decide el partido: no hay rival personal
  dentro de esa lista.

**Cuántos se muestran:** los 12 primeros del índice en el plano, y la lista
completa en el panel (en Bogotá son cientos). Tope a decidir (P10).

---

## 3. El plano de posicionamiento

```
 afinidad territorial  ▲
 (cuánto rinde en su   │          ○ ─ ─ ─ ●(rival no elegido, ci, 1,86)
  base, log)       2,0 ┤              ●●
                       │        ○   ●●●●  ○
    mismo terreno  1,15┤╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌  (franja gris)
                   0,85┤╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
                   0,5 ┤     ○        ○      ●        ○
                       └──────┬──────┬══════┬──────┬──────┬──────►
                            Izq.   C-izq.  Centro  C-der.  Der.
                                   ▐USTED▌                         familia
                       ┌──────────────────────────────────────┐
                       │ No sabemos · aval amplio o sin línea │  ○ ○ ○
                       └──────────────────────────────────────┘
   ● ocupa el cargo · ○ compitió / tiene base · tamaño = votos en el territorio
```

### 3.1 Eje X · familia política

- Rival: `PartidosBloques.bloqueDeCandidatura(partido, nombre)` sobre su
  candidatura **más reciente**. Los cinco valores del espectro son columnas
  discretas; dentro de una columna los puntos se reparten con un desplazamiento
  **fijo** (hash del nombre), para que no bailen en cada carga.
- **«No sabemos»** es una franja aparte, debajo del eje, no una columna del
  espectro: `sc` y los avales amplios (`esAvalAmplio`: ASI, MAIS, AICO,
  independientes). Ponerlos en el centro sería afirmar algo que no sabemos (H9).
- Usted: la familia del **aval de la campaña** (`campana.partido`), o el
  espectro si va por firmas o sin decidir (`campana.espectro`). No se dibuja
  como un punto sino como una **columna resaltada**: el eje Y se mide contra su
  base, así que usted no tiene «afinidad consigo mismo».
- Se declara: la familia es la del **partido**, no la de la persona. Un
  candidato que cambia de aval se mueve de columna cuando la revisión lo
  detecta.

### 3.2 Eje Y · afinidad territorial

```
                Σ_p  s_U(p) · ( v_R(p) / válidos(p) )
afinidad(R) = ─────────────────────────────────────────
                       V_R / VÁLIDOS del territorio
```

- `s_U(p)` = parte de **su base** que cae en el puesto p (recortada al
  territorio de campaña). `v_R(p)` = votos del rival en p.
- Se lee así: **cuánto más (o menos) saca el rival en los puestos donde usted
  saca votos, que en el promedio del territorio.** 1 = igual que en todas
  partes; 2 = el doble; 0,5 = la mitad. No depende del tamaño del rival (eso es
  la burbuja) ni del suyo.
- Escala logarítmica fija de 0,25 a 4 (el eje no se estira para inventar
  diferencias), con la franja **0,85–1,15 «mismo terreno»**.
- **Qué es «su base»**, en orden:
  1. Su votación anterior en la misma corporación y territorio.
  2. Su votación anterior de otra corporación, recortada al territorio (el
     salto: la base de la JAL dentro del Concejo).
  3. Sin votos en el territorio (candidatura nueva, o viene de otro municipio):
     **los votos de su familia política en 2023**, la misma cuenta del Día D
     (`C360DiaD.fuente`), y el eje se rotula «afinidad con su familia». Nunca en
     silencio.
- Medido (H1, H2): JAL 0,76–1,11; Concejo 0–10,6. En la JAL la tarjeta dice
  *«En una localidad todos compiten por los mismos puestos: lo que los separa
  es la lista y la familia política»* y el plano se lee por columnas.

**Descartadas, medidas:**
- *Similitud de distribuciones* `Σ min(s_U, s_R)`: en el salto JAL→Concejo da
  0,01–0,05 para todos (la base cubre 31 de 943 puestos), no separa.
- *Correlación de la fuerza relativa entre puestos*: en la JAL es la que más
  separa (−0,34 a 0,47) pero con 32 puestos es ruidosa y difícil de explicar.
  Queda en la ficha como dato secundario, no como eje.

### 3.3 La burbuja

Votos del rival **dentro del territorio de campaña** en su elección más
reciente, recortados. Un senador con 100.000 votos nacionales y 3.000 en su
municipio es una burbuja de 3.000.

### 3.4 Revisión mensual en la tarjeta

Encabezado: **«Revisado el 1 de octubre de 2026 · próxima revisión: 1 de
noviembre»** y, si hubo cambios, una línea: *«Desde la revisión anterior: entra
1 (prensa, 2 medios) · 1 cambió de aval · 3 con titulares nuevos»*. Detalle en
§8.

---

## 4. El mapa de disputa latente

### 4.1 La métrica

Por puesto p, dos índices relativos (el mismo «le pega» de la página del
electorado, sin perfil):

```
i_U(p) = (v_U(p) / válidos(p)) ÷ (V_U / VÁLIDOS)          su fuerza relativa ahí
i_R(p) = (Σ_cercanos v_R(p) / válidos(p)) ÷ (Σ V_R / VÁLIDOS)   la de sus rivales cercanos
```

«Rivales cercanos» = los de su columna y las vecinas (cercanía ≥ 0,6 en §6),
o uno solo si el usuario lo elige en el plano. Cuatro categorías:

| | rivales ≥ 1 | rivales < 1 |
|---|---|---|
| **usted ≥ 1** | **Disputa** — los dos rinden por encima de su promedio | **Fortaleza** — usted rinde, sus rivales cercanos no |
| **usted < 1** | **Terreno de sus rivales** | **Terreno ajeno** — ni usted ni ellos |

más **«sin votos suyos»** (gris) y **«muy pocos votos para leer»** (puestos con
< 200 válidos o < 5 votos suyos: se agregan al barrio o comuna antes de
clasificar).

### 4.2 Medido

| Caso | Fortaleza | Disputa | Terreno de rivales | Terreno ajeno | Sin votos suyos |
|---|---|---|---|---|---|
| JAL Barrios Unidos (32 puestos) | 10 | 1 | 12 | 8 | 1 |
| Concejo de Bogotá, su base (943 puestos) | 7 | 24 | 0 | 0 | **912** |

El segundo renglón es la razón de la **segunda capa**: cuando la base es más
chica que el territorio, el mapa de «su base contra sus rivales» es un punto en
la ciudad. Por eso hay dos capas:

1. **Su base** — las cuatro categorías sobre los puestos donde tiene votos.
2. **El territorio de la campaña** — solo `i_R`: dónde rinden sus rivales
   cercanos en toda la ciudad (o el departamento). Es el mapa de *adónde tendría
   que ir a disputar*. En la JAL las dos capas coinciden y la segunda no se
   ofrece.

### 4.3 Cómo se pinta sin sugerir quién votó por quién

- **Colores categóricos**, no una rampa de «votos del rival»: una rampa invita a
  leer «aquí están los votantes de X».
- Unidad = puesto, agregado a barrio / comuna / localidad / municipio con las
  **mismas capas** del CRM y de la página del electorado (`CIUDADES`,
  `BARRIOS_DIC`, `fuenteBarrial`); Bogotá rotada, Cartagena con sus tres
  escalas. Donde no hay cartografía: puestos como círculos.
- Relleno de vecino para barrios sin puesto, punteado y fuera de los conteos
  (la regla de siempre).
- Tooltip en lenguaje de puesto: *«En este puesto usted sacó 1,3 veces su
  promedio y las listas de su familia 1,2 veces el suyo. No dice quién votó por
  quién: dice dónde rinden las dos cosas a la vez.»*
- Lo omitido se declara: puestos de 2023 que no existen en 2026 y el ~1 % que
  la matriz pierde.

---

## 5. El rival dentro de su propia lista

Solo en corporaciones con **voto preferente y lista abierta** (concejo,
asamblea, JAL). En lista cerrada la tarjeta dice *«Su lista es cerrada: el
orden lo pone el partido, así que no compite en votos con sus compañeros»*.

Una **escalera**, aparte del plano:

```
Nuevo Liberalismo · JAL Barrios Unidos · 2023 · ganó 2 curules
  1  ██████████████████  1.634  ● elegido
  2  █████████████████▊  1.619  ● elegido   ← último elegido
  3  ███████▊              709  USTED       a 910 votos del último elegido
  4  █████▊                532
  …
```

- «Su lista» = la del partido del catálogo que eligió en la ruta (H7), en la
  corporación y territorio de la campaña. Si su partido no compitió ahí en 2023,
  no hay escalera y lo dice.
- La distancia se mide contra **el último elegido de su lista**, que es la
  misma referencia de la meta por partido (`referenciaPorPartido`, tipo
  `lista-con-curul`). Medido en el Concejo: último elegido de NL 2023 = **9.280**
  (índice oficial; la matriz por comuna daba 9.153 porque pierde ~1 % de los votos);
  la meta probable con NL es **9.880** (9.280 traído a 2027). Las dos pantallas
  hablan del mismo número.
- Si viene de otra corporación, la escalera es la de la lista a la que llega y
  «usted» no aparece en ella: se muestra dónde quedaría **su meta** en esa
  escalera.

---

## 6. El índice de presión competitiva

Nombre propuesto: **presión competitiva**, no «amenaza» (§9). Heurística
declarada, con el criterio a la vista en la ⓘ:

```
presión = cercanía(Δ familia) × afinidad acotada × tamaño

cercanía  = 1 misma familia · 0,6 a un paso · 0,25 a dos · 0,1 a tres · 0,05 a cuatro · 0,4 «no sabemos»
afinidad  = min(2, afinidad territorial) ÷ 2
tamaño    = votos del rival en el territorio ÷ (esos votos + su meta, escalón probable)
```

- El tamaño era `min(1, votos/meta)` en la medición y **se saturaba**: en el
  Concejo todos los concejales pasan la meta de una edilesa, así que el índice
  quedaba en cercanía × afinidad. La forma `v/(v+meta)` vale 0,5 cuando son
  iguales y no se satura.
- «No sabemos» vale 0,4, ni cerca ni lejos: un aval amplio puede traer a
  alguien de su propia familia.
- **Se publica en tres niveles (alta · media · baja) por terciles dentro de su
  territorio**, no como número: el número invita a comparar lo incomparable
  entre territorios.
- Medido: en la JAL los dos primeros son sus compañeros de lista (H3); en el
  Concejo, los 12 primeros de centro-izquierda y el primero un no elegido (H4).
- Congresistas 2026 y titulares de alcaldía o gobernación no entran al índice
  (§2).

---

## 7. La ficha por contendiente

| Bloque | Fuente | Estado |
|---|---|---|
| **Historial electoral** — cada candidatura con año, corporación, partido y votos | registro + agrupación por persona | dato público, **en vitrina** |
| **Dónde saca sus votos** — sus 5 unidades fuertes dentro del territorio | su JSON o la matriz, recortado | dato |
| **La meta de su lista** — lo que costó en 2023 entrar por su lista, traído a 2027 | `VoteTarget.estimate({corp, territory, partido: el suyo})` | cálculo nuestro, rotulado como **la meta de su lista**, no «la meta que él se puso» |
| **Frente a usted** — afinidad, familia, presión, la escalera si comparten lista | motor | heurística declarada |
| **En prensa** — titulares que lo nombran con nombre completo, por mes (6 meses), y los últimos 5 con enlace | acción `medios` + `menciona_persona` | literal; sin resumen de modelo |
| **Temas con los que aparece** | `C360Saliencia.analizar` sobre sus titulares | ver la regla de abajo |

**Aliados probables del rival — fuera de la v1.** Exigiría correr la regresión
del endoso de cada rival contra todos los candidatos de su territorio: es caro,
y sobre todo es **inferir alianzas de un tercero** y publicarlas. La ficha dice,
en cambio, algo verificable: *con qué lista compitió y quiénes iban en ella*.

**Temas sensibles:** un rival que sale en titulares del tema «Corrupción y
control» no lleva esa etiqueta pegada a su nombre (una etiqueta insinúa;
un titular informa). Se muestran los **titulares literales** con su medio y su
fecha, y el conteo por tema solo para los otros diez temas. Decisión P8.

---

## 8. La revisión mensual

### Qué se revisa

| Cambio | Cómo se detecta | Quién decide |
|---|---|---|
| Nuevos contendientes nombrados en prensa (fuente D) | Consultas de aspiración por territorio + nombres propios (`candidatosActor` de la saliencia) cruzados con el registro (`personaKey`) | **una persona**: nada de prensa entra sin revisión |
| Cambio de aval, adhesión o renuncia a un partido | Titulares con el nombre completo + vocabulario de aval | una persona |
| Titulares nuevos de los contendientes conocidos | Consulta por nombre, `menciona_persona` | automático |
| Datos nuevos del registro (p. ej. D1, la inscripción D3) | Versión del índice | automático |
| Correcciones (D4: renunció, lo reemplazaron, ya no compite) | La persona que revisa, o el usuario con «Avisar un cambio» | una persona |

H5 dice que hoy la prensa casi no trae aspirantes: en 2026 la revisión va a ser
casi toda «sin cambios», y eso se dice tal cual (*«Revisado el 1 de noviembre:
sin cambios»*). En 2027 sube de volumen, y en la fase 7 la inscripción oficial
la reemplaza.

### Quién la corre

**Un cron propone y una persona aprueba**, como el panel de correcciones del
mapa del sismo:

1. GitHub Actions, el día 1 de cada mes (`candidato-360-contendientes.yml`):
   `tools/candidato-360/contendientes/revisar.py` pide al worker los
   **territorios** con vínculos activos (no las personas), consulta la prensa y
   escribe **propuestas** en el worker.
2. Una pestaña del panel de administración (misma sesión admin de hoy) muestra
   las propuestas con sus titulares y botones *aprobar / descartar*. Lo del
   registro y los titulares nuevos de rivales ya conocidos se aprueban solos.
3. Al cerrar la revisión se sella la versión.

### Cómo se versiona

- El snapshot es **por territorio y corporación**, no por cuenta: todas las
  candidaturas al Concejo de Bogotá ven la misma lista de rivales. KV del
  worker: `c360:contendientes:<corp>:<territorio>:<AAAA-MM>` =
  `{revisado, revisor, lista:[{personaKey, fuentes, aval, marcas}], cambios:[…]}`
  y un puntero `…:ultima`.
- **Qué se movió** = la diferencia entre la versión del mes y la anterior,
  calculada al sellar y guardada en `cambios`, así la tarjeta no recalcula
  nada.
- Lo que es **de cada cuenta** —su base, el plano, la presión, los que agregó
  a mano— se calcula en el navegador y no se versiona en el servidor.
- Rutas nuevas: `GET /c360/contendientes` (sesión + acceso; devuelve el
  snapshot del territorio de su vínculo) y tres de servicio en la tabla
  `SERVICIO` con el guarda de siempre: `/c360/contendientes/{inventario,
  propuesta, sellar}`.

---

## 9. Cuidados legales y de tono

1. **El voto es secreto.** El mapa describe puestos y territorios; ninguna frase
   dice ni sugiere que los votantes de un rival sean de alguien.
2. **Los rivales son personas.** Solo datos electorales públicos (el registro) y
   prensa publicada, con enlace. Sin dirección, teléfono, familia, patrimonio,
   procesos judiciales ni redes personales.
3. **Nada se insinúa.** Sin resúmenes de modelo sobre un rival, sin
   «sentimiento», sin etiquetas de tema sensibles (§7). Lo que se muestra de
   prensa es el titular literal.
4. **Vocabulario.** «Contendiente», «rival», «presión competitiva», «disputa».
   Nunca «amenaza», «enemigo», «atacar».
5. **Lo estimado se rotula.** «Rivales probables» hasta la inscripción; «ganó la
   curul en 2023», no «ocupa la curul»; «la meta de su lista», no «su meta».
6. **Quien agrega a alguien a mano** agrega un dato de un tercero. Si esa
   persona no está en el registro (no ha sido candidata), el nombre vive **solo
   en el navegador**, la misma regla que los líderes del endoso. Decisión P2.

### Redes de terceros por Apify

- **Costo:** bajo. Con los precios de referencia de `escucha/costos.mjs`
  (sin medir todavía con `medir.mjs`), leer el perfil público de 5 rivales en 4
  redes a ~60 publicaciones al mes son ~1.200 ítems: **del orden de US$ 0,3 a
  1,2 por cuenta y mes**, sin comentarios.
- **Recomendación: no en la v1.** El costo no es el problema: raspar perfiles
  de terceros choca con los términos de uso de las plataformas, y la regla 3
  (nada de sentimiento sobre un rival) le quita a esa lectura casi todo su
  valor. Si algún día entra, solo cuentas **oficiales de campaña** verificadas,
  solo volumen y frecuencia de publicación, sin comentarios. Decisión P6.

---

## 10. Escenarios de fragmentación (evaluación)

«¿Qué pasa con la meta si entra o sale un rival de su bloque?» **es un
pronóstico**: supone a dónde se irían sus votos. Choca con «no es un
predictor» y no entra en la v1.

Lo que sí cabe, como fase opcional, es un **contrafactual sobre 2023**, que es
aritmética sobre el pasado: *«si en 2023 las listas de Verde y de NL hubieran
ido juntas, la cifra repartidora habría sido X y el último elegido de esa lista
Y»*. Se rehace el reparto con `reconstructedCutoff` sumando o quitando listas,
**sin redistribuir votos**, y el texto lo dice. Decisión P5.

---

## 11. Qué se reusa (y qué no se duplica)

| Pieza | De dónde | Para qué |
|---|---|---|
| Recorte al territorio, alcance de la campaña, comuna por puesto | `C360Endoso.alcanceDe / enAlcance / areaDe / comunaDesde` | la base propia y los votos de cada rival en el territorio |
| Totales por puesto | `totales-puesto/` | los válidos de la afinidad y del mapa, fuera de las 11 ciudades |
| Base de la familia política | `C360DiaD.fuente` | la base de una candidatura nueva |
| Reparto, cifra repartidora, último elegido de la lista | `vote-target.js` (+ helper `electos`, D2) | fuente A, escalera, meta de la lista del rival |
| Familia y aval amplio | `partidos-bloques.js` | eje X |
| Persona única | `CandRegistry.personaKey`, `agruparPersonas` | unir fuentes |
| Búsqueda | `CandRegistry.acRank` | agregar a mano |
| Prensa | `C360Panel.caudal({action:'medios'})`, `menciona_persona` y `agrupar_por_cobertura` del briefing | ficha y revisión |
| Temas | `C360Saliencia.analizar` | ficha |
| Capas del mapa | `C360Electorado.CIUDADES`, `BARRIOS_DIC`, `fuenteBarrial`, `rotar90`, relleno de vecino | mapa de disputa |
| Vitrina | `VITRINA_MUESTRA`, `.vitrina-blur`, `candadoDetalle` | lo que ve quien no paga |
| Chasis del panel | `candidato-360-panel.js` | sesión, vínculo, muro |
| Candi | `VISTAS` + `C360_CANDI_VISTAS` del worker | la vista `contendientes` (las dos, o Candi describe mal la pantalla sin error) |

**No se duplica:** la matriz de puesto no se arma en el navegador si el archivo
existe; el recorte no se reescribe; la escucha de prensa no tiene un segundo
cliente.

---

## 12. Maquetas

### Tarjeta 10 en el CRM

```
┌─────────────────────────────────────────────────────────────┐
│ 10 · Sus contendientes                  Revisado el 1-oct   │
│ ¿Contra quién compite y dónde se pelea el voto?             │
│                                                             │
│  [mini plano: 5 columnas + franja «no sabemos»,             │
│   sus 3 rivales de más presión rotulados]                   │
│                                                             │
│  Presión alta: 3 · media: 5 · baja: 4 · no sabemos: 2        │
│  Desde la revisión anterior: sin cambios.                   │
│                                                             │
│  [ Ver sus contendientes → ]      12 rivales probables      │
│                                   antes de la inscripción   │
└─────────────────────────────────────────────────────────────┘
```

### Panel `candidato-360-contendientes.html`

```
Encabezado: su candidatura · revisado el … · «rivales probables hasta la
            inscripción de 2027»

01 · El plano               plano grande; clic en un punto → su ficha;
                            filtro «solo quienes ocupan el cargo»
02 · Dentro de su lista     escalera (o el aviso de lista cerrada)
03 · Dónde se pelea         mapa con las dos capas; conteo de puestos por
                            categoría; top 10 puestos de disputa
04 · La lista completa      tabla ordenable: nombre, fuente, familia,
                            afinidad, votos en el territorio, presión, prensa
05 · Qué se movió           la bitácora de revisiones, mes por mes
06 · Agregar a alguien      buscador del registro + nombre libre (§9.6)
Pie: fuentes y cobertura de cada número; el método en una ⓘ por sección
```

Ficha (panel lateral o modal): historial · dónde saca sus votos · la meta de su
lista · frente a usted · en prensa.

### Vitrina (sin acceso)

- Plano: **los 3 de más presión nítidos**, el resto como burbujas borrosas con
  el conteo a la vista («y 9 más»).
- Ficha: el historial electoral completo (es el índice público, la vitrina de
  siempre); lo demás con candado.
- Mapa: conteo por categoría visible; las unidades borrosas salvo las 3 de más
  disputa.
- Escalera, lista completa, prensa, revisión y agregar: tras el muro.

---

## 13. Fases

| # | Qué | Sale |
|---|---|---|
| 1 | **Motor** `candidato-360-contendientes.js` sin DOM: fuentes A-C desde el registro, unión por persona, eje X, eje Y con las tres bases, burbuja, presión, escalera. Helper `electos` en `vote-target.js` sin cambiar cifras. Solo con las matrices que ya existen (11 ciudades + asamblea) y el JSON de cada rival donde no. `prueba-contendientes.mjs` con las cifras de §0 fijadas. | **hecho 28-sep-2026** |
| 2 | **Panel** con el plano, la escalera, la lista y la ficha (sin prensa). Tarjeta 10 como enlace. Vitrina. Candi (frontend + worker). | **hecho 28-sep-2026** (sin desplegar) |
| 3 | **Mapa de disputa** con las dos capas, sobre las capas del CRM. | sección 03 |
| 4 | **D1** `build_matriz_puesto.py`: concejo y JAL fuera de las 11 ciudades, alcaldía, gobernación; después 2019. | todo el país sin bajar cientos de JSON |
| 5 | **Prensa y revisión mensual**: ficha con titulares, worker (KV + 4 rutas), cron, pestaña de administración, «qué se movió». Agregar a mano. | revisión del 1 de cada mes |
| 6 | **Briefing**: sección «Sus contendientes» en el correo existente. | alertas |
| 7 | **Inscripción oficial 2027** (D3): los inscritos reemplazan a los probables; la tarjeta cambia de título. | cuando la RNEC publique |
| 8 | *(opcional, P5 y P6)* contrafactual de 2023; cuentas oficiales de campaña. | solo si se decide |

**Alertas en el briefing (fase 6), recomendación: dentro del correo existente**,
como una sección más después de «La conversación». Un segundo correo cada tres
días le quita fuerza al primero y el briefing ya tiene su regla de oro («sin
nada que decir no se manda»). La sección aparece solo si hay algo: un rival
nombrado con nombre completo en un titular nuevo, o un cambio de aval aprobado
en la revisión. Máximo 3 líneas, con enlace al panel. Para eso el inventario
del worker necesita saber qué rivales mira esa cuenta: el snapshot del
territorio basta, salvo los agregados a mano (P2).

---

## 14. Pruebas

### Node (el motor)

`tools/candidato-360/prueba-contendientes.mjs`, como `prueba-endoso.mjs`:

1. **Sin red** (`--sin-red`), casos sintéticos, una regla por caso: afinidad = 1
   con distribuciones iguales; afinidad acotada en el eje; base propia → base
   recortada → base de la familia; cercanía por pasos y «no sabemos»; aval
   amplio a la franja; unión por `personaKey` con y sin alias; homónimo en otro
   departamento no se funde; titular de alcaldía fuera del índice; congresista
   marcado; lista cerrada sin escalera; partido que cambia de nombre entre
   corporaciones (H7); puestos chicos agregados antes de clasificar; las cuatro
   categorías del mapa.
2. **Con red**, contra S3, con las cifras de §0 fijadas: rangos de afinidad
   (0,76–1,11 · 0–10,6), conteos 118/140/176, 10/1/12/8/1 y 7/24/0/0/912, el
   reparto de H8, el 3.º puesto y los 910 votos de H3, 72 de 434 sin bloque.
   Si cambian, cambió el motor o cambiaron los datos, y hay que saber cuál.

### Playwright (el panel y la tarjeta, todo lo remoto simulado con `page.route`)

`prueba-contendientes-panel.mjs`:

- Con acceso: el plano pinta las 5 columnas y la franja; la columna de usted
  resaltada; clic en un punto abre su ficha con historial, meta de su lista y
  fuentes.
- JAL: aparece el aviso de «todos compiten por los mismos puestos» y la
  escalera con «a N votos del último elegido».
- Salto (base fuera del territorio): el mapa ofrece las dos capas.
- Candidatura nueva: el eje dice «afinidad con su familia».
- Lista cerrada: el aviso, sin escalera.
- Revisión: con un snapshot simulado de dos meses, «qué se movió» lista las
  diferencias; sin cambios dice «sin cambios».
- **Vitrina:** solo 3 nítidos; ni el texto de la lista completa ni los titulares
  llegan al DOM.
- Sin la palabra «amenaza» en ninguna parte del DOM.
- 375 px sin desborde; tarjeta y panel dan el mismo conteo por nivel de presión.

`prueba-vitrina.mjs` suma la tarjeta 10 a lo que se revisa; `prueba-candi.mjs`
detecta si falta la vista en el frontend o en el worker.

---

## 15. Preguntas que tiene que decidir Ricardo antes de construir

| # | Pregunta | Recomendación |
|---|---|---|
| P1 | ¿El índice se llama «presión competitiva» y se muestra solo en tres niveles? ¿O no se muestra y el plano basta? | Tres niveles con ese nombre; el número queda en la ⓘ. |
| P2 | Un contendiente agregado a mano que **no** está en el registro: ¿vive solo en el navegador (como los líderes del endoso) o en el worker (así el briefing lo vigila)? | Navegador. Los que sí están en el registro pueden ir al worker como `personaKey`, que es dato público. |
| P3 | La revisión mensual: ¿cron que propone + persona que aprueba, o solo cron? ¿Quién revisa? | Cron + persona para todo lo que salga de prensa. |
| P4 | Alertas: ¿dentro del correo del briefing o aparte? | Dentro (§13). |
| P5 | Fragmentación: ¿nada, o el contrafactual sobre 2023? | Nada en la v1; el contrafactual como fase 8 si un cliente lo pide. |
| P6 | Redes de terceros: ¿no, o solo cuentas oficiales de campaña, solo volumen? | No en la v1. |
| P7 | Umbral de la fuente B: ¿50 % del último elegido de su lista? | Empezar ahí y medir cuántos quedan por territorio en la fase 1. |
| P8 | Temas sensibles de un rival (corrupción y control): ¿titulares literales sin etiqueta, o fuera del todo? | Titulares literales sin etiqueta. |
| P9 | ¿Se afloja `listaDelPartido` para casar «NL - Agrupación Política en Marcha» con «NL en Marcha»? Cambiaría la meta de algunas candidaturas. | Sí, con prueba: exigir el núcleo sin las palabras de coalición («agrupación», «en marcha») y medir cuántas metas cambian antes de subirlo. **Decidido y aplicado (28-sep-2026):** solo «agrupación»; ver la bitácora. |
| P10 | ¿Cuántos rivales en el plano? | 12, y la lista completa en el panel. |
| P11 | ¿En qué plan entra? (el endoso quedó en «Completo») | Plano y ficha en el plan base; mapa de disputa, revisión y alertas en «Completo». |
| P12 | Vitrina: ¿los 3 de más presión nítidos, con nombre? | Sí: su historial ya es público en el índice, y sin nombres la vitrina no vende. |

---

## Bitácora

**Decisiones (28-sep-2026).** Ricardo aceptó las doce recomendaciones de §15.

**Fase 1 (28-sep-2026) · en código, verificación real pendiente.**

- `candidato-360-contendientes.js` (`window.C360Contendientes`), sin DOM. Dos capas:
  `cargar` (IO: reparto, matriz o archivos, fuente C, base) y `evaluar` (cálculo puro:
  familia, afinidad, correlación, franjas, presión, niveles, escalera, mapa de disputa,
  marcas de titular y de congresista, avisos). Depende de `PartidosBloques`,
  `CandRegistry` (persona), `VoteTarget` (reparto y `listaDelPartido`), `C360Endoso`
  (`enAlcance`) y `C360DiaD.puestosDestino`.
- `vote-target.js`: `reconstructedCutoff` devuelve también `electos` y se exporta
  `VoteTarget.reparto(...)` —el mismo camino de `estimate` sin la meta— y
  `listaDelPartido`. `estimate` no se tocó: comparado en Node contra la versión de
  `HEAD` con un concejo sintético y seis partidos, da lo mismo salvo el caso de P9.
- `candidato-360-diad.js` exporta `puestosDestino` (los mismos archivos de 2023 por
  comuna o municipio). Se subieron los `?v=` de los dos archivos.
- **P9 aplicado.** Medido sobre los catálogos de partidos × todas las
  circunscripciones de concejo (161.386 pares) y JAL (78.448) de 2023: sumar
  «AGRUPACION» a las palabras estructurales hace que 14 circunscripciones encuentren
  lista donde no había (11 concejos, 3 JAL), todas de «AGRUPACIÓN POLÍTICA EN
  MARCHA» en coaliciones donde corrió, y **ninguna cambia de lista**. Sumar también
  «EN» se descartó: 756 pares de concejo y 256 de JAL cambiaban, casi todos «Gente
  en Movimiento» cayendo en el Partido de la U. H7 se corrige: el nombre de la JAL
  («NUEVO LIBERALISMO- AGRUPACION…») lo marca el catálogo como coalición y no se
  ofrece; quien elige «PARTIDO NUEVO LIBERALISMO» o «NUEVO LIBERALISMO EN MARCHA» ya
  encontraba su lista.
- Dos decisiones de construcción que no estaban escritas en el plan:
  · **El mapa cuenta el voto de lista.** «Rivales cercanos» son todas las candidaturas
    de su familia y las vecinas **más el voto solo por la lista** de sus partidos: sin
    él, el Pacto (lista cerrada) no existía en el mapa. Por eso los conteos del motor
    difieren de los de §0, que se midieron sin voto de lista; la prueba reproduce §0
    llamando a `disputa` sin listas ni umbral, y aparte imprime los del motor.
  · **Fuente C, alcance de la fase 1:** solo candidaturas cuya circunscripción cabe
    entera en el territorio (concejo y JAL de años anteriores, alcaldía, las JAL de la
    ciudad para un concejo, la Cámara en Bogotá y en lo departamental). Lo que es más
    grande que el territorio (Senado, la Cámara de un departamento para un concejo
    municipal, el concejo para una JAL) exige recortar su archivo y queda para después.
    Se bajan hasta 40 archivos, los de más votos entre los que pasan el umbral.
- `tools/candidato-360/prueba-contendientes.mjs`: **30 casos sintéticos, todos pasan**
  (`--sin-red`). La parte real (JAL de Barrios Unidos y Concejo de Bogotá, con las
  cifras de §0 fijadas: rangos de afinidad, 65 de 67, 119/140/175, 72 sin bloque con
  171.499 votos, el reparto de H8, la escalera 3.ª a 910 votos, el último elegido de NL
  en 9.280, el congresista marcado, los 12 del plano de centro-izquierda y los dos
  conteos del mapa) **está escrita pero no ha corrido**: la red desde la que se
  construyó pasa por un firewall Fortinet que sustituye el certificado de S3, y ni
  `curl` ni Node lo aceptan. No se desactivó la verificación TLS. Correrla desde otra
  red: `node tools/candidato-360/prueba-contendientes.mjs`.
- `prueba-endoso.mjs --sin-red` sigue pasando. `prueba-meta.mjs` (Playwright) no se
  pudo correr: Playwright no está instalado en la Mac M5.

**Fase 1 · verificación real (28-sep-2026, desde otra red).** La prueba completa
corrió contra S3 en 2 min 20 s: **30 sintéticos + 21 reales, todo en orden**, con
dos correcciones que eran errores del PLAN, no del motor:

- **H2 era 119/140/175 y es 118/140/176.** El script de la medición clasificaba la
  afinidad redondeada a dos decimales: una candidata con 1,147 caía en «alta» y un
  concejal con 0,845 en «mismo terreno». El motor usa el valor sin redondear.
- **El último elegido de NL es 9.280, no 9.153.** La medición lo tomó de la matriz por
  comuna, que pierde ~1 % de los votos (puestos de 2023 que no están en el georef de
  2026). El motor lo toma del índice, que es el total oficial y el mismo de la meta.
  Ojo con las otras cifras de §0 que nombran votos de un candidato (p. ej. los 9.588
  de H4): también salen de la matriz y pueden estar ~1 % por debajo del oficial.

Lo que imprime el motor con sus reglas completas (umbral de puestos chicos y voto de
lista en el mapa), para tener la referencia:

| | JAL Barrios Unidos | Concejo de Bogotá |
|---|---|---|
| Meta probable (con su partido) | 1.730 | 9.880 |
| Rivales probables (en el índice) | 32 (32) | 92 (87; 40 por fuente C, 5 fuera del índice) |
| Niveles alta · media · baja | 11 · 11 · 10 | 29 · 29 · 29 |
| Mapa: fortaleza · disputa · terreno de rivales · ajeno · sin base · poco | 6 · 4 · 7 · 7 · 0 · 8 | 15 · 9 · 0 · 0 · 879 · 40 |

En la JAL, 8 de 32 puestos quedan en «muy pocos votos para leer» (menos de 200
válidos o menos de 5 votos suyos): con 709 votos repartidos en 31 puestos, la
cuarta parte de su base está en puestos donde la categoría sería ruido. Al pintar
(fase 3) conviene agregar esos puestos a su barrio antes de clasificar, como dice §4.1.

**Fase 2 (28-sep-2026) · panel, tarjeta 10, vitrina y Candi.**

- **`candidato-360-contendientes.html`** (panel 10): 01 el plano (con resumen por
  niveles, avisos y leyenda), la ficha al tocar un punto o una fila (frente a usted,
  historial, dónde saca sus votos, la meta de su lista con `VoteTarget.estimate`),
  02 la escalera dentro de su lista, 03 la tabla ordenable y la nota de método.
  Usa el chasis `C360Panel` (muro sin acceso o sin vínculo).
- **Tarjeta 10 en el CRM** (`pintarContendientes`, sección «9 ter» de
  `candidato-360.js`): mini plano con los tres de más presión, conteo y niveles.
  Se llama DESPUÉS de la meta (la presión usa el escalón probable). En vitrina,
  los demás puntos van borrosos y **sin nombre ni título en el DOM**, y el botón
  lo intercepta el paywall como a los demás módulos.
- **El motor ganó lo que las dos pantallas comparten**, para que den lo mismo:
  `leer` (orquesta todo con las mismas entradas), `registroC` (baja solo los índices
  de la fuente C que pueden caber en el territorio y deja sus filas), `planoSVG`
  (el dibujo, como texto SVG sin DOM), `completarCampana` y los textos (`sello`,
  `AVISO_TXT`, `MARCA_TXT`…). `candidato-360.css` trae el estilo del plano, con
  rótulos cortos de columna en pantallas angostas.
- **Candi**: vista `contendientes` en el frontend y en `C360_CANDI_VISTAS` del
  worker (y la del CRM menciona el módulo 10). **Worker sin desplegar**, como el
  endoso: `src/index.js` de `rr-auth` tiene además cambios de otras sesiones.

Tres cosas que salieron al construir y que cambian cifras o reglas:

1. **«La misma corporación» guarda la campaña SIN territorio.** El CRM deja
   departamento, municipio y localidad vacíos; sin arreglo, el motor no encontraba la
   matriz y caía al modo lento. `completarCampana` lo completa desde el alcance y el
   nombre de sus mesas. La prueba real de la JAL corre ahora así.
2. **Votos a alcaldía o gobernación no entran al índice de una corporación de lista.**
   Por la fuente C entraba el alcalde de Bogotá 2.º al plano del Concejo con 1,5
   millones de votos. Ahora quien viene de alcaldía o gobernación queda en la lista con
   la marca «sus votos son de alcaldía o gobernación», fuera del índice, y el ganador
   de 2023 lleva además «hoy ocupa ese cargo». En el Concejo de Bogotá son 7. Con eso el
   plano cambia: entra al puesto 10 un concejal liberal (un paso, afinidad ×1,71), y
   H4 queda como «los 9 primeros son de centro-izquierda y los 12 están a un paso o
   menos».
3. **La fuente C ya no baja el archivo de quien ya es rival por 2023**: su historial
   entra con los votos del índice. Tope de 20 personas nuevas. La prueba real bajó de
   2 min 20 s a 51 s. Y si una parte de la matriz no llega, el aviso
   «matriz incompleta» lo dice; si no llega nada, `leer` falla en vez de pintar cero
   rivales.

Pruebas: `prueba-contendientes.mjs` (57 sin red + 23 reales) y la nueva
`prueba-contendientes-panel.mjs` (Playwright, 24 casos): rivales por fuente, la
persona única sin bajar su archivo viejo, escalera, plano, tabla ordenable, ficha con
la meta de su lista, «amenaza» ausente, 375 px sin desborde, muro sin acceso, y la
tarjeta del CRM en vitrina con **el mismo conteo y los mismos niveles que el panel**.
Pasan también `prueba-candi`, `prueba-meta` (31/31), `prueba-listas` (15/15) y
`prueba-endoso --sin-red`. **`prueba-vitrina` y `prueba-paneles` fallan, pero ya
fallaban en el commit anterior** (verificado en un worktree): la primera espera un
«Abrir CRM» habilitado sin aval marcado, la segunda un bloque de la escucha. Son
pruebas viejas, fuera de este módulo.

Playwright se instaló de forma global en la Mac M5 (`npm i -g playwright`); las
suites lo encuentran con `PLAYWRIGHT_PATH=/opt/homebrew/lib/node_modules/playwright/index.mjs`.
