#!/usr/bin/env python3
"""
Propuesta técnica y económica — IA OPERATIVA para el Youth Climate Justice Fund.
Cliente: YCJF · contacto Tatiana Restrepo (Finance & Operations Manager).

SISTEMA VISUAL v2 (decisión Ricardo, jul-2026 — aplica a TODAS las propuestas
nuevas): diseño basado en index.html — fondo oscuro #060810, azul #0047FF /
#3d6fff, naranja #f97316, verde #4ade80, Helvetica Neue embebida (fonts/*.woff2
del repo) para TODO el texto, Syne SOLO en el wordmark, CERO fuentes mono.
Logo = 4 barras descendentes (20/15/9/4 proporción) + "Ricardo.Ruiz" con el
punto en azul, igual que la nav del sitio.

Modelo LEGO: bloque base obligatorio (diagnóstico + política de IA responsable/
ambiental + taller + los 2 quick wins de Tatiana: grants→Sheets y correos de
contratos) + bloques opcionales a precio fijo (reclutamiento · planeación anual
· evento octubre · copiloto de reuniones) + retainer mensual + fase 2 (triaje
Submittable en 7 idiomas, a cotizar).

Frontera de alcance: lo que corre por el fiscal sponsor (RIA/Rockefeller:
contratación de consultores, invoicing, pagos) NO se toca — la consultoría vive
del lado YCJF (Workspace · Slack · Monday · Sheets).

DRAFT=True agrega la banda "BORRADOR INTERNO". Cambiar a False (y fijar
precios) antes de enviar a Tatiana.

Salida: Propuestas/Propuesta-YCJF-IA-Operativa.pdf
"""
import os
import datetime
from weasyprint import HTML

ROOT = "/Users/ricardoruiz/ricardoruiz.co"
OUT = os.path.join(ROOT, "Propuestas", "Propuesta-YCJF-IA-Operativa.pdf")

# --- Estado del documento ---------------------------------------------------
DRAFT = True   # False = versión para enviar (quita banda de borrador)

# --- Cifras de REFERENCIA (revisar con el equipo antes de enviar) -----------
BASE_USD      = "US$ 2.500"     # bloque base, pago único (incluye quick wins)
B_RECLUT      = "US$ 1.200"     # bloque reclutamiento
B_PLANEA      = "US$ 1.500"     # bloque planeación anual (incluye facilitación)
B_EVENTO      = "US$ 1.800"     # bloque evento octubre (~100 personas)
B_REUNION     = "US$ 900"       # bloque copiloto de reuniones
RETAINER_USD  = "US$ 600"       # retainer mensual (soporte + iteración)
FASE2         = "A cotizar"     # triaje Submittable 7 idiomas

_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
_hoy = datetime.date.today()
FECHA = f"{_hoy.day} DE {_MESES[_hoy.month - 1].upper()} DE {_hoy.year}"

F_SYNE   = os.path.join(ROOT, "tools", "build-propuesta-tesis-oe3", "fonts", "Syne-ExtraBold.ttf")
FDIR     = os.path.join(ROOT, "fonts")
F_HN     = os.path.join(FDIR, "helveticaneue.woff2")
F_HN_B   = os.path.join(FDIR, "helveticaneue-bold.woff2")
F_HN_I   = os.path.join(FDIR, "helveticaneue-italic.woff2")
F_HN_M   = os.path.join(FDIR, "helveticaneue-medium.woff2")
F_HN_L   = os.path.join(FDIR, "helveticaneue-light.woff2")

DRAFT_BAND = ("""
  <div class="draftband">BORRADOR INTERNO v1 · cifras de referencia por definir · no enviar</div>
""" if DRAFT else "")

HTML_DOC = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<style>
  @font-face{ font-family:"Syne"; src:url("file://__SYNE__") format("truetype"); font-weight:800; font-style:normal; }
  @font-face{ font-family:"HelveticaNeue"; src:url("file://__HN__") format("woff2"); font-weight:400; font-style:normal; }
  @font-face{ font-family:"HelveticaNeue"; src:url("file://__HNB__") format("woff2"); font-weight:700; font-style:normal; }
  @font-face{ font-family:"HelveticaNeue"; src:url("file://__HNI__") format("woff2"); font-weight:400; font-style:italic; }
  @font-face{ font-family:"HelveticaNeue"; src:url("file://__HNM__") format("woff2"); font-weight:500; font-style:normal; }
  @font-face{ font-family:"HelveticaNeue"; src:url("file://__HNL__") format("woff2"); font-weight:300; font-style:normal; }
  @page {
    size: Letter;
    margin: 14mm 15mm 13mm 15mm;
    background: #060810;
    @bottom-left {
      content: "Ricardo.Ruiz  ·  ricardoruiz.co  ·  Documento privado";
      font-family: "HelveticaNeue", Helvetica, sans-serif;
      font-size: 7pt; color: #4a5060; letter-spacing: .6px;
    }
    @bottom-right {
      content: "Pág. " counter(page) " / " counter(pages);
      font-family: "HelveticaNeue", Helvetica, sans-serif;
      font-size: 7pt; color: #4a5060;
    }
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  :root{
    --white:#f4f3ef; --blue:#0047FF; --blue-light:#3d6fff;
    --green:#4ade80; --orange:#f97316;
    --txt:rgba(255,255,255,.66); --txt-soft:rgba(255,255,255,.48);
    --dim:rgba(255,255,255,.35); --line:rgba(255,255,255,.12);
    --card:rgba(255,255,255,.035);
  }
  body{
    font-family:"HelveticaNeue", Helvetica, Arial, sans-serif;
    color:var(--txt); font-size:13.5px; line-height:1.55;
  }

  .draftband{ font-family:"HelveticaNeue",Helvetica,sans-serif; font-weight:700; font-size:10.5px;
    letter-spacing:2px; text-transform:uppercase; color:var(--orange);
    background:rgba(249,115,22,.10); border:1px dashed rgba(249,115,22,.55); padding:6px 12px;
    text-align:center; margin-bottom:12px; }

  /* ---- header ---- */
  .top{ display:flex; justify-content:space-between; align-items:center; }
  .top-left .priv{ font-weight:700; font-size:11px; letter-spacing:2.5px; color:var(--blue-light); }
  .top-left .loc{ font-size:9.5px; letter-spacing:1.3px; color:var(--dim); margin-top:4px; }
  .brand{ display:flex; align-items:center; gap:7px; }
  .brand .bars{ display:inline-block; width:30px; white-space:nowrap; flex:none; }
  .brand .bars i{ display:inline-block; vertical-align:bottom; width:4.5px; margin-right:2.5px;
    background:var(--blue); opacity:.85; border-radius:1px 1px 0 0; }
  .brand .bars i.b1{ height:17px; } .brand .bars i.b2{ height:13px; }
  .brand .bars i.b3{ height:8px; }  .brand .bars i.b4{ height:3.5px; }
  .brand .name{ font-family:"Syne", Arial, sans-serif; font-weight:800; font-size:20px; line-height:1;
    letter-spacing:-.5px; color:var(--white); }
  .brand .name span{ color:var(--blue-light); }

  .cli-ribbon{ display:flex; align-items:center; gap:7px; margin-top:14px; }
  .cli-ribbon .swz{ display:inline-flex; gap:3px; }
  .cli-ribbon .swz b{ width:14px; height:7px; border-radius:1px; display:block; }
  .cli-ribbon .swz .g1{ background:var(--blue); }
  .cli-ribbon .swz .g2{ background:var(--green); }
  .cli-ribbon .swz .g3{ background:var(--orange); }
  .cli-ribbon .mtxt{ font-weight:700; font-size:9.5px; letter-spacing:1.6px; color:var(--txt-soft); text-transform:uppercase; }

  .docline{ font-weight:700; font-size:11.5px; letter-spacing:2.4px; color:var(--blue-light); margin-top:16px;
    display:flex; align-items:center; gap:10px; }
  .docline::after{ content:""; width:26px; height:1.5px; background:var(--blue); display:inline-block; }

  h1.title{ font-weight:700; font-size:31px; letter-spacing:-.7px; line-height:1.1; margin-top:8px; color:var(--white); }
  h1.title em{ font-style:italic; font-weight:400; color:var(--blue-light); }
  .sub{ font-size:15px; color:var(--txt); line-height:1.58; margin-top:10px; max-width:97%; }
  .sub b{ color:var(--white); }

  /* ---- parties ---- */
  .parties{ display:flex; gap:34px; margin-top:16px; }
  .party{ flex:1; background:var(--card); border:1px solid rgba(255,255,255,.07); padding:12px 14px 13px; }
  .pnum{ font-weight:700; font-size:10.5px; color:var(--blue-light); letter-spacing:1px; }
  .plabel{ font-weight:700; font-size:11px; letter-spacing:2.4px; color:var(--blue-light); display:flex;
    align-items:center; gap:9px; margin-top:2px; }
  .plabel::after{ content:""; flex:1; height:1px; background:var(--line); }
  .pname{ font-weight:700; font-size:17px; margin-top:10px; letter-spacing:-.2px; color:var(--white); }
  .psub{ font-style:italic; font-size:13px; color:var(--txt-soft); margin-top:3px; line-height:1.4; }
  .frow{ display:flex; margin-top:5px; font-size:11.5px; }
  .frow:first-of-type{ margin-top:10px; }
  .frow .k{ width:78px; flex:none; color:var(--dim); letter-spacing:.6px; font-size:10.5px; text-transform:uppercase; padding-top:1px; }
  .frow .v{ color:var(--txt); }

  .block-label{ font-weight:700; font-size:11.5px; letter-spacing:2.4px; color:var(--blue-light);
    display:flex; align-items:center; gap:10px; margin-top:15px; text-transform:uppercase; }
  .block-label::after{ content:""; flex:1; height:1px; background:var(--line); }
  .block-label.dash::after{ flex:none; width:24px; height:1.5px; background:var(--blue); }
  .sechead{ margin-top:24px; padding-bottom:5px; }

  .concept p{ font-size:14.5px; line-height:1.62; color:var(--txt); text-align:justify; margin-top:9px; }
  .concept p .b{ color:var(--blue-light); font-weight:700; }
  .concept p b{ color:var(--white); }

  /* ---- chips ---- */
  .cad{ display:inline-block; font-weight:700; font-size:9px; letter-spacing:.8px; padding:2.5px 8px;
    border-radius:3px; white-space:nowrap; text-transform:uppercase; }
  .cad.base{ color:var(--blue-light); background:rgba(0,71,255,.14); border:1px solid rgba(61,111,255,.5); }
  .cad.opt{ color:var(--white); border:1px solid rgba(255,255,255,.28); }
  .cad.fase{ color:var(--dim); border:1px solid rgba(255,255,255,.14); }

  /* ---- modules ---- */
  .module{ break-inside:avoid; margin-top:13px; }
  .module .mh{ display:block; overflow:hidden; }
  .module .mh .mnum{ font-weight:700; font-size:11.5px; color:var(--blue-light); letter-spacing:.5px; margin-right:7px; }
  .module .mh .mname{ font-weight:700; font-size:15.5px; color:var(--white); letter-spacing:-.2px; }
  .module .mh .cad{ float:right; margin-left:12px; margin-top:2px; }
  .module p{ font-size:14px; line-height:1.58; color:var(--txt); text-align:justify; margin-top:5px; }
  .module p b{ color:var(--white); }
  .module p .b{ color:var(--blue-light); font-weight:700; }

  /* ---- amount ---- */
  .amount{ display:flex; justify-content:space-between; align-items:flex-end; margin-top:9px; }
  .amount .words{ font-style:italic; font-size:14px; color:var(--txt-soft); max-width:48%; }
  .amount .num{ text-align:right; line-height:1; }
  .amount .num .cop{ font-size:12.5px; color:var(--txt-soft); vertical-align:top; letter-spacing:1.5px; margin-right:5px; }
  .amount .num .big{ font-weight:700; font-size:38px; color:var(--blue-light); letter-spacing:-1px; }
  .amount .num .usd{ display:block; font-size:10.5px; color:var(--dim); margin-top:6px; letter-spacing:.6px; }

  /* ---- detail table ---- */
  table.det{ width:100%; border-collapse:collapse; margin-top:11px; }
  table.det th{ font-weight:700; font-size:10px; letter-spacing:1.6px; color:var(--dim);
    text-transform:uppercase; padding:0 0 9px; border-bottom:1px solid var(--line); text-align:left; }
  table.det th.r{ text-align:right; }
  table.det td{ padding:8px 0; border-bottom:1px solid var(--line); vertical-align:top; }
  td.desc .t{ font-weight:700; font-size:14.5px; color:var(--white); }
  td.desc .d{ font-size:12.5px; color:var(--txt-soft); line-height:1.5; margin-top:4px; }
  td.tag{ font-size:10.5px; color:var(--txt-soft); text-align:right; white-space:nowrap; padding-left:10px; padding-right:16px; letter-spacing:.4px; }
  td.val{ font-weight:700; font-size:14px; color:var(--white); text-align:right; padding-left:14px; white-space:nowrap; }
  td.desc .t span{ font-weight:700; font-size:9px; color:var(--blue-light); letter-spacing:1.2px; margin-left:6px; text-transform:uppercase; }
  tr.hl td{ background:rgba(0,71,255,.10); }
  tr.hl td:first-child{ padding-left:8px; }
  tr.hl td.val{ color:var(--blue-light); padding-right:8px; }

  .grid2{ display:flex; gap:34px; margin-top:12px; }
  .grid2 > div{ flex:1; }

  .gift-note{ margin-top:11px; background:rgba(74,222,128,.06); border-left:3px solid var(--green); padding:11px 14px; }
  .gift-note .nl{ font-weight:700; font-size:10.5px; letter-spacing:1.6px; color:var(--green); text-transform:uppercase; }
  .gift-note p{ font-size:13.5px; line-height:1.56; color:var(--txt); margin-top:6px; text-align:justify; }
  .gift-note p b{ color:var(--green); }

  .note{ margin-top:11px; background:rgba(0,71,255,.08); border-left:2.4px solid var(--blue); padding:10px 14px; }
  .note .nl{ font-weight:700; font-size:10.5px; letter-spacing:1.6px; color:var(--blue-light); text-transform:uppercase; }
  .note p{ font-size:13px; line-height:1.54; color:var(--txt); margin-top:6px; text-align:justify; }
  .note p b{ color:var(--white); }

  .frow.tight{ margin-top:7px; }
  .frow.tight:first-of-type{ margin-top:12px; }

  .signs{ display:flex; gap:34px; margin-top:18px; }
  .signs > div{ flex:1; padding-top:10px; border-top:1.5px solid rgba(255,255,255,.55); }
  .signs .sname{ font-weight:700; font-size:14.5px; color:var(--white); }
  .signs .scap{ font-size:10px; color:var(--dim); letter-spacing:.5px; margin-top:5px; text-transform:uppercase; }

  .footer{ margin-top:14px; padding-top:11px; border-top:1px solid var(--line); display:flex; justify-content:space-between; gap:30px; }
  .footer .notes{ font-size:9.5px; color:var(--dim); line-height:1.6; max-width:68%; }
  .footer .notes b{ color:var(--txt-soft); font-weight:700; }
  .footer .by{ font-size:10px; color:var(--dim); text-align:right; line-height:1.7; }
  .footer .by b{ color:var(--txt); font-weight:700; }

  .keep{ break-inside:avoid; }
</style>
</head>
<body>

  __DRAFTBAND__

  <div class="top">
    <div class="top-left">
      <div class="priv">PROPUESTA PRIVADA</div>
      <div class="loc">BOGOTÁ D.C. · COLOMBIA · __FECHA__</div>
    </div>
    <div class="brand">
      <span class="bars"><i class="b1"></i><i class="b2"></i><i class="b3"></i><i class="b4"></i></span>
      <span class="name">Ricardo<span>.</span>Ruiz</span>
    </div>
  </div>

  <div class="cli-ribbon">
    <span class="swz"><b class="g1"></b><b class="g2"></b><b class="g3"></b></span>
    <span class="mtxt">Hecha a la medida del Youth Climate Justice Fund</span>
  </div>

  <div class="docline">PROPUESTA T&Eacute;CNICA Y ECON&Oacute;MICA · IA OPERATIVA · 2026</div>
  <h1 class="title">El trabajo repetitivo a los flujos,<br><em>el criterio al equipo de trabajo</em></h1>
  <div class="sub">Un plan <b>por bloques</b> para llevar inteligencia artificial a los procesos del equipo de
    operaciones: se empieza por lo que m&aacute;s duele, cada pieza funciona sola, y el fondo decide hasta
    d&oacute;nde llegar &mdash; con <b>datos protegidos</b> y <b>huella ambiental medida</b>, como corresponde a un
    fondo de justicia clim&aacute;tica.</div>

  <div class="parties">
    <div class="party">
      <div class="pnum">01</div>
      <div class="plabel">CONSULTOR</div>
      <div class="pname">Ricardo Esteban Ruiz Castro</div>
      <div class="psub">Persona natural &middot; Consultor en datos, IA operativa y decisiones p&uacute;blicas</div>
      <div class="frow"><span class="k">SITIO</span><span class="v">ricardoruiz.co</span></div>
      <div class="frow"><span class="k">CIUDAD</span><span class="v">Bogot&aacute; D.C., Colombia</span></div>
      <div class="frow"><span class="k">CORREO</span><span class="v">hola@ricardoruiz.co</span></div>
    </div>
    <div class="party">
      <div class="pnum">02</div>
      <div class="plabel">CLIENTE</div>
      <div class="pname">Youth Climate Justice Fund</div>
      <div class="psub">Fondo filantr&oacute;pico &middot; justicia clim&aacute;tica juvenil &middot; equipo remoto global</div>
      <div class="frow"><span class="k">CONTACTO</span><span class="v">Tatiana Restrepo</span></div>
      <div class="frow"><span class="k">CARGO</span><span class="v">Finance &amp; Operations Manager</span></div>
      <div class="frow"><span class="k">SITIO</span><span class="v">ycjf.org</span></div>
    </div>
  </div>

  <div class="concept">
    <div class="block-label">QUI&Eacute;N LO CONSTRUYE</div>
    <p>Ricardo Ruiz es <b>consultor en datos e inteligencia artificial aplicada a la operaci&oacute;n</b>. Desde
      ricardoruiz.co construye los flujos que sostienen sus propias plataformas &mdash;procesamiento de millones de
      registros, asistentes de IA a la medida, tableros en vivo&mdash; sobre infraestructura ligera que un equipo
      peque&ntilde;o puede sostener solo. Ese mismo oficio es el que ofrece aqu&iacute;: mirar c&oacute;mo trabaja un
      equipo real y quitarle la parte repetitiva, sin cambiarle las herramientas que ya usa.</p>
  </div>

  <div class="concept">
    <div class="block-label">LO QUE ESCUCHAMOS</div>
    <p>YCJF mueve financiamiento a iniciativas juveniles de justicia clim&aacute;tica en decenas de pa&iacute;ses,
      con un equipo de <span class="b">13 personas distribuidas por el mundo</span> y en pleno crecimiento. La
      operaci&oacute;n diaria vive en <b>Google Workspace, Slack, Monday y Sheets</b> &mdash; y buena parte del
      seguimiento se hace a mano: cuando llega un grant nuevo, alguien abre el correo, lee el PDF y pasa los datos a
      una hoja de c&aacute;lculo. Cuando se renueva un contrato, se redacta otra vez el mismo correo. Nadie
      dise&ntilde;&oacute; esos procesos; se fueron acumulando mientras el fondo crec&iacute;a. Esta propuesta los
      ordena y les quita el trabajo repetitivo, uno por uno.</p>
  </div>

  <div class="concept">
    <div class="block-label">C&Oacute;MO FUNCIONA: UN PLAN POR BLOQUES</div>
    <p>No proponemos un megaproyecto. Proponemos un <span class="b">bloque base</span> &mdash;el diagn&oacute;stico,
      las reglas de juego y los dos primeros flujos funcionando&mdash; y un men&uacute; de <span class="b">bloques
      opcionales</span> con precio fijo, que el equipo escoge seg&uacute;n prioridad y presupuesto. Cada bloque
      funciona por s&iacute; solo y se entrega funcionando: al primer mes ya hay resultados sobre procesos reales,
      no diapositivas.</p>
  </div>

  <div class="block-label dash sechead">EL BLOQUE BASE &mdash; POR AQU&Iacute; SE EMPIEZA</div>

  <div class="module">
    <div class="mh"><span class="cad base">BLOQUE BASE</span><span class="mnum">00</span><span class="mname">Diagn&oacute;stico, reglas de juego y primeros flujos</span></div>
    <p>Dos a tres semanas de trabajo con el equipo: <b>entrevistas cortas</b> por rol, mapeo de los procesos reales
      (no los del organigrama) y auditor&iacute;a de c&oacute;mo se conectan Workspace, Slack, Monday y Sheets. De
      ah&iacute; sale un <b>mapa priorizado</b>: qu&eacute; automatizar ya, qu&eacute; despu&eacute;s, qu&eacute; no
      vale la pena. Incluye una <b>pol&iacute;tica de uso responsable de IA</b> para el fondo &mdash;qu&eacute;
      datos pueden tocar los modelos y cu&aacute;les no, y c&oacute;mo se mide la huella ambiental de cada
      flujo&mdash; y un <b>taller de arranque</b> con las 13 personas del staff.</p>
    <p>El base incluye adem&aacute;s los dos primeros flujos funcionando (m&oacute;dulos 01 y 02): la
      demostraci&oacute;n, sobre procesos propios, de que esto no es teor&iacute;a.</p>
  </div>

  <div class="module">
    <div class="mh"><span class="cad base">INCLUIDO EN BASE</span><span class="mnum">01</span><span class="mname">Grants entrantes &rarr; Google Sheets</span></div>
    <p>Llega el correo con el PDF del grant; el flujo lo lee, extrae <b>monto, financiador, fechas y
      condiciones</b>, agrega la fila a la hoja de seguimiento y avisa por Slack. Lo que hoy toma abrir, leer,
      copiar y pegar, pasa a ser un aviso de &laquo;ya qued&oacute;&raquo; &mdash; con la persona revisando, no
      transcribiendo. Cubre tambi&eacute;n las descargas peri&oacute;dicas de la plataforma del fiscal sponsor
      hacia Sheets.</p>
  </div>

  <div class="module">
    <div class="mh"><span class="cad base">INCLUIDO EN BASE</span><span class="mnum">02</span><span class="mname">Correos recurrentes de contratos</span></div>
    <p>El mismo correo que hoy se redacta a mano por cada contrato de staff hacia el fiscal sponsor pasa a
      dispararse desde Monday con los datos ya puestos: un click, revisar, enviar. Es el bloque m&aacute;s
      peque&ntilde;o de todos &mdash; y por eso va incluido: elimina una fricci&oacute;n semanal desde la primera
      semana.</p>
  </div>

  <div class="block-label dash sechead">LOS BLOQUES OPCIONALES &mdash; EL EQUIPO ESCOGE</div>

  <div class="module">
    <div class="mh"><span class="cad opt">BLOQUE OPCIONAL</span><span class="mnum">03</span><span class="mname">Reclutamiento asistido</span></div>
    <p>Un embudo ordenado para las convocatorias de personal: formulario de entrada, lectura autom&aacute;tica de
      hojas de vida y una <b>matriz comparable</b> contra los criterios del cargo, con res&uacute;menes por
      candidato. La IA organiza y compara; <b>las personas deciden</b> &mdash; y as&iacute; queda escrito en el
      dise&ntilde;o del flujo, porque en una organizaci&oacute;n de justicia el sesgo algor&iacute;tmico no es un
      detalle t&eacute;cnico sino una l&iacute;nea roja.</p>
  </div>

  <div class="module">
    <div class="mh"><span class="cad opt">BLOQUE OPCIONAL</span><span class="mnum">04</span><span class="mname">Planeaci&oacute;n anual colaborativa</span></div>
    <p>La construcci&oacute;n del plan del a&ntilde;o siguiente hoy depende de juntar voces dispersas. Este bloque
      recoge los insumos del equipo (formularios y Slack), los <b>agrupa por temas con IA</b> y entrega un borrador
      de necesidades y prioridades listo para discutir &mdash; m&aacute;s la facilitaci&oacute;n de la sesi&oacute;n
      donde se decide. La IA hace la s&iacute;ntesis pesada; la conversaci&oacute;n estrat&eacute;gica sigue siendo
      del equipo.</p>
  </div>

  <div class="module">
    <div class="mh"><span class="cad opt">BLOQUE OPCIONAL</span><span class="mnum">05</span><span class="mname">Evento de octubre (~100 personas)</span></div>
    <p>Registro e invitados, agenda, comunicaciones en varios idiomas, preguntas frecuentes automatizadas y
      seguimiento log&iacute;stico en Monday. Un evento de 100 personas organizado por un equipo peque&ntilde;o es,
      sobre todo, cientos de micro-tareas repetitivas: este bloque las convierte en flujos y deja al equipo
      libre para el contenido y la gente.</p>
  </div>

  <div class="module">
    <div class="mh"><span class="cad opt">BLOQUE OPCIONAL</span><span class="mnum">06</span><span class="mname">Copiloto de reuniones</span></div>
    <p>Notas autom&aacute;ticas de las reuniones de equipo, <b>compromisos que caen solos a Monday</b> y un resumen
      semanal en Slack. Para un equipo repartido en diez zonas horarias, el resumen que llega solo vale m&aacute;s
      que la reuni&oacute;n que hubo que perderse.</p>
  </div>

  <div class="module">
    <div class="mh"><span class="cad fase">FASE FUTURA</span><span class="mnum">07</span><span class="mname">Triaje de aplicaciones (Submittable &middot; 7 idiomas)</span></div>
    <p>El lugar donde m&aacute;s horas se queman en todo el fondo: la revisi&oacute;n de cientos de aplicaciones en
      &aacute;rabe, ingl&eacute;s, franc&eacute;s, hindi, portugu&eacute;s, espa&ntilde;ol y suajili. Un flujo que
      verifique elegibilidad, resuma cada aplicaci&oacute;n en una p&aacute;gina est&aacute;ndar <b>en el idioma de
      cada comit&eacute; regional</b> y deje a los comit&eacute;s decidir sobre material comparable. No hace parte
      de esta propuesta &mdash; se dimensiona con el equipo de grants cuando el fondo quiera dar ese paso.</p>
  </div>

  <div class="gift-note keep">
    <div class="nl">IA RESPONSABLE &mdash; DATOS PROTEGIDOS Y HUELLA MEDIDA</div>
    <p>YCJF trabaja con activistas j&oacute;venes en pa&iacute;ses donde el activismo clim&aacute;tico es riesgoso, y
      es un fondo clim&aacute;tico: ni los datos ni la energ&iacute;a son detalles. Por eso todos los flujos se
      dise&ntilde;an con dos reglas fijas: <b>los datos sensibles no salen hacia servicios de terceros sin
      control</b> (la informaci&oacute;n se procesa en infraestructura propia o se anonimiza antes de tocar un
      modelo), y cada flujo usa <b>el modelo m&aacute;s peque&ntilde;o que resuelva la tarea</b>, con su consumo
      estimado documentado. Una automatizaci&oacute;n que ahorra horas de trabajo suele tener una huella neta menor
      que el proceso manual que reemplaza &mdash; y aqu&iacute; eso no se afirma: se mide.</p>
  </div>

  <div class="note keep">
    <div class="nl">FRONTERA DE ALCANCE &mdash; EL FISCAL SPONSOR NO SE TOCA</div>
    <p>Los procesos que corren por las plataformas del fiscal sponsor &mdash;contrataci&oacute;n de consultores,
      facturaci&oacute;n y pagos&mdash; ya est&aacute;n automatizados por ellos y <b>quedan expl&iacute;citamente
      fuera del alcance</b>: no se puede (ni conviene) automatizar sistemas ajenos. Esta consultor&iacute;a trabaja
      del lado YCJF: Google Workspace, Slack, Monday, Sheets y las conexiones entre ellos.</p>
  </div>

  <div class="block-label dash keep">INVERSI&Oacute;N</div>
  <div class="amount keep">
    <div class="words">Bloque base &mdash; diagn&oacute;stico, pol&iacute;tica de IA, taller y los dos primeros
      flujos funcionando. Los dem&aacute;s bloques se suman a decisi&oacute;n del equipo.</div>
    <div class="num"><span class="cop">BASE · PAGO &Uacute;NICO</span><span class="big">__BASE__</span>
      <span class="usd">bloques opcionales con precio fijo · retainer mensual opcional</span></div>
  </div>

  <table class="det keep">
    <thead>
      <tr><th>CONCEPTO</th><th class="r">TIPO</th><th class="r">INVERSI&Oacute;N</th></tr>
    </thead>
    <tbody>
      <tr class="hl">
        <td class="desc">
          <div class="t">Bloque base <span>INCLUYE M&Oacute;DULOS 01 Y 02</span></div>
          <div class="d">Diagn&oacute;stico y mapeo de procesos &middot; auditor&iacute;a del stack &middot;
            pol&iacute;tica de IA responsable y huella ambiental &middot; taller de arranque (13 personas) &middot;
            flujo de grants entrantes &rarr; Sheets &middot; correos recurrentes de contratos desde Monday.</div>
        </td>
        <td class="tag">Pago &uacute;nico</td>
        <td class="val">__BASE__</td>
      </tr>
      <tr>
        <td class="desc"><div class="t">03 &middot; Reclutamiento asistido</div>
          <div class="d">Embudo de candidatos + matriz comparable + guardas anti-sesgo por dise&ntilde;o.</div></td>
        <td class="tag">Bloque opcional</td>
        <td class="val">__B3__</td>
      </tr>
      <tr>
        <td class="desc"><div class="t">04 &middot; Planeaci&oacute;n anual colaborativa</div>
          <div class="d">Recolecci&oacute;n + s&iacute;ntesis con IA + facilitaci&oacute;n de la sesi&oacute;n de decisi&oacute;n.</div></td>
        <td class="tag">Bloque opcional</td>
        <td class="val">__B4__</td>
      </tr>
      <tr>
        <td class="desc"><div class="t">05 &middot; Evento de octubre</div>
          <div class="d">Registro, agenda, comunicaciones multiling&uuml;es, FAQ y log&iacute;stica en Monday.</div></td>
        <td class="tag">Bloque opcional</td>
        <td class="val">__B5__</td>
      </tr>
      <tr>
        <td class="desc"><div class="t">06 &middot; Copiloto de reuniones</div>
          <div class="d">Notas autom&aacute;ticas, compromisos a Monday, resumen semanal en Slack.</div></td>
        <td class="tag">Bloque opcional</td>
        <td class="val">__B6__</td>
      </tr>
      <tr>
        <td class="desc"><div class="t">Soporte e iteraci&oacute;n <span>RETAINER</span></div>
          <div class="d">Ajustes a los flujos vivos, automatizaciones peque&ntilde;as nuevas, acompa&ntilde;amiento
            al equipo. Los flujos mejoran con el uso; este retainer es lo que los mantiene afinados.</div></td>
        <td class="tag">Mensual</td>
        <td class="val">&nbsp;&nbsp;&nbsp;&nbsp;__RET__ /mes</td>
      </tr>
      <tr>
        <td class="desc"><div class="t">07 &middot; Triaje Submittable (7 idiomas)</div>
          <div class="d">Se dimensiona con el equipo de grants cuando el fondo decida dar el paso.</div></td>
        <td class="tag">Fase futura</td>
        <td class="val">__F2__</td>
      </tr>
    </tbody>
  </table>

  <div class="grid2 keep">
    <div>
      <div class="block-label">CONDICIONES</div>
      <div class="frow tight"><span class="k">MODALIDAD</span><span class="v">100% remoto &middot; equipo global</span></div>
      <div class="frow tight"><span class="k">FACTURA</span><span class="v">Invoice en USD &middot; v&iacute;a proceso del fiscal sponsor</span></div>
      <div class="frow tight"><span class="k">INICIO</span><span class="v">Base ~3 semanas &middot; flujos 01-02 al 1.er mes</span></div>
      <div class="frow tight"><span class="k">BLOQUES</span><span class="v">Se contratan cuando el equipo decida</span></div>
      <div class="frow tight"><span class="k">RETAINER</span><span class="v">Cancelable con 15 d&iacute;as de aviso</span></div>
    </div>
    <div>
      <div class="block-label">LO QUE QUEDA EN CASA</div>
      <div class="frow tight"><span class="k">C&Oacute;DIGO</span><span class="v">Documentado y de propiedad de YCJF</span></div>
      <div class="frow tight"><span class="k">ACCESOS</span><span class="v">En cuentas del fondo, no del consultor</span></div>
      <div class="frow tight"><span class="k">CAPACIDAD</span><span class="v">El equipo aprende a operar cada flujo</span></div>
      <div class="frow tight"><span class="k">POL&Iacute;TICA IA</span><span class="v">Documento propio del fondo, reutilizable</span></div>
      <div class="frow tight"><span class="k">SALIDA</span><span class="v">Nada deja de funcionar si termina el contrato</span></div>
    </div>
  </div>

  <div class="signs keep">
    <div>
      <div class="sname">Ricardo Esteban Ruiz Castro</div>
      <div class="scap">CONSULTOR &middot; ricardoruiz.co &middot; BOGOT&Aacute; D.C.</div>
    </div>
    <div>
      <div class="sname">Aceptaci&oacute;n del cliente</div>
      <div class="scap">YOUTH CLIMATE JUSTICE FUND &middot; FECHA: ____ / ____ / 2026</div>
    </div>
  </div>

  <div class="footer">
    <div class="notes"><b>Validez de la oferta:</b> 30 d&iacute;as calendario. Cifras en d&oacute;lares
      estadounidenses. Documento privado, sin valor tributario hasta la emisi&oacute;n del invoice
      correspondiente.</div>
    <div class="by">Preparado por<br><b>RICARDO ESTEBAN RUIZ CASTRO</b><br>ricardoruiz.co</div>
  </div>

</body>
</html>"""

HTML_DOC = (HTML_DOC
            .replace("__SYNE__", F_SYNE)
            .replace("__HNB__", F_HN_B)
            .replace("__HNI__", F_HN_I)
            .replace("__HNM__", F_HN_M)
            .replace("__HNL__", F_HN_L)
            .replace("__HN__", F_HN)
            .replace("__DRAFTBAND__", DRAFT_BAND)
            .replace("__FECHA__", FECHA)
            .replace("__BASE__", BASE_USD)
            .replace("__B3__", B_RECLUT)
            .replace("__B4__", B_PLANEA)
            .replace("__B5__", B_EVENTO)
            .replace("__B6__", B_REUNION)
            .replace("__RET__", RETAINER_USD)
            .replace("__F2__", FASE2))


def build():
    HTML(string=HTML_DOC).write_pdf(OUT)
    return os.path.getsize(OUT)


if __name__ == "__main__":
    n = build()
    print(f"PDF generado: {OUT}  ({n/1024:.1f} KB)")
