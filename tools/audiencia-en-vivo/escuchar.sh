#!/bin/bash
# Escucha una transmisión en vivo de YouTube y la transcribe local con whisper.cpp.
# Uso: escuchar.sh <url-youtube> <carpeta-salida>
# - ffmpeg corta el audio en tramos de 2 min sin huecos (se reinicia si el enlace vence).
# - otro bucle transcribe cada tramo terminado y lo agrega a transcripcion.md con la hora.
URL="$1"; OUT="$2"
[ -z "$URL" ] || [ -z "$OUT" ] && { echo "uso: $0 <url> <carpeta>"; exit 1; }
mkdir -p "$OUT/tramos"
MODELO="$HOME/.cache/whisper/ggml-small.bin"
TXT="$OUT/transcripcion.md"
[ -f "$TXT" ] || echo "# Transcripción automática (whisper small, local) · $URL" > "$TXT"

capturar() {
  while true; do
    S=$(yt-dlp --no-warnings -f "bestaudio/best" -g "$URL" 2>/dev/null | head -1)
    if [ -z "$S" ]; then echo "[$(date +%T)] sin señal, reintento en 30 s" >> "$OUT/log.txt"; sleep 30; continue; fi
    ffmpeg -nostdin -loglevel error -i "$S" -vn -ac 1 -ar 16000 \
      -f segment -segment_time 120 -reset_timestamps 1 -strftime 1 \
      "$OUT/tramos/%Y%m%d-%H%M%S.wav" >> "$OUT/log.txt" 2>&1
    echo "[$(date +%T)] ffmpeg terminó, reconecto" >> "$OUT/log.txt"; sleep 3
  done
}

transcribir() {
  while true; do
    # todos menos el más nuevo (que sigue grabándose)
    # ls | while read: la carpeta puede tener espacios ("Bases de datos")
    ls "$OUT"/tramos/*.wav 2>/dev/null | sort | sed '$d' | while IFS= read -r f; do
      b=$(basename "$f" .wav)
      [ -f "$OUT/tramos/$b.hecho" ] && continue
      h="${b:9:2}:${b:11:2}"
      t=$(whisper-cli -m "$MODELO" -l es -f "$f" -nt -np 2>/dev/null | tr -s ' \n' ' ')
      printf '\n## %s\n%s\n' "$h" "$t" >> "$TXT"
      touch "$OUT/tramos/$b.hecho"; rm -f "$f"
    done
    sleep 20
  done
}

capturar & transcribir & wait
