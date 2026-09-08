# Candidato 360 · buscar y validar las redes de la candidatura

El paso 2 del wizard de `candidato-360.html` preguntaba un mote y seguía de
largo: la escucha de medios y redes se montaba sobre un texto que **nadie
comprobó**. Ahora la persona marca en qué redes está (X, TikTok, Instagram),
escribe el usuario, y antes de construir el punto de partida la plataforma
busca esa cuenta y dice si parece ser la suya.

## Qué hace, en orden

| Paso | Fuente | Qué aporta |
|---|---|---|
| **1. Sondeo** | El endpoint público de cada red: el widget «Follow» de X (`cdn.syndication.twimg.com`), el **oEmbed** de TikTok y los metadatos `og:` del perfil de Instagram | Lo único que dice si la cuenta **existe** y con qué nombre. Sin llaves ni sesión |
| **2. Señales abiertas** | Google News RSS con el nombre y el nombre público (12 meses) | Si esa persona ya aparece en prensa y con qué rol — sirve para detectar el homónimo |
| **3. Veredicto** | DeepSeek V4 Flash | Lee **solo** lo anterior y devuelve, red por red, `confirmado · probable · dudoso · no_encontrado · no_verificable` con una frase de por qué |

Cache en S3, 7 días, con el resultado del sondeo dentro de la llave: si mañana
la cuenta aparece o cambia de nombre es otra pregunta, y no puede contestarla
el cache de ayer.

## Las dos reglas que sostienen esto

- **Un sondeo que no responde NO es un perfil falso.** Las tres redes bloquean
  tráfico de datacenter de a ratos. La Lambda distingue «no existe» (404
  limpio) de «no pude comprobarlo» (bloqueo, timeout, muro de login) y el
  frontend los pinta distinto: `Sin cuenta` en coral, `Sin comprobar` en ámbar.
- **El sondeo manda sobre el modelo.** DeepSeek no puede subir un veredicto por
  encima de la evidencia: está en el system prompt y se vuelve a imponer en
  código (`_sellar_veredictos`) porque un prompt no es un control. Un
  «confirmado» sobre una red que no contestó se degrada a `no_verificable`
  antes de salir.

Validar **nunca bloquea**. Si la red no deja comprobar o el endpoint todavía no
está desplegado, el wizard sigue y la candidatura queda guardada con
`redes.validado = false`. Un candidato no se puede quedar por fuera de su
propia campaña porque X no contestó.

## Contrato

`POST` (la llave de DeepSeek no puede viajar al navegador: este repo es
público, así que el frontend habla con el worker y el worker con la Lambda).

```jsonc
// petición
{ "nombre": "Alejandra Palacio Restrepo",
  "alias": "La Profe",                  // opcional · nombre público o mote
  "corp": "Concejo municipal o distrital",
  "territorio": "Bogotá D.C.",
  "redes": [{ "red": "x", "handle": "apalacio" },
            { "red": "tiktok", "handle": "laprofe" }] }   // máximo 3

// respuesta
{ "ok": true,
  "perfiles": [{ "red": "tiktok", "handle": "laprofe", "url": "https://www.tiktok.com/@laprofe",
                 "veredicto": "confirmado", "confianza": 88, "existe": true, "sondeo": "ok",
                 "nombre_perfil": "Alejandra Palacio", "seguidores": null, "verificada": null,
                 "motivo": "El nombre del perfil coincide con el de la candidatura." }],
  "resumen": "…", "riesgo_homonimo": "…", "alertas": ["…"],
  "titulares": [{ "titulo": "…", "medio": "…", "fecha": "…", "link": "…" }],
  "modelo": "deepseek-v4-flash", "generado_en": "…", "cache_hit": false }
```

Errores que el frontend distingue y traduce: `404` (la ruta del worker todavía
no existe), `403` (la cuenta no tiene acceso), `400 sin_redes`, `502` (el
modelo no contestó).

## La ruta del worker (`rr-auth`) · **falta desplegar**

| Ruta | Quién | Para qué |
|---|---|---|
| `POST /c360/redes` | sesión con acceso a Candidato 360 | Reenvía el cuerpo a la Lambda y devuelve su respuesta tal cual |

Mismo patrón de `/caudal/api`: el worker decide **quién** puede llamar (limita
por IP y comprueba el acceso), le habla a la Lambda con un secreto compartido y
así la URL de la Lambda no queda publicada en un repo abierto.

```js
// rr-auth · src/index.js
if (url.pathname === '/c360/redes' && request.method === 'POST') {
  const sesion = await sesionDe(request, env);                 // el mismo helper de /c360/me
  if (!sesion) return json(401, { ok: false, error: 'sin_sesion' });
  if (!(await tieneAccesoC360(sesion.email, env))) return json(403, { ok: false, error: 'sin_acceso' });
  if (await excedeCuota(`c360redes:${sesion.email}`, 20, 86400, env))   // 20 validaciones al día
    return json(429, { ok: false, error: 'cuota' });
  const r = await fetch(env.C360_REDES_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-C360-Service': env.C360_SERVICE_TOKEN },
    body: await request.text(),
  });
  return new Response(await r.text(), { status: r.status, headers: cors(request, 'application/json') });
}
```

Variables del worker: `C360_REDES_URL` (la URL del Function URL / API Gateway)
y `C360_SERVICE_TOKEN` (el mismo valor que la Lambda lleva en
`C360_SERVICE_TOKEN`; sin la cabecera la Lambda responde 404 como una ruta que
no existe).

## Desplegar la Lambda

```bash
cd tools/candidato-360/redes
zip -j function.zip lambda_handler.py
aws lambda create-function \
  --function-name candidato-360-redes \
  --runtime python3.12 --handler lambda_handler.handler \
  --role "$LAMBDA_ROLE_ARN" --timeout 60 --memory-size 512 \
  --zip-file fileb://function.zip
aws lambda update-function-configuration \
  --function-name candidato-360-redes \
  --environment "Variables={DEEPSEEK_API_KEY=…,C360_SERVICE_TOKEN=…,S3_BUCKET=elecciones-2026}"
# actualizar después:
aws lambda update-function-code --function-name candidato-360-redes --zip-file fileb://function.zip
```

Permisos: `s3:GetObject` y `s3:PutObject` sobre
`elecciones-2026/ricardoruiz.co/candidato-360/redes-cache/*` (el cache falla en
silencio si no los tiene: se paga otra llamada a DeepSeek, no se cae nada).

Variables: ver la cabecera de `lambda_handler.py`. `PROMPT_VERSION` se bumpea al
tocar el prompt — si no, el cache sirve la lectura vieja.

## Probar

```bash
python3 tools/candidato-360/redes/prueba_offline.py     # sin red ni DeepSeek: el sellado de veredictos
python3 tools/candidato-360/redes/lambda_handler.py --sondeo   # solo los sondeos, contra las tres redes
python3 tools/candidato-360/redes/lambda_handler.py --prompt   # lo que se le manda al modelo
DEEPSEEK_API_KEY=… python3 tools/candidato-360/redes/lambda_handler.py   # la respuesta completa
node tools/candidato-360/redes/prueba-wizard.mjs        # el paso 2 de la página, con el worker stubbeado
```

> **Sin comprobar contra las redes de verdad.** Los tres sondeos se escribieron
> contra endpoints públicos documentados, pero el entorno donde se programaron
> no tiene salida a `cdn.syndication.twimg.com`, `www.tiktok.com` ni
> `www.instagram.com`: la primera corrida de `--sondeo` en una máquina con red
> es la que dice si alguno de los tres cambió de forma. Lo que sí está medido
> es que un sondeo caído no puede terminar en un veredicto falso
> (`prueba_offline.py`) y que la página se comporta con cualquiera de las
> respuestas (`prueba-wizard.mjs`, 17 comprobaciones).

## Modo pruebas del frontend

`candidato-360.js` levanta la regla de «una cuenta = un candidato» para la
cuenta de administración (`ADMIN_EMAILS`, o `fuente === 'admin'` desde
`/c360/me`): se entra por las dos rutas cuantas veces haga falta, se cambia de
candidato y **nada se escribe en el worker** — el vínculo queda solo en memoria
(`SESSION.vinculo.local`). Es lo que permite recorrer el wizard completo sin
dejar puesto un vínculo que después solo soporte puede borrar. Para ver la
página como la ve un cliente: `candidato-360.html?pruebas=0`.
