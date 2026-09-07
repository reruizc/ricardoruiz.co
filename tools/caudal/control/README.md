# Caudal · Órganos de control y altas cortes

## Estado publicado · 7 sep 2026

**10.861 providencias de la Corte Constitucional** (8.216 autos + 2.645
sentencias), rango 2021-01-12 → 2026-09-02, deduplicadas a partir de **51
consultas temáticas** alineadas con los sectores del radar. Publicado en
`s3://caudal-legislativo/metadata/{control.jsonl,control-stats.json}`; la
acción es `{"action":"control","query":"…"}`.

Antes eran 499 con 5 consultas. El salto no vino de una fuente nueva sino de
dos medidas: **`maxprov` no está capado del lado del servidor** (con 100 la
consulta "salud" devuelve 98 providencias; con **1000**, 894, en 2,2 s) y las
consultas pasaron de 5 a 51.

```bash
python3 tools/caudal/control/harvest_jurisprudencia.py fetch --workers 4
python3 tools/caudal/control/harvest_jurisprudencia.py build
aws s3 cp "Bases de datos/leyes-senado/control/dist/s3/control.jsonl" \
  s3://caudal-legislativo/metadata/control.jsonl --content-type application/json
aws s3 cp "Bases de datos/leyes-senado/control/dist/s3/control-stats.json" \
  s3://caudal-legislativo/metadata/control-stats.json --content-type application/json
```
`fetch` cachea por consulta (`raw/corte/{slug}.json`) y es resumible;
`--refrescar` ignora el caché, `--solo "tema"` corre una sola.

## ⚠️ El alcance se declara, no se disimula

El buscador de la relatoría **no expone "todo lo publicado entre dos fechas"**:
exige un texto de búsqueda. Así que el índice es la unión de las 51 consultas,
y eso viaja en `control-stats.json → cobertura` y se imprime en la vista. Un
tema fuera de esa lista devuelve cero, y **cero no significa "no hay
jurisprudencia": significa "no lo hemos cosechado"**. La interfaz lo dice con
esas palabras ("Ninguna de las 51 consultas cosechadas trae «criptoactivos»").
Es la misma regla del índice de bloqueo del Senado y del voto nominal.

15 de las 51 consultas topan el techo de 1000 (salud, pensiones, trabajo,
ambiente, elecciones…): ahí la cobertura es de las 1000 más relevantes, no del
total. Para ampliarlas la vía es partir esas consultas por año (`fini`/`ffin`),
no subir más el tope.

## ⚠️ Tres trampas del HTML de la relatoría

1. **La primera celda no es solo el identificador.** Trae el enlace, un "Ver
   ficha" de adorno y, en los autos de seguimiento, el nombre del caso pegado
   (`A. 1201/26 Departamento de la Guajira - Wayuu (T-302/17)`). El
   identificador es el texto del `<a title="Ver providencia">`; el caso va a su
   propio campo, porque para un auto de seguimiento es lo único que lo nombra.
2. **La tercera celda son dos campos en uno** (`<b>TEMA:</b>… <br>
   <b>RESUMEN:</b>…`) → `sintesis` y `resumen`.
3. **`Sin información` es el marcador de ausencia de la Corte.** Sin filtrarlo,
   8 de cada 10 autos quedaban con el resumen "Sin información RESUMEN: Sin
   información" — el mismo modo de falla del `sancionado: "—"` de la ANLA.
   Ausencia se guarda como vacío (`_sin_marcador`). Tras el fix: 7 de 10.861
   registros sin ningún texto.

## ⚠️ Stdlib pura + curl por subprocess

Sin `requests` ni `bs4`, por dos razones medidas: no están en la Mac M5, y el
TLS de python 3.14 de esa máquina no valida el certificado de
corteconstitucional.gov.co (`CERTIFICATE_VERIFY_FAILED`). Mismo patrón de
`scrape_cne.py` y `tools/leyes-senado/harvest.py`.

## Consejo de Estado · lo que se sabe y lo que falta (7 sep 2026)

**No está conectado y no se inventa.** Se exploraron las cinco vías; esto es lo
medido, para que el próximo intento no repita el camino:

| Vía | Estado |
|---|---|
| `samaicore.consejodeestado.gov.co` · **Swagger PÚBLICO** en `/swagger/v1/swagger.json` (314 KB, 81 rutas, "Servicios SAMAI Para Integraciones") | **la más prometedora**, ver abajo |
| `WebRelatoria/ce/index.xhtml` (JSF/PrimeFaces, en `jurisprudencia.ramajudicial.gov.co` y en `servicios.consejodeestado.gov.co`) | el postback se ejecuta pero **la tabla vuelve vacía** en 4 variantes |
| `servicios.consejodeestado.gov.co/testmaster/nue_decis.asp` | responde 200 pero **congelado en enero de 2020** |
| `testmaster/nue_autos.asp`, `nue_gener.asp` | **HTTP 500** |
| `samai…/BuscadorProvidenciasTituladas.aspx` (WebForms) | el adaptador viejo nunca devolvió resultados verificables |

**Lo concreto del swagger** (esto es lo que hay que retomar):
- El endpoint es **`POST /api/ProvidenciasTituladas`**, cuerpo `ReporteCENDOJIn`:
  `{fechaTitulacionInicio, fechaTitulacionFin, corporacion, modo, boletin?,
  filtro?, busqueda?}`. Es un reporte **por rango de fechas**, o sea el flujo
  completo — justo lo que el buscador de la Corte no permite.
- **`corporacion` = `1100103`**, confirmado: aparece en el único enlace a
  samaicore de la home de consejodeestado.gov.co
  (`/api/DescargarProvidenciaPublica/1100103/11001031500020260605100/<hash>/2`).
  `modo` es un enum {0,1,2}; el enlace público usa `2`.
- **Falta la API key.** El swagger NO declara `securitySchemes`, pero el
  servidor responde `401 · No se envió Api Key`. El header correcto es
  **`ApiKey`** (probado: con `ApiKey: x` responde `Api key no autorizada`,
  mientras `Api-Key`, `X-Api-Key` y `Authorization` siguen diciendo "no se
  envió"). No está en el HTML ni en los JS del portal, porque SAMAI es
  WebForms y llama al core del lado del servidor.
- `DescargarProvidenciaPublica` responde **403 Forbidden** a curl incluso con
  la URL literal de la home — probablemente valida `Referer` u origen.

**Próximo paso concreto:** abrir el geovisor/portal con el navegador y capturar
las peticiones a `samaicore` (`read_network_requests` filtrando `samaicore`),
que es exactamente como se consiguieron la api-key de la SFC y el authkey del
GeoServer de Cúcuta. Con la key, `ProvidenciasTituladas` da el flujo por fechas
y el Consejo de Estado deja de ser una promesa de la portada.

**Procuraduría** queda fuera hasta validar una fuente con identificador y
enlace público estable.
