# Candidato 360 · buscar y validar las redes de la candidatura

El paso 2 del wizard de `candidato-360.html` preguntaba un mote y seguía de
largo: la escucha de medios y redes se montaba sobre un texto que **nadie
comprobó**. Ahora la persona marca en qué redes está (X, TikTok, Instagram),
escribe el usuario, y antes de construir el punto de partida la plataforma
busca esa cuenta y dice si parece ser la suya.

> **El código del backend vive en `rr-auth`** (worker de Cloudflare), no acá:
> `src/c360-redes.js` + la ruta `POST /c360/redes` en `src/index.js`. Este repo
> es público y el worker ya guarda `DEEPSEEK_API_KEY` como secreto; poner la
> llave a un paso del navegador sería regalarla. Acá queda el contrato que
> consume la página y la prueba del wizard.

## Qué hace, en orden

| Paso | Fuente | Qué aporta |
|---|---|---|
| **1. Sondeo** | El endpoint público de cada red: el widget «Follow» de X (`cdn.syndication.twimg.com`), el **oEmbed** de TikTok y los metadatos `og:` del perfil de Instagram | Lo único que dice si la cuenta **existe** y con qué nombre. Sin llaves ni sesión |
| **2. Señales abiertas** | Google News RSS con el nombre y el nombre público (12 meses) | Si esa persona ya aparece en prensa y con qué rol — sirve para detectar el homónimo |
| **3. Veredicto** | DeepSeek V4 Flash | Lee **solo** lo anterior y devuelve, red por red, `confirmado · probable · dudoso · no_encontrado · no_verificable` con una frase de por qué |

Los tres sondeos salen del **edge de Cloudflare**, no del navegador: pedidos
desde la página los mata CORS. El resultado se guarda 7 días en KV
(`c360:redes:<hash24>`), con el sondeo dentro de la llave — si mañana la cuenta
aparece o cambia de nombre es otra pregunta, y no puede contestarla el cache de
ayer. Tope de **40 validaciones por cuenta y por día**: una validación cuesta
una llamada al modelo.

## Las dos reglas que sostienen esto

- **Un sondeo que no responde NO es un perfil falso.** Las tres redes bloquean
  tráfico de servidor de a ratos. El worker distingue «no existe» (404 limpio)
  de «no pude comprobarlo» (bloqueo, timeout, muro de login) y la página los
  pinta distinto: `Sin cuenta` en coral, `Sin comprobar` en ámbar.
- **El sondeo manda sobre el modelo.** DeepSeek no puede subir un veredicto por
  encima de la evidencia: está en el system prompt y se vuelve a imponer en
  código (`sellarVeredictos`) porque un prompt no es un control. Un
  «confirmado» sobre una red que no contestó se degrada a `no_verificable`
  antes de salir.

Validar **nunca bloquea**. Si la red no deja comprobar, si se acabó la cuota o
si el modelo se cae, el wizard sigue y la candidatura queda guardada con
`redes.validado = false`. Un candidato no se puede quedar por fuera de su
propia campaña porque X no contestó.

## Contrato · `POST /c360/redes`

Sesión con acceso a Candidato 360 (`Authorization: Bearer <token>`).

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

Errores, todos con `detalle` en español que la página muestra tal cual:
`401` sesión vencida · `403` sin acceso · `400 falta_nombre` · `400 sin_redes` ·
`429 cuota` · `502 modelo_no_respondio`. Un `404` significa que la ruta todavía
no está desplegada, y la página lo dice así — no como «no encontramos su
perfil», que haría borrar un usuario bien escrito.

## Desplegar

En `rr-auth` (el worker es compartido: un despliegue afecta a Caudal, el Lab,
Gastos y el juez a la vez):

```bash
npx wrangler deploy --dry-run   # valida que compile
npx wrangler deploy             # publica
```

No hace falta ningún secreto nuevo: usa el `DEEPSEEK_API_KEY` que el worker ya
tiene y el KV `RR_STORE` que ya está bindeado.

## Probar

```bash
node tools/candidato-360/redes/prueba-wizard.mjs   # el paso 2 de la página, con el worker stubbeado (17 comprobaciones)
# en rr-auth:
node test/c360-redes.test.mjs                      # sondeos, RSS, sellado de veredictos y cache (32, sin red ni DeepSeek)
npx wrangler dev --local                           # y contra 127.0.0.1:8788, con una sesión sembrada en el KV local:
#   npx wrangler kv key put --local --binding RR_STORE "sessions:tok" '{"email":"…","plan":"premium"}'
```

> **Los tres sondeos no se han corrido contra las redes de verdad.** Se
> escribieron contra endpoints públicos documentados, pero el entorno donde se
> programaron no tiene salida a `cdn.syndication.twimg.com`, `www.tiktok.com`
> ni `www.instagram.com`: la primera validación real es la que dice si alguno
> cambió de forma. El de Instagram es el más frágil de los tres — si empieza a
> devolver siempre `Sin comprobar`, es que el muro de login se cerró más y toca
> cambiar de fuente, no que las cuentas no existan.

## Modo pruebas del frontend

`candidato-360.js` levanta la regla de «una cuenta = un candidato» para la
cuenta de administración (`ADMIN_EMAILS`, o `fuente === 'admin'` desde
`/c360/me`): se entra por las dos rutas cuantas veces haga falta, se cambia de
candidato y **nada se escribe en el worker** — el vínculo queda solo en memoria
(`SESSION.vinculo.local`). Es lo que permite recorrer el wizard completo sin
dejar puesto un vínculo que después solo soporte puede borrar. Para ver la
página como la ve un cliente: `candidato-360.html?pruebas=0`.
