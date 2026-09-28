/* ═══════════════════════════════════════════════════════════════════════════
   EL ELECTORADO DE UNA CANDIDATURA · cálculo compartido
   ───────────────────────────────────────────────────────────────────────────
   Las cuentas que responden «cómo es y cómo vota el territorio donde están sus
   votos» las usan dos pantallas: la tarjeta 07 del CRM (candidato-360.js) y la
   página de análisis (candidato-360-electorado.html). Viven acá para que sean
   LA MISMA cuenta: dos implementaciones serían dos respuestas distintas a la
   misma pregunta, y la de la tarjeta y la de la página se contradirían.

   Este archivo solo devuelve DATOS —números y nombres tal como vienen—. Cómo
   se escriben (tipo oración, porcentajes, colores) es cosa de cada pantalla.

   El voto es secreto: nada de esto dice quién votó por alguien. Describe el
   CENSO de los puestos donde están sus votos, ponderado por cuántos sacó en
   cada uno, y lo compara con el municipio entero. Es una lectura del terreno.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';
  const S3 = global.RRData.publicUrl('congreso-2026/output');
  const cache = new Map();
  function json(url) {
    if (!cache.has(url)) cache.set(url, fetch(url).then(r => r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status))).catch(e => { cache.delete(url); throw e; }));
    return cache.get(url);
  }

  /* ── QUIÉN PUEDE VOTAR en cada puesto (sep-2026) ───────────────────────
     El censo electoral del Congreso 2026 que publica la Registraduría, puesto
     por puesto: sexo y diez rangos de edad OBSERVADOS, más el cruce sexo ×
     edad (estimado con raking sobre la forma de 2022) y el censo de 2023 para
     comparar. Lo produce tools/candidato-360/perfil/construir-censo-2026.py.
     Se describe a quien PUEDE votar y no a quien votó en 2022 a propósito: la
     participación viene subiendo (58 % en la primera vuelta de 2026, 64 % en
     la segunda) y el electorado de 2027 no va a ser el que votó antes.
     Fila: [potencial, mujeres, hombres, 10 bandas, 6 celdas H/M × 18-30 ·
     31-60 · 61+, bloque, censo2023, cruce2023]. Sin exterior. */
  let censoPromise = null;
  function censo2026() {
    if (!censoPromise) censoPromise = fetch(`${S3}/mapas-2026/CENSO_PUESTO_2026.json`).then(r => r.ok ? r.json() : null).catch(() => null);
    return censoPromise;
  }
  const BANDAS_EDAD = ['18-20', '21-25', '26-30', '31-35', '36-40', '41-45', '46-50', '51-55', '56-60', '61+'];
  /* Los tres grupos que se muestran de entrada; los diez rangos, al desglosar.
     «Adultos mayores» es más de 60, el corte de la ley colombiana. */
  const GRUPOS_EDAD = [
    { clave: 'jovenes', nombre: 'Jóvenes', rango: '18 a 30', bandas: [0, 1, 2], figura: 'joven' },
    { clave: 'adultos', nombre: 'Adultos', rango: '31 a 60', bandas: [3, 4, 5, 6, 7, 8], figura: 'adulto' },
    { clave: 'mayores', nombre: 'Adultos mayores', rango: 'más de 60', bandas: [9], figura: 'mayor' },
  ];
  const agruparEdad = bandas => GRUPOS_EDAD.map(g => g.bandas.reduce((s, i) => s + (bandas[i] || 0), 0));

  /* ── El censo por puesto de votación ─────────────────────────────────────
     Las coordenadas, el barrio y la comuna salen de PUESTOS_GEOREF (columnas
     1 código, 7 barrio, 9/10 lat/lng, 11/12 comuna, 18 nombre). El CENSO ya
     no: sus columnas 13/14 son un corte viejo de 38,6 millones, 2,65 millones
     por debajo del oficial. Manda el censo de 2026; solo si no respondiera se
     cae al del georef, y `fuenteCenso` lo dice. */
  let puestosPromise = null;
  function puestos() {
    if (!puestosPromise) puestosPromise = Promise.all([
      fetch(`${S3}/mapas-2026/PUESTOS_GEOREF.csv`).then(r => r.ok ? r.text() : Promise.reject(new Error('sin PUESTOS_GEOREF'))),
      censo2026(),
    ]).then(([raw, C]) => {
      const lookup = {}, filas = C?.puestos || {};
      raw.split(/\r?\n/).slice(1).forEach(line => {
        const row = line.split(';'), code = String(row[1] || ''), barrio = row[7];
        if (!code || !barrio) return;
        const mesa = { dep: code.slice(0, 2), mun: code.slice(2, 5), zon: code.slice(5, 7), pue: code.slice(7, 9), com: String(row[11] || ''), comNom: String(row[12] || '') };
        const f = filas[code];
        const mujeres = f ? f[1] : Number(row[13]) || 0, hombres = f ? f[2] : Number(row[14]) || 0;
        lookup[code] = { barrio, nombre: String(row[18] || '').trim(), lat: Number(row[9]), lng: Number(row[10]), censo: f ? f[0] : mujeres + hombres, mujeres, hombres, mesa, fuenteCenso: f ? 'censo-2026' : 'georef' };
      });
      return lookup;
    }).catch(e => { puestosPromise = null; throw e; });
    return puestosPromise;
  }
  /* La edad por puesto: los diez rangos observados del censo de 2026. Que el
     archivo falte no puede tumbar el resto de la lectura. */
  let edadPromise = null;
  function censoEdad() {
    if (!edadPromise) edadPromise = censo2026().then(C => {
      if (!C?.puestos) return null;
      const puestos = {}, bloques = {};
      Object.entries(C.puestos).forEach(([k, f]) => { puestos[k] = f.slice(3, 13); if (f[19] >= 0) bloques[k] = f[19]; });
      return { bandas: BANDAS_EDAD, puestos, bloques, fuente: 'Censo electoral por puesto del Congreso 2026 (Registraduría).' };
    });
    return edadPromise;
  }

  /* ── El cruce SEXO × EDAD de quien puede votar en cada puesto ────────────
     Es lo que arma los «perfiles de votante» de la página del electorado. La
     Registraduría publica sexo y edad por separado, así que el cruce es una
     ESTIMACIÓN: la forma sale de los sufragantes de 2022 de ese puesto y los
     totales del censo de 2026. La página lo dice. */
  let sexoEdadPromise = null;
  function sexoEdad() {
    if (!sexoEdadPromise) sexoEdadPromise = censo2026().then(C => {
      if (!C?.puestos) return null;
      const puestos = {};
      Object.entries(C.puestos).forEach(([k, f]) => { puestos[k] = f.slice(13, 19); });
      return { sexos: ['H', 'M'], edades: ['18-30', '31-60', '61+'], puestos, fuente: C.fuente };
    });
    return sexoEdadPromise;
  }
  /* Las seis celdas, en el orden del archivo: H 18-30 · H 31-60 · H 61+ ·
     M 18-30 · M 31-60 · M 61+. Los nombres son los de una campaña, no los de
     una tabla del DANE. */
  const PERFILES = [
    { i: 0, sexo: 'H', edad: '18-30', nombre: 'Hombres jóvenes', corto: 'hombres de 18 a 30', figura: 'joven' },
    { i: 1, sexo: 'H', edad: '31-60', nombre: 'Hombres adultos', corto: 'hombres de 31 a 60', figura: 'adulto' },
    { i: 2, sexo: 'H', edad: '61+',   nombre: 'Hombres mayores', corto: 'hombres de más de 60', figura: 'mayor' },
    { i: 3, sexo: 'M', edad: '18-30', nombre: 'Mujeres jóvenes', corto: 'mujeres de 18 a 30', figura: 'joven' },
    { i: 4, sexo: 'M', edad: '31-60', nombre: 'Mujeres adultas', corto: 'mujeres de 31 a 60', figura: 'adulto' },
    { i: 5, sexo: 'M', edad: '61+',   nombre: 'Mujeres mayores', corto: 'mujeres de más de 60', figura: 'mayor' },
  ];

  /* ── Cómo cambió el censo de 2023 a 2026 ─────────────────────────────────
     Lo que decide una estrategia de inscripción de cédulas. Cuidado con leerlo
     puesto a puesto: entre las dos elecciones la Registraduría abrió puestos,
     cerró otros y movió mesas, así que un puesto puede crecer porque le
     trasladaron gente. El número firme es el del territorio entero; los
     puestos van con esa advertencia. `prefijo` = dep (2) o dep+mun (5). */
  async function cambioCenso(prefijo) {
    const [C, lugares] = await Promise.all([censo2026(), puestos().catch(() => ({}))]);
    if (!C?.puestos || !prefijo) return null;
    let hoy = 0, antes = 0, nuevos = 0, censoNuevos = 0, jovenes = 0;
    const comparables = [];
    Object.entries(C.puestos).forEach(([k, f]) => {
      if (!k.startsWith(prefijo)) return;
      hoy += f[0]; jovenes += f[3];
      if (f[20] >= 0) { antes += f[20]; comparables.push({ code: k, hoy: f[0], antes: f[20], renumerado: f[21] === 2, nombre: lugares[k]?.nombre || '', barrio: lugares[k]?.barrio || '' }); }
      else { nuevos++; censoNuevos += f[0]; }
    });
    let cerrados = 0, censoCerrados = 0;
    Object.entries(C.cerrados2023 || {}).forEach(([m, [n, c]]) => { if (m.startsWith(prefijo)) { cerrados += n; censoCerrados += c; } });
    const antesTotal = antes + censoCerrados;
    if (!hoy || !antesTotal) return null;
    const crecen = comparables.filter(x => x.antes >= 300).map(x => ({ ...x, delta: x.hoy - x.antes, tasa: x.hoy / x.antes - 1 })).sort((a, b) => b.delta - a.delta);
    return { hoy, antes: antesTotal, crecimiento: hoy / antesTotal - 1, nuevos, censoNuevos, cerrados, censoCerrados,
      primeros: jovenes, top: crecen.slice(0, 8), crecieronFuerte: crecen.filter(x => x.tasa >= .3).length, comparables: comparables.length };
  }
  const suma6 = (a, b) => a.map((x, i) => x + (b?.[i] || 0));
  const shares = v => { const t = v.reduce((s, x) => s + x, 0); return t ? v.map(x => x / t) : null; };
  /* Votos de una familia política en un puesto, leyendo el JSON mesa a mesa
     de una corporación de 2023: v = [[índiceCandidato, votos]], cands[i] =
     [nombre, índicePartido], partidos[j] = [nombre, votos]. */
  /* `familia` puede ser una clave ('cd') o un Set de claves: cuando la familia
     exacta no tiene lista en el territorio (el centro-derecha en el Concejo de
     Bogotá 2023, donde Cambio Radical y La U quedan en el centro), se mide con
     sus vecinas del espectro y la página lo declara. */
  const VECINAS = { izq: ['izq', 'ci'], ci: ['ci', 'izq', 'c'], c: ['c', 'ci', 'cd'], cd: ['cd', 'c', 'd'], d: ['d', 'cd'] };
  const setFamilia = f => f instanceof Set ? f : new Set([f]);
  /* `listas` es el voto SOLO POR LA LISTA (el logo), que no tiene candidato y
     va indexado por partido. Sin él, una lista cerrada vale cero: el Pacto
     Histórico sacó 376.644 votos en el Concejo de Bogotá 2023 y todos fueron
     así, de modo que el mapa de la izquierda bogotana salía vacío. */
  function votosFamilia(v, cands, partidos, familia, listas) {
    const PB = global.PartidosBloques, fam = setFamilia(familia); let propios = 0, total = 0;
    const sumar = (nombre, n) => {
      if (!nombre) return;
      total += n; if (fam.has(PB?.bloqueDeOrganizacion?.(nombre) || 'sc')) propios += n;
    };
    (v || []).forEach(([ci, n]) => sumar(partidos?.[cands?.[ci]?.[1]]?.[0], n));
    (listas || []).forEach(([pi, n]) => sumar(partidos?.[pi]?.[0], n));
    return { propios, total };
  }
  function votosFamiliaPartidos(partidos, familia) {
    const PB = global.PartidosBloques, fam = setFamilia(familia); let propios = 0, total = 0;
    (partidos || []).forEach(([nombre, n]) => { total += Number(n) || 0; if (fam.has(PB?.bloqueDeOrganizacion?.(nombre) || 'sc')) propios += Number(n) || 0; });
    return { propios, total };
  }
  /* Cuánto rinde cada perfil para una familia: el peso del perfil donde la
     familia saca votos, contra su peso en todo el territorio. 1,20 = «donde
     su familia vota, ese grupo pesa un 20 % más que en el promedio». Y por
     unidad (comuna, barrio, municipio), «dónde le pega» cada perfil:
     concentración del perfil × fuerza relativa de la familia. */
  function perfiles(unidades) {
    const conDato = unidades.filter(u => u.comp && u.total > 0);
    const compTerr = shares(conDato.reduce((acc, u) => suma6(acc, u.comp), [0, 0, 0, 0, 0, 0]));
    const famTerr = conDato.reduce((s, u) => s + u.propios, 0) / Math.max(1, conDato.reduce((s, u) => s + u.total, 0));
    if (!compTerr || !famTerr) return null;
    const indice = PERFILES.map(p => {
      let num = 0, den = 0;
      conDato.forEach(u => { const sh = shares(u.comp); if (!sh) return; num += u.propios * sh[p.i]; den += u.propios; });
      return den ? (num / den) / compTerr[p.i] : 1;
    });
    const pega = unidades.map(u => {
      const sh = u.comp ? shares(u.comp) : null; if (!sh || !u.total) return null;
      const fam = (u.propios / u.total) / famTerr;
      return PERFILES.map(p => ({ conc: sh[p.i] / compTerr[p.i], fam, pega: (sh[p.i] / compTerr[p.i]) * fam, share: sh[p.i] }));
    });
    return { compTerr, famTerr, indice, pega };
  }

  /* ── Las ciudades con cartografía por comuna o localidad ─────────────────
     Mismas capas que el CRM (CITY_JAL_LAYERS en candidato-360.js); el código
     de comuna del georef coincide con las llaves de resultados-concejo-2023.
     Medellín: la Registraduría numera los corregimientos 17-21 y el DAP 50-90. */
  const MDE_CORR = { '17': '70', '18': '80', '19': '50', '20': '60', '21': '90' };
  const CIUDADES = [
    { match: ['BOGOTA'], path: 'BOG-LOCALIDADX.json', unidad: 'localidad', code: p => String(p.LocCodigo || '').padStart(2, '0'), name: p => p.LocNombre || 'Localidad', rotate: true, barrios: 'bogota', ventana: { sur: 4.23, norte: 4.845, oeste: -74.28, este: -73.975 } },
    { match: ['MEDELLIN'], path: 'MEDELLINX.json', unidad: 'comuna', code: p => String(p.CODIGO || '').padStart(2, '0'), name: p => p.NOMBRE || p.IDENTIFICACION || 'Comuna', dataKey: c => MDE_CORR[c] || c },
    { match: ['CALI'], path: 'CALIX.json', unidad: 'comuna', code: p => String(p.comuna || '').padStart(2, '0'), name: p => p.nombre || 'Comuna', barrios: 'cali' },
    { match: ['PEREIRA'], path: 'PEREIRAX.json', unidad: 'comuna', code: p => String(p.Comuna || ''), name: p => p.Comuna || 'Comuna', porNombre: true },
    { match: ['IBAGUE'], path: 'IBAGUEX.json', unidad: 'comuna', code: p => String(p.COMUNAS || '').replace(/\D/g, '').padStart(2, '0'), name: p => p.COMUNAS || 'Comuna' },
    { match: ['BARRANQUILLA'], path: 'BARRANQUILLAX.json', unidad: 'localidad', code: p => ({ 4: '01', 2: '02', 1: '03', 3: '04', 5: '05' })[Number(p.id)] || '', name: p => p.nombre || 'Localidad' },
    /* Cartagena se divide en 15 Unidades Comuneras de Gobierno más la 20, que
       agrupa los corregimientos y las islas. El georef solo le pone las 3
       localidades, así que la UCG de cada puesto la resuelve por PIP
       build_cartagena_ucg.py; acá va la capa ya disuelta.
       ⚠️ Lleva ventana fija por lo mismo que Bogotá: la UCG 20 llega hasta
       Isla Fuerte, a 100 km al sur, y encuadrar por ella deja el casco urbano
       8 veces más pequeño de lo que cabe. Las islas siguen en el mapa; hay
       que alejar para verlas. */
    { match: ['CARTAGENA'], path: 'CARTAGENA-UCG.json', unidad: 'comuna', code: p => String(p.CODIGO || ''), name: p => p.NOMBRE || 'UCG', barrios: 'cartagena', ventana: { sur: 10.275, norte: 10.47, oeste: -75.58, este: -75.415 }, ventanaBarrios: true, localidades: 'CARTAGENA-LOCALIDADES.json', rotuloUnidad: 'UCG' },
    { match: ['MONTERIA'], path: 'MONTERIAX.json', unidad: 'comuna', code: p => String(p.CC_COMUNA || '').padStart(2, '0'), name: p => p.NMG || 'Comuna' },
    { match: ['MANIZALES'], path: 'MANIZALESX.json', unidad: 'comuna', code: p => String(p.ID_COMUNA || '').padStart(2, '0'), name: p => p.NOMBRES_CO || 'Comuna' },
    { match: ['BUCARAMANGA'], path: 'BUCARAMANGAX.json', unidad: 'comuna', code: p => String(p.COD_COMUNA || '').padStart(2, '0'), name: p => p.NOMBRE_COM || 'Comuna' },
    { match: ['CUCUTA'], path: 'CUCUTAX.json', unidad: 'comuna', code: p => { const n = String(p.Comuna ?? '').replace(/\D/g, ''); return (!n || n === '0' ? '6' : n).padStart(2, '0'); }, name: p => `Comuna ${Number(String(p.Comuna ?? '').replace(/\D/g, '')) || 6}` },
    { match: ['NEIVA'], path: 'NEIVAX.json', unidad: 'comuna', code: p => String(p.comuna || '').replace(/\D/g, '').padStart(2, '0'), name: p => String(p.comuna || 'Comuna').replace(/\s+/g, ' ') },
    { match: ['POPAYAN'], path: 'POPAYANX.json', unidad: 'comuna', code: p => String(p.COMUNAS || p.ACAD_TEXT || '').replace(/\D/g, '').padStart(2, '0'), name: p => p.COMUNAS || 'Comuna' },
    { match: ['SINCELEJO'], path: 'SINCELEJOX.json', unidad: 'comuna', code: p => String(p.Nombre || '').replace(/\D/g, '').padStart(2, '0'), name: p => p.Nombre || 'Comuna' },
    { match: ['VILLAVICENCIO'], path: 'VILLAVICENCIOX.json', unidad: 'comuna', code: p => String(p.Comuna || '').replace(/\D/g, '').padStart(2, '0'), name: p => p.Comuna || 'Comuna' },
  ];
  const normTexto = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toUpperCase();
  function ciudadDe(nombre) { const c = normTexto(nombre); return CIUDADES.find(x => x.match.some(m => c.includes(m))) || null; }
  /* Bogotá se dibuja girada 90° a la izquierda (convención del proyecto). */
  function rotar90(geoData) {
    const cx = -74.08, cy = 4.65, rot = ([lon, lat]) => [cx - (lat - cy), cy + (lon - cx)];
    const geom = g => g.type === 'Polygon' ? { ...g, coordinates: g.coordinates.map(r => r.map(rot)) } : g.type === 'MultiPolygon' ? { ...g, coordinates: g.coordinates.map(pg => pg.map(r => r.map(rot))) } : g;
    return { ...geoData, features: geoData.features.map(f => ({ ...f, geometry: geom(f.geometry) })) };
  }

  const codigoPuesto = m => `${String(m.dep || '').padStart(2, '0')}${String(m.mun || '').padStart(3, '0')}${String(m.zon || '').padStart(2, '0')}${String(m.pue || '').padStart(2, '0')}`;
  const ZONA_ESPECIAL = new Set(['90', '98']);   /* censo consolidado y cárceles: ni rural ni urbano */

  /* ── El perfil de su votación ────────────────────────────────────────────
     Ponderar el censo del puesto por los votos que sacó ahí responde «cómo es
     el electorado donde usted saca votos», que no es «quién votó por usted»
     —eso no lo sabe nadie— ni «cómo es el municipio», que es contra lo que se
     compara para que el número signifique algo. */
  async function perfil(mesas) {
    const lugares = await puestos();
    const edad = await censoEdad();
    const municipio = municipioMayoritario(mesas);
    let votos = 0, conCenso = 0, mujeres = 0, rural = 0, urbano = 0, especial = 0, sinCoordenada = 0;
    const bandas = edad?.bandas || [], edadVotos = bandas.map(() => 0); let conEdad = 0;
    /* Votos en puestos con «bloque de edad»: la página lo declara si pesan. */
    let enBloque = 0; const bloquePuestos = new Map();
    (mesas || []).forEach(m => {
      const v = Number(m.v || 0); if (!v) return;
      votos += v;
      const zona = String(m.zon || '').padStart(2, '0');
      if (zona === '99') rural += v; else if (ZONA_ESPECIAL.has(zona)) especial += v; else urbano += v;
      const code = codigoPuesto(m), p = lugares[code];
      if (p && p.mujeres + p.hombres > 0) { conCenso += v; mujeres += v * p.mujeres / (p.mujeres + p.hombres); } else sinCoordenada += v;
      const e = edad?.puestos?.[code];
      if (e) { const tot = e.reduce((s, x) => s + Number(x || 0), 0); if (tot > 0) { conEdad += v; e.forEach((x, i) => { edadVotos[i] += v * Number(x || 0) / tot; }); } }
      const b = edad?.bloques?.[code];
      if (b != null) { enBloque += v; const q = bloquePuestos.get(code) || { code, banda: bandas[b], votos: 0, nombre: p?.nombre || '', barrio: p?.barrio || '' }; q.votos += v; bloquePuestos.set(code, q); }
    });
    /* El municipio entero, para comparar: el censo de TODOS sus puestos. */
    let munM = 0, munT = 0, munRural = 0, munCenso = 0;
    const edadMunicipio = bandas.map(() => 0); let munConEdad = 0;
    Object.entries(lugares).forEach(([code, p]) => {
      if (code.slice(0, 5) !== municipio) return;
      const censo = p.mujeres + p.hombres; if (!censo) return;
      munM += p.mujeres; munT += censo; munCenso += censo;
      if (code.slice(5, 7) === '99') munRural += censo;
      const e = edad?.puestos?.[code];
      if (e) { const tot = e.reduce((s, x) => s + Number(x || 0), 0); if (tot > 0) { munConEdad += tot; e.forEach((x, i) => { edadMunicipio[i] += Number(x || 0); }); } }
    });
    return {
      votos, municipio,
      mujeres: conCenso ? mujeres / conCenso : null, cobertura: votos ? conCenso / votos : 0, sinCoordenada,
      mujeresMunicipio: munT ? munM / munT : null, ruralMunicipio: munCenso ? munRural / munCenso : null, censoMunicipio: munCenso,
      rural: votos ? rural / votos : 0, urbano: votos ? urbano / votos : 0, especial,
      edad: conEdad ? { bandas, reparto: edadVotos.map(x => x / conEdad), grupos: agruparEdad(edadVotos.map(x => x / conEdad)), cobertura: conEdad / votos, fuente: edad?.fuente || '' } : null,
      edadMunicipio: munConEdad ? { bandas, reparto: edadMunicipio.map(x => x / munConEdad), grupos: agruparEdad(edadMunicipio.map(x => x / munConEdad)) } : null,
      bloque: votos && enBloque ? { votos: enBloque, peso: enBloque / votos, puestos: [...bloquePuestos.values()].sort((a, b) => b.votos - a.votos) } : null,
    };
  }
  function municipioMayoritario(mesas) {
    const votos = {};
    (mesas || []).forEach(m => { const k = `${String(m.dep || '').padStart(2, '0')}${String(m.mun || '').padStart(3, '0')}`; if (k !== '00000') votos[k] = (votos[k] || 0) + Number(m.v || 0); });
    return Object.entries(votos).sort((a, b) => b[1] - a[1])[0]?.[0] || '';
  }

  /* ── Cómo vota el territorio ─────────────────────────────────────────────
     La Asamblea 2023 es la única elección que baja a TODOS los municipios del
     país con el voto por partido (el concejo por comuna existe en once
     ciudades), así que de ahí sale la historia ideológica, con cada
     organización puesta en su familia por partidos-bloques.js. */
  async function ideologia({ departamento, municipio }) {
    const dep = String(departamento || '').padStart(2, '0');
    if (!/^\d{2}$/.test(dep) || dep === '00') return null;
    const r = await json(`${S3}/asamblea-2023/dep/${dep}.json`);
    const mun = municipio ? String(municipio).padStart(3, '0') : '';
    const area = mun ? r?.comunas?.[mun] : null;
    const fuente = area || r?.totals; if (!fuente) return null;
    const organizaciones = fuente.partidos || fuente.top_partidos || [];
    const PB = global.PartidosBloques;
    const porBloque = {}; let total = 0; const sinLinea = [], avales = [];
    organizaciones.forEach(([nombre, v]) => {
      const b = PB?.bloqueDeOrganizacion?.(nombre) || 'sc', n = Number(v) || 0;
      porBloque[b] = (porBloque[b] || 0) + n; total += n;
      if (b === 'sc' && n > 0) sinLinea.push({ nombre, votos: n, aval: Boolean(PB?.esAvalAmplio?.(nombre)) });
      /* Avales que se prestan: tienen familia como partido, pero la lista que
         los llevó en ESTE municipio puede venir de otra. Se advierte. */
      else if (n > 0 && PB?.esAvalAmplio?.(nombre)) avales.push({ nombre, votos: n, bloque: b });
    });
    if (!total) return null;
    sinLinea.sort((a, b) => b.votos - a.votos); avales.sort((a, b) => b.votos - a.votos);
    return { nombre: (area ? fuente.name : r.name) || '', ambito: area ? 'municipio' : 'departamento',
      potencial: Number(fuente.potencial || 0), votantes: Number(fuente.votantes || 0), validos: Number(fuente.validos || 0),
      porBloque, total, sinLinea, avales, organizaciones: organizaciones.slice(0, 10) };
  }

  /* ── El electorado que le falta ──────────────────────────────────────────
     Los votos que le faltan para la meta no se parecen a su base —esos ya los
     tiene—: se parecen al territorio del que los va a sacar. El perfil
     objetivo es el promedio de los dos, pesado por cuántos votos pone cada
     uno. Quien se muda empieza en cero: su votación anterior no cuenta donde
     no la sacó. */
  function objetivo(p, meta, { mismoTerritorio = true } = {}) {
    const m = Number(meta || 0); if (!m || !p) return null;
    const base = mismoTerritorio ? Math.min(Number(p.votos || 0), m) : 0;
    const faltan = Math.max(0, m - base);
    const mezcla = (suyo, terr) => (suyo == null || terr == null) ? null : (base * suyo + faltan * terr) / m;
    const mezclaBandas = (suyo, terr) => (!suyo || !terr) ? null : suyo.map((x, i) => (base * x + faltan * terr[i]) / m);
    const edad = mezclaBandas(p.edad?.reparto, p.edadMunicipio?.reparto);
    return { meta: m, base, faltan, mismoTerritorio,
      mujeres: mezcla(p.mujeres, p.mujeresMunicipio), rural: mezcla(p.rural, p.ruralMunicipio),
      edad, edadGrupos: edad ? agruparEdad(edad) : null };
  }

  /* ── Las mesas de una candidatura ────────────────────────────────────────
     El JSON mesa a mesa vive en la carpeta de su elección y el slug dice
     cuál: «ALC2023-05-001-…» → alcaldia-2023. Resolverlo así le ahorra a la
     página de análisis bajar los índices completos (40 MB) para averiguar una
     URL que el propio slug ya contiene. Ojo con el orden: CONC es concejo y
     CON es congreso. */
  const CARPETAS = [[/^ASAM(\d{4})/, 'asamblea-$1'], [/^CONC(\d{4})/, 'concejo-$1'], [/^JAL(\d{4})/, 'jal-$1'],
    [/^ALC(\d{4})/, 'alcaldia-$1'], [/^GOB(\d{4})/, 'gobernacion-$1'], [/^CON(\d{4})/, 'congreso-$1'],
    [/^CONSU(\d{4})/, 'consu-$1'], [/^PRES(\d{4})/, 'pres-$1']];
  function urlCandidatura(slug) {
    const s = String(slug || ''); if (!s) return '';
    for (const [re, carpeta] of CARPETAS) { const m = s.match(re); if (m) return `${S3}/${carpeta.replace('$1', m[1])}/${s}.json`; }
    return `${S3}/endoso/${s}.json`;   /* lo que no reconocemos, como en cand-index.js */
  }
  /* Una persona puede tener varias candidaturas: sus mesas son la suma. Una
     fuente caída no puede tumbar la lectura de las demás. */
  async function mesasDe(slugs) {
    const partes = await Promise.all((slugs || []).map(s => json(urlCandidatura(s)).then(d => d.mesas || []).catch(() => [])));
    return partes.flat();
  }

  /* El vínculo guarda el municipio por NOMBRE («LA CEJA») y la Asamblea lo
     indexa por código electoral: la capa municipal del departamento tiene los
     dos, así que ella hace de traductora. */
  async function codigoMunicipio(departamento, nombre) {
    const dep = String(departamento || '').padStart(2, '0');
    if (!/^\d{2}$/.test(dep) || !nombre) return '';
    const norm = x => String(x || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replace(/[^A-Z0-9]/g, '');
    const geo = await json(`${S3}/mapas-2026/Departamentos-mps/${dep}.json`).catch(() => null);
    const f = geo?.features?.find(x => norm(x.properties?.mpio_cnmbr) === norm(nombre));
    const codigo = f?.properties?.mun_elec ?? f?.properties?.mun_electoral;
    return codigo === undefined ? '' : String(codigo);
  }

  global.C360Electorado = { perfil, ideologia, objetivo, puestos, censoEdad, sexoEdad, censo2026, cambioCenso, BANDAS_EDAD, GRUPOS_EDAD, agruparEdad, PERFILES, perfiles, VECINAS, votosFamilia, votosFamiliaPartidos, shares, suma6, CIUDADES, ciudadDe, rotar90, json, codigoPuesto, municipioMayoritario, urlCandidatura, mesasDe, codigoMunicipio, ZONA_ESPECIAL };
})(window);
