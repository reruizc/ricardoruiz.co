#!/usr/bin/env python3
"""
Brief comercial de Candidato 360 · 6 láminas apaisadas (A4 horizontal).

Es el PDF que se descarga desde los botones «¿Cómo funciona?» y «¿Por qué
elegirnos?» de la portada (candidato-360.html, INTRO_INFO → BRIEF_PDF). Cada
lámina cabe en una página: si el texto crece, hay que recortarlo, no dejar que
salte de página.

Láminas: 1 portada con tres diferenciales · 2 cómo funciona (cinco pasos +
once módulos) · 3 arquetipos por barrio · 4 por qué elegirnos (lo habitual
contra lo que hace Candidato 360, curaduría mensual, lo que no hacemos) ·
5 su territorio mes a mes (Policía, DANE, Ministerio de Educación; es la
tarjeta 12 del CRM) · 6 planes.

Imágenes: los pictogramas de las fases (assets/candidato-360/fases/*.webp) y
dos dibujados a mano en el mismo estilo (assets/candidato-360/brief/*.svg).

Identidad: la de Candidato 360 (papel, azul noche, verde azulado, coral), no
el sistema visual v2 oscuro del sitio. Helvetica Neue del repo; Syne solo en
el nombre. Los precios salen de la escalera de candidato-360-brief.html
(BASE_LISTA 300.000 × factor por corporación; completo 1.100.000 de lista)
MÁS el 20 % que Ricardo pidió para el brief el 26-oct-2026 (SUBIDA). La
página candidato-360-brief.html todavía no lleva esa subida.

    python3 tools/candidato-360/brief-comercial/build.py

Salida: assets/candidato-360/Candidato-360-brief-comercial.pdf (público, lo
sirve GitHub Pages).
"""
import os
import datetime
from weasyprint import HTML

ROOT = "/Users/ricardoruiz/ricardoruiz.co"
OUT = os.path.join(ROOT, "assets", "candidato-360", "Candidato-360-brief-comercial.pdf")
FDIR = os.path.join(ROOT, "fonts")
F_SYNE = os.path.join(ROOT, "tools", "build-propuesta-tesis-oe3", "fonts", "Syne-ExtraBold.ttf")

_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
_hoy = datetime.date.today()
FECHA = f"{_MESES[_hoy.month - 1].capitalize()} de {_hoy.year}"

# ── Precios «desde» por corporación: escalera del brief vigente (tamaño 1,0) ──
BASE_LISTA, COMPLETO_LISTA = 300_000, 1_100_000
SUBIDA = 1.2   # +20 % sobre la escalera del brief web (26-oct-2026)
FACTOR = [("Junta Administradora Local", 1.0), ("Concejo", 1.4), ("Alcaldía", 1.8),
          ("Asamblea", 2.4), ("Gobernación", 3.0)]
cop = lambda n: "$" + f"{round(n / 10_000) * 10_000:,}".replace(",", ".")
PRECIOS = [(c, cop(BASE_LISTA * f * SUBIDA), cop(COMPLETO_LISTA * f * SUBIDA)) for c, f in FACTOR]
DESDE = cop(BASE_LISTA * SUBIDA)
IMG = lambda n: f"file://{ROOT}/assets/candidato-360/{n}"

CSS = f"""
@font-face{{font-family:HN;src:url('file://{FDIR}/helveticaneue.woff2')}}
@font-face{{font-family:HN;font-weight:700;src:url('file://{FDIR}/helveticaneue-bold.woff2')}}
@font-face{{font-family:HN;font-weight:500;src:url('file://{FDIR}/helveticaneue-medium.woff2')}}
@font-face{{font-family:HN;font-style:italic;src:url('file://{FDIR}/helveticaneue-italic.woff2')}}
@font-face{{font-family:HN;font-weight:300;src:url('file://{FDIR}/helveticaneue-light.woff2')}}
@font-face{{font-family:Syne;font-weight:800;src:url('file://{F_SYNE}')}}
@page{{size:A4 landscape;margin:0}}
*{{box-sizing:border-box}}
body{{font:9.6pt/1.45 HN,Helvetica,Arial,sans-serif;color:#102238;margin:0}}
.lam{{width:297mm;height:210mm;padding:14mm 16mm 12mm;position:relative;overflow:hidden;background:#f6f1e8;break-after:page}}
.lam:last-child{{break-after:auto}}
.lam.oscura{{background:#102b46;color:#f6f1e8}}
.marca{{font:800 13pt Syne;letter-spacing:-.02em;color:#102b46}} .marca b{{color:#ef705d}}
.oscura .marca{{color:#f6f1e8}}
.cab{{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid rgba(16,34,56,.18);padding-bottom:3mm;margin-bottom:6mm}}
.oscura .cab{{border-color:rgba(246,241,232,.25)}}
.cab .ojo{{font:700 7.4pt HN;letter-spacing:.18em;text-transform:uppercase;color:#147c70}}
.oscura .cab .ojo{{color:#b9ded2}}
h1{{font:700 34pt/1.04 HN;letter-spacing:-.025em;margin:0 0 6mm;max-width:190mm}}
h2{{font:700 21pt/1.1 HN;letter-spacing:-.02em;color:#102b46;margin:0 0 2mm}}
h2 span{{display:block;font:700 7.4pt HN;letter-spacing:.18em;text-transform:uppercase;color:#ef705d;margin-bottom:1.6mm}}
.lead{{font:300 12pt/1.45 HN;color:#22364d;max-width:200mm;margin:0 0 6mm}}
.oscura .lead{{color:#dfe8ea}}
.pie{{position:absolute;left:16mm;right:16mm;bottom:9mm;display:flex;justify-content:space-between;font:400 7.6pt/1.5 HN;color:#637080;border-top:1px solid rgba(16,34,56,.14);padding-top:2.6mm}}
.oscura .pie{{color:#b9c6cf;border-color:rgba(246,241,232,.25)}}
.pie b{{color:#102b46}} .oscura .pie b{{color:#f6f1e8}}
/* portada */
.cifras{{display:flex;gap:6mm;margin-top:14mm}}
.cifra{{flex:1;border-top:3px solid #ef705d;padding-top:3mm}}
.cifra b{{display:block;font:700 26pt/1 HN;letter-spacing:-.03em;color:#fff;margin-bottom:1.6mm}}
.cifra span{{font:400 9.2pt/1.4 HN;color:#b9ded2}}
.portada-sub{{font:300 13.5pt/1.45 HN;color:#dfe8ea;max-width:190mm;margin:0}}
/* pasos */
.pasos{{display:flex;gap:4mm;margin:0 0 6mm}}
.paso{{flex:1;background:#fffdf8;border:1px solid rgba(16,34,56,.14);padding:4mm 4mm 3.6mm;box-shadow:3mm 3mm 0 #b9ded2}}
.paso i{{display:inline-grid;place-items:center;width:8mm;height:8mm;background:#102b46;color:#fff;font:700 10pt HN;font-style:normal;margin-bottom:2.4mm}}
.paso b{{display:block;font:700 10.4pt/1.2 HN;color:#102b46;margin-bottom:1.6mm}}
.paso p{{margin:0;font-size:8.6pt;line-height:1.42;color:#3a4a5c}}
.modulos{{display:grid;grid-template-columns:repeat(4,1fr);gap:2.2mm 4mm}}
.mod{{border-top:1px solid rgba(16,34,56,.18);padding-top:1.6mm;font-size:8pt;line-height:1.38;color:#3a4a5c}}
.mod b{{display:block;color:#102b46;font-size:8.6pt}} .mod b i{{font-style:normal;color:#147c70;font-weight:700;margin-right:1.2mm}}
.h3{{font:700 7.4pt HN;letter-spacing:.18em;text-transform:uppercase;color:#147c70;margin:0 0 2.4mm}}
/* por qué */
table{{width:100%;border-collapse:collapse;font-size:8.4pt;line-height:1.4}}
th{{background:#102b46;color:#f6f1e8;font:700 7.2pt HN;letter-spacing:.1em;text-transform:uppercase;text-align:left;padding:2mm 2.6mm}}
td{{padding:2mm 2.6mm;border-bottom:.6px solid rgba(16,34,56,.16);vertical-align:top}}
td.q{{font-weight:700;color:#102b46;width:34mm}} td.ellos{{color:#637080;width:78mm}} td.nos b{{color:#147c70}}
tbody tr:nth-child(even) td{{background:#fffdf8}}
.dos{{display:grid;grid-template-columns:1fr 62mm;gap:6mm;align-items:start}}
.caja{{background:#fffdf8;border-left:3px solid #ef705d;padding:3mm 3.6mm;font-size:8.1pt;line-height:1.42;color:#3a4a5c}}
.caja b{{display:block;color:#102b46;font-size:9.4pt;margin-bottom:1.2mm}}
.caja.verde{{border-color:#147c70;margin-top:3mm}}
.caja ul{{margin:1mm 0 0;padding-left:4mm}} .caja li{{margin-bottom:1.2mm}}
/* planes */
.planes{{display:grid;grid-template-columns:1.15fr 1fr;gap:8mm;align-items:start}}
.formas{{display:flex;gap:3.5mm;margin:0 0 5mm}}
.forma{{flex:1;background:#fffdf8;border:1px solid rgba(16,34,56,.14);padding:3.6mm 3.8mm}}
.forma.star{{background:#102b46;color:#f6f1e8;border-color:#102b46}}
.forma b{{display:block;font:700 11pt/1.15 HN;margin-bottom:1.4mm}} .forma.star b{{color:#fff}}
.forma em{{display:block;font:700 8pt HN;font-style:normal;color:#ef705d;margin-bottom:2mm}}
.forma p{{margin:0;font-size:8.2pt;line-height:1.4;color:#3a4a5c}} .forma.star p{{color:#dfe8ea}}
.tabla-precios td:nth-child(2),.tabla-precios td:nth-child(3){{font-weight:700;color:#102b46;white-space:nowrap}}
.pasos-v{{counter-reset:n;margin:0;padding:0;list-style:none}}
.pasos-v li{{position:relative;padding:0 0 0 11mm;margin:0 0 3.2mm;font-size:9pt;line-height:1.42;color:#3a4a5c}}
.pasos-v li b{{color:#102b46}}
.pasos-v li::before{{counter-increment:n;content:counter(n);position:absolute;left:0;top:0;width:8mm;height:8mm;display:grid;place-items:center;background:#ef705d;color:#fff;font:700 10pt HN}}
.contacto{{margin-top:5mm;background:#fffdf8;border:1px solid rgba(16,34,56,.14);padding:3.6mm 4mm;font-size:9pt;line-height:1.5}}
.contacto b{{color:#102b46}}
small{{color:#637080;font-size:7.6pt}}
.top{{display:grid;grid-template-columns:1fr 64mm;gap:8mm;align-items:center;margin-bottom:4mm}}
.top .lead{{margin-bottom:0}}
.top img{{width:64mm;height:42.6mm;object-fit:cover;display:block;border:1px solid rgba(16,34,56,.12)}}
.portada-grid{{display:grid;grid-template-columns:1fr 92mm;gap:10mm;align-items:center;margin-top:10mm}}
.portada-grid img{{width:92mm;height:61.3mm;object-fit:cover;display:block;border:3px solid #f6f1e8}}
.cifra b.t{{font-size:15pt;line-height:1.12;letter-spacing:-.015em}}
.ciudades{{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm;margin:0 0 4mm}}
.ciudad{{background:#fffdf8;border:1px solid rgba(16,34,56,.14);border-top:3px solid #147c70;padding:3.4mm 3.8mm}}
.ciudad b{{display:block;font:700 11pt HN;color:#102b46}}
.ciudad em{{display:block;font-style:normal;font:700 7.4pt HN;letter-spacing:.08em;text-transform:uppercase;color:#ef705d;margin:.8mm 0 1.8mm}}
.ciudad p{{margin:0 0 1.6mm;font-size:8.2pt;line-height:1.4;color:#3a4a5c}}
.chips{{display:flex;flex-wrap:wrap;gap:1.2mm}}
.chip{{font:500 7.2pt HN;background:#f6f1e8;border:1px solid rgba(16,34,56,.16);padding:.6mm 1.8mm;color:#102b46}}
.entrega{{display:grid;grid-template-columns:repeat(4,1fr);gap:3.5mm}}
.entrega div{{border-top:1px solid rgba(16,34,56,.2);padding-top:1.8mm;font-size:8.2pt;line-height:1.4;color:#3a4a5c}}
.entrega b{{display:block;color:#102b46;font-size:8.8pt;margin-bottom:.6mm}}
.banda{{background:#102b46;color:#f6f1e8;padding:2.8mm 4.4mm;margin:0 0 3mm;display:grid;grid-template-columns:44mm 1fr;gap:5mm;align-items:center}}
.banda b{{font:700 12.5pt/1.15 HN;color:#fff}}
.banda span{{font-size:8.8pt;line-height:1.45;color:#dfe8ea}}
.fuentes3{{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm;margin:0 0 5mm}}
.fuente{{background:#fffdf8;border:1px solid rgba(16,34,56,.14);padding:3.6mm 4mm;box-shadow:2.6mm 2.6mm 0 #b9ded2}}
.fuente em{{display:block;font-style:normal;font:700 7.2pt HN;letter-spacing:.14em;text-transform:uppercase;color:#147c70;margin-bottom:1.2mm}}
.fuente b{{display:block;font:700 11pt/1.2 HN;color:#102b46;margin-bottom:1.6mm}}
.fuente p{{margin:0;font-size:8.4pt;line-height:1.45;color:#3a4a5c}}
.fuente small{{display:block;margin-top:2mm}}
.dos table{{font-size:7.9pt;line-height:1.34}} .dos td{{padding:1.5mm 2.2mm}} .dos th{{padding:1.6mm 2.2mm}}
.ciudad p{{font-size:9.2pt;line-height:1.45}} .chip{{font-size:8pt;padding:.8mm 2mm}} .ciudad{{padding:4.4mm 4.6mm}}
.ciudad em{{margin-bottom:2.4mm}} .entrega div{{font-size:9.2pt;line-height:1.45}} .entrega b{{font-size:10pt}}
.fuente p{{font-size:9.6pt;line-height:1.5}} .fuente b{{font-size:12.5pt}} .fuente{{padding:5mm 5mm 4.4mm}}
.lam5 .caja{{font-size:9.6pt;padding:4mm 4.6mm}} .lam5 .caja b{{font-size:11pt}}
"""

MODULOS = [
    ("01", "Mapa del historial", "Su votación, puesto por puesto: localidad, comuna, barrio donde hay cartografía."),
    ("02", "Meta de votos", "Cuántos necesita, con la ley electoral, en cuatro escalones."),
    ("03", "Briefing cada 3 días", "Prensa, contratos públicos y normas de su territorio, en su correo."),
    ("04", "Escucha social", "Lo que se dice de usted en prensa y redes, por temas y lugares."),
    ("05", "Arquetipos", "Qué mueve el voto en cada barrio: Bogotá, Medellín y Cartagena."),
    ("06", "Perfil del votante", "Quién puede votar por usted, con el censo de 2026 por sexo y edad."),
    ("07", "Firmas", "Si va sin aval: cuántas exige la ley y dónde cuesta menos reunirlas."),
    ("08", "Endoso de aliados", "Cuántos votos le pueden pasar los candidatos y listas afines."),
    ("09", "Día de la elección", "En qué puestos necesita testigo y la ficha logística de cada uno."),
    ("10", "Contendientes", "Contra quién compite y dónde se pelea el voto."),
    ("11", "Estrategia", "Plan por fases: posicionamiento, campaña, remate y día D."),
]

VENTAJAS = [
    ("Historial electoral",
     "Resultados por municipio, a veces por puesto, solo en planes para partidos.",
     "<b>Mesa a mesa, 2010 a 2026, todas las corporaciones</b>, buscable por el nombre del candidato, y <b>cada puesto conectado con su barrio</b>."),
    ("Meta de votos",
     "Una casilla que la campaña llena a ojo.",
     "<b>Calculada con la ley</b>: umbral, cifra repartidora y curules reales, en cuatro escalones del mínimo al deseado, repartida por localidad y barrio."),
    ("Electorado",
     "Demografía general del municipio.",
     "<b>Censo oficial de 2026 puesto por puesto</b>, por sexo y edad, y <b>arquetipos por barrio</b>: qué mueve el voto en cada uno."),
    ("Rivales y aliados",
     "«Análisis de oposición» en redes, sin votos.",
     "<b>Medidos con votos y revisados cada mes</b>: contra quién compite, dónde se pelea el voto y cuántos votos le pueden pasar sus aliados."),
    ("Día de la elección",
     "Una app de testigos que opera ese día.",
     "<b>El plan antes del día</b>: en qué puestos necesita testigo y la ficha logística de cada uno (señal, internet, acceso, orden público)."),
    ("Información del territorio",
     "Escucha de redes, cobrada aparte.",
     "<b>Seguridad, empleo, contratos y normas</b> de su territorio, actualizados cada mes, y la prensa en su correo cada tres días."),
    ("Precio",
     "Cotización por demo; sin cifras públicas.",
     f"<b>Publicado, por mes y por módulos</b>, desde {DESDE}. Se cancela cuando quiera."),
]


def modulos_html():
    return "".join(f'<div class="mod"><b><i>{n}</i>{t}</b>{d}</div>' for n, t, d in MODULOS)


def ventajas_html():
    filas = "".join(f'<tr><td class="q">{q}</td><td class="ellos">{e}</td><td class="nos">{n}</td></tr>'
                    for q, e, n in VENTAJAS)
    return f'<table><thead><tr><th></th><th>Lo que suele ofrecerse</th><th>Lo que hace Candidato 360</th></tr></thead><tbody>{filas}</tbody></table>'


def precios_html():
    filas = "".join(f"<tr><td>{c}</td><td>{b}</td><td>{f}</td></tr>" for c, b, f in PRECIOS)
    return f'<table class="tabla-precios"><thead><tr><th>Corporación</th><th>Base, desde</th><th>Completo, desde</th></tr></thead><tbody>{filas}</tbody></table>'


PIE = f'<div class="pie"><span><b>Candidato 360</b> · ricardoruiz.co/candidato-360.html · hola@ricardoruiz.co</span><span>Brief comercial · {FECHA}</span></div>'

HTML_DOC = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>{CSS}</style></head><body>

<div class="lam oscura">
  <div class="cab"><div class="marca">Candidato <b>360</b></div><div class="ojo">Plataforma electoral · Elecciones territoriales de Colombia · octubre de 2027</div></div>
  <div class="portada-grid">
    <div>
      <h1 style="color:#fff">Su campaña empieza con evidencia.</h1>
      <p class="portada-sub">Un CRM electoral que convierte los resultados oficiales y el censo en decisiones de campaña: dónde están sus votos, cuántos le faltan y qué hacer para conseguirlos. Para concejo, alcaldía, JAL, asamblea y gobernación.</p>
    </div>
    <img src="{IMG('fases/planeacion.webp')}" alt="">
  </div>
  <div class="cifras">
    <div class="cifra"><b>Más de 400.000</b><span>candidaturas de 2010 a 2026, mesa a mesa y buscables por nombre</span></div>
    <div class="cifra"><b class="t">Su perfil y el de su familia política</b><span>quién es usted como candidato y cómo vota el partido o el sector ideológico por el que se lanza</span></div>
    <div class="cifra"><b class="t">Puestos conectados con sus barrios</b><span>la lista de puestos existe; saber en qué barrio está cada voto, no. Nosotros lo cruzamos</span></div>
  </div>
  {PIE}
</div>

<div class="lam">
  <div class="cab"><div class="marca">Candidato <b>360</b></div><div class="ojo">Lámina 2 de 6 · Cómo funciona</div></div>
  <div class="top"><div>
    <h2><span>Así funciona</span>De su nombre a su plan de campaña, en una sesión.</h2>
    <p class="lead">Cinco pasos. Los dos primeros los da usted; los otros tres los da la plataforma con datos oficiales.</p>
  </div><img src="{IMG('fases/posicionamiento.webp')}" alt=""></div>
  <div class="pasos">
    <div class="paso"><i>1</i><b>Díganos quién es</b><p>Si ya se lanzó, lo buscamos entre más de 400.000 candidaturas y traemos su historial mesa a mesa. Si es su primera vez, bastan seis preguntas.</p></div>
    <div class="paso"><i>2</i><b>Elija a qué se lanza</b><p>Corporación, territorio y aval: partido o firmas. Con eso armamos su perfil y el de su familia política.</p></div>
    <div class="paso"><i>3</i><b>Reciba su punto de partida</b><p>El mapa de su votación por barrio y puesto, la meta calculada con la ley y quién puede votar por usted, con el censo de 2026.</p></div>
    <div class="paso"><i>4</i><b>Lea el territorio</b><p>Arquetipos por barrio, contendientes y aliados revisados cada mes, y lo que dicen la prensa y las redes.</p></div>
    <div class="paso"><i>5</i><b>Planee y ejecute</b><p>Hoja de ruta en cinco etapas, plan del día de la elección puesto por puesto y un briefing en su correo cada tres días.</p></div>
  </div>
  <div class="h3">Los once módulos del tablero</div>
  <div class="modulos">{modulos_html()}</div>
  {PIE}
</div>

<div class="lam">
  <div class="cab"><div class="marca">Candidato <b>360</b></div><div class="ojo">Lámina 3 de 6 · Arquetipos</div></div>
  <div class="top"><div>
    <h2><span>Lo que nadie más tiene</span>Qué mueve el voto en cada barrio.</h2>
    <p class="lead">Un arquetipo es una forma de votar que se repite en varios barrios: qué decide a la gente de ahí, qué la moviliza y qué la aleja. Ningún programa de campaña que revisamos, en Colombia ni afuera, lo ofrece.</p>
  </div><img src="{IMG('fases/campana.webp')}" alt=""></div>
  <div class="ciudades">
    <div class="ciudad"><b>Medellín</b><em>5 arquetipos · 152 barrios</em><p>Cartografía emocional del voto barrial de 2015 a 2023, con su proyección a 2027.</p><div class="chips"><span class="chip">Protección con resultados</span><span class="chip">Castigo y alternancia</span><span class="chip">Continuidad pragmática</span><span class="chip">Supervivencia económica</span><span class="chip">Pertenencia comunitaria</span></div></div>
    <div class="ciudad"><b>Cartagena</b><em>8 tipologías · 211 barrios</em><p>Tipologías propias de la ciudad, con la mezcla de las ocho en cada barrio.</p><div class="chips"><span class="chip">Orden que Cumple</span><span class="chip">Ojo al Poder</span><span class="chip">Barrio que Resuelve</span><span class="chip">Cambio de Verdad</span><span class="chip">Orgullo de Tierra</span><span class="chip">Que Miren la Isla</span><span class="chip">Primero el Trabajo</span><span class="chip">El que Responde</span></div></div>
    <div class="ciudad"><b>Bogotá</b><em>8 por corporación · 519 barrios</em><p>Salen de cómo vota cada barrio en Concejo, Alcaldía y presidencial, con su estrato. Al Concejo, por ejemplo:</p><div class="chips"><span class="chip">Clase media sin dueño</span><span class="chip">Norte de opinión</span><span class="chip">Norte de figuras</span><span class="chip">Barrio de gestión</span><span class="chip">Periferia de partido</span><span class="chip">Ciudadela movilizada</span></div></div>
  </div>
  <div class="h3">Lo que le entrega</div>
  <div class="entrega">
    <div><b>Su arquetipo principal</b>Y su ascendente: con qué forma de votar se parece más su votación, medido barrio por barrio.</div>
    <div><b>Dónde pesa cada uno</b>Los barrios de su territorio por arquetipo, con su votación y la de su familia política.</div>
    <div><b>Cómo hablarle</b>Qué lo activa, qué lo desmoviliza, el tono y los canales que funcionan con cada uno.</div>
    <div><b>Qué pasa si…</b>Un simulador: si la seguridad o el empleo empeoran, qué barrios cambian de ánimo.</div>
  </div>
  {PIE}
</div>

<div class="lam">
  <div class="cab"><div class="marca">Candidato <b>360</b></div><div class="ojo">Lámina 4 de 6 · Por qué elegirnos</div></div>
  <div class="top"><div>
    <h2><span>Por qué elegirnos</span>Lo que ningún otro programa de campaña le muestra.</h2>
    <p class="lead">Los demás administran a su gente. Candidato 360 le dice dónde están los votos, cuántos le faltan y qué hacer para conseguirlos.</p>
  </div><img src="{IMG('fases/remate.webp')}" alt=""></div>
  <div class="banda"><b>Curamos la información cada mes.</b><span>Cada mes revisamos sus contendientes y sus aliados: quién entra, quién se baja, quién cambia de partido o de aval. La campaña se mueve con el posicionamiento, y la lectura se mueve con ella.</span></div>
  <div class="dos">
    <div>{ventajas_html()}</div>
    <div>
      <div class="caja"><b>Lo que no hacemos, a propósito</b>No guardamos su base de contactos ni hacemos envíos masivos por WhatsApp: su información sigue siendo suya y su campaña no corre el riesgo de un bloqueo.</div>
      <div class="caja verde"><b>Cada cifra con su fuente</b>Resultados oficiales de la Registraduría y censo electoral. Cuando algo se estima, se dice con qué. El voto es secreto: se describe el censo de los puestos, nunca a las personas.</div>
    </div>
  </div>
  {PIE}
</div>

<div class="lam lam5">
  <div class="cab"><div class="marca">Candidato <b>360</b></div><div class="ojo">Lámina 5 de 6 · Su territorio, mes a mes</div></div>
  <div class="top"><div>
    <h2><span>Datos del territorio</span>Lo que pasa en su territorio, cada mes.</h2>
    <p class="lead">La tarjeta 12 del tablero, en las etapas de planeación, posicionamiento y campaña: las bases públicas que se actualizan cada mes, leídas para su localidad si va a una JAL, su municipio si va a un concejo o una alcaldía, y su departamento si va a una asamblea o una gobernación.</p>
  </div><img src="{IMG('brief/territorio-mes.svg')}" alt=""></div>
  <div class="fuentes3">
    <div class="fuente"><em>Seguridad</em><b>Delitos de la Policía Nacional</b><p>Homicidios, hurtos, violencia intrafamiliar, extorsión y diecisiete delitos más, por municipio. En las ciudades principales, por comuna y barrio: mes contra mes y año corrido.</p><small>Policía Nacional y Ministerio de Defensa</small></div>
    <div class="fuente"><em>Empleo</em><b>Mercado laboral del DANE</b><p>Desempleo, ocupación e informalidad en las 32 capitales, y en 23 ciudades con su área metropolitana el trimestre que el DANE publica cada mes.</p><small>DANE · Gran Encuesta Integrada de Hogares</small></div>
    <div class="fuente"><em>Educación</em><b>Cobertura y deserción escolar</b><p>Cuántos niños de 5 a 16 años están matriculados y cuántos dejan el colegio en el año, de 2018 a hoy, por municipio.</p><small>Ministerio de Educación Nacional</small></div>
  </div>
  <div class="caja verde" style="margin-top:0"><b>Para qué le sirve</b>Frases listas para cada discurso y cada debate, armadas con esas cifras: dónde subió el hurto, cuánto pesa su localidad en la ciudad, cómo está el desempleo frente al país. Con la fuente al lado, para que nadie se las pueda discutir. Los contratos públicos y las normas de su territorio le llegan aparte, en el briefing cada tres días.</div>
  {PIE}
</div>

<div class="lam">
  <div class="cab"><div class="marca">Candidato <b>360</b></div><div class="ojo">Lámina 6 de 6 · Planes y cómo empezar</div></div>
  <div class="top"><div>
    <h2><span>Planes</span>Un precio por mes. Sin contratos largos.</h2>
    <p class="lead">La base incluye el mapa, la meta, el electorado y las firmas. Cada módulo se suma aparte y se activa o se quita cualquier mes. El precio escala con la corporación y con el tamaño del territorio.</p>
  </div><img src="{IMG('fases/dia.webp')}" alt=""></div>
  <div class="planes">
    <div>
      <div class="formas">
        <div class="forma"><b>Esencial</b><em>Base + briefing</em><p>Para arrancar con el territorio claro y la meta puesta, con su territorio en el correo cada tres días.</p></div>
        <div class="forma star"><b>Con escucha</b><em>El más elegido</em><p>La base, el briefing y la escucha social dos veces al día en X, Instagram, TikTok y Facebook.</p></div>
        <div class="forma"><b>Completo</b><em>Todo el tablero</em><p>Briefing, escucha con sentimiento, arquetipos, endoso, estrategia y acciones, en un solo lugar.</p></div>
      </div>
      {precios_html()}
      <small>Pesos colombianos por mes, IVA incluido, para el territorio más pequeño de cada corporación; una ciudad o un departamento grande sube hasta 1,6 veces. Precios de lista a {FECHA.lower()}; la cotización exacta se arma en la plataforma.</small>
    </div>
    <div>
      <div class="h3">Cómo empezar</div>
      <ol class="pasos-v">
        <li><b>Entre con su nombre.</b> La búsqueda es abierta: vea su historial, el mapa de su votación y su meta antes de pagar.</li>
        <li><b>Arme su candidatura.</b> Diga a qué se lanza, con qué aval y en qué territorio. Puede hacerlo sin cuenta.</li>
        <li><b>Active el acceso.</b> Una cuenta se vincula a un solo candidato. La corporación y el territorio sí se ajustan cuando quiera.</li>
        <li><b>La primera semana.</b> Escriba sus ideas de campaña y conecte sus redes: el primer briefing llega a los tres días.</li>
      </ol>
      <div class="contacto"><b>ricardoruiz.co/candidato-360.html</b><br>hola@ricardoruiz.co · WhatsApp +57 324 303 6767<br><small>Agende 30 minutos: calendar.app.google/PGDbTQfmNmtgPud8A</small></div>
    </div>
  </div>
  {PIE}
</div>

</body></html>"""

if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    HTML(string=HTML_DOC, base_url=ROOT).write_pdf(OUT)
    print("→", OUT, f"{os.path.getsize(OUT) / 1024:.0f} KB")
