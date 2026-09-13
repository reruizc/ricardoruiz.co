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
let CAMPANA_ACTUAL = null;
async function guardarCampana(campana) {
  if (!SESSION.vinculo) return;
  CAMPANA_ACTUAL = campana;
  if (SESSION.vinculo.local) { SESSION.vinculo.campana = campana; return; }
  try { const r = await apiC360('/c360/campana', { method: 'POST', body: JSON.stringify({ campana }) }); if (r.ok) SESSION.vinculo = r.data.vinculo; } catch {}
}
/* La meta la calcula VoteTarget en el navegador; se guarda en la campaña para
   que el briefing la recuerde. Solo si cambió, para no gastar escrituras de KV. */
function guardarMeta(target) {
  const c = CAMPANA_ACTUAL || SESSION.vinculo?.campana; if (!c || !target || !SESSION.vinculo) return;
  if (Number(SESSION.vinculo.campana?.meta || 0) === Number(target)) return;
  guardarCampana({ ...c, meta: target });
}
/* Paneles 04 y 05: viven en su propio HTML (candidato-360-medios.html y
   candidato-360-redes.html) y lo que el CRM muestra es solo el estado de lo
   que esas páginas guardaron en el vínculo. */
function pintarEscucha() {
  const e = SESSION.vinculo?.escucha || {};
  const ideas = e.ideas?.length || 0, perfiles = e.redes?.perfiles?.length || 0;
  const medios = $('crmMediosEstado'), redes = $('crmRedesEstado');
  if (medios) medios.textContent = ideas ? `${ideas} ${ideas === 1 ? 'idea' : 'ideas'}` : 'Sin ideas';
  if (redes) redes.textContent = perfiles ? `${perfiles} ${perfiles === 1 ? 'cuenta' : 'cuentas'}${e.redes.validado ? ' · validadas' : ' · sin validar'}` : 'Sin cuentas';
}
/* Interruptor del briefing (panel 03 del CRM). El estado vive en el vínculo. */
function pintarBriefing() {
  const b = SESSION.vinculo?.briefing || null, btn = $('crmBriefingBtn'), est = $('crmBriefingEstado'), sub = $('crmBriefingSub'), inp = $('crmBriefingCorreo');
  if (!btn) return;
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
  if (SESSION.vinculo.local) { SESSION.vinculo.briefing = { activo: !on, correo, envios: 0 }; pintarBriefing(); $('crmBriefingSub').textContent = 'modo pruebas: el interruptor no se guardó en el servidor'; return; }
  const btn = $('crmBriefingBtn'); btn.disabled = true;
  try {
    const r = await apiC360('/c360/briefing', { method: 'POST', body: JSON.stringify({ activo: !on, correo }) });
    if (!r.ok) { alert(r.data?.error || `No se pudo cambiar el briefing (HTTP ${r.status})`); return; }
    SESSION.vinculo.briefing = r.data.briefing;
  } finally { btn.disabled = false; }
  pintarBriefing();
}

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
/* Vínculo de mentiras, solo en memoria: el CRM necesita uno para pintarse. */
function vinculoLocal(payload) { SESSION.vinculo = Object.assign({ local: true }, payload); }
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
  if (new URLSearchParams(location.search).get('comprar') === '1' && SESSION.listo && !SESSION.acceso) { history.replaceState(null, '', PAGINA); abrirPaywall(SESSION.token ? 'Su cuenta ya existe. Falta activar el acceso a Candidato 360.' : ''); }
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
  aviso.innerHTML = `<p>Búsquese: su historial está acá y lo puede abrir para ver de qué candidaturas hablamos. Lo que necesita acceso es el CRM que se construye con él — mapa, meta de votos y briefing. Cada cuenta se vincula a <b>un solo candidato</b>.</p><button type="button" onclick="abrirPaywall()">Activar mi candidatura</button>`;
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
  if (boton) boton.textContent = bloqueado ? 'Activar y abrir el CRM →' : 'Abrir CRM de campaña →';
  if (!bloqueado) return aviso?.remove();
  if (!aviso) {
    aviso = document.createElement('div');
    aviso.id = 'avisoGateRuta';
    aviso.className = 'c360-vitrina';
    (form.querySelector('.paso-pie') || boton)?.before(aviso);
  }
  aviso.innerHTML = `<p>Este es su historial y hasta acá puede llegar sin cuenta. El CRM —mapa por puesto de votación, meta de votos y briefing cada tres días— se abre con el acceso activo, y deja su cuenta vinculada a <b>este candidato</b>.</p><button type="button" onclick="abrirPaywall()">Ver qué incluye</button>`;
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
      if (d?.logos?.length) LOGOS_PARTIDOS.set(key, new Map(d.logos.map(l => [normalizedText(l.nombre), `candidato-360-data/logos-partidos/${key}/${l.archivo}`])));
      else if (!LOGOS_PARTIDOS.has(key)) LOGOS_PARTIDOS.set(key, new Map());
      return LOGOS_PARTIDOS.get(key);
    }));
  return logosPendientes.get(key);
}
function logoDePartido(nombre, dep) {
  const clave = normalizedText(nombre), key = String(dep || '').padStart(2, '0');
  return LOGOS_PARTIDOS.get(key)?.get(clave) || LOGOS_PARTIDOS.get(LOGOS_BASE)?.get(clave) || '';
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
async function pintarMapaDepto({ id = 'mapaDepto', codigo = '', nombre = '', municipio = '', select = '' } = {}) {
  const caja = $(id), lienzo = $(id + 'Lienzo'); if (!caja || !lienzo) return;
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
    const pista = codigo && !municipio && partes > 1 ? 'Toque su municipio' : '';
    /* Bogotá es distrito y departamento: «BOGOTÁ, D.C. · Bogotá D.C.» sobra. */
    const repetido = normalizedText(municipio) === normalizedText(nombre);
    $(id + 'Pie').innerHTML = escHtml(municipio && !repetido ? `${NOMBRE_BONITO(municipio)} · ${nombre}` : (nombre || 'Elija el departamento')) + (pista ? `<small>${pista}</small>` : '');
    caja.classList.toggle('sin-elegir', !nombre);
    caja.classList.toggle('es-municipal', Boolean(codigo) && Boolean(select));
    caja.classList.remove('hidden');
    return encendidos;
  } catch (e) {
    /* Si la capa municipal no está, el mapa no desaparece: vuelve al de
       Colombia con el departamento encendido, que es lo que había antes. */
    if (codigo) { lienzo.dataset.capa = ''; return pintarMapaDepto({ id, nombre, select: '' }); }
    ocultarMapaDepto(id);
  }
}
/* El mapa de la tarjeta del lugar y el del wizard preguntan lo mismo en dos
   formularios distintos: cada uno sabe de dónde leer su territorio. */
function mapaDeptoRuta() {
  const sel = $('campaignDepartment'), municipal = CORP_MUNICIPAL.includes($('otherCorporation').value);
  return pintarMapaDepto({ id: 'mapaDepto', codigo: sel?.value || '', nombre: nombreDepartamentoElegido(),
    municipio: municipal ? ($('campaignMunicipality')?.value || '') : '', select: municipal ? 'campaignMunicipality' : '' });
}
function mapaDeptoNuevo() {
  const sel = $('department'); if (!sel?.value) return ocultarMapaDepto('mapaDeptoNuevo');
  const municipal = MUNICIPAL_ELECTIONS.includes($('election').value);
  return pintarMapaDepto({ id: 'mapaDeptoNuevo', codigo: sel.value, nombre: sel.options[sel.selectedIndex]?.text || '',
    municipio: municipal ? ($('municipality')?.value || '') : '', select: municipal ? 'municipality' : '' });
}
/* Tocar un municipio en el mapa es responder el desplegable: el mapa no es un
   adorno al lado de la pregunta, es la otra manera de contestarla. */
document.addEventListener('click', evento => {
  const path = evento.target.closest?.('.mapa-depto.es-municipal .muni'); if (!path) return;
  const select = $(path.closest('.mapa-depto-lienzo')?.dataset.select || ''); if (!select) return;
  const opcion = [...select.options].find(o => o.value && normalizedText(o.value) === normalizedText(path.dataset.parte));
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
  if (CAMPANA_ACTUAL?.avales === 'firmas') return '';
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
  const firmas = CORP_UNINOMINAL.includes(corpKey) && avalVigente() === 'firmas';
  return { corp: corpKey, avales: firmas ? 'firmas' : 'partido', espectro: firmas ? espectroVigente() : '',
    partido: firmas ? '' : (String($('campaignParty')?.value || '').trim() || crmCandidate?.partido || ''), ruta: isOther ? 'other' : 'same', departamento: isOther ? $('campaignDepartment').value : '', departamentoNombre: isOther ? ($('campaignDepartment').options[$('campaignDepartment').selectedIndex]?.text || '') : '', municipio: isOther ? $('campaignMunicipality').value : '', localidad: isOther ? $('campaignLocality').value : '' };
}
/* Rellena la ruta con la campaña guardada (al volver con vínculo). */
async function precargarCampana(campana) {
  if (!campana) return;
  const isOther = campana.ruta === 'other' || !corporacionHistorica(crmCandidate);
  document.querySelector(`input[name="corporationRoute"][value="${isOther ? 'other' : 'same'}"]`).checked = true;
  if (campana.partido && $('campaignParty')) $('campaignParty').value = campana.partido;
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
function espectroVigente() { return $('espectro')?.querySelector('[aria-checked="true"]')?.dataset.bloque || ''; }
/* El bloque con el que se reparte: el que la persona eligió si va por firmas,
   y si no el que le corresponde a su partido. */
function bloqueVigente() {
  if (CAMPANA_ACTUAL?.avales === 'firmas' || (!CAMPANA_ACTUAL && avalVigente() === 'firmas')) return CAMPANA_ACTUAL?.espectro || espectroVigente() || '';
  return '';
}
function pintarEspectro() {
  const caja = $('espectro'); if (!caja || caja.dataset.listo === '1') return;
  caja.dataset.listo = '1';
  caja.innerHTML = ESPECTRO.map(([id, label]) => {
    const color = window.PartidosBloques?.BLOQUE_COLOR?.[id] || 'var(--green)';
    return `<button type="button" class="espectro-op" role="radio" aria-checked="false" data-bloque="${id}" style="--bloque:${color}"><i></i><b>${label}</b></button>`;
  }).join('');
  caja.addEventListener('click', e => {
    const boton = e.target.closest('[data-bloque]'); if (!boton) return;
    caja.querySelectorAll('[data-bloque]').forEach(b => b.setAttribute('aria-checked', String(b === boton)));
    salto(boton);
    refrescarContinuarPartido();
  });
}
function marcarEspectro(bloque) {
  pintarEspectro();
  $('espectro')?.querySelectorAll('[data-bloque]').forEach(b => b.setAttribute('aria-checked', String(b.dataset.bloque === bloque)));
}
/* La pregunta del aval solo aplica a los cargos uninominales: a un concejo o a
   una asamblea se llega por lista, y una lista siempre tiene organización. */
function elegirAval({ animar = false } = {}) {
  const firmas = avalVigente() === 'firmas';
  if (animar) salto(document.querySelector(`input[name="avalRuta"]:checked`)?.closest('.route-option'));
  revelar($('espectroField'), firmas, animar);
  revelar($('campaignPartyField'), !firmas, animar);
  revelar($('vitrinaPartidos'), !firmas && vitrinaTienePartidos(), animar);
  if (firmas) pintarEspectro(); else refrescarPartidoCampana();
  if (pasoRuta === 'partido' && firmas) { $('rutaTitulo').textContent = '¿Dónde se ubica?'; $('rutaCopy').textContent = 'Por firmas no hay partido cuya huella seguir. Con el espectro buscamos dónde votan los partidos de su familia: ahí es donde las firmas se recogen más rápido.'; }
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
  boton.disabled = avalVigente() === 'firmas' && !espectroVigente();
}
function prepararPasoPartido() {
  const uninominal = CORP_UNINOMINAL.includes(corpDeLaRuta());
  revelar($('avalOpciones'), uninominal, false);
  if (!uninominal) {
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
  if (!vitrinaTienePartidos() || avalVigente() === 'firmas') { caja.classList.add('hidden'); return; }
  rejilla.innerHTML = VITRINA.map((o, i) => `<button type="button" class="vitrina-op" data-i="${i}" title="${escHtml(o[0])}">${imgLogo(o[0], dep)}<small>${escHtml(nombreCortoPartido(o[0]))}</small></button>`).join('');
  caja.classList.remove('hidden');
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
}
async function loadLocalities() { await cargarLocalidades($('locality'), $('localityStatus'), $('department').options[$('department').selectedIndex].text, $('municipality').value); }
function updateTerritory() {
  const election = $('election').value, municipal = MUNICIPAL_ELECTIONS.includes(election);
  mapaDeptoNuevo();
  pintarEstadoPartido({ input: 'party', estado: 'partyStatus', departamento: () => $('department').value });
  $('municipalityField').classList.toggle('hidden', !municipal); $('localityField').classList.toggle('hidden', election !== 'jal');
  if (!municipal) $('municipalityNota').classList.add('hidden');
  $('municipality').required = municipal; $('locality').required = election === 'jal';
  if (municipal && $('department').value) loadMunicipalities(); else $('municipality').innerHTML = '<option value="">Primero seleccione departamento</option>';
  if (election !== 'jal') $('locality').innerHTML = '<option value="">Primero seleccione municipio</option>';
}
function updateLocality() { mapaDeptoNuevo(); if ($('election').value === 'jal' && $('municipality').value) loadLocalities(); }
function togglePublicName() { $('publicNameField').classList.toggle('hidden', !$('publicFigure').checked); $('publicName').required = $('publicFigure').checked; }
/* ─── 7 bis. Identidad pública: redes sociales y su validación ───────────────
   Hasta acá el paso 2 preguntaba un mote y seguía de largo: la escucha de la
   candidatura se armaba sobre un texto que nadie comprobó. Ahora la persona
   marca en qué redes está, escribe el usuario y ANTES de construir el punto de
   partida se valida: el worker (POST /c360/redes) sondea cada red por su
   fuente pública y le pide a DeepSeek un veredicto SOBRE ESA EVIDENCIA.

   Dos reglas del producto viven acá:
   · La llave de DeepSeek no puede estar en el navegador — este repo es
     público. Por eso el sondeo y el modelo viven en el worker (rr-auth ·
     src/c360-redes.js). Contrato: tools/candidato-360/redes/README.md.
   · Validar nunca bloquea. Si la red no deja comprobar (las tres bloquean
     tráfico de servidor de a ratos) o el endpoint todavía no está desplegado,
     el wizard sigue y la candidatura queda marcada «sin validar». Un candidato
     no se puede quedar por fuera de su propia campaña porque X no contestó. */
const REDES_DEFS = [
  { key: 'x', nombre: 'X', detalle: 'antes Twitter', ph: '@usuario' },
  { key: 'tiktok', nombre: 'TikTok', detalle: 'video corto', ph: '@usuario' },
  { key: 'instagram', nombre: 'Instagram', detalle: 'perfil público', ph: 'usuario' }
];
const VEREDICTOS = {
  confirmado: { etiqueta: 'Confirmado', clase: 'ok' },
  probable: { etiqueta: 'Probable', clase: 'ok' },
  dudoso: { etiqueta: 'Dudoso', clase: 'warn' },
  no_encontrado: { etiqueta: 'Sin cuenta', clase: 'bad' },
  no_verificable: { etiqueta: 'Sin comprobar', clase: 'warn' }
};
let REDES_VALIDACION = null;   /* respuesta del worker + la firma que la produjo */
let redesCargando = false, redesOmitir = false;

/* El usuario pega la URL completa tan seguido como escribe el @. Misma
   normalización que el worker, para que la firma del cache coincida. */
function limpiarHandle(valor) {
  return String(valor || '').trim()
    .replace(/^https?:\/\//i, '').replace(/^www\./i, '')
    .replace(/^(x|twitter|tiktok|instagram)\.com\//i, '')
    .split(/[?#]/)[0].split('/')[0].replace(/^@+/, '').trim();
}
function montarRedes() {
  const grid = $('redesGrid'); if (!grid) return;
  grid.innerHTML = REDES_DEFS.map(r => `<div class="red-row" data-red="${r.key}">
    <button type="button" class="red-chip" onclick="toggleRed('${r.key}')" aria-pressed="false"><i></i><b>${escHtml(r.nombre)}</b><small>${escHtml(r.detalle)}</small></button>
    <input class="red-handle" id="red-${r.key}" placeholder="${escHtml(r.ph)}" autocomplete="off" disabled oninput="redesTocadas()">
  </div>`).join('');
  pintarEstadoRedes();
}
function toggleRed(key) {
  const row = document.querySelector(`.red-row[data-red="${key}"]`); if (!row) return;
  const activa = row.classList.toggle('on');
  row.querySelector('.red-chip').setAttribute('aria-pressed', String(activa));
  const input = row.querySelector('.red-handle');
  input.disabled = !activa;
  if (activa) input.focus({ preventScroll: true }); else input.value = '';
  redesTocadas();
}
function redesElegidas() {
  return REDES_DEFS.map(r => ({ red: r.key, handle: limpiarHandle($(`red-${r.key}`)?.value) }))
    .filter(r => document.querySelector(`.red-row[data-red="${r.red}"]`)?.classList.contains('on') && r.handle);
}
function firmaRedes() {
  const n = ($('newName')?.value || '').trim().toLowerCase();
  return `${n}|${($('publicName')?.value || '').trim().toLowerCase()}|` + redesElegidas().map(r => `${r.red}:${r.handle.toLowerCase()}`).join(',');
}
/* Editar un usuario después de validar invalida el veredicto: si no, la
   candidatura se guardaría con el sello de una cuenta que ya no es la escrita. */
function redesTocadas() {
  if (REDES_VALIDACION && REDES_VALIDACION.firma !== firmaRedes()) { REDES_VALIDACION = null; redesOmitir = false; $('redesResultado').classList.add('hidden'); }
  pintarEstadoRedes();
}
function pintarEstadoRedes() {
  const est = $('redesEstado'), btn = $('redesBuscar'); if (!est || !btn) return;
  const n = redesElegidas().length;
  btn.disabled = redesCargando || !n;
  btn.textContent = redesCargando ? 'Buscando…' : (REDES_VALIDACION ? 'Volver a validar' : 'Buscar y validar');
  est.className = 'redes-estado' + (REDES_VALIDACION ? ' ok' : '');
  est.textContent = redesCargando ? 'Consultando cada red y leyendo señales abiertas…'
    : REDES_VALIDACION ? `Validado · ${REDES_VALIDACION.perfiles.length} ${REDES_VALIDACION.perfiles.length === 1 ? 'perfil' : 'perfiles'}`
    : n ? `${n} ${n === 1 ? 'red marcada' : 'redes marcadas'} · sin validar` : 'Marque una red y escriba su usuario';
}
async function validarRedes() {
  const redes = redesElegidas(); if (!redes.length) return;
  const nombre = ($('newName')?.value || '').trim();
  if (nombre.length < 3) { $('newName')?.focus(); return avisoRedes('Escriba primero su nombre completo: sin él no hay con qué comparar el perfil.'); }
  /* El usuario que se valida es el limpio: si pegó la URL, la casilla queda
     con el @ que de verdad se va a guardar. */
  redes.forEach(r => { const input = $(`red-${r.red}`); if (input && input.value !== r.handle) input.value = r.handle; });
  const firma = firmaRedes();
  redesCargando = true; pintarEstadoRedes();
  $('redesResultado').classList.remove('hidden');
  $('redesResultado').innerHTML = `<div class="redes-cargando"><i></i><span>Buscando @${escHtml(redes.map(r => r.handle).join(', @'))} en ${redes.length === 1 ? 'su red' : 'sus redes'} y cruzando con la prensa abierta…</span></div>`;
  const dep = $('department'), territorio = [$('locality')?.value, $('municipality')?.value, dep?.options[dep.selectedIndex]?.text].filter(Boolean).join(' · ');
  let r;
  try {
    r = await apiC360('/c360/redes', { method: 'POST', body: JSON.stringify({ nombre, alias: ($('publicName')?.value || '').trim(), corp: CRM_CORPORATIONS[$('election')?.value] || '', territorio, redes }) });
  } catch (e) { r = { status: 0, ok: false, data: {} }; }
  redesCargando = false;
  if (!r.ok || !Array.isArray(r.data?.perfiles)) return pintarFalloRedes(r);
  REDES_VALIDACION = Object.assign({}, r.data, { firma });
  redesOmitir = false;
  pintarValidacionRedes(REDES_VALIDACION);
  pintarEstadoRedes();
}
/* El error se dice tal cual es. Un 404 acá no es «no encontramos su perfil»:
   es que la ruta del worker todavía no existe, y confundir las dos cosas hace
   que el candidato borre un usuario que estaba bien escrito. */
function pintarFalloRedes(r) {
  /* El worker manda un `detalle` en español para casi todo (nombre corto, sin
     redes válidas, cuota del día, el modelo caído): se prefiere ese antes que
     una frase nuestra que puede estar diciendo otra cosa. */
  const motivo = r.status === 404 ? 'El buscador de redes todavía no está publicado en el servidor (falta la ruta <code>/c360/redes</code>).'
    : r.status === 401 ? 'Su sesión venció. Vuelva a entrar y repita la validación.'
    : r.status === 403 ? 'Su cuenta no tiene acceso a la validación de redes.'
    : r.data?.detalle ? escHtml(String(r.data.detalle))
    : r.status === 502 ? 'El modelo no contestó a tiempo. Vuelva a intentar en un minuto.'
    : r.status === 0 ? 'No hubo conexión con el servidor.'
    : `El servidor respondió ${escHtml(String(r.status))}${r.data?.error ? ` (${escHtml(String(r.data.error))})` : ''}.`;
  $('redesResultado').innerHTML = `<div class="redes-fallo"><b>No se pudo validar.</b><p>${motivo}</p><p class="redes-fallo-salida">Puede seguir: la candidatura queda marcada <b>sin validar</b> y las redes se guardan tal como las escribió.</p></div>`;
  redesOmitir = true;
  pintarEstadoRedes();
}
function avisoRedes(texto) {
  $('redesResultado').classList.remove('hidden');
  $('redesResultado').innerHTML = `<div class="redes-fallo"><p>${escHtml(texto)}</p></div>`;
}
function pintarValidacionRedes(d) {
  const fichas = d.perfiles.map(p => {
    const v = VEREDICTOS[p.veredicto] || VEREDICTOS.no_verificable, def = REDES_DEFS.find(x => x.key === p.red) || { nombre: p.red };
    const datos = [p.nombre_perfil ? `perfil a nombre de <b>${escHtml(p.nombre_perfil)}</b>` : '', p.seguidores != null ? `${escHtml(String(p.seguidores))} seguidores` : '', p.verificada ? 'cuenta verificada por la plataforma' : '', p.fuente === 'apify' ? 'comprobado vía Apify' : ''].filter(Boolean).join(' · ');
    return `<div class="red-ficha ${v.clase}">
      <div class="red-ficha-top"><b>${escHtml(def.nombre)}</b><a href="${escHtml(p.url)}" target="_blank" rel="noopener">@${escHtml(p.handle)}</a><span class="red-sello">${v.etiqueta}${p.confianza ? ` · ${p.confianza}%` : ''}</span></div>
      ${datos ? `<p class="red-ficha-datos">${datos}</p>` : ''}
      <p class="red-ficha-motivo">${escHtml(p.motivo || '')}</p></div>`;
  }).join('');
  const alertas = (d.alertas || []).length ? `<ul class="redes-alertas">${d.alertas.map(a => `<li>${escHtml(a)}</li>`).join('')}</ul>` : '';
  const homonimo = d.riesgo_homonimo ? `<p class="redes-homonimo"><b>Cuidado con el homónimo:</b> ${escHtml(d.riesgo_homonimo)}</p>` : '';
  const prensa = (d.titulares || []).length ? `<details class="redes-prensa"><summary>${d.titulares.length} titulares abiertos con ese nombre</summary><ul>${d.titulares.map(t => `<li><a href="${escHtml(t.link)}" target="_blank" rel="noopener">${escHtml(t.titulo)}</a>${t.medio ? ` · ${escHtml(t.medio)}` : ''}</li>`).join('')}</ul></details>` : '';
  $('redesResultado').classList.remove('hidden');
  $('redesResultado').innerHTML = `${d.resumen ? `<p class="redes-resumen">${escHtml(d.resumen)}</p>` : ''}${fichas}${homonimo}${alertas}${prensa}<p class="redes-pie">${escHtml(d.modelo || 'DeepSeek')} leyó lo que respondió cada red${d.cache_hit ? ' (respuesta guardada de una consulta reciente)' : ''}. Si algún veredicto no cuadra, corrija el usuario y vuelva a validar.</p>`;
}
/* Lo que se guarda en el vínculo: los usuarios y el sello con el que salieron.
   Sin validación se guarda igual, pero marcado — el briefing necesita saber si
   puede confiar en el perfil antes de escuchar en su nombre. */
/* Una frase para el CRM: qué identidad quedó lista para escuchar. */
function textoRedesCRM(redes) {
  if (!redes || !redes.perfiles?.length) return '';
  const buenos = redes.perfiles.filter(p => p.veredicto === 'confirmado' || p.veredicto === 'probable');
  const lista = redes.perfiles.map(p => `@${p.handle} (${(REDES_DEFS.find(d => d.key === p.red) || {}).nombre || p.red})`).join(', ');
  if (!redes.validado) return ` Escucharemos ${lista}: son las cuentas que usted escribió, todavía sin validar.`;
  return buenos.length
    ? ` Escucharemos ${buenos.map(p => `@${p.handle}`).join(', ')}: ${buenos.length === 1 ? 'la cuenta quedó validada' : 'las cuentas quedaron validadas'} contra la fuente pública de cada red.`
    : ` Ninguna de las cuentas escritas (${lista}) pudo validarse; la escucha queda pendiente de confirmarlas.`;
}
function redesParaGuardar() {
  const elegidas = redesElegidas();
  if (!elegidas.length) return null;
  const val = REDES_VALIDACION && REDES_VALIDACION.firma === firmaRedes() ? REDES_VALIDACION : null;
  return {
    validado: !!val,
    validadoEn: val ? val.generado_en : null,
    modelo: val ? val.modelo : null,
    resumen: val ? val.resumen : '',
    perfiles: elegidas.map(e => {
      const p = val?.perfiles.find(x => x.red === e.red);
      return { red: e.red, handle: e.handle, url: p?.url || `https://${e.red === 'x' ? 'x.com/' : e.red === 'tiktok' ? 'www.tiktok.com/@' : 'www.instagram.com/'}${e.handle}`, veredicto: p?.veredicto || 'sin_validar', confianza: p?.confianza || 0, nombrePerfil: p?.nombre_perfil || '' };
    })
  };
}

function toggleParty() { const isNew = $('partyMode').value === 'new'; $('partyExisting').classList.toggle('hidden', isNew); $('partyNew').classList.toggle('hidden', !isNew); $('party').required = !isNew; $('partyName').required = isNew; }
/* Una pregunta a la vez. Los campos se MUEVEN, no se recrean, para conservar
   validaciones y datos ya cargados. */
const NEW_STEPS_TOTAL = 6;
function montarWizardNuevo() {
  const form = document.querySelector('#new form'); if (!form) return;
  const findField = id => $(id)?.closest('.field');
  const fields = { name: findField('newName'), pub: findField('publicFigure'), pubName: $('publicNameField'), redes: $('redesField'), election: findField('election'), department: findField('department'), municipality: findField('municipality'), locality: findField('locality'), mapa: $('mapaDeptoNuevo')?.closest('.field'), partyMode: findField('partyMode'), partyExisting: $('partyExisting'), partyNew: $('partyNew'), goal: findField('goal') };
  const formGrid = form.querySelector('.form-grid'), originalSubmit = form.querySelector('[type="submit"]');
  const wizard = document.createElement('div'); wizard.className = 'new-wizard'; formGrid.before(wizard);
  Object.values(fields).forEach(f => f?.remove()); formGrid.remove(); originalSubmit.remove();
  const steps = [
    { title: '¿Cómo aparecerá en campaña?', copy: 'Empecemos por su nombre completo.', fields: [fields.name] },
    { title: '¿Dónde puede encontrarlo la gente?', copy: 'Su nombre público y sus redes. Buscamos cada cuenta y la validamos antes de montar la escucha sobre ella.', fields: [fields.pub, fields.pubName, fields.redes], redes: true },
    { title: '¿A qué corporación aspira?', copy: 'La corporación define el territorio y la lectura electoral que activaremos.', fields: [fields.election], cards: true },
    /* El mapa viaja con la pregunta del territorio: si se queda en la rejilla
       original lo borra el `formGrid.remove()` de abajo y el wizard pierde la
       confirmación que sí tiene la ruta. */
    { title: '¿Dónde será la candidatura?', copy: 'Ubique el territorio en el que va a competir.', fields: [fields.department, fields.municipality, fields.locality, fields.mapa] },
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
  montarRedes();   /* después de repartir los campos: antes, #redesGrid está desprendido del documento */
  function showNewWizardStep(index) {
    wizard.querySelectorAll('.new-wizard-step').forEach((s, p) => s.classList.toggle('active', p === index));
    const stepLabel = document.querySelector('#new .flow-top .step'); if (stepLabel) stepLabel.textContent = `Paso ${index + 1} de ${NEW_STEPS_TOTAL} · Candidatura nueva`;
  }
  function advanceNewWizard(index) {
    if (index === 2 && !electionSelect.value) { $('newCorporationPicker').classList.add('shake'); setTimeout(() => $('newCorporationPicker').classList.remove('shake'), 500); return; }
    /* Identidad: si marcó redes y no las ha validado, se pide una vez. A la
       segunda pasa igual — la validación informa, no es un peaje. */
    if (steps[index].redes && redesElegidas().length && !redesOmitir && !(REDES_VALIDACION && REDES_VALIDACION.firma === firmaRedes())) {
      redesOmitir = true;
      $('redesResultado').classList.remove('hidden');
      $('redesResultado').innerHTML = '<div class="redes-fallo"><b>Sus redes están sin validar.</b><p>Toque <b>Buscar y validar</b> para comprobar que esas cuentas son suyas. Si prefiere seguir, vuelva a tocar «Siguiente» y quedarán guardadas sin validar.</p></div>';
      $('redesBuscar').classList.add('shake'); setTimeout(() => $('redesBuscar').classList.remove('shake'), 500);
      return;
    }
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
  const nuevo = { nombre: $('newName').value.trim(), publico: $('publicFigure').checked, nombrePublico: $('publicName').value.trim(), partido: $('partyMode').value === 'new' ? $('partyName').value.trim() : $('party').value, partidoNuevo: $('partyMode').value === 'new', objetivo: $('goal').value, redes: redesParaGuardar() };
  const campana = { corp: $('election').value, ruta: 'other', departamento: dep.value, departamentoNombre: depNombre, municipio: MUNICIPAL_ELECTIONS.includes($('election').value) ? $('municipality').value : '', localidad: $('election').value === 'jal' ? $('locality').value : '' };
  if (!nuevo.nombre || !campana.corp || !campana.departamento) return;
  if (PRUEBAS) vinculoLocal({ tipo: 'nuevo', nuevo, campana });
  else if (!SESSION.vinculo) {
    const sigue = await confirmarVinculo(nuevo.nombre, `${CRM_CORPORATIONS[campana.corp]} · ${[campana.localidad, campana.municipio, depNombre].filter(Boolean).join(' · ')}`);
    if (!sigue) return;
    const r = await guardarVinculo({ tipo: 'nuevo', nuevo, campana });
    if (!r.ok) { if (r.existente) { alert(`Su cuenta ya está vinculada a ${vinculoDescripcion()}. Para cambiarla escriba a ${SESSION.soporte}.`); return abrirVinculo(); } if (r.sinAcceso) return abrirPaywall(); alert(`No se pudo guardar la candidatura: ${r.error}`); return; }
  }
  NUEVO = { ...nuevo, campana };
  /* El vínculo solo guarda lo que su normalizador conoce; las redes tienen ruta
     propia (/c360/escucha) porque las escriben también los paneles. */
  if (nuevo.redes?.perfiles?.length && SESSION.vinculo && !SESSION.vinculo.local) {
    const r = await apiC360('/c360/escucha', { method: 'POST', body: JSON.stringify({ redes: nuevo.redes }) });
    if (r.ok && r.data?.vinculo) SESSION.vinculo = r.data.vinculo;
  } else if (nuevo.redes?.perfiles?.length && SESSION.vinculo?.local) {
    SESSION.vinculo.escucha = { redes: nuevo.redes };
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
const NOMBRE_BONITO = s => String(s || '').toLowerCase().replace(/(^|[\s(\-·])([a-záéíóúñü])/g, (m, a, b) => a + b.toUpperCase())
  .replace(/\b(De|Del|La|Las|Los|Y|El)\b/g, w => w.toLowerCase()).replace(/^(\w)/, c => c.toUpperCase())
  /* Las siglas con punto se quedan como son: los puestos de votación se llaman
     "I.E. SAN JOSÉ" y "E.S.E. HOSPITAL", y «I.e.» no es un nombre. */
  .replace(/\b(?:[a-záéíóúñüA-ZÁÉÍÓÚÑÜ]\.){2,}/g, sigla => sigla.toUpperCase());
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
function tipoDeSalto(desde, hacia) {
  if (desde === hacia) return 'misma';
  if (desde === 'camara' || desde === 'senado') return 'congreso>territorial';
  if (desde === 'presidencial') return 'presidencial>territorial';
  return FRASES_SALTO[`${desde}>${hacia}`] ? `${desde}>${hacia}` : 'otra';
}
function elegir(lista, semilla) { let h = 0; for (const c of String(semilla || '')) h = (h * 31 + c.charCodeAt(0)) >>> 0; return lista[h % lista.length]; }
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
  const partido = String(campana?.partido || candidate?.partido || '').trim();
  const bloque = partido ? PartidosBloques.bloqueDeCandidatura(partido, candidate?.nombre || '') : 'sc';
  const partidoBonito = partido.replace(/^(PARTIDO|MOVIMIENTO)\s+(POLÍTICO\s+)?/i, '').split(' ').map(w => w.length > 3 ? NOMBRE_BONITO(w) : w.toLowerCase()).join(' ').replace(/^(\w)/, c => c.toUpperCase());
  const cambioDePartido = partido && candidate?.partido && normalizedText(partido) !== normalizedText(candidate.partido);
  const avalNuevo = !cambioDePartido ? ''
    : mudanza ? ' Es un aval nuevo, y en territorio nuevo: la huella que cuenta es la de ese partido allá.'
    : ' Es un aval nuevo: el mapa conserva su votación, la huella del partido cambia.';
  const conQuien = partido ? elegir(FRASES_BLOQUE[bloque] || FRASES_BLOQUE.sc, candidate?.nombre)(partidoBonito) + avalNuevo : '';
  const contexto = { lugarViejo: hist.lugar, lugarNuevo, mudanza, esCiudad: Boolean(cityLayerFor(lugarNuevo)) };
  const salto = punto(FRASES_SALTO[tipoDeSalto(hist.tipo, corpKey)](contexto));
  return [apertura, ahora, salto, conQuien].filter(Boolean).join(' ');
}

/* ─── 8. CRM: apertura, meta de votos y foto ─────────────────────────────── */
/* La meta depende del PARTIDO: no cuesta lo mismo entrar de décimo en una
   lista grande que arrastrar una lista pequeña. Va el aval con el que se
   lanza y el departamento (para estimar con la Cámara 2026 a quien no corrió
   en 2023). */
async function estimateVoteTarget(corp, territory) {
  const departamento = CAMPANA_ACTUAL?.departamento || departamentoDeCandidatura(crmCandidate);
  return VoteTarget.estimate({ corp, territory: territory || crmCandidate?.circunscripcion || '', baseUrl: S3, partido: partidoVigente(), departamento });
}
let META_ACTUAL = null;
function pintarMeta(estimate) {
  META_ACTUAL = estimate || null;
  if (estimate.target) { $('crmVoteNumber').textContent = estimate.target.toLocaleString('es-CO'); $('crmVoteTarget').textContent = `Meta inicial: ${estimate.target.toLocaleString('es-CO')} votos`; guardarMeta(estimate.target); }
  else { $('crmVoteNumber').textContent = '—'; $('crmVoteTarget').textContent = 'Meta pendiente de referencia territorial'; }
  $('crmVoteFormula').textContent = estimate.formula;
  /* La ⓘ solo aparece cuando hay una meta que explicar: junto a un guion no
     explica nada, y el propio panel ya dice que falta la referencia. */
  document.querySelectorAll('.meta-i').forEach(b => b.classList.toggle('hidden', !(estimate.target && estimate.detalle)));
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
    : P.tipo === 'lista-sin-curul'
      ? `<li><b>${fmt(P.votos)}</b> · <b>jalar la lista</b> de ${escHtml(P.lista.nombre)}: en 2023 sumó ${fmt(P.lista.total)} y la cifra repartidora fue ${fmt(P.cifra)}, le faltaron ${fmt(P.faltanLista)}. Si el resto de la lista repite, a quien la encabece le toca poner ${fmt(P.votos)}.</li>`
      : `<li><b>${fmt(P.votos)}</b> · ${escHtml(P.nombre)} no tuvo lista en esta corporación en 2023. Su fuerza se estima con la <b>Cámara de 2026</b>: ${fmt(P.camara.votos)} votos en el departamento, que al tamaño de esta corporación son ${fmt(P.camara.totalEstimado)}. ${P.k ? `Con eso arrastraría ${P.k} curul${P.k === 1 ? '' : 'es'} y entrar de ${P.k} cuesta lo que suele sacar el ${P.k}.º de una lista así.` : `No alcanza la cifra repartidora (${fmt(P.cifra)}): a quien encabece le toca poner la diferencia.`}</li>`;
  const piso = R.tipo === 'partido' ? `<li><b>${fmt(R.piso)}</b> · el <b>piso de la corporación</b>: la última curul ${escHtml(corpConArticulo(d.corporacionClave, d.corporacion, 1))} de ${escHtml(d.territorio)} en 2023${R.curules ? `, con ${R.curules} curules` : ''}. Es lo mínimo con que alguien entró, no lo que cuesta entrar por su lista.</li>` : '';
  const sinPartido = P && P.tipo === 'sin-dato' ? `<p class="puntaje-nota">De ${escHtml(P.nombre)} no hay lista en esta corporación en 2023 ni votación a Cámara en 2026 en este departamento, así que la meta es la de la corporación. Si es una organización nueva, tómela como piso.</p>` : '';
  const puntoDePartida = R.tipo === 'partido' ? porPartido + piso : R.tipo === 'ganadora'
    ? `<li><b>${R.votos.toLocaleString('es-CO')}</b> · lo que sacó <b>quien ganó</b> ${escHtml(corpConArticulo(d.corporacionClave, d.corporacion, 1))} de ${escHtml(d.territorio)} en 2023${R.nombre ? ` (${escHtml(R.nombre)})` : ''}. En un cargo uninominal la meta es ganar, no pasar un corte.</li>`
    : R.tipo === 'curul-verificada'
      ? `<li><b>${R.votos.toLocaleString('es-CO')}</b> · la <b>última curul</b> ${escHtml(corpConArticulo(d.corporacionClave, d.corporacion, 1))} de ${escHtml(d.territorio)} en 2023${R.curules ? `, de ${R.curules} curules` : ''}, tomada del acto de escrutinio.</li>`
      : R.tipo === 'piso-observado'
        ? `<li><b>${R.votos.toLocaleString('es-CO')}</b> · el <b>piso observado</b> entre quienes salieron elegidos en 2023${R.curules ? ` (${R.curules} curules)` : ''}. La fuente no permite reconstruir todas las curules, así que este número es un mínimo, no un corte exacto.</li>`
        : `<li><b>${R.votos.toLocaleString('es-CO')}</b> · el <b>corte de la última curul</b> ${escHtml(corpConArticulo(d.corporacionClave, d.corporacion, 1))} de ${escHtml(d.territorio)} en 2023${R.curules ? `, con ${R.curules} curules` : ''}, reconstruido con umbral y cifra repartidora.</li>`;
  const ajustes = [
    `<li><b>${veces(d.censo.factor)}</b> · censo electoral: ${d.censo.potencial ? `${d.censo.potencial.toLocaleString('es-CO')} personas habilitadas en 2023 y ` : ''}un crecimiento de ${pct(d.censo.crecimiento)} hasta 2027.</li>`,
    d.participacion.p2023
      ? `<li><b>${veces(d.participacion.factor)}</b> · participación: votó el ${pct(d.participacion.p2023)} en 2023 y proyectamos ${pct(d.participacion.p2027)} en 2027 (las locales de mitad de periodo suben poco).</li>`
      : `<li><b>× 1,000</b> · participación: sin dato de censo y votantes para ese territorio la dejamos estable, sin inventar un alza.</li>`,
    `<li><b>${veces(1 + d.margen)}</b> · margen competitivo: ${Math.round(d.margen * 100)} % por encima del corte. Empatar con la última curul no la gana; hay que pasarla.</li>`
  ].join('');
  $('introModalTitle').textContent = `Su meta: ${d.objetivo.toLocaleString('es-CO')} votos`;
  $('introModalText').innerHTML = `
    <p>No es un pronóstico de cuántos votos va a sacar. Es <b>cuántos hacen falta</b>: lo que costó entrar ${escHtml(corpConArticulo(d.corporacionClave, d.corporacion))} de ${escHtml(d.territorio)} en 2023${R.tipo === 'partido' ? ` <b>por la lista de ${escHtml(P.nombre)}</b>` : ''}, puesto en 2027.${R.tipo === 'partido' ? ' No cuesta lo mismo entrar de décimo en una lista grande que arrastrar una lista pequeña.' : ''}</p>
    ${sinPartido}
    <p style="margin-bottom:8px"><b>De dónde parte</b></p>
    <ul class="puntaje-escala">${puntoDePartida}</ul>
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
async function launchCRM(event) {
  event?.preventDefault();
  if (!crmCandidate) return;
  if (!SESSION.acceso) return abrirPaywall();
  const isOther = document.querySelector('input[name="corporationRoute"]:checked')?.value === 'other';
  if (isOther && !$('otherCorporation').value) return irAPaso('corporacion', { animar: true });
  const corpKey = isOther ? $('otherCorporation').value : corporacionHistorica(crmCandidate) || 'concejo';
  const corporation = CRM_CORPORATIONS[corpKey], territory = campaignTerritory(corpKey);
  if (territory === null) { irAPaso('lugar', { animar: true }); $('campaignDepartment').focus({ preventScroll: true }); return; }
  const campana = campanaActual(corpKey);
  if (PRUEBAS) vinculoLocal({ tipo: 'historial', candidato: { id: crmCandidate.id, nombre: crmCandidate.nombre, slugs: (crmCandidate.history?.length ? crmCandidate.history : [crmCandidate]).map(c => c.slug).filter(Boolean), corp: crmCandidate.corp, partido: crmCandidate.partido, circunscripcion: crmCandidate.circunscripcion }, campana });
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
  $('crmVoteNumber').textContent = '…'; $('crmVoteTarget').textContent = 'Calculando objetivo competitivo'; $('crmVoteFormula').textContent = 'Contrastando la corporación y el territorio con la última elección comparable.';
  $('crmMapPanelNum').textContent = '01 · Mapa de historial electoral';
  showScreen('crm');
  pintarBriefing();
  pintarEscucha();
  pintarArquetipos();
  pintarPerfil();
  pintarFirmas();
  loadHistoricalMap(crmCandidate);
  renderCRMProfilePhoto(crmCandidate);
  pintarPuntaje(crmCandidate);
  await prepararSalto(corpKey, campana);
  pintarMeta(await estimateVoteTarget(corpKey, territory));
  if (SALTO_ACTUAL && crmMapMode === 'proyectado') refreshCRMMapMode();
}
/* CRM de una candidatura nueva: sin historial, el punto de partida es el
   territorio al que aspira y la referencia de 2023 de ese territorio. */
async function abrirCRMNuevo() {
  const n = NUEVO; if (!n) return;
  crmCandidate = null;
  const c = n.campana, lugar = [c.localidad, c.municipio, c.departamentoNombre].filter(Boolean).map(NOMBRE_BONITO).join(' · ');
  $('crmBack').textContent = '← Inicio'; $('crmBack').onclick = () => showScreen('intro');
  $('crmInitials').textContent = initials(n.nombre); $('crmName').textContent = n.nombre;
  $('crmTarget').textContent = `Candidatura 2027 · ${CRM_CORPORATIONS[c.corp]} · ${lugar}`;
  $('crmContext').textContent = `Candidatura nueva${n.partido ? ` con ${n.partido}${n.partidoNuevo ? ' (movimiento por constituir)' : ''}` : ''}. Sin historial propio, el punto de partida es el territorio: la referencia son los resultados de 2023 en ${lugar}.${n.objetivo ? ` Primer objetivo: ${n.objetivo.toLowerCase()}.` : ''}${textoRedesCRM(n.redes)}`;
  $('crmVoteNumber').textContent = '…'; $('crmVoteTarget').textContent = 'Calculando objetivo competitivo'; $('crmVoteFormula').textContent = 'Contrastando la corporación y el territorio con la última elección comparable.';
  $('crmMapPanelNum').textContent = '01 · Territorio de campaña';
  document.getElementById('crmProfilePhoto')?.remove(); document.getElementById('crmProfilePhotoMissing')?.remove(); $('crmInitials').classList.remove('crm-avatar-hidden');
  $('crmPuntaje').innerHTML = ''; $('crmPuntaje').classList.add('hidden'); PUNTAJE_ACTUAL = null;   /* sin historial no hay puntaje: un cero ahí sería una calificación, no un dato */
  CAMPANA_ACTUAL = c;
  showScreen('crm');
  pintarBriefing();
  pintarEscucha();
  pintarArquetipos();
  pintarPerfil();
  pintarFirmas();
  renderTerritorioObjetivo(c);
  pintarMeta(await VoteTarget.estimate({ corp: c.corp, territory: lugar, baseUrl: S3, partido: n.partido || '', departamento: c.departamento || '' }));
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
const SALTOS = { 'jal>concejo': 'localidad', 'concejo>asamblea': 'municipio', 'alcaldia>gobernacion': 'municipio', 'concejo>gobernacion': 'municipio', 'alcaldia>asamblea': 'municipio' };
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
    for (const [nombre, n] of (d?.partidos || [])) if (PartidosBloques.bloqueDePartido(nombre) === bloque) v += Number(n) || 0;
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
    const m = mesas?.[0]; if (!m) return null;
    const key = `${String(m.dep || '').padStart(2, '0')}-${String(m.mun || '').padStart(3, '0')}`;
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
    return SALTO_ACTUAL;
  } catch (e) { return null; }
}
/* Texto de la nota del mapa: dice qué capa se usó y de dónde salió el arraigo.
   Sin esto un reparto por bloque se leería como una predicción del partido. */
function notaSalto(base) {
  const s = SALTO_ACTUAL; if (!s || !base) return '';
  const capa = base.capa === 'partido' ? `la huella de ${base.etiqueta} en esa corporación (2023)`
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
  const base = baseDestino({ porArea, partido: partidoVigente(), nombreCandidato: crmCandidate?.nombre, bloqueFirmas: bloqueVigente() });
  if (!base) return null;
  const origen = Object.keys(state.votesByArea || {}).filter(k => Number(state.votesByArea[k] || 0) > 0);
  const reparto = repartoSalto({ meta: goal, propio: state.votesByArea, origen, base, arraigo: s.arraigo });
  if (!reparto) return null;
  s.base = base;
  return reparto;
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
    const origen = Object.keys(nombres).filter(k => k === origenNombre || (origenNombre && k.includes(origenNombre)));
    const propio = Object.fromEntries(origen.map(k => [k, Number(crmCandidate?.votos || 1)]));
    const reparto = repartoSalto({ meta: goal, propio, origen, base, arraigo: s.arraigo });
    if (!reparto) return false;
    s.base = base;
    const max = Math.max(1, ...Object.values(reparto));
    crearMapa([4.6, -74.1], 5); aplicarBasemap(false);
    crmMapLayer = L.geoJSON(geoData, {
      style: f => { const k = normalizedText(nameOf(f)), v = reparto[k] || 0; return { color: '#fff', weight: origen.includes(k) ? 2 : 1, fillColor: MAP_COLOR(v / max), fillOpacity: origen.includes(k) ? .9 : .78 }; },
      onEachFeature: (f, layer) => { const k = normalizedText(nameOf(f)); layer.bindTooltip(`<strong>${NOMBRE_BONITO(nameOf(f))}</strong><br>${(reparto[k] || 0).toLocaleString('es-CO')} votos proyectados`, { sticky: true }); }
    }).addTo(crmLeafletMap);
    encuadrar(crmMapLayer, 24);
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
  if (!crmLeafletMap) { mapEl.innerHTML = ''; crmLeafletMap = L.map(mapEl, { zoomControl: false, attributionControl: true, zoomSnap: 0.1, scrollWheelZoom: false, dragging: false, touchZoom: false, doubleClickZoom: false, boxZoom: false, keyboard: false, tap: false }).setView(center, zoom); }
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
function electoralPlaceCode(mesa) { return `${String(mesa.dep || '').padStart(2, '0')}${String(mesa.mun || '').padStart(3, '0')}${String(mesa.zon || '').padStart(2, '0')}${String(mesa.pue || '').padStart(2, '0')}`; }
let puestosBarrioPromise = null;
async function puestosPorBarrio() {
  /* Columnas: 1 código completo (dep+mun+zon+pue), 7 barrio, 9/10 lat/lng,
     13/14 mujeres/hombres — la suma es el CENSO del puesto, que es lo que
     permite repartir una meta por barrio donde la persona nunca sacó votos. */
  if (!puestosBarrioPromise) puestosBarrioPromise = fetch(`${S3}/mapas-2026/PUESTOS_GEOREF.csv`).then(r => r.ok ? r.text() : Promise.reject()).then(raw => {
    const lookup = {};
    raw.split(/\r?\n/).slice(1).forEach(line => {
      const row = line.split(';'), code = String(row[1] || ''), barrio = row[7];
      if (!code || !barrio) return;
      /* La «mesa» es falsa pero sirve para lo único que importa: pasarla por la
         MISMA función de llave de área que usa el mapa de esa ciudad, sea por
         código de comuna o por nombre. Así no hay una segunda regla que
         mantener sincronizada. */
      const mesa = { dep: code.slice(0, 2), mun: code.slice(2, 5), zon: code.slice(5, 7), pue: code.slice(7, 9), com: String(row[11] || ''), comNom: String(row[12] || '') };
      const mujeres = Number(row[13]) || 0, hombres = Number(row[14]) || 0;
      lookup[code] = { barrio, lat: Number(row[9]), lng: Number(row[10]), censo: mujeres + hombres, mujeres, hombres, mesa };
    });
    return lookup;
  });
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
function projectedVotesByArea() {
  const goal = Number(String($('crmVoteNumber').textContent || '').replace(/\D/g, ''));
  /* Con salto de corporación la meta no puede caer donde cayó el historial:
     se reparte con la huella del destino (sección 8 ter). Si el salto no se
     pudo preparar, se conserva el reparto proporcional de siempre. */
  const salto = crmMapState ? repartoSaltoCiudad(crmMapState, goal) : null;
  return salto || distributeVotes(crmMapState?.votesByArea || {}, goal);
}
function renderMapBreakdown(votesByArea, namesByArea, title) {
  const rows = Object.entries(votesByArea).map(([key, value]) => ({ key, name: namesByArea[key] || key, value: Number(value) || 0 })).filter(row => row.value > 0).sort((a, b) => b.value - a.value), max = Math.max(1, ...rows.map(row => row.value));
  $('crmBreakdown').innerHTML = `<h4 id="crmBreakdownTitle">${title}</h4>` + (rows.length ? rows.map(row => `<button class="crm-breakdown-item" type="button" data-area-key="${escHtml(row.key)}" onclick="openMapAreaFromBreakdown(this.dataset.areaKey)"><span class="crm-breakdown-row"><b>${escHtml(NOMBRE_BONITO(row.name))}</b><span>${row.value.toLocaleString('es-CO')}</span></span><span class="crm-breakdown-bar"><i style="width:${Math.max(3, Math.round(row.value / max * 100))}%"></i></span></button>`).join('') : '<p class="helper">No hay votos desagregados disponibles.</p>');
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
  const donde = state.tituloLugar || '';
  return modo === 'proyectado' ? `¿Dónde debería estar su votación${donde ? ` en ${donde}` : ''}?` : `¿Dónde estuvo su votación${donde ? ` en ${donde}` : ''}?`;
}
function refreshCRMMapMode() {
  const state = crmMapState; if (!state || !crmMapLayer) return;
  if (state.tituloLugar) $('crmMapTitle').textContent = tituloMapa();
  /* Salto a escala de departamento: «Proyectado» pinta los municipios del
     destino; «Total» devuelve el mapa histórico de la ciudad. */
  if (SALTO_ACTUAL?.tipo.unidad === 'municipio') {
    const goal = Number(String($('crmVoteNumber').textContent || '').replace(/\D/g, ''));
    document.querySelectorAll('#crmMapToggles .map-toggle[data-mode]').forEach(b => b.classList.toggle('active', b.dataset.mode === crmMapMode));
    if (crmMapMode === 'proyectado') { pintarProyeccionDepartamental(goal); return; }
    if (state.geometriaDestino) { loadHistoricalMap(crmCandidate); return; }
  }
  const projected = projectedVotesByArea(), values = crmMapMode === 'proyectado' ? projected : state.votesByArea, max = Math.max(1, ...Object.values(values));
  renderMapBreakdown(values, state.namesByArea, crmMapMode === 'proyectado' ? `Meta proyectada por ${state.config.title}` : `Votos por ${state.config.title}`);
  document.querySelectorAll('#crmMapToggles .map-toggle[data-mode]').forEach(b => b.classList.toggle('active', b.dataset.mode === crmMapMode));
  crmMapLayer.eachLayer(layer => {
    const key = state.config.code(layer.feature.properties), observed = Number(state.votesByArea[key] || 0), proj = Number(projected[key] || 0), value = Number(values[key] || 0);
    layer.setStyle({ fillColor: MAP_COLOR(value / max), fillOpacity: key === state.targetKey ? .78 : .38 });
    layer.bindTooltip(`<strong>${NOMBRE_BONITO(state.config.name(layer.feature.properties))}</strong><br>${(crmMapMode === 'proyectado' ? proj : observed).toLocaleString('es-CO')} ${crmMapMode === 'proyectado' ? 'votos proyectados' : 'votos'}`, { sticky: true });
  });
  $('crmMapNote').textContent = (crmMapMode === 'proyectado' ? (SALTO_ACTUAL?.base ? notaSalto(SALTO_ACTUAL.base) + ` Haga clic en una ${state.config.title} para ver su detalle.` : `Meta total distribuida proporcionalmente a la votación histórica. Haga clic en una ${state.config.title} para ver su detalle.`) : `Votación total histórica. Haga clic en una ${state.config.title} para ver el detalle y su meta proyectada.`) + notaRecorte();
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
  return recorte?.alcance?.tipo === 'municipio' ? ($('campaignMunicipality').value || 'el municipio') : ($('campaignDepartment').options[$('campaignDepartment').selectedIndex]?.text || 'el departamento');
}
function notaRecorte(recorte = recorteActivo) {
  if (!recorte || !recorte.mesasFuera) return '';
  const donde = lugarDelAlcance(recorte);
  if (recorte.sinVotos) return ` Su votación histórica no tiene mesas en ${donde}, así que el mapa la muestra donde estuvo; la campaña nueva se ubica en ${donde}.`;
  return ` Se muestran solo los votos en ${donde}: quedaron por fuera ${recorte.votosFuera.toLocaleString('es-CO')} votos en ${recorte.mesasFuera.toLocaleString('es-CO')} mesas de otros territorios, que no cuentan para esta candidatura.`;
}
/* ¿El historial tiene votos dentro del territorio objetivo? Decide si el
   mapa va por el territorio nuevo (Bogotá, Cali) o por donde estuvo la votación. */
async function historialEnObjetivo(candidate) {
  try { return !(await datosCandidatura(candidate)).recorte?.sinVotos; } catch (e) { return true; }
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
  crmMapLayer = L.geoJSON(geoData, { style: f => ({ color: '#fff', weight: 1, fillColor: MAP_COLOR((votesByArea[featureCode(f.properties)] || 0) / max), fillOpacity: .94 }), onEachFeature: (f, layer) => layer.bindTooltip(`<strong>${NOMBRE_BONITO(featureName(f.properties))}</strong><br>${(votesByArea[featureCode(f.properties)] || 0).toLocaleString('es-CO')} votos`, { sticky: true }) }).addTo(crmLeafletMap);
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
const BOGOTA_VENTANA_URBANA = { sur: 4.49, norte: 4.837, oeste: -74.224, este: -73.987 };
function encuadreBogota() {
  const { sur, norte, oeste, este } = BOGOTA_VENTANA_URBANA;
  const esquinas = [[oeste, sur], [este, sur], [oeste, norte], [este, norte]].map(c => rotateGeoJSON90Left({ features: [{ geometry: { type: 'Polygon', coordinates: [[c]] } }] }).features[0].geometry.coordinates[0][0]);
  return L.latLngBounds(esquinas.map(([lon, lat]) => [lat, lon]));
}
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
function cityLayerFor(nombre) { const city = normalizedText(nombre); return CITY_JAL_LAYERS.find(item => item.match.some(name => city.includes(name))) || null; }
/* Pinta una ciudad por comuna/localidad con el estado compartido de los mapas
   de ciudad (toggles, detalle por barrio, niveles). */
function pintarCiudad({ geoData, config, mesas, total, votesByArea, namesByArea, targetKey, city, rotate, lugar, title, note, center, zoom, fitTarget, fueraDelEncuadre, encuadre }) {
  completaNombres(geoData, config.code, config.name, namesByArea);
  const max = Math.max(1, ...Object.values(votesByArea));
  crmMapMode = 'total';
  const m0 = mesas[0] || {};
  fijarRampaMapa(partidoVigente(), crmCandidate?.nombre);
  crmMapState = { city, ciudad: `${String(m0.dep || '').padStart(2, '0')}${String(m0.mun || '').padStart(3, '0')}`, config, geoData, votesByArea, namesByArea, mesas, total, max, targetKey, focusKey: null, rotado: Boolean(rotate), tituloLugar: lugar || '', encuadre: encuadre || null, fueraDelEncuadre: fueraDelEncuadre || null };
  $('crmMapTitle').textContent = lugar ? tituloMapa('total') : title; ensureCRMMapToggles();
  crearMapa(center || [4.6, -74.1], zoom || 5); aplicarBasemap(Boolean(rotate));
  let targetLayer = null;
  crmMapLayer = L.geoJSON(geoData, {
    style: f => { const key = config.code(f.properties); return { color: '#fff', weight: key === targetKey ? 2 : 1, fillColor: MAP_COLOR((votesByArea[key] || 0) / max), fillOpacity: key === targetKey ? .78 : .42 }; },
    onEachFeature: (f, layer) => { if (config.code(f.properties) === targetKey) targetLayer = layer; layer.on('click', () => showCRMMapDetail(layer)); }
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
  const config = cityLayerFor(mesas.find(m => m.munNom)?.munNom || candidate.circunscripcion);
  return config ? { config, mesas } : null;
}
async function renderCiudadMap(candidate, ciudad) {
  const { config, mesas } = ciudad || await ciudadDeLaCandidatura(candidate) || {};
  if (!config) throw new Error('Ciudad sin capa local');
  let geoData = await fetchJSON(`${S3}/mapas-2026/Ciudades-COM-LOC/${config.path}`); if (config.rotate) geoData = rotateGeoJSON90Left(geoData);
  const { votesByArea, namesByArea } = agregarPorArea(mesas, m => config.mesaKey ? config.mesaKey(m) : claveLocal(m));
  /* La Registraduría escribe la comuna como «06COMUNA 6 DOCE DE OCTUBRE»: el
     código pegado al nombre. En el desglose sobra. */
  Object.keys(namesByArea).forEach(k => { if (namesByArea[k]) namesByArea[k] = String(namesByArea[k]).replace(/^\d+\s*/, ''); else delete namesByArea[k]; });
  const total = mesas.reduce((sum, m) => sum + Number(m.v || 0), 0) || Number(candidate.votos) || 0, targetKey = Object.entries(votesByArea).sort((a, b) => b[1] - a[1])[0]?.[0];
  const esJal = String(candidate.corp || '').toUpperCase().startsWith('JAL'), lugar = mesas.find(m => m.munNom)?.munNom || '';
  pintarCiudad({ geoData, config, mesas, total, votesByArea, namesByArea, targetKey, city: normalizedText(lugar), rotate: config.rotate, lugar,
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
  crmMapMode = 'total';
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
let bogotaPuestoBarrioPromise = null, caliPuestoBarrioPromise = null;
const bogotaBarriosPorLocalidad = new Map(), caliBarriosPorComuna = new Map();
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
async function caliBarrios(comunaCode) {
  const key = String(comunaCode || '').padStart(2, '0');
  if (!caliPuestoBarrioPromise) caliPuestoBarrioPromise = window.Candidato360CaliPuestoBarrio ? Promise.resolve(window.Candidato360CaliPuestoBarrio) : loadCandidateMapScript('candidato-360-data/cali-puesto-barrio.js').then(() => window.Candidato360CaliPuestoBarrio);
  if (!caliBarriosPorComuna.has(key)) caliBarriosPorComuna.set(key, (window.Candidato360CaliBarrios?.[key] ? Promise.resolve() : loadCandidateMapScript(`candidato-360-data/cali-barrios/${key}.js`)).then(() => { const geo = window.Candidato360CaliBarrios?.[key]; if (!geo) throw new Error(`Sin cartografía barrial para la comuna ${key}`); return geo; }));
  return Promise.all([caliPuestoBarrioPromise, caliBarriosPorComuna.get(key)]);
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
function pintarBarrios(geo, values, codeOf, nameOf, nota) {
  if (crmBarrioLayer) crmLeafletMap.removeLayer(crmBarrioLayer);
  ponerBasemap('crm-basemap-tenue');
  if (crmMapLayer && crmMapState?.rotado) crmLeafletMap.removeLayer(crmMapLayer);   /* se saca del mapa, no del grupo: sus capas siguen ahí */
  const max = Math.max(1, ...Object.values(values));
  crmBarrioLayer = L.geoJSON(geo, {
    style: f => { const votes = values[codeOf(f)] || 0; return { fillColor: MAP_COLOR(votes / max), fillOpacity: votes ? .62 : .12, color: 'rgba(16,34,56,.55)', weight: .7 }; },
    onEachFeature: (f, layer) => { const votes = Number(values[codeOf(f)] || 0); layer.bindTooltip(`<strong>${NOMBRE_BONITO(nameOf(f))}</strong><br>${votes.toLocaleString('es-CO')} ${crmMapMode === 'proyectado' ? 'votos proyectados' : 'votos'}`, { sticky: true }); layer.on('mouseover', () => layer.setStyle({ weight: 1.5, color: '#fff' })); layer.on('mouseout', () => crmBarrioLayer.resetStyle(layer)); }
  }).addTo(crmLeafletMap);
  encuadrar(crmBarrioLayer, 20);
  $('crmMapNote').innerHTML = nota;
}
/* ── La meta a escala de barrio ──────────────────────────────────────────────
   Repartir la meta de una localidad entre sus barrios necesita un peso. Si la
   persona ya sacó votos ahí, el peso es su propia huella: es lo más suyo que
   hay. Si no —una localidad que nunca disputó, o un salto de corporación que
   le manda meta a media ciudad—, el peso es el CENSO ELECTORAL de cada barrio.
   No dice dónde la quieren; dice dónde hay gente que vota, que es la única
   pregunta que los datos pueden contestar ahí. La nota del mapa lo aclara,
   porque un mapa de censo leído como un mapa de apoyo miente. */
async function censoBarrialBogota(localidad, puestoBarrio, code6) {
  const places = await puestosPorBarrio(), out = {};
  Object.entries(puestoBarrio || {}).forEach(([zonaPuesto, barrio]) => {
    if (!String(zonaPuesto).startsWith(`${localidad}-`)) return;
    const censo = places[`16001${String(zonaPuesto).replace('-', '')}`]?.censo || 0;
    if (censo) out[code6(barrio)] = (out[code6(barrio)] || 0) + censo;
  });
  return out;
}
async function censoBarrialCali(comuna, puestoBarrio) {
  const places = await puestosPorBarrio(), out = {}, c = String(comuna).padStart(2, '0');
  Object.entries(puestoBarrio || {}).forEach(([code, info]) => {
    if (String(info?.comuna || '').padStart(2, '0') !== c || !info?.barrio) return;
    const censo = places[code]?.censo || 0;
    if (censo) out[info.barrio] = (out[info.barrio] || 0) + censo;
  });
  return out;
}
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
  return crmMapMode !== 'proyectado' ? 'Votos totales por barrio'
    : base === 'censo' ? 'Meta proyectada por barrio · censo' : 'Meta proyectada por barrio';
}
function notaBarrial(donde, base) {
  const cabeza = `Detalle poligonal por barrio de ${donde}.`;
  if (crmMapMode !== 'proyectado') return cabeza;
  if (base === 'censo') return `${cabeza} Usted no tuvo votos acá, así que la meta se reparte por el <b>censo electoral</b> de cada barrio: dice dónde hay gente que vota, no dónde ya votaron por usted.`;
  if (base === 'historial') return `${cabeza} La meta de esta zona se reparte en la misma proporción en que ya votaron por usted, barrio por barrio.`;
  if (base === 'sin-meta') return `${cabeza} Esta zona no recibe meta en la proyección.`;
  return `${cabeza} No se pudo repartir la meta por barrio: el censo por puesto de votación no respondió.`;
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
      const { values, base } = await valoresBarriales(historical, localGoal, () => censoBarrialCali(key, puestoBarrio));
      renderMapBreakdown(values, Object.fromEntries(geo.features.map(f => [f.properties.barrio, f.properties.barrio])), tituloBarrial(base));
      return pintarBarrios(geo, values, f => f.properties.barrio, f => f.properties.barrio, notaBarrial(state.namesByArea[key] || `la comuna ${key}`, base));
    } catch (e) { $('crmBreakdown').innerHTML = '<h4>Votos por barrio</h4><p class="helper">No fue posible cargar los polígonos barriales de esta comuna.</p>'; return; }
  }
  /* Bogotá se reconoce por la capa que está pintada, no por las mesas: con un
     salto de corporación la meta cae en localidades donde la persona nunca
     tuvo una mesa, y mirar las mesas mandaba esas localidades al camino
     genérico de puestos de votación. */
  if (String(state.city || '').startsWith('BOGOTA') || state.mesas.some(m => String(m.dep) === '16')) {
    try {
      const [puestoBarrio, geo] = await bogotaBarrios(key), historical = {}, code6 = v => String(v).padStart(6, '0');
      mesas.forEach(m => { const barrio = puestoBarrio[`${String(m.zon || '').padStart(2, '0')}-${String(m.pue || '').padStart(2, '0')}`]; if (barrio) historical[code6(barrio)] = (historical[code6(barrio)] || 0) + Number(m.v || 0); });
      const { values, base } = await valoresBarriales(historical, localGoal, () => censoBarrialBogota(key, puestoBarrio, code6));
      renderMapBreakdown(values, Object.fromEntries(geo.features.map(f => [code6(f.properties.codigo), f.properties.nombre])), tituloBarrial(base));
      return pintarBarrios(geo, values, f => code6(f.properties.codigo), f => f.properties.nombre, notaBarrial(geo.features[0]?.properties.loc_nombre || 'la localidad', base));
    } catch (e) { /* sin polígono → puestos */ }
  }
  /* Las demás ciudades con cartografía barrial: el puesto se ubica por
     coordenada dentro del polígono, y se dibujan solo los barrios de la
     comuna que se abrió. */
  const capaBarrios = cityBarrioLayerFor(state.city);
  if (capaBarrios) {
    try {
      const [{ geo, indice }, places] = await Promise.all([cargarBarriosCiudad(capaBarrios), puestosPorBarrio()]);
      const llaveDe = m => (state.config.mesaKey ? state.config.mesaKey(m) : claveLocal(m));
      const ciudad = state.ciudad || `${String(state.mesas[0]?.dep || '').padStart(2, '0')}${String(state.mesas[0]?.mun || '').padStart(3, '0')}`;
      /* Todos los puestos de esa comuna, tenga o no votos ahí: los suyos dan el
         mapa de votación y el resto da el censo con el que se reparte la meta. */
      const deLaComuna = Object.entries(places).filter(([code, p]) => code.startsWith(ciudad) && p.mesa && llaveDe(p.mesa) === key);
      const barrioPorPuesto = new Map(deLaComuna.map(([code, p]) => [code, barrioDelPunto(indice, p.lng, p.lat)]));
      const dentro = new Set([...barrioPorPuesto.values()].filter(Boolean));
      if (dentro.size) {
        const historical = {};
        mesas.forEach(m => { const b = barrioPorPuesto.get(electoralPlaceCode(m)); if (b) historical[b] = (historical[b] || 0) + Number(m.v || 0); });
        const censoDe = () => { const out = {}; for (const [code, p] of deLaComuna) { const b = barrioPorPuesto.get(code); if (b && p.censo) out[b] = (out[b] || 0) + p.censo; } return out; };
        const { values, base } = await valoresBarriales(historical, localGoal, censoDe);
        const recorte = { type: 'FeatureCollection', features: geo.features.filter(f => dentro.has(capaBarrios.code(f.properties))) };
        const nombres = Object.fromEntries(recorte.features.map(f => [capaBarrios.code(f.properties), capaBarrios.name(f.properties)]));
        renderMapBreakdown(values, nombres, tituloBarrial(base));
        return pintarBarrios(recorte, values, f => capaBarrios.code(f.properties), f => capaBarrios.name(f.properties), notaBarrial(state.namesByArea[key] || `la ${state.config.title} ${key}`, base) + (capaBarrios.aviso ? ` ${capaBarrios.aviso}` : ''));
      }
    } catch (e) { /* sin cartografía barrial → puestos */ }
  }
  const layer = crmMapLayer?.getLayers().find(item => state.config.code(item.feature.properties) === key);
  return pintarPuestos(mesas, layer ? state.config.name(layer.feature.properties) : `la ${state.config.title}`, localGoal);
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
  if (crmMapLayer && crmMapState?.rotado) crmLeafletMap.removeLayer(crmMapLayer);
  /* El tamaño del punto lleva la magnitud, no solo el color: sobre el
     callejero un círculo pequeño y claro se pierde. */
  crmBarrioLayer = L.featureGroup(Object.entries(points).map(([name, point]) => {
    const v = Number(values[name] || 0);
    return L.circleMarker([point.lat, point.lng], { radius: 5 + Math.round(9 * Math.sqrt(v / max)), color: '#fff', weight: 1.2, fillColor: MAP_COLOR(v / max), fillOpacity: .92 })
      .bindTooltip(`<strong>${escHtml(name)}</strong><br>${v.toLocaleString('es-CO')} ${proyectando ? 'votos proyectados' : censo ? 'personas habilitadas' : 'votos'}`, { sticky: true });
  })).addTo(crmLeafletMap);
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
/* ¿Esta ciudad tiene cartografía barrial? Bogotá y Cali la traen curada; el
   resto, en CITY_BARRIO_LAYERS. Donde no hay, el último nivel no puede
   llamarse «Barrio»: son puestos de votación, y decirlo evita prometer un
   detalle que no existe. */
function ciudadTieneBarrios(state) {
  const city = String(state?.city || '');
  return city.startsWith('BOGOTA') || city === 'CALI' || Boolean(cityBarrioLayerFor(city));
}
/* Niveles para un municipio sin comunas: no hay barrio que abrir, pero sí
   puestos. Lo que se ve en La Ceja, en Sabaneta, en el 90 % del país. */
function nivelesMunicipio() {
  const mapEl = $('crmMap'); if (!mapEl || !MAPA_MUNICIPAL || !crmMapLayer) return;
  const controls = document.createElement('div'); controls.className = 'crm-map-levels';
  controls.innerHTML = '<button type="button" class="crm-map-level active" data-level="municipio">Municipio</button><button type="button" class="crm-map-level" data-level="puestos">Puestos</button>';
  mapEl.append(controls);
  const marcar = level => controls.querySelectorAll('[data-level]').forEach(b => b.classList.toggle('active', b.dataset.level === level));
  controls.querySelector('[data-level="municipio"]').addEventListener('click', () => {
    if (crmBarrioLayer) { crmLeafletMap.removeLayer(crmBarrioLayer); crmBarrioLayer = null; }
    aplicarBasemap(false); crmMapLayer.setStyle({ fillOpacity: .94 });
    encuadrar(crmMapLayer, 15);
    $('crmMapNote').textContent = (MAPA_MUNICIPAL.censo
      ? `${MAPA_MUNICIPAL.nombre} es el territorio de su candidatura. Abra «Puestos» para ver dónde vota la gente, puesto por puesto.`
      : `Votación histórica concentrada en ${MAPA_MUNICIPAL.nombre}. Abra «Puestos» para ver dónde está, puesto por puesto.`) + notaColorPartido();
    marcar('municipio');
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
  const localLabel = state.config.title === 'comuna' ? 'Comuna' : 'Localidad';
  const detalle = ciudadTieneBarrios(state) ? 'Barrio' : 'Puestos';
  /* Sin «Municipio»: cuando el mapa ES la ciudad, ese botón mostraba lo mismo
     que «Comuna» —la ciudad entera dividida— y dejaba la alcaldía de Medellín
     abriendo en un nivel que no existe. Los niveles son los que de verdad
     cambian el dibujo. */
  const controls = document.createElement('div'); controls.className = 'crm-map-levels';
  controls.innerHTML = `<button type="button" class="crm-map-level" data-level="localidad">${localLabel}</button><button type="button" class="crm-map-level" data-level="barrio" disabled>${detalle}</button>`;
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
  controls.querySelector('[data-level="localidad"]').addEventListener('click', () => volver('localidad'));
  controls.querySelector('[data-level="barrio"]').addEventListener('click', () => { if (crmMapState?.focusKey) { renderBarriosForArea(crmMapState.focusKey); setMapLevel('barrio'); } });
  setMapLevel(state.focusKey ? 'barrio' : 'localidad');
}
/* Punto de entrada del mapa histórico. */
/* Si la campaña se muda a un territorio donde su historial no tiene un solo
   voto —de la JAL de Teusaquillo al Concejo de Leticia—, el mapa de su
   votación anterior no informa nada sobre la nueva: lo útil es ver el
   territorio al que aspira, con sus puestos. */
async function loadHistoricalMap(candidate) {
  electionViewRecords = []; electionViewSnapshots = new Map(); electionViewActive = ''; $('crmMapToggles')?.remove(); crmMapState = null; recorteActivo = null;
  /* Con la campaña mudada a otro territorio, las vistas por año sobran: todas
     muestran votaciones que no cuentan donde ahora compite. */
  if (alcanceObjetivo() && !(await historialEnObjetivo(candidate))) { await renderTerritorioDeCampana(); return; }
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
  const corp = $('otherCorporation').value || CAMPANA_ACTUAL?.corp || corporacionHistorica(crmCandidate) || 'concejo';
  const c = alcanceObjetivo() ? campanaActual(corp) : (CAMPANA_ACTUAL || campanaActual(corp));
  $('crmMapPanelNum').textContent = '01 · Mapa del territorio de campaña';
  /* Los niveles del mapa anterior no sirven acá hasta saber si hay puestos. */
  $('crmMap')?.querySelector('.crm-map-levels')?.remove();
  await renderTerritorioObjetivo(c);
  MAPA_MUNICIPAL = null;
  if (!CORP_MUNICIPAL.includes(c.corp) || !c.municipio) return;
  try {
    const codigo = codigoMunicipioObjetivo(); if (!codigo) return;
    const puestos = await puestosPorBarrio(), prefijo = `${String(c.departamento || '').padStart(2, '0')}${String(codigo).padStart(3, '0')}`;
    const mesas = Object.entries(puestos).filter(([code]) => code.slice(0, 5) === prefijo)
      .map(([code, p]) => ({ dep: code.slice(0, 2), mun: code.slice(2, 5), zon: code.slice(5, 7), pue: code.slice(7, 9), pueNom: p.barrio, v: p.censo }));
    if (mesas.length) { MAPA_MUNICIPAL = { mesas, nombre: c.municipio, censo: true }; refreshMapLevels(); }
  } catch (e) { /* sin puestos, queda el polígono del municipio */ }
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
    } else if (CORP_MUNICIPAL.includes(c.corp) && c.corp === 'jal' && cityLayerFor(c.municipio)) {
      const cfg = cityLayerFor(c.municipio); let src = await fetchJSON(`${S3}/mapas-2026/Ciudades-COM-LOC/${cfg.path}`); if (cfg.rotate) { src = rotateGeoJSON90Left(src); rotate = true; }
      geoData = src; unidad = cfg.title; nameOf = f => cfg.name(f.properties); isTarget = f => { const n = normalizedText(cfg.name(f.properties)), corto = normalizedText(cortoLocal(c.localidad)); return n === loc || (corto && (n === corto || n.includes(corto) || corto.includes(n))); };
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
  } catch (e) {
    $('crmMap').innerHTML = '<div style="padding:28px;color:#667068">No fue posible cargar el territorio en este momento.</div>'; crmLeafletMap = null; crmMapLayer = null; crmTileLayer = null;
    $('crmBreakdown').innerHTML = '<p class="helper">No fue posible cargar el territorio.</p>'; $('crmMapNote').textContent = 'La fuente cartográfica no respondió.';
  }
}

/* ─── 9 bis. El territorio por dentro: arquetipos y perfil del votante ───────
   Dos lecturas del mismo territorio que el mapa no da, las dos ponderadas por
   SU votación —no «cómo es la ciudad» sino «cómo es el pedazo de ciudad donde
   están sus votos»:

   · ARQUETIPOS (hoy solo Medellín). El Proyecto DC reconstruyó barrio por
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
const ARQ_BASE = RRData.publicUrl('bases+de+datos/Proyecto+DC/arquetipos');
const VOT27_URL = `${RRData.publicUrl('bases+de+datos/Proyecto+DC/votacion-arquetipo-2027')}/votacion-2027.json?v=20260528`;
const MEDELLIN = '01001';
/* Una candidatura nueva no tiene archivo de mesas y no por eso se rompen las
   tarjetas: se leen con cero votos y cada una decide qué mostrar. */
async function mesasDelHistorial() { try { return (await datosCandidatura(crmCandidate)).mesas || []; } catch (e) { return []; } }
const codigoMunicipio = mesa => `${String(mesa.dep || '').padStart(2, '0')}${String(mesa.mun || '').padStart(3, '0')}`;
function municipioDeCampana() {
  const a = alcanceObjetivo();
  return a?.tipo === 'municipio' && a.municipio ? `${String(a.departamento).padStart(2, '0')}${String(a.municipio).padStart(3, '0')}` : '';
}
function municipioMayoritario(mesas) {
  const votos = {};
  (mesas || []).forEach(m => { const k = codigoMunicipio(m); if (k !== '00000') votos[k] = (votos[k] || 0) + Number(m.v || 0); });
  return Object.entries(votos).sort((a, b) => b[1] - a[1])[0]?.[0] || '';
}
/* Los archivos del Proyecto DC (≈ 560 KB) se piden UNA vez y solo si la
   candidatura toca Medellín. votacion-2027 trae el arquetipo ajustado a mano
   por la socia: se aplica igual que en proyecto-dc/arquetipos.html para que
   las dos páginas no digan cosas distintas del mismo barrio. */
let arqPromise = null;
function datosArquetipos() {
  if (!arqPromise) arqPromise = Promise.all([
    fetchJSON(`${ARQ_BASE}/arquetipos.json`),
    fetchJSON(`${ARQ_BASE}/por-barrio.json`),
    fetchJSON(`${ARQ_BASE}/por-comuna.json`),
    fetchJSON(VOT27_URL).catch(() => null)
  ]).then(([familias, barrios, comunas, vot27]) => {
    Object.entries(vot27?.barrios || {}).forEach(([dap, v]) => {
      const b = barrios[dap]; if (!b || !v.arquetipo_ajustado_2027) return;
      b.proyeccion_2027 = { ...(b.proyeccion_2027 || {}), arquetipo_proy: v.arquetipo_ajustado_2027, arquetipo_alt: v.arquetipo_alterno_2027 || b.proyeccion_2027?.arquetipo_alt };
    });
    return { familias, barrios, comunas };
  }).catch(e => { arqPromise = null; throw e; });
  return arqPromise;
}
/* Votos de la candidatura repartidos por barrio (DAP) y por comuna de
   Medellín. El puesto se ubica por coordenada en la capa barrial oficial —la
   misma regla del mapa— y la comuna sale del propio polígono, no del nombre
   que trae la mesa: «11COMUNA 11 LAURELES» contra «Laureles Estadio» no casa
   por texto y sí por geometría. */
async function votosArquetipoMedellin(mesas) {
  const cfg = cityBarrioLayerFor('MEDELLIN');
  const [capa, puestos] = await Promise.all([cargarBarriosCiudad(cfg), puestosPorBarrio()]);
  const comunaDe = {};
  (capa.geo.features || []).forEach(f => { const c = String(f.properties?.CODIGO || ''); if (c && f.properties?.COMUNA) comunaDe[c.slice(0, 2)] = f.properties.COMUNA; });
  const porBarrio = {}, porComuna = {};
  let votos = 0, ubicados = 0;
  mesas.forEach(m => {
    const v = Number(m.v || 0); if (!v || codigoMunicipio(m) !== MEDELLIN) return;
    votos += v;
    const p = puestos[electoralPlaceCode(m)]; if (!p) return;
    const dap = barrioDelPunto(capa.indice, p.lng, p.lat); if (!dap) return;
    ubicados += v;
    porBarrio[dap] = (porBarrio[dap] || 0) + v;
    const comuna = comunaDe[dap.slice(0, 2)]; if (comuna) porComuna[comuna] = (porComuna[comuna] || 0) + v;
  });
  return { porBarrio, porComuna, votos, ubicados };
}
/* La lectura completa: reparto de SUS votos por arquetipo en 2023 y en 2027,
   comunas y barrios ordenados. Sin votos propios en la ciudad (una campaña
   nueva en Medellín) se describe la ciudad con los votos de 2023 del propio
   estudio, y la tarjeta lo dice. */
async function lecturaArquetipos() {
  const mesas = await mesasDelHistorial();
  const { familias, barrios, comunas } = await datosArquetipos();
  const propio = await votosArquetipoMedellin(mesas);
  const conVotos = propio.ubicados > 0;
  const pesos = conVotos ? propio.porBarrio : Object.fromEntries(Object.values(barrios).map(b => [b.dap, Number(b.proyeccion_2027?.votos_por_arquetipo ? Object.values(b.proyeccion_2027.votos_por_arquetipo).reduce((s, x) => s + Number(x || 0), 0) : 0)]));
  const reparto = { '2023': {}, '2027': {} };
  let total = 0, sinDato = 0;
  Object.entries(pesos).forEach(([dap, v]) => {
    if (!v) return; total += v;
    const b = barrios[dap];
    if (!b) { sinDato += v; return; }
    const a23 = b.arquetipo?.['2023'], a27 = b.proyeccion_2027?.arquetipo_proy;
    if (a23) reparto['2023'][a23] = (reparto['2023'][a23] || 0) + v;
    if (a27) reparto['2027'][a27] = (reparto['2027'][a27] || 0) + v;
  });
  const orden = obj => Object.entries(obj).sort((a, b) => b[1] - a[1]);
  const filasComuna = conVotos
    ? orden(propio.porComuna).map(([nombre, v]) => ({ nombre, votos: v, a23: comunas[nombre]?.['2023']?.dominante, a27: comunas[nombre]?.['2027']?.dominante }))
    : Object.entries(comunas).map(([nombre, c]) => ({ nombre, votos: Number(c['2023']?.votos_total || 0), a23: c['2023']?.dominante, a27: c['2027']?.dominante })).sort((a, b) => b.votos - a.votos);
  const filasBarrio = orden(pesos).slice(0, 10).map(([dap, v]) => ({ dap, votos: v, nombre: barrios[dap]?.barrio || dap, comuna: barrios[dap]?.comuna || '', a23: barrios[dap]?.arquetipo?.['2023'], a27: barrios[dap]?.proyeccion_2027?.arquetipo_proy, riesgo: barrios[dap]?.proyeccion_2027?.nivel_riesgo }));
  return { familias, conVotos, total, sinDato, reparto, filasComuna, filasBarrio, votosCiudad: propio.votos, ubicados: propio.ubicados };
}
function nombreArquetipo(familias, id, año) {
  const f = familias?.arquetipos?.[id]; if (!f) return 'Sin dato';
  return año === '2027' ? f.evol.nombre : f.base.nombre;
}
function colorArquetipo(familias, id) { return familias?.arquetipos?.[id]?.color || '#6b7280'; }
let ARQUETIPOS_ACTUAL = null;
/* La tarjeta: titular con el arquetipo donde está la mayoría de sus votos. */
async function pintarArquetipos() {
  const card = $('crmArquetipos'); if (!card) return;
  ARQUETIPOS_ACTUAL = null;
  const mesas = await mesasDelHistorial();
  const enMedellin = municipioDeCampana() === MEDELLIN || municipioMayoritario(mesas) === MEDELLIN;
  $('crmArqBtn').disabled = true;
  if (!enMedellin) {
    card.classList.add('module-apagado');
    $('crmArqTitulo').textContent = 'Por ahora, solo Medellín.';
    $('crmArqCopy').textContent = 'La cartografía emocional —qué mueve el voto en cada barrio— está reconstruida para los 152 barrios de Medellín con las elecciones de 2015, 2019 y 2023. Cuando exista para su ciudad, esta tarjeta se enciende sola.';
    $('crmArqDato').textContent = '—'; $('crmArqSub').textContent = 'sin cartografía emocional acá';
    return;
  }
  card.classList.remove('module-apagado');
  $('crmArqTitulo').textContent = 'Leyendo los barrios de Medellín…';
  $('crmArqCopy').textContent = 'Cruzando su votación con los cinco arquetipos del territorio.';
  try {
    const L = await lecturaArquetipos();
    ARQUETIPOS_ACTUAL = L;
    const top = Object.entries(L.reparto['2023']).sort((a, b) => b[1] - a[1])[0];
    if (!top) throw new Error('sin cruce');
    const [fam, votos] = top, pct = Math.round(votos / L.total * 100);
    const base = L.familias.arquetipos[fam].base;
    $('crmArqTitulo').textContent = L.conVotos ? `Su voto vive en barrios de ${base.nombre.toLowerCase()}.` : `Medellín vota desde ${base.nombre.toLowerCase()}.`;
    $('crmArqCopy').textContent = `${base.deseo} ${L.conVotos ? `Es el arquetipo de ${pct} % de sus votos en la ciudad, repartidos en ${L.filasComuna.length} comunas.` : `Es el arquetipo dominante de la ciudad; cuando tenga votos propios acá la lectura se hace con ellos.`}`;
    $('crmArqDato').textContent = `${pct} %`;
    $('crmArqSub').textContent = L.conVotos ? 'de sus votos, en ese arquetipo' : 'del voto de la ciudad';
    $('crmArqBtn').disabled = false;
  } catch (e) {
    $('crmArqTitulo').textContent = 'No pudimos leer los arquetipos.';
    $('crmArqCopy').textContent = 'La fuente del Proyecto DC no respondió. Vuelva a abrir el CRM en un momento.';
    $('crmArqDato').textContent = '—'; $('crmArqSub').textContent = 'fuente no disponible';
  }
}
function barraArquetipos(L, año) {
  const filas = Object.entries(L.reparto[año]).sort((a, b) => b[1] - a[1]);
  if (!filas.length) return '';
  return `<div class="arq-barra">${filas.map(([id, v]) => `<i style="flex:${v};background:${colorArquetipo(L.familias, id)}" title="${escHtml(nombreArquetipo(L.familias, id, año))}"></i>`).join('')}</div>
    <ul class="arq-lista">${filas.map(([id, v]) => `<li><span class="arq-punto" style="background:${colorArquetipo(L.familias, id)}"></span><b>${Math.round(v / L.total * 100)} %</b> ${escHtml(nombreArquetipo(L.familias, id, año))}<em>${Math.round(v).toLocaleString('es-CO')} votos</em></li>`).join('')}</ul>`;
}
function mostrarArquetipos() {
  const L = ARQUETIPOS_ACTUAL; if (!L) return;
  const fam = id => escHtml(L.familias.arquetipos[id]?.label_corto || 'Sin dato');
  $('introModalKicker').textContent = 'Candidato 360 · arquetipos del territorio';
  $('introModalTitle').textContent = L.conVotos ? '¿En qué clase de barrio está su voto?' : 'Los arquetipos de Medellín';
  $('introModalText').innerHTML = `
    <p>Cada barrio de Medellín tiene un <b>arquetipo</b>: la emoción que ordena su voto, reconstruida con Alcaldía, Concejo y JAL de 2015, 2019 y 2023. ${L.conVotos ? `Acá están sus <b>${Math.round(L.total).toLocaleString('es-CO')} votos</b> repartidos por esa lectura${L.sinDato ? `; ${Math.round(L.sinDato).toLocaleString('es-CO')} cayeron en barrios sin medición` : ''}.` : 'Todavía no tiene votos propios en la ciudad, así que esto es la ciudad, no usted.'}</p>
    <p style="margin-bottom:8px"><b>Su voto hoy (lectura 2023)</b></p>
    ${barraArquetipos(L, '2023')}
    <p style="margin-bottom:8px"><b>A dónde va ese mismo voto en 2027</b></p>
    ${barraArquetipos(L, '2027')}
    <p style="margin-bottom:8px"><b>Por comuna</b></p>
    <ul class="puntaje-escala">${L.filasComuna.slice(0, 8).map(f => `<li><b>${Math.round(f.votos).toLocaleString('es-CO')}</b> ${escHtml(f.nombre)} · ${fam(f.a23)} → <b style="min-width:0;font-size:14px">${fam(f.a27)}</b> en 2027</li>`).join('')}</ul>
    <p style="margin-bottom:8px"><b>Sus barrios más fuertes</b></p>
    <ul class="puntaje-escala">${L.filasBarrio.slice(0, 6).map(f => `<li><b>${Math.round(f.votos).toLocaleString('es-CO')}</b> ${escHtml(f.nombre)}${f.comuna ? ` · ${escHtml(f.comuna)}` : ''} · ${fam(f.a23)}${f.riesgo ? ` · riesgo de cambio ${escHtml(String(f.riesgo).toLowerCase())}` : ''}</li>`).join('')}</ul>
    <p class="puntaje-nota">Fuente: Proyecto DC · cartografía emocional de Medellín (152 barrios, 21 comunas), con la proyección 2027 ajustada. El arquetipo es del <b>barrio</b>, no de sus votantes: dice en qué clase de territorio está su votación, no qué siente cada persona que votó por usted.</p>`;
  $('introModal').classList.add('open');
}

/* ── Perfil del votante ─────────────────────────────────────────────────────
   Ponderar por votos el censo del puesto responde «cómo es el electorado
   donde usted saca votos», que es distinto de «quién votó por usted» —eso no
   lo sabe nadie— y distinto del promedio del municipio, que es contra lo que
   se compara para que el número signifique algo. */
const EDAD_PUESTO_URL = `${S3}/mapas-2026/CENSO_EDAD_PUESTO.json`;
let edadPuestoPromise = null;
function censoEdadPuesto() {
  if (!edadPuestoPromise) edadPuestoPromise = fetch(EDAD_PUESTO_URL).then(r => r.ok ? r.json() : null).catch(() => null);
  return edadPuestoPromise;
}
const ZONA_ESPECIAL = new Set(['90', '98']);   /* censo consolidado y cárceles: ni rural ni urbano */
async function perfilDelVotante() {
  const mesas = await mesasDelHistorial();
  const puestos = await puestosPorBarrio();
  const municipio = municipioMayoritario(mesas);
  let votos = 0, conCenso = 0, mujeres = 0, rural = 0, urbano = 0, especial = 0, sinCoordenada = 0;
  const edad = await censoEdadPuesto();
  const bandas = edad?.bandas || [], edadVotos = bandas.map(() => 0); let conEdad = 0;
  mesas.forEach(m => {
    const v = Number(m.v || 0); if (!v) return;
    votos += v;
    const zona = String(m.zon || '').padStart(2, '0');
    if (zona === '99') rural += v; else if (ZONA_ESPECIAL.has(zona)) especial += v; else urbano += v;
    const code = electoralPlaceCode(m), p = puestos[code];
    if (p && p.mujeres + p.hombres > 0) { conCenso += v; mujeres += v * p.mujeres / (p.mujeres + p.hombres); } else sinCoordenada += v;
    const e = edad?.puestos?.[code];
    if (e) { const tot = e.reduce((s, x) => s + Number(x || 0), 0); if (tot > 0) { conEdad += v; e.forEach((x, i) => { edadVotos[i] += v * Number(x || 0) / tot; }); } }
  });
  /* El municipio entero, para comparar: el censo de TODOS sus puestos. */
  let munM = 0, munT = 0, munRural = 0, munCenso = 0;
  Object.entries(puestos).forEach(([code, p]) => {
    if (code.slice(0, 5) !== municipio) return;
    const censo = p.mujeres + p.hombres; if (!censo) return;
    munM += p.mujeres; munT += censo; munCenso += censo;
    if (code.slice(5, 7) === '99') munRural += censo;
  });
  return {
    votos, municipio,
    mujeres: conCenso ? mujeres / conCenso : null, cobertura: votos ? conCenso / votos : 0, sinCoordenada,
    mujeresMunicipio: munT ? munM / munT : null, ruralMunicipio: munCenso ? munRural / munCenso : null,
    rural: votos ? rural / votos : 0, urbano: votos ? urbano / votos : 0, especial,
    edad: conEdad ? { bandas, reparto: edadVotos.map(x => x / conEdad), cobertura: conEdad / votos, fuente: edad?.fuente || '' } : null
  };
}
let PERFIL_ACTUAL = null;
const pct1 = x => `${(x * 100).toFixed(1).replace('.', ',')} %`;
async function pintarPerfil() {
  const card = $('crmPerfil'); if (!card) return;
  PERFIL_ACTUAL = null;
  $('crmPerfilBtn').disabled = true;
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
    $('crmPerfilBtn').disabled = false;
  } catch (e) {
    $('crmPerfilTitulo').textContent = 'Todavía no hay perfil para esta candidatura.';
    $('crmPerfilCopy').textContent = 'Los puestos de su votación no tienen censo publicado, así que preferimos no estimar un perfil que no podemos sostener.';
    $('crmPerfilDato').textContent = '—'; $('crmPerfilSub').textContent = 'sin censo por puesto';
  }
}
function mostrarPerfil() {
  const P = PERFIL_ACTUAL; if (!P) return;
  const barra = (a, b, etA, etB) => `<div class="arq-barra"><i style="flex:${Math.max(a, .0001)};background:var(--green)" title="${escHtml(etA)}"></i><i style="flex:${Math.max(b, .0001)};background:#c9d6cd" title="${escHtml(etB)}"></i></div>`;
  const edad = P.edad
    ? `<p style="margin-bottom:8px"><b>Edad</b></p>
       ${`<ul class="arq-lista">${P.edad.reparto.map((x, i) => `<li><span class="arq-punto" style="background:var(--green);opacity:${1 - i * .2}"></span><b>${pct1(x)}</b> ${escHtml(P.edad.bandas[i])}</li>`).join('')}</ul>`}
       <p class="puntaje-nota" style="border:0;padding-top:0">${escHtml(P.edad.fuente || 'Censo por edad de cada puesto, ponderado por su votación.')}</p>`
    : `<p style="margin-bottom:8px"><b>Edad</b></p>
       <p>Todavía no. El censo por edad existe por puesto de votación, pero no está publicado en la fuente que lee esta página; en cuanto se publique, la edad aparece acá sin tocar nada más. Preferimos decirlo a estimarla con el promedio del municipio y presentarla como suya.</p>`;
  $('introModalKicker').textContent = 'Candidato 360 · perfil del votante';
  $('introModalTitle').textContent = 'Cómo es el electorado donde usted vota';
  $('introModalText').innerHTML = `
    <p>El voto es secreto: <b>nadie</b> puede decir quién votó por usted. Lo que sí se puede es describir el electorado de los puestos donde están sus votos, ponderado por cuántos votos sacó en cada uno. Es una lectura del terreno, no de sus votantes.</p>
    <p style="margin-bottom:8px"><b>Sexo</b></p>
    ${barra(P.mujeres, 1 - P.mujeres, 'Mujeres', 'Hombres')}
    <ul class="puntaje-escala">
      <li><b>${pct1(P.mujeres)}</b> de mujeres en el censo de sus puestos.</li>
      ${P.mujeresMunicipio === null ? '' : `<li><b>${pct1(P.mujeresMunicipio)}</b> de mujeres en el municipio entero. La diferencia es lo suyo: dónde saca votos, no cuántos.</li>`}
    </ul>
    <p style="margin-bottom:8px"><b>Rural y urbano</b></p>
    ${barra(P.urbano, P.rural, 'Urbano', 'Rural')}
    <ul class="puntaje-escala">
      <li><b>${pct1(P.rural)}</b> de sus votos en puestos rurales (zona 99)${P.ruralMunicipio === null ? '' : `, contra ${pct1(P.ruralMunicipio)} del censo del municipio`}.</li>
      <li><b>${pct1(P.urbano)}</b> en la cabecera.${P.especial ? ` Otros ${P.especial.toLocaleString('es-CO')} votos están en puestos especiales (cárceles y censo consolidado), que no son ni lo uno ni lo otro.` : ''}</li>
    </ul>
    ${edad}
    <p class="puntaje-nota">Fuente: censo electoral por puesto de la Registraduría (PUESTOS_GEOREF, columnas de mujeres y hombres) y la zona electoral de cada mesa. Cubre el ${pct1(P.cobertura)} de su votación: ${P.sinCoordenada ? `${P.sinCoordenada.toLocaleString('es-CO')} votos están en puestos sin censo publicado` : 'todos sus puestos tienen censo publicado'}. <a class="enlace-boton" href="candidato-360-perfil.html">Cómo se lee esto sin violar el secreto del voto →</a></p>`;
  $('introModal').classList.add('open');
}

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
  Object.entries(puestos).forEach(([code, p]) => { if (code.slice(0, prefijo.length) === prefijo) { censo += Number(p.censo || 0); n++; } });
  return { censo, puestos: n };
}
let FIRMAS_ACTUAL = null;
async function lecturaFirmas(campana) {
  const bloque = campana?.espectro; if (!bloque) return null;
  const mesas = await mesasDelHistorial();
  const unidad = CORP_MUNICIPAL.includes(campana.corp) ? 'localidad' : 'municipio';
  const [territorio, rd] = await Promise.all([
    censoDelTerritorio(campana),
    resultadosDestino(unidad, mesas.length ? mesas : [{ dep: campana.departamento, mun: codigoMunicipioObjetivo() }], campana).catch(() => null),
  ]);
  const req = requisitoDeFirmas(territorio.censo);
  const hb = rd ? huellaBloque(rd.porArea, bloque) : { huella: null };
  const props = hb.huella ? proporciones(hb.huella) : null;
  const reparto = props ? distributeVotes(hb.huella, req.exigido) : null;
  const nombres = rd?.porArea || {};
  const filas = reparto
    ? Object.entries(reparto).map(([area, firmas]) => ({ area, nombre: nombres[area]?.nombre || nombres[area]?.comuna || area, firmas, votos: hb.huella[area] || 0 }))
      .filter(f => f.firmas > 0).sort((a, b) => b.firmas - a.firmas)
    : [];
  FIRMAS_ACTUAL = { bloque, req, territorio, filas, unidad, campana, cobertura: hb.cobertura || 0 };
  return FIRMAS_ACTUAL;
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
    $('crmFirmasCopy').textContent = L.filas.length
      ? `El ${Math.round(FIRMAS_FRACCION * 100)} % del censo de su territorio (${L.territorio.censo.toLocaleString('es-CO')} personas)${L.req.topeAplica ? `, con el tope legal de ${FIRMAS_TOPE.toLocaleString('es-CO')}` : ''}. Repartidas por donde vota ${etiqueta.toLowerCase()}: ${L.filas.slice(0, 3).map(f => f.nombre).join(', ')} concentran ${Math.round(L.filas.slice(0, 3).reduce((s, f) => s + f.firmas, 0) / L.req.exigido * 100)} % de la meta.`
      : `El ${Math.round(FIRMAS_FRACCION * 100)} % del censo de su territorio (${L.territorio.censo.toLocaleString('es-CO')} personas)${L.req.topeAplica ? `, con el tope legal de ${FIRMAS_TOPE.toLocaleString('es-CO')}` : ''}. Todavía no podemos repartirlas: no hay resultados de esa familia política en este territorio.`;
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
    <p>Por firmas no hay huella de partido que seguir, así que se usa la de <b>${escHtml(etiqueta.toLowerCase())}</b> —la familia que usted eligió— en las últimas elecciones de este territorio. No predice que esa gente lo apoye: dice dónde hay más personas a las que la conversación les suena, que es donde una firma cuesta menos trabajo.</p>
    <p style="margin-bottom:8px"><b>Cuántas</b></p>
    <ul class="puntaje-escala">
      <li><b>${L.territorio.censo.toLocaleString('es-CO')}</b> personas en el censo electoral de su territorio, sumando los ${L.territorio.puestos.toLocaleString('es-CO')} puestos de votación publicados.</li>
      <li><b>${L.req.crudo.toLocaleString('es-CO')}</b> es el ${Math.round(FIRMAS_FRACCION * 100)} % de ese censo, que es la regla del artículo 9 de la Ley 130 de 1994 para un cargo uninominal.</li>
      ${L.req.topeAplica ? `<li><b>${FIRMAS_TOPE.toLocaleString('es-CO')}</b> es el tope que fija la misma norma: por grande que sea el territorio, no se exigen más.</li>` : ''}
    </ul>
    <p style="margin-bottom:8px"><b>Dónde, ${unidad} por ${unidad}</b></p>
    ${L.filas.length ? `<ul class="arq-lista">${L.filas.slice(0, 12).map(f => `<li><span class="arq-punto" style="background:${window.PartidosBloques?.BLOQUE_COLOR?.[L.bloque] || 'var(--green)'}"></span><b>${f.firmas.toLocaleString('es-CO')}</b> ${escHtml(f.nombre)}<em>${Math.round(f.firmas / max * 100)} %</em></li>`).join('')}</ul>`
      : '<p>No hay resultados de esa familia política en este territorio, así que no repartimos nada: preferimos no inventar un plan de recolección.</p>'}
    <p class="puntaje-nota">La cifra es una <b>estimación</b>: el censo de corte y las resoluciones de la Registraduría mueven el número exacto, y conviene confirmarlo con ellos antes de imprimir formularios. El reparto sale de los votos de ${escHtml(etiqueta.toLowerCase())} en la última elección comparable de este territorio, no de una encuesta.</p>`;
  $('introModal').classList.add('open');
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
