/* ═══════════════════════════════════════════════════════════════════════════
   CANDI · la guía de Candidato 360 (20-sep-2026)
   ───────────────────────────────────────────────────────────────────────────
   Candi es la perrita del usuario (Luna) convertida en guía de la plataforma.
   NO es un chat de datos electorales: sabe en qué vista está el usuario y
   explica QUÉ es y QUÉ hacer ahí. Las cifras las da la página, no ella.

   Dos capas, a propósito separadas:

   · La GUÍA (VISTAS, más abajo) es texto nuestro, determinista. Está siempre
     —sin sesión, sin red y sin modelo— y es la versión accesible de lo que
     dice la mascota. La mascota es decorativa: si el atlas no carga, no se
     pierde ni una palabra.
   · Las PREGUNTAS escritas van al worker (POST /c360/candi), que llama al
     modelo con la clave del servidor. Si no hay sesión, cuota o clave, se dice
     exactamente eso: nunca se inventa una respuesta y se la atribuye a nadie.

   Candi ENTRA SOLA al cargar la página (una vez): llega, saluda, se sienta y
   se queda atenta con la cola en un bucle suave (v3 atlética). Abrir o cerrar
   el panel no la hace saludar otra vez: ya está ahí.

   Habla de TÚ. El resto del producto habla de usted a propósito —es la voz
   seria de la plataforma— y ella es la voz cercana; son dos cosas distintas.
   ═══════════════════════════════════════════════════════════════════════════ */
(() => {
  'use strict';
  const BASE = 'assets/candidato-360/candi/';
  /* La miniatura del botón: la pose SENTADA de la v3 atlética. Las
     coordenadas de la v2 no sirven — es otro atlas y otra grilla. Índice 8 de
     una grilla 4×4 = columna 0, fila 2 → posición 0% 66,6667%. */
  const ATLAS = BASE + 'candi-sentarse-atenta-v3.webp';
  const API = (() => { try { return AUTH_API; } catch { return 'https://rr-auth.reruizc.workers.dev'; } })();

  /* Estados que el MODELO puede pedir. El worker valida contra su propia copia;
     ésta es la del cliente. `saludo` es la entrada y solo la dispara la carga
     de la página, así que un `saludo` pedido por el modelo se ignora.
     `sit_down` e `idle_seated` ya existen, pero son la secuencia local de la
     entrada y no se le piden al modelo: por eso no están acá. La reacción
     `curious` tampoco — está pendiente de documentar y no se conecta aún. */
  const ESTADOS = { saludo: { clip: 'enter_greet', soloAlEntrar: true } };

  /* ─── La guía por vista ──────────────────────────────────────────────────
     Una entrada por pantalla de candidato-360.html. `chips` son preguntas
     sugeridas: rellenan el campo, no se envían solas. */
  const VISTAS = {
    intro: {
      titulo: 'Estás en la portada',
      texto: 'Acá se decide por dónde entrar: si ya fuiste candidato, buscamos tu historial electoral y lo conectamos con la campaña de 2027; si es tu primera candidatura, armamos el punto de partida desde el territorio.',
      saludo: 'Un dato antes de escoger: aunque hayas sido candidato una sola vez, hace años o en otra corporación, entra por «ya me he lanzado». Con esa votación real el cálculo sale mucho más fino que partiendo de cero.',
      chips: ['¿Qué diferencia hay entre las dos rutas?', '¿Qué necesito para empezar?']
    },
    existing: {
      titulo: 'Búsqueda de tu historial',
      texto: 'Escribe tu nombre completo. Buscamos en todas las elecciones que tenemos cargadas —Congreso, asambleas, concejos, JAL, alcaldías y gobernaciones— y te mostramos cada candidatura con su votación. Si apareces varias veces, es la misma persona en años distintos.',
      saludo: 'Escribe el nombre como quedó inscrito en la Registraduría, con los dos apellidos: así te separo de tus homónimos. Si tienes un nombre común, mira los votos y el municipio de cada resultado antes de escogerte.',
      chips: ['No me encuentro, ¿qué hago?', '¿Qué elecciones tienen cargadas?']
    },
    candidateRoute: {
      titulo: 'Tu campaña de 2027',
      texto: 'Acá defines a qué corporación te lanzas y dónde. Si cambias de corporación, el territorio cambia con ella: tu meta y tu mapa se recalculan con esa nueva escala, no con la de tu elección anterior.',
      saludo: 'Si cambias de corporación, tu votación anterior no se pierde: la uso para ver dónde ya tienes gente, pero la meta la calculo con los resultados de 2023 del territorio nuevo. Y si todavía no tienes partido, escoge tu familia política: con eso alcanza para arrancar.',
      chips: ['¿Puedo cambiar de corporación?', '¿Qué pasa si todavía no tengo partido?']
    },
    new: {
      titulo: 'Candidatura nueva',
      texto: 'Sin historial propio, el punto de partida es el territorio: tomamos los resultados de 2023 en el lugar al que aspiras y sobre eso se calcula la meta. Puedes dejar el partido pendiente y elegir por ahora tu familia política.',
      saludo: 'Son seis pasos cortos y nada es definitivo: el partido, el territorio y el objetivo se pueden cambiar después desde el CRM. Lo único que sí importa acertar es la corporación, porque de ahí sale la escala de todo lo demás.',
      chips: ['¿Por qué me piden las redes?', '¿Puedo seguir sin partido?']
    },
    crm: {
      titulo: 'Tu CRM de campaña',
      texto: 'Arriba, el mapa de dónde estuvo tu votación y la meta que necesitas. Abajo, los módulos: briefing cada tres días, escucha social, arquetipos del territorio, perfil del votante, endoso de aliados, el plan del día de la elección y tus contendientes.',
      saludo: 'Este es tu tablero. Un orden que funciona: primero la meta y el mapa, para saber cuánto falta y dónde; después el electorado, para saber a quién hablarle; y ya con eso, el endoso y el día de la elección. El briefing enciéndelo hoy: llega solo, cada tres días.',
      chips: ['¿De dónde sale mi meta de votos?', '¿Qué hace el briefing?', '¿Para qué sirve el día de la elección?']
    }
  };
  /* Las páginas de módulo no tienen `.screen`: se identifican con
     <body data-candi-vista="…">. Van en esta misma tabla y en el worker. */
  VISTAS.electorado = {
    titulo: 'El electorado de tu votación',
    texto: 'Aquí ves quién puede votar donde está tu votación: sexo, edad y si es urbana o rural, contra el promedio de tu territorio. Arriba, los perfiles que más te rinden; el mapa se ilumina donde cada uno pesa más. El sexo y la edad son el censo electoral de 2026 tal como lo publica la Registraduría; el cruce de los dos, para armar los perfiles, es una estimación.',
    /* El saludo de esta página explica la decisión de fondo: describir a quien
       PUEDE votar y no a quien votó. Cifras de participación: preconteo 2026
       (58 % en primera vuelta, 63,6 % en segunda) y segunda vuelta 2022 (58 %). */
    saludo: 'Aquí te muestro a quien PUEDE votar, no solo a quien votó la última vez. ¿Por qué? Porque la participación viene subiendo: en la segunda vuelta de 2026 votó el 64 % del censo, casi seis puntos más que en la primera y más que en 2022. El electorado de 2027 no va a ser el mismo que votó antes.',
    chips: ['¿Por qué quién puede votar y no quién votó?', '¿Qué significa que un perfil me rinda ×1,20?', '¿Dónde creció el censo?']
  };
  VISTAS.arquetipos = {
    titulo: 'Los arquetipos de tu territorio',
    texto: 'Aquí ves qué mueve el voto en cada barrio donde están tus votos: el arquetipo que manda, cómo se reparte tu votación entre todos en 2023 y a dónde va en 2027, el mapa barrio por barrio y la ficha de cada arquetipo. Si todavía no tienes votos en la ciudad, lo que ves es la ciudad, no tú.',
    saludo: 'Los arquetipos no son grupos de gente: son la emoción con la que un barrio decide el voto. Por eso el mismo barrio puede cambiar de arquetipo entre una elección y otra. Úsalos para decidir cómo hablar, no a quién.',
    chips: ['¿Qué es un arquetipo?', '¿Por qué 2027 es una simulación?', '¿Cómo le hablo al arquetipo que manda?']
  };
  VISTAS.diad = {
    titulo: 'El día de la elección',
    texto: 'Aquí decides cuántos testigos necesitas y en qué puestos. Si te lanzas a otra corporación, los puestos son los de ese territorio, ordenados por los votos de tu familia política en 2023. Mueve el control para ver cuánto cubres, y revisa los avisos: señal, internet y dónde se publica el E-14.',
    saludo: 'La votación nunca se reparte pareja: unos pocos puestos juntan la mayor parte de los votos. Empieza por los que cubren el 70 % y mira cuántos de esos no tienen señal: ahí el testigo necesita un plan para reportar antes de que llegue el domingo.',
    chips: ['¿Por qué me salen tantos puestos?', '¿Qué hago con un puesto sin señal?', '¿Cómo descargo el plan?']
  };
  VISTAS.endoso = {
    titulo: 'Endoso de aliados',
    texto: 'Aquí sumas a quienes te van a apoyar: excandidatos, con su votación, y líderes sin candidatura propia, marcando en el mapa los puestos donde trabajan. Si me dices a quién apoyó cada uno antes, mido cuánto rindió esa persona donde ellos estaban. Solo cuentan los votos del territorio donde compites, y todo sale en rango: es un techo, no una promesa. Los nombres de tus líderes se quedan en tu navegador; no los guardamos en ningún servidor.',
    saludo: 'Cuando sumes a alguien, fíjate en el rango y no en el número alto: un líder que sacó 2.000 votos hace ocho años no te trae 2.000 votos, y de esos, solo cuentan los del territorio donde compites. Lo útil es comparar aliados entre sí, no sumarlos a la meta.',
    chips: ['¿Por qué sale en rango?', '¿Cómo mides a un líder sin candidatura?', '¿Dónde queda el nombre de mis líderes?']
  };
  VISTAS.contendientes = {
    titulo: 'Tus contendientes',
    texto: 'Aquí ves contra quién compites. Son rivales probables, no inscritos: quien ganó la curul en 2023, quien compitió aquí con buena votación y quien tiene votos en tu territorio de otra elección. El plano cruza su familia política con cuánto rinde cada uno en los puestos donde tú sacas votos. Si vas en lista abierta, abajo está quién te compite dentro de tu propia lista. Al abrir la ficha de un rival ves sus titulares de los últimos seis meses, literales y con enlace. Cada mes revisamos la prensa de tu territorio: a quien nombran como aspirante lo sumamos después de que una persona lo revisa. Y si falta alguien, lo puedes agregar tú.',
    saludo: 'Hasta que cierren las inscripciones, nadie es rival seguro: esto es un mapa de probables. El que más te quita votos no siempre es el que más votos tiene, sino el que los saca en tus mismos puestos. Y si vas en lista abierta, el rival de adentro pesa tanto como el de afuera.',
    chips: ['¿Qué quiere decir la afinidad?', '¿Por qué hay rivales en «no sabemos»?', '¿Cómo se calcula la presión?', '¿Cómo funciona la revisión mensual?']
  };
  const SIN_VISTA = { titulo: 'Candidato 360', texto: 'Te voy diciendo qué hace cada parte de la plataforma. Pregúntame por lo que estés mirando.', chips: [] };
  const SIN_SESION = 'Para preguntarme por escrito necesito que inicies sesión; así sé de qué campaña estamos hablando. La guía de esta pantalla no depende de eso.';

  /* La sesión: en el CRM es `SESSION`; en las páginas de módulo, la de
     candidato-360-panel.js. Se lee a demanda, nunca se copia. */
  function ses() {
    try { if (typeof SESSION !== 'undefined' && SESSION) return SESSION; } catch {}
    return window.C360Panel?.SESION || null;
  }
  const volverAca = () => `login.html?next=${encodeURIComponent(location.pathname.split('/').pop() || 'candidato-360.html')}`;

  /* ─── Lo que Candi sabe de la vista: se lee del DOM, no del estado interno.
     Así nunca le dice al usuario algo distinto de lo que tiene en pantalla. */
  function contexto() {
    const pantalla = document.querySelector('.screen:not(.hidden)');
    const vista = document.body?.dataset?.candiVista || pantalla?.id || '';
    const ctx = { vista };
    const txt = id => document.getElementById(id)?.textContent?.trim() || '';
    if (vista === 'crm') {
      ctx.campana = txt('crmTarget');                                  /* «Candidatura 2027 · Concejo … · Bogotá» */
      const meta = txt('crmVoteNumber'); if (meta && meta !== '—' && meta !== '…') ctx.meta = meta;
      ctx.vitrina = document.getElementById('crm')?.classList.contains('en-vitrina') || false;
    }
    const paso = pantalla?.querySelector('.paso:not(.hidden)[data-paso]');
    if (paso) ctx.paso = paso.dataset.paso;
    const S = ses(); ctx.sesion = Boolean(S?.token); ctx.acceso = Boolean(S?.acceso);
    return ctx;
  }

  /* El primer nombre, SOLO para saludar en el navegador: no viaja al modelo.
     Se busca donde ya esté (candidatura abierta, wizard, vínculo de la cuenta);
     si no hay ninguno, el saludo va sin nombre y ya. */
  function primerNombre() {
    let n = '';
    try { n = crmCandidate?.nombre || ''; } catch {}
    if (!n) { try { n = NUEVO?.nombre || ''; } catch {} }
    if (!n) { const v = ses()?.vinculo; n = v?.candidato?.nombre || v?.nuevo?.nombre || ''; }
    const p = String(n).trim().split(/\s+/)[0] || '';
    if (p.length < 2 || /\d/.test(p)) return '';
    /* El índice electoral guarda los nombres en MAYÚSCULAS. */
    try { return NOMBRE_BONITO(p); } catch { return p.charAt(0).toUpperCase() + p.slice(1).toLowerCase(); }
  }

  /* ═══ LOS TEMAS: lo que Candi comenta según lo que escogiste (1-oct-2026) ══
     El `saludo` de cada vista es uno y fijo. Los TEMAS dependen de la campaña
     que la persona armó —corporación, partido o firmas, si cambia de
     corporación, la ciudad— y de qué módulos existen para su territorio
     (arquetipos solo en Medellín y Cartagena, barrios solo donde hay
     cartografía, firmas solo en cargo uninominal por firmas).

     Cada tema: { id, si(p) → ¿aplica?, texto(p), chip?, mod?, cambio? }
       · `mod`    (solo CRM) selector de la tarjeta: Candi lo comenta cuando la
                  persona se detiene en ella (≥60 % visible, 2,5 s).
       · `cambio` se dice en cuanto la selección lo vuelve cierto (la ruta y el
                  wizard): es la respuesta a lo que se acaba de escoger.
       · sin los dos: tema general, sale solo un rato después del saludo.
     Todos van además a la guía del panel («Para tu campaña») y, si traen
     `chip`, a las preguntas sugeridas. Cada tema se dice UNA vez por pestaña.

     ⚠️ Mismas reglas que la guía: ninguna cifra de la campaña sale de acá (las
     da la página) y nada promete un resultado. Lo que se afirma del producto
     tiene que ser cierto del producto: al cambiar un módulo, revisar su tema. */
  const CORP_NOMBRE = { jal: 'la JAL', concejo: 'el Concejo', alcaldia: 'la Alcaldía', asamblea: 'la Asamblea', gobernacion: 'la Gobernación' };
  const CIUDAD_NOMBRE = { BOGOTA: 'Bogotá', MEDELLIN: 'Medellín', CALI: 'Cali', CARTAGENA: 'Cartagena' };
  const normT = s => String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().replace(/[^A-Z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim();
  function corpDeTexto(s) {
    const t = normT(s);
    if (/\bJAL\b|JUNTA ADMIN|\bEDIL/.test(t)) return 'jal';
    if (/CONCEJO/.test(t)) return 'concejo';
    if (/ALCALD/.test(t)) return 'alcaldia';
    if (/ASAMBLEA/.test(t)) return 'asamblea';
    if (/GOBERN/.test(t)) return 'gobernacion';
    return '';
  }
  /* «Cali» va con límite de palabra: CALIMA contiene CALI (mismo gotcha del CRM). */
  function ciudadDeTexto(s) {
    const t = ' ' + normT(s) + ' ';
    for (const c of ['BOGOTA', 'MEDELLIN', 'CARTAGENA']) if (t.includes(' ' + c + ' ') || t.includes(c)) return c;
    return / CALI /.test(t) || t.includes('SANTIAGO DE CALI') ? 'CALI' : '';
  }
  const valor = id => document.getElementById(id)?.value || '';
  const textoSel = id => { const s = document.getElementById(id); return s?.options?.[s.selectedIndex]?.value ? s.options[s.selectedIndex].text : ''; };
  const marcado = n => document.querySelector(`input[name="${n}"]:checked`)?.value || '';

  /* Lo que la persona escogió, leído a demanda de donde esté: el formulario
     mientras lo llena, la campaña guardada después. Nunca se copia. */
  function perfil() {
    const S = ses(), v = S?.vinculo || null, ctx = contexto(), vista = ctx.vista;
    let camp = null; try { camp = CAMPANA_ACTUAL || null; } catch {}
    camp = camp || v?.campana || {};
    let cand = null; try { cand = crmCandidate || null; } catch {}
    let pais = ''; try { pais = PAIS || ''; } catch {}
    const p = { vista, sesion: ctx.sesion, acceso: ctx.acceso, vitrina: !!ctx.vitrina, vinculada: !!v, pais,
      corp: '', aval: '', partido: '', espectro: '', historial: false, salto: false, lugar: '', paso: ctx.paso || '' };

    if (vista === 'candidateRoute') {
      const ruta = marcado('corporationRoute');
      const corpHist = corpDeTexto(document.getElementById('sameCorporationLabel')?.textContent || cand?.corp || '');
      p.historial = true;
      p.corp = ruta === 'other' ? valor('otherCorporation') : ruta === 'same' ? corpHist : '';
      p.salto = ruta === 'other' && !!p.corp && p.corp !== corpHist;
      p.aval = marcado('avalRuta');
      p.partido = valor('campaignParty').trim();
      p.lugar = [textoSel('campaignLocality'), textoSel('campaignMunicipality'), textoSel('campaignDepartment'), ruta === 'same' ? (cand?.corp || '') : ''].join(' ');
    } else if (vista === 'new') {
      p.corp = valor('election');
      const modo = valor('partyMode');
      p.aval = modo === 'indeciso' ? 'indeciso' : 'partido';
      p.partido = modo === 'new' ? valor('partyName') : valor('party');
      p.lugar = [textoSel('locality'), textoSel('municipality'), textoSel('department')].join(' ');
    } else {
      p.historial = v ? v.tipo !== 'nuevo' : !!cand;
      const corpHist = corpDeTexto(v?.candidato?.corp || cand?.corp || '');
      p.corp = camp.corp || corpDeTexto(ctx.campana || '') || corpHist;
      p.salto = p.historial && camp.ruta === 'other' && !!corpHist && p.corp !== corpHist;
      p.aval = camp.avales || '';
      p.partido = camp.partido || (camp.avales && camp.avales !== 'partido' ? '' : (v?.candidato?.partido || cand?.partido || ''));
      p.espectro = camp.espectro || '';
      p.lugar = [camp.localidad, camp.municipio, camp.departamentoNombre, ctx.campana, camp.ruta === 'other' ? '' : (v?.candidato?.corp || cand?.corp || '')].filter(Boolean).join(' ');
      p.briefing = !!v?.briefing?.activo;
      p.escucha = !!(v?.escucha?.preferencias?.medios?.length || v?.escucha?.cuentas?.length);
    }
    p.uninominal = p.corp === 'alcaldia' || p.corp === 'gobernacion';
    p.departamental = p.corp === 'asamblea' || p.corp === 'gobernacion';
    p.lista = p.corp === 'concejo' || p.corp === 'asamblea' || p.corp === 'jal';
    p.ciudad = p.departamental ? '' : ciudadDeTexto(p.lugar);
    p.ciudadNombre = CIUDAD_NOMBRE[p.ciudad] || '';
    p.cargo = CORP_NOMBRE[p.corp] || 'tu corporación';
    p.arquetipos = p.ciudad === 'MEDELLIN' || p.ciudad === 'CARTAGENA';
    p.barrios = !!p.ciudad;                       /* las cuatro con cartografía barrial en el CRM */
    p.firmas = p.uninominal && p.aval === 'firmas';
    p.sinPartido = p.aval === 'firmas' || p.aval === 'indeciso';
    return p;
  }

  /* Los temas que se repiten en la ruta y en el wizard: dependen de lo mismo. */
  const T_CORP = [
    { id: 'uninominal', cambio: true, si: p => p.uninominal,
      texto: p => `A ${p.cargo} gana una sola persona: tu meta no es una curul, es el ganador de 2023 traído a 2027. Por eso el partido no la mueve; lo que sí cambia es dónde buscas esos votos.`,
      chip: '¿Por qué mi meta es el ganador de 2023?' },
    { id: 'curules', cambio: true, si: p => p.corp === 'concejo' || p.corp === 'asamblea',
      texto: p => `En ${p.cargo} se reparten curules por cifra repartidora: cuentan los votos de toda tu lista, no solo los tuyos. Por eso el partido sí mueve la meta.`,
      chip: '¿Cómo se reparten las curules?' },
    { id: 'jal', cambio: true, si: p => p.corp === 'jal',
      texto: () => 'En la JAL compites en una sola localidad o comuna. Para la meta uso las curules oficiales de cada Junta; donde no las tengo, las infiero de la lista más larga inscrita en 2023 y te lo digo.',
      chip: '¿Cuántas curules tiene mi Junta?' },
    { id: 'departamental', cambio: true, si: p => p.departamental,
      texto: () => 'Tu territorio es el departamento entero: en el tablero el mapa deja de ir por barrios y pasa a municipios.' },
    { id: 'cartagena-jal', cambio: true, si: p => p.ciudad === 'CARTAGENA' && p.corp === 'jal',
      texto: () => 'En Cartagena las Juntas se eligen por localidad, no por unidad comunera: son tres. En el mapa vas a poder cambiar de escala entre localidad, UCG y barrio.' },
    { id: 'firmas', cambio: true, si: p => p.firmas,
      texto: () => 'Por firmas te pido tu familia política porque las firmas se recogen más rápido donde esa familia vota. En el tablero se abre un módulo que te dice cuántas necesitas y en qué zonas cuesta menos.',
      chip: '¿Dónde recojo las firmas?' },
    { id: 'indeciso', cambio: true, si: p => p.aval === 'indeciso',
      texto: () => 'Sin partido todavía, calculo todo con tu familia política: la meta, el mapa y el electorado. Cuando lo tengas, en el tablero hay un botón para ponerlo y todo se recalcula.' },
    { id: 'partido', cambio: true, si: p => p.aval === 'partido' && !!p.partido && p.lista,
      texto: () => 'Con tu partido mido dónde vota su lista. Si no tuvo lista aquí en 2023, uso su lista a Cámara de 2026; y si tampoco, su familia política. Siempre te digo con cuál medí.',
      chip: '¿Con qué votos se mide mi partido?' }
  ];

  const TEMAS = {
    intro: [
      { id: 'vinculada', si: p => p.vinculada,
        texto: () => 'Tu cuenta ya está vinculada a una candidatura: entres por donde entres, te llevo a ella. Cambiar de persona solo se hace escribiéndole a soporte; la corporación y el territorio sí los cambias tú.' },
      { id: 'sin-sesion', si: p => !p.sesion,
        texto: () => 'Puedes mirar la portada sin cuenta. Para buscarte y abrir tu tablero necesito que inicies sesión: así sé de qué campaña estamos hablando.' },
      { id: 'vitrina-antes', si: p => p.sesion && !p.acceso,
        texto: () => 'Aunque todavía no tengas plan, puedes abrir tu tablero en vista previa: ves el mapa, tu historial y la meta. El detalle por barrio y por puesto, y los módulos, se abren al activarlo.' },
      { id: 'pais', si: p => p.pais === 'ec' || p.pais === 'py',
        texto: () => 'Los módulos son los mismos en los tres países; lo que cambia son los datos electorales y la cartografía de cada uno.' }
    ],
    existing: [
      { id: 'cobertura', si: () => true,
        texto: () => 'Tengo concejos, asambleas, JAL, alcaldías y gobernaciones de 2011, 2015, 2019 y 2023, y Congreso desde 2014. Si tu candidatura es anterior, no va a aparecer.' },
      { id: 'forma-corta', si: () => true,
        texto: () => 'Si no te encuentras, prueba también con tu primer nombre y tu primer apellido: en algunas elecciones la Registraduría inscribe la forma corta del nombre.' }
    ],
    candidateRoute: [
      { id: 'misma-territorial', si: p => p.paso === 'ruta',
        texto: () => '«La misma corporación» solo te la ofrezco si tu última candidatura fue territorial. Si vienes del Senado, la Cámara o una consulta, escoge a cuál te lanzas.' },
      { id: 'salto', cambio: true, si: p => p.salto,
        texto: () => 'Cambias de corporación: tu votación anterior la uso para ver dónde ya tienes gente, pero la meta sale del territorio nuevo. Si tus votos venían de un territorio más grande, en el mapa solo cuento los que caen dentro del nuevo y te digo cuántos quedaron por fuera.',
        chip: '¿Qué pasa con mis votos de antes?' },
      ...T_CORP
    ],
    new: [
      { id: 'nuevo-base', si: () => true,
        texto: p => p.uninominal
          ? `Sin historial propio, tu punto de partida es el territorio: los resultados de 2023 del lugar al que aspiras. Tu partido no cambia la meta de ${p.cargo}, pero sí dónde te conviene buscar votos.`
          : 'Sin historial propio, tu punto de partida es el territorio: lo que sacó tu familia política ahí en 2023. Por eso el partido o el espectro importan tanto como el lugar.' },
      ...T_CORP
    ],
    crm: [
      { id: 'vitrina', si: p => p.vitrina,
        texto: () => 'Estás en vista previa. Los tres lugares con más votos se ven nítidos; el resto del detalle y los módulos de abajo se abren al activar tu plan.' },
      { id: 'pendiente-partido', si: p => p.aval === 'indeciso',
        texto: () => 'Recuerda que estás midiendo con tu familia política. Cuando tengas partido, el botón de arriba lo pone y todo se recalcula con su huella.' },
      { id: 'mapa-recorte', mod: '#crmMap', si: p => p.salto,
        texto: () => 'Como cambias de corporación, el mapa es el del territorio nuevo: tus votos de antes solo cuentan si caen dentro de él, y si quedaron por fuera te lo digo debajo. «Proyectado» reparte tu meta por ese territorio.' },
      { id: 'mapa-historial', mod: '#crmMap', si: p => p.historial && !p.salto,
        texto: () => '«Total» es lo que sacaste; «Proyectado» reparte tu meta donde ya tienes gente. Toca una zona del mapa para bajar de nivel.' },
      { id: 'mapa-censo', mod: '#crmMap', si: p => !p.historial && p.barrios && (p.corp === 'concejo' || p.corp === 'alcaldia'),
        texto: p => `Sin votos propios en ${p.ciudadNombre}, «Total» te muestra el censo electoral —cuánta gente puede votar en cada zona— y «Proyectado», dónde sacó votos tu familia política en 2023.` },
      { id: 'barrios', mod: '#crmMap', si: p => p.barrios && p.historial,
        texto: p => `En ${p.ciudadNombre} puedo bajar hasta el barrio. Los barrios sin puesto propio salen punteados: toman el color del vecino más cercano y no suman a ningún total.` },
      { id: 'meta-uninominal', mod: '.crm-vote-target', si: p => p.uninominal,
        texto: p => `En ${p.cargo} gana uno solo, así que tu meta es el ganador de 2023 traído a 2027. La ⓘ te explica de dónde sale.` },
      { id: 'meta-escalones', mod: '.crm-vote-target', si: p => p.lista,
        texto: () => 'Los cuatro escalones van de menos a más esfuerzo. Inminente es la mitad del probable; posible es lo que costó la curul en una lista más exigente de 2023; deseado es ganarla solo con tus votos. El que escojas es el que guardo como meta.',
        chip: '¿Qué escalón de la meta escojo?' },
      { id: 'briefing', mod: '#crmBriefing', si: p => !p.briefing && !p.vitrina,
        texto: p => `El briefing es lo único que trabaja sin que entres: cada tres días te llega la prensa de tu territorio, los contratos que firmó tu ${p.departamental ? 'departamento' : 'municipio'}${p.corp === 'jal' ? ' y tu Alcaldía Local' : ''} y las normas que lo tocan. Se enciende con un clic.` },
      { id: 'escucha', mod: '#crmEscucha', si: p => !p.escucha,
        texto: () => 'La escucha arranca con dos preguntas: qué redes usas y qué medios quieres leer. Antes de montarla compruebo que cada cuenta sea la tuya: un homónimo o una cuenta vieja arruinan la lectura.' },
      { id: 'arq-medellin', mod: '#crmArquetipos', si: p => p.ciudad === 'MEDELLIN',
        texto: () => 'En Medellín los arquetipos son cinco familias emocionales por barrio. No te dicen a quién hablarle sino cómo: el mismo mensaje se escucha distinto en un barrio de protección que en uno de castigo.' },
      { id: 'arq-cartagena', mod: '#crmArquetipos', si: p => p.ciudad === 'CARTAGENA',
        texto: () => 'Cartagena tiene ocho arquetipos propios, no los de Medellín, y cada barrio es una mezcla de ellos. Ojo: 2023 es proyección y 2027 es simulación.' },
      { id: 'arq-no', mod: '#crmArquetipos', si: p => !p.arquetipos,
        texto: () => 'Los arquetipos hoy existen para Medellín y Cartagena. Para tu territorio, lo que más te dice a quién hablarle es el perfil del votante, la tarjeta de al lado.' },
      { id: 'electorado', mod: '#crmPerfil', si: () => true,
        texto: p => `Ahí ves a quién puede votar, no solo a quién votó: el censo de 2026 por sexo y edad en tus puestos${p.sinPartido ? ', medido con tu familia política' : ''}. Empieza por los perfiles que salen marcados como viables.` },
      { id: 'firmas-mod', mod: '#crmFirmas', si: p => p.firmas,
        texto: () => 'Este módulo aparece porque vas por firmas: cuántas necesitas y en qué zonas cuesta menos recogerlas, según dónde vota tu familia política.' },
      { id: 'endoso', mod: '#crmEndoso', si: () => true,
        texto: () => 'Antes de sumar aliados, piensa a quién apoyó cada uno la vez pasada: con eso mido cuánto pasó de verdad. Los nombres de tus líderes se quedan en tu navegador.' },
      { id: 'diad-territorio', mod: '#crmDiaD', si: p => p.salto || !p.historial,
        texto: () => 'Como compites en un territorio donde no tienes votación propia, el plan de testigos se ordena con los votos de tu familia política en 2023, puesto por puesto.' },
      { id: 'diad-propio', mod: '#crmDiaD', si: p => p.historial && !p.salto,
        texto: () => 'Tu plan de testigos sale de tu propia votación: unos pocos puestos juntan la mayor parte. Mira cuántos de esos no tienen señal antes de contar testigos.' },
      { id: 'cont-uninominal', mod: '#crmContendientes', si: p => p.uninominal,
        texto: () => 'En un cargo de uno solo, el rival que más te quita no es el de más votos sino el que los saca en tus mismos puestos.' },
      { id: 'cont-lista', mod: '#crmContendientes', si: p => p.lista,
        texto: () => 'Si tu lista es abierta, en el módulo también vas a ver quién te compite dentro de tu propia lista: ese rival pesa tanto como el de afuera.' }
    ],
    electorado: [
      { id: 'medida-familia', si: p => p.sinPartido,
        texto: () => 'Como todavía no hay partido, mido «dónde sacas votos» con tu familia política; si esa familia no tuvo lista aquí, con sus vecinas del espectro. Arriba de los perfiles te digo con cuál.' },
      { id: 'medida-partido', si: p => p.aval === 'partido' && !!p.partido,
        texto: () => 'Mido con la lista de tu partido en 2023; si no tuvo, con su lista a Cámara de 2026; y si tampoco, con su familia. Arriba de los perfiles dice cuál usé.' },
      { id: 'escala-cartagena', si: p => p.ciudad === 'CARTAGENA',
        texto: () => 'En Cartagena puedes leerlo por localidad, por unidad comunera o por barrio: está en el selector de escala.' },
      { id: 'barrios-clic', si: p => p.ciudad === 'BOGOTA' || p.ciudad === 'CALI',
        texto: p => `En ${p.ciudadNombre}, al tocar una zona del mapa bajas a sus barrios.` },
      { id: 'departamento', si: p => p.departamental,
        texto: () => 'Como compites en todo el departamento, el mapa va por municipios.' },
      { id: 'crecimiento', si: () => true, chip: '¿Dónde crecieron las cédulas?',
        texto: () => 'La pestaña de crecimiento del censo es tu pista para inscribir cédulas: compara 2023 con 2026. Puesto por puesto léela con cuidado, porque se abrieron y cerraron puestos.' }
    ],
    arquetipos: [
      { id: 'lentes', si: () => true,
        texto: () => 'Arriba puedes cambiar la lente: tus votos, tu partido o la ciudad entera. El arquetipo «más afín» es el que pesa más en tu votación que en la ciudad, no el más grande.',
        chip: '¿Qué quiere decir «más afín»?' },
      { id: 'sin-votos', si: p => !p.historial || p.salto,
        texto: () => 'Si todavía no tienes votos en la ciudad, abro con la lente de tu partido o tu familia: lo que ves es dónde está tu gente posible, no tus votantes.' },
      { id: 'cartagena', si: p => p.ciudad === 'CARTAGENA',
        texto: () => 'En Cartagena cada barrio es una mezcla de ocho arquetipos, así que tus votos se reparten entre varios. La ficha trae las palancas de cada uno: úsalas para escoger el tono.' },
      { id: 'otra-ciudad', si: p => !p.arquetipos,
        texto: () => 'Tu campaña no es en Medellín ni en Cartagena, que son las dos ciudades con arquetipos. Lo que ves acá es la ciudad, no tu territorio.' }
    ],
    diad: [
      { id: 'fuente-territorio', si: p => p.salto || !p.historial,
        texto: () => 'Como no tienes votación propia en este territorio, los puestos van ordenados por los votos de tu familia política en 2023. Tus votos de antes, si caen aquí, salen marcados aparte.' },
      { id: 'departamento', si: p => p.departamental,
        texto: () => 'Compites en el departamento, así que el plan cubre puestos de muchos municipios: fíjate en cuáles caen los primeros antes de repartir testigos.' },
      { id: 'csv', si: () => true,
        texto: () => 'El plan baja con la columna de testigo en blanco: los nombres los pones tú en tu archivo. Nunca los pedimos ni los guardamos.' }
    ],
    endoso: [
      { id: 'lista', si: p => p.lista,
        texto: () => 'Abajo está la escalera de tu propia lista: con voto preferente, tu compañero de lista también es tu rival.' },
      { id: 'agregar', si: () => true,
        texto: () => 'Si falta alguien que ya suena, agrégalo tú: desde el registro, con sus votos, o solo con el nombre, que se queda en tu navegador.' }
    ]
  };

  /* Lo que viaja al modelo de lo escogido: solo categorías, nunca el nombre ni
     el lugar exacto. Le basta para no responder del Concejo a quien se lanza
     a la Gobernación. El worker valida contra sus propias listas. */
  function seleccion() {
    const p = perfil();
    return { corp: p.corp, aval: p.aval, historial: p.historial, salto: p.salto, ciudad: p.ciudad,
      arquetipos: p.arquetipos, firmas: p.firmas };
  }
  function temasDe(p = perfil()) {
    return (TEMAS[p.vista] || []).filter(t => { try { return t.si(p); } catch { return false; } })
      .map(t => ({ ...t, clave: `${p.vista}:${t.id}`, dicho: (() => { try { return t.texto(p); } catch { return ''; } })() }))
      .filter(t => t.dicho);
  }

  /* ─── Andamiaje ──────────────────────────────────────────────────────── */
  const esc = s => String(s == null ? '' : s).replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
  let dock, panel, escena, launcher, globo, log, input, enviar, guia, chips, mascota = null;
  let abierto = false, entroYa = false, enVuelo = false, vistaPintada = '';
  /* ─── La memoria de la sesión ──────────────────────────────────────────
     Cada módulo es una página aparte, así que sin esto Candi entraba
     caminando y decía «¡Hola! Soy Candi…» en cada clic del tablero (pedido de
     Ricardo, 30-sep-2026). Ahora se presenta UNA vez por pestaña; en las demás
     cargas ya está sentada y, si tiene algo que decir de esa pantalla, lo dice
     una sola vez. sessionStorage y no localStorage a propósito: abrir la
     plataforma otro día merece la entrada otra vez. */
  const MEMORIA_KEY = 'candi-sesion-v1';
  const memoria = (() => { try { return Object.assign({ presentada: false, dichas: [], temas: [] }, JSON.parse(sessionStorage.getItem(MEMORIA_KEY) || '{}')); } catch { return { presentada: false, dichas: [], temas: [] }; } })();
  if (!Array.isArray(memoria.temas)) memoria.temas = [];
  function recordar() { try { sessionStorage.setItem(MEMORIA_KEY, JSON.stringify(memoria)); } catch {} }
  const yaDicha = v => memoria.dichas.includes(v);
  function marcarDicha(v) { if (v && !yaDicha(v)) { memoria.dichas.push(v); recordar(); } }
  const historial = [];                                    /* {rol, texto} — se manda recortado */

  function montar() {
    dock = document.createElement('div');
    dock.className = 'candi-dock'; dock.id = 'candiDock'; dock.hidden = true;
    dock.style.setProperty('--candi-atlas', `url("${ATLAS}")`);
    dock.innerHTML = `
      <section class="candi-panel" id="candiPanel" role="dialog" aria-labelledby="candiTitulo" hidden>
        <header class="candi-head">
          <div>
            <div class="kicker">Candidato 360</div>
            <h2 id="candiTitulo">Candi</h2>
            <p>Tu guía de la plataforma. Te digo qué hace cada parte y dónde está cada cosa.</p>
          </div>
          <button type="button" class="candi-min" id="candiMin" aria-label="Cerrar el panel de Candi">–</button>
        </header>
        <div class="candi-cuerpo">
          <div class="candi-guia" id="candiGuia"></div>
          <div class="candi-chips" id="candiChips"></div>
          <div class="candi-log" id="candiLog" role="log" aria-live="polite" aria-label="Conversación con Candi"></div>
        </div>
        <div class="candi-pie">
          <form class="candi-form" id="candiForm">
            <label class="hidden" for="candiInput">Pregúntale a Candi</label>
            <input id="candiInput" type="text" autocomplete="off" maxlength="400" placeholder="¿Qué quieres saber de esta pantalla?">
            <button type="submit" id="candiEnviar">Enviar</button>
          </form>
          <p class="candi-nota" id="candiNota"></p>
        </div>
      </section>
      <div class="candi-globo" id="candiGlobo" role="status" hidden>
        <p id="candiGloboTexto"></p>
        <button type="button" class="candi-globo-x" id="candiGloboX" aria-label="Cerrar el saludo de Candi">×</button>
      </div>
      <div class="candi-stage candi-escena" id="candiEscena" aria-hidden="true"></div>
      <button type="button" class="candi-launcher" id="candiLauncher" aria-expanded="false" aria-controls="candiPanel">
        <span class="candi-cara" aria-hidden="true"></span><span class="candi-launcher-txt">Pregúntame</span>
      </button>`;
    document.body.append(dock);
    panel = dock.querySelector('#candiPanel'); escena = dock.querySelector('#candiEscena');
    launcher = dock.querySelector('#candiLauncher'); log = dock.querySelector('#candiLog');
    input = dock.querySelector('#candiInput'); enviar = dock.querySelector('#candiEnviar');
    guia = dock.querySelector('#candiGuia'); chips = dock.querySelector('#candiChips');
    globo = dock.querySelector('#candiGlobo');

    launcher.addEventListener('click', () => abierto ? cerrar({ foco: true }) : abrir());
    dock.querySelector('#candiMin').addEventListener('click', () => cerrar({ foco: true }));
    globo.querySelector('p').addEventListener('click', abrir);
    globo.querySelector('#candiGloboX').addEventListener('click', e => { e.stopPropagation(); ocultarGlobo(); });
    dock.querySelector('#candiForm').addEventListener('submit', e => { e.preventDefault(); preguntar(input.value); });
    /* Escape cierra, pero solo si el foco está adentro: si hay un modal del
       CRM encima, la tecla es suya. */
    document.addEventListener('keydown', e => {
      if (e.key !== 'Escape' || !abierto || !dock.contains(document.activeElement)) return;
      e.stopPropagation(); cerrar({ foco: true });
    });
    /* La guía se repinta al cambiar de pantalla; la animación NO se repite.
       Se observan las cinco pantallas y nada más: dentro del CRM, Leaflet
       cambia clases sin parar y un observador con subtree se dispararía
       miles de veces por sesión. */
    const obsVista = new MutationObserver(() => {
      if (abierto) pintarGuia();
      /* showScreen toca la clase de las cinco pantallas de una: un solo turno. */
      if (!alCambiarVista._t) alCambiarVista._t = setTimeout(() => { alCambiarVista._t = 0; alCambiarVista(); }, 60);
    });
    document.querySelectorAll('.screen').forEach(s => obsVista.observe(s, { attributes: true, attributeFilter: ['class'] }));
    /* Lo que se escoge en la ruta o el wizard: un turno por ráfaga de cambios. */
    const enSeleccion = e => {
      if (!e.target.closest?.('#candidateRoute, #new')) return;
      clearTimeout(enSeleccion._t); enSeleccion._t = setTimeout(alCambiarSeleccion, 450);
    };
    document.addEventListener('change', enSeleccion);
    relojGenerales = setInterval(tocaGeneral, 10000);
    window.addEventListener('pagehide', destruir, { once: true });
  }
  let relojGenerales = 0;

  /* Al cambiar de pantalla dentro de la misma página (portada → buscador →
     ruta → CRM) Candi comenta la nueva, una vez por sesión. Volver a la
     portada ya no la hace repetirse: si ya lo dijo, se queda callada. */
  let vistaComentada = '';
  function alCambiarVista() {
    ubicarEnPortada();
    if (!dock.hidden && !entroYa) entrar();
    else if (!dock.hidden && contexto().vista !== 'intro') mascota?.idle().catch(() => {});
    const v = contexto().vista;
    if (v === vistaComentada) return;
    vistaComentada = v;
    vigilarTarjetas();
    if (!presentada || abierto || calculando) return;
    const texto = VISTAS[v]?.saludo;
    /* Un comentario de la pantalla anterior no se queda colgado sobre la nueva. */
    if (!texto || yaDicha(v)) { if (!globo.hidden && globo.dataset.aviso !== 'calculo') ocultarGlobo(); return; }
    marcarDicha(v);
    decir(texto, 22000);
  }
  function pintarGuia() {
    const p = perfil(), temas = temasDe(p);
    const llave = p.vista + '|' + temas.map(t => t.id).join(',');
    if (llave === vistaPintada) return;
    vistaPintada = llave;
    const g = VISTAS[p.vista] || SIN_VISTA;
    /* «Para tu campaña»: lo mismo que Candi comenta en el globo, escrito y
       siempre a la mano. Es la versión accesible de los comentarios. */
    const lista = temas.slice(0, 5);
    guia.innerHTML = `<h3>${esc(g.titulo)}</h3><p>${esc(g.texto)}</p>` +
      (lista.length ? `<div class="candi-temas"><h4>Para tu campaña</h4><ul>${lista.map(t => `<li>${esc(t.dicho)}</li>`).join('')}</ul></div>` : '');
    const sugeridas = [...new Set([...(g.chips || []), ...temas.map(t => t.chip).filter(Boolean)])].slice(0, 6);
    chips.innerHTML = sugeridas.map(c => `<button type="button" class="candi-chip">${esc(c)}</button>`).join('');
    chips.querySelectorAll('.candi-chip').forEach(b => b.addEventListener('click', () => { input.value = b.textContent; input.focus(); }));
  }

  /* ─── Los comentarios: Candi dice los temas sola, sin que se le pregunte ──
     Tres disparadores, y ninguno interrumpe: con el panel abierto, un cálculo
     en curso o el globo ocupado, espera.
       1. CAMBIO de selección en la ruta o el wizard → el tema que esa
          selección acaba de volver cierto, de una (es la respuesta a lo que
          se escogió; no espera turno).
       2. En el CRM, detenerse en una TARJETA (≥60 % visible 2,5 s) → su tema.
       3. Un tema general, ~30 s después de que se fue el último globo; como
          mucho tres por carga. Más que eso sería una mascota que no se calla.
     Cada tema, una vez por pestaña (`memoria.temas`). */
  const PAUSA_ENTRE = 25000, MAX_GENERALES = 3;
  let ultimoComentario = Date.now(), generalesDichos = 0;   /* el reloj arranca con la página: nada antes del saludo */
  const temaDicho = t => memoria.temas.includes(t.clave);
  function libre() { return !dock.hidden && !(document.getElementById('partidaSaludo') && contexto().vista === 'intro') && presentada && !abierto && !calculando && globo && globo.hidden; }
  function comentar(t) {
    if (!t || temaDicho(t)) return false;
    if (!decir(t.dicho, 20000)) return false;
    memoria.temas.push(t.clave); recordar();
    ultimoComentario = Date.now();
    return true;
  }
  function alCambiarSeleccion() {
    const p = perfil();
    if (p.vista !== 'candidateRoute' && p.vista !== 'new') return;
    if (abierto) pintarGuia();
    if (!presentada || calculando) return;
    const t = temasDe(p).find(x => x.cambio && !temaDicho(x));
    if (t) comentar(t);
  }
  function tocaGeneral() {
    if (!libre() || generalesDichos >= MAX_GENERALES) return;
    if (Date.now() - ultimoComentario < PAUSA_ENTRE + 5000) return;
    const t = temasDe().find(x => !x.mod && !temaDicho(x));
    if (t && comentar(t)) generalesDichos++;
  }
  /* Las tarjetas del CRM: un observador por tarjeta con tema. Se arma cuando
     el CRM aparece; antes sus tarjetas están ocultas y no hay qué observar. */
  let obsTarjetas = null;
  function vigilarTarjetas() {
    if (obsTarjetas || typeof IntersectionObserver !== 'function' || contexto().vista !== 'crm') return;
    const relojes = new Map();
    obsTarjetas = new IntersectionObserver(entradas => entradas.forEach(e => {
      clearTimeout(relojes.get(e.target));
      if (!e.isIntersecting || e.intersectionRatio < .6) return;
      relojes.set(e.target, setTimeout(() => {
        if (!libre() || Date.now() - ultimoComentario < PAUSA_ENTRE || contexto().vista !== 'crm') return;
        const t = temasDe().find(x => x.mod && (e.target.matches(x.mod) || e.target.querySelector(x.mod)) && !temaDicho(x));
        if (t) comentar(t);
      }, 2500));
    }), { threshold: [0, .6] });
    const selectores = [...new Set(TEMAS.crm.map(t => t.mod).filter(Boolean))];
    document.querySelectorAll(selectores.join(',')).forEach(el => obsTarjetas.observe(el.closest('article') || el));
  }

  /* El pie no promete lo que no hay: sin sesión, solo la guía escrita. */
  function pintarPie() {
    const nota = dock.querySelector('#candiNota');
    const hay = Boolean(ses()?.token);
    input.placeholder = hay ? '¿Qué quieres saber de esta pantalla?' : 'Inicia sesión para preguntarme';
    nota.innerHTML = hay
      ? 'Mis respuestas escritas las redacta un modelo. Explico la plataforma; las cifras de tu campaña salen de la página, no de mí.'
      : `La guía de arriba funciona siempre. Para preguntas escritas, <a href="${volverAca()}">inicia sesión</a>.`;
  }

  /* ─── La entrada: una sola vez por carga de la página ────────────────────
     Llega, saluda, se sienta y queda atenta con la cola en bucle suave
     (CandiAtletica, v3). El globo aparece al TERMINAR EL SALUDO, igual que con
     la v2 — y ojo, eso ya no es `candi:complete`: en la v3 ese evento llega a
     los 4,8 s, cuando ya se sentó, así que colgarse de él retrasaba el globo
     1,6 s sin que nadie lo decidiera. El fin del saludo es el paso a
     `sit_down`. Si la animación no avanza (atlas caído, pestaña que nunca se
     mostró), el globo entra igual a los 5 s. */
  function entrar() {
    if (entroYa) return; entroYa = true;
    if (typeof CandiAtletica !== 'function') { fallarAtlas('falta candi-atletica.js'); return mostrarGlobo(); }
    mascota = new CandiAtletica(escena);
    escena.addEventListener('candi:state', e => { escena.dataset.estado = e.detail?.state || ''; });
    escena.addEventListener('candi:reaction-complete', () => { escena.dataset.estado = 'idle_seated'; });
    /* Ya se presentó en esta pestaña: aparece sentada y atenta, sin caminar.
       `idle()` arranca en 4,8 s y no emite `candi:complete`, así que el
       descanso y el globo se enganchan a mano. */
    if (memoria.presentada && !document.getElementById('partidaSaludo')) {
      escena.dataset.estado = 'idle_seated';
      mascota.idle().catch(e => fallarAtlas(e && e.message));
      montarDescanso();
      setTimeout(mostrarGlobo, 900);          /* que alcance a verse sentada antes de hablar */
      return;
    }
    /* Dos señales, y gana la primera. Con animación, `sit_down` (3,2 s) llega
       antes que `candi:complete` (4,8 s). Con MOVIMIENTO REDUCIDO el reproductor
       salta directo al reposo y emite `candi:complete` sin pasar nunca por
       `sit_down`: colgarse solo de `sit_down` dejaba el globo esperando los 5 s
       del respaldo justo a quien no tiene ninguna animación que esperar. */
    let listo = false;
    const red = setTimeout(() => presentarse(), 5000);
    const alEstado = e => { if (e.detail?.state === 'sit_down') presentarse(); };
    function presentarse() {
      if (listo) return; listo = true;
      clearTimeout(red);
      escena.removeEventListener('candi:state', alEstado);
      escena.removeEventListener('candi:complete', presentarse);
      mostrarGlobo();
    }
    escena.addEventListener('candi:state', alEstado);
    escena.addEventListener('candi:complete', () => { escena.dataset.estado = 'idle_seated'; });
    escena.addEventListener('candi:complete', presentarse);
    escena.addEventListener('candi:complete', montarDescanso, { once: true });
    mascota.play().catch(e => { fallarAtlas(e && e.message); presentarse(); });
  }

  /* ─── El descanso con el hueso rosado ────────────────────────────────────
     Tras 20 s sin actividad, estando atenta, Candi cruza la pantalla de lado
     a lado, recoge su hueso con la boca y se echa (CandiBoneSequence, de
     Astra). Corre en una TIRA del ancho de la ventana, no en el dock: el dock
     mide 250 px y el recorrido tiene que ser de lado a lado. La tira es
     transparente a los clics.
     · Alterna (v2 del reproductor, 29-sep): derecha → izquierda → derecha…
       El reproductor guarda `side` (el último lado completado) y, al acabar
       echada, rearma la misma espera: el siguiente descanso sale DESDE DONDE
       ESTÁ hacia el extremo contrario, sin pasar por el dock. El extremo
       derecho es la casa (el dock vive pegado al borde derecho).
     · Una sola perrita visible: el reproductor oculta la del dock mientras
       camina, y al despertar se queda SENTADA Y ATENTA DONDE ESTÉ (una segunda
       CandiAtletica en la tira, `rincon`), con la del dock escondida. Si
       despierta en su casa, vuelve la del dock. Vuelve al dock al abrir el
       panel o cuando tiene que reaccionar (pensar, investigar).
     · Con el panel abierto no descansa (se está leyendo una respuesta), ni
       mientras piensa o investiga, ni con la pantalla tan baja que el dock
       esconde la escena. Al volver a estar libre arranca una espera COMPLETA.
     · UN solo temporizador: el del reproductor (`arm`). Acá no hay ninguno
       propio; inhibir es `enable(false)` y soltar es `enable(true)`, que
       rearma desde cero.
     · La pestaña oculta, el movimiento reducido y la actividad los maneja el
       propio reproductor; acá solo se limpia lo que se crea. */
  const DESCANSO_MS = 20000;
  const bajito = matchMedia('(max-height:520px)');
  let tira = null, descanso = null, rincon = null, origen = null;

  function montarDescanso() {
    if (descanso || !mascota || typeof CandiBoneSequence !== 'function') return;
    tira = document.createElement('div');
    tira.className = 'candi-bone-strip'; tira.setAttribute('aria-hidden', 'true');
    document.body.append(tira);
    ajustarSuelo();
    descanso = new CandiBoneSequence(tira, { mascot: mascota, inactivityMs: DESCANSO_MS, activityTarget: document });
    /* Tres ajustes al reproductor de Astra, como propiedades de la instancia
       (su código llama `this.layout()`, `this.play()` y `this.stop()`, así que
       las toma). El resto —registro vertical, recortes, tiempos— es el suyo.

       1) layout: el tamaño se parece al de la Candi del dock, para que no se
          note el cambio de reproductor; el INICIO es donde está la Candi que se
          ve (`origen`, que fija `play`) y el FIN es el extremo de `toSide`. El
          extremo derecho es la casa y no `ancho − tamaño − margen`: quedan a
          menos de 10 px, y así al despertar allá vuelve exactamente a su sitio. */
    const layoutBase = descanso.layout.bind(descanso);
    descanso.layout = () => {
      const g = layoutBase();
      const cs = getComputedStyle(mascota.sprite);   /* vale aunque el sprite esté oculto: es el CSS */
      const sw = parseFloat(cs.width) || g.size, der = parseFloat(cs.right) || 0;
      const size = Math.min(210, Math.max(100, sw * 1.1), Math.max(1, g.width - 24));
      const izq = g.margin, tope = Math.max(g.margin, g.width - size - g.margin);
      const acota = x => Math.max(izq, Math.min(tope, x));
      /* Sin escena a la vista (pantalla baja: el CSS la esconde) su caja mide
         cero y la «casa» caía en el borde IZQUIERDO; la casa es el derecho. */
      const r = escena.getBoundingClientRect();
      const casa = r.width ? acota(r.right - der - sw - tira.getBoundingClientRect().left + (sw - size) / 2) : tope;
      const extremo = lado => lado === 'left' ? izq : casa;
      const start = origen == null ? extremo(descanso.fromSide) : acota(origen);
      return { ...g, size, start, end: extremo(descanso.toSide), casa, izq };
    };
    /* 2) play: antes de salir se anota dónde está la Candi visible. Si ya está
          prácticamente en el extremo al que le tocaría ir (volvió al dock tras
          un viaje a la derecha, o la despertaron llegando), se invierte el lado:
          si no, caminaría en el sitio 1,4 s y dejaría el hueso bajo sus patas. */
    const playBase = descanso.play.bind(descanso);
    descanso.play = (...args) => {
      /* ⚠️ El `change` de la media query puede llegar tarde (visto al girar
         con la pestaña en segundo plano): si el temporizador se cumple con la
         pantalla ya baja, se hace aquí lo que haría `alCambiarAlto`. */
      if (bajito.matches) { alCambiarAlto(); return Promise.resolve(); }
      origen = posicionVisible();
      const g = descanso.layout(), destino = descanso.side === 'right' ? g.izq : g.casa;
      if (Math.abs(origen - destino) < g.size / 2) descanso.side = descanso.side === 'right' ? 'left' : 'right';
      return playBase(...args);
    };
    /* 3) stop: al restaurar, el reproductor corre el sprite al margen izquierdo
          si el último lado fue la izquierda. Eso sirve en su demo, donde el
          sprite y el recorrido comparten escenario; acá el sprite vive en el
          dock (250 px) y ese `left` lo descuadraba ahí dentro. La posición en
          la franja la pone `despertarDonde`. Y si hay una Candi sentada en la
          franja, la del dock sigue escondida: nunca dos a la vez.
          ⚠️ Y solo restaura si de verdad estaba en un recorrido: la
          restauración hace `mascot.seek(4800)`, y `enable(false)` (abrir el
          panel, mandar una pregunta, empezar un cálculo) pasa por acá aunque
          no esté caminando. Medido: esa llamada pisaba la lupa recién
          arrancada —la fase saltaba a `idle_seated` a mitad de la reacción—
          y dejaba la puerta abierta a pensar y a investigar a la vez. */
    const stopBase = descanso.stop.bind(descanso);
    descanso.stop = (restore = true) => {
      restore = restore && descanso.active;
      stopBase(restore);
      if (!restore || !mascota) return;
      mascota.sprite.style.left = ''; mascota.sprite.style.right = '';
      if (rincon) mascota.sprite.hidden = true;
    };
    /* El reproductor escucha `candi:state` en SU escenario; la mascota lo emite en el dock. */
    escena.addEventListener('candi:state', reenviarEstado);
    tira.addEventListener('candi:bone-state', alDescanso);
    tira.addEventListener('candi:bone-error', e => console.warn('[Candi] hueso:', e.detail?.message));
    bajito.addEventListener('change', alCambiarAlto);
    addEventListener('resize', alRedimensionar);
    habilitarDescanso();
  }
  /* Dónde está la Candi que se ve, en coordenadas de la franja: sentada en la
     franja, echada al final del viaje anterior, o en su casa. */
  function posicionVisible() {
    if (rincon) return rincon.x;
    const x = parseFloat(descanso.actor.style.left);
    if (descanso.active && !descanso.actor.hidden && Number.isFinite(x)) return x;
    return descanso.layout().casa;
  }
  const reenviarEstado = e => tira?.dispatchEvent(new CustomEvent('candi:state', { detail: e.detail }));
  /* Libre = panel cerrado, pantalla con escena, sin pregunta en vuelo y sin
     cálculo en curso (mientras investiga o piensa no se va por el hueso). */
  function habilitarDescanso() { descanso?.enable(!abierto && !bajito.matches && !enVuelo && !calculando && !(document.getElementById('candiBienvenida') && contexto().vista === 'intro')); }
  function alCambiarAlto() { if (bajito.matches) volverAlDock(); habilitarDescanso(); ajustarSuelo(); }

  /* La tira se apoya en la misma línea de suelo que la escena del dock. */
  function ajustarSuelo() {
    if (!tira || escena.hidden) return;
    const r = escena.getBoundingClientRect();
    if (!r.height) return;
    tira.style.setProperty('--candi-suelo', Math.max(0, innerHeight - r.bottom) + 'px');
  }
  function alRedimensionar() {
    ajustarSuelo();
    if (!rincon) return;
    const g = descanso.layout();                   /* girar el teléfono no la deja fuera */
    rincon.x = Math.max(g.margin, Math.min(rincon.x, g.width - g.size - g.margin));
    Object.assign(rincon.el.style, { left: rincon.x + 'px', width: g.size + 'px', height: g.size + 'px' });
  }

  /* Cuando el recorrido ya pinta su primer cuadro, la Candi sentada en la
     franja (si la había) sobra: el actor sale desde su misma posición. Ya no
     hay atajo «si está junto al hueso, a recogerlo»: el hueso ahora queda en
     el extremo contrario, así que siempre camina. */
  function alDescanso(e) {
    const st = e.detail?.state;
    if (st === 'awake') return despertarDonde();
    if (st === 'walk') quitarRincon();
  }
  /* Al despertar, el reproductor devuelve la Candi del dock. Si despertó
     lejos de su casa, se sienta atenta ahí mismo y la del dock se esconde. */
  function despertarDonde() {
    if (rincon) { mascota.pause(); return; }   /* la despertaron antes del primer paso: sigue donde estaba */
    const x = parseFloat(descanso.actor.style.left), size = parseFloat(descanso.actor.style.width);
    if (!Number.isFinite(x) || !Number.isFinite(size) || abierto || bajito.matches) return;
    if (Math.abs(x - descanso.layout().casa) < 32) return;    /* está (o quedó) en su casa */
    mascota.pause(); mascota.sprite.hidden = true;
    const el = document.createElement('div');
    el.className = 'candi-bone-atenta';
    Object.assign(el.style, { left: x + 'px', width: size + 'px', height: size + 'px' });
    tira.append(el);
    rincon = { el, x, m: new CandiAtletica(el) };
    rincon.m.idle().catch(() => {});
  }
  function quitarRincon() { if (!rincon) return; rincon.m.destroy(); rincon.el.remove(); rincon = null; }
  function volverAlDock() {
    if (descanso?.active) descanso.wake();
    if (!rincon) return;
    quitarRincon();
    if (mascota) { mascota.sprite.hidden = false; mascota.idle().catch(() => {}); }
  }
  function mostrarGlobo() {
    presentada = true;
    if (document.getElementById('partidaSaludo') && contexto().vista === 'intro') {
      memoria.presentada = true; recordar();
      globo.hidden = true;
      return; // El saludo de Luna se lee en el panel, sin globo duplicado.
    }
    vigilarTarjetas();
    vistaComentada = contexto().vista;
    if (abierto || globo.dataset.visto === '1') { if (calculando) avisarCalculo(); return; }
    const primera = !memoria.presentada;
    const vista = saludoDeVista(), vistaId = contexto().vista;
    let texto;
    if (primera) {
      const nombre = primerNombre();
      /* Si la meta todavía se está calculando, el saludo lo dice de una vez: dos
         globos seguidos se leerían como Candi hablando sola. */
      texto = `${nombre ? `¡Hola, ${nombre}!` : '¡Hola!'} Soy Candi, tu estratega de campaña. ` +
        (calculando ? avisoActual : (vista ? (saludoDicho = true, vista) : 'Pregúntame lo que quieras de la pantalla en la que estés.'));
      memoria.presentada = true; if (vista && !calculando) marcarDicha(vistaId); recordar();
    } else if (calculando) {
      texto = avisoActual;
    } else if (vista && !yaDicha(vistaId)) {
      texto = vista; saludoDicho = true; marcarDicha(vistaId);
    } else return;                            /* ya lo dijo: sentada y callada */
    globo.querySelector('#candiGloboTexto').textContent = texto;
    globo.dataset.aviso = calculando ? 'calculo' : '';
    globo.hidden = false;
    if (calculando) pensarYa();
    clearTimeout(mostrarGlobo._t);
    mostrarGlobo._t = setTimeout(ocultarGlobo, saludoDicho ? 22000 : 12000);   /* se presenta y se quita sola */
  }
  /* Algunas páginas traen un saludo propio que explica una decisión de fondo
     (el electorado: por qué se describe a quien puede votar). Si la página
     arranca calculando, el saludo va DESPUÉS del aviso de cálculo, no se pierde. */
  let saludoDicho = false;
  function saludoDeVista() { return VISTAS[contexto().vista]?.saludo || ''; }
  function decirSaludoDeVista() {
    if (saludoDicho || abierto || !saludoDeVista() || yaDicha(contexto().vista)) return false;
    saludoDicho = true; marcarDicha(contexto().vista);
    globo.querySelector('#candiGloboTexto').textContent = saludoDeVista();
    globo.dataset.aviso = ''; globo.dataset.visto = ''; globo.hidden = false;
    clearTimeout(mostrarGlobo._t);
    mostrarGlobo._t = setTimeout(ocultarGlobo, 22000);
    return true;
  }
  function ocultarGlobo() { ultimoComentario = Date.now(); globo.dataset.visto = '1'; globo.dataset.aviso = ''; globo.hidden = true; clearTimeout(mostrarGlobo._t); }

  /* ─── Mientras se calcula la meta de votos ───────────────────────────────
     La meta tarda (baja índices y reparte curules) y la tarjeta se queda en
     «…». Candi piensa y avisa que se puede seguir explorando, para que la
     espera no se lea como página colgada. Durante la entrada NO interrumpe:
     el aviso va dentro del saludo. Con el panel abierto va como mensaje. El
     clip de pensar es de 6 s y no se repite en bucle (sacaría y guardaría las
     gafas en cada vuelta); el aviso sí se queda hasta que la meta aterriza. */
  const AVISO_CALCULO = '¡Estamos calculando el número de votos! Ve explorando el resto de la página.';
  let calculando = false, presentada = false, avisoActual = AVISO_CALCULO;
  function avisarCalculo() {
    if (abierto) { burbuja('ella', `<p>${esc(avisoActual)}</p>`); pensarYa(); return; }
    globo.querySelector('#candiGloboTexto').textContent = avisoActual;
    globo.dataset.aviso = 'calculo';
    globo.hidden = false;
    clearTimeout(mostrarGlobo._t);
    pensarYa();
  }
  /* `texto` deja que cada página diga qué está calculando (el panel 09 arma
     el plan de testigos, no la meta). */
  function calculo(activo, texto) {
    activo = !!activo;
    if (activo) avisoActual = texto || AVISO_CALCULO;
    if (activo === calculando) return;
    calculando = activo;
    habilitarDescanso();                     /* calculando no se va por el hueso; al terminar, espera completa */
    if (activo) { if (presentada) avisarCalculo(); return; }   /* si aún entra, lo dice el saludo */
    if (globo && presentada && decirSaludoDeVista()) return;
    if (globo && globo.dataset.aviso === 'calculo') {
      globo.dataset.aviso = '';
      clearTimeout(mostrarGlobo._t);
      mostrarGlobo._t = setTimeout(ocultarGlobo, 1200);       /* lo alcanza a leer y se va */
    }
  }

  /* ─── Que una página diga algo puntual ───────────────────────────────────
     Para avisos que dan tranquilidad en el momento en que importan (el
     endoso: dónde queda el nombre de un líder que se acaba de sumar). Con el
     panel abierto va como mensaje; con un cálculo en curso no interrumpe: el
     aviso del cálculo manda y la página lo puede volver a pedir al terminar. */
  function decir(texto, ms = 16000) {
    if (!globo || !texto) return false;
    if (abierto) { burbuja('ella', `<p>${esc(texto)}</p>`); return true; }
    if (calculando) return false;
    globo.querySelector('#candiGloboTexto').textContent = texto;
    globo.dataset.aviso = ''; globo.dataset.visto = ''; globo.hidden = false;
    clearTimeout(mostrarGlobo._t);
    mostrarGlobo._t = setTimeout(ocultarGlobo, ms);
    return true;
  }

  /* La portada reserva un lugar en el flujo: la mascota y su saludo nunca
     cubren las opciones. Al abrir el chat vuelve al dock flotante habitual. */
  function ubicarEnPortada() {
    const sitio = document.getElementById('candiBienvenida');
    if (!sitio || !dock) return;
    const enIntro = contexto().vista === 'intro';
    const stage = document.getElementById('intro').dataset.stage;
    const visible = !enIntro || stage === 'greeting' || stage === 'options';
    const destino = enIntro && !abierto ? sitio : document.body;
    if (dock.parentElement !== destino) {
      volverAlDock();
      destino.append(dock);
    }
    dock.hidden = !visible;
    if (!visible) { ocultarGlobo(); mascota?.pause(); }
    habilitarDescanso();
  }
  function sincronizarEtapaIntro() {
    if (!dock) return;
    ubicarEnPortada();
    if (dock.hidden) return;
    const stage = document.getElementById('intro')?.dataset.stage;
    if (!entroYa) entrar();
    else if (stage === 'greeting') mascota?.play().catch(e => fallarAtlas(e?.message));
    else mascota?.idle().catch(() => {});
  }
  document.addEventListener('c360:intro-stage', sincronizarEtapaIntro);

  /* ─── Abrir, cerrar, desmontar ───────────────────────────────────────── */
  function abrir() {
    abierto = true; ocultarGlobo();
    ubicarEnPortada();
    habilitarDescanso(); volverAlDock();
    dock.classList.add('abierto'); panel.hidden = false;
    launcher.setAttribute('aria-expanded', 'true');
    pintarGuia();
    pintarPie();
    setTimeout(() => input.focus({ preventScroll: true }), 60);
  }
  function cerrar({ foco = false } = {}) {
    abierto = false;
    dock.classList.remove('abierto'); panel.hidden = true;
    launcher.setAttribute('aria-expanded', 'false');
    ubicarEnPortada();
    if (foco) launcher.focus();
    habilitarDescanso();
    /* Ojo: NO se llama pause() acá. Candi vive en la pantalla aunque el panel
       esté cerrado, y el reproductor ya deja de avanzar cuando la pestaña se
       oculta. Pausar acá congelaba la entrada a mitad de camino. */
  }
  function destruir() {
    clearInterval(relojGenerales); obsTarjetas?.disconnect();
    descanso?.destroy(); descanso = null; quitarRincon(); tira?.remove(); tira = null;
    escena?.removeEventListener('candi:state', reenviarEstado);
    bajito.removeEventListener('change', alCambiarAlto); removeEventListener('resize', alRedimensionar);
    mascota?.destroy(); mascota = null;
  }

  /* La mascota es decorativa: si su imagen falla, el panel sigue completo. */
  function fallarAtlas(msg) {
    escena.hidden = true; dock.classList.add('sin-atlas');
    console.warn('[Candi]', msg || 'atlas no disponible');
  }

  /* ─── Las preguntas escritas ─────────────────────────────────────────── */
  function burbuja(clase, html) {
    const d = document.createElement('div');
    d.className = 'candi-msg ' + clase; d.innerHTML = html;
    log.append(d); d.scrollIntoView({ block: 'nearest' });
    return d;
  }
  const parrafos = t => String(t).split(/\n{2,}/).map(p => `<p>${esc(p.trim()).replace(/\n/g, '<br>')}</p>`).join('');

  async function preguntar(texto) {
    const q = String(texto || '').trim();
    if (!q || enVuelo) return;
    const token = ses()?.token || null;
    input.value = '';
    burbuja('yo', parrafos(q));
    /* Sin sesión no hay a quién cobrarle la pregunta: se dice acá y no se
       gasta un viaje al worker para que él responda lo mismo con un 401. */
    if (!token) return sinRespuesta(SIN_SESION, `<a href="${volverAca()}">Iniciar sesión</a>`);
    enVuelo = true; enviar.disabled = true;
    habilitarDescanso();                     /* con una pregunta en vuelo no se va por el hueso */
    investigar();                            /* esto SÍ es una consulta de verdad: la lupa */
    const esperando = burbuja('ella', '<span class="candi-puntos" role="status" aria-label="Candi está pensando"><i></i><i></i><i></i></span>');
    try {
      const r = await fetch(`${API}/c360/candi`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ pregunta: q, contexto: { ...contexto(), seleccion: seleccion() }, historial: historial.slice(-6) })
      });
      let data = null; try { data = await r.json(); } catch {}
      esperando.remove();
      if (r.status === 401) return sinRespuesta(SIN_SESION, `<a href="${volverAca()}">Iniciar sesión</a>`);
      if (r.status === 404) return sinRespuesta('Todavía no puedo responder preguntas escritas: falta desplegar mi conexión. La guía de cada pantalla sí funciona.');
      if (r.status === 429) return sinRespuesta(data?.error || 'Por hoy se acabaron las preguntas de esta cuenta. La guía de cada pantalla sigue disponible.');
      if (!r.ok || !data || data.ok === false || !data.respuesta) return sinRespuesta(data?.error || `No pude responder (HTTP ${r.status}). La guía de cada pantalla sigue disponible.`);
      burbuja('ella', parrafos(data.respuesta));
      historial.push({ rol: 'usuario', texto: q }, { rol: 'candi', texto: data.respuesta });
      aplicarEstado(data.estado);
    } catch (e) {
      esperando.remove();
      sinRespuesta('No pude conectarme para responder eso. La guía de cada pantalla sigue disponible aquí arriba.');
    } finally { enVuelo = false; enviar.disabled = false; habilitarDescanso(); input.focus({ preventScroll: true }); }
  }
  /* Nunca se rellena el hueco con una respuesta inventada: se dice qué falta. */
  function sinRespuesta(motivo, extra) { burbuja('falla', `<p>${esc(motivo)}</p>${extra ? `<p>${extra}</p>` : ''}`); }

  /* El modelo puede pedir un estado de animación; se valida contra ESTADOS y
     se ignora lo que no exista o lo que rompa la regla de entrar una sola vez. */
  function aplicarEstado(estado) {
    if (!estado) return;
    const e = ESTADOS[estado];
    if (!e) return console.warn('[Candi] estado no permitido:', estado);
    if (e.soloAlEntrar) return;                         /* pendiente: sit_down / idle_seated */
  }

  /* ─── Arranque ───────────────────────────────────────────────────────────
     Candi entra cuando la pantalla de carga ya se fue: con el preload puesto
     no hay nada que guiar, y su saludo se perdería detrás. */
  function arrancar() {
    montar();
    ubicarEnPortada();
    const preload = document.getElementById('preload');
    const mostrar = () => {
      if (document.getElementById('partidaSaludo')) sincronizarEtapaIntro();
      else { dock.hidden = false; entrar(); }
    };
    if (!preload || !preload.classList.contains('active')) return mostrar();
    const obs = new MutationObserver(() => { if (!preload.classList.contains('active')) { obs.disconnect(); mostrar(); } });
    obs.observe(preload, { attributes: true, attributeFilter: ['class'] });
    setTimeout(() => { obs.disconnect(); mostrar(); }, 8000);   /* red de seguridad */
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', arrancar, { once: true });
  else arrancar();

  /* Para depurar desde la consola; no es API pública. */
  /* ─── Pensando: al abrir un módulo que calcula ───────────────────────────
     Saca las gafas, mira arriba, se le prende el bombillo y vuelve a quedar
     atenta (6 s, v3). Solo con los módulos que abren su cálculo EN la página
     —arquetipos, firmas, endoso y el «por qué» de la meta—: los que llevan a
     otra página la cortarían a la mitad. Nunca durante la entrada, y como
     mucho una vez cada 20 s: una mascota que piensa a cada clic deja de decir
     algo. `curious` sigue sin conectar: no está decidido cuándo va. */
  const PIENSA_EN = '#crmArqBtn, #crmFirmasBtn, #crmEndosoBtn, .meta-i';
  let ultimaVez = 0;
  function pensar() {
    const ahora = Date.now(); if (ahora - ultimaVez < 20000) return;
    pensarYa();
  }
  /* Sin el tope de 20 s: lo usa el aviso de cálculo, que es un hecho y no un clic. */
  function pensarYa() {
    if (!mascota || typeof mascota.thinking !== 'function') return;
    volverAlDock();                               /* para reaccionar vuelve a su sitio */
    const estado = escena.dataset.estado;
    if (estado === 'thinking') return;                             /* ya está en eso */
    if (estado !== 'idle_seated') {             /* no interrumpe la entrada ni la lupa */
      if (!pensarYa._espera) { pensarYa._espera = true; cuandoAtenta(() => { pensarYa._espera = false; if (calculando) pensarYa(); }); }
      return;
    }
    ultimaVez = Date.now();
    mascota.thinking().catch(e => console.warn('[Candi] pensando:', e && e.message));
  }

  /* ─── Investigando: la lupa, para una consulta REAL de datos ─────────────
     (v3 atlética, 29-sep: 24 poses, 4,8 s). Se dispara al mandar una pregunta
     escrita al worker, que es la única consulta que Candi hace de verdad; la
     espera habitual de los cálculos de la página sigue siendo `pensarYa`.
     · Nunca las dos a la vez: si está pensando (o entrando), la lupa espera a
       que vuelva a quedar atenta, y solo sale si la pregunta sigue en vuelo.
     · Una lupa por pregunta, sin bucle: si el worker tarda más de 4,8 s,
       vuelve a atenta y ahí se queda (repetirla sacaría y guardaría la lupa
       en cada vuelta, como con las gafas).
     · Si la respuesta llega ANTES de que termine, se la deja terminar: son
       4,8 s y cortar la lupa a mitad de examen se lee como un salto del
       dibujo. La respuesta ya está en el panel; la mascota es decorativa. Si
       algún día hiciera falta cortarla, `mascota.idle()` la cancela. */
  function investigar() {
    if (!mascota || typeof mascota.investigating !== 'function') return;
    volverAlDock();                               /* para reaccionar vuelve a su sitio */
    const estado = escena.dataset.estado;
    if (estado === 'investigating') return;                        /* ya está en eso */
    if (estado !== 'idle_seated') {
      if (!investigar._espera) { investigar._espera = true; cuandoAtenta(() => { investigar._espera = false; if (enVuelo) investigar(); }); }
      return;
    }
    mascota.investigating().catch(e => console.warn('[Candi] investigando:', e && e.message));
  }

  /* Una sola vez, cuando vuelva a quedar sentada y atenta. ⚠️ No basta con
     `candi:complete`: ese evento solo sale al terminar la ENTRADA (o de una,
     con movimiento reducido). Tras una reacción la vuelta a atenta es
     `idle()` desde 4,8 s, que no lo emite, y quien esperara solo ese evento
     se quedaba colgado para siempre — y con él todo pensar posterior. */
  function cuandoAtenta(fn) {
    const hecho = () => { escena.removeEventListener('candi:state', alEstado); escena.removeEventListener('candi:complete', hecho); fn(); };
    const alEstado = e => { if (e.detail?.state === 'idle_seated') hecho(); };
    escena.addEventListener('candi:state', alEstado);
    escena.addEventListener('candi:complete', hecho);
  }
  document.addEventListener('click', e => { if (e.target.closest?.(PIENSA_EN)) pensar(); });

  window.Candi = { abrir, cerrar, entrar, pensar, investigar, calculo, decir, perfil, temas: () => temasDe(), get mascota() { return mascota; }, get descanso() { return descanso; }, contexto, primerNombre };
})();
