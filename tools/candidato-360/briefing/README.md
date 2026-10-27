# Candidato 360 · Briefing cada 3 días

El push del CRM. Hasta ahora Candidato 360 era una página a la que había que
entrar; con esto, cada tres días el candidato recibe en su correo lo que pasó en
**su territorio**, leído del vínculo que ya tiene guardada su cuenta
(corporación + departamento + municipio + localidad).

## Qué lleva

| Sección | Fuente | Regla |
|---|---|---|
| **De lo que habla el país** | Google News con tres anclajes anchos: `"Colombia"`, `"Gobierno Nacional"`, `"Congreso de la República"` | No hay un «top» que pedir: Google News entrega titulares por consulta, no un ranking. Así que se calcula. Los titulares se agrupan por historia (palabras cortadas a seis letras, porque cada medio conjuga el hecho a su manera) y las historias se ordenan por **cuántos medios distintos** las publicaron, no por cuántos titulares: un portal que repite su nota cinco veces no es «de lo que habla todo el mundo». Se muestran las tres primeras, con el titular más reciente de cada una |
| **La conversación · sobre usted** | Google News (acción `medios` de la Lambda) con el nombre y el nombre público entre comillas | Un titular «lo nombra» si trae nombre + apellido (o los dos apellidos) |
| **La conversación · su territorio** | Consultas entre comillas: la localidad (JAL), «Alcaldía de X», «Concejo de X», el municipio | Cada titular recibe un **puntaje**: +3 si nombra la localidad, +2 si nombra un actor institucional (alcaldía, concejo, secretaría, obra, licitación…), +1 si nombra el municipio. En Bogotá, Medellín, Cali, Barranquilla y Cartagena se exige ≥2: «Bogotá» aparece en cualquier cosa. Clima, loterías, vacantes y cortes de luz salen por regex |
| **La plata** | SECOP II (acción `contratacion`) con `orden_entidad: Territorial`, `departamento` y `query` = municipio | Sin el filtro territorial salían la UNP o la Fuerza Aérea solo por estar ubicadas en Bogotá. Para una JAL se consulta además la **localidad**: la Alcaldía Local firma contratos propios y van primero |
| **Las reglas** | Normativa del Ejecutivo (acción `ejecutivo`) con el municipio y el departamento | Ventana de 30 días (el dataset de Presidencia es mensual). Si no hay nada, la sección **no aparece** |

En el panel 04 (la escucha social) el orden es: lo que lo nombra a usted, la
agenda del país y después su territorio. Lo que ya salió como suyo o como
local no se repite arriba: en el bloque del país estorba y abajo es donde
sirve.

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
- La lectura del ciclo es determinista (sin LLM): sale de la prensa, las redes,
  los arquetipos y las visitas. Ver «El correo con la lectura del ciclo».

## Lo que el candidato marcó en la escucha manda (sep-2026)

El inventario del worker trae `escucha` (`ideas`, `preferencias`, `redes`) y
`preferencias_de(v)` lo traduce a la lectura: **clase de medio** (solo
tradicionales / solo alternativos / todo; `tipo_medio` es el mismo puerto de
`candidato-360-panel.js`, lo desconocido no se descarta), **escala** (territorio
y/o país; el bloque «De lo que habla el país» agrupa por cobertura entre
medios, `agrupar_por_cobertura`) y **sus temas** (cada idea entre comillas más
el lugar, si marcó «de una causa»). Sin preferencias: solo el territorio, más
las ideas si las escribió. Probar sin worker:
`python3 motor.py --inventario prueba.json --dry-run --forzar --guardar-html /tmp/b`.


## El correo con la lectura del ciclo (oct-20-2026)

Desde el 20-oct el correo ya no es solo dato ordenado: lleva la **lectura de la
tarjeta 03 del CRM** con la forma del correo de Caudal (saludo, portada oscura
con la lectura, tres cifras, «si solo tiene tiempo para una cosa», el párrafo,
**dónde estar esta semana** con los barrios por visitar, qué llevar, lo que se
movió en una línea cada cosa y lo que viene).

| Pieza | Qué hace |
|---|---|
| `lectura.mjs` | Corre en Node **los mismos scripts del navegador** (`candidato-360-arq-lectura.js`, `-saliencia.js`, `-ciclo.js`…) en un contexto `vm`. Entra el vínculo, los titulares, la captura de redes y las visitas; sale la lectura (arquetipos con su relevancia y prioridades por localidad). Un solo cálculo para la tarjeta y el correo. |
| `correo_ciclo.py` | Arma el correo (HTML y texto) desde la lectura, más contratos y normas en una línea cada uno. |
| `motor.py` | Igual que antes (cadencia, visto, silencio si no hay nada), pero con `render_ciclo`. Si la lectura falla, sale el formato anterior: un briefing nunca se pierde por esto. `--formato-viejo` fuerza el de antes. |

El inventario del worker trae ahora `candidato.slugs` (para leer sus votos),
`captura` (solo temas y postura de la última lectura de redes) y `visitas`.

**Las visitas viven en el worker** (`GET/POST /c360/visitas`, llave
`c360:visitas:<email>`): las marca cualquiera del equipo en el mapa de la tarjeta
03 y el correo las descuenta (≤7 días ×0,35; ≤21 días ×0,6). La copia local del
navegador queda de respaldo; la primera vez se sube lo que ya estaba marcado.

Sin arquetipos para la ciudad (hoy hay Bogotá, Medellín y Cartagena) el correo
sale igual con prensa, redes, plata y reglas, y dice por qué no trae zonas.
De sus temas solo entra lo que nombra su territorio y la mitad de las palabras
de la idea: una idea suelta trae notas de cualquier parte del país.
En Bogotá se descartan los contratos de entidades de Cundinamarca (tienen sede
en Bogotá y firman obras de otros municipios).

```bash
python3 tools/candidato-360/briefing/motor.py --inventario prueba.json --dry-run --forzar --guardar-html /tmp/b
echo '{"vinculo":{…},"items":[…]}' | node tools/candidato-360/briefing/lectura.mjs
```

## Gráficos en el correo (oct-27-2026 · solo borrador por ahora)

`graficos.py` dibuja cuatro PNG desde la MISMA lectura del correo: de qué habló
la prensa (`prensa`), el mapa de Bogotá con el peso de cada localidad
(`zonas`, rotado 90° y sin Sumapaz), la postura de los comentarios por red
(`redes`: verde a favor · gris neutro · coral en contra o ataque, con la cifra
en cada tramo) y el rendimiento por arquetipo frente a la ciudad
(`arquetipos`). Se dibujan a 1200 px para un correo de 600.

```bash
python3 motor.py --inventario prueba.json --dry-run --forzar --guardar-html /tmp/b --graficos
```

Deja `<slug>-graficos/*.png` al lado del HTML y el correo los busca con ruta
relativa, con la marca de borrador. ⚠️ **Para el envío real falta publicarlos**
en una URL pública (S3) y pasar esa URL en `graf_url`: con rutas relativas el
correo llega sin imágenes. Hasta entonces la corrida diaria no los usa.

De paso: «En X le comentan duro» solo sale si lo hostil pesa una cuarta parte
o más (o supera lo a favor). Antes salía con 3 de 45 en contra y 37 a favor.
