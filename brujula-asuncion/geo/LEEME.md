# Barrios de Asunción · polígonos (GeoJSON WGS84)

Todos los archivos están en **EPSG:4326**. El origen INE viene en EPSG:4674
(SIRGAS 2000); la diferencia con WGS84 es submétrica y se reproyectó con geopandas.
Las coordenadas caen en lon −57.674 … −57.525 · lat −25.381 … −25.224 (Asunción).

| Archivo | Fuente | Features | Campo nombre | Código |
|---|---|---|---|---|
| **`ASUNCION-BARRIOS.geojson`** (recomendado) | INE · Cartografía Digital **2012** · capa `Barrios_Localidades_Asuncion` | 68 | `BARLO_DESC` (MAYÚSC.) · `nombre` (Title Case) | `BAR_LOC` (001-068) · `CLAVE` |
| `ASUNCION-BARRIOS-INE2022.geojson` | INE · Cartografía Censal **2022** · capa `Barrios Localidades_Asuncion` | 68 | `BARLO_DESC` · `nombre` | `BAR_LOC` · `CLAVE_BAR` |
| `ASUNCION-BARRIOS-ARCGIS-POB2012.geojson` | ArcGIS Online `Mapa_Poblacion_Asuncion_WFL1` (usuario de Esri PY, derivado del INE 2012) | 68 | `BARLO_DESC` | — (trae `Pob_2012` y `superficie`) |

## URLs exactas
- INE 2012 (ZIP con 8 GeoJSON: barrios, manzanas, vías, hidrografía, distrito, depto):
  `https://www.ine.gov.py/microdatos/register/CARTOGRAFIA%20DIGITAL%202012%20ZIP/GEOJSON/00%20ASUNCION.ZIP`
  (también hay `/SHAPE/` y `/KML/`; índice en `https://www.ine.gov.py/microdatos/cartografia-digital-2012.php`)
- INE 2022 (RAR, mismo contenido + .qmd de QGIS):
  `https://www.ine.gov.py/microdatos/register/CARTOGRAFIA%20CENSAL%202022/CARTOGRAFIA%20CENSAL_GeoJSON/00%20ASUNCION.rar`
  (índice en `https://www.ine.gov.py/microdatos/cartografia-digital-2022.php`)
- ArcGIS población 2012:
  `https://services9.arcgis.com/r89cNWDiPAS7i8iA/arcgis/rest/services/Mapa_Poblacion_Asuncion_WFL1/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson`
- ArcGIS copia del INE 2022 (no guardada, idéntica a INE2022 en nombres/campos): item `144aef0520624f14b3eb91705ea088d0` (`BarriosAsuncion`, services9 r89cNWDiPAS7i8iA).

**Licencia:** el INE no declara licencia en la página de descarga (datos públicos de
la cartografía censal, uso habitual con cita "INE, Cartografía Censal"). Los items de
ArcGIS no traen `licenseInfo`.

## Por qué el 2012 es el recomendado
El pedido habla del **Atlas de Barrios 2012** y sus 68 nombres. La capa 2012 es esa
exacta. La capa 2022 también tiene 68, pero **no es la misma lista**: el código
`BAR_LOC=032` cambió de polígono y de nombre — en 2012 es **DE LA RESIDENTA**
(noreste, junto al Botánico; centroide −57.547, −25.241) y en 2022 es **SAN JUAN**
(centro, entre Jara y San Blas; centroide −57.605, −25.270). Con ese cambio se
redibujaron Botánico (IoU 0,31 entre censos), Loma Pytá (0,39), Jara (0,72) y
San Blas (0,79); los otros 63 barrios son casi idénticos (IoU > 0,93).
Si el cruce es con datos del censo 2022 o posteriores, usar `ASUNCION-BARRIOS-INE2022`.

## Problemas encontrados
- El GeoJSON 2012 del INE trae la **Ñ rota en origen** (byte U+FFFD) en tres
  nombres: BAÑADO CARA CARA, CAÑADA DEL YVYRAY, ÑU GUASU. Se corrigió tomando el
  nombre de la capa 2022 por código `BAR_LOC` (verificado carácter por carácter).
- En 2022 el INE escribe `ASUNCIÓN` con tilde en `DPTO_DESC`/`DIST_DESC`; en 2012 sin tilde.
- La columna `DIST_DESC_` (2022) se renombró a `DIST_DESC` para que las dos capas compartan esquema.
- Los nombres del INE van en MAYÚSCULAS sin tildes (`MBURICAO`, `BOTANICO`,
  `TTE. SILVIO PETTIROSSI`, `MADAME ELISA ALICIA LINCH`); al cruzar con listas
  externas, normalizar sin tildes/mayúsculas.

## Fuentes revisadas y descartadas
- Municipalidad de Asunción: no expone geoportal/WFS alcanzable (`geo.`, `geoportal.`,
  `datos.asuncion.gov.py` no resuelven); `/catastro/` es un visor ArcGIS JS sin servicio público visible.
- IDE Paraguay (`ide.gov.py`): no resuelve.
- datos.gov.py: la búsqueda "barrios" no devuelve límites de barrio.
- OpenStreetMap (Overpass): no se necesitó como fallback al existir fuente oficial.
- HDX / GADM: solo hasta distrito.
