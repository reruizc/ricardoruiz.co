# Nuevo Liberalismo · rumbo a 2027 — presentación en HTML

Abrir `index.html` con doble clic (funciona sin servidor; solo el logo usa la fuente Syne de Google y cae a una de sistema si no hay internet).
Alt + ← / Alt + → pasa de módulo. Todo está en `datos/*.js` (copias de los `.json`), Leaflet en `vendor/`, fuentes en `fonts/`.

| Módulo | Página | Constructor (en `tools/nuevo-liberalismo/`) |
|---|---|---|
| Hub | `index.html` | `build_hub_mapa.py` (mapa de la portada, tras el inventario) y `build_hub.py` (correr al final) |
| 01 Tablero | `tablero.html` | `agrega_congreso.py` → `agrega_presidencial.py` → `build_tablero.py` · `build_senado_historico.py` |
| 02 Inventario | `inventario.html` | `agrega_ter2023.py` → `build_inventario.py` |
| 03 Clima social | `clima.html` | `build_clima.py` |
| 04 Reglas y escenarios | `escenarios.html` | `build_escenarios.py` (lee `ter2023-agg.json` del inventario) |

Después de cualquier constructor: `python3.14 tools/nuevo-liberalismo/build_hub_mapa.py && python3.14 tools/nuevo-liberalismo/build_hub.py && python3.14 tools/nuevo-liberalismo/empaqueta.py`, y subir `DATOS_V` en `base.js` (si no, el navegador muestra los datos viejos). Al tocar `base.css` o `base.js`, subir su `?v=` en las cinco páginas.
Los intermedios pesados viven en `Bases de datos/nuevo-liberalismo/` (gitignoreado).

## Lo que hay que saber antes de presentar
- **Tablero**: inferencia ecológica por puesto (13.038 con Senado, presidencial y censo; sin exterior). Los márgenes salen de 200 réplicas por municipio; la prueba con municipios apartados está en la propia página. El Nuevo Liberalismo va dentro de «Ahora Colombia» en el Senado; solo en Bogotá, a la Cámara, tuvo lista propia.
- **Senado 2014-2026**: los vínculos son linaje de partido, no trasvase de votantes. Las fusiones están declaradas en `build_senado_historico.py` (`SUCESION`).
- **Inventario**: las curules de concejo, asamblea y JAL son estimadas (escala de la Ley 136 + art. 263 C.P.), no declaratorias.
- **Clima**: el banco es de prensa de Medellín/Antioquia más 4 medios nacionales; tema y tono los clasificó un modelo.
- **Escenarios**: calendario según la Resolución 12338 de 2026 leída vía prensa (el comunicado oficial no abrió); lo no confirmado va marcado «por verificar».
- **Repo público**: esta carpeta NO está en `.gitignore`. No hacer `git add -A` sin sacarla.

## Cambios del 10-nov-2026

- **Orden de módulos:** 01 inventario · 02 análisis (`tablero.html`) · 03 dónde estamos (`clima.html`) · 04 reglas y escenarios · 05 estrategia (`estrategia.html`).
- **Selector de ámbito** General · Bogotá · Resto del país en cada módulo (lo pinta `NL.nav` en `base.js`). Se guarda en `localStorage['nl-ambito']` y en `?ambito=`. Un elemento con `data-en="bogota resto"` solo se ve en esos ámbitos. API: `NL.ambito()`, `NL.setAmbito()`, `NL.alCambiarAmbito(fn)`.
- **Letra:** Archivo variable (`fonts/archivo-var.woff2`, peso y ancho). El logo del partido (`img/nl-logo.png`) y la silueta del título (`img/nl-silueta.png`) salen de nuevoliberalismo.org. Las fotos de las tarjetas son copias de `imagenes/` del sitio.
- **Estrategia (módulo 05):** tres archivos, `datos/estrategia-{general,bogota,resto}.json`, generados por `tools/nuevo-liberalismo/build_estrategia_{general,bogota,resto}.py`. Cada pilar cita un principio y fichas de `candidato-360-data/estrategia-banco.json`; lo que no sale del banco va como criterio de oficio. Es una propuesta para discutir, no un pronóstico.
- **Lista propia o coalición:** cada curul estimada dice de qué lista salió. Concejo de Bogotá verificado contra la página oficial del Concejo (consultada el 10-nov-2026).
- **Datos nuevos:** `hub-mapa` (`build_hub_mapa.py`), `clima-ambito` (`build_clima_ambito.py`), `bog-localidades`, territorio «Resto del país» en `tablero` (`build_tablero.py`).
- Al regenerar datos: subir `DATOS_V` en `base.js` y el `?v=` de `base.css`/`base.js` en las seis páginas.
