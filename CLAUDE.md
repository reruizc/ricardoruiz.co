# ricardoruiz.co — Plataforma Electoral Colombia 2026

## Archivos principales
- `electoral.html` — hub de navegación (senado, cámara, consultas)
- `senado-2026.html` — escrutinio senado, todos los toggles y visualizaciones
- `camara-2026.html` — (en construcción) espejo de senado para cámara
- `endoso-2026.html` — comparación mesa a mesa senado vs cámara
- `previa-1v.html` — simulador de intención presidencial 1ª vuelta
- `oportunidad.html` — **módulo B2B** voto blando afín por candidato (LISTO, ver sección dedicada)
- `veleta.html` — municipios sensibles al cambio (score multidimensional)
- `test-presidencial-2026.html` — **test de arquetipo emocional + lectura LLM** (LISTO v1, ver sección dedicada)
- `analisis-estructural.html` — **Lab de Políticas Públicas y Prospectiva** · hub del lab + módulo análisis estructural (MicMac · DEMATEL · ISM modernizado, fuzzy, valencias firmadas, copiloto IA). LISTO, ver sección dedicada.
- `mactor.html` — **Lab** · módulo análisis de actores y conflictos (MID + MAO, copiloto IA). LISTO.
- `problema-publico.html` — **Lab** · módulo problema público (Eightfold Path de Bardach condensado a 5 mecánicas + capa metodológica profunda con wizard de síntoma, árbol del problema CEPAL/Ortegón, test Rittel-Webber y selector de marco analítico). Cloud-save + 3 acciones IA + Issue Paper export. LISTO (Sprint A).
- `evaluacion.html` — **Lab** · módulo evaluación de política (OCDE-DAC + Mayne + CEPAL/ILPES + Pre-Analysis Plans + literatura 2020-2026). **8 mecánicas**: pregunta evaluativa (tipo + alcance + tipología Sinergia DNP) · teoría de cambio · indicadores SMART · selector de método (14 métodos · frontera 2020-2026) · criterios OCDE-DAC · análisis económico (CBA · MVPF · CEA) · plan operativo · resultados. Detección automática de tratamiento escalonado con warning TWFE (Goodman-Bacon 2021) redirigiendo a DID escalonado (Callaway-Sant'Anna 2021). Cloud-save + 3 acciones IA + plan .md + **Pre-Analysis Plan .md** (AEA RCT Registry / OSF compatible, 13 secciones con MHT correction pre-registrada) + matriz .csv. LISTO (Sprint B + B v2).
- `alternativas.html` — **Lab** · módulo Alternativas de Política (Zwicky 1969 + Lempert/Walker RDM 2003 + Ritchey + Howard + Keeney + MVPF Hendren 2020 + CEA J-PAL). 6 mecánicas: variables de decisión · opciones por variable · matriz morfológica · alternativas ensambladas · robustez en 4 escenarios + lente económica · decisión final. Cloud-save + 4 acciones IA + memo .md + matriz .csv + ficha CONPES light .pdf + envío bidireccional a problema-publico + envío a AIN. LISTO (Sprint C).
- `ain.html` — **Lab** · módulo Análisis de Impacto Normativo (DNP/Función Pública Decreto 1081/2015 + 1273/2020 + RIA OCDE 2012/2022 + Sunstein Simpler 2013 + Hahn-Tetlock 2008 + Stigler 1971 + Mashaw 2018). 6 mecánicas: problema regulatorio (tipo de falla) · objetivos normativos medibles · opciones regulatorias (6 familias) · matriz de impactos (5 categorías) · consulta pública + 5 riesgos regulatorios · implementación + monitoreo + cláusula de revisión. Cloud-save + 3 acciones IA + memo .md + matriz .csv + memo CONPES regulatorio .pdf + auto-import desde pp/alt + envío a evaluacion. LISTO (Sprint D).
- `lab-recursos.js` — catálogo compartido de 32 recursos en 5 categorías; cargado por los 6 módulos del lab.
- `pricing.html` — planes (Básico / Pro 39.900 COP · Premium 99.900 COP · Personalizado)
- `lang.js` — i18n (co/us/cn); `CLAUDE.md` vive en la raíz del repo

## Tareas pendientes — `previa-1v.html`
- **Gráfico temporal de evolución por candidato** (pendiente, prioridad media):
  un line chart ponderado que muestre cómo crece o decrece cada candidato a lo
  largo del tiempo, usando los datos crudos de cada encuesta + los pesos del
  ponderador propio (`Bases de datos/output_ponderador/ponderador-detalle.json`,
  campo `contribuciones`). Cada punto del eje X es una semana ISO; cada línea
  un candidato. Debería respetar el toggle día/noche y la paleta del proyecto.

## Módulo Veleta — `veleta.html` (por construir, prioridad ALTA, ventana hasta 1ª vuelta)

Producto B2B para equipos de campaña: mapa de **municipios veleta** (sensibles al
cambio electoral) con score multidimensional. Es el bottom-of-funnel comercial
del ciclo electoral 2026 — diferenciador frente a herramientas genéricas de
visualización porque combina histórico + competitividad + peso en una sola métrica
defendible.

**Definición del Score Veleta (0–100)** — promedio ponderado:
- **Swing histórico (40%)**: `|Δ pct_Petro_2022 − pct_Petro_2018|`, normalizado al
  percentil 95 nacional. Bonus +15 pts si el ganador del municipio cambió entre
  ciclos (`top1_2018 ≠ top1_2022`). Petro candidato en ambas presidenciales =
  proxy directo del eje izquierda↔resto.
- **Competitividad (40%)**: margen `top1 − top2` en presidencial 2022 sobre
  votos válidos. Lineal invertido: margen 0 pp → 100, margen ≥25 pp → 0.
- **Peso electoral (20%)**: `log(censo_municipal)` normalizado min/max nacional.
  Filtra ruido de municipios pequeños sin sacrificar cobertura.

`Score = 0.4·swing + 0.4·comp + 0.2·peso`. Municipios con score ≥ umbral (default
70, slider 50–90) se renderizan con **patrón rayado SVG** (`<pattern>` global +
`fillColor: 'url(#vel-stripes)'` — Leaflet pasa el fill textualmente al path,
funciona porque la referencia se resuelve por id en el DOM). Resto del mapa:
gradiente lineal gris frío → ámbar → rojo según score.

**Datos de entrada** (todos en S3):
```
historicos/pres-2018-v1/por-mun.json   { "depCod-munCod": { candidatos:{1:{nombre,pct},...}, votos_validos } }
historicos/pres-2022-v1/por-mun.json   misma estructura
puestos-censos-agg.json                { porMun: { "depCod-munCod": int }, nacional: int }
mapas-2026/DEPARTAMENTOS2.json         GeoJSON deptos
mapas-2026/MUNICIPIOSX.json            GeoJSON municipios nacional (9 MB)
```

**Estructura UX**:
1. Header + breadcrumb (mismo nav que `previa-1v.html`).
2. Sección intro con 3 cards explicando los componentes del score (transparencia
   metodológica = clave para venta B2B).
3. Toggle nivel territorial (departamental por defecto / municipal). Slider de
   umbral del rayado.
4. Shell 2 columnas: mapa Leaflet + panel lateral con leyenda, detalle de
   municipio en hover, top-30 ranking clickeable, CTA de venta ("¿Equipo de
   campaña? Reporte territorial 3M COP").
5. Drill-down por click en depto → muestra solo municipios de ese depto.

**Componentes reutilizables de `previa-1v.html`**:
- Nav, breadcrumb, header, day-mode (toggleTheme).
- Helpers `pad()`, hover-chip flotante, estructura `.shell`/`.map-wrap`/`.panel`.
- Patrón Leaflet: SVG renderer (NO canvas — el rayado necesita SVG).
- `colorWithIntensity()` no aplica aquí (cambia paleta a gradiente score-driven).

**Color tokens nuevos** (variantes a las globales):
```css
--vel-low:#2d3340;  --vel-mid:#f59e0b;  --vel-high:#f87171;
/* Stops del gradiente: 0→#2d3340, 40→#463c3c, 60→#b46e32, 75→#f59e0b, 100→#f87171 */
/* Acento del módulo (en lugar de --blue): --orange (#fb923c) */
```

**Patrón de rayado SVG** (insertar en `<body>` antes del nav, una sola vez):
```html
<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <defs>
    <pattern id="vel-stripes" patternUnits="userSpaceOnUse" width="6" height="6"
             patternTransform="rotate(45)">
      <rect width="6" height="6" fill="#f87171"/>
      <line x1="0" y1="0" x2="0" y2="6" stroke="#fff" stroke-width="2.2" stroke-opacity=".45"/>
    </pattern>
    <!-- duplicar como #vel-stripes-day con fill #dc2626 + stroke-opacity .7 para day-mode -->
  </defs>
</svg>
```

**Notas de cálculo**:
- En agregado por depto: promedio de score ponderado por censo. Conteo
  independiente de "veleta count" (`recs.filter(r => r.score >= threshold).length`)
  para que el slider del umbral repinte sin recomputar scores.
- Header del mapa: número de municipios veleta + % del censo nacional que
  representan ("censo en juego"). Es el número que un jefe de campaña quiere ver.

**Riesgo metodológico**: la elección de Petro como ancla del swing carga el
score hacia volatilidad en el eje izquierda. Es defendible (eje principal de la
contienda 2026) pero documentar en el footer y en el reporte de venta — un
consultor experto lo va a preguntar.

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

## Kart Electoral — `kart-presidencial1v.html`

Juego de karts estilo Mario Kart / CTR con los 8 candidatos presidenciales
2026. Single-file HTML autocontenido (~3000 líneas), sin build step. Linkeado
desde `index.html` (proyectos, en es/en/zh).

### Tech base
- **Mode 7 fake-3D** sobre Canvas 2D. Resolución interna `IW=480, IH=270`,
  escalada al viewport con `imageSmoothingEnabled=false` (look pixelart).
- **Texture procedural 4096×4096** (`TRACK_SIZE`, ~64 MB ImageData) que se
  samplea por inverse-mode-7 cada frame. Bitwise `& TRACK_MASK` (potencia de 2)
  para wrap rápido. La pista misma ocupa una zona pequeña del centro; la
  textura grande mantiene las repeticiones lejos en la fog.
- **Inner loop mode 7** (renderMode7): por cada scanline `y`, distancia
  `dist = CAM_HEIGHT * FOV / yy`, sample paso `dist/FOV`. Píxeles en
  `groundImg` (ImageData reusada — alpha pre-rellenada).
- **Cámara**: chase camera 28 unidades detrás del jugador
  (`CAM_DIST=28`), altura `CAM_HEIGHT=32`, `FOV=300`, `HORIZON=102`.

### Pista — silueta de Bogotá
- `RAW_CENTERLINE`: 41 vértices que aproximan la silueta D.C. (Suba bulge NW,
  Bosa SW, San Cristóbal SE knee, Usaquén tip N, Cerros recta E, notch oeste).
  Ajustada con `CL_OFFSET_X=1024, CL_OFFSET_Y=924` para centrar en 4096².
- **Importante**: arranca en el sur ([1080,1880] raw → world [2104,2804])
  y va sentido **horario**. Si rotás el start a otra parte del lazo, validá
  que el `totalAngle` de detección de vueltas siga decreciendo (ver más abajo).
- `posAtParam(t)`: devuelve `{x, y, angle}` interpolando la polilínea por
  longitud acumulada (`CL_LENS`/`CL_TOTAL`).
- `buildTrack(c, S)` dibuja: pasto granulado, edificios fantasma fuera del
  loop, berma ladrillo, asfalto en 3 capas, carril TM rojo tenue, kerbs en
  curvas, líneas blancas borde, línea de meta a cuadros, banner BOGOTÁ con
  bandera amarilla/azul/roja, chevrons amarillos pre-meta.

### Detección de vueltas
- `totalAngle` = ángulo acumulado del jugador alrededor de
  `(TRACK_CX, TRACK_CY)` = promedio de vértices del centerline.
- En sentido horario (canvas y-down), `totalAngle` **decrece**. Lap cuando
  `totalAngle <= -2π`. **Si la pista arranca al norte** (jugador encima del
  centroide), la dirección se invierte y el lap nunca se cuenta — bug
  histórico que rompió la versión anterior con start [1024, 350].
- IA usa `t` lineal (`ai.t += ai.speed`); cada wrap a `>= CL_TOTAL` incrementa
  `ai.lap`. Inicializan en `lap: 0` y `t = CL_TOTAL - offset` (grilla detrás
  del jugador) para que la primera cruzada de meta los pase a lap 1 sin
  regalarles distancia.

### Candidatos
- Array `CANDIDATES` (8), cada uno con:
  - `color` (del partido, según `previa-1v.html`): Cepeda `#51458F`,
    Abelardo `#000062`, Paloma `#1866DF`, Claudia `#d9db24`,
    Fajardo `#EEAA22`, Murillo `#16a34a`. Botero `#d4af37` y
    Caicedo `#ff6eb4` son locales (no están en previa).
  - `features`: `hairStyle` (`curly`/`short`/`shortF`/`long`/`bald`),
    `hair` (color), `skin` (`SKIN.fair/medium/dark`), `glasses`, `beard`.
  - `photo`: URL S3 (Cepeda, Abelardo, Paloma) o Wikipedia (Claudia,
    Fajardo, Murillo) o `null` (Botero, Caicedo — pendientes de subir).
- `skill` 0.90–1.00 multiplica la velocidad base de la IA (~3.55).
  Bogotá da home boost ×1.05 (Claudia), Cundinamarca ×1.02 (Botero).
- **Foto pendiente**: subir a `/Fotos-presidenciales/` en S3 con formato
  300×300: `CLAUDIA+LOPEZ.jpg`, `SERGIO+FAJARDO.jpg`, `LUIS+GILBERTO+MURILLO.jpg`,
  `SANTIAGO+BOTERO.jpg`, `CARLOS+CAICEDO.jpg`. Las de Wikipedia pueden
  fallar por hotlinking; el fallback dibuja iniciales en círculo del color.

### Sprite unificado del kart
- `drawKartSprite(c, candidate, opts)` dibuja al origen; el caller hace
  `translate/rotate/scale`. Mismo sprite para jugador (escala `KART_SCALE=1.10`)
  y para IA (escala calculada por proyección).
- Colores derivados de `candidate.color` con `darkenHex/lightenHex`:
  `carBase, carDark, carDarker, carLight, carLighter, carShine, carCabin`.
- Cabeza vista **desde atrás** (cámara detrás del kart): mayoritariamente
  silueta de cabello con color del partido en el cuello de camisa. Estilos:
  `long` (cae a hombros, flequillo), `shortF` (corte corto femenino),
  `short`, `curly` (bumps irregulares), `bald` (corona + skin top).
- Llantas delanteras: elipses 6×11 (alargadas) que rotan hasta `0.75 rad`
  (~43°) con el steering — **importante** para que el giro sea visible.
  Traseras 10×16 con spin acumulado por velocidad.

### Proyección y rivales
- `projectWorld(wx, wy)` retorna `{x, y, kartScale, lmScale, dist}`:
  - `kartScale = (CAM_DIST / rx) * KART_SCALE` — a la distancia del jugador
    da exactamente el mismo tamaño que el sprite del jugador.
  - `lmScale = FOV / rx` — escala "intrínseca" para landmarks; multiplicada
    por `obj.size` (controla qué tan grande es cada landmark).
- En `renderWorldObjects`: `RIVAL_BOOST = 1.7` multiplica el `kartScale` de
  los rivales (intermedio entre tamaño igual al jugador y la versión gigante).

### Landmarks — al BORDE de la pista
- `placeOnEdge(tFrac, lateralOff, type, size, name)` resuelve un landmark
  a coordenadas world a partir de un t (fracción del lazo) y un offset
  lateral. `lateralOff > 0` = derecha del sentido de marcha = exterior CW.
- Asfalto halfwidth = 110, berma ~145, así que offsets ≥165 quedan en pasto.
- Tipos definidos (cada uno con sprite procedural detallado tipo PS1):
  `plaza` (Plaza Bolívar con estatua, palomas, farolas),
  `capitolio` (6 columnas, frontón, bandera ondeando),
  `candelaria` (7 casas coloniales con tejas),
  `parque` (cipreses, banca, iglesia con cruz),
  `campin` (estadio oval con cancha + 4 torres luz),
  `arena` (Movistar, domo con paneles + entrada),
  `tm` (TransMilenio articulado, 8 ventanas, faja blanca, logo),
  `tribune` (4 niveles graduados con público + banner sponsor).

### Render pipeline (por frame)
1. `renderSky(ictx, dayness, rainK)` — gradiente, sol/luna, estrellas,
   nubes con parallax (2 capas), Cerros Orientales (Monserrate + Guadalupe).
2. `renderMode7(dayness, rainK)` — piso vía sample del trackData.
3. `renderWorldObjects(ictx, dayness)` — proyecta IA + landmarks + tribunas,
   ordena far-to-near, dibuja.
4. `renderSmoke(ictx)` — partículas de escape (sólo en movimiento).
5. `renderPlayerKart(ictx, dayness)` — sprite del jugador encima.
6. `renderRain(ictx, rainK)` — streaks + tinte azul-gris.
7. `ctx.drawImage(ic, ...)` — escala el canvas interno al viewport, con
   shake aleatorio si `speed > 0.7 * MAX_FWD`.
8. `renderMinimap()` — canvas 130×150 abajo derecha con trazado, posición
   del jugador (flecha), markers IA y landmarks.

### Día/noche y lluvia (independientes)
- Día/noche: `getDayness(timeMs)` cicla cada 4 min (`CYCLE_MS=240000`):
  42% día → 8% sunset → 42% noche → 8% sunrise. `dayness ∈ [0,1]`.
- Lluvia: estado `rainState` `dry`/`wet`. Próximo aguacero en
  `nextRainAt = raceTimeMs + 90 a 140 s`. Duración `35–55 s`. Fade in/out
  de 5 s. `getRainIntensity()` retorna 0..1. Decoupled del día/noche.

### Estados y flujo
- `state`: `'menu'` → `'select'` → `'countdown'` → `'racing'` → `'finished'`.
  `'paused'` se intercambia con `'racing'` vía `ESC` o botón `#btn-pause`.
- `resetRace()` reinicia jugador, IA, lapTimes, smoke, rain.
- `chooseCandidate(id)` setea `selectedCandidate`, llama `resetRace`,
  arranca countdown, `initAudio()` (engine sintetizado + beeps).

### Layout HTML
- `<nav>` con logo Ricardo.Ruiz, selector de país (lang.js compartido),
  Proyectos / Noticias / Planes / Iniciar sesión / Registrarse — copiado
  literal de `index.html` para mantener identidad visual.
- `<main id="game-wrap">` flex-1 contiene el `<canvas#game>`, todos los
  HUDs (`#hud`, `#hud-track`, `#hud-laps`, `#hud-pos`), el panel
  `#standings` (top-4 con foto), el `<canvas#minimap>`, y los modales
  (menu, select, countdown, pause-overlay, finish-overlay).
- Cursor custom z-index 9999/9998 (no 100000 como en otras páginas — match
  con index.html).

### Tunables principales (top del script)
```
ACCEL=0.058 BRAKE=0.085 REV_ACCEL=0.030 FRICTION=0.985
MAX_FWD=4.40 MAX_REV=-1.60 TURN_RATE=0.050 TURN_RAMP=1.30
CAM_HEIGHT=32 CAM_DIST=28 FOV=300 HORIZON=102
KART_SCALE=1.10 TOTAL_LAPS=3 CYCLE_MS=240000
TRACK_SIZE=4096 TR_HALF_WIDTH=110
RIVAL_BOOST=1.7 (en renderWorldObjects)
```

### Pendientes / próximas iteraciones
- Subir 5 fotos faltantes a S3 (Claudia, Fajardo, Murillo, Botero, Caicedo).
- Reemplazar URLs en `CANDIDATES[].photo` cuando estén arriba.
- Refinar más la silueta de Bogotá si queda corta.
- Sprites de landmarks como PNG en S3 si la versión procedural no alcanza.
- Pistas adicionales: una por departamento clave (Cauca, Antioquia,
  Magdalena, Bolívar, Atlántico, Chocó, Cundinamarca).

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
proyecto-dc.html                          hub: 9 tarjetas de módulos + secciones descriptivas
proyecto-dc/voto-historico.html           módulo 01
proyecto-dc/seguridad.html                módulo 02
proyecto-dc/comportamiento-electoral.html módulo 03
proyecto-dc/pobreza-ipm.html              módulo 04
proyecto-dc/gobierno-criminal.html        módulo 06
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
| 08 | Fricción ciudadana / PQRSD | — | pendiente datos |
| 09 | Simulador what-if | — | pendiente |

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
(comparte con `kart-presidencial1v.html`).

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

### Lo que falta (pendientes activos)

1. **Memes procedurales** — 30 imágenes (6 candidatos × 5 arquetipos),
   1080×1080 JPG sin texto encima. Ricardo los va generando.
   Naming: `{candidato}-{arquetipo}.jpg` (ej `cepeda-proteccion.jpg`).
   Local: `Bases de datos/test-presidencial/memes/` (gitignored).
   S3: `congreso-2026/output/test-presidencial/memes/` (prefijo
   público). Brief y referentes culturales por arquetipo en
   `memes-spec.txt`. Cuando haya ≥1 set completo, prender el módulo
   de "compartir como meme" (canvas que pinta el mensaje_corto +
   watermark + descarga PNG / compartir).
2. **Revisión humana del banco de preguntas** — Ricardo edita el Excel
   `banco-preguntas-v1.xlsx`. Falta `xlsx_to_json.py` (script inverso)
   para reintegrar al JSON canónico.
3. **Contactar a El País Cali** — enviar la propuesta PDF y arrancar
   el embed antes del 24 de mayo idealmente. Lanzar 20-23 may, correr
   hasta 31 may.
4. **Iterar el prompt de DeepSeek** según comportamiento real (la
   adherencia de tono ya está blindada por post-proceso; la regla de
   no inventar rasgos del barrio funciona bien; vigilar la latencia
   contra el límite de 30 s).

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

## Lab de Políticas Públicas y Prospectiva (Sprints A + B + C + D · LISTO)

**El hub vive en `analisis-estructural.html`** (mismo archivo, rebrandeado).
Los 6 módulos del lab están operativos:

| # | Módulo | Archivo | Estado |
|---|---|---|---|
| 1 | Problema público | `problema-publico.html` | ✓ vivo (Sprint A) |
| 2 | Análisis estructural | `analisis-estructural.html` (mismo HTML que el hub) | ✓ vivo |
| 3 | Análisis de actores | `mactor.html` | ✓ vivo |
| 4 | Evaluación de política | `evaluacion.html` | ✓ vivo (Sprint B + B v2 · literatura 2020-2026) |
| 5 | Alternativas de política | `alternativas.html` | ✓ vivo (Sprint C) |
| 6 | Análisis de Impacto Normativo | `ain.html` | ✓ vivo (Sprint D) |

Sólo `analisis-estructural.html` figura en el listado de proyectos de
`index.html` (como "Análisis Estructural de Sistemas"). Desde su hub se
llega a los otros 5 módulos. El hub-grid se renderiza en 3 cols × 2 rows
en desktop (3+3) para acomodar las 6 cards limpiamente. Cada módulo
tiene cross-links amarillos a los otros 2-4 en su stage-results.

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

### Worker rr-auth — endpoints del lab

Total **42 endpoints** (7 micmac + 7 mactor + 7 pp + 7 ev + 7 alt + 7 ain),
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
```

**DeepSeek:** API key `DEEPSEEK_API_KEY` como secret del worker
(misma que la Lambda `test-presidencial-explica`). Modelo
`deepseek-v4-flash`. AbortSignal 28s. Cache hash24 con
`PROMPT_VERSION='v1'` (bumpear al cambiar prompts para invalidar cache).

**Plan gate (común a los 6 módulos):**
```js
MICMAC_MAX_PROJ = MACTOR_MAX_PROJ = PP_MAX_PROJ = EV_MAX_PROJ = ALT_MAX_PROJ = AIN_MAX_PROJ = { free:1, pro:5, premium:25, full:50 }
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

### Cómo agregar una acción IA nueva

1. Definir un `PROMPT` constante con regla JSON estricta.
2. Crear `_micmacNueva(env, payload)` que devuelve `{ok, data}` o
   `{ok:false, error}`.
3. Registrar en `COPILOTO_ACTIONS` con `{fn, planes, plan}`.
4. Frontend: nueva función `iaNueva()` en analisis-estructural.html
   con loading state, plan gate y render del resultado.

### Backlog del lab

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

**Reservados para después de los 6 módulos:**
- **Sprint E** — datos municipales (~1.100 muns × 5 indicadores)
  precargados desde DANE / Policía / MEN microdatos. Beneficia a los
  6 módulos cuando estén.
- **Sprint F** — escenarios prospectivos: vista "what-if" sobre MicMac,
  Mactor, problema-publico, alternativas y AIN. Los 4 escenarios de
  Alternativas (C.5) son un primer paso editable.
- **Sprint G** — informe combinado de los 6 módulos exportado como PDF
  dinámico (un solo entregable con problema + variables del sistema +
  actores + alternativas + AIN + plan de evaluación).

**Mejoras de módulos vivos:**
- **Mactor MIDI** (opcional) — matriz pivotada de influencias
  indirectas entre actores (multiplica MID consigo misma).
- **Problema-Público v2** — sub-vista de árbol de objetivos (espejo
  del árbol del problema, lado positivo) y exportación PowerPoint.
- **Alternativas v2** — integración QCA (Ragin) para identificar
  configuraciones suficientes/necesarias en alternativas multi-caso.
  Reusa la infraestructura de matriz incompat de Sprint C.
- **Alternativas v2** — análisis de sensibilidad sobre ratings y
  probabilidades de escenarios (Monte Carlo cliente-side).

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

## Convenciones de commit
```
git commit -m "scope: descripción concisa\n\nDetalle si es necesario\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
git push origin HEAD:main
```
> Usar el nombre del modelo activo (Opus 4.7 / Sonnet 4.6 / Haiku 4.5),
> no un valor fijo. Si Claude está en otro modelo, ajustar.
