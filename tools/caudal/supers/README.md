# Caudal · sanciones de superintendencias (el "dapper interno")

Extractor de sanciones/actos de superintendencias y entidades reguladoras para
**Cauce**. Cumple una promesa que ya está escrita en el documento estratégico
(`Propuestas/Cauce-Estado-de-Cosas-Inteligencia-Legislativa.pdf`): las
superintendencias son una de las 9 categorías del "mapa inicial de fuentes"
(18 en "Superintendencias y comisiones"), y el ejemplo estrella del pitch —la
alerta de precisión para una empresa de salud— usa justamente una **circular de
la Supersalud** como una de las dos alertas que importan.

## Estado (piloto vía 1 · LISTO)

`harvest_supers.py` baja **6 fuentes vía Socrata** y las normaliza a un esquema
común de sanción. Verificado end-to-end (2026-07): **6.084 sanciones a nivel
entidad** consolidadas.

```bash
python3 tools/caudal/supers/harvest_supers.py list       # mapa de fuentes
python3 tools/caudal/supers/harvest_supers.py test       # valida mapeos (1 fila/fuente)
python3 tools/caudal/supers/harvest_supers.py fetch       # baja todas las vía 1
python3 tools/caudal/supers/harvest_supers.py fetch --desde 2024-01-01
python3 tools/caudal/supers/harvest_supers.py normalize   # raw -> dist (JSONL + CSV + stats)
```

Salidas (gitignored, como el resto de datos de Caudal):
```
Bases de datos/leyes-senado/supers/
  raw/{slug}.json        crudo por fuente (resumible)
  dist/sanciones.jsonl   consolidado, esquema común
  dist/sanciones.csv     idem (Excel, BOM utf-8)
  dist/stats.json        conteo por fuente
```

## Esquema normalizado

Toda sanción, venga de donde venga, se mapea a estos campos (definidos en
`fuentes.json._schema_normalizado`):

`fuente · fuente_nombre · sector · sancionado · identificacion · tipo_sancion ·
motivo · monto · resolucion · fecha_firmeza · estado · descripcion · _id · _raw`

`_raw` conserva la fila original (trazabilidad — cada alerta cita su fuente,
regla dura del pitch).

## Las tres vías de extracción

| Vía | Qué es | Dificultad | Ejemplos |
|---|---|---|---|
| **1 · Socrata** | dataset JSON directo en datos.gov.co | baja | INVIMA, SECOP I/II, Contraloría, Junta de Contadores |
| **2 · API interna** | endpoint no documentado del portal | media | Superfinanciera (SiriWeb), Supertransporte (WP), SIC (RSS) |
| **3 · Normograma/PDF** | resoluciones/circulares en PDF | alta | Supersalud, Supersociedades |

### Vía 1 — Socrata (implementada)
El patrón de `lab-indicadores` / ponderador. Query directa
`https://www.datos.gov.co/resource/{id}.json?$where=...`. Cero scraping. **Ojo:**
cuatro datasets de Min. Trabajo son **agregados** (por territorial/sector, solo
conteos) → `granularidad: agregado` en el registro, no entran al consolidado por
entidad (sirven de contexto).

### Vía 2 — API interna del portal
Mismo enfoque que la "API oculta" de `leyes.senado.gov.co`.

- **Superfinanciera — IMPLEMENTADA (`harvest_sfc.py`, jul-2026).** El buscador
  SiriWeb es una app Angular que habla con
  `.../api-siri-casillero/.../api/actoAdmin/listarSancionesMercadoValores`. La
  **api-key vive en texto plano en el bundle JS público** (`SiriWeb/main.js`,
  `const Qt = {...apiKey:"..."}`) — se re-extrae en cada corrida con regex
  (`harvest_sfc.py get_api_key()`), tolera rotación (falla claro si el bundle
  cambia de forma o si la key ya no sirve). **Header correcto: `api-key` o
  `Api-Key` — `apiKey`/`x-api-key` dan 401.** 805 sanciones, todas
  `estadoSancion:"En firme"`. Fechas en epoch-millis → ISO (`_epoch_to_iso`,
  descarta año fuera de [2000, hoy+1] en vez de adivinar — la fuente trae un
  typo real, año 3022). `numeroActoAdmin` llega como int → se fuerza a string
  antes de que `build_s3.py` le haga `.strip()`.
  ```bash
  python3 tools/caudal/supers/harvest_sfc.py test    # valida la key + 1 fila
  python3 tools/caudal/supers/harvest_sfc.py fetch   # -> raw/sfc-mercado-valores.json
  ```
  Endpoints hermanos sin implementar: `listaSancionesGeneral`, `listaReporteSanciones`
  (esperan otro payload).
- **Supertransporte** (pendiente): WordPress 6.9 → `?rest_route=/wp/v2/posts`
  (BOM utf-8-sig). Multas como noticias; DeepSeek estructura sancionado/monto
  del cuerpo.
- **SIC** (pendiente): `sic.gov.co/rss.xml` (10 items recientes, título+pubDate).
  Ventana corta.

### Vía 3 — normograma/PDF (registrada, pendiente)
Reusa **el pipeline de gacetas de Caudal fase 3** (`extraer_gaceta.py` +
Lambda acción `gaceta`): bajar PDF → pypdf → DeepSeek estructura el acto
sancionatorio. Supersalud (SharePoint/normograma) y Supersociedades (Liferay,
478 resoluciones + 198 circulares). PDFs viejos → OCR, como las gacetas 90-2005.

## Cómo agregar una fuente

**Vía 1 (Socrata):** una entrada en `fuentes.json.fuentes` con `via:1`,
`socrata_id`, `fecha_col` y el `map` (campo_normalizado → columna_del_dataset).
Descubrir el id y columnas:
```bash
curl -s "https://api.us.socrata.com/api/catalog/v1?domains=www.datos.gov.co&q=sanciones+<entidad>&limit=10"
curl -s "https://www.datos.gov.co/resource/<id>.json?\$limit=1"   # ver columnas
```
Corre `test` para validar el mapeo, luego `fetch <slug>` + `normalize`.

**Vía 2/3:** harvester hermano (`harvest_sfc.py`, `harvest_pdf.py`) que emite
`raw/{slug}.json` con la fila cruda; `normalize_all()` de este script lo
consolida si la fuente tiene `map` en el registro.

## Siguiente sprint (recomendado)

1. ✅ HECHO — `harvest_sfc.py` (Superfinanciera vía 2).
2. ✅ HECHO — `dist/sanciones.jsonl` enganchado a la Lambda (acción `sanciones`)
   y al Radar del cliente (acción `cliente`, sector `financiero` ahora con
   datos reales).
3. Vía 3 (Supersalud) con el pipeline de gacetas — cierra el ejemplo del pitch.
4. Supertransporte + SIC (vía 2, mismo patrón que Superfinanciera).

Ver el mapa completo de las 18+ fuentes y su estado en `fuentes.json`.
