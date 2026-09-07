#!/usr/bin/env python3
"""
Brief de asuntos públicos · Cauce — semana del 7 de septiembre de 2026.
Ventana: lunes 31 de agosto → domingo 6 de septiembre (más la prensa del lunes 7
temprano). PURAMENTE NACIONAL, a diferencia del de Binance.

A QUIÉN LE HABLA. A los socios de Cauce (Diego Baquero · Pablo Cárdenas), como
su analista: no a un cliente. Cauce trabaja cuatro áreas —navegación política y
regulatoria, inception electoral, negociación y gestión de acuerdos, landing
LATAM— y publica un Horóscopo semanal (lectura presidencial · política ·
constelación ministerial). Este brief es el INSUMO verificado de esa lectura:
cada ítem dice qué pasó, por qué le importa a la práctica de Cauce (y a qué tipo
de cliente) y qué hacer con eso. El editorial lo ponen ellos.

Mismo chasis visual del brief de Binance (build_brief_binance.py: CSS, logo,
papel). Salida en caudalxcauce/Cauce/ (gitignorada: material de cliente).
"""
import os, sys, subprocess, shutil
sys.path.insert(0, os.path.dirname(__file__))
import build_brief_binance as base

ROOT = base.ROOT
OUT = os.path.join(ROOT, "caudalxcauce", "Cauce", "Brief-Cauce-2026-09-07.pdf")

TOP = f"""
<div class="top">
  <img src="file://{base.LOGO}" alt="Caudal × Cauce">
  <div class="meta">Brief de asuntos públicos · Cauce · Colombia<br>Semana del 7 de septiembre de 2026</div>
</div>
"""

HTML_DOC = f"""
<html><head><meta charset="utf-8"><style>{base.CSS}
.item.neg {{ border-left-color:#8a6d1c; background:#fbf9f2; border-color:#eadfbf; }}
.item.neg .porque .et {{ color:#8a6d1c; }}
.area {{ font-size:7.2pt; letter-spacing:1.1px; text-transform:uppercase; color:#8a6d1c; font-weight:700; }}
table.ag td:first-child {{ white-space:nowrap; color:#0b0d11; font-weight:700; width:22%; }}
</style></head><body>
{TOP}

<div class="hero">
  <h1>El presupuesto tropezó, la consulta previa se abrió y <span class="hl">la paz total se cerró por resolución</span>.</h1>
  <p class="lead">Barrido del 31 de agosto al 6 de septiembre sobre el Congreso, el Ejecutivo, los
  reguladores, las cortes, la consulta pública de normas y la conversación pública. Nueve temas,
  ordenados por lo que exige atención primero, y la agenda de la semana que entra.</p>
  <div class="window">Ventana 31 de agosto – 6 de septiembre de 2026 · Colombia</div>
</div>

<div class="item resumen">
  <div class="num">Lectura de la semana</div>
  <h2>El Congreso le mostró los dientes al gabinete antes de la primera votación</h2>
  <p>El primer debate del presupuesto de 2027 se levantó el 2 de septiembre porque no llegó ninguno
  de los cuatro ministros citados, y las comisiones económicas condicionaron el trámite a la
  asistencia obligatoria del gabinete. Es la primera prueba de gobernabilidad del gobierno en el
  Legislativo y arrancó con un desplante, no con una derrota: el presupuesto vuelve al orden del
  día el 9 y el monto tiene que estar aprobado el 15.</p>
  <p>Fuera del Congreso, dos frentes de la práctica de negociación cambiaron de reglas la misma
  semana: el Ministerio del Interior anunció una reforma administrativa a la consulta previa con
  el caso Sirius como bandera, y el Consejo de Estado fijó que quien bloquea y causa daño
  demostrable responde con su patrimonio. Y en el Ejecutivo, el primer cambio de gabinete a los
  27 días, más las resoluciones que cerraron formalmente las mesas de la paz total.</p>
  <div class="porque"><span class="et">Si solo hay tiempo para una cosa</span>
  La consulta previa. Se está moviendo por tres vías a la vez —reforma administrativa en
  Interior, proyecto de ley radicado el 1 de septiembre y un caso empresarial de alto perfil— y
  el encuadre público («derecho» contra «extorsión») se está fijando esta semana. Es el momento
  de definir la posición de cada cliente con proyectos en consulta.</div>
</div>

<div class="item urg">
  <div class="num">01 · Fiscal · <span class="area">navegación política y regulatoria</span></div>
  <h2>El primer debate del presupuesto se levantó por inasistencia del gabinete, y el reloj legal sigue corriendo</h2>
  <p>El proyecto de presupuesto de 2027, por <b>$634,9 billones</b>, llegó a las comisiones económicas
  conjuntas el 2 de septiembre y la sesión se levantó: no asistieron el ministro de Hacienda, Miguel
  Gómez, el director del DNP, Julián Buitrago, el ministro de Vivienda, Jaime Beltrán, ni la ministra
  de Educación, Viviane Morales. El presidente de la comisión, Alexander Bermúdez (Liberal), la
  cerró con un «se levanta la sesión», y el Congreso condicionó el trámite a la asistencia
  obligatoria de los ministros. Está agendado de nuevo para el <b>9 de septiembre</b>. Plazos: el
  monto antes del <b>15 de septiembre</b>, el primer debate antes del <b>25</b>, las plenarias
  antes del <b>20 de octubre</b>. Coordina la ponencia Carlos Meisel (Centro Democrático) con siete
  ponentes de seis bancadas, entre ellos David Racero y Deisy Osorio (Pacto), Sara Castellanos
  (Salvación Nacional) y Andrea Padilla (Verde).</p>
  <p>Del lado del Ejecutivo, el Consejo de Ministros aprobó el 29 de agosto un recorte de
  <b>$21,9 billones</b> al gasto de 2026, que se hará por decreto, con la liquidación del Ministerio
  de la Igualdad y la eliminación de cinco viceministerios como primera partida. La prensa de la
  semana lee el presupuesto como «hueco fiscal» por sincerar; JPMorgan proyecta un déficit de 8,2 %
  del PIB en 2026 con la legislación vigente.</p>
  <div class="porque"><span class="et">Por qué le importa a Cauce</span>
  Es la primera medición real de la relación del gobierno con el Congreso, y la señal es de un
  Legislativo que cobra caro la ausencia. Para cualquier cliente con rubro en el presupuesto
  —o con una exención tributaria que la reforma pueda tocar— las dos fechas que mandan son el 15
  y el 25; después del 25 solo queda la plenaria, donde los cambios son de margen.</div>
  <div class="porque"><span class="et">Qué hacer con esto</span>
  Alerta estratégica a clientes con rubros o exenciones en juego, con las dos fechas. Y para el
  Horóscopo: la lectura no es «el presupuesto se cayó» sino «el Congreso fijó el precio de la
  gobernabilidad antes de votar».</div>
</div>

<div class="item neg urg">
  <div class="num">02 · Consulta previa · <span class="area">negociación y gestión de acuerdos</span></div>
  <h2>Interior anunció una reforma administrativa a la consulta previa, con Sirius como caso bandera y un proyecto de ley recién radicado</h2>
  <p>El ministro del Interior, Rodrigo Lara, anunció el 6 de septiembre una reforma a la Dirección
  de Consulta Previa: separar la consulta de la licencia ambiental para que avancen en paralelo,
  flexibilizarla en zonas de desastre para la reconstrucción, y «modernizar y sistematizar» la
  dirección, con Hilda María Pardo y Ángela María Ortiz al frente. Lo dijo con una frase que va a
  quedar: «la consulta previa, que es importante y defendemos, está siendo usada por inescrupulosos
  para extorsionar». El detonante es <b>Sirius</b>: Ecopetrol y Petrobras denunciaron que la comunidad
  de Taganga pide un pago veinte veces mayor que el de las otras 116 comunidades consultadas, y la
  ACP (Frank Pearl) pidió «desarticular grupos extorsivos que se tomaron algunas consultas». La
  comunidad respondió en El Tiempo. En La Guajira, el pueblo Wayuu reclama por la transición
  energética.</p>
  <p>En el Congreso entró el 1 de septiembre el <b>218/2026 Senado</b> (Juan Espinal y Gonzalo
  Baute, Centro Democrático), «proceso administrativo de la consulta previa». No es el primer
  intento: el registro de Caudal tiene 110 proyectos que han tocado el tema; el que reglamenta el
  artículo 246 de la Constitución (050/2025 Senado – 496/2025 Cámara) sigue en trámite, y el de
  Alfredo Deluque de 2024 se archivó. El Colombiano abrió el debate el 7 con la cifra: más de
  13.000 consultas en 15 años.</p>
  <div class="porque"><span class="et">Por qué le importa a Cauce</span>
  Es el núcleo del área de negociación, y el marco se está moviendo por tres vías a la vez:
  administrativa (Interior), legislativa (218/26 y el 050/25) y de opinión (el encuadre
  «extorsión»). Cada cliente con un proyecto en consulta va a tener que decidir esta semana si se
  sube al relato de Sirius o se distancia de él. Y el relato de «consulta como extorsión» tiene un
  costo: las comunidades que negocian de buena fe quedan bajo la misma sombra.</div>
  <div class="porque"><span class="et">Qué hacer con esto</span>
  Matriz de riesgo normativo para clientes con consultas abiertas: qué cambia si la consulta se
  separa de la licencia y qué no cambia (el derecho sigue siendo fundamental). Mapa de actores de
  la reforma: Lara, Pardo y Ortiz en Interior; Espinal y Baute en el Senado; ACP y Ecopetrol del
  lado empresarial; las organizaciones étnicas todavía sin vocería unificada.</div>
</div>

<div class="item neg">
  <div class="num">03 · Protesta y bloqueos · <span class="area">negociación y gestión de acuerdos</span></div>
  <h2>El Consejo de Estado fijó que quien bloquea y causa daño responde con su patrimonio</h2>
  <p>En un fallo conocido el 2 de septiembre, el Consejo de Estado condenó a la Corporación de Juntas
  de Acción Comunal San Isidro de Chichimene y a su entonces representante legal a indemnizar a
  Ecopetrol por los bloqueos y el «sabotaje» a la estación de Chichimene (Acacías, Meta) entre el 31
  de julio y el 15 de agosto de 2017. La tesis: la protesta pierde su protección constitucional
  cuando deja de ser pacífica y causa un daño demostrable a terceros; «la protesta siempre será
  válida, pero debe tener límites». Enrique Peñalosa lo celebró; la comunidad de Chichimene pidió
  diálogo. En paralelo, la «ley anticapuchos» (hasta ocho años de cárcel por actos vandálicos con
  el rostro cubierto) avanzó en el Congreso, y el dato de fondo: 309 bloqueos en las vías entre
  enero y mayo de 2026, con pérdidas de $1,3 billones.</p>
  <div class="porque"><span class="et">Por qué le importa a Cauce</span>
  Cambia el cálculo de las dos sillas de la mesa. Quien bloquea ahora arriesga su patrimonio y el
  de su organización; quien es bloqueado tiene una vía de reparación que antes era teórica. El
  precedente se va a citar en Transmilenio, en los paros docentes y en cualquier vía nacional.</div>
  <div class="porque"><span class="et">Qué hacer con esto</span>
  Incorporar el fallo a los scripts y ensayos de reuniones: es un argumento nuevo en la mesa, y
  usarlo mal (como amenaza) rompe la zona de acuerdo. Para clientes con operaciones expuestas:
  documentar el daño desde el primer día del bloqueo, que es lo que el fallo exige probar.</div>
</div>

<div class="item">
  <div class="num">04 · Ejecutivo · <span class="area">lectura presidencial</span></div>
  <h2>Primer cambio de gabinete a los 27 días, y las mesas de la paz total cerradas por resolución</h2>
  <p>Viviane Morales renunció a Educación por «una situación familiar inesperada» (carta del 31 de
  agosto); la reemplaza <b>Ilva Myriam Hoyos</b>, que asume el 7 de septiembre: abogada del Rosario,
  doctora en Derecho de Navarra, exprocuradora delegada para la infancia en la Procuraduría de
  Ordóñez y exdecana de Derecho de La Sabana. Infobae la presenta como «polémica». El 28 de
  agosto, con nueve resoluciones ejecutivas (342 a 350), el Gobierno dio por terminadas las mesas
  con el Estado Mayor de los Bloques (Gentil Duarte, Jorge Suárez Briceño, Raúl Reyes), con la
  Coordinadora Nacional Ejército Bolivariano y el espacio con las Autodefensas Conquistadoras de la
  Sierra, y revocó a todos sus representantes: el cierre formal de la paz total. Esta semana
  siguió la secuencia de seguridad: Bloque de Búsqueda Anticorrupción «caiga quien caiga» con
  cooperación del FBI, estrategia de «mando, drones y combate», la UNP bajo la lupa por 37
  protegidos asesinados en el gobierno anterior. Y el 7, la visita de Marco Rubio, leída como
  nueva era de la relación con Estados Unidos.</p>
  <p>En la constelación institucional cambiaron dos caras que importan a los clientes regulados:
  Julia Eva Pretelt asumió Supersociedades el 1 de septiembre, con prioridad declarada en empresas
  en crisis, y la directora de la UIAF, Martha Luz Reyes, enfrenta una queja disciplinaria ante la
  Procuraduría por el ingreso de un civil a zonas restringidas de la entidad.</p>
  <div class="porque"><span class="et">Por qué le importa a Cauce</span>
  El gabinete empezó a moverse antes del mes, y la agenda de seguridad desplazó por completo a la
  de paz como marco del gobierno. Para la lectura presidencial del Horóscopo, el dato duro es que la
  paz total no se «desmontó» en un discurso: se cerró en nueve actos administrativos con número.</div>
  <div class="porque"><span class="et">Qué hacer con esto</span>
  Actualizar la constelación ministerial (Educación) y sumar a Supersociedades y la UIAF al mapa de
  interlocutores: los dos supervisan a clientes del sector real y financiero.</div>
</div>

<div class="item">
  <div class="num">05 · Congreso · <span class="area">navegación política y regulatoria</span></div>
  <h2>Trece proyectos entraron al Senado en dos días; tres tocan a las empresas directamente</h2>
  <p>Entre el 1 y el 2 de septiembre se radicaron trece proyectos en el Senado. Los que tocan la
  práctica: <b>220/2026</b>, simplificación de trámites para las empresas (María Clara Posada);
  <b>227/2026</b>, modifica el mecanismo de reajuste anual de las pensiones (Luis Eduardo Díaz
  Mateus); <b>222/2026</b>, amplía la edad de retiro forzoso (Antonio Correa); <b>226/2026</b>,
  racionalización y distancia mínima de los peajes (Luis Carlos Rúa); <b>219/2026</b>, reforma a
  la Ley 1341 de TIC (María Lucía Villalba); <b>217/2026</b>, beneficio de alimentación al
  trabajador (Nadia Blel); y <b>225/2026</b>, Universidad Nacional del Catatumbo (Aída Avella). El
  Senado aprobó la ley de salud mental para médicos y la ley nuclear avanzó. El Tiempo publicó
  el 4 que en ocho años solo se aprobó uno de cada siete proyectos; el registro de Caudal, sobre
  13.787 proyectos con fecha desde 1990, da 2.467 leyes (17,9 %) y el dato que más importa:
  el 64 % muere antes del primer debate.</p>
  <div class="porque"><span class="et">Por qué le importa a Cauce</span>
  El 220 es el proyecto que un gremio quiere y el 227 y el 222 los que un fondo de pensiones o
  una entidad pública deben leer hoy. Y la cifra de mortalidad es el argumento para el cliente
  que se asusta con un radicado: la mayoría no llega al primer debate, y lo que decide es la
  agenda de la comisión, no la votación.</div>
  <div class="porque"><span class="et">Qué hacer con esto</span>
  Alerta por sector: trámites (220), pensiones (227, 222), transporte (226), TIC (219). Los
  cuatro están en Caudal con texto radicado.</div>
</div>

<div class="item">
  <div class="num">06 · Regulación y control · <span class="area">navegación política y regulatoria</span></div>
  <h2>La Superfinanciera cobró dos veces en una semana, y la Contraloría puso cifra a la deuda de las EPS</h2>
  <p>La Superintendencia Financiera ordenó a Acción Fiduciaria devolver más de $950 millones a un
  inversionista del BD Bacatá (2 de septiembre; la fiduciaria apelará) y frenó un esquema que captó
  $9.489 millones prometiendo 28 % anual. La Contraloría alertó que la deuda de las EPS con
  hospitales y proveedores llegó a $58 billones. El Ministerio de la Igualdad, en liquidación,
  revocó más de 60 contratos. Y el Decreto 1040 de 2026, que reglamenta la protección frente al
  acoso y la discriminación laboral bajo la Ley 2466, entró esta semana a la conversación de las
  firmas laborales.</p>
  <div class="porque"><span class="et">Por qué le importa a Cauce</span>
  Ninguno cambia una regla general, pero los dos de la Superfinanciera fijan tono: el supervisor
  del nuevo gobierno actúa sobre casos con nombre propio y los comunica. Para clientes del sector
  fiduciario e inmobiliario, BD Bacatá es el precedente a seguir.</div>
</div>

<div class="item ok">
  <div class="num">07 · Consulta pública de normas</div>
  <h2>Diecinueve consultas abiertas; ninguna de peso nacional, y la mitad cierra esta semana</h2>
  <p>De las 19 consultas de proyectos de norma abiertas hoy, 13 cierran en los próximos siete días.
  Las que pueden tocar a un cliente: la de la <b>CRA</b> sobre el régimen tarifario de agua y
  saneamiento (cierra el 10), la de la <b>Aeronáutica Civil</b> que modifica la Resolución 3104 de
  2015 (cierra el 11), la del <b>Ministerio de Agricultura</b> que deroga cinco resoluciones de 2025
  y 2026 (cierra el 16) y la de la <b>Gobernación del Valle</b> sobre sustitución gradual y
  eliminación progresiva (cierra el 16). Ninguna viene de Hacienda, Interior, Minas ni de las
  superintendencias.</p>
  <div class="porque"><span class="et">Por qué le importa a Cauce</span>
  El silencio es el dato: la reforma a la consulta previa y el recorte de gasto van por decreto y
  directiva, no por consulta pública. Cuando alguno de los dos salga al SUCOP, el plazo se cuenta
  en días.</div>
</div>

<div class="item">
  <div class="num">08 · Conversación pública · <span class="area">horóscopo político y regulatorio</span></div>
  <h2>Presupuesto, consulta previa y la reorganización de la izquierda dominan la semana</h2>
  <p>Los temas del momento que detecta Caudal cruzando prensa política, radicados y consultas, en
  orden: <b>presupuesto 2027</b> (65 titulares en siete días), <b>reforma pensional</b>, <b>consulta
  previa</b>, <b>sistema general de regalías</b>, <b>plan de energía</b>, <b>distancia entre
  peajes</b> y <b>edad de retiro forzoso</b>. En la oposición, El Espectador describe una izquierda
  que se reorganiza tras un mes fuera del poder, la Alianza Verde se declaró en independencia
  («el petrouribismo existe», dijo Mauricio Toro) y Petro habla de una «Matrix de la falsedad» y de
  doble nacionalidad con Venezuela. En política exterior, Razón Pública resume la línea del
  gobierno como «alineamiento y aislamiento».</p>
  <div class="porque"><span class="et">Qué hacer con esto</span>
  Los siete temas son la agenda del Horóscopo de esta semana si el criterio es «de qué está
  hablando el país». Los tres primeros ya tienen ítem propio arriba.</div>
</div>

<div class="item">
  <div class="num">09 · Termómetro 2027 · <span class="area">inception electoral</span></div>
  <h2>Las regionales todavía no existen en la prensa nacional, pero en las ciudades ya hay listas de precandidatos</h2>
  <p>Ibagué ya cuenta 16 precandidatos a la Alcaldía (Ecos del Combeima, 6 de septiembre). En el
  ámbito nacional, las señales son de reacomodo, no de candidaturas: la izquierda se reorganiza
  como oposición y los verdes se separan del gobierno. No hay todavía un movimiento de peso en
  Bogotá o Medellín que la prensa registre como tal.</p>
  <div class="porque"><span class="et">Qué hacer con esto</span>
  Es el momento de armar el tablero por ciudad antes de que exista la conversación: Caudal ya
  tiene el histórico electoral por puesto de las cuatro últimas locales, y la cartografía de
  arquetipos de Medellín.</div>
</div>

<div class="hero" style="page-break-inside:auto">
<h3 class="sec" style="margin-top:0">Agenda de la semana que entra</h3>
<table class="ag">
  <tr><td>Lunes 7</td><td class="q">Ilva Myriam Hoyos asume el Ministerio de Educación. Consulta del DNP sobre el Decreto 1082 cierra hoy.</td></tr>
  <tr><td>Martes 8</td><td class="q">Plenaria de Cámara con seis proyectos en el orden del día, entre ellos el 534/2026 y el 476/2025.</td></tr>
  <tr><td>Miércoles 9</td><td class="q">Presupuesto 2027 de nuevo en las comisiones económicas conjuntas. Cierra la consulta de la SIC.</td></tr>
  <tr><td>Jueves 10 – viernes 11</td><td class="q">Cierran las consultas de la CRA (10) y de la Aeronáutica Civil (11).</td></tr>
  <tr><td>Martes 15</td><td class="q">Plazo legal para aprobar el monto del presupuesto.</td></tr>
  <tr><td>Miércoles 16</td><td class="q">Cierran las consultas del Ministerio de Agricultura y de la Gobernación del Valle.</td></tr>
  <tr><td>Viernes 25</td><td class="q">Plazo legal para el primer debate del presupuesto.</td></tr>
</table>

<h3 class="sec">Qué no se movió — verificado, no asumido</h3>
<table>
  <tr><th style="width:26%">Fuente</th><th>En la ventana</th></tr>
  <tr><td>Corte Constitucional</td><td class="q">Sin providencias nuevas en el registro desde la T-246 del 12 de agosto.</td></tr>
  <tr><td>Ejecutivo · normativa</td><td class="q">Cincuenta y un decretos desde el 20 de agosto y casi todos son nombramientos y encargos; el registro de Presidencia va hasta el 28 de agosto.</td></tr>
  <tr><td>Superintendencias · actos</td><td class="q">Tres resoluciones nuevas en el registro, las tres de la DIAN y sobre su propia contratación directa.</td></tr>
</table>

<div class="foot">
  <b>Fuentes.</b> Registro de proyectos de ley del Senado y la Cámara y órdenes del día de sus
  comisiones; normativa de Presidencia; consulta pública de proyectos de norma del DNP (SUCOP);
  registro regulatorio de 17 fuentes; providencias de la Corte Constitucional; prensa nacional y
  regional (El Tiempo, El Espectador, Semana, El Colombiano, El País, Infobae, Portafolio, Valora
  Analitik, Razón Pública, Noticias RCN, entre otros). Cada afirmación es verificable contra el
  acto o la nota que la respalda.<br>
  <b>Ventana.</b> 31 de agosto al 6 de septiembre de 2026, más la prensa del 7 en la mañana.<br>
  <b>Alcance.</b> Insumo de monitoreo para el equipo de Cauce; no constituye asesoría legal.<br>
  Caudal · módulo de inteligencia regulatoria de Cauce.
</div>
</div>

</body></html>
"""


def render():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    try:
        from weasyprint import HTML
        HTML(string=HTML_DOC, base_url=ROOT).write_pdf(OUT)
        return "weasyprint"
    except ImportError:
        pass
    tmp = OUT[:-4] + ".html"
    open(tmp, "w", encoding="utf-8").write(HTML_DOC)
    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--print-to-pdf=" + OUT, "file://" + tmp], check=True, capture_output=True, timeout=120)
    os.remove(tmp)
    return "chrome"


if __name__ == "__main__":
    motor = render()
    print(f"OK ({motor}) · {OUT} · {os.path.getsize(OUT)/1024:.0f} KB")
