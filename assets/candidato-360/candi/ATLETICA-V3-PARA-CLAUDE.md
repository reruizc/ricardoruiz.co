# Candi atlética v3 — sustitución visual y nuevos clips

El usuario pidió corregir la mascota: Luna es más atlética, de patas largas y cuerpo esbelto. Nuevas fotos guiaron la revisión completa. Las versiones anteriores quedan como historial; no son la referencia anatómica vigente.

## Entregables vigentes

- `candi-3d-estados-atletica-v3.png`: nueva referencia de doce estados.
- `candi-storyboard-atletica-v3.png`: llegada → saludo → sentarse → atenta.
- `candi-saludo-atletica-v3.png` / `.webp`: atlas de 20 poses, 5 × 4.
- `candi-sentarse-atenta-v3.png` / `.webp`: atlas 4 × 4; posiciones 0–7 sentarse, 8–15 atenta/cola.
- `candi-atletica.js`: clase `CandiAtletica`, independiente del reproductor integrado v2.
- `demo-saludo.html`: demo actualizada, incluye botón «Solo atenta».
- `prompt-*-v3.txt`: prompts exactos utilizados con image_gen integrado.

Las imágenes son nuevas versiones, no reemplazos destructivos. Los WebP conservan transparencia y se sirven en la demo; los PNG son fuentes. El JS/CSS del chat y la página principal no se han modificado en esta revisión.

## Uso

Cargar `candi-saludo.css` (estilos geométricos existentes) y `candi-atletica.js`, luego:

```js
const mascota = new CandiAtletica(escena);
mascota.play().catch(fallarAtlas);
// Alternativa para revisar únicamente reposo:
// mascota.idle().catch(fallarAtlas);
```

Secuencia: `enter_greet` (0–3200 ms) → `sit_down` (3200–4800) → `idle_seated` (bucle de 4 s).

El bucle hace una pausa suave y recorre cola baja con índices `8,13,14,15,14,13,8,8`. Se omiten los barridos altos del atlas porque el usuario pidió movimiento leve. El último cuadro del saludo usa la pose 18 para mantener la pata levantada al enlazar con el primer cuadro de sentarse. El saludo aplica un recorte CSS de 1,5% para ocultar líneas residuales del borde de la cuadrícula generada.

Métodos: `play({speed,from})`, `idle({speed})`, `seek(ms)`, `pause()`, `destroy()`. `ready` resuelve cuando ambos atlas cargan. `seek(4800)` muestra reposo sin animarlo. `candi:frame` entrega `{time,frame,state}`; `candi:state` indica cada cambio de estado. `candi:complete` se emite UNA vez al entrar en reposo, no en cada vuelta del bucle. Con movimiento reducido muestra reposo estático; responde también si esa preferencia cambia durante la reproducción. Al ocultar la pestaña deja de avanzar; al destruirse cancela el bucle y listeners.

## Sustitución en la integración existente

Lee `INTEGRACION.md` y conserva la guía por vista, DeepSeek, privacidad y regla de saludo automático una vez por carga. Cambia la clase usada en `entrar()` y la carga del script con un nuevo `?v=`. No repitas el saludo al abrir/cerrar el panel. La mascota visible puede seguir atenta aunque el panel se cierre; pausa únicamente cuando se oculte/desmonte la mascota.

El globo actual escucha `candi:complete`, que ahora llega a los 4,8 s: ajustar el respaldo actual de 4,5 s o usar `candi:state` con `sit_down` si se quiere mostrar justo al acabar el saludo. No cambiar ese comportamiento accidentalmente.

Actualizar también `ATLAS` de `candidato-360-candi.js` y `.candi-cara`: las coordenadas de la v2 NO sirven para la nueva pose. Para una miniatura sentada usar atlas seated, índice8, grid4×4, background-size400%400%, posición0%66.6667%. Confirmar el encuadre de esa miniatura y bumpear los `?v=` del HTML.

No hace falta pedir estos estados a DeepSeek: son una secuencia visual local. No cambies el worker ni sus listas permitidas para esta sustitución. Si luego añades acciones solicitadas por el modelo, valida contra una lista explícita y respeta la regla de entrada.

## Límites conocidos

Animación por poses generadas, no rig 3D. Hay variaciones de pelaje, tamaño y alineación entre fotogramas y entre los dos atlas; el giro y el descenso aún pueden mostrar saltos. La cola se limita a un subconjunto de poses para reducir su amplitud. Es una versión funcional de revisión, pendiente de pulido para continuidad perfecta. Verificar fondos claro/oscuro, móvil, pausa, reducción de movimiento y evitar duplicar reproductores.

## Curiosa — añadida después de la entrega inicial de v3

Ya existe `candi-curiosa-atletica-v3.png` / `.webp`: 12 poses, cuadrícula 4 × 3, transparencia. La mascota está sentada, inclina la cabeza, sostiene brevemente la expresión y vuelve a neutral. Se conserva el estilo atlético; pequeñas variaciones entre atlas siguen pendientes de pulido.

`await mascota.curious({speed:1})` inicia la reacción de 2,8 segundos. La promesa resuelve al iniciar, no al finalizar. El atlas se carga bajo demanda, sin bloquear saludo/sentarse si falla. Un segundo disparo cancela la reproducción anterior. Al terminar emite `candi:reaction-complete` con `{state:'curious'}` y vuelve automáticamente a `idle_seated`; no repite el saludo. `candi:state` usa `curious` durante la reacción. `pause()` y `destroy()` también cancelan esta animación. Con movimiento reducido muestra reposo estático.

La demo incluye botón «Curiosa». Usar el script `candi-atletica.js?v=2` o una versión superior al integrar. Es apropiada al pedir una aclaración al usuario; no dispararla con cada letra o cada mensaje, ni interrumpir la entrada/sentarse. No añadir llamadas al modelo para decidir esta reacción local. Si el modelo solicita estados, mantener la validación explícita y coordinar cualquier cambio del worker por separado.

El prompt visual exacto se conserva en `prompt-curiosa-atletica-v3.txt`, generado con image_gen integrado.

## Pensando — 30 fotogramas con gafas y bombillo

Archivos `candi-pensando-atletica-v3.png` / `.webp`: 30 fotogramas en cuadrícula 6 × 5, orden por filas. La secuencia dura 6 segundos a velocidad normal (200 ms por pose): saca gafas, se las coloca, mira arriba, el bombillo se ilumina gradualmente, retira las gafas y vuelve al reposo. Son 30 poses, no 30 fps.

Se activa con `mascota.thinking({speed:1})`. Comparte la carga bajo demanda y cancelación de `curious()`. Emite `candi:state` con `thinking`, y al acabar `candi:reaction-complete` con `{state:'thinking'}` antes de volver a `idle_seated`. No emite un nuevo saludo. `pause()`, `destroy()`, pestaña oculta y movimiento reducido siguen respetándose. La promesa del método resuelve al comenzar; para detectar el final usar el evento.

La demo añade el botón «Pensando» y permite recorrer sus poses con el deslizador después de activarla. `reactionFrame('thinking',ms)` pinta una pose para revisión; llamar `pause()` antes de usarlo. El script de demo lleva `?v=3`; actualizar la versión usada por la integración al adoptar esta revisión.

El bombillo es una reacción visual: no representa verificación de datos ni certeza del modelo. El clip actual es de duración fija. No vincular su encendido a «respuesta recibida» sin coordinarlo con el estado real de la petición; tampoco repetirlo automáticamente mientras se espera, porque sacaría y guardaría las gafas en cada vuelta. Esta entrega no modifica el backend.

Como en los otros clips, los fotogramas generados pueden variar ligeramente en tamaño y expresión. Revisar a tamaño real de interfaz antes del despliegue. PNG fuente generado con image_gen integrado; WebP para reproducción. Prompt original y corrección de continuidad guardados en `prompt-pensando-atletica-v3.txt`.

Corrección de continuidad en el reproductor: los índices 20–23 del atlas aún pierden las gafas; durante esos cuatro intervalos se mantiene el índice19 (bombillo encendido con gafas). La secuencia conserva 30 intervalos y seis segundos, pero reutiliza esa pose para evitar parpadeos de las gafas.

Encuadre de pensando: la cuadrícula visual no registró filas uniformes. El reproductor usa inicios Y `[0,226,445,690,936]` y alturas `[226,219,245,246,209]` sobre un PNG de 1374 × 1145; conservarlos para evitar cortar patas y bombillo.
