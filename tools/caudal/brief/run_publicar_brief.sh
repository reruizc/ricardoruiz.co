#!/bin/bash
# Brief de Fable para el botón de la Rosa. Lunes y jueves a las 09:30 (launchd
# co.ricardoruiz.caudal-brief-rosa; en el servidor, la línea de ec2/crontab):
# después del rastreo de las 08:00 y de la escucha de redes, para que el brief
# salga con los registros del día y la conversación en X.
set -u
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
LOG="$REPO/Bases de datos/caudal-briefs/publicar.log"
mkdir -p "$(dirname "$LOG")"
for f in anthropic.env briefs.env; do
  if [ -f "$HOME/.config/caudal/$f" ]; then set -a; . "$HOME/.config/caudal/$f"; set +a; fi
done
echo "== $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG"
python3 "$REPO/tools/caudal/brief/publicar_brief.py" >> "$LOG" 2>&1
