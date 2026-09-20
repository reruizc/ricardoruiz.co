# Candi · brief de diseño visual (para GPT Astra)

Candi es la asistente flotante de ricardoruiz.co: un Clippy, pero perrita.
En la vida real se llama **Luna**. La foto de referencia es `fuente/luna-01.webp`.

## Quién es

Perra mestiza colombiana, blanca con manchas **canela y marrón chocolate**,
orejas largas caídas (una marrón oscuro, otra canela), **ojos marrones grandes
y muy expresivos**, hocico blanco con pecas negras, nariz negra, pecho blanco
con pelo largo. Pañoleta oscura al cuello — **la pañoleta es su marca**, va en
todas las poses y es donde se puede meter un acento de color del sitio.

Tono: cercana y lista, nunca bufonesca. Acompaña a alguien que está trabajando
con datos electorales, no lo interrumpe para hacer gracias. La referencia no es
Clippy dando lata, es un perro que se sienta al lado del escritorio.

## Lo que se necesita

**Una sola imagen**: hoja de contactos de **4 columnas × 3 filas**, fondo
transparente, cada celda una pose completa de cuerpo entero o medio cuerpo,
todas con la MISMA identidad, el mismo grosor de línea y la misma paleta.

> Pedirlo como una sola hoja y no como 12 imágenes sueltas es deliberado: al
> generarlas por separado la identidad se va (cambia el pelo, las manchas, el
> largo de la oreja) y no hay forma de arreglarlo después. Las 12 en una pasada
> comparten el mismo trazo. Del recorte nos encargamos nosotros.

| # | Estado | Qué debe leerse en un vistazo |
|---|---|---|
| 1 | **reposo** | sentada, tranquila, mirando al frente. Es la que más se ve |
| 2 | **saludo** | pata levantada, orejas arriba, aparece por primera vez |
| 3 | **atenta** | cabeza ladeada, orejas alerta — el usuario está escribiendo |
| 4 | **pensando** | mirando arriba, pata en el hocico — esperando la respuesta |
| 5 | **hablando** | boca abierta, gesto de estar contando algo |
| 6 | **idea** | ojos muy abiertos, orejas disparadas: encontró algo |
| 7 | **alerta** | ceño, orejas atrás, seria — un dato que hay que mirar dos veces |
| 8 | **celebrando** | salto o cola en movimiento: salió bien |
| 9 | **confundida** | cabeza muy ladeada, una oreja arriba: no entendió |
| 10 | **dormida** | enroscada, ojos cerrados — inactividad larga |
| 11 | **cargando** | trotando de perfil, para el estado de espera largo |
| 12 | **despidiéndose** | de espaldas mirando por encima del hombro |

## Estilo

- **Ilustración vectorial plana**, contorno limpio, sombreado mínimo. Nada de
  foto-realismo ni 3D: tiene que leerse nítida a 64 px y no pelear con la
  página. Sin sombra proyectada (la pone el CSS).
- Paleta de la perra: blanco hueso, canela `#c8955f`, chocolate `#5b3a24`,
  nariz `#1a1510`, ojos marrón ámbar. La pañoleta puede ir en azul `#0047FF`
  (el azul del sitio).
- **Cada celda centrada y con aire alrededor**, sin tocar los bordes, sin texto,
  sin números, sin marco. Fondo transparente de verdad (PNG con alfa), no blanco.
- Canvas grande: **4096×3072** (cada celda 1024×1024).

## Entrega

`candi/fuente/candi-hoja.png`. Nosotros recortamos, normalizamos a 512×512 y
convertimos a WebP con alfa (una pose ronda los 20-40 KB así; en PNG se va a
300 KB y son doce).

⚠️ No hace falta que genere los archivos sueltos ni que optimice nada: la hoja
en máxima calidad y ya.
