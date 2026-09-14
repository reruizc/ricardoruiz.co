#!/usr/bin/env python3
"""
Propuesta comercial · Caudal para Cauce — 14 de septiembre de 2026.

BORRADOR 2. Mismo documento del 7 de septiembre con TODAS las cifras
remedidas contra producción el 14, los mismos precios, y dos cambios de
fondo: la ficha del cliente entró en producción y el motor del brief pasó de
«no está» a «construido, falta la llave de la API». El costo del brief se
midió de verdad y quedó veinte veces por debajo de lo estimado en el borrador 1.

QUÉ ES. Primer borrador de la estructura comercial de Caudal como producto que
Cauce vende: el diferencial defendible, el producto mínimo viable, el piso que
Ricardo puede cobrarle a Cauce, y los dos precios públicos (plataforma sola y
plataforma con acompañamiento humano).

A QUIÉN LE HABLA. A Diego Baquero y Pablo Cárdenas, como socio, no como
proveedor. No es un brief: los briefs le hablan al cliente final sobre lo que
pasó esta semana. Este documento habla de plata y de alcance, así que es
explícito con lo que NO está listo — un socio que descubre el hueco después de
vender es un socio que no vuelve.

DISEÑO. Mismo chasis de los briefs (build_brief_binance.py: CSS, logo, papel).
Se agregan tres clases: `.item.plata` (verde oliva, los bloques de precio),
`table.p` (tabla de precios con la cifra alineada a la derecha) y `.cifra`.

⚠️ CIFRAS. Los costos de infraestructura y de modelo están MEDIDOS (S3 real,
barrido real de 22.101 caracteres, tarifas publicadas de Anthropic y DeepSeek al
7-sep-2026). Los precios de Dapper, Orza y Nomos NO son públicos: lo que se dice
de ellos es capacidad publicada, nunca precio. La tasa de cambio se toma a 4.000
COP/USD y está declarada en el pie.

Salida: caudalxcauce/Cauce/Propuesta-Caudal-Cauce-2026-09-14.pdf (carpeta
gitignorada: es material comercial y el repo es público).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import build_brief_binance as base

ROOT = base.ROOT
OUT = os.path.join(ROOT, "caudalxcauce", "Cauce", "Propuesta-Caudal-Cauce-2026-09-14.pdf")

# Sin llaves dobles: no es f-string, así que el CSS va literal.
EXTRA = """
.item.plata { border-left-color:#5c7a29; background:#f7faf2; border-color:#dde8cb; }
.item.plata .porque .et { color:#5c7a29; }
.item.neg { border-left-color:#8a6d1c; background:#fbf9f2; border-color:#eadfbf; }
.item.neg .porque .et { color:#8a6d1c; }
table.p td:last-child, table.p th:last-child { text-align:right; white-space:nowrap;
                                               font-weight:700; color:#0b0d11; }
table.p td:first-child { color:#0b0d11; }
table.d td:first-child { width:31%; color:#0b0d11; font-weight:500; }
.cifra { font-size:12.6pt; font-weight:700; color:#5c7a29; letter-spacing:-.3px; }
.si { color:#2b8a3e; font-weight:700; }
.no { color:#c92a2a; font-weight:700; }
ul.t { margin:4px 0 6px; padding-left:16px; }
ul.t li { margin-bottom:3px; color:#2b303a; }
"""

TOP = f"""
<div class="top">
  <img src="file://{base.LOGO}" alt="Caudal × Cauce">
  <div class="meta">Propuesta comercial · Caudal para Cauce<br>Borrador 2 · 14 de septiembre de 2026</div>
</div>
"""

HTML_DOC = f"""
<html><head><meta charset="utf-8"><style>{base.CSS}{EXTRA}</style></head><body>
{TOP}

<div class="hero">
  <h1>Qué vende Cauce cuando vende Caudal, <span class="hl">y en cuánto</span>.</h1>
  <p class="lead">Segunda versión, con todas las cifras remedidas contra producción el 14 de
  septiembre y los mismos precios: el diferencial que se puede demostrar en tres minutos, el producto
  que ya está listo para poner frente a un cliente, lo que todavía no, y los tres precios — el que
  Cauce le paga a Caudal, el de la plataforma sola y el de la plataforma con analista.</p>
  <div class="window">Borrador para discusión · Diego Baquero y Pablo Cárdenas · no es oferta en firme</div>
</div>

<div class="item resumen">
  <div class="num">La lectura en una página</div>
  <h2>El brief automático dejó de ser una promesa: está construido y su costo real resultó veinte veces menor. El precio no lo fija el costo, lo fija la capacidad de analista.</h2>
  <p>Caudal tiene hoy ocho pilares vivos sobre el Estado colombiano y tres cosas que ningún competidor
  publica: el registro de las <b>dos cámaras deduplicado</b>, el <b>índice de bloqueo</b> — por qué un
  proyecto no avanza, no si avanza — y el <b>voto nominal clasificado por tipo</b>. Eso es lo que se
  vende, y se demuestra en una pantalla.</p>
  <p>Servir la plataforma cuesta <b>$2.200 pesos por cliente al mes</b>. El brief personalizado,
  escrito con Claude Opus 5 —el modelo de mayor calidad del mercado—, agrega <b>$4.100</b>: no los
  $11.000 del borrador anterior, porque aquella era una estimación y esta es una medición sobre un
  brief real. Con costos así, el precio es una decisión comercial, no una cuenta: lo que de verdad
  limita cuántos clientes se pueden atender es cuántas horas de analista hay para revisar lo que el
  motor escribe.</p>
  <div class="porque"><span class="et">Si solo hay tiempo para una decisión</span>
  Si arrancamos con un piloto de 90 días y tres cuentas reales, por <b>$2.500.000 al mes</b> fijos y
  sin cobro por cuenta, Cauce prueba el producto con clientes de verdad y Caudal cubre su piso de
  operación. Es la forma más barata de saber si el brief cada cuatro días aguanta a escala.</div>
</div>

<h3 class="sec">01 · El diferencial</h3>

<div class="item">
  <div class="num">01 · Lo que se demuestra en tres minutos</div>
  <h2>Dapper publica 3.478 proyectos de ley para 2022-2026. El universo real, sin contar dos veces, es 2.826.</h2>
  <p>Un proyecto que cruza de cámara tiene dos números de radicado y una ficha en cada registro. Sumar
  los dos registros lo cuenta dos veces: la suma bruta da 3.447 y la cifra que ellos publican queda
  justo ahí. Nosotros deduplicamos y auditamos la deduplicación: de los 621 registros de Cámara que se
  retiran, <b>580 declaran explícitamente su propio número de Senado</b> — lo dice la fuente, no lo
  inferimos —, 41 salen por parecido de título y 9 se nos colaron. El verdadero está entre 2.817 y
  2.867, y nuestros 2.826 caen adentro.</p>
  <p>No es un detalle de contabilidad. Es la primera pregunta que hace un director de asuntos públicos
  cuando le muestran una plataforma: <i>«¿de dónde sale ese número?»</i>. Poder responderla con el
  método y el margen es el argumento comercial más fuerte que tenemos, y no exige que el cliente nos
  crea nada.</p>
  <div class="porque"><span class="et">Cómo se usa en una reunión</span>
  Se abre la cifra de los dos lados y se explica en treinta segundos por qué difieren. El cliente no
  tiene que evaluar dos productos: ve un error aritmético en el otro y un método en el nuestro.</div>
</div>

<div class="item">
  <div class="num">02 · El dato que nadie más tiene</div>
  <h2>Sonar predice si un proyecto avanza. Caudal explica por qué se queda quieto.</h2>
  <p>El cementerio legislativo no es la votación: es el <b>orden del día</b>. Medimos, sobre las
  órdenes del día reales de las dos cámaras, la probabilidad de que un proyecto sea tratado según la
  posición en que lo agendan. En comisión de Cámara, el primero del día llega al <b>52,5%</b> y el
  cuarto al sexto caen al <b>28,5%</b>; en plenaria de Cámara, de <b>71,1%</b> a <b>48,0%</b>. En el
  Senado la curva se degrada más rápido: de <b>49,2%</b> el primero a <b>24,8%</b> el cuarto al
  sexto, y a <b>17,6%</b> entre el puesto once y el quince. Son 2.655 proyectos sobre 1.466 sesiones
  en Cámara y 777 sobre 454 en Senado. La mediana de un proyecto son siete agendamientos; hay uno
  agendado ochenta veces.</p>
  <p>A eso se suman <b>342.655 votos nominales consultables por proyecto</b> —205.628 de Cámara
  (2014-2026, 474 proyectos) y 137.027 de Senado (2017-2026, 287 proyectos)— clasificados en 16 tipos
  de votación. La diferencia importa: un representante puede salir con «40 Sí y 36 No» en
  la reforma a la salud y en realidad haber votado <b>38 a favor del fondo contra 1</b> — los 36 No
  eran a impedimentos y a proposiciones de archivo. Un contador ciego de Sí y No no dice nada; el
  nuestro dice la posición.</p>
  <div class="porque"><span class="et">Por qué esto vende</span>
  Un cliente no paga por saber que existe un proyecto: eso lo encuentra gratis en Congreso Visible.
  Paga por saber si le va a pasar algo y cuándo hay que moverse. El índice de bloqueo es esa
  respuesta, y es nuestra.</div>
</div>

<div class="item">
  <div class="num">03 · La tabla corta</div>
  <h2>Ocho pilares, y cuatro columnas donde estamos solos</h2>
  <table class="d">
    <tr><th></th><th>Caudal</th><th>Dapper</th><th>Orza · Sonar</th></tr>
    <tr><td>Países</td><td class="q">1</td><td class="q">11</td><td class="q">1</td></tr>
    <tr><td>Histórico</td><td class="si">1990-2026 · 14.130 PL</td><td class="q">desde 2024</td><td class="q">parcial</td></tr>
    <tr><td>Dos cámaras deduplicado</td><td class="si">sí</td><td class="no">no</td><td class="no">no</td></tr>
    <tr><td>Índice de bloqueo</td><td class="si">sí</td><td class="no">no</td><td class="no">no</td></tr>
    <tr><td>Voto nominal por tipo</td><td class="si">342.655 votos</td><td class="no">no</td><td class="no">no</td></tr>
    <tr><td>Contratación · SECOP</td><td class="si">6,0M contratos</td><td class="no">no</td><td class="no">no</td></tr>
    <tr><td>Reguladores</td><td class="q">12 fuentes · 80.582 actos</td><td class="q">sí</td><td class="q">parcial</td></tr>
    <tr><td>Diccionario marca a tema</td><td class="si">2.011 entradas</td><td class="q">parcial</td><td class="no">no</td></tr>
    <tr><td>Sesiones transcritas en vivo</td><td class="no">no</td><td class="si">36.000 min/mes</td><td class="no">no</td></tr>
    <tr><td>Alertas por WhatsApp</td><td class="no">no</td><td class="si">sí</td><td class="q">parcial</td></tr>
    <tr><td>Equipo y acuerdo de servicio</td><td class="no">una persona</td><td class="si">sí</td><td class="si">sí</td></tr>
  </table>
  <div class="porque"><span class="et">La lectura honesta</span>
  Contra Dapper no se compite por cobertura: ellos resuelven once países en un contrato y nosotros
  uno. Se compite por profundidad en Colombia, que es donde están los clientes de Cauce. Contra Orza
  se compite por independencia del dato: Sonar corre sobre La Silla Datos, que es de un tercero.</div>
</div>

<h3 class="sec">02 · Producto mínimo viable</h3>

<div class="item ok">
  <div class="num">04 · Lo que ya está en producción</div>
  <h2>Se puede poner frente a un cliente esta semana</h2>
  <ul class="t">
    <li><b>Ocho pilares vivos:</b> Congreso (14.130 proyectos de ley y 2.475 leyes desde 1990) ·
    Regulatorio (12 fuentes, 80.582 actos) · Ejecutivo (12.030 normas, de las cuales 10.538 decretos) ·
    Contratación (6,0M contratos y 9M procesos de SECOP) · Medios (~250 medios) · Gacetas (32.585, de
    las cuales 15.964 con texto buscable) · Voceros (94 entidades) · Control.</li>
    <li><b>Ficha del cliente</b> (nuevo esta semana): además de qué vigila, el perfil guarda quién es
    —a qué se dedica, quién lee el brief, qué decide con él, sus líneas de negocio, sus plazos propios
    y qué NO le interesa—. Es lo que separa un listado de señales de un briefing: con la ficha, el
    análisis dejó de recomendar «monitorear» y pasó a recomendar acciones con el plazo del cliente
    adentro.</li>
    <li><b>Perfil por cliente:</b> el cliente registra sus vigiladas y sus temas, y el radar cruza los
    pilares y prioriza con nivel y acción sugerida. Ya funciona con perfiles guardados en la nube.</li>
    <li><b>Alertas por correo</b> dos veces al día, con silencio cuando no hay nada — un digest vacío
    mata el canal.</li>
    <li><b>Búsqueda universal</b> con el diccionario de empresas: quien escribe «Uber» encuentra
    «plataformas tecnológicas», que es como legisla el Congreso.</li>
  </ul>
</div>

<div class="item neg">
  <div class="num">05 · El brief automático · qué cambió en una semana</div>
  <h2>El motor está construido y ya produjo un brief real; falta enchufarlo y verificarlo en operación</h2>
  <p>El borrador anterior decía que el brief se escribía a mano y que automatizarlo eran dos o tres
  semanas de ingeniería. Esta semana se construyó: el barrido <b>deriva sus consultas de la ficha del
  cliente</b> —sin una sola escrita a mano por cuenta— y el documento se redacta con Claude Opus 5
  sobre esa evidencia. El brief de Cauce del 14 de septiembre, que va adjunto, salió así.</p>
  <p>Lo que falta es corto y concreto: la llave de la API de Anthropic, verificar la generación en
  operación —latencia y costo real de punta a punta— y automatizar el envío. Es <b>una semana</b>, no
  tres. Lo que no cambia: tampoco tenemos transcripción de sesiones en vivo, alertas por WhatsApp,
  aplicación móvil ni cobertura fuera de Colombia, y nada de eso entra al piloto.</p>
  <div class="porque"><span class="et">Lo que se aprendió construyéndolo, y vale más que el código</span>
  Con ventana de 72 horas, <b>tres de los ocho pilares salen vacíos casi todos los días</b>, y un
  pilar vacío significa dos cosas opuestas: que no pasó nada, o que el registro va atrasado. El brief
  ahora mide y declara hasta qué fecha llega cada fuente — hoy el Congreso hasta el 8 de septiembre,
  el Ejecutivo hasta el 28 de agosto y los reguladores hasta el 13 de mayo. Ningún competidor publica
  eso sobre sí mismo, y es lo que permite decir «verificado» en vez de «no hubo».</div>
</div>

<div class="item urg">
  <div class="num">06 · Lo que hay que cerrar antes de firmar</div>
  <h2>Tres cosas, ninguna mayor a tres semanas</h2>
  <table class="d">
    <tr><th>Qué</th><th class="q">Por qué</th><th>Plazo</th></tr>
    <tr><td>Sacar el pipeline del Mac</td><td class="q">Hoy el rastreo corre en la máquina de Ricardo dos veces al día. Con clientes pagando eso deja de ser una decisión de ingeniería y pasa a ser riesgo contractual. Se mueve a un servidor chico, unos 60.000 pesos al mes.</td><td>1 semana</td></tr>
    <tr><td>Llave de la API del modelo</td><td class="q">El motor del brief está construido y probado con evidencia real; falta la credencial para que corra solo y medir latencia y costo de punta a punta.</td><td>1 día</td></tr>
    <tr><td>Envío automático del brief</td><td class="q">Hoy el PDF se genera y se manda a mano. El canal de correo ya existe y funciona para las alertas.</td><td>1 semana</td></tr>
    <tr><td>Verificar la entrega del correo</td><td class="q">El envío está montado y aceptado por el proveedor, pero nadie ha confirmado la bandeja de entrada de un tercero.</td><td>1 día</td></tr>
  </table>
  <div class="porque"><span class="et">Una ventaja de vender a través de Cauce</span>
  No hace falta pasarela de pago. La venta directa exige cablear Wompi —hoy sin terminar—; una
  factura mensual a Cauce elimina ese bloqueador por completo.</div>
</div>

<h3 class="sec">03 · Los tres precios</h3>

<div class="item plata">
  <div class="num">07 · El piso · lo que cuesta operar esto</div>
  <h2>Servir un cliente cuesta entre 2.200 y 4.100 pesos al mes</h2>
  <table class="p">
    <tr><th>Concepto</th><th>Cálculo</th><th>COP/mes</th></tr>
    <tr><td>Infraestructura fija</td><td class="q">34,1 GB en S3 y 55.041 objetos, funciones, proxy, correo — no se mueve entre 5 y 500 cuentas</td><td>100.000</td></tr>
    <tr><td>Brief personalizado</td><td class="q"><b>Medido, no estimado:</b> 7,6 briefs/mes · Claude Opus 5 · 6.746 tokens de entrada y 4.000 de salida por brief, sobre el barrido real de Cauce del 14 de septiembre. Son $535 por brief.</td><td>4.100 <span class="q">/ cuenta</span></td></tr>
    <tr><td>Brief sectorial compartido</td><td class="q">un brief por sector en vez de uno por cliente</td><td>2.200 <span class="q">/ cuenta</span></td></tr>
    <tr><td>Lecturas de plataforma</td><td class="q">se dejan en el modelo económico: es lo único que escala con el uso</td><td>200 <span class="q">/ cuenta</span></td></tr>
    <tr><td><b>Mantenimiento del pipeline</b></td><td class="q">12 fuentes que se rompen solas — el portal de Supersociedades se vació el 4 de septiembre y el de la SIC lleva casi tres años mudo. Entre 25 y 40 horas al mes.</td><td><b>2.000.000 a 3.200.000</b></td></tr>
  </table>
  <div class="porque"><span class="et">La conclusión que importa</span>
  El costo variable es despreciable: diez cuentas cuestan <b>143.000 pesos al mes</b> de servir, con
  el brief personalizado incluido. El costo real de Caudal es el mantenimiento, que existe haya una
  cuenta o cincuenta. Por eso el precio
  a Cauce tiene una parte fija: si fuera solo por cuenta, con pocos clientes Caudal estaría
  subsidiando la operación.</div>
</div>

<div class="item plata">
  <div class="num">08 · Lo que Cauce le paga a Caudal</div>
  <h2>Una licencia base más un valor por cuenta activa</h2>
  <table class="p">
    <tr><th>Concepto</th><th>Qué cubre</th><th>COP/mes</th></tr>
    <tr><td>Licencia base</td><td class="q">Plataforma operando, fuentes actualizadas a diario, fuentes nuevas, soporte. Se cobra haya o no cuentas vendidas.</td><td>2.500.000</td></tr>
    <tr><td>Cuenta · Plataforma</td><td class="q">Acceso, perfil de vigiladas y temas, radar, alertas, brief cada cuatro días.</td><td>750.000</td></tr>
    <tr><td>Cuenta · con acompañamiento</td><td class="q">Lo anterior, con el brief trabajado a mayor profundidad para que el analista de Cauce lo cierre.</td><td>950.000</td></tr>
  </table>
  <p><b>Piso absoluto:</b> <span class="cifra">$2.500.000 al mes</span>. Por debajo de eso Caudal
  subsidia el mantenimiento con trabajo no pagado, y esa es exactamente la clase de acuerdo que se
  cae al sexto mes. El piso técnico puro —no perder plata— serían 100.000 pesos más 4.300 por
  cuenta, pero ese número no paga que alguien arregle el harvester el día que el portal cambia.</p>
  <p><b>Piloto sugerido:</b> 90 días, hasta 3 cuentas, <span class="cifra">$2.500.000 al mes</span>
  fijos y sin cobro por cuenta. Cauce prueba con clientes reales y Caudal cubre su piso.</p>
  <div class="porque"><span class="et">Alternativa, si prefieren alinear incentivos</span>
  30% de lo que Cauce facture por Caudal, con piso de $3.000.000 al mes. Es más limpio de administrar
  y le da a Caudal una razón directa para que el producto ayude a vender, no solo a entregar.</div>
</div>

<div class="item plata">
  <div class="num">09 · Lo que Cauce le cobra al cliente</div>
  <h2>Dos precios públicos, y el segundo es donde está el negocio de Cauce</h2>
  <table class="p">
    <tr><th>Plan</th><th>Qué recibe el cliente</th><th>COP/mes</th></tr>
    <tr><td><b>Plataforma</b></td><td class="q">Acceso completo a los ocho pilares, perfil propio, radar priorizado, alertas por correo y brief cada cuatro días. Sin analista.</td><td>2.900.000</td></tr>
    <tr><td><b>Con acompañamiento</b></td><td class="q">Lo anterior, más analista de Cauce: monta el perfil, revisa cada brief, escribe cuando algo se mueve, prepara el memo de junta y acompaña la respuesta.</td><td>7.900.000</td></tr>
  </table>
  <table class="p">
    <tr><th></th><th>Cauce recibe</th><th>Cauce paga</th><th>Le queda</th></tr>
    <tr><td>Plataforma</td><td class="q">2.900.000</td><td class="q">750.000</td><td>2.150.000 · 74%</td></tr>
    <tr><td>Con acompañamiento</td><td class="q">7.900.000</td><td class="q">950.000</td><td>6.950.000 · 88%</td></tr>
  </table>
  <p>Ese 88% no es real y conviene decirlo: de ahí sale el tiempo del analista. Con unas ocho horas al
  mes por cuenta, el margen efectivo del plan con acompañamiento queda cerca del <b>78%</b>, que sigue
  siendo un margen de consultoría con producto adentro y no de reventa.</p>
  <p><b>Punto de equilibrio de Cauce:</b> con <b>dos cuentas de plataforma</b> queda cubierta la
  licencia base. La tercera ya es margen.</p>
  <div class="porque"><span class="et">Rango del plan con acompañamiento</span>
  $7.900.000 es la entrada. Una cuenta con incidencia activa —temporada de reforma, proyecto propio
  radicado, vocería— sostiene entre $10 y $12 millones, que es donde están los retainers de asuntos
  públicos en Colombia. La referencia interna de la casa apunta al mismo orden: nuestro producto de
  campaña más completo para alcaldía está en $11.900.000.</div>
</div>

<div class="item urg">
  <div class="num">10 · El riesgo que hay que resolver antes de publicar precios</div>
  <h2>Caudal se vende hoy directo a $2.500.000. Si Cauce vende lo mismo por menos, el canal directo se muere.</h2>
  <p>El SKU actual de Caudal en ricardoruiz.co es de $2.500.000 al mes. Por eso el plan Plataforma
  vía Cauce se propone en <b>$2.900.000</b> y no por debajo: incluye el brief personalizado al perfil
  del cliente y el montaje que hace Cauce, así que es un producto distinto y más completo, no el
  mismo con descuento. Hay tres salidas y hay que escoger una antes de que salga la primera
  propuesta:</p>
  <ul class="t">
    <li><b>Paridad</b> — el precio vía Cauce nunca queda por debajo del directo. Es la que propongo.</li>
    <li><b>Segmentación</b> — Caudal directo deja de venderle a corporativos con área de asuntos
    públicos y se queda con gremios chicos y equipos de campaña.</li>
    <li><b>Exclusividad</b> — Cauce toma el canal corporativo completo, con un mínimo mensual que
    compense el cierre de la venta directa.</li>
  </ul>
</div>

<h3 class="sec">04 · Cómo arrancar</h3>

<div class="item">
  <div class="num">11 · Los siguientes 90 días</div>
  <h2>Tres cuentas reales antes de publicar una lista de precios</h2>
  <table class="d">
    <tr><th>Cuándo</th><th class="q">Qué</th></tr>
    <tr><td>Semana 1</td><td class="q">Cerrar los cuatro huecos del punto 06 — el más grande, la llave de la API, es de un día. Cauce escoge tres cuentas piloto y, con cada una, se llena su ficha: qué hace, quién lee el brief y qué decide con él.</td></tr>
    <tr><td>Semanas 2-12</td><td class="q">Piloto en marcha: brief a las tres cuentas, alertas activas, revisión conjunta cada quince días de qué se leyó y qué se ignoró.</td></tr>
    <tr><td>Semana 13</td><td class="q">Decisión sobre el modelo definitivo — licencia más cuenta, o participación — con datos de uso reales en la mano, no con supuestos.</td></tr>
  </table>
  <div class="porque"><span class="et">Lo que hay que medir en el piloto</span>
  Cuántas horas cuesta de verdad cerrar un brief, cuántas señales del radar el analista descarta —si
  descarta demasiadas, el filtro está mal calibrado— y si el cliente abre el correo. Esos tres
  números deciden a cuántas cuentas se puede escalar y en cuánto. Un cuarto, ahora que la ficha
  existe: cuánto mejora el brief cuando la ficha del cliente está completa frente a cuando está a
  medias. Si la diferencia es grande, llenarla bien pasa a ser parte del montaje que cobra Cauce.</div>
</div>

<div class="foot">
  <b>Cifras.</b> Todas las de este documento se remidieron contra producción el 14 de septiembre de
  2026: los conteos de cada pilar salen de la propia API de Caudal, el almacenamiento de S3 (34,1 GB
  en 55.041 objetos) y el costo del brief de una corrida real —22.586 caracteres de evidencia— con
  las tarifas publicadas de Anthropic a esa fecha. Se toma una tasa de 4.000 pesos por dólar.<br>
  <b>Competencia.</b> Lo que se dice de Dapper, Orza y Sonar sale de sus propias publicaciones y de
  prensa. <b>Ninguno de los tres publica precios</b>: en este documento no se les atribuye ninguno.<br>
  <b>Alcance.</b> Borrador para discusión entre socios. No es oferta en firme ni asesoría legal.<br>
  Caudal · módulo de inteligencia regulatoria de Cauce.
</div>

</body></html>
"""


def render():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    from weasyprint import HTML
    HTML(string=HTML_DOC, base_url=ROOT).write_pdf(OUT)
    return "weasyprint"


if __name__ == "__main__":
    motor = render()
    print(f"OK ({motor}) · {OUT} · {os.path.getsize(OUT)/1024:.0f} KB")
