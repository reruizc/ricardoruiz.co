/* ═══ Candidato 360 · la lectura de ARQUETIPOS (panel 05) ════════════════════
   Qué mueve el voto en cada barrio donde la candidatura saca votos. La usan la
   tarjeta 05 del CRM y la página candidato-360-arquetipos.html: vive acá, en un
   solo sitio, para que las dos no puedan decir cifras distintas del mismo
   barrio (antes estaba dentro de candidato-360.js y la página no existía).

   Dos ciudades, dos modelos que NO se homologan:
   · MEDELLÍN — Proyecto DC: cinco familias, UN arquetipo por barrio (DAP), con
     la proyección 2027 ajustada a mano por la socia (votacion-2027.json se
     aplica igual que en proyecto-dc/arquetipos.html). El puesto se ubica en el
     barrio por COORDENADA: el nombre de la mesa no casa con el del DAP.
   · CARTAGENA — la cartografía emocional de Nury: OCHO arquetipos propios y una
     MEZCLA por barrio (suma 1), así que los votos se reparten con la mezcla y no
     con el dominante. 2015 es ancla; 2019 y 2023 son proyecciones
     retrospectivas; 2027 es simulación. El barrio casa POR NOMBRE con el
     diccionario puesto→barrio del mapa (los 211 de Nury son los 211 de la capa).

   Sin votos propios en la ciudad (una candidatura nueva) se describe la ciudad
   con el volumen que el propio estudio le da a cada barrio, y se dice.

   Depende de C360Electorado (puestos con coordenada, códigos de puesto y de
   municipio) y de RRData. No toca el DOM.                                      */
(function (global) {
  const RR = global.RRData;
  const E = () => global.C360Electorado;
  const MEDELLIN = '01001', CARTAGENA = '05001';
  const ARQ_BASE = RR.publicUrl('bases+de+datos/Proyecto+DC/arquetipos');
  const VOT27_URL = `${RR.publicUrl('bases+de+datos/Proyecto+DC/votacion-arquetipo-2027')}/votacion-2027.json?v=20260528`;
  const ARQ_CTG_BASE = RR.publicUrl('bases+de+datos/Proyecto+DC/arquetipos-cartagena');
  const ARQ_CTG_URL = `${ARQ_CTG_BASE}/arquetipos-cartagena.json?v=20261001`;
  const MDE_BARRIOS_URL = `${RR.publicUrl('bases+de+datos')}/MEDELLIN_BARRIOS_OFICIAL.json`;
  const CTG_BARRIOS_URL = `${RR.publicUrl('congreso-2026/output')}/mapas-2026/Ciudades-COM-LOC/CARTAGENAX.json`;
  /* El diccionario puesto→barrio de Cartagena es el mismo del CRM y del panel
     del electorado; con ?v= porque una copia vieja sin `loc` no da error. */
  const CTG_DIC_JS = 'candidato-360-data/cartagena-puesto-barrio.js?v=20260927';

  const cache = new Map();
  const json = url => {
    if (!cache.has(url)) cache.set(url, fetch(url).then(r => r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status))).catch(e => { cache.delete(url); throw e; }));
    return cache.get(url);
  };
  const scripts = new Map();
  const cargarScript = src => {
    if (!scripts.has(src)) scripts.set(src, new Promise((ok, no) => { const s = document.createElement('script'); s.src = src; s.onload = ok; s.onerror = () => { scripts.delete(src); no(new Error(src)); }; document.head.appendChild(s); }));
    return scripts.get(src);
  };
  const normBarrio = s => String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^A-Za-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim().toUpperCase();
  const codigoMunicipio = mesa => `${String(mesa.dep || '').padStart(2, '0')}${String(mesa.mun || '').padStart(3, '0')}`;
  /* Nury escribe la emoción con «+» («Malestar + búsqueda de solución»): en una frase va «y». */
  const emocion = f => String(f?.emocion || '').replace(/\s*\+\s*/g, ' y ').toLowerCase();

  /* ── Qué ciudad ──────────────────────────────────────────────────────────
     Manda el municipio al que se lanza; si no hay (campaña departamental o la
     ruta «la misma corporación»), donde están la mayoría de sus votos. Y si se
     lanza en otro lado pero sus votos están en una de las dos, se lee ahí.  */
  function ciudadDe(municipioCampana, mesas) {
    const mayor = E().municipioMayoritario(mesas || []);
    const campana = municipioCampana || '';
    if (campana === MEDELLIN || (!campana && mayor === MEDELLIN)) return 'medellin';
    if (campana === CARTAGENA || (!campana && mayor === CARTAGENA)) return 'cartagena';
    if (mayor === MEDELLIN) return 'medellin';
    if (mayor === CARTAGENA) return 'cartagena';
    return null;
  }
  /* El municipio de la campaña guardada en el vínculo, como código electoral
     de 5 dígitos. El formulario guarda el nombre DANE («CARTAGENA DE INDIAS»):
     se traduce con la capa municipal del departamento. */
  async function municipioDeCampana(campana) {
    const c = campana || {};
    if (!['jal', 'concejo', 'alcaldia'].includes(c.corp) || !c.municipio || !c.departamento) return '';
    const mun = await E().codigoMunicipio(c.departamento, c.municipio).catch(() => '');
    return mun ? `${String(c.departamento).padStart(2, '0')}${String(mun).padStart(3, '0')}` : '';
  }

  /* ── Medellín ─────────────────────────────────────────────────────────── */
  let mdePromise = null;
  function datosMedellin() {
    if (!mdePromise) mdePromise = Promise.all([
      json(`${ARQ_BASE}/arquetipos.json`), json(`${ARQ_BASE}/por-barrio.json`), json(`${ARQ_BASE}/por-comuna.json`), json(VOT27_URL).catch(() => null),
    ]).then(([familias, barrios, comunas, vot27]) => {
      Object.entries(vot27?.barrios || {}).forEach(([dap, v]) => {
        const b = barrios[dap]; if (!b || !v.arquetipo_ajustado_2027) return;
        b.proyeccion_2027 = { ...(b.proyeccion_2027 || {}), arquetipo_proy: v.arquetipo_ajustado_2027, arquetipo_alt: v.arquetipo_alterno_2027 || b.proyeccion_2027?.arquetipo_alt };
      });
      return { familias, barrios, comunas };
    }).catch(e => { mdePromise = null; throw e; });
    return mdePromise;
  }
  /* Ray casting con caja envolvente, y hasta 60 m de tolerancia para el puesto
     que cae en el borde: la coordenada de la Registraduría no es de topógrafo. */
  function enAnillo(x, y, a) { let d = false; for (let i = 0, j = a.length - 1; i < a.length; j = i++) { const xi = a[i][0], yi = a[i][1], xj = a[j][0], yj = a[j][1]; if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) d = !d; } return d; }
  function enGeometria(x, y, g) { const ps = g?.type === 'Polygon' ? [g.coordinates] : g?.type === 'MultiPolygon' ? g.coordinates : []; return ps.some(an => enAnillo(x, y, an[0]) && !an.slice(1).some(h => enAnillo(x, y, h))); }
  function indice(geo, code) {
    return (geo?.features || []).map(f => {
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      const r = c => { if (typeof c[0] === 'number') { x0 = Math.min(x0, c[0]); x1 = Math.max(x1, c[0]); y0 = Math.min(y0, c[1]); y1 = Math.max(y1, c[1]); } else c.forEach(r); };
      if (f.geometry?.coordinates) r(f.geometry.coordinates);
      return { f, code: code(f.properties), caja: [x0, y0, x1, y1] };
    }).filter(x => x.code && Number.isFinite(x.caja[0]));
  }
  function barrioDelPunto(idx, lng, lat) {
    if (!Number.isFinite(lng) || !Number.isFinite(lat)) return '';
    for (const it of idx) { const [x0, y0, x1, y1] = it.caja; if (lng < x0 || lng > x1 || lat < y0 || lat > y1) continue; if (enGeometria(lng, lat, it.f.geometry)) return it.code; }
    let mejor = '', dist = 0.00055;
    for (const it of idx) { const [x0, y0, x1, y1] = it.caja; const d = Math.hypot(Math.max(x0 - lng, 0, lng - x1), Math.max(y0 - lat, 0, lat - y1)); if (d < dist) { dist = d; mejor = it.code; } }
    return mejor;
  }
  let mdeGeoPromise = null;
  const geoMedellin = () => mdeGeoPromise || (mdeGeoPromise = json(MDE_BARRIOS_URL).then(geo => ({ geo, idx: indice(geo, p => String(p.CODIGO || '')) })).catch(e => { mdeGeoPromise = null; throw e; }));
  async function leerMedellin(mesas) {
    const [{ familias, barrios, comunas }, capa, puestos] = await Promise.all([datosMedellin(), geoMedellin(), E().puestos()]);
    const comunaDe = {};
    (capa.geo.features || []).forEach(f => { const c = String(f.properties?.CODIGO || ''); if (c && f.properties?.COMUNA) comunaDe[c.slice(0, 2)] = f.properties.COMUNA; });
    const porBarrio = {}, porComuna = {};
    let votos = 0, ubicados = 0;
    (mesas || []).forEach(m => {
      const v = Number(m.v || 0); if (!v || codigoMunicipio(m) !== MEDELLIN) return;
      votos += v;
      const p = puestos[E().codigoPuesto(m)]; if (!p) return;
      const dap = barrioDelPunto(capa.idx, p.lng, p.lat); if (!dap) return;
      ubicados += v; porBarrio[dap] = (porBarrio[dap] || 0) + v;
      const comuna = comunaDe[dap.slice(0, 2)]; if (comuna) porComuna[comuna] = (porComuna[comuna] || 0) + v;
    });
    const conVotos = ubicados > 0;
    const pesos = conVotos ? porBarrio : Object.fromEntries(Object.values(barrios).map(b => [b.dap, Number(b.proyeccion_2027?.votos_por_arquetipo ? Object.values(b.proyeccion_2027.votos_por_arquetipo).reduce((s, x) => s + Number(x || 0), 0) : 0)]));
    const reparto = { '2023': {}, '2027': {} };
    let total = 0, sinDato = 0;
    Object.entries(pesos).forEach(([dap, v]) => {
      if (!v) return; total += v;
      const b = barrios[dap]; if (!b) { sinDato += v; return; }
      const a23 = b.arquetipo?.['2023'], a27 = b.proyeccion_2027?.arquetipo_proy;
      if (a23) reparto['2023'][a23] = (reparto['2023'][a23] || 0) + v;
      if (a27) reparto['2027'][a27] = (reparto['2027'][a27] || 0) + v;
    });
    const orden = o => Object.entries(o).sort((a, b) => b[1] - a[1]);
    const filasComuna = conVotos
      ? orden(porComuna).map(([nombre, v]) => ({ nombre, votos: v, a23: comunas[nombre]?.['2023']?.dominante, a27: comunas[nombre]?.['2027']?.dominante }))
      : Object.entries(comunas).map(([nombre, c]) => ({ nombre, votos: Number(c['2023']?.votos_total || 0), a23: c['2023']?.dominante, a27: c['2027']?.dominante })).sort((a, b) => b.votos - a.votos);
    const filaBarrio = (dap, v) => ({ code: dap, votos: v, nombre: barrios[dap]?.barrio || dap, comuna: barrios[dap]?.comuna || '', a23: barrios[dap]?.arquetipo?.['2023'], a27: barrios[dap]?.proyeccion_2027?.arquetipo_proy, riesgo: barrios[dap]?.proyeccion_2027?.nivel_riesgo });
    const filasBarrio = orden(pesos).filter(([, v]) => v).map(([dap, v]) => filaBarrio(dap, v));
    const A = familias?.arquetipos || {};
    const ids = Object.keys(A).sort((a, b) => (A[a].orden || 0) - (A[b].orden || 0));
    return {
      ciudad: 'medellin', nombreCiudad: 'Medellín', unidad: 'comuna', unidades: 'comunas', familias, barrios, comunas,
      conVotos, total, sinDato, reparto, filasComuna, filasBarrio, pesos, votosCiudad: votos, ubicados, ids,
      nombreDe: (id, año) => { const f = A[id]; return f ? (año === '2027' ? f.evol.nombre : f.base.nombre) : 'Sin dato'; },
      cortoDe: id => A[id]?.label_corto || 'Sin dato',
      colorDe: id => A[id]?.color || '#6b7280',
      /* Para el mapa: el polígono se casa por su CODIGO (DAP). */
      geo: capa.geo, codeDe: p => String(p.CODIGO || ''), nombreGeo: p => p.NOMBRE || 'Barrio',
      dominanteDe: (code, año) => año === '2027' ? barrios[code]?.proyeccion_2027?.arquetipo_proy : barrios[code]?.arquetipo?.['2023'],
      mezclaDe: () => null,
      ficha: id => { const f = A[id]; if (!f) return null; return { id, nombre: f.base.nombre, nombre27: f.evol?.nombre, color: f.color, lema: f.base.deseo, emocion: String(f.base.emocion || '').toLowerCase(), miedo: f.base.miedo, sesgo: f.base.sesgo, escudo: f.base.escudo, escudo27: f.evol?.escudo }; },
    };
  }

  /* ── Cartagena ────────────────────────────────────────────────────────── */
  let ctgPromise = null;
  const datosCartagena = () => ctgPromise || (ctgPromise = json(ARQ_CTG_URL).catch(e => { ctgPromise = null; throw e; }));
  async function leerCartagena(mesas) {
    const [D] = await Promise.all([datosCartagena(), cargarScript(CTG_DIC_JS).catch(() => null)]);
    const dic = global.Candidato360CartagenaPuestoBarrio || {};
    const porBarrio = {};
    let votos = 0, ubicados = 0;
    (mesas || []).forEach(m => {
      const v = Number(m.v || 0); if (!v || codigoMunicipio(m) !== CARTAGENA) return;
      votos += v;
      const k = normBarrio(dic[E().codigoPuesto(m)]?.barrio); if (!k) return;
      ubicados += v; porBarrio[k] = (porBarrio[k] || 0) + v;
    });
    const conVotos = ubicados > 0;
    const pesos = conVotos ? porBarrio : Object.fromEntries(Object.entries(D.barrios).map(([k, b]) => [k, Number(b.volumen?.['2023'] || 0)]));
    const reparto = { '2023': {}, '2027': {} }, porLoc = {};
    let total = 0, sinDato = 0;
    Object.entries(pesos).forEach(([k, v]) => {
      if (!v) return; total += v;
      const b = D.barrios[k]; if (!b) { sinDato += v; return; }
      const L = porLoc[b.localidad] || (porLoc[b.localidad] = { votos: 0, '2023': {}, '2027': {} });
      L.votos += v;
      ['2023', '2027'].forEach(a => Object.entries(b.mezcla[a] || {}).forEach(([id, p]) => {
        reparto[a][id] = (reparto[a][id] || 0) + v * p;
        L[a][id] = (L[a][id] || 0) + v * p;
      }));
    });
    const top = o => Object.entries(o).sort((a, b) => b[1] - a[1])[0]?.[0];
    const filasComuna = Object.entries(porLoc).sort((a, b) => b[1].votos - a[1].votos).map(([nombre, L]) => ({ nombre, votos: L.votos, a23: top(L['2023']), a27: top(L['2027']) }));
    const filasBarrio = Object.entries(pesos).filter(([k, v]) => v && D.barrios[k]).sort((a, b) => b[1] - a[1]).map(([k, v]) => {
      const b = D.barrios[k];
      return { code: k, votos: v, nombre: b.nombre, comuna: b.localidad, a23: b.dominante['2023'], a27: b.dominante['2027'], riesgo: b.volatilidad?.nivel, heredado: /heredado/i.test(b.tipo || '') };
    });
    const F = D.familias;
    const geo = await json(CTG_BARRIOS_URL).catch(() => null);
    return {
      ciudad: 'cartagena', nombreCiudad: 'Cartagena', unidad: 'localidad', unidades: 'localidades', D,
      conVotos, total, sinDato, reparto, filasComuna, filasBarrio, pesos, votosCiudad: votos, ubicados, ids: D.orden || Object.keys(F),
      nombreDe: id => F[id]?.nombre || 'Sin dato', cortoDe: id => F[id]?.nombre || 'Sin dato', colorDe: id => F[id]?.color || '#6b7280',
      geo, codeDe: p => normBarrio(p.NOMBRE), nombreGeo: p => p.NOMBRE || 'Barrio',
      dominanteDe: (code, año) => D.barrios[code]?.dominante?.[año],
      mezclaDe: (code, año) => D.barrios[code]?.mezcla?.[año] || null,
      ficha: id => { const f = F[id]; if (!f) return null; return { ...f, id, emocion: emocion(f), escudo: `${ARQ_CTG_BASE}/escudos/${id}.jpg` }; },
    };
  }

  /* La lectura de una ciudad. */
  function leer(ciudad, mesas) {
    if (ciudad === 'cartagena') return leerCartagena(mesas);
    if (ciudad === 'medellin') return leerMedellin(mesas);
    return Promise.reject(new Error('sin cartografía emocional'));
  }
  /* ── La huella de su PARTIDO o de su familia política en la ciudad ───────
     Para leer los arquetipos desde donde vota su lado, no solo desde donde
     votó usted o la ciudad entera. Misma cascada que el panel del electorado:
       1. la LISTA del partido al Concejo 2023, puesto por puesto;
       2. si no tuvo lista (o no llegó al 1 %), su lista a Cámara 2026 —la de
          Oviedo en Bogotá o Cartagena no existía en 2023—;
       3. la FAMILIA política (la del partido o el espectro que eligió), y si
          no tuvo lista, sus vecinas del espectro.
     Devuelve los votos como «mesas» por puesto, para leerlos con `leer()`
     igual que una votación propia. */
  const S3 = RR.publicUrl('congreso-2026/output');
  const CIUDAD_COD = { cartagena: ['05', '001'], medellin: ['01', '001'] };
  async function huella(ciudad, campana) {
    const PB = global.PartidosBloques, EE = E(), c = campana || {};
    const [dep, mun] = CIUDAD_COD[ciudad] || []; if (!dep) return null;
    const partido = !['firmas', 'indeciso'].includes(c.avales) && c.partido ? c.partido : '';
    const familia = partido ? PB.bloqueDeOrganizacion(partido) : (c.espectro || '');
    const res = await json(`${S3}/concejo-2023/resultados-concejo-2023.json`).catch(() => null);
    const comunas = Object.keys(res?.data?.[`${dep}-${mun}`]?.comunas || {}).filter(k => !['90', '98', 'NULL', ''].includes(k));
    const docs = (await Promise.all(comunas.map(k => json(`${S3}/concejo-2023/comuna/${dep}-${mun}-${k}.json`).catch(() => null)))).filter(Boolean);
    const puestos = [];
    docs.forEach(d => (d.puestos || []).forEach(pu => puestos.push({ code: dep + mun + String(pu.code || '').replace('-', ''), pu, d })));
    const medir2023 = pred => {
      let p = 0, t = 0;
      const filas = puestos.map(x => { const f = EE.votosFamilia(x.pu.v, x.d.cands, x.d.partidos, pred, x.pu.l); p += f.propios; t += f.total; return [x.code, f.propios]; });
      return { share: t ? p / t : 0, votos: p, filas };
    };
    const aMesas = filas => filas.filter(([, v]) => v > 0).map(([code, v]) => ({ dep: code.slice(0, 2), mun: code.slice(2, 5), zon: code.slice(5, 7), pue: code.slice(7), v }));
    if (partido) {
      const pred = EE.calzaPartido(partido);
      const m = medir2023(pred);
      if (m.share >= .01) return { fuente: 'lista', partido, familia, share: m.share, votos: m.votos, mesas: aMesas(m.filas) };
      const cam = await EE.camaraPuestos(dep).catch(() => null);
      if (cam) {
        const codes = Object.keys(cam.puestos || {}).filter(k => k.startsWith(dep + mun));
        const tot = EE.votosCamara(cam, codes, () => true).total;
        const filas = codes.map(k => [k, EE.votosCamara(cam, [k], pred).propios]);
        const votos = filas.reduce((s, [, v]) => s + v, 0);
        if (tot && votos / tot >= .01) return { fuente: 'camara', partido, familia, share: votos / tot, votos, mesas: aMesas(filas) };
      }
    }
    if (familia && familia !== 'sc') {
      let m = medir2023(new Set([familia])), vecinas = false;
      if (m.share < .01 && EE.VECINAS?.[familia]) { m = medir2023(new Set(EE.VECINAS[familia])); vecinas = true; }
      if (m.votos > 0) return { fuente: 'familia', partido, familia, vecinas, share: m.share, votos: m.votos, mesas: aMesas(m.filas) };
    }
    return { fuente: null, partido, familia };
  }
  /* El arquetipo más AFÍN a una huella: el que más pesa en ella comparado con
     lo que pesa en la ciudad (×1,30 = «un 30 % más que en la ciudad»). Se
     exige un 8 % del voto para que un arquetipo marginal no gane por azar:
     con 5 %, en Cartagena ganaba el guardián insular del centro-derecha con
     6 % contra 5 % de la ciudad, que es ruido y no un nicho. */
  function afinidad(L, Lciudad, año = '2023') {
    const sh = (X, id) => (X.reparto[año]?.[id] || 0) / (X.total || 1);
    return (L.ids || []).map(id => ({ id, share: sh(L, id), ciudad: sh(Lciudad, id), ratio: sh(Lciudad, id) ? sh(L, id) / sh(Lciudad, id) : 0 }))
      .filter(x => x.share >= .08).sort((a, b) => b.ratio - a.ratio);
  }
  /* El arquetipo que más pesa en 2023 y su porcentaje. */
  function principal(L, año = '2023') {
    const top = Object.entries(L.reparto[año] || {}).sort((a, b) => b[1] - a[1])[0];
    return top ? { id: top[0], votos: top[1], share: L.total ? top[1] / L.total : 0 } : null;
  }

  global.C360ArqLectura = { MEDELLIN, CARTAGENA, ciudadDe, municipioDeCampana, leer, principal, huella, afinidad, emocion, normBarrio };
})(window);
