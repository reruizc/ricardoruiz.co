# Decisiones técnicas iniciales

## Pipeline ahora

`Catálogo público DASCD → PDF publicado → validación/hash → texto por página → chunks → BM25`

El catálogo es un Drupal View con filtros GET (`title`, `field_terma_target_id`, `field_sub_tema_target_id`). El crawler usa un conjunto pequeño de términos públicos para obtener variedad; cada candidato procede de una fila del catálogo, y el PDF solo se acepta si está enlazado en su propia ficha. Así no se explora almacenamiento ni se construyen URLs por conjetura.

## Datos y trazabilidad

Los campos solicitados viven en `concepts.jsonl`. La respuesta binaria se valida por firma `%PDF-` y se vuelve a abrir con `pypdf`; se conserva su SHA-256, URL de ficha, URL de PDF y URL de la consulta de catálogo.

La extracción determinística conserva un `.txt` por PDF con marcadores de página. `extractions.jsonl` enlaza cada texto con el SHA-256 del PDF y del texto, versión del motor, número de páginas, volumen extraído y diagnóstico OCR. Esto permite que futuros chunks mantengan la relación `fragmento → página → PDF → URL oficial`.

## Retrieval local

El índice actual contiene chunks limitados a una sola página, con 220 palabras objetivo y 40 de solapamiento. Se excluyen páginas o colas de menos de 40 palabras porque corresponden principalmente a pies de página y enlaces sin contenido jurídico. BM25 se calcula en memoria sobre 1.631 chunks de 728 páginas sustantivas y pondera tres veces título, tema y subtema. Para 100 documentos esto evita infraestructura adicional, permite inspección completa y mantiene costo cero. La interfaz de datos (`chunks.jsonl`) permite sustituir el motor por embeddings o búsqueda híbrida sin reprocesar los PDFs.

## Evolución prevista (sin implementar aún)

1. Adaptador `LLMProvider` (OpenAI/DeepSeek/Kimi) que reciba solo chunks recuperados y devuelva un borrador marcado como no aprobado, con sus fuentes.
2. Embeddings y búsqueda híbrida como experimento comparable contra el baseline BM25.
3. S3 opcional: `concepthia/raw/pdf`, `extracted/text`, `metadata`, configurado por variables de entorno. Ninguna operación AWS se ejecuta en este piloto.

## Costos

El crawler y la extracción son locales: solo requieren tráfico HTTP público, CPU y disco. AWS, embeddings e inferencia LLM no generan costos durante esta etapa.
