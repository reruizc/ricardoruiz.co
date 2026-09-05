#!/bin/bash
# Brief matutino — runner del cron (launchd, diario 07:15).
# Lee lo que los crons existentes ya produjeron; no toca run_diario.sh
# ni run_alertas.sh. Sin secretos en el repo (es público): se cargan de
# ~/.config/caudal/alertas.env, igual que hace el motor de alertas.

set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

REPO="${CAUDAL_REPO:-/Users/ricardoruiz/ricardoruiz.co}"   # la instancia EC2 lo pasa por el crontab
AQUI="$REPO/tools/brief"
SALIDA="$REPO/Bases de datos/brief"
LOG="$SALIDA/brief.log"

mkdir -p "$SALIDA"
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') · $*" >> "$LOG"; }

if [ -f "$HOME/.config/caudal/alertas.env" ]; then
  # shellcheck disable=SC1091
  set -a; . "$HOME/.config/caudal/alertas.env"; set +a
fi

cd "$REPO" || { log "no existe $REPO"; exit 1; }
log "arranca"
python3 "$AQUI/brief.py" "$@" >> "$LOG" 2>&1
RC=$?
log "termina con código $RC"

# tope del log
if [ -f "$LOG" ] && [ "$(wc -l < "$LOG")" -gt 2000 ]; then
  tail -n 1500 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi
exit $RC
