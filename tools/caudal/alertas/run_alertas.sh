#!/bin/bash
# Caudal · Alertas — runner del cron.
#
# Corre DESPUÉS del rastreo diario y es INDEPENDIENTE de él: no se toca
# run_diario.sh (es de otro proceso) y este script no escribe nada suyo.
# Si el rastreo se cayó, el motor igual corre y lo dice por el canal de
# operación — que es justamente cuando más falta hace.
#
# Instalación: ver README.md, sección "Cómo se monta el cron".

set -uo pipefail

# aws y python3 viven en /opt/homebrew/bin y launchd arranca con un PATH mínimo.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

REPO="${CAUDAL_REPO:-/Users/ricardoruiz/ricardoruiz.co}"   # la instancia EC2 lo pasa por el crontab
AQUI="$REPO/tools/caudal/alertas"
DATOS="${CAUDAL_ALERTAS_DIR:-$AQUI/datos}"
LOG="$DATOS/alertas.log"

mkdir -p "$DATOS"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') · $*" >> "$LOG"; }

# --- candado ---------------------------------------------------------------
# Dos corridas simultáneas se pisarían el estado y podrían mandar el mismo
# digest dos veces. mkdir es atómico; si el dueño del candado ya murió (Mac
# suspendido a media corrida), se recupera.
LOCK="$DATOS/.alertas.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  DUENO=$(cat "$LOCK/pid" 2>/dev/null || echo "")
  if [ -n "$DUENO" ] && kill -0 "$DUENO" 2>/dev/null; then
    log "otra corrida sigue viva (pid $DUENO): salgo sin hacer nada"
    exit 0
  fi
  log "candado huérfano (pid '$DUENO' ya no existe): lo recupero"
  rm -rf "$LOCK" && mkdir "$LOCK" || { log "no pude tomar el candado"; exit 1; }
fi
echo $$ > "$LOCK/pid"
trap 'rm -rf "$LOCK"' EXIT

# --- los dos secretos ------------------------------------------------------
# NINGUNO vive en el repo (que es público). Se buscan, en orden:
#   1. el entorno (si alguien los exportó antes de llamar)
#   2. ~/.config/caudal/alertas.env  (chmod 600, fuera del repo)
#
#   RESEND_API_KEY        manda los correos. Sin ella el motor NO falla:
#                         escribe los digests y los deja encolados.
#   CAUDAL_ALERTAS_TOKEN  lee los perfiles de cliente del worker rr-auth
#                         (mismo valor que `npx wrangler secret put
#                         CAUDAL_ALERTAS_TOKEN`). Sin él la corrida no se cae:
#                         se queda con los sectores, que es el fallback.
if [ -f "$HOME/.config/caudal/alertas.env" ] &&
   { [ -z "${RESEND_API_KEY:-}" ] || [ -z "${CAUDAL_ALERTAS_TOKEN:-}" ]; }; then
  # shellcheck disable=SC1091
  set -a; . "$HOME/.config/caudal/alertas.env"; set +a
fi

if [ -z "${RESEND_API_KEY:-}" ]; then
  log "RESEND_API_KEY ausente · los digests quedarán en disco y encolados"
fi
if [ -z "${CAUDAL_ALERTAS_TOKEN:-}" ]; then
  log "CAUDAL_ALERTAS_TOKEN ausente · sin perfiles de cliente, corrida por sectores"
fi

# --- corrida ---------------------------------------------------------------
cd "$REPO" || { log "no existe $REPO"; exit 1; }
INICIO=$(date +%s)
log "arranca (fecha $(date '+%Y-%m-%d'))"

# timeout defensivo: la Lambda y Google News son terceros y pueden colgarse.
# 12 min es holgado — la corrida completa medida tarda ~45 s.
if command -v timeout >/dev/null 2>&1; then
  TIMEOUT="timeout 720"
elif command -v gtimeout >/dev/null 2>&1; then
  TIMEOUT="gtimeout 720"
else
  TIMEOUT=""
fi

$TIMEOUT python3 "$AQUI/motor.py" "$@" >> "$LOG" 2>&1
RC=$?

DUR=$(( $(date +%s) - INICIO ))
case $RC in
  0)   log "termina ok en ${DUR}s" ;;
  124) log "TIMEOUT a los ${DUR}s — probablemente un tercero colgado" ;;
  *)   log "termina con código $RC en ${DUR}s" ;;
esac

# El log crece poco (unas 30 líneas por corrida), pero sin tope crece para
# siempre. Se conservan las últimas 5000 líneas.
if [ -f "$LOG" ] && [ "$(wc -l < "$LOG")" -gt 5000 ]; then
  tail -n 4000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

exit $RC
