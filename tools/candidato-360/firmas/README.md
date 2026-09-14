# Candidato 360 · aval por firmas (tarjeta 07)

A la **Alcaldía** y a la **Gobernación** se llega de dos maneras y las dos son
normales: con el aval de un partido o **por firmas**, como grupo significativo
de ciudadanos. La página solo sabía preguntar por el partido, así que quien iba
por firmas tenía que escribir una organización que no existe.

A un concejo o a una asamblea no se le pregunta: ahí se compite por lista, y una
lista siempre tiene organización detrás.

## Por qué el espectro y no el partido

Por firmas no hay huella de partido que seguir. Lo único que orienta la
recolección es **dónde se ubica la candidatura**, así que se pregunta —cinco
posiciones: izquierda, centro-izquierda, centro, centro-derecha, derecha— y con
eso el reparto usa la **huella del bloque ideológico**, el mismo diccionario
(`partidos-bloques.js`) que pinta los mapas y clasifica los partidos. El mapa
toma además el color de ese bloque, para que lo que eligió sea lo que ve.

No predice apoyo. Dice dónde hay más gente a la que la conversación le suena,
que es donde una firma cuesta menos trabajo. La tarjeta lo dice con esas
palabras.

## Cuántas firmas

Se estima con la regla del **artículo 9 de la Ley 130 de 1994**: el 20 % del
censo electoral dividido por los cargos a proveer —uno, en un cargo
uninominal— con el **tope de 50.000 firmas** que la misma norma fija. El censo
sale de sumar los puestos de votación del territorio (`PUESTOS_GEOREF`).

Se presenta siempre como **estimación**: el censo de corte y las resoluciones
de la Registraduría mueven el número exacto, y eso va escrito en el modal. La
cifra útil del producto no es la legal sino el **reparto**: cuántas firmas
buscar en cada comuna o municipio.

## Cuántos partidos hay por municipio (para la vitrina)

Medido sobre las listas al Concejo de 2023, 1.016 municipios con datos:

| | organizaciones |
|---|---:|
| Promedio | **9,3** |
| Mediana | 9 |
| p10 · p90 | 5 · 15 |
| Máximo (Villavicencio, Barrancabermeja, Facatativá) | 23 |
| Bogotá · Medellín · Cali | 12 · 14 · 15 |

Por eso el campo de partido puede ser una **vitrina de logos** y no un campo de
escritura: nueve tarjetas se eligen con el ojo. El catálogo del departamento
trae más (listas de JAL, de Cámara, el mismo partido escrito de cuatro formas),
así que la vitrina deduplica **por logo** —que es lo que el ojo distingue— y
corta en 16 por fuerza electoral. Lo que queda fuera se escribe: el campo sigue
ahí para una coalición que se inscribe ahora y no está en ningún catálogo.

La vitrina aparece donde haya al menos 4 logos en
`candidato-360-data/logos-partidos/<dep>/index.json` (hoy: Bogotá). Para otra
ciudad basta agregar sus logos y correr
`tools/candidato-360/logos/construir.mjs <dep>`.

La prueba es `tools/candidato-360/prueba-firmas.mjs`.

## Cuando el territorio no tiene resultados por comuna

Los resultados de concejo bajan a comuna en **once ciudades**; en el resto del
país —el 95 % de los municipios— no hay huella de una familia política por área,
y la tarjeta se rendía ahí («todavía no podemos repartirlas»), que es dejar sin
plan justo a quien más lo necesita. Ahora hay plan B: el reparto se hace por
**censo electoral de cada puesto**, y se dice. No es lo mismo y no se disfraza —
el censo no mide afinidad, mide dónde hay gente—, pero para una recolección eso
ya es la mitad del problema. Los puestos cuya columna BARRIO dice «NO APLICA»
(cárceles, censo consolidado) se agrupan como «Sin barrio identificado»: no son
un sitio al que se pueda mandar a alguien con un formulario.

La huella se busca en el territorio de la **campaña**, no en el del historial:
quien se muda de ciudad tenía el reparto de firmas en la ciudad vieja.

## Más firmas que votos

En un municipio pequeño el requisito puede ser **mayor que la votación con la
que se gana**: La Ceja pide 11.003 firmas (20 % de 55.015) y la alcaldía se ganó
en 2023 con 10.213 votos. No es un error del cálculo, es la regla: el 20 % se
aplica igual en un municipio de 55.000 habilitados que en uno de 500.000, y el
tope de 50.000 solo alivia a las ciudades grandes. La tarjeta lo compara con la
meta y lo dice con todas las letras, porque el número solo deja pensando que
algo está mal.
