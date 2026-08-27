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
- CORS: `https://ricardoruiz.co`

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

El rol de Lambda usa permisos de logs y la política de `policy.json`. La URL ya está
configurada en `brujula-asuncion/config.js`. El panel queda en
`/brujula-asuncion/admin.html`.

La captura es deliberadamente anónima: la Lambda aplica whitelist y no guarda IP,
User-Agent, correo, nombre, coordenadas ni local de votación.
