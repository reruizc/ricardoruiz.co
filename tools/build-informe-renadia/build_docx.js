/*
 * RENADIA · Informe de resultados — Convocatoria "Mundial 2026" (versión Word)
 * Mismo contenido y cifras que el PDF (build.py), mismo espíritu de identidad
 * visual (teal / magenta / amarillo, sin marca ricardoruiz.co) adaptado a un
 * documento Word editable para el equipo RENADIA/DNP.
 *
 * Fuente de datos: Bases de datos/DNP/respuestas-export/
 *   RENADIA_respuestas_SIN_VANESSA.xlsx (hoja Resumen + 3 hojas de retos).
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  Header, Footer, PageBreak, PageNumber, LevelFormat, convertInchesToTwip,
  VerticalAlign, TabStopType, TabStopPosition,
} = require("docx");

const OUT = path.join(
  "/Users/ricardoruiz/ricardoruiz.co", "Bases de datos", "DNP",
  "RENADIA-Informe-Resultados-Mundial2026.docx"
);

// ---- paleta RENADIA -------------------------------------------------------
const TEAL = "008C8A", TEALDK = "005f5e", TEALLT = "00C3C1";
const MAG = "FE187B", MAGDK = "9c0f4c";
const YEL = "FFCA00";
const INK = "12182A", INK2 = "39415A", MUTE = "6B748A";
const PAPER = "F4F6FB", LINE = "E2E7F1", WHITE = "FFFFFF";

const FONT = "Calibri";

// ---- datos (idénticos al PDF) --------------------------------------------
const PARTICIPANTES = 33, PARTIDAS = 73;
const RETO1_N = 36, RETO2_N = 18, RETO3_N = 19;

const POR_DIA = [["6 jul", 6, 8], ["7 jul", 43, 59], ["8 jul", 22, 30], ["9 jul", 2, 3]];
const RETOS = [["Reto 1 · Carta de jugador", 36, 49], ["Reto 2 · Diagnóstico sectorial", 18, 25], ["Reto 3 · Penaltis (mito o realidad)", 19, 26]];
const SEGMENTOS = [["Entidad nacional", 14, 39], ["Sector privado", 12, 33], ["Entidad territorial", 5, 14], ["Sector académico", 5, 14]];
const POSICIONES = [["DAT · exploración de datos", 17, 47], ["IA · automatizar y predecir", 10, 28], ["COC · cocreación y comunidad", 5, 14], ["GOB · gobernanza y ética", 4, 11]];
const QUE_MUEVE = [["Tomar mejores decisiones con evidencia", 13, 36], ["Aprender y crecer en datos e IA", 11, 31], ["Llevar la IA a resultados concretos", 8, 22], ["Conectar y construir con otros", 4, 11]];
const QUE_FRENA = [["Faltan capacidades o talento", 12, 33], ["Falta con quién intercambiar experiencias", 10, 28], ["Falta claridad para usar IA con ética", 7, 19], ["Faltan datos de calidad", 7, 19]];
const COMO_SUMAR = [["En mesas temáticas de trabajo", 22, 61], ["En webinars y charlas", 11, 31], ["En diálogos uno a uno", 3, 8]];
const SECTORES_R2 = ["Financiero (×2)", "Educación (×3, con variantes de escritura)", "Salud (×2)", "Gobernanza de IA", "Sector gastronómico", "Desarrollo económico", "Ambiente", "TIC", "Seguridad", "Gerencia de proyectos", "Seguros", "Minero-energético"];
const PENALTIS_Q = [["P1 · acierto", 14, 19, 74], ["P2 · acierto", 17, 19, 89], ["P3 · acierto", 15, 19, 79], ["P4 · acierto", 14, 19, 74], ["P5 · acierto", 16, 19, 84]];
const QUOTES_R2 = [
  ["Financiero", "«Las entidades tienen muchos datos al interior de forma dispersa en distintas bases de datos y poco personal para explotarlos.»"],
  ["TIC", "«Unas plantillas que faciliten la estructuración de una política del dato institucional […] apuntando a marcos por excelencia aceptados por la industria para el Gobierno y Gobernanza de datos.»"],
  ["Minero-energético", "«Centralización de datos e interoperabilidad» — citada como el desafío más urgente del sector."],
  ["Entidad territorial", "«El trabajo se acaba cuando cambian de contratistas y se pierde el conocimiento, falta de empalme y guardar información.»"],
];

// Embudo por sesión (33 sesiones ≡ 33 participantes)
const EMBUDO = [["Completaron los 3 retos (circuito completo)", 16, 48], ["Completaron 2 retos", 3, 9], ["Jugaron 1 reto", 14, 42]];

// Penaltis con el texto real de cada afirmación
const PENALTIS_MITOS = [
  ["«La IA reemplazará a los funcionarios públicos» (mito)", 14, 74],
  ["«Para empezar a usar analítica hay que invertir millones» (mito)", 17, 89],
  ["«Compartir aprendizajes entre entidades acelera la madurez» (realidad)", 15, 79],
  ["«La gobernanza de datos es solo un asunto técnico de TI» (mito)", 14, 74],
  ["«Unirse a RENADIA tiene costos y obligaciones legales» (mito)", 16, 84],
];

// Anexo: las 33 sesiones/participantes (nombre tal como lo escribió cada quien)
const ANEXO = [
  ["6 jul", "coquito", "Entidad nacional", "—", "1 y 3"],
  ["6 jul", "ALETHEOX", "Sector privado", "Gobernanza de IA", "1, 2 y 3"],
  ["7 jul", "Jesus Zetien", "Sector privado", "Sector gastronómico", "1, 2 y 3"],
  ["7 jul", "Victor Hugo Vidal Molina", "Entidad territorial", "Desarrollo Económico", "1, 2 y 3"],
  ["7 jul", "Juan_Useche", "Entidad nacional", "—", "1"],
  ["7 jul", "siiuary", "Entidad territorial", "Educación", "1, 2 y 3"],
  ["7 jul", "Karen", "Entidad nacional", "—", "1"],
  ["7 jul", "NORMA ALVAREZ", "Sector académico", "Educación", "1, 2 y 3"],
  ["7 jul", "Omar Villarreal Osorio", "Entidad nacional", "Ambiente", "1, 2 y 3"],
  ["7 jul", "Diafon", "Sector privado", "Financiero", "1, 2 y 3"],
  ["7 jul", "JulianDDM", "Entidad territorial", "—", "1"],
  ["7 jul", "MIGUEL CRUZ", "Entidad nacional", "TIC", "1, 2 y 3"],
  ["7 jul", "Diana", "Entidad territorial", "—", "1, 2 y 3"],
  ["7 jul", "Jacquelie", "Sector privado", "—", "1"],
  ["7 jul", "(sin nombre)", "—", "Seguridad", "2"],
  ["7 jul", "Brandon Arboleda Jaramillo", "Sector académico", "Educación", "1 y 2"],
  ["7 jul", "CEO Juan Carlos", "Sector privado", "Gerencia de Proyectos", "1, 2 y 3"],
  ["7 jul", "Emilio9306", "Sector académico", "Educación", "1, 2 y 3"],
  ["7 jul", "Johan", "Sector privado", "—", "1"],
  ["7 jul", "Juan", "Sector privado", "—", "1"],
  ["7 jul", "Esteban Urrutia", "Entidad nacional", "—", "1"],
  ["8 jul", "Willinton", "Entidad nacional", "—", "1"],
  ["8 jul", "Claudiaj", "Sector privado", "Financiero", "1, 2 y 3"],
  ["8 jul", "Alvaro23", "Sector privado", "Seguros", "1, 2 y 3"],
  ["8 jul", "Laura M", "Entidad territorial", "—", "1"],
  ["8 jul", "Lorena", "Entidad nacional", "—", "1 y 3"],
  ["8 jul", "werewr", "Entidad nacional", "Minero-energético", "1, 2 y 3"],
  ["8 jul", "Alejandro Gutiérrez", "Sector académico", "Salud", "1, 2 y 3"],
  ["8 jul", "Carlos", "Entidad nacional", "—", "1"],
  ["8 jul", "Santiago", "Entidad nacional", "Información de salud", "1, 2 y 3"],
  ["8 jul", "Gustavo Cadena", "Entidad nacional", "—", "1"],
  ["9 jul", "Diana Paola Ahumada Riaño", "Sector académico", "—", "1"],
  ["9 jul", "Echo40", "Sector privado", "—", "1"],
];

// ---- helpers de texto ------------------------------------------------------
function P(children, opts = {}) {
  return new Paragraph({ children, spacing: { after: 140, ...(opts.spacing || {}) }, ...opts });
}
function T(text, opts = {}) { return new TextRun({ text, font: FONT, ...opts }); }

function body(text) {
  return P([T(text, { size: 21, color: INK2 })], { spacing: { after: 180, line: 300 } });
}

function eyebrow(text) {
  return P([T(text.toUpperCase(), { size: 16, bold: true, color: TEAL, characterSpacing: 20 })],
    { spacing: { before: 80, after: 60 } });
}

function h2(children) {
  return P(children, {
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 0, after: 220 },
  });
}
function hrun(text, opts = {}) { return new TextRun({ text, font: FONT, size: 30, bold: true, color: INK, ...opts }); }

function h3(text) {
  return P([T(text, { size: 24, bold: true, color: TEALDK })], { spacing: { before: 260, after: 120 } });
}

function bullet(children, color = TEALLT) {
  return P(children, {
    spacing: { after: 130, line: 280 },
    bullet: { level: 0 },
  });
}

function bulletRun(bold, rest, opts = {}) {
  const runs = [];
  if (bold) runs.push(T(bold, { size: 21, bold: true, color: INK }));
  runs.push(T(rest, { size: 21, color: INK2 }));
  return bullet(runs, opts.color);
}

function num(children) {
  return P(children, { spacing: { after: 150, line: 280 }, numbering: { reference: "steps", level: 0 } });
}
function numRecs(children) {
  return P(children, { spacing: { after: 150, line: 280 }, numbering: { reference: "recs", level: 0 } });
}

function calloutTable(text, { border = TEALLT, fill = "EFFAFA" } = {}) {
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: allBorders(border, 8),
    rows: [
      new TableRow({
        children: [
          new TableCell({
            shading: { type: ShadingType.CLEAR, fill },
            margins: { top: 160, bottom: 160, left: 220, right: 220 },
            children: [P([T(text, { size: 21, color: INK })], { spacing: { after: 0 }, line: 300 })],
          }),
        ],
      }),
    ],
  });
}

function allBorders(color, size = 4) {
  const b = { style: BorderStyle.SINGLE, size, color };
  return { top: b, bottom: b, left: b, right: b, insideHorizontal: b, insideVertical: b };
}
function noBorders() {
  const b = { style: BorderStyle.NONE, size: 0, color: WHITE };
  return { top: b, bottom: b, left: b, right: b, insideHorizontal: b, insideVertical: b };
}

// tabla simple: [label, n, pct] con header oscuro
function dataTable(rows, { headerLabel = "Ítem", headerColor = INK, accent = TEALLT } = {}) {
  const headerRow = new TableRow({
    tableHeader: true,
    children: [
      new TableCell({ shading: { type: ShadingType.CLEAR, fill: headerColor }, width: { size: 62, type: WidthType.PERCENTAGE },
        margins: { top: 90, bottom: 90, left: 140, right: 140 },
        children: [P([T(headerLabel, { size: 17, bold: true, color: WHITE, characterSpacing: 8 })], { spacing: { after: 0 } })] }),
      new TableCell({ shading: { type: ShadingType.CLEAR, fill: headerColor }, width: { size: 19, type: WidthType.PERCENTAGE },
        margins: { top: 90, bottom: 90, left: 140, right: 140 },
        children: [P([T("N", { size: 17, bold: true, color: WHITE, characterSpacing: 8 })], { alignment: AlignmentType.RIGHT, spacing: { after: 0 } })] }),
      new TableCell({ shading: { type: ShadingType.CLEAR, fill: headerColor }, width: { size: 19, type: WidthType.PERCENTAGE },
        margins: { top: 90, bottom: 90, left: 140, right: 140 },
        children: [P([T("%", { size: 17, bold: true, color: WHITE, characterSpacing: 8 })], { alignment: AlignmentType.RIGHT, spacing: { after: 0 } })] }),
    ],
  });
  const bodyRows = rows.map(([label, n, pct], i) => new TableRow({
    children: [
      new TableCell({ shading: { type: ShadingType.CLEAR, fill: i % 2 ? PAPER : WHITE },
        margins: { top: 90, bottom: 90, left: 140, right: 140 },
        children: [P([T(label, { size: 19, color: INK })], { spacing: { after: 0 } })] }),
      new TableCell({ shading: { type: ShadingType.CLEAR, fill: i % 2 ? PAPER : WHITE },
        margins: { top: 90, bottom: 90, left: 140, right: 140 },
        children: [P([T(String(n), { size: 19, bold: true, color: accent })], { alignment: AlignmentType.RIGHT, spacing: { after: 0 } })] }),
      new TableCell({ shading: { type: ShadingType.CLEAR, fill: i % 2 ? PAPER : WHITE },
        margins: { top: 90, bottom: 90, left: 140, right: 140 },
        children: [P([T(pct + "%", { size: 19, bold: true, color: accent })], { alignment: AlignmentType.RIGHT, spacing: { after: 0 } })] }),
    ],
  }));
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: allBorders(LINE, 4),
    rows: [headerRow, ...bodyRows],
  });
}

// tabla del anexo: 5 columnas [fecha, nombre, segmento, sector, retos]
function anexoTable(rows) {
  const widths = [10, 28, 22, 26, 14];
  const heads = ["Fecha", "Participante", "Segmento (Reto 1)", "Sector (Reto 2)", "Retos"];
  const headerRow = new TableRow({
    tableHeader: true,
    children: heads.map((h, i) => new TableCell({
      shading: { type: ShadingType.CLEAR, fill: TEALDK },
      width: { size: widths[i], type: WidthType.PERCENTAGE },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: [P([T(h, { size: 16, bold: true, color: WHITE, characterSpacing: 6 })], { spacing: { after: 0 } })],
    })),
  });
  const bodyRows = rows.map((r, ri) => new TableRow({
    children: r.map((cellText, i) => new TableCell({
      shading: { type: ShadingType.CLEAR, fill: ri % 2 ? PAPER : WHITE },
      width: { size: widths[i], type: WidthType.PERCENTAGE },
      margins: { top: 70, bottom: 70, left: 120, right: 120 },
      children: [P([T(cellText, { size: 17, color: i === 1 ? INK : INK2, bold: i === 1 })], { spacing: { after: 0 } })],
    })),
  }));
  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: allBorders(LINE, 4),
    rows: [headerRow, ...bodyRows],
  });
}

function statTiles(items) {
  // items: [n, label, fill]
  const cells = items.map(([n, label, fill]) => new TableCell({
    shading: { type: ShadingType.CLEAR, fill },
    width: { size: 25, type: WidthType.PERCENTAGE },
    margins: { top: 200, bottom: 200, left: 160, right: 160 },
    verticalAlign: VerticalAlign.CENTER,
    children: [
      P([T(n, { size: 40, bold: true, color: WHITE })], { spacing: { after: 60 } }),
      P([T(label, { size: 15, color: "D7E6E6" })], { spacing: { after: 0 }, line: 260 }),
    ],
  }));
  return new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, borders: noBorders(),
    rows: [new TableRow({ children: cells })] });
}

function spacer(h = 120) { return P([T("", { size: 2 })], { spacing: { after: h } }); }

// ---------------------------------------------------------------------------
const doc = new Document({
  numbering: {
    config: [
      { reference: "steps", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 460, hanging: 300 } } } }] },
      { reference: "recs", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 460, hanging: 300 } } } }] },
    ],
  },
  styles: {
    default: {
      document: { run: { font: FONT, size: 21, color: INK2 } },
    },
    paragraphStyles: [
      {
        id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 34, bold: true, color: INK },
        paragraph: { spacing: { before: 0, after: 220 } },
      },
    ],
  },
  sections: [
    // ---- PORTADA ----
    {
      properties: {
        page: { size: { width: 11906, height: 16838 }, margin: { top: 1600, bottom: 1600, left: 1440, right: 1440 } },
      },
      children: [
        P([T("INFORME DE RESULTADOS", { size: 18, bold: true, color: YEL, characterSpacing: 30 })], { spacing: { after: 500 } }),
        P([T("Colombia jugó el Mundial de los datos.", { size: 46, bold: true, color: INK })], { spacing: { after: 40 }, line: 300 }),
        P([T("Esto fue lo que dejó el primer partido.", { size: 46, bold: true, color: TEAL })], { spacing: { after: 500 }, line: 300 }),
        P([T("Resultados y lectura de impacto del piloto de convocatoria gamificada de RENADIA — Red Nacional de Analítica de Datos e Inteligencia Artificial — desplegado del 6 al 9 de julio de 2026.",
          { size: 23, color: INK2 })], { spacing: { after: 500 }, line: 320 }),
        calloutTable("Documento interno de trabajo. Preparado para el equipo RENADIA · Unidad de Ciencia de Datos · Dirección de Desarrollo Digital (DNP).",
          { border: TEALLT, fill: "EFFAFA" }),
        spacer(600),
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE }, borders: noBorders(),
          rows: [new TableRow({ children: [
            new TableCell({ width: { size: 34, type: WidthType.PERCENTAGE }, children: [
              P([T("VENTANA ANALIZADA", { size: 15, bold: true, color: MUTE, characterSpacing: 10 })], { spacing: { after: 40 } }),
              P([T("6 – 9 de julio de 2026", { size: 19, color: INK })], { spacing: { after: 0 } }),
            ] }),
            new TableCell({ width: { size: 33, type: WidthType.PERCENTAGE }, children: [
              P([T("PARTICIPACIÓN", { size: 15, bold: true, color: MUTE, characterSpacing: 10 })], { spacing: { after: 40 } }),
              P([T("33 participantes · 73 partidas", { size: 19, color: INK })], { spacing: { after: 0 } }),
            ] }),
            new TableCell({ width: { size: 33, type: WidthType.PERCENTAGE }, children: [
              P([T("PREPARADO", { size: 15, bold: true, color: MUTE, characterSpacing: 10 })], { spacing: { after: 40 } }),
              P([T(new Date().toLocaleDateString("es-CO", { year: "numeric", month: "long", day: "numeric" }), { size: 19, color: INK })], { spacing: { after: 0 } }),
            ] }),
          ] })],
        }),
        P([new PageBreak()]),

        // ---- 01 · RESUMEN EJECUTIVO ----
        eyebrow("01 · Resumen ejecutivo"),
        h2([hrun("En 56 horas, "), hrun("33 personas", { color: MAG }), hrun(" jugaron su forma de entrar a RENADIA.")]),
        body("Entre el 6 y el 9 de julio de 2026 estuvo activo el microsite de convocatoria \"Mundial 2026\" — una forma alternativa, lúdica, de presentar RENADIA y explicar en qué consiste vincularse a la red, sin depender de un webinar o un boletín. El resultado: 73 partidas jugadas por 33 personas distintas, con participación de entidades nacionales, territoriales, sector privado y academia, y un corpus de respuestas abiertas que funciona como diagnóstico temprano de madurez analítica en 12+ sectores."),
        statTiles([
          ["33", "personas distintas jugaron al menos un reto", TEAL],
          ["73", "partidas completadas en total", MAG],
          ["56h", "de ventana activa (6–9 jul, 2,3 días)", INK2],
          ["12+", "sectores distintos autodeclarados", TEALDK],
        ]),
        spacer(260),
        h3("Lo más importante para RENADIA"),
        calloutTable("El reto 1 midió, sin decirlo, la pregunta que RENADIA se está haciendo en este mismo momento. A la pregunta \"¿cómo prefieres sumar al equipo?\", el 61% de las 36 respuestas eligió mesas temáticas de trabajo por encima de webinars (31%) y diálogos uno a uno (8%). Esto corre en paralelo — misma semana — al piloto de Mesas Temáticas que arrancó el 6 de julio: el microsite entregó, sin proponérselo, una primera señal cuantitativa a favor del giro estratégico hacia formatos interactivos descrito en la sección 3.2 del documento base de RENADIA.",
          { border: TEALLT, fill: "EFFAFA" }),
        h3("Cómo leer este informe"),
        body("Las secciones 2 y 3 explican qué se construyó y cómo funcionó el embudo de participación. Las secciones 4 a 6 presentan los resultados cuantitativos y cualitativos por reto. La sección 7 conecta esos resultados con las líneas de trabajo y oportunidades de mejora ya identificadas por el equipo RENADIA. La sección 8 es honesta sobre los límites de esta primera ventana y qué se recomienda medir en la siguiente."),

        P([new PageBreak()]),

        // ---- 02 · QUÉ SE CONSTRUYÓ ----
        eyebrow("02 · Qué se construyó"),
        h2([hrun("Un "), hrun("microsite", { color: MAG }), hrun(" con la mecánica de un álbum de figuritas del Mundial.")]),
        body("En lugar de un formulario de inscripción tradicional, la convocatoria se armó como una experiencia jugable, mobile-first, con la estética de un Mundial de fútbol — la misma metáfora que ya usaba el \"Tablero fest\" de RENADIA en formato físico, ahora en digital."),
        h3("La mecánica: 3 retos + álbum de 5 láminas"),
        num([T("Reto 1 · \"Tu carta de jugador\"", { bold: true, color: INK, size: 21 }), T(" — 5 preguntas cortas arman una carta de FIFA con OVR y posición (DAT / IA / GOB / COC), reflejo del perfil de la persona frente a datos e IA. Es la puerta de entrada: la más jugada de las tres.", { color: INK2, size: 21 })]),
        num([T("Reto 2 · \"Tu sector frente a los datos\"", { bold: true, color: INK, size: 21 }), T(" — 4 preguntas abiertas de diagnóstico: desafío más urgente, qué datos faltan, qué datos ya existen, qué iniciativas de IA conoce la persona en su sector. Es el reto de mayor compromiso — texto libre, no opción múltiple.", { color: INK2, size: 21 })]),
        num([T("Reto 3 · \"Tanda de penaltis\"", { bold: true, color: INK, size: 21 }), T(" — 5 afirmaciones de mito o realidad sobre datos e IA; cada acierto \"ataja\" un penalti. Funciona como pieza educativa.", { color: INK2, size: 21 })]),
        num([T("Álbum RENADIA", { bold: true, color: INK, size: 21 }), T(" — completar los 3 retos, más registrarse y compartir, llena las 5 láminas del álbum. El CTA final no es un \"gracias\" — es un enlace directo al formulario oficial de RENADIA (Microsoft Forms), la vinculación real. El juego es el enganche; el formulario sigue siendo la puerta formal.", { color: INK2, size: 21 })]),
        h3("Bajo el capó"),
        bulletRun("Desplegado como sitio estático independiente en renadia-mundial.pages.dev — ", "pensado para ser embebible dentro de la web institucional del DNP sin depender de su infraestructura."),
        bulletRun("Cada respuesta se envía por sendBeacon a un backend serverless propio ", "(AWS Lambda + API Gateway) y queda guardada en S3, un objeto por partida, con sesión, origen y timestamp — sin necesidad de que la persona complete nada más que el juego mismo."),
        bulletRun("Identidad visual propia (teal / magenta / amarillo), ", "sin marca de terceros — el microsite se ve y se siente 100% RENADIA."),

        P([new PageBreak()]),

        // ---- 03 · PARTICIPACIÓN ----
        eyebrow("03 · Participación"),
        h2([hrun("73 partidas, con un pico claro el "), hrun("7 de julio", { color: MAG }), hrun(".")]),
        body("La distribución por día muestra una convocatoria puntual — no una campaña sostenida en el tiempo. El 59% de las partidas ocurrió en un solo día, lo que sugiere que el enlace se compartió una vez (correo, webinar o publicación) en lugar de mantenerse activo con recordatorios escalonados."),
        dataTable(POR_DIA, { headerLabel: "Día", headerColor: INK, accent: TEALDK }),
        spacer(200),
        h3("Partidas por reto"),
        dataTable(RETOS, { headerLabel: "Reto", headerColor: TEALDK, accent: TEALDK }),
        body("El Reto 1 concentra casi la mitad de las partidas — es, como estaba pensado, la puerta de entrada más liviana. El Reto 2 (texto libre) retuvo a la mitad de quienes jugaron el Reto 1: buena señal de compromiso para un formato que exige más esfuerzo."),
        h3("Segmento declarado (Reto 1, n=36)"),
        dataTable(SEGMENTOS, { headerLabel: "Segmento", headerColor: MAGDK, accent: MAGDK }),
        body("Paridad casi perfecta entre entidad nacional (39%) y sector privado (33%) — la convocatoria no solo llegó al público natural de RENADIA (entidades públicas), sino que atrajo en volumen comparable a empresas privadas, con presencia adicional de territorial y academia."),
        P([new PageBreak()]),
        h3("El embudo: casi la mitad completó el circuito entero"),
        dataTable(EMBUDO, { headerLabel: "Recorrido (33 sesiones)", headerColor: TEALDK, accent: TEALDK }),
        body("De las 33 personas que entraron a jugar, 16 (48%) completaron los tres retos — un circuito de unos 10 minutos que incluye un reto de texto libre. Para una experiencia voluntaria, sin premio material y sin registro obligatorio, esa retención es alta: la mecánica de álbum (\"te faltan N láminas\") parece estar haciendo su trabajo de arrastre entre retos."),
        h3("Cuándo jugaron"),
        body("El 77% de las partidas ocurrió en horario laboral (8:00–17:00, hora de Colombia), con el pico en la franja de 12:00 a 14:00 (42% del total) — consistente con una difusión por canales institucionales que la gente atendió durante la jornada. Hay además una cola nocturna (22:00–23:00, 16%) que sugiere que varias personas retomaron el enlace por su cuenta al final del día."),

        P([new PageBreak()]),

        // ---- 04 · PERFIL Y MOTIVACIONES ----
        eyebrow("04 · Perfil y motivaciones (Reto 1)"),
        h2([hrun("La mayoría se ve "), hrun("explorando datos", { color: MAG }), hrun(", no haciendo gobernanza.")]),
        body("La posición de la carta de jugador (DAT / IA / GOB / COC) resume, con una sola palabra, cómo cada persona se percibe frente a los datos y la IA."),
        dataTable(POSICIONES, { headerLabel: "Posición", headerColor: TEALDK, accent: TEALDK }),
        body("Casi la mitad (47%) se identifica como perfil DAT — \"los exploro y visualizo para encontrar historias\" — por encima de IA (28%), cocreación (14%) y gobernanza (11%). Para RENADIA esto es una pista de tono: el mensaje que mejor conecta hoy es el del dato práctico y exploratorio, no el marco normativo o de gobernanza (que sigue siendo relevante, pero conecta menos en primer contacto)."),
        h3("¿Qué te mueve a jugar este partido?"),
        dataTable(QUE_MUEVE, { headerLabel: "Motivación", headerColor: MAGDK, accent: MAGDK }),
        h3("¿Qué te frena hoy?"),
        dataTable(QUE_FRENA, { headerLabel: "Freno", headerColor: "8a6d00", accent: "8a6d00" }),
        body("El freno más citado no es la tecnología ni los datos — es talento y capacidades (33%), seguido de cerca por la falta de pares con quién intercambiar experiencias (28%). Ambos son exactamente lo que una red de pares como RENADIA está en posición de resolver."),
        h3("¿Cómo prefieres sumar al equipo?"),
        dataTable(COMO_SUMAR, { headerLabel: "Formato preferido", headerColor: INK2, accent: INK2 }),
        calloutTable("Mesas temáticas de trabajo (61%) gana por más del doble sobre webinars y charlas (31%), y por siete veces sobre diálogos uno a uno (8%). Es la validación cuantitativa más directa que este piloto produjo para el giro estratégico hacia formatos interactivos.",
          { border: MAG, fill: "FFF0F6" }),
        spacer(120),
        body("La preferencia por mesas temáticas es además transversal a los cuatro segmentos: es la primera opción en sector privado (8 de 12), entidad nacional (7 de 14) y sector académico (5 de 5, unánime), y empata con webinars en entidad territorial (2 de 5). No es un sesgo de un solo público — es un patrón de toda la muestra."),

        P([new PageBreak()]),

        // ---- 05 · DIAGNÓSTICO SECTORIAL ----
        eyebrow("05 · Diagnóstico sectorial (Reto 2)"),
        h2([hrun("18 diagnósticos de texto libre, en "), hrun("12+ sectores", { color: MAG }), hrun(" distintos.")]),
        body("El Reto 2 no ofrece opciones — pide texto libre sobre el desafío más urgente del sector, qué datos faltan, qué datos ya existen y qué iniciativas de IA conoce la persona. El resultado es un corpus cualitativo real, sin filtrar por lo que RENADIA cree que la gente va a decir."),
        h3("Sectores autodeclarados"),
        ...SECTORES_R2.map((s) => bulletRun("", s)),
        body("Más de la mitad de estos sectores (salud, TIC, seguridad, seguros, gerencia de proyectos, gastronómico) no corresponden a ninguno de los dos sectores cubiertos hasta ahora por el ciclo de webinars sectoriales (Comercio/Industria/Turismo y Minas y Energía) — una señal de demanda para próximos sectores en cola."),
        h3("Temas que se repiten aunque nadie los coordinó"),
        bulletRun("Interoperabilidad y centralización de datos. ", "Aparece con distintas palabras en TIC, minero-energético, seguridad (\"datos unificados\") y ambiente (\"interoperabilidad\") — es el desafío transversal más mencionado."),
        bulletRun("Datos dispersos y de mala calidad. ", "Financiero, salud y educación coinciden en que el problema no es la falta de datos sino su dispersión en sistemas que no se hablan y la falta de gente para explotarlos."),
        bulletRun("Talento y capacitación. ", "Coherente con el freno más citado del Reto 1 (\"faltan capacidades o talento\", 33%): varios diagnósticos piden formación antes que tecnología."),
        bulletRun("Pérdida de conocimiento institucional. ", "Una respuesta territorial lo dice sin rodeos — ver la última cita abajo: la rotación de contratistas borra la memoria de las entidades. Es un problema de gestión del conocimiento, exactamente el tipo de práctica que una red de pares puede ayudar a sistematizar."),
        h3("Algunas voces textuales"),
        ...QUOTES_R2.flatMap(([who, txt]) => [
          P([T(who.toUpperCase(), { size: 16, bold: true, color: TEALDK, characterSpacing: 10 })], { spacing: { before: 120, after: 40 } }),
          P([T(txt, { size: 20, color: INK, italics: false })], { spacing: { after: 160 }, line: 300,
            border: { left: { style: BorderStyle.SINGLE, size: 18, color: TEALLT, space: 8 } } }),
        ]),
        h3("Reto 3 · Mito o realidad (penaltis)"),
        body("Acierto promedio: 4,0 / 5 (80%). El contenido educativo del juego aterrizó bien — la mayoría \"atajó\" 4 o 5 de los 5 mitos. El detalle por afirmación deja dos lecturas útiles:"),
        dataTable(PENALTIS_MITOS, { headerLabel: "Afirmación del penalti", headerColor: TEALDK, accent: TEALDK }),
        bulletRun("Los mitos más persistentes (74% de acierto, 1 de cada 4 falló) ", "son \"la IA reemplazará a los funcionarios públicos\" y \"la gobernanza de datos es solo un asunto de TI\". Son los dos frentes donde más pedagogía falta — candidatos naturales a contenido de próximos webinars y boletines."),
        bulletRun("El mito de los costos de membresía fue bien atajado (84%). ", "El mensaje central de la convocatoria — vinculación voluntaria, sin costos ni obligaciones legales — está llegando con claridad."),

        P([new PageBreak()]),

        // ---- 06 · LECTURA DE IMPACTO ----
        eyebrow("06 · Lectura de impacto"),
        h2([hrun("Lo que este piloto le "), hrun("aporta", { color: MAG }), hrun(" a RENADIA más allá del conteo.")]),
        bulletRun("Validación temprana de la apuesta a Mesas Temáticas. ", "El 61% de preferencia por este formato (sección 4) llega justo en la semana en que RENADIA empezó a pilotearlo (fase 1, desde el 6 de julio) — es una señal externa e independiente de que el giro estratégico va en la dirección correcta."),
        bulletRun("Insumo directo para el \"instrumento de diagnóstico periódico\" ", "que el documento base de RENADIA identifica como oportunidad de mejora (línea 3): las 18 respuestas del Reto 2 son, en la práctica, un primer prototipo — barato y rápido de levantar — de ese instrumento, con datos reales de 12+ sectores."),
        bulletRun("Demanda sectorial para expandir el ciclo de webinars. ", "Sectores como salud, TIC, seguridad y financiero aparecieron por iniciativa propia de los participantes, sin que RENADIA los convocara — son candidatos naturales para las próximas rondas de webinars sectoriales."),
        bulletRun("Un canal de bajo costo y bajo esfuerzo de mantenimiento. ", "33 personas en 56 horas, sin pauta paga, sin evento presencial y con un solo envío de enlace — comparado con el costo operativo de una campaña de correos entidad por entidad, es un canal barato de calentar interés antes del formulario oficial."),
        bulletRun("Paridad público-privado inesperada. ", "El 33% de participación de sector privado (sección 3) sugiere que el microsite, al no requerir credenciales institucionales ni un correo de gobierno, atrajo a un público que un boletín dirigido a entidades no habría alcanzado igual de fácil — relevante para la ambición de RENADIA de operar como \"red de redes\" más allá del sector público."),
        bulletRun("El formato retiene: 48% completó el circuito entero. ", "16 de 33 personas jugaron los tres retos, incluido el de texto libre — el más exigente. La mecánica de álbum sostiene el recorrido completo mejor de lo que suele sostener un formulario largo tradicional."),
        bulletRun("33 contactos identificables para los Diálogos Bilaterales. ", "La mayoría dejó nombre (varios, nombre completo real) y segmento o sector — el anexo consolida la lista. Es una lista semilla concreta para el relacionamiento personalizado que RENADIA está pilotando, empezando por las 16 personas que completaron todo el circuito (las de mayor engagement demostrado)."),

        P([new PageBreak()]),

        // ---- 07 · LÍMITES DEL PILOTO ----
        eyebrow("07 · Límites del piloto"),
        h2([hrun("Qué "), hrun("no", { color: MAG }), hrun(" dice todavía este número, con honestidad.")]),
        bulletRun("No hay dato de alcance ni de visitas. ", "El backend solo registra partidas completadas, no vistas de página ni abandonos — no se puede calcular una tasa de conversión real (cuántas personas vieron el microsite y no jugaron)."),
        bulletRun("Ventana corta y concentrada. ", "56 horas con un solo pico de difusión (59% en un día) no permite separar \"el formato funciona\" de \"el momento de difusión funcionó\" — habría que repetirlo con difusión escalonada para aislar el efecto del formato."),
        bulletRun("No se rastrea conversión a vinculación formal. ", "El juego entrega al formulario oficial de Microsoft Forms, pero ese formulario vive fuera de este sistema — no se puede confirmar hoy cuántas de las 33 personas completaron también la inscripción real a RENADIA."),
        bulletRun("Muestra autoseleccionada y pequeña. ", "33 personas es útil como señal direccional (por ejemplo, la preferencia por mesas temáticas), pero no alcanza para tratarse como representativo de todo el universo de entidades y personas que RENADIA busca vincular."),
        bulletRun("El microsite aún no estaba embebido en la web institucional del DNP. ", "El 100% del tráfico llegó por el dominio independiente (renadia-mundial.pages.dev); integrarlo al sitio institucional es una fuente de alcance todavía sin explotar."),

        P([new PageBreak()]),

        // ---- 08 · RECOMENDACIONES ----
        eyebrow("08 · Recomendaciones"),
        h2([hrun("Qué haría más fuerte la "), hrun("próxima ronda", { color: MAG }), hrun(".")]),
        numRecs([T("Difusión escalonada, no de un solo golpe.", { bold: true, color: INK, size: 21 }), T(" Repartir el enlace en 2 o 3 momentos (ej. tras un webinar, en un boletín, en redes) en vez de un único envío, para sostener el flujo en lugar de un pico de un día.", { color: INK2, size: 21 })]),
        numRecs([T("Instrumentar vistas de página, no solo partidas completadas.", { bold: true, color: INK, size: 21 }), T(" Agregar un evento simple de \"entró al microsite\" permite calcular una tasa de conversión real de visita → juego completado.", { color: INK2, size: 21 })]),
        numRecs([T("Cerrar el ciclo con el formulario oficial.", { bold: true, color: INK, size: 21 }), T(" Cruzar (por correo o nombre, con consentimiento) quién jugó contra quién efectivamente se inscribió en el formulario de Microsoft Forms, para medir conversión real a vinculación.", { color: INK2, size: 21 })]),
        numRecs([T("Usar el corpus del Reto 2 como insumo vivo", { bold: true, color: INK, size: 21 }), T(" de la primera versión del instrumento de diagnóstico periódico de madurez analítica — ya hay 18 respuestas reales de las que partir, sin empezar de cero.", { color: INK2, size: 21 })]),
        numRecs([T("Embeber el microsite en la web institucional del DNP", { bold: true, color: INK, size: 21 }), T(" además del dominio independiente, para sumar el tráfico que hoy solo llega por enlace directo.", { color: INK2, size: 21 })]),
        numRecs([T("Repetir el formato para sectores en cola", { bold: true, color: INK, size: 21 }), T(" (salud, TIC, seguridad, financiero) que se autoidentificaron en el Reto 2 sin haber sido convocados — son la lista más barata de priorizar para el próximo ciclo de webinars sectoriales.", { color: INK2, size: 21 })]),
        numRecs([T("Activar el anexo como lista semilla de los Diálogos Bilaterales.", { bold: true, color: INK, size: 21 }), T(" Las 16 personas que completaron el circuito entero ya demostraron interés real; contactarlas primero (verificando el tratamiento de datos personales que aplique) convierte este piloto en relacionamiento efectivo, no solo en medición.", { color: INK2, size: 21 })]),
        spacer(160),
        calloutTable("Este informe se preparó a partir de las 73 partidas recogidas entre el 6 y el 9 de julio de 2026 (hoja \"Resumen\" de RENADIA_respuestas_SIN_VANESSA.xlsx), excluyendo pruebas internas del equipo y envíos vacíos de bots. Los datos crudos, con sesión, fecha y origen de cada partida, están disponibles para el equipo RENADIA en el mismo archivo.",
          { border: TEALLT, fill: "EFFAFA" }),

        P([new PageBreak()]),

        // ---- ANEXO · PARTICIPANTES ----
        eyebrow("Anexo · Participantes"),
        h2([hrun("Las 33 personas que jugaron, "), hrun("una a una", { color: MAG }), hrun(".")]),
        body("Cada fila es una sesión de juego (una persona). El nombre aparece tal como lo escribió cada participante — algunos usaron alias; varios, su nombre completo real. \"Segmento\" es el declarado en el Reto 1 y \"Sector\" el declarado en el Reto 2 (— indica que no jugó ese reto o no diligenció el campo). Uso interno: insumo de relacionamiento para los Diálogos Bilaterales, sujeto al tratamiento de datos personales que aplique."),
        anexoTable(ANEXO),
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log("OK ->", OUT);
});
