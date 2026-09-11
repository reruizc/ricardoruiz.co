# Candidato 360 · arquetipos del territorio (tarjeta 06)

El Proyecto DC reconstruyó, barrio por barrio en Medellín, **qué emoción ordena
el voto**: protección y orden, continuidad, supervivencia, castigo o
pertenencia. La reconstrucción usa Alcaldía, Concejo y JAL de 2015, 2019 y 2023,
y proyecta 2027. El tablero completo es `proyecto-dc/arquetipos.html`.

La tarjeta 06 del CRM no repite ese tablero: lo **cruza con la votación de la
persona**. La pregunta no es «cómo es Medellín» sino «en qué clase de barrio
están sus votos».

## Cómo se cruza

1. Cada mesa lleva al puesto (`PUESTOS_GEOREF`), y el puesto a su **barrio por
   coordenada** sobre `MEDELLIN_BARRIOS_OFICIAL.json` —la misma regla del mapa,
   no un cruce por nombres, que entre Registraduría y catastro casi nunca casan.
2. El barrio trae su arquetipo (`por-barrio.json`) y su comuna sale del propio
   polígono: «11COMUNA 11 LAURELES» contra «Laureles Estadio» no casa por texto
   y sí por geometría.
3. Los votos se suman por arquetipo, en la lectura de 2023 y en la proyección
   de 2027. El **ajuste a mano de la socia** (`votacion-2027.json`,
   `arquetipo_ajustado_2027`) manda sobre el proyectado tendencial, igual que en
   el tablero: las dos páginas no pueden decir cosas distintas del mismo barrio.

Una candidatura nueva en Medellín, sin votos propios en la ciudad, ve la ciudad
—no a sí misma— y la tarjeta lo dice.

## Fuentes (S3)

```
bases+de+datos/Proyecto+DC/arquetipos/arquetipos.json     familias, colores, escudos
bases+de+datos/Proyecto+DC/arquetipos/por-barrio.json     152 barrios · arquetipo por año + proyección 2027
bases+de+datos/Proyecto+DC/arquetipos/por-comuna.json     21 comunas · dominante y distribución
bases+de+datos/Proyecto+DC/votacion-arquetipo-2027/votacion-2027.json   ajuste definitivo 2027
```

Son ~560 KB: se piden una sola vez y **solo si la candidatura toca Medellín**.
Fuera de Medellín la tarjeta se apaga y dice qué falta, que es más honesto que
esconderla. Cuando exista cartografía emocional de otra ciudad, basta añadirla
a la misma estructura.

La prueba es `tools/candidato-360/prueba-arquetipos.mjs`.
