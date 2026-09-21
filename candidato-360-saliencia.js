/* ═══════════════════════════════════════════════════════════════════════════
   CANDIDATO 360 · saliencia mediática de la escucha
   ───────────────────────────────────────────────────────────────────────────
   La capa de análisis del panel 04, hermana de la saliencia de Proyecto DC
   (proyecto-dc/agenda.html: nube · quién cubre · a quién nombran · de qué se
   habla · qué hacer según el arquetipo). Allá corre un pipeline de Lambdas
   sobre 10 medios de Medellín; acá se calcula en el navegador sobre los
   titulares que el panel YA trajo de Google News, porque cada candidatura
   tiene su propio territorio y no hay un agregado que precalcular.

   Todo es determinista (diccionarios y conteos), sin modelo: cada cifra se
   puede rastrear hasta sus titulares, y el panel deja filtrarlos.

   Lo que mide y lo que no:
   · Mide lo que se PUBLICA. Un tema mudo en los medios puede estar vivo en la
     calle.
   · El tema sale del vocabulario del titular: un titular puede tener varios
     temas o ninguno, y el porcentaje «sin tema» se muestra, no se esconde.
   · El encuadre (conflicto o gestión) también es vocabulario, no lectura de
     intención.
   · Los actores se detectan por nombres propios en mayúscula: es una
     aproximación y se rotula así.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';

  const norm = s => ' ' + String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^A-Za-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim().toUpperCase() + ' ';
  const sinTilde = s => String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '');

  /* ── Temas de agenda ────────────────────────────────────────────────────
     Raíces que deben EMPEZAR palabra (\b al inicio): sin eso «paro» casa
     dentro de «amparo» y «obra» dentro de «sobra» — la misma trampa del
     diccionario de empresas de Caudal. Las ocho primeras llaves son las que
     pesan en los arquetipos (candidato-360-arquetipos.js). */
  const TEMAS = [
    { id: 'seguridad', nombre: 'Seguridad', raices: ['HOMICID', 'ASESIN', 'HURTO', 'ROBO', 'ROBOS', 'ROBAR', 'ATRACO', 'EXTORSI', 'SICARI', 'BANDA', 'POLICIA', 'POLICIAL', 'EJERCITO', 'CAPTUR', 'MASACRE', 'ATENTADO', 'DISIDENCIA', 'ELN', 'CLAN DEL GOLFO', 'INSEGURIDAD', 'SEGURIDAD', 'VIOLENCIA', 'CRIMEN', 'CRIMINAL', 'DELINCU', 'ARMA', 'ARMAS', 'BALACERA', 'SECUESTR', 'FEMINICID', 'MICROTRAFIC', 'CAMARAS DE SEGURIDAD', 'CUADRANTE', 'MILITARIZ'] },
    { id: 'corrupcion', nombre: 'Corrupción y control', raices: ['CORRUP', 'SOBORNO', 'PECULADO', 'IRREGULAR', 'SOBRECOSTO', 'DETRIMENTO', 'PROCURADURIA', 'CONTRALORIA', 'PERSONERIA', 'FISCALIA', 'INVESTIGAC', 'DENUNCI', 'ESCANDALO', 'CONTRATO', 'CONTRATACI', 'LICITACI', 'CARTEL', 'DESTITU', 'SUSPENDID', 'IMPUTA', 'VEEDURIA'] },
    { id: 'empleo', nombre: 'Empleo, economía y bolsillo', raices: ['EMPLEO', 'DESEMPLEO', 'TRABAJO', 'TRABAJADOR', 'SALARIO', 'INFLACION', 'COSTO DE VIDA', 'PRECIO', 'IMPUESTO', 'PREDIAL', 'TRIBUT', 'EMPRES', 'EMPRENDI', 'COMERCIO', 'COMERCIANTE', 'VENDEDOR', 'INFORMAL', 'TURISMO', 'ECONOM', 'SUBSIDIO', 'RENTA', 'POBREZA', 'HAMBRE', 'MERCADO', 'CAMPESIN', 'AGRO', 'COSECHA', 'BANCO', 'BANCOS', 'FINTECH', 'ICA'] },
    { id: 'servicios', nombre: 'Servicios públicos', raices: ['AGUA', 'AGUAS', 'ACUEDUCTO', 'ALCANTARILL', 'RACIONAMIENTO', 'ENERGIA', 'ELECTRIC', 'APAGON', 'CORTE DE LUZ', 'TARIFA', 'SERVICIOS PUBLICOS', 'GAS', 'BASURA', 'RESIDUOS', 'ASEO', 'RELLENO SANITARIO', 'RECICLA', 'INTERNET', 'CONECTIVIDAD', 'ALUMBRADO'] },
    { id: 'movilidad', nombre: 'Movilidad', raices: ['MOVILIDAD', 'TRANSMILENIO', 'METRO', 'METROPLUS', 'MIO', 'SITP', 'BUS', 'BUSES', 'TRANSPORTE', 'TRANCON', 'TRAFICO', 'VIA', 'VIAS', 'VIAL', 'CARRETERA', 'AUTOPISTA', 'PICO Y PLACA', 'TAXI', 'TAXIS', 'MOTO', 'MOTOS', 'MOTOCICL', 'ACCIDENTE', 'SINIESTRO', 'CICLORRUTA', 'BICICLET', 'PEATON', 'HUECO', 'PUENTE', 'TUNEL', 'AEROPUERTO', 'CICLISTA', 'FOTOMULTA', 'COMPARENDO', 'INFRACCI'] },
    { id: 'salud_educacion', nombre: 'Salud y educación', raices: ['SALUD', 'HOSPITAL', 'CLINICA', 'EPS', 'IPS', 'MEDIC', 'PACIENTE', 'URGENCIA', 'VACUN', 'DENGUE', 'BROTE', 'EPIDEMI', 'SALUD MENTAL', 'COLEGIO', 'ESCUELA', 'ESTUDIANT', 'DOCENTE', 'PROFESOR', 'MAESTRO', 'EDUCACI', 'UNIVERSIDAD', 'MATRICUL', 'BECA', 'BECAS', 'ICFES', 'PAE', 'ALIMENTACION ESCOLAR', 'JARDIN INFANTIL'] },
    { id: 'participacion', nombre: 'Participación y comunidad', raices: ['JAL', 'EDIL', 'EDILES', 'JUNTA DE ACCION', 'JUNTAS DE ACCION', 'ACCION COMUNAL', 'COMUNAL', 'PRESUPUESTO PARTICIPATIVO', 'PARTICIPACI', 'CABILDO', 'CONSULTA', 'ASAMBLEA COMUNITARIA', 'LIDER SOCIAL', 'LIDERES SOCIALES', 'LIDERESA', 'RECOLECCION DE FIRMAS', 'FIRMAS', 'VECINOS', 'COMUNIDAD', 'COMUNIDADES', 'CIUDADANOS', 'VEEDOR'] },
    { id: 'cultura', nombre: 'Cultura, deporte e identidad', raices: ['CULTURA', 'CULTURAL', 'FESTIVAL', 'FERIA', 'CARNAVAL', 'CONCIERTO', 'MUSICA', 'ARTE', 'ARTISTA', 'TEATRO', 'MUSEO', 'BIBLIOTECA', 'PATRIMONIO', 'DEPORTE', 'DEPORTIV', 'ESTADIO', 'FUTBOL', 'INDIGENA', 'AFRO', 'AFRODESCENDIENT', 'CAMPESINA', 'TRADICION', 'IDENTIDAD', 'JUVENTUD', 'JOVENES'] },
    { id: 'politica', nombre: 'Política y elecciones', raices: ['ELECCION', 'ELECTORAL', 'CANDIDAT', 'CAMPANA', 'PARTIDO', 'COALICION', 'VOTO', 'VOTOS', 'VOTACION', 'REGISTRADURIA', 'CNE', 'CONGRESO', 'SENADO', 'OPOSICION', 'PETRO', 'GOBIERNO NACIONAL', 'MINISTR', 'ENCUESTA', 'SONAJERO', 'SUENAN', 'ASPIRA', 'PRECANDIDAT', 'AVAL'] },
    /* ⚠️ Sin «Concejo», «Asamblea» ni «Alcaldía»: son las anclas de la búsqueda
       del territorio, así que salen en casi todo titular y la política se
       llevaba dos de cada tres. Medido en Bogotá: 47 de 71. */
    { id: 'ambiente', nombre: 'Ambiente y riesgo', raices: ['AMBIENT', 'LLUVIA', 'INVIERNO', 'INUNDACI', 'DESLIZAMIENTO', 'EMERGENCIA', 'DAMNIFIC', 'INCENDIO', 'SEQUIA', 'CALIDAD DEL AIRE', 'CONTAMINACI', 'RIO', 'RIOS', 'QUEBRADA', 'HUMEDAL', 'ARBOL', 'ARBOLES', 'DEFORESTACI', 'MINERIA', 'CLIMA', 'CAMBIO CLIMATICO', 'ANIMAL', 'FAUNA', 'SISMO', 'TERREMOTO', 'GESTION DEL RIESGO'] },
    { id: 'vivienda', nombre: 'Vivienda, obras y POT', corto: 'vivienda, obras y POT', raices: ['VIVIENDA', 'POT', 'ORDENAMIENTO', 'URBANIS', 'OBRA', 'OBRAS', 'CONSTRUCCI', 'INFRAESTRUCTURA', 'PARQUE', 'ESPACIO PUBLICO', 'RENOVACION URBANA', 'BARRIO', 'LEGALIZACI', 'INVASION', 'DESALOJO', 'ARRIENDO', 'PLAN DE DESARROLLO', 'PRESUPUESTO'] },
  ];
  /* Las raíces de 4 letras o menos van como palabra ENTERA: «VIA» casaría con
     «viaje», «ARMA» con «Armando» y «ARTE» con «Arteaga». */
  const TEMA_RE = TEMAS.map(t => ({ id: t.id, re: new RegExp('\\b(?:' + t.raices.map(r => r.replace(/ /g, '\\s') + (r.length <= 4 ? '\\b' : '')).join('|') + ')') }));
  const temasDe = tituloN => TEMA_RE.filter(t => t.re.test(tituloN)).map(t => t.id);

  /* ── Encuadre ───────────────────────────────────────────────────────────
     Vocabulario de conflicto contra vocabulario de gestión. Un titular puede
     no tener ninguno (neutro). */
  const CONFLICTO = /\b(?:DENUNCI|ESCANDALO|CRISIS|POLEMIC|CRITIC|RECHAZ|ALERTA|PROTESTA|PARO|BLOQUEO|CAOS|ABANDONO|RIESGO|MUERT|MUERE|MURIO|ASESIN|ATAQUE|AMENAZ|IRREGULAR|INVESTIGAC|SANCION|DEMANDA|QUEJA|RECLAM|FALLA|COLAPSO|RETRASO|INCUMPL|EMERGENCIA|PELEA|ENFRENTA|TENSION|CONTROVERS)/;
  const GESTION = /\b(?:ANUNCIA|INAUGUR|ENTREG|AVANZA|AVANCE|LANZA|INVIERT|INVERSION|BENEFICI|RECUPER|MEJORA|NUEVO|NUEVA|NUEVOS|NUEVAS|PROGRAMA|PLAN\b|APRUEBA|APROBO|ABRE|ABRIO|AMPLIA|GARANTIZ|FIRMA|ACUERDO|INICIA|COMIENZA|SOLUCION|LOGRA|CELEBRA|PREMIO|RECONOC)/;

  /* ── Palabras vacías para la nube ────────────────────────────────────── */
  const VACIAS = new Set(('PARA POR CON LOS LAS DEL QUE UNA UNO UNAS UNOS SUS ESTE ESTA ESTOS ESTAS ESO ESA ESOS ESAS COMO MAS MENOS PERO SOBRE ENTRE DESDE HASTA TRAS ANTE SEGUN SOLO '
    + 'HOY AYER MANANA ASI FUE SER SON HAY VAN TIENE TIENEN TENER HACE HACER HIZO PUEDE PUEDEN DEBE DEBEN SERA SERAN ESTA ESTAN ESTABA HABIA HABRA SIDO SIENDO '
    + 'DICE DIJO DICEN AFIRMA AFIRMO ASEGURA ASEGURO SENALA SENALO REVELA REVELO EXPLICA EXPLICO ANUNCIO CONFIRMA CONFIRMO ADVIERTE ADVIRTIO PIDE PIDIO '
    + 'TODO TODOS TODA TODAS CADA OTRO OTRA OTROS OTRAS MISMO MISMA DONDE CUANDO QUIEN QUIENES CUAL CUALES PORQUE AUNQUE MIENTRAS DURANTE CONTRA SIN MUY '
    + 'TAMBIEN AHORA YA AUN TODAVIA ANOS ANO DIAS DIA MES MESES SEMANA SEMANAS HORAS HORA VECES PRIMER PRIMERA NUEVO NUEVA NUEVOS NUEVAS GRAN GRANDE '
    + 'ENERO FEBRERO MARZO ABRIL MAYO JUNIO JULIO AGOSTO SEPTIEMBRE OCTUBRE NOVIEMBRE DICIEMBRE LUNES MARTES MIERCOLES JUEVES VIERNES SABADO DOMINGO '
    + 'COLOMBIA COLOMBIANO COLOMBIANA COLOMBIANOS PAIS NACIONAL VIDEO FOTOS NOTICIAS NOTICIA ULTIMA MINUTO CASO CASOS PERSONAS PERSONA TRAVES PARTE LUEGO '
    + 'SOBRE BAJO FRENTE DENTRO FUERA CERCA LEJOS ALGUNOS ALGUNAS MUCHOS MUCHAS POCO POCOS HABLA HABLO QUEDA QUEDO LLEGA LLEGO SALE SALIO TRAS VUELVE').split(' '));

  /* ── Actores ─────────────────────────────────────────────────────────────
     Nombres propios: dos o más palabras en mayúscula seguidas (con «de»,
     «del», «la» de conector), más las instituciones que se nombran con una
     sola palabra. Una palabra suelta en mayúscula NO cuenta por sí sola —la
     primera del titular va en mayúscula por ser la primera—: solo si es una
     institución o el apellido de un nombre completo visto en otro titular. */
  const INSTITUCIONES = { ALCALDIA: 'Alcaldía', CONCEJO: 'Concejo', GOBERNACION: 'Gobernación', ASAMBLEA: 'Asamblea', PROCURADURIA: 'Procuraduría', CONTRALORIA: 'Contraloría',
    FISCALIA: 'Fiscalía', PERSONERIA: 'Personería', DEFENSORIA: 'Defensoría del Pueblo', REGISTRADURIA: 'Registraduría', POLICIA: 'Policía', EJERCITO: 'Ejército',
    CNE: 'CNE', JEP: 'JEP', DNP: 'DNP', UNGRD: 'UNGRD', ICBF: 'ICBF', SENA: 'SENA', PETRO: 'Gustavo Petro', CONGRESO: 'Congreso', SENADO: 'Senado' };
  /* Sin «y»: juntaba dos actores distintos («TransMilenio y SITP»). */
  const CONECTORES = new Set(['de', 'del', 'la', 'las', 'los']);
  const NO_ACTOR = /^(EL|LA|LOS|LAS|UN|UNA|ESTE|ESTA|ASI|QUE|QUIEN|COMO|POR|PARA|EN|CON|SIN|TRAS|HOY|YA|ALERTA|ATENCION|VIDEO|ULTIMA|LO|SE|SI|NO|ES)$/;
  const esMayus = w => /^[A-ZÁÉÍÓÚÑÜ]/.test(w) && !/^[A-ZÁÉÍÓÚÑÜ]+$/.test(w.length > 6 ? w : 'x');
  const esSigla = w => /^[A-ZÁÉÍÓÚÑ]{2,6}$/.test(w);
  function candidatosActor(titulo) {
    /* La puntuación corta la secuencia: «Bogotá: Concejo aprueba…» no es un
       actor llamado «Bogotá Concejo». */
    /* Google News pega el medio al final («… | El Colombiano»): no es actor. */
    titulo = String(titulo).replace(/\s+[|–—-]\s+[^|–—-]{2,40}$/, '');
    const palabras = String(titulo).replace(/[«»"“”‘’'()]/g, ' ').replace(/[,.:;¿?¡!|–—]|\s-\s/g, ' · ').split(/\s+/).filter(Boolean);
    const salida = [];
    let actual = [];
    const cerrar = () => {
      while (actual.length && CONECTORES.has(actual[actual.length - 1])) actual.pop();
      /* El artículo o la preposición en mayúscula al inicio no son parte del
         nombre: «La OPS», «De la Espriella» → «OPS», «Espriella». */
      while (actual.length > 1 && /^(EL|LA|LOS|LAS|DE|DEL|UN|UNA)$/.test(sinTilde(actual[0]).toUpperCase())) { actual.shift(); while (actual.length && CONECTORES.has(actual[0])) actual.shift(); }
      const fuertes = actual.filter(w => !CONECTORES.has(w));
      if (fuertes.length >= 2) salida.push(actual.join(' '));
      else if (fuertes.length === 1) salida.push(fuertes[0]); /* suelta solo cuenta si es institución o apellido de un nombre completo (ver analizar) */
      actual = [];
    };
    palabras.forEach((w, i) => {
      if (w === '·') { if (actual.length) cerrar(); return; }
      if (esMayus(w) || esSigla(w)) { if (!actual.length) actual.inicio = i; actual.push(w); }
      else if (actual.length && CONECTORES.has(w)) actual.push(w);
      else if (actual.length) cerrar();
    });
    if (actual.length) cerrar();
    return salida.filter(a => !NO_ACTOR.test(sinTilde(a).toUpperCase()));
  }

  /* ── El análisis ─────────────────────────────────────────────────────────
     items: [{ titulo, medio, url, fecha }] ya deduplicados.
     ctx:   { locales: ['BOGOTA', …], persona: [['NATALIA','PARRA'], …], anclas: ['Alcaldía de Bogotá', …], hoy } */
  function analizar(items, ctx = {}) {
    const locales = (ctx.locales || []).map(x => String(x).toUpperCase());
    const hoy = ctx.hoy ? new Date(ctx.hoy) : new Date();
    const dia = f => { const d = new Date(String(f).slice(0, 10) + 'T12:00:00'); return isNaN(d) ? null : Math.floor((hoy - d) / 864e5); };
    const filas = items.map(it => {
      const n = norm(it.titulo);
      return Object.assign({}, it, { _n: n, _temas: temasDe(n), _dias: dia(it.fecha),
        _enc: CONFLICTO.test(n) ? (GESTION.test(n) ? 'mixto' : 'conflicto') : (GESTION.test(n) ? 'gestion' : 'neutro') });
    });
    const N = filas.length;

    /* Temas: cuántos titulares tocan cada uno. */
    const temas = TEMAS.map(t => {
      const suyos = filas.filter(f => f._temas.includes(t.id));
      const recientes = suyos.filter(f => f._dias != null && f._dias <= 7).length;
      return { id: t.id, nombre: t.nombre, corto: t.corto || t.nombre.toLowerCase(), n: suyos.length, pct: N ? suyos.length / N : 0, recientes };
    }).filter(t => t.n).sort((a, b) => b.n - a.n);
    const sinTema = filas.filter(f => !f._temas.length).length;

    /* Qué sube: participación en la última semana contra las tres anteriores.
       Exige al menos 3 titulares recientes: con menos, «sube» es ruido. */
    const nRec = filas.filter(f => f._dias != null && f._dias <= 7).length, nPrev = filas.filter(f => f._dias != null && f._dias > 7).length;
    const subiendo = nRec >= 5 && nPrev >= 5 ? temas.map(t => {
      const prev = filas.filter(f => f._dias != null && f._dias > 7 && f._temas.includes(t.id)).length;
      return Object.assign({}, t, { delta: t.recientes / nRec - prev / nPrev });
    }).filter(t => t.recientes >= 3 && t.delta >= 0.05).sort((a, b) => b.delta - a.delta).slice(0, 3) : [];

    /* Medios: quién cubre más. */
    const porMedio = new Map();
    for (const f of filas) { const m = (f.medio || 'Sin identificar').trim(); porMedio.set(m, (porMedio.get(m) || 0) + 1); }
    const medios = [...porMedio].map(([medio, n]) => ({ medio, n, pct: N ? n / N : 0 })).sort((a, b) => b.n - a.n);

    /* Actores: primero los nombres completos; después, un apellido suelto
       («Galán anunció…») se le suma al nombre completo que lo contiene, si
       hay uno solo que lo contenga. */
    const conteo = new Map(), claveAct = a => sinTilde(a).toUpperCase().replace(/\s+/g, ' ').trim();
    const porTitulo = filas.map(f => candidatosActor(f.titulo));
    const nombres = new Map();
    porTitulo.flat().forEach(a => { if (a.split(' ').length >= 2) { const k = claveAct(a); if (!nombres.has(k)) nombres.set(k, a); } });
    const apellido = new Map(), cabeza = new Map();
    for (const [k, a] of nombres) {
      const ps = k.split(' '), ult = ps[ps.length - 1];
      if (ult.length >= 4) apellido.set(ult, apellido.has(ult) && apellido.get(ult) !== k ? null : k);
      /* «Concejo» a secas se suma a «Concejo de Bogotá» si es el único concejo nombrado. */
      if (INSTITUCIONES[ps[0]]) cabeza.set(ps[0], cabeza.has(ps[0]) && cabeza.get(ps[0]) !== k ? null : k);
    }
    const anclas = new Set((ctx.anclas || []).map(claveAct));
    /* Y su cabeza suelta: en un corpus buscado con «Concejo de Bogotá», el
       «Concejo» a secas es ese mismo concejo. */
    [...anclas].forEach(k => anclas.add(k.split(' ')[0]));
    porTitulo.forEach((cands, i) => {
      const vistos = new Set();
      for (const a of cands) {
        let k = claveAct(a), mostrar = a;
        if (k.split(' ').length === 1) {
          if (cabeza.get(k)) { k = cabeza.get(k); mostrar = nombres.get(k); }
          else if (INSTITUCIONES[k]) { mostrar = INSTITUCIONES[k]; k = claveAct(mostrar); }
          else if (apellido.get(k)) { k = apellido.get(k); mostrar = nombres.get(k); }
          else continue;
        }
        if (locales.some(l => k === l || k === `${l} D C`) || /^(COLOMBIA|BOGOTA D C)$/.test(k)) continue;
        /* Las anclas de la búsqueda (la Alcaldía y el Concejo del territorio)
           salen en casi todo por construcción: contarlas no dice nada. */
        if (anclas.has(k) || vistos.has(k)) continue;
        vistos.add(k);
        const e = conteo.get(k) || { actor: mostrar, n: 0, idx: [] };
        e.n++; e.idx.push(i); conteo.set(k, e);
      }
    });
    const persona = ctx.persona || [];
    const actores = [...conteo.values()].filter(a => a.n >= 2).map(a => Object.assign(a, {
      pct: N ? a.n / N : 0,
      usted: persona.some(tk => tk.filter(x => norm(a.actor).includes(` ${x} `)).length >= 2),
    })).sort((a, b) => b.n - a.n).slice(0, 12);

    /* Nube: raíz de 6 letras para juntar conjugaciones, se muestra la forma
       más frecuente. Sin palabras vacías ni el nombre del territorio. */
    /* Los nombres ya salen en «a quién nombran»: en la nube serían repetición. */
    const deActores = new Set(actores.concat((ctx.anclas || []).map(x => ({ actor: x }))).flatMap(a => sinTilde(a.actor).toUpperCase().split(/\s+/)));
    const raiz = new Map();
    filas.forEach(f => {
      const vistas = new Set();
      String(f.titulo).split(/[^A-Za-zÁÉÍÓÚÑÜáéíóúñü]+/).forEach(w => {
        const W = sinTilde(w).toUpperCase();
        if (W.length < 5 || VACIAS.has(W) || locales.includes(W) || deActores.has(W)) return;
        const r = W.slice(0, 6);
        if (vistas.has(r)) return;
        vistas.add(r);
        const e = raiz.get(r) || { n: 0, formas: new Map() };
        e.n++; const forma = w.toLowerCase(); e.formas.set(forma, (e.formas.get(forma) || 0) + 1);
        raiz.set(r, e);
      });
    });
    const nube = [...raiz].filter(([, e]) => e.n >= 2).map(([r, e]) => ({ w: [...e.formas].sort((a, b) => b[1] - a[1])[0][0], n: e.n, r }))
      .sort((a, b) => b.n - a.n).slice(0, 36);

    /* Ritmo: titulares por día en la ventana. */
    const ventana = ctx.ventana || 30, serie = Array(ventana).fill(0);
    filas.forEach(f => { if (f._dias != null && f._dias >= 0 && f._dias < ventana) serie[ventana - 1 - f._dias]++; });

    const enc = { conflicto: 0, gestion: 0, mixto: 0, neutro: 0 };
    filas.forEach(f => enc[f._enc]++);

    return { N, filas, temas, sinTema, subiendo, medios, actores, nube, serie, encuadre: enc, nRec, nPrev };
  }

  /* ── Sintonía con los arquetipos ─────────────────────────────────────────
     Cuánto le habla la agenda publicada a cada familia: promedio de su
     sensibilidad (1-5) sobre los temas que tienen peso, ponderado por cuánto
     se publica cada tema. Y dos lecturas por familia: el tema de la agenda
     que más la activa, y el tema que más la mueve pero la agenda calla (la
     oportunidad de entrar). */
  function sintonia(analisis, familias) {
    const conPeso = analisis.temas.filter(t => familias.some(f => f.sens[t.id] != null));
    const total = conPeso.reduce((s, t) => s + t.n, 0);
    return familias.map(f => {
      let suma = 0;
      conPeso.forEach(t => { suma += (f.sens[t.id] || 0) * t.n; });
      const indice = total ? suma / total : 0; /* 1-5 */
      const activa = conPeso.slice().sort((a, b) => (f.sens[b.id] || 0) * b.n - (f.sens[a.id] || 0) * a.n)[0] || null;
      const pct = id => (analisis.temas.find(t => t.id === id)?.pct || 0);
      const hueco = Object.entries(f.sens).filter(([id, w]) => w >= 5 && pct(id) < 0.06).map(([id]) => (t => t && (t.corto || t.nombre.toLowerCase()))(TEMAS.find(t => t.id === id))).filter(Boolean);
      return { familia: f, indice, activa, hueco };
    }).sort((a, b) => b.indice - a.indice);
  }

  global.C360Saliencia = { TEMAS, analizar, sintonia, temasDe, norm };
})(window);
