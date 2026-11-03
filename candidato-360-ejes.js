/* ═══════════════════════════════════════════════════════════════════════════
   CANDIDATO 360 · EL EJE DE CAMPAÑA (2-nov-2026)
   ───────────────────────────────────────────────────────────────────────────
   Pedido de Ricardo: la estrategia no es la lista de rasgos que la candidatura
   comparte con su electorado ni un banco de principios académicos. Es la idea
   que la campaña sostiene de aquí a la elección —el eje—, y encima van las
   acciones, que sí cambian con el calendario y con la coyuntura.

   Este archivo es solo el catálogo y la regla que elige: recibe las señales de
   la candidatura (familia política, partidos con los que se ha lanzado, las
   iglesias de barrio donde coincide su voto, lo que le rinde en redes, los
   temas de sus barrios, si es figura o barrio, su causa) y devuelve los ejes
   ordenados, cada uno con las razones que lo sostienen. La candidatura
   confirma uno y desde ahí queda fijo, guardado en su campaña.

   Puro (sin DOM ni red): se prueba en Node con tools/candidato-360/prueba-ejes.mjs.
   Las reglas son a la vista y con puntos enteros a propósito: quien vea el eje
   tiene que poder leer por qué salió ese y no otro.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';
  const norm = s => ' ' + String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9ñ ]+/g, ' ').replace(/\s+/g, ' ').trim() + ' ';

  /* Partidos de base religiosa (confesionales o de derecha cristiana de
     familia). Salvación Nacional y Centro Democrático NO están: son derecha de
     valores, y cuentan aparte, con menos peso. */
  const CONFESIONAL = /justa libres|colombia justa|\bmira\b|bogota mas fuerte|nueva fuerza democratica|\blibres\b/;
  const DERECHA_VALORES = /salvacion nacional|centro democratico/;

  /* Palabras que ubican una publicación en un tema. Se comparan como inicio
     de palabra («impuest» casa impuesto e impuestos). */
  const TEMAS_REDES = {
    fe: ['dios', 'fe', 'familia', 'familias', 'iglesia', 'iglesias', 'pastor', 'pastores', 'oracion', 'orar', 'oremos', 'bendicion', 'bendecid', 'bendic', 'cristian', 'biblia', 'jesus', 'jesucristo', 'congregacion', 'evangel', 'amen', 'creyente'],
    seguridad: ['seguridad', 'inseguridad', 'policia', 'delito', 'delincuen', 'hurto', 'robo', 'crimen', 'criminal', 'extorsion', 'sicari', 'convivencia'],
    bolsillo: ['impuest', 'tributari', 'predial', 'alivio', 'moros', 'empleo', 'desempleo', 'tarifa', 'costo de vida', 'precio', 'subsidio', 'emprend'],
    gestion: ['concejo', 'aprobad', 'aprobamos', 'proyecto de acuerdo', 'plenaria', 'debate', 'gestion', 'logramos', 'radicamos', 'propuesta'],
  };
  const tieneTema = (txt, tema) => { const t = norm(txt); return TEMAS_REDES[tema].some(w => t.includes(' ' + w)); };

  /* Lo que una causa escrita por la persona dice de su eje. */
  const CAUSA_EJE = [
    ['fe', ['fe', 'dios', 'familia', 'vida', 'valores', 'iglesia', 'ninos', 'niñez', 'ninez']],
    ['orden', ['seguridad', 'seguro', 'segura', 'seguros', 'seguras', 'orden', 'policia', 'delito', 'robo', 'parques']],
    ['bolsillo', ['impuest', 'empleo', 'trabajo', 'tarifa', 'predial', 'precio', 'costo', 'moros', 'emprend', 'deuda']],
    ['derechos', ['derecho', 'dignidad', 'mujer', 'mujeres', 'igualdad', 'inclusion', 'diversidad', 'paz']],
    ['resolver', ['vias', 'huecos', 'agua', 'acueducto', 'alumbrado', 'barrio', 'obras', 'servicio']],
    ['cambio', ['corrupcion', 'cambio', 'nuevo', 'renovar', 'transparencia']],
  ];

  /* Arquetipos que empujan a cada eje. Bogotá (Concejo) y las familias de
     Medellín y Cartagena. Se casa por id; los nombres emocionales cambian. */
  const ARQ_EJE = {
    movilizada: ['pertenencia', 'fe'], pertenencia: ['pertenencia'],
    gestion: ['resolver'], estabilidad: ['resolver'], continuidad: ['resolver'], nombre: ['resolver'],
    'sin-dueno': ['voz'], opinion: ['voz'],
    proteccion: ['orden'],
    supervivencia: ['bolsillo'],
    castigo: ['cambio'], alternativa: ['cambio'], 'poco-voto': ['cambio'],
    partido: ['derechos', 'fe'], figuras: ['voz'],
  };
  /* Temas de la agenda (sensibilidad del arquetipo 4-5) que empujan a cada eje. */
  const TEMA_EJE = { seguridad: 'orden', empleo: 'bolsillo', vivienda: 'bolsillo', servicios: 'resolver', movilidad: 'resolver', salud_educacion: 'derechos', corrupcion: 'cambio', participacion: 'pertenencia', cultura: 'pertenencia', ambiente: 'voz', politica: 'voz' };

  /* El catálogo. `idea` y `pilares` son el respaldo fijo: lo que la tarjeta
     muestra si la IA no responde. La IA los reescribe con los datos de la
     candidatura al confirmar el eje, sin cambiarles el sentido. */
  const EJES = [
    { id: 'fe', nombre: 'Fe y familia', corto: 'fe',
      idea: 'Tu campaña es la de una persona de fe que sirve: los valores de la familia puestos a trabajar por el barrio y por la ciudad.',
      pilares: [
        { titulo: 'La fe como identidad', texto: 'Que se sepa quién eres y en qué crees, en todo lo que publiques. La fe no se esconde ni se usa: se nota en cómo trabajas.' },
        { titulo: 'La gestión contada desde los valores', texto: 'Cada logro se cuenta como cuidado de la familia: a quién le sirvió, con nombre y cara, no con cifras sueltas.' },
        { titulo: 'Las comunidades de barrio', texto: 'Presencia constante en los barrios donde ya tienes votos y en sus comunidades pequeñas, sin convertir el culto en tarima.' },
      ],
      noDecir: ['No pidas el voto dentro de un culto ni a una congregación como bloque.', 'No uses la fe para atacar a nadie: tu campaña es de servicio, no de cruzada.'] },
    { id: 'orden', nombre: 'Orden y seguridad', corto: 'seguridad',
      idea: 'Tu campaña es la de quien le devuelve la tranquilidad al día a día: calles, parques y entornos donde la gente vuelva a estar segura.',
      pilares: [
        { titulo: 'Lo que se puede ver', texto: 'Hablar de lugares concretos: el parque, la esquina, el paradero. Nada de seguridad en abstracto.' },
        { titulo: 'Resultados medibles', texto: 'Cada propuesta con una forma de comprobar si funcionó, y rendir cuentas sobre eso.' },
        { titulo: 'Con la comunidad', texto: 'Frentes de seguridad, juntas y comerciantes como aliados, no como público.' },
      ],
      noDecir: ['No prometas acabar con el delito: promete lo que puedes hacer desde tu cargo.', 'No estigmatices a migrantes ni a jóvenes de un barrio.'] },
    { id: 'resolver', nombre: 'El que resuelve', corto: 'gestión',
      idea: 'Tu campaña es la de quien está y resuelve: lo que se arregló, lo que falta y cómo lo vas a sacar adelante.',
      pilares: [
        { titulo: 'Rendir cuentas', texto: 'Mostrar lo hecho con fotos, lugares y personas, y decir con la misma claridad lo que no se logró.' },
        { titulo: 'Presencia', texto: 'Estar en el barrio antes de que llegue la campaña: la gente vota a quien ya vio.' },
        { titulo: 'Lo próximo', texto: 'Tres compromisos concretos y comprobables para el siguiente periodo.' },
      ],
      noDecir: ['No te atribuyas obras que no son tuyas.', 'No hables de gestión sin decir dónde.'] },
    { id: 'bolsillo', nombre: 'El bolsillo de la familia', corto: 'bolsillo',
      idea: 'Tu campaña es la de quien cuida el bolsillo de la familia: impuestos, tarifas y empleo, contados en lo que le cambia a la casa.',
      pilares: [
        { titulo: 'Lo que le cambia a la casa', texto: 'Cada propuesta contada en pesos y en meses, no en artículos ni en siglas.' },
        { titulo: 'Quién se beneficia', texto: 'Ponerle cara a cada alivio: la familia, el tendero, el que se atrasó.' },
        { titulo: 'Cuentas claras', texto: 'Explicar de dónde sale la plata, antes de que otro lo pregunte.' },
      ],
      noDecir: ['No prometas bajar lo que no depende de tu cargo.', 'No presentes un alivio como premio a quien no paga.'] },
    { id: 'pertenencia', nombre: 'Lo nuestro', corto: 'barrio',
      idea: 'Tu campaña es la de alguien del barrio que defiende lo que el barrio construyó: su gente, su historia y su manera de hacer las cosas.',
      pilares: [
        { titulo: 'Raíz', texto: 'Contar de dónde vienes y con quién has trabajado, con nombres del barrio.' },
        { titulo: 'Orgullo', texto: 'Celebrar lo que el barrio logró solo, y ponerlo como ejemplo.' },
        { titulo: 'Voz en la ciudad', texto: 'Llevar lo del barrio a donde se decide, y volver a contarlo.' },
      ],
      noDecir: ['No hables del barrio como un problema.', 'No prometas lo que la comunidad no pidió.'] },
    { id: 'voz', nombre: 'Voz de ciudad', corto: 'opinión',
      idea: 'Tu campaña es la de una voz de ciudad con posiciones claras: alguien que dice lo que piensa y lo sostiene.',
      pilares: [
        { titulo: 'Tres posiciones', texto: 'Pocas causas, dichas siempre igual, para que se recuerden.' },
        { titulo: 'Control', texto: 'Debates y preguntas públicas con documentos, no con adjetivos.' },
        { titulo: 'Coherencia', texto: 'Que lo que votas, publicas y dices en el barrio sea lo mismo.' },
      ],
      noDecir: ['No opines de todo: el que opina de todo no se recuerda por nada.', 'No ataques personas: discute decisiones.'] },
    { id: 'cambio', nombre: 'Algo nuevo', corto: 'cambio',
      idea: 'Tu campaña es la de quien llega a hacer las cosas distinto: sin deudas con nadie y con la gente que ya se cansó de lo mismo.',
      pilares: [
        { titulo: 'Quién eres', texto: 'Presentarte rápido y bien: nadie vota por quien no conoce.' },
        { titulo: 'Contra qué', texto: 'Nombrar la práctica que quieres cambiar, no a la persona.' },
        { titulo: 'Cómo se nota', texto: 'Una forma de hacer política que se vea desde la campaña: cuentas abiertas, gente nueva.' },
      ],
      noDecir: ['No te presentes como antipolítico si ya has estado en la política.', 'No prometas limpiar todo: di qué vas a cambiar primero.'] },
    { id: 'derechos', nombre: 'Dignidad y derechos', corto: 'derechos',
      idea: 'Tu campaña es la de quien pone a la gente primero: derechos que se cumplan en el barrio, no solo en el papel.',
      pilares: [
        { titulo: 'Lo que falta', texto: 'Salud, educación y vivienda contadas con casos del territorio.' },
        { titulo: 'Con quién', texto: 'Las organizaciones del barrio como coautoras de las propuestas.' },
        { titulo: 'Cumplir', texto: 'Hacer seguimiento público a lo que se promete en el territorio.' },
      ],
      noDecir: ['No hables de los derechos como una lista: cuéntalos en una persona.', 'No prometas lo que depende de la Nación.'] },
  ];
  const porId = Object.fromEntries(EJES.map(e => [e.id, e]));

  /* Qué rinde en redes: promedio de interacción (reacciones + comentarios) de
     las publicaciones propias de cada tema contra el de todas. Los retuits no
     cuentan: su interacción es del trino original. */
  function redesPorTema(publicados) {
    const xs = (publicados || []).filter(p => p && p.texto && !/^RT @/.test(p.texto));
    const inter = p => Number(p.reaccion || 0) + Number(p.comentarios || 0);
    const total = xs.length, prom = total ? xs.reduce((s, p) => s + inter(p), 0) / total : 0;
    const out = { total, prom, temas: {} };
    Object.keys(TEMAS_REDES).forEach(t => {
      const ys = xs.filter(p => tieneTema(p.texto, t));
      out.temas[t] = { n: ys.length, prom: ys.length ? ys.reduce((s, p) => s + inter(p), 0) / ys.length : 0 };
    });
    return out;
  }

  /* sen = {
       bloque, partidos:[nombres de todos sus avales], causa,
       arquetipos:[{id, nombre, share, ratio, temas:[ids de tema]}],
       figura: 'figura'|'barrio'|'mixto', historial:{n, misma},
       iglesias:{pequenas, coinciden}, redes: salida de redesPorTema,
       edadMayor: bool, edadJoven: bool, nuevo: bool }
     → [{id, nombre, idea, pilares, noDecir, puntos, razones:[texto]}] */
  function proponer(sen) {
    const s = sen || {}, P = {}, R = {};
    EJES.forEach(e => { P[e.id] = 0; R[e.id] = []; });
    const suma = (id, n, razon) => { if (!P.hasOwnProperty(id) || !n) return; P[id] += n; if (razon && !R[id].includes(razon)) R[id].push(razon); };
    const partidos = (s.partidos || []).filter(Boolean), np = partidos.map(norm);

    const conf = partidos.find((p, i) => CONFESIONAL.test(np[i]));
    if (conf) suma('fe', 3, `Te has lanzado con ${conf}, un partido de base cristiana y de familia.`);
    else if (np.some(p => DERECHA_VALORES.test(p))) { suma('fe', 1, 'Tu partido es de la derecha de valores.'); suma('orden', 1, 'Tu partido pone la seguridad en el centro.'); }
    if (s.bloque === 'd') { suma('fe', 1, 'Tu familia política es la derecha.'); suma('orden', 1, 'Tu familia política es la derecha.'); }
    if (s.bloque === 'cd') { suma('orden', 1, 'Tu familia política es el centro-derecha.'); suma('bolsillo', 1, 'Tu familia política es el centro-derecha.'); }
    if (s.bloque === 'izq' || s.bloque === 'ci') { suma('derechos', 2, `Tu familia política es ${s.bloque === 'izq' ? 'la izquierda' : 'el centro-izquierda'}.`); suma('voz', 1); }
    if (s.bloque === 'c') { suma('voz', 1); suma('resolver', 1); }

    const ig = s.iglesias;
    if (ig && ig.coinciden >= 5) suma('fe', 2, `Tu voto coincide con ${ig.coinciden} iglesias cristianas de barrio${ig.pequenas ? `, de ${ig.pequenas} que tiene el mapa` : ''}.`);
    else if (ig && ig.coinciden >= 1) suma('fe', 1, `Tu voto coincide con ${ig.coinciden} iglesia${ig.coinciden === 1 ? '' : 's'} cristiana${ig.coinciden === 1 ? '' : 's'} de barrio.`);

    const rd = s.redes;
    if (rd && rd.total >= 6 && rd.prom > 0) {
      const EJE_DE = { fe: 'fe', seguridad: 'orden', bolsillo: 'bolsillo', gestion: 'resolver' };
      const NOM = { fe: 'de fe', seguridad: 'de seguridad', bolsillo: 'del bolsillo', gestion: 'de tu gestión' };
      Object.entries(rd.temas).forEach(([t, v]) => {
        if (v.n < 2) return;
        const veces = v.prom / rd.prom;
        if (veces >= 1.1) suma(EJE_DE[t], 2, `En redes, lo que publicas ${NOM[t]} rinde más que el resto (${v.n} publicaciones).`);
        else if (v.n / rd.total >= .2) suma(EJE_DE[t], 1, `Publicas a menudo ${NOM[t]} (${v.n} de ${rd.total}).`);
      });
    }

    const arqs = (s.arquetipos || []).slice().sort((a, b) => (b.share || 0) - (a.share || 0)).slice(0, 3);
    arqs.forEach((a, i) => {
      const w = i === 0 ? 2 : 1, rinde = a.ratio != null && a.ratio >= 1.05;
      (ARQ_EJE[a.id] || []).forEach((e, j) => suma(e, j === 0 ? w + (rinde ? 1 : 0) : 1, j === 0 ? `Tus votos pesan en los barrios «${a.nombre}»${rinde ? ', donde rindes por encima de la ciudad' : ''}.` : ''));
      (a.temas || []).forEach(t => { if (TEMA_EJE[t]) suma(TEMA_EJE[t], 1); });
    });

    if (s.figura === 'barrio') { suma('resolver', 2, 'Tu voto es de barrio: se apoya en presencia.'); suma('pertenencia', 1); }
    if (s.figura === 'figura') suma('voz', 2, 'Tu voto es de opinión: llega a toda la ciudad.');
    if (s.historial && s.historial.n >= 2) suma('resolver', 1, `Te has lanzado ${s.historial.n} veces: tienes una trayectoria que contar.`);
    if (s.nuevo) suma('cambio', 2, 'Es tu primera candidatura: llegas sin una trayectoria que defender.');
    if (s.edadJoven) suma('cambio', 1);

    const cz = norm(s.causa);
    if (cz.trim()) CAUSA_EJE.forEach(([id, ws]) => { if (ws.some(w => cz.includes(' ' + w))) suma(id, 3, `Tu causa: «${String(s.causa).trim()}».`); });

    return EJES.map(e => ({ ...e, puntos: P[e.id], razones: R[e.id] }))
      .filter(e => e.puntos > 0)
      .sort((a, b) => b.puntos - a.puntos || EJES.indexOf(porId[a.id]) - EJES.indexOf(porId[b.id]));
  }

  global.C360Ejes = { EJES, porId, proponer, redesPorTema, tieneTema };
})(typeof window !== 'undefined' ? window : globalThis);
