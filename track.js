/*
 * track.js — pixel ligero (~1 KB) que envía un pageview al worker rr-auth.
 *
 * Se incluye al final de theme.js (cargado en la mayoría de páginas) y como
 * <script defer src="track.js"></script> en index.html, register.html, login.html.
 *
 * Reglas:
 *   - No trackea en localhost / 127.* / *.test
 *   - No trackea si <meta name="robots" content="noindex…"> (Proyecto DC, etc).
 *   - Respeta DNT y la cabecera Sec-GPC del navegador.
 *   - sessionStorage `rr-track-sid` = id de sesión (vive lo que la pestaña).
 *   - localStorage   `rr-track-vid` = visitante (90 días, sin PII).
 *   - El servidor agrega request.cf.country (gratis en Workers).
 *
 * Privacidad: no se envía IP (queda en el log de CF, no se persiste), no se
 * envía user-agent, no hay cookies. Solo path + referrer + flags + dos IDs
 * aleatorios que no se cruzan con la cuenta del usuario.
 */
(function () {
  'use strict';
  try {
    var host = location.hostname;
    if (host === 'localhost' || host.startsWith('127.') || host.endsWith('.test') || host.endsWith('.local')) return;
    if (navigator.doNotTrack === '1' || window.doNotTrack === '1' || navigator.globalPrivacyControl) return;
    var noidx = document.querySelector('meta[name="robots"]');
    if (noidx && /noindex/i.test(noidx.getAttribute('content') || '')) return;

    var VID = 'rr-track-vid', SID = 'rr-track-sid';
    var vid = null, isNewVisitor = false;
    try {
      vid = localStorage.getItem(VID);
      if (!vid) {
        vid = (crypto.randomUUID && crypto.randomUUID()) || (Date.now() + '-' + Math.random().toString(36).slice(2));
        localStorage.setItem(VID, vid);
        isNewVisitor = true;
      }
    } catch (e) { /* incognito sin localStorage: tratar cada visita como nueva */ isNewVisitor = true; }

    var sid = null, isNewSession = false;
    try {
      sid = sessionStorage.getItem(SID);
      if (!sid) {
        sid = (crypto.randomUUID && crypto.randomUUID()) || (Date.now() + '-' + Math.random().toString(36).slice(2));
        sessionStorage.setItem(SID, sid);
        isNewSession = true;
      }
    } catch (e) { isNewSession = true; }

    var utm = null;
    try {
      var qs = new URLSearchParams(location.search);
      var s = qs.get('utm_source') || qs.get('ref') || qs.get('src');
      if (s) utm = String(s).slice(0, 60);
    } catch (e) {}

    var payload = JSON.stringify({
      path: location.pathname,
      ref: document.referrer || null,
      isNewSession: isNewSession,
      isNewVisitor: isNewVisitor,
      utm: utm,
    });

    // Beacon es ideal (fire-and-forget, no bloquea unload). Fallback a fetch.
    var url = 'https://rr-auth.reruizc.workers.dev/track/pageview';
    if (navigator.sendBeacon) {
      try { navigator.sendBeacon(url, new Blob([payload], { type: 'application/json' })); return; }
      catch (e) { /* fallthrough */ }
    }
    fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: payload, keepalive: true, mode: 'cors', credentials: 'omit' }).catch(function () {});
  } catch (e) { /* fail silent */ }
})();
