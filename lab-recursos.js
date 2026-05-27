// ═════════════════════════════════════════════════════════════════════════
// Lab de Políticas Públicas y Prospectiva · Catálogo de Recursos & Datos
// ═════════════════════════════════════════════════════════════════════════
// Recursos externos curados, agrupados por categoría y etiquetados por
// módulo del lab donde son más relevantes. Cargado por los 6 módulos
// (analisis-estructural, mactor, problema-publico, evaluacion,
// alternativas, ain) vía <script src="lab-recursos.js"></script> al
// final del body.
//
// Convenciones:
//   - SOLO recursos oficiales o instituciones reconocidas (no blogs).
//   - URLs ESTABLES — sólo dominios institucionales o sitios académicos
//     consolidados. Si un link se rompe, hay que actualizarlo aquí y
//     ya queda corregido para los 5 puntos de carga.
//   - 'modulos' marca dónde se destaca el recurso. Vacío = todos.
//   - Para añadir un módulo nuevo (ej. 'alternativas'), simplemente
//     agrégalo al array correspondiente; el frontend lo recoge sin
//     tocar lógica.
// ═════════════════════════════════════════════════════════════════════════

window.LAB_RECURSOS = {
  categorias: [
    { id: 'co-pp',       nombre: 'Colombia · Política pública',     orden: 1 },
    { id: 'co-datos',    nombre: 'Colombia · Datos abiertos',       orden: 2 },
    { id: 'evaluacion',  nombre: 'Evaluación de política',          orden: 3 },
    { id: 'diseno',      nombre: 'Diseño de política y participación', orden: 4 },
    { id: 'prospectiva', nombre: 'Prospectiva y método',            orden: 5 }
  ],
  items: [
    // ─── Colombia · Política pública ───────────────────────────────────────
    {
      id: 'conpes', categoria: 'co-pp',
      nombre: 'CONPES · Documentos de política',
      url: 'https://colaboracion.dnp.gov.co/CDT/Conpes/',
      desc: 'Repositorio completo de documentos CONPES (Consejo Nacional de Política Económica y Social). El instrumento por excelencia de política pública nacional en Colombia.',
      modulos: ['problema', 'estructural', 'evaluacion', 'alternativas', 'ain']
    },
    {
      id: 'sisconpes', categoria: 'co-pp',
      nombre: 'SISCONPES · Sistema de Seguimiento',
      url: 'https://sisconpes.dnp.gov.co/SisCONPESWeb/',
      desc: 'Tablero de seguimiento del avance de las acciones CONPES vigentes. Útil para entender qué políticas están activas y en qué fase.',
      modulos: ['problema', 'evaluacion', 'alternativas', 'ain']
    },
    {
      id: 'sinergia', categoria: 'co-pp',
      nombre: 'SINERGIA · Sistema Nacional de Evaluación',
      url: 'https://sinergia.dnp.gov.co/',
      desc: 'Plataforma del DNP con evaluaciones de política pública e indicadores de seguimiento al Plan Nacional de Desarrollo.',
      modulos: ['evaluacion', 'problema']
    },
    {
      id: 'dnp', categoria: 'co-pp',
      nombre: 'DNP · Departamento Nacional de Planeación',
      url: 'https://www.dnp.gov.co/',
      desc: 'Sitio central del DNP: marco fiscal, guías metodológicas, KPT (Kit del Plan Territorial), instrumentos de planeación territorial.',
      modulos: ['problema', 'estructural', 'evaluacion', 'ain']
    },
    {
      id: 'dnp-kpt', categoria: 'co-pp',
      nombre: 'DNP · Kit del Plan Territorial (KPT)',
      url: 'https://kpt.dnp.gov.co/',
      desc: 'Caja de herramientas oficial para alcaldías y gobernaciones que construyen su Plan de Desarrollo Territorial. Incluye diagnósticos y formatos.',
      modulos: ['problema', 'estructural', 'alternativas', 'ain']
    },
    {
      id: 'kp-dnp', categoria: 'co-pp',
      nombre: 'DNP · Banco de Programas y Proyectos',
      url: 'https://proyectostipo.dnp.gov.co/',
      desc: 'Proyectos tipo del DNP: alternativas estandarizadas de intervención por sector. Útil para construir alternativas concretas y costos referenciales.',
      modulos: ['problema', 'alternativas']
    },

    // ─── Colombia · Datos abiertos ─────────────────────────────────────────
    {
      id: 'dane', categoria: 'co-datos',
      nombre: 'DANE · Departamento Administrativo Nacional de Estadística',
      url: 'https://www.dane.gov.co/',
      desc: 'Estadísticas oficiales: censo, calidad de vida, mercado laboral, pobreza, geoestadísticas, proyecciones poblacionales.',
      modulos: ['problema', 'estructural', 'evaluacion']
    },
    {
      id: 'terridata', categoria: 'co-datos',
      nombre: 'TerriData · Indicadores territoriales',
      url: 'https://terridata.dnp.gov.co/',
      desc: 'Indicadores territoriales del DNP a nivel municipal y departamental. ~700 indicadores estandarizados con fichas técnicas.',
      modulos: ['problema', 'estructural']
    },
    {
      id: 'datos-gov', categoria: 'co-datos',
      nombre: 'Datos.gov.co · Datos Abiertos Colombia',
      url: 'https://www.datos.gov.co/',
      desc: 'Portal oficial de datos abiertos del Estado colombiano. Datasets de todas las entidades nacionales y muchas territoriales.',
      modulos: ['problema', 'estructural', 'evaluacion']
    },
    {
      id: 'banrep', categoria: 'co-datos',
      nombre: 'Banco de la República · Estadísticas',
      url: 'https://www.banrep.gov.co/es/estadisticas',
      desc: 'Series de tiempo macroeconómicas: tasas, inflación, cuentas nacionales, sector externo, mercado financiero.',
      modulos: ['problema', 'estructural']
    },
    {
      id: 'secop', categoria: 'co-datos',
      nombre: 'SECOP · Contratación Pública',
      url: 'https://www.colombiacompra.gov.co/secop/secop-ii',
      desc: 'Sistema Electrónico de Contratación Pública. Toda la contratación del Estado colombiano. Útil para mapear actores y dimensionar costos reales.',
      modulos: ['mactor', 'problema']
    },
    {
      id: 'registraduria', categoria: 'co-datos',
      nombre: 'Registraduría Nacional · Resultados electorales',
      url: 'https://www.registraduria.gov.co/',
      desc: 'Resultados electorales históricos por mesa, puesto, municipio y departamento. Base para análisis de comportamiento político.',
      modulos: ['mactor']
    },
    {
      id: 'mineduc-snies', categoria: 'co-datos',
      nombre: 'MEN · SNIES (educación superior)',
      url: 'https://snies.mineducacion.gov.co/portal/',
      desc: 'Sistema Nacional de Información de Educación Superior: matrícula, oferta, graduados, instituciones.',
      modulos: ['problema']
    },
    {
      id: 'sispro', categoria: 'co-datos',
      nombre: 'MinSalud · SISPRO',
      url: 'https://www.sispro.gov.co/',
      desc: 'Sistema integral de información de salud: aseguramiento, prestaciones, eventos en salud pública, mortalidad.',
      modulos: ['problema']
    },
    {
      id: 'policia-stats', categoria: 'co-datos',
      nombre: 'Policía Nacional · Información criminalidad',
      url: 'https://www.policia.gov.co/grupo-informacion-criminalidad',
      desc: 'Estadísticas de hechos delictivos por tipología, municipio y período. Microdatos para análisis territorial.',
      modulos: ['problema', 'estructural']
    },

    // ─── Evaluación de política ────────────────────────────────────────────
    {
      id: 'ivalua', categoria: 'evaluacion',
      nombre: 'Ivàlua · Institut Català d\'Avaluació',
      url: 'https://www.ivalua.cat/',
      desc: 'Instituto público catalán especializado en evaluación de políticas. Guías metodológicas libres y ejemplos reales.',
      modulos: ['evaluacion']
    },
    {
      id: '3ie', categoria: 'evaluacion',
      nombre: '3ie · International Initiative for Impact Evaluation',
      url: 'https://www.3ieimpact.org/',
      desc: 'Repositorio global de evaluaciones de impacto rigurosas en desarrollo. Útil para benchmarks y referentes metodológicos.',
      modulos: ['evaluacion']
    },
    {
      id: 'egap', categoria: 'evaluacion',
      nombre: 'EGAP · Method Guides',
      url: 'https://egap.org/methods-guides/',
      desc: 'Guías abiertas de métodos para evaluación experimental y cuasi-experimental en política pública. Lenguaje accesible.',
      modulos: ['evaluacion']
    },
    {
      id: 'wb-dime', categoria: 'evaluacion',
      nombre: 'World Bank · DIME (Development Impact)',
      url: 'https://www.worldbank.org/en/research/dime',
      desc: 'Iniciativa de evaluación de impacto del Banco Mundial. Notas técnicas, datos replicables y casos de aplicación.',
      modulos: ['evaluacion']
    },
    {
      id: 'oecd-dac', categoria: 'evaluacion',
      nombre: 'OCDE · Criterios DAC de evaluación',
      url: 'https://www.oecd.org/dac/evaluation/daccriteriaforevaluatingdevelopmentassistance.htm',
      desc: 'Los 6 criterios canónicos para evaluar política pública: relevancia, coherencia, efectividad, eficiencia, impacto, sostenibilidad.',
      modulos: ['evaluacion', 'problema']
    },

    // ─── Diseño de política y participación ────────────────────────────────
    {
      id: 'uk-opm', categoria: 'diseno',
      nombre: 'UK · Open Policy Making toolkit',
      url: 'https://www.gov.uk/guidance/open-policy-making-toolkit',
      desc: 'Toolkit del gobierno británico para diseño abierto de política. Métodos de diagnóstico participativo y prototipado.',
      modulos: ['problema', 'mactor', 'alternativas']
    },
    {
      id: 'service-design', categoria: 'diseno',
      nombre: 'Service Design Tools',
      url: 'https://servicedesigntools.org/',
      desc: 'Caja de herramientas de diseño de servicios públicos: mapas de viaje del usuario, blueprints, journey mapping.',
      modulos: ['problema', 'alternativas']
    },
    {
      id: 'bi-team', categoria: 'diseno',
      nombre: 'Behavioural Insights Team',
      url: 'https://www.bi.team/',
      desc: 'Instituto pionero en aplicar economía conductual al diseño de política pública. Publicaciones libres con casos reales.',
      modulos: ['problema', 'evaluacion', 'alternativas', 'ain']
    },
    {
      id: 'cepal-ilpes', categoria: 'diseno',
      nombre: 'CEPAL · ILPES (Planificación)',
      url: 'https://www.cepal.org/es/ilpes',
      desc: 'Instituto Latinoamericano y del Caribe de Planificación. Manuales de marco lógico, prospectiva, planificación estratégica.',
      modulos: ['problema', 'estructural', 'evaluacion', 'alternativas', 'ain']
    },

    // ─── Prospectiva y método ──────────────────────────────────────────────
    {
      id: 'lipsor', categoria: 'prospectiva',
      nombre: 'LIPSOR · Laboratoire d\'Investigation en Prospective',
      url: 'http://en.laprospective.fr/',
      desc: 'Laboratorio fundado por Michel Godet (CNAM, París). Software libre (MicMac, Mactor, MorPhol, MultiPol) + publicaciones sobre prospectiva estratégica. MorPhol implementa el análisis morfológico de Zwicky.',
      modulos: ['estructural', 'mactor', 'alternativas', 'prospect']
    },
    {
      id: 'externado-cipe', categoria: 'prospectiva',
      nombre: 'Externado · Centro de Pensamiento Estratégico Internacional',
      url: 'https://www.uexternado.edu.co/centros-de-pensamiento/',
      desc: 'Referente colombiano en prospectiva estratégica. Tradición de Francisco José Mojica (formado con Godet en la Sorbona). Publicaciones de referencia para política pública colombiana.',
      modulos: ['estructural', 'mactor', 'prospect']
    },
    {
      id: 'foresight-cards', categoria: 'prospectiva',
      nombre: 'Future Today Institute · Foresight Toolkit',
      url: 'https://futuretodayinstitute.com/',
      desc: 'Caja de herramientas contemporánea de prospectiva (escenarios, señales débiles, futuros alternativos). Reportes anuales de tendencias.',
      modulos: ['estructural', 'alternativas', 'prospect']
    },
    {
      id: 'rand-rdm', categoria: 'prospectiva',
      nombre: 'RAND · Robust Decision Making',
      url: 'https://www.rand.org/methods/rdm.html',
      desc: 'Página oficial de Robust Decision Making (Lempert · Walker · Bankes 2003). Marco para decidir bajo incertidumbre profunda mediante escenarios y rangos en lugar de pronósticos puntuales. Esencial para identificar decisiones no-regret.',
      modulos: ['alternativas', 'estructural', 'prospect']
    },
    {
      id: 'schwartz-gbn', categoria: 'prospectiva',
      nombre: 'Schwartz · The Art of the Long View (GBN)',
      url: 'https://en.wikipedia.org/wiki/Peter_Schwartz_(futurist)',
      desc: 'Peter Schwartz · Global Business Network (1991). Método de los ejes de incertidumbre: 2 incertidumbres críticas → 4 escenarios narrados. Estándar corporativo y de planificación pública desde Shell hasta CIA.',
      modulos: ['prospect']
    },
    {
      id: 'gordon-cross-impact', categoria: 'prospectiva',
      nombre: 'Cross-Impact Analysis · Gordon & Hayward 1968',
      url: 'https://www.millennium-project.org/projects/cross-impact-analysis/',
      desc: 'Cross-Impact Analysis original (Theodore Gordon, RAND 1968). Mide cómo la ocurrencia de un evento altera la probabilidad de otros. Base metodológica del cross-impact por escenarios usado en Sprint F.',
      modulos: ['prospect', 'mactor']
    },
    {
      id: 'mojica-prospectiva', categoria: 'prospectiva',
      nombre: 'Mojica · Concepto y aplicación de la prospectiva estratégica',
      url: 'https://revistas.uexternado.edu.co/index.php/sotavento/article/view/1601',
      desc: 'Francisco José Mojica (Externado · Sorbona). Adaptación latinoamericana del método Godet, aplicado a Colombia. Lectura obligada para entender por qué los CONPES de prospectiva en Colombia siguen esta tradición.',
      modulos: ['prospect', 'estructural', 'mactor']
    },
    {
      id: 'policyimpacts-mvpf', categoria: 'evaluacion',
      nombre: 'Policy Impacts · Base pública MVPF',
      url: 'https://policyimpacts.org/',
      desc: 'Base abierta del Harvard Opportunity Insights con MVPF (Marginal Value of Public Funds, Hendren & Sprung-Keyser NBER 2020) calculados para cientos de políticas en EEUU. Referencia metodológica.',
      modulos: ['alternativas', 'evaluacion']
    },
    {
      id: 'jpal-cea', categoria: 'evaluacion',
      nombre: 'J-PAL · Cost-Effectiveness Analysis',
      url: 'https://www.povertyactionlab.org/page/cost-effectiveness-and-welfare-analysis',
      desc: 'Recursos de J-PAL sobre análisis de costo-efectividad: guías, plantillas, base comparativa de evaluaciones de impacto. Útil cuando los beneficios no son monetizables.',
      modulos: ['alternativas', 'evaluacion']
    },
    {
      id: 'ocde-ria', categoria: 'evaluacion',
      nombre: 'OCDE · Regulatory Impact Assessment',
      url: 'https://www.oecd.org/regreform/regulatory-impact-analysis.htm',
      desc: 'Página oficial de la OCDE sobre Regulatory Impact Assessment (RIA): manuales, casos comparativos por país, índice global de Regulatory Policy and Governance. Marco internacional del AIN.',
      modulos: ['ain', 'evaluacion']
    },
    {
      id: 'funcion-publica-ain', categoria: 'co-pp',
      nombre: 'Función Pública · AIN Colombia',
      url: 'https://www.funcionpublica.gov.co/web/eva/gestor-normativo',
      desc: 'Gestor Normativo y portal SUCOP de Función Pública. Decreto 1081/2015 + Decreto 1273/2020 sobre proyectos normativos y consulta pública. Guía oficial colombiana del Análisis de Impacto Normativo.',
      modulos: ['ain', 'problema']
    }
  ]
};
