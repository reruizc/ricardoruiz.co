# ricardoruiz.co — Plataforma Electoral Colombia 2026

## Archivos principales
- `electoral.html` — hub de navegación (senado, cámara, consultas)
- `senado-2026.html` — escrutinio senado, todos los toggles y visualizaciones
- `camara-2026.html` — (en construcción) espejo de senado para cámara
- `endoso-2026.html` — comparación mesa a mesa senado vs cámara
- `lang.js` — i18n (co/us/cn); `CLAUDE.md` vive en la raíz del repo

## Worktree y deploy
```
worktree activo: /Users/ricardoruiz/ricardoruiz.co/.claude/worktrees/agitated-rosalind/
deploy:          git push origin HEAD:main   (desde dentro del worktree)
```

## AWS / S3
El usuario **NO tiene AWS CLI instalado localmente** y prefiere subir él
mismo los artefactos a S3. No invocar `aws s3 cp` ni `aws s3 sync` ni
confirmar credenciales AWS. Cuando un script produzca JSONs/CSVs para
S3: dejarlos en disco local y entregar al usuario el comando exacto que
debe correr él (incluyendo ruta origen → prefijo destino), junto con una
lista clara de los archivos generados.

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
| 07 | Saliencia/agenda pública | — | pendiente pipeline |
| 08 | Fricción ciudadana / PQRSD | — | pendiente datos |
| 09 | Simulador what-if | — | pendiente |

### Datos pendientes / faltantes
- Censos electorales históricos por año (potencial 2015/2019/2023) → calcular abstención real
- PQRSD Medellín (datos abiertos)
- MEData / SISC / SIMM
- Pobreza/IPM oficial (DANE / Medellín Cómo Vamos) — reemplazar simulado
- Padrón electoral 2027 cuando salga
- Pipeline scraping (Apify token, YouTube Data API, Google Trends)
- Mapa de actores políticos (concejales, periodistas, influencers)
- Senado/Cámara 2026 a nivel comuna Medellín (S3 actual solo tiene a
  nivel municipio — reprocesar `Congreso_2026_MMV170326.csv` similar al
  script de TER si se necesita drilldown)

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
git commit -m "scope: descripción concisa\n\nDetalle si es necesario\n\nCo-Authored-By: Claude Sonnet 4-6 <noreply@anthropic.com>"
git push origin HEAD:main
```
