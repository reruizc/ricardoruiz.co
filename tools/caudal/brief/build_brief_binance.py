#!/usr/bin/env python3
"""
Brief regulatorio semanal · Binance Colombia — Caudal x Cauce.

Ventana: jueves 6 → sábado 8 de agosto de 2026. Se entrega el lunes 10.

VOZ (decisión de Ricardo, ago-2026): el documento le habla A BINANCE, como su
asistente regulatorio. Cada punto es «pasó esto → le pega a Binance por esto →
esto es lo que hay que mirar». NO es un inventario de normas ni un informe de
avance nuestro.

⚠️ NADA DE COCINA INTERNA. Fuera toda referencia a su matriz de priorización:
si una fila está desactualizada o si una norma no la tenían registrada es un
insumo NUESTRO para trabajar, no algo que el cliente deba leer. El brief dice
qué pasó y por qué le importa; el contraste con su matriz se usa para DECIDIR
qué entra, y ahí se queda.

DISEÑO: fondo claro y tinta negra (antes era el oscuro del sistema visual v2 —
se cambió porque un brief se imprime y se reenvía). El logo va arriba a la
izquierda, en su versión de tinta oscura (assets/caudalxcauce-tinta.png, que se
genera del alfa del logo del sitio: el original es de trazo casi blanco y sobre
papel desaparece). Sin marca de agua: el logo ya está arriba y repetirlo detrás
del texto ensucia la lectura.

Salida: caudalxcauce/Binance/Brief-Binance-2026-08-10.pdf  (carpeta gitignorada:
es material de cliente y el repo es público).
"""
import os
from weasyprint import HTML

ROOT = "/Users/ricardoruiz/ricardoruiz.co"
OUT = os.path.join(ROOT, "caudalxcauce", "Binance", "Brief-Binance-2026-08-10.pdf")

FDIR = os.path.join(ROOT, "fonts")
F_HN = os.path.join(FDIR, "helveticaneue.woff2")
F_HN_B = os.path.join(FDIR, "helveticaneue-bold.woff2")
F_HN_M = os.path.join(FDIR, "helveticaneue-medium.woff2")
F_HN_L = os.path.join(FDIR, "helveticaneue-light.woff2")
F_HN_I = os.path.join(FDIR, "helveticaneue-italic.woff2")
LOGO = os.path.join(ROOT, "tools", "caudal", "brief", "assets", "caudalxcauce-tinta.png")
TILE = os.path.join(ROOT, "tools", "caudal", "brief", "assets", "papel-guilloche.png")

CSS = f"""
@font-face {{ font-family:'HN'; src:url('file://{F_HN}'); font-weight:400; }}
@font-face {{ font-family:'HN'; src:url('file://{F_HN_B}'); font-weight:700; }}
@font-face {{ font-family:'HN'; src:url('file://{F_HN_M}'); font-weight:500; }}
@font-face {{ font-family:'HN'; src:url('file://{F_HN_L}'); font-weight:300; }}
@font-face {{ font-family:'HN'; src:url('file://{F_HN_I}'); font-style:italic; }}

@page {{ size:A4; margin:27mm 12mm 13mm 12mm;
         /* Papel con textura de cuadrícula fina, tipo dial guilloché
            («grande tapisserie»): dos rejillas de hairlines cruzadas a 4,2mm
            que forman cuadros pequeños, más una diagonal aún más tenue que
            insinúa el relieve. El contraste con el fondo es de 3-4 puntos de
            luminancia: se percibe como textura, no como rayado, y no se
            ensucia al imprimir. */
         background-color:#fbfaf8;
         background-image:url('file://{TILE}');
         background-size:4.6px 4.6px; background-repeat:repeat; }}
* {{ box-sizing:border-box; }}
body {{ font-family:'HN',sans-serif; color:#15171c; background:transparent;
        font-size:9.8pt; line-height:1.5; margin:0; }}

.top {{ display:flex; justify-content:space-between; align-items:flex-end;
        border-bottom:1.5px solid #15171c; padding:0 0 6px;
        background:#fbfaf8;
        /* `position:fixed` en WeasyPrint significa «repetir en cada página».
           El encabezado deja de ser parte del flujo, así que el margen superior
           de @page se ensancha para dejarle sitio y que no pise el contenido. */
        position:fixed; top:-14mm; left:0; right:0; }}
.top img {{ height:12.5mm; }}
.top .meta {{ font-size:7.8pt; color:#5a6070; text-align:right; letter-spacing:.4px;
              text-transform:uppercase; line-height:1.6; }}

h1 {{ font-size:19.3pt; font-weight:700; line-height:1.14; margin:0 0 7px;
      letter-spacing:-.5px; color:#0b0d11; }}
h1 .hl {{ color:#2b5672; }}   /* azul de cauce.co, no el #0047FF del sitio */
.lead {{ font-size:10.1pt; color:#3d434f; font-weight:300; margin:0 0 4px; max-width:168mm; }}
.window {{ font-size:7.4pt; color:#5a6070; text-transform:uppercase; letter-spacing:.6px;
           margin:9px 0 0; padding-top:7px; border-top:1px solid #dfe2e8; }}

/* El texto nunca va directo sobre la textura del papel: a ciertos zooms las
   diagonales entran en moiré con los trazos de la letra y el titular se
   ensucia. Las tarjetas ya traen fondo propio; la cabecera necesitaba el suyo.
   El patrón queda donde debe leerse: márgenes y aire entre bloques. */
.hero {{ background:#fdfdfc; border:1px solid #eceef2; border-radius:2px;
         padding:12px 15px 10px; margin:0 0 13px; page-break-inside:avoid; }}

/* Las tarjetas: fondo gris muy claro + borde completo + franja de color a la
   izquierda. Antes eran solo una franja sobre fondo casi igual al papel y no se
   leían como bloques separados. */
.item {{ margin:0 0 13px; padding:12px 15px; background:#fdfdfc;
         border:1px solid #e2e5ea; border-left:3px solid #2b5672;
         border-radius:2px;
         /* Las cajas FLUYEN entre páginas. Con `page-break-inside:avoid` una
            caja alta que no cabía saltaba entera y dejaba un tercio de página
            en blanco — pasaba en dos de las cuatro páginas. Lo que sí se
            protege es que el título no quede huérfano al pie (`h2` y el rótulo
            con `page-break-after:avoid`) y que los bloques de «por qué» no se
            partan: son cortos y partidos no se entienden. */
         orphans:3; widows:3; }}
.item.urg {{ border-left-color:#d9480f; background:#fdf7f4; border-color:#f0dbd0; }}
.item.ok  {{ border-left-color:#2b8a3e; background:#f5faf6; border-color:#d6e9da; }}
/* Resumen ejecutivo: violeta, el único de los cuatro que no está en uso (azul
   = tema normal · café = urgente · verde = sin acción). Va con la franja más
   gruesa porque abre el documento. */
.item.resumen {{ border-left-width:5px; border-left-color:#5f3dc4;
                 background:#f8f6fd; border-color:#e0d8f5; }}
.item.resumen h2 {{ font-size:12.4pt; }}
.item.resumen p {{ font-size:10.1pt; }}
.num {{ font-size:7.4pt; color:#6b7280; letter-spacing:1.2px; text-transform:uppercase;
        margin-bottom:4px; font-weight:500; page-break-after:avoid; }}
.item h2 {{ font-size:11.7pt; font-weight:700; margin:0 0 5px; line-height:1.28; color:#0b0d11;
            page-break-after:avoid; }}
.item p {{ margin:0 0 6px; color:#2b303a; }}
.item p:last-child {{ margin-bottom:0; }}
b {{ color:#0b0d11; font-weight:700; }}

/* «Por qué le importa» y «qué mirar»: son la razón de ser del brief, así que
   van marcados y no como un párrafo más. */
.porque {{ page-break-inside:avoid; margin-top:6px; padding:7px 10px; background:#fff; border:1px solid #e2e5ea;
           border-radius:2px; font-size:9.35pt; color:#2b303a; }}
.porque .et {{ display:block; font-size:7.2pt; letter-spacing:1.1px; text-transform:uppercase;
               color:#2b5672; font-weight:700; margin-bottom:2px; }}
.item.urg .porque .et {{ color:#d9480f; }}
.item.ok  .porque .et {{ color:#2b8a3e; }}
.item.resumen .porque .et {{ color:#5f3dc4; }}

h3.sec {{ font-size:8.6pt; text-transform:uppercase; letter-spacing:1.1px; color:#5a6070;
          margin:13px 0 6px; padding-bottom:4px; border-bottom:1px solid #dfe2e8; }}
table {{ width:100%; border-collapse:collapse; font-size:9.0pt; }}
td, th {{ text-align:left; padding:4px 8px 4px 0; vertical-align:top;
          border-bottom:1px solid #e6e9ee; }}
th {{ color:#5a6070; font-weight:500; font-size:7.8pt; text-transform:uppercase;
      letter-spacing:.5px; }}
td.q {{ color:#3d434f; }}
.foot {{ margin-top:16px; padding-top:9px; border-top:1px solid #d8dce3;
         font-size:7.8pt; color:#6b7280; line-height:1.6; }}
.foot b {{ color:#3d434f; }}
"""

TOP = f"""
<div class="top">
  <img src="file://{LOGO}" alt="Caudal × Cauce">
  <div class="meta">Brief regulatorio · Binance Colombia<br>Semana del 10 de agosto de 2026</div>
</div>
"""

HTML_DOC = f"""
<html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
{TOP}

<div class="hero">
  <h1>Lo que se movió en Colombia y <span class="hl">cómo afecta a Binance</span>.</h1>
  <p class="lead">Barrido del jueves 6 al sábado 8 de agosto sobre el Congreso, las
  superintendencias, el Ejecutivo, la consulta pública de normas y la prensa. Cinco temas,
  ordenados por lo que exige atención primero.</p>
  <div class="window">Ventana 6–8 de agosto de 2026 · Colombia</div>
</div>

<div class="item resumen">
  <div class="num">Resumen ejecutivo</div>
  <h2>Lo que se movió no es lo que ocupa la conversación pública</h2>
  <p>Mientras la discusión sigue puesta en si Colombia tendrá o no una ley de criptoactivos,
  los tres frentes que se movieron esta semana <b>ya están vigentes y ya le aplican a Binance</b>:
  la obligación de reporte ante la UIAF —con calendario 2026 corriendo y datos exigidos a nivel de
  wallet—, la reescritura que hizo Supersociedades de las reglas de prevención de lavado el 2 de
  julio, y la decisión de la DIAN de llevar los criptoactivos a la declaración de renta, que esta
  semana saltó a prensa con anuncio de sanción.</p>
  <p>En el Congreso <b>no hay ninguna ley de cripto en trámite</b> —la que había fue archivada, y es
  el sexto intento fallido desde 2018—, pero cuatro proyectos fiscales y de consumidor financiero
  alcanzan a Binance por otra vía. Y no hay ninguna ventana de comentarios abierta que le aplique,
  así que esta semana no hay nada que responder.</p>
  <div class="porque"><span class="et">Si solo hay tiempo para una cosa</span>
  Confirmar el estado de reporte ante la UIAF. Es el único punto donde una omisión sería presente
  y verificable, no una exposición futura.</div>
</div>

<div class="item urg">
  <div class="num">01 · Cumplimiento</div>
  <h2>Binance ya es sujeto obligado a reportar ante la UIAF, y el calendario de 2026 está corriendo</h2>
  <p>La <b>Resolución 314 de 2021</b> obliga a reportar a la Unidad de Información y Análisis
  Financiero a «las empresas y personas naturales que provean servicios de activos virtuales en
  Colombia», y la <b>Resolución 84 de 2022</b> desarrolla ese régimen. La UIAF mantiene un sector
  reportante propio para activos virtuales, con <b>calendario de reportes 2026 ya publicado</b> y
  anexos técnicos que piden, por operación, <b>número de wallet, hash de la transacción y wallet
  de contraparte</b>.</p>
  <div class="porque"><span class="et">Por qué le importa a Binance</span>
  Es la obligación más exigente que tiene hoy en Colombia, y la única que pide datos a nivel de
  transacción. No depende de que salga la ley de proveedores de servicios de activos virtuales:
  existe por vía administrativa desde hace cinco años y aplica ahora. Mientras la discusión
  pública se concentra en si habrá o no una ley, este es el frente donde un incumplimiento sería
  presente y verificable, no futuro.</div>
  <div class="porque"><span class="et">Qué conviene revisar</span>
  El estado de registro ante la UIAF y la ejecución del calendario de este año. El calendario de
  2027 se publica en diciembre.</div>
</div>

<div class="item">
  <div class="num">02 · Prevención de lavado de activos</div>
  <h2>Supersociedades reescribió las reglas de prevención de lavado que le aplican a Binance</h2>
  <p>El <b>2 de julio de 2026</b> expidió la <b>Circular Externa 100-000020</b>, que modifica
  integralmente su Circular Básica Jurídica — el cuerpo normativo donde vive el <b>SAGRILAFT</b>,
  el sistema de autocontrol y gestión del riesgo de lavado de activos. El texto pasó por dos
  rondas de comentarios antes de expedirse, la última cerrada el 8 de abril.</p>
  <div class="porque"><span class="et">Por qué le importa a Binance</span>
  En Colombia el supervisor de lavado de activos de un exchange de criptoactivos <b>no es la
  Superintendencia Financiera sino Supersociedades</b>, porque opera como sociedad del sector
  real y no como entidad vigilada financiera. Esa es, de hecho, la razón por la que existe el
  proyecto de ley de PSAV. Lo que cambie en esa circular cambia directamente el programa de
  cumplimiento que Binance debe tener montado.</div>
  <div class="porque"><span class="et">Qué conviene revisar</span>
  El Capítulo X en su nueva redacción, contrastado contra el programa vigente, y los plazos de
  transición que fije la circular.</div>
</div>

<div class="item">
  <div class="num">03 · Tributario</div>
  <h2>La DIAN llevó los criptoactivos a la declaración de renta, y esta semana lo dijo en público</h2>
  <p>La <b>Resolución 000240 del 24 de diciembre de 2025</b> incorporó el reporte de criptoactivos
  al régimen de información. Entre el 5 y el 7 de agosto el tema salió en tres medios —Infobae,
  Noticias RCN y redmas—, el último con el anuncio de <b>sanción para quienes omitan reportar
  criptoactivos en su declaración de renta</b>.</p>
  <div class="porque"><span class="et">Por qué le importa a Binance</span>
  El desplazamiento es el dato: la conversación pasó de «si se regula» a «cómo se declara». Eso
  mueve el problema del área de asuntos públicos a producto y soporte, porque a partir de esta
  semana quien pregunta no es el regulador sino el usuario, y pregunta por su propia
  declaración. Es carga operativa medible y estacional: aprieta en el calendario de renta.</div>
  <div class="porque"><span class="et">Qué conviene revisar</span>
  Si el material de ayuda al usuario responde qué se reporta y con qué soporte. Es la pregunta
  que va a llegar en volumen.</div>
</div>

<div class="item">
  <div class="num">04 · Legislativo</div>
  <h2>No hay una ley de cripto en trámite, pero sí cuatro proyectos que alcanzan a Binance de lado</h2>
  <p>De los <b>258 proyectos radicados</b> en la legislatura que arrancó el 20 de julio,
  <b>ninguno regula criptoactivos</b>. El proyecto que sí lo hacía —el que creaba el régimen de
  proveedores de servicios de activos virtuales— <b>fue archivado</b>. Es el sexto intento
  fallido desde 2018, y cuatro de esos seis son el mismo texto vuelto a radicar.</p>
  <p>Lo que sí está vivo llega por otra puerta, y en las dos comisiones donde se decide:</p>
  <table>
    <tr><th style="width:19%">Proyecto</th><th>Cómo alcanza a Binance</th></tr>
    <tr><td><b>068/2026C</b></td><td class="q">Impulsa las finanzas abiertas (<i>open finance</i>) y modifica la Ley 1328. Define quién accede a información financiera del usuario y bajo qué condiciones.</td></tr>
    <tr><td><b>070/2026C</b></td><td class="q">Elimina la retención en la fuente en pagos con tarjeta: toca directamente los rieles de entrada y salida de dinero.</td></tr>
    <tr><td><b>004/2026C</b></td><td class="q">Reforma tributaria. Es el vehículo donde puede definirse el tratamiento fiscal de los activos digitales.</td></tr>
    <tr><td><b>085/2026C</b></td><td class="q">Modifica el Estatuto Tributario.</td></tr>
    <tr><td colspan="2" class="q">Además, dos proyectos modifican el régimen del consumidor financiero y cuatro regulan inteligencia artificial.</td></tr>
  </table>
  <div class="porque"><span class="et">Por qué le importa a Binance</span>
  La regulación que va a alcanzarlo en Colombia probablemente no va a llevar la palabra «cripto»
  en el título. Va a llegar dentro del paquete fiscal y del régimen de consumidor financiero, que
  es donde hoy hay actividad real. Vigilar solo por la palabra clave deja el frente descubierto.</div>
</div>

<div class="item ok">
  <div class="num">05 · Consulta pública</div>
  <h2>Esta semana no hay ninguna ventana abierta para comentar</h2>
  <p>De las <b>31 consultas públicas de proyectos de norma abiertas</b> hoy, ninguna proviene del
  Ministerio de Hacienda, la DIAN, la Superintendencia de Industria y Comercio ni
  Supersociedades. No hay nada que comentar en esta ventana.</p>
  <div class="porque"><span class="et">Por qué le importa a Binance</span>
  El punto de vigilancia es el borrador de proyecto de ley que preparan de forma conjunta el
  Ministerio de Hacienda y el Banco de la República. Cuando salga a consulta, el plazo para
  comentar se cuenta en días, no en semanas — y es el único momento en que se puede incidir
  antes de que el texto quede en firme.</div>
</div>

<div class="hero">
<h3 class="sec" style="margin-top:0">Un frente que conviene sumar al radar</h3>
<table>
  <tr><th style="width:26%">Régimen cambiario</th><td class="q">Para cualquier operación con divisas, la circular vigente del Banco de la República es la <b>DCIP-83</b>, expedida en 2023. La DCIN-83, que suele citarse de memoria y sigue circulando en documentos de referencia, está <b>derogada desde el 31 de octubre de 2023</b>. Trabajar sobre la circular equivocada es un riesgo silencioso.</td></tr>
</table>

<h3 class="sec">Qué no se movió — verificado, no asumido</h3>
<table>
  <tr><th style="width:26%">Fuente</th><th>En la ventana</th></tr>
  <tr><td>Congreso</td><td class="q">Cero radicaciones. El viernes 7 fue posesión presidencial y festivo.</td></tr>
  <tr><td>Ejecutivo</td><td class="q">Sin novedad. La norma más reciente de Presidencia es del 1 de julio: esa fuente se publica mensualmente.</td></tr>
  <tr><td>Superintendencias</td><td class="q">Ningún acto nuevo en la ventana.</td></tr>
  <tr><td>Contratación estatal</td><td class="q">No aplica: Binance no registra contratos con el Estado colombiano.</td></tr>
</table>

<div class="foot">
  <b>Fuentes.</b> Registro de proyectos de ley del Senado y la Cámara; normativa de la DIAN y de
  Supersociedades; obligaciones de reporte de la UIAF; régimen cambiario del Banco de la República;
  consulta pública de proyectos de norma del DNP; prensa nacional y regional. Cada afirmación es
  verificable contra el acto que la respalda.<br>
  <b>Ventana.</b> 6 al 8 de agosto de 2026.<br>
  <b>Alcance.</b> Documento de monitoreo regulatorio; no constituye asesoría legal ni tributaria.
  Las decisiones de cumplimiento requieren el criterio del equipo jurídico de Binance.<br>
  Caudal · módulo de inteligencia regulatoria de Cauce.
</div>
</div>

</body></html>
"""

if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    HTML(string=HTML_DOC, base_url=ROOT).write_pdf(OUT)
    print(f"OK · {OUT} · {os.path.getsize(OUT)/1024:.0f} KB")
