# scrape-encuestas-wiki

Scrapes la tabla canónica de encuestas presidenciales primera vuelta
2026 desde **Wikipedia** (sección *Oficialización de candidaturas*) y
las normaliza al esquema de `Bases de datos/encuestas_porcentajes.csv`.

Útil para:

- **Auditar** que ninguna encuesta nueva se nos pasó por alto sin tener
  que abrir el PDF del CNE.
- **Bootstrap** del CSV cuando salga una encuesta y el usuario aún no
  haya descargado el PDF.

## Requisitos
- Node ≥ 18 (usa `fetch` nativo y nada más).

## Uso

```bash
# JSON con todas las encuestas que la tabla de Wikipedia muestra
node scrape.js

# Reporta sólo las que NO están en encuestas_porcentajes.csv
node scrape.js --diff

# Imprime las filas CSV listas para `>>` al CSV local
node scrape.js --diff --csv >> "../../Bases de datos/encuestas_porcentajes.csv"
```

## Cómo distingue "ya conozco esta encuesta"

Para evitar falsos positivos por diferencias menores entre Wikipedia y
nuestro CSV, dos encuestas se consideran la misma cuando:

1. La firma cae al mismo bucket en `FIRMA_ALIAS` (ej: `"Centro Nacional
   de Consultoría"` y `"CNC"` → `cnc`; `"Atlas Intel"` y `"AtlasIntel"`
   → `atlas-intel`).
2. Las fechas caen en el mismo bin de 5 días dentro del mismo mes.

Esto absorbe la diferencia natural entre la fecha de **fin de campo**
(que reporta Wikipedia) y la fecha de **publicación** (que suele estar
en el CSV).

## Limitaciones conocidas

- **Forzosos vs abierto**: Wikipedia muestra para Invamer la pregunta
  *forced choice* (con menos candidatos). Nuestro CSV usa el escenario
  abierto. El scraper no diferencia y reportará los valores tal como los
  ve Wikipedia. Hay que reconciliar a mano cuando hay diferencias > 1pp.
- **Modo de la encuesta**: Wikipedia no trae columna de "modo"
  (presencial/digital/telefónica). El CSV de salida lo deja vacío.
  Si se necesita, completar manualmente o cruzar contra
  `cne_encuestas_2026.csv` por id de CNE.
- **Año implícito**: si la celda de fecha sólo dice "Abr 2026", se usa
  el día 15 como aproximación.
- **Renombramiento de columnas**: el orden de candidatos está hardcoded
  en `COL_CAND` y vale para la tabla de *Oficialización de candidaturas*.
  Si Wikipedia introduce un nuevo aspirante a esa tabla habrá que
  actualizar el array.

## Salidas
- `--csv` agrega encabezados sólo cuando NO se usa `--diff`. Con
  `--diff --csv` se omite el header (asume append).
- Categorías `Otros / Blanco / Ninguno / NS-NR` se incluyen como filas
  con `categoria=presidencial_nacional` y nombre del candidato igual al
  rótulo agregado.

## Próximos pasos

- Cachear la respuesta de la API local 1h para evitar peticiones
  redundantes (`~/.cache/scrape-encuestas-wiki/wikitext.json`).
- Comparación numérica: cuando la encuesta SÍ existe en local pero los
  pcts difieren > 1pp en algún candidato, marcar como "discrepancia".
