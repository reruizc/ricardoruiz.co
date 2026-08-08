#!/usr/bin/env python3
"""
Brief regulatorio semanal · Binance Colombia — Caudal x Cauce.

Ventana: jueves 6 → sábado 8 de agosto de 2026. Se entrega el lunes 10.

QUÉ ES Y QUÉ NO: es un brief de MONITOREO (qué se movió, qué no y qué sigue),
no una pieza de incidencia como el boletín de IATA que sirvió de referencia de
forma. Todo lo que afirma sale de una fuente verificada de Caudal; lo que no se
pudo verificar se dice, no se rellena.

CONTEXTO DEL CLIENTE: se contrasta contra su propia matriz LATAM
(caudalxcauce/Binance/), fechada 8-abr-2026, cuyas 7 filas de Colombia son:
  1.1 PL 510/25C · PSAV · «amigable» · «pendiente segundo debate»
  1.2 Borrador PL grupo intergubernamental · MinHacienda/BanRep · «adversarial»
  1.3 Resolución 000240 de 24-dic-2025 · DIAN · «adversarial»
  1.4 Circular Externa 002 de 07-oct-2025 · SIC · «neutral / costosa»
  1.5 Circular Externa 001 de 18-sep-2025 · SIC · «neutral / costosa»
  1.6 Proyecto de Circular sobre SAGR · Supersociedades · «adversarial / costosa»
  1.7 Decreto 0368 de 2026 · Finanzas Abiertas · MinHacienda · «neutral / costosa»

DOS HALLAZGOS que cambian el estado de esa matriz, ambos verificados contra el
dato crudo (no contra el reporte de quien cosechó la fuente):
  · La obligación de reporte a la UIAF para PSAV existe desde 2021 y la matriz
    no la registra. Verificado en raw/uiaf-reportantes.json.
  · El «proyecto» de circular de SAGR se expidió el 2-jul-2026 como Circular
    Externa 100-000020. Verificado en raw/supersociedades.json.

SISTEMA VISUAL v2: fondo #060810, Helvetica Neue embebida de fonts/*.woff2,
Syne solo en el wordmark, logo de 4 barras. Misma plantilla que las propuestas.

Salida: caudalxcauce/Binance/Brief-Binance-2026-08-10.pdf  (carpeta gitignorada:
es material de cliente y el repo es público).
"""
import os
from weasyprint import HTML

ROOT = "/Users/ricardoruiz/ricardoruiz.co"
OUT = os.path.join(ROOT, "caudalxcauce", "Binance", "Brief-Binance-2026-08-10.pdf")

FDIR = os.path.join(ROOT, "fonts")
F_SYNE = os.path.join(ROOT, "tools", "build-propuesta-tesis-oe3", "fonts", "Syne-ExtraBold.ttf")
F_HN = os.path.join(FDIR, "helveticaneue.woff2")
F_HN_B = os.path.join(FDIR, "helveticaneue-bold.woff2")
F_HN_M = os.path.join(FDIR, "helveticaneue-medium.woff2")
F_HN_L = os.path.join(FDIR, "helveticaneue-light.woff2")
F_HN_I = os.path.join(FDIR, "helveticaneue-italic.woff2")
LOGO = os.path.join(ROOT, "caudalxcauce.png")   # el mismo de caudal.html

CSS = f"""
@font-face {{ font-family:'HN'; src:url('file://{F_HN}'); font-weight:400; }}
@font-face {{ font-family:'HN'; src:url('file://{F_HN_B}'); font-weight:700; }}
@font-face {{ font-family:'HN'; src:url('file://{F_HN_M}'); font-weight:500; }}
@font-face {{ font-family:'HN'; src:url('file://{F_HN_L}'); font-weight:300; }}
@font-face {{ font-family:'HN'; src:url('file://{F_HN_I}'); font-style:italic; }}
@font-face {{ font-family:'Syne'; src:url('file://{F_SYNE}'); font-weight:800; }}

@page {{ size:A4; margin:14mm 13mm 15mm 13mm; background:#060810; }}
* {{ box-sizing:border-box; }}
body {{ font-family:'HN',sans-serif; color:#e8e9ee; background:#060810;
        font-size:9.1pt; line-height:1.5; margin:0; }}

.top {{ display:flex; justify-content:space-between; align-items:flex-end;
        border-bottom:1px solid rgba(255,255,255,.14); padding-bottom:6px; margin-bottom:14px; }}
.brand {{ font-family:'Syne',sans-serif; font-weight:800; font-size:12pt; letter-spacing:-.3px; }}
.brand .dot {{ color:#3d6fff; }}
.top .meta {{ font-size:7.2pt; color:#8b90a0; text-align:right; letter-spacing:.4px; text-transform:uppercase; }}

h1 {{ font-size:20pt; font-weight:700; line-height:1.12; margin:0 0 6px; letter-spacing:-.6px; }}
h1 .hl {{ color:#3d6fff; }}
.lead {{ font-size:9.4pt; color:#b9bdc9; font-weight:300; margin:0 0 4px; max-width:165mm; }}
.window {{ font-size:7.4pt; color:#8b90a0; text-transform:uppercase; letter-spacing:.6px;
           margin:10px 0 16px; padding-top:8px; border-top:1px solid rgba(255,255,255,.09); }}

.item {{ margin:0 0 13px; padding:12px 14px; background:rgba(255,255,255,.032);
         border-left:2px solid #3d6fff; page-break-inside:avoid; }}
.item.warn {{ border-left-color:#f97316; }}
.item.ok {{ border-left-color:#4ade80; }}
.num {{ font-size:7pt; color:#8b90a0; letter-spacing:1.1px; text-transform:uppercase; margin-bottom:3px; }}
.item h2 {{ font-size:11pt; font-weight:700; margin:0 0 5px; line-height:1.25; }}
.item p {{ margin:0 0 5px; color:#ccd0da; }}
.item p:last-child {{ margin-bottom:0; }}
b {{ color:#fff; font-weight:700; }}
.tag {{ display:inline-block; font-size:6.6pt; letter-spacing:.7px; text-transform:uppercase;
        padding:1.5px 6px; border-radius:2px; margin-left:5px; vertical-align:2px; font-weight:700; }}
.tag.new {{ background:#f97316; color:#1a0d02; }}
.tag.upd {{ background:#3d6fff; color:#fff; }}
.qhacer {{ margin-top:6px; padding-top:5px; border-top:1px dashed rgba(255,255,255,.14);
           font-size:8.4pt; color:#9aa0b0; }}
.qhacer b {{ color:#e8e9ee; }}

h3.sec {{ font-size:8pt; text-transform:uppercase; letter-spacing:1.1px; color:#8b90a0;
          margin:16px 0 7px; padding-bottom:4px; border-bottom:1px solid rgba(255,255,255,.1); }}
table {{ width:100%; border-collapse:collapse; font-size:8.1pt; }}
td, th {{ text-align:left; padding:4px 7px 4px 0; vertical-align:top;
          border-bottom:1px solid rgba(255,255,255,.07); }}
th {{ color:#8b90a0; font-weight:500; font-size:7.2pt; text-transform:uppercase; letter-spacing:.5px; }}
td.q {{ color:#9aa0b0; }}
.foot {{ margin-top:16px; padding-top:8px; border-top:1px solid rgba(255,255,255,.12);
         font-size:7.2pt; color:#7d8290; line-height:1.55; }}
.foot b {{ color:#a8adba; }}

/* Marca de agua: el logo de Caudal, centrado arriba y en TODAS las páginas.
   `position:fixed` en WeasyPrint significa «repetir en cada página», que es
   justo lo que queremos. Va detrás del contenido (z-index negativo) y a opacidad
   baja: tiene que leerse como sello, no competir con el titular. */
.wm {{ position:fixed; top:26mm; left:0; right:0; text-align:center;
       z-index:-1; opacity:.07; }}
.wm img {{ width:118mm; }}
"""

TOP = """
<div class="top">
  <div class="brand">Caudal<span class="dot">·</span>Cauce</div>
  <div class="meta">Brief regulatorio · Binance Colombia<br>Semana del 10 de agosto de 2026</div>
</div>
"""

HTML_DOC = f"""
<html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div class="wm"><img src="file://{LOGO}" alt=""></div>
{TOP}

<h1>Lo que se movió, y lo que <span class="hl">su matriz todavía no registra</span>.</h1>
<p class="lead">Barrido del jueves 6 al sábado 8 de agosto sobre Congreso, superintendencias,
Ejecutivo, consulta pública de normas y prensa. Dos de los siete frentes colombianos de su
matriz cambiaron de estado, y hay una obligación vigente que la matriz no tiene.</p>
<div class="window">Ventana 6–8 ago 2026 · contrastado contra la Matriz de Priorización LATAM del 8 de abril</div>

<div class="item warn">
  <div class="num">01 · Cumplimiento</div>
  <h2>Ya tienen una obligación de reporte viva ante la UIAF<span class="tag new">no está en la matriz</span></h2>
  <p>La <b>Resolución 314 de 2021</b> impone el reporte a la UIAF a «las empresas y personas naturales
  que provean servicios de activos virtuales en Colombia», y la <b>Resolución 84 de 2022</b> la
  desarrolla. No es un proyecto: la UIAF mantiene un sector reportante propio de activos virtuales,
  con <b>calendario de reportes 2026 vigente</b> y anexos técnicos que exigen número de wallet,
  hash de la operación y wallet de contraparte.</p>
  <p>El contraste importa: mientras el debate público —y la matriz— se concentran en si habrá o no
  una ley de PSAV, la obligación operativa <b>ya existe por vía administrativa</b> y lleva cinco años.
  Ninguna de las siete filas de Colombia la registra.</p>
  <div class="qhacer"><b>Qué haría yo:</b> confirmar el estado de registro y de reporte antes de que
  el tema escale. Es el único punto de este brief donde el riesgo es de incumplimiento presente,
  no de exposición futura.</div>
</div>

<div class="item upd">
  <div class="num">02 · Lavado de activos</div>
  <h2>El «proyecto de circular de SAGR» dejó de ser proyecto el 2 de julio<span class="tag upd">actualiza fila 1.6</span></h2>
  <p>Su matriz lo tiene como <i>«en consulta hasta el 8 de abril de 2026 · adversarial / costosa»</i>.
  La fecha era exacta, pero el estado quedó atrás: se expidió como <b>Circular Externa 100-000020
  del 2 de julio de 2026</b>, que modifica integralmente la Circular Básica Jurídica de
  Supersociedades — el cuerpo donde vive el SAGRILAFT.</p>
  <p>Y hay un antecedente que la matriz tampoco recoge: el mismo texto ya había estado en consulta
  entre el 19 de diciembre de 2025 y el 4 de enero de 2026. Fueron dos rondas, no una.</p>
  <p>Vale la pena precisar por qué esta entidad y no otra: <b>Supersociedades es el supervisor de
  lavado de activos del sector real</b>, y los exchanges de criptoactivos no son vigilados de la
  Superintendencia Financiera — esa es justamente la razón de ser del proyecto de ley de PSAV.</p>
  <div class="qhacer"><b>Qué haría yo:</b> mover la fila 1.6 de «en consulta» a «expedida» y
  revisar el Capítulo X de la nueva Circular Básica Jurídica contra su programa actual.</div>
</div>

<div class="item">
  <div class="num">03 · Fiscal</div>
  <h2>El único frente con tracción pública esta semana fue el de la DIAN</h2>
  <p>La <b>Resolución 000240 del 24 de diciembre de 2025</b> —su fila 1.3, marcada adversarial—
  aterrizó en prensa en tres medios en tres días: Infobae (5 de agosto), Noticias RCN (6) y
  redmas (7), este último con el anuncio de <b>sanción para quienes omitan reportar criptoactivos
  en la declaración de renta</b>.</p>
  <p>El desplazamiento de la conversación es el dato: pasó de «si se regula» a «cómo se declara».
  Para una plataforma eso mueve el problema del área de asuntos públicos al área de producto y
  soporte, porque quien pregunta ya no es el regulador sino el usuario.</p>
</div>

<div class="item">
  <div class="num">04 · Legislativo</div>
  <h2>No hay vehículo de cripto en el Congreso — el cerco viene por el lado financiero</h2>
  <p>De los <b>258 proyectos radicados</b> en la legislatura que arrancó el 20 de julio,
  <b>ninguno es de criptoactivos</b>. Y su fila 1.1 hay que corregirla: el <b>PL 510/2025 Cámara
  de PSAV está archivado</b>. No es un tropiezo aislado — es el <b>sexto intento fallido desde
  2018</b>, y cuatro de los seis son el mismo proyecto re-radicado una y otra vez.</p>
  <p>Pero lo que sí está radicado los toca de lado, y en sus dos comisiones:</p>
  <table>
    <tr><th>Proyecto</th><th>Por qué les pega</th></tr>
    <tr><td><b>068/2026C</b></td><td class="q">Finanzas abiertas (<i>open finance</i>) y modifica la Ley 1328. Toca el mismo marco que el Decreto 0368 de su fila 1.7, pero por vía legislativa.</td></tr>
    <tr><td><b>070/2026C</b></td><td class="q">Elimina con rango legal la retención en la fuente en pagos con tarjeta: rieles de entrada y salida.</td></tr>
    <tr><td><b>004/2026C</b></td><td class="q">Reforma tributaria. Es el vehículo donde se define el tratamiento fiscal de los activos digitales.</td></tr>
    <tr><td><b>085/2026C</b></td><td class="q">Modifica el Estatuto Tributario.</td></tr>
    <tr><td colspan="2" class="q">Dos proyectos más modifican la Ley 1328 de 2009 (régimen del consumidor financiero) y cuatro regulan inteligencia artificial.</td></tr>
  </table>
  <div class="qhacer"><b>Lectura:</b> la regulación que los va a alcanzar en Colombia no va a llegar
  con el título «cripto». Va a llegar dentro del paquete fiscal y de consumidor financiero.</div>
</div>

<div class="item ok">
  <div class="num">05 · Consulta pública</div>
  <h2>Esta semana no hay nada que comentar, y eso también es información</h2>
  <p>De las <b>31 consultas públicas abiertas</b> hoy en el sistema del DNP, <b>ninguna</b> es de
  MinHacienda, la DIAN, la SIC ni Supersociedades. No hay ventana abierta que les aplique.</p>
  <p>El punto de vigilancia es su <b>fila 1.2</b>: el borrador del grupo intergubernamental
  (MinHacienda y Banco de la República), que la matriz marca «en construcción» y «adversarial».
  Cuando salga a consulta va a aparecer ahí, con plazo de días, no de semanas.</p>
</div>

<h3 class="sec">Lo que su matriz no cubre y sí les aplica</h3>
<table>
  <tr><th style="width:32%">Frente</th><th>Estado</th></tr>
  <tr><td><b>UIAF · reporte de operaciones</b></td><td class="q">Obligación vigente desde 2021. Ver punto 01.</td></tr>
  <tr><td><b>Régimen cambiario</b></td><td class="q">La circular vigente del Banco de la República es la <b>DCIP-83</b> (2023). La DCIN-83, que suele citarse de memoria, está derogada desde el 31 de octubre de 2023. Para operaciones con divisas la referencia correcta importa.</td></tr>
</table>

<h3 class="sec">Qué no pasó — verificado, no asumido</h3>
<table>
  <tr><th style="width:26%">Fuente</th><th>En la ventana</th></tr>
  <tr><td>Congreso</td><td class="q">Cero radicaciones. El viernes 7 fue posesión presidencial y festivo; el registro cierra el 5 de agosto.</td></tr>
  <tr><td>Ejecutivo</td><td class="q">Sin novedad. La norma más reciente de Presidencia es del 1 de julio: la fuente se publica mensualmente.</td></tr>
  <tr><td>Superintendencias</td><td class="q">Ningún acto nuevo en la ventana. El más reciente del pilar es del 14 de julio.</td></tr>
  <tr><td>Contratación estatal</td><td class="q">No aplica: Binance no registra contratos con el Estado colombiano.</td></tr>
</table>

<div class="foot">
  <b>Trazabilidad.</b> Cada afirmación de este brief sale de una fuente oficial cosechada por Caudal
  y es verificable contra su acto: registro de proyectos de ley del Senado y la Cámara, normativa de
  la DIAN, normativa de Supersociedades, obligaciones de reporte de la UIAF, régimen cambiario del
  Banco de la República, sistema de consulta pública del DNP y prensa nacional y regional.<br>
  <b>Ventana.</b> 6 al 8 de agosto de 2026. El contraste con la matriz se hace contra la versión del
  8 de abril de 2026 entregada por el cliente.<br>
  <b>Alcance.</b> Este documento es un insumo de monitoreo; no constituye asesoría legal ni tributaria.
  Las decisiones de cumplimiento requieren el criterio de su equipo jurídico.<br>
  Caudal · módulo de inteligencia regulatoria de Cauce.
</div>

</body></html>
"""

if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    HTML(string=HTML_DOC, base_url=ROOT).write_pdf(OUT)
    print(f"OK · {OUT} · {os.path.getsize(OUT)/1024:.0f} KB")
