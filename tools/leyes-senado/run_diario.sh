#!/bin/bash
# Rastreo diario de proyectos de ley del Senado → Caudal (S3).
# Lo dispara launchd (co.ricardoruiz.leyes-diario) 1-2 veces al día.
#
#   harvest_diario.py       lista → detalle → PDF → texto → diff → novedades
#   build_diario_s3.py --upload   manifiesto + PDF + texto al bucket privado
#   harvest_ordenes.py todas      órdenes del día (14 comisiones + plenaria) →
#   build_bloqueo_s3.py           bloqueo.json → S3 (índice de agendamientos)
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
  echo "--- harvest Senado exit=$rc_h · build_diario_s3 --upload ---"
  python3 tools/leyes-senado/build_diario_s3.py --upload
  rc_u=$?
  echo "--- harvest Cámara (camara.gov.co) ---"
  python3 tools/leyes-senado/harvest_camara.py
  rc_c=$?
  echo "--- build_diario_camara_s3 --upload (resuelve+baja gacetas nuevas) ---"
  python3 tools/leyes-senado/build_diario_camara_s3.py --upload
  rc_cu=$?
  # Feed 'En vivo' de legislativo.html (en-vivo.json): top-5 por cámara. Va de
  # ÚLTIMO a propósito → las etapas de Cámara/Imprenta dan un respiro entre los
  # golpes al Senado (harvest_diario) y estos (esquiva el WAF). Sube solo aunque
  # no haya boto3 (cae al AWS CLI).
  echo "--- leyes_en_vivo --upload (feed 'En vivo' de legislativo.html) ---"
  python3 tools/leyes-senado/leyes_en_vivo.py --upload
  rc_ev=$?
  # Órdenes del día de Cámara (agenda de comisiones + plenaria) → índice de
  # bloqueo. Otro host (camara.gov.co/wp-json, sin WAF) y es incremental: los
  # PDF/TXT se cachean por evento, así que una corrida normal solo baja las
  # sesiones nuevas. Va al final: si falla, no arrastra al resto.
  echo "--- harvest_ordenes todas (órdenes del día: 14 comisiones + plenaria) ---"
  python3 tools/caudal/actas/harvest_ordenes.py todas \
    | grep -E "órdenes del día de|PDFs nuevos|^  !"
  rc_od=${PIPESTATUS[0]}
  echo "--- build_bloqueo_s3 + subida de bloqueo.json ---"
  python3 tools/caudal/actas/build_bloqueo_s3.py
  rc_bl=$?
  if [ $rc_bl -eq 0 ]; then
    aws s3 cp "$REPO/Bases de datos/leyes-senado/actas/bloqueo.json" \
      "s3://caudal-legislativo/metadata/bloqueo.json" \
      --content-type "application/json" --cache-control "private, max-age=300"
    rc_bu=$?
  else
    rc_bu=skip
  fi
  echo "═════════ fin $(date '+%H:%M:%S') · senado=$rc_h upload=$rc_u camara=$rc_c camara_up=$rc_cu envivo=$rc_ev ordenes=$rc_od bloqueo=$rc_bl bloqueo_up=$rc_bu ═════════"
} >> "$LOG" 2>&1
