#!/bin/bash
# Saca un cuadro del video cada N segundos y lee la pantalla con OCR local (Vision).
# Uso: cuadros.sh <url-youtube> <carpeta-salida> [segundos=30]
# Salidas en la carpeta: cuadros/HHMMSS.jpg · ocr.tsv (epoch, hora, y, x, texto)
#   · oradores.tsv (epoch, hora, nombre, organización) solo cuando cambia quien habla.
URL="$1"; OUT="$2"; CADA="${3:-30}"
[ -z "$URL" ] || [ -z "$OUT" ] && { echo "uso: $0 <url> <carpeta> [seg]"; exit 1; }
DIR="$(cd "$(dirname "$0")" && pwd)"
OCR="$HOME/.cache/audiencia-en-vivo/ocr_cuadro"
if [ ! -x "$OCR" ] || [ "$DIR/ocr_cuadro.swift" -nt "$OCR" ]; then
  mkdir -p "$(dirname "$OCR")"; swiftc -O "$DIR/ocr_cuadro.swift" -o "$OCR" || exit 1
fi
mkdir -p "$OUT/cuadros"; touch "$OUT/ocr.tsv" "$OUT/oradores.tsv"
# ningún comando de red puede colgar el bucle: corte duro con alarm
limite() { perl -e 'alarm shift; exec @ARGV' "$@"; }
V=""; t0=0; ultimo=""
while true; do
  ahora=$(date +%s)
  # el enlace del video vence: renovar cada hora o si falla
  if [ -z "$V" ] || [ $((ahora - t0)) -gt 3600 ]; then
    V=$(limite 60 yt-dlp --no-warnings -f "270/232/best" -g "$URL" 2>/dev/null | head -1); t0=$ahora
  fi
  h=$(date +%H%M%S); f="$OUT/cuadros/$h.jpg"
  if [ -n "$V" ] && limite 40 ffmpeg -rw_timeout 15000000 -nostdin -loglevel error -y -i "$V" -frames:v 1 -q:v 4 "$f" 2>>"$OUT/log-cuadros.txt"; then
    hh=$(date +%H:%M:%S)
    "$OCR" "$f" | awk -F'\t' -v e="$ahora" -v h="$hh" 'BEGIN{OFS="\t"}{print e,h,$1,$2,$3}' > "$OUT/.ocr_tmp"
    cat "$OUT/.ocr_tmp" >> "$OUT/ocr.tsv"
    # rótulo del orador: franja y∈[0.15,0.26], x<0.7 → la línea de arriba es el nombre, la de abajo la organización
    o=$(awk -F'\t' '$3>=0.15 && $3<=0.26 && $4<0.7' "$OUT/.ocr_tmp" | sort -t$'\t' -k3,3nr | cut -f5 | head -2 | paste -sd$'\t' -)
    if [ -n "$o" ] && [ "$o" != "$ultimo" ]; then printf '%s\t%s\t%s\n' "$ahora" "$hh" "$o" >> "$OUT/oradores.tsv"; ultimo="$o"; fi
  else
    V=""   # forzar renovación del enlace
  fi
  sleep $(( CADA - ($(date +%s) - ahora) > 1 ? CADA - ($(date +%s) - ahora) : 1 ))
done
