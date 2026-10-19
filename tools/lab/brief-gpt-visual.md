# Brief para GPT · pulido visual del Lab de Políticas Públicas

> Pégale a GPT (o a Grok) este archivo completo. Le pide **transiciones, estados y
> detalles visuales** que mejoren la sensación del Lab sin tocar la lógica. Está
> escrito para que lo que devuelva se pueda pegar casi tal cual en los 8 HTML.
> Lo que NO es negociable está marcado con ⚠️. Fecha: 18-oct-2026.

## 1. Qué es esto y qué tiene que devolver

El Lab son 8 páginas HTML independientes (sin framework, sin build) que comparten
un chasis: `analisis-estructural.html` (hub + módulo 1), `problema-publico.html`,
`mactor.html`, `evaluacion.html`, `alternativas.html`, `ain.html`,
`prospect-escenarios.html`, `comunicar.html`. Cada módulo es un flujo de 5 a 9
pasos («stages») que se muestran y ocultan con `classList.toggle('is-hidden')`.
Hoy el cambio de paso es un corte seco: desaparece una sección y aparece otra, y
la página hace `window.scrollTo({top:0, behavior:'smooth'})`.

**Lo que esperamos de ti:** un paquete de CSS (+ el JS mínimo si hace falta,
vanilla) con:

1. Transición entre pasos (entrada/salida de `section[id^="stage-"]`).
2. Microinteracciones en los controles que más se repiten (lista en §4).
3. Estados vacíos («aún no agregaste…») y de carga (copiloto IA, 10-25 s)
   que se sientan diseñados, no provisionales.
4. Una propuesta para que el **hub** (la grilla de 8 tarjetas) se lea como un
   recorrido y no como un catálogo: orden, jerarquía, conectores entre tarjetas.
5. Una propuesta de **barra de progreso del módulo** persistente y uniforme (seis
   módulos tienen pastillas `.step-pill`; MicMac y Mactor no, y el estilo varía).

Entrega: un solo bloque `<style>` por tema (puede ir en un `lab-motion.css`
compartido) + snippets de HTML/JS mínimos con el `id`/clase exacta que tocan +
una línea por decisión explicando por qué. Sin librerías. Sin Tailwind. Sin
frameworks de animación.

## 2. ⚠️ Lo que no se puede cambiar

- **Paleta y tipografía existentes.** Todo va por variables CSS que ya están en
  `:root` (ver §3). Nada de colores nuevos en hex: si necesitas un tono, derívalo
  con `color-mix()` desde las variables.
- **Cursor custom.** `body{cursor:none}` y dos divs `#cursor` / `#cursorRing` que
  siguen al mouse. Cualquier overlay nuevo debe tener `z-index` **menor a 99999**
  y, si tiene botón de cerrar, al cerrarse debe resetear el estilo del cursor
  (patrón ya documentado en el proyecto). Los elementos interactivos nuevos
  llevan `cursor:none`, no `pointer`.
- **Modo día/noche.** Existe `body.day-mode` que redefine las mismas variables.
  Todo lo que propongas tiene que verse bien en los dos sin reglas duplicadas:
  usa las variables, no valores absolutos.
- **Sin `requestAnimationFrame` para nada que deba verse al volver a una pestaña
  en segundo plano** (se congela). Transiciones en CSS; si hay JS, `setTimeout`.
- **Respetar `prefers-reduced-motion: reduce`**: con esa preferencia, todo lo que
  propongas se apaga (duración 0 o `animation:none`).
- **Nada que mueva el layout mientras el usuario escribe** (los formularios
  guardan en `localStorage` en cada tecla y se re-renderizan).
- **Accesibilidad mínima:** foco visible (`:focus-visible`) en todo botón y
  campo; el contraste del texto secundario no puede bajar de lo actual
  (`--ink-2` sobre `--paper`).
- Los `id` y las clases que ya existen no se renombran: hay JS que los usa.

## 3. Tokens que ya existen (cópialos, no los reinventes)

```css
:root {
  --paper:#1a1610; --paper-2:#221d15; --paper-3:#2a241b;
  --ink:#f4f3ef; --ink-2:#b8b1a0; --ink-3:#807a6c;
  --rule:#f4f3ef1c; --rule-strong:#f4f3ef38;
  --accent:#d96a50; --accent-2:#e08266; --accent-soft:#d96a5018; --accent-tint:#d96a5036;
  --gold:#d6a83a; --green:#6fa07a; --amber:#d6a83a; --danger:#d96a50; --on-accent:#14110a;
  --sans:'Familjen Grotesk',system-ui,sans-serif;   /* texto y títulos */
  --italic:'Petrona',Georgia,serif;                 /* énfasis, ayudas, citas */
  --mono:'Space Mono',ui-monospace,monospace;       /* etiquetas, kickers, cifras */
  --display:'Syne',sans-serif;                      /* SOLO el logo */
}
body.day-mode { --paper:#f4f3ef; --paper-2:#ecebe5; --paper-3:#e0ddd2; --ink:#14110a;
  --ink-2:#5a5448; --ink-3:#948e80; --rule:#14110a1f; --rule-strong:#14110a40;
  --accent:#8a1e16; --accent-2:#a02a20; --accent-soft:#8a1e161a; --accent-tint:#8a1e1633;
  --gold:#8a6a1a; --green:#2f6b3f; --amber:#8a6a1a; --danger:#b03524; --on-accent:#f4f3ef; }
```

Carácter visual: papel oscuro cálido, salmón como único acento, esquinas
rectas (no hay `border-radius` en tarjetas ni botones), bordes de 1 px, kickers
en mono mayúscula con tracking amplio, serif itálica para las ayudas. Piensa en
un cuaderno técnico, no en un SaaS azul. Las animaciones deben sentirse
**editoriales**: cortas (150-320 ms), con `ease-out` para entradas y
`ease-in` para salidas, desplazamientos de 6-12 px, nunca rebotes.

## 4. Elementos que se repiten en los 8 módulos (los que vale la pena animar)

| Elemento | Selector / patrón | Qué pasa hoy | Qué queremos |
|---|---|---|---|
| Cambio de paso | `section[id^="stage-"]` + clase `.is-hidden` | corte seco + scroll al tope | fade + 8 px de subida en la entrada; la salida puede ser instantánea. Que el scroll al tope no compita con la animación. |
| Pastillas de paso | `.step-pill`, `.step-pill.active`, `.step-pill.done` (en 6 módulos; el hub/MicMac y Mactor no las tienen) | cambio de color | el «done» gana su ✓ con una micro-animación; la activa tiene un subrayado que se desliza. Propón cómo llevarlas también a MicMac y Mactor. |
| Tarjetas del hub | `.mod-card` (8), `.mod-badge-reco` | hover: borde y fondo | hover con elevación sutil sin sombra azulada (usa `--paper-3` + borde `--accent`); el badge «Recomendado» aparece con una entrada clara cuando el wizard lo asigna (`highlightRecommendation`). |
| Botones | `.btn`, `.btn-ghost`, `.btn-mini`, `.btn.disabled` | hover plano | estado `:active` con 1 px de hundimiento; `disabled` que explique con `title` por qué. |
| Chips editables | `.chip`, `.chip-name[contenteditable]` | aparecen de golpe | entrada escalonada (stagger 30 ms) al renderizar una lista; salida con colapso de ancho. |
| Matrices NxN | `table.matrix td.cell` (MicMac y Mactor, con `data-i`/`data-j` y `tabindex`), `.cmp-table td` (Problema Público), `.morph-cell`/`.rob-cell` (Alternativas); celdas con ciclo 0→1→2→3 al clic | el número cambia sin feedback | pulso de fondo de 180 ms al cambiar valor; la fila y columna activas se iluminan al pasar el mouse (crosshair). |
| Barras de ranking | `.rank-bars` → `.rank-bar-row` (y `.winner`) en Problema Público | ancho fijo | el ancho crece desde 0 al renderizar (transición de `width`), con los números subiendo (opcional, JS mínimo). |
| Barras de IA | `.ia-bar`, `.ia-result`, botón `#ia-*-btn` | el botón dice «Generando…» | estado de espera con una línea que respira (no spinner circular) y una frase que rota cada 2 s; el `.ia-result` entra desplegándose. |
| Barra de nube | `.cloud-bar`, `.cb-status` | texto «guardado» | el punto `.cb-icon` cambia de color con transición y hace un pulso al guardar. |
| Toasts | `showToast()` → `#toast` | aparece/desaparece | entrada desde abajo, salida con fade; máximo uno visible. |
| Modales | `.modal-back`, `.modal` | display block/none | fondo con fade, caja con 10 px de subida; cerrar con Esc ya existe. |
| Acordeones | `details.accordion` | abre de golpe | altura animada con `grid-template-rows: 0fr → 1fr` (sin JS). |
| FAB recursos | `.lab-fab` (abajo izquierda) | tapa campos en pantallas ≤ 900 px | propón dónde vive en móvil para no tapar inputs ni el pie. |

## 5. El hub como recorrido (la pieza que más importa)

Hoy la grilla son 8 tarjetas iguales en 3 columnas. El texto debajo explica la
ruta («problema → alternativas → sistema → actores → escenarios → AIN →
evaluación → comunicar») pero la grilla no la muestra. Queremos que **la propia
grilla cuente el orden**:

- Numeración visible 01-08 en la esquina de cada tarjeta.
- Un conector visual (línea fina en `--rule-strong` con un punto en `--accent`)
  que enlace la tarjeta N con la N+1 en desktop; en móvil, una línea vertical a
  la izquierda tipo timeline.
- La tarjeta con contenido guardado (clase `.is-done` que ya usa la sección
  «Mi informe del lab») debe verse distinta: borde `--green`, kicker «En curso».
- El módulo recomendado por el wizard ya recibe `.mod-badge-reco`: dale una
  entrada memorable (una sola vez, 400 ms) y que el resto de tarjetas baje un
  poco su opacidad durante 2 s para dirigir la mirada.

No cambies la cantidad de columnas (1 / 2 / 3 según ancho) ni el `min-height`
de 260 px de las tarjetas.

## 6. Estados vacíos y de carga

Patrones que hoy son una línea en itálica gris («Aún no agregaste fuentes…»).
Queremos una pieza consistente para los 8 módulos:

- Caja punteada (`1px dashed var(--rule-strong)`), icono lineal de 24 px en
  `--ink-3`, una frase en `--italic` y **un botón de acción primaria** dentro
  («+ Agregar fila», «Cargar ejemplo»). La caja entra con fade.
- Para la espera del copiloto IA (10-25 s): un bloque con tres líneas
  «esqueleto» del ancho del texto que va a llegar, y la frase que rota. Al
  llegar el resultado, el esqueleto hace fade-out y el texto fade-in.

## 7. Cómo entregarlo para que se pueda pegar

- Un archivo `lab-motion.css` con secciones comentadas por elemento (§4), cada
  regla con su selector exacto. Variables de duración al inicio:
  `--t-fast:150ms; --t-base:220ms; --t-slow:320ms; --ease-out:cubic-bezier(.2,.7,.2,1)`.
- Si una pieza necesita JS (stagger de chips, conteo de números, estado de IA),
  una función pequeña y pura con el nombre que se llamaría desde el código
  existente, por ejemplo `labStagger(container)`; dinos dónde la invocaríamos.
- Una lista corta de lo que **no** hiciste y por qué, si algo del brief te
  pareció mala idea. Preferimos menos piezas bien resueltas que todas a medias.
