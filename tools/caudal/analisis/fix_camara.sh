#!/bin/bash
# Re-extrae los proyectos de CÁMARA con la ventana ampliada.
#
# El texto de Cámara no es el radicado suelto: es la Gaceta del Congreso, de
# ~200.000 caracteres, donde el articulado del proyecto empieza pasado el
# carácter 137.000. Con la ventana en 28.000 se le manda al modelo un tramo que
# a menudo no es el articulado de ESE proyecto — medido: el 85% de los
# proyectos de Cámara tiene un resumen que no corresponde a su título, contra
# el 2% en Senado, y son 811 obligaciones atribuidas al proyecto equivocado.
#
# Va a un caché APARTE: si la ventana ampliada no mejora la atribución, no se
# fusiona nada. La comparación se hace después, no aquí.
set -u
cd "$(dirname "$0")/../../.."
A="Bases de datos/leyes-senado/analisis"
export CAUDAL_EXTRACCION_BACKEND=ollama CAUDAL_EXTRACCION_MODEL=qwen3:32b
curl -s -m 5 http://localhost:11434/api/tags >/dev/null 2>&1 || { nohup ollama serve >/tmp/ollama.log 2>&1 & sleep 8; }

echo "== $(date +%H:%M) Cámara · 217 proyectos · ventana 60k · tope 16"
CAUDAL_MAX_CHARS=60000 CAUDAL_MAX_OBLIGACIONES=16 CAUDAL_EXTRACCION_DIR="$A/extract-camara60k" \
  python3 tools/caudal/analisis/extraer_articulado.py extract \
  --toks "$(cat "$A/_camara.txt")" --workers 1
echo "== $(date +%H:%M) FIN · $(ls "$A/extract-camara60k" 2>/dev/null | wc -l) extracciones"
