# Venta por archivo · Datos por barrio (850.000 c/u)

> ESTADO (2026-07-08): ✅ Archivos en S3 privado · ✅ Lambda `descarga-barrio` + API Gateway desplegados
> (`API_ID=ciupqm47ki`, endpoint `https://ciupqm47ki.execute-api.us-east-1.amazonaws.com/entrega`, pegado
> en `descarga-entrega.html`) · ✅ tab en `descargas.html`. **PENDIENTE: crear los 6 Links de Pago en Wompi
> (PASO 4) y pegarlos en `WOMPI_LINKS` de `descargas.html`; luego `git push`.** Redeploy Lambda:
> `bash tools/descarga-barrio/deploy.sh`.


Entrega automática: **Wompi → `descarga-entrega.html` → Lambda `descarga-barrio` → URL firmada de S3 privado**.
No toca el worker `rr-auth`. Los archivos viven en un prefijo **privado** de S3 (no en `DESCARGAS/`, que es público).

## Piezas
- `lambda_handler.py` — verifica el pago con la API pública de Wompi + firma la URL de S3. Amarra cada
  transacción a UN producto (marcador en S3), re-descarga permitida 30 días.
- `descarga-entrega.html` (raíz del repo) — página de retorno de Wompi.
- `descargas.html` — tab "Datos por barrio · Premium" con las 6 tarjetas (`WOMPI_LINKS` + `BARRIO_PRODUCTOS`).

## Productos (id → archivo → precio)
| id | archivo | precio |
|---|---|---|
| resultados-1v | Resultados_1V_2026_por_barrio_ciudades.xlsx | 850.000 |
| resultados-2v | Resultados_2V_2026_por_barrio_ciudades.xlsx | 850.000 |
| genero-1v | Genero_1V_2026_por_barrio_ciudades.xlsx | 850.000 |
| genero-2v | Genero_2V_2026_por_barrio_ciudades.xlsx | 850.000 |
| edad-1v | Edad_1V_2026_por_barrio_ciudades.xlsx | 850.000 |
| edad-2v | Edad_2V_2026_por_barrio_ciudades.xlsx | 850.000 |

---

## PASO 1 · Subir los 6 archivos a S3 PRIVADO (NO al prefijo público)
```bash
cd "/Users/ricardoruiz/ricardoruiz.co/Bases de datos/output_2v"
for f in Resultados_1V Resultados_2V Genero_1V Genero_2V Edad_1V Edad_2V; do
  aws s3 cp "${f}_2026_por_barrio_ciudades.xlsx" \
    "s3://elecciones-2026/ricardoruiz.co/productos-barrio/${f}_2026_por_barrio_ciudades.xlsx" \
    --content-type "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
done
# Verificar que NO son públicos (debe dar 403):
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/productos-barrio/Genero_1V_2026_por_barrio_ciudades.xlsx"
# -> 403  (correcto: la bucket policy pública NO cubre productos-barrio/)
```

## PASO 2 · IAM role de la Lambda
Rol `lambda-descarga-barrio` con:
- `AWSLambdaBasicExecutionRole` (logs)
- inline policy: `s3:GetObject` + `s3:PutObject` sobre
  `arn:aws:s3:::elecciones-2026/ricardoruiz.co/productos-barrio/*`
  (GetObject para firmar; PutObject/GetObject para los marcadores en `_redenciones/`).

## PASO 3 · Desplegar la Lambda + API Gateway
`bash tools/descarga-barrio/deploy.sh` (crea/actualiza la función; imprime la URL del endpoint).
Runtime `python3.12` (boto3 viene incluido). Timeout 15 s, memoria 256 MB.
Env vars: BUCKET, PREFIX=`ricardoruiz.co/productos-barrio/`, WOMPI_BASE=`https://production.wompi.co/v1`,
PRECIO_MIN=`85000000`.

Copiar la URL del endpoint (`https://XXXX.execute-api.us-east-1.amazonaws.com/entrega`) a la constante
`API` de `descarga-entrega.html`.

## PASO 4 · Crear los 6 Links de Pago en Wompi  ← LO HACE RICARDO (dashboard Wompi)
Por CADA producto, en el panel de Wompi → Links de pago:
- Monto: **850.000 COP** · Moneda COP · Nombre = título del producto.
- **URL de redirección**: `https://ricardoruiz.co/descarga-entrega.html?p=<id>`
  (ej. `...?p=genero-1v`). El `<id>` es la columna "id" de la tabla de arriba. **Esto es lo que
  amarra el pago al producto correcto.**
- Copiar la URL del link (`https://checkout.wompi.co/l/XXXXXX`) y pegarla en `WOMPI_LINKS` de `descargas.html`.

## PASO 5 · Pegar los links y probar
- `descargas.html` → `WOMPI_LINKS = { 'genero-1v':'https://checkout.wompi.co/l/...', ... }`
- Prueba end-to-end con el **modo sandbox** de Wompi primero (WOMPI_BASE sandbox + links sandbox),
  luego producción.
- Push: `git push origin HEAD:main`.

## Notas de seguridad
- Archivos en prefijo privado → nunca accesibles sin pasar por la Lambda.
- La Lambda exige `status=APPROVED` y `amount >= 850.000`, y amarra tx→producto (una compra = un archivo).
- URL firmada TTL 10 min; re-descarga 30 días con la misma transacción.
- Riesgo aceptado: quien comparta su `?p=&id=` deja re-descargar SU archivo a un tercero (como compartir
  el recibo). No permite bajar otros productos.
