# Luna · cumpleaños de Ricardo (encargo para Astra)

## Dónde dejar los archivos

Todo va en esta carpeta del repo:

    /Users/ricardoruiz/ricardoruiz.co/assets/cumple-2026/luna/

- PNG original de cada atlas: `luna-cumple-{llegada,fiesta,celebra}-v1.png`
- La misma imagen en WebP para servir (`cwebp -q 90 -alpha_q 100 -m 6`):
  `luna-cumple-{llegada,fiesta,celebra}-v1.webp`
- El prompt usado para cada atlas: `prompt-{llegada,fiesta,celebra}-v1.txt`
- Una nota `CUMPLE-PARA-CLAUDE.md` con, por cada atlas: columnas × filas,
  cuántas poses trae, milisegundos por pose, cuáles poses hacen bucle y
  en qué pose termina.

La página que la usa es `cumple.html` (raíz del repo). Hoy muestra la
Candi atlética v3 de `assets/candidato-360/candi/` como marcador de posición.
No modifiques esos archivos: el cumpleaños va aparte.

## Base común de los tres atlas

Luna es la MISMA perrita atlética adulta de la referencia (Candi atlética v3):
patas largas y delgadas, torso angosto, hocico adulto natural, ojos cafés,
mancha blanca asimétrica en la frente, hocico con pecas, pelaje castaño y
blanco, orejas con flecos. Render 3D suave, sin proporciones de cachorro.
Para esta ocasión cambia la pañoleta roja de puntos por un GORRO DE FIESTA
cónico pequeño, dorado (#ffc145) con rayas rosadas (#ff5d8f) y un pompón
blanco, sujeto con elástico. El gorro debe verse igual en todas las poses.

Canal alfa transparente de verdad. Sin texto, bordes, líneas de cuadrícula,
sombras, escenario ni piso. Cuadrícula uniforme, cámara fija, la perrita a
la misma escala en todas las celdas, figura completa (con gorro y cola)
dentro del 76 % central de cada celda con 12 % de margen. Las patas siempre
sobre la misma línea, al 86 % del alto de la celda. Se leen de izquierda a
derecha y de arriba abajo. Sin cuadros espejados: las manchas del pelaje
deben ser consistentes. No mover a la perrita horizontalmente entre celdas:
el desplazamiento lo pone el código.

## 1 · LLEGADA (entra con la invitación) · 20 poses, 5 × 4

Luna entra trotando de derecha a izquierda, en tres cuartos mirando a la
IZQUIERDA del espectador, con un SOBRE blanco de invitación en la boca
(sobre rectangular con solapa y un sello rosado redondo).
Poses 1-10: ciclo de trote con el sobre en la boca.
Poses 11-14: frena, planta las cuatro patas y gira de frente al espectador.
Poses 15-17: baja la cabeza y suelta el sobre en el piso frente a ella.
Poses 18-20: levanta la cabeza, mira al espectador y saluda levantando
una pata delantera. El sobre queda en el piso sin cambiar de lugar. Nunca
se duplica ni desaparece antes de soltarlo.

## 2 · FIESTA (reposo en bucle) · 16 poses, 4 × 4

Luna sentada, de frente al espectador, con el gorro de fiesta.
Poses 1-8: reposo atento, la cola se mueve suave de lado a lado (debe cerrar
en bucle: la pose 8 empalma con la 1).
Poses 9-16: sopla un espanta suegras de papel (rosado y dorado) que sostiene
en la boca: se desenrolla en las poses 9-12 y se recoge en las 13-16. Al
final no queda nada en la boca y vuelve a la pose 1.

## 3 · CELEBRA (cuando alguien confirma) · 24 poses, 6 × 4

Luna de frente, junto a una pequeña URNA de votación de cartón blanco con
ranura arriba y un moño de regalo rosado (la urna fija a su derecha, a la
izquierda del espectador, siempre en el mismo lugar).
Poses 1-4: sentada, mira la urna.
Poses 5-10: con el hocico empuja un tarjetón doblado dentro de la ranura
hasta que desaparece.
Poses 11-18: celebra: salta en su sitio y da un giro completo, orejas al
aire, cola moviéndose rápido.
Poses 19-24: aterriza y se sienta de frente, contenta, con la boca abierta.
La última pose debe calzar con la pose 1 de FIESTA para volver al reposo sin salto.

## Tiempos sugeridos

Llegada ~3,2 s · fiesta 8 poses de cola a ~275 ms y el soplido a ~200 ms ·
celebra ~4,8 s (200 ms por pose). Que respete el mismo encuadre de la
Candi atlética v3 para poder reutilizar su reproductor.
