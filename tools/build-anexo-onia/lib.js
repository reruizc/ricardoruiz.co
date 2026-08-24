// Chasis compartido para los anexos ONIA en formato de documento tecnico DENDD.
// Reglas tomadas de "Pautas para la elaboracion, revision y entrega de documentos
// tecnicos" (DENDD, v1): Arial 11 (size 22), interlineado 1,5 (line 360), texto
// alineado a la izquierda sin justificar, margenes 2,54 cm (1440 twips), tablas
// Arial 9-10, fuentes y notas Arial 9, numeracion multinivel hasta 3 niveles,
// paginado "Pagina X de Y" en el encabezado.

const fs = require('fs');
const d = require('docx');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, LevelFormat,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, Header, Footer,
  PageNumber, ImageRun, TableOfContents, SequentialIdentifier, PageOrientation,
} = d;

const ARIAL = 'Arial';
const HEADER_FILL = '000000';       // fondo de la fila de encabezado de las tablas
const ZEBRA = 'EBF3FB';
const PENDING = 'FFF2CC';           // filas plantilla por completar
const BORDER = { style: BorderStyle.SINGLE, size: 4, color: 'BFBFBF' };
const CELL_BORDERS = { top: BORDER, bottom: BORDER, left: BORDER, right: BORDER };
const CONTENT_W = 9360;             // vertical:  12240 - 1440*2
const CONTENT_W_LS = 12960;         // horizontal: 15840 - 1440*2

// Firmas institucionales (portada y pagina legal)
const REVISORES = ['Lorena Margarita Moreno Prieto', 'Edward Alexander Niño Virachaca'];
const APROBADOR = 'Edwin Alejandro Buenhombre Moreno';

// ---------- parrafos ----------
const p = (text, opts = {}) => new Paragraph({
  children: [new TextRun({ text, font: ARIAL, size: opts.size || 22, bold: opts.bold, italics: opts.italics, color: opts.color || '000000' })],
  alignment: opts.align || AlignmentType.LEFT,
  spacing: opts.spacing || { before: 0, after: 120, line: 360, lineRule: 'auto' },
  indent: opts.indent,
  pageBreakBefore: opts.pageBreakBefore,
  style: opts.style,
});

const rich = (runs, opts = {}) => new Paragraph({
  children: runs.map(r => typeof r === 'string'
    ? new TextRun({ text: r, font: ARIAL, size: opts.size || 22 })
    : new TextRun(Object.assign({ font: ARIAL, size: opts.size || 22 }, r))),
  alignment: opts.align || AlignmentType.LEFT,
  spacing: opts.spacing || { before: 0, after: 120, line: 360, lineRule: 'auto' },
  indent: opts.indent,
});

const blank = (n = 1) => Array.from({ length: n }, () => new Paragraph({
  children: [new TextRun({ text: '', font: ARIAL, size: 22 })],
  spacing: { before: 0, after: 0, line: 360, lineRule: 'auto' },
}));

// Titulo preliminar: centrado, estilo Titulo 1, sin numeracion, en hoja nueva
const prelim = (text, firstPage = false) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  alignment: AlignmentType.CENTER,
  pageBreakBefore: !firstPage,
  spacing: { before: 0, after: 360, line: 360, lineRule: 'auto' },
  children: [new TextRun({ text, font: ARIAL, size: 28, bold: true, color: '000000' })],
});

// Titulos numerados (numeracion multinivel automatica ligada a los estilos)
const h = (text, level, pageBreakBefore = false) => new Paragraph({
  heading: [HeadingLevel.HEADING_1, HeadingLevel.HEADING_2, HeadingLevel.HEADING_3][level - 1],
  numbering: { reference: 'titulos-dendd', level: level - 1 },
  pageBreakBefore,
  children: [new TextRun({ text, font: ARIAL, size: [28, 24, 22][level - 1], bold: true, color: '000000' })],
});

const bullet = (runs) => new Paragraph({
  children: (Array.isArray(runs) ? runs : [runs]).map(r => typeof r === 'string'
    ? new TextRun({ text: r, font: ARIAL, size: 22 })
    : new TextRun(Object.assign({ font: ARIAL, size: 22 }, r))),
  numbering: { reference: 'vinetas-dendd', level: 0 },
  alignment: AlignmentType.LEFT,
  spacing: { before: 0, after: 120, line: 360, lineRule: 'auto' },
});

// Titulo de tabla con campo SEQ automatico -> alimenta la "Lista de tablas"
const caption = (text) => new Paragraph({
  style: 'Caption',
  alignment: AlignmentType.LEFT,
  spacing: { before: 120, after: 60, line: 240, lineRule: 'auto' },
  keepNext: true,
  children: [
    new TextRun({ text: 'Tabla ', font: ARIAL, size: 20, bold: true }),
    new SequentialIdentifier('Tabla'),
    new TextRun({ text: `: ${text}`, font: ARIAL, size: 20, bold: true }),
  ],
});

const fuente = (text = 'Fuente: elaboración propia.') => new Paragraph({
  children: [new TextRun({ text, font: ARIAL, size: 18 })],
  spacing: { before: 60, after: 240, line: 240, lineRule: 'auto' },
});

const nota = (text) => new Paragraph({
  children: [new TextRun({ text, font: ARIAL, size: 18 })],
  spacing: { before: 60, after: 240, line: 240, lineRule: 'auto' },
});

const ref = (runs) => new Paragraph({
  style: 'Referencia',
  children: runs.map(r => typeof r === 'string'
    ? new TextRun({ text: r, font: ARIAL, size: 22 })
    : new TextRun(Object.assign({ font: ARIAL, size: 22 }, r))),
});

// ---------- tablas ----------
const cell = (text, { width, header = false, bold = false, fill, size = 20, align = AlignmentType.LEFT, pad = 100 }) =>
  new TableCell({
    width: { size: width, type: WidthType.DXA },
    borders: CELL_BORDERS,
    shading: { type: ShadingType.CLEAR, color: 'auto', fill: fill || 'FFFFFF' },
    margins: { top: 60, bottom: 60, left: pad, right: pad },
    verticalAlign: 'center',
    children: [new Paragraph({
      alignment: align,
      spacing: { before: 20, after: 20, line: 240, lineRule: 'auto' },
      children: [new TextRun({ text, font: ARIAL, size, bold: header || bold, color: header ? 'FFFFFF' : '000000' })],
    })],
  });

// rows: matriz de strings. opts.pendingRows: indices (base 0, incluyendo el
// encabezado) que se sombrean como plantilla por completar.
const buildTable = (widths, rows, size = 20, pad = 100, opts = {}) => {
  const pending = new Set(opts.pendingRows || []);
  return new Table({
    columnWidths: widths,
    width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
    rows: rows.map((cells, ri) => new TableRow({
      tableHeader: ri === 0,
      cantSplit: true,
      children: cells.map((txt, ci) => cell(txt, {
        width: widths[ci],
        header: ri === 0,
        bold: ri > 0 && ci === 0,
        fill: ri === 0 ? HEADER_FILL : (pending.has(ri) ? PENDING : (ri % 2 === 0 ? ZEBRA : 'FFFFFF')),
        size, pad,
        align: ri === 0 ? AlignmentType.CENTER : AlignmentType.LEFT,
      })),
    })),
  });
};

// ---------- encabezado ----------
const logo = fs.readFileSync(__dirname + '/assets/logo_header.png');
const logoPortada = fs.readFileSync(__dirname + '/assets/logo_portada.png');

const makeHeaderTable = (contentW) => {
  const col = Math.round(contentW / 3);
  const none = { style: BorderStyle.NONE };
  return new Table({
    columnWidths: [col, col, col],
    width: { size: contentW, type: WidthType.DXA },
    borders: { top: none, bottom: none, left: none, right: none, insideHorizontal: none, insideVertical: none },
    rows: [new TableRow({
      children: [
        new TableCell({
          width: { size: col, type: WidthType.DXA }, margins: { left: 0, right: 0 },
          children: [new Paragraph({ children: [new TextRun({ text: '', font: ARIAL, size: 18 })], spacing: { after: 0 } })],
        }),
        new TableCell({
          width: { size: col, type: WidthType.DXA }, margins: { left: 0, right: 0 },
          children: [new Paragraph({
            alignment: AlignmentType.CENTER, spacing: { after: 0 },
            children: [new ImageRun({ type: 'png', data: logo, transformation: { width: 92, height: 44 } })],
          })],
        }),
        new TableCell({
          width: { size: col, type: WidthType.DXA }, margins: { left: 0, right: 0 },
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT, spacing: { after: 0 },
            children: [new TextRun({
              children: ['Página ', PageNumber.CURRENT, ' de ', PageNumber.TOTAL_PAGES],
              font: ARIAL, size: 18,
            })],
          })],
        }),
      ],
    })],
  });
};

const headerFor = (contentW) => new Header({
  children: [makeHeaderTable(contentW), new Paragraph({ children: [new TextRun({ text: '', font: ARIAL, size: 8 })], spacing: { after: 0 } })],
});
const emptyHF = (C) => new C({ children: [new Paragraph({ children: [new TextRun({ text: '', font: ARIAL, size: 18 })] })] });

// ---------- preliminares ----------
function portada({ titulo, subtitulo, version = '1', anio = '2026' }) {
  const line = (t, o) => p(t, Object.assign({ align: AlignmentType.CENTER }, o));

  // La portada debe caber en una sola hoja. Con un titulo de dos lineas y un
  // subtitulo de dos lineas los espacios en blanco de referencia (1/2/2/2) la
  // llenan justo; por cada linea adicional se recortan lineas en blanco, en
  // orden: cabecera, espacio bajo el logo, espacio final, espacio intermedio.
  const estLines = (t, cpl) => Math.max(1, Math.ceil((t || '').length / cpl));
  let extra = 2 * Math.max(0, estLines(titulo, 46) - 2)      // titulo: Arial 18 negrita
            + 1 * Math.max(0, estLines(subtitulo, 70) - 2)   // subtitulo: Arial 13
            + (REVISORES.length - 1);                        // firmas de revision adicionales
  const gaps = { lead: 1, g1: 2, g3: 2, g2: 2 };
  const floors = { lead: 0, g1: 0, g3: 1, g2: 1 };
  for (const k of ['lead', 'g1', 'g3', 'g2']) {
    const take = Math.min(extra, gaps[k] - floors[k]);
    gaps[k] -= take; extra -= take;
    if (extra <= 0) break;
  }

  return [
    ...blank(gaps.lead),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { after: 360 },
      children: [new ImageRun({ type: 'png', data: logoPortada, transformation: { width: 196, height: 90 } })],
    }),
    ...blank(gaps.g1),
    line(titulo, { size: 36, bold: true, spacing: { before: 0, after: 240, line: 360, lineRule: 'auto' } }),
    line(subtitulo, { size: 26, spacing: { before: 0, after: 120, line: 360, lineRule: 'auto' } }),
    line('Dirección de Economía Naranja y Desarrollo Digital', { size: 26, spacing: { before: 0, after: 60, line: 360, lineRule: 'auto' } }),
    line(`Versión ${version}`, { size: 22, spacing: { before: 0, after: 0, line: 360, lineRule: 'auto' } }),
    ...blank(gaps.g2),
    p('Elaborado por:', { size: 22, indent: { left: 4680 }, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } }),
    p('Ricardo Esteban Ruiz Castro', { size: 22, indent: { left: 5040 }, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } }),
    p('Contratista, Tanque de Pensamiento de Desarrollo Digital', { size: 18, indent: { left: 5040 }, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } }),
    ...blank(1),
    p('Revisado por:', { size: 22, indent: { left: 4680 }, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } }),
    ...REVISORES.map(n => p(n, { size: 22, indent: { left: 5040 }, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } })),
    p('Dirección de Economía Naranja y Desarrollo Digital', { size: 18, indent: { left: 5040 }, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } }),
    ...blank(1),
    p('Aprobado por:', { size: 22, indent: { left: 4680 }, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } }),
    p(APROBADOR, { size: 22, indent: { left: 5040 }, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } }),
    p('Director Técnico', { size: 18, indent: { left: 5040 }, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } }),
    ...blank(gaps.g3),
    line('Departamento Nacional de Planeación', { size: 24, bold: true, spacing: { before: 0, after: 60, line: 300, lineRule: 'auto' } }),
    line('Bogotá, D.C.', { size: 22, spacing: { before: 0, after: 60, line: 300, lineRule: 'auto' } }),
    line(anio, { size: 22, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } }),
  ];
}

function paginaLegal({ cambio, anio = '2026', mes = 'Junio de 2026' }) {
  return [
    prelim('Página legal y control documental'),
    buildTable([2800, 6560], [
      ['Elemento', 'Detalle'],
      ['Código', '[Por asignar por el Sistema de Gestión Institucional]'],
      ['Versión', '1'],
      ['Fecha de aprobación', '[Por definir]'],
      ['Dependencia responsable', 'Dirección de Economía Naranja y Desarrollo Digital (DENDD)'],
      ['Elaboró', 'Ricardo Esteban Ruiz Castro — contratista, Tanque de Pensamiento de Desarrollo Digital (DENDD)'],
      ['Revisó', `${REVISORES.join(' y ')} — Dirección de Economía Naranja y Desarrollo Digital`],
      ['Aprobó', `${APROBADOR} — Director Técnico`],
    ]),
    ...blank(1),
    p('Historial de cambios', { size: 24, bold: true, align: AlignmentType.CENTER, spacing: { before: 240, after: 120, line: 360, lineRule: 'auto' } }),
    buildTable([1400, 5960, 2000], [
      ['Versión', 'Descripción del cambio', 'Fecha'],
      ['1', cambio, mes],
    ]),
    ...blank(2),
    p(`© Departamento Nacional de Planeación, ${anio}`, { size: 20, align: AlignmentType.CENTER, spacing: { before: 240, after: 60, line: 300, lineRule: 'auto' } }),
    p('Se permite la reproducción con reconocimiento de la fuente.', { size: 20, align: AlignmentType.CENTER, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } }),
  ];
}

function preliminares(opts) {
  return [
    ...portada(opts),
    ...paginaLegal(opts),
    prelim('Tabla de contenido'),
    new TableOfContents('Tabla de contenido', { hyperlink: true, headingStyleRange: '1-3' }),
    prelim('Lista de tablas'),
    new TableOfContents('Lista de tablas', { hyperlink: true, captionLabel: 'Tabla' }),
    prelim('Siglas y abreviaturas'),
    buildTable([2200, 7160], [['Sigla', 'Significado'], ...opts.siglas]),
    prelim('Presentación'),
    ...opts.presentacion.map(t => p(t)),
  ];
}

// ---------- documento ----------
// blocks: [{ landscape?:bool, children:[...] }]. Los preliminares se anteponen
// al primer bloque, que siempre es vertical.
function buildDoc({ titulo, subtitulo, descripcion, siglas, presentacion, cambio, blocks }) {
  const sections = blocks.map((b, i) => {
    const ls = !!b.landscape;
    const cw = ls ? CONTENT_W_LS : CONTENT_W;
    return {
      properties: {
        titlePage: i === 0,
        page: {
          // docx intercambia ancho y alto cuando la orientacion es horizontal:
          // siempre se pasan las medidas en vertical (carta 21,59 x 27,94 cm).
          size: {
            width: 12240, height: 15840,
            orientation: ls ? PageOrientation.LANDSCAPE : PageOrientation.PORTRAIT,
          },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440, header: 709, footer: 709 },
        },
      },
      headers: i === 0
        ? { first: emptyHF(Header), default: headerFor(cw) }
        : { default: headerFor(cw) },
      footers: i === 0
        ? { first: emptyHF(Footer), default: emptyHF(Footer) }
        : { default: emptyHF(Footer) },
      children: i === 0
        ? [...preliminares({ titulo, subtitulo, siglas, presentacion, cambio }), ...b.children]
        : b.children,
    };
  });

  return new Document({
    creator: 'Departamento Nacional de Planeación',
    title: titulo,
    description: descripcion,
    styles: {
      default: {
        document: {
          run: { font: ARIAL, size: 22, color: '000000' },
          paragraph: { spacing: { before: 0, after: 120, line: 360, lineRule: 'auto' }, alignment: AlignmentType.LEFT },
        },
        heading1: {
          run: { font: ARIAL, size: 28, bold: true, color: '000000' },
          paragraph: { spacing: { before: 360, after: 180, line: 360, lineRule: 'auto' }, keepNext: true, alignment: AlignmentType.LEFT },
        },
        heading2: {
          run: { font: ARIAL, size: 24, bold: true, color: '000000' },
          paragraph: { spacing: { before: 280, after: 140, line: 360, lineRule: 'auto' }, keepNext: true, alignment: AlignmentType.LEFT },
        },
        heading3: {
          run: { font: ARIAL, size: 22, bold: true, color: '000000' },
          paragraph: { spacing: { before: 240, after: 120, line: 360, lineRule: 'auto' }, keepNext: true, alignment: AlignmentType.LEFT },
        },
      },
      paragraphStyles: [
        {
          id: 'Caption', name: 'Caption', basedOn: 'Normal', next: 'Normal', quickFormat: true,
          run: { font: ARIAL, size: 20, bold: true, color: '000000' },
          paragraph: { spacing: { before: 120, after: 60, line: 240, lineRule: 'auto' }, keepNext: true },
        },
        {
          id: 'Referencia', name: 'Referencia', basedOn: 'Normal', next: 'Referencia',
          run: { font: ARIAL, size: 22 },
          paragraph: { spacing: { before: 0, after: 120, line: 360, lineRule: 'auto' }, indent: { left: 720, hanging: 720 } },
        },
      ],
    },
    numbering: {
      config: [
        {
          reference: 'titulos-dendd',
          levels: [
            { level: 0, format: LevelFormat.DECIMAL, text: '%1', alignment: AlignmentType.LEFT,
              style: { paragraph: { indent: { left: 432, hanging: 432 } } } },
            { level: 1, format: LevelFormat.DECIMAL, text: '%1.%2', alignment: AlignmentType.LEFT,
              style: { paragraph: { indent: { left: 576, hanging: 576 } } } },
            { level: 2, format: LevelFormat.DECIMAL, text: '%1.%2.%3', alignment: AlignmentType.LEFT,
              style: { paragraph: { indent: { left: 720, hanging: 720 } } } },
          ],
        },
        {
          reference: 'vinetas-dendd',
          levels: [
            { level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
              style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
          ],
        },
      ],
    },
    features: { updateFields: true },
    sections,
  });
}

function save(doc, outPath) {
  return Packer.toBuffer(doc).then(buf => {
    fs.writeFileSync(outPath, buf);
    console.log('OK', outPath.split('/').pop(), (buf.length / 1024).toFixed(1) + ' KB');
  });
}

module.exports = {
  ARIAL, AlignmentType, CONTENT_W, CONTENT_W_LS,
  p, rich, blank, prelim, h, bullet, caption, fuente, nota, ref,
  buildTable, buildDoc, save,
};
