# Acceso a Caudal · aprovisionamiento manual de clientes

Abrirle Caudal a un cliente **sin editar código ni hacer push**.

El gate de `caudal.html` nació como una lista de correos escrita a mano dentro
del HTML (`const ALLOWED = [...]`). Con Cauce trayendo clientes eso pasa a ser
semanal, y cada alta significaba un commit y un despliegue. Este CLI mueve la
lista al KV del worker `rr-auth`: otorgar y revocar es inmediato.

**No es autoservicio.** El modelo comercial es aprovisionamiento manual de
cuentas ya habladas: no hay pasarela de pago acá y todo exige admin.

---

## Uso

```bash
python3 tools/caudal/acceso/acceso.py listar
python3 tools/caudal/acceso/acceso.py otorgar diego@cauce.co --nota "Cauce · piloto"
python3 tools/caudal/acceso/acceso.py otorgar juan@gremio.co --dias 90 --nota "Prueba 3 meses"
python3 tools/caudal/acceso/acceso.py ver diego@cauce.co
python3 tools/caudal/acceso/acceso.py revocar diego@cauce.co
```

- **Sin `--dias` el acceso no vence.** Con `--dias`, la llave de KV se borra
  sola al vencer *y además* la fecha se revalida al leer (la expiración de KV
  es eventual, así que la fecha es la que manda).
- `otorgar` sobre un correo que ya tiene acceso lo **renueva**: conserva quién
  lo abrió y cuándo, y actualiza vencimiento y nota.
- `revocar` es idempotente: si no estaba, lo dice en vez de fingir que hizo algo.
- `ver` sale con código 1 si el correo no tiene acceso (sirve para scripts).

⚠️ **Esto autoriza un correo, no crea la cuenta.** El cliente necesita
registrarse en `ricardoruiz.co/register.html`; el correo con el que se registre
tiene que ser exactamente el autorizado.

Los **admins** (`ADMIN_EMAILS` del worker: hoy `reruizc@gmail.com`, más
cualquier usuario con `role:admin`) entran siempre, sin llave en KV y sin
posibilidad de revocarse desde acá. Es a propósito: que Ricardo no se pueda
dejar afuera. `listar` los muestra aparte para que la lista no se lea como el
universo completo de quién puede abrir Caudal.

## Credenciales

Dos caminos, en orden de preferencia:

1. **`RR_ADMIN_API_KEY`** en el entorno o en `~/.config/caudal/acceso.env`
   (`chmod 600`, **fuera del repo**). Es el secreto `ADMIN_API_KEY` del worker;
   viaja en la cabecera `X-Admin-Api-Key` y no necesita sesión — el camino para
   scripts.

   ```bash
   printf 'RR_ADMIN_API_KEY=...\n' > ~/.config/caudal/acceso.env
   chmod 600 ~/.config/caudal/acceso.env
   ```

   > Ese archivo es el mismo patrón que `~/.config/caudal/alertas.env`, pero
   > **son dos archivos distintos**: aquel lleva `RESEND_API_KEY` y
   > `CAUDAL_ALERTAS_TOKEN` para el motor de alertas.

2. **Sesión de admin.** Sin api-key, el CLI pide la contraseña una vez y cachea
   el token en `~/.config/caudal/acceso-session.json` (`chmod 600`). La
   contraseña no se guarda nunca. Si el token vence, vuelve a preguntar sola.

Otro correo de admin: `--admin-email otro@ejemplo.co`.
Otro backend (pruebas): `RR_AUTH_API=http://localhost:8799`.

## Qué hay del otro lado

Cuatro rutas en `rr-auth` (`/Users/ricardoruiz/rr-auth/src/index.js`, bloque
`CAUDAL · ACCESO POR CUENTA`):

| Ruta | Guard | Para qué |
|---|---|---|
| `GET /caudal/acceso/me` | sesión de usuario | Lo consulta el **frontend**: ¿esta cuenta puede abrir Caudal? |
| `GET /caudal/acceso/list` | admin | `listar` |
| `POST /caudal/acceso/save` | admin | `otorgar` |
| `DELETE /caudal/acceso/delete?email=` | admin | `revocar` |

KV: una llave por cuenta, `caudal:acceso:<correo>` →
`{email, nota, otorgadoPor, otorgadoEn, expiraEn, actualizadoEn}`.

`/caudal/acceso/me` responde `{acceso, fuente, expiraEn}` con `fuente` ∈
`admin` · `otorgado` · `vencido` · `ninguno`. **No devuelve `nota` ni
`otorgadoPor`**: son apuntes internos del consultor, no cosa del cliente.

Los tres caminos de acceso a Caudal quedan separados a propósito:

- **admin** — permanente, no revocable por KV.
- **cuenta autorizada** (`caudal:acceso:`) — el cliente de Cauce. Esto.
- **link de invitado** (`caudal-guest:` + `/caudal/guest`) — socio sin cuenta,
  por `?acceso=<token>`. Sigue vivo y sin cambios.

## Pendiente: cablear el frontend

`caudal.html` **todavía usa su lista `ALLOWED` hardcodeada** — el cambio del
frontend se hizo aparte, a propósito. Mientras no se cablee, otorgar acceso por
CLI **no abre la puerta todavía**. Lo que falta ahí es reemplazar el chequeo
local por una llamada a `/caudal/acceso/me` con el bearer de la sesión, y mandar
a `dashboard.html` cuando responda `acceso:false`.

## Desplegar el worker

`rr-auth` **no es repo git** y es **compartido** con micmac, mactor, pp, ev,
alt, ain, prospect, comunicar y los pronósticos. Validar siempre antes:

```bash
cd /Users/ricardoruiz/rr-auth && npx wrangler deploy --dry-run
cd /Users/ricardoruiz/rr-auth && npx wrangler deploy
```
