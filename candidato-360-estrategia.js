/* ═══ Candidato 360 · el motor de ESTRATEGIA (tarjeta 11) ════════════════════
   Plan en tools/candidato-360/estrategia/PLAN.md. Responde, con lo que el CRM
   ya tiene cargado y sin modelo de lenguaje:

     1. en qué FASE del calendario está la campaña;
     2. qué PRINCIPIOS del banco pesan más para esta candidatura: Σ sobre los
        arquetipos de (peso del arquetipo en su votación × afinidad acotada) ×
        la celda de la matriz arquetipo × principio;
     3. la TABLA DE TERRITORIO: cada arquetipo en un cuadrante según su peso en
        el territorio y la afinidad de esta votación con él;
     4. si es FIGURA de ciudad o trabajo de BARRIO, según el arraigo medido;
     5. la COMPETENCIA dentro de su lista (lo que ya calculó el panel 10).

   La tarjeta 11 y la vista ampliada de candidato-360.html llaman lo mismo, así
   que no pueden dar cifras distintas. La afinidad NO se calcula aquí: sale de
   C360ArqLectura.afinidad, la misma del panel 05.

   El banco (candidato-360-data/estrategia-banco.json) sale de
   tools/candidato-360/estrategia/build_banco.py. ⚠️ La modulación por
   arquetipo y la matriz son hipótesis del equipo: la página lo dice.
   ⚠️ El voto es secreto: todo se describe por el censo y el comportamiento de
   los barrios donde están sus votos, nunca por quién votó.

   No toca el DOM. En Node se usa pasándole `banco` y las lecturas a `evaluar`. */
(function (global) {
  const BANCO_URL = 'candidato-360-data/estrategia-banco.json?v=20261020-ctg';
  const ARRAIGO_URL = 'candidato-360-data/arraigo-concejo-bogota-2023.json?v=20261019';
  /* Corporaciones que se leen con arquetipos de ciudad. Una asamblea o una
     gobernación se juegan en todo el departamento y los arquetipos son de una
     ciudad: ahí la estrategia dice «todavía no». */
  const CORP_CIUDAD = ['concejo', 'jal', 'alcaldia'];
  const AFIN_ALTA = 1.05;          /* el mismo umbral del panel 05 para «se despega» */
  const AFIN_TOPE = [0.5, 2];      /* afinidad acotada: un arquetipo marginal no manda por un cociente grande */
  const PART_BAJA = 0.04;          /* 4 pp por debajo de la participación del territorio = «vota poco» */
  const BARRIO_MIN = 0.0006;       /* barrios con al menos este peso del territorio (≈1.500 votantes en Bogotá) */
  const ARRAIGO_FIGURA = 0.75, ARRAIGO_BARRIO = 1.25;   /* arraigo / referencia de la ciudad */

  const cache = new Map();
  const json = url => {
    if (!cache.has(url)) cache.set(url, fetch(url).then(r => r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status))).catch(e => { cache.delete(url); throw e; }));
    return cache.get(url);
  };
  const cargarBanco = () => json(BANCO_URL);
  const cargarArraigo = () => json(ARRAIGO_URL).catch(() => null);

  const norm = s => String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^A-Za-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim().toUpperCase();
  const r3 = x => Math.round(x * 1000) / 1000;
  const acotar = x => Math.min(AFIN_TOPE[1], Math.max(AFIN_TOPE[0], x));

  /* ── 1. Fase ─────────────────────────────────────────────────────────────
     La fecha se lee en hora de Bogotá: a las 8 p. m. del último día de una
     fase, en UTC ya es el día siguiente. */
  function hoyISO(fecha) {
    if (typeof fecha === 'string' && /^\d{4}-\d\d-\d\d$/.test(fecha)) return fecha;
    /* `getTime` y no `instanceof Date`: una fecha de otro contexto (la prueba
       en Node, un iframe) no es instancia de este Date. */
    const d = fecha && typeof fecha.getTime === 'function' ? fecha : new Date();
    return new Date(d.getTime() - 5 * 3600e3).toISOString().slice(0, 10);
  }
  const dias = (a, b) => Math.round((Date.parse(b) - Date.parse(a)) / 86400e3);
  function fase(banco, fecha) {
    const C = banco.calendario, hoy = hoyISO(fecha);
    const f = C.fases.find(x => (!x.desde || x.desde <= hoy) && (!x.hasta || hoy <= x.hasta)) || C.fases[0];
    const i = C.fases.indexOf(f);
    const proximo = C.hitos.find(h => h.fecha > hoy) || null;
    return {
      id: f.id, nombre: f.nombre, que: f.que, fichas: f.fichas || [], corte: f.corte, desde: f.desde || null, hasta: f.hasta || null, hoy,
      quedan: f.hasta ? dias(hoy, f.hasta) : null,
      siguiente: C.fases[i + 1] ? { id: C.fases[i + 1].id, nombre: C.fases[i + 1].nombre, desde: C.fases[i + 1].desde } : null,
      proximo: proximo ? { ...proximo, dias: dias(hoy, proximo.fecha) } : null,
      eleccion: { fecha: C.eleccion, dias: dias(hoy, C.eleccion) },
      hitos: C.hitos.map(h => ({ ...h, pasado: h.fecha <= hoy })), nota: C.nota,
    };
  }

  /* ── 2. Qué arquetipos de la matriz corresponden a esta lectura ──────────
     La matriz tiene una fila por código (CMN, PRO…). Cada código dice de qué
     ciudad, de qué corte y con qué id lo trae C360ArqLectura. */
  function codigos(banco, ciudad, corte) {
    const out = {};
    Object.entries(banco.arquetipos || {}).forEach(([cod, a]) => { if (a.ciudad === ciudad && String(a.corte) === String(corte)) out[a.id] = cod; });
    return out;
  }
  /* El corte que se lee: en Bogotá, la tipología de la corporación de la
     campaña (va primero en L.cortes); en Medellín, 2023, que es lo observado. */
  const corteDe = L => L?.cortes?.[0] || '2023';

  /* Los arquetipos de la lectura, con la afinidad del panel 05 (sin el piso
     del 8 %: la tabla de territorio necesita también los chicos). */
  function arquetiposDe({ banco, ciudad, L, LT, lente }) {
    const A = global.C360ArqLectura, corte = corteDe(LT || L), cod = codigos(banco, ciudad, corte);
    const medida = lente !== 'ciudad';
    const filas = A.afinidad(L, LT, corte, { minimo: 0 });
    const D = LT?.D;   /* Bogotá trae la participación del arquetipo y de la ciudad */
    return filas.filter(x => cod[x.id]).map(x => {
      const f = L.ficha?.(x.id) || {};
      return {
        codigo: cod[x.id], id: x.id, nombre: L.nombreDe ? L.nombreDe(x.id, corte) : x.id, color: L.colorDe ? L.colorDe(x.id) : '#6b7280',
        share: x.share, territorio: x.ciudad, ratio: medida ? x.ratio : null,
        participacion: f.perfil?.p ?? null, participacionRef: D?.ciudad?.p ?? null,
      };
    });
  }

  /* ── 3. El peso de cada principio ────────────────────────────────────────
     peso del arquetipo = su parte en esta votación × afinidad acotada,
     normalizado para que sume 1. El puntaje de un principio va de −1 (todos
     los arquetipos en riesgo) a 2 (todos en central). Sin votos propios ni de
     su partido (lente «ciudad») la afinidad es 1: pesa solo el tamaño. */
  function pesos(arqs) {
    const w = arqs.map(a => a.share * (a.ratio == null ? 1 : acotar(a.ratio)));
    const s = w.reduce((x, y) => x + y, 0) || 1;
    return Object.fromEntries(arqs.map((a, i) => [a.codigo, w[i] / s]));
  }
  function principios(banco, arqs) {
    const W = pesos(arqs), M = banco.matriz, N = banco.notas_matriz || {};
    const fichaDe = id => banco.fichas.find(f => f.id === id);
    const top = Object.entries(W).sort((a, b) => b[1] - a[1]).map(([c]) => c);
    const lista = banco.principios.map(p => {
      const aportes = Object.entries(W).map(([c, w]) => ({ codigo: c, peso: w, celda: M[c]?.[p.id] ?? 0, nota: N[c]?.[p.id] || '' }))
        .filter(x => x.celda !== 0).sort((a, b) => Math.abs(b.peso * b.celda) - Math.abs(a.peso * a.celda));
      const puntaje = r3(Object.entries(W).reduce((s, [c, w]) => s + w * (M[c]?.[p.id] ?? 0), 0));
      /* Las ramas del principio que sirven a alguno de sus arquetipos con peso. */
      const ramas = (banco.ramas || []).filter(r => p.ramas.includes(r.id) && r.arquetipos.some(c => (W[c] || 0) >= .1));
      const fichas = [...p.fichas, ...ramas.flatMap(r => r.fichas)].filter((x, i, a) => a.indexOf(x) === i);
      /* Lo que cada ficha dice para los dos arquetipos que más pesan. */
      const modulacion = fichas.map(fichaDe).filter(Boolean).flatMap(f => top.slice(0, 2).filter(c => f.modula?.[c]).map(c => ({ ficha: f.id, codigo: c, texto: f.modula[c] })));
      return { id: p.id, corto: p.corto, texto: p.texto, puntaje, aportes, fichas, ramas: ramas.map(r => r.id), modulacion };
    });
    return lista.sort((a, b) => (b.puntaje - a.puntaje) || a.id.localeCompare(b.id));
  }

  /* ── 4. La tabla de territorio ───────────────────────────────────────────
     Dos ejes: el peso del arquetipo en el territorio (grande = de la mediana
     para arriba) y la afinidad de esta votación (alta = ×1,05 o más). La
     baja participación manda a «movilizar» cuando el arquetipo ya lo prefiere
     o pesa mucho (rama R2: el que ya lo prefiere y no sale). */
  function mediana(xs) { const s = [...xs].sort((a, b) => a - b), n = s.length; return n ? (n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2) : 0; }
  function cuadrante(a, med) {
    if (a.ratio == null) return null;
    const grande = a.territorio >= med, alta = a.ratio >= AFIN_ALTA;
    const vota_poco = a.participacion != null && a.participacionRef != null && a.participacion <= a.participacionRef - PART_BAJA;
    if (vota_poco && (alta || grande)) return 'movilizar';
    if (alta) return grande ? 'retener' : 'retener-crecer';
    return grande ? 'conocer' : 'no-gastar';
  }
  /* Los barrios fuertes y los huecos de cada arquetipo: índice = peso del
     barrio en esta votación ÷ su peso en el territorio, solo en barrios con un
     tamaño mínimo (un barrio de 300 votantes da cocientes de ruido). */
  function barrios({ L, LT, corte, ids, n = 3 }) {
    const out = Object.fromEntries(ids.map(id => [id, { fuertes: [], huecos: [] }]));
    if (!L?.total || !LT?.total) return out;
    const nombre = Object.fromEntries((LT.filasBarrio || []).map(f => [f.code, { nombre: f.nombre, unidad: f.comuna }]));
    const filas = [];
    Object.entries(LT.pesos || {}).forEach(([code, w]) => {
      if (!w || w < BARRIO_MIN * LT.total) return;
      const dom = LT.dominanteDe(code, corte); if (!out[dom]) return;
      const idx = ((L.pesos?.[code] || 0) / L.total) / (w / LT.total);
      filas.push({ code, dom, idx: r3(idx), peso: w, ...(nombre[code] || { nombre: code, unidad: '' }) });
    });
    ids.forEach(id => {
      const mias = filas.filter(f => f.dom === id);
      out[id].fuertes = mias.filter(f => f.idx >= 1.25).sort((a, b) => (b.idx - a.idx) || (b.peso - a.peso)).slice(0, n);
      out[id].huecos = mias.filter(f => f.idx <= 0.8).sort((a, b) => (a.idx - b.idx) || (b.peso - a.peso)).slice(0, n);
    });
    return out;
  }
  function territorio(banco, arqs, ctx = {}) {
    const med = mediana(arqs.map(a => a.territorio));
    const B = ctx.L && ctx.LT && arqs.some(a => a.ratio != null) ? barrios({ L: ctx.L, LT: ctx.LT, corte: ctx.corte, ids: arqs.map(a => a.id) }) : {};
    const M = banco.matriz, N = banco.notas_matriz || {};
    return arqs.map(a => {
      const q = cuadrante(a, med), C = q ? banco.cuadrantes[q] : null;
      const celdas = v => Object.entries(M[a.codigo] || {}).filter(([, x]) => x === v).map(([p]) => ({ principio: p, nota: N[a.codigo]?.[p] || '' }));
      return { ...a, grande: a.territorio >= med, cuadrante: q, accion: C?.nombre || null, que: C?.que || null, fichas: C?.fichas || [],
        centrales: celdas(2), riesgos: celdas(-1), fuertes: B[a.id]?.fuertes || [], huecos: B[a.id]?.huecos || [] };
    }).sort((a, b) => b.territorio - a.territorio);
  }

  /* ── 5. Figura de ciudad o trabajo de barrio ─────────────────────────────
     El arraigo es la parte de su votación que se aparta de la geografía de su
     propia lista, descontado el azar (medido para el Concejo de Bogotá 2023).
     Se compara con el de la ciudad, con la misma regla. */
  function arraigoDe(datos, slugs) {
    if (!datos?.slugs) return null;
    const slug = (slugs || []).find(s => datos.slugs[s]); if (!slug) return null;
    const [loc, bar] = datos.slugs[slug];
    return { valor: Math.max(loc, bar), localidad: loc, barrio: bar, referencia: datos.referencia, slug };
  }
  function figura({ arraigo, corp }) {
    if (arraigo?.valor != null && arraigo.referencia) {
      const r = arraigo.valor / arraigo.referencia;
      const lectura = r < ARRAIGO_FIGURA ? 'figura' : r > ARRAIGO_BARRIO ? 'barrio' : 'mixto';
      return { lectura, medida: true, valor: arraigo.valor, referencia: arraigo.referencia, ratio: r3(r), ...TEXTO_FIGURA[lectura] };
    }
    if (corp === 'jal') return { lectura: 'barrio', medida: false, oficio: true, ...TEXTO_FIGURA.barrio,
      texto: 'La JAL se elige en la localidad: el trabajo es de barrio. Es criterio de oficio, porque el arraigo todavía solo está medido para el Concejo de Bogotá 2023.' };
    return { lectura: 'sin-medida', medida: false, principios: [], fichas: [],
      texto: 'El arraigo —cuánto de su voto es de base propia de barrio— solo está medido para el Concejo de Bogotá 2023. Sin él no inclinamos la estrategia hacia la ciudad ni hacia el barrio.' };
  }
  const TEXTO_FIGURA = {
    figura: { nombre: 'Figura de ciudad', principios: ['A1', 'A7'], fichas: ['T1', 'T20', 'T22'],
      texto: 'Su voto se reparte por toda la ciudad y casi no es de base propia de barrio: la estrategia es reputación de ciudad —publicidad del nombre y toma de posición—, no feudos.' },
    barrio: { nombre: 'Trabajo de barrio', principios: ['A7'], fichas: ['T21', 'R3.1', 'R3.2'],
      texto: 'Una parte grande de su voto es de base propia en sus barrios: el trabajo es presencia, crédito visible y rendición de cuentas donde ya lo conocen.' },
    mixto: { nombre: 'Entre figura y barrio', principios: ['A1', 'A7'], fichas: ['T20', 'T21'],
      texto: 'Su arraigo está cerca del de la ciudad: tiene base de barrio y voto disperso a la vez. Sirven las dos cosas, reputación de ciudad y presencia donde ya es fuerte.' },
  };

  /* ── 6. La competencia dentro de su lista ────────────────────────────────
     Con voto preferente el rival principal está en la propia lista (Carey y
     Shugart, T3). Lee la escalera y el plano del panel 10, no los recalcula. */
  function competencia(escalera, plano = []) {
    const e = escalera || { estado: 'sin-dato' };
    const base = { estado: e.estado, fichas: ['T3'] };
    if (e.estado === 'abierta') {
      const internos = (e.filas || []).filter(f => !f.usted);
      const u = e.usted;
      /* El rival principal: si usted está en la lista, el de arriba más cercano
         (o el de abajo si ya entra); si no estuvo, el último que entró. */
      let principal = null;
      if (u) {
        const arriba = internos.filter(f => f.votos >= u.votos).sort((a, b) => a.votos - b.votos)[0];
        const abajo = internos.filter(f => f.votos < u.votos).sort((a, b) => b.votos - a.votos)[0];
        principal = (u.elegido ? abajo || arriba : arriba || abajo) || null;
      } else principal = e.ultimo || internos[0] || null;
      const presion = (plano || []).filter(r => norm(r.partido) === norm(e.lista)).map(r => ({ nombre: r.nombre, nivel: r.nivel, votos: r.votos }));
      return { ...base, lista: e.lista, curules: e.k, usted: u ? { puesto: u.puesto, votos: u.votos, elegido: u.elegido } : null, distancia: e.distancia,
        principal: principal ? { nombre: principal.nombre, votos: principal.votos, puesto: principal.puesto, elegido: principal.elegido } : null,
        internos: internos.slice(0, 5).map(f => ({ nombre: f.nombre, votos: f.votos, puesto: f.puesto, elegido: f.elegido })), presion,
        texto: 'Lista abierta con voto preferente: el rival principal está en su propia lista. La reputación personal decide quién entra.' };
    }
    if (e.estado === 'cerrada') return { ...base, lista: e.lista, curules: e.k, texto: 'Lista cerrada: el orden lo fija el partido y el voto personal no decide la curul. Pesan el renglón y la fuerza de la lista.' };
    if (e.estado === 'uninominal') return { ...base, fichas: [], rivales: (plano || []).slice(0, 3).map(r => ({ nombre: r.nombre, nivel: r.nivel, votos: r.votos })), texto: 'Cargo uninominal: no hay lista; el rival está afuera.' };
    if (e.estado === 'sin-partido') return { ...base, texto: 'Sin partido definido no hay lista contra la cual medirse. Cuando lo defina, aparece aquí.' };
    if (e.estado === 'sin-lista') return { ...base, lista: e.partido, texto: 'Su partido no tuvo lista en 2023 en este territorio: no hay escalera con la cual compararse.' };
    return { ...base, estado: 'sin-dato', fichas: [], texto: 'La competencia en su lista sale del panel de contendientes, que todavía no terminó de leer el registro.' };
  }

  /* ── 7. Las acciones de la fase ──────────────────────────────────────────
     Del banco, en el orden de los principios. Las que dependen de la lectura
     (figura o barrio) o del tipo de lista solo salen si aplican. */
  function acciones(banco, faseId, orden, fig, comp) {
    const rango = Object.fromEntries(orden.map((p, i) => [p.id, i]));
    return (banco.acciones || []).filter(a => a.fase === faseId)
      .filter(a => !a.lectura || a.lectura === fig?.lectura || (fig?.lectura === 'mixto'))
      .filter(a => !a.lista || a.lista === comp?.estado)
      .map(a => ({ ...a, oficio: !(a.fichas || []).length }))
      .sort((a, b) => ((rango[a.principio] ?? 9) - (rango[b.principio] ?? 9)) || ((b.lectura || b.lista ? 1 : 0) - (a.lectura || a.lista ? 1 : 0)));
  }

  /* ── El lugar que ocupa, en una frase ────────────────────────────────────
     Sale de los datos: figura o barrio, y su mejor terreno (el arquetipo más
     afín que pesa al menos 8 % de su votación, la regla del panel 05). El
     personaje y los temas propios llegan con el cuestionario. */
  const veces = x => `×${x.toFixed(2).replace('.', ',')}`;
  function lugar(fig, arqs, lente) {
    const afin = arqs.filter(a => a.ratio != null && a.share >= .08).sort((a, b) => b.ratio - a.ratio)[0];
    const quien = { figura: 'Figura de ciudad', barrio: 'Candidatura de barrio', mixto: 'Entre figura de ciudad y candidatura de barrio' }[fig?.lectura] || '';
    const de = lente === 'partido' ? 'su partido' : 'su votación';
    if (!afin) return quien ? `${quien}.` : lente === 'ciudad' ? 'Sin votos propios en la ciudad todavía: la lectura es la de la ciudad entera.' : 'Sin un arquetipo donde se despegue: compite en toda la ciudad.';
    const terreno = afin.ratio >= AFIN_ALTA ? `con su mejor terreno en «${afin.nombre}» (${veces(afin.ratio)} lo que pesa en el territorio)` : `sin un arquetipo donde ${de} se despegue`;
    return quien ? `${quien}, ${terreno}.` : `${terreno.charAt(0).toUpperCase()}${terreno.slice(1)}.`;
  }

  /* ── Entrada única ───────────────────────────────────────────────────────
     e = { banco, fecha?, ciudad, corp, L (la lente: sus votos, su partido o la
           ciudad), lente ('propio'|'partido'|'ciudad'), LT (el territorio: la
           ciudad o, en JAL, su localidad), arraigo?, escalera?, plano? }  */
  function evaluar(e) {
    const banco = e.banco, F = fase(banco, e.fecha);
    const todaviaNo = motivo => ({ estado: 'todavia-no', motivo, fase: F, advertencias: banco.advertencias });
    if (!e.ciudad) return todaviaNo('Los arquetipos —cómo vota cada barrio— existen por ahora para Bogotá, Medellín y Cartagena. Cuando existan para su ciudad, la estrategia se arma sola.');
    if (!CORP_CIUDAD.includes(e.corp)) return todaviaNo('La estrategia por arquetipos se arma para campañas de ciudad (Concejo, Alcaldía y JAL). Una campaña departamental se juega en todo el departamento y los arquetipos son de una ciudad: todavía no.');
    const L = e.L, LT = e.LT || e.L;
    if (!L?.total || !LT?.total) return todaviaNo('No pudimos cruzar la votación con los barrios de la ciudad.');
    const corte = corteDe(LT);
    const cod = codigos(banco, e.ciudad, corte);
    if (!Object.keys(cod).length) {
      const motivo = e.ciudad === 'cartagena' ? 'Cartagena tiene ocho arquetipos propios y la matriz del banco todavía no tiene una fila para cada uno.'
        : e.ciudad === 'bogota' && corte === 'alcaldia' ? 'Los cinco arquetipos de Alcaldía de Bogotá todavía no tienen fila en la matriz del banco (arrancó con los seis de Concejo).'
        : 'Los arquetipos de esta ciudad todavía no tienen fila en la matriz del banco.';
      return todaviaNo(motivo);
    }
    const arqs = arquetiposDe({ banco, ciudad: e.ciudad, L, LT, lente: e.lente });
    const orden = principios(banco, arqs);
    const fig = figura({ arraigo: e.arraigo, corp: e.corp });
    const comp = competencia(e.escalera, e.plano);
    const acc = acciones(banco, F.id, orden, fig, comp);
    return {
      estado: 'ok', fase: F, ciudad: e.ciudad, corp: e.corp, corte, lente: e.lente, recorte: LT.recorte || null,
      arquetipos: arqs, pesos: pesos(arqs), principios: orden,
      /* Filas que redactó el equipo y nadie ha validado (hoy, las 8 de Cartagena). */
      matrizSinValidar: Object.values(cod).some(c => banco.arquetipos?.[c]?.fuente === 'equipo-sin-validar'), territorio: territorio(banco, arqs, { L, LT, corte }),
      figura: fig, competencia: comp, acciones: acc, accion: acc[0] || null, lugar: lugar(fig, arqs, e.lente),
      advertencias: banco.advertencias,
    };
  }

  /* Para pintar una ficha: «Green y Gerber 2019» con su enlace. */
  function ficha(banco, id) { return banco.fichas.find(f => f.id === id) || null; }
  function enlaceDe(f) { const r = f?.refs?.[0]; return r?.doi || r?.url || null; }

  global.C360Estrategia = { BANCO_URL, ARRAIGO_URL, cargarBanco, cargarArraigo, fase, codigos, arquetiposDe, pesos, principios, cuadrante, barrios, territorio, arraigoDe, figura, competencia, acciones, lugar, evaluar, ficha, enlaceDe, hoyISO };
})(typeof window !== 'undefined' ? window : globalThis);
