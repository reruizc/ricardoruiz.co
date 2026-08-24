#!/usr/bin/env python3
"""
Propuesta técnica y económica — OE3 (Social Listening + PLN sobre @petrogustavo)
Cliente: Carlos Henry Rodríguez Salgado (tesis doctoral USMP, Lima).
Marca Ricardo.Ruiz (estética de la cuenta de cobro 002), render con WeasyPrint.

Salida: consultoria-tesis/Propuesta-OE3-Social-Listening-Petro.pdf
"""
import os
from weasyprint import HTML

ROOT = "/Users/ricardoruiz/ricardoruiz.co"
OUT = os.path.join(ROOT, "Propuestas",
                   "Propuesta-OE3-Social-Listening-Petro.pdf")

# --- Cifras (editar aquí si cambian) ---------------------------------------
# Headline = plan Esencial (el recomendado / puerta de entrada).
PRECIO_BASE   = "$ 6.500.000"
PRECIO_BASE_W = "Plan Esencial &mdash; seis millones quinientos mil pesos M/Cte."
PRECIO_BASE_USD = "US$ 1.600"
# Otros planes (van hardcodeados en la tabla de planes).
PRECIO_COMPLETO = "$ 8.000.000"
PRECIO_ADDON    = "$ 2.000.000"
# Enlace de pago personalizado (Ricardo lo mapea al link de Wompi).
PAGO_URL = "ricardoruiz.co/perfil-personalizado"

# Fecha de emisión (hoy)
import datetime
_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
_hoy = datetime.date.today()
FECHA = f"{_hoy.day} DE {_MESES[_hoy.month - 1].upper()} DE {_hoy.year}"

FONT_SYNE = os.path.join(ROOT, "tools", "build-propuesta-tesis-oe3",
                         "fonts", "Syne-ExtraBold.ttf")

HTML_DOC = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<style>
  @font-face{
    font-family:"Syne";
    src:url("file://__SYNE__") format("truetype");
    font-weight:800; font-style:normal;
  }
  @page {
    size: Letter;
    margin: 16mm 15mm 15mm 15mm;
    background: #eaf1fb;
    @bottom-left {
      content: "Ricardo.Ruiz  ·  ricardoruiz.co  ·  Documento privado";
      font-family: "DejaVu Sans Mono", Menlo, monospace;
      font-size: 7pt; color: #b1aca1; letter-spacing: .3px;
    }
    @bottom-right {
      content: "Pág. " counter(page) " / " counter(pages);
      font-family: "DejaVu Sans Mono", Menlo, monospace;
      font-size: 7pt; color: #b1aca1;
    }
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  :root{
    --bg:#eef2fb; --ink:#1b1830; --blue:#5d3a9c; --muted:#857e9c;
    --muted2:#aaa6c2; --line:#dad6ec; --serif:#2a2740; --serif-soft:#544f6b;
  }
  body{
    font-family: Arial, "Liberation Sans", Helvetica, sans-serif;
    color:var(--ink); font-size:10px; line-height:1.5;
  }
  .mono{ font-family:"DejaVu Sans Mono", Menlo, "Courier New", monospace; }
  .rom { font-family: Georgia, "Times New Roman", serif; }

  /* ---- header ---- */
  .top{ display:flex; justify-content:space-between; align-items:center; }
  .brand{ display:flex; align-items:flex-end; gap:6px; }
  .brand .bars{ display:inline-flex; align-items:flex-end; gap:2.5px; height:16px; margin-bottom:3px; }
  .brand .bars i{ width:3.6px; background:var(--blue); display:block; border-radius:1px; }
  .brand .bars i:nth-child(1){ height:7px; }
  .brand .bars i:nth-child(2){ height:11.5px; }
  .brand .bars i:nth-child(3){ height:16px; }
  .brand .name{ font-family:"Syne", Arial, sans-serif; font-weight:800; font-size:20px; line-height:1; letter-spacing:-.2px; color:var(--ink); }
  .brand .name span{ color:var(--blue); }
  .top-left{ text-align:left; }
  .top-left .priv{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:9.5px; letter-spacing:2.5px; color:#3b4a6b; }
  .top-left .loc{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:8px; letter-spacing:1.3px; color:var(--muted2); margin-top:4px; }

  .docline{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:9.5px; letter-spacing:2.4px; color:var(--blue); margin-top:15px; display:flex; align-items:center; gap:10px; }
  .docline::after{ content:""; width:26px; height:1.5px; background:var(--blue); display:inline-block; }

  h1.title{ font-weight:700; font-size:34px; letter-spacing:-.9px; line-height:1.04; margin-top:6px; }
  h1.title em{ font-family:Georgia,"Times New Roman",serif; font-style:italic; font-weight:400; color:var(--blue); }
  .sub{ font-family:Georgia,"Times New Roman",serif; font-size:11.5px; color:var(--serif-soft); line-height:1.45; margin-top:8px; max-width:96%; }

  /* ---- parties ---- */
  .parties{ display:flex; gap:34px; margin-top:15px; }
  .party{ flex:1; }
  .pnum{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:9px; color:var(--blue); letter-spacing:1px; }
  .plabel{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:9.5px; letter-spacing:2.4px; color:var(--blue); display:flex; align-items:center; gap:9px; margin-top:2px; }
  .plabel::after{ content:""; flex:1; height:1px; background:var(--line); }
  .pname{ font-weight:700; font-size:15px; margin-top:11px; letter-spacing:-.2px; }
  .psub{ font-family:Georgia,"Times New Roman",serif; font-size:10.5px; color:var(--serif-soft); margin-top:3px; line-height:1.4; }
  .frow{ display:flex; margin-top:5px; font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:9.2px; }
  .frow:first-of-type{ margin-top:10px; }
  .frow .k{ width:64px; flex:none; color:var(--muted); letter-spacing:.4px; }
  .frow .v{ color:#2c2a26; }

  /* ---- generic block label ---- */
  .block-label{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:9.5px; letter-spacing:2.4px; color:var(--blue); display:flex; align-items:center; gap:10px; margin-top:13px; }
  .block-label::after{ content:""; flex:1; height:1px; background:var(--line); }
  .block-label.dash::after{ flex:none; width:24px; height:1.5px; background:var(--blue); }

  .concept p{ font-family:Georgia,"Times New Roman",serif; font-size:11.8px; line-height:1.62; color:var(--serif); text-align:justify; margin-top:10px; }
  .concept p .b{ color:var(--blue); font-weight:700; }

  /* ---- deliverables list ---- */
  ul.deliv{ list-style:none; margin-top:11px; }
  ul.deliv li{ position:relative; padding-left:20px; margin-top:8px; font-size:10.6px; line-height:1.52; color:#26252c; text-align:justify; }
  ul.deliv li::before{ content:""; position:absolute; left:4px; top:6px; width:6px; height:6px; background:var(--blue); border-radius:1px; }
  ul.deliv li b{ color:var(--ink); }
  ul.deliv li .lead{ font-weight:700; color:var(--ink); }

  /* ---- amount ---- */
  .amount{ display:flex; justify-content:space-between; align-items:flex-end; margin-top:8px; }
  .amount .words{ font-family:Georgia,"Times New Roman",serif; font-style:italic; font-size:11px; color:var(--muted); }
  .amount .num{ text-align:right; line-height:1; }
  .amount .num .cop{ font-size:11px; color:#3a3833; vertical-align:top; letter-spacing:1px; margin-right:5px; }
  .amount .num .big{ font-weight:700; font-size:33px; color:var(--blue); letter-spacing:-1px; }
  .amount .num .usd{ display:block; font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:9px; color:var(--muted); margin-top:5px; letter-spacing:.5px; }

  /* ---- detail table ---- */
  table.det{ width:100%; border-collapse:collapse; margin-top:9px; }
  table.det th{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:8.5px; letter-spacing:1.4px; color:var(--muted); font-weight:400; text-transform:uppercase; padding:0 0 8px; border-bottom:1px solid var(--line); text-align:left; }
  table.det th.r{ text-align:right; }
  table.det td{ padding:5px 0; border-bottom:1px solid var(--line); vertical-align:top; }
  td.desc .t{ font-weight:700; font-size:11px; color:var(--ink); }
  td.desc .d{ font-family:Georgia,"Times New Roman",serif; font-size:9.4px; color:var(--serif-soft); line-height:1.38; margin-top:3px; }
  td.tag{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:8.4px; color:#2c2a26; text-align:right; white-space:nowrap; padding-left:10px; }
  td.val{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:11px; color:#2c2a26; text-align:right; padding-left:10px; white-space:nowrap; }
  .opt td{ opacity:.95; }
  td.desc .t span{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:7.5px; color:var(--blue); letter-spacing:1px; margin-left:6px; }
  .total{ display:flex; justify-content:flex-end; align-items:baseline; gap:30px; margin-top:9px; }
  .total .lab{ font-weight:700; font-size:13px; color:var(--ink); }
  .total .v{ font-weight:700; font-size:21px; color:var(--blue); letter-spacing:-.5px; }
  .total .v small{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:9px; color:var(--muted); font-weight:400; margin-left:8px; letter-spacing:.4px; }

  /* ---- two-col grids ---- */
  .grid2{ display:flex; gap:34px; margin-top:8px; }
  .grid2 > div{ flex:1; }
  .ck{ font-size:9.6px; line-height:1.5; color:#26252c; margin-top:7px; padding-left:16px; position:relative; text-align:justify; }
  .ck::before{ content:"›"; position:absolute; left:2px; top:0; color:var(--blue); font-weight:700; }
  .ck b{ color:var(--ink); }

  /* ---- comparison table ---- */
  table.cmp{ width:100%; border-collapse:collapse; margin-top:11px; }
  table.cmp th{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:8px; letter-spacing:1.1px; text-transform:uppercase; color:var(--muted); font-weight:400; padding:0 9px 7px; border-bottom:1px solid var(--line); text-align:left; vertical-align:bottom; }
  table.cmp th.us{ color:var(--blue); }
  table.cmp td{ padding:4px 9px; border-bottom:1px solid var(--line); vertical-align:top; font-size:8.7px; line-height:1.34; }
  td.crit{ font-weight:700; color:var(--ink); width:23%; }
  td.comp{ color:var(--serif-soft); font-family:Georgia,"Times New Roman",serif; width:38%; }
  td.us{ color:var(--ink); background:rgba(93,58,156,.08); width:39%; }
  td.us b{ color:var(--blue); }
  table.cmp tr td.us{ border-left:2px solid var(--blue); }

  /* ---- transparency note ---- */
  .note{ margin-top:9px; background:rgba(93,58,156,.07); border-left:2.4px solid var(--blue); padding:8px 12px; }
  .note .nl{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:8.5px; letter-spacing:1.6px; color:var(--blue); }
  .note p{ font-family:Georgia,"Times New Roman",serif; font-size:9.6px; line-height:1.48; color:var(--serif); margin-top:5px; text-align:justify; }

  /* ---- pay block ---- */
  .frow.tight{ margin-top:6px; }
  .frow.tight:first-of-type{ margin-top:11px; }

  .signs{ display:flex; gap:34px; margin-top:10px; }
  .signs > div{ flex:1; padding-top:9px; border-top:1.5px solid var(--ink); }
  .signs .sname{ font-weight:700; font-size:12px; }
  .signs .scap{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:8.4px; color:var(--muted); letter-spacing:.3px; margin-top:4px; }

  .footer{ margin-top:8px; padding-top:9px; border-top:1px solid var(--line); display:flex; justify-content:space-between; gap:30px; }
  .footer .notes{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:7.6px; color:var(--muted); line-height:1.55; max-width:68%; }
  .footer .notes b{ color:#5a564e; font-weight:400; }
  .footer .by{ font-family:"DejaVu Sans Mono",Menlo,monospace; font-size:8px; color:var(--muted); text-align:right; line-height:1.7; }
  .footer .by b{ color:#46433d; font-weight:400; }

  .keep{ break-inside:avoid; }
  .cmpwrap{ break-inside:avoid; margin-top:11px; }
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

  <div class="docline">PROPUESTA TÉCNICA Y ECONÓMICA · RR-OE3-001 · 2026</div>
  <h1 class="title">Análisis de sentimiento y reputación digital<br>del discurso presidencial en X (Twitter)</h1>
  <div class="sub">Ejecución técnica integral del <b>OE3</b> de la tesis doctoral: <b>Social Listening,
    minería de datos y análisis de sentimiento (PLN)</b> sobre la cuenta oficial
    <b>@petrogustavo</b> en X (Twitter), aplicado a tres hitos de crisis del periodo 2022&ndash;2026.</div>

  <div class="parties">
    <div class="party">
      <div class="pnum">01</div>
      <div class="plabel">CONSULTOR</div>
      <div class="pname">Ricardo Esteban Ruiz Castro</div>
      <div class="psub">Persona natural &middot; Consultor en datos, NLP y comunicaci&oacute;n pol&iacute;tica</div>
      <div class="frow"><span class="k">SITIO</span><span class="v">ricardoruiz.co</span></div>
      <div class="frow"><span class="k">CIUDAD</span><span class="v">Bogot&aacute; D.C., Colombia</span></div>
      <div class="frow"><span class="k">CORREO</span><span class="v">reruizc@gmail.com</span></div>
    </div>
    <div class="party">
      <div class="pnum">02</div>
      <div class="plabel">CLIENTE</div>
      <div class="pname">Carlos Henry Rodr&iacute;guez Salgado</div>
      <div class="psub">Candidato a Doctor en Relaciones P&uacute;blicas y Comunicaci&oacute;n Digital &middot; USMP, Lima</div>
      <div class="frow"><span class="k">PROYECTO</span><span class="v">Tesis doctoral &middot; OE3</span></div>
      <div class="frow"><span class="k">CORREO</span><span class="v">Carloshrodriquez10@hotmail.com</span></div>
    </div>
  </div>

  <div class="concept">
    <div class="block-label">EL ENCARGO</div>
    <p>Se contrata la <span class="b">ejecuci&oacute;n t&eacute;cnica completa del Objetivo Espec&iacute;fico 3</span>:
      desde la extracci&oacute;n segura del hist&oacute;rico de X hasta la entrega de la matriz lista para SPSS,
      un tablero interactivo y el soporte metodol&oacute;gico. El corpus se acota a <span class="b">tres
      crisis presidenciales</span>: (1)&nbsp;el esc&aacute;ndalo de la UNGRD; (2)&nbsp;la postura de
      pol&iacute;tica exterior frente al conflicto Palestina&ndash;Israel; y (3)&nbsp;el choque institucional
      con las Altas Cortes por la reforma tributaria mediante decreto. La unidad de an&aacute;lisis son las
      publicaciones de la cuenta oficial <span class="b">@petrogustavo</span> dentro de esas ventanas.</p>
  </div>

  <div class="block-label dash">QU&Eacute; ENTREGAMOS</div>
  <ul class="deliv">
    <li><span class="lead">Corpus extra&iacute;do y verificable.</span> Tweets de @petrogustavo en las tres
      ventanas, con <b>m&eacute;tricas p&uacute;blicas</b> (likes, reposts, respuestas, quotes), texto, fecha y
      <b>URL real</b>. Extracci&oacute;n gestionada con proxies + capa propia de validaci&oacute;n de m&eacute;tricas.</li>
    <li><span class="lead">An&aacute;lisis de sentimiento PLN en espa&ntilde;ol colombiano.</span> Clasificaci&oacute;n
      positivo / negativo / neutral y <b>Net Sentiment Score</b> por tweet y por crisis, con un clasificador
      <b>transparente y auditable</b> (no caja negra).</li>
    <li><span class="lead">Frecuencia y co-ocurrencia de t&eacute;rminos clave.</span> Atribuci&oacute;n de
      liderazgo sobre el l&eacute;xico definido (&ldquo;confianza&rdquo;, &ldquo;l&iacute;der&rdquo;, &ldquo;cambio&rdquo;&hellip;).</li>
    <li><span class="lead">Validaci&oacute;n acad&eacute;mica del clasificador.</span> Subconjunto codificado a mano
      con reporte de <b>Kappa de Cohen, F1 y matriz de confusi&oacute;n</b> &mdash; el est&aacute;ndar que blinda la
      sustentaci&oacute;n.</li>
    <li><span class="lead">Matriz de Registro diligenciada + archivo listo para SPSS.</span> Con prueba de
      normalidad (Shapiro&ndash;Wilk) y <b>correlaci&oacute;n Rho de Spearman</b> ya corrida e interpretada (H3).</li>
    <li><span class="lead">Tablero interactivo.</span> Serie temporal del Net Sentiment frente a los picos de
      crisis (&Iacute;ndice de Crisis Digital &gt; 2&sigma;) y mapa de co-ocurrencia l&eacute;xica.</li>
    <li><span class="lead">Memorando metodol&oacute;gico + paquete reproducible.</span> Procedencia de datos,
      l&iacute;mites, &eacute;tica y f&oacute;rmulas (NSS / TE / TV / ICD / AL), documentado para defensa ante el jurado.</li>
  </ul>

  <div class="cmpwrap">
  <div class="block-label dash" style="margin-top:0">POR QU&Eacute; ESTE SERVICIO Y NO OTRO</div>
  <table class="cmp">
    <thead>
      <tr>
        <th>Criterio</th>
        <th>Freelancer &middot; herramienta de IA gen&eacute;rica</th>
        <th class="us">Ricardo.Ruiz</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td class="crit">Extracci&oacute;n de datos</td>
        <td class="comp">Scraper fr&aacute;gil con cuenta personal; se rompe a mitad y arriesga bloqueo.</td>
        <td class="us">Extracci&oacute;n <b>gestionada con proxies</b> + capa propia de validaci&oacute;n de m&eacute;tricas.</td>
      </tr>
      <tr>
        <td class="crit">An&aacute;lisis de sentimiento</td>
        <td class="comp">Caja negra (ChatGPT / Brandwatch) que el jurado no puede auditar.</td>
        <td class="us">Clasificador <b>transparente y auditable</b>, afinado a espa&ntilde;ol colombiano.</td>
      </tr>
      <tr>
        <td class="crit">Validaci&oacute;n del m&eacute;todo</td>
        <td class="comp">Ninguna. &ldquo;Conf&iacute;a en que el modelo acert&oacute;.&rdquo;</td>
        <td class="us"><b>Kappa de Cohen + F1 + matriz de confusi&oacute;n</b> sobre muestra codificada a mano.</td>
      </tr>
      <tr>
        <td class="crit">Defensa ante el jurado</td>
        <td class="comp">&ldquo;Lo corr&iacute; en mi PC&rdquo; &mdash; indefendible si preguntan c&oacute;mo.</td>
        <td class="us"><b>Memo metodol&oacute;gico</b> + procedencia reproducible de cada dato.</td>
      </tr>
      <tr>
        <td class="crit">Entregables</td>
        <td class="comp">Un CSV suelto. T&uacute; armas la matriz y corres SPSS.</td>
        <td class="us">Matriz diligenciada + <b>SPSS con Spearman corrido</b> + tablero interactivo.</td>
      </tr>
      <tr>
        <td class="crit">Honestidad de l&iacute;mites</td>
        <td class="comp">Rellena con m&eacute;tricas que ya no se pueden medir (impresiones).</td>
        <td class="us">Declara lo no medible y <b>ajusta la f&oacute;rmula</b>, sin sorpresas en la defensa.</td>
      </tr>
    </tbody>
  </table>
  </div>

  <div class="note keep">
    <div class="nl">NOTA DE TRANSPARENCIA</div>
    <p>Las <b>impresiones</b> y el <b>CTR</b> de cuentas ajenas <b>no son recuperables retroactivamente</b> en X.
      Las m&eacute;tricas de impacto (V1) se fijan a las p&uacute;blicas verificables (likes, reposts, respuestas,
      quotes) y la tasa de engagement se calcula con un denominador documentado. El an&aacute;lisis de
      sentimiento se realiza sobre los <b>mensajes del mandatario</b> (tono e intensidad emocional, que es lo
      que sostiene la H3); incorporar el sentimiento de las <b>respuestas del p&uacute;blico</b> se cotiza como
      ampliaci&oacute;n. Todo queda expl&iacute;cito en el memorando para evitar observaciones del jurado.</p>
  </div>

  <div class="block-label dash keep">PLANES E INVERSI&Oacute;N</div>
  <div class="amount keep">
    <div class="words">__WORDS__</div>
    <div class="num"><span class="cop">DESDE COP</span><span class="big">__PRECIO__</span>
      <span class="usd">&asymp; __USD__ &middot; herramientas de extracci&oacute;n incluidas</span></div>
  </div>

  <table class="det keep">
    <thead>
      <tr><th>PLAN</th><th class="r">INCLUYE</th><th class="r">INVERSI&Oacute;N</th></tr>
    </thead>
    <tbody>
      <tr>
        <td class="desc">
          <div class="t">Esencial <span>RECOMENDADO</span></div>
          <div class="d">Extracci&oacute;n segura de las 3 crisis + QA &middot; sentimiento PLN (es-CO) &middot;
            t&eacute;rminos clave &middot; <b>validaci&oacute;n con Kappa de Cohen</b> &middot; matriz diligenciada +
            archivo SPSS con Spearman corrido &middot; memorando metodol&oacute;gico reproducible &middot;
            gr&aacute;ficos del informe. Herramientas de extracci&oacute;n incluidas.</div>
        </td>
        <td class="tag">Todo lo<br>defendible</td>
        <td class="val">__PRECIO__</td>
      </tr>
      <tr>
        <td class="desc">
          <div class="t">Completo</div>
          <div class="d">Todo lo del Esencial <b>+ tablero interactivo</b>: serie temporal del Net Sentiment
            frente a los picos de crisis (&Iacute;ndice de Crisis Digital &gt; 2&sigma;) y mapa de co-ocurrencia
            l&eacute;xica.</div>
        </td>
        <td class="tag">Con tablero</td>
        <td class="val">__COMPLETO__</td>
      </tr>
      <tr class="opt">
        <td class="desc">
          <div class="t">Acompa&ntilde;amiento a la sustentaci&oacute;n <span>OPCIONAL</span></div>
          <div class="d">Diapositivas del cap&iacute;tulo, ensayo de defensa y gui&oacute;n de respuestas a las
            preguntas probables del jurado sobre el m&eacute;todo cuantitativo.</div>
        </td>
        <td class="tag">Se suma</td>
        <td class="val">+ __ADDON__</td>
      </tr>
    </tbody>
  </table>

  <div class="grid2 keep">
    <div>
      <div class="block-label">CONDICIONES</div>
      <div class="frow tight"><span class="k">PAGO</span><span class="v">50% para iniciar &middot; 50% contra entrega</span></div>
      <div class="frow tight"><span class="k">PLAZO</span><span class="v">7 d&iacute;as h&aacute;biles desde confirmaci&oacute;n</span></div>
      <div class="frow tight"><span class="k">INICIO</span><span class="v">Al cerrar las fechas de las 3 crisis</span></div>
      <div class="frow tight"><span class="k">MONEDA</span><span class="v">COP (ref. US$ a tasa del d&iacute;a)</span></div>
      <div class="frow tight"><span class="k">R&Eacute;GIMEN</span><span class="v">No responsable de IVA</span></div>
    </div>
    <div>
      <div class="block-label">PAGO EN L&Iacute;NEA</div>
      <div class="frow tight"><span class="k">ENLACE</span><span class="v">__PAGOURL__</span></div>
      <div class="frow tight"><span class="k">TARJETA</span><span class="v">Cr&eacute;dito / d&eacute;bito &middot; Visa &middot; Mastercard &middot; Amex</span></div>
      <div class="frow tight"><span class="k">TAMBI&Eacute;N</span><span class="v">PSE &middot; Nequi &middot; Bot&oacute;n Bancolombia &middot; efectivo</span></div>
      <div class="frow tight"><span class="k">CUOTAS</span><span class="v">Difi&eacute;relo a cuotas con tu tarjeta de cr&eacute;dito</span></div>
      <div class="frow tight"><span class="k">PASARELA</span><span class="v">Wompi (Bancolombia) &middot; pago seguro</span></div>
    </div>
  </div>

  <div class="signs keep">
    <div>
      <div class="sname">Ricardo Esteban Ruiz Castro</div>
      <div class="scap">CONSULTOR &middot; ricardoruiz.co &middot; BOGOT&Aacute; D.C.</div>
    </div>
    <div>
      <div class="sname">Aceptaci&oacute;n del cliente</div>
      <div class="scap">CARLOS HENRY RODR&Iacute;GUEZ SALGADO &middot; FECHA: ____ / ____ / 2026</div>
    </div>
  </div>

  <div class="footer">
    <div class="notes"><b>Validez de la oferta:</b> 30 d&iacute;as calendario. El valor incluye las herramientas
      de extracci&oacute;n. El sentimiento se mide sobre las publicaciones del mandatario; el an&aacute;lisis de
      respuestas del p&uacute;blico se cotiza aparte. Documento privado, sin valor tributario hasta la emisi&oacute;n
      de la cuenta de cobro correspondiente.</div>
    <div class="by">Preparado por<br><b>RICARDO ESTEBAN RUIZ CASTRO</b><br>ricardoruiz.co</div>
  </div>

</body>
</html>"""

HTML_DOC = (HTML_DOC
            .replace("__SYNE__", FONT_SYNE)
            .replace("__WORDS__", PRECIO_BASE_W)
            .replace("__USD__", PRECIO_BASE_USD)
            .replace("__COMPLETO__", PRECIO_COMPLETO)
            .replace("__ADDON__", PRECIO_ADDON)
            .replace("__PAGOURL__", PAGO_URL)
            .replace("__FECHA__", FECHA)
            .replace("__PRECIO__", PRECIO_BASE))


def build():
    HTML(string=HTML_DOC).write_pdf(OUT)
    return os.path.getsize(OUT)


if __name__ == "__main__":
    n = build()
    print(f"PDF generado: {OUT}  ({n/1024:.1f} KB)")
