# Ampliar el diccionario de empresas de Caudal

El diccionario (`tools/caudal/empresas.py`) traduce el nombre de una empresa a
las dos cosas que Caudal necesita: el **vocabulario legislativo** que la toca
(pilares Congreso y Ejecutivo) y su **identidad legal** (pilares Regulatorio,
Contratación y Medios). Este directorio tiene lo que hace falta para crecerlo
sin romperlo.

## El flujo, en cuatro pasos

```bash
export CAUDAL_DICC_DIR="$PWD/Bases de datos/caudal-diccionario"

python3 tools/caudal/diccionario/candidatas.py          # 1. qué falta, según el dato
python3 tools/caudal/diccionario/verificar_evidencia.py nombres.txt   # 2. ¿existe?
#    3. escribir las tuplas a mano en $CAUDAL_DICC_DIR/tandas/*.py
python3 tools/caudal/diccionario/validar_tandas.py      # 4a. revisar
python3 tools/caudal/diccionario/integrar.py            # 4b. escribir en empresas.py
python3 tools/caudal/empresas.py verificar              # 4c. auditor oficial
```

`integrar.py` es **idempotente**: reemplaza el bloque marcado dentro de `_RAW`,
así que se puede correr las veces que haga falta. Serializa desde las tuplas ya
evaluadas, no copia texto, de modo que lo que entra al diccionario es
exactamente lo que el validador revisó (los archivos de tanda pueden usar
helpers para escribir menos).

## ⚠️ Lo que se midió y no hay que volver a intentar

**El TEMA no se deriva automáticamente. No hay atajo.** Se probaron los dos
candidatos obvios y los dos fallan:

| Vía | Acierto | Por qué falla |
|---|---|---|
| Palabras de la razón social | **20%** | el 80% de la cola de SECOP es opaca: `DISTRACOM`, `SUPRISA`, `GESCOM`, `Avántika` no dicen a qué se dedican |
| Código UNSPSC del contrato | **49%** | describe **qué le vendió al Estado**, no a qué se dedica: Claro aparece como servicios de TI, las universidades como consultoría |

Es el mismo modo de falla del `origen` en los registros de Cámara y del
`adjudicado` en SECOP: un campo que responde otra pregunta y **no da error,
solo miente**. El sector sí predice el núcleo temático (77% sobre las entradas
curadas a mano, 100% en 15 de los 30 sectores), pero asignar el sector a una
razón social opaca es justamente lo que no se automatiza.

**Conclusión operativa:** el nombre y la identidad se derivan del dato; el tema
lo pone un humano. Por eso el paso 3 es a mano.

## ⚠️ Otras cosas medidas

- **SECOP ordenado por valor no sirve para priorizar**: `valor_del_contrato`
  trae errores de digitación (un contrato de 767 billones de pesos, media vez
  el PIB del país). Ordenar por número de contratos sí funciona.
- **`tipodocproveedor='NIT'`** separa empresas de personas naturales mucho mejor
  que cualquier regex sobre el nombre. Son 5.000 proveedores limpios.
- **El `&` se pierde al normalizar**: `DELOITTE & TOUCHE` queda
  `deloitte touche`. Una razón social escrita con `and` **no casa** con el
  registro real. Escribir las dos variantes (el integrador ya lo hace para las
  tandas, pero al agregar entidades a mano hay que recordarlo).
- **El riesgo de un alias no es su longitud sino su ambigüedad.** `zoetis`,
  `pulzo` o `endava` son cortos y perfectamente seguros porque son marcas
  inventadas; `zenu` es peligroso porque el pueblo Zenú aparece en proyectos de
  consulta previa, y `familia`, `exito` o `corona` son palabras del español. La
  lista `AMBIGUOS` de `validar_tandas.py` es lo que hay que ampliar cuando
  aparezca un caso nuevo, no el umbral de caracteres.
- **La evidencia por articulado es débil** y no debe usarse sola: busca la
  palabra más distintiva del nombre, y palabras como `grasas` o `merca` aparecen
  en decenas de proyectos por razones ajenas. La evidencia fuerte es SECOP y los
  actos regulatorios, donde el match es contra la razón social completa.

## Las dos pruebas que deciden si se puede desplegar

1. **Falsos disparos**: una consulta temática normal (`reforma pensional`,
   `cambio climatico`) NO puede activar una empresa. La referencia es **1 de 57**,
   y ese uno es el `sena de la mujer` que ya estaba documentado.
2. **Regresión**: `uber`, `claro`, `rappi`, `sena`, `epm`, `ecopetrol`,
   `anglogold`, `findeter` tienen que seguir resolviendo a lo mismo.

Ambas están en el script de regresión que acompaña a este flujo. `exito` NO
resuelve, y es correcto: su alias es `grupo exito` porque «éxito» es una palabra
común.

## Rendimiento

Con 2.008 entradas: `empresas_en()` (lo que corre por consulta en la Lambda)
tarda **0,55 ms**, y `casa_registro_any()` **0,72 ms por registro**, o sea unos
**60 s** por pasada completa sobre los 83.360 actos del pilar Regulatorio. Esa
pasada solo ocurre en `harvest_anla.build`, que tiene memo por documento; al
cambiar el diccionario el memo se invalida y **la primera corrida del cron
después de ampliar tarda ~60 s en vez de ~4 s**. Es esperado, y una sola vez.
