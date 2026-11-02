# Rastreo de la Ley de Rescate (PL 477 de 2026 Cámara)

Alimenta `ley-de-rescate-avance.html`: en qué etapa va, cuándo se vota, quién tiene los votos y qué artículos se discuten.

```
temas.json          libro de códigos: 24 temas que agrupan los 106 artículos (nombre, artículos, página, nota)
articulos.json      los 106 artículos con página y tema · lo genera build_articulos.py
hitos.json          bitácora curada a mano. Un hito con "etapa":"pon|inf|anu|c1|p2|c3|p4|con|san" marca esa etapa como hecha
voces.json          declaraciones verificadas una por una (p: a apoya · r rechaza · m reparos · i sin definir)
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

- **La ficha manda.** La prensa nunca marca una etapa como hecha. Una señal de prensa va a la bitácora rotulada «sin verificar».
- **La postura es frente a la medida, no frente al Gobierno.** «Informa» no es neutralidad del medio: es que el titular no toma partido.
- **Sin modelo no hay postura.** Sin `DEEPSEEK_API_KEY` el tema sale por palabras y la postura queda vacía.
- **Las llaves solo se leen del entorno.** No se traen de la Lambda ni de archivos.
- **Personas comunes sin nombre.** Ni en la página ni en el corpus: citas sin `@`, enlaces ni teléfonos. El autor solo se guarda si es verificado o tiene 50.000 seguidores.
- Un orden del día escaneado no significa que el proyecto no esté: va a `agenda_no_leida`.
- Al cambiar el libro de códigos o el prompt, subir `CLAS_VERSION`: reclasifica todo.
- Cuando salga la ponencia, actualizar `temas.json`, porque el articulado cambia.
