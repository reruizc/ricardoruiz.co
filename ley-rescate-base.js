/* Seguimiento de la Ley de Rescate · base compartida de las 8 páginas.
   Carga ley-rescate-data/estado.json (lo escribe a diario tools/ley-rescate/rastreo.py),
   pinta la nav Caudal × Cauce, las secciones y el pie, y da los cálculos comunes.
   Al tocar este archivo, subir el ?v= en las 8 páginas. */
(function () {
  const LOCAL = new URLSearchParams(location.search).has('local');
  const URL_DATOS = (LOCAL ? 'Bases de datos/ley-rescate/estado.json' : 'ley-rescate-data/estado.json') + '?v=' + Math.floor(Date.now() / 6e5);
  const SECCIONES = [['hub', 'ley-de-rescate-avance.html', 'Dónde va'], ['reloj', 'ley-de-rescate-reloj.html', 'El reloj'], ['votos', 'ley-de-rescate-votos.html', 'Los votos'], ['fuerzas', 'ley-de-rescate-fuerzas.html', 'Esquema de fuerzas'],
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
  const iniciales = n => n.replace(/^(el|la|los|las|de|del)\s/i, '').split(/\s+/).filter(w => w.length > 2).slice(0, 2).map(w => w[0]).join('').toUpperCase();
  function cara(E, slug, nombre, org) {
    const p = (E.personas || {})[slug];
    if (p && p.foto) return `<img class="cara" src="${esc(p.foto)}" alt="${esc(p.n)}" loading="lazy" />`;
    return `<span class="cara ${org ? 'org' : ''}" aria-hidden="true">${esc(iniciales(nombre || (p && p.n) || '?'))}</span>`;
  }
  const marca = () => `<a class="poweredby" href="index.html" aria-label="Powered by Ricardo Ruiz"><span class="pb-txt">powered by</span><span class="logo-bars" aria-hidden="true"><span class="logo-bar" style="height:15px"></span><span class="logo-bar" style="height:11px"></span><span class="logo-bar" style="height:7px"></span><span class="logo-bar" style="height:3px"></span></span><span class="logo-text">Ricardo<span>.</span>Ruiz</span></a>`;
  function chasis(id) {
    document.body.insertAdjacentHTML('afterbegin', `<nav class="lr-nav" aria-label="Navegación"><div class="lr-izq"><a class="lr-btn" href="legislativo.html">← Legislativo</a><a class="lr-btn" href="ley-de-rescate.html">Cómo le pega</a></div><div class="lr-marca"><a href="caudal-portada.html"><img class="cobrand" src="caudalxcauce.png" alt="Caudal × Cauce · navegar la complejidad" /></a></div><div class="lr-der">${marca()}</div></nav>
      <div class="lr-sec">${SECCIONES.map(([k, h, t]) => `<a href="${h}${LOCAL ? '?local=1' : ''}" class="${k === id ? 'on' : ''}" ${k === id ? 'aria-current="page"' : ''}>${t}</a>`).join('')}</div><div id="tip"></div>`);
    document.body.insertAdjacentHTML('beforeend', `<footer class="lr-pie"><div><img class="cobrand" src="caudalxcauce.png" alt="Caudal × Cauce" /><p>Seguimiento del Proyecto de Ley 477 de 2026 Cámara. Mide lo que se publica, no lo que piensa el país. <a href="ley-de-rescate-bitacora.html#metodo">Cómo se mide</a>.</p>${marca()}</div></footer>`);
    const tip = $('#tip');
    document.addEventListener('mousemove', e => { const t = e.target.closest?.('[data-tip]'); if (!t) { tip.style.opacity = 0; return; } tip.innerHTML = t.dataset.tip; tip.style.opacity = 1; tip.style.left = Math.min(e.clientX + 14, innerWidth - 300) + 'px'; tip.style.top = (e.clientY + 14) + 'px'; });
    if (LOCAL) document.querySelectorAll('a[href^="ley-de-rescate-"]').forEach(a => { if (!a.href.includes('local=1')) a.href = a.getAttribute('href').replace(/(\.html)(#.*)?$/, '$1?local=1$2'); });
  }
  function pagina(id, pintar) {
    chasis(id);
    fetch(URL_DATOS, { cache: 'no-store' }).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }).then(E => {
      $('#carga').hidden = true; $('#app').hidden = false; pintar(E);
      if (LOCAL) document.querySelectorAll('a[href^="ley-de-rescate-"]').forEach(a => { if (!a.href.includes('local=1')) a.href = a.getAttribute('href').replace(/(\.html)(#.*)?$/, '$1?local=1$2'); });
    }).catch(e => { $('#carga').textContent = 'El seguimiento no está disponible en este momento. Intente de nuevo en unos minutos.'; console.error(e); });
  }
  window.LR = { $, esc, num, fecha, iso, mas, corta, larga, dias, FN, P, MIN_POST, CIERRE, ULT, suma, dur, etapas, pasos, cara, pagina, LOCAL };
})();
