# Candi, integrada en Candidato 360 — estado al 20-sep-2026

Lo que sigue describe **lo que ya está en la página**. El brief de diseño y los
límites del atlas viven en `README.md` y `PROMPT-PARA-CLAUDE.md`; esto es el
lado del producto.

## Qué es Candi acá

Una **guía de la plataforma**, no un chat de datos electorales. Sabe en qué
pantalla está el usuario y explica qué es esa pantalla y qué hacer en ella. Las
cifras de la campaña (meta, votos, territorio) las pinta el CRM; Candi no las
calcula ni las inventa.

## Archivos

| Archivo | Qué hace |
|---|---|
| `candi-saludo-atlas-v2-20.webp` · `candi-saludo.js` · `candi-saludo.css` | el reproductor de 20 poses de Astra. Solo se le cambió **la línea del atlas**: sirve el WebP |
| `candi-saludo-atlas-v2-20.png` | la fuente del atlas. **No se sirve**: queda para regenerar el WebP |
| `candidato-360-candi.js` (raíz) | el asistente: dock, panel, guía por vista, preguntas al worker |
| `candidato-360-candi.css` (raíz) | sus estilos y el ajuste del escenario al dock |
| `tools/candidato-360/prueba-candi.mjs` | lo que no puede romperse en silencio |
| `rr-auth/src/index.js` → `c360Candi` | `POST /c360/candi`, el cerebro por DeepSeek |

⚠️ Al tocar el `.js` o el `.css` hay que **bumpear su `?v=`** en
`candidato-360.html`, o el navegador sirve la copia vieja sin dar ningún error
(mismo aviso que ya traía `candidato-360.js`).

## Las dos capas, y por qué están separadas

1. **La guía** (`VISTAS` en `candidato-360-candi.js`) es texto nuestro, una
   entrada por pantalla. Está **siempre**: sin sesión, sin red, sin modelo y sin
   el atlas. Es la versión accesible de lo que la mascota representa.
2. **Las preguntas escritas** van a `POST /c360/candi` (**desplegada el
   20-sep-2026**; sin sesión responde 401). Piden sesión: el modelo cuesta y la
   cuota es por cuenta, 40 al día. Si falta la sesión, la clave o la ruta, Candi
   **dice cuál de las tres falta**; nunca rellena el hueco con una respuesta
   inventada y atribuida al modelo.

## La regla del saludo

Candi **entra sola al cargar la página**, una vez: camina, saluda, se presenta
en un globo y se queda quieta en su pose final. Abrir el panel **ya no la hace
caminar otra vez** —ya está ahí— y tampoco lo hacen una respuesta, un repintado
del CRM ni un cambio de pantalla interna. El globo se quita solo a los 12 s, o
al tocarlo (abre el panel) o al cerrarlo con la ×.

⚠️ **`cerrar()` NO llama `pause()`.** Antes sí, porque la mascota solo existía
con el panel abierto; ahora vive en la pantalla y pausar ahí congelaba la
entrada a mitad de camino si alguien abría y cerraba el panel mientras caminaba.
El reproductor ya deja de avanzar cuando la pestaña se oculta, y `destroy()`
sigue en `pagehide`.

## El nombre y la voz

Saluda por el **primer nombre** cuando lo sabe: lo busca en la candidatura
abierta, en el wizard o en el vínculo de la cuenta, y lo pasa por
`NOMBRE_BONITO` porque el índice electoral lo guarda en MAYÚSCULAS. Sin nombre,
saluda sin nombre.

⚠️ **Ese nombre NO viaja al modelo**: el saludo se arma en el navegador. El
prompt incluso le prohíbe saludar por el nombre, porque no lo recibe y se lo
inventaría. Si algún día se quiere que lo use en la conversación, hay que
mandarlo en el contexto a propósito.

Candi **habla de tú**. El resto del producto habla de usted y así se queda: esa
es la voz seria de la plataforma y ella es la voz cercana. El prompt se lo dice
explícito para que no se contagie de los textos que le llegan en el contexto.

⚠️ Al cambiar el prompt hay que **subir `C360_CANDI_PROMPT_V`** (hoy `v2`), que
entra al hash de la caché: si no, durante seis horas se siguen sirviendo las
respuestas viejas. El paso de usted a tú fue exactamente ese caso.

## Lo que todavía no existe

## Lo que todavía no existe

`sit_down` e `idle_seated` están en el storyboard, **no como clip**. La
secuencia prevista sigue siendo `enter_greet → sit_down → idle_seated`, y la
animación termina de pie con la pata levantada, sin bucle.

La lista permitida de estados vive **en los dos lados** (`ESTADOS` en el
frontend, `C360_CANDI_ESTADOS` en el worker) y hoy solo contiene `saludo`. El
modelo puede pedir un estado; el worker descarta lo que no esté en su lista y el
frontend ignora `saludo` porque la regla de «una vez por apertura» manda sobre
lo que pida un texto generado. Cuando existan los clips, agregarlos a las dos
listas y quitarles `soloAlAbrir`.

## Peso

⚠️ El atlas se baja en **cada carga de candidato-360**, porque el botón de Candi
usa su pose final recortada. En PNG eran **2,0 MB**; en WebP son **561 KB**
(3,6× menos) y la diferencia, medida a tamaño de pantalla, es de 3,8/255 por
píxel: invisible. Para regenerarlo desde el PNG:

```bash
cwebp -q 90 -alpha_q 100 -m 6 candi-saludo-atlas-v2-20.png -o candi-saludo-atlas-v2-20.webp
```

Si Astra entrega un atlas nuevo, entrega el PNG: **hay que volver a convertirlo**
y subir el `?v=` de `candi-saludo.js` en `candidato-360.html` y en la demo.

## Privacidad

El contexto que viaja al modelo es: la pantalla, la línea de campaña **tal como
la muestra el encabezado del CRM**, la meta en pantalla, el paso del formulario
y si está en vitrina. **El nombre de la persona no se manda**: para guiar la
página no hace falta. Está probado en `prueba-candi.mjs`.
