# Caudal · Órganos de control y altas cortes

## Estado publicado · 23 ago 2026

El índice activo contiene **499 providencias** de la Corte Constitucional,
deduplicadas a partir de las consultas `contratación estatal`, `salud`,
`pensiones`, `ambiente` y `elecciones` (rango: 2021-02-23 a 2026-08-12). Cada
fila conserva tipo, fecha, extracto y URL oficial. Los artefactos ya están
publicados en `s3://caudal-legislativo/metadata/` y la acción Lambda es
`{"action":"control","query":"…"}`.

El harvester también incluye el adaptador de Consejo de Estado (SAMAI), pero
esa fuente solo entra al índice si devuelve resultados verificables; nunca se
rellena con enlaces de búsqueda. Procuraduría queda fuera hasta validar una
fuente con identificador y enlace público estable.

```bash
python3 tools/caudal/control/harvest_jurisprudencia.py fetch --sources corte
python3 tools/caudal/control/harvest_jurisprudencia.py build
```

Los artefactos de `Bases de datos/leyes-senado/control/dist/s3/` se suben como
`metadata/control.jsonl` y `metadata/control-stats.json`. Después de cambiar
la Lambda, ejecutar `python3 tools/caudal/lambda/build_zip.py` y actualizar la
función `caudal-analiza`.
