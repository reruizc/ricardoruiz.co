/**
 * lang.js — Selector de país/idioma compartido · ricardoruiz.co
 * 
 * Uso: incluir este script en cualquier página que tenga el selector de país.
 * Requiere en el HTML:
 *   - <span id="countryBtnLabel">
 *   - <button id="countryBtn" onclick="toggleCountryDropdown()">
 *   - <div id="countryDropdown">
 *   - <div class="country-option" data-value="co|us|mx" onclick="selectCountry(this)">
 * 
 * La página debe definir window.__applyLang(lang) para aplicar el idioma.
 */

(function() {
  const LANG_MAP   = { co: 'co', us: 'us', mx: 'co', cn: 'cn' };
  const LABEL_MAP  = { co: 'Colombia', us: 'United States / UK', mx: 'México', cn: '中国 / China' };
  const VAL_MAP    = { co: 'co', us: 'us', cn: 'cn' }; // inverso: lang → val del dropdown

  function getSavedLang() {
    return localStorage.getItem('rr-lang') || 'co';
  }

  function getSavedVal() {
    const lang = getSavedLang();
    if (lang === 'us') return 'us';
    if (lang === 'cn') return 'cn';
    return 'co';
  }

  function applySelector(val) {
    const btn   = document.getElementById('countryBtnLabel');
    const opts  = document.querySelectorAll('.country-option');
    if (btn)  btn.textContent = LABEL_MAP[val] || 'Colombia';
    opts.forEach(o => o.classList.toggle('selected', o.dataset.value === val));
  }

  window.toggleCountryDropdown = function() {
    const btn      = document.getElementById('countryBtn');
    const dropdown = document.getElementById('countryDropdown');
    const chevron  = document.getElementById('countryChevron');
    if (!btn || !dropdown) return;
    btn.classList.toggle('open');
    dropdown.classList.toggle('open');
    if (chevron) chevron.style.transform = dropdown.classList.contains('open') ? 'rotate(180deg)' : '';
  };

  window.selectCountry = function(el) {
    const val  = el.dataset.value;
    const lang = LANG_MAP[val] || 'co';
    const btn      = document.getElementById('countryBtn');
    const dropdown = document.getElementById('countryDropdown');
    if (btn)      btn.classList.remove('open');
    if (dropdown) dropdown.classList.remove('open');

    const prev = getSavedLang();
    localStorage.setItem('rr-lang', lang);
    applySelector(val);

    // Aplicar idioma en la página actual
    if (typeof window.__applyLang === 'function') {
      window.__applyLang(lang);
    }
  };

  // Cerrar dropdown al hacer clic fuera
  document.addEventListener('click', function(e) {
    const wrap = document.querySelector('.country-selector-wrap');
    if (wrap && !wrap.contains(e.target)) {
      const btn      = document.getElementById('countryBtn');
      const dropdown = document.getElementById('countryDropdown');
      if (btn)      btn.classList.remove('open');
      if (dropdown) dropdown.classList.remove('open');
    }
  });

  // Inicializar selector al cargar
  document.addEventListener('DOMContentLoaded', function() {
    applySelector(getSavedVal());
  });
})();
