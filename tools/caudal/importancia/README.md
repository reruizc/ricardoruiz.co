# Caudal · Por qué importa — las tres coordenadas

Caudal sabía **detectar**. No sabía decir **qué importa**. Tres fuentes
independientes señalaron el mismo hueco:

- El ranking puso el fracking como lo de mayor alcance, cuando nuestro propio
  dato dice 11 radicaciones desde 2018, cero leyes y ocho marcadas `vitrina` por
  el motor de la Fase 1. **El sistema ya lo sabía y el ranking no lo usó.**
- El corte se hizo sobre los 35 proyectos radicados hasta ese día, y lo que
  importaba —la tributaria del Pacto, la reforma a la salud— todavía no estaba
  radicado.
- El motor de alertas explicaba sus señales altas casi siempre igual: *«radicado
  en la Comisión Séptima»*. Sabía decir por qué marcó algo, no por qué importa.

Este módulo es el modelo de importancia. **No es un score único: son
coordenadas, y quien consulta elige el lente.**

---

## Las tres coordenadas

| Eje | Pregunta | De dónde sale | ¿Validable? |
|---|---|---|---|
| **1 · Avance** | ¿va a pasar? | regresión logística calibrada contra 13.660 proyectos con desenlace conocido, 1990-2026 | **Sí, y se validó** |
| **2 · Impacto** | ¿qué me hace si pasa? | articulado ya extraído: obligaciones, sanciones, norma que modifica, vigilancia, a quién aplica | Parcialmente: los insumos son observados, los pesos son criterio |
| **3 · Político** | ¿qué significa? | heurística sobre la firma: cuántos firman, de qué bancada, cuántas veces lo han vuelto a radicar | **No. Y por eso se firma como heurística** |

### Por qué van separadas y no combinadas en un número

Vitrina y bandera son **la misma señal leída con dos lentes**. Un proyecto
radicado once veces sin pasar nunca es basura para un gremio que gestiona riesgo
regulatorio y es el mejor indicador disponible de qué defiende un bloque político
para quien lee la política. Las dos lecturas son ciertas al tiempo.

Si se penalizara la importancia por la probabilidad, se borraría justo lo que
hace visible el segundo caso. Por eso son ejes y no un promedio.

El único lente que combina es el de riesgo, y lo hace por una razón que no es un
peso a ojo: **el riesgo esperado de una norma es lo que te hace multiplicado por
la probabilidad de que llegue a hacértelo.** Es una esperanza, no una
ponderación arbitraria. Las tres coordenadas viajan siempre visibles.

---

## Eje 1 — lo que se puede validar, se validó

**AUC out-of-time 0,745** (entrenado con lo radicado antes de 2015, medido sobre
2015-2024, n=3.653). Estable entre **0,737 y 0,767** moviendo el corte a 2006,
2010, 2014 y 2018. El top 10% del ranking concentra leyes a **2,6×** la tasa base.

Contra qué se compara, mismo test y misma métrica:

| | AUC |
|---|---|
| solo «lo radica el Gobierno» | 0,583 |
| solo «es tratado internacional» | 0,531 |
| Gobierno + tratado + comisión | 0,695 |
| **modelo completo** | **0,745** |

Reporte completo, con calibración por deciles y pesos aprendidos, en
[`reportes/validacion-eje1.md`](reportes/validacion-eje1.md).

### Fugas encontradas y eliminadas

Un modelo que use el desenlace luce perfecto y no sirve para nada. Tres fugas
salieron en la construcción, y **las tres estaban dando AUC gratis**:

1. **`veces_presentado` / `empuje` / `vitrina_score`.** Los calcula
   `clasificar.py` sobre el cluster completo, incluyendo radicaciones futuras. Un
   proyecto de 2014 «sabía» que en 2022 lo volverían a radicar. Se reconstruyen
   desde `historial_reradicacion` cortando por año.
2. **`origen_registro`.** `camara` significa «no cruzó a Senado», porque los que
   cruzan quedan deduplicados bajo el registro del Senado: 0,7% de leyes contra
   24,9%. Eso no es el Congreso, es nuestro pipeline.
3. **`origen`** (la cámara donde nació). La menos obvia y la que más costaba:
   parece un metadato inocente que se sabe al radicar, pero **dentro del registro
   del Senado un proyecto de origen Cámara es uno que ya cruzó**, o sea que ya
   aprobó dos debates. 46,6% de leyes contra 18,6%; etapa máxima media 3,69 contra
   1,33. Quitarla bajó el AUC de 0,82 a 0,74. **Ese es el número honesto.**

Se descartó además la feature «no tiene comisión asignada»: sus 114 casos son
fichas viejas o incompletas y ninguno llegó a ley, pero en la legislatura viva los
75 sin comisión son de Cámara, cuyo listado simplemente no publica el campo.
Habría hundido a todos los proyectos de Cámara por un artefacto del scraper.

`calibrar.py` corre una **auditoría anti-fuga** antes de entrenar: borra los
campos de desenlace en 600 registros al azar y reconstruye el índice de
trayectoria a la época de otros 200, y aborta si algún vector de features cambia.
Los campos prohibidos están listados en `PROHIBIDOS`, incluido `origen`, para que
reintroducirlo dispare la alarma solo.

### Qué aprendió

Los pesos más grandes son legibles y coinciden con cómo funciona el Congreso: ser
acto legislativo hunde (ocho debates en un año), radicarlo el Gobierno empuja,
las comisiones económicas conjuntas y la Segunda (que despacha tratados en
bloque) empujan, radicar contra el cierre de la legislatura hunde, y que un
intento anterior haya pasado del segundo debate empuja.

---

## Eje 3 — por qué esto sí es una heurística y se dice

«Peso político» **no tiene desenlace observable**: no existe un registro de qué
proyecto fue bandera de quién. Lo que hay son proxies del comportamiento de la
firma. Se declaran, se pueden discutir renglón por renglón, y viajan en la
respuesta:

| Señal | Peso | Por qué |
|---|---|---|
| firma colectiva | 28 | 60 firmas no son 60 autores: son un acto de bloque |
| cohesión de bancada | 18 | ¿la firma es de un bloque o transversal? |
| persistencia | 24 | re-radicado sin pasar: lo sostienen por lo que dice |
| agenda del Ejecutivo | 16 | lo radica el Gobierno: es programa |
| rango normativo | 14 | cambiar las reglas del juego, no una regla |

La cohesión se calcula cruzando los firmantes con `autor-partido.json`. En la
reforma a la salud da 71,4% Pacto Histórico sobre 65 firmantes → *«bancada
cerrando filas»*; en la tributaria, 73,7%; en el fracking, 100% sobre los 17
firmantes con partido conocido. Es la distinción que pidió Pablo entre bandera de
identidad y proyecto que toca mercados, calculada y no supuesta.

**El eje 1 se puede validar y por eso se validó. Este no, y por eso se firma como
criterio y no se disfraza de medición.**

### Un defecto del clustering que salía justo en el caso de Diego

`clasificar.py` agrupa re-radicaciones por firma **exacta** de tokens, y descarta
los títulos que dejan menos de tres tokens significativos. La reforma a la salud
reduce a `{transform, salud}` — dos tokens — así que sus tres radicaciones
quedaron en clusters distintos (12290, 12301, 12311) y su persistencia daba
**cero**, justo en el proyecto que un experto señaló como el que más importa. El
efecto es sistemático, no anecdótico: los títulos genéricos son los de las
reformas grandes.

`antecedentes.py` lo complementa por otra vía —parecido de título (Jaccard ≥ 0,55
con al menos dos raíces distintivas en común, y solo contra años anteriores)— y
recupera historia en **250 de 1.090** proyectos vivos:

| | cluster exacto | por parecido |
|---|---|---|
| reforma a la salud 024/2026 | 0 | **2** (216/23 retirado · 410/25 llegó a 4º debate y se archivó) |
| fracking 011/26 | 1 | **2** (150/24 y 294/25, los dos archivados por tiempo) |
| reforma tributaria 004/2026 | 0 | **1** (245/2020, retirado) |

No reemplaza al clustering: alimenta **solo el eje 3**. El eje 1 sigue usando
`historial_reradicacion` tal cual, para no meterle una señal nueva a una
calibración ya validada sin volver a medirla. Incorporarla al eje 1 y recalibrar
es la mejora pendiente más clara.

---

## Uso

```bash
# calibrar contra el histórico + reporte de validación
python3 tools/caudal/importancia/calibrar.py --reporte reportes/validacion-eje1.md

# correr los tres lentes sobre la legislatura viva
python3 tools/caudal/importancia/evaluar.py --top 10

# un caso concreto
python3 tools/caudal/importancia/evaluar.py --caso fracking
```

Salidas a `Bases de datos/leyes-senado/dist/s3/`: `importancia-modelo.json` (3 KB),
`importancia-autores.json` (trayectoria de 4.146 firmantes) e
`importancia-antecedentes.json`. Subir los tres a
`s3://caudal-legislativo/metadata/` y redesplegar la Lambda. `antecedentes.py` no
viaja en el ZIP: su índice se precomputa aquí y la Lambda solo lo lee.

### API

```jsonc
{"action":"importancia"}                                  // metadatos y lentes
{"action":"importancia","id":9934,"tb":"pdly"}            // coordenadas de uno
{"action":"importancia","lente":"riesgo","limit":15,
 "perfil":{"sectores":["salud"],"empresas":["Sanitas"]}}  // ranking
```

Lentes: `riesgo` · `politico` · `agenda` · `impacto`. La respuesta trae siempre
tres bloques —`ranking`, `pendientes`, `n_fuera`— porque **un lente no puede
desaparecer proyectos en silencio**.

---

## Límites conocidos, medidos

- **Sobre-confianza en el decil alto.** El decil superior predice 0,69 y observa
  0,57. Ordena bien y exagera el nivel arriba. El intercepto se corrige por deriva
  de época (el Congreso aprueba menos que antes: 27,1% antes de 2015, 21,5%
  después), pero eso mueve el nivel, no la pendiente.
- **La dispersión dentro de la legislatura viva es estrecha**: mediana 0,19 con
  cuartiles en 0,14 y 0,21. Todos los proyectos son del año 1, ninguno tiene
  historia de trámite todavía, así que el eje 1 discrimina mucho mejor en agregado
  que entre vecinos. Se ensancha solo con el tiempo.
- **La capa de bloqueo casi no aporta hoy**: 3 de 214 proyectos tienen
  agendamientos observados, porque la legislatura arrancó hace semanas. La curva
  P(tratado|posición) que usa está medida, pero su efecto se verá en meses.
- **La cohesión de bancada solo se calcula en 77 de 214** (los que tienen al
  menos tres firmantes con partido conocido). En el resto, ese componente aporta
  cero, que no es lo mismo que «firma transversal».
- **74 de 207 articulados salen solo del título.** Su impacto es un piso, no una
  medida, y el sesgo no es aleatorio: las reformas grandes llegan con el texto
  tarde. Por eso van en un bloque `pendientes` aparte y **nunca mezclados en el
  ranking** — es lo que evita que la reforma tributaria quede al fondo por no
  haberla leído todavía.
- **Aplicar el modelo a un proyecto que solo existe en el registro de Cámara es
  una extrapolación**: se entrenó sobre el registro del Senado por la fuga
  estructural descrita arriba.
