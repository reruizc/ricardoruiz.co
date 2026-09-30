# Luna cumpleaños · entrega v1

Generado con image_gen integrado. Todos los archivos están en esta carpeta. PNG originales conservados sin retoques; WebP convertidos con `cwebp -q 90 -alpha_q 100 -m 6`. Prompts finales en `prompt-{llegada,fiesta,celebra}-v1.txt`. No se modificaron cumple.html ni los assets originales de Candi.

## Archivos y tiempos propuestos

Poses numeradas desde 1, de izquierda a derecha y de arriba abajo. En JavaScript restar 1 para índices desde cero.

| Atlas (PNG + WebP) | Columnas × filas | Poses | ms por pose | Bucle | Final |
| --- | --- | --- | --- | --- | --- |
| luna-cumple-llegada-v1 | 5 × 4 | 20 | 160 | 1–10 solo mientras se desplaza; luego 11–20 una vez | 20, saludo con sobre abajo |
| luna-cumple-fiesta-v1 | 4 × 4 | 16 | 275 en 1–8; 200 en 9–16 | 1–8; insertar 9–16 ocasionalmente y volver a 1 | 16 → 1 |
| luna-cumple-celebra-v1 | 6 × 4 | 24 | 200 | Sin bucle, ejecutar una vez | 24 → fiesta 1 |

Llegada sin repetir trote: 3.200 ms. Fiesta reposo: 2.200 ms; soplido: 1.600 ms; secuencia completa: 3.800 ms. Celebra: 4.800 ms.

## Verificación y pendientes reales antes de producción

**La entrega conserva limitaciones del generador; no está validada como animación lista para producción.**

- Llegada: PNG RGBA 1402 × 1122; WebP 473.582 bytes. Se corrigieron dirección del trote y reparto 5 × 4. La celda nominal mide 280,4 × 280,5 px: usar coordenadas proporcionales o normalizar el atlas antes de asumir celdas enteras.
- Fiesta: PNG RGBA 1254 × 1254; WebP 446.158 bytes. Cuadrícula 4 × 4; celda nominal 313,5 × 313,5 px. Alfa con extremos 0–255, igual que llegada.
- Celebra: PNG RGBA 1536 × 1024; WebP 399.086 bytes. Cuadrícula 6 × 4 con celdas de 256 px. **Conserva un fondo marrón visible aunque el archivo tenga canal alfa (extremos 0–254). Tener RGBA no prueba transparencia correcta.** Se intentó regenerar y retirar el fondo con image_gen varias veces sin resolverlo. No superponer este atlas en producción hasta eliminar el fondo o regenerarlo. La urna sí está presente en las 24 poses de la versión guardada.
- El margen central del 76%, la línea de patas al 86%, la escala constante y la posición fija de los objetos no se cumplen con precisión de píxel. Hay variaciones de encuadre entre poses; requieren registro/alineación antes de una reproducción fluida. No se aplicó espejado ni recorte automático que pudiera alterar manchas o cortar figuras.
- Celebra adelanta la inserción del tarjetón respecto al guion; los tiempos anteriores son una propuesta de reproducción, no una certificación del reparto exacto de acciones. El empalme celebra 24 → fiesta 1 no es idéntico: cambian posición/escala y desaparece la urna. Ajustar transición después de corregir el atlas.
- No se ejecutó QA en el reproductor de cumple.html. Los originales se entregan para revisión de Claude, con las limitaciones explícitas, sin sustituir silenciosamente el marcador de posición.
