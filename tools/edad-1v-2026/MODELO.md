# Modelo de composición etaria del voto · 1V 2026 vs 1V 2022

**Estado: pipeline completo CORRIDO (2026-06-09). Resultados con IC 95%,
cotas Duncan-Davis y sensibilidad en `Bases de datos/output_edad_1v/ei-report.txt`
(+ `ei-final.csv` formato long). Estimador: QP símplex por 7 estratos
regionales, bootstrap por municipios B=300; el ruido de proyección va como
análisis de sensibilidad aparte (meterlo al bootstrap atenúa — EIV — y los
IC dejarían de contener el punto).**

## 1. Pregunta

¿Cómo se distribuye el voto de los candidatos principales de la 1ª vuelta 2026
(Cepeda, Abelardo, Paloma, Fajardo) por grupos de edad, y cómo se compara esa
estructura con la 1ª vuelta 2022 (Petro, Fico, Rodolfo, Fajardo)?

No existe dato individual de voto × edad. Lo que existe:

| Insumo | Fuente | Nivel | Años |
|---|---|---|---|
| Sufragantes × edad × sexo | `Edadygenero.xlsx` (RNEC, 645k filas) | mesa | 2018, 2019, 2022, 2023 |
| Votos por candidato | GCS 2022 (escrutinio) · preconteo 0247 2026 | mesa | 2022, 2026 |
| Censo electoral | `censos-puesto-{2018,2022,2026}.json` | puesto | 2018, 2022, 2026 |
| Población × edad simple × sexo | `DANE-AreaSexoEdadDep-2018-2050_VP.xlsx` | **depto** | 2018–2050 |

El problema es de **inferencia ecológica (EI)** con una covariable (edad de
votantes 2026) que además debe **proyectarse demográficamente**, porque
Edadygenero termina en 2023.

## 2. Notación

- Unidades: puestos `p` (llave RNEC `dep-mun-zz-pp`). 2022: 12.376 con perfil
  etario; 2026: 13.245 domésticos con votos.
- Bandas RNEC `a`: 18-20, 21-25, 26-30, 31-35, 36-40, 41-45, 46-50, 51-55,
  56-60, 61+ (10). Para EI se colapsan a 5 grupos: 18-25, 26-35, 36-45,
  46-60, 61+.
- `n_a^t(p)`: sufragantes de banda `a` en puesto `p`, año `t` (observado
  t=2018, 2022).
- `N_a^t(d)`: población DANE banda `a`, depto `d`, año `t`.
- `V_c^t(p)`: votos del candidato `c`; `T^t(p)` votos totales.
- `w_a^t(p) = n_a^t(p) / Σ_a n_a^t(p)`: composición etaria de votantes.

## 3. Modelo en cuatro pasos

### Paso 1 — Composición etaria 2022 por puesto (observada, con control de calidad)

`w_a^22(p)` sale directo de Edadygenero P1V-2022 agregado mesa→puesto.

**Fix obligatorio (descubierto en el probe):** en Bogotá la columna
`Cód. Comuna / Localidad` trae el **nombre** de la localidad, no el código de
zona. Mapeo canónico Usaquén=01 … Sumapaz=20, Corferias=90, Cárceles=98.
Con el fix, el cruce edad22 ∩ votos22 cubre **98,65%** de los votos 2022
(12.366/12.376 puestos).

Edadygenero 2022 solo desglosa 18,8M de 21,5M sufragantes (87,5%): las mesas
sin biometría/desglose no se reportan. Control de calidad por puesto con la
razón `cov(p) = sufragantes_edad(p) / votos_escrutinio(p)`:

- `cov ∈ [0.70, 1.10]` → perfil de puesto utilizable (75% de los votos).
- fuera de rango → cae al perfil de **zona**, y si la zona también falla, al
  de **municipio** (las razones fuera de rango indican mesas re-asignadas
  entre puestos vecinos o cobertura parcial; a nivel municipal se cancelan).

### Paso 2 — Proyección demográfica 2022 → 2026

La edad de los votantes 2026 no se observa; se proyecta en dos niveles:

**(a) Nivel departamental — tasas de participación por edad.**
Tasa implícita 2022: `ρ_a^22(d) = n_a^22(d) / N_a^22(d)`.
Votantes esperados 2026: `ñ_a^26(d) = ρ_a^22(d) · N_a^26(d) · κ(d)`,
donde `κ(d)` reescala para que el total coincida con los votantes reales
2026 del depto (preconteo). El supuesto es que la **forma** del perfil de
participación por edad es estable entre presidenciales 1V consecutivas; el
**nivel** lo fija el dato real 2026.

**(b) Nivel puesto — asignación con raking (IPF).**
Semilla: `n_a^22(p)` (el perfil local). Márgenes: filas = `ñ_a^26(d)` (edades
del depto), columnas = `T^26(p)` (votantes reales por puesto del preconteo).
IPF estándar (Deming-Stephan 1940) converge a `ŵ_a^26(p)` consistente con
ambos márgenes. Puestos nuevos sin semilla 2022 (11,9% de los votos): semilla
de zona (8,7%) o municipio (3,2%).

La cohorte nueva (18-20 de 2026 no existía en 2022) entra por el denominador
DANE con la `ρ_18-20` de 2022 — supuesto de *efecto edad* (la banda vota como
votaba la banda), no de cohorte. Sensibilidad: ±20% en `ρ` de bandas jóvenes.

**Backtest del supuesto (2018→2022, ya corrido):**

| Nivel | Métrica | Resultado |
|---|---|---|
| Nacional | MAE share por banda | **0,32 pp** (máx 1,07 pp en 61+) |
| Depto | mediana MAE | 0,47 pp (peor: San Andrés 1,9) |
| Puesto | mediana MAE shape | 1,87 pp · p90 3,6 pp |
| Naive (sin DANE) | MAE nacional | 0,47 pp → el ajuste DANE aporta |

La señal entre puestos (σ del share por banda: 2,6–7,9 pp; share 61+ va de
10,6% a 29,5% entre p10 y p90) es ~4× el error de proyección → hay
identificación de sobra.

### Paso 3 — Inferencia ecológica RxC

Modelo de tablas: en cada puesto, la fracción del voto del candidato `c` es
mezcla de las preferencias por banda:

`V_c(p)/T(p) = Σ_a β_ca(p) · w_a(p)`,  con `β_ca(p) ∈ [0,1]`, `Σ_c β_ca(p) = 1`.

Tres estimadores, del más conservador al más informativo:

1. **Cotas deterministas de Duncan-Davis (método de bounds, "cota dura de
   King")**: por puesto y banda, `β` está acotado por los márgenes sin ningún
   supuesto. Se agregan a cotas nacionales. Es lo único 100% libre de
   supuestos y es la base del claim público honesto.
2. **Goodman ponderado con restricciones de símplex** (QP): mínimos cuadrados
   ponderados por votos con `β` constante entre puestos dentro de **estratos**
   (región × urbano/rural), restricciones `[0,1]` y suma 1 conjunta. El demo
   sin restricciones conjuntas ya reproduce los patrones conocidos y la
   consistencia nacional exacta (ver §5); las versiones con símplex eliminan
   las soluciones de esquina (0%/84%).
3. **EI jerárquico bayesiano Multinomial-Dirichlet** (King-Rosen-Tanner 1999,
   RxC): `β` varía por puesto alrededor de una media por estrato; produce
   intervalos de credibilidad. Implementable en numpyro/PyMC; es el estimador
   para cifras publicables con incertidumbre.

Para 2026, la incertidumbre del Paso 2 se propaga: bootstrap por bloques
(municipios) re-muestreando también `ρ_a` con el error del backtest.

### Paso 4 — Comparativo 2022 vs 2026

El MISMO estimador (3) corrido sobre 2022 con `w` observado da los perfiles
de Petro/Fico/Rodolfo/Fajardo. Comparables directos:
Petro22→Cepeda26, "no-Petro"22→Abelardo26, brecha generacional por bloque,
y los flancos (Fajardo 22 vs 26, Paloma vs el votante de Fico).
Nota: 2022 es escrutinio y 2026 preconteo (~99,9% del potencial) — diferencia
de fuente documentada, no material para shares.

## 4. Supuestos de identificación (explícitos)

- **S1 (proyección):** la forma del perfil de participación por edad de cada
  territorio es estable entre 1V-2022 y 1V-2026, condicional al nivel real de
  participación. Evidencia: backtest 2018→2022 (0,32 pp nacional) — y eso que
  2018→2022 cruzó un estallido social y +2,3 pp de participación.
- **S2 (cobertura):** dentro de un puesto con `cov ∈ [0.70,1.10]`, las mesas
  sin desglose etario son ignorables respecto a la edad (la mesa se asigna por
  orden de cédula, no por edad → defendible). Para puestos fuera del rango se
  usa el agregado superior.
- **S3 (EI, constancy):** `β_ca` constante dentro de estrato región×urbanidad
  (relajable con el jerárquico). El sesgo de agregación (Robinson 1950;
  crítica de Freedman) no es eliminable: por eso TODO claim público lleva la
  cota de Duncan-Davis al lado de la estimación puntual.
- **S4 (demografía):** proyecciones DANE post-censales correctas a nivel
  depto-banda en horizonte de 4 años (riesgo bajo; migración venezolana ya
  absorbida en la base 2018).

## 5. Evidencia de viabilidad (corrida 2026-06-09)

**Cruces (tras fix Bogotá):**

| Cruce | Resultado |
|---|---|
| edad22 ∩ votos22 (escrutinio) | 12.366 puestos · **98,7% de los votos** |
| votos26 con perfil 2022 directo | **88,0%** de los votos domésticos |
| + fallback zona | +8,7% → **96,7%** |
| censo26 ∩ preconteo26 | 100% (13.245/13.245) |
| crosswalk DANE↔RNEC deptos | 33/33 (Consulados queda fuera, sin DANE) |

**Demo EI (Goodman NNLS, sin símplex conjunto — solo direccional):**

2022 (w observado, 5.183 puestos limpios, 15,5M votos): Petro 61% en 18-25
decreciendo con la edad; Fico 84% en 61+ (corner solution, sobre-estimado);
Rodolfo plano 25-50%. Nacional implícito == nacional observado al decimal.
Coincide con los postelectorales públicos de 2022 en dirección y orden.

2026 (w proyectado, preliminar): Cepeda fuerte en 18-25 (~60%) y débil en
61+; Abelardo domina 61+ (~74%) y 36-45; Paloma concentrada en 61+. **NO
publicar estas cifras**: son demo con corner solutions; el estimador final
las moderará y les pondrá cotas e intervalos.

**Exclusiones:** exterior (dep 88), cárceles (zz 98) y puesto censo (zz 90)
— sin geografía estable ni demografía DANE (~2,6% de los votos 2026).

## 6. Limitaciones honestas (van en cualquier entregable)

1. Es inferencia ecológica: estima comportamientos de grupo, no individuos;
   las cotas duras acompañan siempre a la estimación puntual.
2. La banda 61+ es una sola (la RNEC no desagrega 70+/80+) y es justo la que
   más crece (×1,135). Heterogeneidad interna invisible.
3. La composición 2026 es proyectada, no observada (error puesto-nivel ~1,9 pp
   mediana se propaga por bootstrap). Si la RNEC publica Edadygenero 2026, el
   Paso 2 se reemplaza por dato y el modelo mejora gratis.
4. 2026 es preconteo (escrutinio definitivo pendiente); 2022 cubre 87,5% de
   sufragantes con desglose.
5. DANE municipal por edad existe pero no está descargado: hoy el ajuste
   demográfico es departamental. Bajarlo refinaría `ρ_a` a nivel municipio
   (mejora marginal esperada: el backtest dep ya da 0,32 pp).

## 7. Veredicto de viabilidad por nivel

| Nivel | Unidades | Veredicto |
|---|---|---|
| **Puesto (pp)** | ~11.4k con perfil directo | **VIABLE — nivel principal.** Mediana 606 votos/puesto; señal etaria 4× el ruido de proyección |
| Zona (zz) | 2.690 | VIABLE — robustez y fallback (mediana 3.826 votos) |
| Mesa | 112k (2022) | Solo para EI-2022 como chequeo (las mesas no persisten entre elecciones; la proyección exige puesto) |
| Municipio | ~1.100 | Agregación de control y fallback final |

## 8. Pipeline propuesto (si se aprueba)

```
tools/edad-1v-2026/
  extract_edadygenero.py   ✓ hecho (caché mesa-level P1V18/P1V22/P2V22)
  aggregate_votes.py       ✓ hecho (votos 2022/2026 → puesto, totales validados)
  probe_viabilidad.py      ✓ hecho (cruces + DANE + backtest dep)
  demo_ei.py               ✓ hecho (Goodman direccional)
  build_w26.py             ✓ hecho — Paso 2 (ρ por dep, IPF a votos reales 2026
                             por puesto; semillas: 64% puesto · 33% zona · 3% mun)
  fit_ei.py                ✓ hecho — Paso 3: QP símplex (proyección de Duchi 2008,
                             gradiente proyectado con momentos precomputados) por
                             7 estratos regionales + cotas Duncan-Davis + bootstrap
                             cluster-mun B=300 + sensibilidad a error de proyección
  report_edad.py           → pendiente: gráficos (pirámide por candidato, perfil
                             por banda con cotas) para publicación
```

Hallazgos centrales (ver ei-report.txt para la tabla completa):
- 2022: Petro 62% (IC 56-66) en 18-25 cayendo monótono a 3% en 61+;
  Fico 69% (59-76) en 61+; Rodolfo plano (25-37%) con pico en 46-60.
- 2026: Cepeda 60% (54-66) en 18-25 y 7% en 61+; Abelardo crece monótono
  de 23% (18-25) a 79% (72-85) en 61+; Paloma concentrada en 46+ (~10-12%);
  Fajardo-26 con perfil JOVEN (8% en 18-25 vs 2% en 61+ — invierte su 2022).
- Electorado de Abelardo: 38% tiene 61+. El de Cepeda: 49% menor de 36 y
  solo 3% mayor de 60. El de Paloma: 72% mayor de 45.
- Sensibilidad: el error de proyección comprime los contrastes ≤6,5 pp
  (Abelardo) — la dirección de TODOS los hallazgos es robusta; los valores
  extremos (3%, 79%) son los más expuestos al sesgo de agregación de EI y
  se publican siempre con su cota dura al lado.
