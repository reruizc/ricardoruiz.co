#!/usr/bin/env bash
# Arma el sitio que sirve Cloudflare Pages en brujulapolitica.pages.dev.
#
# La estructura es país/ciudad, no ciudad suelta: la marca es Brújula Política y cada
# elección entra como /paraguay/asuncion/, /colombia/bogota/, /brasil/saopaulo/…
# Agregar una es UNA línea en SITIOS más su carpeta en el repo — nada de tocar el motor.
#
# La raíz redirige a la ciudad de RAIZ con 302 (no 301: el día que la raíz sea un índice
# de países, un 301 cacheado en el navegador seguiría mandando a Asunción).
#
# En el panel de Pages:
#   Build command:            bash tools/brujula-pages/build_pages.sh
#   Build output directory:   _site
set -euo pipefail

# carpeta_en_el_repo:ruta_publicada
SITIOS=(
  "brujula-asuncion:paraguay/asuncion"
)
RAIZ="paraguay/asuncion"     # a dónde manda brujulapolitica.pages.dev a secas
DESTINO="_site"

rm -rf "$DESTINO"; mkdir -p "$DESTINO"

for s in "${SITIOS[@]}"; do
  origen="${s%%:*}"; ruta="${s#*:}"
  [ -d "$origen" ] || { echo "FALTA la carpeta $origen" >&2; exit 1; }
  mkdir -p "$DESTINO/$ruta"
  cp -R "$origen"/. "$DESTINO/$ruta/"
  # el builder de datos y las notas internas no tienen nada que hacer en el sitio publicado
  rm -rf "$DESTINO/$ruta/tools"
  rm -f  "$DESTINO/$ruta/LEEME.md"
  echo "  $origen -> /$ruta/"
done

printf '/ /%s/ 302\n' "$RAIZ" > "$DESTINO/_redirects"

echo "OK · $(find "$DESTINO" -type f | wc -l | tr -d ' ') archivos · raíz -> /$RAIZ/ (302)"
