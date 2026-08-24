// Anexo 5 — Plan de Captura y Generacion de Informacion de Productos del ONIA.
// Componente 1: caracterizacion basica (paso 4 de la Lista de Verificacion).
// Fuente: "Anexo 5_Plan_Captura_Punto5_Caracterizacion_ONIA.docx" (version de trabajo).

const L = require('./lib');
const { p, h, caption, fuente, nota, ref, buildTable, buildDoc, save, blank } = L;

const SIGLAS = [
  ['API', 'Interfaz de programación de aplicaciones (application programming interface)'],
  ['BFP', 'Banco de Fuentes Primarias del DNP'],
  ['CONPES', 'Consejo Nacional de Política Económica y Social'],
  ['DANE', 'Departamento Administrativo Nacional de Estadística'],
  ['DAPRE', 'Departamento Administrativo de la Presidencia de la República'],
  ['DENDD', 'Dirección de Economía Naranja y Desarrollo Digital'],
  ['DNP', 'Departamento Nacional de Planeación'],
  ['FURAG', 'Formulario Único de Reporte de Avances de la Gestión'],
  ['HAI', 'Institute for Human-Centered Artificial Intelligence (Universidad de Stanford)'],
  ['HIP', 'Hexágono de Innovación Pública'],
  ['IA', 'Inteligencia artificial'],
  ['MinCiencias', 'Ministerio de Ciencia, Tecnología e Innovación'],
  ['MinTIC', 'Ministerio de Tecnologías de la Información y las Comunicaciones'],
  ['OCDE', 'Organización para la Cooperación y el Desarrollo Económicos'],
  ['ONIA', 'Observatorio Nacional de Inteligencia Artificial'],
  ['RENADIA', 'Red Nacional de Analítica de Datos e Inteligencia Artificial'],
  ['SIGEP', 'Sistema de Información y Gestión del Empleo Público'],
];

const PRESENTACION = [
  'El Departamento Nacional de Planeación (DNP), a través de la Dirección de Economía Naranja y Desarrollo Digital (DENDD), adelanta la estructuración del Observatorio Nacional de Inteligencia Artificial (ONIA) como instrumento de conocimiento para la observación, el monitoreo y el análisis de la inteligencia artificial (IA) en Colombia y de su gobernanza.',
  'La Lista de Verificación para la creación de observatorios del DNP exige, en su paso 4, la caracterización básica de la iniciativa: qué información se captura, de qué fuentes, con qué técnicas, a través de qué actores y mediante qué flujos de procesamiento. Este anexo responde a ese requisito y constituye el primer componente del Plan de Captura y Generación de Información de Productos del observatorio.',
  'El documento se dirige a la Oficina Asesora de Planeación, a la Dirección de Economía Naranja y Desarrollo Digital, al Subcomité de Gestión del Conocimiento e Innovación y a las instancias que participan en la revisión y la aprobación del observatorio. Su resultado esperado es que la caracterización de la captura quede documentada con el detalle suficiente para sustentar la operación del observatorio y, en particular, la producción de su producto faro: el Informe Anual sobre Gobernanza de la IA en Colombia.',
];

const cuerpo = [
  // 1. INTRODUCCIÓN
  h('Introducción', 1, true),
  p('El Plan de Captura y Generación de Información de Productos define la manera en que el Observatorio Nacional de Inteligencia Artificial obtiene, consolida, valida, procesa y divulga la información con la que elabora sus bienes y servicios. El plan se organiza en componentes y cada componente responde a un paso de la Lista de Verificación para la creación de observatorios del DNP. Este anexo desarrolla el primero de ellos: el paso 4, la caracterización básica del observatorio.'),
  p('El problema que atiende es operativo, no conceptual.'),
  p('Un observatorio que no precisa sus fuentes ni sus responsables termina produciendo información que no puede rastrearse hasta su origen, y repitiendo capturas que otras dependencias del DNP ya adelantan. El riesgo mayor aparece cuando cambia el equipo a cargo: sin la captura documentada, la operación se reconstruye desde cero y los productos pierden continuidad. Caracterizar la captura antes de operar es lo que permite anticipar ese escenario.'),
  p('En consecuencia, el propósito de este anexo es definir las técnicas de recolección, las fuentes, los actores responsables y los flujos de procesamiento que permiten producir los bienes y servicios cualitativos y cuantitativos del observatorio. Para ello se delimita el universo de fuentes y participantes, se describen las técnicas e instrumentos de captura previstos, se expone el flujo de procesamiento y validación hasta el producto faro, y se asignan los roles correspondientes.'),
  p('El alcance se limita a la caracterización de la captura y de la generación de información. No se abordan aquí el diseño conceptual del plan ni su estructuración operativa detallada, que corresponden al componente 3 del mismo plan (paso 7 de la Lista de Verificación), ni las fichas técnicas de los indicadores del observatorio. El anexo se articula con los numerales 7.3.1, 7.3.4, 7.3.5 y 8 del Anexo de propuesta de creación del ONIA, y opera bajo el procedimiento institucional PT-GI-05, Procesamiento y consolidación de información.'),
  p('Los capítulos 2 a 6 desarrollan, en ese orden, el propósito y el alcance del componente, el universo de fuentes, las técnicas de captura, el flujo de procesamiento y la asignación de roles. El capítulo 7 recoge las conclusiones y el 8 las referencias consultadas.'),

  // 2. PROPÓSITO Y ALCANCE
  h('Propósito y alcance del componente', 1),
  h('Propósito', 2),
  p('Este componente sustenta la caracterización básica del observatorio en el marco del paso 4 de la Lista de Verificación para la creación de observatorios del DNP. Su propósito es definir, de manera precisa, las técnicas de recolección, las fuentes, los actores responsables y los flujos de procesamiento que permiten producir los bienes y servicios cualitativos y cuantitativos del observatorio, así como soportar la operación del producto faro: el Informe Anual sobre Gobernanza de la IA en Colombia.'),
  h('Alcance y delimitaciones', 2),
  p('El componente cubre la captura de información propia y de terceros que alimenta las cinco líneas de acción del observatorio, así como su consolidación y su trazabilidad hasta la publicación. Se articula con los numerales 7.3.1, 7.3.4, 7.3.5 y 8 del Anexo de propuesta de creación del ONIA y opera bajo el procedimiento institucional PT-GI-05.'),
  p('Quedan fuera del alcance de este componente la definición de los indicadores y de sus fichas técnicas, la estructuración detallada del cronograma operativo y los aspectos presupuestales de la iniciativa, que se tratan en los instrumentos correspondientes del observatorio.'),

  // 3. UNIVERSO DE FUENTES Y PARTICIPANTES
  h('Universo de fuentes y participantes', 1),
  p('El universo de captura combina fuentes primarias y secundarias, articuladas con los roles internos y externos definidos en el numeral 7.3.4 del Anexo de propuesta de creación del ONIA. Las fuentes primarias corresponden a información que el observatorio genera o coproduce; las secundarias, a información ya publicada por terceros que el observatorio consolida y analiza. La Tabla 1 relaciona las tres categorías del universo con sus fuentes y con su rol en la captura.'),
  caption('Universo de fuentes y participantes del observatorio'),
  buildTable([2100, 4560, 2700], [
    ['Categoría', 'Fuentes y actores', 'Rol en la captura'],
    ['Fuentes primarias internas', 'Equipo técnico de la DENDD; RENADIA; mesas técnicas con direcciones del DNP; talleres de co-creación con el Subcomité de Gestión del Conocimiento e Innovación.', 'Generación directa de información y validación técnica interna.'],
    ['Fuentes primarias externas', 'Entidades nacionales y territoriales con iniciativas de IA; MinTIC; MinCiencias; DAPRE; academia; centros de pensamiento; actores de la sociedad civil convocados a través de RENADIA.', 'Aporte de información no publicada y contraste con el ecosistema.'],
    ['Fuentes secundarias', 'Repositorios institucionales (FURAG, SIGEP, OCDE.AI, AI Index Report de Stanford HAI, GovTech Maturity Index del Banco Mundial); Banco de Fuentes Primarias del DNP (formato F-GI-01); documentos CONPES vigentes; bibliografía especializada.', 'Consolidación y análisis de información ya publicada.'],
  ]),
  fuente(),
  p('Con las tres categorías puede contrastarse lo que las entidades declaran contra lo que registran los repositorios oficiales y lo que reportan las mediciones internacionales. Ninguna línea de análisis del observatorio queda sostenida por una sola fuente.'),

  // 4. TÉCNICAS E INSTRUMENTOS
  h('Técnicas e instrumentos de captura', 1),
  p('La captura se realiza mediante una matriz mixta cuantitativa, cualitativa, georreferenciada y prospectiva, en línea con la metodología del Hexágono de Innovación Pública (HIP) y con los vectores OPEN, TRANS y TEC del observatorio. La Tabla 2 relaciona cada técnica con sus instrumentos, sus herramientas y su aplicación prevista.'),
  caption('Técnicas, instrumentos y herramientas de captura'),
  buildTable([1700, 3230, 1830, 2600], [
    ['Técnica', 'Instrumento', 'Herramienta', 'Aplicación'],
    ['Cuantitativa', 'Extracción automatizada sobre repositorios abiertos y API públicas; encuestas estructuradas a entidades públicas mediante formularios electrónicos.', 'Python (pandas, requests, BeautifulSoup)', 'Series de datos y líneas base sobre adopción y gobernanza de la IA.'],
    ['Cualitativa', 'Entrevistas semiestructuradas; grupos focales con RENADIA; talleres de co-creación.', 'Codificación temática asistida (NVivo o equivalente)', 'Interpretación de prácticas, barreras y percepciones del ecosistema.'],
    ['Georreferenciada', 'Mapeo de iniciativas territoriales de IA, brechas regionales y nodos institucionales.', 'QGIS', 'Análisis de la distribución territorial del ecosistema de IA.'],
    ['Prospectiva y de IA aplicada', 'Análisis estructural de variables; identificación de señales débiles y clasificación de tecnologías emergentes.', 'MicMac; scikit-learn', 'Alertas tempranas y escenarios sobre la evolución de la IA.'],
  ], 18, 80),
  fuente(),
  nota('Nota. El análisis estructural parte de las doce variables identificadas en el numeral 9 del Anexo de propuesta de creación del ONIA.'),

  // 5. PROCESAMIENTO Y TRAZABILIDAD
  h('Procesamiento, validación y trazabilidad hacia el producto faro', 1),
  p('El flujo operativo sigue las cinco etapas del procedimiento PT-GI-05. La Tabla 3 describe cada etapa con sus actividades y su salida.'),
  caption('Etapas del flujo de captura y generación (PT-GI-05)'),
  buildTable([1900, 4860, 2600], [
    ['Etapa', 'Actividades', 'Salida'],
    ['1. Captura', 'Aplicación de los instrumentos por tipo de fuente, con registro de fecha, fuente y responsable.', 'Datos crudos con metadatos de origen.'],
    ['2. Consolidación', 'Integración de la información capturada y armonización de formatos.', 'Bases consolidadas por línea de acción.'],
    ['3. Validación', 'Cruces de bases de datos con entidades externas y mesas presenciales con actores de RENADIA cuando la información resulte inconsistente.', 'Bases validadas o devolución a la etapa de captura.'],
    ['4. Procesamiento', 'Análisis cuantitativo, cualitativo, espacial y prospectivo según la técnica aplicable.', 'Resultados analíticos y hallazgos.'],
    ['5. Divulgación', 'Publicación de los productos conforme al procedimiento PT-GC-01, Divulgación de información.', 'Bienes y servicios del observatorio publicados.'],
  ]),
  fuente(),
  p('La información procesada se traduce en los bienes y servicios del observatorio, cuya relación con el flujo anterior se presenta en la Tabla 4. El Informe Anual sobre Gobernanza de la IA en Colombia opera como producto integrador: recoge los resultados de las demás salidas del periodo y constituye el producto faro de la iniciativa.'),
  caption('Bienes y servicios generados a partir del flujo de captura'),
  buildTable([3400, 3760, 2200], [
    ['Producto', 'Contenido', 'Periodicidad'],
    ['Informe Anual sobre Gobernanza de la IA en Colombia (producto faro)', 'Consolidación analítica del periodo y línea base nacional sobre gobernanza de la IA.', 'Anual'],
    ['Boletines de alertas tempranas', 'Señales débiles y tendencias emergentes identificadas en la vigilancia tecnológica.', 'Trimestral'],
    ['Reportes de seguimiento al CONPES 4144', 'Avance de las acciones del CONPES 4144 de 2025 a cargo de la entidad.', 'Según los hitos del CONPES'],
    ['Repositorio de fuentes especializadas', 'Fuentes identificadas y caracterizadas, con sus metadatos.', 'Actualización continua'],
    ['Tableros de monitoreo', 'Visualización de los indicadores del observatorio.', 'Actualización continua'],
    ['Estudios de caso', 'Análisis en profundidad de experiencias sectoriales o territoriales.', 'Según programación'],
  ]),
  fuente(),

  // 6. ROLES
  h('Roles y responsables', 1),
  p('La operación del componente se sustenta en la distribución de responsabilidades que establece el procedimiento PT-GI-05 y que precisa la Tabla 5.'),
  caption('Roles y responsables en la captura y la generación de información'),
  buildTable([2400, 2960, 4000], [
    ['Rol', 'Responsable', 'Funciones'],
    ['Coordinación general', 'Director Técnico de la DENDD', 'Orientación del plan, aprobación de los productos y control del cumplimiento.'],
    ['Equipo técnico interno', 'Asesores y contratistas de la DENDD', 'Captura, consolidación y procesamiento de la información.'],
    ['Equipo técnico externo', 'Nodos de RENADIA y aliados estratégicos', 'Validación y coproducción de contenidos.'],
  ]),
  fuente(),
  nota('Nota. La asignación nominal de los responsables por producto debe completarse con la programación operativa de la DENDD para la vigencia.'),

  // 7. CONCLUSIONES
  h('Conclusiones', 1),
  p('La caracterización desarrollada en este componente responde al paso 4 de la Lista de Verificación para la creación de observatorios del DNP y deja resueltos cuatro asuntos de la operación del observatorio.'),
  p('El universo de captura queda delimitado en tres categorías: fuentes primarias internas, fuentes primarias externas y fuentes secundarias. Esa separación permite contrastar lo que las entidades declaran contra lo que registran los repositorios oficiales, de modo que ningún dato del observatorio depende de una sola fuente.'),
  p('La captura se organiza en cuatro técnicas, cada una con sus instrumentos y sus herramientas. Cada línea de acción del observatorio cuenta así con un método de recolección explícito.'),
  p('El flujo adopta las cinco etapas del procedimiento PT-GI-05 y establece la trazabilidad entre la información capturada y los productos publicados. El Informe Anual sobre Gobernanza de la IA en Colombia opera como producto integrador de ese flujo.'),
  p('Queda pendiente un asunto. La asignación de roles que aquí se propone es funcional (coordinación general, equipo técnico interno y equipo técnico externo) y su concreción nominal por producto depende de la programación operativa de la DENDD para la vigencia. Sin ese paso, el componente queda completo en su diseño pero no en su ejecución.'),

  // 8. REFERENCIAS
  h('Referencias', 1, true),
  ref(['Banco Mundial. (s. f.). ', { text: 'GovTech Maturity Index (GTMI)', italics: true }, '. https://www.worldbank.org/en/programs/govtech']),
  ref(['Consejo Nacional de Política Económica y Social. (2025). ', { text: 'Documento CONPES 4144. Política nacional de inteligencia artificial', italics: true }, '. Departamento Nacional de Planeación.']),
  ref(['Departamento Nacional de Planeación. (s. f.-a). ', { text: 'Banco de Fuentes Primarias (F-GI-01)', italics: true }, ' [documento interno del Sistema de Gestión Institucional].']),
  ref(['Departamento Nacional de Planeación. (s. f.-b). ', { text: 'Lista de verificación para la creación de observatorios', italics: true }, ' [documento interno del Sistema de Gestión Institucional].']),
  ref(['Departamento Nacional de Planeación. (2020). ', { text: 'Procesamiento y consolidación de información (PT-GI-05, versión 7)', italics: true }, ' [documento interno del Sistema de Gestión Institucional].']),
  ref(['Departamento Nacional de Planeación. (s. f.-c). ', { text: 'Divulgación de información (PT-GC-01)', italics: true }, ' [documento interno del Sistema de Gestión Institucional].']),
  ref(['Departamento Nacional de Planeación, Dirección de Economía Naranja y Desarrollo Digital. (2026). ', { text: 'Anexo de propuesta de creación del Observatorio Nacional de Inteligencia Artificial (ONIA)', italics: true }, ' [documento interno].']),
  ref(['Función Pública. (s. f.-a). ', { text: 'Formulario Único de Reporte de Avances de la Gestión (FURAG)', italics: true }, '. https://www.funcionpublica.gov.co/']),
  ref(['Función Pública. (s. f.-b). ', { text: 'Sistema de Información y Gestión del Empleo Público (SIGEP)', italics: true }, '. https://www.funcionpublica.gov.co/']),
  ref(['Organización para la Cooperación y el Desarrollo Económicos. (s. f.). ', { text: 'OECD.AI Policy Observatory', italics: true }, '. https://oecd.ai/']),
  ref(['Universidad de Stanford, Institute for Human-Centered Artificial Intelligence. (s. f.). ', { text: 'AI Index Report', italics: true }, '. https://hai.stanford.edu/ai-index']),
];

const doc = buildDoc({
  titulo: 'Anexo 5. Plan de Captura y Generación de Información de Productos del Observatorio Nacional de Inteligencia Artificial (ONIA). Componente 1: caracterización básica',
  subtitulo: 'Paso 4 de la Lista de Verificación para la creación de observatorios del Departamento Nacional de Planeación',
  descripcion: 'Componente 1 del Plan de Captura y Generación de Información de Productos del ONIA',
  cambio: 'Emisión inicial. Caracterización básica del observatorio: universo de fuentes, técnicas e instrumentos de captura, flujo de procesamiento y trazabilidad, y asignación de roles.',
  siglas: SIGLAS,
  presentacion: PRESENTACION,
  blocks: [{ children: cuerpo }],
});

save(doc, process.argv[2] || 'Anexo5.docx');
