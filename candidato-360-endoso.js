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
      no cuánto compartieron. Por eso todo se presenta como «hasta».
   Sin medición la tasa es la mediana de los aliados medidos o, si no hay
   ninguno, un supuesto editable que queda rotulado como supuesto.

   Sin dependencias del CRM ni del DOM: se prueba en Node con
   tools/candidato-360/prueba-endoso.mjs.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';

  const SUPUESTO = .3, SATURACION = .95, MAX = 25;

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
    const medidas = filas.filter(f => f.par?.valida).map(f => f.par.tasa).sort((a, b) => a - b);
    const mediana = medidas.length ? medidas[Math.floor((medidas.length - 1) / 2)] : null;
    let total = 0, techo = 0; const porArea = {};
    filas.forEach(f => {
      if (f.error) return;
      if (f.par?.valida) { f.tasa = f.par.tasa; f.fuente = 'medida'; }
      else if (Number.isFinite(f.al.manual)) { f.tasa = f.al.manual / 100; f.fuente = 'suya'; }
      else if (mediana !== null) { f.tasa = mediana; f.fuente = 'mediana'; }
      else { f.tasa = SUPUESTO; f.fuente = 'supuesto'; }
      f.est = Math.round(f.terr * f.tasa); total += f.est; techo += f.terr;
      if (areaDe) f.dentro.forEach(m => {
        const area = areaDe(m, alcance);
        if (area) porArea[area] = (porArea[area] || 0) + Number(m.v || 0) * f.tasa;
      });
    });
    const areas = Object.entries(porArea).map(([nombre, v]) => ({ nombre, v: Math.round(v) })).filter(a => a.v > 0).sort((a, b) => b.v - a.v);
    return { alcance, lugar, filas, total, techo, mediana, nMedidas: medidas.length, areas };
  }

  /* ── Lista de aliados ──────────────────────────────────────────────────
     Vive en el navegador, por cuenta y candidatura: no cambia el vínculo, y
     el nombre de un líder de zona es un dato de un tercero que no tenemos
     por qué custodiar. */
  const clave = (correo, candidatura) => `c360-aliados:${String(correo || 'anon').toLowerCase()}:${candidatura || 'sin-candidatura'}`;
  function cargar(k) { try { return JSON.parse(global.localStorage.getItem(k) || '[]').slice(0, MAX); } catch { return []; } }
  function guardar(k, lista) { try { global.localStorage.setItem(k, JSON.stringify(lista)); } catch { /* sin almacenamiento: la lista vive mientras dure la pestaña */ } }

  const FUENTE = {
    medida: 'medida con a quién apoyó',
    suya: 'tasa que usted escribió',
    mediana: 'mediana de sus aliados medidos',
    supuesto: 'supuesto: escriba el suyo o mida el par',
  };
  const CLASE = {
    cota: 'misma jornada, tarjetón distinto: cota superior',
    transferencia: 'elecciones distintas: transferencia entre fechas, comparada por puesto',
  };

  global.C360Endoso = { SUPUESTO, SATURACION, MAX, FUENTE, CLASE, anio, corp, clase, ficha, mesas, suma, llavePuesto, llaveMesa, agrupar, medirPar, evaluar, clave, cargar, guardar };
})(typeof window !== 'undefined' ? window : globalThis);
