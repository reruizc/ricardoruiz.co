#!/bin/bash
set -u
cd "$(dirname "$0")/../../.."
A="Bases de datos/leyes-senado/analisis"
export CAUDAL_EXTRACCION_BACKEND=ollama CAUDAL_EXTRACCION_MODEL=qwen3:32b
curl -s -m 5 http://localhost:11434/api/tags >/dev/null 2>&1 || { nohup ollama serve >/tmp/ollama.log 2>&1 & sleep 8; }

echo "== $(date +%H:%M) A · 30 ponencias 2022-2026 (tope 8, ventana normal)"
CAUDAL_MAX_OBLIGACIONES=8 CAUDAL_EXTRACCION_DIR="$A/extract-pon2022" \
  python3 tools/caudal/analisis/extraer_articulado.py extract \
  --cuatrienio 2022-2026 --base ponencia --limit 30 --workers 1
echo "== $(date +%H:%M) A lista: $(ls "$A/extract-pon2022" 2>/dev/null | wc -l)"

echo "== $(date +%H:%M) B · 10 truncados con ventana 60k y tope 24"
CAUDAL_MAX_CHARS=60000 CAUDAL_MAX_OBLIGACIONES=24 CAUDAL_EXTRACCION_DIR="$A/extract-v60k" \
  python3 tools/caudal/analisis/extraer_articulado.py extract \
  --toks "$(cat "$A/_retopados.txt")" --workers 1
echo "== $(date +%H:%M) FIN · pon2022: $(ls "$A/extract-pon2022" 2>/dev/null | wc -l) · v60k: $(ls "$A/extract-v60k" 2>/dev/null | wc -l)"
