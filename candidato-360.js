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
    10. Arranque

   Reglas del producto que viven acá (decisión de Ricardo, sep-2026):
   · La búsqueda y el wizard se ven, pero BORROSOS, hasta que la cuenta tenga
     acceso (plan c360, cortesía o admin). El dato es la vitrina.
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
async function localidadesDe(depNombre, munNombre) {
  const rows = await comunasCSV();
  const dep = canonical(depNombre), mun = canonical(munNombre);
  return [...new Set(rows.filter(r => canonical(r[5]) === dep && canonical(r[6]) === mun).map(r => nombreLocalidad(r[10])).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'es'));
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
}
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
function abrirPaywall(motivo) {
  const modal = $('c360Paywall'); if (!modal) return;
  const next = encodeURIComponent(`${PAGINA}?comprar=1`);
  const configurado = Boolean(SESSION.planes?.configurado && SESSION.planes?.links?.mensual);
  const mailto = `mailto:${SESSION.soporte}?subject=${encodeURIComponent('Acceso a Candidato 360')}&body=${encodeURIComponent(`Hola Ricardo, quiero activar Candidato 360${SESSION.user?.email ? ` para la cuenta ${SESSION.user.email}` : ''}.`)}`;
  $('c360PaywallMotivo').textContent = motivo || 'Para abrir su candidatura necesita una cuenta con acceso a Candidato 360.';
  $('c360PaywallPrecio').textContent = textoPrecio();
  let botones = '';
  if (!SESSION.token) botones = `<a class="wall-btn primary" href="register.html?next=${next}">Crear cuenta</a><a class="wall-btn" href="login.html?next=${next}">Ya tengo cuenta</a>`;
  else if (configurado) botones = `<button type="button" class="wall-btn primary" onclick="iniciarPago()">Activar por ${escHtml(textoPrecio())}</button><a class="wall-btn" href="${mailto}">Escribir a soporte</a>`;
  else botones = `<a class="wall-btn primary" href="${mailto}">Solicitar acceso por correo</a>`;
  $('c360PaywallBotones').innerHTML = botones;
  modal.classList.add('open');
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
async function guardarCampana(campana) {
  if (!SESSION.vinculo) return;
  try { const r = await apiC360('/c360/campana', { method: 'POST', body: JSON.stringify({ campana }) }); if (r.ok) SESSION.vinculo = r.data.vinculo; } catch {}
}

/* Aplica el estado de acceso a las dos rutas y a la portada. */
function aplicarGate() {
  const intro = $('introVinculo');
  if (intro) {
    if (SESSION.vinculo) { intro.innerHTML = `Su cuenta está vinculada a <b>${escHtml(vinculoDescripcion())}</b>. Cualquiera de las dos rutas abre esa candidatura; para cambiarla escriba a <a href="mailto:${escHtml(SESSION.soporte)}">${escHtml(SESSION.soporte)}</a>.`; intro.classList.remove('hidden'); }
    else intro.classList.add('hidden');
  }
  aplicarGateExistente();
  aplicarGateNuevo();
  if (new URLSearchParams(location.search).get('comprar') === '1' && SESSION.listo && !SESSION.acceso) { history.replaceState(null, '', PAGINA); abrirPaywall(SESSION.token ? 'Su cuenta ya existe. Falta activar el acceso a Candidato 360.' : ''); }
}
function muro(contenedor, texto) {
  if (!contenedor) return;
  let wall = contenedor.querySelector(':scope > .c360-wall');
  if (!wall) { wall = document.createElement('div'); wall.className = 'c360-wall'; contenedor.append(wall); }
  wall.innerHTML = `<div class="c360-wall-card"><span class="kicker">Candidato 360 · acceso</span><p>${texto}</p><button type="button" onclick="abrirPaywall()">Activar mi candidatura</button></div>`;
}
function quitarMuro(contenedor) { contenedor?.querySelector(':scope > .c360-wall')?.remove(); }
function aplicarGateExistente() {
  const box = document.querySelector('#existing .search-box'); if (!box) return;
  const bloqueado = SESSION.listo && !SESSION.acceso;
  box.classList.toggle('locked', bloqueado);
  if (bloqueado) muro(box, 'Busque su nombre: verá que su historial está aquí. Para abrirlo y construir el CRM, active su acceso. Cada cuenta se vincula a <b>un solo candidato</b>.');
  else quitarMuro(box);
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
  loadParties();
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
/* Los partidos salen del índice que ya está en memoria: son las mismas cinco
   fuentes territoriales de 2023 que CandRegistry descarga de todos modos. */
const PARTY_SOURCES = new Set(['asamblea', 'gob2023', 'alc2023', 'concejo', 'jal']);
function loadParties() {
  const party = $('party'), partyStatus = $('partyStatus'); if (!party) return;
  const parties = [...new Set(historicalIndex.filter(c => PARTY_SOURCES.has(c.source)).map(c => c.partido).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'es'));
  if (!parties.length) { party.innerHTML = '<option value="">Cargando la base de partidos…</option>'; partyStatus.textContent = 'Se completa mientras llega el índice electoral.'; return; }
  const elegido = party.value;
  party.innerHTML = optionList(parties, 'Seleccione de la base');
  if (elegido) party.value = elegido;
  partyStatus.textContent = `${parties.length} partidos, movimientos, coaliciones y listas encontrados en los índices territoriales.${historicalLocalDone ? '' : ' Siguen llegando.'}`;
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
   una tarjeta por elección. El historial conserva todas sus candidaturas. */
function fourNameKey(candidate) {
  const key = CandRegistry.personaKey(candidate?.nombre);
  const isRobertoOrtizCali = key === 'ROBERTO ORTIZ URUENA' && normalizedText(candidate?.circunscripcion).includes('CALI');
  return isRobertoOrtizCali ? `CALI-${key}` : key.split(/\s+/).filter(Boolean).length === 4 ? key : '';
}
function candidateProfile(candidate) {
  const key = fourNameKey(candidate); if (!key) return { ...candidate, id: candidate.slug };
  const seen = new Set;
  const history = historicalIndex.filter(item => fourNameKey(item) === key).filter(item => { const itemKey = item.slug || `${item.nombre}|${item.corp}|${item.partido}`; if (seen.has(itemKey)) return false; seen.add(itemKey); return true; }).sort((a, b) => candidateYear(b) - candidateYear(a));
  if (history.length < 2) return { ...candidate, id: candidate.slug };
  const years = [...new Set(history.map(candidateYear).filter(Boolean))].sort((a, b) => a - b);
  return { ...history[0], id: `persona-${key.toLowerCase().replace(/\s+/g, '-')}`, nombre: history[0].nombre, history, historyVotes: history.reduce((sum, item) => sum + Number(item.votos || 0), 0), historyLabel: `${history.length} candidaturas registradas · ${years.join(', ')}` };
}
function beginHistorical() {
  /* Con vínculo no se busca: la cuenta ya tiene candidato. */
  if (SESSION.vinculo) return abrirVinculo();
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
  $('searchResults').insertAdjacentHTML('beforeend', profiles.map(c => `<div class="result" role="button" tabindex="0" data-profile="${escHtml(c.id)}" onclick="openHistoricCandidate(this.dataset.profile)" onkeydown="if(event.key==='Enter')openHistoricCandidate(this.dataset.profile)"><div class="result-main"><span class="avatar">${escHtml(initials(c.nombre))}</span><span><b>${escHtml(c.nombre)}</b><small>${escHtml(c.historyLabel || `${c.corp || 'Historial electoral'} · ${c.partido || 'Sin partido registrado'}`)}${c.votos ? ` · ${Number(c.votos).toLocaleString('es-CO')} votos` : ''}</small></span></div><span class="tag">${SESSION.acceso ? 'Continuar' : 'Activar'}</span></div>`).join(''));
  if (note) note.textContent = historicalLocalDone ? `${historicalIndex.length.toLocaleString('es-CO')} candidaturas disponibles.` : 'Resultados parciales: seguimos incorporando concejos y JAL.';
  if (rank.total > items.length) $('searchResults').insertAdjacentHTML('beforeend', `<p class="search-note search-more">${items.length} de ${rank.total.toLocaleString('es-CO')} coincidencias · agregue un apellido para afinar.</p>`);
}
function openHistoricCandidate(id) {
  if (!SESSION.acceso) return abrirPaywall();
  const profile = candidateProfiles.get(id) || historicalIndex.find(c => c.slug === id);
  if (!profile) return;
  if (SESSION.vinculo && !vinculoCoincide(profile)) { alert(`Su cuenta ya está vinculada a ${vinculoDescripcion()}. Para cambiar de candidato escriba a ${SESSION.soporte}.`); return abrirVinculo(); }
  abrirRutaCandidato(profile);
}
function abrirRutaCandidato(profile) {
  crmCandidate = profile;
  $('routeInitials').textContent = initials(profile.nombre); $('routeName').textContent = profile.nombre;
  $('routeHistory').textContent = profile.historyLabel ? `Historial: ${profile.historyLabel}` : `Historial: ${profile.corp || 'candidatura registrada'}${profile.partido ? ` · ${profile.partido}` : ''}`;
  const sameCorp = corporacionHistorica(profile);
  /* "La misma corporación" solo aplica si la última fue territorial: un Senado
     o una consulta no tienen "misma corporación" en las locales de 2027. */
  const sameOpt = document.querySelector('.route-option[data-route="same"]');
  sameOpt.classList.toggle('hidden', !sameCorp);
  $('sameCorporationLabel').textContent = sameCorp ? CRM_CORPORATIONS[sameCorp] : 'No aplica';
  campaignDeptOptions();
  document.querySelector(`input[name="corporationRoute"][value="${sameCorp ? 'same' : 'other'}"]`).checked = true;
  toggleCorporationChoice();
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
  ['concejo', 'Concejo Municipal', 'Representación local.'],
  ['alcaldia', 'Alcaldía Municipal', 'Gestión de la ciudad.'],
  ['asamblea', 'Asamblea Departamental', 'Control y visión regional.'],
  ['gobernacion', 'Gobernación', 'Liderazgo para todo el territorio.']
];
function corporationCards(selected, onSelect) {
  const grid = document.createElement('div'); grid.className = 'corporation-card-grid';
  CORPORATION_CARDS.forEach(([key, title, description]) => {
    const card = document.createElement('button'); card.type = 'button'; card.className = `corporation-card${selected === key ? ' is-selected' : ''}`; card.dataset.corporation = key;
    card.innerHTML = `<b>${title}</b><small>${description}</small>`;
    card.addEventListener('click', () => { onSelect(key); grid.querySelectorAll('.corporation-card').forEach(item => item.classList.toggle('is-selected', item === card)); });
    grid.append(card);
  });
  return grid;
}
function createCorporationPicker(label, selected, onSelect) { const picker = document.createElement('div'); picker.className = 'corporation-picker'; picker.innerHTML = `<label>${label}</label>`; picker.append(corporationCards(selected, onSelect)); return picker; }
function marcarCard(picker, key) { picker?.querySelectorAll('.corporation-card').forEach(c => c.classList.toggle('is-selected', c.dataset.corporation === key)); }
const historicCorporationPicker = createCorporationPicker('Nueva corporación', '', key => { $('otherCorporation').value = key; updateCampaignTerritory(); });
historicCorporationPicker.id = 'historicCorporationPicker'; historicCorporationPicker.classList.add('hidden');
$('otherCorporationField').after(historicCorporationPicker);
function toggleCorporationChoice() {
  const isOther = document.querySelector('input[name="corporationRoute"]:checked')?.value === 'other';
  $('otherCorporation').disabled = !isOther;
  historicCorporationPicker.classList.toggle('hidden', !isOther);
  $('campaignPlace').classList.toggle('hidden', !isOther);
  if (isOther) updateCampaignTerritory();
}
function updateCampaignTerritory() {
  const corp = $('otherCorporation').value, municipal = CORP_MUNICIPAL.includes(corp), jal = corp === 'jal';
  $('campaignMunicipalityField').classList.toggle('hidden', !municipal); $('campaignLocalityField').classList.toggle('hidden', !jal);
  $('campaignDepartment').required = municipal || CORP_DEPARTAMENTAL.includes(corp); $('campaignMunicipality').required = municipal; $('campaignLocality').required = jal;
  if ($('campaignDepartment').value && municipal) loadCampaignMunicipalities();
}
async function cargarMunicipios(select, dep, cacheKey) {
  select.innerHTML = '<option value="">Cargando municipios…</option>';
  try {
    const data = await fetchJSON(`${S3}/mapas-2026/Departamentos-mps/${dep}.json`);
    municipalitiesByDepartment[cacheKey] = data;
    const municipalities = [...new Set(data.features.map(f => f.properties.mpio_cnmbr).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'es'));
    select.innerHTML = optionList(municipalities, 'Seleccione municipio o distrito');
  } catch (e) { select.innerHTML = '<option value="">No se pudieron cargar los municipios</option>'; }
}
let municipalitiesByDepartment = {};
async function loadCampaignMunicipalities() {
  const dep = $('campaignDepartment').value; if (!dep) return;
  $('campaignLocality').innerHTML = '<option value="">Primero seleccione municipio</option>';
  await cargarMunicipios($('campaignMunicipality'), dep, `crm-${dep}`);
}
async function cargarLocalidades(select, status, depNombre, munNombre) {
  select.innerHTML = '<option value="">Cargando comunas o localidades…</option>'; status.textContent = '';
  try {
    const localities = await localidadesDe(depNombre, munNombre);
    select.innerHTML = optionList(localities, 'Seleccione comuna o localidad');
    status.textContent = localities.length ? `${localities.length} comunas o localidades disponibles.` : 'No hay una división local disponible para este municipio en la fuente actual.';
  } catch (e) { select.innerHTML = '<option value="">No se pudieron cargar las comunas o localidades</option>'; status.textContent = 'La fuente territorial no está disponible en este momento.'; }
}
async function loadCampaignLocalities() {
  if ($('otherCorporation').value !== 'jal' || !$('campaignMunicipality').value) return;
  await cargarLocalidades($('campaignLocality'), $('campaignLocalityStatus'), $('campaignDepartment').options[$('campaignDepartment').selectedIndex].text, $('campaignMunicipality').value);
}
function campaignTerritory(corp) {
  if (document.querySelector('input[name="corporationRoute"]:checked').value !== 'other') return '';
  const dep = $('campaignDepartment').options[$('campaignDepartment').selectedIndex]?.text || '', mun = $('campaignMunicipality').value, local = $('campaignLocality').value;
  if (!$('campaignDepartment').value || (CORP_MUNICIPAL.includes(corp) && !mun) || (corp === 'jal' && !local)) return null;
  const seen = new Set;
  return [local, mun, dep].filter(Boolean).filter(place => { const key = normalizedText(place); if (seen.has(key)) return false; seen.add(key); return true; }).join(' · ');
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
  return { corp: corpKey, ruta: isOther ? 'other' : 'same', departamento: isOther ? $('campaignDepartment').value : '', departamentoNombre: isOther ? ($('campaignDepartment').options[$('campaignDepartment').selectedIndex]?.text || '') : '', municipio: isOther ? $('campaignMunicipality').value : '', localidad: isOther ? $('campaignLocality').value : '' };
}
/* Rellena la ruta con la campaña guardada (al volver con vínculo). */
async function precargarCampana(campana) {
  if (!campana) return;
  const isOther = campana.ruta === 'other' || !corporacionHistorica(crmCandidate);
  document.querySelector(`input[name="corporationRoute"][value="${isOther ? 'other' : 'same'}"]`).checked = true;
  toggleCorporationChoice();
  if (!isOther) return;
  $('otherCorporation').value = campana.corp; marcarCard(historicCorporationPicker, campana.corp); updateCampaignTerritory();
  if (campana.departamento) {
    $('campaignDepartment').value = campana.departamento;
    if (CORP_MUNICIPAL.includes(campana.corp)) { await loadCampaignMunicipalities(); $('campaignMunicipality').value = campana.municipio || ''; }
    if (campana.corp === 'jal' && campana.municipio) { await loadCampaignLocalities(); $('campaignLocality').value = campana.localidad || ''; }
  }
}

/* ─── 7. Candidatura nueva: wizard ───────────────────────────────────────── */
async function cargarDepartamentos() {
  try {
    const data = await fetchJSON(`${S3}/mapas-2026/DEPARTAMENTOS2.json`);
    const names = data.features.map(f => f.properties.name).filter(n => DEP_CODES[n]).sort((a, b) => a.localeCompare(b, 'es'));
    $('department').innerHTML = '<option value="">Seleccione un departamento</option>' + names.map(n => `<option value="${DEP_CODES[n]}">${n === 'Distrito Capital de Bogotá' ? 'Bogotá D.C.' : n}</option>`).join('');
    campaignDeptOptions();
  } catch (e) { $('department').innerHTML = '<option value="">No se pudieron cargar los departamentos</option>'; }
}
async function loadMunicipalities() { const dep = $('department').value; if (!dep) return; await cargarMunicipios($('municipality'), dep, dep); }
async function loadLocalities() { await cargarLocalidades($('locality'), $('localityStatus'), $('department').options[$('department').selectedIndex].text, $('municipality').value); }
function updateTerritory() {
  const election = $('election').value, municipal = MUNICIPAL_ELECTIONS.includes(election);
  $('municipalityField').classList.toggle('hidden', !municipal); $('localityField').classList.toggle('hidden', election !== 'jal');
  $('municipality').required = municipal; $('locality').required = election === 'jal';
  if (municipal && $('department').value) loadMunicipalities(); else $('municipality').innerHTML = '<option value="">Primero seleccione departamento</option>';
  if (election !== 'jal') $('locality').innerHTML = '<option value="">Primero seleccione municipio</option>';
}
function updateLocality() { if ($('election').value === 'jal' && $('municipality').value) loadLocalities(); }
function togglePublicName() { $('publicNameField').classList.toggle('hidden', !$('publicFigure').checked); $('publicName').required = $('publicFigure').checked; }
function toggleParty() { const isNew = $('partyMode').value === 'new'; $('partyExisting').classList.toggle('hidden', isNew); $('partyNew').classList.toggle('hidden', !isNew); $('party').required = !isNew; $('partyName').required = isNew; }
/* Una pregunta a la vez. Los campos se MUEVEN, no se recrean, para conservar
   validaciones y datos ya cargados. */
const NEW_STEPS_TOTAL = 6;
function montarWizardNuevo() {
  const form = document.querySelector('#new form'); if (!form) return;
  const findField = id => $(id)?.closest('.field');
  const fields = { name: findField('newName'), pub: findField('publicFigure'), pubName: $('publicNameField'), election: findField('election'), department: findField('department'), municipality: findField('municipality'), locality: findField('locality'), partyMode: findField('partyMode'), partyExisting: $('partyExisting'), partyNew: $('partyNew'), goal: findField('goal') };
  const formGrid = form.querySelector('.form-grid'), originalSubmit = form.querySelector('[type="submit"]');
  const wizard = document.createElement('div'); wizard.className = 'new-wizard'; formGrid.before(wizard);
  Object.values(fields).forEach(f => f?.remove()); formGrid.remove(); originalSubmit.remove();
  const steps = [
    { title: '¿Cómo aparecerá en campaña?', copy: 'Empecemos por su nombre completo.', fields: [fields.name] },
    { title: '¿Su identidad es pública?', copy: 'Podemos preparar señales abiertas bajo su nombre, apodo o trayectoria.', fields: [fields.pub, fields.pubName] },
    { title: '¿A qué corporación aspira?', copy: 'La corporación define el territorio y la lectura electoral que activaremos.', fields: [fields.election], cards: true },
    { title: '¿Dónde será la candidatura?', copy: 'Ubique el territorio en el que va a competir.', fields: [fields.department, fields.municipality, fields.locality] },
    { title: '¿Con qué partido o movimiento?', copy: 'Puede vincular una organización existente o preparar una nueva.', fields: [fields.partyMode, fields.partyExisting, fields.partyNew] },
    { title: '¿Cuál es el primer objetivo?', copy: 'Con esto cerraremos su punto de partida.', fields: [fields.goal], final: true }
  ];
  const electionSelect = fields.election.querySelector('#election'); fields.election.id = 'electionField'; electionSelect.value = '';
  fields.municipality.classList.add('hidden'); fields.locality.classList.add('hidden');
  steps.forEach((def, index) => {
    const step = document.createElement('section'); step.className = `new-wizard-step${index === 0 ? ' active' : ''}`; step.dataset.step = index;
    step.innerHTML = `<div class="wizard-progress">${steps.map((_, p) => `<i class="${p <= index ? 'active' : ''}"></i>`).join('')}</div><h3>${def.title}</h3><p>${def.copy}</p>`;
    def.fields.forEach(f => f && step.append(f));
    if (def.cards) { const picker = createCorporationPicker('Seleccione una corporación', '', key => { electionSelect.value = key; updateTerritory(); }); picker.id = 'newCorporationPicker'; step.append(picker); }
    const actions = document.createElement('div'); actions.className = 'wizard-actions';
    if (index) { const back = document.createElement('button'); back.type = 'button'; back.className = 'wizard-back'; back.textContent = '← Anterior'; back.addEventListener('click', () => showNewWizardStep(index - 1)); actions.append(back); }
    const next = document.createElement('button'); next.type = def.final ? 'submit' : 'button'; next.className = 'next wizard-next'; next.textContent = def.final ? 'Crear punto de partida →' : 'Siguiente →';
    if (!def.final) next.addEventListener('click', () => advanceNewWizard(index));
    actions.append(next); step.append(actions); wizard.append(step);
  });
  function showNewWizardStep(index) {
    wizard.querySelectorAll('.new-wizard-step').forEach((s, p) => s.classList.toggle('active', p === index));
    const stepLabel = document.querySelector('#new .flow-top .step'); if (stepLabel) stepLabel.textContent = `Paso ${index + 1} de ${NEW_STEPS_TOTAL} · Candidatura nueva`;
  }
  function advanceNewWizard(index) {
    if (index === 2 && !electionSelect.value) { $('newCorporationPicker').classList.add('shake'); setTimeout(() => $('newCorporationPicker').classList.remove('shake'), 500); return; }
    const required = steps[index].fields.flatMap(f => f ? [...f.querySelectorAll('input,select')] : []).filter(input => input.required && !input.closest('.hidden'));
    const invalid = required.find(input => !input.checkValidity()); if (invalid) { invalid.reportValidity(); return; }
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
  const nuevo = { nombre: $('newName').value.trim(), publico: $('publicFigure').checked, nombrePublico: $('publicName').value.trim(), partido: $('partyMode').value === 'new' ? $('partyName').value.trim() : $('party').value, partidoNuevo: $('partyMode').value === 'new', objetivo: $('goal').value };
  const campana = { corp: $('election').value, ruta: 'other', departamento: dep.value, departamentoNombre: depNombre, municipio: MUNICIPAL_ELECTIONS.includes($('election').value) ? $('municipality').value : '', localidad: $('election').value === 'jal' ? $('locality').value : '' };
  if (!nuevo.nombre || !campana.corp || !campana.departamento) return;
  if (!SESSION.vinculo) {
    const sigue = await confirmarVinculo(nuevo.nombre, `${CRM_CORPORATIONS[campana.corp]} · ${[campana.localidad, campana.municipio, depNombre].filter(Boolean).join(' · ')}`);
    if (!sigue) return;
    const r = await guardarVinculo({ tipo: 'nuevo', nuevo, campana });
    if (!r.ok) { if (r.existente) { alert(`Su cuenta ya está vinculada a ${vinculoDescripcion()}. Para cambiarla escriba a ${SESSION.soporte}.`); return abrirVinculo(); } if (r.sinAcceso) return abrirPaywall(); alert(`No se pudo guardar la candidatura: ${r.error}`); return; }
  }
  NUEVO = { ...nuevo, campana };
  abrirCRMNuevo();
}

/* ─── 8. CRM: apertura, meta de votos y foto ─────────────────────────────── */
async function estimateVoteTarget(corp, territory) { return VoteTarget.estimate({ corp, territory: territory || crmCandidate?.circunscripcion || '', baseUrl: S3 }); }
function pintarMeta(estimate) {
  if (estimate.target) { $('crmVoteNumber').textContent = estimate.target.toLocaleString('es-CO'); $('crmVoteTarget').textContent = `Meta inicial: ${estimate.target.toLocaleString('es-CO')} votos`; }
  else { $('crmVoteNumber').textContent = '—'; $('crmVoteTarget').textContent = 'Meta pendiente de referencia territorial'; }
  $('crmVoteFormula').textContent = estimate.formula;
}
function vinculoCoincide(profile) {
  const v = SESSION.vinculo; if (!v || v.tipo !== 'historial') return false;
  const slugs = new Set(v.candidato?.slugs || []);
  const propios = (profile.history?.length ? profile.history : [profile]).map(c => c.slug).filter(Boolean);
  return propios.some(s => slugs.has(s)) || (v.candidato?.id && v.candidato.id === profile.id);
}
async function launchCRM(event) {
  event?.preventDefault();
  if (!crmCandidate) return;
  if (!SESSION.acceso) return abrirPaywall();
  const isOther = document.querySelector('input[name="corporationRoute"]:checked').value === 'other';
  if (isOther && !$('otherCorporation').value) { historicCorporationPicker.scrollIntoView({ behavior: 'smooth', block: 'center' }); return; }
  const corpKey = isOther ? $('otherCorporation').value : corporacionHistorica(crmCandidate) || 'concejo';
  const corporation = CRM_CORPORATIONS[corpKey], territory = campaignTerritory(corpKey);
  if (territory === null) { $('campaignPlace').scrollIntoView({ behavior: 'smooth', block: 'center' }); $('campaignDepartment').focus({ preventScroll: true }); return; }
  const campana = campanaActual(corpKey);
  if (!SESSION.vinculo) {
    const sigue = await confirmarVinculo(crmCandidate.nombre, `${corporation}${territory ? ` · ${territory}` : ''}`);
    if (!sigue) return;
    const slugs = (crmCandidate.history?.length ? crmCandidate.history : [crmCandidate]).map(c => c.slug).filter(Boolean);
    const r = await guardarVinculo({ tipo: 'historial', candidato: { id: crmCandidate.id, nombre: crmCandidate.nombre, slugs, corp: crmCandidate.corp, partido: crmCandidate.partido, circunscripcion: crmCandidate.circunscripcion }, campana });
    if (!r.ok) { if (r.existente) { alert(`Su cuenta ya está vinculada a ${vinculoDescripcion()}. Para cambiarla escriba a ${SESSION.soporte}.`); return abrirVinculo(); } if (r.sinAcceso) return abrirPaywall(); alert(`No se pudo guardar el vínculo: ${r.error}`); return; }
  } else guardarCampana(campana);

  $('crmBack').textContent = '← Cambiar corporación'; $('crmBack').onclick = () => showScreen('candidateRoute');
  $('crmInitials').textContent = initials(crmCandidate.nombre); $('crmName').textContent = crmCandidate.nombre;
  $('crmTarget').textContent = `Candidatura 2027 · ${corporation}${territory ? ` · ${territory}` : ''}`;
  $('crmContext').textContent = crmCandidate.history?.length
    ? `Integramos ${crmCandidate.history.length} candidaturas de la misma persona (${[...new Set(crmCandidate.history.map(candidateYear).filter(Boolean))].sort((a, b) => a - b).join(', ')}). El CRM conserva todo su historial; el mapa toma la elección más reciente como referencia territorial para no mezclar votaciones de años diferentes.`
    : `Partimos de ${crmCandidate.corp || 'su historial electoral'}${crmCandidate.partido ? ` y ${crmCandidate.partido}` : ''}. El mapa conserva la votación histórica; la nueva campaña queda ubicada en ${territory || 'su territorio electoral anterior'}.`;
  $('crmVoteNumber').textContent = '…'; $('crmVoteTarget').textContent = 'Calculando objetivo competitivo'; $('crmVoteFormula').textContent = 'Contrastando la corporación y el territorio con la última elección comparable.';
  $('crmMapPanelNum').textContent = '01 · Mapa de historial electoral';
  showScreen('crm');
  loadHistoricalMap(crmCandidate);
  renderCRMProfilePhoto(crmCandidate);
  pintarMeta(await estimateVoteTarget(corpKey, territory));
}
/* CRM de una candidatura nueva: sin historial, el punto de partida es el
   territorio al que aspira y la referencia de 2023 de ese territorio. */
async function abrirCRMNuevo() {
  const n = NUEVO; if (!n) return;
  crmCandidate = null;
  const c = n.campana, lugar = [c.localidad, c.municipio, c.departamentoNombre].filter(Boolean).join(' · ');
  $('crmBack').textContent = '← Inicio'; $('crmBack').onclick = () => showScreen('intro');
  $('crmInitials').textContent = initials(n.nombre); $('crmName').textContent = n.nombre;
  $('crmTarget').textContent = `Candidatura 2027 · ${CRM_CORPORATIONS[c.corp]} · ${lugar}`;
  $('crmContext').textContent = `Candidatura nueva${n.partido ? ` con ${n.partido}${n.partidoNuevo ? ' (movimiento por constituir)' : ''}` : ''}. Sin historial propio, el punto de partida es el territorio: la referencia son los resultados de 2023 en ${lugar}.${n.objetivo ? ` Primer objetivo: ${n.objetivo.toLowerCase()}.` : ''}`;
  $('crmVoteNumber').textContent = '…'; $('crmVoteTarget').textContent = 'Calculando objetivo competitivo'; $('crmVoteFormula').textContent = 'Contrastando la corporación y el territorio con la última elección comparable.';
  $('crmMapPanelNum').textContent = '01 · Territorio de campaña';
  document.getElementById('crmProfilePhoto')?.remove(); document.getElementById('crmProfilePhotoMissing')?.remove(); $('crmInitials').classList.remove('crm-avatar-hidden');
  showScreen('crm');
  renderTerritorioObjetivo(c);
  pintarMeta(await VoteTarget.estimate({ corp: c.corp, territory: lugar, baseUrl: S3 }));
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
  if (!fotosPresPromise) fotosPresPromise = fetch(PRES_INDEX_URL).then(r => r.ok ? r.json() : Promise.reject()).then(d => (d.personas || []).filter(p => p.foto).map(p => ({ clave: CandRegistry.personaKey(p.nombre), foto: p.foto }))).catch(() => []);
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

/* ─── 9. Mapas ───────────────────────────────────────────────────────────── */
let crmLeafletMap = null, crmMapLayer = null, crmBarrioLayer = null, crmTileLayer = null;
let crmMapMode = 'total', crmMapState = null;
const MAP_COLOR = ratio => ratio <= 0 ? '#d8dfd7' : ratio < .12 ? '#b7d9bf' : ratio < .35 ? '#79b987' : ratio < .65 ? '#3e8a5b' : '#174f35';
function crearMapa(center, zoom) {
  const mapEl = $('crmMap');
  if (!crmLeafletMap) { mapEl.innerHTML = ''; crmLeafletMap = L.map(mapEl, { zoomControl: false, attributionControl: true, scrollWheelZoom: false, dragging: false, touchZoom: false, doubleClickZoom: false, boxZoom: false, keyboard: false, tap: false }).setView(center, zoom); }
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
  if (rotado) { if (crmTileLayer) { crmLeafletMap.removeLayer(crmTileLayer); crmTileLayer = null; } return; }
  if (crmTileLayer) return;
  crmTileLayer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, opacity: .72, attribution: '&copy; OpenStreetMap contributors' }).addTo(crmLeafletMap);
}
function encuadrar(layer, padding = 24) { const bounds = layer?.getBounds(); if (bounds?.isValid()) crmLeafletMap.fitBounds(bounds, { padding: [padding, padding], animate: false }); setTimeout(() => crmLeafletMap?.invalidateSize(), 120); }
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
function claveLocal(mesa) { const com = String(mesa.com || '').replace(/^0+/, ''), zon = String(mesa.zon || '').replace(/^0+/, ''); return (com || zon || '').padStart(2, '0'); }
function completaNombres(geoData, code, name, namesByArea) { (geoData?.features || []).forEach(f => { const k = code(f.properties); if (k && !namesByArea[k]) namesByArea[k] = name(f.properties); }); return namesByArea; }
function electoralPlaceCode(mesa) { return `${String(mesa.dep || '').padStart(2, '0')}${String(mesa.mun || '').padStart(3, '0')}${String(mesa.zon || '').padStart(2, '0')}${String(mesa.pue || '').padStart(2, '0')}`; }
let puestosBarrioPromise = null;
async function puestosPorBarrio() {
  if (!puestosBarrioPromise) puestosBarrioPromise = fetch(`${S3}/mapas-2026/PUESTOS_GEOREF.csv`).then(r => r.ok ? r.text() : Promise.reject()).then(raw => { const lookup = {}; raw.split(/\r?\n/).slice(1).forEach(line => { const row = line.split(';'), code = row[1], barrio = row[7]; if (code && barrio) lookup[code] = { barrio, lat: Number(row[9]), lng: Number(row[10]) }; }); return lookup; });
  return puestosBarrioPromise;
}
/* Reparte una meta en proporción a lo observado sin perder un voto por redondeo. */
function distributeVotes(source, target) {
  const total = Object.values(source).reduce((sum, v) => sum + Number(v || 0), 0);
  if (!total || !target) return source;
  const rows = Object.entries(source).map(([key, value]) => { const raw = Number(value) * target / total; return { key, value: Math.floor(raw), rest: raw - Math.floor(raw) }; });
  let pending = target - rows.reduce((sum, row) => sum + row.value, 0);
  rows.sort((a, b) => b.rest - a.rest).slice(0, pending).forEach(row => row.value++);
  return Object.fromEntries(rows.map(row => [row.key, row.value]));
}
function projectedVotesByArea() { const goal = Number(String($('crmVoteNumber').textContent || '').replace(/\D/g, '')); return distributeVotes(crmMapState?.votesByArea || {}, goal); }
function renderMapBreakdown(votesByArea, namesByArea, title) {
  const rows = Object.entries(votesByArea).map(([key, value]) => ({ key, name: namesByArea[key] || key, value: Number(value) || 0 })).filter(row => row.value > 0).sort((a, b) => b.value - a.value), max = Math.max(1, ...rows.map(row => row.value));
  $('crmBreakdown').innerHTML = `<h4 id="crmBreakdownTitle">${title}</h4>` + (rows.length ? rows.map(row => `<button class="crm-breakdown-item" type="button" data-area-key="${escHtml(row.key)}" onclick="openMapAreaFromBreakdown(this.dataset.areaKey)"><span class="crm-breakdown-row"><b>${escHtml(row.name)}</b><span>${row.value.toLocaleString('es-CO')}</span></span><span class="crm-breakdown-bar"><i style="width:${Math.max(3, Math.round(row.value / max * 100))}%"></i></span></button>`).join('') : '<p class="helper">No hay votos desagregados disponibles.</p>');
}
/* TOTAL / PROYECTADO: solo cuando la candidatura tiene UNA elección; con varias
   mandan los toggles por año (que también traen PROYECTADO). */
function ensureCRMMapToggles() {
  if (electionViewRecords.length >= 2) return;
  const head = $('crmMapTitle').closest('.panel-head'); if (!head || $('crmMapToggles')) return;
  head.insertAdjacentHTML('beforeend', '<div class="map-toggles" id="crmMapToggles"><button class="map-toggle active" type="button" data-mode="total">TOTAL</button><button class="map-toggle" type="button" data-mode="proyectado">PROYECTADO</button></div>');
  $('crmMapToggles').addEventListener('click', event => { const button = event.target.closest('[data-mode]'); if (button) { crmMapMode = button.dataset.mode; refreshCRMMapMode(); } });
}
function refreshCRMMapMode() {
  const state = crmMapState; if (!state || !crmMapLayer) return;
  const projected = projectedVotesByArea(), values = crmMapMode === 'proyectado' ? projected : state.votesByArea, max = Math.max(1, ...Object.values(values));
  renderMapBreakdown(values, state.namesByArea, crmMapMode === 'proyectado' ? `Meta proyectada por ${state.config.title}` : `Votos por ${state.config.title}`);
  document.querySelectorAll('#crmMapToggles .map-toggle[data-mode]').forEach(b => b.classList.toggle('active', b.dataset.mode === crmMapMode));
  crmMapLayer.eachLayer(layer => {
    const key = state.config.code(layer.feature.properties), observed = Number(state.votesByArea[key] || 0), proj = Number(projected[key] || 0), value = Number(values[key] || 0);
    layer.setStyle({ fillColor: MAP_COLOR(value / max), fillOpacity: key === state.targetKey ? .78 : .38 });
    layer.bindTooltip(`<strong>${state.config.name(layer.feature.properties)}</strong><br>${(crmMapMode === 'proyectado' ? proj : observed).toLocaleString('es-CO')} ${crmMapMode === 'proyectado' ? 'votos proyectados' : 'votos'}`, { sticky: true });
  });
  $('crmMapNote').textContent = (crmMapMode === 'proyectado' ? `Meta total distribuida proporcionalmente a la votación histórica. Haga clic en una ${state.config.title} para ver su detalle.` : `Votación total histórica. Haga clic en una ${state.config.title} para ver el detalle y su meta proyectada.`) + notaRecorte();
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
  if (alcance.municipio) return mun === alcance.municipio;
  return normalizedText(mesa.munNom || '') === alcance.municipioNombre;
}
async function datosCandidatura(candidate) {
  const url = candidate?.dataUrl || '';
  if (!datosCandidaturaCache.has(url)) datosCandidaturaCache.set(url, fetch(url).then(r => r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status))).catch(error => { datosCandidaturaCache.delete(url); throw error; }));
  const data = await datosCandidaturaCache.get(url), alcance = alcanceObjetivo(), mesas = data.mesas || [];
  if (!alcance) { recorteActivo = null; return { ...data, mesas, recorte: null }; }
  const dentro = mesas.filter(mesa => mesaEnAlcance(mesa, alcance)), votos = m => m.reduce((sum, mesa) => sum + Number(mesa.v || 0), 0);
  recorteActivo = { alcance, mesasFuera: mesas.length - dentro.length, votosFuera: votos(mesas) - votos(dentro), votosDentro: votos(dentro) };
  return { ...data, mesas: dentro, recorte: recorteActivo };
}
function notaRecorte(recorte = recorteActivo) {
  if (!recorte || !recorte.mesasFuera) return '';
  const donde = recorte.alcance.tipo === 'municipio' ? ($('campaignMunicipality').value || 'el municipio') : ($('campaignDepartment').options[$('campaignDepartment').selectedIndex]?.text || 'el departamento');
  return ` Se muestran solo los votos en ${donde}: quedaron por fuera ${recorte.votosFuera.toLocaleString('es-CO')} votos en ${recorte.mesasFuera.toLocaleString('es-CO')} mesas de otros territorios, que no cuentan para esta candidatura.`;
}

/* Mapa genérico: por departamento (nacional), o el municipio recortado del
   departamento cuando la evidencia pertenece a un solo municipio. */
async function renderGenericMap(candidate) {
  crmMapState = null;
  const candidateData = await datosCandidatura(candidate), mesas = candidateData.mesas || [], total = mesas.reduce((sum, m) => sum + Number(m.v || 0), 0) || Number(candidate.votos) || 0;
  const municipalityCodes = [...new Set(mesas.map(m => String(m.mun || '').replace(/^0+/, '')).filter(Boolean))];
  let geoData, votesByArea = {}, namesByArea = {}, featureCode, featureName, detailNote, breakdownTitle;
  if (municipalityCodes.length === 1 && mesas[0]?.dep) {
    const depCode = String(mesas[0].dep).padStart(2, '0'), municipalGeo = await fetchJSON(`${S3}/mapas-2026/Departamentos-mps/${depCode}.json`), municipalCode = municipalityCodes[0];
    geoData = { ...municipalGeo, features: municipalGeo.features.filter(f => String(f.properties?.mun_elec || f.properties?.mun_electoral || '').replace(/^0+/, '') === municipalCode) };
    if (!geoData.features.length) throw new Error('Municipio histórico sin geometría');
    const municipalName = mesas.find(m => m.munNom)?.munNom || candidate.circunscripcion || 'municipio';
    votesByArea = { [municipalCode]: total }; namesByArea = { [municipalCode]: municipalName };
    featureCode = p => String(p.mun_elec || p.mun_electoral || '').replace(/^0+/, ''); featureName = p => p.mpio_cnmbr || municipalName;
    $('crmMapTitle').textContent = `¿Dónde estuvo su votación en ${municipalName}?`; detailNote = 'Votación histórica concentrada en este municipio; la nueva campaña puede ubicarse en otro territorio.'; breakdownTitle = 'Votos en el municipio';
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
  crmMapLayer = L.geoJSON(geoData, { style: f => ({ color: '#fff', weight: 1, fillColor: MAP_COLOR((votesByArea[featureCode(f.properties)] || 0) / max), fillOpacity: .94 }), onEachFeature: (f, layer) => layer.bindTooltip(`<strong>${featureName(f.properties)}</strong><br>${(votesByArea[featureCode(f.properties)] || 0).toLocaleString('es-CO')} votos`, { sticky: true }) }).addTo(crmLeafletMap);
  encuadrar(crmMapLayer, 15);
  $('crmMapVotes').textContent = `${total.toLocaleString('es-CO')} votos`; $('crmMapNote').textContent = detailNote + notaRecorte();
}
/* Las JAL se leen a escala de comuna/localidad con las capas de Análisis de
   Candidato. */
const CITY_JAL_LAYERS = [
  { match: ['BOGOTA'], path: 'BOG-LOCALIDADX.json', title: 'localidad', code: p => String(p.LocCodigo || '').padStart(2, '0'), name: p => p.LocNombre || 'Localidad', rotate: true },
  { match: ['MEDELLIN'], path: 'MEDELLINX.json', title: 'comuna', code: p => String(p.CODIGO || '').padStart(2, '0'), name: p => p.NOMBRE || p.IDENTIFICACION || 'Comuna' },
  { match: ['CALI'], path: 'CALIX.json', title: 'comuna', code: p => String(p.comuna || '').padStart(2, '0'), name: p => p.nombre || 'Comuna' },
  { match: ['PEREIRA'], path: 'PEREIRAX.json', title: 'comuna', code: p => normalizedText(p.Comuna), name: p => p.Comuna || 'Comuna', mesaKey: m => normalizedText(String(m.comNom || '').replace(/^\d+\s*COMUNA\s*/i, '')) },
  { match: ['IBAGUE'], path: 'IBAGUEX.json', title: 'comuna', code: p => String(p.COMUNAS || '').replace(/\D/g, '').padStart(2, '0'), name: p => p.COMUNAS || 'Comuna' },
  { match: ['BARRANQUILLA'], path: 'BARRANQUILLAX.json', title: 'localidad', code: p => ({ 4: '01', 2: '02', 1: '03', 3: '04', 5: '05' })[Number(p.id)] || '', name: p => p.nombre || 'Localidad' },
  { match: ['MONTERIA'], path: 'MONTERIAX.json', title: 'comuna', code: p => String(p.CC_COMUNA || '').padStart(2, '0'), name: p => p.NMG || 'Comuna' },
  { match: ['MANIZALES'], path: 'MANIZALESX.json', title: 'comuna', code: p => String(p.ID_COMUNA || '').padStart(2, '0'), name: p => p.NOMBRES_CO || 'Comuna' }
];
function cityLayerFor(nombre) { const city = normalizedText(nombre); return CITY_JAL_LAYERS.find(item => item.match.some(name => city.includes(name))) || null; }
/* Pinta una ciudad por comuna/localidad con el estado compartido de los mapas
   de ciudad (toggles, detalle por barrio, niveles). */
function pintarCiudad({ geoData, config, mesas, total, votesByArea, namesByArea, targetKey, city, rotate, title, note, center, zoom, fitTarget }) {
  completaNombres(geoData, config.code, config.name, namesByArea);
  const max = Math.max(1, ...Object.values(votesByArea));
  crmMapMode = 'total';
  crmMapState = { city, config, geoData, votesByArea, namesByArea, mesas, total, max, targetKey, focusKey: null };
  $('crmMapTitle').textContent = title; ensureCRMMapToggles();
  crearMapa(center || [4.6, -74.1], zoom || 5); aplicarBasemap(Boolean(rotate));
  let targetLayer = null;
  crmMapLayer = L.geoJSON(geoData, {
    style: f => { const key = config.code(f.properties); return { color: '#fff', weight: key === targetKey ? 2 : 1, fillColor: MAP_COLOR((votesByArea[key] || 0) / max), fillOpacity: key === targetKey ? .78 : .42 }; },
    onEachFeature: (f, layer) => { if (config.code(f.properties) === targetKey) targetLayer = layer; layer.on('click', () => showCRMMapDetail(layer)); }
  }).addTo(crmLeafletMap);
  refreshCRMMapMode();
  encuadrar(fitTarget && targetLayer ? targetLayer : crmMapLayer, 24);
  $('crmMapVotes').textContent = `${total.toLocaleString('es-CO')} votos`;
  $('crmMapNote').textContent = note + notaRecorte();
}
function agregarPorArea(mesas, keyFn) { const votesByArea = {}, namesByArea = {}; mesas.forEach(m => { const key = keyFn(m); votesByArea[key] = (votesByArea[key] || 0) + Number(m.v || 0); namesByArea[key] = nombreLocal(m) || namesByArea[key]; }); return { votesByArea, namesByArea }; }
async function renderJalCityMap(candidate) {
  const data = await datosCandidatura(candidate), mesas = data.mesas || [], config = cityLayerFor(mesas[0]?.munNom || candidate.circunscripcion);
  if (!config) throw new Error('Ciudad sin capa local');
  let geoData = await fetchJSON(`${S3}/mapas-2026/Ciudades-COM-LOC/${config.path}`); if (config.rotate) geoData = rotateGeoJSON90Left(geoData);
  const { votesByArea, namesByArea } = agregarPorArea(mesas, m => config.mesaKey ? config.mesaKey(m) : claveLocal(m));
  const total = mesas.reduce((sum, m) => sum + Number(m.v || 0), 0) || Number(candidate.votos) || 0, targetKey = Object.entries(votesByArea).sort((a, b) => b[1] - a[1])[0]?.[0];
  pintarCiudad({ geoData, config, mesas, total, votesByArea, namesByArea, targetKey, city: normalizedText(mesas[0]?.munNom || ''), rotate: config.rotate, title: `¿Dónde estuvo su votación en ${mesas[0]?.munNom || 'la ciudad'}?`, note: `Distribución por ${config.title} de su candidatura JAL. Haga clic en una ${config.title} para ver el detalle por barrio.`, fitTarget: true });
}
async function renderBogotaCampaignMap(candidate) {
  const data = await datosCandidatura(candidate), mesas = data.mesas || [];
  const geoSource = rotateGeoJSON90Left(await fetchJSON(`${S3}/mapas-2026/Ciudades-COM-LOC/BOG-LOCALIDADX.json`));
  const geoData = { ...geoSource, features: geoSource.features.filter(f => String(f.properties.LocCodigo) !== '20') };   /* sin Sumapaz: aplasta el mapa */
  const config = { title: 'localidad', code: p => String(p.LocCodigo || '').padStart(2, '0'), name: p => p.LocNombre || 'Localidad' };
  const { votesByArea, namesByArea } = agregarPorArea(mesas, claveLocal);
  const total = mesas.reduce((sum, m) => sum + Number(m.v || 0), 0) || Number(candidate.votos) || 0;
  pintarCiudad({ geoData, config, mesas, total, votesByArea, namesByArea, targetKey: null, city: 'BOGOTA', rotate: true, title: '¿Dónde estuvo su votación en Bogotá?', note: 'Vista de Bogotá sin Sumapaz. Seleccione una localidad para abrir el desglose por barrio.' });
}
async function renderCaliCampaignMap(candidate) {
  const data = await datosCandidatura(candidate), mesas = data.mesas || [], geoData = await fetchJSON(`${S3}/mapas-2026/Ciudades-COM-LOC/CALIX.json`);
  const config = { title: 'comuna', code: p => String(p.comuna || '').padStart(2, '0'), name: p => p.nombre || `Comuna ${p.comuna}` };
  const votesByArea = {}, namesByArea = {};
  mesas.forEach(m => { const key = claveLocal(m); votesByArea[key] = (votesByArea[key] || 0) + Number(m.v || 0); namesByArea[key] = (nombreLocal(m) || namesByArea[key] || `Comuna ${Number(key)}`).replace(/^\d+\s*COMUNA\s*/i, 'Comuna '); });
  const total = mesas.reduce((sum, m) => sum + Number(m.v || 0), 0) || Number(candidate.votos) || 0, targetKey = Object.entries(votesByArea).sort((a, b) => b[1] - a[1])[0]?.[0];
  pintarCiudad({ geoData, config, mesas, total, votesByArea, namesByArea, targetKey, city: 'CALI', rotate: false, title: '¿Dónde estuvo su votación en Cali?', note: 'Seleccione una comuna para abrir la votación por barrio.', center: [3.44, -76.53], zoom: 11 });
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
  crmMapMode = 'total';
  $('crmMapVotes').textContent = 'Cargando'; $('crmMapNote').textContent = 'Cargando distribución territorial desde el historial del candidato.';
  const isJal = String(candidate.corp || '').toUpperCase().startsWith('JAL');
  try {
    if (isCaliElection(candidate)) return await renderCaliCampaignMap(candidate);
    if (isBogotaElection(candidate, currentTargetTerritory())) return await renderBogotaCampaignMap(candidate);
    if (isJal) { try { return await renderJalCityMap(candidate); } catch (e) { /* ciudad sin capa → genérico */ } }
    return await renderGenericMap(candidate);
  } catch (e) {
    $('crmMap').innerHTML = '<div style="padding:28px;color:#667068">No fue posible cargar el mapa histórico en este momento.</div>'; crmLeafletMap = null; crmMapLayer = null; crmTileLayer = null;
    $('crmBreakdown').innerHTML = '<p class="helper">No fue posible cargar el desglose territorial.</p>'; $('crmMapVotes').textContent = 'Sin mapa'; $('crmMapNote').textContent = 'La fuente del historial no respondió; podrá reintentar al abrir el CRM.';
  }
}

/* Barrios: polígonos locales (Bogotá y Cali) o puestos georreferenciados. */
function loadCandidateMapScript(src) { return new Promise((resolve, reject) => { const script = document.createElement('script'); script.src = src; script.async = true; script.onload = resolve; script.onerror = () => reject(new Error(`No se pudo cargar ${src}`)); document.head.appendChild(script); }); }
let bogotaPuestoBarrioPromise = null, caliPuestoBarrioPromise = null;
const bogotaBarriosPorLocalidad = new Map(), caliBarriosPorComuna = new Map();
async function bogotaBarrios(localityCode) {
  const key = String(localityCode || '').padStart(2, '0');
  if (!bogotaPuestoBarrioPromise) bogotaPuestoBarrioPromise = window.Candidato360BogotaPuestoBarrio ? Promise.resolve(window.Candidato360BogotaPuestoBarrio) : loadCandidateMapScript('candidato-360-data/bogota-puesto-barrio.js').then(() => window.Candidato360BogotaPuestoBarrio);
  if (!bogotaBarriosPorLocalidad.has(key)) bogotaBarriosPorLocalidad.set(key, (window.Candidato360BogotaBarrios?.[key] ? Promise.resolve() : loadCandidateMapScript(`candidato-360-data/bogota-barrios/${key}.js`)).then(() => { const geo = window.Candidato360BogotaBarrios?.[key]; if (!geo) throw new Error(`Sin cartografía barrial para la localidad ${key}`); return rotateGeoJSON90Left(geo); }));
  return Promise.all([bogotaPuestoBarrioPromise, bogotaBarriosPorLocalidad.get(key)]);
}
async function caliBarrios(comunaCode) {
  const key = String(comunaCode || '').padStart(2, '0');
  if (!caliPuestoBarrioPromise) caliPuestoBarrioPromise = window.Candidato360CaliPuestoBarrio ? Promise.resolve(window.Candidato360CaliPuestoBarrio) : loadCandidateMapScript('candidato-360-data/cali-puesto-barrio.js').then(() => window.Candidato360CaliPuestoBarrio);
  if (!caliBarriosPorComuna.has(key)) caliBarriosPorComuna.set(key, (window.Candidato360CaliBarrios?.[key] ? Promise.resolve() : loadCandidateMapScript(`candidato-360-data/cali-barrios/${key}.js`)).then(() => { const geo = window.Candidato360CaliBarrios?.[key]; if (!geo) throw new Error(`Sin cartografía barrial para la comuna ${key}`); return geo; }));
  return Promise.all([caliPuestoBarrioPromise, caliBarriosPorComuna.get(key)]);
}
function pintarBarrios(geo, values, codeOf, nameOf, nota) {
  if (crmBarrioLayer) crmLeafletMap.removeLayer(crmBarrioLayer);
  const max = Math.max(1, ...Object.values(values));
  crmBarrioLayer = L.geoJSON(geo, {
    style: f => { const votes = values[codeOf(f)] || 0; return { fillColor: MAP_COLOR(votes / max), fillOpacity: votes ? .82 : .28, color: 'rgba(23,37,28,.38)', weight: .55 }; },
    onEachFeature: (f, layer) => { const votes = Number(values[codeOf(f)] || 0); layer.bindTooltip(`<strong>${nameOf(f)}</strong><br>${votes.toLocaleString('es-CO')} ${crmMapMode === 'proyectado' ? 'votos proyectados' : 'votos'}`, { sticky: true }); layer.on('mouseover', () => layer.setStyle({ weight: 1.5, color: '#fff' })); layer.on('mouseout', () => crmBarrioLayer.resetStyle(layer)); }
  }).addTo(crmLeafletMap);
  encuadrar(crmBarrioLayer, 20);
  $('crmMapNote').textContent = nota;
}
async function renderBarriosForArea(key) {
  const state = crmMapState; if (!state) return;
  state.focusKey = key;
  const mesas = state.mesas.filter(m => (state.config.mesaKey ? state.config.mesaKey(m) : claveLocal(m)) === key), localGoal = Number(projectedVotesByArea()[key] || 0);
  const titulo = `${crmMapMode === 'proyectado' ? 'Meta proyectada' : 'Votos totales'} por barrio`;
  const conValores = historical => crmMapMode === 'proyectado' ? distributeVotes(historical, localGoal) : historical;
  $('crmBreakdown').innerHTML = '<h4>Votos por barrio</h4><p class="helper">Cargando polígonos y resultados barriales…</p>';
  if (state.city === 'CALI') {
    try {
      const [puestoBarrio, geo] = await caliBarrios(key), historical = {};
      mesas.forEach(m => { const barrio = puestoBarrio[electoralPlaceCode(m)]?.barrio; if (barrio) historical[barrio] = (historical[barrio] || 0) + Number(m.v || 0); });
      const values = conValores(historical);
      renderMapBreakdown(values, Object.fromEntries(geo.features.map(f => [f.properties.barrio, f.properties.barrio])), titulo);
      return pintarBarrios(geo, values, f => f.properties.barrio, f => f.properties.barrio, `Detalle poligonal por barrio de ${state.namesByArea[key] || `la comuna ${key}`}.`);
    } catch (e) { $('crmBreakdown').innerHTML = '<h4>Votos por barrio</h4><p class="helper">No fue posible cargar los polígonos barriales de esta comuna.</p>'; return; }
  }
  if (state.mesas.some(m => String(m.dep) === '16')) {
    try {
      const [puestoBarrio, geo] = await bogotaBarrios(key), historical = {}, code6 = v => String(v).padStart(6, '0');
      mesas.forEach(m => { const barrio = puestoBarrio[`${String(m.zon || '').padStart(2, '0')}-${String(m.pue || '').padStart(2, '0')}`]; if (barrio) historical[code6(barrio)] = (historical[code6(barrio)] || 0) + Number(m.v || 0); });
      const values = conValores(historical);
      renderMapBreakdown(values, Object.fromEntries(geo.features.map(f => [code6(f.properties.codigo), f.properties.nombre])), titulo);
      return pintarBarrios(geo, values, f => code6(f.properties.codigo), f => f.properties.nombre, `Detalle poligonal por barrio de ${geo.features[0]?.properties.loc_nombre || 'la localidad'}.`);
    } catch (e) { /* sin polígono → puestos */ }
  }
  let places = {}; try { places = await puestosPorBarrio(); } catch (e) {}
  const historical = {}, points = {};
  mesas.forEach(m => { const place = places[electoralPlaceCode(m)], name = place?.barrio || m.pueNom || 'Puesto sin barrio identificado'; historical[name] = (historical[name] || 0) + Number(m.v || 0); if (place && Number.isFinite(place.lat) && Number.isFinite(place.lng)) points[name] = place; });
  const values = conValores(historical);
  renderMapBreakdown(values, Object.fromEntries(Object.keys(values).map(name => [name, name])), titulo);
  if (crmBarrioLayer) crmLeafletMap.removeLayer(crmBarrioLayer);
  crmBarrioLayer = L.layerGroup(Object.entries(points).map(([name, point]) => L.circleMarker([point.lat, point.lng], { radius: 6, color: '#fff', weight: 1, fillColor: '#ee745e', fillOpacity: .9 }).bindTooltip(`<strong>${name}</strong><br>${Number(values[name] || 0).toLocaleString('es-CO')} ${crmMapMode === 'proyectado' ? 'votos proyectados' : 'votos'}`, { sticky: true }))).addTo(crmLeafletMap);
  const layer = crmMapLayer.getLayers().find(item => state.config.code(item.feature.properties) === key);
  $('crmMapNote').textContent = `Detalle por barrio de ${layer ? state.config.name(layer.feature.properties) : 'la localidad'}. ${Object.keys(places).length ? '' : 'La fuente de barrios no respondió; se muestran puestos de votación.'}`;
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
  for (const record of electionViewRecords) { if (!electionViewSnapshots.has(record.year)) await showElectionYear(record, { restoreToggles: false }); }
  const snapshots = [...electionViewSnapshots.values()];
  if (!snapshots.length) { showTerritoryNotApplicable('PROMEDIO'); renderElectionViewToggles(); return; }
  const compatible = snapshots.filter(s => s.config?.title === snapshots[0].config?.title), reference = compatible[compatible.length - 1];
  const keys = new Set(compatible.flatMap(s => Object.keys(s.votesByArea || {})));
  const votesByArea = Object.fromEntries([...keys].map(key => [key, Math.round(compatible.reduce((sum, s) => sum + Number(s.votesByArea[key] || 0), 0) / compatible.length)]));
  crmMapState = { ...reference, votesByArea, total: Object.values(votesByArea).reduce((sum, v) => sum + Number(v || 0), 0), max: Math.max(1, ...Object.values(votesByArea)), targetKey: null, focusKey: null };
  crmMapMode = projected ? 'proyectado' : 'total'; electionViewActive = projected ? 'projected' : 'average';
  if (crmBarrioLayer) { crmLeafletMap.removeLayer(crmBarrioLayer); crmBarrioLayer = null; }
  electionViewStyleMap();
  $('crmMapNote').textContent = projected ? 'Meta distribuida desde el promedio de las elecciones comparables.' : 'Promedio simple de las elecciones comparables en esta entidad territorial.';
  renderElectionViewToggles(); refreshMapLevels();
}
async function showElectionView(view) {
  if (view === 'average') return showElectionAverage(false);
  if (view === 'projected') return showElectionAverage(true);
  const record = electionViewRecords.find(item => item.year === view); if (record) return showElectionYear(record);
}
/* Niveles Municipio / Localidad / Barrio: solo tienen sentido sobre un mapa de
   ciudad (crmMapState); sobre el genérico por departamento se retiran. */
function setMapLevel(level) {
  const controls = $('crmMap')?.querySelector('.crm-map-levels'); if (!controls) return;
  controls.querySelectorAll('[data-level]').forEach(b => b.classList.toggle('active', b.dataset.level === level));
  const barrio = controls.querySelector('[data-level="barrio"]'); if (barrio) barrio.disabled = !crmMapState?.focusKey;
}
function refreshMapLevels() {
  const mapEl = $('crmMap'); if (!mapEl) return;
  mapEl.querySelector('.crm-map-levels')?.remove();
  const state = crmMapState; if (!state?.config) return;
  const isJal = String(crmCandidate?.corp || '').toUpperCase().startsWith('JAL'), localLabel = state.config.title === 'comuna' ? 'Comuna' : 'Localidad';
  const controls = document.createElement('div'); controls.className = 'crm-map-levels';
  controls.innerHTML = `${isJal ? '' : '<button type="button" class="crm-map-level" data-level="municipio">Municipio</button>'}<button type="button" class="crm-map-level" data-level="localidad">${localLabel}</button><button type="button" class="crm-map-level" data-level="barrio" disabled>Barrio</button>`;
  mapEl.append(controls);
  const volver = level => { if (crmBarrioLayer) { crmLeafletMap.removeLayer(crmBarrioLayer); crmBarrioLayer = null; } if (crmMapState) crmMapState.focusKey = null; refreshCRMMapMode(); encuadrar(crmMapLayer, 24); setMapLevel(level); };
  controls.querySelector('[data-level="municipio"]')?.addEventListener('click', () => volver('municipio'));
  controls.querySelector('[data-level="localidad"]')?.addEventListener('click', () => volver('localidad'));
  controls.querySelector('[data-level="barrio"]').addEventListener('click', () => { if (crmMapState?.focusKey) { renderBarriosForArea(crmMapState.focusKey); setMapLevel('barrio'); } });
  setMapLevel(state.focusKey ? 'barrio' : isJal ? 'localidad' : 'municipio');
}
/* Punto de entrada del mapa histórico. */
async function loadHistoricalMap(candidate) {
  electionViewRecords = []; electionViewSnapshots = new Map(); electionViewActive = ''; $('crmMapToggles')?.remove(); crmMapState = null; recorteActivo = null;
  const records = electionViewHistory(candidate);
  if (records.length < 2) { await renderSingleElection(candidate); ensureCRMMapToggles(); refreshMapLevels(); return; }
  electionViewRecords = records; electionViewActive = records[records.length - 1].year;
  await showElectionYear(records[records.length - 1], { restoreToggles: false });
  renderElectionViewToggles();
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
      geoData = { ...src, features: src.features.filter(f => String(f.properties.LocCodigo) !== '20') };
      nameOf = f => f.properties.LocNombre || 'Localidad'; isTarget = f => c.corp !== 'jal' || normalizedText(f.properties.LocNombre) === normalizedText(cortoLocal(c.localidad));
    } else if (CORP_MUNICIPAL.includes(c.corp) && c.corp === 'jal' && cityLayerFor(c.municipio)) {
      const cfg = cityLayerFor(c.municipio); let src = await fetchJSON(`${S3}/mapas-2026/Ciudades-COM-LOC/${cfg.path}`); if (cfg.rotate) { src = rotateGeoJSON90Left(src); rotate = true; }
      geoData = src; unidad = cfg.title; nameOf = f => cfg.name(f.properties); isTarget = f => { const n = normalizedText(cfg.name(f.properties)), corto = normalizedText(cortoLocal(c.localidad)); return n === loc || (corto && (n === corto || n.includes(corto) || corto.includes(n))); };
    } else {
      geoData = await fetchJSON(`${S3}/mapas-2026/Departamentos-mps/${dep}.json`);
      nameOf = f => f.properties.mpio_cnmbr || 'Municipio'; isTarget = f => CORP_DEPARTAMENTAL.includes(c.corp) || normalizedText(f.properties.mpio_cnmbr) === muni;
    }
    crearMapa([4.6, -74.1], 5); aplicarBasemap(rotate);
    let targetLayer = null, n = 0;
    crmMapLayer = L.geoJSON(geoData, { style: f => ({ color: '#fff', weight: isTarget(f) ? 2 : 1, fillColor: isTarget(f) ? '#3e8a5b' : '#d8dfd7', fillOpacity: isTarget(f) ? .82 : .5 }), onEachFeature: (f, layer) => { layer.bindTooltip(`<strong>${nameOf(f)}</strong>`, { sticky: true }); if (isTarget(f)) { n++; if (!targetLayer) targetLayer = layer; } } }).addTo(crmLeafletMap);
    encuadrar(CORP_DEPARTAMENTAL.includes(c.corp) || n > 1 ? crmMapLayer : (targetLayer || crmMapLayer), 24);
    filas = geoData.features.map(nameOf).sort((a, b) => a.localeCompare(b, 'es'));
    $('crmBreakdown').innerHTML = `<h4>${CORP_DEPARTAMENTAL.includes(c.corp) ? `Municipios de ${c.departamentoNombre}` : `${unidad === 'municipio' ? 'Municipios' : unidad === 'comuna' ? 'Comunas' : 'Localidades'} en el mapa`}</h4>` + filas.map(nm => `<div class="crm-breakdown-item static${normalizedText(nm) === (c.corp === 'jal' ? loc : muni) ? ' is-target' : ''}"><span class="crm-breakdown-row"><b>${escHtml(nm)}</b></span></div>`).join('');
    $('crmMapNote').textContent = CORP_DEPARTAMENTAL.includes(c.corp) ? `La circunscripción es todo ${c.departamentoNombre}: ${filas.length} municipios.` : `En verde, el territorio al que aspira. Sin historial propio no hay votos que distribuir; la meta de la derecha sale de los resultados de 2023 en ese territorio.`;
  } catch (e) {
    $('crmMap').innerHTML = '<div style="padding:28px;color:#667068">No fue posible cargar el territorio en este momento.</div>'; crmLeafletMap = null; crmMapLayer = null; crmTileLayer = null;
    $('crmBreakdown').innerHTML = '<p class="helper">No fue posible cargar el territorio.</p>'; $('crmMapNote').textContent = 'La fuente cartográfica no respondió.';
  }
}

/* ─── 10. Arranque ───────────────────────────────────────────────────────── */
(function init() {
  montarWizardNuevo();
  toggleParty();
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
    if (SESSION.vinculo && new URLSearchParams(location.search).get('abrir') === '1') abrirVinculo();
  });
  setTimeout(() => { clearInterval(strategyMessageTimer); $('preload').classList.remove('active'); }, 6000);   /* red de seguridad si el worker no responde */
})();
