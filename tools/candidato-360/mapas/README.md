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
| **Ibagué · Montería** | **No hay.** Se muestran los puestos de votación como puntos |

Para sumar una ciudad basta agregarla a `CITY_BARRIO_LAYERS` en
`candidato-360.js` con la URL de su capa y cómo leer el nombre y el código del
barrio. No hace falta nada más: la ubicación por coordenada es genérica.

## Qué se reparte en cada barrio

Si la persona ya sacó votos en esa comuna, la meta se reparte con **su propia
huella**. Si no —una comuna que nunca disputó, o un salto de corporación—, con
el **censo electoral** de cada barrio, que sale de sumar mujeres y hombres por
puesto en `PUESTOS_GEOREF.csv`. La nota del mapa dice cuál de las dos se usó:
un mapa de censo leído como un mapa de apoyo miente.

## Dos trampas del encuadre

**El municipio no es la ciudad.** Cali llega hasta los Farallones y Bogotá hasta
el páramo de Sumapaz. Encuadrar por el polígono completo deja la ciudad del
tamaño de una uña, así que se encuadra por las áreas que concentran el **98 % de
la votación**; el resto se sigue dibujando, desbordado.

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
node tools/candidato-360/prueba-mapa.mjs        # Bogotá: Sumapaz, callejero, censo (14)
node tools/candidato-360/prueba-ciudades.mjs    # Medellín: encuadre, barrios, modal (10)
node tools/candidato-360/prueba-salto-crm.mjs   # el salto de corporación en el mapa (13)
```

Las tres necesitan Leaflet en disco:

```
npm pack leaflet@1.9.4 && tar xzf leaflet-1.9.4.tgz     # deja package/dist/
```
