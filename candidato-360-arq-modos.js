/* ═══ Candidato 360 · panel 05 · los modos «Ver arquetipos» y «Simulación» ═══
   Dos vistas más sobre la cartografía emocional de CARTAGENA (Nury Astrid),
   encima de la lectura de siempre («Leer desde»):

   · VER ARQUETIPOS — el mapa de la ciudad entera y, al tocar un barrio, su
     ficha completa: qué arquetipo manda y con cuánto, su trayectoria
     2015→2027, la emoción que Nury le leyó en cada ciclo, cómo votó (qué tan
     concentrado), qué tan estable es y qué significa ese arquetipo para una
     campaña. TODO sale del JSON de Nury (tools/candidato-360/arquetipos/
     build_cartagena.py); no hay texto de internet ni de un modelo: con 211
     barrios no habría cómo verificar cada frase, y una ficha que inventa un
     rasgo del barrio es peor que una que se queda en el dato.

   · SIMULACIÓN — palancas de −5 a +5, como el simulador de Proyecto DC, que
     mueven la MEZCLA de cada barrio (no solo el dominante: en Cartagena cada
     barrio es una mezcla de los ocho). La regla es nuestra y está declarada:
       peso'(a) ∝ peso(a) · exp( K · respuesta(barrio) · Σ empuje(tema) · (sens(a,tema) − media de los ocho en ese tema) )
     · empuje = −valor si el tema mejora hacia la derecha (deterioro activa al
       arquetipo sensible a ese tema; mejora lo calma), +valor si la palanca
       mide el problema (costo de vida que sube).
     · sens(a,tema) son las palancas temáticas 1-5 que Nury calificó para cada
       arquetipo (completadas donde ella no calificó; ver `sens_nury`).
     · respuesta(barrio) crece con su volatilidad composicional: un barrio que
       ya se ha movido se mueve más. La palanca «Apertura al cambio» la escala.
     · «Favorabilidad de la Alcaldía» es una regla nuestra, no de Nury.
     Sirve para COMPARAR escenarios, no para pronosticar.

   No toca nada de la lectura de siempre: recibe la lectura de Cartagena (`L`)
   y pinta en sus propios contenedores.                                       */
(function (global) {
  'use strict';
  const AÑOS = ['2015', '2019', '2023', '2027'];
  const VENTANA = [[10.275, -75.58], [10.47, -75.415]];
  const NAT = { '2015': 'ancla', '2019': 'proyección retrospectiva', '2023': 'proyección retrospectiva', '2027': 'simulación de Nury' };

  /* Las palancas. `tema` = llave de `sens` en el JSON. `sign:+1` → la derecha
     es mejora; `sign:-1` → la derecha es el problema. */
  const PALANCAS = [
    { id: 'seguridad', tema: 'seguridad', sign: 1, label: 'Seguridad percibida', hint: '−5 deterioro · +5 mejora visible' },
    { id: 'empleo', tema: 'empleo', sign: 1, label: 'Empleo e ingresos', hint: '−5 desempleo · +5 mejora' },
    { id: 'costo', tema: 'empleo', sign: -1, label: 'Costo de vida', hint: '−5 baja · +5 sube' },
    { id: 'servicios', tema: 'servicios', sign: 1, label: 'Agua, luz y servicios', hint: '−5 cortes y fallas · +5 servicio estable' },
    { id: 'movilidad', tema: 'movilidad', sign: 1, label: 'Movilidad (vías, Transcaribe, lanchas)', hint: '−5 trancones y fallas · +5 fluidez' },
    { id: 'vivienda', tema: 'vivienda', sign: 1, label: 'Vivienda, espacio público y turismo', hint: '−5 desorden y deterioro · +5 mejora' },
    { id: 'corrupcion', tema: 'corrupcion', sign: 1, label: 'Transparencia', hint: '−5 escándalo · +5 gestión limpia y verificable' },
    { id: 'ambiente', tema: 'ambiente', sign: 1, label: 'Ambiente y riesgo (inundación, erosión)', hint: '−5 emergencia · +5 mejora' },
    { id: 'salud', tema: 'salud_educacion', sign: 1, label: 'Salud y educación', hint: '−5 deterioro · +5 mejora' },
    { id: 'participacion', tema: 'participacion', sign: 1, label: 'Cumplimiento y presencia institucional', hint: '−5 promesas incumplidas · +5 acuerdos cumplidos' },
    { id: 'cultura', tema: 'cultura', sign: 1, label: 'Reconocimiento del barrio', hint: '−5 invisibilización · +5 reconocimiento' },
    { id: 'alcaldia', especial: true, label: 'Favorabilidad de la Alcaldía', hint: '−5 muy baja · +5 muy alta (regla nuestra)' },
    { id: 'apertura', especial: true, label: 'Apertura al cambio', hint: '−5 los barrios se aferran · +5 todo se mueve' },
  ];
  /* Favorabilidad: arriba refuerza a quien premia la gestión que funciona y el
     vínculo; abajo, a quien castiga o vigila. Pesos nuestros, declarados. */
  const ALCALDIA = {
    mas: { 'pragmatico-servicios': .6, 'guardian-funcional': .5, 'mediador-comunitario': .5, 'productivo-pragmatico': .3 },
    menos: { 'protesta-resolutiva': .9, 'gestor-vigilante': .6, 'defensor-territorial': .3 },
  };
  const ESCENARIOS = [
    ['Crisis de agua y servicios', { servicios: -5, participacion: -3, alcaldia: -3 }],
    ['Ola de inseguridad', { seguridad: -5 }],
    ['Escándalo en la Alcaldía', { corrupcion: -5, alcaldia: -4 }],
    ['Golpe económico', { empleo: -4, costo: 4 }],
    ['Temporada de lluvias', { ambiente: -4, movilidad: -2, servicios: -2 }],
    ['Gestión que se ve', { servicios: 3, movilidad: 3, seguridad: 2, alcaldia: 3 }],
  ];
  const K = 0.085;

  let C = null;   // contexto: { P, lectura(), votos(), voz() }
  const S = { modo: 'lectura', verAno: '2027', verPinta: null, verSel: null, simBase: '2027', simVer: 'dom', simSel: null, pal: {} };
  PALANCAS.forEach(p => { S.pal[p.id] = 0; });
  const M = { ver: null, verCapa: null, sim: null, simCapa: null };

  const esc = s => C.P.esc(s);
  const $ = id => document.getElementById(id);
  const pct = x => `${Math.round((x || 0) * 100)} %`;
  const pp = x => { const r = Math.round(x * 1000) / 10; return `${r > 0 ? '+' : r < 0 ? '−' : '±'}${Math.abs(r).toString().replace('.', ',')} pp`; };
  const num = x => Math.round(Number(x || 0)).toLocaleString('es-CO');
  const lugar = s => C.P.lugar(s);
  const L = () => C.lectura();
  const D = () => L().D;
  const F = id => D().familias[id];
  const color = id => F(id)?.color || '#9aa09a';
  const nombre = id => F(id)?.nombre || 'sin dato';
  const chip = (id, extra = '') => id ? `<span class="aq-chip"><i style="background:${color(id)}"></i>${esc(nombre(id))}${extra}</span>` : '<span class="aq-chip" style="color:var(--muted)">sin dato</span>';
  const orden = mez => Object.entries(mez || {}).sort((a, b) => b[1] - a[1]);
  const top = mez => orden(mez)[0]?.[0];

  /* ── El cambio de modo ──────────────────────────────────────────────── */
  function pintarModos() {
    const caja = $('aqModos');
    if (!L() || L().ciudad !== 'cartagena') { caja.classList.add('hidden'); return; }
    caja.classList.remove('hidden');
    const ops = [['lectura', 'Su lectura', 'leer desde sus votos, su lado o la ciudad'], ['ver', 'Ver arquetipos', 'el mapa y la ficha de cada barrio'], ['sim', 'Simulación', 'mueva palancas y vea qué cambia']];
    caja.innerHTML = `<span class="rot">Ver</span>` + ops.map(([k, t, sub]) => `<button type="button" class="aq-lente" data-modo="${k}" aria-pressed="${S.modo === k}">${esc(t)}<small>${esc(sub)}</small></button>`).join('');
    caja.querySelectorAll('[data-modo]').forEach(b => b.addEventListener('click', () => usarModo(b.dataset.modo)));
  }
  function usarModo(m) {
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
    m.setView([10.4, -75.5], 12);
    /* Leaflet mide el contenedor al crearse y aquí nace oculto. */
    if (global.ResizeObserver) new ResizeObserver(() => m.invalidateSize()).observe($(id));
    return m;
  }
  function encuadrar(m) { setTimeout(() => { m.invalidateSize(); m.fitBounds(VENTANA, { animate: false }); }, 0); }

  /* ═══ VER ARQUETIPOS ════════════════════════════════════════════════════ */
  function pintarVer() {
    const l = L();
    if (!l.geo) { $('aqVerMapa').classList.add('hidden'); $('aqVerNota').textContent = 'La cartografía de barrios no respondió.'; return; }
    $('aqVerControles').innerHTML = `<span class="rot">Año</span>${AÑOS.map(a => `<button type="button" class="aq-tog" data-ano="${a}" aria-pressed="${S.verAno === a}">${a} · ${NAT[a]}</button>`).join('')}`;
    $('aqVerControles').querySelectorAll('[data-ano]').forEach(b => b.addEventListener('click', () => { S.verAno = b.dataset.ano; pintarVer(); }));
    if (!M.ver) { M.ver = crearMapa('aqVerMapa'); encuadrar(M.ver); } else setTimeout(() => M.ver.invalidateSize(), 0);
    if (M.verCapa) M.ver.removeLayer(M.verCapa);
    const a = S.verAno, pinta = S.verPinta;
    const maxPeso = pinta ? Math.max(.01, ...Object.values(D().barrios).map(b => b.mezcla?.[a]?.[pinta] || 0)) : 1;
    M.verCapa = global.L.geoJSON(l.geo, {
      style: f => {
        const code = l.codeDe(f.properties), b = D().barrios[code], dom = b?.dominante?.[a], sel = code === S.verSel;
        if (!b) return { color: '#fff', weight: .6, fillColor: '#c9ccc4', fillOpacity: .18 };
        if (pinta) { const p = b.mezcla?.[a]?.[pinta] || 0; return { color: sel ? '#111' : '#fff', weight: sel ? 2.4 : .6, fillColor: color(pinta), fillOpacity: .06 + .84 * Math.sqrt(p / maxPeso) }; }
        return { color: sel ? '#111' : '#fff', weight: sel ? 2.4 : .6, fillColor: color(dom), fillOpacity: .35 + .6 * Math.min(1, ((b.pct_dominante?.[a] || .5) - .4) / .3) };
      },
      onEachFeature: (f, layer) => {
        const code = l.codeDe(f.properties), b = D().barrios[code];
        layer.bindTooltip(`<b>${esc(lugar(l.nombreGeo(f.properties)))}</b> · ${b ? esc(nombre(b.dominante?.[a])) : 'sin medición'}`, { className: 'aq-tt', sticky: true });
        layer.on('click', () => { S.verSel = code; fichaVer(code); M.verCapa.setStyle(M.verCapa.options.style); if (matchMedia('(max-width:900px)').matches) $('aqVerFicha').scrollIntoView({ behavior: 'instant', block: 'start' }); });
      },
    }).addTo(M.ver);
    /* Leyenda: tocar un arquetipo pinta cuánto pesa en cada barrio. */
    const cuenta = {};
    Object.values(D().barrios).forEach(b => { const d = b.dominante?.[a]; if (d) cuenta[d] = (cuenta[d] || 0) + 1; });
    $('aqVerLeyenda').innerHTML = `<span class="rot">${pinta ? 'Pinta el peso de' : 'Toque uno para ver dónde pesa'}</span>` + D().orden.map(id => `<button type="button" class="aq-ley" data-arq="${id}" aria-pressed="${pinta === id}"><i style="background:${color(id)}"></i>${esc(nombre(id))} <em>${cuenta[id] || 0}</em></button>`).join('') + (pinta ? '<button type="button" class="aq-ley" data-arq="">← volver al que manda</button>' : '');
    $('aqVerLeyenda').querySelectorAll('[data-arq]').forEach(b => b.addEventListener('click', () => { S.verPinta = b.dataset.arq && b.dataset.arq !== S.verPinta ? b.dataset.arq : null; pintarVer(); }));
    $('aqVerNota').innerHTML = pinta
      ? `Intensidad: cuánto pesa <b>${esc(nombre(pinta))}</b> en la mezcla de cada barrio (${a}). El número junto a cada arquetipo es en cuántos barrios manda.`
      : `Color: el arquetipo que manda en cada barrio (${a}, ${NAT[a]}); más intenso, más concentrado. El número junto a cada arquetipo es en cuántos barrios manda. El mapa abre sobre el casco urbano; las islas siguen ahí si aleja.`;
    if (S.verSel) fichaVer(S.verSel); else $('aqVerFicha').innerHTML = fichaCiudad();
  }

  /* Sin barrio elegido: la ciudad y cómo usar el mapa. */
  function fichaCiudad() {
    const a = S.verAno, sh = D().ciudad_share?.[a] || {};
    return `<h4>Cartagena · ${a}</h4><p class="aq-v-sub">Toque un barrio en el mapa para ver su ficha completa.</p>
      ${barra(sh)}<ul class="aq-lista">${orden(sh).map(([id, p]) => `<li><span class="pt" style="background:${color(id)}"></span><b>${pct(p)}</b><span>${esc(nombre(id))}</span><em>${D().dominantes?.[a]?.[id] || 0} barrios</em></li>`).join('')}</ul>
      <p class="aq-v-nota">El porcentaje es el peso de cada arquetipo en el voto de la ciudad (ponderado por el volumen de cada barrio). ${a === '2015' ? '2015 es el ancla del estudio.' : a === '2027' ? '2027 es la simulación de Nury.' : `${a} es una proyección retrospectiva: describe la mezcla más compatible con cómo votó cada barrio ese año.`}</p>`;
  }
  const barra = mez => `<div class="aq-barra">${orden(mez).map(([id, p]) => `<i style="flex:${p};background:${color(id)}" title="${esc(nombre(id))} ${pct(p)}"></i>`).join('')}</div>`;

  /* La lectura escrita del barrio, armada con sus datos. */
  function relato(b, a) {
    const mez = orden(b.mezcla?.[a]), [d, pd] = mez[0] || [], [s2, p2] = mez[1] || [];
    const f = F(d) || {};
    const cs = D().ciudad_share?.[a]?.[d] || 0;
    const partes = [];
    partes.push(`<b>${esc(lugar(b.nombre))}</b> es un barrio de <b>${esc(nombre(d))}</b>: en ${a} ese arquetipo explica el <b>${pct(pd)}</b> de su mezcla${s2 ? `, y le sigue ${esc(nombre(s2))} con ${pct(p2)}` : ''}.`);
    partes.push(pd >= .6 ? 'Es un barrio de lectura clara: un solo arquetipo ordena a la mayoría.' : pd >= .5 ? 'Manda, pero con competencia: un mensaje solo para ese arquetipo deja afuera casi la mitad del barrio.' : 'Es un barrio mixto: ningún arquetipo pasa de la mitad.');
    if (cs) partes.push(`En la ciudad, ${esc(nombre(d))} pesa ${pct(cs)}: aquí pesa ${(pd / cs).toFixed(1).replace('.', ',')} veces eso.`);
    const doms = AÑOS.map(x => b.dominante?.[x]);
    const cambios = b.volatilidad?.cambios || 0;
    partes.push(cambios ? `Su dominante cambió ${cambios === 1 ? 'una vez' : `${cambios} veces`} entre 2015 y 2027 (${doms.map(x => esc(nombre(x))).join(' → ')}).` : 'Ha tenido el mismo dominante en los cuatro cortes, de 2015 a 2027.');
    if ((f.representativos || '').toUpperCase().normalize('NFD').replace(/[̀-ͯ]/g, '').includes(String(b.nombre).toUpperCase().normalize('NFD').replace(/[̀-ͯ]/g, ''))) partes.push(`Nury lo pone entre los barrios más representativos de ${esc(nombre(d))}.`);
    return partes.join(' ');
  }

  function fichaVer(code) {
    const b = D().barrios[code]; if (!b) return;
    const a = S.verAno, d = b.dominante?.[a], f = F(d) || {}, ev = b.evidencia || {};
    const her = /heredado/i.test(b.tipo || '');
    const votos = C.votos?.()?.[code];
    const loc = Object.values(D().barrios).filter(x => x.localidad === b.localidad);
    const locIgual = loc.filter(x => x.dominante?.[a] === d).length;
    const sh = D().ciudad_share?.[a] || {};
    const mezcla = orden(b.mezcla?.[a]);
    const tray = AÑOS.map(x => `<div class="aq-tray-p"><small>${x}</small>${chip(b.dominante?.[x])}<em>${pct(b.pct_dominante?.[x])}</em></div>`).join('<span class="aq-tray-f">→</span>');
    const emo = ['2015', '2019', '2023'].filter(x => b.emocion?.[x]).map(x => `<div class="fila"><span>${x}</span><b>${esc(b.emocion[x])}${ev.intensidad?.[x] ? ` · <em>intensidad ${ev.intensidad[x]}/5</em>` : ''}</b></div>`).join('');
    const conc = ev.concentracion ? `<table class="aq-mini"><thead><tr><th></th><th>Cómo votó</th><th class="num">Alcaldía</th><th class="num">Concejo</th><th class="num">JAL</th></tr></thead><tbody>
        ${['2015', '2019', '2023'].map(x => `<tr><td>${x}</td><td>${esc(ev.estructura?.[x] || '—')}</td>${(ev.concentracion[x] || []).map(v => `<td class="num">${v == null ? '—' : `${String(v).replace('.', ',')} %`}</td>`).join('')}</tr>`).join('')}
        <tr><td>2026</td><td>${esc(ev.estructura?.['2026'] || '—')}</td>${(ev.concentracion['2026'] || []).map(v => `<td class="num">${v == null ? '—' : `${String(v).replace('.', ',')} %`}</td>`).join('')}</tr>
      </tbody></table><p class="aq-v-nota">El porcentaje es lo que sacó el más votado en el barrio: alto, voto concentrado; bajo, voto repartido. En 2026 las columnas son Presidencia (1.ª vuelta), Senado y Cámara.</p>` : '';
    const vol = b.volumen || {};
    const temas = (f.tematicas || []).slice(0, 3).map(([n, v]) => `${esc(n)} (${v}/5)`).join(', ');
    $('aqVerFicha').innerHTML = `
      <h4>${esc(lugar(b.nombre))}</h4>
      <p class="aq-v-sub">${esc(b.localidad)} · ${her ? `sin puesto propio${b.cercano?.cluster ? ` · lectura heredada de ${esc(lugar(b.cercano.cluster))}${b.cercano.km ? ` (${String(b.cercano.km).replace('.', ',')} km)` : ''}` : ''}` : 'con puesto de votación propio'} · confianza ${esc(String(b.confianza || '').toLowerCase())}</p>
      ${votos ? `<p class="aq-v-votos">${esc(C.voz().unidad)} acá: <b>${num(votos)}</b></p>` : ''}
      <p class="aq-v-relato">${relato(b, a)}</p>
      <h5>La mezcla en ${a}</h5>${barra(b.mezcla?.[a])}
      <ul class="aq-lista">${mezcla.filter(([, p]) => p >= .02).map(([id, p]) => `<li><span class="pt" style="background:${color(id)}"></span><b>${pct(p)}</b><span>${esc(nombre(id))}</span><em>ciudad ${pct(sh[id])}</em></li>`).join('')}</ul>
      <h5>Su trayectoria</h5><div class="aq-tray">${tray}</div>
      ${emo ? `<h5>La emoción que le leyó Nury</h5>${emo}${b.familia_emocional ? `<div class="fila"><span>Familia emocional</span><b>${esc(b.familia_emocional)}</b></div>` : ''}` : ''}
      ${conc ? `<h5>Cómo ha votado${her ? ' <small>(datos de su barrio-fuente)</small>' : ''}</h5>${conc}` : ''}
      <h5>Qué tan estable es</h5>
      <div class="fila"><span>Volatilidad de la mezcla</span><b>${esc(String(b.volatilidad?.nivel || '—').toLowerCase())}</b></div>
      ${ev.continuidad ? `<div class="fila"><span>Continuidad electoral 2015-2026</span><b>${esc(ev.continuidad)}</b></div>` : ''}
      ${b.sensibilidad ? `<div class="fila"><span>Sensibilidad del volumen</span><b>${esc(String(b.sensibilidad.nivel || '').toLowerCase())} · ${esc(String(b.sensibilidad.tendencia || '').toLowerCase())}</b></div>${b.sensibilidad.lectura ? `<p class="aq-v-nota">${esc(b.sensibilidad.lectura)}</p>` : ''}` : ''}
      <div class="fila"><span>Volumen electoral</span><b>${['2015', '2019', '2023'].map(x => num(vol[x])).join(' · ')} · ${num(ev.volumen_2026)} (2026) · ${num(vol['2027_base'])} (2027)</b></div>
      <h5>Qué significa para una campaña</h5>
      <div class="aq-v-arq" style="--c:${color(d)}">
        <b>${esc(nombre(d))}</b> · <em>${esc(f.lema || '')}</em>
        ${f.perfil ? `<p><span>Quién es:</span> ${esc(f.perfil)}${f.edades ? ` (${esc(f.edades)} años)` : ''}</p>` : ''}
        ${f.decide ? `<p><span>Cómo decide:</span> ${esc(f.decide)}</p>` : ''}
        ${f.sube ? `<p><span>Lo enciende:</span> ${esc(f.sube)}</p>` : ''}
        ${f.baja ? `<p><span>Lo calma:</span> ${esc(f.baja)}</p>` : ''}
        ${temas ? `<p><span>Temas que lo mueven:</span> ${temas}.</p>` : ''}
      </div>
      <p class="aq-v-nota">En ${esc(b.localidad)}, ${locIgual} de ${loc.length} barrios tienen el mismo arquetipo dominante en ${a}.</p>
      <button type="button" class="ghost aq-v-cerrar" id="aqVerCerrar">← Ver la ciudad</button>`;
    $('aqVerCerrar').onclick = () => { S.verSel = null; pintarVer(); };
  }

  /* ═══ SIMULACIÓN ════════════════════════════════════════════════════════ */
  function activo() { return PALANCAS.some(p => S.pal[p.id]); }
  function simular(b, base) {
    const mez = b.mezcla?.[base]; if (!mez) return null;
    if (!activo()) return { ...mez };
    const resp = Math.max(.05, Math.min(3, (0.55 + 3 * (b.volatilidad?.media || .15)) * (1 + .12 * S.pal.apertura)));
    const out = {}; let tot = 0;
    for (const [id, p] of Object.entries(mez)) {
      const sens = F(id)?.sens || {};
      let sh = 0;
      for (const pa of PALANCAS) {
        const v = S.pal[pa.id]; if (!v || pa.especial) continue;
        sh += (-pa.sign * v) * ((sens[pa.tema] || 2.5) - mediaSens(pa.tema));
      }
      const al = S.pal.alcaldia;
      if (al > 0) sh += al * (ALCALDIA.mas[id] || 0) * 1.5;
      if (al < 0) sh += -al * (ALCALDIA.menos[id] || 0) * 1.5;
      const w = Math.max(p, .004) * Math.exp(K * resp * sh);
      out[id] = w; tot += w;
    }
    for (const id in out) out[id] /= tot;
    return out;
  }
  /* Se centra en el promedio de los ocho para ESE tema: si Nury calificó los
     servicios alto para casi todos, una crisis de servicios mueve poco, y eso
     es lo que dice su dato, no un defecto del simulador. */
  const MEDIA = {};
  function mediaSens(t) {
    if (!(t in MEDIA)) { const v = D().orden.map(id => F(id)?.sens?.[t] || 2.5); MEDIA[t] = v.reduce((a, b) => a + b, 0) / v.length; }
    return MEDIA[t];
  }
  function calcularSim() {
    const base = S.simBase, R = {};
    for (const [code, b] of Object.entries(D().barrios)) {
      const s = simular(b, base); if (!s) continue;
      R[code] = { base: b.mezcla[base], sim: s, d0: top(b.mezcla[base]), d1: top(s) };
    }
    return R;
  }

  function pintarSim() {
    const l = L();
    if (!$('aqSimPalancas').dataset.listo) {
      $('aqSimPalancas').innerHTML = `<div class="aq-esc"><span class="rot">Escenarios</span>${ESCENARIOS.map(([t], i) => `<button type="button" class="aq-tog" data-esc="${i}">${esc(t)}</button>`).join('')}<button type="button" class="aq-tog" data-esc="reset">↻ Todo en cero</button></div>`
        + PALANCAS.map(p => `<label class="aq-pal"><span class="aq-pal-n">${esc(p.label)}<b id="aqPalV-${p.id}">0</b></span><input type="range" min="-5" max="5" step="1" value="0" data-pal="${p.id}"><small>${esc(p.hint)}</small></label>`).join('');
      $('aqSimPalancas').dataset.listo = '1';
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
    $('aqSimControles').innerHTML = `<span class="rot">Parte de</span>${[['2027', '2027 · simulación de Nury'], ['2023', '2023 · proyección']].map(([k, t]) => `<button type="button" class="aq-tog" data-base="${k}" aria-pressed="${S.simBase === k}">${t}</button>`).join('')}`
      + `<span class="rot" style="margin-left:12px">Qué pinta</span>${[['dom', 'El que manda en el escenario'], ['cambio', 'Solo los barrios que cambian']].map(([k, t]) => `<button type="button" class="aq-tog" data-sver="${k}" aria-pressed="${S.simVer === k}">${t}</button>`).join('')}`;
    $('aqSimControles').querySelectorAll('[data-base]').forEach(b => b.addEventListener('click', () => { S.simBase = b.dataset.base; pintarSim(); }));
    $('aqSimControles').querySelectorAll('[data-sver]').forEach(b => b.addEventListener('click', () => { S.simVer = b.dataset.sver; pintarSim(); }));
    if (!l.geo) { $('aqSimMapa').classList.add('hidden'); return; }
    if (!M.sim) { M.sim = crearMapa('aqSimMapa'); encuadrar(M.sim); } else setTimeout(() => M.sim.invalidateSize(), 0);
    repintarSim();
  }
  function valoresPal() { PALANCAS.forEach(p => { const v = S.pal[p.id], e = $(`aqPalV-${p.id}`); if (e) { e.textContent = v > 0 ? `+${v}` : String(v); e.classList.toggle('on', !!v); } }); }

  let RS = {};
  function repintarSim() {
    const l = L();
    RS = calcularSim();
    if (M.simCapa) M.sim.removeLayer(M.simCapa);
    M.simCapa = global.L.geoJSON(l.geo, {
      style: f => {
        const code = l.codeDe(f.properties), r = RS[code], sel = code === S.simSel;
        if (!r) return { color: '#fff', weight: .6, fillColor: '#c9ccc4', fillOpacity: .18 };
        const cambia = r.d0 !== r.d1;
        if (S.simVer === 'cambio') return { color: sel ? '#111' : cambia ? '#111' : '#fff', weight: sel ? 2.4 : cambia ? 1.3 : .5, fillColor: cambia ? color(r.d1) : '#c9ccc4', fillOpacity: cambia ? .85 : .2 };
        return { color: sel ? '#111' : cambia ? '#111' : '#fff', weight: sel ? 2.4 : cambia ? 1.4 : .6, dashArray: cambia && !sel ? '3 2' : null, fillColor: color(r.d1), fillOpacity: .35 + .6 * Math.min(1, ((r.sim[r.d1] || .5) - .3) / .4) };
      },
      onEachFeature: (f, layer) => {
        const code = l.codeDe(f.properties), r = RS[code];
        layer.bindTooltip(() => { const r2 = RS[code]; return `<b>${esc(lugar(l.nombreGeo(f.properties)))}</b> · ${r2 ? (r2.d0 !== r2.d1 ? `${esc(nombre(r2.d0))} → ${esc(nombre(r2.d1))}` : esc(nombre(r2.d1))) : 'sin medición'}`; }, { className: 'aq-tt', sticky: true });
        if (r) layer.on('click', () => { S.simSel = code; fichaSim(); M.simCapa.setStyle(M.simCapa.options.style); });
      },
    }).addTo(M.sim);
    pintarResumenSim();
    if (S.simSel) fichaSim(); else $('aqSimFicha').innerHTML = '<p class="vacio">Toque un barrio para comparar su mezcla antes y después del escenario.</p>';
  }

  function pintarResumenSim() {
    if (!Object.keys(RS).length) return;
    const base = S.simBase;
    /* La ciudad, pesada por el volumen de cada barrio en el año base. */
    const peso = code => Number(D().barrios[code]?.volumen?.[base === '2027' ? '2027_base' : '2023'] || 0);
    const agrega = (pesoDe, cual) => { const o = {}; let t = 0; for (const [code, r] of Object.entries(RS)) { const w = pesoDe(code); if (!w) continue; t += w; for (const [id, p] of Object.entries(r[cual])) o[id] = (o[id] || 0) + w * p; } for (const id in o) o[id] /= t || 1; return o; };
    const c0 = agrega(peso, 'base'), c1 = agrega(peso, 'sim');
    const cambian = Object.entries(RS).filter(([, r]) => r.d0 !== r.d1).sort((a, b) => peso(b[0]) - peso(a[0]));
    const votosCiudad = cambian.reduce((s, [c]) => s + peso(c), 0), totCiudad = Object.keys(RS).reduce((s, c) => s + peso(c), 0);
    const flujos = {};
    cambian.forEach(([, r]) => { const k = `${r.d0}>${r.d1}`; flujos[k] = (flujos[k] || 0) + 1; });
    /* La lente activa: si lee sus votos o los de su lado, cómo quedan. */
    const votos = C.votos?.() || null, V = C.voz?.();
    let lente = '';
    if (votos && Object.keys(votos).length && V && V.unidad !== 'Votos 2023') {
      const v0 = agrega(c => votos[c] || 0, 'base'), v1 = agrega(c => votos[c] || 0, 'sim');
      lente = `<div class="aq-sim-bloque"><h5>${esc(V.Voto)} en este escenario</h5>${tablaDelta(v0, v1)}</div>`;
    }
    $('aqSimResumen').innerHTML = !activo()
      ? `<p class="aq-v-nota">Todas las palancas en cero: el mapa es la ${base === '2027' ? 'simulación 2027 de Nury' : 'proyección 2023'} tal cual. Mueva una palanca o escoja un escenario.</p>`
      : `<div class="aq-sim-cifras"><div><b>${cambian.length}</b><span>de ${Object.keys(RS).length} barrios cambian de arquetipo dominante</span></div><div><b>${pct(votosCiudad / (totCiudad || 1))}</b><span>del voto de la ciudad vive en esos barrios</span></div></div>
        <div class="aq-sim-grid"><div class="aq-sim-bloque"><h5>Cartagena: antes y después</h5>${tablaDelta(c0, c1)}</div>${lente}
        <div class="aq-sim-bloque"><h5>Los movimientos</h5>${Object.entries(flujos).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([k, n]) => { const [x, y] = k.split('>'); return `<div class="fila"><span>${chip(x)} → ${chip(y)}</span><b>${n}</b></div>`; }).join('') || '<p class="aq-v-nota">Ningún barrio cambia de dominante: el escenario mueve la mezcla, pero no alcanza a voltear a nadie.</p>'}
        ${cambian.length ? `<p class="aq-v-nota">Los más grandes que cambian: ${cambian.slice(0, 8).map(([c]) => esc(lugar(D().barrios[c].nombre))).join(', ')}.</p>` : ''}</div></div>`;
  }
  function tablaDelta(a, b) {
    return `<ul class="aq-lista aq-delta">${D().orden.map(id => [id, a[id] || 0, b[id] || 0]).sort((x, y) => y[2] - x[2]).map(([id, p0, p1]) => `<li><span class="pt" style="background:${color(id)}"></span><b>${pct(p1)}</b><span>${esc(nombre(id))}</span><em class="${p1 - p0 > .003 ? 'sube' : p1 - p0 < -.003 ? 'baja' : ''}">${pp(p1 - p0)}</em></li>`).join('')}</ul>`;
  }
  function fichaSim() {
    const code = S.simSel, r = RS[code], b = D().barrios[code]; if (!r || !b) return;
    const movs = D().orden.map(id => [id, (r.sim[id] || 0) - (r.base[id] || 0)]).sort((x, y) => Math.abs(y[1]) - Math.abs(x[1])).slice(0, 4);
    $('aqSimFicha').innerHTML = `<h5>${esc(lugar(b.nombre))}</h5><div style="color:var(--muted);font-size:12px;margin-bottom:6px">${esc(b.localidad)} · volatilidad ${esc(String(b.volatilidad?.nivel || '').toLowerCase())}</div>
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
    pintarModos();
    if (!L() || L().ciudad !== 'cartagena') return;
    const h = location.hash;
    if (h === '#arquetipos') usarModo('ver'); else if (h === '#simulacion') usarModo('sim');
  }
  global.C360ArqModos = { montar, usarModo, lenteCambio, simular, PALANCAS, estado: () => S, resultado: () => RS };
})(window);
