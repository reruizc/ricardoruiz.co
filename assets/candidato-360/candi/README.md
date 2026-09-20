> **Versión vigente: v2 de 20 poses.** Abre `demo-saludo.html`. El reproductor y CSS usan `candi-saludo-atlas-v2-20.png` (1402 × 1122, transparente, cuadrícula 5 × 4). Duración: 3,2 s; ocho poses de caminata, cuatro de frenada/giro y ocho de elevación/saludo. Son veinte poses, no veinte fps. El clip de sentarse sigue pendiente. Las notas de v1 más abajo se conservan como historial y no describen el atlas vigente.
>
> **Para Claude:** copia el contenido de `PROMPT-PARA-CLAUDE.md`. Prompt visual exacto de la v2: `prompt-atlas-v2-20.txt`, generado con image_gen integrado.

# Candi — referencias y dirección de movimiento v1

Candi es Luna, la perrita del usuario, convertida en asistente de Candidato 360.
Estilo elegido por el usuario: **3D suave**. DeepSeek y la integración conversacional quedan a cargo de Claude.

## Archivos

- `candi-3d-estados-concepto-v1.png`: referencia de identidad y doce estados.
- `candi-llegada-saludo-sentarse-storyboard-v1.png`: diez poses clave para las dos primeras acciones.
- `prompt-storyboard-v1.txt`: prompt de generación, herramienta integrada image_gen.

Estas láminas son referencias estáticas de diseño. No son clips animados, sprites listos para reproducir, imágenes con transparencia ni un modelo 3D con rig. La animación continua y los assets finales todavía deben producirse.

## Identidad constante

Pelaje blanco y café, franja blanca asimétrica en la frente, pecas en el hocico, ojos cafés, orejas largas con flecos y pañuelo rojo con puntos blancos. Mantener las manchas en el mismo lado: no espejar imágenes para cambiar de dirección. Anatomía canina, sin manos humanas. Cámara y luz fijas; cuerpo completo sin cortar orejas, patas ni cola.

## 01 — Entrada y saludo (3,2 segundos propuestos, una vez)

Pensado para su ubicación en la esquina inferior derecha. Entra desde el borde derecho hacia la izquierda, hasta su punto de reposo.

| Tiempo | Acción |
| --- | --- |
| 0–1,1 s | Dos o tres pasos cortos. Orejas, cola y pañuelo acompañan con un pequeño retraso. Las patas apoyadas no resbalan. |
| 1,1–1,5 s | Desacelera, planta las patas y gira suavemente hacia el usuario. |
| 1,5–2,0 s | Transfiere el peso y levanta la pata delantera derecha; sigue de pie sobre las otras tres. |
| 2,0–2,8 s | Muestra las almohadillas y hace dos oscilaciones pequeñas de saludo. Cola alegre, sin agitar todo el cuerpo. |
| 2,8–3,2 s | Sostiene brevemente el saludo y prepara la bajada. |

## 02 — Sentarse (1,6 segundos propuestos, una vez)

Empieza exactamente en la pose final del saludo, sin salto de escala, posición o cámara.

| Tiempo local | Acción |
| --- | --- |
| 0–0,35 s | Baja la misma pata y vuelve a apoyar las cuatro. |
| 0,35–1,05 s | Flexiona las patas traseras y baja la cadera. Las delanteras quedan apoyadas. |
| 1,05–1,4 s | Acomoda el peso y recoge la cola junto al cuerpo. Orejas y pañuelo terminan de asentarse. |
| 1,4–1,6 s | Cierra suavemente la boca y queda atenta, sentada. |

## Reposo sentado

Pose habitual: último cuadro del storyboard. Respiración muy sutil; parpadeo breve cada 4–7 segundos con variación; movimiento ocasional de oreja o punta de la cola. Evitar un saludo repetido, jadeo permanente o balanceo de todo el personaje. La transición al reposo debe ser continua; los extremos de cualquier bucle deben coincidir.

## Entrega posterior para la interfaz

Secuencia prevista: `enter_greet → sit_down → idle_seated`. Cada clip termina antes de comenzar el siguiente. El saludo se reproduce al abrir el asistente, no con cada respuesta del modelo.

Producir fotogramas o clips con transparencia, cámara fija, misma escala y ancla de suelo. Propuesta inicial: lienzo de 512 × 512 por fotograma y prueba de lectura a 128–180 px. El recorrido horizontal puede controlarse en la interfaz, sincronizado con el ciclo de pasos. Separar ese recorrido del movimiento corporal. No convertir la lámina en un carrusel ni usar fundidos entre poses como sustituto de animación continua.

Con movimiento reducido, mostrar directamente la pose sentada. Pausar el reposo cuando el asistente o la pestaña no sean visibles. No hace falta un modelo 3D en tiempo real si se entregan clips prerenderizados con estas condiciones.

## Revisión pendiente antes de producir

El storyboard fija intención y poses, no fotogramas consecutivos. La frenada necesita posiciones intermedias y el descenso de cadera necesita mayor continuidad que la representada. Comprobar consistencia de manchas, longitud de orejas y volumen corporal, apoyos sin deslizamiento y transición sin salto entre clips. La producción animada todavía está pendiente.

## Prototipo reproducible — llegar y saludar

Ya existe una primera animación por poses en `demo-saludo.html`. Abrir directamente en un navegador o servir esta carpeta por HTTP. No requiere npm ni DeepSeek.

Archivos de integración:
- `candi-saludo-atlas-v1.png`: PNG RGBA de 1448 × 1086, cuadrícula 4 × 3; cada celda mide 362 × 362. Generado con image_gen integrado a partir de la referencia de doce estados.
- `candi-saludo.css`: tamaño, posicionamiento y recorte de la mascota.
- `candi-saludo.js`: reproductor independiente de 3,2 segundos. Repite las cuatro poses de caminata dos veces, gira y reproduce el saludo. El trayecto horizontal lo controla el reproductor.
- `demo-saludo.html`: reproducción, pausa, velocidad lenta, revisión con deslizador y fondos claro/oscuro.

Ejemplo (ajustar las rutas según la página):

```html
<link rel="stylesheet" href="assets/candidato-360/candi/candi-saludo.css">
<div id="candi" class="candi-stage"></div>
<script src="assets/candidato-360/candi/candi-saludo.js"></script>
<script>
  const host = document.querySelector('#candi');
  const mascota = new CandiSaludo(host);
  mascota.play().catch(console.error);
  // mascota.pause(); mascota.seek(2000); mascota.destroy();
  host.addEventListener('candi:complete', () => {
    // Conectar aquí sentarse cuando exista ese clip.
  });
</script>
```

`play({speed: 0.5})` reproduce lentamente. `ready` es una promesa de carga del atlas. `candi:frame` entrega `{time, frame}` (milisegundos e índice desde cero). Pausa el avance en pestañas ocultas; con movimiento reducido muestra directamente la última pose. El integrador debe llamar `pause()` cuando oculte su panel y `destroy()` al desmontarlo.

**Límite de esta versión:** es un prototipo de 12 poses, no una animación 3D continua. Hay variaciones de encuadre/anatomía entre poses generadas y saltos visibles en la caminata y giro. No contiene el clip de sentarse. No está integrado en la página principal. Antes de producción hay que pulir continuidad, apoyos y bordes y ampliar fotogramas o renderizar desde un rig consistente.

Dirección usada para generar el atlas: cuadrícula transparente de 4 × 3 sin texto, misma Candi 3D en doce poses de caminar a la izquierda, detenerse, mirar al usuario, levantar la pata delantera derecha y saludar, siempre de pie, con escala y suelo constantes.
