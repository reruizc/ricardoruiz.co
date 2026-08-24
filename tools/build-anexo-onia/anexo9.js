// Anexo 9 — Matriz de trazabilidad entre el CONPES 4144 de 2025 y las funciones del ONIA.
// Responde al ajuste No. 4 del memorando OAP No. 20266900157443 del 1 de junio de 2026.
// Fuente: "Anexo 9_Matriz_Trazabilidad_CONPES4144_ONIA.docx" (version de trabajo).
// La matriz va en una seccion horizontal por su numero de columnas.

const L = require('./lib');
const { p, h, caption, fuente, nota, ref, buildTable, buildDoc, save } = L;

const SIGLAS = [
  ['CIGD', 'Comité Institucional de Gestión y Desempeño'],
  ['CONPES', 'Consejo Nacional de Política Económica y Social'],
  ['DENDD', 'Dirección de Economía Naranja y Desarrollo Digital'],
  ['DNP', 'Departamento Nacional de Planeación'],
  ['I+D+i', 'Investigación, desarrollo e innovación'],
  ['IA', 'Inteligencia artificial'],
  ['OAP', 'Oficina Asesora de Planeación'],
  ['ONIA', 'Observatorio Nacional de Inteligencia Artificial'],
  ['RENADIA', 'Red Nacional de Analítica de Datos e Inteligencia Artificial'],
  ['SisCONPES', 'Sistema de Seguimiento a Documentos CONPES'],
];

const PRESENTACION = [
  'El Departamento Nacional de Planeación (DNP), a través de la Dirección de Economía Naranja y Desarrollo Digital (DENDD), adelanta la estructuración del Observatorio Nacional de Inteligencia Artificial (ONIA) como instrumento de conocimiento para la observación, el monitoreo y el análisis de la inteligencia artificial (IA) en Colombia y de su gobernanza.',
  'En la revisión del documento técnico del observatorio, la Oficina Asesora de Planeación solicitó, mediante el ajuste No. 4 del memorando OAP No. 20266900157443 del 1 de junio de 2026, relacionar las acciones del CONPES 4144 de 2025 a cargo del DNP con las funciones concretas del observatorio. Este anexo atiende esa solicitud.',
  'El documento se dirige a la Oficina Asesora de Planeación, a la Dirección de Economía Naranja y Desarrollo Digital y a las instancias que participan en la revisión y en la aprobación del observatorio. Su resultado esperado es doble: evidenciar de qué manera el observatorio contribuye al cumplimiento de los compromisos de la entidad en el CONPES 4144 y delimitar sus funciones frente a otras instancias, con el fin de evitar duplicidades.',
];

// ---------- bloque 1 (vertical): introduccion y marco ----------
const bloque1 = [
  h('Introducción', 1, true),
  p('El CONPES 4144 de 2025 asigna compromisos a distintas entidades del Gobierno nacional en materia de inteligencia artificial. Entre ellos, la acción 1.3 prevé la creación y la puesta en marcha del Observatorio Nacional de Inteligencia Artificial a cargo del Departamento Nacional de Planeación. La estructuración del observatorio debe, por tanto, mostrar de manera explícita su correspondencia con esos compromisos.'),
  p('El problema que atiende este anexo es de trazabilidad. En la versión previa del documento técnico, la relación entre las acciones del CONPES y las funciones del observatorio quedaba enunciada de manera general, lo que dificultaba valorar dos asuntos: si el observatorio responde efectivamente a los compromisos de la entidad y si alguna de sus funciones se superpone con las de otras instancias. La Oficina Asesora de Planeación solicitó cerrar esa brecha mediante el ajuste No. 4 de su memorando.'),
  p('El propósito de este anexo es relacionar, acción por acción, los compromisos del CONPES 4144 de 2025 a cargo del DNP con las funciones concretas del observatorio, los productos esperados y los responsables. Cada acción se ubica en su eje estratégico, se le asocia la función del observatorio que la atiende y se identifican el producto, el responsable y la periodicidad. La matriz también deja constancia de lo contrario: qué funciones no son propias del observatorio y por qué instancia se canalizan.'),
  p('El alcance de esta versión se limita a las acciones plenamente documentadas en los insumos disponibles del observatorio, que corresponden a la acción 1.3 y a su hito 2. Las demás acciones del CONPES 4144 a cargo del DNP y de la DENDD se incorporan como filas plantilla, que deben completarse con el anexo del plan de acción del CONPES disponible en el Sistema de Seguimiento a Documentos CONPES (SisCONPES), una vez se identifiquen las acciones específicas asignadas a la entidad. Esta delimitación se declara de manera expresa para no atribuir al observatorio compromisos que aún no han sido verificados.'),
  p('Los capítulos 2 y 3 preparan la lectura de la matriz: el primero con los ejes estratégicos del CONPES que le sirven de marco, el segundo con el criterio de diligenciamiento de cada columna. La matriz está en el capítulo 4. El capítulo 5 desarrolla lo que ella deja ver sobre el límite de las funciones del observatorio. Cierran las conclusiones y las referencias consultadas.'),

  h('Marco de referencia: ejes estratégicos del CONPES 4144', 1),
  p('El CONPES 4144 de 2025 organiza su política en seis ejes estratégicos. La columna Eje estratégico de la matriz ubica cada acción en el eje que le corresponde, de modo que puede verificarse la cobertura temática de la contribución del observatorio. La Tabla 1 relaciona los seis ejes.'),
  caption('Ejes estratégicos del CONPES 4144 de 2025'),
  buildTable([1100, 3260, 5000], [
    ['No.', 'Eje estratégico', 'Relación con el observatorio'],
    ['i', 'Gobernanza y ética de la IA', 'Eje principal del observatorio: concentra su objeto de observación y análisis.'],
    ['ii', 'Infraestructura tecnológica y datos', 'Soporta el mapa de fuentes, el repositorio especializado y los tableros de monitoreo.'],
    ['iii', 'Investigación, desarrollo e innovación (I+D+i)', 'Por precisar según las acciones asignadas a la entidad.'],
    ['iv', 'Formación y talento digital', 'Se atiende mediante las actividades de divulgación y apropiación del conocimiento.'],
    ['v', 'Prevención de riesgos', 'Por precisar según las acciones asignadas a la entidad.'],
    ['vi', 'Adopción de la IA en los sectores público y privado', 'Por precisar según las acciones asignadas a la entidad.'],
  ]),
  fuente('Fuente: elaboración propia a partir del CONPES 4144 de 2025.'),

  h('Estructura de la matriz', 1),
  p('La matriz relaciona cada acción del CONPES con la función del observatorio que la atiende, el producto con el que se materializa y el responsable de su ejecución. La Tabla 2 describe el contenido de cada columna y el criterio con el que se diligencia.'),
  caption('Estructura y criterios de diligenciamiento de la matriz'),
  buildTable([2400, 3560, 3400], [
    ['Columna', 'Contenido', 'Criterio de diligenciamiento'],
    ['No.', 'Identificador de la acción del CONPES.', 'Se registra el número de la acción; las filas por completar se marcan con corchetes.'],
    ['Eje estratégico', 'Eje del CONPES 4144 al que pertenece la acción.', 'Se selecciona uno de los seis ejes relacionados en la Tabla 1.'],
    ['Acción / hito CONPES', 'Compromiso a cargo del DNP, con su hito asociado.', 'Se transcribe del anexo del plan de acción del CONPES.'],
    ['Función del observatorio', 'Función concreta con la que el observatorio atiende la acción.', 'Debe corresponder al alcance funcional definido para el observatorio.'],
    ['Producto esperado', 'Bien o servicio con el que se evidencia el cumplimiento.', 'Debe ser verificable y estar previsto en el portafolio del observatorio.'],
    ['Responsable', 'Unidad o instancia a cargo.', 'Se identifica la unidad de gestión del observatorio o la instancia articulada.'],
    ['Periodicidad', 'Frecuencia de generación del producto.', 'Se expresa en términos de la programación del producto.'],
  ], 18, 80),
  fuente(),
];

// ---------- bloque 2 (horizontal): la matriz ----------
const MATRIZ = [
  ['No.', 'Eje estratégico CONPES 4144', 'Acción / hito CONPES (a cargo del DNP)', 'Función concreta del observatorio (ONIA)', 'Producto esperado', 'Responsable', 'Periodicidad'],
  ['1.3', 'Gobernanza y ética de la IA', 'Acción 1.3 — Hito 2: creación y puesta en marcha del Observatorio Nacional de Inteligencia Artificial (ONIA).', 'Observación, monitoreo y análisis de la gobernanza de la IA en Colombia; consolidación de la línea base nacional.', 'Informe Anual sobre Gobernanza de la IA en Colombia (producto faro).', 'DENDD — Unidad de Investigación del ONIA', 'Anual'],
  ['1.3', 'Gobernanza y ética de la IA', 'Acción 1.3 — Hito 2: seguimiento al avance de la política y a las tendencias emergentes.', 'Vigilancia tecnológica y prospectiva; identificación de señales débiles y alertas tempranas.', 'Cuatro informes trimestrales con alertas tempranas y recomendaciones priorizadas.', 'DENDD — Unidades de Investigación y de Redes y Gestión del ONIA', 'Trimestral'],
  ['1.3', 'Formación y talento digital', 'Acción 1.3 — Hito 2: fortalecimiento de capacidades para la gobernanza participativa de la IA.', 'Divulgación y apropiación del conocimiento; formación a actores habilitantes.', 'Cuatro capacitaciones a actores habilitantes, en articulación con RENADIA.', 'DENDD — Área de Capacitación, en articulación con RENADIA', 'Anual (cuatro al año)'],
  ['1.3', 'Gobernanza y ética de la IA', 'Acción 1.3 — Hito 2: articulación de capacidades nacionales en analítica e IA.', 'Articulación interinstitucional y comunidad de práctica. Función canalizada por RENADIA; no es propia del observatorio.', 'Sesiones y productos colaborativos de la Red Nacional de Analítica de Datos e Inteligencia Artificial (RENADIA).', 'DENDD — Unidad de Redes y Gestión / RENADIA', 'Permanente'],
  ['1.3', 'Infraestructura tecnológica y datos', 'Acción 1.3 — Hito 2: ecosistema de fuentes e interoperabilidad de información sobre IA.', 'Producción y curaduría del mapa de fuentes; repositorio especializado; tableros de monitoreo.', 'Repositorio de fuentes especializadas y tableros de monitoreo, bajo el procedimiento PT-GI-05.', 'DENDD — Unidad de Investigación del ONIA', 'Continua'],
  ['[ ]', 'Investigación, desarrollo e innovación (I+D+i)', '[Por completar: acción o hito del CONPES 4144 a cargo del DNP-DENDD, según el anexo del plan de acción]', '[Función concreta del observatorio asociada]', '[Producto esperado]', '[Responsable]', '[Periodicidad]'],
  ['[ ]', 'Prevención de riesgos', '[Por completar: acción o hito del CONPES 4144 a cargo del DNP-DENDD]', '[Función concreta del observatorio asociada]', '[Producto esperado]', '[Responsable]', '[Periodicidad]'],
  ['[ ]', 'Adopción de la IA en los sectores público y privado', '[Por completar: acción o hito del CONPES 4144 a cargo del DNP-DENDD]', '[Función concreta del observatorio asociada]', '[Producto esperado]', '[Responsable]', '[Periodicidad]'],
];

const bloque2 = [
  h('Matriz de trazabilidad', 1),
  p('La Tabla 3 presenta la matriz de trazabilidad entre las acciones del CONPES 4144 de 2025 a cargo del DNP, las funciones del observatorio, los productos esperados y los responsables.'),
  caption('Matriz de trazabilidad entre el CONPES 4144 de 2025 y las funciones del ONIA'),
  buildTable([700, 1700, 2600, 2600, 2360, 1700, 1300], MATRIZ, 18, 60, { pendingRows: [6, 7, 8] }),
  fuente(),
  nota('Nota. Las filas sombreadas corresponden a plantillas por completar con las demás acciones del CONPES 4144 a cargo del DNP-DENDD, conforme al anexo del plan de acción del CONPES disponible en SisCONPES. Las filas diligenciadas corresponden a la acción 1.3 — hito 2, documentada en los insumos del observatorio.'),
];

// ---------- bloque 3 (vertical): delimitacion, conclusiones, referencias ----------
const bloque3 = [
  h('Delimitación de funciones frente a otras instancias', 1),
  p('La matriz cumple una segunda finalidad, además de la trazabilidad: hacer explícito el límite entre lo que el observatorio ejecuta directamente y lo que se canaliza por otras instancias de la Dirección o de la entidad.'),
  p('De las cinco filas diligenciadas, cuatro corresponden a funciones propias del observatorio: observación, monitoreo y análisis; vigilancia tecnológica y prospectiva; divulgación y apropiación; y producción y curaduría del mapa de fuentes.'),
  p('La quinta es distinta. La articulación de capacidades nacionales en analítica e inteligencia artificial no es una función del observatorio: se canaliza a través de RENADIA, en su condición de mecanismo de articulación interinstitucional. La matriz la registra de manera expresa, y no la omite, precisamente para que no se le atribuya al observatorio una función que corresponde a la red. Esa distinción es consistente con la arquitectura institucional definida para la iniciativa, en la que el Tanque de Pensamiento de Desarrollo Digital asume la producción de conocimiento estratégico de mayor alcance y las entidades competentes conservan la asistencia técnica y la producción normativa.'),

  h('Conclusiones', 1),
  p('Con la matriz queda atendido el ajuste No. 4 del memorando OAP No. 20266900157443.'),
  p('Las funciones del observatorio quedan asociadas a acciones concretas del CONPES 4144 de 2025 y a productos verificables, con responsable y periodicidad definidos. La contribución del observatorio al cumplimiento de los compromisos de la entidad puede valorarse, así, en términos de productos y no de enunciados generales. La matriz distingue además esas funciones de las que se canalizan por RENADIA, con lo que se previene la duplicidad dentro de la Dirección.'),
  p('El alcance de esta versión es parcial y conviene decirlo sin rodeos. La matriz cubre la acción 1.3 y su hito 2. Las acciones de los ejes de investigación, desarrollo e innovación, prevención de riesgos y adopción de la IA quedan como plantillas, porque los insumos disponibles del observatorio no permiten atribuirlas todavía. Cerrarlas exige identificar las acciones específicas asignadas al DNP y a la DENDD en el anexo del plan de acción del CONPES, disponible en SisCONPES. Es el paso siguiente de este anexo.'),

  h('Referencias', 1, true),
  ref(['Consejo Nacional de Política Económica y Social. (2025). ', { text: 'Documento CONPES 4144. Política nacional de inteligencia artificial', italics: true }, '. Departamento Nacional de Planeación.']),
  ref(['Departamento Nacional de Planeación. (s. f.-a). ', { text: 'Procesamiento y consolidación de información (PT-GI-05)', italics: true }, ' [documento interno del Sistema de Gestión Institucional].']),
  ref(['Departamento Nacional de Planeación. (s. f.-b). ', { text: 'Sistema de Seguimiento a Documentos CONPES (SisCONPES)', italics: true }, '. https://www.dnp.gov.co/']),
  ref(['Departamento Nacional de Planeación, Dirección de Economía Naranja y Desarrollo Digital. (2026). ', { text: 'Anexo de propuesta de creación del Observatorio Nacional de Inteligencia Artificial (ONIA)', italics: true }, ' [documento interno].']),
  ref(['Departamento Nacional de Planeación, Oficina Asesora de Planeación. (2026, 1 de junio). ', { text: 'Memorando No. 20266900157443', italics: true }, ' [documento interno].']),
];

const doc = buildDoc({
  titulo: 'Anexo 9. Matriz de trazabilidad entre el CONPES 4144 de 2025 y las funciones del Observatorio Nacional de Inteligencia Artificial (ONIA)',
  subtitulo: 'Respuesta al ajuste No. 4 del memorando OAP No. 20266900157443 del 1 de junio de 2026',
  descripcion: 'Matriz de trazabilidad entre las acciones del CONPES 4144 de 2025 a cargo del DNP y las funciones del ONIA',
  cambio: 'Emisión inicial. Matriz de trazabilidad entre las acciones del CONPES 4144 de 2025 a cargo del DNP-DENDD y las funciones, productos y responsables del observatorio.',
  siglas: SIGLAS,
  presentacion: PRESENTACION,
  blocks: [
    { children: bloque1 },
    { landscape: true, children: bloque2 },
    { children: bloque3 },
  ],
});

save(doc, process.argv[2] || 'Anexo9.docx');
