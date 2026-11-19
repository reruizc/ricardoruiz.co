# Correo de novedades · noviembre de 2026 · borrador v2 (19-nov)

> ⚠️ Superado por `correo.html` (v1 en HTML, 19-nov). Este texto queda como historia.

Público: todos los usuarios (mismo envío que el de octubre, por rr-email-sender).
Formato: el del correo de octubre (`tools/correo-novedades-2026-10/correo.html`).
Nunca por el conector de Gmail: borra fondos e imágenes.

**Asunto:** Lo nuevo de noviembre: Ley de Rescate, Afluente, resultados para descargar y lo que presentamos el lunes
**Texto de vista previa:** El seguimiento diario de la Ley de Rescate, Afluente con Cauce, las territoriales de 2011 a 2023 para descargar y un adelanto de Candidato 360.

---

¡Hola, {{firstName}}!
Lo nuevo de noviembre

En este mes seguimos día a día la reforma tributaria más grande del año, abrimos con Cauce una forma sencilla de seguir al Congreso y al Gobierno, ordenamos quince años de resultados electorales para que los descargues, y el lunes presentamos Candidato 360.

**Al día · Congreso**
**La Ley de Rescate, todos los días**
El proyecto sigue en la comisión, y el Gobierno ya anunció que saca del IVA la canasta básica, la comida para mascotas y la medicina prepagada. En una sola página tienes cuánto tiempo le queda, quién está a favor y quién en contra, los 106 artículos explicados uno por uno y lo que dice cada sector. También hay una calculadora para ver cuánto te cambia la renta.
→ Seguir la Ley de Rescate (ley-de-rescate-avance.html) · Hacer la cuenta (ley-de-rescate.html)

**Nuevo · Afluente, con Cauce**
**Lo que se mueve en el Congreso y el Gobierno, a tiempo para opinar**
Con Cauce [una línea sobre Cauce] armamos Afluente: cada proyecto de ley explicado en lenguaje sencillo, lo que se vota en las próximas sesiones y los borradores de decretos y resoluciones del Gobierno que todavía reciben comentarios, con el plazo para opinar. Eliges tus temas y todo se filtra solo. Es gratis durante el piloto.
→ Abrir Afluente (afluente.html)

**Ampliado · Elecciones**
**Las territoriales de 2011 a 2023, para descargar**
Las elecciones de autoridades locales de 2011, 2015, 2019 y 2023 se descargan por puesto y por mesa, en CSV y en Excel, con el nombre del departamento, el municipio y el candidato al lado de cada código. En Alcaldías 2023 ves quién ganó en cada municipio y cómo quedaron los partidos en todo el país, y con el plan [Pro o Premium] también el sexo y la edad de quienes votaron en cada territorio. Si necesitas una elección o un corte que no encuentras en la página, responde este correo y lo preparamos.
→ Ir a las descargas (descargas.html) · Ver Alcaldías 2023 (alcaldias-2023.html)

**Lo que viene · el lunes 23**
**Candidato 360**
[portada con botón de play → página del adelanto]
El tablero de campaña para las territoriales de 2027: cuántos votos necesitas, dónde están, quiénes son tus rivales y cómo te va en redes, barrio por barrio. Este video es el adelanto; el lunes lo presentamos completo. Si te lanzas o asesoras una campaña, responde este correo y te guardamos un cupo.
→ Ver el adelanto
_Candidato 360 es un producto aparte, con su propio acceso._

---

## Por confirmar antes de armar el HTML
- Sexo y edad de Alcaldías: el código lo abre con **Pro** (`_planDescarga` → pro · premium · full). Ricardo dijo Premium: o el correo dice «Pro o Premium», o se sube el candado a Premium.
- Una línea que diga qué es Cauce.
- Video: borrador v10 de producto (no el de «80 años», que no se puede publicar) y origen de `assets/musica.mp3`.
- Página del adelanto en ricardoruiz.co con el video servido desde S3.

## Verificación de descargas territoriales (19-nov)
Los 16 archivos de 2011-2023 (CSV mesa, CSV puesto, Excel puesto, ZIP por departamento) responden en S3,
pesan lo mismo que la copia local, pasan la prueba de integridad y cada ZIP trae sus 33 libros con hoja Léeme.
Defecto: 2011 por mesa (CSV y ZIP) trae 17 municipios con la Ñ cambiada por «/» (PUERTO CARRE/O, NARI/O,
OCA/A…), 112.837 filas. Viene de DES_MM de la fuente; el Excel y el CSV por puesto de 2011 están bien.
