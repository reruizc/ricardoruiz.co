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

Datos en `Bases de datos/ley-rescate/` (gitignored): `corpus.json` y `clasif.json` son privados porque guardan
comentarios de personas. Solo `estado.json` se publica, en
`s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/legislativo/ley-rescate/estado.json` (gzip). En Actions el
estado anterior vive en el prefijo privado `ricardoruiz.co/ley-rescate-privado/`. `?local=1` lee el JSON del disco.

## Encender

1. Subir el estado inicial al prefijo privado:
   `aws s3 cp "Bases de datos/ley-rescate/" s3://elecciones-2026/ricardoruiz.co/ley-rescate-privado/ --recursive --exclude "estado.json"`
2. Publicar `estado.json`: `python3 tools/ley-rescate/rastreo.py --solo-calcular --subir`
3. `git push origin HEAD:main`, y correr el workflow a mano una vez desde la pestaña Actions.

La primera corrida dirá si `RR_S3_KEY_ID` puede escribir en esos prefijos y si los campos de los actores siguen vigentes.
La capa de redes nunca se ha probado en vivo: se escribió con el código ya probado de la escucha, pero falta esa primera corrida.

## Costo

| Capa | Costo | Tope |
|---|---|---|
| Prensa | gratis | no aplica |
| Clasificación DeepSeek | centavos por corrida | no aplica |
| Redes Apify | a medir en la primera corrida; estimado US$1 al día | `LR_TOPE_USD` 1,5 por corrida · `LR_TOPE_MES_USD` 45 |

Para apagar las redes sin apagar lo demás: variable `LR_REDES=off` en GitHub.

## Reglas

- **La ficha manda.** La prensa nunca marca una etapa como hecha. Una señal de prensa va a la bitácora rotulada «sin verificar».
- **La postura es frente a la medida, no frente al Gobierno.** «Informa» no es neutralidad del medio: es que el titular no toma partido.
- **Sin modelo no hay postura.** Sin `DEEPSEEK_API_KEY` el tema sale por palabras y la postura queda vacía.
- **Las llaves solo se leen del entorno.** No se traen de la Lambda ni de archivos.
- **Personas comunes sin nombre.** Citas sin `@`, enlaces ni teléfonos. El autor solo sale si es verificado o tiene 50.000 seguidores.
- Un orden del día escaneado no significa que el proyecto no esté: va a `agenda_no_leida`.
- Al cambiar el libro de códigos o el prompt, subir `CLAS_VERSION`: reclasifica todo.
- Cuando salga la ponencia, actualizar `temas.json`, porque el articulado cambia.
