/* ═══════════════════════════════════════════════════════════════════════════
   CANDIDATO 360 · lógica de la página (consolidada el 5-sep-2026)
   ───────────────────────────────────────────────────────────────────────────
   Antes eran 12 bloques <script> apilados que se envolvían unos a otros
   (launchCRM 4 veces, loadHistoricalMap 5). Ahora es UN archivo con un orden
   que se puede leer de arriba abajo:

     1. Configuración y helpers
     2. Pantallas y modales
     3. Sesión, acceso y VÍNCULO (el gate de pago y el "un solo candidato")
     4. Índice electoral (cand-index.js) y su pantalla de espera
     5. Búsqueda de candidato con historial
     6. Ruta del candidato con historial: corporación y territorio 2027
     7. Ruta de candidatura nueva: wizard
     8. CRM: apertura, meta de votos y foto
     9. Mapas: recorte territorial, ciudad, barrios, vistas por año, niveles
     9 bis. Arquetipos del territorio y perfil del votante
    10. Arranque

   Reglas del producto que viven acá (decisión de Ricardo, sep-2026):
   · El dato es la vitrina, y una vitrina no se tapa: sin acceso se busca el
     nombre, se ve el historial y se entra a la candidatura. El muro cae en el
     CRM (mapa, meta y briefing), que es lo que se cobra. El único que sigue
     borroso es el wizard de candidatura nueva: es un formulario, no un dato.
     Acceso = plan c360, cortesía o admin.
   · Una cuenta se vincula a UN candidato y no se cambia desde la plataforma:
     el vínculo vive en el worker (POST /c360/vinculo devuelve 409 si ya hay
     uno) y solo soporte lo borra. La campaña (corporación + territorio) sí
     se puede editar.
   ═══════════════════════════════════════════════════════════════════════════ */

/* ─── 1. Configuración y helpers ─────────────────────────────────────────── */
const S3 = RRData.publicUrl('congreso-2026/output');
const AUTH_API = (window.RR_RUNTIME_CONFIG && window.RR_RUNTIME_CONFIG.authBase) || 'https://rr-auth.reruizc.workers.dev';
const PAGINA = 'candidato-360.html';
const MUNICIPAL_ELECTIONS = ['concejo', 'alcaldia', 'jal'];
const CORP_MUNICIPAL = ['jal', 'concejo', 'alcaldia'], CORP_DEPARTAMENTAL = ['asamblea', 'gobernacion'];
const CRM_CORPORATIONS = { concejo: 'Concejo municipal o distrital', alcaldia: 'Alcaldía municipal o distrital', jal: 'Junta administradora local', asamblea: 'Asamblea departamental', gobernacion: 'Gobernación' };
/* El nombre del archivo Departamentos-mps/{cod}.json es el código ELECTORAL,
   no el DANE: 01.json es Antioquia (DANE 05) y 05.json es Bolívar (DANE 13).
   Un diccionario DANE aquí no da 404: carga el departamento equivocado con
   HTTP 200. Esta tabla es la única fuente de códigos de la página. */
const DEP_BOGOTA = 'Distrito Capital de Bogotá';
const DEP_CODES = { 'Amazonas': '60', 'Antioquia': '01', 'Arauca': '40', 'Atlántico': '03', 'Bolívar': '05', 'Boyacá': '07', 'Caldas': '09', 'Caquetá': '44', 'Casanare': '46', 'Cauca': '11', 'Cesar': '12', 'Chocó': '17', 'Córdoba': '13', 'Cundinamarca': '15', 'Distrito Capital de Bogotá': '16', 'Guainía': '50', 'Guaviare': '54', 'Huila': '19', 'La Guajira': '48', 'Magdalena': '21', 'Meta': '52', 'Nariño': '23', 'Norte de Santander': '25', 'Putumayo': '64', 'Quindío': '26', 'Risaralda': '24', 'San Andrés y Providencia': '56', 'Santander': '27', 'Sucre': '28', 'Tolima': '29', 'Valle del Cauca': '31', 'Vaupés': '68', 'Vichada': '72' };

const escHtml = s => String(s || '').replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
function normalizedText(value) { return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replace(/[^A-Z0-9]/g, ''); }
function initials(name) { return String(name || 'CR').split(/\s+/).slice(0, 2).map(x => x[0] || '').join('').toUpperCase() || 'CR'; }
function optionList(items, label) { return `<option value="">${label}</option>` + items.map(x => `<option value="${escHtml(x.value || x)}">${escHtml(x.label || x)}</option>`).join(''); }
const $ = id => document.getElementById(id);

/* El año sale del corp ("ALCALDÍA · BOGOTÁ D.C. · 2019"). Medido sobre los
   índices: la ÚNICA fuente que no lo trae es endoso (2.822 candidaturas de
   2026, corp "SENADO" / "CÁMARA" / "CONSULTAS"). Sin esto quedaban en año 0 y
   se ordenaban al FINAL del historial. */
const SRC_YEAR = { endoso: 2026 };
function candidateYear(candidate) { return Number(String(candidate?.corp || '').match(/20\d{2}/)?.[0] || SRC_YEAR[candidate?.source] || 0); }

/* Los archivos del territorio se piden una sola vez por sesión. */
const geoCache = new Map();
function fetchJSON(url) {
  if (!geoCache.has(url)) geoCache.set(url, fetch(url).then(r => r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status))).catch(e => { geoCache.delete(url); throw e; }));
  return geoCache.get(url);
}
let comunasDataPromise = null;
function comunasCSV() {
  if (!comunasDataPromise) comunasDataPromise = fetch(`${S3}/Divipole-actualizado/COMUNAS_DATA.csv`).then(r => r.ok ? r.text() : Promise.reject()).then(raw => raw.split(/\r?\n/).slice(1).map(row => row.replace(/^\uFEFF/, '').split(';'))).catch(e => { comunasDataPromise = null; throw e; });
  return comunasDataPromise;
}
/* La Divipola escribe "Bogota. D.C.": se compara sin tildes ni puntuación. */
const canonical = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replace(/[^A-Z0-9]/g, '');
/* La columna 10 de COMUNAS_DATA trae el código pegado al nombre
   ("13LOCALIDAD 13 TEUSAQUILLO" · "14COMUNA 14 EL POBLADO" · "30VALENCIA DE
   JESUS"). Se quita el código y, en Bogotá, el "LOCALIDAD 13": así el valor
   casa con la circunscripción del índice 2023 ("TEUSAQUILLO · BOGOTÁ D.C." ·
   "COMUNA 14 EL POBLADO · MEDELLIN"), que es lo que VoteTarget busca. */
function nombreLocalidad(raw) { return String(raw || '').replace(/^\d{2}(?=\S)/, '').replace(/\s+/g, ' ').trim().replace(/^LOCALIDAD\s*\d+\s+/i, ''); }
/* Para casar con el nombre del polígono: "COMUNA 14 EL POBLADO" → "EL POBLADO". */
function cortoLocal(raw) { return nombreLocalidad(raw).replace(/^(COMUNA|COM|CORREGIMIENTO|CORREG\.?|CORRE\.?)\s*\d*\s*/i, '').trim(); }
/* ¿Es el mismo municipio escrito por el DANE y por la Registraduría?
   «SANTIAGODECALI»/«CALI» y «CARTAGENADEINDIAS»/«CARTAGENA» sí;
   «CALIMA»/«CALI» no, aunque empiece igual. «CALIMADARIEN»/«CALIMA» sí: la
   Registraduría a veces agrega el nombre viejo entre paréntesis. */
function mismoMunicipio(a, b) {
  if (a === b) return true;
  const [largo, corto] = a.length >= b.length ? [a, b] : [b, a];
  return largo.endsWith(corto) || largo.startsWith(corto + 'DE') || largo === corto + 'DC' || (largo.startsWith(corto) && a.length < b.length);
}
async function localidadesDe(depNombre, munNombre) {
  const rows = await comunasCSV();
  const dep = canonical(depNombre), pedido = canonical(munNombre);
  /* El formulario escribe el municipio como el mapa del DANE («SANTIAGO DE
     CALI», «CARTAGENA DE INDIAS», «SAN JOSÉ DE CÚCUTA») y COMUNAS_DATA como la
     Registraduría («CALI»…): sin este puente la JAL de esas ciudades salía sin
     una sola comuna. Solo si no hay nombre exacto, y por inicio o final —con
     «contiene», CALIMA pasaría por CALI—; gana el nombre más largo. */
  /* Y el departamento viene recortado («VALLE», «NORTE DE SAN»): exacto si
     existe, si no por inicio. */
  const deps = new Set(rows.map(r => canonical(r[5])));
  const depCsv = deps.has(dep) ? dep : [...deps].filter(d => d.length > 3 && dep.startsWith(d)).sort((a, b) => b.length - a.length)[0] || dep;
  const delDepto = rows.filter(r => canonical(r[5]) === depCsv);
  let mun = pedido;
  if (!delDepto.some(r => canonical(r[6]) === pedido)) {
    mun = [...new Set(delDepto.map(r => canonical(r[6])))].filter(m => m.length > 3 && mismoMunicipio(pedido, m)).sort((a, b) => b.length - a.length)[0] || pedido;
  }
  return [...new Set(delDepto.filter(r => canonical(r[6]) === mun).map(r => nombreLocalidad(r[10])).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'es'));
}

/* ─── 2. Pantallas y modales ─────────────────────────────────────────────── */
const screens = [...document.querySelectorAll('.screen')];
const topBack = document.createElement('button');
topBack.type = 'button'; topBack.className = 'nav-back'; topBack.textContent = '← Volver';
document.querySelector('.topbar .nav-left').prepend(topBack);
topBack.addEventListener('click', () => document.querySelector('.screen:not(.hidden) .flow-top .back')?.click());
function refreshTopBack() { const current = document.querySelector('.screen:not(.hidden)'); topBack.classList.toggle('visible', Boolean(current && current.id !== 'intro')); }
function showScreen(id) {
  screens.forEach(s => s.classList.toggle('hidden', s.id !== id));
  /* El shell recorta con overflow:clip, así que ni focus() ni scrollIntoView
     pueden desplazarlo de lado; el scroll vertical sí se lleva arriba. */
  window.scrollTo({ top: 0, behavior: 'instant' });
  refreshTopBack();
  if (id === 'existing') setTimeout(() => $('candidateSearch')?.focus({ preventScroll: true }), 80);
  if (id === 'new') aplicarGateNuevo();
  if (id !== 'intro') clearTimeout(partidaTimer);
}
/* Presentación secuencial; los pasos siguientes conservan su estado. */
function avanzarIntro() {
  if ($('introNext').disabled) return;
  $('introPresentation').classList.add('hidden');
  $('choicePanel').classList.remove('hidden');
  $('intro').classList.add('intro-choosing');
  cambiarPais(false);
  const heading = document.querySelector('#paisPaso h2');
  if (heading) { heading.tabIndex = -1; heading.focus({ preventScroll: true }); }
  window.scrollTo({ top: 0, behavior: 'instant' });
}
function volverIntro() {
  $('choicePanel').classList.add('hidden');
  $('introPresentation').classList.remove('hidden');
  $('intro').classList.remove('intro-choosing');
  clearTimeout(partidaTimer);
  etapaIntro('welcome');
  $('introNext').focus({ preventScroll: true });
}
(function prepararIntro() {
  const card = $('introPresentation');
  const links = card.querySelector('.intro-links');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  links.inert = true;
  function ready() {
    links.inert = false;
    card.classList.add('intro-ready');
    card.classList.remove('intro-playing');
    $('introNext').disabled = false;
  }
  function start() {
    card.classList.add('intro-playing');
    if (reduced.matches) ready();
    else {
      setTimeout(() => { links.inert = false; card.classList.add('intro-details'); }, 1100);
      setTimeout(ready, 1900);
    }
  }
  const preload = $('preload');
  if (preload?.classList.contains('active')) {
    const observer = new MutationObserver(() => {
      if (!preload.classList.contains('active')) { observer.disconnect(); start(); }
    });
    observer.observe(preload, { attributes: true, attributeFilter: ['class'] });
  } else start();
})();

const INTRO_INFO = {
  how: { kicker: 'Así funciona', title: 'De la evidencia a la campaña.', paragraphs: ['Primero identificamos si ya tiene historia electoral o si empieza desde cero. Con ese punto de partida activamos únicamente las fuentes y los territorios que necesita su candidatura.', 'Después conectamos resultados, conversación pública, agenda normativa y territorio en un CRM preparado para convertir evidencia electoral en decisiones de campaña.'] },
  why: { kicker: 'Por qué elegirnos', title: 'Toda la inteligencia electoral, en un solo lugar.', paragraphs: ['Integramos evidencia territorial, competencia, resultados históricos y seguimiento de campaña para traducir información compleja en decisiones claras y oportunas.', 'Es una plataforma diseñada específicamente para candidaturas en Colombia: reúne una lectura que normalmente estaría dispersa entre bases, mapas y equipos distintos.'] }
};
function showIntroInfo(topic) {
  const content = INTRO_INFO[topic]; if (!content) return;
  $('introModalKicker').textContent = content.kicker; $('introModalTitle').textContent = content.title;
  $('introModalText').innerHTML = content.paragraphs.map(p => `<p>${p}</p>`).join('');
  $('introModal').classList.add('open');
}
function closeIntroModal() { $('introModal').classList.remove('open'); }
$('introModal').addEventListener('click', e => { if (e.target === $('introModal')) closeIntroModal(); });

/* ─── 3. Sesión, acceso y vínculo ────────────────────────────────────────── */
const SESSION = { token: null, user: null, listo: false, acceso: false, fuente: 'ninguno', vinculo: null, planes: null, soporte: 'hola@ricardoruiz.co', error: null };
const PLAN_LABEL = { free: 'Básico', pro: 'Pro', premium: 'Premium', full: 'Full', caudal: 'Caudal', c360: 'Candidato 360' };
function leerSesionLocal() {
  try { SESSION.token = localStorage.getItem('rr-token') || null; SESSION.user = JSON.parse(localStorage.getItem('rr-user') || 'null'); } catch { SESSION.token = null; SESSION.user = null; }
}
async function apiC360(path, opts = {}) {
  const headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
  if (SESSION.token) headers.Authorization = `Bearer ${SESSION.token}`;
  const r = await fetch(`${AUTH_API}${path}`, Object.assign({}, opts, { headers }));
  let data = null; try { data = await r.json(); } catch {}
  return { status: r.status, ok: r.ok && data?.ok !== false, data: data || {} };
}
async function cargarSesion() {
  leerSesionLocal();
  const planes = apiC360('/c360/planes').then(r => { if (r.ok) SESSION.planes = r.data; if (r.data?.soporte) SESSION.soporte = r.data.soporte; }).catch(() => {});
  if (SESSION.token) {
    try {
      const r = await apiC360('/c360/me');
      if (r.status === 401) { localStorage.removeItem('rr-token'); localStorage.removeItem('rr-user'); SESSION.token = null; SESSION.user = null; }
      else if (r.ok) { SESSION.acceso = !!r.data.acceso; SESSION.fuente = r.data.fuente || 'ninguno'; SESSION.vinculo = r.data.vinculo || null; if (r.data.soporte) SESSION.soporte = r.data.soporte; if (r.data.email) SESSION.user = Object.assign({}, SESSION.user || {}, { email: r.data.email, plan: r.data.plan }); }
      else SESSION.error = r.data?.error || `HTTP ${r.status}`;   /* sin respuesta válida no hay acceso: falla cerrado */
    } catch (e) { SESSION.error = String(e); }
  }
  await planes;
  SESSION.listo = true;
  resolverModoPruebas();
  pintarNav();
  aplicarGate();
}
function pintarNav() {
  const nav = $('navAuth'); if (!nav) return;
  const next = encodeURIComponent(PAGINA);
  if (!SESSION.token || !SESSION.user) { nav.innerHTML = `<a class="nav-login" href="login.html?next=${next}">Iniciar sesión</a><a class="nav-register" href="register.html?next=${next}">Registrarse</a>`; return; }
  const plan = String(SESSION.user.plan || 'free').toLowerCase();
  const etiqueta = SESSION.acceso ? (SESSION.fuente === 'plan' || SESSION.fuente === 'admin' ? PLAN_LABEL[plan] || plan : 'Acceso Candidato 360') : (PLAN_LABEL[plan] || plan);
  nav.innerHTML = `<span class="nav-plan${SESSION.acceso ? ' ok' : ''}">${escHtml(etiqueta)}</span><a class="nav-login" href="dashboard.html">Mi perfil</a><button type="button" class="nav-salir" onclick="cerrarSesion()">Salir</button>`;
}
async function cerrarSesion() {
  try { await apiC360('/auth/logout', { method: 'POST' }); } catch {}
  localStorage.removeItem('rr-token'); localStorage.removeItem('rr-user');
  location.href = PAGINA;
}

/* El muro: se ve lo que hay detrás, borroso, y se explica qué compra. */
function textoPrecio() {
  const p = SESSION.planes?.precio || {};
  if (p.mensual) return `$${Number(p.mensual).toLocaleString('es-CO')} COP al mes`;
  return 'Precio por confirmar';
}
/* Los tres planes son las «tres formas frecuentes de armarlo» del brief
   comercial (candidato-360-brief.html#precios). El precio queda «Por definir»
   hasta que Ricardo fije la cifra base por corporación; lo que sí decide el
   modal es el siguiente paso: sin cuenta → registrarse (y volver acá con el
   plan elegido); con cuenta → el pago si está configurado, o el correo. */
const C360_PLANES_UI = [
  { id: 'esencial', nombre: 'Esencial', desc: 'La base y el briefing en el correo. Para arrancar con el territorio claro y la meta puesta.', incluye: ['Historial mesa a mesa, recortado al territorio', 'Mapa por localidad, comuna y barrio', 'Meta de votos y electorado', 'Briefing cada 3 días en su correo'] },
  { id: 'escucha', nombre: 'Con escucha diaria', destacado: true, desc: 'La base, el briefing y la escucha social dos veces al día en las cuatro redes. El más elegido.', incluye: ['Todo lo del Esencial', 'Escucha social · X, Instagram, TikTok y Facebook', 'Dos lecturas al día sobre sus ideas y su nombre'] },
  { id: 'completo', nombre: 'Completo', desc: 'La campaña entera leída y planeada desde un solo lugar.', incluye: ['Todo lo de Con escucha diaria', 'Sentimiento en los comentarios', 'Endoso, estrategia y acciones de campaña', 'Arquetipos del territorio (hoy, Medellín y Cartagena)'] },
];
function abrirPaywall(motivo) {
  const modal = $('c360Paywall'); if (!modal) return;
  const configurado = Boolean(SESSION.planes?.configurado && SESSION.planes?.links?.mensual);
  const elegido = new URLSearchParams(location.search).get('plan') || (() => { try { return localStorage.getItem('c360-plan'); } catch { return ''; } })();
  $('c360PaywallMotivo').textContent = motivo || 'El detalle por barrio y los módulos se abren con un plan activo. Elija uno y su cuenta queda vinculada a este candidato.';
  $('c360PaywallPlanes').innerHTML = C360_PLANES_UI.map(pl => `<div class="c360-plan${pl.destacado ? ' destacado' : ''}${pl.id === elegido ? ' elegido' : ''}"><h3>${escHtml(pl.nombre)}</h3><div class="c360-plan-precio">Por definir<small> /mes</small></div><p>${escHtml(pl.desc)}</p><ul class="c360-lista">${pl.incluye.map(i => `<li>${escHtml(i)}</li>`).join('')}</ul><button type="button" class="wall-btn primary" onclick="elegirPlan('${pl.id}')">${SESSION.token ? 'Elegir este plan' : 'Crear cuenta y elegir'}</button></div>`).join('');
  const next = encodeURIComponent(`${PAGINA}?comprar=1${elegido ? `&plan=${elegido}` : ''}`);
  $('c360PaywallBotones').innerHTML = SESSION.token
    ? (configurado ? '' : `<span class="helper" style="margin:0">Mientras se define el precio, la activación se pide por correo: al elegir un plan se abre el mensaje.</span>`)
    : `<span class="helper" style="margin:0">¿Ya tiene cuenta en ricardoruiz.co? <a href="login.html?next=${next}">Inicie sesión</a> y elija el plan desde acá.</span>`;
  modal.classList.add('open');
}
function elegirPlan(id) {
  const plan = C360_PLANES_UI.find(p => p.id === id); if (!plan) return;
  try { localStorage.setItem('c360-plan', id); } catch {}
  if (!SESSION.token) { location.href = `register.html?next=${encodeURIComponent(`${PAGINA}?comprar=1&plan=${id}`)}`; return; }
  if (SESSION.planes?.configurado && SESSION.planes?.links?.mensual) return iniciarPago();
  const cuerpo = `Hola Ricardo, quiero activar Candidato 360 con el plan ${plan.nombre}${SESSION.user?.email ? ` para la cuenta ${SESSION.user.email}` : ''}${crmCandidate?.nombre ? ` (candidatura: ${crmCandidate.nombre})` : ''}.`;
  location.href = `mailto:${SESSION.soporte}?subject=${encodeURIComponent(`Candidato 360 · plan ${plan.nombre}`)}&body=${encodeURIComponent(cuerpo)}`;
}
function cerrarPaywall() { $('c360Paywall')?.classList.remove('open'); }
$('c360Paywall')?.addEventListener('click', e => { if (e.target === $('c360Paywall')) cerrarPaywall(); });
/* Mismo contrato que pricing.html: rr-pending-plan + customer-email +
   reference `rr-{email}-{plan}-{ciclo}-{ts}` (emailFromReference del worker). */
function iniciarPago() {
  const link = SESSION.planes?.links?.mensual; const email = SESSION.user?.email;
  if (!link || !email) return abrirPaywall();
  localStorage.setItem('rr-pending-plan', JSON.stringify({ planId: 'c360_mensual', planName: 'Candidato 360', billing: 'mensual', timestamp: Date.now() }));
  const params = new URLSearchParams({ 'customer-email': email, reference: `rr-${email}-c360-mensual-${Date.now()}` });
  location.href = `${link}?${params}`;
}

/* Confirmación antes de vincular: es la única decisión irreversible. */
let confirmarResolver = null;
function confirmarVinculo(nombre, detalle) {
  return new Promise(resolve => {
    confirmarResolver = resolve;
    $('c360ConfirmNombre').textContent = nombre;
    $('c360ConfirmDetalle').textContent = detalle || '';
    $('c360ConfirmSoporte').textContent = SESSION.soporte;
    $('c360Confirm').classList.add('open');
  });
}
function resolverConfirmacion(valor) { $('c360Confirm').classList.remove('open'); const r = confirmarResolver; confirmarResolver = null; if (r) r(valor); }
function vinculoDescripcion(v = SESSION.vinculo) {
  if (!v) return '';
  return v.tipo === 'nuevo' ? `${v.nuevo?.nombre || 'candidatura nueva'} (candidatura nueva)` : `${v.candidato?.nombre || 'candidato'} (historial electoral)`;
}
async function guardarVinculo(payload) {
  const r = await apiC360('/c360/vinculo', { method: 'POST', body: JSON.stringify(payload) });
  if (r.status === 409) { SESSION.vinculo = r.data.vinculo || SESSION.vinculo; return { ok: false, existente: true }; }
  if (r.status === 403) { SESSION.acceso = false; return { ok: false, sinAcceso: true }; }
  if (!r.ok) return { ok: false, error: r.data?.error || `HTTP ${r.status}` };
  SESSION.vinculo = r.data.vinculo; return { ok: true };
}
let CAMPANA_ACTUAL = null;
async function guardarCampana(campana) {
  if (!SESSION.vinculo) return;
  CAMPANA_ACTUAL = campana;
  if (SESSION.vinculo.local) { SESSION.vinculo.campana = campana; persistirVinculoLocal(); return; }
  try { const r = await apiC360('/c360/campana', { method: 'POST', body: JSON.stringify({ campana }) }); if (r.ok) SESSION.vinculo = r.data.vinculo; } catch {}
}
/* La meta la calcula VoteTarget en el navegador; se guarda en la campaña para
   que el briefing la recuerde. Solo si cambió, para no gastar escrituras de KV. */
function guardarMeta(target) {
  const c = CAMPANA_ACTUAL || SESSION.vinculo?.campana; if (!c || !target || !SESSION.vinculo) return;
  if (Number(SESSION.vinculo.campana?.meta || 0) === Number(target)) return;
  guardarCampana({ ...c, meta: target });
}
/* Panel 04: vive en su propio HTML (candidato-360-escucha.html) y lo que el
   CRM muestra es solo el estado de lo que esa página guardó en el vínculo. Son
   las dos mitades de la escucha —las ideas con las que se lee la prensa y las
   cuentas de redes—, así que la tarjeta dice cuál de las dos falta: «3 ideas»
   a secas dejaba creer que ya estaba todo configurado. */
function pintarEscucha() {
  const e = SESSION.vinculo?.escucha || {};
  const ideas = e.ideas?.length || 0, perfiles = e.redes?.perfiles?.length || 0;
  const dato = $('crmEscuchaEstado'), sub = $('crmEscuchaSub');
  if (!dato) return;
  const partes = [];
  if (ideas) partes.push(`${ideas} ${ideas === 1 ? 'idea' : 'ideas'}`);
  if (perfiles) partes.push(`${perfiles} ${perfiles === 1 ? 'cuenta' : 'cuentas'}`);
  dato.textContent = partes.length ? partes.join(' · ') : 'Sin configurar';
  if (!sub) return;
  const una = perfiles === 1;
  sub.textContent = !partes.length ? 'ideas y cuentas guardadas'
    : !perfiles ? 'sin cuentas conectadas'
    : !ideas ? (e.redes.validado ? `${una ? 'cuenta validada' : 'cuentas validadas'} · sin ideas` : `${una ? 'cuenta' : 'cuentas'} sin validar`)
    : (e.redes.validado ? `ideas y ${una ? 'cuenta validada' : 'cuentas validadas'}` : `${una ? 'cuenta' : 'cuentas'} sin validar`);
}
/* Interruptor del briefing (panel 03 del CRM). El estado vive en el vínculo. */
/* El copy del panel 03 vende el briefing según a qué se lanza y con quién:
   no es lo mismo lo que necesita saber cada tres días quien aspira a una JAL
   con un partido de oposición que quien va por una gobernación con el aval
   del gobierno. Cuando ya está encendido, la tarjeta vuelve a describir lo
   que manda. */
const BRIEFING_COPY_CORP = {
  jal: t => `Una JAL se gana cuadra por cuadra${t ? ` en ${t}` : ''}: la obra que la alcaldía local contrató y no ha empezado, la nota de prensa que nombra su zona, el acuerdo del Concejo que le cambia la vida a sus vecinos. Ellos van a preguntarle; el briefing hace que usted ya tenga la respuesta.`,
  concejo: t => `Un concejal se hace en el control político${t ? `, y en ${t}` : ', y'} eso empieza antes de la elección: qué contrató la alcaldía, con quién y por cuánto; qué obra se anunció y no llegó; qué norma nacional le mueve el presupuesto al municipio. Cada tres días, sin tener que buscarlo.`,
  alcaldia: t => `Quien aspira a la alcaldía${t ? ` de ${t}` : ''} tiene que hablar de la ciudad mejor que quien la gobierna: cada contrato firmado, cada titular regional, cada decreto nacional que le cambia el juego, en su correo y listo para el discurso.`,
  asamblea: t => `La asamblea se gana municipio por municipio${t ? ` en ${t}` : ''}: el briefing le sigue la prensa del departamento, los contratos de la gobernación y de las alcaldías, y las normas que tocan las regalías y la inversión regional. Usted llega a cada pueblo sabiendo qué pasó ahí esta semana.`,
  gobernacion: t => `Para gobernar${t ? ` ${t}` : ' un departamento'} hay que conocerlo mejor que el gobernador saliente: qué contrató, qué titula la prensa regional y qué decide la Nación sobre el territorio. Cada tres días, para que ningún alcalde ni ningún periodista sepa algo antes que usted.`,
};
function copyBriefing() {
  const c = CAMPANA_ACTUAL || SESSION.vinculo?.campana || {};
  const corp = c.corp || crmCandidate?.corp || 'concejo';
  const lugar = NOMBRE_BONITO(corp === 'jal' ? (c.localidad || c.municipio) : CORP_MUNICIPAL.includes(corp) ? c.municipio : c.departamentoNombre) || (META_ACTUAL?.detalle?.territorio || '');
  const base = (BRIEFING_COPY_CORP[corp] || BRIEFING_COPY_CORP.concejo)(lugar);
  const partido = sinPartido(c.avales) ? '' : (c.partido || crmCandidate?.partido || '');
  const bloque = partido ? (window.PartidosBloques?.bloqueDeCandidatura?.(partido, crmCandidate?.nombre || '') || 'sc') : (c.espectro || 'sc');
  const familia = FAMILIA_CON_ARTICULO[bloque] || FAMILIA_CON_ARTICULO.sc;
  const con = partido ? `Con el aval de ${NOMBRE_BONITO(partido)}` : c.avales === 'firmas' ? 'Por firmas, sin la maquinaria de un partido detrás' : `Desde ${familia}`;
  const linea = bloque === 'izq' || bloque === 'ci'
    ? `${con}, con el gobierno nacional en la otra orilla, cada contrato y cada decreto que aterrice en su territorio es una pregunta que solo usted va a estar listo para hacer.`
    : bloque === 'd' || bloque === 'cd'
      ? `${con}, cercano al gobierno nacional, le va a tocar defender lo que llegue a su territorio y explicar lo que no: el briefing le da los dos lados antes que a sus rivales.`
      : bloque === 'c'
        ? `${con}, se compite con argumentos y el argumento es el dato: el briefing se lo pone en la mano antes de cada debate.`
        : `${con}, la información es la ventaja que nadie le puede quitar: lo que otros se enteran por rumor, usted lo lee con fuente y fecha.`;
  const reg = crmCandidate ? regionDeCampana(crmCandidate, c) : { dep: c.departamento, municipio: c.municipio };
  const tema = window.C360Frases?.tema(reg) || '';
  const enTema = tema ? ` Ahí lo que más pesa es ${tema}: el briefing lo sigue por usted.` : '';
  return `${base}${enTema} ${linea} Se activa con un clic y el primero sale en la próxima corrida.`;
}
function pintarBriefing() {
  const b = SESSION.vinculo?.briefing || null, btn = $('crmBriefingBtn'), est = $('crmBriefingEstado'), sub = $('crmBriefingSub'), inp = $('crmBriefingCorreo');
  if (!btn) return;
  const copy = $('crmBriefingCopy');
  if (copy) copy.textContent = b && b.activo ? 'Cada tres días: la prensa que nombra a su territorio y a usted, los contratos que firmó su municipio y las normas nacionales que lo tocan.' : copyBriefing();
  if (inp && !inp.value) inp.value = b?.correo || SESSION.user?.email || '';
  const on = !!(b && b.activo);
  btn.textContent = on ? 'Apagar briefing' : 'Activar briefing'; btn.classList.toggle('on', on);
  est.textContent = on ? 'Encendido' : 'Apagado';
  if (on) { const u = b.ultimoEnvio ? new Date(b.ultimoEnvio) : null; sub.textContent = u ? `último envío ${u.toLocaleDateString('es-CO', { day: 'numeric', month: 'short' })} · ${b.envios || 0} enviados` : 'el primero sale en la próxima corrida (07:30)'; }
  else sub.textContent = 'se activa con un clic';
}
async function toggleBriefing() {
  if (!SESSION.acceso) return abrirPaywall();
  if (!SESSION.vinculo) { alert('Primero abra el CRM de su candidatura: el briefing se ata a ella.'); return; }
  const on = !!SESSION.vinculo.briefing?.activo, correo = ($('crmBriefingCorreo')?.value || '').trim();
  /* Con vínculo local no hay a quién avisarle: el interruptor se mueve para
     poder ver el panel, y se dice que no queda encendido de verdad. */
  if (SESSION.vinculo.local) { SESSION.vinculo.briefing = { activo: !on, correo, envios: 0 }; persistirVinculoLocal(); pintarBriefing(); $('crmBriefingSub').textContent = 'modo pruebas: el interruptor no se guardó en el servidor'; return; }
  const btn = $('crmBriefingBtn'); btn.disabled = true;
  try {
    const r = await apiC360('/c360/briefing', { method: 'POST', body: JSON.stringify({ activo: !on, correo }) });
    if (!r.ok) { alert(r.data?.error || `No se pudo cambiar el briefing (HTTP ${r.status})`); return; }
    SESSION.vinculo.briefing = r.data.briefing;
  } finally { btn.disabled = false; }
  pintarBriefing();
}

/* ─── 3 ter. El país ────────────────────────────────────────────────────────
   Primer paso del cuadro «Comencemos»: Colombia, Ecuador o Paraguay, con su
   bandera. Los módulos son los mismos en los tres; lo que cambia son los datos
   electorales y la cartografía, y eso se irá acomodando por país. La elección
   se recuerda por dispositivo y ?pais= manda sobre lo recordado. */
const PAISES = { co: { nombre: 'Colombia', bandera: '🇨🇴' }, ec: { nombre: 'Ecuador', bandera: '🇪🇨' }, py: { nombre: 'Paraguay', bandera: '🇵🇾' } };
let PAIS = null;
function paisInicial() {
  const q = new URLSearchParams(location.search).get('pais');
  if (q && PAISES[q]) return q;
  try { const g = localStorage.getItem('c360-pais'); if (g && PAISES[g]) return g; } catch {}
  return null;
}
let partidaTimer = 0;
function etapaIntro(stage) {
  $('intro').dataset.stage = stage;
  document.dispatchEvent(new CustomEvent('c360:intro-stage', { detail: { stage } }));
}
function elegirPais(codigo) {
  if (!PAISES[codigo]) return;
  PAIS = codigo;
  try { localStorage.setItem('c360-pais', codigo); } catch {}
  $('paisNombre').textContent = PAISES[codigo].nombre;
  $('paisPaso').classList.add('hidden');
  $('partidaPaso').classList.remove('hidden');
  $('partidaOpciones').classList.add('hidden');
  $('partidaSkip').classList.remove('hidden');
  clearTimeout(partidaTimer);
  etapaIntro('greeting');
  window.scrollTo({ top: 0, behavior: 'instant' });
  $('lunaSaludoTitulo').focus({ preventScroll: true });
  // Texto siempre disponible, incluso si el atlas de la mascota falla.
  partidaTimer = setTimeout(mostrarOpcionesPartida, matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 7500);
}
function mostrarOpcionesPartida() {
  clearTimeout(partidaTimer);
  if ($('intro').dataset.stage !== 'greeting' || $('intro').classList.contains('hidden')) return;
  $('partidaOpciones').classList.remove('hidden');
  const moveFocus = document.activeElement === $('partidaSkip');
  $('partidaSkip').classList.add('hidden');
  etapaIntro('options');
  if (moveFocus) $('partidaTitulo').focus({ preventScroll: true });
}
function cambiarPais(enfocar = true) {
  clearTimeout(partidaTimer);
  $('partidaPaso').classList.add('hidden'); $('paisPaso').classList.remove('hidden');
  etapaIntro('country');
  if (enfocar) document.querySelector('#paisPaso [data-pais="' + (PAIS || 'co') + '"]')?.focus({ preventScroll: true });
}
function montarPais() { PAIS = paisInicial(); }

/* ─── 3 bis. Modo pruebas (cuenta de administración) ─────────────────────────
   «Una cuenta = un candidato» es una regla del PRODUCTO: existe para que un
   cliente no se equivoque de candidatura, no para que quien construye la
   plataforma no pueda recorrerla. Con la cuenta de administración la página
   trabaja EN LOCAL: se entra por las dos rutas cuantas veces haga falta, se
   cambia de candidato y NADA se escribe en el worker — así ninguna prueba deja
   puesto un vínculo que después solo soporte puede borrar. Se apaga con
   ?pruebas=0 para ver la página tal como la ve un cliente. */
const ADMIN_EMAILS = ['reruizc@gmail.com', 'nuevagemela@gmail.com'];
let PRUEBAS = false;
function esAdmin() { return SESSION.fuente === 'admin' || ADMIN_EMAILS.includes(String(SESSION.user?.email || '').toLowerCase().trim()); }
function resolverModoPruebas() {
  PRUEBAS = esAdmin() && new URLSearchParams(location.search).get('pruebas') !== '0';
  /* El muro es de vitrina (el dato de esta página es público); abrirlo en local
     no da acceso a nada del worker, que sigue decidiendo por su cuenta. */
  if (PRUEBAS) SESSION.acceso = true;
}
/* Vínculo de mentiras: el CRM necesita uno para pintarse. Vive en memoria y
   además en sessionStorage de la pestaña, porque los paneles (escucha,
   electorado) son otras páginas: al volver con «← CRM» (?abrir=1) la memoria
   ya no existe y, sin esta copia, el modo pruebas caía a la búsqueda en vez de
   reabrir la candidatura que se estaba mirando. Se guarda en sessionStorage
   y en localStorage, y al leer manda localStorage (ver leerVinculoLocal). */
const VINCULO_LOCAL_KEY = 'c360-vinculo-pruebas';
function vinculoLocal(payload) { SESSION.vinculo = Object.assign({ local: true }, payload); persistirVinculoLocal(); }
function persistirVinculoLocal() {
  if (!SESSION.vinculo?.local) return;
  /* También en localStorage: quien escribe la URL de un panel en otra pestaña
     (lo normal al probar) no tiene el sessionStorage de esta. Al leer manda
     la de localStorage, que es siempre la última escrita. */
  try { const j = JSON.stringify(SESSION.vinculo); sessionStorage.setItem(VINCULO_LOCAL_KEY, j); localStorage.setItem(VINCULO_LOCAL_KEY, j); } catch {}
}
/* ⚠️ Manda la copia de localStorage, no la de la pestaña (sep-29-2026). Cada
   apertura escribe en las dos, así que la de localStorage es SIEMPRE la más
   reciente; la de sessionStorage puede ser vieja. Con la pestaña primero,
   Nury creó su candidatura nueva a la Alcaldía de Cartagena y el panel de
   arquetipos —abierto en una pestaña donde antes se probó a Fabio
   Aristizábal— le seguía mostrando Medellín. Costo aceptado: quien pruebe
   dos candidaturas a la vez en dos pestañas ve en los paneles la última. */
function leerVinculoLocal() {
  try { const v = JSON.parse(localStorage.getItem(VINCULO_LOCAL_KEY) || sessionStorage.getItem(VINCULO_LOCAL_KEY) || 'null'); return v && v.local && v.tipo ? v : null; } catch { return null; }
}
/* El vínculo real de la cuenta de administración estorba para probar: las
   páginas de medios y redes lo leen del servidor, no del modo pruebas. Esto
   llama a la ruta de soporte que ya existe (DELETE /c360/admin/vinculo), que
   deja copia del borrado 400 días. Solo funciona para quien es admin. */
async function borrarVinculoPropio() {
  if (!PRUEBAS || !SESSION.user?.email) return;
  if (!confirm(`¿Borrar de su cuenta el vínculo con ${vinculoDescripcion()}? Queda una copia en soporte por 400 días.`)) return;
  try {
    const r = await apiC360(`/c360/admin/vinculo?email=${encodeURIComponent(SESSION.user.email)}&motivo=${encodeURIComponent('pruebas: cuenta de administración')}`, { method: 'DELETE' });
    if (!r.ok) { alert(`No se pudo borrar: ${r.data?.error || r.status}`); return; }
    SESSION.vinculo = null; CAMPANA_ACTUAL = null;
    aplicarGate();
    alert('Listo: la cuenta quedó sin vínculo. Las páginas de medios y redes también lo van a ver vacío.');
  } catch (e) { alert('No se pudo borrar el vínculo: ' + e.message); }
}

/* Aplica el estado de acceso a las dos rutas y a la portada. */
function aplicarGate() {
  const intro = $('introVinculo');
  if (intro) {
    if (PRUEBAS) intro.innerHTML = `<b>Modo pruebas · cuenta de administración.</b> La restricción de «un solo candidato» está levantada: puede abrir cualquier candidatura por las dos rutas y nada se guarda en el servidor.${SESSION.vinculo && !SESSION.vinculo.local ? ` El vínculo real de la cuenta sigue siendo <b>${escHtml(vinculoDescripcion())}</b> y las páginas de medios y redes lo leen de ahí: <button type="button" class="enlace-boton" onclick="borrarVinculoPropio()">borrarlo de la cuenta</button>.` : ''} Para ver la página como la ve un cliente, abra <a href="${PAGINA}?pruebas=0">${PAGINA}?pruebas=0</a>.`;
    else if (SESSION.vinculo) intro.innerHTML = `Su cuenta está vinculada a <b>${escHtml(vinculoDescripcion())}</b>. Cualquiera de las dos rutas abre esa candidatura; para cambiarla escriba a <a href="mailto:${escHtml(SESSION.soporte)}">${escHtml(SESSION.soporte)}</a>.`;
    intro.classList.toggle('hidden', !PRUEBAS && !SESSION.vinculo);
    intro.classList.toggle('is-pruebas', PRUEBAS);
  }
  aplicarGateExistente();
  aplicarGateRuta();
  aplicarGateNuevo();
  if (new URLSearchParams(location.search).get('comprar') === '1' && SESSION.listo && !SESSION.acceso) { abrirPaywall(SESSION.token ? 'Su cuenta ya existe. Falta elegir el plan de Candidato 360.' : ''); history.replaceState(null, '', PAGINA); }
}
function muro(contenedor, texto) {
  if (!contenedor) return;
  let wall = contenedor.querySelector(':scope > .c360-wall');
  if (!wall) { wall = document.createElement('div'); wall.className = 'c360-wall'; contenedor.append(wall); }
  wall.innerHTML = `<div class="c360-wall-card"><span class="kicker">Candidato 360 · acceso</span><p>${texto}</p><button type="button" onclick="abrirPaywall()">Activar mi candidatura</button></div>`;
}
function quitarMuro(contenedor) { contenedor?.querySelector(':scope > .c360-wall')?.remove(); }
/* La búsqueda NO se tapa: el índice de candidaturas es la vitrina, y una
   vitrina borrosa no vende nada. Sin acceso se buscan los nombres y se
   selecciona uno igual que con acceso; el muro cae al ENTRAR al candidato
   (openHistoricCandidate → abrirPaywall), que es donde empieza lo que se
   cobra: el CRM, el mapa, la meta de votos y el briefing. */
function aplicarGateExistente() {
  const box = document.querySelector('#existing .search-box'); if (!box) return;
  box.classList.remove('locked'); quitarMuro(box);
  const bloqueado = SESSION.listo && !SESSION.acceso;
  let aviso = box.querySelector(':scope > .c360-vitrina');
  if (!bloqueado) return aviso?.remove();
  if (!aviso) {
    aviso = document.createElement('div');
    aviso.className = 'c360-vitrina';
    box.querySelector('.search-row')?.after(aviso);
  }
  aviso.innerHTML = `<p>Búsquese: su historial está acá y lo puede abrir para ver de qué candidaturas hablamos. Con él se arma el CRM de campaña, que puede ver en vista previa; el detalle por barrio y los módulos se abren con el acceso. Cada cuenta se vincula a <b>un solo candidato</b>.</p>`;
}
/* La pantalla del candidato se ve completa; lo que se anuncia es que el CRM
   —lo que se cobra— pide acceso. Anunciarlo ACÁ y no al final evita que
   alguien llene la corporación y el territorio para chocarse con un muro. */
function aplicarGateRuta() {
  const form = document.querySelector('#candidateRoute form'); if (!form) return;
  const bloqueado = SESSION.listo && !SESSION.acceso;
  /* El aviso se busca por id y en TODO el formulario. Buscarlo como hijo
     directo dejó de funcionar cuando los botones se mudaron al pie: se
     insertaba con `boton.before()`, o sea DENTRO de `.paso-pie`, la búsqueda no
     lo encontraba y cada llamada al gate agregaba otro —tres avisos iguales
     apilados entre los botones—. Ahora el aviso va ARRIBA del pie, que es
     donde se lee antes de decidir, y siempre es el mismo. */
  let aviso = form.querySelector('#avisoGateRuta');
  /* Por id, no por clase: en el pie hay dos botones «next» —continuar y abrir
     el CRM— y el primero se quedaba con la etiqueta del segundo. */
  const boton = $('abrirCRM');
  if (boton) boton.textContent = bloqueado ? 'Ver el CRM de campaña →' : 'Abrir CRM de campaña →';
  if (!bloqueado) return aviso?.remove();
  if (!aviso) {
    aviso = document.createElement('div');
    aviso.id = 'avisoGateRuta';
    aviso.className = 'c360-vitrina';
    (form.querySelector('.paso-pie') || boton)?.before(aviso);
  }
  aviso.innerHTML = `<p>Sin cuenta puede ver el CRM en vista previa: mapa, historial, proyección y meta de votos. El detalle por barrio y los módulos —briefing, escucha, arquetipos, perfil del votante— se abren con el acceso activo, que deja su cuenta vinculada a <b>este candidato</b>.</p>`;
}
function aplicarGateNuevo() {
  const box = document.querySelector('#new .search-box'); if (!box) return;
  const bloqueado = SESSION.listo && !SESSION.acceso;
  box.classList.toggle('locked', bloqueado);
  if (bloqueado) muro(box, 'La candidatura nueva se construye con su acceso activo. Cada cuenta se vincula a <b>una sola candidatura</b>, y esa decisión no se cambia desde la plataforma.');
  else quitarMuro(box);
}

/* ─── 4. Índice electoral y pantalla de espera ───────────────────────────── */
let historicalIndex = [], historicalSources = 0, historicalLocalDone = false, historicalBaseReady = false;
const historicalTotal = CandRegistry.SOURCES.length + CandRegistry.LOCAL_SOURCES.length;
const STRATEGY_LOADING_MESSAGES = ['Calculando cuánto necesita para ganar…', 'Midiendo el momentum de cada partido político…', 'Analizando cómo votaron en su barrio en la última elección…', 'Identificando dónde puede crecer su campaña…', 'Conectando las señales que pueden mover la elección…'];
let strategyLoadingIndex = Math.floor(Math.random() * STRATEGY_LOADING_MESSAGES.length);
function rotateStrategyMessage() { $('preloadText').textContent = STRATEGY_LOADING_MESSAGES[strategyLoadingIndex]; strategyLoadingIndex = (strategyLoadingIndex + 1) % STRATEGY_LOADING_MESSAGES.length; }
function paintIndexProgress() {
  historicalSources++;
  $('preloadBar').style.width = `${Math.min(96, 7 + (historicalSources / historicalTotal) * 89)}%`;
  const note = $('searchNote'); if (note) note.textContent = 'La información electoral se está preparando en segundo plano.';
}
function appendHistorical(list) {
  if (!list || !list.length) return;
  historicalIndex = historicalIndex.concat(list);
  if ($('candidateSearch')?.value.trim().length >= 2) searchCandidate($('candidateSearch').value);
}
async function prepareHistoricalIndex() {
  historicalBaseReady = true;
  const base = CandRegistry.load({ includeParties: false, onSource: list => { appendHistorical(list); paintIndexProgress(); } });
  const local = CandRegistry.loadLocal({ includeParties: false, onSource: list => { appendHistorical(list); paintIndexProgress(); } })
    .then(() => { historicalLocalDone = true; const note = $('searchNote'); if (note) note.textContent = 'La información electoral está lista para buscar.'; })
    .catch(() => { historicalLocalDone = true; });
  await Promise.allSettled([base, local]);
  historicalLocalDone = true;
  $('preloadBar').style.width = '100%'; $('preloadMeta').textContent = 'Inteligencia electoral preparada';
}
/* ─── 6 bis. Partidos: se escriben, no se buscan en una lista de mil ─────────
   En las territoriales de 2023 se inscribieron 2.258 organizaciones distintas
   en el país. Muchas son la misma coalición escrita de diez formas y muchas
   solo existen en un departamento. Un desplegable nacional con eso es
   inservible: en Bogotá hay 43 organizaciones y en Antioquia 341, y quien
   busca la suya en una lista de dos mil termina eligiendo la homónima de otro
   departamento.

   Por eso: se escribe, se sugiere lo del DEPARTAMENTO elegido y se acepta
   texto libre (una coalición que se inscribe en 2027 no está en ningún
   catálogo anterior).

   El catálogo cruza dos elecciones porque ninguna sola alcanza: las
   territoriales de 2023 traen los movimientos locales que solo existen en un
   municipio, y la CÁMARA DE 2026 dice qué está vivo hoy —Salvación Nacional no
   existía en 2023 y sacó 190.113 votos en Bogotá—. Cada entrada es
   [nombre, candidaturas de 2023, votos a Cámara 2026]; lo construye
   tools/candidato-360/partidos/construir.mjs y vive partido por departamento
   en candidato-360-data/partidos/. */
const partidosPorDep = new Map();
function cargarPartidos(dep) {
  const key = String(dep || '').padStart(2, '0');
  if (!/^\d{2}$/.test(key)) return Promise.resolve([]);
  if (!partidosPorDep.has(key)) partidosPorDep.set(key, (window.Candidato360Partidos?.[key] ? Promise.resolve() : loadCandidateMapScript(`candidato-360-data/partidos/${key}.js`))
    .then(() => window.Candidato360Partidos?.[key] || [])
    .catch(() => []));
  return partidosPorDep.get(key);
}
/* El departamento de una candidatura histórica: el segundo segmento del slug
   es el código ELECTORAL en las cinco fuentes territoriales (JAL2023-16-… es
   Bogotá). Si el slug no sirve, se busca por el nombre de la circunscripción. */
function departamentoDeCandidatura(candidate) {
  const delSlug = String(candidate?.slug || '').split('-')[1];
  if (/^\d{1,2}$/.test(delSlug || '')) { const p = delSlug.padStart(2, '0'); if (Object.values(DEP_CODES).includes(p)) return p; }
  const texto = normalizedText(`${candidate?.circunscripcion || ''} ${candidate?.corp || ''}`);
  if (/BOGOTA/.test(texto)) return '16';
  const hit = Object.entries(DEP_CODES).find(([nombre]) => nombre !== DEP_BOGOTA && texto.includes(normalizedText(nombre)));
  return hit ? hit[1] : '';
}
/* Ranking de sugerencias: cada palabra escrita tiene que prefijar alguna
   palabra del nombre (igual que el buscador de candidatos, que la gente ya
   sabe usar). Desempata el tamaño: primero las organizaciones que más
   candidaturas inscribieron en ese departamento. */
/* ⚠️ normalizedText() pega todo (quita hasta los espacios), que es justo lo
   que NO sirve acá: hay que comparar palabra por palabra. */
const normPalabras = s => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replace(/[^A-Z0-9Ñ]+/g, ' ').trim();
/* El tamaño de una organización en su departamento, en una escala común: no se
   pueden comparar votos a Cámara con número de candidaturas, así que cada uno
   se mide contra el mayor de su propia columna y gana el más alto de los dos.
   Sin esto, un movimiento local de 2023 con 300 candidaturas aplastaría a
   Salvación Nacional, que no tiene ninguna. */
function pesoPartidos(lista) {
  const maxVotos = Math.max(1, ...lista.map(x => x[2] || 0)), maxCand = Math.max(1, ...lista.map(x => x[1] || 0));
  return item => Math.max((item[2] || 0) / maxVotos, (item[1] || 0) / maxCand);
}
/* Las coaliciones (cuarto campo = 1) no se ofrecen: uno se lanza «con Cambio
   Radical», no «con Cambio Radical - MIRA - La U». Se quedan en el catálogo
   porque sí sirven para medir la huella del partido en el territorio. */
const esCoalicion = item => Number(item?.[3] || 0) === 1;
const partidosElegibles = lista => (lista || []).filter(x => !esCoalicion(x));
function rankearPartidos(lista, consulta, limite = 8) {
  lista = partidosElegibles(lista);
  const peso = pesoPartidos(lista);
  const q = normPalabras(consulta).split(' ').filter(Boolean);
  if (!q.length) return lista.slice(0, limite);
  const puntuadas = [];
  for (const item of lista) {
    const n = normPalabras(item[0]), palabras = n.split(' ');
    if (!q.every(w => palabras.some(pal => pal.startsWith(w)))) continue;
    puntuadas.push({ item, punto: (n.startsWith(q.join(' ')) ? 2 : 0) + (palabras[0]?.startsWith(q[0]) ? 1 : 0) });
  }
  return puntuadas.sort((a, b) => b.punto - a.punto || peso(b.item) - peso(a.item)).slice(0, limite).map(x => x.item);
}
/* Por qué esa organización está en la lista: lo más reciente primero. */
function respaldoPartido([, cand, votos]) {
  const partes = [];
  if (votos) partes.push(`${Number(votos).toLocaleString('es-CO')} votos a Cámara en 2026`);
  if (cand) partes.push(`${Number(cand).toLocaleString('es-CO')} candidatura${cand === 1 ? '' : 's'} territorial${cand === 1 ? '' : 'es'} en 2023`);
  return partes.join(' · ') || 'sin votación reciente registrada';
}
/* Un autocompletado sencillo y accesible: flechas, Enter, Escape y clic.
   `fuente()` devuelve la lista vigente; el campo NUNCA obliga a elegir de ella. */
function montarSugeridor({ input, lista, fuente, alElegir, logo }) {
  const caja = $(input), menu = $(lista); if (!caja || !menu) return;
  if (caja.dataset.sugeridor === '1') return;
  caja.dataset.sugeridor = '1';
  caja.setAttribute('autocomplete', 'off'); caja.setAttribute('role', 'combobox'); caja.setAttribute('aria-expanded', 'false');
  let opciones = [], activo = -1;
  const cerrar = () => { menu.classList.add('hidden'); menu.innerHTML = ''; activo = -1; caja.setAttribute('aria-expanded', 'false'); };
  const pintar = () => {
    menu.innerHTML = opciones.map((o, i) => `<button type="button" class="sugerencia${i === activo ? ' activa' : ''}" data-i="${i}">${logo?.(o[0]) || ''}<span><b>${escHtml(o[0])}</b><small>${escHtml(respaldoPartido(o))}</small></span></button>`).join('');
    menu.classList.toggle('hidden', !opciones.length); caja.setAttribute('aria-expanded', String(Boolean(opciones.length)));
  };
  const elegir = i => { const o = opciones[i]; if (!o) return; caja.value = o[0]; cerrar(); alElegir?.(o[0]); };
  const abrir = async () => { opciones = rankearPartidos(await fuente(), caja.value); activo = -1; pintar(); };
  caja.addEventListener('input', () => { abrir(); alElegir?.(caja.value); });
  caja.addEventListener('focus', abrir);
  caja.addEventListener('blur', () => setTimeout(cerrar, 140));
  caja.addEventListener('keydown', e => {
    if (e.key === 'Escape') return cerrar();
    if (!opciones.length) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); activo = (activo + 1) % opciones.length; pintar(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); activo = (activo <= 0 ? opciones.length : activo) - 1; pintar(); }
    else if (e.key === 'Enter' && activo >= 0) { e.preventDefault(); elegir(activo); }
  });
  menu.addEventListener('mousedown', e => { const boton = e.target.closest('[data-i]'); if (boton) { e.preventDefault(); elegir(Number(boton.dataset.i)); } });
}
/* Conecta un campo de partido con el departamento que lo filtra. */
/* ── Logos de partido ────────────────────────────────────────────────────────
   Un nombre en mayúsculas no se reconoce; el logo sí. Cada ciudad tiene su
   carpeta —se empezó por Bogotá— y su `index.json` lista SOLO los archivos que
   existen, así que mientras falten no hay imágenes rotas ni peticiones de más:
   simplemente no aparece el logo. Lo mantiene tools/candidato-360/logos. */
const LOGOS_PARTIDOS = new Map(), logosPendientes = new Map();
/* Un logo es de la ORGANIZACIÓN, no del departamento: el Partido Liberal se ve
   igual en Antioquia que en Bogotá. La carpeta está partida por departamento
   porque así se armó el repositorio y porque ahí viven los movimientos locales
   («Bogotá entre todos»), pero hoy solo existe la de Bogotá. Así que esa hace
   de catálogo BASE para todo el país y el departamento propio manda sobre ella
   cuando exista. Sin esto, fuera de Bogotá la vitrina se quedaba vacía y la
   pregunta del partido volvía a ser un campo de texto en blanco. */
const LOGOS_BASE = '16';
function cargarLogos(dep) {
  const key = String(dep || '').padStart(2, '0');
  const suyos = /^\d{2}$/.test(key) && key !== LOGOS_BASE ? [manifiestoLogos(key)] : [];
  return Promise.all([...suyos, manifiestoLogos(LOGOS_BASE)]).then(([primero]) => primero);
}
function manifiestoLogos(key) {
  /* `fetch` puede fallar ANTES de devolver promesa (un file:// abierto a mano,
     una CSP): si eso escapa, se lleva por delante al sugeridor de partidos, que
     es lo único importante de este campo. */
  if (!logosPendientes.has(key)) logosPendientes.set(key, Promise.resolve()
    .then(() => fetch(`candidato-360-data/logos-partidos/${key}/index.json`))
    .then(r => r.ok ? r.json() : null)
    .catch(() => null)
    .then(d => {
      /* Un manifiesto vacío o caído no borra lo que ya se tenga cargado. */
      if (d?.logos?.length) {
        LOGOS_PARTIDOS.set(key, new Map(d.logos.map(l => [normalizedText(l.nombre), `candidato-360-data/logos-partidos/${key}/${l.archivo}`])));
        const nucleos = new Map(); d.logos.forEach(l => { const n = nucleoLogo(l.nombre); if (n && !nucleos.has(n)) nucleos.set(n, `candidato-360-data/logos-partidos/${key}/${l.archivo}`); });
        LOGOS_NUCLEO.set(key, nucleos);
      }
      else if (!LOGOS_PARTIDOS.has(key)) LOGOS_PARTIDOS.set(key, new Map());
      return LOGOS_PARTIDOS.get(key);
    }));
  return logosPendientes.get(key);
}
/* Las listas a Cámara 2026 llevan el departamento en el nombre —«PACTO
   HISTÓRICO BOLÍVAR», «…ANTIOQUIA», «…CÓRDOBA»: el Pacto en 13
   departamentos— y el catálogo toma ese nombre porque es el vigente. Sin
   quitarlo no casaban con su logo y la rejilla, que solo muestra lo que tiene
   logo, dejaba al Pacto por fuera en todo el país menos Bogotá. Se compara el
   núcleo: sin «PARTIDO/MOVIMIENTO POLÍTICO» delante y sin el departamento
   al final. Solo el departamento EXACTO al final: «PACTO HISTÓRICO ALIANZA
   VERDE» es una coalición y no puede heredar solo el logo del Pacto. */
const COLAS_DEPARTAMENTO = [...new Set(Object.keys(DEP_CODES).flatMap(n => { const x = normPalabras(n); return [x, x.replace(/^(LA|EL) /, ''), x.replace(/^DISTRITO CAPITAL DE /, ''), x.replace(/ DEL CAUCA$/, ''), x.replace(/ Y PROVIDENCIA$/, '')]; }))].sort((a, b) => b.length - a.length);
function nucleoLogo(nombre) {
  let x = normPalabras(nombre).replace(/^(PARTIDO |MOVIMIENTO )?(POLITICO )?/, '');
  const cola = COLAS_DEPARTAMENTO.find(c => x.endsWith(` ${c}`) && x.length > c.length + 5);
  if (cola) x = x.slice(0, -cola.length - 1);
  return x.split(' ').length >= 2 ? x : '';
}
const LOGOS_NUCLEO = new Map();
function logoPorNucleo(key, nombre) { const n = nucleoLogo(nombre); return n ? LOGOS_NUCLEO.get(key)?.get(n) || '' : ''; }
function logoDePartido(nombre, dep) {
  const clave = normalizedText(nombre), key = String(dep || '').padStart(2, '0');
  return LOGOS_PARTIDOS.get(key)?.get(clave) || LOGOS_PARTIDOS.get(LOGOS_BASE)?.get(clave)
    || logoPorNucleo(key, nombre) || logoPorNucleo(LOGOS_BASE, nombre) || '';
}
function imgLogo(nombre, dep) {
  const src = logoDePartido(nombre, dep);
  /* Si el archivo desaparece, la etiqueta se borra sola: nunca un cuadro roto. */
  return src ? `<img class="logo-partido" src="${escHtml(src)}" alt="" loading="lazy" onerror="this.remove()">` : '';
}
function montarCampoPartido({ input, lista, estado, departamento }) {
  montarSugeridor({ input, lista, fuente: () => { cargarLogos(departamento()); return cargarPartidos(departamento()); }, logo: nombre => imgLogo(nombre, departamento()), alElegir: () => pintarEstadoPartido({ input, estado, departamento }) });
  pintarEstadoPartido({ input, estado, departamento });
}
async function pintarEstadoPartido({ input, estado, departamento }) {
  const nota = $(estado); if (!nota) return;
  const dep = departamento();
  if (!dep) { nota.textContent = 'Seleccione primero el departamento y le sugerimos las organizaciones que inscribieron candidatura allí.'; return; }
  const [catalogoCrudo] = await Promise.all([cargarPartidos(dep), cargarLogos(dep)]);
  const catalogo = partidosElegibles(catalogoCrudo), nombre = nombreDepartamento(dep);
  if (!catalogo.length) { nota.textContent = 'No pudimos cargar el catálogo de ese departamento: escriba el nombre y lo tomamos como está.'; return; }
  const escrito = String($(input)?.value || '').trim();
  const enCatalogo = escrito && catalogo.some(([n]) => normalizedText(n) === normalizedText(escrito));
  nota.innerHTML = imgLogo(escrito, dep) + (escrito && !enCatalogo
    ? `No aparece en ${escHtml(nombre)} ni en las territoriales de 2023 ni en la Cámara de 2026. Lo tomamos como está: puede ser una organización nueva o una coalición que se inscribe ahora.`
    : `${catalogo.length} organizaciones con votación en ${escHtml(nombre)}: las que inscribieron candidatura en las territoriales de 2023 y las que sacaron votos a la Cámara en 2026. Escriba y le sugerimos; también puede escribir una que no esté.`);
}
function nombreDepartamento(dep) {
  const hit = Object.entries(DEP_CODES).find(([, code]) => code === String(dep).padStart(2, '0'));
  return hit ? (hit[0] === DEP_BOGOTA ? 'Bogotá D.C.' : hit[0]) : 'ese departamento';
}
/* El campo del wizard de candidatura nueva, filtrado por su departamento. */
function loadParties() {
  montarCampoPartido({ input: 'party', lista: 'partyLista', estado: 'partyStatus', departamento: () => $('department')?.value || '' });
}

/* Pantalla de espera del índice: cuadritos + progreso REAL por fuente + datos
   curiosos del propio archivo (copiados de analisis-candidato para no inventar
   cifras). Sondeo cada 400 ms, sin rAF: sigue avanzando en pestaña de fondo. */
const C360_FACTS = [
  ['El votante mediano no existe', 'Un concejal <b>mediano</b> saca <b>69</b> votos. El más votado del país, <b>Edison Julián Forero</b>, sacó <b>70.032</b>: mil veces más.'],
  ['La política se decide abajo', '<b>8 de cada 10</b> candidaturas de este archivo son al Concejo, y el <b>61%</b> de ellas no llegó a <b>100</b> votos.'],
  ['Cuánto cuesta cada silla', 'Votación mediana por cargo: concejal <b>69</b> · edil <b>175</b> · diputado <b>1.126</b> · alcalde <b>1.250</b> · senador <b>1.491</b> · representante <b>2.157</b> · gobernador <b>22.429</b>.'],
  ['Un gobernador vale 325 concejales', 'El gobernador mediano saca <b>22.429</b> votos; el concejal mediano, <b>69</b>. Esa es la distancia entre los dos extremos del voto colombiano.'],
  ['Bogotá pesa más que el Senado', '<b>Carlos Fernando Galán</b> sacó <b>1.499.734</b> votos en la Alcaldía de 2023: más que el senador más votado de todo el archivo, <b>Álvaro Uribe</b> con <b>891.964</b>.'],
  ['El edil que le gana al alcalde', 'El más votado de una JAL, <b>Juan Camilo Ramírez</b> en Suba, sacó <b>12.165</b> votos: casi <b>diez veces</b> lo que saca un alcalde mediano.'],
  ['Diez por silla', 'Al Concejo de Bogotá de 2023 se presentaron <b>435</b> candidatos para <b>45</b> curules.'],
  ['El efecto de la lista cerrada', 'El Pacto Histórico y el Centro Democrático aparecen con <b>cero</b> votos nominales al Senado: el voto fue al logo, no a la persona.'],
  ['La misma persona, dos nombres', 'La Registraduría lo inscribe como «Gustavo Petro» en la presidencial y «Gustavo Francisco Petro Urrego» en la Alcaldía: aquí se unen en una sola ficha.'],
  ['El país cabe en este archivo', 'Son <b>437.845</b> candidaturas reales, con los concejos de <b>1.020</b> municipios en cuatro elecciones.']
];
let idxOrden = [], idxI = 0, idxFactTimer = null, idxPollTimer = null, idxPct = 0;
function idxPintaFact() {
  const el = $('idx-fact'); if (!el) return;
  if (!idxOrden.length) { idxOrden = C360_FACTS.map((_, i) => i); for (let i = idxOrden.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [idxOrden[i], idxOrden[j]] = [idxOrden[j], idxOrden[i]]; } }
  const [k, txt] = C360_FACTS[idxOrden[idxI % idxOrden.length]]; idxI++;
  el.classList.add('fade');
  setTimeout(() => { el.innerHTML = `<span class="idx-kicker">${k}</span>${txt}`; el.classList.remove('fade'); }, 300);
}
function idxLoaderHTML() {
  const [k, txt] = C360_FACTS[Math.floor(Math.random() * C360_FACTS.length)];
  return `<div class="idx-load" id="idx-load"><div class="idx-load-top"><div class="idx-load-count"><b id="idx-count">0</b> candidaturas listas</div><div class="idx-load-state" id="idx-state">Preparando el índice electoral</div></div><div class="idx-bar"><i id="idx-bar" style="width:4%"></i></div><div class="idx-fact" id="idx-fact"><span class="idx-kicker">${k}</span>${txt}</div></div><div class="idx-skel" id="idx-skel">${'<div class="idx-skel-row"><div class="idx-skel-av idx-sh"></div><div class="idx-skel-l"><i class="idx-sh w60"></i><i class="idx-sh w35"></i></div></div>'.repeat(3)}</div>`;
}
function idxRefresca() {
  const bar = $('idx-bar'); if (!bar) return idxDetiene();
  const pct = Math.min(97, 4 + (historicalSources / historicalTotal) * 93);
  if (pct > idxPct) { idxPct = pct; bar.style.width = `${pct}%`; }   /* nunca retrocede */
  const n = $('idx-count'); if (n) n.textContent = historicalIndex.length.toLocaleString('es-CO');
  const st = $('idx-state'); if (st) st.textContent = historicalLocalDone ? 'Índice completo' : `Faltan ${Math.max(0, historicalTotal - historicalSources)} fuentes`;
  if (historicalLocalDone) { bar.style.width = '100%'; setTimeout(idxCierra, 700); }
}
function idxDetiene() { clearInterval(idxFactTimer); clearInterval(idxPollTimer); idxFactTimer = idxPollTimer = null; }
function idxCierra() { idxDetiene(); $('idx-load')?.remove(); $('idx-skel')?.remove(); }
function idxArranca() {
  if (historicalLocalDone) return;
  const cont = $('searchResults'); if (!cont || $('idx-load')) return;
  cont.insertAdjacentHTML('afterbegin', idxLoaderHTML());
  idxI = 1; idxOrden = []; idxPct = 0;
  idxFactTimer = setInterval(idxPintaFact, 5200); idxPollTimer = setInterval(idxRefresca, 400); idxRefresca();
}
function idxSoloProgreso(hayConsulta) { const skel = $('idx-skel'); if (skel) skel.style.display = hayConsulta ? 'none' : 'grid'; }

/* ─── 5. Búsqueda de candidato con historial ─────────────────────────────── */
const candidateProfiles = new Map();
let crmCandidate = null;
/* Cuando los cuatro componentes del nombre coinciden es una sola persona y no
   una tarjeta por elección. El historial conserva todas sus candidaturas.
   Con TRES componentes (Daniel Carvalho Mejía: Cámara Antioquia 2022 y
   Concejo Medellín 2015 y 2019) también, pero solo si todas sus candidaturas
   territoriales caen en el MISMO departamento: «Juan Carlos López» aparece en
   veinte departamentos y son veinte personas; un nombre que solo existe en
   Antioquia es una. Lo nacional (Senado, consultas) no suma ni resta
   departamento. El listado de grupos para validar la regla lo produce
   tools/candidato-360/personas/similares.mjs. */
function fourNameKey(candidate) {
  const key = CandRegistry.personaKey(candidate?.nombre);
  const isRobertoOrtizCali = key === 'ROBERTO ORTIZ URUENA' && normalizedText(candidate?.circunscripcion).includes('CALI');
  const partes = key.split(/\s+/).filter(Boolean).length;
  return isRobertoOrtizCali ? `CALI-${key}` : partes === 4 || partes === 3 ? key : '';
}
/* Departamento electoral de una candidatura, por el slug: ASAM2023-31-…,
   GOB2023-1-…, ALC2023-16-…, JAL2023-16-…, CONC2019-1-… y CON2022-C-1-…
   (Cámara). Senado, presidencia, consultas y circunscripciones especiales
   (CA, CI, CE, CT) no tienen: ''. */
function departamentoDelSlug(slug) {
  const m = String(slug || '').match(/^(?:ASAM|GOB|ALC|JAL|CONC)\d{4}-(\d+)-|^CON\d{4}-C-(\d+)-/);
  return m ? String(m[1] || m[2]).replace(/^0+/, '') : '';
}
function candidateProfile(candidate) {
  const key = fourNameKey(candidate); if (!key) return { ...candidate, id: candidate.slug };
  const seen = new Set;
  const history = historicalIndex.filter(item => fourNameKey(item) === key).filter(item => { const itemKey = item.slug || `${item.nombre}|${item.corp}|${item.partido}`; if (seen.has(itemKey)) return false; seen.add(itemKey); return true; }).sort((a, b) => candidateYear(b) - candidateYear(a));
  if (history.length < 2) return { ...candidate, id: candidate.slug };
  if (key.split(/\s+/).length === 3 && new Set(history.map(item => departamentoDelSlug(item.slug)).filter(Boolean)).size !== 1) return { ...candidate, id: candidate.slug };
  const years = [...new Set(history.map(candidateYear).filter(Boolean))].sort((a, b) => a - b);
  return { ...history[0], id: `persona-${key.toLowerCase().replace(/\s+/g, '-')}`, nombre: history[0].nombre, history, historyVotes: history.reduce((sum, item) => sum + Number(item.votos || 0), 0), historyLabel: `${history.length} candidaturas registradas · ${years.join(', ')}` };
}
function beginHistorical() {
  /* Con vínculo no se busca: la cuenta ya tiene candidato (en modo pruebas sí). */
  if (SESSION.vinculo && !PRUEBAS) return abrirVinculo();
  showScreen('existing');
  $('searchResults').innerHTML = '<p class="search-note" id="searchNote">Escriba al menos dos letras: los resultados aparecerán mientras el índice termina de llegar.</p>';
  $('candidateSearch').disabled = false;
  setTimeout(idxArranca, 400);
}
let searchDebounceTimer = null, queuedSearch = '';
/* Debounce: no se repinta el índice de 439 mil registros por cada tecla. */
function searchCandidate(query, now = false) {
  queuedSearch = query || ''; clearTimeout(searchDebounceTimer);
  idxSoloProgreso(queuedSearch.trim().length >= 2);
  const note = $('searchNote'); if (queuedSearch.trim().length >= 2 && note) note.textContent = historicalLocalDone ? 'Buscando coincidencias…' : 'Actualizando el índice electoral…';
  const run = () => searchCandidateImmediate(queuedSearch);
  if (now) return run();
  searchDebounceTimer = setTimeout(run, historicalLocalDone ? 120 : 360);
}
function searchCandidateImmediate(query) {
  const q = (query || '').trim(), note = $('searchNote');
  document.querySelectorAll('#searchResults .result,#searchResults .empty,#searchResults .search-more').forEach(el => el.remove());
  if (q.length < 2) { if (note) note.textContent = 'Escriba al menos dos letras para buscar por nombre o apellido.'; return; }
  const queryAliases = { 'ROBERTO ORTIZ URENA': 'ROBERTO ORTIZ URUENA' };
  const rank = CandRegistry.acRank(queryAliases[CandRegistry.normNombre(q)] || q, historicalIndex, 12), items = rank.items;
  if (!items.length) { $('searchResults').insertAdjacentHTML('beforeend', `<div class="empty">${historicalBaseReady ? 'Aún no encontramos una coincidencia.' : 'El índice está llegando; pruebe de nuevo en unos segundos.'}</div>`); return; }
  candidateProfiles.clear();
  const shown = new Set, profiles = items.map(candidateProfile).filter(p => { if (shown.has(p.id)) return false; shown.add(p.id); candidateProfiles.set(p.id, p); return true; });
  $('searchResults').insertAdjacentHTML('beforeend', profiles.map(c => `<div class="result" role="button" tabindex="0" data-profile="${escHtml(c.id)}" onclick="elegirResultado(this)" onkeydown="if(event.key==='Enter')elegirResultado(this)"><div class="result-main"><span class="avatar">${escHtml(initials(c.nombre))}</span><span><b>${escHtml(c.nombre)}</b><small>${escHtml(c.historyLabel || `${c.corp || 'Historial electoral'} · ${c.partido || 'Sin partido registrado'}`)}${c.votos ? ` · ${Number(c.votos).toLocaleString('es-CO')} votos` : ''}</small></span></div><span class="tag">${SESSION.acceso ? 'Continuar' : 'Activar'}</span></div>`).join(''));
  if (note) note.textContent = historicalLocalDone ? `${historicalIndex.length.toLocaleString('es-CO')} candidaturas disponibles.` : 'Resultados parciales: seguimos incorporando concejos y JAL.';
  if (rank.total > items.length) $('searchResults').insertAdjacentHTML('beforeend', `<p class="search-note search-more">${items.length} de ${rank.total.toLocaleString('es-CO')} coincidencias · agregue un apellido para afinar.</p>`);
}
/* El clic en un resultado no cambia de pantalla de una: la tarjeta brinca
   primero. Son 320 ms que confirman CUÁL de los homónimos se eligió —el error
   más caro de esta pantalla es entrar al candidato equivocado— y de paso tapan
   el trabajo de armar el perfil. */
function elegirResultado(el) {
  if (!el || el.dataset.abriendo === '1') return;
  el.dataset.abriendo = '1';
  document.querySelectorAll('#searchResults .result').forEach(r => r.classList.toggle('elegido', r === el));
  salto(el);
  setTimeout(() => { el.dataset.abriendo = ''; openHistoricCandidate(el.dataset.profile); }, 320);
}
function openHistoricCandidate(id) {
  /* Sin acceso también se entra: ver su nombre y sus candidaturas es
     justamente lo que convence. El muro cae en launchCRM. */
  const profile = candidateProfiles.get(id) || historicalIndex.find(c => c.slug === id);
  if (!profile) return;
  if (SESSION.vinculo && !PRUEBAS && !vinculoCoincide(profile)) { alert(`Su cuenta ya está vinculada a ${vinculoDescripcion()}. Para cambiar de candidato escriba a ${SESSION.soporte}.`); return abrirVinculo(); }
  abrirRutaCandidato(profile);
}
function abrirRutaCandidato(profile) {
  crmCandidate = profile;
  $('routeInitials').textContent = initials(profile.nombre); $('routeName').textContent = profile.nombre;
  $('routeHistory').textContent = profile.historyLabel ? `Historial: ${profile.historyLabel}` : `Historial: ${profile.corp || 'candidatura registrada'}${profile.partido ? ` · ${profile.partido}` : ''}`;
  /* Se precarga el partido de su última elección, pero es un campo abierto:
     asumir que repite aval era el error. */
  if ($('campaignParty')) $('campaignParty').value = profile.partido || '';
  montarCampoPartido({ input: 'campaignParty', lista: 'campaignPartyLista', estado: 'campaignPartyStatus', departamento: departamentoDeCampana });
  const sameCorp = corporacionHistorica(profile);
  /* "La misma corporación" solo aplica si la última fue territorial: un Senado
     o una consulta no tienen "misma corporación" en las locales de 2027. */
  const sameOpt = document.querySelector('.route-option[data-route="same"]');
  sameOpt.classList.toggle('hidden', !sameCorp);
  $('sameCorporationLabel').textContent = sameCorp ? CRM_CORPORATIONS[sameCorp] : 'No aplica';
  campaignDeptOptions();
  /* Sin historial territorial la única ruta posible es «otra corporación», así
     que se marca sola; con historial no se preselecciona nada: la primera
     pregunta es la que manda y el resto aparece cuando se responda. */
  document.querySelectorAll('input[name="corporationRoute"]').forEach(r => { r.checked = !sameCorp && r.value === 'other'; });
  $('otherCorporation').value = ''; marcarCard(historicCorporationPicker, '');
  if ($('campaignParty')) $('campaignParty').value = profile.partido || '';
  toggleCorporationChoice();
  aplicarGateRuta();
  showScreen('candidateRoute');
}

/* ─── 6. Ruta con historial: corporación y territorio 2027 ───────────────── */
function corporacionHistorica(candidate) {
  const first = String(candidate?.corp || '').split('·')[0].trim().toLowerCase();
  if (first.includes('jal') || first.includes('administradora')) return 'jal';
  if (first.includes('concejo')) return 'concejo';
  if (first.includes('alcald')) return 'alcaldia';
  if (first.includes('asamblea')) return 'asamblea';
  if (first.includes('gobern')) return 'gobernacion';
  return '';
}
function campaignDeptOptions() { $('campaignDepartment').innerHTML = $('department').innerHTML; $('campaignDepartment').value = ''; }
const CORPORATION_CARDS = [
  ['jal', 'Junta Administradora Local', 'Decisiones desde la localidad.'],
  ['concejo', 'Concejo Distrital o Municipal', 'Representación local.'],
  ['alcaldia', 'Alcaldía Distrital o Municipal', 'Gestión de la ciudad.'],
  ['asamblea', 'Asamblea Departamental', 'Control y visión regional.'],
  ['gobernacion', 'Gobernación', 'Liderazgo para todo el territorio.']
];
function corporationCards(selected, onSelect) {
  const grid = document.createElement('div'); grid.className = 'corporation-card-grid';
  CORPORATION_CARDS.forEach(([key, title, description]) => {
    const card = document.createElement('button'); card.type = 'button'; card.className = `corporation-card${selected === key ? ' is-selected' : ''}`; card.dataset.corporation = key;
    card.innerHTML = `<b>${title}</b><small>${description}</small>`;
    card.addEventListener('click', () => { onSelect(key, card); grid.querySelectorAll('.corporation-card').forEach(item => item.classList.toggle('is-selected', item === card)); });
    grid.append(card);
  });
  return grid;
}
function createCorporationPicker(label, selected, onSelect) { const picker = document.createElement('div'); picker.className = 'corporation-picker'; picker.innerHTML = `<label>${label}</label>`; picker.append(corporationCards(selected, onSelect)); return picker; }
function marcarCard(picker, key) { picker?.querySelectorAll('.corporation-card').forEach(c => c.classList.toggle('is-selected', c.dataset.corporation === key)); }
/* ── El salto ────────────────────────────────────────────────────────────────
   Elegir algo en esta página abre otra pregunta más abajo, y sin un acuse el
   cambio pasa desapercibido: la persona no sabe si su clic entró. Dos brincos
   cortos sobre lo que acaba de elegir lo dicen sin una sola palabra. Con
   `prefers-reduced-motion` la animación no corre (lo apaga el CSS). */
function salto(el) {
  if (!el) return;
  el.classList.remove('salta'); void el.offsetWidth;   /* reinicia la animación si se repite el clic */
  el.classList.add('salta');
  el.addEventListener('animationend', () => el.classList.remove('salta'), { once: true });
}
/* ── La ruta, una pregunta por tarjeta ───────────────────────────────────────
   El paso 2 mostraba todo de una: corporación, territorio y partido, con la
   mitad de los campos deshabilitados esperando a que alguien adivinara el
   orden. Ahora funciona como la búsqueda del nombre: la tarjeta hace UNA
   pregunta y, al responderla, CAMBIA por la siguiente. El nombre de la persona
   se queda arriba, que es lo que da continuidad.

     misma corporación  →  partido
     otra corporación   →  cuál  →  dónde será  →  partido

   El camino de vuelta existe («← Atrás»): una pregunta a la vez solo funciona
   si se puede desandar. Y el copy de la izquierda dice en cuál va, para que
   los cuatro pasos no se sientan la misma pantalla. */
const PASO_COPY = {
  ruta: ['Definamos su próxima corporación.', 'Si cambia de corporación, ubique la candidatura: el territorio no tiene por qué ser el mismo de su elección anterior.'],
  corporacion: ['¿A cuál se lanza?', 'Las cinco corporaciones territoriales que se eligen en octubre de 2027.'],
  lugar: ['¿Dónde será la candidatura?', 'El territorio decide contra qué votación se mide su meta y qué mapa abre el CRM.'],
  partido: ['¿Con qué partido se lanza?', 'No tiene por qué ser el de su última elección: la mitad de las candidaturas territoriales cambia de aval de una elección a la siguiente.'],
};
let pasoRuta = 'ruta';
function rutaEsOtra() { return document.querySelector('input[name="corporationRoute"]:checked')?.value === 'other'; }
function pasosDeLaRuta() { return rutaEsOtra() ? ['ruta', 'corporacion', 'lugar', 'partido'] : ['ruta', 'partido']; }
function territorioListo(corp) { return corp ? campaignTerritory(corp) !== null : false; }
function irAPaso(nombre, { animar = false } = {}) {
  const pasos = pasosDeLaRuta();
  pasoRuta = pasos.includes(nombre) ? nombre : 'ruta';
  document.querySelectorAll('#candidateRoute .paso').forEach(el => {
    const activo = el.dataset.paso === pasoRuta;
    el.classList.toggle('hidden', !activo);
    if (activo && animar) { el.classList.add('paso-entra'); el.addEventListener('animationend', () => el.classList.remove('paso-entra'), { once: true }); }
  });
  /* «Atrás» no lleva a una pregunta que no se hizo: a quien no tiene historial
     territorial nunca se le preguntó «¿la misma corporación?». */
  const sinPreguntaDeRuta = document.querySelector('.route-option[data-route="same"]')?.classList.contains('hidden');
  $('pasoAtras').classList.toggle('hidden', pasos.indexOf(pasoRuta) <= (sinPreguntaDeRuta ? 1 : 0));
  $('abrirCRM').classList.toggle('hidden', pasoRuta !== 'partido');
  $('continuarLugar').classList.toggle('hidden', pasoRuta !== 'lugar');
  if (pasoRuta === 'partido') prepararPasoPartido();
  if (pasoRuta === 'lugar') { mapaDeptoRuta(); refrescarContinuar(); } else ocultarMapaDepto();
  const [titulo, copy] = PASO_COPY[pasoRuta] || PASO_COPY.ruta;
  $('rutaTitulo').textContent = titulo; $('rutaCopy').textContent = copy;
  if (animar) document.querySelector('#candidateRoute .search-box')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
/* Responder y pasar: primero el brinco sobre lo que se acaba de elegir y, con
   él todavía a la vista, la tarjeta cambia de pregunta. */
function avanzarPaso(nombre, elemento) {
  salto(elemento);
  setTimeout(() => irAPaso(nombre, { animar: true }), elemento ? 260 : 0);
}
function pasoAnterior() {
  const pasos = pasosDeLaRuta();
  irAPaso(pasos[Math.max(pasos.indexOf(pasoRuta) - 1, 0)], { animar: true });
}
/* ── El mapa del lugar, con drill down ───────────────────────────────────────
   Elegir «Boyacá» en un desplegable de 33 no confirma nada: los nombres se
   parecen y nadie revisa dos veces. El mapa sí, y sigue la misma escalera de
   la pregunta:

     sin departamento  →  Colombia apagada: falta elegir
     con departamento  →  SOLO ese departamento, encendido y con sus municipios
     con municipio     →  el departamento en gris y el municipio encendido

   La capa municipal es la MISMA que llena el desplegable de municipios
   (`Departamentos-mps/<cod>.json`, ya en caché), así que el drill down no
   cuesta una descarga más. Y como los municipios están dibujados, se pueden
   tocar: al hacerlo se elige ese municipio en el desplegable.              */
function proyectarMapa(geo, ancho) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  const recorre = c => { if (typeof c[0] === 'number') { x0 = Math.min(x0, c[0]); x1 = Math.max(x1, c[0]); y0 = Math.min(y0, c[1]); y1 = Math.max(y1, c[1]); } else c.forEach(recorre); };
  (geo.features || []).forEach(f => f.geometry?.coordinates && recorre(f.geometry.coordinates));
  /* Colombia va de -4° a 13° de latitud: a esa distancia del ecuador la
     corrección de Mercator no se nota, así que basta con escalar igual en los
     dos ejes y centrar. Estirarla para llenar la caja la deformaría.
     La caja, en cambio, sí se adapta a la figura: Atlántico es ancho y el
     Chocó es largo, y con un alto fijo cualquiera de los dos quedaba nadando
     en un marco vacío. El recorte se limita para que la tarjeta no se
     desfigure con un departamento muy alargado. */
  const alto = Math.round(Math.min(Math.max(ancho * (y1 - y0) / (x1 - x0), ancho * .62), ancho * 1.35));
  const escala = Math.min(ancho / (x1 - x0), alto / (y1 - y0)) * .96;
  const dx = (ancho - (x1 - x0) * escala) / 2, dy = (alto - (y1 - y0) * escala) / 2;
  const proy = ([lng, lat]) => [((lng - x0) * escala + dx).toFixed(1), ((y1 - lat) * escala + dy).toFixed(1)];
  return { proy, ancho, alto };
}
function caminoDeGeometria(geom, proy) {
  const anillos = geom?.type === 'Polygon' ? geom.coordinates : geom?.type === 'MultiPolygon' ? geom.coordinates.flat() : [];
  /* Un municipio trae miles de vértices y el mapita mide 300px: los puntos que
     caen en el mismo décimo de píxel se dibujarían uno encima de otro. */
  return anillos.map(anillo => {
    const puntos = []; let previo = '';
    anillo.forEach(c => { const punto = proy(c).join(' '); if (punto !== previo) { puntos.push(punto); previo = punto; } });
    return puntos.length > 2 ? 'M' + puntos.join('L') + 'Z' : '';
  }).join('');
}
function ocultarMapaDepto(id = 'mapaDepto') { $(id)?.classList.add('hidden'); }
/* Redibujar 125 municipios cada vez que cambia el desplegable sería tirar el
   trabajo hecho: el lienzo recuerda qué capa tiene puesta (`data-capa`) y, si
   es la misma, solo cambia de sitio la luz. */
async function pintarMapaDepto({ id = 'mapaDepto', codigo = '', nombre = '', municipio = '', select = '', selectDepto = '', local = null } = {}) {
  const caja = $(id), lienzo = $(id + 'Lienzo'); if (!caja || !lienzo) return;
  /* Tercer escalón: la JAL se elige por comuna o localidad, así que con el
     municipio ya contestado el mapa baja a la ciudad (si hay cartografía) y
     las localidades se tocan igual que los municipios. Sin capa de ciudad se
     queda en el municipio encendido, que es lo que había. */
  if (codigo && municipio && local && await pintarMapaCiudad({ id, caja, lienzo, nombre, municipio, local })) return 1;
  try {
    const capa = codigo || 'pais';
    if (lienzo.dataset.capa !== capa) {
      const geo = await fetchJSON(`${S3}/mapas-2026/${codigo ? `Departamentos-mps/${codigo}` : 'DEPARTAMENTOS2'}.json`);
      const { proy, ancho: W, alto: H } = proyectarMapa(geo, 300);
      const partes = (geo.features || []).map(f => {
        const parte = String((codigo ? f.properties?.mpio_cnmbr : f.properties?.name) || '');
        return `<path d="${caminoDeGeometria(f.geometry, proy)}" data-parte="${escHtml(parte)}" class="${codigo ? 'muni' : 'depto'}"><title>${escHtml(NOMBRE_BONITO(parte))}</title></path>`;
      }).join('');
      lienzo.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${escHtml(nombre ? (codigo ? `Mapa de ${nombre} por municipios` : `Mapa de Colombia con ${nombre} resaltado`) : 'Mapa de Colombia')}">${partes}</svg>`;
      lienzo.dataset.capa = capa;
    }
    lienzo.dataset.select = select;
    lienzo.dataset.selectDepto = codigo ? '' : selectDepto;
    /* Con departamento pero sin municipio se enciende el departamento entero:
       la silueta ES la respuesta a la pregunta que ya se contestó. */
    const objetivo = normalizedText(codigo ? municipio : nombre), todo = Boolean(codigo) && !municipio;
    let encendidos = 0;
    lienzo.querySelectorAll('path').forEach(path => {
      const suyo = todo || (objetivo && normalizedText(path.dataset.parte) === objetivo);
      path.classList.toggle('depto-elegido', Boolean(suyo));
      if (suyo) encendidos++;
    });
    const partes = lienzo.querySelectorAll('path').length;
    const pista = codigo && !municipio && partes > 1 ? 'Toque su municipio' : !codigo && selectDepto && !nombre ? 'Toque su departamento' : '';
    /* Bogotá es distrito y departamento: «BOGOTÁ, D.C. · Bogotá D.C.» sobra. */
    const repetido = normalizedText(municipio) === normalizedText(nombre);
    $(id + 'Pie').innerHTML = escHtml(municipio && !repetido ? `${NOMBRE_BONITO(municipio)} · ${nombre}` : (nombre || 'Elija el departamento')) + (pista ? `<small>${pista}</small>` : '');
    caja.classList.toggle('sin-elegir', !nombre);
    caja.classList.toggle('es-municipal', Boolean(codigo) && Boolean(select));
    caja.classList.toggle('es-pais', !codigo && Boolean(selectDepto));
    caja.classList.remove('es-local');
    caja.classList.remove('hidden');
    return encendidos;
  } catch (e) {
    /* Si la capa municipal no está, el mapa no desaparece: vuelve al de
       Colombia con el departamento encendido, que es lo que había antes. */
    if (codigo) { lienzo.dataset.capa = ''; return pintarMapaDepto({ id, nombre, select: '', selectDepto }); }
    ocultarMapaDepto(id);
  }
}
/* ¿La opción del desplegable (COMUNAS_DATA: «COMUNA 14 EL POBLADO»,
   «TEUSAQUILLO», «LOCALIDAD NO.4 NORTE CENTRO HI») es este polígono?
   Manda el NOMBRE cuando los dos lados lo traen: el número no es confiable
   entre fuentes (en Barranquilla la «localidad No. 4» de la Registraduría no
   es el polígono 4). Solo si a uno le falta nombre («COMUNA 1» contra
   «Comuna 1») se cruza por número, y ahí un corregimiento nunca casa con una
   comuna: Ibagué, Manizales o Villavicencio numeran los dos del 1 en adelante. */
const baseLocal = t => normalizedText(String(t || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase()
  .replace(/\b(COMUNAS?|COM|CORREGIMIENTOS?|CORREG|CORR|COR|LOCALIDAD|LOC|NO|AREA|DE|DEL|LA|EL|LOS|LAS)\b\.?/g, ' ').replace(/\d+/g, ' '));
const esCorregimiento = t => /^\s*(\d+\s*)?(CORR|COR\.|CORREG)/i.test(String(t || '').normalize('NFD').replace(/[\u0300-\u036f]/g, ''));
function casaLocal(config, props, opcion) {
  if (!opcion) return false;
  if (config.casaLocalidad) return config.casaLocalidad(props, opcion);
  const nombre = config.name(props), a = baseLocal(opcion), b = baseLocal(nombre);
  /* Prefijo y no «contiene»: «ORIENTAL» cabe dentro de «NORORIENTAL» y son
     comunas distintas de Bucaramanga; la Registraduría sí trunca por el final
     («NORTE CENTRO HI» por «Norte - Centro Histórico»). */
  if (a && b) return a === b || (a.length > 3 && b.length > 3 && (a.startsWith(b) || b.startsWith(a)));
  if (esCorregimiento(opcion) !== esCorregimiento(nombre)) return false;
  const codigo = String(config.code(props) || ''), nOpt = numeroDe(opcion), nCod = /^\d+$/.test(codigo) ? codigo.padStart(2, '0') : numeroDe(nombre);
  return Boolean(nOpt && nCod) && nOpt === nCod;
}
async function pintarMapaCiudad({ id, caja, lienzo, nombre, municipio, local }) {
  const config = cityLayerFor(municipio, { jal: true }); if (!config) return false;
  /* cityLayerFor casa por «contiene» y CALIMA contiene CALI: acá se exige que
     el nombre empiece o termine en la ciudad (mismo cuidado que el CRM). */
  const mun = normalizedText(municipio);
  if (!config.match.some(c => mismoMunicipio(mun, c))) return false;
  try {
    const capa = `ciudad:${config.path}`;
    if (lienzo.dataset.capa !== capa) {
      let geo = await fetchJSON(`${S3}/mapas-2026/Ciudades-COM-LOC/${config.path}`);
      if (config.rotate) geo = rotateGeoJSON90Left(geo);
      const { proy, ancho: W, alto: H } = proyectarMapa(geo, 300);
      const partes = (geo.features || []).map((f, i) => {
        const etiqueta = String(config.name(f.properties || {}) || '');
        return `<path d="${caminoDeGeometria(f.geometry, proy)}" data-i="${i}" class="local"><title>${escHtml(NOMBRE_BONITO(etiqueta))}</title></path>`;
      }).join('');
      lienzo.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${escHtml(`Mapa de ${NOMBRE_BONITO(municipio)} por ${config.title === 'localidad' ? 'localidades' : 'comunas'}`)}">${partes}</svg>`;
      lienzo._geo = geo; lienzo._config = config;
      lienzo.dataset.capa = capa;
    }
    lienzo.dataset.select = local.select; lienzo.dataset.selectDepto = '';
    const valor = $(local.select)?.value || '';
    let encendidos = 0;
    lienzo.querySelectorAll('path.local').forEach(path => {
      const suyo = casaLocal(config, lienzo._geo.features[Number(path.dataset.i)]?.properties || {}, valor);
      path.classList.toggle('depto-elegido', suyo);
      if (suyo) encendidos++;
    });
    const unidad = config.title === 'localidad' ? 'localidad' : 'comuna';
    const ciudad = normalizedText(municipio) === normalizedText(nombre) ? NOMBRE_BONITO(municipio) : `${NOMBRE_BONITO(municipio)} · ${nombre}`;
    $(id + 'Pie').innerHTML = escHtml(valor ? `${NOMBRE_BONITO(cortoLocal(valor) || valor)} · ${NOMBRE_BONITO(municipio)}` : ciudad) + (valor ? '' : `<small>Toque su ${unidad}</small>`);
    caja.classList.remove('sin-elegir', 'es-municipal', 'es-pais');
    caja.classList.add('es-local');
    caja.classList.remove('hidden');
    return true;
  } catch (e) { lienzo.dataset.capa = ''; return false; }
}
/* El mapa de la tarjeta del lugar y el del wizard preguntan lo mismo en dos
   formularios distintos: cada uno sabe de dónde leer su territorio. */
function mapaDeptoRuta() {
  const sel = $('campaignDepartment'), corp = $('otherCorporation').value, municipal = CORP_MUNICIPAL.includes(corp);
  const municipio = municipal ? ($('campaignMunicipality')?.value || '') : '';
  return pintarMapaDepto({ id: 'mapaDepto', codigo: sel?.value || '', nombre: nombreDepartamentoElegido(),
    municipio, select: municipal ? 'campaignMunicipality' : '', selectDepto: 'campaignDepartment',
    local: corp === 'jal' && municipio ? { select: 'campaignLocality' } : null });
}
/* El wizard de candidatura nueva sigue la misma escalera que la ruta con
   historial: Colombia apagada → departamento → municipio → (JAL) localidad. */
function mapaDeptoNuevo() {
  const sel = $('department'), election = $('election').value, municipal = MUNICIPAL_ELECTIONS.includes(election);
  const municipio = sel?.value && municipal ? ($('municipality')?.value || '') : '';
  return pintarMapaDepto({ id: 'mapaDeptoNuevo', codigo: sel?.value || '', nombre: sel?.value ? (sel.options[sel.selectedIndex]?.text || '') : '',
    municipio, select: municipal ? 'municipality' : '', selectDepto: 'department',
    local: election === 'jal' && municipio ? { select: 'locality' } : null });
}
/* Tocar un municipio en el mapa es responder el desplegable: el mapa no es un
   adorno al lado de la pregunta, es la otra manera de contestarla. */
document.addEventListener('click', evento => {
  const path = evento.target.closest?.('.mapa-depto.es-municipal .muni, .mapa-depto.es-pais .depto, .mapa-depto.es-local .local'); if (!path) return;
  const lienzo = path.closest('.mapa-depto-lienzo'); if (!lienzo) return;
  const esDepto = path.classList.contains('depto'), esLocal = path.classList.contains('local');
  const select = $(esDepto ? lienzo.dataset.selectDepto || '' : lienzo.dataset.select || ''); if (!select) return;
  /* Departamento: el polígono trae el nombre y el desplegable el código. */
  const opcion = esDepto ? [...select.options].find(o => o.value && o.value === DEP_CODES[path.dataset.parte])
    : esLocal ? [...select.options].find(o => o.value && casaLocal(lienzo._config, lienzo._geo?.features[Number(path.dataset.i)]?.properties || {}, o.value))
    : [...select.options].find(o => o.value && normalizedText(o.value) === normalizedText(path.dataset.parte));
  if (!opcion || select.value === opcion.value) return;
  select.value = opcion.value;
  select.dispatchEvent(new Event('change', { bubbles: true }));
});
function nombreDepartamentoElegido() { const sel = $('campaignDepartment'); return sel?.value ? (sel.options[sel.selectedIndex]?.text || '') : ''; }
/* El departamento se elige y se enciende en el mapa; de ahí en adelante manda
   la persona: el botón de continuar se habilita cuando el territorio está
   completo, pero no salta solo. */
async function elegirDepartamento() {
  await loadCampaignMunicipalities();   /* el catálogo limpia el municipio viejo antes de que el mapa lo lea */
  return mapaDeptoRuta();
}
function refrescarContinuar() {
  const boton = $('continuarLugar'); if (!boton) return;
  boton.disabled = !territorioListo($('otherCorporation').value);
}
/* Cada cambio del territorio decide si ya se puede continuar. */
function territorioResuelto() { refrescarContinuar(); }
const historicCorporationPicker = createCorporationPicker('Nueva corporación', '', (key, card) => { $('otherCorporation').value = key; updateCampaignTerritory(); avanzarPaso('lugar', card); });
historicCorporationPicker.id = 'historicCorporationPicker';
$('otherCorporationField').after(historicCorporationPicker);
function toggleCorporationChoice(opciones = {}) {
  const elegido = document.querySelector('input[name="corporationRoute"]:checked');
  const isOther = elegido?.value === 'other';
  $('otherCorporation').disabled = !isOther;
  if (isOther) updateCampaignTerritory();
  refrescarPartidoCampana();
  if (!elegido) return irAPaso('ruta');
  const siguiente = isOther ? 'corporacion' : 'partido';
  if (opciones.animar) avanzarPaso(siguiente, elegido.closest('.route-option'));
  else irAPaso(opciones.paso || siguiente);
}
/* El departamento que filtra el catálogo de partidos de la ruta: el elegido
   para 2027 si cambia de corporación, y si no el de su candidatura anterior. */
function departamentoDeCampana() {
  const isOther = document.querySelector('input[name="corporationRoute"]:checked')?.value === 'other';
  return (isOther ? $('campaignDepartment')?.value : '') || departamentoDeCandidatura(crmCandidate);
}
function refrescarPartidoCampana() { pintarEstadoPartido({ input: 'campaignParty', estado: 'campaignPartyStatus', departamento: departamentoDeCampana }); }

/* El partido con el que se lanza, que NO tiene por qué ser el de su última
   elección: la mitad de las candidaturas territoriales cambia de aval entre
   una elección y la siguiente. Manda lo que la persona escribió. */
function partidoVigente() {
  if (sinPartido(CAMPANA_ACTUAL?.avales)) return '';
  return String(CAMPANA_ACTUAL?.partido || $('campaignParty')?.value || '').trim() || crmCandidate?.partido || '';
}
function updateCampaignTerritory() {
  const corp = $('otherCorporation').value, municipal = CORP_MUNICIPAL.includes(corp), jal = corp === 'jal';
  refrescarPartidoCampana();
  /* Sin departamento no hay municipio que ofrecer: el desplegable en «Primero
     seleccione departamento» es una pregunta que no se puede responder. */
  $('campaignMunicipalityField').classList.toggle('hidden', !municipal || !$('campaignDepartment').value);
  $('campaignLocalityField').classList.toggle('hidden', !jal || !$('campaignMunicipality').value);
  if (!municipal) $('campaignMunicipalityNota').classList.add('hidden');
  $('campaignDepartment').required = municipal || CORP_DEPARTAMENTAL.includes(corp); $('campaignMunicipality').required = municipal; $('campaignLocality').required = jal;
  if ($('campaignDepartment').value && municipal) loadCampaignMunicipalities();
}
async function cargarMunicipios(select, dep, cacheKey) {
  select.innerHTML = '<option value="">Cargando municipios…</option>';
  try {
    const data = await fetchJSON(`${S3}/mapas-2026/Departamentos-mps/${dep}.json`);
    municipalitiesByDepartment[cacheKey] = data;
    const municipalities = [...new Set(data.features.map(f => f.properties.mpio_cnmbr).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'es'));
    /* La capital encabeza la lista: concentra las candidaturas del
       departamento y es la que más se busca. No hace falta una tabla de 33
       capitales —la Divipola las marca con el código de municipio 001— así que
       la regla la decide el DATO y no un `if` por departamento. */
    const capital = data.features.find(f => String(f.properties?.mpio_ccdgo || '') === '001')?.properties?.mpio_cnmbr || '';
    const orden = [...municipalities.filter(m => m === capital), ...municipalities.filter(m => m !== capital)];
    select.innerHTML = optionList(orden.map(m => ({ value: m, label: NOMBRE_BONITO(m) })), 'Seleccione municipio o distrito');
    return orden;
  } catch (e) { select.innerHTML = '<option value="">No se pudieron cargar los municipios</option>'; return []; }
}
/* Un departamento con UN solo municipio no tiene nada que preguntar: Bogotá
   D.C. es distrito y departamento a la vez, y pedir «municipio o distrito»
   después de haberla elegido en el departamento es un paso vacío. La regla se
   decide con el DATO (cuántos municipios trae la fuente) y no con un `if` sobre
   el código 16: si mañana entra otro distrito, ya está resuelto. El valor se
   pone igual —el mapa, la meta y el briefing lo necesitan—, lo que se ahorra es
   la pregunta. */
function municipioImplicito(select, field, nota, municipios) {
  const unico = municipios.length === 1;
  field.classList.toggle('hidden', unico);
  if (unico) select.value = municipios[0];
  if (nota) {
    nota.classList.toggle('hidden', !unico);
    nota.textContent = unico ? `${NOMBRE_BONITO(municipios[0])} es el único municipio del departamento: la candidatura queda ubicada ahí.` : '';
  }
  return unico;
}
let municipalitiesByDepartment = {};
async function loadCampaignMunicipalities() {
  const dep = $('campaignDepartment').value;
  refrescarPartidoCampana();                 /* otro departamento, otro catálogo de partidos */
  if (!dep) { $('campaignMunicipalityField').classList.add('hidden'); return refrescarContinuar(); }
  $('campaignLocality').innerHTML = '<option value="">Primero seleccione municipio</option>';
  /* Ya hay departamento: la pregunta del municipio tiene sentido y aparece
     —salvo que el departamento tenga uno solo, que lo decide municipioImplicito. */
  if (CORP_MUNICIPAL.includes($('otherCorporation').value)) $('campaignMunicipalityField').classList.remove('hidden');
  const municipios = await cargarMunicipios($('campaignMunicipality'), dep, `crm-${dep}`);
  if (municipioImplicito($('campaignMunicipality'), $('campaignMunicipalityField'), $('campaignMunicipalityNota'), municipios)) loadCampaignLocalities();
  territorioResuelto();
}
async function cargarLocalidades(select, status, depNombre, munNombre) {
  select.innerHTML = '<option value="">Cargando comunas o localidades…</option>'; status.textContent = '';
  try {
    const localities = await localidadesDe(depNombre, munNombre);
    select.innerHTML = optionList(localities.map(l => ({ value: l, label: NOMBRE_BONITO(l) })), 'Seleccione comuna o localidad');
    status.textContent = localities.length ? `${localities.length} comunas o localidades disponibles.` : 'No hay una división local disponible para este municipio en la fuente actual.';
  } catch (e) { select.innerHTML = '<option value="">No se pudieron cargar las comunas o localidades</option>'; status.textContent = 'La fuente territorial no está disponible en este momento.'; }
}
async function loadCampaignLocalities() {
  mapaDeptoRuta();                           /* el municipio elegido se enciende en el mapa */
  const jal = $('otherCorporation').value === 'jal', hayMunicipio = Boolean($('campaignMunicipality').value);
  $('campaignLocalityField').classList.toggle('hidden', !jal || !hayMunicipio);
  territorioResuelto();
  if (!jal || !hayMunicipio) return;
  await cargarLocalidades($('campaignLocality'), $('campaignLocalityStatus'), $('campaignDepartment').options[$('campaignDepartment').selectedIndex].text, $('campaignMunicipality').value);
}
function campaignTerritory(corp) {
  if (document.querySelector('input[name="corporationRoute"]:checked')?.value !== 'other') return '';
  const dep = $('campaignDepartment').options[$('campaignDepartment').selectedIndex]?.text || '', mun = $('campaignMunicipality').value, local = $('campaignLocality').value;
  if (!$('campaignDepartment').value || (CORP_MUNICIPAL.includes(corp) && !mun) || (corp === 'jal' && !local)) return null;
  const seen = new Set;
  return [local, mun, dep].filter(Boolean).filter(place => { const key = normalizedText(place); if (seen.has(key)) return false; seen.add(key); return true; }).map(NOMBRE_BONITO).join(' · ');
}
function currentTargetTerritory() {
  const isOther = document.querySelector('input[name="corporationRoute"]:checked')?.value === 'other';
  if (!isOther) return null;
  const departmentName = $('campaignDepartment').options?.[$('campaignDepartment').selectedIndex]?.text || '';
  return { corporation: String($('otherCorporation').value || ''), department: normalizedText(departmentName), municipality: normalizedText($('campaignMunicipality').value || ''), locality: normalizedText($('campaignLocality').value || '') };
}
/* Lo que se guarda como campaña en el vínculo (editable). */
function campanaActual(corpKey) {
  const isOther = document.querySelector('input[name="corporationRoute"]:checked')?.value === 'other';
  const aval = avalVigente();
  const firmas = CORP_UNINOMINAL.includes(corpKey) && aval === 'firmas', indeciso = aval === 'indeciso';
  return { corp: corpKey, avales: firmas ? 'firmas' : indeciso ? 'indeciso' : 'partido', espectro: firmas || indeciso ? espectroVigente() : '',
    partido: firmas || indeciso ? '' : (String($('campaignParty')?.value || '').trim() || crmCandidate?.partido || ''), ruta: isOther ? 'other' : 'same', departamento: isOther ? $('campaignDepartment').value : '', departamentoNombre: isOther ? ($('campaignDepartment').options[$('campaignDepartment').selectedIndex]?.text || '') : '', municipio: isOther ? $('campaignMunicipality').value : '', localidad: isOther ? $('campaignLocality').value : '' };
}
/* Rellena la ruta con la campaña guardada (al volver con vínculo). */
async function precargarCampana(campana) {
  if (!campana) return;
  const isOther = campana.ruta === 'other' || !corporacionHistorica(crmCandidate);
  document.querySelector(`input[name="corporationRoute"][value="${isOther ? 'other' : 'same'}"]`).checked = true;
  if (campana.partido && $('campaignParty')) $('campaignParty').value = campana.partido;
  /* Quien volvió sin partido —por firmas o sin decidirse— vuelve con su
     espectro puesto, no con la pregunta en blanco. */
  if (sinPartido(campana.avales)) { const r = document.querySelector(`input[name="avalRuta"][value="${campana.avales}"]`); if (r) r.checked = true; marcarEspectro(campana.espectro || ''); }
  else if (campana.partido) { const r = document.querySelector('input[name="avalRuta"][value="partido"]'); if (r) r.checked = true; }
  toggleCorporationChoice();
  if (!isOther) return;
  $('otherCorporation').value = campana.corp; marcarCard(historicCorporationPicker, campana.corp); updateCampaignTerritory();
  if (campana.departamento) {
    $('campaignDepartment').value = campana.departamento;
    if (CORP_MUNICIPAL.includes(campana.corp)) { await loadCampaignMunicipalities(); $('campaignMunicipality').value = campana.municipio || ''; }
    if (campana.corp === 'jal' && campana.municipio) { await loadCampaignLocalities(); $('campaignLocality').value = campana.localidad || ''; }
  }
  irAPaso('partido');                     /* quien vuelve cae en la última pregunta, ya respondida */
}

/* ─── 6 ter. Aval: con partido o por firmas ──────────────────────────────────
   A la Alcaldía y a la Gobernación se llega de dos maneras y las dos son
   normales: con el aval de un partido o por firmas, como grupo significativo
   de ciudadanos. Antes la página solo sabía preguntar por el partido, y quien
   iba por firmas tenía que escribir algo que no existía.

   Por firmas no hay huella de partido que seguir, así que se pregunta lo único
   que de verdad orienta la recolección: DÓNDE SE UBICA en el espectro. Con eso
   el reparto usa la huella del bloque ideológico —el mismo diccionario que
   pinta los mapas— y la tarjeta de firmas dice en qué comunas o municipios
   están los votos de esa familia política, que es donde una firma cuesta menos
   trabajo. El espectro no es una etiqueta que le ponemos: es la que la persona
   se pone, y se puede cambiar. */
const ESPECTRO = [
  ['izq', 'Izquierda'],
  ['ci', 'Centro-izquierda'],
  ['c', 'Centro'],
  ['cd', 'Centro-derecha'],
  ['d', 'Derecha'],
];
const CORP_UNINOMINAL = ['alcaldia', 'gobernacion'];
function corpDeLaRuta() {
  const isOther = document.querySelector('input[name="corporationRoute"]:checked')?.value === 'other';
  return isOther ? $('otherCorporation').value : (corporacionHistorica(crmCandidate) || '');
}
function avalVigente() { return document.querySelector('input[name="avalRuta"]:checked')?.value || 'partido'; }
/* Por firmas o sin decidirse: no hay partido, hay familia política. Todo lo
   que se calcula con la huella del partido se calcula con la del bloque. */
function sinPartido(aval) { return aval === 'firmas' || aval === 'indeciso'; }
/* `avalVigente()` supone «partido» cuando no hay nada marcado —es lo que
   necesitan los cálculos—, pero la PANTALLA no puede suponerlo: la rejilla de
   partidos salía antes de que la persona eligiera «Con un partido». */
function avalElegidoPartido() { return document.querySelector('input[name="avalRuta"]:checked')?.value === 'partido'; }
function espectroVigente() { return $('espectro')?.querySelector('[aria-checked="true"]')?.dataset.bloque || ''; }
/* El bloque con el que se reparte: el que la persona eligió si va por firmas,
   y si no el que le corresponde a su partido. */
function bloqueVigente() {
  if (sinPartido(CAMPANA_ACTUAL?.avales) || (!CAMPANA_ACTUAL && sinPartido(avalVigente()))) return CAMPANA_ACTUAL?.espectro || espectroVigente() || '';
  return '';
}
/* El mismo espectro sirve en la ruta con historial (#espectro) y en el wizard
   de candidatura nueva (#espectroNuevo): una sola forma de pintarlo. */
function pintarEspectroEn(caja, alCambiar) {
  if (!caja || caja.dataset.listo === '1') return;
  caja.dataset.listo = '1';
  caja.innerHTML = ESPECTRO.map(([id, label]) => {
    const color = window.PartidosBloques?.BLOQUE_COLOR?.[id] || 'var(--green)';
    return `<button type="button" class="espectro-op" role="radio" aria-checked="false" data-bloque="${id}" style="--bloque:${color}"><i></i><b>${label}</b></button>`;
  }).join('');
  caja.addEventListener('click', e => {
    const boton = e.target.closest('[data-bloque]'); if (!boton) return;
    caja.querySelectorAll('[data-bloque]').forEach(b => b.setAttribute('aria-checked', String(b === boton)));
    salto(boton);
    alCambiar?.();
  });
}
function pintarEspectro() { pintarEspectroEn($('espectro'), refrescarContinuarPartido); }
function espectroNuevoVigente() { return $('espectroNuevo')?.querySelector('[aria-checked="true"]')?.dataset.bloque || ''; }
function marcarEspectro(bloque) {
  pintarEspectro();
  $('espectro')?.querySelectorAll('[data-bloque]').forEach(b => b.setAttribute('aria-checked', String(b.dataset.bloque === bloque)));
}
/* La pregunta del aval solo aplica a los cargos uninominales: a un concejo o a
   una asamblea se llega por lista, y una lista siempre tiene organización. */
function elegirAval({ animar = false } = {}) {
  const aval = avalVigente(), firmas = aval === 'firmas', indeciso = aval === 'indeciso', espectro = sinPartido(aval);
  if (animar) salto(document.querySelector(`input[name="avalRuta"]:checked`)?.closest('.route-option'));
  revelar($('espectroField'), espectro, animar);
  revelar($('campaignPartyField'), avalElegidoPartido(), animar);
  revelar($('vitrinaPartidos'), avalElegidoPartido() && vitrinaTienePartidos(), animar);
  if (espectro) pintarEspectro(); else refrescarPartidoCampana();
  if (pasoRuta === 'partido' && firmas) { $('rutaTitulo').textContent = '¿Dónde se ubica?'; $('rutaCopy').textContent = 'Por firmas no hay partido cuya huella seguir. Con el espectro buscamos dónde votan los partidos de su familia: ahí es donde las firmas se recogen más rápido.'; }
  else if (pasoRuta === 'partido' && indeciso) { $('rutaTitulo').textContent = '¿Dónde se siente mejor ideológicamente?'; $('rutaCopy').textContent = 'Todavía no tiene partido y queda más de un año de campaña. Con su familia política se calcula todo —la meta, el mapa proyectado, el electorado— y el partido se pone cuando lo tenga, desde el CRM.'; }
  else if (pasoRuta === 'partido') { const [t, c] = PASO_COPY.partido; $('rutaTitulo').textContent = t; $('rutaCopy').textContent = c; }
  refrescarContinuarPartido();
}
function revelar(el, visible, animar) {
  if (!el) return;
  const estaba = !el.classList.contains('hidden');
  el.classList.toggle('hidden', !visible);
  if (visible && !estaba && animar) { el.classList.add('paso-entra'); el.addEventListener('animationend', () => el.classList.remove('paso-entra'), { once: true }); }
}
/* Por firmas hace falta el espectro para poder decir dónde recogerlas. */
function refrescarContinuarPartido() {
  const boton = $('abrirCRM'); if (!boton) return;
  /* Sin ninguna opción marcada no se sigue: suponer «con partido» fue lo que
     dejaba ver la rejilla antes de tiempo. */
  const marcado = document.querySelector('input[name="avalRuta"]:checked');
  boton.disabled = !marcado || (sinPartido(avalVigente()) && !espectroVigente());
}
/* «Ya tengo partido político»: desde el CRM se vuelve al paso del partido con
   «con un partido» marcado; al abrir el CRM de nuevo la campaña se guarda con
   el partido y todo se recalcula con su huella. */
async function definirPartido() {
  /* Candidatura nueva: el partido se define en el wizard, en su paso. Quien
     vuelve de otra sesión trae el formulario vacío, así que se rellena desde
     lo guardado antes de saltar al paso. */
  if (!crmCandidate && NUEVO) {
    await precargarNuevo(NUEVO);
    showScreen('new');
    $('partyMode').value = 'existing'; toggleParty();
    window.showNewWizardStep?.(4);
    $('party')?.focus({ preventScroll: true });
    return;
  }
  showScreen('candidateRoute');
  const r = document.querySelector('input[name="avalRuta"][value="partido"]'); if (r) r.checked = true;
  irAPaso('partido', { animar: true });
  $('campaignParty')?.focus({ preventScroll: true });
}
async function precargarNuevo(n) {
  const c = n.campana || {};
  if ($('newName') && !$('newName').value) $('newName').value = n.nombre || '';
  if ($('publicFigure')) { $('publicFigure').checked = Boolean(n.publico); togglePublicName(); if (n.nombrePublico) $('publicName').value = n.nombrePublico; }
  if ($('goal') && n.objetivo) $('goal').value = n.objetivo;
  if (c.corp && $('election').value !== c.corp) { $('election').value = c.corp; updateTerritory(); }
  if (c.departamento && $('department').value !== c.departamento) {
    $('department').value = c.departamento;
    if (MUNICIPAL_ELECTIONS.includes(c.corp)) { await Promise.resolve(loadMunicipalities()); $('municipality').value = c.municipio || ''; }
    if (c.corp === 'jal' && c.municipio) { await Promise.resolve(loadLocalities()); $('locality').value = c.localidad || ''; }
  }
}
function prepararPasoPartido() {
  /* Las firmas son de los cargos uninominales; «no me he decidido» es de
     cualquiera: a una lista también se llega con partido por definir. */
  const uninominal = CORP_UNINOMINAL.includes(corpDeLaRuta());
  revelar($('avalOpciones'), true, false);
  document.querySelector('.route-option[data-aval="firmas"]')?.classList.toggle('hidden', !uninominal);
  if (!uninominal && avalVigente() === 'firmas') {
    document.querySelectorAll('input[name="avalRuta"]').forEach(r => { r.checked = r.value === 'partido'; });
  }
  elegirAval();
  montarVitrinaPartidos();
}

/* ─── 6 quáter. La vitrina de partidos ───────────────────────────────────────
   Un municipio colombiano tiene 9 organizaciones en promedio inscritas al
   concejo (mediana 9, máximo 23 en 2023): eso cabe en una rejilla y no hace
   falta escribirlo. Donde hay logos se muestran como una vitrina —se elige
   con el ojo, no con el teclado— y a la derecha queda la ficha de lo elegido.
   El campo de texto sigue ahí para lo que no está: una coalición que se
   inscribe ahora no existe en ningún catálogo. */
/* Cuántas caben: un municipio tiene 9,3 organizaciones inscritas al concejo en
   promedio (mediana 9; el p90 es 15 y el máximo medido en 2023 fue 23), así que
   16 tarjetas cubren el caso real sin volverse un muro. El catálogo del
   departamento trae más —listas de JAL, de Cámara, el mismo partido escrito de
   cuatro formas—: se deduplica por logo, que es lo que el ojo distingue, y se
   corta por fuerza. Lo que quede fuera se escribe. */
const VITRINA_MINIMO = 4, VITRINA_MAXIMO = 16;
let VITRINA = [];
function vitrinaTienePartidos() { return VITRINA.length >= VITRINA_MINIMO; }
async function montarVitrinaPartidos() {
  const caja = $('vitrinaPartidos'), rejilla = $('vitrinaRejilla'); if (!caja || !rejilla) return;
  const dep = departamentoDeCampana();
  VITRINA = [];
  try {
    const [catalogo] = await Promise.all([cargarPartidos(dep), cargarLogos(dep)]);
    const conLogo = partidosElegibles(catalogo).filter(o => logoDePartido(o[0], dep));
    const vistos = new Set();
    VITRINA = rankearPartidos(conLogo, '', 60)
      .filter(o => { const logo = logoDePartido(o[0], dep); if (!logo || vistos.has(logo)) return false; vistos.add(logo); return true; })
      .slice(0, VITRINA_MAXIMO);
  } catch (e) { VITRINA = []; }
  if (!vitrinaTienePartidos()) { caja.classList.add('hidden'); return; }
  rejilla.innerHTML = VITRINA.map((o, i) => `<button type="button" class="vitrina-op" data-i="${i}" title="${escHtml(o[0])}">${imgLogo(o[0], dep)}<small>${escHtml(nombreCortoPartido(o[0]))}</small></button>`).join('');
  // Se arma siempre (así está lista), pero solo se ve con «Con un partido» marcado.
  caja.classList.toggle('hidden', !avalElegidoPartido());
  if (!rejilla.dataset.listo) {
    rejilla.dataset.listo = '1';
    rejilla.addEventListener('click', e => {
      const boton = e.target.closest('[data-i]'); if (!boton) return;
      const o = VITRINA[Number(boton.dataset.i)]; if (!o) return;
      $('campaignParty').value = o[0];
      rejilla.querySelectorAll('[data-i]').forEach(b => b.classList.toggle('elegido', b === boton));
      salto(boton);
      fichaVitrina(o);
      refrescarPartidoCampana();
    });
  }
  const escrito = String($('campaignParty')?.value || '').trim();
  const yaElegido = VITRINA.findIndex(o => normalizedText(o[0]) === normalizedText(escrito));
  if (yaElegido >= 0) { rejilla.querySelectorAll('[data-i]')[yaElegido]?.classList.add('elegido'); fichaVitrina(VITRINA[yaElegido]); }
  else fichaVitrina(null);
}
/* «MOVIMIENTO POLÍTICO PACTO HISTÓRICO» no cabe debajo de un logo. */
function nombreCortoPartido(nombre) {
  return String(nombre).replace(/^(PARTIDO|MOVIMIENTO)\s+(POLÍTICO|POLITICO)?\s*/i, '').replace(/\s*[-–]\s*.*$/, '').trim() || nombre;
}
function fichaVitrina(o) {
  const ficha = $('vitrinaFicha'); if (!ficha) return;
  if (!o) { ficha.innerHTML = '<p class="vitrina-vacia">Elija una organización para ver su fuerza en el territorio, o escríbala abajo si no está.</p>'; return; }
  const dep = departamentoDeCampana(), bloque = window.PartidosBloques?.bloqueDePartido?.(o[0]) || 'sc';
  ficha.innerHTML = `${imgLogo(o[0], dep)}<h4>${escHtml(o[0])}</h4>`
    + `<p class="vitrina-respaldo">${escHtml(respaldoPartido(o))}</p>`
    + `<p class="vitrina-bloque"><span style="background:${window.PartidosBloques?.BLOQUE_COLOR?.[bloque] || 'var(--green)'}"></span>${escHtml(window.PartidosBloques?.BLOQUE_LABEL?.[bloque] || 'Sin clasificar')}</p>`;
}

/* ─── 7. Candidatura nueva: wizard ───────────────────────────────────────── */
async function cargarDepartamentos() {
  try {
    const data = await fetchJSON(`${S3}/mapas-2026/DEPARTAMENTOS2.json`);
    const names = data.features.map(f => f.properties.name).filter(n => DEP_CODES[n]).sort((a, b) => a.localeCompare(b, 'es'));
    /* Bogotá encabeza la lista y el resto sigue alfabético: una de cada cinco
       candidaturas territoriales del país se juega ahí, y en un desplegable de
       33 departamentos «Distrito Capital» quedaba enterrado en la D. */
    const orden = [...names.filter(n => n === DEP_BOGOTA), ...names.filter(n => n !== DEP_BOGOTA)];
    $('department').innerHTML = '<option value="">Seleccione un departamento</option>' + orden.map(n => `<option value="${DEP_CODES[n]}">${n === DEP_BOGOTA ? 'Bogotá D.C.' : n}</option>`).join('');
    campaignDeptOptions();
  } catch (e) { $('department').innerHTML = '<option value="">No se pudieron cargar los departamentos</option>'; }
}
async function loadMunicipalities() {
  const dep = $('department').value; if (!dep) return;
  const municipios = await cargarMunicipios($('municipality'), dep, dep);
  /* Al fijarlo por código no hay evento `change`: la localidad se pide a mano. */
  if (municipioImplicito($('municipality'), $('municipalityField'), $('municipalityNota'), municipios)) updateLocality();
  else mapaDeptoNuevo();   /* el mapa baja al departamento cuando ya están sus municipios */
}
async function loadLocalities() { await cargarLocalidades($('locality'), $('localityStatus'), $('department').options[$('department').selectedIndex].text, $('municipality').value); }
function updateTerritory() {
  const election = $('election').value, municipal = MUNICIPAL_ELECTIONS.includes(election), dep = $('department').value;
  pintarEstadoPartido({ input: 'party', estado: 'partyStatus', departamento: () => $('department').value });
  /* Misma regla que la ruta con historial: sin departamento no hay municipio
     que ofrecer, y sin municipio no hay localidad. */
  $('municipalityField').classList.toggle('hidden', !municipal || !dep); $('localityField').classList.add('hidden');
  if (!municipal) $('municipalityNota').classList.add('hidden');
  $('municipality').required = municipal; $('locality').required = election === 'jal';
  $('locality').innerHTML = '<option value="">Primero seleccione municipio</option>';
  if (municipal && dep) { $('municipality').innerHTML = '<option value="">Cargando municipios…</option>'; loadMunicipalities(); }
  else $('municipality').innerHTML = '<option value="">Primero seleccione departamento</option>';
  mapaDeptoNuevo();
}
function updateLocality() {
  const jal = $('election').value === 'jal', hay = Boolean($('municipality').value);
  $('localityField').classList.toggle('hidden', !jal || !hay);
  mapaDeptoNuevo();
  if (jal && hay) loadLocalities();
}
function togglePublicName() { $('publicNameField').classList.toggle('hidden', !$('publicFigure').checked); $('publicName').required = $('publicFigure').checked; }
/* ─── 7 bis. Identidad pública: ¿tiene redes? ─────────────────────────────
   El paso 2 pedía marcar cada red, escribir el usuario y validarlo antes de
   seguir. Era demasiado para la segunda pregunta de alguien que apenas está
   conociendo la plataforma (decisión de Ricardo, sep-30-2026): ahora solo se
   pregunta SI tiene redes y, si dice que sí, CUÁLES. El usuario exacto de cada
   cuenta —y su validación contra la red— se piden después, en el panel de
   escucha social, que ya tiene ese flujo completo.
   Lo marcado viaja como `escucha.preferencias.redes` del vínculo: así el panel
   de escucha abre con esas redes ya marcadas en su cuestionario. */
const REDES_DEFS = [
  { key: 'facebook', nombre: 'Facebook', detalle: 'página o perfil' },
  { key: 'x', nombre: 'X', detalle: 'antes Twitter' },
  { key: 'instagram', nombre: 'Instagram', detalle: 'perfil público' },
  { key: 'tiktok', nombre: 'TikTok', detalle: 'video corto' }
];
const nombreRed = key => (REDES_DEFS.find(d => d.key === key) || {}).nombre || key;
let TIENE_REDES = '';   /* '' sin responder · 'si' · 'no' */
function montarRedes() {
  const grid = $('redesGrid'); if (!grid) return;
  grid.innerHTML = REDES_DEFS.map(r => `<button type="button" class="red-chip" data-red="${r.key}" aria-pressed="false" onclick="toggleRed('${r.key}')"><i></i><b>${escHtml(r.nombre)}</b><small>${escHtml(r.detalle)}</small></button>`).join('');
}
function tieneRedes(valor) {
  const antes = TIENE_REDES; TIENE_REDES = valor;
  document.querySelectorAll('.redes-opcion').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.tiene === valor)));
  $('redesCuales').classList.toggle('hidden', valor !== 'si');
  if (valor !== 'si') document.querySelectorAll('#redesGrid .red-chip').forEach(b => b.setAttribute('aria-pressed', 'false'));
  /* Candi explica para qué sirven en el momento en que importa: cuando dice
     que sí. Una sola vez por respuesta, no a cada clic. */
  if (valor === 'si' && antes !== 'si') window.Candi?.decir?.('¡Buenísimo! Tus redes nos sirven para tres cosas: afinar tu huella, mejorar el cálculo electoral y montar la escucha social. Por ahora solo marca en cuáles estás; el usuario exacto de cada cuenta te lo pido más adelante.');
}
function toggleRed(key) {
  const b = document.querySelector(`#redesGrid .red-chip[data-red="${key}"]`); if (!b) return;
  b.setAttribute('aria-pressed', String(b.getAttribute('aria-pressed') !== 'true'));
}
function redesElegidas() {
  return TIENE_REDES === 'si' ? [...document.querySelectorAll('#redesGrid .red-chip[aria-pressed="true"]')].map(b => b.dataset.red) : [];
}
/* El paso no se puede saltar sin contestar, y «sí» sin marcar ninguna es una
   respuesta a medias. */
function redesRespondidas() {
  if (!TIENE_REDES) { const c = document.querySelector('.redes-si-no'); c?.classList.add('shake'); setTimeout(() => c?.classList.remove('shake'), 500); return false; }
  if (TIENE_REDES === 'si' && !redesElegidas().length) { const g = $('redesGrid'); g?.classList.add('shake'); setTimeout(() => g?.classList.remove('shake'), 500); return false; }
  return true;
}
/* Una frase para el CRM: qué redes declaró y qué falta. */
function textoRedesCRM(n) {
  const usa = n?.redesUsa || [];
  if (n?.tieneRedes === 'no') return ' Todavía no tiene redes: la escucha social arranca con la prensa y las cuentas se suman cuando las abra.';
  if (!usa.length) return '';
  const lista = usa.map(nombreRed), texto = lista.length > 1 ? `${lista.slice(0, -1).join(', ')} y ${lista.at(-1)}` : lista[0];
  return ` Está en ${texto}: el usuario de cada cuenta se pide en la escucha social.`;
}

/* Tres respuestas: un partido que existe, uno por constituir, o ninguno
   todavía —y entonces el espectro, con el que se calcula todo mientras tanto—. */
function toggleParty() {
  const modo = $('partyMode').value, isNew = modo === 'new', indeciso = modo === 'indeciso';
  $('partyExisting').classList.toggle('hidden', isNew || indeciso); $('partyNew').classList.toggle('hidden', !isNew); $('partyEspectro')?.classList.toggle('hidden', !indeciso);
  $('party').required = !isNew && !indeciso; $('partyName').required = isNew;
  if (indeciso) pintarEspectroEn($('espectroNuevo'));
}
/* Una pregunta a la vez. Los campos se MUEVEN, no se recrean, para conservar
   validaciones y datos ya cargados. */
const NEW_STEPS_TOTAL = 6;
function montarWizardNuevo() {
  const form = document.querySelector('#new form'); if (!form) return;
  const findField = id => $(id)?.closest('.field');
  const fields = { name: findField('newName'), pub: findField('publicFigure'), pubName: $('publicNameField'), redes: $('redesField'), election: findField('election'), department: findField('department'), municipality: findField('municipality'), locality: findField('locality'), mapa: $('mapaDeptoNuevo')?.closest('.field'), partyMode: findField('partyMode'), partyExisting: $('partyExisting'), partyNew: $('partyNew'), partyEspectro: $('partyEspectro'), goal: findField('goal') };
  const formGrid = form.querySelector('.form-grid'), originalSubmit = form.querySelector('[type="submit"]');
  const wizard = document.createElement('div'); wizard.className = 'new-wizard'; formGrid.before(wizard);
  Object.values(fields).forEach(f => f?.remove()); formGrid.remove(); originalSubmit.remove();
  const steps = [
    { title: '¿Cómo aparecerá en campaña?', copy: 'Empecemos por su nombre completo.', fields: [fields.name] },
    { title: '¿Dónde puede encontrarlo la gente?', copy: 'Su nombre público y si tiene redes sociales. Los usuarios de cada cuenta se los pedimos más adelante.', fields: [fields.pub, fields.pubName, fields.redes], redes: true },
    { title: '¿A qué corporación aspira?', copy: 'La corporación define el territorio y la lectura electoral que activaremos.', fields: [fields.election], cards: true },
    /* El mapa viaja con la pregunta del territorio: si se queda en la rejilla
       original lo borra el `formGrid.remove()` de abajo y el wizard pierde la
       confirmación que sí tiene la ruta. */
    { title: '¿Dónde será la candidatura?', copy: 'Ubique el territorio en el que va a competir.', fields: [fields.department, fields.municipality, fields.locality, fields.mapa], lugar: true },
    { title: '¿Con qué partido o movimiento?', copy: 'Puede vincular una organización existente o preparar una nueva.', fields: [fields.partyMode, fields.partyExisting, fields.partyNew, fields.partyEspectro] },
    { title: '¿Cuál es el primer objetivo?', copy: 'Con esto cerraremos su punto de partida.', fields: [fields.goal], final: true }
  ];
  const electionSelect = fields.election.querySelector('#election'); fields.election.id = 'electionField'; electionSelect.value = '';
  fields.municipality.classList.add('hidden'); fields.locality.classList.add('hidden');
  steps.forEach((def, index) => {
    const step = document.createElement('section'); step.className = `new-wizard-step${index === 0 ? ' active' : ''}`; step.dataset.step = index;
    step.innerHTML = `<div class="wizard-progress">${steps.map((_, p) => `<i class="${p <= index ? 'active' : ''}"></i>`).join('')}</div><h3>${def.title}</h3><p>${def.copy}</p>`;
    if (def.lugar) {
      /* Formulario y mapa lado a lado, como en la ruta con historial: el mapa
         es la otra manera de contestar la misma pregunta. */
      const grid = document.createElement('div'); grid.className = 'lugar-grid';
      const campos = document.createElement('div'); campos.className = 'lugar-campos';
      def.fields.filter(f => f && f !== fields.mapa).forEach(f => campos.append(f));
      grid.append(campos); if (fields.mapa) grid.append(fields.mapa); step.append(grid);
    } else def.fields.forEach(f => f && step.append(f));
    if (def.cards) { const picker = createCorporationPicker('Seleccione una corporación', '', key => { electionSelect.value = key; updateTerritory(); }); picker.id = 'newCorporationPicker'; step.append(picker); }
    const actions = document.createElement('div'); actions.className = 'wizard-actions';
    if (index) { const back = document.createElement('button'); back.type = 'button'; back.className = 'wizard-back'; back.textContent = '← Anterior'; back.addEventListener('click', () => showNewWizardStep(index - 1)); actions.append(back); }
    const next = document.createElement('button'); next.type = def.final ? 'submit' : 'button'; next.className = 'next wizard-next'; next.textContent = def.final ? 'Crear punto de partida →' : 'Siguiente →';
    if (!def.final) next.addEventListener('click', () => advanceNewWizard(index));
    actions.append(next); step.append(actions); wizard.append(step);
  });
  montarRedes();   /* después de repartir los campos: antes, #redesGrid está desprendido del documento */
  function showNewWizardStep(index) {
    wizard.querySelectorAll('.new-wizard-step').forEach((s, p) => s.classList.toggle('active', p === index));
    const stepLabel = document.querySelector('#new .flow-top .step'); if (stepLabel) stepLabel.textContent = `Paso ${index + 1} de ${NEW_STEPS_TOTAL} · Candidatura nueva`;
    if (steps[index].lugar) mapaDeptoNuevo();
  }
  function advanceNewWizard(index) {
    if (index === 2 && !electionSelect.value) { $('newCorporationPicker').classList.add('shake'); setTimeout(() => $('newCorporationPicker').classList.remove('shake'), 500); return; }
    if (steps[index].redes && !redesRespondidas()) return;
    const required = steps[index].fields.flatMap(f => f ? [...f.querySelectorAll('input,select')] : []).filter(input => input.required && !input.closest('.hidden'));
    const invalid = required.find(input => !input.checkValidity()); if (invalid) { invalid.reportValidity(); return; }
    /* Sin partido, el espectro no es opcional: es con lo que se calcula todo. */
    if (steps[index].fields.includes(fields.partyEspectro) && $('partyMode').value === 'indeciso' && !espectroNuevoVigente()) { $('espectroNuevo').classList.add('shake'); setTimeout(() => $('espectroNuevo').classList.remove('shake'), 500); return; }
    showNewWizardStep(index + 1);
  }
  window.showNewWizardStep = showNewWizardStep;
}
/* Estado de la candidatura nueva (se guarda en el vínculo). */
let NUEVO = null;
async function createNew(e) {
  e.preventDefault();
  if (!SESSION.acceso) return abrirPaywall();
  const dep = $('department'), depNombre = dep.options[dep.selectedIndex]?.text || '';
  const modo = $('partyMode').value, indeciso = modo === 'indeciso';
  if (indeciso && !espectroNuevoVigente()) { window.showNewWizardStep?.(4); return; }
  const nuevo = { nombre: $('newName').value.trim(), publico: $('publicFigure').checked, nombrePublico: $('publicName').value.trim(), partido: indeciso ? '' : modo === 'new' ? $('partyName').value.trim() : $('party').value, partidoNuevo: modo === 'new', objetivo: $('goal').value, tieneRedes: TIENE_REDES, redesUsa: redesElegidas() };
  /* El partido va también en la campaña: es lo que /c360/campana sabe guardar
     cuando quien no se había decidido lo define desde el CRM. */
  const campana = { corp: $('election').value, ruta: 'other', avales: indeciso ? 'indeciso' : 'partido', espectro: indeciso ? espectroNuevoVigente() : '', partido: nuevo.partido, departamento: dep.value, departamentoNombre: depNombre, municipio: MUNICIPAL_ELECTIONS.includes($('election').value) ? $('municipality').value : '', localidad: $('election').value === 'jal' ? $('locality').value : '' };
  if (!nuevo.nombre || !campana.corp || !campana.departamento) return;
  if (PRUEBAS) vinculoLocal({ tipo: 'nuevo', nuevo, campana });
  else if (SESSION.vinculo) guardarCampana(campana);   /* quien vuelve a definir el partido */
  else {
    const sigue = await confirmarVinculo(nuevo.nombre, `${CRM_CORPORATIONS[campana.corp]} · ${[campana.localidad, campana.municipio, depNombre].filter(Boolean).join(' · ')}`);
    if (!sigue) return;
    const r = await guardarVinculo({ tipo: 'nuevo', nuevo, campana });
    if (!r.ok) { if (r.existente) { alert(`Su cuenta ya está vinculada a ${vinculoDescripcion()}. Para cambiarla escriba a ${SESSION.soporte}.`); return abrirVinculo(); } if (r.sinAcceso) return abrirPaywall(); alert(`No se pudo guardar la candidatura: ${r.error}`); return; }
  }
  NUEVO = { ...nuevo, campana };
  /* El vínculo solo guarda lo que su normalizador conoce: las redes que
     declaró van como preferencias de la escucha (/c360/escucha), que es donde
     después se piden los usuarios. `medios` va vacío a propósito: esa pregunta
     la hace el panel de escucha, y con él vacío el panel la sigue haciendo. */
  if (nuevo.redesUsa.length) {
    const preferencias = { redes: nuevo.redesUsa, medios: [] };
    if (SESSION.vinculo?.local) { SESSION.vinculo.escucha = Object.assign({}, SESSION.vinculo.escucha || {}, { preferencias }); persistirVinculoLocal(); }
    else if (SESSION.vinculo) {
      const r = await apiC360('/c360/escucha', { method: 'POST', body: JSON.stringify({ preferencias }) }).catch(() => null);
      if (r?.ok && r.data?.vinculo) SESSION.vinculo = r.data.vinculo;
    }
  }
  abrirCRMNuevo();
}

/* ─── 7 ter. El punto de partida, dicho como se dice ────────────────────────
   «Partimos de JAL · TEUSAQUILLO · BOGOTÁ D.C. · 2015 y PARTIDO CAMBIO
   RADICAL» es un registro de base de datos leído en voz alta. La tarjeta que
   abre el CRM es el primer saludo de la herramienta y tiene que sonar a
   alguien que miró el historial: cuánto hace, a qué se lanzó, a dónde va
   ahora y con quién. Es un banco de frases, no una plantilla: la corporación
   de destino y el bloque ideológico del partido eligen cada tramo. La frase
   se elige por el nombre —no al azar— para que no cambie en cada recarga.   */
/* La Registraduría escribe los lugares en mayúscula sostenida ("MEDELLÍN",
   "BOGOTÁ, D.C.", "COMUNA 11 LAURELES") y los departamentos llegan en tipo
   oración: en la misma línea quedaba «Concejo · MEDELLÍN · Antioquia», con la
   mitad gritando. Esto es SOLO cómo se muestra: lo que se guarda y lo que se
   compara sigue siendo el nombre original, que es la llave contra la Divipola. */
const NOMBRE_BONITO = s => String(s || '').trim().replace(/\s+/g, ' ').toLowerCase().replace(/(^|[\s(\-·])([a-záéíóúñü])/g, (m, a, b) => a + b.toUpperCase())
  .replace(/\b(De|Del|La|Las|Los|Y|E|El)\b/g, w => w.toLowerCase()).replace(/^(\w)/, c => c.toUpperCase())
  /* Tras «·», «:» o «,» empieza otro nombre: «UCG 12 · El Socorro» y
     «Bayunca, La Boquilla», no «· el Socorro» ni «, la Boquilla». */
  .replace(/([·:,]\s*)([a-záéíóúñü])/g, (m, a, b) => a + b.toUpperCase())
  /* Las siglas con punto se quedan como son: los puestos de votación se llaman
     "I.E. SAN JOSÉ" y "E.S.E. HOSPITAL", y «I.e.» no es un nombre. */
  .replace(/\b(?:[a-záéíóúñüA-ZÁÉÍÓÚÑÜ]\.){2,}/g, sigla => sigla.toUpperCase())
  /* Y la sigla entre comillas también: los partidos se llaman «MOVIMIENTO
     ALTERNATIVO INDÍGENA Y SOCIAL "MAIS"», y «"mais"» no es nadie. */
  .replace(/"([a-záéíóúñü]{2,6})"/g, (m, w) => `"${w.toUpperCase()}"`)
  /* Siglas SIN punto que el producto usa como nombre propio: la unidad de
     Cartagena se llama UCG y «Ucg 5» no es nada. Van una a una a propósito:
     una regla de «tres letras en mayúscula es sigla» dejaría USME y BOSA
     gritando. */
  .replace(/\b(Ucg|Jal)\b/g, w => w.toUpperCase());
/* «CONCEJO · MEDELLIN · 2019» → { tipo: 'concejo', lugar: 'Medellín', año: 2019 } */
function leerCorpHistorica(corp) {
  const partes = String(corp || '').split('·').map(x => x.trim()).filter(Boolean);
  const año = candidateYear({ corp }), t = normalizedText(partes[0] || '');
  const tipo = t.includes('JAL') ? 'jal' : t.includes('CONCEJO') ? 'concejo' : t.includes('ALCALD') ? 'alcaldia' : t.includes('ASAMBLEA') ? 'asamblea' : t.includes('GOBERN') ? 'gobernacion'
    : t.includes('CAMARA') ? 'camara' : t.includes('SENADO') ? 'senado' : t.includes('PRESID') || t.includes('CONSULTA') ? 'presidencial' : 'otra';
  const lugar = NOMBRE_BONITO(partes.slice(1).find(x => !/^\d{4}$/.test(x)) || '');
  return { tipo, lugar, año };
}
const CORP_CON_LUGAR = {
  jal: l => `la JAL de ${l}`, concejo: l => `el Concejo de ${l}`, alcaldia: l => `la Alcaldía de ${l}`,
  asamblea: l => `la Asamblea de ${l}`, gobernacion: l => `la Gobernación de ${l}`,
  camara: l => `la Cámara por ${l}`, senado: () => 'el Senado', presidencial: () => 'la consulta presidencial', otra: l => l || 'una elección',
};
/* «a el Concejo» no existe: en español es «al Concejo». */
function aEl(frase) { return String(frase || '').replace(/^el\s/, ''); }
function aCorp(tipo, lugar) { const n = nombreDeCorp(tipo, lugar); return n.startsWith('el ') ? `al ${aEl(n)}` : `a ${n}`; }
/* Ni «Bogotá, D.C..»: si el nombre ya termina en punto, no se le pone otro. */
function punto(frase) { return /\.$/.test(frase) ? frase : frase + '.'; }
function nombreDeCorp(tipo, lugar) { const f = CORP_CON_LUGAR[tipo] || CORP_CON_LUGAR.otra; return lugar ? f(lugar) : (tipo === 'senado' || tipo === 'presidencial' ? f() : { jal: 'la JAL', concejo: 'el Concejo', alcaldia: 'la Alcaldía', asamblea: 'la Asamblea', gobernacion: 'la Gobernación', camara: 'la Cámara' }[tipo] || 'una elección'); }
function haceCuanto(año) {
  const n = 2027 - Number(año || 0);
  if (!año || n <= 0) return '';
  return n === 1 ? 'el año pasado' : `hace ${n} años`;
}
/* Una frase por bloque, de varias posibles: la elige el nombre, no el azar. */
const FRASES_BLOQUE = {
  izq: [
    p => `Con ${p} la conversación es de derechos y de barrio: la meta vive donde la gente le pide más al Estado.`,
    p => `${p} gana en la calle y en la organización: cada puesto de votación es una reunión que ya debería estar agendada.`,
  ],
  ci: [
    p => `Con ${p} el voto es de cambio con cabeza: se gana explicando, y explicando bien.`,
    p => `${p} vive del votante que quiere que las cosas cambien sin que se rompan; ahí está su meta.`,
  ],
  c: [
    p => `El centro no se arrastra, se convence: con ${p} la meta se consigue puesto por puesto.`,
    p => `Con ${p} el reto es el de siempre en el centro: que el votante indeciso decida por usted.`,
  ],
  cd: [
    p => `Con ${p} el mensaje es gestión: obras, orden y resultados que se puedan mostrar.`,
    p => `${p} habla de que las cosas funcionen; la meta está donde la gente ya está cansada de que no.`,
  ],
  d: [
    p => `Con ${p} el mensaje es orden y resultados: la meta vive donde la gente pide autoridad que cumpla.`,
    p => `${p} convence con firmeza y con obra: los votos están donde el barrio quiere sentirse seguro.`,
  ],
  sc: [
    p => `Con ${p} el mensaje lo pone usted: no hay un bloque que lo defina de antemano, y eso también es una ventaja.`,
  ],
};
/* El salto se cuenta distinto si además CAMBIA DE TERRITORIO —una edil de
   Teusaquillo que se lanza al Concejo de Leticia no está dando el mismo paso
   que si se lanzara al de Bogotá— y si el destino es una ciudad grande o un
   municipio pequeño, donde «la ciudad entera» no significa nada. */
const FRASES_SALTO = {
  misma: c => c.mudanza
    ? `Y se muda: de ${c.lugarViejo} a ${c.lugarNuevo}. La corporación la conoce; el territorio es nuevo y su votación anterior no cuenta ahí.`
    : 'Repetir es la forma más barata de crecer: ya sabe dónde están sus votos y el mapa se los muestra.',
  'jal>concejo': c => c.esCiudad
    ? 'De la localidad a la ciudad entera: el salto es grande, y por eso la meta se reparte por donde vota su partido.'
    : `De una localidad a todo ${c.lugarNuevo}: es otra escala y otro censo, así que la meta sale de lo que costó una curul allá.`,
  'jal>alcaldia': c => c.esCiudad
    ? 'De la localidad a la ciudad entera, y de una curul al primer puesto: el mapa cambia de escala.'
    : `De una localidad a la Alcaldía de ${c.lugarNuevo}: ya no es sumar para una curul, es ganar.`,
  'concejo>alcaldia': () => 'Del Concejo a la Alcaldía se pasa de sumar a ganar: ya no es una curul, es el primer puesto.',
  'concejo>asamblea': () => 'Del municipio al departamento: la meta ya no vive en una ciudad sino en todas.',
  'concejo>gobernacion': () => 'Del Concejo a la Gobernación: de una curul en una ciudad al primer puesto del departamento.',
  'alcaldia>gobernacion': () => 'De la Alcaldía a la Gobernación: la misma pregunta —ganar— en un territorio mucho más grande.',
  'asamblea>gobernacion': () => 'De la Asamblea a la Gobernación: del voto por lista al voto por nombre.',
  'congreso>territorial': c => `Del Congreso al territorio: su votación de entonces está regada por todo el departamento y la meta ahora vive en ${c.lugarNuevo || 'un solo lugar'}`,
  'presidencial>territorial': () => 'De una campaña nacional a una local: los votos de entonces no son suyos, pero el músculo sí.',
  otra: c => c.mudanza
    ? `Cambia de corporación y de territorio: la meta se calcula contra la elección de 2023 de ESA corporación en ${c.lugarNuevo}`
    : 'Cambiar de corporación cambia la pregunta: la meta se calcula contra la elección de 2023 de ESA corporación en ese lugar.',
};
/* Por firmas NO hay partido del que hablar: la familia la eligió la persona en
   el espectro. Antes la frase agarraba el aval VIEJO —«con Alternativo Indígena
   y Social el mensaje lo pone usted»— y lo presentaba como si fuera el de esta
   campaña: exactamente lo contrario de lo que la persona acababa de responder.
   Acá se dice de dónde viene, que va sin aval, y qué significa la familia que
   eligió para lo único que cambia de verdad: recoger firmas antes de votos. */
const FAMILIA_CON_ARTICULO = { izq: 'la izquierda', ci: 'el centro-izquierda', c: 'el centro', cd: 'el centro-derecha', d: 'la derecha', sc: 'su familia política' };
const FRASES_FIRMAS = {
  izq: [f => `va por firmas y se ubica en ${f}: sin aval no hay maquinaria prestada, y las firmas salen más rápido donde esa familia ya tiene conversación.`,
        f => `va por firmas desde ${f}: la estructura la arma usted, así que el primer mapa no es el de los votos sino el de dónde recogerlas.`],
  ci: [f => `va por firmas desde ${f}: el aval no lo respalda nadie, pero tampoco lo amarra nadie, y eso en campaña se nota.`,
       f => `va por firmas y se ubica en ${f}: las firmas se recogen donde esa familia ya vota, que es donde menos hay que explicar.`],
  c: [f => `va por firmas desde ${f}: sin etiqueta que lo defina, el mensaje es suyo entero; el costo es que la estructura también.`,
      f => `va por firmas y se ubica en ${f}: el centro no tiene una base cautiva, así que la recolección manda más que nunca.`],
  cd: [f => `va por firmas desde ${f}: sin aval, pero con una familia que en este territorio ya tiene dónde apoyarse.`,
       f => `va por firmas y se ubica en ${f}: las firmas se buscan donde esa familia votó en 2023, que es el trabajo menos costoso.`],
  d: [f => `va por firmas desde ${f}: nadie le pone el mensaje, y la recolección se apoya en donde esa familia ya es fuerte.`,
      f => `va por firmas y se ubica en ${f}: sin aval la campaña empieza antes —primero las firmas, después los votos—.`],
  sc: [() => 'va por firmas: sin aval de partido, la recolección es la primera campaña y por eso tiene su propia tarjeta.'],
};
function tipoDeSalto(desde, hacia) {
  if (desde === hacia) return 'misma';
  if (desde === 'camara' || desde === 'senado') return 'congreso>territorial';
  if (desde === 'presidencial') return 'presidencial>territorial';
  return FRASES_SALTO[`${desde}>${hacia}`] ? `${desde}>${hacia}` : 'otra';
}
function elegir(lista, semilla) { let h = 0; for (const c of String(semilla || '')) h = (h * 31 + c.charCodeAt(0)) >>> 0; return lista[h % lista.length]; }
/* Dónde compite la candidatura, para el diccionario regional
   (candidato-360-frases.js): el territorio de la campaña si lo eligió, y si
   no («la misma corporación»), el de su última elección. */
function regionDeCampana(candidate, campana) {
  const dep = campana?.departamento || departamentoDeCandidatura(candidate);
  const partes = String(candidate?.circunscripcion || '').split('·').map(x => x.trim()).filter(Boolean);
  const municipio = campana?.municipio || (CORP_MUNICIPAL.includes(campana?.corp || '') || campana?.corp === 'jal' || !campana?.corp ? partes[partes.length - 1] : '') || '';
  return { dep, municipio };
}
/* La frase medida (cifras de 2023) llega después: necesita bajar un JSON. Se
   agrega al párrafo solo si sigue siendo la misma candidatura en pantalla. */
async function agregarDatoRegional(el, { dep, municipio, bloque, partido, corp }) {
  const F = window.C360Frases; if (!el || !F) return;
  const antes = el.textContent;
  let codigoMunicipio = '';
  try { if (municipio && dep && dep !== '16') codigoMunicipio = await C360Electorado.codigoMunicipio(dep, municipio); } catch {}
  const d = await F.dato({ dep, municipio, codigoMunicipio, bloque, partido, corp }).catch(() => '');
  if (d && el.textContent === antes) el.textContent = `${antes} ${d}`;
}
function fraseDePartida({ candidate, corpKey, territory, campana }) {
  const hist = leerCorpHistorica(candidate?.corp), n = candidate?.history?.length || 0;
  const lugarNuevo = NOMBRE_BONITO(String(territory || '').split('·')[0].trim()) || hist.lugar;
  const destino = nombreDeCorp(corpKey, lugarNuevo);
  const cuando = haceCuanto(hist.año);
  const apertura = n >= 2
    ? punto(`¡${n} candidaturas en el historial (${[...new Set(candidate.history.map(candidateYear).filter(Boolean))].sort((a, b) => a - b).join(', ')})! La última fue ${aCorp(hist.tipo, hist.lugar)}${cuando ? ` ${cuando}` : ''}`)
    : `¡Vimos que se lanzó ${aCorp(hist.tipo, hist.lugar)}${cuando ? ` ${cuando}` : ''}!`;
  const ahora = punto(`Ahora vamos por ${destino}`);
  /* ¿Se muda? El territorio de la campaña contra el de su última elección. */
  const mudanza = Boolean(lugarNuevo) && Boolean(hist.lugar) && normalizedText(lugarNuevo) !== normalizedText(hist.lugar);
  const porFirmas = campana?.avales === 'firmas', indeciso = campana?.avales === 'indeciso';
  const bonito = nombre => String(nombre || '').replace(/^(PARTIDO|MOVIMIENTO)\s+(POLÍTICO\s+)?/i, '').split(' ').map(w => w.length > 3 ? NOMBRE_BONITO(w) : w.toLowerCase()).join(' ').replace(/^(\w)/, c => c.toUpperCase());
  const partido = porFirmas || indeciso ? '' : String(campana?.partido || candidate?.partido || '').trim();
  const bloque = partido ? PartidosBloques.bloqueDeCandidatura(partido, candidate?.nombre || '') : 'sc';
  const partidoBonito = bonito(partido);
  const cambioDePartido = partido && candidate?.partido && normalizedText(partido) !== normalizedText(candidate.partido);
  const avalNuevo = !cambioDePartido ? ''
    : mudanza ? ' Es un aval nuevo, y en territorio nuevo: la huella que cuenta es la de ese partido allá.'
    : ' Es un aval nuevo: el mapa conserva su votación, la huella del partido cambia.';
  const reg = regionDeCampana(candidate, campana);
  /* Con partido: primero cómo se ubica ESE partido (si está en el
     diccionario), si no, la frase de su familia. */
  const identidad = partido ? window.C360Frases?.partido(partido) : '';
  let conQuien = partido ? (identidad ? punto(identidad.charAt(0).toUpperCase() + identidad.slice(1)) : elegir(FRASES_BLOQUE[bloque] || FRASES_BLOQUE.sc, candidate?.nombre)(partidoBonito)) + avalNuevo : '';
  if (porFirmas) {
    const espectro = campana?.espectro || 'sc';
    const familia = FAMILIA_CON_ARTICULO[espectro] || FAMILIA_CON_ARTICULO.sc;
    const viene = candidate?.partido ? `Viene de ${bonito(candidate.partido)}, pero esta vez ` : '';
    const frase = viene + elegir(FRASES_FIRMAS[espectro] || FRASES_FIRMAS.sc, candidate?.nombre)(familia);
    conQuien = punto(frase.charAt(0).toUpperCase() + frase.slice(1));
  }
  if (indeciso) {
    const espectro = campana?.espectro || 'sc';
    const familia = FAMILIA_CON_ARTICULO[espectro] || FAMILIA_CON_ARTICULO.sc;
    const viene = candidate?.partido ? `Viene de ${bonito(candidate.partido)} y ` : '';
    conQuien = punto(`${viene ? viene + 'todavía' : 'Todavía'} no tiene partido: se lanza desde ${familia}, y con esa familia se calcula todo mientras lo define. Cuando lo tenga, se pone en el CRM y el mapa cambia a la huella de ese partido`);
  }
  const contexto = { lugarViejo: hist.lugar, lugarNuevo, mudanza, esCiudad: Boolean(cityLayerFor(lugarNuevo)) };
  const salto = punto(FRASES_SALTO[tipoDeSalto(hist.tipo, corpKey)](contexto));
  /* Y lo que significa esa familia EN ESTE territorio: la lectura regional. */
  const familiaRegion = partido ? bloque : (campana?.espectro || '');
  const regional = window.C360Frases?.linea({ ...reg, bloque: familiaRegion }) || '';
  return [apertura, ahora, salto, conQuien, regional].filter(Boolean).join(' ');
}

/* ─── 8. CRM: apertura, meta de votos y foto ─────────────────────────────── */
/* La meta depende del PARTIDO: no cuesta lo mismo entrar de décimo en una
   lista grande que arrastrar una lista pequeña. Va el aval con el que se
   lanza y el departamento (para estimar con la Cámara 2026 a quien no corrió
   en 2023). */
async function estimateVoteTarget(corp, territory) {
  const departamento = CAMPANA_ACTUAL?.departamento || departamentoDeCandidatura(crmCandidate);
  /* Con territorio elegido en el formulario va también su CÓDIGO: el nombre
     del DANE no siempre casa con el de la Registraduría (vote-target.js). */
  const codigo = territory ? { dep: $('campaignDepartment')?.value || departamento, mun: codigoMunicipioObjetivo() } : null;
  return VoteTarget.estimate({ corp, territory: territory || crmCandidate?.circunscripcion || '', baseUrl: S3, partido: partidoVigente(), departamento, bloque: bloqueVigente(), codigo });
}
let META_ACTUAL = null;
/* Cuatro escenarios sobre la MISMA proyección (censo × participación), de
   menor a mayor esfuerzo, para que el candidato vea la escala sin creer que la
   meta es un número exacto. Antes eran tres y el último saltaba ×3 (en el
   Concejo de Bogotá, de 17.600 a 52.700): entre la lista típica y la cifra
   repartidora no había nada, aunque en 2023 hubo ocho listas con costos
   escalonados de 9 a 24 mil votos. El peldaño que faltaba sale de ahí.
   · inminente (rojo)     → la votación más baja que puede sacar: la mitad del
                            probable (decisión de Ricardo, sep-2026).
   · probable  (amarillo) → un trabajo normal: lo que costó entrar por su lista
                            en 2023, o por una lista típica, más el margen.
   · posible   (verde)    → una buena votación: lo que costó entrar por la
                            SIGUIENTE lista más exigente de 2023 (el primer
                            último-elegido que supera en 25 % al probable).
                            Dato observado y dependiente del partido. Si
                            ninguna lista lo supera, el punto medio en
                            proporción entre probable y deseado.
   · deseado   (violeta)  → lo más alto: la cifra repartidora con el margen.
                            Con esos votos PROPIOS la lista gana una curul
                            aunque nadie más sume, y quien los pone va de
                            primero. Sin reparto (uninominal o fuente
                            incompleta), un 15 % sobre la referencia. */
const META_ESCENARIOS = [
  { id: 'inminente', label: 'Inminente', color: '#e0533f' },
  { id: 'probable',  label: 'Probable',  color: '#f2c14e' },
  { id: 'posible',   label: 'Posible',   color: '#4ade80' },
  { id: 'deseado',   label: 'Deseado',   color: '#a78bfa' },
];
const META_MARGEN_DESEADO = 0.15;
const META_SALTO_POSIBLE = 1.25;    /* el posible arranca un 25 % sobre el probable */
let META_ESCENARIO = (() => { try { return localStorage.getItem('c360-meta-escenario') || 'probable'; } catch { return 'probable'; } })();
if (!META_ESCENARIOS.some(e => e.id === META_ESCENARIO)) META_ESCENARIO = 'probable';
/* Mismo redondeo de VoteTarget: hacia arriba, al paso que corresponde. */
function redondearMeta(v) { const paso = v < 10000 ? 10 : v < 100000 ? 100 : 1000; return Math.ceil(v / paso) * paso; }
function escenariosDe(d) {
  if (!d || d.falla || !d.objetivo) return null;
  const f = (d.censo?.factor || 1) * (d.participacion?.factor || 1), R = d.referencia || {}, rep = d.reparto;
  const probable = d.objetivo, margen = 1 + (d.margen || 0);
  const inminente = redondearMeta(probable * 0.5);
  /* Deseado: la cifra repartidora; sin reparto, la referencia con más margen. */
  let deseado = rep && rep.cifra > 0 ? redondearMeta(rep.cifra * f * margen) : 0;
  const conCifra = deseado > probable;
  if (!conCifra) deseado = redondearMeta((R.votos || probable) * f * (1 + META_MARGEN_DESEADO));
  if (deseado < probable) deseado = probable;
  /* Posible: la siguiente lista más exigente de 2023, ya traída a 2027. */
  const piso = probable * META_SALTO_POSIBLE;
  const siguiente = (rep?.listas || [])
    .map(l => ({ ...l, proyectado: redondearMeta(l.votos * f * margen) }))
    .filter(l => l.proyectado >= piso && l.proyectado < deseado)
    .sort((a, b) => a.proyectado - b.proyectado)[0];
  const posible = siguiente ? siguiente.proyectado
    : Math.max(probable, Math.min(deseado, redondearMeta(Math.sqrt(probable * deseado))));
  return {
    inminente: { votos: inminente, base: probable, tipo: 'mitad' },
    probable:  { votos: probable,  base: R.votos, tipo: 'medicion' },
    posible:   siguiente ? { votos: posible, base: siguiente.votos, tipo: 'lista', partido: siguiente.partido, k: siguiente.k }
                         : { votos: posible, base: null, tipo: 'intermedio' },
    deseado:   { votos: deseado,   base: conCifra ? rep.cifra : R.votos, tipo: conCifra ? 'cifra' : 'margen' },
  };
}
/* El mensaje de la tarjeta: motivación con los pies en 2023, no la fórmula
   (la fórmula vive en la ⓘ). Cambia con el escenario elegido. */
function mensajeMeta(esc, d) {
  const lugar = d?.territorio ? ` en ${NOMBRE_BONITO(d.territorio)}` : '';
  const corp = d?.corporacion ? corpConArticulo(d.corporacionClave, d.corporacion, 0) : 'a la corporación';
  if (esc === 'inminente') return `La votación más baja que puede sacar con una campaña seria: la mitad de la probable. Es el piso de su trabajo, no la meta. Por debajo de esto, algo no está funcionando.`;
  if (d?.uninominal) {
    return esc === 'posible' ? `Una buena votación: ganar${lugar} con aire, sin depender de cómo se reparta el resto. Es la cifra para la que se construye un equipo fuerte.`
      : esc === 'deseado' ? `Lo más alto que tiene sentido buscar${lugar}: una victoria que nadie discute. Con esto no hay noche larga.`
      : `Nuestra medición hoy: lo que sacó quien ganó${lugar} en 2023, puesto en 2027 con un margen encima. Cada uno de esos votos ya existió; con un trabajo normal, la campaña es ir a buscarlos otra vez.`;
  }
  const suya = d?.referencia?.tipo === 'partido' ? 'la suya' : 'una lista típica';
  return esc === 'posible' ? `Una buena votación: con esto entraba ${corp}${lugar} hasta por una lista más exigente que ${suya} en 2023. Ya no depende de que su lista le alcance justo.`
    : esc === 'deseado' ? `Con estos votos propios la curul es suya sin depender de la lista: usted la arrastra. Es lo que consigue un gran trabajo, y es lo que separa a quien entra de quien manda en la lista.`
    : `Nuestra medición hoy: lo que costó entrar ${corp}${lugar} en 2023, traído a 2027. Todos esos votos ya se dieron una vez; con un trabajo normal, la campaña es demostrar que esta vez son para usted.`;
}
function pintarMeta(estimate) {
  setTimeout(() => { if (ENDOSO.aliados.length) pintarEndoso(); }, 0);
  META_ACTUAL = estimate || null;
  const esc = escenariosDe(estimate?.detalle);
  if (estimate.target) { pintarEscenario(); }
  else { $('crmVoteNumber').textContent = '—'; $('crmVoteTarget').textContent = 'Meta pendiente de referencia territorial'; $('crmVoteFormula').textContent = estimate.formula; }
  /* Con la meta ya en mano, la tarjeta de firmas puede compararse con ella.
     (Este refresco estuvo colgado del if de arriba como su else: sin firmas,
     la meta se pintaba y acto seguido se borraba con «—», y el mapa
     proyectado caía al reparto del historial.) */
  if (FIRMAS_ACTUAL && $('crmFirmasCopy')) $('crmFirmasCopy').textContent = textoFirmas(FIRMAS_ACTUAL);
  /* Los escenarios solo tienen sentido con una meta que explicar. */
  $('crmMetaEscenarios')?.classList.toggle('hidden', !esc);
  /* La ⓘ solo aparece cuando hay una meta que explicar: junto a un guion no
     explica nada, y el propio panel ya dice que falta la referencia. */
  document.querySelectorAll('.meta-i').forEach(b => b.classList.toggle('hidden', !(estimate.target && estimate.detalle)));
}
/* Pinta el escenario vigente sobre META_ACTUAL: número, título, mensaje y
   toggles. Es lo que se repite al cambiar de escenario sin recalcular nada. */
function pintarEscenario() {
  const e = META_ACTUAL; if (!e?.target) return;
  const esc = escenariosDe(e.detalle), cur = esc?.[META_ESCENARIO];
  const votos = cur ? cur.votos : e.target;
  /* Los cuatro escalones quedan en el navegador para el panel 08, que así no
     tiene que recalcular la meta (el servidor guarda solo la cifra elegida). */
  if (esc && window.C360Endoso) E360.guardarEscalones(E360.claveMeta(SESSION.user?.email, endosoCand()), esc, META_ESCENARIO);
  $('crmVoteNumber').textContent = votos.toLocaleString('es-CO');
  $('crmVoteTarget').textContent = `Meta ${META_ESCENARIO === 'probable' ? 'inicial' : META_ESCENARIO}: ${votos.toLocaleString('es-CO')} votos`;
  $('crmVoteFormula').textContent = esc ? mensajeMeta(META_ESCENARIO, e.detalle) : e.formula;
  const rotulo = document.querySelector('.crm-vote-target .metric small');
  if (rotulo) rotulo.textContent = META_ESCENARIO === 'probable' ? 'votos objetivo inicial' : `votos · escenario ${META_ESCENARIO}`;
  const caja = $('crmMetaEscenarios');
  if (caja) {
    if (!caja.dataset.listo) {
      caja.dataset.listo = '1';
      caja.innerHTML = META_ESCENARIOS.map(x => `<button type="button" class="meta-esc" role="radio" aria-checked="false" data-esc="${x.id}" style="--esc:${x.color}" onclick="elegirEscenario('${x.id}')"><i></i>${x.label}<b></b></button>`).join('');
    }
    caja.querySelectorAll('.meta-esc').forEach(b => {
      b.setAttribute('aria-checked', String(b.dataset.esc === META_ESCENARIO));
      b.querySelector('b').textContent = esc ? esc[b.dataset.esc].votos.toLocaleString('es-CO') : '';
    });
  }
  guardarMeta(votos);
}
function elegirEscenario(id) {
  if (!META_ESCENARIOS.some(e => e.id === id) || id === META_ESCENARIO) return;
  META_ESCENARIO = id;
  try { localStorage.setItem('c360-meta-escenario', id); } catch {}
  pintarEscenario();
  if (ENDOSO.aliados.length) pintarEndoso();   /* el % de la meta de la tarjeta 08 es del escenario elegido */
  if (FIRMAS_ACTUAL && $('crmFirmasCopy')) $('crmFirmasCopy').textContent = textoFirmas(FIRMAS_ACTUAL);
  /* El mapa proyectado reparte lo que diga el número: hay que repintarlo. */
  if (crmMapMode === 'proyectado' && typeof refreshCRMMapMode === 'function') refreshCRMMapMode();
}
/* Cómo se reparte la meta sobre el mapa, en una frase. Es la otra mitad de la
   pregunta «por qué proyectan esa votación»: de dónde sale el número y por qué
   cae donde cae. */
function comoSeReparte() {
  if (SALTO_ACTUAL?.base) return notaSalto(SALTO_ACTUAL.base);
  if (!crmCandidate) return 'Sin historial propio, el mapa reparte la meta según la votación de 2023 en el territorio al que aspira.';
  return 'Como sigue en la misma corporación, el mapa reparte la meta en la misma proporción en que ya votaron por usted: donde sacó el 20 % de sus votos le corresponde el 20 % de la meta.';
}
/* «entrar a la Concejo» no lo dice nadie. El artículo va por corporación. */
const CORP_ARTICULO = { jal: ['la', 'de la'], concejo: ['el', 'del'], alcaldia: ['la', 'de la'], asamblea: ['la', 'de la'], gobernacion: ['la', 'de la'] };
function corpConArticulo(clave, etiqueta, forma = 0) {
  const art = (CORP_ARTICULO[clave] || ['la', 'de la'])[forma];
  return `${forma === 0 ? (art === 'el' ? 'al' : 'a la') : art} ${etiqueta}`;
}
function mostrarMetaInfo() {
  const e = META_ACTUAL; if (!e) return;
  const d = e.detalle;
  $('introModalKicker').textContent = 'Candidato 360 · meta de votos';
  if (!d || d.falla) {
    $('introModalTitle').textContent = 'Todavía no hay meta para este territorio';
    $('introModalText').innerHTML = `<p>${escHtml(e.formula)}</p>
      <p class="puntaje-nota">La meta se calcula contra la elección de 2023 de <b>esa</b> corporación en <b>ese</b> lugar. Cuando la referencia no está completa preferimos no mostrar un número: una meta inventada es peor que ninguna.</p>`;
    return $('introModal').classList.add('open');
  }
  const pct = x => `${(x * 100).toFixed(1).replace('.', ',')} %`;
  const veces = x => `× ${x.toLocaleString('es-CO', { minimumFractionDigits: 3, maximumFractionDigits: 3 })}`;
  const R = d.referencia || {}, P = d.partido;
  const fmt = n => Number(n || 0).toLocaleString('es-CO');
  /* Con partido, el punto de partida es la LISTA; la última curul de la
     corporación queda como el piso, para que se vea la diferencia. */
  const porPartido = R.tipo !== 'partido' || !P ? '' : P.tipo === 'lista-con-curul'
    ? `<li><b>${fmt(P.votos)}</b> · entrar de <b>${P.k}</b> en la lista de ${escHtml(P.lista.nombre)}: en 2023 ganó ${P.k} curul${P.k === 1 ? '' : 'es'} con ${fmt(P.lista.total)} votos, y su ${P.k === 1 ? 'único' : `${P.k}.º`} elegido${P.lista.ultimoNombre ? ` (${escHtml(P.lista.ultimoNombre)})` : ''} sacó ${fmt(P.votos)}. ${P.k >= 3 ? 'En una lista grande la entrada no depende de arrastrarla: depende de quedar entre los primeros.' : 'En una lista corta hay que estar arriba.'}</li>`
    : P.tipo === 'lista-cerrada'
      ? `<li><b>${fmt(P.votos)}</b> · la lista de ${escHtml(P.lista.nombre)} fue <b>cerrada</b>: sin voto preferente, nadie entró con votos propios. Ganó ${P.k} curul${P.k === 1 ? '' : 'es'} con ${fmt(P.lista.total)} votos, a ${fmt(P.porCurul)} por curul. Ahí no se compite por votos personales sino por el <b>renglón</b>, así que como meta ponemos lo que cuesta entrar por una lista abierta típica.</li>`
    : P.tipo === 'lista-sin-curul'
      ? `<li><b>${fmt(P.votos)}</b> · <b>jalar la lista</b> de ${escHtml(P.lista.nombre)}: en 2023 sumó ${fmt(P.lista.total)} y la cifra repartidora fue ${fmt(P.cifra)}, le faltaron ${fmt(P.faltanLista)}. Si el resto de la lista repite, a quien la encabece le toca poner ${fmt(P.votos)}.</li>`
      : `<li><b>${fmt(P.votos)}</b> · ${escHtml(P.nombre)} no tuvo lista en esta corporación en 2023. Su fuerza se estima con la <b>Cámara de 2026</b>: ${fmt(P.camara.votos)} votos en el departamento, que al tamaño de esta corporación son ${fmt(P.camara.totalEstimado)}. ${P.k ? `Con eso arrastraría ${P.k} curul${P.k === 1 ? '' : 'es'} y entrar de ${P.k} cuesta lo que suele sacar el ${P.k}.º de una lista así.` : `No alcanza la cifra repartidora (${fmt(P.cifra)}): a quien encabece le toca poner la diferencia.`}</li>`;
  const piso = R.tipo === 'partido' ? `<li><b>${fmt(R.piso)}</b> · el <b>piso de la corporación</b>: la última curul ${escHtml(corpConArticulo(d.corporacionClave, d.corporacion, 1))} de ${escHtml(d.territorio)} en 2023${R.curules ? `, con ${R.curules} curules` : ''}. Es lo mínimo con que alguien entró, no lo que cuesta entrar por su lista.</li>` : '';
  const sinPartido = P && P.tipo === 'sin-dato' ? `<p class="puntaje-nota">De ${escHtml(P.nombre)} no hay lista en esta corporación en 2023 ni votación a Cámara en 2026 en este departamento, así que la meta es la de la corporación. Si es una organización nueva, tómela como piso.</p>` : '';
  /* Sin partido, el piso de la corporación engaña: casi siempre lo paga el
     último de la lista más grande, que entró de arrastre. La referencia es lo
     que costó entrar por una lista típica (o por una de su familia). */
  const tipicaLi = (R.tipo === 'mediana-listas' || R.tipo === 'mediana-bloque' || R.tipo === 'cifra-repartidora')
    ? (R.tipo === 'cifra-repartidora'
        ? `<li><b>${fmt(R.votos)}</b> · la <b>cifra repartidora</b> de 2023: lo que le costó a una lista cada curul. Todas las curules fueron de listas cerradas, así que no hay voto personal con el que comparar.</li>`
        : `<li><b>${fmt(R.votos)}</b> · lo que costó entrar por una <b>lista ${R.tipo === 'mediana-bloque' ? 'de su familia política' : 'típica'}</b> ${escHtml(corpConArticulo(d.corporacionClave, d.corporacion, 1))} de ${escHtml(d.territorio)} en 2023: la mediana del último elegido de ${R.listas === 1 ? 'la única lista' : `las ${R.listas} listas`} ${R.tipo === 'mediana-bloque' ? 'de esa familia' : 'con curul'}.</li>`)
      + (R.piso ? `<li><b>${fmt(R.piso)}</b> · el <b>piso de la corporación</b>: la curul más barata de 2023${R.curules ? `, de ${R.curules}` : ''}. Casi siempre es el último de la lista más grande, que entró de arrastre: por eso no se usa como meta.</li>` : '')
    : '';
  const puntoDePartida = R.tipo === 'partido' ? porPartido + piso : tipicaLi || (R.tipo === 'ganadora'
    ? `<li><b>${R.votos.toLocaleString('es-CO')}</b> · lo que sacó <b>quien ganó</b> ${escHtml(corpConArticulo(d.corporacionClave, d.corporacion, 1))} de ${escHtml(d.territorio)} en 2023${R.nombre ? ` (${escHtml(R.nombre)})` : ''}. En un cargo uninominal la meta es ganar, no pasar un corte.</li>`
    : R.tipo === 'curul-verificada'
      ? `<li><b>${R.votos.toLocaleString('es-CO')}</b> · la <b>última curul</b> ${escHtml(corpConArticulo(d.corporacionClave, d.corporacion, 1))} de ${escHtml(d.territorio)} en 2023${R.curules ? `, de ${R.curules} curules` : ''}, tomada del acto de escrutinio.</li>`
      : R.tipo === 'piso-observado'
        ? `<li><b>${R.votos.toLocaleString('es-CO')}</b> · el <b>piso observado</b> entre quienes salieron elegidos en 2023${R.curules ? ` (${R.curules} curules)` : ''}. La fuente no permite reconstruir todas las curules, así que este número es un mínimo, no un corte exacto.</li>`
        : `<li><b>${R.votos.toLocaleString('es-CO')}</b> · el <b>corte de la última curul</b> ${escHtml(corpConArticulo(d.corporacionClave, d.corporacion, 1))} de ${escHtml(d.territorio)} en 2023${R.curules ? `, con ${R.curules} curules` : ''}, reconstruido con umbral y cifra repartidora.</li>`);
  /* Cómo se repartieron las curules: con cuántas se cuenta, cuál va al
     estatuto de oposición y si el voto de lista está contado. */
  const rep = d.reparto;
  const notaReparto = !rep ? '' : `<p class="puntaje-nota">En 2023 esta corporación tuvo ${rep.curules} curules${rep.oposicion ? `, de las cuales ${rep.porRepartidora} se repartieron por cifra repartidora (${fmt(rep.cifra)} votos por curul) y una fue para el segundo de la alcaldía o la gobernación, por el estatuto de oposición` : `, todas por cifra repartidora (${fmt(rep.cifra)} votos por curul)`}.${rep.cerradas && rep.cerradas.length ? ` ${rep.cerradas.map(c => `${escHtml(c.partido)} fue lista cerrada y ganó ${c.k} curul${c.k === 1 ? '' : 'es'}`).join('; ')}.` : ''}${rep.conListas ? ' El voto solo por la lista está contado.' : ''}${rep.curulesOficiales ? ' El número de curules es el oficial de la Registraduría, no una estimación.' : ''}</p>`;
  const ajustes = [
    `<li><b>${veces(d.censo.factor)}</b> · censo electoral: ${d.censo.potencial ? `${d.censo.potencial.toLocaleString('es-CO')} personas habilitadas en 2023 y ` : ''}un crecimiento de ${pct(d.censo.crecimiento)} hasta 2027.</li>`,
    d.participacion.p2023
      ? `<li><b>${veces(d.participacion.factor)}</b> · participación: votó el ${pct(d.participacion.p2023)} en 2023 y proyectamos ${pct(d.participacion.p2027)} en 2027 (las locales de mitad de periodo suben poco).</li>`
      : `<li><b>× 1,000</b> · participación: sin dato de censo y votantes para ese territorio la dejamos estable, sin inventar un alza.</li>`,
    `<li><b>${veces(1 + d.margen)}</b> · margen competitivo: ${Math.round(d.margen * 100)} % por encima del corte. Empatar con la última curul no la gana; hay que pasarla.</li>`
  ].join('');
  const esc = escenariosDe(d), cual = esc?.[META_ESCENARIO];
  const notaEsc = x => x.tipo === 'medicion' ? 'un trabajo normal. Nuestra medición: la referencia de 2023 con el margen competitivo'
    : x.tipo === 'mitad' ? 'la votación más baja con una campaña seria: la mitad del probable'
    : x.tipo === 'lista' ? `una buena votación. Lo que costó el último elegido de ${escHtml(x.partido)} en 2023 (${fmt(x.base)} votos, su curul ${x.k}), traído a 2027 con el margen: la siguiente lista más exigente por encima del probable`
    : x.tipo === 'intermedio' ? 'una buena votación. Ninguna lista de 2023 queda entre el probable y el deseado, así que va a medio camino, en proporción, entre los dos'
    : x.tipo === 'cifra' ? `un gran trabajo. La cifra repartidora de 2023 (${fmt(x.base)} votos por curul) puesta en 2027 con el margen: con esos votos propios su lista gana una curul aunque nadie más sume, y quien los pone va de primero`
    : `un gran trabajo. La referencia con un margen del ${Math.round(META_MARGEN_DESEADO * 100)} % en vez del 3 %: cubre que entren más listas o suba la cifra repartidora`;
  const escenariosHtml = !esc ? '' : `<p style="margin-bottom:8px"><b>Cuatro escenarios, una misma cuenta</b></p>
    <ul class="puntaje-escala meta-esc-lista">${META_ESCENARIOS.map(x => `<li${x.id === META_ESCENARIO ? ' class="vigente"' : ''}><b>${fmt(esc[x.id].votos)}</b> · <i class="meta-esc-dot" style="--esc:${x.color}"></i><b class="meta-esc-nombre">${x.label}</b>${x.id === META_ESCENARIO ? ' (el que está en la tarjeta)' : ''} · ${notaEsc(esc[x.id])}.</li>`).join('')}</ul>
    <p class="puntaje-nota">De menor a mayor esfuerzo: inminente es lo que ya casi pasa, probable lo que exige una campaña normal y posible lo que exige una grande. Los tres salen de la misma proyección de censo y participación; solo cambia el punto de partida. El escenario se escoge en la tarjeta y el mapa proyectado se reparte con el que esté elegido.</p>`;
  $('introModalTitle').textContent = `Su meta: ${(cual ? cual.votos : d.objetivo).toLocaleString('es-CO')} votos`;
  $('introModalText').innerHTML = `
    <p class="puntaje-nota" style="margin-top:0">${escHtml(e.formula)}</p>
    ${escenariosHtml}
    <p>No es un pronóstico de cuántos votos va a sacar. Es <b>cuántos hacen falta</b>: lo que costó entrar ${escHtml(corpConArticulo(d.corporacionClave, d.corporacion))} de ${escHtml(d.territorio)} en 2023${R.tipo === 'partido' ? ` <b>por la lista de ${escHtml(P.nombre)}</b>` : ''}, puesto en 2027.${R.tipo === 'partido' ? ' No cuesta lo mismo entrar de décimo en una lista grande que arrastrar una lista pequeña.' : ''}</p>
    ${sinPartido}
    <p style="margin-bottom:8px"><b>De dónde parte</b></p>
    <ul class="puntaje-escala">${puntoDePartida}</ul>
    ${notaReparto}
    <p style="margin-bottom:8px"><b>Qué le ajustamos</b></p>
    <ul class="puntaje-escala">${ajustes}</ul>
    <p>${d.referencia.votos.toLocaleString('es-CO')} × esos tres factores dan ${Math.round(d.crudo).toLocaleString('es-CO')}, que redondeamos hacia arriba a <b>${d.objetivo.toLocaleString('es-CO')}</b>. Redondear hacia abajo sería fijar una meta que no alcanza.</p>
    <p style="margin-bottom:8px"><b>Por qué cae donde cae en el mapa</b></p>
    <p>${escHtml(comoSeReparte())}</p>
    <p class="puntaje-nota">Es un punto de partida, no una promesa: 2027 puede traer más listas, otra composición del concejo o un censo distinto. Se recalcula cada vez que usted cambia de corporación o de territorio.</p>`;
  $('introModal').classList.add('open');
}
function vinculoCoincide(profile) {
  const v = SESSION.vinculo; if (!v || v.tipo !== 'historial') return false;
  const slugs = new Set(v.candidato?.slugs || []);
  const propios = (profile.history?.length ? profile.history : [profile]).map(c => c.slug).filter(Boolean);
  return propios.some(s => slugs.has(s)) || (v.candidato?.id && v.candidato.id === profile.id);
}
/* ─── Vitrina del CRM ────────────────────────────────────────────────────────
   Sin acceso, el CRM SÍ abre: mapa, historial por año, promedio, proyección y
   meta de votos. Es lo que convence. Lo que se cobra se ve pero no se usa: el
   detalle por barrio o puesto sale borroso con su candado, y los módulos
   (briefing, escucha, arquetipos, perfil, firmas) abren el paywall al tocar
   su botón. Nada se vincula ni se guarda en el worker: el vínculo —la única
   decisión irreversible— sigue pasando solo con el acceso activo. */
let CRM_VITRINA = false;
function pintarVitrina() {
  const crm = $('crm'); if (!crm) return;
  crm.classList.toggle('en-vitrina', CRM_VITRINA);
  let banda = $('crmVitrinaBanda');
  if (!CRM_VITRINA) { banda?.remove(); candadoDetalle(); return; }
  if (!banda) {
    banda = document.createElement('div'); banda.id = 'crmVitrinaBanda'; banda.className = 'c360-vitrina crm-vitrina-banda';
    crm.querySelector('.dash-head')?.after(banda);
  }
  banda.innerHTML = `<p><b>Vista previa.</b> Esto es lo que ve su campaña: el historial, la proyección y la meta. El detalle por barrio y los módulos se abren con el acceso activo, que deja su cuenta vinculada a <b>este candidato</b>.</p><button type="button" onclick="abrirPaywall()">Activar mi candidatura</button>`;
  candadoDetalle();
}
/* El detalle (barrios o puestos) existe cuando crmBarrioLayer está en el mapa.
   Se pinta igual —así se nota cuántos barrios hay y dónde— pero borroso y sin
   tooltips; el desglose de la derecha también. */
const VITRINA_MUESTRA = 3;
/* Los N con más votos, para dejarlos ver en la vitrina. */
function vitrinaTop(values, n = VITRINA_MUESTRA) {
  return new Set(Object.entries(values).filter(([, v]) => Number(v) > 0).sort((a, b) => Number(b[1]) - Number(a[1])).slice(0, n).map(([k]) => k));
}
function candadoDetalle() {
  const mapEl = $('crmMap'), desglose = $('crmBreakdown'); if (!mapEl || !crmLeafletMap) return;
  /* Dos cosas se tapan: el DETALLE (barrios o puestos, en cualquier modo) y la
     PROYECCIÓN del nivel de arriba (localidades, comunas o municipios en
     «Proyectado»). El historial en «Total» es dato público y se ve entero. */
  const detalle = Boolean(crmBarrioLayer && crmLeafletMap.hasLayer(crmBarrioLayer));
  const proyectado = !detalle && crmMapMode === 'proyectado' && Boolean(crmMapLayer && crmLeafletMap.hasLayer(crmMapLayer));
  const on = CRM_VITRINA && (detalle || proyectado), capa = detalle ? crmBarrioLayer : crmMapLayer;
  mapEl.classList.toggle('vitrina-lock', on); desglose?.classList.toggle('vitrina-lock', on);
  /* Los N con más votos salen del propio desglose, que ya viene ordenado de
     mayor a menor: así la regla es la misma para barrios, puestos, localidades
     y municipios. Se borra pieza por pieza, no la capa entera. */
  const items = [...(desglose?.querySelectorAll('.crm-breakdown-item') || [])];
  const top = new Set(items.slice(0, VITRINA_MUESTRA).map(b => b.dataset.areaKey));
  [crmMapLayer, crmBarrioLayer].forEach(c => c?.eachLayer(l => { if (l._contorno) return; const el = l.getElement?.(); if (el) el.classList.toggle('vitrina-blur', on && c === capa && !top.has(l._vitrinaCode)); }));
  items.forEach((b, i) => b.classList.toggle('vitrina-blur', on && i >= VITRINA_MUESTRA));
  let tapa = mapEl.querySelector(':scope > .vitrina-tapa');
  const ocultos = on ? capa.getLayers().filter(l => !l._contorno && !top.has(l._vitrinaCode)).length : 0;
  if (!on || ocultos <= 0) return tapa?.remove();
  if (!tapa) { tapa = document.createElement('div'); tapa.className = 'vitrina-tapa'; mapEl.append(tapa); }
  const esPuesto = detalle && crmBarrioLayer instanceof L.FeatureGroup && !(crmBarrioLayer instanceof L.GeoJSON);
  const unidad = detalle ? (esPuesto ? 'puesto de votación' : 'barrio') : (PROYECCION_DEPTAL || crmMapState?.geometriaDestino ? 'municipio' : (crmMapState?.config?.title || 'localidad'));
  const plural = { 'puesto de votación': 'puestos de votación', barrio: 'barrios', municipio: 'municipios', localidad: 'localidades', comuna: 'comunas' }[unidad] || unidad + 's';
  const que = ocultos === 1 ? unidad : plural;
  tapa.innerHTML = `<div class="c360-wall-card"><span class="kicker">🔒 ${detalle ? 'Detalle' : 'Meta proyectada'} por ${escHtml(unidad)}</span><p>Le mostramos ${top.size === 1 ? 'el' : 'los'} <b>${top.size}</b> con más ${detalle ? 'votos' : 'meta'}. ${ocultos === 1 ? 'Queda' : 'Quedan'} <b>${ocultos.toLocaleString('es-CO')} ${escHtml(que)}</b> más, con ${detalle ? 'su votación y la meta repartida' : 'la meta repartida'}, que se abren con un plan activo.</p><button type="button" onclick="abrirPaywall()">Ver los planes</button></div>`;
}
/* Cualquier botón o enlace de un módulo abre el paywall en vitrina. Captura,
   para ganarle a los onclick y a los href de cada tarjeta. La meta (02) y el
   enlace al método no son módulos cobrados: pasan. */
document.addEventListener('click', e => {
  if (!CRM_VITRINA) return;
  const el = e.target.closest('#crm .crm-grid .module:not(.crm-vote-target) :is(button, a, input)');
  if (!el || el.classList.contains('enlace-boton') || el.classList.contains('meta-i')) return;
  e.preventDefault(); e.stopPropagation();
  const modulo = el.closest('.module')?.querySelector('.panel-num')?.textContent.replace(/^\d+\s*·\s*/, '') || 'Este módulo';
  abrirPaywall(`${modulo} se abre con el acceso a Candidato 360.`);
}, true);

async function launchCRM(event) {
  event?.preventDefault();
  if (!crmCandidate) return;
  CRM_VITRINA = SESSION.listo && !SESSION.acceso;
  const isOther = document.querySelector('input[name="corporationRoute"]:checked')?.value === 'other';
  if (isOther && !$('otherCorporation').value) return irAPaso('corporacion', { animar: true });
  const corpKey = isOther ? $('otherCorporation').value : corporacionHistorica(crmCandidate) || 'concejo';
  const corporation = CRM_CORPORATIONS[corpKey], territory = campaignTerritory(corpKey);
  if (territory === null) { irAPaso('lugar', { animar: true }); $('campaignDepartment').focus({ preventScroll: true }); return; }
  const campana = campanaActual(corpKey);
  if (CRM_VITRINA) { /* vista previa: nada se guarda ni se vincula */ }
  else if (PRUEBAS) vinculoLocal({ tipo: 'historial', candidato: { id: crmCandidate.id, nombre: crmCandidate.nombre, slugs: (crmCandidate.history?.length ? crmCandidate.history : [crmCandidate]).map(c => c.slug).filter(Boolean), corp: crmCandidate.corp, partido: crmCandidate.partido, circunscripcion: crmCandidate.circunscripcion }, campana });
  else if (!SESSION.vinculo) {
    const sigue = await confirmarVinculo(crmCandidate.nombre, `${corporation}${territory ? ` · ${territory}` : ''}`);
    if (!sigue) return;
    const slugs = (crmCandidate.history?.length ? crmCandidate.history : [crmCandidate]).map(c => c.slug).filter(Boolean);
    const r = await guardarVinculo({ tipo: 'historial', candidato: { id: crmCandidate.id, nombre: crmCandidate.nombre, slugs, corp: crmCandidate.corp, partido: crmCandidate.partido, circunscripcion: crmCandidate.circunscripcion }, campana });
    if (!r.ok) { if (r.existente) { alert(`Su cuenta ya está vinculada a ${vinculoDescripcion()}. Para cambiarla escriba a ${SESSION.soporte}.`); return abrirVinculo(); } if (r.sinAcceso) return abrirPaywall(); alert(`No se pudo guardar el vínculo: ${r.error}`); return; }
  } else guardarCampana(campana);
  CAMPANA_ACTUAL = campana;

  $('crmBack').textContent = '← Cambiar corporación'; $('crmBack').onclick = () => showScreen('candidateRoute');
  $('crmInitials').textContent = initials(crmCandidate.nombre); $('crmName').textContent = crmCandidate.nombre;
  $('crmTarget').textContent = `Candidatura 2027 · ${corporation}${territory ? ` · ${territory}` : ''}`;
  $('crmContext').textContent = fraseDePartida({ candidate: crmCandidate, corpKey, territory, campana });
  {
    const partidoCtx = sinPartido(campana.avales) ? '' : String(campana.partido || crmCandidate.partido || '');
    const bloqueCtx = partidoCtx ? PartidosBloques.bloqueDeCandidatura(partidoCtx, crmCandidate.nombre || '') : (campana.espectro || '');
    agregarDatoRegional($('crmContext'), { ...regionDeCampana(crmCandidate, campana), bloque: bloqueCtx, partido: partidoCtx, corp: campana?.corp || '' });
  }
  $('crmPartidoPendiente')?.classList.toggle('hidden', campana.avales !== 'indeciso');
  $('crmVoteNumber').textContent = '…'; $('crmVoteTarget').textContent = 'Calculando objetivo competitivo'; $('crmVoteFormula').textContent = 'Contrastando la corporación y el territorio con la última elección comparable.';
  $('crmMapPanelNum').textContent = '01 · Mapa de historial electoral';
  showScreen('crm');
  pintarVitrina();
  pintarBriefing();
  pintarEscucha();
  pintarArquetipos();
  pintarPerfil();
  pintarDiaD();
  pintarFirmas();
  pintarEndoso();
  loadHistoricalMap(crmCandidate);
  renderCRMProfilePhoto(crmCandidate);
  pintarPuntaje(crmCandidate);
  window.Candi?.calculo?.(true);
  try {
    await prepararSalto(corpKey, campana);
    pintarMeta(await estimateVoteTarget(corpKey, territory));
  } finally { window.Candi?.calculo?.(false); }
  pintarContendientes();   /* después de la meta: la presión usa el escalón probable */
  if (SALTO_ACTUAL?.tipo?.unidad === 'municipio') ensureCRMMapToggles();
  if (SALTO_ACTUAL && crmMapMode === 'proyectado') refreshCRMMapMode();
}
/* CRM de una candidatura nueva: sin historial, el punto de partida es el
   territorio al que aspira y la referencia de 2023 de ese territorio. */
async function abrirCRMNuevo() {
  const n = NUEVO; if (!n) return;
  crmCandidate = null;
  const c = n.campana, lugar = [c.localidad, c.municipio, c.departamentoNombre].filter(Boolean).map(NOMBRE_BONITO).join(' · ');
  const indeciso = c.avales === 'indeciso', partido = indeciso ? '' : (n.partido || c.partido || '');
  $('crmBack').textContent = '← Inicio'; $('crmBack').onclick = () => showScreen('intro');
  $('crmInitials').textContent = initials(n.nombre); $('crmName').textContent = n.nombre;
  $('crmTarget').textContent = `Candidatura 2027 · ${CRM_CORPORATIONS[c.corp]} · ${lugar}`;
  $('crmContext').textContent = `Candidatura nueva${indeciso ? `, todavía sin partido: se lanza desde ${FAMILIA_CON_ARTICULO[c.espectro] || FAMILIA_CON_ARTICULO.sc}, y con esa familia se calcula todo mientras lo define` : partido ? ` con ${partido}${n.partidoNuevo ? ' (movimiento por constituir)' : ''}` : ''}. Sin historial propio, el punto de partida es el territorio: la referencia son los resultados de 2023 en ${lugar}.${n.objetivo ? ` Primer objetivo: ${n.objetivo.toLowerCase()}.` : ''}${textoRedesCRM(n)}`;
  {
    const bloqueN = partido ? PartidosBloques.bloqueDeCandidatura(partido, n.nombre || '') : (c.espectro || '');
    const identidad = partido ? window.C360Frases?.partido(partido) : '';
    const regional = window.C360Frases?.linea({ dep: c.departamento, municipio: c.municipio, bloque: bloqueN }) || '';
    const extra = [identidad ? `${identidad.charAt(0).toUpperCase()}${identidad.slice(1)}.` : '', regional].filter(Boolean).join(' ');
    if (extra) $('crmContext').textContent += ` ${extra}`;
    agregarDatoRegional($('crmContext'), { dep: c.departamento, municipio: c.municipio, bloque: bloqueN, partido, corp: c.corp });
  }
  $('crmPartidoPendiente')?.classList.toggle('hidden', !indeciso);
  $('crmVoteNumber').textContent = '…'; $('crmVoteTarget').textContent = 'Calculando objetivo competitivo'; $('crmVoteFormula').textContent = 'Contrastando la corporación y el territorio con la última elección comparable.';
  $('crmMapPanelNum').textContent = '01 · Territorio de campaña';
  document.getElementById('crmProfilePhoto')?.remove(); document.getElementById('crmProfilePhotoMissing')?.remove(); $('crmInitials').classList.remove('crm-avatar-hidden');
  $('crmPuntaje').innerHTML = ''; $('crmPuntaje').classList.add('hidden'); PUNTAJE_ACTUAL = null;   /* sin historial no hay puntaje: un cero ahí sería una calificación, no un dato */
  CAMPANA_ACTUAL = c;
  CRM_VITRINA = false;
  showScreen('crm');
  pintarVitrina();
  pintarBriefing();
  pintarEscucha();
  pintarArquetipos();
  pintarPerfil();
  pintarDiaD();
  pintarFirmas();
  pintarEndoso();
  renderTerritorioCiudad({ ...c, partido: c.partido || n.partido || '' }).then(ok => { if (!ok) renderTerritorioObjetivo(c); }).catch(() => renderTerritorioObjetivo(c));
  window.Candi?.calculo?.(true);
  try {
    const munCodigo = c.municipio ? await C360Electorado.codigoMunicipio(c.departamento, c.municipio).catch(() => '') : '';
    pintarMeta(await VoteTarget.estimate({ corp: c.corp, territory: lugar, baseUrl: S3, partido: n.partido || '', departamento: c.departamento || '', bloque: bloqueVigente(), codigo: { dep: c.departamento, mun: munCodigo } }));
  } finally { window.Candi?.calculo?.(false); }
  pintarContendientes();
}
/* Volver a la candidatura vinculada (al cargar o al intentar cambiarla). */
async function abrirVinculo() {
  const v = SESSION.vinculo; if (!v) return showScreen('intro');
  if (v.tipo === 'nuevo') { NUEVO = { ...v.nuevo, campana: v.campana }; return abrirCRMNuevo(); }
  const slugs = v.candidato?.slugs || [];
  const preload = $('preload');
  preload.classList.add('active'); $('preloadText').textContent = `Abriendo la candidatura de ${v.candidato?.nombre || 'su cuenta'}…`;
  const inicio = Date.now();
  await new Promise(resolve => { const t = setInterval(() => { const hit = historicalIndex.find(c => slugs.includes(c.slug)); if ((hit && historicalLocalDone) || Date.now() - inicio > 90000) { clearInterval(t); resolve(); } }, 400); });
  preload.classList.remove('active');
  const hit = historicalIndex.find(c => slugs.includes(c.slug));
  if (!hit) { showScreen('existing'); $('searchResults').innerHTML = `<div class="empty">No encontramos en el índice la candidatura vinculada a su cuenta (${escHtml(v.candidato?.nombre || '')}). Escriba a ${escHtml(SESSION.soporte)}.</div>`; return; }
  const profile = candidateProfile(hit);
  abrirRutaCandidato(profile);
  if (v.campana?.corp) { await precargarCampana(v.campana); launchCRM(); }
}

/* Foto: manda el banco fotos-candidatos/{slug}.jpg (82 hoy, casi todas de
   2026). Se prueban TODOS los slugs de la persona; el índice presidencial es
   el respaldo (nombre corto de la RNEC → match por 1er nombre + 2 apellidos). */
const CANDIDATE_PHOTO_BASE = RRData.publicUrl('congreso-2026/output/fotos-candidatos');
const PHOTO_UPLOAD_URL = 'https://drive.google.com/drive/folders/1ULVQC1Cyz_fjnhGdM7ydzg7tEgiDcPRS?usp=share_link';
const PRES_INDEX_URL = RRData.publicUrl('congreso-2026/output/presidencial/index-presidencial.json');
let fotosPresPromise = null;
function fotosPresidenciales() {
  if (!fotosPresPromise) fotosPresPromise = indicePresidencial().then(d => (d?.personas || []).filter(p => p.foto).map(p => ({ clave: CandRegistry.personaKey(p.nombre), foto: p.foto })));
  return fotosPresPromise;
}
function mismaPersonaPresidencial(claveCorta, claveLarga) {
  if (claveCorta === claveLarga) return true;
  const a = claveCorta.split(/\s+/).filter(Boolean), b = claveLarga.split(/\s+/).filter(Boolean);
  if (a.length < 3 || b.length < 3) return false;
  return a[0] === b[0] && a[a.length - 1] === b[b.length - 1] && a[a.length - 2] === b[b.length - 2];
}
async function urlsDeFoto(candidate) {
  const urls = [];
  if (candidate.fotoUrl) urls.push(candidate.fotoUrl);
  const slugs = (candidate.history?.length ? candidate.history : [candidate]).map(c => c.slug).filter(Boolean);
  if (candidate.slug) slugs.unshift(candidate.slug);
  slugs.forEach(slug => urls.push(`${CANDIDATE_PHOTO_BASE}/${slug}.jpg`));
  const clave = CandRegistry.personaKey(candidate.nombre || '');
  const hit = (await fotosPresidenciales()).find(p => mismaPersonaPresidencial(p.clave, clave));
  if (hit) urls.push(hit.foto);
  return [...new Set(urls)];
}
function sinFoto(avatar, candidate) {
  const missing = document.createElement('div'); missing.id = 'crmProfilePhotoMissing'; missing.className = 'crm-profile-photo-missing';
  missing.innerHTML = `<strong>${escHtml(initials(candidate.nombre))}</strong><span>Aún no hay foto de hoja de vida.</span><a href="${PHOTO_UPLOAD_URL}" target="_blank" rel="noopener">¿Es usted? Súbala aquí</a>`;
  avatar.after(missing);
}
async function renderCRMProfilePhoto(candidate) {
  const avatar = $('crmInitials'); if (!avatar || !candidate) return;
  avatar.classList.add('crm-avatar-hidden');
  $('crmProfilePhoto')?.remove(); $('crmProfilePhotoMissing')?.remove();
  for (const url of await urlsDeFoto(candidate)) {
    const ok = await new Promise(resolve => { const probe = new Image(); probe.onload = () => resolve(true); probe.onerror = () => resolve(false); probe.src = url; });
    if (!ok) continue;
    if (crmCandidate !== candidate) return;
    const photo = document.createElement('img'); photo.id = 'crmProfilePhoto'; photo.className = 'crm-profile-photo'; photo.alt = `Foto de ${candidate.nombre || 'candidato'}`; photo.src = url;
    avatar.after(photo); return;
  }
  if (crmCandidate === candidate) sinFoto(avatar, candidate);
}

/* ─── 8 bis. Puntaje electoral ───────────────────────────────────────────────
   El mismo puntaje de analisis-candidato.html y del modal de Caudal, para que
   un número signifique lo mismo en toda la plataforma:

       100 · log10(votos + 1) / log10(vmax + 1),   vmax = votos del presidente

   Es logarítmica a propósito. Entre una JAL (342 votos) y la Presidencia (12,9
   millones) hay cuatro órdenes de magnitud: en una regla lineal TODA candidatura
   territorial —que es la clientela de esta página— valdría 0. En la logarítmica
   cada escalón es «diez veces más votos», que es como se lee de verdad una
   carrera política.

   El número solo dice tamaño. Lo que dice DESEMPEÑO es el cuartil: contra
   quiénes compitió esa misma elección y a cuántos superó. Por eso el color sale
   del cuartil y no del puntaje — 40 puntos en una JAL de Tunja y 40 puntos en el
   Concejo de Bogotá no son la misma noticia. */
let SCORE_LOG_MAX = Math.log10(12950643 + 1);   /* respaldo: 2V 2026, se refresca con presIndex.vmax */
let presIndexPromise = null;
function indicePresidencial() {
  if (!presIndexPromise) presIndexPromise = fetch(PRES_INDEX_URL).then(r => r.ok ? r.json() : Promise.reject())
    .then(d => { if (d?.vmax) SCORE_LOG_MAX = Math.log10(Number(d.vmax) + 1); return d; }).catch(() => null);
  return presIndexPromise;
}
function puntajeDeVotos(votos) {
  const v = Number(votos || 0); if (!v) return 1;
  return Math.max(1, Math.min(99, Math.round(100 * Math.log10(v + 1) / SCORE_LOG_MAX)));
}
const CUARTILES = {
  4: { etiqueta: 'Cuartil superior', clase: 'q4' },
  3: { etiqueta: 'Tercer cuartil', clase: 'q3' },
  2: { etiqueta: 'Segundo cuartil', clase: 'q2' },
  1: { etiqueta: 'Cuartil inferior', clase: 'q1' }
};
/* Rivales = la MISMA elección. `corp` ya trae corporación · territorio · año
   ("CONCEJO · TUNJA · 2023"), así que una comparación de cadenas basta y no hay
   que reconstruir la circunscripción. Con menos de 8 candidaturas un cuartil no
   dice nada y se calla. */
function cuartilElectoral(candidatura) {
  const corp = String(candidatura?.corp || ''); if (!corp) return null;
  const votos = Number(candidatura.votos || 0);
  const rivales = historicalIndex.filter(c => c.corp === corp);
  if (rivales.length < 8) return null;
  const debajo = rivales.filter(c => Number(c.votos || 0) < votos).length;
  const percentil = Math.round(100 * debajo / rivales.length);
  return { cuartil: percentil >= 75 ? 4 : percentil >= 50 ? 3 : percentil >= 25 ? 2 : 1, rivales: rivales.length, percentil };
}
/* La candidatura que se puntúa es la MÁS RECIENTE (history ya viene ordenado
   por año descendente): el puntaje es «cómo le fue la última vez», no su récord
   histórico. */
function candidaturaPuntuada(profile) { return profile?.history?.length ? profile.history[0] : profile; }
/* Referencia territorial: en Bogotá el alcalde, en el resto el gobernador del
   departamento donde se va a lanzar. Sale del mismo índice que ya está en
   memoria: el más votado de esa elección es quien la ganó. */
function referenciaEjecutiva() {
  const campana = CAMPANA_ACTUAL || SESSION.vinculo?.campana || null;
  const territorio = normalizedText(campana?.departamentoNombre || crmCandidate?.circunscripcion || '');
  const esBogota = territorio.includes('BOGOTA');
  const cargo = esBogota ? 'ALCALDIA' : 'GOBERNACION';
  const lugar = esBogota ? 'BOGOTA' : territorio;
  if (!lugar) return null;
  const candidatos = historicalIndex.filter(c => {
    const corp = normalizedText(c.corp);
    return corp.startsWith(cargo) && (corp.includes(lugar) || normalizedText(c.circunscripcion).includes(lugar));
  });
  if (!candidatos.length) return null;
  const ganador = candidatos.sort((a, b) => (candidateYear(b) - candidateYear(a)) || (Number(b.votos || 0) - Number(a.votos || 0)))
    .filter((c, _, lista) => candidateYear(c) === candidateYear(lista[0]))
    .sort((a, b) => Number(b.votos || 0) - Number(a.votos || 0))[0];
  if (!ganador?.votos) return null;
  return { cargo: esBogota ? 'Alcaldía de Bogotá' : `Gobernación de ${campana?.departamentoNombre || crmCandidate?.circunscripcion || ''}`.trim(),
           nombre: ganador.nombre, votos: Number(ganador.votos), anio: candidateYear(ganador), puntaje: puntajeDeVotos(ganador.votos) };
}
let PUNTAJE_ACTUAL = null;
/* La estrella vive en el encabezado del CRM, al lado del nombre: es lo primero
   que la persona busca de sí misma. Solo aparece con historial — una
   candidatura nueva no tiene desempeño pasado que mostrar, y un cero ahí sería
   una calificación, no un dato. */
async function pintarPuntaje(profile) {
  const caja = $('crmPuntaje'); if (!caja) return;
  const candidatura = candidaturaPuntuada(profile);
  const votos = Number(candidatura?.votos || 0);
  if (!votos) { caja.innerHTML = ''; caja.classList.add('hidden'); PUNTAJE_ACTUAL = null; return; }
  await indicePresidencial();   /* refresca vmax antes de calcular, si el índice contesta */
  const cuartil = cuartilElectoral(candidatura);
  PUNTAJE_ACTUAL = { candidatura, votos, puntaje: puntajeDeVotos(votos), cuartil };
  const clase = cuartil ? CUARTILES[cuartil.cuartil].clase : 'qsin';
  caja.classList.remove('hidden');
  caja.innerHTML = `<span class="puntaje ${clase}" title="Puntuación electoral pasada">
      <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 2.6l2.9 5.9 6.5.9-4.7 4.6 1.1 6.4L12 17.4l-5.8 3 1.1-6.4L2.6 9.4l6.5-.9z"/></svg>
      <b>${PUNTAJE_ACTUAL.puntaje}</b>
      <button type="button" class="puntaje-i" aria-label="Qué significa esta puntuación" onclick="mostrarPuntajeInfo()">i</button>
    </span>`;
}
function mostrarPuntajeInfo() {
  const p = PUNTAJE_ACTUAL; if (!p) return;
  const c = p.candidatura, ref = referenciaEjecutiva();
  const eleccion = String(c.corp || 'su última candidatura');
  const escala = [
    `<li><b>100</b> · Presidencia de la República — el presidente electo es el techo de la escala.</li>`,
    ref ? `<li><b>${ref.puntaje}</b> · ${escHtml(ref.cargo)}${ref.anio ? ` ${ref.anio}` : ''} — ${escHtml(ref.nombre)}, ${ref.votos.toLocaleString('es-CO')} votos.</li>` : '',
    `<li><b>${p.puntaje}</b> · usted, con ${p.votos.toLocaleString('es-CO')} votos en ${escHtml(eleccion)}.</li>`
  ].filter(Boolean).join('');
  $('introModalKicker').textContent = 'Candidato 360 · puntuación electoral';
  $('introModalTitle').textContent = `Su puntuación electoral pasada: ${p.puntaje}`;
  $('introModalText').innerHTML = `
    <p>Es el tamaño de su última votación en una escala donde el <b>presidente electo vale 100</b>. La escala es logarítmica: cada escalón vale diez veces más votos, porque entre una JAL y una Presidencia hay cuatro órdenes de magnitud y en una regla lineal toda candidatura territorial marcaría cero.</p>
    <ul class="puntaje-escala">${escala}</ul>
    ${p.cuartil
      ? `<p>El color viene del <b>cuartil</b>, no del puntaje: es contra quiénes compitió. En ${escHtml(eleccion)} hubo <b>${p.cuartil.rivales.toLocaleString('es-CO')} candidaturas</b> y usted superó al <b>${p.cuartil.percentil}%</b> — ${CUARTILES[p.cuartil.cuartil].etiqueta.toLowerCase()}.</p>`
      : `<p>No pintamos cuartil: en esa elección hay menos de ocho candidaturas en el índice y comparar contra tan pocos no dice nada.</p>`}
    <p class="puntaje-nota">Mide tamaño de votación, no favorabilidad ni intención de voto. Misma fórmula del Análisis de Candidato y de Caudal: 100 · log10(votos + 1) / log10(votos del presidente + 1).</p>`;
  $('introModal').classList.add('open');
}

/* ─── 8 ter. Reparto de la meta cuando la candidatura SALTA de corporación ───
   La proyección repartía la meta proporcional al historial propio. Eso está
   bien mientras la corporación sea la misma; en un salto de escala colapsa:
   una edil de Barrios Unidos con 709 votos que se lanza al Concejo recibía sus
   6.770 votos proyectados enteros en Barrios Unidos, como si las otras 19
   localidades no existieran.

   La idea, en una frase: LO QUE YA TIENE SE QUEDA DONDE LO CONSIGUIÓ; LO QUE
   LE FALTA LO BUSCA DONDE YA VOTA SU PARTIDO.

       reparto = arraigo · propio  +  (1 − arraigo) · base

   · `propio`  es su huella histórica dentro del territorio de origen.
   · `base`    es cómo vota el territorio destino, en cascada: la huella real
               del PARTIDO en esa corporación (resultados 2023) → si no
               alcanza, la del BLOQUE ideológico (partidos-bloques.js) → si
               tampoco, la PARTICIPACIÓN (dónde vota la gente).
   · `arraigo` es qué fracción de su votación destino cae en el territorio de
               origen. NO es una perilla: sale del estudio de quienes ya dieron
               ese mismo salto en el ciclo siguiente (tools/candidato-360/
               saltos/estudio.mjs → saltos-arraigo.json, mediana por salto y
               departamento; nacional si el departamento tiene pocos casos).
               Sin estudio publicado, arraigo = la parte que el origen pesa en
               la base — es decir, sin bono: solo el patrón del partido.

   Toda la lógica es pura (entra un objeto, sale un objeto) para poderla probar
   sin mapa y sin red: prueba-salto.mjs. */
/* ⚠️ Todo salto entre corporaciones DISTINTAS tiene que estar acá. Sin su
   entrada, `tipoSalto` devuelve null y la meta cae al reparto proporcional de
   siempre, que la deja ENTERA sobre el territorio de origen: un edil de
   Teusaquillo que se lanza a la Alcaldía de Bogotá veía 1,5 millones de votos
   en Teusaquillo y cero en las otras 19 localidades (sep-2026). Solo tienen
   estudio de arraigo tres (`saltos-arraigo.json`); el resto va sin bono.
   Unidad: `localidad` cuando el destino es una ciudad (las 11 con resultados
   por comuna); `municipio` cuando el destino es el departamento. */
const SALTOS = {
  'jal>concejo': 'localidad', 'jal>alcaldia': 'localidad', 'concejo>alcaldia': 'localidad', 'alcaldia>concejo': 'localidad',
  'asamblea>concejo': 'localidad', 'asamblea>alcaldia': 'localidad', 'gobernacion>concejo': 'localidad', 'gobernacion>alcaldia': 'localidad',
  'jal>asamblea': 'municipio', 'jal>gobernacion': 'municipio', 'concejo>asamblea': 'municipio', 'concejo>gobernacion': 'municipio',
  'alcaldia>asamblea': 'municipio', 'alcaldia>gobernacion': 'municipio', 'asamblea>gobernacion': 'municipio', 'gobernacion>asamblea': 'municipio',
};
const ARRAIGO_N_MINIMO = 5;   /* con menos casos, una mediana es una anécdota */
function tipoSalto(corpOrigen, corpDestino) {
  const k = `${corpOrigen}>${corpDestino}`;
  return SALTOS[k] ? { clave: k, unidad: SALTOS[k] } : null;
}
/* Normaliza un mapa {área: valor} a proporciones que suman 1. Vacío → null. */
function proporciones(mapa) {
  const entradas = Object.entries(mapa || {}).map(([k, v]) => [k, Math.max(0, Number(v) || 0)]);
  const total = entradas.reduce((s, [, v]) => s + v, 0);
  return total > 0 ? Object.fromEntries(entradas.map(([k, v]) => [k, v / total])) : null;
}
/* La huella del partido en la corporación destino. `porArea` es
   {área: {partidos: [[nombre, votos]…], votantes}}, el formato de los
   resultados-*.json. Se aceptan las partes de una coalición y se suman. */
/* Las palabras que identifican a un partido, sin las estructurales: «PARTIDO
   NUEVO LIBERALISMO» → {NUEVO, LIBERALISMO}. Una lista de coalición cuenta para
   el partido si trae TODAS sus palabras: «NUEVO LIBERALISMO- AGRUPACION POLITICA
   EN MARCHA» sí es huella del Nuevo Liberalismo aunque no diga «PARTIDO». */
const PALABRAS_ESTRUCTURALES = new Set(['PARTIDO', 'MOVIMIENTO', 'POLITICO', 'POLITICA', 'COALICION', 'DE', 'DEL', 'LA', 'EL', 'LOS', 'LAS', 'Y']);
function nucleoPartido(nombre) { return normPalabras(nombre).split(' ').filter(w => w && !PALABRAS_ESTRUCTURALES.has(w)); }
function huellaPartido(porArea, partes) {
  const claves = (partes || []).map(p => PartidosBloques.norm(p)).filter(Boolean);
  const nucleos = claves.map(nucleoPartido).filter(n => n.length);
  if (!claves.length) return { huella: null, cobertura: 0, votos: 0 };
  const huella = {}; let areasCon = 0, votos = 0;
  for (const [area, d] of Object.entries(porArea || {})) {
    let v = 0;
    for (const [nombre, n] of (d?.partidos || [])) {
      const nn = PartidosBloques.norm(nombre), palabras = new Set(normPalabras(nombre).split(' '));
      const calza = claves.some(c => nn === c || (c.length > 8 && nn.includes(c)) || (nn.length > 8 && c.includes(nn))) || nucleos.some(nu => nu.every(w => palabras.has(w)));
      if (calza) v += Number(n) || 0;
    }
    huella[area] = v; votos += v; if (v > 0) areasCon++;
  }
  const n = Object.keys(porArea || {}).length;
  return { huella, cobertura: n ? areasCon / n : 0, votos };
}
function huellaBloque(porArea, bloque) {
  if (!bloque || bloque === 'sc') return { huella: null, cobertura: 0, votos: 0 };
  const huella = {}; let areasCon = 0, votos = 0;
  for (const [area, d] of Object.entries(porArea || {})) {
    let v = 0;
    for (const [nombre, n] of (d?.partidos || [])) if (PartidosBloques.bloqueDeOrganizacion(nombre) === bloque) v += Number(n) || 0;
    huella[area] = v; votos += v; if (v > 0) areasCon++;
  }
  const n = Object.keys(porArea || {}).length;
  return { huella, cobertura: n ? areasCon / n : 0, votos };
}
function huellaParticipacion(porArea) {
  return Object.fromEntries(Object.entries(porArea || {}).map(([area, d]) => [area, Number(d?.votantes || d?.validos || 0)]));
}
/* La cascada de la base. Un partido cuenta como «con masa» si aparece en al
   menos el 60 % de las áreas y pesa ≥ 1 % de los válidos: por debajo de eso su
   huella es ruido de dos o tres candidatos, no un patrón del territorio. */
function baseDestino({ porArea, partido, nombreCandidato, bloqueFirmas }) {
  /* Por firmas no hay partido: manda el bloque que la persona eligió. */
  if (bloqueFirmas) {
    const hb = huellaBloque(porArea, bloqueFirmas);
    if (hb.huella && hb.votos > 0) return { capa: 'firmas', etiqueta: PartidosBloques.BLOQUE_LABEL[bloqueFirmas] || bloqueFirmas, bloque: bloqueFirmas, proporciones: proporciones(hb.huella) };
    const part = proporciones(huellaParticipacion(porArea));
    return part ? { capa: 'participacion', etiqueta: 'participación', proporciones: part } : null;
  }
  const partes = PartidosBloques.partesDeCoalicion(partido || '');
  const totalValidos = Object.values(porArea || {}).reduce((s, d) => s + (d?.partidos || []).reduce((t, [, v]) => t + (Number(v) || 0), 0), 0);
  const hp = huellaPartido(porArea, partes);
  if (hp.huella && hp.cobertura >= .6 && totalValidos && hp.votos / totalValidos >= .01) return { capa: 'partido', etiqueta: partes.join(' + '), proporciones: proporciones(hp.huella) };
  const bloque = PartidosBloques.bloqueDeCandidatura(partido || '', nombreCandidato || '');
  const hb = huellaBloque(porArea, bloque);
  if (hb.huella && hb.cobertura >= .6 && hb.votos > 0) return { capa: 'bloque', etiqueta: PartidosBloques.BLOQUE_LABEL[bloque] || bloque, bloque, proporciones: proporciones(hb.huella) };
  const part = proporciones(huellaParticipacion(porArea));
  return part ? { capa: 'participacion', etiqueta: 'participación', proporciones: part } : null;
}
/* El arraigo empírico para este salto: departamento si tiene casos, nacional
   si no; null si no hay estudio (o no llega al mínimo). */
function arraigoEmpirico(tabla, claveSalto, departamento) {
  const t = tabla?.[claveSalto]; if (!t) return null;
  const dep = t[String(departamento || '').replace(/^0+/, '')], nac = t._nacional;
  /* `lift` es cuántas veces pesa el origen frente a lo que pesa en la huella
     del partido (mediana medida). Manda sobre la fracción cruda porque no
     depende del tamaño del territorio de origen: Suba no es La Candelaria. */
  const arma = (d, ambito) => ({ valor: d.arraigo_mediana, lift: Number(d.lift_n) >= ARRAIGO_N_MINIMO && d.lift_mediana != null ? Number(d.lift_mediana) : null, n: d.n, ambito });
  if (dep && dep.n >= ARRAIGO_N_MINIMO) return arma(dep, 'departamento');
  if (nac && nac.n >= ARRAIGO_N_MINIMO) return arma(nac, 'nacional');
  return null;
}
/* Reparte `meta` entre las áreas del destino. `propio` es {área: votos} del
   historial (solo tiene áreas del origen); `origen` es el conjunto de claves
   que forman el territorio de origen dentro del destino. `arraigo` es null
   (sin estudio), una fracción, o {valor, lift} del estudio: con lift, el
   origen pesa lift × su peso en la base, acotado al 95 %. Devuelve enteros
   que suman exactamente `meta` (mismo cuidado de distributeVotes). */
function repartoSalto({ meta, propio, origen, base, arraigo }) {
  const areas = Object.keys(base?.proporciones || {});
  if (!areas.length || !meta) return null;
  const origenSet = new Set(origen || []);
  const pesoOrigenEnBase = areas.filter(a => origenSet.has(a)).reduce((s, a) => s + base.proporciones[a], 0);
  /* Sin estudio, el origen pesa lo que pesa en la base: cero bono. Con
     estudio, el origen recibe la fracción medida y el resto sale a la base
     RE-NORMALIZADA fuera del origen — si no, el origen cobraría dos veces. */
  const cfg = arraigo != null && typeof arraigo === 'object' ? arraigo : { valor: arraigo };
  const acota = x => Math.max(0, Math.min(.95, Number(x) || 0));
  const a = cfg.lift != null && pesoOrigenEnBase > 0 ? acota(cfg.lift * pesoOrigenEnBase)
    : cfg.valor != null ? acota(cfg.valor) : pesoOrigenEnBase;
  const propioProp = proporciones(Object.fromEntries(Object.entries(propio || {}).filter(([k]) => origenSet.has(k))));
  const fueraTotal = areas.filter(x => !origenSet.has(x)).reduce((s, x) => s + base.proporciones[x], 0);
  const crudo = {};
  for (const area of areas) {
    const enOrigen = origenSet.has(area);
    let p;
    if (enOrigen) {
      /* dentro del origen: la forma la pone su huella propia; si no la hay, la base */
      const forma = propioProp ? (propioProp[area] || 0) : (pesoOrigenEnBase ? base.proporciones[area] / pesoOrigenEnBase : 0);
      p = a * forma;
    } else {
      p = fueraTotal ? (1 - a) * base.proporciones[area] / fueraTotal : 0;
    }
    crudo[area] = p * meta;
  }
  return distributeVotes(crudo, meta);
}

/* ── El salto en el CRM ──────────────────────────────────────────────────────
   Se prepara al abrir el CRM (launchCRM) y lo consume projectedVotesByArea.
   Dos geometrías:
   · localidad (JAL → Concejo en las 11 ciudades con resultados por comuna):
     la misma capa que ya pinta el mapa, así que solo cambian los números.
   · municipio (→ Asamblea / Gobernación): el destino es el departamento
     entero, que el mapa histórico no muestra. En «Proyectado» se pinta la
     capa de municipios del departamento con el reparto; en «Total» vuelve el
     mapa histórico. */
let SALTO_ACTUAL = null;
/* true mientras el mapa muestra la proyección departamental (que puede pintarse
   sin `crmMapState`, cuando el historial no toca el destino). */
let PROYECCION_DEPTAL = false;
/* El estudio de saltos viaja CON el sitio (lo produce
   tools/candidato-360/saltos/estudio.mjs y queda versionado en el repo: son
   22 KB). La copia en S3 existe para poder refrescarlo sin desplegar, y por
   eso manda cuando está. */
const SALTOS_ARRAIGO_URL = 'candidato-360-data/saltos-arraigo.json';
const SALTOS_ARRAIGO_URL_S3 = `${S3}/candidato-360/saltos-arraigo.json`;
let saltosArraigoPromise = null;
function tablaArraigo() {
  if (!saltosArraigoPromise) saltosArraigoPromise = fetchJSON(SALTOS_ARRAIGO_URL_S3).catch(() => fetchJSON(SALTOS_ARRAIGO_URL)).catch(() => null);
  return saltosArraigoPromise;
}
/* Los resultados por área de la corporación destino, en el formato
   {área: {name, partidos, votantes}} que espera baseDestino. */
async function resultadosDestino(unidad, mesas, campana) {
  if (unidad === 'localidad') {
    /* La ciudad es la de la CAMPAÑA, no la de la primera mesa: quien viene de
       otro municipio (o de una asamblea) tiene sus mesas en otra parte. */
    const m = mesas?.[0], depC = String(campana?.departamento || '').replace(/^0+/, ''), munC = codigoMunicipioObjetivo();
    const dep = depC || String(m?.dep || ''), mun = munC || String(m?.mun || '');
    if (!dep || !mun) return null;
    const key = `${dep.padStart(2, '0')}-${mun.padStart(3, '0')}`;
    const r = await fetchJSON(`${S3}/concejo-2023/resultados-concejo-2023.json`);
    const comunas = r?.data?.[key]?.comunas; if (!comunas) return null;
    return { porArea: comunas, key };
  }
  const dde = String(campana?.departamento || mesas?.[0]?.dep || '').padStart(2, '0'); if (!dde || dde === '00') return null;
  const r = await fetchJSON(`${S3}/asamblea-2023/dep/${dde}.json`);
  const comunas = r?.comunas; if (!comunas) return null;
  return { porArea: comunas, key: dde };
}
/* Empareja las áreas de los resultados con las llaves del mapa: por código y,
   si no calza, por nombre normalizado. Devuelve porArea re-indexado con las
   llaves del mapa. */
function emparejarAreas(porArea, llavesMapa, nombresMapa) {
  const salida = {}, porNombre = {};
  for (const [k, nombre] of Object.entries(nombresMapa || {})) porNombre[normalizedText(nombre)] = k;
  for (const [code, d] of Object.entries(porArea || {})) {
    const c2 = String(code).padStart(2, '0');
    const llave = llavesMapa.includes(code) ? code : llavesMapa.includes(c2) ? c2 : porNombre[normalizedText(d?.name || '')];
    if (llave) salida[llave] = d;
  }
  return salida;
}
async function prepararSalto(corpDestino, campana) {
  SALTO_ACTUAL = null;
  const corpOrigen = corporacionHistorica(crmCandidate);
  const tipo = tipoSalto(corpOrigen, corpDestino); if (!tipo || !crmCandidate) return null;
  try {
    const data = await datosCandidatura(crmCandidate), mesas = data.mesas || [];
    const rd = await resultadosDestino(tipo.unidad, mesas, campana); if (!rd) return null;
    const tabla = await tablaArraigo();
    const arraigo = arraigoEmpirico(tabla, tipo.clave, campana?.departamento || mesas[0]?.dep);
    SALTO_ACTUAL = { tipo, porArea: rd.porArea, arraigo, corpOrigen, corpDestino, campana };
    /* A la Alcaldía se la mide con el Concejo de la ciudad, que trae partido
       por comuna. Donde la familia no tuvo lista al Concejo pero sí candidato
       a la Alcaldía (Cartagena con el Pacto), mandan esos votos: es la misma
       corporación a la que se lanza. */
    if (corpDestino === 'alcaldia' && tipo.unidad === 'localidad') {
      const puestos = await puestosPorBarrio().catch(() => null);
      const f = await proyeccionFamiliar(campana, puestos);
      if (f?.deAlcaldia?.length) SALTO_ACTUAL.alcaldia = f;
    }
    return SALTO_ACTUAL;
  } catch (e) { return null; }
}
/* Texto de la nota del mapa: dice qué capa se usó y de dónde salió el arraigo.
   Sin esto un reparto por bloque se leería como una predicción del partido. */
function notaSalto(base) {
  const s = SALTO_ACTUAL; if (!s || !base) return '';
  const capa = base.capa === 'alcaldia' ? `los votos de su familia política a la Alcaldía de 2023 (${base.etiqueta}): no tuvo lista al Concejo`
    : base.capa === 'partido' ? `la huella de ${base.etiqueta} en esa corporación (2023)`
    : base.capa === 'bloque' ? `el bloque ${base.etiqueta.toLowerCase()} (su partido no tiene huella suficiente en esa corporación)`
    : 'la participación electoral (ni su partido ni su bloque tienen huella suficiente)';
  const ambito = s.arraigo?.ambito === 'departamento' ? 'en este departamento' : 'en el país';
  const arraigo = s.arraigo?.lift != null
    ? `Su territorio de origen pesa ${s.arraigo.lift.toLocaleString('es-CO', { maximumFractionDigits: 1 })} veces lo que pesa en esa huella: es la mediana de ${s.arraigo.n} candidaturas que dieron este mismo salto ${ambito}.`
    : s.arraigo
    ? `El ${Math.round(s.arraigo.valor * 100)} % se queda en su territorio de origen: es la mediana de ${s.arraigo.n} candidaturas que dieron este mismo salto ${ambito}.`
    : 'Sin estudio de saltos publicado, su territorio de origen pesa lo que pesa en esa huella: no lleva bono.';
  return `Salto de ${CRM_CORPORATIONS[s.corpOrigen] || s.corpOrigen} a ${CRM_CORPORATIONS[s.corpDestino] || s.corpDestino}: la meta se reparte según ${capa}. ${arraigo}`;
}
/* Reparto para la geometría de localidad (el mapa de ciudad que ya está). */
function repartoSaltoCiudad(state, goal) {
  const s = SALTO_ACTUAL; if (!s || s.tipo.unidad !== 'localidad') return null;
  const llaves = Object.keys(state.namesByArea || {});
  const porArea = emparejarAreas(s.porArea, llaves, state.namesByArea);
  if (Object.keys(porArea).length < 2) return null;
  let base = baseDestino({ porArea, partido: partidoVigente(), nombreCandidato: crmCandidate?.nombre, bloqueFirmas: bloqueVigente() });
  if (s.alcaldia && base?.capa !== 'partido') {
    const agg = agregarPorArea(s.alcaldia.mesas, m => state.config.mesaKey ? state.config.mesaKey(m) : claveLocal(m)).votesByArea;
    const prop = proporciones(agg);
    if (prop) base = { capa: 'alcaldia', etiqueta: s.alcaldia.deAlcaldia.map(NOMBRE_BONITO).join(', '), proporciones: prop };
  }
  if (!base) return null;
  const origen = Object.keys(state.votesByArea || {}).filter(k => Number(state.votesByArea[k] || 0) > 0);
  const reparto = repartoSalto({ meta: goal, propio: state.votesByArea, origen, base, arraigo: s.arraigo });
  if (!reparto) return null;
  s.base = base;
  return reparto;
}
/* Mudanza de localidad dentro de la misma ciudad. No es un salto de
   corporación —sigue siendo una JAL— pero sí de territorio, y el reparto
   proporcional de siempre dejaba la meta sobre la localidad ANTERIOR: al edil
   de Teusaquillo que se lanza por Tunjuelito le pintaba sus 2.400 votos en
   Teusaquillo, donde en 2027 no se le cuenta ni uno.

   Acá no hay nada que repartir: a una JAL se entra por UNA localidad, así que
   la meta entera cae en la suya. Vale también para el que se queda donde
   estaba —toda su votación ya estaba ahí—, de modo que la regla es una sola. */
let MUDANZA_LOCAL = null;
function repartoMudanzaLocal(state, goal) {
  const alcance = alcanceObjetivo();
  if (alcance?.tipo !== 'localidad' || !state?.namesByArea) return null;
  const objetivo = normalizedText(cortoLocal(alcance.localidad)); if (!objetivo) return null;
  const llave = Object.keys(state.namesByArea).find(k => normalizedText(cortoLocal(state.namesByArea[k])) === objetivo);
  if (!llave) return null;
  MUDANZA_LOCAL = state.namesByArea[llave];
  return { [llave]: goal };
}
/* Geometría de municipio: pinta el departamento con el reparto. */
async function pintarProyeccionDepartamental(goal) {
  const s = SALTO_ACTUAL; if (!s || s.tipo.unidad !== 'municipio') return false;
  const dep = String(s.campana?.departamento || '').padStart(2, '0');
  try {
    const geoData = await fetchJSON(`${S3}/mapas-2026/Departamentos-mps/${dep}.json`);
    const nameOf = f => f.properties.mpio_cnmbr || 'Municipio';
    const nombres = Object.fromEntries(geoData.features.map(f => [normalizedText(nameOf(f)), nameOf(f)]));
    const porArea = emparejarAreas(s.porArea, Object.keys(nombres), nombres);
    const base = baseDestino({ porArea, partido: partidoVigente(), nombreCandidato: crmCandidate?.nombre, bloqueFirmas: bloqueVigente() });
    if (!base) return false;
    const origenNombre = normalizedText(String(crmCandidate?.corp || '').split('·')[1] || crmCandidate?.circunscripcion || '');
    /* Con origen departamental (diputado, gobernador) no hay UN municipio de
       origen: el «·ANTIOQUIA·» del corp casaría con cualquier municipio que se
       llame como el departamento (Bolívar, en el Cauca). Va todo a la base. */
    const origen = CORP_DEPARTAMENTAL.includes(s.corpOrigen) ? [] : Object.keys(nombres).filter(k => k === origenNombre || (origenNombre && k.includes(origenNombre)));
    const propio = Object.fromEntries(origen.map(k => [k, Number(crmCandidate?.votos || 1)]));
    const reparto = repartoSalto({ meta: goal, propio, origen, base, arraigo: s.arraigo });
    if (!reparto) return false;
    s.base = base;
    const max = Math.max(1, ...Object.values(reparto));
    crearMapa([4.6, -74.1], 5); aplicarBasemap(false);
    crmMapLayer = L.geoJSON(geoData, {
      style: f => { const k = normalizedText(nameOf(f)), v = reparto[k] || 0; return { color: '#fff', weight: origen.includes(k) ? 2 : 1, fillColor: MAP_COLOR(v / max), fillOpacity: origen.includes(k) ? .9 : .78 }; },
      onEachFeature: (f, layer) => { const k = normalizedText(nameOf(f)); layer._vitrinaCode = k; layer.bindTooltip(`<strong>${NOMBRE_BONITO(nameOf(f))}</strong><br>${(reparto[k] || 0).toLocaleString('es-CO')} votos proyectados`, { sticky: true }); }
    }).addTo(crmLeafletMap);
    encuadrar(crmMapLayer, 24);
    PROYECCION_DEPTAL = true;
    renderMapBreakdown(reparto, nombres, `Meta proyectada por municipio`);
    $('crmMapTitle').textContent = `¿Dónde buscar los votos en ${s.campana?.departamentoNombre || 'el departamento'}?`;
    $('crmMapVotes').textContent = `${goal.toLocaleString('es-CO')} votos · meta`;
    $('crmMapNote').textContent = notaSalto(base);
    if (crmMapState) crmMapState.geometriaDestino = true;
    return true;
  } catch (e) { return false; }
}

/* ─── 9. Mapas ───────────────────────────────────────────────────────────── */
let crmLeafletMap = null, crmMapLayer = null, crmBarrioLayer = null, crmTileLayer = null;
let crmMapMode = 'total', crmMapState = null;
/* El mapa se pinta con el color del PARTIDO con el que la persona se lanza: una
   rampa de un solo tono, de claro a oscuro, porque lo que codifica es una
   magnitud (cuántos votos). El tono da identidad; la claridad, la cantidad.
   Sin partido —o con uno sin color ni bloque— queda el verde de siempre. */
const RAMPA_POR_DEFECTO = ['#b7d9bf', '#79b987', '#3e8a5b', '#174f35'];
let RAMPA_MAPA = RAMPA_POR_DEFECTO;
function fijarRampaMapa(partido, nombreCandidato) {
  const bloque = bloqueVigente(), colorBloque = bloque && window.PartidosBloques?.BLOQUE_COLOR?.[bloque];
  RAMPA_MAPA = (colorBloque && window.PartidosBloques?.rampaDeColor?.(colorBloque))
    || (window.PartidosBloques?.rampaDePartido?.(partido, nombreCandidato)) || RAMPA_POR_DEFECTO;
  /* Las barras del desglose van del mismo color que el mapa: son el mismo dato
     leído de otra forma, y verlas en verde al lado de un mapa azul confunde. */
  document.getElementById('crm')?.style.setProperty('--partido', RAMPA_MAPA[2]);
  return RAMPA_MAPA;
}
const MAP_COLOR = ratio => ratio <= 0 ? (window.PartidosBloques?.SIN_VOTOS || '#eef0ea') : ratio < .12 ? RAMPA_MAPA[0] : ratio < .35 ? RAMPA_MAPA[1] : ratio < .65 ? RAMPA_MAPA[2] : RAMPA_MAPA[3];
/* Una frase para la nota del mapa cuando el color no es el de la casa. */
function notaColorPartido() {
  const partido = partidoVigente();
  if (!partido || RAMPA_MAPA === RAMPA_POR_DEFECTO) return '';
  const propio = window.PartidosBloques?.PARTIDO_COLOR?.[window.PartidosBloques.norm(partido)];
  return ` El mapa va en el color de ${partido}${propio ? '' : ' (el de su bloque ideológico: esa organización no tiene color propio en la paleta)'}.`;
}
function crearMapa(center, zoom) {
  const mapEl = $('crmMap');
  /* zoomSnap: Leaflet, por defecto, solo usa zooms ENTEROS. fitBounds elegía
     el mayor entero en el que cabía la ciudad, y entre un nivel y el siguiente
     hay un factor 2: Bogotá quedaba en zoom 11 ocupando la mitad del marco,
     con Kennedy y Bosa diminutas y el resto vacío. Con zoom fraccionario el
     encuadre es exacto. */
  if (!crmLeafletMap) { mapEl.innerHTML = ''; crmLeafletMap = L.map(mapEl, { zoomControl: false, attributionControl: true, zoomSnap: 0.1, scrollWheelZoom: false, dragging: false, touchZoom: false, doubleClickZoom: false, boxZoom: false, keyboard: false, tap: false }).setView(center, zoom); crmLeafletMap.on('layeradd layerremove', () => setTimeout(candadoDetalle, 0)); }
  else { crmLeafletMap.invalidateSize(); if (crmMapLayer) { crmLeafletMap.removeLayer(crmMapLayer); crmMapLayer = null; } }
  if (crmBarrioLayer) { crmLeafletMap.removeLayer(crmBarrioLayer); crmBarrioLayer = null; }
  mapEl.querySelector('.crm-territory-notice')?.remove();
  return crmLeafletMap;
}
/* La base vial solo se pinta donde la geometría NO va rotada. Bogotá se dibuja
   con rotateGeoJSON90Left (convención del proyecto) y un callejero sin rotar
   debajo contradice los polígonos: Soacha aparecía al norte y Chía al oriente. */
function aplicarBasemap(rotado) {
  if (!crmLeafletMap) return;
  if (rotado) return quitarBasemap();
  ponerBasemap('crm-basemap');
}
/* Dos intensidades: el callejero de una ciudad se lee de frente; el de un
   barrio va de fondo, en gris, para que el color del voto siga mandando. */
function ponerBasemap(clase) {
  const tenue = clase === 'crm-basemap-tenue', opacidad = tenue ? .58 : .72;
  if (crmTileLayer) {
    const cont = crmTileLayer.getContainer();
    cont?.classList.toggle('crm-basemap-tenue', tenue); cont?.classList.toggle('crm-basemap', !tenue);
    crmTileLayer.setOpacity(opacidad);
    return;
  }
  crmTileLayer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, opacity: opacidad, className: clase, attribution: '&copy; OpenStreetMap contributors' }).addTo(crmLeafletMap);
}
function quitarBasemap() { if (crmTileLayer) { crmLeafletMap.removeLayer(crmTileLayer); crmTileLayer = null; } }
/* El encuadre puede NO ser el de la capa: Sumapaz es el 42% de Bogotá y
   metida en el fitBounds deja la ciudad urbana del tamaño de una uña. Se
   dibuja completa —y se desborda del marco, que para eso el contenedor
   recorta— pero el encuadre lo mandan las localidades urbanas. */
/* ⚠️ Leaflet calcula el zoom con el tamaño que TIENE el contenedor en ese
   instante. Si el mapa se arma mientras el panel todavía se está acomodando
   —fuentes, la ficha de la izquierda, el desglose de la derecha—, mide de
   menos y elige un zoom para una caja que ya no existe: al crecer el
   contenedor, la ciudad queda diminuta en un marco enorme. Por eso se mide
   antes, se encuadra, y se vuelve a medir y encuadrar cuando el navegador ya
   acomodó todo. Era lo que dejaba a Cali del tamaño de una uña. */
function encuadrarBounds(bounds, padding = 24) {
  if (!crmLeafletMap || !bounds?.isValid()) return;
  const ajustar = () => { crmLeafletMap?.invalidateSize(); crmLeafletMap?.fitBounds(bounds, { padding: [padding, padding], animate: false }); };
  ajustar();
  setTimeout(ajustar, 60);
  setTimeout(ajustar, 260);
}
function encuadrar(layer, padding = 24) { encuadrarBounds(layer?.getBounds(), padding); }
/* Encuadre por donde ESTÁN los votos. Un municipio como Cali llega hasta los
   Farallones y Bogotá hasta el páramo de Sumapaz: encuadrar por el polígono
   completo deja la ciudad —donde vive la campaña— del tamaño de una uña. Se
   toman las áreas que concentran el 98 % de la votación y se encuadra ahí; el
   resto se sigue dibujando, solo que desbordado. Sin votos, la capa entera. */
function boundsDeVotos(capa, config, votesByArea, excluir, cobertura = .98) {
  const total = Object.values(votesByArea || {}).reduce((s, v) => s + Number(v || 0), 0);
  if (!total) return boundsSin(capa, excluir || (() => false));
  const orden = Object.entries(votesByArea).map(([k, v]) => [k, Number(v) || 0]).sort((a, b) => b[1] - a[1]);
  const dentro = new Set(); let suma = 0;
  for (const [k, v] of orden) { if (suma >= total * cobertura) break; dentro.add(k); suma += v; }
  const b = L.latLngBounds([]);
  capa.eachLayer(item => {
    if (excluir?.(item.feature) || !dentro.has(config.code(item.feature.properties))) return;
    b.extend(item.getBounds ? item.getBounds() : item.getLatLng());
  });
  return b.isValid() ? b : boundsSin(capa, excluir || (() => false));
}
/* Bounds de una capa saltándose los rasgos que `excluir` marque. */
function boundsSin(capa, excluir) {
  const b = L.latLngBounds([]);
  capa.eachLayer(item => { if (!excluir(item.feature)) b.extend(item.getBounds ? item.getBounds() : item.getLatLng()); });
  return b.isValid() ? b : capa.getBounds();
}
function rotateGeoJSON90Left(geoData) {
  const cx = -74.08, cy = 4.65, rotate = ([lon, lat]) => [cx - (lat - cy), cy + (lon - cx)];
  const geometry = geom => geom.type === 'Polygon' ? { ...geom, coordinates: geom.coordinates.map(ring => ring.map(rotate)) } : geom.type === 'MultiPolygon' ? { ...geom, coordinates: geom.coordinates.map(polygon => polygon.map(ring => ring.map(rotate))) } : geom;
  return { ...geoData, features: geoData.features.map(feature => ({ ...feature, geometry: geometry(feature.geometry) })) };
}
function depCodeFromFeature(props) { return String(props?.electoral_id ?? props?.ELECTORAL_ID ?? props?.codigo ?? props?.COD_DEP ?? DEP_CODES[props?.name] ?? '').replace(/^0+/, '') || '0'; }
function depNameFromFeature(props) { return props?.name || props?.nombre || props?.DEP_NOMBRE || props?.dpto_cnmbr || 'Departamento'; }
/* ⚠️ com "000" NO es una comuna: es el marcador de "no aplica" de las
   circunscripciones NACIONALES (comNom "NACIONAL"). Como "000" es truthy,
   `m.com||m.zon` lo prefería y TODA la ciudad caía en una sola clave. En
   Bogotá la zona electoral ES la localidad. El nombre real lo pone el GeoJSON. */
const COM_NOM_NULO = new Set(['NACIONAL', 'NULL', 'SN', '']);
function nombreLocal(mesa) { const n = String(mesa.comNom || '').trim(); return COM_NOM_NULO.has(n.toUpperCase()) ? '' : n; }
/* En Bogotá la ZONA electoral es la localidad, así que sirve de respaldo
   cuando no hay comuna. Las zonas 90 y 98 no: son el censo consolidado y las
   cárceles, que no quedan en ningún barrio. Colándose por el respaldo, la 90
   se pintaba encima del corregimiento de Santa Elena, que en la cartografía
   del DAP también es «90». */
const ZONA_SIN_TERRITORIO = new Set(['90', '98']);
function claveLocal(mesa) {
  const com = String(mesa.com || '').replace(/^0+/, ''), zon = String(mesa.zon || '').padStart(2, '0');
  if (com) return com.padStart(2, '0');
  return ZONA_SIN_TERRITORIO.has(zon) ? '' : zon.replace(/^0+/, '').padStart(2, '0');
}
function completaNombres(geoData, code, name, namesByArea) { (geoData?.features || []).forEach(f => { const k = code(f.properties); if (k && !namesByArea[k]) namesByArea[k] = name(f.properties); }); return namesByArea; }
function electoralPlaceCode(mesa) { return C360Electorado.codigoPuesto(mesa); }
/* El censo por puesto y el perfil del electorado viven en
   candidato-360-electorado.js: los comparte con la página de análisis, que
   tiene que dar exactamente los mismos números que esta tarjeta. */
function puestosPorBarrio() { return C360Electorado.puestos(); }
/* Reparte una meta en proporción a lo observado sin perder un voto por redondeo. */
function distributeVotes(source, target) {
  const total = Object.values(source).reduce((sum, v) => sum + Number(v || 0), 0);
  if (!total || !target) return source;
  const rows = Object.entries(source).map(([key, value]) => { const raw = Number(value) * target / total; return { key, value: Math.floor(raw), rest: raw - Math.floor(raw) }; });
  let pending = target - rows.reduce((sum, row) => sum + row.value, 0);
  rows.sort((a, b) => b.rest - a.rest).slice(0, pending).forEach(row => row.value++);
  return Object.fromEntries(rows.map(row => [row.key, row.value]));
}
function projectedVotesByArea() {
  const goal = Number(String($('crmVoteNumber').textContent || '').replace(/\D/g, ''));
  /* Con salto de corporación la meta no puede caer donde cayó el historial:
     se reparte con la huella del destino (sección 8 ter). Si el salto no se
     pudo preparar, se conserva el reparto proporcional de siempre. */
  MUDANZA_LOCAL = null;
  if (crmMapState?.censo) return proyeccionTerritorio(crmMapState, goal);
  const salto = crmMapState ? repartoSaltoCiudad(crmMapState, goal) : null;
  if (salto) return salto;
  return (crmMapState ? repartoMudanzaLocal(crmMapState, goal) : null) || distributeVotes(crmMapState?.votesByArea || {}, goal);
}
function renderMapBreakdown(votesByArea, namesByArea, title) {
  const rows = Object.entries(votesByArea).map(([key, value]) => ({ key, name: namesByArea[key] || key, value: Number(value) || 0 })).filter(row => row.value > 0).sort((a, b) => b.value - a.value), max = Math.max(1, ...rows.map(row => row.value));
  $('crmBreakdown').innerHTML = `<h4 id="crmBreakdownTitle">${title}</h4>` + (rows.length ? rows.map(row => `<button class="crm-breakdown-item" type="button" data-area-key="${escHtml(row.key)}" onclick="openMapAreaFromBreakdown(this.dataset.areaKey)"><span class="crm-breakdown-row"><b>${escHtml(NOMBRE_BONITO(row.name))}</b><span>${row.value.toLocaleString('es-CO')}</span></span><span class="crm-breakdown-bar"><i style="width:${Math.max(3, Math.round(row.value / max * 100))}%"></i></span></button>`).join('') : '<p class="helper">No hay votos desagregados disponibles.</p>');
  setTimeout(candadoDetalle, 0);
}
/* TOTAL / PROYECTADO: solo cuando la candidatura tiene UNA elección; con varias
   mandan los toggles por año (que también traen PROYECTADO). */
function ensureCRMMapToggles() {
  if (electionViewRecords.length >= 2) return;
  const head = $('crmMapTitle').closest('.panel-head'); if (!head || $('crmMapToggles')) return;
  head.insertAdjacentHTML('beforeend', '<div class="map-toggles" id="crmMapToggles"><button class="map-toggle active" type="button" data-mode="total">TOTAL</button><button class="map-toggle" type="button" data-mode="proyectado">PROYECTADO</button></div>');
  $('crmMapToggles').addEventListener('click', event => { const button = event.target.closest('[data-mode]'); if (button) { crmMapMode = button.dataset.mode; refreshCRMMapMode(); } });
}
/* «¿Dónde estuvo su votación?» es historia; «Proyectado» es lo contrario: lo
   que falta por conseguir. Mantener el mismo título hacía leer la meta como si
   fuera votación pasada. */
function tituloMapa(modo = crmMapMode) {
  const state = crmMapState; if (!state) return '';
  const donde = NOMBRE_BONITO(state.tituloLugar || '');
  if (state.censo) return modo === 'proyectado' ? `¿Dónde buscar los votos${donde ? ` en ${donde}` : ''}?` : `¿Dónde vota la gente${donde ? ` en ${donde}` : ''}?`;
  return modo === 'proyectado' ? `¿Dónde debería estar su votación${donde ? ` en ${donde}` : ''}?` : `¿Dónde estuvo su votación${donde ? ` en ${donde}` : ''}?`;
}
function refreshCRMMapMode() {
  const state = crmMapState, saltoDeptal = SALTO_ACTUAL?.tipo?.unidad === 'municipio';
  /* Sin estado NO hay mapa histórico que repintar… salvo en el salto a
     departamento, donde el historial puede estar entero fuera del destino (un
     edil de Bogotá que se lanza a la Gobernación de Cundinamarca): ahí el
     mapa es el del territorio de campaña, sin estado, y «Proyectado» tiene
     que poder pintar igual los municipios con la meta repartida. */
  if (DESTINO_FUERA && !saltoDeptal && !pintandoDestino) {
    if (crmMapMode === 'proyectado' && !EN_DESTINO) { pintarDestino(); return; }
    if (crmMapMode !== 'proyectado' && EN_DESTINO) { loadHistoricalMap(crmCandidate); return; }
  }
  if (!saltoDeptal && (!state || !crmMapLayer)) return;
  if (state?.tituloLugar) $('crmMapTitle').textContent = tituloMapa();
  /* Salto a escala de departamento: «Proyectado» pinta los municipios del
     destino; «Total» devuelve el mapa histórico (o el territorio de campaña). */
  if (saltoDeptal) {
    const goal = Number(String($('crmVoteNumber').textContent || '').replace(/\D/g, ''));
    document.querySelectorAll('#crmMapToggles .map-toggle[data-mode]').forEach(b => b.classList.toggle('active', b.dataset.mode === crmMapMode));
    if (crmMapMode === 'proyectado') { if (goal) pintarProyeccionDepartamental(goal); return; }
    if (PROYECCION_DEPTAL || state?.geometriaDestino) { loadHistoricalMap(crmCandidate); return; }
    if (!state) return;
  }
  const projected = projectedVotesByArea(), values = crmMapMode === 'proyectado' ? projected : state.votesByArea, max = Math.max(1, ...Object.values(values));
  renderMapBreakdown(values, state.namesByArea, crmMapMode === 'proyectado' ? `Meta proyectada por ${state.config.title}` : `${state.censo ? 'Censo electoral' : 'Votos'} por ${state.config.title}`);
  if (state.censo) $('crmMapVotes').textContent = crmMapMode === 'proyectado' ? `${Object.values(projected).reduce((t, v) => t + Number(v || 0), 0).toLocaleString('es-CO')} votos · meta` : `${Number(state.total || 0).toLocaleString('es-CO')} electores`;
  document.querySelectorAll('#crmMapToggles .map-toggle[data-mode]').forEach(b => b.classList.toggle('active', b.dataset.mode === crmMapMode));
  crmMapLayer.eachLayer(layer => {
    const key = state.config.code(layer.feature.properties), observed = Number(state.votesByArea[key] || 0), proj = Number(projected[key] || 0), value = Number(values[key] || 0);
    layer.setStyle({ fillColor: MAP_COLOR(value / max), fillOpacity: key === state.targetKey ? .78 : .38 });
    layer.bindTooltip(`<strong>${NOMBRE_BONITO(state.config.name(layer.feature.properties))}</strong><br>${(crmMapMode === 'proyectado' ? proj : observed).toLocaleString('es-CO')} ${crmMapMode === 'proyectado' ? 'votos proyectados' : state.censo ? 'personas habilitadas' : 'votos'}`, { sticky: true });
  });
  if (state.censo) {
    $('crmMapNote').textContent = (crmMapMode === 'proyectado' ? notaProyeccionTerritorio(state)
      : `${NOMBRE_BONITO(state.tituloLugar)} es el territorio de su candidatura y usted todavía no tiene votos acá: el color es el censo electoral, cuánta gente puede votar en cada ${state.config.title}.`) + ` Haga clic en una ${state.config.title} para ver sus barrios.` + notaColorPartido();
    if (state.focusKey) renderBarriosForArea(state.focusKey);
    return;
  }
  $('crmMapNote').textContent = (crmMapMode === 'proyectado' ? (SALTO_ACTUAL?.base ? notaSalto(SALTO_ACTUAL.base) + ` Haga clic en una ${state.config.title} para ver su detalle.` : MUDANZA_LOCAL ? `A la Junta administradora local se entra por una sola ${state.config.title}: la meta completa se juega en ${NOMBRE_BONITO(MUDANZA_LOCAL)}, no en la ${state.config.title} donde votó antes.` : `Meta total distribuida proporcionalmente a la votación histórica. Haga clic en una ${state.config.title} para ver su detalle.`) : `Votación total histórica. Haga clic en una ${state.config.title} para ver el detalle y su meta proyectada.`) + (crmMapMode === 'proyectado' && MUDANZA_LOCAL ? '' : notaRecorte());
  if (state.focusKey) renderBarriosForArea(state.focusKey);
}
function showCRMMapDetail(layer) { const state = crmMapState; if (!state) return; layer.openTooltip(); renderBarriosForArea(state.config.code(layer.feature.properties)); setMapLevel('barrio'); }
function openMapAreaFromBreakdown(key) {
  const state = crmMapState; if (!state || !crmMapLayer) return;
  const layer = crmMapLayer.getLayers().find(item => state.config.code(item.feature.properties) === key);
  if (layer) { crmLeafletMap.fitBounds(layer.getBounds(), { padding: [30, 30], animate: false }); showCRMMapDetail(layer); }
}

/* RECORTE TERRITORIAL: una candidatura anterior puede ser de MAYOR alcance que
   la corporación a la que se aspira (Senado 2014 → Alcaldía de Bogotá). El mapa
   muestra SOLO los votos dentro del territorio objetivo, por CÓDIGO electoral
   (comparar «CALI» con includes() casa «CALIMA»), y lo omitido se declara. */
let recorteActivo = null;
const datosCandidaturaCache = new Map();
function alcanceObjetivo() {
  const target = currentTargetTerritory(); if (!target?.corporation) return null;
  const departamento = String($('campaignDepartment').value || '').replace(/^0+/, '');
  /* La JAL se elige por LOCALIDAD, no por municipio. Sin este nivel, un edil
     de Teusaquillo que se lanza por Tunjuelito «seguía en alcance» —las dos
     son Bogotá— y el mapa proyectaba toda su meta en Teusaquillo, o sea en el
     territorio que acaba de dejar y donde su votación anterior no cuenta. */
  if (target.corporation === 'jal' && target.locality) return { tipo: 'localidad', departamento, municipio: codigoMunicipioObjetivo(), municipioNombre: target.municipality, localidad: target.locality, departamentoNombre: target.department };
  if (CORP_MUNICIPAL.includes(target.corporation) && target.municipality) return { tipo: 'municipio', departamento, municipio: codigoMunicipioObjetivo(), municipioNombre: target.municipality, departamentoNombre: target.department };
  if (CORP_DEPARTAMENTAL.includes(target.corporation) && target.department) return { tipo: 'departamento', departamento, departamentoNombre: target.department };
  return null;
}
function codigoMunicipioObjetivo() {
  const geo = municipalitiesByDepartment[`crm-${$('campaignDepartment').value || ''}`], nombre = normalizedText($('campaignMunicipality').value || '');
  const feature = geo?.features?.find(f => normalizedText(f.properties?.mpio_cnmbr || '') === nombre);
  const codigo = feature?.properties?.mun_elec ?? feature?.properties?.mun_electoral;
  return codigo === undefined ? '' : String(codigo).replace(/^0+/, '');
}
function mesaEnAlcance(mesa, alcance) {
  const dep = String(mesa.dep || '').replace(/^0+/, ''), mun = String(mesa.mun || '').replace(/^0+/, '');
  if (alcance.departamento && dep && dep !== alcance.departamento) return false;
  if (alcance.tipo === 'departamento') return alcance.departamento ? Boolean(dep) : normalizedText(mesa.depNom || '') === alcance.departamentoNombre;
  const enMunicipio = alcance.municipio ? mun === alcance.municipio : normalizedText(mesa.munNom || '') === alcance.municipioNombre;
  if (alcance.tipo !== 'localidad') return enMunicipio;
  /* La localidad de la mesa viene como «13LOCALIDAD 13 TEUSAQUILLO» o
     «14COMUNA 14 EL POBLADO»: se compara por el nombre pelado. */
  if (!enMunicipio) return false;
  const suya = normalizedText(cortoLocal(nombreLocal(mesa))), objetivo = normalizedText(cortoLocal(alcance.localidad));
  return Boolean(suya) && Boolean(objetivo) && suya === objetivo;
}
async function datosCandidatura(candidate) {
  const url = candidate?.dataUrl || '';
  /* Sin archivo no hay nada que pedir: `fetch('')` se trae la página actual y
     el error aparece como si la fuente estuviera caída. */
  if (!url) throw new Error('Candidatura sin archivo de datos');
  if (!datosCandidaturaCache.has(url)) datosCandidaturaCache.set(url, fetch(url).then(r => r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status))).catch(error => { datosCandidaturaCache.delete(url); throw error; }));
  const data = await datosCandidaturaCache.get(url), alcance = alcanceObjetivo(), mesas = data.mesas || [];
  if (!alcance) { recorteActivo = null; return { ...data, mesas, recorte: null }; }
  const dentro = mesas.filter(mesa => mesaEnAlcance(mesa, alcance)), votos = m => m.reduce((sum, mesa) => sum + Number(mesa.v || 0), 0);
  recorteActivo = { alcance, mesasFuera: mesas.length - dentro.length, votosFuera: votos(mesas) - votos(dentro), votosDentro: votos(dentro), sinVotos: mesas.length > 0 && !votos(dentro) };
  /* Un representante de Antioquia que se lanza al Concejo de Bogotá no tiene
     un solo voto en Bogotá: recortar dejaba un mapa de Bogotá vacío con la
     nota «quedaron por fuera 37.111 votos». Sin votos dentro se pinta el
     historial completo, donde sí está su votación. */
  return { ...data, mesas: recorteActivo.sinVotos ? mesas : dentro, recorte: recorteActivo };
}
function lugarDelAlcance(recorte = recorteActivo) {
  const tipo = recorte?.alcance?.tipo;
  if (tipo === 'localidad') return NOMBRE_BONITO($('campaignLocality').value || '') || 'la localidad';
  if (tipo === 'municipio') return NOMBRE_BONITO($('campaignMunicipality').value || '') || 'el municipio';
  return $('campaignDepartment').options[$('campaignDepartment').selectedIndex]?.text || 'el departamento';
}
function notaRecorte(recorte = recorteActivo) {
  if (!recorte || !recorte.mesasFuera) return '';
  const donde = lugarDelAlcance(recorte);
  if (recorte.sinVotos) return ` Su votación histórica no tiene mesas en ${donde}, así que «Total» la muestra donde estuvo; abra «Proyectado» para ver ${donde}, donde compite ahora.`;
  return ` Se muestran solo los votos en ${donde}: quedaron por fuera ${recorte.votosFuera.toLocaleString('es-CO')} votos en ${recorte.mesasFuera.toLocaleString('es-CO')} mesas de otros territorios, que no cuentan para esta candidatura.`;
}
/* ¿El historial tiene votos dentro del territorio objetivo? Decide si el
   mapa va por el territorio nuevo (Bogotá, Cali) o por donde estuvo la votación. */
async function historialEnObjetivo(candidate) {
  try { return !(await datosCandidatura(candidate)).recorte?.sinVotos; } catch (e) { return true; }
}
/* Pero mudarse de LOCALIDAD no es mudarse de ciudad. Un edil que pasa de
   Teusaquillo a Tunjuelito sigue en Bogotá: su votación anterior existe, está
   dibujada en este mismo mapa y «Total» tiene que poder mostrarla. Cambiar el
   mapa entero por el territorio nuevo —como se hace cuando alguien de La Ceja
   se lanza al Concejo de Bogotá— le borraba el historial de la pantalla.
   La pregunta para eso es la CIUDAD, un nivel por encima del alcance. */
async function historialEnCiudad(candidate) {
  const alcance = alcanceObjetivo(); if (!alcance) return true;
  if (alcance.tipo !== 'localidad') return historialEnObjetivo(candidate);
  const ciudad = { ...alcance, tipo: 'municipio' };
  try {
    const mesas = (await datosCandidatura(candidate)).mesas || [];
    return mesas.some(mesa => mesaEnAlcance(mesa, ciudad) && Number(mesa.v || 0) > 0);
  } catch (e) { return true; }
}

/* Mapa genérico: por departamento (nacional), o el municipio recortado del
   departamento cuando la evidencia pertenece a un solo municipio. */
/* El municipio del mapa genérico —uno sin capa de comunas, como La Ceja—
   para que el nivel «Puestos» sepa qué mesas pintar y cómo se llama. */
let MAPA_MUNICIPAL = null;
async function renderGenericMap(candidate) {
  crmMapState = null; MAPA_MUNICIPAL = null;
  fijarRampaMapa(partidoVigente(), candidate?.nombre);
  const candidateData = await datosCandidatura(candidate), mesas = candidateData.mesas || [], total = mesas.reduce((sum, m) => sum + Number(m.v || 0), 0) || Number(candidate.votos) || 0;
  const municipalityCodes = [...new Set(mesas.map(m => String(m.mun || '').replace(/^0+/, '')).filter(Boolean))];
  let geoData, votesByArea = {}, namesByArea = {}, featureCode, featureName, detailNote, breakdownTitle;
  if (municipalityCodes.length === 1 && mesas[0]?.dep) {
    const depCode = String(mesas[0].dep).padStart(2, '0'), municipalGeo = await fetchJSON(`${S3}/mapas-2026/Departamentos-mps/${depCode}.json`), municipalCode = municipalityCodes[0];
    geoData = { ...municipalGeo, features: municipalGeo.features.filter(f => String(f.properties?.mun_elec || f.properties?.mun_electoral || '').replace(/^0+/, '') === municipalCode) };
    if (!geoData.features.length) throw new Error('Municipio histórico sin geometría');
    const municipalName = mesas.find(m => m.munNom)?.munNom || candidate.circunscripcion || 'municipio';
    votesByArea = { [municipalCode]: total }; namesByArea = { [municipalCode]: municipalName };
    MAPA_MUNICIPAL = { mesas, nombre: municipalName };
    featureCode = p => String(p.mun_elec || p.mun_electoral || '').replace(/^0+/, ''); featureName = p => p.mpio_cnmbr || municipalName;
    $('crmMapTitle').textContent = `¿Dónde estuvo su votación en ${NOMBRE_BONITO(municipalName)}?`; detailNote = 'Votación histórica concentrada en este municipio; la nueva campaña puede ubicarse en otro territorio.'; breakdownTitle = 'Votos en el municipio';
  } else {
    geoData = await fetchJSON(`${S3}/mapas-2026/DEPARTAMENTOS2.json`);
    mesas.forEach(m => { const key = String(m.dep || '').replace(/^0+/, '') || '0'; votesByArea[key] = (votesByArea[key] || 0) + Number(m.v || 0); namesByArea[key] = m.depNom || `Departamento ${key}`; });
    featureCode = depCodeFromFeature; featureName = depNameFromFeature;
    $('crmMapTitle').textContent = '¿Dónde estuvo su votación?'; detailNote = 'Distribución por departamento en la candidatura histórica. El territorio nuevo se aplica a la estrategia de 2027, no altera esta evidencia.'; breakdownTitle = 'Votos por departamento';
  }
  completaNombres(geoData, featureCode, featureName, namesByArea);
  const max = Math.max(1, ...Object.values(votesByArea));
  renderMapBreakdown(votesByArea, namesByArea, breakdownTitle);
  crearMapa([4.6, -74.1], 5); aplicarBasemap(false);
  crmMapLayer = L.geoJSON(geoData, { style: f => ({ color: '#fff', weight: 1, fillColor: MAP_COLOR((votesByArea[featureCode(f.properties)] || 0) / max), fillOpacity: .94 }), onEachFeature: (f, layer) => { layer._vitrinaCode = featureCode(f.properties); layer.bindTooltip(`<strong>${NOMBRE_BONITO(featureName(f.properties))}</strong><br>${(votesByArea[featureCode(f.properties)] || 0).toLocaleString('es-CO')} votos`, { sticky: true }); } }).addTo(crmLeafletMap);
  encuadrar(crmMapLayer, 15);
  $('crmMapVotes').textContent = `${total.toLocaleString('es-CO')} votos`; $('crmMapNote').textContent = detailNote + notaRecorte() + notaColorPartido();
}
/* Las JAL se leen a escala de comuna/localidad con las capas de Análisis de
   Candidato. */
/* Sumapaz (localidad 20) es rural y enorme; se pinta, pero no encuadra. */
const ES_SUMAPAZ = f => String(f?.properties?.LocCodigo || '') === '20';
/* Bogotá se encuadra por su PERÍMETRO URBANO, no por sus localidades. Usme
   baja hasta 4,27 y Ciudad Bolívar hasta 4,38 de latitud, casi todo páramo y
   vereda; encuadrar por el polígono completo estiraba el marco hacia el sur y
   dejaba a Kennedy y a Bosa —donde vive la mitad de los votos— del tamaño de
   una uña. La ventana va de Suba (4,84) al norte urbano de Usme y Ciudad
   Bolívar (4,49), y de Bosa (-74,22) a los cerros (-73,99). Lo que queda por
   fuera —el sur de Usme y Ciudad Bolívar, Sumapaz— se sigue dibujando,
   desbordado por la derecha del mapa rotado. En coordenadas reales; se rota
   igual que la capa. */
/* La ventana va de la punta de Usaquén (norte) hasta pasada la parte rural
   de Usme y Ciudad Bolívar (sur), con una tajada de Sumapaz: antes cortaba
   en 4,49 y lo rural se dibujaba FUERA del encuadre, hacia la derecha, con la
   holgura vacía al norte —el mapa se veía tirado a la derecha—. Con la
   rotación, norte es izquierda y sur es derecha; la proporción 0,615 × 0,305
   es la de la caja del mapa, así que no sobra a ningún lado. */
const BOGOTA_VENTANA_URBANA = { sur: 4.23, norte: 4.845, oeste: -74.28, este: -73.975 };
function encuadreBogota() {
  const { sur, norte, oeste, este } = BOGOTA_VENTANA_URBANA;
  const esquinas = [[oeste, sur], [este, sur], [oeste, norte], [este, norte]].map(c => rotateGeoJSON90Left({ features: [{ geometry: { type: 'Polygon', coordinates: [[c]] } }] }).features[0].geometry.coordinates[0][0]);
  return L.latLngBounds(esquinas.map(([lon, lat]) => [lat, lon]));
}
/* Una ventana fija (sur/norte/oeste/este) como bounds de Leaflet. */
function ventanaBounds({ sur, norte, oeste, este }) { return L.latLngBounds([[sur, oeste], [norte, este]]); }
/* Cartagena se lee a DOS escalas, y las dos son legítimas:
   · 3 LOCALIDADES — la circunscripción de sus Juntas Administradoras Locales.
   · 16 Unidades Comuneras de Gobierno (15 urbanas + la 20, rural e insular),
     como el Distrito parte la ciudad y la escala a la que un concejo o una
     alcaldía leen su votación. No tienen nombre oficial; la capa las rotula
     con sus barrios de más electores (build_cartagena_ucg.py).
   ⚠️ El georef solo le pone las 3 localidades, así que la unidad de la mesa
   sale del diccionario de puestos (`prepare` lo carga antes de agregar): leer
   la UCG de `com` mandaría la ciudad entera a tres unidades de dieciséis.
   ⚠️ Ventana urbana fija por lo mismo que Bogotá: la UCG 20 llega hasta Isla
   Fuerte, 100 km al sur. Las islas siguen dibujadas; hay que alejar. */
const numeroDe = s => String(s || '').match(/\d+/)?.[0]?.padStart(2, '0') || '';
const CARTAGENA_VENTANA = { sur: 10.275, norte: 10.47, oeste: -75.58, este: -75.415 };
const cartagenaDic = () => window.Candidato360CartagenaPuestoBarrio;
const CARTAGENA_CAPAS = {
  localidad: { clave: 'localidad', match: ['CARTAGENA'], path: 'CARTAGENA-LOCALIDADES.json', title: 'localidad', nivel: 'Localidad', code: p => String(p.CODIGO || ''), name: p => p.NOMBRE || 'Localidad',
    prepare: () => cartagenaPuestoBarrio(), nombreDeCapa: true, mesaKey: m => cartagenaDic()?.[electoralPlaceCode(m)]?.loc || '',
    unidadBarrio: p => p.loc || '', unidadEsArchivo: false, ventana: CARTAGENA_VENTANA,
    /* El formulario trae «LOC. 1 HISTORICA Y DEL CARIBE» y el polígono
       «Localidad 1 · Histórica y del Caribe Norte»: casan por número. */
    casaLocalidad: (p, elegida) => Boolean(numeroDe(elegida)) && numeroDe(p.CODIGO) === numeroDe(elegida) },
  ucg: { clave: 'ucg', match: ['CARTAGENA'], path: 'CARTAGENA-UCG.json', title: 'unidad comunera', nivel: 'UCG', code: p => String(p.CODIGO || ''), name: p => p.NOMBRE || 'UCG',
    prepare: () => cartagenaPuestoBarrio(), nombreDeCapa: true, mesaKey: m => cartagenaDic()?.[electoralPlaceCode(m)]?.comuna || '',
    unidadBarrio: p => p.comuna || '', ventana: CARTAGENA_VENTANA },
};
Object.values(CARTAGENA_CAPAS).forEach(c => { c.familia = CARTAGENA_CAPAS; });
const CITY_JAL_LAYERS = [
  { match: ['BOGOTA'], path: 'BOG-LOCALIDADX.json', title: 'localidad', code: p => String(p.LocCodigo || '').padStart(2, '0'), name: p => p.LocNombre || 'Localidad', rotate: true },
  /* La Registraduría numera los corregimientos de Medellín del 17 al 21 y la
     cartografía del DAP los numera 50, 60, 70, 80 y 90. Sin esta tabla los
     votos de Altavista, San Antonio de Prado, Palmitas, San Cristóbal y Santa
     Elena no caían en ningún polígono. */
  { match: ['MEDELLIN'], path: 'MEDELLINX.json', title: 'comuna', code: p => String(p.CODIGO || '').padStart(2, '0'), name: p => p.NOMBRE || p.IDENTIFICACION || 'Comuna',
    mesaKey: m => { const k = claveLocal(m); return ({ '17': '70', '18': '80', '19': '50', '20': '60', '21': '90' })[k] || k; } },
  { match: ['CALI'], path: 'CALIX.json', title: 'comuna', code: p => String(p.comuna || '').padStart(2, '0'), name: p => p.nombre || 'Comuna' },
  { match: ['PEREIRA'], path: 'PEREIRAX.json', title: 'comuna', code: p => normalizedText(p.Comuna), name: p => p.Comuna || 'Comuna', mesaKey: m => normalizedText(String(m.comNom || '').replace(/^\d+\s*COMUNA\s*/i, '')) },
  { match: ['IBAGUE'], path: 'IBAGUEX.json', title: 'comuna', code: p => String(p.COMUNAS || '').replace(/\D/g, '').padStart(2, '0'), name: p => p.COMUNAS || 'Comuna' },
  { match: ['BARRANQUILLA'], path: 'BARRANQUILLAX.json', title: 'localidad', code: p => ({ 4: '01', 2: '02', 1: '03', 3: '04', 5: '05' })[Number(p.id)] || '', name: p => p.nombre || 'Localidad' },
  { match: ['MONTERIA'], path: 'MONTERIAX.json', title: 'comuna', code: p => String(p.CC_COMUNA || '').padStart(2, '0'), name: p => p.NMG || 'Comuna' },
  CARTAGENA_CAPAS.ucg,
  { match: ['MANIZALES'], path: 'MANIZALESX.json', title: 'comuna', code: p => String(p.ID_COMUNA || '').padStart(2, '0'), name: p => p.NOMBRES_CO || 'Comuna' },
  /* Las otras seis capitales con cartografía por comuna (las mismas de
     veleta.html). El código de comuna viene escrito de seis maneras distintas
     —número suelto, «COMUNA 2», «Comuna 5»—, así que se saca a dígitos. */
  { match: ['BUCARAMANGA'], path: 'BUCARAMANGAX.json', title: 'comuna', code: p => String(p.COD_COMUNA || '').padStart(2, '0'), name: p => p.NOMBRE_COM || 'Comuna' },
  /* La capa de Cúcuta trae diez polígonos numerados 0-5 y 7-10: al que le
     falta número es la comuna 6, la única ausente de una ciudad que tiene
     diez. Sin repararlo, uno de cada doce votos no caía en ningún lado. */
  { match: ['CUCUTA'], path: 'CUCUTAX.json', title: 'comuna', code: p => { const n = String(p.Comuna ?? '').replace(/\D/g, ''); return (!n || n === '0' ? '6' : n).padStart(2, '0'); }, name: p => `Comuna ${Number(String(p.Comuna ?? '').replace(/\D/g, '')) || 6}` },
  { match: ['NEIVA'], path: 'NEIVAX.json', title: 'comuna', code: p => String(p.comuna || '').replace(/\D/g, '').padStart(2, '0'), name: p => String(p.comuna || 'Comuna').replace(/\s+/g, ' ') },
  { match: ['POPAYAN'], path: 'POPAYANX.json', title: 'comuna', code: p => String(p.COMUNAS || p.ACAD_TEXT || '').replace(/\D/g, '').padStart(2, '0'), name: p => p.COMUNAS || 'Comuna' },
  { match: ['SINCELEJO'], path: 'SINCELEJOX.json', title: 'comuna', code: p => String(p.Nombre || '').replace(/\D/g, '').padStart(2, '0'), name: p => p.Nombre || 'Comuna' },
  { match: ['VILLAVICENCIO'], path: 'VILLAVICENCIOX.json', title: 'comuna', code: p => String(p.Comuna || '').replace(/\D/g, '').padStart(2, '0'), name: p => p.Comuna || 'Comuna' }
];
/* Una ciudad con varias escalas (Cartagena) abre en la que la persona eligió
   en el mapa; si no ha elegido, en la de su corporación: la JAL se elige por
   localidad, el Concejo y la Alcaldía se leen por UCG. */
const CAPA_ELEGIDA = {};
function cityLayerFor(nombre, { jal = false } = {}) {
  const city = normalizedText(nombre);
  const base = CITY_JAL_LAYERS.find(item => item.match.some(name => city.includes(name))) || null;
  if (!base?.familia) return base;
  return base.familia[CAPA_ELEGIDA[base.match[0]]] || (jal ? base.familia.localidad : null) || base;
}
const esJalCandidatura = candidate => String(candidate?.corp || '').toUpperCase().startsWith('JAL') || currentTargetTerritory()?.corporation === 'jal';
/* Pinta una ciudad por comuna/localidad con el estado compartido de los mapas
   de ciudad (toggles, detalle por barrio, niveles). */
function pintarCiudad({ geoData, config, mesas, total, votesByArea, namesByArea, targetKey, city, rotate, lugar, title, note, center, zoom, fitTarget, fueraDelEncuadre, encuadre, candidato }) {
  completaNombres(geoData, config.code, config.name, namesByArea);
  const max = Math.max(1, ...Object.values(votesByArea));
  crmMapMode = 'total';
  const m0 = mesas[0] || {};
  fijarRampaMapa(partidoVigente(), crmCandidate?.nombre);
  crmMapState = { city, ciudad: `${String(m0.dep || '').padStart(2, '0')}${String(m0.mun || '').padStart(3, '0')}`, config, geoData, votesByArea, namesByArea, mesas, total, max, targetKey, focusKey: null, rotado: Boolean(rotate), tituloLugar: lugar || '', encuadre: encuadre || null, fueraDelEncuadre: fueraDelEncuadre || null, candidato: candidato || null };
  $('crmMapTitle').textContent = lugar ? tituloMapa('total') : title; ensureCRMMapToggles();
  crearMapa(center || [4.6, -74.1], zoom || 5); aplicarBasemap(Boolean(rotate));
  let targetLayer = null;
  crmMapLayer = L.geoJSON(geoData, {
    style: f => { const key = config.code(f.properties); return { color: '#fff', weight: key === targetKey ? 2 : 1, fillColor: MAP_COLOR((votesByArea[key] || 0) / max), fillOpacity: key === targetKey ? .78 : .42 }; },
    onEachFeature: (f, layer) => { layer._vitrinaCode = config.code(f.properties); if (config.code(f.properties) === targetKey) targetLayer = layer; layer.on('click', () => showCRMMapDetail(layer)); }
  }).addTo(crmLeafletMap);
  refreshCRMMapMode();
  encuadrarBounds(fitTarget && targetLayer ? targetLayer.getBounds() : encuadre || boundsDeVotos(crmMapLayer, config, votesByArea, fueraDelEncuadre), 24);
  $('crmMapVotes').textContent = `${total.toLocaleString('es-CO')} votos`;
  $('crmMapNote').textContent = note + notaRecorte() + notaColorPartido();
}
function agregarPorArea(mesas, keyFn) { const votesByArea = {}, namesByArea = {}; mesas.forEach(m => { const key = keyFn(m); if (!key) return; votesByArea[key] = (votesByArea[key] || 0) + Number(m.v || 0); namesByArea[key] = nombreLocal(m) || namesByArea[key]; }); return { votesByArea, namesByArea }; }
/* ¿Toda la votación cabe en UNA ciudad con capa de comunas? Entonces el mapa
   es esa ciudad, sea JAL, Concejo o Alcaldía. Antes solo la JAL entraba acá y
   un concejal de Medellín veía el municipio entero como una sola mancha, sin
   comunas ni barrios, cuando la cartografía estaba a un clic. */
async function ciudadDeLaCandidatura(candidate) {
  const mesas = (await datosCandidatura(candidate)).mesas || [];
  const municipios = new Set(mesas.filter(m => Number(m.v || 0)).map(m => `${m.dep}-${m.mun}`));
  if (municipios.size !== 1) return null;
  const config = cityLayerFor(mesas.find(m => m.munNom)?.munNom || candidate.circunscripcion, { jal: esJalCandidatura(candidate) });
  return config ? { config, mesas } : null;
}
async function renderCiudadMap(candidate, ciudad) {
  const { config, mesas } = ciudad || await ciudadDeLaCandidatura(candidate) || {};
  if (!config) throw new Error('Ciudad sin capa local');
  /* Una ciudad cuya unidad no está en la mesa (Cartagena) carga su diccionario
     ANTES de agregar: con `mesaKey` sin dato, los votos no caen en ninguna
     unidad y el mapa sale vacío sin dar error. */
  if (config.prepare) await config.prepare();
  let geoData = await fetchJSON(`${S3}/mapas-2026/Ciudades-COM-LOC/${config.path}`); if (config.rotate) geoData = rotateGeoJSON90Left(geoData);
  const { votesByArea, namesByArea } = agregarPorArea(mesas, m => config.mesaKey ? config.mesaKey(m) : claveLocal(m));
  /* ⚠️ En Cartagena el nombre NO puede salir de la mesa: el georef le pone la
     LOCALIDAD («Loc. 2 la Virgen y Turística») y el mapa dibuja UCG, así que
     el desglose rotulaba cinco unidades distintas con el mismo nombre. Donde
     la unidad viene de un archivo externo manda el nombre del polígono. */
  if (config.nombreDeCapa) Object.keys(namesByArea).forEach(k => delete namesByArea[k]);
  /* La Registraduría escribe la comuna como «06COMUNA 6 DOCE DE OCTUBRE»: el
     código pegado al nombre. En el desglose sobra. */
  Object.keys(namesByArea).forEach(k => { if (namesByArea[k]) namesByArea[k] = String(namesByArea[k]).replace(/^\d+\s*/, ''); else delete namesByArea[k]; });
  const total = mesas.reduce((sum, m) => sum + Number(m.v || 0), 0) || Number(candidate.votos) || 0, targetKey = Object.entries(votesByArea).sort((a, b) => b[1] - a[1])[0]?.[0];
  const esJal = String(candidate.corp || '').toUpperCase().startsWith('JAL'), lugar = mesas.find(m => m.munNom)?.munNom || '';
  pintarCiudad({ geoData, config, mesas, total, votesByArea, namesByArea, targetKey, city: normalizedText(lugar), rotate: config.rotate, lugar, candidato: candidate,
    encuadre: config.ventana ? ventanaBounds(config.ventana) : null,
    note: esJal
      ? `Distribución por ${config.title} de su candidatura JAL. Haga clic en una ${config.title} para ver el detalle por barrio.`
      : `Distribución por ${config.title} en ${lugar || 'la ciudad'}. Haga clic en una ${config.title} para ver el detalle por barrio.`,
    fitTarget: esJal });
}
async function renderBogotaCampaignMap(candidate) {
  const data = await datosCandidatura(candidate), mesas = data.mesas || [];
  const geoData = rotateGeoJSON90Left(await fetchJSON(`${S3}/mapas-2026/Ciudades-COM-LOC/BOG-LOCALIDADX.json`));
  const config = { title: 'localidad', code: p => String(p.LocCodigo || '').padStart(2, '0'), name: p => p.LocNombre || 'Localidad' };
  const { votesByArea, namesByArea } = agregarPorArea(mesas, claveLocal);
  const total = mesas.reduce((sum, m) => sum + Number(m.v || 0), 0) || Number(candidate.votos) || 0;
  pintarCiudad({ geoData, config, mesas, total, votesByArea, namesByArea, targetKey: null, city: 'BOGOTA', rotate: true, fueraDelEncuadre: ES_SUMAPAZ, encuadre: encuadreBogota(), lugar: 'Bogotá', note: 'El mapa encuadra el perímetro urbano, que es donde están los votos; el sur rural de Usme y Ciudad Bolívar y Sumapaz se dibujan aunque se salgan del marco. Seleccione una localidad para abrir el desglose por barrio.' });
}
async function renderCaliCampaignMap(candidate) {
  const data = await datosCandidatura(candidate), mesas = data.mesas || [], geoData = await fetchJSON(`${S3}/mapas-2026/Ciudades-COM-LOC/CALIX.json`);
  const config = { title: 'comuna', code: p => String(p.comuna || '').padStart(2, '0'), name: p => p.nombre || `Comuna ${p.comuna}` };
  const votesByArea = {}, namesByArea = {};
  mesas.forEach(m => { const key = claveLocal(m); votesByArea[key] = (votesByArea[key] || 0) + Number(m.v || 0); namesByArea[key] = (nombreLocal(m) || namesByArea[key] || `Comuna ${Number(key)}`).replace(/^\d+\s*COMUNA\s*/i, 'Comuna '); });
  const total = mesas.reduce((sum, m) => sum + Number(m.v || 0), 0) || Number(candidate.votos) || 0, targetKey = Object.entries(votesByArea).sort((a, b) => b[1] - a[1])[0]?.[0];
  pintarCiudad({ geoData, config, mesas, total, votesByArea, namesByArea, targetKey, city: 'CALI', rotate: false, lugar: 'Cali', note: 'Seleccione una comuna para abrir la votación por barrio.' });
}
function isBogotaElection(candidate, target) {
  const corp = normalizedText(candidate?.corp || ''), municipality = normalizedText(candidate?.circunscripcion || '');
  const territorialOffice = corp.includes('JAL') || corp.includes('CONCEJO') || corp.includes('ALCALD');
  const targetIsBogota = Boolean(target?.municipality?.includes('BOGOTA')) && CORP_MUNICIPAL.includes(target?.corporation);
  return (territorialOffice && municipality.includes('BOGOTA')) || targetIsBogota;
}
function isCaliElection(candidate) { return normalizedText(candidate?.circunscripcion).includes('CALIVALLEDELCAUCA') || String(candidate?.corp || '').includes('· CALI ·'); }
/* UNA elección → el mapa que le corresponde. Es el único punto de decisión;
   antes eran cinco wrappers que se pisaban y el caso de Bogotá se saltaba los
   controles de nivel. */
async function renderSingleElection(candidate) {
  crmMapMode = 'total'; EN_DESTINO = false;
  if (crmBarrioLayer && crmLeafletMap) { crmLeafletMap.removeLayer(crmBarrioLayer); crmBarrioLayer = null; }
  $('crmMap')?.querySelector('.crm-territory-notice')?.remove();
  $('crmMapVotes').textContent = 'Cargando'; $('crmMapNote').textContent = 'Cargando distribución territorial desde el historial del candidato.';
  const isJal = String(candidate.corp || '').toUpperCase().startsWith('JAL');
  try {
    if (isCaliElection(candidate)) return await renderCaliCampaignMap(candidate);
    if (isBogotaElection(candidate, null) || (isBogotaElection(candidate, currentTargetTerritory()) && await historialEnObjetivo(candidate))) return await renderBogotaCampaignMap(candidate);
    try { const ciudad = await ciudadDeLaCandidatura(candidate); if (ciudad) return await renderCiudadMap(candidate, ciudad); } catch (e) { /* ciudad sin capa → genérico */ }
    return await renderGenericMap(candidate);
  } catch (e) {
    $('crmMap').innerHTML = '<div style="padding:28px;color:#667068">No fue posible cargar el mapa histórico en este momento.</div>'; crmLeafletMap = null; crmMapLayer = null; crmTileLayer = null;
    $('crmBreakdown').innerHTML = '<p class="helper">No fue posible cargar el desglose territorial.</p>'; $('crmMapVotes').textContent = 'Sin mapa'; $('crmMapNote').textContent = 'La fuente del historial no respondió; podrá reintentar al abrir el CRM.';
  }
}

/* Barrios: polígonos locales (Bogotá y Cali) o puestos georreferenciados. */
function loadCandidateMapScript(src) { return new Promise((resolve, reject) => { const script = document.createElement('script'); script.src = src; script.async = true; script.onload = resolve; script.onerror = () => reject(new Error(`No se pudo cargar ${src}`)); document.head.appendChild(script); }); }
let bogotaPuestoBarrioPromise = null;
const bogotaBarriosPorLocalidad = new Map();
/* Ciudades con cartografía barrial en el repo Y diccionario puesto→barrio.
   Cali y Cartagena comparten forma de dato ({barrio, comuna} por puesto y
   `properties.barrio` en el polígono), así que comparten camino: una entrada
   más acá basta para sumar una ciudad. Bogotá va aparte porque su diccionario
   es {zona-puesto: código catastral}, otra llave y otro nombre. */
const BARRIOS_DIC = {
  CALI: { carpeta: 'cali-barrios', dic: 'cali-puesto-barrio.js', diccionario: () => window.Candidato360CaliPuestoBarrio, registro: () => window.Candidato360CaliBarrios, unidad: 'comuna',
    archivos: Array.from({ length: 22 }, (_, i) => String(i + 1).padStart(2, '0')) },
  CARTAGENA: { carpeta: 'cartagena-barrios', dic: 'cartagena-puesto-barrio.js', diccionario: () => window.Candidato360CartagenaPuestoBarrio, registro: () => window.Candidato360CartagenaBarrios, unidad: 'unidad comunera', v: '20260927',
    archivos: Array.from({ length: 15 }, (_, i) => String(i + 1).padStart(2, '0')).concat('20') },
};
const dicPuestoBarrio = new Map(), geoBarrialPorUnidad = new Map();
/* ⚠️ Los polígonos de barrio van SIN rotar. La ciudad se dibuja rotada 90°
   (convención del proyecto: Bogotá es larga de norte a sur y así cabe en el
   panel), pero a escala de barrio entra el callejero real de OpenStreetMap
   debajo. Rotar los barrios sobre un callejero sin rotar los mandaba a los
   cerros orientales: la silueta se veía bien y no coincidía con ninguna calle.
   Por eso pintarBarrios saca del mapa la capa de localidades, que sí va rotada. */
async function bogotaBarrios(localityCode) {
  const key = String(localityCode || '').padStart(2, '0');
  if (!bogotaPuestoBarrioPromise) bogotaPuestoBarrioPromise = window.Candidato360BogotaPuestoBarrio ? Promise.resolve(window.Candidato360BogotaPuestoBarrio) : loadCandidateMapScript('candidato-360-data/bogota-puesto-barrio.js').then(() => window.Candidato360BogotaPuestoBarrio);
  if (!bogotaBarriosPorLocalidad.has(key)) bogotaBarriosPorLocalidad.set(key, (window.Candidato360BogotaBarrios?.[key] ? Promise.resolve() : loadCandidateMapScript(`candidato-360-data/bogota-barrios/${key}.js`)).then(() => { const geo = window.Candidato360BogotaBarrios?.[key]; if (!geo) throw new Error(`Sin cartografía barrial para la localidad ${key}`); return geo; }));
  return Promise.all([bogotaPuestoBarrioPromise, bogotaBarriosPorLocalidad.get(key)]);
}
/* El diccionario de puestos de una ciudad, una sola vez por sesión. */
function puestoBarrioDe(ciudad) {
  const cfg = BARRIOS_DIC[ciudad]; if (!cfg) return Promise.resolve(null);
  if (!dicPuestoBarrio.has(ciudad)) dicPuestoBarrio.set(ciudad, cfg.diccionario() ? Promise.resolve(cfg.diccionario()) : loadCandidateMapScript(`candidato-360-data/${cfg.dic}${cfg.v ? `?v=${cfg.v}` : ''}`).then(() => cfg.diccionario()));
  return dicPuestoBarrio.get(ciudad);
}
/* Se llama diferido desde la capa de Cartagena (`prepare`), que se declara
   antes que esto: nombrarlo directo allá rompe el arranque del archivo. */
const cartagenaPuestoBarrio = () => puestoBarrioDe('CARTAGENA');
/* Los barrios de UNA unidad (comuna o unidad comunera) y el diccionario. */
async function barriosPorDiccionario(ciudad, unidadCode) {
  const cfg = BARRIOS_DIC[ciudad], key = String(unidadCode || '').padStart(2, '0'), llave = `${ciudad}:${key}`;
  if (!geoBarrialPorUnidad.has(llave)) geoBarrialPorUnidad.set(llave, (cfg.registro()?.[key] ? Promise.resolve() : loadCandidateMapScript(`candidato-360-data/${cfg.carpeta}/${key}.js${cfg.v ? `?v=${cfg.v}` : ''}`)).then(() => { const geo = cfg.registro()?.[key]; if (!geo) throw new Error(`Sin cartografía barrial para la ${cfg.unidad} ${key}`); return geo; }));
  return Promise.all([puestoBarrioDe(ciudad), geoBarrialPorUnidad.get(llave)]);
}
/* ─── Barrios de las demás ciudades ──────────────────────────────────────────
   Bogotá y Cali traen cartografía barrial partida por localidad/comuna y un
   diccionario puesto→barrio hecho a mano. Para el resto hay un GeoJSON de
   ciudad entera y ningún diccionario, así que el puesto se ubica por
   COORDENADA: cada puesto de votación tiene lat/lng en PUESTOS_GEOREF y se
   busca en qué polígono cae. Es exacto y no depende de que el nombre del
   barrio en la Registraduría coincida con el del catastro, que casi nunca
   pasa («LA ESPERANZA #2» contra «La Esperanza No. 2»).

   Medellín, Ibagué y Montería: Medellín tiene su capa oficial aparte; para
   Ibagué y Montería no hay cartografía barrial publicada y el mapa se queda en
   los puestos de votación, que es el modo degradado de siempre. */
const CITY_BARRIO_LAYERS = [
  { match: ['MEDELLIN'], url: () => `${RRData.publicUrl('bases+de+datos')}/MEDELLIN_BARRIOS_OFICIAL.json`, name: p => p.NOMBRE || 'Barrio', code: p => String(p.CODIGO || p.NOMBRE || '') },
  { match: ['PEREIRA'], url: () => `${S3}/mapas-2026/Ciudades-COM-LOC/PEREIRA-BARRIOS.json`, name: p => p.NOMBRE || 'Barrio', code: p => String(p.NOMBRE || '') },
  { match: ['MANIZALES'], url: () => `${S3}/mapas-2026/Ciudades-COM-LOC/MANIZALES-BARRIOS.json`, name: p => p.BARRIOS || 'Barrio', code: p => String(p.BARRIOS || '') },
  { match: ['BARRANQUILLA'], url: () => `${S3}/mapas-2026/Ciudades-COM-LOC/BARRANQUILLA-BARRIOS.json`, name: p => p.NOMBRE || 'Barrio', code: p => String(p.NOMBRE || '') },
  { match: ['BUCARAMANGA'], url: () => `${S3}/mapas-2026/Ciudades-COM-LOC/BUCARAMANGA-BARRIOS.json`, name: p => p.barrio || 'Barrio', code: p => String(p.barrio || '') },
  { match: ['CUCUTA'], url: () => `${S3}/mapas-2026/Ciudades-COM-LOC/CUCUTA-BARRIOS.json`, name: p => p.barrio || 'Barrio', code: p => String(p.barrio || '') },
  { match: ['POPAYAN'], url: () => `${S3}/mapas-2026/Ciudades-COM-LOC/POPAYAN-BARRIOS.json`, name: p => p.BARRIOS || 'Barrio', code: p => String(p.BARRIOS || '') },
  /* Ibagué y Montería no tienen cartografía barrial publicada en ninguna
     fuente alcanzable. Sus barrios son una APROXIMACIÓN por Voronoi sobre los
     puestos de votación, recortada por comuna —lo mismo que el proyecto hizo
     para Medellín antes de tener la capa oficial— y viven en el repo
     (tools/candidato-360/barrios-voronoi/). El aviso va en la nota del mapa:
     un límite de Voronoi leído como límite administrativo miente. */
  { match: ['IBAGUE'], url: () => 'candidato-360-data/barrios-voronoi/IBAGUE-BARRIOS.json', name: p => p.NOMBRE || 'Barrio', code: p => String(p.CODIGO || p.NOMBRE || ''), aviso: 'Los barrios de Ibagué son una aproximación: cada uno es el área más cercana a sus puestos de votación, no el límite oficial.' },
  { match: ['MONTERIA'], url: () => 'candidato-360-data/barrios-voronoi/MONTERIA-BARRIOS.json', name: p => p.NOMBRE || 'Barrio', code: p => String(p.CODIGO || p.NOMBRE || ''), aviso: 'Los barrios de Montería son una aproximación: cada uno es el área más cercana a sus puestos de votación, no el límite oficial.' },
];
function cityBarrioLayerFor(city) { const c = normalizedText(city || ''); return CITY_BARRIO_LAYERS.find(x => x.match.some(m => c.includes(m))) || null; }
/* Ray casting. Un punto está en el polígono si cruza un número impar de
   aristas; los anillos interiores (huecos) lo sacan. */
function puntoEnAnillo(x, y, anillo) {
  let dentro = false;
  for (let i = 0, j = anillo.length - 1; i < anillo.length; j = i++) {
    const xi = anillo[i][0], yi = anillo[i][1], xj = anillo[j][0], yj = anillo[j][1];
    if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) dentro = !dentro;
  }
  return dentro;
}
function puntoEnGeometria(x, y, geom) {
  const poligonos = geom?.type === 'Polygon' ? [geom.coordinates] : geom?.type === 'MultiPolygon' ? geom.coordinates : [];
  return poligonos.some(anillos => puntoEnAnillo(x, y, anillos[0]) && !anillos.slice(1).some(hueco => puntoEnAnillo(x, y, hueco)));
}
/* Índice con caja envolvente: descarta el 99 % de los polígonos sin recorrer
   sus vértices. Con 332 barrios y 200 puestos la diferencia se nota. */
function indiceBarrios(geo, cfg) {
  return (geo?.features || []).map(f => {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    const recorre = c => { if (typeof c[0] === 'number') { x0 = Math.min(x0, c[0]); x1 = Math.max(x1, c[0]); y0 = Math.min(y0, c[1]); y1 = Math.max(y1, c[1]); } else c.forEach(recorre); };
    if (f.geometry?.coordinates) recorre(f.geometry.coordinates);
    return { f, code: cfg.code(f.properties), caja: [x0, y0, x1, y1] };
  }).filter(x => x.code && Number.isFinite(x.caja[0]));
}
function barrioDelPunto(indice, lng, lat) {
  if (!Number.isFinite(lng) || !Number.isFinite(lat)) return '';
  for (const item of indice) {
    const [x0, y0, x1, y1] = item.caja;
    if (lng < x0 || lng > x1 || lat < y0 || lat > y1) continue;
    if (puntoEnGeometria(lng, lat, item.f.geometry)) return item.code;
  }
  /* Un puesto a pocos metros del borde —la coordenada de la Registraduría no
     es de topógrafo— se queda con el barrio cuya caja está más cerca, hasta
     60 m. Más lejos que eso, mejor no inventar. */
  const TOLERANCIA = 0.00055;
  let mejor = '', mejorDist = TOLERANCIA;
  for (const item of indice) {
    const [x0, y0, x1, y1] = item.caja;
    const dx = Math.max(x0 - lng, 0, lng - x1), dy = Math.max(y0 - lat, 0, lat - y1), d = Math.hypot(dx, dy);
    if (d < mejorDist) { mejorDist = d; mejor = item.code; }
  }
  return mejor;
}
const barriosCiudadCache = new Map();
function cargarBarriosCiudad(cfg) {
  const url = cfg.url();
  if (!barriosCiudadCache.has(url)) barriosCiudadCache.set(url, fetchJSON(url).then(geo => ({ geo, indice: indiceBarrios(geo, cfg) })));
  return barriosCiudadCache.get(url);
}
/* A escala de barrio la pregunta deja de ser «cuánto» y pasa a ser «dónde
   queda»: sin calles nadie reconoce su cuadra. Los polígonos barriales SÍ van
   en coordenadas reales (a diferencia de las localidades de Bogotá, que van
   rotadas), así que acá el callejero calza — se pone en gris y atenuado, y el
   relleno baja de opacidad para que las carreras se lean por debajo. Mientras
   dura esta vista se esconde la capa de localidades: rotada sobre un
   callejero sin rotar, contradice cada calle que hay debajo. */
/* Los límites de las unidades (localidades, comunas, UCG) sobre la vista de
   barrios: sin relleno y sin clics, solo para que se sepa dónde termina cada
   una. La abierta va gruesa. Bogotá se dibuja rotada 90° y los barrios van en
   coordenadas reales, así que sus localidades se des-rotan para calzar. */
function desrotarGeoJSON(geoData) {
  const cx = -74.08, cy = 4.65, back = ([x, y]) => [cx + (y - cy), cy - (x - cx)];
  const geometry = g => g.type === 'Polygon' ? { ...g, coordinates: g.coordinates.map(r => r.map(back)) } : g.type === 'MultiPolygon' ? { ...g, coordinates: g.coordinates.map(p => p.map(r => r.map(back))) } : g;
  return { ...geoData, features: geoData.features.map(f => ({ ...f, geometry: geometry(f.geometry) })) };
}
function contornoUnidades(state, key) {
  if (!state?.geoData) return null;
  if (state.rotado && !state.geoSinRotar) state.geoSinRotar = desrotarGeoJSON(state.geoData);
  const geo = state.rotado ? state.geoSinRotar : state.geoData;
  const capa = L.geoJSON(geo, { interactive: false, style: f => { const foco = state.config.code(f.properties) === key; return { fill: false, color: '#173f2c', weight: foco ? 3.2 : 1.1, opacity: foco ? .95 : .5 }; } });
  capa._contorno = true;
  return capa;
}
/* Una ventana fija recorta el encuadre de una unidad que se sale de la
   ciudad: la UCG 20 de Cartagena llega a Isla Fuerte, 100 km al sur. */
function recortarAVentana(bounds, ventana) {
  if (!ventana || !bounds?.isValid()) return bounds;
  const s = Math.max(ventana.sur, bounds.getSouth()), n = Math.min(ventana.norte, bounds.getNorth()), o = Math.max(ventana.oeste, bounds.getWest()), e = Math.min(ventana.este, bounds.getEast());
  return s < n && o < e ? L.latLngBounds([[s, o], [n, e]]) : ventanaBounds(ventana);
}
/* ── Barrios de la ciudad entera ─────────────────────────────────────────────
   Al abrir una localidad o comuna el mapa pasa a escala de BARRIO EN TODA LA
   CIUDAD, con una sola escala de color y la unidad abierta marcada con un
   borde grueso. Antes se pintaban solo los barrios de esa unidad y alrededor
   quedaban las demás comunas con su color de votos —otra escala con la misma
   rampa— o el callejero en gris, y no se sabía qué se comparaba con qué. El
   desglose de la derecha sigue siendo el de la unidad abierta. */
/* ── Barrios sin puesto propio: el color del vecino más cercano ────────────
   Un barrio sin puesto de votación no tiene votos ni censo propios, y en el
   mapa quedaba como un hueco (en Cartagena, 138 de 213). Se pinta con el valor
   del barrio CON puesto más cercano por centroide, punteado y translúcido, y
   nunca entra al desglose ni a un total. Mismo criterio que la página del
   electorado y los tableros de 2023. Tope de 3 km: más lejos queda sin dato. */
const RELLENO_MAX_KM = 3;
function centroideBarrio(g) {
  const anillos = g?.type === 'Polygon' ? [g.coordinates[0]] : g?.type === 'MultiPolygon' ? g.coordinates.map(pg => pg[0]) : [];
  let x = 0, y = 0, n = 0;
  anillos.forEach(r => r.forEach(([lon, lat]) => { x += lon; y += lat; n++; }));
  return n ? [x / n, y / n] : null;
}
function rellenosBarrios(features, conPuesto) {
  const con = [], sin = [];
  features.forEach(f => { const c = centroideBarrio(f.geometry), k = f.properties._k; if (!c || !k) return; (conPuesto.has(k) ? con : sin).push({ k, c, n: f.properties._n }); });
  const out = new Map();
  sin.forEach(b => {
    if (out.has(b.k)) return;
    let mejor = null, d2 = Infinity;
    con.forEach(o => { const dx = (o.c[0] - b.c[0]) * Math.cos(b.c[1] * Math.PI / 180), dy = o.c[1] - b.c[1], d = dx * dx + dy * dy; if (d < d2) { d2 = d; mejor = o; } });
    const km = Math.sqrt(d2) * 111.32;
    if (mejor && km <= RELLENO_MAX_KM) out.set(b.k, { de: mejor.k, nombre: mejor.n, km });
  });
  return out;
}
async function pintarCiudadBarrios(state, fuente, features, key, { encuadre = true } = {}) {
  /* key '*' = la ciudad entera por barrio, sin una unidad abierta: es el
     nivel «Barrio» cuando se pide sin haber tocado antes una localidad. */
  const todo = key === '*';
  const historical = {};
  /* Sin votos propios, lo que reparte la meta por barrio es la huella de la
     familia (si la hay); el censo sigue siendo lo que se ve en «Total». */
  const familia = state.censo && crmMapMode === 'proyectado' && state.proy?.mesas?.length;
  (familia ? state.proy.mesas : state.mesas).forEach(m => { const b = fuente.barrioDeMesa(m); if (b) historical[b] = (historical[b] || 0) + Number(m.v || 0); });
  const unidadDe = {}; features.forEach(f => { unidadDe[f.properties._k] = f.properties._u; });
  let values = historical, baseFoco = state.censo ? 'censo-total' : 'historial';
  if (crmMapMode === 'proyectado') {
    /* La meta de cada unidad se reparte entre SUS barrios: por la votación
       propia si la hay, si no por el censo electoral (valoresBarriales). */
    const metas = projectedVotesByArea(); values = {};
    let censo = null; const bases = [];
    const censoDe = u => async () => { if (!censo) censo = await fuente.censo(); return Object.fromEntries(Object.entries(censo).filter(([k]) => unidadDe[k] === u)); };
    for (const u of new Set(features.map(f => f.properties._u).filter(Boolean))) {
      const hist = Object.fromEntries(Object.entries(historical).filter(([k]) => unidadDe[k] === u));
      const r = await valoresBarriales(hist, Number(metas[u] || 0), censoDe(u));
      Object.assign(values, r.values);
      if (u === key) baseFoco = familia && r.base === 'historial' ? 'familia' : r.base;
      if (Number(metas[u] || 0) > 0) bases.push(r.base);
    }
    /* Con la ciudad entera no hay UNA unidad que diga de dónde sale el reparto:
       manda la votación (propia o de la familia) si alguna zona la tuvo. */
    if (todo) { const b = bases.includes('historial') ? 'historial' : bases.includes('censo') ? 'censo' : bases[0]; if (b) baseFoco = familia && b === 'historial' ? 'familia' : b; }
  }
  /* Qué barrios tienen puesto: los que tienen censo o votos propios. */
  const censoBarrio = await fuente.censo().catch(() => ({}));
  const conPuesto = new Set([...Object.keys(censoBarrio).filter(k => censoBarrio[k] > 0), ...Object.keys(historical)]);
  const relleno = rellenosBarrios(features, conPuesto);
  if (crmMapState !== state || state.focusKey !== key) return;
  const foco = todo ? features : features.filter(f => f.properties._u === key);
  const valoresFoco = Object.fromEntries(foco.map(f => [f.properties._k, Number(values[f.properties._k] || 0)]).filter(([, v]) => v > 0));
  renderMapBreakdown(valoresFoco, Object.fromEntries(foco.map(f => [f.properties._k, f.properties._n])), tituloBarrial(baseFoco));
  const max = Math.max(1, ...features.map(f => Number(values[f.properties._k] || 0)));
  if (crmBarrioLayer) crmLeafletMap.removeLayer(crmBarrioLayer);
  ponerBasemap('crm-basemap-tenue');
  if (crmMapLayer) crmLeafletMap.removeLayer(crmMapLayer);   /* se saca del mapa, no del grupo: vuelve al subir de nivel */
  const estilo = f => {
    const k = f.properties._k, enFoco = !todo && f.properties._u === key, r = !conPuesto.has(k) && relleno.get(k);
    if (r) { const v = Number(values[r.de] || 0); return { fillColor: MAP_COLOR(v / max), fillOpacity: v ? .3 : .08, color: 'rgba(16,34,56,.5)', weight: enFoco ? .9 : .6, dashArray: '3 3' }; }
    const v = Number(values[k] || 0); return { fillColor: MAP_COLOR(v / max), fillOpacity: v ? .62 : .1, color: enFoco ? 'rgba(16,34,56,.7)' : 'rgba(16,34,56,.3)', weight: enFoco ? .9 : .5, dashArray: null };
  };
  crmBarrioLayer = L.geoJSON({ type: 'FeatureCollection', features }, {
    style: estilo,
    onEachFeature: (f, layer) => {
      const k = f.properties._k, u = f.properties._u, v = Number(values[k] || 0), r = !conPuesto.has(k) && relleno.get(k);
      layer._vitrinaCode = k;
      const unidad = u && state.namesByArea[u] ? `<br><span style="opacity:.7">${escHtml(NOMBRE_BONITO(state.namesByArea[u]))}</span>` : '';
      const que = crmMapMode === 'proyectado' ? 'votos proyectados' : state.censo ? 'personas habilitadas' : 'votos';
      layer.bindTooltip(r
        ? `<strong>${NOMBRE_BONITO(f.properties._n)}</strong>${unidad}<br>Sin puesto de votación propio: toma el color de <b>${escHtml(NOMBRE_BONITO(r.nombre))}</b>, el barrio con puesto más cercano (${r.km < 1 ? `${Math.round(r.km * 1000)} m` : `${r.km.toFixed(1).replace('.', ',')} km`}), que tiene ${Number(values[r.de] || 0).toLocaleString('es-CO')} ${que}. Es un color inferido: no suma a ningún total.`
        : !conPuesto.has(k) ? `<strong>${NOMBRE_BONITO(f.properties._n)}</strong>${unidad}<br>Sin puesto de votación propio ni barrio con puesto a menos de ${RELLENO_MAX_KM} km.`
        : `<strong>${NOMBRE_BONITO(f.properties._n)}</strong>${unidad}<br>${v.toLocaleString('es-CO')} ${que}`, { sticky: true });
      layer.on('mouseover', () => layer.setStyle({ weight: 1.5, color: '#fff' }));
      layer.on('mouseout', () => layer.setStyle(estilo(f)));
      /* Tocar un barrio de otra zona abre esa zona, sin mover el encuadre:
         la persona ya está mirando donde quiere mirar. */
      if (u && u !== key) layer.on('click', () => { renderBarriosForArea(u, { encuadre: false }); setMapLevel('barrio'); });
    }
  });
  const contorno = contornoUnidades(state, todo ? null : key); if (contorno) crmBarrioLayer.addLayer(contorno);
  crmBarrioLayer._vitrinaTop = vitrinaTop(valoresFoco);
  crmBarrioLayer.addTo(crmLeafletMap);
  if (encuadre && foco.length) encuadrarBounds(recortarAVentana(L.geoJSON({ type: 'FeatureCollection', features: foco }).getBounds(), state.config.ventana), 20);
  const donde = todo ? (NOMBRE_BONITO(state.tituloLugar || '') || 'la ciudad') : fuente.donde(key, foco);
  $('crmMapNote').innerHTML = notaBarrial(donde, baseFoco) + (todo
    ? ` Toda la ciudad por barrio, con una sola escala de color; el borde marca cada ${escHtml(state.config.title)}. Toque un barrio para abrir su zona.`
    : ` Se ve toda la ciudad por barrio, con una sola escala de color; el borde grueso marca ${escHtml(NOMBRE_BONITO(donde))}. Toque un barrio de otra zona para abrirla.`)
    + (() => { const n = new Set(features.filter(f => !conPuesto.has(f.properties._k) && relleno.has(f.properties._k)).map(f => f.properties._k)).size;
        return n ? ` Los ${n.toLocaleString('es-CO')} barrios punteados no tienen puesto de votación propio: toman el color del barrio con puesto más cercano (a menos de ${RELLENO_MAX_KM} km). Ese color es inferido y no entra al desglose.` : ''; })()
    + (fuente.aviso ? ` ${fuente.aviso}` : '');
  setTimeout(candadoDetalle, 0);
}
/* ── La meta a escala de barrio ──────────────────────────────────────────────
   Repartir la meta de una localidad entre sus barrios necesita un peso. Si la
   persona ya sacó votos ahí, el peso es su propia huella: es lo más suyo que
   hay. Si no —una localidad que nunca disputó, o un salto de corporación que
   le manda meta a media ciudad—, el peso es el CENSO ELECTORAL de cada barrio.
   No dice dónde la quieren; dice dónde hay gente que vota, que es la única
   pregunta que los datos pueden contestar ahí. La nota del mapa lo aclara,
   porque un mapa de censo leído como un mapa de apoyo miente. */
async function valoresBarriales(historical, localGoal, censoDe) {
  if (crmMapMode !== 'proyectado') return { values: historical, base: 'historial' };
  if (Object.values(historical).some(v => v > 0)) return { values: distributeVotes(historical, localGoal), base: 'historial' };
  if (!localGoal) return { values: {}, base: 'sin-meta' };
  try {
    const censo = await censoDe();
    if (Object.values(censo).some(v => v > 0)) return { values: distributeVotes(censo, localGoal), base: 'censo' };
  } catch (e) { /* el CSV de puestos no respondió */ }
  return { values: {}, base: 'sin-base' };
}
function tituloBarrial(base) {
  return crmMapMode !== 'proyectado' ? (base === 'censo-total' ? 'Censo electoral por barrio' : 'Votos totales por barrio')
    : base === 'censo' ? 'Meta proyectada por barrio · censo' : 'Meta proyectada por barrio';
}
function notaBarrial(donde, base) {
  const cabeza = `Detalle poligonal por barrio de ${donde}.`;
  if (crmMapMode !== 'proyectado') return base === 'censo-total' ? `${cabeza} El color es el censo electoral: cuánta gente puede votar en cada barrio.` : cabeza;
  if (base === 'familia') return `${cabeza} La meta de esta zona se reparte según dónde votó su familia política en 2023, barrio por barrio.`;
  if (base === 'censo') return `${cabeza} Usted no tuvo votos acá, así que la meta se reparte por el <b>censo electoral</b> de cada barrio: dice dónde hay gente que vota, no dónde ya votaron por usted.`;
  if (base === 'historial') return `${cabeza} La meta de esta zona se reparte en la misma proporción en que ya votaron por usted, barrio por barrio.`;
  if (base === 'sin-meta') return `${cabeza} Esta zona no recibe meta en la proyección.`;
  return `${cabeza} No se pudo repartir la meta por barrio: el censo por puesto de votación no respondió.`;
}
/* De dónde salen los barrios de una ciudad. Tres caminos, una sola forma:
   cada polígono sale con `_k` (su llave), `_u` (la unidad del nivel que se
   está viendo) y `_n` (su nombre), y cada mesa se ubica en un `_k`.
   · Diccionario (Cali, Cartagena): polígonos partidos por comuna/UCG y un
     diccionario puesto→barrio hecho a mano.
   · Bogotá: polígonos por localidad y diccionario zona-puesto→código catastral.
   · Capa de ciudad entera (Medellín, Pereira…): el puesto se ubica por
     COORDENADA y el barrio toma la unidad de la mayoría de sus puestos. */
let barriosTok = 0;
const code6 = v => String(v).padStart(6, '0');
function fuenteBarrial(state) {
  const dic = BARRIOS_DIC[state.city];
  if (dic) {
    const unidadDe = state.config.unidadBarrio || (p => p.comuna || '');
    const llave = d => d?.barrio ? `${d.comuna}|${d.barrio}` : '';
    let pb = null;
    return {
      archivos: dic.archivos,
      /* Los archivos van por comuna/UCG: si esa es la unidad abierta se pinta
         primero y el resto llega después. A escala de localidad (Cartagena)
         una localidad junta varias UCG, así que se carga todo de una. */
      primero: key => state.config.unidadEsArchivo === false ? dic.archivos : [String(key).padStart(2, '0')],
      prep: async () => { pb = await puestoBarrioDe(state.city); },
      cargar: async a => { const [, geo] = await barriosPorDiccionario(state.city, a); return geo.features.map(f => ({ ...f, properties: { ...f.properties, _k: llave(f.properties), _u: unidadDe(f.properties), _n: f.properties.barrio } })); },
      barrioDeMesa: m => llave(pb?.[electoralPlaceCode(m)]),
      censo: async () => { const places = await puestosPorBarrio(), out = {}; Object.entries(pb || {}).forEach(([code, d]) => { const k = llave(d), c = places[code]?.censo || 0; if (k && c) out[k] = (out[k] || 0) + c; }); return out; },
      donde: key => state.namesByArea[key] || `la ${state.config.title} ${key}`,
    };
  }
  /* Bogotá se reconoce por la capa que está pintada, no por las mesas: con un
     salto de corporación la meta cae en localidades donde la persona nunca
     tuvo una mesa. */
  if (String(state.city || '').startsWith('BOGOTA') || state.mesas.some(m => String(m.dep) === '16')) {
    let pb = null;
    return {
      /* Sumapaz (20) no tiene cartografía barrial: su archivo no existe. */
      archivos: Array.from({ length: 19 }, (_, i) => String(i + 1).padStart(2, '0')),
      primero: key => [String(key).padStart(2, '0')],
      prep: async () => {},
      cargar: async a => { const [dicc, geo] = await bogotaBarrios(a); pb = dicc; return geo.features.map(f => ({ ...f, properties: { ...f.properties, _k: code6(f.properties.codigo), _u: a, _n: f.properties.nombre } })); },
      barrioDeMesa: m => { const b = pb?.[`${String(m.zon || '').padStart(2, '0')}-${String(m.pue || '').padStart(2, '0')}`]; return b ? code6(b) : ''; },
      censo: async () => { const places = await puestosPorBarrio(), out = {}; Object.entries(pb || {}).forEach(([zp, b]) => { const c = places[`16001${String(zp).replace('-', '')}`]?.censo || 0; if (c) out[code6(b)] = (out[code6(b)] || 0) + c; }); return out; },
      donde: (key, foco) => foco?.[0]?.properties.loc_nombre || state.namesByArea[key] || 'la localidad',
    };
  }
  const capa = cityBarrioLayerFor(state.city);
  if (capa) {
    const ciudad = state.ciudad || `${String(state.mesas[0]?.dep || '').padStart(2, '0')}${String(state.mesas[0]?.mun || '').padStart(3, '0')}`;
    const llaveDe = m => (state.config.mesaKey ? state.config.mesaKey(m) : claveLocal(m));
    let data = null, places = null; const barrioPorPuesto = new Map(), unidadDeBarrio = {};
    return {
      archivos: ['*'], primero: () => ['*'],
      prep: async () => {
        if (data) return;
        [data, places] = await Promise.all([cargarBarriosCiudad(capa), puestosPorBarrio()]);
        const conteo = {};
        for (const [code, p] of Object.entries(places)) {
          if (!code.startsWith(ciudad) || !p.mesa) continue;
          const b = barrioDelPunto(data.indice, p.lng, p.lat); if (!b) continue;
          barrioPorPuesto.set(code, b);
          const u = llaveDe(p.mesa); if (u) (conteo[b] ||= {})[u] = (conteo[b][u] || 0) + (p.censo || 1);
        }
        Object.entries(conteo).forEach(([b, us]) => { unidadDeBarrio[b] = Object.entries(us).sort((x, y) => y[1] - x[1])[0][0]; });
      },
      cargar: async () => data.geo.features.map(f => { const k = capa.code(f.properties); return { ...f, properties: { ...f.properties, _k: k, _u: unidadDeBarrio[k] || '', _n: capa.name(f.properties) } }; }),
      barrioDeMesa: m => barrioPorPuesto.get(electoralPlaceCode(m)) || '',
      censo: async () => { const out = {}; for (const [code, b] of barrioPorPuesto) { const c = places[code]?.censo || 0; if (c) out[b] = (out[b] || 0) + c; } return out; },
      donde: key => state.namesByArea[key] || `la ${state.config.title} ${key}`,
      aviso: capa.aviso || '',
    };
  }
  return null;
}
async function renderBarriosForArea(key, { encuadre = true } = {}) {
  const state = crmMapState; if (!state) return;
  state.focusKey = key;
  const tok = ++barriosTok;
  $('crmBreakdown').innerHTML = '<h4>Votos por barrio</h4><p class="helper">Cargando polígonos y resultados barriales…</p>';
  const fuente = fuenteBarrial(state);
  if (fuente) {
    try {
      await fuente.prep();
      const primero = key === '*' ? fuente.archivos : fuente.primero(key), resto = fuente.archivos.filter(a => !primero.includes(a));
      const lote = lista => Promise.all(lista.map(a => fuente.cargar(a).catch(() => []))).then(x => x.flat());
      const features = await lote(primero);
      if (tok !== barriosTok) return;
      if (key === '*' ? features.length : features.some(f => f.properties._u === key)) {
        await pintarCiudadBarrios(state, fuente, features, key, { encuadre });
        /* El resto de la ciudad llega después y se repinta sin mover la vista. */
        if (resto.length) {
          const mas = await lote(resto);
          if (tok === barriosTok) await pintarCiudadBarrios(state, fuente, features.concat(mas), key, { encuadre: false });
        }
        return;
      }
    } catch (e) { /* sin cartografía barrial → puestos */ }
  }
  if (tok !== barriosTok) return;
  if (key === '*') {
    const metaCiudad = Object.values(projectedVotesByArea()).reduce((t, v) => t + Number(v || 0), 0);
    return pintarPuestos(state.mesas, NOMBRE_BONITO(state.tituloLugar || '') || 'la ciudad', metaCiudad, { censo: Boolean(state.censo) });
  }
  const mesas = state.mesas.filter(m => (state.config.mesaKey ? state.config.mesaKey(m) : claveLocal(m)) === key), localGoal = Number(projectedVotesByArea()[key] || 0);
  const layer = crmMapLayer?.getLayers().find(item => state.config.code(item.feature.properties) === key);
  return pintarPuestos(mesas, layer ? state.config.name(layer.feature.properties) : `la ${state.config.title}`, localGoal, { censo: Boolean(state.censo) });
}

/* ── Puestos de votación ─────────────────────────────────────────────────────
   El último nivel cuando no hay cartografía barrial: los puestos, cada uno en
   su coordenada, agrupados por el barrio que les asigna la Registraduría. No
   es un mapa de áreas —un puesto es un punto, no un polígono— pero dice lo
   único que importa a esa escala: dónde está la gente que ya votó por usted.
   Lo usan el nivel «Puestos» de los municipios sin comunas y el respaldo de
   las ciudades cuya capa barrial no cargó. */
async function pintarPuestos(mesas, donde, meta = 0, { censo = false } = {}) {
  let places = {}; try { places = await puestosPorBarrio(); } catch (e) {}
  const historical = {}, points = {};
  mesas.forEach(m => {
    const place = places[electoralPlaceCode(m)], name = place?.barrio || m.pueNom || 'Puesto sin barrio identificado';
    historical[name] = (historical[name] || 0) + Number(m.v || 0);
    if (place && Number.isFinite(place.lat) && Number.isFinite(place.lng)) points[name] = place;
  });
  const proyectando = crmMapMode === 'proyectado' && Boolean(meta);
  const values = proyectando ? distributeVotes(historical, meta) : historical;
  const max = Math.max(1, ...Object.values(values));
  const que = proyectando ? 'Meta proyectada' : censo ? 'Censo electoral' : 'Votos';
  renderMapBreakdown(values, Object.fromEntries(Object.keys(values).map(name => [name, name])), `${que} por puesto de votación`);
  if (crmBarrioLayer) crmLeafletMap.removeLayer(crmBarrioLayer);
  ponerBasemap('crm-basemap-tenue');
  /* Dentro de una ciudad se sacan las comunas pintadas (otra escala con la
     misma rampa, confundía) y queda solo su borde. */
  if (crmMapLayer && crmMapState) crmLeafletMap.removeLayer(crmMapLayer);
  /* El tamaño del punto lleva la magnitud, no solo el color: sobre el
     callejero un círculo pequeño y claro se pierde. */
  crmBarrioLayer = L.featureGroup(Object.entries(points).map(([name, point]) => {
    const v = Number(values[name] || 0);
    return Object.assign(L.circleMarker([point.lat, point.lng], { radius: 5 + Math.round(9 * Math.sqrt(v / max)), color: '#fff', weight: 1.2, fillColor: MAP_COLOR(v / max), fillOpacity: .92 })
      .bindTooltip(`<strong>${escHtml(name)}</strong><br>${v.toLocaleString('es-CO')} ${proyectando ? 'votos proyectados' : censo ? 'personas habilitadas' : 'votos'}`, { sticky: true }), { _vitrinaCode: name });
  }));
  const contornoPuestos = crmMapState ? contornoUnidades(crmMapState, crmMapState.focusKey === '*' ? null : crmMapState.focusKey) : null; if (contornoPuestos) crmBarrioLayer.addLayer(contornoPuestos);
  crmBarrioLayer._vitrinaTop = vitrinaTop(values);
  crmBarrioLayer.addTo(crmLeafletMap);
  const conCoordenada = Object.keys(points).length;
  encuadrar(crmBarrioLayer, 40);
  $('crmMapNote').innerHTML = `Puestos de votación de ${escHtml(donde)}, en su coordenada y agrupados por el barrio que les asigna la Registraduría. `
    + (conCoordenada
      ? (proyectando ? 'El tamaño del punto es la meta que le toca a cada puesto.' : censo ? 'El tamaño del punto es el censo electoral: cuánta gente vota ahí. Usted todavía no tiene votos en este territorio.' : 'El tamaño del punto es la votación.')
      : 'Ninguno de sus puestos tiene coordenada publicada, así que en el mapa no aparecen; el desglose de la derecha sí los lista.')
    + (Object.keys(places).length ? '' : ' La fuente de puestos no respondió.');
}

/* Vistas por año: una candidatura recurrente se lee elección por elección;
   nunca se mezclan votos de años o territorios distintos para armar el mapa. */
let electionViewRecords = [], electionViewSnapshots = new Map(), electionViewActive = '';
function electionViewHistory(candidate) {
  const source = Array.isArray(candidate?.history) && candidate.history.length ? candidate.history : [candidate], byYear = new Map();
  source.forEach(item => { const year = String(candidateYear(item) || '').match(/\d{4}/)?.[0]; if (!year) return; const existing = byYear.get(year); if (!existing || Number(item.votos || 0) > Number(existing.votos || 0)) byYear.set(year, item); });
  return [...byYear.entries()].sort((a, b) => Number(a[0]) - Number(b[0])).map(([year, cand]) => ({ year, candidate: cand }));
}
async function electionAppliesToTarget(candidate) {
  if (!alcanceObjetivo()) return { applies: true };
  try { const data = await datosCandidatura(candidate); return { applies: (data.mesas || []).length > 0, data }; } catch (error) { return { applies: false }; }
}
function showTerritoryNotApplicable(year) {
  if (crmMapLayer) { crmLeafletMap?.removeLayer(crmMapLayer); crmMapLayer = null; }
  if (crmBarrioLayer) { crmLeafletMap?.removeLayer(crmBarrioLayer); crmBarrioLayer = null; }
  const mapEl = $('crmMap'); mapEl.querySelector('.crm-territory-notice')?.remove();
  const notice = document.createElement('div'); notice.className = 'crm-territory-notice'; notice.innerHTML = `<strong>${year}</strong><span>Esa votación no aplica para esta entidad territorial.</span>`; mapEl.append(notice);
  $('crmMapVotes').textContent = 'No aplica';
  $('crmBreakdown').innerHTML = '<h4>Lectura territorial</h4><p class="helper">Esta candidatura no registró votación en el territorio seleccionado.</p>';
  $('crmMapNote').textContent = 'Seleccione otra elección, el promedio o la proyección para continuar.';
}
function captureElectionSnapshot(year) { if (!crmMapState) return; electionViewSnapshots.set(year, { ...crmMapState, votesByArea: { ...(crmMapState.votesByArea || {}) }, namesByArea: { ...(crmMapState.namesByArea || {}) }, mesas: [...(crmMapState.mesas || [])] }); }
function renderElectionViewToggles() {
  const head = $('crmMapTitle').closest('.panel-head'); if (!head) return;
  $('crmMapToggles')?.remove();
  const toggles = document.createElement('div'); toggles.className = 'map-toggles election-map-toggles'; toggles.id = 'crmMapToggles';
  toggles.innerHTML = [...electionViewRecords.map(r => `<button class="map-toggle${electionViewActive === r.year ? ' active' : ''}" type="button" data-election-view="${r.year}">${r.year}</button>`), `<button class="map-toggle${electionViewActive === 'average' ? ' active' : ''}" type="button" data-election-view="average">PROMEDIO</button>`, `<button class="map-toggle${electionViewActive === 'projected' ? ' active' : ''}" type="button" data-election-view="projected">PROYECTADO</button>`].join('');
  toggles.addEventListener('click', e => { const b = e.target.closest('[data-election-view]'); if (b) showElectionView(b.dataset.electionView); });
  head.append(toggles);
}
function electionViewStyleMap() {
  const state = crmMapState; if (!state || !crmMapLayer) return;
  const values = crmMapMode === 'proyectado' ? projectedVotesByArea() : state.votesByArea, max = Math.max(1, ...Object.values(values));
  crmMapLayer.eachLayer(layer => { const value = Number(values[state.config.code(layer.feature.properties)] || 0); layer.setStyle({ fillColor: MAP_COLOR(value / max), fillOpacity: value ? .7 : .26 }); });
  renderMapBreakdown(values, state.namesByArea, crmMapMode === 'proyectado' ? `Meta proyectada por ${state.config.title}` : `Promedio de votos por ${state.config.title}`);
  $('crmMapVotes').textContent = `${Math.round(Object.values(values).reduce((t, v) => t + Number(v || 0), 0)).toLocaleString('es-CO')} votos`;
}
async function showElectionYear(record, { restoreToggles = true } = {}) {
  const applicability = await electionAppliesToTarget(record.candidate);
  electionViewActive = record.year;
  if (!applicability.applies) { showTerritoryNotApplicable(record.year); if (restoreToggles) renderElectionViewToggles(); return false; }
  await renderSingleElection(record.candidate);
  captureElectionSnapshot(record.year);
  crmMapMode = 'total';
  if (crmMapState) $('crmMapVotes').textContent = `${Number(crmMapState.total || 0).toLocaleString('es-CO')} votos`;
  if (restoreToggles) renderElectionViewToggles();
  refreshMapLevels();
  return true;
}
async function showElectionAverage(projected = false) {
  /* Desde el mapa del destino, el promedio se pinta sobre la capa del historial. */
  if (EN_DESTINO && electionViewRecords.length) { destinoTok++; await renderSingleElection(electionViewRecords[electionViewRecords.length - 1].candidate); }
  for (const record of electionViewRecords) { if (!electionViewSnapshots.has(record.year)) await showElectionYear(record, { restoreToggles: false }); }
  const snapshots = [...electionViewSnapshots.values()];
  if (!snapshots.length) { showTerritoryNotApplicable('PROMEDIO'); renderElectionViewToggles(); return; }
  const compatible = snapshots.filter(s => s.config?.title === snapshots[0].config?.title), reference = compatible[compatible.length - 1];
  const keys = new Set(compatible.flatMap(s => Object.keys(s.votesByArea || {})));
  const votesByArea = Object.fromEntries([...keys].map(key => [key, Math.round(compatible.reduce((sum, s) => sum + Number(s.votesByArea[key] || 0), 0) / compatible.length)]));
  crmMapState = { ...reference, votesByArea, total: Object.values(votesByArea).reduce((sum, v) => sum + Number(v || 0), 0), max: Math.max(1, ...Object.values(votesByArea)), targetKey: null, focusKey: null };
  crmMapMode = projected ? 'proyectado' : 'total'; electionViewActive = projected ? 'projected' : 'average';
  if (crmBarrioLayer) { crmLeafletMap.removeLayer(crmBarrioLayer); crmBarrioLayer = null; }
  if (crmMapLayer && !crmLeafletMap.hasLayer(crmMapLayer)) { crmMapLayer.addTo(crmLeafletMap); aplicarBasemap(Boolean(crmMapState?.rotado)); }
  electionViewStyleMap();
  $('crmMapNote').textContent = projected ? 'Meta distribuida desde el promedio de las elecciones comparables.' : 'Promedio simple de las elecciones comparables en esta entidad territorial.';
  renderElectionViewToggles(); refreshMapLevels();
}
async function showElectionView(view) {
  if (view === 'projected' && DESTINO_FUERA) { crmMapMode = 'proyectado'; return pintarDestino(); }
  if (view === 'average') return showElectionAverage(false);
  if (view === 'projected') return showElectionAverage(true);
  const record = electionViewRecords.find(item => item.year === view); if (record) return showElectionYear(record);
}
/* Niveles Municipio / Localidad / Barrio: solo tienen sentido sobre un mapa de
   ciudad (crmMapState); sobre el genérico por departamento se retiran. */
function setMapLevel(level) {
  const controls = $('crmMap')?.querySelector('.crm-map-levels'); if (!controls) return;
  controls.querySelectorAll('[data-level]').forEach(b => b.classList.toggle('active', b.dataset.level === level && (!b.dataset.capa || b.dataset.capa === crmMapState?.config?.clave)));
  const barrio = controls.querySelector('[data-level="barrio"]'); if (barrio) barrio.disabled = !crmMapState?.config;
}
/* ¿Esta ciudad tiene cartografía barrial? Bogotá y Cali la traen curada; el
   resto, en CITY_BARRIO_LAYERS. Donde no hay, el último nivel no puede
   llamarse «Barrio»: son puestos de votación, y decirlo evita prometer un
   detalle que no existe. */
function ciudadTieneBarrios(state) {
  const city = String(state?.city || '');
  return city.startsWith('BOGOTA') || Boolean(BARRIOS_DIC[city]) || Boolean(cityBarrioLayerFor(city));
}
/* Niveles para un municipio sin comunas: no hay barrio que abrir, pero sí
   puestos. Lo que se ve en La Ceja, en Sabaneta, en el 90 % del país. */
const UNIDAD_NIVEL = { localidad: 'Localidad', comuna: 'Comuna', municipio: 'Municipio' };
function nivelesMunicipio() {
  const mapEl = $('crmMap'); if (!mapEl || !MAPA_MUNICIPAL || !crmMapLayer) return;
  /* «Municipio» no vale en Bogotá, donde lo que se dibuja son localidades, ni
     en Medellín, donde son comunas: el botón se llama como la unidad que
     realmente está en el mapa. */
  const etiqueta = UNIDAD_NIVEL[MAPA_MUNICIPAL.unidad] || 'Municipio';
  const controls = document.createElement('div'); controls.className = 'crm-map-levels';
  controls.innerHTML = `<button type="button" class="crm-map-level active" data-level="territorio">${etiqueta}</button><button type="button" class="crm-map-level" data-level="puestos">Puestos</button>`;
  mapEl.append(controls);
  const marcar = level => controls.querySelectorAll('[data-level]').forEach(b => b.classList.toggle('active', b.dataset.level === level));
  controls.querySelector('[data-level="territorio"]').addEventListener('click', () => {
    if (crmBarrioLayer) { crmLeafletMap.removeLayer(crmBarrioLayer); crmBarrioLayer = null; }
    /* La capa de Bogotá va rotada: un callejero sin rotar debajo la contradice
       (Soacha aparecía al norte). Volver al territorio tiene que devolver el
       mapa como lo dejó renderTerritorioObjetivo, encuadre incluido. */
    aplicarBasemap(Boolean(MAPA_MUNICIPAL.rotado)); crmMapLayer.setStyle({ fillOpacity: .94 });
    if (MAPA_MUNICIPAL.encuadre) encuadrarBounds(MAPA_MUNICIPAL.encuadre, 24); else encuadrar(crmMapLayer, 15);
    $('crmMapNote').textContent = (MAPA_MUNICIPAL.censo
      ? `${MAPA_MUNICIPAL.nombre} es el territorio de su candidatura. Abra «Puestos» para ver dónde vota la gente, puesto por puesto.`
      : `Votación histórica concentrada en ${MAPA_MUNICIPAL.nombre}. Abra «Puestos» para ver dónde está, puesto por puesto.`) + notaColorPartido();
    marcar('territorio');
  });
  controls.querySelector('[data-level="puestos"]').addEventListener('click', async () => {
    const meta = crmMapMode === 'proyectado' ? Number(String($('crmVoteNumber').textContent || '').replace(/\D/g, '')) : 0;
    /* A escala de puestos el municipio llena la pantalla: el polígono pasa a
       contorno para que se vea el callejero y los puntos, no un bloque de color. */
    crmMapLayer.setStyle({ fillOpacity: .08 });
    await pintarPuestos(MAPA_MUNICIPAL.mesas, MAPA_MUNICIPAL.nombre, meta, { censo: Boolean(MAPA_MUNICIPAL.censo) });
    marcar('puestos');
  });
}
function refreshMapLevels() {
  const mapEl = $('crmMap'); if (!mapEl) return;
  mapEl.querySelector('.crm-map-levels')?.remove();
  const state = crmMapState; if (!state?.config) return nivelesMunicipio();
  /* El rótulo del botón lo puede fijar la capa: en Cartagena la unidad se
     llama «unidad comunera» y en el mapa se rotula UCG, que es como la nombra
     el Distrito y lo único que cabe en el botón. */
  const localLabel = state.config.nivel || (state.config.title === 'comuna' ? 'Comuna' : 'Localidad');
  const detalle = ciudadTieneBarrios(state) ? 'Barrio' : 'Puestos';
  /* Sin «Municipio»: cuando el mapa ES la ciudad, ese botón mostraba lo mismo
     que «Comuna» —la ciudad entera dividida— y dejaba la alcaldía de Medellín
     abriendo en un nivel que no existe. Los niveles son los que de verdad
     cambian el dibujo. */
  /* Una ciudad con varias escalas (Cartagena: Localidad y UCG) muestra un
     botón por escala; el resto, uno solo con el nombre de su unidad. */
  const familia = state.config.familia;
  const unidades = familia ? Object.values(familia).map(c => `<button type="button" class="crm-map-level" data-level="localidad" data-capa="${c.clave}">${c.nivel}</button>`).join('') : `<button type="button" class="crm-map-level" data-level="localidad">${localLabel}</button>`;
  const controls = document.createElement('div'); controls.className = 'crm-map-levels';
  controls.innerHTML = `${unidades}<button type="button" class="crm-map-level" data-level="barrio" disabled>${detalle}</button>`;
  mapEl.append(controls);
  /* Volver a la ciudad deshace lo del barrio: sin callejero (la capa de
     Bogotá va rotada) y con las localidades de vuelta en el mapa. */
  const volver = level => {
    if (crmBarrioLayer) { crmLeafletMap.removeLayer(crmBarrioLayer); crmBarrioLayer = null; }
    if (crmMapLayer && !crmLeafletMap.hasLayer(crmMapLayer)) crmMapLayer.addTo(crmLeafletMap);
    aplicarBasemap(Boolean(crmMapState?.rotado));
    if (crmMapState) crmMapState.focusKey = null;
    refreshCRMMapMode();
    encuadrarBounds(crmMapState.encuadre || boundsDeVotos(crmMapLayer, crmMapState.config, crmMapState.votesByArea, crmMapState.fueraDelEncuadre), 24);
    setMapLevel(level);
  };
  controls.querySelectorAll('[data-level="localidad"]').forEach(b => b.addEventListener('click', () => {
    if (familia && b.dataset.capa !== crmMapState?.config?.clave) return cambiarCapaCiudad(familia[b.dataset.capa]);
    volver('localidad');
  }));
  /* Sin una localidad abierta, «Barrio» muestra la ciudad entera por barrio. */
  controls.querySelector('[data-level="barrio"]').addEventListener('click', () => { if (crmMapState?.config) { renderBarriosForArea(crmMapState.focusKey || '*'); setMapLevel('barrio'); } });
  setMapLevel(state.focusKey ? 'barrio' : 'localidad');
}
/* Cambia la escala de la ciudad (Cartagena: localidad ↔ UCG) y la recuerda
   para las demás vistas —años, promedio— de esta sesión. */
async function cambiarCapaCiudad(config) {
  const state = crmMapState; if (!config || !state) return;
  if (state.censo && state.territorio) {
    CAPA_ELEGIDA[config.match[0]] = config.clave;
    const modo = crmMapMode;
    if (crmBarrioLayer) { crmLeafletMap.removeLayer(crmBarrioLayer); crmBarrioLayer = null; }
    await pintarTerritorioCiudad(state.territorio, config, state.mesas, state.proy, modo);
    return;
  }
  if (!state.candidato) return;
  CAPA_ELEGIDA[config.match[0]] = config.clave;
  const modo = crmMapMode;
  if (crmBarrioLayer) { crmLeafletMap.removeLayer(crmBarrioLayer); crmBarrioLayer = null; }
  await renderCiudadMap(state.candidato, { config, mesas: state.mesas });
  /* Los años ya vistos quedaron guardados con la escala anterior: el
     promedio no puede mezclar localidades con UCG. */
  electionViewSnapshots = new Map();
  if (/^\d{4}$/.test(electionViewActive)) captureElectionSnapshot(electionViewActive);
  if (modo === 'proyectado') { crmMapMode = 'proyectado'; refreshCRMMapMode(); }
  refreshMapLevels();
}
/* Punto de entrada del mapa histórico. */
/* Si la campaña se muda a un territorio donde su historial no tiene un solo
   voto —de la JAL de Teusaquillo a la Alcaldía de Cartagena—, son DOS mapas
   distintos y no se reemplazan uno al otro (decisión de Ricardo, sep-2026):
   «Total» (y cada año) es su votación histórica, donde de verdad estuvo;
   «Proyectado» es el territorio al que aspira —Cartagena con sus escalas y
   barrios— con la meta repartida. Antes el territorio nuevo tapaba el
   historial y «Total» mostraba el censo de la ciudad destino. */
let DESTINO_FUERA = null, EN_DESTINO = false, pintandoDestino = 0, destinoTok = 0;
function campanaDestino() {
  const corp = $('otherCorporation').value || CAMPANA_ACTUAL?.corp || corporacionHistorica(crmCandidate) || 'concejo';
  return alcanceObjetivo() ? campanaActual(corp) : (CAMPANA_ACTUAL || campanaActual(corp));
}
async function loadHistoricalMap(candidate) {
  electionViewRecords = []; electionViewSnapshots = new Map(); electionViewActive = ''; $('crmMapToggles')?.remove(); crmMapState = null; recorteActivo = null; PROYECCION_DEPTAL = false;
  EN_DESTINO = false; DESTINO_FUERA = null; destinoTok++;
  if (crmBarrioLayer && crmLeafletMap) { crmLeafletMap.removeLayer(crmBarrioLayer); crmBarrioLayer = null; }
  if (alcanceObjetivo() && !(await historialEnCiudad(candidate))) DESTINO_FUERA = campanaDestino();
  $('crmMapPanelNum').textContent = '01 · Mapa de historial electoral';
  const records = electionViewHistory(candidate);
  if (records.length < 2) { await renderSingleElection(candidate); ensureCRMMapToggles(); refreshMapLevels(); return; }
  electionViewRecords = records; electionViewActive = records[records.length - 1].year;
  await showElectionYear(records[records.length - 1], { restoreToggles: false });
  renderElectionViewToggles();
}
/* El territorio de la campaña cuando el historial está en otra parte: el mismo
   mapa que ve una candidatura nueva, más los puestos de votación del municipio
   —dimensionados por censo, que es lo único honesto cuando no hay votos
   propios— para que el nivel «Puestos» tenga qué mostrar. */
async function renderTerritorioDeCampana() {
  /* La campaña que manda es la del formulario —es la que acaba de responder la
     persona—; CAMPANA_ACTUAL es el respaldo para cuando se vuelve al CRM. */
  const c = campanaDestino();
  $('crmMapPanelNum').textContent = '01 · Mapa del territorio de campaña';
  /* Los niveles del mapa anterior no sirven acá hasta saber si hay puestos. */
  $('crmMap')?.querySelector('.crm-map-levels')?.remove();
  MAPA_MUNICIPAL = null;
  if (await renderTerritorioCiudad(c)) return;
  const vista = await renderTerritorioObjetivo(c);
  /* Con salto a departamento hay algo que proyectar aunque no haya historial
     acá: los toggles TOTAL / PROYECTADO tienen que existir. */
  if (SALTO_ACTUAL?.tipo?.unidad === 'municipio') ensureCRMMapToggles();
  MAPA_MUNICIPAL = null;
  if (!CORP_MUNICIPAL.includes(c.corp) || !c.municipio) return;
  try {
    const codigo = codigoMunicipioObjetivo(); if (!codigo) return;
    const puestos = await puestosPorBarrio(), prefijo = `${String(c.departamento || '').padStart(2, '0')}${String(codigo).padStart(3, '0')}`;
    /* Una JAL compite en UNA localidad: mostrarle los puestos de toda la
       ciudad sería ofrecerle un territorio que no es el suyo. */
    const loc = c.corp === 'jal' ? normalizedText(cortoLocal(c.localidad)) : '';
    const mesas = Object.entries(puestos).filter(([code, p]) => code.slice(0, 5) === prefijo && (!loc || normalizedText(cortoLocal(p.mesa?.comNom || '')) === loc))
      .map(([code, p]) => ({ dep: code.slice(0, 2), mun: code.slice(2, 5), zon: code.slice(5, 7), pue: code.slice(7, 9), pueNom: p.barrio, v: p.censo }));
    if (mesas.length) { MAPA_MUNICIPAL = { mesas, nombre: loc ? c.localidad : c.municipio, censo: true, unidad: vista?.unidad || 'municipio', rotado: Boolean(vista?.rotado), encuadre: vista?.encuadre || null }; refreshMapLevels(); }
  } catch (e) { /* sin puestos, queda el polígono del municipio */ }
}
/* Alcaldía o Concejo en una ciudad con capa de comunas, sin votos propios ahí:
   la ciudad se dibuja por SUS unidades —con escalas, barrios y proyección—, no
   como un municipio verde entre los del departamento con «Municipio · Puestos».
   Sin historial no hay votos que mostrar, así que «Total» es el CENSO
   ELECTORAL (quién puede votar en cada unidad) y lo dice; «Proyectado» reparte
   la meta por donde votó su familia política en 2023 —la misma cuenta del
   Día D, que cae a la Alcaldía cuando la familia no tuvo lista al Concejo—.
   La JAL sigue en renderTerritorioObjetivo: compite en UNA localidad. */
async function renderTerritorioCiudad(c, modo = 'total') {
  if (!['concejo', 'alcaldia'].includes(c?.corp) || !c.municipio) return false;
  const config = cityLayerFor(c.municipio); if (!config) return false;
  /* cityLayerFor casa por «contiene»: CALIMA contiene CALI. Acá eso dibujaría
     el mapa de Cali con los puestos de Calima. Se exige que el nombre empiece
     o termine en la ciudad (SANTIAGO DE CALI, CARTAGENA DE INDIAS, BOGOTÁ D.C.). */
  const nom = normalizedText(c.municipio);
  if (!config.match.some(m => nom === m || nom.startsWith(m) || nom.endsWith(m))) return false;
  electionViewRecords = []; $('crmMapToggles')?.remove(); recorteActivo = null;
  try {
    const dep = String(c.departamento || '').padStart(2, '0');
    const mun = String(await C360Electorado.codigoMunicipio(dep, c.municipio).catch(() => '') || '').padStart(3, '0');
    if (mun === '000') return false;
    const puestos = await puestosPorBarrio(), prefijo = `${dep}${mun}`;
    const mesas = Object.entries(puestos)
      .filter(([code, p]) => code.slice(0, 5) === prefijo && p.censo > 0 && !ZONA_SIN_TERRITORIO.has(code.slice(5, 7)))
      .map(([, p]) => ({ ...p.mesa, munNom: c.municipio, pueNom: p.barrio, v: p.censo }));
    if (!mesas.length) return false;
    const proy = await proyeccionFamiliar(c, puestos);
    await pintarTerritorioCiudad(c, config, mesas, proy, modo);
    return true;
  } catch (e) { return false; }
}
/* Dónde votó la familia política en 2023, puesto por puesto. Las mesas del Día
   D no traen la comuna: se completa con el georef para que casen con la capa. */
async function proyeccionFamiliar(c, puestos) {
  try {
    const f = await window.C360DiaD?.fuente({ slugs: [], campana: { ...c, ruta: 'other' } });
    if (f?.modo !== 'territorio' || !f.mesas?.length) return null;
    const mesas = f.mesas.map(m => { const p = puestos?.[electoralPlaceCode(m)]?.mesa; return p ? { ...m, com: p.com, comNom: p.comNom } : m; });
    return { mesas, famTexto: f.famTexto, fuenteTexto: f.fuenteTexto, ampliada: f.ampliada, deAlcaldia: f.deAlcaldia, familia: f.familia };
  } catch (e) { return null; }
}
async function pintarTerritorioCiudad(c, config, mesas, proy, modo = 'total') {
  pintandoDestino++;
  try {
  if (config.prepare) await config.prepare();
  let geoData = await fetchJSON(`${S3}/mapas-2026/Ciudades-COM-LOC/${config.path}`); if (config.rotate) geoData = rotateGeoJSON90Left(geoData);
  const { votesByArea, namesByArea } = agregarPorArea(mesas, m => config.mesaKey ? config.mesaKey(m) : claveLocal(m));
  if (config.nombreDeCapa) Object.keys(namesByArea).forEach(k => delete namesByArea[k]);
  Object.keys(namesByArea).forEach(k => { if (namesByArea[k]) namesByArea[k] = String(namesByArea[k]).replace(/^\d+\s*/, ''); else delete namesByArea[k]; });
  const total = mesas.reduce((sum, m) => sum + Number(m.v || 0), 0), bogota = config.match[0] === 'BOGOTA';
  pintarCiudad({ geoData, config, mesas, total, votesByArea, namesByArea, targetKey: null, city: config.match[0], rotate: config.rotate, lugar: c.municipio, candidato: null,
    encuadre: bogota ? encuadreBogota() : config.ventana ? ventanaBounds(config.ventana) : null, fueraDelEncuadre: bogota ? ES_SUMAPAZ : null, note: '' });
  Object.assign(crmMapState, { censo: true, territorio: c, proy });
  $('crmMapPanelNum').textContent = '01 · Mapa del territorio de campaña';
  crmMapMode = modo;
  refreshCRMMapMode();
  refreshMapLevels();
  } finally { pintandoDestino--; }
}
/* «Proyectado» con el historial fuera del destino: se dibuja el territorio al
   que aspira. Las vistas por año se conservan para poder volver a ellas. */
async function pintarDestino() {
  const c = DESTINO_FUERA; if (!c) return;
  EN_DESTINO = true; const tok = ++destinoTok;
  const recs = electionViewRecords, snaps = electionViewSnapshots;
  if (crmBarrioLayer && crmLeafletMap) { crmLeafletMap.removeLayer(crmBarrioLayer); crmBarrioLayer = null; }
  $('crmMap')?.querySelector('.crm-territory-notice')?.remove();
  MAPA_MUNICIPAL = null;
  $('crmMapVotes').textContent = 'Cargando'; $('crmMapNote').textContent = 'Cargando el territorio de campaña…';
  let ok = false;
  if (SALTO_ACTUAL?.tipo?.unidad === 'municipio') {
    const goal = Number(String($('crmVoteNumber').textContent || '').replace(/\D/g, ''));
    ok = goal ? await pintarProyeccionDepartamental(goal) : false;
  }
  if (!ok) ok = await renderTerritorioCiudad(c, 'proyectado');
  if (!ok) await renderTerritorioDeCampana();
  if (tok !== destinoTok) return;
  electionViewRecords = recs; electionViewSnapshots = snaps; crmMapMode = 'proyectado';
  $('crmMapPanelNum').textContent = '01 · Mapa del territorio de campaña';
  if (recs.length >= 2) { electionViewActive = 'projected'; renderElectionViewToggles(); }
  else { ensureCRMMapToggles(); document.querySelectorAll('#crmMapToggles .map-toggle[data-mode]').forEach(b => b.classList.toggle('active', b.dataset.mode === 'proyectado')); }
}
/* La meta repartida por la huella de la familia; si no la hay, por el censo. */
function proyeccionTerritorio(state, goal) {
  const keyFn = m => state.config.mesaKey ? state.config.mesaKey(m) : claveLocal(m);
  const fam = state.proy?.mesas ? agregarPorArea(state.proy.mesas, keyFn).votesByArea : {};
  const conFamilia = Object.values(fam).some(v => v > 0);
  state.proyBase = conFamilia ? 'familia' : 'censo';
  return distributeVotes(conFamilia ? fam : (state.votesByArea || {}), goal);
}
function notaProyeccionTerritorio(state) {
  const p = state.proy;
  const ver = DESTINO_FUERA ? ' Su votación anterior está en «Total».' : '';
  if (state.proyBase !== 'familia' || !p) return `Usted no tiene votos en ${NOMBRE_BONITO(state.tituloLugar)}: la meta se reparte por el censo electoral de cada ${state.config.title}, que dice dónde hay gente que vota, no dónde lo apoyan.${ver}`;
  const alcaldia = p.deAlcaldia?.length ? ` —su familia no tuvo lista al Concejo en 2023 pero sí candidatura a la Alcaldía (${p.deAlcaldia.map(NOMBRE_BONITO).join(', ')}), y con esos votos se mide—` : '';
  const vecinas = p.ampliada ? ' (su familia casi no tuvo lista ahí, así que se mide con las vecinas del espectro)' : '';
  return `Usted no tiene votos en ${NOMBRE_BONITO(state.tituloLugar)}: la meta se reparte según dónde votó ${p.famTexto} en ${p.fuenteTexto}${alcaldia}${vecinas}. Es la misma cuenta del Día D.${ver}`;
}
/* Territorio objetivo de una candidatura NUEVA: no hay votos que pintar; se
   muestra dónde va a competir, con la unidad elegida resaltada. */
async function renderTerritorioObjetivo(c) {
  electionViewRecords = []; $('crmMapToggles')?.remove(); crmMapState = null; recorteActivo = null;
  $('crmMapTitle').textContent = 'Su territorio de campaña'; $('crmMapVotes').textContent = CRM_CORPORATIONS[c.corp]; $('crmMapNote').textContent = 'Cargando el territorio…';
  try {
    const dep = String(c.departamento || '').padStart(2, '0'), muni = normalizedText(c.municipio), loc = normalizedText(c.localidad);
    let geoData, isTarget, nameOf, rotate = false, unidad = 'municipio', filas;
    if (dep === '16' && CORP_MUNICIPAL.includes(c.corp)) {
      const src = rotateGeoJSON90Left(await fetchJSON(`${S3}/mapas-2026/Ciudades-COM-LOC/BOG-LOCALIDADX.json`)); rotate = true; unidad = 'localidad';
      geoData = src;   /* Sumapaz entra al dibujo; el encuadre la deja fuera (ES_SUMAPAZ) */
      nameOf = f => f.properties.LocNombre || 'Localidad'; isTarget = f => c.corp !== 'jal' || normalizedText(f.properties.LocNombre) === normalizedText(cortoLocal(c.localidad));
    } else if (CORP_MUNICIPAL.includes(c.corp) && c.corp === 'jal' && cityLayerFor(c.municipio, { jal: true })) {
      const cfg = cityLayerFor(c.municipio, { jal: true }); let src = await fetchJSON(`${S3}/mapas-2026/Ciudades-COM-LOC/${cfg.path}`); if (cfg.rotate) { src = rotateGeoJSON90Left(src); rotate = true; }
      geoData = src; unidad = cfg.title; nameOf = f => cfg.name(f.properties); isTarget = f => { if (cfg.casaLocalidad) return cfg.casaLocalidad(f.properties, c.localidad); const n = normalizedText(cfg.name(f.properties)), corto = normalizedText(cortoLocal(c.localidad)); return n === loc || (corto && (n === corto || n.includes(corto) || corto.includes(n))); };
    } else {
      geoData = await fetchJSON(`${S3}/mapas-2026/Departamentos-mps/${dep}.json`);
      nameOf = f => f.properties.mpio_cnmbr || 'Municipio'; isTarget = f => CORP_DEPARTAMENTAL.includes(c.corp) || normalizedText(f.properties.mpio_cnmbr) === muni;
    }
    crearMapa([4.6, -74.1], 5); aplicarBasemap(rotate);
    let targetLayer = null, n = 0;
    crmMapLayer = L.geoJSON(geoData, { style: f => ({ color: '#fff', weight: isTarget(f) ? 2 : 1, fillColor: isTarget(f) ? '#3e8a5b' : '#d8dfd7', fillOpacity: isTarget(f) ? .82 : .5 }), onEachFeature: (f, layer) => { layer.bindTooltip(`<strong>${NOMBRE_BONITO(nameOf(f))}</strong>`, { sticky: true }); if (isTarget(f)) { n++; if (!targetLayer) targetLayer = layer; } } }).addTo(crmLeafletMap);
    const capaEncuadre = CORP_DEPARTAMENTAL.includes(c.corp) || n > 1 ? crmMapLayer : (targetLayer || crmMapLayer);
    encuadrarBounds(capaEncuadre === crmMapLayer && rotate ? boundsSin(crmMapLayer, ES_SUMAPAZ) : capaEncuadre.getBounds(), 24);
    filas = geoData.features.map(nameOf).sort((a, b) => a.localeCompare(b, 'es'));
    $('crmBreakdown').innerHTML = `<h4>${CORP_DEPARTAMENTAL.includes(c.corp) ? `Municipios de ${c.departamentoNombre}` : `${unidad === 'municipio' ? 'Municipios' : unidad === 'comuna' ? 'Comunas' : 'Localidades'} en el mapa`}</h4>` + filas.map(nm => `<div class="crm-breakdown-item static${normalizedText(nm) === (c.corp === 'jal' ? loc : muni) ? ' is-target' : ''}"><span class="crm-breakdown-row"><b>${escHtml(NOMBRE_BONITO(nm))}</b></span></div>`).join('');
    $('crmMapNote').textContent = CORP_DEPARTAMENTAL.includes(c.corp) ? `La circunscripción es todo ${c.departamentoNombre}: ${filas.length} municipios.` : `En verde, el territorio al que aspira. Sin historial propio no hay votos que distribuir; la meta de la derecha sale de los resultados de 2023 en ese territorio.`;
    /* Qué unidad quedó dibujada y si va rotada: los niveles del mapa se
       nombran con eso, y volver al primero tiene que rehacer este encuadre. */
    return { unidad, rotado: rotate, encuadre: capaEncuadre === crmMapLayer && rotate ? boundsSin(crmMapLayer, ES_SUMAPAZ) : capaEncuadre.getBounds() };
  } catch (e) {
    $('crmMap').innerHTML = '<div style="padding:28px;color:#667068">No fue posible cargar el territorio en este momento.</div>'; crmLeafletMap = null; crmMapLayer = null; crmTileLayer = null;
    $('crmBreakdown').innerHTML = '<p class="helper">No fue posible cargar el territorio.</p>'; $('crmMapNote').textContent = 'La fuente cartográfica no respondió.';
  }
}

/* ─── 9 bis. El territorio por dentro: arquetipos y perfil del votante ───────
   Dos lecturas del mismo territorio que el mapa no da, las dos ponderadas por
   SU votación —no «cómo es la ciudad» sino «cómo es el pedazo de ciudad donde
   están sus votos»:

   · ARQUETIPOS (Medellín y Cartagena). El Proyecto DC reconstruyó barrio por
     barrio qué mueve el voto —protección, continuidad, supervivencia, castigo,
     pertenencia— con Alcaldía, Concejo y JAL de 2015, 2019 y 2023, y proyectó
     2027. Acá se cruza con los votos de la persona. Otras ciudades ven la
     tarjeta apagada diciendo qué falta, que es más honesto que esconderla.

   · PERFIL DEL VOTANTE. El voto es secreto y nadie puede decir quién votó por
     usted; lo que sí se puede es describir el ELECTORADO de los puestos donde
     están sus votos. Sexo sale del censo por puesto de la Registraduría
     (columnas MUJERES/HOMBRES de PUESTOS_GEOREF) y rural/urbano de la zona
     electoral (99 = rural). La edad necesita el censo por edad por puesto, que
     todavía no está publicado: la tarjeta lo dice en vez de estimarlo.        */
/* Una candidatura nueva no tiene archivo de mesas y no por eso se rompen las
   tarjetas: se leen con cero votos y cada una decide qué mostrar. */
async function mesasDelHistorial() { try { return (await datosCandidatura(crmCandidate)).mesas || []; } catch (e) { return []; } }
function municipioDeCampana() {
  const a = alcanceObjetivo();
  /* Una JAL también compite dentro de un municipio: su alcance es la localidad
     y el municipio sigue siendo el de los arquetipos. */
  return (a?.tipo === 'municipio' || a?.tipo === 'localidad') && a.municipio ? `${String(a.departamento).padStart(2, '0')}${String(a.municipio).padStart(3, '0')}` : '';
}
function municipioMayoritario(mesas) { return C360Electorado.municipioMayoritario(mesas); }
/* ⚠️ Una candidatura NUEVA no pasa por el formulario de la ruta con historial,
   así que `municipioDeCampana()` —que lee ese formulario— sale vacío: Nury,
   probando como candidata nueva a la Alcaldía de Cartagena, veía la tarjeta
   apagada («Por ahora, Medellín y Cartagena»), porque sin votos propios
   tampoco había municipio mayoritario (sep-29-2026). Sin candidato de
   historial manda la campaña guardada (CAMPANA_ACTUAL). */
async function municipioArquetipos() {
  return municipioDeCampana() || (!crmCandidate ? await C360ArqLectura.municipioDeCampana(CAMPANA_ACTUAL) : '');
}
/* La tarjeta 05: titular con el arquetipo donde está la mayoría de sus votos.
   La lectura entera vive en candidato-360-arq-lectura.js y la página completa
   en candidato-360-arquetipos.html; esto es solo el adelanto. */
async function pintarArquetipos() {
  const card = $('crmArquetipos'); if (!card) return;
  const A = window.C360ArqLectura;
  const mesas = await mesasDelHistorial();
  const ciudad = A.ciudadDe(await municipioArquetipos(), mesas);
  if (!ciudad) {
    card.classList.add('module-apagado');
    $('crmArqTitulo').textContent = 'Por ahora, Medellín y Cartagena.';
    $('crmArqCopy').textContent = 'La cartografía emocional —qué mueve el voto en cada barrio— está reconstruida para los barrios de Medellín y de Cartagena con las elecciones de 2015, 2019 y 2023. Cuando exista para su ciudad, esta tarjeta se enciende sola.';
    $('crmArqDato').textContent = '—'; $('crmArqSub').textContent = 'sin cartografía emocional acá';
    return;
  }
  const nombreCiudad = ciudad === 'cartagena' ? 'Cartagena' : 'Medellín';
  card.classList.remove('module-apagado');
  $('crmArqTitulo').textContent = `Leyendo los barrios de ${nombreCiudad}…`;
  $('crmArqCopy').textContent = ciudad === 'cartagena' ? 'Cruzando su votación con los ocho arquetipos de la ciudad.' : 'Cruzando su votación con los cinco arquetipos del territorio.';
  try {
    const L = await A.leer(ciudad, mesas), top = A.principal(L);
    if (!top) throw new Error('sin cruce');
    const f = L.ficha(top.id), pct = Math.round(top.share * 100);
    const lema = ciudad === 'cartagena' ? `${f.lema}. La emoción que lo ordena: ${f.emocion}.` : f.lema;
    const unidades = L.filasComuna.length === 1 ? `una ${L.unidad}` : `${L.filasComuna.length} ${L.unidades}`;
    const art = ciudad === 'cartagena' ? 'el arquetipo ' : '';
    $('crmArqTitulo').textContent = L.conVotos ? `Su voto vive en barrios de ${ciudad === 'cartagena' ? 'arquetipo ' : ''}${f.nombre.toLowerCase()}.` : `${nombreCiudad} vota desde ${art}${f.nombre.toLowerCase()}.`;
    $('crmArqCopy').textContent = `${lema} ${L.conVotos ? `Es el arquetipo de ${pct} % de sus votos en la ciudad, repartidos en ${unidades}.` : 'Es el arquetipo con más peso en la ciudad; cuando tenga votos propios acá la lectura se hace con ellos.'}`;
    $('crmArqDato').textContent = `${pct} %`;
    $('crmArqSub').textContent = L.conVotos ? 'de sus votos, en ese arquetipo' : 'del voto de la ciudad';
  } catch (e) {
    $('crmArqTitulo').textContent = 'No pudimos leer los arquetipos.';
    $('crmArqCopy').textContent = 'La fuente de la cartografía emocional no respondió. Vuelva a abrir el CRM en un momento.';
    $('crmArqDato').textContent = '—'; $('crmArqSub').textContent = 'fuente no disponible';
  }
}

/* ── Perfil del votante ─────────────────────────────────────────────────────
   Ponderar por votos el censo del puesto responde «cómo es el electorado
   donde usted saca votos», que es distinto de «quién votó por usted» —eso no
   lo sabe nadie— y distinto del promedio del municipio, que es contra lo que
   se compara para que el número signifique algo. */

async function perfilDelVotante() { return C360Electorado.perfil(await mesasDelHistorial()); }
let PERFIL_ACTUAL = null;
const pct1 = x => `${(x * 100).toFixed(1).replace('.', ',')} %`;
/* ── 09 · El día de la elección ───────────────────────────────────────────
   La tarjeta adelanta la cifra que resuelve el panel: con cuánta gente cubre
   el 70 % de su votación. El plan completo vive en candidato-360-diad.html.
   Ojo: acá no se pide ni se guarda un dato del equipo del candidato — los
   nombres de sus testigos son su base de datos, no la nuestra. */
async function pintarDiaD() {
  const card = $('crmDiaD'); if (!card || !window.C360DiaD) return;
  const D = window.C360DiaD;
  $('crmDiaDTitulo').textContent = 'Armando el plan de testigos…';
  try {
    /* La misma fuente que el panel 09: los testigos cuidan la candidatura que
       viene, así que el plan sale del territorio y la corporación a los que se
       lanza, no de la elección anterior. */
    const slugs = crmCandidate ? (crmCandidate.history?.length ? crmCandidate.history : [crmCandidate]).map(c => c.slug).filter(Boolean) : [];
    const F = await D.fuente({ slugs, campana: CAMPANA_ACTUAL || {} });
    if (!F.mesas.length) throw new Error('sin puestos');
    const plan = D.plan(F.mesas, await D.hvpDe(F.mesas));
    if (!plan.puestos.length) throw new Error('sin puestos');
    const n = D.testigosPara(plan, .7), c = D.cobertura(plan, n);
    const av = D.alertas(c), peor = av[0], N = x => x.toLocaleString('es-CO');
    const T = F.modo === 'territorio';
    $('crmDiaDTitulo').textContent = T
      ? `Con ${N(n)} testigo${n === 1 ? '' : 's'} cubre el 70 % de los votos de ${F.famTexto}.`
      : `Con ${N(n)} testigo${n === 1 ? '' : 's'} cubre el 70 % de su votación.`;
    $('crmDiaDCopy').textContent = (T
      ? `Para ${F.corpTexto} sus testigos cuidan la lista en ${N(plan.puestos.length)} puestos. Los ${N(n)} primeros, según ${F.fuenteTexto}, suman ${N(c.mesas)} mesas.`
      : `Sus votos están repartidos en ${N(plan.puestos.length)} puestos y no pesan igual: los ${N(n)} primeros suman ${N(c.mesas)} mesas.`) +
      (peor ? ` De esos, ${N(peor.n)} están ${peor.titulo}.` : '');
    $('crmDiaDDato').textContent = N(n);
    $('crmDiaDSub').textContent = 'testigos para el 70 %';
  } catch (e) {
    $('crmDiaDTitulo').textContent = 'Todavía no hay plan para esta candidatura.';
    $('crmDiaDCopy').textContent = 'Sin votos por puesto en el territorio al que se lanza no hay qué priorizar, y priorizar al azar sería peor que no hacerlo. La hoja de vida de los puestos sí existe y la va a encontrar en el panel.';
    $('crmDiaDDato').textContent = '—'; $('crmDiaDSub').textContent = 'sin votos por puesto';
  }
}
async function pintarPerfil() {
  const card = $('crmPerfil'); if (!card) return;
  PERFIL_ACTUAL = null;
  $('crmPerfilTitulo').textContent = 'Leyendo el electorado de sus puestos…';
  try {
    const P = await perfilDelVotante();
    if (!P.votos || P.mujeres === null) throw new Error('sin censo');
    PERFIL_ACTUAL = P;
    const dif = P.mujeresMunicipio === null ? null : P.mujeres - P.mujeresMunicipio;
    const sesgo = dif === null || Math.abs(dif) < .005 ? 'igual que el promedio del municipio' : dif > 0 ? `${pct1(Math.abs(dif))} más mujeres que el promedio del municipio` : `${pct1(Math.abs(dif))} menos mujeres que el promedio del municipio`;
    const campo = P.rural >= .5 ? 'rural' : P.rural >= .15 ? 'mixto, con una pata rural' : 'urbano';
    $('crmPerfilTitulo').textContent = `Su voto es ${campo}: ${pct1(P.mujeres)} de mujeres.`;
    $('crmPerfilCopy').textContent = `El electorado de los puestos donde usted saca votos, ponderado por cuántos saca en cada uno: ${sesgo}. ${P.rural ? `${pct1(P.rural)} de sus votos están en puestos rurales` : 'Ninguno de sus votos está en puestos rurales'}${P.ruralMunicipio !== null ? `, contra ${pct1(P.ruralMunicipio)} del censo del municipio` : ''}.`;
    $('crmPerfilDato').textContent = pct1(P.mujeres);
    $('crmPerfilSub').textContent = 'mujeres en el censo de sus puestos';
  } catch (e) {
    $('crmPerfilTitulo').textContent = 'Todavía no hay perfil para esta candidatura.';
    $('crmPerfilCopy').textContent = 'Los puestos de su votación no tienen censo publicado, así que preferimos no estimar un perfil que no podemos sostener.';
    $('crmPerfilDato').textContent = '—'; $('crmPerfilSub').textContent = 'sin censo por puesto';
  }
}
/* El análisis largo —territorio, familias políticas y la votación que debería
   buscar— vive en candidato-360-electorado.html, que tiene sitio para gráficos
   y figuras. Acá queda el resumen que cabe en una tarjeta y el botón que lleva
   allá; las cuentas son las mismas porque las hace el módulo compartido. */

/* ─── 9 quáter. Dónde recoger las firmas ─────────────────────────────────────
   Quien va por firmas no tiene partido cuya huella seguir, pero sí tiene una
   familia política: la que él mismo eligió en el espectro. Los votos de esa
   familia en el territorio dicen dónde una firma cuesta menos trabajo —donde
   ya hay gente que piensa parecido— y esa es toda la promesa de esta tarjeta:
   no predice apoyo, ordena la logística.

   El requisito legal se estima con la regla del artículo 9 de la Ley 130 de
   1994: el 20 % del censo electoral dividido por los cargos a proveer (uno,
   en alcaldía y gobernación), con el tope de 50.000 firmas que la misma norma
   fija. Se muestra como ESTIMACIÓN y se dice que la cifra exacta la resuelve
   la Registraduría, porque el censo de corte y las reformas la mueven.       */
const FIRMAS_FRACCION = .2, FIRMAS_TOPE = 50000;
function requisitoDeFirmas(censo) {
  const crudo = Math.ceil(Number(censo || 0) * FIRMAS_FRACCION);
  return { crudo, exigido: Math.min(crudo, FIRMAS_TOPE), topeAplica: crudo > FIRMAS_TOPE };
}
/* El censo del territorio de la candidatura, sumando los puestos publicados. */
async function censoDelTerritorio(campana) {
  const puestos = await puestosPorBarrio();
  const dep = String(campana?.departamento || '').padStart(2, '0');
  const mun = CORP_MUNICIPAL.includes(campana?.corp) ? String(codigoMunicipioObjetivo() || '').padStart(3, '0') : '';
  const prefijo = mun ? `${dep}${mun}` : dep;
  let censo = 0, n = 0;
  /* El censo por sector sirve de plan B para el reparto: dice dónde está la
     gente aunque no se sepa cómo votó. */
  const porSector = {};
  Object.entries(puestos).forEach(([code, p]) => {
    if (code.slice(0, prefijo.length) !== prefijo) return;
    censo += Number(p.censo || 0); n++;
    /* La columna BARRIO trae «NO APLICA» en los puestos que no están en un
       barrio (cárceles, censo consolidado, veredas sin nombre): eso no es un
       sector al que se pueda mandar a alguien a recoger firmas. */
    const crudo = String(p.barrio || '').trim();
    const nombre = !crudo || /^(NO APLICA|N\/?A|SIN INFORMACION)$/i.test(crudo) ? 'Sin barrio identificado' : NOMBRE_BONITO(crudo);
    porSector[nombre] = (porSector[nombre] || 0) + Number(p.censo || 0);
  });
  return { censo, puestos: n, porSector };
}
/* La pregunta que deja la tarjeta es inevitable: «¿más firmas que votos para
   ganar?». En un municipio pequeño, sí — la ley pide el 20 % del censo y el
   tope de 50.000 solo alivia a las ciudades grandes—, así que se dice en vez
   de dejar al usuario pensando que el número está mal. */
function comparaConLaMeta(exigido) {
  const meta = Number(META_ACTUAL?.target || 0); if (!meta || !exigido) return '';
  const razon = exigido / meta;
  if (exigido > meta) return ` Son más firmas que los ${meta.toLocaleString('es-CO')} votos de su meta: en municipios pequeños inscribirse por firmas cuesta más que ganar.`;
  if (razon >= .85) return ` Es casi tanto como los ${meta.toLocaleString('es-CO')} votos de su meta.`;
  if (razon <= .5) return ` Es menos de la mitad de los ${meta.toLocaleString('es-CO')} votos de su meta.`;
  return ` Es el ${Math.round(razon * 100)} % de los ${meta.toLocaleString('es-CO')} votos de su meta.`;
}
let FIRMAS_ACTUAL = null;
async function lecturaFirmas(campana) {
  const bloque = campana?.espectro; if (!bloque) return null;
  const unidad = CORP_MUNICIPAL.includes(campana.corp) ? 'localidad' : 'municipio';
  /* Las firmas se recogen donde va a ser la CANDIDATURA, no donde fue la
     anterior: quien se muda de ciudad tenía el reparto en la ciudad vieja,
     porque la huella se buscaba con las mesas de su historial. El territorio
     de la campaña manda, y el historial solo entra si no hay campaña. */
  const delTerritorio = { dep: String(campana?.departamento || ''), mun: String(codigoMunicipioObjetivo() || '') };
  const mesas = delTerritorio.dep ? [delTerritorio] : await mesasDelHistorial();
  const [territorio, rd] = await Promise.all([
    censoDelTerritorio(campana),
    (mesas.length ? resultadosDestino(unidad, mesas, campana) : Promise.resolve(null)).catch(() => null),
  ]);
  const req = requisitoDeFirmas(territorio.censo);
  const hb = rd ? huellaBloque(rd.porArea, bloque) : { huella: null };
  const props = hb.huella ? proporciones(hb.huella) : null;
  const reparto = props ? distributeVotes(hb.huella, req.exigido) : null;
  const nombres = rd?.porArea || {};
  let base = 'bloque';
  let filas = reparto
    ? Object.entries(reparto).map(([area, firmas]) => ({ area, nombre: NOMBRE_BONITO(nombres[area]?.name || nombres[area]?.nombre || nombres[area]?.comuna || area), firmas, votos: hb.huella[area] || 0 }))
      .filter(f => f.firmas > 0).sort((a, b) => b.firmas - a.firmas)
    : [];
  /* Los resultados de concejo solo bajan a comuna en once ciudades: en La Ceja
     —y en el 95 % de los municipios— no hay huella de familia por área. Antes
     la tarjeta se rendía ahí («no podemos repartirlas»), que es dejar sin plan
     justo a quien más lo necesita. El plan B no inventa afinidad: reparte por
     CENSO de los puestos, que es dónde está la gente, y lo dice. */
  if (!filas.length && territorio.porSector && Object.keys(territorio.porSector).length) {
    const porCenso = distributeVotes(territorio.porSector, req.exigido);
    filas = Object.entries(porCenso).map(([nombre, firmas]) => ({ area: nombre, nombre, firmas, censo: territorio.porSector[nombre] || 0 }))
      .filter(f => f.firmas > 0).sort((a, b) => b.firmas - a.firmas);
    base = filas.length ? 'censo' : base;
  }
  FIRMAS_ACTUAL = { bloque, req, territorio, filas, unidad, campana, base, cobertura: hb.cobertura || 0 };
  return FIRMAS_ACTUAL;
}
/* El copy se arma aparte porque la meta de votos llega DESPUÉS de las
   tarjetas (es una estimación con su propia consulta): cuando aterriza, la
   comparación se vuelve a escribir en vez de quedarse sin ella. */
function textoFirmas(L) {
  const etiqueta = window.PartidosBloques?.BLOQUE_LABEL?.[L.bloque] || 'su familia política';
  const cuanto = `El ${Math.round(FIRMAS_FRACCION * 100)} % del censo de su territorio (${L.territorio.censo.toLocaleString('es-CO')} personas)${L.req.topeAplica ? `, con el tope legal de ${FIRMAS_TOPE.toLocaleString('es-CO')}` : ''}.`;
  const cabeza = L.filas.slice(0, 3), peso = Math.round(cabeza.reduce((t, f) => t + f.firmas, 0) / L.req.exigido * 100);
  return `${cuanto}${comparaConLaMeta(L.req.exigido)} ${!L.filas.length ? 'Todavía no podemos repartirlas por falta de datos del territorio.'
    : L.base === 'censo' ? `Repartidas por el censo de los puestos —acá los resultados no bajan de la cabecera municipal—: ${cabeza.map(f => f.nombre).join(', ')} concentran ${peso} %.`
    : `Repartidas por donde vota ${etiqueta.toLowerCase()}: ${cabeza.map(f => f.nombre).join(', ')} concentran ${peso} % de la meta.`}`;
}
async function pintarFirmas() {
  const card = $('crmFirmas'); if (!card) return;
  const campana = CAMPANA_ACTUAL;
  const firmas = campana?.avales === 'firmas';
  card.classList.toggle('hidden', !firmas);
  if (!firmas) { FIRMAS_ACTUAL = null; return; }
  $('crmFirmasBtn').disabled = true;
  $('crmFirmasTitulo').textContent = 'Calculando cuántas firmas y dónde…';
  $('crmFirmasCopy').textContent = 'Cruzando el censo del territorio con los votos de su familia política.';
  try {
    const L = await lecturaFirmas(campana); if (!L) throw new Error('sin espectro');
    const etiqueta = window.PartidosBloques?.BLOQUE_LABEL?.[L.bloque] || 'su familia política';
    $('crmFirmasTitulo').textContent = `Necesita unas ${L.req.exigido.toLocaleString('es-CO')} firmas.`;
    $('crmFirmasCopy').textContent = textoFirmas(L);
    $('crmFirmasDato').textContent = L.req.exigido.toLocaleString('es-CO');
    $('crmFirmasSub').textContent = 'firmas estimadas';
    $('crmFirmasBtn').disabled = false;
  } catch (e) {
    $('crmFirmasTitulo').textContent = 'Todavía no podemos estimar sus firmas.';
    $('crmFirmasCopy').textContent = 'Falta el censo del territorio o los resultados de su familia política. Vuelva a abrir el CRM en un momento.';
    $('crmFirmasDato').textContent = '—'; $('crmFirmasSub').textContent = 'sin datos suficientes';
  }
}
function mostrarFirmas() {
  const L = FIRMAS_ACTUAL; if (!L) return;
  const etiqueta = window.PartidosBloques?.BLOQUE_LABEL?.[L.bloque] || 'su familia política';
  const unidad = L.unidad === 'localidad' ? 'comuna o localidad' : 'municipio';
  const max = Math.max(1, ...L.filas.map(f => f.firmas));
  $('introModalKicker').textContent = 'Candidato 360 · recolección de firmas';
  $('introModalTitle').textContent = `Dónde recoger sus ${L.req.exigido.toLocaleString('es-CO')} firmas`;
  $('introModalText').innerHTML = `
    <p>${L.base === 'censo'
      ? `En este territorio los resultados de 2023 no bajan de la cabecera municipal, así que no hay huella de <b>${escHtml(etiqueta.toLowerCase())}</b> por área. El reparto se hace entonces por <b>censo electoral de cada puesto</b>: no dice dónde hay afinidad, dice dónde hay gente, que para recoger firmas es la mitad del problema.`
      : `Por firmas no hay huella de partido que seguir, así que se usa la de <b>${escHtml(etiqueta.toLowerCase())}</b> —la familia que usted eligió— en las últimas elecciones de este territorio. No predice que esa gente lo apoye: dice dónde hay más personas a las que la conversación les suena, que es donde una firma cuesta menos trabajo.`}</p>
    <p style="margin-bottom:8px"><b>Cuántas</b></p>
    <ul class="puntaje-escala">
      <li><b>${L.territorio.censo.toLocaleString('es-CO')}</b> personas en el censo electoral de su territorio, sumando los ${L.territorio.puestos.toLocaleString('es-CO')} puestos de votación publicados.</li>
      <li><b>${L.req.crudo.toLocaleString('es-CO')}</b> es el ${Math.round(FIRMAS_FRACCION * 100)} % de ese censo, que es la regla del artículo 9 de la Ley 130 de 1994 para un cargo uninominal.</li>
      ${L.req.topeAplica ? `<li><b>${FIRMAS_TOPE.toLocaleString('es-CO')}</b> es el tope que fija la misma norma: por grande que sea el territorio, no se exigen más.</li>` : ''}
      ${META_ACTUAL?.target ? `<li><b>${Number(META_ACTUAL.target).toLocaleString('es-CO')}</b> son los votos de su meta para ganar. ${L.req.exigido > META_ACTUAL.target ? 'Sí: le piden <b>más firmas que votos</b>. No es un error del cálculo — es la regla: el 20 % del censo se aplica igual en un municipio de 55.000 habilitados que en uno de 500.000, y el tope de 50.000 solo alivia a las ciudades grandes.' : 'Las firmas son el primer filtro; los votos, el segundo.'}</li>` : ''}
    </ul>
    <p style="margin-bottom:8px"><b>Dónde, ${L.base === 'censo' ? 'puesto por puesto' : `${unidad} por ${unidad}`}</b></p>
    ${L.filas.length ? `<ul class="arq-lista">${L.filas.slice(0, 12).map(f => `<li><span class="arq-punto" style="background:${window.PartidosBloques?.BLOQUE_COLOR?.[L.bloque] || 'var(--green)'}"></span><b>${f.firmas.toLocaleString('es-CO')}</b> ${escHtml(f.nombre)}<em>${Math.round(f.firmas / max * 100)} %</em></li>`).join('')}</ul>`
      : '<p>No hay resultados de esa familia política en este territorio, así que no repartimos nada: preferimos no inventar un plan de recolección.</p>'}
    <p class="puntaje-nota">La cifra es una <b>estimación</b>: el censo de corte y las resoluciones de la Registraduría mueven el número exacto, y conviene confirmarlo con ellos antes de imprimir formularios. El reparto sale ${L.base === 'censo' ? 'del censo electoral de cada puesto publicado por la Registraduría' : `de los votos de ${escHtml(etiqueta.toLowerCase())} en la última elección comparable de este territorio`}, no de una encuesta.</p>`;
  $('introModal').classList.add('open');
}

/* ─── 9 bis. Endoso de aliados ───────────────────────────────────────────────
   El cálculo vive en candidato-360-endoso.js (window.C360Endoso), el mismo que
   usa el panel candidato-360-endoso.html: la tarjeta y el panel no pueden dar
   cifras distintas. Acá queda solo lo que depende del CRM —el territorio de la
   campaña, cómo se nombran sus áreas— y la interfaz del modal. */
const E360 = window.C360Endoso;
let ENDOSO = { aliados: [], lectura: null };
const endosoCand = () => crmCandidate?.id || (NUEVO?.nombre ? `nuevo-${normalizedText(NUEVO.nombre)}` : 'sin-candidatura');
function endosoKey() { return E360.clave(SESSION.user?.email, endosoCand()); }
/* La meta del escenario elegido (la tarjeta 02), no siempre la probable. */
function endosoMeta() { return escenariosDe(META_ACTUAL?.detalle)?.[META_ESCENARIO]?.votos || Number(META_ACTUAL?.target || 0); }
function endosoCargar() { ENDOSO.aliados = E360.cargar(endosoKey()); }
function endosoGuardar() { E360.guardar(endosoKey(), ENDOSO.aliados); }
/* El territorio contra el que se recorta: lo que esté puesto en el formulario
   (la campaña que se está editando) y, si no, lo que resuelve el motor con la
   campaña guardada o con su última candidatura — la misma cuenta del panel. */
async function endosoAlcance() {
  const a = alcanceObjetivo(); if (a) return a;
  return E360.alcanceDe({ campana: CAMPANA_ACTUAL || SESSION.vinculo?.campana || {}, corpHistorica: corporacionHistorica(crmCandidate),
    mesasPropias: crmCandidate ? await mesasDelHistorial() : null, codigoMunicipio: C360Electorado.codigoMunicipio });
}
function endosoLugar(alcance) {
  if (!alcance) return 'su territorio';
  if (alcance.tipo === 'departamento') return nombreDepartamento?.(alcance.departamento) || NOMBRE_BONITO(alcance.nombre) || 'el departamento';
  if (alcance.tipo === 'localidad') return NOMBRE_BONITO(cortoLocal(alcance.localidad)) || 'la localidad';
  /* municipioNombre va sin espacios («LACEJA»): es llave de comparación, no
     un nombre. Solo es el último recurso. */
  return NOMBRE_BONITO(alcance.nombre || $('campaignMunicipality')?.value || CAMPANA_ACTUAL?.municipio || alcance.municipioNombre || '') || 'el municipio';
}
const endosoArea = (m, alcance) => NOMBRE_BONITO(E360.areaDe(m, alcance));
async function endosoEvaluar() {
  const alcance = await endosoAlcance();
  let propio = null;
  if (crmCandidate) { try { propio = await mesasDelHistorial(); } catch { propio = null; } }
  /* La corporación de la campaña: de sus válidos de 2023 sale el electorado
     de cada puesto, para no contar dos veces a quien votó por dos aliados. */
  const corpCampana = currentTargetTerritory()?.corporation || CAMPANA_ACTUAL?.corp || SESSION.vinculo?.campana?.corp || corporacionHistorica(crmCandidate);
  /* Un líder de zona se compara con el resto de su comuna, que sale del georef. */
  const comunaDe = ENDOSO.aliados.some(a => a.tipo === 'lider') ? E360.comunaDesde(await C360Electorado.puestos().catch(() => null)) : null;
  return E360.evaluar(ENDOSO.aliados, { alcance, lugar: endosoLugar(alcance), enAlcance: mesaEnAlcance, areaDe: endosoArea, propio, corpCampana, comunaDe });
}
async function pintarEndoso() {
  const card = $('crmEndoso'); if (!card) return;
  endosoCargar();
  const n = ENDOSO.aliados.length;
  if (!n) {
    ENDOSO.lectura = null;
    $('crmEndosoTitulo').textContent = '¿Cuántos votos le pueden pasar sus aliados?';
    $('crmEndosoCopy').textContent = 'Sume a los líderes y excandidatos que lo van a apoyar. Medimos cuánto le pasaron antes a quien apoyaron y cuántos de sus votos caen en su territorio.';
    $('crmEndosoDato').textContent = '—'; $('crmEndosoSub').textContent = 'sin aliados todavía';
    return;
  }
  $('crmEndosoTitulo').textContent = 'Calculando el endoso de sus aliados…';
  $('crmEndosoDato').textContent = '…';
  try {
    const L = ENDOSO.lectura = await endosoEvaluar();
    const meta = endosoMeta();
    const cifra = x => x.toLocaleString('es-CO');
    const medidos = L.filas.filter(f => f.fuente === 'medida' || f.fuente === 'regresion' || (f.fuente === 'lider' && f.origen === 'medido')).length;
    /* Un rango, no una cifra: la retención del voto propio varía mucho entre
       personas, y un solo número escondería esa dispersión. */
    $('crmEndosoTitulo').textContent = L.bajo === L.alto ? `Sus aliados le pueden pasar hasta ${cifra(L.total)} votos.` : `Sus aliados le pueden pasar entre ${cifra(L.bajo)} y ${cifra(L.alto)} votos.`;
    $('crmEndosoCopy').textContent = `${n === 1 ? 'Su aliado tiene' : `Sus ${n} aliados tienen`} ${cifra(L.techo)} votos en ${L.lugar}${meta ? `; el punto medio es el ${Math.round(L.total / meta * 100)} % de su meta` : ''}${L.dobleConteo > 0 ? `, sin contar dos veces a quien votó por más de uno` : ''}. ${medidos ? `${medidos} ${medidos === 1 ? 'tasa sale medida' : 'tasas salen medidas'} con a quién apoyaron antes.` : 'Diga a quién apoyó cada uno para medir su tasa: hoy se estima con lo que conserva cada uno de su propio voto.'}`;
    $('crmEndosoDato').textContent = L.total.toLocaleString('es-CO');
    $('crmEndosoSub').textContent = `votos, punto medio · ${n} ${n === 1 ? 'aliado' : 'aliados'}`;
  } catch (e) {
    $('crmEndosoTitulo').textContent = 'No pudimos calcular el endoso todavía.';
    $('crmEndosoDato').textContent = '—'; $('crmEndosoSub').textContent = 'vuelva a intentar en un momento';
  }
}
/* ─── 9 ter. Contendientes (tarjeta 10) ─────────────────────────────────────
   El cálculo vive en candidato-360-contendientes.js (window.C360Contendientes);
   el panel candidato-360-contendientes.html llama la misma `leer` con las
   mismas entradas —campaña, candidaturas, mesas, territorio y el escalón
   probable de la meta—, así que las dos pantallas dan las mismas cifras.
   En vitrina el plano deja nítidos los tres de más presión (su historial ya
   es público en el índice) y a los demás los pinta sin nombre. */
let CONT_TURNO = 0;
async function pintarContendientes() {
  const card = $('crmContendientes'), K = window.C360Contendientes; if (!card || !K) return;
  const turno = ++CONT_TURNO;
  $('crmContTitulo').textContent = 'Buscando a sus rivales probables…';
  $('crmContDato').textContent = '…'; $('crmContSub').textContent = 'leyendo el registro'; $('crmContPlano').innerHTML = ''; $('crmContRevision').textContent = '';
  try {
    const campana = CAMPANA_ACTUAL || SESSION.vinculo?.campana || {};
    const corp = currentTargetTerritory()?.corporation || campana.corp || corporacionHistorica(crmCandidate);
    const alcance = await endosoAlcance();
    const slugs = crmCandidate ? (crmCandidate.history?.length ? crmCandidate.history : [crmCandidate]).map(c => c.slug).filter(Boolean) : [];
    const propias = crmCandidate ? await mesasDelHistorial() : null;
    const meta = escenariosDe(META_ACTUAL?.detalle)?.probable?.votos || Number(META_ACTUAL?.target || 0);
    const L = await K.leer({ campana: { ...campana, corp }, slugs, mesasPropias: propias, alcance, meta, usuario: { nombre: crmCandidate?.nombre || NUEVO?.nombre || '', slugs } });
    if (turno !== CONT_TURNO) return;
    const r = L.resumen, N = x => Number(x || 0).toLocaleString('es-CO'), top = L.plano.slice(0, 3);
    if (!r.enIndice) throw new Error('sin rivales');
    $('crmContTitulo').textContent = `${N(r.enIndice)} rivales probables${corp === 'jal' ? ' en su localidad' : ''}.`;
    const esc = L.escalera;
    const nombres = top.map(x => NOMBRE_BONITO(K.corto(x.nombre)));
    $('crmContCopy').textContent = `Los de más presión: ${nombres.length > 1 ? `${nombres.slice(0, -1).join(', ')} y ${nombres[nombres.length - 1]}` : nombres[0]}. En el plano, su familia política contra cuánto rinde cada uno en los puestos donde usted saca votos.`
      + (L.avisos.includes('territorio-parejo') ? ' En su territorio todos compiten por los mismos puestos: lo que los separa es la lista y la familia.' : '')
      + (esc?.usted && !esc.usted.elegido && esc.distancia != null ? ` En su lista de 2023 quedó ${esc.usted.puesto}.º, a ${N(esc.distancia)} votos del último elegido.` : '');
    $('crmContPlano').innerHTML = K.planoSVG(L, { ancho: 520, alto: 300, etiquetas: 3, vitrina: CRM_VITRINA });
    $('crmContDato').textContent = N(r.enIndice);
    $('crmContSub').textContent = `presión alta ${N(r.niveles.alta)} · media ${N(r.niveles.media)} · baja ${N(r.niveles.baja)}`;
    /* La revisión mensual de prensa del territorio (fase 5). En vitrina no se
       pide: es parte de lo que se cobra, y sin acceso el worker no la da. */
    const t = K.terrKey(L.corp || corp, alcance);
    if (!CRM_VITRINA && t) {
      const rv = await apiC360(`/c360/contendientes?t=${encodeURIComponent(t)}`).catch(() => null);
      if (turno !== CONT_TURNO) return;
      const info = K.integrarRevision(L, rv && rv.ok ? rv.data.version : null);
      $('crmContRevision').textContent = info.revisado
        ? `Revisado el ${K.fechaLarga(info.revisado)} · próxima revisión: ${K.fechaLarga(info.proxima)}. ${info.linea}`
        : `Revisión mensual de prensa: la primera es el ${K.fechaLarga(info.proxima)}.`;
    }
  } catch (e) {
    if (turno !== CONT_TURNO) return;
    /* Una falla de red no es «no hay registro»: se dice distinto. */
    if (/No se pudieron leer/.test(e?.message || '')) { $('crmContTitulo').textContent = 'No pudimos leer el registro de su territorio.'; $('crmContCopy').textContent = 'Vuelva a cargar la página en un momento.'; $('crmContDato').textContent = '—'; $('crmContSub').textContent = 'sin conexión con los datos'; return; }
    $('crmContTitulo').textContent = 'Todavía no hay rivales que mostrar.';
    $('crmContCopy').textContent = 'Sin resultados de 2023 en la corporación y el territorio a los que se lanza no hay registro del cual sacar rivales probables. Cuando se inscriban las candidaturas de 2027, aparecen.';
    $('crmContDato').textContent = '—'; $('crmContSub').textContent = 'sin registro comparable';
  }
}
/* ─── 10. Arranque ───────────────────────────────────────────────────────── */
(function init() {
  montarWizardNuevo();
  toggleParty();
  montarPais();
  loadParties();
  cargarDepartamentos();
  rotateStrategyMessage();
  const strategyMessageTimer = setInterval(rotateStrategyMessage, 950);
  prepareHistoricalIndex();
  cargarSesion().then(() => {
    /* Con vínculo la portada sigue siendo la entrada, pero el preload se
       cierra al conocer la sesión; con la cuenta lista se abre directo. */
    clearInterval(strategyMessageTimer);
    $('preload').classList.remove('active');
    /* «Abrir mi candidatura» desde un panel (escucha, electorado) llega con
       ?abrir=1. Con vínculo se abre el CRM directo; SIN vínculo la respuesta
       no es la portada —desde la que el botón parece no haber hecho nada— sino
       la búsqueda, que es donde una candidatura se abre de verdad. */
    if (new URLSearchParams(location.search).get('abrir') === '1') {
      /* En modo pruebas manda la candidatura que se estaba mirando en esta
         pestaña, no el vínculo real de la cuenta de administración. */
      const local = PRUEBAS && leerVinculoLocal();
      if (local) SESSION.vinculo = local;
      if (SESSION.vinculo) abrirVinculo(); else beginHistorical();
    }
  });
  setTimeout(() => { clearInterval(strategyMessageTimer); $('preload').classList.remove('active'); }, 6000);   /* red de seguridad si el worker no responde */
})();
