/* lab-demo.js · caso de ejemplo del Lab de Políticas Públicas (oct-2026)
 *
 * UN solo caso, coherente en los 8 módulos, para que quien llega al Lab pueda
 * ver cada módulo LLENO en diez segundos en vez de inventarse un problema.
 * Caso: deserción escolar en grados 9-11 de colegios oficiales de Bogotá.
 *
 * ⚠ Las cifras son ILUSTRATIVAS (verosímiles, no oficiales) y cada enunciado
 *   empieza con «[Ejemplo]» para que ningún memo exportado pase por real.
 * ⚠ Escribe los 8 estados en localStorage con las MISMAS claves que usa cada
 *   módulo. Si un módulo cambia el shape de su STATE, hay que tocar esto.
 *
 * API: window.LabDemo = { cargar({abrir, confirmar}), limpiar(), activo(), hayContenido(), KEYS, HREF, TITULO }
 */
(function () {
  'use strict';

  const KEYS = {
    pp:        'pp-current-v1',
    micmac:    'micmac-current-v2',
    mactor:    'mactor-current-v1',
    ev:        'ev-current-v1',
    alt:       'alt-current-v1',
    ain:       'ain-current-v1',
    prospect:  'prospect-current-v1',
    comunicar: 'comunicar-current-v1'
  };
  const HREF = {
    pp:        'problema-publico.html',
    micmac:    'analisis-estructural.html#estructural',
    mactor:    'mactor.html',
    ev:        'evaluacion.html',
    alt:       'alternativas.html',
    ain:       'ain.html',
    prospect:  'prospect-escenarios.html',
    comunicar: 'comunicar.html'
  };
  const FLAG = 'lab-demo-loaded';
  const TITULO = 'Deserción escolar en grados 9-11 · Bogotá (caso de ejemplo)';
  const ENUNCIADO = '[Ejemplo] La deserción escolar en los grados 9 a 11 de los colegios oficiales de Bogotá subió de 8,1 % a 12,3 % entre 2021 y 2024, concentrada en Ciudad Bolívar, Usme, Bosa y San Cristóbal, y supera la meta del Plan de Desarrollo Distrital.';

  // ───────────────────────── 1 · Problema público ─────────────────────────
  function pp() {
    const alternativas = [
      { nombre: 'No hacer nada (baseline)', desc: 'Mantener la oferta actual: jornada única parcial y PAE sin acompañamiento en media.', supuestos: 'La deserción sigue la tendencia 2021-2024 (+1,4 pp por año).', costo: '$0 adicional', plazo: '—', baseline: true },
      { nombre: 'Transferencia condicionada a asistencia (9-11)', desc: 'Subsidio mensual a la familia del estudiante de 9-11 en 4 localidades, condicionado a asistencia ≥ 90 %.', supuestos: 'La restricción económica del hogar es la causa principal; la Secretaría puede verificar asistencia con SIMAT mensual.', costo: '$1.480 millones / año', plazo: '12 meses' },
      { nombre: 'Tutoría y acompañamiento psicosocial en colegio', desc: 'Un orientador adicional por cada 400 estudiantes de media + tutorías de pares en contrajornada.', supuestos: 'El rezago académico y los problemas de convivencia pesan tanto como el ingreso; hay oferta de orientadores en el mercado.', costo: '$2.100 millones / año', plazo: '18 meses' },
      { nombre: 'Media técnica articulada con el SENA', desc: 'Doble titulación en 9-11 con práctica remunerada en el último año, en los 40 colegios de mayor deserción.', supuestos: 'La expectativa de empleo temprano retiene; el SENA tiene cupos y los colegios infraestructura mínima.', costo: '$3.300 millones / año', plazo: '24 meses' }
    ];
    const criterios = [
      { nombre: 'Eficiencia', peso: 20 }, { nombre: 'Equidad', peso: 25 }, { nombre: 'Factibilidad política', peso: 15 },
      { nombre: 'Costo', peso: 20 }, { nombre: 'Sostenibilidad', peso: 20 }
    ];
    // filas = alternativas (0..3) · columnas = criterios (0..4) · valores 1-5
    const tabla = [
      [1, 1, 4, 5, 2],
      [4, 5, 3, 3, 3],
      [4, 4, 4, 3, 4],
      [3, 3, 2, 2, 5]
    ];
    const scores = {};
    tabla.forEach((fila, ai) => fila.forEach((v, ci) => { scores[ai + '-' + ci] = v; }));
    return {
      step: 5,
      sintoma: { sintoma: 'Muchos estudiantes de décimo y once dejan el colegio antes de graduarse', quienes: 'estudiantes de colegios oficiales en Ciudad Bolívar, Usme, Bosa y San Cristóbal', cuando: 'desde 2021, +4,2 pp en tres años', evidencia: 'SIMAT 2024 · Secretaría de Educación del Distrito (cifra ilustrativa)' },
      diagnostico: { rittel: [true, true, false, true, true, false, true, false, false, true], marco: 'multicriterio' },
      definicion: {
        enunciado: ENUNCIADO, magnitud: '12,3 % de deserción · ≈ 9.800 estudiantes por año', urgencia: 'alta',
        afectados: ['Estudiantes de 14 a 17 años de estratos 1 y 2', 'Familias con jefatura femenina y empleo informal', 'Colegios oficiales de Ciudad Bolívar, Usme, Bosa y San Cristóbal'],
        evidenciaInicial: 'SIMAT 2024 y Encuesta Multipropósito 2023 (cifras ilustrativas)',
        causas: ['Necesidad de ingreso del hogar', 'Rezago académico acumulado desde la pandemia', 'Embarazo adolescente y cuidado de hermanos', 'Inseguridad en el entorno escolar'],
        efectos: ['Menor ingreso laboral a lo largo de la vida', 'Mayor exposición a reclutamiento y violencia', 'Caída de la cobertura en educación superior']
      },
      evidencia: [
        { fuente: 'SIMAT · Secretaría de Educación del Distrito', anyo: '2024', dato: 'Deserción intraanual 9-11: 12,3 % (8,1 % en 2021)', link: 'https://www.educacionbogota.edu.co', nota: 'Cifra ilustrativa para el caso de ejemplo.' },
        { fuente: 'Encuesta Multipropósito Bogotá · DANE-SDP', anyo: '2023', dato: '61 % de los jóvenes que desertaron citan «necesidad de trabajar»', link: 'https://www.sdp.gov.co', nota: 'Cifra ilustrativa.' },
        { fuente: 'Pruebas Saber 9 · ICFES', anyo: '2023', dato: 'Brecha de 48 puntos entre colegios oficiales de las 4 localidades y el promedio distrital', link: 'https://www.icfes.gov.co', nota: 'Cifra ilustrativa.' },
        { fuente: 'Observatorio de Convivencia Escolar', anyo: '2024', dato: '27 % de los estudiantes de media reporta sentirse inseguro en el trayecto al colegio', link: '', nota: 'Cifra ilustrativa.' }
      ],
      alternativas, criterios, scores
    };
  }

  // ───────────────────────── 2 · Análisis estructural (MicMac) ─────────────────────────
  function micmac() {
    const vars = [
      'Ingreso del hogar', 'Rezago académico', 'Embarazo adolescente', 'Inseguridad en el entorno',
      'Oferta de media técnica', 'Acompañamiento psicosocial', 'Expectativa de empleo', 'Deserción 9-11'
    ];
    // Fila i influye sobre columna j · '-' diagonal · 0-3 · '-2' = inhibe
    const M = [
      ['-', '2', '2', '1', '0', '0', '2', '3'],
      ['0', '-', '1', '0', '1', '0', '2', '3'],
      ['1', '2', '-', '0', '0', '1', '1', '3'],
      ['1', '2', '1', '-', '0', '0', '1', '2'],
      ['1', '-2', '0', '0', '-', '1', '3', '-3'],
      ['0', '-2', '-2', '0', '0', '-', '1', '-2'],
      ['1', '1', '0', '0', '1', '0', '-', '-2'],
      ['2', '1', '1', '1', '0', '0', '1', '-']
    ];
    const now = new Date().toISOString();
    return {
      wizard: { q1: 'planeacion', q2: 'politica', q3: 'mixto', q4: 'educacion', tpl: null, step: 4 },
      meta: { tplId: null, nombre: TITULO, createdAt: now, updatedAt: now },
      vars, matrix: M, captureIdx: vars.length * (vars.length - 1), mode: 'table', uncertainty: 'medium'
    };
  }

  // ───────────────────────── 3 · Actores (Mactor) ─────────────────────────
  function mactor() {
    const actores = ['Secretaría de Educación', 'Concejo de Bogotá', 'Rectores y docentes', 'Familias y asociaciones de padres', 'SENA', 'Secretaría de Hacienda', 'Organizaciones juveniles'];
    const objetivos = ['Subsidio condicionado a asistencia', 'Orientador adicional por colegio', 'Media técnica con el SENA', 'Focalizar en 4 localidades', 'Evaluación de impacto independiente'];
    const mid = [
      ['-', '2', '3', '2', '2', '2', '1'],
      ['2', '-', '1', '1', '0', '3', '1'],
      ['1', '1', '-', '2', '1', '0', '2'],
      ['1', '2', '2', '-', '0', '0', '2'],
      ['1', '0', '2', '1', '-', '0', '1'],
      ['3', '2', '0', '0', '1', '-', '0'],
      ['1', '1', '1', '2', '0', '0', '-']
    ];
    const mao = [
      ['3', '3', '4', '3', '2'],
      ['2', '1', '3', '-1', '3'],
      ['1', '4', '2', '2', '-1'],
      ['4', '3', '3', '-2', '1'],
      ['0', '0', '4', '1', '1'],
      ['-3', '-2', '-1', '3', '2'],
      ['3', '2', '2', '1', '3']
    ];
    const now = new Date().toISOString();
    return { wizard: { tpl: null }, meta: { tplId: null, nombre: TITULO, createdAt: now, updatedAt: now }, actores, objetivos, mid, mao };
  }

  // ───────────────────────── 4 · Alternativas (morfológico + RDM) ─────────────────────────
  function alt() {
    const variables = [
      { id: 'v-instr', nombre: 'Instrumento', tipo: 'instrumento' },
      { id: 'v-cob',   nombre: 'Cobertura', tipo: 'cobertura' },
      { id: 'v-cond',  nombre: 'Condicionalidad', tipo: 'condicionalidad' },
      { id: 'v-gob',   nombre: 'Gobernanza', tipo: 'gobernanza' }
    ];
    const opciones = {
      'v-instr': ['Transferencia monetaria', 'Acompañamiento psicosocial', 'Media técnica con práctica'],
      'v-cob':   ['Universal en Bogotá', 'Focalizada en 4 localidades', 'Solo 40 colegios críticos'],
      'v-cond':  ['Sin condición', 'Asistencia ≥ 90 %', 'Asistencia + promoción de grado'],
      'v-gob':   ['Centralizada en la SED', 'Cogestionada con rectores', 'Operador externo']
    };
    const incompat = [['v-instr:2', 'v-cob:0'], ['v-instr:0', 'v-cond:0']];
    const alternativas = [
      { id: 'alt-base', nombre: 'Statu quo', desc: 'No hacer nada / mantener la política actual. Baseline contra el que se comparan las demás alternativas.', supuestos: '', costo: '', plazo: '', combo: {}, baseline: true, econ: { costo_total: '', beneficio_total: '', unidad_outcome: '', outcome_total: '' } },
      { id: 'alt-tmc', nombre: 'Transferencia focalizada y condicionada', desc: 'Subsidio mensual a familias de 9-11 en 4 localidades, condicionado a asistencia ≥ 90 %, operado por la SED.', supuestos: 'La restricción de ingreso es la causa dominante.', costo: '$1.480 millones / año', plazo: '12 meses', combo: { 'v-instr': 0, 'v-cob': 1, 'v-cond': 1, 'v-gob': 0 }, baseline: false, econ: { costo_total: '1480000000', beneficio_total: '2650000000', unidad_outcome: 'estudiantes retenidos', outcome_total: '1150' } },
      { id: 'alt-psico', nombre: 'Acompañamiento cogestionado en 40 colegios', desc: 'Orientador adicional y tutoría de pares en los 40 colegios de mayor deserción, gestionado con rectores.', supuestos: 'El rezago y la convivencia pesan tanto como el ingreso.', costo: '$2.100 millones / año', plazo: '18 meses', combo: { 'v-instr': 1, 'v-cob': 2, 'v-cond': 0, 'v-gob': 1 }, baseline: false, econ: { costo_total: '2100000000', beneficio_total: '2900000000', unidad_outcome: 'estudiantes retenidos', outcome_total: '1300' } },
      { id: 'alt-sena', nombre: 'Media técnica con práctica remunerada', desc: 'Doble titulación con el SENA y práctica pagada en el último año, en 40 colegios, con operador externo.', supuestos: 'La expectativa de empleo retiene en 10-11.', costo: '$3.300 millones / año', plazo: '24 meses', combo: { 'v-instr': 2, 'v-cob': 2, 'v-cond': 2, 'v-gob': 2 }, baseline: false, econ: { costo_total: '3300000000', beneficio_total: '4100000000', unidad_outcome: 'estudiantes retenidos', outcome_total: '1600' } }
    ];
    const escenarios = [
      { id: 'baseline',   nombre: 'Baseline',   descripcion: 'Tendencia base: presupuesto distrital estable, mercado laboral juvenil sin cambios.', prob: 40 },
      { id: 'optimista',  nombre: 'Optimista',  descripcion: 'Crecimiento económico, cupos SENA ampliados, coalición estable en el Concejo.', prob: 25 },
      { id: 'pesimista',  nombre: 'Pesimista',  descripcion: 'Recorte fiscal distrital del 15 %, rotación de rectores, oposición al subsidio.', prob: 25 },
      { id: 'disruptivo', nombre: 'Disruptivo', descripcion: 'Choque externo: nueva crisis sanitaria o migratoria que dispara la demanda de cupos.', prob: 10 }
    ];
    const ratings = {
      'alt-base':  { baseline: 1, optimista: 2, pesimista: 1, disruptivo: 1 },
      'alt-tmc':   { baseline: 4, optimista: 4, pesimista: 2, disruptivo: 3 },
      'alt-psico': { baseline: 4, optimista: 4, pesimista: 3, disruptivo: 4 },
      'alt-sena':  { baseline: 3, optimista: 5, pesimista: 2, disruptivo: 2 }
    };
    return {
      step: 6,
      contexto: { enunciado_problema: ENUNCIADO, dep_cod: '11', mun_cod: '11001', sector: 'educacion', importedFromPP: true },
      variables, opciones, incompat, alternativas, escenarios, ratings,
      decision: { altId_recomendada: 'alt-psico', justificacion: 'Es la única alternativa con peor caso ≥ 3: aguanta el recorte fiscal y el choque externo. La transferencia rinde más en el baseline pero se cae en el escenario pesimista; la media técnica depende de los cupos del SENA.' }
    };
  }

  // ───────────────────────── 5 · Análisis de Impacto Normativo ─────────────────────────
  function ain() {
    const opciones = [
      { id: 'op-sq',   nombre: 'Statu quo', tipo: 'statu-quo', desc: 'Mantener el Acuerdo distrital vigente de permanencia escolar sin condicionar recursos a resultados.', supuestos: '', baseline: true, importedFromAlt: false },
      { id: 'op-dec',  nombre: 'Decreto distrital de permanencia 9-11', tipo: 'regular', desc: 'Norma que crea el programa de acompañamiento, fija la focalización en 40 colegios y obliga reporte mensual en SIMAT.', supuestos: 'La SED tiene capacidad de reglamentar y de verificar.', baseline: false, importedFromAlt: true },
      { id: 'op-coreg', nombre: 'Co-regulación con rectores', tipo: 'co-regulacion', desc: 'Protocolo acordado con los consejos directivos; la SED fija metas y los colegios eligen el medio.', supuestos: 'Los rectores tienen incentivos a reportar bien.', baseline: false, importedFromAlt: false },
      { id: 'op-sand', nombre: 'Piloto regulatorio (sandbox) en 10 colegios', tipo: 'sandbox', desc: 'Excepción temporal de 18 meses para probar el acompañamiento con evaluación independiente antes de la norma general.', supuestos: 'Se acepta escalar solo con evidencia.', baseline: false, importedFromAlt: false }
    ];
    return {
      step: 6,
      contexto: { enunciado_problema: ENUNCIADO, dep_cod: '11', mun_cod: '11001', sector: 'educacion', instrumento_norm: 'decreto distrital', importedFromPP: true, importedFromAlt: true },
      problema_reg: { enunciado: '[Ejemplo] Los colegios oficiales de media en las 4 localidades no tienen obligación ni incentivo de reportar y atender el riesgo de deserción individual; el dato llega a la SED al cierre del año, cuando el estudiante ya se fue.', tipo_falla: 'coordinacion', afectados: ['Estudiantes de 9-11 en riesgo', 'Rectores y orientadores', 'Secretaría de Educación'], evidencia_inicial: 'SIMAT 2024: 12,3 % de deserción 9-11 (cifra ilustrativa); el reporte es anual y agregado.' },
      objetivos: [
        { id: 'ob-1', enunciado: 'Bajar la deserción 9-11 en las 4 localidades', indicador: 'Tasa de deserción intraanual SIMAT', meta: '≤ 8 %', plazo: '2027' },
        { id: 'ob-2', enunciado: 'Detectar el riesgo individual a tiempo', indicador: '% de estudiantes con alerta temprana atendida en < 30 días', meta: '≥ 80 %', plazo: '2026' },
        { id: 'ob-3', enunciado: 'No aumentar la carga administrativa de los colegios', indicador: 'Horas/mes de reporte por colegio', meta: '≤ 4 h', plazo: '2026' }
      ],
      opciones,
      impactos: {
        'op-sq':    { costos_directos: 'bajo', costos_indirectos: 'alto', beneficios: 'bajo', captura: 'bajo', carga_admin: 'bajo' },
        'op-dec':   { costos_directos: 'medio', costos_indirectos: 'bajo', beneficios: 'alto', captura: 'bajo', carga_admin: 'medio' },
        'op-coreg': { costos_directos: 'bajo', costos_indirectos: 'medio', beneficios: 'medio', captura: 'medio', carga_admin: 'bajo' },
        'op-sand':  { costos_directos: 'medio', costos_indirectos: 'bajo', beneficios: 'medio', captura: 'bajo', carga_admin: 'medio' }
      },
      consulta: { plan: 'Publicación del proyecto de decreto 15 días en la web de la SED, mesa técnica con rectores de las 4 localidades y audiencia pública con asociaciones de padres y organizaciones juveniles.', audiencias: ['Rectores y consejos directivos', 'Asociaciones de padres', 'Organizaciones juveniles', 'Sindicato docente (ADE)', 'Concejo de Bogotá'], instrumentos: ['consulta-web', 'mesa-tecnica', 'audiencia-publica'], cronograma: 'Consulta web: mes 1 · mesas técnicas: mes 2 · audiencia: mes 3 · expedición: mes 4.' },
      riesgo_reg: { captura: 'bajo', asimetria: 'medio', carga_excesiva: 'medio', fragmentacion: 'alto', obsolescencia: 'bajo' },
      implementacion: { cronograma: 'Reglamentación en 4 meses · contratación de orientadores en 6 · primer reporte mensual en SIMAT en el mes 7.', responsables: 'Dirección de Cobertura de la SED (líder) · rectores (reporte) · Secretaría de Hacienda (recursos).', presupuesto: '$2.100 millones / año (cifra ilustrativa).', indicadores_monitoreo: 'Tasa de deserción 9-11 mensual · % de alertas atendidas en < 30 días · horas de reporte por colegio.', clausula_revision: 'Revisión a los 24 meses con evaluación independiente; si la deserción no baja al menos 2 pp, se reabre la opción de sandbox.' },
      recomendacion: { opcionId_recomendada: 'op-dec', justificacion: 'Es la única opción que resuelve la falla de coordinación (reporte mensual obligatorio) con beneficios altos y captura baja; la carga administrativa media se mitiga con el formulario único en SIMAT.' }
    };
  }

  // ───────────────────────── 6 · Evaluación de política ─────────────────────────
  function ev() {
    return {
      step: 7,
      pregunta: { tipo: 'causal', alcance: 'ex-post', enunciado: '[Ejemplo] ¿El programa de acompañamiento psicosocial en 40 colegios redujo la deserción en grados 9-11 respecto a los colegios comparables que no lo recibieron?', subpreguntas: ['¿El efecto es mayor en los colegios que lo recibieron primero?', '¿Cambió la asistencia antes que la deserción?', '¿Hay efectos distintos por sexo y por grado?'], tipo_sinergia: 'impacto' },
      teoria: {
        insumos: ['40 orientadores adicionales', '$2.100 millones / año', 'Datos SIMAT mensuales'],
        actividades: ['Alertas tempranas por inasistencia', 'Tutorías de pares en contrajornada', 'Visitas a familias en riesgo'],
        productos: ['1.600 estudiantes con plan de acompañamiento', '180 talleres por año', '% de alertas atendidas en < 30 días'],
        resultados: ['Asistencia ≥ 90 % sostenida', 'Promoción de grado 9 → 10 → 11'],
        impacto: ['Deserción 9-11 ≤ 8 % en las 4 localidades'],
        supuestos: ['Los colegios reportan la inasistencia a tiempo', 'Las familias aceptan la visita', 'No hay un choque económico que domine el efecto']
      },
      indicadores: [
        { nivel: 'productos',  nombre: 'Estudiantes con plan de acompañamiento activo', def: 'Estudiantes de 9-11 con alerta y plan registrado en el sistema', formula: '# estudiantes con plan vigente', fuente: 'Sistema del programa', base: '0', meta: '1.600 al cierre de 2026', frecuencia: 'mensual' },
        { nivel: 'productos',  nombre: 'Alertas atendidas en menos de 30 días', def: 'Alertas de inasistencia con primera acción en < 30 días', formula: '(alertas atendidas < 30 d / alertas) × 100', fuente: 'Sistema del programa', base: '—', meta: '≥ 80 %', frecuencia: 'mensual' },
        { nivel: 'resultados', nombre: 'Tasa de asistencia escolar', def: '% de días asistidos sobre días lectivos', formula: '(días asistidos / días lectivos) × 100', fuente: 'SIMAT', base: '78 %', meta: '≥ 90 %', frecuencia: 'trimestral' },
        { nivel: 'impacto',    nombre: 'Tasa de deserción anual 9-11', def: 'Matriculados al inicio que no terminan el año', formula: '(desertores / matrícula inicial) × 100', fuente: 'SIMAT', base: '12,3 %', meta: '≤ 8 % en 2027', frecuencia: 'anual' }
      ],
      metodo: { id: 'did-staggered', justificacion: 'El programa entra por tandas (10 colegios cada semestre), así que el DID clásico con TWFE sesgaría la estimación; se usa Callaway-Sant\'Anna con los colegios aún no tratados como control.', tratamiento_escalonado: 'si' },
      dac: { relevance: 'Responde a la meta del Plan de Desarrollo Distrital y a la causa que más citan las familias.', coherence: 'Complementa el PAE y la jornada única; no duplica el subsidio de transporte.', effectiveness: 'Se mide con la deserción intraanual y la asistencia, ambas en SIMAT.', efficiency: 'Costo por estudiante retenido estimado en $1,6 millones (cifra ilustrativa).', impact: 'Efecto sobre deserción y promoción de grado a 24 meses.', sustainability: 'Depende de que los orientadores pasen a planta tras el piloto.' },
      economico: { activo: true, cba: { costos_total: '4200000000', beneficios_total: '5800000000', tasa_descuento: '9', horizonte_anios: '10', weights_distrib: '' }, mvpf: { beneficios_receptores: '5800000000', costo_neto_gob: '3900000000' }, cea: { costo_total: '4200000000', outcome_unidad: 'estudiante retenido', outcome_total: '2600' } },
      plan: { cronograma: 'Línea base: semestre 1 de 2026 · seguimiento trimestral · corte de impacto: diciembre de 2027.', equipo: 'Evaluador externo (universidad) con 2 investigadores al 50 % + enlace de la SED al 20 %.', presupuesto: '$320 millones (cifra ilustrativa).', uso: 'Comité de permanencia escolar de la SED decide en 2028 si el programa pasa a planta o se rediseña.' }
    };
  }

  // ───────────────────────── 7 · Escenarios prospectivos ─────────────────────────
  function prospect() {
    const elementos = [
      { id: 'el-ingreso', tipo: 'variable', nombre: 'Ingreso del hogar', source: 'micmac' },
      { id: 'el-rezago',  tipo: 'variable', nombre: 'Rezago académico', source: 'micmac' },
      { id: 'el-sed',     tipo: 'actor', nombre: 'Secretaría de Educación', source: 'mactor' },
      { id: 'el-hda',     tipo: 'actor', nombre: 'Secretaría de Hacienda', source: 'mactor' },
      { id: 'el-tmc',     tipo: 'alternativa', nombre: 'Transferencia focalizada y condicionada', source: 'alt' },
      { id: 'el-psico',   tipo: 'alternativa', nombre: 'Acompañamiento cogestionado en 40 colegios', source: 'alt' },
      { id: 'el-sena',    tipo: 'alternativa', nombre: 'Media técnica con práctica remunerada', source: 'alt' }
    ];
    return {
      step: 4,
      contexto: { enunciado_problema: ENUNCIADO, importedFromPP: true },
      ejes: {
        x: { nombre: 'Mercado laboral juvenil', polo_neg: 'Informal y precario', polo_pos: 'Formal y con práctica', importedFrom: 'micmac' },
        y: { nombre: 'Capacidad fiscal del Distrito', polo_neg: 'Recorte', polo_pos: 'Expansión', importedFrom: 'manual' }
      },
      escenarios: {
        NE: { nombre: 'Bogotá que retiene', narrativa: 'Hay plata y hay empleo formal para jóvenes: la media técnica se vuelve la ruta natural y el subsidio se usa poco. El riesgo es la complacencia.', prob: 20 },
        NO: { nombre: 'Subsidio sin salida', narrativa: 'El Distrito tiene recursos pero el mercado juvenil sigue informal: la transferencia retiene en el colegio, pero al graduarse no hay a dónde ir.', prob: 35 },
        SO: { nombre: 'Cada colegio por su cuenta', narrativa: 'Recorte fiscal y empleo precario: solo sobrevive lo que los colegios puedan sostener con su gente. El acompañamiento cogestionado es lo único que no depende de caja nueva.', prob: 30 },
        SE: { nombre: 'Empleo que compite con el aula', narrativa: 'Sin plata pública pero con empleo juvenil formal: el trabajo temprano jala a los de 16-17 fuera del colegio. La práctica remunerada dentro de la media es la respuesta.', prob: 15 }
      },
      elementos,
      impactos: {
        'el-ingreso': { NE: 2, NO: 1, SO: -2, SE: 1 },
        'el-rezago':  { NE: 1, NO: 0, SO: -2, SE: -1 },
        'el-sed':     { NE: 1, NO: 1, SO: -1, SE: 0 },
        'el-hda':     { NE: 2, NO: 1, SO: -2, SE: -2 },
        'el-tmc':     { NE: 1, NO: 2, SO: -2, SE: -1 },
        'el-psico':   { NE: 1, NO: 1, SO: 1, SE: 1 },
        'el-sena':    { NE: 2, NO: -1, SO: -2, SE: 2 }
      },
      estrategia: { contingencia: 'Si el Distrito recorta (SO), el acompañamiento se sostiene con reasignación interna de orientadores y se congela el subsidio; si el empleo juvenil se formaliza (SE), se adelanta la práctica remunerada al grado 10.', senales_tempranas: 'Ejecución presupuestal de la SED al primer trimestre · tasa de informalidad juvenil del DANE (GEIH) · matrícula en media técnica del SENA en Bogotá.' }
    };
  }

  // ───────────────────────── 8 · Comunicar la política ─────────────────────────
  function comunicar() {
    const audiencias = [
      { nombre: 'Familias de estudiantes de 9-11 en las 4 localidades', perfil: 'Hogares de estratos 1 y 2, jefatura femenina frecuente, uso intensivo de WhatsApp', prioridad: 'alta', tono: 'cercano, sin siglas', conocimiento: 'bajo' },
      { nombre: 'Rectores, orientadores y docentes', perfil: 'Ejecutan el programa; temen más carga administrativa', prioridad: 'alta', tono: 'de par a par, con datos del propio colegio', conocimiento: 'alto' },
      { nombre: 'Concejo de Bogotá y medios locales', perfil: 'Deciden presupuesto y marcan agenda', prioridad: 'media', tono: 'preciso, con cifras y plazos', conocimiento: 'medio' },
      { nombre: 'Organizaciones juveniles y de estudiantes', perfil: 'Legitiman o desacreditan el programa entre los propios jóvenes', prioridad: 'media', tono: 'horizontal, reconocimiento', conocimiento: 'medio' }
    ];
    const seleccionados = ['whatsapp', 'territorial', 'medios_trad', 'redes_tiktok', 'web_oficial'];
    const matriz = {
      a0: { whatsapp: 3, territorial: 2, medios_trad: 1, redes_tiktok: 1, web_oficial: 0 },
      a1: { whatsapp: 2, territorial: 3, medios_trad: 0, redes_tiktok: 0, web_oficial: 2 },
      a2: { whatsapp: 0, territorial: 1, medios_trad: 3, redes_tiktok: 0, web_oficial: 2 },
      a3: { whatsapp: 2, territorial: 2, medios_trad: 0, redes_tiktok: 3, web_oficial: 1 }
    };
    const kpis = {
      alcance:        { nombre: 'Familias alcanzadas por WhatsApp', meta: '70 % de las familias de 9-11 en 4 localidades', fuente: 'Canal de difusión de la SED' },
      engagement:     { nombre: 'Respuestas y reenvíos', meta: '15 % de los mensajes', fuente: 'Métricas del canal' },
      atencion:       { nombre: 'Recuerdo del mensaje', meta: '40 % en encuesta de salida', fuente: 'Encuesta en entrega de boletines' },
      comprension:    { nombre: 'Familias que explican qué es el programa', meta: '60 %', fuente: 'Grupos focales' },
      satisfaccion:   { nombre: 'Satisfacción con la atención del orientador', meta: '≥ 4/5', fuente: 'Encuesta trimestral' },
      apoyo:          { nombre: 'Apoyo declarado al programa', meta: '≥ 65 %', fuente: 'Encuesta distrital' },
      actitudinal:    { nombre: 'Percepción de que «terminar el colegio vale la pena»', meta: '+10 pp', fuente: 'Encuesta a estudiantes' },
      intencion:      { nombre: 'Estudiantes que dicen que terminarán once', meta: '≥ 85 %', fuente: 'Encuesta a estudiantes' },
      comportamiento: { nombre: 'Asistencia y permanencia', meta: 'Deserción ≤ 8 %', fuente: 'SIMAT' }
    };
    return {
      step: 8,
      contexto: { politica: 'Programa de permanencia escolar 9-11', fase: 'implementacion', enunciado: ENUNCIADO, objetivo: 'movilizar', horizonte: '12m', dep_cod: '11', dep_nombre: 'Bogotá D.C.', mun_cod: '11001', mun_nombre: 'Bogotá D.C.', importedFromPP: true, importedFromEv: false, importedFromAin: true, importedFromAlt: true },
      audiencias,
      mensaje: { primario: 'Ningún estudiante de Bogotá deja el colegio sin que alguien lo busque.', secundarios: ['Un orientador en cada colegio sabe quién está faltando y por qué.', 'El apoyo llega en menos de 30 días, antes de que el estudiante se vaya.', 'Terminar once abre la media técnica y el primer empleo formal.'], promesa: 'Alerta y acompañamiento en menos de 30 días para cada estudiante de 9-11 que empiece a faltar.', evidencia: '12,3 % de deserción en 9-11 (SIMAT 2024, cifra ilustrativa); 61 % de quienes desertan citan la necesidad de trabajar.', valores: ['oportunidad', 'cuidado', 'futuro'] },
      narrativa: { self: 'Yo terminé el colegio porque alguien se dio cuenta de que estaba faltando y fue a buscarme a la casa.', us: 'En Ciudad Bolívar, Usme, Bosa y San Cristóbal hay miles de familias que quieren que sus hijos se gradúen y no tienen cómo sostenerlos en el aula.', now: 'Este año, por primera vez, cada colegio tendrá un orientador que vea la inasistencia el mismo mes en que ocurre. Empieza en marzo en 40 colegios.' },
      framing: { valor: 'Cuidado: nadie se queda atrás', metafora: 'Una red que atrapa antes de la caída', encuadre_evitar: 'No responder a «subsidio a vagos»: no repetir la palabra subsidio; hablar de acompañamiento y de la fecha de graduación.', palabras_propias: ['acompañamiento', 'graduación', 'alerta temprana', 'orientador', 'red', 'permanencia'], palabras_adversario: ['subsidio', 'regalo', 'asistencialismo', 'vagancia'] },
      canales: { seleccionados, matriz, notas_east: 'Fácil: un solo número de WhatsApp por colegio. Atractivo: mensajes con el nombre del estudiante. Social: testimonios de egresados del mismo barrio. Oportuno: la primera semana de cada corte de notas.' },
      voceria: { vocero: { nombre: 'Secretaria de Educación del Distrito', rol: 'Vocera principal', justifica: 'Es quien firma el decreto y responde ante el Concejo; credibilidad técnica alta.' }, multiplicadores: [{ nombre: 'Rectora de un colegio de Usme', tipo: 'territorial', audiencia: 'Rectores y docentes' }, { nombre: 'Egresado de media técnica', tipo: 'sc', audiencia: 'Organizaciones juveniles' }, { nombre: 'Investigadora en educación (universidad)', tipo: 'academico', audiencia: 'Concejo y medios' }], riesgos: 'Que el debate se vaya al costo del programa y no a la deserción; que un caso individual mal atendido se vuelva titular.' },
      cronograma: { fase_pre: 'Febrero: briefing a rectores, pruebas de mensaje con 3 grupos de familias, acuerdo con 2 medios locales.', fase_lanzamiento: 'Marzo: anuncio en los 40 colegios, rueda de prensa, primer mensaje de WhatsApp a las familias.', fase_mantenimiento: 'Abril a noviembre: un mensaje por corte de notas, testimonios mensuales, informe trimestral al Concejo.', fase_evaluacion: 'Diciembre: encuesta de recuerdo y apoyo, informe de medición OCDE 9 dimensiones.' },
      medicion: { kpis, plan_monitoreo: 'Tablero mensual con las 9 dimensiones; revisión con el equipo de prensa cada corte.', triggers_ajuste: 'Si el apoyo baja de 50 % o el recuerdo no llega a 25 % en junio, se rehace el mensaje primario con un nuevo grupo focal.' }
    };
  }

  const BUILD = { pp, micmac, mactor, alt, ain, ev, prospect, comunicar };

  function hayContenido() {
    return Object.values(KEYS).some(k => { try { return !!localStorage.getItem(k); } catch (e) { return false; } });
  }
  function activo() { try { return localStorage.getItem(FLAG) === '1'; } catch (e) { return false; } }

  // cargar({ abrir:'pp'|'micmac'|…|null, confirmar:true })
  function cargar(opts) {
    opts = opts || {};
    const confirmar = opts.confirmar !== false;
    if (confirmar && hayContenido() && !activo()) {
      const ok = window.confirm('Ya tienes trabajo guardado en el Lab. El caso de ejemplo lo reemplaza en los ocho módulos (puedes volver a borrarlo desde el hub). ¿Continuar?');
      if (!ok) return false;
    }
    try {
      Object.keys(BUILD).forEach(k => localStorage.setItem(KEYS[k], JSON.stringify(BUILD[k]())));
      localStorage.setItem(FLAG, '1');
    } catch (e) { window.alert('No se pudo guardar el caso de ejemplo en este navegador.'); return false; }
    if (opts.abrir && HREF[opts.abrir]) {
      const dest = HREF[opts.abrir];
      // Misma página → recargar para que el módulo lea el estado nuevo.
      const mismaPagina = location.pathname.endsWith('/' + dest.split('#')[0]);
      location.href = dest;
      if (mismaPagina) location.reload();
    }
    return true;
  }
  function limpiar(opts) {
    opts = opts || {};
    if (opts.confirmar !== false) {
      const ok = window.confirm('Se borra el caso de ejemplo de los ocho módulos, incluidos los cambios que le hayas hecho. ¿Continuar?');
      if (!ok) return false;
    }
    try { Object.values(KEYS).forEach(k => localStorage.removeItem(k)); localStorage.removeItem(FLAG); } catch (e) {}
    if (opts.recargar !== false) location.reload();
    return true;
  }

  window.LabDemo = { cargar, limpiar, activo, hayContenido, KEYS, HREF, TITULO };
})();

/* ── Render automático: cualquier <p data-lab-demo="pp|micmac|…|hub"> se llena solo ── */
(function () {
  'use strict';
  const CSS = `
.lab-demo-line{margin:1.1rem auto 0;text-align:center;font-family:var(--italic,Georgia,serif);font-style:italic;font-size:.9rem;line-height:1.5;color:var(--ink-3,#807a6c);max-width:60ch}
.lab-demo-line a,.lab-demo-line button{font-family:var(--mono,monospace);font-style:normal;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--accent,#d96a50);background:none;border:0;padding:0;cursor:none;text-decoration:none;border-bottom:1px solid var(--accent-tint,#d96a5036);transition:border-color .15s}
.lab-demo-line a:hover,.lab-demo-line button:hover{border-color:var(--accent,#d96a50)}
.lab-demo-line.is-active{color:var(--ink-2,#b8b1a0)}
.lab-demo-line .ld-tag{font-family:var(--mono,monospace);font-style:normal;font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--gold,#d6a83a);margin-right:.5rem}
.hub-demo-bar{display:flex;align-items:center;justify-content:center;gap:.9rem;flex-wrap:wrap;margin:1.1rem auto 0;padding:.9rem 1.1rem;border:1px dashed var(--rule-strong,#f4f3ef38);max-width:880px;font-family:var(--italic,Georgia,serif);font-style:italic;font-size:.93rem;line-height:1.5;color:var(--ink-2,#b8b1a0)}
.hub-demo-bar .btn-ghost,.hub-demo-bar .btn{font-style:normal}
`;
  function render() {
    const nodes = document.querySelectorAll('[data-lab-demo]');
    if (!nodes.length || !window.LabDemo) return;
    if (!document.getElementById('lab-demo-css')) {
      const st = document.createElement('style'); st.id = 'lab-demo-css'; st.textContent = CSS; document.head.appendChild(st);
    }
    const act = window.LabDemo.activo();
    nodes.forEach(el => {
      const mod = el.getAttribute('data-lab-demo');
      if (mod === 'hub') {
        el.className = 'hub-demo-bar';
        el.innerHTML = act
          ? `<span><span class="ld-tag" style="font-family:var(--mono);font-style:normal;font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--gold)">Caso de ejemplo cargado</span> Los ocho módulos tienen el caso «deserción escolar 9-11 · Bogotá». Ábrelos, edítalos o bórralo cuando quieras empezar el tuyo.</span>
             <button class="btn-ghost" type="button" onclick="LabDemo.limpiar()">Borrar el caso de ejemplo</button>`
          : `<span>¿Prefieres ver primero cómo funciona? Carga un caso completo —deserción escolar 9-11 en Bogotá, cifras ilustrativas— en los ocho módulos y recórrelo.</span>
             <button class="btn-ghost" type="button" onclick="LabDemo.cargar({abrir:'pp'})">Explorar con un caso de ejemplo →</button>`;
        return;
      }
      el.className = 'lab-demo-line' + (act ? ' is-active' : '');
      el.innerHTML = act
        ? `<span class="ld-tag">Caso de ejemplo</span>Estás viendo «deserción escolar 9-11 · Bogotá», con cifras ilustrativas. <button type="button" onclick="LabDemo.limpiar()">Borrar y empezar el mío</button>`
        : `¿Solo quieres ver cómo funciona? <a href="#" onclick="LabDemo.cargar({abrir:'${mod}'});return false;">Carga el caso de ejemplo →</a> (deserción escolar 9-11 en Bogotá, los ocho módulos llenos).`;
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', render); else render();
})();
