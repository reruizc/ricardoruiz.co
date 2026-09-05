#!/bin/bash
# Manda el ESTADO del pipeline de la Mac a la instancia (rsync, resumible).
# Solo lo que el cron lee o escribe: ~8 GB. Fuera quedan las actas de plenaria
# de Cámara (3,2 GB, solo para el voto nominal), los PDF de gacetas (1,5 GB,
# solo para análisis puntual) y los análisis locales.
#
#   tools/caudal/ec2/sync-estado.sh ec2-user@IP_O_DNS          # primera vez y refrescos
#   tools/caudal/ec2/sync-estado.sh ec2-user@IP_O_DNS --dry-run
#
# Se puede correr las veces que sea: solo viaja lo que cambió. ANTES de apagar
# el launchd de la Mac, correrlo una última vez para que la instancia arranque
# con el snapshot de hoy (el diff diario compara contra el de ayer).
set -euo pipefail
DEST="${1:?uso: sync-estado.sh usuario@host [--dry-run]}"; shift || true
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
RSYNC=(rsync -az --info=progress2 --partial "$@"
  --exclude 'actas/plenaria-camara/' --exclude 'gacetas/*.pdf' --exclude 'analisis/'
  --exclude '*.bak' --exclude '__pycache__/' --exclude '.DS_Store')
"${RSYNC[@]}" "$REPO/Bases de datos/leyes-senado/" "$DEST:/srv/caudal/ricardoruiz.co/Bases de datos/leyes-senado/"
"${RSYNC[@]}" "$REPO/tools/caudal/alertas/datos/"  "$DEST:/srv/caudal/ricardoruiz.co/tools/caudal/alertas/datos/"
echo "estado sincronizado → $DEST"
