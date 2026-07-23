# ricardoruiz.co — Plataforma Electoral Colombia 2026

## Archivos principales
- `electoral.html` — hub de navegación (senado, cámara, consultas)
- `senado-2026.html` — escrutinio senado, todos los toggles y visualizaciones
- `camara-2026.html` — **LISTO** · escrutinio Cámara 2026 espejo de senado. 4 circunscripciones (Territorial · Indígena · Afro · Resultados Generales con WHAT IF), drill territorial Dep → Mun → Zona → Puesto → Mesa, hemiciclo SVG de 165 curules, mapa Leaflet, listas cerradas por depto, race-fix `_rgIIFEToken`, BIG_CITIES toast custom (C.1).
- `endoso-2026.html` — comparación mesa a mesa senado vs cámara
- `previa-1v.html` — simulador de intención presidencial 1ª vuelta
- `oportunidad.html` — **módulo B2B** voto blando afín por candidato (LISTO, ver sección dedicada)
- `veleta.html` — **módulo B2B LISTO** · municipios sensibles al cambio con score por candidato (Cepeda · Abelardo · Paloma). Drill nacional→depto→mun→ciudades-UPL/comunas→barrios. Excel con categoría + proy + censo + Premium PDF top 50. Ver sección dedicada.
- `test-presidencial-2026.html` — **test de arquetipo emocional + lectura LLM** (LISTO v1, ver sección dedicada)
- `combate-electoral.html` — **juego de pelea tipo KOF'98** (parodia, LISTO v1) · candidatos 2026, escalera + jefe final Ricardo, motor canvas 2D. Reemplazó al kart (eliminado). Assets en `combate-electoral/`. Ver sección dedicada.
- `analisis-estructural.html` — **Lab de Políticas Públicas y Prospectiva** · hub del lab + módulo análisis estructural (MicMac · DEMATEL · ISM modernizado, fuzzy, valencias firmadas, copiloto IA) + **sección "Mi informe del lab" (Sprint G)** que une los 6 módulos en un memo combinado (PDF + Markdown). LISTO, ver sección dedicada.
- `mactor.html` — **Lab** · módulo análisis de actores y conflictos (MID + MAO, copiloto IA). LISTO.
- `problema-publico.html` — **Lab** · módulo problema público (Eightfold Path de Bardach condensado a 5 mecánicas + capa metodológica profunda con wizard de síntoma, árbol del problema CEPAL/Ortegón, test Rittel-Webber y selector de marco analítico). Cloud-save + 3 acciones IA + Issue Paper export. LISTO (Sprint A).
- `evaluacion.html` — **Lab** · módulo evaluación de política (OCDE-DAC + Mayne + CEPAL/ILPES + Pre-Analysis Plans + literatura 2020-2026). **8 mecánicas**: pregunta evaluativa (tipo + alcance + tipología Sinergia DNP) · teoría de cambio · indicadores SMART · selector de método (14 métodos · frontera 2020-2026) · criterios OCDE-DAC · análisis económico (CBA · MVPF · CEA) · plan operativo · resultados. Detección automática de tratamiento escalonado con warning TWFE (Goodman-Bacon 2021) redirigiendo a DID escalonado (Callaway-Sant'Anna 2021). Cloud-save + 3 acciones IA + plan .md + **Pre-Analysis Plan .md** (AEA RCT Registry / OSF compatible, 13 secciones con MHT correction pre-registrada) + matriz .csv. LISTO (Sprint B + B v2).
- `alternativas.html` — **Lab** · módulo Alternativas de Política (Zwicky 1969 + Lempert/Walker RDM 2003 + Ritchey + Howard + Keeney + MVPF Hendren 2020 + CEA J-PAL). 6 mecánicas: variables de decisión · opciones por variable · matriz morfológica · alternativas ensambladas · robustez en 4 escenarios + lente económica · decisión final. Cloud-save + 4 acciones IA + memo .md + matriz .csv + ficha CONPES light .pdf + envío bidireccional a problema-publico + envío a AIN. LISTO (Sprint C).
- `ain.html` — **Lab** · módulo Análisis de Impacto Normativo (DNP/Función Pública Decreto 1081/2015 + 1273/2020 + RIA OCDE 2012/2022 + Sunstein Simpler 2013 + Hahn-Tetlock 2008 + Stigler 1971 + Mashaw 2018). 6 mecánicas: problema regulatorio (tipo de falla) · objetivos normativos medibles · opciones regulatorias (6 familias) · matriz de impactos (5 categorías) · consulta pública + 5 riesgos regulatorios · implementación + monitoreo + cláusula de revisión. Cloud-save + 3 acciones IA + memo .md + matriz .csv + memo CONPES regulatorio .pdf + auto-import desde pp/alt + envío a evaluacion. LISTO (Sprint D).
- `lab-recursos.js` — catálogo compartido de 32 recursos en 5 categorías; cargado por los 6 módulos del lab.
- `lab-informe.js` — **Sprint G** · helpers + generador PDF/MD del informe combinado del lab. Lee los 6 localStorage keys y produce un memo CONPES integrado. Cargado solo desde el hub.
- `lab-indicadores.js` — **Sprint E (Fase A)** · helper de indicadores municipales oficiales con panel temporal 2018-2024. 8 indicadores × 1.108 municipios desde datos.gov.co (Policía Nacional + MEN). API lookupMun/getSerie/searchMun/matchIndicadorByKeyword. Cargado por analisis-estructural, problema-publico, ain y evaluacion.
- `prospect-escenarios.html` — **Sprint F + F v2** · séptimo módulo del lab. Escenarios prospectivos por método de los ejes de incertidumbre (Schwartz · GBN), prospectiva estratégica francesa (Godet · Mojica · LIPSOR) y Robust Decision Making (Lempert · RAND). 4 mecánicas: incertidumbres críticas (auto-suggest desde MicMac) · narrativa de 4 cuadrantes · cross-impact con variables/actores/alternativas (Gordon 1968) · decisiones no-regret + señales tempranas. Cloud-save + 2 acciones IA copiloto (sugerir-ejes Pro · narrar-escenarios Premium) + 3 exports (memo .md + matriz .csv + ficha .pdf jsPDF). Integrado al informe combinado del lab (sección 8). LISTO (Sprint F + F v2).
- `comunicar.html` — **Sprint H · v1** · **octavo módulo del lab**. Plan de comunicación de la política pública. 8 mecánicas: contexto + alcance · audiencias (mín 2 / máx 6) · mensaje clave (primario ≤15 palabras + 3 secundarios + valores) · narrativa pública Ganz (Story of Self/Us/Now) · framing Lakoff + Shenker-Osorio (valor central, palabras propias vs adversario) · matriz audiencia × canal con heurística BIT EAST · vocería principal + multiplicadores · cronograma 4 fases + medición OCDE 9-dim. STATE en `localStorage['comunicar-current-v1']`. 3 exports: plan .md, matriz .csv (audiencia×canal + KPIs), guía de mensajes .md para vocería. Auto-import desde PP/Ev/Alt/AIN. Marco metodológico: OCDE Public Communication Report 2021 · CLAD Carta Iberoamericana de Gobierno Abierto 2016 · MIPG · Función Pública (Decreto 1499/2017, Manual v6 dic 2024) · Ley 1712 de 2014 · Ganz · Lakoff 2024 · Anat Shenker-Osorio · BIT EAST 2024 · Stone · Omar Rincón. **Cloud-save + colaboración + 3 acciones IA copiloto** (sugerir-audiencias Pro+ · validar-mensaje Premium+ · narrativa-ganz Premium+) operativos vía worker `/comunicar/*`. PDFs de metodología en S3. LISTO (Sprint H v1 + **v2**).
- `pricing.html` — planes (Básico / Pro 39.900 COP · Premium 99.900 COP · Personalizado)
- `lang.js` — i18n (co/us/cn); `CLAUDE.md` vive en la raíz del repo

## Tareas pendientes — `previa-1v.html`
- **Gráfico temporal de evolución por candidato** (pendiente, prioridad media):
  un line chart ponderado que muestre cómo crece o decrece cada candidato a lo
  largo del tiempo, usando los datos crudos de cada encuesta + los pesos del
  ponderador propio (`Bases de datos/output_ponderador/ponderador-detalle.json`,
  campo `contribuciones`). Cada punto del eje X es una semana ISO; cada línea
  un candidato. Debería respetar el toggle día/noche y la paleta del proyecto.

## Análisis de Candidato — `analisis-candidato.html` (reestructurado jul-2026 · sistema visual v2)

Perfil electoral por candidato (buscador + foto + mapa Leaflet + radar + score).
Reestructura de jul-2026: **nav idéntica a index.html** (sin modo día/noche,
sin breadcrumb), **Helvetica Neue embebida** (Syne solo en el logo), y suma los
**candidatos presidenciales 1V + 2V** al buscador de congreso/consultas.

- **Datos presidenciales**: `tools/analisis-candidato/build_presidenciales.py`
  genera 16 JSONs mesa-a-mesa (13 de 1V + Cepeda/Abelardo 2V + índice) en el
  MISMO formato `endoso/{slug}.json`, desde `PRECONTEO_1V_2026_MESA_con_Claudia.csv`
  + `output_2v/PRECONTEO_2V_2026_MESA.csv` + PUESTOS_GEOREF (nombres). Output
  local gitignoreado: `Bases de datos/output_presidencial_endoso/` (~170 MB).
  Valida contra los 7 totales oficiales del 0247. S3 (frontend lo consume):
  ```
  aws s3 cp "Bases de datos/output_presidencial_endoso/" \
    "s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/presidencial/" \
    --recursive --content-type "application/json" --cache-control "public, max-age=300"
  ```
  El frontend tolera 404 del índice (los presidenciales simplemente no aparecen).
  `?preslocal=1` lee los JSONs locales del repo (verificación pre-subida).
- **Histórico electoral**: una entrada por persona en el buscador
  (`PRES-{persona}`); barra bajo la foto con consulta · 1V · 2V (clickeable,
  cambia la elección cargada). Las consultas se vinculan por slug del índice
  endoso (Paloma/Claudia/Roy).
- **Score renormalizado**: Abelardo 2V (presidente) = **100 en dorado**
  (`--gold`, badge `.presidente`); el resto en azul con
  `round(100·log10(v+1)/log10(vmax+1))` cap 99 (Cepeda 2V=99 · consulta
  Paloma=92 · top senado≈74). `vmax` viene de `index-presidencial.json`.
- **Asamblea Departamental 2023** (para cliente potencial): 3.307 candidatos
  desde `FINAL SUBIDA GCS/GCS_2023TER.csv` (COD_COR='2'). Pipeline
  `tools/analisis-candidato/build_asamblea_2023.py` → un JSON mesa-a-mesa por
  candidato (formato endoso) `ASAM2023-{dde}-{par}-{can}.json` + índice, en
  `Bases de datos/output_asamblea_2023/` (~664 MB, gitignoreado). Asamblea es
  circunscripción **departamental** (32 deptos, sin Bogotá): cada candidato
  colorea un solo depto y drilla a sus municipios. `COD_DDE` es Registraduría
  (Antioquia=1) → casa con el mapa vía `normalizeDepCode`. El buscador lo suma
  como candidato normal (corp "ASAMBLEA · {DEPTO} · 2023", `dataUrl` propio);
  score en la misma escala azul global. `?asamlocal=1` lee los JSONs locales.
  S3: `congreso-2026/output/asamblea-2023/` (subir con `aws s3 cp --recursive`).
- **Base compartida `cand-index.js`** (jul-2026): registro único de candidatos
  con datos mesa-a-mesa, consumido por **analisis-candidato.html**,
  **endoso-2026.html** y **comparar-candidatos.html** (`<script src="cand-index.js">`).
  `window.CandRegistry.load({includeParties,bases})` fusiona los índices de todas
  las fuentes (`SOURCES` = endoso + asamblea-2023 + congreso-2018, extensible) en
  una lista con `dataUrl` por candidato; `CandRegistry.dataUrlFor(slug)` resuelve
  slug → JSON. **Para ampliar a más candidaturas (concejos, JAL, …): agregar una
  entrada a `SOURCES` y las tres páginas la reciben** — no hay que tocar cada HTML.
  Si una fuente no responde, `load` la captura y devuelve `[]` con un warning (las
  demás siguen) → se puede desplegar el código antes de subir sus datos.
  Presidenciales NO están en el registro (modelo por-persona con histórico);
  analisis-candidato los agrega encima leyendo `index-presidencial.json`.
  endoso mantiene partidos en el buscador; comparar y analisis-candidato los filtran.
- **Congreso 2018-2022** (`tools/analisis-candidato/build_congreso_2018.py`, jul-2026):
  2.379 candidatos mesa-a-mesa desde `GCS_2018CON.csv` (1,28 GB · 7,08M filas), en el
  MISMO formato endoso. Mezcla dos ALCANCES: **Senado NACIONAL** (COD_COR=1, CIR=0) y
  las especiales (indígena CIR=4, afro CIR=5) son nacionales → llave SIN depto, mapa
  de los 33 deptos; **Cámara TERRITORIAL** (COR=2, CIR=1) compite en un depto → llave
  CON depto, mapa de un solo depto (igual que asamblea). Slugs: `CON2018-{S|SI|CA|CI}-{par}-{can}`
  (nacionales) y `CON2018-C-{dde}-{par}-{can}` (cámara). Salida local ~1,2 GB en
  `Bases de datos/output_congreso_2018/` (gitignored). Validado: Uribe 891.964 ·
  Mockus 549.734 · Robledo 229.276 en Senado 2018 (cuadran con el resultado oficial).
  S3: `congreso-2026/output/congreso-2018/` (subir con `aws s3 cp --recursive`).
- **Congreso 2022-2026** (`tools/analisis-candidato/build_congreso_2022.py`, jul-2026):
  **2.254 candidatos** mesa-a-mesa desde `GCS_2022CON.csv` (1,2 GB · 6,99M filas), mismo
  formato endoso. ⚠️ **2022 NO usa los códigos de circunscripción de 2018** (verificado):
  Senado nac `(1,1)` [era (1,0)] · Senado indígena `(1,6)` [era (1,4)] · Cámara territorial
  `(2,2)` [era (2,1)] · afro `(2,5)` · indígena `(2,6)` [era (2,4)] · **+2 nuevas:**
  Internacional `(2,0)` (exterior, 2 curules) y **CITREP `(2,7)`** (16 curules de paz).
  **CITREP tiene estructura irregular:** el candidato = una ORGANIZACIÓN (`COD_PAR` único,
  p.ej. Jorge Tovar=428 'Paz es Vida'), `COD_CAN` es marcador constante (501/502), y sus
  votos se reparten en los VARIOS deptos que cubre su distrito → se keyea NACIONAL por
  `(COD_PAR, COD_CAN)` para agregar el distrito en un solo JSON (Tovar 15.272 en
  Cesar+Magdalena+Guajira; Salazar/ASOINTEC 9.672 en Cauca+Nariño+Valle). Slugs:
  `CON2022-{S|SI|CA|CI|CE|CT}-{par}-{can}` (nacionales) · `CON2022-C-{dde}-{par}-{can}`
  (cámara territorial). Salida local ~1,19 GB en `Bases de datos/output_congreso_2022/`
  (gitignored). **Validado:** Miguel Uribe Turbay 226.922 (senador más votado 2022, exacto)
  · Cabal 207.732 · 'Jota Pe' Hernández 194.758 · De la Calle 189.068. Efecto lista cerrada
  esperado: Pacto Histórico Senado = 0 nominal (voto al logo, sin filas por candidato — igual
  que 2018/2026). S3: `congreso-2026/output/congreso-2022/`. Cableado: `con2022` en `SOURCES`
  de cand-index.js + `SRC_YEAR.con2022 = 2022` en analisis-candidato.html.
- **Una entrada por PERSONA + toggle de elecciones** (`agruparPersonas` en
  analisis-candidato.html): el registro trae una entrada por CANDIDATURA, así que la
  misma persona sale varias veces (Senado 2018 · Asamblea 2023 · Congreso 2026). Se
  colapsa por nombre normalizado a UNA entrada de buscador —la candidatura **más
  reciente** (`SRC_YEAR` endoso 2026 > asamblea 2023 > con2018 2018), a igual año la
  más votada— y el resto queda en `congHistBySlug` → la **misma barra de histórico**
  que ya usaban los presidenciales (`renderHistorial` cae a este grupo cuando no hay
  persona presidencial; el pintado se comparte en `pintarHistorial`). 205 personas se
  agrupan 2018∩2026 (Robledo 229k→28,6k · Lidio García 121k→180k · Laureano Acuña
  pasó de Senado a Cámara). Ojo: si la persona es presidencial, esa barra manda (el
  histórico presidencial tiene precedencia sobre el de Congreso).

> **📌 HANDOFF · qué falta de CONGRESO en analisis-candidato (jul-2026)**
>
> **Cobertura hoy:** Congreso **2018** ✓ (`con2018`, subido) · Congreso **2022** ✓
> (`con2022`, subido jul-2026) · Congreso **2026** ✓ (`endoso`) · Asamblea **2023** ✓.
> Presidenciales aparte (modelo por-persona).
>
> **1. ✓ HECHO — Congreso 2022** (`build_congreso_2022.py`, ver entrada arriba). Es el
> término **2022-2026**, el mismo cuyo voto nominal ya construimos (actas de plenaria de
> Cámara 2020-2026, sección Caudal) → ahora la ficha de un representante actual muestra la
> elección del período en que votó, listo para el join con el panel "cómo votó".
>
> **2. FALTA Congreso 2014** (`GCS_2014CON.csv`, 0,8 GB) — extiende la historia.
> **NO existe `GCS_2010CON`**: los archivos de Congreso arrancan en 2014, así que el
> span real es **2014-2026**, no 2010-2026 (corrige la expectativa inicial).
>
> **3. FALTA cablear el panel "cómo votó en el Congreso"** en la ficha. La acción
> `congresista` de la Lambda `caudal-analiza` YA existe y resuelve por nombre
> (subconjunto de tokens) o por `key`; devuelve bancada + alineación con gobierno +
> récord por proyecto. Solo falta llamarla desde analisis-candidato y pintarla.
> Cubre Cámara 2020-2026 (los senadores y quienes no votaron ahí no aparecen).
>
> **Deudas conocidas:** (a) el georef es de 2026 y los datos de 2018 son viejos →
> **17% de mesas sin nombre de puesto** ("PUESTO 00-00"); depto/municipio resuelven
> al 99%, así que el mapa está bien y solo el drill más profundo tiene el hueco.
> (b) Paloma/Roy tienen su Senado 2018 tapado por la precedencia presidencial.
> (c) **Sin verificar en navegador**: el sandbox del preview no baja archivos grandes
> (falla el índice de endoso de 656 KB, Divipole y PUESTOS_GEOREF con "Failed to
> fetch"). La lógica se verificó en Node con los índices reales (8.146 candidaturas
> → 7.739 entradas, 398 personas con toggle), pero **el render de la barra no se ha
> visto** — abrir `analisis-candidato.html` y buscar "Robledo" o "Manzur" para
> confirmar.
- **Fotos**: los 6 grandes usan `Fotos-presidenciales/{slug}.jpg` (campo `foto`
  del índice); consultas vinculadas caen a esa foto si el endoso jpg no existe.
  **Flujo sistematizado de fotos**: carpeta staging `fotos-candidatos/`
  (pendientes/ + subidas/ + LEEME.md, gitignoreada) +
  `tools/fotos-candidatos/sync.py`: `status` cruza índice vs S3 y escribe
  `pendientes.csv` con los slugs exactos ordenados por votos (Ricardo genera la
  imagen en NanoBanana y la guarda como `pendientes/{SLUG}.png`); `subir`
  normaliza (JPG, crop-to-fill centrado al tamaño editorial fijo **1248×864** vía
  sips) → S3 `fotos-candidatos/{SLUG}.jpg` → mueve a subidas/. Valida slugs contra
  el índice —endoso + presidenciales + Asamblea— (`--force` para saltar).

## Módulo Veleta — `veleta.html` (LISTO · B2B)

Producto B2B para equipos de campaña: mapa de **municipios sensibles al cambio
electoral** con score por candidato. Bottom-of-funnel comercial del ciclo
2026 — diferenciador frente a herramientas genéricas porque combina histórico
electoral + ponderador propio + cruce con techo captable por bloque ideológico
en una sola métrica defendible por candidato.

### Score por modo (los 3 modos están implementados)

Score 0–100 por percentil dentro de la cohorte (deptos entre sí, muns
nacionales entre sí, comunas de la ciudad entre sí). El score base se
construye distinto por modo:

**Modo Cepeda** — objetivo: ganar 1ª vuelta con >50%
```
proyCepeda = izq22 × (CepedaNac2026 / izqNac22)
techoCaptable = max(izq10,izq14,izq18,izq22) × scaleIzq + (centro18 / 3)
gap = max(0, 50 − proyCepeda)
captable = max(0, techoCaptable − proyCepeda)  (capped a 10pp)
score = (0.6 · proximidad + 0.4 · plausibilidad) × 100
Si proyCepeda ≥ 50 → score = 35 (ya ganado en 1V, baja prioridad)
```

**Modo Abelardo / Paloma** — objetivo: 2do dentro del bloque derecha
```
derTotal22 = d22 + cd22  // bloque derecha completo en 2022
candProy = derTotal22 × (derPondNac2026 / derNac22) × shareCandNac × HOME_TURF[mode][depCod]
HOME_TURF Abelardo: Costa Atlántica (03, 05, 12, 13, 21, 28, 48) ×1.20 · Antioquia (01) ×1.10
HOME_TURF Paloma:   Cauca (11) ×1.30 · Valle (31) ×1.15 · Antioquia (01) ×1.10 · Boyacá/Cundinamarca ×1.05
techoDer = max(d10+cd10, d14+cd14, d18+cd18, d22+cd22) × scaleDer
captable = max(0, techoDer × shareCand × boost − candProy)
score = (0.7 · proximidad + 0.3 · plausibilidad) × 100
Si proyCand ≥ 50 → score = 35
```

### Drill territorial (4 niveles + ciudades)

1. **Nacional · 33 deptos** (default).
2. **Depto → muns** (~1.100 muns del país).
3. **Ciudad → UPL/comuna** (14 ciudades: Bogotá UPL · Medellín, Cali,
   Barranquilla, Manizales, Pereira, Ibagué, Montería, Bucaramanga, Cúcuta,
   Neiva, Popayán, Sincelejo, Villavicencio).
4. **Ciudad → barrio** (solo Bogotá UPL → 1.001 barrios catastrales, y
   Medellín comuna → ~165 barrios urbanos · ambos Premium).

### Plan gate (modelo B2B)

| Feature | Anónimo | Free | Pro | Premium |
|---|---|---|---|---|
| Cambio de candidato | 1 switch (Cepeda+1) | ✓ | ✓ | ✓ |
| Drill nacional → depto → mun + hover detalle | ✓ | ✓ | ✓ | ✓ |
| Drill mun → 14 ciudades a UPL/comuna | ✗ modal | ✗ modal | ✓ | ✓ |
| Toggle Local / Nacional (cohorte de comparación) | ✗ | ✗ | ✓ | ✓ |
| Drill ciudad → barrios (Bogotá catastral + Medellín) | ✗ | ✗ | ✗ modal | ✓ |
| Descarga Excel (lista completa scope visible) | ✗ | ✗ | 3/mes | 10/mes |
| **Descarga PDF top 50 + metodología** (V.2) | ✗ | ✗ | ✗ modal | 10/mes |

Cuota Excel + PDF compartida con `oportunidad.html` (mismo contador
mensual server-side en `rr-auth /dl/status` + `/dl/consume` con KV
`RR_DL`).

### Descargas (Sprint V)

**Excel** — 2 hojas:

- *Metodología*: explicación del score por modo + tabla de **categorías**
  (V.1) + cómo descargar agregado por UPL/comuna (V.3).
- *Datos*: header con `candidato, modo, scope, nivel, rank, nombre, depto,
  mun_elec, upl_o_comuna, barrio, loc_codigo, loc_nombre, proy_pct,
  categoria, score, censo, fecha_export`. Para barrios Bogotá:
  `loc_codigo` + `loc_nombre` permiten reconstruir agregados por localidad
  (los barrios catastrales no traen UPL pre-asignada).

**Categoría por candidato (helper `_categoriaFor`, V.1):**

| Candidato | Tier | Threshold |
|---|---|---|
| Cepeda | Ya proyecta >50% (asegura 1V) | `proy ≥ 50` |
| Cepeda | A menos de 5 pp del 50% (esfuerzo más rentable) | `45 ≤ proy < 50` |
| Cepeda | Entre 5 y 15 pp del 50% (campaña fuerte) | `35 ≤ proy < 45` |
| Cepeda | A más de 15 pp del 50% (bastión opositor) | `proy < 35` |
| Abelardo/Paloma | Base sólida | `proy ≥ 25` |
| Abelardo/Paloma | Base media | `15 ≤ proy < 25` |
| Abelardo/Paloma | Base débil | `proy < 15` |

Los thresholds son idénticos a los que muestra el panel lateral de la UI.

**PDF Premium top 50** (V.2) — `_buildAndDownloadVeletaPDF` con jsPDF 2.5.1
on-demand desde jsdelivr. Página 1: tabla top 50 con #, territorio, depto,
score, proy_pct, categoría (top 10 highlighted en accent oxblood/orange).
Página 2: metodología completa por modo + cómo descargar UPL agregada +
fuentes. Footer con disclaimer "borrador automático".

**Title dinámico de los botones de descarga** (V.3) — `renderDlCounter`
actualiza el title de `#dl-btn` y `#dl-btn-pdf` con el scope actual y
hints contextuales: "Para descargar UPL/comuna: click en mun capital
(Bogotá → 16-001)" cuando el cliente está en vista nacional/depto.

### Datos de entrada (S3)
```
bases+de+datos/output_ponderador/proyeccion-por-mun.json
bases+de+datos/output_ponderador/proyeccion-por-barrio-bogota.json
bases+de+datos/output_ponderador/proyeccion-por-barrio-medellin.json
ricardoruiz.co/oportunidad-2026/ciudades/*.json        (proyección por UPL/comuna)
mapas-2026/DEPARTAMENTOS2.json                          GeoJSON deptos
mapas-2026/Departamentos-mps/{cod}.json                 GeoJSON muns por depto
mapas-2026/Ciudades-COM-LOC/{CITY}X.json                GeoJSON comunas/UPL
mapas-2026/BOG-BARRIOS-CATASTRALES.json                 1.001 barrios Bogotá
mapas-2026/MEDELLIN-BARRIOS.json                         ~165 barrios Medellín
```

### Riesgo metodológico documentado en footer

- **HOME_TURF heurístico**: sin polling per-mun que separe Abelardo de
  Paloma, el boost regional es una heurística declarada (Costa+Antioquia
  para Abelardo, Cauca+Valle+Antioquia para Paloma). Documentado en el
  footer y en la hoja Metodología del Excel.
- **Ancla izquierda 2022**: la proyección de Cepeda usa el bloque izquierda
  agregado 2022 (Petro) como ancla. Defendible (eje principal de la
  contienda 2026) pero un consultor experto lo va a preguntar.

## Módulo Oportunidad — `oportunidad.html` (LISTO · B2B)

Producto B2B complementario a Veleta: si Veleta dice **dónde se decide la
elección**, Oportunidad dice **dónde un candidato específico puede crecer**.
Voto blando afín por candidato sobre 4 fuentes históricas, NS-NR redistribuido
por territorio + transferencia intra-bloque + abstención.

### Fórmula vigente (v3)
- `proj_base(C, M) = pondPct(C) × bias_C(M)` — punto de partida del candidato.
- `gap_local = proj_base × (NS-NR/sumDeclarado) + Σ_donor xferFrac × pondPct(donor) × bias_donor(M)`.
- `contrib_nac = gap_local × censo_M / censo_nacional`.
- `bias_C(M)` = pct afín local / pct afín nacional, ponderado por 4 buckets
  (pres-22, congreso-26, pres-18, consultas) con pesos editables.
- Bloques amplios para transferencia: ic↔rb↔cl↔lm, pv↔ae, sf↔cl↔rb↔lm.
- 6 candidatos: ic (Cepeda) · ae (De la Espriella) · pv (Paloma) · sf (Fajardo)
  · cl (Claudia) · rb (Roy).

### Niveles de granularidad (drill-in)
1. Nacional · departamental (33 deptos).
2. Depto → municipios (~1.100).
3. 14 ciudades · comunas/localidades.
4. Medellín · barrios (147) — click en comuna abre **sólo los barrios de esa comuna**.
5. Bogotá · UPL (33) o Localidades — click abre **barrios de esa UPL/localidad**.
6. Bogotá · barrios catastrales (1.000).
7. Puestos (~13.5k a nivel país) — capa Premium.

**Bogotá** salta el nivel "municipio" desde el mapa nacional (un solo mun 001
= Bogotá D.C., no aporta nada como paso intermedio). Onclick depto 16 →
directo a localidades. Back desde Bogotá ciudad → directo a nacional.

### Plan gate (modelo B2B)
Estados: **anonymous → free → pro → premium → full**. Lee `user.plan` del
worker `rr-auth.reruizc.workers.dev/auth/me` (mismo contrato que dashboard).

| Feature | Anónimo | Básico | Pro | Premium |
|---|---|---|---|---|
| Mapa nacional + dep + mun + hover detalle | ✗ modal | ✓ | ✓ | ✓ |
| Cambio de candidato | 1 switch gratis (Cepeda+1) | ✓ | ✓ | ✓ |
| Capa Oportunidad + Abstención | ✗ modal | ✓ | ✓ | ✓ |
| Ciudades comunas (8) + UPL Bogotá + Barrios MDE/BOG | ✗ | ✗ modal Pro | ✓ | ✓ |
| Transferencia intra-bloque + sliders pesos | ✗ | ✗ candado Pro | ✓ | ✓ |
| Descarga CSV (lista completa) | ✗ | ✗ modal Pro | 3/mes | 10/mes |
| Capa Puestos (~13.5k) | ✗ | ✗ | ✗ modal Premium | ✓ |
| Reporte territorial PDF (top 50) | — | — | — | ✓ |

Helpers JS: `loadUserFromStorage` + `refreshUserFromAPI` (al cargar);
`hasFeature(name)` + `requireFeature(name)` (gate por acción);
`openBlockedModal(feat)` con copy específico por feature.

UI del gate:
- **Chip "Plan: X · ↑ Upgrade"** en la nav (link a `pricing.html`).
- **Modal de bloqueo** con tag, título, descripción, precio (Pro $39.900 ·
  Premium $99.900), CTA primario (`pricing.html` o `register.html` si anónimo)
  + **login inline** dentro del mismo modal (form email+password → POST
  `/auth/login`, sin sacar al usuario de la página).
- **Lock overlay 🔒** sobre los panel-cards de Transferencia y Pesos cuando
  tier < Pro (captura el click → modal).
- **Welcome modal** anónimo en primer visit (flag `opo-welcome-shown` en
  localStorage).

### Cuota de descargas
Persistida client-side por mes (`opo-dl-YYYY-MM` en localStorage). El frontend
intenta hablar primero con el worker (`GET /dl/status`, `POST /dl/consume`) y
cae a localStorage si retorna 404. **Snippet listo para pegar en el worker
`rr-auth`** vive en `tools/rr-auth-downloads-route.md` — usa KV namespace
`RR_DL` con TTL 45 días. Bumpear `DL_QUOTA` en frontend si cambian los números.

### Descarga CSV vs PDF
- **CSV (`Lista (CSV)`)**: exporta `STATE._topItemsAll` — lista COMPLETA del
  scope visible (33 deptos / N muns del depto / N comunas / 33 UPL / ~1k
  barrios BOG / 147 barrios MDE / puestos visibles).
- **PDF (`Top 50 (PDF)`)**: jsPDF cargado por CDN al primer click. Header con
  candidato + mensaje táctico + métricas globales + tabla top 50 + footer
  metodológico. Sólo visible para Premium+.
- Ambos consumen del mismo contador.

### Limpieza de datos · puestos especiales (mayo 2026)
Aprendizaje doloroso: los puestos zona **90 (PUESTO CENSO, ej CORFERIAS)** y
**98 (cárceles)** son ruido para el cruce geográfico — recogen votantes sin
asignación específica e inflan artificialmente el barrio donde están
físicamente.

Fix por capa:
- `tools/build-bog-barrio.py` y `tools/build-mde-por-barrio.js`: filtran
  zona 90 y 98 antes del cruce a barrios. Re-correr y subir a S3 cuando se
  modifiquen los inputs (PUESTOS_GEOREF.csv o las señales).
- Frontend (`computeCityComunaMetrics`, `precomputeCityNacAfin`): excluye los
  agregados especiales `OTROS`, `CORR`, `CIUDAD` que los build scripts dejan
  en `por_comuna.json`. Cubre las 13 ciudades por comuna sin re-correr nada.

### Match puesto → barrio catastral (Bogotá)
El GeoJSON catastral oficial (1.000 barrios) NO coincide 1:1 con los nombres
del CSV PUESTOS_GEOREF. Ejemplo: el puesto físico "CENTRO NARIÑO" tiene un
centroide que cae en el polígono catastral "Ortezal" por PIP. Fix en
`build_puesto_to_barrio` (cascada de 3 niveles):
1. **Match por nombre normalizado** (BARRIO del CSV vs `nombre` del GeoJSON) → 551 puestos.
2. Match removiendo sufijo de 1-2 caracteres ("QUINTA PAREDES B" → "QUINTA PAREDES").
3. Fallback PIP por lat/lon → 493 puestos sin match nominal.

### Cache de JSONs (cache-buster)
Safari es agresivo con cache de JSON sin Cache-Control. `loadBogBarrioSignals`
agrega `?v=YYYYMMDD` a las URLs de `bog-barrio-*.json` y `censo-barrio-*.json`.
**Bumpear el valor (`v = 'YYYYMMDD'` dentro de la función) cuando se
regeneren outputs.**

### Mobile (`@media (max-width:640px)`)
Bloque completo de overrides al final del `<style>`. Padding lateral 2.5rem→1rem
en todos los containers, chips/fuentes escalados, `cand-pill` 15% más
pequeños, top-row con grid apretado, descargas en 2 columnas full-width,
modal scrollable, **chip de nombre al tap** sobre el mapa de barrios Bogotá
(`#map-tap-name`, auto-hide 2.5s, sólo mobile vía CSS).

### Estructura del top + scope label
`collectScopeItems()` devuelve `{ items, unitLabel, scope, displayTopN }` con
la lista COMPLETA del scope activo (ordenada por contribución desc). El
`scope` refleja el padre cuando hay drill a barrios: "Medellín · Comuna 14 El
Poblado", "Bogotá · Chapinero", "Bogotá · UPL CHAPINERO ALTO". Vista general
muestra **top 10 departamentos**; con depto activo, **top 10 muns**; en
puestos, top 15; resto, top 12.

### S3 paths (datos del módulo)
```
bases+de+datos/output_ciudades/bogota/
  bog-barrio-{pres-2010,2014,2018,2022,consulta-2025-pacto,
              consulta-2026-{gran,frente,soluciones},senado-2026,camara-2026}.json
  censo-barrio-{2018,2022,2026}.json
  bog-puesto-to-barrio.json
  por_comuna por_upl etc.
bases+de+datos/output_medellin/por-barrio/
  {alc,concejo}-{2015,2019,2023}-mde.json + pres + consultas + senado/cámara 2026.
bases+de+datos/output_ciudades/{cali,barranquilla,…}/   por-comuna por señal.
```

### Estado actual
**LISTO en producción.** Bloques A→D del plan gate cerrados. Build scripts de
Bogotá y Medellín actualizados. Datos limpios en S3. Mobile OK. PDF Premium
operativo. Cuota de descargas server-side: `/dl/status` + `/dl/consume`
desplegados en `rr-auth` (binding KV `RR_DL`) — el frontend ya consume
estos endpoints; si el worker falla cae a localStorage como fallback.

## Ponderador propio

Pipeline en `tools/ponderador/` que calibra firmas encuestadoras contra el
único ground truth post-Ley 2494: las consultas del 8 de marzo de 2026.

### Scripts (todos stdlib pura, sin deps)
```
tools/ponderador/
  scrape_cne.py    refresca cne_encuestas_2026.{json,csv} desde
                   https://www.cne.gov.co/encuestas-2026 (paginado).
                   Maneja casos rotos del CNE (firma=fecha, texto truncado).
                   Flags: --dry-run --diff --out-dir. Curl por subprocess
                   (esquiva el TLS de python 3.14 sin certifi).
  remap_ids.py     renombra ids del ponderador a los ids reales del CNE
                   cuando una encuesta entró a mano antes de radicación.
                   Mapping hardcoded; --apply para escribir (deja .bak).
  ponderador.py    re-calcula q_firma/q_modo/promedios y emite
                   ponderador-actual.json + ponderador-detalle.json.
```

### Reconstrucción del `ponderador.py` (2026-05-20)
El .py original se extravió; solo sobrevivía
`__pycache__/ponderador.cpython-314.pyc`. La reconstrucción combina:
- **docstring + nombres de funciones** del .pyc vía `marshal` + `dis`
- **bytecode** de `calcular_q_firma` / `calcular_q_modo` / `delta_recencia`
  — el mapeo lineal MAE→q_firma quedó confirmado:
  `q = 1 - 0.6·(mae - mn)/(mx - mn)`, MAE [mn, mx] → q ∈ [1.0, 0.4]
- **re-cómputo client-side en `previa-1v.html` líneas 6938-7013**
  (mismas constantes, fórmula `peso = q_firma × q_modo × exp(-λ·d)`)

Validado: `python3 ponderador.py` sin overrides + HOY=2026-05-15 reproduce
el `ponderador-actual.json` original al cent.

Si el .pyc también se pierde: `previa-1v.html` tiene la fórmula y todas
las constantes documentadas en comentarios. Re-validar contra el último
`ponderador-actual.json` archivado.

### Q_FIRMA_OVERRIDE — sub-pondera por encuesta_id
Dict hardcoded al inicio de `ponderador.py`. Para casos puntuales en que
una firma sin calibración debe entrar atenuada (cocina compartida entre
dos firmas, sospecha de manipulación, etc.). Se aplica ANTES del fallback
a q_firma calibrada / default 1.0.

Estado actual (2026-05-20):
```python
Q_FIRMA_OVERRIDE = {
    "45-genesis-may11":   0.45,  # cocina compartida con Corp MMM
    "46-corp-mmm-may17":  0.45,  # Casanare 27-feb radicado bajo
                                 # ambos sellos con cifras idénticas
                                 # (id 24-genesis-crea y 26-corp-mmm)
}
```

### Datos de entrada y salida
```
Bases de datos/cne_pdfs/                 → PDFs descargados a mano del CNE
Bases de datos/cne_encuestas_2026.json   → inventario scrapeado (scrape_cne.py)
Bases de datos/cne_encuestas_clasificadas.csv  → con auto-clasificación
Bases de datos/encuestas_porcentajes.csv → % por candidato (manual desde PDF)
Bases de datos/encuestas_distribucion_muestral.csv → muestra por depto
Bases de datos/output_ponderador/ponderador-actual.json  → consume previa-1v.html
Bases de datos/output_ponderador/ponderador-detalle.json → transparencia total
Bases de datos/output_ponderador/representatividad.json  → KL vs censo Divipole
```

### Flujo típico cuando aparece encuesta nueva
1. `python3 tools/ponderador/scrape_cne.py --diff` — ve qué hay nuevo en CNE.
2. Si la encuesta NO está en CNE (heyzine/Wikipedia/prensa): agregar a mano
   filas a `cne_encuestas_clasificadas.csv` (id + metadatos) y
   `encuestas_porcentajes.csv` (un row por candidato).
3. Si los ids manuales coinciden con ids posteriores del CNE:
   `python3 tools/ponderador/remap_ids.py --apply`.
4. `python3 tools/ponderador/ponderador.py` — regenera JSONs.
5. Subir a S3 para que el frontend los consuma:
   ```
   aws s3 cp "Bases de datos/output_ponderador/ponderador-actual.json" \
     "s3://elecciones-2026/ricardoruiz.co/bases de datos/output_ponderador/ponderador-actual.json"
   aws s3 cp "Bases de datos/output_ponderador/ponderador-detalle.json" \
     "s3://elecciones-2026/ricardoruiz.co/bases de datos/output_ponderador/ponderador-detalle.json"
   ```
6. Si actualizas `previa-1v.html` para mostrar firmas/Q nuevas, bumpear
   también las constantes `FIRMA_Q` y `POLLS` (línea 6890-6936)
   para que el chart temporal y el promedio coincidan.

### Decisiones metodológicas (resumen)
- Sólo el 8-mar como benchmark (Ley 2494 cambió la regla del juego).
- MAE filtra candidatos extintos antes de normalizar (Cepeda no estuvo en Frente).
- `q_firma` ∈ [0.40, 1.00]; firmas no calibradas entran con 1.00 + bandera.
- House effect post-marzo vs mediana semanal por candidato.
- Representatividad muestral: KL + χ² + bandera por depto |delta|≥5pp.

## Admin del sitio
- **Email administrador único: `reruizc@gmail.com`** (whitelist en
  `admin-analytics.html`, `admin-pronosticos.html` y `PRIVATE_TOOLS` de
  `dashboard.html`). El gate hace triple chequeo: localStorage user +
  `/auth/me` del worker + whitelist hardcodeada.

## Concurso "Tu Pronóstico" — `pronostico-1v.html` (wizard) + backend

Wizard mobile-first (10 pasos) que recoge un pronóstico de 1ª vuelta y
lo guarda para el concurso de **$100.000 al más certero** (menor MAE vs
resultado oficial). Flujo: intro → concurso+PDF reglas → ponderador →
participación → candidatos (2 slides de 3) → voto blanco → mapa
(municipal, bloqueado) → **datos del participante** → compartir.

- **Sin login.** El concurso es abierto: el paso "datos" pide nombre,
  apellido, depto, municipio (+ comuna/localidad si Bogotá/Medellín/
  Cali), correo y WhatsApp. El correo es el identificador único.
- **Backend en worker `rr-auth`** (`/Users/ricardoruiz/rr-auth/src/index.js`,
  no es repo git — deploy con `cd /Users/ricardoruiz/rr-auth && npx
  wrangler deploy`):
  - `POST /pron/save` — sin auth. Valida campos + suma de pcts ≈ 100.
    Guarda en `RR_STORE` bajo `pron:${correo}`. Conserva `createdAt`
    del primer envío, refresca `updatedAt`. Reescribe si reenvía.
  - `GET /pron/me?correo=` — devuelve el registro de ese correo.
  - `GET /pron/admin/all` — `adminGuard` (sesión admin). Dump paginado
    (hasta 5k) para calcular el ganador.
- **Dashboard admin:** `admin-pronosticos.html` (card en `PRIVATE_TOOLS`,
  solo `reruizc@gmail.com`). KPIs + tabla + exporta CSV. Tiene un bloque
  para ingresar el resultado oficial y calcular el ranking por **MAE**
  (promedio de |pronóstico − real| en pp sobre participación + cada
  candidato + blanco); desempate por `createdAt` más antiguo.
- **PDF de reglas:** `tools/build-reglas-pronostico-pdf.py` (reportlab)
  → `Bases de datos/pronostico-1v/reglas-pronostico-1v-2026.pdf` →
  S3 `DESCARGAS/reglas-pronostico-1v-2026.pdf` (prefijo público).
  Cubre: en qué consiste, sistema de elección del ganador, cláusula de
  que NO es apuesta (Ley 643/2001), tratamiento de datos (Ley 1581/2012).
  Re-generar y re-subir si cambian las reglas.
- Cifras del wizard arrancan del ponderador (`ponderador-actual.json`,
  igual que `previa-1v.html`); el mapa reusa todo el motor de bias
  territorial de `previa-1v.html`. `WIZ_PHOTO` apunta a fotos en
  `Fotos-presidenciales/` (S3, slugs lowercase).

## Worktree y deploy
```
worktree activo: /Users/ricardoruiz/ricardoruiz.co/.claude/worktrees/agitated-rosalind/
deploy:          git push origin HEAD:main   (desde dentro del worktree)
```

## AWS / S3
AWS CLI v2 instalado vía Homebrew (`/opt/homebrew/bin/aws`).
- Cuenta AWS: `167386641785`
- Usuario IAM: `ricardo-mac-cli` (creado 2026-05-07, dedicado al CLI local)
- Política adjunta: `elecciones-2026-rw` (custom, scoped sólo al bucket
  `elecciones-2026`: `s3:ListBucket` + `GetBucketLocation` sobre el bucket
  y `Get/Put/Delete/GetAcl/PutAclObject` sobre objetos)
- Region default: `us-east-1`
- Credenciales en `~/.aws/credentials` (modo 600)

Comandos típicos que se pueden invocar directamente:
```bash
aws s3 cp <local> s3://elecciones-2026/<prefijo>/         # subir 1 archivo
aws s3 cp <dir>/ s3://elecciones-2026/<prefijo>/ --recursive
aws s3 sync <dir>/ s3://elecciones-2026/<prefijo>/         # solo cambios
aws s3 ls s3://elecciones-2026/<prefijo>/                 # listar
aws s3 rm s3://elecciones-2026/<prefijo>/<key>            # borrar
```

**Nunca usar `--delete` con `sync`** salvo confirmación explícita del
usuario (borra del destino lo que no esté en origen — pérdida de datos
silenciosa). Para el prefijo con espacio literal (`bases de datos/`),
en CLI usar comillas: `"s3://elecciones-2026/bases de datos/..."` (NO
codificar como `bases+de+datos/`; eso es solo para URLs públicas en el
frontend).

Aún así, **antes de borrados masivos o re-uploads de muchos archivos,
confirmar con el usuario** la ruta destino y mostrar lista de archivos
afectados. El usuario sigue prefiriendo control sobre cuándo y qué
sube/borra; el CLI es para automatizar las tareas tediosas, no para
actuar por iniciativa propia sobre datos en producción.

## Entrega de archivos al usuario
**NUNCA** dejar artefactos en `~/Desktop`, `~/Downloads` o paths fuera del
proyecto. **SIEMPRE** entregar dentro de `/Users/ricardoruiz/ricardoruiz.co/`
y elegir la subcarpeta acorde al proyecto:
- Proyecto DC (Medellín 2027) → `Bases de datos/proyecto-dc/<modulo>/`
- Datos electorales 2026 → `Bases de datos/output_*/...` o `Bases de datos/<categoria>/`
- Scripts / build tools → `tools/<modulo>/` (worktree, gitignored si genera artefactos)

Si la subcarpeta no existe, crearla con `mkdir -p` en una ruta semánticamente
clara. El worktree (`/.claude/worktrees/.../`) está oculto en Finder, así que
los artefactos finales que el usuario va a manipular (zips de deploy, CSVs
para subir a S3, exports) deben vivir en el repo principal, no en el worktree.

## Pipeline de históricos — `tools/build-historicos.js`
Script Node (streaming, sin dependencias) que procesa un archivo GCS de
la Registraduría y genera tres JSONs agregados por elección:
```
tools/build-historicos.js <archivo.csv> <out-dir> [--meta k=v,k=v]
  → {out-dir}/resumen.json     (~2 KB,  nacional por candidato)
  → {out-dir}/por-depto.json   (~30 KB, depto × candidato)
  → {out-dir}/por-mun.json     (~1 MB,  mun × candidato)
```
Normaliza nombres (MAYÚS sin tildes). `COD_CAN` 996/997/998/999 se
agrupan en `especiales` aparte; el porcentaje de cada candidato se
calcula sobre `votos_validos` (excluyendo especiales). Procesa 100 MB
en ~1,5 s en una laptop.

**Outputs locales** (gitignored, no subir al repo):
```
/Users/ricardoruiz/ricardoruiz.co/Bases de datos/output_historicos/
  pres-2010-v1/{resumen,por-depto,por-mun}.json
  pres-2014-v1/{resumen,por-depto,por-mun}.json
  pres-2018-v1/{resumen,por-depto,por-mun}.json
  pres-2022-v1/{resumen,por-depto,por-mun}.json
  consulta-2025-pacto/{resumen,por-depto,por-mun}.json
```
Subir a S3 bajo `ricardoruiz.co/congreso-2026/output/historicos/`.

## Data — S3
```
const S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output';
senado/resumen.json          → totales nacionales, partidos[], curules D'Hondt
senado/departamentos.json    → array de deptos con por_circunscripcion
senado/departamentos/{cod}/municipios.json
senado/departamentos/{cod}/puestos.json
senado/departamentos/{cod}/mesas.json
mapas-2026/DEPARTAMENTOS2.json          → GeoJSON departamentos Colombia
mapas-2026/Departamentos-mps/{cod}.json → GeoJSON municipios por depto (pad 2 dígitos)
mapas-2026/Ciudades-COM-LOC/BOG-LOCALIDADX.json → Bogotá localidades (depCode=16)
mapas-2026/PUESTOS_GEOREF.csv           → georreferenciación de puestos (NO usar para censo)
Divipole-actualizado/COMUNAS_DATA.csv   → censo electoral oficial: dd, mm, zz, pp,
                                          mujeres, hombres, total (41.287.084 total nacional)
```

## Censos electorales históricos (Divipole por elección)

Para calcular abstención de elecciones pasadas hace falta el censo
*de la época*, no el actual. Los Divipole oficiales que tenemos:

```
Bases de datos/Divipol 23.09.2021.xlsx     → censo previo a pres-2022 1V (38.6M nacional)
                                             shape: dd, mm, zz, pp + departamento, municipio,
                                             puesto, mujeres, hombres, total, mesas, comuna,
                                             dirección. Procesado a JSON por
                                             tools/build-censo-divipole.py.
Bases de datos/Edadygenero2018Congreso.xlsx → NO ES XLSX. Header TCicada v2.0 2017-05-26
                                             (formato propietario Registraduría). No abre con
                                             openpyxl/Excel — re-pedir a Registraduría en CSV.
```

Divipole 2018 oficial NO disponible. Para abstención pres-2018:
opción A) pedir CSV a Registraduría; opción B) usar censo 2022 como
proxy (cambios marginales 2018→2022); opción C) reconstruir con
proyecciones DANE.

## Análisis demográfico de votantes — `Bases de datos/Edadygenero.xlsx` (~135 MB)

Archivo Registraduría con **votantes por mesa desglosados por edad y
género** para 2018, 2019, 2022 y 2023. Estructura: 645k filas × 47
columnas. Filtros: columna `Año` y columna `Datos de tipo de elección`
(`Congreso de la República` / `Presidencia 1V` / `Presidencia 2V` /
`Autoridades Locales`).

Cobertura por (año, tipo):
- 2018 Congreso (103.779 mesas, 17.8M votantes)
- 2018 Presidencia 1V (97.638, 19.6M)  ← cuadra con oficial 19.61M
- 2019 Autoridades Locales (107.684, 22.2M)
- 2022 Congreso (112.012, 18.8M)
- 2022 Presidencia 1V (112.012, 18.8M)  ← falta vs oficial 21.5M
- 2022 Presidencia 2V (112.012, 18.8M)
- 2023 Autoridades Locales (248 mesas — incompleto, ignorar)

Las 3 elecciones 2022 con cifras idénticas (18.8M) sugiere que solo
trajeron sufragantes con desglose válido — falta ~2.7M cuyas mesas no
tenían breakdown demográfico. Para conteo total de votantes 2022 usar
los archivos GCS, no este.

**Columna "Cantidad de Sufragantes" = personas que VOTARON** (no
censo). Confirmado al sumar 2018 contra cifra oficial (match 99.9%).
**NO usar como denominador de abstención.** Sí usar para:
- Análisis demográfico de votantes (módulo futuro: pirámide poblacional
  electoral, sesgos de edad por candidato, etc.).
- Validación cruzada de votos totales por mesa con GCS.

Depto 88 (Consulados/Exterior) sí está incluido.

**⚠️ Gotcha de llaves (descubierto jun-2026):** en Bogotá la columna
`Cód. Comuna / Localidad` trae el **NOMBRE de la localidad** ("Usaquén",
"Suba"…), no el código de zona. Mapear con el dict canónico Usaquén=01 …
Sumapaz=20, Corferias=90, Cárceles=98 (ya implementado en
`tools/edad-1v-2026/probe_viabilidad.py::BOG_LOC`). El resto del país sí
trae la zona electoral numérica y matchea con GCS/preconteo casi 1:1.

## Análisis etario 1V 2026 — `tools/edad-1v-2026/` (LISTO · pipeline corrido 2026-06-09)

Composición etaria del voto por candidato 1V-2026 vs 1V-2022 vía inferencia
ecológica a nivel **puesto**, con composición de votantes 2026 **proyectada**
(Edadygenero 2022 × proyecciones DANE dep × raking IPF a votantes reales por
puesto). **Spec formal completa en `tools/edad-1v-2026/MODELO.md`** (4 pasos:
perfil 2022 con gates de calidad → proyección demográfica → EI RxC con cotas
Duncan-Davis + QP símplex + opcional bayesiano → comparativo 2022/2026).

### Cómo se saca la edad + alcances puesto vs mesa

- **De dónde sale la edad:** `Edadygenero.xlsx` (RNEC) trae SUFRAGANTES por
  mesa × edad (10 bandas: 18-20, 21-25 … 56-60, "Mayor a 60"=61+) × sexo para
  2018/2019/2022/2023. Dice CUÁNTOS votaron por banda en cada mesa, NUNCA por
  quién. La edad por candidato es SIEMPRE estimación ecológica (cruzar la
  variación de composición etaria entre puestos con la variación del voto).
- **2026 aún no existe** → se PROYECTA: perfil etario 2022 del puesto ×
  envejecimiento DANE por depto (ρ_a=sufragantes/población, aplicada a DANE
  2026) × raking IPF a los votantes reales del preconteo por puesto. El nivel
  es dato; solo la mezcla interna es modelo. Cuando la RNEC publique
  Edadygenero 2026 (rezago ~1-2 años), la proyección desaparece y todo pasa a
  observado — re-correr `fit_ei.py` sin más.
- **Por qué PUESTO y no mesa** (el dato crudo SÍ es mesa: 112.012 mesas 2022 ·
  121.863 preconteo 2026 → ~12,4k puestos con perfil · muestra EI 9.346 con
  ≥200 votos): las mesas NO persisten entre elecciones — se asignan por orden
  de cédula y la numeración se rearma con el censo — así que la proyección
  2022→2026 exige unidad territorial estable. Mesa mediana ~200 votantes vs
  ~600 del puesto. Usar puesto NO sesga vs mesa: solo ensancha el IC, y ese
  costo ya está incluido en el ± publicado.
- **Alcance mesa (upgrade v2, decidido NO por ahora · jun-2026):** el orden de
  cédula genera sorting etario brutal entre mesas del MISMO puesto (mesas
  bajas = inscritos viejos; cédulas viejas de mujeres arrancan en 20M → también
  sorting por sexo). Comparar mesas jóvenes vs viejas del mismo puesto =
  efectos fijos de puesto → mata la confusión edad↔ingreso (la que acorrala
  Cepeda-61+ a 0% en ciudades). EI-2022 a mesa se puede correr YA (edad
  observada, 112k mesas, sirve como validación dura). Para 2026: aprender el
  patrón rango-de-mesa→perfil con 2022 (validable 2018→2022) + raking (~1 día
  de trabajo). Vale la pena montarlo antes del análisis de la 2V (21-jun).
- **Precisión publicable (puesto):** IC95 nacional ±3-6 pp típico (peor ±10 en
  36-45, donde se cruzan las líneas); ciudades (duelo estratificado) ±3 pp
  típico, máx ±9 en 61+. Decir "95% de confianza" (no "probabilidad de 95%");
  analogía válida: "margen de error similar al de una encuesta grande". El IC
  cubre muestreo; el error de proyección va aparte (atenúa ≤6,5 pp, los
  contrastes reales serían ≥); el sesgo de agregación no es cuantificable →
  cotas duras junto a valores extremos.

Probe de viabilidad corrido (2026-06-09), todo VIABLE:
- Cruce edad22∩votos22 = 98,7% de votos · votos26 con perfil directo 88% (+8,7% zona).
- Backtest del supuesto de proyección 2018→2022: MAE nacional 0,32 pp por banda.
- DANE↔RNEC crosswalk dep 33/33 por nombre. Factores 22→26: 61+ ×1,135 (la banda que más crece).
- Demo Goodman reproduce 2022 conocido (Petro joven / Fico 61+) con consistencia nacional exacta.
- Edadygenero 2022 cubre 87,5% de sufragantes → gate `cov∈[0.70,1.10]` por puesto, fallback zona→mun.

Scripts (todos corridos): `extract_edadygenero.py` (caché mesa P1V18/P1V22/
P2V22), `aggregate_votes.py` (votos→puesto, validados al voto exacto),
`probe_viabilidad.py`, `demo_ei.py`, `build_w26.py` (proyección+IPF; semillas
64% puesto/33% zona), `fit_ei.py` (QP símplex 7 estratos + cotas Duncan-Davis
+ bootstrap mun B=300 + sensibilidad). Outputs en `Bases de datos/
output_edad_1v/` (`ei-report.txt` = tabla final con IC; `ei-final.csv` long).
**Resultados clave:** 2026 Cepeda 60% en 18-25 y 7% en 61+; Abelardo monótono
23%→79% en 61+; Paloma concentrada 46+; Fajardo-26 perfil joven (invierte su
2022). 2022: Petro 62% jóvenes/3% mayores · Fico 69% en 61+. Electorado de
Abelardo 38% es 61+; el de Cepeda 49% <36. **Regla de publicación:** valores
extremos siempre con cota dura al lado; IC no incluye sesgo de agregación;
el error de proyección ATENÚA (compresión ≤6,5 pp) — los contrastes reales
serían ≥ los reportados. Gotcha EIV: NO meter el ruido de proyección al
bootstrap de los IC (atenúa y el IC deja de contener el punto); va aparte
como sensibilidad. `report_edad.py` = gráficos nacionales (líneas/barras
light+dark).

**Geo + carrusel de redes (jun-2026):**
- `build_blocs_depto.py` — margen izq/der + **pista limpia del Pacto
  (Petro→Cepeda) por depto** → `blocs-depto.csv`. OJO: el margen der−izq tiene
  **artefacto Rodolfo** (sus ~6M de 2022 clasificados como derecha inflan el
  margen 2022 en sus bastiones — N.Santander, Sucre, llanos — y al no haber
  "Rodolfo" en 2026 parece giro a la izquierda). Por eso el chart usa la pista
  Petro→Cepeda (candidato Pacto, comparable año a año): **Cepeda creció en 27/33
  deptos, cayó en Bogotá −5,4 y Atlántico −2,7; nacional plano +0,7**.
  Códigos RNEC verificados contra depname (27=Santander, 25=N.Santander — el
  dict viejo estaba descuadrado, corregido).
- `fit_ei_geo.py` — EI por ciudad y depto. A N moderado la EI de 6 candidatos
  se **acorrala en el borde** (Cepeda 0% en 61+) por **confusión ecológica
  real** (en grandes ciudades edad↔ingreso van juntos; validado: con Petro
  2022 OBSERVADO pasa idéntico — 0% en Bog/Med/Cali/Cart). Fixes: (1) **3
  bandas** (18-35/36-60/61+); (2) **cara a cara Cepeda-vs-Abelardo** (EI
  binaria, suma 100); (3) **ciudades ESTRATIFICADAS por localidad/comuna**
  (Medellín agrupa 2 zonas=1 comuna; shrink 0.03 al prior nacional por
  estrato vía `fit_qp_reg`) → 61+ del duelo: Bogotá 9 · Cali 14 · B/quilla 23
  · Cartagena 13 · B/manga 6 · Medellín <5 (genuinamente al piso).
  Consistencia implícito/observado ≤1.3pp. Salidas `ei-ciudades.csv` +
  `ei-deptos.csv`. Slide 07 muestra `<5`/`>95` bajo ese umbral.
  **Deptos pequeños** (Guainía·Vaupés·Vichada·Amazonas·San Andrés, <20 puestos
  en muestra): muestra ampliada (`load_year(min_votes=50, seeds=+mun)`) +
  **prior recentrado** al resultado global del depto (swing uniforme sobre el
  patrón etario nacional; NO heredan prior regional ajeno) + shrink 0.10 →
  `robust=2` en ei-deptos.csv. Vaupés es el mejor registro de Cepeda en 61+
  (45% del duelo) y aun así pierde la franja → "Abelardo gana 61+ en TODOS"
  se sostiene en 33/33.
- `report_carrusel.py` — **9 slides Twitter-first**: apaisadas 1200×900 (4:3)
  salvo la 02 (flechas, vertical 1080×1350). Identidad de carruseles previos:
  **títulos Arima 700** (TTFs estáticas en `tools/edad-1v-2026/fonts/`, bajadas
  de Google Fonts con UA viejo), kicker Helvetica bold **oxblood #8a1e16**,
  paper #f1eee4 / ink #1a1510 (paleta de carousel-conflicto.html). Slides:
  portada · **02 flechas = margen cara-a-cara** (Pacto − mejor derecha, 0 al
  centro, zonas "va adelante la izq/der" → así Bogotá lee "ganó pero
  retrocedió", orden alfabético) · mapa shift (texto izq + mapa der, sin
  solapes) · perfil nacional (etiquetas directas con dodge, sin leyenda) ·
  herencia (2 paneles lado a lado) · electorado · **ciudades WaPo** (caja 100%
  con números adentro, fila Nacional saturada, ganador con borde, números <13%
  por fuera) · 2 mapas jóvenes-vs-mayores · cierre 2×2. Geo de
  `output_pacto_1v_2026/geo/DEPARTAMENTOS2.json` (match por `name`).
  `python3 report_carrusel.py all` (Twitter 4:3) · `... all ig` (**Instagram
  cuadrado 1080×1080** → `carrusel-ig/`, layouts ajustados por flag `IG`).
  blocs-depto.csv trae h2h22/h2h26/h2h_shift
  (margen vs mejor derecha: izq adelante 19→18 deptos, margen cerrado en 20/33,
  Bogotá +24,9→+4,0; flips Quindío/Risaralda→der, Vichada→izq).
- Hilo de 13 trinos + caption IG en `rrss/twitter/hilo-edad-1v.md`. Colores
  🔴 Cepeda/izq · 🔵 Abelardo/der. **Hallazgo central:** choque de generaciones
  — Cepeda ~60% en 18-25 / ~7% en 61+; Abelardo 23%→79%. Se hereda de 2022
  (Cepeda=perfil de Petro, Abelardo=perfil de Fico). Pasa en las 6 ciudades.
  Entre jóvenes Cepeda gana el país menos Antioquia+Llanos; entre mayores
  Abelardo gana TODOS los deptos.
- **Noticia + página de análisis (jun-10):** `edades-1v.html` (tema claro
  paper #f1eee4 cohesivo con el carrusel — NO el dark de leyseca/trasvase;
  títulos Arima, kicker ox, hero-stats, 7 figuras, metodología con límites,
  related links). Imágenes del carrusel copiadas a `analisis-edades/*.png`
  (patrón carpeta-por-análisis tipo `analisis-leyseca/`). Card NOTICIA 14 en
  `noticias.html` → link a edades-1v.html. JS inline validado con
  `new Function`; verificado en preview (14 articles, 7 imgs OK).

## Data local — históricos pre-2026 (GCS)
Histórico electoral desde 2010 (Registraduría, formato GCS unificado). **Pesados, no se
despliegan al navegador**: se procesan y se suben a S3 como JSON agregados.

```
/Users/ricardoruiz/ricardoruiz.co/Bases de datos/FINAL SUBIDA GCS/
  GCS_2010PRES1V.csv   GCS_2014PRES1V.csv   GCS_2018PRES1V.csv   GCS_2022PRES1V.csv
  GCS_2010PRES2V.csv   GCS_2014PRES2V.csv   GCS_2018PRES2V.csv   GCS_2022PRES2V.csv
  GCS_2014CON.csv      GCS_2018CON.csv      GCS_2022CON.csv       (Congreso)
  GCS_2022CONSU.csv    GCS_2025CONSU.csv    GCS_2025CONSU_CAM/SEN.csv
  GCS_201XTER.csv / GCS_20XXCLMJ.csv / GCS_20XXJAL.csv / GCS_2016PLEB.csv
```

Columnas (mismas en todos los años, orden puede variar ligeramente en 2010/2025):
`FUENTE; FEC_ELEC; COD_COR; DES_COR; COD_CIR; DES_CIR; COD_DDE; COD_MME; COD_ZZ;
 COD_PP; DES_MS; COD_PAR; DES_PAR; COD_CAN; DES_CAN; NUM_VOT`
- `COD_DDE`/`COD_MME`/`COD_ZZ`/`COD_PP` = códigos Registraduría (depto/mun/zona/puesto)
- `DES_MS` = mesa; `COD_CAN`/`DES_CAN` = candidato; `NUM_VOT` = votos
- `COD_CAN` especiales: 996=Blanco, 997=Nulos, 998/999=No marcados

## Data local — 2026 agregada (antes de subir a S3)
```
/Users/ricardoruiz/ricardoruiz.co/Bases de datos/
  DEPTOS_DECLARADOS/                    → raw 2026 declarados por depto
  output_agregados/consultas/
    resumen.json                        → nacional: 3 consultas y sus candidatos
    deps.json                           → array compacto de deptos
    dep-{cod}.json                      → tree depto → consulta → cands → municipios[]
  output_declarados/CONSULTAS/NACIONAL/candidatos/   → por candidato
```
Las 3 consultas presidenciales 2026 (claves):
- `gran`       → La Gran Consulta por Colombia (derecha, ganó **Paloma Valencia**, 3.2M)
- `frente`     → Frente por la Vida (centro-izq, ganó **Roy Barreras**, 259K)
- `soluciones` → Consulta de Soluciones (centro, ganó **Claudia López**, 573K)

Consulta Pacto Histórico 2025: ganó **Iván Cepeda** (consulta única, `GCS_2025CONSU.csv`).
Todos los JSON tienen `por_circunscripcion: { NACIONAL: {...}, INDIGENAS: {...} }`.

## Preconteo 1V 2026 por mesa — `PRECONTEO_REGIS_*.csv`

Archivos crudos del preconteo de la Registraduría (noche del 31-may-2026), a
nivel de **mesa**. Viven en `Bases de datos/nuevos archivos 1v 2026/`. Se
usarán bastante mientras llega el escrutinio definitivo. **Tienen dos trampas
graves: nombres de columna barajados y un swap de header entre snapshots.**

### Cuál usar
- **`PRECONTEO_REGIS_1780270247.csv`** → **el bueno** (snapshot casi final,
  121.863 mesas, hasta 23:30). Sus totales cuadran con el oficial.
- `PRECONTEO_REGIS_1780265633.csv` → snapshot parcial anterior (97.339 mesas,
  hasta 22:12). **NO usar** salvo como histórico de la noche.
- ⚠️ **El orden de columnas difiere entre los dos**: en 5633 el header es
  `...,raul,abelardo,...` y en 0247 es `...,abelardo,raul,...` (las etiquetas
  `abelardo`↔`raul` están intercambiadas entre archivos). No se puede reusar el
  mismo mapeo para ambos. El mapeo de abajo es **solo para 0247**.

### Columnas barajadas → candidato real (verificado por match exacto de totales)
Las etiquetas del header NO corresponden al candidato. Mapeo para **0247**:
```python
NAME_0247 = {
  'ivan':'Iván Cepeda', 'abelardo':'Abelardo De La Espriella',
  'gustavo':'Paloma Valencia', 'paloma':'Sergio Fajardo',
  'claudia':'Santiago Botero', 'raul':'Mauricio Lizcano',
  'oscar':'Miguel Uribe', 'miguel':'Sondra Macollins',
  'sondra':'Roy Barreras', 'sergio':'Gilberto Murillo',
  'roy':'Carlos Caicedo', 'carlos':'Gustavo Matamoros',
  'luis':'Claudia López',   # ⚠️ SIEMPRE 0 en el preconteo por mesa
}
# Solo la columna 'abelardo' coincide con su dato real; las otras 12 están barajadas.
# Totales de control (0247): Cepeda 9.680.095 · Abelardo 10.346.010 ·
# Paloma 1.637.665 · Fajardo 1.007.627 · Botero 206.024 · Lizcano 53.828.
```

### Claudia López — su columna llega en 0 PERO es recuperable EXACTA por mesa
Su columna (`luis`) llega en **0 en las 121.863 mesas**. **PERO sus votos NO se
perdieron: están escondidos en `total_votos_urna`** (el total de cada urna sí los
contaba). Entonces `Claudia_mesa = total_votos_urna − (suma de las otras 12 columnas
+ blanco + nulos + no_marcados)`. El residual nacional da **225.287 EXACTO, sin un
solo negativo** = su total oficial. **Es dato real por mesa, no estimación.**
- Ya generado: `tools/cliente-mesa/build.py` → `PRECONTEO_1V_2026_MESA_con_Claudia.csv`
  (idéntico pero con Claudia llena) + `Resultados_1V_2026_por_mesa.xlsx` (Excel bonito
  con nombres). Ver sección "Entregable Pacto Histórico → Entregable aparte".
- (Histórico: antes creíamos que Claudia "solo existía a municipio" en `Base nombres
  corregidos primera vuelta 2026.csv`; eso quedó superado por el truco del residual.)

### Copia con nombres corregidos (ya generada)
`Bases de datos/nuevos archivos 1v 2026/PRECONTEO_1V_2026_MESA_nombres_corregidos.csv`
— copia de 0247 con los 13 nombres reales en el header, mismo formato (códigos
quoted con ceros a la izquierda, BOM utf-8 para Excel). Claudia sigue en 0.

### `Base nombres corregidos primera vuelta 2026.csv`
Agregación **a municipio** (cols `Candidato, cod_departamento, cod_municipio,
Llave mun, Suma de Votos`), ya con nombres propios. Misma cifra por candidato
que las columnas de 0247 **+ Claudia López 225.287** traída de otra fuente.
Total 23.657.546 (incluye blanco 406.805). Es la fuente de Claudia a municipio
(la usa `build_excel2.py` del análisis Pacto).

### Cobertura vs censo electoral 2026 (al corte 0247)
Censo: **41.287.084 potencial · 13.746 puestos · 125.259 mesas**
(`censos-puesto-2026.json` campo `nacional`+`porPuesto`; mesas en
`COMUNAS_DATA.csv`, delimitado por `;`).
- Potencial cubierto: **99,9%** (faltan 59.821).
- Puestos con reporte: 13.707 / 13.746 → **39 puestos sin abrir** (0,3%).
- Mesas: 121.863 reportadas → **~3.396 mesas pendientes** (2,7%, bajo potencial).
- Participación nacional: **58,0%** (23.950.441 votantes).
- Blanco 406.805 · nulos 245.324 · no marcados 47.571.
- El preconteo trae **~698 puestos de más** que no están en el censo doméstico:
  son **exterior/consulados + cárceles + puesto censo** (14.405 puestos en el
  preconteo vs 13.746 del censo de COMUNAS_DATA, que es solo territorio nacional).

### Esquema del CSV (23 columnas)
`cod_departamento, cod_municipio, zona, puesto, num_mesa,` + 13 candidatos +
`votos_blanco, votos_nulos, votos_no_marcados, total_votos_urna,
fecha_actualizacion`. Códigos quoted (preservan ceros), votos sin comillas.
Clave de mesa = `(cod_departamento, cod_municipio, zona, puesto, num_mesa)`;
clave de puesto para cruzar con censo = `f"{dep}-{mun}-{zona}-{puesto}"`
(coincide con las keys de `censos-puesto-2026.json`).

> Distinto del `COL2CAND` de `tools/pacto-1v-2026/build_base_2026.py`: ese mapea
> a slugs cortos (`cepeda`, `paloma`…) para el pipeline; el de aquí usa nombres
> completos. Ambos describen el MISMO barajado de 0247.

### Mapa Bogotá por localidad — `presidencial-prec-2026.html`

El preconteo presidencial (`presidencial-prec-2026.html`) es un tracker en
vivo del feed de la Registraduría (worker `registraduria-proxy`): mapa nacional
→ click depto → municipios (vía `mapagan`). **Bogotá es un solo municipio
(16-001)**, así que al abrir el depto NO hay municipios que mostrar. Para eso se
agregó un mapa por **localidad** (20, no UPL):

- En Bogotá la columna `zona` del preconteo == **localidad** (01..20) y coincide
  1:1 con `LocCodigo` de `BOG-LOCALIDADX.json`. 90/98 (puesto-censo Corferias +
  cárceles) NO son localidades → van a un bucket `especiales`, fuera del mapa.
- El feed en vivo **no desagrega por localidad** (`/presidente/16001` trae
  `mapagan` vacío), así que el coloreado sale de un **JSON estático del
  preconteo final** (no live): `tools/build-bog-localidades-prec/build.py` lee
  `PRECONTEO_1V_2026_MESA_nombres_corregidos.csv` y emite
  `Bases de datos/output_prec_1v/bogota-localidades.json` (~9 KB). Cada
  localidad: votos por slug de candidato (`cepeda`, `espriella`, `valencia`…
  mismos keys que `candColor()`), `base` (válidos+blanco), `winner`,
  `winner_pct`, mesas.
- S3 (público, mismo prefijo del resto de la página):
  `congreso-2026/output/prec-1v/bogota-localidades.json`. Regenerar:
  ```bash
  python3 tools/build-bog-localidades-prec/build.py
  aws s3 cp "Bases de datos/output_prec_1v/bogota-localidades.json" \
    "s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/prec-1v/bogota-localidades.json" \
    --content-type "application/json" --cache-control "public, max-age=300"
  ```
- Frontend: `renderMunMap()` intercepta `STATE.dep==='16'` → `renderBogLocMap()`.
  Reusa los 2 modos de pintado (líder / candidato `mapCand` por codpar→slug vía
  `_candSlugFor`). Geo rotado 90° izq (`_rotBogGeo`, convención Bogotá del
  proyecto). El swing vs Petro 22 NO está por localidad (hint lo aclara).
  `_clearBogLoc()` limpia la capa al volver a nacional o cambiar de depto.
  Re-pinta in-place (sin re-zoom) en el refresh de 90s y al cambiar de modo.
- Resultado (ganador por localidad, snapshot final): **Cepeda** gana las 10 del
  sur/centro (Usme, Bosa, Ciudad Bolívar, San Cristóbal, Rafael Uribe, Santa Fe,
  Tunjuelito, Kennedy, Candelaria, Sumapaz); **Abelardo** las 10 del norte/occ
  (Usaquén, Chapinero, Suba, Engativá, Fontibón, Teusaquillo, Barrios Unidos,
  Puente Aranda, Antonio Nariño, Los Mártires). Ciudad: Cepeda 42.7%.

## Segunda vuelta en vivo — `segunda-vuelta-prec-2026.html` (LISTO · 21 jun 2026)

Tracker del balotaje **Cepeda vs Abelardo** centrado en **cuándo el ganador es
irreversible**, ponderando *dónde* falta voto (no el conteo bruto). Reemplazó el
placeholder `locked` "Resultados 2V" del cajón Segunda Vuelta en `electoral.html`.

### Feed v2 (portal nuevo de la Registraduría) — CLAVE
La 1V vivía en `…/json/ACT/PR/{amb}.json`. La **2V vive bajo el portal v2**:
`https://resultados.registraduria.gov.co/v2/json/ACT/PR/{amb}.json`. Misma forma
de JSON (totales.act · camaras[0].partotabla · mapagan) PERO **codpars distintos:
Cepeda = `2`, Abelardo = `3`** (en 1V eran 7 y 10). `tope:"2"`. Sin CORS → worker.
- Worker `registraduria-proxy` ahora tiene ruta **`/presidente2v`** → base v2
  (`BASE_BY_ROUTE` en `tools/registraduria-proxy/worker.js`). `/presidente` sigue
  sirviendo la 1V final. Deploy: `cd tools/registraduria-proxy && npx wrangler deploy`.
- Descubrimiento del endpoint: el bundle SPA `/v2/assets/index-*.js` (build
  "PROD 2a VUELTA") usa `path:"/json/ACT/:electionSiglas/:scopeCode"` con prefijo `v2`.

### Modelo geográfico de irreversibilidad (el diferencial)
**Una sola llamada nacional** (`/presidente2v`) trae todo: el `mapagan` del JSON
nacional da, por depto, `mesesc`, `votcan` y el ganador → con 2 candidatos se
reconstruye cep_d y abe_d (perdedor = votcan − ganador). Por depto:
- `f_d = mesesc_d / metota_d` (mesas escrutadas).
- Voto 2-cand que falta `R_d = max(0, Vtot_d − votcan_d)`, con `Vtot_d` por
  extrapolación de mesas (`votcan_d/f_d`) anclada al `censo_d × participación × validFrac`
  cuando `f_d~0`. **Participación = ancla 1V (0.58) migrando al dato en vivo** (las
  primeras mesas rurales van menos llenas → extrapolar crudo subestima el faltante).
- Inclinación de lo que falta `q_d` (share Cepeda) = mezcla del 2V en vivo del depto
  y su **huella 1V por trasvase** (prior), pesada por `f_d`.
- Proyección final = Σ(contado + R_d·q_d). **Robusta desde el boletín 1**: en el demo
  marca Abelardo 47%Cep estable mientras el conteo bruto va Cepeda +58pp→−5pp.
- **Cota dura** (nunca en falso): ventaja > `inscritos de mesas sin escrutar`
  (`(metota−mesesc)·censo/metota`, techo absoluto). **Cota geográfica**: σ* = 50% +
  ventaja/(2·falta) vs expectativa `t̄` del de atrás → "le faltan X pp que superar
  en todo el país a la vez". **Probabilística**: Φ((p̂−0.5)/(σ·√(falta/total))).

### Anclas estáticas (embebidas inline en el HTML)
`tools/segunda-vuelta-prec/build_anclas.py` → `anclas-2v.json`: por depto `metota`
(mesas 2V), `censo`, `cep1v`/`abe1v` y `prior` (share Cepeda 2V esperado por trasvase
de bloques 1V: cep_bloc = Cepeda + 0.55·Fajardo + 0.65·Claudia + 0.85·{Roy,Caicedo,
Murillo}; abe_bloc = Abelardo + 0.85·Paloma + 0.78·{M.Uribe,Matamoros,Botero,Macollins}
+ 0.55·Lizcano). prior_nac = 0.4651 (Abelardo favorito, consistente con 1V 10.36M vs
9.69M). Para regenerar: `python3 tools/segunda-vuelta-prec/build_anclas.py` (66 fetches
a old+v2; metota/censo del v2). Bastiones prior: Chocó .79 · Vaupés .80 · Cauca .73 ·
Nariño .73 pro-Cepeda; N.Santander .21 · Casanare .28 · Antioquia .32 pro-Abelardo.

### UI (chasis de `presidencial-prec-2026.html`)
Veredicto (proyección + tier Definido/Encaminado/Inclinado/En disputa) · barra cara
a cara del conteo · KPIs · "la cuenta de la remontada" (2 cotas + prob) · mapa
("voto que falta": color=inclinación, intensidad=cuánto falta · toggle "líder ahora"
· click depto→municipios) · **tabla "Dónde está el voto que falta y a quién favorece"**
(por depto: **va ganando = margen REAL del depto** [resuelve confusión: "neto pendiente"
es solo del voto sin escrutar, ≠ resultado del depto], %escr, voto que falta, inclinación
+ neto pendiente "de lo que falta", ordenable) · evolución del margen conteo vs proyectado
por boletín · **gráfico de la diferencia (Abelardo−Cepeda) en votos por boletín** (sube/baja
= se amplía/recorta, con stat creció↑/se redujo↓). Auto-refresh 60s.
`window.STATE`/`computeModel`/`ANCLAS` expuestos para debug. (Los controles de
operador — recalcular/borrar/demo — se quitaron de la UI; `runDemo`/`resetBoletines`
quedan latentes en el código.)
- **Señal de sorpresa vs huella 1V** (`surpriseOf`/`surpriseTag`): en la tabla, cada
  depto compara su voto 2V EN VIVO (`sLive`) con lo esperado por el trasvase 1V (`prior`).
  `flip` = se inclina al lado CONTRARIO (badge "⇄ vira a X" + fila resaltada + nombre
  en el subtítulo, garantizado visible aunque sea depto chico); `move` = mismo lado
  pero ≥8 pp de corrimiento (▲/▼). Gate de fiabilidad: f_d≥0.10 y votcan≥1500.

## Análisis post-2V 2026 por mesa/barrio — `tools/segunda-vuelta-prec/` + `Bases de datos/output_2v/`

Pipeline completo de análisis del **resultado** de la 2ª vuelta (no el tracker en
vivo de arriba, sino el estudio posterior). Construido jun-2026. La pieza reusable
para CUALQUIER comparativo elección-a-elección es el **master por puesto**.

### Datos de entrada (cómo tenemos la 2V)
- **`Bases de datos/output_2v/detalle_nacional_presidencia_mesas.xlsx`** — preconteo
  2V **por mesa** (122.020 mesas × 25 cols). Es el equivalente 2V del
  `PRECONTEO_1V_2026_MESA`. ⚠️ Las columnas de votos llevan prefijo **`Pre_`** =
  **PRECONTEO**; las columnas de escrutinio (`recontadaComision`, `excluida`,
  `Causal`, `EstadoReclamacion`, `votosUrna`, `sufragantesE11SegunE14`…) llegan en
  **`N/A` al 100%** hasta que las comisiones escrutadoras avancen. O sea: HOY es
  preconteo con el molde del escrutinio vacío. Snapshot ~99,9% mesas (un pelín
  anterior al feed final). Solo trae Cepeda y Abelardo por mesa.
- **Feed en vivo** `/presidente2v` (worker `registraduria-proxy`) para el 2V
  municipal: Cepeda `codpar 2`, Abelardo `codpar 3` (ver memoria del feed v2).
- **1V**: `Bases de datos/nuevos archivos 1v 2026/PRECONTEO_1V_2026_MESA_con_Claudia.csv`.
- **Georef**: `PUESTOS_GEOREF.csv` (puesto→barrio/lat/lon/comuna, clave de 9 díg) +
  `test-presidencial/divipola.json` (nombre→código, fallback).
- **Control nacional**: 2V Cepeda **12.708.712** / Abelardo **12.959.542** (margen
  **250.830 = 0,98 pp**, participación 63,6%). 1V cara a cara Cep 9.680.095 / Abe
  10.346.010 (Abe +665.915).

### La unidad reusable — `master_unificado_puesto.json`
**14.220 puestos**, cada uno con: 1V (13 candidatos + blanco + censo `pot` +
votantes `urna1`) · 2V (`cep2`/`abe2`/`urna2`) · georef (lat/lon/barrio/comuna/
ciudad) · techo Petro-2V 2022 + `recuperar`. **99,1% del voto nacional**. El puesto
es la unidad ESTABLE entre elecciones (las mesas se reasignan) → es la base ideal
para cruzar cualquier par de elecciones. Para añadir otra elección al comparativo,
agregar sus votos por puesto por `pcode` (dep+mun+zona+puesto, 9 díg).

### Pipeline (orden de corrida)
```
fetch_2v_municipios.py   feed /presidente2v → dos_vuelta_municipios.json (2V municipal)
analisis_2v_vs_1v.py     1V(csv) vs 2V(municipal) → municipios_2v_vs_1v.csv (margen/swing/flips, 1.189 munis)
build_master_2v.py       une 1V(13 cands)+2V por puesto → master_unificado_puesto.json + agg_municipio.json
build_trasvases.py       inferencia ecológica por BLOQUE (lsq_linear+bootstrap) → trasvases.json
build_analisis_2v.py     3 estrategias + participación + atípicos → analisis_2v.json
build_barrios_2v.py      PIP puesto→barrio · mapas 1V vs 2V (14 ciudades) → barrios_2v.json + mapas/*_{v1,v2}.png
build_comunas_2v.py      agrega por comuna/localidad → comunas_2v.json
build_graficos_2v.py     5 gráficos nacionales (limpios) → graficos/
build_pdf_60.py          documento extenso (56 pág, TOC, encriptado no-copy, watermark) → Analisis_2V_2026_Extendido.pdf
build_pdf.py             documento corto (3 pág) → Analisis_2V_2026_donde_gano_Abelardo.pdf
build_linkedin_imgs.py   3 gráficos con marca Ricardo.Ruiz, SIN watermark → rrss/linkedin/
```

### Gotchas metodológicos (CRÍTICOS para reusar)
- **El XLSX 2V usa NOMBRES de depto/mun** (no códigos). `build_master_2v` mapea
  nombre→código con `normm()` (quita tildes + **paréntesis + puntos**: "TIQUISIO
  (PTO. RICO)" == GEOREF "TIQUISIO PTO. RICO") + fallback `divipola.json`. Bogotá:
  `cod5_of` lo fuerza a `16001`.
- **Claudia López llega en 0 por mesa** en el preconteo → traerla a municipio del
  `Base nombres corregidos primera vuelta 2026.csv` (igual que en pacto-1v-2026).
- **Trasvases por BLOQUE, no por candidato** (Paloma y minoritarios de derecha votan
  los mismos territorios → colinealidad ecológica). Se estima por bloque (Derecha ·
  Centro · Izq menor · Nuevos votantes) y se atribuye la tasa del bloque a cada
  candidato. Bootstrap 400 munis. R²≈0,99.
- **Barrios**: encuadre al **casco urbano = `gp[direct].total_bounds`** (NO a los
  puestos, que traen outliers rurales que estiran el marco y dejan la ciudad
  diminuta). Relleno de vecino más cercano es SOLO visual (no suma a totales; los
  totales salen de los puestos directos). 14 ciudades con polígono bueno; Pasto,
  Tumaco, Palmira, Sincelejo se descartaron por mapa pobre.
- **Watermark/seguridad**: mapas llevan "DOCUMENTO / CONFIDENCIAL / RICARDORUIZ.CO"
  diagonal 45° (anti-robo de la pieza suelta). PDF extenso encriptado con `canCopy=0`
  (no se puede seleccionar texto) + watermark de página. Las imágenes de LinkedIn van
  **SIN** watermark (son públicas, solo logo + crédito).

### Hallazgos clave (para no recalcular)
- **Antioquia decide**: +1.052.153 de margen neto = **419% del margen nacional**.
  Sin Antioquia, Cepeda sería presidente por ~800.000.
- **Trasvases reales**: Derecha (84% Paloma) → **81% Abelardo** · Centro
  (Fajardo+Claudia) → **81% Cepeda** · Izq menor → 100% Cepeda · Nuevos votantes →
  **81% Cepeda** (promedio nacional; en bastiones de Abelardo van a él).
- **Las 3 estrategias del Pacto cuajaron** (Centro 143% del target · Recuperación
  100% del techo · Abstención +667K netos) y **aun así perdió**: la participación
  subió pareja (60,3→66,4%, +2,33M, en 1.121/1.122 munis), sin ventaja diferencial.
- Veredicto: la elección estaba estructuralmente decidida desde 1V; la geografía
  pesó más que la campaña.

### Entregables
- `Analisis_2V_2026_Extendido.pdf` (56 pág · **CONFIDENCIAL**, encriptado) ·
  `Analisis_2V_2026_donde_gano_Abelardo.pdf` (3 pág).
- `rrss/linkedin/articulo-abelardo-un-punto.md` + 3 imágenes (`1-tres-estrategias`,
  `2-antioquia-decide`, `3-trasvases`) — artículo "¿Por qué Abelardo ganó, y solo
  con un punto?".

### Las 4 grandes ciudades 2V barrio por barrio (`ciudades-2v-barrios.html`) — jun-2026

Deep-dive de **Bogotá · Medellín · Barranquilla · Cali** en 2V por barrio (distinto
del análisis nacional de arriba). Tesis: Cepeda ganó 3 de las 4 grandes (Bogotá
53,7% · Cali 60,6% · B/quilla 54,8%) y en las 3 amplió; Abelardo solo Medellín
(66,3%, achicándose de +39,1 a +32,7). La fractura interna es de **estrato**: barrios
ricos (La Cabrera, El Poblado, Riomar, Pance) → Abelardo; periferia popular → Cepeda.
B/quilla dio el mayor giro (empate +1,6 → Cepeda +9,6). Pero la presidencia se ganó
afuera (Antioquia = 2× el margen nacional).
- **Datos:** `tools/segunda-vuelta-prec/build_ciudades_barrios.py` lee
  `master_unificado_puesto.json`, PIP puesto→barrio (4 ciudades) + vecino más cercano,
  emite `Bases de datos/output_2v/ciudades-barrios-2v.json` (dict por ciudad, `b`
  keyed por código estable [Medellín `CODIGO`] o índice de feature [resto, match por
  orden — verificado S3==local]). Margen `(abe−cep)/(abe+cep)`, negativo=Cepeda.
- **HTML:** standalone dark, identidad 2V (Cepeda rojo `#c0392b`/Abelardo azul
  `#1f47cc`), Leaflet. Tabs 4 ciudades · toggle 1V/2V · modo Ganador/Cambio(swing) ·
  panel KPIs + tops + leyenda dinámica · Bogotá rotada 90°. Fetch data JSON + GeoJSON
  de S3 (URLs en `meta.url`). Bug clave resuelto: NO hacer `innerHTML=''` al cambiar
  de ciudad (destruye el contenedor Leaflet) — init del mapa una sola vez.
- **Imágenes** (`tools/segunda-vuelta-prec/build_ciudades_imgs.py` → 14 PNG 1080×1080
  en `rrss/twitter/ciudades-2v-png/`): portada + por ciudad {mapa, a1 "dos ciudades en
  una"=leaderboard barrios, a2 "cambio 1V→2V"=barras+flecha} + cierre. Identidad paper
  `#f1eee4`/Arima/Inter, **SIN watermark** (públicas), logo+crédito. Gotcha respetado:
  Inter no trae emoji ni `→` (usar bullets `Rectangle`, flechas `annotate`, coma decimal).
- **S3 subido** (público): `congreso-2026/output/prec-2v/ciudades-barrios-2v.json` +
  `…/mapas-2026/Ciudades-COM-LOC/{CALI,BARRANQUILLA}-BARRIOS.json` (Bogotá/Medellín ya
  estaban). Bumpear `?v=YYYYMMDD` del `DATA_URL` en el HTML al regenerar.
- **Redes:** hilo X `rrss/twitter/hilo-ciudades-2v.md` (14 trinos: portada + mapa+2
  análisis por ciudad + cierre) · carrusel IG `rrss/instagram/carrusel-ciudades-2v/`
  (10: portada+mapa+a1 por ciudad+cierre) · LinkedIn `rrss/linkedin/articulo-ciudades-2v.md`.
  Card NOTICIA 16 en `noticias.html`.

## Mapas por barrio 1V 2026 — `bogota-1v-barrios.html` + `medellin-1v-barrios.html`

Notas/mapas interactivos (enlazados desde `noticias.html`) que llevan el
preconteo 1V por mesa al barrio. Mismo motor: cada puesto se asigna por
**PIP** (lat/lon de `PUESTOS_GEOREF.csv`) al polígono que lo contiene; los
barrios sin puesto propio se rellenan con la tendencia del **vecino más
cercano por centroide** (`FILL`, translúcido). El titular cuenta **solo
barrios con dato directo** (no los rellenados).

- **Bogotá** (`bogota-1v-barrios.html`): 1.001 barrios catastrales (IDECA,
  `BOG-BARRIOS-CATASTRALES`), geo rotada 90° izq. Cepeda gana 435 barrios /
  Abelardo 223 (directos). Datos inline `BARRIOS`+`FILL` generados por
  `tools/trasvase-paloma/build_barrio_pip.py` (PIP base) y
  **`tools/trasvase-paloma/build_barrio_override.py`** (override "llenar
  huérfanos por nombre", ver abajo). El override reinyecta `BARRIOS`/`FILL`
  + el titular in-place; reproduce y **asserta** el baseline (625 · Cepeda
  412 / Abelardo 213) antes de tocar la página.
- **Medellín** (`medellin-1v-barrios.html`): 332 barrios oficiales DAP
  (`MEDELLIN_BARRIOS_OFICIAL.json`, dep 01 mun 001, **sin rotar**). Abelardo
  arrasa (54,5% ciudad); de 154 barrios directos gana 137, Cepeda 17 (foco
  rojo en centro/Popular/Manrique/Santo Domingo). Build:
  **`tools/build-mde-barrios-prec/build.py`** (autocontenido, emite el HTML).
  GEO_URL = `bases+de+datos/MEDELLIN_BARRIOS_OFICIAL.json` (S3 público).

**Override "llenar huérfanos por nombre"** (decisión del usuario, jun-2026):
si un puesto se *llama* como un barrio catastral (p.ej. "QUINTA PAREDES A/B")
pero por PIP cae en un barrio vecino (su georef y su columna `BARRIO` lo
confirman — Quinta Paredes A→Ciudad Universitaria, B→Ortezal), y el barrio
homónimo está **huérfano** (0 puestos), se le asigna el puesto por nombre —
**solo si moverlo no deja huérfana a la fuente** (conteo dinámico, no
estático: dos puestos que comparten fuente no la vacían). 33 movimientos en
Bogotá (incluye Quinta Paredes ← QP B). No es blanket name-match: 112 puestos
tienen nombre = barrio pero solo se mueven los ~33 que llenan huérfanos sin
robar dato. Mantiene el principio "PIP > nombre" salvo en los huecos.

**Descargas (ambas páginas):** gratis para usuarios **registrados**
(`plan!=='anonymous'`, antes era Premium-only). Ofrecen el preconteo 1V
nacional por mesa: `DESCARGAS/Resultados_1V_2026_por_mesa.xlsx` (nombres) +
`DESCARGAS/PRECONTEO_1V_2026_MESA_con_Claudia.csv` (códigos, Claudia
recuperada). Anónimo → `register.html`.

## Entregable Pacto Histórico — informe 1V 2026 (`tools/pacto-1v-2026/`)

Análisis para cliente del Pacto: **un solo Word con capítulos + resumen
ejecutivo + Excel de soporte**. **Estado actual: LISTO · Word de ~43 páginas
(8 capítulos + metodología, Inter incrustada · gráfico de brecha `g_brecha_2v` al
cierre del Cap 2 · Cap 8 = 3 campañas con mapa por barrio numerado de 9 ciudades) ·
Excel de soporte de 15 hojas + 3 Excel de estrategia.** Salidas en
`Bases de datos/output_pacto_1v_2026/` (gitignored).

Diagnóstico de 1V 2026 por bloque + **camino a la 2ª vuelta**: Petro 2V-1V ·
Cepeda vs Petro (con mapas) · Centro/Oviedo (incl. trasvase de Oviedo) · Derecha ·
Bogotá por estrato · mapa de la 2V (techo) · abstención · **cuántos votos
necesita Cepeda para ganar (modelo de trasvase + dónde están los ~1,9M, hasta
comuna/barrio/puesto)**.

### Pipeline (orden de corrida)
```
build_base_2026.py   preconteo 0247 → master_2026_puesto.json (14.220 puestos, georef)
build_base_2022.py   GCS 2022 1V+2V → master_2022_puesto.json
engine.py / engine2.py  → blocks_all.json (depto + ciudad·comuna) + blocks_full.json
                        (municipio + ciudad·barrio + muni_abst) + dif_2022.json
                        (bogota_loc) + estrato_bogota.json (join puestos↔manzana SDP)
build_2v.py          modelo de 2ª vuelta → twov_model.json (nacional + trasvase)
                     + twov_territorial.json (recuperar por municipio + puesto)
build_voronoi_barrios.py → polígonos de barrio APROXIMADOS (Voronoi de puestos · convex-hull del
                     casco urbano si no hay geojson de comuna) para ciudades SIN capa pública: Cúcuta +
                     7 zonas fuertes de abstención (Buenaventura, Pasto, Santa Marta, Palmira, Tumaco,
                     Sincelejo, Soledad). Correr ANTES de build_maps.
build_maps.py        ~44 mapas m_*.png · incl. **28 por barrio**: 9 ciudades base × {centro, recuperación}
                     (Bogotá, Medellín, Cali, Barranquilla, Cartagena, Manizales, Pereira, Bucaramanga,
                     Cúcuta) + abstención en **11 zonas fuertes** (las 4 grandes + Buenaventura, Soledad,
                     Pasto, Santa Marta, Palmira, Tumaco, Sincelejo · Quibdó se omite: georef con 4
                     barrios). Helper genérico barrio_map() con métrica centro/rec/abst, relleno de vecino,
                     ETIQUETAS NUMÉRICAS (1..N) → barrio_labels.json (lo lee el Word).
build_charts.py      7 gráficos g_*.png (estrato, ciudades-techo, recuperación, oviedo-localidad,
                     oviedo-destino, trasvase-2V, **brecha-2V** [waterfall del Cap 2])
build_estrategias.py → twov_estrategias.json (incl. city9: totales municipio por ciudad) + 3 Excel de
                     estrategia (Centro · Recuperación · Abstención) · lee twov_model+territorial+master+CSV
build_excel2.py      → Soporte_Analisis_Pacto_1V_2026.xlsx (15 hojas) · lee twov_territorial
build_report.py      → Analisis_Nacional_Electoral_Pacto_1V_2026.docx (incrusta Inter) · lee
                     twov_model + twov_estrategias (Cap 8 = 3 campañas)
build_oviedo_docs.py bloque Oviedo (Excel + correlaciones · genera oviedo_*.json)
```
**Orden importa:** `build_2v` antes que `build_estrategias`/`build_excel2`/`build_report`;
`build_estrategias` antes que `build_report` (escribe `twov_estrategias.json` con `city9` que el
Cap 8 lee); `build_maps`+`build_charts` antes que `build_report` (incrusta PNG + `barrio_labels.json`
que los párrafos del Cap 8 leen para numerar barrios); `build_voronoi_barrios` antes que `build_maps`
(genera los geojson aproximados de Cúcuta). Verificación visual: `soffice --headless --convert-to pdf` + leer el PDF.
**Regenerar todo:**
```bash
cd /Users/ricardoruiz/ricardoruiz.co
python3 tools/pacto-1v-2026/build_2v.py
python3 tools/pacto-1v-2026/build_voronoi_barrios.py   # geojson aprox (Cúcuta) — solo si faltan en geo/
python3 tools/pacto-1v-2026/build_maps.py
python3 tools/pacto-1v-2026/build_charts.py
python3 tools/pacto-1v-2026/build_estrategias.py
python3 tools/pacto-1v-2026/build_excel2.py
python3 tools/pacto-1v-2026/build_report.py
cd "Bases de datos/output_pacto_1v_2026"
/Applications/LibreOffice.app/Contents/MacOS/soffice --headless --convert-to pdf --outdir . Analisis_Nacional_Electoral_Pacto_1V_2026.docx
```

### Tres campañas de 2V (`build_estrategias.py`) — Cap 8 + 3 Excel

El cliente pidió separar el "camino a la 2V" en **3 estrategias de campaña
distintas** porque la tabla única (que mezclaba "recuperar" y "centro
disponible") los enredaba. `build_estrategias.py` produce `twov_estrategias.json`
(que el Cap 8 del Word lee) + 3 Excel independientes, cada uno con hoja "Léeme"
que explica la métrica y cómo (no) se suma:

- **`Estrategia_1_Centro.xlsx`** · persuasión. Centro transferible =
  `0,55·Fajardo + 0,65·Claudia` (supuestos del modelo) = **~700.631** nacional.
  Hojas: por municipio (CSV nombres corregidos como columna vertebral, incluye
  municipios chicos + fila agregada "Exterior") · Bogotá localidad/barrio ·
  16 ciudades comuna/barrio. **Claudia solo existe a municipio en el preconteo**
  (su columna llegó en 0 por mesa); en las hojas submunicipales va como columna
  **"Claudia (est.)"** = total municipal repartido en proporción a Fajardo
  (reconcilia exacto por ciudad). Transferible submunicipal = 0,55·Fajardo +
  0,65·Claudia(est).
- **`Estrategia_2_Recuperacion.xlsx`** · el techo. `max(0, techo Petro-2V −
  Cepeda 1V)` = **~2.050.187**. Hojas: municipio · puesto · ciudades
  comuna/barrio. Es el "universo" de la izquierda demovilizada.
- **`Estrategia_3_Abstencion.xlsx`** · movilización NETA. `max(0, abstención ×
  (2·share_Petro2V − 1))` — solo positivo donde la izquierda gana la 2V (zonas
  fuertes). Σ nacional **~2,63M**; la columna "Suma el objetivo 1,9M" marca con
  ✓ los **73 municipios** que juntan el `gap` (1.915.513). Hojas: municipio ·
  Bogotá localidad · ciudades comuna · **ciudades barrio** (dedup por
  (ciudad,comuna,barrio); como el neto se recorta a 0, al bajar de nivel afloran
  bolsones fuertes en comunas mixtas → el total por barrio sale algo más alto que
  por comuna, no re-sumar contra el objetivo nacional). Censo/votantes desde
  `pot`/`total_votos_urna` por puesto del master 2026.

**Cómo (no) se suman** (clave del entregable, repetido en cada Léeme y en el Cap 8):
Centro (~0,7M) **se suma** a Movilización (~1,9M) = 2,65M (`need_over_1v`).
Recuperación y Abstención **NO se suman entre sí**: mismo universo, dos lentes
(una dimensiona el techo, la otra dice cómo recuperarlo vía participación).

Las 16 ciudades se resuelven por **código electoral** (no DANE): Bucaramanga
27-001, Manizales 09-001, Cúcuta 25-001, Soledad 03-052, Soacha 15-247, etc.
Reusa la fusión de barrios por `(ciudad, norm(comuna), norm(barrio))` con
`_bestname` (mismo fix que `build_excel2.py`, ver gotcha de tildes).

### Mapas por barrio + relleno de vecino (`barrio_map` en build_maps.py)

Helper genérico `barrio_map(city,dep,mun,geofile,namefield,fname,metric,rotate,...,citycode,frame,approx,vq)`:
agrega los puestos al polígono de barrio por `sjoin_nearest`, calcula la métrica y pinta.
- **3 métricas**: `'centro'` → `0,55·Fajardo + 0,65·Claudia(est ∝ Fajardo)` (Claudia desde
  `CLA_MUN`, ámbar `CM_CENTRO`); `'rec'` → `max(0,techo−cepeda)` (verde); `'abst'` → neto
  `max(0,(censo−votantes)·(2·share−1))` (cobre). centro usa TODOS los puestos; rec/abst filtran `has_sh`.
- **Etiquetas numéricas**: numera los top-N barrios con DATO DIRECTO (dedup por nombre — un barrio
  catastral puede venir en varios polígonos), pone círculos 1..N en el mapa, y vuelca el mapeo
  nº→barrio→valor a `LABELS` → `barrio_labels.json`. El Word (`bcity` en build_report) lo lee y
  **desarrolla los barrios numerados en el texto** (sin encimar nombres en el mapa). `total` = suma
  por nombre único (no por polígono, que multicontaría).
- **Relleno de vecino** (`_fill_neighbors`): barrios sin puesto propio heredan la tendencia del más
  cercano (no entran a `total` ni a la numeración). Gotcha: tras el fill no quedan NaN →
  `if len(gnan): gnan.plot(...)` (geopandas revienta en `set_aspect` con subset vacío).
- `frame='pts'` encuadra al casco urbano (Cartagena, que trae rural/islas). `rotate=True` solo Bogotá.
  `comuna_field`+`urban_set` filtran corregimientos (Medellín). `approx=True` añade nota de polígono aproximado (Cúcuta).
- **28 mapas vivos**: 9 ciudades base × {centro, rec} (loop `CITY_BARRIO`) + abstención en **11 zonas
  fuertes** (loop `CITY_BARRIO` para las 9 — abst se genera para todas — pero solo se EMBEBEN en el Word
  las de neto>0: Bogotá/Cali/Barranquilla/Cartagena; + loop `ABST_EXTRA` con las 7 Voronoi nuevas).
- **Las 5 ciudades débiles NO entran a abstención en el Word** (Medellín/Manizales/Pereira/Bucaramanga/
  Cúcuta): su muni-neto es 0 (share Petro-2V <50% → movilizar le suma a Abelardo). Bucaramanga y Cúcuta
  dan total 0 (mapa en blanco). Van con una nota en vez de mapa. También NO van en recuperación si
  muni-recuperar=0 (Bucaramanga).

**Geojson de barrio por ciudad (en `output_pacto_1v_2026/geo/`, bajados a mano — gitignored):**
- Bogotá `BOG-BARRIOS-CATASTRALES.json` (`nombre`, 1.001) · Medellín `MEDELLIN_BARRIOS_OFICIAL.json`
  (`NOMBRE`+`COMUNA`, 332) · Cali `CALI-BARRIOS.json` (`barrio`, 339, de datos.cali.gov.co ZIP shapefile
  EPSG:6249) · Manizales `MANIZALES-BARRIOS.json` (`BARRIOS`, 116) · Barranquilla `BARRANQUILLA-BARRIOS.json`
  (`NOMBRE`, 189) · Cartagena `CARTAGENA-BARRIOS.json` (`NOMBRE`, 213, `frame='pts'`) · Pereira
  `PEREIRA-BARRIOS.json` (`NOMBRE`, 486).
- **Bucaramanga `BUCARAMANGA-BARRIOS.json` (`barrio`, 219 REAL)**: portal propio
  `geodata.bucaramanga.gov.co/waportal/sharing/rest/content/items/<id>?f=json` → `url` apunta al host
  interno `vmarcgis01.bucaramanga.gov.co/waserver/rest/services/Hosted/Barrios/FeatureServer` (el proxy
  público da HTML; el host interno SÍ responde el query geojson).
- **Cúcuta `CUCUTA-BARRIOS.json` (`barrio`, 424 REAL)** + **Soledad `SOLEDAD-BARRIOS.json` (`barrio`, 239 REAL)**:
  de los **GeoServer de catastro vía IDEEP** (ver método abajo). Cúcuta `geoservicioside.cucuta.gov.co`
  capa `cucuta:barrios_poligono`; Soledad `geoservicios.catastrosoledad.gov.co` capa `soledad:barrios_v2`.
- **Buenaventura `BUENAVENTURA-BARRIOS.json` (`barrio`, 110 REAL)**: capa hosted de ArcGIS Online
  (`services2.arcgis.com/EsyoEkMlTcucSCqP/.../Buenaventura_barrios/FeatureServer`).
- **Quibdó `QUIBDO-BARRIOS.json` (`barrio`, 60 REAL)**: capa ArcGIS Online
  (`services4.arcgis.com/3OgCxmjOXo22H0MY/.../Barrios_Quibdo_1`, campo `N_BARRIO`). **Lección:** el
  "solo 4 barrios" era del CAMPO DE TEXTO del puesto; `barrio_map` asigna por UBICACIÓN (sjoin punto→polígono),
  así que los 43 puestos caen en 20 barrios distintos → mapa usable. No descartar una ciudad por el conteo
  del campo de texto.
- **Voronoi aprox que QUEDAN (pendientes de capa real):** Pasto, Santa Marta, Palmira, Tumaco, Sincelejo
  (`build_voronoi_barrios.py`, `approx=True` en ABST_EXTRA). Tumaco/Sincelejo se ven feos (revisar).

**Método IDEEP (catastro municipal · sirve para muchas ciudades con "catastro multipropósito"):**
El geovisor `https://<host_catastro>/ideep_geovisor/index.html?...&codigo_dane=<dane>` carga su GeoServer
desde un config en runtime, NO alcanzable por curl. Con la **extensión Claude in Chrome**: navegar al
geovisor → `read_network_requests` filtrando `geoserver` → de ahí salen el host del GeoServer
(`geoservicios...`/`geoservicioside...`), el workspace y el `authkey`. Luego, aunque WFS GetCapabilities dé
**403**, `GetFeature` sobre la capa autorizada SÍ responde:
`<host>/geoserver/<ws>/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=<ws>:barrios_poligono&outputFormat=application/json&srsName=EPSG:4326&count=2000&authkey=<key>`.
Para listar capas usar **WMS** GetCapabilities (sí pasa con el authkey) y buscar `<Name>barrios*</Name>`.
Usar `/usr/bin/curl` (no el de PATH) para bajar y el `python3` normal (con geopandas) para procesar.

**Cómo se consiguieron Manizales y Barranquilla (método ArcGIS, reusable para otras ciudades):**
1. `curl "https://www.arcgis.com/sharing/rest/search?q=barrios+<ciudad>&f=json&num=25"` → lista
   items; quedarse con los `Feature Service` cuyo título sea "Barrios de <ciudad>".
2. `curl "https://www.arcgis.com/sharing/rest/content/items/<itemId>?f=json"` → campo `url` = el
   FeatureServer (p.ej. `.../Barrios_de_Barranquilla/FeatureServer`).
3. `curl "<featureServerUrl>/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson"` → geojson directo.
4. `gpd.read_file(...).to_crs('EPSG:4326')[['<nombre>','geometry']].to_file(...,driver='GeoJSON')`.
   (datos.gov.co/SODA NO sirve: expone geometría null; el export shapefile da 500.)

### Motor de mapas (`build_maps.py`) — geopandas + matplotlib
- GeoJSON oficiales (los MISMOS de senado/cámara), cacheados en
  `output_pacto_1v_2026/geo/`. Se bajan de S3
  (`.../congreso-2026/output/mapas-2026/`): `DEPARTAMENTOS2.json` (33 deptos,
  prop `name`), `Departamentos-mps/{cod}.json` (municipios, props
  `dep_electoral`+`mun_elec` → clave `01001`), `Ciudades-COM-LOC/BOG-LOCALIDADX.json`
  y `BOG-UPL.json` (33 UPL, prop `CODIGO_UPL`). Bajar con `aws s3 cp` (el loop
  curl tuvo hipos; aws es robusto).
- Match depto: por nombre normalizado + alias `Distrito Capital de Bogotá→Bogotá`,
  `San Andrés y Providencia→San Andrés`. Vista nacional recortada al continente
  (`xlim -79.3..-66.8`, `ylim -4.4..13.7`); barra de color al costado IZQUIERDO
  (sobre el Pacífico, vacío) para no taparse con los llanos.
- **Bogotá se rota 90° a la izquierda (CCW)** — convención de cómo se ve la
  ciudad. Helper `rotate_gdf(g, 90)` (mismo giro que `rotateGeoJSON90Left` de
  cámara/senado: `x'=cx-(lat-cy), y'=cy+(lon-cx)`). Aplica al mapa de estrato
  (manzana, gpkg proyectado) y al de Cepeda por UPL.
- **Cepeda por UPL**: spatial-join `sjoin_nearest` de los 1.038 puestos
  georreferenciados contra `BOG-UPL.json`, agrega `cepeda/base` por UPL. Encuadre
  a los puestos (urbano) para que las UPL rurales del sur no aplasten el mapa.
- **Estrato Bogotá** (manzana): `manzana_estrato_bog.gpkg` (44.260 manzanas,
  SDP/IDECA). Colores estrato 1→6 (rojo→azul, espejo del voto Cepeda↓/Abelardo↑).

### Tipografía Inter incrustada en el Word
**El informe Word usa Inter (no Helvetica) e incrusta la fuente** para que el
cliente la vea idéntica en Windows/Office aunque no la tenga. El "saltarín" que
veíamos era Helvetica Neue ausente en el cliente → sustitución glifo por glifo
(tildes/ñ/guiones de otra fuente). Inter es la "Helvetica de hoy", gratis y de
uso comercial.
- TTF en `tools/pacto-1v-2026/fonts/Inter-{Regular,Bold,Italic}.ttf` (subset
  latín, ~230 glifos). Instaladas en `~/Library/Fonts/` para que LibreOffice y
  matplotlib las rendericen.
- `build_report.py`: fuente en estilo Normal + **docDefaults** (clave para que
  las celdas de tabla también hereden Inter). Tras `d.save()`, `embed_inter()`
  incrusta los 3 TTF con la **obfuscación OOXML estándar** (XOR de los primeros
  32 bytes con el GUID invertido) + `fontTable.xml` (`w:embedRegular/Bold/Italic`
  + `w:fontKey`) + `fontTable.xml.rels` + `Default Extension="odttf"` en
  Content-Types + `<w:embedTrueTypeFonts/>` en settings (va entre `zoom` y
  `proofState`). Verificación: de-obfuscar el `.odttf` y confirmar magic
  `00010000` (TTF válido) ⇒ Word lo leerá.
- `build_maps.py` y `build_charts.py` registran Inter en matplotlib
  (`font_manager.addfont` + `rcParams['font.family']='Inter'`) para que mapas y
  gráficos vayan en la misma fuente.

**⚠️ El subset latín de Inter NO trae flechas ni estrellas** (`→ ← ↔ ★ ✦`,
U+2190-2194 salvo ↑↓, U+2605). En texto del Word o de los gráficos producen
cajas (tofu). Usar `—` / `a` / `vs` / `–` en su lugar (ya aplicado: "2022 a
2026", "Oviedo–Paloma"). Si en el futuro se necesita el set completo, instanciar
Inter variable de Google Fonts a estáticas 400/700 con `fontTools.varLib.instancer`
y reembeber.

**⚠️⚠️ Inter es SOLO para el informe Word + sus mapas/gráficos. Las imágenes de
redes / Instagram (`rrss/instagram/carousel.html`, `rrss/twitter/*`) CONSERVAN
Helvetica + Arima y su formato propio** — se ven muy bien así y NO se tocan.
No portar Inter ni este pipeline a las piezas de redes.

### Bloque Oviedo (capítulo del Centro)
Refuta la hipótesis del cliente (Paloma-1V = voto de Oviedo). Cruce mesa a mesa:
del voto de Oviedo (1,26M, 2º Gran Consulta) **solo ~8% fue a Paloma**; ~67% a
Cepeda, ~20% a Fajardo, ~5% a Abelardo (87% izquierda+centro). Correlaciones por
puesto lo respaldan (Oviedo↔Fajardo +0,60, ↔Cepeda +0,32, ↔Abelardo −0,41,
↔Paloma −0,12; en Bogotá ↔Paloma −0,57). Claim con **cota dura de King** (techo
teórico ~64%) + nota honesta de lo que la inferencia ecológica no fija. Gráfico
`g_oviedo_destino.png`.

### Capítulos del informe (`build_report.py`)
Portada + índice + **resumen ejecutivo (8 hallazgos)** + 8 capítulos + nota
metodológica. **Cada capítulo arranca en página nueva** (`cap()` pone
`paragraph_format.page_break_before=True`; NO hay `add_page_break` manual salvo
el del cierre del resumen ejecutivo... ojo: se quitó, lo hace el `page_break_before`
del Cap 1). Helpers: `cap(num,txt)` (título + eyebrow), `h()` (subtítulo 12.5),
`body()` (10.5, **justificado**), `note()` (9, para metodología/salvedades),
`bullet()` (10.5 justificado), `tbl()` (header oxblood 8.5), `img(name,w)`
(centrado, espaciado apretado). `body()` parsea `**negrita**` (NO `*italic*` —
los asteriscos sueltos salen literales).
- **Cap 1** Petro 2V-1V · **Cap 2** Cepeda vs Petro (mapa ganador con Abelardo en
  **azul rey `#1f47cc`** para contrastar con el morado de Cepeda · swing municipal ·
  Cepeda municipal) · **Cap 3** Centro/Oviedo (bullets + g_oviedo_destino +
  g_oviedo_bogota_localidad) · **Cap 4** Derecha (m_derecha_dep) · **Cap 5** Bogotá
  estrato (m_bogota_estrato manzana + m_bogota_upl_cepeda + g_bogota_estrato) ·
  **Cap 6** mapa de la 2V/techo (m_recuperacion_dep) · **Cap 7** abstención
  (m_abstencion_mun) · **Cap 8** cuántos votos necesita Cepeda (g_trasvase_2v +
  tabla cuenta-de-cobro + m_bogota_recuperar + m_{cali,medellin,barranquilla}_recuperar).
- **Frases del cliente neutralizadas**: nada de "el cliente plantea/pregunta" en
  el texto final → "Se plantea la posibilidad de", "Conviene darle la vuelta a la
  pregunta", "La pregunta de fondo". (El cliente NO quiere verse citado.)

### Modelo de 2ª vuelta (`build_2v.py`)
Aritmética con **supuestos de trasvase EXPLÍCITOS** (movibles, en el dict `T`):
Paloma 85%→Abelardo, minoritarios derecha 78%→Abe, Fajardo 55% Cep / 30% Abe,
Claudia 65% / 20%, minoritarios izq 85%→Cep. Totales 1V hardcoded en `V` (verificados).
- **Piso de Abelardo (derecha consolidada): ~12,33M · Cepeda con todo el centro:
  ~10,41M · brecha ~1,92M · Cepeda debe sumar ~2,65M (0,73M centro + 1,9M
  movilización).** Es escenario para dimensionar, NO pronóstico. Lo honesto: la
  derecha llega favorita porque se consolidó en 1V; remontar es la jugada de Petro
  2022 (que movió +2,7M de 1V a 2V), pero más difícil esta vez.
- **Territorial** (`twov_territorial.json`): `recuperar = max(0, techo − cepeda)`
  donde techo = Petro 2V 2022. Por **municipio** (desde `BF['muni']` petro2v/cep26/base,
  + "centro disponible" = centro26×base×0,55) y por **puesto** (join masters 2026↔2022
  por pcode `dep+mun+zona+puesto`, **filtra zona 90/98 y dep 88**). El recuperar nacional
  (~2,05M por municipio) ≈ la brecha de 1,9M → "los votos ya existieron con Petro 2022".

### Mapas de recuperación + matching por ciudad (`build_maps.py`)
`bogota_recuperar_map` (localidad, rotado 90°) + `city_recuperar_map(city, geojson,
codefield, namefield, fname, mode)` para Cali/Medellín/Barranquilla (sin rotar).
`recuperar` por comuna desde `BA['city_comuna'][city]`. **Cada ciudad casa distinto:**
- **Medellín/Cali** `mode='num'`: match por número de comuna (`int` del código).
  Medellín CODIGO 01-16 (corregimientos 50+ quedan grises); Cali comuna 1-22.
- **Barranquilla** `mode='name'`: su número de localidad NO coincide con el `id` del
  GeoJSON → match por nombre, con **clave de prefijo alfanumérico de 8 chars**
  (`re.sub(r'[^A-Z0-9]','',norm(s))[:8]`) que fusiona "Norte Centro Hi"+"Norte Centro
  Historico" y quita el guion de "Norte - Centro Histórico".
- Tres trampas resueltas: (1) si TODAS las comunas casan, el subset gris queda vacío y
  geopandas revienta en `set_aspect('equal')` → guardar `if len(gi): gi.plot(...)`;
  (2) features sin nombre (polígonos "SN") salían como "Nan" → nular `g[namefield].isna()`;
  (3) `int(zona/puesto)` falla en exterior (códigos alfanuméricos tipo 'A2') → `if isdigit`.

### Excel de soporte (`build_excel2.py`) — 15 hojas
Resumen · 1·Petro 2V-1V (depto/muni) · 2·Cepeda vs Petro (depto/muni/Bogotá-loc/crece+abst) ·
3·Centro · 4·Derecha (depto/muni) · **Ciudades·comuna** + **Ciudades·barrio** (enriquecidas:
"Votos por recuperar" + "Centro disponible") · Bogotá·estrato · **8·Camino 2V (municipio)** +
**8·Camino 2V (puesto)** (del `twov_territorial`; puesto trae nombres de depto/municipio).
- `fin(ws, pcols, zebra)`: bordes + **zebra crema** (`F4F0E7`, filas pares) + miles
  automáticos (`#,##0` a valores ≥1000) + autofiltro + freeze `A2`. `cf_div` (escala
  roja→verde en columnas con "(pp)") y `cf_bar` (barras de datos en "recuperar"/"centro
  disponible"); `cf_auto(ws)` las aplica por nombre de header al final, sobre TODAS las hojas.
- **Ciudades·comuna/barrio**: recuperar = (petro2v−cep26)×base, centro = centro26×base×0,55.
  **FUSIONAN duplicados por tilde** (ver gotcha) y filtran ruido (`_noise`: PUESTO CENSO,
  CONSULADO, CARCEL, EXTERIOR, OTROS, CORR, CIUDAD, SN, NULL).

### Gotchas de datos (CRÍTICOS — perder uno arruina cifras)
- **`city_comuna` tiene DUPLICADOS por tilde**: "Ciudad Bolívar"+"Ciudad Bolivar",
  "Mártires"+"Martires" → si no fusionas por nombre normalizado (sumando votos
  absolutos), una pisa a la otra (Ciudad Bolívar salía 4k en vez de 43k) o aparecen
  como dos filas. Fusionar SIEMPRE por `norm(nombre)`.
- **Puestos zona 90 (PUESTO CENSO/Corferias) y 98 (cárceles) + dep 88 (exterior)** son
  ruido geográfico → filtrarlos en la hoja de puestos y en los mapas/comunas.
- **Inter (subset latín) NO trae `→ ← ↔ ★ ✦`** → en el Word/gráficos usar `—`/`a`/`vs`/`–`.
- **Exterior**: códigos de zona/puesto alfanuméricos, sin nombre en PUESTOS_GEOREF.

### Entregable aparte para OTRO cliente — `tools/cliente-mesa/build.py`
Genera, desde `PRECONTEO_1V_2026_MESA_nombres_corregidos.csv`:
1. **`PRECONTEO_1V_2026_MESA_con_Claudia.csv`** — idéntico pero con Claudia López
   **recuperada EXACTA por mesa**. Hallazgo clave: **los votos de Claudia estaban
   escondidos en `total_votos_urna`** (el total ya los contaba, su columna llegaba en 0)
   → `Claudia_mesa = total − suma del resto de partes`. El residual nacional da
   **225.287 exacto, sin negativos** = su total oficial. **NO es estimación, es dato.**
   (Esto SUPERA la nota vieja de que Claudia "solo existe a nivel municipio".)
2. **`Resultados_1V_2026_por_mesa.xlsx`** — Excel bonito: hoja *Instrucciones* + hoja
   *Datos por mesa* como **Table de openpyxl** (`TableStyleInfo`, autofiltro + zebra),
   freeze `F2`, **sin códigos** → nombres de Departamento/Municipio/Zona-Comuna/Puesto
   (cruce con `PUESTOS_GEOREF.csv` por `CÓDIGO COMPLETO` de 9 dígitos = dep+mun+zona+puesto;
   `NOMBRE COMUNA` con "NULL" → vacío → "Zona N"; `NOMBRE PUESTO` para el puesto).
   Candidatos ordenados por votación nacional. 121.863 filas, ~12 MB. Ambos en
   `Bases de datos/nuevos archivos 1v 2026/`.

## Tipografía
| Uso | Familia | Peso |
|-----|---------|------|
| Títulos, partidos, página | `'Syne', sans-serif` | 800/500/400 |
| Candidatos en tabla | `'Syne', sans-serif` | 300 / 1.05rem |
| Datos numéricos (votos, donut) | `Avenir, sans-serif` | 400 |
| cbadge (curules) | `'Avenir Next', Avenir, sans-serif` | 500 / 0.95rem |
| Labels, monospace, nav | `'DM Mono', monospace` | 400 |

## Colores CSS
```css
:root {
  --white: #f4f3ef;   /* en day-mode: #1a1a2e */
  --blue:  #0047FF;
  --green: #4ade80;
}
body.day-mode { background: #e6ded3; color: #1a1a2e; }
/* Elegido: #39ff7a (noche) | var(--blue) (día) */
/* Tooltip hemiciclo/mapa: background rgba(6,8,16,0.97), border rgba(0,71,255,0.4) */
```

## Circunscripciones y toggles
`activeCirc` ∈ `'NACIONAL' | 'INDIGENAS' | 'RESULTADOS_GENERALES'`
- **NACIONAL / INDIGENAS** → muestra tabla de partidos con votos reales; D'Hondt de 100 o 2 curules
- **RESULTADOS_GENERALES** → muestra hemiciclo SVG + mapa Leaflet; si hay filtro territorial activo activa modo **WHAT IF** (D'Hondt sobre votos del territorio)
- `onCircChange(val)` es **async**: al pasar a RG propaga el filtro dep/mun con `loadRGFilter` + `updateHemicicloMap`

## Funciones JS clave
```js
dhondt(parties, seats)          // D'Hondt puro, devuelve array con .curules
getCircPartidosCalculated()     // partidos de activeCirc con curules calculados
getElegidosNac()                // Map<partido → Set<nombre>> de electos reales (lista abierta)
getTopCandidatesNac(partido, n) // primeros N elegidos; prioriza CLOSED_LISTS luego open list
renderHemiciclo()               // dibuja SVG + leyenda; usa _rgFilter para modo WHAT IF
renderNacional()                // tabla principal en modo NACIONAL/INDIGENAS
renderGeoPartidos(nivel, ...)   // tabla filtrada por dep/mun/pue
loadRGFilter(depCod, munCod)    // llena _rgFilter con votos del territorio
onDepChange / onMunChange / ... // cascada de filtros geográficos
```

## Listas cerradas
```js
const CLOSED_LISTS = {
  'PACTO HISTÓRICO SENADO': [...],       // 50+ nombres en orden de asignación
  'PARTIDO CENTRO DEMOCRÁTICO': [...],
  'PARTIDO POLÍTICO OXÍGENO': [...],
  'LA LISTA DE OVIEDO - CON TODA POR COLOMBIA': [...],
  'COLOMBIA SEGURA Y PRÓSPERA': [...],
  'PATRIOTAS': [...],
};
// renderListaCerrada(partido, curules) → HTML de filas con ✦ en elegidos
```
Para listas cerradas, `p.candidatos` en el JSON viene vacío; los nombres vienen de `CLOSED_LISTS`.

## Sistema de mapas Leaflet

### Variables globales (senado)
```js
senaMap            // instancia L.map (panel principal)
hemicicloMap       // instancia L.map (panel RESULTADOS_GENERALES)
_deptoGeoRaw       // GeoJSON departamentos (cacheado una sola vez)
_senaDepGeoCache   // { depCod: geoJSON } por municipios
senaDepWinner      // { depCode: {partido, votos, nombre} }
_senaMunWinner     // { munCode: {partido, votos, nombre} }
_senaNomMap        // { nombreNorm: depCode } para lookup por nombre
```

### Flujo de inicialización
```
init() → buildSenaDepWinner(deps) → rellena senaDepWinner + _senaNomMap
       → initSenaMap() → sólo cachea DEPTO_GEOJSON en _deptoGeoRaw (sin crear mapa)
Al ir a RESULTADOS_GENERALES → initHemicicloMap() → crea hemicicloMap + _buildHemicicloGeo()
```

### Identificar el departamento en GeoJSON
```js
function _senaDepCode(props) {
  // Primero intenta props.electoral_id
  // Luego busca en _senaNomMap por nombre normalizado (sin tildes, uppercase)
}
```
Aliases especiales en `_senaNomMap`: NORTE DE SANTANDER, VALLE DEL CAUCA, SAN ANDRES, BOGOTA D.C.

### Actualizar el mapa al filtrar
```js
updateSenaMap(depCod)                 // panel principal (NACIONAL/INDIGENAS) — actualmente no inicializa L.map
updateHemicicloMap(depCod, munCod)    // RESULTADOS_GENERALES
// depCod '' → vista nacional (_hemicicloNacLayer)
// depCod=16 (Bogotá)        → BOGOTA_LOC_URL + rotateGeoJSON90Left + colorea por LocCodigo
// depCod+munCod=Medellín    → MEDELLIN_COM_URL sin rotar + colorea por CODIGO
// default                   → DEPTOS_MPS_URL/{padCode}.json + colorea por mun_elec
```

### Ciudades especiales (CITY_MAPS)
```js
// Todos los GeoJSON viven en mapas-2026/Ciudades-COM-LOC/:
// BOG-LOCALIDADX.json   → Bogotá (localidades, rota 90° izq)
// MEDELLINX.json        → Medellín   CODIGO (2c), NOMBRE
// CALIX.json            → Cali       comuna (int), nombre
// BARRANQUILLAX.json    → Barranquilla  id (int), nombre
// IBAGUEX.json          → Ibagué     COMUNAS='COMUNA N'
// MANIZALESX.json       → Manizales  ID_COMUNA ('01'..'12'), NOMBRES_CO
// PEREIRAX.json         → Pereira    Comuna (nombre; match por __byName)

rotateGeoJSON90Left(geoData)            // sólo Bogotá, cx=-74.08, cy=4.65

_buildLocComWinner(depCod, munCod)
// → { '01':{...}, ..., __byName:{ 'NORM NOMBRE':{...} } }
//   Index por código zz y por nombre normalizado. Requerido para Pereira.

CITY_MAPS = { bogota, medellin, cali, barranquilla, ibague, manizales, pereira }
// Cada entry: { key, url, rotate, code(p), name(p) }
detectCity(depCod, munCod, munName)     // → cfg o null
_renderCityLayer(cfg, winner)           // genérico: fetch+cache+style+tooltip+fit
_cityGeoCache = {}                      // una fetch por ciudad/sesión

// Bogotá se detecta por depCod=16 (su único mun es 001).
// Las demás se detectan por nombre del mun en getDepJSON('municipios').
```

### Botón volver del mapa RG
- `#hemiciclo-back` está absolutamente posicionado top-right dentro del contenedor relativo del mapa.
- `updateHemicicloBackBtn(depCod, munCod)` se llama al final de `updateHemicicloMap`:
  - Sin `depCod` → oculto
  - Con `munCod` → label "← Departamento", onclick limpia `mun-select` y llama `onMunChange('')`
  - Sin `munCod` → label "← Nacional", onclick limpia `dep-select`+`mun-select` y llama `onDepChange('')`

### Custom select overlay (móvil rotado)
Problema: `<select>` abre el picker del SO en orientación del dispositivo, ignorando
nuestro `transform:rotate(-90deg)`. Solución: al detectar
`window.matchMedia('(orientation:portrait) and (max-width:900px)')`, interceptar
`mousedown`/`touchstart` de los selects y mostrar un modal propio
(`._sel-overlay`/`._sel-panel`) dentro del DOM rotado. Tras elegir una opción,
`selectEl.dispatchEvent(new Event('change',{bubbles:true}))` dispara el inline
`onchange="onDepChange(this.value)"` como si fuera nativo.

### Click-to-filter en el mapa RG
- `_buildHemicicloGeo()` (capa nacional): click en depto → `dep-select.value=cod; onDepChange(cod)`
- `updateHemicicloMap` default (capa muns): click en mun → `mun-select.value=cod; onMunChange(cod)`
- Ambos buscan la opción del select con `String(Number(o.value))===String(Number(code))`
  para reconciliar códigos padded ('01') vs normalizados ('1').
- CSS: `#hemiciclo-map .leaflet-interactive{cursor:pointer}` da señal visual.

### Filtro RG propagado desde NACIONAL/INDIGENAS
`onCircChange('RESULTADOS_GENERALES')` lee dep/mun/zona/pue/mesa y construye `_rgFilter`
usando el dato más profundo disponible (mesa → pue → zona → mun → dep) vía `_buildRGFilterFromData`.

### Tooltip del mapa
```css
/* CSS obligatorio para override de Leaflet */
.leaflet-tooltip {
  font-family: Avenir, sans-serif !important;
  font-weight: 400 !important;
  font-size: .85rem !important;
  background: rgba(6,8,16,0.97) !important;
  border: 1px solid rgba(0,71,255,0.4) !important;
  color: #f4f3ef !important;
  width: 220px !important;           /* fijo para evitar colapso con nombres largos */
  white-space: normal !important;
  overflow-wrap: break-word !important;
  word-break: normal !important;     /* NO usar break-word aquí, colapsa a 1 char */
  border-radius: 0 !important;
  padding: .45rem .65rem !important;
}
.leaflet-tooltip:before { display: none !important; }
```
El HTML del tooltip va en un `<div>` inline con los mismos estilos de fuente (Leaflet ignora estilos del contenido sin el CSS override arriba).

### Portar el mapa a camara-2026.html
Renombrar variables `sena` → `cam` y duplicar:
- `senaMap` → `camMap`, `senaDepWinner` → `_camDepWinner`, etc.
- Las URLs S3 cambian: `senado/` → `camara/` (confirmar estructura)
- `DEPTO_GEOJSON` y `DEPTOS_MPS_URL` son compartidos (mismos GeoJSON)
- `getColor(partido)` es compartido
- **Atención códigos**: la Cámara usa `electoral_id` que NO coincide con DANE.
  En cámara: `01`=Antioquia, `03`=Atlántico, `05`=Bolívar, `16`=Bogotá, `60`=Amazonas.
  Los archivos `Departamentos-mps/{cod}.json` están keyados por electoral_id (no DANE).
  El GeoJSON nacional `DEPARTAMENTOS2.json` NO trae `electoral_id` — sólo `name` —
  así que `_camDepCode(props)` cae al lookup por nombre normalizado en `_camNomMap`.

## Cámara 2026 — sistema RG (WHAT IF) y flujo

### Variables globales clave
```js
_rgMode           // true cuando el toggle "Resultados Generales" está activo
_rgCamFilter      // { nombre, partidos, depCod } | null — WHAT IF state
_rgIIFEToken      // contador para abortar IIFE stale (ver race fix abajo)
camMap            // L.map del panel RG
_camDeptoGeoRaw   // GeoJSON nacional cacheado
_camDepGeoCache   // { depCod: geoJSON } por dep
_camNacLayer      // capa nacional (se REMUEVE al entrar a dep)
_camDepLayer      // capa dep (se REMUEVE al volver a nacional)
_camDepWinner     // { depCod: {partido, votos, nombre} }
_camNomMap        // { NOMBRE_NORM: depCod } para lookup desde GeoJSON
curDep/curMun/curZon/curPue/curMesa  // 'TODOS' o código
curDepData/curComData                // JSON cargado del dep / de la comuna
```

### Race condition del toggle RG (fix commit `eab3225`)
`onCircChange('RESULTADOS_GENERALES')` destruye el mapa y lanza un IIFE async
que termina con `rAF x2 → initCamMap().then(updateCamMap(...))`. El closure
captura `_rgEffDep/_rgEffMun` del momento del toggle. Si el usuario hacía
click en un depto antes de que el rAF disparara, el IIFE resumía con valores
stale y llamaba `updateCamMap('', '')` pisando el `_camDepLayer` recién
renderizado por `switchDep`.

**Solución**: `_rgIIFEToken` global. `onCircChange` captura su token; cada
async checkpoint y el rAF final chequean `_rgMyToken !== _rgIIFEToken → return`.
`_ensureRGActive()` (llamado por switchDep/switchMun/switchZon/switchPue/
switchMesa en rama RG) bumpea el token, invalidando cualquier IIFE stale.
Adentro del rAF final también se leen `curDep/curMun` frescos en vez de
los capturados en closure, como segunda línea de defensa.

### WHAT IF — reconstrucción al entrar a RG
`onCircChange('RG')` lee mun/zon/pue/mesa actuales y construye `_rgCamFilter`
con el dato más profundo disponible (mesa → pue → zon → mun). Si `curComData`
no está cargado pero hay `zon`, intenta `getComJSON(dep,mun,zon)`. Luego
`_rgRenderHemicicloWhatIf()` corre `asignarCurules()` (NO `dhondt()` — la
cámara sólo tiene `asignarCurules`, `dhondtDep`, `dhondtPuro`) sobre
`_rgCamFilter.partidos` con las curules del depto. Muestra aclaración
WHAT IF?! arriba del hemi vía `_setWhatIfText(lugar)`.

### Helpers recientes
```js
_zonLabelFor(depCod, munName)  // 'Localidad:' para Bogotá (dep=16) y
                               // Barranquilla (match por nombre); resto 'Comuna:'
_applyZonLabel(depCod, munName) // aplica al DOM #zon-label
```
Placeholder del zon-select también cambia: `'Todas las localidades'` vs `'Todas las comunas'`.

### Auto-mun para Bogotá
Al hacer `switchDep('16')` (tanto en TERRITORIAL como en RG), se setea
automáticamente `mun-select.value='001'` y se llama `switchMun('001')` para
abrir directo la vista de localidades. Bogotá tiene un solo mun (001 =
Bogotá D.C.) y no tiene sentido quedarse en la vista de "muns del depto".

### Listas cerradas cámara (por dep)
`CLOSED_LISTS_CAM[depCod]` y `AFRO_CLOSED_LISTS` (circunscripción afro).
`_buildWinnerNamesDep(dep, curMap)` → nombres de ganadores para tooltips
del hemiciclo. `_buildWinnerNamesNacional()` combina territorial + indígenas
+ afro para la vista nacional (165 curules = 161+2+2).

### BIG_CITIES toast custom (C.1 · sprint cámara cierre)
Cuando el usuario hace drill a las ciudades grandes, los archivos del mun
(com-{mun}-{com}.json hasta ~3 MB) tardan en cargar. `showLoadingToast(msg)`
acepta mensaje custom. `isBigCity(depCod, munCod)` chequea contra
`BIG_CITIES = {16:001 Bogotá, 01:001 Medellín, 05:001 Bolívar/Cartagena,
31:001 Cali, 08:001/03:001 Barranquilla}` (mezcla códigos DANE + electoral_id
porque la cámara usa estos últimos pero hay variantes).

Hooks vivos:
- `switchMun`: `showLoadingToast(isBigCity(curDep, munCod) ? 'En unos segundos cargarán las comunas/localidades' : undefined)`.
- `switchZon`: `showLoadingToast(isBigCity(curDep, curMun) ? 'En unos segundos cargarán los puestos y mesas' : undefined)`.

> Nota: cámara NO rota el contenido 90° en móvil portrait como senado.
> El `<select>` nativo funciona OK en móvil sin overlay custom. Si en el
> futuro se decide rotar la cámara para móvil, copiar el patrón
> `_sel-overlay`/`_sel-panel` de senado (líneas ~2327-2378).

## Donut chart — participación + género
### Donut principal `#donut-senado`
- Chart.js 4, `type:'doughnut'`, `cutout:'72%'`
- Centro: `#pct-senado` (porcentaje) y `#sub-senado` (label dinámico)
- Si hay potencial electoral → centro muestra `% participación`, segmento **Abstención** en gris
- Si no hay potencial → modo legacy `% válidos`
- Day-mode: `.donut-sub` necesita `color: rgba(0,0,0,.45)`
- Leyenda: `.li` / `.ld` / `.lv` en Avenir 400

### Potencial electoral
- Fuente: `COMUNAS_DATA.csv` (Divipole-actualizado), columnas `dd/mm/zz/pp/mujeres/hombres/total`
- `dd` = dep (2 chars), `mm` = mun (3 chars), `zz` = zona/commune (2 chars), `pp` = puesto (2 chars)
- `loadPotencialCSV()` → carga y cachea una sola vez
- `getPotencialFor({depCod, munCod, comCod, zonaCod, pueCod})` → `{potencial, mujeres, hombres}`
  - `comCod` y `zonaCod` ambos mapean a la columna `zz` del CSV
  - **Normalización de códigos**: UI usa 3-char para comuna (`'001'`) y código compuesto
    para puesto (`'com-zona-pue'`, ej: `'000-90-01'`). El helper normaliza con
    `String(parseInt(v,10)||0).padStart(2,'0')` para que coincida con `zz`/`pp` del CSV.
  - Si `pueCod` viene compuesto, se extrae `parts[1]` → zz, `parts[2]` → pp.
  - Mesas no tienen censo propio → pasa `potencial:null` pero sí pasa m/h del puesto padre

### Donut de género `#donut-gender`
- Canvas 90×90px dentro de `#gender-donut-wrap` (oculto con `display:none` si no hay datos)
- `drawGenderDonut({mujeres, hombres})` — llamado internamente desde `drawDonut()`
- Colores: mujeres `#ff6eb4` (rosa), hombres `#0047FF` (azul)
- Centro: `#pct-gender` muestra % mujeres; sub-label fijo "mujeres"
- Leyenda: `#leg-gender` con cifras absolutas

### Flujo de render
```js
drawDonut({vv, vn, vm, vb, votant, potencial, mujeres, hombres})
  → actualiza #pct-senado / #sub-senado / #leg-senado / donutChart
  → llama drawGenderDonut({mujeres, hombres})

// Obtener datos de potencial antes de llamar drawDonut:
const {potencial, mujeres, hombres} = getPotencialFor({depCod, munCod, comCod});
```

## Toast de carga
```js
showLoadingToast(msg?)  // 'Un momento, cargando…' por defecto; override con msg custom
// En onPueChange, si isBigCity(depCod, munCod) → 'En unos segundos cargarán las mesas'
const BIG_CITIES = new Set(['16:001','05:001','01:001','76:001','31:001']); // Bogotá, Medellín, Cali (tentativo por electoral_id)
```

## Hemiciclo SVG
- 100 curules en 4 anillos: r=80(16), r=123(22), r=168(28), r=213(34)
- `viewBox="0 0 600 310"`, centro `cx=300, cy=295`
- Posiciones de izquierda→arriba→derecha, ordenadas por partido (mayor curules primero)
- Tooltip: `div#hemi-tooltip` creado dinámicamente, `position:fixed`, Avenir 400 .85rem
- Modo WHAT IF activo cuando `_rgFilter != null`

## Cursor custom + modales (regla importante)
`body{cursor:none}` + `<div class="cursor">` + `<div class="cursor-ring">` con
handlers JS en `mousemove`/`mouseover`. Dos reglas que hay que respetar al
añadir modales/overlays:

1. **z-index del cursor > z-index de cualquier modal/overlay.**
   `.cursor` usa `z-index:100000`, `.cursor-ring` usa `99999`.
   `.dl-modal` (descarga excel) usa `z-index:99997`. Si se añade un overlay
   nuevo con z-index ≥ 100000, el cursor queda oculto detrás → "se desaparece
   el mouse" mientras el modal está abierto.
2. **Al cerrar un modal hay que resetear el estilo del cursor.** El botón
   "Cancelar" sobre el que se hizo click desaparece sin disparar `mouseout`,
   y el cursor queda con los estilos de hover (`background:transparent`,
   `ring opacity:0`) = cursor fantasma hasta que el mouse se mueve sobre
   otro elemento. Ver `closeDlModal()` en `camara-2026.html`:
   ```js
   const c=document.getElementById('cursor'), r=document.getElementById('cursorRing');
   if(c){ c.style.transform='translate(-50%,-50%) scale(1)'; c.style.background='var(--blue)'; c.style.border='none'; }
   if(r){ r.style.opacity='.4'; }
   ```
   Aplicar este reset en cualquier función que cierre un modal u overlay
   donde el elemento bajo el puntero desaparece del DOM.

## Combate Electoral — `combate-electoral.html` (juego de pelea tipo KOF'98 · LISTO v1)

> **Renombrado:** antes era `kof-electoral.html` / carpeta `kof-electoral/`. Se
> cambió a `combate-electoral.html` / `combate-electoral/` **por seguridad legal**
> (fuera todo "KOF" / "King of Fighters" visible: `<title>`, cards del index en
> es/en/zh/pt — se quitó 格斗之王 —, y los 3 mp3 "KOF98…"). El **Kart Presidencial**
> (`kart-presidencial1v.html`) se **eliminó del repo** y su enlace en `index.html`
> se reemplazó por este juego. URL pública: `ricardoruiz.co/combate-electoral.html`.

Juego de pelea **tipo The King of Fighters '98** (parodia) con los candidatos
presidenciales 2026, tema **"SEGUNDA VUELTA COLOMBIA '26"**. Single-file HTML
autocontenido (~50 KB, sin build), motor de pelea en **canvas 2D**. Enlazado
desde `index.html` (proyectos, es/en/zh/pt como "Combate Electoral").

### Estructura de archivos
```
combate-electoral.html                       el juego (todo: HTML+CSS+JS inline)
combate-electoral/
  LEEME.txt                                  doc de assets de candidatos+música
  candidatos/<id>.png                        retrato del selector (PNG TRANSPARENTE vertical)
  candidatos/fight/<id>.png                  pose base de pelea (guardia, transparente)
  candidatos/fight/punos/<id>-der|izq.png    pose de PUÑO (der=mira derecha, izq=izquierda)
  candidatos/fight/patada/<id>-der|izq.png   pose de PATADA
  candidatos/fight/golpe-recibido/<id>-der|izq.png   pose de GOLPE RECIBIDO (o <id>.png único)
  stages/<id>.png                            escenarios panorámicos (~16:9, sin espacios en el nombre)
  stages/LEEME.txt
  music/intro.mp3 · instrucciones.mp3 · seleccion.mp3   música por pantalla (loop)
  music/winner.mp3 · continue.mp3 · "jefe final.mp3"    clips one-shot
```
`ids`: `cepeda · petro · santos · abelardo · uribe · paloma · ricardo`.
**El motor carga los frames por nombre; lo que falte cae a la pose base** (no se
rompe nada). `.DS_Store` ya está en `.gitignore` (raíz del repo).

### Candidatos (`FIGHTERS`) + `RICARDO` (anfitrión / jefe final)
6 seleccionables: **Cepeda · Petro · Santos · Abelardo · Uribe · Paloma**.
`RICARDO` es el **anfitrión** (instrucciones) y el **JEFE FINAL** (no aparece en la
selección salvo que lo desbloquees venciéndolo). Cada uno: `id, name, short, ini,
partido, epi, color, accent, special, stats, line, srcFace`.
- **`srcFace`** = orientación natural del PNG base (1 = mira a la derecha, -1 = a la
  izquierda). Solo **Cepeda = -1**; el resto = 1. `drawFighter` voltea con
  `facing !== srcFace` para que cada uno mire al rival.

### Flujo de pantallas (`go(id)`)
```
title → howto → select → versus → fight → (winner | continue) → [credits]
```
- **title**: logo "SEGUNDA VUELTA / COLOMBIA '26 / EL CAMBIO POR LA VIDA O FIRMES
  POR LA PATRIA". "INSERTE VOTO". Por el bloqueo de autoplay, **el 1er toque
  desbloquea audio + intro y el 2º entra** (si el navegador permite autoplay, un
  solo toque).
- **howto (instrucciones)**: muestra a **Ricardo (anfitrión)** con su frase fija;
  su imagen **alterna puño/patada cada 1 s** (sin badge). Controles reales:
  **← → mover · ↑ saltar · ↓ cubrir · A puño · S patada** + nota de botones en móvil.
- **select**: 6 candidatos + Ricardo (si desbloqueado). Botón **🎲 AL AZAR**, **TIME
  grande** (cuenta 26→0, auto-elige). Bloqueados en gris + 🔒 + "???". **Sin
  iniciales detrás** de las fotos (son transparentes).
- **versus**: ruleta **"EL SIGUIENTE RIVAL"**. Para el **jefe final**: pantalla
  oscura **"COMBATE FINAL"** con **tu silueta (?)**, el **lugar a la derecha**
  (C.C. Galerías) y **los derrotados en gris**. Hint del escenario = `ricardoruiz.co`.
- **fight**: motor de pelea (ver abajo).
- **winner / continue / credits**: ver abajo.

### Desbloqueos y escalera
- **Desbloqueos** en `localStorage['combate-unlocked']`. Base: **Cepeda + Abelardo**.
  Cada victoria **desbloquea al vencido** (vencer a Ricardo desbloquea a Ricardo
  como jugable). `getUnlocked()/unlock(id)`.
- **Escalera (`confirmPick`)**: orden **FIJO** para los dos finalistas reales y al
  azar para el resto. `FIXED_LADDER`:
  - **Cepeda** → Paloma, Uribe, Santos, Petro, Abelardo, **+ Ricardo (jefe)**.
  - **Abelardo** → Petro, Santos, Paloma, Uribe, Cepeda, **+ Ricardo (jefe)**.
  - resto → `shuffle`. `state.stageOrder = shuffle(STAGES)` → **escenarios no se
    repiten** en una escalera.

### Motor de pelea (canvas, objeto `F`)
- Canvas interno **1024×768**, 4:3. `F` = `{W,H, groundY:0.90, spriteH:0.42,
  walk:3.6, jumpV:20, grav:0.95, reach:104, punchDmg:4.2, kickDmg:7, punchCD:340,
  kickCD:560, atkWindow:160, knock:30, hitStun:280, comboWin:1100, koDur:2600}`.
  (Daño −30% vs original 6/10: las peleas duraban 10-12 s.)
  **Escala por peleador**: `fd.scale` (solo **Abelardo `1.05`**, +5%) multiplica la
  altura en `drawFighter` y ancho/hitbox/sombra/límites en `fwOf`; pies anclados
  (`top=gy-dh`).
- **Frames por estado** (`drawFighter`): `stun/ko` → pose de **golpe-recibido**;
  `atk==='punch'` → **puño** (der/izq según facing); `atk==='kick'` → **patada**;
  si no, **pose base**. der/izq ya van orientadas (no se voltean); base usa `srcFace`.
  **Flash blanco** al recibir golpe (`ctx.filter='brightness(0) invert(1)'`).
- **Física**: salto (`jumpV`), gravedad, separación de cuerpos, límites.
- **IA** (`aiIntent`): acerca, golpea con cooldown, cubre, retrocede. El jefe (boss)
  tiene 120 de vida (vs 100) y es algo más agresivo.
- **Combos** (`N HITS`), **Perfect** (ganar sin recibir daño), **score** =
  vitalidad + tiempo + perfect + racha + combo (se **acumula por partida**).
- **HUD**: barras **anchas** con **capa roja de daño** (baja con retraso hasta la
  vida real), **timer grande** al centro, **foto pequeña** (1P izquierda, **2P al
  extremo derecho**), **nombre debajo de la barra** y **score del 1P**. Móvil:
  `body.touch` muestra **#fight-touch** (d-pad ◀▲▼▶ + botones A/S). Las teclas se
  dimensionan **relativas al cabinet** (`clamp(px, min(vh,vw), px)`, no `vw` puro, que
  en landscape se inflaba) y en touch el **piso sube a `0.80`** (`fGroundPx`) para que
  los peleadores queden por encima de las teclas. El cabinet es **4:3** fijo
  (`#screen: min(100vw,100vh·4/3)`); pensado para **landscape** (en portrait queda chico
  y centrado con franjas negras).
- **Layout VERTICAL en móvil** (`@media (orientation:portrait) and (max-width:820px)`,
  al final del `<style>` para ganar la cascada): aplica por ORIENTACIÓN, no por
  dispositivo → **iPhone y Android idéntico** (verificado en viewport 375×812 y
  412×915). NO se fuerza landscape (el `#rotate-hint` quedó retirado). `#screen`
  rompe el 4:3 y usa `100svh` con **fallback `100vh`** (Android/WebView viejos sin
  `svh` descartarían la regla y caerían al cabinet 4:3 chico). La **pelea va centrada verticalmente**: el canvas
  + sus overlays se envuelven en `.fight-stage` (4:3, sin estirar) y `#scr-fight.active`
  es `flex column; justify-content:center` con `padding` de `env(safe-area-inset-*)` →
  canvas y controles centrados como grupo, **libres del notch (arriba) y del home bar
  (abajo)**. `#fight-touch` pasa a item de flex debajo del canvas (relativo, no
  absolute). Instrucciones y winner pasan a **columna centrada** (arte arriba, texto
  abajo). El botón **¡PELEAR!** del versus se sube con `padding-bottom` (no pegado al
  borde). **Clave:** los overrides de `#scr-fight`/`#fight-touch` deben ir calificados
  con `.active` (p.ej. `#scr-fight.active{display:flex}`) — un `#scr-fight{display:flex}`
  pelado (ID) pisa el `.screen{display:none}` y deja la pantalla SIEMPRE visible (bug).
- **`svh` + pantalla completa**: el cabinet usa `100svh` (fallback `vh`) → alto visible.
  `goFullscreen()` pide `requestFullscreen()` al primer toque (solo `body.touch`):
  Android/iPad entran a pantalla completa; iPhone Safari no lo permite por API (ahí el
  `svh` + layout vertical ya resuelven). El fullscreen **NO toca la orientación** (no
  hay `orientation.lock`): en Android vertical solo quita la barra del navegador y el
  layout vertical se mantiene. Metas `apple-mobile-web-app-capable` +
  `viewport-fit=cover` para "Agregar a inicio" sin barra.
- **Layout responsive (cabinet-relative)** para que nada se desborde en cabinet chico:
  logo `.fighters`/`.year` con `min(vw,vh)` (antes `vw` puro se salía en landscape);
  título `.tap-hint`/`.insert` con `bottom:max(%,px)` (no pisan el `.hud`); botón
  **AL AZAR** más compacto en `@media` (font 7px, sin letter-spacing); instrucciones
  `@media` compactas + top-align + `#scr-howto .hud` oculto para que no se recorte el
  texto ni choque el "PULSA TECLA" abajo.
- **Cámara** (`drawCover` + `fCamX`): el fondo panorámico **panea** según el punto
  medio entre peleadores; el paneo es **proporcional al sobre-ancho** de cada
  imagen (anchos como Cali/Barranquilla/Galerías se mueven más). Sin huecos.
- **K.O.** (`endFight` → `fPhase='ko'`): al llegar la vida a 0, el perdedor **se
  desploma rotando (~85°) y bajando durante ~2.6 s** (`koDur`), con su pose de
  golpe-recibido + texto **"K.O."**; al terminar → `finishMatch()` abre winner /
  continue. (Por tiempo agotado: gana quien tenga más vida, sin caída.)
  **Destello de pantalla**: durante el K.O. `fDraw` pinta un strobe **rojo/blanco
  fuerte** (~14 Hz, con fade-in/out) ENTRE el fondo y los peleadores → la pantalla
  destella pero **los combatientes NO se tiñen** (van encima; su flash propio se
  suprime con `fPhase!=='ko'`). El texto **"K.O." va al doble** (`#fight-center-msg.big`,
  solo ese texto) y sale el aviso **"(NOMBRE) GANA"** (`#ko-win-banner`) del lado del
  ganador mientras suenan los audios.
- **Controles**: teclado (← → ↑ ↓ A S) + táctiles en móvil.

### Winner / derrota ante el jefe / continue / créditos
- **Winner** (jugador gana): retrato del selector + **frase del ganador SOBRE el
  vencido** (`SPEECHES`, ver abajo) + **tally de score** animado (`winner.mp3`,
  ~6 s) + **animación de entrada** (el cuadro entra por un lado y el texto por el
  otro). Móvil: **tocar en cualquier parte avanza**. Desbloquea al vencido.
  - **Campeón** (venciste al jefe final): título **personalizado** (`championTitle`):
    Cepeda/Abelardo → "¡-N- PRESIDENTE EN 2NDA VUELTA!"; Paloma → "¡PALOMA SERÁ
    PRESIDENTA EN 2030!"; Petro → "¡PETRO PRESIDENTE DE NUEVO!"; Uribe/Santos →
    "¡-N- PRESIDENTE ETERNO!". El botón pasa a **VER CRÉDITOS**.
- **Derrota ante el JEFE FINAL** (`fBossWin`): **Ricardo gana** y **critica a tu
  candidato con un dato real** (`RICARDO_WIN`); al terminar `winner.mp3` → arranca
  el **continue**.
- **Continue**: `continue.mp3` + countdown 10 s. **SÍ = revancha** del mismo rival;
  **NO/0 = inicio**.
- **Créditos** (`#scr-credits`): al vencer al jefe final y pasar el winner → roll de
  créditos (título de campeón + ficha técnica + "El voto es tuyo. Nos vemos en las
  urnas." + gracias · ricardoruiz.co) → VOLVER AL INICIO (tap en cualquier parte).

### Frases (`SPEECHES`, `RICARDO_WIN`) — ojo legal
- **Ancladas en rivalidades públicas y documentadas**, en personaje, **neutrales y
  sin imputar delitos ni inventar citas textuales**: Cepeda↔Uribe (el duelo en los
  estrados, "de acusador a acusado, absuelto 2025"), Santos (ex-MinDefensa de
  Uribe y el "No" al Acuerdo 2016), Petro (ex-M-19, alcalde/presidente), Abelardo
  (admira a Uribe; **es el rival real de 2da vuelta de Cepeda, 43,7% en 1V**),
  Paloma (uribista, propuso regiones autónomas), Pacto = lista más votada al Senado
  2022, plebiscito 2016. **Slogans** al final de la frase: Abelardo "¡Firmes por la
  Patria!", Cepeda "¡Me la juego por la Vida!".
- Si el usuario aporta **citas textuales reales con fuente**, insertarlas atribuidas.
- Fuentes usadas (rivalidad Uribe/Cepeda y perfil Abelardo): Wikipedia "Caso Uribe",
  CNN Español (fallo 2025 / revocatoria oct-2025 / perfil Abelardo 28-may-2026).

### Escenarios (`STAGES`)
`bogota` (Plaza de Bolívar) · `medellin` (El Poblado) · `cali` (Jaime Varela) ·
`barranquilla` (Malecón del Río) · `cartagena` (Castillo de San Felipe) ·
`macarena` (Caño Cristales) · `narino` (Santuario de Las Lajas) · + **`final-boss-stage`**
(C.C. Galerías, Bogotá — solo el jefe final). En una escalera no se repiten.

### Audio (3 canales + SFX)
- **Música de pantalla** (`TRACKS`, loop): `intro.mp3` (title), `instrucciones.mp3`
  (howto), `seleccion.mp3` (select).
- **Clips one-shot** (`CLIPS`, canal único `curClip` vía `playClip`): `winner.mp3`,
  `continue.mp3`, `"jefe final.mp3"` (tema del jefe, loop en el boss fight).
- **Voces / locuciones** (`VOICES`, **canal propio** `curVoice` vía `playVoice` /
  `playVoiceSeq` / `stopVoice` — se solapan con los clips y **encadenan** una tras otra):
  - **ROUND** al entrar a cada rival: `playVoiceSeq([round, NUM_VOICE[matchIdx], ready])`
    → "ROUND ONE/TWO/…" + **"¿Listos?"** (`ready-voice`). En el **jefe final** suena
    `[round, ready]` **sin número**. `NUM_VOICE` mapea one…six; los que falten se
    omiten solos (`onerror`). El texto en pantalla también es dinámico (`ROUND N`).
  - **K.O.**: `ko-voice` en el momento del K.O. (con los destellos); `perfect`
    **encadenado después** sólo si fue K.O. perfecto del jugador (sin recibir daño).
  - **Winner**: `winner-voice` en capa con `winner.mp3` al aparecer la imagen (también
    en la derrota ante el jefe).
- **Saludos de apertura** (**en secuencia** tras el "¿Listos?", antes de pelear ·
  `playGreetings`): primero el del **rival** (`opp-me`, si tiene), al terminar el del
  **candidato propio** (`me-opp`). Cada peleador saluda con `"{id}-{rival}.MP3"`; si no
  existe, cae al genérico `"{id}-all.MP3"` (p.ej. **`santos-all`** — Santos no necesita
  uno por rival). NO se solapan (token `greetTok` invalida secuencias viejas).
- **Voz de victoria del ganador** (`playKoWinner`): al K.O. suena `"{ganador}-winner.MP3"`
  y **la pantalla de winner ESPERA** a que termine (gate `fKoWinReady` + `fKoUntil`).
- **`mkAudioChain(bases[])`**: prueba una lista de bases en orden, cada una con
  **`.MP3` → `.mp3`** (el host de prod es case-sensitive; el usuario mezcla mayús/minús).
  Toca la primera que exista; si ninguna, sigue sin colgar.
- **Gating del arranque** (`fFightStartAt`): la pelea arranca tras
  ROUND→número→¿Listos?→saludos (callbacks encadenados; topes anti-cuelgue 4–12 s +
  watchdog en `playVoiceSeq`). Muteado: intro fija de 1.1 s.
- **SFX de combate** (`SFX_FILES`, **fire-and-forget** vía `playSfxFile`): `puno.MP3` /
  `patada.MP3` **compartidos**, suenan en `tryAttack` al iniciar el golpe (jugador e IA).
- SFX sintetizados extra (WebAudio `sfx.gong/coin/...`). Botón 🔊 mute corta música +
  clips + voces + saludos + voz de ganador.
- **WIP del usuario** (NO referenciados · fuera del repo): `OICE COLLECTION…mp3` (base de
  música), SFX por candidato `puno/patada-{cepeda,paloma}.MP3` (si se quieren, wirear un
  override per-fighter; hoy el golpe es compartido), drafts con espacios (`cepeda a
  paloma.mp3`…), `holasantos.mp3`, `petrofin.mp3`, `recibe-puno.MP3`.

### Cómo agregar/cambiar assets (convenciones)
- Retrato selector: `candidatos/<id>.png` (transparente). Pose base: `fight/<id>.png`.
- Puño/patada: `fight/punos|patada/<id>-der.png` y `<id>-izq.png` (**der = golpe a
  la derecha**, ya orientadas — el motor NO las voltea).
- Golpe recibido: `fight/golpe-recibido/<id>-der|izq.png` (o `<id>.png` único como
  fallback). Stages: `stages/<id>.png` panorámico (sin espacios en el nombre; si
  trae espacio, renombrar — pasó con "La Macarena.png" → `macarena.png`).
- Tras subir imágenes/música: `git add` selectivo + commit + `git push origin HEAD:main`.
  **Validar el JS embebido con `new Function` antes de cada push** (regla del proyecto).

### Estado de frames por candidato (qué falta DIBUJAR)
| Candidato | Puño | Patada | Golpe recibido |
|---|---|---|---|
| Cepeda · Santos · Uribe · Paloma · Ricardo · Petro · Abelardo | ✅ | ✅ | ✅ |
→ Los 6 + Ricardo tienen puño/patada/golpe-recibido (der/izq) completos.

### Animaciones que aún NO existen (opcionales, backlog)
- **Salto** con frame propio (hoy usa la pose base en el aire).
- **Bloqueo** con frame propio (hoy pose base).
- **Pose de victoria en el ring** antes del winner.
- Pulido del K.O. (polvo/impacto al tocar el piso, pausa dramática).
- Caminar (ciclo) y mareo — nicho.

### Pendientes / ideas (handoff)
1. **`abelardo-izq`** golpe-recibido (solo está `-der`) → entra solo por nombre.
2. (Opcional) **SFX de golpe por candidato**: ya hay `puno-paloma`/`patada-paloma`;
   hoy el golpe es compartido (`SFX_FILES`). Wirear override per-fighter si se quiere.
3. **Música propia/libre**: la base WIP es `OICE COLLECTION & sound effects.mp3`.
4. (Opcional) animaciones de salto/bloqueo/victoria + pulido de K.O. + frames de
   **caminar** (carpeta `caminar/`, en progreso · `<id>-der1`/`-der2` para el ciclo).
5. Ideas grandes: best-of-3 rounds, dificultad creciente, más candidatos/escenarios.

### Verificación / preview (gotchas)
- `launch.json` levanta `python3 -m http.server 8765`. Abrir
  `http://localhost:8765/combate-electoral.html`.
- **El preview headless pausa `requestAnimationFrame` cuando `document.hidden`** →
  la pelea **no anima oculta** (el timer no baja, la caída no corre). Verificar la
  lógica por **DOM/eval** o por **screenshot** (que reactiva la visibilidad). Las
  pantallas DOM (selector/winner/continue/créditos) y los timers (ruletas) sí corren
  ocultos. El screenshot a veces va **rezagado** (muestra un frame anterior).
- Mezcla de orientaciones de PNG (algunos 1024×1536, otros cuadrados/panorámicos):
  el motor calcula el ancho **por imagen** (no asume aspecto fijo).

## Proyecto DC — capa privada (Daniel Carvalho · Alcaldía Medellín 2027)

### Contexto y reglas de visibilidad
Plataforma de investigación no declarativa para posicionar a Daniel Carvalho
rumbo a la Alcaldía de Medellín en 2027. **El nombre del candidato y el
objetivo electoral NO deben aparecer en HTML/contenido visible** — solo en
este CLAUDE.md y en commits internos. Las páginas se nombran "Proyecto DC ·
Investigación Medellín". Todas llevan `<meta name="robots" content="noindex,nofollow">`.

### Acceso (gate por email)
- Whitelist hardcodeada en cada HTML privado: `['reruizc@gmail.com', 'nuevagemela@gmail.com']`
- **Doble gate**: localStorage (instantáneo, sin flash) + verificación contra
  `https://rr-auth.reruizc.workers.dev/auth/me` antes de revelar el contenido
- Si email no matchea → `window.location.replace('../dashboard.html')`
- Si token inválido → redirect a `login.html`
- Mientras verifica: overlay `.gate` con barra animada y texto "Verificando acceso"
- En `dashboard.html`: array `PRIVATE_TOOLS` con `allowedEmails` filtra qué
  tarjetas se renderizan en la grilla (tag morado `private-tag` `#7c3aed`)

### Archivos
```
proyecto-dc.html                          hub: 8 tarjetas de módulos + secciones descriptivas
proyecto-dc/voto-historico.html           módulo 01
proyecto-dc/seguridad.html                módulo 02
proyecto-dc/comportamiento-electoral.html módulo 03
proyecto-dc/pobreza-ipm.html              módulo 04
proyecto-dc/arquetipos.html               módulo 05
proyecto-dc/gobierno-criminal.html        módulo 06
proyecto-dc/agenda.html                   módulo 07
proyecto-dc/escenarios-2027.html          módulo 08 (simulador what-if 2027)
```

### Convención visual de páginas privadas (chasis a copiar)
- Cursor `--purple` `#7c3aed` (no blue como las públicas) · `--purple-dim` rgba 0.10
- Banner amarillo `--warn` `#f0c040` para datos simulados o disclaimers
- Banner rojo `--danger` `#e63946` para alertas
- Tipografía heredada del resto del sitio: Syne 800/500/400, DM Mono, Fraunces 300/400
- Mapa Leaflet con tooltip dark `rgba(6,8,16,0.97)`, border `var(--purple)`
- `.gate` overlay z-index 5000 que se remueve cuando `revealPage()`
- `.private-badge` en nav: "Privado" en morado

### Códigos Registraduría (archivos GCS_*TER.csv)
- **Antioquia=1, Medellín=1** (Registraduría — NO confundir con DANE 5/001)
- Bogotá=16/1 (Galán 2023 lo confirmó: 1.5M votos en (16,1))
- `COD_COR` numérico cambia entre años; usar `DES_COR` (texto) que también varía:
  - 2015: `ALCALDIA` / `GOBERNACION`
  - 2019/2023: `ALCALDE` / `GOBERNADOR`
- Aceptar ambas formas: `COR_DES_TO_NAME = {'ALCALDE':'alcaldia','ALCALDIA':'alcaldia','CONCEJO':'concejo'}`

### Mapeo zona electoral → comuna política Medellín
`COD_ZZ` del CSV TER es zona electoral (1-32, 90, 98, 99), NO comuna política.
Mapeo derivado de `PUESTOS_GEOREF.csv` (col ZONA → CÓDIGO COMUNA), estable
entre 2015-2026. Hardcodeado en `tools/build-medellin-historicos.js`:
```
01-02 → 01 Popular            17-18 → 09 Buenos Aires
03-04 → 02 Santa Cruz         19-20 → 10 La Candelaria
05-06 → 03 Manrique           21-22 → 11 Laureles Estadio
07-08 → 04 Aranjuez           23-24 → 12 La América
09-10 → 05 Castilla           25-26 → 13 San Javier
11-12 → 06 Doce de Octubre    27-28 → 14 El Poblado
13-14 → 07 Robledo            29    → 15 Guayabal
15-16 → 08 Villa Hermosa      30-32 → 16 Belén
99 → CORR (5 corregimientos agregados)   90,98 → OTROS / consular
```
Para desagregar corregimientos individuales (50/60/70/80/90 del GeoJSON)
hay que cruzar `(ZZ=99, COD_PP)` con PUESTOS_GEOREF. Pendiente para v1.

### Scripts de procesamiento
- `tools/build-medellin-historicos.js` — Node streaming. Procesa
  `GCS_2015TER.csv`, `GCS_2019TER.csv`, `GCS_2023TER.csv` (~1.9 GB c/u) en ~15s
  cada uno. Filtra (depto=1, mun=1) y produce 5 niveles de agregación por
  corporación (alcaldía, concejo): `resumen.json` (ciudad), `por-comuna.json`
  (16+CORR+OTROS), `por-zona.json` (zonas electorales), `por-puesto.json`,
  `por-mesa.json`. Para concejo agrega D'Hondt sobre 21 curules.
- `tools/build-seguridad-medellin.py` — Python. Procesa los 19 CSVs de la
  Policía Nacional (un archivo por tipología) filtrando `MUNICIPIO_HECHO ==
  "Medellín (CT)"`. Extrae comuna desde `COMUNAS_ZONAS_DESCRIPCION` con regex
  (codes 01-16 + 50/60/70/80/90 alineados con GeoJSON). Genera 7 JSONs por
  período: `resumen` (nacional + Medellín + share + tasa por 100k),
  `por-comuna`, `por-dia`, `por-hora`, `por-genero`, `por-clase-sitio`,
  `por-dia-semana`. ~22% de incidentes caen en "OTROS / sin clasificar"
  porque `COMUNAS_ZONAS_DESCRIPCION` trae valores no parseables ("COMUNA
  NORORIENTAL", vacíos). Mejorar con cruce por barrio si sube prioridad.

### Validación de resultados (sanity check)
- 2015 alcaldía: Federico Gutiérrez 38.3% vs Vélez 36.8% (margen estrecho)
- 2019 alcaldía: Daniel Quintero 43.3% vs Alfredo Ramos 33.5%
- 2023 alcaldía: Federico Gutiérrez 79.1% (697.910 votos)
- Si los números no se acercan a estos valores conocidos, hay bug en el
  script (probablemente filtro de depto/mun o asignación de COR).

### S3 — paths del proyecto DC
**Política del bucket actual** (`elecciones-2026`) cubre:
- `consulta-2025/*` · `Congreso_2026_MMV170326.csv` · `congreso-2026/output/*`
- `DESCARGAS/*` · `Fotos-presidenciales/*` · `bases de datos/*` (incluye
  espacio literal en ARN — URL las codifica como `+` o `%20`)
- `ricardoruiz.co/proyecto-dc/agenda/agregados/*` (nube/medios/titulares
  del módulo 07 — añadida 2026-04-30)

> **Importante**: cada vez que se cree un nuevo prefijo bajo el bucket
> que el frontend deba leer públicamente, hay que añadir un statement
> a la bucket policy. El prefijo `raw/` y `state/` del módulo 07 NO
> son públicos (solo los lee la Lambda con su IAM role).

Datos del proyecto DC viven bajo `bases de datos/`:
```
bases+de+datos/output_medellin/{2015,2019,2023}/{alcaldia,concejo}/
  {resumen,por-comuna,por-zona,por-puesto,por-mesa}.json
bases+de+datos/output_seguridad/2026-01/
  {resumen,por-comuna,por-dia,por-hora,por-genero,por-clase-sitio,por-dia-semana}.json
bases+de+datos/Proyecto+DC/pdfs/
  informe_unificado_comportamiento_electoral_medellin_2021_2026.pdf
  informe_grupos_criminales_medellin_elecciones_2023_2026.pdf
```
Constante en módulos: `const HIST_BASE = '${S3_BASE}/bases+de+datos/output_medellin'`
y similares por módulo.

### Datos embebidos vs. S3 fetch (criterio)
- **Embebidos en HTML** (objetos JS al inicio del script): cuando son
  análisis cerrados, pequeños (<200 KB) y NO periódicos.
  - Módulo 03 (comportamiento electoral): paquete socia 2021-2026 cerrado
  - Módulo 04 (pobreza/IPM): cifras simuladas v0
  - Módulo 06 (gobierno criminal): paquete socia 2023-2026 cerrado
- **S3 + fetch**: datasets pesados o periódicos
  - Módulo 01 (voto histórico): 30 JSONs / ~43 MB total
  - Módulo 02 (seguridad): 7 JSONs por mes / ~60 KB total
  - Módulo 05 (arquetipos): 7 JSONs + 10 escudos + 10 PNGs de cartografía + PPTX

### Módulos disponibles (estado actual)
| # | Módulo | Datos | Estado |
|---|---|---|---|
| 01 | Voto histórico | 2015/2019/2023 alcaldía+concejo (S3) | ✓ |
| 02 | Seguridad y delitos | enero 2026 PNP (S3) | ✓ |
| 03 | Comportamiento electoral & MOE | paquete socia 2021-2026 (embebido) | ✓ |
| 04 | Pobreza e IPM | simulado v0 (embebido) | ✓ datos simulados |
| 05 | Arquetipos territoriales | paquete socia 2015-2027 (S3) | ✓ |
| 06 | Gobierno criminal | paquete socia 2023-2026 (embebido) | ✓ |
| 07 | Saliencia/agenda pública | 10 medios RSS + agregador (S3) | ✓ v1 (medios) |
| 08 | Simulador what-if 2027 (`escenarios-2027.html`) | arquetipo base módulo 05 + matriz psicopolítica Nury 2027 + huella Carvalho-Quintero (S3/embebido) | ✓ · 16 comunas + 5 corregimientos · 332 barrios |

> **Nota (2026-05-31):** el módulo 08 es ahora el **Simulador what-if 2027**
> (`escenarios-2027.html`), no PQRSD. El viejo "módulo 09 · proyección 1V
> Medellín" fue borrado (commit `ec4cba6`). La idea de **Fricción ciudadana /
> PQRSD** ya NO es una card numerada del hub — queda como fuente de datos
> pendiente (ver "Datos pendientes / faltantes"), no como módulo. El hub tiene
> 8 módulos (01–08).

### Datos pendientes / faltantes
- Censos electorales históricos por año (potencial 2015/2019/2023) → calcular abstención real
- PQRSD Medellín (datos abiertos)
- MEData / SISC / SIMM
- Pobreza/IPM oficial (DANE / Medellín Cómo Vamos) — reemplazar simulado
- Padrón electoral 2027 cuando salga
- Bloque B medios (4): El Colombiano, Blu Radio, Pulzo, Q'Hubo Medellín
  — Lambda con paso extra de parsear sitemap.xml + comparar lastmod.
- Bloque C medios (6): Caracol Medellín, RCN Radio, La FM, Semana, ADN,
  Teleantioquia — scraping HTML con selectores propios (Teleantioquia
  es SPA, requiere headless light o reemplazo).
- Redes sociales (Track 2): X, Instagram, Facebook (vía Apify si DIY no
  alcanza). Pendiente decisión costo/beneficio (~$200–400/mes con Apify
  vs scraper propio que requiere mantenimiento).
- Atribución a actores políticos (NER + lista curada con alias).
- YouTube Data API + Google Trends para señal de búsqueda.
- Mapa de actores políticos (concejales, periodistas, influencers)
- Senado/Cámara 2026 a nivel comuna Medellín (S3 actual solo tiene a
  nivel municipio — reprocesar `Congreso_2026_MMV170326.csv` similar al
  script de TER si se necesita drilldown)

### Módulo 05 — arquetipos territoriales (cartografía emocional)

Paquete cerrado de la socia (Nury, mayo 2026) sobre el voto barrial
en Medellín entre 2015 y 2027 (proyectado). Cubre 152 barrios DAP, 16
comunas + 5 corregimientos. **Clave de cruce:** `Código DAP` mapea 1:1
con `properties.CODIGO` de `MEDELLIN_BARRIOS_OFICIAL.json` (100%
coverage, sin fuzzy matching). PUESTOS_GEOREF.csv NO es necesario
para este módulo.

**Taxonomía de los 5 arquetipos × 2 versiones (10 entradas en
`arquetipos.json`):**
- Protección (azul `#2563eb`): base "Protección y orden cotidiano" → evol "Protección con resultados y orden competente"
- Continuidad (verde `#16a34a`): "Estabilidad y continuidad" → "Continuidad pragmática y gestión barrial"
- Supervivencia (cobrizo `#b45309`): "Supervivencia económica y servicios básicos" → "…y servicios cotidianos"
- Castigo (rojo `#dc2626`): "Desconfianza y castigo" → "Castigo a la restauración y demanda de alternancia"
- Pertenencia (fucsia `#a21caf`, distinto del cursor morado `#7c3aed`): "Pertenencia y dignidad territorial" → "Pertenencia comunitaria y autonomía territorial"

Las 5 versiones base 2015-2023 usan estética vintage propaganda; las 5
evolucionadas 2027 son rediseño moderno con vectores limpios. El tab
switch base/evol en cada card del módulo se lee como "antes/después"
sin etiqueta explícita.

**Pipeline de ingesta** — `tools/build-arquetipos-medellin/build.py`:
- Python + openpyxl (sin deps externas más allá de openpyxl).
- Lee 3 Excel en `Insumos /` y emite 7 JSONs:
  - `arquetipos.json` (6 KB) — definición canónica 5×2
  - `por-barrio.json` (430 KB) — master keyed por DAP
  - `por-comuna.json` (20 KB) — agregado 21 comunas × 4 años
  - `proyeccion-2027-resumen.json` (3 KB) — KPI ciudad
  - `correlaciones-top.json` (55 KB) — top 50 trías por año
  - `transiciones.json` (12 KB) — matrices 6×6 + trayectorias
  - `metodologia.json` (4 KB) — texto fuente para footer
- Round a 4 decimales para JSON compacto.
- 152 barrios validados contra GeoJSON oficial al final del run.

**Outputs en S3** (todos públicos, bajo `ricardoruiz.co/bases+de+datos/Proyecto+DC/`):
```
arquetipos/arquetipos.json
arquetipos/por-barrio.json
arquetipos/por-comuna.json
arquetipos/proyeccion-2027-resumen.json
arquetipos/correlaciones-top.json
arquetipos/transiciones.json
arquetipos/metodologia.json
arquetipos/escudos/{proteccion-orden,proteccion-resultados,
                    estabilidad-continuidad,continuidad-gestion,
                    supervivencia-basicos,supervivencia-cotidianos,
                    desconfianza-castigo,castigo-restauracion,
                    pertenencia-dignidad,pertenencia-comunitaria}.jpg
arquetipos/cartografia/slide_{01..10}.png
pdfs/cartografia_emocional_medellin_2015_2023.pptx (16 MB)
```

**Gotcha del bucket** (aprendido en este módulo): las URLs públicas
usan `Proyecto+DC/` (donde `+` decodifica a espacio), pero las keys
reales del bucket son `Proyecto DC/` con **espacio literal**. Si subís
con `aws s3 cp` y pasás `Proyecto+DC/` la CLI lo interpreta como
literal `+` → crea una key paralela que la bucket policy NO cubre y
queda 403 anonymous. **Subir siempre con espacio en la key**:
`aws s3 cp ... "s3://elecciones-2026/ricardoruiz.co/bases de datos/Proyecto DC/..."`.
La política del bucket ya cubre todo `bases de datos/Proyecto DC/*`
(con espacio); el frontend usa `+` en la URL y S3 decodifica al
servir.

**Módulo frontend** — `proyecto-dc/arquetipos.html`:
- Chasis privado idéntico a `gobierno-criminal.html` (gate por
  whitelist + `noindex,nofollow` + cursor morado + theme auto).
- Layout 2 col: mapa Leaflet (BARRIOS_OFICIAL.json) + panel ficha.
- Toggle año 2015/2019/2023/Proyección 2027 + toggle nivel barrio/comuna.
- Click barrio → ficha completa: escudo, scores 0–1 de 5 familias,
  trayectoria 2015→2027 con probabilidades 2027, ganadores
  Alcaldía/Concejo/JAL, correlaciones triádicas (firmadas + nivel),
  contexto territorial, comportamiento probable 2027.
- Click comuna → zoom a barrios de esa comuna + ficha de distribución
  por arquetipo + evolución 4 años.
- Vista comuna: GeoJSON Ciudades-COM-LOC/MEDELLINX.json (compartido
  con voto-historico).
- Secciones: 5 arquetipos con tab base/evol · trayectorias (85 cambio
  parcial / 45 volátiles / 13 estables + top 12 patrones) · proyección
  2027 (5 bolsas) · top correlaciones triádicas por año · 6 slides
  seleccionadas del PPTX inline.

**Cuando agregar más datos:**
- Re-correr `build.py` sobre los Excel actualizados → 7 JSONs nuevos.
- `aws s3 cp Bases\ de\ datos/proyecto-dc/arquetipos/ "s3://elecciones-2026/ricardoruiz.co/bases de datos/Proyecto DC/arquetipos/" --recursive --exclude "escudos/*" --exclude "cartografia/*"`
- Safari cachea JSON agresivo: si actualizás, considerar bumpear un
  query string `?v=YYYYMMDD` en `URL.*` dentro del HTML (patrón
  `oportunidad.html`). Hoy no hace falta porque el módulo es nuevo.

### Módulo 07 — agenda pública (saliencia mediática)

Pipeline de scraping de medios + agregador + frontend interactivo. Todo
en infraestructura propia (Lambda + S3 + EventBridge), sin servicios
pagos. Costo real <$1/mes (cabe en free tier salvo S3 storage marginal).

**Arquitectura**:
```
EventBridge (rate 30min) ─▶ Lambda agenda-medios-rss
   ├─ fetch paralelo 10 RSS (ThreadPoolExecutor, ~5s)
   ├─ User-Agent tipo Chrome (evita fingerprinting)
   ├─ HTTP_TIMEOUT=15s, dedup por hash24 de url canónica
   └─ S3: raw/medios/yyyy=Y/mm=M/dd=D/{medio}__{run_id}.jsonl
                                                  │
EventBridge (rate 1h) ──▶ Lambda agenda-medios-aggregator
   ├─ lista 6 días de raw/medios/, lee y dedupea por id
   ├─ filtra por ventana (6h / 24h / 5d) según fecha_pub
   ├─ tokeniza título (peso 2x) + resumen (1x)
   ├─ strip URLs (regex http/https/www) antes de tokenizar
   ├─ filtra stopwords ES + reporting verbs + ruido geo + ruido URL
   └─ S3: agregados/{nube,medios,titulares}-{6h,24h,5d}.json
                                                  │
proyecto-dc/agenda.html ◀──── fetch directo a S3 (cache 5min)
   ├─ toggle ventana 6h | 24h | 5d
   ├─ nube top-50 con tooltip ::after (data-count)
   ├─ click-filtro: titulares con regex word-boundary ES
   ├─ chip "Filtrando por X ×"
   └─ tipografía: Fraunces serif + Arima sans (no DM Mono)
```

**Layout S3** (bajo `ricardoruiz.co/proyecto-dc/agenda/`):
- `state/medios.json` — privado, dedup state del RSS reader (lista de IDs vistos por medio, cap MAX_SEEN_PER_FEED=600)
- `raw/medios/yyyy=YYYY/mm=MM/dd=DD/{medio}__{run_id}.jsonl` — privado
- `agregados/{nube,medios,titulares}-{6h,24h,5d}.json` — **público** vía bucket policy

**Retención e histórico (verificado 2026-06-15):**
- **`raw/medios/` + `enriched/` se ACUMULAN** con `run_id` (timestamp) en la key →
  nada las borra, no hay lifecycle policy. Al 2026-06-15: **7.064 archivos en
  `raw/medios/`, del 30-abr-2026 a hoy, día por día** (particiones Hive `yyyy=/mm=/dd=`).
  Cada evento trae `titulo`, `resumen`, `fecha_pub`. **Hay que conservar esto** —
  es el insumo para estudios futuros de saliencia/agenda.
- **`agregados/` y las `recomendaciones-*` se SOBRESCRIBEN** (key fija): solo
  sobrevive la última ventana 6h/24h/5d y la última recomendación de cada arquetipo.
  **No hay histórico de recomendaciones ni de titulares agregados** — la lectura
  táctica de DeepSeek de una corrida se pierde en la siguiente (cada 6h).
- **PENDIENTE · ver titulares de fechas pasadas:** hoy NO hay forma de consultarlos
  (el frontend solo lee los agregados rolling). El dato existe en `raw/`/`enriched/`.
  Para estudios futuros: (a) script Python que lea `raw/` por fecha/rango → CSV/MD,
  o (b) vista con calendario en `agenda.html` (requiere agregador que lea fechas
  arbitrarias), o (c) Athena sobre `raw/` (ya particionado Hive). **NO es entregable
  para Carvalho** — es para investigación interna. No construido aún.

**Esquema del evento** (jsonl raw):
```json
{
  "id": "hash24 url canónica", "medio": "minuto30", "fuente": "rss",
  "url": "...", "url_canonica": "...",
  "titulo": "...", "resumen": "texto plano sin tags",
  "fecha_pub": "ISO 8601 con tz",
  "fecha_capturada": "ISO 8601 UTC",
  "autor": "...|null", "categorias": ["..."],
  "raw_id": "guid del feed", "run_id": "YYYYMMDDTHHMMSSZ"
}
```

**IAM** — un solo role `lambda-agenda-medios-rss` reusado por ambas Lambdas:
- `s3:GetObject`, `s3:PutObject` sobre `proyecto-dc/agenda/*`
- `s3:ListBucket` sobre el bucket con condition `s3:prefix` que matchea el mismo prefijo (necesario para que GetObject de archivo inexistente devuelva NoSuchKey en vez de AccessDenied)
- `AWSLambdaBasicExecutionRole` para CloudWatch logs

**Medios — bloque A (RSS, los 10 desplegados)**:
| medio | feed |
|---|---|
| minuto30 | https://www.minuto30.com/feed/ |
| telemedellin | https://telemedellin.tv/feed/ |
| eltiempo-medellin | https://www.eltiempo.com/rss/colombia_medellin.xml |
| vivirenelpoblado | https://vivirenelpoblado.com/feed/ |
| mioriente | https://www.mioriente.com/feed |
| hacemosmemoria | https://hacemosmemoria.org/feed/ |
| periferia | https://periferiaprensa.com/feed/ |
| las2orillas | https://www.las2orillas.co/feed/ |
| delaurbe | https://delaurbe.udea.edu.co/feed/ |
| centropolis | https://www.centropolismedellin.com/feed/ |

> **Centrópolis** es intermitente desde us-east-1 (TLS handshake timeout
> ocasional, hosting compartido lento). Como el RSS no es incremental,
> entra cuando alcanza a responder. Si después de varios días sigue sin
> dar señales, considerar moverlo a fallback HTML scraping.

**Medios pendientes — bloque B (sitemap, ~1 Lambda)**:
- El Colombiano — sitemap.xml (557+ URLs con lastmod)
- Blu Radio — sitemap-latest.xml
- Pulzo — sitemap.xml index → sub-sitemap mensual
- Q'Hubo Medellín — sitemap.xml (limitado, ~40 URLs de secciones)

**Medios pendientes — bloque C (HTML scraping, 1 Lambda por medio)**:
- Caracol Radio Medellín (bloqueado vía WebFetch, requiere UA rotation)
- RCN Radio Medellín
- La FM
- Semana (filtrar por keyword Medellín/Antioquia)
- ADN Colombia
- Teleantioquia (SPA — requiere puppeteer-core en Lambda layer)

**Stopwords y filtros** (`tools/agenda-medios-aggregator/stopwords-es.txt`):
- Artículos, preposiciones, pronombres, demostrativos, cuantificadores
- Auxiliares (ser, estar, haber, tener, poder, deber, hacer, ir, decir, ver, saber)
- Verbos de noticia (afirma/afirmó/afirman, asegura, indica, declara,
  sostiene, expresa, manifiesta, señala, revela, confirma, explica,
  agrega, añade, anuncia, denuncia, advierte, alerta, informa, publica…)
- Tiempo / fechas (días de la semana, meses, año/mes/día)
- Numerales escritos
- Ruido geográfico (medellín, antioquia, colombia y variantes)
- Ruido de URLs (https, http, webp, jpeg, jpg, www, com, html, content,
  wp-content, uploads, staticprd) — y `URL_RE` strip antes de tokenizar
- `MIN_WORD_LEN=4` filtra palabras de ≤3 chars

**Reglas de despliegue del módulo 07**:
- Ambas Lambdas: Python 3.14, x86_64, runtime stdlib + boto3 (sin deps externos).
- Memoria: RSS reader 256 MB, aggregator 512 MB.
- Timeout: RSS 1 min, aggregator 2 min.
- Handler: `lambda_handler.handler`.
- ZIP de deploy: bundle plano (`zip -j`) con `lambda_handler.py` + config (`feeds.json` o `stopwords-es.txt`). No requiere `pip install`.
- Para añadir medios al bloque A: editar `tools/agenda-medios-rss/feeds.json`, rebuild, re-upload. La dedup state.json maneja IDs nuevos sin tocar nada más.
- Para refinar stopwords: editar `tools/agenda-medios-aggregator/stopwords-es.txt`, rebuild, re-upload. La próxima corrida del agregador (cada hora) reescribe los JSONs.

### Cosas a no perder
- Los nombres de bandas (La Oficina, Los Triana, Pachelly, La Agonía, Los
  Pesebreros) sí se muestran tal cual en módulo 06, con disclaimer en el
  banner amarillo: "no es señalamiento judicial, prueba penal ni
  cartografía oficial". Reproducen lenguaje de fuentes citadas en el
  informe original de la socia.
- Los GeoJSON de Medellín (`MEDELLINX.json`) tienen 23 features: 16
  comunas (CODIGO 01-16) + 5 corregimientos (50/60/70/80/90) + 2 SN.
  Los corregimientos NO están en el análisis de comportamiento electoral
  ni de gobierno criminal — se pintan en gris con tooltip "No incluido en
  este análisis".

## Test Presidencial 2026 — `test-presidencial-2026.html` (v1 LISTO · B2C/B2B híbrido)

Test de **arquetipo emocional del votante** que contrasta el candidato
declarado del usuario con su perfil emocional y, próximamente, con la
huella territorial del bloque del candidato en su barrio/municipio.

### Arquetipos (5 + 5 variantes evolucionadas)

Adoptados del paquete de Nury Astrid (mismo modelo usado en módulo 05
de proyecto-dc · Cartografía Emocional 2015-2027):

| ID | Nombre 2027 (mostrado al usuario) | Color hex | Marco teórico |
|---|---|---|---|
| `proteccion` | Protección con resultados y orden competente | #1e6fb8 | Securitization (Buzan & Wæver) + RWA (Altemeyer) |
| `estabilidad` | Continuidad pragmática y gestión barrial | #2f6b3f | System Justification (Jost) + Loss Aversion (Kahneman) |
| `supervivencia` | Supervivencia económica y servicios cotidianos | #c9682e | Economic Voting (Lewis-Beck) + Pocketbook (Achen & Bartels) |
| `castigo` | Castigo a la restauración y demanda de alternancia | #a02020 | Affective Intelligence (Marcus) + Negativity Bias |
| `pertenencia` | Pertenencia comunitaria y autonomía territorial | #7a3b8f | Social Identity (Tajfel & Turner) + Politics of Resentment (Cramer) |

### Candidatos (6 del set de `oportunidad.html`)

```
ic — Iván Cepeda          (Pacto Histórico)          #51458F
ae — Abelardo De la Espriella (Independiente)        #000062
pv — Paloma Valencia      (Centro Democrático)       #1866DF
cl — Claudia López        (Centro/Centroizquierda)   #d9db24
sf — Sergio Fajardo       (Coalición de Centro)      #EEAA22
rb — Roy Barreras         (Frente por la Vida)       #3d8b3d
```
Fotos en S3: `bases+de+datos/fotos-candidatos-ctr/{cepeda,abelardo,paloma,claudia,fajardo,roy}.jpg`
(set propio del test; `kart-presidencial1v.html` fue eliminado del repo y
`combate-electoral.html` usa sus propios PNG en `combate-electoral/candidatos/`).

### Flujo del usuario (6 pasos)

1. **Registro** (popular · digital · analítico) — cambia el tono del texto.
2. **Candidato declarado** (6 cards con foto) o `Aún no me decido` → mini-test
   de 4 preguntas con scoring sobre los 6 candidatos.
3. **Demografía** (2 preguntas, no scoring): edad (5 rangos) + identidad
   cotidiana (7 opciones: trabajo, barrio, familia, ciudad, gremio,
   comunidad, región).
4. **Ubicación** — botón geo (Nominatim reverse + nearest-neighbor sobre
   13.506 puestos de PUESTOS_GEOREF para resolver barrio) + dropdowns
   dep→mun como fallback. Identifica barrio, comuna, mun, dep, y calcula
   `tono_regional` (voseo paisa / voseo caleño / ustedeo boyacense /
   tuteo costeño / tuteo neutro).
5. **PRIO** (prioridad temática, multi-respuesta hasta 2 de 10 temas:
   seguridad, economía, salud, costo de vida, anticorrupción, política
   exterior, agraria, instituciones, educación, ambiente). Calibra
   cuál variante temática se muestra en P1/P2/P3/P4/P6.
6. **7 preguntas de arquetipo + 1 de balance Petro (P8)**. Opciones
   barajadas con Fisher-Yates. Cada opción cambia según candidato +
   registro elegido.

### Banco de preguntas (1.268 textos)

- 720 mainstream (8 preguntas × 5 opciones × 6 candidatos × 3 registros)
- 450 variantes temáticas (5 preguntas con variante × 5 × 6 × 3)
- 33 PRIO (10 temas × 3 registros + 3 enunciados)
- 18 demografía (edad + identidad × 3)
- 32 mini-test (4 preguntas × scoring × 6 candidatos)
- P6 con casos reales: UNGRD, Odebrecht, Centros Poblados, Nicolás Petro,
  OCAD-Paz, Agro Ingreso Seguro — distribuidos según el lente del candidato.
- Pertenencia diversificada por candidato (no más sesgo región-vs-Bogotá):
  · ic → comunidades populares, sindicatos
  · ae → pequeño empresariado, gente del común
  · pv → gremios productivos, sectores que sostienen al país
  · cl → ciudades capitales, profesionales urbanos, localidades
  · sf → clase media educada, profesionales, maestros
  · rb → regiones del posconflicto, víctimas

### Datos del banco — paths S3

```
S3_BASE = ricardoruiz.co/congreso-2026/output/test-presidencial/
  arquetipos.json           5 arquetipos con marco teórico + color
  candidatos.json           6 candidatos con lente, tono_propio, foto
  registros.json            3 registros con tono_redaccion
  mini_test.json            4 preguntas con scoring por candidato
  preguntas.json            8 preguntas + 5 opciones × 6 cand × 3 reg
                            + sección demografia (edad + identidad)
                            + sección prioridad_tematica (10 temas)
  variantes-tematicas.json  5 variantes (salud, costo_vida, agraria,
                            exterior, instituciones) × 5 × 6 × 3
  divipola.json             34 deptos + 1.189 muns (cód. Registraduría)
  puestos-light.json        13.506 puestos con lat/lon + barrio + comuna
```

Ediciones manuales del banco: `Bases de datos/test-presidencial/banco-preguntas-v1.xlsx`
(12 hojas, gitignored). Script `tools/build-banco-preguntas/json_to_xlsx.py`
exporta JSON → Excel. Script inverso (`xlsx_to_json.py`) pendiente.

### Lambda DeepSeek — `tools/test-presidencial-explica/`

- **Función:** `test-presidencial-explica` en us-east-1.
- **Endpoint:** `https://9w1xcwe2sj.execute-api.us-east-1.amazonaws.com/explica`
  (POST con CORS abierto, OPTIONS preflight 204).
- **Modelo:** `deepseek-v4-flash` (DEEPSEEK_MODEL env var). API key
  compartida con `agenda-medios-recomienda` y `agenda-medios-enrich`.
- **HTTP_TIMEOUT 55s · Lambda timeout 60s** (V4 con reasoning largo
  puede llegar a 30s en cold call). max_tokens 4000.
- **Cache S3:** `ricardoruiz.co/test-presidencial-2026/cache/{hash24}.json`
  con TTL 14 días. Key incluye registro + candidato + edad + identidad
  + tono_regional + dep_cod + prio (sorted) + arq_dom + arq_sec.
- **Tono regional** controlado por `TONO_REGIONAL` dict en
  `lambda_handler.py`. El system prompt obliga a usar el tono regional
  del usuario (voseo paisa para Antioquia/Eje Cafetero, voseo caleño
  para Valle, ustedeo formal para Boyacá, tuteo costeño para Caribe,
  tuteo neutro para Bogotá/Santanderes/Llanos/Sur). Prohibe explícitamente
  voseo argentino y "che".
- **Output del LLM:** JSON estricto con `lectura` (2 párrafos de 70-90
  palabras), `mensaje_corto` (12-18 palabras para meme/redes), `alineacion`
  (alineado/vientos_cruzados/neutro).
- **Tiempos:** ~10-12s warm, ~25-30s cold start, ~1-3s cache hit.
- **Costo:** ~$0.00015 USD por test (V4 Flash). Con cache razonable a
  ~$5-15 USD por cada 100.000 tests.

IAM role `lambda-test-presidencial-explica`:
- `AWSLambdaBasicExecutionRole` (CloudWatch logs)
- Inline `s3-cache` (Get/Put sobre `cache/*`)

Usuario IAM `ricardo-mac-cli` tiene:
- `elecciones-2026-rw` (S3 sobre el bucket)
- `AWSLambda_FullAccess` (gestión Lambda)
- `AmazonAPIGatewayAdministrator` (API Gateway)
- `test-presidencial-deploy` inline (PassRole + Logs + roles `lambda-*`)

### Frontend (`test-presidencial-2026.html`)

Funcionalidades visuales:
- Cursor custom azul (`var(--blue)`).
- Cards de candidatos con foto circular + iniciales fallback.
- Hero del arquetipo dominante con color hex del arquetipo.
- Loader animado durante la espera de DeepSeek: 5 mensajes que rotan
  cada 2.2s + barra de progreso indeterminada con animación CSS.
- Shuffle Fisher-Yates de opciones, memoizado por pregunta
  (`STATE._shuffled`).
- Variante temática activa según PRIO: el tag de la pregunta muestra
  "Tema · Subtema" cuando se activa.
- **Distribución de arquetipos** se guarda en el STATE y se envía a la
  Lambda como `arq_score`, pero **NO se muestra al usuario**. Es señal
  interna que se almacena en el cache de S3 para análisis posterior.

Estado del usuario:
```js
STATE = {
  registro, candidato, candOrigen,
  mtAnswers, mtIndex,
  demo: { edad, identidad },
  ubicacion: { dep_cod, dep_nombre, mun_cod, mun_nombre, barrio, comuna,
               cod_puesto, fuente, lat, lon, tono_regional },
  prio: [tema1, tema2],
  answers: { P1, P2, ..., P8 },
  arqScore: { proteccion, estabilidad, supervivencia, castigo, pertenencia }
}
// window.STATE y window.DATA están expuestos a propósito para debugging.
// DATA se llena con Object.assign(DATA, {...}) — NO reasignar a literal.
```

### Pantalla final del test (2 sub-vistas + pre-fetch)

El `#panel-result` se divide en dos sub-vistas dentro del mismo panel:

**Sub-vista A — `#result-summary`** (visible al terminar las 8 preguntas):
- `arq-hero` con el arquetipo dominante (color del arquetipo de fondo).
- `cand-block` con la apuesta declarada (foto + nombre + partido).
- `barrio-block` con el gráfico **"Cómo se inclinaría tu zona"** — 6 barras
  horizontales con `pondPct_nac × bias_local` renormalizado a 100%. La
  barra del candidato declarado lleva la clase `.mine` (negrita + bullet).
- Pie del bloque con 3 hechos crudos del territorio (top 2022, top
  consulta Pacto 2025, consulta 2026 ganadora).
- Botón CTA `#btn-ver-lectura` (clase `.btn-primary`, azul fuerte).
  Empieza disabled, se habilita cuando la lectura llega.
- `#cta-status` con estado del pre-fetch: "Preparando…" → "Listo. Toca
  el botón." (clase `.ready`) o error.

**Sub-vista B — `#result-lectura`** (oculta hasta el click):
- `.ai-message` con la lectura personalizada (2 párrafos + frase final).
- Si la lectura llega antes del click: renderiza al click (instantáneo).
- Si el usuario clickea antes: muestra el loader de 5 frases rotando.
- Si falla: cae al texto fallback (sin DeepSeek).

**Pre-fetch en paralelo** (clave del UX): `renderResultado()` dispara
`iniciarPrefetchLectura()` inmediatamente al pintar la sub-vista A.
DeepSeek toma 10-15s warm; mientras tanto el usuario ve candidato +
arquetipo + gráfico de barrio (mucho contenido para leer). Al click del
botón, la lectura **suele estar ya cacheada** en `_lecturaData`.

El `result-tag` cambia: "Resultado" en A → "Análisis" en B.

### Huella territorial — pipeline + integración

Pipeline en `tools/build-huella-territorial/build.py` (Python, una
corrida ~3 minutos):
- Lookup directo desde `PUESTOS_GEOREF.csv` (columna `BARRIO` poblada al
  100% en los 13.508 puestos del país — sin necesidad de polígonos).
- Cruza 9 señales electorales: 5 GCS crudos (`GCS_2010/14/18/22PRES1V`,
  `GCS_2025CONSU` Pacto) + 4 desde S3 (`consulta-2026-gran/frente/soluciones`
  como `por-puesto.json` con wrapper `{puestos: {...}}`, y `senado-2026`
  por depto).
- Cascada de matching: **A** exacto `(DD,MMM,ZZ,PP)` (87-99% según
  señal), **B** por zona `(DD,MMM,ZZ)` → barrio modal, **C** solo
  municipio. Sin descarte.
- Aplica la fórmula del ponderador con las `EQUIVALENCIAS` de
  `previa-1v.html` (líneas 1636-1685, copiadas literalmente al script):
  `bias_c(M) = afín_local(c,M) / afín_nacional(c)`. 1.0 = neutral.
- Output: `huella-territorial.json` (~1.27 MB · 2.506 barrios + 1.122
  muns) en
  `s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/huella/`
  (prefijo público bajo la bucket policy ya existente).

**Ciudades con desagregación por barrio** (27, definidas en
`CIUDADES_BARRIO` del script): Bogotá, Medellín, Cali, Barranquilla,
Cartagena, Ibagué, Montería, Villavicencio, Manizales, Cúcuta,
Bucaramanga, Pereira, Pasto, Santa Marta, Popayán, Valledupar,
Riohacha, Neiva, Armenia, Palmira, Buenaventura, Barrancabermeja, Tuluá,
Bello, Soledad, Soacha, Tumaco. El resto del país queda a nivel
municipio.

Shape (keys cortas):
```jsonc
{
  "v": "2026-05-18", "cands": ["ic","ae","pv","sf","cl","rb"],
  "afin_nac": { "ic": 0.395, "ae": 0.256, ... },
  "barrios": {
    "medellin::comuna-11-laureles::laureles": {
      "n": "LAURELES", "ciudad":"Medellín", "subloc":"COMUNA 11 LAURELES",
      "mun":"01-001", "dep":"ANTIOQUIA", "puestos":3, "censo":30824,
      "b": { "ic":0.79, "ae":1.50, "pv":1.77, "sf":0.99, "cl":1.04, "rb":0.88 },
      "h": {
        "p22":  { "n":"FEDERICO GUTIERREZ", "pct":66.0 },
        "c25p": { "n":"IVAN CEPEDA CASTRO", "pct":66.2 },
        "c26":  "gran",  // gran|frente|soluciones
        "s26":  { "n":"PARTIDO CENTRO DEMOCRATICO", "pct":53.2 }
      }
    }
  },
  "muns": { "01-151": { "n":"ITAGUI", "dep":"ANTIOQUIA", "puestos":18,
                        "censo":24500, "b":{...}, "h":{...} } }
}
```

**Lambda integración** (`tools/test-presidencial-explica/lambda_handler.py`):
- `_load_huella()` con cache por contenedor warm. Lee de S3 vía IAM.
- `_resolver_huella(ubi)` cascada: barrio (match por slug del barrio +
  comuna como tiebreaker) → mun → None.
- `_format_huella_block(entry, level, candidato_id)` arma bloque de
  texto que se appendea al `user_msg`. Incluye: ubicación, censo, top
  2022, top consulta Pacto 2025, consulta 2026 ganadora, top partido
  senado 2026, **6 bias por candidato** (1 marcado como `← CANDIDATO
  DECLARADO`), y una interpretación textual del bias del declarado
  (MÁS afín / MENOS afín / neutro).
- Regla 6 al SYSTEM_PROMPT: el modelo usa la huella como evidencia
  objetiva, no inventa nada.
- `_cache_key` incluye `mun_cod` + `barrio` (slug) para que dos usuarios
  de barrios distintos no compartan respuesta cacheada.
- `max_tokens` subido a **8000** (era 4000): V4 con bloque de huella
  agotaba todo en reasoning_tokens y dejaba `content` vacío con
  `finish_reason=length`.

**IAM** — `lambda-test-presidencial-explica` inline policy `s3-cache`:
- `Get/PutObject` sobre `ricardoruiz.co/test-presidencial-2026/cache/*`
- `GetObject` sobre `ricardoruiz.co/congreso-2026/output/huella/*`

**Frontend integración** (`test-presidencial-2026.html`):
- `HUELLA_URL` apunta al mismo prefijo público. **Precarga en
  `ubiNext()`** (apenas el user sale de la pantalla de ubicación), así
  durante los 30s de las 8 preguntas se descarga (1.27 MB con gzip
  ~250 KB).
- `cargarHuella()` lazy con `_huellaCache` / `_huellaPromise` para no
  duplicar fetches.
- `resolverHuella(huella)` espejo del de la Lambda (slug barrio + comuna
  tiebreaker → fallback mun).
- `calcularIntencionBarrio(entry)` = `POND_NAC × bias` renormalizado.
  `POND_NAC` está hardcoded al inicio del script y debe sincronizarse
  con `previa-1v.html` si el ponderador cambia.
- `renderIntencionBarrio(cand)` pinta las 6 barras animadas (delay 60ms
  para que el width:0→pct anime) + footnote de hechos.

**Cómo regenerar la huella**:
```bash
python3 tools/build-huella-territorial/build.py
# → escribe Bases de datos/output_huella/huella-territorial.json (~3 min)

aws s3 cp "Bases de datos/output_huella/huella-territorial.json" \
  "s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/huella/huella-territorial.json" \
  --content-type "application/json" --cache-control "public, max-age=300"
```
Cache S3 del frontend dura 5 min — si necesitas invalidar antes,
bumpear un `?v=YYYYMMDD` en `HUELLA_URL`.

### Estado al 2026-05-20 (snapshot de handoff)

Calendario en marcha: **1ª vuelta el 31 de mayo de 2026**, 2ª vuelta el
21 de junio. El módulo cubre **solo 1ª vuelta**; la 2ª sería un módulo
aparte (decisión de Ricardo).

**En producción (todo desplegado y verificado):**

- **Pantalla welcome inicial** — único panel al abrir el test.
  Título *"¿De qué te sirve votar por **tu candidato** en tu barrio o
  vereda?"*, subtítulo expandido (qué le beneficia + proyecciones +
  qué propone su candidato), hint con cita a la **Ley 1581 de 2012**
  (habeas data, +20% de tamaño), botón "Empecemos →". Se eliminó el
  `.head-wrap` global; los pasos siguientes traen su propio header de
  paso. Aplica a formato general y embed.
- **Pregunta de registro renombrada**: *"¿Cómo te sientes más cómodo
  respondiendo? Escoge un modelo."*
- **Embed El País Cali** (`?embed=1&brand=elpais&territorio=valle`):
  paleta El País (Lato, azul `#0067b1`, esquinas a 2px), barra de marca
  full-bleed con **logo oficial de El País centrado** + "POWERED BY ·
  Ricardo.Ruiz" a la derecha (mismo lockup del header del test normal).
  Logo a 80 px desktop / stack vertical en móvil ≤640 px.
  Logo en S3: `…/test-presidencial/brand/elpais-logo.png`.
- **Programa real del candidato** inyectado al prompt de DeepSeek según
  prioridades del usuario. JSON destilado de los 10 PDFs oficiales
  (`Bases de datos/programas_candidatos/`) → 6 candidatos cubiertos,
  Miguel Uribe sobra. Roy solo tiene 4 sectoriales (declarado en `nota`).
  Pipeline: `tools/build-apoyo-reco/build.py` parsea
  `apoyo-recomendaciones.txt` y regenera el JSON; mismo patrón con
  `programas-candidatos.json`. Validado: el bloque de Abelardo línea
  por línea contra el PDF — 100% fiel, cero invención.
- **Lectura DeepSeek (v4 del prompt)**: NO nombra el arquetipo ni da
  porcentajes; explica el perfil en lenguaje natural. NO cita cifras
  electorales crudas; usa veredicto cualitativo (*"le va muy bien /
  bien / regular / la tiene difícil"*) + **% proyectado** en su barrio
  (`POND_NAC × bias` renormalizado). Aterriza una propuesta al nombre
  del barrio + censo (microdato real), **sin inventar rasgos** del
  territorio (regla 7, prohibido inventar "inseguridad/pobreza" no
  declaradas). `PROMPT_VERSION` versionado para invalidar cache al
  cambiar el prompt.
- **Adherencia de tono determinista** — `_voseo_a_tuteo()` con
  diccionario CERRADO (formas voseo presente con tilde + vos/sos)
  aplicado solo si tono ∈ {tuteo_neutro, tuteo_costeño}. No depende del
  modelo, sin falsos positivos.
- **Persistencia + dashboard live**:
  · `_emit_event` escribe un evento anónimo por completación a
    `responses/yyyy=Y/mm=M/dd=D/{ts}_{uuid}.json` (sin PII).
  · Lambda agregadora (`test-presidencial-dashboard-agg`) con
    **EventBridge cada 5 min** → `aggregates.json` (resumen liviano)
    y `aggregates-geo.json` (todos los deptos y muns) en prefijo
    público `congreso-2026/output/test-presidencial/dashboard/`.
  · `dashboard-general.html` — selector de scope (todo/medio/territorio)
    + KPIs + cruce candidato×arquetipo + top municipios + serie diaria
    + stream + **mapa Colombia lazy** (botón "Ver mapa", carga Leaflet
    + GeoJSON + geo solo al pulsarlo).
  · `elpais-cali-dashboard.html` consume el mismo `aggregates.json`
    filtrado a `por_brand.elpais` (fallback a `por_territorio.valle`).
- **Botones de compartir** (general + embed): WhatsApp / X / copiar /
  Web Share. Comparten el `mensaje_corto` de DeepSeek.
- **Párrafo de apoyo según posición del candidato en el barrio**
  (template determinista cliente-side, 0 latencia) + **botón "Cómo
  apoyar"** que carga la matriz registro × arquetipo de
  `apoyo-recomendaciones.json` (incluye hashtags por candidato).
- **Opt-in con datos para campaña** (rompe el modelo anónimo solo si el
  user lo autoriza): email + celular + checkbox Ley 1581, va a un store
  S3 separado `opt-in/`. PII aislada del flujo anónimo.

**Latencia DeepSeek:** ~23-26 s cache miss · ~1 s cache hit. Cerca del
límite del API Gateway (30 s); el **pre-fetch** del frontend lo cubre
(la lectura se pide en background mientras el user ve el gráfico del
barrio, ~10-15 s).

**Marco legal verificado (fuente Registraduría + CNE):**
- 1ª vuelta presidencial **31 may 2026**, 2ª vuelta 21 jun 2026.
- Veda general de encuestas: 1 semana antes (último día de publicación
  para 1ª vuelta = 24 may 2026; del 25 al 31, veda).
- **Ley 2494 de 2025** (encuestas electorales) — exige muestra
  probabilística + auditable + registro CNE. El test es audiencia
  autoseleccionada, NO califica como encuesta. Distingue "sondeo" pero
  el disparador es la **publicación** de cualquier estudio cuantitativo
  con propósito electoral. Por eso el tablero se vende como
  **inteligencia editorial INTERNA** (no se activa la ley) y publicar
  cifras al aire queda a criterio de la jurídica del medio.

**Entregable comercial:** `Bases de datos/test-presidencial/elpais-propuesta-test-presidencial.pdf`
— 1.5 páginas, generado con `tools/build-elpais-propuesta/build.py`.
Tono comercial, identidad El País, encuadre legal correcto (test +
inteligencia editorial, NO publicación de sondeo).

### Estado: LISTO (cerrado jul-2026)

Todos los pendientes activos (memes procedurales, revisión del banco de
preguntas, contacto El País Cali, iteración del prompt DeepSeek) quedaron
resueltos o descartados. Módulo cerrado.

### Convenciones del módulo

- **Datos del módulo viven en `Bases de datos/test-presidencial/`**
  (gitignored). Solo el código va al repo. Los JSON/PNG/PDF se suben
  a S3 con `aws s3 cp`. Prefijo público:
  `s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/test-presidencial/`
  (NO `test-presidencial-2026/*`, ese da 403 anónimo).
- **El `.txt` es la fuente de verdad** para listas editables por
  Ricardo (apoyo-recomendaciones, memes-spec). Un script en `tools/`
  parsea el `.txt` y regenera el `.json` con validación dura. Patrón:
  editar `.txt` → `python3 tools/build-…/build.py` → `aws s3 cp`.
- **Cuando actualices la Lambda explica**: zip + `aws lambda
  update-function-code`. Si cambias el SYSTEM_PROMPT, **bumpea
  `PROMPT_VERSION`** (entra al `_cache_key`) para invalidar cache v
  anterior. Cache TTL 14 días.
- **No metas el voseo argentino**. Para tuteo neutro/costeño la red
  determinista `_voseo_a_tuteo` ya lo blinda. Para textos del banco el
  tono regional viene del `tono_regional` del state.
- **El prompt sistémico de la Lambda** está en `tools/test-presidencial-explica/lambda_handler.py`
  buscar `SYSTEM_PROMPT = `. Es corto a propósito — V4 consume reasoning
  con prompts largos. Si lo amplías, mide la latencia después (límite
  blando 30 s por API Gateway).

## Lab de Políticas Públicas y Prospectiva (Sprints A · B · B v2 · C · D · E Fase A · F · F v2 · G · LISTO)

**El hub vive en `analisis-estructural.html`** (mismo archivo, rebrandeado).
**Los 7 módulos del lab están operativos** con cloud-save, copiloto IA
DeepSeek y informe combinado:

| # | Módulo | Archivo | Sprints | What-if / extras |
|---|---|---|---|---|
| 1 | Problema público | `problema-publico.html` | A · 3 IA · cloud · Excel + PDF | — |
| 2 | Análisis estructural | `analisis-estructural.html` (también es el hub) | A · 5 IA · cloud · panel municipal con sparkline 2018-2024 | **slider what-if motricidad** (Sprint F.B.1) |
| 3 | Análisis de actores | `mactor.html` | A · 3 IA · cloud · 4 plantillas seed | **slider what-if Ri** (Sprint F.B.2) |
| 4 | Evaluación de política | `evaluacion.html` | B + **B v2** (literatura 2020-2026 · 14 métodos · TWFE warning · Sinergia DNP · 3 calculadoras económicas CBA/MVPF/CEA · Pre-Analysis Plan AEA RCT exportable) · 3 IA · cloud | — |
| 5 | Alternativas de política | `alternativas.html` | C · 4 IA · cloud · Excel + CSV + CONPES PDF · envío bidireccional a pp · envío a AIN | **Monte Carlo estocástico 500-5000 sims** (Sprint F.C.1) |
| 6 | Análisis de Impacto Normativo | `ain.html` | D · 3 IA · cloud · memo CONPES regulatorio · auto-import pp/alt · envío a evaluación | — |
| 7 | Escenarios prospectivos | `prospect-escenarios.html` | F (módulo nuevo · 4 mecánicas · 3 exports) + **F v2** (cloud + 2 IA copiloto + integración informe combinado) | — |

**Cierre del lab** (no es un módulo más, son herramientas transversales):
- **Sprint G — Informe combinado** en `lab-informe.js` (~720 líneas): lee
  los 7 localStorage keys del usuario y genera un PDF/MD único con 9
  secciones que une diagnóstico + sistema + actores + alternativas + AIN
  + evaluación + escenarios prospectivos + próximos pasos. Punto de
  entrada en `stage-hub` de `analisis-estructural.html` ("Mi informe
  del lab" con anchor `#informe`). Cliente-side jsPDF on-demand.
- **Sprint E Fase A — Indicadores municipales** en `lab-indicadores.js`
  (~270 líneas) + JSON ~980 KB en S3: 8 indicadores oficiales (Policía
  Nacional + MEN) × 1.108 municipios × panel temporal 2018-2024.
  Integrado en `analisis-estructural` (sparkline SVG), `problema-publico`
  (botón "Cargar evidencia oficial"), `ain` (grid de cifras
  territoriales) y `evaluacion` (chip ✦ Autocompletar línea base).

**Worker rr-auth** (`/Users/ricardoruiz/rr-auth/src/index.js`): 49
endpoints, 7 por prefijo × 7 módulos del lab (micmac · mactor · pp ·
ev · alt · ain · prospect) + 21 acciones IA copiloto distribuidas.

Sólo `analisis-estructural.html` figura en el listado de proyectos de
`index.html` (como "Análisis Estructural de Sistemas"). Desde su hub se
llega a los otros 6 módulos. El hub-grid renderiza 7 cards (4+3 en
desktop). Cada módulo tiene cross-links amarillos al informe combinado
del lab (∑) y a los módulos adyacentes en el ciclo.

**Pendiente único del Lab (Sprint E Fase B):** descarga manual de
TerriData / DANE EEVV / MinSalud para añadir 8 indicadores más al
JSON municipal: IPM 2018, NBI 2018, población DIVIPOLA, agua potable,
internet hogares, mortalidad infantil, mortalidad materna, embarazo
adolescente, vacunación PAI. **Checklist operativo detallado en la
sección "Sprint E Fase B · descarga manual pendiente"** más abajo. ~6-8h
de trabajo combinado (3h descarga manual, 2-3h escribir parsers Python,
1-2h validar y subir a S3).

### Hub del lab (`stage-hub` en analisis-estructural.html)

- **Hero** "Para diseñar política pública *con método*" + bajada que
  cita 3 escuelas: francesa de prospectiva (Godet · Mojica · LIPSOR) +
  análisis de políticas (Bardach · UNDP · Ortegón) + evaluación
  (OCDE-DAC · SINERGIA · Ivàlua).
- **Grid de 4 cards** (1/2/4 cols según breakpoint). Cada card tiene
  badge "Recomendado para ti" oculto que se anima cuando el wizard
  entry-point la sugiere. La de "Evaluación" tiene badge "Próximamente".
- **CTA bottom-grid** "Ayúdame a escoger →" abre el wizard
  entry-point de 5 preguntas (`stage-hub-wizard`).
- **Sección colapsable "Recursos & Datos"** al pie con todo el catálogo
  agrupado por las 5 categorías (Sprint A.1, ver abajo).

### Wizard entry-point de 5 preguntas (`stage-hub-wizard`)

5 preguntas binarias/ternarias (pregunta dominante · momento del
proceso · mayor incertidumbre · escala del equipo · entregable
esperado). Cada opción suma 0/1/2 a cada uno de los 4 módulos. Tiebreak
estructural > mactor > problema > evaluacion. Si el ganador es un
módulo `soon`, se highlight el fallback con badge "Empieza por aquí".
Animación: panel "thinking" de 1.8s con frases rotativas → vuelve al
hub → pulse de borde + scroll-into-view + badge salmón.

### Estructura visual común (los 4 módulos)

Heredan el chasis de `dashboard.html`:
- Fuentes: Familjen Grotesk (sans), Petrona italic (énfasis serif),
  Space Mono (técnico), Syne 800 solo en logo.
- Paleta: paper `#1a1610` · accent salmón `#d96a50` (modo noche) o
  paper cream · accent oxblood `#8a1e16` (modo día).
- **Auto día/noche** según hora local (6-19h → día) si no hay
  preferencia en `localStorage.rr-theme`. Patrón clonado de
  `proyeccion-1v.html`. Replicado en los 3 módulos del lab.
- Cursor custom salmón 12px + ring 36px.
- Topbar con btn-back, center label, toggle día/noche, logo y auth chip.

### `analisis-estructural.html` (MicMac + DEMATEL + ISM)

**Etapas (showStage):**
1. `stage-welcome` — título "Entiende lo que mueve tu política pública",
   3 accordions explicativos (qué hace · qué entrega · para qué sirve),
   botón "¿Cómo lo calculamos?" abre `modal-method`, link sutil a Mactor
   al final.
2. `stage-wizard` — 4 preguntas (org · propósito · nivel técnico · dominio).
   Q4 con **16 dominios alineados a ministerios** (4×4 grid, cada uno
   con icono SVG y hint corto). Sugiere plantilla por scoring de overlap
   de tags `{org, proposito, nivel, dominio}`.
3. `stage-vars` — sub-vistas:
   - `vars-intro` con cita a Mojica y 3 reglas prácticas + botón "Empezar módulo".
   - `vars-editor` con grid de chips editables, badge `DATO` salmón en
     chips que matchean un indicador del catálogo, selector de territorio
     (33 deptos + Colombia), barra IA con 2 botones (Pro+).
4. `stage-capture` — captura matriz NxN. Dos modos:
   - Tabla: ciclo extendido `'' → +1 → +2 → +3 → P → −1 → −2 → −3 → 0`.
     Shift+click invierte signo. Tecla `-` también.
   - Guiado: magnitud (0/1/2/3/P) → si magnitud ∈ {1,2,3} aparece
     toggle Facilita/Inhibe. Botón "✦ Pista de IA (Premium)" opt-in
     para sugerencia contextual del par.
   - Selector de confianza global (Alta/Media/Baja → bandas ±0/±0.5/±1).
   - Barra IA "Revisar matriz" (Premium+).
5. `stage-results` — sub-vistas:
   - `results-intro` con explicación de las 3 lentes y botón "Ver resultados".
   - `results-content` con tabs MicMac · DEMATEL · ISM. Las bandas fuzzy
     dibujan cruces de incertidumbre alrededor de cada punto en MicMac
     y DEMATEL. Barra IA "Generar lectura" (Premium+).

**11 plantillas + 8 plantillas por dominio = 19 plantillas totales**
en `TEMPLATES`: pdt-mixto, prospectiva-2040, seguridad-urbana, taller-
actores, academia-blank, movilidad, salud-publica, educacion, economia-
empleo, ambiente-clima, gobernanza, agricultura, vivienda, energia,
cultura, tecnologia, ciencia, justicia, exteriores. Cada una con tags
para el scoring del wizard.

**Catálogo de indicadores embebido (`INDICATORS`):** 16 indicadores
oficiales nacionales 2023-2024 (IPM, homicidios, desempleo, etc.) con
fuente, año, unidad, nota. `matchIndicator(varName)` busca match por
keyword normalizada. Si una variable matchea, su chip muestra badge
`DATO` clickable que abre panel inline con cifra nacional + cifra
departamental (si hay territorio elegido).

**JSON de indicadores departamentales** en S3:
```
s3://elecciones-2026/ricardoruiz.co/bases de datos/analisis-estructural/
  indicadores-depto.json   (5.9 KB · 33 deptos × 5 indicadores · v=20260523)
  metodologia-paso-a-paso.pdf  (16.9 KB)
  respaldo-academico.pdf       (20.8 KB)
```
5 indicadores con dato departamental: ipm, homicidios, desempleo,
pobreza-monetaria, cobertura-media. Pipeline en
`tools/build-indicadores-depto/build.py`. Regenerar con
`python3 tools/build-indicadores-depto/build.py` + `aws s3 cp`. Bump
`?v=YYYYMMDD` en `INDICADORES_DEPTO_URL` si cambian datos.

**Cálculos (todo cliente, sin libs externas):**
- `computeMicMac()` — magnitud absoluta. Eleva matriz hasta estabilizar
  ranking (k ≤ 6). Devuelve motri/dep directos e indirectos +
  cuadrantes (motriz/clave/autonoma/resultado) + bandas si fuzzy.
- `computeDEMATEL()` — preserva signos. `D = M / max(sumRow|M|, sumCol|M|)`,
  `T = D · (I-D)^(-1)` (Gauss-Jordan local). R, C, R+C, R-C +
  cuadrantes (causa/causa-central/efecto-autonomo/efecto-central).
- `computeISM(threshold)` — magnitud absoluta sobre umbral.
  Reachability por Warshall + niveles por intersección Reach∩Antec.

### `mactor.html` (análisis de actores)

**Etapas:**
1. `stage-welcome` — título "Quién apoya, quién bloquea, quién decide".
   3 accordions + botón método + link sutil a analisis-estructural.
2. `stage-wizard` — 1 pregunta (tipo de proceso) sugiere una de **4
   plantillas seed**: reforma-tributaria, reforma-pensional,
   paz-territorial, politica-mde.
3. `stage-actores` — intro + editor de chips. Barra IA "Sugerir actores"
   (Pro+) que devuelve 8-15 actores típicos del contexto colombiano con
   familia conceptual y botón "+ Agregar" por sugerencia.
4. `stage-objetivos` — editor simple de objetivos.
5. `stage-mid` — matriz NxN actor × actor, escala 0-4 (nula · procesos
   · proyectos · misión · existencia).
6. `stage-mao` — matriz N×M actor × objetivo, escala -4..+4 (signo
   captura facilitación vs inhibición). Cloud-bar + barra IA "Revisar
   posiciones" (Premium+).
7. `stage-results` — 3 tabs:
   - Influencia × Dependencia (cuadrantes dominantes / enlace /
     autónomos / dominados, ranking por Ri).
   - Convergencia × Divergencia (cuadrantes coaliciones / conflictivos
     / marginales / opositores, top 6 alianzas y top 6 conflictos por
     pares).
   - Objetivos por movilización con saldo neto ponderado por Ri.
   Cloud-bar + barra IA "Generar lectura" (Premium+) + bloque amarillo
   cross-link a analisis-estructural.

**Cálculos Mactor:**
- `Ii = sum_j MID[i,j]` (influencia directa)
- `Di = sum_j MID[j,i]` (dependencia directa)
- `Ri = Ii / (Ii + Di)` (poder relativo, [0,1])
- `Conv[i,j] = sum_k min(|MAO[i,k]|, |MAO[j,k]|)` si signos iguales
- `Div[i,j]` igual pero signos opuestos
- Movilización objetivo k: `sum_i |MAO[i,k]|`
- Saldo neto k: `sum_i MAO[i,k] · Ri[i]`

**PDFs Mactor en S3:**
```
s3://elecciones-2026/ricardoruiz.co/bases de datos/mactor/
  metodologia-paso-a-paso.pdf  (11 KB)
  respaldo-academico.pdf       (10 KB)
```
Pipeline en `tools/build-mactor-docs/{build_metodologia.py, build_respaldo.py}`.

### `problema-publico.html` (problema público con método)

Módulo de definición y diseño de política basado en el **Eightfold
Path** de Bardach (condensado a 5 mecánicas operativas) + capa
metodológica profunda con wizard de síntoma, test Rittel-Webber +
selector de marco analítico y árbol del problema CEPAL/Ortegón.

**Flow completo:**
```
Welcome → Wizard de síntoma (00) → Definir (01)
                                      ↓
                                  [opcional ↘]
                              Rittel-Webber (01·b) → Marco analítico (01·c)
                                      ↓
                              Evidencia (02) → Alternativas (03)
                              → Criterios (04) → Comparar (05) → Results (06)
```

**6 stages principales + 2 sub-stages opcionales** (todos en `STAGES`
array, navegados por `showStage`):

1. **`stage-welcome`** — 3 accordions explicativos + botón "Empecemos →".
2. **`stage-sintoma`** (A.7.1) — 4 preguntas que arman un draft del
   enunciado en vivo. Pre-rellena `STATE.definicion.enunciado` y
   `STATE.definicion.afectados` si el usuario acepta. Botón "Ya tengo
   el problema claro →" salta.
3. **`stage-definicion`** (mecánica 1) — toggle Formulario / Árbol.
   Formulario: enunciado · magnitud · urgencia (pills) · afectados
   (chips). Árbol (A.7.4): causas raíz arriba + problema central +
   efectos abajo, ≤5 nodos cada lado, editables inline. Botón
   "Profundizar diagnóstico →" lleva al sub-flow Rittel-Webber.
4. **`stage-rittel`** (A.7.2 · opcional) — 10 propiedades canónicas de
   Rittel-Webber (1973) como preguntas SÍ/NO. Score 0-10 con barra
   visual. Clasificación: tame (0-2) · complejo (3-5) · wicked (6-8) ·
   meta-wicked (9-10) en `rittelTipo(score)`.
5. **`stage-marco`** (A.7.3 · opcional) — 4 cards con el marco
   sugerido auto-destacado: racional simple (Bardach·CEPAL) ·
   multi-criterio adaptativo (Walker·Lempert) · participativo
   (Roberts·Head&Alford) · gobernanza colaborativa (Ansell&Gash).
   Se persiste en `STATE.diagnostico.marco` y entra al memo final.
6. **`stage-evidencia`** (mecánica 2) — tabla editable con
   fuente·año·dato·link·nota. Botón "Cargar 3 fuentes típicas"
   (DANE·TerriData·datos.gov.co) como seed.
7. **`stage-alternativas`** (mecánica 3) — 3-5 cards con
   nombre·desc·supuestos·costo·plazo. **Baseline "No hacer nada"**
   primera card fija, no eliminable, renombrable. IA bar Pro+ "Sugerir
   alternativas".
8. **`stage-criterios`** (mecánica 4) — 5 default (eficiencia·
   equidad·factibilidad política·costo·sostenibilidad) con pesos
   0-100 editables (mínimo 2, máximo 8). NO exige sumar 100 (se
   normaliza al calcular). IA bar Premium+ "Revisar criterios".
9. **`stage-comparacion`** (mecánica 5) — matriz alternativas ×
   criterios, cycle on click 1→5. Score = `Σ valor × (peso / Σ pesos)`.
   Ranking visual con barras y winner highlighted.
10. **`stage-results`** — resumen + recomendación + tabla compacta.
    3 botones de descarga: **memo .md**, **Issue Paper Bardach .md**
    (A.7.5), **matriz .csv**. IA bar Premium+ "Generar lectura
    interpretativa". 2 cross-links amarillos a estructural y mactor.

**STATE shape:**
```js
STATE = {
  step: 1,
  sintoma:    { sintoma, quienes, cuando, evidencia },
  diagnostico:{ rittel: [null×10], marco: null|<id> },
  definicion: { enunciado, magnitud, urgencia, afectados[],
                evidenciaInicial, causas[], efectos[] },
  evidencia:    [{ fuente, anyo, dato, link, nota }],
  alternativas: [{ nombre, desc, supuestos, costo, plazo, baseline }],
  criterios:    [{ nombre, peso }],   // 5 default
  scores:       { 'ai-ci': 1..5 }     // celdas matriz
}
```
Persistido en `localStorage['pp-current-v1']`. `loadState()` defensivo
(las sesiones previas siguen funcionando si faltan campos nuevos).

**PDFs Problema Público en S3** (Sprint A.6):
```
s3://elecciones-2026/ricardoruiz.co/bases de datos/pp/
  metodologia-paso-a-paso.pdf  (16 KB · 12 secciones operativas)
  respaldo-academico.pdf       (15 KB · fórmulas + ~25 referencias)
```
Pipeline en `tools/build-pp-docs/{build_metodologia.py, build_respaldo.py}`.
Reportlab, sin más deps. Para regenerar:
```bash
python3 tools/build-pp-docs/build_metodologia.py
python3 tools/build-pp-docs/build_respaldo.py
aws s3 cp "Bases de datos/pp/metodologia-paso-a-paso.pdf" \
  "s3://elecciones-2026/ricardoruiz.co/bases de datos/pp/metodologia-paso-a-paso.pdf" \
  --content-type "application/pdf" --cache-control "public, max-age=300"
aws s3 cp "Bases de datos/pp/respaldo-academico.pdf" \
  "s3://elecciones-2026/ricardoruiz.co/bases de datos/pp/respaldo-academico.pdf" \
  --content-type "application/pdf" --cache-control "public, max-age=300"
```

### `evaluacion.html` (evaluación de política · Sprint B + B v2)

Cuarto módulo del lab. Diseña la evaluación de una política pública
con **ocho decisiones canónicas**, anclado en OCDE-DAC + theory-based
evaluation (Mayne · Pawson) + marco lógico CEPAL/ILPES + Pre-Analysis
Plans (AEA RCT Registry). **B v2 incorpora literatura econométrica
2020-2026** (Callaway-Sant'Anna · Cattaneo · Ben-Michael · Wager-Athey
· Chernozhukov · Mayne 2024 · Hendren) + tipología Sinergia DNP +
3 calculadoras económicas (CBA · MVPF · CEA) + Pre-Analysis Plan
exportable.

**8 mecánicas operativas + welcome + results:**

1. **`stage-pregunta`** — selector de tipo de pregunta (descripción ·
   atribución causal · valor · proceso · gestión) + alcance temporal
   (ex-ante · concurrente · ex-post · meta-evaluación) + **tipología
   Sinergia DNP** (ejecutiva · operaciones · resultados · impacto ·
   institucional · mapas de evidencia). Enunciado libre + hasta 5
   sub-preguntas.
2. **`stage-teoria`** — editor visual del marco lógico CEPAL con 5
   columnas (insumos → actividades → productos → resultados → impacto),
   nodos editables inline (máx 4 por nivel) + supuestos transversales
   (máx 6). Plantilla seed de educación.
3. **`stage-indicadores`** — tabla SMART con 10 columnas: nivel · nombre
   · definición operativa · fórmula · fuente · línea base · meta ·
   frecuencia · chip SMART (validación 0-5) · eliminar. Hasta 30
   indicadores. Seed de 4 indicadores típicos.
4. **`stage-metodo`** — **14 métodos pre-cargados** (frontera 2020-2026):
   RCT (Banerjee-Duflo-Kremer) · **DID escalonado ★** (Callaway-Sant'Anna
   2021 · Sun-Abraham 2021 · Borusyak-Jaravel-Spiess 2024) · DID clásico
   (Card-Krueger 1994) · **Synthetic Control aumentado ★** (Ben-Michael
   2021) · SC clásico (Abadie 2010) · **RDD moderno ★** (Cattaneo-Keele-
   Titiunik 2023) · RD clásico · **Double ML ★** (Chernozhukov 2018) ·
   **Causal Forests ★** (Wager-Athey 2018) · Matching (Rosenbaum-Rubin) ·
   **Análisis de Contribución ★** (Mayne 2024 · WB IEG 2023) ·
   cualitativo (Patton 2022 · Yin 2018) · mixto (Creswell-Plano Clark
   2017) · VfM + MVPF (HM Treasury 2022 + Hendren-Sprung-Keyser 2020).
   Badge "Sugerido" según tipo. **Toggle "tratamiento escalonado"**: si
   selecciona DID clásico con rollout escalonado → warning automático
   sobre sesgo TWFE (Goodman-Bacon 2021) + sugerencia de migrar a DID
   escalonado.
5. **`stage-dac`** — 6 cards con criterios OCDE-DAC (versión 2019):
   relevance, coherence, effectiveness, efficiency, impact,
   sustainability. Por cada uno: definición + textarea auto-evaluación
   + botón "Marcar como NO APLICA…" con prompt de justificación.
6. **`stage-economico`** (B v2.4 · opcional) — toggle activo/inactivo +
   3 calculadoras conviventes:
   - **CBA · Cost-Benefit** (Green Book HM Treasury 2022): VPN = Σ(B−C)/(1+r)^t
     con tasa de descuento configurable (DNP 9% · GB 3.5%) y horizonte 1-50
     años. Reporta VPN + ratio B/C.
   - **MVPF** (Hendren-Sprung-Keyser NBER 2020): WTP_receptores / costo
     neto al gobierno. &gt; 1 → política Pareto-superior. Comparable
     inter-programa.
   - **CEA** (J-PAL): costo total / outcome total en unidad natural.
     Útil cuando monetizar el beneficio es controversial.
   Cálculo cliente-side con `_calcCBA`, `_calcMVPF`, `_calcCEA`. Los
   tres resultados entran al plan .md y al PAP exportable.
7. **`stage-plan`** — 4 campos operativos: cronograma · equipo
   evaluador (con dedicaciones) · presupuesto estimado · plan de uso
   de resultados.

**`stage-results`** — resumen con tarjeta de método elegido + 4 KPI
cards (teoría/indicadores/DAC/plan) + cierre operativo + 2 cross-links
amarillos (Mactor + problema-publico).

**Exports:**
- `downloadPlanMD` — plan estructurado en 6 secciones compatible
  con formato Sinergia/DNP.
- **`downloadPAPMD`** (B v2.5) — **Pre-Analysis Plan en 13 secciones**
  compatible con AEA RCT Registry / OSF: research question +
  hipótesis primarias/secundarias + outcomes (primarios/secundarios/
  exploratorios) + ToC + especificación econométrica explícita +
  **MHT correction pre-registrada** (Bonferroni k≤3 · Holm/Romano-Wolf
  k≤8 · Benjamini-Hochberg FDR k≥9, según Anderson 2008 JASA ·
  List-Shaikh-Xu 2019 Exp Econ) + heterogeneidad pre-especificada +
  power calculation placeholder + análisis económico (si activo) +
  OCDE-DAC + limitations + **protocolo de desviaciones** + bibliografía.
- `downloadMatrizCSV` — matriz de indicadores con SMART score + missing.

**STATE shape (B v2):**
```js
STATE = {
  step: 1,
  pregunta: { tipo, alcance, enunciado, subpreguntas[], tipo_sinergia },
  teoria:    { insumos[], actividades[], productos[], resultados[], impacto[], supuestos[] },
  indicadores: [{ nivel, nombre, def, formula, fuente, base, meta, frecuencia }],
  metodo:    { id, justificacion, tratamiento_escalonado },  // 'si'|'no'|''
  dac:       { relevance, coherence, effectiveness, efficiency, impact, sustainability },
  economico: { activo, cba:{costos_total, beneficios_total, tasa_descuento, horizonte_anios, weights_distrib},
               mvpf:{beneficios_receptores, costo_neto_gob},
               cea:{costo_total, outcome_unidad, outcome_total} },
  plan:      { cronograma, equipo, presupuesto, uso }
}
```
Persistido en `localStorage['ev-current-v1']`. `loadState()` defensivo.

**Copiloto IA (Sprint B.8):** 3 acciones con cache hash24 TTL 7d:
- `sugerir-indicadores` (Pro+) · 4-6 indicadores SMART desde teoría
  y pregunta; botón "+ Agregar" inyecta al state.
- `validar-teoria` (Premium+) · detecta saltos lógicos, supuestos
  implícitos, niveles desbalanceados, impactos vagos + sugiere
  supuestos faltantes.
- `narrativa-plan` (Premium+) · lectura interpretativa del plan:
  lógica + fortalezas + riesgos del método + puntos a cerrar antes
  de comité.

**PDFs Evaluación en S3** (Sprint B.10 + B v2.6):
```
s3://elecciones-2026/ricardoruiz.co/bases de datos/ev/
  metodologia-paso-a-paso.pdf  (19.2 KB · 11 secciones · v2.0)
  respaldo-academico.pdf       (26.9 KB · marco + fórmulas + 48 refs · v2.0)
```
Pipeline en `tools/build-ev-docs/{build_metodologia.py, build_respaldo.py}`.
Para regenerar:
```bash
python3 tools/build-ev-docs/build_metodologia.py
python3 tools/build-ev-docs/build_respaldo.py
aws s3 cp "Bases de datos/ev/metodologia-paso-a-paso.pdf" \
  "s3://elecciones-2026/ricardoruiz.co/bases de datos/ev/metodologia-paso-a-paso.pdf" \
  --content-type "application/pdf" --cache-control "public, max-age=300"
aws s3 cp "Bases de datos/ev/respaldo-academico.pdf" \
  "s3://elecciones-2026/ricardoruiz.co/bases de datos/ev/respaldo-academico.pdf" \
  --content-type "application/pdf" --cache-control "public, max-age=300"
```

**Validación del worker (B v2.7):** El worker rr-auth valida en `/ev/save`:
- 14 method ids whitelisted en `EV_METODOS_ID`.
- `tratamiento_escalonado` ∈ {'si','no',''}.
- `tipo_sinergia` ∈ {6 tipos DNP, ''}.
- Bloque `economico` persiste como strings (frontend valida numéricamente).

### `alternativas.html` (Alternativas de política · Sprint C)

Quinto módulo del lab. Es la **versión profunda del paso 3 de
problema-publico** (Bardach): donde pp pide enumerar 3-5 opciones,
este módulo te obliga a recorrer el espacio completo de combinaciones
con análisis morfológico, descartar las inviables, y probar las
restantes contra 4 escenarios antes de recomendar una.

Anclado en cinco escuelas: **Zwicky** (Caltech 1969, análisis morfológico),
**Ritchey** (Swedish Morphological Society 2011, cross-consistency
assessment), **Lempert &amp; Walker** (RAND 2003, Robust Decision Making),
**Howard** (Stanford 1968, Decision Analysis), **Keeney** (USC 1992,
Value-Focused Thinking). Lente económica opcional con **MVPF** de
Hendren &amp; Sprung-Keyser (NBER 2020) y **CEA** de J-PAL. Anclaje
regulatorio: **SINERGIA · DNP** + formato CONPES light.

**6 mecánicas operativas + welcome + decisión + results:**

1. **`stage-variables`** — editor de chips con 11 tipos (cobertura,
   financiamiento, instrumento, gobernanza, condicionalidad, timing,
   población, ámbito, modalidad, sostenibilidad, otra) + 6 plantillas
   seed por dominio (cobertura-social, reforma-fiscal, servicio-publico,
   regulacion, seguridad, blanco). Mín 3 / máx 8. IA "sugerir-variables"
   (Pro+) propone 5-7 variables desde el enunciado del problema.
2. **`stage-opciones`** — paneles por variable con 3-5 opciones
   editables inline. Mín 2 / máx 5 por variable. Stage meta muestra el
   producto de combinaciones posibles. IA "sugerir-opciones" (Pro+)
   opera variable por variable.
3. **`stage-matriz`** — matriz Zwicky visual con 2 modos: <em>marcar
   incompatibilidades</em> (clic en una opción, clic en otra de variable
   distinta → par marcado, clic doble deshace) y <em>explorar combinación</em>
   (selecciona una opción por columna, conteo de combinaciones brutas +
   restantes via brute-force hasta 5.000). Botón "Guardar como
   alternativa" cuando la selección está completa y sin conflictos.
4. **`stage-alternativas`** — cards con baseline "Statu quo" auto-insertado
   (no eliminable, sólo renombrable). Cada card: nombre + combinación +
   descripción + supuestos críticos + costo + plazo + riesgo dominante.
   Editor inline de combinación con selects por variable. Warning rojo
   si la combinación contiene pares incompatibles marcados. Max 6 +
   baseline. IA "validar-coherencia" (Premium+) detecta combinaciones
   operativamente contradictorias.
5. **`stage-robustez`** — 4 escenarios pre-definidos editables (baseline
   40% · optimista 25% · pesimista 25% · disruptivo 10%) con
   probabilidad subjetiva editable. Matriz alternativas × escenarios
   con rating 1-5 por celda. Score esperado = Σ(prob × rating) / Σprob.
   Bonus +0.5 si peor caso ≥ 3. Lente económica opcional por alternativa:
   costo total, beneficio total, unidad outcome, outcome total → MVPF
   (β/c) y CEA (c/outcome) cliente-side. Badge "PARETO-SUPERIOR" si
   MVPF &gt; 1.
6. **`stage-decision`** — cards ordenadas por score final desc con
   radio de selección. Textarea de justificación obligatoria.
   `stage-results` con hero + 4 KPIs + tabla compacta + IA
   "narrativa-alternativas" (Premium+) + 3 exports + botón "Enviar a
   Problema Público".

**Cálculos clave (cliente, sin libs externas):**
- `_calcRestantesPostIncompat()` — enumera combinaciones válidas
  brute-force hasta 5.000; arriba muestra "—".
- `_calcScoresAlt(altId)` — devuelve `{ expected, worst, best, bonus,
  final, complete }`. Normaliza por probSum.
- `_calcEconAlt(alt)` — devuelve `{ c, b, o, u, mvpf, cea }`.

**STATE shape:**
```js
STATE = {
  step: 1,
  contexto:     { enunciado_problema, dep_cod, mun_cod, sector, importedFromPP },
  variables:    [{ id, nombre, tipo }],           // 3-8
  opciones:     { [varId]: ['opt 1', 'opt 2', ...] }, // 2-5 por var
  incompat:     [['varId:optIdx', 'varId:optIdx'], ...],
  alternativas: [{ id, nombre, desc, supuestos, costo, plazo, riesgo,
                   combo:{[varId]:optIdx}, baseline,
                   econ:{ costo_total, beneficio_total, unidad_outcome,
                          outcome_total } }],
  escenarios:   [{ id, nombre, descripcion, prob }],
  ratings:      { [altId]: { [scenId]: 1..5 } },
  decision:     { altId_recomendada, justificacion }
}
```
Persistido en `localStorage['alt-current-v1']`. `loadState()` defensivo.

**Copiloto IA (Sprint C.7):** 4 acciones con cache hash24 TTL 7d:
- `sugerir-variables`      (Pro+)    · paso 1, 5-7 variables típicas
- `sugerir-opciones`       (Pro+)    · paso 2, 3-5 opciones por variable
- `validar-coherencia`     (Premium+)· paso 4, detecta combos contradictorios
- `narrativa-alternativas` (Premium+)· paso 7, lectura interpretativa del ranking

**Exports (Sprint C.6):**
- `downloadMemoMD` — markdown estructurado en 5 secciones + footer metodológico.
- `downloadMatrizCSV` — CSV alternativas × escenarios + scores + lente económica.
- `downloadConpesPDF` — PDF jsPDF (CDN on-demand) formato CONPES light.
- `enviarAProblemaPublico` — escribe `localStorage['alt-import-to-pp']`
  con shape compatible con `STATE.alternativas` de pp + redirige a
  `problema-publico.html?import=alt`. pp tiene `handleAltImportOnLoad()`
  que prompts confirm y reemplaza el state.

**PDFs Alternativas en S3** (Sprint C.9):
```
s3://elecciones-2026/ricardoruiz.co/bases de datos/alt/
  metodologia-paso-a-paso.pdf  (16.8 KB · 10 secciones operativas + ejemplo completo)
  respaldo-academico.pdf       (19.7 KB · marco + fórmulas + 29 referencias)
```
Pipeline en `tools/build-alt-docs/{build_metodologia.py, build_respaldo.py}`.

### `ain.html` (Análisis de Impacto Normativo · Sprint D)

Sexto módulo del lab. Opera sobre el estándar **Regulatory Impact
Assessment (RIA)** de la OCDE (2012, revisión 2022), operacionalizado
en Colombia por **DNP y Función Pública** vía **Decreto 1081/2015**
(proyectos normativos) y **Decreto 1273/2020** (consulta pública).
Marco teórico: Sunstein (*Simpler* 2013), Hahn-Tetlock (JEP 2008),
Stigler (1971 captura del regulador), Mashaw (*Reasoned Administration*
2018), Pigou, Coase, Akerlof.

**6 mecánicas operativas + welcome + results:**

1. **`stage-problema`** — caracteriza el problema regulatorio.
   Enunciado + tipo de falla (6 familias canónicas: mercado,
   externalidad, asimetría info, coordinación, equidad distributiva,
   monopolio natural) + afectados (chips, max 12) + evidencia inicial.
   Banner "Importar desde Problema Público" lee localStorage
   `pp-current-v1` y precarga.
2. **`stage-objetivos`** — 1-5 objetivos con 4 campos cada uno:
   enunciado, indicador, meta, plazo. Validación de "completo" cuando
   los 4 están llenos.
3. **`stage-opciones`** — 7 tipos canónicos (statu-quo baseline,
   regular directo, autorregulación, co-regulación, sandbox,
   instr-mercado, otra) según Sunstein. Cada card con tipo + descripción
   operativa + supuestos. Banner "Importar desde Alternativas" lee
   `alt-current-v1` o `alt-import-to-ain`. IA "sugerir-opciones-
   regulatorias" (Pro+). Max 6 + baseline.
4. **`stage-impactos`** — matriz opciones × 5 categorías (costos
   directos, costos indirectos, beneficios, captura, carga admin) con
   escala B/M/A/MA. Score agregado = beneficios − promedio(costos+
   captura+carga). Winner highlighted.
5. **`stage-consulta`** — plan de consulta (audiencias chips + 7
   instrumentos multi-select + cronograma) + matriz de 5 riesgos
   regulatorios (captura, asimetría, carga excesiva, fragmentación,
   obsolescencia · Hahn-Tetlock 2008 + Stigler 1971) con pills
   bajo/medio/alto. IA "detectar-riesgos-regulatorios" (Premium+) con
   niveles + justificaciones + mitigaciones + botón "Adoptar".
6. **`stage-implementacion`** — 5 campos textarea: cronograma de
   implementación, responsables, presupuesto, indicadores de monitoreo,
   cláusula de revisión (24-36m con criterio cuantitativo).

**`stage-results`** — hero con opción recomendada + 4 KPIs + tabla
compacta con scores + selector de recomendación con justificación
textual obligatoria. IA "narrativa-ain" (Premium+) genera informe
estilo DNP con: justificación del problema, justificación de la
recomendación, objeciones anticipadas en consulta, mitigaciones de
riesgo, condiciones de revisión.

**Cálculos clave:**
- `_calcImpScore(optId)` → `{ score, complete, beneficios, costos_promedio }`.
  Mapeo cualitativo bajo=1/medio=2/alto=3/muy-alto=4. Score =
  beneficios − promedio(4 categorías invertidas).
- `_optRankings()` → ordena opciones por score desc.

**STATE shape:**
```js
STATE = {
  step: 1,
  contexto:     { enunciado_problema, dep_cod, mun_cod, sector,
                  instrumento_norm, importedFromPP, importedFromAlt },
  problema_reg: { enunciado, tipo_falla, afectados[], evidencia_inicial },
  objetivos:    [{ id, enunciado, indicador, meta, plazo }],
  opciones:     [{ id, nombre, tipo, desc, supuestos, baseline,
                   importedFromAlt }],
  impactos:     { [optId]: { costos_directos, costos_indirectos,
                             beneficios, captura, carga_admin } },
  consulta:     { plan, audiencias[], instrumentos[], cronograma },
  riesgo_reg:   { captura, asimetria, carga_excesiva, fragmentacion,
                  obsolescencia },
  implementacion: { cronograma, responsables, presupuesto,
                    indicadores_monitoreo, clausula_revision },
  recomendacion: { opcionId_recomendada, justificacion }
}
```
Persistido en `localStorage['ain-current-v1']`. `loadState()` defensivo.

**Copiloto IA (Sprint D.8):** 3 acciones con cache hash24 TTL 7d:
- `sugerir-opciones-regulatorias` (Pro+) · 4-6 opciones cubriendo al
  menos 4 familias regulatorias canónicas con descripción + justificación.
- `detectar-riesgos-regulatorios` (Premium+) · estima los 5 riesgos
  como bajo/medio/alto con justificación por dimensión + mitigaciones.
- `narrativa-ain` (Premium+) · redacta informe estilo DNP con 5
  secciones: justificación problema, justificación recomendación,
  objeciones anticipadas, mitigaciones de riesgo, condiciones de
  revisión.

**Exports (Sprint D.7):**
- `downloadMemoMD` — markdown en 7 secciones con footer metodológico.
- `downloadMatrizCSV` — CSV opciones × impactos + scores.
- `downloadConpesPDF` — jsPDF on-demand. Memo CONPES regulatorio con
  problema + objetivos + opciones + matriz impactos + análisis de
  riesgo + consulta + implementación + recomendación. Disclaimer
  "borrador estilo CONPES; no es CONPES oficial".
- `enviarAEvaluacion` — escribe `localStorage['ain-import-to-ev']` con
  opción recomendada + objetivos + indicadores monitoreo + justificación.
  Redirige a `evaluacion.html?import=ain`. Pickup en
  `evaluacion.html` con `handleAINImportOnLoad()` precarga pregunta
  evaluativa (causal · ex-post) + sub-preguntas desde objetivos AIN +
  marco lógico inicial.

**PDFs AIN en S3** (Sprint D.10):
```
s3://elecciones-2026/ricardoruiz.co/bases de datos/ain/
  metodologia-paso-a-paso.pdf  (15.1 KB · 10 secciones + ejemplo regulatorio
                                  · pólizas de salud prepagada)
  respaldo-academico.pdf       (15.5 KB · marco + fórmulas + 26 referencias
                                  · Pigou, Coase, Stigler, Akerlof, Sunstein,
                                  Hahn-Tetlock, Mashaw, OCDE-RIA, Decretos)
```
Pipeline en `tools/build-ain-docs/{build_metodologia.py, build_respaldo.py}`.
Reportlab, sin más deps. Para regenerar:
```bash
python3 tools/build-ain-docs/build_metodologia.py
python3 tools/build-ain-docs/build_respaldo.py
aws s3 cp "Bases de datos/ain/metodologia-paso-a-paso.pdf" \
  "s3://elecciones-2026/ricardoruiz.co/bases de datos/ain/metodologia-paso-a-paso.pdf" \
  --content-type "application/pdf" --cache-control "public, max-age=300"
aws s3 cp "Bases de datos/ain/respaldo-academico.pdf" \
  "s3://elecciones-2026/ricardoruiz.co/bases de datos/ain/respaldo-academico.pdf" \
  --content-type "application/pdf" --cache-control "public, max-age=300"
```
Reportlab, sin más deps. Para regenerar:
```bash
python3 tools/build-alt-docs/build_metodologia.py
python3 tools/build-alt-docs/build_respaldo.py
aws s3 cp "Bases de datos/alt/metodologia-paso-a-paso.pdf" \
  "s3://elecciones-2026/ricardoruiz.co/bases de datos/alt/metodologia-paso-a-paso.pdf" \
  --content-type "application/pdf" --cache-control "public, max-age=300"
aws s3 cp "Bases de datos/alt/respaldo-academico.pdf" \
  "s3://elecciones-2026/ricardoruiz.co/bases de datos/alt/respaldo-academico.pdf" \
  --content-type "application/pdf" --cache-control "public, max-age=300"
```

### Recursos & Datos · catálogo compartido `lab-recursos.js` (Sprint A.1)

Catálogo curado de 30 recursos en 5 categorías (Colombia política
pública · Colombia datos abiertos · Evaluación · Diseño/participación ·
Prospectiva). Cada item etiquetado con qué módulos del lab destaca.

**Distribución por módulo:**
- problema: 19 recursos · evaluación: 15 · estructural: 13 · mactor: 5
- alternativas: 13 (CONPES, SISCONPES, DNP-KPT, KP-DNP, CEPAL-ILPES,
  UK-OPM, service-design, BI-team, LIPSOR, RAND-RDM, Policy Impacts,
  J-PAL CEA, Future Today)

**Dos puntos de carga:**
1. **Hub** (`stage-hub` de analisis-estructural.html) muestra TODO el
   catálogo en `<details>` colapsable al pie.
2. **FAB "Recursos"** en los 4 módulos sub (`.lab-fab` bottom-left,
   z-index 8000) abre `modal-recursos` filtrado por
   `LAB_CURRENT_MODULE` ∈ {'estructural','mactor','problema','evaluacion','alternativas'}.

Cargado vía `<script src="lab-recursos.js">` en los 5 HTMLs.
Mantener URLs estables (dominios oficiales). Si un link rompe, se
actualiza en un solo archivo y los 5 puntos lo recogen.

### Sprint G · informe combinado del lab (`lab-informe.js`)

Cierre natural del lab: un solo PDF/MD que une el trabajo del usuario
en los 6 módulos en un memo CONPES integrado. **Cliente-side puro,
sin backend** — el archivo `lab-informe.js` lee los 6 localStorage
keys del navegador del usuario y arma el informe con jsPDF (carga
on-demand desde CDN, mismo patrón de `alternativas.html` y `ain.html`).

**Punto de entrada:** sección `Mi informe del lab` en el `stage-hub`
de `analisis-estructural.html`, después del wizard y antes del
catálogo de Recursos. Cards de los 6 módulos con badge ✓/○ según
estado de localStorage, snippet del contenido principal de cada
módulo, y 2 botones de export: `↓ Informe combinado (.pdf)` y
`↓ Memo .md`. Disclaimer recordando que los datos se leen del
navegador (no se envían a ningún servidor).

**Estructura del informe** (8 secciones, ~5-8 páginas A4):

1. **Portada** — fecha, descripción, lista de los 6 módulos con
   estado ✓/○.
2. **Resumen ejecutivo** — auto-generado a partir del state combinado.
   Hila enunciado del problema + Rittel-Webber + variables motrices +
   actores dominantes + alternativa recomendada + opción regulatoria
   + método evaluativo en un solo párrafo.
3. **Diagnóstico del problema** (PP) — enunciado · magnitud · urgencia
   · afectados · causas · efectos · Rittel-Webber · marco analítico ·
   evidencia.
4. **Variables motrices del sistema** (MicMac) — top 5 motrices
   calculadas a partir de `s.matrix` con valencias firmadas, cuadrante
   asignado por mediana de motricidad/dependencia.
5. **Mapa de actores y conflictos** (Mactor) — top 5 dominantes por
   poder relativo Ri = Ii / (Ii+Di) + objetivos por saldo neto
   ponderado.
6. **Espacio de alternativas** (Alt) — recomendación final (decision
   explícita o ranking por score esperado) + lente económica (MVPF ·
   CEA si disponibles).
7. **Análisis de Impacto Normativo** (AIN) — tipo de falla · opción
   recomendada · riesgos regulatorios (Hahn-Tetlock 2008) ·
   justificación.
8. **Plan de evaluación** (Ev) — pregunta + tipo + Sinergia DNP +
   método (con warning TWFE si tratamiento escalonado) + indicadores
   SMART + análisis económico tripartito.
9. **Próximos pasos operativos** — derivados automáticamente del state:
   "levantar más evidencia" si pp.evidencia.length < 3; "estrategia
   con dominantes opositores" si saldo del objetivo principal < 0;
   "completar matriz robustez" si alt sin recomendada; etc.

**Footer metodológico:** cita las escuelas combinadas (Bardach 2020 ·
Godet/Mojica/LIPSOR · Lempert-Walker RAND 2003 · Zwicky 1969 · Ritchey
2011 · OCDE RIA · Hendren NBER 2020 · OCDE-DAC · AEA RCT Registry ·
frontera causal 2020-2026).

**Archivos involucrados:**
```
lab-informe.js                            (~720 líneas · helpers + PDF + MD)
analisis-estructural.html                 (Sección "Mi informe del lab" + wiring)
problema-publico.html · mactor.html       (cross-links amarillos a #informe)
evaluacion.html · alternativas.html · ain.html  (cross-links amarillos a #informe)
```

**API pública en `window.LabInforme`:**
- `getLabState()` → `{ pp:{exists,data,resumen}, micmac:{...}, mactor:{...}, alt:{...}, ain:{...}, ev:{...} }`
- `countActiveModules(state)` → número 0-6 de módulos con contenido.
- `buildLabPDF(state?)` → `Promise<filename>`; carga jsPDF si hace falta, dispara descarga.
- `buildLabMarkdown(state?)` → `string` con el informe en markdown.
- `buildResumenEjecutivo(state)` → `string` con el párrafo de exec summary.

**Anchor `#informe`:** cualquier link a
`analisis-estructural.html#informe` hace scroll a la sección al cargar
la página (handler en `init()`). Los 5 módulos sub-lab tienen un
cross-link visualmente distinto (acento oxblood, símbolo ∑) que apunta
ahí.

**Limitaciones conocidas:**
- El cálculo de PP recomendada usa los `scores` cliente-side del
  módulo Problema Público; si el usuario no completó la matriz, no
  hay recomendación visible (solo lista de alternativas).
- MicMac: el script asume que `s.matrix[i-j]` puede ser número o
  objeto `{valor}`; usa magnitud absoluta para calcular cuadrantes
  (no preserva signos). DEMATEL/ISM no entran al informe — solo
  MicMac.
- Si el usuario tiene contenido en localStorage de versiones previas
  con shape distinto, los resumidores devuelven `isEmpty:true`
  defensivamente.
- PDF se descarga directo sin pre-vista. Si el usuario quiere editar
  antes de comité, exportar `.md` y editarlo en su editor preferido
  es la ruta recomendada.

### Sprint E · indicadores municipales oficiales (`lab-indicadores.js`)

Pipeline de datos territoriales precargados desde fuentes oficiales para
los 4 módulos analíticos del lab (analisis-estructural, problema-publico,
ain, evaluacion). **Fase A LISTA** (8 indicadores · 1.108 muns · panel
2018-2024). Fase B pendiente (descargas manuales desde TerriData / DANE
EEVV / MinSalud).

**Pipeline · `tools/build-indicadores-mun/build.py`** (Python stdlib pura):
- 6 datasets Socrata de datos.gov.co (resource IDs constantes):
  - `m8fd-ahd9` — HOMICIDIO (MinDefensa · DIVIPOLA)
  - `4rxi-8m8d` — HURTO PERSONAS (MinDefensa)
  - `csb4-y6v2` — HURTO VEHÍCULOS (MinDefensa)
  - `gepp-dxcs` — VIOLENCIA INTRAFAMILIAR (MinDefensa)
  - `bz43-8ahq` — DELITOS SEXUALES (MinDefensa)
  - `sras-4t5p` — MEN_ESTADISTICAS_POR_ETC (cobertura neta · deserción ·
    matrícula 5-16, **a nivel Entidad Territorial Certificada**)
- Query agregada Socrata: `$select=cod_muni,date_extract_y(fecha_hecho) as anio,sum(cantidad) as total &$where=date_extract_y(fecha_hecho)>=2018 AND <=2024 &$group=cod_muni,anio &$limit=50000`.
- Mapeo ETC→DIVIPOLA: 97 ETCs (32 deptales + 65 muns certificados). Para
  muns no certificados aplica el valor del ETC departamental con marca
  `_meta: "ETC departamental (aprox)"`.
- Aliases manuales en `ETC_ALIASES` para los 4 casos donde el nombre del
  MEN no matchea con el DIVIPOLA (Cartagena, San Andrés, Bogotá D.C.,
  La Estrella).
- Cache local en `Bases de datos/indicadores-mun/raw/` (JSONs intermedios).
  Re-correr con `--no-cache` para refresh completo.
- Output: `Bases de datos/indicadores-mun/indicadores-mun.json` (~980 KB
  plano, ~150 KB gzip).

Para regenerar:
```bash
python3 tools/build-indicadores-mun/build.py
aws s3 cp "Bases de datos/indicadores-mun/indicadores-mun.json" \
  "s3://elecciones-2026/ricardoruiz.co/bases de datos/indicadores-mun/indicadores-mun.json" \
  --content-type "application/json" --cache-control "public, max-age=600"
```
Bumpear `CACHE_BUSTER` en `lab-indicadores.js` al refrescar.

**Shape del JSON:**
```jsonc
{
  "v": "20260526", "sprint": "E.2", "fase": "A", "periodo": [2018, 2024],
  "indicadores": [
    { "id":"homicidios", "nombre":"Homicidios (víctimas)", "unidad":"víctimas/año",
      "categoria":"seguridad", "fuente":"Policía Nacional · Ministerio de Defensa",
      "fuente_url":"https://www.datos.gov.co/d/m8fd-ahd9",
      "nota":"...", "panel":[2018,...,2024] },
    ...8 indicadores...
  ],
  "muns": {
    "05001": {
      "nombre":"Medellin", "depto":"Antioquia", "cod_depto":"05",
      "datos": {
        "homicidios": {"2018":625,"2019":576,..."2024":309},
        "hurto_personas": {...},
        "cobertura_neta": {"2018":96.88,..."2024":93.58},
        "_meta": { "cobertura_neta":"ETC departamental (aprox)" }  // si proxy
      }
    },
    ...1.108 muns...
  }
}
```

**`lab-indicadores.js` (helper, ~270 líneas):**

API en `window.LabIndicadores`:
- `load()` → Promise · carga lazy del JSON (cache en memoria por sesión).
- `getCatalog()` → 8 indicadores con metadatos.
- `getMun(divipola)` → `{ nombre, depto, cod_depto, datos }`.
- `getMunsByDepto(codDepto)` → lista de muns del depto, ordenada A→Z.
- `getValue(divipola, indicadorId, year)` → `{ value, year, isProxy, source, proxyNote }`.
- `getLatestValue(divipola, indicadorId)` → último año disponible.
- `getSerie(divipola, indicadorId)` → `{ values:{year:v,...}, isProxy, proxyNote, indicador }`.
- `searchMun(query, codDepto?)` → top 30 muns que matchean por nombre.
- `getDeptosCatalog()` → 33 deptos ordenados A→Z.
- `matchIndicadorByKeyword(text)` → id del indicador si el texto contiene
  un keyword conocido (homicidio, hurto, deserción, cobertura, etc.).
- `formatValue(value, indicadorId)` → string formateado (% / conteo / COP).

**Cobertura por módulo (Sprint E.4-E.7):**

| Módulo | Integración | Aporte |
|---|---|---|
| `analisis-estructural.html` (E.4) | Selector territorio depto + mun cascada; `showIndicator` muestra panel municipal con **sparkline SVG inline** + serie 2018-2024 cuando `municipal_id` matchea | 3 indicadores nuevos en INDICATORS (deserción, hurto vehículos, delitos sexuales); 5 indicadores existentes ganan datos municipales |
| `problema-publico.html` (E.5) | Selector territorio en `stage-evidencia` + botón "↓ Cargar evidencia oficial" precarga 5 filas con datos reales del último año disponible | Saca al usuario de la búsqueda manual de cifras DANE |
| `ain.html` (E.6) | Selector territorio en `stage-problema` con grid de 6 indicadores territoriales (último año + fuente + proxy badge). Setea `STATE.contexto.mun_cod` para el copiloto y los exports CONPES | Dimensiona el problema regulatorio con cifras auditables |
| `evaluacion.html` (E.7) | Selector territorio en `stage-indicadores`. Chip `✦ Autocompletar` al lado del input nombre del indicador, sólo si hay match keyword + mun. Pre-rellena base, fuente, def y fórmula | Acelera la captura SMART evitando copy-paste de DANE |

**Cómo se ve para el usuario:**

1. En cualquiera de los 4 módulos elige *Antioquia* en el primer select.
2. Se puebla el segundo select con los 125 muns de Antioquia.
3. Elige *Medellín* (DIVIPOLA 05001).
4. El módulo muestra:
   - En estructural: si nombra una variable "Inseguridad", el chip DATO
     ahora abre un panel con valor nacional + depto + **municipio
     (sparkline 2018→2024)**.
   - En problema-publico: botón "Cargar evidencia oficial" agrega 5 filas
     a la tabla con `Homicidios · Medellín: 309 víctimas (2024)` y
     similares, con link al dataset.
   - En AIN: grid con 6 mini-cards mostrando "Homicidios · 309 ·
     [fuente↗]" etc., y se guarda `mun_cod` en el contexto.
   - En evaluación: al escribir "cobertura escolar" en un indicador,
     aparece chip ✦ Autocompletar (Medellín) que rellena base+fuente+def.

**Fase B · descarga manual pendiente (checklist operativo):**

Esta sección queda para consulta futura cuando se decida cerrar Fase B.
La razón de la fase manual: TerriData, DANE EEVV microdatos y MinSalud
SISPRO son SPAs detrás de login o filtros JavaScript que WebFetch no
puede traer limpios. Toca click manual una vez.

**Indicadores faltantes (~8 indicadores agrupados por fuente):**

| # | Indicador | Fuente | Cosecha | Dónde bajarlo | Formato |
|---|---|---|---|---|---|
| F1 | IPM 2018 (Pobreza multidimensional) | DANE Censo 2018 | Único | `terridata.dnp.gov.co/#/descargas` → ficha "IPM" | XLS por dimensión |
| F2 | NBI 2018 (Necesidades básicas insatisfechas) | DANE Censo 2018 | Único | TerriData → ficha "NBI" | XLS |
| F3 | Población DIVIPOLA proyectada | DANE proyecciones | 2018-2024 anual | TerriData → ficha "Demografía" | XLS |
| F4 | Acceso a agua potable | DANE Censo 2018 / SUI | 2018 + actualizaciones | TerriData → "Servicios públicos" | XLS |
| F5 | Internet hogares | DANE ENCV / MinTIC | 2023 | TerriData → "Conectividad" (solo cabecera urbana en muchos casos) | XLS |
| F6 | Mortalidad infantil (<1 año) | DANE EEVV no fetales | 2018-2022 anual | `microdatos.dane.gov.co/index.php/catalog/EEVV-2022` | CSV ~250 MB/año |
| F7 | Mortalidad materna | DANE EEVV | 2018-2022 anual | Mismo path EEVV | Mismo CSV (filtrar por causa CIE-10) |
| F8 | Embarazo adolescente (10-19) | DANE EEVV nacimientos | 2018-2022 anual | `microdatos.dane.gov.co/index.php/catalog/EEVV-NAC-2022` | CSV ~150 MB/año |
| F9 | Vacunación DPT3 (cobertura PAI) | MinSalud SISPRO | 2018-2023 anual | `bodega.sispro.gov.co` (login con cualquier correo) → cubo "PAI - Coberturas" → exportar | XLSX por depto/mun |

**Ruta esperada de los archivos descargados:**

```
Bases de datos/indicadores-mun/raw/
  terridata/
    ipm-2018-por-mun.xlsx        ← TerriData ficha IPM (todos los muns)
    nbi-2018-por-mun.xlsx        ← idem NBI
    poblacion-2018-2024.xlsx     ← idem proyecciones anuales
    agua-2018-por-mun.xlsx       ← idem servicios públicos
    internet-2023-por-mun.xlsx   ← idem conectividad
  dane-eevv/
    EEVV-Defunciones-2018.csv    ← microdatos defunciones no fetales
    EEVV-Defunciones-2019.csv
    ...
    EEVV-Defunciones-2022.csv
    EEVV-Nacimientos-2018.csv    ← microdatos nacimientos (para embarazo adolescente)
    ...
    EEVV-Nacimientos-2022.csv
  minsalud/
    pai-cobertura-2018-2023.xlsx ← bodega SISPRO export
```

**Cómo extender el pipeline `tools/build-indicadores-mun/build.py`:**

1. Crear una nueva función por fuente:
   - `_fetch_terridata_xlsx(path, col_divipola, col_valor)` — usa openpyxl
     (única dep extra), lee `Bases de datos/indicadores-mun/raw/terridata/`
     y devuelve `{ divipola: valor }` o `{ divipola: { año: valor } }`.
   - `_fetch_eevv_csv(path, año, filtro)` — lee CSVs DANE en streaming
     (puede ser pesado, usar pandas o stdlib `csv.DictReader`). Cruza
     `COD_MUNI_OCU` o `COD_MUNI_RES` (decidir cuál → según indicador, la
     convención DANE es "lugar de ocurrencia") y agrupa por mun.
   - `_fetch_pai_xlsx(path, col_mun, col_cobertura)` — lee bodega SISPRO.

2. Agregar los nuevos indicadores a `indicadores_meta`:
   ```python
   { "id":"ipm", "nombre":"Pobreza multidimensional (IPM)", "unidad":"%",
     "categoria":"pobreza", "fuente":"DANE Censo 2018", ... }
   ```

3. Ensamblar el merge con datos Fase A en el bloque final.

4. Bumpear `CACHE_BUSTER` en `lab-indicadores.js` (`v=YYYYMMDD`).

5. Re-correr → re-subir a S3 → spot-check de Medellín / Bogotá / un mun
   pequeño contra la ficha oficial TerriData.

**Keywords nuevas para `matchIndicadorByKeyword` en `lab-indicadores.js`:**

```js
'ipm': 'ipm', 'pobreza multidim': 'ipm', 'multidimensional': 'ipm',
'nbi': 'nbi', 'necesidades basicas': 'nbi',
'agua potable': 'agua', 'acueducto': 'agua',
'internet': 'internet', 'conectividad': 'internet',
'mortalidad infantil': 'mortalidad_infantil',
'mortalidad materna': 'mortalidad_materna',
'embarazo adolescente': 'embarazo_adolescente', 'fecundidad adolescente': 'embarazo_adolescente',
'vacunacion': 'vacunacion_dpt', 'cobertura pai': 'vacunacion_dpt', 'dpt3': 'vacunacion_dpt'
```

**Notas operativas críticas:**

- **TerriData no expone API REST estable.** Los XLS descargados manualmente
  son la única vía. Algunos archivos vienen con encabezados en español
  con caracteres especiales — abrir en Excel + guardar como CSV UTF-8
  antes de procesar.
- **DANE EEVV son pesados** (~150-300 MB por año). Pre-filtrar con
  `csv.DictReader` por columnas estrictas; no cargar todo a memoria.
- **MinSalud SISPRO requiere registro gratuito** (cualquier correo).
  El cubo "PAI - Coberturas" se exporta a XLSX directo desde el dashboard
  con filtros depto/mun/año.
- **DIVIPOLA en EEVV**: la columna `COD_MUNI_OCU` (lugar de ocurrencia)
  vs `COD_MUNI_RES` (lugar de residencia). Para mortalidad usamos
  ocurrencia; para nacimientos usamos residencia de la madre. Documentado
  en el manual EEVV-2022 del DANE.
- **Bumpear `CACHE_BUSTER` en `lab-indicadores.js`** SIEMPRE que se
  regenere el JSON, sino los navegadores cachean la versión vieja por
  10 minutos.

**Tiempo estimado Fase B completa:** ~6-8 horas (3h descarga manual de
las 9 fuentes, 2-3h escribir parsers Python, 1-2h validar y subir).

### Sprint F · escenarios prospectivos (3 frentes simultáneos)

Tres frentes complementarios en un solo sprint, cierre prospectivista del lab:

**(A) Módulo nuevo `prospect-escenarios.html`** — séptimo módulo del lab.
2.407 líneas. Marco metodológico combinado:

- **Método de los ejes de incertidumbre** (Schwartz · Global Business
  Network 1991): 2 incertidumbres críticas → 4 cuadrantes narrados.
- **Prospectiva estratégica francesa** (Godet · LIPSOR · CNAM, adaptada
  por Mojica en Externado): incertidumbres derivadas del análisis
  estructural (variables motrices del MicMac).
- **Cross-impact analysis** (Gordon & Hayward 1968, RAND): matriz
  elementos × escenarios con valencias -2..+2.
- **Robust Decision Making** (Lempert & Walker 2003, RAND): decisiones
  no-regret = válidas en ≥3 de 4 escenarios. Plan de contingencia para
  escenarios donde falla. Señales tempranas para vigilancia estratégica.

4 mecánicas + welcome + results:
1. `stage-incertidumbres` — define 2 ejes con polo neg/pos. Botón
   "✦ Importar de MicMac" lee `localStorage['micmac-current-v2']`,
   calcula motricidad `Σ|M[i,j]|` por fila y sugiere las 2 top.
2. `stage-escenarios` — matriz 2x2 visual con NE/NO/SO/SE editables
   (nombre + narrativa + probabilidad). Sum-check de probabilidad ≈ 100%.
3. `stage-cross-impact` — auto-import desde MicMac (variables), Mactor
   (actores), Alt (alternativas) con checkboxes. Matriz con celdas
   cyclando 0→+1→+2→-1→-2.
4. `stage-estrategia` — lista de alternativas con badge ✓ NO-REGRET si
   ≥3 escenarios tienen impacto ≥+1. Textareas de contingencia +
   señales tempranas.
5. `stage-results` — resumen + 3 exports (memo .md, matriz .csv, ficha
   .pdf jsPDF on-demand).

STATE en `localStorage['prospect-current-v1']`. Sin cloud-save ni IA
copiloto en v1 (solo localStorage). Cuando se quiera multi-user, agregar
endpoints `/prospect/*` al worker rr-auth (no implementado en F).

**(B) Capa what-if en módulos vivos** — paneles "¿Qué pasa si...?" al
final del stage-results de los módulos analíticos:

- `analisis-estructural.html` (+151 líneas): slider -3..+3 (mapeado a
  ±30% motricidad de la variable). Re-corre `_computeMicMacOn` sobre
  una copia de la matriz, recalcula cuadrantes por mediana y diff'ea
  contra el original. Reporta variables que cambian de cuadrante o
  suben/bajan ≥2 posiciones en motricidad. La matriz guardada no se
  toca.
- `mactor.html` (+152 líneas): slider -50%..+50% sobre la fila MID del
  actor seleccionado. Recalcula Ri = I/(I+D) para todos los actores y
  saldos por objetivo. Reporta top 2 ΔRi (uno arriba, uno abajo) y
  objetivos que cambian de signo (de positivo a negativo o viceversa).
  MID/MAO originales sin tocar.

**(C) Monte Carlo en `alternativas.html`** (+227 líneas) — análisis
estocástico bajo incertidumbre en ratings y probabilidades. Botón "Correr
simulaciones" al final del stage-robustez. Configuración:

- Número de sims: 500 / 1000 / 5000.
- Perturbación rating: ±0.5 / ±1 / ±1.5 (escala 1-5 truncada).
- Perturbación probabilidad: ±5 / ±10 / ±20 puntos porcentuales
  (renormalizada a suma 100% post-perturbación).

Loop en batches de 100 sims con `requestIdleCallback` cuando N≥2000
(fallback `setTimeout` para no bloquear UI). Por sim aplica la fórmula
`Σ(prob × rating) / Σprob + bonus(worst≥3)` con `_calcScoresAlt` reusado.
Acumula winCount por alternativa + samples ordenados.

Resultado: tabla con P(#1) % + barra visual + score medio + p10-p90.
Interpretación auto: P(#1) > 60% = robusta · 30-60% = moderada · < 30% =
contingente. Sin libs externas.

**Hub 7 cards** — actualizado de 3+3 a 3+4 (o 4+3 según breakpoint).
Card prospect agregada al final con tag "Schwartz · Godet · Mojica ·
Lempert".

**Cross-links** — desde stage-results de problema-publico, evaluacion,
ain agregamos un cross-link gold hacia prospect ANTES del cross-link
oxblood al informe combinado. Cada link tiene su pretexto contextual
("¿La regulación es robusta en distintos futuros?", "¿La política
mantiene sentido si el contexto cambia?", etc.).

**PDFs en S3** (Sprint F.D.3):
```
s3://elecciones-2026/ricardoruiz.co/bases de datos/prospect/
  metodologia-paso-a-paso.pdf  (10.2 KB · 7 secciones operativas)
  respaldo-academico.pdf       (13.1 KB · 20 referencias clásicas)
```
Pipeline en `tools/build-prospect-docs/{build_metodologia.py, build_respaldo.py}`.
Reportlab puro. Re-correr y `aws s3 cp` al actualizar.

**lab-recursos.js** — sumados 3 recursos nuevos al catálogo:
- Schwartz · The Art of the Long View (GBN)
- Cross-Impact Analysis · Gordon & Hayward 1968
- Mojica · Concepto y aplicación de la prospectiva estratégica

Y tag `prospect` agregado a los recursos existentes que aplican: LIPSOR,
Externado-CIPE, Future Today Institute, RAND-RDM.

### Worker rr-auth — endpoints del lab

Total **56 endpoints** (7 micmac + 7 mactor + 7 pp + 7 ev + 7 alt + 7 ain + 7 prospect + 7 comunicar),
agrupados en 6 módulos paralelos con el mismo patrón CRUD + invite +
copiloto.

**MicMac (`/micmac/*`):**
- `GET    /micmac/list` — lista proyectos (owner + collab).
- `POST   /micmac/save` — crea o actualiza. Plan gate por cuota.
- `GET    /micmac/load?projId=&since=` — carga con polling.
- `DELETE /micmac/delete?projId=` — solo owner.
- `POST   /micmac/invite` — manda correo Resend con link 14d.
- `GET    /micmac/accept?token=` — acepta invitación.
- `POST   /micmac/copiloto` — 5 acciones IA.

**Mactor (`/mactor/*`):** mismos 6 endpoints CRUD/invite + uno copiloto.

**Problema Público (`/pp/*`)** — Sprint A.3 y A.4:
- `GET    /pp/list` — lista análisis (owner + collab).
- `POST   /pp/save` — crea o actualiza. Validación dura.
- `GET    /pp/load?projId=&since=` — carga con polling.
- `DELETE /pp/delete?projId=` — solo owner.
- `POST   /pp/invite` — correo Resend con link 14d.
- `GET    /pp/accept?token=` — acepta invitación.
- `POST   /pp/copiloto` — 3 acciones IA (Sprint A.4).

**Evaluación (`/ev/*`)** — Sprint B.7 y B.8:
- `GET    /ev/list` — lista análisis (owner + collab).
- `POST   /ev/save` — crea o actualiza. Validación dura:
  `pregunta.enunciado` no vacío, ≤30 indicadores, niveles/tipos/
  alcances/métodos whitelisted.
- `GET    /ev/load?projId=&since=` — carga con polling.
- `DELETE /ev/delete?projId=` — solo owner.
- `POST   /ev/invite` — correo Resend con link 14d, copy "Evaluación".
- `GET    /ev/accept?token=` — acepta invitación.
- `POST   /ev/copiloto` — 3 acciones IA (Sprint B.8).

**Alternativas (`/alt/*`)** — Sprint C.7:
- `GET    /alt/list` — lista análisis (owner + collab).
- `POST   /alt/save` — crea o actualiza. Validación dura: ≤8 variables,
  ≤5 opciones por variable, ≤7 alternativas (6 + baseline), ≤60 incompats,
  ≤4 escenarios, ratings 1-5, scenIds whitelisted, tipos de variable
  whitelisted, ids hex.
- `GET    /alt/load?projId=&since=` — carga con polling.
- `DELETE /alt/delete?projId=` — solo owner.
- `POST   /alt/invite` — correo Resend con link 14d, copy "Alternativas
  de Política".
- `GET    /alt/accept?token=` — acepta invitación.
- `POST   /alt/copiloto` — 4 acciones IA (Sprint C.7).

**AIN (`/ain/*`)** — Sprint D.8:
- `GET    /ain/list` — lista análisis (owner + collab).
- `POST   /ain/save` — crea o actualiza. Validación dura: tipo_falla
  whitelisted, ≤5 objetivos, ≤7 opciones (6 + baseline), tipo de opción
  whitelisted, niveles de impacto whitelisted, ≤12 afectados, ≤10
  audiencias, instrumentos whitelisted, dimensiones de riesgo
  whitelisted, niveles riesgo whitelisted, ids hex.
- `GET    /ain/load?projId=&since=` — carga con polling.
- `DELETE /ain/delete?projId=` — solo owner.
- `POST   /ain/invite` — correo Resend con link 14d, copy "Análisis
  de Impacto Normativo".
- `GET    /ain/accept?token=` — acepta invitación.
- `POST   /ain/copiloto` — 3 acciones IA (Sprint D.8).

**Prospect (`/prospect/*`)** — Sprint F v2:
- `GET    /prospect/list` — lista análisis prospectivos (owner + collab).
- `POST   /prospect/save` — crea o actualiza. Validación dura: ejes con
  polos neg/pos, 4 escenarios {NE,NO,SO,SE} con prob 0-100,
  ≤30 elementos importados con tipo whitelisted
  ({variable,actor,alternativa}) y source whitelisted
  ({micmac,mactor,alt,manual}), impactos como int -2..+2 por
  cuadrante, ids hex.
- `GET    /prospect/load?projId=&since=` — carga con polling.
- `DELETE /prospect/delete?projId=` — solo owner.
- `POST   /prospect/invite` — correo Resend con link 14d, copy
  "Escenarios Prospectivos".
- `GET    /prospect/accept?token=` — acepta invitación.
- `POST   /prospect/copiloto` — 2 acciones IA (Sprint F v2.3).

**Acciones IA por módulo (action en body):**
| Módulo | Acción | Plan |
|---|---|---|
| micmac | `validar-vars` | Pro+ |
| micmac | `categorizar` | Pro+ |
| micmac | `contexto-relacion` | Premium+ |
| micmac | `validar-matriz` | Premium+ |
| micmac | `narrativa` | Premium+ |
| mactor | `sugerir-actores` | Pro+ |
| mactor | `validar-mao` | Premium+ |
| mactor | `narrativa` | Premium+ |
| pp     | `sugerir-alternativas` | Pro+ |
| pp     | `validar-criterios` | Premium+ |
| pp     | `narrativa-memo` | Premium+ |
| ev     | `sugerir-indicadores` | Pro+ |
| ev     | `validar-teoria` | Premium+ |
| ev     | `narrativa-plan` | Premium+ |
| alt    | `sugerir-variables` | Pro+ |
| alt    | `sugerir-opciones` | Pro+ |
| alt    | `validar-coherencia` | Premium+ |
| alt    | `narrativa-alternativas` | Premium+ |
| ain    | `sugerir-opciones-regulatorias` | Pro+ |
| ain    | `detectar-riesgos-regulatorios` | Premium+ |
| ain    | `narrativa-ain` | Premium+ |
| prospect | `sugerir-ejes` | Pro+ |
| prospect | `narrar-escenarios` | Premium+ |
| comunicar | `sugerir-audiencias` | Pro+ |
| comunicar | `validar-mensaje` | Premium+ |
| comunicar | `narrativa-ganz` | Premium+ |

**Storage KV (`RR_STORE`):**
```
micmac:proj:<projId>         JSON completo del proyecto
micmac:owner:<email>:<projId>  "1" (índice owner)
micmac:collab:<email>:<projId> "1" (índice collab)
micmac:invite:<token>        invitación TTL 14d
micmac:copiloto:<hash24>     respuestas IA TTL 7d
mactor:* (mismo layout con prefijo mactor)
pp:*     (mismo layout con prefijo pp)
ev:*     (mismo layout con prefijo ev)
alt:*    (mismo layout con prefijo alt)
ain:*    (mismo layout con prefijo ain)
prospect:* (mismo layout con prefijo prospect)
comunicar:* (mismo layout con prefijo comunicar)
```

**DeepSeek:** API key `DEEPSEEK_API_KEY` como secret del worker
(misma que la Lambda `test-presidencial-explica`). Modelo
`deepseek-v4-flash`. AbortSignal 28s. Cache hash24 con
`PROMPT_VERSION='v1'` (bumpear al cambiar prompts para invalidar cache).

**Plan gate (común a los 7 módulos):**
```js
MICMAC_MAX_PROJ = MACTOR_MAX_PROJ = PP_MAX_PROJ = EV_MAX_PROJ = ALT_MAX_PROJ = AIN_MAX_PROJ = PROSPECT_MAX_PROJ = { free:1, pro:5, premium:25, full:50 }
PP_MAX_ALTERNATIVAS = 5
PP_MAX_CRITERIOS    = 8
PP_MAX_EVIDENCIA    = 60
PP_MAX_AFECTADOS    = 30
EV_MAX_INDICADORES  = 30
EV_MAX_SUBPREGUNTAS = 5
EV_MAX_SUPUESTOS    = 6
EV_MAX_NODOS_NIVEL  = 4
ALT_MAX_VARIABLES        = 8
ALT_MAX_OPCIONES_POR_VAR = 5
ALT_MAX_ALTERNATIVAS     = 7   // 6 + baseline
ALT_MAX_INCOMPAT         = 60
ALT_MAX_ESCENARIOS       = 4
AIN_MAX_OBJETIVOS        = 5
AIN_MAX_OPCIONES         = 7   // 6 + baseline statu-quo
AIN_MAX_AFECTADOS        = 12
AIN_MAX_AUDIENCIAS       = 10
PROSPECT_MAX_ELEMENTOS   = 30  // cross-impact: vars + actores + alts
COMUNICAR_MAX_PROJ       = { free:1, pro:5, premium:25, full:50 }
COMUNICAR_MAX_AUD        = 6
COMUNICAR_MAX_MULT       = 8
COMUNICAR_MAX_PALABRAS   = 16   // palabras propias / adversario (framing)
// canales whitelisted (14) · matriz audiencia×canal 0-3 · 9 KPIs OCDE · fase/objetivo/prioridad/tipo-multiplicador whitelisted
```

**Deploy del worker:**
```bash
cd /Users/ricardoruiz/rr-auth && npx wrangler deploy
```
**Atención:** este worker es compartido — cambios afectan también a
micmac, mactor y los demás módulos del sitio. Pedir luz verde antes
de deployar en producción.

**Helpers compartidos:** `sessionGuard(request, env)` valida Bearer
token + plan. `_callDeepSeek(env, systemPrompt, userMsg, opts)`. `_hash24(str)`.

### Sprint F v2 · cloud-save + IA copiloto para prospect (cierre del 7º módulo)

Cierra el séptimo módulo del lab a paridad de los otros seis: cloud-save
multi-user, invitaciones por correo y dos acciones IA copiloto.

**Worker rr-auth** (+440 líneas en `/Users/ricardoruiz/rr-auth/src/index.js`):
- 7 endpoints `/prospect/*` espejo del patrón `/alt/*` y `/ain/*`:
  list, save, load, delete, invite, accept, copiloto.
- Validación dura en `/prospect/save`:
  - Ejes con `nombre`, `polo_neg`, `polo_pos` (cada uno ≤240 chars).
  - 4 escenarios `{NE,NO,SO,SE}` con `nombre`, `narrativa`, `prob`
    (clamped 0-100).
  - ≤30 elementos con tipo whitelisted (`variable`/`actor`/`alternativa`)
    + source whitelisted (`micmac`/`mactor`/`alt`/`manual`) +
    id alfanumérico 2-80 chars.
  - Impactos por elemento × cuadrante: integer en [-2, +2] (clamped).
  - Estrategia con `contingencia` + `senales_tempranas` (≤4000 chars).
- 2 acciones IA copiloto:
  - `sugerir-ejes` (Pro+) · DeepSeek V4 Flash, max 1500 tokens, temp
    0.4. Recibe `{contexto, variables_micmac}` con las 12 top motrices
    si vienen del análisis estructural previo. Devuelve 2 ejes con
    polos descriptivos + rationale.
  - `narrar-escenarios` (Premium+) · DeepSeek V4 Flash, max 3000 tokens,
    temp 0.55. Recibe `{ejes, contexto}` con los 2 ejes confirmados.
    Devuelve 4 narrativas plausibles con nombre evocador + probabilidad
    subjetiva. Renormaliza probs a sumar 100 si el modelo se equivoca.
  - Cache hash24 TTL 7d.

**Frontend `prospect-escenarios.html`** (+~600 líneas):
- Bloque AUTH/CLOUD copiado del patrón de `ain.html`: `loadUserFromAPI`,
  `renderAuthChip`, `apiCall`, `cloudSave`, `cloudLoad`, `cloudDelete`,
  `newProject`, `openInviteModal`, `submitInvite`, `acceptInviteFlow`.
- UI cloud-bar en `stage-results` (y opcionalmente en `cloud-bar-flow`
  durante las 4 mecánicas).
- Sección `#my-projects` arriba con `<details>` para abrir análisis
  guardados.
- Auto-cloud-save con debounce de 2s: `saveState()` dispara
  `cloudSave()` si `AUTH.isLogged && CLOUD.projId`.
- Polling cada 10s mientras la pestaña está activa para sincronizar
  ediciones de colaboradores.
- 2 ia-bars:
  - En `stage-incertidumbres`: "Sugerir incertidumbres con IA"
    (`iaSugerirEjes()`). Si hay `localStorage['micmac-current-v2']`,
    calcula motricidad de cada variable y pasa top 8 como contexto.
  - En `stage-escenarios`: "Narrar los 4 escenarios con IA"
    (`iaNarrarEscenarios()`). Requiere 2 ejes con polos definidos.
  - Ambas con botón "+ Adoptar" que aplica el resultado al STATE.

**`lab-informe.js`** (+~150 líneas):
- `getLabState()` agrega `prospect: { exists, data, resumen }`.
- Nuevo helper `_resumenProspect(s)` que extrae:
  - ejes con polos
  - 4 escenarios narrados con probabilidad
  - nElementos (de cross-impact)
  - **noRegret[]**: alternativas con impacto ≥+1 en ≥3 escenarios
    (cálculo Lempert · RDM)
  - estrategia (contingencia + señales tempranas)
- `countActiveModules()` ahora cuenta hasta 7.
- `buildResumenEjecutivo()` agrega línea sobre escenarios prospectivos
  si tienen contenido.
- **Sección 8 nueva** en el MD y PDF del informe combinado: ejes +
  tabla 4×4 de escenarios + alternativas no-regret + contingencia +
  señales tempranas.
- "Próximos pasos" considera prospect: si tiene ejes sin escenarios →
  recomienda narrar los 4 cuadrantes; si tiene cross-impact sin
  no-regret → recomienda completar la matriz para identificar
  decisiones robustas.

**Deploy de v2:**
```bash
cd /Users/ricardoruiz/rr-auth && npx wrangler deploy
```
Ya desplegado en producción.

### Cómo agregar una acción IA nueva

1. Definir un `PROMPT` constante con regla JSON estricta.
2. Crear `_micmacNueva(env, payload)` que devuelve `{ok, data}` o
   `{ok:false, error}`.
3. Registrar en `COPILOTO_ACTIONS` con `{fn, planes, plan}`.
4. Frontend: nueva función `iaNueva()` en analisis-estructural.html
   con loading state, plan gate y render del resultado.

### Sprint H · Comunicar la política (octavo módulo del lab)

Octavo módulo. Plan operativo de comunicación pública para una política
diseñada/evaluada/implementada/en crisis. **v1 sin worker** (igual que
prospect v1): solo localStorage, cloud-save y copiloto IA quedan para
v2 cuando se aprueben los endpoints `/comunicar/*` en `rr-auth`.

Vive en `comunicar.html` (~119 KB · 2.050 líneas, chasis y look idéntico
a `ain.html` y `prospect-escenarios.html`).

**Marco metodológico convergente (5 escuelas):**
- **OCDE · Public Communication Report 2021** (`Reaching Out and
  Reaching In`). De ahí salen las **9 dimensiones de medición**
  (alcance · engagement · atención · comprensión · satisfacción · apoyo
  · cambio actitudinal · intención · comportamiento). Ver también
  *Accessible and Inclusive Public Communication* (OCDE WP 54, 2022).
- **CLAD Carta Iberoamericana de Gobierno Abierto 2016** (firmada en
  Bogotá). Marco regional común a 22 países iberoamericanos.
- **Colombia · Función Pública · MIPG Dimensión 5** "Información y
  Comunicación" (Decreto 1499/2017 + Manual Operativo v6 dic 2024).
  Y **Ley 1712 de 2014** (transparencia + lenguaje claro).
- **Marshall Ganz** (Harvard Kennedy School) · Public Narrative
  *Self/Us/Now*. La narrativa es traducción de valores en acción
  colectiva.
- **George Lakoff** (UC Berkeley) · *Don't Think of an Elephant!* ed.
  2024 (framing). **Anat Shenker-Osorio** · ASO Communications · *Words
  To Win By* (priming experiments + dial surveys). **BIT EAST framework**
  (UK Behavioural Insights Team, 2014 rev. 2024): Easy · Attractive ·
  Social · Timely. **Deborah Stone** · *Policy Paradox* (Counting ·
  Causation · Comparison). **Omar Rincón** (UniAndes · CESPA) ·
  narrativas mediáticas en Colombia.

**8 mecánicas operativas + welcome + results:**

1. **`stage-contexto`** — Nombre de la política · fase del ciclo
   (`diseno`/`evaluacion`/`implementacion`/`crisis`) · enunciado breve ·
   objetivo comunicacional (informar/persuadir/movilizar/dar cuenta/
   defender/co-crear) · horizonte (1m/3m/6m/12m/multi) · territorio.
   Banner "Importar desde PP/Ev/Alt/AIN" lee los `localStorage`
   correspondientes y precarga el `enunciado`.
2. **`stage-audiencias`** — Mín 2 / máx 6. Cada una con `nombre · perfil
   · prioridad (alta/media/baja) · conocimiento previo · tono`. Botón
   "Cargar audiencias típicas" siembra 6 audiencias sector público
   (ciudadanía afectada · medios · concejo/asamblea · sociedad civil ·
   academia · equipo interno).
3. **`stage-mensaje`** — Primario ≤15 palabras (counter en vivo) +
   3 secundarios (BBC Editorial Guidelines / Frank Luntz / ASO) +
   promesa concreta + evidencia principal + 2-5 valores invocados
   desde un dropdown de 15 valores universales.
4. **`stage-narrativa`** — 3 textareas Ganz: Story of Self · Story of
   Us · Story of Now. Hint en cada una con plantilla.
5. **`stage-framing`** — Valor central · metáfora dominante · chips de
   palabras propias (≤16) · chips de palabras del adversario (≤16, NO
   repetir, regla Lakoff 1) · cómo romper el encuadre adversario.
6. **`stage-canales`** — 14 canales pre-cargados en el catálogo
   (medios trad · redes Meta · X · TikTok · YouTube · WhatsApp · web
   oficial · email · territorial · eventos · sociedad civil · influencers
   · gremios · academia). Pills para seleccionar (mín 3, máx 10). Luego
   matriz audiencia × canal con celdas que ciclan 0→1→2→3 (apoyo/
   principal/saturación). Textarea notas EAST por canal principal.
7. **`stage-voceria`** — Vocero principal (nombre + rol + justificación)
   + hasta 8 multiplicadores con tipo (académico/gremial/territorial/
   medios/sociedad civil/celebridad/político aliado) + audiencia que
   cubre + riesgos de vocería + plan B.
8. **`stage-cronograma`** — 4 fases (pre-lanzamiento · lanzamiento ·
   mantenimiento · evaluación) + grid de 9 KPIs (uno por dimensión
   OCDE: alcance/engagement/atención/comprensión/satisfacción/apoyo/
   actitudinal/intención/comportamiento) con nombre/meta/fuente
   editables + plan de monitoreo + triggers de ajuste.

**STATE shape:**
```js
STATE = {
  step: 1,
  contexto: { politica, fase, enunciado, objetivo, horizonte,
              dep_cod, dep_nombre, mun_cod, mun_nombre,
              importedFromPP, importedFromEv, importedFromAin, importedFromAlt },
  audiencias: [{ nombre, perfil, prioridad, tono, conocimiento }],
  mensaje: { primario, secundarios:[...], promesa, evidencia, valores:[...] },
  narrativa: { self, us, now },
  framing: { valor, metafora, encuadre_evitar,
             palabras_propias:[...], palabras_adversario:[...] },
  canales: { seleccionados:[...], matriz:{[aId]:{[cId]:0-3}}, notas_east },
  voceria: { vocero:{nombre,rol,justifica},
             multiplicadores:[{nombre,tipo,audiencia}], riesgos },
  cronograma: { fase_pre, fase_lanzamiento, fase_mantenimiento, fase_evaluacion },
  medicion:   { kpis:{[dimId]:{nombre,meta,fuente}}, plan_monitoreo, triggers_ajuste }
}
```
Persistido en `localStorage['comunicar-current-v1']`. `loadState()`
defensivo (merge contra defaults, sesiones previas siguen funcionando).

**Exports (3 entregables):**
- `downloadPlanMD()` — plan estructurado en 9 secciones (contexto ·
  audiencias · mensaje · narrativa · framing · canales · vocería ·
  cronograma · medición OCDE 9-dim) con footer metodológico.
- `downloadMatrizCSV()` — CSV con 2 bloques: matriz audiencia × canal
  + tabla KPIs OCDE 9-dim (dimensión, kpi, meta, fuente).
- `downloadGuiaMensajesMD()` — guía operativa para el vocero y prensa
  con mensaje primario destacado, 3 secundarios, narrativa Ganz en 90s,
  lenguaje (decimos · NO repetimos · valor central · metáfora) y plan
  de respuesta al frame adversario.

**Hub integrado** (`analisis-estructural.html`):
- Card #8 agregada al `hub-grid` (tag "OCDE 2021 · CLAD · MIPG · Ganz ·
  Lakoff · EAST").
- `HUB_MODULES.comunicar = { name:'Comunicar la política', href:'comunicar.html' }`.
- Eyebrow del hub pasa de "7 módulos integrados" → "8".
- Closing paragraph del hub explica el encadenamiento completo de los
  8 módulos.

**Cross-links amarillos hacia comunicar desde:**
- `problema-publico.html` · stage-results · "¿Y cómo se va a contar
  esta política al público?"
- `mactor.html` · stage-results · "¿Cómo le hablamos a cada uno de
  estos actores?"
- `evaluacion.html` · stage-results · "¿Cómo se comunican los
  resultados de esta evaluación?"
- `alternativas.html` · stage-results · "¿Cómo defiendes en público
  la alternativa elegida?"
- `ain.html` · stage-results · "¿Cómo le explicas la norma a quienes
  regulas?" (cita Ley 1712 transparencia + lenguaje claro)
- `prospect-escenarios.html` · stage-results · "¿Cómo cuentas estos
  escenarios al equipo, los aliados y la ciudadanía?"
- `analisis-estructural.html` · stage-results · "¿Cómo le explicas el
  mapa del sistema a quien decide?"

Además todos los módulos que ya tenían cross-link al informe combinado
actualizaron el texto de "6 módulos" / "7 módulos" → "8 módulos
(problema · sistema · actores · alternativas · AIN · evaluación ·
escenarios · comunicar)".

**Integración a `lab-informe.js` (sección 9 nueva):**
- Helper `_resumenComunicar(s)` que extrae política, fase, objetivo,
  nAud, audPrioAlta, mensaje primario, secundarios, narrativa Ganz
  (con flag `completa: ganzListos === 3`), framing, canales activos,
  vocería y nKpis OCDE.
- `getLabState()` agrega `comunicar: {exists, data, resumen}` leyendo
  `localStorage['comunicar-current-v1']`.
- `countActiveModules()` ahora cuenta hasta 8 (`pp`, `micmac`, `mactor`,
  `ev`, `alt`, `ain`, `prospect`, `comunicar`).
- `buildResumenEjecutivo()` agrega una línea sobre el plan de
  comunicación cuando tiene contenido.
- **Sección 9 nueva** en el MD y PDF del informe combinado:
  `## 9. Plan de comunicación de la política` con política/fase,
  audiencias prioritarias, mensaje primario, secundarios, promesa,
  evidencia, valores, narrativa Ganz, framing (valor + propias +
  adversario), canales activos, vocería y medición OCDE 9-dim.
- **Sección 10 "Próximos pasos operativos"** (antes era la 9). Sugerencias
  derivadas: completar audiencias si <2 · completar Ganz si listos<3 ·
  definir vocero si vacío · diseñar el plan si pp.exists pero
  comunicar.isEmpty.
- Footer metodológico extendido con las 5 escuelas de comunicación.

**Catálogo `lab-recursos.js`:**
- +12 recursos nuevos con tag `comunicar`: OCDE Public Communication
  Report 2021 · OCDE Accessible and Inclusive 2022 · CLAD Carta
  Iberoamericana 2016 · MIPG Política de Comunicación · Ley 1712 ·
  Ganz Public Narrative MLD-355 · Leading Change Network · Lakoff
  *Don't Think of an Elephant!* 2024 · ASO *Words To Win By* · BIT
  EAST 2024 · Omar Rincón (Academia.edu UniAndes) · Stone *Policy
  Paradox* · Narrative Arts (Public Narrative en español).
- Tag `comunicar` añadido también a recursos preexistentes pertinentes
  (Función Pública AIN).

**`renderInformeSection` en `analisis-estructural.html`:**
- Counter pasa de "X / 6 módulos" → "X / 8 módulos".
- Array `order` ahora incluye los 8 módulos en orden lógico (PP →
  MicMac → Mactor → Alt → AIN → Ev → Prospect → Comunicar). Antes
  estaba bug-fix oculto: prospect tampoco estaba en el grid del
  informe combinado del hub, quedó arreglado en este sprint.
- `_informeSnippet` ahora maneja `prospect` (noRegret, ejes) y
  `comunicar` (nAud + primario, o política + fase).

**v2 · cloud-save + IA copiloto** ✓ LISTO (2026-05-31):
- **7 endpoints `/comunicar/*`** en `rr-auth` (list, save, load, delete,
  invite, accept, copiloto) espejo del patrón `/prospect/*`. KV prefijo
  `comunicar:*`. Total del worker: **56 endpoints**.
- Validación dura en `/comunicar/save`: ≤6 audiencias, mensaje primario
  ≤300 chars, ≤16 palabras propias/adversario, canales whitelisted (14),
  matriz audiencia×canal con valores ∈ {0,1,2,3} (≤12 filas), ≤8
  multiplicadores con tipo whitelisted, 9 KPIs OCDE, fase/objetivo/
  prioridad whitelisted.
- 3 acciones IA copiloto (DeepSeek V4 Flash · cache hash24 TTL 7d):
  - `sugerir-audiencias` (Pro+) · 4-6 audiencias típicas adaptadas al
    contexto y la fase. Botón "+ Agregar" inyecta al STATE (≤6).
  - `validar-mensaje` (Premium+) · heurística ASO/Lakoff (valor antes
    que política · ≤15 palabras · verbo de acción · beneficio · no
    repetir al adversario). Devuelve veredicto + issues + mensaje_mejorado
    con botón "Usar esta propuesta".
  - `narrativa-ganz` (Premium+) · borrador de Story of Self/Us/Now desde
    enunciado + valores + framing. Botón "Usar este borrador" rellena los
    3 campos.
- Frontend `comunicar.html`: bloque AUTH/CLOUD portado de `ain.html`
  (auth chip en nav, cloud-bars flow+results, `#my-projects`,
  modal-login, modal-invite, polling 10s, auto-save con debounce 2s vía
  `saveState`→`cloudAutoSave`, guard `_applyingRemote` para evitar
  ping-pong entre colaboradores). JS validado con `new Function` (0
  errores). Worker validado con `wrangler deploy --dry-run` (bundle OK).

**PDFs metodología (v2)** ✓ LISTOS (2026-05-31):
- `Bases de datos/comunicar/metodologia-paso-a-paso.pdf` (12.1 KB · 10
  secciones: intro + las 8 mecánicas + exportables · tabla OCDE 9-dim +
  heurística EAST + narrativa Ganz).
- `Bases de datos/comunicar/respaldo-academico.pdf` (9.4 KB · marco de las
  5 escuelas + 31 referencias canónicas).
- Pipeline en `tools/build-comunicar-docs/{build_metodologia.py, build_respaldo.py}`
  (reportlab, misma plantilla que prospect/ain). Regenerar:
  ```bash
  python3 tools/build-comunicar-docs/build_metodologia.py
  python3 tools/build-comunicar-docs/build_respaldo.py
  ```
- ✅ Subidos a S3 `bases de datos/comunicar/*`. Módulo cerrado.

### Versión portuguesa del Lab (Brasil) · `tools/build-pt-lab/translate.py`

Para la salida a Brasil, el Lab se traduce a PT-BR con un traductor por
diccionario (sin deps, stdlib pura). **No es traducción neuronal**: es
substitución ordenada de frases + palabras con word-boundary. Genera los 8
módulos desde sus fuentes ES.

**Mapa de archivos (`MODULES` en el script):**
```
analisis-estructural.html → analisis-estrutural.html   (entry; index.html ya lo enlaza para 'br')
mactor.html               → mactor-pt.html
problema-publico.html     → problema-publico-pt.html
evaluacion.html           → evaluacion-pt.html
alternativas.html         → alternativas-pt.html
ain.html                  → ain-pt.html
prospect-escenarios.html  → prospect-escenarios-pt.html
comunicar.html            → comunicar-pt.html
```

**Cómo corre el motor (en orden):** protege `<style>`/`<script>`/atributos
URL (`href`/`src`/`action`) → traduce HTML visible (PHRASES → WORDS →
restaura PHRASES → `contract()`) → restaura atributos reescribiendo
cross-links ES→PT → traduce string-literals **y template literals
backtick** dentro de `<script>` (preservando `${...}`) → quita `¿`/`¡`.
`contract()` recombina `em+art`/`de+art`/`a+art`/`por+art` en las
contracciones del portugués (no, na, do, da, ao, à, pelo…).

**Regenerar:**
```bash
python3 tools/build-pt-lab/translate.py            # los 8 módulos
python3 tools/build-pt-lab/translate.py mactor.html # uno solo (ES o PT name)
```

**Garantías validadas tras cada corrida:** integridad estructural (conteos
de `` ` ``, `${`, `{`, `}` idénticos a la fuente ES → el JS/CSS no se rompe),
0 cross-links ES restantes (toda navegación queda PT-interna), 0 `¿`/`¡`.

**Calidad (importante para el partner brasileño):** el chasis compartido
(nav, cloud-bar, auth, footer, wizard, recursos) y el vocabulario de política
pública común quedan en buen PT-BR. **Queda un long-tail** de español
residual y de gramática que el diccionario no cubre: concordancia de género
(«o equipe» → debería «a equipe»), clíticos («as podrás abordar»), y frases
variantes que no calzan con una PHRASE exacta (p.ej. «Les llegará un
correo»). El módulo más pulido es `analisis-estrutural.html` (el diccionario
está afinado para él). Para subir calidad: agregar PHRASES/WORDS por módulo,
o hacer una pasada humana/LLM sobre la copia que ve primero el partner
(welcome + hero + wizard). Los 8 archivos PT viven en el repo pero **no se
despliegan** hasta hacer push; `lab-recursos.js`/`lab-informe.js`/
`lab-indicadores.js` siguen en español (pendiente si se quiere el modal de
recursos y el informe combinado en PT).

### Backlog del lab

> **📌 HANDOFF PARA PRÓXIMA CONVERSACIÓN · Estado al 2026-05-28:**
>
> El Lab está **LISTO con 8 módulos** (11 sprints cerrados: A · B ·
> B v2 · C · D · E Fase A · F · F v2 · G · H v1 · varias V de Veleta
> y C de Cámara). 7 módulos operativos con cloud-save + copiloto IA
> DeepSeek (21 acciones) + informe combinado (sección 9 nueva con
> comunicar) + 8 indicadores municipales con panel 2018-2024.
> Octavo módulo **comunicar** entregado v1 solo localStorage (sin
> worker, sin copiloto).
>
> **ÚNICO PENDIENTE explícito del Lab: Sprint E Fase B** — agregar 8
> indicadores municipales más (IPM, NBI, agua, internet, mortalidad
> infantil/materna, embarazo adolescente, vacunación PAI). Requiere
> ~3h de descarga MANUAL (TerriData/DANE EEVV/MinSalud no exponen API
> limpia · WebFetch falla en sus SPAs) y luego ~3-5h de parser Python.
> El checklist completo está en la sección **"Sprint E Fase B ·
> descarga manual pendiente"** más abajo (busca `## Sprint E Fase B`
> o `terridata.dnp.gov.co/#/descargas`). Cubre las 9 fuentes con
> URLs, formato esperado, rutas locales, cómo extender
> `build-indicadores-mun/build.py` y keywords nuevas para
> `matchIndicadorByKeyword` en `lab-indicadores.js`.
>
> Otros pendientes del proyecto (NO del Lab) están más arriba en este
> archivo: `previa-1v.html` (gráfico temporal), Proyecto DC
> (módulos 08-09). Test Presidencial, Voto Fusil y Comunicar v2 ya
> cerraron (jul-2026).

**Sprint D · AIN** ✓ LISTO (ver sección dedicada arriba).

**Sprint B v2 · Evaluación con literatura 2020-2026** ✓ LISTO (ver sección
`evaluacion.html` arriba). Cerró:
- ✓ B v2.1 — 14 métodos (6 estado del arte ★ añadidos: DID escalonado,
  SC aumentado, RDD moderno, DML, causal forests, contribución).
- ✓ B v2.2 — TWFE warning automático cuando tratamiento escalonado.
- ✓ B v2.3 — Tipología Sinergia DNP en paso 1.
- ✓ B v2.4 — 3 calculadoras económicas (CBA · MVPF · CEA).
- ✓ B v2.5 — Pre-Analysis Plan exportable estilo AEA RCT Registry / OSF.
- ✓ B v2.6 — Modal "¿En qué se basa?" + PDFs v2.0 actualizados.
- ✓ B v2.7 — Worker validation + CLAUDE.md + deploy.

Investigación fuente: `Bases de datos/evaluacion-politicas/investigacion-literatura-2020-2026.txt`.
Posibles iteraciones futuras (no urgentes):
- Cargar el documento de literatura para enriquecer prompts del copiloto
  IA sin reescribir las 8 mecánicas.
- Power calculator integrado (no solo placeholder): inputs ICC/atrición/N
  + cálculo de MDE bajo distintos diseños.

**Sprint G · Informe combinado** ✓ LISTO. Ver sección "Sprint G ·
informe combinado" más abajo. Cierre natural del lab: un solo PDF/MD
que une el trabajo del usuario en los 6 módulos.

**Sprint E · Datos municipales Fase A** ✓ LISTO. Ver sección "Sprint E ·
indicadores municipales oficiales" más abajo. 8 indicadores con panel
2018-2024 sobre 1.108 municipios desde datos.gov.co. Integrado en
analisis-estructural, problema-publico, ain y evaluacion.

**Sprint F · Escenarios prospectivos** ✓ LISTO. Ver sección "Sprint F ·
escenarios prospectivos" más abajo. Tres frentes simultáneos:
- (A) Nuevo módulo `prospect-escenarios.html` (7º del lab · 2.407 líneas)
  con método de los ejes de incertidumbre (Schwartz · GBN), prospectiva
  estratégica francesa (Godet · Mojica), cross-impact (Gordon 1968) y
  RDM (Lempert).
- (B) Capa what-if en estructural (slider motricidad) + mactor (slider Ri).
- (C) Monte Carlo en alternativas (500/1000/5000 sims con perturbación
  configurable + P(#1) por alternativa).

**Sprint F v2 · Cloud-save + IA para prospect** ✓ LISTO. Ver sección
"Sprint F v2 · cloud-save + IA copiloto para prospect" más abajo. El
worker ahora tiene 56 endpoints (los 7 de prospect + 7 de comunicar). El
informe combinado de Sprint G integra el séptimo módulo en una nueva
sección 8.

**🟡 ÚNICO pendiente explícito del Lab — Sprint E Fase B:**

Agregar 8 indicadores municipales más al JSON `indicadores-mun.json`
(IPM 2018, NBI 2018, población DIVIPOLA, agua potable, internet hogares,
mortalidad infantil/materna, embarazo adolescente, vacunación PAI).

Requiere **descarga manual** porque TerriData (DNP), DANE EEVV
microdatos y MinSalud SISPRO son SPAs detrás de filtros JavaScript que
WebFetch no puede leer; toca click manual una vez. Checklist operativo
completo con URLs, formato y rutas locales en la sección **"Sprint E
Fase B · descarga manual pendiente (checklist operativo)"** más arriba
(busca `## Sprint E Fase B` en este archivo, ~línea 2742).

Estimación: 3h descarga manual + 2-3h escribir parsers `_fetch_terridata_xlsx`,
`_fetch_eevv_csv`, `_fetch_pai_xlsx` en `tools/build-indicadores-mun/build.py`
+ 1-2h validar contra fichas oficiales y subir a S3. Total ~6-8h.

Cuando se haga, **bumpear `CACHE_BUSTER` en `lab-indicadores.js`** (formato
`v=YYYYMMDD`) para invalidar el cache de 10 min en navegadores.

**Mejoras opcionales de módulos vivos (no pendientes activos):**
- **Mactor MIDI** — matriz pivotada de influencias indirectas entre
  actores (multiplica MID consigo misma).
- **Problema-Público v2** — sub-vista de árbol de objetivos (espejo
  del árbol del problema, lado positivo) y exportación PowerPoint.
- **Alternativas v2** — integración QCA (Ragin) para identificar
  configuraciones suficientes/necesarias en alternativas multi-caso.
  Reusa la infraestructura de matriz incompat de Sprint C.
- **Evaluación v3** — power calculator integrado (inputs ICC/atrición/N
  + cálculo de MDE bajo distintos diseños). Hoy es placeholder en el PAP.
- **Lab Sprint H (futuro)** — multi-lenguaje del Lab (inglés/portugués),
  útil si el producto se quiere vender en consultorías regionales.

### Reglas de oro para Lab de Políticas Públicas y Prospectiva

- **Cita siempre las raíces metodológicas** en textos públicos:
  Godet/Mojica/LIPSOR/Externado para prospectiva; Bardach/Patashnik/
  Ortegón/Torres-Melo para análisis de políticas; Zwicky/Ritchey/
  Lempert/Howard/Keeney para alternativas; OCDE-DAC/SINERGIA/Ivàlua
  para evaluación; Hendren/J-PAL para lente económica. Es lo que da
  legitimidad académica frente a un consultor experto.
- **El copiloto IA sugiere; el humano decide.** Siempre repetir esa
  línea en disclaimers, evitar UI que parezca "decisión automática del
  modelo".
- **No inventar referencias bibliográficas** con autor+año específicos
  en prompts del modelo. Si tenemos cita, va al respaldo PDF.
  Descriptor genérico "estudios de CEPAL sobre X" es OK.
- **Bumpear `PROMPT_VERSION` al cambiar prompts** del copiloto (entra
  al hash de cache).
- **Tuteo neutro Bogotá** en todos los textos del lab (sin voseo
  argentino, sin regionalismos paisa/costeño).
- **Cross-links entre módulos siempre contextuales.** No "abrir otro
  módulo" genérico, sino "Las variables que mueven este problema →"
  o "Los actores que pueden bloquear esta política →". Cada cross-link
  explica por qué tiene sentido el encadenamiento.
- **Sesiones previas deben seguir funcionando.** `loadState()` es
  defensivo: si faltan campos del state nuevo, los inicializa con
  defaults sin romper. Aplica a los 5 módulos.
- **Hub a 5 cards.** Cuando agregues un sexto módulo, considera dejar
  el actual de 3 cols × 2 rows (5 cards = 3+2) o subir a 3+3 = 6 cards.
  Más de 6 satura — meterlo como sub-módulo de uno existente (como
  Alternativas es sub-módulo de Problema Público).

## Páginas públicas del pilar Congreso — `legislativo.html` + `comision.html`

Cara pública (no gated) del histórico legislativo de abajo, para el ciudadano
general — distinta del privado `caudal.html`. `legislativo.html` es el hub
nacional (embudo, mortandad, bloqueo, acuerdo de presidencias); `comision.html`
(`?id=PRIMERA..SEPTIMA`) es la ficha por comisión constitucional, con el mismo
bloque de análisis replicado 100% a nivel de esa comisión.

**Composición de integrantes** (`comisiones-2026.json` en
`s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/legislativo/`):
consumida por `comision.html` (fetch directo, `COMISIONES_URL`) para pintar
las bolitas de Senado/Cámara — sin dato, cada cupo queda como placeholder "?"
("las plenarias eligen tras la instalación del 20 de julio de 2026"). Shape:
```json
{"v":"YYYY-MM-DD","comisiones":{"PRIMERA":{"senado":[{"nombre","partido"}],"camara":[...]}, ...}}
```
- **Fuente Cámara**: `Legislativo/Comisiones Cámara.xlsx` (Ricardo la baja a
  mano; hojas `Comisión Primera`..`Séptima` con Nombres+Partido+Comisión ya
  filtrado). El conteo real por comisión **no calza con los cupos teóricos**
  de `COMISIONES` en comision.html (Ley 3ª de 1992 — ej. Sexta trae 20 reales
  vs 28 de referencia); es esperado, no bug — `bubHtml` ya renderiza por
  `list.length`, no por `cupos`, así que no hace falta reconciliar.
  - Regenerar: leer las 7 hojas de comisión del xlsx, mapear
    `{nombre: Nombres, partido: Partido}` → `camara[]`; `senado` queda `[]`
    hasta que exista una fuente con esa asignación (la hoja `Senado` del xlsx
    trae a todos los 103 senadores pero sin columna Comisión rellenada aún).
  - Subir: `aws s3 cp "Bases de datos/legislativo/comisiones-2026.json"
    "s3://elecciones-2026/ricardoruiz.co/congreso-2026/output/legislativo/comisiones-2026.json"
    --content-type application/json --cache-control "public, max-age=300"`.
- **`ACUSACIONES`** (Comisión Legal de Investigación y Acusaciones, Cámara):
  entrada extra en el mismo JSON con los 17 integrantes (transcritos de una
  foto de la composición, jul-2026 — sin fuente oficial escaneable todavía).
  **`comision.html` NO tiene esta key en su array `COMISIONES`** (solo
  conoce PRIMERA..SEPTIMA) — el dato queda banked en el JSON para cuando se
  decida construir una ficha de comisiones legales (Ética, Acusaciones,
  Derechos Humanos, Cuentas, Equidad de la Mujer — mencionadas como nota en
  `legislativo.html` pero sin página propia). Varios de sus integrantes
  también se sientan en una constitucional (normal: es comisión legal, no
  exclusiva) — confirmado cruzando contra las hojas del xlsx.

## Histórico legislativo — `tools/leyes-senado/` (harvester LISTO · foso de Cauce)

Cosecha completa del histórico de **proyectos de ley, leyes sancionadas,
proyectos de acto legislativo y actos legislativos** del Congreso desde
**1990 hasta hoy**, scrapeado de `leyes.senado.gov.co`. Es la capa de datos
base del frente **[[project_cauce_alianza]]** (inteligencia legislativa) — el
"esqueleto" navegable de todo el trámite, con punteros a las gacetas donde
vive el texto. Corrido completo el 2026-07-10.

### La "API" no documentada del Senado
`leyes.senado.gov.co` es un frontend estático (Bootstrap + `js/app.js`) que
habla con endpoints PHP internos. **Sin auth, sin CSRF, sin captcha** — solo
403 si el request no trae User-Agent de navegador (curl pelado falla; con UA
Chrome pasa). Los 6 endpoints:
```
POST api/search_pdly.php   proyectos de ley (JSON)   → filtra ?legislatura= → SIN cap
POST api/search_pal.php    proy. acto legislativo     → idem por legislatura
POST api/search_lys.php    leyes sancionadas          → ⚠️ cap 100, NO filtra legislatura
POST api/search_actos.php  actos legislativos         → ⚠️ idem cap 100
GET  api/get_detalle_{pdly,lys,pal,actos}.php?id=N    ficha completa (HTML), IDs SECUENCIALES
```
El cap de 100 en lys/actos se rodea **enumerando IDs del detalle** (por eso el
harvester baja por id, no por búsqueda). Campos del form: pdly=`legislatura,
autor,comision,palabra_clave`; lys/actos=`palabra_clave,n_senado,n_camara`;
pal=`legislatura,autor,palabra_clave`. Legislaturas van `1990-1991`..`2025-2026`.

### `harvest.py` (stdlib pura, curl por subprocess, resumible)
Mismo patrón que `scrape_cne.py` (curl subprocess esquiva el TLS de python
3.14). **Decodifica bytes con tolerancia** (`errors='replace'`) porque algunas
fichas traen encoding mixto utf-8/latin-1 que rompe `subprocess(text=True)` —
ese era el falso "error de red" que abortaba corridas. 3 fases:
```
python3 tools/leyes-senado/harvest.py listas                    # pdly+pal por las 36 legislaturas → listas/*.json
python3 tools/leyes-senado/harvest.py detalles --workers 4      # baja fichas 1..max por id (PARALELO)
python3 tools/leyes-senado/harvest.py dataset                   # parsea HTML → JSONL + CSV por tabla
python3 tools/leyes-senado/harvest.py test                      # slice de validación
```
- **Resumible**: cada ficha bajada queda en `raw/{tabla}/{id}.html` (vacío =
  gap marcado); el resume reconstruye `pendientes` saltando lo que ya está.
- **`--workers N`**: fase detalles con `ThreadPoolExecutor` (curl subprocess
  libera el GIL). 4 obreros = ~45 min para las ~10k pdly vs horas secuencial.
  El sitio lanza errores intermitentes → cada id reintenta 3× con backoff.
  Secuencial (`--workers 1`) tiene backoff global que aborta a 40 errores
  seguidos. **Correr una 2ª pasada** al terminar recupera los ids con error
  (sin archivo → el resume los reintenta).
- `MAX_ID_DEFAULT` (medido por bisección): pdly 10100 · lys 2800 · pal 820 ·
  actos 90. Bumpear cuando el Congreso avance.

### Cobertura final (2026-07-10) + columnas
```
Bases de datos/leyes-senado/{pdly,lys,pal,actos}.{jsonl,csv}   (gitignored)
  pdly  9.919 proyectos de ley          (40 columnas)
  lys   2.475 leyes sancionadas         (11 columnas)
  pal     745 proy. acto legislativo    (34 columnas)
  actos    33 actos legislativos        (12 columnas)
```
- **pdly** (el más rico): título · números Senado/Cámara · cuatrienio ·
  legislatura · origen · tipo de ley · **autor(es) completos** · comisión ·
  fecha presentación · **ponente + fecha de aprobación de los 4 debates**
  (comisión+plenaria, Senado+Cámara) · conciliadores+fechas · **estado con
  causa legal** · + 6 filas de documentos (exposición motivos, 1ª/2ª ponencia,
  texto plenaria, conciliación, objeciones) → cada una con su **número de
  Gaceta** (`exposicion_de_motivos: "Gaceta 258/08"` + `_url`).
- **lys**: + `numero_ley` (solo en el buscador, NO en la ficha) · fecha de
  sanción · presidente del Congreso · **cross-link `_ref_id` al pdly** que la
  originó (trazabilidad proyecto→ley regalada).
- **Gotchas del parser** (`parse_detalle`): (1) autor viejo usa toggle
  `<span id='fullautor_N'>` "Ver más" → quedarse con el full; (2) `_cell_gaceta`
  debe ignorar el anchor "Ver más" y solo disparar con texto tipo "Gaceta N/YY"
  o href a imprenta.gov.co (si no, mete "Ver más" como si fuera documento);
  (3) IDs secuenciales por año → **pdly id ↑ = más reciente** (id 9540=2025-26,
  4177=2007-08), la descarga cronológica se ve en la distribución de legislaturas.

### El texto completo vive en la Imprenta (otro corpus)
Las fichas NO traen el articulado — traen el **número de Gaceta** donde está.
El texto vive en `svrpubindc.imprenta.gov.co/senado/` (**31.110 gacetas**):
- Es una app **JSF/PrimeFaces 5.2** (GlassFish, ViewState, sesión). Filtra
  SOLO por número/entidad/fecha — **NO busca dentro del texto**. La descarga
  del PDF es un *postback* con estado (`btnDescargarPdf`), no URL directa.
- **Automatizar por navegador** (extensión Chrome), no por curl: filtrar
  Número Gaceta → ir a la fila del año correcto (la col "Documento" clasifica:
  "Ponencia para Primer Debate", "Acta de Comisión"…) → click descargar. El
  PDF cae a `~/Downloads/gaceta_{N}.pdf`. Probado con Gaceta 601/2008.
- **Una gaceta es un BOLETÍN con muchos documentos** de distintos proyectos —
  no es "el PDF de un proyecto". El número de gaceta apunta a la sección.
- Gacetas 2006+ son **PDF digital** (pypdf saca texto limpio, sin OCR). Años
  90–2005 pueden venir **escaneadas** (requieren OCR: Tesseract o visión).

### Arquitectura del producto (S3 privado + DeepSeek · pendiente de construir)
```
S3 privado (leyes-senado/):
  metadata/{pdly,lys,pal,actos}.jsonl   ← el índice (chico, sube ENTERO; alimenta búsqueda/embudo/stats)
  gacetas/{num}-{año}.pdf               ← cache de PDFs SOLO los consultados (NO bulk — 31k son gigas)
  gacetas-texto/{num}-{año}.txt         ← texto extraído (pypdf digital / OCR escaneado)
  analisis-cache/{hash24}.json          ← salida DeepSeek cacheada TTL
Lambda leyes-analiza (patrón test-presidencial-explica):
  {tema|proyecto_id} → busca metadata → gacetas relevantes → baja faltantes (Imprenta)
  → extrae texto (pypdf|OCR) → DeepSeek V4 Flash → JSON {ponente,sentido,firmantes,argumentos} → cache
```
- **DeepSeek es texto, NO visión**: no "lee OCR", consume el texto que el OCR
  produzca. El OCR es paso aparte río arriba. DeepSeek V4 limpia OCR ruidoso
  (erratas, palabras cortadas) pero no recupera lo que el OCR no capturó.
- **No entrenar/fine-tune**: es extracción/lectura, zero-shot con prompt
  estructurado. ~fracciones de centavo/gaceta con V4 Flash. Una consulta tipo
  "eutanasia" = ~6 intentos × ~2-3 gacetas ≈ 5 centavos USD.

### Análisis que habilita (survival / embudo legislativo)
Los metadatos solos (sin gaceta) permiten **análisis de supervivencia** del
trámite — el foso que ni Dapper ni Sonar tienen. Hallazgos ya calculados
(sobre pdly, no recalcular a menos que cambien los datos):
- **74% de los proyectos mueren SIN llegar a primer debate** (96% presentados
  → 26% debatidos). El cementerio es el **orden del día**, no la votación.
- Solo **~28% terminan en ley**. Los que cruzan 1er debate: volado **50/50**.
- **Mortalidad por brecha entre debates** (confirma "después de X se cae"): de
  los que aprueban 1er debate en Senado, mueren el **34%** si el 2º debate
  llega ≤90 días, **60%** a 181-365 días, **85%** si tarda >1 año o nunca
  (=caso eutanasia: ponencia favorable, no se re-agenda, muere por Art. 190).
- Reframe honesto: el riesgo real es **el calendario** (fin de legislatura +
  Art. 190 Ley 5ª), no días sueltos. Modelo correcto = Kaplan-Meier con el
  reloj legislativo. Fechas necesitan limpieza (typos con brechas de 200 años).

### Temas de mujer (para MxD · [[reference_mxd_brand]] · 1990-2026)
Búsqueda por título en pdly+pal, cruzada con lys sancionadas. Hallazgos:
- **Feminicidio**: 11 intentos. La Ley 1761/2015 (Rosa Elvira Cely) **murió
  por Art. 190 en 2012 y solo pasó cuando Gloria Inés Ramírez la re-radicó en
  2013**. 7 intentos más de endurecer (2 leyes: 2356/2022, 2530/2023).
- **Paridad política**: ~5 intentos (Claudia López 2×, CNE, reformas const.),
  **CERO leyes** 2015-2025. La frontera sin conquistar — dato-bandera de MxD.
- **Derechos sexuales/reproductivos**: 9 intentos en 26 años, **CERO leyes**.
  De Piedad Córdoba (1996) a Angélica Lozano (2022) + licencia menstrual de
  V. Sandino (2021). Todo lo que avanzó (IVE) vino de la **Corte**, no del
  Congreso. Cuidado: A. Moreno Piraquive legisla el tema desde marco conservador.
- **Patrón transversal**: mueren por "Art. 190" (tiempo), no por rechazo
  (economía del cuidado 11 de 14 caídas por tiempo; maternidad 17 de 32). La
  incidencia es por **agenda**, no por convencer opositores.

### Módulo Caudal (el histórico como producto de Cauce · en construcción)

**Caudal** = el módulo de Cauce que convierte el histórico legislativo en
producto. El nombre juega la metáfora de la marca (el caudal que corre por el
Cauce = el cuerpo de datos legislativos). Vive en `tools/caudal/`.

- **`build_dataset.py`** — enriquece el crudo del harvester → `Bases de datos/
  leyes-senado/dist/`: `proyectos.jsonl` (pdly, con autores separados + gacetas
  estructuradas + resultado normalizado + etapa_max + días entre etapas),
  `actos-legis.jsonl` (pal), `leyes.jsonl` (lys con ref al proyecto),
  `indice.json` (índice compacto pdly+pal para búsqueda en memoria) y
  `stats.json` (embudo + resultados por año/comisión, precalculado).
  `resultado` ∈ {LEY, ARCHIVADO_TIEMPO, ARCHIVADO_OTRO, RETIRADO, EN_TRAMITE, OTRO}.
- **`caudal_core.py`** — motor de consulta puro (sin AWS; lee local `dist/`, la
  Lambda inyectará los mismos JSON desde S3). API: `buscar(query, filtros)`,
  `resumen_tema(query)` (embudo + survival + top autores + línea de intentos),
  `proyecto(id)` (ficha + punteros de gaceta para la fase DeepSeek). Trae un
  **stemmer ligero** (`_stem`) que tolera erratas del propio Congreso — p.ej.
  "feminicidio" matchea el título con errata "FEMINICIDO" vía la raíz "feminicid".
- **`normalize_autores.py`** — normalización de autores (LISTO). El campo `autor`
  del Senado es un desastre: variantes por tilde/mojibake ("Iván"/"Ivan"/"Ivã¡N"),
  ruido ("Otros"/"Y Otros"), y radicaciones del Ejecutivo con listas de gabinete.
  Resuelve por **clave canónica** (sin tildes + MAYÚSCULAS + solo alfanum) que
  colapsa variantes exactas-módulo-acentos; **display** = variante más acentuada
  entre las frecuentes; descarta ruido; clasifica institucionales (Gobierno,
  Defensor, Fiscal…). Resultado: **9.156 → 6.354 personas canónicas + 9 entidades**;
  1.321 proyectos marcados `autor_tipo=institucional` (Gobierno Nacional).
  `build_dataset.py` lo integra: cada registro trae `autores` (display), `autores_keys`
  (para el join a partido) y `autor_tipo`; emite `dist/autores.json` (registro
  6.354 personas). **NO hace fuzzy-subset** ("Gloria Ramírez" vs "Gloria Ramírez Ríos"
  quedan separados) — conservador a propósito; refinable después.
- **`build_roster.py`** — join autor→partido/bancada (LISTO · **70% ponderado por
  proyectos**, jul-2026). Los autores de proyectos SON congresistas electos → aparecen
  en los resultados de Congreso con su partido. Extrae cada candidato→partido de GCS
  2014/2018/2022 + preconteo 2026 (`DES_CAN`→`DES_PAR`), canoniza con la MISMA
  clave de `normalize_autores`, y une contra `autores.json`. **Matching:** exacto
  primero, luego **subconjunto de tokens** (el padrón usa el nombre legal completo
  "PALOMA SUSANA VALENCIA LASERNA" vs el autor "PALOMA VALENCIA LASERNA" — el
  segundo nombre rompía el exacto; subset con ≥3 tokens lo arregla sin falsos
  positivos). `MANUAL` = override curado (~33) para prolíficos fuera del join, por
  pre-2014 O por fragmentación de nombre (2 tokens no subset-matchean: Paloma
  Valencia, Nadia Blel, Efraín Cepeda…). Solo afiliación de alta confianza;
  switchers/ambiguos deliberadamente fuera (Benedetti, Moreno de Caro, Vélez Uribe,
  Clopatofsky, Araújo). Se supera cuando la RNEC entregue los GCS_*CON pre-2014.
  Tras editar `MANUAL`: `build_roster.py --reuse` → subir `dist/autor-partido.json` a
  `s3://caudal-legislativo/metadata/` → reciclar la Lambda (`update-function-code`,
  el `_caudal()` recarga el autor-partido en contenedor frío).
  Salidas: `dist/roster-autores.json` (8.883 congresistas) + `dist/autor-partido.json`
  (clave autor→partido). `--reuse` evita re-escanear los 4GB de GCS. **Límite:** solo
  hay Congreso desde 2014 → los misses son casi todos pre-2014. El motor
  (`resumen_tema`) agrega `bancadas` (qué partidos impulsan el tema) + cobertura; la
  ficha de `proyecto` trae partido por autor; la síntesis LLM lo usa ("transversal vs
  un bloque"). `indice.json` ganó campo `ak` (autores_keys top 6) para el join.
- **S3 privado**: bucket dedicado **`caudal-legislativo`** (decisión: bucket
  aparte, NO prefijo en `elecciones-2026`, cuyo `bases de datos/*` es público).
  `ricardo-mac-cli` está scoped a `elecciones-2026` → **no puede crear el bucket
  ni el IAM**: eso lo corre el usuario con admin. Snippet listo en
  `tools/caudal/setup-s3-privado.md` (create-bucket + block-public-access +
  encryption + `iam-caudal-rw.json` para dar rw a la CLI). Estructura de llaves:
  `metadata/{proyectos,leyes,indice,stats}` · `raw/*` · `gacetas/{num}-{año}.pdf`
  · `gacetas-texto/*` · `analisis-cache/{hash}.json`. **Frontend NO lee el bucket
  directo — habla con la Lambda.**

**Estado (2026-07-11) · LISTO y en producción — handoff:**
- 🔗 **En vivo:** `https://ricardoruiz.co/caudal.html` (gated, whitelist `reruizc@gmail.com`;
  card en `dashboard.html` grupo encargos). GitHub Pages desde main.
- ✅ Histórico cosechado (13.172 registros, 1990-2026) → `Bases de datos/leyes-senado/`.
- ✅ Dataset enriquecido (`build_dataset.py` → `dist/`) + **autores normalizados**
  (`normalize_autores.py`, 6.354 personas) + **join autor→partido** (`build_roster.py`,
  67% ponderado) → `autor-partido.json` → bancadas por tema.
- ✅ **Bucket privado `caudal-legislativo`** (403 anónimo) con `metadata/*` + `gacetas-texto/*`.
- ✅ **Lambda `caudal-analiza`** desplegada (`POST https://l3kmprdjkl.execute-api.us-east-1.amazonaws.com`),
  model-agnostic (DeepSeek V4 default, switch a Claude por env var), `DEEPSEEK_API_KEY` seteada.
  Acciones: `tema` (embudo+bancadas+intención+lectura LLM) · `buscar` (filtros tipologia/empuje) ·
  `proyecto` (ficha + bloqueo + votaciones) · `stats` · `bloqueo` (sistema P(tratado|posición)) ·
  `gaceta` (acta/ponencia · aplazamiento+voto nominal) · `contexto` (rastreo de medios · Serper+DeepSeek).
- ✅ **Frontend `caudal.html`** (sistema visual v2: Helvetica, azul #060810) con búsqueda,
  embudo, bancadas, lectura del analista y ficha con análisis de ponencia por IA.
- ✅ **Fase 3 piloto** verificado (Gaceta 857/2013 feminicidio → ponente/sentido/argumentos).
- ✅ **Fase 1 · lectura de intención** (2026-07-11 · todo desde metadata, sin fuente nueva).
  `tools/caudal/clasificar.py` deriva por proyecto: **tipología** (honores/fondos/reforma/
  presupuestal/ordinaria + banderas `crea_fondo`, `jala_presupuesto_regional`), **empuje/
  vitrina** (clusters de re-radicación por firma de título — tokens significativos + números
  para no colapsar reformas de artículos distintos; `vitrina` = re-radicado ≥2 términos sin
  superar 1er debate, umbral tuneable `VITRINA_MIN_VECES`), **autoría real** (1º firmante =
  autor, resto firmones; EXCEPCIÓN actos legislativos ≥8 firmas = coautoría colectiva real),
  **reloj por tipo** (AL 1 año/8 debates vs ordinaria 2 legisl/4). `build_dataset.py` lo cablea
  y emite los campos a `proyectos.jsonl`/`actos-legis.jsonl`/`indice.json` (`tip/emp/vs/vp/ap`)
  + stats (`tipologia`, `empuje`, `mortandad_por_anio_cuatrienio` → año 4 muere 34.7% vs ~26%).
  `caudal_core.py` los expone en `resumen_tema` (desglose + n_vitrina) y `proyecto` (autoría,
  historial de re-radicación). Frontend: chips de intención **clickeables que filtran** la
  línea de intentos + ficha con autor principal ★, reloj e historial.
- ✅ **Rastreo de medios contextual** (acción `contexto` del Lambda). Botón en la ficha →
  **Serper.dev** (Google, `gl=co`, secreto `SERPER_API_KEY`, 2.5k gratis) busca prensa del
  proyecto → DeepSeek interpreta titulares → `{tuvo_controversia, nivel, quien_se_opuso,
  murio_por_impopularidad, veredicto}` + fuentes REALES (URLs de Serper, no del LLM). Cache
  S3 `analisis-cache/contexto-{hash}`. Sirve para explicar muertes "por tiempo" que en
  realidad fueron impopularidad/bloqueo de gremio. Cobertura buena ~2015+, pobre pre-2010
  (dice "sin señal" honesto). `PROMPT_VERSION='v4'`. Verificado en vivo (caso Uber →
  controversia alta, impopularidad probable, 8 fuentes).
- ✅ **Fase 3 · Índice de bloqueo** (2026-07-12/13). Herramientas en `tools/caudal/actas/`.
  Responde el foso que ni Dapper ni Sonar tienen: **agendado N× vs debatido/aplazado/votado**.
  - **Agendamientos** (`harvest_ordenes.py`): Cámara **wp-json** `/wp/v2/evento?comision_evento=<id>&evento_tipo=185`
    (órdenes del día, PDF de descarga directa, sin JSF). Barrió las **14 comisiones** (term ids en
    `COMISIONES`, Primera=183; `harvest_ordenes.py todas`). PDFs digitales → texto → nº de proyecto
    agendado por sesión (regex bloque "Proyecto de Ley No. N de AAAA Cámara «título»"). Corta en
    "Anuncio de proyectos" para que la POSICIÓN sea la de la cola de debate. Cache en
    `Bases de datos/leyes-senado/actas/ordenes/{com}/` (gitignored, ~1.1GB solo texto+pdf).
  - **Análisis** (`analiza_bloqueo.py` por comisión · `analiza_nacional.py` agrega): proxy "tratado"=
    no reaparece la sesión siguiente (gap≤45d). Hallazgos: **P(tratado|posición) 1º≈53% → 4º-6º≈21%**
    (el orden de la agenda decide); mediana 5 agendamientos; **hazard de parar más alto al inicio**
    (1º-2º) → los que sobreviven entran en "purgatorio" (re-agendar rinde ~21%). Solo cuenta proyectos
    con ≥2 agendamientos (los one-off contaminan). El 16º+ tiene composición mixta (agendas largas).
  - **Outcome histórico** (`harvest_votaciones.py`): **Congreso Visible** (Uniandes) — su web Next.js
    trae las votaciones server-rendered en `__NEXT_DATA__`. `…/votaciones/?rows=10300` devuelve las
    **10.205** de una (87MB, ~40s, 2006→**nov-2022**). Cada una linkea a proyecto (numero_camara Y
    senado), con `motivo` (aplazamientos/archivos), votos, `acta`, `urlGaceta`, `observaciones`
    (relato con quién propuso archivo + tally). → `votaciones.json` (1.627 proyectos, 260 aplazamientos).
    El voto nominal por congresista está en el detalle `/votaciones/{id}/` (pendiente, bajo demanda).
  - **Datos a S3** (`build_bloqueo_s3.py` → `metadata/bloqueo.json` sistema+lookup · `votaciones.json`).
    Lambda: acciones `bloqueo` (sistema para el landing) + enriquece `proyecto` con `bloqueo` (match
    nº Cámara) y `votaciones` (match Senado/Cámara). Frontend: panel ámbar "Bloqueo en comisión"
    (agendado N×, posición) + panel azul "Trámite · debates y votaciones" (aplazamientos + tally) +
    gráfica P(tratado|posición) en el landing.
  - **Descarga de gacetas por CURL — RESUELTO (jul-2026, `descargar_gaceta.py`).** La nota vieja
    ("NO bulk automatizable, clic a clic") **quedó obsoleta**: el portal de la Imprenta SÍ se
    automatiza. El deep-link `index2.xhtml?ent=Senado|Camara&fec=D-M-YYYY&num=NNN` (que sale del
    botón "Ver Link PDF" del portal) renderiza una página que al cargar hace un postback PrimeFaces
    (`pdfIr`) que devuelve el PDF. Reproducible en 2 pasos: **(1)** GET del deep-link con cookie jar
    → captura `jsessionid` (cookie) + `javax.faces.ViewState` (en el HTML); **(2)** POST a
    `index2.xhtml;jsessionid=…` con `dldFile=dldFile` + `pdfIr=pdfIr` + `javax.faces.ViewState=…`
    → `Content-Type: application/pdf`. `tools/caudal/actas/descargar_gaceta.py <Senado|Camara>
    <D-M-YYYY> <num>` lo encapsula (guarda `gaceta_{num}_{año}.pdf` en `gacetas/`). El único input
    es `(ent, fec, num)`; el `fec` EXACTO sale del portal al filtrar por número (col Fecha Gaceta).
    Verificado: reforma laboral 870/2025 (67 MB, 175 pág) y acta comisión 1942/2025 bajadas por curl.
  - **Encontrar actas:** el filtro **Documento="acta de plenaria"** del portal devuelve ~2.549
    (aunque la columna Documento se vea vacía en la lista, el filtro SÍ matchea el tipo interno). El
    match es fuzzy (1942 salió como "actas de comisión" bajo ese filtro). `procesar_gacetas.py` toma
    el folder `gacetas/` como cola → clasifica acta/ponencia → sube texto a `gacetas-texto/{n-año}.txt`
    (`extraer_gaceta.py <pdf> <key>` sube una sola). **Ponencias** → sentido/ponentes/argumentos;
    **actas** → la acción `gaceta` extrae aplazamiento + votación + **nominal** (`PROMPT_VERSION='v6'`).
    **VOTO NOMINAL PROBADO (jul-2026):** acta de plenaria **1069/2019** (Senado, auto-descargada) →
    la Lambda extrajo el roll-call de **84 senadores** (informe de conciliación, 83 Sí / 1 No, cada
    uno con su voto: Roy Barreras, Nadya Blel, Aída Avella, David Barguil, Wilson Arias…). También
    ponencia 870/2025 (reforma laboral) → favorable · Aída Avella · 6 args.
  - **Ventana inteligente para actas largas (`_ventana`):** las actas de plenaria (300k-700k chars)
    ponen el roll-call DESPUÉS del preámbulo (asistencia/quórum), lejos de los primeros 60k. `_ventana`
    centra la ventana de 60k en la votación relevante: ancla en palabras distintivas del contexto
    (≥8 chars, saltando ubicuas como proyecto/senado/plenaria) y, si no, en la primera "votación
    nominal". **NO ancla en números sueltos** (un nº de proyecto aparece en cualquier parte del acta y
    manda la ventana a un lugar sin voto — bug corregido). Para ver el nominal de un proyecto concreto,
    el `contexto` (nº + título del proyecto votado en esa sesión) enfoca su votación.
  - **Cómo cazar actas con nominal:** portal Documento="acta de plenaria" + Entidad=Senado → las que
    traen "Acta de Plenaria" EXPLÍCITO en la columna (3 botones) son las confirmadas (p.ej. Senado
    2019: 1147, 1069, 1068, 1067, 1066, 992, 970, 969). El roll-call va como "Por el Sí: N Por el No: M
    … Honorables Senadores por el SÍ: [Apellidos Nombres] …". **Gotcha:** no toda acta trae roll-call —
    muchas votan por unanimidad/agregado (la 1942/2025 comisión salió sin nominal).
    **Gotcha de targeting — RESUELTO para Cámara, sigue abierto para Senado** (ver bloque
    "Fase 3 · voto nominal de Cámara" más abajo): Cámara tiene su propio índice público
    sesión→acta→gaceta que hace innecesario adivinar. Senado sigue sin fuente limpia
    equivalente → sus actas 2023-2026 quedan **on-demand** (opción B).
- 🔜 **Pendiente (Fase 3):** targeting de actas de **Senado** (sin fuente limpia todavía,
  a diferencia de Cámara) · voto MANUAL de Cámara ago-2021/sep-2022 (columna "X" sin texto,
  necesita extracción por coordenadas tipo pdfplumber) · OCR de actas/gacetas escaneadas
  pre-nov-2020 · voto nominal por congresista del detalle de Congreso Visible (Senado
  pre-2022) · refinar títulos de agendamientos (71%→100%). NADA bloquea el pitch — el
  módulo se demuestra completo. Ver `[[reference_actas_bloqueo_fuentes]]` en memoria.

**Fase 3 · voto nominal de Cámara — RESUELTO (jul-2026 · `tools/caudal/actas/`).** Cierra
el hueco de "voto nominal cuatrienio actual" que había quedado on-demand: se encontró que
`camara.gov.co/secretaria-general/actas-votaciones-y-otros/` esconde un widget AJAX
(`admin-ajax.php`, `action=get_actas_y_otros_page`, nonce público de 24h leído del HTML,
`comision=Secretaría General`) que es **el índice sesión→acta→gaceta que el portal JSF de
la Imprenta no da** — y de regalo, cada acta trae un `enlace` de descarga DIRECTA (sin JSF,
sin postback) al ZIP/PDF de esa sesión.
- **Cobertura verificada:** 1.400 actas de plenaria 2010-2026 en el índice (140 páginas ×10,
  `per_page` configurable). El `enlace` cambia de formato con los años, pero **NO hay un
  corte limpio por fecha** — el mismo tipo de documento aparece como texto nativo un año y
  como imagen escaneada el siguiente (verificado: 2013 sí trae texto nativo, 2014-2017 no,
  pese a ser el mismo formato de documento) → **detección por CONTENIDO en cada PDF**, tres
  formatos:
  - **consolidado** (~oct-2022 en adelante): 1 PDF "Registro de Asistencia y Votación
    Electrónica" con TODAS las votaciones de la sesión, bloques `VOTACION N` + tabla nominal
    con nombre completo (Apellidos Nombres) — alta confianza, sin OCR.
  - **fragmentado_electronico** (~nov-2020 a ~sep-2022): 1 PDF por votación, votantes
    identificados por **email** (`nombre.apellido@camara.gov.co`) con Sí/No/Abstención como
    texto explícito → parseable.
  - **manual_tabla** (intermitente ~2011-2020, y también la 2ª sección "REGISTRO MANUAL PARA
    VOTACIONES" que trae el mismo PDF de `fragmentado_electronico`): tabla No./Nombre/
    Circunscripción/Partido/SI/NO con una **"X" posicional** bajo la columna que corresponde
    (no es texto — pypdf linealiza y pierde la columna). Resuelto con
    **`pdfplumber.extract_table()`**, que reconstruye filas/columnas por coordenadas y
    devuelve las celdas ya separadas — no hace falta calcular posiciones a mano. Confirmado
    en muestreo (56 actas sin parsear 2010-2020): ~20% traían esta tabla con texto nativo,
    rescatables sin gastar en OCR.
- **Pipeline:** `harvest_actas_plenaria_camara.py index` (baja el índice completo,
  paginado) → `harvest_actas_plenaria_camara.py download --workers N` (descarga resumible
  de los 1.400 `enlace`, cache por id) → `parse_votaciones_camara.py` (extrae texto con
  pypdf, autodetecta el formato por contenido — regex de bloques `VOTACION N` / filas con
  email / `REGISTRO MANUAL PARA VOTACIONES` vía pdfplumber —, cruza cada votante contra
  `dist/roster-autores.json` por **subconjunto de tokens** —mismo algoritmo de
  `build_roster.py`, funciona pese al orden Apellido-Apellido-Nombre-Nombre de las actas vs
  Nombre-Nombre-Apellido-Apellido del roster— y vincula el nombre de la votación
  (`PL.NNN/YY`) contra `numero_camara` de `proyectos.jsonl` con el mismo `PROJ_RE` de
  `harvest_ordenes.py`).
- **Resultado final (2026-07-15):** **445 actas parseadas** (de 1.400 · el resto cae en
  imagen sin texto — requiere OCR, no procesado —, o formatos `.rar`/`.docx`/`.doc` de
  2011-2014 sin soportar), rango **2020-11-12 → 2026-06-17**, **3.956 votaciones · 317.455
  votos individuales · 90,3% con partido asignado**. Outputs LOCALES (gitignored, NO
  subidos a S3 todavía — pendiente luz verde):
  `Bases de datos/leyes-senado/actas/plenaria-camara/{index,raw,parsed}/` +
  `Bases de datos/leyes-senado/dist/{votaciones-camara-nominal.jsonl,votaciones-camara-stats.json}`.
  Piloto de OCR (`tools/caudal/actas/ocr_pilot.py`, Tesseract+pymupdf, ambos instalados
  vía `brew install tesseract-lang` + `pip install --break-system-packages pymupdf
  pytesseract`) confirmó que el rango pre-2011 SÍ es OCR-eable (nombres reales salen
  legibles) pero no se ha corrido en masa — queda como pendiente explícito, ya no
  bloqueado por falta de piloto.
- **Validado cruzado** contra [Congreso a la mano](https://congresoalamano.elespectador.com)
  (El Espectador): Barguil "Sí" en reforma tributaria y "No" sostenido en reforma a la salud
  coincide en ambas fuentes. Esa herramienta externa **no tiene registrada la reforma
  laboral** para los congresistas probados — nuestro pipeline sí, con el detalle completo de
  cada artículo + la conciliación final, una ventaja real sobre la competencia editorial.
- **EXPUESTO EN PRODUCCIÓN (jul-2026 · con luz verde de Ricardo):** el voto nominal
  ya es producto vivo en Caudal, por dos ejes:
  - **Por proyecto** — `tools/caudal/build_votaciones_camara_s3.py` →
    `metadata/votaciones-camara-nominal.json` (por proyecto: tally + desglose por
    bancada + lista nominal con `k`=roster_key). La acción `proyecto` de la Lambda
    inyecta `voto_nominal` (aditivo). En la ficha: bloque "Voto nominal" con cada
    votación expandible al nominal por congresista.
  - **Por congresista** — `tools/caudal/build_congresista_s3.py` →
    `metadata/votaciones-camara-congresista.json` (keyed por roster_key: bancada +
    resumen + `alineacion_gob` [% con Pacto en votaciones CONTESTADAS, min lado ≥15%]
    + `por_proyecto` con su Sí/No/Abst por proyecto e `id` para click-through).
    Nueva acción Lambda `congresista` (resuelve `{key}` exacto o `{q}`/`{nombre}` por
    subconjunto de tokens; si es ambiguo devuelve `candidatos` para desambiguar).
    Frontend: buscador "¿cómo votó un representante?" en la vista Congreso + nombres
    del nominal y autores clickeables → ficha del congresista (alineación + récord
    por proyecto con barras Sí/No). Verificado con Barguil (66% alineación, 600 votos).
  - **Fix de linking clave** (parse_votaciones_camara): `PROJ_RE` usaba `\b` final
    que fallaba con el sufijo de cámara pegado (`166/23C`); + `PROJ_DASH_RE` para el
    formato con guion y año de 4 dígitos (`118-2022`); + `_norm_proj` normaliza el año
    a 2 dígitos. Cobertura de votos ligados a proyecto **17% → 43%** (135.293 votos,
    328 proyectos). Re-linkear tras un cambio: leer el jsonl, re-aplicar `link_proyecto`
    con `load_numero_camara_map`, reescribir (no hace falta re-parsear PDFs).
  - **Regenerar/redeploy:** `build_votaciones_camara_s3.py` + `build_congresista_s3.py`
    → `aws s3 cp … s3://caudal-legislativo/metadata/` → `build_zip.py` +
    `update-function-code` (la Lambda recarga los JSON en contenedor frío; para forzar
    el recycle, re-deploy). Los dos JSON viven local en `dist/s3/` (gitignored).
  - **Hogar futuro de la ficha-persona:** `analisis-candidato.html` (foto/mapa/score/
    histórico electoral) es la ficha rica; los perfiles de Congreso **2018 y 2026 ya
    están ahí** (ver sección analisis-candidato) → falta solo CABLEAR el panel "cómo
    votó" llamando a la MISMA acción `congresista` (join por nombre → roster_key, que
    la Lambda ya resuelve). Caudal es el hogar actual.
- **Pendiente de voto (backlog, en orden de valor):**
  1. **Congreso 2022 en analisis-candidato** (`GCS_2022CON.csv`) — no es voto, pero es
     el término 2022-2026 = el mismo que cubre nuestro nominal. Sin él el join queda
     cojo. Ver el handoff de la sección analisis-candidato.
  2. **Cablear el panel "cómo votó"** en la ficha (acción Lambda ya lista).
  3. **Senado** — bloqueado por fuente (no hay export electrónico ni índice limpio;
     solo targeted vía Gaceta, ver abajo).
  4. **OCR Cámara pre-2020** (~928 actas imagen en disco, piloto Tesseract listo).
  5. **Disciplina de bancada** como vista propia (la alineación ya se mide por persona
     y por bancada; falta exponerla agregada). Coaliciones sigue PAUSADO por decisión.

**Fase 3 · voto nominal de SENADO — investigación en curso, sin resolver (jul-2026).**
Se buscó un equivalente al AJAX de Cámara. `senado.gov.co` es Joomla (no WordPress) — sin
`admin-ajax.php`. Se encontró `secretariasenado.gov.co` (subsitio Joomla separado, también
Secretaría General, con contenido spam SEO inyectado en el menú/footer — enlaces a sitios
porno, vulnerabilidad Joomla clásica, **NO es cosa nuestra arreglarlo**, solo hay que
ignorar esos links al scrapear) con una jerarquía real de carpetas DOCman:
`/cuatrienio-2022-2026/legislatura-YYYY-YYYY/plenarias-N/mes/día-de-la-semana-DD-de-mes-de-AAAA/
{impedimentos|constancias|proposiciones|proyectos-de-ley}` — y dentro de "proyectos de ley",
una subcarpeta por proyecto (`pl-NNN-de-AAAA-senado-MMM-de-AAAA-camara`) con un archivo por
documento (`P-NNN-ART-NNN-...pdf`, `CT-NNN-...pdf`).
- **Gotcha de scraping:** curl simple con regex no encontró los archivos — el listado SÍ es
  server-rendered (no hace falta JS/AJAX, confirmado con el navegador), el problema fue que
  el texto de cada `<a>` va envuelto en spans anidados (`koowa_header__item` de Joomla/Koowa)
  que mi regex simple no capturaba. Usar el navegador (o un parser HTML real, no regex) para
  extraer los links.
- **Lo que SÍ hay:** carpetas con contenido real, confirmado en 2 cuatrienios (2018-2022 y
  2022-2026), URLs amigables terminadas en `/file` que curl descarga directo sin JSF ni
  postback (mismo patrón fácil que Cámara).
- **Lo que falta (el problema real):** los archivos que se revisaron (`P-045-ART 139...`,
  `P-040-ART 132...`, `CT-009...`) son **documentos de TRÁMITE** (texto de la proposición +
  justificación, o escaneo de la constancia) — **ninguno trae tabla de voto nominal**. A
  diferencia de Cámara (que exporta un "Registro de Asistencia y Votación Electrónica"
  consolidado por sesión), Senado parece guardar aquí solo el papeleo, no el resultado del
  conteo. No se encontró todavía el equivalente al export Bosch/DCN-SW de Cámara — si existe,
  puede vivir en otra sección del sitio, o Senado puede simplemente no tener un sistema de
  voto electrónico exportable como el de Cámara (mociones nominales se piden caso a caso y
  quedan solo en la Gaceta/acta narrativa).
- **Conclusión del 2º intento (jul-2026):** la sección `área-legislativa/seccion-de-relatoria`
  de senado.gov.co (donde viven las actas) **remite todo a la Gaceta del Congreso** — el
  Senado **NO tiene un export electrónico de votación equivalente al Bosch/DCN-SW de Cámara**.
  Sus votos nominales quedan en el ACTA NARRATIVA publicada en la Gaceta (formato "Por el Sí:
  N … Honorables Senadores por el SÍ: [apellidos]", como el acta 1069/2019 con 84 senadores
  que ya extrajimos). El árbol DOCman de secretariasenado.gov.co solo guarda trámite.
- **3er intento — portal Imprenta scriptable pero filtro inservible (jul-2026 · `harvest_actas_plenaria_senado.py`):**
  Se crackeó la MECÁNICA del buscador JSF de la Imprenta (dataTable PrimeFaces lazy, 31k
  gacetas): el POST parcial de filtro (Entidad="Senado de la República" + `_filtering=true`)
  y de paginación (`_pagination=true`+`_first`, fecha DESC) SÍ se scriptan por curl. **PERO
  el filtro no sirve para aislar las actas de plenaria con voto nominal:** (a) la columna
  "Documento" se renderiza VACÍA en el listado → solo hay (num, entidad, fecha), sin tipo;
  (b) el filtro Documento es FUZZY — `plenaria` devuelve mayormente PONENCIAS/órdenes del día,
  y `acta de plenaria` devuelve hasta gacetas de "ACTAS DE COMISIÓN" (verificado: gaceta
  787/2026 sale de primera con ese filtro y es comisión, 0 roll-call). No existe un filtro
  que dé limpio las actas de sesión. Clasificar acta-vs-ponencia-vs-comisión exige DESCARGAR
  y leer el masthead de la página 1 ("ACTAS DE PLENARIA" vs "ACTAS DE COMISIÓN" vs "PONENCIAS").
- **Conclusión definitiva para Senado:** no hay atajo tipo Cámara. La vía realista es
  **TARGETED, no bulk**: para un voto concreto (reforma X, senador Y) → conocer la FECHA de
  sesión → bajar las gacetas candidatas de esa ventana con `descargar_gaceta.py` → quedarse
  con la de masthead "ACTAS DE PLENARIA" que traiga "Por el Sí"/"Honorables Senadores" →
  parsear con la acción `gaceta` del Lambda → cruzar con `electos-2026-2030.json`. Un harvest
  exhaustivo (bajar cientos de gacetas grandes y clasificarlas por masthead) es caro y ruidoso;
  para preguntas puntuales, Congreso a la mano ya da el cross-check. **Se cierra esta línea de
  investigación** — el mecanismo queda scriptado en `harvest_actas_plenaria_senado.py` (con
  docstring que documenta el límite) por si se quiere el targeted más adelante.
- **Reglas:** deploy = `git push origin HEAD:main`. Redeploy Lambda:
  `python3 tools/caudal/lambda/build_zip.py && aws lambda update-function-code --function-name caudal-analiza --zip-file fileb://tools/caudal/lambda/caudal-analiza.zip`.
  Regenerar dataset: `harvest.py dataset` → `build_dataset.py` → `build_roster.py --reuse`
  → subir `dist/*` a `s3://caudal-legislativo/metadata/`.

**Lambda `caudal-analiza` (LISTO · data path)** — `tools/caudal/lambda/`:
- `lambda_handler.py` envuelve `caudal_core` (inyecta índice/registros desde S3, no
  usa `from_local`) + capa de síntesis LLM. Acciones POST JSON: `tema` (embudo +
  supervivencia + autores + `lectura` LLM opcional), `buscar` (lista del índice),
  `proyecto` (ficha + punteros de gaceta). `build_zip.py` empaqueta handler +
  `caudal_core.py` CANÓNICO (sin drift). Guía completa en `setup-lambda.md`.
- **Desplegada:** función `caudal-analiza` (python3.13, rol `lambda-caudal-analiza`
  con AWSLambdaBasicExecutionRole + inline `caudal-s3`). **API pública:**
  `POST https://l3kmprdjkl.execute-api.us-east-1.amazonaws.com` (HTTP API, CORS `*`).
  Gotcha: `apigatewayv2 create-api --target` NO agrega el permiso de invocación →
  hay que `lambda add-permission` a mano (si no, 500 con el Lambda corriendo limpio).
- **Model-agnostic:** `STEP_MODELS` con provider/model por env var
  (`CAUDAL_SINTESIS_PROVIDER/MODEL`, default `deepseek`/`deepseek-v4-flash`). El
  switch a Claude para la síntesis es cambiar env vars a `anthropic`/`claude-sonnet-5`
  + setear `ANTHROPIC_API_KEY` — cero código (el handler ya tiene `_call_anthropic`).
  Razón (decisión 2026-07-11): extracción de gaceta = alto volumen, dato en el texto
  → DeepSeek barato; síntesis del memo = bajo volumen, alto valor → candidata a Claude.
- **✅ `DEEPSEEK_API_KEY` seteada (2026-07-11) → síntesis viva.** La lectura de un
  tema (feminicidio) volvió en ~12s, tuteo neutro, anclada solo en los datos.
- **Gotcha de max_tokens (mismo que test-presidencial):** DeepSeek V4 gasta tokens en
  reasoning y con presupuesto bajo deja `content` vacío (`finish_reason=length`). La
  síntesis usa `max_tokens=6000`; NO bajarlo. El handler además limpia fences ```json.
- Cache de síntesis en `analisis-cache/{hash24}.json`, TTL vía `PROMPT_VERSION`
  (va en `v2`). No cachea respuestas con error.

**Frontend `caudal.html` (LISTO · gated · en producción)** — es el **HOME paraguas**
(ver "Arquitectura Caudal · paraguas vs pilares"): hero "El Estado, leído", búsqueda
universal y grilla de 9 pilares. Lo que sigue en esta ficha describe la **vista
Congreso** (`view-congreso`), uno de los pilares. Página privada en la raíz,
sistema visual v2 (Helvetica embebida, fondo `#060810`, acento teal, azul `#0047FF`,
cursor custom, `noindex,nofollow`). Gate calcado de proyecto-dc: `rr-token`/`rr-user`
+ whitelist **`['reruizc@gmail.com','nuevagemela@gmail.com']`** (Nury Gómez agregada
jul-2026) + verificación contra `rr-auth /auth/me`. Card en `dashboard.html`

**Acceso de invitado a Caudal (link/QR sin registro · jul-2026).** Para mostrarle
Caudal a socios (Cauce) sin crearles cuenta: `?acceso=<token>` en la URL. El token
**NO vive en el HTML** (sería un secreto público e irrevocable en un repo abierto);
vive en el KV del worker y `checkShareAccess()` lo valida contra
**`GET /caudal/guest?token=`** de `rr-auth` (responde `{ok:true, valid:bool}`; no
expone la lista de tokens). Falla cerrado: si el worker no responde o el token no
está, cae al gate normal. En modo invitado la nav muestra "Vista de invitado" (sin
Volver/Salir, que no aplican sin cuenta).
```bash
# sembrar un token (TTL en segundos · 2592000 = 30 días)
TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(18))")
cd /Users/ricardoruiz/rr-auth && npx wrangler kv key put "caudal-guest:$TOKEN" "cauce" \
  --binding=RR_STORE --remote --ttl=2592000        # ⚠ el flag es --ttl, NO --expiration-ttl
# revocar antes de tiempo
npx wrangler kv key delete "caudal-guest:$TOKEN" --binding=RR_STORE --remote
```
El `get` puede dar 404 unos segundos tras el `put` (consistencia eventual del KV) —
reintentar antes de asumir que falló. QR del link: `Bases de datos/caudal-acceso/`
(gitignored, generado con segno — vive en python3.11, no en el python3 default).
PRIVATE_TOOLS (grupo encargos). **Nav v2 estándar del sitio**: izq Volver+Privado+Salir,
centro "Caudal", der logo Ricardo.Ruiz (Syne + barras, cargado por Google Fonts, igual a
index.html). **Rediseño UX jul-2026:**
- **Landing pre-búsqueda** (acción `stats`+`bloqueo`): totales del histórico (proyectos de
  ley/actos/leyes/vitrina) + mortandad por año de cuatrienio + gráfica **P(tratado|posición)**.
- **Vista de tema**: KPIs · tira de intención (chips **filtrables** por empuje/tipología + ⓘ
  tooltip que explica cada categoría) · lectura del analista (LLM, pre-fetch) · **embudo
  escalonado** con % de supervivencia + ⓘ · 4 gráficas (**intentos por año** [agrupa por
  lustros cuando >15 años, sueltos '23-'26] · composición tipología+empuje · **éxito por
  comisión** [fusiona duplicados por casing SEPTIMA/Septima] · mortandad) · bancadas · **línea
  de intentos** con títulos LEGIBLES (sin "POR MEDIO DE LA CUAL SE") + tipo PL/AL + badges.
- **Búsqueda estricta + aviso de ampliar**: si trae pocos, "También hay N con «pensional» —
  ver todos" (backend calcula el término más distintivo).
- **Ficha (modal)**: autor real vs firmones (★, actos legislativos=coautoría colectiva) · tipología ·
  reloj por tipo · re-radicaciones · **panel Bloqueo en comisión** (agendado N×, posición) ·
  **panel Trámite/votaciones** (aplazamientos+tally de Congreso Visible) · **botón Rastreo en medios**
  (Serper, con aviso <2010) · botón analizar ponencia/acta (DeepSeek).
- JS validado con `new Function` antes de cada push (regla del proyecto). Todo desplegado.

**Fase 3 · texto de gaceta (PILOTO LISTO · verificado end-to-end):** loop
completo probado con feminicidio. (1) **Descarga** semi-manual del portal JSF de
la Imprenta **vía Chrome** (la extensión Claude in Chrome; el navegador in-app es
Safari-sandbox y **aborta descargas a disco** — [[feedback_announce_browser_use]]).
Filtrar Número Gaceta → fila del año correcto (columna "Documento" clasifica:
"Informe de Ponencia Para Primer debate"…) → botón descargar (Chrome baja auto a
`~/Downloads`). **Gotcha macOS:** Bash NO puede leer `~/Downloads` (TCC lo bloquea,
"Operation not permitted" incluso con sandbox off) → mover el PDF a la carpeta del
repo. (2) **`tools/caudal/extraer_gaceta.py <pdf> <key>`**: pypdf → texto → sube a
`s3://caudal-legislativo/gacetas-texto/{num-año}.txt` (digital 2006+ limpio; viejos
requieren OCR aparte). (3) **Lambda acción `gaceta`** (`{action:"gaceta",key,contexto}`):
lee el texto de S3, DeepSeek paso `extraccion` (max_tokens 6000) → `{tipo_documento,
ponentes, sentido, sentido_detalle, argumentos, en_contra}`, cache en
`analisis-cache/gaceta-{hash}.json`. **Clave:** una gaceta es un BOLETÍN con varias
ponencias; el `contexto` (número+título del proyecto) hace que DeepSeek aísle el
documento correcto. Probado: Gaceta 857/2013 (boletín con proyectos 86/107/15/22)
→ extrajo la ponencia del 107/2013 (feminicidio): sentido favorable, ponente Doris
Clemencia Vega Quiroz, 5 argumentos reales. Los PDFs locales van a `Bases de datos/
leyes-senado/gacetas/` (gitignored; no guardamos PDFs en prod, solo el texto en S3).

**Ficha del frontend wireada (LISTO):** en el modal de proyecto, los documentos de
ponencia/plenaria/conciliación son clicables → llaman la acción `gaceta` de la
Lambda → `analizarGaceta` renderiza según el `tipo_documento`: **ponencia** (sentido
favorable/archivo verde/rojo + ponentes + argumentos + oposición) y **acta**
(header dinámico + **aplazamiento** [propuesto_por + detalle] + **votación**: tally
favor/contra + **listado nominal por congresista** coloreado por voto Sí/No). Si la
gaceta no tiene texto en S3, muestra "no procesada (se baja bajo demanda)".
Verificado: Rosa Elvira Cely / Gaceta 857-2013 → favorable · Doris Clemencia Vega
Quiroz · 6 argumentos. El render de acta espera el primer lote de actas procesadas.

> **Voto nominal · hallazgo jul-2026 (feasibility):** el nominal por congresista
> **NO existe en Congreso Visible** para 2006-2022 — solo el tally. Verificado:
> `votacion_congresista=[]` en las 10.205 del dump + `CurulData` (112 curules) con
> `tipo_respuesta_votacion_id`/`congresista_id` en null en 6 votaciones muestreadas
> (2015-2022), y viene del SSR/backend de ellos (no es un XHR por capturar). El voto
> nominal SOLO se obtiene de las **actas de gaceta** (la acción `gaceta` ya lo extrae
> cuando el acta lo trae). → el nominal loopea a procesar actas.

**Pendiente (gacetas de SENADO · ver bloque "Fase 3" arriba y `procesar_gacetas.py`) —
Cámara ya no depende de esto, ver "Fase 3 · voto nominal de Cámara":**
1. ✅ Descarga: carpeta de Chrome de Ricardo ya apunta a `Bases de datos/leyes-senado/gacetas/`
   (sin diálogo). El folder es la cola; `procesar_gacetas.py` clasifica/enruta/sube texto.
   Bulk NO automatizable (portal JSF hostil). Actas de Senado del cuatrienio actual = **on-demand**
   (opción B, decisión Ricardo jul-2026). Targeting de actas de Senado (qué nº de gaceta es
   acta) = sin resolver → opción A. **Buscar si Senado tiene un endpoint propio equivalente al
   de Cámara** (`secretaria-general/actas-votaciones-y-otros/`) antes de seguir por gacetas.
2. OCR para gacetas escaneadas (años 90-2005) antes de subir su texto.
3. Voto nominal de Senado por congresista: detalle `/votaciones/{id}/` de Congreso Visible
   (pre-2022) + extracción de actas (cuatrienio actual, on-demand).

Refinamientos opcionales del join autor→partido: (a) más años de Congreso (pre-2014)
para cubrir legisladores viejos; (b) ampliar `MANUAL`; (c) votación nominal por
bancada (necesita actas de gaceta, fase 3).

**Búsqueda + capa de sinónimos (LISTO · jul-2026):** el índice usa un stemmer
ligero (`_stem`) que tolera erratas del Congreso, y ahora una **capa de sinónimos
curada** (`SINONIMOS` en `caudal_core.py`) para temas de vocabulario disperso.
Cuando la consulta cae en un tópico curado, la búsqueda pasa de AND-de-palabras a
**OR sobre todo el vocabulario del tópico** (más recall); fuera de tópico se
comporta idéntico a antes (cero regresión). Cada tópico `{k, terms}`; los `terms`
cumplen doble rol: **disparan** el tópico desde la consulta Y **expanden** el
match (palabra ≥4 chars por substring/raíz · frase = todas sus palabras >3).
15 tópicos hoy (aborto/derechos reproductivos, eutanasia↔muerte digna, paridad↔
cuota de género, cannabis, protección animal, trata de personas, etc.). Hallazgo
clave: el Congreso **no titula "aborto"** (0 hits) — el debate vive como "derechos
sexuales y reproductivos"/"salud reproductiva" (→ ahora 12). `resumen_tema`
devuelve `sinonimos:{topicos,incluye}`; el frontend lo muestra ("Búsqueda por
tema · se incluyen: …") y suprime el hint de `broaden` en ese caso. **Agregar un
tópico:** una entrada en `SINONIMOS` + validar contra el vocabulario REAL de los
títulos (no el conceptual) + `build_zip.py` + `update-function-code`. Para casos
no cubiertos, sigue disponible el stemmer Snowball español completo como upgrade.

### Arquitectura Caudal · paraguas vs pilares (aclaración conceptual jul-2026)

**Caudal = la plataforma-paraguas** (el "mini-Dapper interno" de Cauce que
aglutina TODAS nuestras bases de datos). Lo que hoy llamamos Caudal
(`caudal.html` + Lambda `caudal-analiza` + `harvest.py` de leyes.senado) es
**solo el pilar Congreso**. A partir de jul-2026 Caudal se organiza en pilares:

```
Caudal (paraguas)  ·  caudal.html = HOME multi-pilar (9 cards del mapa de fuentes de Cauce)
├── Congreso      → view-congreso    + Lambda caudal-analiza (tema/proyecto/gaceta/…)   (LISTO · en prod)
├── Regulatorio   → view-regulatorio + Lambda action `sanciones` + tools/caudal/supers/  (LISTO · en prod)
├── Medios        → view-medios      + Lambda action `medios` (Google News RSS, gratis)  (LISTO · en prod)
└── Cortes / Datos abiertos / Territoriales / …   (cards "Próximamente" en el home)

⊕ Vista Cliente   → view-cliente + Lambda action `cliente` — lente SIGA que CRUZA los
                    pilares por sector y triaja a acción (SKU A, NO es un pilar)  (LISTO · en prod)
```

> **Decisión de naming RESUELTA (jul-2026 · modelo paraguas):** todo vive bajo
> `tools/caudal/`; Regulatorio es un pilar de Caudal, NO un hermano — no se
> bifurca a `tools/cauce/regulatorio/`. `caudal.html` es el HOME paraguas: hero
> "El Estado, leído", búsqueda universal y grilla de **9 pilares** (Congreso
> activo · Regulatorio activo · los 7 restantes "Próximamente", reproduciendo el
> mapa de fuentes del pitch). Cada pilar es una **vista** (`view-home`,
> `view-congreso`, `view-regulatorio`) con su hero, su búsqueda y un back a
> Caudal; el router es `showView(v)`. Los pilares NO comparten código de datos
> entre sí, pero SÍ el shell del frontend y la Lambda (acciones **aditivas** —
> agregar un pilar no toca los otros).

### Vista Cliente · Radar (SKU A · LISTO · en prod · jul-2026)

La **lente SIGA** del pitch, materializada: eliges un **sector** y Caudal cruza
Congreso + Regulatorio filtrado por ese sector, descarta el ruido y deja las
señales que mueven la aguja, cada una con **nivel (alto/medio/bajo) + acción
sugerida**, más una **lectura del analista** (LLM). Reproduce el "9 señales → 6
descartadas → 2 importan" del roadmap con datos reales. Es el producto **SKU A**,
NO un pilar (vive encima de los pilares).

- **Entrada:** card `#radar-cta` en el home de `caudal.html` → `view-cliente`.
- **Presets de sector** (`SECTORES_CLIENTE` en `caudal_core.py`): salud,
  contratacion, financiero, energia, educacion, trabajo. Cada uno: `temas`
  (búsqueda en el Congreso · **curados para precisión**: palabra sola solo si es
  distintiva; si el término corto colisiona por substring —seguros→seguridad,
  credito, pension→suspension— se usa frase AND), `sector_sanciones` (filtro del
  pilar Regulatorio; salud+contratacion tienen sanciones reales, el resto muestra
  "fuente por conectar") y `comision` de referencia.
- **Triaje determinista** (`Caudal.radar_congreso` + `_senal_congreso`): score de
  accionabilidad (EN_TRAMITE > caído reciente > ley reciente > antecedente) →
  nivel + acción. **Cero invención de cifras** (todo sale del dato). La acción cita
  la comisión REAL del proyecto. Regulatorio: sanción reciente del sector = alto.
- **Lambda acción `cliente`** (`{action:'cliente', sector, lectura}`): ensambla
  `radar_congreso` (Congreso) + `_sanciones()` filtrado por sector (Regulatorio) +
  KPIs; con `lectura:true` agrega `_lectura_cliente` (DeepSeek, cache hash24 por
  sector+conteos, mismo patrón que `_sintesis_tema`). Aditiva — no toca las otras rutas.
- **Frontend** (`view-cliente`): pills de sector → `cliLoad()` pinta KPIs + nota
  "de N proyectos que tocaron el sector, el radar prioriza M" + lectura (pre-fetch
  como en tema) + 2 secciones de señales (Legislativo · Regulatorio) con dot de
  nivel y acción. `CLI_SECS` hardcoded (espejo de `SECTORES_CLIENTE`).
- **Pendiente / v2:** perfil de cliente guardado (temas propios + storage), triaje
  LLM por-señal (hoy es determinista + 1 lectura global), y cuando entren
  Superfinanciera/otras superintendencias, los sectores financiero/energía ganan
  Regulatorio real.

### Pilar Regulatorio · sanciones de superintendencias (`tools/caudal/supers/` · piloto vía 1 LISTO)

Extractor de sanciones/actos de superintendencias y entidades reguladoras.
Cumple una promesa que YA está en el documento de Cauce
(`Propuestas/Cauce-Estado-de-Cosas-Inteligencia-Legislativa.pdf`): las
superintendencias son 1 de las 9 categorías del "mapa inicial de fuentes" (18 en
"Superintendencias y comisiones") y el ejemplo estrella del pitch (alerta de
precisión para empresa de salud) usa una **circular de la Supersalud**.

**Estado (jul-2026) · PILAR EN PRODUCCIÓN (vía 1):** ya tiene frontend +
Lambda + S3, no solo datos.
- **Frontend:** `view-regulatorio` en `caudal.html` (hero "Las sanciones del
  Estado, leídas" + búsqueda + pills de sector Todos/Salud/Contratación/
  Jurídico/Control + landing con KPIs y cards por sector + lista de sanciones).
  Se entra por la card "Superintendencias" del home.
- **Lambda:** acción **aditiva** `sanciones` en `caudal-analiza`
  (`lambda_handler.py`). Sin query/sector → devuelve los agregados
  precalculados (landing, rápido). Con `query`/`sector` → carga
  `metadata/sanciones.jsonl` (cache warm), filtra por substring sobre un blob
  `q` (sancionado+motivo+descripción) y/o sector, y devuelve hasta 120 (las
  más recientes) + agregados del subconjunto. No toca ninguna ruta del Congreso.
- **S3** (bucket privado `caudal-legislativo`): `metadata/sanciones.jsonl`
  (slim, sin `_raw` ni cédulas · 3.5 MB) + `metadata/sanciones-stats.json`
  (agregados chicos: total, por_sector, por_fuente, por_tipo, monto, recientes).
- **Build:** `python3 tools/caudal/supers/build_s3.py` toma `dist/sanciones.jsonl`
  (salida de `harvest_supers.py normalize`) → emite `dist/s3/{sanciones.jsonl,
  sanciones-stats.json}`; subir con `aws s3 cp … s3://caudal-legislativo/metadata/`.
  Re-correr cuando cambien los datos (o entre una fuente vía 2/3).

**Esquema común de sanción** (`fuentes.json._schema_normalizado`): `fuente ·
fuente_nombre · sector · sancionado · identificacion · tipo_sancion · motivo ·
monto · resolucion · fecha_firmeza · estado · descripcion · _id · _raw`
(`_raw` = fila original, trazabilidad — cada alerta cita su fuente).

**Las 3 vías de extracción:**
- **Vía 1 · Socrata** (datos.gov.co, JSON directo — IMPLEMENTADA): patrón de
  `lab-indicadores`. Query `resource/{id}.json?$where=...`, cero scraping.
- **Vía 2 · API interna del portal — Superfinanciera IMPLEMENTADA (jul-2026,
  `harvest_sfc.py`)**: buscador SiriWeb (Angular) habla con
  `.../api-siri-casillero/.../api/actoAdmin/listarSancionesMercadoValores`; la
  **api-key vive en texto plano en el bundle público `SiriWeb/main.js`**
  (`const Qt = {..., apiKey:"..."}`, regex `apiKey\s*:\s*"([^"]+)"`) — no es
  una credencial protegida, es la misma que usa cualquier visitante del
  buscador; el harvester la re-extrae en cada corrida por si rota. Header
  correcto: **`api-key` (minúsculas) o `Api-Key`** — `apiKey`/`x-api-key` dan
  401. **805 sanciones** verificadas (`nombreDestino/montoSancion/tipoSancion/
  temaClasificacion/estadoSancion/fechaFirmeza/observacion`), todas
  `estadoSancion:"En firme"`. Fechas llegan en epoch-millis → `harvest_sfc.py`
  las convierte a ISO y descarta las fuera de rango sano (la fuente trae al
  menos 1 typo real, año 3022) en vez de adivinar. `numeroActoAdmin` llega
  como int → se convierte a string (si no, `build_s3.py` revienta con
  `.strip()` sobre un int). Supertransporte (WP `?rest_route=/wp/v2/posts`,
  BOM utf-8-sig) y SIC (`rss.xml`) siguen pendientes, mismo patrón.
- **Vía 3 · normograma/PDF** (registrada, pendiente): reusa el **pipeline de
  gacetas de Caudal fase 3** (pypdf + DeepSeek). Supersalud (SharePoint) y
  Supersociedades (Liferay, 478 resoluciones + 198 circulares). PDFs viejos → OCR.

**Gotcha de `build_s3.py` encontrado con los datos de Superfinanciera (jul-2026):**
algunos textos largos (`observacion`) traen mojibake de control chars —
comillas/elipsis de Windows-1252 mal transcodeadas (`\x93…\x85`) — mezclado
con el texto real. Más allá de ensuciar la UI, **`U+0085` (NEL) es "salto de
línea" para `str.splitlines()`** aunque NO sea el `\n` real que separa los
registros del JSONL → partía un registro en dos fragmentos inválidos y
`build_s3.py` reventaba con `JSONDecodeError: Unterminated string`. Fix: (1)
`build_s3.py` lee con `.split('\n')`, nunca `.splitlines()` — regla general
para cualquier JSONL que pueda traer texto con `U+0085`/`U+2028`/`U+2029`.
(2) nuevo `_clean_text()` en `slim()` quita control chars (`\x00-\x1f`,
`\x7f-\x9f`) de sancionado/motivo/descripcion antes de truncar — doble
beneficio: no rompe el parseo Y no le muestra mojibake al cliente. **Ojo:**
la Lambda (`_sanciones()` en `lambda_handler.py`) lee el mismo formato de
archivo con el mismo patrón `.splitlines()` — quedó dormido esta vez porque
el texto problemático cayó dentro de los primeros 120 chars que sí se
truncan, pero es la misma clase de bug latente ahí; pendiente portar el
mismo fix si vuelve a aparecer con otra fuente.

**Comandos** (`harvest_supers.py`, stdlib + curl subprocess, resumible):
```bash
python3 tools/caudal/supers/harvest_supers.py list        # mapa de fuentes
python3 tools/caudal/supers/harvest_supers.py test        # valida mapeos (1 fila/fuente)
python3 tools/caudal/supers/harvest_supers.py fetch [slugs...] [--desde YYYY-MM-DD]
python3 tools/caudal/supers/harvest_supers.py normalize    # raw -> dist (JSONL+CSV+stats)
```
Salidas (gitignored): `Bases de datos/leyes-senado/supers/{raw/{slug}.json,
dist/{sanciones.jsonl,sanciones.csv,stats.json}}`.

**Verificado end-to-end (2026-07):** **6.889 sanciones a nivel entidad**
consolidadas de las 6 fuentes por-entidad: INVIMA (3.690), SECOP I (1.707),
SECOP II (542), Junta de Contadores (85), Contraloría responsabilidad fiscal
(60), **Superfinanciera (805, vía 2)**. El dataset vía 1 de Min. Trabajo es
**agregado** (por territorial/sector, solo conteos) → `granularidad: agregado`,
NO entra al consolidado por entidad (sirve de contexto). Sector `financiero`
del Radar del cliente (Vista Cliente/SIGA) pasó de "sin fuente conectada" a
datos reales — verificado en vivo (`action:cliente,sector:financiero`).

**Cómo agregar una fuente vía 1:** una entrada en `fuentes.json.fuentes` con
`via:1`, `socrata_id`, `fecha_col` y el `map` (campo_normalizado → columna).
Descubrir: `catalog/v1?domains=www.datos.gov.co&q=sanciones+<entidad>` →
`resource/<id>.json?$limit=1` para ver columnas. `test` valida el mapeo.

**Siguiente sprint (recomendado):** (1) ✅ HECHO (jul-2026) — `harvest_sfc.py`
(Superfinanciera vía 2). (2) ✅ HECHO — `sanciones.jsonl` ya está enganchado a
la Lambda (acción `sanciones`, filtro por sector+texto) con frontend
`view-regulatorio` en `caudal.html`, y ✅ cruzado con el Radar del cliente
(SIGA) — ver sección "Vista Cliente · Radar". (3) Vía 3 Supersalud con el
pipeline de gacetas — cierra el ejemplo del pitch, sigue pendiente. (4)
Supertransporte + SIC (vía 2, mismo patrón que SFC, más simples).

**Estado:** commit `9f1c296` en `main` (solo `tools/caudal/supers/*` + `.gitignore`;
NO tocó `caudal.html`). **Datos ya subidos a S3 con luz verde de Ricardo
(jul-2026)** — ver "Vía 2 · Superfinanciera IMPLEMENTADA" arriba.

### Pilar Medios · prensa nacional y regional (`view-medios` en `caudal.html` · LISTO vía Google News RSS)

Tercer pilar en vivo de Caudal (junto a Congreso y Regulatorio). Responde el
mismo mapa de fuentes del pitch de Cauce ("medios" es 1 de las 9 categorías).
**Mecanismo: Google News RSS** (`news.google.com/rss/search?q=…&hl=es-419&gl=CO&ceid=CO:es`),
gratis y sin API key — el mismo motor que ya se usaba en
`tools/radar-mujer-medios/collect.py` (monitor de prensa de Radar Mujer/MxD):
una sola query trae ~50 titulares de **todo el ecosistema de prensa** (nacional
+ regional) con el nombre del medio limpio en el tag `<source>`, sin mantener
un conector por outlet. `urllib.request.urlopen` sigue el 302 de Google
automáticamente (no hace falta manejarlo a mano).

- **Backend** (`tools/caudal/lambda/lambda_handler.py`, acción `medios`,
  añadido self-contained — sin nuevas deps, sigue empaquetando solo
  `lambda_handler.py` + `caudal_core.py` vía `build_zip.py`):
  - `{"action":"medios"}` sin `query` → **landing**: fetch en paralelo
    (`ThreadPoolExecutor`) de 4 queries amplias (`MEDIOS_LANDING_Q`: Congreso,
    Gobierno Nacional, Corte Constitucional, "reforma Colombia"), ventana
    `when:3d`, dedup + agregado.
  - `{"action":"medios","query":"reforma pensional","dias":30}` → **búsqueda**:
    una sola query con ventana `when:{dias}d` (default 30).
  - Dedup por (título normalizado, medio) — mismo criterio que collect.py.
    Título de Google News trae sufijo `" - Medio"` redundante con el tag
    `<source>`; `_medios_split_title` lo recorta solo cuando coincide.
  - **Clasificador nacional/regional** (`_medios_alcance`): lista curada
    `_MEDIOS_REGIONALES` (~34 outlets, forma "compacta" sin tildes/espacios/
    puntos — así matchea tanto "El Heraldo" como "ELHERALDO.CO"). No pretende
    ser exhaustiva; lo que no matchea cae a `nacional` (fallback seguro, la
    mayoría de la prensa digital colombiana es de alcance nacional).
  - **Cache pobre-pero-efectivo** en `analisis-cache/` (mismo prefijo S3 que
    el resto de Caudal): la key incluye un bucket de 3h
    (`int(time.time()//10800)`), así que dentro de esa ventana la misma query
    es instantánea y después de esa ventana se refresca sola — sin lógica de
    TTL/expiración explícita, solo keys que cambian con el tiempo.
  - Sin síntesis LLM en v1 (a diferencia de `tema`/`cliente`) — es agregación
    pura, cero costo de DeepSeek. Iteración futura natural: una lectura corta
    tipo `_contexto_medios` sobre los titulares de una búsqueda.
- **Frontend** (`view-medios`, patrón calcado de `view-regulatorio`): hero +
  buscador + chips de ejemplo (reforma pensional, reforma laboral, reforma a
  la salud, seguridad Catatumbo, paro camionero, Petro Congreso) + landing
  (KPIs: titulares, medios distintos, nacional, regional + lista de titulares
  recientes) + resultados de búsqueda (mismo shape). Reusa las clases CSS
  `.sanc`/`.sanc-list`/`.doc-badge` (ya existían para el pilar Regulatorio) —
  cero CSS nuevo. Badge "Regional" reusa `.doc-badge.pal` (ámbar) tal cual.
- **Validado con datos reales** (jul-2026, antes de deploy): landing trajo 265
  titulares / 98 medios distintos (216 nacional / 49 regional); búsqueda
  "reforma pensional" trajo 51 titulares con El Colombiano, Infobae, El
  Espectador, La FM, Tropicana, ElUniversal.com.co, etc. — la mezcla
  nacional+regional que promete el nombre del pilar, cero conectores que
  mantener.
- **Pilar marcado `status:'live'`** en el array `PILLARS` del home (antes
  `soon`). `PILLARS`/`showView`/`renderPillars` actualizados para enrutar a
  `view-medios`.
- **Cruzado con Vista Cliente/Radar (SIGA) — LISTO (jul-2026).** El radar de
  un sector ahora suma un tercer bloque "Medios · Prensa" junto a Congreso y
  Regulatorio. Helper `_medios_para_sector(temas, dias=14, cap=6)`: corre una
  query de Google News por cada tema del sector en paralelo
  (`ThreadPoolExecutor`), reusa el mismo filtro de ruido/dedup/normalización
  del pilar Medios, cachea 3h por combinación de temas. En la acción
  `cliente`: nivel `alto` si el titular es de los últimos 5 días, si no
  `medio`; entra al conteo combinado de `senales` (así `n_radar`/`alto` del
  KPI reflejan los 3 pilares). Nuevo campo `kpis.n_medios_sector` (volumen
  total de cobertura del sector, no solo los 5 que se muestran) + `medios[]`
  en el payload. Frontend: `cliSigCard` gana rama `tipo==='medios'` (titular
  linkeado + medio + alcance + fecha); `cliRender` agrega la sección "Medios ·
  Prensa" tras Regulatorio. Verificado en vivo: sector salud (5 titulares,
  Supersalud/medicamentos entre ellos) y educación (sin sanciones conectadas,
  el bloque de medios igual funciona).
- **Relevancia Colombia + filtro institucional — LISTO (jul-2026).** Dos bugs
  encontrados probando el cruce con Vista Cliente: (1) `gl=CO` en la query de
  Google News solo **sesga**, no restringe — sectores con temas genéricos
  (`financiero`: "sistema financiero", "mercado de valores"; `trabajo`:
  "salario minimo") traían prensa de México/España/Uruguay sin relación con
  Colombia. Fix en `_medios_gn_url`: si la query no menciona ya "colombia"
  (case-insensitive), se le agrega " Colombia" antes de mandarla — vuelve el
  match un AND real. (2) Google News trae comunicados de entidades propias
  (Sena.edu.co, Gobernación del Magdalena, Ministerio de Minas...) mezclados
  con prensa editorial independiente. Nuevo `_medios_es_institucional(medio)`:
  dominio `.gov.co`/`.edu.co` (chequeado sobre el string CRUDO, no el
  compacto — `_medios_compact` se come los puntos) + palabras-raíz
  (gobernacion, alcaldia, ministerio, universidad, camaradecomercio,
  super{intendencia,salud,financiera,sociedades,transporte,servicios},
  policianacional, registraduria...). Se filtra junto al de redes sociales en
  `_medios_query_events` — un solo punto, aplica a landing/buscar/sector por
  igual. De paso se sumó `t.co` (acortador de X) a `_MEDIOS_FUENTES_EXCLUIR`.
  Verificado en vivo: sector salud pasó de traer Sena.edu.co/Gobernación a
  traer "Newsroom RCN Radio · Supersalud pone límite a la espera..." — el
  ejemplo real que reemplaza al hipotético del PDF de Cauce. **Gotcha
  operativo:** el cache S3 (`analisis-cache/medios-*`) no invalida al
  redeployar — la key es solo por tiempo (bucket de 3h), no por versión de
  código. Cada vez que se cambie lógica del pilar Medios, borrar a mano las
  keys `medios-*` en `s3://caudal-legislativo/analisis-cache/` después del
  redeploy, o el bug corregido sigue sirviéndose desde caché hasta 3h.
- **Pendiente / iteraciones futuras:** lectura LLM sobre los titulares de una
  búsqueda (mismo patrón que `_sintesis_tema`); ampliar
  `_MEDIOS_REGIONALES`/`_MEDIOS_INSTITUCIONAL_RE` según se detecten casos
  nuevos en producción; el filtro institucional es heurístico, no
  exhaustivo (mismo criterio que el resto del pilar).

## Roadmap post-2V · Chats conversacionales (LLM + function calling)

Dos productos planeados para julio 2026 (post-2V) que comparten
infraestructura técnica pero atienden universos distintos.

### Contexto competitivo
Wonk (`getwonk.co`, lanzado mayo 2026) hace BI conversacional sobre
datos abiertos COL (DANE, MinHacienda, Registraduría) con interfaz de
chat en español. Equipo de 6 personas (Bogotá), fundadores Bernardo
Romero-Torres (econometría aplicada) + Samuel David Echeverry. Su
tablero electoral histórico (presi+cámara+senado+locales) probablemente
llega hasta municipio. NO baja a puesto/mesa ni tiene voto blando afín,
ponderador propio o drill barrial.

Decisión estratégica: nuestro chat NO compite head-to-head con BI
horizontal. Compite verticalmente sobre datos electorales granulares
que sólo nosotros tenemos curados (foso = años de pipelines sobre los
CSV GCS de la Registraduría + cruces zona electoral → comuna política +
PUESTOS_GEOREF + listas cerradas).

### Chat #1 — Electoral conversacional

Producto B2C/B2B. Pregunta natural → respuesta con datos exactos +
visualización ligera + cita de fuente. Cero alucinación numérica vía
function calling estricto.

**Arquitectura mínima:**
```
Lambda chat-electoral
├─ Sonnet 4.6 (B2B serio) o DeepSeek V4 Flash (B2C masivo)
├─ ~25 tools de lookup sobre JSONs S3 ya curados
│   ├─ votos_candidato_territorio(cand, dep|mun|com|barrio, año)
│   ├─ resultado_municipio(mun, año, corporacion)
│   ├─ partido_lista(partido, dep, año)
│   ├─ ponderador_actual(candidato)
│   ├─ huella_territorial(barrio_slug, candidato)
│   ├─ comparar_elecciones(territorio, años[])
│   ├─ ganador_mesa(mesa_id, año)
│   ├─ topN_municipios(corte, año, partido)
│   ├─ indicador_municipal(mun, indicador, año)
│   ├─ arquetipo_barrio(barrio_dap, año)
│   ├─ buscar_territorio(texto_libre) → divipola
│   └─ coverage_check(territorio, eleccion, año, granularidad)
│        → { disponible: ✓ | parcial | ✗,
│            latencia: instantáneo | 24-72h }
├─ Cache S3 hash24 TTL 7d para preguntas repetitivas
└─ Output: { texto, datos_crudos, sugerencia_visualizacion }
```

**Reglas duras del system prompt:**
1. Cero datos numéricos sin tool call (regex de validación en
   post-proceso elimina cifras sin respaldo).
2. Siempre citar fuente + año.
3. Si `coverage_check` retorna ✗, decir honestamente "no procesado, lo
   proceso en 24-72h con plan Pro/Premium" — nunca inventar.

**Unit economics:**
- Sonnet 4.6 con cache: ~$0.013-0.02 USD/pregunta.
- DeepSeek V4 Flash: ~$0.0002 USD/pregunta.
- Pro $39.900 con 150 preguntas/mes → margen 80%+.
- Premium $99.900 con 800 preguntas/mes → margen 85%+.

**Cobertura · pre-procesamiento antes del lanzamiento:**

Bloque A — antes de primera semana julio 2026 (compromiso del usuario):
- Territoriales 2019 y 2023 a 5 niveles (alcalde+concejo+JAL) para
  32 capitales × 3 años × 3 corporaciones (~288 corridas, ~1-2 días).
  Generalizar `tools/build-medellin-historicos.js` parametrizando
  (COD_DDE, COD_MME).
- Presidenciales 2018 a puesto+mesa.
- Generalizar `tools/build-historicos.js` para que también escriba
  `por-puesto.json` y `por-mesa.json` (hoy sólo hasta `por-mun`).

Bloque B — opcional pre-julio si hay tiempo:
- Congreso 2014/2018/2022 a mesa (formato ya conocido del 2026).
- Presidenciales 2010 y 2014 a puesto+mesa.

Cobertura proyectada post-Bloque A:
- 100% Presi 2018-2026 a mesa.
- 100% Senado/Cámara 2026 a mesa (ya está).
- 100% Territoriales 2019/2023 a mesa para 32 capitales.
- Bogotá y Medellín a barrio (ya está).
- Cola on-demand 24-72h para muns no-capitales y elecciones pre-2018.

### Chat #2 — Asistente metodológico del Lab de PP

Producto transversal a los 8 módulos del Lab (no es módulo nuevo).
Capa de guía que reduce abandono y aumenta activación. NO canibaliza
el chat electoral — universos completamente distintos (datos vs
metodología).

**Arquitectura:** misma Lambda template + mismo patrón de cache + mismo
gate de plan en `rr-auth`. Cambia el system prompt y el catálogo de
tools.

```
Lambda lab-asistente
├─ DeepSeek V4 Flash (90% de preguntas) + Sonnet 4.6 para
│   diagnósticos profundos del state (Premium)
├─ Tools:
│   ├─ leer_state(modulo)            → lee localStorage del módulo
│   ├─ diagnosticar_progreso(modulo) → qué está completo / qué falta
│   ├─ explicar_concepto(termino)    → definición + cita académica
│   │                                   desde lab-recursos.js
│   ├─ sugerir_siguiente_modulo()    → según state cross-módulo
│   └─ revisar_calidad(modulo)       → red flags metodológicos
│        (matriz muy pequeña, indicadores sin línea base,
│         alternativas sin baseline "statu-quo", etc.)
└─ UI: FAB ✦ Asistente del Lab en cada módulo, acento oxblood/salmón
       del Lab (no el azul/morado de los chats principales)
```

**System prompt:** "Eres el asistente metodológico del Lab de PP de
ricardoruiz.co. Conoces los 8 módulos, sus marcos teóricos y su orden.
Tu trabajo es guiar al usuario, NO hacer el trabajo por él."

**Casos típicos que resuelve:**
- *"¿Qué es un problema wicked?"* → definición + cita Rittel-Webber 1973.
- *"¿Cuándo uso DEMATEL vs MicMac?"* → diferencia conceptual + sugerencia
  según contexto.
- *"Mi MicMac tiene 4 variables, ¿es suficiente?"* → diagnóstico real:
  poco para detectar bucles, recomienda agregar 2-3 más por dominio.
- *"Ya definí el problema, ¿qué sigue?"* → lee state del PP, sugiere
  abrir alternativas con Zwicky o levantar evidencia adicional.

**Por qué importa:** hoy mucha gente abre el Lab, no entiende qué llenar
y se va. El asistente lleva al usuario al `stage-results` y al informe
combinado. Eso es activación de usuario, que es lo que después convierte
a pago.

### Packaging conjunto · cómo evitar canibalización

El chat (electoral o Lab) es **exploración / insight rápido**. Los
reportes (Excel/PDF/mapas embebibles) son **entregable formal de
trabajo**. Son jobs-to-be-done distintos.

| Feature | Free anon | Free email | Pro $39.900 | Premium $99.900 |
|---|---|---|---|---|
| Chat electoral preguntas/mes | 5/día | 30 | 150 | 800 |
| Asistente Lab preguntas/mes | — | 5 | 30 | 150 |
| Tablero electoral | dep/mun | dep/mun | + comuna/puesto | + mesa/barrio |
| Veleta / Oportunidad | demo | demo | acceso completo | + barrios catastrales |
| Excel descarga | ✗ | ✗ | 3/mes | 10/mes |
| PDF Top 50 con metodología | ✗ | ✗ | ✗ | 10/mes |
| Mapas embebibles | ✗ | ✗ | ✗ | ✓ |
| Dashboard custom guardado | ✗ | ✗ | ✗ | ✓ |
| `revisar_calidad` del Lab (Sonnet) | ✗ | ✗ | ✗ | ✓ |
| Cola priorizada (no-cobertura) | — | 72h | 72h | 24h |
| API B2B | ✗ | ✗ | ✗ | 100 calls/día |

**Regla de oro:** el chat da el dato hablado. El entregable formal
(PDF metodológico, Excel base, mapa HD embebible, dashboard custom)
es Premium. Cada respuesta del chat puede mostrar **preview bloqueado**
de versión HD/PDF con CTA upsell a Premium.

### Cronograma sugerido

- Mayo-Junio 2026: foco 100% en 2V (pipeline mesa-a-mesa post-1V,
  endoso simulator, Veleta/Oportunidad 2V, concurso de pronóstico 2V).
- Junio 2026 en paralelo: pre-procesamiento Bloque A (territoriales
  2019/2023 a 32 capitales + presi 2018 a mesa + generalizar
  `build-historicos.js`). En seco, diseño del catálogo de tools de
  ambos chats.
- Primera semana julio 2026 (post-2V): build Lambda chat-electoral +
  UI `pregunta.html`.
- Segunda semana julio: build Lambda lab-asistente (reusa infra).
- Tercera semana julio: integración con `rr-auth` (cuotas + plan gate)
  + landing comercial.
- Lanzamiento: agosto 2026. Coincide con arranque de ciclo electoral
  2027 (Medellín + Bogotá + locales).

### Riesgos a mitigar
- **Alucinación numérica** → function calling estricto + post-proceso
  con regex que valida que toda cifra venga de tool result.
- **Cobertura faltante en preguntas reales** → `coverage_check` como
  tool obligatoria + cola on-demand convertida en feature comercial
  ("procesamiento priorizado en 24h con Premium").
- **Canibalización de Premium** → packaging por job-to-be-done + cuotas
  estrictas en Pro + previews bloqueados que convierten cada respuesta
  del chat en upsell.
- **Costos LLM out of control** → cache S3 hash24 por pregunta
  canonicalizada (la mayoría se repiten) + rate limit por plan.
- **El chat aprende qué pre-procesar** → loguear cada pregunta no
  respondida con conteo de veces que la piden. Es heatmap de demanda
  para priorizar el siguiente lote de pre-procesamiento.

## Análisis "voto fusil" 2V 2026 (LISTO · cerrado jul-2026)

Frente periodístico que **afina** el debate del "voto fusil" del balotaje Cepeda–Abelardo.
**Tesis (de Ricardo):** el fusil existe, está probado puntualmente, opera en varios bandos,
NO fue masivo ni decidió la elección; el dato cuantitativo **ACOTA dónde mirar (no prueba)**,
el terreno valida. NO comparar con 2018/22 (es contextual); comparar **dentro del ciclo
(1V→2V)**. Ajuste de framing (jun-2026): donde hay coacción documentada (asesinato de
líderes, audio exigiendo certificado electoral, "gobernanza criminal" de la Defensoría),
**la evidencia inclina la balanza hacia el fusil**; el terreno valida denuncias puntuales,
no decide si el fenómeno existe.

### La métrica propia: la TIJERA — a nivel PUESTO, NO municipio (clave)
- **Unidad = PUESTO rural (zona 99), georreferenciado** (lat/lon en
  `master_unificado_puesto.json` / `PUESTOS_GEOREF.csv`). NO municipio — ese es el foso
  (rural + georref). La agregación a municipio fue **solo** para cruzar con los hechos de
  Defensoría/prensa (que se reportan a corregimiento/municipio). Mantener esa distinción.
- **Tijera** = puesto donde el ganador 2V ≥95% Y el rival cae ≥10 votos ABSOLUTOS de 1V a
  2V (anómalo: la participación subió). Calculada sobre
  `Bases de datos/output_2v/master_unificado_puesto.json` (14.220 puestos con
  cep1/abe1/cep2/abe2/urna1/urna2/pot/lat/lon). **976 puestos (7%) con caída del rival;
  entre ≥95% sube a 42%; 89 tijeras fuertes, TODAS lado Cepeda** (lado Abelardo 3 débiles =
  sesgo de tamaño de puesto).

### Hallazgos verificados
- 675 mesas 100% Cepeda (Abelardo 81, 64 exterior). 532 en Cauca/Chocó/Nariño, 521 rural.
- **Descomposición (PIP capas oficiales ANT) de las 532:** afro 52% / resguardo indígena
  27% / campesino-coca 22% (étnico 78%); en VOTOS afro 45 / ind 30 / camp 25. → NO es "voto
  resguardo" (La Silla), es territorio colectivo étnico, sobre todo **AFRO**.
- **Inversión clave:** las mesas 100% son étnicas (78%); las **TIJERAS son campesinas (72%)**.
  El voto en bloque étnico es genuino; el desplome del rival (tijera) es campesino-coca bajo EMC-Mordisco.
- Continuidad 1V→2V: 81% de las mesas 100% ya eran ≥90% Cepeda en 1V (estructural).
- **Participación = movilización, no abstención** (censo POR PUESTO `pot`, Divipole — no por
  mesa): nacional 58,8→64,8 (+6); tijeras 69,5→83,0 (+13,6); 10 zonas 55,7→69,6 (+13,9);
  Tumaco 37,9→57,7 (+19,9). Matiza a la FIP (−4pp promedio).
- 17 mesas "100%" eran error de digitación E14 (descontadas).

### Las 10 zonas (municipio · m100 · tijeras · frente EMC-Mordisco · triangulación)
6 FULL (grupo+Defensoría+prensa fechada) + 4 PARCIAL (2 + prensa estructural):
Tumaco(Nar 112·9, F.Oliver Sinisterra/CN-EB; AT 013-25 gobernanza criminal, minas 11-may,
líder Awá 14-jun) · Policarpa(Nar 9·6, F.Franco Benavides; masacre La Vega 5-mar + audio
"certificado electoral" 31-may) · Argelia(Cau 7·6, F.Carlos Patiño; combates El Plateado
9-12 abr) · Patía(Cau 4·6, F.Carlos Patiño; atentado Panamericana 25-abr) · El Tambo(Cau
8·5, F.Carlos Patiño) · Mercaderes(Cau 4·3, F.Carlos Patiño; Panamericana 25-abr) — los 6
FULL. PARCIAL: Bolívar-Cauca(24·18, F.Carlos Patiño+ELN) · Leiva(Nar 6·8, F.Franco
Benavides) · Cumbitara(Nar 12·3, F.Franco Benavides) · Almaguer(Cau 11·2, F.Carlos Patiño).
**Frentes EMC línea 'Mordisco' (NO Calarcá):** Carlos Patiño (Cauca sur, 6 zonas), Franco
Benavides (cordillera Nariño, 3), Oliver Sinisterra/CN-EB (Tumaco, 1).

### Simetría "varios bandos" (Catatumbo, lado Abelardo)
A nivel MUNICIPIO el voto sigue el linaje del grupo: ELN→Cepeda (El Tarra 82, Teorama 86,
San Calixto 89, Hacarí 70); derecha (Clan del Golfo/ACSN/Frente 33-EMBF de 'Calarcá')→
Abelardo (Sardinata 89, Toledo 88, Ábrego 82, Ocaña 71, Tibú 60). Tijera mesa-a-mesa casi
nula del lado Abelardo (puestos chicos); sin hecho documentado de presión pro-Abelardo en
sus municipios de arrase (cordillera/Santander, separados del Catatumbo en guerra).

### Archivos
- `voto-fusil-2026.html` — página/hub (hero + mapa Leaflet 10 zonas con fichas/popups + 4
  figuras + tabla diferenciación + metodología + fuentes; tema paper). Verificado en navegador.
- `rrss/twitter/hilo-voto-fusil.md` — 14 trinos (Premium), apunta a ricardoruiz.co/voto-fusil-2026.html.
  (Se quitó el trino "en qué nos distanciamos"; trino 11 Catatumbo suavizado a "coincidencia, no prueba".)
- `rrss/twitter/voto-fusil-png/{inversion-territorio, participacion-movilizacion,
  mapa-tijeras-cauca, mapa-tijeras-narino, simetria-catatumbo, tabla-10-zonas-1,
  tabla-10-zonas-2, caso-llorente}.png` — 8 imágenes. **El mapa y la tabla quedaron
  partidos en 2** (antes `mapa-10-sitios.png` y `tabla-10-zonas.png`, eliminados). El mapa
  ahora es a nivel **PUESTO** georreferenciado (zona 99), dividido Cauca (40 ptos) / Nariño
  (26 ptos). `caso-llorente.png` = anatomía de una tijera en un puesto concreto (LLORENTE,
  Tumaco, pcode 231399959: Cepeda 1816→3678, Abelardo 219→101, +1.681 votantes).
- `rrss/linkedin/articulo-voto-fusil.md` — columna extendida (tuteo neutro), profundiza
  más allá de las imágenes. LISTA.
- `rrss/instagram/carrusel-voto-fusil/01..10.png` — **carrusel IG (10 slides · 1080×1080)**.
  Portada = imagen de referencia (comandante EMC "profesor", `tools/voto-fusil/assets/portada-ref.png`)
  + título largo. Resto condensa el análisis (02 el 100% · 03 la tijera · 04 Llorente ·
  05 inversión · 06 participación · 07 mapa 10 zonas · 08 coacción documentada · 09
  Catatumbo coincidencia-no-prueba · 10 cierre). Caption en `rrss/instagram/voto-fusil-caption.md`.
  Script **`tools/voto-fusil/build_carrusel_ig.py`** (Arima + DejaVu Sans, logo+crédito+contador
  n/10, SIN watermark). Identidad igual que las imágenes twitter.
- **`tools/voto-fusil/build_imgs.py`** — regenera las 4 imágenes corregidas (a inversión,
  b participación, c mapas Cauca/Nariño a nivel puesto, d tabla partida en 2 con el hecho
  visible). Reconstruido jun-2026 (el script original no quedó en el repo). Lee
  `tools/voto-fusil/_tijeras.json` (89 tijeras fuertes con lat/lon, regenerable desde
  `master_unificado_puesto.json`) y la geo municipal de
  `Bases de datos/output_pacto_1v_2026/geo/mps/{11,23}.json` (Cauca=11, Nariño=23
  electoral; match por `mun_elec`). 10 zonas en dict `ZONAS`. Tijera fuerte = Cepeda
  cep2/(cep2+abe2)≥0.95 y abe1−abe2≥10. Correr: `python3 tools/voto-fusil/build_imgs.py`.
- `Bases de datos/output_2v/voto-fusil-memo-tecnico.md` — memo backbone (todo + fuentes + diferenciación).
- Datos: `Bases de datos/output_2v/{master_unificado_puesto.json, Mesas_Cepeda_100pct_2V_vs_1V.xlsx,
  Cepeda_Cauca_Choco_Narino_analisis.xlsx, _cache_resguardos_cn.geojson, _cache_afro_cn.geojson}`.
  Capas ANT: services9.arcgis.com/pZylgd2zhNey2qXF — `10_12_24_RESGUARDO_INDIGENA_FORMALIZADO`
  (layer 19) + `10_12_24_COMUNIDAD_NEGRA_TITULADA` (layer 18), DEPARTAMENTO=DANE (Cauca 19,
  Chocó 27, Nariño 52). MOE: `.claude/riesgo-2025/full.txt` (Tabla 1/2/3/4 GAI por municipio,
  split EMC Mordisco vs Calarcá en línea ~313).
- **Identidad imágenes:** matplotlib + Arima (`tools/edad-1v-2026/fonts/Arima-{Bold,SemiBold}.ttf`),
  paper #f1eee4, ink #1a1510, oxblood #8a1e16, ámbar #cf7d2a, Cepeda rojo #c0392b / Abelardo
  azul #1f47cc. Redes usan Helvetica/Arima (NO Inter). Censo por PUESTO (no mesa).

### Estado: LISTO (cerrado jul-2026)
1. ✅ **Columna/artículo (LinkedIn)** — `rrss/linkedin/articulo-voto-fusil.md` (jun-2026).
2. ✅ **Fix imágenes** — los 4 fixes hechos vía `tools/voto-fusil/build_imgs.py`:
   (a) inversión: interlineado del subtítulo + leyenda separada del cuadro · (b)
   participación: `%` separado del nombre + interlineado · (c) mapa a nivel PUESTO,
   partido Cauca/Nariño · (d) tabla partida en 2 con el hecho visible por zona.
3. ✅ **Carrusel IG** (10 slides) — `rrss/instagram/carrusel-voto-fusil/`.

Todos los pendientes (incluida la validación geográfica km puesto→hecho y el
enlace en `noticias.html`) quedaron resueltos o descartados. Módulo cerrado.

## Sistema visual v2 (jul-2026) — oscuro azul + Helvetica

Migración en curso al **sistema visual v2**: fondo `#060810` + gradientes
radiales azules, **Helvetica Neue embebida** (`fonts/*.woff2`, familia completa
200/300/400/500/700+italic), **Syne SOLO en el logo Ricardo.Ruiz**, tarjetas
`rgba(10,10,16,.75)` borde `rgba(255,255,255,.07)`, azul `#0047FF` (CTAs) /
`#3d6fff` (acento texto), naranja `#f97316` (Iniciar sesión / MI PERFIL),
verde `#4ade80` (Volver / Planes & Precios). **Oscuro único: SIN modo día**
(decisión 9-jul; reversible vía variables).

**Convertidas:** `index.html` (portada de cuadros + pestañas Inicio/Proyectos/
Servicios, hero "Datos que <verbo> <sustantivo>" rotando, cuadros con imagen en
`imagenes-index/`, modal contacto correo/WhatsApp), `electoral.html`,
`perfil.html`, `pricing.html`, `descargas.html`, `pago-confirmado.html` (nueva),
`analisis-candidato.html`, `endoso-2026.html`, `comparar-candidatos.html`
(estas 3 comparten el nav v2 + `cand-index.js`; endoso/comparar perdieron el
modo día/noche), `dashboard.html`/`login.html`/`register.html`/`forgot.html`
(commit `f653657`, jul-11: Familjen Grotesk/Petrona → Helvetica Neue embebida,
Syne solo en logo, modo día neutralizado y oculto — JS intacto), `noticias.html`
(jul-18: nav reemplazada por el chasis `.electoral-nav`/`.e-nav-left`/
`.e-nav-right` con selector de país + chip de sesión login/Mi perfil; el resto
de la página ya estaba en paleta oscura/Helvetica). **En Asamblea la
comparación geográfica es departamental** (no nacional): comparar baja el radar
a "Presencia por municipios" y endoso arranca el drill en el departamento del
candidato (helper `isDeptRace`/`initialDrill`).
**Pendientes:** resto del sitio no listado arriba (revisar caso a caso — este
listado se desactualiza fácil, verificar con `git log -- <archivo>` o abriendo
la página antes de asumir que algo sigue pendiente).

Reglas al convertir una página:
- Nav electoral: `.e-nav-left` (← Volver verde + auth) / `.e-nav-right` (país +
  logo). Logueado → chip de plan + botón naranja **MI PERFIL** → dashboard +
  Salir (sin nombre de usuario). Marcar `dataset.loggedIn` para que el cambio
  de idioma no revierta el estado.
- Móvil ≤900px: nav en columna — línea 1 = logo CENTRADO (país en absolute a la
  izquierda), línea 2 = volver+auth centrados; ≤360px reduce país/logo.
- i18n co/us/cn/**br** (Brasil está en todos los dropdowns nuevos).
- Deploy: GitHub Pages desde `main` con **`.nojekyll`** (no quitarlo: un build
  Jekyll roto congeló el sitio el 9-jul).

### Centro de descargas — permisos y nombres en crudos
- **`FILE_GRANTS`** en `descargas.html`: permisos puntuales por archivo
  (`email → [{cat, anio}]`) sin acceso total y sin consumir cuota Premium.
  Activo: `consultoria@legitimalab.com` (Juan José Guerrero) → Territoriales
  2023. Además `ADMIN_EMAILS` / `FULL_ACCESS_EMAILS` (bypass total).
- **Nombres en crudos GCS**: `tools/build-csv-names/build.py` (CSV) y
  `tools/build-xlsx-zip-depto/build.py` (ZIP Excel por depto) insertan
  `DES_DDE`/`DES_MME`/`DES_PP` junto a su código. Fuentes: divipola.json
  (con `DEP_FIXES`: 25=Norte De Santander, 31=Valle Del Cauca — divipola los
  trae mal) + PUESTOS_GEOREF 2026 + Divipol 2021 fallback (header en fila 5).
- ⚠ **El dict `DEPTOS` viejo estaba descuadrado** con los códigos reales RNEC
  (40=Arauca, 68=Vaupés, 72=Vichada, 19=Huila, 21=Magdalena, 23=Nariño,
  25=N.Santander…). Los ZIP de Congreso del 31-may quedaron mal etiquetados y
  se regeneraron el 10-jul. El mapeo de nombres de archivo ahora se deriva de
  divipola+fixes — no reintroducir dicts hardcodeados.
- **CSV mesa NO abre completo en Excel** (límite 1.048.576 filas → aviso "El
  archivo no está totalmente cargado"). Nota visible en el tab crudos + modal.
- Estado del catálogo: TER-2023 CSV mesa/puesto **con nombres** en S3; ZIPs
  con nombres: TER-2023 + CON 2014/2018/2022 (regenerados 10-jul). Pendiente:
  ZIPs TER 2011/2015/2019 (no existen; `xlsxZip:false` hasta generarlos) y
  enriquecer los CSVs del resto del catálogo (~15 GB de re-uploads).

### Pagos Wompi
- `pago-confirmado.html` = redirección post-pago (lee `?id=`, consulta API
  pública Wompi, polling a `/auth/me`, refresca `rr-user` en caché). Configurar
  en cada link de Wompi: redirección `https://ricardoruiz.co/pago-confirmado.html`,
  pago único NO, SKU `plan-{pro|premium}-{mensual|anual}`.
- Pendiente: Ricardo crea los 4 links nuevos → actualizar `WOMPI_LINKS` en
  `pricing.html`. Pricing quedó mensual por defecto, sin promo y sin Plan Datos.

## Cliente YCJF · consultoría IA operativa (STAND BY · jul-2026)

**Youth Climate Justice Fund** (`ycjf.org`) — fondo filantrópico de justicia
climática juvenil (partner ClimateWorks): 115 grants en 51 países, $8.1M
comprometidos, equipo ~13-15 personas 100% remoto. Contacto: **Tatiana
Restrepo, Finance & Operations Manager** (Colombia/Bélgica), referida por
Pablo Cárdenas. Piden consultoría de IA para procesos del equipo de
operaciones (hoy todo manual en Google Sheets/Word).

**Frontera de alcance (clave):** todo lo que pasa por el fiscal sponsor
(RIA/Rockefeller — contratación de consultores, invoicing, pagos) ya está
automatizado en las plataformas de ellos y NO compete. La consultoría vive
del lado YCJF: **Google Workspace + Slack + Monday + Sheets** (+ Submittable
para el grantmaking).

**Necesidades de la reunión (17-jul-2026):**
1. Grants entrantes: llega correo con PDF del grant → meter la info a un
   Google Sheet de Tatiana (+ descargas de la plataforma del sponsor → Sheets).
2. Correos recurrentes de contratos de staff al fiscal sponsor (mismo correo
   cada vez, disparable desde Monday).
3. Reclutamiento: filtrar/comparar candidatos con IA, menos manual.
4. Planeación anual colaborativa (identificación de necesidades del equipo).
5. Evento de octubre (~100 personas): organización/logística.
6. Preocupación explícita por el **impacto ambiental del uso de IA** (para un
   fondo climático es criterio de selección — responder con "IA sobria":
   modelos eficientes por tarea + huella estimada + política de uso).

**Propuesta pensada: modelo LEGO** — bloque base obligatorio (diagnóstico +
auditoría de stack + política IA responsable/ambiental + taller) + bloques
operativos a precio fijo que ellos escogen (los 6 de arriba; 1 y 2 son quick
wins empaquetables con la base) + retainer mensual + bloque de expansión
futuro (triaje IA de aplicaciones Submittable en 7 idiomas — donde más horas
se queman, pero no es el área de Tatiana). Precios en USD.

**Estado: BORRADOR v1 EN REVISIÓN INTERNA** (jul-2026). PDF armado en
`Propuestas/Propuesta-YCJF-IA-Operativa.pdf` (4 págs, **sistema visual v2**:
fondo #060810 + Helvetica woff2 del repo + Syne solo wordmark + logo 4 barras
— esta es LA PLANTILLA para propuestas nuevas, decisión jul-2026) vía
`tools/build-propuesta-ycjf/build.py` (WeasyPrint 68; los woff2 de `fonts/`
cargan directo con @font-face file://; gotcha: en tablas auto-layout el
padding no separa la celda más ancha de su vecina → usar &nbsp;).
Ricardo lo repasa con su equipo antes de enviarlo a Tatiana. **Precios en USD
son de REFERENCIA** (constantes al inicio del build: base $2.500 único con
quick wins 01-02 incluidos · reclutamiento $1.200 · planeación $1.500 ·
evento $1.800 · reuniones $900 · retainer $600/mes · Submittable a cotizar)
— editarlas y poner `DRAFT = False` (quita la banda "BORRADOR INTERNO")
antes de enviar. Sigue pendiente el ejemplo del correo de grant de Tatiana
(insumo técnico del módulo 01, no bloquea la propuesta).

**Derivada estratégica:** este lead confirmó demanda por un servicio de
"construcción de flujos de trabajo con IA" (tipo AI builder — nombre tomado
por Microsoft) más allá de lo electoral. Pendiente: sumar ese servicio como
el principal en la sección Servicios de `index.html`.

## Convenciones de commit
```
git commit -m "scope: descripción concisa\n\nDetalle si es necesario\n\nCo-Authored-By: Ricardo y Claudio <noreply@anthropic.com>"
git push origin HEAD:main
```
> Firma fija "Ricardo y Claudio" (decisión del usuario, jul-2026) — NO usar
> el nombre del modelo (Opus/Sonnet/Haiku) en el Co-Authored-By.
