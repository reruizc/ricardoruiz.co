#!/usr/bin/env python3
"""
Brief regulatorio · Binance — Caudal x Cauce · semana del 7 de septiembre de 2026.
Ventana: lunes 31 de agosto → domingo 6 de septiembre de 2026.

Colombia es el eje y va primero; la lectura regional (los países de la matriz de
priorización LATAM: Venezuela · Perú · Bolivia · El Salvador · República
Dominicana, más Guatemala y México como señales que conviene sumar) va después.
Misma VOZ del brief del 10 de agosto: le habla A BINANCE, «pasó esto → le pega
por esto → esto es lo que hay que mirar». NADA DE COCINA INTERNA: cero
referencias a su matriz; el contraste con la matriz se usa para decidir qué
entra y queda en las notas para Ricardo, no en el documento.

Reusa el chasis visual (CSS, logo, papel) de build_brief_binance.py. Render:
WeasyPrint si está instalado; si no, Chrome headless (print-to-pdf), que en
esta Mac sí está. Con Chrome el encabezado fijo se repite igual por página.

Salida: caudalxcauce/Binance/Brief-Binance-2026-09-07.pdf (carpeta gitignorada:
material de cliente, el repo es público) + el .html intermedio al lado.
"""
import os, sys, subprocess, shutil
sys.path.insert(0, os.path.dirname(__file__))
import build_brief_binance as base   # CSS · LOGO · ROOT (no ejecuta nada al importar)

ROOT = base.ROOT
OUT = os.path.join(ROOT, "caudalxcauce", "Binance", "Brief-Binance-2026-09-07.pdf")
HTML_TMP = OUT[:-4] + ".html"

TOP = f"""
<div class="top">
  <img src="file://{base.LOGO}" alt="Caudal × Cauce">
  <div class="meta">Brief regulatorio · Binance<br>Semana del 7 de septiembre de 2026</div>
</div>
"""

HTML_DOC = f"""
<html><head><meta charset="utf-8"><style>{base.CSS}
.item.lat {{ border-left-color:#8a6d1c; background:#fbf9f2; border-color:#eadfbf; }}
.item.lat .porque .et {{ color:#8a6d1c; }}
.pais {{ font-size:7.2pt; letter-spacing:1.1px; text-transform:uppercase; color:#8a6d1c; font-weight:700; }}
@media print {{ body {{ -webkit-print-color-adjust:exact; print-color-adjust:exact; }} }}
</style></head><body>
{TOP}

<div class="hero">
  <h1>Cambió el supervisor, no la regla: <span class="hl">lo que se movió para Binance</span> en Colombia y la región.</h1>
  <p class="lead">Barrido del 31 de agosto al 6 de septiembre sobre el Congreso, las superintendencias,
  el Ejecutivo, la consulta pública de normas y la prensa, más los seis mercados de la región que
  siguen en vigilancia. Cinco temas de Colombia y cinco señales regionales, ordenados por lo que
  exige atención primero.</p>
  <div class="window">Ventana 31 de agosto – 6 de septiembre de 2026 · Colombia y LATAM</div>
</div>

<div class="item resumen">
  <div class="num">Resumen ejecutivo</div>
  <h2>Los dos interlocutores de Binance en Colombia cambiaron de cara la misma semana</h2>
  <p>El 1 de septiembre se posesionó una nueva superintendente de Sociedades, el supervisor de
  prevención de lavado de un exchange en Colombia, con una prioridad declarada que no es esa:
  acompañar empresas en crisis. Y la UIAF, la entidad a la que Binance reporta operación por
  operación, entró en una crisis interna con queja disciplinaria contra su directora. Ninguna
  regla cambió; cambió quién la aplica, y ese es el momento en que se fijan las prioridades de
  un supervisor.</p>
  <p>Lo que sí se mueve en firme es el frente fiscal: el presupuesto de 2027 llega a su primer
  debate el 9 de septiembre y el Gobierno anunció para finales de mes una «ley fiscal» que promete
  no subir impuestos; el tratamiento de los criptoactivos va a definirse ahí. No hay ninguna
  norma sobre criptoactivos expedida ni en consulta esta semana, en Colombia. En la región sí:
  Guatemala pone a los exchanges bajo control antilavado desde el 17 de septiembre.</p>
  <div class="porque"><span class="et">Si solo hay tiempo para una cosa</span>
  Agendar en las próximas dos semanas una presentación institucional ante la nueva
  superintendente de Sociedades. La regla de lavado que le aplica a Binance se reescribió el 2 de
  julio; quien la va a interpretar llegó el 1 de septiembre y todavía no ha fijado su lectura.</div>
</div>

<div class="item urg">
  <div class="num">01 · Supervisor</div>
  <h2>Supersociedades tiene nueva superintendente desde el 1 de septiembre, y su prioridad declarada no es el lavado de activos</h2>
  <p><b>Julia Eva Pretelt Vargas</b> se posesionó el 1 de septiembre (Decreto 1282 del 25 de agosto
  de 2026), abogada con 35 años en resolución de controversias y gobierno corporativo. Su apuesta
  pública: acompañar a las empresas en dificultades económicas y a las que buscan reorganizarse.
  En la misma semana la prensa contable recordó a las vigiladas la <b>contribución 2026</b>
  (Resolución 100-027492): 0,1212 por cada mil pesos de activos totales al 31 de diciembre de 2025, pagadera
  en los <b>20 días calendario</b> siguientes a la cuenta de cobro.</p>
  <div class="porque"><span class="et">Por qué le importa a Binance</span>
  Supersociedades, no la Superfinanciera, es el supervisor de lavado de activos de un exchange
  en Colombia, y el 2 de julio reescribió íntegramente la Circular Básica Jurídica donde vive el
  SAGRILAFT. La circular ya está; la lectura que le dé la nueva administración, no. Un despacho
  concentrado en insolvencia y reorganización tiende a mirar el cumplimiento LA/FT como trámite
  de la delegatura, y esa es la ventana para que Binance se presente como vigilada que reporta y
  cumple, antes de que la primera interacción sea un requerimiento.</div>
  <div class="porque"><span class="et">Qué conviene revisar</span>
  Solicitar reunión de presentación con el despacho y con la delegatura de asuntos económicos y
  societarios. Confirmar en qué categoría figura la filial colombiana (vigilada o controlada) y si
  la cuenta de cobro de la contribución 2026 ya llegó: el plazo corre desde su expedición, no desde
  su lectura.</div>
</div>

<div class="item urg">
  <div class="num">02 · Cumplimiento · UIAF</div>
  <h2>La UIAF entró en crisis interna: queja disciplinaria contra su directora por el manejo de información reservada</h2>
  <p>Entre el 2 y el 6 de septiembre cinco medios reportaron una queja ante la Procuraduría contra
  la directora de la Unidad de Información y Análisis Financiero, <b>Martha Luz Reyes</b>, de
  reciente nombramiento. El hecho: un civil sin vínculo con la entidad recibió acceso biométrico a
  zonas restringidas donde se procesa inteligencia financiera, con autorización de un asesor del
  despacho. Hubo sala de crisis e inspección, y el funcionario que reportó el ingreso fue
  retirado.</p>
  <div class="porque"><span class="et">Por qué le importa a Binance</span>
  La UIAF es la contraparte de la obligación más exigente que Binance tiene en Colombia: el
  reporte por operación, con número de wallet, hash y contraparte, bajo las Resoluciones 314 de
  2021 y 84 de 2022. Lo que está en cuestión es la reserva de la información que los reportantes
  entregan y la continuidad de los interlocutores técnicos. Una entidad en crisis interna no
  suspende la obligación de reportar, pero sí vuelve más probable el cambio de dirección y de
  criterios en las próximas semanas.</div>
  <div class="porque"><span class="et">Qué conviene revisar</span>
  Confirmar que los reportes del calendario 2026 siguen entrando con acuse, y quién es hoy el
  interlocutor técnico del sector de activos virtuales. Dejar constancia escrita de cada envío
  mientras dure la turbulencia.</div>
</div>

<div class="item">
  <div class="num">03 · Fiscal</div>
  <h2>El presupuesto de 2027 llega a primer debate el 9 de septiembre, y el Gobierno anuncia para fin de mes una «ley fiscal» que insiste en no llamar reforma tributaria</h2>
  <p>El proyecto de presupuesto (152/2026 Cámara – 111/2026 Senado, radicado el 29 de julio) ha
  estado diez veces en el orden del día desde el 11 de agosto y aparece agendado para el
  <b>9 de septiembre</b> en las comisiones económicas. La prensa de la semana lo lee como un
  «hueco fiscal» por sincerar, y JPMorgan advierte que, tras la tesis T.I.G.R.E. con la que leyó
  al nuevo gobierno, «lo difícil empieza ahora»: proyecta un déficit total de 8,2 % del PIB en
  2026 con la legislación vigente.</p>
  <p>El ministro de Hacienda, Miguel Gómez, confirmó que radicará a finales de septiembre un
  proyecto de ajuste que el Gobierno llama <b>«ley fiscal» o «ley de rescate»</b>, y fue categórico
  en que no sube impuestos: «una reforma tributaria es una reforma que aumenta impuestos; la ley
  fiscal busca disminuir el gasto». Semana tituló el 7 de septiembre «la ley fiscal que nadie
  quiere llamar reforma tributaria», y cuatro expertos consultados coinciden en que un proyecto
  fiscal tiene que tocar tributos aunque no suba tarifas. La reforma tributaria radicada por el
  gobierno anterior (004/2026 Cámara, del 20 de julio) sigue formalmente en trámite en la Comisión
  Tercera, en la misma fila donde esperan dos proyectos que tocan el dinero en movimiento: el
  <b>259/2026C</b>, que elimina el gravamen a los movimientos financieros sobre traslados entre
  productos de un mismo titular, y el <b>262/2026C</b>, que amplía el universo de entidades
  autorizadas para recaudar tributos.</p>
  <div class="porque"><span class="et">Por qué le importa a Binance</span>
  El tratamiento fiscal de los criptoactivos en Colombia va a definirse dentro del paquete
  fiscal, no en una ley con la palabra «cripto» en el título. Que el Gobierno prometa no subir
  tarifas no significa que no toque la base: una ley que «disminuye el gasto» y simplifica
  tributos puede redefinir qué se reporta y cómo se declara un activo digital sin crear un
  impuesto nuevo. Y si el 4×1000 deja de aplicar a traslados entre productos del mismo titular,
  la discusión sobre si una transferencia hacia un exchange es un «traslado» o un «pago» se
  vuelve material.</div>
  <div class="porque"><span class="et">Qué conviene revisar</span>
  El texto de la «ley fiscal» el día que se radique (finales de septiembre): es el vehículo real,
  no la reforma del gobierno anterior. Del presupuesto, el artículo de disposiciones generales,
  donde suelen entrar reglas fiscales que no pasan por ninguna reforma.</div>
</div>

<div class="item">
  <div class="num">04 · Reputación</div>
  <h2>La salida de Europa llegó a la prensa económica colombiana como titular de opinión</h2>
  <p>Portafolio tituló el 7 de septiembre «Binance, ¡fuera de Europa!», y Bloomberg Línea preguntó
  el 5 «¿cómo sigue operando en Europa pese a no tener licencia MiCA?». Los hechos, según esa
  cobertura: Binance retiró su solicitud en Grecia el 16 de junio, un día antes de que el regulador
  la debatiera; desde el 1 de julio cerró registros nuevos, depósitos y compras spot para usuarios
  de la Unión Europea, con retiros abiertos; sigue atendiendo por solicitud inversa desde una entidad
  en Abu Dabi; dice tramitar una licencia vía Francia, y la ESMA le pidió por carta confirmar que
  está liquidando sus operaciones en el bloque. En la misma semana El Tiempo y Teleantioquia
  cubrieron un operativo internacional contra una red de explotación infantil que cobraba en
  bitcoin, sin mención de plataformas.</p>
  <div class="porque"><span class="et">Por qué le importa a Binance</span>
  El argumento «sin licencia» viaja, y la versión que llega a Colombia ya no es solo «se fue»
  sino «se quedó sin licencia»: el matiz de Bloomberg es el que un periodista va a usar. En
  Colombia no existe una licencia que pedir, pero el caso europeo es el precedente que un
  periodista o un congresista va a citar cuando pregunte bajo qué autorización opera Binance aquí. Conviene tener la respuesta lista y verificable: sociedad del
  sector real supervisada por Supersociedades, sujeto obligado a reportar ante la UIAF, con
  reporte tributario a la DIAN.</div>
  <div class="porque"><span class="et">Qué conviene revisar</span>
  Que la línea de vocería para Colombia esté escrita y en manos de quien atiende prensa, antes de
  que la pregunta llegue.</div>
</div>

<div class="item ok">
  <div class="num">05 · Consulta pública</div>
  <h2>Ninguna ventana abierta le aplica esta semana</h2>
  <p>De las <b>19 consultas públicas</b> de proyectos de norma abiertas hoy, 13 cierran en los
  próximos siete días y ninguna proviene del Ministerio de Hacienda, la DIAN, Supersociedades ni
  el Banco de la República. La única de la Superintendencia de Industria y Comercio (cierra el 9
  de septiembre) es sobre marcas holográficas.</p>
  <div class="porque"><span class="et">Por qué le importa a Binance</span>
  El borrador de ley sobre proveedores de servicios de activos virtuales que preparan el
  Ministerio de Hacienda y el Banco de la República sigue sin salir a consulta. Con el cambio de
  gobierno, el equipo que lo redactaba también cambió: cuando salga, el plazo para comentar se
  cuenta en días.</div>
</div>

<h3 class="sec">La región · lo que se movió en los mercados en vigilancia</h3>

<div class="item lat urg">
  <div class="num"><span class="pais">Guatemala</span> · nuevo mercado regulado · plazo 17 de septiembre</div>
  <h2>Los exchanges pasan a ser sujetos obligados antilavado en diez días</h2>
  <p>El <b>Decreto 15-2026</b>, nueva ley antilavado, entra en vigencia el <b>17 de septiembre</b>:
  clasifica a exchanges y custodios como proveedores de servicios de activos virtuales, sujetos
  obligados ante la Intendencia de Verificación Especial de la Superintendencia de Bancos, con
  KYC y reporte de transacciones. El objetivo declarado es alinearse con las 40 recomendaciones
  del GAFI antes de la evaluación de febrero de 2027 y evitar la lista gris.</p>
  <div class="porque"><span class="et">Por qué le importa a Binance</span>
  Es el mismo diseño que Colombia adoptó por vía administrativa en 2021, ahora con rango de ley
  y en un país que hasta hoy no tenía marco. Todo usuario guatemalteco atendido desde una entidad
  regional queda dentro del alcance desde el día 17.</div>
</div>

<div class="item lat">
  <div class="num"><span class="pais">El Salvador</span> · acuerdo con el FMI</div>
  <h2>El FMI desbloqueó fondos y el Estado se retiró de Chivo; la reserva de bitcoin queda congelada a donaciones</h2>
  <p>El 3 de septiembre el FMI anunció un acuerdo preliminar por cerca de US$140 millones. En su
  comunicado dice que la propiedad mayoritaria y el control operativo de la billetera Chivo pasaron
  a un operador privado; el presidente Bukele respondió que se transfirieron las acciones de Chivo,
  no la reserva estratégica, que la Oficina Bitcoin sitúa en más de 7.764 BTC. El FMI reitera que el
  país no aumentará sus tenencias más allá de donaciones auditadas.</p>
  <div class="porque"><span class="et">Por qué le importa a Binance</span>
  El Estado salvadoreño deja de ser operador de billetera y competidor: el espacio de la
  custodia y el intercambio minorista queda para privados con licencia bajo la NRP-29. El mercado
  sigue chico en volumen, pero el regulador dejó de ser jugador.</div>
</div>

<div class="item lat">
  <div class="num"><span class="pais">República Dominicana</span> · Congreso</div>
  <h2>Los dos proyectos de ley siguen parados en la Comisión de Hacienda</h2>
  <p>Las iniciativas 05400 (prevención, control y regulación de las criptomonedas, del diputado
  Carlos de Pérez) y 05569 (activos digitales y criptoactivos, del diputado Jorge Frías) llevan
  más de dos meses sin convocatoria desde las vistas técnicas del 28 de mayo y el 8 de junio, en
  las que participaron Tether, Finlabs y la Asociación de Bitcoin Dominicana.</p>
  <div class="porque"><span class="et">Por qué le importa a Binance</span>
  El proyecto que proponía licencias para exchanges y custodios no avanza, y la comisión ya
  escuchó a la industria. Es una ventana para incidir en el texto antes de que se reactive, no
  después.</div>
</div>

<div class="item lat ok">
  <div class="num"><span class="pais">Perú · Bolivia · Venezuela</span> · sin novedad en la ventana</div>
  <h2>Los tres regímenes siguen como estaban; el siguiente hito en cada uno es administrativo, no legislativo</h2>
  <p>En Perú el régimen PSAV (Decreto Supremo 006-2023-JUS y Resolución SBS 02648-2024) no
  registró actos nuevos y el proyecto de ley marco sigue sin avance en el Congreso. En Bolivia el
  plazo de la ASFI para presentar carta de intención venció el 30 de abril: quien no lo hizo quedó
  impedido de operar y de publicitarse como fintech autorizada; la banca ya ofrece cuentas en
  USDT desde la app. En Venezuela solo dos plataformas operan con licencia de la Sunacrip
  (Crixto hasta el 31 de diciembre de 2026, Kontigo hasta 2027) y no hubo actos nuevos.</p>
  <div class="porque"><span class="et">Por qué le importa a Binance</span>
  En los tres el siguiente hito no es una norma sino una decisión administrativa: autorizaciones
  de la ASFI, supervisión de la SBS y las renovaciones de la Sunacrip, que se concentran en el
  primer trimestre de 2027. Vigilar resoluciones, no proyectos.</div>
</div>

<div class="item lat">
  <div class="num"><span class="pais">México</span> · señal para el radar regional</div>
  <h2>La iniciativa AVE reservaría la emisión de stablecoins en pesos a bancos e instituciones de fondos de pago</h2>
  <p>La iniciativa presentada en mayo por el senador Alejandro Murat crea los «activos virtuales
  estables referenciados a la moneda nacional»: paridad 1:1 con el peso, emisión solo por
  instituciones de fondos de pago electrónico y bancos con autorización de Banxico, y pena de
  cinco a quince años de prisión por emitir sin autorización.</p>
  <div class="porque"><span class="et">Por qué le importa a Binance</span>
  Si prospera, un producto de stablecoin en pesos mexicanos solo podría ofrecerse a través de una
  entidad autorizada. México no está hoy entre los mercados en vigilancia; esta iniciativa es la
  razón para sumarlo.</div>
</div>

<div class="hero">
<h3 class="sec" style="margin-top:0">Qué no se movió — verificado, no asumido</h3>
<table>
  <tr><th style="width:26%">Fuente</th><th>En la ventana</th></tr>
  <tr><td>Superintendencias y reguladores</td><td class="q">Cero actos sobre activos virtuales, criptoactivos o lavado de activos en las 17 fuentes del registro regulatorio entre el 31 de agosto y el 6 de septiembre.</td></tr>
  <tr><td>Ejecutivo</td><td class="q">La normativa de Presidencia está al día al 28 de agosto; ningún decreto de agosto menciona criptoactivos o activos virtuales.</td></tr>
  <tr><td>Congreso</td><td class="q">Trece proyectos radicados entre el 1 y el 2 de septiembre; ninguno sobre criptoactivos. El proyecto de proveedores de servicios de activos virtuales sigue archivado.</td></tr>
  <tr><td>DIAN</td><td class="q">Sin actos nuevos sobre criptoactivos. El calendario de renta de personas naturales sigue corriendo en septiembre: la pregunta del usuario por cómo declarar sigue llegando.</td></tr>
  <tr><td>Contratación estatal</td><td class="q">No aplica: Binance no registra contratos con el Estado colombiano.</td></tr>
</table>

<div class="foot">
  <b>Fuentes.</b> Registro de proyectos de ley del Senado y la Cámara y órdenes del día de sus
  comisiones; normativa de Presidencia, la DIAN y Supersociedades; obligaciones de reporte de la
  UIAF; consulta pública de proyectos de norma del DNP; prensa nacional y regional de Colombia y
  de los seis países en vigilancia; comunicados del FMI, la Superintendencia de Bancos de
  Guatemala, la ASFI de Bolivia, la SBS de Perú y la Sunacrip. Cada afirmación es verificable
  contra el acto o la nota que la respalda.<br>
  <b>Ventana.</b> 31 de agosto al 6 de septiembre de 2026.<br>
  <b>Alcance.</b> Documento de monitoreo regulatorio; no constituye asesoría legal ni tributaria.
  Las decisiones de cumplimiento requieren el criterio del equipo jurídico de Binance.<br>
  Caudal · módulo de inteligencia regulatoria de Cauce.
</div>
</div>

</body></html>
"""


def render():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(HTML_TMP, "w", encoding="utf-8") as f:
        f.write(HTML_DOC)
    try:
        from weasyprint import HTML
        HTML(string=HTML_DOC, base_url=ROOT).write_pdf(OUT)
        return "weasyprint"
    except ImportError:
        pass
    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if not os.path.exists(chrome):
        chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        raise SystemExit("ni weasyprint ni Chrome: no hay con qué renderizar")
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--print-to-pdf=" + OUT, "file://" + HTML_TMP],
                   check=True, capture_output=True, timeout=120)
    return "chrome"


if __name__ == "__main__":
    motor = render()
    print(f"OK ({motor}) · {OUT} · {os.path.getsize(OUT)/1024:.0f} KB")
