#!/bin/bash
# Fase 0 EXPRESS · ¿esta IP pasa los dos WAF? Corre igual en la Mac y en la EC2,
# así que la comparación es del mismo momento y contra el mismo servidor.
#
#   bash tools/caudal/ec2/sondeo-waf.sh            # sondeo base (~2 min)
#   bash tools/caudal/ec2/sondeo-waf.sh rafaga 150 # ¿a las cuántas peticiones banea?
#
# En la EC2, sin llave SSH, va por SSM:
#   B64=$(base64 < tools/caudal/ec2/sondeo-waf.sh | tr -d '\n')
#   aws ssm send-command --region us-east-1 --instance-ids <id> \
#     --document-name AWS-RunShellScript --timeout-seconds 900 \
#     --parameters "commands=[\"echo $B64 | base64 -d > /tmp/s.sh\",\"bash /tmp/s.sh\"]"
#
# ⚠ El juego COMPLETO de headers es obligatorio para el BanRep. Probarlo solo con
# -A da captcha siempre y parece un bloqueo de IP que no es (me pasó, 20-sep-2026).
set -uo pipefail
MODO="${1:-base}"
N="${2:-150}"
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
H=(-H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
   -H 'Accept-Language: es-CO,es;q=0.9,en;q=0.8'
   -H 'sec-ch-ua: "Chromium";v="126", "Not)A;Brand";v="24"'
   -H 'sec-ch-ua-mobile: ?0' -H 'sec-ch-ua-platform: "macOS"'
   -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate'
   -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-User: ?1'
   -H 'Upgrade-Insecure-Requests: 1')
SEN='https://leyes.senado.gov.co'
BAN='https://www.banrep.gov.co/es/normatividad/regulacion-operaciones-cambiarias/compendios-dcin-83-dcip-83'
echo "IP: $(curl -s -m 10 https://checkip.amazonaws.com || echo '?')  ·  $(date '+%F %H:%M:%S')"

if [ "$MODO" = "rafaga" ]; then
  # El WAF del Senado no castiga la petición suelta sino el VOLUMEN acumulado, y
  # cuenta a través de corridas: dos ráfagas pegadas suman. Replica el ritmo del
  # harvester (DELAY_META=3 s) sin necesitar el repo.
  echo "--- ráfaga de $N peticiones a 3 s (ritmo del harvester) ---"
  ids=$(curl -s -m 45 -X POST -A "$UA" --data-urlencode 'legislatura=2026-2027' \
        "$SEN/api/search_pdly.php" | tr ',' '\n' | grep -o '"id":[0-9]*' | cut -d: -f2 | head -60)
  [ -z "$ids" ] && { echo "  ! no pude traer la lista: o no hay red o ya estamos baneados"; exit 1; }
  n=0; ok=0; vacias=0; t0=$(date +%s)
  while [ $n -lt "$N" ]; do
    for id in $ids; do
      [ $n -ge "$N" ] && break
      n=$((n+1))
      b=$(curl -s -m 25 -A "$UA" "$SEN/api/get_detalle_pdly.php?id=$id" 2>/dev/null); rc=$?
      if [ $rc -ne 0 ] || [ ${#b} -lt 200 ]; then
        vacias=$((vacias+1))
        echo "  ! pet $n SIN RESPUESTA (rc=$rc len=${#b}) a los $(( $(date +%s) - t0 ))s"
        [ $vacias -ge 3 ] && { echo "  >> 3 seguidas: es el ban (rc=52 = 'Empty reply')."; break 2; }
      else ok=$((ok+1)); vacias=0; fi
      [ $((n % 40)) -eq 0 ] && echo "  · $n peticiones · $(( $(date +%s) - t0 ))s · ok=$ok"
      sleep 3
    done
  done
  echo "RESUMEN ráfaga: $n peticiones en $(( $(date +%s) - t0 ))s · ok=$ok"
  exit 0
fi

echo "--- leyes.senado.gov.co ---"
for i in 1 2 3 4; do
  echo "  home $i: $(curl -s -o /dev/null -m 30 -A "$UA" -w '%{http_code} %{size_download} %{time_total}s' "$SEN/" || echo "rc=$?")"
  sleep 4
done
tmp=$(mktemp)
echo "  API lista: $(curl -s -m 45 -X POST -A "$UA" --data-urlencode 'legislatura=2026-2027' \
      -o "$tmp" -w '%{http_code} %{size_download}' "$SEN/api/search_pdly.php" || echo "rc=$?") · filas: $(grep -o '"id"' "$tmp" | wc -l | tr -d ' ')"
rm -f "$tmp"

echo "--- www.banrep.gov.co (Radware · el frasco de cookies es lo que lo pasa) ---"
JAR=$(mktemp)
for i in 1 2 3 4 5; do
  b=$(curl -sk -m 25 -A "$UA" --compressed -L -b "$JAR" -c "$JAR" "${H[@]}" "$BAN" 2>/dev/null); rc=$?
  if [ $rc -ne 0 ]; then echo "  hist $i: timeout(rc=$rc)"
  elif [ ${#b} -lt 40000 ] && echo "$b" | head -c 4000 | grep -qi perfdrive; then echo "  hist $i: CAPTCHA (${#b} b)"
  else echo "  hist $i: ok (${#b} b)"; fi
  sleep 6
done
rm -f "$JAR"
