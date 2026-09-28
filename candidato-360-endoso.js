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
  /* Generado por tools/candidato-360/endoso/calibrar.mjs el 2026-09-28: [p25, mediana, p75, n] por corporación y años de distancia. No editar a mano: volver a correr el script. */
  const RETENCION = {"jal":{"4":[0.308,0.656,0.829,1198],"8":[0.087,0.516,0.766,796],"12":[0,0.384,0.689,398]},"concejo":{"4":[0.467,0.705,0.866,1178],"8":[0.362,0.65,0.856,772],"12":[0.257,0.555,0.787,379]},"alcaldia":{"4":[0.662,0.89,0.957,1190],"8":[0.365,0.744,0.915,784],"12":[0.23,0.684,0.897,390]},"asamblea":{"4":[0.429,0.56,0.664,1198],"8":[0.326,0.463,0.566,586],"12":[0.221,0.377,0.491,168]},"gobernacion":{"4":[0.545,0.726,0.805,39],"8":[0.253,0.62,0.695,21],"12":[0.219,0.427,0.467,3]},"camara":{"4":[0.432,0.575,0.676,308],"8":[0.331,0.49,0.566,75]},"senado":{"4":[0.134,0.268,0.476,256],"8":[0.091,0.144,0.314,53]},"_todas":{"4":[0.416,0.643,0.854,5367],"8":[0.282,0.552,0.804,3087],"12":[0.155,0.483,0.781,1338]}};
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
     candidatura de 2022 cae en la de 4 años). Con menos de 20 casos propios,
     o sin una distancia propia cercana, se usa la de todas las corporaciones juntas: presidencia y consultas no
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
  function retencionDe(c, T = RETENCION) {
    const a = anio(c), g = a ? Math.max(1, AÑO_ELECCION - a) : 4, cp = corpRetencion(c);
    /* La propia solo si midió una distancia parecida (±2 años: el Congreso
       de 2022 está a 5 de 2027 y se midió a 4). Un edil de 2015 está a 12, y
       usar la de 8 porque es la única que hay subestimaría el desgaste. */
    let k = cercana(T[cp], g), tabla = T[cp], propia = true;
    if (k == null || Math.abs(k - g) > 2) { k = cercana(T._todas, g); tabla = T._todas; propia = false; }
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

  /* ── La regresión ecológica (fase 4) ──────────────────────────────────
     Σ min dice cuánto electorado PUDIERON compartir; la regresión estima
     cuánto compartieron. Puesto por puesto, con la participación de cada uno
     sobre los válidos de SU elección:
         part_apoyado = α + β · part_aliado
     α es cuánto del resto del electorado votó por el apoyado, y α + β, cuánto
     de quienes votaron por el aliado lo hizo (Goodman). Los puestos donde el
     aliado sacó cero votos cuentan: por eso hacen falta los totales por puesto
     (tools/candidato-360/endoso/build_totales_puesto.py, en S3 en
     totales-puesto/{corp}-{año}.json), que los archivos de candidatura no traen.

     Dos cosas que no se negocian:
     · El universo son los puestos donde LOS DOS estaban en el tarjetón: el
       municipio (JAL: la zona, que en Bogotá es la localidad), el
       departamento o el país según la corporación. Meter puestos donde uno de
       los dos no existía pone ceros que no son de nadie.
     · Mide votantes COMPARTIDOS, no convencidos: si el aliado y el apoyado
       son de la misma corriente, parte de α + β es afinidad y no endoso. Es
       mejor estimación central que Σ min, pero sigue sin ser causal. */
  const S3_OUT = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output';
  const totalesCache = new Map();
  function totales(nombre) {
    if (!totalesCache.has(nombre)) totalesCache.set(nombre, fetch(`${S3_OUT}/totales-puesto/${nombre}.json`).then(r => r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status))).then(d => d.puestos || {}).catch(e => { totalesCache.delete(nombre); throw e; }));
    return totalesCache.get(nombre);
  }
  /* Qué archivo de totales es cada candidatura y a qué escala compite. El
     orden importa: CONC es concejo y CON es Congreso. */
  function eleccionDe(c) {
    const s = String(c?.slug || '');
    let m = s.match(/^(JAL|CONC|ALC|ASAM|GOB)(\d{4})-/);
    if (m) return { totales: `${{ JAL: 'jal', CONC: 'concejo', ALC: 'alcaldia', ASAM: 'asamblea', GOB: 'gobernacion' }[m[1]]}-${m[2]}`, escala: { JAL: 'zona', CONC: 'mun', ALC: 'mun', ASAM: 'dep', GOB: 'dep' }[m[1]] };
    m = s.match(/^CON(\d{4})-(SI|S|CA|CI|CE|CT|C)-/);
    if (m) return { totales: `${m[2].startsWith('S') ? 'senado' : 'camara'}-${m[1]}`, escala: m[2] === 'C' ? 'dep' : 'nac' };
    return null;
  }
  const ambitoDe = (m, escala) => escala === 'nac' ? '' : escala === 'dep' ? pad(m.dep, 2) : escala === 'mun' ? pad(m.dep, 2) + pad(m.mun, 3) : pad(m.dep, 2) + pad(m.mun, 3) + pad(m.zon, 2);
  const ambitoCodigo = (k, escala) => escala === 'nac' ? '' : k.slice(0, escala === 'dep' ? 2 : escala === 'mun' ? 5 : 7);
  const MIN_PUESTOS = 20, MAX_ERROR = .15;   /* ± 29 puntos con 1,96 errores */
  async function regresion(aliado, opts = {}) {
    const leer = opts.mesasDe || mesas, leerTotales = opts.totalesDe || totales;
    if (clase(aliado, aliado.apoyo) === 'mismo') return null;
    const ea = eleccionDe(aliado), eb = eleccionDe(aliado.apoyo);
    if (!ea || !eb) return { valida: false, motivo: 'no tenemos los totales por puesto de esa elección' };
    let ma, mb, TA, TB;
    try { [ma, mb, TA, TB] = await Promise.all([leer(aliado.dataUrl), leer(aliado.apoyo.dataUrl), leerTotales(ea.totales), leerTotales(eb.totales)]); }
    catch { return { valida: false, motivo: 'no se pudieron leer los totales por puesto' }; }
    const ambA = new Set(ma.filter(m => Number(m.v) > 0).map(m => ambitoDe(m, ea.escala))), ambB = new Set(mb.filter(m => Number(m.v) > 0).map(m => ambitoDe(m, eb.escala)));
    const A = {}, B = {}; ma.forEach(m => { const k = codigoPuesto(m); A[k] = (A[k] || 0) + Number(m.v || 0); }); mb.forEach(m => { const k = codigoPuesto(m); B[k] = (B[k] || 0) + Number(m.v || 0); });
    const obs = [];
    for (const k of Object.keys(TA)) {
      const ta = TA[k], tb = TB[k];
      if (!tb || !ta[0] || !tb[0] || !ambA.has(ambitoCodigo(k, ea.escala)) || !ambB.has(ambitoCodigo(k, eb.escala))) continue;
      obs.push([(A[k] || 0) / ta[0], (B[k] || 0) / tb[0], tb[0]]);
    }
    const n = obs.length;
    if (n < MIN_PUESTOS) return { valida: false, n, motivo: `solo ${n} puestos donde los dos estaban en el tarjetón: muy pocos para una regresión` };
    /* Mínimos cuadrados ponderados por los válidos del apoyado. */
    const W = obs.reduce((s, o) => s + o[2], 0), xm = obs.reduce((s, o) => s + o[0] * o[2], 0) / W, ym = obs.reduce((s, o) => s + o[1] * o[2], 0) / W;
    let sxx = 0, sxy = 0; obs.forEach(([x, y, w]) => { sxx += w * (x - xm) ** 2; sxy += w * (x - xm) * (y - ym); });
    if (!(sxx > 0)) return { valida: false, n, motivo: 'la votación del aliado no varía entre puestos: no hay con qué estimar' };
    const beta = sxy / sxx, alfa = ym - beta * xm, tau = alfa + beta;
    /* Error estándar de α + β = ȳ + β(1 − x̄), con los pesos llevados a media 1. */
    const wm = W / n; let see = 0; obs.forEach(([x, y, w]) => { see += (w / wm) * (y - alfa - beta * x) ** 2; });
    const s2 = see / (n - 2), varB = s2 / (sxx / wm), error = Math.sqrt(s2 / n + (1 - xm) ** 2 * varB);
    const base = { n, alfa, beta, tau, error, xm, ym };
    if (tau < -.05 || tau > 1.05) return { ...base, valida: false, motivo: `la regresión da ${Math.round(tau * 100)} %, fuera de lo posible: los dos votan en puestos que no se separan bien` };
    if (error > MAX_ERROR) return { ...base, valida: false, motivo: `la estimación es muy imprecisa (± ${Math.round(1.96 * error * 100)} puntos)` };
    return { ...base, tau: Math.min(1, Math.max(0, tau)), valida: true };
  }

  /* ── La lectura completa ───────────────────────────────────────────────
     opts:
       alcance    el territorio de la campaña (o null: sin recorte)
       lugar      cómo se nombra ese territorio en el texto
       enAlcance  (mesa, alcance) → bool; el recorte por código electoral
       areaDe     (mesa, alcance) → nombre del área donde se concentra
       propio     mesas del historial del candidato, para medir el solape
       mesasDe    url → Promise<mesas>; por defecto el fetch con caché
       retencion  otra tabla de retención (las pruebas); por defecto la medida
       totalesDe  nombre → Promise<{puesto: [válidos, votantes, blanco]}>; las pruebas
       corpCampana la corporación a la que se lanza (jal, concejo, alcaldia,
                   asamblea, gobernacion): de ahí sale el electorado de cada
                   puesto para no contar dos veces a los aliados */
  async function evaluar(aliados, opts = {}) {
    const { alcance = null, lugar = 'su territorio', enAlcance, areaDe, mesasDe = mesas } = opts;
    const propio = opts.propio ? agrupar(opts.propio, llavePuesto) : null;
    const filas = await Promise.all((aliados || []).map(async al => {
      try {
        const ms = await mesasDe(al.dataUrl), dentro = alcance && enAlcance ? ms.filter(m => enAlcance(m, alcance)) : ms;
        const fila = { al, total: suma(ms), terr: suma(dentro), dentro, par: null };
        if (al.apoyo) {
          try { fila.par = await medirPar(al, { mesasDe }); } catch (e) { fila.par = { valida: false, motivo: 'no se pudo leer la votación de a quién apoyó' }; }
          try { fila.reg = await regresion(al, { mesasDe, totalesDe: opts.totalesDe }); } catch (e) { fila.reg = { valida: false, motivo: 'no se pudo calcular la regresión' }; }
        }
        if (propio && fila.terr) { const pa = agrupar(dentro, llavePuesto); let s = 0; Object.entries(pa).forEach(([k, v]) => { s += Math.min(v, propio[k] || 0); }); fila.solape = s / fila.terr; }
        return fila;
      } catch (e) { return { al, error: true }; }
    }));
    const medidas = filas.filter(f => f.par?.valida).map(f => f.par.tasa).sort((a, b) => a - b), nM = medidas.length;
    const mediana = !nM ? null : nM % 2 ? medidas[(nM - 1) / 2] : (medidas[nM / 2 - 1] + medidas[nM / 2]) / 2;
    let techo = 0; const sumas = [0, 0, 0];
    filas.forEach(f => {
      if (f.error) return;
      f.ret = retencionDe(f.al, opts.retencion || RETENCION);
      let r;
      if (Number.isFinite(f.al.manual)) { const t = f.al.manual / 100; r = [t, t, t]; f.fuente = 'suya'; }
      else if (f.reg?.valida) {
        /* La regresión da el centro y el piso (menos 1,96 errores); el techo
           sigue siendo Σ min si el par se pudo medir, y todo queda acotado
           por la retención de su nivel. */
        const techoPar = f.par?.valida ? f.par.tasa : 1, q = f.ret?.q || [1, 1, 1];
        r = [Math.min(Math.max(0, f.reg.tau - 1.96 * f.reg.error), q[0]), Math.min(f.reg.tau, q[1]), Math.min(techoPar, q[2])].sort((a, b) => a - b);
        f.fuente = 'regresion';
      }
      else if (f.par?.valida && f.ret) { r = f.ret.q.map(q => Math.min(f.par.tasa, q)); f.fuente = 'medida'; }
      else if (f.par?.valida) { r = [f.par.tasa, f.par.tasa, f.par.tasa]; f.fuente = 'medida'; }
      else if (f.ret) { r = f.ret.q.slice(); f.fuente = 'retencion'; }
      else { r = [SUPUESTO, SUPUESTO, SUPUESTO]; f.fuente = 'supuesto'; }
      [f.tasaBaja, f.tasa, f.tasaAlta] = r;
      f.estBajo = Math.round(f.terr * r[0]); f.est = Math.round(f.terr * r[1]); f.estAlto = Math.round(f.terr * r[2]);
      sumas[0] += f.estBajo; sumas[1] += f.est; sumas[2] += f.estAlto; techo += f.terr;
    });

    /* ── Sin contar dos veces (fase 5) ───────────────────────────────────
       Dos aliados que trabajan el mismo puesto no le pasan la suma de los
       dos: parte de quienes votaron por uno también votaron por el otro. Por
       puesto, con V = el electorado del puesto, lo que llega es
           V · (1 − Π (1 − e_i / V))
       la probabilidad de que un votante sea alcanzado por al menos uno,
       suponiendo que alcanzan a gente independiente. Con aportes chicos frente
       a V es casi la suma; con dos aliados fuertes en el mismo puesto, bastante
       menos. Si los dos son de la misma corriente el solape real es MAYOR que
       este, así que la unión sigue siendo generosa.
       V son los votos válidos de 2023 de la corporación a la que se lanza la
       campaña (totales-puesto/{corp}-2023.json). Sin ese dato, en ese puesto
       se suma, y se cuenta cuántos votos quedaron así. */
    let den = null;
    if (opts.corpCampana) { try { den = await (opts.totalesDe || totales)(`${opts.corpCampana}-2023`); } catch { den = null; } }
    const porK = new Map();
    filas.forEach((f, i) => {
      if (f.error || !f.terr) return;
      f.dentro.forEach(m => {
        const v = Number(m.v || 0); if (!v) return;
        const k = codigoPuesto(m);
        if (!porK.has(k)) porK.set(k, { code: k, nombre: m.pueNom || '', munNom: m.munNom || '', comNom: nombreLocal(m), area: areaDe ? areaDe(m, alcance) : '', votos: 0, e: {} });
        const p = porK.get(k); p.votos += v;
        const e = p.e[i] || (p.e[i] = [0, 0, 0]); e[0] += v * f.tasaBaja; e[1] += v * f.tasa; e[2] += v * f.tasaAlta;
      });
    });
    /* El extremo opuesto, para decirlo junto: si en cada puesto los votantes de
       los aliados fueran LOS MISMOS, solo contaría el aporte del más fuerte. La
       unión supone lo contrario (gente independiente); la verdad está entre los
       dos, más cerca de este cuando los aliados son de la misma corriente. */
    const union = [0, 0, 0], porArea = {}; let sinDen = 0, votosSinDen = 0, siSeRepiten = 0;
    const puestos = [...porK.values()].map(p => {
      const V = den?.[p.code]?.[0] || 0, aportes = Object.values(p.e);
      const u = [0, 1, 2].map(l => {
        const s = aportes.reduce((t, e) => t + e[l], 0);
        if (!V || aportes.length === 1) return s;
        return V * (1 - aportes.reduce((t, e) => t * (1 - Math.min(1, e[l] / V)), 1));
      });
      if (!V && aportes.length > 1) { sinDen++; votosSinDen += u[1]; }
      siSeRepiten += Math.max(...aportes.map(e => e[1]));
      u.forEach((x, l) => { union[l] += x; });
      if (p.area) porArea[p.area] = (porArea[p.area] || 0) + u[1];
      /* porAliado en la escala de la unión: cada uno con su parte proporcional. */
      const sMed = aportes.reduce((t, e) => t + e[1], 0) || 1, porAliado = {};
      Object.entries(p.e).forEach(([i, e]) => { porAliado[i] = e[1] / sMed * u[1]; });
      return { code: p.code, nombre: p.nombre, munNom: p.munNom, comNom: p.comNom, votos: p.votos, V, total: u[1], bajo: u[0], alto: u[2], suma: aportes.reduce((t, e) => t + e[1], 0), aliados: aportes.length, porAliado };
    }).sort((a, b) => b.total - a.total);
    const areas = Object.entries(porArea).map(([nombre, v]) => ({ nombre, v: Math.round(v) })).filter(a => a.v > 0).sort((a, b) => b.v - a.v);
    const [bajo, total, alto] = union.map(Math.round);
    return { alcance, lugar, filas, total, bajo, alto, techo, mediana, nMedidas: nM, areas, puestos,
      suma: { bajo: sumas[0], total: sumas[1], alto: sumas[2] }, dobleConteo: sumas[1] - total, siSeRepiten: Math.round(siSeRepiten),
      denominador: den ? `${opts.corpCampana}-2023` : null, sinDenominador: { puestos: sinDen, votos: Math.round(votosSinDen) } };
  }

  /* ── Cuánto se pisan dos aliados ───────────────────────────────────────
     Para cada par: qué parte de los votos del más chico cae en puestos donde
     el otro también saca votos, Σ min(a, b) ÷ min(Σa, Σb), dentro del
     territorio. 100 % = el chico vive dentro de la huella del grande; 0 % =
     no comparten un solo puesto. Es geografía, no votantes: dice dónde puede
     haber doble conteo, no cuánto lo hay. */
  function solapes(lectura) {
    const fs = (lectura?.filas || []).map((f, i) => ({ f, i })).filter(({ f }) => !f.error && f.terr > 0);
    const por = fs.map(({ f }) => agrupar(f.dentro, codigoPuesto));
    const out = [];
    for (let a = 0; a < fs.length; a++) for (let b = a + 1; b < fs.length; b++) {
      const A = por[a], B = por[b]; let m = 0, puestos = 0;
      Object.entries(A).forEach(([k, v]) => { const w = B[k] || 0; if (w) { m += Math.min(v, w); puestos++; } });
      out.push({ i: fs[a].i, j: fs[b].i, coincidencia: m / Math.min(fs[a].f.terr, fs[b].f.terr), puestos });
    }
    return out.sort((x, y) => y.coincidencia - x.coincidencia);
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
    if (lectura?.puestos) return lectura.puestos;   /* ya viene con la unión (fase 5) */
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
    regresion: 'estimada puesto a puesto con a quién apoyó',
    supuesto: 'supuesto: escriba el suyo o mida el par',
  };
  const CLASE = {
    cota: 'misma jornada, tarjetón distinto: cota superior',
    transferencia: 'elecciones distintas: transferencia entre fechas, comparada por puesto',
  };

  global.C360Endoso = { SUPUESTO, SATURACION, MAX, FUENTE, CLASE, anio, corp, clase, ficha, mesas, suma, llavePuesto, llaveMesa, agrupar, medirPar, regresion, eleccionDe, evaluar, solapes, retencionDe, corpRetencion, RETENCION,
    enAlcance, areaDe, corpHistorica, municipioMayoritario, alcanceDe, codigoPuesto, porPuesto, clave, candidaturaId, cargar, guardar };
})(typeof window !== 'undefined' ? window : globalThis);
