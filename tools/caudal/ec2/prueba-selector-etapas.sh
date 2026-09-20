#!/bin/bash
# Pruebas de _le_toca(), el selector que decide qué etapas corre cada máquina.
# Se extrae la función DEL PROPIO run_diario.sh, así se prueba el código real y
# no una copia que se desactualiza. Es crítico: si esto se equivoca, una máquina
# deja de correr etapas y la otra no lo cubre.
#
#   bash tools/caudal/ec2/prueba-selector-etapas.sh
set -uo pipefail
RUN="$(cd "$(dirname "$0")/../../.." && pwd)/tools/leyes-senado/run_diario.sh"
eval "$(sed -n '/^_le_toca() {/,/^}/p' "$RUN")"
[ "$(type -t _le_toca)" = function ] || { echo "✗ no pude extraer _le_toca de $RUN"; exit 1; }

FALLAS=0
prueba() {  # $1=CAUDAL_ETAPAS  $2=etapa  $3=esperado(si|no)  $4=por qué
  CAUDAL_ETAPAS="$1"
  if _le_toca "$2"; then got=si; else got=no; fi
  if [ "$got" = "$3" ]; then echo "  ✓ $4"
  else echo "  ✗ $4 — esperaba $3, dio $got (ETAPAS='$1' etapa='$2')"; FALLAS=$((FALLAS+1)); fi
}

echo "A · sin configurar corre todo (es el default, y el del Mac hasta ahora)"
prueba ""  senado_radicados si "vacío → corre senado_radicados"
prueba ""  temas_upload     si "vacío → corre temas_upload"

echo
echo "B · lista blanca: el Mac en Fase 1"
M='senado_*,banrep_fetch,red_lista'
prueba "$M" senado_radicados si "senado_radicados sí"
prueba "$M" senado_upload    si "senado_upload sí (casa senado_*)"
prueba "$M" banrep_fetch     si "banrep_fetch sí"
prueba "$M" red_lista        si "red_lista sí (las dos máquinas la necesitan)"
prueba "$M" camara_radicados no "camara_radicados NO"
prueba "$M" dataset_build    no "dataset_build NO"

echo
echo "C · lista negra: la EC2 en Fase 1 (todo menos lo del WAF)"
E='!senado_radicados,!banrep_fetch'
prueba "$E" camara_radicados si "camara_radicados sí"
prueba "$E" temas_upload     si "temas_upload sí"
prueba "$E" senado_upload    si "senado_upload sí: sube lo que haya, no toca el WAF"
prueba "$E" senado_radicados no "senado_radicados NO"
prueba "$E" banrep_fetch     no "banrep_fetch NO"

echo
echo "D · detalles que rompen en producción"
prueba "senado_*, banrep_fetch" banrep_fetch si "tolera espacios tras la coma"
prueba "!senado_*"    dian_fetch     si "solo exclusiones: lo no excluido pasa"
prueba "!senado_*"    senado_upload  no "y lo excluido no pasa ni por comodín"
prueba "camara_*"     camara         no "prefijo sin sufijo no casa de más"
prueba "dataset_build" dataset_build si "nombre exacto"
prueba "dataset_build" dataset_upload_indice no "nombre exacto no arrastra a los hermanos"
prueba "*"           lo_que_sea      si "'*' corre todo"

echo
echo "E · la partición REAL de Fase 1, contra los nombres del propio script"
MAC='red_lista,senado_*,banrep_fetch'
EC2='!senado_*,!banrep_fetch'
NOMBRES=$(grep -o -- '--nombre [a-z_0-9]*' "$RUN" | awk '{print $2}' | grep . | sort -u)
solo_mac=""; solo_ec2=""; ambas=""; ninguna=""
for e in $NOMBRES; do
  CAUDAL_ETAPAS="$MAC"; if _le_toca "$e"; then m=1; else m=0; fi
  CAUDAL_ETAPAS="$EC2"; if _le_toca "$e"; then c=1; else c=0; fi
  if [ $m = 1 ] && [ $c = 1 ]; then ambas="$ambas$e "
  elif [ $m = 1 ]; then solo_mac="$solo_mac$e "
  elif [ $c = 1 ]; then solo_ec2="$solo_ec2$e "
  else ninguna="$ninguna$e "; fi
done
echo "     Mac: $solo_mac"
echo "     EC2: $(echo $solo_ec2 | wc -w | tr -d ' ') etapas"
echo "     en ambas: ${ambas:-—}"
[ "$ambas" = "red_lista " ] \
  && echo "  ✓ lo único compartido es red_lista, que es lo correcto: cada máquina
    necesita saber si TIENE red antes de arrancar" \
  || { echo "  ✗ se comparten etapas que escribirían el mismo objeto: $ambas"; FALLAS=$((FALLAS+1)); }
[ -z "$ninguna" ] && echo "  ✓ ninguna etapa se queda sin dueño" \
  || { echo "  ✗ sin dueño (nadie las correría): $ninguna"; FALLAS=$((FALLAS+1)); }
CAUDAL_ETAPAS="$EC2"
if _le_toca senado_upload; then
  echo "  ✗ senado_upload correría en la EC2: subiría el manifiesto del Senado sin tener su estado"
  FALLAS=$((FALLAS+1))
else
  echo "  ✓ senado_upload NO corre en la EC2 (sube el manifiesto del Senado: es del Mac)"
fi

echo
if [ "$FALLAS" -gt 0 ]; then echo "✗ $FALLAS fallas"; exit 1; fi
echo "✓ todo bien"
