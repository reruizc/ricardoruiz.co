#!/bin/bash
# Rastreo diario de proyectos de ley del Senado → Caudal (S3).
# Lo dispara launchd (co.ricardoruiz.leyes-diario) 1-2 veces al día.
#
#   harvest_diario.py       lista → detalle → PDF → texto → diff → novedades
#   build_diario_s3.py --upload   manifiesto + PDF + texto al bucket privado
#
# launchd corre con un entorno mínimo → fijamos PATH (aws y python3 viven en
# /opt/homebrew/bin) y HOME lo pone launchd (para que aws lea ~/.aws/credentials).
# Ritmo lento embebido en harvest_diario esquiva el WAF; una corrida diaria
# baja SOLO los PDFs nuevos, así que reintentos suaves no reactivan el ban.

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
REPO="/Users/ricardoruiz/ricardoruiz.co"
LOG="$REPO/Bases de datos/leyes-senado/diario/cron.log"

cd "$REPO" || { echo "no pude cd a $REPO" >&2; exit 1; }

{
  echo ""
  echo "═════════ $(date '+%Y-%m-%d %H:%M:%S %z') · run_diario ═════════"
  python3 tools/leyes-senado/harvest_diario.py
  rc_h=$?
  echo "--- harvest exit=$rc_h · build_diario_s3 --upload ---"
  python3 tools/leyes-senado/build_diario_s3.py --upload
  rc_u=$?
  echo "═════════ fin $(date '+%H:%M:%S') · harvest=$rc_h upload=$rc_u ═════════"
} >> "$LOG" 2>&1
