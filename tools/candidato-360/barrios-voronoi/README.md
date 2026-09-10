# Candidato 360 · barrios por Voronoi (Ibagué y Montería)

Ibagué y Montería tienen **comunas** publicadas (`IBAGUEX.json`, `MONTERIAX.json`)
pero **ningún GeoJSON de barrios** en ninguna fuente alcanzable: ni en
`Ciudades-COM-LOC/`, ni en `barrios-veleta/` (que trae once ciudades y no estas
dos), ni en los portales de datos abiertos, que desde el entorno de trabajo
están bloqueados.

Lo que sí hay, para cada puesto de votación, es su **coordenada** y el **barrio**
que la Registraduría le asigna (`PUESTOS_GEOREF.csv`). Con eso se hace lo mismo
que el proyecto hizo para Medellín antes de tener la capa oficial
(`tools/build-barrios-voronoi.py`): cada puesto se queda con el área que le
queda más cerca (Voronoi), las celdas del mismo barrio se unen, y cada barrio
queda con nombre, comuna, censo y los puestos que lo forman.

**No es cartografía oficial.** El límite de cada barrio es el punto medio entre
sus puestos y los de los vecinos. Sirve para ubicar la votación y repartir la
meta; no para discutir dónde termina un barrio. El archivo lleva el aviso en
`metadata.disclaimer` y el CRM lo repite en la nota del mapa.

## Qué cambia frente al de Medellín

| | Medellín (2025) | Acá |
|---|---|---|
| Recorte | Al contorno de la ciudad | A **su comuna**: ningún barrio cruza un límite, porque el CRM los pinta por comuna |
| Puestos rurales | Entraban | **Se omiten**: su celda recortada al contorno urbano daba una astilla en el borde de la ciudad |
| Puestos en el borde | — | La comuna de un puesto la decide la geometría, no el CSV; si cae en un hueco entre polígonos, va a la más cercana (hasta 400 m) y su celda se recorta con la holgura justa para que el puesto quede dentro de su barrio |
| Nombres | Tal cual | Se funden las variantes de la Registraduría («BARRIO LA PRADERA» y «LA PRADERA», «EL DORADO» y «DORADO») y se quita el «Barrio » del frente |

| Ciudad | Puestos | Barrios | Comunas | Omitidos (corregimientos) |
|---|---|---|---|---|
| Ibagué | 106 | 71 | 13 | 23 |
| Montería | 95 | 40 | 9 | 37 |

## Correrlo

```
pip3 install numpy scipy shapely
python3 tools/candidato-360/barrios-voronoi/construir.py            # ambas
python3 tools/candidato-360/barrios-voronoi/construir.py monteria
```

Escribe `candidato-360-data/barrios-voronoi/{CIUDAD}-BARRIOS.json` (136 y 37
KB). Van en el repo, no en S3: la página los carga por ruta relativa. Si algún
día aparece la capa oficial de una de las dos, basta cambiar la URL en
`CITY_BARRIO_LAYERS` y quitar el `aviso`.

## Pruebas

```
node tools/candidato-360/prueba-barrios-voronoi.mjs     # los archivos (14)
node tools/candidato-360/prueba-ciudades.mjs            # el camino genérico del CRM (10)
```

La primera usa la **misma** función de punto-en-polígono del CRM y comprueba que
cada puesto caiga dentro del barrio que formó: si eso falla, la ubicación por
coordenada del mapa lo perdería.
