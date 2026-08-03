#!/bin/bash
# Rastreo diario de Caudal → S3. Lo dispara launchd (co.ricardoruiz.leyes-diario)
# a las 08:00 y 19:30.
#
# Etapas, en orden (los nombres son ESTABLES: estado.json y el alertador los usan
# como llave — si renombras una, avisa):
#
#   senado_radicados          harvest_diario.py           lista → detalle → PDF → texto → diff
#   senado_upload             build_diario_s3.py          manifiesto + PDF + texto al bucket privado
#   camara_radicados          harvest_camara.py           lo mismo del lado Cámara
#   camara_upload             build_diario_camara_s3.py   resuelve y baja gacetas nuevas
#   en_vivo                   leyes_en_vivo.py            feed "En vivo" de legislativo.html
#   ritmo                     build_ritmo.py              monitor de ritmo de radicación
#   ordenes_camara            harvest_ordenes.py          órdenes del día: 14 comisiones + plenaria
#   ordenes_senado_indice     harvest_ordenes_senado.py   refresca el índice DOCman + plenaria
#   ordenes_senado_comisiones   ídem `buenas`             Cuarta/Quinta/Sexta
#   ordenes_senado_plenaria     ídem `plenaria`           secretariasenado.gov.co
#   secop_fetch/build/upload  harvest_secop.py            agregados de SECOP II
#   bloqueo_build/upload      build_bloqueo_s3.py         índice de agendamientos
#   camara_fichas             harvest_camara_fichas.py    fechas de radicación y debate
#   dataset_build             build_dataset.py            histórico + legislatura viva
#   texto_index               build_texto_index.py        articulado buscable (incl. lo vivo)
#   dataset_upload_*          aws s3 cp                   dist/ → metadata/
#   salud                     tools/caudal/salud/check.py frescura en S3 + ping a la Lambda
#
# Tres cosas que este script garantiza y que antes no:
#   · una sola corrida a la vez (candado). Dos corridas en paralelo contra
#     leyes.senado.gov.co son un ban del WAF asegurado, y launchd puede disparar
#     la corrida perdida al despertar el Mac justo encima de la programada.
#   · una etapa caída NO arrastra a las siguientes. Las únicas dependencias son
#     explícitas: no se sube lo que no se construyó, y no se insiste contra un
#     host que acaba de fallar.
#   · queda constancia. Cada etapa se corre a través de `salud/etapa.py`, que le
#     pone timeout y anota rc/duración; al final `salud/check.py` junta eso con
#     la frescura de S3 y el estado de la Lambda en `diario/estado.json`.
#
# launchd corre con un entorno mínimo → fijamos PATH (aws y python3 viven en
# /opt/homebrew/bin) y HOME lo pone launchd (para que aws lea ~/.aws/credentials).
# El ritmo lento embebido en harvest_diario esquiva el WAF; una corrida diaria
# baja SOLO los PDFs nuevos, así que reintentos suaves no reactivan el ban.

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
REPO="/Users/ricardoruiz/ricardoruiz.co"
DIARIO="$REPO/Bases de datos/leyes-senado/diario"
LOG="$DIARIO/cron.log"
LOCK="$DIARIO/.run_diario.lock"
REG="$DIARIO/.etapas.jsonl"
ESTADO="$DIARIO/estado.json"

# Tope de la corrida entera. Con dos disparos separados 11,5 h, una corrida que
# pase de 4 h ya es una corrida colgada: las etapas que falten se omiten y se
# registran como tal, en vez de solaparse con la siguiente.
TOPE_HORAS=4

cd "$REPO" || { echo "run_diario: no pude cd a $REPO" >&2; exit 1; }
mkdir -p "$DIARIO"

# Secretos FUERA del repo (este repo es público). Hoy solo se usa para
# SOCRATA_APP_TOKEN: sin él, harvest_secop corre con el rate limit anónimo de
# datos.gov.co. Para activarlo basta crear ~/.caudal.env con:
#     export SOCRATA_APP_TOKEN=xxxxxxxx
# El harvester ya lo lee del entorno (`os.environ.get('SOCRATA_APP_TOKEN','')`),
# así que no hay que tocar código. Si el archivo no existe, no pasa nada.
# shellcheck source=/dev/null
[ -f "$HOME/.caudal.env" ] && . "$HOME/.caudal.env"

# ── candado: una corrida a la vez ────────────────────────────────────────────
# mkdir es atómico en cualquier FS; si el candado quedó de una corrida que se
# murió sin limpiar (kill -9, reinicio), se comprueba el PID y se lo roba.
if ! mkdir "$LOCK" 2>/dev/null; then
  otro=$(cat "$LOCK/pid" 2>/dev/null)
  if [ -n "$otro" ] && kill -0 "$otro" 2>/dev/null; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') · run_diario: ya hay una corrida viva (pid $otro), me salgo" >> "$LOG"
    exit 0
  fi
  echo "$(date '+%Y-%m-%d %H:%M:%S') · run_diario: candado huérfano (pid ${otro:-?}), lo reclamo" >> "$LOG"
  rm -rf "$LOCK"
  mkdir "$LOCK" || { echo "run_diario: no pude tomar el candado" >> "$LOG"; exit 1; }
fi
echo $$ > "$LOCK/pid"
trap 'rm -rf "$LOCK"' EXIT INT TERM

# ── rotación del log ─────────────────────────────────────────────────────────
# cron.log crecía sin techo (iba por 340 KB y sube ~50 KB por corrida). El disco
# de este Mac está apretado; se guarda una vuelta anterior y nada más.
MAX_LOG=$((20 * 1024 * 1024))
tam=$(stat -f%z "$LOG" 2>/dev/null || stat -c%s "$LOG" 2>/dev/null || echo 0)   # BSD || GNU
[ "$tam" -gt "$MAX_LOG" ] && mv -f "$LOG" "$LOG.1"

: > "$REG"                                   # el registro es de ESTA corrida
DEADLINE=$(( $(date +%s) + TOPE_HORAS * 3600 ))
etapa() { python3 "$REPO/tools/caudal/salud/etapa.py" --reg "$REG" --deadline "$DEADLINE" "$@"; }

{
  echo ""
  echo "═════════ $(date '+%Y-%m-%d %H:%M:%S %z') · run_diario (pid $$) ═════════"

  # ── radicados · Senado (leyes.senado.gov.co · el host con WAF) ──
  etapa --nombre senado_radicados --critica --timeout 2700 \
        --desc "radicados del Senado (lista → detalle → PDF → texto)" \
        -- python3 tools/leyes-senado/harvest_diario.py

  # Se sube aunque el harvest haya fallado a medias: el manifiesto se arma con
  # lo que YA está en disco, así que una cosecha parcial igual llega al cliente.
  etapa --nombre senado_upload --critica --timeout 1800 \
        --desc "manifiesto + PDF + texto de Senado a S3" \
        -- python3 tools/leyes-senado/build_diario_s3.py --upload

  # ── radicados · Cámara (camara.gov.co · otro host, sin WAF) ──
  etapa --nombre camara_radicados --critica --timeout 1800 \
        --desc "radicados de Cámara" \
        -- python3 tools/leyes-senado/harvest_camara.py

  etapa --nombre camara_upload --critica --timeout 2400 \
        --desc "manifiesto de Cámara a S3 (resuelve y baja gacetas nuevas)" \
        -- python3 tools/leyes-senado/build_diario_camara_s3.py --upload

  # ── feed público "En vivo" ──
  # Va acá a propósito: las etapas de Cámara/Imprenta dan un respiro entre los
  # golpes al Senado (harvest_diario) y este. Sube igual sin boto3 (cae al CLI).
  etapa --nombre en_vivo --timeout 1500 \
        --desc "feed 'En vivo' de legislativo.html" \
        -- python3 tools/leyes-senado/leyes_en_vivo.py --upload

  # ── monitor de ritmo (2026 vs 2022 vs 2018) ──
  # Después del feed: así ya se refrescó el manifiesto de radicados del día.
  etapa --nombre ritmo --timeout 1200 \
        --desc "monitor de ritmo de radicación" \
        -- python3 tools/leyes-senado/build_ritmo.py --upload

  # ── órdenes del día · Cámara (wp-json, incremental) ──
  etapa --nombre ordenes_camara --timeout 3000 \
        --desc "órdenes del día de Cámara (14 comisiones + plenaria)" \
        --filtro "órdenes del día de|PDFs nuevos|^  !" \
        -- python3 tools/caudal/actas/harvest_ordenes.py todas

  # ── órdenes del día · Senado ──
  # --actualizar-indice es obligatorio en el cron: sin él el índice cacheado hace
  # que la corrida NUNCA vea una sesión nueva. Refresca los dos listados
  # (comisiones en senado.gov.co, plenaria en secretariasenado.gov.co).
  etapa --nombre ordenes_senado_indice --timeout 2100 \
        --desc "refresco del índice DOCman (comisiones + plenaria)" \
        -- python3 tools/caudal/actas/harvest_ordenes_senado.py --actualizar-indice
  rc_idx=$?

  # Si el índice falló, saltamos las COMISIONES: viven en el mismo host que
  # acaba de fallar, e insistir solo suma minutos de timeouts. La PLENARIA sí
  # corre — es otro host (secretariasenado.gov.co) y puede estar perfecta.
  if [ $rc_idx -eq 0 ]; then
    etapa --nombre ordenes_senado_comisiones --timeout 3000 \
          --desc "órdenes del día · Cuarta/Quinta/Sexta" \
          --filtro "órdenes del día de|descargas nuevas|^  !" \
          -- python3 tools/caudal/actas/harvest_ordenes_senado.py buenas --workers 4
  else
    etapa --nombre ordenes_senado_comisiones \
          --omitida "el índice de senado.gov.co falló (rc=$rc_idx); insistir contra el mismo host solo suma timeouts"
  fi

  etapa --nombre ordenes_senado_plenaria --timeout 2400 \
        --desc "órdenes del día · plenaria de Senado" \
        --filtro "órdenes del día de|descargas nuevas|^  !" \
        -- python3 tools/caudal/actas/harvest_ordenes_senado.py plenaria --workers 4

  # ── SECOP II (datos.gov.co · fuente diaria) ──
  # `fetch` sin --force se salta lo que ya bajó hoy → la segunda corrida del día
  # no le vuelve a pegar a Socrata.
  etapa --nombre secop_fetch --timeout 1800 \
        --desc "agregados de SECOP II (Socrata)" \
        -- python3 tools/caudal/secop/harvest_secop.py fetch

  # `build` corre aunque `fetch` falle: reconstruye desde el raw cacheado, que es
  # mejor que dejar el landing sin nada.
  etapa --nombre secop_build --timeout 900 \
        --desc "secop-stats.json desde el raw" \
        -- python3 tools/caudal/secop/harvest_secop.py build
  rc_secop=$?

  if [ $rc_secop -eq 0 ]; then
    etapa --nombre secop_upload --timeout 600 --desc "secop-stats.json → S3" \
          -- aws s3 cp "$REPO/Bases de datos/leyes-senado/secop/dist/s3/secop-stats.json" \
             "s3://caudal-legislativo/metadata/secop-stats.json" \
             --content-type "application/json" --cache-control "private, max-age=300"
  else
    etapa --nombre secop_upload --omitida "el build falló (rc=$rc_secop): no hay archivo nuevo que subir"
  fi

  # ── índice de bloqueo (agendamientos de las dos cámaras) ──
  etapa --nombre bloqueo_build --timeout 1200 \
        --desc "bloqueo.json desde las órdenes del día" \
        -- python3 tools/caudal/actas/build_bloqueo_s3.py
  rc_bloq=$?

  if [ $rc_bloq -eq 0 ]; then
    etapa --nombre bloqueo_upload --timeout 600 --desc "bloqueo.json → S3" \
          -- aws s3 cp "$REPO/Bases de datos/leyes-senado/actas/bloqueo.json" \
             "s3://caudal-legislativo/metadata/bloqueo.json" \
             --content-type "application/json" --cache-control "private, max-age=300"
  else
    etapa --nombre bloqueo_upload --omitida "el build falló (rc=$rc_bloq): no hay archivo nuevo que subir"
  fi

  # ── fichas individuales de Cámara (la fecha de radicación) ──
  # Incremental de verdad: cachea por proyecto, así que en una corrida normal
  # baja solo los radicados del día. Es el único sitio donde Cámara publica la
  # fecha — sin esto sus proyectos entran al dataset sin fecha y quedan fuera
  # del embudo (ver harvest_camara_fichas.py).
  etapa --nombre camara_fichas --timeout 2400 \
        --desc "fichas individuales de Cámara (fechas de radicación y debate)" \
        --filtro "objetivo|descarga|fecha de radicación|^  !" \
        -- python3 tools/leyes-senado/harvest_camara_fichas.py --workers 6

  # ── dataset + índice de texto (la legislatura viva entra al producto) ──
  # Sin estas dos etapas el rastreo diario llegaba a S3 como manifiesto suelto
  # pero NO al dataset: medido el 2026-08-02, pdly.jsonl se cortaba en el id 9923
  # con cero proyectos de 2026-2027 mientras el cron ya tenía 139 de Senado y 71
  # de Cámara. O sea: lo que se está debatiendo hoy no se podía buscar. Ahora
  # build_dataset los absorbe (lee diario/ y diario-camara/, sin volver a la red)
  # y build_texto_index indexa su articulado desde el .txt que ya está en disco.
  etapa --nombre dataset_build --timeout 1200 \
        --desc "dataset (histórico + legislatura viva)" \
        -- python3 tools/leyes-senado/build_dataset.py
  rc_ds=$?

  if [ $rc_ds -eq 0 ]; then
    # --incremental reusa las palabras ya extraídas por gaceta (el caché) y solo
    # paga red por lo nuevo; los radicados se releen siempre (son locales y
    # cambian mientras el proyecto se mueve).
    etapa --nombre texto_index --timeout 1800 \
          --desc "índice de texto (gacetas + radicados vivos)" \
          -- python3 tools/caudal/build_texto_index.py --incremental

    for f in proyectos.jsonl actos-legis.jsonl indice.json stats.json texto-index.json; do
      etapa --nombre "dataset_upload_${f%%.*}" --timeout 900 --desc "$f → S3" \
            -- aws s3 cp "$REPO/Bases de datos/leyes-senado/dist/$f" \
               "s3://caudal-legislativo/metadata/$f" \
               --cache-control "private, max-age=300"
    done
  else
    etapa --nombre texto_index --omitida "el dataset falló (rc=$rc_ds): indexar sobre un dataset roto sería peor que no indexar"
    etapa --nombre dataset_upload --omitida "el dataset falló (rc=$rc_ds): no hay archivo nuevo que subir"
  fi

  # ── chequeo de salud ──
  # Fuera del registro de etapas a propósito: es el que JUZGA la corrida, no una
  # etapa más. Escribe diario/estado.json (frescura de S3 + ping a la Lambda +
  # el detalle de estas etapas). Su rc: 0 ok · 1 aviso · 2 error · 3 se rompió.
  echo "--- salud: frescura en S3 + ping a la Lambda ---"
  python3 tools/caudal/salud/check.py --etapas "$REG" --out "$ESTADO"
  rc_salud=$?

  # Resumen final sin red: si el chequeo de salud no pudo correr, esta línea es
  # lo único que queda, y tiene que decir QUÉ falló, no cuántas fallaron.
  python3 - "$REG" <<'PY'
import json, sys
fall, omit, lentas = [], [], []
try:
    lineas = open(sys.argv[1], encoding='utf-8').read().split('\n')
except Exception as e:
    print(f'· no pude leer el registro de etapas: {e}'); raise SystemExit(0)
for ln in lineas:
    if not ln.strip():
        continue
    try:
        r = json.loads(ln)
    except Exception:
        continue
    n = r.get('nombre', '?')
    if r.get('estado') == 'error':
        fall.append(f'{n} ({r.get("motivo") or "rc=" + str(r.get("rc"))})')
    elif r.get('estado') == 'omitida':
        omit.append(n)
    if (r.get('duracion_s') or 0) > 900:
        lentas.append(f'{n} {r["duracion_s"]:.0f}s')
print('· FALLARON : ' + ('; '.join(fall) if fall else 'ninguna'))
print('· OMITIDAS : ' + (', '.join(omit) if omit else 'ninguna'))
if lentas:
    print('· lentas   : ' + ', '.join(lentas))
PY

  echo "═════════ fin $(date '+%H:%M:%S') · salud=$rc_salud (0 ok · 1 aviso · 2 error · 3 el chequeo se rompió) ═════════"
} >> "$LOG" 2>&1
