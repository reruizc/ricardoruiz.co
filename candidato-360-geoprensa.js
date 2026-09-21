/* ═══════════════════════════════════════════════════════════════════════════
   CANDIDATO 360 · dónde pasa lo que se publica
   ───────────────────────────────────────────────────────────────────────────
   Cruza cada titular de la escucha con los lugares del territorio de la
   candidatura, buscando sus NOMBRES en el texto:

   · Ciudad con cartografía (Bogotá, Medellín, Cali… la lista CIUDADES de
     candidato-360-electorado.js): sus localidades o comunas, y los barrios de
     cada una tal como los nombra el georef de puestos (PUESTOS_GEOREF). El
     barrio se ubica en el punto medio de sus puestos de votación y suma a su
     comuna.
   · Asamblea o gobernación: los municipios del departamento.
   · Resto de municipios: los municipios vecinos del departamento más los
     barrios y veredas del propio municipio (también del georef).

   Es búsqueda de nombres, no geolocalización de la noticia: un titular que
   dice «Suba» cuenta para Suba aunque la nota trate de otra cosa. Por eso los
   nombres ambiguos se filtran fuerte (ver `sirve`) y cada coincidencia se puede
   revisar contra su titular.

   Se apoya en C360Electorado (capas, georef, código de municipio) para que el
   mapa sea EL MISMO de la página de sexo y edad.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';
  const E = global.C360Electorado;
  const S3 = global.RRData.publicUrl('congreso-2026/output');
  const pad = (v, n) => String(v ?? '').replace(/\D/g, '').padStart(n, '0').slice(-n);
  const N = s => ' ' + String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^A-Za-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim().toUpperCase() + ' ';
  const clave = s => N(s).trim();
  const sinTildes = s => String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '');

  /* Nombres que no se pueden buscar sueltos: palabras comunes, países y
     sustantivos que un titular usa sin hablar de un barrio. */
  const STOP = new Set(['CENTRO', 'EL CENTRO', 'LA PAZ', 'SAN JOSE', 'LA ESPERANZA', 'EL CARMEN', 'EL PORVENIR', 'PORVENIR', 'BUENOS AIRES', 'LA FLORIDA',
    'SAN ANTONIO', 'SAN FRANCISCO', 'LA VICTORIA', 'LA LIBERTAD', 'EL PARAISO', 'LA UNION', 'LA ESTRELLA', 'LA GLORIA', 'LA PRIMAVERA', 'LAS FERIAS', 'LA ISLA',
    'LA PLAYA', 'EL TRIUNFO', 'LA INDEPENDENCIA', 'LA REFORMA', 'LA NUEVA', 'EL PROGRESO', 'LA FE', 'LA MERCED', 'LAS AMERICAS', 'AMERICAS', 'LOS ALPES',
    'COLOMBIA', 'BRASIL', 'VENEZUELA', 'PANAMA', 'MEXICO', 'ESPANA', 'ITALIA', 'CUBA', 'CHILE', 'PERU', 'ECUADOR', 'ARGENTINA', 'EUROPA', 'CANADA', 'JAPON',
    'ESTADIO', 'EL ESTADIO', 'TERMINAL', 'AEROPUERTO', 'UNIVERSIDAD', 'HOSPITAL', 'COLEGIO', 'CEMENTERIO', 'CARCEL', 'PLAZA', 'PARQUE', 'INDUSTRIAL', 'ZONA INDUSTRIAL',
    'COMERCIAL', 'RURAL', 'SIN INFORMACION', 'SIN BARRIO', 'NULL', 'OTROS', 'VARIOS', 'CABECERA', 'CABECERA MUNICIPAL', 'ZONA RURAL', 'CORREGIMIENTO', 'VEREDA',
    'SANTA FE', 'LA SALLE', 'EL NOGAL', 'LA CUMBRE', 'SAN MARTIN', 'SUCRE', 'BOLIVAR', 'CORDOBA', 'CALDAS', 'SANTANDER', 'NARINO', 'CAUCA', 'MAGDALENA', 'META',
    'CAQUETA', 'CESAR', 'GUAINIA', 'VICHADA', 'HUILA', 'TOLIMA', 'RISARALDA', 'QUINDIO', 'CHOCO', 'ANTIOQUIA', 'ATLANTICO', 'BOYACA', 'CUNDINAMARCA', 'PUTUMAYO',
    'AMAZONAS', 'ARAUCA', 'CASANARE', 'GUAVIARE', 'VAUPES', 'LA GUAJIRA',
    /* Nombres de periódicos y frases hechas que también son barrios. */
    'LA PATRIA', 'EL TIEMPO', 'EL ESPECTADOR', 'LA REPUBLICA', 'EL PAIS', 'LA OPINION', 'EL HERALDO', 'EL UNIVERSAL', 'LA NACION', 'EL NUEVO SIGLO', 'EL MUNDO',
    'NO APLICA', 'SIN DATO', 'UNION EUROPEA', 'NACIONES UNIDAS', 'ESTADOS UNIDOS', 'LA ESPERANZA', 'LA CONCORDIA', 'LA DEMOCRACIA', 'LA CONSTITUCION', 'EL RETIRO', 'LA ALBORADA', 'EL JARDIN']);
  /* Barrios con nombre de persona: en un titular casi siempre es la persona.
     Si el primer nombre es uno de estos, el barrio solo cuenta con «barrio»,
     «sector» o «vereda» delante. */
  const NOMBRES_PILA = new Set(['JUAN', 'JOSE', 'CARLOS', 'JORGE', 'GUSTAVO', 'ALFONSO', 'SIMON', 'NICOLAS', 'LUIS', 'PEDRO', 'ANTONIO', 'FRANCISCO', 'RAFAEL',
    'MANUEL', 'CAMILO', 'EDUARDO', 'ALBERTO', 'ALVARO', 'ANDRES', 'FERNANDO', 'JAIME', 'JAVIER', 'MIGUEL', 'MARIA', 'ANA', 'POLICARPA', 'OLAYA', 'LAUREANO',
    'MARCO', 'MARCOS', 'GABRIEL', 'GUILLERMO', 'HERNANDO', 'JULIO', 'LUCERO', 'MISAEL', 'RICARDO', 'ROBERTO', 'SANTIAGO', 'VICTOR', 'ENRIQUE', 'DIEGO', 'DANIEL', 'GILMA']);
  const CONTEXTO = /\b(?:BARRIO|BARRIOS|SECTOR|VEREDA|CORREGIMIENTO|URBANIZACION|CONJUNTO|CASERIO|INSPECCION)\s$/;
  /* Contextos que desmienten un nombre: «Independiente Santa Fe» no es la
     localidad. */
  const DESMIENTE = [/INDEPENDIENTE SANTA FE|SANTA FE VS|VS SANTA FE/];

  function limpiarBarrio(s) {
    return clave(String(s || '')
      .replace(/#\s*\d+|\bNO\.?\s*\d+\b|\b\d+\b/gi, ' ')
      .replace(/\b(I{1,3}|IV|V|VI{0,3}|IX|X)\b\s*$/i, ' ')
      .replace(/\b(SECTOR|ETAPA|MZ|MANZANA)\b.*$/i, ' '));
  }
  /* Cómo se MUESTRA un barrio: sin «#2» ni el «II» de la etapa. */
  const bonito = s => String(s || '').replace(/#\s*\d+/g, ' ').replace(/\s+\b(I{1,3}|IV|V|VI{0,3}|IX|X|\d+)\b\s*$/i, ' ').replace(/\s+/g, ' ').trim();
  function limpiarUnidad(s) {
    return clave(String(s || '').replace(/^\s*\d+\s*/, '').replace(/^(COMUNA|LOCALIDAD|LOC|UCG|ZONA)\.?\s*\d*\s*/i, '').replace(/^\d+\s*/, ''));
  }
  /* Un nombre se busca suelto si es distintivo: dos palabras o más, o una sola
     de seis letras o más, y fuera de la lista de comunes. */
  /* Las localidades y comunas se aceptan desde cuatro letras («Suba», «Usme»,
     «Bosa»): son pocas, se conocen, y en la prensa de su ciudad casi siempre
     son eso. */
  function sirve(k, unidad) {
    if (!k || STOP.has(k)) return false;
    const w = k.split(' ');
    return w.length >= 2 ? k.length >= 7 : k.length >= (unidad ? 4 : 6);
  }

  /* ── La gaceta del territorio ────────────────────────────────────────────
     Devuelve { modo, lugar, geo, code(props), name(props), propia, nombres }
     donde `nombres` es [{ k, tipo: 'unidad'|'lugar', unidad, nombre, lat, lng,
     contexto }] ordenado de más largo a más corto. */
  const cacheG = new Map();
  function gaceta(campana, t) {
    const llave = JSON.stringify([campana?.corp, campana?.departamento, campana?.municipio]);
    if (!cacheG.has(llave)) cacheG.set(llave, armar(campana, t).catch(e => { cacheG.delete(llave); throw e; }));
    return cacheG.get(llave);
  }
  async function armar(campana, t) {
    const dep = pad(campana?.departamento, 2);
    if (!dep || dep === '00') return null;
    const nombres = [], vistos = new Set();
    const poner = (k, x) => { if (!sirve(k, x.tipo === 'unidad') && !x.contexto) return; if (vistos.has(k)) return; vistos.add(k); nombres.push(Object.assign({ k }, x)); };

    const geoDep = () => E.json(`${S3}/mapas-2026/Departamentos-mps/${dep}.json`);
    const munDe = p => pad(p.mun_elec ?? p.mun_electoral, 3);
    const nombresMunicipios = (geo, excepto) => {
      for (const f of geo.features || []) {
        const code = munDe(f.properties), nom = f.properties.mpio_cnmbr || '';
        if (code === excepto) continue;
        const k = limpiarUnidad(nom);
        poner(k, { tipo: 'unidad', unidad: code, nombre: nom });
        const sinArt = k.replace(/^(EL|LA|LOS|LAS) /, '');
        if (sinArt !== k && sinArt.length >= 7) poner(sinArt, { tipo: 'unidad', unidad: code, nombre: nom });
      }
    };
    /* Barrios y veredas del georef: el punto medio de sus puestos, y la
       unidad (comuna o municipio) donde caen más puestos. */
    const lugaresDe = async (prefijo, unidadDe) => {
      const pu = await E.puestos();
      const acc = new Map();
      for (const [code, p] of Object.entries(pu)) {
        if (!code.startsWith(prefijo) || ['90', '98'].includes(p.mesa.zon)) continue;
        /* En Kennedy (Bogotá) y otros pocos el campo trae VARIOS barrios pegados
           sin separador («CATALINA CATALINAII CEMENTERIO JARDINES…»): no es un
           nombre que se pueda buscar. */
        if (String(p.barrio || '').length > 45) continue;
        const k = limpiarBarrio(p.barrio);
        if (!k || !Number.isFinite(p.lat) || !Number.isFinite(p.lng)) continue;
        const u = unidadDe(p);
        const a = acc.get(k) || { lat: 0, lng: 0, n: 0, unidades: new Map(), nombre: p.barrio };
        a.lat += p.lat; a.lng += p.lng; a.n++; a.unidades.set(u, (a.unidades.get(u) || 0) + 1); acc.set(k, a);
      }
      for (const [k, a] of acc) {
        const unidad = [...a.unidades].sort((x, y) => y[1] - x[1])[0][0];
        const nom = bonito(a.nombre);
        const persona = NOMBRES_PILA.has(k.split(' ')[0]);
        const corto = k.split(' ').length === 1;
        poner(k, { tipo: 'lugar', unidad, nombre: nom, lat: a.lat / a.n, lng: a.lng / a.n, contexto: persona || corto });
      }
    };

    let out;
    if (t.departamental) {
      const geo = await geoDep();
      nombresMunicipios(geo, null);
      out = { modo: 'depto', lugar: t.depNombre, geo, code: munDe, name: p => p.mpio_cnmbr || 'Municipio', propia: null, unidadLabel: ['municipio', 'municipios'] };
    } else {
      const cfg = E.ciudadDe(campana.municipio);
      const mun3 = pad(await E.codigoMunicipio(dep, campana.municipio).catch(() => '') || (t.esBogota ? '001' : ''), 3);
      if (cfg) {
        let geo = await E.json(`${S3}/mapas-2026/Ciudades-COM-LOC/${cfg.path}`);
        if (cfg.rotate) geo = E.rotar90(geo);
        const code = cfg.porNombre ? (p => clave(cfg.code(p))) : cfg.code;
        for (const f of geo.features || []) {
          const u = code(f.properties), k = limpiarUnidad(cfg.name(f.properties));
          poner(k, { tipo: 'unidad', unidad: u, nombre: cfg.name(f.properties) });
          const sinArt = k.replace(/^(EL|LA|LOS|LAS) /, '');
          if (sinArt !== k && sinArt.length >= 7) poner(sinArt, { tipo: 'unidad', unidad: u, nombre: cfg.name(f.properties) });
        }
        /* Bogotá y Cali tienen además la cartografía catastral de barrios (la
           misma del mapa de sexo y edad), con nombre oficial y localidad o
           comuna: esos nombres entran primero. */
        if (cfg.barrios) await barriosCatastrales(cfg.barrios, poner).catch(e => console.warn('barrios', e));
        const unidadDe = p => cfg.porNombre ? clave(String(p.mesa.comNom || '').replace(/^\d+\s*COMUNA\s*/i, '')) : (cfg.dataKey ? cfg.dataKey(p.mesa.com) : p.mesa.com);
        if (mun3 && mun3 !== '000') await lugaresDe(dep + mun3, unidadDe).catch(() => {});
        out = { modo: 'ciudad', lugar: t.base, geo, code, name: cfg.name, propia: null, rotate: !!cfg.rotate, ventana: cfg.ventana || null, unidadLabel: [cfg.unidad, cfg.unidad === 'localidad' ? 'localidades' : 'comunas'] };
      } else {
        const geo = await geoDep();
        nombresMunicipios(geo, mun3);
        if (mun3 && mun3 !== '000') await lugaresDe(dep + mun3, () => mun3).catch(() => {});
        out = { modo: 'municipio', lugar: t.base, geo, code: munDe, name: p => p.mpio_cnmbr || 'Municipio', propia: mun3, unidadLabel: ['municipio', 'municipios'] };
      }
    }
    /* La ciudad o el departamento mismos no son un lugar DENTRO del territorio. */
    const propio = new Set([clave(t.base), clave(t.depNombre), clave(t.munLimpio)].filter(Boolean));
    out.nombres = nombres.filter(x => !propio.has(x.k)).sort((a, b) => b.k.length - a.k.length);
    /* Las anclas del territorio: su nombre y el de sus unidades. Un barrio sin
       «barrio» delante solo cuenta si el titular nombra alguna. */
    out.anclas = [...propio].concat(out.nombres.filter(x => x.tipo === 'unidad').map(x => x.k)).filter(k => k.length >= 4);
    return out;
  }

  const scripts = new Map();
  function cargarScript(src) {
    if (!scripts.has(src)) scripts.set(src, new Promise((ok, no) => { const el = document.createElement('script'); el.src = src; el.onload = ok; el.onerror = () => no(new Error(src)); document.head.appendChild(el); }));
    return scripts.get(src);
  }
  async function barriosCatastrales(ciudad, poner) {
    const partes = ciudad === 'bogota' ? Array.from({ length: 19 }, (_, i) => pad(i + 1, 2)) : Array.from({ length: 22 }, (_, i) => pad(i + 1, 2));
    await Promise.all(partes.map(c => cargarScript(`candidato-360-data/${ciudad}-barrios/${c}.js`).catch(() => null)));
    const dic = ciudad === 'bogota' ? global.Candidato360BogotaBarrios : global.Candidato360CaliBarrios;
    for (const [unidad, fc] of Object.entries(dic || {})) {
      for (const f of fc.features || []) {
        const nom = ciudad === 'bogota' ? f.properties.nombre : String(f.properties.barrio || '').replace(/^Sector\s+/i, '');
        const k = limpiarBarrio(nom);
        if (!k) continue;
        /* El punto: el promedio de los vértices del anillo exterior basta para
           ubicar el barrio en el mapa. */
        const g = f.geometry, anillo = g?.type === 'Polygon' ? g.coordinates[0] : g?.type === 'MultiPolygon' ? g.coordinates[0][0] : [];
        if (!anillo.length) continue;
        const lng = anillo.reduce((s, c) => s + c[0], 0) / anillo.length, lat = anillo.reduce((s, c) => s + c[1], 0) / anillo.length;
        const u = ciudad === 'bogota' ? pad(f.properties.loc_codigo || unidad, 2) : pad(f.properties.comuna || unidad, 2);
        poner(k, { tipo: 'lugar', unidad: u, nombre: bonito(nom), lat, lng, contexto: NOMBRES_PILA.has(k.split(' ')[0]) || k.split(' ').length === 1 });
      }
    }
  }

  /* ── El cruce ────────────────────────────────────────────────────────────
     filas: las del análisis de saliencia (traen `_n`, el titular normalizado
     con espacios en los bordes). Devuelve { lugares, unidades } con los
     índices de fila de cada coincidencia. */
  function cruzar(filas, g) {
    const lugares = new Map(), unidades = new Map();
    filas.forEach((f, i) => {
      const n = f._n || N(f.titulo);
      if (DESMIENTE.some(re => re.test(n))) return;
      const tomados = [], enFila = new Set();
      for (const x of g.nombres) {
        const pos = n.indexOf(` ${x.k} `);
        if (pos < 0) continue;
        if (tomados.some(k => k.includes(x.k))) continue; /* «San Javier» no vuelve a contar como «Javier» */
        /* «Los Andes» es la universidad o la cordillera, no el municipio de Andes. */
        if (/ (?:LOS|LAS) $/.test(n.slice(0, pos + 1)) && x.k.split(' ').length === 1) continue;
        /* Un nombre de una palabra tiene que venir con mayúscula en el titular:
           «bello» o «remedios» en minúscula son adjetivo y sustantivo. */
        if (x.k.split(' ').length === 1 && !new RegExp(`(?:^|[^A-Za-z])${x.k[0]}${x.k.slice(1).toLowerCase()}(?![a-z])`).test(sinTildes(f.titulo))) continue;
        const conPalabra = CONTEXTO.test(n.slice(0, pos + 1));
        if (x.contexto && !conPalabra) continue;
        /* Medido en Bogotá: sin esta regla «Unión Europea» y «La Patria»
           contaban como barrios en titulares que no eran de la ciudad. */
        if (x.tipo === 'lugar' && !conPalabra && g.modo !== 'depto' && !(g.anclas || []).some(k => k !== x.k && n.includes(` ${k} `))) continue;
        tomados.push(x.k);
        const idL = `${x.tipo}:${x.k}`;
        const l = lugares.get(idL) || Object.assign({ n: 0, idx: [] }, x);
        l.n++; l.idx.push(i); lugares.set(idL, l);
        if (x.unidad && !enFila.has(x.unidad)) {
          enFila.add(x.unidad);
          const u = unidades.get(x.unidad) || { unidad: x.unidad, n: 0, idx: [], nombres: new Set() };
          u.n++; u.idx.push(i); u.nombres.add(x.tipo === 'unidad' ? x.nombre : x.nombre); unidades.set(x.unidad, u);
        }
      }
    });
    return {
      lugares: [...lugares.values()].sort((a, b) => b.n - a.n),
      unidades,
      conLugar: new Set([...lugares.values()].flatMap(l => l.idx)).size,
    };
  }

  global.C360GeoPrensa = { gaceta, cruzar, limpiarBarrio, limpiarUnidad, sirve };
})(window);
