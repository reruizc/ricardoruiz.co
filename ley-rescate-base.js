/* Seguimiento de la Ley de Rescate · base compartida de las 9 páginas.
   Carga ley-rescate-data/estado.json (lo escribe a diario tools/ley-rescate/rastreo.py),
   pinta la nav Caudal × Cauce, las secciones y el pie, y da los cálculos comunes.
   Al tocar este archivo, subir el ?v= en las 9 páginas. */
(function () {
  const LOCAL = new URLSearchParams(location.search).has('local');
  const URL_DATOS = (LOCAL ? 'Bases de datos/ley-rescate/estado.json' : 'ley-rescate-data/estado.json') + '?v=' + Math.floor(Date.now() / 6e5);
  const SECCIONES = [['hub', 'ley-de-rescate-avance.html', 'Dónde va'], ['generalidades', 'ley-de-rescate-generalidades.html', 'Generalidades'], ['historico', 'ley-de-rescate-historico.html', 'Entran y salen'], ['analisis', 'ley-de-rescate-analisis.html', 'Quién gana'], ['reloj', 'ley-de-rescate-reloj.html', 'El reloj'], ['votos', 'ley-de-rescate-votos.html', 'Los votos'], ['fuerzas', 'ley-de-rescate-fuerzas.html', 'Esquema de fuerzas'], ['antecedentes', 'ley-de-rescate-antecedentes.html', 'Las fuerzas de antes'],
    ['discusion', 'ley-de-rescate-discusion.html', 'La discusión'], ['articulos', 'ley-de-rescate-articulos.html', 'Los 106 artículos'], ['voces', 'ley-de-rescate-voces.html', 'Las voces'], ['bitacora', 'ley-de-rescate-bitacora.html', 'Bitácora y método']];
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const num = n => Number(n || 0).toLocaleString('es-CO');
  const MES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'], DS = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];
  const fecha = d => new Date(d + 'T12:00:00'), iso = d => d.toISOString().slice(0, 10);
  const mas = (s, n) => { const d = fecha(s); d.setDate(d.getDate() + n); return iso(d); };
  const corta = s => { const d = fecha(s); return `${d.getDate()} ${MES[d.getMonth()]}`; };
  const larga = s => { const d = fecha(s); return `${DS[d.getDay()]} ${d.getDate()} ${MES[d.getMonth()]}`; };
  const dias = (a, b) => Math.round((fecha(b) - fecha(a)) / 864e5);
  const FN = { todo: 'Todo', prensa: 'Prensa', x: 'X', tiktok: 'TikTok', instagram: 'Instagram', facebook: 'Facebook' };
  const P = { a: ['Apoya', 'var(--apoya)'], r: ['Rechaza', 'var(--rechaza)'], m: ['Con reparos', '#a87a1f'], i: ['Sin definir', 'var(--ink3)'] };
  const MIN_POST = 6, CIERRE = '2026-12-16';
  const ULT = { normal: mas(CIERRE, -(8 + 15 + 8 + 1)), urgencia: mas(CIERRE, -(8 + 1)) };

  function suma(t, f) {
    const o = { n: 0, apoya: 0, rechaza: 0, mixta: 0, informa: 0, sin: 0, inter: 0 };
    for (const [k, v] of Object.entries(t.por || {})) if (f === 'todo' || f === k) for (const c in o) o[c] += v[c] || 0;
    o.post = o.apoya + o.rechaza + o.mixta; return o;
  }
  const dur = o => o.post ? o.rechaza / o.post : null;

  function etapas(E) {
    const T = E.tramite || {}, deb = T.debates || [], pon = deb.flatMap(d => d.ponentes || []), pub = deb.flatMap(d => d.publicaciones || []), est = (T.estado || '').toLowerCase();
    const L = [
      ['rad', 'Radicado', true, 'El proyecto entra por la Cámara porque es tributario: los proyectos sobre tributos empiezan allá.', 'Art. 154 C.P.', corta(E.proyecto.radicado)],
      ['pon', 'Ponentes', pon.length > 0, 'La mesa directiva de la comisión escoge a los congresistas que estudian el texto y proponen cambios. Ahí empieza la negociación real.', 'Art. 150 Ley 5ª'],
      ['inf', 'Ponencia', pub.some(p => /ponencia/i.test(p.texto)), 'Los ponentes presentan su informe, con plazo de 5 a 15 días calendario, y se publica en la Gaceta. Es el texto que se vota.', 'Arts. 153 y 156 Ley 5ª'],
      ['anu', 'Anuncio', false, 'Ningún proyecto se puede votar sin haberse anunciado en una sesión anterior. El anuncio es la señal de que la votación viene.', 'Art. 160 C.P.'],
      ['c1', '1.º debate Cámara', /aprobado.*primer|segundo debate/.test(est), 'Vota la Comisión Tercera de la Cámara. Con mensaje de urgencia y sesión conjunta se une la del Senado, y cada una vota por separado.', 'Arts. 157 y 163 C.P.'],
      ['p2', '2.º debate Cámara', false, 'Vota la plenaria de la Cámara. Deben pasar al menos 8 días desde el primer debate.', 'Art. 160 C.P.'],
      ['c3', '1.º debate Senado', false, 'Comisión Tercera del Senado. En trámite normal deben pasar 15 días desde la plenaria de la Cámara.', 'Art. 160 C.P.'],
      ['p4', '2.º debate Senado', false, 'Vota la plenaria del Senado, 8 días después.', 'Art. 160 C.P.'],
      ['con', 'Conciliación', false, 'Si los dos textos difieren, una comisión accidental los une y las plenarias votan el resultado, publicado con un día de anticipación.', 'Art. 161 C.P.'],
      ['san', 'Sanción', false, 'El presidente la firma. Con más de 50 artículos tiene hasta 20 días para objetar.', 'Art. 166 C.P.'],
    ].map(([id, nom, hecho, txt, norma, f]) => ({ id, nom, hecho, txt, norma, f }));
    for (const h of E.hitos || []) if (h.etapa) { const x = L.find(l => l.id === h.etapa); if (x) { x.hecho = true; x.f = corta(h.fecha); } }
    const i = L.findIndex(l => !l.hecho); if (i >= 0) L[i].ahora = true;
    return L;
  }
  function pasos(d1, m) {
    if (m === 'urgencia') { const p = mas(d1, 8); return [[d1, 'Primer debate conjunto: Terceras de Cámara y Senado, cada una vota por separado'], [p, 'Segundo debate: las dos plenarias, pueden ser el mismo día'], [mas(p, 1), 'Conciliación, si los textos difieren']]; }
    const p2 = mas(d1, 8), c3 = mas(p2, 15), p4 = mas(c3, 8);
    return [[d1, 'Primer debate: Tercera de Cámara'], [p2, 'Segundo debate: plenaria de Cámara, 8 días después'], [c3, 'Tercer debate: Tercera de Senado, 15 días después'], [p4, 'Cuarto debate: plenaria de Senado, 8 días después'], [mas(p4, 1), 'Conciliación, si los textos difieren']];
  }
  const iniciales = n => { const w = n.replace(/^(el|la|los|las|de|del)\s/i, '').split(/\s+/).filter(x => x.length > 2); return (w.length > 1 ? w.slice(0, 2).map(x => x[0]).join('') : (w[0] || n).slice(0, 2)).toUpperCase(); };
  function cara(E, slug, nombre, org) {
    const p = (E.personas || {})[slug];
    if (p && p.foto) return `<img class="cara${p.logo ? ' org logo' : ''}" src="${esc(p.foto)}" alt="${esc(p.n)}" loading="lazy" />`;
    return `<span class="cara ${org ? 'org' : ''}" aria-hidden="true">${esc(iniciales(nombre || (p && p.n) || '?'))}</span>`;
  }
  const marca = () => `<a class="poweredby" href="index.html" aria-label="Powered by Ricardo Ruiz"><span class="pb-txt">powered by</span><span class="logo-bars" aria-hidden="true"><span class="logo-bar" style="height:15px"></span><span class="logo-bar" style="height:11px"></span><span class="logo-bar" style="height:7px"></span><span class="logo-bar" style="height:3px"></span></span><span class="logo-text">Ricardo<span>.</span>Ruiz</span></a>`;
  function chasis(id) {
    document.body.insertAdjacentHTML('afterbegin', `<nav class="lr-nav" aria-label="Navegación"><div class="lr-izq"><a class="lr-btn" href="legislativo.html">← Legislativo</a><a class="lr-btn lleno" href="caudal-portada.html">Conozca Caudal</a><a class="lr-btn" href="ley-de-rescate.html">Cómo le afecta</a></div><div class="lr-marca"><a href="caudal-portada.html"><img class="cobrand" src="caudalxcauce.png" alt="Caudal × Cauce · navegar la complejidad" /></a></div><div class="lr-der">${marca()}</div></nav>
      <div class="lr-sec">${SECCIONES.map(([k, h, t]) => `<a href="${h}${LOCAL ? '?local=1' : ''}" class="${k === id ? 'on' : ''}" ${k === id ? 'aria-current="page"' : ''}>${t}</a>`).join('')}</div><div id="tip"></div>`);
    document.body.insertAdjacentHTML('beforeend', `<footer class="lr-pie"><div><img class="cobrand" src="caudalxcauce.png" alt="Caudal × Cauce" /><p>Seguimiento del Proyecto de Ley 477 de 2026 Cámara (328 de 2026 Senado). Mide lo que se publica, no lo que piensa el país. <a href="ley-de-rescate-bitacora.html#metodo">Cómo se mide</a>.</p>${marca()}<p class="lr-invita">Si quiere tener a su organización, gremio o empresa, pública o privada, al día en materia regulatoria y reputacional, con datos públicos y privados, lo invitamos a conocer <a href="caudal-portada.html">Caudal</a>.</p></div></footer>`);
    const tip = $('#tip');
    document.addEventListener('mousemove', e => { const t = e.target.closest?.('[data-tip]'); if (!t) { tip.style.opacity = 0; return; } tip.innerHTML = t.dataset.tip; tip.style.opacity = 1; tip.style.left = Math.min(e.clientX + 14, innerWidth - 300) + 'px'; tip.style.top = (e.clientY + 14) + 'px'; });
    if (LOCAL) document.querySelectorAll('a[href^="ley-de-rescate-"]').forEach(a => { if (!a.href.includes('local=1')) a.href = a.getAttribute('href').replace(/(\.html)(#.*)?$/, '$1?local=1$2'); });
  }
  // Sello de «última actualización»: la hora real en que corrió el rastreo (E.v, UTC), en hora de Colombia,
  // con un «hace N» que se refresca solo. Pasadas 30 h se pinta en ámbar: el rastreo diario se atrasó.
  function sello(E) {
    const t = Date.parse(E.v); if (!t) return;
    const lead = document.querySelector('main .lead'); if (!lead) return;
    const f = new Intl.DateTimeFormat('es-CO', { timeZone: 'America/Bogota', weekday: 'long', day: 'numeric', month: 'long', hour: 'numeric', minute: '2-digit' }).format(new Date(t));
    lead.insertAdjacentHTML('afterend', `<p class="lr-act" id="lr-act"><i aria-hidden="true"></i><span>Última actualización: <b>${esc(f.replace(/\s*a\.\s*m\./, ' a. m.').replace(/\s*p\.\s*m\./, ' p. m.'))}</b> <span class="lr-act-z">(hora de Colombia)</span> · <span id="lr-hace"></span></span></p>`);
    const hace = () => {
      const m = Math.max(0, Math.round((Date.now() - t) / 60000)), h = Math.floor(m / 60);
      $('#lr-hace').textContent = m < 1 ? 'hace un momento' : m < 60 ? `hace ${m} min` : h < 48 ? `hace ${h} h` : `hace ${Math.floor(h / 24)} días`;
      $('#lr-act').classList.toggle('vieja', h >= 30);
    };
    hace(); setInterval(hace, 60000);
  }
  // El barco de Caudal × Cauce mientras carga (mismo dibujo que caudal-comun.js). El CSS vive en ley-rescate-base.css.
  function mar(msgs, mini) {
    const m = (msgs && msgs.length ? msgs : ['Cargando…']).slice(0, 3); while (m.length < 3) m.push(m[m.length - 1]);
    const cresta = y => { let d = `M-80 ${y}`; for (let x = -80; x < 400; x += 80) d += ' q20 -7 40 0 t40 0'; return d; }, ola = y => cresta(y) + ' V70 H-80 Z';
    return `<div class="cau-mar${mini ? ' mini' : ''}" role="status" aria-live="polite"><svg viewBox="0 0 320 70" aria-hidden="true"><path class="cm-ola o2" d="${ola(44)}"/><g class="cm-barco"><g class="cm-bob"><path class="cm-vela" d="M14 34 V14 L26 32 Z"/><path class="cm-vela" d="M12 34 V20 L5 33 Z" opacity=".6"/><path class="cm-casco" d="M2 35 H30 L25 41 H7 Z"/></g></g><path class="cm-ola" d="${ola(40)}"/><path class="cm-cresta" d="${cresta(40)}"/></svg><div class="cm-msgs">${m.map(t => `<span>${esc(t)}</span>`).join('')}</div></div>`;
  }
  function pagina(id, pintar) {
    chasis(id);
    const c = $('#carga'); if (c) c.innerHTML = mar(['Leyendo la ficha de la Cámara…', 'Sumando prensa y redes…', 'Casi listo…']);
    fetch(URL_DATOS, { cache: 'no-store' }).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }).then(E => {
      // La corrida diaria llega a veces en la tarde: los contadores de días usan la fecha real de Bogotá; E.dato guarda la del dato.
      E.dato = E.hoy; const hb = new Date(Date.now() - 5 * 36e5).toISOString().slice(0, 10); if (hb > E.hoy) E.hoy = hb;
      $('#carga').hidden = true; $('#app').hidden = false; sello(E); pintar(E);
      if (LOCAL) document.querySelectorAll('a[href^="ley-de-rescate-"]').forEach(a => { if (!a.href.includes('local=1')) a.href = a.getAttribute('href').replace(/(\.html)(#.*)?$/, '$1?local=1$2'); });
    }).catch(e => { $('#carga').textContent = 'El seguimiento no está disponible en este momento. Intente de nuevo en unos minutos.'; console.error(e); });
  }
  window.LR = { $, esc, num, fecha, iso, mas, corta, larga, dias, FN, P, MIN_POST, CIERRE, ULT, suma, dur, etapas, pasos, cara, pagina, mar, LOCAL };
})();
