# Backend de Brújula Asunción

Guarda una respuesta anónima por objeto en S3 y ofrece lectura administrativa protegida
por el `isAdmin` del sistema `rr-auth`.

## Recursos AWS

- Lambda Python 3.13: `brujula-asuncion-respuestas`
- API Gateway HTTP API:
  - `POST /respuesta`
  - `GET /admin/respuestas`
  - `OPTIONS /{proxy+}`
- Bucket: `elecciones-2026`
- Prefijo privado: `ricardoruiz.co/brujula-asuncion/respuestas/`
- CORS: **en dos capas** — la `CorsConfiguration` de la HTTP API (responde el preflight) y
  `ALLOWED_ORIGIN` de la Lambda (admite **lista separada por comas**). Hay que tocar las dos.

Desplegado el 26 de agosto de 2026:

- API: `https://ha0iona65c.execute-api.us-east-1.amazonaws.com`
- Lambda: `arn:aws:lambda:us-east-1:167386641785:function:brujula-asuncion-respuestas`
- Rol: `arn:aws:iam::167386641785:role/lambda-brujula-asuncion`

Variables de entorno:

```text
BUCKET=elecciones-2026
PREFIX=ricardoruiz.co/brujula-asuncion/respuestas
ALLOWED_ORIGIN=https://ricardoruiz.co
AUTH_ME=https://rr-auth.reruizc.workers.dev/auth/me
MAX_ADMIN_ROWS=10000
```

## Servir la Brújula desde otro dominio

`ALLOWED_ORIGIN` acepta varios orígenes separados por comas y `response()` devuelve el que
coincida (nunca `*`: con `Authorization` el navegador lo rechaza). Un solo valor se comporta
exactamente como antes.

⚠️ **Sin esto, mudar la página de dominio falla en silencio.** El `POST /respuesta` viaja
como *simple request* (`Content-Type: text/plain`), así que llega al servidor igual, pero el
navegador bloquea la respuesta: el `catch` del front solo hace `console.warn` y nunca marca
el `sessionStorage`, de modo que quien repita el test en la misma sesión duplica registros.
Y `admin.html` sí se cae entero, porque manda `Authorization` y eso dispara preflight.

⚠️⚠️ **El preflight NO lo responde la Lambda: lo responde API Gateway.** Medido el
2-sep-2026 contra producción: un `OPTIONS /admin/respuestas` con `Origin:
https://brujulapolitica.pages.dev` devuelve **204 sin un solo header de CORS**, mientras que
el mismo pedido desde `https://ricardoruiz.co` sí trae `access-control-allow-origin`. O sea
que la HTTP API tiene su propia `CorsConfiguration` con un único origen y contesta el
preflight sin invocar la Lambda. **Tocar solo `ALLOWED_ORIGIN` no alcanza** — el panel de
administración seguiría roto desde el dominio nuevo.

Al agregar un dominio son TRES comandos, y el tercero es el que de verdad destraba el
preflight:

```bash
cd tools/brujula-asuncion-backend && zip -j /tmp/brujula.zip lambda_function.py
aws lambda update-function-code --function-name brujula-asuncion-respuestas \
  --zip-file fileb:///tmp/brujula.zip

# ⚠️ --environment REEMPLAZA todo el bloque: van las cinco variables, no solo la que cambia
aws lambda update-function-configuration --function-name brujula-asuncion-respuestas \
  --environment 'Variables={BUCKET=elecciones-2026,PREFIX=ricardoruiz.co/brujula-asuncion/respuestas,ALLOWED_ORIGIN="https://ricardoruiz.co,https://brujulapolitica.pages.dev",AUTH_ME=https://rr-auth.reruizc.workers.dev/auth/me,MAX_ADMIN_ROWS=10000}'

# el que responde el preflight (api id = el subdominio del endpoint)
aws apigatewayv2 update-api --api-id ha0iona65c --cors-configuration '{
  "AllowOrigins":["https://ricardoruiz.co","https://brujulapolitica.pages.dev"],
  "AllowMethods":["GET","OPTIONS","POST"],
  "AllowHeaders":["authorization","content-type"],
  "MaxAge":86400}'
```

Comprobar que quedó, sin abrir el navegador:

```bash
curl -s -o /dev/null -D- -X OPTIONS "https://ha0iona65c.execute-api.us-east-1.amazonaws.com/admin/respuestas" \
  -H "Origin: https://brujulapolitica.pages.dev" -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: authorization" | grep -i access-control-allow-origin
```

El rol de Lambda usa permisos de logs y la política de `policy.json`. La URL ya está
configurada en `brujula-asuncion/config.js`. El panel queda en
`/brujula-asuncion/admin.html`.

La captura es deliberadamente anónima: la Lambda aplica whitelist y no guarda IP,
User-Agent, correo, nombre, coordenadas ni local de votación.
