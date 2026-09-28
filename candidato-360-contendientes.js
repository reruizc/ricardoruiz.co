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
  const MAX_OTRAS = 40;                    /* rivales de otras elecciones cuyo archivo se baja */
  const AVISO_PAREJO = .8;                 /* ≥ 80 % de los rivales en la franja → territorio parejo */

  const S3_FALLBACK = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output';
  const S3 = (global.RRData && typeof global.RRData.publicUrl === 'function') ? global.RRData.publicUrl('congreso-2026/output') : S3_FALLBACK;

  const pad = (v, n) => String(v ?? '').replace(/\D/g, '').padStart(n, '0');
  const norm = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().replace(/[^A-Z0-9]+/g, ' ').trim();
  const llaveCand = (nombre, partido) => `${norm(nombre)}|${norm(partido)}`;
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
    const validos = new Map(), info = new Map(), porCand = new Map(), listas = new Map();
    (archivos || []).forEach(({ d, mun, nombre }) => {
      if (!d) return;
      const dep2 = pad(d.dde, 2), mun3 = pad(d.mme || mun, 3);
      const partidos = (d.partidos || []).map(p => p[0]);
      (d.puestos || []).forEach(pu => {
        const [zon, pue] = String(pu.code || '').split('-');
        if (!zon || !pue || ['90', '98'].includes(zon)) return;
        const code = dep2 + mun3 + pad(zon, 2) + String(pue).trim().toUpperCase().padStart(2, '0');
        validos.set(code, (validos.get(code) || 0) + Number(pu.validos || 0));
        if (!info.has(code)) info.set(code, { nombre: pu.nombre || '', barrio: pu.barrio || '', unidad: nombre || d.name || '', lat: pu.lat, lon: pu.lon });
        (pu.v || []).forEach(([i, v]) => {
          const c = (d.cands || [])[i]; if (!c || !v) return;
          const k = llaveCand(c[0], partidos[c[1]]);
          if (!porCand.has(k)) porCand.set(k, { nombre: c[0], partido: partidos[c[1]] || '', porPuesto: new Map(), total: 0 });
          const x = porCand.get(k); x.porPuesto.set(code, (x.porPuesto.get(code) || 0) + v); x.total += v;
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
    return { validos, info, porCand, listas, origen: 'matriz' };
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
    const a = af == null ? 1 : Math.min(AFINIDAD_TOPE, af) / AFINIDAD_TOPE;
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
  function disputa(base, datos, cercanos, opts = {}) {
    const umbral = opts.umbral !== false;
    const VAL = totalValidos(datos);
    const R = new Map(); let RT = 0;
    cercanos.forEach(pp => pp.forEach((v, code) => { if (datos.validos.get(code)) { R.set(code, (R.get(code) || 0) + v); RT += v; } }));
    const conteo = { fortaleza: 0, disputa: 0, 'terreno-rivales': 0, 'terreno-ajeno': 0, 'sin-base': 0, poco: 0 };
    const puestos = [];
    datos.validos.forEach((val, code) => {
      const b = base?.porPuesto.get(code) || 0;
      const iR = RT ? ((R.get(code) || 0) / val) / (RT / VAL) : null;
      const iU = base?.total ? (b / val) / (base.total / VAL) : null;
      let cat;
      if (umbral && val < MIN_VALIDOS_PUESTO) cat = 'poco';
      else if (!b) cat = 'sin-base';
      else if (umbral && b < MIN_VOTOS_BASE) cat = 'poco';
      else if (iR == null) cat = iU >= 1 ? 'fortaleza' : 'terreno-ajeno';
      else cat = iU >= 1 ? (iR >= 1 ? 'disputa' : 'fortaleza') : (iR >= 1 ? 'terreno-rivales' : 'terreno-ajeno');
      conteo[cat]++;
      puestos.push({ code, cat, iU, iR, votos: b, validos: val, ...(datos.info.get(code) || {}) });
    });
    /* La segunda capa solo tiene sentido si la base cubre una parte chica del
       territorio (el salto de JAL a Concejo: 31 de 943 puestos). */
    const cobertura = datos.validos.size ? (base?.puestos || 0) / datos.validos.size : 0;
    return { puestos, conteo, cobertura, dosCapas: cobertura < .5, rivalesVotos: RT };
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
      const x = datos.porCand.get(llaveCand(row.nombre, row.partido));
      añadir(row, f, x ? x.porPuesto : null, x ? x.total : Number(row.votos || 0));
    });
    /* Fuente C: otras elecciones con votos en el territorio (ya recortados). */
    const refC = F.referencia;
    (ctx.otras || []).forEach(o => {
      if (esUsuario(o.entrada) || !refC || o.total < refC) return;
      añadir(o.entrada, ['C'], o.porPuesto || null, o.total);
    });

    const rivales = [...porPersona.values()].map(r => {
      const e = r.actual, fam = familia(e.partido, e.nombre);
      const af = r.porPuesto ? afinidad(ctx.base, r.porPuesto, r.votos, datos, VAL) : null;
      const cer = fu ? cercania(fu, fam) : CERCANIA_NO_SABEMOS;
      const marcas = [];
      if (F.titular && r.entradas.some(x => x.slug === F.titular)) marcas.push('titular-no-reelegible');
      if (esCongresista(e.nombre, ctx.congresistas)) marcas.push('congresista-2026');
      const partidos = new Set(r.entradas.map(x => norm(x.partido)));
      if (partidos.size > 1) marcas.push('cambio-de-partido');
      const enIndice = !marcas.includes('titular-no-reelegible') && !marcas.includes('congresista-2026');
      return {
        key: r.key, nombre: e.nombre, partido: e.partido || '', slug: e.slug, corp: e.corp || '', anio: anio(e),
        familia: fam, pasos: fu && fam.sabemos ? pasos(fu, fam.bloque) : null, cercania: cer,
        fuentes: ['A', 'B', 'C'].filter(f => r.fuentes.has(f)), votos: r.votos,
        afinidad: af, franja: franja(af), correlacion: r.porPuesto ? correlacion(ctx.base, r.porPuesto, datos) : null,
        presion: presion({ cercania: cer, afinidad: af, votos: r.votos, meta: ctx.meta }),
        marcas, enIndice, porPuesto: r.porPuesto,
        entradas: r.entradas.map(x => ({ slug: x.slug, nombre: x.nombre, corp: x.corp, partido: x.partido, votos: x.votos })),
      };
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
    const rep = await global.VoteTarget.reparto({ corp, territory: territorioDe(alcance, campana), baseUrl, codigo }).catch(() => null);
    const urlDe = c => c.dataUrl || (global.CandRegistry ? global.CandRegistry.dataUrlFor(c.slug) : `${baseUrl}/${c.slug}.json`);

    /* La matriz, si existe para ESTA corporación. */
    let datos = null;
    if (CON_MATRIZ.includes(corp)) {
      const destino = await (deps.puestosDestino || global.C360DiaD?.puestosDestino)?.(campana).catch(() => null);
      if (destino && destino.fuente === corp && destino.archivos.length) datos = matrizDesdeArchivos(destino.archivos);
    }
    if (!datos) {
      const filas = (rep?.rows || []).filter(r => Number(r.votos || 0) > 0);
      const partes = await enTandas(filas.map(r => () => leerMesas(urlDe(r)).then(mesas => ({ entrada: r, mesas }))));
      const tot = await leerTotales(TOTALES[corp]).catch(() => ({}));
      datos = matrizDesdeMesas(partes.filter(Boolean), tot, dentro);
    }

    /* Fuente C. */
    const excluir = new Set((rep?.rows || []).map(r => r.slug));
    let otras = [];
    const ref = fuentesDelReparto(rep).referencia;
    if (ref) {
      const cand = candidatasOtras(deps.registro, alcance, corp, excluir).filter(c => Number(c.votos || 0) >= ref)
        .sort((a, b) => b.votos - a.votos).slice(0, MAX_OTRAS);
      const partes = await enTandas(cand.map(c => () => leerMesas(urlDe(c)).then(mesas => ({ c, mesas }))));
      otras = partes.filter(Boolean).map(({ c, mesas }) => {
        const pp = new Map(); let total = 0;
        mesas.forEach(m => { if (dentro && !dentro(m)) return; const v = Number(m.v || 0); if (!v) return; const k = codigoPuesto(m); pp.set(k, (pp.get(k) || 0) + v); total += v; });
        return { entrada: c, porPuesto: pp, total };
      });
    }

    /* La base: la propia recortada; si no alcanza, la de su familia. */
    let base = baseDesdeMesas(deps.mesasPropias, datos, dentro), baseModo = null;
    const mismaCorp = (deps.slugsPropios || []).some(s => ({ JAL: 'jal', CONC: 'concejo', ALC: 'alcaldia', ASAM: 'asamblea', GOB: 'gobernacion' })[String(s).match(/^[A-Z]+/)?.[0]] === corp);
    if (baseSuficiente(base)) baseModo = mismaCorp ? 'propio' : 'salto';
    else if (deps.mesasFamilia) { base = baseDesdeMesas(deps.mesasFamilia, datos, null); baseModo = baseSuficiente(base) ? 'familia' : null; }
    if (!baseModo) base = null;

    return { corp, reparto: rep, datos, base, baseModo, otras, alcance };
  }

  global.C360Contendientes = {
    ORDEN, CERCANIA_PASOS, CERCANIA_NO_SABEMOS, CERCANO, MISMO_TERRENO, UMBRAL_LISTA, UMBRAL_UNINOMINAL, MIN_VALIDOS_PUESTO, MIN_VOTOS_BASE, MIN_BASE, TOP_PLANO, VITRINA, MAX_OTRAS,
    familia, familiaCampana, pasos, cercania, llavePersona, esCongresista, codigoPuesto,
    matrizDesdeArchivos, matrizDesdeMesas, baseDesdeMesas, afinidad, correlacion, franja, presion, niveles, disputa,
    fuentesDelReparto, escalera, evaluar, candidatasOtras, territorioDe, cargar,
  };
})(typeof window !== 'undefined' ? window : globalThis);
