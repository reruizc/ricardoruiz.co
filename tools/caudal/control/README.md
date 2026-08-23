# Caudal · Órganos de control y altas cortes

Primer corte publicado: Corte Constitucional. El harvester también incluye el
adaptador de Consejo de Estado (SAMAI), pero esa fuente solo entra al índice si
devuelve resultados verificables; nunca se rellena con enlaces de búsqueda.
No mezcla resultados de buscadores externos: cada fila conserva su URL oficial.

```bash
python3 tools/caudal/control/harvest_jurisprudencia.py fetch
python3 tools/caudal/control/harvest_jurisprudencia.py build
```

Los artefactos de `Bases de datos/leyes-senado/control/dist/s3/` se suben como
`metadata/control.jsonl` y `metadata/control-stats.json`. Luego se publica la
Lambda actualizada. Procuraduría queda fuera de este corte hasta validar una
fuente con identificador y enlace público estable.
