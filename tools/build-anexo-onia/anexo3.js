// Anexo 3 — Apartados para el documento tecnico del ONIA.
// Ajustes en respuesta al memorando OAP No. 20266900157443 del 1 de junio de 2026.
// Reemplaza a build.js (monolito original): mismo contenido, sobre el chasis
// compartido de lib.js, con las firmas institucionales y la pasada de asimetria.

const L = require('./lib');
const { p, h, caption, fuente, nota, ref, buildTable, buildDoc, save } = L;

const SIGLAS = [
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
];

const PRESENTACION = [
  'El Departamento Nacional de Planeación (DNP), a través de la Dirección de Economía Naranja y Desarrollo Digital (DENDD), adelanta la estructuración del Observatorio Nacional de Inteligencia Artificial (ONIA) como instrumento de conocimiento para la observación, el monitoreo y el análisis de la inteligencia artificial (IA) en Colombia y de su gobernanza.',
  'En el marco de ese proceso, la Oficina Asesora de Planeación (OAP) formuló observaciones al documento técnico del observatorio mediante el memorando No. 20266900157443 del 1 de junio de 2026. El presente anexo consolida los apartados que se integrarán a la versión ajustada de dicho documento técnico, en atención a las observaciones 2, 3 y 5 del citado memorando.',
  'Estos apartados desarrollan, con mayor detalle, lo expuesto de manera resumida en la respuesta al oficio. El documento se dirige a la Oficina Asesora de Planeación, a la Dirección de Economía Naranja y Desarrollo Digital y a las instancias que participan en la revisión y en la aprobación del observatorio. Su resultado esperado es que el documento técnico del ONIA cuente con la precisión requerida sobre su diferenciación institucional, su alcance funcional, sus fuentes de información y sus condiciones de sostenibilidad, con miras a su presentación ante el Comité Institucional de Gestión y Desempeño (CIGD).',
];

const cuerpo = [
  // 1. INTRODUCCIÓN
  h('Introducción', 1, true),
  p('El documento técnico del Observatorio Nacional de Inteligencia Artificial sustenta la creación del observatorio y su presentación ante el Comité Institucional de Gestión y Desempeño. En la revisión de ese documento, la Oficina Asesora de Planeación formuló observaciones orientadas a precisar tres asuntos: la diferenciación del ONIA frente a los observatorios existentes en la entidad (observación 2), la delimitación de su alcance funcional frente a las demás iniciativas de la DENDD (observación 3) y la caracterización de sus fuentes de información, junto con las condiciones de sostenibilidad de la iniciativa (observación 5).'),
  p('El problema es de forma, no de fondo.'),
  p('La versión previa del documento técnico expone esos tres asuntos de manera resumida, y ese resumen no alcanza para valorar la pertinencia institucional del observatorio, su no duplicidad con otras instancias de la entidad ni su viabilidad en el tiempo. La respuesta al oficio se elaboró, además, en un formato breve. De ahí la necesidad de un desarrollo que pueda incorporarse directamente al cuerpo del documento técnico.'),
  p('El propósito de este anexo es, entonces, desarrollar los apartados que responden a las observaciones 2, 3 y 5 con el nivel de detalle suficiente para su integración en la versión ajustada del documento técnico. Se precisa la diferenciación del observatorio frente a las iniciativas existentes, se delimita su alcance funcional dentro de la arquitectura institucional de la DENDD, se presenta el mapa preliminar de fuentes con los atributos solicitados, se describe el portafolio mínimo de productos y se expone el análisis preliminar de sostenibilidad.'),
  p('El alcance se limita a los apartados señalados. No se abordan aquí los demás componentes del documento técnico del observatorio (entre ellos el marco conceptual, la justificación normativa y las fichas técnicas de indicadores), que se mantienen conforme a su versión vigente. Los apartados se elaboran a partir de la revisión de los documentos institucionales del observatorio y de las iniciativas de la DENDD, del mapeo de los observatorios existentes en la entidad, y de la identificación y caracterización de fuentes de información según los atributos solicitados por la OAP. El mapa de fuentes opera bajo el procedimiento institucional PT-GI-05 y se articula con el Plan de Captura y Generación de Información del observatorio.'),
  p('Los capítulos 2 a 6 desarrollan, en ese orden, la diferenciación frente a observatorios existentes, el alcance funcional y la arquitectura institucional, el mapa de fuentes y sus criterios de priorización, el portafolio mínimo de productos y el análisis de sostenibilidad. El capítulo 7 recoge las conclusiones y el 8 las referencias consultadas.'),

  // 2. DIFERENCIACIÓN
  h('Diferenciación frente a observatorios existentes', 1),
  p('En atención a la observación No. 2, se incorpora el Observatorio de Participación Ciudadana, cuya viabilidad fue aprobada por el CIGD, al mapeo de iniciativas existentes, y se precisa su diferenciación frente al ONIA. Ambos observatorios tienen objetos de estudio distintos y complementarios, sin superposición funcional, como se resume en la Tabla 1.'),
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
  p('La diferencia no es de matiz: el Observatorio de Participación Ciudadana se ocupa de la participación como fenómeno social y el ONIA se ocupa de la inteligencia artificial y de su gobernanza como objeto de política pública. Ninguna de sus cinco líneas coincide con las del otro. La coexistencia clarifica la oferta institucional de observatorios del DNP en vez de fragmentarla.'),

  // 3. ALCANCE FUNCIONAL
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

  // 4. MAPA DE FUENTES
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
  p('Conviene notar el resultado de aplicar esos criterios: de las ocho fuentes, seis son secundarias. En su arranque, el observatorio dependerá sobre todo de información que produce otro, y sus dos fuentes primarias son también las de mayor esfuerzo de captura.'),

  // 5. PORTAFOLIO
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

  // 6. SOSTENIBILIDAD
  h('Análisis de sostenibilidad', 1),
  p('En atención a la observación No. 5, se incorpora un análisis preliminar de la sostenibilidad técnica, operativa y financiera del observatorio.'),
  h('Sostenibilidad técnica', 2),
  p('El observatorio se apoya en la infraestructura de difusión institucional (página web, repositorios y tableros) y en el uso de herramientas de analítica como Python, QGIS y MicMac, así como de software libre y licenciado. Su operación aplica estándares de interoperabilidad y de protección de datos personales, conforme a la Ley 1581 de 2012.'),
  h('Sostenibilidad operativa', 2),
  p('La operación se sustenta en el talento humano especializado de la DENDD para la captura, la consolidación y el procesamiento de la información; en la articulación con los nodos de RENADIA para la validación y la coproducción; y en la aplicación del procedimiento PT-GI-05 para el mantenimiento y la actualización de contenidos.'),
  h('Sostenibilidad financiera', 2),
  p('El observatorio opera con los recursos operativos de la DENDD. De manera complementaria, se identifican posibles fuentes de cofinanciación con aliados estratégicos y organismos de cooperación, entre ellos el BID, la OCDE, la UNESCO y la CEPAL. Estas últimas son opciones identificadas, no recursos asegurados.'),
  nota('Nota. Los requerimientos cuantitativos de talento humano, infraestructura y financiación por vigencia deben completarse con la información presupuestal de la DENDD.'),

  // 7. CONCLUSIONES
  h('Conclusiones', 1),
  p('Los apartados desarrollados en este anexo responden a las observaciones 2, 3 y 5 del memorando OAP No. 20266900157443.'),
  p('La comparación entre el Observatorio de Participación Ciudadana y el ONIA muestra objetos de análisis, fenómenos observados, líneas y productos distintos. Su coexistencia no genera duplicidad sino complementariedad dentro de la oferta institucional de observatorios del DNP.'),
  p('El alcance funcional del observatorio queda circunscrito a la observación, el monitoreo, el análisis, la prospectiva, la divulgación y la apropiación. Las funciones de pensamiento estratégico, de articulación de actores y de asistencia técnica y producción normativa se asignan, respectivamente, al Tanque de Pensamiento de Desarrollo Digital, a RENADIA y a las entidades competentes.'),
  p('El mapa preliminar identifica ocho fuentes, seis secundarias y dos primarias, caracterizadas con los seis atributos solicitados por la OAP, bajo el procedimiento PT-GI-05 y articuladas con el Plan de Captura y Generación de Información. Sobre esa base se define un portafolio mínimo de productos organizado en cinco categorías.'),
  p('El análisis de sostenibilidad es el punto que queda abierto. Expone las condiciones técnicas, operativas y financieras previstas para el funcionamiento del observatorio, pero su cierre depende de la información presupuestal de la DENDD sobre los requerimientos de talento humano, infraestructura y financiación por vigencia. Mientras esa información no se incorpore, la viabilidad en el tiempo queda sustentada en términos cualitativos.'),

  // 8. REFERENCIAS
  h('Referencias', 1, true),
  ref(['Banco Mundial. (s. f.). ', { text: 'GovTech Maturity Index (GTMI)', italics: true }, '. https://www.worldbank.org/en/programs/govtech']),
  ref(['Congreso de la República de Colombia. (2012, 17 de octubre). Ley 1581 de 2012. Por la cual se dictan disposiciones generales para la protección de datos personales.']),
  ref(['Departamento Nacional de Planeación. (s. f.-a). ', { text: 'Banco de Fuentes Primarias (F-GI-01)', italics: true }, ' [documento interno del Sistema de Gestión Institucional].']),
  ref(['Departamento Nacional de Planeación. (s. f.-b). ', { text: 'Procedimiento de gestión de la información (PT-GI-05)', italics: true }, ' [documento interno del Sistema de Gestión Institucional].']),
  ref(['Departamento Nacional de Planeación, Oficina Asesora de Planeación. (2026, 1 de junio). ', { text: 'Memorando No. 20266900157443', italics: true }, ' [documento interno].']),
  ref(['Función Pública. (s. f.-a). ', { text: 'Formulario Único de Reporte de Avances de la Gestión (FURAG)', italics: true }, '. https://www.funcionpublica.gov.co/']),
  ref(['Función Pública. (s. f.-b). ', { text: 'Sistema de Información y Gestión del Empleo Público (SIGEP)', italics: true }, '. https://www.funcionpublica.gov.co/']),
  ref(['Gobierno de Colombia. (s. f.). ', { text: 'Datos Abiertos Colombia', italics: true }, '. https://www.datos.gov.co/']),
  ref(['Organización para la Cooperación y el Desarrollo Económicos. (s. f.). ', { text: 'OECD.AI Policy Observatory', italics: true }, '. https://oecd.ai/']),
  ref(['Universidad de Stanford, Institute for Human-Centered Artificial Intelligence. (s. f.). ', { text: 'AI Index Report', italics: true }, '. https://hai.stanford.edu/ai-index']),
];

const doc = buildDoc({
  titulo: 'Anexo 3. Apartados para el documento técnico del Observatorio Nacional de Inteligencia Artificial (ONIA)',
  subtitulo: 'Ajustes en respuesta al memorando OAP No. 20266900157443 del 1 de junio de 2026',
  descripcion: 'Ajustes en respuesta al memorando OAP No. 20266900157443 del 1 de junio de 2026',
  cambio: 'Emisión inicial. Consolidación de los apartados que responden a las observaciones 2, 3 y 5 del memorando OAP No. 20266900157443.',
  siglas: SIGLAS,
  presentacion: PRESENTACION,
  blocks: [{ children: cuerpo }],
});

save(doc, process.argv[2] || 'Anexo3.docx');
