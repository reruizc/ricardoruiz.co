#!/bin/zsh
# Corre una batalla y la publica. Lo llama el agente launchd co.ricardoruiz.batalla cada 10 min.
#   tools/batalla/run_batalla.sh marcha-14oct-2026
# Deja de correr solo cuando pasa la fecha «hasta» del archivo de la batalla.
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin
REPO=/Users/ricardoruiz/ricardoruiz.co
B=${1:-marcha-14oct-2026}
LOG="$REPO/Bases de datos/batalla/$B/run.log"
LOCK=/tmp/batalla-$B.lock
mkdir -p "$REPO/Bases de datos/batalla/$B"
mkdir "$LOCK" 2>/dev/null || { echo "$(date '+%F %T') ya hay una corrida en curso" >> "$LOG"; exit 0; }
trap 'rmdir "$LOCK"' EXIT
HASTA=$(python3 -c "import json;print(json.load(open('$REPO/tools/batalla/batallas/$B.json')).get('hasta',''))")
if [[ -n "$HASTA" ]] && python3 -c "import datetime as d,sys;sys.exit(0 if d.datetime.now(d.timezone.utc)>d.datetime.fromisoformat('$HASTA') else 1)"; then
  echo "$(date '+%F %T') la batalla terminó ($HASTA): no se corre" >> "$LOG"; exit 0
fi
cd "$REPO" && { echo "--- $(date '+%F %T')"; python3 -u tools/batalla/batalla.py "$B" --subir; } >> "$LOG" 2>&1
