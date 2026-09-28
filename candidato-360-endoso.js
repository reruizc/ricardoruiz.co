/* ═══════════════════════════════════════════════════════════════════════════
   CANDIDATO 360 · ENDOSO DE ALIADOS · cálculo compartido
   ───────────────────────────────────────────────────────────────────────────
   El candidato suma líderes o excandidatos que lo van a apoyar y esto estima
   cuántos votos le pueden pasar. La tarjeta 08 del CRM y el panel propio
   (candidato-360-endoso.html) llaman ESTAS funciones: no pueden dar cifras
   distintas. Plan de trabajo en tools/candidato-360/endoso/PLAN.md.

   Reusa el método de endoso-2026.html: Σ min(aliado, apoyado) mesa por mesa
   sobre los votos del aliado.

   Tres reglas que NO hay que aflojar:
   1. Los votos del aliado se recortan al territorio de la campaña con la misma
      regla del mapa (código electoral, no nombre). Un concejal de Medellín que
      apoya a alguien al Concejo de Bogotá no le pasa ni un voto. El recorte lo
      decide quien llama (`enAlcance`): el motor no conoce el formulario.
   2. La tasa solo se MIDE si se dice a quién apoyó antes el aliado, y el par
      tiene que ser medible: mismo tarjetón = nadie pudo votar por los dos, y
      si el apoyado lo supera en casi todas las mesas, min(A, B) es siempre A
      y la cifra da ~100 % sin separar nada. En esos casos se dice y no se usa.
   3. Σ min es una COTA SUPERIOR: dice cuánto electorado pudieron compartir,
      no cuánto compartieron. Por eso todo se presenta como techo.

   Y el tiempo (fase 3): un aliado no le pasa a otro más de lo que conservaría
   de su propio voto si se lanzara él mismo. Eso se MIDE: la RETENCIÓN, cuánto
   de su votación conserva, puesto por puesto, la misma persona que repite en
   la misma corporación 4, 8 o 12 años después (tools/candidato-360/endoso/
   calibrar.mjs). Con sus cuartiles sale el rango de cada aliado:
     con par medido  →  min(tasa medida, retención)   en p25 · mediana · p75
     sin par         →  la retención sola             (reemplaza el 30 % fijo)
     tasa escrita    →  la que escribió el usuario, sin rango
   No se le suma el crecimiento del censo a 2027: la retención ya se midió con
   el electorado de cada año, y sumarlo lo contaría dos veces.

   Sin dependencias del CRM ni del DOM: se prueba en Node con
   tools/candidato-360/prueba-endoso.mjs.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';

  const SUPUESTO = .3, SATURACION = .95, MAX = 25;
  /* RETENCION:inicio */
  const RETENCION = {};
  /* RETENCION:fin */

  /* ── Identidad de una candidatura ─────────────────────────────────────── */
  const normalizar = v => String(v || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().replace(/[^A-Z0-9]/g, '');
  /* El año sale de `corp`; la única fuente sin año es endoso (Congreso 2026).
     Igual que candidateYear del CRM. */
  const AÑO_FUENTE = { endoso: 2026 };
  const anio = c => Number(String(c?.corp || '').match(/20\d{2}/)?.[0] || AÑO_FUENTE[c?.source] || 0);
  /* Qué candidatura es, sin el lugar: «CONCEJO · BOGOTÁ · 2023» → «CONCEJO». */
  const corp = c => normalizar(String(c?.corp || '').split('·')[0]);
  function clase(a, b) {
    const ya = anio(a), yb = anio(b);
    if (ya && yb && ya !== yb) return 'transferencia';
    if (corp(a) && corp(a) === corp(b)) return 'mismo';
    return 'cota';
  }
  /* Lo que se guarda de cada aliado y de a quién apoyó. */
  const ficha = (c, dataUrlFor) => ({ slug: c.slug, nombre: c.nombre, corp: c.corp || '', partido: c.partido || '', votos: Number(c.votos || 0), dataUrl: c.dataUrl || (dataUrlFor ? dataUrlFor(c.slug) : '') });

  /* ── La retención de un aliado ─────────────────────────────────────────
     La corporación sale del corp («CÁMARA · ANTIOQUIA · 2022» → camara) y la
     distancia, de su año hasta 2027, llevada a la más cercana medida (una
     candidatura de 2022 cae en la de 4 años). Con menos de 20 casos propios
     se usa la de todas las corporaciones juntas: presidencia y consultas no
     tienen personas que repitan, y la gobernación a 12 años tiene tres. */
  const AÑO_ELECCION = 2027, MIN_CASOS = 20;
  function corpRetencion(c) {
    const t = normalizar(String(c?.corp || '').split('·')[0]);
    if (/^JAL|ADMINISTRADORA/.test(t)) return 'jal';
    if (t.startsWith('CONCEJO')) return 'concejo';
    if (t.startsWith('ALCALD')) return 'alcaldia';
    if (t.startsWith('ASAMBLEA')) return 'asamblea';
    if (t.startsWith('GOBERN')) return 'gobernacion';
    if (t.startsWith('CAMARA')) return 'camara';
    if (t.startsWith('SENADO')) return 'senado';
    return '';
  }
  function cercana(tabla, g) {
    const ks = Object.keys(tabla || {}).map(Number).filter(k => (tabla[k]?.[3] || 0) >= MIN_CASOS);
    if (!ks.length) return null;
    return ks.sort((a, b) => Math.abs(a - g) - Math.abs(b - g) || a - b)[0];
  }
  function retencionDe(c) {
    const a = anio(c), g = a ? Math.max(1, AÑO_ELECCION - a) : 4, cp = corpRetencion(c);
    let k = cercana(RETENCION[cp], g), tabla = RETENCION[cp], propia = true;
    if (k == null) { k = cercana(RETENCION._todas, g); tabla = RETENCION._todas; propia = false; }
    if (k == null) return null;
    const [p25, p50, p75, n] = tabla[k];
    return { q: [p25, p50, p75], corp: propia ? cp : '', anos: g, medida: k, n, propia };
  }

  /* ── Mesas ───────────────────────────────────────────────────────────── */
  const cache = new Map();
  function mesas(url) {
    if (!url) return Promise.reject(new Error('Candidatura sin archivo de datos'));
    if (!cache.has(url)) cache.set(url, fetch(url).then(r => r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status))).then(d => d.mesas || []).catch(e => { cache.delete(url); throw e; }));
    return cache.get(url);
  }
  const suma = ms => ms.reduce((s, m) => s + Number(m.v || 0), 0);
  const llavePuesto = m => `${String(m.dep || '').padStart(2, '0')}|${String(m.mun || '').padStart(3, '0')}|${String(m.zon || '').padStart(2, '0')}|${String(m.pue || '').padStart(2, '0')}`;
  const llaveMesa = m => `${llavePuesto(m)}|${m.mesa ?? ''}`;
  function agrupar(ms, llave) { const o = {}; ms.forEach(m => { const k = llave(m); o[k] = (o[k] || 0) + Number(m.v || 0); }); return o; }

  /* ── El par aliado → a quién apoyó ─────────────────────────────────────
     Universo = los departamentos donde los dos tienen votos; unidad = mesa si
     es la misma jornada, puesto si son años distintos (las mesas se rearman
     con el censo). */
  async function medirPar(aliado, opts = {}) {
    const leer = opts.mesasDe || mesas;
    const cl = clase(aliado, aliado.apoyo);
    if (cl === 'mismo') return { clase: cl, valida: false, motivo: 'compitieron en el mismo tarjetón: nadie pudo votar por los dos, así que no hay endoso que medir' };
    const [ma, mb] = await Promise.all([leer(aliado.dataUrl), leer(aliado.apoyo.dataUrl)]);
    const llave = cl === 'transferencia' ? llavePuesto : llaveMesa;
    const A = agrupar(ma, llave), B = agrupar(mb, llave);
    const depsA = new Set(Object.keys(A).map(k => k.slice(0, 2))), depsB = new Set(Object.keys(B).map(k => k.slice(0, 2)));
    let sumA = 0, sumMin = 0, cubiertos = 0, comunes = 0;
    Object.entries(A).forEach(([k, a]) => {
      if (!a || !depsB.has(k.slice(0, 2))) return;
      const b = B[k] || 0; sumA += a; sumMin += Math.min(a, b);
      if (b > 0) comunes++;
      if (b >= a) cubiertos += a;
    });
    if (!sumA || ![...depsA].some(d => depsB.has(d))) return { clase: cl, valida: false, motivo: 'no compartieron territorio: no hay mesas donde los dos tengan votos' };
    const tasa = sumMin / sumA, saturado = cubiertos / sumA >= SATURACION;
    if (saturado) return { clase: cl, tasa, comunes, valida: false, motivo: `el apoyado le sacó más votos en casi todas sus ${cl === 'transferencia' ? 'puestos' : 'mesas'}, así que la coincidencia da ~${Math.round(tasa * 100)} % sin decir cuánto le pasó` };
    return { clase: cl, tasa, comunes, valida: true };
  }

  /* ── La lectura completa ───────────────────────────────────────────────
     opts:
       alcance    el territorio de la campaña (o null: sin recorte)
       lugar      cómo se nombra ese territorio en el texto
       enAlcance  (mesa, alcance) → bool; el recorte por código electoral
       areaDe     (mesa, alcance) → nombre del área donde se concentra
       propio     mesas del historial del candidato, para medir el solape
       mesasDe    url → Promise<mesas>; por defecto el fetch con caché */
  async function evaluar(aliados, opts = {}) {
    const { alcance = null, lugar = 'su territorio', enAlcance, areaDe, mesasDe = mesas } = opts;
    const propio = opts.propio ? agrupar(opts.propio, llavePuesto) : null;
    const filas = await Promise.all((aliados || []).map(async al => {
      try {
        const ms = await mesasDe(al.dataUrl), dentro = alcance && enAlcance ? ms.filter(m => enAlcance(m, alcance)) : ms;
        const fila = { al, total: suma(ms), terr: suma(dentro), dentro, par: null };
        if (al.apoyo) { try { fila.par = await medirPar(al, { mesasDe }); } catch (e) { fila.par = { valida: false, motivo: 'no se pudo leer la votación de a quién apoyó' }; } }
        if (propio && fila.terr) { const pa = agrupar(dentro, llavePuesto); let s = 0; Object.entries(pa).forEach(([k, v]) => { s += Math.min(v, propio[k] || 0); }); fila.solape = s / fila.terr; }
        return fila;
      } catch (e) { return { al, error: true }; }
    }));
    const medidas = filas.filter(f => f.par?.valida).map(f => f.par.tasa).sort((a, b) => a - b), nM = medidas.length;
    const mediana = !nM ? null : nM % 2 ? medidas[(nM - 1) / 2] : (medidas[nM / 2 - 1] + medidas[nM / 2]) / 2;
    let total = 0, bajo = 0, alto = 0, techo = 0; const porArea = {};
    filas.forEach(f => {
      if (f.error) return;
      f.ret = retencionDe(f.al);
      let r;
      if (Number.isFinite(f.al.manual)) { const t = f.al.manual / 100; r = [t, t, t]; f.fuente = 'suya'; }
      else if (f.par?.valida && f.ret) { r = f.ret.q.map(q => Math.min(f.par.tasa, q)); f.fuente = 'medida'; }
      else if (f.par?.valida) { r = [f.par.tasa, f.par.tasa, f.par.tasa]; f.fuente = 'medida'; }
      else if (f.ret) { r = f.ret.q.slice(); f.fuente = 'retencion'; }
      else { r = [SUPUESTO, SUPUESTO, SUPUESTO]; f.fuente = 'supuesto'; }
      [f.tasaBaja, f.tasa, f.tasaAlta] = r;
      f.estBajo = Math.round(f.terr * r[0]); f.est = Math.round(f.terr * r[1]); f.estAlto = Math.round(f.terr * r[2]);
      total += f.est; bajo += f.estBajo; alto += f.estAlto; techo += f.terr;
      if (areaDe) f.dentro.forEach(m => {
        const area = areaDe(m, alcance);
        if (area) porArea[area] = (porArea[area] || 0) + Number(m.v || 0) * f.tasa;
      });
    });
    const areas = Object.entries(porArea).map(([nombre, v]) => ({ nombre, v: Math.round(v) })).filter(a => a.v > 0).sort((a, b) => b.v - a.v);
    return { alcance, lugar, filas, total, bajo, alto, techo, mediana, nMedidas: nM, areas };
  }

  /* ── El territorio de la campaña ───────────────────────────────────────
     ⚠️ `enAlcance` es un PUERTO FIEL de mesaEnAlcance de candidato-360.js (el
     recorte del mapa). El CRM usa la suya y el panel esta: si una cambia sin
     la otra, la tarjeta y el panel dejan de dar la misma cifra y nada falla.
     prueba-endoso.mjs las compara sobre mesas reales. */
  const COM_NOM_NULO = new Set(['NACIONAL', 'NULL', 'SN', '']);
  const nombreLocal = m => { const n = String(m.comNom || '').trim(); return COM_NOM_NULO.has(n.toUpperCase()) ? '' : n; };
  const nombreLocalidad = raw => String(raw || '').replace(/^\d{2}(?=\S)/, '').replace(/\s+/g, ' ').trim().replace(/^LOCALIDAD\s*\d+\s+/i, '');
  const cortoLocal = raw => nombreLocalidad(raw).replace(/^(COMUNA|COM|CORREGIMIENTO|CORREG\.?|CORRE\.?)\s*\d*\s*/i, '').trim();
  function enAlcance(mesa, alcance) {
    const dep = String(mesa.dep || '').replace(/^0+/, ''), mun = String(mesa.mun || '').replace(/^0+/, '');
    if (alcance.departamento && dep && dep !== alcance.departamento) return false;
    if (alcance.tipo === 'departamento') return alcance.departamento ? Boolean(dep) : normalizar(mesa.depNom || '') === alcance.departamentoNombre;
    const enMunicipio = alcance.municipio ? mun === alcance.municipio : normalizar(mesa.munNom || '') === alcance.municipioNombre;
    if (alcance.tipo !== 'localidad') return enMunicipio;
    if (!enMunicipio) return false;
    const suya = normalizar(cortoLocal(nombreLocal(mesa))), objetivo = normalizar(cortoLocal(alcance.localidad));
    return Boolean(suya) && Boolean(objetivo) && suya === objetivo;
  }
  /* Dónde se concentra, sin maquillar: municipios en una campaña
     departamental, puestos en una JAL, localidades o comunas en lo municipal.
     El nombre bonito lo pone quien pinta. */
  function areaDe(m, alcance) {
    if (alcance?.tipo === 'departamento') return m.munNom || '';
    if (alcance?.tipo === 'localidad') return m.pueNom || '';
    return cortoLocal(nombreLocal(m)) || m.pueNom || '';
  }
  const DEPARTAMENTAL = ['asamblea', 'gobernacion'];
  function corpHistorica(c) {
    const first = String(c?.corp || '').split('·')[0].trim().toLowerCase();
    if (first.includes('jal') || first.includes('administradora')) return 'jal';
    if (first.includes('concejo')) return 'concejo';
    if (first.includes('alcald')) return 'alcaldia';
    if (first.includes('asamblea')) return 'asamblea';
    if (first.includes('gobern')) return 'gobernacion';
    return '';
  }
  function municipioMayoritario(ms) {
    const votos = {};
    (ms || []).forEach(m => { const k = `${String(m.dep || '').padStart(2, '0')}${String(m.mun || '').padStart(3, '0')}`; if (k !== '00000') votos[k] = (votos[k] || 0) + Number(m.v || 0); });
    return Object.entries(votos).sort((a, b) => b[1] - a[1])[0]?.[0] || '';
  }
  /* El territorio contra el que se recorta, desde lo que guardó la campaña.
     Con territorio propio (otra corporación, candidatura nueva) manda ese —y
     el municipio va por CÓDIGO ELECTORAL, que `codigoMunicipio` traduce del
     nombre: el formulario escribe «Cartagena de Indias» y la Registraduría
     «CARTAGENA»—. En «la misma corporación» es el de su última candidatura,
     donde está la mayoría de su voto. `nombre` es solo para mostrar. */
  async function alcanceDe({ campana = {}, corpHistorica: corpHist = '', mesasPropias = null, codigoMunicipio = null } = {}) {
    const c = campana || {};
    const dep = String(c.departamento || '').replace(/^0+/, ''), corp = c.corp || corpHist || '';
    if (c.ruta !== 'same' && dep && corp) {
      if (DEPARTAMENTAL.includes(corp)) return { tipo: 'departamento', departamento: dep, nombre: c.departamentoNombre || '' };
      if (!c.municipio) return { tipo: 'departamento', departamento: dep, nombre: c.departamentoNombre || '' };
      let mun = '';
      if (codigoMunicipio) { try { mun = String(await codigoMunicipio(dep, c.municipio) || '').replace(/^0+/, ''); } catch { mun = ''; } }
      const base = { departamento: dep, municipio: mun, municipioNombre: normalizar(c.municipio) };
      if (corp === 'jal' && c.localidad) return { tipo: 'localidad', ...base, localidad: c.localidad, nombre: cortoLocal(c.localidad) };
      return { tipo: 'municipio', ...base, nombre: c.municipio };
    }
    const mm = municipioMayoritario(mesasPropias); if (!mm) return null;
    const depM = String(Number(mm.slice(0, 2))), mun = String(Number(mm.slice(2)));
    const deAqui = (mesasPropias || []).filter(m => `${String(m.dep || '').padStart(2, '0')}${String(m.mun || '').padStart(3, '0')}` === mm);
    if (DEPARTAMENTAL.includes(corp)) return { tipo: 'departamento', departamento: depM, nombre: deAqui[0]?.depNom || '' };
    if (corp === 'jal') {
      const porLocal = {}; (mesasPropias || []).forEach(m => { const n = nombreLocal(m); if (n) porLocal[n] = (porLocal[n] || 0) + Number(m.v || 0); });
      const loc = Object.entries(porLocal).sort((x, y) => y[1] - x[1])[0]?.[0];
      if (loc) return { tipo: 'localidad', departamento: depM, municipio: mun, localidad: loc, nombre: cortoLocal(loc) };
    }
    return { tipo: 'municipio', departamento: depM, municipio: mun, nombre: deAqui[0]?.munNom || '' };
  }

  /* ── El endoso por puesto ──────────────────────────────────────────────
     Reparte lo estimado de cada aliado en los puestos donde tiene sus votos
     (votos del puesto × su tasa). Para el mapa y el desglose; la suma por
     aliado puede diferir en ±1 del estimado por el redondeo. El código es el
     de la hoja de vida del puesto: la letra de los dos últimos caracteres se
     conserva (187 puestos del país la llevan). */
  const pad = (v, n) => String(v || '').replace(/\D/g, '').padStart(n, '0');
  const codigoPuesto = m => pad(m.dep, 2) + pad(m.mun, 3) + pad(m.zon, 2) + String(m.pue == null ? '' : m.pue).trim().toUpperCase().padStart(2, '0');
  function porPuesto(lectura) {
    const o = new Map();
    (lectura?.filas || []).forEach((f, i) => {
      if (f.error || !f.tasa) return;
      f.dentro.forEach(m => {
        const k = codigoPuesto(m), v = Number(m.v || 0) * f.tasa; if (!v) return;
        if (!o.has(k)) o.set(k, { code: k, nombre: m.pueNom || '', munNom: m.munNom || '', comNom: nombreLocal(m), total: 0, votos: 0, porAliado: {} });
        const p = o.get(k); p.total += v; p.votos += Number(m.v || 0); p.porAliado[i] = (p.porAliado[i] || 0) + v;
      });
    });
    return [...o.values()].sort((a, b) => b.total - a.total);
  }

  /* ── Lista de aliados ──────────────────────────────────────────────────
     Vive en el navegador, por cuenta y candidatura: no cambia el vínculo, y
     el nombre de un líder de zona es un dato de un tercero que no tenemos
     por qué custodiar. */
  const clave = (correo, candidatura) => `c360-aliados:${String(correo || 'anon').toLowerCase()}:${candidatura || 'sin-candidatura'}`;
  /* La misma candidatura que usa el CRM (crmCandidate.id o «nuevo-NOMBRE»):
     así la tarjeta y el panel leen la misma lista. */
  const candidaturaId = v => v?.tipo === 'nuevo' ? `nuevo-${normalizar(v.nuevo?.nombre || '')}` : (v?.candidato?.id || '');
  function cargar(k) { try { return JSON.parse(global.localStorage.getItem(k) || '[]').slice(0, MAX); } catch { return []; } }
  function guardar(k, lista) { try { global.localStorage.setItem(k, JSON.stringify(lista)); } catch { /* sin almacenamiento: la lista vive mientras dure la pestaña */ } }

  const FUENTE = {
    medida: 'medida con a quién apoyó',
    suya: 'tasa que usted escribió',
    retencion: 'lo que conserva de su propio voto: diga a quién apoyó para medirla',
    supuesto: 'supuesto: escriba el suyo o mida el par',
  };
  const CLASE = {
    cota: 'misma jornada, tarjetón distinto: cota superior',
    transferencia: 'elecciones distintas: transferencia entre fechas, comparada por puesto',
  };

  global.C360Endoso = { SUPUESTO, SATURACION, MAX, FUENTE, CLASE, anio, corp, clase, ficha, mesas, suma, llavePuesto, llaveMesa, agrupar, medirPar, evaluar, retencionDe, corpRetencion, RETENCION,
    enAlcance, areaDe, corpHistorica, municipioMayoritario, alcanceDe, codigoPuesto, porPuesto, clave, candidaturaId, cargar, guardar };
})(typeof window !== 'undefined' ? window : globalThis);
