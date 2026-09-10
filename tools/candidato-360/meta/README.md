# Candidato 360 · la meta de votos

`vote-target.js` calcula cuántos votos hacen falta para entrar a una
corporación en un territorio, y la ficha ⓘ del CRM lo explica pieza por pieza.

## Antes: la última curul de la corporación

Para Concejo, JAL y Asamblea se reconstruye la elección de 2023 con umbral y
cifra repartidora (art. 263) y se toma el candidato elegido con menos votos.
Ese número **engaña**: en el Concejo de Bogotá 2023 fue **6.314**, la tercera
curul de la lista LARA, arrastrada por los 70.032 votos de Julián Forero.
Entrar por la Alianza Verde costó 13.942 y por el Liberal 19.808. Una sola
cifra para toda la corporación le decía lo mismo a quien iba por una lista
grande que a quien tenía que jalar una lista pequeña.

## Ahora: lo que cuesta entrar por SU lista

Con el partido que la persona escribió (`campana.partido`), la meta parte de la
lista de ese partido en esa corporación y territorio en 2023:

| Caso | Punto de partida | Ejemplo Bogotá 2023 |
|---|---|---|
| **La lista ganó k curules** | Los votos del k-ésimo elegido de la lista: hay que entrar de k | Alianza Verde, 10 curules → 13.942 (el 10.º) |
| **La lista no ganó curul** | Primero la lista tiene que llegar a la cifra repartidora. Si el resto de la lista repite, a quien la encabece le toca poner la diferencia: `max(cabeza, cifra − (total − cabeza))` | Dignidad & Compromiso sumó 26.673, la cifra fue 33.419 |
| **El partido no corrió en 2023** | Su fuerza se estima con la **Cámara de 2026** en el departamento, escalada al tamaño de la corporación (`votos × válidos_corp / válidos_cámara`). Si eso arrastra k curules, la meta es lo que suele sacar el k-ésimo de una lista de ese tamaño (mediana de las listas de 2023 con k curules); si no, la lista tiene que jalarse como en el caso anterior | Salvación Nacional: 190.113 a Cámara en Bogotá |
| **Sin lista ni Cámara** | El piso de la corporación, diciéndolo | Una organización nueva |

**Es una sola lógica para Concejo, Asamblea y JAL**: las tres se reconstruyen
igual (umbral y cifra repartidora sobre las listas de la circunscripción) y la
meta por partido se calcula encima. Corrido contra los índices reales:

| Corporación | Piso de la corporación | Por lista |
|---|---|---|
| Asamblea de Antioquia (26 curules) | 11.788 | Centro Democrático, 6 curules → 18.662 · Liberal, 4 → 25.474 |
| Asamblea de Cundinamarca (16) | 13.545 | Cambio Radical, 4 → 13.545 · Alianza Verde, 1 → 17.588 · Salvación Nacional, en la lista «Centro Democrático y Salvación Nacional», 1 → 17.566 |
| JAL de Suba (11) | 3.873 | Alianza Verde, 2 → 5.090 · Nuevo Liberalismo, en «Nuevo Liberalismo - Agrupación Política En Marcha», 3 → 3.873 · Salvación Nacional, sin lista en 2023, por Cámara 2026 → 5.865 |
| JAL de Teusaquillo (9) | 1.114 (curul verificada) | Alianza Verde, 2 → 1.114 · Centro Democrático, 2 → 1.896 |

En la JAL la circunscripción es «LOCALIDAD · CIUDAD» y el índice se filtra a
esa localidad: la lista de la Alianza Verde en Usaquén no cuenta para Suba.
Para la Cámara de 2026 se usa el departamento de la localidad; es el mismo
proxy que en Concejo, con la misma limitación: mide la marca en el
departamento, no en la localidad.

La lista del partido se encuentra por las palabras que lo identifican (sin
«PARTIDO», «MOVIMIENTO», «DE», «LA»…): «PARTIDO NUEVO LIBERALISMO» encuentra la
lista «NUEVO LIBERALISMO EN MARCHA», y si hay varias coaliciones con el
partido, gana la de más votos. La última curul de la corporación sigue en la
ficha como **piso**, para que se vea la diferencia.

Encima de ese punto de partida van los mismos tres ajustes de siempre: censo
(+1,4 % a 2027), participación (2023 → 2027, +1 punto) y margen competitivo
(3 %), y se redondea hacia arriba.

**Alcaldía y Gobernación** no cambian: son uninominales y ganar cuesta lo que
sacó el ganador, sea cual sea el aval.

## Límites que la ficha dice

- Que la lista repita su tamaño de 2023 es un supuesto, no un pronóstico.
- La Cámara de 2026 es un proxy: mide la marca del partido en el departamento,
  no una lista al Concejo. Sirve para partidos nuevos; para los demás manda 2023.
- Las listas cerradas salen solas: su cabeza carga todos los votos y «entrar
  de k» es el orden de la lista, no una votación personal.

## Pruebas

```
node tools/candidato-360/prueba-meta.mjs     # la ficha ⓘ y la meta por partido en Concejo, Asamblea y JAL (29)
```

La prueba usa un Concejo de tres listas y tres curules y comprueba los cuatro
casos, más una Asamblea (donde Salvación Nacional tiene que dar con su lista
de coalición) y una JAL (donde la lista de otra localidad no puede mezclarse),
además de que las piezas que muestra la ficha multipliquen exactamente la meta
que se ve en pantalla.
