# Prompt para GPT · carrusel de Instagram de «Anatomía de una contienda mediática»

Adjunta en GPT el ZIP `Bases de datos/batalla/paquete-carrusel.zip` y pega el texto de abajo.

---

Eres director de arte y editor de datos. Vas a diseñar un **carrusel de Instagram de 10 imágenes** que cuente los hallazgos de «Anatomía de una contienda mediática», un tablero de Caudal × Cauce (powered by Ricardo.Ruiz) que mide cómo se disputó en prensa y en X la narrativa de las marchas del 14 de octubre de 2026 en Colombia. La página en vivo es https://ricardoruiz.co/contienda.html. Debe sentirse como la página: editorial, sobria y entretenida de seguir, como una transmisión deportiva bien hecha. No debe parecer un panfleto ni una infografía genérica.

## Qué hay en el ZIP (rutas relativas a la raíz)
- `contienda.html`: la página. Úsala como referencia de estilo (todo el CSS está en el `<style>` del `<head>`).
- `Bases de datos/batalla/marcha-14oct-2026/batalla.json`: todos los datos. Si sirves la carpeta (`python3 -m http.server`) y abres `contienda.html?local=1`, ves la página con esos datos.
- `caudalxcauce.png`: logo Caudal × Cauce.
- `caudalxcauce/img/{mapa-rio-azul,ondas,topo,mapa-ciudad}.webp`: texturas de Caudal para fondos.
- `fonts/helveticaneue{,-light,-medium,-bold}.woff2`: la tipografía.

## Formato
- 10 imágenes PNG de **1080 × 1350 px** (4:5), numeradas `01.png` … `10.png`.
- Margen interior mínimo de 80 px. Nada importante en los 120 px inferiores (Instagram tapa esa franja con la interfaz).
- Texto legible en el teléfono: titulares de 64 px o más, cuerpo de 30 px o más, cifras grandes de 140 px o más. Máximo unas 35 palabras por imagen, salvo la portada y el cierre.
- Cada imagen lleva, discretos: el logo Caudal × Cauce arriba a la izquierda, «powered by Ricardo.Ruiz» arriba a la derecha y el contador «n/10» abajo.
- Entrega también el código que genera las imágenes (HTML/CSS o Python), para poder corregir una cifra y regenerar.

## Identidad (no la cambies)
- Fondo casi negro `#0a0a0a`. Acento azul cielo `#98c0f8`. Tinta `#f0f0f0`, `#b8c0cc` y `#8a93a3`.
- Helvetica Neue 800 con tracking negativo para titulares; Syne 800 solo para «Ricardo.Ruiz».
- La «onda» (el trazo curvo de 120×24 que aparece bajo el título de la página) como separador. Las texturas de mapa de río y de ondas como fondo, muy tenues.
- **Colores de los bandos (ya decididos y validados para daltonismo):** Gobierno `#1f9e92` (verde azulado), Oposición `#d4702a` (naranja), los dos marcos `#c9ccd3`, sin marco `#6b7280`. Nunca rojo y azul, nunca violeta, y nunca el azul cielo para un bando.
- El botón amarillo `#f5c518` se usa solo para la advertencia de «primer saque».

## Reglas de lenguaje (decididas con Cauce, no se negocian)
1. Nada de «ganó», «perdió», «ganador», «derrota» ni «victoria». Usa «ventaja», «puntos», «lleva la iniciativa», «parejo».
2. Nada de lenguaje bélico: no «batalla», «guerra», «frente», «soldados», «armamento», «batallones» ni emojis de espadas. Es una **contienda mediática**. La metáfora es deportiva: sets, marcador, jugada a jugada.
3. No tomamos partido. Se describe qué marco tomó ventaja y dónde, sin calificar a ningún bando.
4. Usa solo las cifras de abajo (todas salen de `batalla.json`). No inventes datos, citas ni nombres de cuentas.
5. Español de Colombia, tuteo neutro.

## Datos verificados
- **Corpus:** 1.282 titulares de 402 medios entre el 11 y el 14 de octubre; 724 son de prensa nacional sobre la contienda. Además, 592 publicaciones en X, de 500 cuentas.
- **Corte:** 7:30 p. m. del 14 de octubre. El pico de atención fue al mediodía (23 titulares en media hora).
- **Sets (prensa nacional, % de la fuerza):**
  - Preparación (la víspera, hasta las 9 a. m.): Gobierno 95 %.
  - Despliegue (9 a. m.–2 p. m.): parejo, 53–47.
  - Choque (2–6 p. m.): parejo, 46–54.
  - Desenlace (6–7:30 p. m.): Gobierno 70 %.
- **Marcador ponderado por atención:** 70–30 para el Gobierno (69–31 sin ponderar). El mejor tramo de la Oposición fue de 71 %, a las 2:30 p. m., con la atención en un tercio del pico.
- **El mensaje que fijó el marco:** «La protesta se respeta, pero la violencia no», más el Decreto 1525 de 2026, la noche anterior.
- **Marcos más usados:** Gobierno, «Orden y garantías» (89 titulares) y «Terrorismo y vandalismo» (24). Oposición, «Autoritarismo y represión» (69) y «Masividad en la calle» (10). «Lazos con el paramilitarismo»: 0 titulares.
- **Conversaciones paralelas:** solo el 1 % de los titulares llevó los dos marcos. La Oposición nombró al Gobierno en el 46 % de sus titulares; el Gobierno a la Oposición, en el 9 %.
- **Cómo nos ven afuera:** 90 titulares de 66 medios internacionales, contados aparte. El 68 % llevó el marco de la Oposición.
- **En X:** el Gobierno tuvo el 64 % de la fuerza, con 241 cuentas contra 133. Las publicaciones con más interacción fueron de la Oposición. La fuerza crece con el cuadrado del número de voces: duplicar las cuentas vale lo que cuadruplicar el alcance de cada una.
- **Ciudades con más titulares:** Bogotá 77, Medellín 27, Cali 22, Barranquilla 16, Bucaramanga 14.
- **Método:** cada titular se clasificó con un libro de códigos fijo (11 marcos) y quién habla en él. La fuerza = (medios o cuentas que llevan el marco)² × su peso.

## Guion sugerido (ajústalo si encuentras un mejor ritmo, sin agregar datos)
1. **Portada.** «Anatomía de una contienda mediática». Bajada: «Cómo se disputó la narrativa de las marchas del 14 de octubre, en prensa y en X». Sello amarillo «Primer saque · work in progress».
2. **Qué medimos.** 1.282 titulares · 402 medios · 592 publicaciones en X. Una línea: «No tomamos partido: observamos la cancha».
3. **La víspera.** Gobierno 95 % en la preparación. El mensaje «La protesta se respeta, pero la violencia no» fijó el marco antes de que empezara la marcha.
4. **El marcador por sets.** Los cuatro sets como en un marcador de tenis: 95 % · 53–47 · 46–54 · 70 %.
5. **Pegar cuando nadie mira.** El mejor tramo de la Oposición (71 %) llegó con la atención en un tercio del pico. Ponderado por atención: 70–30.
6. **Dos conversaciones paralelas.** 1 % de cruce. 46 % frente a 9 %: uno reacciona, el otro fija la agenda.
7. **Los marcos.** Orden y garantías frente a autoritarismo y represión, con barras de los marcos de cada bando.
8. **Cómo nos ven afuera.** 90 titulares internacionales, 68 % con el marco de la Oposición. Afuera la lectura fue otra.
9. **En X.** 64 % para el Gobierno: 241 cuentas contra 133. La regla: el número de voces pesa más que el aplauso a cada una.
10. **Cierre.** «Cada evento político relevante será una nueva contienda para medir». Vienen agendas legislativas y la contienda por alcaldías y gobernaciones. Llamado: «Mira la repetición jugada a jugada en ricardoruiz.co/contienda.html».

## Entrega
- Las 10 imágenes PNG.
- El código que las genera.
- Un texto para el pie de la publicación de máximo 120 palabras, con el enlace, y 5 hashtags sobrios (#AsuntosPúblicos, #Colombia, #AnálisisDeDatos, #Comunicación, #ConversaciónPública).
- Una lista corta que diga de qué campo de `batalla.json` sale cada cifra que usaste.
