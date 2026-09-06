# Candidato 360 · Briefing cada 3 días

El push del CRM. Hasta ahora Candidato 360 era una página a la que había que
entrar; con esto, cada tres días el candidato recibe en su correo lo que pasó en
**su territorio**, leído del vínculo que ya tiene guardada su cuenta
(corporación + departamento + municipio + localidad).

## Qué lleva

| Sección | Fuente | Regla |
|---|---|---|
| **La conversación · sobre usted** | Google News (acción `medios` de la Lambda) con el nombre y el nombre público entre comillas | Un titular «lo nombra» si trae nombre + apellido (o los dos apellidos) |
| **La conversación · su territorio** | Consultas entre comillas: la localidad (JAL), «Alcaldía de X», «Concejo de X», el municipio | Cada titular recibe un **puntaje**: +3 si nombra la localidad, +2 si nombra un actor institucional (alcaldía, concejo, secretaría, obra, licitación…), +1 si nombra el municipio. En Bogotá, Medellín, Cali, Barranquilla y Cartagena se exige ≥2: «Bogotá» aparece en cualquier cosa. Clima, loterías, vacantes y cortes de luz salen por regex |
| **La plata** | SECOP II (acción `contratacion`) con `orden_entidad: Territorial`, `departamento` y `query` = municipio | Sin el filtro territorial salían la UNP o la Fuerza Aérea solo por estar ubicadas en Bogotá. Para una JAL se consulta además la **localidad**: la Alcaldía Local firma contratos propios y van primero |
| **Las reglas** | Normativa del Ejecutivo (acción `ejecutivo`) con el municipio y el departamento | Ventana de 30 días (el dataset de Presidencia es mensual). Si no hay nada, la sección **no aparece** |

Y el pie recuerda la **meta de votos** que calculó `VoteTarget` en el CRM (la
guarda el frontend en `campana.meta`).

## Reglas del motor

- **Cadencia por vínculo.** El workflow corre a diario a las 07:30 de Bogotá; el
  motor manda a quien tenga el último envío con 3 días o más. Un Mac apagado no
  cambia nada: esto corre en GitHub Actions.
- **No se repite.** Cada titular, contrato y norma enviados quedan en el
  snapshot `briefing.visto` del vínculo, en el worker (300 ids por sección).
- **Sin nada que decir no se manda y NO se mueve la fecha.** Al día siguiente se
  intenta con una ventana más larga (tope 10 días). Un correo vacío mata el canal.
- **Nada se inventa.** Si una fuente no responde, su sección lo dice.
- **El opt-in nace apagado.** Un vínculo sin el interruptor encendido ni
  siquiera sale del inventario del worker: el motor no ve su correo.
- **Un plan vencido deja de recibir solo:** el inventario filtra por acceso
  vigente, y la ruta de envío vuelve a comprobarlo.

## Las rutas del worker (`rr-auth`)

| Ruta | Quién | Para qué |
|---|---|---|
| `POST /c360/briefing {activo, correo?}` | sesión con acceso y vínculo | El interruptor del panel 03 del CRM. Puede mandarlo a otro correo (el del jefe de campaña) |
| `GET /c360/briefing/inventario` | servicio | Vínculos encendidos con acceso vigente: territorio, nombre, correo, snapshot |
| `POST /c360/briefing/estado` | servicio | Sella `visto` y `ultimoEnvio` |
| `POST /c360/briefing/enviar` | servicio | Manda por Resend. Fija remitente, obliga el asunto a empezar por «Candidato 360 ·» y **solo acepta el correo del briefing de ese vínculo**. Tope 120 correos/día |

Las tres de servicio van en la tabla `SERVICIO` con el guarda de seis capas de
Caudal y el **mismo secreto `CAUDAL_ALERTAS_TOKEN`** (cabecera
`X-Caudal-Service`). Sin el secreto responden 404 como una ruta inexistente.

## Cómo se corre

```bash
CAUDAL_ALERTAS_TOKEN=… python3 tools/candidato-360/briefing/motor.py             # corrida real
python3 tools/candidato-360/briefing/motor.py --dry-run --guardar-html /tmp/b   # arma, no manda
python3 tools/candidato-360/briefing/motor.py --solo correo@dominio.co --forzar # una cuenta, sin cadencia
python3 tools/candidato-360/briefing/motor.py --worker http://localhost:8788    # contra wrangler dev
```

Para probar sin tocar producción: `preview_start rr-auth-dev` (wrangler dev con
`.dev.vars` que trae un `CAUDAL_ALERTAS_TOKEN` de prueba), sembrar sesiones en
el KV local y encender el briefing con `POST /c360/briefing`. Medido: dos
vínculos, 37 s, sin fallos de fuente.

## Lo que hace falta para que corra solo

1. El secreto **`CAUDAL_ALERTAS_TOKEN` en GitHub Actions** del repo
   `ricardoruiz.co` (Settings → Secrets → Actions), el mismo valor que tiene el
   worker. Es el mismo que necesita `mi-congreso-alertas.yml`.
2. Nada más: el workflow `candidato-360-briefing.yml` ya está en el repo.

## Deudas

- Para **Medellín, Cali y Barranquilla** la localidad de una JAL viene como
  «COMUNA 14 EL POBLADO»: el puntaje usa las palabras del nombre y funciona,
  pero no se ha medido con un vínculo real de esas ciudades.
- La normativa por municipio casi siempre viene vacía (Presidencia rara vez
  nombra un municipio). Vale la pena sumar las **ordenanzas y acuerdos** del
  propio concejo cuando exista esa fuente (módulo de proyectos de acuerdo).
- No hay lectura del analista (LLM) todavía: el briefing es dato ordenado. Es
  la evolución natural cuando el módulo de arquetipos exista.
