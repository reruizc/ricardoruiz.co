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

  /* ── El censo por puesto de votación ─────────────────────────────────────
     Columnas de PUESTOS_GEOREF: 1 código completo (dep+mun+zona+puesto),
     7 barrio, 9/10 lat/lng, 13/14 mujeres/hombres — la suma es el censo. */
  let puestosPromise = null;
  function puestos() {
    if (!puestosPromise) puestosPromise = fetch(`${S3}/mapas-2026/PUESTOS_GEOREF.csv`).then(r => r.ok ? r.text() : Promise.reject(new Error('sin PUESTOS_GEOREF'))).then(raw => {
      const lookup = {};
      raw.split(/\r?\n/).slice(1).forEach(line => {
        const row = line.split(';'), code = String(row[1] || ''), barrio = row[7];
        if (!code || !barrio) return;
        const mesa = { dep: code.slice(0, 2), mun: code.slice(2, 5), zon: code.slice(5, 7), pue: code.slice(7, 9), com: String(row[11] || ''), comNom: String(row[12] || '') };
        const mujeres = Number(row[13]) || 0, hombres = Number(row[14]) || 0;
        lookup[code] = { barrio, lat: Number(row[9]), lng: Number(row[10]), censo: mujeres + hombres, mujeres, hombres, mesa };
      });
      return lookup;
    }).catch(e => { puestosPromise = null; throw e; });
    return puestosPromise;
  }
  /* La edad vive en un archivo aparte que puede no estar publicado todavía:
     que falte no puede tumbar el resto de la lectura. */
  let edadPromise = null;
  function censoEdad() {
    if (!edadPromise) edadPromise = fetch(`${S3}/mapas-2026/CENSO_EDAD_PUESTO.json`).then(r => r.ok ? r.json() : null).catch(() => null);
    return edadPromise;
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
    (mesas || []).forEach(m => {
      const v = Number(m.v || 0); if (!v) return;
      votos += v;
      const zona = String(m.zon || '').padStart(2, '0');
      if (zona === '99') rural += v; else if (ZONA_ESPECIAL.has(zona)) especial += v; else urbano += v;
      const code = codigoPuesto(m), p = lugares[code];
      if (p && p.mujeres + p.hombres > 0) { conCenso += v; mujeres += v * p.mujeres / (p.mujeres + p.hombres); } else sinCoordenada += v;
      const e = edad?.puestos?.[code];
      if (e) { const tot = e.reduce((s, x) => s + Number(x || 0), 0); if (tot > 0) { conEdad += v; e.forEach((x, i) => { edadVotos[i] += v * Number(x || 0) / tot; }); } }
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
      edad: conEdad ? { bandas, reparto: edadVotos.map(x => x / conEdad), cobertura: conEdad / votos, fuente: edad?.fuente || '' } : null,
      edadMunicipio: munConEdad ? { bandas, reparto: edadMunicipio.map(x => x / munConEdad) } : null,
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
    const porBloque = {}; let total = 0; const sinLinea = [];
    organizaciones.forEach(([nombre, v]) => {
      const b = PB?.bloqueDeOrganizacion?.(nombre) || 'sc', n = Number(v) || 0;
      porBloque[b] = (porBloque[b] || 0) + n; total += n;
      if (b === 'sc' && n > 0) sinLinea.push({ nombre, votos: n, aval: Boolean(PB?.esAvalSinLinea?.(nombre)) });
    });
    if (!total) return null;
    sinLinea.sort((a, b) => b.votos - a.votos);
    return { nombre: (area ? fuente.name : r.name) || '', ambito: area ? 'municipio' : 'departamento',
      potencial: Number(fuente.potencial || 0), votantes: Number(fuente.votantes || 0), validos: Number(fuente.validos || 0),
      porBloque, total, sinLinea, organizaciones: organizaciones.slice(0, 10) };
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
    return { meta: m, base, faltan, mismoTerritorio,
      mujeres: mezcla(p.mujeres, p.mujeresMunicipio), rural: mezcla(p.rural, p.ruralMunicipio),
      edad: mezclaBandas(p.edad?.reparto, p.edadMunicipio?.reparto) };
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

  global.C360Electorado = { perfil, ideologia, objetivo, puestos, censoEdad, codigoPuesto, municipioMayoritario, urlCandidatura, mesasDe, codigoMunicipio, ZONA_ESPECIAL };
})(window);
