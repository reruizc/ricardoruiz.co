#!/usr/bin/env python3
"""
Propuesta técnica y económica — RADAR MUJER (observatorio + inteligencia interna)
Cliente: Fundación Mujeres por la Democracia (MxD) · directora Laura Herrera.

Producto NUEVO (MxD nunca lo ha visto). NO hablar de "evolución del Observatorio
Mujer" ni "ya construido": producto/propuesta nueva, hecha a su medida.

Estructura: bio de Ricardo → "por qué ahora" → "QUÉ ES RADAR MUJER" (no "EL
ENCARGO") → 8 módulos con 2 párrafos c/u (qué es + para qué le sirve) → comparativa
vs Brandwatch/Meltwater/Talkwalker → cortesía del montaje → inversión → pago Wompi.

Monitor de medios + lector de redes = USO INTERNO para decisiones, NO público.
NO se nombra el proveedor de extracción ("Apify") al cliente.

Datos oficiales: DANE (demografía · mercado laboral MENSUAL según sexo · economía
del cuidado ENUT/Cuenta Satélite, = 20% PIB) · Registraduría+MOE · Policía Nacional.

Cobro (decisión Ricardo): todo mensual. Operación Esencial $1.000.000/mes (incluye
monitor diario) + único opcional Informe de coyuntura +$300.000/mes. El MONTAJE
(~$3.5M ref.) lo regala Ricardo como APOYO a MxD. Pago: slug ricardoruiz.co/pago,
link Wompi que se activa al aceptar.

Formato: 4-5 páginas, letra cómoda (decisión del usuario). Marca MxD vinotinto/
amarillo, Inter + Syne wordmark. WeasyPrint (python3).

Salida: Propuestas/Propuesta-Radar-Mujer-MxD.pdf
"""
import os
import datetime
from weasyprint import HTML

ROOT = "/Users/ricardoruiz/ricardoruiz.co"
OUT = os.path.join(ROOT, "Propuestas", "Propuesta-Radar-Mujer-MxD.pdf")

# --- Cifras (editar aquí si cambian) ---------------------------------------
MENSUAL        = "$ 1.000.000"
MENSUAL_W      = "Plan Esencial &mdash; un mill&oacute;n de pesos M/Cte. al mes."
MENSUAL_USD    = "~ US$ 250 / mes"
MONTAJE_VALOR  = "$ 3.500.000"      # valor de referencia del montaje (regalado)
ADDON_COYUNT   = "+ $ 300.000 /mes"  # informe de coyuntura (único opcional)

# Slug genérico; el link Wompi personalizado se genera al aceptar la suscripción.
PAGO_URL = "ricardoruiz.co/pago"

_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
_hoy = datetime.date.today()
FECHA = f"{_hoy.day} DE {_MESES[_hoy.month - 1].upper()} DE {_hoy.year}"

FONT_DIR_SYNE = os.path.join(ROOT, "tools", "build-propuesta-tesis-oe3", "fonts")
FONT_DIR_INTER = os.path.join(ROOT, "tools", "pacto-1v-2026", "fonts")
F_SYNE   = os.path.join(FONT_DIR_SYNE, "Syne-ExtraBold.ttf")
F_INTER  = os.path.join(FONT_DIR_INTER, "Inter-Regular.ttf")
F_INTER_B = os.path.join(FONT_DIR_INTER, "Inter-Bold.ttf")
F_INTER_I = os.path.join(FONT_DIR_INTER, "Inter-Italic.ttf")

HTML_DOC = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<style>
  @font-face{ font-family:"Syne"; src:url("file://__SYNE__") format("truetype"); font-weight:800; font-style:normal; }
  @font-face{ font-family:"Inter"; src:url("file://__INTER__") format("truetype"); font-weight:400; font-style:normal; }
  @font-face{ font-family:"Inter"; src:url("file://__INTERB__") format("truetype"); font-weight:700; font-style:normal; }
  @font-face{ font-family:"Inter"; src:url("file://__INTERI__") format("truetype"); font-weight:400; font-style:italic; }
  @page {
    size: Letter;
    margin: 14mm 15mm 13mm 15mm;
    background: #f6efe3;
    @bottom-left {
      content: "Ricardo.Ruiz  ·  ricardoruiz.co  ·  Documento privado";
      font-family: "DejaVu Sans Mono", Menlo, monospace;
      font-size: 7pt; color: #b3a39a; letter-spacing: .3px;
    }
    @bottom-right {
      content: "Pág. " counter(page) " / " counter(pages);
      font-family: "DejaVu Sans Mono", Menlo, monospace;
      font-size: 7pt; color: #b3a39a;
    }
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  :root{
    --bg:#f6efe3; --ink:#2b1622; --vino:#5E003F; --vino2:#7d1457;
    --muted:#9a8a90; --muted2:#bcaeb3; --line:#e6d8d0;
    --serif:#3a2230; --serif-soft:#6b5560; --amar:#F9E254;
  }
  body{
    font-family:"Inter", Arial, "Liberation Sans", Helvetica, sans-serif;
    color:var(--ink); font-size:10.5px; line-height:1.55;
  }

  /* ---- header ---- */
  .top{ display:flex; justify-content:space-between; align-items:center; }
  .top-left{ text-align:left; }
  .top-left .priv{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:9.5px; letter-spacing:2.5px; color:var(--vino); }
  .top-left .loc{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:8px; letter-spacing:1.3px; color:var(--muted2); margin-top:4px; }
  .brand{ display:flex; align-items:flex-end; gap:6px; }
  .brand .bars{ display:inline-flex; align-items:flex-end; gap:2.5px; height:17px; margin-bottom:3px; }
  .brand .bars i{ width:3.8px; background:var(--vino); display:block; border-radius:1px; }
  .brand .bars i:nth-child(1){ height:7.5px; }
  .brand .bars i:nth-child(2){ height:12px; }
  .brand .bars i:nth-child(3){ height:17px; }
  .brand .name{ font-family:"Syne", Arial, sans-serif; font-weight:800; font-size:21px; line-height:1; letter-spacing:-.2px; color:var(--ink); }
  .brand .name span{ color:var(--vino); }

  /* MxD identity ribbon */
  .mxd-ribbon{ display:flex; align-items:center; gap:7px; margin-top:14px; }
  .mxd-ribbon .swz{ display:inline-flex; gap:3px; }
  .mxd-ribbon .swz b{ width:14px; height:7px; border-radius:1px; display:block; }
  .mxd-ribbon .swz .v{ background:var(--vino); }
  .mxd-ribbon .swz .a{ background:var(--amar); }
  .mxd-ribbon .swz .l{ background:#EEBCFF; }
  .mxd-ribbon .mtxt{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:7.8px; letter-spacing:1.6px; color:var(--muted); text-transform:uppercase; }

  .docline{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:9.7px; letter-spacing:2.4px; color:var(--vino); margin-top:16px; display:flex; align-items:center; gap:10px; }
  .docline::after{ content:""; width:26px; height:1.5px; background:var(--vino); display:inline-block; }

  h1.title{ font-weight:700; font-size:32px; letter-spacing:-.7px; line-height:1.08; margin-top:7px; }
  h1.title em{ font-style:italic; font-weight:400; color:var(--vino); }
  .sub{ font-size:11.8px; color:var(--serif-soft); line-height:1.58; margin-top:10px; max-width:97%; }
  .sub b{ color:var(--ink); }

  /* ---- parties ---- */
  .parties{ display:flex; gap:34px; margin-top:16px; }
  .party{ flex:1; }
  .pnum{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:9px; color:var(--vino); letter-spacing:1px; }
  .plabel{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:9.7px; letter-spacing:2.4px; color:var(--vino); display:flex; align-items:center; gap:9px; margin-top:2px; }
  .plabel::after{ content:""; flex:1; height:1px; background:var(--line); }
  .pname{ font-weight:700; font-size:15.5px; margin-top:11px; letter-spacing:-.2px; }
  .psub{ font-style:italic; font-size:10.8px; color:var(--serif-soft); margin-top:3px; line-height:1.4; }
  .frow{ display:flex; margin-top:5px; font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:9.5px; }
  .frow:first-of-type{ margin-top:10px; }
  .frow .k{ width:66px; flex:none; color:var(--muted); letter-spacing:.4px; }
  .frow .v{ color:#3a2230; }

  /* ---- generic block label ---- */
  .block-label{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:9.8px; letter-spacing:2.4px; color:var(--vino); display:flex; align-items:center; gap:10px; margin-top:15px; }
  .block-label::after{ content:""; flex:1; height:1px; background:var(--line); }
  .block-label.dash::after{ flex:none; width:24px; height:1.5px; background:var(--vino); }
  .sechead{ margin-top:24px; padding-bottom:5px; font-size:10.3px; }

  .concept p{ font-size:11.5px; line-height:1.62; color:var(--serif); text-align:justify; margin-top:9px; }
  .concept p .b{ color:var(--vino); font-weight:700; }
  .concept p b{ color:var(--ink); }

  /* ---- cadence chips ---- */
  .cad{ display:inline-block; font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:7.6px; letter-spacing:.5px; padding:2px 7px; border-radius:3px; white-space:nowrap; }
  .cad.fijo{ color:var(--muted); border:1px solid var(--line); }
  .cad.iter{ color:var(--vino); border:1px solid var(--vino); }
  .cad.interno{ color:var(--vino); background:rgba(94,0,63,.08); border:1px solid rgba(94,0,63,.22); }

  /* ---- module sections ---- */
  .module{ break-inside:avoid; margin-top:13px; }
  .module .mh{ display:flex; align-items:baseline; gap:9px; }
  .module .mh .mnum{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:9.5px; color:var(--vino); letter-spacing:.5px; }
  .module .mh .mname{ font-weight:700; font-size:13.5px; color:var(--ink); letter-spacing:-.2px; }
  .module .mh .cad{ margin-left:auto; align-self:center; }
  .module p{ font-size:10.8px; line-height:1.58; color:var(--serif); text-align:justify; margin-top:5px; }
  .module p b{ color:var(--ink); }
  .module p .b{ color:var(--vino); font-weight:700; }

  .periodic{ font-size:10.6px; color:var(--serif-soft); line-height:1.55; margin-top:13px; }
  .periodic b{ color:var(--vino); }

  /* ---- amount ---- */
  .amount{ display:flex; justify-content:space-between; align-items:flex-end; margin-top:9px; }
  .amount .words{ font-style:italic; font-size:11.5px; color:var(--muted); max-width:48%; }
  .amount .num{ text-align:right; line-height:1; }
  .amount .num .cop{ font-size:11.5px; color:#5a4450; vertical-align:top; letter-spacing:1px; margin-right:5px; }
  .amount .num .big{ font-weight:700; font-size:35px; color:var(--vino); letter-spacing:-1px; }
  .amount .num .per{ font-size:15px; color:var(--vino); font-weight:700; }
  .amount .num .usd{ display:block; font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:9.3px; color:var(--muted); margin-top:6px; letter-spacing:.4px; }

  /* ---- detail table ---- */
  table.det{ width:100%; border-collapse:collapse; margin-top:11px; }
  table.det th{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:8.7px; letter-spacing:1.4px; color:var(--muted); font-weight:400; text-transform:uppercase; padding:0 0 9px; border-bottom:1px solid var(--line); text-align:left; }
  table.det th.r{ text-align:right; }
  table.det td{ padding:8px 0; border-bottom:1px solid var(--line); vertical-align:top; }
  td.desc .t{ font-weight:700; font-size:11.8px; color:var(--ink); }
  td.desc .d{ font-size:9.8px; color:var(--serif-soft); line-height:1.5; margin-top:4px; }
  td.tag{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:8.7px; color:#3a2230; text-align:right; white-space:nowrap; padding-left:10px; }
  td.val{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:11.5px; color:#3a2230; text-align:right; padding-left:10px; white-space:nowrap; }
  td.desc .t span{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:7.7px; color:var(--vino); letter-spacing:1px; margin-left:6px; }
  td.val s{ color:var(--muted2); font-size:9.3px; }
  td.val .free{ color:var(--vino); font-weight:700; }
  tr.gift td{ background:rgba(249,226,84,.20); }
  .opt td{ opacity:.96; }

  /* ---- two-col grids ---- */
  .grid2{ display:flex; gap:34px; margin-top:12px; }
  .grid2 > div{ flex:1; }

  /* ---- comparison table ---- */
  table.cmp{ width:100%; border-collapse:collapse; margin-top:10px; }
  .cmp-lead{ font-size:10.4px; color:var(--serif-soft); line-height:1.56; margin-top:9px; text-align:justify; }
  .cmp-lead b{ color:var(--vino); }
  table.cmp th{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:8.3px; letter-spacing:1.1px; text-transform:uppercase; color:var(--muted); font-weight:400; padding:0 9px 8px; border-bottom:1px solid var(--line); text-align:left; vertical-align:bottom; }
  table.cmp th.us{ color:var(--vino); }
  table.cmp td{ padding:5px 9px; border-bottom:1px solid var(--line); vertical-align:top; font-size:9.3px; line-height:1.42; }
  td.crit{ font-weight:700; color:var(--ink); width:21%; }
  td.comp{ color:var(--serif-soft); font-style:italic; width:39%; }
  td.us{ color:var(--ink); background:rgba(94,0,63,.07); width:40%; }
  td.us b{ color:var(--vino); }
  table.cmp tr td.us{ border-left:2px solid var(--vino); }

  /* ---- gift / transparency notes ---- */
  .gift-note{ margin-top:11px; background:rgba(249,226,84,.30); border-left:3px solid var(--vino); padding:11px 14px; }
  .gift-note .nl{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:8.7px; letter-spacing:1.6px; color:var(--vino); }
  .gift-note p{ font-size:10.6px; line-height:1.56; color:var(--serif); margin-top:6px; text-align:justify; }
  .gift-note p b{ color:var(--vino); }

  .note{ margin-top:11px; background:rgba(94,0,63,.055); border-left:2.4px solid var(--vino); padding:10px 14px; }
  .note .nl{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:8.7px; letter-spacing:1.6px; color:var(--vino); }
  .note p{ font-size:10px; line-height:1.54; color:var(--serif); margin-top:6px; text-align:justify; }

  .frow.tight{ margin-top:7px; }
  .frow.tight:first-of-type{ margin-top:12px; }

  .signs{ display:flex; gap:34px; margin-top:18px; }
  .signs > div{ flex:1; padding-top:10px; border-top:1.5px solid var(--ink); }
  .signs .sname{ font-weight:700; font-size:12.5px; }
  .signs .scap{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:8.6px; color:var(--muted); letter-spacing:.3px; margin-top:5px; }

  .footer{ margin-top:14px; padding-top:11px; border-top:1px solid var(--line); display:flex; justify-content:space-between; gap:30px; }
  .footer .notes{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:7.9px; color:var(--muted); line-height:1.6; max-width:68%; }
  .footer .notes b{ color:#6b5560; font-weight:400; }
  .footer .by{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:8.2px; color:var(--muted); text-align:right; line-height:1.7; }
  .footer .by b{ color:#4a3340; font-weight:400; }

  .keep{ break-inside:avoid; }
  .cmpwrap{ break-inside:avoid; margin-top:14px; }
</style>
</head>
<body>

  <div class="top">
    <div class="top-left">
      <div class="priv">PROPUESTA PRIVADA</div>
      <div class="loc">BOGOTÁ D.C. · COLOMBIA · __FECHA__</div>
    </div>
    <div class="brand">
      <span class="bars"><i></i><i></i><i></i></span>
      <span class="name">Ricardo<span>.Ruiz</span></span>
    </div>
  </div>

  <div class="mxd-ribbon">
    <span class="swz"><b class="v"></b><b class="a"></b><b class="l"></b></span>
    <span class="mtxt">Hecho a la medida de Mujeres por la Democracia</span>
  </div>

  <div class="docline">PROPUESTA TÉCNICA Y ECONÓMICA · RADAR MUJER · 2026</div>
  <h1 class="title">Radar Mujer: el observatorio que <em>escucha</em><br>y mide la participación política de las mujeres</h1>
  <div class="sub">Un observatorio digital hecho a la medida de Mujeres por la Democracia: <b>datos oficiales al
    día</b> (DANE &middot; Registraduría &middot; Polic&iacute;a Nacional) e <b>inteligencia interna</b> de medios y
    redes, le&iacute;da por un <b>asistente de IA</b> &mdash; con foco en participaci&oacute;n femenina y violencia
    pol&iacute;tica de g&eacute;nero.</div>

  <div class="parties">
    <div class="party">
      <div class="pnum">01</div>
      <div class="plabel">CONSULTOR</div>
      <div class="pname">Ricardo Esteban Ruiz Castro</div>
      <div class="psub">Persona natural &middot; Consultor en datos, observatorios y comunicaci&oacute;n p&uacute;blica</div>
      <div class="frow"><span class="k">SITIO</span><span class="v">ricardoruiz.co</span></div>
      <div class="frow"><span class="k">CIUDAD</span><span class="v">Bogot&aacute; D.C., Colombia</span></div>
      <div class="frow"><span class="k">CORREO</span><span class="v">reruizc@gmail.com</span></div>
    </div>
    <div class="party">
      <div class="pnum">02</div>
      <div class="plabel">CLIENTE</div>
      <div class="pname">Fundaci&oacute;n Mujeres por la Democracia</div>
      <div class="psub">Organizaci&oacute;n no partidista &middot; participaci&oacute;n pol&iacute;tica de las mujeres</div>
      <div class="frow"><span class="k">DIRECTORA</span><span class="v">Laura Herrera</span></div>
      <div class="frow"><span class="k">PROYECTO</span><span class="v">Radar Mujer</span></div>
      <div class="frow"><span class="k">CORREO</span><span class="v">Laurajulianaherrera@gmail.com</span></div>
    </div>
  </div>

  <div class="concept">
    <div class="block-label">QUI&Eacute;N LO CONSTRUYE</div>
    <p>Ricardo Ruiz es <b>analista de datos y consultor en inteligencia electoral y de pol&iacute;ticas
      p&uacute;blicas</b>. Desde ricardoruiz.co construye plataformas que procesan datos oficiales &mdash;Registradur&iacute;a,
      DANE, Polic&iacute;a Nacional&mdash; hasta el nivel de <b>barrio y mesa</b>, y los combina con escucha social y
      modelos de inteligencia artificial. Su trabajo va del an&aacute;lisis del voto &mdash;incluida la
      composici&oacute;n del <b>voto femenino</b> por edad y territorio&mdash; a tableros de decisi&oacute;n para
      campa&ntilde;as, medios y un laboratorio de pol&iacute;ticas p&uacute;blicas. Esa misma maquinaria es la que
      sostiene a Radar Mujer.</p>
  </div>

  <div class="concept">
    <div class="block-label">POR QU&Eacute; AHORA</div>
    <p>La Fundaci&oacute;n <span class="b">Mujeres por la Democracia</span> trabaja por m&aacute;s mujeres en lo
      p&uacute;blico desde la <span class="b">investigaci&oacute;n, la formaci&oacute;n y la incidencia</span>. Su
      propio estudio puso el dedo en la llaga: aunque el <span class="b">94%</span> de los colombianos cree que
      mujeres y hombres tienen igual capacidad de liderazgo, ellas ocupan apenas el <span class="b">29% del
      Congreso</span> y el <span class="b">12,5% de los cargos directivos</span> del pa&iacute;s. Cerrar esa brecha
      es trabajo sostenido &mdash; y la incidencia se sostiene con <span class="b">evidencia que no caduca</span>.
      Hoy esa evidencia llega suelta: estudios puntuales, cifras dispersas, recortes de prensa. Radar Mujer la
      re&uacute;ne en un solo lugar y la mantiene viva, como <b>insumo interno para decidir</b> d&oacute;nde
      concentrar el esfuerzo.</p>
  </div>

  <div class="concept">
    <div class="block-label">QU&Eacute; ES RADAR MUJER</div>
    <p>Radar Mujer es un <b>observatorio digital sobre la participaci&oacute;n pol&iacute;tica de las mujeres</b>,
      hecho a la medida de la Fundaci&oacute;n. Re&uacute;ne en un solo lugar lo que hoy est&aacute; disperso: los
      <b>datos oficiales</b> que importan, la <b>conversaci&oacute;n p&uacute;blica</b> en medios y redes, y un
      <b>asistente de inteligencia artificial</b> que ayuda a leerlo todo. Est&aacute; pensado para uso interno de
      la organizaci&oacute;n &mdash; para decidir d&oacute;nde concentrar la investigaci&oacute;n, la
      formaci&oacute;n y la incidencia. A continuaci&oacute;n, pieza por pieza.</p>
  </div>

  <div class="block-label dash sechead">LOS DATOS OFICIALES, AL D&Iacute;A</div>

  <div class="module">
    <div class="mh"><span class="mnum">01</span><span class="mname">Demograf&iacute;a de las mujeres</span><span class="cad fijo">ESTRUCTURAL</span></div>
    <p>Cu&aacute;ntas mujeres hay, d&oacute;nde viven y en qu&eacute; edades, a partir de las <b>proyecciones de
      poblaci&oacute;n del DANE</b>, hasta el nivel municipal y por grupos de edad. Es el mapa base: el denominador
      de todo lo dem&aacute;s.</p>
    <p>Sin saber d&oacute;nde est&aacute;n las mujeres y c&oacute;mo se distribuyen por edad, cualquier cifra queda
      en el aire. Esta capa permite <b>focalizar</b>: d&oacute;nde hay m&aacute;s mujeres j&oacute;venes por
      movilizar, d&oacute;nde envejece el electorado femenino, en qu&eacute; territorios concentrar formaci&oacute;n
      o incidencia. Cambia poco, pero es el suelo sobre el que se paran las dem&aacute;s capas.</p>
  </div>

  <div class="module">
    <div class="mh"><span class="mnum">02</span><span class="mname">Mercado laboral y brechas econ&oacute;micas</span><span class="cad iter">MENSUAL</span></div>
    <p>El empleo, el desempleo, la informalidad y la brecha de ingresos de las mujeres, seg&uacute;n la <b>Gran
      Encuesta Integrada de Hogares del DANE</b>, que publica estas cifras <b>cada mes desagregadas por sexo</b>. La
      participaci&oacute;n laboral femenina (~53%) sigue muy por debajo de la masculina (~76%), y la informalidad y
      la pobreza pesan m&aacute;s sobre ellas.</p>
    <p>La autonom&iacute;a econ&oacute;mica es la base de la autonom&iacute;a pol&iacute;tica. Seguir mes a mes
      c&oacute;mo se mueve el empleo femenino le da a la Fundaci&oacute;n el <b>pulso de la realidad material</b> de
      las mujeres &mdash; el argumento m&aacute;s contundente en una mesa de incidencia, y el term&oacute;metro para
      saber si las pol&iacute;ticas de equidad est&aacute;n funcionando o no.</p>
  </div>

  <div class="module">
    <div class="mh"><span class="mnum">03</span><span class="mname">Econom&iacute;a del cuidado</span><span class="cad iter">ANUAL</span></div>
    <p>El trabajo dom&eacute;stico y de cuidado <b>no remunerado</b> que sostienen las mujeres, a partir de la
      <b>Encuesta Nacional de Uso del Tiempo</b> y la <b>Cuenta Sat&eacute;lite de Econom&iacute;a del Cuidado</b> del
      DANE. Las cifras son contundentes: 9 de cada 10 mujeres hacen trabajo no remunerado, dedican m&aacute;s del
      doble de horas que los hombres (<b>7h35 frente a 3h12 al d&iacute;a</b>) y ese trabajo equivale al
      <b>20% del PIB</b>.</p>
    <p>Es, probablemente, el dato m&aacute;s poderoso para la causa: la econom&iacute;a del pa&iacute;s se sostiene
      sobre horas de trabajo femenino invisible. Tenerlo procesado y a la mano convierte a la Fundaci&oacute;n en
      <b>vocera autorizada</b> de un debate en plena ebullici&oacute;n &mdash;la Pol&iacute;tica Nacional de Cuidado,
      los sistemas distritales de cuidado&mdash; y abre puertas con la cooperaci&oacute;n internacional.</p>
  </div>

  <div class="module">
    <div class="mh"><span class="mnum">04</span><span class="mname">Participaci&oacute;n y representatividad electoral</span><span class="cad iter">CADA ELECCI&Oacute;N</span></div>
    <p>Cu&aacute;ntas mujeres votan y cu&aacute;ntas resultan electas, desde 2010 hasta hoy, cruzando los datos de la
      <b>Registradur&iacute;a</b> con la s&iacute;ntesis de la <b>Misi&oacute;n de Observaci&oacute;n Electoral</b>. La
      brecha entre votar y gobernar es enorme: las mujeres son mayor&iacute;a del censo, pero apenas el 29% del
      Congreso.</p>
    <p>Es el coraz&oacute;n de la misi&oacute;n de la Fundaci&oacute;n. Medir esa brecha <b>elecci&oacute;n por
      elecci&oacute;n y por territorio</b> permite ver d&oacute;nde la paridad avanza y d&oacute;nde retrocede,
      qu&eacute; partidos cumplen y cu&aacute;les no, y d&oacute;nde se cierra el embudo que va de candidatas a
      electas. Es la l&iacute;nea base contra la cual medir cualquier avance hacia la paridad.</p>
  </div>

  <div class="module">
    <div class="mh"><span class="mnum">05</span><span class="mname">Delitos y violencia contra la mujer</span><span class="cad iter">MENSUAL</span></div>
    <p>La <b>violencia intrafamiliar</b>, los <b>delitos sexuales</b> y los <b>feminicidios</b>, por territorio y mes
      a mes, a partir de los registros de la <b>Polic&iacute;a Nacional</b>. Permite ver no solo el agregado
      nacional, sino d&oacute;nde se concentra y c&oacute;mo evoluciona.</p>
    <p>La violencia es el obst&aacute;culo m&aacute;s brutal a la participaci&oacute;n de las mujeres en lo
      p&uacute;blico, y la <b>violencia pol&iacute;tica de g&eacute;nero</b> &mdash;agresiones a lideresas y
      candidatas&mdash; se agudiza en a&ntilde;o electoral. Seguir estas cifras le permite a la Fundaci&oacute;n
      <b>documentar, anticipar y exigir</b>: d&oacute;nde proteger, d&oacute;nde alzar la voz, con qu&eacute; datos
      respaldar una denuncia o una pol&iacute;tica.</p>
  </div>

  <div class="block-label dash sechead">LA INTELIGENCIA INTERNA</div>

  <div class="module">
    <div class="mh"><span class="mnum">06</span><span class="mname">Monitor de medios</span><span class="cad interno">USO INTERNO</span></div>
    <p>Recoge de forma continua lo que publica la prensa &mdash;nacional y regional&mdash; sobre mujeres en la
      pol&iacute;tica, liderazgo femenino y violencia de g&eacute;nero, y organiza el <b>volumen, los temas y el
      tono</b> de esa cobertura en un solo lugar.</p>
    <p>Es una herramienta de <b>uso interno para la toma de decisiones</b>, no un producto p&uacute;blico. Le dice a
      la Fundaci&oacute;n c&oacute;mo se est&aacute; contando el tema &mdash;qu&eacute; se nombra, qu&eacute; se
      silencia, qui&eacute;n marca la agenda&mdash; para decidir cu&aacute;ndo y c&oacute;mo intervenir: una columna,
      una reacci&oacute;n, una vocer&iacute;a. Es leer el campo antes de jugar.</p>
  </div>

  <div class="module">
    <div class="mh"><span class="mnum">07</span><span class="mname">Lector de redes sociales</span><span class="cad interno">USO INTERNO</span></div>
    <p>El pulso de la conversaci&oacute;n p&uacute;blica en redes sobre la participaci&oacute;n pol&iacute;tica de las
      mujeres: <b>volumen, temas, tono</b> y los momentos en que la conversaci&oacute;n se enciende. Trabaja sobre
      contenido p&uacute;blico, sin datos personales privados.</p>
    <p>Como el monitor de medios, es <b>inteligencia interna para decidir</b>, no un tablero para publicar. Le
      permite a la Fundaci&oacute;n entender qu&eacute; moviliza a la opini&oacute;n, advertir a tiempo una ola de
      violencia pol&iacute;tica digital contra una lideresa, y medir si sus propios mensajes est&aacute;n calando. El
      insumo para una vocer&iacute;a que llega a tiempo y con el tono justo.</p>
  </div>

  <div class="module">
    <div class="mh"><span class="mnum">08</span><span class="mname">Asistente de IA estrat&eacute;gico</span><span class="cad interno">TRANSVERSAL</span></div>
    <p>Un asistente de inteligencia artificial que <b>lee todo lo anterior</b> &mdash;los datos oficiales y la
      conversaci&oacute;n p&uacute;blica&mdash; y lo traduce a lenguaje claro: qu&eacute; cambi&oacute;, qu&eacute;
      significa y qu&eacute; conviene hacer.</p>
    <p>No reemplaza el criterio de la Fundaci&oacute;n; lo <b>acelera</b>. Ante una reuni&oacute;n, una vocer&iacute;a
      o un informe para cooperaci&oacute;n, el asistente resume el panorama, sugiere d&oacute;nde concentrar el
      esfuerzo y prepara el argumento con la cifra exacta al lado. Convierte un mar de datos en una decisi&oacute;n.</p>
  </div>

  <div class="periodic"><b>Cada mes:</b> reporte con marca MxD, tablero con drill territorial (pa&iacute;s &middot;
    municipio &middot; comuna &middot; barrio) y memo metodol&oacute;gico &mdash; listos para circular ante aliados,
    prensa o cooperaci&oacute;n internacional (ONU&nbsp;Mujeres, BID).</div>

  <div class="cmpwrap">
  <div class="block-label dash">POR QU&Eacute; RADAR MUJER Y NO BRANDWATCH, MELTWATER O TALKWALKER</div>
  <p class="cmp-lead">Hay plataformas potentes de escucha &mdash;<b>Brandwatch, Meltwater, Talkwalker</b>&mdash; y
    agencias que las revenden. Son excelentes para una marca que vende un producto; no para una fundaci&oacute;n
    que defiende la participaci&oacute;n pol&iacute;tica de las mujeres en Colombia. Esto las separa:</p>
  <table class="cmp">
    <thead>
      <tr>
        <th>Criterio</th>
        <th>Brandwatch &middot; Meltwater &middot; Talkwalker</th>
        <th class="us">Radar Mujer &middot; Ricardo.Ruiz</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td class="crit">Qu&eacute; datos cruza</td>
        <td class="comp">Redes sociales, sin el contexto oficial.</td>
        <td class="us">Redes y medios <b>+ microdato oficial</b> (DANE, electoral, delitos) cruzado por territorio.</td>
      </tr>
      <tr>
        <td class="crit">Acompa&ntilde;amiento</td>
        <td class="comp">Una licencia de software y soporte por tickets.</td>
        <td class="us">Un <b>consultor que conoce tu causa</b> y lee los datos contigo.</td>
      </tr>
      <tr>
        <td class="crit">Detalle territorial</td>
        <td class="comp">Tableros nacionales; no bajan del pa&iacute;s.</td>
        <td class="us">Drill a <b>municipio, comuna y barrio</b>, hecho para Colombia.</td>
      </tr>
      <tr>
        <td class="crit">Qu&eacute; hace con el dato</td>
        <td class="comp">Te entregan gr&aacute;ficas; t&uacute; interpretas.</td>
        <td class="us"><b>Asistente de IA</b> que sugiere d&oacute;nde actuar, qu&eacute; priorizar y c&oacute;mo vocear.</td>
      </tr>
      <tr>
        <td class="crit">Costo y contrato</td>
        <td class="comp"><b>Miles de USD al mes</b>, contrato anual.</td>
        <td class="us">Mensualidad en pesos, <b>sin licencias</b>, cancelable con 15 d&iacute;as.</td>
      </tr>
      <tr>
        <td class="crit">Montaje</td>
        <td class="comp">Cobran aparte la implementaci&oacute;n.</td>
        <td class="us">Lo <b>asume Ricardo.Ruiz como apoyo</b> a MxD (ver abajo).</td>
      </tr>
    </tbody>
  </table>
  </div>

  <div class="gift-note keep">
    <div class="nl">EL MONTAJE CORRE POR NUESTRA CUENTA &mdash; APOYO A MxD</div>
    <p>El <b>montaje e implementaci&oacute;n</b> &mdash;construir y poner en marcha el observatorio completo (los
      datos oficiales, el monitor de medios y redes y el asistente de IA) con la marca <b>Radar Mujer</b>&mdash; tiene
      un valor de referencia de <b>__MONTAJE__</b> y <b>corre por cuenta de Ricardo.Ruiz como aporte a Mujeres por la
      Democracia</b>. MxD no paga setup: solo asume la operaci&oacute;n mensual &mdash; es nuestra forma de respaldar
      a la organizaci&oacute;n.</p>
  </div>

  <div class="block-label dash keep">INVERSI&Oacute;N</div>
  <div class="amount keep">
    <div class="words">__WORDS__</div>
    <div class="num"><span class="cop">DESDE COP</span><span class="big">__MENSUAL__</span><span class="per"> /mes</span>
      <span class="usd">__USD__ &middot; monitoreo diario y asistente de IA incluidos &middot; montaje sin costo</span></div>
  </div>

  <table class="det keep">
    <thead>
      <tr><th>CONCEPTO</th><th class="r">PERIODICIDAD</th><th class="r">INVERSI&Oacute;N</th></tr>
    </thead>
    <tbody>
      <tr class="gift">
        <td class="desc">
          <div class="t">Montaje e implementaci&oacute;n <span>APORTE RR</span></div>
          <div class="d">Construcci&oacute;n y puesta en marcha del observatorio completo con la marca Radar Mujer:
            los m&oacute;dulos de datos oficiales, el monitor de medios y redes, el asistente de IA y la primera carga
            de informaci&oacute;n.</div>
        </td>
        <td class="tag">Pago &uacute;nico</td>
        <td class="val"><s>__MONTAJE__</s><br><span class="free">CORTES&Iacute;A</span></td>
      </tr>
      <tr>
        <td class="desc">
          <div class="t">Operaci&oacute;n mensual &middot; Radar Mujer <span>ESENCIAL</span></div>
          <div class="d">Datos oficiales al d&iacute;a (mercado laboral y violencia contra la mujer, mensuales) &middot;
            monitor de medios y lector de redes con <b>seguimiento diario</b> (uso interno) &middot; <b>asistente de
            IA</b> &middot; reporte mensual con marca MxD &middot; tablero con drill territorial &middot; soporte.
            Monitoreo y herramientas incluidos.</div>
        </td>
        <td class="tag">Mes a mes</td>
        <td class="val">__MENSUAL__</td>
      </tr>
      <tr class="opt">
        <td class="desc">
          <div class="t">Informe de coyuntura <span>OPCIONAL</span></div>
          <div class="d">Cada mes, un informe corto sobre un tema o hecho espec&iacute;fico (una elecci&oacute;n, un
            debate de ley, una agresi&oacute;n a una lideresa): datos + escucha + insumo de mensajes para vocer&iacute;a.</div>
        </td>
        <td class="tag">Mensual &middot; se suma</td>
        <td class="val">__ADDONC__</td>
      </tr>
    </tbody>
  </table>

  <div class="grid2 keep">
    <div>
      <div class="block-label">CONDICIONES</div>
      <div class="frow tight"><span class="k">MONTAJE</span><span class="v">Cortes&iacute;a Ricardo.Ruiz &middot; apoyo a MxD</span></div>
      <div class="frow tight"><span class="k">FACTURA</span><span class="v">Mensual &middot; cuenta de cobro</span></div>
      <div class="frow tight"><span class="k">PERMANENCIA</span><span class="v">Sugerida 3 meses &middot; cancelable con 15 d&iacute;as</span></div>
      <div class="frow tight"><span class="k">INICIO</span><span class="v">Montaje ~10 d&iacute;as h&aacute;biles &middot; 1.er reporte al mes</span></div>
      <div class="frow tight"><span class="k">MONEDA</span><span class="v">COP &middot; No responsable de IVA</span></div>
    </div>
    <div>
      <div class="block-label">PAGO EN L&Iacute;NEA</div>
      <div class="frow tight"><span class="k">ENLACE</span><span class="v">__PAGOURL__</span></div>
      <div class="frow tight"><span class="k">SE ACTIVA</span><span class="v">Link personalizado al aceptar la suscripci&oacute;n</span></div>
      <div class="frow tight"><span class="k">TARJETA</span><span class="v">Cr&eacute;dito / d&eacute;bito &middot; Visa &middot; Mastercard &middot; Amex</span></div>
      <div class="frow tight"><span class="k">TAMBI&Eacute;N</span><span class="v">PSE &middot; Nequi &middot; Bot&oacute;n Bancolombia</span></div>
      <div class="frow tight"><span class="k">PASARELA</span><span class="v">Wompi (Bancolombia) &middot; pago seguro</span></div>
    </div>
  </div>

  <div class="note keep">
    <div class="nl">NOTA DE TRANSPARENCIA</div>
    <p>El monitor de medios y el lector de redes son herramientas de <b>uso interno</b> para la toma de decisiones de
      la Fundaci&oacute;n, no productos p&uacute;blicos, y trabajan sobre <b>contenido p&uacute;blico</b>
      (publicaciones abiertas y notas de prensa), sin datos personales privados. La lectura del asistente de IA es una
      <b>estimaci&oacute;n auditable</b>, no una verdad absoluta. Todo queda documentado en el memorando.</p>
  </div>

  <div class="signs keep">
    <div>
      <div class="sname">Ricardo Esteban Ruiz Castro</div>
      <div class="scap">CONSULTOR &middot; ricardoruiz.co &middot; BOGOT&Aacute; D.C.</div>
    </div>
    <div>
      <div class="sname">Aceptaci&oacute;n del cliente</div>
      <div class="scap">FUNDACI&Oacute;N MUJERES POR LA DEMOCRACIA &middot; FECHA: ____ / ____ / 2026</div>
    </div>
  </div>

  <div class="footer">
    <div class="notes"><b>Validez de la oferta:</b> 30 d&iacute;as calendario. El montaje es un aporte sin costo de
      Ricardo.Ruiz a MxD; MxD solo asume la mensualidad. Documento privado, sin valor tributario hasta la
      emisi&oacute;n de la cuenta de cobro correspondiente.</div>
    <div class="by">Preparado por<br><b>RICARDO ESTEBAN RUIZ CASTRO</b><br>ricardoruiz.co</div>
  </div>

</body>
</html>"""

HTML_DOC = (HTML_DOC
            .replace("__SYNE__", F_SYNE)
            .replace("__INTERB__", F_INTER_B)
            .replace("__INTERI__", F_INTER_I)
            .replace("__INTER__", F_INTER)
            .replace("__WORDS__", MENSUAL_W)
            .replace("__USD__", MENSUAL_USD)
            .replace("__MONTAJE__", MONTAJE_VALOR)
            .replace("__ADDONC__", ADDON_COYUNT)
            .replace("__PAGOURL__", PAGO_URL)
            .replace("__FECHA__", FECHA)
            .replace("__MENSUAL__", MENSUAL))


def build():
    HTML(string=HTML_DOC).write_pdf(OUT)
    return os.path.getsize(OUT)


if __name__ == "__main__":
    n = build()
    print(f"PDF generado: {OUT}  ({n/1024:.1f} KB)")
