# Charla · Maestría en Comunicación Política · Universidad de La Sabana

Clase **Estrategias de Participación Digital**. ~40–45 min + 10 de preguntas.
Tema: *cómo se lee socialmente a un público con datos* (sin revelar técnica),
con tres casos de la 1ª vuelta 2026 y cómo le sirve a una causa social.

## Archivos
- `presentacion.html` — el deck (HTML autocontenido, a la marca). **Es el principal.**
- `presentacion.pdf` — respaldo (20 páginas 16:9) por si el proyector falla.
- `img/` — imágenes usadas (carrusel de edad + mapas de Bogotá del informe Pacto).

## Cómo presentar
Abre `presentacion.html` en el navegador (doble clic o desde el server local).

| Tecla | Acción |
|---|---|
| `→` / espacio | Avanzar |
| `←` | Retroceder |
| **`N`** | **Notas del orador** (guion de cada diapositiva, abajo) |
| `F` | Pantalla completa |
| `Inicio` / `Fin` | Primera / última |
| `?` | Ayuda de controles |

Las notas del orador (tecla `N`) traen el guion hablado de cada slide y, donde
aplica, un recordatorio **EN VIVO →** para abrir tus herramientas reales
(`edades-1v.html`, `bogota-1v-barrios.html`, `oportunidad.html`).

## ⚠️ Antes de presentar
En las notas de la **portada** hay un placeholder: `[Saludar a la profesora por su nombre]`.
Reemplázalo por el nombre real (búscalo en `presentacion.html`).

## Estructura (20 diapositivas)
1. Portada · 2. Quién habla · 3. La premisa (resolución) · 4. Método (lo justo)
· **5–9 Caso 1: generaciones** · **10–13 Caso 2: las dos Bogotás** ·
**14–16 Caso 3: arquetipos emocionales** · 17. Para una causa · 18. Límites
del método · 19. Cierre · 20. Gracias / preguntas.

## Regenerar el PDF (si editas el deck)
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --no-pdf-header-footer \
  --run-all-compositor-stages-before-draw --virtual-time-budget=12000 \
  --print-to-pdf="charla-sabana/presentacion.pdf" \
  "file:///Users/ricardoruiz/ricardoruiz.co/charla-sabana/presentacion.html"
```
El deck tiene un `@media print` que pone una diapositiva por página (16:9).
