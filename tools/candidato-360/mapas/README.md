# Candidato 360 · el mapa del CRM

## Las tres escalas

| Nivel | Qué muestra | De dónde sale |
|---|---|---|
| **Municipio** | El departamento o el municipio completo | `mapas-2026/Departamentos-mps/` |
| **Comuna / localidad** | La ciudad por comunas o localidades | `mapas-2026/Ciudades-COM-LOC/` |
| **Barrio** | Los barrios de la comuna que se abrió | Ver abajo |

## Barrios: dos caminos y un modo degradado

**Bogotá y Cali** tienen cartografía barrial partida por localidad o comuna en
`candidato-360-data/` y un diccionario puesto→barrio hecho a mano. Es lo más
preciso y no se toca.

**Medellín, Pereira, Manizales y Barranquilla** tienen un GeoJSON de ciudad
entera y ningún diccionario. Ahí el puesto de votación se ubica **por
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
| **Ibagué · Montería** | **No hay capa publicada.** Quedan enchufadas a `Ciudades-COM-LOC/IBAGUE-BARRIOS.json` y `MONTERIA-BARRIOS.json`: el día que el archivo aparezca en S3, el nivel de barrio arranca solo. Mientras tanto, puestos de votación como puntos |

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
```

Las tres necesitan Leaflet en disco:

```
npm pack leaflet@1.9.4 && tar xzf leaflet-1.9.4.tgz     # deja package/dist/
```
