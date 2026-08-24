// Anexo 7 — Plan de Captura y Generacion de Informacion de Productos del ONIA.
// Componente 3: diseno conceptual y estructuracion (paso 7 de la Lista de Verificacion).
// Fuente: "Anexo 7_Plan_Captura_Punto7_Diseno_Conceptual_ONIA.docx" (version de trabajo).

const L = require('./lib');
const { p, h, caption, fuente, nota, ref, buildTable, buildDoc, save } = L;

const SIGLAS = [
  ['CIGD', 'Comité Institucional de Gestión y Desempeño'],
  ['CONPES', 'Consejo Nacional de Política Económica y Social'],
  ['DANE', 'Departamento Administrativo Nacional de Estadística'],
  ['DCAT-AP', 'Data Catalogue Vocabulary — Application Profile'],
  ['DENDD', 'Dirección de Economía Naranja y Desarrollo Digital'],
  ['DNP', 'Departamento Nacional de Planeación'],
  ['IA', 'Inteligencia artificial'],
  ['MinCiencias', 'Ministerio de Ciencia, Tecnología e Innovación'],
  ['MinTIC', 'Ministerio de Tecnologías de la Información y las Comunicaciones'],
  ['MIPG', 'Modelo Integrado de Planeación y Gestión'],
  ['OCDE', 'Organización para la Cooperación y el Desarrollo Económicos'],
  ['ONIA', 'Observatorio Nacional de Inteligencia Artificial'],
  ['RENADIA', 'Red Nacional de Analítica de Datos e Inteligencia Artificial'],
];

const PRESENTACION = [
  'El Departamento Nacional de Planeación (DNP), a través de la Dirección de Economía Naranja y Desarrollo Digital (DENDD), adelanta la estructuración del Observatorio Nacional de Inteligencia Artificial (ONIA) como instrumento de conocimiento para la observación, el monitoreo y el análisis de la inteligencia artificial (IA) en Colombia y de su gobernanza.',
  'La Lista de Verificación para la creación de observatorios del DNP exige, en su paso 7, el diseño conceptual y la estructuración de la iniciativa. Este anexo responde a ese requisito y constituye el tercer componente del Plan de Captura y Generación de Información de Productos del observatorio. Corresponde al entregable formal que se presenta al Subcomité de Gestión del Conocimiento e Innovación y, posteriormente, al Comité Institucional de Gestión y Desempeño (CIGD) del DNP.',
  'El documento se dirige a esas dos instancias, a la Oficina Asesora de Planeación y a la Dirección de Economía Naranja y Desarrollo Digital. Su resultado esperado es que el diseño del plan quede sustentado en sus referentes normativos y metodológicos, con un flujo de captura estructurado, articulado con las líneas de acción del observatorio y sujeto a mecanismos explícitos de control de calidad.',
];

const cuerpo = [
  // 1. INTRODUCCIÓN
  h('Introducción', 1, true),
  p('El paso 7 de la Lista de Verificación para la creación de observatorios del DNP exige el diseño conceptual y la estructuración de la iniciativa. Es el entregable que se somete al Subcomité de Gestión del Conocimiento e Innovación y, después, al Comité Institucional de Gestión y Desempeño. Este anexo lo desarrolla como componente 3 del Plan de Captura y Generación de Información de Productos del Observatorio Nacional de Inteligencia Artificial.'),
  p('Saber de dónde sale la información no basta para sustentar la creación del observatorio ante las instancias de decisión. Esa fue la conclusión del componente 1, que caracterizó fuentes y técnicas pero dejó abierto el asunto metodológico: de qué normas y procedimientos se deriva el plan, cómo se encadenan sus etapas y bajo qué controles se asegura la calidad de la información que produce. Sin ese diseño, la operación queda a discreción del equipo que la ejecute y deja de ser verificable.'),
  p('En consecuencia, el propósito de este anexo es exponer el diseño conceptual del plan y su estructuración operativa. Para ello se precisa su sustento normativo y metodológico, se describe la estructura del flujo de captura y generación, se articula ese flujo con las cinco líneas de acción del observatorio, se presentan el cronograma y los instrumentos previstos, y se establecen los mecanismos de control de calidad.'),
  p('El alcance se limita al diseño y a la estructuración del plan. Quedan fuera la caracterización básica del observatorio (componente 1, paso 4 de la Lista de Verificación) y las fichas técnicas de los indicadores. El diseño se sustenta en la acción 1.3 del CONPES 4144 de 2025, en el Decreto 1499 de 2017 y en la dimensión de Gestión del Conocimiento y la Innovación del MIPG. Operativamente se rige por el procedimiento institucional PT-GI-05 y se articula con los procedimientos PT-GI-03, PT-GI-04 y PT-GC-01.'),
  p('El capítulo 2 fija el marco normativo y los procedimientos que rigen el plan. Sobre esa base, los capítulos 3 y 4 describen el flujo de captura y su correspondencia con las líneas de acción del observatorio. Los capítulos 5 y 6 pasan a la operación: cronograma, instrumentos y controles de calidad. Cierran las conclusiones y las referencias consultadas.'),

  // 2. SUSTENTO
  h('Sustento normativo y metodológico', 1),
  p('Este componente corresponde al entregable formal que se presenta al Subcomité de Gestión del Conocimiento e Innovación y, posteriormente, al Comité Institucional de Gestión y Desempeño del DNP.'),
  h('Referencias normativas y de política', 2),
  p('El plan se sustenta en la acción 1.3 del CONPES 4144 de 2025, que prevé la creación y la puesta en marcha del observatorio; en el Decreto 1499 de 2017, que actualiza el Modelo Integrado de Planeación y Gestión; y en la dimensión de Gestión del Conocimiento y la Innovación del MIPG, que orienta la generación, la captura y la disposición del conocimiento institucional.'),
  h('Procedimientos institucionales aplicables', 2),
  p('Operativamente, el plan se rige por el procedimiento PT-GI-05 y se articula con otros tres procedimientos del Sistema de Gestión Institucional, como se detalla en la Tabla 1.'),
  caption('Procedimientos institucionales aplicables al plan'),
  buildTable([1300, 3860, 4200], [
    ['Código', 'Procedimiento', 'Aplicación en el plan'],
    ['PT-GI-05', 'Procesamiento y consolidación de información', 'Define las cinco etapas del flujo de captura y generación.'],
    ['PT-GI-03', 'Medición del desempeño y asuntos públicos', 'Orienta la medición asociada a los indicadores del observatorio.'],
    ['PT-GI-04', 'Estudios en aspectos de competencia del DNP', 'Enmarca los estudios y análisis derivados de la información capturada.'],
    ['PT-GC-01', 'Divulgación de información', 'Rige la publicación de los productos del observatorio.'],
  ]),
  fuente(),

  // 3. ESTRUCTURA DEL FLUJO
  h('Estructura del flujo de captura y generación', 1),
  p('El componente 1 estableció de dónde proviene la información del observatorio; a este componente le corresponde ordenarla en un flujo. Ese flujo se organiza en las cinco etapas del procedimiento PT-GI-05, articuladas con las unidades de gestión del observatorio: Investigación, Asesoría, Capacitación, Redes y Gestión, y Comunicaciones. La Tabla 2 describe cada etapa con sus actividades, sus instrumentos y su salida.'),
  caption('Estructura del flujo de captura y generación de información'),
  buildTable([1750, 3210, 2200, 2200], [
    ['Etapa', 'Actividades', 'Instrumentos', 'Salida'],
    ['1. Captura', 'Definición de instrumentos por tipo de fuente: cuantitativa, cualitativa, georreferenciada y prospectiva. Las bases del Banco de Fuentes Primarias del DNP se registran en el formato F-GI-01.', 'Formularios de captura; formato F-GI-01', 'Datos crudos con metadatos de origen.'],
    ['2. Consolidación', 'Integración por unidad de gestión, con filtros de calidad, deduplicación y armonización de metadatos.', 'Estándares Dublin Core y DCAT-AP', 'Bases consolidadas por unidad de gestión.'],
    ['3. Validación', 'Cruces con entidades externas (MinTIC, MinCiencias, DANE) y mesas técnicas con RENADIA. La inconsistencia o la falta de información retorna el flujo a la etapa de captura.', 'Bitácoras de validación', 'Bases validadas o devolución a captura.'],
    ['4. Procesamiento', 'Análisis cuantitativo, espacial, prospectivo y cualitativo según la técnica aplicable.', 'Python (pandas, scikit-learn); QGIS; MicMac; codificación temática', 'Resultados analíticos y hallazgos.'],
    ['5. Divulgación', 'Publicación conforme al procedimiento PT-GC-01.', 'Repositorio del observatorio; tableros', 'Bases certificadas, tableros, boletines, informes trimestrales e Informe Anual.'],
  ], 18, 80),
  fuente(),
  p('La devolución prevista en la etapa de validación opera como control del flujo: ninguna base pasa a procesamiento sin haber superado el cruce con fuentes externas o la revisión en mesa técnica.'),

  // 4. LÍNEAS DE ACCIÓN
  h('Articulación con las líneas de acción del observatorio', 1),
  p('El plan cubre las cinco líneas de acción del ONIA descritas en el numeral 7.3.4 del Anexo de propuesta de creación del observatorio. Cada línea cuenta con instrumentos específicos de captura, como se relaciona en la Tabla 3.'),
  caption('Instrumentos de captura por línea de acción'),
  buildTable([2400, 4160, 2800], [
    ['Línea de acción', 'Instrumento de captura', 'Fuente principal'],
    ['Vigilancia tecnológica', 'Monitoreo automatizado de fuentes globales.', 'OCDE.AI, AI Index Report, arXiv'],
    ['Prospectiva', 'Talleres de análisis estructural y construcción de escenarios.', 'Panel de expertos; herramienta MicMac'],
    ['Ética y regulación', 'Levantamiento de marcos regulatorios y autodiagnósticos.', 'Normativa vigente; entidades públicas'],
    ['Adopción sectorial y territorial', 'Mapeo de iniciativas.', 'Entidades nacionales y territoriales'],
    ['Articulación con RENADIA', 'Encuestas estructuradas a nodos.', 'Nodos de RENADIA'],
  ]),
  fuente(),

  // 5. CRONOGRAMA E INSTRUMENTOS
  h('Cronograma e instrumentos', 1),
  h('Cronograma', 2),
  p('La operación del plan se programa a 34 semanas, entre abril y diciembre de 2026, distribuidas en cuatro fases sincronizadas con las cuatro entregas contractuales y con los cinco hitos del CONPES 4144. La Tabla 4 presenta esa distribución.'),
  caption('Fases de operación del plan'),
  buildTable([1560, 2400, 2800, 2600], [
    ['Fase', 'Énfasis', 'Actividades principales', 'Entrega asociada'],
    ['Fase 1 (semanas 1 a 8)', 'Alistamiento y captura inicial', 'Definición de instrumentos, apertura del repositorio y primeras capturas.', 'Primera entrega contractual'],
    ['Fase 2 (semanas 9 a 17)', 'Consolidación y validación', 'Integración por unidad de gestión, cruces con entidades externas y mesas técnicas.', 'Segunda entrega contractual'],
    ['Fase 3 (semanas 18 a 26)', 'Procesamiento y análisis', 'Análisis cuantitativo, espacial, prospectivo y cualitativo de la información validada.', 'Tercera entrega contractual'],
    ['Fase 4 (semanas 27 a 34)', 'Divulgación y cierre', 'Publicación de productos y consolidación del Informe Anual.', 'Cuarta entrega contractual'],
  ], 18, 80),
  fuente(),
  nota('Nota. La distribución por fases es indicativa: el número total de semanas y su marco temporal corresponden a la programación de la iniciativa, mientras que la asignación semana a semana debe ajustarse al cronograma definitivo de las entregas contractuales y a las fechas de los hitos del CONPES 4144.'),
  h('Instrumentos', 2),
  p('La operación se apoya en cinco instrumentos, relacionados en la Tabla 5. Toda la información capturada queda registrada con trazabilidad de fecha, fuente y responsable.'),
  caption('Instrumentos de operación del plan'),
  buildTable([2800, 4160, 2400], [
    ['Instrumento', 'Descripción', 'Aporte a la trazabilidad'],
    ['Matriz maestra de fuentes y actores', 'Registro único de las fuentes identificadas y de los actores vinculados a cada una.', 'Identifica el origen de cada dato.'],
    ['Formularios estandarizados de captura', 'Instrumentos homogéneos por tipo de fuente.', 'Asegura la comparabilidad entre capturas.'],
    ['Repositorio centralizado del observatorio', 'Almacenamiento único de las bases y de los documentos de soporte.', 'Conserva las versiones de cada base.'],
    ['Libros de código', 'Documentación del procesamiento aplicado a cada base.', 'Permite reproducir los resultados.'],
    ['Bitácoras de validación', 'Registro de los cruces y de las mesas técnicas realizadas.', 'Documenta las decisiones de validación.'],
  ]),
  fuente(),

  // 6. CONTROL DE CALIDAD
  h('Mecanismos de control de calidad', 1),
  p('El plan incorpora cuatro mecanismos de control de calidad, que operan de manera continua sobre el flujo descrito en el capítulo 3. La Tabla 6 los relaciona con su responsable y su periodicidad.'),
  caption('Mecanismos de control de calidad'),
  buildTable([2200, 4160, 1600, 1400], [
    ['Mecanismo', 'Descripción', 'Responsable', 'Periodicidad'],
    ['Doble revisión', 'Todo dato consolidado pasa por revisión técnica de un segundo asesor antes de su procesamiento.', 'Equipo técnico de la DENDD', 'Por cada base'],
    ['Auditoría documental', 'Control de las bases del observatorio.', 'Coordinación de la DENDD', 'Trimestral'],
    ['Estándares éticos y de protección de datos', 'Cumplimiento de la Ley 1581 de 2012 y de los lineamientos de uso responsable de la IA del CONPES 4144 de 2025.', 'Equipo técnico de la DENDD', 'Continua'],
    ['Reproducibilidad', 'Publicación de scripts y libros de código para garantizar la verificabilidad de los resultados.', 'Equipo técnico de la DENDD', 'Por cada producto'],
  ], 18, 80),
  fuente(),

  // 7. CONCLUSIONES
  h('Conclusiones', 1),
  p('Con lo anterior queda cubierto el paso 7 de la Lista de Verificación.'),
  p('El plan queda sustentado en la acción 1.3 del CONPES 4144 de 2025, en el Decreto 1499 de 2017 y en la dimensión de Gestión del Conocimiento y la Innovación del MIPG, y se rige por cuatro procedimientos del Sistema de Gestión Institucional. Su operación no depende, entonces, de arreglos propios de la iniciativa: cuando cambie el equipo, el procedimiento sigue siendo el mismo.'),
  p('El flujo adopta las cinco etapas del PT-GI-05 con un control explícito en la validación. La información inconsistente retorna a captura y no avanza a procesamiento.'),
  p('Las cinco líneas de acción del observatorio cuentan con instrumentos de captura y fuentes principales identificadas, con lo que el plan cubre la totalidad del alcance funcional definido para la iniciativa. La operación se programa en cuatro fases a lo largo de 34 semanas, apoyada en cinco instrumentos de soporte y cuatro mecanismos de control de calidad.'),
  p('Sobre el cronograma conviene ser explícito. El número de semanas y su marco temporal corresponden a la programación de la iniciativa, pero la distribución por fases que presenta la Tabla 4 es una propuesta: su ajuste depende del cronograma definitivo de las entregas contractuales y de las fechas de los hitos del CONPES 4144.'),

  // 8. REFERENCIAS
  h('Referencias', 1, true),
  ref(['Congreso de la República de Colombia. (2012, 17 de octubre). Ley 1581 de 2012. Por la cual se dictan disposiciones generales para la protección de datos personales.']),
  ref(['Consejo Nacional de Política Económica y Social. (2025). ', { text: 'Documento CONPES 4144. Política nacional de inteligencia artificial', italics: true }, '. Departamento Nacional de Planeación.']),
  ref(['Departamento Nacional de Planeación. (s. f.-a). ', { text: 'Banco de Fuentes Primarias (F-GI-01)', italics: true }, ' [documento interno del Sistema de Gestión Institucional].']),
  ref(['Departamento Nacional de Planeación. (s. f.-b). ', { text: 'Divulgación de información (PT-GC-01)', italics: true }, ' [documento interno del Sistema de Gestión Institucional].']),
  ref(['Departamento Nacional de Planeación. (s. f.-c). ', { text: 'Estudios en aspectos de competencia del DNP (PT-GI-04)', italics: true }, ' [documento interno del Sistema de Gestión Institucional].']),
  ref(['Departamento Nacional de Planeación. (s. f.-d). ', { text: 'Lista de verificación para la creación de observatorios', italics: true }, ' [documento interno del Sistema de Gestión Institucional].']),
  ref(['Departamento Nacional de Planeación. (s. f.-e). ', { text: 'Medición del desempeño y asuntos públicos (PT-GI-03)', italics: true }, ' [documento interno del Sistema de Gestión Institucional].']),
  ref(['Departamento Nacional de Planeación. (2020). ', { text: 'Procesamiento y consolidación de información (PT-GI-05, versión 7)', italics: true }, ' [documento interno del Sistema de Gestión Institucional].']),
  ref(['Departamento Nacional de Planeación, Dirección de Economía Naranja y Desarrollo Digital. (2026). ', { text: 'Anexo de propuesta de creación del Observatorio Nacional de Inteligencia Artificial (ONIA)', italics: true }, ' [documento interno].']),
  ref(['Función Pública. (2024). ', { text: 'Manual operativo del Modelo Integrado de Planeación y Gestión (versión 6)', italics: true }, '. https://www.funcionpublica.gov.co/']),
  ref(['Presidencia de la República de Colombia. (2017, 11 de septiembre). Decreto 1499 de 2017. Por medio del cual se modifica el Decreto 1083 de 2015, Decreto Único Reglamentario del Sector Función Pública, en lo relacionado con el Sistema de Gestión establecido en el artículo 133 de la Ley 1753 de 2015.']),
];

const doc = buildDoc({
  titulo: 'Anexo 7. Plan de Captura y Generación de Información de Productos del Observatorio Nacional de Inteligencia Artificial (ONIA). Componente 3: diseño conceptual y estructuración',
  subtitulo: 'Paso 7 de la Lista de Verificación para la creación de observatorios del Departamento Nacional de Planeación',
  descripcion: 'Componente 3 del Plan de Captura y Generación de Información de Productos del ONIA',
  cambio: 'Emisión inicial. Diseño conceptual y estructuración del plan: sustento normativo y metodológico, estructura del flujo, articulación con las líneas de acción, cronograma e instrumentos, y mecanismos de control de calidad.',
  siglas: SIGLAS,
  presentacion: PRESENTACION,
  blocks: [{ children: cuerpo }],
});

save(doc, process.argv[2] || 'Anexo7.docx');
