/* ─────────────────────────────────────────────────────────────────────────
   cand-index.js — Registro compartido de candidatos con datos mesa-a-mesa.

   Base única para analisis-candidato.html, endoso-2026.html y
   comparar-candidatos.html. Fusiona los índices de las distintas candidaturas
   (endoso = Congreso + Consultas, Asamblea 2023, …) en una sola lista con un
   `dataUrl` por candidato, y resuelve slug → URL del JSON mesa-a-mesa.

   PARA AMPLIAR A MÁS CANDIDATURAS (concejos, JAL, etc.): agregar una entrada a
   SOURCES con { name, dir, indexFile, list }. Todas las páginas la reciben
   automáticamente — no hay que tocar cada HTML.

   Nota: los presidenciales (1V/2V con histórico por persona) NO están aquí;
   son un modelo por-persona propio de analisis-candidato.html, que los agrega
   encima de esta base.
   ───────────────────────────────────────────────────────────────────────── */
(function (global) {
  'use strict';

  const S3 = 'https://elecciones-2026.s3.us-east-1.amazonaws.com/ricardoruiz.co/congreso-2026/output';

  // Cada fuente vive en `${S3}/${dir}/`: el índice es `${dir}/${indexFile}` y
  // cada candidato es `${dir}/${slug}.json`. `list(raw)` extrae el array de
  // candidatos del JSON del índice (endoso es un array plano; asamblea lo
  // envuelve en {candidatos:[…]}).
  const SOURCES = [
    { name: 'endoso',   dir: 'endoso',        indexFile: 'index.json',                    list: d => Array.isArray(d) ? d : (d.candidatos || []) },
    { name: 'asamblea', dir: 'asamblea-2023', indexFile: 'index-asamblea-2023.json',       list: d => d.candidatos || [] },
    { name: 'con2018',  dir: 'congreso-2018', indexFile: 'index-congreso-2018.json',       list: d => d.candidatos || [] },
  ];

  const _bySlug = {};   // slug → entrada (para dataUrlFor)

  function isPartyEntry(c) {
    if (!c || !c.nombre) return false;
    if (c.tipo === 'partido') return true;
    if (c.nombre === c.partido) return true;
    const n = c.nombre.normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase();
    return /^(PARTIDO|MOVIMIENTO|COALICION|ALIANZA|LISTA|PACTO)\b/.test(n);
  }

  // Búsqueda tolerante: cada palabra del query debe prefijar alguna del nombre.
  function acMatch(q, nombre) {
    const norm = s => (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().trim();
    const words = norm(q).split(/\s+/).filter(Boolean);
    const tw = norm(nombre).split(/\s+/);
    return words.every(w => tw.some(t => t.startsWith(w)));
  }

  // Carga y fusiona todas las fuentes. Tolerante a 404: una fuente caída no
  // rompe el resto (útil mientras se sube una candidatura nueva a S3).
  //   opts.bases   → { <name>: '<baseUrl>' } override del base por fuente
  //                  (p.ej. rutas locales para verificación pre-subida).
  //   opts.includeParties=false → filtra entradas de partido.
  async function load(opts) {
    opts = opts || {};
    const bases = opts.bases || {};
    const perSource = await Promise.all(SOURCES.map(async src => {
      const base = bases[src.name] || `${S3}/${src.dir}`;
      try {
        const r = await fetch(`${base}/${src.indexFile}`);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const raw = await r.json();
        return src.list(raw).map(c => ({
          nombre: c.nombre,
          slug: c.slug,
          corp: c.corp || '',
          circunscripcion: c.circunscripcion || '',
          partido: c.partido || '',
          votos: c.votos || 0,
          tipo: c.tipo || 'candidato',
          source: src.name,
          dataUrl: `${base}/${c.slug}.json`,
        }));
      } catch (e) {
        console.warn(`[CandRegistry] fuente "${src.name}" no disponible:`, e.message);
        return [];
      }
    }));
    let all = perSource.flat();
    // Indexar TODO por slug (incluidos partidos) para resolver dataUrl siempre.
    all.forEach(c => { _bySlug[c.slug] = c; });
    if (opts.includeParties === false) all = all.filter(c => !isPartyEntry(c));
    return all;
  }

  // slug → URL del JSON mesa-a-mesa. Cae a la ruta endoso si el slug no se
  // cargó por el registro (compatibilidad hacia atrás).
  function dataUrlFor(slug) {
    return (_bySlug[slug] && _bySlug[slug].dataUrl) || `${S3}/endoso/${slug}.json`;
  }

  global.CandRegistry = { S3, SOURCES, isPartyEntry, acMatch, load, dataUrlFor };
})(typeof window !== 'undefined' ? window : this);
