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
#   ordenes_camara            harvest_ordenes.py          órdenes del día: 14 comisiones + plenaria
#   ordenes_senado_indice     harvest_ordenes_senado.py   refresca el índice DOCman + plenaria
#   ordenes_senado_comisiones   ídem `buenas`             Cuarta/Quinta/Sexta
#   ordenes_senado_plenaria     ídem `plenaria`           secretariasenado.gov.co
#   secop_fetch/build/upload  harvest_secop.py            agregados de SECOP II
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
  etapa --nombre banrep_fetch --timeout 600 \
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
