# Rastreo de la Ley de Rescate (PL 477 de 2026 Cámara)

Alimenta el seguimiento público con identidad Caudal × Cauce: hub `ley-de-rescate-avance.html` y seis páginas
(`-reloj` · `-votos` · `-fuerzas` · `-discusion` · `-articulos` · `-voces` · `-bitacora`), con `ley-rescate-base.css` y `.js` compartidos.
Al tocar la base, subir el `?v=` en las ocho.

```
temas.json          libro de códigos: 24 temas que agrupan los 106 artículos (nombre, artículos, página, nota)
articulos.json      los 106 artículos con página y tema · lo genera build_articulos.py
hitos.json          bitácora curada a mano. Un hito con "etapa":"pon|inf|anu|c1|p2|c3|p4|con|san" marca esa etapa como hecha
voces.json          declaraciones verificadas una por una (p: a apoya · r rechaza · m reparos · i sin definir · g: con congreso · pub público · pri privado · n: nivel 5-2 del eje de poder · k: rótulo corto · al: nombres para contar menciones)
personas.json       fotos y créditos · lo genera build_personas.py (foto oficial de Senado y Cámara; Wikipedia solo con licencia libre)
votos.json          bancadas de las Comisiones Terceras y su postura inicial. Solo se marca sí/no si habló la bancada
redes.mjs           X, TikTok, Instagram y Facebook por Apify → redes-crudo.json. Reusa los actores de candidato-360/escucha/perfil.mjs
rastreo.py          trámite + prensa + clasificación + cálculo → estado.json
.github/workflows/ley-rescate-rastreo.yml   corrida diaria, 06:15 de Bogotá
```

Solo `estado.json` se publica, copiado a `ley-rescate-data/estado.json` en el repo (lo sirve
GitHub Pages; el workflow lo commitea a diario). En Actions el corpus viaja como **artefacto**
`ley-rescate-estado` de una corrida a la siguiente: las llaves de S3 del repositorio no pueden escribir en prefijos
nuevos. ⚠️ En un repo público cualquier cuenta de GitHub puede bajar un artefacto, así que el corpus se guarda sin
usuarios ni enlaces de personas comunes, y `redes-crudo.json`, que sí los trae, no se sube. ⚠️ `upload-artifact` omite
las carpetas ocultas: por eso es `lr-datos/` y no `.lr/` (así se perdió la primera lectura). `?local=1` lee el JSON del disco.

## Operar

- Correr a mano: pestaña Actions → «Ley de Rescate · rastreo diario» → Run workflow (`tope_usd` sube el tope de Apify
  solo esa vez; `sin_redes` no gasta).
- Bajar el corpus para mirarlo: `gh run download <id> -n ley-rescate-estado -D "Bases de datos/ley-rescate"`.
- Apagar las redes sin apagar lo demás: variable `LR_REDES=off` en GitHub.

## Costo

| Capa | Costo | Tope |
|---|---|---|
| Prensa | gratis | no aplica |
| Clasificación DeepSeek | centavos por corrida | no aplica |
| Redes Apify | medido: US$0,97 y US$1,06 solo en publicaciones; con comentarios, hasta US$1,5 | `LR_TOPE_USD` 1,5 por corrida (reserva US$0,40 para comentarios) · `LR_TOPE_MES_USD` 45 |

## Reglas

- **Eje de poder del esquema de fuerzas:** lectura propia con regla fija, y la página la dice. 5 escribieron el proyecto, presiden o votan en una Comisión Tercera. 4 los demás congresistas y jefes de partido. 3 gremios grandes, sindicatos e instituciones. 2 los demás. El otro eje, presencia, sí es medición.

- **Inclinaciones (nov-6):** una voz `p:'i'` puede llevar `t` (a · m · r) y `tr` (la razón); un bloque `post:'sin'` puede llevar `tiende` (si · aj · no · null) y `por`. Salen de lo que dijo su bancada u organización, nunca del modelo, y la página las pinta con borde punteado: no son postura declarada. Cuando el actor habla, se cambia `p` y se borra `t`.
- **La ficha manda.** La prensa nunca marca una etapa como hecha. Una señal de prensa va a la bitácora rotulada «sin verificar».
- **La postura es frente a la medida, no frente al Gobierno.** «Informa» no es neutralidad del medio: es que el titular no toma partido.
- **Sin modelo no hay postura.** Sin `DEEPSEEK_API_KEY` el tema sale por palabras y la postura queda vacía.
- **Las llaves solo se leen del entorno.** No se traen de la Lambda ni de archivos.
- **Personas comunes sin nombre.** Ni en la página ni en el corpus: citas sin `@`, enlaces ni teléfonos. El autor solo se guarda si es verificado o tiene 50.000 seguidores.
- Un orden del día escaneado no significa que el proyecto no esté: va a `agenda_no_leida`.
- Al cambiar el libro de códigos o el prompt, subir `CLAS_VERSION`: reclasifica todo.
- Cuando salga la ponencia, actualizar `temas.json`, porque el articulado cambia.

## Texto de los artículos y Word (nov-3-2026)

Pedido de Pablo: el PDF radicado pesa 3 MB y tiene 334 páginas, y abrirlo desde el mapa de artículos tardaba mucho.
`python3 tools/ley-rescate/build_texto_articulos.py` saca el texto de los 106 artículos de
`Bases de datos/reforma-tributaria/capa-i/pl477-2026.txt` y escribe:
- `ley-rescate-data/texto-articulos.json` (378 KB): título propio `t` o, si el artículo es «Modifíquese el artículo…»,
  un rótulo derivado `d` («Modifica el artículo 424 del Estatuto Tributario»), página `p` y párrafos `x`;
- `ley-rescate-data/word/articulo-NNN.docx` (106) y `articulado-completo.docx` (135 KB).
`ley-de-rescate-articulos.html` muestra la ficha con el texto en la misma página (`#art=N`), con el Word y el PDF
oficial como opciones. El texto se recorre en secuencia: hay artículos en mayúscula («ARTÍCULO 51.») y otros que
citan artículos de otras leyes. Solo hay que volver a correrlo si el proyecto cambia (texto de ponencia).
El barco de carga (`LR.mar`) es copia del de `caudal-comun.js`; reemplaza el «Cargando…» en las 11 páginas.
