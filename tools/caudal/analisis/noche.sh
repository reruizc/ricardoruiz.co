#!/bin/bash
# Tanda nocturna del articulado. Dos trabajos en orden de valor:
#   1) 30 exposiciones de motivos de 2022-2026, tope 8 → ¿rinde esa fuente?
#      Es lo que decide si el cuatrienio pasado se puede procesar tal cual o
#      si primero hay que conseguir los textos radicados. Tope 90 min: si algo
#      sale mal ahí, no se puede comer la noche entera.
#   2) los proyectos que llegaron al tope de 8 obligaciones, releídos con 16.
#      Medido sobre 6: +42% de obligaciones, todas ancladas en el texto.
#      Tope 7 h.
# Cachés APARTE: nada se mezcla con el corpus bueno hasta haberlo mirado.
# El extractor es resumible (caché por proyecto), así que matarlo por tiempo
# no pierde lo ya hecho.
set -u
cd "$(dirname "$0")/../../.."
A="Bases de datos/leyes-senado/analisis"
export CAUDAL_EXTRACCION_BACKEND=ollama CAUDAL_EXTRACCION_MODEL=qwen3:32b

# Sin el servidor de ollama arriba, el extractor falla los N documentos en
# segundos con "Connection refused" y la noche se pierde en silencio. Pasó.
ollama_arriba () {
  curl -s -m 5 http://localhost:11434/api/tags >/dev/null 2>&1 && return 0
  echo "   (ollama caído · levantando)"
  nohup ollama serve > /tmp/ollama.log 2>&1 &
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    sleep 3
    curl -s -m 5 http://localhost:11434/api/tags >/dev/null 2>&1 && return 0
  done
  echo "   !! ollama no responde · se aborta la tanda"; return 1
}

corre () {   # corre <segundos> <comando...>
  local t=$1; shift
  "$@" &
  local pid=$!
  ( sleep "$t"; kill -TERM "$pid" 2>/dev/null; sleep 20; kill -9 "$pid" 2>/dev/null ) &
  local wd=$!
  wait "$pid" 2>/dev/null
  kill "$wd" 2>/dev/null
}

ollama_arriba || exit 1
echo "== $(date +%H:%M) tanda 1 · 30 exposiciones de motivos 2022-2026 (tope 8 · máx 90 min)"
CAUDAL_MAX_OBLIGACIONES=8 CAUDAL_EXTRACCION_DIR="$A/extract-em2022" \
  corre 5400 python3 tools/caudal/analisis/extraer_articulado.py extract \
  --cuatrienio 2022-2026 --base exposicion_motivos --limit 30 --workers 1
echo "== $(date +%H:%M) tanda 1 lista: $(ls "$A/extract-em2022" 2>/dev/null | wc -l) extracciones"

ollama_arriba || exit 1
echo "== $(date +%H:%M) tanda 2 · topados releídos con tope 16 (máx 7 h)"
CAUDAL_MAX_OBLIGACIONES=16 CAUDAL_EXTRACCION_DIR="$A/extract-tope16" \
  corre 25200 python3 tools/caudal/analisis/extraer_articulado.py extract \
  --toks "$(cat "$A/_topados.txt")" --workers 1
echo "== $(date +%H:%M) FIN · tope16: $(ls "$A/extract-tope16" | wc -l) · em2022: $(ls "$A/extract-em2022" 2>/dev/null | wc -l)"
