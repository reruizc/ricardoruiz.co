# Hilo Twitter/X — Barrios veleta · proyección 2ª vuelta 2026

Publicar jun 2026. Tuteo neutro, datos. Link final → ricardoruiz.co/barrios-veleta-1v.html
Fuente: preconteo Registraduría 1V por mesa × cartografía oficial de barrios (11 ciudades);
proyección 2V con el trasvase del simulador de ponderador-2v (matriz AtlasIntel 1V→2V) + blanco 2,4%.
Método: a cada barrio se le aplica el MISMO trasvase nacional sobre su composición real de 1ª vuelta.
Es un ejercicio de escenarios, no un pronóstico. 8 trinos · 4 imágenes.

Colores: 🔴 Cepeda · 🔵 Abelardo · 🟡 veleta (empate técnico).

---

**1/** 🧵 Para la segunda vuelta, ¿dónde se decide la elección **barrio por barrio**? Tomamos el resultado de 1ª vuelta en 11 ciudades y le aplicamos el trasvase de votos para proyectar el duelo Cepeda vs Abelardo. En dorado, los **barrios veleta** —donde se pelea voto a voto— 👇🗺️
[IMG bv-01-bogota-2v.png]

**2/** La cuenta NO es el mapa de 1ª vuelta. Sobre el voto real de cada barrio repartimos el de los eliminados como dicen las encuestas: 🔵 Paloma ~85% a Abelardo, 🔴 Fajardo ~58% a Cepeda, más Claudia, los menores y la abstención que se moviliza. Misma matriz del simulador de **ponderador-2v**, con un voto en blanco del 2,4%.

**3/** El efecto se ve clarísimo en **Bogotá**. En 1ª vuelta Cepeda ganaba **360 barrios**; al pasar el voto de Paloma a Abelardo, la proyección de 2ª vuelta lo deja en **299**, y Abelardo sube de 188 a **241**.
[IMG bv-02-bogota-1v-2v.png]

**4/** Y crecen los barrios veleta: de **43 a 51**, todos alineados sobre la vieja frontera norte–sur de la ciudad. Bogotá es **el** campo de batalla de la segunda vuelta, cuadra por cuadra.

**5/** Pero cada ciudad late distinto 👇
🔵 **Medellín** es un muro azul (Abelardo gana 143 barrios; Cepeda, 5).
🔴 **Cali** aguanta rojo (Cepeda 107 vs 36).
Cartagena y Barranquilla siguen de Cepeda; en **Pereira y Manizales** sus pocos focos se encogen al sumarle Paloma a Abelardo.
[IMG bv-03-ciudades-2v.png]

**6/** Y hay ciudades sin disputa: 🔵 **Cúcuta** entera para Abelardo, 🔴 **Soledad** entera para Cepeda. Ahí no hay veleta que valga —el mapa es de un solo color.

**7/** ¿Por qué importa? Un barrio que Cepeda ganó **por pelos** en 1ª vuelta, pero lleno de votantes de Paloma, se voltea en 2ª. Sumando las 11 ciudades, cerca de **90 barrios** quedan en empate técnico (±3 pp) en la proyección. Ahí se define el voto urbano.

**8/** Ojo con la letra: es un **ejercicio de escenarios, no un pronóstico** —asume que el trasvase es igual en todo el país y arranca del preconteo, no del escrutinio final. En el mapa puedes alternar entre 1ª y 2ª vuelta y mover el umbral.
👉 ricardoruiz.co/barrios-veleta-1v.html
[IMG bv-04-cierre.png]

---

## Notas / control
- Conteos = barrios con dato directo (puesto propio), por nombre único. Margen sobre votos válidos en 1V; en 2V, margen `(proyCepeda − proyAbelardo)/(proyCepeda + proyAbelardo)` con un voto en blanco del 2,4% sobre el total.
- Bogotá: 1V → Cepeda 360 / Abelardo 188 / veleta 43. 2V proyectada → Cepeda 299 / Abelardo 241 / veleta 51. Parques (Country Club, Simón Bolívar, etc.) excluidos.
- Otras (2V proyectada, veleta a ±3 pp): Cali 11 (C107/A36) · Medellín 10 (C5/A143) · Pereira 6 (C7/A41) · Manizales 4 (C4/A46) · Barranquilla 4 (C61/A29) · Cartagena 2 (C57/A9) · Popayán 1 (C39/A3) · Cúcuta 0 (A61) · Bucaramanga 0 (A64) · Soledad 0 (C44). Total veleta 2V ≈ 89 en las 11 ciudades.
- Trasvase (defaults AtlasIntel, ponderador-2v): fidelidad Cepeda 0,97 / Abelardo 0,95; Paloma 3,3% a Cepeda; Fajardo 58,5%; Claudia 55%; menores+Botero 47,8%; blanco/nulo 11%; abstención movilizada 6% del potencial, 34,2% a Cepeda. Cada bloque deja una fracción en blanco/casa (no transferible).
- Cruce puesto→barrio por punto-en-polígono (lat/lon de PUESTOS_GEOREF). Barrios sin puesto propio heredan al vecino más cercano (no cuentan). Bogotá rotada 90° (norte a la izquierda). Es preconteo (preliminar).
- Honestidad: tasas de trasvase uniformes en todo el país (en la realidad varían por región); el modelo es para explorar escenarios. Cifras = composición real de 1ª vuelta de cada barrio.

## Versión corta (tweet único)
Para la 2ª vuelta proyectamos, barrio por barrio en 11 ciudades, a dónde va el voto de Paloma, Fajardo y Claudia (trasvase de ponderador-2v). El efecto: en Bogotá, Cepeda pasa de ganar 360 barrios en 1ª vuelta a 299 en la proyección, y los **barrios veleta** suben de 43 a 51. 🔴 Cepeda · 🔵 Abelardo · 🟡 veleta.
👉 ricardoruiz.co/barrios-veleta-1v.html

## Carrusel Instagram (8 piezas cuadradas · rrss/instagram/barrios-veleta-png/)
Orden: 01 portada · 02 Bogotá (el campo de batalla) · 03 Bogotá 1ª→2ª (el shift) ·
04 cómo se proyecta (el trasvase) · 05 Medellín · 06 Cali · 07 cuatro ciudades · 08 cierre/link.
Genera con: `python3 tools/barrios-disputados-1v/build_hilo_maps.py ig`

### Speech / caption del carrusel
🗳️ Los barrios VELETA de la segunda vuelta

La primera vuelta ya dibujó el mapa; la segunda lo redibuja. Tomamos el preconteo **barrio por barrio en 11 ciudades** y proyectamos el duelo Cepeda vs Abelardo aplicando el trasvase de votos que miden las encuestas: 🔵 Paloma reparte ~85% a Abelardo, 🔴 Fajardo ~58% a Cepeda, más Claudia, los menores, el blanco/nulo y la abstención que se moviliza (matriz AtlasIntel del simulador de ponderador-2v), con un voto en blanco del 2,4%.

El resultado son los barrios "veleta" 🟡 —lo que en EE.UU. llaman *swing* o *purple precincts*—, donde se pelea voto a voto.

El efecto del trasvase se ve clarísimo en **Bogotá**: Cepeda ganó 360 barrios en primera vuelta, pero al sumarle Paloma a Abelardo la proyección de segunda vuelta lo deja en 299 —y los barrios veleta suben de 43 a 51, alineados sobre la vieja frontera norte–sur.

Y cada ciudad late distinto: 🔵 Medellín es un muro azul (Abelardo 143 vs 5), 🔴 Cali aguanta rojo (Cepeda 107 vs 36), Cartagena y Barranquilla siguen de Cepeda, y en Pereira y Manizales los pocos focos de Cepeda se encogen. Cúcuta y Soledad, palizas sin disputa.

⚠️ Es un ejercicio de escenarios, no un pronóstico: asume que el trasvase es igual en todo el país y arranca del preconteo, no del escrutinio final.

🗺️ El mapa interactivo —alterna 1ª/2ª vuelta, mueve el umbral y pasa el cursor por cada barrio— y la metodología en ricardoruiz.co (link en bio). Desliza →

🔴 Cepeda · 🔵 Abelardo · 🟡 veleta
#Elecciones2026 #Colombia #SegundaVuelta #Cepeda #Abelardo #DatosElectorales #Bogotá #Medellín #Cali
