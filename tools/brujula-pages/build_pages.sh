#!/usr/bin/env bash
# Arma el sitio que sirve Cloudflare Pages en brujulapolitica.pages.dev.
#
# La Brújula vive en /asuncion/ y NO en la raíz, a propósito: el dominio es la marca
# (Brújula Política), no la ciudad. Si mañana hay otra ciudad entra al lado, sin mover
# la de Asunción — un enlace compartido no se puede romper después.
# La raíz redirige a /asuncion/ con 302 (no 301: el día que la raíz sea un índice de
# ciudades, un 301 cacheado en el navegador seguiría mandando a Asunción).
#
# En el panel de Pages:
#   Build command:            bash tools/brujula-pages/build_pages.sh
#   Build output directory:   _site
set -euo pipefail

ORIGEN="brujula-asuncion"
DESTINO="_site"
CIUDAD="asuncion"

rm -rf "$DESTINO"
mkdir -p "$DESTINO/$CIUDAD"
cp -R "$ORIGEN"/. "$DESTINO/$CIUDAD/"

# el builder de datos y el .docx fuente no tienen nada que hacer en el sitio publicado
rm -rf "$DESTINO/$CIUDAD/tools"
rm -f  "$DESTINO/$CIUDAD/LEEME.md"

printf '/ /%s/ 302\n' "$CIUDAD" > "$DESTINO/_redirects"

echo "OK · $(find "$DESTINO" -type f | wc -l | tr -d ' ') archivos en $DESTINO/"
echo "     raíz -> /$CIUDAD/ (302)"
