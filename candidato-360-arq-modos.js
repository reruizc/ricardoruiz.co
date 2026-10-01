/* ═══ Candidato 360 · panel 05 · los modos «Ver arquetipos» y «Simulación» ═══
   Dos vistas más sobre la cartografía emocional, encima de la lectura de
   siempre («Leer desde»). Sirven para Cartagena y Medellín, cada una con SU
   modelo — no se homologan — a través de un adaptador por ciudad (`ADAPT`).

   · VER ARQUETIPOS — el mapa de la ciudad entera y, al tocar un barrio, su
     ficha completa armada SOLO con el dato del estudio: qué arquetipo manda y
     con cuánto, su trayectoria 2015→2027, cómo votó, qué tan estable es y qué
     significa ese arquetipo para una campaña. No hay texto de internet ni de
     un modelo: con cientos de barrios no habría cómo verificar cada frase, y
     una ficha que inventa un rasgo del barrio es peor que una que se queda en
     el dato.

   · SIMULACIÓN — palancas de −5 a +5, como el simulador de Proyecto DC, que
     mueven la MEZCLA de cada barrio y pintan el arquetipo que queda mandando:
       peso'(a) ∝ peso(a) · exp( K · resp(barrio) · Σ empuje(tema) · (sens(a,tema) − media del tema) )
     · empuje = −valor si la derecha es mejora (el deterioro activa al
       arquetipo sensible al tema; la mejora lo calma), +valor si la palanca
       mide el problema (costo de vida que sube).
     · Se centra en la media del tema entre los arquetipos de la ciudad: si
       todos son muy sensibles a un tema, moverlo cambia poco quién manda. Es
       lo que dice el dato, no un defecto.
     · resp(barrio) crece con lo volátil que ha sido el barrio; la palanca
       «Apertura al cambio» la escala.
     · La aprobación del alcalde arranca en la cifra MEDIDA de cada ciudad
       (Cómo Vamos 2025); a qué arquetipos mueve es regla nuestra.
     Sirve para COMPARAR escenarios, no para pronosticar.

   ⚠️ Producto general: ningún texto visible nombra a quien construyó la
   cartografía. Se habla de «el estudio» o «la cartografía emocional».

   ⚠️ Medellín: la mezcla 2015-2023 es el puntaje relativo del estudio
   (normalizado a 1) y la de 2027 son sus probabilidades de proyección. Como
   el estudio AJUSTÓ a mano el arquetipo 2027 de 48 barrios, la mezcla 2027 se
   reordena para que el ajustado quede primero (intercambia su peso con el que
   el modelo ponía arriba): así, con las palancas en cero, la simulación
   coincide con el mapa.                                                      */
(function (global) {
  'use strict';
  const AÑOS = ['2015', '2019', '2023', '2027'];
  const K = 0.085;
  /* Cuánto pesa la palanca del alcalde frente a las temáticas. */
  const PESO_ALCALDE = 2.4;

  /* Las palancas. `tema` = llave de `sens` del arquetipo. `sign:+1` → la
     derecha es mejora; `sign:-1` → la derecha es el problema. Una palanca
     cuyo tema no califica ningún arquetipo de la ciudad no se muestra. */
  const PALANCAS = [
    { id: 'seguridad', tema: 'seguridad', sign: 1, label: 'Seguridad percibida', hint: '−5 deterioro · +5 mejora visible' },
    { id: 'empleo', tema: 'empleo', sign: 1, label: 'Empleo e ingresos', hint: '−5 desempleo · +5 mejora' },
    { id: 'costo', tema: 'empleo', sign: -1, label: 'Costo de vida', hint: '−5 baja · +5 sube' },
    { id: 'servicios', tema: 'servicios', sign: 1, label: 'Agua, luz y servicios', hint: '−5 cortes y fallas · +5 servicio estable' },
    { id: 'movilidad', tema: 'movilidad', sign: 1, label: 'Movilidad', hint: '−5 trancones y fallas · +5 fluidez' },
    { id: 'vivienda', tema: 'vivienda', sign: 1, label: 'Vivienda, espacio público y turismo', hint: '−5 desorden y deterioro · +5 mejora' },
    { id: 'corrupcion', tema: 'corrupcion', sign: 1, label: 'Transparencia', hint: '−5 escándalo · +5 gestión limpia y verificable' },
    { id: 'ambiente', tema: 'ambiente', sign: 1, label: 'Ambiente y riesgo (inundación, erosión)', hint: '−5 emergencia · +5 mejora' },
    { id: 'salud', tema: 'salud_educacion', sign: 1, label: 'Salud y educación', hint: '−5 deterioro · +5 mejora' },
    { id: 'participacion', tema: 'participacion', sign: 1, label: 'Cumplimiento y presencia institucional', hint: '−5 promesas incumplidas · +5 acuerdos cumplidos' },
    { id: 'cultura', tema: 'cultura', sign: 1, label: 'Reconocimiento del barrio', hint: '−5 invisibilización · +5 reconocimiento' },
    { id: 'alcaldia', especial: true, ancla: true, label: 'Aprobación de la gestión del alcalde' },
    { id: 'apertura', especial: true, label: 'Apertura al cambio', hint: '−5 los barrios se aferran · +5 todo se mueve' },
  ];
  const ESCENARIOS = [
    ['Crisis de agua y servicios', { servicios: -5, participacion: -3, alcaldia: -3 }],
    ['Ola de inseguridad', { seguridad: -5 }],
    ['Escándalo en la Alcaldía', { corrupcion: -5, alcaldia: -3 }],
    ['Golpe económico', { empleo: -4, costo: 4 }],
    ['Temporada de lluvias', { ambiente: -4, movilidad: -2, servicios: -2 }],
    ['Gestión que se ve', { servicios: 3, movilidad: 3, seguridad: 2, alcaldia: 3 }],
  ];

  /* ── Los adaptadores ────────────────────────────────────────────────────
     Cada uno devuelve, a partir de la lectura de su ciudad (`L`), lo mismo:
     arquetipos (`orden`, `fam`), barrios normalizados (`B`), cómo encuadrar,
     el ancla del alcalde, a quién mueve esa palanca y la parte de la ficha
     que solo esa ciudad tiene. */
  const ADAPT = {
    cartagena(L) {
      const D = L.D, F = D.familias;
      const B = {};
      for (const [code, b] of Object.entries(D.barrios)) {
        B[code] = {
          nombre: b.nombre, unidad: b.localidad, dom: b.dominante, mez: b.mezcla,
          resp: 0.55 + 3 * (b.volatilidad?.media || .15), volNivel: b.volatilidad?.nivel,
          peso: { '2015': b.volumen?.['2015'], '2019': b.volumen?.['2019'], '2023': b.volumen?.['2023'], '2027': b.volumen?.['2027_base'] },
          raw: b,
        };
      }
      return {
        id: 'cartagena', nombre: 'Cartagena', ventana: [[10.275, -75.58], [10.47, -75.415]],
        nat: { '2015': 'ancla', '2019': 'proyección retrospectiva', '2023': 'proyección retrospectiva', '2027': 'simulación' },
        orden: D.orden, B,
        fam: id => F[id] && { nombre: F[id].nombre, largo: F[id].nombre, color: F[id].color, sens: F[id].sens || {} },
        mezcla: 'mezcla',
        share: a => D.ciudad_share?.[a] || null,
        movilidad: 'Movilidad (vías, Transcaribe, lanchas)',
        ancla: {
          alcalde: 'Dumek Turbay', valor: 52, paso: 6, imagen: 74,
          fuente: 'Cartagena Cómo Vamos 2025', detalle: 'Cifras & Conceptos, octubre de 2025, 1.071 encuestas, ±4,7 %',
          url: 'https://cartagenacomovamos.org/wp-content/uploads/2026/02/Encuesta-Percepcion-Ciudadana-Cartagena-2025vf.pdf',
          nota: 'Con la Ley 2494 de 2025 la encuesta ya no publica el desglose por localidad, así que el ancla es la misma en cada barrio.',
        },
        /* Arriba premia a quien valora la gestión que funciona y el vínculo;
           abajo, a quien castiga o vigila. */
        alcaldia: { mas: { 'pragmatico-servicios': .6, 'guardian-funcional': .5, 'mediador-comunitario': .5, 'productivo-pragmatico': .3 },
          menos: { 'protesta-resolutiva': .9, 'gestor-vigilante': .6, 'defensor-territorial': .3 } },
        introVer: n => `Los ${n} barrios de la cartografía emocional de Cartagena, con sus ocho arquetipos. Cada barrio es una mezcla de los ocho: el color es el que manda.`,
        notaMapa: ' El mapa abre sobre el casco urbano; las islas siguen ahí si aleja.',
        ficha: null, /* se asigna abajo */
        campana: id => { const f = F[id] || {}; return { lema: f.lema, perfil: f.perfil ? `${f.perfil}${f.edades ? ` (${f.edades} años)` : ''}` : '', decide: f.decide, enciende: f.sube, calma: f.baja, temas: (f.tematicas || []).slice(0, 3).map(([n, v]) => `${n} (${v}/5)`).join(', '), representativos: f.representativos }; },
      };
    },
    medellin(L) {
      const A = L.familias?.arquetipos || {}, FAM = global.C360Arquetipos?.FAMILIAS || [];
      const sensDe = id => FAM.find(f => f.slug === id)?.sens || {};
      const norma = o => { const t = Object.values(o || {}).reduce((s, x) => s + Number(x || 0), 0); return t ? Object.fromEntries(Object.entries(o).map(([k, v]) => [k, Number(v || 0) / t])) : null; };
      const B = {};
      for (const [code, b] of Object.entries(L.barrios || {})) {
        const dom = { '2015': b.arquetipo?.['2015'], '2019': b.arquetipo?.['2019'], '2023': b.arquetipo?.['2023'], '2027': b.proyeccion_2027?.arquetipo_proy };
        const mez = { '2015': norma(b.scores?.['2015']), '2019': norma(b.scores?.['2019']), '2023': norma(b.scores?.['2023']), '2027': norma(b.proyeccion_2027?.probs) };
        /* El ajuste a mano del 2027 queda primero (ver cabecera). */
        const m = mez['2027'], d = dom['2027'];
        if (m && d && m[d] != null) { const t = Object.entries(m).sort((x, y) => y[1] - x[1])[0][0]; if (t !== d) { const v = m[t]; m[t] = m[d]; m[d] = v; } }
        B[code] = {
          nombre: b.barrio, unidad: b.comuna, dom, mez,
          /* Más baja que en Cartagena a propósito: aquí el perfil de cada barrio
             es más parejo (el dominante 2027 ronda 45-55 %) y con la misma
             respuesta un solo escenario volteaba tres de cada cuatro barrios. */
          resp: 0.25 + 0.7 * (b.proyeccion_2027?.riesgo_cambio ?? .54), volNivel: b.proyeccion_2027?.nivel_riesgo,
          peso: b.votos || {}, raw: b,
        };
      }
      const orden = Object.keys(A).sort((a, b) => (A[a].orden || 0) - (A[b].orden || 0));
      return {
        id: 'medellin', nombre: 'Medellín', ventana: null,
        nat: { '2015': 'lectura observada', '2019': 'lectura observada', '2023': 'lectura observada', '2027': 'proyección ajustada' },
        orden, B,
        fam: id => A[id] && { nombre: A[id].label_corto || A[id].base?.nombre, largo: A[id].base?.nombre, color: A[id].color, sens: sensDe(id) },
        mezcla: 'perfil',
        share: () => null,
        movilidad: 'Movilidad (vías, metro, buses)',
        ancla: {
          alcalde: 'Federico Gutiérrez', valor: 61, paso: 6, imagen: 74,
          fuente: 'Medellín Cómo Vamos 2025', detalle: 'Invamer, octubre de 2025, 1.800 encuestas, ±2,31 %',
          url: 'https://www.medellincomovamos.org/wp-content/uploads/2025/12/20251116-ENCUESTA-DE-PERCEPCION-CIUDADANA-2025-MEDELLIN-VF.pdf',
          nota: 'La encuesta no publica la gestión del alcalde por comuna, así que el ancla es la misma en cada barrio.',
        },
        /* La misma regla del simulador de Proyecto DC: arriba refuerza
           continuidad y protección; abajo, castigo. */
        alcaldia: { mas: { continuidad: .7, proteccion: .5 }, menos: { castigo: .9, supervivencia: .2 } },
        introVer: n => `Los ${n} barrios del estudio de Medellín, con sus cinco arquetipos. Cada barrio tiene un arquetipo que manda; la ficha muestra también cómo puntúa en los otros cuatro. Los corregimientos no están en el estudio y quedan en gris.`,
        notaMapa: ' Los corregimientos no están en el estudio.',
        ficha: null,
        campana: id => {
          const f = FAM.find(x => x.slug === id) || {}, a = A[id] || {};
          return { lema: f.tagline, perfil: a.base?.deseo ? `Quiere ${a.base.deseo.charAt(0).toLowerCase()}${a.base.deseo.slice(1)}` : '', decide: a.base?.sesgo, enciende: f.activa, calma: f.desmoviliza, fuga: f.fuga, tono: f.tono, canales: f.canales, miedo: a.base?.miedo };
        },
      };
    },
  };

  let C = null, X = null;   // C: contexto de la página · X: adaptador de la ciudad activa
  const S = { modo: 'lectura', verAno: '2027', verPinta: null, verSel: null, simBase: '2027', simVer: 'dom', simSel: null, pal: {} };
  PALANCAS.forEach(p => { S.pal[p.id] = 0; });
  const M = { ver: null, verCapa: null, sim: null, simCapa: null };

  const esc = s => C.P.esc(s);
  const $ = id => document.getElementById(id);
  const pct = x => `${Math.round((x || 0) * 100)} %`;
  const pp = x => { const r = Math.round(x * 1000) / 10; return `${r > 0 ? '+' : r < 0 ? '−' : '±'}${Math.abs(r).toString().replace('.', ',')} pp`; };
  const num = x => Math.round(Number(x || 0)).toLocaleString('es-CO');
  const dec = x => String(x).replace('.', ',');
  const lugar = s => C.P.lugar(s);
  const L = () => C.lectura();
  const F = id => X.fam(id);
  const color = id => F(id)?.color || '#9aa09a';
  const nombre = id => F(id)?.nombre || 'sin dato';
  const chip = id => id ? `<span class="aq-chip"><i style="background:${color(id)}"></i>${esc(nombre(id))}</span>` : '<span class="aq-chip" style="color:var(--muted)">sin dato</span>';
  const orden = mez => Object.entries(mez || {}).sort((a, b) => b[1] - a[1]);
  const top = mez => orden(mez)[0]?.[0];
  const valorAlcaldia = v => X.ancla.valor + v * X.ancla.paso;
  const visible = p => p.especial || X.orden.some(id => F(id)?.sens?.[p.tema] != null);

  /* La ciudad: participación de cada arquetipo, pesada por el volumen de
     cada barrio en ese año. Cartagena la trae calculada por el estudio. */
  function share(a) {
    const dada = X.share(a); if (dada) return dada;
    const o = {}; let t = 0;
    for (const b of Object.values(X.B)) { const w = Number(b.peso?.[a] || 0), m = b.mez?.[a]; if (!w || !m) continue; t += w; for (const [id, p] of Object.entries(m)) o[id] = (o[id] || 0) + w * p; }
    for (const id in o) o[id] /= t || 1;
    return o;
  }
  function domCount(a) { const c = {}; Object.values(X.B).forEach(b => { const d = b.dom?.[a]; if (d) c[d] = (c[d] || 0) + 1; }); return c; }

  /* ── El cambio de modo ──────────────────────────────────────────────── */
  function pintarModos() {
    const caja = $('aqModos');
    if (!X) { caja.classList.add('hidden'); return; }
    caja.classList.remove('hidden');
    const ops = [['lectura', 'Su lectura', 'leer desde sus votos, su lado o la ciudad'], ['ver', 'Ver arquetipos', 'el mapa y la ficha de cada barrio'], ['sim', 'Simulación', 'mueva palancas y vea qué cambia']];
    caja.innerHTML = `<span class="rot">Ver</span>` + ops.map(([k, t, sub]) => `<button type="button" class="aq-lente" data-modo="${k}" aria-pressed="${S.modo === k}">${esc(t)}<small>${esc(sub)}</small></button>`).join('');
    caja.querySelectorAll('[data-modo]').forEach(b => b.addEventListener('click', () => usarModo(b.dataset.modo)));
  }
  function usarModo(m) {
    if (!X) return;
    S.modo = m;
    pintarModos();
    $('aqLectura').classList.toggle('hidden', m !== 'lectura');
    $('aqLentes').classList.toggle('hidden', m === 'ver');
    $('aqVer').classList.toggle('hidden', m !== 'ver');
    $('aqSim').classList.toggle('hidden', m !== 'sim');
    if (m === 'ver') pintarVer();
    if (m === 'sim') pintarSim();
    try { history.replaceState(null, '', m === 'lectura' ? location.pathname + location.search : `#${m === 'ver' ? 'arquetipos' : 'simulacion'}`); } catch {}
  }
  /* La lente cambió (Leer desde): la simulación lee el reparto de esa lente. */
  function lenteCambio() { if (S.modo === 'sim') pintarResumenSim(); if (S.modo === 'ver' && S.verSel) fichaVer(S.verSel); }

  function crearMapa(id) {
    const m = global.L.map(id, { zoomControl: true, attributionControl: false, scrollWheelZoom: false, zoomSnap: .25 });
    m.setView([6.25, -75.57], 12);
    /* Leaflet mide el contenedor al crearse y aquí nace oculto. */
    if (global.ResizeObserver) new ResizeObserver(() => m.invalidateSize()).observe($(id));
    return m;
  }
  /* Cartagena encuadra su ventana urbana (las islas llegan 100 km al sur);
     Medellín, los barrios del estudio (sin los corregimientos). */
  function encuadrar(m, capa) {
    setTimeout(() => {
      m.invalidateSize();
      if (X.ventana) return m.fitBounds(X.ventana, { animate: false });
      const b = global.L.latLngBounds([]);
      capa.eachLayer(l => { if (X.B[L().codeDe(l.feature.properties)]) b.extend(l.getBounds()); });
      if (b.isValid()) m.fitBounds(b, { padding: [8, 8], animate: false });
    }, 0);
  }

  /* ═══ VER ARQUETIPOS ════════════════════════════════════════════════════ */
  function pintarVer() {
    const l = L();
    $('aqVerIntro').textContent = X.introVer(Object.keys(X.B).length) + ' Toque un barrio para ver su ficha: qué arquetipo manda y con cuánto, cómo ha cambiado desde 2015, cómo ha votado y qué significa ese arquetipo para una campaña.';
    if (!l.geo) { $('aqVerMapa').classList.add('hidden'); $('aqVerNota').textContent = 'La cartografía de barrios no respondió.'; return; }
    $('aqVerControles').innerHTML = `<span class="rot">Año</span>${AÑOS.map(a => `<button type="button" class="aq-tog" data-ano="${a}" aria-pressed="${S.verAno === a}">${a} · ${X.nat[a]}</button>`).join('')}`;
    $('aqVerControles').querySelectorAll('[data-ano]').forEach(b => b.addEventListener('click', () => { S.verAno = b.dataset.ano; pintarVer(); }));
    const nuevo = !M.ver;
    if (nuevo) M.ver = crearMapa('aqVerMapa'); else setTimeout(() => M.ver.invalidateSize(), 0);
    if (M.verCapa) M.ver.removeLayer(M.verCapa);
    const a = S.verAno, pinta = S.verPinta;
    const maxPeso = pinta ? Math.max(.01, ...Object.values(X.B).map(b => b.mez?.[a]?.[pinta] || 0)) : 1;
    M.verCapa = global.L.geoJSON(l.geo, {
      style: f => {
        const code = l.codeDe(f.properties), b = X.B[code], dom = b?.dom?.[a], sel = code === S.verSel;
        if (!b || !dom) return { color: '#fff', weight: .6, fillColor: '#c9ccc4', fillOpacity: .18 };
        if (pinta) { const p = b.mez?.[a]?.[pinta] || 0; return { color: sel ? '#111' : '#fff', weight: sel ? 2.4 : .6, fillColor: color(pinta), fillOpacity: .06 + .84 * Math.sqrt(p / maxPeso) }; }
        const pd = b.mez?.[a]?.[dom];
        return { color: sel ? '#111' : '#fff', weight: sel ? 2.4 : .6, fillColor: color(dom), fillOpacity: pd == null ? .75 : .35 + .6 * Math.min(1, Math.max(0, (pd - .2) / .5)) };
      },
      onEachFeature: (f, layer) => {
        const code = l.codeDe(f.properties), b = X.B[code];
        layer.bindTooltip(`<b>${esc(lugar(l.nombreGeo(f.properties)))}</b> · ${b?.dom?.[a] ? esc(nombre(b.dom[a])) : 'sin medición'}`, { className: 'aq-tt', sticky: true });
        if (b) layer.on('click', () => { S.verSel = code; fichaVer(code); M.verCapa.setStyle(M.verCapa.options.style); if (matchMedia('(max-width:900px)').matches) $('aqVerFicha').scrollIntoView({ behavior: 'instant', block: 'start' }); });
      },
    }).addTo(M.ver);
    if (nuevo) encuadrar(M.ver, M.verCapa);
    /* Leyenda: tocar un arquetipo pinta cuánto pesa en cada barrio. */
    const cuenta = domCount(a);
    $('aqVerLeyenda').innerHTML = `<span class="rot">${pinta ? 'Pinta el peso de' : 'Toque uno para ver dónde pesa'}</span>` + X.orden.map(id => `<button type="button" class="aq-ley" data-arq="${id}" aria-pressed="${pinta === id}"><i style="background:${color(id)}"></i>${esc(nombre(id))} <em>${cuenta[id] || 0}</em></button>`).join('') + (pinta ? '<button type="button" class="aq-ley" data-arq="">← volver al que manda</button>' : '');
    $('aqVerLeyenda').querySelectorAll('[data-arq]').forEach(b => b.addEventListener('click', () => { S.verPinta = b.dataset.arq && b.dataset.arq !== S.verPinta ? b.dataset.arq : null; pintarVer(); }));
    $('aqVerNota').innerHTML = (pinta
      ? `Intensidad: cuánto pesa <b>${esc(nombre(pinta))}</b> en el ${X.mezcla} de cada barrio (${a}). El número junto a cada arquetipo es en cuántos barrios manda.`
      : `Color: el arquetipo que manda en cada barrio (${a}, ${X.nat[a]}); más intenso, más concentrado. El número junto a cada arquetipo es en cuántos barrios manda.`) + X.notaMapa;
    if (S.verSel && X.B[S.verSel]) fichaVer(S.verSel); else $('aqVerFicha').innerHTML = fichaCiudad();
  }

  /* Sin barrio elegido: la ciudad y cómo usar el mapa. */
  function fichaCiudad() {
    const a = S.verAno, sh = share(a), cuenta = domCount(a);
    return `<h4>${esc(X.nombre)} · ${a}</h4><p class="aq-v-sub">Toque un barrio en el mapa para ver su ficha completa.</p>
      ${barra(sh)}<ul class="aq-lista">${orden(sh).map(([id, p]) => `<li><span class="pt" style="background:${color(id)}"></span><b>${pct(p)}</b><span>${esc(nombre(id))}</span><em>${cuenta[id] || 0} barrios</em></li>`).join('')}</ul>
      <p class="aq-v-nota">El porcentaje es el peso de cada arquetipo en el voto de la ciudad (ponderado por el volumen de cada barrio). ${a} es ${X.nat[a]}.</p>`;
  }
  const barra = mez => `<div class="aq-barra">${orden(mez).map(([id, p]) => `<i style="flex:${p};background:${color(id)}" title="${esc(nombre(id))} ${pct(p)}"></i>`).join('')}</div>`;

  /* La lectura escrita del barrio, armada con sus datos. */
  function relato(code, a) {
    const b = X.B[code], mez = orden(b.mez?.[a]), d = b.dom?.[a];
    const pd = b.mez?.[a]?.[d], seg = mez.find(([id]) => id !== d);
    const cs = share(a)?.[d] || 0;
    const partes = [`<b>${esc(lugar(b.nombre))}</b> es un barrio de <b>${esc(nombre(d))}</b>${pd != null ? `: en ${a} ese arquetipo explica el <b>${pct(pd)}</b> de su ${X.mezcla}${seg ? `, y le sigue ${esc(nombre(seg[0]))} con ${pct(seg[1])}` : ''}` : ` en ${a}`}.`];
    if (pd != null) partes.push(pd >= .6 ? 'Es un barrio de lectura clara: un solo arquetipo ordena a la mayoría.' : pd >= .45 ? 'Manda, pero con competencia: un mensaje solo para ese arquetipo deja afuera a buena parte del barrio.' : 'Es un barrio mixto: ningún arquetipo se despega.');
    if (cs && pd != null) partes.push(`En la ciudad, ${esc(nombre(d))} pesa ${pct(cs)}: aquí, ${dec((pd / cs).toFixed(1))} veces eso.`);
    const doms = AÑOS.map(x => b.dom?.[x]).filter(Boolean);
    const cambios = doms.slice(1).filter((x, i) => x !== doms[i]).length;
    partes.push(cambios ? `Su dominante cambió ${cambios === 1 ? 'una vez' : `${cambios} veces`} entre 2015 y 2027 (${doms.map(x => esc(nombre(x))).join(' → ')}).` : 'Ha tenido el mismo dominante en todos los cortes, de 2015 a 2027.');
    const rep = X.campana(d)?.representativos;
    const n = s => String(s || '').toUpperCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
    if (rep && n(rep).includes(n(b.nombre))) partes.push(`Es uno de los barrios más representativos de ${esc(nombre(d))} según el estudio.`);
    return partes.join(' ');
  }

  function fichaVer(code) {
    const b = X.B[code]; if (!b) return;
    const a = S.verAno, d = b.dom?.[a];
    const votos = C.votos?.()?.[code];
    const loc = Object.values(X.B).filter(x => x.unidad === b.unidad), locIgual = loc.filter(x => x.dom?.[a] === d).length;
    const sh = share(a);
    const tray = AÑOS.map(x => `<div class="aq-tray-p"><small>${x}</small>${chip(b.dom?.[x])}${b.mez?.[x]?.[b.dom?.[x]] != null ? `<em>${pct(b.mez[x][b.dom[x]])}</em>` : ''}</div>`).join('<span class="aq-tray-f">→</span>');
    const cp = X.campana(d) || {};
    const fila = (t, v) => v ? `<p><span>${t}:</span> ${esc(v)}</p>` : '';
    $('aqVerFicha').innerHTML = `
      <h4>${esc(lugar(b.nombre))}</h4>
      <p class="aq-v-sub">${esc(lugar(b.unidad))}${X.ficha.sub(b)}</p>
      ${votos ? `<p class="aq-v-votos">${esc(C.voz().unidad)} acá: <b>${num(votos)}</b></p>` : ''}
      <p class="aq-v-relato">${relato(code, a)}</p>
      ${b.mez?.[a] ? `<h5>${X.mezcla === 'perfil' ? 'Su perfil' : 'La mezcla'} en ${a}</h5>${barra(b.mez[a])}
      <ul class="aq-lista">${orden(b.mez[a]).filter(([, p]) => p >= .02).map(([id, p]) => `<li><span class="pt" style="background:${color(id)}"></span><b>${pct(p)}</b><span>${esc(nombre(id))}</span><em>ciudad ${pct(sh?.[id])}</em></li>`).join('')}</ul>
      ${X.id === 'medellin' ? `<p class="aq-v-nota">${a === '2027' ? 'Probabilidad de cada arquetipo en la proyección 2027.' : 'Puntaje relativo de cada arquetipo en el estudio, llevado a 100.'}</p>` : ''}` : ''}
      <h5>Su trayectoria</h5><div class="aq-tray">${tray}</div>
      ${X.ficha.cuerpo(b, a)}
      <h5>Qué significa para una campaña</h5>
      <div class="aq-v-arq" style="--c:${color(d)}">
        <b>${esc(F(d)?.largo || nombre(d))}</b>${cp.lema ? ` · <em>${esc(cp.lema)}</em>` : ''}
        ${fila('Quién es', cp.perfil)}${fila('Cómo decide', cp.decide)}${fila('Lo enciende', cp.enciende)}${fila('Lo calma', cp.calma)}
        ${fila('A qué le teme', cp.miedo)}${fila('Si no se le cumple', cp.fuga)}${fila('Cómo hablarle', cp.tono)}${fila('Por dónde', cp.canales)}
        ${cp.temas ? `<p><span>Temas que lo mueven:</span> ${esc(cp.temas)}.</p>` : ''}
      </div>
      <p class="aq-v-nota">En ${esc(lugar(b.unidad))}, ${locIgual} de ${loc.length} barrios tienen el mismo arquetipo dominante en ${a}.</p>
      <button type="button" class="ghost aq-v-cerrar" id="aqVerCerrar">← Ver la ciudad</button>`;
    $('aqVerCerrar').onclick = () => { S.verSel = null; pintarVer(); };
  }

  /* La parte de la ficha propia de cada estudio. */
  const conc = v => v == null ? '—' : `${dec(v)} %`;
  const FICHA = {
    cartagena: {
      sub: b => { const r = b.raw, her = /heredado/i.test(r.tipo || ''); return ` · ${her ? `sin puesto propio${r.cercano?.cluster ? ` · lectura heredada de ${esc(lugar(r.cercano.cluster))}${r.cercano.km ? ` (${dec(r.cercano.km)} km)` : ''}` : ''}` : 'con puesto de votación propio'} · confianza ${esc(String(r.confianza || '').toLowerCase())}`; },
      cuerpo: b => {
        const r = b.raw, ev = r.evidencia || {}, her = /heredado/i.test(r.tipo || ''), vol = r.volumen || {};
        const emo = ['2015', '2019', '2023'].filter(x => r.emocion?.[x]).map(x => `<div class="fila"><span>${x}</span><b>${esc(r.emocion[x])}${ev.intensidad?.[x] ? ` · <em>intensidad ${ev.intensidad[x]}/5</em>` : ''}</b></div>`).join('');
        const tabla = ev.concentracion ? `<table class="aq-mini"><thead><tr><th></th><th>Cómo votó</th><th class="num">Alcaldía</th><th class="num">Concejo</th><th class="num">JAL</th></tr></thead><tbody>
            ${['2015', '2019', '2023', '2026'].map(x => `<tr><td>${x}</td><td>${esc(ev.estructura?.[x] || '—')}</td>${(ev.concentracion[x] || []).map(v => `<td class="num">${conc(v)}</td>`).join('')}</tr>`).join('')}
          </tbody></table><p class="aq-v-nota">El porcentaje es lo que sacó el más votado en el barrio: alto, voto concentrado; bajo, voto repartido. En 2026 las columnas son Presidencia (1.ª vuelta), Senado y Cámara.</p>` : '';
        return `${emo ? `<h5>La emoción del barrio en cada elección</h5>${emo}${r.familia_emocional ? `<div class="fila"><span>Familia emocional</span><b>${esc(r.familia_emocional)}</b></div>` : ''}` : ''}
          ${tabla ? `<h5>Cómo ha votado${her ? ' <small>(datos de su barrio-fuente)</small>' : ''}</h5>${tabla}` : ''}
          <h5>Qué tan estable es</h5>
          <div class="fila"><span>Volatilidad de la mezcla</span><b>${esc(String(r.volatilidad?.nivel || '—').toLowerCase())}</b></div>
          ${ev.continuidad ? `<div class="fila"><span>Continuidad electoral 2015-2026</span><b>${esc(ev.continuidad)}</b></div>` : ''}
          ${r.sensibilidad ? `<div class="fila"><span>Sensibilidad del volumen</span><b>${esc(String(r.sensibilidad.nivel || '').toLowerCase())} · ${esc(String(r.sensibilidad.tendencia || '').toLowerCase())}</b></div>${r.sensibilidad.lectura ? `<p class="aq-v-nota">${esc(r.sensibilidad.lectura)}</p>` : ''}` : ''}
          <div class="fila"><span>Volumen electoral</span><b>${['2015', '2019', '2023'].map(x => num(vol[x])).join(' · ')} · ${num(ev.volumen_2026)} (2026) · ${num(vol['2027_base'])} (2027)</b></div>`;
      },
    },
    medellin: {
      sub: b => { const r = b.raw; return `${r.tipo_evolucion ? ` · ${esc(String(r.tipo_evolucion).toLowerCase())}` : ''}${r.proyeccion_2027?.nivel_riesgo ? ` · riesgo de cambio ${esc(String(r.proyeccion_2027.nivel_riesgo).toLowerCase())}` : ''}`; },
      cuerpo: b => {
        const r = b.raw, p = r.proyeccion_2027 || {}, g = r.ganadores || {}, cx = r.contexto || {};
        const gan = (n, x) => n ? `${esc(lugar(String(n).split(' · ')[0]))}${x != null ? ` <em>${pct(x)}</em>` : ''}` : '—';
        const tabla = Object.keys(g).length ? `<table class="aq-mini"><thead><tr><th></th><th>Alcaldía</th><th>Concejo</th></tr></thead><tbody>
            ${['2015', '2019', '2023'].filter(x => g[x]).map(x => `<tr><td>${x}</td><td>${gan(g[x].alcaldia, g[x].pct_alc)}</td><td>${gan(g[x].concejo, g[x].pct_con)}</td></tr>`).join('')}
          </tbody></table><p class="aq-v-nota">Quién ganó en el barrio y con qué porcentaje. En el Concejo el ganador puede ser una lista.</p>` : '';
        const tr = [r.transicion_15_19 && `2015-2019: ${r.transicion_15_19}`, r.transicion_19_23 && `2019-2023: ${r.transicion_19_23}`].filter(Boolean);
        const ctx = ['2015', '2019', '2023'].filter(x => cx[x]).map(x => `<div class="fila"><span>${x}</span><b>${esc(String(cx[x].agenda || '—').replace(/\.$/, ''))}${cx[x].riesgo ? ` · <em>riesgo ${esc(String(cx[x].riesgo).toLowerCase())}</em>` : ''}</b></div>`).join('');
        const ajustado = p.probs && p.arquetipo_proy && Object.entries(p.probs).sort((x, y) => y[1] - x[1])[0][0] !== p.arquetipo_proy;
        return `${tr.length ? `<h5>Cómo se movió</h5>${tr.map(t => `<p class="aq-v-nota" style="margin-top:2px">${esc(t)}.</p>`).join('')}` : ''}
          ${tabla ? `<h5>Quién ganó en el barrio</h5>${tabla}` : ''}
          ${ctx ? `<h5>La agenda de cada elección</h5>${ctx}` : ''}
          <h5>Hacia 2027</h5>
          ${p.comportamiento ? `<p class="aq-v-relato">${esc(p.comportamiento)}</p>` : ''}
          ${p.arquetipo_alt ? `<div class="fila"><span>Arquetipo alterno</span><b>${chip(p.arquetipo_alt)}</b></div>` : ''}
          ${p.riesgo_cambio != null ? `<div class="fila"><span>Riesgo de cambio</span><b>${pct(p.riesgo_cambio)} · ${esc(String(p.nivel_riesgo || '').toLowerCase())}</b></div>` : ''}
          ${ajustado ? '<p class="aq-v-nota">El arquetipo 2027 de este barrio fue ajustado a mano en el estudio: el modelo ponía otro primero.</p>' : ''}
          <div class="fila"><span>Votos del barrio</span><b>${['2015', '2019', '2023'].map(x => num(r.votos?.[x])).join(' · ')} · ${num(r.votos?.['2027'])} (2027)</b></div>`;
      },
    },
  };

  /* ═══ SIMULACIÓN ════════════════════════════════════════════════════════ */
  function activo() { return PALANCAS.some(p => S.pal[p.id] && visible(p)); }
  const MEDIA = {};
  function mediaSens(t) {
    const k = `${X.id}:${t}`;
    if (!(k in MEDIA)) { const v = X.orden.map(id => F(id)?.sens?.[t] ?? 2.5); MEDIA[k] = v.reduce((a, b) => a + b, 0) / v.length; }
    return MEDIA[k];
  }
  function simular(b, base) {
    const mez = b.mez?.[base]; if (!mez) return null;
    if (!activo()) return { ...mez };
    const resp = Math.max(.05, Math.min(3, b.resp * (1 + .12 * S.pal.apertura)));
    const out = {}; let tot = 0;
    for (const [id, p] of Object.entries(mez)) {
      const sens = F(id)?.sens || {};
      let sh = 0;
      for (const pa of PALANCAS) {
        const v = S.pal[pa.id]; if (!v || pa.especial || !visible(pa)) continue;
        sh += (-pa.sign * v) * ((sens[pa.tema] ?? 2.5) - mediaSens(pa.tema));
      }
      const al = S.pal.alcaldia;
      if (al > 0) sh += al * (X.alcaldia.mas[id] || 0) * PESO_ALCALDE;
      if (al < 0) sh += -al * (X.alcaldia.menos[id] || 0) * PESO_ALCALDE;
      const w = Math.max(p, .004) * Math.exp(K * resp * sh);
      out[id] = w; tot += w;
    }
    for (const id in out) out[id] /= tot;
    return out;
  }
  function calcularSim() {
    const base = S.simBase, R = {};
    for (const [code, b] of Object.entries(X.B)) {
      const s = simular(b, base); if (!s) continue;
      /* Con todo en cero manda el dominante del estudio; en escenario, el que
         quede arriba de la mezcla simulada. */
      const d0 = b.dom?.[base] || top(b.mez[base]);
      R[code] = { base: b.mez[base], sim: s, d0, d1: activo() ? top(s) : d0 };
    }
    return R;
  }

  function pintarSim() {
    const l = L(), A = X.ancla;
    $('aqSimIntro').innerHTML = `Cada palanca va de −5 a +5. Cuando un tema se deteriora, ganan peso los arquetipos más sensibles a ese tema según el estudio; cuando mejora, se calman. Lo que se mueve es ${X.id === 'cartagena' ? 'la mezcla de los ocho arquetipos de cada barrio' : 'el perfil de cada barrio en los cinco arquetipos'}, y el mapa pinta el que queda mandando.`;
    $('aqSimNota').innerHTML = `La simulación es nuestra: parte del ${X.mezcla} de cada barrio y de qué tan sensible es cada arquetipo a cada tema, y aplica una regla declarada: el peso de cada arquetipo se multiplica según qué tan sensible es a los temas que se movieron, más en los barrios que históricamente han sido más volátiles. La palanca del alcalde arranca en la cifra medida: <b>${A.valor} %</b> califica buena o muy buena la gestión de ${esc(A.alcalde)} y <b>${A.imagen} %</b> tiene imagen favorable de él (<a href="${A.url}" target="_blank" rel="noopener">${esc(A.fuente)}</a>, ${esc(A.detalle)}); se usa la gestión porque es lo que un barrio premia o castiga. ${esc(A.nota)} A qué arquetipos mueve esa palanca es regla nuestra. Sirve para comparar escenarios, no para pronosticar.`;
    if ($('aqSimPalancas').dataset.ciudad !== X.id) {
      $('aqSimPalancas').innerHTML = `<div class="aq-esc"><span class="rot">Escenarios</span>${ESCENARIOS.map(([t], i) => `<button type="button" class="aq-tog" data-esc="${i}">${esc(t)}</button>`).join('')}<button type="button" class="aq-tog" data-esc="reset">↻ Todo en cero</button></div>`
        + PALANCAS.filter(visible).map(p => `<label class="aq-pal${p.ancla ? ' aq-pal-ancla' : ''}"><span class="aq-pal-n">${esc(p.id === 'movilidad' ? X.movilidad : p.label)}<b id="aqPalV-${p.id}">0</b></span><input type="range" min="-5" max="5" step="1" value="${S.pal[p.id]}" data-pal="${p.id}"><small>${p.ancla
          ? `Hoy: <b>${A.valor} %</b> califica buena la gestión de ${esc(A.alcalde)} (imagen favorable: ${A.imagen} %). Cada paso, ${A.paso} puntos: de ${valorAlcaldia(-5)} % a ${valorAlcaldia(5)} %. <a href="${A.url}" target="_blank" rel="noopener">${esc(A.fuente)}</a>.`
          : esc(p.hint)}</small></label>`).join('');
      $('aqSimPalancas').dataset.ciudad = X.id;
      valoresPal();
      let t = null;
      $('aqSimPalancas').querySelectorAll('[data-pal]').forEach(inp => inp.addEventListener('input', () => {
        S.pal[inp.dataset.pal] = Number(inp.value); valoresPal();
        clearTimeout(t); t = setTimeout(repintarSim, 60);
      }));
      $('aqSimPalancas').querySelectorAll('[data-esc]').forEach(btn => btn.addEventListener('click', () => {
        PALANCAS.forEach(p => { S.pal[p.id] = 0; });
        if (btn.dataset.esc !== 'reset') Object.assign(S.pal, ESCENARIOS[+btn.dataset.esc][1]);
        $('aqSimPalancas').querySelectorAll('[data-pal]').forEach(inp => { inp.value = S.pal[inp.dataset.pal]; });
        valoresPal(); repintarSim();
      }));
    }
    $('aqSimControles').innerHTML = `<span class="rot">Parte de</span>${[['2027', `2027 · ${X.nat['2027']}`], ['2023', `2023 · ${X.nat['2023']}`]].map(([k, t]) => `<button type="button" class="aq-tog" data-base="${k}" aria-pressed="${S.simBase === k}">${t}</button>`).join('')}`
      + `<span class="rot" style="margin-left:12px">Qué pinta</span>${[['dom', 'El que manda en el escenario'], ['cambio', 'Solo los barrios que cambian']].map(([k, t]) => `<button type="button" class="aq-tog" data-sver="${k}" aria-pressed="${S.simVer === k}">${t}</button>`).join('')}`;
    $('aqSimControles').querySelectorAll('[data-base]').forEach(b => b.addEventListener('click', () => { S.simBase = b.dataset.base; pintarSim(); }));
    $('aqSimControles').querySelectorAll('[data-sver]').forEach(b => b.addEventListener('click', () => { S.simVer = b.dataset.sver; pintarSim(); }));
    if (!l.geo) { $('aqSimMapa').classList.add('hidden'); return; }
    if (!M.sim) M.sim = crearMapa('aqSimMapa'); else setTimeout(() => M.sim.invalidateSize(), 0);
    repintarSim();
  }
  function valoresPal() { PALANCAS.forEach(p => { const v = S.pal[p.id], e = $(`aqPalV-${p.id}`); if (e) { e.textContent = p.ancla ? `${valorAlcaldia(v)} %${v ? ` (${v > 0 ? '+' : '−'}${Math.abs(v * X.ancla.paso)})` : ''}` : v > 0 ? `+${v}` : String(v); e.classList.toggle('on', !!v); } }); }

  let RS = {};
  function repintarSim() {
    const l = L(), nuevo = !M.simCapa;
    RS = calcularSim();
    if (M.simCapa) M.sim.removeLayer(M.simCapa);
    M.simCapa = global.L.geoJSON(l.geo, {
      style: f => {
        const code = l.codeDe(f.properties), r = RS[code], sel = code === S.simSel;
        if (!r) return { color: '#fff', weight: .6, fillColor: '#c9ccc4', fillOpacity: .18 };
        const cambia = r.d0 !== r.d1;
        if (S.simVer === 'cambio') return { color: sel || cambia ? '#111' : '#fff', weight: sel ? 2.4 : cambia ? 1.3 : .5, fillColor: cambia ? color(r.d1) : '#c9ccc4', fillOpacity: cambia ? .85 : .2 };
        return { color: sel || cambia ? '#111' : '#fff', weight: sel ? 2.4 : cambia ? 1.4 : .6, dashArray: cambia && !sel ? '3 2' : null, fillColor: color(r.d1), fillOpacity: .35 + .6 * Math.min(1, Math.max(0, ((r.sim[r.d1] || .5) - .2) / .5)) };
      },
      onEachFeature: (f, layer) => {
        const code = l.codeDe(f.properties);
        layer.bindTooltip(() => { const r2 = RS[code]; return `<b>${esc(lugar(l.nombreGeo(f.properties)))}</b> · ${r2 ? (r2.d0 !== r2.d1 ? `${esc(nombre(r2.d0))} → ${esc(nombre(r2.d1))}` : esc(nombre(r2.d1))) : 'sin medición'}`; }, { className: 'aq-tt', sticky: true });
        if (X.B[code]) layer.on('click', () => { S.simSel = code; fichaSim(); M.simCapa.setStyle(M.simCapa.options.style); });
      },
    }).addTo(M.sim);
    if (nuevo) encuadrar(M.sim, M.simCapa);
    pintarResumenSim();
    if (S.simSel && RS[S.simSel]) fichaSim(); else $('aqSimFicha').innerHTML = '<p class="vacio">Toque un barrio para comparar su perfil antes y después del escenario.</p>';
  }

  function pintarResumenSim() {
    if (!Object.keys(RS).length) return;
    const base = S.simBase;
    const peso = code => Number(X.B[code]?.peso?.[base] || 0);
    const agrega = (pesoDe, cual) => { const o = {}; let t = 0; for (const [code, r] of Object.entries(RS)) { const w = pesoDe(code); if (!w) continue; t += w; for (const [id, p] of Object.entries(r[cual])) o[id] = (o[id] || 0) + w * p; } for (const id in o) o[id] /= t || 1; return o; };
    const c0 = agrega(peso, 'base'), c1 = agrega(peso, 'sim');
    const cambian = Object.entries(RS).filter(([, r]) => r.d0 !== r.d1).sort((a, b) => peso(b[0]) - peso(a[0]));
    const votosCiudad = cambian.reduce((s, [c]) => s + peso(c), 0), totCiudad = Object.keys(RS).reduce((s, c) => s + peso(c), 0);
    const flujos = {};
    cambian.forEach(([, r]) => { const k = `${r.d0}>${r.d1}`; flujos[k] = (flujos[k] || 0) + 1; });
    /* La lente activa: si lee sus votos o los de su lado, cómo quedan. */
    const votos = C.votos?.() || null, V = C.voz?.();
    let lente = '';
    if (votos && Object.keys(votos).length && V) {
      const v0 = agrega(c => votos[c] || 0, 'base'), v1 = agrega(c => votos[c] || 0, 'sim');
      if (Object.keys(v0).length) lente = `<div class="aq-sim-bloque"><h5>${esc(V.Voto)} en este escenario</h5>${tablaDelta(v0, v1)}</div>`;
    }
    $('aqSimResumen').innerHTML = !activo()
      ? `<p class="aq-v-nota">Todas las palancas en cero: el mapa es el ${base} del estudio (${X.nat[base]}) tal cual. Mueva una palanca o escoja un escenario.</p>`
      : `<div class="aq-sim-cifras"><div><b>${cambian.length}</b><span>de ${Object.keys(RS).length} barrios cambian de arquetipo dominante</span></div><div><b>${pct(votosCiudad / (totCiudad || 1))}</b><span>del voto de la ciudad vive en esos barrios</span></div></div>
        <div class="aq-sim-grid"><div class="aq-sim-bloque"><h5>${esc(X.nombre)}: antes y después</h5>${tablaDelta(c0, c1)}</div>${lente}
        <div class="aq-sim-bloque"><h5>Los movimientos</h5>${Object.entries(flujos).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([k, n]) => { const [x, y] = k.split('>'); return `<div class="fila"><span>${chip(x)} → ${chip(y)}</span><b>${n}</b></div>`; }).join('') || '<p class="aq-v-nota">Ningún barrio cambia de dominante: el escenario mueve los perfiles, pero no alcanza a voltear a nadie.</p>'}
        ${cambian.length ? `<p class="aq-v-nota">Los más grandes que cambian: ${cambian.slice(0, 8).map(([c]) => esc(lugar(X.B[c].nombre))).join(', ')}.</p>` : ''}</div></div>`;
  }
  function tablaDelta(a, b) {
    return `<ul class="aq-lista aq-delta">${X.orden.map(id => [id, a[id] || 0, b[id] || 0]).sort((x, y) => y[2] - x[2]).map(([id, p0, p1]) => `<li><span class="pt" style="background:${color(id)}"></span><b>${pct(p1)}</b><span>${esc(nombre(id))}</span><em class="${p1 - p0 > .003 ? 'sube' : p1 - p0 < -.003 ? 'baja' : ''}">${pp(p1 - p0)}</em></li>`).join('')}</ul>`;
  }
  function fichaSim() {
    const code = S.simSel, r = RS[code], b = X.B[code]; if (!r || !b) return;
    const movs = X.orden.map(id => [id, (r.sim[id] || 0) - (r.base[id] || 0)]).sort((x, y) => Math.abs(y[1]) - Math.abs(x[1])).slice(0, 4);
    $('aqSimFicha').innerHTML = `<h5>${esc(lugar(b.nombre))}</h5><div style="color:var(--muted);font-size:12px;margin-bottom:6px">${esc(lugar(b.unidad))}${b.volNivel ? ` · ${X.id === 'cartagena' ? 'volatilidad' : 'riesgo de cambio'} ${esc(String(b.volNivel).toLowerCase())}` : ''}</div>
      <div class="fila"><span>Manda hoy (${S.simBase})</span><b>${chip(r.d0)}</b></div>
      <div class="fila"><span>En el escenario</span><b>${chip(r.d1)}${r.d0 !== r.d1 ? '<span class="aq-marca">cambia</span>' : ''}</b></div>
      <div style="margin-top:8px;font-size:11.5px;color:var(--muted)">Antes</div><div class="mez">${orden(r.base).map(([id, p]) => `<i style="flex:${p};background:${color(id)}"></i>`).join('')}</div>
      <div style="font-size:11.5px;color:var(--muted)">Después</div><div class="mez">${orden(r.sim).map(([id, p]) => `<i style="flex:${p};background:${color(id)}"></i>`).join('')}</div>
      ${movs.map(([id, d]) => `<div class="fila"><span>${esc(nombre(id))}</span><b class="${d > 0 ? 'sube' : 'baja'}">${pct(r.base[id])} → ${pct(r.sim[id])}</b></div>`).join('')}
      ${C.votos?.()?.[code] ? `<div class="fila"><span>${esc(C.voz().unidad)} acá</span><b>${num(C.votos()[code])}</b></div>` : ''}`;
  }

  /* ── Arranque ───────────────────────────────────────────────────────── */
  function montar(ctx) {
    C = ctx;
    const l = L();
    X = l && ADAPT[l.ciudad] ? ADAPT[l.ciudad](l) : null;
    if (X) X.ficha = FICHA[X.id];
    pintarModos();
    if (!X) return;
    const h = location.hash;
    if (h === '#arquetipos') usarModo('ver'); else if (h === '#simulacion') usarModo('sim');
  }
  global.C360ArqModos = { montar, usarModo, lenteCambio, PALANCAS, ciudad: () => X, estado: () => S, resultado: () => RS };
})(window);
