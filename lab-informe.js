/*
 * lab-informe.js — Sprint G del Lab de Políticas Públicas y Prospectiva.
 *
 * Genera un informe combinado (PDF + Markdown) a partir del trabajo del
 * usuario en los 6 módulos del lab. Lee los 6 localStorage keys:
 *
 *   pp-current-v1      problema-publico.html
 *   micmac-current-v2  analisis-estructural.html
 *   mactor-current-v1  mactor.html
 *   ev-current-v1      evaluacion.html
 *   alt-current-v1     alternativas.html
 *   ain-current-v1     ain.html
 *
 * Expone tres funciones públicas en window.LabInforme:
 *   getLabState()                  → { pp:{exists,data,resumen}, ... }
 *   buildLabPDF(state, jsPDF)      → Promise (descarga PDF)
 *   buildLabMarkdown(state)        → string markdown
 *
 * Sin dependencias salvo jsPDF (cargado on-demand). No toca el DOM
 * directamente; quien lo invoque le pasa el container.
 *
 * Patrón estilo: paleta oxblood (#8a1e16) tomada del chasis del lab.
 */
(function() {
  'use strict';

  // ═══════════════════════════════════════════════════════════════════════
  // Helpers genéricos
  // ═══════════════════════════════════════════════════════════════════════
  function _safeJSON(raw) {
    if (!raw) return null;
    try { return JSON.parse(raw); } catch { return null; }
  }
  function _readLS(key) {
    try { return _safeJSON(localStorage.getItem(key)); }
    catch { return null; }
  }
  function _ymd(d) {
    d = d || new Date();
    return d.toISOString().slice(0, 10);
  }
  function _esLong(d) {
    d = d || new Date();
    return d.toLocaleDateString('es-CO', { year:'numeric', month:'long', day:'numeric' });
  }
  function _trim(s, n) { s = String(s == null ? '' : s).trim(); return s.length > n ? s.slice(0, n - 1) + '…' : s; }
  function _fmtCOP(n) {
    if (n == null || isNaN(n)) return '—';
    const abs = Math.abs(n);
    if (abs >= 1e9) return `COP ${(n/1e9).toFixed(2)}MM`;
    if (abs >= 1e6) return `COP ${(n/1e6).toFixed(1)}M`;
    if (abs >= 1e3) return `COP ${(n/1e3).toFixed(0)}K`;
    return `COP ${n.toFixed(0)}`;
  }
  function _toNum(v) {
    if (typeof v === 'number') return v;
    if (v == null) return null;
    const s = String(v).replace(/[^0-9.,-]/g, '').replace(/,/g, '.');
    const n = parseFloat(s);
    return isNaN(n) ? null : n;
  }
  function _arrSafe(x) { return Array.isArray(x) ? x : []; }
  function _nonEmpty(s) { return String(s == null ? '' : s).trim().length > 0; }

  async function _ensureJsPDF() {
    if (window.jspdf && window.jspdf.jsPDF) return window.jspdf.jsPDF;
    await new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/jspdf@2.5.1/dist/jspdf.umd.min.js';
      s.onload = resolve;
      s.onerror = () => reject(new Error('No se pudo cargar jsPDF.'));
      document.head.appendChild(s);
    });
    if (!window.jspdf || !window.jspdf.jsPDF) throw new Error('jsPDF no disponible.');
    return window.jspdf.jsPDF;
  }

  // ═══════════════════════════════════════════════════════════════════════
  // Diccionarios de labels — copiados de cada módulo para que el informe
  // sea autónomo (no depende del DOM del módulo que lo invoca).
  // ═══════════════════════════════════════════════════════════════════════

  // PP — magnitud / urgencia / marco analítico
  const PP_MAGNITUD = { baja:'baja', media:'media', alta:'alta', critica:'crítica' };
  const PP_URGENCIA = { electoral:'ventana electoral', presupuestal:'ventana presupuestal', emergencia:'emergencia', estructural:'estructural' };
  const PP_MARCO = {
    'racional-bardach':       'Racional simple (Bardach · CEPAL)',
    'multicriterio-adaptativo':'Multi-criterio adaptativo (Walker · Lempert RAND)',
    'participativo':          'Participativo (Roberts · Head & Alford)',
    'gobernanza-colaborativa':'Gobernanza colaborativa (Ansell & Gash)'
  };

  // EV — tipo, alcance, Sinergia DNP, métodos
  const EV_TIPO = {
    descripcion:'Descripción', causal:'Atribución causal', valor:'Valor',
    proceso:'Proceso', gestion:'Gestión'
  };
  const EV_ALCANCE = {
    'ex-ante':'Ex-ante', concurrente:'Concurrente', 'ex-post':'Ex-post', meta:'Meta-evaluación'
  };
  const EV_SINERGIA = {
    ejecutiva:'Ejecutiva', operaciones:'Operaciones', resultados:'Resultados',
    impacto:'Impacto', institucional:'Institucional', mbe:'Mapas de evidencia'
  };
  const EV_METODO = {
    'rct':              'RCT (Banerjee-Duflo-Kremer)',
    'did-staggered':    'DID escalonado (Callaway-Sant\'Anna 2021) ★',
    'did':              'DID clásico (Card-Krueger 1994)',
    'sc-augmented':     'Synthetic Control aumentado (Ben-Michael 2021) ★',
    'sc':               'Synthetic Control clásico (Abadie 2010)',
    'rdd-moderno':      'RDD moderno (Cattaneo-Keele-Titiunik 2023) ★',
    'rd':               'RD clásico (Thistlethwaite-Campbell)',
    'dml':              'Double Machine Learning (Chernozhukov 2018) ★',
    'causal-forest':    'Causal Forests (Wager-Athey 2018) ★',
    'matching':         'Matching / PSM (Rosenbaum-Rubin 1983)',
    'contribucion':     'Análisis de Contribución (Mayne 2024) ★',
    'qual':             'Cualitativo (Patton · Yin)',
    'mixto':            'Mixto (Creswell-Plano Clark 2017)',
    'vfm':              'Value-for-Money + MVPF (HM Treasury · Hendren 2020)'
  };
  const EV_NIVEL = { insumos:'Insumos', actividades:'Actividades', productos:'Productos', resultados:'Resultados', impacto:'Impacto' };

  // ALT — tipos de variable, escenarios
  const ALT_VAR_TIPO = {
    cobertura:'Cobertura', financiamiento:'Financiamiento', instrumento:'Instrumento',
    gobernanza:'Gobernanza', condicionalidad:'Condicionalidad', timing:'Timing',
    poblacion:'Población', ambito:'Ámbito', modalidad:'Modalidad',
    sostenibilidad:'Sostenibilidad', otra:'Otra'
  };

  // AIN — tipo de falla, tipo de opción, nivel de impacto, nivel de riesgo
  const AIN_TIPO_FALLA = {
    mercado:'Falla de mercado', externalidad:'Externalidad',
    'asimetria-info':'Asimetría de información', coordinacion:'Falla de coordinación',
    'equidad-distributiva':'Equidad distributiva', 'monopolio-natural':'Monopolio natural'
  };
  const AIN_OPT_TIPO = {
    'statu-quo':'Statu quo (no regular)',
    'regular-directo':'Regulación directa',
    'autorregulacion':'Autorregulación',
    'co-regulacion':'Co-regulación',
    'sandbox':'Sandbox regulatorio',
    'instr-mercado':'Instrumentos de mercado',
    'otra':'Otra'
  };
  const AIN_IMP_LABEL = { 'bajo':'Bajo', 'medio':'Medio', 'alto':'Alto', 'muy-alto':'Muy alto' };
  const AIN_RIESGO_LABEL = { 'bajo':'Bajo', 'medio':'Medio', 'alto':'Alto' };
  const AIN_RIESGO_DIM = {
    captura:'Captura del regulador',
    asimetria:'Asimetría de información',
    carga_excesiva:'Carga excesiva',
    fragmentacion:'Fragmentación normativa',
    obsolescencia:'Obsolescencia'
  };

  // ═══════════════════════════════════════════════════════════════════════
  // Resumidores por módulo
  // Cada uno devuelve { titulo, descripcion, kpis:[{k,v}], extras:{}, isEmpty }
  // ═══════════════════════════════════════════════════════════════════════

  function _resumenPP(s) {
    if (!s || !s.definicion) return { isEmpty:true };
    const d = s.definicion || {};
    const enun = String(d.enunciado || '').trim();
    if (!enun && _arrSafe(d.causas).length === 0 && _arrSafe(d.afectados).length === 0) return { isEmpty:true };
    const causas = _arrSafe(d.causas).filter(_nonEmpty);
    const efectos = _arrSafe(d.efectos).filter(_nonEmpty);
    const afectados = _arrSafe(d.afectados).filter(_nonEmpty);
    const ev = _arrSafe(s.evidencia).filter(e => e && (_nonEmpty(e.dato) || _nonEmpty(e.fuente)));
    const alt = _arrSafe(s.alternativas);
    const crit = _arrSafe(s.criterios);
    // Recomendación: alternativa con score más alto en s.scores
    let recomendada = null;
    if (alt.length > 0 && crit.length > 0 && s.scores && typeof s.scores === 'object') {
      const sumPesos = crit.reduce((a,c) => a + (Number(c.peso) || 0), 0) || 1;
      let bestScore = -Infinity, bestIdx = -1;
      alt.forEach((a, ai) => {
        let sc = 0, n = 0;
        crit.forEach((c, ci) => {
          const cell = s.scores[`a${ai}-c${ci}`];
          if (typeof cell === 'number') { sc += cell * ((Number(c.peso)||0)/sumPesos); n++; }
        });
        if (n === crit.length && sc > bestScore) { bestScore = sc; bestIdx = ai; }
      });
      if (bestIdx >= 0) recomendada = { nombre: alt[bestIdx]?.nombre || `Alternativa ${bestIdx+1}`, score: bestScore };
    }
    // Diagnóstico Rittel
    const rittel = _arrSafe(s.diagnostico?.rittel);
    const rittelScore = rittel.filter(v => v === true).length;
    let rittelTipo = '';
    if (rittel.some(v => v !== null && v !== undefined)) {
      if (rittelScore <= 2) rittelTipo = 'Tame';
      else if (rittelScore <= 5) rittelTipo = 'Complejo';
      else if (rittelScore <= 8) rittelTipo = 'Wicked';
      else rittelTipo = 'Meta-wicked';
    }
    return {
      isEmpty: false,
      titulo: 'Diagnóstico del problema',
      enunciado: enun || '—',
      magnitud: PP_MAGNITUD[d.magnitud] || d.magnitud || null,
      urgencia: PP_URGENCIA[d.urgencia] || d.urgencia || null,
      afectados, causas, efectos,
      evidencia: ev,
      alternativas: alt,
      recomendada,
      rittelScore: rittel.length ? rittelScore : null,
      rittelTipo,
      marco: PP_MARCO[s.diagnostico?.marco] || ''
    };
  }

  function _resumenMicmac(s) {
    if (!s) return { isEmpty:true };
    const variables = _arrSafe(s.variables).filter(v => v && _nonEmpty(v.nombre));
    if (variables.length < 2) return { isEmpty:true };
    // Calculamos motricidad / dependencia desde la matriz (acepta valencias firmadas).
    const M = s.matrix && typeof s.matrix === 'object' ? s.matrix : {};
    const N = variables.length;
    const motri = new Array(N).fill(0);
    const dep   = new Array(N).fill(0);
    for (let i = 0; i < N; i++) {
      for (let j = 0; j < N; j++) {
        if (i === j) continue;
        const key = `${i}-${j}`;
        const v = M[key];
        let mag = 0;
        if (typeof v === 'number') mag = Math.abs(v);
        else if (typeof v === 'object' && v) mag = Math.abs(Number(v.valor) || 0);
        motri[i] += mag;
        dep[j]   += mag;
      }
    }
    const total = motri.reduce((a,b)=>a+b, 0);
    if (total === 0) return { isEmpty:true };
    const items = variables.map((v, i) => ({
      nombre: v.nombre, motri: motri[i], dep: dep[i],
      cuadrante: _cuadranteMicmac(motri[i], dep[i], motri, dep)
    }));
    const topMotri = items.slice().sort((a,b) => b.motri - a.motri).slice(0, 5);
    const claves = items.filter(it => it.cuadrante === 'motriz' || it.cuadrante === 'clave');
    return {
      isEmpty: false,
      titulo: 'Análisis estructural del sistema',
      nVars: variables.length,
      topMotri,
      claves: claves.slice(0, 5),
      territorio: s.territorio || s.contexto?.territorio || '',
      plantilla: s.plantilla || ''
    };
  }
  function _cuadranteMicmac(mi, di, motri, dep) {
    const mMed = _med(motri), dMed = _med(dep);
    if (mi >= mMed && di >= dMed) return 'clave';
    if (mi >= mMed && di < dMed)  return 'motriz';
    if (mi < mMed && di >= dMed)  return 'resultado';
    return 'autonoma';
  }
  function _med(a) {
    const s = a.slice().sort((x,y)=>x-y);
    const n = s.length;
    if (n === 0) return 0;
    return n % 2 === 0 ? (s[n/2-1] + s[n/2]) / 2 : s[(n-1)/2];
  }

  function _resumenMactor(s) {
    if (!s) return { isEmpty:true };
    const actores = _arrSafe(s.actores).filter(a => a && _nonEmpty(a.nombre));
    const objetivos = _arrSafe(s.objetivos).filter(o => o && _nonEmpty(o.nombre || o));
    if (actores.length < 2) return { isEmpty:true };
    const N = actores.length;
    const MID = s.mid || {};
    const MAO = s.mao || {};
    const I = new Array(N).fill(0), D = new Array(N).fill(0);
    for (let i = 0; i < N; i++) {
      for (let j = 0; j < N; j++) {
        if (i === j) continue;
        const v = Number(MID[`${i}-${j}`]) || 0;
        I[i] += v;
        D[j] += v;
      }
    }
    const R = actores.map((_, i) => {
      const den = I[i] + D[i];
      return den > 0 ? I[i] / den : 0;
    });
    const items = actores.map((a, i) => ({
      nombre: a.nombre, I:I[i], D:D[i], R:R[i],
      cuadrante: _cuadranteMactor(I[i], D[i], I, D)
    }));
    const topDom = items.slice().sort((a,b) => b.R - a.R).slice(0, 5);
    // Saldo por objetivo
    const M = objetivos.length;
    const saldos = [];
    for (let k = 0; k < M; k++) {
      let saldo = 0, mov = 0;
      for (let i = 0; i < N; i++) {
        const v = Number(MAO[`${i}-${k}`]) || 0;
        saldo += v * R[i];
        mov += Math.abs(v);
      }
      saldos.push({
        nombre: objetivos[k]?.nombre || objetivos[k] || `Obj ${k+1}`,
        saldo, mov
      });
    }
    const objetivosSorted = saldos.slice().sort((a,b) => b.saldo - a.saldo);
    return {
      isEmpty: false,
      titulo: 'Mapa de actores y conflictos',
      nActores: actores.length,
      nObjetivos: objetivos.length,
      topDom,
      objetivos: objetivosSorted.slice(0, 6)
    };
  }
  function _cuadranteMactor(Ii, Di, I, D) {
    const im = _med(I), dm = _med(D);
    if (Ii >= im && Di >= dm) return 'enlace';
    if (Ii >= im && Di < dm)  return 'dominante';
    if (Ii < im && Di >= dm)  return 'dominado';
    return 'autonomo';
  }

  function _resumenEv(s) {
    if (!s || !s.pregunta) return { isEmpty:true };
    const enun = String(s.pregunta.enunciado || '').trim();
    if (!enun) return { isEmpty:true };
    const inds = _arrSafe(s.indicadores).filter(i => i && _nonEmpty(i.nombre));
    const eco = s.economico || {};
    let ecoBlock = null;
    if (eco.activo) {
      const cba = _calcCBA(eco.cba || {});
      const mvpf = _calcMVPF(eco.mvpf || {});
      const cea = _calcCEA(eco.cea || {});
      ecoBlock = { cba, mvpf, cea };
    }
    return {
      isEmpty: false,
      titulo: 'Plan de evaluación',
      enunciado: enun,
      tipo: EV_TIPO[s.pregunta.tipo] || '',
      alcance: EV_ALCANCE[s.pregunta.alcance] || '',
      tipoSinergia: EV_SINERGIA[s.pregunta.tipo_sinergia] || '',
      metodo: EV_METODO[s.metodo?.id] || '',
      tratamientoEscalonado: s.metodo?.tratamiento_escalonado || '',
      justificacion: s.metodo?.justificacion || '',
      nIndicadores: inds.length,
      indicadoresImpacto: inds.filter(i => i.nivel === 'impacto').slice(0, 4),
      indicadoresResultado: inds.filter(i => i.nivel === 'resultados').slice(0, 4),
      eco: ecoBlock,
      plan: s.plan || {}
    };
  }
  function _calcCBA(cba) {
    const c = _toNum(cba.costos_total);
    const b = _toNum(cba.beneficios_total);
    const r = (_toNum(cba.tasa_descuento) || 9) / 100;
    const h = Math.max(1, Math.min(50, Math.round(_toNum(cba.horizonte_anios) || 10)));
    if (c == null || b == null) return { vpn:null, h, r, ratio:null };
    let vpn = 0;
    const flujo = b - c;
    for (let t = 1; t <= h; t++) vpn += flujo / Math.pow(1 + r, t);
    const ratio = c > 0 ? b / c : null;
    return { vpn, h, r, ratio };
  }
  function _calcMVPF(mvpf) {
    const b = _toNum(mvpf.beneficios_receptores);
    const c = _toNum(mvpf.costo_neto_gob);
    if (b == null || c == null || c <= 0) return { ratio:null, pareto:false };
    return { ratio: b/c, pareto: b/c > 1 };
  }
  function _calcCEA(cea) {
    const c = _toNum(cea.costo_total);
    const o = _toNum(cea.outcome_total);
    if (c == null || o == null || o <= 0) return { cea:null, unidad: cea.outcome_unidad || 'unidad' };
    return { cea: c / o, unidad: cea.outcome_unidad || 'unidad' };
  }

  function _resumenAlt(s) {
    if (!s) return { isEmpty:true };
    const vars = _arrSafe(s.variables).filter(v => v && _nonEmpty(v.nombre));
    const alts = _arrSafe(s.alternativas).filter(a => a && _nonEmpty(a.nombre));
    if (vars.length === 0 && alts.length === 0) return { isEmpty:true };
    // Recomendación final
    const recId = s.decision?.altId_recomendada;
    let recomendada = recId ? alts.find(a => a.id === recId) : null;
    // Si no hay decisión explícita, ranking por score final
    if (!recomendada && alts.length > 0) {
      const scenarios = _arrSafe(s.escenarios);
      const probSum = scenarios.reduce((a, e) => a + (Number(e.prob) || 0), 0) || 1;
      let bestF = -Infinity, best = null;
      alts.forEach(alt => {
        const r = s.ratings?.[alt.id] || {};
        let exp = 0, worst = 5, complete = true;
        scenarios.forEach(e => {
          const rv = Number(r[e.id]);
          if (!rv || rv < 1) complete = false;
          else { exp += rv * (Number(e.prob)||0); if (rv < worst) worst = rv; }
        });
        if (!complete) return;
        const expectedAvg = exp / probSum;
        const bonus = worst >= 3 ? 0.5 : 0;
        const fin = expectedAvg + bonus;
        if (fin > bestF) { bestF = fin; best = { alt, fin, exp: expectedAvg, worst }; }
      });
      if (best) recomendada = { ...best.alt, score: best.fin, expected: best.exp, worst: best.worst };
    }
    // Lente económica
    let econ = null;
    if (recomendada?.econ) {
      const c = _toNum(recomendada.econ.costo_total);
      const b = _toNum(recomendada.econ.beneficio_total);
      const o = _toNum(recomendada.econ.outcome_total);
      if (c != null && b != null) econ = { mvpf: c > 0 ? b/c : null, costo:c, beneficio:b };
      if (c != null && o != null && o > 0) econ = { ...(econ||{}), cea: c/o, unidad: recomendada.econ.unidad_outcome || 'unidad' };
    }
    return {
      isEmpty: false,
      titulo: 'Alternativas de política',
      nVars: vars.length,
      nAlts: alts.length,
      variables: vars.map(v => ({ nombre:v.nombre, tipo: ALT_VAR_TIPO[v.tipo] || v.tipo || '' })),
      alternativas: alts,
      recomendada,
      justificacion: s.decision?.justificacion || '',
      econ
    };
  }

  function _resumenAin(s) {
    if (!s || !s.problema_reg) return { isEmpty:true };
    const pr = s.problema_reg || {};
    const enun = String(pr.enunciado || '').trim();
    const opciones = _arrSafe(s.opciones).filter(o => o && _nonEmpty(o.nombre));
    if (!enun && opciones.length === 0) return { isEmpty:true };
    const objetivos = _arrSafe(s.objetivos).filter(o => o && _nonEmpty(o.enunciado));
    // Recomendación final
    const recId = s.recomendacion?.opcionId_recomendada;
    let recomendada = recId ? opciones.find(o => o.id === recId) : null;
    // Si no hay decisión explícita, ranking por score de impactos
    if (!recomendada && opciones.length > 0) {
      const mapImp = { 'bajo':1, 'medio':2, 'alto':3, 'muy-alto':4 };
      let bestS = -Infinity, best = null;
      opciones.forEach(o => {
        const ip = (s.impactos || {})[o.id] || {};
        const bene = mapImp[ip.beneficios];
        const cd = mapImp[ip.costos_directos], ci = mapImp[ip.costos_indirectos];
        const cap = mapImp[ip.captura], ca = mapImp[ip.carga_admin];
        if (!bene || !cd || !ci || !cap || !ca) return;
        const cost = (cd + ci + cap + ca) / 4;
        const sc = bene - cost;
        if (sc > bestS) { bestS = sc; best = { o, sc, bene, cost }; }
      });
      if (best) recomendada = { ...best.o, score: best.sc };
    }
    // Riesgos
    const riesgos = s.riesgo_reg || {};
    const riesgoChips = [];
    Object.keys(AIN_RIESGO_DIM).forEach(k => {
      if (riesgos[k]) riesgoChips.push({ dim: AIN_RIESGO_DIM[k], nivel: AIN_RIESGO_LABEL[riesgos[k]] || riesgos[k] });
    });
    return {
      isEmpty: false,
      titulo: 'Análisis de Impacto Normativo',
      enunciado: enun,
      tipoFalla: AIN_TIPO_FALLA[pr.tipo_falla] || '',
      afectados: _arrSafe(pr.afectados).filter(_nonEmpty),
      objetivos,
      nOpciones: opciones.length,
      opciones,
      recomendada,
      justificacion: s.recomendacion?.justificacion || '',
      riesgos: riesgoChips,
      implementacion: s.implementacion || {}
    };
  }

  // ═══════════════════════════════════════════════════════════════════════
  // API pública · getLabState
  // ═══════════════════════════════════════════════════════════════════════
  function getLabState() {
    const pp        = _readLS('pp-current-v1');
    const micmac    = _readLS('micmac-current-v2');
    const mactor    = _readLS('mactor-current-v1');
    const ev        = _readLS('ev-current-v1');
    const alt       = _readLS('alt-current-v1');
    const ain       = _readLS('ain-current-v1');
    return {
      pp:         { exists: !!pp,     data: pp,     resumen: _resumenPP(pp) },
      micmac:     { exists: !!micmac, data: micmac, resumen: _resumenMicmac(micmac) },
      mactor:     { exists: !!mactor, data: mactor, resumen: _resumenMactor(mactor) },
      ev:         { exists: !!ev,     data: ev,     resumen: _resumenEv(ev) },
      alt:        { exists: !!alt,    data: alt,    resumen: _resumenAlt(alt) },
      ain:        { exists: !!ain,    data: ain,    resumen: _resumenAin(ain) }
    };
  }

  function countActiveModules(state) {
    let n = 0;
    if (!state) return 0;
    ['pp','micmac','mactor','ev','alt','ain'].forEach(k => { if (!state[k].resumen.isEmpty) n++; });
    return n;
  }

  // ═══════════════════════════════════════════════════════════════════════
  // Resumen ejecutivo (auto-generado a partir del state)
  // ═══════════════════════════════════════════════════════════════════════
  function buildResumenEjecutivo(state) {
    const partes = [];
    const pp = state.pp.resumen;
    if (!pp.isEmpty) {
      partes.push(`El problema central es: «${_trim(pp.enunciado, 200)}»`);
      if (pp.rittelTipo) partes.push(`El diagnóstico Rittel-Webber lo clasifica como ${pp.rittelTipo.toLowerCase()} (${pp.rittelScore}/10).`);
    }
    const mc = state.micmac.resumen;
    if (!mc.isEmpty && mc.topMotri.length > 0) {
      const palancas = mc.topMotri.slice(0, 3).map(v => v.nombre).join(', ');
      partes.push(`El análisis estructural identifica como variables motrices del sistema: ${palancas}.`);
    }
    const ma = state.mactor.resumen;
    if (!ma.isEmpty && ma.topDom.length > 0) {
      const dom = ma.topDom.slice(0, 2).map(a => a.nombre).join(' y ');
      partes.push(`El mapa de actores ubica a ${dom} como dominantes del proceso.`);
    }
    const al = state.alt.resumen;
    if (!al.isEmpty && al.recomendada) {
      partes.push(`La alternativa recomendada es «${_trim(al.recomendada.nombre, 100)}»` +
        (al.recomendada.score ? ` con score esperado ${al.recomendada.score.toFixed(2)}.` : '.'));
    }
    const ai = state.ain.resumen;
    if (!ai.isEmpty && ai.recomendada) {
      partes.push(`Si la salida es regulatoria, la opción seleccionada es «${_trim(ai.recomendada.nombre, 100)}».`);
    }
    const ev = state.ev.resumen;
    if (!ev.isEmpty) {
      partes.push(`El plan de evaluación usa ${ev.metodo || 'método sin definir'} ` +
        `con ${ev.nIndicadores} indicador${ev.nIndicadores === 1 ? '' : 'es'}.`);
    }
    if (partes.length === 0) {
      return 'Este informe está vacío — comience por definir el problema en el módulo de Problema Público.';
    }
    return partes.join(' ');
  }

  // ═══════════════════════════════════════════════════════════════════════
  // Markdown builder
  // ═══════════════════════════════════════════════════════════════════════
  function buildLabMarkdown(state) {
    state = state || getLabState();
    const date = _esLong();
    let md = `# Informe combinado del Lab de Políticas Públicas y Prospectiva\n\n`;
    md += `**Fecha:** ${date}\n\n`;
    md += `*Borrador integrado automatizado por el Laboratorio de Políticas ` +
          `de ricardoruiz.co. Combina los 6 módulos canónicos del lab: ` +
          `problema público (Bardach · CEPAL), análisis estructural ` +
          `(MicMac · DEMATEL · ISM), análisis de actores (Mactor · Godet), ` +
          `alternativas (Zwicky · Lempert/RDM), Análisis de Impacto Normativo ` +
          `(OCDE RIA · DNP Decreto 1081), y evaluación (OCDE-DAC · Mayne · ` +
          `Pre-Analysis Plans).*\n\n`;
    md += `---\n\n`;
    md += `## Resumen ejecutivo\n\n${buildResumenEjecutivo(state)}\n\n`;

    // 1. Diagnóstico
    const pp = state.pp.resumen;
    md += `## 1. Diagnóstico del problema\n\n`;
    if (pp.isEmpty) {
      md += `_(El módulo de Problema Público no tiene contenido — completa ` +
            '`problema-publico.html` para una sección sustantiva aquí.)_\n\n';
    } else {
      md += `**Enunciado:** ${pp.enunciado}\n\n`;
      if (pp.magnitud || pp.urgencia) md += `**Magnitud:** ${pp.magnitud || '—'}  ·  **Urgencia:** ${pp.urgencia || '—'}\n\n`;
      if (pp.afectados.length) md += `**Población afectada:** ${pp.afectados.join('; ')}\n\n`;
      if (pp.causas.length) { md += `**Causas raíz:**\n\n`; pp.causas.forEach(c => md += `- ${c}\n`); md += `\n`; }
      if (pp.efectos.length) { md += `**Efectos:**\n\n`; pp.efectos.forEach(e => md += `- ${e}\n`); md += `\n`; }
      if (pp.rittelTipo) md += `**Diagnóstico de complejidad (Rittel-Webber 1973):** ${pp.rittelTipo} — ${pp.rittelScore}/10 propiedades wicked.\n\n`;
      if (pp.marco) md += `**Marco analítico:** ${pp.marco}.\n\n`;
      if (pp.evidencia.length) {
        md += `**Evidencia inicial (${pp.evidencia.length} fuentes):**\n\n`;
        pp.evidencia.slice(0, 8).forEach(e => {
          md += `- ${e.fuente || 'Fuente'}${e.anyo ? ' ('+e.anyo+')' : ''}: ${e.dato || '—'}\n`;
        });
        md += `\n`;
      }
    }

    // 2. Sistema
    const mc = state.micmac.resumen;
    md += `## 2. Variables motrices del sistema (Análisis estructural)\n\n`;
    if (mc.isEmpty) {
      md += `_(El módulo de Análisis Estructural no tiene matriz capturada.)_\n\n`;
    } else {
      md += `Sistema con **${mc.nVars} variables** analizadas.\n\n`;
      md += `**Top variables motrices (palancas del sistema):**\n\n`;
      md += `| # | Variable | Motricidad | Dependencia | Cuadrante |\n`;
      md += `|---|---|---|---|---|\n`;
      mc.topMotri.forEach((v, i) => {
        md += `| ${i+1} | ${v.nombre} | ${v.motri.toFixed(1)} | ${v.dep.toFixed(1)} | ${v.cuadrante} |\n`;
      });
      md += `\n`;
      if (mc.claves.length) {
        md += `**Variables clave (alta motricidad + alta dependencia):** ` +
              mc.claves.map(v => v.nombre).join(', ') + `.\n\n`;
      }
    }

    // 3. Actores
    const ma = state.mactor.resumen;
    md += `## 3. Mapa de actores y conflictos (Mactor)\n\n`;
    if (ma.isEmpty) {
      md += `_(El módulo de Mactor no tiene actores capturados.)_\n\n`;
    } else {
      md += `${ma.nActores} actores y ${ma.nObjetivos} objetivos en disputa.\n\n`;
      md += `**Actores dominantes (poder relativo Ri = Ii / (Ii+Di)):**\n\n`;
      md += `| # | Actor | Influencia | Dependencia | Ri |\n`;
      md += `|---|---|---|---|---|\n`;
      ma.topDom.forEach((a, i) => {
        md += `| ${i+1} | ${a.nombre} | ${a.I.toFixed(1)} | ${a.D.toFixed(1)} | ${a.R.toFixed(2)} |\n`;
      });
      md += `\n`;
      if (ma.objetivos.length) {
        md += `**Objetivos por saldo neto (ponderado por poder de cada actor):**\n\n`;
        md += `| # | Objetivo | Saldo | Movilización |\n`;
        md += `|---|---|---|---|\n`;
        ma.objetivos.forEach((o, i) => {
          md += `| ${i+1} | ${o.nombre} | ${o.saldo >= 0 ? '+' : ''}${o.saldo.toFixed(1)} | ${o.mov.toFixed(1)} |\n`;
        });
        md += `\n`;
      }
    }

    // 4. Alternativas
    const al = state.alt.resumen;
    md += `## 4. Espacio de alternativas (análisis morfológico + RDM)\n\n`;
    if (al.isEmpty) {
      md += `_(El módulo de Alternativas no tiene contenido.)_\n\n`;
    } else {
      md += `${al.nVars} variables de decisión × ${al.nAlts} alternativas ensambladas.\n\n`;
      if (al.recomendada) {
        md += `**Alternativa recomendada:** ${al.recomendada.nombre}`;
        if (al.recomendada.score) md += ` _(score ${al.recomendada.score.toFixed(2)})_`;
        md += `\n\n`;
        if (al.recomendada.desc) md += `${al.recomendada.desc}\n\n`;
        if (al.recomendada.supuestos) md += `**Supuestos críticos:** ${al.recomendada.supuestos}\n\n`;
        if (al.recomendada.riesgo) md += `**Riesgo dominante:** ${al.recomendada.riesgo}\n\n`;
      }
      if (al.econ) {
        md += `**Lente económica:**\n`;
        if (al.econ.mvpf != null) md += `- MVPF = ${al.econ.mvpf.toFixed(2)}${al.econ.mvpf > 1 ? ' (Pareto-superior)' : ''}\n`;
        if (al.econ.cea != null) md += `- CEA = ${_fmtCOP(al.econ.cea)} por ${al.econ.unidad}\n`;
        md += `\n`;
      }
      if (al.justificacion) md += `**Justificación de la elección:** ${al.justificacion}\n\n`;
    }

    // 5. Análisis Regulatorio
    const ai = state.ain.resumen;
    md += `## 5. Análisis de Impacto Normativo (AIN)\n\n`;
    if (ai.isEmpty) {
      md += `_(No aplica una salida regulatoria, o el módulo está vacío.)_\n\n`;
    } else {
      if (ai.tipoFalla) md += `**Tipo de falla regulatoria:** ${ai.tipoFalla}\n\n`;
      if (ai.enunciado) md += `${ai.enunciado}\n\n`;
      if (ai.recomendada) {
        md += `**Opción regulatoria recomendada:** ${ai.recomendada.nombre} _(${AIN_OPT_TIPO[ai.recomendada.tipo] || ai.recomendada.tipo})_\n\n`;
        if (ai.recomendada.desc) md += `${ai.recomendada.desc}\n\n`;
      }
      if (ai.riesgos.length) {
        md += `**Riesgos regulatorios identificados:**\n\n`;
        ai.riesgos.forEach(r => md += `- ${r.dim}: ${r.nivel}\n`);
        md += `\n`;
      }
      if (ai.justificacion) md += `**Justificación:** ${ai.justificacion}\n\n`;
    }

    // 6. Evaluación
    const ev = state.ev.resumen;
    md += `## 6. Plan de evaluación\n\n`;
    if (ev.isEmpty) {
      md += `_(El módulo de Evaluación no tiene plan capturado.)_\n\n`;
    } else {
      md += `**Pregunta evaluativa:** ${ev.enunciado}\n\n`;
      if (ev.tipo || ev.alcance) md += `**Tipo:** ${ev.tipo || '—'}  ·  **Alcance:** ${ev.alcance || '—'}`;
      if (ev.tipoSinergia) md += `  ·  **Sinergia DNP:** ${ev.tipoSinergia}`;
      md += `\n\n`;
      if (ev.metodo) md += `**Método principal:** ${ev.metodo}\n\n`;
      if (ev.tratamientoEscalonado === 'si') md += `> Tratamiento escalonado detectado — se recomienda DID escalonado (Callaway-Sant'Anna 2021) para evitar el sesgo TWFE.\n\n`;
      md += `**Indicadores SMART:** ${ev.nIndicadores} registrados`;
      if (ev.indicadoresImpacto.length) md += ` · impacto: ${ev.indicadoresImpacto.map(i => i.nombre).join(', ')}`;
      md += `.\n\n`;
      if (ev.eco) {
        md += `**Análisis económico (pre-registrado):**\n`;
        if (ev.eco.cba.vpn != null) md += `- CBA → VPN ${_fmtCOP(ev.eco.cba.vpn)} (r=${(ev.eco.cba.r*100).toFixed(1)}% · h=${ev.eco.cba.h}a)`+(ev.eco.cba.ratio ? ` · B/C ${ev.eco.cba.ratio.toFixed(2)}` : '')+`\n`;
        if (ev.eco.mvpf.ratio != null) md += `- MVPF → ${ev.eco.mvpf.ratio.toFixed(2)}${ev.eco.mvpf.pareto ? ' (Pareto-superior)' : ''}\n`;
        if (ev.eco.cea.cea != null) md += `- CEA → ${_fmtCOP(ev.eco.cea.cea)} por ${ev.eco.cea.unidad}\n`;
        md += `\n`;
      }
    }

    // Próximos pasos
    md += `## 7. Próximos pasos operativos\n\n`;
    const pasos = [];
    if (!pp.isEmpty && pp.evidencia.length < 3) pasos.push('Levantar evidencia adicional (mínimo 3 fuentes) para sostener el diagnóstico.');
    if (!ma.isEmpty && ma.objetivos.length && ma.objetivos[0].saldo < 0) pasos.push(`El saldo del objetivo principal es negativo (${ma.objetivos[0].nombre}) — diseñar estrategia de negociación con dominantes opositores.`);
    if (!al.isEmpty && !al.recomendada) pasos.push('Completar la matriz de robustez en los 4 escenarios para identificar la alternativa recomendada.');
    if (!ev.isEmpty && ev.nIndicadores < 4) pasos.push('Completar indicadores SMART mínimos (≥ 4) para la evaluación.');
    if (!ev.isEmpty && !ev.eco) pasos.push('Activar el módulo económico (CBA · MVPF · CEA) para defender la asignación presupuestal.');
    if (state.pp.exists && !state.ev.exists) pasos.push('Planificar la evaluación del problema definido — abrir `evaluacion.html` para diseñar el Pre-Analysis Plan.');
    if (pasos.length === 0) pasos.push('Validar el informe con los actores dominantes identificados y refinar antes de comité.');
    pasos.forEach((p, i) => md += `${i+1}. ${p}\n`);
    md += `\n---\n\n`;
    md += `*Generado con el Lab de Políticas Públicas y Prospectiva (ricardoruiz.co). ` +
          `Las raíces metodológicas combinadas en este informe: Eightfold Path ` +
          `(Bardach 2020), prospectiva francesa (Godet · Mojica · LIPSOR), ` +
          `Robust Decision Making (Lempert-Walker RAND 2003), análisis morfológico ` +
          `(Zwicky 1969 · Ritchey 2011), OCDE RIA (2012/2022), MVPF ` +
          `(Hendren-Sprung-Keyser NBER 2020), OCDE-DAC (2019/2021) y ` +
          `Pre-Analysis Plans (AEA RCT Registry · Olken 2015 JEP). Este es un ` +
          `**borrador automatizado**; debe ser revisado, editado y validado ` +
          `antes de presentarse ante comité técnico.*\n`;

    return md;
  }

  // ═══════════════════════════════════════════════════════════════════════
  // PDF builder con jsPDF
  // ═══════════════════════════════════════════════════════════════════════
  async function buildLabPDF(state) {
    state = state || getLabState();
    let jsPDF;
    try { jsPDF = await _ensureJsPDF(); }
    catch (e) { throw new Error('No se pudo cargar jsPDF: ' + e.message); }
    const doc = new jsPDF({ unit:'mm', format:'a4' });
    const PW = 210, PH = 297, M = 18;
    let y = M;
    const ACC  = [137, 30, 22];
    const INK  = [26, 22, 16];
    const INK2 = [90, 84, 72];
    const RULE = [200, 195, 185];
    const SOFT = [245, 240, 230];

    function setFont(w, s) { doc.setFont('helvetica', w); doc.setFontSize(s); }
    function pageBreak(needed) { if (y + needed > PH - M - 8) { _drawFooter(); doc.addPage(); y = M; _drawHeader(); } }
    function _drawHeader() {
      setFont('normal', 8); doc.setTextColor(...INK2);
      doc.text('Informe combinado · Lab de Políticas Públicas y Prospectiva', M, M - 6);
      doc.setDrawColor(...RULE); doc.setLineWidth(0.2);
      doc.line(M, M - 4, PW - M, M - 4);
      doc.setTextColor(...INK);
    }
    function _drawFooter() {
      const yy = PH - 10;
      setFont('normal', 8); doc.setTextColor(...INK2);
      doc.text('ricardoruiz.co · Laboratorio de Políticas · ' + _esLong(), M, yy);
      doc.text(String(doc.internal.getCurrentPageInfo().pageNumber), PW - M, yy, { align:'right' });
      doc.setTextColor(...INK);
    }
    function drawTitle(t) {
      setFont('bold', 18); doc.setTextColor(...ACC); doc.text(t, M, y); y += 8;
      doc.setDrawColor(...ACC); doc.setLineWidth(0.6); doc.line(M, y, PW - M, y); y += 6;
      doc.setTextColor(...INK);
    }
    function drawH2(t) {
      pageBreak(14);
      setFont('bold', 13); doc.setTextColor(...ACC); doc.text(t, M, y); y += 7;
      doc.setTextColor(...INK);
    }
    function drawPara(t, opts) {
      if (t == null || String(t).trim() === '') return;
      setFont(opts?.bold ? 'bold' : 'normal', opts?.size || 10);
      doc.setTextColor(...(opts?.color || INK));
      const lines = doc.splitTextToSize(String(t), PW - 2 * M);
      lines.forEach(line => { pageBreak(5); doc.text(line, M, y); y += 4.8; });
      y += 1.5;
    }
    function drawKV(k, v) {
      if (v == null || String(v).trim() === '') return;
      setFont('bold', 10); doc.setTextColor(...INK); pageBreak(5);
      const klabel = k + ': '; doc.text(klabel, M, y);
      const kw = doc.getTextWidth(klabel);
      setFont('normal', 10); doc.setTextColor(...INK2);
      const lines = doc.splitTextToSize(String(v), PW - 2 * M - kw);
      if (lines.length === 1) { doc.text(lines[0], M + kw, y); y += 5.5; }
      else {
        doc.text(lines[0], M + kw, y); y += 4.8;
        for (let i = 1; i < lines.length; i++) { pageBreak(5); doc.text(lines[i], M, y); y += 4.8; }
        y += 1.5;
      }
      doc.setTextColor(...INK);
    }
    function drawList(items, opts) {
      if (!items || !items.length) return;
      setFont('normal', opts?.size || 10); doc.setTextColor(...INK);
      items.forEach(it => {
        const txt = '• ' + it;
        const lines = doc.splitTextToSize(txt, PW - 2 * M - 3);
        lines.forEach((line, i) => { pageBreak(5); doc.text(line, M + (i === 0 ? 0 : 3), y); y += 4.6; });
      });
      y += 1;
    }
    function drawTable(headers, rows, widths, highlightIdx) {
      pageBreak(10);
      setFont('bold', 9); doc.setTextColor(...ACC); doc.setFillColor(...SOFT);
      let x = M;
      headers.forEach((h, i) => { doc.rect(x, y - 4, widths[i], 6, 'FD'); doc.text(String(h), x + 1.5, y); x += widths[i]; });
      y += 4; doc.setTextColor(...INK);
      rows.forEach((row, ri) => {
        setFont('normal', 9);
        if (ri === highlightIdx) { doc.setFillColor(252, 240, 233); doc.setTextColor(...ACC); }
        else { doc.setTextColor(...INK); }
        const cells = row.map((c, i) => doc.splitTextToSize(String(c == null ? '' : c), widths[i] - 3));
        const maxLines = cells.reduce((a, c) => Math.max(a, c.length), 1);
        const rowH = Math.max(6, maxLines * 4 + 2);
        pageBreak(rowH);
        x = M;
        cells.forEach((arr, i) => {
          doc.setDrawColor(...RULE);
          doc.rect(x, y - 4, widths[i], rowH, ri === highlightIdx ? 'FD' : 'D');
          arr.forEach((line, li) => doc.text(line, x + 1.5, y + li * 4));
          x += widths[i];
        });
        y += rowH - 2;
      });
      y += 2;
    }
    function drawCalloutBox(text, hex) {
      pageBreak(16);
      const lines = doc.splitTextToSize(text, PW - 2 * M - 6);
      const h = Math.max(10, lines.length * 4.6 + 4);
      doc.setFillColor(hex[0], hex[1], hex[2]); doc.rect(M, y - 4, PW - 2*M, h, 'F');
      doc.setDrawColor(...ACC); doc.setLineWidth(0.5);
      doc.line(M, y - 4, M, y - 4 + h);
      setFont('italic', 9.5); doc.setTextColor(...INK);
      lines.forEach((line, i) => doc.text(line, M + 3, y + i * 4.6));
      y += h;
    }

    // ─── Portada
    _drawHeader();
    drawTitle('Informe combinado · Lab de Políticas');
    setFont('normal', 11); doc.setTextColor(...INK2);
    doc.text(_esLong(), M, y); y += 7;
    setFont('normal', 10); doc.setTextColor(...INK);
    drawPara('Este documento integra el trabajo realizado en los 6 módulos del ' +
             'Lab de Políticas Públicas y Prospectiva (ricardoruiz.co). Es un ' +
             'borrador automatizado a partir del estado del navegador del ' +
             'usuario — debe ser revisado, editado y validado antes de ' +
             'presentarse ante comité técnico.');
    // Módulos activos
    const moduleLabels = {
      pp:'Problema público (Bardach · CEPAL)',
      micmac:'Análisis estructural (MicMac · DEMATEL · ISM)',
      mactor:'Mapa de actores (Mactor · Godet)',
      alt:'Alternativas de política (Zwicky · RDM)',
      ain:'Análisis de Impacto Normativo (OCDE RIA · DNP)',
      ev:'Plan de evaluación (OCDE-DAC · PAP)'
    };
    setFont('bold', 11); doc.setTextColor(...ACC); pageBreak(8);
    doc.text('Módulos integrados en este informe', M, y); y += 6;
    Object.keys(moduleLabels).forEach(k => {
      pageBreak(5);
      const isActive = !state[k].resumen.isEmpty;
      doc.setTextColor(...(isActive ? INK : INK2));
      setFont('normal', 10);
      doc.text(isActive ? '✓' : '○', M, y);
      doc.text(moduleLabels[k], M + 5, y);
      y += 5;
    });
    y += 2;

    // ─── Resumen ejecutivo
    drawH2('Resumen ejecutivo');
    drawPara(buildResumenEjecutivo(state));

    // ─── 1. Diagnóstico
    const pp = state.pp.resumen;
    drawH2('1. Diagnóstico del problema');
    if (pp.isEmpty) {
      drawCalloutBox('El módulo de Problema Público está vacío. Para una sección sustantiva, abrir problema-publico.html y completar el wizard.', SOFT);
    } else {
      drawPara(pp.enunciado);
      if (pp.magnitud || pp.urgencia) drawKV('Magnitud / Urgencia', `${pp.magnitud || '—'}  ·  ${pp.urgencia || '—'}`);
      if (pp.afectados.length) drawKV('Población afectada', pp.afectados.join('; '));
      if (pp.causas.length) { setFont('bold', 10); doc.text('Causas raíz:', M, y); y += 5; setFont('normal', 10); drawList(pp.causas); }
      if (pp.efectos.length) { setFont('bold', 10); doc.text('Efectos:', M, y); y += 5; setFont('normal', 10); drawList(pp.efectos); }
      if (pp.rittelTipo) drawKV('Diagnóstico de complejidad (Rittel-Webber)', `${pp.rittelTipo} — ${pp.rittelScore}/10 propiedades wicked`);
      if (pp.marco) drawKV('Marco analítico', pp.marco);
    }

    // ─── 2. Sistema
    const mc = state.micmac.resumen;
    drawH2('2. Variables motrices del sistema');
    if (mc.isEmpty) {
      drawCalloutBox('Análisis estructural sin matriz capturada. Abrir analisis-estructural.html para identificar las palancas del sistema (MicMac · DEMATEL).', SOFT);
    } else {
      drawPara(`Sistema con ${mc.nVars} variables analizadas.`);
      const rows = mc.topMotri.map((v, i) => [i+1, v.nombre, v.motri.toFixed(1), v.dep.toFixed(1), v.cuadrante]);
      drawTable(['#','Variable','Motri.','Dep.','Cuadrante'], rows, [10, 95, 22, 22, 25]);
      if (mc.claves.length) drawKV('Variables clave', mc.claves.map(v => v.nombre).join(', '));
    }

    // ─── 3. Actores
    const ma = state.mactor.resumen;
    drawH2('3. Mapa de actores y conflictos');
    if (ma.isEmpty) {
      drawCalloutBox('No hay actores capturados. Abrir mactor.html para mapear influencia / dependencia / posiciones sobre los objetivos.', SOFT);
    } else {
      drawPara(`${ma.nActores} actores y ${ma.nObjetivos} objetivos en disputa.`);
      setFont('bold', 10); doc.text('Actores dominantes (Ri = Ii / (Ii+Di))', M, y); y += 5;
      const rD = ma.topDom.map((a, i) => [i+1, a.nombre, a.I.toFixed(1), a.D.toFixed(1), a.R.toFixed(2)]);
      drawTable(['#','Actor','Influencia','Dependencia','Ri'], rD, [10, 100, 22, 22, 20]);
      if (ma.objetivos.length) {
        setFont('bold', 10); doc.text('Objetivos por saldo neto', M, y); y += 5;
        const rO = ma.objetivos.map((o, i) => [i+1, o.nombre, (o.saldo >= 0 ? '+' : '') + o.saldo.toFixed(1), o.mov.toFixed(1)]);
        drawTable(['#','Objetivo','Saldo','Movilización'], rO, [10, 110, 25, 29]);
      }
    }

    // ─── 4. Alternativas
    const al = state.alt.resumen;
    drawH2('4. Espacio de alternativas (análisis morfológico + RDM)');
    if (al.isEmpty) {
      drawCalloutBox('No hay alternativas capturadas. Abrir alternativas.html para recorrer el espacio morfológico con Zwicky y probar robustez en 4 escenarios.', SOFT);
    } else {
      drawPara(`${al.nVars} variables de decisión × ${al.nAlts} alternativas ensambladas.`);
      if (al.recomendada) {
        drawKV('Alternativa recomendada', al.recomendada.nombre + (al.recomendada.score ? ` (score ${al.recomendada.score.toFixed(2)})` : ''));
        if (al.recomendada.desc) drawPara(al.recomendada.desc, { color: INK2 });
        if (al.recomendada.supuestos) drawKV('Supuestos críticos', al.recomendada.supuestos);
        if (al.recomendada.riesgo) drawKV('Riesgo dominante', al.recomendada.riesgo);
        if (al.recomendada.costo) drawKV('Costo estimado', al.recomendada.costo);
        if (al.recomendada.plazo) drawKV('Plazo', al.recomendada.plazo);
      }
      if (al.econ) {
        setFont('bold', 10); doc.text('Lente económica', M, y); y += 5;
        if (al.econ.mvpf != null) drawKV('  MVPF (Hendren-Sprung-Keyser 2020)', al.econ.mvpf.toFixed(2) + (al.econ.mvpf > 1 ? ' (Pareto-superior)' : ''));
        if (al.econ.cea != null) drawKV('  CEA (J-PAL)', `${_fmtCOP(al.econ.cea)} por ${al.econ.unidad}`);
      }
      if (al.justificacion) drawKV('Justificación', al.justificacion);
    }

    // ─── 5. AIN (opcional)
    const ai = state.ain.resumen;
    drawH2('5. Análisis de Impacto Normativo');
    if (ai.isEmpty) {
      drawCalloutBox('No se contempló una salida regulatoria. Si la política requiere instrumento normativo, abrir ain.html para análisis RIA estilo OCDE / DNP.', SOFT);
    } else {
      if (ai.tipoFalla) drawKV('Tipo de falla regulatoria', ai.tipoFalla);
      if (ai.enunciado) drawPara(ai.enunciado);
      if (ai.afectados.length) drawKV('Audiencias afectadas', ai.afectados.join('; '));
      if (ai.recomendada) {
        drawKV('Opción regulatoria recomendada', ai.recomendada.nombre + ' (' + (AIN_OPT_TIPO[ai.recomendada.tipo] || ai.recomendada.tipo) + ')');
        if (ai.recomendada.desc) drawPara(ai.recomendada.desc, { color: INK2 });
      }
      if (ai.riesgos.length) {
        setFont('bold', 10); doc.text('Riesgos regulatorios', M, y); y += 5;
        drawList(ai.riesgos.map(r => `${r.dim}: ${r.nivel}`));
      }
      if (ai.justificacion) drawKV('Justificación', ai.justificacion);
    }

    // ─── 6. Evaluación
    const ev = state.ev.resumen;
    drawH2('6. Plan de evaluación');
    if (ev.isEmpty) {
      drawCalloutBox('No hay plan de evaluación. Abrir evaluacion.html para diseñar pregunta · teoría de cambio · método · MHT correction · PAP exportable.', SOFT);
    } else {
      drawPara(ev.enunciado);
      drawKV('Tipo · Alcance · Sinergia DNP', `${ev.tipo || '—'}  ·  ${ev.alcance || '—'}  ·  ${ev.tipoSinergia || '—'}`);
      if (ev.metodo) drawKV('Método principal', ev.metodo);
      if (ev.tratamientoEscalonado === 'si') drawCalloutBox('Tratamiento escalonado detectado — el plan usa Callaway-Sant\'Anna (2021) para evitar el sesgo TWFE (Goodman-Bacon 2021).', SOFT);
      if (ev.justificacion) drawKV('Justificación del método', ev.justificacion);
      drawKV('Indicadores SMART', `${ev.nIndicadores} registrados`);
      if (ev.indicadoresImpacto.length) drawKV('  Impacto', ev.indicadoresImpacto.map(i => i.nombre).join(', '));
      if (ev.indicadoresResultado.length) drawKV('  Resultados', ev.indicadoresResultado.map(i => i.nombre).join(', '));
      if (ev.eco) {
        setFont('bold', 10); doc.text('Análisis económico pre-registrado', M, y); y += 5;
        if (ev.eco.cba.vpn != null) drawKV('  CBA · VPN', `${_fmtCOP(ev.eco.cba.vpn)} (r=${(ev.eco.cba.r*100).toFixed(1)}% · h=${ev.eco.cba.h}a)${ev.eco.cba.ratio ? ' · B/C ' + ev.eco.cba.ratio.toFixed(2) : ''}`);
        if (ev.eco.mvpf.ratio != null) drawKV('  MVPF', ev.eco.mvpf.ratio.toFixed(2) + (ev.eco.mvpf.pareto ? ' (Pareto-superior)' : ''));
        if (ev.eco.cea.cea != null) drawKV('  CEA', `${_fmtCOP(ev.eco.cea.cea)} por ${ev.eco.cea.unidad}`);
      }
      if (ev.plan.cronograma) drawKV('Cronograma', ev.plan.cronograma);
      if (ev.plan.presupuesto) drawKV('Presupuesto', ev.plan.presupuesto);
    }

    // ─── 7. Próximos pasos
    drawH2('7. Próximos pasos operativos');
    const pasos = [];
    if (!pp.isEmpty && pp.evidencia.length < 3) pasos.push('Levantar evidencia adicional (mínimo 3 fuentes) para sostener el diagnóstico.');
    if (!ma.isEmpty && ma.objetivos.length && ma.objetivos[0].saldo < 0) pasos.push(`El saldo del objetivo principal es negativo (${ma.objetivos[0].nombre}) — diseñar estrategia de negociación con dominantes opositores.`);
    if (!al.isEmpty && !al.recomendada) pasos.push('Completar la matriz de robustez en los 4 escenarios para identificar la alternativa recomendada.');
    if (!ev.isEmpty && ev.nIndicadores < 4) pasos.push('Completar indicadores SMART mínimos (≥ 4) para la evaluación.');
    if (!ev.isEmpty && !ev.eco) pasos.push('Activar el módulo económico (CBA · MVPF · CEA) para defender la asignación presupuestal.');
    if (state.pp.exists && !state.ev.exists) pasos.push('Planificar la evaluación del problema definido — abrir evaluacion.html para diseñar el Pre-Analysis Plan.');
    if (pasos.length === 0) pasos.push('Validar el informe con los actores dominantes identificados y refinar antes de comité.');
    drawList(pasos);

    // ─── Footer metodológico
    pageBreak(28);
    doc.setDrawColor(...RULE); doc.setLineWidth(0.3); doc.line(M, y, PW - M, y); y += 5;
    setFont('italic', 8.5); doc.setTextColor(...INK2);
    const footer = 'Raíces metodológicas combinadas en este informe: Eightfold ' +
      'Path (Bardach 2020), prospectiva francesa (Godet · Mojica · LIPSOR), ' +
      'Robust Decision Making (Lempert-Walker RAND 2003), análisis morfológico ' +
      '(Zwicky 1969 · Ritchey 2011), OCDE RIA (2012/2022), MVPF ' +
      '(Hendren-Sprung-Keyser NBER 2020), OCDE-DAC (2019/2021), Pre-Analysis ' +
      'Plans (AEA RCT Registry · Olken 2015 JEP) y la frontera causal moderna ' +
      '2020-2026 (Callaway-Sant\'Anna · Cattaneo · Ben-Michael · Wager-Athey · ' +
      'Chernozhukov · Mayne). Este es un BORRADOR AUTOMATIZADO — debe ser ' +
      'revisado, editado y validado antes de comité técnico. ricardoruiz.co';
    const flines = doc.splitTextToSize(footer, PW - 2 * M);
    flines.forEach(l => { pageBreak(4.2); doc.text(l, M, y); y += 4.2; });

    _drawFooter();

    const filename = `informe-lab-${_ymd()}.pdf`;
    doc.save(filename);
    return filename;
  }

  // Exponer API
  window.LabInforme = {
    getLabState,
    countActiveModules,
    buildLabPDF,
    buildLabMarkdown,
    buildResumenEjecutivo,
    MODULE_LABELS: {
      pp: { titulo:'Problema público', icono:'1', archivo:'problema-publico.html' },
      micmac: { titulo:'Análisis estructural', icono:'2', archivo:'analisis-estructural.html' },
      mactor: { titulo:'Mapa de actores', icono:'3', archivo:'mactor.html' },
      alt: { titulo:'Alternativas de política', icono:'4', archivo:'alternativas.html' },
      ain: { titulo:'Análisis de Impacto Normativo', icono:'5', archivo:'ain.html' },
      ev: { titulo:'Plan de evaluación', icono:'6', archivo:'evaluacion.html' }
    }
  };

})();
