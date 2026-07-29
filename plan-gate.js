/* plan-gate.js — gate por plan (anónimo · Básico · Pro · Premium) compartido.
 *
 * Extrae el bloque que veleta.html y oportunidad.html tenían duplicado inline.
 * Todo vive dentro de un IIFE y solo se expone `window.PlanGate`, para no chocar
 * con constantes que las páginas ya declaran (PLAN_LABEL, etc.).
 *
 * Uso:
 *   <script>window.GATE_FEATURES = {
 *     plan: { 'barrios':'pro', 'mesas':'premium' },              // feature → plan mínimo
 *     copy: { 'barrios': {title:'…', desc:'…'} },                // texto del modal
 *   };</script>
 *   <script src="plan-gate.js"></script>
 *   …
 *   await PlanGate.init();                  // lee localStorage + refresca contra el worker
 *   if (!PlanGate.require('barrios')) return;   // abre el modal y devuelve false
 *
 * El modal (DOM + CSS) lo inyecta el propio script: la página no copia HTML.
 * Paleta del sistema visual v2 (fondo #060810, azul #0047FF); sin modo día.
 */
(function () {
  'use strict';

  var AUTH_URL  = 'https://rr-auth.reruizc.workers.dev/auth/me';
  var LOGIN_URL = 'https://rr-auth.reruizc.workers.dev/auth/login';

  // `anonymous` es sintético del cliente (el worker nunca lo devuelve).
  // full y premium empatan a propósito: full es premium sin caducidad.
  var PLAN_RANK  = { anonymous: 0, free: 1, basico: 1, pro: 2, premium: 3, full: 3 };
  var PLAN_LABEL = { anonymous: 'Anónimo', free: 'Básico', basico: 'Básico',
                     pro: 'Pro', premium: 'Premium', full: 'Full' };
  var PLAN_PRICE = {
    pro:     { cop: '$79.900 COP', sub: 'al mes · $59.900/mes pagando anual' },
    premium: { cop: '$219.000 COP', sub: 'al mes · $179.000/mes pagando anual' },
  };

  var _plan = 'anonymous';
  var _user = null;
  var _listeners = [];

  function cfg() { return window.GATE_FEATURES || { plan: {}, copy: {} }; }
  function planFor(feat) { return (cfg().plan || {})[feat] || 'free'; }
  function copyFor(feat) {
    return (cfg().copy || {})[feat] ||
      { title: 'Esta función está bloqueada', desc: 'Requiere un plan superior.' };
  }

  function loadUserFromStorage() {
    try {
      var raw = localStorage.getItem('rr-user');
      var tok = localStorage.getItem('rr-token');
      if (raw && tok) {
        _user = JSON.parse(raw);
        _plan = (_user && _user.plan) || 'free';
        return true;
      }
    } catch (_) {}
    _user = null; _plan = 'anonymous';
    return false;
  }

  async function refreshUserFromAPI() {
    var tok = localStorage.getItem('rr-token');
    if (!tok) { _user = null; _plan = 'anonymous'; return; }
    try {
      var res = await fetch(AUTH_URL, { headers: { 'Authorization': 'Bearer ' + tok } });
      if (res.status === 401) {          // token vencido → limpiar y volver a anónimo
        localStorage.removeItem('rr-token');
        localStorage.removeItem('rr-user');
        _user = null; _plan = 'anonymous';
        return;
      }
      var data = await res.json();
      if (data && data.ok && data.user) {
        _user = data.user;
        _plan = data.user.plan || 'free';
        localStorage.setItem('rr-user', JSON.stringify(data.user));
      }
    } catch (_) { /* sin red → conservar lo del localStorage */ }
  }

  function has(feat) {
    return (PLAN_RANK[_plan] || 0) >= (PLAN_RANK[planFor(feat)] || 0);
  }

  function require_(feat) {
    if (has(feat)) return true;
    openModal(feat);
    return false;
  }

  /* Muestra gratis para anónimos: N usos antes de exigir cuenta (patrón veleta). */
  function sampleUsed(key) {
    try { return parseInt(localStorage.getItem('gate-sample-' + key) || '0', 10) || 0; }
    catch (_) { return 0; }
  }
  function sampleBump(key) {
    try { localStorage.setItem('gate-sample-' + key, String(sampleUsed(key) + 1)); } catch (_) {}
  }
  /* true si puede seguir; consume una muestra cuando el plan no alcanza. */
  function requireOrSample(feat, key, max) {
    if (has(feat)) return true;
    if (_plan === 'anonymous' && sampleUsed(key) < (max || 1)) { sampleBump(key); return true; }
    openModal(feat);
    return false;
  }

  function onChange(fn) { if (typeof fn === 'function') _listeners.push(fn); }
  function emit() { _listeners.forEach(function (f) { try { f(_plan, _user); } catch (_) {} }); }

  /* ── Modal ─────────────────────────────────────────────────────────── */
  var CSS = [
    '.pg-overlay{display:none;position:fixed;inset:0;background:rgba(4,6,16,.78);backdrop-filter:blur(4px);z-index:9500;align-items:center;justify-content:center;padding:1.5rem}',
    '.pg-overlay.show{display:flex}',
    '.pg-card{max-width:470px;width:100%;background:#0e1220;border:1px solid rgba(0,71,255,.45);padding:1.7rem 1.8rem 1.5rem;box-shadow:0 12px 40px rgba(0,0,0,.5);font-family:"HelveticaNeue",Helvetica,"Helvetica Neue",Arial,sans-serif;max-height:90vh;overflow-y:auto}',
    '.pg-tag{display:inline-block;font-weight:600;font-size:.7rem;letter-spacing:.14em;text-transform:uppercase;color:#6f9bff;background:rgba(0,71,255,.14);border:1px solid rgba(0,71,255,.45);padding:.25rem .55rem;margin-bottom:.85rem}',
    '.pg-title{font-weight:700;font-size:1.2rem;letter-spacing:-.01em;color:#f4f3ef;margin-bottom:.55rem;line-height:1.25}',
    '.pg-desc{font-size:.92rem;line-height:1.55;color:rgba(255,255,255,.8);margin-bottom:1.2rem}',
    '.pg-price{font-weight:800;font-size:1.4rem;color:#6f9bff;letter-spacing:-.01em;margin-bottom:.25rem}',
    '.pg-price-sub{font-size:.82rem;color:rgba(255,255,255,.45);margin-bottom:1.1rem}',
    '.pg-actions{display:flex;gap:.6rem;flex-wrap:wrap}',
    '.pg-btn{display:inline-flex;align-items:center;justify-content:center;font-family:inherit;font-weight:600;font-size:.82rem;letter-spacing:.07em;text-transform:uppercase;padding:.62rem 1.05rem;cursor:pointer;text-decoration:none;border:1px solid transparent;transition:all .15s}',
    '.pg-btn-primary{background:#0047FF;border-color:#0047FF;color:#fff}',
    '.pg-btn-primary:hover{background:#0035cc;border-color:#0035cc}',
    '.pg-btn-ghost{background:transparent;border-color:rgba(255,255,255,.25);color:rgba(255,255,255,.72)}',
    '.pg-btn-ghost:hover{border-color:rgba(255,255,255,.5);color:#fff}',
    '.pg-login{display:none;margin-top:1.1rem;padding-top:1.1rem;border-top:1px solid rgba(255,255,255,.1)}',
    '.pg-login.show{display:block}',
    '.pg-login-title{font-weight:600;font-size:.72rem;letter-spacing:.14em;text-transform:uppercase;color:rgba(255,255,255,.5);margin-bottom:.7rem}',
    '.pg-field{display:flex;flex-direction:column;gap:.3rem;margin-bottom:.7rem}',
    '.pg-field label{font-weight:500;font-size:.76rem;color:rgba(255,255,255,.7)}',
    '.pg-field input{font-family:inherit;font-size:.9rem;padding:.55rem .7rem;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.18);color:#f4f3ef;outline:none;transition:border-color .15s}',
    '.pg-field input:focus{border-color:#0047FF}',
    '.pg-err{font-size:.8rem;color:#ff5c5c;min-height:1.1rem}',
    '.pg-login-actions{display:flex;align-items:center;justify-content:space-between;gap:.6rem;margin-top:.6rem;flex-wrap:wrap}',
    '.pg-forgot{font-size:.76rem;color:rgba(255,255,255,.5);text-decoration:none}',
    '.pg-forgot:hover{color:#6f9bff}',
    /* candado reusable para lo bloqueado en la propia página */
    '.pg-lock{display:inline-flex;align-items:center;gap:.35rem;font-size:.66rem;letter-spacing:.1em;text-transform:uppercase;color:#6f9bff;background:rgba(0,71,255,.12);border:1px solid rgba(0,71,255,.35);padding:.16rem .4rem;vertical-align:middle}',
    '@media(max-width:640px){.pg-card{padding:1.3rem 1.2rem}.pg-title{font-size:1.05rem}}',
  ].join('\n');

  var MODAL_HTML = '' +
    '<div class="pg-card" role="dialog" aria-modal="true">' +
      '<div class="pg-tag" id="pg-tag"></div>' +
      '<div class="pg-title" id="pg-title"></div>' +
      '<div class="pg-desc" id="pg-desc"></div>' +
      '<div class="pg-price" id="pg-price"></div>' +
      '<div class="pg-price-sub" id="pg-price-sub"></div>' +
      '<div class="pg-actions">' +
        '<a class="pg-btn pg-btn-primary" id="pg-cta" href="pricing.html">Ver planes</a>' +
        '<button type="button" class="pg-btn pg-btn-ghost" id="pg-cta-login">Ya tengo cuenta</button>' +
        '<button type="button" class="pg-btn pg-btn-ghost" id="pg-cta-close">Cerrar</button>' +
      '</div>' +
      '<form class="pg-login" id="pg-login">' +
        '<div class="pg-login-title">Iniciar sesión</div>' +
        '<div class="pg-field"><label for="pg-email">Email</label>' +
          '<input id="pg-email" type="email" autocomplete="email" required /></div>' +
        '<div class="pg-field"><label for="pg-pw">Contraseña</label>' +
          '<input id="pg-pw" type="password" autocomplete="current-password" required /></div>' +
        '<div class="pg-err" id="pg-err"></div>' +
        '<div class="pg-login-actions">' +
          '<a class="pg-forgot" href="forgot.html">¿Olvidaste tu contraseña?</a>' +
          '<button type="submit" class="pg-btn pg-btn-primary" id="pg-login-submit">Entrar</button>' +
        '</div>' +
      '</form>' +
    '</div>';

  var _injected = false;
  function inject() {
    if (_injected) return;
    _injected = true;
    var st = document.createElement('style');
    st.textContent = CSS;
    document.head.appendChild(st);
    var ov = document.createElement('div');
    ov.className = 'pg-overlay';
    ov.id = 'pg-modal';
    ov.innerHTML = MODAL_HTML;
    document.body.appendChild(ov);
    ov.addEventListener('click', function (e) { if (e.target === ov) closeModal(); });
    document.getElementById('pg-cta-close').addEventListener('click', closeModal);
    document.getElementById('pg-cta-login').addEventListener('click', toggleLogin);
    document.getElementById('pg-login').addEventListener('submit', onInlineLogin);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && ov.classList.contains('show')) closeModal();
    });
  }

  function openModal(feat) {
    inject();
    var needed = planFor(feat);
    var c = copyFor(feat);
    var isAnon = _plan === 'anonymous';
    document.getElementById('pg-tag').textContent =
      isAnon ? 'Crea tu cuenta gratis' : 'Disponible en ' + (PLAN_LABEL[needed] || needed);
    document.getElementById('pg-title').textContent = c.title;
    document.getElementById('pg-desc').textContent  = c.desc;
    var price = document.getElementById('pg-price');
    var sub   = document.getElementById('pg-price-sub');
    var p = PLAN_PRICE[needed];
    // A un anónimo primero le pedimos cuenta (gratis); el precio solo confunde.
    if (!isAnon && p) {
      price.textContent = p.cop; sub.textContent = p.sub;
      price.style.display = sub.style.display = '';
    } else {
      price.style.display = sub.style.display = 'none';
    }
    var cta = document.getElementById('pg-cta');
    var login = document.getElementById('pg-cta-login');
    if (isAnon) {
      cta.href = 'register.html';
      cta.textContent = 'Crear cuenta gratis';
      login.style.display = '';
    } else {
      cta.href = 'pricing.html';
      cta.textContent = 'Pasar a ' + (PLAN_LABEL[needed] || needed);
      login.style.display = 'none';
    }
    document.getElementById('pg-modal').classList.add('show');
  }

  function closeModal() {
    var ov = document.getElementById('pg-modal');
    if (ov) ov.classList.remove('show');
    var form = document.getElementById('pg-login');
    if (form) { form.classList.remove('show'); form.reset(); }
    var err = document.getElementById('pg-err');
    if (err) err.textContent = '';
    // El cursor custom del sitio queda "pegado" si el botón bajo el puntero
    // desaparece sin disparar mouseout (regla del proyecto).
    var c = document.getElementById('cursor'), r = document.getElementById('cursorRing');
    if (c) { c.style.transform = 'translate(-50%,-50%) scale(1)'; c.style.background = 'var(--blue)'; c.style.border = 'none'; }
    if (r) { r.style.opacity = '.4'; }
  }

  function toggleLogin() {
    var form = document.getElementById('pg-login');
    if (!form) return;
    form.classList.toggle('show');
    if (form.classList.contains('show')) {
      setTimeout(function () { var e = document.getElementById('pg-email'); if (e) e.focus(); }, 30);
    }
  }

  async function onInlineLogin(ev) {
    ev.preventDefault();
    var email = document.getElementById('pg-email');
    var pw    = document.getElementById('pg-pw');
    var err   = document.getElementById('pg-err');
    var btn   = document.getElementById('pg-login-submit');
    err.textContent = '';
    btn.disabled = true;
    var prev = btn.textContent;
    btn.textContent = 'Entrando…';
    try {
      var res = await fetch(LOGIN_URL, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.value.trim(), password: pw.value }),
      });
      var data = await res.json().catch(function () { return {}; });
      if (data && data.ok && data.token && data.user) {
        localStorage.setItem('rr-token', data.token);
        localStorage.setItem('rr-user', JSON.stringify(data.user));
        _user = data.user;
        _plan = data.user.plan || 'free';
        closeModal();
        emit();
      } else {
        err.textContent = (data && (data.error || data.message)) || 'Email o contraseña incorrectos.';
      }
    } catch (_) {
      err.textContent = 'No se pudo conectar. Revisa tu conexión e intenta de nuevo.';
    } finally {
      btn.disabled = false;
      btn.textContent = prev;
    }
    return false;
  }

  async function init() {
    loadUserFromStorage();
    inject();
    emit();                                    // pinta ya con lo del localStorage
    await refreshUserFromAPI();                // valida token / detecta upgrades
    emit();
    return _plan;
  }

  window.PlanGate = {
    init: init,
    has: has,
    require: require_,
    requireOrSample: requireOrSample,
    sampleUsed: sampleUsed,
    open: openModal,
    close: closeModal,
    onChange: onChange,
    refresh: async function () { await refreshUserFromAPI(); emit(); return _plan; },
    reset: function () { _user = null; _plan = 'anonymous'; emit(); },
    get plan() { return _plan; },
    get user() { return _user; },
    label: function (p) { return PLAN_LABEL[p || _plan] || p || ''; },
    rank: function (p) { return PLAN_RANK[p || _plan] || 0; },
    planFor: planFor,
  };
})();
