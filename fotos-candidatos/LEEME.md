# Fotos de candidatos · flujo de trabajo

Staging local para las fotos que consume `analisis-candidato.html`
(S3 → `congreso-2026/output/fotos-candidatos/{SLUG}.jpg` y
`Fotos-presidenciales/{slug}.jpg` para los 6 presidenciales grandes).

## Flujo (sistematizado)

1. **Ver qué falta** — genera/actualiza `pendientes.csv` (ordenado por votos,
   los más votados primero) y muestra el top de faltantes en consola:
   ```bash
   python3 tools/fotos-candidatos/sync.py status
   ```

2. **Crear la imagen con IA (NanoBanana)** — abre `pendientes.csv`, copia el
   valor de la columna `slug` del candidato y guarda la imagen generada como
   `pendientes/{SLUG}.png` (o `.jpg`). El nombre del archivo ES el slug —
   sin eso no hay match. Formato ideal: editorial 3:2 (1248×864), el rostro
   arriba del centro (la página recorta con `object-position: center 15%`).

3. **Subir a S3** — normaliza (convierte a JPG, redimensiona a máx 1200 px),
   sube todo lo que haya en `pendientes/` y mueve el original a `subidas/`:
   ```bash
   python3 tools/fotos-candidatos/sync.py subir --dry-run   # ver qué haría
   python3 tools/fotos-candidatos/sync.py subir             # subir de verdad
   ```

Los presidenciales sin foto aparecen en el CSV con slug `PRES1V_...` — se
suben a la misma carpeta `fotos-candidatos/` de S3 y la página los toma solos.

> `pendientes/`, `subidas/` y `pendientes.csv` están gitignoreados: las fotos
> viven en S3, no en el repo.
