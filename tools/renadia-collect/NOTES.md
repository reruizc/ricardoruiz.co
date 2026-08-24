# RENADIA · backend de recolección de respuestas

> ## ⛔ DESMONTADO el 13-ago-2026 — nada de esto sigue vivo
>
> Se cerró el Mundial de datos de RENADIA. Se eliminaron, por pedido de Ricardo:
> - **La página**: proyecto Cloudflare Pages `renadia-mundial`
>   (`https://renadia-mundial.pages.dev`) → borrado, hoy responde 530.
> - **Los HTML**: `Bases de datos/DNP/RENADIA-unete-mundial{,-v2,-v3}.html` y la
>   copia de deploy `tools/renadia-pages/index.html` → borrados del disco.
> - **El backend**: API Gateway `1zg0z2trt3` y Lambda `renadia-collect` →
>   borrados. **El endpoint de abajo ya no resuelve.**
>
> **Lo que SÍ sobrevive** (no se tocó a propósito):
> - Las **145 respuestas** en `s3://elecciones-2026/renadia-collect/respuestas/`.
> - Los informes `RENADIA-Informe-Resultados-Mundial2026.{docx,pdf}` y la
>   Evidencia 1.1.1 del informe de actividades del contrato DNP.
> - **Residuos que la CLI no pudo borrar** (`ricardo-mac-cli` no tiene permiso de
>   `iam:DeleteRolePolicy` ni `logs:DeleteLogGroup`) — inofensivos, no ejecutan
>   nada sin la Lambda, pero quedan ahí si se quieren limpiar con una cuenta admin:
>   el rol IAM `lambda-renadia-collect` (+ su policy inline `renadia-collect-inline`)
>   y el log group `/aws/lambda/renadia-collect`.
>
> Lo de abajo queda solo como registro histórico de cómo estaba montado.

Recibe las respuestas de la zona de juegos de `RENADIA-unete-mundial-v3.html`
(las manda por `sendBeacon` a un endpoint) y las guarda en S3. Funciona aunque
el HTML esté **embebido en la web del DNP** (POST cross-origin, CORS abierto).

## Recursos desplegados (cuenta AWS 167386641785 · us-east-1)

- **Lambda** `renadia-collect` — Python 3.13, handler `lambda_function.handler`,
  env `BUCKET=elecciones-2026`, `PREFIX=renadia-collect/respuestas`.
- **Rol** `lambda-renadia-collect` — inline `renadia-collect-inline`
  (logs + `s3:PutObject` sobre `elecciones-2026/renadia-collect/*`). Trust en `trust.json`, permisos en `policy.json`.
- **API Gateway HTTP API** `renadia-collect-api` (id `1zg0z2trt3`) · CORS `*` · POST/OPTIONS.
- **Endpoint (el que va en el HTML, constante `RENADIA_ENDPOINT`):**
  `https://1zg0z2trt3.execute-api.us-east-1.amazonaws.com/`
- (Se creó y luego se borró una Lambda Function URL: la cuenta la devolvía 403;
  por eso se usa API Gateway.)

## Dónde quedan los datos

Un objeto JSON por respuesta, **privado** (no público):
```
s3://elecciones-2026/renadia-collect/respuestas/AAAA/MM/DD/<juego>/<HHMMSS>_<rand>.json
```
`<juego>` = `carta` | `madurez` | `penaltis`. Cada objeto trae el payload del
juego + `sid` (id de sesión del participante, enlaza sus 3 retos), `origen`
(URL donde estaba embebido), `_recibido` (timestamp servidor) y `_ip`.

## Leer / descargar las respuestas

```bash
# listar
aws s3 ls "s3://elecciones-2026/renadia-collect/respuestas/" --recursive
# bajar todo a local
aws s3 sync "s3://elecciones-2026/renadia-collect/respuestas/" ./respuestas/
```
(Para un CSV consolidado se puede escribir un agregador que recorra el prefijo;
pendiente si se necesita.)

## Actualizar el código del Lambda

```bash
cd tools/renadia-collect
zip -j function.zip lambda_function.py
aws lambda update-function-code --function-name renadia-collect --zip-file fileb://function.zip
rm function.zip
```

## Prueba rápida del endpoint

```bash
curl -s -X POST "https://1zg0z2trt3.execute-api.us-east-1.amazonaws.com/" \
  -H "Content-Type: text/plain" \
  --data '{"juego":"prueba","nombre":"test"}'
# -> {"ok": true}
```

## Cambiar a un endpoint del DNP en el futuro

Si el DNP prefiere recibir en su propia infraestructura (Power Automate, Azure
Function, etc.), solo se cambia la constante `RENADIA_ENDPOINT` en el HTML por
esa URL. El resto (sendBeacon + respaldo local) no cambia.
