# Mi Congreso · Alertas

El push de `mi-congreso.html`: el congresista (o su UTL) deja un correo y le
llega un aviso cuando algo se mueve en su curul. Es el primer paso del roadmap
de Mi Congreso, y el que hace que la herramienta vuelva a buscar al usuario en
vez de esperarlo.

## Qué avisa

Por suscripción confirmada, en cada corrida:

| Señal | De dónde sale |
|---|---|
| Un proyecto que firma **cambió de estado** (o apareció por primera vez) | `action:'radicados'` de la Lambda `caudal-analiza` |
| Un proyecto suyo **entró a un orden del día** vigente | `ordenes-vigentes.json` (S3), cruzado por número |
| **Su comisión o la plenaria** de su cámara publicaron sesión | `ordenes-vigentes.json` + `comisiones-2026.json` |

La primera corrida manda un «así va tu curul hoy» con la foto completa y sella
el snapshot; desde ahí solo se avisa lo que cambia. **Sin novedades no hay
correo.**

## Las piezas

```
mi-congreso.html                         panel «Alertas por correo» (alta sin sesión)
rr-auth/src/index.js                     rutas /micongreso/alerta{,/confirmar,/baja}
                                         + servicio /micongreso/alertas/{inventario,estado,enviar}
tools/mi-congreso/alertas/motor.py       el motor (stdlib pura, corre en cualquier parte)
.github/workflows/mi-congreso-alertas.yml   cron · 08:40 y 18:40 Colombia
```

**Por qué GitHub Actions y no la Mac:** el rastreo legislativo ya corre en AWS y
se dispara desde Actions (`ordenes-legislativo.yml`); la Mac nueva no tiene
`aws`, ni launchd del proyecto, ni `~/.config/caudal`. El motor solo necesita
Python y red, y su estado (el snapshot por suscripción) vive en el registro del
worker, no en disco.

## Confirmación, no sesión

La alta no pide cuenta —matar la conversión en el primer contacto no tiene
sentido— pero **nada se envía a un correo que no haya hecho clic** en el enlace
de confirmación (72 h). El registro existe apagado hasta entonces y ni siquiera
sale en el inventario que ve el motor. Cada correo lleva su enlace de baja.

Anti-abuso en la alta: honeypot, 10 altas por IP y hora, consentimiento
explícito (Ley 1581). Anti-relay en el envío: remitente y reply-to fijos,
asunto con la marca «Mi Congreso ·», destinatario solo si es suscripción
confirmada, tope de 150 correos/día.

## Correr a mano

```bash
CAUDAL_ALERTAS_TOKEN=… python3 tools/mi-congreso/alertas/motor.py --dry-run
python3 tools/mi-congreso/alertas/motor.py --dry-run --inventario prueba.json --guardar-html /tmp/out
python3 tools/mi-congreso/alertas/motor.py --solo correo@dominio.co
```

`--forzar-primera` trata cada suscripción como recién confirmada (ignora el
snapshot): sirve para ver el resumen completo de alguien sin tocar su estado.

## Gotchas medidos

- **El número de proyecto llega en tres formas** (`152 de 2026 Cámara` en las
  agendas, `276/2026C` y `213/26` en los registros, a veces sin cámara):
  `num_norm` los lleva a (número sin ceros, año a dos dígitos, cámara o None) y
  `num_casa` solo exige que la cámara no se contradiga.
- **El snapshot se sella solo si Resend aceptó el correo**: si el envío falla,
  la señal vuelve a salir en la corrida siguiente en vez de perderse.
- **Cámara publica sus radicados con rezago de días**, así que «nuevo en el
  registro» no significa «radicado hoy». El correo lo dice.
- Los nombres de Cámara en `legislativo-electos.js` van en MAYÚSCULA y sin
  tildes; el motor los canoniza contra ese listado y los muestra en Title Case.

## Despliegue (una vez)

1. `cd /Users/ricardoruiz/rr-auth && npx wrangler deploy` (Ricardo).
2. En GitHub → Settings → Secrets and variables → Actions: secreto
   `CAUDAL_ALERTAS_TOKEN` con el mismo valor que tiene el worker.
3. Probar: Actions → «Mi Congreso · alertas» → Run workflow con `dry_run`.
