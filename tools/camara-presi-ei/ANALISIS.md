# ¿A dónde fueron los votantes de cada representante de Bogotá en la 1V?

Cruce **Cámara Bogotá (8-mar-2026)** → **Presidencial 1V (31-may-2026)** por
inferencia ecológica, a nivel de puesto (1.078 puestos, censo idéntico en ambas
elecciones porque son el mismo año → los mismos electores inscritos por puesto).

## Resultado (% de los votantes de cada lista, entre quienes votaron en mayo)

| Lista (Cámara) | Electos cubiertos | → Cepeda | → Abelardo | → Resto | votos |
|---|---|---:|---:|---:|---:|
| **Pacto Histórico** (cerrada) | Carrascal, Monroy, Beltrán, Landínez, Pizarro, Vargas, Romero, Becerra (8) | **73%** | 13% | 13% | 924.229 |
| **Partido Liberal** | Bleidy Pérez Ballestas | **42%** | 37% | 21% | 112.099 |
| **Alianza Verde** | Catherine Juvinao · Mauricio Toro | **36%** | 41% | 23% | 243.422 |
| **Salvación Nacional** | Carol Borda | **34%** | 43% | 23% | 187.997 |
| **Centro Democrático** (resto) | Uscátegui, Cote, Mosquera, Lorduy, Gordillo | **21%** | 53% | 26% | 425.766 |
| **Daniel Briceño** (CD, individual) | Daniel Briceño | **14%** | 58% | 28% | 262.469 |

"Resto" = demás candidatos presidenciales + voto en blanco/nulo.
Punto central con shrink=0.025. IC95% bootstrap y cotas Duncan-Davis en `out/ei_reporte.txt`.

## Método

- **Base = censo del puesto.** Marzo (Cámara, 52% participación) y mayo
  (Presidencial, 70%) comparten el mismo censo por puesto → ventaja clave: son
  los mismos electores, sólo cambia quién va y por quién vota.
- **King's EI 2×3 regularizada por fuente** (`fit_qp_reg`, símplex + shrinkage
  parcial al prior citywide, à la `fit_ei_geo` del proyecto). `x_p =
  votos_lista / votantes_presi`; `Y_p = [Cepeda, Abelardo, Resto] / votantes_presi`.
  IC por bootstrap de puestos (warm-start) + cotas Duncan-Davis.
- **Validación cruzada**: una segunda formulación (censo-base con abstención de
  mayo explícita, `04_robustez.py`) reproduce el mismo reparto 3-way (±1-2 pp en
  las listas difusas; ±5-9 pp en las polarizadas). Contraste vs estimador
  ingenuo (turf) en el reporte.

## Por qué 6 perfiles para 18 electos (limitación honesta)

La EI identifica la transferencia a nivel de **lista**, no del candidato
individual de lista abierta: los co-partidarios de una misma lista tienen
perfiles geográficos casi idénticos (colineales) → no son separables entre sí.
Por eso:
- Los **8 del Pacto** comparten perfil **por construcción** (lista cerrada: el
  votante eligió el logo).
- Los **5 CD menores** comparten el perfil del bloque CD (la EI no los separa).
- Los **2 de Verde** comparten el perfil de la lista Verde.
- **Briceño** sí se estima aparte: con 262k votos preferentes y geografía
  distintiva, se identifica solo (y sus votantes son la franja más
  abelardista del CD: 58% vs 53% del resto CD).

## Hallazgos

1. **La izquierda consolidó: el electorado del Pacto se fue ~73% con Cepeda** —
   muy por encima del 45% que votó Cepeda en los puestos donde el Pacto es
   fuerte (corrección clave de la EI: los votantes *propios* del Pacto son mucho
   más cepedistas que su territorio mezclado del sur).
2. **El electorado del CD se fue mayoritariamente con Abelardo** (53-58%),
   apenas 14-21% con Cepeda.
3. **El centro de Bogotá se inclinó a la derecha en 1V**: hasta Verde, Salvación
   y los liberales repartieron su voto algo más hacia Abelardo que hacia Cepeda
   (salvo el Liberal, el más parejo: 42/37).
4. El **Liberal de Bleidy Pérez** es el electorado más dividido y "mediano":
   42% Cepeda / 37% Abelardo.

## Archivos

- `01_camara_agg.py` → identifica los 18 electos (D'Hondt + listas).
- `02_extract.py` → tabla por puesto (`out/puestos_bogota.csv`).
- `03_ei.py` → EI principal (`out/ei_resultados.csv`, `out/ei_reporte.txt`).
- `04_robustez.py` → validación con la formulación censo-base.

Datos fuente: `Bases de datos/DEPTOS_DECLARADOS/MMV_XXX_16_*.csv` (Cámara mesa) ·
`Bases de datos/nuevos archivos 1v 2026/PRECONTEO_1V_2026_MESA_con_Claudia.csv` ·
`Bases de datos/COMUNAS_DATA.csv` (censo).
