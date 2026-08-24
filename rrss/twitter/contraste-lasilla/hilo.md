# Hilo · respuesta a La Silla Vacía (autopsia de Paloma)

Imágenes en `rrss/twitter/contraste-lasilla/png/` · una por trino (el 9 va sin imagen).

---

**1/** 📎 `contraste-lsv-1.png`

Algunas personas me citaron sobre este artículo de LSV, así que démosle una revisión.

Lo que sigue: cómo se movió de verdad el voto de derecha entre la consulta de marzo y la 1ª vuelta, mesa a mesa. Y dónde las cifras de la nota no resisten la aritmética. 🧵

---

**2/** 📎 `contraste-lsv-2.png`

Los datos: 119.309 mesas cruzadas entre el escrutinio de marzo (Senado + consultas) y el preconteo de 1V, con la llave dep-mun-zona-puesto-mesa.

El método: regresión ecológica —la misma familia que usa La Silla—, pero con cotas de King, placebos y robustez regional.

---

**3/** 📎 `contraste-lsv-3.png`

Primer hecho: la Gran Consulta fue, en esencia, el Centro Democrático votando.

El 84% de los votantes CD-Senado eligió a Paloma ese mismo día. Casi ninguno se saltó la consulta.

LSV dice que solo el 42% la votó "y el resto se abstuvo". Esa cuenta no cuadra 👇

---

**4/** 📎 `contraste-lsv-4.png`

Si solo el 42% del CD hubiera votado la consulta, ¿quién puso los 5,64 millones de la Gran? Los demás partidos no fueron: entre el 83% y el 99% de sus votantes no votó ninguna consulta.

De los 3,16M de Paloma en consulta, 8 de cada 10 eran votantes del CD.

---

**5/** 📎 `contraste-lsv-5.png`

¿Y de marzo a mayo? La estampida del CD hacia Abelardo fue real, pero fue de ⅔, no del 97%.

Paloma retuvo ~1 de cada 4 votantes de su partido (23–32%; techo lógico: 48,7%).

El 97%/1% de LSV es una "esquina" del modelo: corrimos su misma especificación y entrega 100%/0%.

---

**6/** 📎 `contraste-lsv-6.png`

La prueba más sencilla: la cuenta no cierra.

Con los % del sankey de LSV, Paloma recibiría ~416 mil votos de los partidos. Sacó 1.637.665. Quedan 1,2 millones sin origen (74%).

Nuestro modelo reconstruye el 99,1% de su votación.

---

**7/** 📎 `contraste-lsv-7.png`

¿De dónde salió entonces el 1,64M de Paloma?

• 45% su propia consulta (retuvo solo 23 de cada 100)
• 23% resto de la Gran
• 10% Oviedo
• 15% votó en marzo sin consulta
• 8% votantes nuevos

El 77% viene del universo de la Gran Consulta: quedó su núcleo duro.

---

**8/** 📎 `contraste-lsv-8.png`

La derecha en tres actos:

1. Marzo: el CD votó su consulta en bloque (84% por Paloma).
2. El voto útil se reversó: ⅔ del CD migró a Abelardo; de la Gran, 70–96% terminó con él.
3. Mayo: Paloma quedó con su núcleo, sin maquinarias (0–12%) y casi sin votos nuevos (≤8%).

---

**9/** (sin imagen · cierre)

En la dirección, LSV tiene razón: hubo desbandada y las maquinarias no se movieron por Paloma.

En las magnitudes (97%, 1%, 42%) publicaron las esquinas de una regresión ecológica sin diagnósticos.

Datos: Registraduría. Método y cotas a disposición de quien quiera replicar.

---

*Todos los trinos < 280 caracteres. Cifras: corrida principal de
`tools/trasvase-paloma/cd_senado_y_composicion.py` y `contraste_lasilla.py`
(119.309 mesas · soporte en `Bases de datos/output_trasvase_cd/`).*
