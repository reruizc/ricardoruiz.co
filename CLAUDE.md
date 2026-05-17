# ricardoruiz.co — Plataforma Electoral Colombia 2026

## Archivos principales
- `electoral.html` — hub de navegación (senado, cámara, consultas)
- `senado-2026.html` — escrutinio senado, todos los toggles y visualizaciones
- `camara-2026.html` — (en construcción) espejo de senado para cámara
- `endoso-2026.html` — comparación mesa a mesa senado vs cámara
- `previa-1v.html` — simulador de intención presidencial 1ª vuelta
- `oportunidad.html` — **módulo B2B** voto blando afín por candidato (LISTO, ver sección dedicada)
- `veleta.html` — municipios sensibles al cambio (score multidimensional)
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

## Ponderador propio (en construcción)
Pipeline en `tools/ponderador/` que calibra firmas encuestadoras contra el
único ground truth post-Ley 2494: las consultas del 8 de marzo de 2026.
Ver `tools/ponderador/README.md` para flujo de uso.

```
Bases de datos/cne_pdfs/                 → PDFs descargados a mano del CNE
Bases de datos/cne_encuestas_2026.json   → inventario scrapeado del CNE
Bases de datos/cne_encuestas_clasificadas.csv  → con auto-clasificación
Bases de datos/encuestas_porcentajes.csv → % por candidato (manual desde PDF)
Bases de datos/encuestas_distribucion_muestral.csv → muestra por depto
Bases de datos/output_ponderador/ponderador-actual.json  → consume previa-1v.html
Bases de datos/output_ponderador/ponderador-detalle.json → transparencia total
Bases de datos/output_ponderador/representatividad.json  → KL vs censo Divipole
```

Decisiones metodológicas (resumen):
- Sólo el 8-mar como benchmark (Ley 2494 cambió la regla del juego).
- MAE filtra candidatos extintos antes de normalizar (Cepeda no estuvo en Frente).
- `q_firma` ∈ [0.40, 1.00]; firmas no calibradas entran con 1.00 + bandera.
- House effect post-marzo vs mediana semanal por candidato.
- Representatividad muestral: KL + χ² + bandera por depto |delta|≥5pp.

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

### Módulos disponibles (estado actual)
| # | Módulo | Datos | Estado |
|---|---|---|---|
| 01 | Voto histórico | 2015/2019/2023 alcaldía+concejo (S3) | ✓ |
| 02 | Seguridad y delitos | enero 2026 PNP (S3) | ✓ |
| 03 | Comportamiento electoral & MOE | paquete socia 2021-2026 (embebido) | ✓ |
| 04 | Pobreza e IPM | simulado v0 (embebido) | ✓ datos simulados |
| 05 | Arquetipos territoriales | — | pendiente |
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

## Convenciones de commit
```
git commit -m "scope: descripción concisa\n\nDetalle si es necesario\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
git push origin HEAD:main
```
> Usar el nombre del modelo activo (Opus 4.7 / Sonnet 4.6 / Haiku 4.5),
> no un valor fijo. Si Claude está en otro modelo, ajustar.
