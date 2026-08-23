# CONCEPTHIA Pro Max — piloto de corpus

Este repositorio aislado demuestra los milestones 1 y 2: descubre conceptos desde el catálogo público del DASCD, visita únicamente sus fichas públicas y descarga exclusivamente el PDF que cada ficha enlaza. No enumera ni adivina URLs de almacenamiento y limita cada ejecución al valor explícito de `--limit`. El corpus validado fue ampliado a 500 PDFs, equivalente al 17,9% de una referencia de 2.800 conceptos.

## Estructura

```text
src/concepthia_pilot/pilot.py  crawler reproducible y reporte
src/concepthia_pilot/extract.py extracción local por página
src/concepthia_pilot/retrieval.py chunks, índice y búsqueda BM25
src/concepthia_pilot/answer.py   borrador LLM trazable a los fragmentos
src/concepthia_pilot/web.py      interfaz web local
data/raw/pdf/                  evidencia PDF descargada (ignorada por Git)
data/extracted/text/           texto UTF-8 con marcadores de página
data/metadata/concepts.jsonl   metadatos trazables (ignorado por Git)
data/metadata/extractions.jsonl calidad y hashes de extracción
data/index/chunks.jsonl        fragmentos trazables para retrieval
data/reports/                  reporte del piloto (ignorado por Git)
docs/ARCHITECTURE.md           decisiones y siguiente evolución
```

## Ejecución

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python -m concepthia_pilot.pilot --limit 500 --delay 1.5 --catalogue-pages 8
PYTHONPATH=src python -m concepthia_pilot.extract
PYTHONPATH=src python -m concepthia_pilot.retrieval build
PYTHONPATH=src python -m concepthia_pilot.retrieval search "prima técnica y experiencia profesional"
PYTHONPATH=src python -m concepthia_pilot.retrieval smoke
# Evalúa si los conceptos esperados aparecen en los primeros resultados.
PYTHONPATH=src python -m concepthia_pilot.evaluate
# Requiere DEEPSEEK_API_KEY u OPENAI_API_KEY; genera un borrador con fuentes y páginas.
PYTHONPATH=src python -m concepthia_pilot.answer "¿Cómo aplica la prima técnica?"
# Abre http://127.0.0.1:8000 en el navegador.
PYTHONPATH=src python -m concepthia_pilot.web
```

La demora conservadora predeterminada es 1.5 s entre solicitudes. El crawler es reanudable: si se aumenta `--limit`, conserva el corpus ya validado y descarga únicamente conceptos nuevos. Registra un checkpoint atómico después de cada PDF válido, por lo que una interrupción no pierde trazabilidad. Cada registro JSONL conserva URLs oficiales, hash SHA-256, tamaño y páginas; los campos que el portal no expone quedan como `null`.

Cuando se necesite completar un corpus sin repasar una lista grande de fichas sin archivo publicado, se pueden elegir términos públicos y acotar las fichas revisadas: `--terms "licencia,comisión" --catalogue-pages 2 --max-candidates 40`. Sigue visitando únicamente fichas descubiertas desde el catálogo y acepta solo el PDF que la ficha publique.

## Extracción

El extractor verifica primero el SHA-256 del PDF, procesa cada página con `pypdf`, escribe archivos UTF-8 con marcadores `--- PÁGINA N ---` y registra el hash del texto, conteos y criterios OCR en `extractions.jsonl`. En el corpus actual se procesaron 500 documentos y 3.334 páginas; 490 documentos tienen texto indexable y 18 quedaron señalados como candidatos a OCR. Una extracción ya validada se reutiliza por hash aunque el PDF original ya no esté en disco.

## Alcance actual

La indexación divide cada página sustantiva en fragmentos de hasta 220 palabras con 40 palabras de solapamiento y excluye colas de menos de 40 palabras. Cada chunk conserva concepto, página, PDF, hashes y URLs oficiales. La búsqueda usa BM25 local y pondera título, tema y subtema; no requiere base vectorial ni servicios externos.

Los PDF originales viven en `s3://elecciones-2026/ricardoruiz.co/concepthia-pro-max/raw/pdf/`; el texto, índice y metadatos permanecen localmente para consultas rápidas. Para restaurar los originales: `aws s3 sync s3://elecciones-2026/ricardoruiz.co/concepthia-pro-max/raw/pdf/ data/raw/pdf/`. El comando `answer` y la web envían únicamente fragmentos recuperados al proveedor, priorizan citas `Nro. Rad: …` y usan `[S#]` solo cuando el radicado no se pudo identificar. La interfaz también prepara búsquedas complementarias en las relatorías oficiales y convierte el borrador en un documento editable con plantillas de concepto, oficio o memorando.

Para usar DeepSeek, exporta `DEEPSEEK_API_KEY`; se selecciona automáticamente y usa `deepseek-v4-flash` de forma predeterminada. Para fijar la selección o el modelo, define `CONCEPTHIA_LLM_PROVIDER=deepseek` y `CONCEPTHIA_DEEPSEEK_MODEL`. OpenAI sigue disponible con `OPENAI_API_KEY`. Nunca guardes claves en Git. Si no hay evidencia recuperada, no se llama a ningún proveedor.

## Evaluación de retrieval

`data/evals/retrieval_cases.json` contiene 25 consultas redactadas como preguntas de uso y criterios de éxito revisables. El evaluador genera `data/reports/retrieval_evaluation.json` con el `hit rate@k`, la posición del primer concepto esperado y las fuentes recuperadas. Es una línea base: cada caso debe ser validado o reemplazado por preguntas y relevancias aportadas por usuarios reales.

## Pruebas de la interfaz

Las pruebas locales no consumen una clave ni hacen llamadas al proveedor: validan el formulario, el manejo de preguntas inválidas y que una respuesta incluya fuentes. Ejecútalas con `PYTHONPATH=src python -m unittest discover -s tests -v`.
