#!/bin/zsh
# ¿Quién queda? — corrida cada 6 horas.
# Dispara launchd (co.ricardoruiz.pronosticos.plist). Ver LEEME.md.
#
# Puente mientras el usuario ricardo-mac-cli no tenga permisos de EventBridge;
# cuando los tenga, esto se mueve a Lambda y deja de depender del Mac.

export PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin
REPO="/Users/ricardoruiz/ricardoruiz.co"
OUT="$REPO/Bases de datos/pronosticos"
S3="s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/pronosticos"
LOG="$OUT/cron.log"
LOCK="$OUT/.lock"

mkdir -p "$OUT"

# candado: launchd puede disparar una corrida perdida encima de la programada
if [ -d "$LOCK" ]; then
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +45 2>/dev/null)" ]; then
    rmdir "$LOCK" 2>/dev/null   # candado viejo: la corrida anterior murió
  else
    echo "$(date '+%F %T') · ya hay una corrida en curso, se omite" >> "$LOG"
    exit 0
  fi
fi
mkdir "$LOCK" 2>/dev/null || exit 0
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

# rotación simple del log
if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt 800000 ]; then
  mv "$LOG" "$LOG.1"
fi

echo "════ $(date '+%F %T') ════" >> "$LOG"
cd "$REPO" || exit 1

python3 tools/pronosticos/motor.py >> "$LOG" 2>&1
rc_motor=$?

rc_up=0
if [ $rc_motor -eq 0 ]; then
  for f in "$OUT"/*.json; do
    [ -e "$f" ] || continue
    aws s3 cp "$f" "$S3/$(basename "$f")" \
      --content-type "application/json" \
      --cache-control "public, max-age=300" >> "$LOG" 2>&1 || rc_up=1
  done
else
  echo "motor falló (rc=$rc_motor): no se sube nada, queda el bueno de la corrida anterior" >> "$LOG"
  rc_up=-1
fi

echo "$(date '+%F %T') · cierre motor=$rc_motor upload=$rc_up" >> "$LOG"
exit 0
