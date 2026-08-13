# Gastos · presupuesto alimentado por el banco

App personal: dices cuánto tienes hoy y de ahí en adelante cada gasto lo baja y
cada ingreso lo sube, a medida que llegan las notificaciones del banco.

**No pregunta cuánto ganas**, a propósito: la nómina llega por SMS y la app la
reconoce sola. Pedir un dato que el banco va a informar es pedirlo dos veces.

⚠️ El saldo solo cuenta los movimientos **posteriores al ancla**. Si fijas tu
saldo hoy e importas el historial de mayo, esos gastos ya están descontados de
la cifra que escribiste; restarlos otra vez mostraría mucha menos plata de la
que hay. Los traslados tampoco cuentan: mover plata entre bolsillos propios no
cambia cuánta hay. Reanclar el saldo cuando se desvíe del banco es parte del
uso normal — siempre habrá algo que la app no vio (efectivo, Nubank).

```
gastos.html            la app (PWA instalable, sistema visual v2)
gastos-manifest.json   manifiesto  ·  gastos-sw.js  service worker
imagenes/gastos-icon-{180,192,512}.png
rr-auth/src/gastos-parser.js   el parser (módulo puro, con pruebas)
rr-auth/src/index.js           rutas /gastos/*
tools/gastos/correos.py        lector de correos de banco (cron del Mac)
```

## Por qué no es una app nativa de iOS

**iOS no deja que una app lea los SMS.** No hay API, no es un permiso que se
pueda pedir: Apple simplemente no lo expone. Una app en Swift jamás vería los
mensajes de Nequi. Lo que sí funciona es una **automatización de Atajos**, que
es el puente que usa todo el mundo en Colombia para esto.

Y como el frontend es una **PWA**, se instala en la pantalla de inicio, se ve
como app y no cuesta los USD 99/año del programa de desarrollador ni pasa por
revisión de Apple.

---

## PASO 1 · Secretos del worker  ← esto lo hace Ricardo

```bash
# Genera el secreto (guárdalo: lo vas a pegar en el Atajo del iPhone)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

cd /Users/ricardoruiz/rr-auth
npx wrangler secret put GASTOS_TOKEN      # pega el secreto de arriba
```

`GASTOS_EMAIL` es opcional: sin él, los movimientos se le anotan a
`reruizc@gmail.com`, que es lo correcto para uso personal.

> Sin `GASTOS_TOKEN` la ruta `/gastos/ingest` **no existe** (responde 404 igual
> que cualquier ruta inventada). Es a propósito: desplegar el código antes de
> sembrar el secreto no abre nada.

## PASO 2 · Desplegar

```bash
cd /Users/ricardoruiz/rr-auth && npx wrangler deploy
cd /Users/ricardoruiz/ricardoruiz.co && git push origin HEAD:main
```

⚠️ El worker es **compartido** con Caudal, el Lab y el resto del sitio. No se
despliega sin luz verde.

## PASO 3 · El Atajo del iPhone (SMS)

En la app **Atajos** → pestaña **Automatización** → **+** → **Mensaje**:

1. **Remitente**: los tres números cortos, en UNA sola automatización.

   | Número | Qué llega |
   |---|---|
   | `85540` | Bancolombia · gastos **y** plata que entra (la nómina del DNP) |
   | `85784` | Bancolombia · tarjeta de crédito |
   | `890789` | Lulo Bank |

   *Alternativa:* dejar el remitente vacío y usar **Contiene: `$`**. Atrapa
   más, pero le manda al servidor cualquier mensaje con un signo de pesos,
   incluidos los personales. **Prefiere filtrar por remitente.**
2. Marca **Ejecutar inmediatamente** y desactiva **Avisar antes de ejecutar**.
   Sin esto te pide confirmación en cada compra y el automatismo pierde sentido.
3. Acción: **Obtener contenido de la URL**
   - URL: `https://rr-auth.reruizc.workers.dev/gastos/ingest`
   - Método: **POST**
   - Encabezados:
     - `X-Gastos-Token` → *el secreto del paso 1*
     - `Content-Type` → `application/json`
   - Cuerpo de la solicitud: **JSON**
     - `texto`  → variable mágica **Contenido del mensaje**
     - `metodo` → `sms`

Listo. Cada SMS del banco entra solo.

**Probar sin esperar una compra:** ejecuta el Atajo a mano poniéndole un texto
fijo, o desde el Mac:

```bash
curl -s -X POST https://rr-auth.reruizc.workers.dev/gastos/ingest \
  -H "X-Gastos-Token: TU_SECRETO" -H "Content-Type: application/json" \
  -d '{"texto":"Bancolombia le informa Compra por $52.900 en RAPPI COLOMBIA 15:22","metodo":"sms"}'
# → {"ok":true,"guardado":true,"monto":52900,"comercio":"RAPPI COLOMBIA",...}
```

## PASO 4 · Los correos (opcional, cubre lo que no llega por SMS)

Necesita una **contraseña de aplicación** de Google (no la del correo):
`myaccount.google.com` → Seguridad → Verificación en dos pasos → Contraseñas de
aplicaciones.

```bash
mkdir -p ~/.config/gastos && chmod 700 ~/.config/gastos
cat > ~/.config/gastos/gastos.env <<'EOF'
GASTOS_TOKEN=...
GASTOS_IMAP_USER=reruizc@gmail.com
GASTOS_IMAP_PASS=xxxx xxxx xxxx xxxx
EOF
chmod 600 ~/.config/gastos/gastos.env

python3 tools/gastos/correos.py --dry-run    # ver qué encontraría
python3 tools/gastos/correos.py              # enviarlo de verdad
```

Abre el buzón en **solo lectura**: no marca como leído nada tuyo. Para que corra
solo, agrégalo como una etapa más del cron que ya existe en el Mac.

## ¿Cada cuánto se actualiza?

Hay que separar dos cosas que se confunden:

| | Cómo funciona | Latencia |
|---|---|---|
| **SMS** | El Atajo EMPUJA en el instante en que llega el mensaje. No hay nada que "revisar". | inmediata |
| **Correo** | Hay que ir a mirar el buzón, así que sí es una consulta periódica. | cada 2 h |
| **La pantalla** | Se refresca al volver a la app y cada 90 s mientras esté abierta y a la vista. | inmediata al abrir |

El refresco de pantalla **nunca corre con la app en segundo plano** (gastaría
cuota del KV sin que nadie mire) y **nunca repinta mientras estás editando un
movimiento** — eso borraría lo que estás escribiendo. Al cerrar el editor entra
lo que haya llegado entre tanto.

### Instalar la revisión de correo cada 2 horas

Solo tiene sentido después de poner `GASTOS_IMAP_PASS` (PASO 4). Sin ella el
script sale en silencio, así que instalarlo antes no rompe nada.

```bash
cp tools/gastos/co.ricardoruiz.gastos-correos.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/co.ricardoruiz.gastos-correos.plist
launchctl list | grep gastos-correos          # debe salir con exit 0
```

Va en su **propio** agente, no dentro de `run_diario.sh`: ese es el pipeline de
Caudal, corre 2 veces al día y tiene su propio candado. Mezclarlos haría que un
fallo de uno arrastre al otro.

Para desinstalarlo:
```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/co.ricardoruiz.gastos-correos.plist
```

## PASO 5 · Instalar la app en el iPhone

Safari → `https://ricardoruiz.co/gastos.html` → Compartir → **Agregar a inicio**.
Queda con ícono propio y sin barra del navegador.

---

## Cómo lee los mensajes (y por qué se puede corregir)

El parser vive en `rr-auth/src/gastos-parser.js` y es un **módulo puro**, así
que se prueba entero con node sin desplegar nada.

Decisiones que conviene no deshacer, cada una salió de un caso que falla:

- **El monto es el PRIMERO que no sea saldo**, no el mayor.
  `Nequi: Enviaste $50.000 a Juan. Te queda $120.000` → quedarse con el mayor
  tomaría el saldo.
- **Una compra que además informa el saldo SÍ es un gasto.** Por eso los
  rechazos están partidos en duros (claves, compras rechazadas, avisos de
  facturación) y blandos (saldo, cupo), y los blandos solo aplican si el
  mensaje no trae un verbo de movimiento.
- **"Pago mínimo" y "fecha de pago" son rechazo duro** aunque contengan el
  verbo "pago": son avisos de facturación, no un movimiento que ocurrió.
- **Las claves dinámicas no se guardan** ni siquiera como texto crudo.
- **Ante la duda, gasto.** Subestimar el gasto es el error caro.
- **Nunca se descarta el texto original**: si el parser se equivoca, el
  movimiento igual queda con `crudo` y confianza baja, marcado en amarillo para
  que lo corrijas de un toque. Corregirlo lo deja en confianza alta.

Correr las pruebas (40 casos, sale con código 1 si alguno falla):

```bash
node tools/gastos/prueba-parser.mjs
```

Prueba el archivo que se despliega, no una copia. Cuando aparezca un formato de
banco nuevo, el caso se agrega ahí **primero** y luego se toca el parser.

### Calibrado con mensajes REALES

Once de los 40 casos son SMS textuales que llegaron al teléfono de Ricardo, de
los tres remitentes (`85540` débito e ingresos · `85784` tarjeta de crédito ·
`890789` Lulo). Son la vara: si uno de esos se rompe, el parser está mal.

Lo que enseñaron, y que no se habría descubierto inventando mensajes:

- **Bancolombia manda dos formatos de monto contradictorios** en la misma
  cuenta: `COP12.533,00` (punto de miles) y `$13,693.98` (al revés). La regla
  del último separador aguanta los dos.
- **`tigo` casaba dentro de "Siempre con-tigo"**, la despedida que Bancolombia
  pega en CADA mensaje: cualquier compra podía terminar en "servicios". Trece
  términos del diccionario tenían el mismo defecto.
- **El asterisco significa dos cosas opuestas** (ver el comentario en el
  parser). `DNH*GODADDY#4088755116` se quedaba en "DNH".

Sigue en pie el principio: lo dudoso queda marcado en amarillo y con su texto
original. Cuando aparezca un banco o un formato nuevo, el caso se agrega al
test primero.

## Privacidad

- La app está en un repo público, pero **no hay datos en el HTML**: todo vive
  en el KV del worker detrás de sesión, y solo la abre `reruizc@gmail.com`.
- `/gastos/ingest` va **sin CORS** y rechaza cualquier petición con huella de
  navegador: aunque alguien tuviera el secreto, no la puede llamar desde una
  página web.
- El service worker cachea **solo el cascarón**, nunca los datos: mostrar un
  saldo viejo como si fuera el de hoy es peor que no mostrar nada.
