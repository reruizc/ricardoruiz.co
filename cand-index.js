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
    { name: 'asam2019', dir: 'asamblea-2019', indexFile: 'index-asamblea-2019.json',       list: d => d.candidatos || [] },
    { name: 'asam2015', dir: 'asamblea-2015', indexFile: 'index-asamblea-2015.json',       list: d => d.candidatos || [] },
    { name: 'asam2011', dir: 'asamblea-2011', indexFile: 'index-asamblea-2011.json',       list: d => d.candidatos || [] },
    // Uninominales: gobernaciones (índices de 24-41 KB) y alcaldías (~1 MB c/u).
    // Van al arranque porque son las candidaturas más buscadas del histórico
    // (Petro alcalde 2011, Fico en Medellín, Claudia López, Galán…).
    { name: 'gob2023',  dir: 'gobernacion-2023', indexFile: 'index-gobernacion-2023.json', list: d => d.candidatos || [] },
    { name: 'gob2019',  dir: 'gobernacion-2019', indexFile: 'index-gobernacion-2019.json', list: d => d.candidatos || [] },
    { name: 'gob2015',  dir: 'gobernacion-2015', indexFile: 'index-gobernacion-2015.json', list: d => d.candidatos || [] },
    { name: 'gob2011',  dir: 'gobernacion-2011', indexFile: 'index-gobernacion-2011.json', list: d => d.candidatos || [] },
    { name: 'alc2023',  dir: 'alcaldia-2023',    indexFile: 'index-alcaldia-2023.json',    list: d => d.candidatos || [] },
    { name: 'alc2019',  dir: 'alcaldia-2019',    indexFile: 'index-alcaldia-2019.json',    list: d => d.candidatos || [] },
    { name: 'alc2015',  dir: 'alcaldia-2015',    indexFile: 'index-alcaldia-2015.json',    list: d => d.candidatos || [] },
    { name: 'alc2011',  dir: 'alcaldia-2011',    indexFile: 'index-alcaldia-2011.json',    list: d => d.candidatos || [] },
    { name: 'con2014',  dir: 'congreso-2014', indexFile: 'index-congreso-2014.json',       list: d => d.candidatos || [] },
    { name: 'con2018',  dir: 'congreso-2018', indexFile: 'index-congreso-2018.json',       list: d => d.candidatos || [] },
    { name: 'con2022',  dir: 'congreso-2022', indexFile: 'index-congreso-2022.json',       list: d => d.candidatos || [] },
    { name: 'pres2010', dir: 'pres-2010',     indexFile: 'index-pres-2010.json',           list: d => d.candidatos || [] },
    { name: 'pres2014', dir: 'pres-2014',     indexFile: 'index-pres-2014.json',           list: d => d.candidatos || [] },
    { name: 'pres2018', dir: 'pres-2018',     indexFile: 'index-pres-2018.json',           list: d => d.candidatos || [] },
    { name: 'pres2022', dir: 'pres-2022',     indexFile: 'index-pres-2022.json',           list: d => d.candidatos || [] },
    { name: 'consu2022',dir: 'consu-2022',    indexFile: 'index-consu-2022.json',          list: d => d.candidatos || [] },
  ];

  // Fuentes LOCALES (Concejo · JAL 2023): índices GRANDES (~94k + ~14k candidatos).
  // NO se cargan en load() para no frenar el arranque de las páginas; se piden
  // aparte con loadLocal(), típicamente al primer foco/tecla del buscador.
  // A diferencia del resto, estas NO se agrupan por persona (nombres comunes se
  // repiten entre municipios → colapsarlas por nombre fusionaría personas distintas).
  const LOCAL_SOURCES = [
    { name: 'concejo',  dir: 'concejo-2023', indexFile: 'index-concejo-2023.json', list: d => d.candidatos || [] },
    { name: 'jal',      dir: 'jal-2023',     indexFile: 'index-jal-2023.json',     list: d => d.candidatos || [] },
    { name: 'conc2019', dir: 'concejo-2019', indexFile: 'index-concejo-2019.json', list: d => d.candidatos || [] },
    { name: 'jal2019',  dir: 'jal-2019',     indexFile: 'index-jal-2019.json',     list: d => d.candidatos || [] },
    { name: 'conc2015', dir: 'concejo-2015', indexFile: 'index-concejo-2015.json', list: d => d.candidatos || [] },
    { name: 'jal2015',  dir: 'jal-2015',     indexFile: 'index-jal-2015.json',     list: d => d.candidatos || [] },
    { name: 'conc2011', dir: 'concejo-2011', indexFile: 'index-concejo-2011.json', list: d => d.candidatos || [] },
    { name: 'jal2011',  dir: 'jal-2011',     indexFile: 'index-jal-2011.json',     list: d => d.candidatos || [] },
  ];

  const _bySlug = {};   // slug → entrada (para dataUrlFor)

  /* ── ALIAS DE PERSONA ────────────────────────────────────────────────────
     La RNEC inscribe a la misma persona con nombres distintos según la
     elección: la forma corta (1er nombre + 1er apellido) en presidenciales y
     consultas, el nombre legal completo en las territoriales. Sin esto,
     `agruparPersonas` los deja como dos fichas: Petro aparece dos veces y su
     Alcaldía de Bogotá 2011 no sale en la ficha del presidente.

     Lista CURADA a mano (jul-2026) sobre la revisión de
     `tools/analisis-candidato/dedup_revision.py`. Solo entran los casos
     inequívocos: la carrera es continua y no hay dos candidaturas al mismo
     cargo el mismo año. NO se infiere automáticamente — el mismo apellido
     puede ser el SEGUNDO de otra persona ("GUSTAVO MIGUEL OSORIO PETRO" no es
     Petro) y fusionar por regla generaba errores graves.

     Para ampliar: correr `dedup_revision.py --xlsx`, revisar las filas de
     confianza MEDIA y agregar aquí las confirmadas.                          */
  const ALIAS_PERSONA = {
    'GUSTAVO PETRO':               'GUSTAVO FRANCISCO PETRO URREGO',
    'SERGIO FAJARDO':              'SERGIO FAJARDO VALDERRAMA',
    'ENRIQUE PENALOSA':            'ENRIQUE PENALOSA LONDONO',
    'DAVID BARGUIL':               'DAVID ALEJANDRO BARGUIL ASSIS',
    'JUAN MANUEL GALAN':           'JUAN MANUEL GALAN PACHON',
    'FRANCIA MARQUEZ':             'FRANCIA ELENA MARQUEZ MINA',
    'JORGE ENRIQUE ROBLEDO':       'JORGE ENRIQUE ROBLEDO CASTILLO',
    'HUMBERTO DE LA CALLE':        'HUMBERTO DE LA CALLE LOMBANA',
    'FEDERICO RESTREPO':           'FEDERICO JOSE RESTREPO POSADA',
    'DAVID LUNA':                  'DAVID ANDRES LUNA SANCHEZ',
    'AYDEE LIZARAZO':              'AYDEE LIZARAZO CUBILLOS',
    'JAIME AMIN':                  'JAIME ALEJANDRO AMIN HERNANDEZ',
    'ALAN JARA':                   'ALAN JESUS EDMUNDO JARA URZOLA',
    'VIVIANE MORALES':             'VIVIANE ALEYDA MORALES HOYOS',
    'ARELIS URIANA':               'ARELIS MARIA URIANA GUARIYU',
  };

  function normPersona(s) {
    return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '')
      .toUpperCase().replace(/[^A-Z ]/g, ' ').replace(/\s+/g, ' ').trim();
  }

  // Llave de PERSONA: nombres distintos de la misma persona caen en la misma.
  function personaKey(nombre) {
    const n = normPersona(nombre);
    return ALIAS_PERSONA[n] || n;
  }

  function isPartyEntry(c) {
    if (!c || !c.nombre) return false;
    if (c.tipo === 'partido') return true;
    if (c.nombre === c.partido) return true;
    const n = c.nombre.normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase();
    return /^(PARTIDO|MOVIMIENTO|COALICION|ALIANZA|LISTA|PACTO)\b/.test(n);
  }

  // Búsqueda tolerante: cada palabra del query debe prefijar alguna del nombre.
  // Se conserva la firma (q, nombre) porque otras páginas la llaman con strings
  // sueltos; acRank usa la versión rápida sobre `_n`.
  function acMatch(q, nombre) {
    var n = padNombre(nombre);
    var words = normNombre(q).split(/\s+/).filter(Boolean);
    return words.every(function (w) { return n.indexOf(' ' + w) >= 0; });
  }

  /* ── RANKING DEL AUTOCOMPLETAR ──────────────────────────────────────────
     El buscador cortaba a 20 en el ORDEN DE CARGA de las fuentes, no por
     relevancia. Con 419k candidaturas y nombres que se repiten entre municipios
     eso escondía a cualquiera que no fuera de las primeras fuentes: buscando
     "parra" hay 866 personas y la edilesa de Barrios Unidos caía en la posición
     766 — invisible, y parecía que faltaran los datos de JAL.

     Ahora se ordena por relevancia y, a igual relevancia, por votación:
       4 · el nombre completo empieza por lo que se escribió
       2 · el primer nombre empieza por la primera palabra escrita
       1 · la consulta trae más de una palabra (es específica)
     Devuelve también el TOTAL, para poder decir cuántos quedaron fuera: con una
     sola palabra el corte es inevitable y lo honesto es avisar, no fingir que
     esos 20 son todo.

     ⚠️ Corre sobre `_n` (nombre normalizado, ver más abajo). Si la entrada no lo
     trae —listas armadas fuera del registro— se calcula y se MEMOIZA en la
     entrada, así solo la primera tecla paga el costo.                          */
  function acRank(q, lista, limite) {
    var qq = normNombre(q);
    var palabras = qq.split(/\s+/).filter(Boolean);
    if (!palabras.length) return { total: 0, items: [] };
    // ' '+palabra encuentra "¿alguna palabra del nombre empieza por esto?" sin
    // tener que partir el nombre en cada tecla.
    var agujas = palabras.map(function (w) { return ' ' + w; });
    var pre = ' ' + qq, a0 = agujas[0], na = agujas.length;
    var extra = na > 1 ? 1 : 0;
    var out = [];
    for (var i = 0; i < lista.length; i++) {
      var c = lista[i];
      var n = c._n || (c._n = padNombre(c.nombre));
      var ok = true;
      for (var j = 0; j < na; j++) { if (n.indexOf(agujas[j]) < 0) { ok = false; break; } }
      if (!ok) continue;
      var sc = n.indexOf(pre) === 0 ? 4 : (n.indexOf(a0) === 0 ? 2 : 0);
      out.push({ c: c, s: sc + extra, v: c.votos || 0 });
    }
    out.sort(function (a, b) {
      return (b.s - a.s) || (b.v - a.v) || a.c.nombre.localeCompare(b.c.nombre, 'es');
    });
    return {
      total: out.length,
      items: out.slice(0, limite || 20).map(function (x) { return x.c; }),
    };
  }

  /* ── NOMBRE NORMALIZADO PRECOMPUTADO ────────────────────────────────────
     El autocompletar normalizaba (`normalize('NFD')` + regex) el nombre de CADA
     candidatura en CADA tecla. Con 420k eso cuesta ~180 ms por pulsación en
     Node y bastante más en un navegador: escribir "natalia parra" bloqueaba el
     hilo principal varios segundos seguidos y el buscador se sentía trabado.

     Ahora cada entrada guarda `_n` = ' ' + nombre normalizado + ' ' (medido:
     91 ms una sola vez para 420k, y la búsqueda baja de 180 a 26 ms). Los
     espacios que envuelven permiten preguntar "¿alguna palabra empieza por X?"
     con un indexOf(' '+X), sin partir el nombre en cada tecla.                */
  function normNombre(s) {
    return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase().trim();
  }
  function padNombre(s) { return ' ' + normNombre(s) + ' '; }

  function mapEntry(c, base, srcName) {
    return {
      nombre: c.nombre,
      slug: c.slug,
      corp: c.corp || '',
      circunscripcion: c.circunscripcion || '',
      partido: c.partido || '',
      votos: c.votos || 0,
      tipo: c.tipo || 'candidato',
      source: srcName,
      dataUrl: base + '/' + c.slug + '.json',
      _n: padNombre(c.nombre),
    };
  }

  // Baja UNA fuente y la devuelve mapeada. Tolerante a 404: una fuente caída
  // devuelve [] con un warning y no rompe a las demás.
  async function fetchSource(src, base) {
    try {
      const r = await fetch(`${base}/${src.indexFile}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const raw = await r.json();
      return src.list(raw).map(c => mapEntry(c, base, src.name));
    } catch (e) {
      console.warn(`[CandRegistry] fuente "${src.name}" no disponible:`, e.message);
      return [];
    }
  }

  // Carga y fusiona todas las fuentes.
  //   opts.bases   → { <name>: '<baseUrl>' } override del base por fuente
  //                  (p.ej. rutas locales para verificación pre-subida).
  //   opts.includeParties=false → filtra entradas de partido.
  //   opts.onSource(lista, src, i, total) → se llama en cuanto CADA fuente
  //                  aterriza, para poder ir apilando y buscar antes de que
  //                  terminen todas. Lo que devuelva se ignora.
  async function load(opts) {
    opts = opts || {};
    const bases = opts.bases || {};
    const filtra = l => opts.includeParties === false ? l.filter(c => !isPartyEntry(c)) : l;
    let listos = 0;
    const perSource = await Promise.all(SOURCES.map(async src => {
      const base = bases[src.name] || `${S3}/${src.dir}`;
      const list = await fetchSource(src, base);
      list.forEach(c => { _bySlug[c.slug] = c; });
      listos++;
      if (opts.onSource) { try { opts.onSource(filtra(list), src, listos, SOURCES.length); } catch (e) {} }
      return list;
    }));
    return filtra(perSource.flat());
  }

  // Carga LAZY de las fuentes locales (Concejo · JAL, los 4 años). Se cachea la
  // promesa para no re-pedir. Cada candidatura es su propia entrada, SIN agrupar
  // por persona (nombres comunes se repiten entre municipios → agruparlos
  // fusionaría personas distintas).
  //   opts.bases → { concejo:'<base>', … } override (rutas locales).
  //   opts.includeParties=false → filtra entradas de partido.
  //   opts.onSource(lista, src, i, total) → igual que en load(). Son ~82 MB en
  //     8 archivos: entregarlos a medida que llegan deja buscar en Concejo 2023
  //     a los pocos segundos, en vez de esperar a que estén los ocho.
  //   ⚠️ La promesa se cachea: si loadLocal() ya se llamó, la segunda llamada
  //     recibe la lista completa al resolver pero NO los avisos de onSource.
  let _localPromise = null;
  function loadLocal(opts) {
    opts = opts || {};
    if (_localPromise) return _localPromise;
    const bases = opts.bases || {};
    const filtra = l => opts.includeParties === false ? l.filter(c => !isPartyEntry(c)) : l;
    let listos = 0;
    _localPromise = Promise.all(LOCAL_SOURCES.map(async src => {
      const base = bases[src.name] || `${S3}/${src.dir}`;
      const list = await fetchSource(src, base);
      list.forEach(c => { _bySlug[c.slug] = c; });
      listos++;
      if (opts.onSource) { try { opts.onSource(filtra(list), src, listos, LOCAL_SOURCES.length); } catch (e) {} }
      return list;
    })).then(per => filtra(per.flat()));
    return _localPromise;
  }

  // slug → URL del JSON mesa-a-mesa. Cae a la ruta endoso si el slug no se
  // cargó por el registro (compatibilidad hacia atrás).
  function dataUrlFor(slug) {
    return (_bySlug[slug] && _bySlug[slug].dataUrl) || `${S3}/endoso/${slug}.json`;
  }

  global.CandRegistry = { S3, SOURCES, LOCAL_SOURCES, isPartyEntry, acMatch, acRank, load, loadLocal,
                          dataUrlFor, normPersona, personaKey, normNombre, padNombre, ALIAS_PERSONA };
})(typeof window !== 'undefined' ? window : this);
