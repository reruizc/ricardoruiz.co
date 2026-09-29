# Integrar Candi investigando y recorridos alternados

Los assets y reproductores están preparados en esta carpeta; la integración principal todavía necesita estos ajustes. Mantener DeepSeek, autenticación y el chat existentes.

## Investigando

- `candi-investigando-atletica-v3.webp` para servir; PNG original y prompt junto a él.
- Atlas 6 columnas × 4 filas, 24 poses, 200 ms por pose, duración 4,8 s.
- `await mascota.investigating()` carga bajo demanda y comienza la reacción. Su promesa no espera al final.
- Candi toma una lupa, examina y vuelve a atenta. Evento `candi:reaction-complete` con `detail.state === 'investigating'` al terminar.
- Usar para una consulta o revisión real de datos; conservar pensando para la espera habitual. No disparar ambas a la vez. Si termina antes la consulta, `mascota.idle()` cancela la reacción. No repetir la animación completa indefinidamente.
- Respeta movimiento reducido y pausa en pestaña oculta. Probar con el botón Investigando de `demo-saludo.html`.

## Hueso al extremo contrario

Conservar `DESCANSO_MS = 20000`. El reproductor ahora guarda `side`, `fromSide`, `toSide` y rearma la misma espera al acabar echada. Alterna derecha → izquierda → derecha, con el hueso en el destino. La demo usa 20 segundos al activar su casilla.

Adaptar `candidato-360-candi.js` antes de actualizar sus scripts:

1. Su override de `descanso.layout()` actualmente fuerza el inicio a la posición del dock. Usar la posición de la mascota visible (incluido `rincon`) como inicio y calcular el destino en el extremo opuesto. Respetar `fromSide` y `toSide`; no forzar siempre el extremo izquierdo.
2. Quitar la rama `junto` de `alDescanso` que salta directamente a `descanso.render(descanso.times.walk)` cuando Candi está a la izquierda. Ahora debe caminar a la derecha.
3. Coordinar `despertarDonde`, `quitarRincon` y la restauración del sprite para que solo haya una Candi visible. El reproductor independiente restaura su sprite en el último lado completado; el adaptador debe aplicar la posición en su franja, sin desplazar incorrectamente el sprite dentro del dock.
4. Chat abierto, interacción, investigación o pensando deben cancelar/inhibir descanso; al volver a atenta empezar una espera completa. Evitar dos temporizadores independientes.
5. Bump de scripts al integrar: `candi-atletica.js?v=4`, `candi-hueso.js?v=2` y la versión del adaptador en las páginas candidato-360 que los consumen.

Verificar dos viajes consecutivos sin actividad, despertar a ambos lados, abrir chat durante el viaje, redimensionar/girar móvil y movimiento reducido. El test `node assets/candidato-360/candi/test-hueso.cjs` cubre límites en siete anchos, ambos sentidos, alternancia automática y cancelaciones.

Limitaciones visuales: el viaje hacia la derecha refleja los sprites existentes (también sus manchas). Se reutiliza el inicio de caminar para levantarse; no hay todavía un clip dedicado para levantarse desde echada. Son poses generadas, con pequeñas variaciones entre fotogramas.
