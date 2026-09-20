# Integrar Candi en Candidato 360

Empieza a integrar a Candi, mi asistente perrita, en `candidato-360.html`. El diseño elegido es 3D suave, basado en Luna. Los archivos están en `assets/candidato-360/candi/`. Lee primero las instrucciones del repositorio y revisa la arquitectura actual para integrarla sin interferir con el CRM.

## Archivos que debes usar

- `candi-saludo-atlas-v2-20.png`: versión vigente, PNG transparente con 20 poses en una cuadrícula de 5 columnas × 4 filas, orden de izquierda a derecha y de arriba abajo. Dimensiones totales: 1402 × 1122 px; las celdas son fraccionarias (280,4 × 280,5), por lo que el reproductor usa posiciones porcentuales. No asumir celdas enteras de 362 px: eso era la v1. El atlas generado no registra perfectamente las filas: el reproductor compensa con orígenes Y `[0, 280.5, 550, 813]` y fondo `500% auto`. Conserva esta corrección para no cortar las cabezas de la última fila.
- `candi-saludo.js` y `candi-saludo.css`: reproductor sin dependencias de 3,2 segundos, ya actualizado al atlas de 20 poses.
- `demo-saludo.html`: ejemplo ejecutable con reproducción, pausa, velocidad lenta, deslizador y fondo claro/oscuro.
- `candi-3d-estados-concepto-v1.png`: referencia de identidad y expresiones; no es un atlas de animación.
- `candi-llegada-saludo-sentarse-storyboard-v1.png`: referencia de las transiciones futuras; tampoco es un atlas reproducible.

## Comportamiento que quiero

1. Candi aparece en la esquina inferior derecha dentro de un contenedor compacto. Entra desde la derecha, se detiene, mira al usuario y alza su pata para saludar. Reproducir una vez por apertura del asistente; no repetir con cada respuesta, renderizado del CRM o cambio de pestaña interna.
2. Añade controles accesibles de abrir/minimizar y un panel de conversación acorde con la identidad de Candidato 360. La mascota y el panel no deben tapar acciones importantes, especialmente en móvil. El área transparente no debe interceptar clics del CRM.
3. Usa `new CandiSaludo(host)` y `play().catch(...)`. Espera `ready` si necesitas mostrar un estado de carga. Escucha `candi:complete` para encadenar acciones futuras. Al ocultar el asistente llama `pause()`; al desmontarlo, `destroy()`. Evita crear varias instancias y listeners duplicados.
4. El atlas termina de pie con la pata levantada. **El clip de sentarse y el reposo sentado aún no existen.** Mantén temporalmente la pose final sin bucle y deja preparada la transición futura `enter_greet → sit_down → idle_seated`; no anuncies esos estados como implementados ni recortes el storyboard para fingir el clip.
5. Respeta `prefers-reduced-motion`: el reproductor muestra la pose final directamente. Conserva la pausa del avance en pestañas ocultas. La mascota es decorativa; la información del chat debe seguir disponible como texto accesible.
6. Conecta DeepSeek mediante la arquitectura de backend existente. Reutiliza autenticación y endpoints si existen. Nunca pongas claves en el frontend. Si falta el endpoint o las credenciales, deja la interfaz funcionando y documenta exactamente qué falta; no simules respuestas atribuidas a DeepSeek. Mantén el estado de animación separado de la respuesta textual y valida cualquier estado solicitado por el modelo contra una lista permitida.

## Calidad y alcance

Es un prototipo de animación por 20 poses, no un modelo 3D ni 20 fps. Aún hay variaciones entre poses. No uses interpolación CSS de `background-position`, porque recorrería fragmentos de otras celdas; el cambio de pose debe ser discreto. La traslación horizontal sí es continua. El renderizado actual selecciona el atlas con porcentajes.

Conserva la v1 como referencia. Usa rutas versionadas en CSS/JS si es la convención del proyecto. No añadas librerías pesadas para esta reproducción. No despliegues ni modifiques infraestructura sin la autorización correspondiente.

Verifica escritorio y móvil, entrada/saludo completo, apertura repetida sin duplicaciones, minimizar durante reproducción, movimiento reducido, recuperación al volver a la pestaña, error de carga de imagen y navegación por teclado. Revisa transparencia sobre fondos claro y oscuro. Entrega resumen de lo integrado, archivos modificados, comprobaciones realizadas y pendientes concretos.
