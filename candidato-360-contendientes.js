/* ═══════════════════════════════════════════════════════════════════════════
   CANDIDATO 360 · MONITOREO DE CONTENDIENTES · cálculo compartido
   ───────────────────────────────────────────────────────────────────────────
   Contra quién compite una candidatura, de qué familia política es cada rival,
   cuánto rinde cada uno en la base de la candidatura (el plano), dónde se van
   a pelear el voto (el mapa de disputa) y quién le compite dentro de su propia
   lista (la escalera). La tarjeta 10 del CRM y el panel propio
   (candidato-360-contendientes.html) llaman ESTAS funciones: no pueden dar
   cifras distintas. Plan en tools/candidato-360/contendientes/PLAN.md.

   Dos capas, a propósito separadas:
   · `cargar` hace la IO: el reparto de 2023 (VoteTarget.reparto), la matriz
     de votos por candidato y puesto (C360DiaD.puestosDestino) o, donde no la
     hay, el archivo de cada rival, y los rivales de otras elecciones.
   · `evaluar` es cálculo puro sobre lo cargado: se prueba en Node con datos
     sintéticos y con los reales (tools/candidato-360/prueba-contendientes.mjs).

   Reglas que NO hay que aflojar:
   1. Todo son rivales PROBABLES hasta la inscripción de 2027. Las fuentes se
      dicen (A ganó la curul en 2023 · B compitió aquí en 2023 · C tiene votos
      aquí de otra elección) y nada de prensa entra por este motor.
   2. La familia es la del PARTIDO, no la de la persona. Aval amplio o sin
      línea nacional va a «no sabemos», nunca al centro.
   3. La afinidad describe PUESTOS: cuánto rinde el rival donde usted saca
      votos, frente a su promedio. No dice quién votó por quién.
   4. El índice es una heurística declarada y se publica en tres niveles, no
      como número (PLAN §6).
   ═══════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';

  /* ── Constantes del método (PLAN §3, §4, §6; decisiones P7 y P10) ─────── */
  const ORDEN = { izq: -2, ci: -1, c: 0, cd: 1, d: 2 };
  const CERCANIA_PASOS = [1, .6, .25, .1, .05];
  const CERCANIA_NO_SABEMOS = .4;
  const CERCANO = .6;                      /* su columna y las vecinas: los rivales «cercanos» del mapa */
  const MISMO_TERRENO = [.85, 1.15];
  const AFINIDAD_TOPE = 2;
  const UMBRAL_LISTA = .5;                 /* P7: ≥ 50 % del último elegido de su lista */
  const UMBRAL_UNINOMINAL = .2;            /* alcaldía y gobernación: ≥ 20 % del ganador */
  const MIN_VALIDOS_PUESTO = 200, MIN_VOTOS_BASE = 5;
  const MIN_BASE = { votos: 30, puestos: 3 };
  const TOP_PLANO = 12, VITRINA = 3;
  const MAX_OTRAS = 6;                     /* personas NUEVAS de otras elecciones cuyo archivo se baja (las demás entran sin votos por puesto) */
  const MAX_OTRAS_JAL = 20;                /* los archivos de JAL son chicos: se bajan más */
  const AVISO_PAREJO = .8;
  const UNINOMINALES = ['alcaldia', 'gobernacion'], UNINOMINAL_SLUG = /^(ALC|GOB)\d{4}-/;
  /* 'sin-datos-electorales': dicho en prensa o agregado a mano sin candidatura
     en el registro. Está en la lista, no tiene con qué medirse. */
  const FUERA_DEL_INDICE = new Set(['titular-no-reelegible', 'congresista-2026', 'voto-uninominal', 'en-ejercicio', 'sin-datos-electorales']);                 /* ≥ 80 % de los rivales en la franja → territorio parejo */

  const S3_FALLBACK = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output';
  const S3 = (global.RRData && typeof global.RRData.publicUrl === 'function') ? global.RRData.publicUrl('congreso-2026/output') : S3_FALLBACK;

  const pad = (v, n) => String(v ?? '').replace(/\D/g, '').padStart(n, '0');
  const norm = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().replace(/[^A-Z0-9]+/g, ' ').trim();
  /* Compacta, sin espacios ni signos: el crudo de la Registraduría trae
     caracteres rotos en unos pocos nombres («ZUÐIGA», «D´ACUNTI») que el índice
     escribe limpios («ZUIGA», «DACUNTI»). Con la llave compacta casan igual. */
  const compacto = s => norm(s).replace(/[^A-Z0-9]/g, '');
  const llaveCand = (nombre, partido) => `${compacto(nombre)}|${compacto(partido)}`;
  const mediana = xs => { const s = xs.filter(Number.isFinite).sort((a, b) => a - b); if (!s.length) return null; const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
  const anio = c => Number(String(c?.corp || '').match(/20\d{2}/)?.[0] || (c?.source === 'endoso' ? 2026 : 0));
  /* Mismo código de puesto que el endoso y el Día D (la letra final se conserva). */
  const codigoPuesto = m => pad(m.dep, 2) + pad(m.mun, 3) + pad(m.zon, 2) + String(m.pue == null ? '' : m.pue).trim().toUpperCase().padStart(2, '0');

  /* ── Familia política ─────────────────────────────────────────────────── */
  function familia(partido, nombre) {
    const PB = global.PartidosBloques;
    if (!PB) return { bloque: 'sc', amplio: false, sabemos: false };
    const bloque = PB.bloqueDeCandidatura(partido || '', nombre || '');
    const amplio = PB.esAvalAmplio(partido || '');
    return { bloque, amplio, sabemos: bloque in ORDEN && !amplio };
  }
  /* La de la campaña: el aval elegido, o el espectro si va por firmas o sin
     decidir. Mismo criterio que el Día D (familiaDe). */
  function familiaCampana(campana = {}) {
    const PB = global.PartidosBloques;
    if (campana.avales === 'firmas' || campana.avales === 'indeciso') return ORDEN[campana.espectro] !== undefined ? campana.espectro : '';
    if (!campana.partido || !PB) return '';
    const f = PB.bloqueDeOrganizacion(campana.partido);
    return f in ORDEN && !PB.esAvalAmplio(campana.partido) ? f : '';
  }
  function pasos(fu, fr) { return fu in ORDEN && fr in ORDEN ? Math.abs(ORDEN[fu] - ORDEN[fr]) : null; }
  function cercania(fu, famR) {
    const p = famR && famR.sabemos ? pasos(fu, famR.bloque) : null;
    return p == null ? CERCANIA_NO_SABEMOS : CERCANIA_PASOS[p];
  }

  /* «partido-candidato» desde el slug del índice: CONC/ALC traen
     dep-mun-par-can; GOB/ASAM, dep-par-can. Es la llave de la matriz nacional. */
  function codigoDeSlug(slug) {
    const p = String(slug || '').split('-');
    if (/^(CONC|ALC)\d{4}$/.test(p[0]) && p.length >= 5) return `${p[3]}-${p[4]}`;
    if (/^(GOB|ASAM)\d{4}$/.test(p[0]) && p.length >= 4) return `${p[p.length - 2]}-${p[p.length - 1]}`;
    return '';
  }
  /* El archivo de la matriz nacional donde está una candidatura (D1). */
  const DIR_SLUG = { CONC: 'concejo', ALC: 'alcaldia', GOB: 'gobernacion', ASAM: 'asamblea' };
  function matrizDeSlug(slug) {
    const p = String(slug || '').split('-'), m = p[0].match(/^(CONC|ALC|GOB|ASAM)(\d{4})$/);
    if (!m) return '';
    const dir = `${DIR_SLUG[m[1]]}-${m[2]}`;
    return m[1] === 'GOB' || m[1] === 'ASAM' ? `${dir}/${pad(p[1], 2)}.json` : `${dir}/${pad(p[1], 2)}-${pad(p[2], 3)}.json`;
  }

  /* ── Persona ───────────────────────────────────────────────────────────
     Puerto de fourNameKey/candidateProfile del CRM: tres o cuatro componentes
     del nombre (con ALIAS_PERSONA). Acá todas las candidaturas son del mismo
     territorio, así que la condición de «un solo departamento» se cumple sola.
     Nombres de dos o de cinco componentes no se funden: cada candidatura queda
     sola, como en el CRM. */
  function llavePersona(c) {
    const R = global.CandRegistry;
    const k = R ? R.personaKey(c?.nombre) : norm(c?.nombre);
    const n = k.split(/\s+/).filter(Boolean).length;
    return n === 3 || n === 4 ? k : `slug:${c?.slug || norm(c?.nombre)}`;
  }
  /* «Hoy es congresista»: el nombre corto del electo (≥ 3 componentes) cabe
     entero en el del candidato. Medido sobre Bogotá 2023 sin falsos positivos
     en los 120 más votados (PLAN H10). */
  function esCongresista(nombre, congresistas) {
    const t = new Set(norm(nombre).split(' '));
    return (congresistas || []).some(e => { const s = norm(e).split(' ').filter(Boolean); return s.length >= 3 && s.every(w => t.has(w)); });
  }

  /* ── Los datos por puesto ──────────────────────────────────────────────
     Forma común, venga de la matriz por comuna/municipio o de los archivos de
     cada candidatura:
       { validos: Map(code → válidos), info: Map(code → {nombre, barrio, unidad, lat, lon}),
         porCand: Map(llaveCand → {nombre, partido, porPuesto: Map, total}),
         listas:  Map(partido → Map(code → votos solo por la lista)),
         origen: 'matriz' | 'archivos' } */
  function matrizDesdeArchivos(archivos) {
    const validos = new Map(), info = new Map(), porCand = new Map(), listas = new Map(), porCod = new Map();
    (archivos || []).forEach(({ d, mun, nombre }) => {
      if (!d) return;
      const dep2 = pad(d.dde, 2);
      const partidos = (d.partidos || []).map(p => p[0]);
      (d.puestos || []).forEach(pu => {
        const [zon, pue] = String(pu.code || '').split('-');
        if (!zon || !pue || ['90', '98'].includes(zon)) return;
        /* En la matriz nacional de gobernación y asamblea el archivo es del
           departamento y cada puesto trae su municipio. */
        const mun3 = pad(pu.mme || d.mme || mun, 3);
        const code = dep2 + mun3 + pad(zon, 2) + String(pue).trim().toUpperCase().padStart(2, '0');
        validos.set(code, (validos.get(code) || 0) + Number(pu.validos || 0));
        /* `com` es el código de la comuna o localidad del archivo (en Cartagena,
           la UCG); `mun`, el municipio: con eso el mapa agrupa sin el georef. */
        if (!info.has(code)) info.set(code, { nombre: pu.nombre || '', barrio: pu.barrio || '', unidad: nombre || d.name || '', lat: pu.lat, lon: pu.lon, com: d.comuna != null ? String(d.comuna) : '', mun: mun3 });
        (pu.v || []).forEach(([i, v]) => {
          const c = (d.cands || [])[i]; if (!c || !v) return;
          const k = llaveCand(c[0], partidos[c[1]]);
          if (!porCand.has(k)) porCand.set(k, { nombre: c[0], partido: partidos[c[1]] || '', porPuesto: new Map(), total: 0 });
          const x = porCand.get(k); x.porPuesto.set(code, (x.porPuesto.get(code) || 0) + v); x.total += v;
          /* La matriz nacional trae el código «partido-candidato» del slug: se
             casa por ahí antes que por nombre (el crudo repite códigos con
             nombres distintos). Los archivos por comuna no lo traen. */
          if (c[2] && !porCod.has(c[2])) porCod.set(c[2], x);
        });
        /* `l` apunta a `partidos`, no a `listas` (medido: el índice 4 son los
           8.060 votos del Pacto en Barrios Unidos). */
        (pu.l || []).forEach(([i, v]) => {
          const par = partidos[i]; if (!par || !v) return;
          if (!listas.has(par)) listas.set(par, new Map());
          const m = listas.get(par); m.set(code, (m.get(code) || 0) + v);
        });
      });
    });
    return { validos, info, porCand, listas, porCod, origen: 'matriz' };
  }
  /* Sin matriz (alcaldía, gobernación, concejo fuera de las 11 ciudades): los
     votos de cada rival salen de su archivo, recortados al territorio, y los
     válidos de totales-puesto. Sin voto de lista: se declara. */
  function matrizDesdeMesas(candidatos, totalesPuesto, dentro) {
    const validos = new Map(), info = new Map(), porCand = new Map();
    (candidatos || []).forEach(({ entrada, mesas }) => {
      const k = llaveCand(entrada.nombre, entrada.partido);
      const x = { nombre: entrada.nombre, partido: entrada.partido || '', porPuesto: new Map(), total: 0 };
      (mesas || []).forEach(m => {
        if (dentro && !dentro(m)) return;
        const v = Number(m.v || 0); if (!v || ['90', '98'].includes(pad(m.zon, 2))) return;
        const code = codigoPuesto(m);
        x.porPuesto.set(code, (x.porPuesto.get(code) || 0) + v); x.total += v;
        if (!info.has(code)) info.set(code, { nombre: m.pueNom || '', barrio: '', unidad: m.comNom || m.munNom || '', lat: null, lon: null });
      });
      porCand.set(k, x);
    });
    info.forEach((_, code) => { const t = totalesPuesto?.[code]; if (t && t[0]) validos.set(code, Number(t[0])); });
    return { validos, info, porCand, listas: new Map(), origen: 'archivos' };
  }

  /* La base: votos por puesto (solo puestos con válidos en el territorio). */
  function baseDesdeMesas(mesas, datos, dentro) {
    const porPuesto = new Map(); let total = 0, fuera = 0;
    (mesas || []).forEach(m => {
      if (dentro && !dentro(m)) return;
      const v = Number(m.v || 0); if (!v) return;
      const code = codigoPuesto(m);
      if (!datos.validos.get(code)) { fuera += v; return; }
      porPuesto.set(code, (porPuesto.get(code) || 0) + v); total += v;
    });
    return { porPuesto, total, fuera, puestos: porPuesto.size };
  }
  const baseSuficiente = b => b && b.total >= MIN_BASE.votos && b.puestos >= MIN_BASE.puestos;

  /* ── Afinidad territorial (PLAN §3.2) ──────────────────────────────────
     Σ_p s_U(p) · (v_R(p)/válidos(p))  ÷  (V_R / VÁLIDOS del territorio).
     1 = el rival rinde en la base igual que en todo el territorio. */
  function totalValidos(datos) { let s = 0; datos.validos.forEach(v => { s += v; }); return s; }
  function afinidad(base, porPuesto, total, datos, VAL = totalValidos(datos)) {
    if (!base || !base.total || !total || !VAL || !porPuesto) return null;
    let num = 0;
    base.porPuesto.forEach((vu, code) => { const val = datos.validos.get(code); if (val) num += (vu / base.total) * ((porPuesto.get(code) || 0) / val); });
    return num / (total / VAL);
  }
  /* Secundaria, para la ficha: correlación ponderada de la fuerza relativa
     entre puestos. En la JAL separa más que la afinidad, pero con ~30 puestos
     es ruidosa (PLAN §3.2). */
  function correlacion(base, porPuesto, datos) {
    if (!base || !porPuesto) return null;
    const xs = [], ys = [], ws = [];
    datos.validos.forEach((val, code) => { if (!val) return; xs.push((base.porPuesto.get(code) || 0) / val); ys.push((porPuesto.get(code) || 0) / val); ws.push(val); });
    const W = ws.reduce((a, b) => a + b, 0); if (!W || xs.length < 3) return null;
    const mx = xs.reduce((a, x, i) => a + x * ws[i], 0) / W, my = ys.reduce((a, y, i) => a + y * ws[i], 0) / W;
    let sxy = 0, sxx = 0, syy = 0;
    xs.forEach((x, i) => { sxy += ws[i] * (x - mx) * (ys[i] - my); sxx += ws[i] * (x - mx) ** 2; syy += ws[i] * (ys[i] - my) ** 2; });
    return sxx > 0 && syy > 0 ? sxy / Math.sqrt(sxx * syy) : null;
  }
  const franja = a => a == null ? 'sin-dato' : a >= MISMO_TERRENO[1] ? 'alta' : a >= MISMO_TERRENO[0] ? 'mismo-terreno' : 'baja';

  /* ── Presión competitiva (PLAN §6) ─────────────────────────────────────
     cercanía × min(2, afinidad)/2 × votos/(votos + meta). La forma del tamaño
     no se satura (con min(1, votos/meta) todos los concejales pasaban la meta
     de una edilesa y el índice quedaba en cercanía × afinidad). */
  function presion({ cercania: cer, afinidad: af, votos, meta }) {
    /* Sin afinidad medida, la neutra (1), no el tope: hasta la fase 4 este
       caso valía como afinidad 2 y los rivales sin archivo encabezaban el plano. */
    const a = Math.min(AFINIDAD_TOPE, af == null ? 1 : af) / AFINIDAD_TOPE;
    const t = votos > 0 ? votos / (votos + Math.max(1, Number(meta) || 0)) : 0;
    return cer * a * t;
  }
  /* Tres niveles por terciles dentro del territorio: el número no se publica. */
  function niveles(rivales) {
    const en = rivales.filter(r => r.enIndice).sort((a, b) => b.presion - a.presion);
    const n = en.length, c1 = Math.ceil(n / 3), c2 = Math.ceil(2 * n / 3);
    en.forEach((r, i) => { r.nivel = i < c1 ? 'alta' : i < c2 ? 'media' : 'baja'; });
    rivales.filter(r => !r.enIndice).forEach(r => { r.nivel = null; });
  }

  /* ── Mapa de disputa (PLAN §4) ─────────────────────────────────────────
     Por puesto: i_U = su fuerza relativa, i_R = la de su familia y las vecinas
     (votos personales + votos de lista de sus partidos). Cuatro categorías y
     dos de «no se puede leer». La segunda capa (todo el territorio) es solo i_R. */
  /* La regla de las cuatro categorías, la misma para un puesto que para un
     barrio o una comuna (sumando sus puestos): así un puesto chico no decide
     solo, y el mapa agregado dice lo mismo que la suma de sus partes. */
  function categoria({ b, r, val }, { B, RT, VAL }, umbral = true) {
    const iR = RT ? (r / val) / (RT / VAL) : null;
    const iU = B ? (b / val) / (B / VAL) : null;
    let cat;
    if (umbral && val < MIN_VALIDOS_PUESTO) cat = 'poco';
    else if (!b) cat = 'sin-base';
    else if (umbral && b < MIN_VOTOS_BASE) cat = 'poco';
    else if (iR == null) cat = iU >= 1 ? 'fortaleza' : 'terreno-ajeno';
    else cat = iU >= 1 ? (iR >= 1 ? 'disputa' : 'fortaleza') : (iR >= 1 ? 'terreno-rivales' : 'terreno-ajeno');
    return { cat, iU, iR };
  }
  /* La segunda capa (todo el territorio): dónde rinden sus rivales cercanos,
     sin su base. Tres bandas con la misma franja del plano. */
  const bandaRivales = iR => iR == null ? 'sin-dato' : iR >= MISMO_TERRENO[1] ? 'fuerte' : iR >= MISMO_TERRENO[0] ? 'parejo' : 'flojo';
  function disputa(base, datos, cercanos, opts = {}) {
    const umbral = opts.umbral !== false;
    const VAL = totalValidos(datos);
    const R = new Map(); let RT = 0;
    cercanos.forEach(pp => pp.forEach((v, code) => { if (datos.validos.get(code)) { R.set(code, (R.get(code) || 0) + v); RT += v; } }));
    const conteo = { fortaleza: 0, disputa: 0, 'terreno-rivales': 0, 'terreno-ajeno': 0, 'sin-base': 0, poco: 0 };
    const puestos = [], tot = { B: base?.total || 0, RT, VAL };
    datos.validos.forEach((val, code) => {
      const b = base?.porPuesto.get(code) || 0, r = R.get(code) || 0;
      const c = categoria({ b, r, val }, tot, umbral);
      conteo[c.cat]++;
      puestos.push({ code, ...c, banda: bandaRivales(c.iR), votos: b, rivales: r, validos: val, ...(datos.info.get(code) || {}) });
    });
    /* La segunda capa solo tiene sentido si la base cubre una parte chica del
       territorio (el salto de JAL a Concejo: 31 de 943 puestos). */
    const cobertura = datos.validos.size ? (base?.puestos || 0) / datos.validos.size : 0;
    return { puestos, conteo, cobertura, dosCapas: cobertura < .5, rivalesVotos: RT, totales: tot, umbral };
  }
  /* El mismo mapa por barrio, comuna o municipio: se suman los puestos de cada
     unidad y se clasifica la suma con la misma regla. `claveDe(puesto)` dice a
     qué unidad va cada puesto (o '' si a ninguna: no se inventa). */
  function disputaPorUnidad(mapa, claveDe, nombreDe = k => k) {
    if (!mapa) return { unidades: [], conteo: {}, fuera: 0 };
    const acc = new Map(); let fuera = 0;
    mapa.puestos.forEach(p => {
      const k = claveDe(p); if (!k) { fuera += p.votos; return; }
      if (!acc.has(k)) acc.set(k, { key: k, name: nombreDe(k, p), b: 0, r: 0, val: 0, puestos: 0, codes: [] });
      const a = acc.get(k); a.b += p.votos; a.r += p.rivales; a.val += p.validos; a.puestos++; a.codes.push(p.code);
    });
    const conteo = { fortaleza: 0, disputa: 0, 'terreno-rivales': 0, 'terreno-ajeno': 0, 'sin-base': 0, poco: 0 };
    const unidades = [...acc.values()].map(a => { const c = categoria(a, mapa.totales, mapa.umbral); conteo[c.cat]++; return { ...a, ...c, banda: bandaRivales(c.iR), votos: a.b, rivales: a.r, validos: a.val }; });
    return { unidades, conteo, fuera };
  }

  /* ── Barrios sin puesto propio: el color del vecino más cercano ─────────
     Mismo criterio de la página del electorado y de los tableros de 2023:
     el barrio con dato más cercano por centroide, a menos de 3 km; más lejos
     queda sin dato. Nunca entra a un total ni a una lista. */
  const RELLENO_MAX_KM = 3;
  function centroide(g) {
    const anillos = g?.type === 'Polygon' ? [g.coordinates[0]] : g?.type === 'MultiPolygon' ? g.coordinates.map(pg => pg[0]) : [];
    let x = 0, y = 0, n = 0;
    anillos.forEach(r => r.forEach(([lon, lat]) => { x += lon; y += lat; n++; }));
    return n ? [x / n, y / n] : null;
  }
  function rellenos(features, codeDe, nameDe, conDato, maxKm = RELLENO_MAX_KM) {
    const con = [], sin = [];
    (features || []).forEach(f => { const c = centroide(f.geometry), code = codeDe(f.properties); if (!c) return; (conDato.has(code) ? con : sin).push({ code, c, name: nameDe(f.properties) }); });
    const out = new Map();
    sin.forEach(b => {
      let mejor = null, d2 = Infinity;
      con.forEach(o => { const dx = (o.c[0] - b.c[0]) * Math.cos(b.c[1] * Math.PI / 180), dy = o.c[1] - b.c[1], d = dx * dx + dy * dy; if (d < d2) { d2 = d; mejor = o; } });
      const km = Math.sqrt(d2) * 111.32;
      if (mejor && km <= maxKm) out.set(b.code, { de: mejor.code, nombre: mejor.name, km });
    });
    return out;
  }

  /* ── Las fuentes A y B del reparto de 2023 ─────────────────────────────── */
  function fuentesDelReparto(rep) {
    const out = new Map(); if (!rep) return { porSlug: out, referencia: null };
    if (rep.uninominal) {
      const g = rep.ganador, gv = Number(g?.votos || 0);
      rep.rows.forEach(r => {
        const f = [];
        if (g && r.slug === g.slug) f.push('A');
        else if (gv && Number(r.votos || 0) >= UMBRAL_UNINOMINAL * gv) f.push('B');
        if (f.length) out.set(r.slug, f);
      });
      return { porSlug: out, referencia: gv ? UMBRAL_UNINOMINAL * gv : null, titular: g?.slug || null };
    }
    const ultimo = new Map((rep.ultimos || []).map(u => [norm(u.partido), u.votos]));
    const med = mediana((rep.ultimos || []).map(u => u.votos));
    const electos = new Set((rep.electos || []).map(e => e.slug));
    rep.rows.forEach(r => {
      const f = [];
      if (electos.has(r.slug)) f.push('A');
      const ref = ultimo.get(norm(r.partido)) ?? med;
      if (!f.length && ref && Number(r.votos || 0) >= UMBRAL_LISTA * ref) f.push('B');
      if (f.length) out.set(r.slug, f);
    });
    return { porSlug: out, referencia: med ? UMBRAL_LISTA * med : null };
  }

  /* ── La escalera dentro de su lista (PLAN §5) ──────────────────────────
     Solo con voto preferente y lista abierta. «Su lista» = la del partido del
     CATÁLOGO que eligió en la ruta, casado con listaDelPartido de la meta (la
     misma regla: si la meta la encuentra, la escalera también). */
  function escalera(rep, partidoCampana, usuario = {}) {
    if (!rep || rep.uninominal) return { estado: 'uninominal' };
    if (!partidoCampana) return { estado: 'sin-partido' };
    const VT = global.VoteTarget;
    const party = VT && VT.listaDelPartido ? VT.listaDelPartido(rep.parties || [], partidoCampana) : null;
    if (!party) return { estado: 'sin-lista', partido: partidoCampana };
    const k = (rep.allocations && rep.allocations.get(party.name)) || 0;
    if (party.cerrada) return { estado: 'cerrada', lista: party.name, k, votos: party.votes };
    const suyos = new Set(usuario.slugs || []), suya = usuario.nombre ? llavePersona(usuario) : '';
    const filas = party.candidates.map((c, i) => ({ nombre: c.nombre, slug: c.slug, votos: Number(c.votos || 0), puesto: i + 1, elegido: i < k,
      usted: suyos.has(c.slug) || (suya && !suya.startsWith('slug:') && llavePersona(c) === suya) }));
    const ultimo = k ? filas[k - 1] : null, usted = filas.find(f => f.usted) || null;
    return { estado: 'abierta', lista: party.name, k, votos: party.votes, lista2023: party.lista || 0, filas, ultimo,
      usted, distancia: usted && ultimo && !usted.elegido ? ultimo.votos - usted.votos : null };
  }

  /* ── Evaluar: todo el cálculo sobre lo ya cargado ──────────────────────
     ctx = { corp, reparto, datos, base, baseModo, familiaUsuario, partidoCampana,
             usuario: {nombre, slugs}, meta, otras: [{entrada, porPuesto, total}],
             congresistas: [nombres] } */
  function evaluar(ctx) {
    const { reparto: rep, datos } = ctx;
    const VAL = totalValidos(datos);
    const fu = ctx.familiaUsuario || '';
    const suyos = new Set(ctx.usuario?.slugs || []);
    const llaveUsuario = ctx.usuario?.nombre ? llavePersona(ctx.usuario) : '';
    /* Por slug, por persona (3-4 componentes) o, para nombres de 2 o 5
       componentes que no se funden, por el nombre exacto: en un mismo
       territorio eso es la misma candidatura. */
    const nombreUsuario = norm(ctx.usuario?.nombre);
    const esUsuario = c => suyos.has(c.slug) || (llaveUsuario && !llaveUsuario.startsWith('slug:') && llavePersona(c) === llaveUsuario) || (nombreUsuario && norm(c.nombre) === nombreUsuario);
    const F = fuentesDelReparto(rep);

    /* Rivales de 2023 (A y B), con sus votos por puesto desde la matriz. */
    const porPersona = new Map();
    const añadir = (entrada, fuentes, pp, total) => {
      const k = llavePersona(entrada);
      if (!porPersona.has(k)) porPersona.set(k, { key: k, entradas: [], fuentes: new Set(), actual: null, porPuesto: null, votos: 0 });
      const r = porPersona.get(k);
      r.entradas.push(entrada); fuentes.forEach(f => r.fuentes.add(f));
      /* Manda la candidatura a la MISMA corporación de 2023 (A o B); entre
         las demás, la más reciente. */
      const rango = (fs, e) => (fs.some(f => f === 'A' || f === 'B') ? 10000 : 0) + anio(e);
      if (!r.actual || rango(fuentes, entrada) > rango(r.actualFuentes, r.actual)) { r.actual = entrada; r.actualFuentes = fuentes; r.porPuesto = pp || null; r.votos = total; }
    };
    (rep?.rows || []).forEach(row => {
      const f = F.porSlug.get(row.slug); if (!f || esUsuario(row)) return;
      const x = (datos.porCod && datos.porCod.get(codigoDeSlug(row.slug))) || datos.porCand.get(llaveCand(row.nombre, row.partido));
      añadir(row, f, x ? x.porPuesto : null, x ? x.total : Number(row.votos || 0));
    });
    /* Fuente C: otras elecciones con votos en el territorio (ya recortados). */
    const refC = F.referencia;
    (ctx.otras || []).forEach(o => {
      if (esUsuario(o.entrada)) return;
      if (o.fuente === 'E') { añadir(o.entrada, ['E'], o.porPuesto || null, o.total); return; }
      if (!refC || o.total < refC) return;
      añadir(o.entrada, ['C'], o.porPuesto || null, o.total);
    });

    /* Quien ganó en 2023 una alcaldía o gobernación de su territorio (fuente
       C) hoy ocupa ese cargo: el más votado de su elección entre los que llegan. */
    const enEjercicio = new Set(), mejor = new Map();
    (ctx.otras || []).forEach(o => {
      const p = String(o.entrada.slug || '').split('-'); if (o.fuente === 'E' || !/^(ALC|GOB)2023$/.test(p[0])) return;
      const k = p.slice(0, p[0].startsWith('ALC') ? 3 : 2).join('-'), x = mejor.get(k);   /* ALC2023-dep-mun · GOB2023-dep */
      if (!x || o.total > x.total) mejor.set(k, o);
    });
    mejor.forEach(o => enEjercicio.add(o.entrada.slug));
    const rivales = [...porPersona.values()].map(r => {
      const e = r.actual, fam = familia(e.partido, e.nombre);
      const af = r.porPuesto ? afinidad(ctx.base, r.porPuesto, r.votos, datos, VAL) : null;
      const cer = fu ? cercania(fu, fam) : CERCANIA_NO_SABEMOS;
      const marcas = [];
      if (F.titular && r.entradas.some(x => x.slug === F.titular)) marcas.push('titular-no-reelegible');
      if (esCongresista(e.nombre, ctx.congresistas)) marcas.push('congresista-2026');
      const partidos = new Set(r.entradas.map(x => norm(x.partido)));
      if (partidos.size > 1) marcas.push('cambio-de-partido');
      /* Votos a alcaldía o gobernación en una corporación de lista: miden otra
         cosa (un cargo ejecutivo, con toda la ciudad votando por dos o tres
         nombres) y no se comparan con el voto preferente. Medido: sin esta
         regla el alcalde de Bogotá entraba 2.º al plano del Concejo con 1,5
         millones de votos. Quedan en la lista, fuera del índice. */
      if (!UNINOMINALES.includes(ctx.corp) && UNINOMINAL_SLUG.test(e.slug || '')) marcas.push('voto-uninominal');
      if (enEjercicio.has(e.slug)) marcas.push('en-ejercicio');
      const enIndice = !marcas.some(m => FUERA_DEL_INDICE.has(m));
      return {
        key: r.key, nombre: e.nombre, partido: e.partido || '', slug: e.slug, corp: e.corp || '', anio: anio(e),
        familia: fam, pasos: fu && fam.sabemos ? pasos(fu, fam.bloque) : null, cercania: cer,
        fuentes: ['A', 'B', 'C', 'E'].filter(f => r.fuentes.has(f)), votos: r.votos,
        afinidad: af, franja: franja(af), correlacion: r.porPuesto ? correlacion(ctx.base, r.porPuesto, datos) : null,
        presion: presion({ cercania: cer, afinidad: af, votos: r.votos, meta: ctx.meta }),
        marcas, enIndice, porPuesto: r.porPuesto,
        entradas: r.entradas.map(x => ({ slug: x.slug, nombre: x.nombre, corp: x.corp, partido: x.partido, votos: x.votos })),
      };
    });
    /* Agregados a mano que no están en el registro: el nombre y nada más.
       Viven solo en el navegador del usuario (PLAN §9.6) y no se miden. */
    const yaEstan = new Set(rivales.map(r => norm(r.nombre)));
    (ctx.agregadosLibres || []).forEach(a => {
      const n = String(a?.nombre || '').trim(); if (!n || yaEstan.has(norm(n))) return;
      yaEstan.add(norm(n)); rivales.push(sinDatos({ key: `mano:${norm(n)}`, nombre: n, partido: a.partido || '', fuentes: ['E'], familiaUsuario: fu }));
    });
    niveles(rivales);
    rivales.sort((a, b) => (b.enIndice - a.enIndice) || (b.presion - a.presion) || (b.votos - a.votos));

    /* Rivales cercanos para el mapa: TODAS las candidaturas de su familia y
       las vecinas (no solo las que pasan el umbral), con su voto de lista. Es
       «dónde rinde su familia», que es más estable que unos pocos nombres. */
    const cercanos = [];
    if (fu) {
      datos.porCand.forEach(x => {
        if (esUsuario({ nombre: x.nombre, slug: '' })) return;
        if (cercania(fu, familia(x.partido, x.nombre)) >= CERCANO) cercanos.push(x.porPuesto);
      });
      datos.listas.forEach((pp, partido) => { if (cercania(fu, familia(partido, '')) >= CERCANO) cercanos.push(pp); });
    }
    const mapa = ctx.base ? disputa(ctx.base, datos, cercanos, { umbral: ctx.umbralMapa !== false }) : null;

    const conAf = rivales.filter(r => r.afinidad != null);
    const franjas = { alta: 0, 'mismo-terreno': 0, baja: 0, 'sin-dato': 0 };
    rivales.forEach(r => { franjas[r.franja]++; });
    const noSabemos = rivales.filter(r => !r.familia.sabemos);
    const avisos = [];
    if (conAf.length >= 5 && franjas['mismo-terreno'] / conAf.length >= AVISO_PAREJO) avisos.push('territorio-parejo');
    if (!fu) avisos.push('sin-familia');
    if (ctx.baseModo === 'familia') avisos.push('base-familia');
    if (datos.origen === 'archivos') avisos.push('sin-voto-de-lista');
    if (datos.faltan) avisos.push('matriz-incompleta');
    return {
      rivales, plano: rivales.filter(r => r.enIndice).slice(0, TOP_PLANO),
      vitrina: rivales.filter(r => r.enIndice).slice(0, VITRINA).map(r => r.key),
      escalera: escalera(rep, ctx.partidoCampana, ctx.usuario),
      mapa, avisos, familiaUsuario: fu, baseModo: ctx.baseModo || null,
      base: ctx.base ? { total: ctx.base.total, puestos: ctx.base.puestos, fuera: ctx.base.fuera } : null,
      resumen: {
        rivales: rivales.length, enIndice: rivales.filter(r => r.enIndice).length,
        afinidad: conAf.length ? [Math.min(...conAf.map(r => r.afinidad)), Math.max(...conAf.map(r => r.afinidad))] : null,
        franjas, noSabemos: noSabemos.length, noSabemosVotos: noSabemos.reduce((s, r) => s + r.votos, 0),
        niveles: ['alta', 'media', 'baja'].reduce((o, n) => (o[n] = rivales.filter(r => r.nivel === n).length, o), {}),
        puestos: datos.validos.size, validos: VAL, origen: datos.origen,
      },
      reparto: rep ? { label: rep.label, uninominal: rep.uninominal, curules: rep.seats || null, cifra: rep.cifra ? Math.round(rep.cifra) : null,
        porLista: rep.allocations ? [...rep.allocations.entries()].sort((a, b) => b[1] - a[1]) : null } : null,
    };
  }

  /* ── Cargar: la IO ─────────────────────────────────────────────────────
     deps = { baseUrl?, alcance, mesasPropias?, mesasFamilia?, registro?, congresistas?,
              mesasDe?(url), totalesDe?(nombre), puestosDestino?(campana), dentro?(mesa) }
     `alcance` sale de C360Endoso.alcanceDe (el mismo recorte del mapa). */
  const TOTALES = { concejo: 'concejo-2023', jal: 'jal-2023', alcaldia: 'alcaldia-2023', asamblea: 'asamblea-2023', gobernacion: 'gobernacion-2023' };
  const CON_MATRIZ = ['concejo', 'jal', 'asamblea'];
  const cacheJson = new Map();
  function jsonDe(url) {
    if (!cacheJson.has(url)) cacheJson.set(url, fetch(url).then(r => r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status))).catch(e => { cacheJson.delete(url); throw e; }));
    return cacheJson.get(url);
  }
  async function enTandas(tareas, n = 6) {
    const out = []; let i = 0;
    await Promise.all(Array.from({ length: n }, async () => { while (i < tareas.length) { const k = i++; out[k] = await tareas[k]().catch(() => null); } }));
    return out;
  }
  function territorioDe(alcance, campana) {
    if (!alcance) return '';
    if (alcance.tipo === 'departamento') return campana.departamentoNombre || alcance.nombre || '';
    if (alcance.tipo === 'localidad') return `${alcance.localidad} · ${campana.municipio || ''}`;
    return campana.municipio || alcance.nombre || '';
  }
  /* Rivales de OTRAS elecciones cuya circunscripción cabe entera en el
     territorio: sus votos ya son votos del territorio y no hay que recortar
     para decidir si pasan el umbral. Lo que es más grande que el territorio
     (Senado, la Cámara de un departamento para un concejo municipal, el
     concejo de la ciudad para una JAL) exige bajar su archivo y recortarlo:
     queda para una fase siguiente, y el panel lo dice. */
  function candidatasOtras(registro, alcance, corp, excluir) {
    if (!alcance || !registro) return [];
    const dep = String(Number(alcance.departamento || 0)), mun = String(Number(alcance.municipio || 0));
    const MUN = /^(CONC|ALC|JAL)(\d{4})-(\d+)-(\d+)-/, DEP = /^(ASAM|GOB)(\d{4})-(\d+)-/, CAM = /^CON(\d{4})-C-(\d+)-/;
    const bogota = dep === '16';
    return registro.filter(c => {
      const s = String(c.slug || ''); if (excluir.has(s)) return false;
      let m;
      if (alcance.tipo === 'departamento') {
        if ((m = s.match(DEP))) return m[3] === dep;
        if ((m = s.match(CAM))) return m[2] === dep;
        return false;
      }
      if (alcance.tipo === 'localidad') {
        return (m = s.match(MUN)) && m[1] === 'JAL' && m[3] === dep && m[4] === mun && norm(c.circunscripcion).startsWith(norm(alcance.localidad));
      }
      if ((m = s.match(MUN))) return m[3] === dep && m[4] === mun;
      /* Bogotá es a la vez municipio y departamento: su Cámara cabe entera. */
      if (bogota && (m = s.match(CAM))) return m[2] === dep;
      return false;
    });
  }

  async function cargar(campana, deps = {}) {
    const baseUrl = deps.baseUrl || S3, corp = campana.corp || '';
    const alcance = deps.alcance;
    const leerMesas = deps.mesasDe || (url => jsonDe(url).then(d => d.mesas || []));
    const leerTotales = deps.totalesDe || (n => jsonDe(`${baseUrl}/totales-puesto/${n}.json`).then(d => d.puestos || {}));
    const E = global.C360Endoso;
    const dentro = deps.dentro || (alcance && E ? m => E.enAlcance(m, alcance) : null);
    const codigo = alcance ? { dep: alcance.departamento, mun: alcance.municipio } : null;
    /* El reparto y la matriz van en paralelo: cada uno baja lo suyo (el índice
       de la corporación, los archivos por comuna) y en fila sumaban. */
    const repP = global.VoteTarget.reparto({ corp, territory: territorioDe(alcance, campana), baseUrl, codigo }).catch(() => null);
    const destinoP = CON_MATRIZ.includes(corp) ? Promise.resolve((deps.puestosDestino || global.C360DiaD?.puestosDestino)?.(campana)).catch(() => null) : Promise.resolve(null);
    const [rep, destino] = await Promise.all([repP, destinoP]);
    /* La URL por el slug con la regla del electorado (JAL2023 → jal-2023/…):
       `CandRegistry.dataUrlFor` sin el índice cargado cae a la carpeta del
       Congreso y daba 404 en todo el modo sin matriz. */
    const urlDe = c => c.dataUrl || global.C360Electorado?.urlCandidatura?.(c.slug) || (global.CandRegistry ? global.CandRegistry.dataUrlFor(c.slug) : `${baseUrl}/${c.slug}.json`);

    /* La matriz, si existe para ESTA corporación. */
    let datos = null;
    if (destino && destino.fuente === corp && destino.archivos.length) { datos = matrizDesdeArchivos(destino.archivos); datos.faltan = destino.faltan || 0; }
    /* Sin archivos por comuna, la matriz nacional (D1, fase 4): un archivo por
       municipio o departamento con todas las candidaturas de 2023. */
    const matrizBase = deps.matrizBase || `${baseUrl}/matriz-puesto`;
    if (!datos && alcance && alcance.tipo !== 'localidad' && ['concejo', 'alcaldia', 'gobernacion', 'asamblea'].includes(corp)) {
      const clave = alcance.tipo === 'departamento' ? pad(alcance.departamento, 2) : `${pad(alcance.departamento, 2)}-${pad(alcance.municipio, 3)}`;
      const d = await jsonDe(`${matrizBase}/${corp}-2023/${clave}.json`).catch(() => null);
      if (d?.puestos?.length) { datos = matrizDesdeArchivos([{ d, mun: d.mme }]); datos.origen = 'matriz'; datos.nacional = true; }
    }
    if (!datos) {
      const filas = (rep?.rows || []).filter(r => Number(r.votos || 0) > 0);
      const partes = await enTandas(filas.map(r => () => leerMesas(urlDe(r)).then(mesas => ({ entrada: r, mesas }))));
      const tot = await leerTotales(TOTALES[corp]).catch(() => ({}));
      datos = matrizDesdeMesas(partes.filter(Boolean), tot, dentro);
    }

    /* Fuente C. Sus votos ya están enteros en el territorio (candidatasOtras),
       así que el umbral se aplica sin bajar nada. Y quien ya es rival por su
       candidatura de 2023 (A o B) no necesita su archivo viejo: su historial
       entra con los votos del índice y manda la de 2023. Solo se bajan los
       archivos de las personas NUEVAS, que son las que mueven el plano. */
    const excluir = new Set((rep?.rows || []).map(r => r.slug));
    let otras = [];
    const F0 = fuentesDelReparto(rep), ref = F0.referencia;
    if (ref) {
      const de2023 = new Set((rep?.rows || []).filter(r => F0.porSlug.has(r.slug)).map(llavePersona).filter(k => !k.startsWith('slug:')));
      /* `registro` puede llegar como promesa: `leer` lo pide en paralelo. */
      const pasan = candidatasOtras(await deps.registro, alcance, corp, excluir).filter(c => Number(c.votos || 0) >= ref);
      const conocidas = pasan.filter(c => de2023.has(llavePersona(c)));
      /* Quien viene de alcaldía o gobernación queda fuera del índice en una
         corporación de lista (ver evaluar): su archivo no se baja. El del
         alcalde de Bogotá son 1,5 millones de votos mesa a mesa. */
      const sinArchivo = c => !UNINOMINALES.includes(corp) && UNINOMINAL_SLUG.test(c.slug || '');
      const candidatasNuevas = pasan.filter(c => !de2023.has(llavePersona(c)) && !sinArchivo(c)).sort((a, b) => b.votos - a.votos);
      /* El tope depende de cuánto pesa el archivo: el de un edil ronda 100 KB
         y el de un concejal de Bogotá 2 MB. Las que pasan del tope siguen
         siendo rivales: entran sin votos por puesto (sin afinidad medida, que
         la presión trata como neutra), no desaparecen. */
      const esJal = c => /^JAL\d{4}-/.test(c.slug || '');
      const nuevas = [...candidatasNuevas.filter(esJal).slice(0, MAX_OTRAS_JAL), ...candidatasNuevas.filter(c => !esJal(c)).slice(0, MAX_OTRAS)];
      const bajadas = new Set(nuevas.map(c => c.slug));
      conocidas.push(...pasan.filter(c => !de2023.has(llavePersona(c)) && sinArchivo(c)), ...candidatasNuevas.filter(c => !bajadas.has(c.slug)));
      /* Primero la matriz nacional: un archivo por municipio trae a todas las
         candidaturas de esa elección, así que las personas que estén ahí se
         leen sin bajar su archivo y sin contar contra el tope. */
      const desdeMatriz = [];
      if (alcance && alcance.tipo !== 'localidad') {
        const porArchivo = new Map();
        [...candidatasNuevas].forEach(c => { const f = matrizDeSlug(c.slug); if (f) { if (!porArchivo.has(f)) porArchivo.set(f, []); porArchivo.get(f).push(c); } });
        const leidos = await enTandas([...porArchivo.keys()].map(f => () => jsonDe(`${matrizBase}/${f}`).then(d => ({ f, d }))), 4);
        leidos.filter(Boolean).forEach(({ f, d }) => {
          const M = matrizDesdeArchivos([{ d, mun: d.mme }]);
          porArchivo.get(f).forEach(c => {
            const x = M.porCod.get(codigoDeSlug(c.slug)) || M.porCand.get(llaveCand(c.nombre, c.partido)); if (!x) return;
            const pp = new Map(); let suma = 0;
            x.porPuesto.forEach((v, code) => { if (dentro && !dentro({ dep: code.slice(0, 2), mun: code.slice(2, 5), zon: code.slice(5, 7), pue: code.slice(7) })) return; pp.set(code, v); suma += v; });
            /* El total es el del índice, como en las fuentes A y B: su
               circunscripción cabe entera en el territorio (candidatasOtras) y
               la matriz no trae las zonas 90 y 98 (censo y cárceles). */
            desdeMatriz.push({ entrada: c, porPuesto: pp, total: Number(c.votos || 0) || suma });
          });
        });
      }
      const yaLeidas = new Set(desdeMatriz.map(o => o.entrada.slug));
      const pendientes = nuevas.filter(c => !yaLeidas.has(c.slug));
      /* Las que el tope dejó sin archivo pero sí salieron de la matriz no van
         a la lista de «sin votos por puesto». */
      for (let i = conocidas.length - 1; i >= 0; i--) if (yaLeidas.has(conocidas[i].slug)) conocidas.splice(i, 1);
      const partes = await enTandas(pendientes.map(c => () => leerMesas(urlDe(c)).then(mesas => ({ c, mesas }))));
      otras = desdeMatriz.concat(partes.filter(Boolean).map(({ c, mesas }) => {
        const pp = new Map(); let total = 0;
        mesas.forEach(m => { if (dentro && !dentro(m)) return; const v = Number(m.v || 0); if (!v) return; const k = codigoPuesto(m); pp.set(k, (pp.get(k) || 0) + v); total += v; });
        return { entrada: c, porPuesto: pp, total };
      })).concat(conocidas.map(c => ({ entrada: c, porPuesto: null, total: Number(c.votos || 0) })));
    }

    /* La base: la propia recortada; si no alcanza, la de su familia. */
    let base = baseDesdeMesas(deps.mesasPropias, datos, dentro), baseModo = null;
    const mismaCorp = (deps.slugsPropios || []).some(s => ({ JAL: 'jal', CONC: 'concejo', ALC: 'alcaldia', ASAM: 'asamblea', GOB: 'gobernacion' })[String(s).match(/^[A-Z]+/)?.[0]] === corp);
    if (baseSuficiente(base)) baseModo = mismaCorp ? 'propio' : 'salto';
    else if (deps.mesasFamilia) { base = baseDesdeMesas(deps.mesasFamilia, datos, null); baseModo = baseSuficiente(base) ? 'familia' : null; }
    if (!baseModo) base = null;

    /* Fuente E: los que agregó el usuario desde el registro. Entran aunque no
       pasen el umbral (los puso él) y con sus votos recortados al territorio;
       si su archivo no responde, entran sin votos por puesto. */
    const agregados = (deps.agregados || []).filter(a => a && a.slug);
    if (agregados.length) {
      const partesE = await enTandas(agregados.map(a => () => leerMesas(urlDe(a)).then(mesas => ({ a, mesas })).catch(() => ({ a, mesas: null }))));
      partesE.filter(Boolean).forEach(({ a, mesas }) => {
        if (!mesas) { otras.push({ entrada: a, porPuesto: null, total: Number(a.votos || 0), fuente: 'E' }); return; }
        const pp = new Map(); let total = 0;
        mesas.forEach(m => { if (dentro && !dentro(m)) return; const v = Number(m.v || 0); if (!v) return; const k = codigoPuesto(m); pp.set(k, (pp.get(k) || 0) + v); total += v; });
        otras.push({ entrada: a, porPuesto: pp.size ? pp : null, total, fuente: 'E' });
      });
    }

    return { corp, reparto: rep, datos, base, baseModo, otras, alcance };
  }

  /* ── Los índices de la fuente C ───────────────────────────────────────
     Solo los que pueden traer candidaturas enteras dentro del territorio
     (candidatasOtras filtra por código). Se bajan una vez por página y se
     quedan solo las filas del territorio: un índice de concejos pesa 20 MB en
     claro y de él sirven unos cientos de filas. */
  const INDICES_C = {
    jal: ['jal-2019', 'jal-2015'],
    concejo: ['concejo-2019', 'alcaldia-2023', 'alcaldia-2019', 'jal-2023'],
    alcaldia: ['alcaldia-2019', 'concejo-2023', 'concejo-2019'],
    asamblea: ['asamblea-2019', 'gobernacion-2023'],
    gobernacion: ['gobernacion-2019', 'asamblea-2023'],
  };
  /* ⚠️ La Cámara salió de la fuente C (fase 3, medido): sus archivos mesa a
     mesa pesan ~2 MB cada uno en Bogotá y, con ellos, abrir el Concejo de
     Bogotá bajaba 90 MB y tardaba un minuto. Es raro que un representante
     baje al concejo o la asamblea; si hace falta, entra con una matriz propia
     por circunscripción (D1 del plan), no archivo por archivo. */
  async function registroC(corp, alcance, baseUrl = S3) {
    if (!alcance) return [];
    const dirs = (INDICES_C[corp] || []).slice();
    const partes = await enTandas(dirs.map(dir => () => jsonDe(`${baseUrl}/${dir}/index-${dir}.json`)
      .then(d => (Array.isArray(d) ? d : d.candidatos || []).map(c => ({ ...c, dataUrl: `${baseUrl}/${dir}/${c.slug}.json` })))), 3);
    return candidatasOtras(partes.filter(Boolean).flat(), alcance, corp, new Set());
  }
  /* Los 285 congresistas 2026-2030 de legislativo-electos.js, si la página lo
     cargó (su `const ELECTOS` vive en el ámbito global de los scripts). */
  function congresistas() {
    try { return typeof ELECTOS !== 'undefined' ? ELECTOS.map(e => e.nombre) : []; } catch { return []; }
  }

  /* ── Leer: todo, desde lo que sabe quien llama ─────────────────────────
     El CRM y el panel llaman ESTA función con las mismas entradas (campaña,
     slugs, mesas propias, territorio, meta probable): así la tarjeta 10 y el
     panel dan las mismas cifras. Si la base propia no alcanza, la de su
     familia política con la misma cuenta del Día D (C360DiaD.fuente). */
  /* «La misma corporación» guarda la campaña SIN territorio (el CRM lo deja
     vacío: el territorio es el de su última candidatura). La matriz y la base
     de la familia lo necesitan por nombre y código, así que se completa desde
     el alcance y sus mesas: el municipio por el nombre que traen las mesas,
     que es el que la cartografía traduce a código electoral. */
  function completarCampana(campana = {}, alcance, mesasPropias) {
    if (!alcance) return campana;
    /* El código electoral del municipio va siempre que el alcance lo tenga: el
       nombre no casa entre mesas y cartografía (Cartagena, Cali, Cúcuta). */
    const conCodigo = alcance.municipio ? { municipioCodigo: pad(alcance.municipio, 3) } : {};
    if (campana.departamento) return Object.assign({}, campana, conCodigo);
    const E = global.C360Endoso;
    const mesa = (mesasPropias || []).find(m => E ? E.enAlcance(m, alcance) : true) || {};
    return Object.assign({}, campana, {
      departamento: pad(alcance.departamento, 2), departamentoNombre: campana.departamentoNombre || mesa.depNom || '',
      municipio: alcance.tipo === 'departamento' ? '' : (mesa.munNom || alcance.nombre || ''),
      localidad: alcance.tipo === 'localidad' ? alcance.localidad : '',
    }, conCodigo);
  }
  async function leer({ campana = {}, slugs = [], mesasPropias = null, alcance = null, meta = 0, usuario = {}, baseUrl = S3, registro = null, matrizBase = null, agregados = [] } = {}) {
    campana = completarCampana(campana, alcance, mesasPropias);
    const reg = registro || registroC(campana.corp, alcance, baseUrl).catch(() => []);   /* promesa: corre junto con el reparto y la matriz */
    const cargado = await cargar(campana, { baseUrl, alcance, mesasPropias, slugsPropios: slugs, registro: reg, matrizBase, agregados });
    if (!cargado.base && global.C360DiaD?.fuente) {
      const F = await global.C360DiaD.fuente({ slugs, campana }).catch(() => null);
      if (F && F.modo === 'territorio' && F.mesas.length) {
        const b = baseDesdeMesas(F.mesas, cargado.datos, null);
        if (baseSuficiente(b)) { cargado.base = b; cargado.baseModo = 'familia'; cargado.familiaTexto = F.famTexto || ''; }
      }
    }
    const L = evaluar({ ...cargado, familiaUsuario: familiaCampana(campana), partidoCampana: campana.avales === 'partido' || !campana.avales ? (campana.partido || '') : '',
      usuario, meta, congresistas: congresistas(), agregadosLibres: agregados.filter(a => a && !a.slug) });
    L.familiaTexto = cargado.familiaTexto || '';
    L.alcance = alcance; L.corp = campana.corp || '';
    /* Sin un solo puesto leído no hay lectura: que quien llama lo diga, en vez
       de pintar «cero rivales» como si fuera un dato. */
    if (!cargado.datos.validos.size) throw new Error('No se pudieron leer los resultados de su territorio');
    L.datos = cargado.datos; L.baseDatos = cargado.base; L.campana = campana; L.repartoCompleto = cargado.reparto;
    return L;
  }

  /* Un rival sin datos electorales (fuente D o E fuera del registro): está en
     la lista para que el usuario lo vea, fuera del índice y sin eje Y. */
  function sinDatos({ key, nombre, partido = '', fuentes, familiaUsuario: fu = '' }) {
    const fam = familia(partido, nombre);
    return { key, nombre, partido, slug: '', corp: '', anio: 0, familia: fam, pasos: fu && fam.sabemos ? pasos(fu, fam.bloque) : null,
      cercania: fu ? cercania(fu, fam) : CERCANIA_NO_SABEMOS, fuentes, votos: 0, afinidad: null, franja: 'sin-dato', correlacion: null,
      presion: 0, marcas: ['sin-datos-electorales'], enIndice: false, porPuesto: null, entradas: [] };
  }

  /* ── Fase 5 · la prensa de cada rival (PLAN §7) ────────────────────────
     Titulares LITERALES que lo nombran, sin resumen de modelo. Un titular
     cuenta si trae dos componentes del nombre como palabras enteras (el mismo
     criterio del briefing, pero sin casar dentro de otra palabra). Si trae
     solo la forma corta (nombre + apellido) se marca «parcial»: puede ser un
     homónimo, y la ficha lo dice. */
  const DIAS_PRENSA = 180, MESES_PRENSA = 6, ULTIMOS_PRENSA = 5;
  const TEMAS_SIN_CONTEO = new Set(['corrupcion']);   /* P8: titulares literales, sin etiqueta pegada al nombre */
  const MENUDAS_NOMBRE = new Set(['DE', 'DEL', 'LA', 'LAS', 'LOS', 'Y', 'SAN', 'SANTA']);
  const tokensNombre = n => norm(n).split(' ').filter(t => t.length >= 3 && !MENUDAS_NOMBRE.has(t));
  /* Una mención PARCIAL (nombre y un apellido) tiene que ser un nombre
     completo por sí sola: si viene pegada a otro nombre propio que no es suyo,
     es otra persona. Medido: con «Carlos Fernando Galán Pachón» los 14
     titulares de seis meses eran de «Luis Carlos Galán Sarmiento» (el juicio
     por el magnicidio de su padre). Delante se admite un cargo («Concejal
     Julián Forero») o un signo que corte. */
  const ANTES_OK = new Set(['CONCEJAL', 'CONCEJALA', 'EXCONCEJAL', 'EXCONCEJALA', 'EDIL', 'EDILESA', 'ALCALDE', 'ALCALDESA', 'EXALCALDE', 'EXALCALDESA', 'GOBERNADOR', 'GOBERNADORA',
    'DIPUTADO', 'DIPUTADA', 'SENADOR', 'SENADORA', 'REPRESENTANTE', 'CANDIDATO', 'CANDIDATA', 'PRECANDIDATO', 'PRECANDIDATA', 'EXSENADOR', 'EXSENADORA', 'LIDER', 'LIDERESA',
    'VIDEO', 'HOY', 'EXCLUSIVA', 'ATENCION', 'OPINION', 'ENTREVISTA', 'POLEMICA', 'ASI']);
  const palabrasTitulo = titulo => {
    const out = [];
    String(titulo || '').split(/\s+/).forEach(w => {
      if (!/[A-Za-zÁÉÍÓÚÑÜáéíóúñü0-9]/.test(w)) { if (out.length) out[out.length - 1].corte = true; return; }
      const limpio = w.replace(/^[«"“'‘(¿¡]+/, '');
      out.push({ n: norm(limpio), mayus: /^[A-ZÁÉÍÓÚÑÜ]/.test(limpio), corte: /[,.:;!?)»"”’|]$/.test(w), antesCorte: limpio !== w });
    });
    return out;
  };
  function mencionaPersona(titulo, nombre) {
    const tk = tokensNombre(nombre); if (tk.length < 2) return null;
    const set = new Set(tk), P = palabrasTitulo(titulo);
    const n = tk.filter(t => P.some(p => p.n === t)).length;
    if (n < 2) return null;
    if (n >= Math.min(3, tk.length)) return 'exacto';
    /* Parcial: una racha contigua de ≥ 2 palabras suyas, sin otro nombre propio
       pegado antes ni después. */
    for (let i = 0; i < P.length; i++) {
      if (!set.has(P[i].n)) continue;
      let j = i; while (j + 1 < P.length && !P[j].corte && set.has(P[j + 1].n)) j++;
      if (j === i) continue;
      const a = P[i - 1], d = P[j + 1];
      /* También al arranque del titular: «Luis Carlos Galán: …» es otra
         persona. El costo es perder «Denuncian Julián Forero…» como mención
         parcial; atribuirle a alguien los titulares de otro es peor. */
      const antesMal = a && !a.corte && !P[i].antesCorte && a.mayus && !ANTES_OK.has(a.n);
      const despuesMal = d && !P[j].corte && !d.antesCorte && d.mayus && !set.has(d.n);
      if (!antesMal && !despuesMal) return 'parcial';
      i = j;
    }
    return null;
  }
  /* Las consultas: el nombre completo entre comillas y, con cuatro palabras,
     la forma corta con la que lo nombra la prensa (primer nombre + primer
     apellido). Con tres no: «LUIS JOSE PAZ» daría «Luis José», dos nombres de
     pila, y traería titulares de cualquiera. */
  function consultasPrensa(nombre) {
    const w = String(nombre || '').trim().split(/\s+/).filter(Boolean);
    const q = [w.join(' ')];
    if (w.length >= 4) q.push(`${w[0]} ${w[2]}`);
    return [...new Set(q.filter(x => x.split(' ').length >= 2))].map(x => `"${x}"`);
  }
  const mesDe = f => String(f || '').slice(0, 7);
  function prensaDe(items, nombre, hoy = new Date()) {
    const vistos = new Set(), titulares = [];
    (items || []).forEach(it => {
      const k = norm(it.titulo).slice(0, 90), m = mencionaPersona(it.titulo, nombre);
      if (!k || !m || vistos.has(k)) return;
      vistos.add(k); titulares.push({ titulo: it.titulo, medio: it.medio || '', url: it.url || '', fecha: it.fecha || '', alcance: it.alcance || '', coincidencia: m });
    });
    titulares.sort((a, b) => String(b.fecha).localeCompare(String(a.fecha)));
    const d = new Date(hoy), meses = [];
    for (let i = MESES_PRENSA - 1; i >= 0; i--) { const x = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() - i, 1)); meses.push(x.toISOString().slice(0, 7)); }
    const porMes = meses.map(mes => ({ mes, n: titulares.filter(t => mesDe(t.fecha) === mes).length }));
    const S = global.C360Saliencia, temas = new Map();
    if (S) titulares.forEach(t => S.temasDe(S.norm(t.titulo)).forEach(id => { if (!TEMAS_SIN_CONTEO.has(id)) temas.set(id, (temas.get(id) || 0) + 1); }));
    const nombreTema = id => S?.TEMAS.find(t => t.id === id)?.nombre || id;
    return { total: titulares.length, exactos: titulares.filter(t => t.coincidencia === 'exacto').length, porMes, ultimos: titulares.slice(0, ULTIMOS_PRENSA),
      medios: new Set(titulares.map(t => norm(t.medio)).filter(Boolean)).size,
      temas: [...temas].sort((a, b) => b[1] - a[1]).map(([id, n]) => ({ id, nombre: nombreTema(id), n })) };
  }
  /* La IO: `caudal` es la función que habla con /caudal/api (la del panel). */
  async function buscarPrensa(nombre, { caudal, hoy } = {}) {
    if (!caudal) throw new Error('Sin acceso a la prensa');
    const res = await Promise.all(consultasPrensa(nombre).map(q => caudal({ action: 'medios', query: q, dias: DIAS_PRENSA }).then(d => d?.resultados || []).catch(() => null)));
    if (res.every(r => r === null)) throw new Error('La búsqueda de prensa no respondió');
    return prensaDe(res.filter(Boolean).flat(), nombre, hoy);
  }

  /* ── Fase 5 · la revisión mensual (PLAN §8) ───────────────────────────
     La revisión es por TERRITORIO y corporación, no por cuenta: todas las
     candidaturas al Concejo de Bogotá ven la misma. La llave del territorio
     sale del alcance (códigos, no nombres) y es la misma que usa el worker. */
  const slugTexto = s => norm(s).toLowerCase().replace(/\s+/g, '-');
  function terrKey(corp, alcance) {
    const a = alcance || {}, c = String(corp || '').toLowerCase();
    if (!c || !a.departamento) return '';
    if (a.tipo === 'departamento') return `${c}:${pad(a.departamento, 2)}`;
    const base = `${c}:${pad(a.departamento, 2)}-${pad(a.municipio, 3)}`;
    return a.tipo === 'localidad' && a.localidad ? `${base}:${slugTexto(a.localidad)}` : base;
  }
  const MESES_TXT = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
  const fechaLarga = iso => { const d = new Date(String(iso).slice(0, 10) + 'T12:00:00Z'); return isNaN(d) ? '' : `${d.getUTCDate()} de ${MESES_TXT[d.getUTCMonth()]} de ${d.getUTCFullYear()}`; };
  /* La revisión corre el día 1 de cada mes: la próxima es el 1 del mes siguiente. */
  function proximaRevision(hoy = new Date()) { const d = new Date(hoy); return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1)).toISOString().slice(0, 10); }
  function cambiosTexto(c) {
    if (!c) return '';
    const p = [];
    (c.entran || []).forEach(e => p.push(`entra ${P1(e.nombre)} (prensa, ${e.medios} medio${e.medios === 1 ? '' : 's'})`));
    if (c.aval?.length) p.push(`${c.aval.length} cambió de aval`);
    if (c.salen?.length) p.push(`${c.salen.length} ya no compite${c.salen.length === 1 ? '' : 'n'}`);
    if (c.conTitulares) p.push(`${c.conTitulares} con titulares nuevos`);
    return p.length ? `Desde la revisión anterior: ${p.join(' · ')}.` : 'Sin cambios desde la revisión anterior.';
  }
  const P1 = n => corto(n) || n;
  /* Integra la revisión del territorio a la lectura: quien fue dicho en prensa
     y ya es rival suma la fuente D; quien no, entra a la lista sin datos
     electorales, fuera del índice. Muta L y devuelve el resumen para pintar. */
  function integrarRevision(L, snap, hoy = new Date()) {
    const out = { revisado: null, proxima: proximaRevision(hoy), linea: '', cambios: null };
    if (!L || !snap || !snap.revisado) return out;
    out.revisado = snap.revisado; out.cambios = snap.cambios || null; out.linea = cambiosTexto(snap.cambios);
    /* La próxima sale de la más tardía entre hoy y la revisión: una revisión
       del 1 de octubre vista el 30 de septiembre (reloj del usuario) no puede
       decir «próxima: 1 de octubre». */
    const rev = new Date(snap.revisado);
    if (!isNaN(rev) && rev > new Date(hoy)) out.proxima = proximaRevision(rev);
    const porNombre = new Map(L.rivales.map(r => [norm(r.nombre), r])), porKey = new Map(L.rivales.map(r => [r.key, r]));
    (snap.lista || []).forEach(x => {
      if (!x || !x.nombre) return;
      const r = (x.k && porKey.get(x.k)) || porNombre.get(norm(x.nombre));
      const pr = { medios: Number(x.medios || 0), titulares: (x.titulares || []).slice(0, ULTIMOS_PRENSA), aval: x.aval || '' };
      if (r) { if (!r.fuentes.includes('D')) r.fuentes.push('D'); r.prensaRevision = pr; return; }
      const nuevo = sinDatos({ key: `prensa:${norm(x.nombre)}`, nombre: x.nombre, partido: x.aval || '', fuentes: ['D'], familiaUsuario: L.familiaUsuario || '' });
      nuevo.prensaRevision = pr; L.rivales.push(nuevo); porNombre.set(norm(x.nombre), nuevo);
    });
    return out;
  }

  /* ── Textos compartidos ────────────────────────────────────────────── */
  const FUENTE_TXT = { A: 'Ganó la curul en 2023', B: 'Compitió aquí en 2023', C: 'Tiene votos aquí de otra elección', D: 'Dicho en prensa como aspirante', E: 'Lo agregó usted' };
  const FUENTE_TITULAR = 'Ganó en 2023 · no puede reelegirse';
  function sello(r) {
    if (r.marcas.includes('titular-no-reelegible')) return FUENTE_TITULAR;
    const f = r.fuentes[0];
    if (f === 'D') return `Dicho en prensa · ${r.prensaRevision?.medios || 0} medio${r.prensaRevision?.medios === 1 ? '' : 's'}`;
    return FUENTE_TXT[f] ? `${FUENTE_TXT[f]}${f === 'C' && r.anio ? ` (${r.corp.split('·')[0].trim().toLowerCase()} ${r.anio})` : ''}` : '';
  }
  const FRANJA_TXT = { alta: 'rinde más en su base', 'mismo-terreno': 'mismo terreno', baja: 'rinde menos en su base', 'sin-dato': 'sin votos por puesto' };
  const NIVEL_TXT = { alta: 'Presión alta', media: 'Presión media', baja: 'Presión baja' };
  const MARCA_TXT = { 'congresista-2026': 'Hoy es congresista (2026-2030)', 'titular-no-reelegible': 'No puede reelegirse (C.P. arts. 303 y 314)', 'cambio-de-partido': 'Compitió por otro partido antes', 'voto-uninominal': 'Sus votos son de alcaldía o gobernación: no se comparan con los de una lista', 'en-ejercicio': 'Hoy ocupa ese cargo (elegido en 2023)', 'sin-datos-electorales': 'Sin candidaturas en el registro: no se puede medir' };
  const AVISO_TXT = {
    'territorio-parejo': 'En este territorio todos compiten por los mismos puestos: casi ningún rival rinde en su base distinto de como rinde en el resto. Lo que los separa es la lista y la familia política, no el territorio.',
    'base-familia': 'Todavía no tiene votos propios en este territorio, así que la afinidad se mide contra los votos de su familia política en 2023.',
    'sin-familia': 'Sin partido ni espectro definidos no hay eje ideológico: la cercanía de todos cuenta como «no sabemos».',
    'matriz-incompleta': 'No pudimos leer una parte de los resultados de su territorio: faltan puestos en esta lectura. Vuelva a cargar la página.',
    'sin-voto-de-lista': 'Aquí no tenemos la matriz de 2023 por puesto: los votos de cada rival salen de su propio archivo y no incluyen el voto solo por la lista.',
  };
  const corto = n => { const w = String(n || '').split(/\s+/).filter(Boolean); const bonito = x => x.charAt(0) + x.slice(1).toLowerCase(); return w.length >= 3 ? `${bonito(w[0])} ${bonito(w[w.length >= 4 ? 2 : 1])}` : w.map(bonito).join(' '); };
  const escSvg = s => String(s ?? '').replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));

  /* ── El plano (PLAN §3) ────────────────────────────────────────────────
     SVG en texto, sin DOM: la tarjeta y el panel pintan el mismo dibujo.
     X = familia (cinco columnas) y una franja aparte para «no sabemos»;
     Y = afinidad en escala logarítmica FIJA (0,25 a 4, no se estira para
     inventar diferencias), con la franja «mismo terreno». Burbuja = votos en
     el territorio. `vitrina` deja nítidos solo los primeros y a los demás los
     pinta sin nombre ni título: el texto no llega al DOM. */
  const ROTULO_CORTO = { izq: 'Izq.', ci: 'C-izq.', c: 'Centro', cd: 'C-der.', d: 'Der.' };
  function planoSVG(L, { ancho = 640, alto = 380, etiquetas = TOP_PLANO, vitrina = false, clic = false } = {}) {
    const PB = global.PartidosBloques, col = PB?.BLOQUE_COLOR || {};
    const m = { i: 44, d: 12, a: 14, b: 34 }, franjaNS = 34;   /* la leyenda va en HTML: dentro del SVG se cortaba en pantallas angostas */
    const W = ancho - m.i - m.d, H = alto - m.a - m.b - franjaNS;
    const orden = ['izq', 'ci', 'c', 'cd', 'd'], cw = W / orden.length;
    const yDe = a => { const l = Math.log2(Math.min(4, Math.max(.25, a))); return m.a + H / 2 - (l / 2) * (H / 2); };
    const hash = s => { let h = 0; for (const ch of String(s)) h = (h * 31 + ch.charCodeAt(0)) >>> 0; return (h % 1000) / 1000; };
    const visibles = new Set((vitrina ? L.vitrina : L.plano.slice(0, etiquetas).map(r => r.key)));
    const lista = L.rivales.filter(r => r.enIndice || r.marcas.includes('congresista-2026'));
    const maxV = Math.max(1, ...lista.map(r => r.votos || 0));
    const partes = [];
    partes.push(`<svg class="k-plano" viewBox="0 0 ${ancho} ${alto}" role="img" aria-label="Plano de contendientes: familia política contra afinidad territorial">`);
    orden.forEach((b, k) => {
      const x = m.i + k * cw;
      if (b === L.familiaUsuario) partes.push(`<rect x="${x}" y="${m.a}" width="${cw}" height="${H}" class="k-usted"/><text x="${x + cw / 2}" y="${m.a + 12}" class="k-usted-t" text-anchor="middle">usted</text>`);
      /* Dos rótulos: el largo y el corto, que el CSS alterna en pantallas angostas. */
      partes.push(`<text x="${x + cw / 2}" y="${m.a + H + 16}" text-anchor="middle" class="k-eje k-largo">${escSvg(PB?.BLOQUE_LABEL?.[b] || b)}</text><text x="${x + cw / 2}" y="${m.a + H + 16}" text-anchor="middle" class="k-eje k-corto">${ROTULO_CORTO[b]}</text>`);
    });
    const y1 = yDe(MISMO_TERRENO[1]), y0 = yDe(MISMO_TERRENO[0]);
    partes.push(`<rect x="${m.i}" y="${y1}" width="${W}" height="${y0 - y1}" class="k-franja"/>`);
    [[4, '×4'], [2, '×2'], [1, '×1'], [.5, '×½'], [.25, '×¼']].forEach(([v, t]) => partes.push(`<text x="${m.i - 6}" y="${yDe(v) + 4}" text-anchor="end" class="k-eje">${t}</text>`));
    partes.push(`<text x="${m.i + W - 4}" y="${y1 - 4}" text-anchor="end" class="k-eje">mismo terreno</text>`);
    const yNS = m.a + H + 28;
    partes.push(`<rect x="${m.i}" y="${yNS}" width="${W}" height="${franjaNS - 6}" class="k-ns"/><text x="${m.i + 6}" y="${yNS + 17}" class="k-eje">No sabemos · aval amplio o sin línea nacional</text>`);
    /* Se dibujan de menor a mayor presión: los importantes quedan encima. */
    lista.slice().sort((a, b) => a.presion - b.presion).forEach(r => {
      const rad = 3 + 13 * Math.sqrt((r.votos || 0) / maxV);
      let x, y;
      if (r.familia.sabemos && orden.includes(r.familia.bloque)) {
        x = m.i + orden.indexOf(r.familia.bloque) * cw + cw * (.15 + .7 * hash(r.key));
        y = r.afinidad == null ? yDe(1) : yDe(r.afinidad);
      } else { x = m.i + 150 + (W - 170) * hash(r.key); y = yNS + (franjaNS - 6) / 2; }
      const ve = visibles.has(r.key), color = col[r.familia.sabemos ? r.familia.bloque : 'sc'] || '#667068';
      const cls = `k-punto${r.nivel ? ' n-' + r.nivel : ''}${r.afinidad == null ? ' sin-af' : ''}${vitrina && !ve ? ' vitrina-blur' : ''}`;
      const titulo = vitrina && !ve ? '' : `<title>${escSvg(corto(r.nombre))} · ${escSvg(FRANJA_TXT[r.franja])}${r.afinidad != null ? ` (×${r.afinidad.toFixed(2).replace('.', ',')})` : ''} · ${Number(r.votos || 0).toLocaleString('es-CO')} votos</title>`;
      partes.push(`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${rad.toFixed(1)}" fill="${color}" class="${cls}"${clic && !(vitrina && !ve) ? ` data-key="${escSvg(r.key)}" tabindex="0"` : ''}>${titulo}</circle>`);
      if (ve) partes.push(`<text x="${(x + rad + 3).toFixed(1)}" y="${(y + 4).toFixed(1)}" class="k-nombre">${escSvg(corto(r.nombre))}</text>`);
    });
    partes.push('</svg>');
    return partes.join('');
  }

  global.C360Contendientes = {
    ORDEN, CERCANIA_PASOS, CERCANIA_NO_SABEMOS, CERCANO, MISMO_TERRENO, UMBRAL_LISTA, UMBRAL_UNINOMINAL, MIN_VALIDOS_PUESTO, MIN_VOTOS_BASE, MIN_BASE, TOP_PLANO, VITRINA, MAX_OTRAS, MAX_OTRAS_JAL,
    familia, familiaCampana, pasos, cercania, llavePersona, llaveCand, codigoDeSlug, matrizDeSlug, esCongresista, codigoPuesto,
    matrizDesdeArchivos, matrizDesdeMesas, baseDesdeMesas, afinidad, correlacion, franja, presion, niveles, disputa,
    fuentesDelReparto, escalera, evaluar, candidatasOtras, territorioDe, cargar,
    S3, INDICES_C, registroC, congresistas, completarCampana, leer, categoria, bandaRivales, disputaPorUnidad, centroide, rellenos, RELLENO_MAX_KM, planoSVG, sello, corto, FUENTE_TXT, FRANJA_TXT, NIVEL_TXT, MARCA_TXT, AVISO_TXT,
    sinDatos, DIAS_PRENSA, MESES_PRENSA, mencionaPersona, consultasPrensa, prensaDe, buscarPrensa, terrKey, proximaRevision, fechaLarga, cambiosTexto, integrarRevision,
  };
})(typeof window !== 'undefined' ? window : globalThis);
