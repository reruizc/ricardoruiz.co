# Ficha territorial · JAL Barrios Unidos (Bogotá 2023)

Página: `natalia-parra.html` (privada, `noindex`, gate por whitelist).
Datos servidos: `natalia-parra/datos/*.json` (el HTML los pide por ruta relativa).
Datos de trabajo: `Bases de datos/natalia-parra/` (gitignored, incluye `raw/`).

## Los tres builders

```bash
python3 tools/natalia-parra/build_electoral.py   # resultado + geografía (cacheado, ~instantáneo)
python3 tools/natalia-parra/build_contexto.py    # seguridad + mujer (cacheado)
python3 tools/natalia-parra/build_medios.py      # prensa — el único que conviene refrescar seguido
cp "Bases de datos/natalia-parra/"nsp-*.json natalia-parra/datos/
```

El electoral y el contexto salen de datos cerrados (elección de 2023, PONAL
2015-2024): se corren una vez. **El de medios es el que envejece**: una ventana
móvil de 21 días. Refrescarlo semanalmente es suficiente; el JSON lleva su
propia fecha y la página la muestra.

## Lo que hay que saber antes de tocar esto

**El número de votos por candidato no está en el JSON de la comuna.** Su campo
`cands` es `[nombre, índice_de_partido]` — el segundo valor NO son votos, aunque
lo parezca por el rango. Los votos viven en los arrays `v` = `[[idx, votos]…]`
de barrio, puesto y mesa, y el total se suma de ahí. Verificado: las tres vías
dan 709. Leer `cands[i][1]` como votos daba un ranking de 28 en vez de 23.

**`feat` es el índice del feature en el GeoJSON catastral**, no un código de
barrio: se resuelve por posición contra `BOG-BARRIOS-CATASTRALES.json`.

**El puesto suele llamarse como su barrio** (el puesto "JOSE JOAQUIN VARGAS"
está en el barrio "Jose Joaquin Vargas"). No es un bug de cruce: la tabla lo
colapsa a "idem" para no repetir la cadena en dos columnas.

**2023 no tiene dato por localidad en Bogotá.** En la desagregación por
localidad, 2023 llega en cero exacto en homicidios, lesiones, amenazas, delitos
sexuales, extorsión y hurto de motos, **en las 20 localidades a la vez**,
mientras el total nacional de ese año es normal (13.430 homicidios). Son hechos
que ese año llegaron sin barrio parseable. El builder emite `null` y la página
salta el año: dibujar el cero diría que la localidad no tuvo un solo homicidio
en 2023 y que en 2024 se disparó, y las dos cosas son falsas. La sparkline
dibuja los tramos **separados**, sin unir los extremos del hueco con una recta.

**El hurto de bicicletas solo existe desde 2024** en la fuente (`solo_2024`):
sus ceros previos son "no medido", no una tendencia. Va marcado y sin línea.

**El barrio de la Policía no casa con el barrio catastral** (~64% en Bogotá):
por eso el módulo de seguridad lista barrios y nunca los pinta como polígono.
El mapa electoral sí es polígono porque ahí el cruce es puesto→barrio por
punto-en-polígono, hecho río arriba.

**Los vertederos de registro ya vienen excluidos del hub** (BELLA SUIZA en
Bogotá concentraba el 9,9% de los hechos de la ciudad por ser el valor por
defecto del sistema). No hay que volver a filtrarlos aquí.

**El bloque de mujer describe a la VÍCTIMA, no al agresor.** La fuente no
registra la relación entre los dos: con estos datos no se puede afirmar qué
porcentaje de los casos fue la pareja. Está declarado en la página.

## Prensa

El navegador **nunca** llama a Google News: el script publica un JSON y la
página lo lee. Así no hay CORS, ni bloqueo por origen, ni clave en el cliente.

Dos filtros que costaron una pasada de revisión:

- **Las consultas locales van entre comillas.** Sin comillas, un nombre de
  barrio es ambiguo en toda la región: `La Castellana Bogotá` trajo una nota del
  Cauca sobre un homenaje en Tunía.
- **El titular tiene que nombrar el territorio** (`es_local`), o al menos hablar
  de gobierno local en Bogotá. Con eso el grupo local pasó de 141 titulares
  (mayormente arrastre de la consulta) a 24, todos de Barrios Unidos.
- El filtro de comunicados oficiales compara sobre el nombre **con espacios**:
  `\bgobernacion\b` nunca casa dentro de `gobernaciondelvalle`, porque ahí no
  hay frontera de palabra. Es la misma trampa del diccionario de empresas de
  Caudal.

## Verificar la página

El gate exige sesión, que el preview no tiene. Para verla en el navegador se
hace una copia temporal reemplazando el IIFE del gate por `init()` directo, se
sirve con `python3 -m http.server 8765` y **se borra al terminar** — no dejar
`_verificar-*.html` en el repo.

Al verificar mapas: **`animate: false`** en `fitBounds`/`setView`. El preview
congela `requestAnimationFrame` y la animación deja el zoom a medio camino (se
medía 14 en los tres niveles cuando debía dar 14 → 16 → 18). Y el viewport del
preview arranca en 0×0: hay que `resize_window` antes de medir anchos, o Leaflet
calcula un zoom absurdo sobre un contenedor de 41 px.
