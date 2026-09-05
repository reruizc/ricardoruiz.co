#!/bin/bash
# Fase 0 · ¿la IP de AWS pasa el WAF de leyes.senado.gov.co?
# Corre SOLO el rastreo del Senado, SIN subir nada a S3, y resume qué pasó.
# Se corre en la instancia 3-4 días (a mano o con un cron temporal) mientras
# la Mac sigue siendo la que publica. Compara después con la Mac:
#   diff <(jq -S . novedades-AAAA-MM-DD.json) en las dos máquinas.
set -uo pipefail
REPO="${CAUDAL_REPO:-/srv/caudal/ricardoruiz.co}"
LOG="$REPO/Bases de datos/leyes-senado/diario/piloto-waf.log"
echo "═══ piloto $(date '+%F %T') · IP pública $(curl -s -m 10 https://checkip.amazonaws.com || echo '?')" | tee -a "$LOG"
t0=$(date +%s)
CAUDAL_REPO="$REPO" python3 "$REPO/tools/leyes-senado/harvest_diario.py" 2>&1 | tee /tmp/piloto-run.log | tail -20
rc=${PIPESTATUS[0]}
echo "rc=$rc · $(( $(date +%s) - t0 )) s · 403: $(grep -c ' 403' /tmp/piloto-run.log) · timeouts: $(grep -ci 'timeout\|timed out' /tmp/piloto-run.log) · fichas: $(grep -ci 'detalle' /tmp/piloto-run.log)" | tee -a "$LOG"
# lo que el rastreo vio hoy, para compararlo con la Mac
ls -la "$REPO/Bases de datos/leyes-senado/diario/"novedades-$(date +%F).* 2>/dev/null | tee -a "$LOG" || echo "sin novedades-$(date +%F) (o el rastreo no llegó al diff)" | tee -a "$LOG"
