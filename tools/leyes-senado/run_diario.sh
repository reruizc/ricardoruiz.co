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
#   ejecutivo_*               harvest_decretos.py         normativa de Presidencia (Socrata) → S3
#   temas_*                   build_temas.py              temas del momento (chips de la búsqueda) → S3 público
#   ordenes_camara            harvest_ordenes.py          órdenes del día: 14 comisiones + plenaria
#   ordenes_senado_indice     harvest_ordenes_senado.py   refresca el índice DOCman + plenaria
#   ordenes_senado_comisiones   ídem `buenas`             Cuarta/Quinta/Sexta
#   ordenes_senado_plenaria     ídem `plenaria`           secretariasenado.gov.co
#   secop_fetch/build/upload  harvest_secop.py            agregados de SECOP II
#   red_lista                 salud/espera_red.py         ¿esta máquina tiene red? (el Mac despierta tarde)
#   sucop_fetch/build/upload_*  harvest_sucop.py          consulta pública de normas (el dato que VENCE)
#   bloqueo_build/upload      build_bloqueo_s3.py         índice de agendamientos
#   citaciones_extrae/build/upload  harvest_citaciones.py  control político por congresista
#   camara_fichas             harvest_camara_fichas.py    fechas de radicación y debate
#   dataset_build             build_dataset.py            histórico + legislatura viva
#   texto_index               build_texto_index.py        articulado buscable (incl. lo vivo)
#   dataset_upload_*          aws s3 cp                   dist/ → metadata/
#   ritmo                     build_ritmo.py              monitor de ritmo (lee dist, va tras el dataset)
#   anla_fetch/build          harvest_anla.py             Gaceta Ambiental (pilar Regulatorio)
#   supers_consolida          harvest_supers.py normalize las 12 fuentes del pilar en un dataset
#   supers_build_s3           build_s3.py                 el slim que lee la Lambda
#   supers_verifica           verificar_consolidado.py    piso por fuente ANTES de publicar
#   supers_upload_*           aws s3 cp                   dist/s3/ → metadata/
#   salud                     tools/caudal/salud/check.py frescura en S3 + ping a la Lambda
#   (publicar, no es etapa)   tools/caudal/salud/latido.py  estado.json → S3 privado + latido → S3 público
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
# launchd y systemd corren con un entorno mínimo → fijamos PATH. `CAUDAL_REPO`
# permite usar exactamente este mismo runner en una máquina remota sin rutas de
# macOS; si no viene definida, se deriva desde la ubicación del script.
# El ritmo lento embebido en harvest_diario esquiva el WAF; una corrida diaria
# baja SOLO los PDFs nuevos, así que reintentos suaves no reactivan el ban.

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO="${CAUDAL_REPO:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
DIARIO="$REPO/Bases de datos/leyes-senado/diario"
LOG="$DIARIO/cron.log"
LOCK="$DIARIO/.run_diario.lock"
REG="$DIARIO/.etapas.jsonl"
ESTADO="$DIARIO/estado.json"
LATIDO="$DIARIO/latido.json"

# A dónde se publica el estado. El completo va al bucket PRIVADO (lleva llaves del
# bucket y el detalle de la Lambda); el latido reducido, al prefijo público que ya
# cubre la bucket policy, porque su lector —el vigilante del worker rr-auth— no
# tiene credenciales de AWS. Ver tools/caudal/salud/latido.py.
S3_ESTADO="s3://caudal-legislativo/metadata/estado.json"
S3_LATIDO="s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/legislativo/caudal-latido.json"

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

# El registro es de ESTA corrida, pero el de la anterior se guarda antes de
# truncarlo: cuando una etapa falla de madrugada, su motivo y sus últimas líneas
# viven acá en forma leíble por máquina, y truncar sin más se las llevaba a la
# mañana siguiente, justo cuando alguien iba a mirarlas. Mismo patrón que el
# rotado del log de arriba. Nadie lee el `.1`: está para el humano que llega tarde.
[ -s "$REG" ] && cp -f "$REG" "$REG.1"
: > "$REG"
INICIO=$(date -u +%Y-%m-%dT%H:%M:%SZ)       # para saber si estado.json es de esta corrida
DEADLINE=$(( $(date +%s) + TOPE_HORAS * 3600 ))
# ── qué etapas corre ESTA máquina ───────────────────────────────────────────
# Fase 1 de la migración (20-sep-2026): el pipeline vive en dos sitios. La EC2
# corre las 58 etapas sin WAF y el Mac se queda con las 2 que sí lo tienen
# (senado_radicados y banrep_fetch, medido en la Fase 0 del piloto).
#
#   CAUDAL_ETAPAS=""                → todas (lo de siempre; es el default)
#   CAUDAL_ETAPAS="senado_*,banrep_fetch"   → solo esas
#   CAUDAL_ETAPAS="!senado_*,!banrep_fetch" → todas MENOS esas
#
# Una etapa que no le toca a esta máquina NO se registra: así el estado.json de
# cada una habla solo de su trabajo, en vez de llenarse de 58 «omitidas» que
# dirían que algo se saltó cuando en realidad lo corrió la otra máquina.
CAUDAL_ETAPAS="${CAUDAL_ETAPAS:-}"

# ¿Esta máquina publica el estado y el latido? En Fase 1 SOLO uno de los dos
# sitios debe hacerlo, o se pisan el mismo objeto de S3 y el vigilante lee una
# corrida a medias creyendo que es toda.
#
# Lo publica el MAC, y no es arbitrario: `check.py` no juzga solo las etapas que
# corrieron acá, también mide la FRESCURA de los 31 archivos de S3 — incluidos
# los que sube la EC2. Así que el latido del Mac vigila el producto entero: si la
# EC2 deja de subir en-vivo.json o ritmo-legislaturas.json, esos archivos
# envejecen y el Mac lo reporta. Cero cambios en el worker rr-auth.
# La EC2 igual escribe su estado.json local, que es lo que se mira al depurarla.
CAUDAL_PUBLICA="${CAUDAL_PUBLICA:-si}"
_le_toca() {                      # $1 = nombre de la etapa
  [ -z "$CAUDAL_ETAPAS" ] && return 0
  local n="$1" pat hay_pos=0 casa=0 excluida=0 reglob=0 r=0
  # ⚠ `for pat in $VAR` hace word splitting (lo que queremos) pero TAMBIÉN
  # expansión de rutas: con CAUDAL_ETAPAS='*' el patrón se expandía contra los
  # archivos del repo —run_diario hace `cd $REPO`— y dejaba de casar nada. Lo
  # cazó prueba-selector-etapas.sh. De ahí el noglob, y el único `return` al
  # final: saliendo desde dentro del bucle, el `set +f` no se ejecutaba.
  case $- in *f*) ;; *) reglob=1; set -f;; esac
  local IFS=','
  for pat in $CAUDAL_ETAPAS; do
    pat="${pat#"${pat%%[![:space:]]*}"}"; pat="${pat%"${pat##*[![:space:]]}"}"
    [ -z "$pat" ] && continue
    if [ "${pat#!}" != "$pat" ]; then
      # shellcheck disable=SC2254
      case "$n" in ${pat#!}) excluida=1;; esac
    else
      hay_pos=1
      # shellcheck disable=SC2254
      case "$n" in $pat) casa=1;; esac
    fi
  done
  [ "$reglob" = 1 ] && set +f
  if [ "$excluida" = 1 ]; then r=1                 # una exclusión manda sobre todo
  elif [ "$hay_pos" = 1 ] && [ "$casa" = 0 ]; then r=1
  fi
  return $r
}

etapa() {
  local nombre="" i=1
  # el nombre viene como `--nombre X`; se busca sin consumir el resto de args
  for arg in "$@"; do
    [ "$arg" = "--nombre" ] && { eval "nombre=\${$((i+1))}"; break; }
    i=$((i+1))
  done
  if [ -n "$nombre" ] && ! _le_toca "$nombre"; then
    return 0
  fi
  python3 "$REPO/tools/caudal/salud/etapa.py" --reg "$REG" --deadline "$DEADLINE" "$@"
}

{
  echo ""
  echo "═════════ $(date '+%Y-%m-%d %H:%M:%S %z') · run_diario (pid $$) ═════════"

  # ── ¿hay red? ────────────────────────────────────────────────────────────
  # 8 de 114 corridas del log (7 %) arrancaron SIN red, y 6 de esas 8 son de la
  # mañana: launchd dispara a las 8:00 con el Mac todavía despertando. No es un
  # fallo de ninguna fuente, pero se reportaba como si lo fuera y por triplicado
  # —sucop con `curl rc=6`, secop_upload sin poder hablar con S3, los manifiestos
  # sin subir—. El 11-sep dejó 38 «Could not connect to the endpoint URL».
  # Espera hasta ~5 min a que vuelva; si no vuelve, no tiene sentido correr 60
  # etapas que van a fallar todas. Ver tools/caudal/salud/espera_red.py.
  # 480: las esperas suman 245 s y los sondeos hasta 128 más (ver espera_red.py).
  etapa --nombre red_lista --critica --timeout 480 \
        --desc "¿hay red? (launchd dispara con el Mac despertando)" \
        -- python3 tools/caudal/salud/espera_red.py
  rc_red=$?
  if [ $rc_red -ne 0 ]; then
    echo "═════════ fin $(date '+%H:%M:%S') · sin red: corrida abortada antes de empezar ═════════"
    exit 0
  fi

  # ── radicados · Senado (leyes.senado.gov.co · el host con WAF) ──
  # El WAF corta a los ~11 min de actividad (~85 peticiones) y suelta en ≤10, así
  # que cada ventana da ~80 fichas. Medido en 5 corridas, el throughput efectivo
  # (ya contando los castigos) es de 3,3 a 5,0 fichas/min: las 254 de hoy piden
  # entre 3.050 y 4.620 s. Con 3700 salía parcial (rc=75) SIEMPRE.
  #
  # 5700 y --reserva 3600 (20-sep-2026). El harvester ya no lleva su presupuesto
  # escrito a mano: lo deriva del tope que etapa.py le pasa, que es este --timeout
  # recortado por lo que quede del deadline global menos la reserva. La reserva
  # son 60 min para las otras 59 etapas, que en corridas normales tardan 22-40
  # min; senado_radicados es la PRIMERA de la fila y sin ese freno podía estirarse
  # hasta el tope de 4 h y dejarlas a todas sin correr.
  #
  # --rc-aviso 75: la corrida parcial es degradación prevista, no falla. El
  # harvester conserva el dato anterior de lo que no alcanzó y lo pone primero en
  # la corrida siguiente, así que el ciclo se cierra igual. Si pasa de la mitad
  # sin refrescar sale con 1 (falla de verdad) y el vigilante sí avisa.
  # --minimo 2100: con menos de 35 min no alcanza ni para dos ventanas del WAF, y
  # una cosecha así de corta se reportaría como grave. Mejor omitirla y decirlo.
  etapa --nombre senado_radicados --critica --timeout 5700 --reserva 3600 \
        --minimo 2100 --rc-aviso 75 \
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

  # (el monitor de ritmo bajó a después de dataset_build: desde ago-2026 lee el
  #  dataset, no la Lambda, así que necesita el dist del día — ver allá abajo)

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

  # `ordenes-vigentes.json` ya NO se publica desde este cron: es propiedad de
  # ordenes_cloud.py en la Lambda leyes-en-vivo, disparada por GitHub Actions.
  # Evita que el Mac sobrescriba después un feed cloud más completo/fresco.

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

  # ── SUCOP (sucop.gov.co · consulta pública de normas) ──
  # La etapa MÁS importante de las baratas: es el único pilar cuyo dato vence.
  # Un `sucop.jsonl` de hace una semana no es "un poco viejo", es falso — las
  # consultas que decía abiertas ya cerraron. ~8 requests, ~100 s, host propio
  # (SharePoint del DNP) que no comparte WAF con leyes.senado.
  # `fetch` va SIN --reuse a propósito: --reuse salta las páginas que ya están en
  # disco, así que en una corrida diaria nunca vería un proceso nuevo.
  etapa --nombre sucop_fetch --timeout 900 \
        --desc "procesos de consulta pública (SharePoint DNP)" \
        -- python3 tools/caudal/sucop/harvest_sucop.py fetch
  rc_suc_f=$?

  etapa --nombre sucop_build --timeout 600 \
        --desc "sucop.jsonl + stats desde el raw" \
        -- python3 tools/caudal/sucop/harvest_sucop.py build
  rc_suc_b=$?

  # Se sube solo si la cosecha Y el build salieron bien. Si la fuente no
  # respondió, en S3 se queda el archivo de ayer y su antigüedad la delata en el
  # chequeo de salud; subir un rebuild del raw viejo lo dejaría pasando por
  # fresco, que en este pilar es peor que no subir nada.
  if [ $rc_suc_f -eq 0 ] && [ $rc_suc_b -eq 0 ]; then
    S3SUC="$REPO/Bases de datos/leyes-senado/sucop/dist"
    etapa --nombre sucop_upload_jsonl --timeout 600 --desc "sucop.jsonl → S3" \
          -- aws s3 cp "$S3SUC/sucop.jsonl" \
             "s3://caudal-legislativo/metadata/sucop.jsonl" \
             --content-type "application/json" --cache-control "private, max-age=300"
    etapa --nombre sucop_upload_stats --timeout 300 --desc "sucop-stats.json → S3" \
          -- aws s3 cp "$S3SUC/stats.json" \
             "s3://caudal-legislativo/metadata/sucop-stats.json" \
             --content-type "application/json" --cache-control "private, max-age=300"
  else
    etapa --nombre sucop_upload_jsonl \
          --omitida "cosecha rc=$rc_suc_f · build rc=$rc_suc_b: en S3 se queda el de ayer, y su antigüedad la reporta el chequeo de salud"
    etapa --nombre sucop_upload_stats --omitida "ídem"
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

  # ── citaciones de control político (mismo caché de órdenes del día) ──
  # Va DESPUÉS de las etapas de órdenes porque lee su caché; no toca la red, así
  # que es barato y no pelea con el WAF de leyes.senado.
  etapa --nombre citaciones_extrae --timeout 900 \
        --desc "citaciones de control político desde las órdenes del día" \
        -- python3 tools/caudal/actas/harvest_citaciones.py todas
  rc_cit=$?

  if [ $rc_cit -eq 0 ]; then
    etapa --nombre citaciones_build --timeout 600 \
          --desc "citaciones.json (por congresista)" \
          -- python3 tools/caudal/build_citaciones_s3.py
    rc_citb=$?
  else
    etapa --nombre citaciones_build --omitida "la extracción falló (rc=$rc_cit): no hay qué empaquetar"
    rc_citb=1
  fi

  if [ $rc_citb -eq 0 ]; then
    etapa --nombre citaciones_upload --timeout 600 --desc "citaciones.json → S3" \
          -- aws s3 cp "$REPO/Bases de datos/leyes-senado/dist/s3/citaciones.json" \
             "s3://caudal-legislativo/metadata/citaciones.json" \
             --content-type "application/json" --cache-control "private, max-age=300"
  else
    etapa --nombre citaciones_upload --omitida "el build falló (rc=$rc_citb): no hay archivo nuevo que subir"
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
    #
    # Timeout 2400 y no 1800: medido, la etapa tarda ~14 min y el grueso YA NO es
    # red sino CPU (leer el caché de 123 MB, invertir 8.170 documentos, escribir
    # 38 MB). Con 1800 se cortó en la primera corrida real (rc=124) porque además
    # reintentaba las ~2.200 gacetas sin texto en S3; eso lo arregla el caché de
    # negativos de build_texto_index. Si el corpus vuelve a crecer, medir antes
    # de bajar este número.
    etapa --nombre texto_index --timeout 2400 \
          --desc "índice de texto (gacetas + radicados vivos)" \
          -- python3 tools/caudal/build_texto_index.py --incremental

    for f in proyectos.jsonl actos-legis.jsonl indice.json stats.json texto-index.json; do
      etapa --nombre "dataset_upload_${f%%.*}" --timeout 900 --desc "$f → S3" \
            -- aws s3 cp "$REPO/Bases de datos/leyes-senado/dist/$f" \
               "s3://caudal-legislativo/metadata/$f" \
               --cache-control "private, max-age=300"
    done

    # ── monitor de ritmo (2026 vs 2022 vs 2018) ──
    # Va AQUÍ, y no arriba con el feed, porque desde ago-2026 las tres series
    # salen de dist/proyectos.jsonl (que ya incluye la legislatura viva de las
    # dos cámaras) en vez de la Lambda. Con un dist viejo publicaría una ventana
    # sin la Cámara del día; build_ritmo lo detecta y aborta, pero mejor no
    # llegar ahí. Su ventana cierra dos semanas atrás, así que no le urge la
    # frescura: le urge que el dataset esté bien construido.
    etapa --nombre ritmo --timeout 1200 \
          --desc "monitor de ritmo de radicación" \
          -- python3 tools/leyes-senado/build_ritmo.py --upload
  else
    etapa --nombre texto_index --omitida "el dataset falló (rc=$rc_ds): indexar sobre un dataset roto sería peor que no indexar"
    etapa --nombre dataset_upload --omitida "el dataset falló (rc=$rc_ds): no hay archivo nuevo que subir"
    etapa --nombre ritmo --omitida "el dataset falló (rc=$rc_ds): el monitor lee dist/proyectos.jsonl; con uno roto publicaría una comparación falsa"
  fi

  # ── pilar Regulatorio · Gaceta Ambiental de la ANLA ──
  # Va al final: es otro host (gaceta.anla.gov.co) y no compite con nada de lo
  # de arriba. `fetch` sin argumentos re-baja SOLO el año en curso (~185 páginas,
  # medido 38-46s con 4 workers); los slices cerrados llevan marker `_done`.
  etapa --nombre anla_fetch --timeout 900 \
        --desc "Gaceta Ambiental de la ANLA (año en curso)" \
        -- python3 tools/caudal/supers/harvest_anla.py fetch --workers 4

  # `build` corre aunque `fetch` falle: reconstruye desde las páginas cacheadas,
  # que es mejor que dejar el pilar sin refrescar. Medido ~4s con el memo del
  # cruce contra el diccionario de empresas caliente; ~350s la primera vez
  # después de que ese diccionario cambie (es de otro frente y crece seguido).
  etapa --nombre anla_build --timeout 1200 \
        --desc "anla-gaceta.json desde las páginas cacheadas" \
        -- python3 tools/caudal/supers/harvest_anla.py build
  rc_anla_b=$?

  # ── pilar Regulatorio · las cuatro fuentes NORMATIVAS (ago-2026) ──
  # No son sancionatorias: traen la norma que le crea obligaciones al cliente,
  # que para un gremio vale más que la multa que le pusieron a otro. Entran acá,
  # antes del consolidado, y cada una es OTRO host: ninguna compite con
  # leyes.senado ni entre sí.
  #
  # Las cuatro son incrementales y baratas; los ritmos están medidos:
  #   banrep  ~1 min  · la vista va DESC y para en la primera página ya vista
  #   dian    ~2 min  · resoluciones y circulares del año en curso
  #   uiaf    ~30 s   · 22 peticiones, el resto sale de caché
  #   supersoc ~90 pet· los nodos de proyecto quedan cacheados por URL
  #
  # Ninguna es crítica: si una cae, el consolidado sigue con su raw de ayer y el
  # piso de `verificar_consolidado.py` la respalda. Por eso no se guarda su rc.
  #
  # ⚠ La SIC (harvest_sic_circulares.py) queda FUERA a propósito: son ~800
  # peticiones (~21 min) para un registro que se mueve ~13 actos al año. Se
  # corre a mano cuando haga falta; meterla acá sería gastar 42 min diarios.
  # --rc-aviso 75: www.banrep.gov.co está detrás de Radware Bot Manager y tumba
  # una petición suelta cada tanto. Cuando eso pasa el harvester conserva la copia
  # en disco —los compendios cambiarios cambian cada años, no a diario— y sale
  # con 75. Si la copia pasa de 7 días sale con 1 y entonces sí es falla.
  etapa --nombre banrep_fetch --timeout 600 --rc-aviso 75 \
        --desc "BanRep · Junta Directiva y régimen cambiario (incremental)" \
        -- python3 tools/caudal/supers/harvest_banrep.py fetch

  etapa --nombre dian_fetch --timeout 900 \
        --desc "DIAN · resoluciones y circulares (incremental)" \
        -- python3 tools/caudal/supers/harvest_dian.py fetch

  etapa --nombre uiaf_fetch --timeout 600 \
        --desc "UIAF · obligaciones de reporte ALA/CFT" \
        -- python3 tools/caudal/supers/harvest_uiaf.py fetch

  # Supersociedades tiene dos colas y la que importa refrescar a diario es la de
  # PROYECTOS: sus ventanas de comentarios duran entre 4 y 15 días, así que un
  # rastreo semanal se perdería la mitad.
  etapa --nombre supersociedades_fetch --timeout 900 \
        --desc "Supersociedades · normativa y proyectos en consulta" \
        -- python3 tools/caudal/supers/harvest_supersociedades.py fetch

  # ⚠ `normalize` y `build_s3` consolidan las DOCE fuentes del pilar, no solo
  # ANLA: leen todos los `raw/*.json` que haya en disco. Eso es lo correcto (el
  # pilar es un solo dataset y la Lambda lee un solo archivo), pero significa
  # que una corrida desatendida puede publicar un consolidado al que le falte
  # una fuente si su raw se borró o quedó a medias — `normalize` la salta en
  # silencio. Por eso NO se sube nada sin pasar antes por
  # `verificar_consolidado.py`, que exige piso por fuente y coherencia con los
  # raw en disco. Si falla, en S3 se queda el archivo bueno del día anterior.
  if [ $rc_anla_b -eq 0 ]; then
    etapa --nombre supers_consolida --timeout 900 \
          --desc "consolidado de las 12 fuentes del pilar Regulatorio" \
          -- python3 tools/caudal/supers/harvest_supers.py normalize
    rc_norm=$?
  else
    etapa --nombre supers_consolida \
          --omitida "el build de ANLA falló (rc=$rc_anla_b): consolidar sobre un raw a medias arriesga publicar un pilar mutilado"
    rc_norm=1
  fi

  if [ $rc_norm -eq 0 ]; then
    etapa --nombre supers_build_s3 --timeout 600 \
          --desc "sanciones.jsonl + stats para la Lambda" \
          -- python3 tools/caudal/supers/build_s3.py
    rc_bs3=$?
  else
    etapa --nombre supers_build_s3 --omitida "la consolidación falló (rc=$rc_norm): no hay qué empaquetar"
    rc_bs3=1
  fi

  if [ $rc_bs3 -eq 0 ]; then
    etapa --nombre supers_verifica --timeout 300 \
          --desc "¿el consolidado está completo? (piso por fuente)" \
          -- python3 tools/caudal/supers/verificar_consolidado.py
    rc_ver=$?
  else
    etapa --nombre supers_verifica --omitida "no se construyó el consolidado (rc=$rc_bs3)"
    rc_ver=1
  fi

  if [ $rc_ver -eq 0 ]; then
    S3SUP="$REPO/Bases de datos/leyes-senado/supers/dist/s3"
    etapa --nombre supers_upload_sanciones --timeout 900 --desc "sanciones.jsonl → S3 (42 MB, medido 21s)" \
          -- aws s3 cp "$S3SUP/sanciones.jsonl" \
             "s3://caudal-legislativo/metadata/sanciones.jsonl" \
             --content-type "application/json" --cache-control "private, max-age=300"
    etapa --nombre supers_upload_stats --timeout 300 --desc "sanciones-stats.json → S3" \
          -- aws s3 cp "$S3SUP/sanciones-stats.json" \
             "s3://caudal-legislativo/metadata/sanciones-stats.json" \
             --content-type "application/json" --cache-control "private, max-age=300"
  else
    etapa --nombre supers_upload_sanciones \
          --omitida "el consolidado no pasó la verificación (rc=$rc_ver): en S3 se queda el bueno de ayer"
    etapa --nombre supers_upload_stats --omitida "ídem: no se sube un pilar a medias"
  fi

  # ── pilar Ejecutivo · normativa de Presidencia (Socrata 88h2-dykw, vía 1) ──
  # No estaba en el cron: el índice se quedó en junio mientras la fuente ya iba
  # por el 28-ago (medido sep-2026, «presupuesto general» daba 0 en 2027).
  # Fetch completo (~12k filas, ~1 min); el upload exige un piso de filas para
  # que un fetch a medias no encoja el índice en S3.
  etapa --nombre ejecutivo_fetch --timeout 900 \
        --desc "normativa de Presidencia · Socrata" \
        -- python3 tools/caudal/ejecutivo/harvest_decretos.py fetch
  rc_ej=$?
  if [ $rc_ej -eq 0 ]; then
    etapa --nombre ejecutivo_build --timeout 300 --desc "raw → normativa.jsonl + stats" \
          -- python3 tools/caudal/ejecutivo/harvest_decretos.py build
    rc_ej=$?
  else
    etapa --nombre ejecutivo_build --omitida "el fetch falló (rc=$rc_ej)"
  fi
  if [ $rc_ej -eq 0 ]; then
    EJD="$REPO/Bases de datos/leyes-senado/ejecutivo/dist"
    etapa --nombre ejecutivo_upload --timeout 300 --desc "normativa.jsonl + stats → S3 (piso 11.000 filas)" \
          -- bash -c "n=\$(grep -c . \"$EJD/normativa.jsonl\"); [ \"\$n\" -ge 11000 ] || { echo \"solo \$n filas: no se sube\"; exit 1; }; \
             aws s3 cp \"$EJD/normativa.jsonl\" s3://caudal-legislativo/metadata/normativa.jsonl --content-type application/json --cache-control 'private, max-age=300' && \
             aws s3 cp \"$EJD/stats.json\" s3://caudal-legislativo/metadata/normativa-stats.json --content-type application/json --cache-control 'private, max-age=300'"
  else
    etapa --nombre ejecutivo_upload --omitida "no hay índice nuevo (rc=$rc_ej): en S3 queda el de ayer"
  fi

  # ── temas del momento (chips de la búsqueda de Caudal) ──
  # Prensa política + radicados de la semana + consultas SUCOP abiertas → 8
  # temas de búsqueda, validados contra el propio Caudal. Si el builder no
  # produce al menos 4 temas válidos sale con rc=1 y NO se sube: en S3 queda
  # el JSON anterior (última copia buena).
  etapa --nombre temas_build --timeout 900 \
        --desc "temas del momento: prensa + radicados + SUCOP" \
        -- python3 tools/caudal/temas/build_temas.py
  rc_tm=$?
  if [ $rc_tm -eq 0 ]; then
    etapa --nombre temas_upload --timeout 120 --desc "temas-del-momento.json → S3 público" \
          -- python3 tools/caudal/temas/build_temas.py --upload-only
  else
    etapa --nombre temas_upload --omitida "el builder no produjo temas válidos (rc=$rc_tm): en S3 queda el de ayer"
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
fall, avisa, omit, lentas = [], [], [], []
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
    elif r.get('estado') == 'warn':
        avisa.append(f'{n} ({r.get("motivo") or "rc=" + str(r.get("rc"))})')
    elif r.get('estado') == 'omitida':
        omit.append(n)
    if (r.get('duracion_s') or 0) > 900:
        lentas.append(f'{n} {r["duracion_s"]:.0f}s')
print('· FALLARON : ' + ('; '.join(fall) if fall else 'ninguna'))
print('· PARCIALES: ' + ('; '.join(avisa) if avisa else 'ninguna'))
print('· OMITIDAS : ' + (', '.join(omit) if omit else 'ninguna'))
if lentas:
    print('· lentas   : ' + ', '.join(lentas))
PY

  # ── publicar el estado (para que la alerta viva FUERA de esta máquina) ──
  # Sin esto, si la máquina se cae nadie lo dice: el chequeo corre acá mismo.
  # Tres decisiones:
  #   · NO depende de rc_salud. check.py sale 1 en aviso y 2 en error, que son
  #     justo los días en que el estado más importa publicarlo.
  #   · NO es una etapa. `etapa.py` sirve para que check.py juzgue lo que corrió,
  #     y check.py ya corrió: el registro de esta subida no lo leería nadie (el
  #     .etapas.jsonl se trunca al empezar la siguiente corrida). Quien juzga esta
  #     subida es el vigilante de afuera, y la juzga por lo único que no miente:
  #     si el latido deja de envejecer bien. Una subida fallida se ve igual que una
  #     máquina caída, que es exactamente como tiene que verse.
  #   · El latido se publica SIEMPRE que se llegue hasta acá, aunque check.py se
  #     haya roto y no haya estado.json de esta corrida: en ese caso sale como
  #     error, y el estado.json viejo NO se sube como si fuera de hoy.
  if [ "$CAUDAL_PUBLICA" != "si" ]; then
    echo "--- publicar: NO (CAUDAL_PUBLICA=$CAUDAL_PUBLICA) · el estado queda local en $ESTADO ---"
    echo "═════════ fin $(date '+%H:%M:%S') · salud=$rc_salud · sin publicar (lo hace la otra máquina) ═════════"
    exit 0
  fi
  echo "--- publicar: estado.json (privado) + latido (público) ---"
  python3 tools/caudal/salud/latido.py --estado "$ESTADO" --etapas "$REG" \
          --inicio "$INICIO" --rc-salud "$rc_salud" --out "$LATIDO"
  rc_lat=$?
  if [ $rc_lat -ne 0 ] && [ $rc_lat -ne 10 ]; then
    # latido.py se rompió: igual sale un latido, mínimo y a mano. Un vigilante
    # que se queda sin latido por un bug nuestro tardaría 26 h en gritar.
    printf '{"v":1,"ts":"%s","corrida_inicio":"%s","estado":"error","rc_salud":%s,"motivo":"latido.py se rompió (rc=%s): ver cron.log"}' \
           "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$INICIO" "${rc_salud:-null}" "$rc_lat" > "$LATIDO"
  fi
  # Timeouts del propio CLI: sin `timeout` en macOS, una subida colgada no puede
  # dejar tomado el candado hasta la siguiente corrida.
  S3OPT="--cli-connect-timeout 20 --cli-read-timeout 60"
  if [ $rc_lat -eq 0 ]; then
    # shellcheck disable=SC2086
    aws s3 cp "$ESTADO" "$S3_ESTADO" $S3OPT \
        --content-type "application/json" --cache-control "no-cache" \
      && echo "· estado.json → $S3_ESTADO" \
      || echo "✗ no pude subir estado.json (el vigilante lo va a notar por el latido)"
  else
    echo "· estado.json NO se sube: no es de esta corrida (latido rc=$rc_lat)"
  fi
  # shellcheck disable=SC2086
  aws s3 cp "$LATIDO" "$S3_LATIDO" $S3OPT \
      --content-type "application/json" --cache-control "no-cache" \
    && echo "· latido → $S3_LATIDO" \
    || echo "✗ no pude subir el latido: afuera esto se va a ver como máquina caída"

  echo "═════════ fin $(date '+%H:%M:%S') · salud=$rc_salud (0 ok · 1 aviso · 2 error · 3 el chequeo se rompió) ═════════"
} >> "$LOG" 2>&1
