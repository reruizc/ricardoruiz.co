# Artículo LinkedIn — Colombia votó por edades (1V 2026)

Publicar como artículo largo de LinkedIn. Tono profesional, primera persona.
Nota completa: ricardoruiz.co/edades-1v.html

---

## El voto es secreto, pero la edad deja huella: cómo reconstruimos el voto generacional de la primera vuelta

La pregunta parecía imposible de responder: ¿por quién votaron los jóvenes y por quién los mayores el pasado 31 de mayo? En Colombia no hay exit polls confiables a esa escala y el voto es secreto. Pero hay un dato público que casi nadie usa: la Registraduría publica cuántas personas votaron —por edad y sexo— en cada puesto de votación del país.

Cruzamos ese dato con los resultados de la primera vuelta: 23 millones de votos en más de 12.000 puestos. El resultado es el retrato generacional más fino que se ha publicado de esta elección.

**Lo que encontramos.**

La primera vuelta fue, sobre todo, un choque de generaciones:

- Iván Cepeda ganó cerca de 6 de cada 10 votos entre los menores de 25 años — y menos de 1 de cada 10 entre los mayores de 60.
- Abelardo De La Espriella hizo el camino exactamente inverso: 23% entre los jóvenes y cerca de 8 de cada 10 votos entre los mayores.
- Cepeda puntea en todas las franjas de edad… menos en la de 60+. Esa franja —una quinta parte del electorado, y la que más crece según el DANE— definió la delantera nacional.

El patrón no nació en 2026: se heredó. Cepeda calcó el perfil joven de Petro (60% vs 62% entre los 18-25 de 2022). Abelardo heredó el perfil mayor de Fico Gutiérrez y lo amplificó: de 69% a 79% entre los mayores. La brecha generacional no es nueva; lo nuevo es que se volvió más profunda.

Y es un fenómeno nacional, no regional. En Bogotá, Medellín, Cali, Barranquilla, Cartagena y Bucaramanga el voto se voltea de joven a mayor, sin excepción. Llevado al mapa: si solo votaran los jóvenes, Cepeda ganaría el duelo en casi todo el país; si solo votaran los mayores de 60, Abelardo ganaría en todos los departamentos. Todos.

**Cómo se hace esto sin violar el secreto del voto.**

El método se llama inferencia ecológica y es el estándar de la literatura electoral (Goodman 1953; Duncan & Davis 1953; King 1997) — el mismo que usan las cortes de Estados Unidos para estimar voto por grupo en litigios electorales. La lógica: en más de 12.000 puestos, la composición etaria de los votantes varía muchísimo. Hay puestos donde casi 1 de cada 3 votantes supera los 60 años y otros donde apenas 1 de cada 10. Cruzar esa variación con el voto de cada candidato permite estimar —con intervalos de confianza— cómo votó cada grupo.

Tres decisiones técnicas hicieron la diferencia:

1. **La edad de los votantes de 2026 aún no se publica, así que la proyectamos**: perfil etario 2022 de cada puesto + envejecimiento poblacional del DANE + total real de votantes 2026 de cada puesto. Solo se modela la mezcla interna; los totales son dato. Antes de usar el método lo sometimos a prueba: proyectando 2018→2022 y comparando contra lo observado, el error promedio fue de 0,3 puntos por grupo de edad.

2. **Estimación con restricciones y por estratos regionales**, con intervalos por bootstrap. La consistencia es exacta: el modelo reproduce el resultado nacional al decimal.

3. **En las grandes ciudades, estimamos por localidad y comuna.** Aquí está la lección metodológica que más me gusta compartir: la primera versión del modelo decía que el 0% de los mayores de Bogotá votó por Cepeda. Cero. Sospechoso. Al revisar, el problema no eran los datos: era que en las grandes ciudades la edad y el ingreso van de la mano —los mayores se concentran en los barrios más ricos—, y el método no podía separar "ser mayor" de "vivir en barrio caro". Lo verificamos corriendo el mismo modelo sobre 2022, con datos observados: a Petro le pasaba idéntico. La solución fue estimar por localidad y comuna dentro de cada ciudad. El 0% de Bogotá resultó ser un 9%; el de Cali, un 14%; el de Barranquilla, un 23%. Medellín sí quedó al piso: menos del 5%.

Esa última parte es, para mí, el punto central. Un análisis cuantitativo serio no es el que nunca se equivoca: es el que está construido para detectar sus propios errores, corregirlos y documentarlos. Por eso cada cifra que publicamos va con su intervalo, cada estimación extrema va con su cota, y los límites van en el cuerpo del análisis — no en la letra pequeña.

**Por qué importa para lo que viene.**

La segunda vuelta del 21 de junio se va a decidir, en parte, en términos generacionales: la franja 36-45 es la frontera donde el país se parte en dos, los mayores de 60 son el grupo que más crece, y los electorados de los dos finalistas casi no se tocan por edad (la mitad del voto de Cepeda es menor de 36 años; 4 de cada 10 votos de Abelardo son de mayores de 60). Para campañas, medios y analistas, leer esa estructura no es un lujo académico: es el tablero.

El análisis completo —con gráficas, mapas, metodología y sus límites— está publicado en ricardoruiz.co. Los datos son públicos; el código y el modelo, documentados. Así debería ser siempre el análisis electoral.

---

*Ricardo Ruiz — análisis electoral y de políticas públicas con datos. ricardoruiz.co*
