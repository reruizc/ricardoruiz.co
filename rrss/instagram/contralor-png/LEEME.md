# Contralor General 2026-2030 · pieza IG "mercado de predicción"

`contralor-mercado.png` (**2160×2160**) · genera `tools/contralor-2026/build_img.py`
Se dibuja en coordenadas de 1080 y se renderiza a `ESCALA=2`: a 1080 (el mínimo de
Instagram) se veía suave. Todo pasa por `u()` y `F()`, así que subir `ESCALA` no
descuadra el layout. Las cifras las lee del estado del motor, nunca a mano.
Corte de datos: **10 de agosto de 2026, 8:00 a. m.** (v2 · el corte anterior fue el 6-ago).

## Lo primero: la fecha es el 12, no el 13

El Congreso en pleno fue convocado para el **miércoles 12 de agosto de 2026**
(Congreso definió la fecha el 30-jul; presidente del Congreso Honorio Henríquez).
Voto secreto, mayoría absoluta del pleno (286 congresistas → ~144 votos).
⚠️ Cambio e Infobae hablan de **165 votos**; El Colombiano de ~142. La cifra
que se sostiene por la regla constitucional es la mayoría absoluta del pleno.
No usar 165 sin verificar contra el reglamento aplicado en la sesión.

## Los 10 elegibles y su puntaje del concurso de méritos

| # | Candidato | Puntaje |
|---|---|---|
| 1 | Luis Enrique Abadía García | 86,74 |
| 2 | Andrés Castro Franco | 84,61 |
| 3 | Jorge Eliécer Laverde Vargas | 82,89 |
| 4 | Ana Elena Monsalvo Herrera | 81,96 |
| 5 | Carlos Mario Zuluaga Pardo | 81,33 |
| 6 | Julián Mauricio Ruiz | 77,37 |
| 7 | Diana Carolina Torres García | 75,73 |
| 8 | Amanda Madrid Panesso | 74,18 |
| 9 | Karol González Mora | 69,25 |
| 10 | Rosalba Jazmín Cabrales | 65,81 |

Cinco hombres y cinco mujeres. El puntaje **no ordena la elección**: decide el
Congreso por votación, y el primero del concurso es el que menos respaldo tiene.

## El índice de la pieza — cómo se calcula

`índice = 0,60·respaldo + 0,25·convergencia + 0,15·puntaje_norm`

- **respaldo (0-100)** — juicio codificado a partir de los respaldos declarados
  en prensa, ponderado por tamaño del bloque y descontando vetos activos.
  Es el componente subjetivo; va con el peso mayor porque es lo que decide una
  elección de Congreso, y por eso el rótulo de la pieza dice "índice", no
  "probabilidad".
- **convergencia (0-100)** — en cuántos de los 6 artículos-sonajero verificados
  aparece listado entre los favoritos (El Colombiano ×2, Infobae, Cambio,
  Semana, Valora Analitik).
- **puntaje_norm** — puntaje del concurso reescalado sobre el rango de los diez
  (65,81 → 0; 86,74 → 100).

### v2 · corte 10 de agosto (vigente)

| | respaldo | converg. | pts norm | **índice** | prob. |
|---|---:|---:|---:|---:|---:|
| Laverde | 80 | 100 | 81,5 | **85** | 27% |
| Castro | 76 | 100 | 89,7 | **84** | 26% |
| Zuluaga | 40 | 75 | 74,0 | **54** | 16% |
| Monsalvo | 18 | 50 | 77,0 | **35** | 11% |
| Abadía | 22 | 25 | 100 | **34** | 10% |
| *otros 5* | — | — | — | — | 10% |

Laverde y Castro quedan a **un punto**: empate técnico entre esos dos, con
Zuluaga desprendido. La pieza no afirma un ganador.

### v1 · corte 6 de agosto (histórico, para medir el movimiento)

| | respaldo | converg. | pts norm | **índice** | prob. |
|---|---:|---:|---:|---:|---:|
| Zuluaga | 78 | 100 | 74,0 | **83** | 24% |
| Laverde | 72 | 100 | 81,5 | **80** | 23% |
| Castro | 65 | 100 | 89,7 | **78** | 22% |
| Monsalvo | 35 | 83 | 77,0 | **53** | 15% |
| Abadía | 8 | 33 | 100 | **28** | 8% |

## Métrica que se midió y se descartó

Share of voice en titulares (corpus de **161 titulares únicos**, 12-jun a 6-ago,
Google News vía el pilar Medios de Caudal). Filtrado a contexto Contraloría
quedan 126 titulares y solo **26 menciones nominales**: Castro, Monsalvo,
Zuluaga y Torres empatan en 19,2% cada uno. Con esa n el share of voice **no
discrimina** y no se usó como estimador.

⚠️ Gotcha: hay un homónimo — "Carlos Mario Zuluaga" también aparece en notas de
fútbol (FCF, VIVA, polla mundialista). Contar el apellido sin exigir contexto
"contralor/contraloría/control fiscal" le inflaba las menciones.

## Qué cambió entre el 6 y el 10 de agosto

1. **Se dio vuelta la punta.** Cambio tituló el 10-ago *"Zuluaga pierde votos y
   Laverde toma ventaja"* (el slug del artículo es aún más duro: *"Zuluaga queda
   fuera"*), citando a El Reporte Coronell: Zuluaga "dejó de ser opción viable" y
   Laverde y Castro "se consolidan como los principales contendores".
   ⚠️ Es **una** fuente: El Espectador y La FM del mismo día siguen contando a
   Zuluaga entre los punteros. Por eso baja a 16% y no a cero.
2. **Apareció el fiel de la balanza: el Centro Democrático (47 votos).** Se reúne
   el **martes 11 en la tarde** y anuncia candidato por comunicado; La FM reporta
   que "ahí se pegan los demás partidos". La sesión se pasó a la mañana del 12
   justamente para cerrar la ventana de negociación de última hora.
3. **Se resolvió la duda de los 165 votos**: el umbral es **144**, mayoría
   absoluta de 286. Liberal 34 + Conservador 28 + La U 20 = 82, lejos del umbral.
   Pacto Histórico tiene 63 curules, insuficientes solos; se sumaría al que vaya
   ganando. Cambio Radical podría quedar en libertad.
4. **Monsalvo "no ha cogido vuelo entre las bancadas"** (El Espectador, 10-ago).
5. **Abadía sube levemente**: Semana ya lo lista entre los cinco con más opciones,
   aunque sigue sin padrino. Diana Carolina Torres también entró a esa lista.

⚠️ **La foto del 10 de agosto es provisional por diseño.** Con el Centro
Democrático definiendo el 11 en la tarde, la varianza de estos números es enorme:
la actualización de esa noche es la que tiene valor predictivo.

## Tendencias (los triángulos)

- **Zuluaga =** — estable; puntea el reporteo desde el 27-jul (Portafolio,
  La Opinión: "el candidato que lidera la carrera").
- **Laverde ↓** — era la carta de consenso (Cambio, 26-jul); lo golpearon el
  rechazo de los sindicatos de la Contraloría a sus declaraciones (Blu Radio
  29-jul, Pluralidad Z 30-jul) y un audio de supuesto acoso que él denuncia
  como campaña de desprestigio (Semana 31-jul, Área Cúcuta 5-ago).
- **Castro ↑** — "se consolida" (25-jul), pero Semana revela el 31-jul sus
  reuniones con funcionarios petristas y el MinInterior designado Rodrigo Lara
  pidió a la coalición no pactar con el Pacto Histórico.
- **Monsalvo ↓** — el 1-jul era "la candidata del nuevo Gobierno"; el 6-ago el
  gobierno entrante negó las reuniones y crece la presión para que se retire
  (Portafolio, Infobae). La Red de Veedurías pidió la renuncia de una candidata.

## Respaldos declarados (los del bullet azul)

- **Zuluaga**: Efraín Cepeda / Partido Conservador; sectores del Pacto; el
  MinComercio designado Mauricio Gómez Amín. Riesgo: se lee como continuidad
  del contralor saliente.
- **Castro**: Procurador Gregorio Eljach, sectores del Pacto, magistrado Carlos
  Camargo; cercanía con el excontralor Felipe Córdoba. Riesgo: concentración de
  los órganos de control.
- **Laverde**: liberales, Lidio García y Simón Gaviria; posible coalición
  Liberal + Pacto + Centro Democrático.
- **Monsalvo**: grupo político del Cesar (exministro Sergio Araújo) y el
  empalme de Hacienda de De la Espriella.

## Contexto que puede mover todo antes del 12

- El gobierno De la Espriella **se apartó** de la elección → bancadas de la
  coalición quedan libres.
- Uribe pidió al próximo contralor "cero persecución a Petro y De la Espriella".
- Se especula con una alianza **uribismo + petrismo**, como en elecciones
  anteriores de órganos de control.
- El Consejo de Estado **rechazó** la suspensión provisional del concurso
  (30-jul) → la elección quedó en firme, pero siguen vivas la demanda de
  nulidad y demandas ante la Corte Constitucional.

## Regenerar

```bash
python3 tools/contralor-2026/build_img.py
```

Si cambia el panorama antes del 12, editar el dict `CAND` del script (campos
`idx`, `tend`, `nota`, `resp`) y volver a correr.
