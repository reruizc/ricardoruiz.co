# Gestión de equipo · `candidato-360-equipo.html` — plan de trabajo

Tarjeta 11 del CRM y panel propio. Convierte lo que el producto ya sabe (la meta,
cómo se reparte en el territorio, el plan de testigos, los aliados) en **trabajo
asignado a personas del equipo**, sin que la plataforma se vuelva la custodia de
la base de contactos de la campaña.

Estado: **plan, sin construir** (28-sep-2026). Nada de esto está en producción.

---

## 0. Lo que se revisó antes de escribir el plan (y cambió el diseño)

| # | Hallazgo | Consecuencia |
|---|---|---|
| H1 | **El reparto de la meta por zona no es un módulo.** Vive dentro de `candidato-360.js`, repartido en `distributeVotes`, `proyeccionTerritorio`, `repartoSaltoCiudad`, `repartoMudanzaLocal`, `pintarProyeccionDepartamental` y `valoresBarriales`, y depende del estado del mapa (`crmMapState`, `SALTO_ACTUAL`, `crmMapMode`). `vote-target.js` NO reparte la meta en el territorio: su `reparto()` es el de **curules** (art. 263). | Antes de sub-metas hay que **extraer** el reparto geográfico a `candidato-360-reparto.js`, sin cambiar cifras, como se hizo con el endoso (fase 1). Si el panel de equipo recalculara por su lado, la coordinadora vería una sub-meta distinta de la que pinta el mapa del candidato. |
| H2 | **El Día D ya dejó escrita la regla** («este módulo NO pide ni guarda un solo dato del equipo»), y el CSV sale con «Testigo» en blanco. El endoso guarda aliados y líderes **solo en el navegador** (`localStorage['c360-aliados:<correo>:<candidatura>']`). | La base amplia (testigos, líderes, voluntarios) sigue fuera del servidor. Esta tarjeta no revierte esas decisiones: las extiende a un equipo. |
| H3 | **El patrón de invitación del Lab sirve casi entero** (`/micmac/invite` + `/micmac/accept`, token de 14 días en KV, Resend, índices `owner`/`collab`). Pero guarda el correo del invitado en claro y el proyecto guarda la lista de colaboradores. | Se reusa el flujo y se endurece: la invitación guarda un **hash** del correo; el correo en claro solo pasa hacia Resend. |
| H4 | **El Lab hace polling cada 10 s** mientras la pestaña está activa. Con 10 personas por campaña son ~29.000 lecturas al día por campaña. | Sin polling: se lee al abrir, al volver a la pestaña y con un botón «Actualizar». |
| H5 | **La cuota de KV del plan gratuito son 1.000 escrituras al día para TODO el sitio** (lección de «¿Quién quiere ser juez?», v5.2-v5.3), compartida con Caudal, el Lab, las alertas y el briefing. KV además es *último que escribe gana* y con consistencia eventual: dos personas escribiendo la misma llave pierden cambios. | Regla de diseño: **una llave, un escritor**. Y el conteo de escrituras (§8) sale antes de construir: con uso real, el plan gratuito aguanta un piloto, no una venta. |
| H6 | **`_c360NormalizarCampana` bota en silencio cualquier campo que no conozca** (le pasó a `avales` y `espectro`). | Todo lo del equipo va en llaves y normalizadores propios. No se cuelga nada de `campana`. |
| H7 | **Pertenecer al equipo de una campaña revela orientación política**, y la orientación política es dato sensible en la Ley 1581 (art. 5; ver §2). | Aun en la vía «cada quien con su cuenta», el servidor guarda un dato sensible del integrante: que trabaja para esa candidatura. Eso exige autorización explícita al aceptar, y no se puede condicionar. |

---

## 1. El problema central: gestionar un equipo sin custodiar su base

Tres vías evaluadas y una cuarta que apareció al pensarlas.

### a · Cada integrante con su propia cuenta

La persona recibe una invitación por correo, entra con su cuenta y **ella misma**
autoriza el tratamiento de sus datos al aceptar.

- **A favor.** El dato es de quien tiene la cuenta, no de un tercero que el
  candidato subió. Ya existe el patrón (Lab). Permite permisos por persona,
  reportes firmados por quien los hizo y sacar a alguien del equipo.
- **En contra.** No escala a la base amplia: nadie le va a pedir a 300 testigos
  y 80 líderes que abran cuenta, y si se hiciera, la plataforma quedaría con la
  lista de simpatizantes de la campaña, que es justo lo que no queremos tener.
  Cada invitación y cada aceptación escriben en KV.
- **Riesgo legal.** Bajo y manejable si la autorización se pide bien. Somos
  responsables del dato de la cuenta (como con cualquier usuario) y del registro
  «hace parte del equipo de X», que es sensible (H7). El candidato decide los
  fines del espacio de trabajo (roles, zonas, tareas), así que frente a ese
  contenido él es responsable y nosotros encargados (ver §2).

### b · Local primero

Los contactos viven en el navegador del candidato, en su Drive o en su hoja de
cálculo. El servidor guarda la **estructura**: roles, zonas, tareas y avance, con
identificadores sin nombre («L-07», «T-12»).

- **A favor.** Lo que no se custodia no se puede filtrar, ni pedir, ni vender.
  No nos volvemos encargados de esos datos. Es coherente con Día D y endoso.
  Es un argumento de venta con quien desconfía, que en campaña es casi todo el mundo.
- **En contra.** Si el nombre vive en un solo navegador, el resto del equipo
  solo ve «L-07». Compartirlo exige un mecanismo fuera del servidor (§3.4). Si el
  candidato borra su navegador, pierde los nombres (no la estructura).
- **Riesgo legal.** El más bajo para nosotros. El candidato es responsable de su
  base en su propio archivo, como lo es hoy de su Excel.

### c · Híbrida (recomendada)

**a** para quienes coordinan (el núcleo, entre 5 y 12 personas) y **b** para la
base amplia (líderes, testigos, voluntarios).

### d · Cifrado de punta a punta (evaluada y descartada para v1)

Los nombres se guardan en el servidor cifrados en el navegador con una clave de
la campaña que nunca nos llega (WebCrypto, AES-GCM con clave derivada de una
frase). Resolvería el «solo lo ve un navegador» de **b**.

Se descarta para v1 por tres razones: (1) **no está claro que almacenar un dato
cifrado que no podemos leer deje de ser tratamiento** en la Ley 1581, y eso no
lo pude verificar; (2) si la campaña pierde la frase, pierde los nombres y no
hay soporte que los recupere, y eso va a pasar en la semana de más presión;
(3) repartir la frase a 10 personas por WhatsApp es el eslabón débil de todo el
esquema. Queda como mejora posible si **b** resulta insuficiente en el piloto.

### La recomendación

**Vía c, con dos reglas duras:**

1. **Solo tienen cuenta quienes coordinan.** Testigos, líderes y voluntarios
   nunca son usuarios ni registros del servidor. En el servidor aparecen como
   un identificador, una zona y un contador.
2. **El servidor no acepta texto libre que describa a un tercero.** Los
   identificadores los genera el sistema (`L-07`), no se escriben. El nombre
   humano vive en el **llavero** local (§3.4). En los campos de texto libre que
   sí existen (notas de tareas), se enmascaran correos y corridas de 7+ dígitos,
   como en el mapa del sismo y la HVP, y la interfaz avisa que no se escriban
   nombres de terceros. Eso **reduce**, no elimina: si alguien escribe «visitar a
   doña Marta de la JAC», queda escrito. Se dice en los términos.

Por qué esta y no **a** sola: **a** para todos convierte la plataforma en la base
de simpatizantes de la campaña, que es exactamente Votomap. Por qué no **b** sola:
sin cuentas no hay a quién asignarle una zona ni quién reporte, y la tarjeta se
queda en una hoja de cálculo bonita.

La frase para la tarjeta (argumento de venta): *«Su base de contactos no pasa por
aquí. Acá vive el plan: zonas, metas y tareas. Los nombres de sus líderes y
testigos se quedan en su computador. Lo que no guardamos no se puede filtrar.»*

---

## 2. Lo que dice la Ley 1581 de 2012 (y lo que no pude verificar)

Esto es lectura de la norma para diseñar, **no concepto jurídico**. Antes de la
fase 3 lo tiene que revisar un abogado (pregunta P8).

| Punto | Norma | Qué implica aquí |
|---|---|---|
| Responsable y encargado | Art. 3: el **responsable** decide sobre la base y/o el tratamiento; el **encargado** trata datos por cuenta del responsable. | Datos de la cuenta de cada integrante → responsables nosotros. Contenido del espacio de trabajo de la campaña (roles, zonas, reportes) → el candidato decide los fines, nosotros tratamos por su cuenta: **encargados**. |
| Datos sensibles | Art. 5: incluye los que revelan **orientación política** y la pertenencia a organizaciones o la promoción de intereses de partidos. | Que alguien trabaje en la campaña de X es sensible (H7). Una base de simpatizantes de una campaña es, entera, un banco de datos sensibles. Por eso la vía **b** para la base amplia. |
| Tratamiento de sensibles | Art. 6: prohibido salvo excepciones, entre ellas la **autorización explícita** del titular. Trae otra excepción para organizaciones sin ánimo de lucro de finalidad política respecto de sus miembros. | La excepción de organizaciones políticas es para el partido o la organización, no para un proveedor de software; **no la usamos**. Nos apoyamos en la autorización explícita de cada integrante al aceptar. |
| Autorización | Art. 9: previa, expresa e informada. | Casilla propia, sin marcar, en la pantalla de aceptación, con el texto de qué se guarda, para qué, cuánto tiempo y cómo salir. La aceptación queda registrada con fecha y versión del texto. |
| No condicionar | Decreto 1377 de 2013 (hoy compilado en el Decreto 1074 de 2015): al pedir datos sensibles hay que informar que el titular no está obligado a autorizar. **Artículo exacto sin verificar.** | El texto de aceptación lo dice. Quien no autoriza no entra al equipo, pero la campaña puede seguir trabajando con esa persona fuera de la plataforma. |
| Principios | Art. 4: finalidad, libertad, seguridad, confidencialidad, acceso y circulación restringida. | Permisos por zona en el **servidor** (no solo en la interfaz). Retención limitada (P6). |
| Encargado | Deberes del encargado en el art. 18; contrato de transmisión entre responsable y encargado en el Decreto 1377. **Artículo del contrato sin verificar.** | Los términos de Candidato 360 necesitan una cláusula de encargo para el espacio de trabajo. Hoy no existe. |
| Registro de bases | RNBD ante la SIC; el Decreto 090 de 2018 limitó la obligación por tamaño de la empresa. **Umbral sin verificar.** | Probablemente no nos aplica; que lo confirme el abogado. |
| El candidato como responsable | — | Frente a su llavero y su Excel el responsable es el candidato. La plataforma no lo vuelve responsable de nada nuevo, pero la tarjeta no debería prometerle cumplimiento legal: no somos su asesor. |

Lo que **no** se pudo verificar y queda como pregunta: si guardar datos cifrados
que no podemos leer es tratamiento (vía d), la versión exacta de los artículos del
Decreto 1377 citados arriba, y si alguna regla electoral (CNE) toca el uso de
software para organizar testigos. No inventé artículos para llenar esos huecos.

---

## 3. Modelo de datos

### 3.1 Principios

- **Una llave, un escritor** (H5). El plan lo escribe quien dirige; cada
  integrante escribe solo su propio documento de reportes. Nadie pisa a nadie.
- **Todo cuelga del vínculo.** «Una cuenta, una candidatura» se mantiene: el
  equipo es un anexo del vínculo del candidato. Los integrantes **no** tienen
  vínculo ni acceso a Candidato 360 por su cuenta; tienen acceso **al equipo**.
- **El servidor filtra por rol.** Una coordinadora de zona recibe solo sus zonas
  desde el worker, no un documento completo que la interfaz esconda. (El dato
  electoral es público y se calcula en el navegador: el permiso protege el
  espacio de trabajo, no los resultados de la Registraduría, y se dice así.)
- **Declarado y medido, separados.** Ningún campo reportado por el equipo se
  convierte en votos ni se resta de la meta.

### 3.2 Llaves de KV (worker `rr-auth`)

| Llave | Qué guarda | Escribe | Vida |
|---|---|---|---|
| `c360:eq:<eqId>` | **El plan**: integrantes `{mid, rol, zonas[], alta, estado}`, zonas `{zid, nombre, codigos[], ajusteMeta?}`, tareas del plan, asignación de coordinación de testigos `{puesto → mid}`, aliados por alias `{aid, tipo, zonas[], atiende: mid}`, bitácora de permisos (últimas 200) | dueño y gerente | mientras exista el vínculo; ver P6 |
| `c360:eq:<eqId>:r:<mid>` | **Los reportes de un integrante**: estado de sus tareas, conteos declarados, notas enmascaradas | solo ese integrante | igual |
| `c360:eqmiembro:<correo>` | `{eqId, mid, rol}`: a qué equipo pertenece esta cuenta | aceptar / salir / quitar | mientras sea integrante |
| `c360:eqinv:<token>` | `{eqId, correoHash, rol, zonas, invitadoPor, expira}` | invitar | **TTL 14 días**, se borra al aceptar |
| `c360:eqconsent:<correo>:<ts>` | `{eqId, version, texto hash, aceptadoEn}` | aceptar | **400 días** (prueba de la autorización, como `c360:vinculo-borrado`) |

- `eqId` es un aleatorio de 16 hex que se guarda en el vínculo del dueño
  (`vinculo.equipoId`, campo nuevo con normalizador propio). Así los integrantes
  nunca ven el correo del dueño en una llave.
- `mid` = aleatorio corto. El correo del integrante **no** está en el plan: está
  en su índice `c360:eqmiembro:<correo>`, que solo lee el worker. El plan
  muestra el nombre que la persona puso en su propia cuenta, y lo pone ella.
- **La invitación guarda el hash del correo**, no el correo. Al aceptar, el
  worker compara el hash del correo de la sesión. El correo en claro solo viaja
  a Resend (que es a su vez encargado nuestro: se dice en los términos).

### 3.3 Qué NO se guarda en el servidor

Nombres, celulares, cédulas o direcciones de testigos, líderes o voluntarios.
El texto libre de un tercero. La lista de aliados con nombre (sigue en el
navegador, como hoy en el endoso). La meta por escalones (ya vive en el
navegador, `c360-meta-escalones:*`).

### 3.4 El llavero local

`localStorage['c360-llavero:<eqId>']` = `{ "L-07": "Pedro Gómez · JAC Rincón",
"T-12": "…" }`. Cada navegador tiene el suyo.

Para compartirlo, el dueño **exporta un archivo** (`llavero-<campaña>.json` o
CSV) y lo pasa por donde quiera; quien lo recibe lo importa en su navegador.
Opcional (fase 6): exportar ese archivo con una frase, cifrado en el navegador,
para que no viaje en claro por WhatsApp. El servidor no participa.

Una prueba de Playwright se asegura de que **ningún valor del llavero aparezca en
ninguna petición al worker** (§10).

---

## 4. Roles y permisos

| Rol | Cuántos | Ve | Escribe |
|---|---|---|---|
| **Dueño** (la cuenta vinculada) | 1 | todo | todo; es el único que puede borrar el equipo |
| **Gerencia** | 0-2 | todo el espacio de trabajo | plan, invitaciones, zonas, tareas; no toca el vínculo ni el pago |
| **Coordinación territorial** | 1-8 | **solo sus zonas**: su sub-meta, sus puestos, sus tareas, los aliados (alias) de su zona | sus reportes; tareas dentro de sus zonas |
| **Comunicaciones** | 0-2 | tareas asignadas; los paneles 04 y 05 **en lectura** | sus reportes |
| **Jurídica** | 0-2 | el plan del Día D completo (puestos, alertas, coordinación asignada) | sus reportes |
| **Coordinación de testigos** | 0-6 | los puestos del Día D que le tocan, con sus alertas | sus reportes (cuántos testigos confirmados por puesto, sin nombres) |

Testigos, líderes y voluntarios **no tienen rol ni cuenta** (vía b).

Reglas:
- El filtro por zona lo aplica el worker al armar la respuesta de
  `GET /c360/equipo`. Es una función pura en `src/c360-equipo.js` (como
  `c360-redes.js`) con su prueba en Node.
- Si el acceso del dueño se vence, el equipo queda **en lectura** 30 días para
  exportar y después se cierra (P9).
- Una cuenta pertenece a **un** equipo a la vez (P5). Quien quiera vincular su
  propia candidatura tiene que salir antes del equipo, y quien ya tiene un
  vínculo no puede aceptar una invitación. Así no se rompe «una cuenta, una
  candidatura».

---

## 5. Qué hace la tarjeta (priorizado)

| # | Función | Va | Fase | Nota |
|---|---|---|---|---|
| 1 | Roles y permisos | sí | 3 | §4 |
| 2 | **La meta repartida por zona** | sí, primero | 1-2 | Es el puente con lo que ya vendemos. Funciona **sin equipo**: el candidato solo ya ve sus sub-metas. |
| 3 | Tareas y avance | sí | 2 (local) · 4 (con equipo) | §5.3 |
| 4 | Testigos para el Día D | sí | 5 | Coordinación por puesto; testigos sin nombre. |
| 5 | Aliados y líderes de zona | sí | 5 | Alias + zona + quién lo atiende; el nombre en el llavero. |
| 6 | Plan de la semana | **sí, aquí** | 6 | Su salida son tareas: separarlo en otra tarjeta obligaría a copiar tareas entre dos sitios. El cálculo va en su propia sección del módulo. |
| 7 | Comunicación interna | **no** | — | No competimos con WhatsApp. Cada tarea tiene un botón «Enviar por WhatsApp» que abre `https://wa.me/?text=…` con el mensaje armado; **sin número**: la persona elige el contacto en su teléfono y no guardamos ningún celular. |
| 8 | Exportar e importar | sí, con cuidado | 7 | §5.6 |

### 5.1 La meta repartida por zona

- Una **zona** es un conjunto de códigos de la escala que el mapa ya maneja
  (localidad · comuna · UCG · barrio · puesto · municipio). Se arma tocando el
  mapa, como el selector de zona del líder en el endoso.
- **Sub-meta = la meta del escenario elegido repartida con la MISMA función del
  mapa en «Proyectado»**, sumada sobre los códigos de la zona. Por eso la fase 1
  extrae ese reparto (H1).
- Se muestran **los cuatro escalones** por zona (inminente · probable · posible ·
  deseado), con el elegido marcado, porque así se muestra la meta en el CRM.
- La gerencia puede **ajustar a mano** la sub-meta de una zona. Queda rotulado
  «ajustada por la campaña», y el total de las zonas se compara con la meta: si
  no suman lo mismo, se dice cuánto sobra o falta. No se reparte en silencio.
- Zonas que no cubren todo el territorio → «N puestos y X % de la meta sin
  responsable». Zonas que se pisan → aviso.
- La base de cada zona se declara: «según su votación de 2023», «según su familia
  política en 2023» o «según el censo» (la misma nota que pinta el mapa).

### 5.2 Declarado contra medido

Dos columnas que no se cruzan nunca:

| Medido (dato público) | Declarado (lo reporta el equipo) |
|---|---|
| Sub-meta de la zona, su votación en 2023 ahí, censo, dónde le pega el electorado, peso de sus aliados (estimado, con rango) | Visitas hechas y planeadas, reuniones, eventos, testigos confirmados por puesto, firmas recogidas (si va por firmas) |

El avance que se pinta es **tareas hechas / tareas planeadas**, nunca «votos
conseguidos». Si Ricardo decide admitir «compromisos declarados» (P7), van como
conteo sin nombres, rotulados «declarado por la campaña», y **no se restan de la
meta**.

### 5.3 Tareas

`{tid, tipo, zona|puesto, asignada: mid, fecha, estado, nota}`. Tipos cerrados:
visita a barrio · reunión con aliado (alias) · evento · puerta a puerta ·
recolección de firmas · capacitación de testigos · otra.

- La **crea** gerencia (en el plan) o una coordinadora dentro de su zona (en su
  propio documento). El **estado** lo cambia quien la tiene asignada, en su
  documento. Así cada llave sigue con un solo escritor.
- Guardado explícito o con espera de 5 s, no en cada tecla.

### 5.4 Testigos y Día D

- Parte de `C360DiaD.fuente` y `testigosPara`: el plan de puestos ya calculado,
  con sus alertas (sin señal móvil, sin internet, sin dónde publicar el E-14,
  orden público…).
- La gerencia asigna puestos a una **coordinación de testigos**. Esa persona ve
  sus puestos con las alertas, y reporta **cuántos** testigos tiene confirmados
  por puesto. Nunca quiénes.
- El CSV del Día D gana una columna «Coordinación» (el nombre que esa persona
  puso en su cuenta), y conserva «Testigo» en blanco.

### 5.5 Aliados

- El endoso sigue calculándose en el navegador del dueño con los nombres.
- Al publicar un aliado al equipo sube solo `{aid, tipo, zonas[], atiende: mid,
  pesoEstimado?}`. El peso va con su rango y el rótulo del endoso.
- La coordinadora ve «A-03 · pesa en 4 puestos de su zona · lo atiende usted»; el
  nombre aparece solo si importó el llavero.

### 5.6 Exportar e importar

- **Exportar**: CSV documentado por hoja (zonas y sub-metas, puestos con
  coordinación, tareas). Códigos de puesto de 9 caracteres de la Registraduría
  (con letra en 187 puestos: no limpiar con `\D`), que es lo que cualquier
  sistema electoral colombiano entiende.
- **Importar**: solo estructura. Si el archivo trae nombres, celulares o cédulas,
  el importador los manda **al llavero local** y al servidor solo sube el
  identificador. Se prueba con un archivo que trae celulares (§10).
- **No conozco el formato de Vote360 ni de Votomap** y no encontré una
  especificación pública en esta revisión. No se promete compatibilidad hasta
  tener una exportación real de un cliente (P11).

---

## 6. La frontera con Vote360, Votomap, Avanzoft/Socilítica y Campane

| Hacemos | No hacemos |
|---|---|
| La meta, de dónde sale y cómo se reparte en el territorio | Base de simpatizantes con cédula y celular |
| Zonas con sub-meta y responsable | Pirámide de referidos (quién trajo a quién) |
| Tareas sobre territorios, no sobre personas | Detección de cédulas duplicadas |
| El plan de testigos por puesto con sus alertas | App de testigos que transmite el E-14 |
| Aliados como peso territorial estimado | Mensajería masiva, SMS, WhatsApp Business |
| Exportar para que su operación siga en su sistema | Custodiar la base de la campaña |

Frase de posicionamiento: *«Su sistema de campaña sabe a quién tiene. Candidato
360 le dice dónde le faltan votos y quién del equipo va a ir por ellos.»*

---

## 7. Qué se reusa (y qué no se duplica)

| Pieza | De dónde | Cómo |
|---|---|---|
| Reparto de la meta por zona | `candidato-360.js` (H1) | **Se extrae** a `candidato-360-reparto.js`; el CRM y el panel llaman lo mismo |
| Escalones de la meta | `c360-meta-escalones:*` + `META_ESCENARIOS` | Se leen del navegador, como en el panel del endoso |
| Plan de testigos y alertas | `C360DiaD.fuente`, `testigosPara`, `alertas`, `csv` | Se llaman; el CSV gana una columna |
| Territorio, georef, comuna | `C360Endoso.alcanceDe`, `enAlcance`, `areaDe`, `comunaDesde` | Se llaman |
| Aliados y su peso | `C360Endoso.evaluar`, `porPuesto` | Se llaman en el navegador del dueño |
| Dónde le pega | `candidato-360-electorado.js` | Para el plan de la semana |
| Selector de zona en el mapa | panel del endoso (líder de zona) | Se generaliza |
| Invitación por correo | `micmacInvite` / `micmacAccept` | Mismo flujo; correo en hash, consentimiento explícito |
| Sesión, muro, vínculo | `candidato-360-panel.js`, `_c360AccesoDe` | El chasis del panel; el acceso del integrante se deriva del del dueño |
| Enmascarado de texto libre | mapa del sismo / `build_hvp.py` | Mismo criterio (correos y 7+ dígitos) |

---

## 8. Rutas del worker y su costo en escrituras

Todo en `src/c360-equipo.js` (funciones puras: normalizar, filtrar por rol,
enmascarar) + el guarda en `index.js`. Tope de tamaño por documento.

| Ruta | Guarda | Escrituras |
|---|---|---|
| `GET /c360/equipo` | sesión; dueño con acceso vigente **o** integrante de un equipo cuyo dueño tiene acceso | 0 |
| `POST /c360/equipo/plan` | dueño o gerencia; normalizador estricto, sin texto libre de terceros | 1 |
| `POST /c360/equipo/invitar` | dueño o gerencia; tope de puestos (P2); 10 invitaciones por día por equipo | 1 (+ correo) |
| `POST /c360/equipo/aceptar` | sesión cuyo hash de correo casa; sin vínculo propio; sin otro equipo; `acepto: true` + versión del texto | 3 (índice, consentimiento, plan) + 1 borrado del token |
| `POST /c360/equipo/reporte` | integrante; escribe solo `:r:<su mid>`; filtra tareas fuera de sus zonas | 1 |
| `POST /c360/equipo/salir` | integrante | 2-3 (índice, plan, borrar reportes) |
| `POST /c360/equipo/quitar` | dueño o gerencia | 2-3 |
| `DELETE /c360/equipo` | solo dueño | 1 + N integrantes |

⚠️ En KV un `delete` cuenta como escritura (H5).

**Campaña típica de concejo** (dueño + gerencia + 6 coordinaciones + comunicaciones
+ jurídica = 10 cuentas):

| Momento | Escrituras |
|---|---|
| Montar el equipo (una vez): 9 invitaciones + 9 aceptaciones + ~20 guardados del plan | ~65 |
| Día normal de campaña: 5 guardados del plan + 6 coordinaciones × 3 reportes + 2 de otros roles | ~25 |
| Últimas dos semanas | ~60 por día |
| Día D (coordinación de testigos reportando confirmados) | ~80 |

Lecturas: abrir, volver a la pestaña, «Actualizar». Unas 200 al día por campaña
(el plan gratuito da 100.000 lecturas al día; no es el problema).

**Consecuencia:** con el plan gratuito (1.000 escrituras al día para todo el
sitio) caben unas cuantas campañas de piloto, no una venta. Antes de la fase 3
hay que decidir entre el plan pago de Workers (5 USD al mes, 1 millón de
escrituras al día) o mover reportes y tareas a D1 (P4). La recomendación es el
plan pago: no cambia la arquitectura y el costo es menor que una sola venta.

---

## 9. Maquetas

### 9.1 Tarjeta 11 en el CRM

```
┌─ 11 · EQUIPO ─────────────────────────────────────────────────────┐
│  Meta probable 17.600 repartida en 6 zonas                        │
│                                                                   │
│  Norte · Andrea (coord.)      4.200  ████████░░  12/15 tareas     │
│  Suba Rincón · sin asignar    3.100  ░░░░░░░░░░  ⚠ sin responsable│
│  Engativá · Julián            2.900  █████░░░░░  6/12             │
│  …                                                                │
│  ─────────────────────────────────────────────────────────────    │
│  Día D: 62 puestos en el plan · 40 con coordinación asignada      │
│  Aliados: 7 en el mapa · 5 con alguien del equipo que los atiende │
│                                                                   │
│  Tareas = lo que reporta su equipo. Meta = dato electoral.        │
│  Sus contactos no pasan por aquí.            [ Abrir el equipo → ]│
└───────────────────────────────────────────────────────────────────┘
```

### 9.2 Panel `candidato-360-equipo.html` (vista del dueño y la gerencia)

```
[ Equipo ] [ Zonas y metas ] [ Tareas ] [ Día D ] [ Aliados ] [ Semana ]

Zonas y metas
┌──────────────── mapa ────────────────┐  Zona seleccionada: Norte
│  zonas coloreadas por responsable    │  Responsable: Andrea
│  borde grueso = zona abierta         │  Sub-meta: inminente 2.100 · probable 4.200
│  punteado = sin responsable          │            posible 5.300 · deseado 12.600
└──────────────────────────────────────┘  Base: su familia política en 2023
                                          23 puestos · 4 aliados (alias)
Suma de las zonas: 17.600 de 17.600 ✓     [ Editar zona ] [ Ajustar a mano ]
```

### 9.3 La vista de una coordinadora (mismo panel, filtrado por el worker)

```
Su zona: Norte                        Coordinación territorial
Sub-meta probable 4.200  ·  su votación 2023 aquí: 1.870
[ Mis tareas (15) ] [ Mis puestos (23) ] [ Aliados de mi zona (4) ]
Tarea: puerta a puerta · Barrio La Alhambra · jueves
   [ Hecha ] [ Enviar por WhatsApp ]
```

### 9.4 Vitrina (sin pago)

- Se ven **las sub-metas por zona del territorio real** de la búsqueda: son dato
  público y es el gancho («así se reparte su meta si arma 6 zonas»).
- El equipo, las tareas y los reportes son de **ejemplo**, con el rótulo «datos
  de ejemplo», y borrosos con candado como el resto del CRM (`candadoDetalle`).
- Invitar, crear zonas y exportar abren el muro. En vitrina no se escribe nada
  en el worker (`CRM_VITRINA`).

---

## 10. Pruebas

Playwright contra el HTML real con todo lo remoto simulado (`page.route`), como
las suites que ya existen, más pruebas en Node del worker.

| Suite | Qué comprueba |
|---|---|
| `prueba-reparto.mjs` (fase 1) | El módulo extraído da **exactamente** las mismas cifras que el código del CRM en los casos de siempre: Claudia López (recorte), JAL de Teusaquillo, salto JAL → Concejo, mudanza de localidad, Cartagena por UCG, salto a departamento. Extrae la función vieja de `HEAD`, como `prueba-endoso.mjs`. |
| `prueba-equipo.mjs` | Zonas y sub-metas; la suma contra la meta; zonas que se pisan; ajuste manual rotulado. |
| `prueba-equipo-privacidad.mjs` | **Ningún valor del llavero sale en ninguna petición** (se intercepta todo). Importar un CSV con celulares no los manda al worker. El enmascarado de notas. |
| `prueba-equipo-roles.mjs` | Con el worker simulado por rol: la coordinadora solo recibe sus zonas y la interfaz no muestra lo demás; comunicaciones no puede editar el plan. |
| `prueba-equipo-vitrina.mjs` | Sin acceso: sub-metas reales, equipo de ejemplo rotulado, invitar abre el muro, cero escrituras. |
| `rr-auth/test/c360-equipo.test.mjs` | Normalizador; filtro por rol; hash del correo en la invitación; aceptar exige casilla y sin vínculo propio; un escritor por llave; tope de puestos. |
| `prueba-candi.mjs` | La vista `equipo` en `VISTAS` y en `C360_CANDI_VISTAS` del worker. |

---

## 11. Fases

| # | Qué | Sale |
|---|---|---|
| 0 | Decisiones de Ricardo (§12) y revisión del abogado del texto de aceptación y la cláusula de encargo. | antes de la fase 3 |
| 1 | Extraer el reparto de la meta a `candidato-360-reparto.js` **sin cambiar cifras**. El CRM lo usa. `prueba-reparto.mjs`. | no se ve nada nuevo |
| 2 | **El equipo sin servidor**: zonas con sub-meta, tareas y llavero, todo en el navegador del dueño, con exportar. Tarjeta 11 y panel. Ya sirve a quien trabaja solo o con su equipo por fuera. | primera versión usable |
| 3 | Cuentas del equipo: invitar, aceptar con consentimiento, roles, `GET` filtrado, salir y quitar. Plan del worker en KV. | requiere P4 resuelta |
| 4 | Reportes por integrante; avance declarado contra la sub-meta. | |
| 5 | Día D (coordinación de testigos por puesto) y aliados por alias. | |
| 6 | Plan de la semana: puestos y barrios donde falta más para la sub-meta, cruzados con dónde le pega el electorado y dónde pesan sus aliados, convertidos en tareas asignables. Llavero exportable con frase. | |
| 7 | Exportar e importar para convivir con otros sistemas, después de ver una exportación real (P11). | |
| 8 | Candi (`VISTAS` + `C360_CANDI_VISTAS`), `candidato-360.md` y cierre. | |

La fase 2 es la importante comercialmente: demuestra el valor (la meta convertida
en zonas y trabajo) sin tocar el servidor ni la cuota, y sin ningún riesgo legal
nuevo. La 3 solo vale la pena si el piloto de la 2 muestra que el candidato
quiere que su equipo entre.

---

## 12. Preguntas que tiene que decidir Ricardo antes de construir

1. **¿Vía c (híbrida)?** Cuentas solo para quien coordina, la base amplia fuera
   del servidor y sin texto libre sobre terceros.
2. **¿Cuántos puestos de equipo por corporación?** Propuesta: JAL 4 · concejo de
   municipio 6 · concejo de capital y asamblea 10 · alcaldía y gobernación 15.
3. **¿Cambia el precio?** Opciones: (a) módulo aparte al 30 % del plan base de su
   corporación, que es la regla de precios del 6 de septiembre; (b) incluido
   solo en el plan Completo; (c) puestos adicionales pagos. Los competidores
   cobran por usuario; nuestra ventaja es no tener que hacerlo. Propuesta: (a),
   con los puestos de la P2 incluidos.
4. **Cuota de KV:** ¿plan pago de Workers antes de la fase 3, o D1 para reportes
   y tareas? Propuesta: plan pago.
5. **¿Una cuenta puede estar en más de un equipo?** Los consultores trabajan
   varias campañas a la vez, pero dos campañas rivales en el mismo territorio con
   la misma persona adentro es un problema de confianza para las dos. Propuesta:
   uno a la vez.
6. **Retención:** ¿cuánto vive el espacio de trabajo después de la elección?
   Propuesta: 90 días después de la jornada o 30 días después de que se venza el
   acceso del dueño, lo primero que pase, con aviso para exportar.
7. **¿Se admiten «compromisos declarados»** (conteo sin nombres por zona)? Pedirán
   algo así. Si entra, va rotulado y nunca se resta de la meta.
8. **Abogado:** texto de autorización de sensibles, cláusula de encargo en los
   términos, y si nos aplica el RNBD. Sin esto no se abre la fase 3.
9. **Si se vence el acceso del dueño,** ¿el equipo queda en lectura 30 días o se
   cierra de una?
10. **¿Comunicaciones ve los paneles 04 y 05?** La escucha tiene costo por cuenta
    (Apify) y hoy está apagada; propuesta: en lectura.
11. **¿Consigues una exportación real de Vote360 o Votomap** de algún candidato
    que los use? Sin eso la fase 7 se queda en CSV propio.
12. **Gasto de campaña:** el pago de la plataforma es un gasto que la campaña
    reporta ante el CNE. ¿Queremos que la factura lo facilite (concepto,
    periodo)? Es pregunta de jurídica, no la resolví.

---

## Bitácora

**28-sep-2026.** Plan escrito. Sin código de producto.
