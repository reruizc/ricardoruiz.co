#!/bin/bash
# Revisa el buzón en busca de notificaciones de banco y las manda a /gastos/ingest.
# Lo dispara launchd cada 2 horas (co.ricardoruiz.gastos-correos.plist).
#
# Deliberadamente NO va dentro de run_diario.sh: ese es el pipeline de Caudal,
# corre 2 veces al día y tiene su propio candado. Mezclarlos haría que un fallo
# de uno arrastre al otro.

REPO="/Users/ricardoruiz/ricardoruiz.co"
LOG="$REPO/Bases de datos/leyes-senado/diario/gastos-correos.log"
CFG="$HOME/.config/gastos/gastos.env"

# aws y python3 viven en homebrew; launchd no hereda el PATH de la terminal.
export PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

mkdir -p "$(dirname "$LOG")"

# Sin contraseña de aplicación no hay nada que hacer: se sale en silencio en vez
# de escribir un error cada 2 horas hasta llenar el log.
if [ ! -f "$CFG" ] || ! grep -q '^GASTOS_IMAP_PASS=.\+' "$CFG"; then
  exit 0
fi

# Candado: si la corrida anterior sigue viva, esta no arranca.
LOCK="/tmp/gastos-correos.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  echo "$(date '+%F %T') · saltada (la anterior sigue corriendo)" >> "$LOG"
  exit 0
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

# Rotación simple: el log no debe crecer sin freno.
if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt 1000000 ]; then
  tail -n 500 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

echo "$(date '+%F %T') · revisando correo" >> "$LOG"
cd "$REPO" || exit 1
python3 tools/gastos/correos.py --dias 1 >> "$LOG" 2>&1
echo "$(date '+%F %T') · fin (rc=$?)" >> "$LOG"
