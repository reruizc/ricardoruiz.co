/*
 * RENADIA · Correo a la comunidad — "Llegamos a 1.000" (versión Word, 1 página)
 * Pieza corta a modo de correo/carta para los miembros de la red: hito de los
 * 1.000 miembros + 2-3 datos del ejercicio "Mundial 2026" + anuncio de que
 * arrancan las Mesas Temáticas (porque la comunidad las pidió).
 * Identidad RENADIA (teal / magenta / amarillo), sin marca de terceros.
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  VerticalAlign,
} = require("docx");

const OUT = path.join(
  "/Users/ricardoruiz/ricardoruiz.co", "Bases de datos", "DNP",
  "RENADIA-Correo-Comunidad-1000-Mesas.docx"
);

const TEAL = "008C8A", TEALDK = "005f5e", TEALLT = "00C3C1";
const MAG = "FE187B";
const YEL = "FFCA00";
const INK = "12182A", INK2 = "39415A", MUTE = "6B748A";
const PAPER = "F4F6FB", LINE = "E2E7F1", WHITE = "FFFFFF";
const FONT = "Calibri";

function P(children, opts = {}) {
  return new Paragraph({ children, spacing: { after: 140, ...(opts.spacing || {}) }, ...opts });
}
function T(text, opts = {}) { return new TextRun({ text, font: FONT, ...opts }); }
function body(runs, opts = {}) {
  return P(runs, { spacing: { after: 170, line: 290 }, ...opts });
}
function noBorders() {
  const b = { style: BorderStyle.NONE, size: 0, color: WHITE };
  return { top: b, bottom: b, left: b, right: b, insideHorizontal: b, insideVertical: b };
}
function allBorders(color, size = 4) {
  const b = { style: BorderStyle.SINGLE, size, color };
  return { top: b, bottom: b, left: b, right: b, insideHorizontal: b, insideVertical: b };
}

// banda de 3 stats
function statBand(items) {
  const cells = items.map(([n, label, fill]) => new TableCell({
    shading: { type: ShadingType.CLEAR, fill },
    width: { size: 34, type: WidthType.PERCENTAGE },
    margins: { top: 150, bottom: 150, left: 150, right: 150 },
    verticalAlign: VerticalAlign.CENTER,
    children: [
      P([T(n, { size: 34, bold: true, color: WHITE })], { alignment: AlignmentType.CENTER, spacing: { after: 40 } }),
      P([T(label, { size: 14, color: "E6F7F7" })], { alignment: AlignmentType.CENTER, spacing: { after: 0 }, line: 240 }),
    ],
  }));
  return new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, borders: noBorders(),
    rows: [new TableRow({ children: cells })] });
}

const doc = new Document({
  styles: { default: { document: { run: { font: FONT, size: 21, color: INK2 } } } },
  sections: [{
    properties: {
      page: { size: { width: 11906, height: 16838 }, margin: { top: 1250, bottom: 1100, left: 1500, right: 1500 } },
    },
    children: [
      // encabezado tipo correo
      P([T("RENADIA · RED NACIONAL DE ANALÍTICA DE DATOS E INTELIGENCIA ARTIFICIAL", { size: 15, bold: true, color: TEAL, characterSpacing: 20 })], { spacing: { after: 60 } }),
      P([T("Para: ", { size: 19, bold: true, color: INK }), T("Miembros de la comunidad RENADIA", { size: 19, color: INK2 })], { spacing: { after: 30 } }),
      P([T("Asunto: ", { size: 19, bold: true, color: INK }), T("Somos 1.000 — y los escuchamos: arrancan las Mesas Temáticas", { size: 19, color: INK2 })],
        { spacing: { after: 160 }, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: LINE, space: 6 } } }),

      // título
      P([
        T("Somos ", { size: 38, bold: true, color: INK }),
        T("1.000", { size: 38, bold: true, color: MAG }),
        T(" en la cancha de los datos. Gracias por jugar.", { size: 38, bold: true, color: INK }),
      ], { spacing: { after: 200 }, line: 280 }),

      body([
        T("Hola,", { size: 21, color: INK2 }),
      ], { spacing: { after: 120 } }),

      body([
        T("Esta semana la comunidad RENADIA llegó a ", { size: 21 }),
        T("1.000 miembros", { size: 21, bold: true, color: TEALDK }),
        T(": entidades nacionales y territoriales, empresas, universidades y personas que creen que los datos y la inteligencia artificial se aprovechan mejor jugando en equipo. Y lo celebramos como se debía: con el ", { size: 21 }),
        T("Mundial de los datos", { size: 21, bold: true, color: INK }),
        T(", nuestra convocatoria gamificada — carta de jugador, diagnóstico sectorial y tanda de penaltis contra los mitos de la IA.", { size: 21 }),
      ]),

      body([T("Tres cosas que nos dejó el partido:", { size: 21, bold: true, color: INK })], { spacing: { after: 110 } }),

      P([
        T("1. Nos pidieron mesas de trabajo, no más conferencias. ", { size: 21, bold: true, color: INK }),
        T("El 61% eligió las mesas temáticas como su forma preferida de sumar al equipo — el doble que los webinars. Y fue así en todos los públicos: entidades públicas, sector privado y academia.", { size: 21, color: INK2 }),
      ], { spacing: { after: 110, line: 280 }, indent: { left: 280 } }),
      P([
        T("2. La cancha es de todos. ", { size: 21, bold: true, color: INK }),
        T("Jugaron por igual entidades públicas y empresas privadas, con academia y territorio en la tribuna activa, y el diagnóstico abierto reunió voces de más de 12 sectores: salud, educación, TIC, financiero, seguridad, minero-energético y más.", { size: 21, color: INK2 }),
      ], { spacing: { after: 110, line: 280 }, indent: { left: 280 } }),
      P([
        T("3. Ya atajamos el mito más importante. ", { size: 21, bold: true, color: INK }),
        T("En los penaltis, la gran mayoría (84%) atajó el mito de que vincularse a RENADIA tiene costos u obligaciones. No los tiene: la membresía es voluntaria y gratuita — y seguirá siéndolo.", { size: 21, color: INK2 }),
      ], { spacing: { after: 190, line: 280 }, indent: { left: 280 } }),

      statBand([
        ["1.000", "miembros de la comunidad RENADIA", TEALDK],
        ["61%", "prefiere mesas temáticas de trabajo", TEAL],
        ["12+", "sectores en el diagnóstico abierto", "39415A"],
      ]),
      P([T("", { size: 4 })], { spacing: { after: 150 } }),

      body([
        T("Como los escuchamos, arrancamos con las Mesas Temáticas. ", { size: 21, bold: true, color: MAG }),
        T("Grupos pequeños de trabajo, con sesiones periódicas, alrededor de los temas que ustedes mismos pusieron sobre la mesa: gobernanza y calidad de datos, ética e IA, analítica territorial e interoperabilidad. De cada mesa saldrán aprendizajes documentados, casos de uso y bases para estándares compartidos — construidos entre pares, no dictados desde un atril.", { size: 21 }),
      ]),

      body([
        T("En los próximos días recibirán la convocatoria con los temas, el calendario y el formulario de inscripción. Los cupos por mesa son limitados para que la conversación sea de verdad de trabajo — si un tema es el suyo, no se queden en la banca.", { size: 21 }),
      ]),

      body([
        T("Gracias por hacer parte de esta selección. Lo que viene lo jugamos juntos.", { size: 21, color: INK }),
      ], { spacing: { after: 200 } }),

      P([T("Equipo RENADIA", { size: 21, bold: true, color: INK })], { spacing: { after: 20 } }),
      P([T("Unidad de Ciencia de Datos · Dirección de Desarrollo Digital", { size: 18, color: MUTE })], { spacing: { after: 20 } }),
      P([T("Departamento Nacional de Planeación", { size: 18, color: MUTE })], { spacing: { after: 140 } }),
      P([T("La vinculación a RENADIA es voluntaria y no genera obligaciones legales ni financieras para sus miembros (CONPES 4144).", { size: 14, italics: true, color: MUTE })],
        { spacing: { after: 0 }, border: { top: { style: BorderStyle.SINGLE, size: 6, color: LINE, space: 6 } } }),
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log("OK ->", OUT);
});
