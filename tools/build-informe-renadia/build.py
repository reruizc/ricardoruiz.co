#!/usr/bin/env python3
"""
RENADIA · Informe de resultados — Convocatoria "Mundial 2026"
Piloto del microsite gamificado (RENADIA-unete-mundial-v3.html), 6-9 jul 2026.

Identidad visual: la MISMA del microsite (no ricardoruiz.co) — teal/magenta/
amarillo, tipografía de sistema (Segoe UI). Entregable blanco (white-label)
para el equipo RENADIA/DNP, igual que el resto de piezas en Bases de datos/DNP/.

Cifras fuente: Bases de datos/DNP/respuestas-export/RENADIA_respuestas_SIN_VANESSA.xlsx
(hoja Resumen + las 3 hojas de retos), sincronizado 2026-07-10 desde
s3://elecciones-2026/renadia-collect/respuestas/. Excluye a Vanessa (pruebas
del equipo) y POSTs vacíos de bots.

Salida: Bases de datos/DNP/RENADIA-Informe-Resultados-Mundial2026.pdf
"""
import os
import datetime
from weasyprint import HTML

ROOT = "/Users/ricardoruiz/ricardoruiz.co"
OUT = os.path.join(ROOT, "Bases de datos", "DNP", "RENADIA-Informe-Resultados-Mundial2026.pdf")

_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
_hoy = datetime.date.today()
FECHA = f"{_hoy.day} de {_MESES[_hoy.month - 1]} de {_hoy.year}"

# ---------------------------------------------------------------------------
# Datos (de RENADIA_respuestas_SIN_VANESSA.xlsx, hoja Resumen + hojas de retos)
# ---------------------------------------------------------------------------
PARTICIPANTES = 33
PARTIDAS = 73
RETO1_N, RETO2_N, RETO3_N = 36, 18, 19
VENTANA = "del 6 al 9 de julio de 2026 (56 horas · 2,3 días corridos)"

POR_DIA = [("6 jul", 6, 8), ("7 jul", 43, 59), ("8 jul", 22, 30), ("9 jul", 2, 3)]

SEGMENTOS = [
    ("Entidad nacional", 14, 39), ("Sector privado", 12, 33),
    ("Entidad territorial", 5, 14), ("Sector académico", 5, 14),
]

POSICIONES = [
    ("DAT · exploración de datos", 17, 47), ("IA · automatizar y predecir", 10, 28),
    ("COC · cocreación y comunidad", 5, 14), ("GOB · gobernanza y ética", 4, 11),
]

QUE_MUEVE = [
    ("Tomar mejores decisiones con evidencia", 13, 36),
    ("Aprender y crecer en datos e IA", 11, 31),
    ("Llevar la IA a resultados concretos", 8, 22),
    ("Conectar y construir con otros", 4, 11),
]

QUE_FRENA = [
    ("Faltan capacidades o talento", 12, 33),
    ("Falta con quién intercambiar experiencias", 10, 28),
    ("Falta claridad para usar IA con ética", 7, 19),
    ("Faltan datos de calidad", 7, 19),
]

COMO_SUMAR = [
    ("En mesas temáticas de trabajo", 22, 61),
    ("En webinars y charlas", 11, 31),
    ("En diálogos uno a uno", 3, 8),
]

SECTORES_R2 = [
    "Financiero (×2)", "Educación (×3, con variantes de escritura)", "Salud (×2)",
    "Gobernanza de IA", "Sector gastronómico", "Desarrollo económico", "Ambiente",
    "TIC", "Seguridad", "Gerencia de proyectos", "Seguros", "Minero-energético",
]

PENALTIS_Q = [
    ("P1", 14, 19, 74), ("P2", 17, 19, 89), ("P3", 15, 19, 79),
    ("P4", 14, 19, 74), ("P5", 16, 19, 84),
]
PENALTIS_PROM = "4,0 / 5 (80%)"

QUOTES_R2 = [
    ("Financiero", "“Las entidades tienen muchos datos al interior de forma dispersa "
     "en distintas bases de datos y poco personal para explotarlos.”"),
    ("TIC", "“Unas plantillas que faciliten la estructuración de una política del "
     "dato institucional […] apuntando a marcos por excelencia aceptados por la "
     "industria para el Gobierno y Gobernanza de datos.”"),
    ("Minero-energético", "“Centralización de datos e interoperabilidad” — "
     "citada como el desafío más urgente del sector."),
    ("Entidad territorial", "“El trabajo se acaba cuando cambian de contratistas y "
     "se pierde el conocimiento, falta de empalme y guardar información.”"),
]

EMBUDO = [
    ("Completaron los 3 retos (circuito completo)", 16, 48),
    ("Completaron 2 retos", 3, 9),
    ("Jugaron 1 reto", 14, 42),
]

PENALTIS_MITOS = [
    ("“La IA reemplazará a los funcionarios públicos” (mito)", 14, 74),
    ("“Para empezar a usar analítica hay que invertir millones” (mito)", 17, 89),
    ("“Compartir aprendizajes acelera la madurez” (realidad)", 15, 79),
    ("“La gobernanza de datos es solo un asunto de TI” (mito)", 14, 74),
    ("“Unirse a RENADIA tiene costos y obligaciones” (mito)", 16, 84),
]

ANEXO = [
    ("6 jul", "coquito", "Entidad nacional", "—", "1 y 3"),
    ("6 jul", "ALETHEOX", "Sector privado", "Gobernanza de IA", "1, 2 y 3"),
    ("7 jul", "Jesus Zetien", "Sector privado", "Sector gastronómico", "1, 2 y 3"),
    ("7 jul", "Victor Hugo Vidal Molina", "Entidad territorial", "Desarrollo Económico", "1, 2 y 3"),
    ("7 jul", "Juan_Useche", "Entidad nacional", "—", "1"),
    ("7 jul", "siiuary", "Entidad territorial", "Educación", "1, 2 y 3"),
    ("7 jul", "Karen", "Entidad nacional", "—", "1"),
    ("7 jul", "NORMA ALVAREZ", "Sector académico", "Educación", "1, 2 y 3"),
    ("7 jul", "Omar Villarreal Osorio", "Entidad nacional", "Ambiente", "1, 2 y 3"),
    ("7 jul", "Diafon", "Sector privado", "Financiero", "1, 2 y 3"),
    ("7 jul", "JulianDDM", "Entidad territorial", "—", "1"),
    ("7 jul", "MIGUEL CRUZ", "Entidad nacional", "TIC", "1, 2 y 3"),
    ("7 jul", "Diana", "Entidad territorial", "—", "1, 2 y 3"),
    ("7 jul", "Jacquelie", "Sector privado", "—", "1"),
    ("7 jul", "(sin nombre)", "—", "Seguridad", "2"),
    ("7 jul", "Brandon Arboleda Jaramillo", "Sector académico", "Educación", "1 y 2"),
    ("7 jul", "CEO Juan Carlos", "Sector privado", "Gerencia de Proyectos", "1, 2 y 3"),
    ("7 jul", "Emilio9306", "Sector académico", "Educación", "1, 2 y 3"),
    ("7 jul", "Johan", "Sector privado", "—", "1"),
    ("7 jul", "Juan", "Sector privado", "—", "1"),
    ("7 jul", "Esteban Urrutia", "Entidad nacional", "—", "1"),
    ("8 jul", "Willinton", "Entidad nacional", "—", "1"),
    ("8 jul", "Claudiaj", "Sector privado", "Financiero", "1, 2 y 3"),
    ("8 jul", "Alvaro23", "Sector privado", "Seguros", "1, 2 y 3"),
    ("8 jul", "Laura M", "Entidad territorial", "—", "1"),
    ("8 jul", "Lorena", "Entidad nacional", "—", "1 y 3"),
    ("8 jul", "werewr", "Entidad nacional", "Minero-energético", "1, 2 y 3"),
    ("8 jul", "Alejandro Gutiérrez", "Sector académico", "Salud", "1, 2 y 3"),
    ("8 jul", "Carlos", "Entidad nacional", "—", "1"),
    ("8 jul", "Santiago", "Entidad nacional", "Información de salud", "1, 2 y 3"),
    ("8 jul", "Gustavo Cadena", "Entidad nacional", "—", "1"),
    ("9 jul", "Diana Paola Ahumada Riaño", "Sector académico", "—", "1"),
    ("9 jul", "Echo40", "Sector privado", "—", "1"),
]

# ---------------------------------------------------------------------------
CSS = """
@page { size: A4; margin: 0; }
@page cover { margin: 0; }
* { margin:0; padding:0; box-sizing:border-box; }
body {
  font-family: "Segoe UI", system-ui, -apple-system, Arial, sans-serif;
  color: #12182A; font-size: 10.6px; line-height: 1.5;
}
:root{}
.page { width:210mm; min-height:297mm; padding: 16mm 17mm 15mm; position:relative;
  page-break-after: always; }
.page:last-child{ page-break-after: auto; }

/* ---- portada ---- */
.cover { width:210mm; height:297mm; page-break-after: always; position:relative;
  background: radial-gradient(1000px 560px at 82% -8%, rgba(0,195,193,.32), transparent 60%),
              radial-gradient(820px 480px at 6% 108%, rgba(254,24,123,.24), transparent 60%),
              linear-gradient(160deg,#0c3a39,#0a2a2a 72%);
  color:#fff; padding: 26mm 20mm; }
.cover .kick{ display:inline-flex; align-items:center; gap:8px; background:rgba(255,202,0,.14);
  border:1px solid rgba(255,202,0,.42); color:#FFCA00; font-weight:800; font-size:10.5px;
  letter-spacing:2.4px; text-transform:uppercase; padding:7px 14px; border-radius:50px; }
.cover h1{ font-size:34px; line-height:1.12; font-weight:800; margin:20mm 0 8mm; max-width:150mm; }
.cover h1 b{ color:#00C3C1; } .cover h1 i{ font-style:normal; color:#FFCA00; }
.cover .sub{ font-size:14px; color:#d7e6e6; max-width:135mm; line-height:1.55; }
.cover .meta{ position:absolute; left:20mm; right:20mm; bottom:20mm;
  display:flex; justify-content:space-between; align-items:flex-end;
  border-top:1px solid rgba(255,255,255,.22); padding-top:6mm; }
.cover .meta .l{ font-size:10.5px; color:#9fc0c0; line-height:1.6; }
.cover .meta .l b{ color:#fff; display:block; font-size:12px; letter-spacing:.5px; }
.cover .badge{ background:rgba(0,195,193,.16); border:1px solid rgba(0,195,193,.4);
  border-radius:12px; padding:9px 13px; font-size:9.5px; color:#cfeeee; max-width:60mm; }

/* ---- headers de sección ---- */
.eyebrow{ font-size:9.5px; font-weight:800; letter-spacing:2.4px; text-transform:uppercase;
  color:#008C8A; }
h2.sec{ font-size:19px; font-weight:800; color:#12182A; margin:2mm 0 4mm; letter-spacing:-.2px; }
h2.sec b{ color:#FE187B; }
p.lede{ font-size:11px; color:#39415A; line-height:1.6; max-width:170mm; margin-bottom:6mm; }
h3.sub{ font-size:12.5px; font-weight:800; color:#005f5e; margin:6mm 0 2.5mm; }
p { color:#39415A; margin-bottom:3mm; }
.pagenum{ position:absolute; bottom:9mm; right:17mm; font-size:8.5px; color:#AEB6C8; }
.foot-brand{ position:absolute; bottom:9mm; left:17mm; font-size:8.5px; color:#AEB6C8;
  letter-spacing:1px; text-transform:uppercase; font-weight:700; }

/* ---- stat tiles ---- */
.tiles{ display:flex; gap:5mm; margin: 4mm 0 7mm; }
.tile{ flex:1; background:linear-gradient(155deg,#008C8A,#005f5e); color:#fff;
  border-radius:6mm; padding:6mm 5mm; }
.tile .n{ font-size:26px; font-weight:800; line-height:1; }
.tile .l{ font-size:9px; margin-top:2mm; color:#cdeeee; line-height:1.4; }
.tile.mag{ background:linear-gradient(155deg,#FE187B,#9c0f4c); }
.tile.ink{ background:linear-gradient(155deg,#39415A,#12182A); }

/* ---- barras ---- */
.bars{ margin: 2mm 0 6mm; }
.bar-row{ display:flex; align-items:center; gap:3mm; margin-bottom:2.6mm; }
.bar-row .lbl{ width:56mm; font-size:9.6px; color:#12182A; font-weight:600; flex:none; }
.bar-row .track{ flex:1; height:5.6mm; background:#E9EDF6; border-radius:3mm; overflow:hidden; }
.bar-row .fill{ height:100%; border-radius:3mm; background:linear-gradient(90deg,#00C3C1,#008C8A); }
.bar-row .fill.mag{ background:linear-gradient(90deg,#FE187B,#9c0f4c); }
.bar-row .fill.yel{ background:linear-gradient(90deg,#FFCA00,#c99900); }
.bar-row .fill.ink{ background:linear-gradient(90deg,#6B748A,#39415A); }
.bar-row .val{ width:20mm; text-align:right; font-size:9.6px; font-weight:800; color:#005f5e;
  flex:none; }

/* ---- tabla de dias ---- */
.days{ display:flex; gap:3mm; margin: 3mm 0 6mm; }
.day{ flex:1; background:#F4F6FB; border:1px solid #E2E7F1; border-radius:4mm; padding:4mm 3mm;
  text-align:center; }
.day .d{ font-size:9px; font-weight:800; text-transform:uppercase; letter-spacing:1px;
  color:#6B748A; }
.day .n{ font-size:20px; font-weight:800; color:#008C8A; margin:1.5mm 0; }
.day .p{ font-size:8.5px; color:#AEB6C8; }
.day.peak{ background:linear-gradient(155deg,#fff7e0,#fff); border-color:#FFCA00; }
.day.peak .n{ color:#c99900; }

/* ---- lista chip ---- */
.chips{ display:flex; flex-wrap:wrap; gap:2.4mm; margin-bottom:5mm; }
.chip{ background:#F4F6FB; border:1px solid #E2E7F1; border-radius:50px; padding:2.2mm 4mm;
  font-size:9px; color:#39415A; font-weight:600; }

/* ---- quotes ---- */
.quote{ border-left:3px solid #00C3C1; background:#F4F6FB; border-radius:0 3mm 3mm 0;
  padding:3.6mm 5mm; margin-bottom:3mm; }
.quote .who{ font-size:8.6px; font-weight:800; letter-spacing:1px; text-transform:uppercase;
  color:#008C8A; margin-bottom:1.4mm; }
.quote .txt{ font-size:10px; color:#12182A; font-style:normal; letter-spacing:.05px; line-height:1.5; }

/* ---- callout ---- */
.callout{ background:linear-gradient(135deg,#fff,#F4F6FB); border:1.5px solid #00C3C1;
  border-radius:5mm; padding:5mm 6mm; margin: 4mm 0 6mm; }
.callout b{ color:#005f5e; }
.callout.mag{ border-color:#FE187B; }
.callout.mag b{ color:#FE187B; }

/* ---- lista de check ---- */
ul.check{ list-style:none; margin: 2mm 0 5mm; }
ul.check li{ position:relative; padding-left:5.5mm; margin-bottom:2.6mm; font-size:10px;
  color:#39415A; line-height:1.5; }
ul.check li:before{ content:"\\25CF"; color:#00C3C1; position:absolute; left:0; font-size:7px;
  top:2px; }
ul.check.mag li:before{ color:#FE187B; }

ol.steps{ counter-reset: step; list-style:none; margin: 2mm 0 5mm; }
ol.steps li{ position:relative; padding-left:9mm; margin-bottom:4mm; font-size:10px;
  color:#39415A; line-height:1.5; }
ol.steps li b{ color:#12182A; }
ol.steps li:before{ counter-increment: step; content: counter(step);
  position:absolute; left:0; top:-1px; width:6.4mm; height:6.4mm; border-radius:50%;
  background:linear-gradient(155deg,#00C3C1,#008C8A); color:#fff; font-weight:800;
  font-size:10px; display:flex; align-items:center; justify-content:center; }

table.tbl{ width:100%; border-collapse:collapse; margin-bottom:6mm; font-size:9.6px; }
table.tbl th{ background:#12182A; color:#fff; text-align:left; padding:3mm 3.4mm;
  font-size:8.8px; letter-spacing:.5px; text-transform:uppercase; }
table.tbl td{ padding:2.8mm 3.4mm; border-bottom:1px solid #E2E7F1; color:#39415A; }
table.tbl tr:nth-child(even) td{ background:#F9FAFC; }
table.tbl.anexo{ font-size:8.4px; }
table.tbl.anexo th{ background:#005f5e; padding:1.9mm 2.6mm; font-size:8px; }
table.tbl.anexo td{ padding:1.35mm 2.6mm; }
"""

def tiles(items):
    out = '<div class="tiles">'
    for n, l, cls in items:
        out += f'<div class="tile {cls}"><div class="n">{n}</div><div class="l">{l}</div></div>'
    out += "</div>"
    return out


def bars(rows, cls="teal", maxv=None):
    maxv = maxv or max(v for _, v, _ in rows)
    out = '<div class="bars">'
    fillcls = {"teal": "", "mag": "mag", "yel": "yel", "ink": "ink"}[cls]
    for lbl, v, pct in rows:
        w = round(v / maxv * 100)
        out += (f'<div class="bar-row"><div class="lbl">{lbl}</div>'
                 f'<div class="track"><div class="fill {fillcls}" style="width:{w}%"></div></div>'
                 f'<div class="val">{v} · {pct}%</div></div>')
    out += "</div>"
    return out


def days_block():
    out = '<div class="days">'
    for d, n, pct in POR_DIA:
        peak = " peak" if n == max(x[1] for x in POR_DIA) else ""
        out += (f'<div class="day{peak}"><div class="d">{d}</div><div class="n">{n}</div>'
                 f'<div class="p">{pct}% de las partidas</div></div>')
    out += "</div>"
    return out


def foot(n, label):
    return (f'<div class="foot-brand">RENADIA · Informe de resultados</div>'
            f'<div class="pagenum">{n} / {label}</div>')


PAGES_TOTAL = 11


def tbl(head, rows, accent="#005f5e"):
    out = f'<table class="tbl"><tr><th>{head[0]}</th><th style="text-align:right">{head[1]}</th><th style="text-align:right">{head[2]}</th></tr>'
    for label, n, pct in rows:
        out += (f'<tr><td>{label}</td>'
                f'<td style="text-align:right;font-weight:800;color:{accent}">{n}</td>'
                f'<td style="text-align:right;font-weight:800;color:{accent}">{pct}%</td></tr>')
    out += "</table>"
    return out


def anexo_tbl(rows):
    out = ('<table class="tbl anexo"><tr><th>Fecha</th><th>Participante</th>'
           '<th>Segmento (Reto 1)</th><th>Sector (Reto 2)</th><th>Retos</th></tr>')
    for fecha, nombre, grupo, sector, retos in rows:
        out += (f'<tr><td>{fecha}</td><td style="font-weight:700;color:#12182A">{nombre}</td>'
                f'<td>{grupo}</td><td>{sector}</td><td>{retos}</td></tr>')
    out += "</table>"
    return out

html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<title>RENADIA · Informe de resultados — Mundial 2026</title>
<style>{CSS}</style></head><body>

<div class="cover">
  <div class="kick">Informe de resultados</div>
  <h1>Colombia jugó el <b>Mundial de los datos</b>.<br>Esto fue lo que <i>dejó</i> el primer partido.</h1>
  <p class="sub">Resultados y lectura de impacto del piloto de convocatoria gamificada
  de RENADIA — Red Nacional de Analítica de Datos e Inteligencia Artificial —
  desplegado del 6 al 9 de julio de 2026.</p>
  <div class="badge">Documento interno de trabajo. Preparado para el equipo RENADIA ·
  Unidad de Ciencia de Datos · Dirección de Desarrollo Digital (DNP).</div>
  <div class="meta">
    <div class="l"><b>Ventana analizada</b>6 – 9 de julio de 2026</div>
    <div class="l"><b>33 participantes · 73 partidas</b>renadia-mundial.pages.dev</div>
    <div class="l"><b>Preparado</b>{FECHA}</div>
  </div>
</div>

<div class="page">
  <div class="eyebrow">01 · Resumen ejecutivo</div>
  <h2 class="sec">En 56 horas, <b>33 personas</b> jugaron su forma de entrar a RENADIA.</h2>
  <p class="lede">Entre el 6 y el 9 de julio de 2026 estuvo activo el microsite de
  convocatoria "Mundial 2026" — una forma alternativa, lúdica, de presentar RENADIA
  y explicar en qué consiste vincularse a la red, sin depender de un webinar o un
  boletín. El resultado: 73 partidas jugadas por 33 personas distintas, con
  participación de entidades nacionales, territoriales, sector privado y academia,
  y un corpus de respuestas abiertas que funciona como diagnóstico temprano de
  madurez analítica en 12+ sectores.</p>

  {tiles([
      (PARTICIPANTES, "personas distintas jugaron al menos un reto", ""),
      (PARTIDAS, "partidas completadas en total", "mag"),
      ("56h", "de ventana activa (6–9 jul, 2,3 días)", "ink"),
      ("12+", "sectores distintos autodeclarados", ""),
  ])}

  <h3 class="sub">Lo más importante para RENADIA</h3>
  <div class="callout">
    <p style="margin:0"><b>El reto 1 midió, sin decirlo, la pregunta que RENADIA se
    está haciendo en este mismo momento.</b> A la pregunta "¿cómo prefieres sumar al
    equipo?", el 61% de las 36 respuestas eligió <b>mesas temáticas de trabajo</b> por
    encima de webinars (31%) y diálogos uno a uno (8%). Esto corre en paralelo — misma
    semana — al piloto de Mesas Temáticas que arrancó el 6 de julio: el microsite
    entregó, sin proponérselo, una primera señal cuantitativa a favor del giro
    estratégico hacia formatos interactivos descrito en la sección 3.2 del documento
    base de RENADIA.</p>
  </div>

  <h3 class="sub">Cómo leer este informe</h3>
  <p>Las secciones 2 y 3 explican qué se construyó y cómo funcionó el embudo de
  participación. Las secciones 4 a 6 presentan los resultados cuantitativos y
  cualitativos por reto. La sección 7 conecta esos resultados con las líneas de
  trabajo y oportunidades de mejora ya identificadas por el equipo RENADIA. La
  sección 8 es honesta sobre los límites de esta primera ventana y qué se
  recomienda medir en la siguiente.</p>
  {foot(1, PAGES_TOTAL)}
</div>

<div class="page">
  <div class="eyebrow">02 · Qué se construyó</div>
  <h2 class="sec">Un <b>microsite</b> con la mecánica de un álbum de figuritas del Mundial.</h2>
  <p class="lede">En lugar de un formulario de inscripción tradicional, la
  convocatoria se armó como una experiencia jugable, mobile-first, con la estética
  de un Mundial de fútbol — la misma metáfora que ya usaba el "Tablero fest" de
  RENADIA en formato físico, ahora en digital.</p>

  <h3 class="sub">La mecánica: 3 retos + álbum de 5 láminas</h3>
  <ol class="steps">
    <li><b>Reto 1 · "Tu carta de jugador"</b> — 5 preguntas cortas arman una carta de
    FIFA con OVR y posición (DAT / IA / GOB / COC), reflejo del perfil de la persona
    frente a datos e IA. Es la puerta de entrada: la más jugada de las tres.</li>
    <li><b>Reto 2 · "Tu sector frente a los datos"</b> — 4 preguntas abiertas de
    diagnóstico: desafío más urgente, qué datos faltan, qué datos ya existen, qué
    iniciativas de IA conoce la persona en su sector. Es el reto de mayor
    compromiso — texto libre, no opción múltiple.</li>
    <li><b>Reto 3 · "Tanda de penaltis"</b> — 5 afirmaciones de mito o realidad sobre
    datos e IA; cada acierto "ataja" un penalti. Funciona como pieza educativa.</li>
    <li><b>Álbum RENADIA</b> — completar los 3 retos, más registrarse y compartir,
    llena las 5 láminas del álbum. El CTA final no es un "gracias" — es un enlace
    directo al <b>formulario oficial de RENADIA</b> (Microsoft Forms), la vinculación
    real. El juego es el enganche; el formulario sigue siendo la puerta formal.</li>
  </ol>

  <h3 class="sub">Bajo el capó</h3>
  <ul class="check">
    <li>Desplegado como sitio estático independiente en <b>renadia-mundial.pages.dev</b>
    — pensado para ser embebible dentro de la web institucional del DNP sin
    depender de su infraestructura.</li>
    <li>Cada respuesta se envía por <b>sendBeacon</b> a un backend serverless propio
    (AWS Lambda + API Gateway) y queda guardada en S3, un objeto por partida, con
    sesión, origen y timestamp — sin necesidad de que la persona complete nada más
    que el juego mismo.</li>
    <li>Identidad visual propia (teal / magenta / amarillo), <b>sin marca de
    terceros</b> — el microsite se ve y se siente 100% RENADIA.</li>
  </ul>
  {foot(2, PAGES_TOTAL)}
</div>

<div class="page">
  <div class="eyebrow">03 · Participación</div>
  <h2 class="sec">73 partidas, con un pico claro el <b>7 de julio</b>.</h2>
  <p class="lede">La distribución por día muestra una convocatoria puntual — no una
  campaña sostenida en el tiempo. El 59% de las partidas ocurrió en un solo día,
  lo que sugiere que el enlace se compartió una vez (correo, webinar o publicación)
  en lugar de mantenerse activo con recordatorios escalonados.</p>
  {days_block()}

  <h3 class="sub">Partidas por reto</h3>
  {bars([("Reto 1 · Carta de jugador", RETO1_N, 49),
         ("Reto 2 · Diagnóstico sectorial", RETO2_N, 25),
         ("Reto 3 · Penaltis (mito o realidad)", RETO3_N, 26)], cls="teal", maxv=RETO1_N)}
  <p style="font-size:9.5px;color:#6B748A;margin-top:-3mm">El Reto 1 concentra casi
  la mitad de las partidas — es, como estaba pensado, la puerta de entrada más
  liviana. El Reto 2 (texto libre) retuvo a la mitad de quienes jugaron el Reto 1:
  buena señal de compromiso para un formato que exige más esfuerzo.</p>

  <h3 class="sub">Segmento declarado (Reto 1, n=36)</h3>
  {bars([(l, v, p) for l, v, p in SEGMENTOS], cls="mag")}
  <p style="font-size:9.5px;color:#6B748A;margin-top:-3mm">Paridad casi perfecta
  entre <b>entidad nacional (39%)</b> y <b>sector privado (33%)</b> — la convocatoria
  no solo llegó al público natural de RENADIA (entidades públicas), sino que
  atrajo en volumen comparable a empresas privadas, con presencia adicional de
  territorial y academia.</p>
  {foot(3, PAGES_TOTAL)}
</div>

<div class="page">
  <div class="eyebrow">03 · Participación (continuación)</div>
  <h2 class="sec">Casi la mitad completó el <b>circuito entero</b>.</h2>
  <p class="lede">Las 73 partidas corresponden a 33 sesiones de juego distintas —
  una por persona. Seguir la sesión permite ver el embudo real: cuánta gente que
  entró jugó todo el circuito.</p>
  {bars([(l, v, p) for l, v, p in EMBUDO], cls="teal")}
  <p style="font-size:9.5px;color:#6B748A;margin-top:-3mm">De las 33 personas que
  entraron a jugar, <b>16 (48%) completaron los tres retos</b> — un circuito de unos
  10 minutos que incluye un reto de texto libre. Para una experiencia voluntaria,
  sin premio material y sin registro obligatorio, esa retención es alta: la mecánica
  de álbum ("te faltan N láminas") parece estar haciendo su trabajo de arrastre
  entre retos.</p>

  <h3 class="sub">Cuándo jugaron</h3>
  <p>El <b>77% de las partidas ocurrió en horario laboral</b> (8:00–17:00, hora de
  Colombia), con el pico en la franja de 12:00 a 14:00 (42% del total) —
  consistente con una difusión por canales institucionales que la gente atendió
  durante la jornada. Hay además una cola nocturna (22:00–23:00, 16%) que sugiere
  que varias personas retomaron el enlace por su cuenta al final del día.</p>
  {foot(4, PAGES_TOTAL)}
</div>

<div class="page">
  <div class="eyebrow">04 · Perfil y motivaciones (Reto 1)</div>
  <h2 class="sec">La mayoría se ve <b>explorando datos</b>, no haciendo gobernanza.</h2>
  <p class="lede">La posición de la carta de jugador (DAT / IA / GOB / COC) resume,
  con una sola palabra, cómo cada persona se percibe frente a los datos y la IA.</p>
  {bars([(l, v, p) for l, v, p in POSICIONES], cls="teal")}
  <p style="font-size:9.5px;color:#6B748A;margin-top:-3mm">Casi la mitad (47%) se
  identifica como perfil <b>DAT</b> — "los exploro y visualizo para encontrar
  historias" — por encima de IA (28%), cocreación (14%) y gobernanza (11%). Para
  RENADIA esto es una pista de tono: el mensaje que mejor conecta hoy es el del
  dato práctico y exploratorio, no el marco normativo o de gobernanza (que sigue
  siendo relevante, pero conecta menos en primer contacto).</p>

  <h3 class="sub">¿Qué te mueve a jugar este partido?</h3>
  {bars([(l, v, p) for l, v, p in QUE_MUEVE], cls="mag")}

  <h3 class="sub">¿Qué te frena hoy?</h3>
  {bars([(l, v, p) for l, v, p in QUE_FRENA], cls="yel")}
  <p style="font-size:9.5px;color:#6B748A;margin-top:-3mm">El freno más citado no es
  la tecnología ni los datos — es <b>talento y capacidades (33%)</b>, seguido de
  cerca por la falta de pares con quién intercambiar experiencias (28%). Ambos son
  exactamente lo que una red de pares como RENADIA está en posición de resolver.</p>

  <h3 class="sub">¿Cómo prefieres sumar al equipo?</h3>
  {bars([(l, v, p) for l, v, p in COMO_SUMAR], cls="ink")}
  <div class="callout mag">
    <p style="margin:0"><b>Mesas temáticas de trabajo (61%)</b> gana por más del
    doble sobre webinars y charlas (31%), y por siete veces sobre diálogos uno a
    uno (8%). Y la preferencia es <b>transversal a los cuatro segmentos</b>:
    primera opción en privado (8/12), nacional (7/14) y académico (5/5, unánime);
    empatada en territorial (2/5). Es la validación cuantitativa más directa que
    este piloto produjo para el giro estratégico hacia formatos interactivos.</p>
  </div>
  {foot(5, PAGES_TOTAL)}
</div>

<div class="page">
  <div class="eyebrow">05 · Diagnóstico sectorial (Reto 2)</div>
  <h2 class="sec">18 diagnósticos de texto libre, en <b>12+ sectores</b> distintos.</h2>
  <p class="lede">El Reto 2 no ofrece opciones — pide texto libre sobre el desafío
  más urgente del sector, qué datos faltan, qué datos ya existen y qué iniciativas
  de IA conoce la persona. El resultado es un corpus cualitativo real, sin filtrar
  por lo que RENADIA cree que la gente va a decir.</p>

  <h3 class="sub">Sectores autodeclarados</h3>
  <div class="chips">{"".join(f'<div class="chip">{s}</div>' for s in SECTORES_R2)}</div>
  <p style="font-size:9.5px;color:#6B748A;margin-top:-3mm">Más de la mitad de estos
  sectores (salud, TIC, seguridad, seguros, gerencia de proyectos, gastronómico) no
  corresponden a ninguno de los dos sectores cubiertos hasta ahora por el ciclo de
  webinars sectoriales (Comercio/Industria/Turismo y Minas y Energía) — una señal de
  demanda para próximos sectores en cola.</p>

  <h3 class="sub">Temas que se repiten aunque nadie los coordinó</h3>
  <ul class="check">
    <li><b>Interoperabilidad y centralización de datos.</b> Aparece con distintas
    palabras en TIC, minero-energético, seguridad ("datos unificados") y ambiente
    ("interoperabilidad") — el desafío transversal más mencionado.</li>
    <li><b>Datos dispersos y de mala calidad.</b> Financiero, salud y educación
    coinciden en que el problema no es la falta de datos sino su dispersión en
    sistemas que no se hablan y la falta de gente para explotarlos.</li>
    <li><b>Talento y capacitación.</b> Coherente con el freno más citado del Reto 1
    ("faltan capacidades o talento", 33%): varios diagnósticos piden formación
    antes que tecnología.</li>
    <li><b>Pérdida de conocimiento institucional.</b> Una respuesta territorial lo
    dice sin rodeos (última cita): la rotación de contratistas borra la memoria de
    las entidades — el tipo de práctica que una red de pares puede ayudar a
    sistematizar.</li>
  </ul>

  <h3 class="sub">Algunas voces textuales</h3>
  {"".join(f'<div class="quote"><div class="who">{who}</div><div class="txt">{txt}</div></div>' for who, txt in QUOTES_R2)}
  {foot(6, PAGES_TOTAL)}
</div>

<div class="page">
  <div class="eyebrow">05 · Diagnóstico sectorial (continuación)</div>
  <h2 class="sec">Penaltis: qué mito costó más <b>atajar</b>.</h2>
  <p class="lede">Acierto promedio del Reto 3: <b>{PENALTIS_PROM}</b>. El contenido
  educativo del juego aterrizó bien — la mayoría "atajó" 4 o 5 de los 5 mitos. El
  detalle por afirmación deja dos lecturas útiles.</p>
  {tbl(("Afirmación del penalti", "Atajaron", "%"), PENALTIS_MITOS)}
  <ul class="check">
    <li><b>Los mitos más persistentes (74% de acierto, 1 de cada 4 falló)</b> son
    "la IA reemplazará a los funcionarios públicos" y "la gobernanza de datos es
    solo un asunto de TI". Son los dos frentes donde más pedagogía falta —
    candidatos naturales a contenido de próximos webinars y boletines.</li>
    <li><b>El mito de los costos de membresía fue bien atajado (84%).</b> El mensaje
    central de la convocatoria — vinculación voluntaria, sin costos ni obligaciones
    legales — está llegando con claridad.</li>
  </ul>
  {foot(7, PAGES_TOTAL)}
</div>

<div class="page">
  <div class="eyebrow">06 · Lectura de impacto</div>
  <h2 class="sec">Lo que este piloto le <b>aporta</b> a RENADIA más allá del conteo.</h2>
  <ul class="check">
    <li><b>Validación temprana de la apuesta a Mesas Temáticas.</b> El 61% de
    preferencia por este formato (sección 4) llega justo en la semana en que RENADIA
    empezó a pilotearlo (fase 1, desde el 6 de julio) — es una señal externa e
    independiente de que el giro estratégico va en la dirección correcta.</li>
    <li><b>Insumo directo para el "instrumento de diagnóstico periódico"</b> que el
    documento base de RENADIA identifica como oportunidad de mejora (línea 3): las
    18 respuestas del Reto 2 son, en la práctica, un primer prototipo — barato y
    rápido de levantar — de ese instrumento, con datos reales de 12+ sectores.</li>
    <li><b>Demanda sectorial para expandir el ciclo de webinars.</b> Sectores como
    salud, TIC, seguridad y financiero aparecieron por iniciativa propia de los
    participantes, sin que RENADIA los convocara — son candidatos naturales para las
    próximas rondas de webinars sectoriales.</li>
    <li><b>Un canal de bajo costo y bajo esfuerzo de mantenimiento.</b> 33 personas
    en 56 horas, sin pauta paga, sin evento presencial y con un solo envío de enlace
    — comparado con el costo operativo de una campaña de correos entidad por
    entidad, es un canal barato de calentar interés antes del formulario oficial.</li>
    <li><b>Paridad público-privado inesperada.</b> El 33% de participación de sector
    privado (sección 3) sugiere que el microsite, al no requerir credenciales
    institucionales ni un correo de gobierno, atrajo a un público que un boletín
    dirigido a entidades no habría alcanzado igual de fácil — relevante para la
    ambición de RENADIA de operar como "red de redes" más allá del sector público.</li>
    <li><b>El formato retiene: 48% completó el circuito entero.</b> 16 de 33
    personas jugaron los tres retos, incluido el de texto libre — el más exigente.
    La mecánica de álbum sostiene el recorrido completo mejor de lo que suele
    sostener un formulario largo tradicional.</li>
    <li><b>33 contactos identificables para los Diálogos Bilaterales.</b> La mayoría
    dejó nombre (varios, nombre completo real) y segmento o sector — el anexo
    consolida la lista. Es una lista semilla concreta para el relacionamiento
    personalizado que RENADIA está pilotando, empezando por las 16 personas que
    completaron todo el circuito (las de mayor engagement demostrado).</li>
  </ul>
  {foot(8, PAGES_TOTAL)}
</div>

<div class="page">
  <div class="eyebrow">07 · Límites del piloto</div>
  <h2 class="sec">Qué <b>no</b> dice todavía este número, con honestidad.</h2>
  <ul class="check mag">
    <li><b>No hay dato de alcance ni de visitas.</b> El backend solo registra
    partidas completadas, no vistas de página ni abandonos — no se puede calcular
    una tasa de conversión real (cuántas personas vieron el microsite y no
    jugaron).</li>
    <li><b>Ventana corta y concentrada.</b> 56 horas con un solo pico de difusión
    (59% en un día) no permite separar "el formato funciona" de "el momento de
    difusión funcionó" — habría que repetirlo con difusión escalonada para
    aislar el efecto del formato.</li>
    <li><b>No se rastrea conversión a vinculación formal.</b> El juego entrega al
    formulario oficial de Microsoft Forms, pero ese formulario vive fuera de este
    sistema — no se puede confirmar hoy cuántas de las 33 personas completaron
    también la inscripción real a RENADIA.</li>
    <li><b>Muestra autoseleccionada y pequeña.</b> 33 personas es útil como señal
    direccional (por ejemplo, la preferencia por mesas temáticas), pero no alcanza
    para tratarse como representativo de todo el universo de entidades y personas
    que RENADIA busca vincular.</li>
    <li><b>El microsite aún no estaba embebido en la web institucional del DNP</b>
    — el 100% del tráfico llegó por el dominio independiente
    (renadia-mundial.pages.dev); integrarlo al sitio institucional es una fuente de
    alcance todavía sin explotar.</li>
  </ul>
  {foot(9, PAGES_TOTAL)}
</div>

<div class="page">
  <div class="eyebrow">08 · Recomendaciones</div>
  <h2 class="sec">Qué haría más fuerte la <b>próxima ronda</b>.</h2>
  <ol class="steps">
    <li><b>Difusión escalonada, no de un solo golpe.</b> Repartir el enlace en 2 o 3
    momentos (ej. tras un webinar, en un boletín, en redes) en vez de un único
    envío, para sostener el flujo en lugar de un pico de un día.</li>
    <li><b>Instrumentar vistas de página, no solo partidas completadas.</b> Agregar
    un evento simple de "entró al microsite" permite calcular una tasa de
    conversión real de visita → juego completado.</li>
    <li><b>Cerrar el ciclo con el formulario oficial.</b> Cruzar (por correo o nombre,
    con consentimiento) quién jugó contra quién efectivamente se inscribió en el
    formulario de Microsoft Forms, para medir conversión real a vinculación.</li>
    <li><b>Usar el corpus del Reto 2 como insumo vivo</b> de la primera versión del
    instrumento de diagnóstico periódico de madurez analítica — ya hay 18 respuestas
    reales de las que partir, sin empezar de cero.</li>
    <li><b>Embeber el microsite en la web institucional del DNP</b> además del
    dominio independiente, para sumar el tráfico que hoy solo llega por enlace
    directo.</li>
    <li><b>Repetir el formato para sectores en cola</b> (salud, TIC, seguridad,
    financiero) que se autoidentificaron en el Reto 2 sin haber sido convocados —
    son la lista más barata de priorizar para el próximo ciclo de webinars
    sectoriales.</li>
    <li><b>Activar el anexo como lista semilla de los Diálogos Bilaterales.</b>
    Las 16 personas que completaron el circuito entero ya demostraron interés
    real; contactarlas primero (verificando el tratamiento de datos personales que
    aplique) convierte este piloto en relacionamiento efectivo, no solo en
    medición.</li>
  </ol>

  <div class="callout">
    <p style="margin:0">Este informe se preparó a partir de las 73 partidas
    recogidas entre el 6 y el 9 de julio de 2026 (hoja "Resumen" de
    <i>RENADIA_respuestas_SIN_VANESSA.xlsx</i>), excluyendo pruebas internas del
    equipo y envíos vacíos de bots. Los datos crudos, con sesión, fecha y origen
    de cada partida, están disponibles para el equipo RENADIA en el mismo
    archivo.</p>
  </div>
  {foot(10, PAGES_TOTAL)}
</div>

<div class="page">
  <div class="eyebrow">Anexo · Participantes</div>
  <h2 class="sec">Las 33 personas que jugaron, <b>una a una</b>.</h2>
  <p class="lede">Cada fila es una sesión de juego (una persona). El nombre aparece
  tal como lo escribió cada participante — algunos usaron alias; varios, su nombre
  completo real. "Segmento" es el declarado en el Reto 1 y "Sector" el declarado en
  el Reto 2 (— indica que no jugó ese reto o no diligenció el campo). Uso interno:
  insumo de relacionamiento para los Diálogos Bilaterales, sujeto al tratamiento de
  datos personales que aplique.</p>
  {anexo_tbl(ANEXO)}
  {foot(11, PAGES_TOTAL)}
</div>

</body></html>"""

if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    HTML(string=html, base_url=ROOT).write_pdf(OUT)
    print("OK ->", OUT)
