/*
 * theme.js — tema día/noche driven por hora local
 *
 * Cada carga decide por la hora (7am–7pm = día). El botón #theme-btn
 * funciona como override de sesión que NO persiste; al recargar la
 * página vuelve al estado de la hora.
 *
 * Si la pestaña queda abierta un rato, un interval revisa cada minuto
 * y auto-cambia al cruzar dawn/dusk (a menos que el usuario haya tocado
 * el botón manualmente en esta sesión).
 *
 * Páginas con efectos secundarios al cambiar tema (repintar mapa,
 * rebuild tile layer, etc.) pueden registrar un callback:
 *
 *   window.__onThemeChange = function(day){ ... };
 *
 * El texto del botón se localiza internamente leyendo `rr-lang` del
 * localStorage. No invoca `window.__applyLang` (algunas páginas usan
 * eso para recargar la página, lo cual sería un loop al togglear).
 */
(function () {
  'use strict';
  let userOverride = false;

  const LABELS = {
    co: { day: '☀ Modo día', night: '🌙 Modo noche' },
    mx: { day: '☀ Modo día', night: '🌙 Modo noche' },
    us: { day: '☀ Day mode', night: '🌙 Night mode' },
    cn: { day: '☀ 日间模式', night: '🌙 夜间模式' },
  };

  function getLabel(day) {
    const lang = localStorage.getItem('rr-lang') || 'co';
    const tl = LABELS[lang] || LABELS.co;
    return day ? tl.night : tl.day;
  }

  function isDayHour() {
    const h = new Date().getHours();
    return h >= 7 && h < 19;
  }

  function applyTheme(day) {
    if (!document.body) return;
    document.body.classList.toggle('day-mode', day);
    // Para páginas que usan data-theme en root (e.g. dashboard.html) en vez de
    // body.day-mode. Es no-op si la página no tiene CSS [data-theme='dark'].
    document.documentElement.setAttribute('data-theme', day ? '' : 'dark');
    const btn = document.getElementById('theme-btn');
    if (btn) btn.textContent = getLabel(day);
    if (typeof window.__onThemeChange === 'function') {
      try { window.__onThemeChange(day); } catch (e) { console.warn('__onThemeChange:', e); }
    }
  }

  function toggleTheme() {
    userOverride = true;
    applyTheme(!document.body.classList.contains('day-mode'));
  }

  // Permite que lang.js refresque la etiqueta del botón al cambiar de idioma
  // sin alterar el estado actual día/noche.
  function refreshThemeLabel() {
    if (!document.body) return;
    applyTheme(document.body.classList.contains('day-mode'));
  }

  window.isDayHour = isDayHour;
  window.applyTheme = applyTheme;
  window.toggleTheme = toggleTheme;
  window.refreshThemeLabel = refreshThemeLabel;

  // Init: si el script se carga antes de que <body> exista (e.g. desde <head>),
  // esperamos a que llegue body antes de aplicar.
  function init() {
    applyTheme(isDayHour());
    setInterval(function () {
      if (userOverride) return;
      const shouldBeDay = isDayHour();
      const isDay = document.body.classList.contains('day-mode');
      if (shouldBeDay !== isDay) applyTheme(shouldBeDay);
    }, 60000);
  }

  if (document.body) init();
  else document.addEventListener('DOMContentLoaded', init);

  // Carga el pixel de tracking de forma asíncrona (no bloqueante).
  // Vive en /track.js; respeta DNT, noindex y localhost por sí mismo.
  try {
    var s = document.createElement('script');
    s.src = '/track.js'; s.async = true; s.defer = true;
    (document.head || document.body || document.documentElement).appendChild(s);
  } catch (e) {}
})();
