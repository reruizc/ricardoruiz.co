# Candidato 360 · el mapa del CRM

## Las tres escalas

| Nivel | Qué muestra | De dónde sale |
|---|---|---|
| **Municipio** | El departamento o el municipio completo | `mapas-2026/Departamentos-mps/` |
| **Comuna / localidad** | La ciudad por comunas o localidades | `mapas-2026/Ciudades-COM-LOC/` |
| **Barrio** | Los barrios de la comuna que se abrió | Ver abajo |
| **Puestos** | Los puestos de votación en su coordenada, con el tamaño del punto como votación | `PUESTOS_GEOREF.csv` |

El tercer botón se llama por lo que hay: «Barrio» en las ciudades con
cartografía barrial (`ciudadTieneBarrios`), «Puestos» en el resto. Y en un
**municipio sin capa de comunas** —La Ceja, Sabaneta, el 90 % del país— los
niveles son solo dos, «Municipio | Puestos» (`nivelesMunicipio`): antes se veía
el polígono del municipio y no había forma de bajar. A escala de puestos el
polígono pasa a contorno y entra el callejero atenuado.

Cuando la campaña se muda a un territorio donde el historial no tiene **ni un
voto** (de la JAL de Teusaquillo al Concejo de Leticia), el mapa del historial
no dice nada de la campaña nueva: se muestra el **territorio al que aspira**
(`renderTerritorioDeCampana`) con sus puestos de votación dimensionados por
**censo electoral**, que es lo único honesto cuando todavía no hay votos
propios ahí. El panel pasa a llamarse «Mapa del territorio de campaña» y las
vistas por año desaparecen: todas mostrarían votaciones que no cuentan donde
ahora compite.

Los botones de nivel son los que **cambian el dibujo**. En un mapa de ciudad no
hay «Municipio»: mostraba exactamente lo mismo que «Comuna» —la ciudad entera
dividida— y dejaba la alcaldía de Medellín abriendo en un nivel que no existe.
Quedan **Comuna/Localidad** y **Barrio** (o **Puestos** donde no hay
cartografía barrial). En un municipio sin comunas sí hay dos niveles reales,
«Municipio | Puestos».

Ciudades con capa por comuna o localidad (`CITY_JAL_LAYERS`, las mismas de
veleta.html): Bogotá (localidades), Medellín, Cali, Barranquilla (localidades),
Manizales, Pereira, Ibagué, Montería, Bucaramanga, Cúcuta, Neiva, Popayán,
Sincelejo y Villavicencio.

Dos cosas que la fuente escribe distinto y hay que traducir:

- Los **corregimientos de Medellín** van del 17 al 21 en la Registraduría y del
  50 al 90 en la cartografía del DAP (Altavista es 17 y 70). Sin la tabla, sus
  votos no caían en ningún polígono.
- Las **zonas 90 y 98** —censo consolidado y cárceles— no son territorio y no
  pueden servir de comuna de respaldo: la 90 se pintaba encima del
  corregimiento de Santa Elena, que en el DAP también es «90», y salía en el
  desglose como «undefined». En Bogotá la zona sí es la localidad, así que el
  respaldo se conserva para el resto.

Una candidatura cuya votación cabe entera en **una ciudad con capa de comunas**
se pinta por comuna, sea JAL, Concejo o Alcaldía (`ciudadDeLaCandidatura` →
`renderCiudadMap`). Antes solo la JAL entraba por ahí y un concejal de Medellín
veía el municipio entero como una mancha, con la cartografía a un clic.

## Barrios: dos caminos y un modo degradado

**Bogotá y Cali** tienen cartografía barrial partida por localidad o comuna en
`candidato-360-data/` y un diccionario puesto→barrio hecho a mano. Es lo más
preciso y no se toca.

**Medellín, Pereira, Manizales, Barranquilla, Ibagué y Montería** tienen un
GeoJSON de ciudad entera y ningún diccionario. Ahí el puesto de votación se ubica **por
coordenada**: cada puesto trae lat/lng en `PUESTOS_GEOREF.csv` y se busca en qué
polígono cae (ray casting con caja envolvente). Es exacto y evita casar nombres,
que casi nunca coinciden entre la Registraduría y el catastro («LA ESPERANZA #2»
contra «La Esperanza No. 2»). Se dibujan solo los barrios que capturaron algún
puesto de esa comuna.

| Ciudad | Capa barrial |
|---|---|
| Bogotá | `candidato-360-data/bogota-barrios/{loc}.js` + diccionario |
| Cali | `candidato-360-data/cali-barrios/{comuna}.js` + diccionario |
| Medellín | `bases+de+datos/MEDELLIN_BARRIOS_OFICIAL.json` (por coordenada) |
| Pereira · Manizales · Barranquilla | `Ciudades-COM-LOC/<CIUDAD>-BARRIOS.json` (por coordenada) |
| Ibagué · Montería | `candidato-360-data/barrios-voronoi/` — **aproximación por Voronoi** sobre los puestos de votación, recortada por comuna (ver `tools/candidato-360/barrios-voronoi/`). No hay capa oficial publicada; la nota del mapa lo avisa |

Un puesto a menos de 60 m del borde de un barrio —la coordenada de la
Registraduría no es de topógrafo— se queda con el barrio más cercano; más lejos,
no se inventa.

Para sumar una ciudad basta agregarla a `CITY_BARRIO_LAYERS` en
`candidato-360.js` con la URL de su capa y cómo leer el nombre y el código del
barrio. No hace falta nada más: la ubicación por coordenada es genérica.

## Qué se reparte en cada barrio

Si la persona ya sacó votos en esa comuna, la meta se reparte con **su propia
huella**. Si no —una comuna que nunca disputó, o un salto de corporación—, con
el **censo electoral** de cada barrio, que sale de sumar mujeres y hombres por
puesto en `PUESTOS_GEOREF.csv`. La nota del mapa dice cuál de las dos se usó:
un mapa de censo leído como un mapa de apoyo miente.

## Tres trampas del encuadre

**Leaflet solo usa zooms enteros, salvo que se le diga lo contrario.** Entre un
nivel y el siguiente hay un factor 2, y `fitBounds` elige el mayor entero en el
que cabe la ciudad: Bogotá quedaba en zoom 11 ocupando la mitad del marco, con
Kennedy y Bosa diminutas y el resto vacío. El mapa se crea con `zoomSnap: 0.1`
y el encuadre es exacto. Era la causa principal de que Cali y Bogotá se vieran
pequeñas.

**Bogotá se encuadra por su perímetro urbano, no por sus localidades.** Usme
baja hasta 4,27 de latitud y Ciudad Bolívar hasta 4,38, casi todo páramo y
vereda. La ventana (`BOGOTA_VENTANA_URBANA`) va de Suba (4,84) al norte urbano
de Usme y Ciudad Bolívar (4,49) y de Bosa (-74,22) a los cerros (-73,99); lo
que queda por fuera se dibuja igual, desbordado por la derecha del mapa rotado.

**El municipio no es la ciudad.** Fuera de Bogotá, el marco lo dan las áreas
que concentran el **98 % de la votación**; el resto se sigue dibujando,
desbordado. Así un corregimiento enorme y sin votos no achica la ciudad.

**Leaflet mide el contenedor cuando se le pide, no cuando termina de crecer.**
Si el mapa se arma mientras el panel se acomoda, elige un zoom para una caja que
ya no existe. `encuadrarBounds` mide y encuadra tres veces —de una, a los 60 ms
y a los 260 ms—. Sin eso el mapa quedaba **23 veces** más ancho de lo debido.

## El color es el del partido

El mapa codifica una **magnitud** (cuántos votos), así que la rampa es de un solo
tono, de claro a oscuro. Lo que cambia con el partido es el **tono**: rojo para
el Liberal, azul para el Conservador, púrpura para el Pacto, verde para la
Alianza Verde. La paleta y la rampa viven en `partidos-bloques.js`
(`PARTIDO_COLOR`, `rampaDePartido`), junto al diccionario de bloques.

Los pasos se calculan en **OKLab**, no mezclando con blanco en sRGB: mezclar en
sRGB apaga el tono y los pasos claros salen grises. Las claridades están
elegidas para que ningún par consecutivo baje de ΔE 8 y para que el paso más
claro no se confunda con el gris de «sin votos» — si no, «pocos votos» y
«ningún voto» se verían igual. Lo comprueba `prueba-colores.mjs` sobre las 29
bases.

Tres decisiones que vale la pena conocer:

- El **Pacto no es rojo** aunque así se pinte en otras páginas del sitio: en
  rojo choca con el Liberal. De los dos tonos que se propusieron (amarillo o
  púrpura) se tomó el púrpura, porque el amarillo casi no tiene recorrido hacia
  lo oscuro y la rampa se aplana.
- Una **coalición** hereda el color de la primera parte que se reconozca:
  «Nuevo Liberalismo - Agrupación Política En Marcha» va en el del Nuevo
  Liberalismo.
- Un movimiento **sin color propio** toma el de su **bloque ideológico**, que es
  información de verdad, y no un tono inventado por una función de hash. La nota
  del mapa lo dice.

Sin partido —o antes de elegirlo— el mapa se queda con el verde de siempre.

## Modales sobre el mapa

Leaflet pone sus paneles en z-index 400-1000 y `.leaflet-container` no crea
contexto de apilamiento, así que esos paneles competían con toda la página y el
mapa se dibujaba **encima** de las fichas. `.crm-map` lleva `isolation:isolate`
para encerrarlos y los modales suben a `z-index:1200`. Cualquiera de las dos
cosas basta; están las dos porque el costo es cero y el síntoma es feo.

## Pruebas

```
node tools/candidato-360/prueba-mapa.mjs        # Bogotá: ventana urbana, callejero, censo (15)
node tools/candidato-360/prueba-ciudades.mjs    # Medellín: encuadre, barrios, modal (10)
node tools/candidato-360/prueba-salto-crm.mjs   # el salto de corporación en el mapa (13)
node tools/candidato-360/prueba-barrios-voronoi.mjs  # los barrios aproximados de Ibagué y Montería (14)
node tools/candidato-360/prueba-colores.mjs     # la rampa según el partido (10)
```

Las tres necesitan Leaflet en disco:

```
npm pack leaflet@1.9.4 && tar xzf leaflet-1.9.4.tgz     # deja package/dist/
```
