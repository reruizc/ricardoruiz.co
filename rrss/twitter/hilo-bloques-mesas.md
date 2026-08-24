# Hilo · respuesta al "patrón matemático de bloques" (prueba de rachas)

Versión ciudadana, 12 trinos. Réplica y controles del estadístico presentado en la exposición
de Presidencia.

Código: `tools/bloques-mesas/build.py` + `join_edad_voto.py` → `Bases de datos/output_bloques/`
Fuentes: preconteo 2V 2026 por mesa · escrutinio 2V 2022 y 2V 2018 por mesa (GCS RNEC) ·
**Edadygenero.xlsx (RNEC): votantes por mesa por edad y sexo**, dato oficial observado.

---

**1/**

Lo que están mostrando es esto: en un puesto de votación con 24 mesas, las mesas 1 a 12 las
gana Abelardo y las 13 a 24 las gana Cepeda. Partido por la mitad. Y aparece en 1.350 puestos.

Visto así asusta. Y la observación es cierta: eso pasa, y pasa mucho.

Pero tiene una explicación que se puede comprobar, y voy a comprobarla con datos de la propia
Registraduría. 🧵

---

**2/** · Primero: ¿por qué a uno le toca la mesa que le toca?

La Registraduría no reparte a la gente entre las mesas al azar. Reparte **por número de
cédula**, en orden. Los números más bajos en las primeras mesas, los más altos en las últimas.

Y el número de cédula es, básicamente, el orden en que uno nació. Un señor de 75 años tiene una
cédula de 5 millones. Un pelao que la sacó hace tres años tiene una de 1.100 millones.

O sea que la fila de mesas de un puesto no está revuelta: **está ordenada de los más viejos a
los más jóvenes**. Siempre. Por diseño del sistema.

---

**3/** · Y eso se nota muchísimo. Mírenlo:

Así se ve el país por dentro, según la posición de la mesa en el puesto (dato observado de la
Registraduría, quién votó y con qué edad):

| | votantes de 18 a 30 | mayores de 56 | mujeres |
|---|---|---|---|
| **primeras mesas** | **2,3%** | **64,9%** | 17,5% |
| mesas del medio | 12,9% | 23,0% | 61,0% |
| **últimas mesas** | **72,4%** | **0,8%** | 53,9% |

Las primeras mesas del país son 2% jóvenes y 65% mayores de 56. Las últimas son 72% jóvenes.

Fíjense en la columna de mujeres: las primeras mesas son casi puros hombres. ¿Por qué? Porque
las cédulas de las mujeres arrancaron en el 20.000.000. También quedan ordenadas.

---

**4/** · Ahora junten eso con lo que pasó en 2026

La elección pasada fue la más partida por edad que hemos medido en Colombia. Lo publicamos en
junio:

· Cepeda sacó cerca del **60% entre los votantes de 18 a 25**… y como el **7% entre los mayores
de 61**.
· Abelardo, al revés: 23% entre los jóvenes, **79% entre los mayores**.

Entonces hagan la cuenta. Tenemos gente **ordenada por edad** en la fila de mesas, y un voto
**partido por edad**.

El resultado no puede ser otro: las primeras mesas las gana uno y las últimas las gana el otro.
No es una operación. Es lo que tenía que pasar.

---

**5/** · ¿Y entonces qué mide la "prueba matemática"?

La prueba que usaron se llama prueba de rachas. Es sencilla: imagínense un mazo de cartas rojas
y negras bien barajado. Si al repartirlas le salen todas las rojas juntas y después todas las
negras, uno con razón sospecha que alguien tocó el mazo.

El problema es que **acá el mazo nunca estuvo barajado**. Viene ordenado de fábrica, por
cédula.

Aplicar esa prueba a las mesas de un puesto es como sorprenderse de que en un salón de clase
los estudiantes estén sentados por orden de lista. Claro que sí: los sentaron así.

---

**6/** · Prueba número 1: el mismo test, en las elecciones anteriores

Si el patrón fuera fraude, debería aparecer solo en 2026. Corrí exactamente el mismo cálculo
en las dos elecciones anteriores:

| elección | puestos revisados | con "bloques" | cuántos por azar | qué tan raro |
|---|---|---|---|---|
| **2V 2026** Cepeda–Abelardo | 2.821 | **1.617** | 64 | 25 veces más |
| **2V 2022** Petro–Rodolfo | 2.269 | **1.393** | 52 | **27 veces más** |
| **2V 2018** Duque–Petro | 2.317 | **1.311** | 53 | 25 veces más |

Sale igual en las tres. Y donde sale **más marcado** es en 2022: la elección **que ganó Petro**.

Si esto probara que hubo fraude, probaría que también lo hubo cuando ganamos.

---

**7/** · Prueba número 2: la más contundente

Corrí el mismo test sobre algo donde el fraude sencillamente no cabe: **la edad de la gente que
votó en cada mesa**. Ese dato lo publica la Registraduría.

Resultado: el "patrón imposible" aparece en **4.104 de 4.292 puestos. El 95,6% del país.** Y
sale todavía más marcado que en los votos.

Léanlo despacio: la edad de los votantes llega en bloques en 96 de cada 100 puestos.

Nadie falsifica la fecha de nacimiento de la gente que hace la fila. **El bloque ya venía en la
lista**, antes de que se contara un solo voto.

---

**8/** · El ejemplo que mostraron en el video

El Colegio Maximino Poitiers, en Suba. El del video: 3.267 contra 3.674, mesas 1 a 12 Abelardo,
13 a 24 Cepeda.

Este es ese mismo puesto en 2022, con quiénes votaron ahí según la Registraduría:

| mesa | de 18 a 30 años | mayores de 56 |
|---|---|---|
| 1 | 1,5% | 50,8% |
| 2 | 2,2% | 43,7% |
| 3 | 2,0% | 1,0% |
| 4 | 2,0% | 12,0% |
| 5 | **69,8%** | 0,4% |
| 6 | **99,0%** | 0,0% |
| 7 | 50,2% | 0,0% |
| 8 | 55,6% | 0,0% |
| 9 | 67,0% | 2,2% |

La mesa 6 de ese puesto era **99% gente entre 18 y 30 años**. Las cuatro primeras, 2%.

El corte estaba ahí **cuatro años antes**. No hay que explicar por qué las primeras mesas votan
distinto a las últimas: votan personas distintas.

---

**9/** · ¿Y de qué tamaño es el efecto? Se puede medir

Crucé 97.172 mesas de 2022 con la edad de quienes votaron en cada una. Y comparé **solo mesas
del mismo puesto**, para que no me digan que es el barrio, el estrato o la ciudad: es el mismo
colegio, el mismo día, la misma cuadra.

· Entre más joven la mesa, más votó por Petro: correlación de **+0,60**.
· Pasa en el **97% de los puestos del país**.
· En un puesto normal, de sus mesas más viejas a sus mesas más jóvenes el voto de izquierda
sube **15 puntos**.

Ese es exactamente el tamaño del salto que produce los bloques del video.

---

**10/** · Que quede claro lo que sí y lo que no

Lo que encontraron **es real**: las mesas de un puesto votan muy distinto entre sí. Eso existe
y está bien visto.

Lo que no se sostiene es la conclusión. Un indicador que marca "imposible" en el 96% de los
puestos, en las tres últimas elecciones, y también sobre las fechas de nacimiento, no sirve
para decir que una de esas elecciones fue robada. No distingue nada.

---

**11/** · Y si uno quiere buscar fraude en serio, ¿dónde se busca?

En los formularios. En comparar el E-14 que firman los jurados contra lo que quedó registrado.
Eso es lo que hacen los testigos electorales y para eso existe el escrutinio. Ahí sí una
diferencia es una diferencia.

Nosotros publicamos las anomalías que encontramos, aunque apuntaran para el otro lado: los
municipios de Nariño y Cauca donde la votación se comportó rarísimo, con alertas de la
Defensoría y presión armada documentada. Ahí ganó Cepeda con más del 90%.

Lo pueden ver acá: ricardoruiz.co/voto-fusil-2026.html

---

**12/** · Los datos, para que cualquiera lo rehaga

Publicamos el resultado del test para los 2.821 puestos de 2026, la réplica en 2022 y 2018, y
el cruce de edad y voto de las 97.172 mesas.

Dos salvedades honestas: nuestros votos de 2026 son del preconteo, no del escrutinio final; y
el archivo de edad de la Registraduría sale con años de retraso, así que la edad de 2026
todavía no existe y los controles van con el dato real de 2022.

A mí me da igual quién ganó ese día. Pero si vamos a hablar de esto, hagámoslo bien.

[link al CSV]
