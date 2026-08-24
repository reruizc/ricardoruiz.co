#!/usr/bin/env python3
"""
Propuesta técnica y económica — REDISEÑO DEL SITIO WEB de Mujeres por la Democracia.
Cliente: Fundación Mujeres por la Democracia (MxD) · contacto Laura Herrera (directora).

SISTEMA VISUAL v2 EN CLARO (pedido de Ricardo, ago-2026): mismo chasis de
tools/build-propuesta-ycjf/build.py pero INVERTIDO a papel #f6f5f1 con tinta
#10131a. Azul #0047FF (acento y monto), azul profundo #0038cc para rótulos
pequeños, naranja #c2410c para el recuadro de advertencia. Helvetica Neue
embebida (fonts/*.woff2) para TODO, Syne SOLO en el wordmark, CERO mono. Logo =
4 barras descendentes (20/15/9/4) + "Ricardo.Ruiz" con el punto en azul.

⚠️ NADA de texto en tono claro: en esta versión NO puede quedar un solo
rgba(255,255,255,...) sobre el papel. Las variables se llaman --ink / --blue-deep
justamente para que nadie reintroduzca un --white de texto por inercia.

El documento es de Ricardo → conserva el azul v2 como acento. La paleta de MxD
(vinotinto #5E003F / amarillo #F9E254 / lila #EEBCFF, del MPLD_BrandSheet.pdf)
aparece solo como muestra dentro del módulo 00, que es donde se propone la
dirección de diseño del sitio.

Alcance: lo que pidió Laura (WhatsApp 30-jul-2026) va COMPLETO en el bloque base
—Decálogo · Informes de gestión · Contacto de correo · Notas de prensa—; las
encuestas van como bloque opcional con la advertencia de fricción escrita, que
fue la reserva que ella misma puso.

Estado del sitio hoy (verificado jul-2026): corre sobre GoDaddy Website Builder,
tres secciones (Quiénes somos · En qué creemos · Qué hacemos), formulario de
contacto que pide nombre, apellido, correo, celular y redes, enlaces a Instagram
y X, página de Régimen Tributario Especial. /blog responde 404.

DRAFT=True agrega la banda "BORRADOR INTERNO". Cambiar a False (y fijar precios)
antes de enviar a Laura.

Salida: Propuestas/Propuesta-MxD-Sitio-Web.pdf
"""
import os
import datetime
from weasyprint import HTML

ROOT = "/Users/ricardoruiz/ricardoruiz.co"
OUT = os.path.join(ROOT, "Propuestas", "Propuesta-MxD-Sitio-Web.pdf")

# --- Estado del documento ---------------------------------------------------
DRAFT = False  # False = versión para enviar (quita banda de borrador)

# --- Cifras de REFERENCIA (definir antes de enviar) -------------------------
BASE_COP   = "$ 1.800.000"   # sitio completo con las 4 piezas pedidas, pago único
B_ENCUESTA = "$ 600.000"     # bloque opcional: encuestas
B_MEDIOS   = "$ 500.000"     # bloque opcional: "En los medios" (alimentado por Radar Mujer)
B_BOLETIN  = "$ 500.000"     # bloque opcional: boletín + base de aliadas

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
    background: #f6f5f1;
    @bottom-left {
      content: "Ricardo.Ruiz  ·  ricardoruiz.co  ·  Documento privado";
      font-family: "HelveticaNeue", Helvetica, sans-serif;
      font-size: 7pt; color: #6f747c; letter-spacing: .6px;
    }
    @bottom-right {
      content: "Pág. " counter(page) " / " counter(pages);
      font-family: "HelveticaNeue", Helvetica, sans-serif;
      font-size: 7pt; color: #6f747c;
    }
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  :root{
    /* TEMA CLARO — papel #f6f5f1, tinta #10131a. No introducir colores claros de texto. */
    --ink:#10131a; --blue:#0047FF; --blue-deep:#0038cc;
    --green:#15803d; --orange:#c2410c;
    --txt:rgba(16,19,26,.78); --txt-soft:rgba(16,19,26,.62);
    --dim:rgba(16,19,26,.50); --line:rgba(16,19,26,.15);
    --card:rgba(16,19,26,.030);
  }
  body{
    font-family:"HelveticaNeue", Helvetica, Arial, sans-serif;
    color:var(--txt); font-size:13.5px; line-height:1.55;
  }

  .draftband{ font-family:"HelveticaNeue",Helvetica,sans-serif; font-weight:700; font-size:10.5px;
    letter-spacing:2px; text-transform:uppercase; color:var(--orange);
    background:rgba(194,65,12,.07); border:1px dashed rgba(194,65,12,.45); padding:6px 12px;
    text-align:center; margin-bottom:12px; }

  /* ---- header ---- */
  .top{ display:flex; justify-content:space-between; align-items:center; }
  .top-left .priv{ font-weight:700; font-size:11px; letter-spacing:2.5px; color:var(--blue-deep); }
  .top-left .loc{ font-size:9.5px; letter-spacing:1.3px; color:var(--dim); margin-top:4px; }
  .brand{ display:flex; align-items:center; gap:7px; }
  .brand .bars{ display:inline-block; width:30px; white-space:nowrap; flex:none; }
  .brand .bars i{ display:inline-block; vertical-align:bottom; width:4.5px; margin-right:2.5px;
    background:var(--blue); opacity:.85; border-radius:1px 1px 0 0; }
  .brand .bars i.b1{ height:17px; } .brand .bars i.b2{ height:13px; }
  .brand .bars i.b3{ height:8px; }  .brand .bars i.b4{ height:3.5px; }
  .brand .name{ font-family:"Syne", Arial, sans-serif; font-weight:800; font-size:20px; line-height:1;
    letter-spacing:-.5px; color:var(--ink); }
  .brand .name span{ color:var(--blue-deep); }

  .cli-ribbon{ display:flex; align-items:center; gap:7px; margin-top:14px; }
  .cli-ribbon .swz{ display:inline-flex; gap:3px; }
  .cli-ribbon .swz b{ width:14px; height:7px; border-radius:1px; display:block; }
  .cli-ribbon .swz .g1{ background:var(--blue); }
  .cli-ribbon .swz .g2{ background:var(--green); }
  .cli-ribbon .swz .g3{ background:var(--orange); }
  .cli-ribbon .mtxt{ font-weight:700; font-size:9.5px; letter-spacing:1.6px; color:var(--txt-soft); text-transform:uppercase; }

  .docline{ font-weight:700; font-size:11.5px; letter-spacing:2.4px; color:var(--blue-deep); margin-top:16px;
    display:flex; align-items:center; gap:10px; }
  .docline::after{ content:""; width:26px; height:1.5px; background:var(--blue); display:inline-block; }

  h1.title{ font-weight:700; font-size:31px; letter-spacing:-.7px; line-height:1.1; margin-top:8px; color:var(--ink); }
  h1.title em{ font-style:italic; font-weight:400; color:var(--blue-deep); }
  .sub{ font-size:15px; color:var(--txt); line-height:1.58; margin-top:10px; max-width:97%; }
  .sub b{ color:var(--ink); }

  /* ---- parties ---- */
  .parties{ display:flex; gap:34px; margin-top:16px; }
  .party{ flex:1; background:var(--card); border:1px solid rgba(16,19,26,.11); padding:12px 14px 13px; }
  .pnum{ font-weight:700; font-size:10.5px; color:var(--blue-deep); letter-spacing:1px; }
  .plabel{ font-weight:700; font-size:11px; letter-spacing:2.4px; color:var(--blue-deep); display:flex;
    align-items:center; gap:9px; margin-top:2px; }
  .plabel::after{ content:""; flex:1; height:1px; background:var(--line); }
  .pname{ font-weight:700; font-size:17px; margin-top:10px; letter-spacing:-.2px; color:var(--ink); }
  .psub{ font-style:italic; font-size:13px; color:var(--txt-soft); margin-top:3px; line-height:1.4; }
  .frow{ display:flex; margin-top:5px; font-size:11.5px; }
  .frow:first-of-type{ margin-top:10px; }
  .frow .k{ width:78px; flex:none; color:var(--dim); letter-spacing:.6px; font-size:10.5px; text-transform:uppercase; padding-top:1px; }
  .frow .v{ color:var(--txt); }

  .block-label{ font-weight:700; font-size:11.5px; letter-spacing:2.4px; color:var(--blue-deep);
    display:flex; align-items:center; gap:10px; margin-top:15px; text-transform:uppercase; }
  .block-label::after{ content:""; flex:1; height:1px; background:var(--line); }
  .block-label.dash::after{ flex:none; width:24px; height:1.5px; background:var(--blue); }
  .sechead{ margin-top:20px; padding-bottom:5px; }

  .concept p{ font-size:14.5px; line-height:1.6; color:var(--txt); text-align:justify; margin-top:8px; }
  .concept p .b{ color:var(--blue-deep); font-weight:700; }
  .concept p b{ color:var(--ink); }

  /* ---- chips ---- */
  .cad{ display:inline-block; font-weight:700; font-size:9px; letter-spacing:.8px; padding:2.5px 8px;
    border-radius:3px; white-space:nowrap; text-transform:uppercase; }
  .cad.base{ color:var(--blue-deep); background:rgba(0,71,255,.08); border:1px solid rgba(0,71,255,.38); }
  .cad.opt{ color:var(--ink); border:1px solid rgba(16,19,26,.30); }
  .cad.fase{ color:var(--dim); border:1px solid rgba(16,19,26,.16); }

  /* ---- modules ---- */
  .module{ break-inside:avoid; margin-top:11px; }
  .module .mh{ display:block; overflow:hidden; }
  .module .mh .mnum{ font-weight:700; font-size:11.5px; color:var(--blue-deep); letter-spacing:.5px; margin-right:7px; }
  .module .mh .mname{ font-weight:700; font-size:15.5px; color:var(--ink); letter-spacing:-.2px; }
  .module .mh .cad{ float:right; margin-left:12px; margin-top:2px; }
  .module p{ font-size:14px; line-height:1.58; color:var(--txt); text-align:justify; margin-top:5px; }
  .module p b{ color:var(--ink); }
  .module p .b{ color:var(--blue-deep); font-weight:700; }

  /* ---- paleta MxD (solo módulo 00) ---- */
  .pal{ display:flex; align-items:center; gap:9px; margin-top:9px; }
  .pal .sw{ display:flex; align-items:center; gap:5px; font-size:10px; color:var(--txt-soft); letter-spacing:.4px; }
  .pal .sw i{ display:block; width:26px; height:11px; border-radius:2px; border:1px solid rgba(16,19,26,.28); }

  /* ---- amount ---- */
  .amount{ display:flex; justify-content:space-between; align-items:flex-end; margin-top:9px; }
  .amount .words{ font-style:italic; font-size:14px; color:var(--txt-soft); max-width:48%; }
  .amount .num{ text-align:right; line-height:1; }
  .amount .num .cop{ display:block; font-size:12px; color:var(--txt-soft); letter-spacing:1.5px;
    margin-bottom:7px; white-space:nowrap; }
  .amount .num .big{ font-weight:700; font-size:35px; color:var(--blue-deep); letter-spacing:-1px;
    white-space:nowrap; }
  .amount .num .usd{ display:block; font-size:10.5px; color:var(--dim); margin-top:6px; letter-spacing:.6px; }

  /* ---- detail table ---- */
  table.det{ width:100%; border-collapse:collapse; margin-top:11px; }
  table.det th{ font-weight:700; font-size:10px; letter-spacing:1.6px; color:var(--dim);
    text-transform:uppercase; padding:0 0 9px; border-bottom:1px solid var(--line); text-align:left; }
  table.det th.r{ text-align:right; }
  table.det td{ padding:8px 0; border-bottom:1px solid var(--line); vertical-align:top; }
  td.desc .t{ font-weight:700; font-size:14.5px; color:var(--ink); }
  td.desc .d{ font-size:12.5px; color:var(--txt-soft); line-height:1.5; margin-top:4px; }
  td.tag{ font-size:10.5px; color:var(--txt-soft); text-align:right; white-space:nowrap; padding-left:10px; padding-right:16px; letter-spacing:.4px; }
  td.val{ font-weight:700; font-size:14px; color:var(--ink); text-align:right; padding-left:14px; white-space:nowrap; }
  td.desc .t span{ font-weight:700; font-size:9px; color:var(--blue-deep); letter-spacing:1.2px; margin-left:6px; text-transform:uppercase; }
  tr.hl td{ background:rgba(0,71,255,.07); }
  tr.hl td:first-child{ padding-left:8px; }
  tr.hl td.val{ color:var(--blue-deep); padding-right:8px; }

  .grid2{ display:flex; gap:34px; margin-top:12px; }
  .grid2 > div{ flex:1; }

  .gift-note{ margin-top:11px; background:rgba(21,128,61,.07); border-left:3px solid var(--green); padding:11px 14px; }
  .gift-note .nl{ font-weight:700; font-size:10.5px; letter-spacing:1.6px; color:var(--green); text-transform:uppercase; }
  .gift-note p{ font-size:13.5px; line-height:1.56; color:var(--txt); margin-top:6px; text-align:justify; }
  .gift-note p b{ color:var(--green); }

  .warn-note{ margin-top:11px; background:rgba(194,65,12,.06); border-left:3px solid var(--orange); padding:11px 14px; }
  .warn-note .nl{ font-weight:700; font-size:10.5px; letter-spacing:1.6px; color:var(--orange); text-transform:uppercase; }
  .warn-note p{ font-size:13.5px; line-height:1.56; color:var(--txt); margin-top:6px; text-align:justify; }
  .warn-note p b{ color:var(--ink); }
  .warn-note p .o{ color:var(--orange); font-weight:700; }

  .note{ margin-top:11px; background:rgba(0,71,255,.05); border-left:2.4px solid var(--blue); padding:10px 14px; }
  .note .nl{ font-weight:700; font-size:10.5px; letter-spacing:1.6px; color:var(--blue-deep); text-transform:uppercase; }
  .note p{ font-size:13px; line-height:1.54; color:var(--txt); margin-top:6px; text-align:justify; }
  .note p b{ color:var(--ink); }

  .frow.tight{ margin-top:7px; }
  .frow.tight:first-of-type{ margin-top:12px; }

  .signs{ display:flex; gap:34px; margin-top:15px; }
  .signs > div{ flex:1; padding-top:10px; border-top:1.5px solid rgba(16,19,26,.58); }
  .signs .sname{ font-weight:700; font-size:14.5px; color:var(--ink); }
  .signs .scap{ font-size:10px; color:var(--dim); letter-spacing:.5px; margin-top:5px; text-transform:uppercase; }

  .footer{ margin-top:12px; padding-top:10px; border-top:1px solid var(--line); display:flex; justify-content:space-between; gap:30px; }
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
    <span class="mtxt">Hecha a la medida de Mujeres por la Democracia</span>
  </div>

  <div class="docline">PROPUESTA TÉCNICA Y ECONÓMICA · SITIO WEB · 2026</div>
  <h1 class="title">Un sitio que muestre lo que la fundación<br><em>ya está haciendo</em></h1>
  <div class="sub">Rediseño completo de <b>mujeresporlademocracia.org</b> alrededor de cuatro piezas que hoy no
    existen o están dispersas: el <b>Decálogo</b>, los <b>informes de gestión</b>, las <b>notas de prensa</b> y un
    <b>contacto que llegue al correo correcto</b>. Con un panel simple para que el equipo publique sin depender
    de nadie.</div>

  <div class="parties">
    <div class="party">
      <div class="pnum">01</div>
      <div class="plabel">CONSULTOR</div>
      <div class="pname">Ricardo Esteban Ruiz Castro</div>
      <div class="psub">Persona natural · Consultor en datos, plataformas y decisiones públicas</div>
      <div class="frow"><span class="k">SITIO</span><span class="v">ricardoruiz.co</span></div>
      <div class="frow"><span class="k">CIUDAD</span><span class="v">Bogotá D.C., Colombia</span></div>
      <div class="frow"><span class="k">CORREO</span><span class="v">hola@ricardoruiz.co</span></div>
    </div>
    <div class="party">
      <div class="pnum">02</div>
      <div class="plabel">CLIENTE</div>
      <div class="pname">Mujeres por la Democracia</div>
      <div class="psub">Fundación independiente · investigación, formación e incidencia por la participación
        política de las mujeres</div>
      <div class="frow"><span class="k">CONTACTO</span><span class="v">Laura Herrera</span></div>
      <div class="frow"><span class="k">CARGO</span><span class="v">Directora</span></div>
      <div class="frow"><span class="k">SITIO</span><span class="v">mujeresporlademocracia.org</span></div>
    </div>
  </div>

  <div class="concept">
    <div class="block-label">QUIÉN LO CONSTRUYE</div>
    <p>Ricardo Ruiz construye <b>plataformas de datos y sitios que aguantan tráfico real</b>. Desde ricardoruiz.co
      opera tableros electorales que procesan millones de registros, herramientas para equipos de campaña y
      observatorios temáticos —todo sobre infraestructura ligera, rápida y barata de sostener. Ya conoce a la
      fundación por dentro: el trabajo previo con MxD parte del mismo criterio que se aplica aquí, que el sitio
      cuente <b>lo que la organización hace, con evidencia y sin adornos</b>.</p>
  </div>

  <div class="concept">
    <div class="block-label">DÓNDE ESTÁ EL SITIO HOY</div>
    <p>La página actual corre sobre un <b>constructor genérico de GoDaddy</b> y resuelve lo básico: tres secciones
      —quiénes somos, en qué creemos, qué hacemos—, un formulario de contacto y los enlaces a redes. Sirvió para
      existir en internet, pero <span class="b">no tiene dónde poner lo que la fundación produce</span>: la sección
      de blog no responde, las notas de prensa no tienen lugar propio y el Decálogo —que es la carta de identidad
      de MxD— no aparece como pieza destacada. Los <b>informes de gestión sí existen</b>, pero viven dentro de la
      página del Régimen Tributario Especial, en una lista de once archivos junto al RUT, los estatutos y los
      formatos 2530 y 2531: cumplen ante la DIAN, pero <b>nadie los va a encontrar ahí</b>. Y el formulario pide
      celular y redes sociales antes de dejar escribir: más fricción de la que aguanta un primer contacto.</p>
    <p>La diferencia entre una organización que <b>parece</b> activa y una que <b>demuestra</b> que lo es cabe en
      cuatro páginas bien hechas. Eso es lo que propone este documento.</p>
  </div>

  <div class="concept">
    <div class="block-label">CÓMO FUNCIONA: UN SITIO Y UN PANEL</div>
    <p>Se entregan dos cosas. Un <span class="b">sitio propio</span>, hecho a la medida de la identidad de MxD, que
      carga rápido en celular y se puede citar página por página. Y un <span class="b">panel de publicación</span>
      para que el equipo suba un informe, publique una nota de prensa o corrija un texto <b>sin escribir una línea
      de código y sin pedirle permiso a nadie</b>. Ese es el punto: que el sitio no vuelva a quedarse quieto
      porque la persona que sabía manejarlo ya no está.</p>
  </div>

  <div class="block-label dash sechead">EL BLOQUE BASE — LAS CUATRO PIEZAS QUE PIDIÓ LA DIRECCIÓN</div>

  <div class="module">
    <div class="mh"><span class="cad base">BLOQUE BASE</span><span class="mnum">00</span><span class="mname">Diseño, arquitectura y panel de publicación</span></div>
    <p>Rediseño completo sobre la <b>identidad gráfica propia de MxD</b> —vinotinto, amarillo y lila del manual de
      marca—, con jerarquía pensada para celular primero, que es por donde entra la mayoría. Incluye la
      arquitectura de secciones, la migración de los textos que hoy existen, tiempos de carga por debajo de un
      segundo, <b>metadatos para que compartir un enlace en X o WhatsApp se vea bien</b>, y el panel desde el cual
      el equipo publica. Dos rondas de ajuste visual con la dirección antes de salir al aire.</p>
    <div class="pal">
      <span class="sw"><i style="background:#5E003F"></i>VINOTINTO</span>
      <span class="sw"><i style="background:#F9E254"></i>AMARILLO</span>
      <span class="sw"><i style="background:#EEBCFF"></i>LILA</span>
      <span class="sw"><i style="background:#FFFFFF"></i>BLANCO</span>
    </div>
  </div>

  <div class="module">
    <div class="mh"><span class="cad base">INCLUIDO EN BASE</span><span class="mnum">01</span><span class="mname">Decálogo</span></div>
    <p>Página propia, con los diez puntos numerados y legibles —no un PDF escondido en un enlace—. Cada punto tiene
      <b>su propia dirección web</b>, así que se puede citar y compartir suelto. Se entrega además en dos formatos
      que sirven para la calle: <b>PDF descargable</b> para imprimir y llevar a una reunión, y <b>una tarjeta por
      punto</b> lista para publicar en redes. El Decálogo deja de ser un documento y pasa a ser la sección que
      explica de una sola mirada qué defiende la fundación.</p>
  </div>

  <div class="module">
    <div class="mh"><span class="cad base">INCLUIDO EN BASE</span><span class="mnum">02</span><span class="mname">Informes de gestión</span></div>
    <p>Lo primero es <b>separar dos cosas que hoy están revueltas</b>. Los informes de gestión salen a sección
      propia: repositorio por año, con título, resumen de dos líneas y descarga directa, buscador por palabra y
      filtro por año, para que un periodista o una aliada encuentre en diez segundos lo que necesita. Cada informe
      registra <b>cuántas veces se descargó</b> —un dato pequeño que sirve para reportar alcance ante cooperantes—.</p>
    <p>Los otros documentos —estatutos, actas, RUT, estados financieros, formatos 2530 y 2531— se quedan en su
      página de <b>Régimen Tributario Especial</b>, pero ordenados por tipo y con fecha visible. Ahí la exigencia
      es legal y basta con cumplirla bien; el informe de gestión, en cambio, es <span class="b">material de
      incidencia</span> y merece vitrina propia. Hoy los dos están en la misma lista, y eso le quita fuerza al que
      sí se quiere mostrar.</p>
  </div>

  <div class="module">
    <div class="mh"><span class="cad base">INCLUIDO EN BASE</span><span class="mnum">03</span><span class="mname">Notas de prensa</span></div>
    <p>Sala de prensa con los comunicados de MxD, cada uno con fecha, título y dirección propia para que un medio
      pueda enlazarlo tal cual. Incluye un <b>kit de prensa</b> —logos en alta, fotografías, biografías cortas de
      las voceras y el contacto de prensa— porque la mitad de las veces lo que frena una nota es que el periodista
      no encuentra un logo decente a la hora de cierre. Publicar una nota nueva toma, desde el panel, menos de dos
      minutos.</p>
  </div>

  <div class="module">
    <div class="mh"><span class="cad base">INCLUIDO EN BASE</span><span class="mnum">04</span><span class="mname">Contacto por correo</span></div>
    <p>Un formulario corto —<b>nombre, correo y mensaje</b>— que llega al buzón de la fundación sin exponer la
      dirección a los robots de spam, con la autorización de tratamiento de datos que exige la <b>Ley 1581 de
      2012</b> escrita como corresponde. Cada mensaje queda además guardado en una hoja ordenada, así que ningún
      contacto se pierde en la bandeja de nadie. Se puede separar por motivo —prensa, alianzas, voluntariado— para
      que cada correo llegue directo a quien lo debe responder.</p>
  </div>

  <div class="block-label dash sechead">LOS BLOQUES OPCIONALES — LA FUNDACIÓN ESCOGE</div>

  <div class="module">
    <div class="mh"><span class="cad opt">BLOQUE OPCIONAL</span><span class="mnum">05</span><span class="mname">Encuestas y consultas a la comunidad</span></div>
    <p>Módulo para preguntarle algo a quien visita el sitio y mostrar el resultado en vivo. Se diseña en el formato
      de <b>menor fricción posible</b>: una sola pregunta, sin registro, sin correo, un toque y listo —y el
      resultado aparece de inmediato, que es lo único que hace que la gente responda—. Para consultas serias con
      su red de aliadas, una segunda modalidad <b>por enlace privado</b>, donde sí se pueden hacer más preguntas
      porque quien entra ya decidió participar. Ver la advertencia de abajo antes de decidir.</p>
  </div>

  <div class="warn-note keep">
    <div class="nl">SOBRE LAS ENCUESTAS — LA RESERVA DE LA DIRECCIÓN ESTÁ BIEN PUESTA</div>
    <p><span class="o">Uno.</span> Toda pregunta cuesta visitantes: un formulario de varias preguntas en la página
      principal pierde a la mayoría antes de la segunda. Por eso, si se hace, se hace de <b>una sola pregunta y
      anónima</b>; nunca como puerta de entrada al sitio.
      <span class="o">Dos.</span> Quien responde en una web se elige a sí mismo: eso <b>no es una muestra
      representativa</b> y no se puede comunicar como si lo fuera. Se publica como «lo que opina nuestra
      comunidad», con el número de respuestas a la vista —una organización que trabaja por la calidad de la
      democracia no puede ser laxa con sus propias cifras—.
      <span class="o">Tres.</span> Si la pregunta toca intención de voto o favorabilidad de candidatos, se entra en
      <b>terreno regulado</b> (Ley 2494 de 2025): ahí el diseño cambia y conviene revisarlo caso por caso.
      <b>Recomendación:</b> dejarlo para una segunda fase, cuando el sitio ya tenga público propio. El módulo queda
      cotizado para cuando lo quieran activar.</p>
  </div>

  <div class="module">
    <div class="mh"><span class="cad opt">BLOQUE OPCIONAL</span><span class="mnum">06</span><span class="mname">«En los medios» — alimentado por el monitor que ya opera</span></div>
    <p>Una sección que muestra automáticamente dónde se está hablando de MxD y de los temas de la fundación,
      tomando el flujo del <b>monitor de medios que ya está construido y funcionando</b>. No hay que recortar ni
      pegar nada: la sección se actualiza sola varias veces al día. Es la forma más barata de que el sitio se vea
      vivo aunque no haya comunicado nuevo esa semana.</p>
  </div>

  <div class="module">
    <div class="mh"><span class="cad opt">BLOQUE OPCIONAL</span><span class="mnum">07</span><span class="mname">Boletín y base de aliadas</span></div>
    <p>Suscripción por correo desde el sitio, con la base guardada en propiedad de la fundación —no dentro de una
      plataforma que después cobra por sacarla— y una plantilla de boletín con la identidad de MxD lista para
      enviar. Es lo que convierte a una visitante que pasó una vez en alguien a quien se le puede volver a
      hablar.</p>
  </div>

  <div class="note keep">
    <div class="nl">FRONTERA DE ALCANCE — QUÉ NO SE TOCA</div>
    <p>El <b>dominio y los correos corporativos actuales se conservan</b> tal como están: el sitio nuevo se conecta
      al mismo dominio, sin migrar cuentas de correo ni arriesgar la comunicación del equipo. No se administran las
      redes sociales ni se produce contenido: <b>los textos, informes y comunicados los entrega MxD</b>, y esta
      consultoría los estructura, los monta y deja el panel para que el equipo siga publicando por su cuenta.</p>
  </div>

  <div class="block-label dash keep">INVERSIÓN</div>
  <div class="amount keep">
    <div class="words">Bloque base — el sitio completo con las cuatro piezas pedidas y el panel de publicación.
      Los demás bloques se suman a decisión de la fundación.</div>
    <div class="num"><span class="cop">BASE · PAGO ÚNICO</span><span class="big">__BASE__</span>
      <span class="usd">los tres bloques opcionales tienen precio fijo</span></div>
  </div>

  <table class="det keep">
    <thead>
      <tr><th>CONCEPTO</th><th class="r">TIPO</th><th class="r">INVERSIÓN</th></tr>
    </thead>
    <tbody>
      <tr class="hl">
        <td class="desc">
          <div class="t">Bloque base <span>INCLUYE MÓDULOS 00 A 04</span></div>
          <div class="d">Diseño y arquitectura con la identidad de MxD · panel de publicación · Decálogo (web, PDF
            y tarjetas) · repositorio de informes de gestión con buscador · sala de prensa con kit descargable ·
            formulario de contacto con Ley 1581 · migración de los textos actuales · puesta al aire sobre el
            dominio existente.&nbsp;</div>
        </td>
        <td class="tag">Pago único</td>
        <td class="val">&nbsp;&nbsp;&nbsp;&nbsp;__BASE__</td>
      </tr>
      <tr>
        <td class="desc"><div class="t">05 · Encuestas y consultas</div>
          <div class="d">Micro-encuesta de una pregunta con resultado en vivo + consultas por enlace privado.</div></td>
        <td class="tag">Bloque opcional</td>
        <td class="val">__B5__</td>
      </tr>
      <tr>
        <td class="desc"><div class="t">06 · «En los medios»</div>
          <div class="d">Sección automática alimentada por el monitor de medios ya operativo.</div></td>
        <td class="tag">Bloque opcional</td>
        <td class="val">__B6__</td>
      </tr>
      <tr>
        <td class="desc"><div class="t">07 · Boletín y base de aliadas</div>
          <div class="d">Suscripción, base propia y plantilla de boletín con la identidad de MxD.</div></td>
        <td class="tag">Bloque opcional</td>
        <td class="val">__B7__</td>
      </tr>
    </tbody>
  </table>

  <div class="grid2 keep">
    <div>
      <div class="block-label">CONDICIONES</div>
      <div class="frow tight"><span class="k">ENTREGA</span><span class="v">7 días hábiles desde aprobación y entrega de contenidos</span></div>
      <div class="frow tight"><span class="k">PAGO</span><span class="v">50% al inicio · 50% contra puesta al aire</span></div>
      <div class="frow tight"><span class="k">AJUSTES</span><span class="v">Dos rondas visuales incluidas</span></div>
      <div class="frow tight"><span class="k">HOSTING</span><span class="v">Sin costo mensual · dominio actual se conserva</span></div>
      <div class="frow tight"><span class="k">BLOQUES</span><span class="v">Se contratan cuando la fundación decida</span></div>
    </div>
    <div>
      <div class="block-label">LO QUE QUEDA EN CASA</div>
      <div class="frow tight"><span class="k">SITIO</span><span class="v">Código y contenidos propiedad de MxD</span></div>
      <div class="frow tight"><span class="k">ACCESOS</span><span class="v">En cuentas de la fundación, no del consultor</span></div>
      <div class="frow tight"><span class="k">PANEL</span><span class="v">El equipo publica sin intermediarios</span></div>
      <div class="frow tight"><span class="k">DATOS</span><span class="v">Contactos y suscriptoras en base propia</span></div>
      <div class="frow tight"><span class="k">SALIDA</span><span class="v">Nada deja de funcionar si termina el contrato</span></div>
    </div>
  </div>

  <div class="signs keep">
    <div>
      <div class="sname">Ricardo Esteban Ruiz Castro</div>
      <div class="scap">CONSULTOR · ricardoruiz.co · BOGOTÁ D.C.</div>
    </div>
    <div>
      <div class="sname">Aceptación del cliente</div>
      <div class="scap">MUJERES POR LA DEMOCRACIA · FECHA: ____ / ____ / 2026</div>
    </div>
  </div>

  <div class="footer">
    <div class="notes"><b>Validez de la oferta:</b> 30 días calendario. Cifras en pesos colombianos. Documento
      privado, sin valor tributario hasta la emisión de la cuenta de cobro correspondiente.</div>
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
            .replace("__BASE__", BASE_COP)
            .replace("__B5__", B_ENCUESTA)
            .replace("__B6__", B_MEDIOS)
            .replace("__B7__", B_BOLETIN)
            )


def build():
    HTML(string=HTML_DOC).write_pdf(OUT)
    return os.path.getsize(OUT)


if __name__ == "__main__":
    n = build()
    print(f"PDF generado: {OUT}  ({n/1024:.1f} KB)")
