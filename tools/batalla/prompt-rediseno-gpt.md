# Prompt para GPT · rediseño visual de «Anatomía de una batalla»

Pega esto en GPT junto con el archivo `batalla.html` y capturas de https://cauce.co y https://ricardoruiz.co/caudal-portada.html.

---

Eres diseñador de producto editorial y de datos. Te paso `batalla.html`, un tablero de un solo archivo (HTML + CSS + JS sin frameworks, mapas con Leaflet 1.9.4) que mide la disputa por el enmarcado de un hecho político en prensa y en X. Hoy se ve como un dashboard genérico oscuro. Quiero que se sienta como un producto de **Caudal × Cauce**: serio, editorial, con carácter, y entretenido de seguir, como una transmisión deportiva bien hecha.

**Identidad que hay que usar**
- Caudal: fondo casi negro `#0a0a0a`, azul cielo `#98c0f8` como acento, tinta `#f0f0f0` / `#b8c0cc` / `#8a93a3`, titulares en Helvetica Neue 800 con tracking negativo, la «onda» (trazo curvo de 120×24) como separador, y texturas de mapa de río / ondas concéntricas / topografía de fondo (archivos `caudalxcauce/img/{mapa-rio-azul,ondas,topo,mapa-ciudad}.webp`).
- Cauce (cauce.co): toma de ahí la sobriedad de consultoría en asuntos públicos (tipografía, espacios en blanco, tono). Logo combinado en `caudalxcauce.png`.
- Syne 800 solo para la marca «Ricardo.Ruiz».

**Restricciones que no se negocian**
1. No cambies los `id` del HTML ni la lógica JS: el JS pinta todo por `id`. Solo HTML de estructura, CSS y, si hace falta, clases.
2. Los colores de datos no son decorativos. Hoy: Gobierno `#4f7dff`, Oposición `#e8483a`, terreno común `#9a7be0`, neutro `#8b93a6`. En la reunión con Cauce se decidió **alejarse del rojo/azul bipartidista**: propón una pareja nueva que no evoque partidos, que sea distinguible para daltónicos (verifícalo) y que no use el azul cielo de la marca para un bando.
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
