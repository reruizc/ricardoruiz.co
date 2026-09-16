#!/bin/bash
# Escucha diaria de redes por perfil (X vía Apify). La dispara launchd a las 08:00
# (co.ricardoruiz.caudal-escucha.plist) y, cuando el cron salga de la Mac, la línea
# equivalente de tools/caudal/ec2/crontab. Sin APIFY_TOKEN hace ensayo y sale bien.
#
# ESCUCHA_PERFILES: presets con escucha contratada, separados por espacio.
set -u
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
LOG="$REPO/Bases de datos/leyes-senado/redes/escucha/escucha.log"
mkdir -p "$(dirname "$LOG")"
if [ -f "$HOME/.config/caudal/redes.env" ]; then set -a; . "$HOME/.config/caudal/redes.env"; set +a; fi
ESCUCHA_PERFILES="${ESCUCHA_PERFILES:-cauce}"
rc=0
for p in $ESCUCHA_PERFILES; do
  echo "== $(date '+%Y-%m-%d %H:%M:%S') · $p" >> "$LOG"
  python3 "$REPO/tools/caudal/redes/escucha_perfil.py" "$p" --gastar --subir >> "$LOG" 2>&1 || rc=1
done
exit $rc
