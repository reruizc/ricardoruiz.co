const fs = require('fs');
const d = require('docx');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, LevelFormat,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, Header, Footer,
  PageNumber, ImageRun, TableOfContents, SequentialIdentifier, PageBreak, convertInchesToTwip
} = d;

const ARIAL = 'Arial';
const NAVY = '1F4E79';
const ZEBRA = 'EBF3FB';
const BORDER = { style: BorderStyle.SINGLE, size: 4, color: 'BFBFBF' };
const CELL_BORDERS = { top: BORDER, bottom: BORDER, left: BORDER, right: BORDER };
const CONTENT_W = 9360; // 12240 - 1440*2

// ---------- helpers ----------
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

// Preliminary title: centered, Heading 1 style, no numbering, new page
const prelim = (text, firstPage = false) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  alignment: AlignmentType.CENTER,
  pageBreakBefore: !firstPage,
  spacing: { before: 0, after: 360, line: 360, lineRule: 'auto' },
  children: [new TextRun({ text, font: ARIAL, size: 28, bold: true, color: '000000' })],
});

// Numbered chapter titles (automatic multilevel numbering bound to heading styles)
const h = (text, level, pageBreakBefore = false) => new Paragraph({
  heading: [HeadingLevel.HEADING_1, HeadingLevel.HEADING_2, HeadingLevel.HEADING_3][level - 1],
  numbering: { reference: 'titulos-dendd', level: level - 1 },
  pageBreakBefore,
  children: [new TextRun({ text, font: ARIAL, size: [28, 24, 22][level - 1], bold: true, color: '000000' })],
});

// Bulleted item
const bullet = (runs) => new Paragraph({
  children: (Array.isArray(runs) ? runs : [runs]).map(r => typeof r === 'string'
    ? new TextRun({ text: r, font: ARIAL, size: 22 })
    : new TextRun(Object.assign({ font: ARIAL, size: 22 }, r))),
  numbering: { reference: 'vinetas-dendd', level: 0 },
  alignment: AlignmentType.LEFT,
  spacing: { before: 0, after: 120, line: 360, lineRule: 'auto' },
});

// Table caption with automatic SEQ field -> feeds the automatic "Lista de tablas"
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

// Table cell
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

const buildTable = (widths, rows, size = 20, pad = 100) => new Table({
  columnWidths: widths,
  width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
  rows: rows.map((cells, ri) => new TableRow({
    tableHeader: ri === 0,
    cantSplit: true,
    children: cells.map((txt, ci) => cell(txt, {
      width: widths[ci],
      header: ri === 0,
      bold: ri > 0 && ci === 0,
      fill: ri === 0 ? NAVY : (ri % 2 === 0 ? ZEBRA : 'FFFFFF'),
      size, pad,
      align: ri === 0 ? AlignmentType.CENTER : AlignmentType.LEFT,
    })),
  })),
});

// ---------- header / footer ----------
const logo = fs.readFileSync(__dirname + '/logo_header.png');
const logoPortada = fs.readFileSync(__dirname + '/logo_portada.png');

const headerTable = new Table({
  columnWidths: [3120, 3120, 3120],
  width: { size: CONTENT_W, type: WidthType.DXA },
  borders: {
    top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE },
    left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE },
    insideHorizontal: { style: BorderStyle.NONE }, insideVertical: { style: BorderStyle.NONE },
  },
  rows: [new TableRow({
    children: [
      new TableCell({
        width: { size: 3120, type: WidthType.DXA }, margins: { left: 0, right: 0 },
        children: [new Paragraph({ children: [new TextRun({ text: '', font: ARIAL, size: 18 })], spacing: { after: 0 } })],
      }),
      new TableCell({
        width: { size: 3120, type: WidthType.DXA }, margins: { left: 0, right: 0 },
        children: [new Paragraph({
          alignment: AlignmentType.CENTER, spacing: { after: 0 },
          children: [new ImageRun({ type: 'png', data: logo, transformation: { width: 92, height: 44 } })],
        })],
      }),
      new TableCell({
        width: { size: 3120, type: WidthType.DXA }, margins: { left: 0, right: 0 },
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

// ---------- document ----------
const doc = new Document({
  creator: 'Departamento Nacional de Planeación',
  title: 'Anexo 3. Apartados para el documento técnico del Observatorio Nacional de Inteligencia Artificial (ONIA)',
  description: 'Ajustes en respuesta al memorando OAP No. 20266900157443 del 1 de junio de 2026',
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
        paragraph: {
          spacing: { before: 0, after: 120, line: 360, lineRule: 'auto' },
          indent: { left: 720, hanging: 720 },
        },
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
  sections: [{
    properties: {
      titlePage: true,
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440, header: 709, footer: 709 },
      },
    },
    headers: {
      first: new Header({ children: [new Paragraph({ children: [new TextRun({ text: '', font: ARIAL, size: 18 })] })] }),
      default: new Header({ children: [headerTable, new Paragraph({ children: [new TextRun({ text: '', font: ARIAL, size: 8 })], spacing: { after: 0 } })] }),
    },
    footers: {
      first: new Footer({ children: [new Paragraph({ children: [new TextRun({ text: '', font: ARIAL, size: 18 })] })] }),
      default: new Footer({ children: [new Paragraph({ children: [new TextRun({ text: '', font: ARIAL, size: 18 })] })] }),
    },
    children: [
      // ============ PORTADA ============
      ...blank(1),
      new Paragraph({
        alignment: AlignmentType.CENTER, spacing: { after: 360 },
        children: [new ImageRun({ type: 'png', data: logoPortada, transformation: { width: 196, height: 90 } })],
      }),
      ...blank(2),
      p('Anexo 3. Apartados para el documento técnico del Observatorio Nacional de Inteligencia Artificial (ONIA)',
        { size: 36, bold: true, align: AlignmentType.CENTER, spacing: { before: 0, after: 240, line: 360, lineRule: 'auto' } }),
      p('Ajustes en respuesta al memorando OAP No. 20266900157443 del 1 de junio de 2026',
        { size: 26, align: AlignmentType.CENTER, spacing: { before: 0, after: 120, line: 360, lineRule: 'auto' } }),
      p('Dirección de Economía Naranja y Desarrollo Digital', { size: 26, align: AlignmentType.CENTER, spacing: { before: 0, after: 60, line: 360, lineRule: 'auto' } }),
      p('Versión 1', { size: 22, align: AlignmentType.CENTER, spacing: { before: 0, after: 0, line: 360, lineRule: 'auto' } }),
      ...blank(2),
      p('Elaborado por:', { size: 22, indent: { left: 4680 }, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } }),
      p('Ricardo Esteban Ruiz Castro', { size: 22, indent: { left: 5040 }, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } }),
      p('Contratista, Tanque de Pensamiento de Desarrollo Digital', { size: 18, indent: { left: 5040 }, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } }),
      ...blank(1),
      p('Revisado por:', { size: 22, indent: { left: 4680 }, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } }),
      p('[Por designar]', { size: 22, indent: { left: 5040 }, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } }),
      p('Dirección de Economía Naranja y Desarrollo Digital', { size: 18, indent: { left: 5040 }, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } }),
      ...blank(1),
      p('Aprobado por:', { size: 22, indent: { left: 4680 }, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } }),
      p('[Por designar]', { size: 22, indent: { left: 5040 }, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } }),
      p('Director Técnico', { size: 18, indent: { left: 5040 }, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } }),
      ...blank(2),
      p('Departamento Nacional de Planeación', { size: 24, bold: true, align: AlignmentType.CENTER, spacing: { before: 0, after: 60, line: 300, lineRule: 'auto' } }),
      p('Bogotá, D.C.', { size: 22, align: AlignmentType.CENTER, spacing: { before: 0, after: 60, line: 300, lineRule: 'auto' } }),
      p('2026', { size: 22, align: AlignmentType.CENTER, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } }),

      // ============ PÁGINA LEGAL Y CONTROL DOCUMENTAL ============
      prelim('Página legal y control documental'),
      buildTable([2800, 6560], [
        ['Elemento', 'Detalle'],
        ['Código', '[Por asignar por el Sistema de Gestión Institucional]'],
        ['Versión', '1'],
        ['Fecha de aprobación', '[Por definir]'],
        ['Dependencia responsable', 'Dirección de Economía Naranja y Desarrollo Digital (DENDD)'],
        ['Elaboró', 'Ricardo Esteban Ruiz Castro — contratista, Tanque de Pensamiento de Desarrollo Digital (DENDD)'],
        ['Revisó', '[Por designar]'],
        ['Aprobó', 'Dirección de Economía Naranja y Desarrollo Digital'],
      ]),
      ...blank(1),
      p('Historial de cambios', { size: 24, bold: true, align: AlignmentType.CENTER, spacing: { before: 240, after: 120, line: 360, lineRule: 'auto' } }),
      buildTable([1400, 5960, 2000], [
        ['Versión', 'Descripción del cambio', 'Fecha'],
        ['1', 'Emisión inicial. Consolidación de los apartados que responden a las observaciones 2, 3 y 5 del memorando OAP No. 20266900157443.', 'Junio de 2026'],
      ]),
      ...blank(2),
      p('© Departamento Nacional de Planeación, 2026', { size: 20, align: AlignmentType.CENTER, spacing: { before: 240, after: 60, line: 300, lineRule: 'auto' } }),
      p('Se permite la reproducción con reconocimiento de la fuente.', { size: 20, align: AlignmentType.CENTER, spacing: { before: 0, after: 0, line: 300, lineRule: 'auto' } }),

      // ============ TABLA DE CONTENIDO ============
      prelim('Tabla de contenido'),
      new TableOfContents('Tabla de contenido', { hyperlink: true, headingStyleRange: '1-3' }),

      // ============ LISTA DE TABLAS ============
      prelim('Lista de tablas'),
      new TableOfContents('Lista de tablas', { hyperlink: true, captionLabel: 'Tabla' }),

      // ============ SIGLAS Y ABREVIATURAS ============
      prelim('Siglas y abreviaturas'),
      buildTable([2200, 7160], [
        ['Sigla', 'Significado'],
        ['BID', 'Banco Interamericano de Desarrollo'],
        ['CEPAL', 'Comisión Económica para América Latina y el Caribe'],
        ['CIGD', 'Comité Institucional de Gestión y Desempeño'],
        ['DAPRE', 'Departamento Administrativo de la Presidencia de la República'],
        ['DENDD', 'Dirección de Economía Naranja y Desarrollo Digital'],
        ['DNP', 'Departamento Nacional de Planeación'],
        ['FURAG', 'Formulario Único de Reporte de Avances de la Gestión'],
        ['HAI', 'Institute for Human-Centered Artificial Intelligence (Universidad de Stanford)'],
        ['IA', 'Inteligencia artificial'],
        ['MinTIC', 'Ministerio de Tecnologías de la Información y las Comunicaciones'],
        ['OAP', 'Oficina Asesora de Planeación'],
        ['OCDE', 'Organización para la Cooperación y el Desarrollo Económicos'],
        ['ONIA', 'Observatorio Nacional de Inteligencia Artificial'],
        ['RENADIA', 'Red Nacional de Analítica de Datos e Inteligencia Artificial'],
        ['SIGEP', 'Sistema de Información y Gestión del Empleo Público'],
        ['UNESCO', 'Organización de las Naciones Unidas para la Educación, la Ciencia y la Cultura'],
      ]),

      // ============ PRESENTACIÓN ============
      prelim('Presentación'),
      p('El Departamento Nacional de Planeación (DNP), a través de la Dirección de Economía Naranja y Desarrollo Digital (DENDD), adelanta la estructuración del Observatorio Nacional de Inteligencia Artificial (ONIA) como instrumento de conocimiento para la observación, el monitoreo y el análisis de la inteligencia artificial (IA) en Colombia y de su gobernanza.'),
      p('En el marco de ese proceso, la Oficina Asesora de Planeación (OAP) formuló observaciones al documento técnico del observatorio mediante el memorando No. 20266900157443 del 1 de junio de 2026. El presente anexo consolida los apartados que se integrarán a la versión ajustada de dicho documento técnico, en atención a las observaciones 2, 3 y 5 del citado memorando.'),
      p('Estos apartados desarrollan, con mayor detalle, lo expuesto de manera resumida en la respuesta al oficio. El documento se dirige a la Oficina Asesora de Planeación, a la Dirección de Economía Naranja y Desarrollo Digital y a las instancias que participan en la revisión y en la aprobación del observatorio. Su resultado esperado es que el documento técnico del ONIA cuente con la precisión requerida sobre su diferenciación institucional, su alcance funcional, sus fuentes de información y sus condiciones de sostenibilidad, con miras a su presentación ante el Comité Institucional de Gestión y Desempeño (CIGD).'),

      // ============ 1. INTRODUCCIÓN ============
      h('Introducción', 1, true),
      p('El documento técnico del Observatorio Nacional de Inteligencia Artificial sustenta la creación del observatorio y su presentación ante el Comité Institucional de Gestión y Desempeño. En la revisión de ese documento, la Oficina Asesora de Planeación formuló observaciones orientadas a precisar tres asuntos: la diferenciación del ONIA frente a los observatorios existentes en la entidad (observación 2), la delimitación de su alcance funcional frente a las demás iniciativas de la DENDD (observación 3) y la caracterización de sus fuentes de información, así como de las condiciones de sostenibilidad de la iniciativa (observación 5).'),
      p('El problema que atiende este anexo es de naturaleza técnica y documental. La versión previa del documento técnico expone de manera resumida esos tres asuntos, lo que dificulta valorar la pertinencia institucional del observatorio, su no duplicidad con otras instancias de la entidad y su viabilidad en el tiempo. La respuesta al oficio se elaboró en un formato breve, por lo que se requiere un desarrollo más detallado que pueda incorporarse directamente al cuerpo del documento técnico.'),
      p('En consecuencia, el propósito de este anexo es desarrollar los apartados que responden a las observaciones 2, 3 y 5, en un nivel de detalle suficiente para su integración en la versión ajustada del documento técnico del ONIA. Sus objetivos específicos son: precisar la diferenciación del observatorio frente a las iniciativas existentes; delimitar su alcance funcional dentro de la arquitectura institucional de la DENDD; presentar el mapa preliminar de fuentes de información con los atributos solicitados; describir el portafolio mínimo de productos; y exponer el análisis preliminar de sostenibilidad.'),
      p('El alcance se limita a los apartados señalados. No se abordan aquí los demás componentes del documento técnico del observatorio —entre ellos el marco conceptual, la justificación normativa y las fichas técnicas de indicadores—, que se mantienen conforme a su versión vigente. Los apartados se elaboran a partir de la revisión de los documentos institucionales del observatorio y de las iniciativas de la DENDD, del mapeo de los observatorios existentes en la entidad, y de la identificación y caracterización de fuentes de información según los atributos solicitados por la OAP. El mapa de fuentes opera bajo el procedimiento institucional PT-GI-05 y se articula con el Plan de Captura y Generación de Información del observatorio.'),
      p('El documento se organiza en ocho capítulos. Tras esta introducción, el capítulo 2 presenta la diferenciación frente a observatorios existentes; el capítulo 3, el alcance funcional y la arquitectura institucional; el capítulo 4, el mapa de fuentes de información y sus criterios de priorización; el capítulo 5, el portafolio mínimo de productos; el capítulo 6, el análisis de sostenibilidad; el capítulo 7 recoge las conclusiones y el capítulo 8 relaciona las referencias consultadas.'),

      // ============ 2. DIFERENCIACIÓN ============
      h('Diferenciación frente a observatorios existentes', 1),
      p('En atención a la observación No. 2, se incorpora el Observatorio de Participación Ciudadana —cuya viabilidad fue aprobada por el CIGD— al mapeo de iniciativas existentes, y se precisa su diferenciación frente al ONIA. Ambos observatorios tienen objetos de estudio distintos y complementarios, sin superposición funcional, como se resume en la Tabla 1.'),
      caption('Diferenciación entre el Observatorio de Participación Ciudadana y el ONIA'),
      buildTable([1900, 3730, 3730], [
        ['Criterio', 'Observatorio de Participación Ciudadana', 'Observatorio Nacional de Inteligencia Artificial (ONIA)'],
        ['Objeto de análisis', 'La participación ciudadana como derecho, proceso e interacción social.', 'La inteligencia artificial en Colombia y su gobernanza.'],
        ['Fenómeno público observado', 'Dinámicas de la participación ciudadana, planeación participativa y control social.', 'Adopción, impacto y regulación de la IA en los sectores público y privado y en el territorio.'],
        ['Dimensiones o líneas', 'Condiciones institucionales de la participación, prácticas ciudadanas, control social, percepción y legitimidad institucional.', 'Vigilancia tecnológica; prospectiva; ética y regulación; adopción sectorial y territorial; articulación con RENADIA.'],
        ['Productos propios', 'Información, datos e indicadores sobre participación ciudadana.', 'Informe anual (producto faro), informes trimestrales con alertas, capacitaciones, repositorio y tableros.'],
        ['Estado institucional', 'Viabilidad aprobada por el CIGD.', 'En proceso de estructuración para presentación ante el CIGD.'],
      ]),
      fuente(),
      p('Esta diferenciación evita duplicidades y clarifica la oferta institucional de observatorios del DNP: el Observatorio de Participación Ciudadana se ocupa de la participación como fenómeno social, mientras que el ONIA se ocupa de la inteligencia artificial y de su gobernanza como objeto de política pública.'),

      // ============ 3. ALCANCE FUNCIONAL ============
      h('Alcance funcional y arquitectura institucional', 1),
      p('En atención a la observación No. 3, se delimita el alcance funcional del observatorio y se aclara su relación con las demás iniciativas de la DENDD. El observatorio asume únicamente funciones de observación, monitoreo, análisis, prospectiva, divulgación y apropiación. Las funciones de producción de conocimiento de mayor alcance, de articulación y de asistencia técnica corresponden a otras instancias, conforme a la arquitectura que presenta la Tabla 2.'),
      caption('Arquitectura institucional y distribución de funciones'),
      buildTable([2600, 4360, 2400], [
        ['Instancia', 'Rol', 'Naturaleza'],
        ['Observatorio Nacional de Inteligencia Artificial (ONIA)', 'Observación, monitoreo, análisis, prospectiva y vigilancia tecnológica de la gobernanza de la IA; divulgación y apropiación.', 'Instrumento de conocimiento (función propia)'],
        ['Tanque de Pensamiento de Desarrollo Digital', 'Producción de conocimiento estratégico de mayor alcance y orientación de la agenda de desarrollo digital.', 'Instancia de pensamiento estratégico'],
        ['RENADIA', 'Articulación interinstitucional, comunidad de práctica y colaboración en analítica e IA.', 'Mecanismo de articulación (red)'],
        ['Entidades competentes (MinTIC, DAPRE, otras)', 'Asistencia técnica, producción normativa y demás funciones de su competencia.', 'Funciones no propias del observatorio'],
      ]),
      fuente(),
      p('De esta manera, el observatorio no asume funciones de tanque de pensamiento, de red de actores, de asistencia técnica ni de producción normativa. Estas se canalizan a través del Tanque de Pensamiento de Desarrollo Digital, de RENADIA o de las entidades competentes, según corresponda.'),

      // ============ 4. MAPA DE FUENTES ============
      h('Mapa de fuentes de información', 1),
      p('En atención a la observación No. 5, se presenta el mapa preliminar de fuentes de información del observatorio, que precisa para cada fuente los seis atributos solicitados por la OAP. El mapa opera bajo el procedimiento institucional PT-GI-05 y se articula con el Plan de Captura y Generación de Información del observatorio.'),
      h('Fuentes identificadas', 2),
      p('La Tabla 3 relaciona las ocho fuentes identificadas en esta fase, con su tipo, disponibilidad, periodicidad de actualización, grado de interoperabilidad, responsable y prioridad.'),
      caption('Mapa preliminar de fuentes de información'),
      buildTable([1400, 1080, 1460, 1360, 1700, 1260, 1100], [
        ['Fuente', 'Tipo', 'Disponibilidad', 'Periodicidad', 'Interoperabilidad', 'Responsable', 'Prioridad'],
        ['FURAG', 'Secundaria', 'Pública', 'Anual', 'Media', 'DENDD', 'Alta'],
        ['SIGEP', 'Secundaria', 'Pública', 'Continua', 'Media', 'DENDD', 'Media'],
        ['OCDE.AI Policy Observatory', 'Secundaria', 'Abierta', 'Continua', 'Alta', 'DENDD', 'Alta'],
        ['AI Index (Stanford HAI)', 'Secundaria', 'Abierta', 'Anual', 'Alta', 'DENDD', 'Alta'],
        ['GovTech Maturity Index (Banco Mundial)', 'Secundaria', 'Abierta', 'Bienal', 'Media', 'DENDD', 'Media'],
        ['datos.gov.co', 'Secundaria', 'Abierta', 'Variable', 'Alta', 'DENDD', 'Media'],
        ['Banco de Fuentes Primarias DNP (F-GI-01)', 'Primaria', 'Interna', 'Continua', 'Alta', 'DENDD', 'Alta'],
        ['Encuestas a entidades y RENADIA', 'Primaria', 'Generada', 'Trimestral', 'Alta', 'DENDD y RENADIA', 'Alta'],
      ], 18, 60),
      fuente(),
      h('Criterios de priorización', 2),
      p('Las fuentes se priorizan según su pertinencia para las líneas de análisis del observatorio, su disponibilidad y oportunidad, su grado de interoperabilidad y la confiabilidad institucional del responsable de su actualización.'),

      // ============ 5. PORTAFOLIO ============
      h('Portafolio mínimo de productos', 1),
      p('El observatorio organiza sus productos en cinco categorías, articuladas con las fichas técnicas de indicadores de impacto, como se detalla en la Tabla 4.'),
      caption('Portafolio mínimo de productos del observatorio'),
      buildTable([1700, 5060, 2600], [
        ['Categoría', 'Producto', 'Periodicidad'],
        ['Monitoreo', 'Tableros y repositorio de fuentes especializadas.', 'Actualización continua'],
        ['Análisis', 'Informe Anual sobre Gobernanza de la IA en Colombia (producto faro).', 'Anual'],
        ['Prospectiva', 'Informes con alertas tempranas y señales débiles.', 'Cuatro informes trimestrales'],
        ['Divulgación', 'Boletines, infografías y microcontenidos dirigidos a decisores, técnicos, academia y ciudadanía.', 'Continua'],
        ['Apropiación', 'Capacitaciones a actores habilitantes, en conjunto con RENADIA.', 'Cuatro capacitaciones anuales'],
      ]),
      fuente(),

      // ============ 6. SOSTENIBILIDAD ============
      h('Análisis de sostenibilidad', 1),
      p('En atención a la observación No. 5, se incorpora un análisis preliminar de la sostenibilidad técnica, operativa y financiera del observatorio.'),
      h('Sostenibilidad técnica', 2),
      p('El observatorio se apoya en la infraestructura de difusión institucional —página web, repositorios y tableros— y en el uso de herramientas de analítica (Python, QGIS y MicMac), así como de software libre y licenciado. Su operación aplica estándares de interoperabilidad y de protección de datos personales, conforme a la Ley 1581 de 2012.'),
      h('Sostenibilidad operativa', 2),
      p('La operación se sustenta en el talento humano especializado de la DENDD para la captura, la consolidación y el procesamiento de la información; en la articulación con los nodos de RENADIA para la validación y la coproducción; y en la aplicación del procedimiento PT-GI-05 para el mantenimiento y la actualización de contenidos.'),
      h('Sostenibilidad financiera', 2),
      p('El observatorio opera con los recursos operativos de la DENDD. De manera complementaria, se identifican posibles fuentes de cofinanciación con aliados estratégicos y organismos de cooperación, entre ellos el BID, la OCDE, la UNESCO y la CEPAL.'),
      nota('Nota. Los requerimientos cuantitativos de talento humano, infraestructura y financiación por vigencia deben completarse con la información presupuestal de la DENDD.'),

      // ============ 7. CONCLUSIONES ============
      h('Conclusiones', 1),
      p('Los apartados desarrollados en este anexo responden a las observaciones 2, 3 y 5 del memorando OAP No. 20266900157443 y permiten precisar cuatro aspectos del documento técnico del observatorio.'),
      p('En primer lugar, la comparación entre el Observatorio de Participación Ciudadana y el ONIA muestra que ambos tienen objetos de análisis, fenómenos observados, líneas y productos distintos, por lo que su coexistencia no genera duplicidad, sino complementariedad dentro de la oferta institucional de observatorios del DNP.'),
      p('En segundo lugar, el alcance funcional del observatorio queda circunscrito a la observación, el monitoreo, el análisis, la prospectiva, la divulgación y la apropiación. Las funciones de pensamiento estratégico, de articulación de actores y de asistencia técnica y producción normativa se asignan, respectivamente, al Tanque de Pensamiento de Desarrollo Digital, a RENADIA y a las entidades competentes.'),
      p('En tercer lugar, el mapa preliminar identifica ocho fuentes —seis secundarias y dos primarias— caracterizadas con los seis atributos solicitados por la OAP, bajo el procedimiento PT-GI-05 y articuladas con el Plan de Captura y Generación de Información. Sobre esa base se define un portafolio mínimo de productos organizado en cinco categorías.'),
      p('Por último, el análisis de sostenibilidad expone las condiciones técnicas, operativas y financieras previstas para el funcionamiento del observatorio. Este análisis es preliminar: su cierre requiere la información presupuestal de la DENDD sobre los requerimientos de talento humano, infraestructura y financiación por vigencia.'),

      // ============ 8. REFERENCIAS ============
      h('Referencias', 1, true),
      new Paragraph({ style: 'Referencia', children: [
        new TextRun({ text: 'Banco Mundial. (s. f.). ', font: ARIAL, size: 22 }),
        new TextRun({ text: 'GovTech Maturity Index (GTMI)', font: ARIAL, size: 22, italics: true }),
        new TextRun({ text: '. https://www.worldbank.org/en/programs/govtech', font: ARIAL, size: 22 }),
      ] }),
      new Paragraph({ style: 'Referencia', children: [
        new TextRun({ text: 'Congreso de la República de Colombia. (2012, 17 de octubre). Ley 1581 de 2012. Por la cual se dictan disposiciones generales para la protección de datos personales.', font: ARIAL, size: 22 }),
      ] }),
      new Paragraph({ style: 'Referencia', children: [
        new TextRun({ text: 'Departamento Nacional de Planeación. (s. f.-a). ', font: ARIAL, size: 22 }),
        new TextRun({ text: 'Banco de Fuentes Primarias (F-GI-01)', font: ARIAL, size: 22, italics: true }),
        new TextRun({ text: ' [documento interno del Sistema de Gestión Institucional].', font: ARIAL, size: 22 }),
      ] }),
      new Paragraph({ style: 'Referencia', children: [
        new TextRun({ text: 'Departamento Nacional de Planeación. (s. f.-b). ', font: ARIAL, size: 22 }),
        new TextRun({ text: 'Procedimiento de gestión de la información (PT-GI-05)', font: ARIAL, size: 22, italics: true }),
        new TextRun({ text: ' [documento interno del Sistema de Gestión Institucional].', font: ARIAL, size: 22 }),
      ] }),
      new Paragraph({ style: 'Referencia', children: [
        new TextRun({ text: 'Departamento Nacional de Planeación, Oficina Asesora de Planeación. (2026, 1 de junio). ', font: ARIAL, size: 22 }),
        new TextRun({ text: 'Memorando No. 20266900157443', font: ARIAL, size: 22, italics: true }),
        new TextRun({ text: ' [documento interno].', font: ARIAL, size: 22 }),
      ] }),
      new Paragraph({ style: 'Referencia', children: [
        new TextRun({ text: 'Función Pública. (s. f.-a). ', font: ARIAL, size: 22 }),
        new TextRun({ text: 'Formulario Único de Reporte de Avances de la Gestión (FURAG)', font: ARIAL, size: 22, italics: true }),
        new TextRun({ text: '. https://www.funcionpublica.gov.co/', font: ARIAL, size: 22 }),
      ] }),
      new Paragraph({ style: 'Referencia', children: [
        new TextRun({ text: 'Función Pública. (s. f.-b). ', font: ARIAL, size: 22 }),
        new TextRun({ text: 'Sistema de Información y Gestión del Empleo Público (SIGEP)', font: ARIAL, size: 22, italics: true }),
        new TextRun({ text: '. https://www.funcionpublica.gov.co/', font: ARIAL, size: 22 }),
      ] }),
      new Paragraph({ style: 'Referencia', children: [
        new TextRun({ text: 'Gobierno de Colombia. (s. f.). ', font: ARIAL, size: 22 }),
        new TextRun({ text: 'Datos Abiertos Colombia', font: ARIAL, size: 22, italics: true }),
        new TextRun({ text: '. https://www.datos.gov.co/', font: ARIAL, size: 22 }),
      ] }),
      new Paragraph({ style: 'Referencia', children: [
        new TextRun({ text: 'Organización para la Cooperación y el Desarrollo Económicos. (s. f.). ', font: ARIAL, size: 22 }),
        new TextRun({ text: 'OECD.AI Policy Observatory', font: ARIAL, size: 22, italics: true }),
        new TextRun({ text: '. https://oecd.ai/', font: ARIAL, size: 22 }),
      ] }),
      new Paragraph({ style: 'Referencia', children: [
        new TextRun({ text: 'Universidad de Stanford, Institute for Human-Centered Artificial Intelligence. (s. f.). ', font: ARIAL, size: 22 }),
        new TextRun({ text: 'AI Index Report', font: ARIAL, size: 22, italics: true }),
        new TextRun({ text: '. https://hai.stanford.edu/ai-index', font: ARIAL, size: 22 }),
      ] }),
    ],
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(process.argv[2] || 'salida.docx', buf);
  console.log('OK', (buf.length / 1024).toFixed(1) + ' KB');
});
