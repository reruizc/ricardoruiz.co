/* ═══════════════════════════════════════════════════════════════════════════
   CANDIDATO 360 · chasis de los paneles (medios y redes)
   ───────────────────────────────────────────────────────────────────────────
   Lo que candidato-360-medios.html y candidato-360-redes.html necesitan por
   igual y no pertenece a ninguna de las dos: sesión, acceso, el vínculo de la
   cuenta (de ahí salen el nombre y el territorio de la campaña), el helper
   contra el worker y el encabezado.

   Cada panel es su propio HTML a propósito. Son dos preguntas distintas —«qué
   dice la prensa de lo suyo» y «cuáles son sus cuentas»— con su propio ritmo:
   una se abre para leer y la otra para configurar. Meterlas en el CRM las
   habría convertido en dos acordeones más de una página que ya es larga.

   ⚠️ Al tocar este archivo hay que bumpear su ?v= en los dos HTML, o el
   navegador sirve la copia vieja sin dar ningún error.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (global) {
  'use strict';

  const AUTH_API = (global.RR_RUNTIME_CONFIG && global.RR_RUNTIME_CONFIG.authBase) || 'https://rr-auth.reruizc.workers.dev';
  const CAUDAL_API = `${AUTH_API}/caudal/api`;
  const SOPORTE_POR_DEFECTO = 'hola@ricardoruiz.co';

  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? '').replace(/[&<>'"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
  const num = n => Number(n || 0).toLocaleString('es-CO');

  const SESION = { token: null, user: null, acceso: false, fuente: 'ninguno', vinculo: null, soporte: SOPORTE_POR_DEFECTO, error: null };

  async function api(path, opts = {}) {
    const headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
    if (SESION.token) headers.Authorization = `Bearer ${SESION.token}`;
    const r = await fetch(`${AUTH_API}${path}`, Object.assign({}, opts, { headers }));
    let data = null; try { data = await r.json(); } catch {}
    return { status: r.status, ok: r.ok && data?.ok !== false, data: data || {} };
  }
  /* La lectura de prensa pasa por el mismo proxy de Caudal: es la fuente que ya
     alimenta el briefing (Google News RSS del lado del servidor). */
  async function caudal(payload) {
    const headers = { 'Content-Type': 'application/json' };
    if (SESION.token) headers.Authorization = `Bearer ${SESION.token}`;
    const r = await fetch(CAUDAL_API, { method: 'POST', headers, body: JSON.stringify(payload) });
    if (r.status === 429) throw new Error('Demasiadas consultas seguidas. Espere un minuto.');
    const d = await r.json();
    if (d?.error) throw new Error(String(d.error));
    return d;
  }

  /* El territorio se arma con lo que el vínculo guardó de la campaña: es lo que
     hace que la lectura sea de SU municipio y no del país entero. */
  function territorio(v = SESION.vinculo) {
    const c = v?.campana; if (!c) return { texto: '', partes: [] };
    const partes = [c.localidad, c.municipio, c.departamentoNombre].filter(Boolean);
    return { texto: partes.join(' · '), partes, municipio: c.municipio || c.departamentoNombre || '', localidad: c.localidad || '' };
  }
  function nombreCandidatura(v = SESION.vinculo) {
    if (!v) return '';
    return v.tipo === 'nuevo' ? (v.nuevo?.nombre || 'su candidatura') : (v.candidato?.nombre || 'su candidatura');
  }
  function nombrePublico(v = SESION.vinculo) { return v?.tipo === 'nuevo' ? (v.nuevo?.nombrePublico || '') : ''; }

  function pintarNav(pagina) {
    const nav = $('navAuth'); if (!nav) return;
    const next = encodeURIComponent(pagina);
    if (!SESION.token || !SESION.user) {
      nav.innerHTML = `<a class="nav-login" href="login.html?next=${next}">Iniciar sesión</a><a class="nav-register" href="register.html?next=${next}">Registrarse</a>`;
      return;
    }
    /* El «← CRM» ya está a la izquierda de la barra: acá solo el plan y el perfil. */
    nav.innerHTML = `<span class="nav-plan${SESION.acceso ? ' ok' : ''}">${SESION.acceso ? 'Candidato 360' : esc(SESION.user.plan || 'free')}</span><a class="nav-login" href="dashboard.html">Mi perfil</a>`;
  }

  /* Un panel sin vínculo no tiene de quién hablar. En vez de una página vacía,
     se dice qué falta y se manda al sitio donde se resuelve. */
  function muro(motivo, accion) {
    const caja = $('panelMuro'); if (!caja) return;
    caja.innerHTML = `<div class="c360-vitrina"><p>${motivo}</p>${accion}</div>`;
    caja.classList.remove('hidden');
    $('panelCuerpo')?.classList.add('hidden');
  }

  async function arrancar(pagina) {
    try { SESION.token = localStorage.getItem('rr-token') || null; SESION.user = JSON.parse(localStorage.getItem('rr-user') || 'null'); } catch {}
    if (SESION.token) {
      try {
        const r = await api('/c360/me');
        if (r.status === 401) { localStorage.removeItem('rr-token'); localStorage.removeItem('rr-user'); SESION.token = null; SESION.user = null; }
        else if (r.ok) {
          SESION.acceso = !!r.data.acceso; SESION.fuente = r.data.fuente || 'ninguno';
          SESION.vinculo = r.data.vinculo || null;
          if (r.data.soporte) SESION.soporte = r.data.soporte;
          if (r.data.email) SESION.user = Object.assign({}, SESION.user || {}, { email: r.data.email, plan: r.data.plan });
        } else SESION.error = r.data?.error || `HTTP ${r.status}`;
      } catch (e) { SESION.error = String(e); }
    }
    pintarNav(pagina);
    const next = encodeURIComponent(pagina);
    if (!SESION.token) return muro('Este panel trabaja sobre <b>su</b> candidatura, así que primero hay que saber quién es.', `<a class="wall-btn primary" href="login.html?next=${next}">Iniciar sesión</a>`), false;
    if (!SESION.acceso) return muro('Su cuenta todavía no tiene acceso a Candidato 360.', `<a class="wall-btn primary" href="candidato-360.html?comprar=1">Ver qué incluye</a>`), false;
    if (!SESION.vinculo) return muro('Su cuenta todavía no tiene una candidatura abierta: los paneles se arman sobre su territorio y su nombre.', `<a class="wall-btn primary" href="candidato-360.html">Abrir mi candidatura</a>`), false;
    const cab = $('panelCandidatura');
    if (cab) {
      const t = territorio();
      cab.innerHTML = `<b>${esc(nombreCandidatura())}</b>${t.texto ? ` · ${esc(t.texto)}` : ''}`;
    }
    return true;
  }

  async function guardarEscucha(datos) {
    const r = await api('/c360/escucha', { method: 'POST', body: JSON.stringify(datos) });
    if (r.ok && r.data?.vinculo) SESION.vinculo = r.data.vinculo;
    return r;
  }

  global.C360Panel = { SESION, api, caudal, arrancar, guardarEscucha, territorio, nombreCandidatura, nombrePublico, muro, $, esc, num };
})(window);
