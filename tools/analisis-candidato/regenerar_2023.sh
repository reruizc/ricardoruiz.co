#!/usr/bin/env bash
# regenerar_2023.sh — vuelve a generar los índices y agregados de 2023 con el
# voto de LISTA, verifica el resultado y deja listos los comandos de subida.
#
# Hace falta porque los índices que están hoy en S3 descartaban la fila
# COD_CAN=0, que es el voto solo por el partido (y, en lista cerrada, TODO su
# voto). Sin eso, el Pacto Histórico no existía en el Concejo de Bogotá y sus
# 7 curules se les repartían a las demás listas.
#
#   bash tools/analisis-candidato/regenerar_2023.sh            # genera y verifica
#   bash tools/analisis-candidato/regenerar_2023.sh --subir    # además sube a S3
#
# Necesita, en «Bases de datos/»:
#   FINAL SUBIDA GCS/GCS_2023TER.csv   (7,4M filas · concejo, asamblea, alcaldía, gobernación)
#   FINAL SUBIDA GCS/GCS_2023JAL.csv   (2,25M filas · JAL)
#   PUESTOS_GEOREF.csv
# Son varios GB y no están en el repo ni en S3: viven solo en su máquina.
# Tiempo aproximado: media hora larga, la mayor parte ordenando el CSV grande.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BD="$RAIZ/Bases de datos"
TOOLS="$RAIZ/tools/analisis-candidato"
SUBIR=0
[[ "${1:-}" == "--subir" ]] && SUBIR=1

faltan=0
for f in "FINAL SUBIDA GCS/GCS_2023TER.csv" "FINAL SUBIDA GCS/GCS_2023JAL.csv" "PUESTOS_GEOREF.csv"; do
  if [[ ! -f "$BD/$f" ]]; then echo "✗ falta «Bases de datos/$f»"; faltan=1; fi
done
if [[ $faltan -eq 1 ]]; then
  echo
  echo "Esos CSV son la fuente cruda de la Registraduría. Sin ellos no hay nada"
  echo "que regenerar: los índices derivados no traen el voto de lista."
  exit 1
fi

# Los temporales ordenados son de varios GB: van al disco de trabajo, no al repo.
export SCRATCH_DIR="${SCRATCH_DIR:-${TMPDIR:-/tmp}/regenerar-2023}"
mkdir -p "$SCRATCH_DIR"
echo "· temporales en $SCRATCH_DIR (se pueden borrar al terminar)"
echo

cd "$RAIZ"
for paso in \
  "índice de concejo:build_concejo_2023.py" \
  "índice de JAL:build_jal_2023.py" \
  "índice de asamblea:build_asamblea_2023.py" \
  "agregado de JAL:build_territorial_resultados.py jal" \
  "agregado de concejo:build_territorial_resultados.py concejo" \
  "agregado de asamblea:build_asamblea_resultados.py" ; do
  nombre="${paso%%:*}"; cmd="${paso#*:}"
  echo "══ $nombre"
  # shellcheck disable=SC2086
  python3 "$TOOLS"/$cmd
  echo
done

echo "══ verificación"
if ! python3 "$TOOLS/verificar_listas_2023.py"; then
  echo
  echo "✗ La verificación no pasó, así que NO se sube nada: un índice malo en S3"
  echo "  le da metas equivocadas a todos los clientes. Revise arriba qué falló"
  echo "  antes de repetir la corrida."
  exit 1
fi
echo

S3="s3://elecciones-2026/ricardoruiz.co/congreso-2026/output"
OPTS=(--recursive --content-type "application/json" --cache-control "public, max-age=300")
subidas=(
  "$BD/output_concejo_2023/:$S3/concejo-2023/"
  "$BD/output_jal_2023/:$S3/jal-2023/"
  "$BD/output_asamblea_2023/:$S3/asamblea-2023/"
)
if [[ $SUBIR -eq 1 ]]; then
  echo "══ subiendo a S3"
  for s in "${subidas[@]}"; do aws s3 cp "${s%%:*}" "${s#*:}" "${OPTS[@]}"; done
  echo
  echo "Listo. Ya se puede quitar LISTAS_VERIFICADAS de vote-target.js: el"
  echo "índice manda sobre esa tabla en cuanto trae «listas»."
else
  echo "══ para subir (revise primero la verificación de arriba)"
  for s in "${subidas[@]}"; do echo "aws s3 cp \"${s%%:*}\" \"${s#*:}\" ${OPTS[*]}"; done
  echo
  echo "o vuelva a correr esto con --subir."
fi
