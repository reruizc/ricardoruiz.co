# Hilo · respuesta al trino del censo electoral ("las pruebas del fraude")

Datos y método: `tools/censo-vs-poblacion/build.py` → `Bases de datos/output_censo_poblacion/`
(CSV municipio por municipio + informe.txt con todas las cifras de abajo).

Fuentes: censo electoral del Divipole 2018 / 2022 / 2026 · proyecciones de población DANE
por municipio · preconteo 1V y 2V 2026 por mesa · escrutinio presidencial 2022.
**1.120 municipios cruzados** (quedan fuera el exterior y 2 áreas no municipalizadas de Vaupés).

⚠️ Los votos de 2026 son de **preconteo**: nuestro margen nacional da 243.210 contra los
250.830 del escrutinio (3% de diferencia). No mueve ninguna conclusión, pero va declarado.

---

**1/**

El hecho de partida es cierto y es viejo: hay municipios donde el censo electoral supera a
la población proyectada. Auditarlo es legítimo y la depuración del censo es un problema real.

Lo que no resiste es la cadena que va de ahí al fraude. La revisamos municipio por municipio. 🧵

---

**2/** · Los 505 municipios no existen

El hilo enumera tres grupos: 95 con más censo que habitantes, 150 por encima del 95% y 256
por encima del 90%. Y después habla de "estos 505 municipios".

Los tres grupos se solapan por definición: un municipio con 105% está en los tres a la vez.
Sumarlos da 501 y cuenta hasta tres veces al mismo municipio.

Con la proyección DANE 2025, el universo real es: **277 municipios por encima del 90%**, de
los cuales **110 por encima del 100%**.

---

**3/** · "Más votantes que habitantes" no es lo que se midió

El censo electoral son personas **inscritas**, no personas que votaron.

Municipios donde los **votos reales** superan a la población: **0**. Ni en primera vuelta ni
en segunda.

El máximo del país es Policarpa, Nariño, con 98,7%. Y ahí ganó Cepeda 9.012 a 470.

---

**4/** · El excedente completo no alcanza

En los 110 municipios con censo mayor a la población, el excedente total —censo menos
población, hasta la última cédula— es de **87.286**.

El margen de la elección fue de 250.830.

Aunque cada una de esas cédulas fuera falsa, y todas hubieran votado por el mismo candidato,
no alcanza para dar vuelta al resultado.

---

**5/** · Y no votaron: la participación ahí es la más baja del país

Participación en 2ª vuelta:

· municipios con censo > población: **58,5%**
· municipios con censo ≤ 80% de la población: **65,4%**
· nacional: 63,7%

El caso extremo lo dice todo. **Puerto Santander** (N. de Santander): censo del **216%** de su
población… y **20% de participación**, de los registros más bajos del país.

Y ese municipio ya estaba en **197% en 2018**. No le añadieron nada dos días antes de nada.

Un censo con cédulas inertes **hunde** la participación. Votantes fantasma que votan la
subirían. Se observa lo primero.

En esos 110 municipios quedaron **345.686 cédulas sin votar**: cuatro veces el excedente
completo. Nadie tuvo que "usarlo".

---

**6/** · Las 850 mil cédulas no caben ahí

El censo de esos 110 municipios creció **61.136 cédulas en cuatro años** (2022 → 2026).

En los 277 municipios por encima del 90%, creció 278.440.

No hay dónde meter 850.000.

---

**7/** · Esto no nació en 2026

Municipios con censo mayor a la población:

· 2018 → **56**
· 2022 → **77**
· 2026 → **110**

Una tendencia estructural que sube unos 4 ó 5 municipios por año, porque el censo crece más
rápido que la población y casi nunca se depura hacia abajo.

De hecho, el censo nacional está hoy en **75,5%** de la población: por debajo del ~79% que el
propio hilo define como techo normal.

---

**8/** · En esos mismos municipios, en 2022, pasó exactamente lo mismo

Los 110 municipios con censo > población, en las dos elecciones:

· 2026 → Abelardo **+134.495** (+28,3 pp)
· 2022 → Rodolfo **+128.780** (+31,3 pp)

Prácticamente calcado. Y 2022 es la elección que **ganó Petro**, con el mismo censo, los
mismos municipios y la misma inclinación. Nadie lo llamó fraude cuando el resultado fue el otro.

---

**9/** · Lo que predice el voto es la geografía, no el censo

Municipios de menos de 20.000 habitantes, ordenados por censo/población:

| censo/población | margen 2026 | margen 2022 |
|---|---|---|
| 106,8% | Abelardo +29,5 pp | Rodolfo +30,9 pp |
| 88,9% | +25,6 pp | +25,8 pp |
| 80,5% | +16,3 pp | +16,8 pp |
| 66,2% | +3,2 pp | +5,1 pp |

Dos elecciones distintas, cuatro años aparte, candidatos distintos: la misma escalera.

La correlación entre el margen de 2022 y el de 2026 es **0,976**. Y en regresión, el
coeficiente del censo se derrumba de +0,77 a **+0,13** cuando se controla por cómo votaba ese
municipio en 2022.

El censo no explica el voto. Explica dónde quedan inscritas las cédulas.

---

**10/** · Lo que sí explica el ratio: la gente se fue

El censo electoral es por lugar de **inscripción**, no de residencia. El que migra deja la
cédula donde la inscribió, y la depuración de fallecidos va con rezago.

· municipios que **pierden** población (2018-2025): ratio medio **96,5%**
· municipios que **ganan** población: ratio medio **79,5%**

Son municipios diminutos —población mediana de 5.058— y están donde uno esperaría: **31 en
Boyacá, 25 en Cundinamarca, 11 en Antioquia**. El mapa del despoblamiento rural, no el de una
operación.

---

**11/** · El truco del subconjunto

Anulando **completos** los 110 municipios —476.077 votantes reales borrados— Abelardo sigue
ganando por **116.335**.

Y al revés: anulando los 110 municipios de **menor** ratio, ganaría por **676.327**.

Escoger el subconjunto donde pierde el rival y sumar su ventaja siempre "da". Es circular:
mide la selección, no la elección.

---

**12/** · Sí hay anomalías. No están donde el hilo las busca.

Los dos municipios donde más se acercaron los votos a la población entera son **Policarpa
(98,7%)** y **Cumbitara (96,7%)**, en Nariño. En los dos ganó Cepeda con el 95% de los votos.
Y los dos están en la lista de zonas donde documentamos alertas de la Defensoría y presión
armada sobre el voto en 2026.

Lo publicamos en su momento, con nombre propio y municipio por municipio, aunque apuntara
hacia el otro lado: ricardoruiz.co/voto-fusil-2026.html

Auditar el censo hace falta. Pero una auditoría que solo mira los municipios donde perdió el
propio candidato no es una auditoría.

---

**13/** · Los datos

Publicamos el cruce completo: censo electoral 2018/2022/2026, población DANE, votos de 1V y
2V y voto de 2022, para los 1.120 municipios. Que cada quien rehaga la cuenta.

[link al CSV]
