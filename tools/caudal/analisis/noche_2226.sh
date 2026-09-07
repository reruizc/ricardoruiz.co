#!/bin/bash
# Cuatrienio 2022-2026, por PONENCIAS.
#
# Por qué ponencias y no exposiciones de motivos: medido sobre 30 documentos de
# cada una, la ponencia rinde 4,6 obligaciones por documento —igual que el texto
# radicado— y la exposición de motivos 0,7, con el 80% sin ninguna. La
# exposición argumenta por qué hace falta la ley; la ponencia trae el articulado.
#
# Ventana en 60.000 y no 28.000: estos textos son Gacetas del Congreso, donde el
# articulado del proyecto puede empezar pasado el carácter 137.000. Con 28k, en
# Cámara solo el 15% de los proyectos quedaba bien atribuido; con 60k, el 90%.
set -u
cd "$(dirname "$0")/../../.."
A="Bases de datos/leyes-senado/analisis"
export CAUDAL_EXTRACCION_BACKEND=ollama CAUDAL_EXTRACCION_MODEL=qwen3:32b
curl -s -m 5 http://localhost:11434/api/tags >/dev/null 2>&1 || { nohup ollama serve >/tmp/ollama.log 2>&1 & sleep 8; }

echo "== $(date +%H:%M) 2022-2026 · ponencias · ventana 60k · tope 16 · máx 8 h"
CAUDAL_MAX_CHARS=60000 CAUDAL_MAX_OBLIGACIONES=16 CAUDAL_EXTRACCION_DIR="$A/extract-2226" \
  python3 tools/caudal/analisis/extraer_articulado.py extract \
  --cuatrienio 2022-2026 --base ponencia --workers 1 &
pid=$!
( sleep 28800; kill -TERM $pid 2>/dev/null; sleep 20; kill -9 $pid 2>/dev/null ) & wd=$!
wait $pid 2>/dev/null; kill $wd 2>/dev/null
echo "== $(date +%H:%M) FIN · $(ls "$A/extract-2226" 2>/dev/null | wc -l) extracciones"
