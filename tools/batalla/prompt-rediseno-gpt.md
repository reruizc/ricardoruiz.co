# Prompt para GPT · rediseño visual de «Anatomía de una batalla»

Adjunta en GPT el ZIP `Bases de datos/batalla/paquete-gpt.zip` y pega el texto de abajo.

---

Eres diseñador de producto editorial y de datos. Te adjunto un ZIP con `batalla.html`, un tablero de un solo archivo (HTML + CSS + JS sin frameworks, mapas con Leaflet 1.9.4) que mide la disputa por el enmarcado de un hecho político en prensa y en X. Hoy se ve como un dashboard genérico oscuro. Quiero que se sienta como un producto de **Caudal × Cauce**: serio, editorial, con carácter, y entretenido de seguir, como una transmisión deportiva bien hecha.

**Qué hay en el ZIP (rutas relativas a la raíz)**
- `batalla.html` — la página (todo el CSS va en el `<style>` del `<head>`).
- `fonts/helveticaneue{,-light,-medium,-bold}.woff2` — las fuentes que carga.
- `caudalxcauce.png` — logo Caudal × Cauce de la barra superior.
- `caudalxcauce/img/{mapa-rio-azul,ondas,topo,mapa-ciudad}.webp` — texturas de Caudal.
- `Bases de datos/batalla/marcha-14oct-2026/batalla.json` — los datos de la marcha. Para verla con ellos, sirve la carpeta (`python3 -m http.server`) y abre `batalla.html?local=1`.
- Referencias en vivo: https://ricardoruiz.co/batalla.html (la página actual), https://ricardoruiz.co/caudal-portada.html (Caudal) y https://cauce.co (Cauce).

**Identidad que hay que usar**
- Caudal: fondo casi negro `#0a0a0a`, azul cielo `#98c0f8` como acento, tinta `#f0f0f0` / `#b8c0cc` / `#8a93a3`, titulares en Helvetica Neue 800 con tracking negativo, la «onda» (trazo curvo de 120×24) como separador, y texturas de mapa de río / ondas concéntricas / topografía de fondo (archivos `caudalxcauce/img/{mapa-rio-azul,ondas,topo,mapa-ciudad}.webp`).
- Cauce (cauce.co): toma de ahí la sobriedad de consultoría en asuntos públicos (tipografía, espacios en blanco, tono). Logo combinado en `caudalxcauce.png`.
- Syne 800 solo para la marca «Ricardo.Ruiz».

**Restricciones que no se negocian**
1. No cambies los `id` del HTML ni la lógica JS: el JS pinta todo por `id`. Solo HTML de estructura, CSS y, si hace falta, clases.
2. Los colores de datos no son decorativos y ya están decididos: Gobierno `#1f9e92` (verde azulado), Oposición `#d4702a` (naranja), los dos marcos `#c9ccd3`, sin marco `#6b7280`. Se eligieron para no evocar partidos y están validados para daltonismo. No los cambies ni uses el azul cielo de la marca para un bando.
3. Lenguaje: nada de «ganó / perdió». Usa «ventaja», «puntos», «lleva la iniciativa».
4. Debe funcionar a 375 px de ancho sin scroll horizontal, con 16 px de margen.
5. Sin librerías nuevas; fuentes ya cargadas en `fonts/`.

**Qué quiero que entregues**
- El bloque `<style>` completo reescrito y los cambios mínimos de marcado.
- Un encabezado más editorial: kicker, titular grande, onda, bajada, el botón amarillo del disclaimer y el reloj del partido como marcador de transmisión.
- El marcador por fases como «sets» con más presencia (tipo marcador de tenis o Fórmula 1).
- Tarjetas con menos bordes y más jerarquía tipográfica; números grandes con `tabular-nums`.
- Pestañas que se lean como secciones de una revista, pegadas arriba al hacer scroll.
- Un estado vacío y uno de carga que no se vean rotos.

Explica en 10 líneas las decisiones y lista cualquier `id` que hayas tenido que mover.
