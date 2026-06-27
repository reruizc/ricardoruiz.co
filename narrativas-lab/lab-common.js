/* ════════════════════════════════════════════════════════════════
   NarrativasLab · lab-common.js
   Gate de acceso (whitelist) + cursor + glue de tema + I/O del mensaje
   compartido (nl-msg) + widget selector de ciudad. Compartido por el hub
   y todas las subpáginas. Requiere cities.js y engine.js cargados antes.
   ════════════════════════════════════════════════════════════════ */
(function(){
  const ALLOWED = ['reruizc@gmail.com', 'frp1978@gmail.com', 'nuevagemela@gmail.com']; // + Nury (socia)

  /* ── GATE ───────────────────────────────────────────── */
  function emailAllowed(em){ return em && ALLOWED.includes(String(em).toLowerCase().trim()); }
  function denyToLogin(){ try{ localStorage.removeItem('rr-token'); localStorage.removeItem('rr-user'); }catch(e){} window.location.replace('../login.html'); }
  function denyToDashboard(){ window.location.replace('../dashboard.html'); }

  function bootGate(onReady){
    let token=null, userRaw=null, user=null;
    try { token = localStorage.getItem('rr-token'); userRaw = localStorage.getItem('rr-user'); } catch(e){}
    try { user = userRaw ? JSON.parse(userRaw) : null; } catch(e){ user = null; }
    const reveal = () => {
      const gate = document.getElementById('gate'); if (gate) gate.remove();
      const nav = document.getElementById('topNav'); if (nav) nav.hidden = false;
      const main = document.getElementById('main'); if (main) main.hidden = false;
      const uc = document.getElementById('userChip');
      if (uc && user) uc.textContent = String(user.email||'').split('@')[0];
      if (typeof onReady === 'function') onReady(user);
    };
    if (!token || !user) return denyToLogin();
    if (!emailAllowed(user.email)) return denyToDashboard();
    // En localhost (máquina de dev) confiamos en la whitelist local y evitamos
    // el round-trip al worker — así el preview funciona sin sesión real.
    if (['localhost','127.0.0.1'].includes(location.hostname)) return reveal();
    (async () => {
      try {
        const res = await fetch('https://rr-auth.reruizc.workers.dev/auth/me', { headers:{ 'Authorization':`Bearer ${token}` } });
        if (res.status === 401) return denyToLogin();
        const data = await res.json();
        if (!data.ok || !emailAllowed(data.user && data.user.email)) return denyToDashboard();
        try { localStorage.setItem('rr-user', JSON.stringify(Object.assign({}, user, data.user))); } catch(e){}
        reveal();
      } catch(e){ reveal(); }   // si el worker no responde, no bloquear (ya pasó la whitelist local)
    })();
  }

  /* ── CURSOR custom ──────────────────────────────────── */
  function initCursor(){
    const cur = document.querySelector('.cursor'), ring = document.querySelector('.cursor-ring');
    if (!cur || !ring) return;
    window.addEventListener('mousemove', e => {
      cur.style.left = ring.style.left = e.clientX + 'px';
      cur.style.top = ring.style.top = e.clientY + 'px';
    });
    document.addEventListener('mouseover', e => {
      const hov = e.target.closest('button,a,.persona,select,input,textarea,.chip,.scen-pill,.modulo,th');
      cur.style.transform = 'translate(-50%,-50%) scale(' + (hov?1.8:1) + ')';
      ring.style.opacity = hov ? '.8' : '.4';
    });
  }

  /* ── TEMA: lo togglea ../theme.js (body.day-mode por hora). Acá solo el ícono. ── */
  window.__onThemeChange = function(day){
    document.querySelectorAll('#theme-toggle-btn').forEach(b => { b.textContent = day ? '🌙' : '☀'; });
  };

  /* ── MENSAJE compartido (nl-msg / nl-var-a / nl-var-b) ── */
  const K_MSG = 'nl-msg', K_A = 'nl-var-a', K_B = 'nl-var-b';
  function _read(k, fallback){ try { const s = localStorage.getItem(k); return s ? JSON.parse(s) : fallback; } catch(e){ return fallback; } }
  function _write(k, obj){ try { localStorage.setItem(k, JSON.stringify(obj)); } catch(e){} }
  const _clone = o => JSON.parse(JSON.stringify(o));
  function getMsg(){ return _read(K_MSG, _clone(window.EX_B || {})); }
  function saveMsg(m){ _write(K_MSG, m); }
  function getVar(which){ return _read(which==='a'?K_A:K_B, _clone((which==='a'?window.EX_A:window.EX_B) || {})); }
  function saveVar(which, m){ _write(which==='a'?K_A:K_B, m); }

  /* ── Widget selector de ciudad (nav o hero) ──────────── */
  function _cityOptions(activeKey){
    const C = window.NLCities; if (!C) return '';
    const grp = { grande:[], intermedia:[] };
    C.LIST.forEach(k => { const c = C.CITIES[k]; (grp[c.grupo]||grp.intermedia).push(c); });
    const opt = c => `<option value="${c.key}"${c.key===activeKey?' selected':''}>${c.nombre}</option>`;
    return `<optgroup label="Principales">${grp.grande.map(opt).join('')}</optgroup>`+
           `<optgroup label="Intermedias">${grp.intermedia.map(opt).join('')}</optgroup>`;
  }
  // Monta un <select> de ciudad dentro de `target` (elemento o selector).
  // onPick(cfg) opcional; por defecto NLCities.setActive (dispara onChange global).
  function mountCitySelect(target, opts){
    opts = opts || {};
    const host = (typeof target === 'string') ? document.querySelector(target) : target;
    if (!host || !window.NLCities) return;
    const ak = window.NLCities.activeKey();
    host.innerHTML = `<div class="city-select-wrap"><label>Ciudad</label>`+
      `<select class="city-select" id="${opts.id||'nl-city-select'}">${_cityOptions(ak)}</select></div>`;
    const sel = host.querySelector('select');
    sel.addEventListener('change', () => {
      window.NLCities.setActive(sel.value);
      if (typeof opts.onPick === 'function') opts.onPick(window.NLCities.active());
    });
    // mantener el <select> en sync si la ciudad cambia por otra vía
    window.NLCities.onChange(c => { if (c && sel.value !== c.key) sel.value = c.key; });
    return sel;
  }

  window.NLCommon = { ALLOWED, bootGate, initCursor, getMsg, saveMsg, getVar, saveVar, mountCitySelect };
})();
