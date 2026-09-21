# Candi — secuencia de inactividad con hueso rosado

Revisión del 21-sep-2026. La demo está en `demo-hueso.html`. El usuario pidió que Candi fuera al otro extremo de la pantalla, recogiera un hueso rosado de goma con la boca y se echara, en unos 70 fotogramas. Esta entrega añade exactamente 70 poses fuente en tres bloques y un juguete independiente.

## Archivos

| Fuente PNG / reproducción WebP | Poses | Cuadrícula |
| --- | --- | --- |
| `candi-hueso-caminar-v1` | 24 | 6 × 4 |
| `candi-hueso-recoger-v1` | 24 | 6 × 4 |
| `candi-hueso-echarse-v1` | 22 | 6 × 4, dos celdas finales vacías |
| `candi-hueso-rosado-v1` | hueso independiente | imagen única |

Los PNG conservan los originales de image_gen integrado. WebP con alfa para servir. Prompts en `prompt-hueso-v1.txt`. `candi-hueso-registro.json` guarda los límites de filas y apoyo en el suelo medidos a partir del alfa: estos datos también están embebidos en el reproductor, sin petición extra de red. No usar un recorte uniforme para echarse: cortaría las patas en las primeras filas.

## Funcionamiento

`candi-hueso.js` expone `CandiBoneSequence`; usa también `candi-hueso.css`.

```js
const descanso = new CandiBoneSequence(escenarioAncho, {
  mascot: mascotaAtletica,
  inactivityMs: 45000,
  activityTarget: document
});
// Activar una vez que la mascota esté montada:
descanso.enable(true);
// Para previsualizar manualmente:
// descanso.play().catch(mostrarError);
// Al desmontar: descanso.destroy();
```

- **El escenario debe abarcar el ancho disponible**, no el dock estrecho de la mascota. En la página principal se puede usar una franja fija inferior con `left:0; right:0`, altura suficiente para la mascota y `pointer-events:none`, respetando el área segura y controles inferiores del sitio. No colocar una capa opaca encima del CRM.
- Mide `host.clientWidth`. Candi comienza dentro del borde derecho, el hueso dentro del izquierdo. Tamaño de mascota entre unos 100–210 px según ancho; no se espejan las manchas de la perrita.
- Los primeros ocho fotogramas la levantan y orientan; el ciclo de caminar se repite según distancia. Los últimos cuatro detienen los pasos. **70 poses fuente no significa 70 cuadros reproducidos exactamente:** un escritorio ancho requiere repetir pasos; en celular el recorrido dura menos.
- El hueso independiente se muestra durante la caminata. Al empezar a recogerlo, se oculta y aparece el que ya forma parte del atlas, evitando duplicarlo cuando entra a la boca.
- Luego se echa con el juguete entre las patas y permanece en la última pose, sin gastar un bucle de reproducción indefinido.
- El recorrido se adapta con `ResizeObserver` si cambia el ancho o gira el teléfono. Se conserva el progreso del movimiento.

## Inactividad y cancelación

La espera es configurable, 45 s por defecto. La demo la activa con una casilla; no se activa silenciosamente al abrir la demo. `enable(true)` la activa en el producto. Solo comienza automáticamente si `mascot.phase === 'idle_seated'`, la pestaña está visible y no se pidió movimiento reducido. Los cuatro recursos se cargan bajo demanda.

La actividad de puntero, teclado, entrada de texto o rueda reinicia la espera; si la secuencia está activa, vuelve a atenta. La reacción de «despertar» **es inmediata**, no hay aún un clip de levantarse y regresar desde el lado izquierdo. Es un límite explícito de esta entrega. La franja no captura clics.

El atributo `data-candi-bone-controls` excluye los controles de revisión de la demo de la detección de actividad, para poder pausar, mover el deslizador o cambiar ancho sin abortar la prueba. No aplicarlo al CRM ni al chat en producción.

Al ocultar la pestaña se pausa el avance y se cancela el temporizador pendiente. Al volver empieza una espera nueva si no estaba reproduciendo. `pause()` invalida también una carga pendiente. `destroy()` cancela temporizadores, frames y listeners, desconecta el observer y restaura la mascota original.

## API y eventos

- `enable(boolean)`, `play()`, `pause()`, `wake()`, `destroy()`.
- `render(ms)` para revisión de poses después de cargar; pausar primero.
- `candi:bone-state`: `{state: 'walk' | 'pickup' | 'lie' | 'resting' | 'awake'}`.
- `candi:bone-frame`: `{time,duration,clip,frame,x,size,width}`.
- `candi:bone-complete`: una vez al quedar echada.
- `candi:bone-error`: error en una carga automática.

`play()` resuelve cuando comienza, no al finalizar. Capturar su error en activaciones manuales. Esta animación es local: no necesita solicitudes a DeepSeek ni cambios del worker.

## Alcance

No se modificó la integración principal del CRM. Para adoptarlo, conservar su política de saludo, chat, autenticación y privacidad, y actualizar las versiones de scripts/estilos que se añadan. Evitar dos instancias de la mascota visibles a la vez: el módulo oculta temporalmente `mascot.sprite`.

Es un prototipo por poses generadas. Hay cambios pequeños de silueta y posición entre bloques, y el hueso independiente puede diferir levemente del dibujado en las poses. El ajuste de alfa mantiene el apoyo en el suelo; una animación con rig tendría mayor continuidad. No es una simulación física ni vídeo continuo.

## Verificación realizada

`node assets/candidato-360/candi/test-hueso.cjs` comprueba límites a 280, 320, 360, 390, 768, 1440 y 2560 px; fin en reposo sin bucle; pausa en pestaña oculta; despertar por actividad; ciclo del temporizador; movimiento reducido y cancelación durante carga. También se revisó visualmente la demo en viewport de 390 px y en ancho de escritorio, con fondos claro y oscuro.

El bloque recoger aplica `clip-path: inset(0 1% 0 7%)` para ocultar un resto de cola de la celda anterior en el borde izquierdo del atlas. Mantener ese recorte junto al registro vertical; no se modificaron los píxeles fuente.
