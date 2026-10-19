// ════════════════════════════════════════════════════════════════════════
// Lab de Políticas Públicas · movimiento (la parte que el CSS no puede hacer)
// ════════════════════════════════════════════════════════════════════════
// Va con lab-motion.css. Tres cosas:
//   1. Pastillas de paso: los módulos re-pintan TODA la fila en cada cambio,
//      así que una animación por CSS estamparía todas las pastillas hechas
//      cada vez. Aquí se compara contra la fila anterior y solo se marca
//      (.lm-recien) la que acaba de completarse.
//   2. Celdas: cada clic re-pinta la tabla, y la celda tocada ya es otro
//      nodo cuando termina el onclick. Se busca el elemento que quedó bajo
//      el puntero y se le pone .lm-pop.
//   3. Resultados: los números de las tarjetas cuentan desde cero al abrir
//      la etapa, y los puntos de los gráficos de Chart.js entran en orden.
// Con movimiento reducido no hace nada (y apaga la animación de Chart.js).
// ════════════════════════════════════════════════════════════════════════
(function () {
  'use strict';
  const reducido = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ── Chart.js ──────────────────────────────────────────────────────────
  if (window.Chart && window.Chart.defaults) {
    if (reducido) {
      window.Chart.defaults.animation = false;
    } else {
      window.Chart.defaults.animation = Object.assign({}, window.Chart.defaults.animation, {
        duration: 700,
        easing: 'easeOutCubic',
        // Cada punto entra un poco después del anterior (tope 0,6 s).
        delay: ctx => (ctx.type === 'data' && ctx.mode === 'default') ? Math.min(ctx.dataIndex * 45, 600) : 0
      });
    }
  }
  if (reducido) return;

  // ── 1 · Pastillas de paso ─────────────────────────────────────────────
  function estadoFila(row) {
    return [...row.querySelectorAll('.step-pill')].map(p =>
      p.classList.contains('done') ? 'd' : (p.classList.contains('active') ? 'a' : '-'));
  }
  function vigilarFila(row) {
    if (row._lm) return;
    row._lm = { prev: estadoFila(row) };
    new MutationObserver(() => {
      const ahora = estadoFila(row);
      const prev = row._lm.prev;
      const pills = row.querySelectorAll('.step-pill');
      if (prev.length === ahora.length) {
        ahora.forEach((e, i) => {
          if (e === 'd' && prev[i] !== 'd') pills[i].classList.add('lm-recien');
          else if (e === 'a' && prev[i] !== 'a') pills[i].classList.add('lm-activa');
        });
      }
      row._lm.prev = ahora;
    }).observe(row, { childList: true, subtree: true, attributes: true, attributeFilter: ['class'] });
  }
  document.querySelectorAll('.steps-row').forEach(vigilarFila);

  // ── 2 · Celdas que rebotan ────────────────────────────────────────────
  const CELDAS = '.matrix td.cell, .cmp-cell, .rob-rate, .ci-cell, .cell-int, .pill, .opt, .lf-chip, .lf-add';
  function pop(el) {
    if (!el) return;
    el.classList.remove('lm-pop');
    void el.offsetWidth;            // reinicia la animación si se toca dos veces
    el.classList.add('lm-pop');
    el.addEventListener('animationend', () => el.classList.remove('lm-pop'), { once: true });
  }
  document.addEventListener('click', ev => {
    if (!ev.target.closest || !ev.target.closest(CELDAS)) return;
    // El onclick del módulo ya corrió y quizá re-pintó: buscar lo que quedó
    // bajo el puntero. Con teclado (detail 0) no hay coordenadas.
    let el = null;
    if (ev.detail > 0 && document.elementFromPoint) {
      const bajo = document.elementFromPoint(ev.clientX, ev.clientY);
      el = bajo && bajo.closest ? bajo.closest(CELDAS) : null;
    }
    pop(el || (ev.target.isConnected ? ev.target.closest(CELDAS) : null));
  });

  // ── 3 · Números que cuentan al abrir resultados ───────────────────────
  // Solo cifras simples: «12», «3/5», «0.82», «64%». Lo demás se deja quieto.
  const NUMEROS = '.res-kpi .rk-num, .kpi-card .k-val';
  function contar(el) {
    const txt = el.textContent.trim();
    const m = txt.match(/^(\d+(?:\.\d+)?)(\s*(?:\/\s*\d+|%))?$/);
    if (!m) return;
    const fin = parseFloat(m[1]);
    if (!(fin > 0)) return;
    const dec = (m[1].split('.')[1] || '').length;
    const cola = m[2] || '';
    const dur = 700, t0 = performance.now();
    const pinta = v => { el.textContent = v.toFixed(dec) + cola; };
    // Pestaña oculta: requestAnimationFrame se congela; mejor no animar.
    if (document.hidden) return;
    const paso = t => {
      const k = Math.min(1, (t - t0) / dur);
      pinta(fin * (1 - Math.pow(1 - k, 3)));
      if (k < 1) requestAnimationFrame(paso); else el.textContent = txt;
    };
    pinta(0);
    requestAnimationFrame(paso);
    // Red de seguridad: si el cuadro se congela, el número final igual queda.
    setTimeout(() => { el.textContent = txt; }, dur + 400);
  }
  const res = document.getElementById('stage-results');
  if (res) {
    let visible = !res.classList.contains('is-hidden');
    new MutationObserver(() => {
      const ahora = !res.classList.contains('is-hidden');
      if (ahora && !visible) setTimeout(() => res.querySelectorAll(NUMEROS).forEach(contar), 60);
      visible = ahora;
    }).observe(res, { attributes: true, attributeFilter: ['class'] });
  }
})();
